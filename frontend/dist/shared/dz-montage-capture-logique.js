// dz-montage-capture-logique.js — t317 (28/10/2026, lot D3 « montage après coup des captures ») : la logique PURE de
// l'éditeur de montage (plan docs/superpowers/plans/2026-10-28-t317-montage-capture.md, spec boîte à outils §8.4).
// SOURCE : frontend/shared/ ; copie OCTET POUR OCTET : frontend/dist/shared/. Aucun DOM. Banc :
// backend/tests/test_capture_montage_ecran.py (sous node).
// Les formules sont CELLES du rendu (app/services/capture_montage.py) : zoomA = zoom_a, segments, versSortie =
// vers_sortie, cadreFormat = cadre_format ; l'aperçu montre donc ce que ffmpeg rendra.

export const FORMATS = { "16:9": [1920, 1080], "9:16": [1080, 1920], "1:1": [1080, 1080] };
export const VITESSES = [2, 4, 8, 16];
export const RAMPE = 400;
export const K_DEFAUT = 1.8, K_MIN = 1.1, K_MAX = 2.5;
const borne = (v, a, b) => Math.max(a, Math.min(b, v));
const ss = (s) => s * s * (3 - 2 * s);

// (niveau, centre x, centre y) à l'instant t (ms de la source) : 1 hors des zooms, montée et descente douces
export function zoomA(m, t) {
  let z = 1, cx = 0.5, cy = 0.5;
  for (const k of (m && m.zooms) || []) {
    if (!(k.t0 <= t && t <= k.t1)) continue;
    const r = Math.min(RAMPE, (k.t1 - k.t0) / 2);
    const e = ss(borne((t - k.t0) / r, 0, 1)) * ss(borne((k.t1 - t) / r, 0, 1));
    z += (k.k - 1) * e; cx += (k.x - 0.5) * e; cy += (k.y - 0.5) * e;
  }
  return { z, cx, cy };
}

// les morceaux gardés [début, fin, vitesse] (ms de la source) ; une coupe « couper » disparaît
export function segments(m, duree) {
  const out = []; let t = 0;
  const cs = ((m && m.coupes) || []).slice().sort((a, b) => a.t0 - b.t0);
  for (const c of cs) {
    const a = Math.max(t, c.t0), b = Math.min(duree, c.t1);
    if (b <= a) continue;
    if (a > t) out.push([t, a, 1]);
    if (c.mode === "accelerer") out.push([a, b, c.vitesse]);
    t = b;
  }
  if (t < duree) out.push([t, duree, 1]);
  return out;
}

export function versSortie(t, segs) {
  let acc = 0;
  for (const [a, b, v] of segs) {
    if (t < a) return acc;
    if (t <= b) return acc + (t - a) / v;
    acc += (b - a) / v;
  }
  return acc;
}

export function horloge(ms) {
  const s = Math.max(0, Math.floor(ms / 1000)), h = Math.floor(s / 3600), r = s % 3600;
  const mm = String(Math.floor(r / 60)).padStart(2, "0"), sec = String(r % 60).padStart(2, "0");
  return h ? `${h}:${mm}:${sec}` : `${mm}:${sec}`;
}

// la fenêtre (paire) au rapport du format, la plus grande possible dans l'image source
export function cadreFormat(fmt, l, h) {
  const [ol, oh] = FORMATS[fmt] || FORMATS["16:9"];
  let w, hh;
  if (l / h > ol / oh) { hh = h; w = Math.round(hh * ol / oh); } else { w = l; hh = Math.round(w * oh / ol); }
  return [Math.max(2, w - (w % 2)), Math.max(2, hh - (hh % 2))];
}

// le rectangle de la SOURCE (px) que montre l'image de sortie à l'instant t : zoom (zoompan) puis recadrage au
// format centré là où tombe le centre du zoom (même calcul que le graphe ffmpeg)
export function fenetre(m, t, l, h, fmt) {
  const { z, cx, cy } = zoomA(m, t);
  const x0 = borne(cx * l - l / z / 2, 0, l - l / z), y0 = borne(cy * h - h / z / 2, 0, h - h / z);
  const ux = (cx * l - x0) * z / l, uy = (cy * h - y0) * z / h;
  const [cw, ch] = cadreFormat(fmt, l - (l % 2), h - (h % 2));
  const kx = borne(ux * l - cw / 2, 0, l - cw), ky = borne(uy * h - ch / 2, 0, h - ch);
  return { sx: x0 + kx / z, sy: y0 + ky / z, sl: cw / z, sh: ch / z };
}

// où en est la lecture de l'aperçu : saut d'une coupe « couper », vitesse d'une coupe « accelerer »
export function lecture(m, t) {
  for (const c of (m && m.coupes) || []) {
    if (t >= c.t0 && t < c.t1) return c.mode === "couper" ? { saut: c.t1, vitesse: 1 } : { saut: null, vitesse: c.vitesse };
  }
  return { saut: null, vitesse: 1 };
}

let compteur = 0;
const nid = (p) => p + Date.now().toString(36).slice(-5) + (compteur++).toString(36);

// un zoom ajouté à l'instant t (fenêtre -500/+1500 ms, bornée à la durée) ; les voisins sont rognés, jamais chevauchés
export function ajouterZoom(m, t, x, y, k, duree) {
  const t0 = Math.max(0, Math.round(t - 500)), t1 = Math.min(duree, Math.round(t + 1500));
  if (t1 - t0 <= 200) return m;
  const z = { id: nid("z"), t0, t1, k: borne(k || K_DEFAUT, K_MIN, K_MAX), x: borne(x, 0, 1), y: borne(y, 0, 1) };
  const autres = [];
  for (const o of m.zooms || []) {
    if (o.t1 <= t0 || o.t0 >= t1) { autres.push(o); continue; }
    if (o.t0 < t0 && t0 - o.t0 > 200) autres.push(Object.assign({}, o, { t1: t0 }));
    else if (o.t1 > t1 && o.t1 - t1 > 200) autres.push(Object.assign({}, o, { t0: t1 }));
  }
  return Object.assign({}, m, { zooms: autres.concat([z]).sort((a, b) => a.t0 - b.t0) });
}

export function ajouterChapitre(m, t, ecran) {
  const h = { id: nid("h"), t: Math.max(0, Math.round(t)), titre: "", ecran: ecran || "" };
  return Object.assign({}, m, { chapitres: (m.chapitres || []).concat([h]).sort((a, b) => a.t - b.t) });
}

export function retirer(m, liste, id) {
  return Object.assign({}, m, { [liste]: (m[liste] || []).filter((x) => x.id !== id) });
}

export function modifier(m, liste, id, champs) {
  return Object.assign({}, m, { [liste]: (m[liste] || []).map((x) => (x.id === id ? Object.assign({}, x, champs) : x)) });
}

// l'écran à l'instant t d'après les événements (pour nommer un chapitre ajouté à la main)
export function ecranA(evenements, t) {
  let e = "";
  for (const x of evenements || []) { if (x.t > t) break; if (x.type === "ecran") e = x.ecran; }
  return e;
}

// le dernier clic non masqué avant t (dans les 3 s) : centre d'un zoom ajouté à la main
export function clicProche(evenements, t) {
  let c = null;
  for (const x of evenements || []) { if (x.t > t) break; if (x.type === "clic" && !x.secret && t - x.t <= 3000) c = x; }
  return c ? { x: c.x, y: c.y } : { x: 0.5, y: 0.5 };
}

// les écrans dont le nom se traduit (libellés du rail de la coque) ; les autres sont des noms propres (Quick, Studio…)
export const ECRANS = { library: "coque.rail.bibliotheque", scheduler: "coque.rail.planificateur",
  episodes: "coque.rail.chapitres", sonvfx: "coque.rail.sonvfx", templates: "coque.rail.modeles" };

// le libellé d'un chapitre : son titre, sinon l'écran (traduit, ou mot capitalisé), sinon son rang
export function libelleChapitre(h, i, T) {
  if (h.titre) return h.titre;
  if (T && ECRANS[h.ecran]) return T(ECRANS[h.ecran]);
  const e = (h.ecran || "").replace(/[_-]/g, " ");
  return e ? e.charAt(0).toUpperCase() + e.slice(1) : String(i + 1);
}

// le brouillon du Planificateur : demain 10 h (heure locale), sans canaux (ceux du projet actif, t307)
export function brouillon(rendu, titre, fmt, maintenant) {
  const d = new Date(maintenant || Date.now());
  d.setDate(d.getDate() + 1); d.setHours(10, 0, 0, 0);
  return { title: String(titre || "").slice(0, 200), caption: rendu.chapitres_texte || "", job_id: rendu.job_id,
    run_at: d.toISOString().replace(/\.\d{3}Z$/, ""), status: "draft", format: fmt };
}

// les chapitres sans titre prennent le libellé de leur écran (dans la langue de l'écran) avant d'être gardés ou rendus
export function titresRemplis(m, T) {
  return Object.assign({}, m, { chapitres: (m.chapitres || []).map((h, i) => (h.titre ? h : Object.assign({}, h,
    { titre: libelleChapitre(h, i, T).slice(0, 80) }))) });
}
