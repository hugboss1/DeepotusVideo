import { useEffect, useState, useMemo } from "react";
import { api } from "../api/client.js";
import { useToast } from "./Toast.jsx";
import { PhotoAvatarUpload } from "./PhotoAvatarUpload.jsx";
import { PromptBuilder } from "./PromptBuilder.jsx";

const COMPOSITION_LAYOUTS = [
  { v: "sequential", label: "→ Sequential (avatar → animation)" },
  { v: "split_vstack", label: "▦ Split (anim top / avatar bottom)" },
  { v: "split_hstack", label: "▥ Split (anim left / avatar right)" },
];

const VOICE_MODES = [
  { v: "", label: "— None (default tone)" },
  { v: "oracle", label: "🔮 Oracle (mythic, slow)" },
  { v: "alpha", label: "⚡ Alpha (direct, confident)" },
  { v: "zen", label: "🧘 Zen (stoic, calm)" },
  { v: "memer", label: "😎 Memer (playful)" },
];

const ASPECTS = [
  { v: "9:16", label: "9:16 vertical" },
  { v: "1:1", label: "1:1 square" },
  { v: "16:9", label: "16:9 horizontal" },
];

/**
 * HeyGen + Composition form.
 * - Mode "heygen": pure avatar video (script + avatar + voice).
 * - Mode "composition": needs a Seedance side from props.
 */
export function HeyGenForm({
  mode,             // "heygen" | "composition"
  startImage,       // for composition mode, the Seedance start image
  templateId,       // for composition mode, the Seedance template
  seedanceConfig,   // {style, aspect, duration, voiceover_enabled, voiceover_language, notes, voice_mode}
}) {
  const toast = useToast();
  const [heygenHealth, setHeygenHealth] = useState(null);
  const [avatars, setAvatars] = useState([]);
  const [avatarQuery, setAvatarQuery] = useState("");
  const [voices, setVoices] = useState([]);
  const [loadingLists, setLoadingLists] = useState(false);

  const [avatarId, setAvatarId] = useState("");
  const [voiceId, setVoiceId] = useState("");
  const [avatarType, setAvatarType] = useState("avatar");
  const [script, setScript] = useState("");
  const [showBuilder, setShowBuilder] = useState(false);
  const [showUploader, setShowUploader] = useState(false);
  const [aspect, setAspect] = useState("9:16");
  const [speed, setSpeed] = useState(1.0);
  const [voiceMode, setVoiceMode] = useState("");
  const [useAvatarIv, setUseAvatarIv] = useState(false);
  const [customCaption, setCustomCaption] = useState("");

  // Composition specifics
  const [layout, setLayout] = useState("sequential");
  const [transitionDuration, setTransitionDuration] = useState(0.4);
  const [audioSource, setAudioSource] = useState("heygen");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.heygenHealth().then(setHeygenHealth).catch(() =>
      setHeygenHealth({ configured: false, reachable: false, message: "Cannot reach backend" })
    );
  }, []);

  async function loadLists() {
    if (loadingLists) return;
    setLoadingLists(true);
    try {
      const [avList, voList] = await Promise.all([
        api.listHeygenAvatars(),
        api.listHeygenVoices(),
      ]);
      setAvatars(avList.avatars || []);
      setVoices(voList.voices || []);
      toast.success(`Loaded ${avList.avatars?.length || 0} avatars, ${voList.voices?.length || 0} voices`);
    } catch (e) {
      toast.error(`Cannot load HeyGen lists: ${e.message}`);
    } finally {
      setLoadingLists(false);
    }
  }

  useEffect(() => {
    if (heygenHealth?.reachable) loadLists();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [heygenHealth]);

  // Auto-pick first French voice if user picks Zen mode (or just suggest)
  const filteredVoices = useMemo(() => {
    if (voices.length === 0) return [];
    // Sort: language EN first, then FR, then alpha
    return [...voices].sort((a, b) => (a.name || "").localeCompare(b.name || ""));
  }, [voices]);

  async function submit() {
    if (!avatarId || !voiceId) {
      toast.error("Pick an avatar and a voice first");
      return;
    }
    if (!script.trim()) {
      toast.error("Enter a script");
      return;
    }
    setSubmitting(true);
    setError(null);

    const heygenPayload = {
      avatar_id: avatarId,
      voice_id: voiceId,
      script: script.trim(),
      avatar_type: avatarType,
      aspect_ratio: aspect,
      speed,
      voice_mode: voiceMode || null,
      use_avatar_iv: useAvatarIv,
      custom_caption: customCaption || null,
    };

    try {
      if (mode === "heygen") {
        await api.generateHeygen(heygenPayload);
        toast.success("HeyGen job queued. Watch the queue.");
      } else {
        // Composition: bundle Seedance side from props
        if (!startImage) {
          toast.error("Pick a Seedance start image first");
          setSubmitting(false);
          return;
        }
        if (!templateId) {
          toast.error("Pick a Seedance template first");
          setSubmitting(false);
          return;
        }
        const compPayload = {
          seedance: {
            image_filename: startImage,
            template_id: templateId,
            style: seedanceConfig?.style || "hybrid",
            aspect_ratio: seedanceConfig?.aspect || aspect,
            duration_s: seedanceConfig?.duration || 5,
            resolution: "1080p",
            voiceover_enabled: false,  // composition uses HeyGen audio
            voiceover_language: seedanceConfig?.voiceover_language || "EN",
            voice_mode: seedanceConfig?.voice_mode || voiceMode || null,
            notes: seedanceConfig?.notes || null,
            prompt_source: "template",
          },
          heygen: heygenPayload,
          layout,
          transition_duration_s: transitionDuration,
          audio_source: audioSource,
        };
        await api.generateComposition(compPayload);
        toast.success(`Composition queued (${layout}). Both clips generate in parallel.`);
      }
    } catch (e) {
      setError(e.message);
      toast.error(`Submit failed: ${e.message}`);
    } finally {
      setSubmitting(false);
    }
  }

  // ---- Render ----

  if (heygenHealth && !heygenHealth.configured) {
    return (
      <div className="panel">
        <div className="panel-title">HeyGen — Not Configured</div>
        <div className="text-sm text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded p-3 space-y-2">
          <div>
            <strong>HEYGEN_API_KEY not set.</strong>
          </div>
          <div className="text-xs text-slate-300">
            1. Get your key at <a href="https://app.heygen.com/api" target="_blank" rel="noreferrer" className="text-bio-cyan underline">app.heygen.com/api</a>
            <br/>
            2. Add it to <code className="font-mono bg-deep-950/60 px-1 rounded">backend/.env</code> as <code className="font-mono bg-deep-950/60 px-1 rounded">HEYGEN_API_KEY=hg_...</code>
            <br/>
            3. Restart the backend
          </div>
        </div>
      </div>
    );
  }

  if (heygenHealth && !heygenHealth.reachable) {
    return (
      <div className="panel">
        <div className="panel-title">HeyGen — Connection Error</div>
        <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded p-3 space-y-2">
          <div><strong>Cannot reach HeyGen API.</strong></div>
          <div className="text-xs font-mono">{heygenHealth.message}</div>
          <div className="text-xs text-slate-400">
            Check your key and network. Re-test by refreshing this panel.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="panel space-y-3">
      <div className="flex items-center justify-between">
        <div className="panel-title mb-0">
          {mode === "composition" ? "Composition Config" : "HeyGen Config"}
        </div>
        <span className="badge bg-green-500/20 border-green-500/40 text-green-300">
          {heygenHealth?.avatar_count || 0} avatars
        </span>
      </div>

      {/* Avatar */}
      <Field label="Avatar">
        <input
          className="input mb-1"
          placeholder={`Search ${avatars.length} avatars…`}
          value={avatarQuery}
          onChange={(e) => setAvatarQuery(e.target.value)}
          disabled={loadingLists}
        />
        {(() => {
          const q = avatarQuery.trim().toLowerCase();
          const matches = q
            ? avatars.filter((a) =>
                `${a.avatar_name || ""} ${a.name || ""} ${a.avatar_id || ""}`
                  .toLowerCase()
                  .includes(q)
              )
            : avatars;
          const shown = matches.slice(0, 200);
          return (
            <>
              <select
                className="input"
                value={avatarId}
                onChange={(e) => {
                  setAvatarId(e.target.value);
                  const av = avatars.find(
                    (a) => a.avatar_id === e.target.value
                  );
                  if (av) setAvatarType(av.avatar_type || "avatar");
                }}
                disabled={loadingLists}
              >
                <option value="">— Select an avatar —</option>
                {shown.map((a) => (
                  <option key={a.avatar_id} value={a.avatar_id}>
                    {(a.avatar_name || a.name || a.avatar_id)}
                    {a.avatar_type === "talking_photo"
                      ? " (photo)"
                      : a.gender
                      ? ` (${a.gender})`
                      : ""}
                  </option>
                ))}
              </select>
              <div className="text-[10px] text-slate-500 mt-0.5">
                {matches.length > 200
                  ? `${matches.length} matches — showing first 200, refine search`
                  : `${matches.length} match${
                      matches.length === 1 ? "" : "es"
                    }`}
              </div>
            </>
          );
        })()}
        {avatars.length === 0 && !loadingLists && (
          <button onClick={loadLists} className="btn-ghost !text-xs mt-2 w-full">
            🔄 Reload avatar list
          </button>
        )}
      </Field>

      {/* Voice */}
      <Field label="Voice">
        <select
          className="input"
          value={voiceId}
          onChange={(e) => setVoiceId(e.target.value)}
          disabled={loadingLists || filteredVoices.length === 0}
        >
          <option value="">— Select a voice —</option>
          {filteredVoices.map((v) => (
            <option key={v.voice_id} value={v.voice_id}>
              {v.name || v.voice_id}
              {v.language ? ` (${v.language})` : ""}
              {v.gender ? ` ${v.gender === "male" ? "♂" : "♀"}` : ""}
            </option>
          ))}
        </select>
      </Field>

      {/* v1.5: Photo Avatar Upload + Universal Builder */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => { setShowUploader(s => !s); setShowBuilder(false); }}
          className={`flex-1 text-[10px] py-1.5 rounded border transition-all ${showUploader ? "bg-bio-violet/20 border-bio-violet/40 text-bio-violet" : "border-deep-700 text-slate-400"}`}
        >
          📸 {showUploader ? "Hide" : "Upload"} avatar
        </button>
        <button
          type="button"
          onClick={() => { setShowBuilder(s => !s); setShowUploader(false); }}
          className={`flex-1 text-[10px] py-1.5 rounded border transition-all ${showBuilder ? "bg-bio-cyan/20 border-bio-cyan/40 text-bio-cyan" : "border-deep-700 text-slate-400"}`}
        >
          🧠 {showBuilder ? "Hide" : "Show"} builder
        </button>
      </div>

      {showUploader && (
        <PhotoAvatarUpload
          onCreated={(result) => {
            toast.success(`Reloading avatars to include "${result.avatar_name}"`);
            loadLists();
            setAvatarId(result.photo_avatar_id);
            setAvatarType("talking_photo");
            setShowUploader(false);
          }}
        />
      )}

      {showBuilder && (
        <PromptBuilder
          target={mode === "composition" ? "composition" : "heygen"}
          voiceMode={voiceMode}
          language={mode === "composition" ? (seedanceConfig?.voiceover_language || "EN") : "EN"}
          layout={layout}
          style={seedanceConfig?.style || "hybrid"}
          aspect={mode === "composition" ? (seedanceConfig?.aspect || aspect) : aspect}
          duration={seedanceConfig?.duration || 5}
          onHeyGenResult={(r) => {
            setScript(r.script);
            if (!customCaption && r.suggested_caption) setCustomCaption(r.suggested_caption);
          }}
          onCompositionResult={(r) => {
            setScript(r.heygen_script);
            if (!customCaption && r.seedance_caption) setCustomCaption(r.seedance_caption);
          }}
        />
      )}

      {/* Script */}
      <Field label={`Script (${script.length}/4900 chars)`}>
        <textarea
          className="input font-mono text-xs"
          rows={4}
          maxLength={4900}
          placeholder="Listen carefully. The deep doesn't ask permission..."
          value={script}
          onChange={(e) => setScript(e.target.value)}
        />
      </Field>

      {/* Common settings */}
      <div className="grid grid-cols-2 gap-2">
        <Field label="Aspect">
          <select className="input text-xs" value={aspect} onChange={(e) => setAspect(e.target.value)}>
            {ASPECTS.map(a => <option key={a.v} value={a.v}>{a.label}</option>)}
          </select>
        </Field>
        <Field label={`Speed ${speed.toFixed(1)}x`}>
          <input
            type="range" min="0.5" max="2.0" step="0.1"
            value={speed}
            onChange={(e) => setSpeed(parseFloat(e.target.value))}
            className="w-full accent-bio-cyan"
          />
        </Field>
      </div>

      <Field label="Voice mode (brand tone)">
        <select className="input text-xs" value={voiceMode} onChange={(e) => setVoiceMode(e.target.value)}>
          {VOICE_MODES.map(m => <option key={m.v} value={m.v}>{m.label}</option>)}
        </select>
      </Field>

      <label className="flex items-center gap-2 text-xs">
        <input
          type="checkbox"
          checked={useAvatarIv}
          onChange={(e) => setUseAvatarIv(e.target.checked)}
          className="accent-bio-cyan"
        />
        Use Avatar IV (premium motion, photo avatars only)
      </label>

      {/* Composition-specific controls */}
      {mode === "composition" && (
        <div className="border-t border-deep-700/50 pt-3 space-y-3">
          <div className="text-[10px] uppercase tracking-wider text-bio-violet/80 font-mono">
            ⚡ Composition layout
          </div>
          <Field label="Layout">
            <select className="input" value={layout} onChange={(e) => setLayout(e.target.value)}>
              {COMPOSITION_LAYOUTS.map(l => <option key={l.v} value={l.v}>{l.label}</option>)}
            </select>
          </Field>
          {layout === "sequential" && (
            <Field label={`Transition flash (${transitionDuration.toFixed(2)}s)`}>
              <input
                type="range" min="0" max="1.0" step="0.05"
                value={transitionDuration}
                onChange={(e) => setTransitionDuration(parseFloat(e.target.value))}
                className="w-full accent-bio-violet"
              />
            </Field>
          )}
          {(layout === "split_vstack" || layout === "split_hstack") && (
            <Field label="Audio source">
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setAudioSource("heygen")}
                  className={`flex-1 py-1.5 text-xs rounded ${audioSource === "heygen" ? "bg-bio-cyan/20 border border-bio-cyan/40 text-bio-cyan" : "border border-deep-700 text-slate-400"}`}
                >
                  HeyGen (avatar)
                </button>
                <button
                  type="button"
                  onClick={() => setAudioSource("seedance")}
                  className={`flex-1 py-1.5 text-xs rounded ${audioSource === "seedance" ? "bg-bio-cyan/20 border border-bio-cyan/40 text-bio-cyan" : "border border-deep-700 text-slate-400"}`}
                >
                  Seedance (animation)
                </button>
              </div>
            </Field>
          )}
          <div className="text-[10px] text-slate-500 italic">
            Estimated cost: ~$0.30 (Seedance) + ~$0.40 (HeyGen 5s) ≈ <span className="font-mono text-bio-cyan">$0.70</span>
          </div>
          {!startImage && (
            <div className="text-xs text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded p-2">
              ⚠️ Pick a Seedance start image (left panel) for composition mode
            </div>
          )}
          {!templateId && startImage && (
            <div className="text-xs text-amber-300 bg-amber-500/10 border border-amber-500/30 rounded p-2">
              ⚠️ Pick a Seedance template for composition mode
            </div>
          )}
        </div>
      )}

      <Field label="Custom caption (optional)">
        <textarea
          className="input text-xs"
          rows={2}
          placeholder="Leave empty to auto-generate from script + voice mode"
          value={customCaption}
          onChange={(e) => setCustomCaption(e.target.value)}
        />
      </Field>

      {error && (
        <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded p-2">
          ❌ {error}
        </div>
      )}

      <button
        onClick={submit}
        disabled={submitting || !avatarId || !voiceId || !script.trim()}
        className="btn-primary w-full"
      >
        {submitting
          ? "Submitting…"
          : (mode === "composition" ? "🐙 Generate Composition" : "🎤 Generate Avatar Video")}
      </button>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <div className="text-[10px] uppercase tracking-wider text-slate-400 font-mono mb-1">
        {label}
      </div>
      {children}
    </label>
  );
}
