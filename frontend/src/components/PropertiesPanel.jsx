// Edit panel for the selected region + template-level settings.

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-[10px] uppercase tracking-wide text-slate-500">
        {label}
      </span>
      {children}
    </label>
  );
}

function Num({ value, onChange, step = 1, min }) {
  return (
    <input
      type="number"
      className="input w-full"
      value={value ?? 0}
      step={step}
      min={min}
      onChange={(e) =>
        onChange(e.target.value === "" ? 0 : Number(e.target.value))
      }
    />
  );
}

const SWATCHES = [
  "#02060d", "#050a17", "#00e5ff", "#a855f7",
  "#fbbf24", "#ffffff", "#000000",
];

function ColorField({ value, onChange }) {
  const v = value || "";
  const hex = /^#[0-9a-fA-F]{6}$/.test(v) ? v : "#000000";
  return (
    <div className="flex items-center gap-2">
      <input
        type="color"
        value={hex}
        onChange={(e) => onChange(e.target.value)}
        style={{ width: 44, height: 32, padding: 2 }}
        className="shrink-0 cursor-pointer rounded border border-deep-600"
        title="Open color picker"
      />
      <input
        className="input flex-1 font-mono text-xs"
        value={v}
        placeholder="#00e5ff"
        onChange={(e) => onChange(e.target.value)}
      />
      <div className="flex gap-1 shrink-0">
        {SWATCHES.map((c) => (
          <button
            key={c}
            type="button"
            title={c}
            onClick={() => onChange(c)}
            className={`h-5 w-5 rounded border ${
              v.toLowerCase() === c
                ? "border-bio-cyan"
                : "border-deep-700/50"
            }`}
            style={{ backgroundColor: c }}
          />
        ))}
      </div>
    </div>
  );
}

const SLOT_TYPES = ["video_slot", "image_slot", "text_slot"];

export function PropertiesPanel({
  template,
  region,
  onTemplateChange,
  onRegionChange,
  onDeleteRegion,
}) {
  const c = template.canvas;

  return (
    <div className="panel space-y-4">
      <div className="panel-title">Template</div>
      <Field label="Name">
        <input
          className="input w-full"
          value={template.name || ""}
          onChange={(e) => onTemplateChange({ name: e.target.value })}
        />
      </Field>
      <div className="grid grid-cols-3 gap-2">
        <Field label="Width">
          <Num value={c.width}
            onChange={(v) => onTemplateChange({ canvas: { ...c, width: v } })} />
        </Field>
        <Field label="Height">
          <Num value={c.height}
            onChange={(v) => onTemplateChange({ canvas: { ...c, height: v } })} />
        </Field>
        <Field label="FPS">
          <Num value={c.fps}
            onChange={(v) => onTemplateChange({ canvas: { ...c, fps: v } })} />
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Field label="Duration (s)">
          <Num value={c.duration_s} step={1} min={1}
            onChange={(v) =>
              onTemplateChange({ canvas: { ...c, duration_s: v } })} />
        </Field>
        <Field label="Background">
          <ColorField
            value={c.background_color || "#02060d"}
            onChange={(val) =>
              onTemplateChange({ canvas: { ...c, background_color: val } })
            }
          />
        </Field>
      </div>

      <div className="border-t border-deep-700/50 pt-3">
        <div className="panel-title">
          {region ? `Region · ${region.id}` : "Region"}
        </div>
        {!region ? (
          <div className="text-sm text-slate-500 italic">
            Select a region on the canvas to edit it.
          </div>
        ) : (
          <div className="space-y-3">
            <div className="text-[11px] font-mono text-slate-400">
              type: {region.type}
            </div>
            <div className="grid grid-cols-4 gap-2">
              <Field label="X">
                <Num value={region.x}
                  onChange={(v) => onRegionChange({ x: v })} />
              </Field>
              <Field label="Y">
                <Num value={region.y}
                  onChange={(v) => onRegionChange({ y: v })} />
              </Field>
              <Field label="Z">
                <Num value={region.z_index ?? 0}
                  onChange={(v) => onRegionChange({ z_index: v })} />
              </Field>
              <div />
              <Field label="W">
                <Num value={region.width}
                  onChange={(v) => onRegionChange({ width: v })} />
              </Field>
              <Field label="H">
                <Num value={region.height}
                  onChange={(v) => onRegionChange({ height: v })} />
              </Field>
            </div>

            {(region.type === "video_slot" ||
              region.type === "image_slot") && (
              <Field label="Fit">
                <select
                  className="input w-full"
                  value={region.fit || "cover"}
                  onChange={(e) => onRegionChange({ fit: e.target.value })}
                >
                  <option value="cover">cover</option>
                  <option value="contain">contain</option>
                  <option value="stretch">stretch</option>
                  <option value="crop">crop</option>
                </select>
              </Field>
            )}

            {(region.type === "video_slot" ||
              region.type === "image_slot") && (
              <Field label="Motion effect">
                <select
                  className="input w-full"
                  value={region.effect || ""}
                  onChange={(e) =>
                    onRegionChange({ effect: e.target.value || undefined })
                  }
                >
                  <option value="">none</option>
                  <option value="zoom_in">zoom in (Ken Burns)</option>
                  <option value="zoom_out">zoom out (Ken Burns)</option>
                </select>
              </Field>
            )}

            {region.type === "video_slot" && (
              <Field label={`Audio volume (${region.audio_volume ?? 0})`}>
                <input
                  type="range"
                  className="w-full"
                  min={0}
                  max={1}
                  step={0.05}
                  value={region.audio_volume ?? 0}
                  onChange={(e) =>
                    onRegionChange({ audio_volume: Number(e.target.value) })
                  }
                />
              </Field>
            )}

            {SLOT_TYPES.includes(region.type) && (
              <>
                <Field label="Slot name (unique)">
                  <input
                    className="input w-full"
                    value={region.slot_name || ""}
                    onChange={(e) =>
                      onRegionChange({ slot_name: e.target.value })
                    }
                  />
                </Field>
                <Field label="Slot label">
                  <input
                    className="input w-full"
                    value={region.slot_label || ""}
                    onChange={(e) =>
                      onRegionChange({ slot_label: e.target.value })
                    }
                  />
                </Field>
              </>
            )}

            {(region.type === "video_slot" ||
              region.type === "image_slot") && (
              <Field label="Default provider">
                <select
                  className="input w-full"
                  value={region.default_provider || ""}
                  onChange={(e) =>
                    onRegionChange({ default_provider: e.target.value })
                  }
                >
                  <option value="">(none)</option>
                  <option value="seedance">seedance</option>
                  <option value="heygen">heygen</option>
                </select>
              </Field>
            )}

            {(region.type === "text" || region.type === "text_slot") && (
              <>
                {region.type === "text" && (
                  <Field label="Text">
                    <input
                      className="input w-full"
                      value={region.text || ""}
                      onChange={(e) =>
                        onRegionChange({ text: e.target.value })
                      }
                    />
                  </Field>
                )}
                {region.type === "text_slot" && (
                  <Field label="Default text">
                    <input
                      className="input w-full"
                      value={region.default_text || ""}
                      onChange={(e) =>
                        onRegionChange({ default_text: e.target.value })
                      }
                    />
                  </Field>
                )}
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Font">
                    <select
                      className="input w-full"
                      value={region.font || "Space Grotesk"}
                      onChange={(e) =>
                        onRegionChange({ font: e.target.value })
                      }
                    >
                      <option>Space Grotesk</option>
                      <option>Inter</option>
                      <option>JetBrains Mono</option>
                    </select>
                  </Field>
                  <Field label="Size">
                    <Num value={region.size ?? 48}
                      onChange={(v) => onRegionChange({ size: v })} />
                  </Field>
                </div>
                <Field label="Color">
                  <ColorField
                    value={region.color || "#00e5ff"}
                    onChange={(val) => onRegionChange({ color: val })}
                  />
                </Field>
                <Field label="Effect">
                  <select
                    className="input w-full"
                    value={region.effect || ""}
                    onChange={(e) =>
                      onRegionChange({ effect: e.target.value || undefined })
                    }
                  >
                    <option value="">none</option>
                    <option value="pulse">pulse (opacity)</option>
                  </select>
                </Field>
                {region.effect === "pulse" && (
                  <Field label="Pulse speed (Hz)">
                    <Num
                      value={region.effect_speed ?? 1}
                      step={0.1}
                      onChange={(v) => onRegionChange({ effect_speed: v })}
                    />
                  </Field>
                )}
              </>
            )}

            {region.type === "separator" && (
              <Field label="Separator color">
                <ColorField
                  value={region.color || "#00e5ff"}
                  onChange={(val) => onRegionChange({ color: val })}
                />
              </Field>
            )}

            {region.type === "ticker" && (
              <>
                <Field label="Ticker text">
                  <input
                    className="input w-full"
                    value={region.text || ""}
                    onChange={(e) => onRegionChange({ text: e.target.value })}
                  />
                </Field>
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Background">
                    <ColorField
                      value={region.background_color || "#050a17"}
                      onChange={(val) =>
                        onRegionChange({ background_color: val })
                      }
                    />
                  </Field>
                  <Field label="Text color">
                    <ColorField
                      value={region.color || "#00e5ff"}
                      onChange={(val) =>
                        onRegionChange({ color: val })
                      }
                    />
                  </Field>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Font">
                    <select
                      className="input w-full"
                      value={region.font || "JetBrains Mono"}
                      onChange={(e) =>
                        onRegionChange({ font: e.target.value })
                      }
                    >
                      <option>Space Grotesk</option>
                      <option>Inter</option>
                      <option>JetBrains Mono</option>
                    </select>
                  </Field>
                  <Field label="Size">
                    <Num
                      value={region.size ?? 40}
                      onChange={(v) => onRegionChange({ size: v })}
                    />
                  </Field>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Speed (px/s)">
                    <Num
                      value={region.speed ?? 140}
                      onChange={(v) => onRegionChange({ speed: v })}
                    />
                  </Field>
                  <Field label="Direction">
                    <select
                      className="input w-full"
                      value={region.direction || "left"}
                      onChange={(e) =>
                        onRegionChange({ direction: e.target.value })
                      }
                    >
                      <option value="left">scroll left</option>
                      <option value="right">scroll right</option>
                    </select>
                  </Field>
                </div>
                <Field label="Effect">
                  <select
                    className="input w-full"
                    value={region.effect || ""}
                    onChange={(e) =>
                      onRegionChange({ effect: e.target.value || undefined })
                    }
                  >
                    <option value="">none</option>
                    <option value="pulse">pulse (opacity)</option>
                  </select>
                </Field>
              </>
            )}

            {region.type === "brand_strip" &&
              (() => {
                const items = Array.isArray(region.items)
                  ? region.items
                  : [];
                const textItem = items.find((i) => i.type === "text");
                const hasMark = items.some((i) => i.type === "mark");
                const setItems = (next) => onRegionChange({ items: next });
                const setText = (txt) =>
                  textItem
                    ? setItems(
                        items.map((i) =>
                          i === textItem ? { ...i, text: txt } : i
                        )
                      )
                    : setItems([
                        ...items,
                        {
                          type: "text",
                          text: txt,
                          x: Math.round(region.width * 0.6),
                          y: Math.round(region.height * 0.35),
                          font: "JetBrains Mono",
                          size: 32,
                          color: "#00e5ff",
                          weight: 700,
                        },
                      ]);
                const setColor = (col) =>
                  textItem
                    ? setItems(
                        items.map((i) =>
                          i === textItem ? { ...i, color: col } : i
                        )
                      )
                    : setItems([
                        ...items,
                        {
                          type: "text",
                          text: "",
                          x: Math.round(region.width * 0.6),
                          y: Math.round(region.height * 0.35),
                          font: "JetBrains Mono",
                          size: 32,
                          color: col,
                          weight: 700,
                        },
                      ]);
                const toggleMark = (on) =>
                  on
                    ? setItems([
                        {
                          type: "mark",
                          src: "marks/wordmark_cyan.png",
                          x: 64,
                          y: Math.round(region.height * 0.3),
                          scale: 0.6,
                        },
                        ...items,
                      ])
                    : setItems(items.filter((i) => i.type !== "mark"));
                return (
                  <>
                    <Field label="Background color">
                      <ColorField
                        value={region.background_color || "#02060d"}
                        onChange={(val) =>
                          onRegionChange({ background_color: val })
                        }
                      />
                    </Field>
                    <Field label="Brand text (cashtag / tagline)">
                      <input
                        className="input w-full"
                        placeholder="$DEEPOTUS"
                        value={textItem?.text || ""}
                        onChange={(e) => setText(e.target.value)}
                      />
                    </Field>
                    <Field label="Brand text color">
                      <ColorField
                        value={textItem?.color || "#00e5ff"}
                        onChange={(val) => setColor(val)}
                      />
                    </Field>
                    <label className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={hasMark}
                        onChange={(e) => toggleMark(e.target.checked)}
                      />
                      <span>Show wordmark logo</span>
                    </label>
                    <div className="text-[10px] text-slate-500">
                      The wordmark uses the bundled
                      marks/wordmark_cyan.png (degrades gracefully if
                      absent).
                    </div>
                  </>
                );
              })()}

            <button
              className="btn-ghost w-full text-red-300 border-red-500/40"
              onClick={onDeleteRegion}
            >
              Delete region
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
