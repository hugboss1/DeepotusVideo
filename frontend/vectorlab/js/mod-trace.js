// mod-trace.js — la vectorisation d'une image (lot A, D6) par imagetracerjs
// vendorisé (Unlicense) : aplats de couleur → chemins du modèle. PUR en
// tête : options bornées, définition de tracé, conversion tracedata →
// objets `path` (trous en sous-chemins, fill-rule evenodd). Le dialogue
// (initTrace) rasterise la fenêtre rognée de l'image dans un canvas,
// trace, montre un aperçu compilé par LE compilateur, puis pose en UNE
// commande (op_vectoriser_poser).
import { T } from "./mod-i18n.js";
import { dzi } from "./mod-icones.js";
import { compilerSVG, op_vectoriser_poser, chemin_parser, chemin_serialiser }
  from "./mod-doc.js";

/* ── pur ── */
export const TRACE_DEFAUTS = { couleurs: 8, lissage: 1, seuil: 8, definition: 512 };
const borne = (v, lo, hi, def) => {
  const n = +v;
  return Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : def;
};

export function options_trace(p = {}) {
  const lissage = borne(p.lissage, 0.1, 10, TRACE_DEFAUTS.lissage);
  return {
    numberofcolors: Math.round(borne(p.couleurs, 2, 64, TRACE_DEFAUTS.couleurs)),
    ltres: lissage, qtres: lissage,
    pathomit: Math.round(borne(p.seuil, 0, 500, TRACE_DEFAUTS.seuil)),
    colorsampling: 2, mincolorratio: 0, colorquantcycles: 3,
    blurradius: 0, blurdelta: 20, layering: 0, rightangleenhance: true,
    strokewidth: 0, linefilter: false, roundcoords: 2, viewbox: false, desc: false,
  };
}

export function definition_trace(fenetre, definition) {
  const d = borne(definition, 64, 2048, TRACE_DEFAUTS.definition);
  const k = Math.min(1, d / Math.max(fenetre.w, fenetre.h));
  return { w: Math.max(1, Math.round(fenetre.w * k)),
           h: Math.max(1, Math.round(fenetre.h * k)), echelle: k };
}

const hex2 = (n) => Math.round(n).toString(16).padStart(2, "0").toUpperCase();
function _d(segments, fx, fy) {
  if (!segments.length) return "";
  let d = `M ${fx(segments[0].x1)} ${fy(segments[0].y1)}`;
  for (const s of segments) {
    d += s.type === "Q" ? ` Q ${fx(s.x2)} ${fy(s.y2)} ${fx(s.x3)} ${fy(s.y3)}`
                        : ` L ${fx(s.x2)} ${fy(s.y2)}`;
  }
  return d + " Z";
}

export function tracedata_vers_objets(td, cadre) {
  const fx = (x) => cadre.x + x * cadre.w / td.width;
  const fy = (y) => cadre.y + y * cadre.h / td.height;
  const out = [];
  td.layers.forEach((chemins, l) => {
    const c = td.palette[l];
    if (!c || c.a < 32) return;                       // transparent : rien
    const fond = "#" + hex2(c.r) + hex2(c.g) + hex2(c.b);
    for (const p of chemins) {
      if (p.isholepath) continue;                     // les trous suivent leur parent
      let d = _d(p.segments, fx, fy);
      for (const k of p.holechildren || []) d += " " + _d(chemins[k].segments, fx, fy);
      if (!d) continue;
      out.push({ type: "path", d: chemin_serialiser(chemin_parser(d)),
                 style: { fond, regle: "evenodd" } });
    }
  });
  return out;
}

/* ── DOM ── */
export function initTrace(VL) {
  const { $, etat } = VL;
  const dlg = $("#traceDlg");
  let courant = null;                  // { id, objets, params }

  function charger(url) {
    return new Promise((res, rej) => {
      const im = new Image();
      im.onload = () => res(im);
      im.onerror = () => rej(new Error(T("vectorlab.trace.source_illisible")));
      im.src = url;
    });
  }
  async function tracer(o, params) {
    if (!window.ImageTracer) throw new Error(T("vectorlab.trace.vendor_absent"));
    const im = await charger(VL.imageUrl(o.href));
    const r = o.rognage || { x: 0, y: 0, w: o.nat.w, h: o.nat.h };
    const def = definition_trace(r, params.definition);
    const cv = document.createElement("canvas");
    cv.width = def.w; cv.height = def.h;
    const ctx = cv.getContext("2d");
    ctx.drawImage(im, r.x, r.y, r.w, r.h, 0, 0, def.w, def.h);
    const td = window.ImageTracer.imagedataToTracedata(
      ctx.getImageData(0, 0, def.w, def.h), options_trace(params));
    return tracedata_vers_objets(td, { x: o.x, y: o.y, w: o.w, h: o.h });
  }
  function lireParams() {
    return { couleurs: +$("#trCouleurs").value, lissage: +$("#trLissage").value,
             seuil: +$("#trSeuil").value, definition: +$("#trDef").value };
  }
  async function apercu() {
    const t = VL.objetDe(courant.id);
    if (!t) throw new Error(T("vectorlab.trace.image_disparue"));
    $("#trEtat").textContent = T("vectorlab.trace.en_cours");
    $("#trValider").disabled = true;
    const objets = await tracer(t.objet, lireParams());
    courant.objets = objets;
    const couleurs = new Set(objets.map((o) => o.style.fond)).size;
    const b = t.objet;
    const mini = { v: 1, taille: { w: b.w, h: b.h }, fond: "#FFFFFF",
      calques: [{ id: "c", objets: objets.map((o, i) => ({ ...o, id: "t" + i })) }] };
    // le même compilateur que l'écran ; les d sont décalés au cadre → viewBox
    $("#trApercu").innerHTML = compilerSVG(mini)
      .replace(`viewBox="0 0 ${+b.w} ${+b.h}"`, `viewBox="${+b.x} ${+b.y} ${+b.w} ${+b.h}"`)
      .replace(`width="${+b.w}" height="${+b.h}"`, `width="100%" height="100%"`);
    $("#trEtat").textContent = T("vectorlab.trace.etat", { n: objets.length, c: couleurs });
    $("#trValider").disabled = !objets.length;
  }
  function fermer() { dlg.classList.add("hidden"); dlg.innerHTML = ""; courant = null; }

  VL.vectoriser = (id) => {
    const t = VL.objetDe(id);
    if (!t || t.objet.type !== "image") { VL.toast(T("vectorlab.trace.pas_image"), true); return; }
    courant = { id, objets: [], params: { ...TRACE_DEFAUTS } };
    const p = courant.params;
    dlg.innerHTML = `<div class="vl-dlg-boite tr-boite">
      <div class="vl-dlg-tete"><b>${T("vectorlab.trace.titre", { href: t.objet.href })}</b><span class="spacer"></span>
        <button id="trFermer" title="${T("vectorlab.trace.annuler")}" aria-label="${T("vectorlab.trace.annuler")}">${dzi("dz-action-fermer", 16)}</button></div>
      <div class="tr-corps">
        <div class="tr-regles">
          <label>${T("vectorlab.trace.couleurs")} <input type="range" id="trCouleurs" min="2" max="32" step="1" value="${p.couleurs}"/><output id="trCouleursV">${p.couleurs}</output></label>
          <label>${T("vectorlab.trace.lissage")} <input type="range" id="trLissage" min="0.5" max="4" step="0.5" value="${p.lissage}"/><output id="trLissageV">${p.lissage}</output></label>
          <label>${T("vectorlab.trace.seuil")} <input type="range" id="trSeuil" min="0" max="64" step="1" value="${p.seuil}"/><output id="trSeuilV">${p.seuil}</output></label>
          <label>${T("vectorlab.trace.definition")} <select id="trDef">${[256, 512, 1024].map((d) => `<option value="${d}"${d === p.definition ? " selected" : ""}>${d} px</option>`).join("")}</select></label>
          <button id="trApercuBtn" class="primaire">${T("vectorlab.trace.apercu")}</button>
          <p id="trEtat" class="tr-etat">${T("vectorlab.trace.reglez")}</p>
        </div>
        <div id="trApercu" class="tr-apercu"></div>
      </div>
      <div class="tr-pied"><button id="trAnnuler">${T("vectorlab.trace.annuler")}</button>
        <button id="trValider" class="primaire" disabled title="${T("vectorlab.trace.valider_titre")}">${T("vectorlab.trace.valider")}</button></div>
    </div>`;
    dlg.classList.remove("hidden");
    for (const [id2, out] of [["trCouleurs", "trCouleursV"], ["trLissage", "trLissageV"], ["trSeuil", "trSeuilV"]]) {
      $("#" + id2).addEventListener("input", (e) => { $("#" + out).textContent = e.target.value; });
    }
    const garde = (fn) => () => Promise.resolve().then(fn).catch((e) => {
      $("#trEtat").textContent = e.message; VL.toast(e.message, true); });
    $("#trApercuBtn").addEventListener("click", garde(apercu));
    $("#trFermer").addEventListener("click", fermer);
    $("#trAnnuler").addEventListener("click", fermer);
    $("#trValider").addEventListener("click", () => {
      const r = VL.executer(op_vectoriser_poser, courant.objets, "vectorisé");
      if (r) {
        etat.calqueActif = r.calqueId;
        VL.setSelection(r.ids);
        VL.toast(T("vectorlab.trace.poses", { n: r.ids.length }));
      }
      fermer();
    });
    garde(apercu)();                    // un premier aperçu aux défauts
  };
}
