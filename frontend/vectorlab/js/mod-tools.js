// mod-tools.js — la machine à gestes (T1.7). Chaque geste TRADUIT une
// intention en UNE commande pure (mod-doc) exécutée à la fin (pointerup) ;
// pendant le geste, seuls des APERÇUS bougent (overlay ou attributs DOM
// provisoires). Aucune mutation du document hors VL.executer.
import { op_ajouter, op_supprimer, op_deplacer, op_redimensionner, op_tourner,
         op_noeud_deplacer, op_noeud_convertir, op_noeud_supprimer,
         op_guide_ajouter, op_guide_deplacer, op_guide_supprimer, op_style,
         chemin_parser, chemin_serialiser, chemin_ancres } from "./mod-doc.js";

const SNS = "http://www.w3.org/2000/svg";

function _objetProfond(doc, id) {
  const chercher = (objs) => {
    for (const o of objs) {
      if (o.id === id) return o;
      if (o.type === "groupe") {
        const r = chercher(o.enfants || []);
        if (r) return r;
      }
    }
    return null;
  };
  for (const c of doc.calques) {
    const r = chercher(c.objets);
    if (r) return r;
  }
  return null;
}

export function initOutils(VL) {
  const { $, etat } = VL;
  const stage = $("#stage");
  let geste = null;          // le geste pointer en cours
  let trace = null;          // le chemin de plume en cours

  /* ── aperçus : un groupe en coordonnées DOCUMENT dans l'overlay ── */
  function tmp() {
    const t = $("#ovTmp");
    if (t) t.innerHTML = "";
    return t;
  }
  function tmpDoc() {
    const t = tmp();
    if (!t) return null;
    const g = document.createElementNS(SNS, "g");
    g.setAttribute("transform",
      `translate(${etat.tx} ${etat.ty}) scale(${etat.zoom})`);
    t.appendChild(g);
    return g;
  }
  function forme(nom, attrs, hote) {
    const el = document.createElementNS(SNS, nom);
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    (hote || $("#ovTmp")).appendChild(el);
    return el;
  }
  /* la COTE VIVE du geste (éditeur complet, E6) : un texte à halo posé
     près du curseur, en coordonnées document, dans l'unité d'affichage */
  function etiquette(g, x, y, texte) {
    if (!g || !texte) return;
    const t = forme("text", {
      x: x + 14 / etat.zoom, y: y - 10 / etat.zoom,
      "font-size": 12 / etat.zoom, fill: "#eef1f5",
      "paint-order": "stroke", stroke: "#101216",
      "stroke-width": 3 / etat.zoom, "stroke-linejoin": "round",
    }, g);
    t.textContent = texte;
  }

  function objetsSelectionnables() {
    const out = [];
    for (const c of etat.doc.calques) {
      if (!c.visible || c.verrou) continue;
      for (const o of c.objets) out.push(o.id);
    }
    return out;
  }
  function docContient(id) {
    for (const c of etat.doc.calques) {
      const o = c.objets.find((x) => x.id === id);
      if (o) return { calque: c, objet: o };
    }
    return null;
  }

  /* ═══════════ pointerdown : router le geste selon la cible ═══════════ */
  stage.addEventListener("pointerdown", (ev) => {
    if (ev.button !== 0 || !etat.doc) return;
    try { stage.setPointerCapture(ev.pointerId); } catch (e) { /* synthétique */ }
    const t = ev.target;
    const [dx, dy] = VL.docPt(ev.clientX, ev.clientY);

    const pgGrad = t.closest && t.closest(".poignee-grad");
    if (pgGrad && etat.outil === "select") {
      const [gid, role] = pgGrad.dataset.grad.split(":");
      geste = { type: "grad", gid, role, patch: null };
      ev.preventDefault();
      return;
    }

    const poignee = t.closest && t.closest(".poignee, .poignee-rot");
    if (poignee && etat.outil === "select" && etat.selection.length) {
      const b0 = VL.bboxSelectionDoc();
      if (poignee.dataset.poignee === "rot") {
        const cx = b0.x + b0.w / 2, cy = b0.y + b0.h / 2;
        geste = { type: "rot", cx, cy, a0: Math.atan2(dy - cy, dx - cx),
                  angle: 0 };
      } else {
        geste = { type: "resize", k: +poignee.dataset.poignee, b0,
                  b1: { ...b0 } };
      }
      ev.preventDefault();
      return;
    }

    const ancre = t.closest && t.closest(".ancre");
    if (ancre && etat.outil === "noeuds") {
      const p = VL.pathSelectionne();
      if (!p) return;
      etat.ancreSel = +ancre.dataset.ancre;
      geste = { type: "ancre", id: p.id, i: etat.ancreSel, x0: dx, y0: dy,
                docAvant: JSON.parse(JSON.stringify(etat.doc)) };
      VL.rendreOverlay();
      ev.preventDefault();
      return;
    }

    const guide = t.closest && t.closest(".guide");
    if (guide) {
      const [axe, i] = guide.dataset.guide.split(":");
      geste = { type: "guide-move", axe, i: +i, pos: null };
      ev.preventDefault();
      return;
    }

    const cible = t.closest && t.closest("[data-objet]");
    const idBrut = cible ? cible.dataset.objet : null;
    // cliquer un enfant de groupe sélectionne le GROUPE (remontée au sommet)
    const idCible = idBrut ? (VL.sommetDe(idBrut) || idBrut) : null;
    const selectionnable = idCible
      && objetsSelectionnables().includes(idCible);

    if (etat.outil === "pipette") {
      if (idBrut) {
        const o = _objetProfond(etat.doc, idBrut);
        if (o && o.style) {
          const pioche = {};
          for (const k of ["fond", "contour", "epaisseur", "pointilles",
                           "joint", "opacite"]) {
            if (k in o.style) pioche[k] = o.style[k];
          }
          etat.styleCourant = { ...etat.styleCourant, ...pioche };
          if (etat.selection.length) {
            VL.executer(op_style, etat.selection.slice(), pioche);
          } else {
            VL.toast("style adopté — les nouveaux objets le prendront");
            VL.surSelection();
          }
        }
      }
      return;
    }

    if (etat.outil === "select") {
      if (selectionnable) {
        let sel = etat.selection.slice();
        if (ev.shiftKey) {
          sel = sel.includes(idCible) ? sel.filter((x) => x !== idCible)
                                      : sel.concat(idCible);
          VL.setSelection(sel);
          return;                              // le shift ajuste, sans drag
        }
        if (!sel.includes(idCible)) VL.setSelection([idCible]);
        geste = { type: "move", x0: dx, y0: dy, dxA: 0, dyA: 0,
                  b0: VL.bboxSelectionDoc(),
                  origines: VL.selectionElems().map((el) =>
                    [el, el.getAttribute("transform") || ""]) };
      } else {
        geste = { type: "lasso", ex0: ev.clientX, ey0: ev.clientY,
                  shift: ev.shiftKey };
      }
      ev.preventDefault();
      return;
    }

    if (etat.outil === "rect" || etat.outil === "ellipse") {
      const [ax, ay] = VL.aimantePt(dx, dy);
      geste = { type: "trace-forme", forme: etat.outil, x0: ax, y0: ay,
                x1: ax, y1: ay, shift: ev.shiftKey };
      ev.preventDefault();
      return;
    }

    if (etat.outil === "ligne" || etat.outil === "mesure") {
      const [ax, ay] = VL.aimantePt(dx, dy);
      geste = { type: "trace-ligne", mesure: etat.outil === "mesure",
                x0: ax, y0: ay, x1: ax, y1: ay };
      ev.preventDefault();
      return;
    }

    if (etat.outil === "plume") {
      plumeDown(dx, dy, ev);
      ev.preventDefault();
      return;
    }

    if (etat.outil === "noeuds" && selectionnable) {
      const o = docContient(idCible);
      if (o && o.objet.type === "path") VL.setSelection([idCible]);
      return;
    }

    if (etat.outil === "texte") {
      const [ax, ay] = VL.aimantePt(dx, dy);
      const contenu = prompt("Texte :", "");
      if (contenu) {
        const sc = etat.styleCourant;
        const fill = (sc.fond && sc.fond !== "none"
                      && !String(sc.fond).startsWith("grad:"))
          ? sc.fond : (sc.contour && sc.contour !== "none"
                       ? sc.contour : "#1F1512");
        const id = VL.executer(op_ajouter, etat.calqueActif,
          { type: "texte", x: ax, y: ay, contenu,
            style: { fond: fill, police: "Segoe UI", corps: 24 } });
        if (id) { VL.setOutil("select"); VL.setSelection([id]); }
      }
      return;
    }
  });

  /* ═══════════ pointermove : les aperçus ═══════════ */
  stage.addEventListener("pointermove", (ev) => {
    if (etat.outil === "plume" && trace && !geste) {
      apercuPlume(...VL.docPt(ev.clientX, ev.clientY));
    }
    if (!geste) return;
    const [dx, dy] = VL.docPt(ev.clientX, ev.clientY);

    if (geste.type === "move") {
      const [cx, cy] = VL.aimantePt(geste.b0.x + (dx - geste.x0),
                                    geste.b0.y + (dy - geste.y0));
      geste.dxA = cx - geste.b0.x;
      geste.dyA = cy - geste.b0.y;
      for (const [el, orig] of geste.origines) {
        el.setAttribute("transform",
          `translate(${geste.dxA} ${geste.dyA})` + (orig ? " " + orig : ""));
      }
      VL.rendreOverlay();
      etiquette(tmpDoc(), dx, dy,
                VL.cote("delta", { dx: geste.dxA, dy: geste.dyA }));
    } else if (geste.type === "lasso") {
      const r = stage.getBoundingClientRect();
      const x = Math.min(geste.ex0, ev.clientX) - r.left;
      const y = Math.min(geste.ey0, ev.clientY) - r.top;
      const w = Math.abs(ev.clientX - geste.ex0);
      const h = Math.abs(ev.clientY - geste.ey0);
      tmp();
      forme("rect", { x, y, width: w, height: h, fill: "rgba(91,130,184,.12)",
                      stroke: "#5b82b8", "stroke-dasharray": "4 3" });
      geste.rect = { x: geste.ex0 < ev.clientX ? geste.ex0 : ev.clientX,
                     y: geste.ey0 < ev.clientY ? geste.ey0 : ev.clientY,
                     w, h };
    } else if (geste.type === "resize") {
      const b = { ...geste.b0 };
      const [ax, ay] = VL.aimantePt(dx, dy);
      const k = geste.k;
      if ([0, 6, 7].includes(k)) { b.w = b.x + b.w - ax; b.x = ax; }
      if ([2, 3, 4].includes(k)) { b.w = ax - b.x; }
      if ([0, 1, 2].includes(k)) { b.h = b.y + b.h - ay; b.y = ay; }
      if ([4, 5, 6].includes(k)) { b.h = ay - b.y; }
      if (geste.shiftOrig === undefined) geste.shiftOrig = ev.shiftKey;
      if (ev.shiftKey && geste.b0.w > 0 && geste.b0.h > 0) {
        const s = Math.max(Math.abs(b.w) / geste.b0.w,
                           Math.abs(b.h) / geste.b0.h);
        const w2 = geste.b0.w * s, h2 = geste.b0.h * s;
        if ([0, 6, 7].includes(k)) b.x = b.x + b.w - w2;
        if ([0, 1, 2].includes(k)) b.y = b.y + b.h - h2;
        b.w = w2; b.h = h2;
      }
      b.w = Math.max(1, b.w); b.h = Math.max(1, b.h);
      geste.b1 = b;
      const g = tmpDoc();
      if (g) {
        forme("rect", { x: b.x, y: b.y, width: b.w, height: b.h,
          fill: "none", stroke: "#5b82b8",
          "stroke-width": 1.5 / etat.zoom, "stroke-dasharray":
          `${4 / etat.zoom} ${3 / etat.zoom}` }, g);
        etiquette(g, ax, ay, VL.cote("rect", { w: b.w, h: b.h }));
      }
    } else if (geste.type === "rot") {
      let a = (Math.atan2(dy - geste.cy, dx - geste.cx) - geste.a0)
              * 180 / Math.PI;
      if (ev.shiftKey) a = Math.round(a / 15) * 15;
      geste.angle = Math.round(a * 10) / 10;
      const g = tmpDoc();
      if (g) {
        forme("line", { x1: geste.cx, y1: geste.cy, x2: dx, y2: dy,
          stroke: "#5b82b8", "stroke-width": 1 / etat.zoom }, g);
        forme("text", { x: dx, y: dy, fill: "#9db4d6",
          "font-size": 12 / etat.zoom }, g).textContent = geste.angle + "°";
      }
    } else if (geste.type === "trace-forme") {
      let [x1, y1] = VL.aimantePt(dx, dy);
      if (ev.shiftKey || geste.shift) {
        const cote = Math.max(Math.abs(x1 - geste.x0), Math.abs(y1 - geste.y0));
        x1 = geste.x0 + Math.sign(x1 - geste.x0 || 1) * cote;
        y1 = geste.y0 + Math.sign(y1 - geste.y0 || 1) * cote;
      }
      geste.x1 = x1; geste.y1 = y1;
      const g = tmpDoc();
      if (!g) return;
      const x = Math.min(geste.x0, x1), y = Math.min(geste.y0, y1);
      const w = Math.abs(x1 - geste.x0), h = Math.abs(y1 - geste.y0);
      const attrs = { fill: "rgba(157,180,214,.25)", stroke: "#5b82b8",
                      "stroke-width": 1.5 / etat.zoom };
      if (geste.forme === "rect") {
        forme("rect", { x, y, width: w, height: h, ...attrs }, g);
        etiquette(g, x1, y1, VL.cote("rect", { w, h }));
      } else {
        forme("ellipse", { cx: x + w / 2, cy: y + h / 2, rx: w / 2,
                           ry: h / 2, ...attrs }, g);
        etiquette(g, x1, y1, VL.cote("ellipse", { rx: w / 2, ry: h / 2 }));
      }
    } else if (geste.type === "trace-ligne") {
      let [x1, y1] = VL.aimantePt(dx, dy);
      if (ev.shiftKey) {                      // Maj : angles contraints à 45°
        const long = Math.hypot(x1 - geste.x0, y1 - geste.y0);
        const a = Math.round(Math.atan2(y1 - geste.y0, x1 - geste.x0)
                             / (Math.PI / 4)) * (Math.PI / 4);
        x1 = geste.x0 + Math.cos(a) * long;
        y1 = geste.y0 + Math.sin(a) * long;
      }
      geste.x1 = x1; geste.y1 = y1;
      const g = tmpDoc();
      if (!g) return;
      forme("line", { x1: geste.x0, y1: geste.y0, x2: x1, y2: y1,
        stroke: geste.mesure ? "#39b3d0" : "#5b82b8",
        "stroke-width": (geste.mesure ? 1.5 : 2) / etat.zoom,
        "stroke-dasharray": geste.mesure
          ? `${5 / etat.zoom} ${4 / etat.zoom}` : "none" }, g);
      etiquette(g, x1, y1, VL.cote("segment",
        { dx: x1 - geste.x0, dy: y1 - geste.y0 }));
    } else if (geste.type === "ancre") {
      const [ax, ay] = VL.aimantePt(dx, dy);
      geste.dxA = ax - geste.x0; geste.dyA = ay - geste.y0;
      const d2 = JSON.parse(JSON.stringify(geste.docAvant));
      op_noeud_deplacer(d2, geste.id, geste.i, geste.dxA, geste.dyA);
      let d = null;
      for (const c of d2.calques) {
        const o = c.objets.find((x) => x.id === geste.id);
        if (o) { d = o.d; break; }
      }
      const el = document.querySelector(
        `#canvasHost [data-objet="${geste.id}"]`);
      if (el && d) el.setAttribute("d", d);
    } else if (geste.type === "grad") {
      const [ax, ay] = VL.aimantePt(dx, dy);
      const gr = (etat.doc.degrades || {})[geste.gid];
      if (!gr) return;
      let patch;
      if (geste.role === "p1") patch = { x1: ax, y1: ay };
      else if (geste.role === "p2") patch = { x2: ax, y2: ay };
      else if (geste.role === "centre") patch = { cx: ax, cy: ay };
      else patch = { r: Math.max(1, Math.hypot(dx - gr.cx, dy - gr.cy)) };
      geste.patch = patch;
      const el = document.getElementById(geste.gid);   // aperçu live du defs
      if (el) {
        for (const [k, v] of Object.entries(patch)) el.setAttribute(k, v);
      }
    } else if (geste.type === "guide-move") {
      geste.pos = geste.axe === "v" ? dx : dy;
      const el = document.querySelector(
        `#overlay [data-guide="${geste.axe}:${geste.i}"]`);
      if (el) {
        if (geste.axe === "v") {
          const [ex] = VL.ecranPt(geste.pos, 0);
          el.setAttribute("x1", ex); el.setAttribute("x2", ex);
        } else {
          const [, ey] = VL.ecranPt(0, geste.pos);
          el.setAttribute("y1", ey); el.setAttribute("y2", ey);
        }
      }
    }
  });

  /* ═══════════ pointerup : UNE commande ═══════════ */
  stage.addEventListener("pointerup", (ev) => {
    if (etat.outil === "plume" && geste && geste.type === "plume-ancre") {
      plumeUp(...VL.docPt(ev.clientX, ev.clientY));
      geste = null;
      return;
    }
    if (!geste) return;
    const g = geste;
    geste = null;
    tmp();
    if (g.type === "move") {
      for (const [el, orig] of g.origines) {
        if (orig) el.setAttribute("transform", orig);
        else el.removeAttribute("transform");
      }
      if (g.dxA || g.dyA) {
        VL.executer(op_deplacer, etat.selection.slice(), g.dxA, g.dyA);
      } else VL.rendreOverlay();
    } else if (g.type === "lasso") {
      if (!g.rect) { if (!g.shift) VL.setSelection([]); return; }
      const touches = [];
      for (const id of objetsSelectionnables()) {
        const el = document.querySelector(`#canvasHost [data-objet="${id}"]`);
        if (!el) continue;
        const r = el.getBoundingClientRect();
        if (r.left < g.rect.x + g.rect.w && r.right > g.rect.x
            && r.top < g.rect.y + g.rect.h && r.bottom > g.rect.y) {
          touches.push(id);
        }
      }
      VL.setSelection(g.shift ? etat.selection.concat(touches) : touches);
    } else if (g.type === "resize") {
      VL.executer(op_redimensionner, etat.selection.slice(), g.b0, g.b1);
    } else if (g.type === "rot") {
      if (g.angle) {
        VL.executer(op_tourner, etat.selection.slice(), g.cx, g.cy, g.angle);
      } else VL.rendreOverlay();
    } else if (g.type === "trace-ligne") {
      if (g.mesure) return;                  // l'outil mesure ne crée RIEN
      if (Math.hypot(g.x1 - g.x0, g.y1 - g.y0) < 1) return;
      const id = VL.executer(op_ajouter, etat.calqueActif,
        { type: "path",
          d: `M${g.x0} ${g.y0} L${g.x1} ${g.y1}`,
          style: { fond: "none",
                   contour: etat.styleCourant.contour || "#1F1512",
                   epaisseur: etat.styleCourant.epaisseur || 3 } });
      if (id) VL.setSelection([id]);
    } else if (g.type === "trace-forme") {
      const w = Math.abs(g.x1 - g.x0), h = Math.abs(g.y1 - g.y0);
      if (w < 1 || h < 1) return;
      let objet;
      if (g.forme === "rect") {
        objet = { type: "rect", x: Math.min(g.x0, g.x1),
                  y: Math.min(g.y0, g.y1), w, h,
                  style: { ...etat.styleCourant } };
      } else {
        objet = { type: "ellipse", cx: (g.x0 + g.x1) / 2,
                  cy: (g.y0 + g.y1) / 2, rx: w / 2, ry: h / 2,
                  style: { ...etat.styleCourant } };
      }
      const id = VL.executer(op_ajouter, etat.calqueActif, objet);
      if (id) VL.setSelection([id]);
    } else if (g.type === "ancre") {
      const el = document.querySelector(`#canvasHost [data-objet="${g.id}"]`);
      if (el) {
        const avant = docContient(g.id);
        if (avant) el.setAttribute("d", avant.objet.d);
      }
      if (g.dxA || g.dyA) {
        VL.executer(op_noeud_deplacer, g.id, g.i, g.dxA, g.dyA);
      }
    } else if (g.type === "grad") {
      if (g.patch) VL.executer(VL.opDegradeModifier, g.gid, g.patch);
      else VL.rendreOverlay();
    } else if (g.type === "guide-move") {
      if (g.pos === null) return;
      const r = stage.getBoundingClientRect();
      const horsScene = g.axe === "v" ? ev.clientX < r.left
                                      : ev.clientY < r.top;
      if (horsScene) VL.executer(op_guide_supprimer, g.axe, g.i);
      else VL.executer(op_guide_deplacer, g.axe, g.i, Math.round(g.pos * 10) / 10);
    }
  });

  /* ═══════════ double-clic : conversion d'ancre ═══════════ */
  stage.addEventListener("dblclick", (ev) => {
    if (etat.outil === "select") {
      // rééditer un texte en place
      const el = ev.target.closest && ev.target.closest("[data-objet]");
      if (el) {
        const o = _objetProfond(etat.doc, el.dataset.objet);
        if (o && o.type === "texte") {
          const contenu = prompt("Texte :", o.contenu || "");
          if (contenu !== null) {
            const cibleId = o.id;
            VL.executer((doc) => {
              const c = _objetProfond(doc, cibleId);
              if (!c) throw new Error("texte introuvable");
              c.contenu = contenu;
            });
          }
          return;
        }
      }
    }
    if (etat.outil === "noeuds") {
      const ancre = ev.target.closest && ev.target.closest(".ancre");
      const p = VL.pathSelectionne();
      if (ancre && p) {
        VL.executer(op_noeud_convertir, p.id, +ancre.dataset.ancre);
        return;
      }
    }
    if (etat.outil === "plume" && trace) plumeFinir(false);
  });

  /* ═══════════ la plume ═══════════ */
  function plumeDown(dx, dy, ev) {
    const [ax, ay] = VL.aimantePt(dx, dy);
    if (trace && trace.ancres.length >= 2) {
      const p0 = trace.ancres[0];
      const [e0x, e0y] = VL.ecranPt(p0.x, p0.y);
      if (Math.hypot(ev.clientX - stage.getBoundingClientRect().left - e0x,
                     ev.clientY - stage.getBoundingClientRect().top - e0y) <= 7) {
        plumeFinir(true);              // clic sur la première ancre : fermer
        return;
      }
    }
    if (!trace) {
      trace = { segs: [{ c: "M", p: [ax, ay] }], ancres: [{ x: ax, y: ay }],
                sortante: null };
    } else {
      const prec = trace.ancres[trace.ancres.length - 1];
      if (trace.sortante) {
        trace.segs.push({ c: "C", p: [trace.sortante.x, trace.sortante.y,
                                      ax, ay, ax, ay] });
      } else {
        trace.segs.push({ c: "L", p: [ax, ay] });
      }
      trace.ancres.push({ x: ax, y: ay });
      void prec;
    }
    trace.sortante = null;
    geste = { type: "plume-ancre", ax, ay };
    apercuPlume(ax, ay);
  }
  stage.addEventListener("pointermove", (ev) => {
    if (!geste || geste.type !== "plume-ancre" || !trace) return;
    // glisser depuis l'ancre : poignées symétriques (entrante = miroir)
    const [dx, dy] = VL.docPt(ev.clientX, ev.clientY);
    const s = trace.segs[trace.segs.length - 1];
    const { ax, ay } = geste;
    if (Math.hypot(dx - ax, dy - ay) > 2 / etat.zoom) {
      if (s.c === "L") {
        const prec = trace.ancres[trace.ancres.length - 2];
        trace.segs[trace.segs.length - 1] =
          { c: "C", p: [prec.x, prec.y, 2 * ax - dx, 2 * ay - dy, ax, ay] };
      } else if (s.c === "C") {
        s.p[2] = 2 * ax - dx; s.p[3] = 2 * ay - dy;
      }
      trace.sortante = { x: dx, y: dy };
    }
    apercuPlume(dx, dy);
  });
  function plumeUp() { /* l'ancre est posée ; la sortante est mémorisée */ }
  function apercuPlume(cx, cy) {
    const g = tmpDoc();
    if (!g || !trace) return;
    const d = chemin_serialiser(trace.segs);
    forme("path", { d, fill: "none", stroke: "#5b82b8",
                    "stroke-width": 2 / etat.zoom }, g);
    const der = trace.ancres[trace.ancres.length - 1];
    forme("line", { x1: der.x, y1: der.y, x2: cx, y2: cy, stroke: "#8b93a0",
                    "stroke-width": 1 / etat.zoom,
                    "stroke-dasharray": `${3 / etat.zoom} ${3 / etat.zoom}` }, g);
    for (const a of trace.ancres) {
      forme("circle", { cx: a.x, cy: a.y, r: 3 / etat.zoom,
                        fill: "#eef1f5", stroke: "#2c4a75",
                        "stroke-width": 1 / etat.zoom }, g);
    }
    etiquette(g, cx, cy, VL.cote("segment",
      { dx: cx - der.x, dy: cy - der.y }));
  }
  function plumeFinir(fermer) {
    if (!trace) return;
    // le double-clic pose une ancre en double avant de finir : l'élaguer
    if (trace.ancres.length >= 2) {
      const a = trace.ancres[trace.ancres.length - 1];
      const b = trace.ancres[trace.ancres.length - 2];
      if (Math.hypot(a.x - b.x, a.y - b.y) < 0.5) {
        trace.segs.pop();
        trace.ancres.pop();
      }
    }
    if (trace.ancres.length >= 2) {
      const segs = trace.segs.slice();
      if (fermer) segs.push({ c: "Z", p: [] });
      const id = VL.executer(op_ajouter, etat.calqueActif,
        { type: "path", d: chemin_serialiser(segs),
          style: { fond: "none",
                   contour: etat.styleCourant.contour || "#1F1512",
                   epaisseur: etat.styleCourant.epaisseur || 3 } });
      if (id) VL.setSelection([id]);
    }
    trace = null;
    tmp();
  }

  /* ═══════════ guides tirés des règles ═══════════ */
  function regleVersGuide(cv, axe) {
    cv.addEventListener("pointerdown", (ev) => {
      const nouveau = { axe, pos: null };
      const move = (e2) => {
        const [dx, dy] = VL.docPt(e2.clientX, e2.clientY);
        nouveau.pos = axe === "v" ? dx : dy;
        const t = tmp();
        if (!t) return;
        const r = stage.getBoundingClientRect();
        if (axe === "v") {
          const [ex] = VL.ecranPt(nouveau.pos, 0);
          forme("line", { x1: ex, y1: 0, x2: ex, y2: r.height,
                          stroke: "#39b3d0", "stroke-dasharray": "5 4" });
        } else {
          const [, ey] = VL.ecranPt(0, nouveau.pos);
          forme("line", { x1: 0, y1: ey, x2: r.width, y2: ey,
                          stroke: "#39b3d0", "stroke-dasharray": "5 4" });
        }
      };
      const up = () => {
        document.removeEventListener("pointermove", move);
        document.removeEventListener("pointerup", up);
        tmp();
        if (nouveau.pos !== null) {
          VL.executer(op_guide_ajouter, axe,
                      Math.round(nouveau.pos * 10) / 10);
        }
      };
      document.addEventListener("pointermove", move);
      document.addEventListener("pointerup", up);
      ev.preventDefault();
    });
  }
  regleVersGuide($("#regleH"), "h");   // règle du haut → guide horizontal
  regleVersGuide($("#regleV"), "v");   // règle de gauche → guide vertical

  /* ═══════════ clavier (délégué par le core) ═══════════ */
  const FLECHES = { ArrowLeft: [-1, 0], ArrowRight: [1, 0],
                    ArrowUp: [0, -1], ArrowDown: [0, 1] };
  VL.surTouche = (ev) => {
    if (FLECHES[ev.key] && etat.selection.length) {
      const k = ev.shiftKey ? 10 : 1;
      VL.executer(op_deplacer, etat.selection.slice(),
                  FLECHES[ev.key][0] * k, FLECHES[ev.key][1] * k);
      ev.preventDefault();
      return;
    }
    if (ev.key === "Delete" || ev.key === "Backspace") {
      if (etat.outil === "noeuds" && etat.ancreSel !== null) {
        const p = VL.pathSelectionne();
        if (!p) return;
        const n = chemin_ancres(chemin_parser(p.d)).length;
        if (n <= 2) VL.executer(op_supprimer, [p.id]);
        else VL.executer(op_noeud_supprimer, p.id, etat.ancreSel);
        etat.ancreSel = null;
        VL.purgerSelection();
        VL.rendreOverlay();
        ev.preventDefault();
        return;
      }
      if (etat.selection.length) {
        VL.executer(op_supprimer, etat.selection.slice());
        VL.setSelection([]);
        ev.preventDefault();
      }
      return;
    }
    if (ev.key === "Enter" && etat.outil === "plume" && trace) {
      plumeFinir(false);
      return;
    }
    if (ev.key === "Escape") {
      if (etat.outil === "plume" && trace) { plumeFinir(false); return; }
      VL.setSelection([]);
    }
  };
  VL.surOutil = () => {
    if (trace) { trace = null; tmp(); }
    etat.ancreSel = null;
  };
}
