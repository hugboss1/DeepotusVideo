// mod-doc.js — LE modèle-document du Vectorlab : validation + compilation
// JSON -> SVG. PUR (aucune lecture du DOM, aucun état) : la même fonction
// sert l'écran, l'export et le banc qa/ node. Le JSON est la vérité ; le
// SVG n'en est qu'une projection.

import { grille_normaliser, hex_centre, hex_d, hex_depuis_point, grille_cellules }
  from "./mod-grille.js";
import { zoom_pour, echantillon_moyen, paliers_bornes, palier } from "./mod-geo.js";
import { forme_d, forme_params_valider } from "./mod-formes.js";
import { effets_valider, filtre_svg, MODES_FUSION, motif_valider, motif_svg, conique_svg } from "./mod-effets.js";
import { couper_lignes, cadre_tspans, mesure_approx } from "./mod-texteplus.js";

const escAttr = (v) => String(v)
  .replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");

/* ── lot C (D3) : la fiche de terrains — défauts fusionnés avec doc.terrains ── */
export const TERRAINS_DEFAUT = Object.freeze({
  mer:      Object.freeze({ nom: "Mer",      couleur: "#2B5F9E", hauteur_mm: 0, motif: "" }),
  plaine:   Object.freeze({ nom: "Plaine",   couleur: "#7FB069", hauteur_mm: 2, motif: "" }),
  foret:    Object.freeze({ nom: "Forêt",    couleur: "#3F7D3A", hauteur_mm: 3, motif: "" }),
  colline:  Object.freeze({ nom: "Colline",  couleur: "#B08D57", hauteur_mm: 5, motif: "" }),
  montagne: Object.freeze({ nom: "Montagne", couleur: "#8A8A8A", hauteur_mm: 8, motif: "" }),
});
const _CLE_TERRAIN = /^[a-z0-9_-]+$/;
function _validerTerrain(k, f) {
  if (!_CLE_TERRAIN.test(k)) throw new Error(`terrain: clé « ${k} » ([a-z0-9_-])`);
  if (!f || typeof f !== "object") throw new Error(`terrain ${k}: fiche requise`);
  if (f.couleur !== undefined && !/^#[0-9A-Fa-f]{3,8}$/.test(f.couleur)) {
    throw new Error(`terrain ${k}: couleur hex`);
  }
  if (f.hauteur_mm !== undefined && !(+f.hauteur_mm >= 0)) {
    throw new Error(`terrain ${k}: hauteur_mm ≥ 0`);
  }
}
export function terrains_de(doc) {
  const out = {};
  for (const [k, f] of Object.entries(TERRAINS_DEFAUT)) out[k] = { ...f };
  for (const [k, f] of Object.entries(doc.terrains || {})) {
    out[k] = { ...(out[k] || { nom: k, couleur: "#888888", hauteur_mm: 0, motif: "" }), ...f };
  }
  return out;
}
export function op_terrain_definir(doc, cle, fiche) {
  _validerTerrain(cle, fiche);
  if (!doc.terrains) doc.terrains = {};
  doc.terrains[cle] = { ...(doc.terrains[cle] || {}), ...fiche };
}
export function op_terrain_supprimer(doc, cle) {
  if (!doc.terrains || !doc.terrains[cle]) {
    throw new Error(`terrain ${cle}: pas de surcharge à retirer`);
  }
  delete doc.terrains[cle];
  if (!Object.keys(doc.terrains).length) delete doc.terrains;
}
function _validerCadre(c, ou) {
  if (!c || typeof c !== "object" || !(c.w > 0) || !(c.h > 0)
      || !Number.isFinite(+c.x) || !Number.isFinite(+c.y)) {
    throw new Error(`${ou}: cadre {x, y, w > 0, h > 0}`);
  }
}
const _GRILLE_TUILE_DEFAUT = Object.freeze({ type: "hex", pas: 32, sous: 1, orientation: "pointe",
                                             origine: [0, 0], echelle: [1, 1] });
function _grilleHex(doc) {
  return (doc.grille && doc.grille.type === "hex") ? doc.grille : _GRILLE_TUILE_DEFAUT;
}

/* ── lot A (D1/D2) : l'objet `image` — href RELATIF (nom du PNG stocké à
   côté du JSON du document, jamais de base64) ou URL absolue ; `nat` =
   taille native ; `rognage` = fenêtre en px NATIFS ; `verrou` = ignoré
   par toutes les commandes de sélection. */
function _validerRognage(r, nat, ou) {
  if (!r || typeof r !== "object") throw new Error(`${ou}: rognage {x,y,w,h}`);
  const { x, y, w, h } = r;
  if (!(x >= 0) || !(y >= 0) || !(w > 0) || !(h > 0)
      || x + w > nat.w + 1e-6 || y + h > nat.h + 1e-6) {
    throw new Error(`${ou}: rognage hors de l'image native`);
  }
}
function _validerObjets(objs, ou) {
  for (const o of objs) {
    if (o.type === "image") {
      if (typeof o.href !== "string" || !o.href) throw new Error(`image ${o.id}: href requis`);
      if (!o.nat || !(o.nat.w > 0) || !(o.nat.h > 0)) throw new Error(`image ${o.id}: nat {w,h} positif requis`);
      if (!(o.w > 0) || !(o.h > 0)) throw new Error(`image ${o.id}: taille positive requise`);
      if (o.rognage !== undefined) _validerRognage(o.rognage, o.nat, `image ${o.id}`);
      if (o.rev !== undefined && !(Number.isInteger(o.rev) && o.rev >= 0)) throw new Error(`image ${o.id}: rev entier ≥ 0`);
    }
    if (o.type === "forme") {
      if (!(o.r > 0)) throw new Error(`forme ${o.id}: rayon > 0 requis`);
      forme_params_valider(o.forme, o.params);
    }
    if (o.type === "tuile") {
      if (!Number.isInteger(o.q) || !Number.isInteger(o.r)) {
        throw new Error(`tuile ${o.id}: q et r entiers requis`);
      }
      if (typeof o.terrain !== "string" || !o.terrain) throw new Error(`tuile ${o.id}: terrain requis`);
      if (o.hauteur_mm !== undefined && !(o.hauteur_mm >= 0)) {
        throw new Error(`tuile ${o.id}: hauteur_mm ≥ 0`);
      }
    }
    if (o.type === "cadre") {
      if (!(o.w > 0) || !(o.h > 0)) throw new Error(`cadre ${o.id}: taille positive requise`);
      if (typeof o.contenu !== "string") throw new Error(`cadre ${o.id}: contenu texte requis`);
    }
    if (o.type === "textechemin") {
      if (typeof o.d !== "string" || !o.d) throw new Error(`textechemin ${o.id}: d requis`);
      if (typeof o.contenu !== "string") throw new Error(`textechemin ${o.id}: contenu texte requis`);
      if (o.decalage !== undefined && !(o.decalage >= 0 && o.decalage <= 100)) throw new Error(`textechemin ${o.id}: decalage 0..100`);
    }
    if (o.type === "instance") {
      if (typeof o.symbole !== "string" || !o.symbole) throw new Error(`instance ${o.id}: symbole requis`);
      if (!Number.isFinite(+o.x) || !Number.isFinite(+o.y)) throw new Error(`instance ${o.id}: x, y requis`);
      if (!((o.sx === undefined || o.sx > 0) && (o.sy === undefined || o.sy > 0))) throw new Error(`instance ${o.id}: sx, sy > 0`);
    }
    if (o.type === "groupe") {
      _validerObjets(o.enfants || [], ou);
      if (o.clip !== undefined && !(o.enfants || []).some((e) => e.id === o.clip)) {
        throw new Error(`groupe ${o.id}: clip doit désigner un enfant`);
      }
    }
    if (o.style) _validerStyleAvance(o.style, `${o.type} ${o.id}`);
  }
}

/* ── lot F : l'apparence avancée d'un style — effets (liste ordonnée),
   fusion (16 modes SVG), contours multiples, masque de transparence
   (« grad:<id> ») ; couleurs « glob:<nom> » résolues à la compilation. */
const _NOM_GLOBAL = /^[A-Za-z0-9_-]+$/;
const _HEX6 = /^#[0-9A-Fa-f]{6}$/;
function _validerStyleAvance(s, ou) {
  if (s.effets !== undefined) { try { effets_valider(s.effets); } catch (e) { throw new Error(`${ou}: ${e.message}`); } }
  if (s.fusion !== undefined && !MODES_FUSION.includes(s.fusion)) throw new Error(`${ou}: mode de fusion inconnu ${s.fusion}`);
  if (s.contours !== undefined) {
    if (!Array.isArray(s.contours)) throw new Error(`${ou}: contours = liste`);
    for (const c of s.contours) {
      if (!c || !(c.epaisseur > 0)) throw new Error(`${ou}: contour {couleur, epaisseur > 0}`);
      if (!(_HEX6.test(String(c.couleur)) || /^glob:/.test(String(c.couleur)))) throw new Error(`${ou}: couleur de contour invalide`);
    }
  }
  if (s.masque !== undefined && !/^grad:.+/.test(String(s.masque))) throw new Error(`${ou}: masque = grad:<id>`);
}
function _validerRefsMasques(doc) {
  const degs = doc.degrades || {};
  const visiter = (objs) => {
    for (const o of objs || []) {
      const m = o.style && o.style.masque;
      if (m && !degs[m.slice(5)]) throw new Error(`${o.id}: masque ${m} inconnu`);
      if (o.type === "groupe") visiter(o.enfants);
    }
  };
  for (const c of doc.calques) visiter(c.objets);
}

export function parserDoc(doc) {
  if (!doc || typeof doc !== "object") throw new Error("document: objet requis");
  if (!doc.v) throw new Error("document: champ v requis");
  if (!doc.taille || !(doc.taille.w > 0) || !(doc.taille.h > 0)) {
    throw new Error("document: taille {w,h} positive requise");
  }
  if (!Array.isArray(doc.calques)) throw new Error("document: calques[] requis");
  for (const c of doc.calques) {
    if (!c.id) throw new Error("calque sans id");
    if (!Array.isArray(c.objets)) throw new Error(`calque ${c.id}: objets[] requis`);
  }
  for (const c of doc.calques) _validerObjets(c.objets, c.id);
  // éditeur complet (E1) : deux champs OPTIONNELS rétro-compatibles —
  // l'unité d'affichage (le document reste en px) et la palette sauvée
  if (doc.unites !== undefined) {
    const u = doc.unites;
    if (!u || typeof u !== "object"
        || !["px", "mm", "cm", "in"].includes(u.affichage)
        || !(+u.dpi > 0)) {
      throw new Error("document: unites {affichage px|mm|cm|in, dpi>0}");
    }
  }
  if (doc.palette !== undefined && !Array.isArray(doc.palette)) {
    throw new Error("document: palette = liste de couleurs");
  }
  if (doc.reperes !== undefined) _validerReperes(doc.reperes, doc.taille);
  // lot C : grille du document, fiche de terrains, planches
  if (doc.grille !== undefined) grille_normaliser(doc.grille);
  if (doc.terrains !== undefined) {
    if (!doc.terrains || typeof doc.terrains !== "object" || Array.isArray(doc.terrains)) {
      throw new Error("document: terrains = {cle: fiche}");
    }
    for (const [k, f] of Object.entries(doc.terrains)) _validerTerrain(k, f);
  }
  if (doc.planches !== undefined) {
    if (!Array.isArray(doc.planches)) throw new Error("document: planches = liste");
    for (const p of doc.planches) {
      if (!p || !p.id) throw new Error("planche sans id");
      _validerCadre(p, `planche ${p.id}`);
    }
  }
  if (doc.geo !== undefined) _validerGeo(doc.geo);
  if (doc.pixelart !== undefined) _validerPixelart(doc.pixelart);
  // lot F : motifs, couleurs globales, masques de transparence
  if (doc.motifs !== undefined) {
    if (!doc.motifs || typeof doc.motifs !== "object" || Array.isArray(doc.motifs)) throw new Error("document: motifs = {id: motif}");
    for (const [id, m] of Object.entries(doc.motifs)) { try { motif_valider(m); } catch (e) { throw new Error(`motif ${id}: ${e.message}`); } }
  }
  if (doc.couleursGlobales !== undefined) {
    if (!doc.couleursGlobales || typeof doc.couleursGlobales !== "object" || Array.isArray(doc.couleursGlobales)) throw new Error("document: couleursGlobales = {nom: hex}");
    for (const [n, h] of Object.entries(doc.couleursGlobales)) {
      if (!_NOM_GLOBAL.test(n) || !_HEX6.test(String(h))) throw new Error(`couleur globale ${n}: nom [A-Za-z0-9_-] et #RRGGBB`);
    }
  }
  _validerRefsMasques(doc);
  if (doc.styles !== undefined) {
    if (!doc.styles || typeof doc.styles !== "object" || Array.isArray(doc.styles)) throw new Error("document: styles = {nom: style}");
    for (const [n, st] of Object.entries(doc.styles)) {
      if (!_NOM_GLOBAL.test(n) || !st || typeof st !== "object") throw new Error(`style ${n}: nom [A-Za-z0-9_-] et objet`);
      _validerStyleAvance(st, `style ${n}`);
    }
  }
  if (doc.symboles !== undefined) {
    if (!doc.symboles || typeof doc.symboles !== "object" || Array.isArray(doc.symboles)) throw new Error("document: symboles = {id: symbole}");
    for (const [id, sy] of Object.entries(doc.symboles)) {
      if (!sy || !Array.isArray(sy.objets)) throw new Error(`symbole ${id}: objets[] requis`);
      _validerCadre(sy.bbox, `symbole ${id}`);
      _validerObjets(sy.objets, `symbole ${id}`);
    }
  }
  _visiterObjets(doc, (o) => {
    if (o.type === "instance" && !(doc.symboles && doc.symboles[o.symbole])) throw new Error(`instance ${o.id}: symbole ${o.symbole} inconnu`);
  });
  return doc;
}

// lot F : « glob:<nom> » → hex de doc.couleursGlobales (repli none)
function _couleur(v, ctx) {
  if (typeof v === "string" && v.startsWith("glob:")) {
    const h = ctx.globales && ctx.globales[v.slice(5)];
    return h || "none";
  }
  return v;
}
function styleAttrs(s = {}, ctx = {}) {
  let fond = s.fond === undefined ? "none" : _couleur(s.fond, ctx);
  if (typeof fond === "string" && fond.startsWith("grad:")) {
    const gid = fond.slice(5);
    fond = (ctx.degrades && ctx.degrades[gid]) ? `url(#${gid})` : "none";
  } else if (typeof fond === "string" && fond.startsWith("motif:")) {
    const mid = fond.slice(6);
    fond = (ctx.motifs && ctx.motifs[mid]) ? `url(#${mid})` : "none";
  }
  let out = ` fill="${escAttr(fond)}"`;
  const contour = _couleur(s.contour, ctx);
  if (contour && contour !== "none") {
    out += ` stroke="${escAttr(contour)}"`
        + ` stroke-width="${Number(s.epaisseur || 1)}"`
        + ` stroke-linejoin="${escAttr(s.joint || "round")}"`
        + ` stroke-linecap="round"`;
    if (s.pointilles) out += ` stroke-dasharray="${escAttr(s.pointilles)}"`;
  }
  if (s.opacite !== undefined && Number(s.opacite) !== 1) {
    out += ` opacity="${Number(s.opacite)}"`;
  }
  if (s.regle) out += ` fill-rule="${escAttr(s.regle)}"`;
  if (s.fusion && s.fusion !== "normal") out += ` style="mix-blend-mode:${escAttr(s.fusion)}"`;
  if (s.masque && ctx.degrades && ctx.degrades[s.masque.slice(5)]) out += ` mask="url(#m_${escAttr(s.masque.slice(5))})"`;
  return out;
}
const _CLES_AVANCEES = ["effets", "fusion", "contours", "masque"];
function _styleNu(s) {
  const o = { ...(s || {}) };
  for (const k of _CLES_AVANCEES) delete o[k];
  return o;
}

const _escTexte = (v) => String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
function _fonteAttrs(s) {
  let attrs = "";
  if (s.police) attrs += ` font-family="${escAttr(s.police)}"`;
  attrs += ` font-size="${Number(s.corps || 16)}"`;
  if (s.graisse) attrs += ` font-weight="${escAttr(s.graisse)}"`;
  if (s.interlettrage) attrs += ` letter-spacing="${Number(s.interlettrage)}"`;
  return attrs;
}
function compilerObjet(o, ctx = {}) {
  const s0 = o.style || {};
  // lot F : effets et contours multiples enveloppent l'objet dans <g data-objet>
  // (patron de l'image) ; les copies sont émises SANS id — un seul élément
  // porte l'id, le hit-testing du cœur reste inchangé
  if (!ctx.sansId && o.type !== "groupe" && o.type !== "image" && ((s0.effets && s0.effets.length) || (s0.contours && s0.contours.length))) {
    const enfantCtx = { ...ctx, sansId: true };
    const nu = { ...o, style: _styleNu(s0) };
    const copies = (s0.contours || []).slice().sort((a, b) => b.epaisseur - a.epaisseur).map((c, i) =>
      compilerObjet({ ...o, style: { fond: "none", contour: c.couleur, epaisseur: c.epaisseur, pointilles: c.pointilles, opacite: c.opacite, joint: s0.joint } }, enfantCtx)
        .replace(/^<(\w+) /, `<$1 data-contour="${i}" `));
    const filtre = s0.effets && s0.effets.length ? ` filter="url(#fx_${escAttr(o.id)})"` : "";
    const fusion = s0.fusion && s0.fusion !== "normal" ? ` style="mix-blend-mode:${escAttr(s0.fusion)}"` : "";
    const masque = s0.masque && ctx.degrades && ctx.degrades[s0.masque.slice(5)] ? ` mask="url(#m_${escAttr(s0.masque.slice(5))})"` : "";
    const corps = compilerObjet(nu, enfantCtx);
    return `<g data-objet="${escAttr(o.id)}"${filtre}${fusion}${masque}>` + copies.join("") + corps + `</g>`;
  }
  const t = ctx.sansId ? "" : ` data-objet="${escAttr(o.id)}"`;
  const tr = o.transform ? ` transform="${escAttr(o.transform)}"` : "";
  const st = styleAttrs(o.style, ctx);
  switch (o.type) {
    case "rect":
      return `<rect${t} x="${+o.x}" y="${+o.y}" width="${+o.w}"`
           + ` height="${+o.h}"${o.rx ? ` rx="${+o.rx}"` : ""}${st}${tr}/>`;
    case "ellipse":
      return `<ellipse${t} cx="${+o.cx}" cy="${+o.cy}" rx="${+o.rx}"`
           + ` ry="${+o.ry}"${st}${tr}/>`;
    case "path":
      return `<path${t} d="${escAttr(o.d)}"${st}${tr}/>`;
    case "texte": {
      const s = o.style || {};
      return `<text${t} x="${+o.x}" y="${+o.y}"${_fonteAttrs(s)}${st}${tr}>${_escTexte(o.contenu || "")}</text>`;
    }
    case "cadre": {
      // lot F : cadre de texte — coupe des lignes par la mesure injectée (opts.mesure)
      const s = o.style || {};
      const lignes = couper_lignes(o.contenu || "", o.w - Number(s.retrait || 0), s, ctx.mesure || mesure_approx);
      const r = cadre_tspans(o, lignes, ctx.mesure || mesure_approx);
      const deb = r.deborde ? ` data-deborde="1"` : "";
      return `<text${t}${deb}${_fonteAttrs(s)}${st}${tr}>${r.html}</text>`;
    }
    case "textechemin": {
      // lot F : texte sur chemin — le d est une COPIE, le chemin porteur est invisible
      const s = o.style || {};
      const pid = `tp_${escAttr(o.id)}`;
      return `<g${t}${tr}><path id="${pid}" d="${escAttr(o.d)}" fill="none" stroke="none"/>`
        + `<text${_fonteAttrs(s)}${st}><textPath href="#${pid}" startOffset="${+(o.decalage || 0)}%">${_escTexte(o.contenu || "")}</textPath></text></g>`;
    }
    case "instance": {
      // lot F : une instance est un <use> du symbole (défini une fois dans les defs)
      const sx = o.sx === undefined ? 1 : +o.sx, sy = o.sy === undefined ? 1 : +o.sy;
      const ech = (sx !== 1 || sy !== 1) ? ` scale(${nbc(sx)} ${nbc(sy)})` : "";
      const trI = ` transform="translate(${nbc(o.x)} ${nbc(o.y)})${ech}${o.transform ? " " + escAttr(o.transform) : ""}"`;
      return `<use${t} href="#sym_${escAttr(o.symbole)}"${trI}/>`;
    }
    case "groupe": {
      // lot F : un groupe écrêté porte clip-path (la géométrie du conteneur est dans les defs)
      const clip = o.clip ? ` clip-path="url(#clip_${escAttr(o.id)})"` : "";
      const fx = s0.effets && s0.effets.length ? ` filter="url(#fx_${escAttr(o.id)})"` : "";
      return `<g${t}${clip}${fx}${st}${tr}>`
           + (o.enfants || []).map((e) => compilerObjet(e, ctx)).join("")
           + `</g>`;
    }
    case "forme":
      // lot B (D2) : le d se RECALCULE à chaque compilation depuis les paramètres
      return `<path${t} data-forme="${escAttr(o.forme)}" d="${forme_d(o)}"${st}${tr}/>`;
    case "tuile": {
      // D3 : la forme est DÉRIVÉE de la grille hex du document (sinon hex
      // 32 pointe) ; la couleur vient de la fiche de terrains
      const g = ctx.grille || _GRILLE_TUILE_DEFAUT;
      const [cx, cy] = hex_centre(o.q, o.r, g);
      const fiche = (ctx.terrains || {})[o.terrain];
      const fond = fiche ? fiche.couleur : "#888888";
      const inconnu = fiche ? "" : ` data-terrain-inconnu="1"`;
      const s = { fond, contour: "#1F1512", epaisseur: 1, ...(o.style || {}) };
      return `<path${t} data-q="${+o.q}" data-r="${+o.r}" data-terrain="${escAttr(o.terrain)}"${inconnu}`
        + ` d="${hex_d(cx, cy, g.pas, g.orientation, g.echelle)}"${styleAttrs(s, ctx)}${tr}/>`;
    }
    case "image": {
      const url = (ctx.image || ((h) => h))(o.href, o.rev);
      const nat = o.nat;
      const r = o.rognage || { x: 0, y: 0, w: nat.w, h: nat.h };
      const verrou = o.verrou ? ` data-verrou="1"` : "";
      return `<g${t}${verrou}${st}${tr}>`
        + `<svg x="${+o.x}" y="${+o.y}" width="${+o.w}" height="${+o.h}"`
        + ` viewBox="${+r.x} ${+r.y} ${+r.w} ${+r.h}" preserveAspectRatio="none">`
        + `<image x="0" y="0" width="${+nat.w}" height="${+nat.h}"`
        + ` href="${escAttr(url)}" preserveAspectRatio="none"/>`
        + `</svg></g>`;
    }
    default:
      // un type inconnu ne casse pas le document : il se voit au commentaire
      return `<!-- objet ${escAttr(o.id)}: type inconnu ${escAttr(o.type)} -->`;
  }
}

/* ── chemins (T1.1) : le d de path, parsé, structuré, canonisé ──
   Segments {c:"M"|"L"|"C"|"Q"|"Z", p:[nombres]} en ABSOLU seulement (v1) ;
   lecture tolérante (virgules, implicites SVG), écriture canonique stable
   à l'octet — les opérations de nœuds et les booléens s'appuient dessus. */
const ARITE = { M: 2, L: 2, C: 6, Q: 4, Z: 0 };

// arrondi 2 décimales SANS le piège flottant (1.005 → 1.01, 3.10 → 3.1)
const nbc = (x) => String(Math.round(Number((x * 100).toPrecision(12))) / 100);

export function chemin_parser(d) {
  const src = String(d ?? "").replace(/,/g, " ").trim();
  const jetons = src.match(/[A-Za-z]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?/g) || [];
  const segs = [];
  let i = 0, cmd = null;
  while (i < jetons.length) {
    const t = jetons[i];
    if (/^[A-Za-z]$/.test(t)) {
      if (!(t in ARITE)) {
        if (t.toUpperCase() in ARITE) {
          throw new Error(`chemin: commande relative '${t}' non supportée `
                          + "(v1: M/L/C/Q/Z absolus)");
        }
        throw new Error(`chemin: commande inconnue '${t}'`);
      }
      cmd = t;
      i++;
      if (cmd === "Z") { segs.push({ c: "Z", p: [] }); cmd = null; }
      continue;
    }
    if (cmd === null) throw new Error("chemin: nombre sans commande");
    const p = [];
    for (let k = 0; k < ARITE[cmd]; k++, i++) {
      if (i >= jetons.length || /^[A-Za-z]$/.test(jetons[i])) {
        throw new Error(`chemin: arité de ${cmd} incomplète`);
      }
      p.push(Number(jetons[i]));
    }
    segs.push({ c: cmd, p });
    if (cmd === "M") cmd = "L";     // implicite SVG : paires après M = L
  }
  return segs;
}

export function chemin_serialiser(segs) {
  return segs.map((s) => s.c === "Z" ? "Z"
                       : s.c + " " + s.p.map(nbc).join(" ")).join(" ");
}


/* ── opérations d'objets (T1.2) : les COMMANDES pures sur le modèle ──
   L'UI ne fait que traduire des gestes vers ces fonctions ; l'historique
   d'annulation capture le JSON avant chacune. Déplacement et
   redimensionnement réécrivent la GÉOMÉTRIE (les booléens de phase 3
   veulent des coordonnées vraies) ; seule la rotation compose `transform`. */

function _calque(doc, calqueId) {
  const c = doc.calques.find((x) => x.id === calqueId);
  if (!c) throw new Error(`calque inconnu: ${calqueId}`);
  return c;
}

function* _objetsCibles(doc, ids, { ignorerVerrouilles = true } = {}) {
  const voulu = new Set(ids);
  for (const c of doc.calques) {
    if (ignorerVerrouilles && c.verrou) continue;
    for (let i = c.objets.length - 1; i >= 0; i--) {
      if (voulu.has(c.objets[i].id) && !c.objets[i].verrou) {
        yield { calque: c, objet: c.objets[i], i };
      }
    }
  }
}

function _idsPris(doc) {
  const pris = new Set();
  for (const cl of doc.calques) {
    (function visiter(objs) {
      for (const o of objs) {
        pris.add(o.id);
        if (o.type === "groupe") visiter(o.enfants || []);
      }
    })(cl.objets);
  }
  return pris;
}

export function idLibre(doc) {
  const pris = _idsPris(doc);
  let n = 1;
  while (pris.has("o" + n)) n++;
  return "o" + n;
}
const _idLibre = idLibre;

export function op_ajouter(doc, calqueId, objet) {
  const c = _calque(doc, calqueId);
  if (c.verrou) throw new Error(`calque verrouillé: ${calqueId}`);
  const pris = _idsPris(doc);
  const id = (objet.id && !pris.has(objet.id)) ? objet.id : _idLibre(doc);
  c.objets.push({ ...objet, id });
  return id;
}

export function op_supprimer(doc, ids) {
  let n = 0;
  for (const { calque, i } of _objetsCibles(doc, ids)) {
    calque.objets.splice(i, 1);
    n++;
  }
  return n;
}

function _decalerObjet(o, dx, dy) {
  switch (o.type) {
    case "rect": case "image": o.x += dx; o.y += dy; break;
    case "ellipse": case "forme": o.cx += dx; o.cy += dy; break;
    case "texte": case "instance": case "cadre": o.x += dx; o.y += dy; break;
    case "path": case "textechemin": {
      const segs = chemin_parser(o.d);
      for (const s of segs) {
        for (let k = 0; k < s.p.length; k += 2) { s.p[k] += dx; s.p[k + 1] += dy; }
      }
      o.d = chemin_serialiser(segs);
      break;
    }
    case "groupe": (o.enfants || []).forEach((e) => _decalerObjet(e, dx, dy)); break;
  }
}

/* ── LES DÉGRADÉS SUIVENT LA FORME ──────────────────────────────────
   `op_deplacer` et `op_redimensionner` MUTENT la géométrie ; le dégradé,
   lui, vit dans `doc.degrades` en `gradientUnits="userSpaceOnUse"` — il
   restait sur place (mesuré au navigateur le 06/09/2026 : forme déplacée
   de +120,+60, dégradé immobile). Ces deux aides le transportent.
   `op_tourner` est HORS SUJET : il pose un `transform` sur l'objet, et le
   user space d'un serveur de peinture est celui de l'élément qui le
   référence — le dégradé tourne déjà avec la forme.
   Un même dégradé peut être partagé par plusieurs objets : `vus` garantit
   qu'il n'est transporté QU'UNE fois par commande. */
function _gradIdsDe(objet, out) {
  const f = objet && objet.style && objet.style.fond;
  if (typeof f === "string" && f.startsWith("grad:")) out.add(f.slice(5));
  const m = objet && objet.style && objet.style.masque;
  if (typeof m === "string" && m.startsWith("grad:")) out.add(m.slice(5));   // lot F : le masque suit aussi
  if (objet && objet.type === "groupe") {
    (objet.enfants || []).forEach((e) => _gradIdsDe(e, out));
  }
  return out;
}

function _gradsDeCibles(doc, objets) {
  const ids = new Set();
  for (const o of objets) _gradIdsDe(o, ids);
  const degs = doc.degrades || {};
  const out = [];
  for (const id of ids) if (degs[id]) out.push(degs[id]);
  return out;
}

// applique (fx, fy) aux points du dégradé ; `kr` multiplie le rayon
function _gradMapper(g, fx, fy, kr) {
  if (g.type === "lineaire") {
    g.x1 = fx(g.x1); g.y1 = fy(g.y1);
    g.x2 = fx(g.x2); g.y2 = fy(g.y2);
  } else {
    g.cx = fx(g.cx); g.cy = fy(g.cy);
    if (kr !== undefined) g.r = Math.max(0.01, g.r * kr);
  }
}

// une tuile est ANCRÉE à la grille : son centre décalé se ré-arrondit à la
// cellule (lot C, D3) — redimensionner et refléter sont sans effet sur elle
function _decalerTuile(o, dx, dy, g) {
  const [cx, cy] = hex_centre(o.q, o.r, g);
  const a = hex_depuis_point(cx + dx, cy + dy, g);
  o.q = a.q; o.r = a.r;
}

export function op_deplacer(doc, ids, dx, dy) {
  const objets = [..._objetsCibles(doc, ids)].map((t) => t.objet);
  const gh = _grilleHex(doc);
  for (const o of objets) {
    if (o.type === "tuile") _decalerTuile(o, dx, dy, gh); else _decalerObjet(o, dx, dy);
  }
  for (const g of _gradsDeCibles(doc, objets)) {
    _gradMapper(g, (X) => X + dx, (Y) => Y + dy);
  }
}

function _mapperObjet(o, av, ap, doc) {
  const sx = ap.w / av.w, sy = ap.h / av.h;
  const fx = (X) => (X - av.x) * sx + ap.x;
  const fy = (Y) => (Y - av.y) * sy + ap.y;
  switch (o.type) {
    case "instance": {                   // lot F : l'échelle se cumule, l'origine suit la bbox
      const b = _bboxObjet(o, doc) || { x: o.x, y: o.y, w: 0, h: 0 };
      const sym = doc && doc.symboles && doc.symboles[o.symbole];
      const nsx = (o.sx || 1) * sx, nsy = (o.sy || 1) * sy;
      const bx = sym ? sym.bbox.x : 0, by = sym ? sym.bbox.y : 0;
      o.x = fx(b.x) - bx * nsx; o.y = fy(b.y) - by * nsy;
      o.sx = nsx; o.sy = nsy;
      break;
    }
    case "cadre":
      o.x = fx(o.x); o.y = fy(o.y); o.w = o.w * sx; o.h = o.h * sy; break;
    case "rect": case "image":
      o.x = fx(o.x); o.y = fy(o.y);
      o.w = o.w * sx; o.h = o.h * sy; break;
    case "ellipse":
      o.cx = fx(o.cx); o.cy = fy(o.cy);
      o.rx = Math.abs(o.rx * sx); o.ry = Math.abs(o.ry * sy); break;
    case "forme":                        // les paramètres restent, sx/sy portent l'échelle
      o.cx = fx(o.cx); o.cy = fy(o.cy);
      o.sx = Math.abs((o.sx || 1) * sx); o.sy = Math.abs((o.sy || 1) * sy); break;
    case "texte":
      o.x = fx(o.x); o.y = fy(o.y);
      if (o.style && o.style.corps) {     // le corps suit la hauteur
        o.style.corps = Math.round(o.style.corps * sy * 100) / 100;
      }
      break;
    case "path": case "textechemin": {
      const segs = chemin_parser(o.d);
      for (const s of segs) {
        for (let k = 0; k < s.p.length; k += 2) {
          s.p[k] = fx(s.p[k]); s.p[k + 1] = fy(s.p[k + 1]);
        }
      }
      o.d = chemin_serialiser(segs);
      break;
    }
    case "groupe": (o.enfants || []).forEach((e) => _mapperObjet(e, av, ap, doc)); break;
  }
}

export function op_redimensionner(doc, ids, bboxAvant, bboxApres) {
  if (!(bboxAvant.w > 0) || !(bboxAvant.h > 0)) return;
  const objets = [..._objetsCibles(doc, ids)].map((t) => t.objet);
  for (const o of objets) _mapperObjet(o, bboxAvant, bboxApres, doc);
  const sx = bboxApres.w / bboxAvant.w, sy = bboxApres.h / bboxAvant.h;
  const fx = (X) => (X - bboxAvant.x) * sx + bboxApres.x;
  const fy = (Y) => (Y - bboxAvant.y) * sy + bboxApres.y;
  // ÉCART ASSUMÉ : un dégradé radial SVG n'a qu'UN rayon ; sous une
  // échelle non uniforme aucune valeur n'est exacte — la moyenne des deux
  // facteurs est le choix retenu, et il est dit ici.
  for (const g of _gradsDeCibles(doc, objets)) {
    _gradMapper(g, fx, fy, (sx + sy) / 2);
  }
}

export function op_tourner(doc, ids, cx, cy, deg) {
  const t = `rotate(${nbc(deg)} ${nbc(cx)} ${nbc(cy)})`;
  for (const { objet } of _objetsCibles(doc, ids)) {
    objet.transform = objet.transform ? `${t} ${objet.transform}` : t;
  }
}


/* ── nœuds Bézier (T1.3) ──
   Une ANCRE = le point on-curve d'un segment M/L/C/Q (ses deux derniers
   nombres). Poignée ENTRANTE = contrôles du segment porteur (C p[2..3],
   Q p[0..1]) ; poignée SORTANTE = premier contrôle du segment C suivant.
   Le Q partage sa poignée : v1 la rattache à l'ancre de FIN du segment. */

function _trouverPath(doc, id) {
  for (const c of doc.calques) {
    if (c.verrou) continue;
    const o = c.objets.find((x) => x.id === id);
    if (o) {
      if (o.type !== "path") throw new Error(`objet ${id}: pas un chemin`);
      return o;
    }
  }
  throw new Error(`chemin introuvable (ou calque verrouillé): ${id}`);
}

function _porteurs(segs) {
  const out = [];
  segs.forEach((s, k) => { if (s.c !== "Z") out.push(k); });
  return out;
}

const _fin = (s) => ({ x: s.p[s.p.length - 2], y: s.p[s.p.length - 1] });

export function chemin_ancres(segs) {
  const noeuds = _porteurs(segs);
  return noeuds.map((k, i) => {
    const s = segs[k];
    const f = _fin(s);
    const entrante = s.c === "C" ? { x: s.p[2], y: s.p[3] }
                   : s.c === "Q" ? { x: s.p[0], y: s.p[1] } : null;
    const kn = noeuds[i + 1];
    const sn = kn === undefined ? null : segs[kn];
    const sortante = sn && sn.c === "C" ? { x: sn.p[0], y: sn.p[1] } : null;
    return { i, x: f.x, y: f.y, entrante, sortante };
  });
}

function _segsDe(o) { return chemin_parser(o.d); }
function _poser(o, segs) { o.d = chemin_serialiser(segs); }

export function op_noeud_deplacer(doc, id, iAncre, dx, dy) {
  const o = _trouverPath(doc, id);
  const segs = _segsDe(o);
  const noeuds = _porteurs(segs);
  const k = noeuds[iAncre];
  if (k === undefined) throw new Error(`ancre ${iAncre} hors chemin`);
  const s = segs[k];
  s.p[s.p.length - 2] += dx;
  s.p[s.p.length - 1] += dy;
  if (s.c === "C") { s.p[2] += dx; s.p[3] += dy; }
  if (s.c === "Q") { s.p[0] += dx; s.p[1] += dy; }
  const kn = noeuds[iAncre + 1];
  if (kn !== undefined && segs[kn].c === "C") {
    segs[kn].p[0] += dx; segs[kn].p[1] += dy;
  }
  _poser(o, segs);
}

export function op_noeud_convertir(doc, id, iAncre) {
  const o = _trouverPath(doc, id);
  const segs = _segsDe(o);
  const noeuds = _porteurs(segs);
  const k = noeuds[iAncre];
  if (k === undefined) throw new Error(`ancre ${iAncre} hors chemin`);
  const ferme = segs.some((s) => s.c === "Z");
  const s = segs[k];
  const f = _fin(s);
  const a = chemin_ancres(segs)[iAncre];
  // COURBE si la poignée ENTRANTE est vive ; une ancre mixte (entrée en
  // ligne, sortie courbe) est un ANGLE — l'ancre M, sans entrante possible,
  // se juge sur sa sortante.
  const vive = (pt) => pt && (pt.x !== f.x || pt.y !== f.y);
  const estCourbe = vive(a.entrante) || (s.c === "M" && vive(a.sortante));
  const kn = noeuds[iAncre + 1];
  if (estCourbe) {
    // courbe → angle : les poignées attachées se dégénèrent sur l'ancre
    if (s.c === "C") { s.p[2] = f.x; s.p[3] = f.y; }
    if (s.c === "Q") { s.p[0] = f.x; s.p[1] = f.y; }
    if (kn !== undefined && segs[kn].c === "C") {
      segs[kn].p[0] = f.x; segs[kn].p[1] = f.y;
    }
  } else {
    // angle → courbe : poignées symétriques ± (suivant − précédent) / 4
    const ancres = chemin_ancres(segs);
    const n = ancres.length;
    const prev = iAncre > 0 ? ancres[iAncre - 1]
               : (ferme && n > 1 ? ancres[n - 1] : a);
    const next = iAncre < n - 1 ? ancres[iAncre + 1]
               : (ferme && n > 1 ? ancres[0] : a);
    const vx = (next.x - prev.x) / 4, vy = (next.y - prev.y) / 4;
    const ent = { x: f.x - vx, y: f.y - vy };
    const sor = { x: f.x + vx, y: f.y + vy };
    if (s.c === "L") {
      segs[k] = { c: "C", p: [prev.x, prev.y, ent.x, ent.y, f.x, f.y] };
    } else if (s.c === "C") { s.p[2] = ent.x; s.p[3] = ent.y; }
    else if (s.c === "Q") { s.p[0] = ent.x; s.p[1] = ent.y; }
    if (kn !== undefined) {
      const sn = segs[kn];
      const nf = _fin(sn);
      if (sn.c === "L") {
        segs[kn] = { c: "C", p: [sor.x, sor.y, nf.x, nf.y, nf.x, nf.y] };
      } else if (sn.c === "C" || sn.c === "Q") {
        sn.p[0] = sor.x; sn.p[1] = sor.y;
      }
    }
  }
  _poser(o, segs);
}

export function op_noeud_supprimer(doc, id, iAncre) {
  const o = _trouverPath(doc, id);
  const segs = _segsDe(o);
  const noeuds = _porteurs(segs);
  const k = noeuds[iAncre];
  if (k === undefined) throw new Error(`ancre ${iAncre} hors chemin`);
  segs.splice(k, 1);
  if (iAncre === 0) {
    if (segs.length && segs[0].c !== "Z") {
      segs[0] = { c: "M", p: [_fin(segs[0]).x, _fin(segs[0]).y] };
    }
  } else if (k < segs.length && (segs[k].c === "C" || segs[k].c === "Q")) {
    segs[k] = { c: "L", p: [_fin(segs[k]).x, _fin(segs[k]).y] };
  }
  _poser(o, segs);
}

export function op_chemin_fermer(doc, id) {
  const o = _trouverPath(doc, id);
  const segs = _segsDe(o);
  if (!segs.length || segs[segs.length - 1].c !== "Z") {
    segs.push({ c: "Z", p: [] });
  }
  _poser(o, segs);
}


/* ── calques (T1.4) : l'ordre du tableau EST l'ordre de peinture
   (le dernier est au-dessus). Un document garde toujours au moins un
   calque — la suppression du dernier est refusée. */

export function op_calque_ajouter(doc, nom) {
  const pris = new Set(doc.calques.map((c) => c.id));
  let n = 1;
  while (pris.has("c" + n)) n++;
  const id = "c" + n;
  doc.calques.push({ id, nom: nom || id, visible: true, verrou: false,
                     objets: [] });
  return id;
}

export function op_calque_renommer(doc, id, nom) {
  _calque(doc, id).nom = String(nom || "");
}

export function op_calque_reordonner(doc, id, nouvelIndex) {
  const c = _calque(doc, id);
  const i = doc.calques.indexOf(c);
  doc.calques.splice(i, 1);
  const j = Math.max(0, Math.min(doc.calques.length, nouvelIndex));
  doc.calques.splice(j, 0, c);
}

export function op_calque_visible(doc, id, visible) {
  _calque(doc, id).visible = !!visible;
}

export function op_calque_verrou(doc, id, verrou) {
  _calque(doc, id).verrou = !!verrou;
}

export function op_calque_supprimer(doc, id) {
  const c = _calque(doc, id);
  if (doc.calques.length <= 1) {
    throw new Error("un document garde au moins un calque");
  }
  doc.calques.splice(doc.calques.indexOf(c), 1);
}


/* ── apparence (T2.1) : style fusionné par patch, opacité de calque ── */

export function op_style(doc, ids, patch) {
  for (const { objet } of _objetsCibles(doc, ids)) {
    const s = { ...(objet.style || {}) };
    for (const [k, v] of Object.entries(patch || {})) {
      if (v === null) delete s[k];
      else s[k] = v;
    }
    objet.style = s;
  }
}

export function op_calque_opacite(doc, id, opacite) {
  _calque(doc, id).opacite = Math.max(0, Math.min(1, Number(opacite)));
}


/* ── groupes, ordre z, sommet (T2.3) ── */

export function sommetDe(doc, id) {
  const dedans = (g) => (g.enfants || []).some(
    (e) => e.id === id || (e.type === "groupe" && dedans(e)));
  for (const c of doc.calques) {
    for (const o of c.objets) {
      if (o.id === id) return id;
      if (o.type === "groupe" && dedans(o)) return o.id;
    }
  }
  return null;
}

export function op_grouper(doc, ids) {
  const voulu = new Set(ids);
  const cibles = [];                   // en ordre de peinture (bas → haut)
  for (const c of doc.calques) {
    if (c.verrou) continue;
    for (const o of c.objets) {
      if (voulu.has(o.id)) cibles.push({ calque: c, objet: o });
    }
  }
  if (cibles.length < 2) {
    throw new Error("grouper: au moins deux objets déverrouillés");
  }
  const hote = cibles[cibles.length - 1].calque;
  for (const { calque, objet } of cibles) {
    calque.objets.splice(calque.objets.indexOf(objet), 1);
  }
  const id = _idLibre(doc);
  hote.objets.push({ id, type: "groupe", style: {},
                     enfants: cibles.map((t) => t.objet) });
  return id;
}

export function op_degrouper(doc, id) {
  for (const c of doc.calques) {
    if (c.verrou) continue;
    const i = c.objets.findIndex((o) => o.id === id);
    if (i >= 0) {
      const g = c.objets[i];
      if (g.type !== "groupe") throw new Error(`${id}: pas un groupe`);
      const enfants = g.enfants || [];
      if (g.transform) {              // le transform du groupe suit les enfants
        for (const e of enfants) {
          e.transform = e.transform ? `${g.transform} ${e.transform}`
                                    : g.transform;
        }
      }
      c.objets.splice(i, 1, ...enfants);
      return enfants.map((e) => e.id);
    }
  }
  throw new Error(`groupe introuvable (ou calque verrouillé): ${id}`);
}

export function op_ordre(doc, ids, mode) {
  if (!["devant", "derriere", "avant", "arriere"].includes(mode)) {
    throw new Error(`ordre: mode inconnu ${mode}`);
  }
  const voulu = new Set(ids);
  for (const c of doc.calques) {
    if (c.verrou) continue;
    const dedans = c.objets.filter((o) => voulu.has(o.id));
    if (!dedans.length) continue;
    if (mode === "devant") {
      c.objets = c.objets.filter((o) => !voulu.has(o.id)).concat(dedans);
    } else if (mode === "derriere") {
      c.objets = dedans.concat(c.objets.filter((o) => !voulu.has(o.id)));
    } else if (mode === "avant") {
      for (let i = c.objets.length - 2; i >= 0; i--) {
        if (voulu.has(c.objets[i].id) && !voulu.has(c.objets[i + 1].id)) {
          [c.objets[i], c.objets[i + 1]] = [c.objets[i + 1], c.objets[i]];
        }
      }
    } else {
      for (let i = 1; i < c.objets.length; i++) {
        if (voulu.has(c.objets[i].id) && !voulu.has(c.objets[i - 1].id)) {
          [c.objets[i], c.objets[i - 1]] = [c.objets[i - 1], c.objets[i]];
        }
      }
    }
  }
}


/* ── dégradés (T2.2) : en coordonnées DOCUMENT (userSpaceOnUse) ──
   doc.degrades = {id: {type: lineaire|radial, stops:[{t, couleur,
   opacite?}], x1..y2 | cx,cy,r}}. Un fond y réfère par "grad:<id>" ; la
   compilation émet <defs> (stops triés par t) et retombe sur "none" si le
   dégradé manque — un document ne casse jamais. */

const _TYPES_DEGRADE = new Set(["lineaire", "radial", "conique"]);

function _degrades(doc) {
  if (!doc.degrades) doc.degrades = {};
  return doc.degrades;
}
function _degrade(doc, id) {
  const g = _degrades(doc)[id];
  if (!g) throw new Error(`degrade inconnu: ${id}`);
  return g;
}

export function op_degrade_creer(doc, spec) {
  if (!spec || !_TYPES_DEGRADE.has(spec.type)) {
    throw new Error("degrade: type invalide (lineaire|radial)");
  }
  const stops = (Array.isArray(spec.stops) && spec.stops.length >= 2)
    ? spec.stops
    : [{ t: 0, couleur: "#000000" }, { t: 1, couleur: "#FFFFFF" }];
  const degs = _degrades(doc);
  let n = 1;
  while (("g" + n) in degs) n++;
  const id = "g" + n;
  const g = { type: spec.type, stops: stops.map((s) => ({ ...s })) };
  if (spec.type === "lineaire") {
    g.x1 = +(spec.x1 ?? 0); g.y1 = +(spec.y1 ?? 0);
    g.x2 = +(spec.x2 ?? 1); g.y2 = +(spec.y2 ?? 0);
  } else {
    g.cx = +(spec.cx ?? 0); g.cy = +(spec.cy ?? 0); g.r = +(spec.r ?? 1);
    if (spec.type === "conique") {
      if (!(g.r > 0)) throw new Error("degrade conique: rayon > 0");
      g.angle = +(spec.angle ?? 0);
    }
  }
  degs[id] = g;
  return id;
}

// lot F : dégradé de TRANSPARENCE = un masque de luminance blanc → noir
// posé sur la bbox de la sélection ; le style référence « grad:<id> »
export function op_degrade_transparence(doc, ids, bbox) {
  if (!bbox || !(bbox.w > 0) || !(bbox.h > 0)) throw new Error("transparence : bbox requise");
  const id = op_degrade_creer(doc, { type: "lineaire", x1: bbox.x, y1: bbox.y + bbox.h / 2, x2: bbox.x + bbox.w, y2: bbox.y + bbox.h / 2,
    stops: [{ t: 0, couleur: "#FFFFFF" }, { t: 1, couleur: "#000000" }] });
  let n = 0;
  for (const { objet } of _objetsCibles(doc, ids)) { objet.style = { ...(objet.style || {}), masque: `grad:${id}` }; n++; }
  if (!n) { delete doc.degrades[id]; throw new Error("transparence : rien à masquer"); }
  return id;
}

export function op_degrade_modifier(doc, id, patch) {
  const g = _degrade(doc, id);
  for (const k of ["x1", "y1", "x2", "y2", "cx", "cy", "r", "angle"]) {
    if (patch && k in patch) g[k] = +patch[k];
  }
}

/* ── lot F : motifs (doc.motifs), couleurs globales, écrêtage ── */
function _visiterObjets(doc, fn) {
  const visiter = (objs) => { for (const o of objs || []) { fn(o); if (o.type === "groupe") visiter(o.enfants); } };
  for (const c of doc.calques) visiter(c.objets);
}
export function op_motif_creer(doc, spec) {
  motif_valider(spec);
  if (!doc.motifs) doc.motifs = {};
  let n = 1;
  while (("m" + n) in doc.motifs) n++;
  doc.motifs["m" + n] = { ...spec };
  return "m" + n;
}
export function op_motif_modifier(doc, id, patch) {
  if (!doc.motifs || !doc.motifs[id]) throw new Error(`motif inconnu: ${id}`);
  const m = { ...doc.motifs[id], ...(patch || {}) };
  motif_valider(m);
  doc.motifs[id] = m;
}
export function op_motif_supprimer(doc, id) {
  if (!doc.motifs || !doc.motifs[id]) throw new Error(`motif inconnu: ${id}`);
  delete doc.motifs[id];
  _visiterObjets(doc, (o) => { if (o.style && o.style.fond === `motif:${id}`) o.style.fond = "none"; });
}
export function op_couleur_globale_definir(doc, nom, hex) {
  if (!_NOM_GLOBAL.test(String(nom || ""))) throw new Error("couleur globale : nom [A-Za-z0-9_-] requis");
  if (!_HEX6.test(String(hex || ""))) throw new Error("couleur globale : #RRGGBB requis");
  if (!doc.couleursGlobales) doc.couleursGlobales = {};
  doc.couleursGlobales[nom] = String(hex).toUpperCase();
}
// supprimer RÉSOUT chaque référence en hex : jamais de référence pendante
export function op_couleur_globale_supprimer(doc, nom) {
  if (!doc.couleursGlobales || !doc.couleursGlobales[nom]) throw new Error(`couleur globale inconnue: ${nom}`);
  const hex = doc.couleursGlobales[nom], ref = `glob:${nom}`;
  const res = (v) => (v === ref ? hex : v);
  _visiterObjets(doc, (o) => {
    if (!o.style) return;
    if (o.style.fond !== undefined) o.style.fond = res(o.style.fond);
    if (o.style.contour !== undefined) o.style.contour = res(o.style.contour);
    for (const c of o.style.contours || []) c.couleur = res(c.couleur);
  });
  for (const g of Object.values(doc.degrades || {})) for (const st of g.stops || []) st.couleur = res(st.couleur);
  for (const m of Object.values(doc.motifs || {})) { m.couleur = res(m.couleur); if (m.fond) m.fond = res(m.fond); }
  delete doc.couleursGlobales[nom];
  if (!Object.keys(doc.couleursGlobales).length) delete doc.couleursGlobales;
}
// écrêtage vectoriel (« coller dans ») : un groupe {clip} dont le premier
// enfant est le conteneur ; les contenus sont rognés par sa géométrie
export function op_ecreter(doc, idConteneur, ids) {
  if (!Array.isArray(ids) || !ids.length) throw new Error("écrêter : rien à rogner");
  const voulu = new Set(ids);
  let hote = null, conteneur = null;
  const contenus = [];
  for (const c of doc.calques) {
    if (c.verrou) continue;
    for (const o of c.objets) {
      if (o.id === idConteneur) { hote = c; conteneur = o; }
      else if (voulu.has(o.id)) contenus.push({ calque: c, objet: o });
    }
  }
  if (!conteneur) throw new Error(`écrêter : conteneur introuvable ${idConteneur}`);
  if (!contenus.length) throw new Error("écrêter : contenus introuvables");
  for (const { calque, objet } of contenus) calque.objets.splice(calque.objets.indexOf(objet), 1);
  const iC = hote.objets.indexOf(conteneur);
  hote.objets.splice(iC, 1);
  const id = _idLibre(doc);
  hote.objets.splice(iC, 0, { id, type: "groupe", clip: idConteneur, style: {}, enfants: [conteneur, ...contenus.map((t) => t.objet)] });
  return id;
}
export function op_desecreter(doc, id) {
  for (const c of doc.calques) {
    if (c.verrou) continue;
    const i = c.objets.findIndex((o) => o.id === id);
    if (i >= 0) {
      const g = c.objets[i];
      if (g.type !== "groupe" || !g.clip) throw new Error(`${id}: pas un groupe écrêté`);
      c.objets.splice(i, 1, ...g.enfants);
      return g.enfants.map((e) => e.id);
    }
  }
  throw new Error(`groupe écrêté introuvable: ${id}`);
}
export const bbox_objet = (o, doc) => _bboxObjet(o, doc);

/* ── lot F : cadre de texte et texte sur chemin ── */
function _trouverType(doc, id, types) {
  for (const { objet } of _objetsCibles(doc, [id])) {
    if (!types.includes(objet.type)) throw new Error(`${id}: ${types.join("|")} attendu, pas ${objet.type}`);
    return objet;
  }
  throw new Error(`objet introuvable: ${id}`);
}
export function op_texte_en_cadre(doc, id, w, h) {
  if (!(w > 0) || !(h > 0)) throw new Error("cadre : taille positive requise");
  const o = _trouverType(doc, id, ["texte"]);
  const corps = Number((o.style && o.style.corps) || 16);
  o.type = "cadre"; o.y = o.y - corps; o.w = +w; o.h = +h;
}
export function op_texte_sur_chemin(doc, idTexte, idChemin) {
  const o = _trouverType(doc, idTexte, ["texte", "cadre"]);
  const c = _trouverType(doc, idChemin, ["path", "forme"]);
  o.type = "textechemin"; o.d = c.type === "forme" ? forme_d(c) : c.d; o.decalage = 0;
  delete o.x; delete o.y; delete o.w; delete o.h;
}
export function op_textechemin_decalage(doc, id, pct) {
  if (!(pct >= 0 && pct <= 100)) throw new Error("décalage : 0 à 100 %");
  _trouverType(doc, id, ["textechemin"]).decalage = +pct;
}

/* ── lot F : styles d'objet (copie à l'application) ── */
const _clone = (v) => JSON.parse(JSON.stringify(v));
export function op_style_definir(doc, nom, style) {
  if (!_NOM_GLOBAL.test(String(nom || ""))) throw new Error("style : nom [A-Za-z0-9_-] requis");
  if (!style || typeof style !== "object") throw new Error("style : objet requis");
  _validerStyleAvance(style, `style ${nom}`);
  if (!doc.styles) doc.styles = {};
  doc.styles[nom] = _clone(style);
}
export function op_style_appliquer(doc, ids, nom) {
  if (!doc.styles || !doc.styles[nom]) throw new Error(`style inconnu: ${nom}`);
  let n = 0;
  for (const { objet } of _objetsCibles(doc, ids)) { objet.style = { ...(objet.style || {}), ..._clone(doc.styles[nom]) }; n++; }
  return n;
}
export function op_style_supprimer(doc, nom) {
  if (!doc.styles || !doc.styles[nom]) throw new Error(`style inconnu: ${nom}`);
  delete doc.styles[nom];
  if (!Object.keys(doc.styles).length) delete doc.styles;
}

/* ── lot F : symboles VIVANTS — doc.symboles[id] = {nom, bbox, objets} ;
   l'instance {symbole, x, y, sx, sy} est un <use> ; modifier le symbole
   change toutes ses instances ; « détacher » copie les objets à leur place. */
export function op_symbole_creer(doc, ids, nom) {
  const voulu = new Set(ids || []);
  const cibles = [];
  for (const c of doc.calques) {
    if (c.verrou) continue;
    for (const o of c.objets) if (voulu.has(o.id)) cibles.push({ calque: c, objet: o });
  }
  if (!cibles.length) throw new Error("symbole : aucun objet");
  const bs = cibles.map((t) => _bboxObjet(t.objet, doc)).filter(Boolean);
  const x0 = Math.min(...bs.map((b) => b.x)), y0 = Math.min(...bs.map((b) => b.y));
  const bbox = { x: x0, y: y0, w: Math.max(0.01, Math.max(...bs.map((b) => b.x + b.w)) - x0), h: Math.max(0.01, Math.max(...bs.map((b) => b.y + b.h)) - y0) };
  if (!doc.symboles) doc.symboles = {};
  let n = 1;
  while (("s" + n) in doc.symboles) n++;
  const sid = "s" + n;
  const dernier = cibles[cibles.length - 1];
  const iD = dernier.calque.objets.indexOf(dernier.objet);
  const id = _idLibre(doc);
  for (const { calque, objet } of cibles) calque.objets.splice(calque.objets.indexOf(objet), 1);
  doc.symboles[sid] = { nom: nom || sid, bbox, objets: cibles.map((t) => t.objet) };
  dernier.calque.objets.splice(Math.min(iD, dernier.calque.objets.length), 0, { id, type: "instance", symbole: sid, x: 0, y: 0, sx: 1, sy: 1, style: {} });
  return sid;
}
export function op_instance_poser(doc, calqueId, sid, x, y) {
  if (!doc.symboles || !doc.symboles[sid]) throw new Error(`symbole inconnu: ${sid}`);
  return op_ajouter(doc, calqueId, { type: "instance", symbole: sid, x: +x, y: +y, sx: 1, sy: 1, style: {} });
}
export function op_symbole_modifier(doc, sid, fn) {
  if (!doc.symboles || !doc.symboles[sid]) throw new Error(`symbole inconnu: ${sid}`);
  const sym = doc.symboles[sid];
  fn(sym.objets, sym);
  _validerObjets(sym.objets, `symbole ${sid}`);
}
export function op_symbole_detacher(doc, idInstance) {
  for (const c of doc.calques) {
    if (c.verrou) continue;
    const i = c.objets.findIndex((o) => o.id === idInstance);
    if (i < 0) continue;
    const inst = c.objets[i];
    if (inst.type !== "instance") throw new Error(`${idInstance}: pas une instance`);
    const sym = doc.symboles && doc.symboles[inst.symbole];
    if (!sym) throw new Error(`symbole inconnu: ${inst.symbole}`);
    const av = sym.bbox, ap = _bboxObjet(inst, doc);
    c.objets.splice(i, 1);
    // copies à ids NEUFS (insérées une à une : _idLibre voit chaque id posé),
    // mappées de la bbox du symbole vers celle de l'instance
    const copies = _clone(sym.objets);
    copies.forEach((o, k) => { o.id = _idLibre(doc); _mapperObjet(o, av, ap, doc); c.objets.splice(i + k, 0, o); });
    return copies.map((o) => o.id);
  }
  throw new Error(`instance introuvable: ${idInstance}`);
}
export function op_symbole_supprimer(doc, sid) {
  if (!doc.symboles || !doc.symboles[sid]) throw new Error(`symbole inconnu: ${sid}`);
  let n = 0;
  _visiterObjets(doc, (o) => { if (o.type === "instance" && o.symbole === sid) n++; });
  if (n) throw new Error(`symbole ${sid} : ${n} instance(s) encore posée(s)`);
  delete doc.symboles[sid];
  if (!Object.keys(doc.symboles).length) delete doc.symboles;
}

export function op_degrade_stop_ajouter(doc, id, stop) {
  const g = _degrade(doc, id);
  g.stops.push({ ...stop });
  return g.stops.length - 1;
}

export function op_degrade_stop_modifier(doc, id, i, patch) {
  const g = _degrade(doc, id);
  if (i < 0 || i >= g.stops.length) throw new Error(`stop ${i} hors bornes`);
  for (const k of ["t", "couleur", "opacite"]) {
    if (patch && k in patch) g.stops[i][k] = patch[k];
  }
}

export function op_degrade_stop_supprimer(doc, id, i) {
  const g = _degrade(doc, id);
  if (g.stops.length <= 2) throw new Error("un degrade garde au moins deux stops");
  if (i < 0 || i >= g.stops.length) throw new Error(`stop ${i} hors bornes`);
  g.stops.splice(i, 1);
}

export function op_degrade_supprimer(doc, id) {
  _degrade(doc, id);
  delete doc.degrades[id];
}


/* ── historique (T1.5) : annulation par INSTANTANÉS du JSON ──
   `capturer(doc)` AVANT chaque commande ; `annuler(courant)` rend l'état
   capturé et empile le courant côté refaire ; `refaire(courant)` fait
   l'inverse. Tout entre et sort en CLONE — aucune référence partagée. */
export class Historique {
  constructor(cap = 1000) {              // lot B : 1 000 pas (Affinity en offre 8 000)
    this.cap = cap;
    this._avant = [];
    this._apres = [];
    this._instantanes = new Map();       // instantanés NOMMÉS de la session
  }
  _clone(doc) { return JSON.parse(JSON.stringify(doc)); }
  instantane(nom, doc) {
    const n = String(nom || "").trim();
    if (!n) throw new Error("instantané : un nom est requis");
    this._instantanes.set(n, this._clone(doc));
    return n;
  }
  instantanes() { return [...this._instantanes.keys()]; }
  restaurer(nom) {
    const d = this._instantanes.get(String(nom));
    if (!d) throw new Error(`instantané inconnu : ${nom}`);
    return this._clone(d);
  }
  capturer(doc) {
    this._avant.push(this._clone(doc));
    if (this._avant.length > this.cap) this._avant.shift();
    this._apres.length = 0;         // une nouvelle commande invalide refaire
  }
  peutAnnuler() { return this._avant.length > 0; }
  peutRefaire() { return this._apres.length > 0; }
  annuler(courant) {
    if (!this.peutAnnuler()) throw new Error("rien à annuler");
    this._apres.push(this._clone(courant));
    return this._avant.pop();
  }
  refaire(courant) {
    if (!this.peutRefaire()) throw new Error("rien à refaire");
    this._avant.push(this._clone(courant));
    return this._apres.pop();
  }
}


/* ── aimantation et guides (T1.6) : les guides d'abord (l'intention posée
   par l'utilisateur prime sur la grille), rien hors tolérance. Les guides
   vivent dans doc.guides {v:[x…], h:[y…]} — mutés par commandes, donc
   capturés par l'historique comme le reste du document. */

export function aimanter(v, { pas = 0, guides = [] } = {}, tol = 0) {
  let meilleur = null, ecart = Infinity;
  for (const g of guides) {
    const e = Math.abs(v - g);
    if (e <= tol && e < ecart) { meilleur = g; ecart = e; }
  }
  if (meilleur !== null) return meilleur;
  if (pas > 0) {
    const g = Math.round(v / pas) * pas;
    if (Math.abs(v - g) <= tol) return g;
  }
  return v;
}

function _axeGuides(doc, axe) {
  if (axe !== "v" && axe !== "h") throw new Error(`axe de guide inconnu: ${axe}`);
  if (!doc.guides) doc.guides = { v: [], h: [] };
  if (!Array.isArray(doc.guides[axe])) doc.guides[axe] = [];
  return doc.guides[axe];
}

export function op_guide_ajouter(doc, axe, pos) {
  const g = _axeGuides(doc, axe);
  g.push(Number(pos));
  return g.length - 1;
}

export function op_guide_deplacer(doc, axe, i, pos) {
  const g = _axeGuides(doc, axe);
  if (i < 0 || i >= g.length) throw new Error(`guide ${axe}[${i}] hors bornes`);
  g[i] = Number(pos);
}

/* ── les classiques (éditeur complet, E8) : dupliquer, miroir, aligner,
   distribuer, rayon d'angle. Les bboxes d'alignement sont FOURNIES par
   l'appelant (le DOM mesure, l'op reste pure — patron op_redimensionner). */

export function op_dupliquer(doc, ids, dx = 12, dy = 12) {
  const cibles = [..._objetsCibles(doc, ids)];
  if (!cibles.length) throw new Error("rien à dupliquer");
  const pris = _idsPris(doc);
  let n = 1;
  const idNeuf = () => {
    while (pris.has("o" + n)) n++;
    const id = "o" + n;
    pris.add(id);
    return id;
  };
  const reid = (o) => {
    o.id = idNeuf();
    if (o.type === "groupe") (o.enfants || []).forEach(reid);
  };
  // Le clone reçoit SA COPIE du dégradé : partagé, un `userSpaceOnUse`
  // suivrait les deux formes à la fois — déplacer la copie déplacerait le
  // dégradé de l'original (mesuré).
  const degs = _degrades(doc);
  const reGrad = (o) => {
    const f = o.style && o.style.fond;
    if (typeof f === "string" && f.startsWith("grad:") && degs[f.slice(5)]) {
      let k = 1;
      while (("g" + k) in degs) k++;
      degs["g" + k] = JSON.parse(JSON.stringify(degs[f.slice(5)]));
      o.style = { ...o.style, fond: "grad:g" + k };
    }
    if (o.type === "groupe") (o.enfants || []).forEach(reGrad);
  };
  const neufs = [];
  // _objetsCibles rend les index DÉCROISSANTS : insérer à i+1 ne décale
  // jamais une cible restante
  for (const { calque, objet, i } of cibles) {
    const clone = JSON.parse(JSON.stringify(objet));
    reid(clone);
    reGrad(clone);
    if (clone.type === "tuile") _decalerTuile(clone, dx, dy, _grilleHex(doc));
    else _decalerObjet(clone, dx, dy);
    for (const g of _gradsDeCibles(doc, [clone])) {
      _gradMapper(g, (X) => X + dx, (Y) => Y + dy);
    }
    calque.objets.splice(i + 1, 0, clone);
    neufs.push(clone.id);
  }
  return neufs;
}

export function op_miroir(doc, ids, axe, bbox) {
  if (axe !== "h" && axe !== "v") throw new Error(`miroir: axe h|v, pas ${axe}`);
  if (!bbox || !(bbox.w >= 0) || !(bbox.h >= 0)) {
    throw new Error("miroir: bbox de référence requise");
  }
  const cx = bbox.x + bbox.w / 2, cy = bbox.y + bbox.h / 2;
  const H = axe === "h";
  const fx = (X) => 2 * cx - X, fy = (Y) => 2 * cy - Y;
  const refl = (o) => {
    switch (o.type) {
      case "rect": case "image":           // image : position seule — les
        if (H) o.x = fx(o.x) - o.w; else o.y = fy(o.y) - o.h; break;   // pixels ne se retournent pas (écart dit)
      case "ellipse": case "forme":
        if (H) o.cx = fx(o.cx); else o.cy = fy(o.cy); break;
      case "texte":                     // position seule — les glyphes ne
        if (H) o.x = fx(o.x); else o.y = fy(o.y); break;   // se reflètent pas
      case "path": case "textechemin": {
        const segs = chemin_parser(o.d);
        for (const s of segs) {
          for (let k = 0; k < s.p.length; k += 2) {
            if (H) s.p[k] = fx(s.p[k]); else s.p[k + 1] = fy(s.p[k + 1]);
          }
        }
        o.d = chemin_serialiser(segs);
        break;
      }
      case "groupe": (o.enfants || []).forEach(refl); break;
    }
  };
  const objets = [..._objetsCibles(doc, ids)].map((t) => t.objet);
  for (const o of objets) refl(o);
  if (!objets.length) throw new Error("rien à réfléchir");
  for (const g of _gradsDeCibles(doc, objets)) {
    _gradMapper(g, H ? fx : (X) => X, H ? (Y) => Y : fy);
  }
  return objets.length;
}

const _ALIGNEMENTS = new Set(["gauche", "centreH", "droite",
                              "haut", "centreV", "bas"]);

export function op_aligner(doc, paires, mode, ref) {
  if (!_ALIGNEMENTS.has(mode)) throw new Error(`aligner: mode inconnu ${mode}`);
  if (!Array.isArray(paires) || !paires.length) {
    throw new Error("aligner: rien à aligner");
  }
  if (!ref || !(ref.w >= 0)) throw new Error("aligner: référence requise");
  for (const { id, bbox } of paires) {
    let dx = 0, dy = 0;
    if (mode === "gauche") dx = ref.x - bbox.x;
    else if (mode === "centreH") dx = (ref.x + ref.w / 2) - (bbox.x + bbox.w / 2);
    else if (mode === "droite") dx = (ref.x + ref.w) - (bbox.x + bbox.w);
    else if (mode === "haut") dy = ref.y - bbox.y;
    else if (mode === "centreV") dy = (ref.y + ref.h / 2) - (bbox.y + bbox.h / 2);
    else dy = (ref.y + ref.h) - (bbox.y + bbox.h);
    if (dx || dy) op_deplacer(doc, [id], dx, dy);
  }
}

export function op_distribuer(doc, paires, axe) {
  if (axe !== "h" && axe !== "v") throw new Error(`distribuer: axe h|v, pas ${axe}`);
  if (!Array.isArray(paires) || paires.length < 3) {
    throw new Error("distribuer: 3 objets au moins");
  }
  const H = axe === "h";
  const tri = paires.slice().sort((a, b) =>
    H ? a.bbox.x - b.bbox.x : a.bbox.y - b.bbox.y);
  const premier = tri[0].bbox, dernier = tri[tri.length - 1].bbox;
  const debut = H ? premier.x : premier.y;
  const fin = H ? dernier.x + dernier.w : dernier.y + dernier.h;
  const somme = tri.reduce((s, p) => s + (H ? p.bbox.w : p.bbox.h), 0);
  const ecart = (fin - debut - somme) / (tri.length - 1);
  let pos = debut;
  for (const p of tri) {
    const actuel = H ? p.bbox.x : p.bbox.y;
    const d = pos - actuel;
    if (d) op_deplacer(doc, [p.id], H ? d : 0, H ? 0 : d);
    pos += (H ? p.bbox.w : p.bbox.h) + ecart;
  }
  return ecart;
}

export function op_rect_rayon(doc, ids, rayon) {
  const r = +rayon;
  if (!(r >= 0)) throw new Error("rayon: valeur ≥ 0 requise");
  let n = 0;
  for (const { objet } of _objetsCibles(doc, ids)) {
    if (objet.type !== "rect") continue;
    if (r === 0) delete objet.rx;
    else objet.rx = Math.min(r, Math.min(objet.w, objet.h) / 2);
    n++;
  }
  if (!n) throw new Error("aucun rectangle dans la sélection");
  return n;
}

export function op_guide_supprimer(doc, axe, i) {
  const g = _axeGuides(doc, axe);
  if (i < 0 || i >= g.length) throw new Error(`guide ${axe}[${i}] hors bornes`);
  g.splice(i, 1);
}

/* ── repères de page (lot A) : fond perdu et zone sûre — retraits [ox, oy]
   en px document depuis les bords. Dessinés par l'overlay (jamais
   compilés), aimantants (reperes_guides). Un nombre = retrait uniforme. */
const _CLES_REPERES = ["fondPerdu", "zoneSure"];

function _validerReperes(r, taille) {
  if (!r || typeof r !== "object" || Array.isArray(r)) {
    throw new Error("document: reperes {fondPerdu?, zoneSure?}");
  }
  for (const k of Object.keys(r)) {
    if (!_CLES_REPERES.includes(k)) throw new Error(`reperes: clé inconnue ${k}`);
    const v = r[k];
    if (!Array.isArray(v) || v.length !== 2 || !(v[0] >= 0) || !(v[1] >= 0)
        || v[0] >= taille.w / 2 || v[1] >= taille.h / 2) {
      throw new Error(`reperes.${k}: [ox, oy] ≥ 0 et sous la demi-page`);
    }
  }
}

export function op_reperes(doc, patch) {
  if (!patch || typeof patch !== "object") throw new Error("reperes: patch requis");
  const r = { ...(doc.reperes || {}) };
  for (const [k, v] of Object.entries(patch)) {
    if (!_CLES_REPERES.includes(k)) throw new Error(`reperes: clé inconnue ${k}`);
    if (v === null || v === undefined) { delete r[k]; continue; }
    r[k] = typeof v === "number" ? [v, v] : v;
  }
  _validerReperes(r, doc.taille);
  if (Object.keys(r).length) doc.reperes = r; else delete doc.reperes;
}

export function reperes_rects(doc) {
  const out = { fondPerdu: null, zoneSure: null };
  const r = doc.reperes || {};
  const W = +doc.taille.w, H = +doc.taille.h;
  for (const k of _CLES_REPERES) {
    if (r[k]) out[k] = { x: r[k][0], y: r[k][1], w: W - 2 * r[k][0], h: H - 2 * r[k][1] };
  }
  return out;
}

export function reperes_guides(doc) {
  const v = [], h = [];
  const rects = reperes_rects(doc);
  for (const k of _CLES_REPERES) {
    const b = rects[k];
    if (b) { v.push(b.x, b.x + b.w); h.push(b.y, b.y + b.h); }
  }
  return { v: [...new Set(v)].sort((a, b) => a - b), h: [...new Set(h)].sort((a, b) => a - b) };
}

/* ── image (lot A) : rognage et verrou d'objet. Ces deux commandes
   trouvent l'objet SANS passer par _objetsCibles — le verrou doit pouvoir
   se retirer. Rognage en px natifs, borné à l'image ; null = entière. */
function _trouverImage(doc, id) {
  for (const c of doc.calques) {
    const o = c.objets.find((x) => x.id === id);
    if (o) {
      if (o.type !== "image") throw new Error(`objet ${id}: pas une image`);
      return o;
    }
  }
  throw new Error(`image introuvable: ${id}`);
}

export function op_image_rogner(doc, id, rognage) {
  const o = _trouverImage(doc, id);
  if (rognage === null || rognage === undefined) { delete o.rognage; return; }
  _validerRognage(rognage, o.nat, `image ${id}`);
  o.rognage = { x: +rognage.x, y: +rognage.y, w: +rognage.w, h: +rognage.h };
}

export function op_image_verrou(doc, id, verrou) {
  const o = _trouverImage(doc, id);
  if (verrou) o.verrou = true; else delete o.verrou;
}

/* ── lot E (D1) : la RÉVISION raster d'un calque image — les pixels vivent
   dans le PNG (journal `.pix<k>.png` côté serveur), le JSON ne porte qu'un
   entier que le résolveur d'href ajoute en `?v=rev` pour casser le cache. */
export function op_image_rev(doc, id, rev) {
  const o = _trouverImage(doc, id);
  if (!(Number.isInteger(rev) && rev >= 0)) throw new Error(`image ${id}: rev entier ≥ 0`);
  if (rev > 0) o.rev = rev; else delete o.rev;
}

/* ── lot E : doc.pixelart = {tuile {w,h} entiers ≥ 1, palette [hex],
   symetrie {h, v}} — les réglages du mode pixel-art, tous optionnels. */
const _CLES_PIXELART = ["tuile", "palette", "symetrie"];
const _HEX = /^#[0-9A-Fa-f]{6}$/;
function _validerPixelart(p) {
  if (!p || typeof p !== "object" || Array.isArray(p)) throw new Error("document: pixelart {tuile?, palette?, symetrie?}");
  for (const k of Object.keys(p)) if (!_CLES_PIXELART.includes(k)) throw new Error(`pixelart: clé inconnue ${k}`);
  if (p.tuile !== undefined) {
    const t = p.tuile;
    if (!t || !(Number.isInteger(t.w) && t.w >= 1) || !(Number.isInteger(t.h) && t.h >= 1)) {
      throw new Error("pixelart.tuile: {w, h} entiers ≥ 1");
    }
  }
  if (p.palette !== undefined) {
    if (!Array.isArray(p.palette) || p.palette.some((c) => !_HEX.test(String(c)))) {
      throw new Error("pixelart.palette: liste de couleurs #RRGGBB");
    }
  }
  if (p.symetrie !== undefined && (!p.symetrie || typeof p.symetrie !== "object")) {
    throw new Error("pixelart.symetrie: {h, v}");
  }
}
export function op_pixelart(doc, patch) {
  if (!patch || typeof patch !== "object") throw new Error("pixelart: patch requis");
  const p = { ...(doc.pixelart || {}) };
  for (const [k, v] of Object.entries(patch)) {
    if (!_CLES_PIXELART.includes(k)) throw new Error(`pixelart: clé inconnue ${k}`);
    if (v === null || v === undefined) { delete p[k]; continue; }
    if (k === "tuile") p.tuile = { w: v.w, h: v.h };
    else if (k === "palette") p.palette = Array.isArray(v) ? v.map((c) => String(c).toUpperCase()) : v;
    else p.symetrie = { h: !!(v && v.h), v: !!(v && v.v) };
  }
  _validerPixelart(p);
  if (Object.keys(p).length) doc.pixelart = p; else delete doc.pixelart;
}

/* ── vectorisation (lot A, D6) : les chemins tracés se posent d'un coup
   dans un calque NEUF au-dessus — une commande, une entrée d'historique. */
export function op_vectoriser_poser(doc, objets, nom) {
  if (!Array.isArray(objets) || !objets.length) {
    throw new Error("rien à vectoriser (image vide ou seuil trop haut)");
  }
  const calqueId = op_calque_ajouter(doc, nom || "vectorisé");
  const ids = objets.map((o) => op_ajouter(doc, calqueId, { ...o, id: undefined }));
  return { calqueId, ids };
}


/* ── texte → chemins (lot D) : l'objet garde son id et son fond, perd sa
   fonte ; les glyphes à trous se peignent en evenodd ── */
export function op_texte_vectoriser(doc, id, d) {
  if (typeof d !== "string" || !d.trim()) {
    throw new Error("vectoriser : chemin vide (texte vide ou police muette)");
  }
  for (const c of doc.calques) {
    if (c.verrou) continue;
    const i = c.objets.findIndex((o) => o.id === id);
    if (i < 0) continue;
    const o = c.objets[i];
    if (o.type !== "texte") throw new Error(`${id}: pas un texte`);
    const s = { ...(o.style || {}) };
    for (const k of ["police", "corps", "graisse", "interlettrage"]) delete s[k];
    if (!s.fond || s.fond === "none") s.fond = s.contour || "#1F1512";
    c.objets[i] = { id: o.id, type: "path", d: chemin_serialiser(chemin_parser(d)),
                    style: { ...s, regle: "evenodd" },
                    ...(o.transform ? { transform: o.transform } : {}) };
    return o.id;
  }
  throw new Error(`texte introuvable (ou calque verrouillé): ${id}`);
}

/* ── grille du document (lot C) : une commande, un patch fusionné ── */
export function op_grille(doc, patch) {
  if (patch === null || patch === undefined) { delete doc.grille; return; }
  if (typeof patch !== "object") throw new Error("grille: patch objet requis");
  doc.grille = grille_normaliser({ ...(doc.grille || {}), ...patch });
}

/* ── tuiles (D3) : objets de premier rang ancrés à la grille hex ── */
export function tuile_a(doc, q, r) {
  for (const c of doc.calques) for (const o of c.objets) {
    if (o.type === "tuile" && o.q === q && o.r === r) return o;
  }
  return null;
}

// le pinceau : peint la tuile existante (calque déverrouillé), pose la
// manquante dans le calque cible — un geste = une commande
export function op_tuiles_peindre(doc, calqueId, cellules, terrain) {
  if (!Array.isArray(cellules) || !cellules.length) throw new Error("pinceau: aucune cellule");
  if (!terrains_de(doc)[terrain]) throw new Error(`pinceau: terrain inconnu ${terrain}`);
  const c = _calque(doc, calqueId);
  if (c.verrou) throw new Error(`calque verrouillé: ${calqueId}`);
  const peintes = [], posees = [], vues = new Set();
  for (const cel of cellules) {
    const k = cel.q + "," + cel.r;
    if (vues.has(k)) continue;
    vues.add(k);
    let existante = null, verrouillee = false;
    for (const cl of doc.calques) for (const o of cl.objets) {
      if (o.type === "tuile" && o.q === cel.q && o.r === cel.r) {
        existante = o; verrouillee = !!cl.verrou;
      }
    }
    if (existante) {
      if (verrouillee) continue;
      existante.terrain = terrain;
      peintes.push(existante.id);
    } else {
      posees.push(op_ajouter(doc, calqueId, { type: "tuile", q: cel.q, r: cel.r, terrain }));
    }
  }
  return { peintes, posees };
}

// le générateur : pose la grille hex (si absente, centrée sur la page) et
// un calque de tuiles ; numérotation axiale optionnelle dans un second calque
export function op_plateau_generer(doc, spec) {
  const terrain = spec.terrain || "plaine";
  if (!terrains_de(doc)[terrain]) throw new Error(`plateau: terrain inconnu ${terrain}`);
  const cellules = grille_cellules(spec);          // refuse les specs invalides
  if (!doc.grille || doc.grille.type !== "hex") {
    doc.grille = grille_normaliser({ type: "hex", pas: +spec.pas || 32,
      orientation: spec.orientation || "pointe",
      origine: [doc.taille.w / 2, doc.taille.h / 2] });
  }
  const calqueId = op_calque_ajouter(doc, spec.nom || "plateau");
  const tuiles = cellules.map((cel) =>
    op_ajouter(doc, calqueId, { type: "tuile", q: cel.q, r: cel.r, terrain }));
  const out = { calqueId, tuiles };
  if (spec.numeroter) {
    out.calqueNumeros = op_calque_ajouter(doc, "numéros");
    const g = doc.grille;
    for (const cel of cellules) {
      const [cx, cy] = hex_centre(cel.q, cel.r, g);
      op_ajouter(doc, out.calqueNumeros, { type: "texte", x: cx - g.pas * 0.45, y: cy + g.pas * 0.15,
        contenu: `${cel.q},${cel.r}`,
        style: { fond: "#1F1512", police: "Segoe UI", corps: Math.max(6, g.pas * 0.36) } });
    }
  }
  return out;
}

/* ── planches (lot C) : des cadres nommés, jamais compilés, aimantants ── */
export function planche_de(doc, id) {
  return (doc.planches || []).find((p) => p.id === id) || null;
}
export function op_planche_ajouter(doc, spec) {
  _validerCadre(spec, "planche");
  if (!doc.planches) doc.planches = [];
  const pris = new Set(doc.planches.map((p) => p.id));
  let n = 1;
  while (pris.has("p" + n)) n++;
  const id = "p" + n;
  doc.planches.push({ id, nom: String(spec.nom || `Planche ${n}`),
                      x: +spec.x, y: +spec.y, w: +spec.w, h: +spec.h });
  return id;
}
export function op_planche_modifier(doc, id, patch) {
  const p = planche_de(doc, id);
  if (!p) throw new Error(`planche inconnue: ${id}`);
  const neuf = { ...p, ...(patch || {}) };
  _validerCadre(neuf, `planche ${id}`);
  Object.assign(p, { nom: String(neuf.nom), x: +neuf.x, y: +neuf.y, w: +neuf.w, h: +neuf.h });
}
export function op_planche_supprimer(doc, id) {
  const p = planche_de(doc, id);
  if (!p) throw new Error(`planche inconnue: ${id}`);
  doc.planches.splice(doc.planches.indexOf(p), 1);
  if (!doc.planches.length) delete doc.planches;
}
export function planches_guides(doc) {
  const v = [], h = [];
  for (const p of doc.planches || []) { v.push(p.x, p.x + p.w); h.push(p.y, p.y + p.h); }
  return { v: [...new Set(v)].sort((a, b) => a - b), h: [...new Set(h)].sort((a, b) => a - b) };
}


/* ── cartes réelles (lot H) : doc.geo = {centre [lat, lon], m_par_px, zoom,
   emprise, emprise_px, attribution?, relief? {w, h, min, max, pasM,
   hauteurs[w·h]}} — les hauteurs sont des DONNÉES (pas des pixels) ── */
function _validerEmprise(e, ou) {
  if (!e || typeof e !== "object") throw new Error(`${ou}: emprise requise`);
  for (const k of ["minLat", "maxLat", "minLon", "maxLon"]) {
    if (!Number.isFinite(e[k])) throw new Error(`${ou}: emprise.${k} numérique`);
  }
  if (!(e.minLat <= e.maxLat) || !(e.minLon <= e.maxLon)) throw new Error(`${ou}: emprise inversée`);
}
function _validerRelief(r) {
  if (!r || typeof r !== "object") throw new Error("geo.relief: objet requis");
  if (!(Number.isInteger(r.w) && r.w >= 2 && Number.isInteger(r.h) && r.h >= 2)) {
    throw new Error("geo.relief: w et h entiers ≥ 2");
  }
  if (!Array.isArray(r.hauteurs) || r.hauteurs.length !== r.w * r.h) {
    throw new Error("geo.relief: hauteurs = w·h nombres");
  }
  if (!Number.isFinite(r.min) || !Number.isFinite(r.max) || !(r.pasM > 0)) {
    throw new Error("geo.relief: min, max, pasM > 0");
  }
}
function _validerGeo(g) {
  if (!g || typeof g !== "object") throw new Error("document: geo = objet");
  if (!Array.isArray(g.centre) || g.centre.length !== 2 || !g.centre.every(Number.isFinite)) {
    throw new Error("geo: centre [lat, lon]");
  }
  if (!(g.m_par_px > 0)) throw new Error("geo: m_par_px > 0");
  if (g.emprise !== undefined) _validerEmprise(g.emprise, "geo");
  if (g.emprise_px !== undefined) _validerCadre(g.emprise_px, "geo.emprise_px");
  if (g.relief !== undefined) _validerRelief(g.relief);
}

const _STYLE_TRACE = { fond: "none", contour: "#d0553a", epaisseur: 3 };
const _dDe = (pts) => "M " + pts.map(([x, y]) => `${nbc(x)} ${nbc(y)}`).join(" L ");

// gpx = sortie de gpx_parser, cadre = sortie de cadrage (vers_px)
export function op_geo_importer(doc, gpx, cadre) {
  if (!gpx || !(gpx.n > 0)) throw new Error("import GPX : aucun point");
  _validerEmprise(gpx.emprise, "import GPX");
  const e = gpx.emprise;
  const no = cadre.vers_px(e.maxLat, e.minLon), se = cadre.vers_px(e.minLat, e.maxLon);
  const emprise_px = { x: Math.min(no[0], se[0]), y: Math.min(no[1], se[1]),
                       w: Math.max(1, Math.abs(se[0] - no[0])), h: Math.max(1, Math.abs(se[1] - no[1])) };
  doc.geo = { centre: [cadre.centre[0], cadre.centre[1]], m_par_px: cadre.m_par_px,
              zoom: zoom_pour(e), emprise: { ...e }, emprise_px };
  const cEmp = op_calque_ajouter(doc, "emprise");
  op_ajouter(doc, cEmp, { type: "rect", ...emprise_px,
    style: { fond: "none", contour: "#39b3d0", epaisseur: 1, pointilles: "6 4" } });
  op_calque_verrou(doc, cEmp, true);
  const cTrace = op_calque_ajouter(doc, "trace");
  for (const t of gpx.traces) {
    if (t.length < 2) continue;
    op_ajouter(doc, cTrace, { type: "path", d: _dDe(t.map((p) => cadre.vers_px(p.lat, p.lon))),
                              style: { ..._STYLE_TRACE } });
  }
  const cPts = op_calque_ajouter(doc, "points");
  for (const p of gpx.points) {
    const [x, y] = cadre.vers_px(p.lat, p.lon);
    op_ajouter(doc, cPts, { type: "ellipse", cx: x, cy: y, rx: 5, ry: 5,
                            style: { fond: "#e0b34a", contour: "#1F1512", epaisseur: 1 } });
    if (p.nom) {
      op_ajouter(doc, cPts, { type: "texte", x: x + 8, y: y - 6, contenu: p.nom,
                              style: { fond: "#1F1512", police: "Segoe UI", corps: 14 } });
    }
  }
  return { calques: { emprise: cEmp, trace: cTrace, points: cPts }, nPoints: gpx.n };
}

export function op_geo_relief(doc, relief) {
  if (!doc.geo) throw new Error("relief : importer d'abord un GPX (doc.geo absent)");
  _validerRelief(relief);
  doc.geo.relief = { w: relief.w, h: relief.h, min: +relief.min, max: +relief.max, pasM: +relief.pasM,
                     hauteurs: relief.hauteurs.map((v) => Math.round(v * 10) / 10),
                     ...(relief.zoom !== undefined ? { zoom: relief.zoom } : {}) };
  if (relief.attribution) doc.geo.attribution = String(relief.attribution);
}

export function op_geo_courbes(doc, lignes_px, pas) {
  const lignes = (lignes_px || []).filter((l) => l && l.length >= 2);
  if (!lignes.length) throw new Error("courbes : aucune ligne à ce pas");
  const calqueId = op_calque_ajouter(doc, `courbes ${pas} m`);
  for (const l of lignes) {
    op_ajouter(doc, calqueId, { type: "path", d: _dDe(l),
      style: { fond: "none", contour: "#6b4a2b", epaisseur: 1 } });
  }
  return { calqueId, n: lignes.length };
}

// la découpe : un plateau hex couvrant l'emprise, chaque tuile prend le
// terrain de son palier d'altitude et une hauteur_mm proportionnelle
const _TERRAINS_PALIERS = ["mer", "plaine", "foret", "colline", "montagne"];
export function op_geo_tuiles(doc, spec = {}) {
  const geo = doc.geo;
  if (!geo || !geo.relief) throw new Error("tuiles : charger d'abord le relief");
  const pas = +spec.pas > 0 ? +spec.pas : 40;
  const relief_mm = +spec.relief_mm > 0 ? +spec.relief_mm : 10;
  const E = geo.emprise_px;
  const S3 = Math.sqrt(3);
  const colonnes = Math.max(1, Math.ceil(E.w / (S3 * pas)) + 1);
  const lignes = Math.max(1, Math.ceil(E.h / (1.5 * pas)) + 1);
  doc.grille = grille_normaliser({ type: "hex", pas, orientation: "pointe",
                                   origine: [E.x + pas * S3 / 2, E.y + pas] });
  const r = op_plateau_generer(doc, { mode: "rect", colonnes, lignes, terrain: "plaine",
                                      nom: spec.nom || "plateau relief" });
  const R = geo.relief;
  const bornes = paliers_bornes(R.min, R.max, _TERRAINS_PALIERS.length);
  const amplitude = Math.max(1e-9, R.max - R.min);
  const calque = _calque(doc, r.calqueId);
  const rayonGrille = Math.max(0.5, pas / E.w * (R.w - 1) * 0.6);
  for (const o of calque.objets) {
    const [cx, cy] = hex_centre(o.q, o.r, doc.grille);
    const gx = (cx - E.x) / E.w * (R.w - 1), gy = (cy - E.y) / E.h * (R.h - 1);
    const alt = echantillon_moyen(R.hauteurs, R.w, R.h, gx, gy, rayonGrille);
    if (alt === null) { o.terrain = "mer"; o.hauteur_mm = 0; continue; }
    o.terrain = _TERRAINS_PALIERS[palier(alt, bornes)];
    o.hauteur_mm = Math.round((alt - R.min) / amplitude * relief_mm * 10) / 10;
  }
  return { calqueId: r.calqueId, tuiles: r.tuiles, paliers: bornes };
}


/* ══════════ lot B : formes paramétriques, inclinaison, puissance, attribut,
   formules ══════════ */
function _trouverForme(doc, id) {
  for (const c of doc.calques) {
    if (c.verrou) continue;
    const o = c.objets.find((x) => x.id === id);
    if (o) {
      if (o.type !== "forme") throw new Error(`objet ${id}: pas une forme paramétrique`);
      return { calque: c, objet: o };
    }
  }
  throw new Error(`forme introuvable (ou calque verrouillé): ${id}`);
}
export function op_forme_param(doc, id, patch) {
  const { objet } = _trouverForme(doc, id);
  const neuf = { ...objet, ...(patch || {}), params: { ...objet.params, ...((patch || {}).params || {}) } };
  if (!(neuf.r > 0)) throw new Error("forme : rayon > 0 requis");
  forme_params_valider(neuf.forme, neuf.params);
  Object.assign(objet, neuf);
}
export function op_forme_en_chemin(doc, id) {
  const { calque, objet } = _trouverForme(doc, id);
  const d = forme_d(objet);
  const i = calque.objets.indexOf(objet);
  calque.objets[i] = { id: objet.id, type: "path", d, style: { ...(objet.style || {}) },
                       ...(objet.transform ? { transform: objet.transform } : {}) };
  return objet.id;
}

// inclinaison (skew) autour d'un pivot — composée devant, comme op_tourner
export function op_incliner(doc, ids, kx, ky, cx, cy) {
  const ax = +kx || 0, ay = +ky || 0;
  if (Math.abs(ax) >= 89 || Math.abs(ay) >= 89) throw new Error("inclinaison : angle sous 89°");
  if (!ax && !ay) return;
  const t = `translate(${nbc(cx)} ${nbc(cy)})` + (ax ? ` skewX(${nbc(ax)})` : "") + (ay ? ` skewY(${nbc(ay)})` : "")
          + ` translate(${nbc(-cx)} ${nbc(-cy)})`;
  for (const { objet } of _objetsCibles(doc, ids)) {
    objet.transform = objet.transform ? `${t} ${objet.transform}` : t;
  }
}

// la boîte GÉOMÉTRIQUE d'un objet (sans DOM) — pour la duplication puissance
function _bboxObjet(o, doc) {
  switch (o.type) {
    case "rect": case "image": case "cadre": return { x: o.x, y: o.y, w: o.w, h: o.h };
    case "instance": {
      const sym = doc && doc.symboles && doc.symboles[o.symbole];
      if (!sym) return { x: o.x, y: o.y, w: 0, h: 0 };
      const sx = o.sx === undefined ? 1 : o.sx, sy = o.sy === undefined ? 1 : o.sy;
      return { x: o.x + sym.bbox.x * sx, y: o.y + sym.bbox.y * sy, w: sym.bbox.w * sx, h: sym.bbox.h * sy };
    }
    case "ellipse": return { x: o.cx - o.rx, y: o.cy - o.ry, w: 2 * o.rx, h: 2 * o.ry };
    case "forme": return { x: o.cx - o.r * (o.sx || 1), y: o.cy - o.r * (o.sy || 1), w: 2 * o.r * (o.sx || 1), h: 2 * o.r * (o.sy || 1) };
    case "texte": return { x: o.x, y: o.y, w: 0, h: 0 };
    case "path": case "textechemin": {
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (const s of chemin_parser(o.d)) for (let k = 0; k < s.p.length; k += 2) {
        x0 = Math.min(x0, s.p[k]); x1 = Math.max(x1, s.p[k]); y0 = Math.min(y0, s.p[k + 1]); y1 = Math.max(y1, s.p[k + 1]);
      }
      return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
    }
    case "groupe": {
      const bs = (o.enfants || []).map((e) => _bboxObjet(e, doc)).filter(Boolean);
      if (!bs.length) return null;
      const x0 = Math.min(...bs.map((b) => b.x)), y0 = Math.min(...bs.map((b) => b.y));
      return { x: x0, y: y0, w: Math.max(...bs.map((b) => b.x + b.w)) - x0, h: Math.max(...bs.map((b) => b.y + b.h)) - y0 };
    }
    default: return null;
  }
}
// duplication puissance : n copies, chacune répétant la transformation
// (décalage, rotation cumulée, échelle cumulée autour de son centre)
export function op_dupliquer_puissance(doc, ids, n, pas = {}) {
  const N = +n;
  if (!(Number.isInteger(N) && N >= 1 && N <= 200)) throw new Error("puissance : n entier de 1 à 200");
  const dx = +pas.dx || 0, dy = +pas.dy || 0, rot = +pas.rotation || 0, ech = pas.echelle === undefined ? 1 : +pas.echelle;
  if (!(ech > 0)) throw new Error("puissance : échelle > 0");
  let sources = ids.slice();
  const out = [];
  for (let k = 1; k <= N; k++) {
    const neufs = op_dupliquer(doc, sources, dx, dy);
    for (const id of neufs) {
      const t = [..._objetsCibles(doc, [id])][0];
      if (!t) continue;
      const b = _bboxObjet(t.objet);
      if (b && b.w > 0 && b.h > 0 && ech !== 1) {
        const cx = b.x + b.w / 2, cy = b.y + b.h / 2;
        op_redimensionner(doc, [id], b, { x: cx - b.w * ech / 2, y: cy - b.h * ech / 2, w: b.w * ech, h: b.h * ech });
      }
      if (rot) {
        const b2 = _bboxObjet(t.objet) || b || { x: 0, y: 0, w: 0, h: 0 };
        // la rotation se cumule : la k-ième copie tourne de k × rot, sans hériter
        t.objet.transform = undefined;
        delete t.objet.transform;
        op_tourner(doc, [id], b2.x + b2.w / 2, b2.y + b2.h / 2, rot * k);
      }
    }
    out.push(...neufs);
    sources = neufs;
  }
  return out;
}

// sélection par attribut : les objets (calques déverrouillés) qui partagent
// une valeur avec la référence — fond, contour, epaisseur ou type
const _ATTRIBUTS = new Set(["fond", "contour", "epaisseur", "type"]);
export function selection_par_attribut(doc, refId, cle) {
  if (!_ATTRIBUTS.has(cle)) throw new Error(`attribut inconnu : ${cle}`);
  let ref = null;
  for (const c of doc.calques) { const o = c.objets.find((x) => x.id === refId); if (o) ref = o; }
  if (!ref) throw new Error(`référence introuvable : ${refId}`);
  const val = (o) => cle === "type" ? o.type : (o.style || {})[cle];
  const cible = val(ref);
  const out = [];
  for (const c of doc.calques) {
    if (c.verrou) continue;
    for (const o of c.objets) if (val(o) === cible && !o.verrou) out.push(o.id);
  }
  return out;
}

// les FORMULES du panneau : « +50% », « *2 », « 10+5 », « 42 » — relatif si
// l'entrée commence par un opérateur, absolu sinon ; jamais d'évaluation libre
export function formule(valeur, texte) {
  const t = String(texte ?? "").trim().replace(/,/g, ".");
  if (!t) throw new Error("formule : vide");
  if (!/^[0-9+\-*/(). %]+$/.test(t)) throw new Error("formule : caractères non numériques");
  if (/\*\*|\/\/|%[0-9(]/.test(t)) throw new Error("formule : opérateur inconnu");
  const evaluer = (expr) => {
    const e = expr.replace(/%/g, "");
    if (!/^[0-9+\-*/(). ]+$/.test(e) || !/[0-9]/.test(e)) throw new Error("formule : illisible");
    let v;
    try { v = Function(`"use strict"; return (${e});`)(); } catch { throw new Error("formule : illisible"); }
    if (!Number.isFinite(v)) throw new Error("formule : résultat non fini");
    return v;
  };
  const op = t[0];
  if ("+-*/".includes(op) && t.length > 1) {
    const reste = t.slice(1).trim();
    const pourcent = reste.endsWith("%");
    const v = evaluer(reste);
    if (op === "+") return pourcent ? valeur * (1 + v / 100) : valeur + v;
    if (op === "-") return pourcent ? valeur * (1 - v / 100) : valeur - v;
    if (pourcent) throw new Error("formule : % seulement avec + ou −");
    if (op === "*") return valeur * v;
    if (v === 0) throw new Error("formule : division par zéro");
    return valeur / v;
  }
  const v = evaluer(t);
  return t.endsWith("%") ? valeur * v / 100 : v;
}


function _defs(doc, ctx = {}) {
  const refs = [], motifs = [], masques = [], filtres = [], clips = [], symboles = [];
  const vus = new Set(), vusM = new Set(), vusK = new Set(), vusS = new Set();
  const visiter = (objs) => {
    for (const o of objs) {
      const s = o.style || {};
      const f = s.fond;
      if (typeof f === "string" && f.startsWith("grad:")) {
        const gid = f.slice(5);
        if (!vus.has(gid)) { vus.add(gid); refs.push(gid); }
      }
      if (typeof f === "string" && f.startsWith("motif:")) {
        const mid = f.slice(6);
        if (!vusM.has(mid)) { vusM.add(mid); motifs.push(mid); }
      }
      if (typeof s.masque === "string") {
        const gid = s.masque.slice(5);
        if (!vus.has(gid)) { vus.add(gid); refs.push(gid); }
        if (!vusK.has(gid)) { vusK.add(gid); masques.push(gid); }
      }
      if (s.effets && s.effets.length) filtres.push(filtre_svg(`fx_${o.id}`, s.effets));
      if (o.type === "instance" && doc.symboles && doc.symboles[o.symbole] && !vusS.has(o.symbole)) {
        vusS.add(o.symbole);
        symboles.push(`<g id="sym_${escAttr(o.symbole)}">` + doc.symboles[o.symbole].objets.map((e) => compilerObjet(e, { ...ctx, sansId: true })).join("") + `</g>`);
      }
      if (o.type === "groupe") {
        if (o.clip) {
          const conteneur = (o.enfants || []).find((e) => e.id === o.clip);
          if (conteneur) clips.push(`<clipPath id="clip_${escAttr(o.id)}">` + compilerObjet({ ...conteneur, style: {} }, { ...ctx, sansId: true }) + `</clipPath>`);
        }
        visiter(o.enfants || []);
      }
    }
  };
  for (const c of doc.calques) visiter(c.objets);
  const degs = doc.degrades || {}, mots = doc.motifs || {};
  const morceaux = [];
  for (const id of refs) {
    const g = degs[id];
    if (!g) continue;                 // référence orpheline: le repli "none"
    if (g.type === "conique") {       // lot F : secteurs interpolés en <pattern>
      morceaux.push(conique_svg(id, { ...g, stops: g.stops.map((s) => ({ ...s, couleur: _couleur(s.couleur, ctx) })) }));
      continue;
    }
    const stops = [...g.stops].sort((a, b) => a.t - b.t).map((s) =>
      `<stop offset="${+s.t}" stop-color="${escAttr(_couleur(s.couleur, ctx))}"`
      + ((s.opacite !== undefined && +s.opacite !== 1)
         ? ` stop-opacity="${+s.opacite}"` : "") + `/>`).join("");
    morceaux.push(g.type === "lineaire"
      ? `<linearGradient id="${escAttr(id)}" gradientUnits="userSpaceOnUse"`
        + ` x1="${+g.x1}" y1="${+g.y1}" x2="${+g.x2}" y2="${+g.y2}">`
        + stops + `</linearGradient>`
      : `<radialGradient id="${escAttr(id)}" gradientUnits="userSpaceOnUse"`
        + ` cx="${+g.cx}" cy="${+g.cy}" r="${+g.r}">`
        + stops + `</radialGradient>`);
  }
  // le masque de transparence : un rect plein-page peint par le dégradé (luminance)
  const { w, h } = doc.taille;
  for (const id of masques) {
    if (!degs[id]) continue;
    morceaux.push(`<mask id="m_${escAttr(id)}"><rect x="0" y="0" width="${+w}" height="${+h}" fill="url(#${escAttr(id)})"/></mask>`);
  }
  for (const id of motifs) if (mots[id]) morceaux.push(motif_svg(id, { ...mots[id], couleur: _couleur(mots[id].couleur, ctx), fond: mots[id].fond ? _couleur(mots[id].fond, ctx) : undefined }));
  morceaux.push(...symboles, ...filtres, ...clips);
  return morceaux.length ? `<defs>${morceaux.join("")}</defs>` : "";
}

export function compilerSVG(doc, opts = {}) {
  parserDoc(doc);
  const ctx = { degrades: doc.degrades || {}, image: opts.image, motifs: doc.motifs || {},
                globales: doc.couleursGlobales || {}, mesure: opts.mesure,
                grille: _grilleHex(doc), terrains: terrains_de(doc) };
  const w = +doc.taille.w, h = +doc.taille.h;
  // lot C : un cadre (planche) devient le viewBox — le fond reste celui de
  // la page entière, le viewBox rogne
  let cadre = { x: 0, y: 0, w, h };
  if (opts.cadre) { _validerCadre(opts.cadre, "cadre"); cadre = opts.cadre; }
  const fond = doc.fond
    ? `<rect x="0" y="0" width="${w}" height="${h}"`
      + ` fill="${escAttr(doc.fond)}" data-fond="1"/>`
    : "";
  const calques = doc.calques.map((c) => {
    const cache = c.visible === false ? ` style="display:none"` : "";
    const op = (c.opacite !== undefined && Number(c.opacite) !== 1)
      ? ` opacity="${Number(c.opacite)}"` : "";
    return `<g data-calque="${escAttr(c.id)}"`
         + ` data-nom="${escAttr(c.nom || "")}"${op}${cache}>`
         + c.objets.map((o) => compilerObjet(o, ctx)).join("") + `</g>`;
  }).join("");
  return `<svg xmlns="http://www.w3.org/2000/svg"`
       + ` viewBox="${+cadre.x} ${+cadre.y} ${+cadre.w} ${+cadre.h}"`
       + ` width="${+cadre.w}" height="${+cadre.h}">`
       + _defs(doc, ctx) + fond + calques + `</svg>`;
}
