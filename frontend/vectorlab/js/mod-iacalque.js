// mod-iacalque.js — t190 (G8, plan « Génération IA enrichie ») : l'IMAGE IA PAR CALQUE du Vectorlab.
//
// Le geste voulu : fond ; calque 1 : générer une image, retirer son fond ; calque 2 : texte et formes ;
// calque 3 : générer une autre image… Le panneau flottant « Image IA sur le calque » (même allure que le
// dialogue IA de mod-ia, posé sur #stage À GAUCHE — le dialogue IA est à droite —, déplaçable par sa tête)
// choisit le CALQUE cible (les calques non verrouillés, présélection = celui d'où l'on vient ; un calque masqué
// le dit), le MODÈLE (DzModelesIA, une option sans clé reste choisissable : le 503 n'arrive qu'au lancement), le
// FORMAT d'après la page, et le DÉTOURAGE (registre G4, sujet à garder si le modèle l'exige) ; le prix TOTAL est
// chiffré par le serveur (/api/cost/estimate, campagne image + détourage), jamais inventé. Sans liste des modèles
// (catalogue illisible), « Générer » reste gris et « Réessayer » relit la liste : le serveur ne tire jamais le
// modèle par défaut sans prix affiché. Jamais gris pour une clé manquante.
//
// Les modèles vectoriels (sortie « svg », Recraft) n'y sont PAS : l'image posée ici est un raster, et
// /images/generate refuse un modèle vectoriel sans `sortie: "svg"` (le dialogue IA du canevas, mod-ia, pose
// les tracés). « Retirer le fond » du panneau Image (ligneDetour, prix serveur affiché à côté) remplace l'image
// par une NOUVELLE image du magasin du document en UNE commande (op_image_remplacer de mod-doc via VL.executer) :
// Ctrl+Z rend l'image d'avant, dont le PNG reste au magasin.
//
// Les gestes du panneau : garderClics (mod-flottant, en bulle) et VL.dansPanneau (les outils en CAPTURE sortent).
// La logique PURE est en tête (banc qa/iacalque.test.mjs) ; initIaCalque ne touche le DOM qu'à l'appel.
import { T } from "./mod-i18n.js";
import { dzi } from "./mod-icones.js";
import { esc, garderClics } from "./mod-flottant.js";
import { op_image_remplacer, image_profonde } from "./mod-doc.js";

/* ── pur ── */
// les formats que /images/generate accepte (fal ; OpenAI et Nano Banana les traduisent, image_providers)
export const TAILLES = ["portrait_16_9", "portrait_4_3", "square_hd", "landscape_4_3", "landscape_16_9"];

// le rapport largeur / hauteur de chaque format
export const RAPPORTS = { portrait_16_9: 9 / 16, portrait_4_3: 3 / 4, square_hd: 1, landscape_4_3: 4 / 3, landscape_16_9: 16 / 9 };

// le format au rapport le plus PROCHE de la page (doc.taille), en écart LOGARITHMIQUE |ln(r) − ln(rf)| : un
// portrait et le paysage symétrique sont à égale distance du carré (2:3 → portrait_4_3, 9:16 → portrait_16_9)
export function taillePour(t) {
  const w = +(t && t.w), h = +(t && t.h);
  if (!(w > 0 && h > 0)) return "square_hd";
  const lr = Math.log(w / h);
  let mieux = "square_hd", ecart = Infinity;
  for (const f of TAILLES) {
    const e = Math.abs(lr - Math.log(RAPPORTS[f]));
    if (e < ecart - 1e-12) { ecart = e; mieux = f; }
  }
  return mieux;
}

// le corps de POST /api/images/generate ({prompt, n, model, size, source})
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

// les calques qu'on peut viser (le dessus en tête, comme le panneau Calques) ; un calque masqué le dit — l'image
// y serait posée invisible
export function calquesCibles(doc) {
  return [...((doc && doc.calques) || [])].reverse().filter((c) => !c.verrou)
    .map((c) => ({ id: c.id, nom: c.nom || c.id, masque: c.visible === false }));
}

// les <option> de la liste des calques (la cible présélectionnée)
export function optionsCalques(doc, cible) {
  return calquesCibles(doc).map((c) => `<option value="${esc(c.id)}"${c.id === cible ? " selected" : ""}>`
    + `${esc(c.nom)}${c.masque ? esc(T("vectorlab.iacalque.masque")) : ""}</option>`).join("");
}

// la cible après un changement du document : la même si elle est encore libre, sinon le calque demandé, sinon
// le premier libre, sinon aucune
export function cibleValide(doc, voulu, repli) {
  const ids = calquesCibles(doc).map((c) => c.id);
  if (ids.includes(voulu)) return voulu;
  if (ids.includes(repli)) return repli;
  return ids[0] || "";
}

// le devis serveur (POST /api/cost/estimate) : une campagne image + détourage
// sans modèle choisi, aucun devis plutôt qu'un prix faux (null → « Prix estimé : … ») — et « Générer » est gris
export function devisCorps(o) {
  if (!o || !o.modele) return null;
  const ops = [{ kind: "image", model: o.modele, n: 1 }];
  if (o && o.detourer && o.modeleDetour) ops.push({ kind: "detourage", modele: o.modeleDetour, images: 1 });
  return { kind: "campaign", ops };
}

// le devis du seul détourage (le bouton « Retirer le fond » du panneau Image)
export function devisDetour(modele) {
  return modele ? { kind: "campaign", ops: [{ kind: "detourage", modele: String(modele), images: 1 }] } : null;
}

// le montant en dollars : DzModelesIA.prixUsd (la même ligne de code que les listes de modèles) ; repli au banc ou
// sans le script, même règle (arrondi au millième, au moins deux décimales)
function dollars(v) {
  const M = typeof window !== "undefined" && window.DzModelesIA;
  const p = M && typeof M.prixUsd === "function" ? M.prixUsd(v) : "";
  if (p) return p;
  let s = (Math.round(v * 1000) / 1000).toFixed(3);
  while (/\.\d{3,}$/.test(s) && s.endsWith("0")) s = s.slice(0, -1);
  return "$" + s;
}

// le libellé du prix : jamais « gratuit » pour un 0 $ payant (« à mesurer ») ; une ligne locale à 0 $ l'est. Le
// total partiel NOMME la ligne à mesurer d'après le devis : l'image (unité « image ») ou le détourage (les autres)
export function libellePrix(devis) {
  if (!devis || !Array.isArray(devis.breakdown)) return T("vectorlab.iacalque.prix_inconnu");
  const total = +devis.total_usd || 0;
  const aMesurer = devis.breakdown.filter((l) => !(+l.usd > 0) && l.provider !== "local");
  if (!(total > 0)) {
    return devis.breakdown.length && !aMesurer.length ? T("vectorlab.iacalque.prix_gratuit") : T("vectorlab.iacalque.prix_a_mesurer");
  }
  const image = aMesurer.some((l) => l.unit === "image"), detour = aMesurer.some((l) => l.unit !== "image");
  return T("vectorlab.iacalque.prix", { prix: dollars(total) })
    + (image ? T("vectorlab.iacalque.prix_partiel_image") : "") + (detour ? T("vectorlab.iacalque.prix_partiel") : "");
}

// le message d'une réponse en échec : 503 = clé absente (lisible), le 402 d'un plafond refusé rend une chaîne
export function messageErreur(status, d, statut) {
  const det = d && d.detail;
  const m = typeof det === "string" ? det
    : det && det.dz_plafond && det.dz_plafond.message ? det.dz_plafond.message
      : det ? JSON.stringify(det) : (statut || String(status));
  return status === 503 ? T("vectorlab.iacalque.cle_absente", { detail: m }) : m;
}

// fetch rejette par un TypeError (« Failed to fetch », « NetworkError… ») quand le serveur ne répond pas : un
// message lisible, dans la langue de l'interface
export async function chercher(url, init, f = (typeof window !== "undefined" && window.fetch) || globalThis.fetch) {
  try { return await f(url, init); } catch (e) { throw new Error(T("vectorlab.iacalque.reseau")); }
}

// UN SEUL tir à la fois : un second appel pendant le vol ne relance rien (rend null) ; `apres` (facultatif) est
// rappelé une fois le vol fini, réussi ou non — l'appelant y redessine ses boutons (« en cours… » ne reste jamais)
export function unSeulVol(fn, apres) {
  const g = async (...a) => {
    if (g.enVol) return null;
    g.enVol = true;
    try { return await fn(...a); } finally {
      g.enVol = false;
      if (apres) { try { apres(); } catch (e) { /* le redessin n'efface pas l'issue du tir */ } }
    }
  };
  g.enVol = false;
  return g;
}

// l'état de « Générer » : gris pendant le vol, sans calque libre, et tant que la liste des modèles n'est pas lue
// (chargement), illisible (raison « catalogue » : message + Réessayer) ou lue mais VIDE (raison « vide » : aucun
// modèle d'image à proposer) — sinon le serveur tirerait le modèle par défaut sans prix affiché. JAMAIS gris pour une clé manquante : l'option sans clé reste choisissable, le 503
// n'arrive qu'au lancement (décision de l'utilisateur 11/10).
//   catalogue : "chargement" | "ok" | "echec" ; modele : la valeur de la liste ("" = aucune)
export function etatGenerer({ enVol, cible, catalogue, modele }) {
  if (enVol) return { gris: true, raison: "" };
  if (!cible) return { gris: true, raison: "calque" };
  if (catalogue === "echec") return { gris: true, raison: "catalogue" };
  if (catalogue === "ok" && !modele) return { gris: true, raison: "vide" };
  if (catalogue !== "ok") return { gris: true, raison: "" };
  return { gris: false, raison: "" };
}

// le détourage demandé est complet AVANT la génération payée : un modèle, sa clé (l'option sans clé reste
// CHOISISSABLE, seul le lancement est refusé) et le sujet si le modèle l'exige. `info` = l'entrée du catalogue
// detourage_image ({dispo, cle, prompt}) — LA source du « sujet requis » et de la clé ; null si inconnue.
// `sansCase` : le panneau Image n'a pas de case « Retirer le fond » à décocher — le message ne la propose pas.
export function verifierDetour(o, info, { sansCase = false } = {}) {
  if (!o || !o.detourer) return;
  requeteDetour({ nom: "", modele: o.modeleDetour, sujet: o.sujet });
  if (info && info.dispo === false) {
    throw new Error(T(sansCase ? "vectorlab.iacalque.detour_cle_image" : "vectorlab.iacalque.detour_cle", { cle: info.cle || "?" }));
  }
  if (info && info.prompt && !String(o.sujet || "").trim()) throw new Error(T("vectorlab.iacalque.sujet_requis"));
}

// le tir : cible vérifiée, génération, détourage éventuel, pose sur LE calque demandé — d = {doc(), post(url,
// corps), poser(nom, calqueId) → id (faux = pose refusée : VL.executer avale l'erreur), infoDetour(id)?}
// (fetch et pose réels dans la page, faux au banc). Tout refus GRATUIT part avant le premier POST. Un détourage
// qui échoue APRÈS la génération payée (plafond refusé, fournisseur en 502…) n'efface pas l'image payée : elle est
// posée telle quelle et `detourEchec` le dit. Une pose impossible le dit aussi, avec le nom gardé en Bibliothèque.
export async function executerPlan(o, d) {
  verifierCible(d.doc(), o.calqueId);
  requete(o);
  verifierDetour(o, o.detourer && d.infoDetour ? await d.infoDetour(o.modeleDetour) : null);
  let nom = null, detourEchec = "";
  for (const e of etapes(o)) {
    if (e.op === "generer") {
      const r = await d.post("/api/images/generate", requete(o));
      nom = (r && r.images || [])[0];
      if (!nom) throw new Error(T("vectorlab.image.generation_vide"));
    } else if (e.op === "detourer") {
      try {
        const r = await d.post("/api/images/process", requeteDetour({ nom, modele: e.modele, sujet: e.sujet }));
        const n2 = (r && r.images || [])[0];
        if (!n2) throw new Error(T("vectorlab.iacalque.detour_vide"));
        nom = n2;
      } catch (x) { detourEchec = String(x && x.message || x); }
    } else if (e.op === "poser") {
      let id;
      try {
        verifierCible(d.doc(), e.calqueId);        // verrouillé ou supprimé PENDANT le vol
        id = await d.poser(nom, e.calqueId);
      } catch (x) {
        throw new Error(T("vectorlab.iacalque.pose_echouee", { raison: String(x && x.message || x), nom }));
      }
      if (!id) throw new Error(T("vectorlab.iacalque.pose_echouee", { raison: T("vectorlab.iacalque.pose_refusee"), nom }));
      return detourEchec ? { nom, id, detourEchec } : { nom, id };
    }
  }
}

// « Retirer le fond » d'une image du document — d = {doc() → le document, versBiblio(o) → nom en Bibliothèque,
// post(url, corps), deposer(nom) → {href, nat} (nouvelle image du magasin du document), executer(fn, …args)}.
// Tout refus GRATUIT part avant le premier POST : modèle, et l'image RETROUVABLE par op_image_remplacer (la même
// recherche, qui descend dans les groupes) — jamais un détourage payé que la commande ne pourrait pas poser.
export async function retirerFondFlux(o, choix, d) {
  if (!o || o.type !== "image") throw new Error(T("vectorlab.iacalque.image_introuvable", { id: String(o && o.id) }));
  const corps = requeteDetour({ nom: "", modele: choix && choix.modele, sujet: choix && choix.sujet });
  image_profonde(d.doc(), o.id);
  corps.filename = await d.versBiblio(o);
  const r = await d.post("/api/images/process", corps);
  const nom = (r && r.images || [])[0];
  if (!nom) throw new Error(T("vectorlab.iacalque.detour_vide"));
  const { href, nat } = await d.deposer(nom);
  // jamais par-dessus l'image d'avant : Annuler doit la retrouver
  if (href === o.href) throw new Error(T("vectorlab.iacalque.meme_image"));
  if (!d.executer(op_image_remplacer, o.id, href, nat)) {
    throw new Error(T("vectorlab.iacalque.detour_remplacement", { nom }));
  }
  return href;
}

// le nom du dépôt en Bibliothèque de l'image à détourer (`vector_` : provenance vectorlab, réécrit en place)
export function nomDepot(docId, href) {
  const a = (s) => String(s || "").replace(/\.png$/i, "").replace(/[^A-Za-z0-9_-]+/g, "-");
  return `vector_${a(docId)}_detour_${a(href)}.png`;
}

// le nom rendu par /api/images/upload, ou une erreur lisible (jamais un « filename » undefined envoyé au détourage)
export function nomDuDepot(d) {
  if (!d || !d.filename) throw new Error(T("vectorlab.iacalque.biblio_sans_nom"));
  return String(d.filename);
}

/* ── DOM ── */
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
    const r = await chercher(url, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corps), cache: "no-store" });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(messageErreur(r.status, d, r.statusText));
    return d;
  }

  // les catalogues (gratuits), lus une fois par page ; un échec se relira (Réessayer)
  const catalogues = {};
  function catalogue(nature) {
    if (!catalogues[nature]) {
      const M = MI();
      catalogues[nature] = M ? M.charger(nature).then((l) => M.filtrer(l)) : Promise.reject(new Error("DzModelesIA"));
      catalogues[nature].catch(() => { delete catalogues[nature]; });
    }
    return catalogues[nature];
  }
  // l'entrée du catalogue d'un modèle de détourage (dispo, clé, sujet exigé) — catalogue() est la SEULE source
  const infoDe = (mods, id) => (mods || []).find((m) => m.id === id) || null;
  const sujetRequis = (mods, id) => !!(infoDe(mods, id) || {}).prompt;

  /* ── le tir ── */
  const deps = {
    doc: () => etat.doc,
    post: poster,
    // le calque actif ne change qu'une fois la pose RÉUSSIE
    poser: async (nom, calqueId) => {
      const id = await VL.poserDepuisLibrary(nom, calqueId);
      if (id) etat.calqueActif = calqueId;
      return id;
    },
    infoDetour: async (id) => infoDe(await catalogue("detourage_image").catch(() => []), id),
  };
  const lancer = unSeulVol(async (o) => {
    VL.toast(T("vectorlab.image.generation"));
    return executerPlan({ ...o, taille: o.taille || taillePour(etat.doc && etat.doc.taille) }, deps);
  }, () => majBouton());

  /* ── le panneau ── */
  let cible = "", modsDetour = [], retour = null, etatCatalogue = "chargement", messageEcrit = "";
  function hote() {
    let el = $("#iaCalqueDlg");
    if (el) return el;
    const stage = $("#stage");
    if (!stage) return null;
    el = document.createElement("div");
    el.id = "iaCalqueDlg";
    el.className = "ia-dlg iac-dlg";
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-labelledby", "iacTitre");
    el.hidden = true;
    stage.appendChild(el);
    brancher(el);
    return el;
  }
  const ouvert = () => { const el = $("#iaCalqueDlg"); return !!(el && !el.hidden); };
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
    el.innerHTML = `
      <div class="ia-tete" data-poigne="1">
        <span class="ia-titre" id="iacTitre">${T("vectorlab.iacalque.titre")}</span>
        <span class="ia-sp"></span>
        <button class="ia-x" data-act="fermer" title="${T("vectorlab.ia.fermer")}" aria-label="${T("vectorlab.ia.fermer")}">${dzi("dz-action-fermer", 16)}</button>
      </div>
      <div class="ia-bas">
        <label class="ia-moteur">${T("vectorlab.iacalque.calque")}
          <select id="iacCalque" title="${T("vectorlab.iacalque.calque_aide")}">${optionsCalques(etat.doc, cible)}</select></label>
        <textarea id="iacPrompt" data-dz-ia="image" rows="3" placeholder="${T("vectorlab.iacalque.placeholder")}"></textarea>
        <label class="ia-moteur">${T("vectorlab.ia.modele")}
          <select id="iacModele" title="${T("vectorlab.iacalque.modele_aide")}"><option value="">…</option></select></label>
        <label class="ia-moteur iac-case"><input type="checkbox" id="iacDetourer"/>${T("vectorlab.iacalque.retirer_fond")}</label>
        <label class="ia-moteur" id="iacDetourLigne" hidden>${T("vectorlab.iacalque.detourage")}
          <select id="iacDetour" title="${T("vectorlab.iacalque.detour_aide")}"><option value="">…</option></select></label>
        <input type="text" id="iacSujet" class="iac-sujet" hidden placeholder="${T("vectorlab.iacalque.sujet")}" title="${T("vectorlab.iacalque.sujet_aide")}"/>
        <div class="iac-prix" id="iacPrix">${T("vectorlab.iacalque.prix_inconnu")}</div>
        <button id="iacGo" class="primaire">${dzi("dz-media-generer-image", 16)}<span id="iacGoTexte"></span></button>
        <div class="iac-etat-ligne"><span class="iac-etat" id="iacEtat" role="status"></span>
          <span class="iac-sep" id="iacSep" hidden>—</span><button id="iacReessayer" class="iac-reessayer" hidden>${T("vectorlab.iacalque.reessayer")}</button></div>
      </div>`;
    chargerModeles();
    catalogue("detourage_image").then((l) => {
      modsDetour = l;
      const sel = $("#iacDetour"), M = MI();
      if (sel && sel.isConnected && M) { M.remplir(sel, l, { valeur: lire("dz_vl_iac_detour") }); majSujet(); majDevis(); }
    }).catch(() => { /* le détourage reste sans liste : la case seule (le tir le refusera, sans dépense) */ });
  }
  // la liste des modèles d'image (cache par page) ; un échec → « Générer » gris + Réessayer
  function chargerModeles() {
    etatCatalogue = "chargement";
    majBouton();
    catalogue("image").then((l) => {
      const sel = $("#iacModele"), M = MI();
      if (sel && sel.isConnected && M) M.remplir(sel, l, { valeur: lire("dz_vl_iac_modele") });
      etatCatalogue = "ok";
      majBouton(); majDevis();
    }).catch(() => { etatCatalogue = "echec"; majBouton(); });
  }
  // la liste des calques seule (réouverture, calque ajouté / renommé / verrouillé / masqué) : le prompt, les
  // listes de modèles et le message restent
  // les <option> ne sont réécrites que si elles ont CHANGÉ : un rendu du document ne referme pas une liste ouverte
  let sigCalques = "";
  function majCalques() {
    const sel = $("#iacCalque");
    cible = cibleValide(etat.doc, cible, "");
    if (sel) {
      const sig = optionsCalques(etat.doc, cible);
      if (sig !== sigCalques) { sel.innerHTML = sig; sigCalques = sig; }
      if (sel.value !== cible) sel.value = cible;
    }
    majBouton();
  }
  function majBouton() {
    const go = $("#iacGo"), tx = $("#iacGoTexte");
    if (!go || !tx) return;
    const { gris, raison } = etatGenerer({ enVol: lancer.enVol, cible, catalogue: etatCatalogue, modele: ($("#iacModele") || {}).value || "" });
    tx.textContent = lancer.enVol ? T("vectorlab.iacalque.en_cours") : T("vectorlab.iacalque.generer_sur", { nom: nomCalque(cible) });
    go.disabled = gris;
    const e = $("#iacEtat"), re = $("#iacReessayer"), sep = $("#iacSep");
    if (re) re.hidden = raison !== "catalogue";
    if (sep) sep.hidden = raison !== "catalogue";
    const m = raison === "calque" ? T("vectorlab.iacalque.aucun_calque_libre")
      : raison === "catalogue" ? T("vectorlab.iacalque.catalogue_absent")
        : raison === "vide" ? T("vectorlab.iacalque.modeles_vides") : "";
    if (e) {
      // la raison est écrite ; une raison levée efface SON message (jamais l'issue d'un tir)
      if (m) e.textContent = m;
      else if (messageEcrit && e.textContent === messageEcrit) e.textContent = "";
    }
    messageEcrit = m;
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
      const corps = devisCorps(choix());
      if (!corps) return;                            // aucun modèle : « Prix estimé : … », jamais un prix faux
      const d = await poster("/api/cost/estimate", corps);
      if (n === devisN) el.textContent = libellePrix(d);
    } catch (e) {
      if (n === devisN) el.textContent = T("vectorlab.iacalque.prix_inconnu");
    }
  }

  async function tirer() {
    if (lancer.enVol) return;                       // anti-double tir : le second clic ne relance rien
    if (etatGenerer({ enVol: false, cible, catalogue: etatCatalogue, modele: ($("#iacModele") || {}).value || "" }).gris) return;
    const c = choix(), dire = (t) => { const e = $("#iacEtat"); if (e) e.textContent = t; };   // relu à chaque fois
    try {
      verifierCible(etat.doc, c.calqueId);          // AVANT toute dépense
      requete(c);
      verifierDetour(c, infoDe(modsDetour, c.modeleDetour));
    } catch (e) { dire(e.message); VL.toast(e.message, true); return; }
    if (c.modele) ecrire("dz_vl_iac_modele", c.modele);
    if (c.modeleDetour) ecrire("dz_vl_iac_detour", c.modeleDetour);
    const p = lancer(c);
    majBouton();
    dire(T("vectorlab.iacalque.en_cours"));
    try {
      const r = await p;
      if (r && r.detourEchec) {
        const t = T("vectorlab.iacalque.detour_echoue_pose", { raison: r.detourEchec, calque: nomCalque(c.calqueId) });
        dire(t); VL.toast(t, true);
      } else if (r) dire(T("vectorlab.iacalque.posee", { nom: r.nom, calque: nomCalque(c.calqueId) }));
    } catch (e) {
      dire(e.message);
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
      else if (b.id === "iacReessayer") chargerModeles();
    });
    el.addEventListener("change", (ev) => {
      const id = ev.target.id;
      if (id === "iacCalque") { cible = ev.target.value; majBouton(); }
      if (id === "iacModele") majBouton();
      if (id === "iacDetourer" || id === "iacDetour") majSujet();
      if (id === "iacModele" || id === "iacDetourer" || id === "iacDetour") majDevis();
    });
    el.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") { ev.preventDefault(); fermer(); }
      if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey) && ev.target.id === "iacPrompt") { ev.preventDefault(); tirer(); }
    });
    brancherPoignee(el, $("#stage"), window);
    garderClics(el);
  }

  function ouvrir(calqueId) {
    if (!etat.doc) { VL.toast(T("vectorlab.image.aucun_doc"), true); return; }
    const el = hote();
    if (!el) return;
    const dejaOuvert = !el.hidden, construit = !!$("#iacPrompt");
    // le focus reviendra à l'élément d'ouverture (bouton du calque, menu…) à la fermeture
    if (!dejaOuvert) retour = document.activeElement && document.activeElement !== document.body ? document.activeElement : null;
    // l'outil actif reste : les outils en CAPTURE sortent devant un panneau flottant (VL.dansPanneau)
    cible = cibleValide(etat.doc, calqueId, "");
    if (calqueId && cible !== calqueId) {
      const c = etat.doc.calques.find((x) => x.id === calqueId);
      VL.toast(c ? T("vectorlab.iacalque.calque_verrouille", { nom: c.nom || c.id })
        : cible ? T("vectorlab.iacalque.calque_disparu", { nom: nomCalque(cible) })
          : T("vectorlab.iacalque.aucun_calque_libre"), true);
    }
    el.hidden = false;
    // le squelette n'est construit qu'UNE fois : rouvert (ou déjà ouvert), la liste des calques seule — le prompt
    // tapé et les listes de modèles restent ; une liste de modèles illisible est relue
    if (!construit) squelette(el);
    else { majCalques(); if (etatCatalogue === "echec") chargerModeles(); }
    const p = $("#iacPrompt");
    if (p) p.focus();
  }
  function fermer() {
    const el = $("#iaCalqueDlg");
    if (!el || el.hidden) return;
    el.hidden = true;
    if (retour && retour.isConnected && typeof retour.focus === "function") retour.focus();
    retour = null;
  }
  // la liste suit le document (calque ajouté, renommé, verrouillé, masqué, supprimé)
  const suivantRendu = VL.surRendu;
  VL.surRendu = () => { if (suivantRendu) suivantRendu(); if (ouvert()) majCalques(); };

  /* ── « Retirer le fond » du panneau Image ── */
  async function versBiblio(o) {
    const r = await chercher(VL.imageUrl(o.href, o.rev, o.px), { cache: "no-store" });
    if (!r.ok) throw new Error(T("vectorlab.iacalque.image_illisible", { href: o.href }));
    const fd = new FormData();
    fd.append("file", new File([await r.blob()], nomDepot(etat.docId, o.href), { type: "image/png" }));
    const u = await chercher("/api/images/upload", { method: "POST", body: fd, cache: "no-store" });
    const d = await u.json().catch(() => ({}));
    if (!u.ok) throw new Error(messageErreur(u.status, d, u.statusText));
    return nomDuDepot(d);
  }
  async function deposer(nom) {
    const r = await chercher("/api/images/" + encodeURIComponent(nom), { cache: "no-store" });
    if (!r.ok) throw new Error(T("vectorlab.image.biblio_introuvable", { nom, status: r.status }));
    return VL.deposerBlob(await r.blob());
  }
  // le bouton du panneau Image : son état suit le vol, et il est REDESSINÉ à la fin (le panneau a pu être rendu
  // pendant le vol — executer → surRendu — avec « en cours… »). Seule pose de son icône et de son libellé :
  // ligneDetour lui passe le bouton qu'elle vient de créer
  function majBoutonDetour(b = $("#imDetourer")) {
    if (!b) return;
    b.disabled = detourer.enVol;
    b.innerHTML = dzi("dz-action-detourer", 16) + (detourer.enVol ? T("vectorlab.iacalque.en_cours") : T("vectorlab.iacalque.retirer_fond"));
  }
  // la barre d'options mesure la boîte de l'objet À L'ÉCRAN : rendue avant que la nouvelle image ne soit chargée,
  // elle se trompait (X −146 au lieu de 0, preuve 8799) — on la remesure au chargement de chaque image sélectionnée
  function remesurer() {
    for (const id of etat.selection || []) {
      const g = document.querySelector(`#canvasHost [data-objet="${String(id).replace(/"/g, "")}"]`);
      const im = g && (g.tagName && g.tagName.toLowerCase() === "image" ? g : g.querySelector("image"));
      if (im) im.addEventListener("load", () => { if (VL.surSelection) VL.surSelection(); }, { once: true });
    }
  }
  const detourer = unSeulVol(async (o, c) => {
    const href = await retirerFondFlux(o, c, { doc: () => etat.doc, versBiblio, post: poster, deposer, executer: VL.executer });
    remesurer();
    return href;
  }, () => majBoutonDetour());
  // Annuler / Refaire du détourage : la même remesure
  const suivantHisto = VL.surHistorique;
  VL.surHistorique = () => { if (suivantHisto) suivantHisto(); remesurer(); };

  // le sujet tapé, par image : la ligne est reconstruite à chaque rendu du panneau Image
  const sujets = new Map();
  // le prix du détourage par modèle (devis serveur) : la PROMESSE est gardée (un devis en vol n'est pas redemandé, le
  // même chiffre avant et après le rendu, sans clignoter) ; un échec n'est pas gardé, mais n'est relu qu'après 30 s
  // (pas une requête à chaque rendu). On n'écrit que dans une ligne encore affichée, pour le modèle encore choisi.
  const prixDetour = new Map(), echecPrix = new Map();
  function prixDe(modele) {
    if (prixDetour.has(modele)) return prixDetour.get(modele);
    if (Date.now() - (echecPrix.get(modele) || -Infinity) < 30000) return Promise.reject(new Error("devis"));
    const p = poster("/api/cost/estimate", devisDetour(modele)).then(libellePrix);
    prixDetour.set(modele, p);
    p.catch(() => { prixDetour.delete(modele); echecPrix.set(modele, Date.now()); });
    return p;
  }
  async function majPrixDetour(span, sel) {
    const modele = sel.value;
    if (!modele) { span.textContent = ""; return; }
    span.textContent = T("vectorlab.iacalque.prix_inconnu");
    let t;
    try { t = await prixDe(modele); } catch (e) { t = T("vectorlab.iacalque.prix_inconnu"); }
    if (span.isConnected && sel.value === modele) span.textContent = t;
  }

  function ligneDetour(ligne, o) {
    ligne.innerHTML = `<span>${T("vectorlab.iacalque.fond")}</span>
      <select id="imDetourModele" title="${T("vectorlab.iacalque.detour_aide")}"><option value="">…</option></select>
      <button id="imDetourer" title="${T("vectorlab.iacalque.retirer_fond_titre")}"></button>
      <span class="iac-prix" id="imDetourPrix"></span>
      <input type="text" id="imDetourSujet" class="iac-sujet" hidden placeholder="${T("vectorlab.iacalque.sujet")}" title="${T("vectorlab.iacalque.sujet_aide")}"/>`;
    const sel = ligne.querySelector("#imDetourModele"), sujet = ligne.querySelector("#imDetourSujet");
    const prix = ligne.querySelector("#imDetourPrix");
    sujet.value = sujets.get(o.id) || "";
    let mods = [];
    const maj = () => { sujet.hidden = !sujetRequis(mods, sel.value); majPrixDetour(prix, sel); };
    majBoutonDetour(ligne.querySelector("#imDetourer"));
    const M = MI();
    if (M) {
      catalogue("detourage_image").then((l) => {
        mods = l;
        if (sel.isConnected) { M.remplir(sel, l, { valeur: lire("dz_vl_iac_detour") }); maj(); }
      }).catch(() => { /* sans catalogue : le bouton refusera (aucun modèle) */ });
    }
    sel.addEventListener("change", () => { ecrire("dz_vl_iac_detour", sel.value); maj(); });
    sujet.addEventListener("input", () => sujets.set(o.id, sujet.value));
    ligne.querySelector("#imDetourer").addEventListener("click", async () => {
      if (detourer.enVol) return;
      // mêmes refus gratuits que le tir : modèle, clé, sujet — avant tout envoi (pas de case ici : sansCase)
      try { verifierDetour({ detourer: true, modeleDetour: sel.value, sujet: sujet.value }, infoDe(mods, sel.value), { sansCase: true }); }
      catch (e) { VL.toast(e.message, true); return; }
      VL.toast(T("vectorlab.iacalque.detour_en_cours"));
      try {
        const p = detourer(o, { modele: sel.value, sujet: sujet.value });
        majBoutonDetour();
        const r = await p;
        if (r) VL.toast(T("vectorlab.iacalque.detour_fait"));
      } catch (e) { VL.toast(e.message, true); }
    });
  }

  VL.iaCalque = { ouvrir, fermer, ligneDetour };
}
