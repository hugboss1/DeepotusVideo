// Preset regions the user can drop onto the canvas. Coordinates assume a
// 1080x1920 canvas; TemplateEditor clamps them to the actual canvas on add.

const PRESETS = [
  {
    key: "video_full",
    label: "Full-screen video",
    hint: "video_slot · 1080×1920",
    region: { type: "video_slot", x: 0, y: 0, width: 1080, height: 1920,
      z_index: 0, fit: "cover", audio_volume: 1.0, slot_name: "video",
      slot_label: "Main video", default_provider: "seedance" },
  },
  {
    key: "video_top_half",
    label: "Top half video",
    hint: "video_slot · 1080×960",
    region: { type: "video_slot", x: 0, y: 0, width: 1080, height: 960,
      z_index: 0, fit: "cover", audio_volume: 0.0, slot_name: "top",
      slot_label: "Top video", default_provider: "seedance" },
  },
  {
    key: "video_bottom_half",
    label: "Bottom half video",
    hint: "video_slot · 1080×960",
    region: { type: "video_slot", x: 0, y: 960, width: 1080, height: 960,
      z_index: 0, fit: "cover", audio_volume: 1.0, slot_name: "bottom",
      slot_label: "Bottom video", default_provider: "heygen" },
  },
  {
    key: "video_top60",
    label: "Top 60% video",
    hint: "video_slot · 1080×1152",
    region: { type: "video_slot", x: 0, y: 0, width: 1080, height: 1152,
      z_index: 0, fit: "cover", audio_volume: 0.0, slot_name: "animation",
      slot_label: "Animation", default_provider: "seedance" },
  },
  {
    key: "video_mid30",
    label: "Mid 30% video",
    hint: "video_slot · 1080×576",
    region: { type: "video_slot", x: 0, y: 1152, width: 1080, height: 576,
      z_index: 0, fit: "cover", audio_volume: 1.0, slot_name: "avatar",
      slot_label: "Avatar", default_provider: "heygen" },
  },
  {
    key: "pip_corner",
    label: "PIP corner (avatar)",
    hint: "video_slot · 250×250",
    region: { type: "video_slot", x: 790, y: 1590, width: 250, height: 250,
      z_index: 1, fit: "cover", audio_volume: 1.0, slot_name: "avatar_pip",
      slot_label: "Avatar PIP", default_provider: "heygen" },
  },
  {
    key: "image_full",
    label: "Full image slot",
    hint: "image_slot · 1080×1920",
    region: { type: "image_slot", x: 0, y: 0, width: 1080, height: 1920,
      z_index: 0, fit: "cover", slot_name: "image", slot_label: "Still image" },
  },
  {
    key: "text_header",
    label: "Header text (static)",
    hint: "text · top",
    region: { type: "text", x: 80, y: 90, width: 920, height: 120, z_index: 2,
      text: "HEADER", font: "Space Grotesk", size: 64, color: "#00e5ff",
      weight: 700, align: "center" },
  },
  {
    key: "text_slot",
    label: "Text slot (fillable)",
    hint: "text_slot · lower third",
    region: { type: "text_slot", x: 64, y: 1650, width: 952, height: 120,
      z_index: 2, font: "Space Grotesk", size: 56, color: "#00e5ff",
      weight: 700, default_text: "From the deep.", max_chars: 60,
      slot_name: "caption", slot_label: "Caption" },
  },
  {
    key: "brand_strip",
    label: "Brand strip",
    hint: "brand_strip · bottom 192",
    region: { type: "brand_strip", x: 0, y: 1728, width: 1080, height: 192,
      z_index: 1, background_color: "#02060d", items: [
        { type: "mark", src: "marks/wordmark_cyan.png", x: 64, y: 60, scale: 0.6 },
        { type: "text", text: "$DEEPOTUS", x: 800, y: 95,
          font: "JetBrains Mono", size: 32, color: "#00e5ff", weight: 700 },
      ] },
  },
  {
    key: "separator_h",
    label: "Separator (horizontal)",
    hint: "separator · full width bar",
    region: { type: "separator", x: 0, y: 956, width: 1080, height: 8,
      z_index: 2, color: "#00e5ff" },
  },
  {
    key: "separator_v",
    label: "Separator (vertical)",
    hint: "separator · full height bar",
    region: { type: "separator", x: 536, y: 0, width: 8, height: 1920,
      z_index: 2, color: "#00e5ff" },
  },
  {
    key: "ticker",
    label: "Ticker (scrolling text)",
    hint: "ticker · bottom bar",
    region: { type: "ticker", x: 0, y: 1760, width: 1080, height: 120,
      z_index: 3, background_color: "#050a17", color: "#00e5ff",
      font: "JetBrains Mono", size: 40, speed: 140, direction: "left",
      text: "$DEEPOTUS — from the deep, for the deep" },
  },
];

export function RegionPalette({ onAdd }) {
  return (
    <div className="panel space-y-2">
      <div className="panel-title">Add region</div>
      <div className="grid grid-cols-1 gap-1.5">
        {PRESETS.map((p) => (
          <button
            key={p.key}
            onClick={() => onAdd(structuredClone(p.region))}
            className="btn-ghost text-left px-3 py-2 leading-tight"
            title={p.hint}
          >
            <div className="text-sm font-medium">{p.label}</div>
            <div className="text-[10px] text-slate-500 font-mono">{p.hint}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
