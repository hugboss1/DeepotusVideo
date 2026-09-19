// mod-pixelui.js — le persona PIXEL (lot E) : les outils raster sur un calque
// image du document et le mode pixel-art vers le Tilelab / Spritelab.
// Chaque geste = lecture du PNG en tampon {w, h, data} (une fois, à
// « Éditer les pixels »), opération PURE (mod-pixel / mod-pixelart), PUT du
// PNG au journal du serveur (`.pix<k>.png` ×10), puis `op_image_rev` : le
// JSON ne porte qu'un entier, l'href gagne `?v=rev`. Le Ctrl+Z du document
// ne rend pas les pixels : « Annuler pixels » dépile le journal (D1). Les
// sélections (masques en px natifs) vivent dans la session.
import { op_ajouter, op_calque_ajouter, op_image_rev, op_pixelart, op_supprimer } from "./mod-doc.js";
import { pinceau, gomme, seau, sel_rect, sel_lasso, sel_baguette, sel_couleur, sel_croitre, sel_contracter,
         sel_inverser, sel_bbox, masque_calque, niveaux, courbes, hsl, noir_blanc, seuil, flou, cloner,
         extraire } from "./mod-pixel.js";
import { ligne_pixel, rect_pixel, symetrie, palette_extraire, quantifier, pixeliser, raccord_3x3,
         feuille_tuiles, bande, pelure, pelure_double, pixel_parfait, masque_losange, pavage_iso, rasteriser, DITHERS } from "./mod-pixelart.js";

const SNS = "http://www.w3.org/2000/svg";
export const OUTILS_PIXEL = [
  { id: "px-pinceau", touche: "b", glyphe: "🖌", titre: "Pinceau — rayon, dureté et couleur dans le panneau (B)" },
  { id: "px-gomme", touche: "e", glyphe: "◻", titre: "Gomme raster — rend les pixels transparents (E)" },
  { id: "px-seau", touche: "g", glyphe: "🪣", titre: "Seau — remplit la zone contiguë (ou globale) à la tolérance près (G)" },
  { id: "px-crayon", touche: "k", glyphe: "✎", titre: "Crayon pixel-parfait — un pixel de large, symétrie du document (K)" },
  { id: "px-ligne", touche: "i", glyphe: "╱", titre: "Ligne pixel-parfaite (Bresenham) (I)" },
  { id: "px-rectpx", touche: "r", glyphe: "▭", titre: "Rectangle pixel — le contour, un pixel de large (R)" },
  { id: "px-selrect", touche: "m", glyphe: "⬚", titre: "Sélection rectangle — Maj ajoute, Alt retire (M)" },
  { id: "px-lasso", touche: "l", glyphe: "◌", titre: "Lasso — Maj ajoute, Alt retire (L)" },
  { id: "px-baguette", touche: "w", glyphe: "✧", titre: "Baguette magique — pixels contigus semblables (tolérance du panneau) (W)" },
  { id: "px-cloner", touche: "c", glyphe: "⧉", titre: "Tampon de clonage — Alt+clic fixe la source, glisser peint (C)" },
];
export const HINTS_PIXEL = {
  "px-pinceau": "glisser peint · clic droit = secondaire (∅ = gomme) · Maj+clic = segment depuis le dernier point · Alt+clic = pipette · X échange",
  "px-gomme": "gommer : les pixels deviennent transparents (respecte la sélection)",
  "px-seau": "cliquer une zone : elle se remplit — Global remplit tous les pixels semblables",
  "px-crayon": "un pixel de large, pixel-parfait (les coins en L s'effacent) · clic droit = secondaire · Maj+clic = segment · Alt+clic = pipette",
  "px-ligne": "glisser : une ligne pixel-parfaite entre les deux points",
  "px-rectpx": "glisser : le contour d'un rectangle, un pixel de large",
  "px-selrect": "glisser un rectangle · Maj ajoute · Alt retire · Échap désélectionne",
  "px-lasso": "entourer à main levée · Maj ajoute · Alt retire",
  "px-baguette": "cliquer : les pixels contigus de la même couleur (± tolérance)",
  "px-cloner": "Alt+clic : la source · glisser : les pixels de la source se copient sous le curseur",
};

/* ── pures ── */
// point du document → pixel natif de l'objet image (la fenêtre de rognage
// est étirée sur le rectangle de l'objet ; la rotation est ignorée)
export function pixel_de_doc(o, dx, dy) {
  const r = o.rognage || { x: 0, y: 0, w: o.nat.w, h: o.nat.h };
  return [r.x + (dx - o.x) / o.w * r.w, r.y + (dy - o.y) / o.h * r.h];
}
export function doc_de_pixel(o, px, py) {
  const r = o.rognage || { x: 0, y: 0, w: o.nat.w, h: o.nat.h };
  return [o.x + (px - r.x) / r.w * o.w, o.y + (py - r.y) / r.h * o.h];
}
// le nom du dépôt en Bibliothèque : `vector_` = provenance vectorlab (dit
// dans la route /images/upload), le reste assaini
export function nom_depot(docId, href, role) {
  const a = (s) => String(s || "").replace(/\.png$/i, "").replace(/[^A-Za-z0-9_-]+/g, "-");
  return `vector_${a(docId)}_${a(role)}_${a(href)}.png`;
}
// la taille native d'une image change (pixeliser, extraire) : le rognage
// devenu faux tombe — commande pure, groupes compris
export function op_image_nat(doc, id, nat) {
  if (!nat || !(nat.w >= 1) || !(nat.h >= 1)) throw new Error(`image ${id}: nat {w, h} ≥ 1`);
  const chercher = (objs) => {
    for (const o of objs || []) {
      if (o.id === id) return o;
      if (o.type === "groupe") { const t = chercher(o.enfants); if (t) return t; }
    }
    return null;
  };
  let o = null;
  for (const c of doc.calques) { o = chercher(c.objets); if (o) break; }
  if (!o || o.type !== "image") throw new Error(`image introuvable: ${id}`);
  o.nat = { w: Math.round(nat.w), h: Math.round(nat.h) };
  delete o.rognage;
}
// les cadres d'animation = les objets image du calque nommé « cadres », dans l'ordre
export function cadres_de(doc) {
  const c = (doc.calques || []).find((k) => String(k.nom || "").toLowerCase() === "cadres");
  return c ? c.objets.filter((o) => o.type === "image") : [];
}
export function paletteHTML(palette, courante) {
  if (!palette || !palette.length) return `<i class="px-note">aucune couleur — extraire ou peindre</i>`;
  return palette.map((c) => `<button data-couleur="${c}" class="px-pastille${c === courante ? " actif" : ""}" style="background:${c}" title="${c}"></button>`).join("");
}

/* ── UI ── */
export function initPixelUI(VL) {
  const { $, etat } = VL;
  const stage = $("#stage");
  etat.px = { id: null, href: null, tampon: null, masque: null, rayon: 4, durete: 1, couleur: "#000000",
              tolerance: 16, global: false, grille: true, pelure: false, source: null, occupe: false,
              secondaire: null, forme: "rond", parfait: true, dernier: null, fps: 12 };   // lot 2 : gestes du Sprite Editor
  const cache = new Map();                  // href → tampon (cadres, pelure)
  let geste = null, apercu = null, rafId = 0;

  // les boutons d'outils du persona dans la barre (après ceux du vecteur)
  const nav = $("#outils");
  for (const o of OUTILS_PIXEL) {
    const b = document.createElement("button");
    b.dataset.outil = o.id; b.className = "outil-pixel"; b.title = o.titre; b.textContent = o.glyphe;
    b.addEventListener("click", () => VL.setOutil(o.id));
    nav.appendChild(b);
  }

  /* ── tampon ↔ PNG ── */
  const objetImage = (id) => { const t = id && VL.objetDe(id); return t && t.objet.type === "image" ? t.objet : null; };
  const courant = () => objetImage(etat.px.id);
  async function lireTampon(href, rev) {
    const r = await fetch(VL.imageUrl(href, rev), { cache: "no-store" });
    if (!r.ok) throw new Error(`image ${href} introuvable (${r.status})`);
    const bm = await createImageBitmap(await r.blob());
    const cv = document.createElement("canvas");
    cv.width = bm.width; cv.height = bm.height;
    const cx = cv.getContext("2d"); cx.drawImage(bm, 0, 0);
    const d = cx.getImageData(0, 0, cv.width, cv.height);
    return { w: d.width, h: d.height, data: new Uint8ClampedArray(d.data) };
  }
  function canvasDe(t) {
    const cv = document.createElement("canvas");
    cv.width = t.w; cv.height = t.h;
    cv.getContext("2d").putImageData(new ImageData(new Uint8ClampedArray(t.data), t.w, t.h), 0, 0);
    return cv;
  }
  const pngDe = (t) => new Promise((res, rej) => canvasDe(t).toBlob((b) => b ? res(b) : rej(new Error("PNG impossible")), "image/png"));
  async function editer(id) {
    const o = objetImage(id);
    if (!o) { VL.toast("sélectionner un calque image", true); return; }
    etat.px.occupe = true;
    try {
      const t = await lireTampon(o.href, o.rev);
      etat.px.id = o.id; etat.px.href = o.href; etat.px.tampon = t; etat.px.masque = null;
      cache.set(o.href, t);
      VL.toast(`pixels de ${o.href} chargés (${t.w}×${t.h})`);
    } catch (e) { VL.toast(e.message, true); }
    etat.px.occupe = false;
    VL.setSelection([o.id]); rendrePanneau(); VL.rendreOverlay();
  }
  // le tampon part au serveur ; l'objet prend la révision — UNE commande
  async function commettre(nat) {
    const o = courant();
    if (!o) return;
    const t = etat.px.tampon;
    const png = await pngDe(t);
    const r = await fetch(`/api/vector/docs/${encodeURIComponent(etat.docId)}/images/${encodeURIComponent(o.href)}`,
      { method: "PUT", headers: { "Content-Type": "image/png" }, body: png });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    cache.set(o.href, t);
    VL.executer((doc) => {
      if (nat) op_image_nat(doc, o.id, nat);
      op_image_rev(doc, o.id, d.rev);
    });
    rendrePanneau();
  }
  const garde = (fn) => async (...a) => {
    if (etat.px.occupe) return;
    etat.px.occupe = true;
    try { await fn(...a); } catch (e) { VL.toast(e.message, true); }
    etat.px.occupe = false;
  };
  async function annulerPixels() {
    const o = courant();
    if (!o) return;
    const r = await fetch(`/api/vector/docs/${encodeURIComponent(etat.docId)}/images/${encodeURIComponent(o.href)}/annuler`, { method: "POST" });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    const t = await lireTampon(o.href, d.rev || 0);
    etat.px.tampon = t; cache.set(o.href, t);
    VL.executer(op_image_rev, o.id, d.rev);
    VL.toast(`pixels annulés (révision ${d.rev})`);
    rendrePanneau();
  }

  /* ── gestes (capture : les outils du vecteur ne voient rien) ── */
  const estPixel = () => etat.persona === "pixel" && String(etat.outil).startsWith("px-");
  const pixelDe = (o, ev) => { const [dx, dy] = VL.docPt(ev.clientX, ev.clientY); return pixel_de_doc(o, dx, dy); };
  const sym = () => (etat.doc.pixelart && etat.doc.pixelart.symetrie) || { h: false, v: false };
  const miroir = (pts, entier) => {
    const s = sym(), t = etat.px.tampon;
    if (entier) return symetrie(pts, t.w, t.h, s);
    const out = pts.slice();
    for (const [x, y] of pts) {
      if (s.h) out.push([t.w - x, y]);
      if (s.v) out.push([x, t.h - y]);
      if (s.h && s.v) out.push([t.w - x, t.h - y]);
    }
    return out;
  };
  // lot 2 : en tuile iso, la peinture est BORNÉE au losange quand aucune sélection n'est posée
  let losange = null;
  const masqueEffectif = () => {
    if (etat.px.masque) return etat.px.masque;
    const t = etat.px.tampon; if (!t || !(etat.doc.pixelart && etat.doc.pixelart.iso)) return undefined;
    if (!losange || losange.w !== t.w || losange.h !== t.h) losange = { w: t.w, h: t.h, m: masque_losange(t.w, t.h) };
    return losange.m;
  };
  const opts = (g) => ({ rayon: etat.px.rayon, couleur: (g && g.couleur) || etat.px.couleur, durete: etat.px.durete, masque: masqueEffectif(), forme: etat.px.forme });
  // lot 2 : le crayon PIXEL-PARFAIT repart du tampon de départ à chaque cadre — tracé entier re-filtré
  function crayonParfait(g) {
    const t = { w: g.base.w, h: g.base.h, data: new Uint8ClampedArray(g.base.data) };
    let pix = [];
    for (let i = 0; i < g.points.length; i++) {
      const a = g.points[Math.max(0, i - 1)], b = g.points[i];
      const seg = i === 0 ? [b] : ligne_pixel(a[0], a[1], b[0], b[1]);
      for (const p of seg) { const d = pix[pix.length - 1]; if (!d || d[0] !== p[0] || d[1] !== p[1]) pix.push(p); }
    }
    if (etat.px.parfait !== false) pix = pixel_parfait(pix);
    for (const p of miroir(pix, true)) {
      if (g.efface) gomme(t, [p], { rayon: 0.5, masque: masqueEffectif() });
      else pinceau(t, [p], { rayon: 0.5, couleur: g.couleur || etat.px.couleur, masque: masqueEffectif() });
    }
    return t;
  }
  // applique le geste courant sur un tampon (aperçu incrémental ou final)
  function appliquer(t, g, depuis) {
    const pts = g.points.slice(depuis);
    if (!pts.length) return;
    // pinceau et gomme JOIGNENT : le segment part du dernier point déjà appliqué
    const joint = depuis > 0 ? g.points.slice(depuis - 1) : pts;
    switch (g.efface && g.type === "px-pinceau" ? "px-gomme" : g.type) {
      case "px-pinceau": for (const tr of traits(miroir(joint, false), joint.length)) pinceau(t, tr, opts(g)); break;
      case "px-gomme": for (const tr of traits(miroir(joint, false), joint.length)) gomme(t, tr, opts(g)); break;
      case "px-crayon": {
        const pix = [];
        for (let i = 0; i < pts.length; i++) {
          const a = i ? pts[i - 1] : (depuis ? g.points[depuis - 1] : pts[0]);
          pix.push(...ligne_pixel(a[0], a[1], pts[i][0], pts[i][1]));
        }
        for (const p of miroir(pix, true)) { if (g.efface) gomme(t, [p], { rayon: 0.5, masque: masqueEffectif() }); else pinceau(t, [p], { rayon: 0.5, couleur: g.couleur || etat.px.couleur, masque: masqueEffectif() }); }
        break;
      }
      case "px-cloner": {
        for (const [x, y] of pts) cloner(t, etat.px.source[0] + (x - g.x0), etat.px.source[1] + (y - g.y0), x, y, etat.px.rayon);
        break;
      }
    }
  }
  // un trait miroir = autant de polylignes que d'images symétriques
  function traits(pts, n) {
    const out = [];
    for (let i = 0; i < pts.length; i += n) out.push(pts.slice(i, i + n));
    return out;
  }
  function apercuRendre() {
    rafId = 0;
    if (!apercu) return;
    const el = $("#pxApercu");
    if (el) el.setAttribute("href", canvasDe(apercu).toDataURL());
  }
  const apercuDemander = () => { if (!rafId) rafId = requestAnimationFrame(apercuRendre); };

  // lot 2 : le clic droit peint avec la secondaire — pas de menu contextuel en persona Pixel
  stage.addEventListener("contextmenu", (ev) => { if (etat.doc && estPixel()) ev.preventDefault(); }, true);
  const PEINTURE = ["px-pinceau", "px-crayon", "px-ligne", "px-rectpx", "px-seau"];
  stage.addEventListener("pointerdown", (ev) => {
    const droit = ev.button === 2;
    if ((ev.button !== 0 && !droit) || !etat.doc || !estPixel()) return;
    if (droit && !PEINTURE.includes(etat.outil)) return;
    ev.stopPropagation(); ev.preventDefault();
    const cible = ev.target.closest && ev.target.closest("[data-objet]");
    let o = courant();
    if (!o || (cible && cible.dataset.objet !== o.id && objetImage(cible.dataset.objet))) {
      const id = cible && objetImage(cible.dataset.objet) ? cible.dataset.objet : null;
      if (!id) { VL.toast("cliquer un calque image (ou « Éditer les pixels »)", true); return; }
      editer(id);                                  // le geste reprend au clic suivant
      return;
    }
    const t = etat.px.tampon;
    const [px, py] = pixelDe(o, ev);
    const outil = etat.outil;
    // lot 2 : Alt+clic = pipette (le cloner garde Alt = source) — bouton droit + Alt → la secondaire
    if (ev.altKey && outil !== "px-cloner" && (PEINTURE.includes(outil) || outil === "px-gomme")) {
      const x = Math.floor(px), y = Math.floor(py);
      if (x < 0 || y < 0 || x >= t.w || y >= t.h) return;
      const k = (y * t.w + x) * 4;
      if (t.data[k + 3] === 0) { VL.toast("pixel transparent — couleur inchangée"); return; }
      const hex = "#" + [t.data[k], t.data[k + 1], t.data[k + 2]].map((v) => v.toString(16).padStart(2, "0").toUpperCase()).join("");
      if (droit) etat.px.secondaire = hex; else etat.px.couleur = hex;
      VL.toast(`${droit ? "secondaire" : "couleur"} : ${hex}`); rendrePanneau(); VL.surRendu();
      return;
    }
    const couleur = droit ? etat.px.secondaire : etat.px.couleur, efface = droit && etat.px.secondaire === null;
    if (outil === "px-cloner" && ev.altKey) { etat.px.source = [px - 0.5, py - 0.5]; VL.toast(`source de clonage : (${Math.floor(px)}, ${Math.floor(py)})`); return; }
    if (outil === "px-cloner" && !etat.px.source) { VL.toast("Alt+clic pour fixer la source", true); return; }
    if (outil === "px-seau") {
      const x = Math.floor(px), y = Math.floor(py);
      if (x < 0 || y < 0 || x >= t.w || y >= t.h) return;
      if (efface) { VL.toast("secondaire transparente : le seau ne remplit rien", true); return; }
      garde(async () => {
        for (const [sx, sy] of miroir([[x, y]], true)) seau(t, sx, sy, couleur, { tolerance: etat.px.tolerance, global: etat.px.global, masque: masqueEffectif() });
        await commettre();
      })();
      etat.px.dernier = [x, y];
      return;
    }
    if (outil === "px-baguette") {
      const x = Math.floor(px), y = Math.floor(py);
      if (x < 0 || y < 0 || x >= t.w || y >= t.h) return;
      poserMasque(sel_baguette(t, x, y, etat.px.tolerance), ev);
      return;
    }
    const entier = ["px-crayon", "px-ligne", "px-rectpx"].includes(outil);
    // les outils à rayon prennent le CENTRE du pixel en entier (mod-pixel) : −0,5
    const p0 = entier ? [Math.floor(px), Math.floor(py)] : [px - 0.5, py - 0.5];
    // lot 2 : Maj+clic = un segment depuis le dernier point posé (pinceau, crayon, gomme) — une commande
    if (ev.shiftKey && etat.px.dernier && ["px-pinceau", "px-gomme", "px-crayon"].includes(outil)) {
      const d0 = entier ? [Math.floor(etat.px.dernier[0]), Math.floor(etat.px.dernier[1])] : [etat.px.dernier[0] - 0.5 + 0.5, etat.px.dernier[1]];
      const g = { type: outil, points: [d0, p0], x0: d0[0], y0: d0[1], couleur, efface, applique: 0, base: t };
      const res = outil === "px-crayon" ? crayonParfait(g) : (appliquer(t, g, 0), t);
      etat.px.tampon = res; etat.px.dernier = p0;
      garde(commettre)();
      return;
    }
    geste = { type: outil, points: [p0], x0: p0[0], y0: p0[1], shift: ev.shiftKey, alt: ev.altKey, applique: 0, couleur, efface, base: t };
    if (["px-pinceau", "px-gomme", "px-crayon", "px-cloner"].includes(outil)) {
      apercu = outil === "px-crayon" ? crayonParfait(geste) : { w: t.w, h: t.h, data: new Uint8ClampedArray(t.data) };
      if (outil !== "px-crayon") appliquer(apercu, geste, 0);
      geste.applique = 1;
      VL.rendreOverlay(); apercuDemander();
    }
  }, true);
  stage.addEventListener("pointermove", (ev) => {
    if (!geste) return;
    ev.stopPropagation();
    const o = courant();
    if (!o) return;
    const [px, py] = pixelDe(o, ev);
    const entier = ["px-crayon", "px-ligne", "px-rectpx"].includes(geste.type);
    const p = entier ? [Math.floor(px), Math.floor(py)] : [px - 0.5, py - 0.5];
    const der = geste.points[geste.points.length - 1];
    if (der[0] === p[0] && der[1] === p[1]) return;
    geste.points.push(p);
    if (apercu) { if (geste.type === "px-crayon") apercu = crayonParfait(geste); else appliquer(apercu, geste, geste.applique); geste.applique = geste.points.length; apercuDemander(); }
    else dessinerTmp();
  }, true);
  stage.addEventListener("pointerup", (ev) => {
    if (!geste) return;
    ev.stopPropagation();
    const g = geste; geste = null;
    const t = etat.px.tampon, o = courant();
    const tmp = $("#ovTmp"); if (tmp) tmp.innerHTML = "";
    if (!o || !t) { apercu = null; return; }
    const p0 = g.points[0], p1 = g.points[g.points.length - 1];
    etat.px.dernier = p1;                          // lot 2 : Maj+clic repartira d'ici
    if (["px-pinceau", "px-gomme", "px-crayon", "px-cloner"].includes(g.type)) {
      // l'aperçu EST le résultat : il a reçu tout le geste, incrémentalement
      etat.px.tampon = apercu; apercu = null;
      garde(commettre)();
      return;
    }
    if (g.type === "px-ligne" || g.type === "px-rectpx") {
      const pix = g.type === "px-ligne" ? ligne_pixel(p0[0], p0[1], p1[0], p1[1]) : rect_pixel(p0[0], p0[1], p1[0], p1[1]);
      garde(async () => {
        for (const p of miroir(pix, true)) { if (g.efface) gomme(t, [p], { rayon: 0.5, masque: masqueEffectif() }); else pinceau(t, [p], { rayon: 0.5, couleur: g.couleur || etat.px.couleur, masque: masqueEffectif() }); }
        await commettre();
      })();
      return;
    }
    if (g.type === "px-selrect") {
      const x = Math.floor(Math.min(p0[0], p1[0])), y = Math.floor(Math.min(p0[1], p1[1]));
      const w = Math.ceil(Math.max(p0[0], p1[0])) - x, h = Math.ceil(Math.max(p0[1], p1[1])) - y;
      poserMasque(sel_rect(t.w, t.h, { x, y, w, h }), g);
    }
    if (g.type === "px-lasso") poserMasque(sel_lasso(t.w, t.h, g.points), g);
  }, true);
  function poserMasque(m, mod) {
    const t = etat.px.tampon, prev = etat.px.masque;
    if (mod.shiftKey || mod.shift) { if (prev) for (let i = 0; i < m.length; i++) m[i] = Math.max(m[i], prev[i]); }
    else if (mod.altKey || mod.alt) { if (prev) for (let i = 0; i < m.length; i++) m[i] = prev[i] && !m[i] ? prev[i] : 0; else m = null; }
    etat.px.masque = m && sel_bbox(m, t.w, t.h) ? m : null;
    VL.rendreOverlay(); rendrePanneau();
  }
  function dessinerTmp() {
    const tmp = $("#ovTmp"), o = courant();
    if (!tmp || !o || !geste) return;
    tmp.innerHTML = "";
    const pts = geste.type === "px-lasso" ? geste.points : [geste.points[0], geste.points[geste.points.length - 1]];
    const ecr = pts.map(([px, py]) => VL.ecranPt(...doc_de_pixel(o, px, py)));
    const el = document.createElementNS(SNS, geste.type === "px-lasso" ? "polyline" : "rect");
    if (geste.type === "px-lasso") el.setAttribute("points", ecr.map((p) => p.join(",")).join(" "));
    else {
      const [a, b] = ecr;
      el.setAttribute("x", Math.min(a[0], b[0])); el.setAttribute("y", Math.min(a[1], b[1]));
      el.setAttribute("width", Math.abs(b[0] - a[0])); el.setAttribute("height", Math.abs(b[1] - a[1]));
    }
    el.setAttribute("fill", "none"); el.setAttribute("stroke", "#ffd166"); el.setAttribute("stroke-dasharray", "4 3");
    tmp.appendChild(el);
  }

  /* ── overlay : cadre de l'image éditée, masque, grille pixel, pelure, aperçu ── */
  const suivantOverlay = VL.surOverlay;
  VL.surOverlay = (ov) => {
    suivantOverlay(ov);
    const o = courant();
    if (!o || etat.persona !== "pixel") return;
    const t = etat.px.tampon;
    const [sx, sy] = VL.ecranPt(o.x, o.y), sw = o.w * etat.zoom, sh = o.h * etat.zoom;
    const r = o.rognage || { x: 0, y: 0, w: o.nat.w, h: o.nat.h };
    const el = (nom, attrs, hote = ov) => { const e = document.createElementNS(SNS, nom); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); hote.appendChild(e); return e; };
    const fenetre = (id, cv, opacite) => {
      const s = el("svg", { x: sx, y: sy, width: sw, height: sh, viewBox: `${r.x} ${r.y} ${r.w} ${r.h}`, preserveAspectRatio: "none", class: "px-couche" });
      el("image", { id, x: 0, y: 0, width: t.w, height: t.h, href: cv ? cv.toDataURL() : "", opacity: opacite, preserveAspectRatio: "none", style: "image-rendering:pixelated" }, s);
    };
    // pelure d'oignon : le cadre précédent à demi-alpha là où le courant est vide
    if (etat.px.pelure) {
      const cadres = cadres_de(etat.doc), i = cadres.findIndex((c) => c.id === o.id);
      const prec = i > 0 ? cache.get(cadres[i - 1].href) : null, suiv = i >= 0 && i + 1 < cadres.length ? cache.get(cadres[i + 1].href) : null;
      if (prec || suiv) fenetre("pxPelure", canvasDe(pelure_double(t, prec, suiv, 0.5)), 1);   // lot 2 : rouge = précédent, bleu = suivant
    }
    if (apercu) fenetre("pxApercu", canvasDe(apercu), 1);
    // grille pixel quand un pixel fait 6 px d'écran au moins ; lignes de tuile plus marquées
    const kx = sw / r.w, ky = sh / r.h;
    if (etat.px.grille && kx >= 6 && ky >= 6) {
      const tuile = etat.doc.pixelart && etat.doc.pixelart.tuile, g = el("g", { class: "px-grille" });
      let d = "", dt = "";
      const iso = !!(etat.doc.pixelart && etat.doc.pixelart.iso && tuile);
      for (let i = 0; i <= r.w; i++) { const x = sx + i * kx; ((tuile && !iso && (i + r.x) % tuile.w === 0) ? (dt += `M${x} ${sy}v${sh}`) : (d += `M${x} ${sy}v${sh}`)); }
      for (let j = 0; j <= r.h; j++) { const y = sy + j * ky; ((tuile && !iso && (j + r.y) % tuile.h === 0) ? (dt += `M${sx} ${y}h${sw}`) : (d += `M${sx} ${y}h${sw}`)); }
      if (iso) {                                   // lot 2 : le losange 2:1 de chaque tuile
        for (let j = 0; j * tuile.h < r.h; j++) for (let i = 0; i * tuile.w < r.w; i++) {
          const x0 = sx + i * tuile.w * kx, y0 = sy + j * tuile.h * ky, x1 = x0 + tuile.w * kx, y1 = y0 + tuile.h * ky, cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
          dt += `M${cx} ${y0}L${x1} ${cy}L${cx} ${y1}L${x0} ${cy}Z`;
        }
      }
      el("path", { d, stroke: "rgba(255,255,255,.14)", "stroke-width": 1, fill: "none" }, g);
      if (dt) el("path", { d: dt, stroke: "rgba(255,209,102,.55)", "stroke-width": 1, fill: "none" }, g);
    }
    // le masque de sélection : une nappe jaune translucide + sa bbox
    if (etat.px.masque) {
      const m = etat.px.masque, cv = document.createElement("canvas"); cv.width = t.w; cv.height = t.h;
      const im = new ImageData(t.w, t.h);
      for (let i = 0; i < m.length; i++) { im.data[i * 4] = 255; im.data[i * 4 + 1] = 209; im.data[i * 4 + 2] = 102; im.data[i * 4 + 3] = m[i] ? 90 : 0; }
      cv.getContext("2d").putImageData(im, 0, 0);
      fenetre("pxMasque", cv, 1);
      const b = sel_bbox(m, t.w, t.h);
      if (b) {
        const [ax, ay] = VL.ecranPt(...doc_de_pixel(o, b.x, b.y)), [bx, by] = VL.ecranPt(...doc_de_pixel(o, b.x + b.w, b.y + b.h));
        el("rect", { x: ax, y: ay, width: bx - ax, height: by - ay, fill: "none", stroke: "#ffd166", "stroke-dasharray": "5 3", class: "px-selbbox" });
      }
    }
    el("rect", { x: sx, y: sy, width: sw, height: sh, fill: "none", stroke: "#39b3d0", "stroke-dasharray": "6 4", class: "px-cadre" });
  };

  /* ── clavier : les touches du persona (capture, avant le cœur) ── */
  document.addEventListener("keydown", (ev) => {
    if (etat.persona !== "pixel" || ev.ctrlKey || ev.altKey || ev.metaKey) return;
    if (/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || "")) return;
    const k = ev.key.toLowerCase();
    const o = OUTILS_PIXEL.find((x) => x.touche === k);
    if (o) { VL.setOutil(o.id); ev.stopImmediatePropagation(); ev.preventDefault(); return; }
    if (k === "x") {                         // lot 2 : échange primaire / secondaire
      if (etat.px.secondaire === null) { VL.toast("secondaire transparente : rien à échanger"); return; }
      [etat.px.couleur, etat.px.secondaire] = [etat.px.secondaire, etat.px.couleur];
      rendrePanneau(); VL.surRendu(); ev.stopImmediatePropagation(); ev.preventDefault(); return;
    }
    if (ev.key === "Enter" && cadres_de(etat.doc || {}).length > 1) { basculerLecture(); ev.stopImmediatePropagation(); ev.preventDefault(); return; }
    if (ev.key === "Escape" && etat.px.masque) { etat.px.masque = null; VL.rendreOverlay(); rendrePanneau(); ev.stopImmediatePropagation(); }
  }, true);

  /* ── le panneau Pixel ── */
  const hote = $("#panneauPixel");
  const num = (id, v, attrs = "") => `<input type="number" id="${id}" value="${v}" ${attrs}/>`;
  function rendrePanneau() {
    if (!hote) return;
    if (!etat.doc) { hote.innerHTML = ""; return; }
    const o = courant(), t = etat.px.tampon, p = etat.px;
    const sel = etat.selection.length === 1 ? objetImage(etat.selection[0]) : null;
    const pa = etat.doc.pixelart || {}, tuile = pa.tuile || { w: 16, h: 16 }, s = pa.symetrie || {};
    const bb = p.masque && t ? sel_bbox(p.masque, t.w, t.h) : null;
    const cadres = cadres_de(etat.doc);
    hote.innerHTML = `
      <div class="ap-ligne"><span>Image</span>${o ? `<i class="img-src" id="pxNom" title="${o.href}">${o.href} · ${t.w}×${t.h}${o.rev ? ` · rév. ${o.rev}` : ""}</i>`
        : `<button id="pxEditer" ${sel ? "" : "disabled"} title="Charge les pixels de l'image sélectionnée">Éditer les pixels</button>`}</div>
      ${o ? `<div class="ap-ligne"><span></span><button id="pxAnnuler" title="Dépile le journal raster du serveur (dix états)">↶ Annuler pixels</button><button id="pxFermer" title="Quitte l'édition (les pixels sont déjà sauvés)">Terminer</button></div>` : ""}
      <div class="ap-ligne"><span>Couleur</span><input type="color" id="pxCouleur" value="${p.couleur}"/>
        <span style="width:auto" title="Secondaire : clic droit ; ∅ = transparente = gomme">2ᵉ</span><input type="color" id="pxSecondaire" value="${p.secondaire || "#FFFFFF"}"${p.secondaire ? "" : ' class="vide"'}/><button id="pxSecVider" title="Secondaire transparente (le clic droit gomme)">∅</button>
        <span style="width:auto">rayon</span>${num("pxRayon", p.rayon, 'min="0.5" step="0.5" title="Rayon du pinceau, de la gomme, du clonage (px natifs)"')}</div>
      <div class="ap-ligne"><span>Dureté</span><input type="range" id="pxDurete" min="0" max="1" step="0.05" value="${p.durete}" title="1 = bord net, 0 = dégradé jusqu'au centre"/></div>
      <div class="ap-ligne"><span>Tolér.</span>${num("pxTol", p.tolerance, 'min="0" max="255" title="Seau et baguette : écart de couleur admis"')}
        <label title="Le seau remplit TOUS les pixels semblables, contigus ou non"><input type="checkbox" id="pxGlobal"${p.global ? " checked" : ""}/> global</label></div>
      <details open><summary class="px-tete">Sélection${bb ? ` · ${bb.w}×${bb.h}` : " · aucune"}</summary>
        <div class="ap-ligne"><span></span><i class="px-note">tout, aucune, inverser, croître, contracter, par couleur : menu des outils de sélection</i></div>
        <div class="ap-ligne"><button id="pxMasqueCalque" ${p.masque ? "" : "disabled"} title="Le masque devient la transparence du calque image (alpha ← min)">Masque de calque</button>
          <button id="pxVersVecteur" ${p.masque ? "" : "disabled"} title="Extrait la sélection en image posée à sa place, puis ouvre Vectoriser">→ vecteur</button></div>
      </details>
      <details><summary class="px-tete">Ajustements</summary>
        <div class="ap-ligne"><span>Niveaux</span>${num("pxNoir", 0, 'min="0" max="254" title="Point noir"')}${num("pxBlanc", 255, 'min="1" max="255" title="Point blanc"')}${num("pxGamma", 1, 'min="0.1" max="5" step="0.1" title="Gamma"')}<button id="pxNiveaux" ${t ? "" : "disabled"}>OK</button></div>
        <div class="ap-ligne"><span>Courbe</span><span style="width:auto">128 →</span>${num("pxCourbe", 128, 'min="0" max="255" title="Sortie du point de contrôle du milieu"')}<button id="pxCourbes" ${t ? "" : "disabled"}>OK</button></div>
        <div class="ap-ligne"><span>HSL</span>${num("pxH", 0, 'min="-180" max="180" title="Teinte (°)"')}${num("pxS", 0, 'min="-100" max="100" title="Saturation (%)"')}${num("pxL", 0, 'min="-100" max="100" title="Luminosité (%)"')}<button id="pxHsl" ${t ? "" : "disabled"}>OK</button></div>
        <div class="ap-ligne"><button id="pxNB" ${t ? "" : "disabled"}>Noir &amp; blanc</button><span style="width:auto">seuil</span>${num("pxSeuilV", 128, 'min="0" max="255"')}<button id="pxSeuil" ${t ? "" : "disabled"}>OK</button></div>
        <div class="ap-ligne"><span>Flou</span>${num("pxFlouR", 2, 'min="1" max="50" title="Rayon (px)"')}<button id="pxFlou" ${t ? "" : "disabled"}>OK</button></div>
      </details>
      <details ${pa.tuile ? "open" : ""}><summary class="px-tete">Pixel-art</summary>
        <div class="ap-ligne"><span>Tuile</span>${num("pxTuileW", tuile.w, 'min="1" title="Largeur d\'une tuile (px)"')}<span style="width:auto">×</span>${num("pxTuileH", tuile.h, 'min="1"')}
          <button id="pxTuileOK" title="Pose les unités de tuile sur le document (rendu au plus proche voisin)">${pa.tuile ? "↻" : "OK"}</button></div>
        <div class="ap-ligne"><label><input type="checkbox" id="pxGrille"${p.grille ? " checked" : ""}/> grille pixel</label>
          <label title="Tuile isométrique 2:1 : grille en losange, peinture bornée au losange, raccord en pavage iso"><input type="checkbox" id="pxIso"${pa.iso ? " checked" : ""}/> iso 2:1</label>
          <label title="Les gestes se répètent en miroir"><input type="checkbox" id="pxSymH"${s.h ? " checked" : ""}/> sym. H</label>
          <label><input type="checkbox" id="pxSymV"${s.v ? " checked" : ""}/> V</label></div>
        <div class="ap-ligne"><span>Palette</span>${num("pxPalN", (pa.palette || []).length || 8, 'min="2" max="64" title="Nombre de couleurs à extraire"')}
          <button id="pxPalExtraire" ${t ? "" : "disabled"} title="Palette indexée par median cut, sauvée avec le document">Extraire</button>
          <button id="pxQuantifier" ${t && pa.palette ? "" : "disabled"} title="Ramène chaque pixel à la couleur de palette la plus proche">Quantifier</button></div>
        <div class="px-palette" id="pxPalette">${paletteHTML(pa.palette || [], p.couleur)}</div>
        <div class="ap-ligne"><span>Rastériser</span>${num("pxRastW", (pa.tuile && pa.tuile.w) || 64, 'min="1" max="4096" title="Largeur cible (px) — la hauteur suit"')}
          <select id="pxRastPal" title="Palette appliquée après la réduction"><option value="aucune">libre</option><option value="doc"${pa.palette ? "" : " disabled"}>palette du doc</option><option value="extraire">extraire N</option></select>
          <select id="pxRastDither" title="Tramage"><option value="aucun">sans tramage</option><option value="ordonne">ordonné</option><option value="floyd">Floyd-Steinberg</option></select></div>
        <div class="ap-ligne"><span></span><button id="pxRasteriser" ${t ? "" : "disabled"} title="Une image générée (Bibliothèque → Image) devient un calque pixel éditable : réduction au plus proche voisin, palette, tramage — annulable">Rastériser cette image</button></div>
        <div class="ap-ligne"><button id="pxPixeliser" ${t ? "" : "disabled"} title="Réduit l'image à la largeur de tuile, au plus proche voisin">Pixeliser l'image</button>
          <button id="pxPixeliserVec" ${etat.selection.length && !o ? "" : "disabled"} title="Rastérise la sélection vectorielle en une tuile (plus proche voisin) posée à sa place">Pixeliser la sélection</button></div>
        <div class="ap-ligne"><button id="pxRaccord" ${t ? "" : "disabled"} title="${pa.iso ? "Pavage iso ×9 (décalages ±w/2, ±h/2) et score de raccord" : "Mosaïque 3×3 et score de raccord (métrique du Tilelab)"}">Raccord ${pa.iso ? "iso ×9" : "3×3"}</button><span id="pxScore" style="width:auto"></span></div>
        <canvas id="pxRaccordCv" class="px-raccord" hidden></canvas>
        <div class="ap-ligne"><span>Feuille</span>${num("pxCols", 8, 'min="1" title="Colonnes de la feuille de tuiles"')}
          <button id="pxFeuille" title="Toutes les images du document (même taille) → PNG + index JSON téléchargés">PNG + JSON</button></div>
      </details>
      <details open><summary class="px-tete">Ligne de temps · ${cadres.length} cadre(s)</summary>
        <div id="pxTimeline" class="px-timeline">${cadres.length ? cadres.map((c, i) => `<canvas class="px-vignette${o && c.id === o.id ? " actif" : ""}" data-id="${c.id}" width="40" height="40" title="cadre ${i + 1} — cliquer pour l'éditer"></canvas>`).join("") : `<i class="px-note">aucun cadre — « ＋ Dupliquer » fait de l'image éditée le cadre 1</i>`}</div>
        <div class="ap-ligne"><button id="pxPlay" ${cadres.length > 1 ? "" : "disabled"} title="Lecture / pause (Entrée)">${lecture.playing ? "⏸" : "▶"}</button>
          <label title="Boucler"><input type="checkbox" id="pxLoop"${lecture.loop ? " checked" : ""}/> boucle</label><span style="width:auto">FPS</span>${num("pxFps", p.fps, 'min="1" max="60"')}
          <canvas id="pxLecture" class="px-lecture" width="48" height="48"></canvas></div>
        <div class="ap-ligne"><button id="pxCadreNouveau" ${o ? "" : "disabled"} title="Copie le cadre édité juste après lui">＋ Dupliquer</button>
          <button id="pxCadreVide" ${o ? "" : "disabled"} title="Un cadre transparent juste après le courant">＋ Vide</button>
          <button id="pxCadreSuppr" ${o && cadres.length > 1 && cadres.some((c) => c.id === o.id) ? "" : "disabled"} title="Supprime le cadre édité (annulable)">✕</button></div>
        <div class="ap-ligne"><label title="Rouge = cadre précédent, bleu = suivant, en transparence"><input type="checkbox" id="pxPelure"${p.pelure ? " checked" : ""}/> pelure</label>
          <button id="pxBande" ${cadres.length ? "" : "disabled"} title="Les cadres côte à côte → PNG">Bande PNG</button></div>
        <div class="ap-ligne"><button id="pxTilelab" ${t ? "" : "disabled"} title="Dépose le PNG dans la Bibliothèque (source vectorlab) et ouvre le Tilelab">→ Tilelab</button>
          <button id="pxSpritelab" ${t ? "" : "disabled"} title="Dépose le PNG dans la Bibliothèque et ouvre le Spritelab">→ Spritelab</button></div>
      </details>`;
    lier();
  }
  const val = (id) => +String($("#" + id).value).replace(",", ".");
  function lier() {
    const on = (id, ev, fn) => { const e = $("#" + id); if (e) e.addEventListener(ev, fn); };
    on("pxEditer", "click", () => editer(etat.selection[0]));
    on("pxAnnuler", "click", garde(annulerPixels));
    on("pxFermer", "click", () => { etat.px.id = null; etat.px.tampon = null; etat.px.masque = null; rendrePanneau(); VL.rendreOverlay(); });
    on("pxCouleur", "input", (ev) => { etat.px.couleur = ev.target.value.toUpperCase(); });
    on("pxSecondaire", "input", (ev) => { etat.px.secondaire = ev.target.value.toUpperCase(); ev.target.classList.remove("vide"); });
    on("pxSecVider", "click", () => { etat.px.secondaire = null; rendrePanneau(); });
    on("pxRayon", "change", () => { etat.px.rayon = Math.max(0.5, val("pxRayon")); });
    on("pxDurete", "input", () => { etat.px.durete = val("pxDurete"); });
    on("pxTol", "change", () => { etat.px.tolerance = Math.max(0, Math.min(255, val("pxTol"))); });
    on("pxGlobal", "change", (ev) => { etat.px.global = ev.target.checked; });
    on("pxGrille", "change", (ev) => { etat.px.grille = ev.target.checked; VL.rendreOverlay(); });
    on("pxPelure", "change", (ev) => { etat.px.pelure = ev.target.checked; chargerCadres().then(() => VL.rendreOverlay()); });
    const t = etat.px.tampon;
    const masqueOp = (fn) => () => { etat.px.masque = fn(); if (etat.px.masque && !sel_bbox(etat.px.masque, t.w, t.h)) etat.px.masque = null; VL.rendreOverlay(); rendrePanneau(); };
    const ajuster = (fn) => garde(async () => { fn(t, etat.px.masque); await commettre(); });
    on("pxMasqueCalque", "click", ajuster((im, m) => masque_calque(im, m)));
    on("pxNiveaux", "click", ajuster((im, m) => niveaux(im, { noir: val("pxNoir"), blanc: val("pxBlanc"), gamma: val("pxGamma") }, m)));
    on("pxCourbes", "click", ajuster((im, m) => courbes(im, [[0, 0], [128, val("pxCourbe")], [255, 255]], m)));
    on("pxHsl", "click", ajuster((im, m) => hsl(im, { h: val("pxH"), s: val("pxS"), l: val("pxL") }, m)));
    on("pxNB", "click", ajuster((im, m) => noir_blanc(im, m)));
    on("pxSeuil", "click", ajuster((im, m) => seuil(im, val("pxSeuilV"), m)));
    on("pxFlou", "click", ajuster((im, m) => flou(im, val("pxFlouR"), m)));
    on("pxVersVecteur", "click", garde(versVecteur));
    on("pxTuileOK", "click", () => VL.executer(op_pixelart, { tuile: { w: Math.round(val("pxTuileW")), h: Math.round(val("pxTuileH")) } }));
    const symChange = () => VL.executer(op_pixelart, { symetrie: { h: $("#pxSymH").checked, v: $("#pxSymV").checked } });
    on("pxSymH", "change", symChange); on("pxSymV", "change", symChange);
    on("pxPalExtraire", "click", () => VL.executer(op_pixelart, { palette: palette_extraire(t, Math.round(val("pxPalN"))) }));
    on("pxQuantifier", "click", ajuster((im) => quantifier(im, etat.doc.pixelart.palette)));
    hote.querySelectorAll(".px-pastille").forEach((b) => b.addEventListener("click", () => { etat.px.couleur = b.dataset.couleur; rendrePanneau(); }));
    on("pxPixeliser", "click", garde(async () => {
      const tuile = (etat.doc.pixelart && etat.doc.pixelart.tuile) || { w: Math.round(val("pxTuileW")) };
      etat.px.tampon = pixeliser(t, tuile.w);
      await commettre({ w: etat.px.tampon.w, h: etat.px.tampon.h });
    }));
    on("pxPixeliserVec", "click", garde(pixeliserSelection));
    on("pxIso", "change", (ev) => { losange = null; VL.executer(op_pixelart, { iso: ev.target.checked ? true : null }); VL.rendreOverlay(); });
    on("pxRasteriser", "click", garde(rasteriserImage));
    on("pxRaccord", "click", () => {
      const r = (etat.doc.pixelart && etat.doc.pixelart.iso) ? pavage_iso(t) : raccord_3x3(t), cv = $("#pxRaccordCv");
      cv.hidden = false; cv.width = r.img.w; cv.height = r.img.h;
      cv.getContext("2d").putImageData(new ImageData(new Uint8ClampedArray(r.img.data), r.img.w, r.img.h), 0, 0);
      $("#pxScore").textContent = `score ${r.score}`;
    });
    on("pxFeuille", "click", garde(feuille));
    on("pxCadreNouveau", "click", garde(() => nouveauCadre(false)));
    on("pxCadreVide", "click", garde(() => nouveauCadre(true)));
    on("pxCadreSuppr", "click", garde(supprimerCadre));
    on("pxPlay", "click", basculerLecture);
    on("pxLoop", "change", (ev) => { lecture.loop = ev.target.checked; });
    on("pxFps", "change", () => { etat.px.fps = Math.max(1, Math.min(60, Math.round(val("pxFps")))); });
    hote.querySelectorAll(".px-vignette").forEach((cv) => cv.addEventListener("click", () => editer(cv.dataset.id)));
    dessinerVignettes();
    on("pxBande", "click", garde(bandeCadres));
    on("pxTilelab", "click", garde(() => envoyer("tilelab")));
    on("pxSpritelab", "click", garde(() => envoyer("spritelab")));
  }

  /* ── actions composées ── */
  async function deposerNouvelleImage(tampon, rect, calqueId) {
    const png = await pngDe(tampon);
    const r = await fetch(`/api/vector/docs/${encodeURIComponent(etat.docId)}/images`, { method: "POST", headers: { "Content-Type": "image/png" }, body: png });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    cache.set(d.name, tampon);
    return { href: d.name, objet: { type: "image", ...rect, href: d.name, nat: { w: tampon.w, h: tampon.h }, style: {} }, calqueId };
  }
  async function versVecteur() {
    const o = courant(), t = etat.px.tampon;
    const e = extraire(t, etat.px.masque);
    const [x0, y0] = doc_de_pixel(o, e.x, e.y), [x1, y1] = doc_de_pixel(o, e.x + e.w, e.y + e.h);
    const n = await deposerNouvelleImage(e, { x: x0, y: y0, w: x1 - x0, h: y1 - y0 }, etat.calqueActif);
    const id = VL.executer(op_ajouter, n.calqueId, n.objet);
    if (id && VL.vectoriser) { VL.setSelection([id]); VL.vectoriser(id); }
  }
  // la sélection vectorielle → une tuile : compilée dans son cadre, dessinée
  // sur un canevas de la taille de tuile au plus proche voisin, posée à sa place
  async function pixeliserSelection() {
    const b = VL.bboxSelectionDoc();
    if (!b) throw new Error("rien de sélectionné");
    const tuile = (etat.doc.pixelart && etat.doc.pixelart.tuile) || { w: Math.round(val("pxTuileW")), h: Math.round(val("pxTuileH")) };
    const { compilerSVG } = await import("./mod-doc.js");
    const doc = JSON.parse(JSON.stringify(etat.doc));
    const ids = new Set(etat.selection);
    for (const c of doc.calques) c.objets = c.objets.filter((x) => ids.has(x.id));
    delete doc.fond;
    const svg = compilerSVG(doc, { image: VL.imageUrl, cadre: { x: b.x, y: b.y, w: b.w, h: b.h } });
    const bm = await new Promise((res, rej) => {
      const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" })), im = new Image();
      im.onload = () => { URL.revokeObjectURL(url); res(im); }; im.onerror = () => { URL.revokeObjectURL(url); rej(new Error("SVG non décodable")); };
      im.src = url;
    });
    const cv = document.createElement("canvas"); cv.width = Math.ceil(b.w); cv.height = Math.ceil(b.h);
    cv.getContext("2d").drawImage(bm, 0, 0, cv.width, cv.height);
    const d = cv.getContext("2d").getImageData(0, 0, cv.width, cv.height);
    const t = pixeliser({ w: d.width, h: d.height, data: new Uint8ClampedArray(d.data) }, tuile.w);
    const n = await deposerNouvelleImage(t, { x: b.x, y: b.y, w: b.w, h: b.h }, etat.calqueActif);
    const id = VL.executer(op_ajouter, n.calqueId, n.objet);
    if (id) { VL.toast(`tuile ${t.w}×${t.h} posée`); await editer(id); }
  }
  const telecharger = (blob, nom) => { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = nom; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); };
  async function tamponsDe(objets) {
    const out = [];
    for (const o of objets) {
      if (!cache.has(o.href)) cache.set(o.href, await lireTampon(o.href, o.rev));
      out.push({ nom: o.id, img: cache.get(o.href) });
    }
    return out;
  }
  // la feuille prend les images À LA TAILLE DE TUILE du document (sinon
  // celles de la taille de la première) : les autres calques image restent dehors
  async function feuille() {
    let images = etat.doc.calques.flatMap((c) => c.objets.filter((o) => o.type === "image"));
    const tuile = etat.doc.pixelart && etat.doc.pixelart.tuile;
    const ref = tuile || (images[0] && images[0].nat);
    images = images.filter((o) => ref && o.nat.w === ref.w && o.nat.h === ref.h);
    if (!images.length) throw new Error(tuile ? `aucune image à la taille de tuile ${tuile.w}×${tuile.h}` : "aucune image dans le document");
    const f = feuille_tuiles(await tamponsDe(images), Math.round(val("pxCols")));
    const base = `vector_${etat.docId}_feuille`;
    telecharger(await pngDe(f.img), base + ".png");
    telecharger(new Blob([JSON.stringify({ tuile: etat.doc.pixelart && etat.doc.pixelart.tuile, feuille: { w: f.img.w, h: f.img.h }, tuiles: f.index }, null, 2)], { type: "application/json" }), base + ".json");
    VL.toast(`feuille ${f.img.w}×${f.img.h}, ${f.index.length} tuiles — PNG + JSON téléchargés`);
  }
  async function chargerCadres() { try { await tamponsDe(cadres_de(etat.doc)); } catch (e) { VL.toast(e.message, true); } }
  // lot 2 : dupliquer (copie) ou vide (transparent), inséré JUSTE APRÈS le cadre édité
  async function nouveauCadre(vide) {
    const o = courant(), t = etat.px.tampon;
    const cadres = cadres_de(etat.doc), der = cadres[cadres.length - 1];
    const rect = der ? { x: der.x + der.w + 8, y: der.y, w: der.w, h: der.h } : { x: o.x, y: o.y + o.h + 8, w: o.w, h: o.h };
    const data = vide ? new Uint8ClampedArray(t.w * t.h * 4) : new Uint8ClampedArray(t.data);
    const n = await deposerNouvelleImage({ w: t.w, h: t.h, data }, rect, null);
    const id = VL.executer((doc) => {
      let c = doc.calques.find((k) => String(k.nom || "").toLowerCase() === "cadres");
      const cid = c ? c.id : op_calque_ajouter(doc, "cadres");
      if (!c) c = doc.calques.find((k) => k.id === cid);
      if (!der && !c.objets.some((x) => x.id === o.id)) {
        // le premier cadre : l'image éditée devient le cadre 1 (déplacée dans « cadres »)
        for (const k of doc.calques) { const i = k.objets.findIndex((x) => x.id === o.id); if (i >= 0) { c.objets.push(k.objets.splice(i, 1)[0]); break; } }
      }
      const id2 = op_ajouter(doc, cid, n.objet);
      const iCour = c.objets.findIndex((x) => x.id === o.id), iNeuf = c.objets.findIndex((x) => x.id === id2);
      if (iCour >= 0 && iNeuf > iCour + 1) c.objets.splice(iCour + 1, 0, c.objets.splice(iNeuf, 1)[0]);
      return id2;
    });
    if (id) await editer(id);
  }
  async function supprimerCadre() {
    const o = courant(); const cadres = cadres_de(etat.doc), i = cadres.findIndex((c) => c.id === o.id);
    if (i < 0 || cadres.length < 2) throw new Error("supprimer : au moins deux cadres, et un cadre édité");
    const voisin = cadres[i + 1] || cadres[i - 1];
    VL.executer(op_supprimer, [o.id]);
    etat.px.id = null; etat.px.tampon = null; etat.px.masque = null;
    await editer(voisin.id);
  }
  /* ── lot 2 : la ligne de temps — vignettes depuis le cache, lecture dans le panneau ── */
  const lecture = { raf: 0, i: 0, acc: 0, last: 0, playing: false, loop: true };
  function dessinerVignettes() {
    const cadres = cadres_de(etat.doc); if (!cadres.length) return;
    chargerCadres().then(() => {
      hote.querySelectorAll(".px-vignette").forEach((cv) => {
        const c = cadres.find((x) => x.id === cv.dataset.id), t = c && cache.get(c.href); if (!t) return;
        const x = cv.getContext("2d"); x.imageSmoothingEnabled = false; x.clearRect(0, 0, 40, 40);
        const k = Math.min(40 / t.w, 40 / t.h); x.drawImage(canvasDe(t), 0, 0, t.w * k, t.h * k);
      });
      if (lecture.playing) tickLecture();
    });
  }
  function tickLecture() {
    cancelAnimationFrame(lecture.raf);
    const cadres = cadres_de(etat.doc), cv = $("#pxLecture");
    if (!cv || cadres.length < 2) { lecture.playing = false; return; }
    const tick = (ts) => {
      if (!lecture.playing) return;
      if (!lecture.last) lecture.last = ts;
      lecture.acc += ts - lecture.last; lecture.last = ts;
      const step = 1000 / (etat.px.fps || 12);
      while (lecture.acc >= step) { lecture.acc -= step; if (lecture.i + 1 >= cadres.length && !lecture.loop) { lecture.playing = false; break; } lecture.i = (lecture.i + 1) % cadres.length; }
      const t = cache.get(cadres[lecture.i].href);
      if (t) { cv.width = t.w; cv.height = t.h; const x = cv.getContext("2d"); x.imageSmoothingEnabled = false; x.drawImage(canvasDe(t), 0, 0); }
      lecture.raf = requestAnimationFrame(tick);
    };
    lecture.raf = requestAnimationFrame(tick);
  }
  function basculerLecture() {
    lecture.playing = !lecture.playing; lecture.last = 0;
    const b = $("#pxPlay"); if (b) b.textContent = lecture.playing ? "⏸" : "▶";
    if (lecture.playing) chargerCadres().then(tickLecture); else cancelAnimationFrame(lecture.raf);
  }
  VL.pixelLecture = () => lecture;             // la preuve
  async function bandeCadres() {
    const cadres = cadres_de(etat.doc);
    const b = bande((await tamponsDe(cadres)).map((c) => c.img));
    telecharger(await pngDe(b), `vector_${etat.docId}_bande.png`);
    VL.toast(`bande ${b.w}×${b.h} (${cadres.length} cadres) téléchargée`);
  }
  async function envoyer(surface) {
    const o = courant(), t = etat.px.tampon;
    const nom = nom_depot(etat.docId, o.href, surface === "tilelab" ? "tuile" : "sprite");
    const fd = new FormData();
    fd.append("file", new File([await pngDe(t)], nom, { type: "image/png" }));
    const r = await fetch("/api/images/upload", { method: "POST", body: fd });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    VL.toast(`${d.filename} déposé dans la Bibliothèque — ${surface} s'ouvre`);
    window.open(`/${surface}/`, "_blank");
  }

  // lot 2 : « Rastériser cette image » — pixeliser à la largeur cible, palette, tramage ; l'objet garde son rectangle
  async function rasteriserImage() {
    const t = etat.px.tampon; if (!t) throw new Error("éditer d'abord les pixels d'une image");
    const mode = $("#pxRastPal").value, pa = etat.doc.pixelart || {};
    const palette = mode === "doc" ? pa.palette : mode === "extraire" ? palette_extraire(t, Math.round(val("pxPalN")) || 8) : null;
    const r = rasteriser(t, { cible_w: Math.round(val("pxRastW")), palette, dither: $("#pxRastDither").value });
    etat.px.tampon = r; etat.px.masque = null; losange = null;
    await commettre({ w: r.w, h: r.h });
    VL.toast(`rastérisée : ${r.w}×${r.h}${palette ? `, ${palette.length} couleurs` : ""} (annulable : ↶ Annuler pixels)`);
  }
  VL.actions = VL.actions || {};
  VL.actions.pixel = Object.assign(VL.actions.pixel || {}, { rasteriser: garde(rasteriserImage), iso: (on) => VL.executer(op_pixelart, { iso: on ? true : null }) });

  /* ── crochets ── */
  const suivantRendu = VL.surRendu;
  VL.surRendu = () => {
    suivantRendu();
    // l'image éditée (et toutes, en mode pixel-art) se rend au plus proche voisin
    const tous = !!(etat.doc && etat.doc.pixelart && etat.doc.pixelart.tuile);
    document.body.classList.toggle("pixelart", tous);
    if (!tous && etat.px.id) {
      const el = document.querySelector(`#canvasHost [data-objet="${etat.px.id}"] image`);
      if (el) el.style.imageRendering = "pixelated";
    }
    if (etat.px.id && !courant()) { etat.px.id = null; etat.px.tampon = null; etat.px.masque = null; }
    rendrePanneau();
  };
  const suivantSel = VL.surSelection;
  VL.surSelection = () => { suivantSel(); rendrePanneau(); };
  const suivantOutil = VL.surOutil;
  VL.hints = Object.assign(VL.hints || {}, HINTS_PIXEL);
  VL.surOutil = () => { suivantOutil(); if (VL.majStatut) VL.majStatut(); else { const h = $("#hintOutil"); if (h && HINTS_PIXEL[etat.outil]) h.textContent = HINTS_PIXEL[etat.outil]; } };
  const suivantPersona = VL.surPersona;
  VL.surPersona = () => { suivantPersona(); rendrePanneau(); };
  const suivantCharge = VL.surCharge;
  VL.surCharge = () => { suivantCharge(); etat.px.id = null; etat.px.tampon = null; etat.px.masque = null; cache.clear(); };
  // les ACTIONS de sélection raster — appelées par les menus des outils de sélection
  const masqueAction = (fn) => () => { const t = etat.px.tampon; if (!t) { VL.toast("éditer d'abord les pixels d'une image", true); return; }
    let m = fn(t); if (m && !sel_bbox(m, t.w, t.h)) m = null; etat.px.masque = m; VL.rendreOverlay(); rendrePanneau(); };
  VL.actions = VL.actions || {};
  VL.actions.pixel = {
    tout: masqueAction((t) => sel_rect(t.w, t.h, { x: 0, y: 0, w: t.w, h: t.h })), aucune: masqueAction(() => null),
    inverser: masqueAction(() => etat.px.masque && sel_inverser(etat.px.masque)), croitre: masqueAction((t) => etat.px.masque && sel_croitre(etat.px.masque, t.w, t.h, 1)),
    contracter: masqueAction((t) => etat.px.masque && sel_contracter(etat.px.masque, t.w, t.h, 1)), couleur: masqueAction((t) => sel_couleur(t, etat.px.couleur, etat.px.tolerance)),
    peut: () => ({ tampon: !!etat.px.tampon, masque: !!etat.px.masque }),
  };
  VL.pixelEditer = editer;                  // la preuve
  VL.pixelCommettre = garde(commettre);
  rendrePanneau();
}
