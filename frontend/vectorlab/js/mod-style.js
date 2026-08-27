// mod-style.js — le panneau Apparence (T2.5) : fond (couleur / aucun /
// dégradé linéaire ou radial), contour (couleur, épaisseur, pointillés,
// joint), opacité, ordre z, grouper/dégrouper, stops du dégradé. Chaque
// interaction = UNE commande via VL.executer ; le panneau reflète le
// premier objet sélectionné, sinon le style courant des nouveaux objets.
import { op_style, op_ordre, op_grouper, op_degrouper, op_degrade_creer,
         op_degrade_modifier, op_degrade_stop_ajouter,
         op_degrade_stop_modifier, op_degrade_stop_supprimer,
         op_deplacer, op_redimensionner, op_aligner, op_distribuer,
         op_miroir, op_rect_rayon }
  from "./mod-doc.js";
import { op_booleen, op_division } from "./mod-bool.js";

const POINTILLES = [["", "plein"], ["6 4", "tirets"], ["2 3", "points"]];
const JOINTS = ["round", "miter", "bevel"];

export function initStyle(VL) {
  const { $, etat } = VL;
  const hote = $("#panneauStyle");

  function objetReflete() {
    if (!etat.selection.length) return null;
    const t = VL.objetDe(etat.selection[0]);
    return t ? t.objet : null;
  }
  function styleReflete() {
    const o = objetReflete();
    return o ? (o.style || {}) : etat.styleCourant;
  }

  function appliquer(patch) {
    for (const [k, v] of Object.entries(patch)) {
      if (v === null) delete etat.styleCourant[k];
      else etat.styleCourant[k] = v;
    }
    if (etat.selection.length) {
      VL.executer(op_style, etat.selection.slice(), patch);
    } else rendrePanneau();
  }

  function degradeDefaut(type) {
    if (etat.selection.length !== 1) {
      VL.toast("sélectionne UN objet pour poser un dégradé", true);
      return;
    }
    const b = VL.bboxSelectionDoc();
    const sel = etat.selection.slice();
    const base = typeof styleReflete().fond === "string"
      && !styleReflete().fond.startsWith("grad:")
      && styleReflete().fond !== "none"
      ? styleReflete().fond : "#0047AB";
    const spec = type === "lineaire"
      ? { type, x1: b.x, y1: b.y + b.h / 2, x2: b.x + b.w,
          y2: b.y + b.h / 2,
          stops: [{ t: 0, couleur: base }, { t: 1, couleur: "#FFFFFF" }] }
      : { type, cx: b.x + b.w / 2, cy: b.y + b.h / 2,
          r: Math.max(b.w, b.h) / 2,
          stops: [{ t: 0, couleur: "#FFFFFF" }, { t: 1, couleur: base }] };
    VL.executer((doc) => {          // une seule entrée d'historique
      const id = op_degrade_creer(doc, spec);
      op_style(doc, sel, { fond: "grad:" + id });
    });
  }

  function fondDegradeId() {
    const f = styleReflete().fond;
    return (typeof f === "string" && f.startsWith("grad:")) ? f.slice(5) : null;
  }

  /* la bbox DOCUMENT d'un objet, mesurée au DOM (contour compris) — les
     ops d'alignement restent pures, c'est l'écran qui mesure (E8) */
  function bboxDocDe(id) {
    const el = document.querySelector(`#canvasHost [data-objet="${id}"]`);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const r0 = $("#stage").getBoundingClientRect();
    return { x: (r.left - r0.left - etat.tx) / etat.zoom,
             y: (r.top - r0.top - etat.ty) / etat.zoom,
             w: r.width / etat.zoom, h: r.height / etat.zoom };
  }
  function pairesSelection() {
    return etat.selection
      .map((id) => ({ id, bbox: bboxDocDe(id) }))
      .filter((p) => p.bbox);
  }
  function reunion(paires) {
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (const { bbox: b } of paires) {
      x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y);
      x1 = Math.max(x1, b.x + b.w); y1 = Math.max(y1, b.y + b.h);
    }
    return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
  }

  function rendrePanneau() {
    if (!etat.doc) { hote.innerHTML = ""; return; }
    const s = styleReflete();
    const fondCouleur = (typeof s.fond === "string" && s.fond.startsWith("#"))
      ? s.fond : "#9DB4D6";
    const gid = fondDegradeId();
    const g = gid && etat.doc.degrades ? etat.doc.degrades[gid] : null;
    const sel = etat.selection.length;
    const b = sel ? VL.bboxSelectionDoc() : null;
    const nv = (px) => Math.round(VL.versUnite(px) * 100) / 100;
    const suf = VL.unites().affichage;
    hote.innerHTML = `
      ${b ? `
      <div class="ap-ligne"><span>X · Y</span>
        <input type="number" id="apX" step="any" value="${nv(b.x)}"
               title="X de la sélection (${suf})"/>
        <input type="number" id="apY" step="any" value="${nv(b.y)}"
               title="Y de la sélection (${suf})"/>
      </div>
      <div class="ap-ligne"><span>L · H</span>
        <input type="number" id="apW" step="any" value="${nv(b.w)}"
               title="Largeur (${suf})"/>
        <input type="number" id="apH" step="any" value="${nv(b.h)}"
               title="Hauteur (${suf})"/>
      </div>
      <div class="ap-ligne"><span>Aligner</span>
        <button data-al="gauche" title="Aligner à gauche (un seul objet : sur la page)">⇤</button>
        <button data-al="centreH" title="Centrer horizontalement">⇔</button>
        <button data-al="droite" title="Aligner à droite">⇥</button>
        <button data-al="haut" title="Aligner en haut">⇧</button>
        <button data-al="centreV" title="Centrer verticalement">⇕</button>
        <button data-al="bas" title="Aligner en bas">⇩</button>
      </div>
      <div class="ap-ligne"><span></span>
        <button data-dist="h" ${sel >= 3 ? "" : "disabled"}
                title="Distribuer horizontalement (écarts égaux, 3 objets au moins)">⇹</button>
        <button data-dist="v" ${sel >= 3 ? "" : "disabled"}
                title="Distribuer verticalement">⇳</button>
        <button data-mir="h" title="Miroir horizontal (géométrie brute — un objet tourné réfléchit sa géométrie)">◧↔◨</button>
        <button data-mir="v" title="Miroir vertical">⬒↕⬓</button>
        <button id="apDupliquer" title="Dupliquer la sélection (Ctrl+D)">⧉+</button>
      </div>` : ""}`;
    hote.innerHTML += `
      <div class="ap-ligne"><span>Fond</span>
        <button class="nu-pastille" id="apFond" style="background:${fondCouleur}"
                data-hex="${fondCouleur}"
                title="Couleur de fond — ouvre le nuancier (RGB, CMJN, hex, palettes)"></button>
        <button id="apFondAucun" class="${s.fond === "none" ? "actif" : ""}"
                title="Sans fond">∅</button>
        <button id="apGradL" title="Dégradé linéaire (sélection unique)">▤</button>
        <button id="apGradR" title="Dégradé radial (sélection unique)">◉</button>
      </div>
      <div class="ap-ligne"><span>Contour</span>
        <button class="nu-pastille" id="apContour"
                style="background:${s.contour && s.contour !== "none" ? s.contour : "#1F1512"}"
                data-hex="${s.contour && s.contour !== "none" ? s.contour : "#1F1512"}"
                title="Couleur de contour — ouvre le nuancier"></button>
        <button id="apContourAucun"
                class="${!s.contour || s.contour === "none" ? "actif" : ""}"
                title="Sans contour">∅</button>
        <input type="number" id="apEpaisseur" min="0.5" max="200" step="0.5"
               value="${s.epaisseur ?? 2}" title="Épaisseur"/>
      </div>
      <div class="ap-ligne"><span>Trait</span>
        <select id="apPointilles" title="Pointillés">${POINTILLES.map(
          ([v, l]) => `<option value="${v}"${(s.pointilles || "") === v
            ? " selected" : ""}>${l}</option>`).join("")}</select>
        <select id="apJoint" title="Joint des angles">${JOINTS.map(
          (j) => `<option${(s.joint || "round") === j ? " selected" : ""}>${j}
          </option>`).join("")}</select>
      </div>
      <div class="ap-ligne"><span>Opacité</span>
        <input type="range" id="apOpacite" min="0" max="100"
               value="${Math.round((s.opacite ?? 1) * 100)}"/>
        <b id="apOpaciteVal">${Math.round((s.opacite ?? 1) * 100)}</b>
      </div>
      <div class="ap-ligne"><span>Ordre</span>
        <button data-ordre="devant" title="Tout devant">⤒</button>
        <button data-ordre="avant" title="Un cran devant">↑</button>
        <button data-ordre="arriere" title="Un cran derrière">↓</button>
        <button data-ordre="derriere" title="Tout derrière">⤓</button>
      </div>
      <div class="ap-ligne">
        <button id="apGrouper" ${sel >= 2 ? "" : "disabled"}
                title="Grouper la sélection (les transformations deviennent communes)">Grouper</button>
        <button id="apDegrouper" ${sel === 1 && objetReflete()
          && objetReflete().type === "groupe" ? "" : "disabled"}
                title="Dissoudre le groupe (son transform suit les enfants)">Dégrouper</button>
      </div>
      <div class="ap-ligne"><span>Booléens</span>
        <button data-bool="union" ${sel >= 2 ? "" : "disabled"}
                title="Union — fusionne la sélection en un chemin">∪</button>
        <button data-bool="soustraction" ${sel >= 2 ? "" : "disabled"}
                title="Soustraction — le plus BAS moins les autres">⊖</button>
        <button data-bool="intersection" ${sel >= 2 ? "" : "disabled"}
                title="Intersection — la partie commune">∩</button>
        <button data-bool="division" ${sel >= 2 ? "" : "disabled"}
                title="Division — le preset vitrail : la plaque (le plus BAS) est découpée par les autres — un plomb TRACÉ découpe par son épaisseur — en fragments indépendants ; les plombs restent">⧉</button>
      </div>
      ${objetReflete() && objetReflete().type === "rect" ? `
      <div class="ap-ligne"><span>Rayon</span>
        <input type="number" id="apRayon" min="0" step="1"
               value="${objetReflete().rx || 0}"
               title="Rayon d'angle du rectangle (px du document, borné à min(L,H)/2 ; 0 = angles vifs)"/>
      </div>` : ""}
      ${objetReflete() && objetReflete().type === "texte" ? `
      <div class="ap-ligne"><span>Fonte</span>
        <input type="text" id="apPolice" value="${s.police || "Segoe UI"}"
               title="Famille de fonte" style="width:90px"/>
        <input type="number" id="apCorps" min="4" max="400"
               value="${s.corps || 16}" title="Corps"/>
      </div>
      <div class="ap-ligne"><span></span>
        <select id="apGraisse" title="Graisse">${["normal", "bold", "300",
          "600", "800"].map((g) => `<option${(s.graisse || "normal") === g
          ? " selected" : ""}>${g}</option>`).join("")}</select>
        <input type="number" id="apInterlettrage" step="0.5" min="-10"
               max="40" value="${s.interlettrage || 0}"
               title="Interlettrage"/>
      </div>` : ""}
      ${g ? `<div class="ap-stops" title="Stops du dégradé du fond">
        ${g.stops.map((st, i) => `<div class="ap-stop">
          <button class="nu-pastille" data-stop="${i}"
                  style="background:${st.couleur}" data-hex="${st.couleur}"
                  title="Couleur du stop — ouvre le nuancier"></button>
          <input type="number" data-stopt="${i}" min="0" max="100"
                 value="${Math.round(st.t * 100)}"/>%
          <button data-stopx="${i}" title="Retirer ce stop">✕</button>
        </div>`).join("")}
        <button id="apStopPlus" title="Ajouter un stop médian">＋ stop</button>
      </div>` : ""}`;

    if (b) {
      const majPos = (patch) => {
        const b0 = VL.bboxSelectionDoc();
        if (!b0) return;
        const sel2 = etat.selection.slice();
        if ("x" in patch || "y" in patch) {
          const dx = "x" in patch ? VL.depuisUnite(patch.x) - b0.x : 0;
          const dy = "y" in patch ? VL.depuisUnite(patch.y) - b0.y : 0;
          if (dx || dy) VL.executer(op_deplacer, sel2, dx, dy);
        } else {
          const b1 = { ...b0 };
          if ("w" in patch) b1.w = Math.max(1, VL.depuisUnite(patch.w));
          if ("h" in patch) b1.h = Math.max(1, VL.depuisUnite(patch.h));
          if (b1.w !== b0.w || b1.h !== b0.h) {
            VL.executer(op_redimensionner, sel2, b0, b1);
          }
        }
      };
      $("#apX").addEventListener("change", (e) => majPos({ x: +e.target.value }));
      $("#apY").addEventListener("change", (e) => majPos({ y: +e.target.value }));
      $("#apW").addEventListener("change", (e) => majPos({ w: +e.target.value }));
      $("#apH").addEventListener("change", (e) => majPos({ h: +e.target.value }));
      hote.querySelectorAll("[data-al]").forEach((btn) =>
        btn.addEventListener("click", () => {
          const paires = pairesSelection();
          if (!paires.length) return;
          // UN objet s'aligne sur LA PAGE, plusieurs sur leur réunion
          const ref = paires.length === 1
            ? { x: 0, y: 0, w: etat.doc.taille.w, h: etat.doc.taille.h }
            : reunion(paires);
          VL.executer(op_aligner, paires, btn.dataset.al, ref);
        }));
      hote.querySelectorAll("[data-dist]").forEach((btn) =>
        btn.addEventListener("click", () => {
          const paires = pairesSelection();
          if (paires.length >= 3) {
            VL.executer(op_distribuer, paires, btn.dataset.dist);
          }
        }));
      hote.querySelectorAll("[data-mir]").forEach((btn) =>
        btn.addEventListener("click", () => {
          const paires = pairesSelection();
          if (!paires.length) return;
          VL.executer(op_miroir, etat.selection.slice(), btn.dataset.mir,
                      reunion(paires));
        }));
      $("#apDupliquer").addEventListener("click", VL.dupliquerSelection);
    }
    if (objetReflete() && objetReflete().type === "rect") {
      $("#apRayon").addEventListener("change", (e) => VL.executer(
        op_rect_rayon, etat.selection.slice(),
        Math.max(0, +e.target.value || 0)));
    }
    $("#apFond").addEventListener("click", (e) =>
      VL.ouvrirNuancier(e.currentTarget.dataset.hex,
                        (hex) => appliquer({ fond: hex }), e.currentTarget));
    $("#apFondAucun").addEventListener("click",
      () => appliquer({ fond: "none" }));
    $("#apGradL").addEventListener("click", () => degradeDefaut("lineaire"));
    $("#apGradR").addEventListener("click", () => degradeDefaut("radial"));
    $("#apContour").addEventListener("click", (e) =>
      VL.ouvrirNuancier(e.currentTarget.dataset.hex,
                        (hex) => appliquer({ contour: hex }), e.currentTarget));
    $("#apContourAucun").addEventListener("click",
      () => appliquer({ contour: null }));
    $("#apEpaisseur").addEventListener("change",
      (e) => appliquer({ epaisseur: Math.max(0.5, +e.target.value || 1) }));
    $("#apPointilles").addEventListener("change",
      (e) => appliquer({ pointilles: e.target.value || null }));
    $("#apJoint").addEventListener("change",
      (e) => appliquer({ joint: e.target.value === "round"
                                ? null : e.target.value }));
    $("#apOpacite").addEventListener("input",
      (e) => { $("#apOpaciteVal").textContent = e.target.value; });
    $("#apOpacite").addEventListener("change",
      (e) => appliquer({ opacite: +e.target.value === 100
                                  ? null : +e.target.value / 100 }));
    hote.querySelectorAll("[data-ordre]").forEach((b) =>
      b.addEventListener("click", () => {
        if (etat.selection.length) {
          VL.executer(op_ordre, etat.selection.slice(), b.dataset.ordre);
        }
      }));
    $("#apGrouper").addEventListener("click", () => {
      const id = VL.executer(op_grouper, etat.selection.slice());
      if (id) VL.setSelection([id]);
    });
    $("#apDegrouper").addEventListener("click", () => {
      const ids = VL.executer(op_degrouper, etat.selection[0]);
      if (ids) VL.setSelection(ids);
    });
    hote.querySelectorAll("[data-bool]").forEach((b) =>
      b.addEventListener("click", () => {
        const sel2 = etat.selection.slice();
        if (sel2.length < 2) return;
        if (b.dataset.bool === "division") {
          const ids = VL.executer(op_division, sel2);
          if (ids) VL.setSelection(ids);
        } else {
          const id = VL.executer(op_booleen, sel2, b.dataset.bool);
          if (id) VL.setSelection([id]);
        }
      }));
    if (objetReflete() && objetReflete().type === "texte") {
      $("#apPolice").addEventListener("change",
        (e) => appliquer({ police: e.target.value || null }));
      $("#apCorps").addEventListener("change",
        (e) => appliquer({ corps: Math.max(4, +e.target.value || 16) }));
      $("#apGraisse").addEventListener("change",
        (e) => appliquer({ graisse: e.target.value === "normal"
                                    ? null : e.target.value }));
      $("#apInterlettrage").addEventListener("change",
        (e) => appliquer({ interlettrage: +e.target.value || null }));
    }
    if (g) {
      hote.querySelectorAll("[data-stop]").forEach((btn) =>
        btn.addEventListener("click", () => VL.ouvrirNuancier(
          btn.dataset.hex,
          (hex) => VL.executer(op_degrade_stop_modifier, gid,
                               +btn.dataset.stop, { couleur: hex }),
          btn)));
      hote.querySelectorAll("[data-stopt]").forEach((inp) =>
        inp.addEventListener("change", () => VL.executer(
          op_degrade_stop_modifier, gid, +inp.dataset.stopt,
          { t: Math.max(0, Math.min(1, +inp.value / 100)) })));
      hote.querySelectorAll("[data-stopx]").forEach((b) =>
        b.addEventListener("click", () => VL.executer(
          op_degrade_stop_supprimer, gid, +b.dataset.stopx)));
      $("#apStopPlus").addEventListener("click", () => VL.executer(
        op_degrade_stop_ajouter, gid, { t: 0.5, couleur: "#888888" }));
    }
  }

  const suivantRendu = VL.surRendu;
  VL.surRendu = () => { suivantRendu(); rendrePanneau(); };
  const suivantSel = VL.surSelection;
  VL.surSelection = () => { suivantSel(); rendrePanneau(); };
  VL.opDegradeModifier = op_degrade_modifier;   // pour les poignées (tools)
}
