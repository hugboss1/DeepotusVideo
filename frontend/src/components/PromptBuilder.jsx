import { useState } from "react";
import { api } from "../api/client.js";
import { useToast } from "./Toast.jsx";

const VOICE_MODES = [
  { v: "", label: "— None" },
  { v: "oracle", label: "🔮 Oracle" },
  { v: "alpha", label: "⚡ Alpha" },
  { v: "zen", label: "🧘 Zen" },
  { v: "memer", label: "😎 Memer" },
];

const TARGET_LABELS = {
  seedance: { title: "✨ Seedance Builder", subtitle: "Free-text → visual prompt", action: "Build prompt" },
  heygen:   { title: "✨ HeyGen Builder",   subtitle: "Free-text → avatar script", action: "Build script" },
  composition: { title: "✨ Composition Builder", subtitle: "Free-text → both sides coherent", action: "Build both" },
};

/**
 * Universal target-aware Builder.
 *
 * Props:
 *  - target: "seedance" | "heygen" | "composition"
 *  - voiceMode: optional preselected voice mode (passed in from parent form)
 *  - language: "EN" | "FR"
 *  - layout: required if target=composition (CompositionLayout value)
 *  - style, aspect, duration: needed for seedance / composition
 *  - onSeedanceResult({ prompt, suggested_caption, suggested_voiceover })
 *  - onHeyGenResult({ script, suggested_caption })
 *  - onCompositionResult({ seedance_prompt, seedance_caption, heygen_script })
 */
export function PromptBuilder({
  target = "seedance",
  voiceMode = "",
  language = "EN",
  layout,
  style = "hybrid",
  aspect = "9:16",
  duration = 5,
  onSeedanceResult,
  onHeyGenResult,
  onCompositionResult,
}) {
  const toast = useToast();
  const [intent, setIntent] = useState("");
  const [injectPersona, setInjectPersona] = useState(true);
  const [maxWords, setMaxWords] = useState(60);
  const [localVoiceMode, setLocalVoiceMode] = useState(voiceMode);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);

  const labels = TARGET_LABELS[target] || TARGET_LABELS.seedance;

  async function run() {
    if (intent.trim().length < 3) {
      toast.error("Intent must be at least 3 characters");
      return;
    }
    setRunning(true);
    setResult(null);

    try {
      if (target === "seedance") {
        const out = await api.buildPromptFromIntent({
          intent,
          style,
          duration_s: duration,
          aspect_ratio: aspect,
          voiceover_language: language,
          inject_persona: injectPersona,
          voice_mode: localVoiceMode || null,
        });
        setResult(out);
        onSeedanceResult?.(out);
        toast.success("Seedance prompt built. Click Apply to use it.");
      } else if (target === "heygen") {
        const out = await api.buildScript({
          intent,
          voice_mode: localVoiceMode || null,
          voiceover_language: language,
          max_words: maxWords,
          inject_persona: injectPersona,
        });
        setResult(out);
        onHeyGenResult?.(out);
        toast.success(`Script built (${out.word_count} words).`);
      } else if (target === "composition") {
        const out = await api.buildComposition({
          intent,
          layout: layout || "sequential",
          style,
          aspect_ratio: aspect,
          duration_s: duration,
          voice_mode: localVoiceMode || null,
          voiceover_language: language,
          max_script_words: maxWords,
          inject_persona: injectPersona,
        });
        setResult(out);
        onCompositionResult?.(out);
        toast.success("Both sides built coherently.");
      }
    } catch (e) {
      toast.error(`Builder failed: ${e.message}`);
    } finally {
      setRunning(false);
    }
  }

  function apply() {
    if (!result) return;
    if (target === "seedance") onSeedanceResult?.(result);
    else if (target === "heygen") onHeyGenResult?.(result);
    else if (target === "composition") onCompositionResult?.(result);
    toast.info("Applied to form.");
  }

  return (
    <div className="rounded-lg border border-bio-violet/30 bg-bio-violet/5 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs font-semibold text-bio-violet">{labels.title}</div>
          <div className="text-[10px] text-slate-400">{labels.subtitle}</div>
        </div>
      </div>

      <textarea
        rows={3}
        className="input text-xs"
        placeholder={
          target === "heygen"
            ? "e.g. announce that the chart just broke resistance and shift to alpha mode"
            : target === "composition"
              ? "e.g. show a phone alert with explosive volume spike + avatar explains what just happened"
              : "e.g. ocean creature emerges from the deep, cinematic slow push-in"
        }
        value={intent}
        onChange={(e) => setIntent(e.target.value)}
      />

      <div className="grid grid-cols-2 gap-2">
        <label className="block">
          <div className="text-[9px] uppercase tracking-wider text-slate-400 font-mono mb-1">
            Voice mode
          </div>
          <select
            className="input text-[10px]"
            value={localVoiceMode}
            onChange={(e) => setLocalVoiceMode(e.target.value)}
          >
            {VOICE_MODES.map((m) => <option key={m.v} value={m.v}>{m.label}</option>)}
          </select>
        </label>
        {(target === "heygen" || target === "composition") && (
          <label className="block">
            <div className="text-[9px] uppercase tracking-wider text-slate-400 font-mono mb-1">
              Max words ({maxWords})
            </div>
            <input
              type="range" min="10" max="200" step="5"
              value={maxWords}
              onChange={(e) => setMaxWords(parseInt(e.target.value, 10))}
              className="w-full accent-bio-violet"
            />
          </label>
        )}
      </div>

      <label className="flex items-center gap-2 text-[10px]">
        <input
          type="checkbox"
          checked={injectPersona}
          onChange={(e) => setInjectPersona(e.target.checked)}
          className="accent-bio-violet"
        />
        Inject deepotus brand DNA (mascot, deep-sea cues, vocabulary filter)
      </label>

      <button
        onClick={run}
        disabled={running || intent.trim().length < 3}
        className="btn-secondary w-full !py-1.5 !text-xs"
      >
        {running ? "Building..." : `🧠 ${labels.action}`}
      </button>

      {result && (
        <div className="space-y-1 mt-2 pt-2 border-t border-bio-violet/20">
          {target === "seedance" && (
            <>
              <div className="text-[9px] uppercase font-mono text-slate-500">Prompt</div>
              <pre className="text-[10px] bg-deep-950/60 p-2 rounded whitespace-pre-wrap font-mono leading-relaxed max-h-32 overflow-y-auto">{result.prompt}</pre>
              {result.suggested_voiceover && (
                <>
                  <div className="text-[9px] uppercase font-mono text-slate-500 mt-1">Suggested voiceover</div>
                  <div className="text-[10px] italic text-slate-300">{result.suggested_voiceover}</div>
                </>
              )}
            </>
          )}
          {target === "heygen" && (
            <>
              <div className="text-[9px] uppercase font-mono text-slate-500">
                Script ({result.word_count} words)
              </div>
              <pre className="text-[10px] bg-deep-950/60 p-2 rounded whitespace-pre-wrap font-sans leading-relaxed max-h-32 overflow-y-auto">{result.script}</pre>
              {result.rationale?.length > 0 && (
                <div className="text-[9px] text-slate-500 italic">
                  · {result.rationale.join(" · ")}
                </div>
              )}
            </>
          )}
          {target === "composition" && (
            <>
              <div className="text-[9px] uppercase font-mono text-slate-500">Seedance prompt</div>
              <pre className="text-[10px] bg-deep-950/60 p-2 rounded whitespace-pre-wrap font-mono leading-relaxed max-h-24 overflow-y-auto">{result.seedance_prompt}</pre>
              <div className="text-[9px] uppercase font-mono text-slate-500 mt-1">HeyGen script</div>
              <pre className="text-[10px] bg-deep-950/60 p-2 rounded whitespace-pre-wrap font-sans leading-relaxed max-h-24 overflow-y-auto">{result.heygen_script}</pre>
              <div className="text-[9px] text-bio-cyan italic">
                {result.coherence_rationale}
              </div>
            </>
          )}

          <button onClick={apply} className="btn-ghost !text-[10px] w-full mt-1">
            ↩ Re-apply to form
          </button>
        </div>
      )}
    </div>
  );
}
