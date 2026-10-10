// mod-couches.js — t153 (parité L3) : le panneau Couches, onglet du groupe Calques.
// Liste lue dans doc.inspect.channels (= channel.list) : composite, couleurs, alpha. Œil = channel.setVisible, clic =
// channel.target (hors historique), Ctrl+clic = select.loadSelection (Maj = ajouter, Alt = soustraire, Maj+Alt =
// intersection), double-clic sur une alpha = channel.rename ; pied : charger, enregistrer la sélection, nouvelle,
// supprimer. Ctrl+2 (composite), Ctrl+3… (couleurs puis alpha, jusqu'à 9).
// doc.render rend TOUJOURS le composite (relevé t153) : la vue d'une ou deux couches est composée ici, à l'affichage,
// à partir du rendu (PL.vue.filtre) — une couche seule en niveaux de gris, plusieurs couleurs = les autres à zéro, une
// alpha visible = recouvrement de sa couleur ; le contenu des alpha vient de /couches (copie rendue par le pont).
// Fonctions PURES exportées (qa/panneaux3.test.mjs).

import { demanderNom } from "./mod-nommer.js";

const COULEURS = ["red", "green", "blue"];
export const NOMS_COULEURS = { Red: "photolab.couches.rouge", Green: "photolab.couches.vert", Blue: "photolab.couches.bleu",
  RGB: "photolab.couches.rvb", Gray: "photolab.couches.gris", Cyan: "photolab.couches.cyan", Magenta: "photolab.couches.magenta",
  Yellow: "photolab.couches.jaune", Black: "photolab.couches.noir" };

// channels de doc.inspect -> lignes [{ref, type, nom, brut, visible, cible, index?, raccourci}].
export function lignesCouches(ch) {
  if (!ch || !Array.isArray(ch.colors)) return [];
  const t = ch.target || { kind: "composite" };
  const lignes = [];
  let n = 2;
  const racc = () => (n <= 9 ? "Ctrl+" + n++ : "");
  if (ch.colors.length > 1) lignes.push({ ref: "composite", type: "composite", nom: ch.composite, visible: !!ch.compositeVisible,
    cible: t.kind === "composite", raccourci: racc() });
  else n++;
  ch.colors.forEach((c, i) => lignes.push({ ref: COULEURS[i] || i, type: "couleur", index: i, nom: c.name, visible: !!c.visible,
    cible: t.kind === "color" && t.index === i, raccourci: racc() }));
  (ch.alpha || []).forEach((a) => lignes.push({ ref: a.index, type: "alpha", index: a.index, nom: a.name, visible: !!a.visible,
    cible: t.kind === "alpha" && t.index === a.index, raccourci: racc(), couleur: a.color, opacite: a.opacity, indique: a.indicates }));
  return lignes;
}
// Ctrl+clic -> opération de select.loadSelection (référence et amont).
export function operationClic(ev) {
  if (ev.shiftKey && ev.altKey) return "intersect";
  if (ev.shiftKey) return "add";
  if (ev.altKey) return "subtract";
  return "new";
}
// Ce que la vue doit montrer : null = le composite tel quel (rien à composer) ; sinon {couleurs:[bool×3], alphas:[index]}.
export function modeVue(ch) {
  if (!ch || !Array.isArray(ch.colors)) return null;
  const couleurs = ch.colors.map((c) => !!c.visible);
  const alphas = (ch.alpha || []).filter((a) => a.visible).map((a) => a.index);
  if (couleurs.every(Boolean) && !alphas.length) return null;
  return { couleurs, alphas };
}
// Composition PURE sur des RGBA (Uint8ClampedArray) : `src` = rendu du composite, `masques` = {index: Uint8 gris de
// même taille}, `alphas` = [{index, couleur:[r,g,b] 0..1, opacite 0..1}] visibles. Une seule couleur visible (et rien
// d'autre) -> niveaux de gris de cette couleur ; aucune couleur et une alpha -> l'alpha en gris ; sinon les couleurs
// masquées à zéro, puis chaque alpha visible en recouvrement là où elle masque (blanc = sélectionné, non recouvert).
export function composerVue(src, mode, masques = {}, alphas = []) {
  const out = new Uint8ClampedArray(src.length);
  const vis = mode.couleurs;
  const nVis = vis.filter(Boolean).length;
  const seule = nVis === 1 && !alphas.length ? vis.indexOf(true) : -1;
  const alphaSeule = nVis === 0 && alphas.length ? masques[alphas[0].index] : null;
  for (let p = 0, q = 0; p < src.length; p += 4, q++) {
    let r, g, b;
    if (seule >= 0) { r = g = b = src[p + seule]; }
    else if (alphaSeule) { r = g = b = alphaSeule[q]; }
    else {
      r = vis[0] ? src[p] : 0; g = vis[1] ? src[p + 1] : 0; b = vis[2] ? src[p + 2] : 0;
      for (const a of alphas) {
        const m = masques[a.index];
        if (!m) continue;
        const k = a.opacite * (1 - m[q] / 255);
        r += (a.couleur[0] * 255 - r) * k; g += (a.couleur[1] * 255 - g) * k; b += (a.couleur[2] * 255 - b) * k;
      }
    }
    out[p] = r; out[p + 1] = g; out[p + 2] = b; out[p + 3] = src[p + 3];
  }
  return out;
}
// Touche Ctrl+n (n = 2..9) -> ligne visée, ou null.
export function ligneDuRaccourci(lignes, n) {
  return lignes.find((l) => l.raccourci === "Ctrl+" + n) || null;
}

export function initCouches(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const corps = PL.$("#corpsCouches");
  if (!corps) return;
  const liste = document.createElement("div"); liste.className = "cou-liste";
  const pied = document.createElement("div"); pied.className = "pr-pied";
  corps.append(liste, pied);
  let lignes = [], masques = {}, revMasques = null, vignettesAlpha = {}, revVignettes = null;
  const bouton = (icone, cle, fn) => {
    const b = document.createElement("button"); b.type = "button"; b.className = "pr-btn"; b.dataset.icone = icone;
    b.title = T(cle); b.setAttribute("aria-label", b.title); b.addEventListener("click", fn); pied.appendChild(b); return b;
  };
  const cibleAlpha = () => lignes.find((l) => l.cible && l.type === "alpha");
  const bCharger = bouton("dz-edit-charger-selection", "photolab.couches.charger", () => {
    const l = lignes.find((x) => x.cible);
    if (l) PL.executer("select.loadSelection", { channel: l.ref, operation: "new" });
  });
  const bEnreg = bouton("dz-edit-enregistrer-selection", "photolab.couches.enregistrer", () => PL.executer("select.saveSelection", {}));
  bouton("dz-action-ajouter", "photolab.couches.nouvelle", () => PL.executer("channel.new", {}));
  const bSuppr = bouton("dz-action-supprimer", "photolab.couches.supprimer", () => { const l = cibleAlpha(); if (l) PL.executer("channel.delete", { channel: l.index }); });
  if (PL.hydraterIcones) PL.hydraterIcones(pied);

  // Vignettes : couleurs tirées du dernier rendu (petit canevas), alpha lues par /couches?maxSide=64.
  function vignette(l) {
    const c = document.createElement("canvas"); c.className = "cou-vignette"; c.width = 40; c.height = 30;
    const im = PL.vue && PL.vue.rendu && PL.vue.rendu.image;
    const ctx = c.getContext("2d");
    if (l.type === "alpha") {
      const src = vignettesAlpha[l.index];
      if (src) { const i = new Image(); i.onload = () => ctx.drawImage(i, 0, 0, 40, 30); i.src = src; }
      return c;
    }
    if (!im) return c;
    ctx.drawImage(im, 0, 0, 40, 30);
    if (l.type === "couleur") {
      const d = ctx.getImageData(0, 0, 40, 30);
      for (let p = 0; p < d.data.length; p += 4) { const v = d.data[p + l.index]; d.data[p] = d.data[p + 1] = d.data[p + 2] = v; }
      ctx.putImageData(d, 0, 0);
    }
    return c;
  }
  function nomDe(l) {
    if (l.type !== "alpha" && NOMS_COULEURS[l.nom]) return { texte: T(NOMS_COULEURS[l.nom]), brut: false };
    return { texte: l.nom, brut: true };
  }
  function dessiner() {
    const d = PL.etat.doc;
    lignes = d ? lignesCouches(d.channels) : [];
    liste.textContent = "";
    for (const l of lignes) {
      const row = document.createElement("div"); row.className = "cou-ligne" + (l.cible ? " cible" : "");
      row.dataset.ref = String(l.ref);
      const oeil = document.createElement("button"); oeil.type = "button"; oeil.className = "cou-oeil";
      oeil.dataset.icone = l.visible ? "dz-etat-visible" : "dz-etat-cache";
      oeil.setAttribute("aria-label", T(l.visible ? "photolab.couches.masquer" : "photolab.couches.afficher"));
      oeil.addEventListener("click", (ev) => { ev.stopPropagation(); PL.executer("channel.setVisible", { channel: l.ref, visible: !l.visible }); });
      const n = nomDe(l);
      const nom = document.createElement("span"); nom.className = "cou-nom"; nom.textContent = n.texte;
      if (n.brut) nom.setAttribute("data-dz-brut", "");
      const racc = document.createElement("kbd"); racc.className = "cou-racc"; racc.textContent = l.raccourci;
      row.append(oeil, vignette(l), nom, racc);
      row.addEventListener("click", (ev) => {
        if (ev.ctrlKey || ev.metaKey) PL.executer("select.loadSelection", { channel: l.ref, operation: operationClic(ev) });
        else PL.executer("channel.target", { channel: l.ref });
      });
      if (l.type === "alpha") {
        row.addEventListener("dblclick", async () => {
          const v = await demanderNom(PL, T("commun.action.renommer"), l.nom);
          if (v) PL.executer("channel.rename", { channel: l.index, name: v });
        });
      }
      liste.appendChild(row);
    }
    if (PL.hydraterIcones) PL.hydraterIcones(liste);
    bSuppr.disabled = !cibleAlpha();
    bCharger.disabled = !lignes.some((l) => l.cible);
    bEnreg.disabled = !(d && d.hasSelection);
  }

  // Vue composée (PL.vue.filtre) : null quand le composite suffit.
  let cacheFiltre = { image: null, cle: "", canvas: null };
  async function lireMasques(mode, maxSide) {
    const d = PL.etat.doc;
    const cle = d.revision + ":" + maxSide;
    if (revMasques === cle) return;
    revMasques = cle;
    masques = {};
    for (const i of mode.alphas) {
      try {
        const r = await PL.get("/couches?index=" + i + "&maxSide=" + Math.max(32, Math.min(1024, maxSide)), true);
        const png = r && r.couches && r.couches[0] && r.couches[0].png;
        if (png) masques[i] = await new Promise((ok) => { const im = new Image(); im.onload = () => ok(im); im.onerror = () => ok(null); im.src = png; });
      } catch (e) { /* recouvrement facultatif */ }
    }
  }
  function filtre(image) {
    const d = PL.etat.doc;
    const mode = d ? modeVue(d.channels) : null;
    if (!mode || !image) return image;
    const w = image.naturalWidth || image.width, h = image.naturalHeight || image.height;
    const cle = JSON.stringify(mode) + "@" + w + "x" + h + ":" + revMasques + ":" + Object.keys(masques).join(",");
    if (cacheFiltre.image === image && cacheFiltre.cle === cle) return cacheFiltre.canvas;
    const c = document.createElement("canvas"); c.width = w; c.height = h;
    const ctx = c.getContext("2d");
    ctx.drawImage(image, 0, 0);
    const src = ctx.getImageData(0, 0, w, h);
    const grisDe = (im) => {
      if (!im) return null;
      const t = document.createElement("canvas"); t.width = w; t.height = h;
      const k = t.getContext("2d"); k.drawImage(im, 0, 0, w, h);
      const px = k.getImageData(0, 0, w, h).data, g = new Uint8ClampedArray(w * h);
      for (let p = 0, q = 0; p < px.length; p += 4, q++) g[q] = px[p];
      return g;
    };
    const m = {};
    for (const i of mode.alphas) m[i] = grisDe(masques[i]);
    const alphas = (d.channels.alpha || []).filter((a) => mode.alphas.includes(a.index) && m[a.index])
      .map((a) => ({ index: a.index, couleur: a.color || [1, 0, 0], opacite: a.opacity != null ? a.opacity : 0.5 }));
    src.data.set(composerVue(src.data, mode, m, alphas));
    ctx.putImageData(src, 0, 0);
    cacheFiltre = { image, cle, canvas: c };
    return c;
  }
  if (PL.vue) PL.vue.filtre = filtre;

  PL.surDoc.push(async (doc) => {
    dessiner();
    if (!doc) return;
    const mode = modeVue(doc.channels);
    if (mode && mode.alphas.length) {
      await lireMasques(mode, PL.vue && PL.vue.rendu ? PL.vue.rendu.maxSide || 1024 : 1024);
      if (PL.vue) PL.vue.dessiner();
    }
    // Vignettes des alpha : relues à chaque révision, panneau visible seulement.
    const alphas = (doc.channels && doc.channels.alpha) || [];
    if (alphas.length && corps.offsetParent && revVignettes !== doc.revision) {
      revVignettes = doc.revision;
      try {
        const r = await PL.get("/couches?maxSide=64", true);
        vignettesAlpha = {};
        for (const c of (r && r.couches) || []) vignettesAlpha[c.index] = c.png;
        dessiner();
      } catch (e) { /* facultatif */ }
    }
  });
  if (PL.surRendu) PL.surRendu.push(() => { if (corps.offsetParent) dessiner(); });

  // Ctrl+2..9 : cible la couche de ce rang (hors champs de saisie).
  document.addEventListener("keydown", (ev) => {
    if (!(ev.ctrlKey || ev.metaKey) || ev.altKey || ev.shiftKey || !PL.etat.doc) return;
    const m = /^Digit([2-9])$/.exec(ev.code || "");
    if (!m) return;
    const t = ev.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
    const l = ligneDuRaccourci(lignesCouches(PL.etat.doc.channels), Number(m[1]));
    if (!l) return;
    ev.preventDefault();
    PL.executer("channel.target", { channel: l.ref });
  });
  PL.couches = { dessiner, lignes: () => lignes, relireVignettes: () => { revVignettes = null; } };
}
