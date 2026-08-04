import { useEffect, useRef } from "react";
import { Group, Rect, Text, Transformer } from "react-konva";

const SNAP = 60;
const snap = (v) => Math.round(v / SNAP) * SNAP;

const TYPE_STYLE = {
  video_slot: { fill: "rgba(0,229,255,0.14)", stroke: "#00e5ff" },
  image_slot: { fill: "rgba(168,85,247,0.14)", stroke: "#a855f7" },
  text: { fill: "rgba(251,191,36,0.12)", stroke: "#fbbf24" },
  text_slot: { fill: "rgba(251,191,36,0.16)", stroke: "#fbbf24" },
  brand_strip: { fill: "rgba(148,163,184,0.14)", stroke: "#94a3b8" },
  separator: { fill: "rgba(0,229,255,0.5)", stroke: "#00e5ff" },
  ticker: { fill: "rgba(5,10,23,0.85)", stroke: "#00e5ff" },
  overlay: { fill: "rgba(148,163,184,0.10)", stroke: "#64748b" },
};

function labelFor(r) {
  if (r.type === "video_slot" || r.type === "image_slot")
    return `${r.type === "image_slot" ? "IMG" : "VID"}: ${r.slot_name || "?"}`;
  if (r.type === "text_slot") return `TXT: ${r.slot_name || "?"}`;
  if (r.type === "text") return `"${(r.text || "").slice(0, 18)}"`;
  if (r.type === "brand_strip") return "BRAND STRIP";
  if (r.type === "separator") return "─ SEPARATOR";
  if (r.type === "ticker") return `TICKER: "${(r.text || "").slice(0, 16)}"`;
  return r.type;
}

/**
 * A single draggable / resizable region drawn in canvas-space coordinates.
 * The parent Layer is scaled for preview; coordinates stay full-resolution.
 */
export function RegionNode({ region, selected, canvas, onSelect, onChange }) {
  const shapeRef = useRef();
  const trRef = useRef();

  useEffect(() => {
    if (selected && trRef.current && shapeRef.current) {
      trRef.current.nodes([shapeRef.current]);
      trRef.current.getLayer()?.batchDraw();
    }
  }, [selected]);

  const style = TYPE_STYLE[region.type] || TYPE_STYLE.overlay;
  const cw = canvas.width;
  const ch = canvas.height;

  function clamp(x, y, w, h) {
    w = Math.max(SNAP, Math.min(w, cw));
    h = Math.max(SNAP, Math.min(h, ch));
    x = Math.max(0, Math.min(x, cw - w));
    y = Math.max(0, Math.min(y, ch - h));
    return { x, y, width: w, height: h };
  }

  return (
    <>
      <Group
        x={region.x}
        y={region.y}
        draggable
        onClick={onSelect}
        onTap={onSelect}
        onDragEnd={(e) => {
          const c = clamp(
            snap(e.target.x()),
            snap(e.target.y()),
            region.width,
            region.height
          );
          e.target.position({ x: c.x, y: c.y });
          onChange(c);
        }}
      >
        <Rect
          ref={shapeRef}
          width={region.width}
          height={region.height}
          fill={style.fill}
          stroke={selected ? "#ffffff" : style.stroke}
          strokeWidth={selected ? 5 : 3}
          cornerRadius={4}
          onTransformEnd={() => {
            const node = shapeRef.current;
            const sx = node.scaleX();
            const sy = node.scaleY();
            node.scaleX(1);
            node.scaleY(1);
            const c = clamp(
              snap(region.x),
              snap(region.y),
              snap(node.width() * sx),
              snap(node.height() * sy)
            );
            onChange(c);
          }}
        />
        <Text
          text={labelFor(region)}
          x={12}
          y={12}
          fontSize={34}
          fontStyle="bold"
          fill={selected ? "#ffffff" : style.stroke}
          listening={false}
        />
        <Text
          text={`z${region.z_index ?? 0} · ${region.width}×${region.height}`}
          x={12}
          y={52}
          fontSize={26}
          fill="#94a3b8"
          listening={false}
        />
      </Group>
      {selected && (
        <Transformer
          ref={trRef}
          rotateEnabled={false}
          keepRatio={false}
          ignoreStroke
          anchorSize={14}
          borderStroke="#00e5ff"
          anchorStroke="#00e5ff"
          anchorFill="#02060d"
          boundBoxFunc={(oldBox, newBox) =>
            newBox.width < SNAP || newBox.height < SNAP ? oldBox : newBox
          }
        />
      )}
    </>
  );
}
