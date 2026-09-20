// mod-geo.js — les cartes RÉELLES du lot H : GPX (parse par expressions
// régulières — node n'a pas de DOMParser, le navigateur non plus dans un
// worker), Mercator LOCAL en mètres (conforme, à l'échelle vraie au centre :
// 0,01° de latitude = 1112 m), cadrage à la page et échelle « 1 : N »,
// tuiles XYZ (Terrarium / OSM), marching squares pour les courbes de
// niveau, échantillonnage, paliers, ombrage (Horn, azimut 315°, 45°).
// Module FEUILLE : aucun import, aucun DOM.
export const R_TERRE = 6378137;
const RAD = Math.PI / 180;

/* ── GPX ── */
const _ENT = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" };
const _decoder = (s) => String(s).replace(/&(amp|lt|gt|quot|apos);/g, (_, e) => _ENT[e])
  .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(+n)).trim();
function _attr(attrs, nom) {
  const m = new RegExp(nom + `\\s*=\\s*"([^"]*)"`).exec(attrs) || new RegExp(nom + `\\s*=\\s*'([^']*)'`).exec(attrs);
  return m ? m[1] : null;
}
function _point(attrs, corps) {
  const lat = parseFloat(_attr(attrs, "lat")), lon = parseFloat(_attr(attrs, "lon"));
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) throw new Error("GPX : un point sans lat/lon numériques");
  const e = /<ele>\s*([^<]*)<\/ele>/.exec(corps || "");
  const ele = e && Number.isFinite(parseFloat(e[1])) ? parseFloat(e[1]) : null;
  const n = /<name>([^<]*)<\/name>/.exec(corps || "");
  return { lat, lon, ele, nom: n ? _decoder(n[1]) : "" };
}
const _RE_PT = /<(trkpt|rtept|wpt)\b([^>]*?)(?:\/>|>([\s\S]*?)<\/\1>)/g;
export function gpx_parser(xml) {
  const s = String(xml || "");
  if (!/<gpx\b/i.test(s)) throw new Error("GPX : pas un fichier GPX (balise <gpx> absente)");
  const traces = [], points = [];
  // les segments : chaque <trkseg> et chaque <rte> est UNE trace
  const blocs = s.match(/<(trkseg|rte)\b[\s\S]*?<\/\1>/g) || [];
  for (const b of blocs) {
    const pts = [];
    for (const m of b.matchAll(_RE_PT)) if (m[1] !== "wpt") pts.push(_point(m[2], m[3]));
    if (pts.length) traces.push(pts);
  }
  for (const m of s.matchAll(_RE_PT)) if (m[1] === "wpt") points.push(_point(m[2], m[3]));
  const tous = [...traces.flat(), ...points];
  if (!tous.length) throw new Error("GPX : aucun point (trkpt, rtept, wpt)");
  const emprise = { minLat: Infinity, maxLat: -Infinity, minLon: Infinity, maxLon: -Infinity };
  for (const p of tous) {
    emprise.minLat = Math.min(emprise.minLat, p.lat); emprise.maxLat = Math.max(emprise.maxLat, p.lat);
    emprise.minLon = Math.min(emprise.minLon, p.lon); emprise.maxLon = Math.max(emprise.maxLon, p.lon);
  }
  return { traces, points, emprise, n: tous.length };
}

/* ── Mercator local, à l'échelle vraie au centre ── */
const _lnTan = (lat) => Math.log(Math.tan(Math.PI / 4 + lat * RAD / 2));
export function mercator_m(lat, lon, lat0, lon0) {
  const k = R_TERRE * Math.cos(lat0 * RAD);
  return [k * (lon - lon0) * RAD, k * (_lnTan(lat) - _lnTan(lat0))];
}

export function cadrage(emprise, taille, marge = 40) {
  const lat0 = (emprise.minLat + emprise.maxLat) / 2, lon0 = (emprise.minLon + emprise.maxLon) / 2;
  const [x1] = mercator_m(lat0, emprise.maxLon, lat0, lon0), [x0] = mercator_m(lat0, emprise.minLon, lat0, lon0);
  const [, y1] = mercator_m(emprise.maxLat, lon0, lat0, lon0), [, y0] = mercator_m(emprise.minLat, lon0, lat0, lon0);
  const largeur_m = Math.max(1, x1 - x0), hauteur_m = Math.max(1, y1 - y0);
  const W = +taille.w, H = +taille.h, m = Math.max(0, +marge || 0);
  const m_par_px = Math.max(largeur_m / Math.max(1, W - 2 * m), hauteur_m / Math.max(1, H - 2 * m));
  return {
    centre: [lat0, lon0], m_par_px, largeur_m, hauteur_m,
    vers_px(lat, lon) {
      const [x, y] = mercator_m(lat, lon, lat0, lon0);
      return [W / 2 + x / m_par_px, H / 2 - y / m_par_px];
    },
  };
}
export function echelle_libelle(m_par_px, dpi) {
  const n = Math.round((m_par_px / (0.0254 / dpi)) / 100) * 100;
  return "1 : " + String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

/* ── tuiles XYZ (slippy map) ── */
export function tuile_xyz(lat, lon, z) {
  const n = 2 ** z, lr = lat * RAD;
  return { x: Math.floor((lon + 180) / 360 * n),
           y: Math.floor((1 - Math.log(Math.tan(lr) + 1 / Math.cos(lr)) / Math.PI) / 2 * n) };
}
export function tuiles_couvrant(emprise, z) {
  const a = tuile_xyz(emprise.maxLat, emprise.minLon, z), b = tuile_xyz(emprise.minLat, emprise.maxLon, z);
  const out = { xmin: a.x, xmax: b.x, ymin: a.y, ymax: b.y };
  out.n = (out.xmax - out.xmin + 1) * (out.ymax - out.ymin + 1);
  return out;
}
export function zoom_pour(emprise, maxTuiles = 16) {
  for (let z = 15; z >= 1; z--) if (tuiles_couvrant(emprise, z).n <= maxTuiles) return z;
  return 1;
}
export function latlon_de_tuile(z, x, y) {
  const n = 2 ** z;
  return { lon: x / n * 360 - 180, lat: Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n))) / RAD };
}

/* ── courbes de niveau : marching squares, segments chaînés ── */
export function courbes_niveau(grid, w, h, niveau) {
  const v = (i, j) => grid[j * w + i];
  const t = (a, b) => (niveau - a) / (b - a);
  const segs = [];
  for (let j = 0; j + 1 < h; j++) for (let i = 0; i + 1 < w; i++) {
    const a = v(i, j), b = v(i + 1, j), c = v(i + 1, j + 1), d = v(i, j + 1);
    const cas = (a >= niveau ? 8 : 0) | (b >= niveau ? 4 : 0) | (c >= niveau ? 2 : 0) | (d >= niveau ? 1 : 0);
    if (cas === 0 || cas === 15) continue;
    // les points sur les 4 arêtes : haut (a-b), droite (b-c), bas (d-c), gauche (a-d)
    const H = [i + t(a, b), j], D = [i + 1, j + t(b, c)], B = [i + t(d, c), j + 1], G = [i, j + t(a, d)];
    const push = (p, q) => segs.push([p, q]);
    switch (cas) {
      case 1: case 14: push(G, B); break;
      case 2: case 13: push(B, D); break;
      case 3: case 12: push(G, D); break;
      case 4: case 11: push(H, D); break;
      case 6: case 9: push(H, B); break;
      case 7: case 8: push(G, H); break;
      case 5: case 10: {
        const centre = (a + b + c + d) / 4 >= niveau;
        if ((cas === 5) === centre) { push(G, H); push(B, D); } else { push(G, B); push(H, D); }
        break;
      }
    }
  }
  // chaînage par extrémités
  const cle = (p) => `${Math.round(p[0] * 1e6)}:${Math.round(p[1] * 1e6)}`;
  const parPoint = new Map();
  segs.forEach((s, k) => { for (const p of s) { const c = cle(p); if (!parPoint.has(c)) parPoint.set(c, []); parPoint.get(c).push(k); } });
  const utilise = new Array(segs.length).fill(false);
  const out = [];
  const suivant = (p, kExclu) => {
    const l = (parPoint.get(cle(p)) || []).filter((k) => !utilise[k] && k !== kExclu);
    return l.length ? l[0] : -1;
  };
  for (let k0 = 0; k0 < segs.length; k0++) {
    if (utilise[k0]) continue;
    utilise[k0] = true;
    const ligne = [segs[k0][0], segs[k0][1]];
    for (const sens of [1, -1]) {
      let k = k0;
      for (;;) {
        const bout = sens === 1 ? ligne[ligne.length - 1] : ligne[0];
        const kn = suivant(bout, k);
        if (kn < 0) break;
        utilise[kn] = true;
        const s = segs[kn];
        const autre = cle(s[0]) === cle(bout) ? s[1] : s[0];
        if (sens === 1) ligne.push(autre); else ligne.unshift(autre);
        k = kn;
        if (cle(ligne[0]) === cle(ligne[ligne.length - 1])) break;
      }
    }
    out.push(ligne);
  }
  return out;
}

/* ── échantillonnage, paliers ── */
export function echantillon_moyen(grid, w, h, cx, cy, rayon) {
  let s = 0, n = 0;
  const r2 = rayon * rayon;
  for (let j = Math.max(0, Math.floor(cy - rayon)); j <= Math.min(h - 1, Math.ceil(cy + rayon)); j++) {
    for (let i = Math.max(0, Math.floor(cx - rayon)); i <= Math.min(w - 1, Math.ceil(cx + rayon)); i++) {
      if ((i - cx) ** 2 + (j - cy) ** 2 <= r2 + 1e-9) { s += grid[j * w + i]; n++; }
    }
  }
  return n ? s / n : null;
}
export function paliers_bornes(min, max, n) {
  const out = [];
  for (let k = 1; k < n; k++) out.push(min + k * (max - min) / n);
  return out;
}
export function palier(v, bornes) {
  let k = 0;
  for (const b of bornes) if (v >= b) k++;
  return k;
}

/* ── ombrage (Horn) : rangée 0 = nord ; lumière du nord-ouest, 45° ── */
export function ombrage(grid, w, h, pasM, exag = 1) {
  const out = new Uint8ClampedArray(w * h);
  const g = (i, j) => grid[Math.min(h - 1, Math.max(0, j)) * w + Math.min(w - 1, Math.max(0, i))] * exag;
  const zen = 45 * RAD, az = (360 - 315 + 90) * RAD;
  for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
    const a = g(i - 1, j - 1), b = g(i, j - 1), c = g(i + 1, j - 1);
    const d = g(i - 1, j), f = g(i + 1, j);
    const gg = g(i - 1, j + 1), hh = g(i, j + 1), ii = g(i + 1, j + 1);
    const dzdx = ((c + 2 * f + ii) - (a + 2 * d + gg)) / (8 * pasM);
    const dzdy = ((gg + 2 * hh + ii) - (a + 2 * b + c)) / (8 * pasM);
    const pente = Math.atan(Math.hypot(dzdx, dzdy));
    let aspect = Math.atan2(dzdy, -dzdx);
    if (aspect < 0) aspect += 2 * Math.PI;
    const s = Math.cos(zen) * Math.cos(pente) + Math.sin(zen) * Math.sin(pente) * Math.cos(az - aspect);
    out[j * w + i] = Math.max(0, Math.min(255, Math.round(255 * s)));
  }
  return out;
}
