import { useEffect, useState } from "react";
import { api } from "../api/client.js";

export function TemplateSelector({ selected, onSelect, disabled }) {
  const [templates, setTemplates] = useState([]);
  const [persona, setPersona] = useState("");

  useEffect(() => {
    api.listTemplates().then((data) => {
      setTemplates(data.templates || []);
      setPersona(data.persona || "");
    });
  }, []);

  return (
    <div className={`panel ${disabled ? "opacity-50" : ""}`}>
      <div className="flex items-baseline justify-between mb-3">
        <div className="panel-title mb-0">Template Library</div>
        <span className="text-xs text-slate-500 font-mono">{persona}</span>
      </div>

      {disabled && (
        <div className="text-xs text-slate-500 italic mb-3 p-2 bg-deep-950/60 rounded border border-deep-700/40">
          Switch back to "Templates" tab to use these presets.
        </div>
      )}

      <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
        {templates.map((tpl) => {
          const isSelected = selected === tpl.id;
          return (
            <button
              key={tpl.id}
              disabled={disabled}
              onClick={() => onSelect(tpl.id)}
              className={`w-full text-left p-3 rounded-lg border transition-all
                ${isSelected ? "border-bio-cyan/60 bg-bio-cyan/5 shadow-glow" : "border-deep-700 hover:border-deep-700/80 hover:bg-deep-800/40"}
                ${disabled ? "cursor-not-allowed" : ""}
              `}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="font-display font-semibold text-sm text-slate-100">
                  {tpl.name}
                </div>
                <span className="badge text-bio-cyan/80 shrink-0">{tpl.duration_s}s</span>
              </div>
              <div className="text-xs text-slate-400 mt-1 line-clamp-2">
                {tpl.description}
              </div>
              <div className="flex flex-wrap gap-1 mt-2">
                <span className="badge">{tpl.camera}</span>
                <span className="badge">{tpl.pacing}</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
