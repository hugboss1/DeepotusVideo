// mod-iacalque.js — t191 (G9, plan « Génération IA ») : le CALQUE IA et le DÉTOURAGE NON DESTRUCTIF du Photolab.
//
// Deux gestes, un même panneau flottant (allure des dialogues de réglage : tête déplaçable, posé en haut à droite de la
// scène) :
//   · « Nouveau calque IA… » (Calque, bouton « IA » du pied du panneau Calques) : prompt, MODÈLE (DzModelesIA, sans les
//     modèles vectoriels ; un modèle sans clé reste CHOISISSABLE, le 503 n'arrive qu'au lancement), case « Retirer le
//     fond » + modèle de détourage (registre G4) + sujet si le modèle l'exige ; le calque visé (« Le nouveau calque se
//     place au-dessus de « X » ») ; POST /api/photolab/calque/ia : génération, détourage éventuel, pose en calque de
//     PIXELS au-dessus du calque choisi, nommé « IA — <début du prompt> » ;
//   · « Retirer le fond du calque » : POST /api/photolab/calque/detourer — la copie détourée est posée au-dessus,
//     l'original MASQUÉ dessous, jamais supprimé.
// Le prix TOTAL est chiffré par le serveur (/api/cost/estimate, campagne image + détourage), jamais inventé : 0 $ =
// « prix à mesurer », aucun devis sans modèle. Tout refus gratuit (calque absent, groupe, verrouillé, prompt vide,
// modèle de détourage, clé du détourage, sujet) part AVANT le premier POST. Annuler passe par l'historique du MOTEUR :
// le calque IA part en DEUX Ctrl+Z (Renommer, Coller), le détourage en TROIS (masquage, Renommer, Coller).
//
// HÉBERGEMENT : le panneau vit dans document.body (comme les dialogues de réglage), HORS de #scene : les gestionnaires
// de la toile (#toile : pointerdown + setPointerCapture + preventDefault de l'outil, glisser de la vue) ne sont pas ses
// ancêtres. Ses gestes s'arrêtent quand même à lui (garderGestes) : aucun écouteur du document (menus, outils, raccourcis
// clavier globaux — une lettre sur un bouton du panneau changeait d'outil) ne les voit.
//
// La logique PURE est en tête (banc qa/iacalque.test.mjs) ; initIaCalque ne touche le DOM qu'à l'appel. t197 : ce qui
// est commun avec le panneau du Vectorlab (formats, devis, prix, refus, un seul vol, gestes gardés) vient de
// /shared/dz-iacalque-commun.js — ici, l'adaptation au document du moteur et aux clés photolab.iacalque.*.
import { positionInitiale, bornerPosition } from "./mod-dialogue-reglage.js";
import * as C from "../../shared/dz-iacalque-commun.js";

const T = (cle, vars) => (typeof window !== "undefined" && window.dzT ? window.dzT(cle, vars) : cle);
// les rôles du module commun -> les clés du Photolab, écrites EN ENTIER (les bancs relèvent les clés par leur texte)
const CLES = {
  prix_inconnu: "photolab.iacalque.prix_inconnu", prix_a_mesurer: "photolab.iacalque.prix_a_mesurer",
  prix_gratuit: "photolab.iacalque.gratuit", prix: "photolab.iacalque.prix",
  prix_partiel_image: "photolab.iacalque.prix_partiel_image", prix_partiel: "photolab.iacalque.prix_partiel",
  cle_absente: "photolab.iacalque.cle_absente", detour_modele: "photolab.iacalque.detour_modele",
  detour_cle: "photolab.iacalque.detour_cle", detour_cle_image: "photolab.iacalque.detour_cle",
  sujet_requis: "photolab.iacalque.sujet_requis",
};
const tr = (role, vars) => T(CLES[role], vars);

/* ── pur ── */
export { TAILLES, RAPPORTS, unSeulVol, dollars, GESTES_GARDES, garderGestes } from "../../shared/dz-iacalque-commun.js";

// le format au rapport le plus PROCHE du document du moteur ({width, height})
export const taillePour = (doc) => C.formatPour(doc && doc.width, doc && doc.height);

const aplatir = (layers) => {
  const out = [];
  const voir = (l) => { for (const c of l || []) { out.push(c); if (Array.isArray(c.children)) voir(c.children); } };
  voir(layers);
  return out;
};
export const estGroupe = (c) => !!c && (Array.isArray(c.children) || /^(group|artboard)$/i.test(String(c.kind || "")));
export const estReglage = (c) => !!c && /^adjustment$/i.test(String(c.kind || ""));
// un verrou posé par le panneau Calques (PL.etat.verrous : le moteur ne les relit pas)
export const estVerrouille = (verrous, id) => Object.values((verrous || {})[id] || {}).some(Boolean);

// la cible AVANT toute dépense : un calque absent, un groupe ou un calque verrouillé est refusé, rien ne part
export function verifierCible(doc, verrous, id, mode = "ia") {
  const c = aplatir(doc && doc.layers).find((x) => x.id === id);
  if (!c) throw new Error(T("photolab.iacalque.calque_absent", { id: String(id) }));
  const nom = c.name || String(c.id);
  if (estGroupe(c)) throw new Error(T("photolab.iacalque.calque_groupe", { nom }));
  if (estVerrouille(verrous, id)) throw new Error(T("photolab.iacalque.calque_verrouille", { nom }));
  if (mode === "detour" && estReglage(c)) throw new Error(T("photolab.iacalque.calque_reglage", { nom }));
  return c;
}

// les calques qu'on peut viser (haut -> bas, comme le panneau Calques)
export function calquesCibles(doc, verrous, mode = "ia") {
  return aplatir(doc && doc.layers)
    .filter((c) => !estGroupe(c) && !estVerrouille(verrous, c.id) && !(mode === "detour" && estReglage(c)))
    .map((c) => ({ id: c.id, nom: c.name || String(c.id) }));
}

// le corps de POST /api/photolab/calque/ia ; sans modèle, le serveur prend celui des Réglages
export function requete(o) {
  const prompt = String((o && o.prompt) || "").trim();
  if (!prompt) throw new Error(T("photolab.iacalque.prompt_vide"));
  const q = { prompt, taille: C.TAILLES.includes(o.taille) ? o.taille : "square_hd", auDessusDe: o.auDessusDe, detourer: !!o.detourer };
  if (o.modele) q.modele = String(o.modele);
  if (o.detourer) {
    if (!o.modeleDetour) throw new Error(T("photolab.iacalque.detour_modele"));
    q.modeleDetour = String(o.modeleDetour);
    const sujet = String(o.sujet || "").trim();
    if (sujet) q.sujet = sujet;
  }
  const nom = String(o.nom || "").trim();
  if (nom) q.nom = nom;
  if (o.reduire === false) q.reduire = false;      // préférence « redimensionner pendant le placement » décochée
  return q;
}

// le corps de POST /api/photolab/calque/detourer
export function requeteDetour(o) {
  if (!o || !o.modeleDetour) throw new Error(T("photolab.iacalque.detour_modele"));
  const q = { layer: o.calque, modele: String(o.modeleDetour) };
  const sujet = String(o.sujet || "").trim();
  if (sujet) q.sujet = sujet;
  return q;
}

// le détourage demandé est complet AVANT la dépense : un modèle, sa clé (l'option sans clé reste CHOISISSABLE, seul le
// lancement est refusé — ici, avant tout POST, quand le catalogue dit dispo:false) et le sujet si le modèle l'exige.
// `info` = l'entrée du catalogue detourage_image ({dispo, cle, prompt}), null si inconnue.
export const verifierDetour = (o, info) => C.verifierDetour(o, info, tr);

// le devis serveur (POST /api/cost/estimate) — sans modèle choisi, aucun devis plutôt qu'un prix faux ; le mode
// « detour » (Retirer le fond du calque) ne génère pas d'image
export const devisCorps = (o) => (o ? C.devisCorps({ image: o.mode !== "detour", modele: o.modele,
  detourer: !!o.detourer || o.mode === "detour", modeleDetour: o.modeleDetour }) : null);

// jamais « gratuit » pour un 0 $ payant (« à mesurer ») ; une ligne locale à 0 $ l'est ; la part à mesurer est nommée
export const libellePrix = (devis) => C.libellePrix(devis, tr);

// le message d'une réponse en échec : 503 = clé absente (le détail la nomme), 402 refusé = le message du plafond
export const messageErreur = (statut, corps) => C.messageErreur(statut, corps, "", tr);

// le nom du calque que le serveur posera (même règle que photolab_routes : « IA — » + 15 premiers caractères)
export function nomCalqueIa(prompt) {
  return T("photolab.iacalque.nom_calque", { debut: String(prompt || "").trim().slice(0, 15) });
}

// le TIR — d = {doc(), verrous(), post(chemin, corps) → réponse (lève sur échec), cycle(), selectionner(id),
// infoDetour(id)?}. Tout refus GRATUIT part avant le POST. La réponse DOIT porter le calque posé : une réponse sans
// `layer` (pose avalée) lève, jamais un « posé » annoncé à tort. Après la pose : un cycle (inspect, rendu, vignettes),
// puis le nouveau calque sélectionné s'il ne l'est pas déjà.
export async function executerPlan(o, d) {
  const mode = o.mode === "detour" ? "detour" : "ia";
  const cible = mode === "detour" ? o.calque : o.auDessusDe;
  verifierCible(d.doc(), d.verrous(), cible, mode);
  const corps = mode === "detour" ? requeteDetour(o) : requete(o);
  verifierDetour({ ...o, detourer: mode === "detour" || o.detourer }, (mode === "detour" || o.detourer) && d.infoDetour
    ? await d.infoDetour(o.modeleDetour) : null);
  const r = await d.post(mode === "detour" ? "/calque/detourer" : "/calque/ia", corps);
  if (!r || !Number.isInteger(r.layer)) throw new Error(T("photolab.iacalque.pose_inconnue", { nom: (r && r.image) || "?" }));
  await d.cycle();
  const doc = d.doc();
  if (doc && doc.activeLayer !== r.layer) await d.selectionner(r.layer);
  return r;
}

/* ── DOM ── */
// Les gestes du panneau s'arrêtent à lui : garderGestes (module commun) — clic, molette, touche ENFONCÉE ; jamais un
// relâchement (t197 : keyup gardé, Espace relâché sur un bouton du panneau laissait l'outil Main de mod-vue collé).

export function initIaCalque(PL) {
  const lire = (k) => { try { return localStorage.getItem(k) || ""; } catch (e) { return ""; } };
  const ecrire = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* stockage indisponible */ } };
  const MI = () => (typeof window !== "undefined" && window.DzModelesIA) || null;
  const el = (tag, classe, texte) => { const e = document.createElement(tag); if (classe) e.className = classe; if (texte != null) e.textContent = texte; return e; };

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
  const infoDe = (mods, id) => (mods || []).find((m) => m.id === id) || null;

  // HORS de PL.file (la file unique du moteur) : la génération dure de quelques secondes à deux minutes, le Photolab
  // reste utilisable pendant ce temps (le serveur revérifie document et calque avant de poser). essai = 1 : JAMAIS de
  // relance automatique — mod-api rejoue un 409, et un POST rejoué après la dépense paierait deux fois.
  async function poster(chemin, corps) {
    try {
      return await PL.api("POST", chemin, corps, 1, true);
    } catch (e) {
      throw new Error(e && e.statut ? messageErreur(e.statut, e.corps) : String((e && e.message) || e));
    }
  }
  const deps = {
    doc: () => PL.etat.doc,
    verrous: () => PL.etat.verrous,
    post: poster,
    cycle: () => PL.cycle(),
    selectionner: (id) => PL.executer("layer.select", { layer: id, mode: "replace" }),
    infoDetour: async (id) => infoDe(await catalogue("detourage_image").catch(() => []), id),
  };
  const lancer = C.unSeulVol((o) => executerPlan(o, deps), () => majBouton());

  /* ── le panneau ── */
  let boite = null, ui = null, mode = "ia", cible = null, modsDetour = [], retour = null, devisN = 0;
  const nomCalque = (id) => { const c = aplatir(PL.etat.doc && PL.etat.doc.layers).find((x) => x.id === id); return c ? (c.name || String(id)) : String(id); };

  function construire() {
    boite = el("div", "pl-dlg pl-reglage pl-iacalque");
    boite.setAttribute("role", "dialog");
    const tete = el("header", "pl-dlg-tete pl-reglage-tete");
    const titre = el("span", "pl-reglage-titre"); titre.id = "plIacTitre";
    boite.setAttribute("aria-labelledby", titre.id);
    const fermerB = el("button", "pl-iac-x"); fermerB.type = "button"; fermerB.dataset.act = "fermer";
    fermerB.title = T("photolab.iacalque.fermer"); fermerB.setAttribute("aria-label", fermerB.title);
    fermerB.innerHTML = PL.icone ? PL.icone("dz-action-fermer", 14) : "";
    tete.append(titre, fermerB);
    const corps = el("div", "pl-dlg-corps pl-reglage-corps");
    const lieu = el("p", "pl-iac-lieu");                        // « Le nouveau calque se place au-dessus de « X » »
    const ligneCalque = el("label", "pl-rg-champ sorte-liste");
    const selCalque = el("select", "pl-rg-choix"); selCalque.title = T("photolab.iacalque.calque_aide");
    ligneCalque.append(el("span", "pl-rg-lib", T("photolab.iacalque.calque")), selCalque);
    const prompt = el("textarea", "pl-iac-prompt"); prompt.rows = 3;
    prompt.setAttribute("data-dz-ia", "image");
    prompt.setAttribute("placeholder", T("photolab.iacalque.placeholder"));
    prompt.setAttribute("aria-label", T("photolab.iacalque.prompt"));
    const ligneModele = el("label", "pl-rg-champ sorte-liste");
    const selModele = el("select", "pl-rg-choix"); selModele.title = T("photolab.iacalque.modele_aide");
    ligneModele.append(el("span", "pl-rg-lib", T("photolab.iacalque.modele")), selModele);
    const ligneCase = el("label", "pl-rg-champ sorte-case");
    const caseDetour = el("input"); caseDetour.type = "checkbox";
    ligneCase.append(caseDetour, el("span", "", T("photolab.iacalque.retirer_fond")));
    const ligneDetour = el("label", "pl-rg-champ sorte-liste");
    const selDetour = el("select", "pl-rg-choix"); selDetour.title = T("photolab.iacalque.detour_aide");
    ligneDetour.append(el("span", "pl-rg-lib", T("photolab.iacalque.detourage")), selDetour);
    const sujet = el("input", "pl-rg-saisie"); sujet.type = "text";
    sujet.setAttribute("placeholder", T("photolab.iacalque.sujet")); sujet.title = T("photolab.iacalque.sujet_aide");
    const prix = el("p", "pl-iac-prix", T("photolab.iacalque.prix_inconnu"));
    const etat = el("p", "pl-iac-etat"); etat.setAttribute("role", "status");
    corps.append(lieu, ligneCalque, prompt, ligneModele, ligneCase, ligneDetour, sujet, prix, etat);
    const pied = el("footer", "pl-dlg-pied pl-reglage-pied");
    const go = el("button", "pl-bouton principal"); go.type = "button"; go.dataset.act = "lancer";
    pied.append(go);
    boite.append(tete, corps, pied);
    ui = { tete, titre, lieu, ligneCalque, selCalque, prompt, ligneModele, selModele, ligneCase, caseDetour, ligneDetour, selDetour, sujet, prix, etat, go };

    boite.addEventListener("click", (ev) => {
      const b = ev.target && ev.target.closest ? ev.target.closest("button") : null;
      const act = b ? b.dataset.act : (ev.target && ev.target.dataset ? ev.target.dataset.act : null);
      if (act === "fermer") fermer();
      else if (act === "lancer") tirer();
    });
    selCalque.addEventListener("change", () => { cible = Number(selCalque.value); majLieu(); majBouton(); });
    caseDetour.addEventListener("change", () => { majSujet(); majDevis(); });
    selModele.addEventListener("change", () => { ecrire("dz_pl_iac_modele", selModele.value); majDevis(); });
    selDetour.addEventListener("change", () => { ecrire("dz_pl_iac_detour", selDetour.value); majSujet(); majDevis(); });
    boite.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") { ev.preventDefault(); fermer(); }
      else if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); tirer(); }
    });
    // déplaçable par la tête (borné à la fenêtre), comme les dialogues de réglage
    let glisse = null;
    tete.addEventListener("pointerdown", (ev) => {
      if (ev.button !== 0 || (ev.target && ev.target.closest && ev.target.closest("button"))) return;
      const r = boite.getBoundingClientRect();
      glisse = { dx: ev.clientX - r.left, dy: ev.clientY - r.top };
      try { tete.setPointerCapture(ev.pointerId); } catch (e) { /* pointeur déjà relâché */ }
    });
    tete.addEventListener("pointermove", (ev) => {
      if (!glisse) return;
      const p = bornerPosition(ev.clientX - glisse.dx, ev.clientY - glisse.dy, { w: boite.offsetWidth, h: boite.offsetHeight },
        { w: window.innerWidth, h: window.innerHeight });
      boite.style.left = p.x + "px"; boite.style.top = p.y + "px";
    });
    const fin = () => { glisse = null; };
    tete.addEventListener("pointerup", fin);
    tete.addEventListener("pointercancel", fin);
    C.garderGestes(boite);
  }

  const choix = () => ({
    mode, auDessusDe: cible, calque: cible, taille: taillePour(PL.etat.doc),
    // t159 : Paramètres › « redimensionner pendant le placement » (vraie par défaut)
    reduire: !(PL.prefs && PL.prefs.p && PL.prefs.p.general && PL.prefs.p.general.resizeImageDuringPlace === false),
    prompt: ui.prompt.value || "", modele: ui.selModele.value || "",
    detourer: mode === "detour" || !!ui.caseDetour.checked, modeleDetour: ui.selDetour.value || "", sujet: ui.sujet.value || "",
  });
  const dire = (t) => { if (ui) ui.etat.textContent = t; };

  function majLieu() {
    ui.lieu.textContent = cible == null ? T("photolab.iacalque.aucun_calque_libre")
      : T(mode === "detour" ? "photolab.iacalque.lieu_detour" : "photolab.iacalque.lieu", { calque: nomCalque(cible) });
  }
  function majBouton() {
    if (!ui) return;
    ui.go.textContent = lancer.enVol ? T("photolab.iacalque.en_cours")
      : T(mode === "detour" ? "photolab.iacalque.detourer_go" : "photolab.iacalque.generer_go");
    ui.go.disabled = lancer.enVol || cible == null;      // jamais pour une clé manquante : le refus vient au lancement
  }
  function majSujet() {
    const c = choix();
    ui.ligneDetour.hidden = !c.detourer;
    ui.sujet.hidden = !(c.detourer && infoDe(modsDetour, c.modeleDetour) && infoDe(modsDetour, c.modeleDetour).prompt);
  }
  async function majDevis() {
    const n = ++devisN;
    ui.prix.textContent = T("photolab.iacalque.prix_inconnu");
    const corps = devisCorps(choix());
    if (!corps || !corps.ops.length) return;             // aucun modèle : « Prix estimé : … », jamais un prix faux
    try {
      const r = await window.fetch("/api/cost/estimate", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corps), cache: "no-store" });
      const d = await r.json().catch(() => null);
      if (n === devisN) ui.prix.textContent = r.ok ? libellePrix(d) : T("photolab.iacalque.prix_inconnu");
    } catch (e) {
      if (n === devisN) ui.prix.textContent = T("photolab.iacalque.prix_inconnu");
    }
  }

  function remplirCalques() {
    const cibles = calquesCibles(PL.etat.doc, PL.etat.verrous, mode);
    if (!cibles.some((c) => c.id === cible)) cible = cibles.length ? cibles[0].id : null;
    ui.selCalque.textContent = "";
    for (const c of cibles) {
      const o = el("option", "", c.nom); o.value = String(c.id);
      o.setAttribute("data-dz-brut", "1");                 // un nom de calque est une donnée de l'utilisateur
      ui.selCalque.appendChild(o);
    }
    ui.selCalque.value = cible == null ? "" : String(cible);
  }

  function preparer(m, calqueId) {
    if (!boite) construire();
    mode = m;
    boite.classList.toggle("mode-detour", mode === "detour");
    ui.go.id = mode === "detour" ? "pl-iac-detourer" : "pl-iac-generer";   // t193 : la fiche du détourage vise ce bouton
    ui.titre.textContent = T(mode === "detour" ? "photolab.iacalque.titre_detour" : "photolab.iacalque.titre");
    const cibles = calquesCibles(PL.etat.doc, PL.etat.verrous, mode);
    cible = cibles.some((c) => c.id === calqueId) ? calqueId : (cibles[0] ? cibles[0].id : null);
    if (calqueId != null && cible !== calqueId) {
      try { verifierCible(PL.etat.doc, PL.etat.verrous, calqueId, mode); } catch (e) { PL.signaler(e.message, true); }
    }
    remplirCalques();
    ui.prompt.hidden = ui.ligneModele.hidden = ui.ligneCase.hidden = mode === "detour";
    ui.caseDetour.checked = false;
    dire("");
    majLieu(); majSujet(); majBouton();
    const M = MI();
    if (!M) { dire(T("photolab.iacalque.catalogue_absent")); return; }
    if (mode !== "detour") {
      catalogue("image").then((l) => { M.remplir(ui.selModele, l, { valeur: lire("dz_pl_iac_modele") }); majDevis(); })
        .catch(() => dire(T("photolab.iacalque.catalogue_absent")));
    }
    catalogue("detourage_image").then((l) => {
      modsDetour = l;
      M.remplir(ui.selDetour, l, { valeur: lire("dz_pl_iac_detour") });
      majSujet(); majDevis();
    }).catch(() => { /* sans liste : le tir refusera (aucun modèle), sans dépense */ });
    majDevis();
  }

  function ouvrir(m, calqueId) {
    if (!PL.etat.doc) { PL.signaler(T("photolab.iacalque.aucun_document"), true); return; }
    const premiere = !boite || !boite.parentNode;
    if (premiere) retour = document.activeElement && document.activeElement !== document.body ? document.activeElement : null;
    preparer(m, calqueId == null ? PL.etat.doc.activeLayer : calqueId);
    if (premiere) {
      document.body.appendChild(boite);
      const scene = PL.$ ? PL.$("#scene") : null;
      const rs = scene && scene.getBoundingClientRect ? scene.getBoundingClientRect() : null;
      const pos = positionInitiale(rs ? { left: rs.left, top: rs.top, width: rs.width, height: rs.height } : null,
        { w: boite.offsetWidth, h: boite.offsetHeight });
      const b = bornerPosition(pos.x, pos.y, { w: boite.offsetWidth, h: boite.offsetHeight },
        { w: window.innerWidth || 1280, h: window.innerHeight || 800 });
      boite.style.left = b.x + "px"; boite.style.top = b.y + "px";
    }
    if (mode === "detour") ui.go.focus(); else ui.prompt.focus();
  }
  function fermer() {
    if (!boite || !boite.parentNode) return;
    boite.remove();
    if (retour && retour.isConnected && typeof retour.focus === "function") retour.focus();
    retour = null;
  }

  async function tirer() {
    if (lancer.enVol) return;                            // anti-double tir : le second clic ne relance rien
    const c = choix();
    try {                                                // refus GRATUITS, avant tout POST
      verifierCible(PL.etat.doc, PL.etat.verrous, cible, mode);
      if (mode === "detour") requeteDetour(c); else requete(c);
      verifierDetour(c, infoDe(modsDetour, c.modeleDetour));
    } catch (e) { dire(e.message); PL.signaler(e.message, true); return; }
    const avant = nomCalque(cible);
    const p = lancer(c);
    majBouton();
    dire(T(mode === "detour" ? "photolab.iacalque.detour_en_cours" : "photolab.iacalque.en_cours"));
    try {
      const r = await p;
      if (!r) return;
      let t;
      if (mode === "detour") t = T("photolab.iacalque.detour_fait", { calque: avant });
      else if (r.detourEchec) t = T("photolab.iacalque.detour_echoue_pose", { raison: r.detourEchec, calque: avant });
      else t = T("photolab.iacalque.posee", { nom: r.nom || nomCalqueIa(c.prompt), calque: avant });
      if (mode !== "detour" && r.reduite) t += " " + T("photolab.iacalque.reduite");
      dire(t); PL.signaler(t, !!r.detourEchec);
      remplirCalques(); majLieu();
    } catch (e) {
      dire(e.message); PL.signaler(e.message, true);
    }
    majBouton();
  }

  PL.iaCalque = {
    ouvrir: (calqueId) => ouvrir("ia", calqueId),
    retirerFond: (calqueId) => ouvrir("detour", calqueId),
    fermer, lancer, get boite() { return boite; }, get ui() { return ui; },
    requete, requeteDetour, verifierCible, taillePour,
  };
  PL.actions = PL.actions || {};
  PL.actions["pl.calque.ia"] = () => ouvrir("ia");
  PL.actions["pl.calque.detourer"] = () => ouvrir("detour");
  // le document a changé (calque supprimé, verrouillé, autre document) : la liste des cibles suit
  if (Array.isArray(PL.surDoc)) PL.surDoc.push((doc) => { if (!boite || !boite.parentNode) return; if (!doc) { fermer(); return; } remplirCalques(); majLieu(); majBouton(); });
}
