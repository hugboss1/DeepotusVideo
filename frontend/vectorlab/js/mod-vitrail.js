// mod-vitrail.js — le mode vitrail (phase 5), nourri par la FICHE ÉPINGLÉE
// servie par GET /api/vector/vitrail (style_vitrail.json, copie du skill —
// l'unique source des ancres, bornes et motifs). Builders PURS (baie,
// motifs) ; l'insertion est UNE commande composée ; les contours générés
// sont des tracés fond:none — donc divisibles par le ⧉ existant.
import { op_ajouter, op_calque_ajouter, op_calque_reordonner, op_calque_renommer }
  from "./mod-doc.js";

const nb = (v) => Math.round(v * 100) / 100;

/* ── le générateur de baie (pur) ── */
export function generer_baie(famille, params = {}) {
  const ancres = Object.values(famille.palette.ancres);
  const plomb = Object.values(famille.palette.contour)[0];
  const [bLo, bHi] = famille.bornes.part_bordure_ornementale;
  const {
    w = 640, h = 960, forme = "ogive", colonnes = 2, rangees = 3,
    marge = 24, epaisseurCadre = 18, epaisseurReseau = 10,
    epaisseurBordure = 8,
  } = params;
  const bordure = Math.max(bLo, Math.min(bHi, params.bordure ?? 0.08));
  const x0 = marge, x1 = w - marge, y0 = marge, y1 = h - marge;
  const W = x1 - x0, H = y1 - y0;
  const d = bordure * Math.min(W, H);
  const ys = forme === "ogive" ? y0 + 0.35 * H : y0 + d;
  const xi0 = x0 + d, xi1 = x1 - d, yi1 = y1 - d;

  // contour ogival : côtés + bas + deux arcs cubiques vers l'apex
  const ogiveD = (gx0, gx1, gys, gy1, apexY) => {
    const gcx = (gx0 + gx1) / 2, tw = gx1 - gx0, monte = gys - apexY;
    return `M ${nb(gx0)} ${nb(gys)} L ${nb(gx0)} ${nb(gy1)}`
      + ` L ${nb(gx1)} ${nb(gy1)} L ${nb(gx1)} ${nb(gys)}`
      + ` C ${nb(gx1)} ${nb(gys - 0.6 * monte)}`
      + ` ${nb(gcx + 0.25 * tw)} ${nb(apexY)} ${nb(gcx)} ${nb(apexY)}`
      + ` C ${nb(gcx - 0.25 * tw)} ${nb(apexY)}`
      + ` ${nb(gx0)} ${nb(gys - 0.6 * monte)} ${nb(gx0)} ${nb(gys)} Z`;
  };

  const verre = [];
  const cw = (xi1 - xi0) / colonnes, rh = (yi1 - ys) / rangees;
  for (let j = 0; j < rangees; j++) {
    for (let i = 0; i < colonnes; i++) {
      verre.push({ type: "rect", x: nb(xi0 + i * cw), y: nb(ys + j * rh),
                   w: nb(cw), h: nb(rh),
                   style: { fond: ancres[(j * colonnes + i) % ancres.length] } });
    }
  }
  if (forme === "ogive") {
    const gcx = (xi0 + xi1) / 2, tw = xi1 - xi0;
    const apexI = y0 + d, monteI = ys - apexI;
    verre.push({ type: "path",
      d: `M ${nb(xi0)} ${nb(ys)}`
        + ` C ${nb(xi0)} ${nb(ys - 0.6 * monteI)}`
        + ` ${nb(gcx - 0.25 * tw)} ${nb(apexI)} ${nb(gcx)} ${nb(apexI)}`
        + ` C ${nb(gcx + 0.25 * tw)} ${nb(apexI)}`
        + ` ${nb(xi1)} ${nb(ys - 0.6 * monteI)} ${nb(xi1)} ${nb(ys)} Z`,
      style: { fond: ancres[(rangees * colonnes) % ancres.length] } });
  }

  const contours = [];
  const sPlomb = (ep) => ({ fond: "none", contour: plomb, epaisseur: ep });
  if (forme === "ogive") {
    contours.push({ type: "path", d: ogiveD(x0, x1, ys, y1, y0),
                    style: sPlomb(epaisseurCadre) });
    contours.push({ type: "path", d: ogiveD(xi0, xi1, ys, yi1, y0 + d),
                    style: sPlomb(epaisseurBordure) });
  } else {
    contours.push({ type: "rect", x: x0, y: y0, w: W, h: H,
                    style: sPlomb(epaisseurCadre) });
    contours.push({ type: "rect", x: nb(xi0), y: nb(y0 + d),
                    w: nb(xi1 - xi0), h: nb(yi1 - (y0 + d)),
                    style: sPlomb(epaisseurBordure) });
  }
  for (let i = 1; i < colonnes; i++) {
    const mx = nb(xi0 + i * cw);
    contours.push({ type: "path", d: `M ${mx} ${nb(ys)} L ${mx} ${nb(yi1)}`,
                    style: sPlomb(epaisseurReseau) });
  }
  for (let j = 1; j < rangees; j++) {
    const my = nb(ys + j * rh);
    contours.push({ type: "path",
                    d: `M ${nb(xi0)} ${my} L ${nb(xi1)} ${my}`,
                    style: sPlomb(epaisseurReseau) });
  }
  return { verre, contours,
           params: { forme, colonnes, rangees, bordure, d: nb(d) } };
}

/* ── presets de motifs (groupes insérables) ── */
export function motif_iris(famille, cx, cy, s = 1) {
  const a = famille.palette.ancres;
  const X = (v) => nb(cx + v * s), Y = (v) => nb(cy + v * s);
  const p = (dd, fond) => ({ type: "path", d: dd, style: { fond } });
  return { type: "groupe", style: {}, enfants: [
    p(`M ${X(0)} ${Y(0)} C ${X(-18)} ${Y(-28)} ${X(-8)} ${Y(-52)}`
      + ` ${X(0)} ${Y(-56)} C ${X(8)} ${Y(-52)} ${X(18)} ${Y(-28)}`
      + ` ${X(0)} ${Y(0)} Z`, a.violet_profond),
    p(`M ${X(0)} ${Y(0)} C ${X(-30)} ${Y(-6)} ${X(-46)} ${Y(-24)}`
      + ` ${X(-44)} ${Y(-38)} C ${X(-26)} ${Y(-34)} ${X(-8)} ${Y(-18)}`
      + ` ${X(0)} ${Y(0)} Z`, a.violet_profond),
    p(`M ${X(0)} ${Y(0)} C ${X(30)} ${Y(-6)} ${X(46)} ${Y(-24)}`
      + ` ${X(44)} ${Y(-38)} C ${X(26)} ${Y(-34)} ${X(8)} ${Y(-18)}`
      + ` ${X(0)} ${Y(0)} Z`, a.violet_profond),
    p(`M ${X(-3)} ${Y(0)} L ${X(3)} ${Y(0)} L ${X(2)} ${Y(34)}`
      + ` L ${X(-2)} ${Y(34)} Z`, a.emeraude),
  ] };
}

export function motif_rayons(famille, cx, cy, r = 80, n = 8) {
  const ambre = famille.palette.ancres.ambre_dore;
  const enfants = [];
  for (let k = 0; k < n; k++) {
    const t = -Math.PI / 2 + 2 * Math.PI * k / n;
    enfants.push({ type: "path",
      d: `M ${nb(cx)} ${nb(cy)} L ${nb(cx + r * Math.cos(t))}`
        + ` ${nb(cy + r * Math.sin(t))}`,
      style: { fond: "none", contour: ambre, epaisseur: 6 } });
  }
  return { type: "groupe", style: {}, enfants };
}

export function motif_halo(famille, cx, cy, r = 60) {
  const ambre = famille.palette.ancres.ambre_dore;
  return { type: "groupe", style: {}, enfants: [
    { type: "ellipse", cx: nb(cx), cy: nb(cy), rx: nb(r), ry: nb(r),
      style: { fond: "none", contour: ambre, epaisseur: 6 } },
    { type: "ellipse", cx: nb(cx), cy: nb(cy), rx: nb(r * 1.25),
      ry: nb(r * 1.25),
      style: { fond: "none", contour: ambre, epaisseur: 3 } },
  ] };
}

/* ── l'UI : panneau Vitrail nourri par l'endpoint ── */
export function initVitrail(VL) {
  const { $, etat } = VL;
  let famille = null;

  function calqueParNom(doc, nom, sousQui) {
    let c = doc.calques.find((x) => x.nom === nom);
    if (!c) {
      const id = op_calque_ajouter(doc, nom);
      c = doc.calques.find((x) => x.id === id);
      if (sousQui) {
        const iRef = doc.calques.findIndex((x) => x.nom === sousQui);
        if (iRef >= 0) op_calque_reordonner(doc, id, iRef);
      }
    }
    return c;
  }

  function insererBaie(params) {
    const b = generer_baie(famille, {
      w: etat.doc.taille.w, h: etat.doc.taille.h, ...params });
    VL.executer((doc) => {
      const cContours = calqueParNom(doc, "contours");
      const cVerre = calqueParNom(doc, "verre", "contours");
      void cVerre;
      for (const o of b.verre) {
        op_ajouter(doc, doc.calques.find((x) => x.nom === "verre").id, o);
      }
      for (const o of b.contours) op_ajouter(doc, cContours.id, o);
    });
    VL.toast(`baie ${b.params.forme} générée — verres et plombs sur leurs `
             + "calques (⧉ divise, la palette colore)");
  }

  function insererMotif(fabrique) {
    const cx = etat.doc.taille.w / 2, cy = etat.doc.taille.h / 2;
    const g = fabrique(famille, cx, cy);
    const id = VL.executer(op_ajouter, etat.calqueActif, g);
    if (id) VL.setSelection([id]);
  }

  function rendrePanneau() {
    const hote = $("#panneauVitrail");
    if (!hote) return;
    if (!famille || !etat.doc) { hote.innerHTML = ""; return; }
    const ancres = Object.entries(famille.palette.ancres);
    const plomb = Object.values(famille.palette.contour)[0];
    hote.innerHTML = `
      <div class="vit-palette" title="La palette de la fiche épinglée — clic : applique à la sélection (ou au style courant)">
        ${ancres.map(([nom, hex]) => `<button class="vit-sw" data-hex="${hex}"
           title="${nom} ${hex}" style="background:${hex}"></button>`).join("")}
        <button class="vit-sw vit-plomb" data-hex="${plomb}" data-contour="1"
           title="plomb ${plomb} (contour)" style="background:${plomb}"></button>
      </div>
      <div class="ap-ligne">
        <button id="vitBaie" title="Génère une baie complète : verres cyclant sur les ancres + plombs (cadre, bordure aux bornes de la fiche, réseau) — une seule entrée d'annulation">◧ Baie…</button>
      </div>
      <div class="ap-ligne"><span>Motifs</span>
        <button id="vitIris" title="Iris stylisé (groupe)">⚜</button>
        <button id="vitRayons" title="Rayons solaires géométriques (groupe)">☀</button>
        <button id="vitHalo" title="Halo rayonnant (groupe)">◎</button>
      </div>`;
    hote.querySelectorAll(".vit-sw").forEach((b) =>
      b.addEventListener("click", async () => {
        const patch = b.dataset.contour
          ? { contour: b.dataset.hex } : { fond: b.dataset.hex };
        Object.assign(etat.styleCourant, patch);
        if (etat.selection.length) {
          const { op_style } = await import("./mod-doc.js");
          VL.executer(op_style, etat.selection.slice(), patch);
        }
      }));
    $("#vitBaie").addEventListener("click", () => {
      const forme = (prompt("Forme (ogive / rectangle) :", "ogive") || "")
        .trim().toLowerCase();
      if (forme !== "ogive" && forme !== "rectangle") return;
      const colonnes = Math.max(1, Math.min(8,
        +(prompt("Colonnes de verre :", "2") || 0)));
      const rangees = Math.max(1, Math.min(10,
        +(prompt("Rangées de verre :", "3") || 0)));
      if (!colonnes || !rangees) return;
      insererBaie({ forme, colonnes, rangees });
    });
    $("#vitIris").addEventListener("click",
      () => insererMotif((f, x, y) => motif_iris(f, x, y, 1.4)));
    $("#vitRayons").addEventListener("click",
      () => insererMotif((f, x, y) => motif_rayons(f, x, y, 110, 8)));
    $("#vitHalo").addEventListener("click",
      () => insererMotif((f, x, y) => motif_halo(f, x, y, 80)));
  }

  fetch("/api/vector/vitrail").then((r) => r.ok ? r.json() : null)
    .then((d) => { famille = d && d.famille; rendrePanneau(); })
    .catch(() => { famille = null; });

  const suivant = VL.surRendu;
  VL.surRendu = () => { suivant(); rendrePanneau(); };
}
