// mod-flyout.js — les menus DÉTACHÉS de la barre d'outils de gauche : un
// bouton à menu porte une marque d'angle ; clic droit, clic sur l'angle ou
// appui long ouvre le menu à côté du bouton (un seul à la fois, Échap ou
// clic dehors le ferme). Un menu par outil dont le panneau porte des choix
// ou des actions fréquentes : Forme, Symboles, Sélection, Nœuds, Texte,
// Crayon / Pinceau vectoriel, Gomme, Coin, Tuiles, Pixel (pinceau, gomme,
// seau, baguette, sélections), Tranche. Les actions DÉLÈGUENT aux
// commandes et aux boutons des panneaux existants — rien de nouveau au
// modèle. La partie haute (bâtisseurs, registre) est PURE.
import { FORMES } from "./mod-formes.js";
import { op_symbole_creer, op_instance_poser, op_style, terrains_de } from "./mod-doc.js";
import { PROFILS } from "./mod-pinceauvec.js";
import { MODES } from "./mod-tranches.js";

/* ── bâtisseurs purs ── */
const GLYPHES = { polygone: "⬠", hexagone: "⬡", etoile: "☆", engrenage: "⚙", fleche: "➜", donut: "◎", spirale: "๑" };
export function flyout_formes(formes, courante) {
  return (formes || []).map((f) => ({ id: f.id, libelle: f.nom, glyphe: GLYPHES[f.id] || "◇", actif: f.id === courante }));
}
export function flyout_symboles(symboles) {
  const entrees = Object.entries(symboles || {}).map(([id, s]) => ({ id, libelle: s.nom || id, detail: `${(s.objets || []).length} objet${(s.objets || []).length > 1 ? "s" : ""}`, action: "poser" }));
  if (!entrees.length) entrees.push({ id: "", libelle: "aucun symbole", detail: "", action: "", desactive: true });
  entrees.push({ id: "", libelle: "Créer depuis la sélection", detail: "", action: "creer" });
  return entrees;
}
export function flyout_choix(liste, courant, { glyphes = {} } = {}) {
  return (liste || []).map((x) => ({ id: x.id, libelle: x.nom || x.libelle || x.id, glyphe: glyphes[x.id] || "", actif: x.id === courant, action: "choix" }));
}
export function flyout_presets(valeurs, courante, unite = "") {
  const vals = (valeurs || []).slice();
  if (courante !== undefined && courante !== null && !vals.includes(courante)) vals.unshift(courante);
  return vals.map((v) => ({ id: String(v), valeur: v, libelle: `${v}${unite ? " " + unite : ""}`, actif: v === courante, action: "preset" }));
}
export function flyout_terrains(terrains, courant) {
  return Object.entries(terrains || {}).map(([id, f]) => ({ id, libelle: f.nom || id, couleur: f.couleur, detail: `${+f.hauteur_mm || 0} mm`, actif: id === courant, action: "choix" }));
}
export function flyout_polices(polices, courante) {
  const src = { lib: "bibliothèque", user: "déposée", systeme: "système" };
  return (polices || []).map((p) => ({ id: p.id, libelle: p.famille, famille: p.famille, detail: src[p.source] || "", actif: p.famille === courante, action: "police" }));
}
export function flyout_actions(liste, disponible = () => true) {
  return (liste || []).map((a) => ({ id: a.id, libelle: a.libelle, glyphe: a.glyphe || "", cible: a.cible, action: "cible", desactive: !disponible(a.cible) }));
}
// réglages de style : chaque valeur porte son patch {cle: v} (ou f(v))
export function flyout_reglages(valeurs, courante, cle, unite = "", f = (v) => v) {
  return (valeurs || []).map((v) => ({ id: `${cle}-${v}`, valeur: v, libelle: `${v}${unite ? " " + unite : ""}`, actif: v === courante, action: "style", patch: { [cle]: f(v) } }));
}
export function flyout_position(bouton, taille, fenetre, marge = 6) {
  let x = bouton.x + bouton.w + marge;
  if (x + taille.w > fenetre.w - marge) x = bouton.x - marge - taille.w;
  let y = bouton.y;
  if (y + taille.h > fenetre.h - marge) y = Math.max(marge, fenetre.h - marge - taille.h);
  return { x, y };
}

/* ── registre : outil → {titre, entrees, choisir(entree)} — `c` = contexte
   {etat, existe(sel), cliquer(sel), setOutil, executer, toast, rendre} ── */
const AL = [["gauche", "⇤ Aligner à gauche"], ["centreH", "⇔ Centrer horizontalement"], ["droite", "⇥ Aligner à droite"], ["haut", "⇧ Aligner en haut"], ["centreV", "⇕ Centrer verticalement"], ["bas", "⇩ Aligner en bas"]];
const ORDRE = [["devant", "⤒ Tout devant"], ["avant", "↑ Un cran devant"], ["arriere", "↓ Un cran derrière"], ["derriere", "⤓ Tout derrière"]];
const BOOL = [["union", "∪ Union"], ["soustraction", "⊖ Soustraction"], ["intersection", "∩ Intersection"], ["division", "⧉ Division"]];
export const MENUS = {
  forme: (c) => ({ titre: "Forme paramétrique", entrees: flyout_formes(FORMES, c.etat.formeCourante), choisir: (e) => {
    c.etat.formeCourante = e.id; c.setOutil("forme"); c.toast(`forme « ${e.libelle} » : cliquer pour la poser (rayon 40) ou glisser depuis le centre`); c.rendre(); } }),
  symbole: (c) => ({ titre: "Symboles", entrees: flyout_symboles(c.etat.doc && c.etat.doc.symboles), choisir: (e) => {
    if (e.action === "poser") { const id = c.executer(op_instance_poser, c.etat.calqueActif, e.id, 24, 24); if (id) { c.setOutil("select"); c.selectionner([id]); } }
    else if (e.action === "creer") {
      if (!c.etat.selection.length) { c.toast("sélectionner d'abord les objets du symbole", true); return; }
      const sid = c.executer(op_symbole_creer, c.etat.selection.slice(), undefined);
      if (sid) c.toast(`symbole ${sid} créé — le menu Symboles le pose`);
    } } }),
  select: (c) => ({ titre: "Sélection", entrees: flyout_actions([
    ...AL.map(([k, l]) => ({ id: "al-" + k, libelle: l, cible: `#panneauStyle [data-al="${k}"]` })),
    ...ORDRE.map(([k, l]) => ({ id: "or-" + k, libelle: l, cible: `#panneauStyle [data-ordre="${k}"]` })),
    { id: "grouper", libelle: "Grouper", cible: "#apGrouper" }, { id: "degrouper", libelle: "Dégrouper", cible: "#apDegrouper" },
    ...BOOL.map(([k, l]) => ({ id: "bo-" + k, libelle: l, cible: `#panneauStyle [data-bool="${k}"]` })),
  ], (sel) => c.etat.selection.length > 0 && c.existe(sel)), choisir: (e) => c.cliquer(e.cible) }),   // rien de sélectionné : tout est désactivé
  noeuds: (c) => ({ titre: "Nœuds", entrees: flyout_actions([
    { id: "diviser", libelle: "Diviser le segment", cible: "#ndDiviser" }, { id: "inverser", libelle: "Inverser le sens", cible: "#ndInverser" },
    { id: "joindre", libelle: "Joindre deux chemins", cible: "#ndJoindre" }, { id: "coins", libelle: "Arrondir les coins", cible: "#ndCoins" },
  ], c.existe), choisir: (e) => c.cliquer(e.cible) }),
  texte: (c) => {
    const t = c.etat.typo || { polices: [], courante: "" };
    const sel = c.etat.selection.length === 1 ? c.objetDe(c.etat.selection[0]) : null;
    const courante = sel && sel.objet.type === "texte" ? (sel.objet.style || {}).police : (t.polices.find((p) => p.id === t.courante) || {}).famille;
    return { titre: "Typographies", entrees: [...flyout_polices(t.polices, courante), { id: "deposer", libelle: "⬆ Déposer une police…", action: "deposer" }], choisir: (e) => {
      if (e.action === "deposer") { c.cliquer("#txDeposer") || c.toast("ouvrir le panneau Texte pour déposer une police", true); return; }
      c.etat.typo.courante = e.id;
      if (sel && (sel.objet.type === "texte" || sel.objet.type === "cadre")) c.style([sel.objet.id], { police: e.famille });
      else { c.setOutil("texte"); c.rendre(); }
    } };
  },
  crayon: (c) => MENUS.pinceauv(c),
  pinceauv: (c) => {
    const pv = c.etat.pinceauv || { profil: "fuseau", largeur: 8 };
    return { titre: "Pinceau vectoriel", entrees: [...flyout_choix(PROFILS, pv.profil, { glyphes: { plat: "▬", fuseau: "◆", calligraphie: "✒" } }), ...flyout_presets([4, 8, 16, 24], pv.largeur, "px")], choisir: (e) => {
      if (e.action === "choix") pv.profil = e.id; else pv.largeur = e.valeur;
      c.setOutil("pinceauv"); c.rendre();
    } };
  },
  gomme: (c) => ({ titre: "Gomme vectorielle", entrees: flyout_presets([6, 12, 24, 48], c.etat.gommeLargeur, "px"), choisir: (e) => { c.etat.gommeLargeur = e.valeur; c.setOutil("gomme"); c.rendre(); } }),
  coin: (c) => ({ titre: "Coins arrondis", entrees: flyout_presets([5, 10, 20, 40], c.etat.coinRayon, "px"), choisir: (e) => { c.etat.coinRayon = e.valeur; c.setOutil("coin"); c.rendre(); } }),
  tuiles: (c) => ({ titre: "Terrains", entrees: [...flyout_terrains(c.etat.doc ? terrains_de(c.etat.doc) : {}, c.etat.terrainCourant), { id: "plateau", libelle: "⬡ Générer le plateau…", action: "plateau" }], choisir: (e) => {
    if (e.action === "plateau") { c.ouvrirSection("plateauDetails"); return; }
    c.etat.terrainCourant = e.id; c.setOutil("tuiles"); c.rendre(); } }),
  "px-pinceau": (c) => MENUS._pxPinceau(c, "px-pinceau"),
  "px-gomme": (c) => MENUS._pxPinceau(c, "px-gomme"),
  _pxPinceau: (c, outil) => {
    const px = c.etat.px || { rayon: 4, durete: 1 };
    return { titre: outil === "px-gomme" ? "Gomme raster" : "Pinceau raster", entrees: [...flyout_presets([1, 2, 4, 8, 16], px.rayon, "px"),
      { id: "nette", libelle: "Dureté nette", action: "durete", valeur: 1, actif: px.durete >= 1 }, { id: "douce", libelle: "Dureté douce", action: "durete", valeur: 0.3, actif: px.durete < 1 }], choisir: (e) => {
      if (e.action === "preset") px.rayon = e.valeur; else px.durete = e.valeur;
      c.setOutil(outil); c.rendre();
    } };
  },
  "px-seau": (c) => MENUS._pxTolerance(c, "px-seau"),
  "px-baguette": (c) => MENUS._pxTolerance(c, "px-baguette"),
  _pxTolerance: (c, outil) => {
    const px = c.etat.px || { tolerance: 16, global: false };
    return { titre: outil === "px-seau" ? "Seau" : "Baguette magique", entrees: [...flyout_presets([0, 16, 48, 96], px.tolerance, "de tolérance"),
      ...(outil === "px-seau" ? [{ id: "global", libelle: "Global (tous les pixels semblables)", action: "global", actif: !!px.global }] : [])], choisir: (e) => {
      if (e.action === "preset") px.tolerance = e.valeur; else px.global = !px.global;
      c.setOutil(outil); c.rendre();
    } };
  },
  "px-selrect": (c) => MENUS._pxSelection(c, "px-selrect"),
  "px-lasso": (c) => MENUS._pxSelection(c, "px-lasso"),
  _pxSelection: (c, outil) => ({ titre: "Sélection raster", entrees: flyout_actions([
    { id: "tout", libelle: "Tout", cible: "#pxSelTout" }, { id: "aucune", libelle: "Aucune", cible: "#pxSelAucune" }, { id: "inverser", libelle: "Inverser", cible: "#pxSelInv" },
    { id: "croitre", libelle: "Croître d'un pixel", cible: "#pxSelPlus" }, { id: "contracter", libelle: "Contracter d'un pixel", cible: "#pxSelMoins" }, { id: "couleur", libelle: "Par couleur courante", cible: "#pxSelCouleur" },
  ], c.existe), choisir: (e) => { c.setOutil(outil); c.cliquer(e.cible); } }),
  image: (c) => {
    const sel = c.etat.selection.length === 1 ? c.objetDe(c.etat.selection[0]) : null, img = sel && sel.objet.type === "image";
    return { titre: "Image", entrees: [
      ...flyout_actions([
        { id: "biblio", libelle: "📚 Bibliothèque…", cible: "#imgBiblio" }, { id: "fichier", libelle: "⬆ Fichier…", cible: "#imgFichier" },
        { id: "coller", libelle: "📋 Presse-papiers", cible: "#imgColler" }, { id: "generer", libelle: "✦ Générer…", cible: "#imgGenerer" },
      ], c.existe),
      ...flyout_actions([
        { id: "vectoriser", libelle: "◇ Vectoriser cette image…", cible: "#imVectoriser" }, { id: "entiere", libelle: "↺ Image entière (sans rognage)", cible: "#imRognerRaz" },
        { id: "verrou", libelle: img && sel.objet.verrou ? "🔓 Déverrouiller" : "🔒 Verrouiller", cible: "#imVerrou" },
      ], (cible) => img && c.existe(cible)),
      { id: "pixels", libelle: "🖌 Éditer les pixels (persona Pixel)", action: "pixels", desactive: !img },
    ], choisir: (e) => { if (e.action === "pixels") c.pixels(); else c.cliquer(e.cible); } };
  },
  apparence: (c) => {
    const sel = c.etat.selection.length === 1 ? c.objetDe(c.etat.selection[0]) : null;
    const s = sel ? (sel.objet.style || {}) : (c.etat.styleCourant || {});
    const n = c.etat.selection.length;
    return { titre: "Apparence", entrees: [
      ...flyout_actions([{ id: "fond", libelle: "■ Couleur de fond…", cible: "#apFond" }, { id: "sansfond", libelle: "∅ Sans fond", cible: "#apFondAucun" },
        { id: "contour", libelle: "□ Couleur de contour…", cible: "#apContour" }, { id: "sanscontour", libelle: "∅ Sans contour", cible: "#apContourAucun" }], c.existe),
      ...flyout_reglages([1, 2, 4, 8], +s.epaisseur || 2, "epaisseur", "px d'épaisseur"),
      ...flyout_reglages([100, 75, 50, 25], Math.round((s.opacite ?? 1) * 100), "opacite", "% d'opacité", (v) => v / 100),
      ...flyout_actions([{ id: "gradl", libelle: "▤ Dégradé linéaire", cible: "#apGradL" }, { id: "gradr", libelle: "◉ Dégradé radial", cible: "#apGradR" },
        { id: "conique", libelle: "◔ Dégradé conique", cible: "#a2Conique" }, { id: "transp", libelle: "◧ Transparence", cible: "#a2Transp" },
        { id: "motif", libelle: "▦ Motif", cible: "#a2Motif" }], (cible) => n >= 1 && c.existe(cible)),
      { id: "ombre", libelle: "☁ Effet : ombre externe", action: "effet", valeur: "ombre", desactive: !n }, { id: "lueur", libelle: "✺ Effet : lueur", action: "effet", valeur: "lueur", desactive: !n },
    ], choisir: (e) => {
      if (e.action === "style") c.style(c.etat.selection.slice(), e.patch);
      else if (e.action === "effet") { const sel2 = document.querySelector("#a2FxType"); if (sel2) { sel2.value = e.valeur; c.cliquer("#a2FxPlus"); } }
      else c.cliquer(e.cible);
    } };
  },
  tranche: (c) => {
    const ex = c.etat.exportPlus || { mode: "document" };
    return { titre: "Tranches d'export", entrees: [...flyout_choix(MODES, ex.mode).map((e) => ({ ...e, libelle: e.libelle })), { id: "effacer", libelle: "✕ Effacer les tranches dessinées", action: "effacer", desactive: !(c.etat.tranches || []).length }], choisir: (e) => {
      if (e.action === "effacer") { c.etat.tranches = []; c.rendre(); return; }
      ex.mode = e.id; if (e.id === "dessinees") c.setOutil("tranche"); c.rendre();
    } };
  },
};

/* ── UI ── */
export function initFlyout(VL) {
  const { $, etat } = VL;
  const hote = document.createElement("div");
  hote.id = "flyout"; hote.hidden = true;
  document.body.appendChild(hote);
  let ouvertPour = null, timerLong = 0;
  const esc = (v) => String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  function fermer() { hote.hidden = true; hote.innerHTML = ""; ouvertPour = null; }
  const ctx = {
    etat, setOutil: VL.setOutil, executer: VL.executer, toast: VL.toast, selectionner: VL.setSelection, objetDe: VL.objetDe,
    existe: (sel) => { const b = $(sel); return !!b && !b.disabled; },
    cliquer: (sel) => { const b = $(sel); if (!b || b.disabled) return false; b.click(); return true; },
    style: (ids, patch) => { if (ids.length) VL.executer(op_style, ids, patch); else { Object.assign(etat.styleCourant, patch); VL.surSelection(); } },
    pixels: () => { if (VL.setPersona) VL.setPersona("pixel"); setTimeout(() => { const b = $("#pxEditer"); if (b && !b.disabled) b.click(); }, 60); },
    rendre: () => { if (etat.doc) { VL.rendre(); } },
    ouvrirSection: (id) => { const d = $("#" + id); if (d) { d.open = true; d.scrollIntoView({ block: "start" }); } },
  };
  function ouvrir(bouton, nom) {
    if (ouvertPour === bouton) { fermer(); return; }
    fermer();
    const menu = MENUS[nom](ctx);
    ouvertPour = bouton;
    hote.innerHTML = `<div class="fo-titre">${esc(menu.titre)}</div>` + menu.entrees.map((e, i) =>
      `<button class="fo-item${e.actif ? " actif" : ""}" data-i="${i}" ${e.desactive ? "disabled" : ""}${e.famille ? ` style="font-family:&quot;${esc(e.famille)}&quot;"` : ""}>`
      + (e.couleur ? `<span class="fo-pastille" style="background:${esc(e.couleur)}"></span>` : e.glyphe ? `<span class="fo-glyphe">${e.glyphe}</span>` : "")
      + `<span class="fo-lib">${esc(e.libelle)}</span>${e.detail ? `<small>${esc(e.detail)}</small>` : ""}</button>`).join("");
    hote.hidden = false;
    const r = bouton.getBoundingClientRect();
    const p = flyout_position({ x: r.left, y: r.top, w: r.width, h: r.height }, { w: hote.offsetWidth, h: hote.offsetHeight }, { w: window.innerWidth, h: window.innerHeight }, 6);
    hote.style.left = p.x + "px"; hote.style.top = p.y + "px";
    hote.querySelectorAll(".fo-item").forEach((b) => b.addEventListener("click", () => { const e = menu.entrees[+b.dataset.i]; fermer(); menu.choisir(e); }));
  }
  // les boutons Image et Apparence (persona Vecteur) — ils ne sont que des menus
  for (const [nom, glyphe, titre] of [["image", "🖼", "Image — poser (Bibliothèque, fichier, presse-papiers, génération), vectoriser, rogner, verrou, pixels (menu)"], ["apparence", "🎨", "Apparence — fond, contour, épaisseur, opacité, dégradés, motif, effets (menu)"]]) {
    const b = document.createElement("button");
    b.dataset.outil = nom; b.dataset.menu = nom; b.title = titre; b.textContent = glyphe;
    b.addEventListener("click", (ev) => { ev.stopPropagation(); ouvrir(b, nom); });
    $("#outils").appendChild(b);
  }
  // le bouton Symboles (persona Vecteur) — il n'est qu'un menu
  {
    const b = document.createElement("button");
    b.dataset.outil = "symbole"; b.dataset.menu = "symbole"; b.title = "Symboles — poser une instance ou créer un symbole depuis la sélection (menu)"; b.textContent = "⧈";
    b.addEventListener("click", (ev) => { ev.stopPropagation(); ouvrir(b, "symbole"); });
    $("#outils").appendChild(b);
  }
  function armer(b) {
    if (b.dataset.arme) return;
    b.dataset.arme = "1"; b.classList.add("a-menu");
    b.addEventListener("contextmenu", (ev) => { ev.preventDefault(); ouvrir(b, b.dataset.menu); });
    b.addEventListener("pointerdown", (ev) => {
      if (ev.button !== 0) return;
      const r = b.getBoundingClientRect();
      if (ev.clientX > r.right - 12 && ev.clientY > r.bottom - 12) { ev.preventDefault(); ev.stopPropagation(); ouvrir(b, b.dataset.menu); b.dataset.angle = "1"; return; }
      timerLong = setTimeout(() => { ouvrir(b, b.dataset.menu); b.dataset.angle = "1"; }, 400);
    });
    b.addEventListener("pointerup", () => clearTimeout(timerLong));
    b.addEventListener("pointerleave", () => clearTimeout(timerLong));
    b.addEventListener("click", (ev) => { if (b.dataset.angle) { delete b.dataset.angle; ev.stopImmediatePropagation(); ev.preventDefault(); } }, true);
  }
  // tous les boutons dont l'outil a un menu — y compris ceux ajoutés par les modules
  for (const b of document.querySelectorAll("#outils button[data-outil]")) {
    const nom = b.dataset.menu || (MENUS[b.dataset.outil] && !b.dataset.outil.startsWith("_") ? b.dataset.outil : null);
    if (nom && !["symbole", "image", "apparence"].includes(nom)) { b.dataset.menu = nom; armer(b); }
  }
  document.addEventListener("pointerdown", (ev) => { if (!hote.hidden && !hote.contains(ev.target) && !(ouvertPour && ouvertPour.contains(ev.target))) fermer(); }, true);
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !hote.hidden) { fermer(); ev.stopImmediatePropagation(); } }, true);
  VL.flyout = { ouvrir: (nom) => ouvrir($(`#outils [data-menu="${nom}"]`) || $(`#outils [data-outil="${nom}"]`), nom), fermer, element: hote, menus: Object.keys(MENUS).filter((k) => !k.startsWith("_")) };   // la preuve
}
