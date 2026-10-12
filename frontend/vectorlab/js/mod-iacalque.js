// mod-iacalque.js — t190 (G8, plan « Génération IA enrichie ») : l'IMAGE IA PAR CALQUE du Vectorlab.
//
// Le geste voulu : fond ; calque 1 : générer une image, retirer son fond ; calque 2 : texte et formes ;
// calque 3 : générer une autre image… Le panneau flottant « Image IA sur le calque » (même allure que le
// dialogue IA de mod-ia : posé sur #stage, déplaçable par sa tête) choisit le CALQUE cible (les calques non
// verrouillés, présélection = celui d'où l'on vient), le MODÈLE (DzModelesIA, une option sans clé reste
// choisissable : le 503 n'arrive qu'au lancement), le FORMAT d'après la page, et le DÉTOURAGE (registre G4,
// sujet à garder si le modèle l'exige) ; le prix TOTAL est chiffré par le serveur (/api/cost/estimate,
// campagne image + détourage), jamais inventé.
//
// Les modèles vectoriels (sortie « svg », Recraft) n'y sont PAS : l'image posée ici est un raster, et
// /images/generate refuse un modèle vectoriel sans `sortie: "svg"` (le dialogue IA du canevas, mod-ia, pose
// les tracés). « Retirer le fond » du panneau Image (ligneDetour) remplace l'image par une NOUVELLE image du
// magasin du document en UNE commande (op_image_remplacer via VL.executer) : Ctrl+Z rend l'image d'avant,
// dont le PNG reste au magasin.
//
// La logique PURE est en tête (banc qa/iacalque.test.mjs) ; initIaCalque ne touche le DOM qu'à l'appel.
import { T } from "./mod-i18n.js";
import { dzi } from "./mod-icones.js";

/* ── pur ── */
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;")
  .replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// les formats que /images/generate accepte (fal ; OpenAI et Nano Banana les traduisent, image_providers)
export const TAILLES = ["portrait_16_9", "portrait_4_3", "square_hd", "landscape_4_3", "landscape_16_9"];

// le format le plus proche du rapport largeur / hauteur de la page (doc.taille)
export function taillePour(t) {
  const w = +(t && t.w), h = +(t && t.h);
  if (!(w > 0 && h > 0)) return "square_hd";
  const r = w / h;
  if (r < 0.7) return "portrait_16_9";
  if (r < 0.9) return "portrait_4_3";
  if (r <= 1 / 0.9) return "square_hd";
  if (r <= 1 / 0.7) return "landscape_4_3";
  return "landscape_16_9";
}

// le corps de POST /api/images/generate ({prompt, n, model, size, source}) ; sans modèle, le serveur prend
// celui des Réglages
export function requete(o) {
  const prompt = String((o && o.prompt) || "").trim();
  if (!prompt) throw new Error(T("vectorlab.iacalque.prompt_vide"));
  const q = { prompt, n: 1 };
  if (o.modele) q.model = String(o.modele);
  q.size = TAILLES.includes(o.taille) ? o.taille : "square_hd";
  q.source = "vectorlab";
  return q;
}

// le corps de POST /api/images/process (registre G4) : {op, filename, modele, sujet?, source}
export function requeteDetour(o) {
  if (!o || !o.modele) throw new Error(T("vectorlab.iacalque.detour_modele"));
  const q = { op: "remove-bg", filename: String(o.nom || ""), modele: String(o.modele) };
  const sujet = String(o.sujet || "").trim();
  if (sujet) q.sujet = sujet;
  q.source = "vectorlab";
  return q;
}

// le PLAN d'un tir : générer, détourer (sur demande), poser sur LE calque demandé
export function etapes(o) {
  const out = [{ op: "generer" }];
  if (o && o.detourer) out.push({ op: "detourer", modele: o.modeleDetour, sujet: o.sujet || "" });
  out.push({ op: "poser", calqueId: o && o.calqueId });
  return out;
}

// la cible AVANT toute dépense : un calque inconnu ou verrouillé est refusé, rien ne part
export function verifierCible(doc, calqueId) {
  const c = doc && Array.isArray(doc.calques) ? doc.calques.find((x) => x.id === calqueId) : null;
  if (!c) throw new Error(T("vectorlab.iacalque.calque_absent", { id: String(calqueId) }));
  if (c.verrou) throw new Error(T("vectorlab.iacalque.calque_verrouille", { nom: c.nom || c.id }));
  return c;
}

// les calques qu'on peut viser (le dessus en tête, comme le panneau Calques)
export function calquesCibles(doc) {
  return [...((doc && doc.calques) || [])].reverse().filter((c) => !c.verrou)
    .map((c) => ({ id: c.id, nom: c.nom || c.id }));
}

// le devis serveur (POST /api/cost/estimate) : une campagne image + détourage
export function devisCorps(o) {
  const ops = [{ kind: "image", model: (o && o.modele) || "flux", n: 1 }];
  if (o && o.detourer && o.modeleDetour) ops.push({ kind: "detourage", modele: o.modeleDetour, images: 1 });
  return { kind: "campaign", ops };
}

// le montant en dollars, même règle que DzModelesIA.prixUsd : arrondi au millième, au moins deux décimales
export function dollars(v) {
  let s = (Math.round(v * 1000) / 1000).toFixed(3);
  while (/\.\d{3,}$/.test(s) && s.endsWith("0")) s = s.slice(0, -1);
  return "$" + s;
}

// le libellé du prix : jamais « gratuit » pour un 0 $ payant (« à mesurer ») ; une ligne locale à 0 $ l'est
export function libellePrix(devis) {
  if (!devis || !Array.isArray(devis.breakdown)) return T("vectorlab.iacalque.prix_inconnu");
  const total = +devis.total_usd || 0;
  const aMesurer = devis.breakdown.some((l) => !(+l.usd > 0) && l.provider !== "local");
  if (!(total > 0)) return T("vectorlab.iacalque.prix_a_mesurer");
  return T("vectorlab.iacalque.prix", { prix: dollars(total) }) + (aMesurer ? T("vectorlab.iacalque.prix_partiel") : "");
}

// le message d'une réponse en échec : 503 = clé absente (lisible), le 402 d'un plafond refusé rend une chaîne
export function messageErreur(status, d, statut) {
  const det = d && d.detail;
  const m = typeof det === "string" ? det
    : det && det.dz_plafond && det.dz_plafond.message ? det.dz_plafond.message
      : det ? JSON.stringify(det) : (statut || String(status));
  return status === 503 ? T("vectorlab.iacalque.cle_absente", { detail: m }) : m;
}

// UN SEUL tir à la fois : un second appel pendant le vol ne relance rien (rend null)
export function unSeulVol(fn) {
  const g = async (...a) => {
    if (g.enVol) return null;
    g.enVol = true;
    try { return await fn(...a); } finally { g.enVol = false; }
  };
  g.enVol = false;
  return g;
}

// le tir : cible vérifiée, génération, détourage éventuel, pose sur LE calque demandé — d = {doc(), post(url,
// corps), poser(nom, calqueId)} (fetch et pose réels dans la page, faux au banc)
export async function executerPlan(o, d) {
  verifierCible(d.doc(), o.calqueId);
  let nom = null;
  for (const e of etapes(o)) {
    if (e.op === "generer") {
      const r = await d.post("/api/images/generate", requete(o));
      nom = (r && r.images || [])[0];
      if (!nom) throw new Error(T("vectorlab.image.generation_vide"));
    } else if (e.op === "detourer") {
      const r = await d.post("/api/images/process", requeteDetour({ nom, modele: e.modele, sujet: e.sujet }));
      nom = (r && r.images || [])[0];
      if (!nom) throw new Error(T("vectorlab.iacalque.detour_vide"));
    } else if (e.op === "poser") {
      verifierCible(d.doc(), e.calqueId);          // verrouillé pendant le vol : l'image reste en Bibliothèque
      return { nom, id: await d.poser(nom, e.calqueId) };
    }
  }
  return { nom, id: undefined };
}

// une image du document (calques et groupes)
function _image(doc, id) {
  const visiter = (objs) => {
    for (const o of objs || []) {
      if (o.id === id) return o;
      if (o.type === "groupe") { const x = visiter(o.enfants); if (x) return x; }
    }
    return null;
  };
  for (const c of (doc && doc.calques) || []) { const o = visiter(c.objets); if (o) return o; }
  return null;
}

// la commande RÉVERSIBLE du détourage : l'objet désigne une AUTRE image du magasin (href) — Annuler rend
// l'href d'avant, dont le PNG n'a pas été touché. La révision raster et l'empreinte de l'ancienne image ne
// suivent pas ; un rognage qui ne tient plus dans la nouvelle taille native tombe.
export function op_image_remplacer(doc, id, href, nat) {
  const o = _image(doc, id);
  if (!o || o.type !== "image") throw new Error(T("vectorlab.iacalque.image_introuvable", { id: String(id) }));
  if (!href || !(nat && nat.w > 0 && nat.h > 0)) throw new Error(T("vectorlab.iacalque.image_invalide"));
  o.href = String(href);
  const memeTaille = o.nat && o.nat.w === nat.w && o.nat.h === nat.h;
  o.nat = { w: nat.w, h: nat.h };
  delete o.rev; delete o.px;
  if (o.rognage && !memeTaille) delete o.rognage;
}

// « Retirer le fond » d'une image du document — d = {versBiblio(o) → nom en Bibliothèque, post(url, corps),
// deposer(nom) → {href, nat} (nouvelle image du magasin du document), executer(fn, …args)}
export async function retirerFondFlux(o, choix, d) {
  if (!o || o.type !== "image") throw new Error(T("vectorlab.iacalque.image_introuvable", { id: String(o && o.id) }));
  const corps = requeteDetour({ nom: "", modele: choix && choix.modele, sujet: choix && choix.sujet });
  corps.filename = await d.versBiblio(o);
  const r = await d.post("/api/images/process", corps);
  const nom = (r && r.images || [])[0];
  if (!nom) throw new Error(T("vectorlab.iacalque.detour_vide"));
  const { href, nat } = await d.deposer(nom);
  // jamais par-dessus l'image d'avant : Annuler doit la retrouver
  if (href === o.href) throw new Error(T("vectorlab.iacalque.meme_image"));
  d.executer(op_image_remplacer, o.id, href, nat);
  return href;
}

// le nom du dépôt en Bibliothèque de l'image à détourer (`vector_` : provenance vectorlab, réécrit en place)
export function nomDepot(docId, href) {
  const a = (s) => String(s || "").replace(/\.png$/i, "").replace(/[^A-Za-z0-9_-]+/g, "-");
  return `vector_${a(docId)}_detour_${a(href)}.png`;
}

/* ── DOM ── */
// le panneau vit DANS #stage : sans garde, le pointerdown d'un contrôle remonte au gestionnaire de l'outil
// Sélection (mod-tools, en bulle sur #stage) qui pose setPointerCapture(#stage) — le click part alors sur
// #stage, la case ne se coche pas, le bouton ne part pas (vu à la preuve 8799). Les gestes du panneau
// s'arrêtent à lui (en bulle : ses propres écouteurs, dont la poignée, ont déjà joué) ; la molette ne zoome
// pas le canevas. Rien n'est preventDefault ici : la case, les listes et le texte gardent leur geste natif.
export const GESTES_GARDES = ["pointerdown", "mousedown", "dblclick", "contextmenu", "wheel"];
export function garderClics(el) {
  for (const t of GESTES_GARDES) {
    el.addEventListener(t, (ev) => ev.stopPropagation(), t === "wheel" ? { passive: true } : false);
  }
}

// déplaçable par sa tête, comme le dialogue IA du canevas (borné à la scène)
export function brancherPoignee(el, stage, win) {
  el.addEventListener("pointerdown", (ev) => {
    if (!ev.target.closest("[data-poigne]") || ev.target.closest("button")) return;
    const r = el.getBoundingClientRect();
    const ox = ev.clientX - r.left, oy = ev.clientY - r.top;
    const sr = stage.getBoundingClientRect();
    const bouge = (e2) => {
      el.style.left = Math.max(0, Math.min(sr.width - 60, e2.clientX - sr.left - ox)) + "px";
      el.style.top = Math.max(0, Math.min(sr.height - 30, e2.clientY - sr.top - oy)) + "px";
      el.style.right = "auto";
    };
    const fin = () => { win.removeEventListener("pointermove", bouge); win.removeEventListener("pointerup", fin); };
    win.addEventListener("pointermove", bouge);
    win.addEventListener("pointerup", fin);
    ev.preventDefault();
  });
}

export function initIaCalque(VL) {
  const { $, etat } = VL;
  const lire = (k) => { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } };
  const ecrire = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* stockage indisponible */ } };
  const MI = () => (typeof window !== "undefined" && window.DzModelesIA) || null;

  async function poster(url, corps) {
    const r = await window.fetch(url, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corps) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(messageErreur(r.status, d, r.statusText));
    return d;
  }

  // les catalogues (gratuits), lus une fois par page
  const catalogues = {};
  function catalogue(nature) {
    if (!catalogues[nature]) {
      const M = MI();
      catalogues[nature] = M ? M.charger(nature).then((l) => M.filtrer(l)) : Promise.resolve([]);
      catalogues[nature].catch(() => { delete catalogues[nature]; });
    }
    return catalogues[nature];
  }
  const sujetRequis = (mods, id) => !!((mods || []).find((m) => m.id === id) || {}).prompt;

  /* ── le tir (avec ou sans panneau) ── */
  const deps = {
    doc: () => etat.doc,
    post: poster,
    poser: (nom, calqueId) => { etat.calqueActif = calqueId; return VL.poserDepuisLibrary(nom, calqueId); },
  };
  const lancer = unSeulVol(async (o) => {
    VL.toast(T("vectorlab.image.generation"));
    return executerPlan({ ...o, taille: o.taille || taillePour(etat.doc && etat.doc.taille) }, deps);
  });

  /* ── le panneau ── */
  let cible = "", modsImage = [], modsDetour = [];
  function hote() {
    let el = $("#iaCalqueDlg");
    if (el) return el;
    const stage = $("#stage");
    if (!stage) return null;
    el = document.createElement("div");
    el.id = "iaCalqueDlg";
    el.className = "ia-dlg iac-dlg";
    el.hidden = true;
    stage.appendChild(el);
    brancher(el);
    return el;
  }
  const nomCalque = (id) => { const c = etat.doc && etat.doc.calques.find((x) => x.id === id); return c ? (c.nom || c.id) : String(id); };
  const choix = () => ({
    calqueId: cible,
    prompt: ($("#iacPrompt") || {}).value || "",
    modele: ($("#iacModele") || {}).value || "",
    detourer: !!($("#iacDetourer") || {}).checked,
    modeleDetour: ($("#iacDetour") || {}).value || "",
    sujet: ($("#iacSujet") || {}).value || "",
  });

  function squelette(el) {
    const cibles = calquesCibles(etat.doc);
    el.innerHTML = `
      <div class="ia-tete" data-poigne="1">
        <span class="ia-titre">${T("vectorlab.iacalque.titre")}</span>
        <span class="ia-sp"></span>
        <button class="ia-x" data-act="fermer" title="${T("vectorlab.ia.fermer")}" aria-label="${T("vectorlab.ia.fermer")}">${dzi("dz-action-fermer", 16)}</button>
      </div>
      <div class="ia-bas">
        <label class="ia-moteur">${T("vectorlab.iacalque.calque")}
          <select id="iacCalque" title="${T("vectorlab.iacalque.calque_aide")}">${cibles.map((c) =>
            `<option value="${esc(c.id)}"${c.id === cible ? " selected" : ""}>${esc(c.nom)}</option>`).join("")}</select></label>
        <textarea id="iacPrompt" data-dz-ia="image" rows="3" placeholder="${T("vectorlab.iacalque.placeholder")}"></textarea>
        <label class="ia-moteur">${T("vectorlab.ia.modele")}
          <select id="iacModele" title="${T("vectorlab.iacalque.modele_aide")}"><option value="">…</option></select></label>
        <label class="ia-moteur iac-case"><input type="checkbox" id="iacDetourer"/>${T("vectorlab.iacalque.retirer_fond")}</label>
        <label class="ia-moteur" id="iacDetourLigne" hidden>${T("vectorlab.iacalque.detourage")}
          <select id="iacDetour" title="${T("vectorlab.iacalque.detour_aide")}"><option value="">…</option></select></label>
        <input type="text" id="iacSujet" hidden placeholder="${T("vectorlab.iacalque.sujet")}" title="${T("vectorlab.iacalque.sujet_aide")}"/>
        <div class="iac-prix" id="iacPrix">${T("vectorlab.iacalque.prix_inconnu")}</div>
        <button id="iacGo" class="primaire">${dzi("dz-media-generer-image", 16)}<span id="iacGoTexte"></span></button>
        <div class="iac-etat" id="iacEtat" role="status"></div>
      </div>`;
    majBouton();
    const M = MI();
    if (!M) { $("#iacEtat").textContent = T("vectorlab.iacalque.catalogue_absent"); return; }
    M.select($("#iacModele"), "image", { valeur: lire("dz_vl_iac_modele") })
      .then((l) => { modsImage = l; majDevis(); })
      .catch(() => { $("#iacEtat").textContent = T("vectorlab.iacalque.catalogue_absent"); });
    M.select($("#iacDetour"), "detourage_image", { valeur: lire("dz_vl_iac_detour") })
      .then((l) => { modsDetour = l; majSujet(); majDevis(); })
      .catch(() => { /* le détourage reste sans liste : la case seule */ });
  }
  function majBouton() {
    const go = $("#iacGo"), tx = $("#iacGoTexte");
    if (!go || !tx) return;
    tx.textContent = lancer.enVol ? T("vectorlab.iacalque.en_cours") : T("vectorlab.iacalque.generer_sur", { nom: nomCalque(cible) });
    go.disabled = lancer.enVol || !cible;
  }
  function majSujet() {
    const c = choix();
    const l = $("#iacDetourLigne"), s = $("#iacSujet");
    if (l) l.hidden = !c.detourer;
    if (s) s.hidden = !(c.detourer && sujetRequis(modsDetour, c.modeleDetour));
  }
  let devisN = 0;
  async function majDevis() {
    const el = $("#iacPrix");
    if (!el) return;
    const n = ++devisN;
    el.textContent = T("vectorlab.iacalque.prix_inconnu");
    try {
      const d = await poster("/api/cost/estimate", devisCorps(choix()));
      if (n === devisN) el.textContent = libellePrix(d);
    } catch (e) {
      if (n === devisN) el.textContent = T("vectorlab.iacalque.prix_inconnu");
    }
  }

  async function tirer() {
    if (lancer.enVol) return;                       // anti-double tir : le second clic ne relance rien
    const c = choix(), etatEl = $("#iacEtat");
    try {
      verifierCible(etat.doc, c.calqueId);          // AVANT toute dépense
      requete(c);
      if (c.detourer && sujetRequis(modsDetour, c.modeleDetour) && !c.sujet.trim()) {
        throw new Error(T("vectorlab.iacalque.sujet_requis"));
      }
    } catch (e) { if (etatEl) etatEl.textContent = e.message; VL.toast(e.message, true); return; }
    if (c.modele) ecrire("dz_vl_iac_modele", c.modele);
    if (c.modeleDetour) ecrire("dz_vl_iac_detour", c.modeleDetour);
    const p = lancer(c);
    majBouton();
    if (etatEl) etatEl.textContent = T("vectorlab.iacalque.en_cours");
    try {
      const r = await p;
      if (r && etatEl) etatEl.textContent = T("vectorlab.iacalque.posee", { nom: r.nom, calque: nomCalque(c.calqueId) });
    } catch (e) {
      if (etatEl) etatEl.textContent = e.message;
      VL.toast(e.message, true);
    }
    majBouton();
  }

  function brancher(el) {
    el.addEventListener("click", (ev) => {
      const b = ev.target.closest("button");
      if (!b) return;
      if (b.dataset.act === "fermer") fermer();
      else if (b.id === "iacGo") tirer();
    });
    el.addEventListener("change", (ev) => {
      const id = ev.target.id;
      if (id === "iacCalque") { cible = ev.target.value; majBouton(); }
      if (id === "iacDetourer" || id === "iacDetour") majSujet();
      if (id === "iacModele" || id === "iacDetourer" || id === "iacDetour") majDevis();
    });
    el.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") fermer();
      if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey) && ev.target.id === "iacPrompt") { ev.preventDefault(); tirer(); }
    });
    brancherPoignee(el, $("#stage"), window);
    garderClics(el);
  }

  function ouvrir(calqueId) {
    if (!etat.doc) { VL.toast(T("vectorlab.image.aucun_doc"), true); return; }
    const el = hote();
    if (!el) return;
    // les outils Plume, Pixel, Nœud… écoutent #stage en CAPTURE (avant le panneau) : l'outil Sélection, lui, en bulle
    if (etat.outil !== "select" && VL.setOutil) VL.setOutil("select");
    const cibles = calquesCibles(etat.doc);
    cible = cibles.some((c) => c.id === calqueId) ? calqueId : (cibles[0] ? cibles[0].id : "");
    if (calqueId && cible !== calqueId) VL.toast(T("vectorlab.iacalque.calque_verrouille", { nom: nomCalque(calqueId) }), true);
    el.hidden = false;
    squelette(el);
    const p = $("#iacPrompt");
    if (p) p.focus();
  }
  function fermer() { const el = $("#iaCalqueDlg"); if (el) el.hidden = true; }

  /* ── « Retirer le fond » du panneau Image ── */
  async function versBiblio(o) {
    const r = await window.fetch(VL.imageUrl(o.href, o.rev, o.px));
    if (!r.ok) throw new Error(T("vectorlab.iacalque.image_illisible", { href: o.href }));
    const fd = new FormData();
    fd.append("file", new File([await r.blob()], nomDepot(etat.docId, o.href), { type: "image/png" }));
    const u = await window.fetch("/api/images/upload", { method: "POST", body: fd });
    const d = await u.json().catch(() => ({}));
    if (!u.ok) throw new Error(messageErreur(u.status, d, u.statusText));
    return d.filename;
  }
  async function deposer(nom) {
    const r = await window.fetch("/api/images/" + encodeURIComponent(nom));
    if (!r.ok) throw new Error(T("vectorlab.image.biblio_introuvable", { nom, status: r.status }));
    return VL.deposerBlob(await r.blob());
  }
  const detourer = unSeulVol((o, c) => retirerFondFlux(o, c, { versBiblio, post: poster, deposer, executer: VL.executer }));

  function ligneDetour(ligne, o) {
    ligne.innerHTML = `<span>${T("vectorlab.iacalque.fond")}</span>
      <select id="imDetourModele" title="${T("vectorlab.iacalque.detour_aide")}"><option value="">…</option></select>
      <button id="imDetourer" title="${T("vectorlab.iacalque.retirer_fond_titre")}"${detourer.enVol ? " disabled" : ""}>${dzi("dz-action-detourer", 16)}${detourer.enVol ? T("vectorlab.iacalque.en_cours") : T("vectorlab.iacalque.retirer_fond")}</button>
      <input type="text" id="imDetourSujet" hidden placeholder="${T("vectorlab.iacalque.sujet")}" title="${T("vectorlab.iacalque.sujet_aide")}"/>`;
    const sel = ligne.querySelector("#imDetourModele"), sujet = ligne.querySelector("#imDetourSujet");
    let mods = [];
    const maj = () => { sujet.hidden = !sujetRequis(mods, sel.value); };
    const M = MI();
    if (M) {
      catalogue("detourage_image").then((l) => {
        mods = l;
        if (sel.isConnected) { M.remplir(sel, l, { valeur: lire("dz_vl_iac_detour") }); maj(); }
      }).catch(() => { /* sans catalogue : le bouton refusera (aucun modèle) */ });
    }
    sel.addEventListener("change", () => { ecrire("dz_vl_iac_detour", sel.value); maj(); });
    ligne.querySelector("#imDetourer").addEventListener("click", async () => {
      if (detourer.enVol) return;
      if (sujetRequis(mods, sel.value) && !sujet.value.trim()) { VL.toast(T("vectorlab.iacalque.sujet_requis"), true); return; }
      VL.toast(T("vectorlab.iacalque.detour_en_cours"));
      try {
        const r = await detourer(o, { modele: sel.value, sujet: sujet.value });
        if (r) VL.toast(T("vectorlab.iacalque.detour_fait"));
      } catch (e) { VL.toast(e.message, true); }
    });
  }

  VL.iaCalque = { ouvrir, fermer, lancer, ligneDetour, taillePour, requete, etapes, verifierCible };
}
