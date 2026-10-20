// mod-echantillons.js — t253 (photocraft 0.10) : l'outil Échantillonneur de couleur. Un clic pose un point de mesure
// (view.colorSamplers.add, au centre du pixel, 10 au plus) ; glisser un point le déplace (…move) ; Alt+clic sur un point
// le retire (…delete) ; « Tout effacer » (…clear). Les points vivent dans le document du MOTEUR (aucun état d'historique)
// et se relisent par view.colorSamplers.list à chaque changement du document : le panneau Infos les montre (#n,
// R/V/B, C/M/J/N), le canevas les marque d'un réticule numéroté.
// Fonctions PURES exportées (qa/selection-m4.test.mjs).
import { versEcran } from "./mod-vue.js";

export const MAX_ECHANTILLONS = 10;

export const positionEchantillon = (x, y) => ({ x: Math.floor(x) + 0.5, y: Math.floor(y) + 0.5 });
// Le moteur rend la position du PIXEL mesuré (entière) : le point se montre et se saisit en son centre.
export const centreEchantillon = (position) => positionEchantillon(position[0], position[1]);

// Indice (dans la liste) du point sous le point ÉCRAN (sx, sy), ou -1.
export function echantillonProche(liste, sx, sy, v, tol = 6) {
  for (let i = 0; i < (liste || []).length; i++) {
    const p = liste[i].position;
    if (!Array.isArray(p)) continue;
    const c = centreEchantillon(p);
    const s = versEcran(v, c.x, c.y);
    if (Math.hypot(sx - s.x, sy - s.y) <= tol) return i;
  }
  return -1;
}

// Que fait un clic (p : {x, y} document et {sx, sy} écran) ? -> {type: "saisir", index} | {type: "supprimer", command,
// params} | {type: "ajouter", command, params} | {type: "plein"} | null (hors document, ou Alt+clic dans le vide).
export function actionEchantillon(liste, p, alt, doc, v) {
  const i = echantillonProche(liste, p.sx, p.sy, v);
  if (i >= 0) {
    const index = liste[i].index != null ? liste[i].index : i;
    return alt ? { type: "supprimer", command: "view.colorSamplers.delete", params: { index } } : { type: "saisir", index };
  }
  if (alt || !doc || p.x < 0 || p.y < 0 || p.x >= doc.width || p.y >= doc.height) return null;
  if ((liste || []).length >= MAX_ECHANTILLONS) return { type: "plein" };
  return { type: "ajouter", command: "view.colorSamplers.add", params: positionEchantillon(p.x, p.y) };
}

// Point du moteur {number, rgb (0..255), cmyk (%)} -> lecture des Infos ; null s'il manque une couleur.
export function lectureEchantillon(s) {
  if (!s || !Array.isArray(s.rgb) || s.rgb.length < 3) return null;
  const k = Array.isArray(s.cmyk) && s.cmyk.length >= 4 ? s.cmyk : [null, null, null, null];
  const n = (x) => (x == null || !Number.isFinite(Number(x)) ? null : Math.round(Number(x)));
  return { numero: s.number, r: n(s.rgb[0]), v: n(s.rgb[1]), b: n(s.rgb[2]), c: n(k[0]), m: n(k[1]), j: n(k[2]), n: n(k[3]) };
}

/* ───────────── côté DOM ───────────── */

export function initEchantillons(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const toile = PL.$("#toile");
  let liste = [];
  let g = null;              // {index, x, y} : point saisi, position document en cours
  let revLue = null, enCours = false;
  const redessiner = () => PL.dessinerFourmis && PL.dessinerFourmis();

  async function relire() {
    const d = PL.etat.doc;
    if (!d) { liste = []; revLue = null; montrer(); return; }
    if (enCours) return;
    enCours = true;
    try {
      const r = await PL.post("/executer", { command: "view.colorSamplers.list", params: {} });
      liste = r && Array.isArray(r.samplers) ? r.samplers : [];
      revLue = d.revision;
    } catch (e) { /* signalé par mod-api */ }
    enCours = false;
    montrer();
  }
  async function lancer(command, params) {
    const r = await PL.executer(command, params);
    await relire();
    return r;
  }
  PL.echantillons = { liste: () => liste, relire };
  PL.actions = PL.actions || {};
  PL.actions["pl.echantillons.effacer"] = () => lancer("view.colorSamplers.clear", {});

  PL.gestes.colorSampler = {
    appui(p, ev) {
      const a = actionEchantillon(liste, p, ev.altKey, PL.etat.doc, PL.vue.v);
      if (!a) return;
      if (a.type === "saisir") { g = { index: a.index, x: p.x, y: p.y }; return; }
      if (a.type === "plein") { PL.signaler(T("photolab.echantillon.plein", { n: MAX_ECHANTILLONS })); return; }
      lancer(a.command, a.params);
    },
    bouger(p) { if (g) { g.x = p.x; g.y = p.y; redessiner(); } },
    relacher() {
      if (!g) return;
      const d = PL.etat.doc, { index, x, y } = g; g = null;
      // Lâché hors du document : le point est retiré (comme dans la référence).
      if (!d || x < 0 || y < 0 || x >= d.width || y >= d.height) lancer("view.colorSamplers.delete", { index });
      else lancer("view.colorSamplers.move", { index, ...positionEchantillon(x, y) });
    },
    survol(p) { toile.style.cursor = echantillonProche(liste, p.sx, p.sy, PL.vue.v) >= 0 ? "move" : "crosshair"; },
    annuler() { g = null; redessiner(); },
    touche(ev) { if (ev.key !== "Escape" || !g) return false; g = null; redessiner(); return true; },
    quitter() { g = null; },
  };

  // Réticule numéroté de chaque point (le point saisi suit le pointeur).
  PL.dessinsSup = PL.dessinsSup || [];
  PL.dessinsSup.push((svg, el, ecran) => {
    if (!PL.etat.doc) return;
    liste.forEach((e, i) => {
      if (!Array.isArray(e.position)) return;
      const pos = g && g.index === (e.index != null ? e.index : i) ? positionEchantillon(g.x, g.y) : centreEchantillon(e.position);
      const s = ecran(pos.x, pos.y);
      for (const classe of ["fourmis-sombre", "fourmis-clair"]) {
        svg.appendChild(el("path", { d: `M${s.x - 7} ${s.y}H${s.x - 2}M${s.x + 2} ${s.y}H${s.x + 7}M${s.x} ${s.y - 7}V${s.y - 2}M${s.x} ${s.y + 2}V${s.y + 7}`, fill: "none" }, classe));
      }
      const t = el("text", { x: s.x + 8, y: s.y + 14 }, "echantillon-numero");
      t.textContent = String(e.number != null ? e.number : i + 1);
      svg.appendChild(t);
    });
  });

  // Panneau Infos : une ligne par point, sous les lectures du pointeur.
  const ci = PL.$("#corpsInfos");
  const boite = ci ? document.createElement("div") : null;
  if (boite) { boite.className = "in-echantillons"; ci.appendChild(boite); }
  function montrer() {
    redessiner();
    if (!boite) return;
    boite.textContent = "";
    for (const e of liste) {
      const lu = lectureEchantillon(e);
      if (!lu) continue;
      const l = document.createElement("p"); l.className = "in-echantillon";
      const f = (x) => (x == null ? "—" : String(x));
      l.textContent = T("photolab.infos.echantillon", { n: lu.numero, r: f(lu.r), v: f(lu.v), b: f(lu.b), c: f(lu.c), m: f(lu.m), j: f(lu.j), k: f(lu.n) });
      boite.appendChild(l);
    }
  }
  // Relus à chaque nouvelle révision du document (couleurs changées, autre document) ; rien de plus.
  PL.surDoc.push((doc) => { if (!doc) { liste = []; revLue = null; montrer(); } else if (doc.revision !== revLue) relire(); });
}
