import { useState, useEffect } from "react";
import { api } from "../api/client.js";
import { useToast } from "./Toast.jsx";

const STYLE_OPTIONS = [
  { v: "ugc_raw", label: "UGC Raw" },
  { v: "cinematic", label: "Cinematic" },
  { v: "hybrid", label: "Hybrid" },
];
const ASPECTS = [
  { v: "9:16", label: "9:16 vertical" },
  { v: "1:1", label: "1:1 square" },
  { v: "16:9", label: "16:9 horizontal" },
];
const RESOLUTIONS = [
  { v: "1080p", label: "1080p" },
  { v: "720p", label: "720p" },
];
const LANGUAGES = [
  { v: "EN", label: "🇬🇧 EN" },
  { v: "FR", label: "🇫🇷 FR" },
];

// v1.3.1: Voice modes from DESIGN.md section 1.3
const VOICE_MODES = [
  { v: "", label: "— None (default tone)" },
  { v: "oracle", label: "🔮 Oracle (mythic, slow, weighty)" },
  { v: "alpha", label: "⚡ Alpha (direct, confident, FOMO)" },
  { v: "zen", label: "🧘 Zen (stoic, calm, reframe)" },
  { v: "memer", label: "😎 Memer (playful, internet-native)" },
];

export function GenerationForm({
  startImage,
  endImage,
  templateId,
  draft,           // optional: clone-from-job seed values
  onJobSubmitted,
  onConfigChange,  // v1.4: notify parent of config changes for composition mode
}) {
  const toast = useToast();
  const [mode, setMode] = useState("template");          // "template" | "builder"
  const [style, setStyle] = useState("hybrid");
  const [aspect, setAspect] = useState("9:16");
  const [duration, setDuration] = useState(5);
  const [extendMode, setExtendMode] = useState("loop");
  const [resolution, setResolution] = useState("1080p");
  const [voEnabled, setVoEnabled] = useState(true);
  const [voLang, setVoLang] = useState("EN");
  const [voScript, setVoScript] = useState("");
  const [customCaption, setCustomCaption] = useState("");
  const [notes, setNotes] = useState("");
  const [seed, setSeed] = useState("");
  const [variations, setVariations] = useState(1);  // v1.3: batch multi-seeds
  const [voiceMode, setVoiceMode] = useState("");   // v1.3.1: brand voice mode

  // Builder state
  const [intent, setIntent] = useState("");
  const [injectPersona, setInjectPersona] = useState(true);
  const [generatedPrompt, setGeneratedPrompt] = useState("");
  const [generatedExplanation, setGeneratedExplanation] = useState("");
  const [building, setBuilding] = useState(false);

  const [preview, setPreview] = useState(null);
  const [previewing, setPreviewing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Apply draft (when cloning a job)
  useEffect(() => {
    if (!draft) return;
    if (draft.style) setStyle(draft.style);
    if (draft.aspect_ratio) setAspect(draft.aspect_ratio);
    if (draft.duration_s) setDuration(draft.duration_s);
    if (draft.voiceover_language) setVoLang(draft.voiceover_language);
    if (draft.seed) setSeed(String(draft.seed));
    if (draft.voice_mode) setVoiceMode(draft.voice_mode);
    if (draft.template_id) setMode("template");
    if (draft.final_prompt && !draft.template_id) {
      setMode("builder");
      setGeneratedPrompt(draft.final_prompt);
    }
    toast.info("Job cloned into draft. Tweak and regenerate.");
  }, [draft]);

  // v1.4: emit config to parent for composition mode
  useEffect(() => {
    onConfigChange?.({
      style, aspect, duration, voiceover_language: voLang,
      voice_mode: voiceMode, notes,
    });
  }, [style, aspect, duration, voLang, voiceMode, notes, onConfigChange]);

  const buildRequest = () => {
    const base = {
      image_filename: startImage,
      image_filename_end: endImage || null,
      style,
      aspect_ratio: aspect,
      duration_s: duration,
      extend_mode: extendMode,
      resolution,
      voiceover_enabled: voEnabled,
      voiceover_language: voLang,
      voiceover_script: voScript || null,
      custom_caption: customCaption || null,
      notes: notes || null,
      seed: seed ? parseInt(seed, 10) : null,
      voice_mode: voiceMode || null,
    };
    if (mode === "template") {
      return { ...base, template_id: templateId, prompt_source: "template" };
    } else {
      return { ...base, custom_prompt: generatedPrompt || null, prompt_source: "builder" };
    }
  };

  // Auto-preview for template mode
  useEffect(() => {
    if (mode !== "template" || !startImage || !templateId) {
      setPreview(null);
      return;
    }
    const t = setTimeout(async () => {
      setPreviewing(true);
      setError(null);
      try {
        const p = await api.previewPrompt(buildRequest());
        setPreview(p);
      } catch (e) {
        setError(e.message);
        setPreview(null);
      } finally {
        setPreviewing(false);
      }
    }, 350);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, startImage, templateId, style, aspect, duration, resolution,
      voEnabled, voLang, voScript, customCaption, notes]);

  async function generateFromIntent() {
    if (!intent.trim()) {
      toast.error("Enter some keywords or a description first");
      return;
    }
    setBuilding(true);
    try {
      const result = await api.buildPromptFromIntent({
        intent,
        style,
        duration_s: duration,
        aspect_ratio: aspect,
        voiceover_language: voLang,
        inject_persona: injectPersona,
        voice_mode: voiceMode || null,
      });
      setGeneratedPrompt(result.prompt);
      setGeneratedExplanation(result.explanation);
      if (!voScript && result.suggested_voiceover) {
        setVoScript(result.suggested_voiceover);
      }
      if (!customCaption && result.suggested_caption) {
        setCustomCaption(result.suggested_caption);
      }
      toast.success("Prompt generated. Edit before submitting if needed.");
    } catch (e) {
      toast.error(`Builder failed: ${e.message}`);
    } finally {
      setBuilding(false);
    }
  }

  async function submit() {
    if (!startImage) {
      toast.error("Select a start image first");
      return;
    }
    if (mode === "template" && !templateId) {
      toast.error("Select a template, or switch to Builder mode");
      return;
    }
    if (mode === "builder" && !generatedPrompt.trim()) {
      toast.error("Generate or write a prompt first");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = buildRequest();
      if (variations > 1) {
        const res = await api.generateBatch({ ...payload, variations_count: variations });
        toast.success(`Batch queued: ${variations} variations · seeds ${res.seeds[0]}-${res.seeds[res.seeds.length-1]}`);
      } else {
        await api.generate(payload);
        toast.success("Job submitted. Check the queue panel for progress.");
      }
    } catch (e) {
      setError(e.message);
      toast.error(`Submit failed: ${e.message}`);
    } finally {
      setSubmitting(false);
    }
  }

  const ready = startImage && (
    (mode === "template" && templateId) ||
    (mode === "builder" && generatedPrompt.trim())
  );

  return (
    <div className="panel space-y-4">
      <div className="panel-title">Configuration</div>

      {/* Mode tabs */}
      <div className="flex gap-1 p-1 bg-deep-950/60 rounded-lg">
        <button
          onClick={() => setMode("template")}
          className={`flex-1 text-xs py-2 rounded-md transition-colors ${
            mode === "template"
              ? "bg-bio-cyan/20 text-bio-cyan border border-bio-cyan/40"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          📋 Templates
        </button>
        <button
          onClick={() => setMode("builder")}
          className={`flex-1 text-xs py-2 rounded-md transition-colors ${
            mode === "builder"
              ? "bg-bio-violet/20 text-bio-violet border border-bio-violet/40"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          🧠 Builder
        </button>
      </div>

      {/* Builder mode panel */}
      {mode === "builder" && (
        <div className="space-y-2 p-3 rounded-lg bg-deep-950/40 border border-bio-violet/20">
          <Field label="Intent / keywords">
            <textarea
              className="input text-xs"
              rows={3}
              placeholder="e.g. phone showing chart pumping, shocked face, neon room, fast and chaotic"
              value={intent}
              onChange={(e) => setIntent(e.target.value)}
            />
          </Field>
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={injectPersona}
              onChange={(e) => setInjectPersona(e.target.checked)}
              className="accent-bio-violet"
            />
            Inject deepotus DNA (mascot, deep sea, brand colors)
          </label>
          <button
            onClick={generateFromIntent}
            disabled={building || !intent.trim()}
            className="btn-ghost w-full !py-2 !text-xs disabled:opacity-40"
          >
            {building ? "Generating…" : "✨ Generate prompt"}
          </button>

          {generatedPrompt && (
            <Field label="Generated prompt (editable)">
              <textarea
                className="input font-mono text-[11px]"
                rows={6}
                value={generatedPrompt}
                onChange={(e) => setGeneratedPrompt(e.target.value)}
              />
            </Field>
          )}
          {generatedExplanation && (
            <div className="text-[10px] text-slate-500 italic">
              {generatedExplanation}
            </div>
          )}
        </div>
      )}

      {/* Common settings */}
      <div className="grid grid-cols-2 gap-3">
        <Field label="Style">
          <Select value={style} onChange={setStyle} options={STYLE_OPTIONS} />
        </Field>
        <Field label="Aspect">
          <Select value={aspect} onChange={setAspect} options={ASPECTS} />
        </Field>
        <Field label="Duration (s)">
          <select
            className="input"
            value={duration}
            onChange={(e) => setDuration(+e.target.value)}
          >
            {[5, 10, 15, 20, 25, 30, 40, 50, 60].map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Resolution">
          <Select value={resolution} onChange={setResolution} options={RESOLUTIONS} />
        </Field>
      </div>
      {duration > 10 && (
        <Field label="Extend mode (>10s: Seedance is looped/held)">
          <select
            className="input"
            value={extendMode}
            onChange={(e) => setExtendMode(e.target.value)}
          >
            <option value="loop">loop</option>
            <option value="hold">hold last frame</option>
          </select>
        </Field>
      )}

      {/* Seed (advanced) */}
      <Field label="Seed (optional, for reproducibility)">
        <div className="flex gap-2">
          <input
            type="number"
            className="input flex-1 font-mono"
            placeholder="leave empty for random"
            value={seed}
            onChange={(e) => setSeed(e.target.value)}
          />
          {seed && (
            <button onClick={() => setSeed("")} className="btn-ghost !px-3 text-xs">
              Clear
            </button>
          )}
        </div>
      </Field>

      {/* Variations — v1.3 batch multi-seeds */}
      <Field label={`Variations (${variations} ${variations === 1 ? "video" : "videos"})`}>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <input
              type="range"
              min="1"
              max="8"
              step="1"
              value={variations}
              onChange={(e) => setVariations(parseInt(e.target.value, 10))}
              className="flex-1 accent-bio-cyan"
            />
            <div className="w-8 text-center font-mono text-sm text-bio-cyan">{variations}</div>
          </div>
          {variations > 1 && (
            <div className="text-[10px] p-2 rounded border border-bio-violet/30 bg-bio-violet/5 text-bio-violet space-y-1">
              <div>
                ⚡ Batch mode: {variations} videos with seeds{" "}
                <span className="font-mono">
                  {seed ? `${seed}, ${parseInt(seed,10)+1}, ..., ${parseInt(seed,10)+variations-1}` : "(random base) + offsets"}
                </span>
              </div>
              <div className="opacity-80">
                Estimated cost: {variations} × ~$0.30 ≈ <span className="font-mono">${(variations * 0.3).toFixed(2)}</span> in fal.ai credits
              </div>
            </div>
          )}
        </div>
      </Field>

      {/* Voice mode — v1.3.1 brand-aware tone */}
      <Field label="Voice mode (brand tone)">
        <Select value={voiceMode} onChange={setVoiceMode} options={VOICE_MODES} />
        {voiceMode && (
          <div className="text-[10px] text-bio-cyan/80 mt-1 italic">
            Style hints injected into prompt + caption + voiceover.
          </div>
        )}
      </Field>

      {/* Voiceover */}
      <div className="border-t border-deep-700/50 pt-3">
        <label className="flex items-center gap-2 mb-2 cursor-pointer">
          <input
            type="checkbox"
            checked={voEnabled}
            onChange={(e) => setVoEnabled(e.target.checked)}
            className="accent-bio-cyan"
          />
          <span className="text-sm font-medium">Voiceover (ElevenLabs)</span>
        </label>
        {voEnabled && (
          <div className="space-y-2 pl-6">
            <Field label="Language">
              <Select value={voLang} onChange={setVoLang} options={LANGUAGES} />
            </Field>
            <Field label="Custom script (overrides default)">
              <textarea
                className="input font-mono text-xs"
                rows={2}
                placeholder="Leave empty to use template/builder default"
                value={voScript}
                onChange={(e) => setVoScript(e.target.value)}
              />
            </Field>
          </div>
        )}
      </div>

      <Field label="Custom caption (optional)">
        <textarea
          className="input text-xs"
          rows={2}
          placeholder="Leave empty to use default caption + hashtags"
          value={customCaption}
          onChange={(e) => setCustomCaption(e.target.value)}
        />
      </Field>

      <Field label="Extra context / notes">
        <input
          className="input"
          placeholder="ex: ambiance plus sombre, focus mascotte"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </Field>

      {/* Live preview (template mode only) */}
      {mode === "template" && (
        <div className="border-t border-deep-700/50 pt-3">
          <div className="flex items-center justify-between mb-2">
            <div className="panel-title mb-0">Live Prompt Preview</div>
            {previewing && <span className="text-xs text-bio-cyan animate-pulse">building…</span>}
          </div>
          {!preview && !previewing && (
            <div className="text-xs text-slate-500 italic">
              Pick image + template to see prompt
            </div>
          )}
          {preview && (
            <div className="space-y-2 text-xs font-mono">
              <PreviewBox label="Positive" value={preview.prompt} />
              <PreviewBox label="Negative" value={preview.negative_prompt} muted />
              {preview.voiceover_script && (
                <PreviewBox label={`Voiceover (${voLang})`} value={preview.voiceover_script} />
              )}
            </div>
          )}
        </div>
      )}

      {/* End image indicator */}
      {endImage && (
        <div className="text-[10px] p-2 rounded border border-bio-violet/30 bg-bio-violet/5 text-bio-violet">
          ⚡ Transition mode: Seedance Lite (start → end frame) will be used
        </div>
      )}

      {error && (
        <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded p-2">
          ❌ {error}
        </div>
      )}

      <button
        onClick={submit}
        disabled={!ready || submitting}
        className="btn-primary w-full"
      >
        {submitting
          ? (variations > 1 ? `Queueing ${variations} variations…` : "Submitting…")
          : (variations > 1 ? `🐙 Generate ${variations} Variations` : "🐙 Generate Video")}
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

function Select({ value, onChange, options }) {
  return (
    <select className="input" value={value} onChange={(e) => onChange(e.target.value)}>
      {options.map((o) => (
        <option key={o.v} value={o.v}>{o.label}</option>
      ))}
    </select>
  );
}

function PreviewBox({ label, value, muted }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-bio-cyan/60 mb-1">{label}</div>
      <div className={`p-2 rounded bg-deep-950/60 border border-deep-700/40 whitespace-pre-wrap break-words ${muted ? "text-slate-500" : "text-slate-200"}`}>
        {value}
      </div>
    </div>
  );
}
