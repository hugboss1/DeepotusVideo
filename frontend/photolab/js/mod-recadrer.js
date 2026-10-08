// mod-recadrer.js — l'outil Recadrage (C3) : tracer un cadre (borné au document), l'ajuster par ses quatre poignées
// (8 px écran), Entrée ou double-clic = image.crop {x, y, width, height, deleteCroppedPixels}, Échap = abandonner ;
// sans cadre mais avec une sélection, Entrée recadre à la sélection (image.crop {}).
// Fonctions PURES exportées (qa/gestes.test.mjs).
import { rectDepuisGlisser } from "./mod-selection.js";
import { rectVersEcran } from "./mod-vue.js";

// Rectangle du glisser, intersecté avec le document {width, height}.
export function rectRecadrage(x0, y0, x1, y1, opts, doc) {
  const r = rectDepuisGlisser(x0, y0, x1, y1, opts || {});
  const gauche = Math.max(0, r.x), haut = Math.max(0, r.y);
  const droite = Math.min(doc.width, r.x + r.width), bas = Math.min(doc.height, r.y + r.height);
  return { x: gauche, y: haut, width: Math.max(0, droite - gauche), height: Math.max(0, bas - haut) };
}

// Poignée du cadre sous le point ÉCRAN (sx, sy) : "nw" | "ne" | "sw" | "se" | null.
export function poigneeSous(cadre, sx, sy, v, tol = 8) {
  if (!cadre) return null;
  // t152 : par la conversion commune (vue en miroir comprise)
  const r = rectVersEcran(v, cadre.x, cadre.y, cadre.width, cadre.height);
  const x0 = r.x, y0 = r.y, x1 = r.x + r.w, y1 = r.y + r.h;
  for (const [nom, x, y] of [["nw", x0, y0], ["ne", x1, y0], ["sw", x0, y1], ["se", x1, y1]]) {
    if (Math.abs(sx - x) <= tol && Math.abs(sy - y) <= tol) return nom;
  }
  return null;
}

// Tirer une poignée jusqu'au point document (x, y) : le coin opposé reste fixe ; dépasser l'autre coin retourne le cadre.
export function redimensionner(cadre, poignee, x, y, doc) {
  const fixeX = poignee.includes("w") ? cadre.x + cadre.width : cadre.x;
  const fixeY = poignee.includes("n") ? cadre.y + cadre.height : cadre.y;
  return rectRecadrage(fixeX, fixeY, x, y, {}, doc);
}

export function commandeRecadrage(cadre, aSelection, deleteCroppedPixels) {
  if (cadre && cadre.width >= 1 && cadre.height >= 1) {
    return { command: "image.crop", params: { x: cadre.x, y: cadre.y, width: cadre.width, height: cadre.height, deleteCroppedPixels: !!deleteCroppedPixels } };
  }
  if (!cadre && aSelection) return { command: "image.crop", params: {} };
  return null;
}

/* ───────────── côté DOM ───────────── */

export function initRecadrer(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const toile = PL.$("#toile");
  let cadre = null;          // cadre courant (coordonnées document)
  let g = null;              // geste : {type: "nouveau"|"poignee", x0, y0, poignee}
  const montrer = () => { PL.apercu = cadre ? { type: "recadrage", cadre } : null; if (PL.dessinerFourmis) PL.dessinerFourmis(); };
  const curseur = { nw: "nwse-resize", se: "nwse-resize", ne: "nesw-resize", sw: "nesw-resize" };

  function valider() {
    const d = PL.etat.doc; if (!d) return;
    const c = commandeRecadrage(cadre, d.hasSelection, PL.etat.options.deleteCroppedPixels);
    cadre = null; montrer();
    if (c) PL.executer(c.command, c.params);
    else PL.signaler(T("photolab.recadrage.aide"));
  }

  PL.gestes.crop = {
    appui(p, ev) {
      const d = PL.etat.doc; if (!d) return;
      const h = poigneeSous(cadre, p.sx, p.sy, PL.vue.v);
      g = h ? { type: "poignee", poignee: h } : { type: "nouveau", x0: p.x, y0: p.y, maj: ev.shiftKey, alt: ev.altKey };
    },
    bouger(p, ev) {
      const d = PL.etat.doc; if (!g || !d) return;
      cadre = g.type === "poignee" ? redimensionner(cadre, g.poignee, p.x, p.y, d)
        : rectRecadrage(g.x0, g.y0, p.x, p.y, { carre: ev.shiftKey && !g.maj, centre: ev.altKey && !g.alt }, d);
      montrer();
    },
    relacher() {
      g = null;
      if (cadre && (cadre.width < 1 || cadre.height < 1)) cadre = null;      // un clic sans glisser n'en laisse pas
      montrer();
    },
    survol(p) { toile.style.cursor = curseur[poigneeSous(cadre, p.sx, p.sy, PL.vue.v)] || "crosshair"; },
    double() { valider(); },
    touche(ev) {
      if (ev.key === "Enter") { valider(); return true; }
      if (ev.key === "Escape" && cadre) { cadre = null; g = null; montrer(); return true; }
      return false;
    },
    annuler() { g = null; },
    quitter() { cadre = null; g = null; },
  };
}
