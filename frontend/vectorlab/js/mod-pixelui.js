// mod-pixelui.js — le persona PIXEL (lot E) : les outils raster sur un calque
// image du document et le mode pixel-art vers le Tilelab / Spritelab.
// Chaque geste = lecture du PNG en tampon {w, h, data} (une fois, à
// « Éditer les pixels »), opération PURE (mod-pixel / mod-pixelart), PUT du
// PNG au journal du serveur (`.pix<k>.png` ×10), puis `op_image_rev` : le
// JSON porte la révision et (t124) l'EMPREINTE du contenu, que l'URL désigne
// (`?px=`). « Annuler pixels » dépile le journal (D1) ; le Ctrl+Z du document
// remet, lui, le contenu que l'étape nomme (pixels_a_restaurer). Les
// sélections (masques en px natifs) vivent dans la session.
import { T } from "./mod-i18n.js";
import { op_ajouter, op_calque_ajouter, op_image_rev, op_pixelart, op_supprimer, op_image_verrou, op_style } from "./mod-doc.js";
import { pinceau, gomme, seau, sel_rect, sel_lasso, sel_baguette, sel_couleur, sel_croitre, sel_contracter,
         sel_inverser, sel_bbox, masque_calque, niveaux, courbes, hsl, noir_blanc, seuil, flou, cloner,
         extraire } from "./mod-pixel.js";
import { ligne_pixel, rect_pixel, symetrie, palette_extraire, quantifier, pixeliser, raccord_3x3,
         feuille_tuiles, bande, pelure, pelure_double, pixel_parfait, masque_losange, masque_losanges, pavage_iso, rasteriser, DITHERS,
         cellule_et_cible, echantillon_cellule, remplir_depuis_modele, couleurs_utilisees,
         contour_sombre, accentuer, agrandir, miroirs, tuile_sous } from "./mod-pixelart.js";
import { matrice_de, matrice_inverse, matrice_mul } from "./mod-pdf.js";
import { PALETTES } from "../../spritelab/palettes.js";
import { dzi } from "./mod-icones.js";   // lot 4 : les palettes nommées partagées avec Spritelab / Tilelab

const SNS = "http://www.w3.org/2000/svg";
export const OUTILS_PIXEL = [
  { id: "px-pinceau", touche: "b", titre: T("vectorlab.pixel.outil_pinceau") },
  { id: "px-gomme", touche: "e", titre: T("vectorlab.pixel.outil_gomme") },
  { id: "px-seau", touche: "g", titre: T("vectorlab.pixel.outil_seau") },
  { id: "px-crayon", touche: "k", titre: T("vectorlab.pixel.outil_crayon") },
  { id: "px-ligne", touche: "i", titre: T("vectorlab.pixel.outil_ligne") },
  { id: "px-rectpx", touche: "r", titre: T("vectorlab.pixel.outil_rectpx") },
  { id: "px-selrect", touche: "m", titre: T("vectorlab.pixel.outil_selrect") },
  { id: "px-lasso", touche: "l", titre: T("vectorlab.pixel.outil_lasso") },
  { id: "px-baguette", touche: "w", titre: T("vectorlab.pixel.outil_baguette") },
  { id: "px-cloner", touche: "c", titre: T("vectorlab.pixel.outil_cloner") },
];
export const HINTS_PIXEL = {
  "px-pinceau": T("vectorlab.pixel.hint_pinceau"),
  "px-gomme": T("vectorlab.pixel.hint_gomme"),
  "px-seau": T("vectorlab.pixel.hint_seau"),
  "px-crayon": T("vectorlab.pixel.hint_crayon"),
  "px-ligne": T("vectorlab.pixel.hint_ligne"),
  "px-rectpx": T("vectorlab.pixel.hint_rectpx"),
  "px-selrect": T("vectorlab.pixel.hint_selrect"),
  "px-lasso": T("vectorlab.pixel.hint_lasso"),
  "px-baguette": T("vectorlab.pixel.hint_baguette"),
  "px-cloner": T("vectorlab.pixel.hint_cloner"),
};

/* ── pures ── */
// point du document → pixel natif de l'objet image (la fenêtre de rognage
// est étirée sur le rectangle de l'objet ; la rotation est ignorée)
// t124 : une image tournée ou mise à l'échelle porte son transform (rendu par le groupe qui l'enveloppe) ;
// le point du document repasse par la transformation INVERSE avant le rognage — sans quoi le pinceau
// peignait à l'endroit où l'image aurait été sans rotation
const _ap = (m, x, y) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
export function pixel_de_doc(o, dx, dy) {
  const r = o.rognage || { x: 0, y: 0, w: o.nat.w, h: o.nat.h };
  if (o.transform) [dx, dy] = _ap(matrice_inverse(matrice_de(o.transform)), dx, dy);
  return [r.x + (dx - o.x) / o.w * r.w, r.y + (dy - o.y) / o.h * r.h];
}
export function doc_de_pixel(o, px, py) {
  const p = local_de_pixel(o, px, py);
  return o.transform ? _ap(matrice_de(o.transform), ...p) : p;
}
// le point AVANT le transform de l'image : les aides de l'overlay se dessinent droites dans ce repère,
// sous un groupe qui porte ecran_transform
export function local_de_pixel(o, px, py) {
  const r = o.rognage || { x: 0, y: 0, w: o.nat.w, h: o.nat.h };
  return [o.x + (px - r.x) / r.w * o.w, o.y + (py - r.y) / r.h * o.h];
}
// le transform de l'image ramené à l'écran (zoom z, décalage tx,ty) : E·M·E⁻¹, "" sans transform
export function ecran_transform(o, z, tx, ty) {
  if (!o.transform) return "";
  const m = matrice_de(o.transform);
  const e = [z, 0, 0, z, tx, ty], ei = [1 / z, 0, 0, 1 / z, -tx / z, -ty / z];
  const n = matrice_mul(matrice_mul(e, m), ei);
  return `matrix(${n.map((v) => Math.round(v * 1e6) / 1e6).join(" ")})`;
}
// t124 : après un Ctrl+Z / Ctrl+Y du document, les images dont le contenu voulu (px de l'objet, ou l'origine
// connue s'il n'en porte pas) n'est plus celui du serveur. Seules les images retouchées dans la session sont
// connues (serveur : href → empreinte courante) ; un href partagé ne compte qu'une fois.
export function pixels_a_restaurer(doc, serveur, origine) {
  const out = [], vus = new Set();
  const visiter = (objs) => {
    for (const o of objs || []) {
      if (o.type === "groupe") { visiter(o.enfants); continue; }
      if (o.type !== "image" || vus.has(o.href)) continue;
      vus.add(o.href);
      const voulu = o.px || origine.get(o.href), actuel = serveur.get(o.href);
      if (voulu && actuel && voulu !== actuel) out.push({ href: o.href, empreinte: voulu });
    }
  };
  for (const c of doc.calques || []) visiter(c.objets);
  return out;
}
// l'empreinte qui désigne le contenu affiché : celle de l'objet, sinon celle de l'origine connue. Mesuré en
// preuve : revenue à l'origine (plus de px), l'image reprenait l'URL nue, relue par le rendu AVANT que la
// restauration n'aboutisse — le navigateur gardait les pixels retouchés sous cette URL
export const empreinte_affichee = (href, px, origine) => px || origine.get(href);
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
  if (!o || o.type !== "image") throw new Error(T("vectorlab.pixel.err_image_introuvable", { id }));
  o.nat = { w: Math.round(nat.w), h: Math.round(nat.h) };
  delete o.rognage;
}
// les cadres d'animation = les objets image du calque nommé « cadres », dans l'ordre
export function cadres_de(doc) {
  const c = (doc.calques || []).find((k) => String(k.nom || "").toLowerCase() === "cadres");
  return c ? c.objets.filter((o) => o.type === "image") : [];
}
export function paletteHTML(palette, courante) {
  if (!palette || !palette.length) return `<i class="px-note">${T("vectorlab.pixel.palette_vide")}</i>`;
  return palette.map((c) => `<button data-couleur="${c}" class="px-pastille${c === courante ? " actif" : ""}" style="background:${c}" title="${c}"></button>`).join("");
}

/* ── UI ── */
export function initPixelUI(VL) {
  const { $, etat } = VL;
  const stage = $("#stage");
  etat.px = { id: null, href: null, tampon: null, masque: null, rayon: 4, durete: 1, couleur: "#000000",
              tolerance: 16, global: false, grille: true, pelure: false, source: null, occupe: false,
              secondaire: null, forme: "rond", parfait: true, dernier: null, fps: 12,   // lot 2 : gestes du Sprite Editor
              pipetteMode: "moyenne", cibleArt: 16, ramenerSwatches: false };          // lot 3 : le calque modèle
  const cache = new Map();                  // href → tampon (cadres, pelure)
  let geste = null, apercu = null, rafId = 0;

  // les boutons d'outils du persona dans la barre (après ceux du vecteur)
  const nav = $("#outils");
  for (const o of OUTILS_PIXEL) {
    const b = document.createElement("button");
    b.dataset.outil = o.id; b.className = "outil-pixel"; b.title = o.titre;   // l'icône : mod-barreoutils (ICONES)
    b.addEventListener("click", () => VL.setOutil(o.id));
    nav.appendChild(b);
  }

  /* ── tampon ↔ PNG ── */
  const objetImage = (id) => { const t = id && VL.objetDe(id); return t && t.objet.type === "image" ? t.objet : null; };
  const courant = () => objetImage(etat.px.id);
  async function lireTampon(href, rev, px) {
    const r = await fetch(VL.imageUrl(href, rev, px), { cache: "no-store" });
    if (!r.ok) throw new Error(T("vectorlab.pixel.err_image_statut", { href, status: r.status }));
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
  const pngDe = (t) => new Promise((res, rej) => canvasDe(t).toBlob((b) => b ? res(b) : rej(new Error(T("vectorlab.pixel.err_png"))), "image/png"));
  async function editer(id) {
    const o = objetImage(id);
    if (!o) { VL.toast(T("vectorlab.pixel.selectionner_image"), true); return; }
    etat.px.occupe = true;
    try {
      const t = await lireTampon(o.href, o.rev, o.px);
      etat.px.id = o.id; etat.px.href = o.href; etat.px.tampon = t; etat.px.masque = null;
      cache.set(o.href, t);
      VL.toast(T("vectorlab.pixel.charges", { href: o.href, w: t.w, h: t.h }));
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
    // t124 : l'objet sans px montrait l'origine — elle est retenue pour qu'un Ctrl+Z jusqu'à lui la remette
    if (!o.px && d.avant && !origine.has(o.href)) origine.set(o.href, d.avant);
    if (d.empreinte) serveurPx.set(o.href, d.empreinte);
    VL.executer((doc) => {
      if (nat) op_image_nat(doc, o.id, nat);
      op_image_rev(doc, o.id, d.rev, d.empreinte);
    });
    rendrePanneau();
  }
  // t124 : le Ctrl+Z du document rend les pixels — chaque image dont l'étape nomme un autre contenu que celui
  // du serveur est restaurée (journalisée : « Annuler pixels » reste cohérent), puis le tampon édité recharge
  const serveurPx = new Map(), origine = new Map();
  const imageUrlBase = VL.imageUrl;
  VL.imageUrl = (href, rev, px) => imageUrlBase(href, rev, empreinte_affichee(href, px, origine));
  let restauration = Promise.resolve();
  const suivantHisto = VL.surHistorique;
  VL.surHistorique = () => {
    suivantHisto();
    restauration = restauration.then(async () => {
      for (const { href, empreinte } of pixels_a_restaurer(etat.doc, serveurPx, origine)) {
        const r = await fetch(`/api/vector/docs/${encodeURIComponent(etat.docId)}/images/${encodeURIComponent(href)}/restaurer`,
          { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ empreinte }) });
        if (!r.ok) { VL.toast(T("vectorlab.pixel.restauration_ancienne", { href }), true); serveurPx.delete(href); continue; }
        serveurPx.set(href, empreinte);
        cache.delete(href);
        if (etat.px.href === href && etat.px.id) {
          const o = courant();
          if (o) { etat.px.tampon = await lireTampon(href, o.rev, o.px); cache.set(href, etat.px.tampon); etat.px.masque = null; losange = null; }
        }
      }
      rendrePanneau(); VL.rendreOverlay();
    }).catch((e) => VL.toast(e.message, true));
  };
  let losange = null;                        // lot 2 : le masque iso pavé, mémorisé par taille
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
    const t = await lireTampon(o.href, d.rev || 0, d.empreinte);
    etat.px.tampon = t; cache.set(o.href, t); losange = null;
    if (d.empreinte) serveurPx.set(o.href, d.empreinte);
    // lot 2 : la taille native SUIT l'image revenue (une rastérisation annulée rendait un nat faux → clics décalés, mesuré)
    VL.executer((doc) => { if (o.nat.w !== t.w || o.nat.h !== t.h) op_image_nat(doc, o.id, { w: t.w, h: t.h }); op_image_rev(doc, o.id, d.rev, d.empreinte); });
    VL.toast(T("vectorlab.pixel.annules", { rev: d.rev }));
    rendrePanneau();
  }

  /* ── gestes (capture : les outils du vecteur ne voient rien) ── */
  const estPixel = () => etat.persona === "pixel" && String(etat.outil).startsWith("px-");
  const pixelDe = (o, ev) => { const [dx, dy] = VL.docPt(ev.clientX, ev.clientY); return pixel_de_doc(o, dx, dy); };
  const sym = () => (etat.doc.pixelart && etat.doc.pixelart.symetrie) || { h: false, v: false };
  // t125 : `miroirs` (pur) — H/V sur l'image, diagonales ⟋ ⟍ sur la tuile iso, images REGROUPÉES
  const miroir = (pts, entier) => {
    const t = etat.px.tampon, pa = etat.doc.pixelart || {};
    return miroirs(pts, entier, t.w, t.h, sym(), pa.iso ? (pa.tuile || { w: 0, h: 0 }) : null);
  };
  // lot 2 : en tuile iso, la peinture est BORNÉE au losange quand aucune sélection n'est posée
  const masqueEffectif = () => {
    if (etat.px.masque) return etat.px.masque;
    const t = etat.px.tampon; if (!t || !(etat.doc.pixelart && etat.doc.pixelart.iso)) return undefined;
    const tu = etat.doc.pixelart.tuile || { w: 0, h: 0 };
    if (!losange || losange.w !== t.w || losange.h !== t.h || losange.tw !== tu.w || losange.th !== tu.h) losange = { w: t.w, h: t.h, tw: tu.w, th: tu.h, m: masque_losanges(t.w, t.h, tu.w, tu.h) };   // le losange de CHAQUE tuile
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
      if (!id) { VL.toast(T("vectorlab.pixel.cliquer_image"), true); return; }
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
      // lot 3 : sur le calque pixel du modèle, la pipette lit LA CELLULE DU MODÈLE (exacte / moyenne / dominante)
      const pa = etat.doc.pixelart || {};
      if (pa.modele && o.id === pa.calque && objetImage(pa.modele.id)) {
        garde(async () => {
          const M = (await tamponsDe([objetImage(pa.modele.id)]))[0].img, c = pa.modele.cellule;
          const hex = echantillon_cellule(M, { x: x * c, y: y * c, w: c, h: c }, etat.px.pipetteMode || "moyenne");
          if (!hex) { VL.toast(T("vectorlab.pixel.cellule_transparente")); return; }
          if (droit) { ajouterSwatch(hex); VL.toast(T("vectorlab.pixel.swatch_ajoute", { hex })); }
          else { etat.px.couleur = hex; VL.toast(T("vectorlab.pixel.couleur_modele", { mode: ({ exact: T("vectorlab.pixel.mode_exact"), moyenne: T("vectorlab.pixel.mode_moyenne"), dominante: T("vectorlab.pixel.mode_dominante") }[etat.px.pipetteMode] || etat.px.pipetteMode), hex })); rendrePanneau(); VL.surRendu(); }
        })();
        return;
      }
      const k = (y * t.w + x) * 4;
      if (t.data[k + 3] === 0) { VL.toast(T("vectorlab.pixel.pixel_transparent")); return; }
      const hex = "#" + [t.data[k], t.data[k + 1], t.data[k + 2]].map((v) => v.toString(16).padStart(2, "0").toUpperCase()).join("");
      if (droit) etat.px.secondaire = hex; else etat.px.couleur = hex;
      VL.toast(T(droit ? "vectorlab.pixel.toast_secondaire" : "vectorlab.pixel.toast_couleur", { hex })); rendrePanneau(); VL.surRendu();
      return;
    }
    const couleur = droit ? etat.px.secondaire : etat.px.couleur, efface = droit && etat.px.secondaire === null;
    if (outil === "px-cloner" && ev.altKey) { etat.px.source = [px - 0.5, py - 0.5]; VL.toast(T("vectorlab.pixel.source_clonage", { x: Math.floor(px), y: Math.floor(py) })); return; }
    if (outil === "px-cloner" && !etat.px.source) { VL.toast(T("vectorlab.pixel.fixer_source"), true); return; }
    if (outil === "px-seau") {
      const x = Math.floor(px), y = Math.floor(py);
      if (x < 0 || y < 0 || x >= t.w || y >= t.h) return;
      if (efface) { VL.toast(T("vectorlab.pixel.seau_rien"), true); return; }
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
    if (!geste) {                                  // t125 : le pixel SURVOLÉ — le raccord mesure la tuile sous le curseur
      if (etat.doc && etat.persona === "pixel") { const o = courant(); if (o) etat.px.survol = pixelDe(o, ev).map(Math.floor); }
      return;
    }
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
    const ecr = pts.map(([px, py]) => VL.ecranPt(...local_de_pixel(o, px, py)));
    const te = ecran_transform(o, etat.zoom, etat.tx, etat.ty);
    const el = document.createElementNS(SNS, geste.type === "px-lasso" ? "polyline" : "rect");
    if (geste.type === "px-lasso") el.setAttribute("points", ecr.map((p) => p.join(",")).join(" "));
    else {
      const [a, b] = ecr;
      el.setAttribute("x", Math.min(a[0], b[0])); el.setAttribute("y", Math.min(a[1], b[1]));
      el.setAttribute("width", Math.abs(b[0] - a[0])); el.setAttribute("height", Math.abs(b[1] - a[1]));
    }
    el.setAttribute("fill", "none"); el.setAttribute("stroke", "#ffd166"); el.setAttribute("stroke-dasharray", "4 3");
    if (te) el.setAttribute("transform", te);       // t124 : le tracé tourne avec l'image
    tmp.appendChild(el);
  }

  /* ── overlay : cadre de l'image éditée, masque, grille pixel, pelure, aperçu ── */
  const suivantOverlay = VL.surOverlay;
  VL.surOverlay = (ov) => {
    suivantOverlay(ov);
    if (etat.persona === "pixel") grilleModele(ov);      // lot 3 : l'aperçu de la grille sur le modèle
    const o = courant();
    if (!o || etat.persona !== "pixel") return;
    const t = etat.px.tampon;
    const [sx, sy] = VL.ecranPt(o.x, o.y), sw = o.w * etat.zoom, sh = o.h * etat.zoom;
    const r = o.rognage || { x: 0, y: 0, w: o.nat.w, h: o.nat.h };
    // t124 : tout ce qui suit se dessine droit puis tourne avec l'image (son transform ramené à l'écran)
    const te = ecran_transform(o, etat.zoom, etat.tx, etat.ty);
    const hoteImg = te ? (() => { const g = document.createElementNS(SNS, "g"); g.setAttribute("transform", te); g.setAttribute("class", "px-tourne"); ov.appendChild(g); return g; })() : ov;
    const el = (nom, attrs, hote = hoteImg) => { const e = document.createElementNS(SNS, nom); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); hote.appendChild(e); return e; };
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
        const [ax, ay] = VL.ecranPt(...local_de_pixel(o, b.x, b.y)), [bx, by] = VL.ecranPt(...local_de_pixel(o, b.x + b.w, b.y + b.h));
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
      if (etat.px.secondaire === null) { VL.toast(T("vectorlab.pixel.rien_a_echanger")); return; }
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
      ${(() => {
        const m = modeleObjet(), cp = calquePixelObjet();
        if (!m) return `<details open><summary class="px-tete">${T("vectorlab.pixel.modele")}</summary><div class="ap-ligne"><button id="pxDesigner" ${sel ? "" : "disabled"} title="${T("vectorlab.pixel.designer_titre")}">${T("vectorlab.pixel.designer")}</button></div>
          <div class="ap-ligne"><span></span><i class="px-note">${T("vectorlab.pixel.modele_note")}</i></div></details>`;
        const cc = cellule_et_cible(m.nat, { cellule: pa.modele.cellule });
        const P = pairesDe(), iAct = P.findIndex((q) => q.modele === m.id);
        return `<details open><summary class="px-tete">${T("vectorlab.pixel.modele")} · ${m.href}</summary>
          ${P.length > 1 ? `<div class="ap-ligne"><span>${T("vectorlab.pixel.paire")}</span><select id="pxPaire" title="${T("vectorlab.pixel.paire_titre")}">${P.map((q, i) => { const om = objetImage(q.modele); return `<option value="${i}"${i === iAct ? " selected" : ""}>${om ? om.href : q.modele} · ${T("vectorlab.pixel.cellule_n", { n: q.cellule })}${q.calque ? " · " + T("vectorlab.pixel.calque_court") : ""}</option>`; }).join("")}</select></div>` : ""}
          <div class="ap-ligne"><span></span><button id="pxDesignerAutre" ${sel && sel.id !== m.id && !P.some((q) => q.modele === sel.id) ? "" : "disabled"} title="${T("vectorlab.pixel.designer_autre_titre")}">${dzi("dz-action-ajouter", 16)}${T("vectorlab.pixel.designer_autre")}</button></div>
          <div class="ap-ligne"><span>${T("vectorlab.pixel.cellule")}</span>${num("pxCellule", cc.cellule, `min="1" title="${T("vectorlab.pixel.cellule_titre")}"`)}<span style="width:auto">px →</span>${num("pxCible", cc.cible_w, `min="1" title="${T("vectorlab.pixel.cible_titre")}"`)}<span style="width:auto">× ${cc.cible_h}</span></div>
          <div class="ap-ligne"><span></span>${[4, 8, 16, 32, 64].map((v) => `<button class="pxCelluleRapide" data-c="${v}" ${v === cc.cellule ? 'class="actif"' : ""}>${v}</button>`).join("")}</div>
          <div class="ap-ligne"><label title="${T("vectorlab.pixel.tuile_art_titre")}"><vl-bascule id="pxTuileArtOn"></vl-bascule> ${T("vectorlab.pixel.tuile_egal")}</label>${num("pxTuileArt", p.cibleArt, 'min="1" style="width:52px"')}<button id="pxCreerCalque" ${cp ? "disabled" : ""} title="${T("vectorlab.pixel.creer_calque_titre", { w: cc.cible_w, h: cc.cible_h })}">${T("vectorlab.pixel.creer_calque", { w: cc.cible_w, h: cc.cible_h })}</button></div>
          <div class="ap-ligne"><button id="pxRemplir" ${o && cp && o.id === cp.id ? "" : "disabled"} title="${T("vectorlab.pixel.remplir_titre")}">${T("vectorlab.pixel.remplir")}</button>
            <label title="${T("vectorlab.pixel.ramener_titre")}"><vl-bascule id="pxRamener"${p.ramenerSwatches ? " checked" : ""}></vl-bascule> → swatches</label><button id="pxModeleRetirer" title="${T("vectorlab.pixel.retirer_titre")}">${T("vectorlab.pixel.retirer")}</button></div>
        </details>`; })()}
      <div class="ap-ligne"><span>Image</span>${o ? `<i class="img-src" id="pxNom" title="${o.href}">${o.href} · ${t.w}×${t.h}${o.rev ? ` · ${T("vectorlab.pixel.rev_n", { n: o.rev })}` : ""}</i>`
        : `<button id="pxEditer" ${sel ? "" : "disabled"} title="${T("vectorlab.pixel.editer_titre")}">${T("vectorlab.pixel.editer")}</button>`}</div>
      ${o ? `<div class="ap-ligne"><span></span><button id="pxAnnuler" title="${T("vectorlab.pixel.annuler_titre")}">${dzi("dz-action-annuler", 16)}${T("vectorlab.pixel.annuler")}</button><button id="pxFermer" title="${T("vectorlab.pixel.terminer_titre")}">${T("vectorlab.pixel.terminer")}</button></div>
      <div class="ap-ligne"><span>Export</span><select id="pxExpK" title="${T("vectorlab.pixel.export_k_titre")}"><option value="1">×1</option><option value="2">×2</option><option value="4" selected>×4</option><option value="8">×8</option><option value="16">×16</option></select><button id="pxExpPng" title="${T("vectorlab.pixel.export_png_titre")}">${dzi("dz-action-telecharger", 16)}PNG ×N</button></div>` : ""}
      <div class="ap-ligne"><span>${T("vectorlab.pixel.couleur")}</span><vl-curseur-couleur id="pxCouleur" value="${p.couleur}"></vl-curseur-couleur>
        <span style="width:auto" title="${T("vectorlab.pixel.secondaire_titre")}">${T("vectorlab.pixel.secondaire_court")}</span><vl-curseur-couleur id="pxSecondaire" value="${p.secondaire || "#FFFFFF"}"${p.secondaire ? "" : ' class="vide"'}></vl-curseur-couleur><button id="pxSecVider" title="${T("vectorlab.pixel.sec_vider_titre")}" aria-label="${T("vectorlab.pixel.sec_vider_aria")}">${dzi("dz-edit-sans-couleur", 16)}</button>
        <span style="width:auto">${T("vectorlab.pixel.rayon")}</span><vl-curseur id="pxRayon" min="0.5" max="64" step="0.5" value="${p.rayon}" title="${T("vectorlab.pixel.rayon_titre")}"></vl-curseur></div>
      <div class="ap-ligne"><span>${T("vectorlab.pixel.durete")}</span><vl-curseur id="pxDurete" min="0" max="1" step="0.05" value="${p.durete}" title="${T("vectorlab.pixel.durete_titre")}"></vl-curseur></div>
      <div class="ap-ligne"><span>${T("vectorlab.pixel.tolerance")}</span><vl-curseur id="pxTol" min="0" max="255" step="1" value="${p.tolerance}" title="${T("vectorlab.pixel.tolerance_titre")}"></vl-curseur>
        <label title="${T("vectorlab.pixel.global_titre")}"><vl-bascule id="pxGlobal"${p.global ? " checked" : ""}></vl-bascule> global</label></div>
      <details open><summary class="px-tete">${T("vectorlab.pixel.selection")}${bb ? ` · ${bb.w}×${bb.h}` : " · " + T("vectorlab.pixel.aucune")}</summary>
        <div class="ap-ligne"><span></span><i class="px-note">${T("vectorlab.pixel.selection_note")}</i></div>
        <div class="vl-rangee"><button id="pxMasqueCalque" ${p.masque ? "" : "disabled"} title="${T("vectorlab.pixel.masque_calque_titre")}">${T("vectorlab.pixel.masque_calque")}</button>
          <button id="pxVersVecteur" ${p.masque ? "" : "disabled"} title="${T("vectorlab.pixel.vers_vecteur_titre")}">${dzi("dz-edit-vectoriser", 16)}${T("vectorlab.pixel.vers_vecteur")}</button></div>
      </details>
      <details><summary class="px-tete">${T("vectorlab.pixel.ajustements")}</summary>
        <div class="ap-ligne"><span>${T("vectorlab.pixel.niveaux")}</span>${num("pxNoir", 0, `min="0" max="254" title="${T("vectorlab.pixel.point_noir")}"`)}${num("pxBlanc", 255, `min="1" max="255" title="${T("vectorlab.pixel.point_blanc")}"`)}${num("pxGamma", 1, 'min="0.1" max="5" step="0.1" title="Gamma"')}<button id="pxNiveaux" ${t ? "" : "disabled"}>OK</button></div>
        <div class="ap-ligne"><span>${T("vectorlab.pixel.courbe")}</span><span style="width:auto">128 →</span>${num("pxCourbe", 128, `min="0" max="255" title="${T("vectorlab.pixel.courbe_titre")}"`)}<button id="pxCourbes" ${t ? "" : "disabled"}>OK</button></div>
        <div class="ap-ligne"><span>HSL</span>${num("pxH", 0, `min="-180" max="180" title="${T("vectorlab.pixel.teinte")}"`)}${num("pxS", 0, `min="-100" max="100" title="${T("vectorlab.pixel.saturation")}"`)}${num("pxL", 0, `min="-100" max="100" title="${T("vectorlab.pixel.luminosite")}"`)}<button id="pxHsl" ${t ? "" : "disabled"}>OK</button></div>
        <div class="ap-ligne"><button id="pxNB" ${t ? "" : "disabled"}>${T("vectorlab.pixel.noir_blanc")}</button><span style="width:auto">${T("vectorlab.pixel.seuil")}</span>${num("pxSeuilV", 128, 'min="0" max="255"')}<button id="pxSeuil" ${t ? "" : "disabled"}>OK</button></div>
        <div class="ap-ligne"><span>${T("vectorlab.pixel.contour")}</span><vl-curseur id="pxContourE" min="1" max="4" step="1" value="1" title="${T("vectorlab.pixel.contour_e_titre")}"></vl-curseur><button id="pxContour" ${t ? "" : "disabled"} title="${T("vectorlab.pixel.contour_titre")}">${T("vectorlab.pixel.contour_sombre")}</button></div>
        <div class="ap-ligne"><span>${T("vectorlab.pixel.accent")}</span><vl-curseur id="pxAccF" min="0.1" max="2" step="0.1" value="1" title="${T("vectorlab.pixel.accent_f_titre")}"></vl-curseur><button id="pxAcc" ${t ? "" : "disabled"} title="${T("vectorlab.pixel.accent_titre")}">${T("vectorlab.pixel.accentuer")}</button></div>
        <div class="ap-ligne"><span>${T("vectorlab.pixel.flou")}</span><vl-curseur id="pxFlouR" min="1" max="50" step="1" value="2" title="${T("vectorlab.pixel.flou_titre")}"></vl-curseur><button id="pxFlou" ${t ? "" : "disabled"}>OK</button></div>
      </details>
      <details ${pa.tuile ? "open" : ""}><summary class="px-tete">Pixel-art</summary>
        <div class="ap-ligne"><span>${T("vectorlab.pixel.tuile")}</span>${num("pxTuileW", tuile.w, `min="1" title="${T("vectorlab.pixel.tuile_w_titre")}"`)}<span style="width:auto">×</span>${num("pxTuileH", tuile.h, 'min="1"')}
          <button id="pxTuileOK" title="${T("vectorlab.pixel.tuile_ok_titre")}"${pa.tuile ? ` aria-label="${T("vectorlab.pixel.tuile_reposer")}"` : ""}>${pa.tuile ? dzi("dz-action-recalculer", 16) : "OK"}</button></div>
        <div class="ap-ligne"><label><vl-bascule id="pxGrille"${p.grille ? " checked" : ""}></vl-bascule> ${T("vectorlab.pixel.grille")}</label>
          <label title="${T("vectorlab.pixel.iso_titre")}"><vl-bascule id="pxIso"${pa.iso ? " checked" : ""}></vl-bascule> iso 2:1</label>
          <label title="${T("vectorlab.pixel.sym_titre")}"><vl-bascule id="pxSymH"${s.h ? " checked" : ""}></vl-bascule> sym. H</label>
          <label><vl-bascule id="pxSymV"${s.v ? " checked" : ""}></vl-bascule> V</label>
          <label title="${pa.iso ? T("vectorlab.pixel.sym_d1_titre") : T("vectorlab.pixel.sym_d_inactif")}"><vl-bascule id="pxSymD1"${s.d1 ? " checked" : ""}${pa.iso ? "" : " disabled"}></vl-bascule> ${dzi("dz-outil-px-symetrie", 16)}</label>
          <label title="${pa.iso ? T("vectorlab.pixel.sym_d2_titre") : T("vectorlab.pixel.sym_d_inactif")}"><vl-bascule id="pxSymD2"${s.d2 ? " checked" : ""}${pa.iso ? "" : " disabled"}></vl-bascule> ${dzi("dz-outil-px-symetrie", 16, "dzi-miroir")}</label></div>
        <div class="ap-ligne"><span>Palette</span>${num("pxPalN", (pa.palette || []).length || 8, `min="2" max="64" title="${T("vectorlab.pixel.pal_n_titre")}"`)}<span style="width:auto">${T("vectorlab.pixel.couleurs")}</span></div>
        <div class="vl-rangee"><button id="pxPalExtraire" ${t ? "" : "disabled"} title="${T("vectorlab.pixel.extraire_titre")}">${T("vectorlab.pixel.extraire")}</button>
          <button id="pxQuantifier" ${t && pa.palette ? "" : "disabled"} title="${T("vectorlab.pixel.quantifier_titre")}">${T("vectorlab.pixel.quantifier")}</button></div>
        <div class="ap-ligne"><span>${T("vectorlab.pixel.prereglage")}</span><select id="pxPreset" title="${T("vectorlab.pixel.preset_titre")}"><option value="">${T("vectorlab.pixel.choisir")}</option>${PALETTES.map((q) => `<option value="${q.id}">${q.nom} (${q.couleurs.length})</option>`).join("")}</select></div>
        <div class="ap-ligne"><span>Swatches</span><button id="pxSwatchPlus" title="${T("vectorlab.pixel.swatch_plus_titre")}">${T("vectorlab.pixel.swatch_plus")}</button><button id="pxPalModele" ${modeleObjet() ? "" : "disabled"} title="${T("vectorlab.pixel.pal_modele_titre")}">${T("vectorlab.pixel.pal_modele")}</button></div>
        <div class="px-palette" id="pxPalette" title="${T("vectorlab.pixel.palette_titre")}">${paletteHTML(pa.palette || [], p.couleur)}</div>
        ${t ? `<div class="ap-ligne"><span>${T("vectorlab.pixel.utilisees")}</span><button id="pxUtiliseesVers" title="${T("vectorlab.pixel.utilisees_titre")}">${dzi("dz-action-ajouter", 16)}swatches</button></div>
        <div class="px-palette px-utilisees">${t.w * t.h <= 1000000 ? couleurs_utilisees(t, 64).map((c) => `<button data-couleur="${c}" class="px-pastille${c === p.couleur ? " actif" : ""}" style="background:${c}" title="${c}"></button>`).join("") || `<i class="px-note">${T("vectorlab.pixel.calque_vide")}</i>` : `<i class="px-note">${T("vectorlab.pixel.image_trop_grande")}</i>`}</div>` : ""}
        <div class="ap-ligne"><span>${T("vectorlab.pixel.rasteriser")}</span>${num("pxRastW", (pa.tuile && pa.tuile.w) || 64, `min="1" max="4096" title="${T("vectorlab.pixel.rast_w_titre")}"`)}
          <select id="pxRastPal" title="${T("vectorlab.pixel.rast_pal_titre")}"><option value="aucune">${T("vectorlab.pixel.rast_libre")}</option><option value="doc"${pa.palette ? "" : " disabled"}>${T("vectorlab.pixel.rast_doc")}</option><option value="extraire">${T("vectorlab.pixel.rast_extraire")}</option></select>
          <select id="pxRastDither" title="${T("vectorlab.pixel.tramage")}"><option value="aucun">${T("vectorlab.pixel.sans_tramage")}</option><option value="ordonne">${T("vectorlab.pixel.ordonne")}</option><option value="floyd">Floyd-Steinberg</option></select></div>
        <div class="ap-ligne"><span></span><button id="pxRasteriser" ${t ? "" : "disabled"} title="${T("vectorlab.pixel.rasteriser_titre")}">${T("vectorlab.pixel.rasteriser_btn")}</button></div>
        <div class="vl-rangee"><button id="pxPixeliser" ${t ? "" : "disabled"} title="${T("vectorlab.pixel.pixeliser_titre")}">${T("vectorlab.pixel.pixeliser")}</button>
          <button id="pxPixeliserVec" ${etat.selection.length && !o ? "" : "disabled"} title="${T("vectorlab.pixel.pixeliser_sel_titre")}">${T("vectorlab.pixel.pixeliser_sel")}</button></div>
        <div class="vl-rangee"><button id="pxRaccord" ${t ? "" : "disabled"} title="${pa.iso ? T("vectorlab.pixel.raccord_iso_titre") : T("vectorlab.pixel.raccord_titre")}">${T("vectorlab.pixel.raccord")} ${pa.iso ? "iso ×9" : "3×3"}</button><span id="pxScore" style="width:auto"></span></div>
        <canvas id="pxRaccordCv" class="px-raccord" hidden></canvas>
        <div class="ap-ligne"><span>${T("vectorlab.pixel.feuille")}</span>${num("pxCols", 8, `min="1" title="${T("vectorlab.pixel.cols_titre")}"`)}
          <button id="pxFeuille" title="${T("vectorlab.pixel.feuille_titre")}">PNG + JSON</button></div>
      </details>
      <details open><summary class="px-tete">${T("vectorlab.pixel.timeline", { n: cadres.length })}</summary>
        <div id="pxTimeline" class="px-timeline">${cadres.length ? cadres.map((c, i) => `<canvas class="px-vignette${o && c.id === o.id ? " actif" : ""}" data-id="${c.id}" width="40" height="40" title="${T("vectorlab.pixel.cadre_titre", { n: i + 1 })}"></canvas>`).join("") : `<i class="px-note">${T("vectorlab.pixel.aucun_cadre")}</i>`}</div>
        <div class="ap-ligne"><button id="pxPlay" ${cadres.length > 1 ? "" : "disabled"} title="${T("vectorlab.pixel.lecture")}" aria-label="${T("vectorlab.pixel.lecture")}">${dzi(lecture.playing ? "dz-media-pause" : "dz-media-lecture", 16)}</button>
          <label title="${T("vectorlab.pixel.boucler_titre")}"><vl-bascule id="pxLoop"${lecture.loop ? " checked" : ""}></vl-bascule> ${T("vectorlab.pixel.boucle")}</label><span style="width:auto">FPS</span><vl-curseur id="pxFps" min="1" max="60" step="1" value="${p.fps}" title="${T("vectorlab.pixel.fps_titre")}"></vl-curseur>
          <canvas id="pxLecture" class="px-lecture" width="48" height="48"></canvas></div>
        <div class="vl-rangee"><button id="pxCadreNouveau" ${o ? "" : "disabled"} title="${T("vectorlab.pixel.dupliquer_titre")}">${dzi("dz-action-dupliquer", 16)}<span class="dzi-lib">${T("vectorlab.pixel.dupliquer")}</span></button>
          <button id="pxCadreVide" ${o ? "" : "disabled"} title="${T("vectorlab.pixel.vide_titre")}">${dzi("dz-action-ajouter", 16)}<span class="dzi-lib">${T("vectorlab.pixel.vide")}</span></button>
          <button id="pxCadreSuppr" ${o && cadres.length > 1 && cadres.some((c) => c.id === o.id) ? "" : "disabled"} title="${T("vectorlab.pixel.supprimer_cadre_titre")}" aria-label="${T("vectorlab.pixel.supprimer_cadre")}">${dzi("dz-action-supprimer", 16)}</button></div>
        <div class="ap-ligne"><label title="${T("vectorlab.pixel.pelure_titre")}"><vl-bascule id="pxPelure"${p.pelure ? " checked" : ""}></vl-bascule> ${T("vectorlab.pixel.pelure")}</label>
          <button id="pxBande" ${cadres.length ? "" : "disabled"} title="${T("vectorlab.pixel.bande_titre")}">${T("vectorlab.pixel.bande")}</button></div>
        <div class="vl-rangee"><button id="pxTilelab" ${t ? "" : "disabled"} title="${T("vectorlab.pixel.tilelab_titre")}">${dzi("dz-cat-tuiles", 16)}Tilelab</button>
          <button id="pxSpritelab" ${t ? "" : "disabled"} title="${T("vectorlab.pixel.spritelab_titre")}">${dzi("dz-cat-sprites", 16)}Spritelab</button></div>
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
    // lot 5 : retouches qui RENDENT un tampon neuf (purs) — commit, annulable
    const remplacer = (fn) => garde(async () => { etat.px.tampon = fn(etat.px.tampon); await commettre(); });
    on("pxContour", "click", remplacer((im) => contour_sombre(im, etat.px.secondaire || "#101010", Math.round(val("pxContourE")) || 1)));
    on("pxAcc", "click", remplacer((im) => accentuer(im, val("pxAccF") || 1)));
    on("pxExpPng", "click", garde(async () => { const k = Math.round(val("pxExpK")) || 1, im = agrandir(etat.px.tampon, k); const o2 = courant(); telecharger(await pngDe(im), `vector_${etat.docId}_${String(o2.href).replace(/\.png$/i, "")}_x${k}.png`); VL.toast(`PNG ×${k} : ${im.w}×${im.h}`); }));
    on("pxVersVecteur", "click", garde(versVecteur));
    on("pxTuileOK", "click", () => VL.executer(op_pixelart, { tuile: { w: Math.round(val("pxTuileW")), h: Math.round(val("pxTuileH")) } }));
    const symChange = () => VL.executer(op_pixelart, { symetrie: { h: $("#pxSymH").checked, v: $("#pxSymV").checked,
      d1: !!($("#pxSymD1") && $("#pxSymD1").checked), d2: !!($("#pxSymD2") && $("#pxSymD2").checked) } });
    on("pxSymH", "change", symChange); on("pxSymV", "change", symChange); on("pxSymD1", "change", symChange); on("pxSymD2", "change", symChange);
    on("pxPalExtraire", "click", () => VL.executer(op_pixelart, { palette: palette_extraire(t, Math.round(val("pxPalN"))) }));
    on("pxQuantifier", "click", ajuster((im) => quantifier(im, etat.doc.pixelart.palette)));
    hote.querySelectorAll(".px-pastille").forEach((b) => {
      b.addEventListener("click", (ev) => { if (ev.altKey && b.closest("#pxPalette")) { VL.executer(op_pixelart, { palette: (etat.doc.pixelart.palette || []).filter((c) => c !== b.dataset.couleur) }); return; } etat.px.couleur = b.dataset.couleur; rendrePanneau(); });
      b.addEventListener("contextmenu", (ev) => { ev.preventDefault(); etat.px.secondaire = b.dataset.couleur; rendrePanneau(); });
    });
    on("pxSwatchPlus", "click", () => ajouterSwatch(etat.px.couleur));
    on("pxPreset", "change", (ev) => { const q = PALETTES.find((x) => x.id === ev.target.value); if (q) VL.executer(op_pixelart, { palette: q.couleurs.slice() }); });
    on("pxPalModele", "click", garde(paletteDepuisModele));
    on("pxUtiliseesVers", "click", () => { const pal = new Set((etat.doc.pixelart || {}).palette || []); for (const c of couleurs_utilisees(t, 64)) pal.add(c); VL.executer(op_pixelart, { palette: [...pal] }); });
    on("pxDesigner", "click", () => { try { designerModele(etat.selection[0]); } catch (e) { VL.toast(e.message, true); } });
    on("pxDesignerAutre", "click", () => { try { designerModele(etat.selection[0]); } catch (e) { VL.toast(e.message, true); } });
    on("pxCellule", "change", () => reglerCellule("cellule", val("pxCellule")));
    on("pxCible", "change", () => reglerCellule("cible", val("pxCible")));
    hote.querySelectorAll(".pxCelluleRapide").forEach((b) => b.addEventListener("click", () => reglerCellule("cellule", +b.dataset.c)));
    on("pxTuileArt", "change", () => { etat.px.cibleArt = Math.max(1, Math.round(val("pxTuileArt"))); });
    on("pxRamener", "change", (ev) => { etat.px.ramenerSwatches = ev.target.checked; });
    on("pxCreerCalque", "click", garde(creerCalquePixel));
    on("pxRemplir", "click", garde(remplirDepuisModele));
    on("pxModeleRetirer", "click", () => { const pa = etat.doc.pixelart || {}; const P = pairesDe().filter((q) => q.modele !== (pa.modele && pa.modele.id)); const n = P[0]; VL.executer(op_pixelart, { paires: P.length ? P : null, modele: n ? { id: n.modele, cellule: n.cellule } : null, calque: n ? (n.calque || null) : null }); VL.rendreOverlay(); });
    on("pxPaire", "change", (ev) => activerPaire(+ev.target.value));
    on("pxPixeliser", "click", garde(async () => {
      const tuile = (etat.doc.pixelart && etat.doc.pixelart.tuile) || { w: Math.round(val("pxTuileW")) };
      etat.px.tampon = pixeliser(t, tuile.w);
      await commettre({ w: etat.px.tampon.w, h: etat.px.tampon.h });
    }));
    on("pxPixeliserVec", "click", garde(pixeliserSelection));
    on("pxIso", "change", (ev) => { losange = null; VL.executer(op_pixelart, { iso: ev.target.checked ? true : null }); VL.rendreOverlay(); });
    on("pxRasteriser", "click", garde(rasteriserImage));
    on("pxRaccord", "click", () => {
      // t125 : la tuile SOUS LE CURSEUR (dernier pixel survolé), plus l'image entière comme une seule tuile
      const pa = etat.doc.pixelart || {}, tu = pa.tuile || { w: 0, h: 0 }, sv = etat.px.survol || [];
      const ts = tuile_sous(t, sv[0], sv[1], tu.w, tu.h);
      const r = pa.iso ? pavage_iso(ts.img) : raccord_3x3(ts.img), cv = $("#pxRaccordCv");
      cv.hidden = false; cv.width = r.img.w; cv.height = r.img.h;
      cv.getContext("2d").putImageData(new ImageData(new Uint8ClampedArray(r.img.data), r.img.w, r.img.h), 0, 0);
      $("#pxScore").textContent = T("vectorlab.pixel.score", { score: r.score }) + (ts.tx === null ? "" : T("vectorlab.pixel.score_tuile", { x: ts.tx + 1, y: ts.ty + 1 }));
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
    // t124 : l'extrait garde le transform de l'image — posé droit dans son repère, il tourne avec elle
    const [x0, y0] = local_de_pixel(o, e.x, e.y), [x1, y1] = local_de_pixel(o, e.x + e.w, e.y + e.h);
    const n = await deposerNouvelleImage(e, { x: x0, y: y0, w: x1 - x0, h: y1 - y0 }, etat.calqueActif);
    if (o.transform) n.objet.transform = o.transform;
    const id = VL.executer(op_ajouter, n.calqueId, n.objet);
    if (id && VL.vectoriser) { VL.setSelection([id]); VL.vectoriser(id); }
  }
  // la sélection vectorielle → une tuile : compilée dans son cadre, dessinée
  // sur un canevas de la taille de tuile au plus proche voisin, posée à sa place
  async function pixeliserSelection() {
    const b = VL.bboxSelectionDoc();
    if (!b) throw new Error(T("vectorlab.pixel.rien_selectionne"));
    const tuile = (etat.doc.pixelart && etat.doc.pixelart.tuile) || { w: Math.round(val("pxTuileW")), h: Math.round(val("pxTuileH")) };
    const { compilerSVG } = await import("./mod-doc.js");
    const doc = JSON.parse(JSON.stringify(etat.doc));
    const ids = new Set(etat.selection);
    for (const c of doc.calques) c.objets = c.objets.filter((x) => ids.has(x.id));
    delete doc.fond;
    const svg = compilerSVG(doc, { image: VL.imageUrl, cadre: { x: b.x, y: b.y, w: b.w, h: b.h } });
    const bm = await new Promise((res, rej) => {
      const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" })), im = new Image();
      im.onload = () => { URL.revokeObjectURL(url); res(im); }; im.onerror = () => { URL.revokeObjectURL(url); rej(new Error(T("vectorlab.pixel.svg_illisible"))); };
      im.src = url;
    });
    const cv = document.createElement("canvas"); cv.width = Math.ceil(b.w); cv.height = Math.ceil(b.h);
    cv.getContext("2d").drawImage(bm, 0, 0, cv.width, cv.height);
    const d = cv.getContext("2d").getImageData(0, 0, cv.width, cv.height);
    const t = pixeliser({ w: d.width, h: d.height, data: new Uint8ClampedArray(d.data) }, tuile.w);
    const n = await deposerNouvelleImage(t, { x: b.x, y: b.y, w: b.w, h: b.h }, etat.calqueActif);
    const id = VL.executer(op_ajouter, n.calqueId, n.objet);
    if (id) { VL.toast(T("vectorlab.pixel.tuile_posee", { w: t.w, h: t.h })); await editer(id); }
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
    if (!images.length) throw new Error(tuile ? T("vectorlab.pixel.feuille_aucune_taille", { w: tuile.w, h: tuile.h }) : T("vectorlab.pixel.feuille_aucune"));
    const f = feuille_tuiles(await tamponsDe(images), Math.round(val("pxCols")));
    const base = `vector_${etat.docId}_feuille`;
    telecharger(await pngDe(f.img), base + ".png");
    telecharger(new Blob([JSON.stringify({ tuile: etat.doc.pixelart && etat.doc.pixelart.tuile, feuille: { w: f.img.w, h: f.img.h }, tuiles: f.index }, null, 2)], { type: "application/json" }), base + ".json");
    VL.toast(T("vectorlab.pixel.feuille_ok", { w: f.img.w, h: f.img.h, n: f.index.length }));
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
    if (i < 0 || cadres.length < 2) throw new Error(T("vectorlab.pixel.supprimer_cadre_err"));
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
    const b = $("#pxPlay"); if (b) b.innerHTML = dzi(lecture.playing ? "dz-media-pause" : "dz-media-lecture", 16);
    if (lecture.playing) chargerCadres().then(tickLecture); else cancelAnimationFrame(lecture.raf);
  }
  VL.pixelLecture = () => lecture;             // la preuve
  async function bandeCadres() {
    const cadres = cadres_de(etat.doc);
    const b = bande((await tamponsDe(cadres)).map((c) => c.img));
    telecharger(await pngDe(b), `vector_${etat.docId}_bande.png`);
    VL.toast(T("vectorlab.pixel.bande_ok", { w: b.w, h: b.h, n: cadres.length }));
  }
  async function envoyer(surface) {
    const o = courant(), t = etat.px.tampon;
    const nom = nom_depot(etat.docId, o.href, surface === "tilelab" ? "tuile" : "sprite");
    const fd = new FormData();
    fd.append("file", new File([await pngDe(t)], nom, { type: "image/png" }));
    const r = await fetch("/api/images/upload", { method: "POST", body: fd });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    VL.toast(T("vectorlab.pixel.depose", { nom: d.filename, surface }));
    window.open(`/${surface}/`, "_blank");
  }

  // lot 2 : « Rastériser cette image » — pixeliser à la largeur cible, palette, tramage ; l'objet garde son rectangle
  async function rasteriserImage() {
    const t = etat.px.tampon; if (!t) throw new Error(T("vectorlab.pixel.editer_dabord"));
    const mode = $("#pxRastPal").value, pa = etat.doc.pixelart || {};
    const palette = mode === "doc" ? pa.palette : mode === "extraire" ? palette_extraire(t, Math.round(val("pxPalN")) || 8) : null;
    const r = rasteriser(t, { cible_w: Math.round(val("pxRastW")), palette, dither: $("#pxRastDither").value });
    etat.px.tampon = r; etat.px.masque = null; losange = null;
    await commettre({ w: r.w, h: r.h });
    VL.toast(T(palette ? "vectorlab.pixel.rasterisee_pal" : "vectorlab.pixel.rasterisee", { w: r.w, h: r.h, n: palette ? palette.length : 0 }));
  }
  VL.actions = VL.actions || {};
  VL.actions.pixel = Object.assign(VL.actions.pixel || {}, { rasteriser: garde(rasteriserImage), iso: (on) => VL.executer(op_pixelart, { iso: on ? true : null }) });

  /* ── lot 3 : le calque modèle — grille en aperçu, calque pixel, remplissage, swatches ── */
  const modeleObjet = () => { const pa = etat.doc && etat.doc.pixelart; return pa && pa.modele ? objetImage(pa.modele.id) : null; };
  // lot 5 : plusieurs modèles — les paires {modele, cellule, calque}, la paire ACTIVE = modele / calque
  const pairesDe = () => { const pa = (etat.doc && etat.doc.pixelart) || {}; if (Array.isArray(pa.paires)) return pa.paires.map((q) => ({ ...q })); return pa.modele ? [{ modele: pa.modele.id, cellule: pa.modele.cellule, calque: pa.calque || null }] : []; };
  function activerPaire(i) {
    const P = pairesDe(), q = P[i]; if (!q) return;
    VL.executer(op_pixelart, { paires: P, modele: { id: q.modele, cellule: q.cellule }, calque: q.calque || null });
    VL.rendreOverlay();
  }
  const calquePixelObjet = () => { const pa = etat.doc && etat.doc.pixelart; return pa && pa.calque ? objetImage(pa.calque) : null; };
  function grilleModele(ov) {
    const pa = etat.doc.pixelart || {}, m = modeleObjet();
    if (!m || calquePixelObjet()) return;
    const c = pa.modele.cellule, r = m.rognage || { x: 0, y: 0, w: m.nat.w, h: m.nat.h };
    // lot 5 : en coordonnées DOCUMENT sous la vue et sous la ROTATION du modèle (la même chaîne transform que le rendu)
    const vue = document.createElementNS(SNS, "g"); vue.setAttribute("class", "px-grille-modele"); vue.setAttribute("transform", `translate(${etat.tx} ${etat.ty}) scale(${etat.zoom})`); ov.appendChild(vue);
    const g = document.createElementNS(SNS, "g"); if (m.transform) g.setAttribute("transform", m.transform); vue.appendChild(g);
    const el = (nom, attrs) => { const e = document.createElementNS(SNS, nom); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); g.appendChild(e); return e; };
    const z = 1 / etat.zoom, kx = m.w / r.w, ky = m.h / r.h;
    el("rect", { x: m.x, y: m.y, width: m.w, height: m.h, fill: "none", stroke: "#ffd166", "stroke-width": 1.5 * z, "stroke-dasharray": `${6 * z} ${3 * z}` });
    if ((r.w / c) * (r.h / c) > 65536) return;
    let d = "";
    for (let i = 0; i <= r.w; i += c) d += `M${m.x + i * kx} ${m.y}v${m.h}`;
    for (let j = 0; j <= r.h; j += c) d += `M${m.x} ${m.y + j * ky}h${m.w}`;
    el("path", { d, stroke: "rgba(255,209,102,.6)", "stroke-width": z, fill: "none" });
  }
  function designerModele(id) {
    const o = objetImage(id); if (!o) throw new Error(T("vectorlab.pixel.designer_err"));
    const cc = cellule_et_cible(o.nat, { cellule: 16 });
    // le style AVANT le verrou : une image verrouillée n'est plus une cible de commande (mesuré)
    const P = pairesDe(); let q = P.find((x) => x.modele === id);
    if (!q) { q = { modele: id, cellule: cc.cellule, calque: null }; P.push(q); }
    VL.executer((doc) => { op_pixelart(doc, { paires: P, modele: { id, cellule: q.cellule }, calque: q.calque || null }); if (!(o.style && o.style.opacite < 1)) op_style(doc, [id], { opacite: 0.6 }); if (!o.verrou) op_image_verrou(doc, id, true); });
    VL.rendreOverlay();
  }
  function reglerCellule(champ, valeur) {
    const pa = etat.doc.pixelart || {}, m = modeleObjet(); if (!m) return;
    const cc = cellule_et_cible(m.nat, champ === "cellule" ? { cellule: valeur } : { cible: valeur });
    if (cc.cellule !== pa.modele.cellule) { const P = pairesDe(); const q = P.find((x) => x.modele === m.id); if (q) q.cellule = cc.cellule; VL.executer(op_pixelart, { paires: P, modele: { id: m.id, cellule: cc.cellule } }); }
    else rendrePanneau();
    VL.rendreOverlay();
  }
  async function creerCalquePixel() {
    const pa = etat.doc.pixelart || {}, m = modeleObjet(); if (!m) throw new Error(T("vectorlab.pixel.designer_dabord"));
    if (calquePixelObjet()) throw new Error(T("vectorlab.pixel.calque_existe"));
    const cc = cellule_et_cible(m.nat, { cellule: pa.modele.cellule });
    const n = await deposerNouvelleImage({ w: cc.cible_w, h: cc.cible_h, data: new Uint8ClampedArray(cc.cible_w * cc.cible_h * 4) }, { x: m.x, y: m.y, w: m.w, h: m.h }, null);
    const tuileArt = $("#pxTuileArtOn") && $("#pxTuileArtOn").checked ? Math.max(1, Math.round(val("pxTuileArt"))) : 0;
    const id = VL.executer((doc) => {
      let c = doc.calques.find((k) => String(k.nom || "").toLowerCase() === "pixel");
      if (!c) { const cid = op_calque_ajouter(doc, "pixel"); c = doc.calques.find((k) => k.id === cid); }
      const id2 = op_ajouter(doc, c.id, n.objet);
      const P = pairesDe(); const q = P.find((x) => x.modele === m.id); if (q) q.calque = id2;
      op_pixelart(doc, { calque: id2, paires: P, ...(tuileArt ? { tuile: { w: tuileArt, h: tuileArt } } : {}) });
      return id2;
    });
    if (id) { await editer(id); VL.toast(T("vectorlab.pixel.calque_pose", { w: cc.cible_w, h: cc.cible_h })); }
  }
  async function remplirDepuisModele() {
    const pa = etat.doc.pixelart || {}, m = modeleObjet(), o = courant();
    if (!m || !o || o.id !== pa.calque) throw new Error(T("vectorlab.pixel.editer_calque_modele"));
    const M = (await tamponsDe([m]))[0].img, t = etat.px.tampon;
    const pal = etat.px.ramenerSwatches && pa.palette && pa.palette.length ? pa.palette : null;
    etat.px.tampon = remplir_depuis_modele(M, t.w, t.h, pa.modele.cellule, etat.px.pipetteMode || "moyenne", pal);
    await commettre();
    VL.toast(T(pal ? "vectorlab.pixel.rempli_swatches" : "vectorlab.pixel.rempli", { mode: ({ exact: T("vectorlab.pixel.mode_exact"), moyenne: T("vectorlab.pixel.mode_moyenne"), dominante: T("vectorlab.pixel.mode_dominante") }[etat.px.pipetteMode] || etat.px.pipetteMode) }));
  }
  function ajouterSwatch(hex) {
    const pa = etat.doc.pixelart || {}, pal = pa.palette || [];
    if (pal.includes(hex)) return;
    VL.executer(op_pixelart, { palette: [...pal, hex] });
  }
  async function paletteDepuisModele() {
    const m = modeleObjet(); if (!m) throw new Error(T("vectorlab.pixel.designer_dabord"));
    const M = (await tamponsDe([m]))[0].img;
    VL.executer(op_pixelart, { palette: palette_extraire(M, Math.round(val("pxPalN")) || 8) });
  }
  VL.pixelTampon = async (id) => { const o = objetImage(id); if (!o) throw new Error(T("vectorlab.pixel.pas_image")); return (await tamponsDe([o]))[0].img; };   // l'impression 3D (lot 3)
  VL.actions.pixel = Object.assign(VL.actions.pixel || {}, { designerModele, creerCalquePixel: garde(creerCalquePixel), remplirDepuisModele: garde(remplirDepuisModele), paletteDepuisModele: garde(paletteDepuisModele) });

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
  VL.surCharge = () => { suivantCharge(); etat.px.id = null; etat.px.tampon = null; etat.px.masque = null; cache.clear(); serveurPx.clear(); origine.clear(); };   // t124 : un href (img1.png) se répète d'un document à l'autre
  // les ACTIONS de sélection raster — appelées par les menus des outils de sélection
  const masqueAction = (fn) => () => { const t = etat.px.tampon; if (!t) { VL.toast(T("vectorlab.pixel.editer_dabord"), true); return; }
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
