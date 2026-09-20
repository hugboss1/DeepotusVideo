// mod-dxf.js — la découpe laser (lot G) : polylignes du document (px,
// Y vers le bas) → millimètres au dpi du document, origine en bas à
// gauche de la tranche, Y vers le haut ; puis DXF R12 texte : HEADER
// ($INSUNITS 4 = mm), TABLES (un calque), ENTITIES en LWPOLYLINE fermées.
// Module FEUILLE.

const _mm = (v) => { const s = String(Math.round(v * 1000) / 1000); return s.includes(".") ? s : s + ".0"; };

export function polylignes_mm(polylignes, cadre, dpi) {
  const k = 25.4 / (+dpi || 300);
  return (polylignes || []).map((pl) => pl.map(([x, y]) => [Math.round((x - cadre.x) * k * 1000) / 1000, Math.round((cadre.y + cadre.h - y) * k * 1000) / 1000]));
}

const _g = (code, valeur) => `${String(code).padStart(3, " ")}\n${valeur}\n`;
export function dxf_de(polylignes, { calque = "0" } = {}) {
  if (!Array.isArray(polylignes) || !polylignes.length) throw new Error("DXF : aucune polyligne");
  for (const pl of polylignes) if (!Array.isArray(pl) || pl.length < 3) throw new Error("DXF : une polyligne a moins de trois points");
  const nom = String(calque || "0").replace(/[^A-Za-z0-9_-]/g, "_") || "0";
  let s = "";
  s += _g(0, "SECTION") + _g(2, "HEADER") + _g(9, "$ACADVER") + _g(1, "AC1009") + _g(9, "$INSUNITS") + _g(70, "     4") + _g(0, "ENDSEC");
  s += _g(0, "SECTION") + _g(2, "TABLES") + _g(0, "TABLE") + _g(2, "LAYER") + _g(70, "     1")
     + _g(0, "LAYER") + _g(2, nom) + _g(70, "     0") + _g(62, "     7") + _g(6, "CONTINUOUS") + _g(0, "ENDTAB") + _g(0, "ENDSEC");
  s += _g(0, "SECTION") + _g(2, "ENTITIES");
  for (const pl of polylignes) {
    s += _g(0, "LWPOLYLINE") + _g(8, nom) + _g(90, String(pl.length).padStart(6, " ")) + _g(70, "     1");
    for (const [x, y] of pl) s += _g(10, _mm(x)) + _g(20, _mm(y));
  }
  s += _g(0, "ENDSEC") + _g(0, "EOF");
  return s;
}
