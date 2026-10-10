// mod-infos.js — t153 (parité L3) : le groupe Histogramme | Infos.
// Histogramme : /histogramme (256 comptes r, g, b, l, compté par le pont sur un rendu de COPIE) ; canal, graphe et
// statistiques de l'amont (tone.rs : moyenne, écart type, médiane, pixels = largeur × hauteur du document) ; triangle
// tant que le graphe ne correspond pas à la dernière révision. Infos : document.pixel sous le pointeur (composite, 0..1,
// hors historique), R/V/B, C/M/J/N par la conversion naïve de l'amont (aucun profil), X/Y, L/H de la sélection, taille.
// Fonctions PURES exportées (qa/panneaux3.test.mjs).
import { cheminHistogramme } from "./mod-courbes.js";

export const CANAUX = [
  { id: "l", cle: "photolab.histogramme.luminosite", couleur: "var(--ink-soft)" },
  { id: "r", cle: "photolab.histogramme.rouge", couleur: "var(--pl-canal-rouge)" },
  { id: "g", cle: "photolab.histogramme.vert", couleur: "var(--pl-canal-vert)" },
  { id: "b", cle: "photolab.histogramme.bleu", couleur: "var(--pl-canal-bleu)" },
];

// 256 comptes -> {moyenne, ecartType (population), mediane, compte} ; null sans aucun pixel compté.
export function statistiques(bins) {
  const h = Array.isArray(bins) ? bins : [];
  let n = 0, s = 0;
  for (let i = 0; i < h.length; i++) { n += h[i]; s += i * h[i]; }
  if (!n) return null;
  const m = s / n;
  let v = 0;
  for (let i = 0; i < h.length; i++) v += h[i] * (i - m) * (i - m);
  let cumul = 0, med = 0;
  for (let i = 0; i < h.length; i++) { cumul += h[i]; if (cumul * 2 >= n) { med = i; break; } }
  return { moyenne: m, ecartType: Math.sqrt(v / n), mediane: med, compte: n };
}

// Pixel du moteur [r,g,b,a] (0..1) -> lecture des Infos : R/V/B 0..255, C/M/J/N en % (conversion naïve de l'amont :
// k = 1 − max ; encre = (1 − v − k) / (1 − k)).
export function lecturePixel(px) {
  if (!Array.isArray(px) || px.length < 3) return null;
  const [r, g, b] = px.map((v) => Math.max(0, Math.min(1, Number(v) || 0)));
  const k = 1 - Math.max(r, g, b);
  const encre = (v) => (k >= 1 ? 0 : (1 - v - k) / (1 - k));
  const pc = (v) => Math.round(v * 100);
  return { r: Math.round(r * 255), v: Math.round(g * 255), b: Math.round(b * 255),
    c: pc(encre(r)), m: pc(encre(g)), j: pc(encre(b)), n: pc(k), a: px.length > 3 ? Math.round(px[3] * 255) : 255 };
}
// Point écran (déjà converti en coordonnées document) -> pixel entier, ou null hors document.
export function pixelSous(p, doc) {
  if (!p || !doc) return null;
  const x = Math.floor(p.x), y = Math.floor(p.y);
  return x >= 0 && y >= 0 && x < doc.width && y < doc.height ? { x, y } : null;
}
// Bornes de sélection de doc.inspect ([x, y, w, h] ou {x, y, width, height}) -> {l, h} ou null.
export function tailleSelection(doc) {
  const s = doc && doc.selectionBounds;
  if (!s || !doc.hasSelection) return null;
  if (Array.isArray(s)) return { l: s[2], h: s[3] };
  return { l: s.width != null ? s.width : s.w, h: s.height != null ? s.height : s.h };
}

export function initInfos(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const NS = "http://www.w3.org/2000/svg";
  // ── Histogramme ──
  const ch = PL.$("#corpsHistogramme");
  let histo = null, revHisto = null, canal = "l", minut = null, enCours = false;
  if (ch) {
    const tete = document.createElement("div"); tete.className = "hi-tete";
    const lib = document.createElement("label"); lib.className = "hi-lib"; lib.textContent = T("photolab.histogramme.canal");
    const choix = document.createElement("select"); choix.className = "hi-canal"; choix.setAttribute("aria-label", T("photolab.histogramme.canal"));
    for (const c of CANAUX) { const o = document.createElement("option"); o.value = c.id; o.textContent = T(c.cle); choix.appendChild(o); }
    choix.addEventListener("change", () => { canal = choix.value; dessinerHisto(); });
    const alerte = document.createElement("span"); alerte.className = "hi-alerte"; alerte.innerHTML = PL.icone("dz-etat-avertissement");
    alerte.title = T("photolab.histogramme.perime"); alerte.setAttribute("role", "img"); alerte.setAttribute("aria-label", alerte.title); alerte.hidden = true;
    lib.appendChild(choix);
    tete.append(lib, alerte);
    const svg = document.createElementNS(NS, "svg"); svg.setAttribute("class", "hi-graphe"); svg.setAttribute("viewBox", "0 0 256 100");
    svg.setAttribute("preserveAspectRatio", "none");
    const chemin = document.createElementNS(NS, "path"); svg.appendChild(chemin);
    const stats = document.createElement("dl"); stats.className = "hi-stats";
    ch.append(tete, svg, stats);
    PL.histogramme = { relire: () => planifier(0), etat: () => ({ histo, canal, revHisto }) };

    function dessinerHisto() {
      const d = PL.etat.doc;
      alerte.hidden = !d || !histo || revHisto === d.revision;
      const c = CANAUX.find((x) => x.id === canal);
      chemin.setAttribute("d", histo && histo[canal] ? cheminHistogramme(histo[canal], 256, 100) : "");
      chemin.style.fill = c.couleur;                     // style, pas attribut : var() ne vaut que dans une propriété CSS
      const st = histo ? statistiques(histo[canal]) : null;
      stats.textContent = "";
      const ligne = (cle, val) => { const dt = document.createElement("dt"); dt.textContent = T(cle); const dd = document.createElement("dd"); dd.textContent = val; stats.append(dt, dd); };
      const f = (v) => (v == null ? "—" : v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
      ligne("photolab.histogramme.moyenne", st ? f(st.moyenne) : "—");
      ligne("photolab.histogramme.ecart_type", st ? f(st.ecartType) : "—");
      ligne("photolab.histogramme.mediane", st ? String(st.mediane) : "—");
      ligne("photolab.histogramme.pixels", d ? (d.width * d.height).toLocaleString() : "—");
    }
    async function lire() {
      const d = PL.etat.doc;
      if (!d || enCours || !ch.offsetParent) { dessinerHisto(); return; }
      enCours = true;
      const rev = d.revision;
      try { histo = await PL.get("/histogramme?maxSide=384", true); revHisto = rev; } catch (e) { /* facultatif */ }
      enCours = false;
      dessinerHisto();
      if (PL.etat.doc && PL.etat.doc.revision !== revHisto) planifier(300);
    }
    // Relu au plus toutes les 250 ms (amont), et seulement panneau visible.
    function planifier(ms = 250) { clearTimeout(minut); minut = setTimeout(lire, ms); }
    PL.surDoc.push((doc) => { if (!doc) { histo = null; revHisto = null; dessinerHisto(); } else { dessinerHisto(); if (ch.offsetParent) planifier(); } });
    dessinerHisto();
  }

  // ── Infos ──
  const ci = PL.$("#corpsInfos");
  if (!ci) return;
  const champs = {};
  const bloc = (cles) => {
    const d = document.createElement("dl"); d.className = "in-bloc";
    for (const [id, cle] of cles) {
      const dt = document.createElement("dt"); dt.textContent = T(cle);
      const dd = document.createElement("dd"); dd.textContent = "—"; champs[id] = dd;
      d.append(dt, dd);
    }
    return d;
  };
  const haut = document.createElement("div"); haut.className = "in-ligne";
  haut.append(bloc([["r", "photolab.infos.r"], ["v", "photolab.infos.v"], ["b", "photolab.infos.b"]]),
    bloc([["c", "photolab.infos.c"], ["m", "photolab.infos.m"], ["j", "photolab.infos.j"], ["n", "photolab.infos.n"]]));
  const bas = document.createElement("div"); bas.className = "in-ligne";
  bas.append(bloc([["x", "photolab.infos.x"], ["y", "photolab.infos.y"]]), bloc([["l", "photolab.infos.l"], ["h", "photolab.infos.h"]]));
  const taille = document.createElement("p"); taille.className = "in-doc";
  ci.append(haut, bas, taille);
  let dernier = null, minutPx = null, attente = null, cache = new Map();

  function afficher(lu, pos) {
    for (const k of ["r", "v", "b"]) champs[k].textContent = lu ? String(lu[k]) : "—";
    for (const k of ["c", "m", "j", "n"]) champs[k].textContent = lu ? lu[k] + " %" : "—";
    champs.x.textContent = pos ? String(pos.x) : "—"; champs.y.textContent = pos ? String(pos.y) : "—";
  }
  function selection() {
    const d = PL.etat.doc, s = tailleSelection(d);
    champs.l.textContent = s ? String(Math.round(s.l)) : "—"; champs.h.textContent = s ? String(Math.round(s.h)) : "—";
    taille.textContent = d ? T("photolab.infos.doc", { l: d.width, h: d.height }) : "";
  }
  async function lirePixel(pos) {
    const d = PL.etat.doc;
    const cle = pos.x + "," + pos.y + "@" + d.revision;
    if (cache.has(cle)) { afficher(cache.get(cle), pos); return; }
    if (attente) { dernier = pos; return; }          // une requête à la fois : la dernière position gagne
    attente = true;
    let lu = null;
    try { lu = lecturePixel(await PL.post("/executer", { command: "document.pixel", params: pos })); } catch (e) { /* signalé */ }
    attente = null;
    if (cache.size > 500) cache = new Map();
    cache.set(cle, lu);
    afficher(lu, pos);
    if (dernier && (dernier.x !== pos.x || dernier.y !== pos.y)) { const p = dernier; dernier = null; lirePixel(p); }
  }
  const scene = PL.$("#scene") || PL.$("#toile");
  if (scene) {
    scene.addEventListener("pointermove", (ev) => {
      if (!ci.offsetParent || !PL.etat.doc || !PL.vue || !PL.vue.versDoc) return;
      const s = PL.vue.pointeur(ev);                     // même repère que les gestes (vue en miroir comprise)
      const pos = pixelSous(PL.vue.versDoc(s.x, s.y), PL.etat.doc);
      if (!pos) { afficher(null, null); return; }
      clearTimeout(minutPx);
      minutPx = setTimeout(() => lirePixel(pos), 40);
    });
    scene.addEventListener("pointerleave", () => { clearTimeout(minutPx); afficher(null, null); });
  }
  PL.surDoc.push(() => { selection(); cache = new Map(); });
  selection();
  PL.infos = { lirePixel: (x, y) => lirePixel({ x, y }), champs };
}
