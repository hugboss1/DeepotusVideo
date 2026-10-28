// mod-schema.js — t314 (28/10/2026, chantier boîte à outils C2, spec §7.3) : une illustration ou un schéma → un
// document du Vectorlab aux CALQUES NOMMÉS (formes, flèches, étiquettes), puis « Envoyer vers › Animation ».
//   1. « Scanner un schéma… » (Fichier) : l'image part à POST /api/schema/analyser (détourage local gratuit, ou fal
//      payant après accord du devis ; étiquettes lues par la lecture de texte de Windows de t312) ; chaque forme et
//      chaque flèche est VECTORISÉE ici par le moteur du Vectorlab (imagetracerjs, options_trace / tracedata_vers_objets
//      de mod-trace.js), chaque étiquette devient un objet texte ; le document est créé (POST /api/vector/docs) et
//      ouvert. `doc.schema` garde l'ordre de révélation (qui suit les flèches) et la nature de chaque calque.
//   2. « Envoyer vers › Animation » (tout document) : chaque calque visible non vide est rendu SEUL (VL.svgCourant,
//      le compilateur de l'export), recadré à ses pixels, déposé dans la Bibliothèque sous un nom STABLE
//      (vector_<doc>_c<calque>.png, réécrit à chaque envoi) ; POST /api/schema/animation rend le graphe Studio
//      (nœud Animation rempli, Rendu motion code, Render) que l'on pose dans window.top.__dzRenderGraph avant
//      d'ouvrir le Studio — le contrat d'« Envoyer vers › Studio » de la Bibliothèque. Vectorlab ouvert seul : le
//      graphe est déjà au magasin du Studio (« Ouvrir un graphe »).
// La logique PURE est en tête (banc node qa/schema.test.mjs) ; initSchema ne touche le DOM qu'à l'appel.
import { T } from "./mod-i18n.js";
import { op_ajouter, op_calque_ajouter } from "./mod-doc.js";
import { options_trace, tracedata_vers_objets, definition_trace } from "./mod-trace.js";
import { recadrer_alpha } from "./mod-exportplus.js";

/* ── pur ── */
const PILE = { forme: 0, fleche: 1, details: 2, etiquette: 3 };       // empilement : les étiquettes au-dessus
export const TRACE_SCHEMA = { couleurs: 4, lissage: 1, seuil: 4, definition: 768 };
const NATURES = { forme: "vectorlab.schema.nature_forme", fleche: "vectorlab.schema.nature_fleche",
                  etiquette: "vectorlab.schema.nature_etiquette", details: "vectorlab.schema.nature_details" };

export function libelle_nature(n) { return T(NATURES[n] || NATURES.forme); }

export function nom_png(docId, calqueId) {
  return `vector_${String(docId)}_c${String(calqueId)}.png`;
}

// une ligne d'étiquette lue → un objet texte. Avec `mesure(texte, corps) → { w, desc }` (canvas, police Segoe UI) :
// le corps qui donne au texte la LARGEUR lue (la hauteur d'une boîte lue dépend des accents et jambages), la ligne de
// base au bas de la boîte moins le jambage mesuré ; sans mesure : d'après la hauteur de la boîte.
export function texte_de_ligne(l, couleur, mesure) {
  const b = l.boite, t = String(l.texte || "");
  let corps = Math.max(6, Math.round(b.h * 0.9)), y = b.y + b.h * 0.82;
  const m = mesure && t ? mesure(t, 100) : null;
  if (m && m.w > 0) {
    corps = Math.max(6, Math.min(Math.round(b.h * 2), Math.round(100 * b.w / m.w)));
    y = b.y + b.h - Math.max(0, (mesure(t, corps).desc || 0));
  }
  return { type: "texte", x: Math.round(b.x * 10) / 10, y: Math.round(y * 10) / 10,
           contenu: t, style: { fond: couleur || "#1F1512", police: "Segoe UI", corps } };
}

// analyse (réponse de /api/schema/analyser) + tracés (Map id d'élément → objets du modèle, déjà au cadre) → document
export function doc_depuis_analyse(analyse, traces, nom, mesure) {
  const doc = { v: 1, nom: String(nom || T("vectorlab.schema.nom_doc")).slice(0, 120),
                taille: { w: analyse.largeur, h: analyse.hauteur }, fond: "#FFFFFF", calques: [] };
  const parOrdre = [...analyse.elements].sort((a, b) => a.ordre - b.ordre);
  const empiles = [...parOrdre].sort((a, b) => (PILE[a.nature] ?? 0) - (PILE[b.nature] ?? 0) || a.ordre - b.ordre);
  const calqueDe = {}, natures = {};
  for (const e of empiles) {
    const objets = e.nature === "etiquette"
      ? (e.lignes || []).map((l) => texte_de_ligne(l, e.couleur, mesure))
      : (traces.get(e.id) || []);
    if (!objets.length) continue;
    const cid = op_calque_ajouter(doc, e.nom);
    for (const o of objets) op_ajouter(doc, cid, o);
    calqueDe[e.id] = cid;
    natures[cid] = { nature: e.nature, element: e.id };
    if (e.queue && e.pointe) Object.assign(natures[cid], { queue: e.queue, pointe: e.pointe });
  }
  doc.schema = { ordre: parOrdre.map((e) => calqueDe[e.id]).filter(Boolean), natures };
  return doc;
}

const _plein = (c) => c && c.visible !== false && Array.isArray(c.objets) && c.objets.length > 0;

// l'ordre d'envoi : celui du scan (calques encore là, visibles, non vides), puis les autres dans l'empilement
export function ordre_envoi(doc) {
  const par = new Map((doc.calques || []).map((c) => [c.id, c]));
  const out = [];
  for (const id of (doc.schema && doc.schema.ordre) || []) if (_plein(par.get(id)) && !out.includes(id)) out.push(id);
  for (const c of doc.calques || []) if (_plein(c) && !out.includes(c.id)) out.push(c.id);
  return out;
}

// le texte du script des nœuds : les étiquettes dans l'ordre, sinon les noms des calques
export function script_de(doc, ids) {
  const par = new Map((doc.calques || []).map((c) => [c.id, c]));
  const textes = [];
  for (const id of ids) {
    for (const o of (par.get(id) || {}).objets || []) if (o.type === "texte" && String(o.contenu || "").trim()) textes.push(String(o.contenu).trim());
  }
  return (textes.length ? textes : ids.map((id) => (par.get(id) || {}).nom || id)).join("\n");
}

// le corps de POST /api/schema/animation ; rasters : Map id de calque → { image, boite }
export function corps_animation(doc, docId, rasters) {
  const nat = (doc.schema && doc.schema.natures) || {};
  const ids = ordre_envoi(doc).filter((id) => rasters.has(id));
  const par = new Map(doc.calques.map((c) => [c.id, c]));
  return {
    doc_id: docId, nom: doc.nom || "", largeur: doc.taille.w, hauteur: doc.taille.h, fond: doc.fond || "#FFFFFF",
    script: script_de(doc, ids),
    calques: ids.map((id) => {
      const n = nat[id] || {}, r = rasters.get(id);
      const k = { image: r.image, nom: par.get(id).nom || id, nature: n.nature || "forme", boite: r.boite };
      if (n.queue && n.pointe) { k.queue = n.queue; k.pointe = n.pointe; }
      return k;
    }),
  };
}

// les lignes du choix de détourage (réponse de /api/schema/devis)
export function options_detourage(modeles) {
  return (modeles || []).map((m) => {
    let lib;
    if (m.id === "local-chroma") lib = T("vectorlab.schema.det_local");
    else if (m.id === "local-rembg") lib = T("vectorlab.schema.det_rembg");
    else lib = T(!m.disponible ? "vectorlab.schema.det_sans_cle" : Number(m.usd) > 0 ? "vectorlab.schema.det_payant"
                 : "vectorlab.schema.det_a_mesurer",
                 { label: m.label, usd: Number(m.usd || 0).toFixed(3), cle: m.raison || "" });
    return { id: m.id, libelle: lib, usd: Number(m.usd || 0), payant: m.voie === "fal" };
  });
}

/* ── DOM ── */
function charger(src) {
  return new Promise((res, rej) => {
    const im = new Image();
    im.onload = () => res(im);
    im.onerror = () => rej(new Error(T("vectorlab.schema.image_illisible")));
    im.src = src;
  });
}

async function lireJson(r) {
  const d = await r.json().catch(() => ({}));
  if (r.ok) return d;
  const det = d && d.detail;
  const e = new Error(typeof det === "string" ? det : (det && det.message) || r.statusText || String(r.status));
  e.statut = r.status; e.detail = det;
  throw e;
}

export function initSchema(VL) {
  const { etat } = VL;
  let dlg = null, analyse = null, fichier = null, enVol = false;

  function fermer() { if (dlg) { dlg.remove(); dlg = null; } analyse = null; fichier = null; enVol = false; }
  const $d = (sel) => dlg && dlg.querySelector(sel);
  function etatTexte(t, erreur) { const p = $d("#schEtat"); if (p) { p.textContent = t; p.classList.toggle("sch-erreur", !!erreur); } }
  function occupe(v) {
    enVol = v;
    for (const id of ["#schAnalyser", "#schCreer", "#schFichier", "#schDetour", "#schLangue"]) {
      const b = $d(id); if (b) b.disabled = v || (id === "#schCreer" && !analyse) || (id === "#schAnalyser" && !fichier);
    }
  }

  function rendreListe() {
    const ul = $d("#schListe");
    if (!ul) return;
    if (!analyse) { ul.innerHTML = ""; return; }
    const els = [...analyse.elements].sort((a, b) => a.ordre - b.ordre);
    ul.innerHTML = "";
    for (const e of els) {
      const li = document.createElement("li");
      li.className = "sch-el sch-" + e.nature;
      const n = document.createElement("span"); n.className = "sch-nature"; n.textContent = libelle_nature(e.nature);
      const t = document.createElement("span"); t.className = "sch-nom"; t.textContent = e.nom;
      li.append(n, t);
      ul.appendChild(li);
    }
    const av = (analyse.avertissements || []).map((a) => a === "ocr_indisponible" ? T("vectorlab.schema.avert_ocr")
      : a === "fond_estime" ? T("vectorlab.schema.avert_fond") : "").filter(Boolean);
    etatTexte(T("vectorlab.schema.bilan", { n: els.length, l: (analyse.liens || []).length }) + (av.length ? " " + av.join(" ") : ""));
  }

  async function analyser() {
    if (!fichier || enVol) return;
    const sel = $d("#schDetour"), opt = sel.options[sel.selectedIndex];
    const payant = opt && opt.dataset.payant === "1";
    let maxUsd = "";
    if (payant) {
      const usd = Number(opt.dataset.usd || 0);
      const ok = await VL.dialogue.confirmer(T("vectorlab.schema.confirmer_cout", { modele: opt.dataset.label || sel.value, usd: usd.toFixed(3) }),
        { titre: T("vectorlab.schema.confirmer_titre"), ok: T("vectorlab.schema.confirmer_ok") });
      if (!ok) return;
      maxUsd = String(usd);
    }
    occupe(true);
    etatTexte(T("vectorlab.schema.analyse_en_cours"));
    try {
      const fd = new FormData();
      fd.append("image", fichier, fichier.name || "schema.png");
      fd.append("detourage", sel.value);
      fd.append("langue", $d("#schLangue").value);
      fd.append("max_usd", maxUsd);
      analyse = await lireJson(await fetch("/api/schema/analyser", { method: "POST", body: fd }));
      if (!analyse.elements.length) { analyse = null; throw new Error(T("vectorlab.schema.aucun_element")); }
      rendreListe();
    } catch (e) {
      analyse = null; rendreListe();
      etatTexte(e.statut === 409 && e.detail && e.detail.usd != null
        ? T("vectorlab.schema.cout_change", { usd: Number(e.detail.usd).toFixed(3) }) : e.message, true);
    } finally { occupe(false); }
  }

  async function tracer(e) {
    if (!window.ImageTracer) throw new Error(T("vectorlab.trace.vendor_absent"));
    const im = await charger(e.png);
    const def = definition_trace({ w: im.naturalWidth, h: im.naturalHeight }, TRACE_SCHEMA.definition);
    const cv = document.createElement("canvas");
    cv.width = def.w; cv.height = def.h;
    const ctx = cv.getContext("2d");
    ctx.drawImage(im, 0, 0, def.w, def.h);
    const td = window.ImageTracer.imagedataToTracedata(ctx.getImageData(0, 0, def.w, def.h), options_trace(TRACE_SCHEMA));
    return tracedata_vers_objets(td, e.boite);
  }

  async function creer() {
    if (!analyse || enVol) return;
    if (etat.sale && !(await VL.dialogue.confirmer(T("vectorlab.schema.quitter_sale"), { titre: T("vectorlab.schema.titre") }))) return;
    occupe(true);
    try {
      const traces = new Map();
      const aTracer = analyse.elements.filter((e) => e.png);
      for (let i = 0; i < aTracer.length; i++) {
        etatTexte(T("vectorlab.schema.trace_en_cours", { i: i + 1, n: aTracer.length }));
        traces.set(aTracer[i].id, await tracer(aTracer[i]));
      }
      const nom = String((fichier && fichier.name) || "").replace(/\.[A-Za-z0-9]{2,5}$/, "") || T("vectorlab.schema.nom_doc");
      const cv = document.createElement("canvas").getContext("2d");
      const mesure = (t, corps) => {
        cv.font = `${corps}px "Segoe UI"`;
        const m = cv.measureText(t);
        return { w: m.width, desc: m.actualBoundingBoxDescent || 0 };
      };
      const doc = doc_depuis_analyse(analyse, traces, nom, mesure);
      if (!doc.calques.length) throw new Error(T("vectorlab.schema.aucun_element"));
      etatTexte(T("vectorlab.schema.creation_en_cours"));
      const d = await lireJson(await fetch("/api/vector/docs", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: doc.nom, role: "libre", doc }) }));
      VL.toast(T("vectorlab.schema.cree", { n: doc.calques.length }));
      etat.sale = false;
      location.href = "?doc=" + encodeURIComponent(d.id);
    } catch (e) {
      etatTexte(e.message, true);
      occupe(false);
    }
  }

  async function chargerModeles() {
    const sel = $d("#schDetour");
    try {
      const d = await lireJson(await fetch("/api/schema/devis", { cache: "no-store" }));
      sel.innerHTML = "";
      const brut = new Map((d.modeles || []).map((m) => [m.id, m]));
      for (const o of options_detourage(d.modeles)) {
        const op = document.createElement("option");
        op.value = o.id; op.textContent = o.libelle;
        op.dataset.payant = o.payant ? "1" : "0"; op.dataset.usd = String(o.usd);
        op.dataset.label = (brut.get(o.id) || {}).label || o.id;
        if (o.id === d.defaut) op.selected = true;
        sel.appendChild(op);
      }
    } catch (e) { etatTexte(e.message, true); }
  }

  function choisir(f) {
    if (!f) return;
    if (!/^image\//.test(f.type || "")) { etatTexte(T("vectorlab.schema.pas_image"), true); return; }
    fichier = f; analyse = null; rendreListe();
    const ap = $d("#schApercu");
    ap.innerHTML = "";
    const im = document.createElement("img");
    im.src = URL.createObjectURL(f);
    im.alt = f.name || "";
    ap.appendChild(im);
    etatTexte(T("vectorlab.schema.pret", { nom: f.name || "" }));
    occupe(false);
  }

  VL.schemaScanner = () => {
    fermer();
    dlg = document.createElement("div");
    dlg.className = "vl-dlg";
    dlg.id = "schemaDlg";
    const lg = (document.documentElement.lang || "fr").slice(0, 2) === "en" ? "en" : "fr";
    dlg.innerHTML = `<div class="vl-dlg-boite sch-boite" role="dialog" aria-modal="true" aria-labelledby="schTitre">
      <div class="vl-dlg-tete"><b id="schTitre">${T("vectorlab.schema.titre")}</b></div>
      <div class="sch-corps">
        <div class="sch-gauche">
          <label class="sch-depot" id="schDepot"><span>${T("vectorlab.schema.depot")}</span>
            <input type="file" id="schFichier" accept="image/*"/></label>
          <div class="sch-apercu" id="schApercu"></div>
          <label class="sch-champ">${T("vectorlab.schema.detourage")} <select id="schDetour"></select></label>
          <label class="sch-champ">${T("vectorlab.schema.langue")} <select id="schLangue">
            <option value="fr"${lg === "fr" ? " selected" : ""}>${T("vectorlab.schema.langue_fr")}</option>
            <option value="en"${lg === "en" ? " selected" : ""}>${T("vectorlab.schema.langue_en")}</option></select></label>
          <p class="sch-aide">${T("vectorlab.schema.aide")}</p>
        </div>
        <div class="sch-droite">
          <b>${T("vectorlab.schema.calques")}</b>
          <ol class="sch-liste" id="schListe"></ol>
          <p class="sch-etat" id="schEtat" aria-live="polite">${T("vectorlab.schema.choisir")}</p>
        </div>
      </div>
      <div class="tr-pied"><button id="schAnnuler">${T("vectorlab.schema.fermer")}</button>
        <button id="schAnalyser" disabled>${T("vectorlab.schema.analyser")}</button>
        <button id="schCreer" class="primaire" disabled>${T("vectorlab.schema.creer")}</button></div>
    </div>`;
    document.body.appendChild(dlg);
    $d("#schAnnuler").addEventListener("click", fermer);
    $d("#schFichier").addEventListener("change", (ev) => choisir(ev.target.files && ev.target.files[0]));
    const depot = $d("#schDepot");
    depot.addEventListener("dragover", (ev) => { ev.preventDefault(); depot.classList.add("survol"); });
    depot.addEventListener("dragleave", () => depot.classList.remove("survol"));
    depot.addEventListener("drop", (ev) => { ev.preventDefault(); depot.classList.remove("survol"); choisir(ev.dataTransfer.files && ev.dataTransfer.files[0]); });
    $d("#schAnalyser").addEventListener("click", () => analyser());
    $d("#schCreer").addEventListener("click", () => creer());
    dlg.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !enVol) { ev.stopPropagation(); fermer(); } });
    chargerModeles();
  };

  /* ── Envoyer vers › Animation ── */
  function rasteriser(svg, w, h) {
    return new Promise((res, rej) => {
      const url = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
      const im = new Image();
      im.onload = () => {
        const cv = document.createElement("canvas");
        cv.width = w; cv.height = h;
        const ctx = cv.getContext("2d");
        ctx.drawImage(im, 0, 0, w, h);
        URL.revokeObjectURL(url);
        res(ctx);
      };
      im.onerror = () => { URL.revokeObjectURL(url); rej(new Error(T("vectorlab.schema.rendu_calque"))); };
      im.src = url;
    });
  }

  async function calquePng(cid) {
    const doc = etat.doc;
    const seul = JSON.parse(JSON.stringify(doc));
    delete seul.fond;
    seul.calques = seul.calques.filter((c) => c.id === cid);
    const k = Math.min(1, 4096 / Math.max(doc.taille.w, doc.taille.h));
    const w = Math.max(1, Math.round(doc.taille.w * k)), h = Math.max(1, Math.round(doc.taille.h * k));
    const ctx = await rasteriser(await VL.svgCourant(true, null, seul), w, h);
    const r = recadrer_alpha(ctx.getImageData(0, 0, w, h).data, w, h);
    if (!r) return null;
    const cv = document.createElement("canvas");
    cv.width = r.largeur; cv.height = r.hauteur;
    cv.getContext("2d").putImageData(new ImageData(new Uint8ClampedArray(r.rgba.buffer), r.largeur, r.hauteur), 0, 0);
    const png = await new Promise((res, rej) => cv.toBlob((b) => b ? res(b) : rej(new Error(T("vectorlab.schema.rendu_calque"))), "image/png"));
    const fd = new FormData();
    fd.append("file", new File([png], nom_png(etat.docId, cid), { type: "image/png" }));
    const d = await lireJson(await fetch("/api/images/upload", { method: "POST", body: fd }));
    return { image: d.filename, boite: { x: r.x0 / k, y: r.y0 / k, w: r.largeur / k, h: r.hauteur / k } };
  }

  VL.schemaAnimation = async () => {
    if (!etat.doc || !etat.docId) { VL.toast(T("vectorlab.schema.sans_doc"), true); return; }
    const ids = ordre_envoi(etat.doc);
    if (!ids.length) { VL.toast(T("vectorlab.schema.envoi_vide"), true); return; }
    try {
      const rasters = new Map();
      for (let i = 0; i < ids.length; i++) {
        VL.toast(T("vectorlab.schema.envoi_en_cours", { i: i + 1, n: ids.length }));
        const r = await calquePng(ids[i]);
        if (r) rasters.set(ids[i], r);
      }
      if (!rasters.size) throw new Error(T("vectorlab.schema.envoi_vide"));
      const j = await lireJson(await fetch("/api/schema/animation", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corps_animation(etat.doc, etat.docId, rasters)) }));
      let haut = null;
      try { haut = window.top !== window && window.top.document ? window.top : null; } catch (e) { haut = null; }
      if (haut) {
        haut.__dzRenderGraph = j.graph;
        haut.dispatchEvent(new haut.CustomEvent("deepotus:navigate", { detail: { view: "studio" } }));
        VL.toast(T("vectorlab.schema.envoi_ok", { n: rasters.size }));
      } else {
        await VL.dialogue.informer(T("vectorlab.schema.envoi_seul", { nom: j.nom_graphe || j.graph.name || "" }), { titre: T("vectorlab.schema.envoi_titre") });
      }
    } catch (e) {
      VL.toast(T("vectorlab.schema.envoi_echec", { m: e.message }), true);
    }
  };
}
