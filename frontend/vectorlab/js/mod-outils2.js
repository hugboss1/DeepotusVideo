// mod-outils2.js — les gestes du lot B, classe Affinity : formes
// paramétriques (tracé au rayon, poignées de paramètres), crayon lissé,
// couteau, gomme vectorielle, outil Coin, Shape Builder (constructeur),
// nœuds MULTIPLES (lasso d'ancres), pivot déplaçable, panneau Nœuds,
// panneau Instantanés. Chaque geste = UNE commande via VL.executer. Les
// listeners du cœur des outils (mod-tools) restent ; ce module écoute en
// phase de CAPTURE et n'arrête la propagation que pour ses propres cibles.
import { op_ajouter, op_forme_param, op_forme_en_chemin, op_supprimer } from "./mod-doc.js";
import { chemin_parser, chemin_serialiser, chemin_ancres } from "./mod-doc.js";
import { FORMES, forme_defaut, forme_d, forme_poignees, forme_poignee_deplacer } from "./mod-formes.js";
import { lisser_vers_d } from "./mod-crayon.js";
import { op_couteau, op_gomme, op_constructeur } from "./mod-bool.js";
import { noeuds_deplacer_segs, op_noeuds_aligner, op_noeud_inserer, op_chemin_inverser,
         op_chemins_joindre, op_coins_arrondir, ancres_dans_rect } from "./mod-noeuds.js";

const SNS = "http://www.w3.org/2000/svg";
export const HINTS2 = {
  forme: "glisser depuis le centre : le rayon suit · la forme se choisit dans le panneau Forme",
  crayon: "dessiner à main levée : le trait se lisse ; fin près du début = fermé",
  couteau: "tirer une droite à travers la sélection (ou tout) : elle la coupe en deux",
  gomme: "glisser sur les formes : le trait les entame (largeur dans le panneau)",
  coin: "cliquer une forme aux angles vifs : ses coins s'arrondissent (rayon dans le panneau)",
  constructeur: "cliquer les régions à garder (Entrée = fusionner, Alt+Entrée = retirer)",
};

export function initOutils2(VL) {
  const { $, etat } = VL;
  const stage = $("#stage");
  etat.formeCourante = "polygone";
  etat.ancresSel = [];
  etat.pivot = null;
  etat.atomesChoisis = [];
  etat.gommeLargeur = 12;
  etat.coinRayon = 10;
  let geste = null;

  function tmpDoc() {
    const t = $("#ovTmp");
    if (!t) return null;
    t.innerHTML = "";
    const g = document.createElementNS(SNS, "g");
    g.setAttribute("transform", `translate(${etat.tx} ${etat.ty}) scale(${etat.zoom})`);
    t.appendChild(g);
    return g;
  }
  function forme(nom, attrs, hote) {
    const el = document.createElementNS(SNS, nom);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    hote.appendChild(el);
    return el;
  }
  const dEtat = (pts) => pts.length ? "M " + pts.map(([x, y]) => `${x} ${y}`).join(" L ") : "";
  const cibles = () => etat.selection.length ? etat.selection.slice()
    : etat.doc.calques.filter((c) => c.visible && !c.verrou).flatMap((c) => c.objets.map((o) => o.id));

  /* ── pointerdown en CAPTURE : poignées de forme, pivot, ancres multiples, outils ── */
  stage.addEventListener("pointerdown", (ev) => {
    if (ev.button !== 0 || !etat.doc) return;
    const t = ev.target;
    const [dx, dy] = VL.docPt(ev.clientX, ev.clientY);
    const pf = t.closest && t.closest(".poignee-forme");
    if (pf && etat.outil === "select") {
      geste = { type: "forme-poignee", id: pf.dataset.forme, cle: pf.dataset.cle, patch: null };
      ev.stopPropagation(); ev.preventDefault(); return;
    }
    const pp = t.closest && t.closest(".poignee-pivot");
    if (pp && etat.outil === "select") {
      geste = { type: "pivot" };
      ev.stopPropagation(); ev.preventDefault(); return;
    }
    if (etat.outil === "noeuds") {
      const anc = t.closest && t.closest(".ancre");
      const p = VL.pathSelectionne();
      if (anc && p && etat.ancresSel.length > 1 && etat.ancresSel.includes(+anc.dataset.ancre)) {
        geste = { type: "ancres", id: p.id, x0: dx, y0: dy, dxA: 0, dyA: 0, segs: chemin_parser(p.d), d0: p.d, d: null };
        VL.apercuNoeuds.debut(p.id, geste.segs);   // R12 : segs parsés une fois, aucun clone
        ev.stopPropagation(); ev.preventDefault(); return;
      }
      if (anc && ev.shiftKey && p) {
        const i = +anc.dataset.ancre;
        etat.ancresSel = etat.ancresSel.includes(i) ? etat.ancresSel.filter((k) => k !== i) : etat.ancresSel.concat(i);
        etat.ancreSel = etat.ancresSel.length === 1 ? etat.ancresSel[0] : null;
        VL.rendreOverlay(); rendreNoeuds();
        ev.stopPropagation(); ev.preventDefault(); return;
      }
      if (!anc && p && !(t.closest && t.closest("[data-objet]"))) {
        geste = { type: "lasso-ancres", id: p.id, x0: dx, y0: dy, x1: dx, y1: dy, shift: ev.shiftKey };
        ev.stopPropagation(); ev.preventDefault(); return;
      }
      return;
    }
    if (etat.outil === "forme") {
      const [ax, ay] = VL.aimantePt(dx, dy);
      geste = { type: "forme", cx: ax, cy: ay, r: 0 };
      ev.stopPropagation(); ev.preventDefault(); return;
    }
    if (etat.outil === "crayon") {
      geste = { type: "crayon", points: [[dx, dy]] };
      ev.stopPropagation(); ev.preventDefault(); return;
    }
    if (etat.outil === "couteau") {
      geste = { type: "couteau", x0: dx, y0: dy, x1: dx, y1: dy };
      ev.stopPropagation(); ev.preventDefault(); return;
    }
    if (etat.outil === "gomme") {
      geste = { type: "gomme", points: [[dx, dy]] };
      ev.stopPropagation(); ev.preventDefault(); return;
    }
    if (etat.outil === "coin") {
      const cible = t.closest && t.closest("[data-objet]");
      if (cible) {
        const id = VL.sommetDe(cible.dataset.objet) || cible.dataset.objet;
        const n = VL.executer(op_coins_arrondir, [id], etat.coinRayon);
        if (n !== undefined) VL.toast(`${n} coin(s) arrondi(s) à ${etat.coinRayon} px`);
      }
      ev.stopPropagation(); ev.preventDefault(); return;
    }
    if (etat.outil === "constructeur") {
      if (etat.selection.length < 2) { VL.toast("constructeur : sélectionner deux formes au moins", true); ev.stopPropagation(); return; }
      etat.atomesChoisis.push({ x: dx, y: dy });
      VL.rendreOverlay();
      VL.toast(`${etat.atomesChoisis.length} région(s) choisie(s) — Entrée fusionne, Alt+Entrée retire, Échap annule`);
      ev.stopPropagation(); ev.preventDefault(); return;
    }
  }, true);

  stage.addEventListener("pointermove", (ev) => {
    if (!geste) return;
    const [dx, dy] = VL.docPt(ev.clientX, ev.clientY);
    const g = tmpDoc();
    if (geste.type === "forme") {
      const [ax, ay] = VL.aimantePt(dx, dy);
      geste.r = Math.max(1, Math.hypot(ax - geste.cx, ay - geste.cy));
      const o = forme_defaut(etat.formeCourante, geste.cx, geste.cy, geste.r);
      if (g) forme("path", { d: forme_d(o), fill: "rgba(157,180,214,.25)", stroke: "#5b82b8", "stroke-width": 1.5 / etat.zoom }, g);
    } else if (geste.type === "crayon" || geste.type === "gomme") {
      geste.points.push([dx, dy]);
      if (g) forme("path", { d: dEtat(geste.points), fill: "none", stroke: geste.type === "gomme" ? "#d0553a" : "#5b82b8",
        "stroke-width": geste.type === "gomme" ? etat.gommeLargeur : 2 / etat.zoom, "stroke-linecap": "round", "stroke-linejoin": "round",
        opacity: geste.type === "gomme" ? 0.5 : 1 }, g);
    } else if (geste.type === "couteau") {
      geste.x1 = dx; geste.y1 = dy;
      if (g) forme("line", { x1: geste.x0, y1: geste.y0, x2: dx, y2: dy, stroke: "#d0553a", "stroke-width": 1.5 / etat.zoom, "stroke-dasharray": `${5 / etat.zoom} ${4 / etat.zoom}` }, g);
    } else if (geste.type === "forme-poignee") {
      const t = VL.objetDe(geste.id);
      if (!t) return;
      geste.patch = forme_poignee_deplacer(t.objet, geste.cle, dx, dy);
      const el = document.querySelector(`#canvasHost [data-objet="${geste.id}"]`);
      if (el) el.setAttribute("d", forme_d({ ...t.objet, ...geste.patch, params: { ...t.objet.params, ...(geste.patch.params || {}) } }));
    } else if (geste.type === "pivot") {
      etat.pivot = [dx, dy];
      VL.rendreOverlay();
    } else if (geste.type === "lasso-ancres") {
      geste.x1 = dx; geste.y1 = dy;
      if (g) forme("rect", { x: Math.min(geste.x0, dx), y: Math.min(geste.y0, dy), width: Math.abs(dx - geste.x0), height: Math.abs(dy - geste.y0),
        fill: "rgba(224,179,74,.12)", stroke: "#e0b34a", "stroke-width": 1 / etat.zoom, "stroke-dasharray": `${4 / etat.zoom} ${3 / etat.zoom}` }, g);
    } else if (geste.type === "ancres") {
      const [ax, ay] = etat.aimantNoeuds === false ? [dx, dy] : VL.aimantePt(dx, dy);   // R10 : magnétisme aux nœuds séparé
      geste.dxA = ax - geste.x0; geste.dyA = ay - geste.y0;
      const segs = noeuds_deplacer_segs(geste.segs, etat.ancresSel, geste.dxA, geste.dyA);
      geste.d = chemin_serialiser(segs);
      VL.apercuNoeuds.poser(segs, geste.d);      // R12 : chemin + overlay au curseur
    }
  });

  stage.addEventListener("pointerup", (ev) => {
    if (!geste) return;
    const g = geste;
    geste = null;
    const t = $("#ovTmp"); if (t) t.innerHTML = "";
    if (g.type === "forme") {
      const r = g.r < 2 ? 40 : g.r;                 // clic sans glisser : la forme au rayon 40
      const o = forme_defaut(etat.formeCourante, g.cx, g.cy, r);
      if (etat.formeCourante !== "spirale" && etat.formeCourante !== "donut") o.style = { ...etat.styleCourant };
      const id = VL.executer(op_ajouter, etat.calqueActif, o);
      if (id) { VL.setOutil("select"); VL.setSelection([id]); }
    } else if (g.type === "crayon") {
      if (g.points.length < 2) return;
      try {
        const d = lisser_vers_d(g.points, { tol: 1.5 / etat.zoom, fermer: true });
        const ferme = d.endsWith("Z");
        const id = VL.executer(op_ajouter, etat.calqueActif, { type: "path", d,
          style: ferme ? { ...etat.styleCourant } : { fond: "none", contour: etat.styleCourant.contour || "#1F1512", epaisseur: etat.styleCourant.epaisseur || 2 } });
        if (id) VL.setSelection([id]);
      } catch (e) { VL.toast(e.message, true); }
    } else if (g.type === "couteau") {
      if (Math.hypot(g.x1 - g.x0, g.y1 - g.y0) < 2) return;
      const ids = VL.executer(op_couteau, cibles(), [g.x0, g.y0, g.x1, g.y1]);
      if (ids) { VL.setSelection(ids); VL.toast(`${ids.length} morceau(x)`); }
    } else if (g.type === "gomme") {
      const ids = VL.executer(op_gomme, cibles(), dEtat(g.points), etat.gommeLargeur);
      if (ids) VL.setSelection(ids);
    } else if (g.type === "forme-poignee") {
      if (g.patch) VL.executer(op_forme_param, g.id, g.patch); else VL.rendre();
    } else if (g.type === "pivot") {
      VL.rendreOverlay();
    } else if (g.type === "lasso-ancres") {
      const p = VL.pathSelectionne();
      if (!p) return;
      const r = { x: Math.min(g.x0, g.x1), y: Math.min(g.y0, g.y1), w: Math.abs(g.x1 - g.x0), h: Math.abs(g.y1 - g.y0) };
      const dans = ancres_dans_rect(chemin_parser(p.d), r);
      etat.ancresSel = g.shift ? [...new Set(etat.ancresSel.concat(dans))] : dans;
      etat.ancreSel = etat.ancresSel.length === 1 ? etat.ancresSel[0] : null;
      VL.rendreOverlay(); rendreNoeuds();
    } else if (g.type === "ancres") {
      const fin = VL.apercuNoeuds.fin();          // R12 : pose ce qui est affiché
      if (fin && fin.d && fin.d !== g.d0) {
        VL.executer((doc) => {
          const o = doc.calques.flatMap((c) => c.objets).find((x) => x.id === g.id);
          if (!o) throw new Error("chemin introuvable");
          o.d = fin.d;
        });
      } else VL.rendre();
    }
  });

  /* ── overlay : poignées de forme, pivot, ancres multiples, atomes ── */
  // le cœur appelle SA rendreOverlay locale : on se greffe par le hook surOverlay
  VL.surOverlay = (o) => {
    if (!o || !etat.doc) return;
    const ov = (nom, attrs) => { const el = document.createElementNS(SNS, nom); for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v); o.appendChild(el); return el; };
    if (etat.outil === "select" && etat.selection.length === 1) {
      const t = VL.objetDe(etat.selection[0]);
      if (t && t.objet.type === "forme") {
        for (const p of forme_poignees(t.objet)) {
          const [ex, ey] = VL.ecranPt(p.x, p.y);
          ov("circle", { cx: ex, cy: ey, r: 6, fill: "#e0b34a", stroke: "#1F1512", class: "poignee-forme", "data-forme": t.objet.id, "data-cle": p.cle });
        }
      }
    }
    if (etat.outil === "select" && etat.selection.length) {
      const b = VL.bboxSelectionDoc();
      if (b) {
        const piv = etat.pivot || [b.x + b.w / 2, b.y + b.h / 2];
        const [ex, ey] = VL.ecranPt(piv[0], piv[1]);
        ov("circle", { cx: ex, cy: ey, r: 5, fill: "none", stroke: "#39b3d0", "stroke-width": 1.5, class: "poignee-pivot", "data-pivot": "1" });
        ov("line", { x1: ex - 8, y1: ey, x2: ex + 8, y2: ey, stroke: "#39b3d0", "pointer-events": "none" });
        ov("line", { x1: ex, y1: ey - 8, x2: ex, y2: ey + 8, stroke: "#39b3d0", "pointer-events": "none" });
      }
    }
    if (etat.outil === "noeuds" && etat.ancresSel.length > 1) {
      o.querySelectorAll(".ancre").forEach((el) => { if (etat.ancresSel.includes(+el.dataset.ancre)) el.setAttribute("fill", "#e0b34a"); });
    }
    if (etat.outil === "constructeur") {
      for (const p of etat.atomesChoisis) {
        const [ex, ey] = VL.ecranPt(p.x, p.y);
        ov("circle", { cx: ex, cy: ey, r: 7, fill: "rgba(224,179,74,.6)", stroke: "#1F1512", class: "atome-choisi", "pointer-events": "none" });
      }
    }
  };

  /* ── clavier : Entrée / Échap du constructeur, Suppr des ancres multiples ── */
  const suivantTouche = VL.surTouche;
  VL.surTouche = (ev) => {
    if (etat.outil === "constructeur") {
      if (ev.key === "Enter") {
        const id = VL.executer(op_constructeur, etat.selection.slice(), etat.atomesChoisis.slice(), ev.altKey ? "retirer" : "fusionner");
        etat.atomesChoisis = [];
        if (id) { VL.setSelection([id]); VL.setOutil("select"); }
        ev.preventDefault(); return;
      }
      if (ev.key === "Escape") { etat.atomesChoisis = []; VL.rendreOverlay(); return; }
    }
    if (etat.outil === "noeuds" && (ev.key === "Delete" || ev.key === "Backspace") && etat.ancresSel.length > 1) {
      const p = VL.pathSelectionne();
      if (p) {
        const n = chemin_ancres(chemin_parser(p.d)).length;
        if (n - etat.ancresSel.length < 2) VL.executer(op_supprimer, [p.id]);
        else {
          const sel = etat.ancresSel.slice().sort((a, b) => b - a);
          VL.executer((doc) => { for (const i of sel) VL.opNoeudSupprimer(doc, p.id, i); });
        }
        etat.ancresSel = []; etat.ancreSel = null;
        ev.preventDefault(); return;
      }
    }
    suivantTouche(ev);
  };

  /* ── panneaux : Forme (formes + gomme + coin), Nœuds, Instantanés ── */
  const hF = $("#panneauForme"), hN = $("#panneauNoeuds"), hI = $("#panneauInstantanes");
  function rendreForme() {
    if (!etat.doc) { hF.innerHTML = ""; return; }
    const t = etat.selection.length === 1 ? VL.objetDe(etat.selection[0]) : null;
    const o = t && t.objet.type === "forme" ? t.objet : null;
    hF.innerHTML = `
      <div class="ap-ligne"><span>Forme</span><i class="px-note">${(FORMES.find((f) => f.id === etat.formeCourante) || {}).nom || ""} — se choisit dans le menu du bouton Forme</i></div>
      ${o ? `<div class="ap-ligne"><span>Rayon</span><input type="number" id="fmR" step="any" min="1" value="${o.r}"/>
        <button id="fmCourbes" title="Fige la forme en chemin éditable (nœuds, booléens)">→ courbes</button></div>
      ${Object.entries(o.params).map(([k, v]) => `<div class="ap-ligne"><span>${k}</span>${k === "type"
        ? `<select data-fm="${k}"><option${v === "lineaire" ? " selected" : ""}>lineaire</option><option${v === "fibonacci" ? " selected" : ""}>fibonacci</option></select>`
        : `<input type="number" data-fm="${k}" step="${k === "ratio" ? 0.05 : 1}" value="${v}"/>`}</div>`).join("")}` : ""}
      <div class="ap-ligne"><span>Gomme</span><input type="number" id="fmGomme" min="1" value="${etat.gommeLargeur}" title="Largeur de la gomme (px)"/>
        <span>Coin</span><input type="number" id="fmCoin" min="1" value="${etat.coinRayon}" title="Rayon de l'outil Coin (px)"/></div>`;
    $("#fmGomme").addEventListener("change", (e) => { etat.gommeLargeur = Math.max(1, +e.target.value || 12); });
    $("#fmCoin").addEventListener("change", (e) => { etat.coinRayon = Math.max(1, +e.target.value || 10); });
    if (o) {
      $("#fmR").addEventListener("change", (e) => VL.executer(op_forme_param, o.id, { r: +e.target.value }));
      $("#fmCourbes").addEventListener("click", () => VL.executer(op_forme_en_chemin, o.id));
      hF.querySelectorAll("[data-fm]").forEach((el) => el.addEventListener("change", () => {
        const k = el.dataset.fm;
        const v = el.tagName === "SELECT" ? el.value : (k === "ratio" ? +el.value : (["n", "dents"].includes(k) ? Math.round(+el.value) : +el.value));
        VL.executer(op_forme_param, o.id, { params: { [k]: v } });
      }));
    }
  }
  function rendreNoeuds() {
    if (!etat.doc) { hN.innerHTML = ""; return; }
    const p = etat.outil === "noeuds" ? VL.pathSelectionne() : null;
    const deux = etat.selection.length === 2 && etat.selection.every((id) => { const t = VL.objetDe(id); return t && t.objet.type === "path"; });
    hN.innerHTML = `
      <div class="ap-ligne"><span>${p ? `${etat.ancresSel.length || (etat.ancreSel !== null ? 1 : 0)} ancre(s)` : "Nœuds"}</span>
        ${["gauche", "centreH", "droite", "haut", "centreV", "bas"].map((m) => `<button data-nal="${m}" ${p && etat.ancresSel.length > 1 ? "" : "disabled"} title="Aligner les ancres : ${m}">${{ gauche: "⇤", centreH: "⇹", droite: "⇥", haut: "⤒", centreV: "⇳", bas: "⤓" }[m]}</button>`).join("")}</div>
      <div class="ap-ligne"><span></span><i class="px-note">diviser, inverser, joindre, coins : menu du bouton Nœuds</i></div>`;
    hN.querySelectorAll("[data-nal]").forEach((b) => b.addEventListener("click", () => {
      if (p) VL.executer(op_noeuds_aligner, p.id, etat.ancresSel.slice(), b.dataset.nal);
    }));
  }
  VL.actions = VL.actions || {};
  VL.actions.noeuds = {
    diviser: () => { const p = VL.pathSelectionne(); if (p && etat.ancreSel !== null && etat.ancreSel > 0) { const i = VL.executer(op_noeud_inserer, p.id, etat.ancreSel, 0.5); if (i !== undefined) { etat.ancreSel = i; etat.ancresSel = [i]; VL.rendreOverlay(); } } else VL.toast("choisir d'abord une ancre (outil Nœuds)", true); },
    inverser: () => { const p = VL.pathSelectionne(); if (p) VL.executer(op_chemin_inverser, p.id); else VL.toast("sélectionner un chemin", true); },
    joindre: () => { if (etat.selection.length !== 2) { VL.toast("sélectionner deux chemins ouverts", true); return; } const id = VL.executer(op_chemins_joindre, etat.selection[0], etat.selection[1]); if (id) VL.setSelection([id]); },
    coins: () => { if (!etat.selection.length) return; const n = VL.executer(op_coins_arrondir, etat.selection.slice(), etat.coinRayon); if (n !== undefined) VL.toast(`${n} coin(s) arrondi(s)`); },
    peut: () => ({ chemin: !!VL.pathSelectionne(), ancre: VL.pathSelectionne() && etat.ancreSel !== null && etat.ancreSel > 0, deux: etat.selection.length === 2, sel: etat.selection.length > 0 }),
  };
  function rendreInstantanes() {
    if (!etat.doc) { hI.innerHTML = ""; return; }
    const noms = etat.histo.instantanes ? etat.histo.instantanes() : [];
    hI.innerHTML = `<div class="ap-ligne"><input type="text" id="insNom" placeholder="nom de l'instantané" style="flex:1"/>
        <button id="insPrendre" title="Garde l'état courant sous ce nom (session)">Prendre</button></div>
      ${noms.map((n) => `<div class="ap-ligne inst-ligne"><span class="nom" title="${n}">${n}</span><button data-ins="${n}" title="Revenir à cet état (annulable)">Restaurer</button></div>`).join("")}
      <p class="carte-attribution">historique : ${etat.histo._avant.length} pas (1 000 au plus)</p>`;
    $("#insPrendre").addEventListener("click", () => {
      const nom = $("#insNom").value.trim() || `état ${noms.length + 1}`;
      try { etat.histo.instantane(nom, etat.doc); VL.toast(`instantané « ${nom} » pris`); rendreInstantanes(); } catch (e) { VL.toast(e.message, true); }
    });
    hI.querySelectorAll("[data-ins]").forEach((b) => b.addEventListener("click", () => {
      VL.executer((doc) => { const r = etat.histo.restaurer(b.dataset.ins); for (const k of Object.keys(doc)) delete doc[k]; Object.assign(doc, r); });
      VL.setSelection([]);
    }));
  }

  const suivantRendu = VL.surRendu;
  VL.surRendu = () => { suivantRendu(); rendreForme(); rendreNoeuds(); rendreInstantanes(); };
  const suivantSel = VL.surSelection;
  VL.surSelection = () => { suivantSel(); etat.pivot = null; etat.ancresSel = []; rendreForme(); rendreNoeuds(); };
  const suivantOutil = VL.surOutil;
  VL.surOutil = () => { suivantOutil(); etat.atomesChoisis = []; if (etat.outil !== "noeuds") etat.ancresSel = []; rendreNoeuds();
    if (VL.majStatut) VL.majStatut(); else { const h = $("#hintOutil"); if (h && HINTS2[etat.outil]) h.textContent = HINTS2[etat.outil]; } };
  VL.hints = Object.assign(VL.hints || {}, HINTS2);
}
