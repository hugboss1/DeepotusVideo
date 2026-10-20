// mod-actions.js — t255 (Photolab M6, photocraft 0.10) : le panneau Actions (onglet du groupe Calques, Fenêtre ›
// Actions, Alt+F9) et Fichier › Automatisation › Traitement par lots.
// Le MOTEUR enregistre, rejoue et édite les actions (actions.*) ; le pont (photolab_actions) vérifie chaque lecture en
// profondeur, éteint les étapes qu'il refuse, garde les actions entre deux démarrages (réserve) et sert l'échange .atn
// en DONNÉES (base64, jamais un chemin). L'écran : la liste (jeux, actions, étapes ; case allumée, bascule de dialogue),
// le pied (Arrêter, Enregistrer, Jouer, Nouveau jeu, Nouvelle action, Supprimer), le menu du panneau, le mode Bouton, les
// dialogues (Nouvelle action, Options, Insérer un arrêt / une condition / un élément de menu, Modifier l'étape) et la
// LECTURE PAS À PAS : le moteur joue sans interface ; une étape dont le dialogue est allumé, ou un Arrêt, coupe la
// lecture en segments (actions.play `until`, clé du pont) et l'écran ouvre le dialogue de la commande (valeurs
// enregistrées) ou montre le message. Fonctions PURES exportées (qa/actions-m6.test.mjs).
import { ouvrirDialogue } from "./mod-fichier.js";
import { demanderNom, nomValide } from "./mod-nommer.js";
import { champsVisibles } from "./mod-champs.js";
import { REFUSES, TRAITES_PAR_ECRAN } from "./mod-menus.js";

export const COULEURS = ["", "red", "orange", "yellow", "green", "blue", "violet", "gray"];
export const cleCouleur = (c) => "photolab.actions.couleur." + (c || "aucune");
// Conditions de actions.conditional (copie de photolab_registre.CONDITIONS_ACTION — banc actions-m6 qui relit le source).
export const CONDITIONS = ["always", "never", "isOpen", "landscape", "square", "portrait", "modeIsRGB", "modeIsCMYK",
  "modeIsGrayscale", "modeIsLab", "modeIsBitmap", "modeIsIndexed", "modeIsDuotone", "modeIsMultichannel",
  "depth8", "depth16", "depth32", "unsaved", "hasSelection", "hasLayers", "hasAlphaChannels",
  "isBackground", "isPixelLayer", "isAdjustmentLayer", "isShapeLayer", "isTypeLayer", "isSmartObject",
  "isLayerGroup", "isLocked", "isVisible", "hasPixelMask", "hasVectorMask", "hasEffects"];
export const cleCondition = (c) => "photolab.actions.condition." + c.replace(/[A-Z0-9]/g, (x) => "_" + x.toLowerCase());
export const MAX_NOM = 128;                  // photolab_registre.MAX_NOM_ACTION
export const MAX_MESSAGE = 512;              // photolab_registre.MAX_MESSAGE_ARRET
export const MAX_OCTETS_ATN = 2_000_000;     // photolab_registre.MAX_OCTETS_ATN
export const ARRET = "actions.stopMessage", JOUER = "actions.play", CONDITION = "actions.conditional", ETAPE_PS = "actions.photoshopStep";

// GET /actions -> l'arbre du panneau, dans l'ordre du moteur : un jeu apparaît à la place de sa première action et
// regroupe les siennes ; une action sans jeu reste à sa place. Les jeux vides de l'écran (Nouveau jeu…, pas encore de
// moteur) suivent. Une action : {nom, index, jeu, couleur, etapes: [{index, id, params, allumee, dialogue}], allumage:
// "plein" | "partiel" | "vide", dialogues: "plein" | "partiel" | "vide", enregistre}.
export function arbreActions(r, jeuxVides = []) {
  const acts = (r && Array.isArray(r.actions)) ? r.actions : [];
  const rec = r ? r.recording : null;
  const racine = [], jeux = new Map();
  acts.forEach((a, index) => {
    const eteintes = new Set(a.disabled || []), dlg = new Set(a.dialogs || []);
    const etapes = (a.steps || []).map(([id, params], i) => ({ index: i, id, params: params || {}, allumee: !eteintes.has(i), dialogue: dlg.has(i) }));
    const n = etapes.length, on = etapes.filter((e) => e.allumee).length, d = etapes.filter((e) => e.dialogue).length;
    const noeud = { type: "action", nom: a.name, index, jeu: a.set == null ? null : a.set, couleur: a.color || "", etapes,
      allumage: !n || on === n ? "plein" : on ? "partiel" : "vide", dialogues: d === 0 ? "vide" : d === n ? "plein" : "partiel",
      enregistre: rec != null && rec === a.name };
    if (noeud.jeu == null) { racine.push(noeud); return; }
    if (!jeux.has(noeud.jeu)) { const j = { type: "jeu", nom: noeud.jeu, actions: [] }; jeux.set(noeud.jeu, j); racine.push(j); }
    jeux.get(noeud.jeu).actions.push(noeud);
  });
  for (const v of jeuxVides) if (!jeux.has(v)) { const j = { type: "jeu", nom: v, actions: [], vide: true }; jeux.set(v, j); racine.push(j); }
  return racine;
}
export const actionsDe = (arbre) => arbre.flatMap((n) => (n.type === "jeu" ? n.actions : [n]));
export const jeuxDe = (arbre) => arbre.filter((n) => n.type === "jeu").map((n) => n.nom);

// Libellé d'une étape : les quatre étapes propres aux actions par le dictionnaire ; sinon le libellé du catalogue des
// menus dans la langue (sans « … ») ; sinon l'id du moteur tel quel (brut : jamais traduit).
export function libelleEtape(etape, catalogue, lang = "fr", t = (c) => c) {
  const p = etape.params || {};
  if (etape.id === JOUER) return { texte: t("photolab.actions.etape_jouer", { nom: String(p.action) }) };
  if (etape.id === ARRET) return { texte: t("photolab.actions.etape_arret") };
  if (etape.id === CONDITION) return { texte: t("photolab.actions.etape_condition", { si: t(cleCondition(String(p.if))) }) };
  if (etape.id === ETAPE_PS) return { texte: String(p.name || p.event || "?"), brut: true, sansEquivalent: true };
  const e = catalogue && catalogue.get ? catalogue.get(etape.id) : null;
  if (e) return { texte: String((lang === "en" ? e.libelle_en : e.libelle_fr) || e.libelle_fr || etape.id).replace(/…$/, "").trim() };
  return { texte: etape.id, brut: true };
}
// Index id -> entrée du catalogue (donnees/menus.json).
export function indexCatalogue(c) {
  const m = new Map();
  for (const e of (c && c.entrees) || []) if (e.id && !m.has(e.id)) m.set(e.id, e);
  return m;
}
// Détail d'une étape dépliée : « clé : valeur » (objets en JSON compact, coupés à 80 caractères ; valeurs nulles tues).
export function detailsEtape(params) {
  return Object.entries(params || {}).filter(([k, v]) => k !== "coalesce" && v != null).map(([k, v]) => {
    let s = typeof v === "string" ? v : JSON.stringify(v);
    if (s.length > 80) s = s.slice(0, 79) + "…";
    return k + " : " + s;
  });
}

// Lecture d'une action depuis l'étape `depuis` -> opérations : des segments joués par le moteur ({segment, from, until},
// until null = jusqu'au bout) coupés aux étapes allumées où l'écran doit agir : un Arrêt ({arret, step, message,
// continuer}) ou une étape au dialogue allumé dont la commande a un formulaire ({dialogue, step}). Sans point : un seul
// segment (une seule lecture du moteur).
export function planLecture(action, depuis = 0, aDialogue = () => false) {
  const ops = [];
  let pos = Math.max(0, depuis | 0);
  for (const e of (action && action.etapes) || []) {
    if (e.index < pos || !e.allumee) continue;
    const arret = e.id === ARRET, dlg = e.dialogue && aDialogue(e.id);
    if (!arret && !dlg) continue;
    if (e.index > pos) ops.push({ type: "segment", from: pos, until: e.index });
    ops.push(arret ? { type: "arret", step: e.index, message: String(e.params.message || ""), continuer: !!e.params.allowContinue }
      : { type: "dialogue", step: e.index });
    pos = e.index + 1;
  }
  const n = ((action && action.etapes) || []).length;
  if (pos < n || !ops.length) ops.push({ type: "segment", from: pos, until: null });
  return ops;
}
export const paramsSegment = (nom, op) => (op.until == null ? (op.from ? { action: nom, from: op.from } : { action: nom })
  : { action: nom, from: op.from, until: op.until });

// Nom d'une copie : « <nom> copie », puis « <nom> copie 2 »… (suffixe du dictionnaire), borné à MAX_NOM.
export function nomCopie(nom, existants, suffixe = "copie") {
  const pris = new Set(existants);
  const base = String(nom).slice(0, MAX_NOM - suffixe.length - 5);
  let n = base + " " + suffixe;
  for (let k = 2; pris.has(n); k++) n = base + " " + suffixe + " " + k;
  return n;
}
// Nom libre pour « Action N » (Nouvelle action).
export function nomNouvelle(existants, gabarit = (n) => "Action " + n) {
  const pris = new Set(existants);
  for (let k = 1; ; k++) if (!pris.has(gabarit(k))) return gabarit(k);
}
// Fichier .atn téléchargé : le nom du jeu (ou de l'action) sans caractères interdits.
export function nomFichierAtn(nom) {
  const s = String(nom || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/[^A-Za-z0-9 _-]+/g, "-").trim().replace(/\s+/g, "-").slice(0, 80);
  return (s || "actions") + ".atn";
}
// Octets -> base64 (morceaux : String.fromCharCode(...grand tableau) dépasserait la pile).
export function versBase64(octets) {
  let s = "";
  for (let i = 0; i < octets.length; i += 0x8000) s += String.fromCharCode.apply(null, octets.subarray(i, i + 0x8000));
  return btoa(s);
}
export function depuisBase64(b64) {
  const s = atob(String(b64 || ""));
  const o = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) o[i] = s.charCodeAt(i);
  return o;
}
// Un fichier choisi -> {erreur: clé} ou {ok: true} (taille, extension ; le contenu est jugé par le moteur).
export function controleAtn(nom, taille) {
  if (!/\.atn$/i.test(String(nom || ""))) return { erreur: "photolab.actions.atn_extension" };
  if (!(taille > 0) || taille > MAX_OCTETS_ATN) return { erreur: "photolab.actions.atn_taille" };
  return { ok: true };
}

// Message d'un Arrêt saisi -> le texte propre ou null.
export function messageValide(brut) {
  const m = String(brut == null ? "" : brut).trim();
  return m && m.length <= MAX_MESSAGE && ![...m].some((c) => c.charCodeAt(0) < 32 && c !== "\n" && c !== "\t") ? m : null;
}

// Rang d'insertion (Insérer un arrêt / une condition / un élément de menu) : après l'étape choisie, sinon à la fin.
export function rangInsertion(sel, action) {
  if (!action) return null;
  if (sel && sel.action === action.nom && Number.isInteger(sel.step)) return sel.step + 1;
  return action.etapes.length;
}
// Déplacement d'un cran (Monter / Descendre) : la cible ou null (bord).
export function deplacement(index, sens, longueur) {
  const to = index + sens;
  return to < 0 || to >= longueur ? null : to;
}

// Commandes proposées par « Insérer un élément de menu » : celles du catalogue que le moteur connaît, que le pont
// ne refuse pas par famille et que l'écran ne sert pas lui-même ; triées par chemin de menu.
export function commandesInserables(catalogue, registre, lang = "fr") {
  const reg = new Map((Array.isArray(registre) ? registre : []).map((r) => [r.id, r]));
  const vus = new Set(), out = [];
  for (const e of (catalogue && catalogue.entrees) || []) {
    if (!e.id || vus.has(e.id) || !reg.has(e.id) || TRAITES_PAR_ECRAN.has(e.id)) continue;
    const low = e.id.toLowerCase();
    if (REFUSES.some((p) => low.startsWith(p)) || e.id.startsWith("actions.")) continue;
    vus.add(e.id);
    const lib = String((lang === "en" ? e.libelle_en : e.libelle_fr) || e.id).replace(/…$/, "").trim();
    const noms = (catalogue && catalogue.menus_fr) || {};
    const chemin = (e.chemin || []).map((m) => (lang === "en" ? m : noms[m] || m));
    out.push({ id: e.id, libelle: lib, chemin: [...chemin, lib].join(" › ") });
  }
  return out.sort((a, b) => a.chemin.localeCompare(b.chemin));
}
export const filtrerCommandes = (liste, q) => {
  const f = String(q || "").trim().toLowerCase();
  return f ? liste.filter((c) => c.chemin.toLowerCase().includes(f) || c.id.toLowerCase().includes(f)) : liste;
};

// Entrées du menu du panneau (≡ du pied et clic droit) -> [{id, cle, actif, coche?} | null (séparateur)].
// e = {sel: {action, step}|{jeu}|null, action: noeud choisi|null, n: nombre d'actions, enregistre, modeBouton, doc}.
export function entreesMenu(e) {
  const a = !!e.action, rec = !!e.enregistre, etape = a && e.sel && Number.isInteger(e.sel.step);
  const it = (id, cle, actif, x = {}) => ({ id, cle, actif: !!actif, ...x });
  return [
    it("bouton", "photolab.actions.menu.mode_bouton", true, { coche: !!e.modeBouton }), null,
    it("nouvelle", "photolab.actions.menu.nouvelle", !rec), it("jeu", "photolab.actions.menu.nouveau_jeu", !rec),
    it("dupliquer", "photolab.actions.menu.dupliquer", a && !rec), it("supprimer", "photolab.actions.menu.supprimer", (a || (e.sel && e.sel.jeu)) && !rec),
    it("jouer", "photolab.actions.menu.jouer", a && !rec), null,
    it("enregistrer", "photolab.actions.menu.commencer", !rec), it("menu", "photolab.actions.menu.inserer_menu", a),
    it("arret", "photolab.actions.menu.inserer_arret", a), it("condition", "photolab.actions.menu.inserer_condition", a), null,
    it("options", "photolab.actions.menu.options", a && !etape && !rec), it("modifier", "photolab.actions.menu.modifier", etape && !rec),
    it("monter", "photolab.actions.menu.monter", a && !rec), it("descendre", "photolab.actions.menu.descendre", a && !rec), null,
    it("effacer", "photolab.actions.menu.effacer", e.n > 0 && !rec), it("charger", "photolab.actions.menu.charger", !rec),
    it("remplacer", "photolab.actions.menu.remplacer", !rec), it("sauver", "photolab.actions.menu.sauver", e.n > 0 && !rec), null,
    it("lot", "photolab.actions.menu.lot", e.n > 0 && !rec),
  ];
}

// Traitement par lots : saisie du dialogue -> {erreur: clé} | {action, images, format, quality?, suffixe, continuer}.
export function paramsLot(s) {
  if (!s || s.action == null || s.action === "") return { erreur: "photolab.actions.lot_erreur_action" };
  const images = [...new Set((s.images || []).filter((x) => typeof x === "string" && x))];
  if (!images.length) return { erreur: "photolab.actions.lot_erreur_images" };
  if (images.length > 500) return { erreur: "photolab.actions.lot_erreur_trop" };
  const format = s.format === "jpg" ? "jpg" : "png";
  const suffixe = String(s.suffixe == null ? "" : s.suffixe).trim().slice(0, 40);
  const p = { action: s.action, images, format, suffixe, continuer: !!s.continuer };
  if (format === "jpg") p.quality = Math.max(1, Math.min(100, Math.round(Number(s.quality) || 90)));
  return p;
}
export const corpsLot = (p, filename) => {
  const c = { action: p.action, filename, format: p.format };
  if (p.quality != null) c.quality = p.quality;
  if (p.suffixe) c.suffixe = p.suffixe;
  return c;
};

export function initActions(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const lang = () => (window.dzLang ? window.dzLang() : "fr");
  const corps = PL.$("#corpsActions");
  if (!corps) return;
  const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
  const brut = (e) => { e.setAttribute("data-dz-brut", ""); return e; };
  let donnees = { actions: [], recording: null }, arbre = [], sel = null, lecture = false, arreterLecture = false;
  const ouvertes = new Set(), jeuxReplies = new Set(), jeuxVides = [];
  let catalogue = null, catalogueBrut = null;
  let modeBouton = false;
  try { modeBouton = localStorage.getItem("photolab.actions.modeBouton") === "1"; } catch (e) { /* stockage indisponible */ }
  fetch("donnees/menus.json").then((r) => r.json()).then((c) => { catalogueBrut = c; catalogue = indexCatalogue(c); dessiner(); }).catch(() => {});

  const liste = el("div", "ac-liste"); liste.setAttribute("role", "tree");
  const pied = el("div", "pr-pied ac-pied");
  corps.append(liste, pied);
  const bouton = (icone, cle, fn, cls = "") => {
    const b = el("button", "pr-btn " + cls); b.type = "button"; b.dataset.icone = icone;
    b.title = T(cle); b.setAttribute("aria-label", b.title); b.addEventListener("click", fn); pied.appendChild(b); return b;
  };
  const bMenu = bouton("dz-action-menu", "photolab.actions.menu_panneau", (ev) => ouvrirMenu(ev.currentTarget.getBoundingClientRect().left, ev.currentTarget.getBoundingClientRect().top, true), "gauche");
  const bArreter = bouton("dz-media-arret", "photolab.actions.arreter", arreter);
  const bEnregistrer = bouton("dz-media-rec", "photolab.actions.enregistrer", commencer, "ac-rec");
  const bJouer = bouton("dz-media-lecture", "photolab.actions.jouer", () => jouerChoix());
  const bJeu = bouton("dz-action-nouveau-dossier", "photolab.actions.nouveau_jeu", nouveauJeu);
  const bNouvelle = bouton("dz-action-ajouter", "photolab.actions.nouvelle", nouvelle);
  const bSupprimer = bouton("dz-action-supprimer", "photolab.actions.supprimer", supprimer);
  if (PL.hydraterIcones) PL.hydraterIcones(pied);

  const actionChoisie = () => (sel && sel.action != null ? actionsDe(arbre).find((a) => a.nom === sel.action) || null : null);
  async function cmd(command, params, relireApres = true) {
    let r = null;
    try { r = await PL.post("/executer", { command, params }); } catch (e) { r = null; }       // signalé par mod-api
    if (relireApres) await relire();
    return r;
  }
  async function relire() {
    try { donnees = await PL.get("/actions", true); } catch (e) { /* moteur absent : panneau vide */ }
    arbre = arbreActions(donnees, jeuxVides);
    if (sel && sel.action != null && !actionsDe(arbre).some((a) => a.nom === sel.action)) sel = null;
    dessiner();
  }
  const signalerEteintes = (r) => {
    const n = (r && r.eteintes) ? r.eteintes.length : 0;
    if (n) PL.signaler(T("photolab.actions.eteintes", { n }), true);
  };
  const confirmer = async (question, titre, ok) => {
    const d = window.__dzDialogue;
    if (d) return d.confirmer(question, { titre, ok });
    return (await ouvrirDialogue(PL, { titre, construire({ corps: c }) { c.appendChild(el("p", null, question)); },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: ok, principal: true }] })) === "ok";
  };
  const registre = () => (PL.menus && Array.isArray(PL.menus.registre) ? PL.menus.registre : []);
  const entreeRegistre = (id) => registre().find((r) => r.id === id) || null;
  const aDialogue = (id) => { const r = entreeRegistre(id); return !!(r && champsVisibles(r.champs || []).length); };
  const libelle = (e) => libelleEtape(e, catalogue, lang(), T);

  /* ── dessin ── */
  function caseAllumage(etat, aria, fn) {
    const b = el("button", "ac-case " + etat); b.type = "button"; b.setAttribute("aria-label", aria);
    b.setAttribute("aria-pressed", etat === "plein" ? "true" : etat === "partiel" ? "mixed" : "false");
    if (etat !== "vide") b.innerHTML = PL.icone("dz-action-valider", 12);
    b.addEventListener("click", (ev) => { ev.stopPropagation(); fn(); });
    return b;
  }
  function caseDialogue(etat, aria, fn, possible = true) {
    const b = el("button", "ac-dlg " + etat); b.type = "button"; b.setAttribute("aria-label", aria);
    b.setAttribute("aria-pressed", etat === "plein" ? "true" : etat === "partiel" ? "mixed" : "false");
    if (!possible) { b.disabled = true; b.classList.add("sans"); return b; }
    if (etat !== "vide") b.innerHTML = PL.icone("dz-etat-dialogue", 12);
    b.addEventListener("click", (ev) => { ev.stopPropagation(); fn(); });
    return b;
  }
  function fleche(ouvert, fn) {
    const f = el("button", "pr-fleche ac-fleche" + (ouvert ? "" : " pl-replie")); f.type = "button"; f.innerHTML = PL.icone("dz-action-deplier");
    f.setAttribute("aria-label", T(ouvert ? "photolab.presets.replier" : "photolab.presets.deplier"));
    f.addEventListener("click", (ev) => { ev.stopPropagation(); fn(); });
    return f;
  }
  function ligneAction(a, profondeur) {
    const row = el("div", "ac-ligne ac-action" + (sel && sel.action === a.nom && !Number.isInteger(sel.step) ? " choisie" : "") + (a.enregistre ? " enregistre" : ""));
    row.style.setProperty("--ac-retrait", profondeur * 14 + "px");
    row.setAttribute("role", "treeitem"); row.dataset.action = a.nom; row.draggable = !donnees.recording;
    const tout = a.allumage !== "plein";
    row.append(caseAllumage(a.allumage, T("photolab.actions.allumer_action"), () => cmd("actions.toggle", { action: a.nom, enabled: tout })),
      caseDialogue(a.dialogues, T("photolab.actions.dialogues_action"), () => cmd("actions.dialog", { action: a.nom, enabled: a.dialogues !== "plein" }), a.etapes.length > 0),
      fleche(ouvertes.has(a.nom), () => { if (ouvertes.has(a.nom)) ouvertes.delete(a.nom); else ouvertes.add(a.nom); dessiner(); }));
    if (a.couleur) { const p = el("span", "ac-pastille ac-c-" + a.couleur); p.title = T(cleCouleur(a.couleur)); row.appendChild(p); }
    const nom = brut(el("span", "ac-nom", a.nom));
    row.appendChild(nom);
    if (a.enregistre) { const r = el("span", "ac-rec-marque"); r.innerHTML = PL.icone("dz-media-rec", 12); r.title = T("photolab.actions.en_cours"); row.appendChild(r); }
    row.addEventListener("click", () => { sel = { action: a.nom }; dessiner(); });
    row.addEventListener("dblclick", () => { sel = { action: a.nom }; optionsAction(); });
    row.addEventListener("contextmenu", (ev) => { ev.preventDefault(); sel = { action: a.nom }; dessiner(); ouvrirMenu(ev.clientX, ev.clientY); });
    glisser(row, { action: a.nom });
    liste.appendChild(row);
    if (!ouvertes.has(a.nom)) return;
    for (const e of a.etapes) {
      const r = el("div", "ac-ligne ac-etape" + (sel && sel.action === a.nom && sel.step === e.index ? " choisie" : "") + (e.allumee ? "" : " eteinte"));
      r.style.setProperty("--ac-retrait", (profondeur + 1) * 14 + 14 + "px");
      r.setAttribute("role", "treeitem"); r.dataset.action = a.nom; r.dataset.step = String(e.index); r.draggable = !donnees.recording;
      const lib = libelle(e);
      const possible = aDialogue(e.id);
      r.append(caseAllumage(e.allumee ? "plein" : "vide", T("photolab.actions.allumer_etape"), () => cmd("actions.toggle", { action: a.nom, step: e.index, enabled: !e.allumee })),
        caseDialogue(e.dialogue ? "plein" : "vide", T("photolab.actions.dialogue_etape"), () => cmd("actions.dialog", { action: a.nom, step: e.index, enabled: !e.dialogue }), possible));
      const n = el("span", "ac-nom", lib.texte);
      if (lib.brut) brut(n);
      if (lib.sansEquivalent) { r.classList.add("sans-equivalent"); n.title = T("photolab.actions.sans_equivalent_etape"); }
      const det = detailsEtape(e.id === ARRET ? { message: e.params.message } : e.id === ETAPE_PS ? {}
        : e.id === CONDITION ? { then: e.params.then, else: e.params.else } : e.params);
      if (det.length) n.title = (n.title ? n.title + "\n" : "") + det.join("\n");
      r.appendChild(n);
      if (det.length && e.id !== JOUER) { const d = brut(el("span", "ac-details", det.join(" · "))); r.appendChild(d); }
      r.addEventListener("click", () => { sel = { action: a.nom, step: e.index }; dessiner(); });
      r.addEventListener("dblclick", () => { sel = { action: a.nom, step: e.index }; modifierEtape(); });
      r.addEventListener("contextmenu", (ev) => { ev.preventDefault(); sel = { action: a.nom, step: e.index }; dessiner(); ouvrirMenu(ev.clientX, ev.clientY); });
      glisser(r, { action: a.nom, step: e.index });
      liste.appendChild(r);
    }
  }
  function dessiner() {
    liste.textContent = "";
    liste.classList.toggle("mode-bouton", modeBouton);
    const rec = donnees.recording;
    if (modeBouton) {
      for (const a of actionsDe(arbre)) {
        const b = brut(el("button", "ac-bouton" + (a.couleur ? " ac-c-" + a.couleur : ""), a.nom)); b.type = "button";
        b.disabled = !!rec || lecture; b.addEventListener("click", () => jouer(a.nom, 0));
        liste.appendChild(b);
      }
      if (!arbre.length) liste.appendChild(el("p", "ac-vide", T("photolab.actions.vide")));
    } else {
      for (const n of arbre) {
        if (n.type === "action") { ligneAction(n, 0); continue; }
        const row = el("div", "ac-ligne ac-jeu" + (sel && sel.jeu === n.nom ? " choisie" : ""));
        row.setAttribute("role", "treeitem"); row.style.setProperty("--ac-retrait", "0px");
        const on = n.actions.length ? (n.actions.every((a) => a.allumage === "plein") ? "plein" : n.actions.some((a) => a.allumage !== "vide") ? "partiel" : "vide") : "plein";
        row.append(caseAllumage(on, T("photolab.actions.allumer_jeu"), async () => { for (const a of n.actions) await cmd("actions.toggle", { action: a.nom, enabled: on !== "plein" }, false); relire(); }),
          caseDialogue("vide", "", () => {}, false),
          fleche(!jeuxReplies.has(n.nom), () => { if (jeuxReplies.has(n.nom)) jeuxReplies.delete(n.nom); else jeuxReplies.add(n.nom); dessiner(); }));
        const ic = el("span", "ac-dossier"); ic.innerHTML = PL.icone("dz-nav-bibliotheque", 14); row.appendChild(ic);
        row.appendChild(brut(el("span", "ac-nom", n.nom)));
        row.addEventListener("click", () => { sel = { jeu: n.nom }; dessiner(); });
        row.addEventListener("dblclick", () => { sel = { jeu: n.nom }; renommerJeu(n); });
        row.addEventListener("contextmenu", (ev) => { ev.preventDefault(); sel = { jeu: n.nom }; dessiner(); ouvrirMenu(ev.clientX, ev.clientY); });
        liste.appendChild(row);
        if (!jeuxReplies.has(n.nom)) for (const a of n.actions) ligneAction(a, 1);
      }
      if (!arbre.length) liste.appendChild(el("p", "ac-vide", T("photolab.actions.vide")));
    }
    const a = actionChoisie();
    bArreter.disabled = !rec && !lecture;
    bEnregistrer.disabled = !!rec || lecture;
    bEnregistrer.classList.toggle("actif", !!rec);
    bJouer.disabled = !a || !!rec || lecture;
    bNouvelle.disabled = bJeu.disabled = !!rec || lecture;
    bSupprimer.disabled = !!rec || lecture || !(a || (sel && sel.jeu));
    bMenu.disabled = false;
    corps.classList.toggle("enregistre", !!rec);
  }

  /* ── glisser-déposer : une action parmi les actions, une étape dans son action (actions.move) ── */
  let glisse = null;
  function glisser(row, quoi) {
    row.addEventListener("dragstart", (ev) => { glisse = quoi; ev.dataTransfer.effectAllowed = "move"; try { ev.dataTransfer.setData("text/plain", quoi.action); } catch (e) { /* */ } });
    row.addEventListener("dragover", (ev) => { if (glisse && cibleDepot(glisse, quoi) != null) { ev.preventDefault(); row.classList.add("depot"); } });
    row.addEventListener("dragleave", () => row.classList.remove("depot"));
    row.addEventListener("drop", (ev) => {
      ev.preventDefault(); row.classList.remove("depot");
      const to = glisse ? cibleDepot(glisse, quoi) : null; const g = glisse; glisse = null;
      if (to == null) return;
      if (Number.isInteger(g.step)) { sel = { action: g.action, step: to }; cmd("actions.move", { action: g.action, step: g.step, to }); }
      else cmd("actions.move", { action: g.action, to });
    });
    row.addEventListener("dragend", () => { glisse = null; });
  }
  function cibleDepot(g, cible) {
    if (Number.isInteger(g.step)) return cible.action === g.action && Number.isInteger(cible.step) && cible.step !== g.step ? cible.step : null;
    if (Number.isInteger(cible.step)) return null;
    const a = actionsDe(arbre).find((x) => x.nom === cible.action);
    return a && cible.action !== g.action ? a.index : null;
  }

  /* ── pied et menu ── */
  async function commencer() {
    const a = actionChoisie();
    if (a) { await cmd("actions.record", { action: a.nom }); PL.signaler(T("photolab.actions.enregistrement", { nom: a.nom })); return; }
    nouvelle();
  }
  async function arreter() {
    if (lecture) { arreterLecture = true; return; }
    if (!donnees.recording) return;
    const r = await cmd("actions.stop", {});
    if (r) { PL.signaler(T("photolab.actions.arrete", { nom: r.action, n: r.steps })); signalerEteintes(r); ouvertes.add(r.action); dessiner(); }
  }
  function jouerChoix() {
    const a = actionChoisie();
    if (!a) return;
    jouer(a.nom, sel && Number.isInteger(sel.step) ? sel.step : 0);
  }
  async function supprimer() {
    const a = actionChoisie();
    if (a && sel && Number.isInteger(sel.step)) {
      const i = sel.step; sel = { action: a.nom, step: Math.max(0, i - 1) };
      if (!(await confirmer(T("photolab.actions.supprimer_etape_q", { nom: libelle(a.etapes[i] || { id: "", params: {} }).texte }), T("photolab.actions.supprimer"), T("commun.action.supprimer")))) return;
      await cmd("actions.delete", { action: a.nom, step: i });
      if (!a.etapes[i - 1]) sel = { action: a.nom };
      return;
    }
    if (a) {
      if (!(await confirmer(T("photolab.actions.supprimer_action_q", { nom: a.nom }), T("photolab.actions.supprimer"), T("commun.action.supprimer")))) return;
      sel = null; await cmd("actions.delete", { action: a.nom }); return;
    }
    if (sel && sel.jeu) {
      const j = arbre.find((n) => n.type === "jeu" && n.nom === sel.jeu);
      if (!j) return;
      if (j.vide) { jeuxVides.splice(jeuxVides.indexOf(j.nom), 1); sel = null; relire(); return; }
      if (!(await confirmer(T("photolab.actions.supprimer_jeu_q", { nom: j.nom, n: j.actions.length }), T("photolab.actions.supprimer"), T("commun.action.supprimer")))) return;
      sel = null;
      for (const x of j.actions) await cmd("actions.delete", { action: x.nom }, false);
      relire();
    }
  }
  let menuOuvert = null;
  const fermerMenu = () => { if (menuOuvert) { menuOuvert.remove(); menuOuvert = null; } };
  function ouvrirMenu(x, y, auDessus = false) {
    fermerMenu();
    const a = actionChoisie();
    const m = el("div", "menu-panneau ac-menu"); m.setAttribute("role", "menu");
    for (const it of entreesMenu({ sel, action: a, n: actionsDe(arbre).length, enregistre: !!donnees.recording, modeBouton, doc: !!PL.etat.doc })) {
      if (!it) { m.appendChild(el("div", "menu-sep")); continue; }
      const l = el("div", "menu-ligne " + (it.actif ? "actif" : "inactif") + (it.coche != null ? " cochable" : "")); l.dataset.id = it.id;
      l.setAttribute("role", it.coche != null ? "menuitemcheckbox" : "menuitem");
      if (it.coche != null) {
        l.setAttribute("aria-checked", it.coche ? "true" : "false");
        const c = el("span", "menu-coche"); if (it.coche) c.innerHTML = PL.icone("dz-action-valider", 12); l.appendChild(c);
      }
      if (!it.actif) l.setAttribute("aria-disabled", "true");
      l.appendChild(el("span", "menu-lib", T(it.cle)));
      l.addEventListener("pointerenter", () => m.querySelectorAll(".menu-ligne").forEach((z) => z.classList.toggle("survol", z === l)));
      l.addEventListener("click", (ev) => { ev.stopPropagation(); if (!it.actif) return; fermerMenu(); choisirMenu(it.id); });
      m.appendChild(l);
    }
    document.body.appendChild(m);
    m.style.left = Math.max(4, Math.min(x, innerWidth - m.offsetWidth - 4)) + "px";
    m.style.top = Math.max(4, Math.min(auDessus ? y - m.offsetHeight - 2 : y, innerHeight - m.offsetHeight - 4)) + "px";
    menuOuvert = m;
  }
  document.addEventListener("pointerdown", (ev) => { if (menuOuvert && !ev.target.closest(".ac-menu")) fermerMenu(); }, true);
  document.addEventListener("keydown", (ev) => { if (menuOuvert && ev.key === "Escape") { ev.stopPropagation(); fermerMenu(); } }, true);
  function choisirMenu(id) {
    const a = actionChoisie();
    if (id === "bouton") { modeBouton = !modeBouton; try { localStorage.setItem("photolab.actions.modeBouton", modeBouton ? "1" : "0"); } catch (e) { /* */ } dessiner(); }
    else if (id === "nouvelle") nouvelle();
    else if (id === "jeu") nouveauJeu();
    else if (id === "dupliquer") dupliquer();
    else if (id === "supprimer") supprimer();
    else if (id === "jouer") jouerChoix();
    else if (id === "enregistrer") commencer();
    else if (id === "menu") insererMenu();
    else if (id === "arret") dialogueArret();
    else if (id === "condition") dialogueCondition();
    else if (id === "options") optionsAction();
    else if (id === "modifier") modifierEtape();
    else if (id === "monter" || id === "descendre") {
      const sens = id === "monter" ? -1 : 1;
      if (sel && Number.isInteger(sel.step)) {
        const to = deplacement(sel.step, sens, a.etapes.length);
        if (to != null) { const de = sel.step; sel = { action: a.nom, step: to }; cmd("actions.move", { action: a.nom, step: de, to }); }
      } else {
        const to = deplacement(a.index, sens, actionsDe(arbre).length);
        if (to != null) cmd("actions.move", { action: a.nom, to });
      }
    }
    else if (id === "effacer") effacerTout();
    else if (id === "charger") charger(false);
    else if (id === "remplacer") charger(true);
    else if (id === "sauver") sauverAtn();
    else if (id === "lot") traitementParLots();
  }

  /* ── dialogues ── */
  function champ(c, libelleCle, element) {
    const l = el("label", "ac-champ"); l.append(el("span", null, T(libelleCle)), element); c.appendChild(l); return element;
  }
  function selectJeux(valeur) {
    const s = el("select");
    const o0 = el("option", null, T("photolab.actions.sans_jeu")); o0.value = ""; s.appendChild(o0);
    for (const j of jeuxDe(arbre)) { const o = brut(el("option", null, j)); o.value = j; s.appendChild(o); }
    s.value = valeur || "";
    return s;
  }
  function selectCouleurs(valeur) {
    const s = el("select");
    for (const c of COULEURS) { const o = el("option", null, T(cleCouleur(c))); o.value = c; s.appendChild(o); }
    s.value = valeur || "";
    return s;
  }
  // Nouvelle action : nom, jeu, couleur -> l'enregistrement commence.
  async function nouvelle() {
    if (donnees.recording || lecture) return;
    const noms = actionsDe(arbre).map((a) => a.nom);
    const s = { nom: nomNouvelle(noms, (n) => T("photolab.actions.action_n", { n })), jeu: (sel && sel.jeu) || (actionChoisie() || {}).jeu || "", couleur: "" };
    let iNom, sJeu, sCou;
    const role = await ouvrirDialogue(PL, { titre: T("photolab.actions.nouvelle_titre"), classe: "ac-dialogue",
      construire: ({ corps: c }) => {
        iNom = champ(c, "photolab.actions.nom", brut(Object.assign(el("input"), { type: "text", maxLength: MAX_NOM, value: s.nom })));
        sJeu = champ(c, "photolab.actions.jeu", selectJeux(s.jeu));
        sCou = champ(c, "photolab.actions.couleur", selectCouleurs(""));
        setTimeout(() => { iNom.focus(); iNom.select(); }, 0);
        return () => nomValide(iNom.value, MAX_NOM) !== null && !noms.includes(nomValide(iNom.value, MAX_NOM));
      },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("photolab.actions.enregistrer"), principal: true }] });
    if (role !== "ok") return;
    const nom = nomValide(iNom.value, MAX_NOM);
    const r = await cmd("actions.record", { name: nom }, false);
    if (!r) return relire();
    if (sJeu.value) await cmd("actions.assignSet", { action: nom, set: sJeu.value }, false);
    if (sCou.value) await cmd("actions.setColor", { action: nom, color: sCou.value }, false);
    const k = jeuxVides.indexOf(sJeu.value); if (k >= 0) jeuxVides.splice(k, 1);
    sel = { action: nom }; ouvertes.add(nom);
    PL.signaler(T("photolab.actions.enregistrement", { nom }));
    relire();
  }
  async function nouveauJeu() {
    const n = await demanderNom(PL, T("photolab.actions.nouveau_jeu_titre"), nomNouvelle(jeuxDe(arbre), (k) => T("photolab.actions.jeu_n", { n: k })), MAX_NOM);
    if (!n || jeuxDe(arbre).includes(n)) return;
    const a = actionChoisie();
    if (a && !donnees.recording) { await cmd("actions.assignSet", { action: a.nom, set: n }); return; }
    jeuxVides.push(n); sel = { jeu: n }; relire();
  }
  async function renommerJeu(j) {
    const n = await demanderNom(PL, T("commun.action.renommer"), j.nom, MAX_NOM);
    if (!n || n === j.nom) return;
    if (j.vide) { jeuxVides[jeuxVides.indexOf(j.nom)] = n; sel = { jeu: n }; relire(); return; }
    for (const a of j.actions) await cmd("actions.assignSet", { action: a.nom, set: n }, false);
    sel = { jeu: n }; relire();
  }
  async function optionsAction() {
    const a = actionChoisie();
    if (!a || donnees.recording) return;
    const autres = actionsDe(arbre).map((x) => x.nom).filter((x) => x !== a.nom);
    let iNom, sJeu, sCou;
    const role = await ouvrirDialogue(PL, { titre: T("photolab.actions.options_titre"), classe: "ac-dialogue",
      construire: ({ corps: c }) => {
        iNom = champ(c, "photolab.actions.nom", brut(Object.assign(el("input"), { type: "text", maxLength: MAX_NOM, value: a.nom })));
        sJeu = champ(c, "photolab.actions.jeu", selectJeux(a.jeu));
        sCou = champ(c, "photolab.actions.couleur", selectCouleurs(a.couleur));
        setTimeout(() => iNom.focus(), 0);
        return () => { const n = nomValide(iNom.value, MAX_NOM); return n !== null && !autres.includes(n); };
      },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.valider"), principal: true }] });
    if (role !== "ok") return;
    let nom = a.nom;
    const n = nomValide(iNom.value, MAX_NOM);
    if (n !== a.nom && await cmd("actions.rename", { action: a.nom, name: n }, false)) nom = n;
    if ((sJeu.value || null) !== a.jeu) await cmd("actions.assignSet", { action: nom, set: sJeu.value || null }, false);
    if (sCou.value !== a.couleur) await cmd("actions.setColor", { action: nom, color: sCou.value }, false);
    if (ouvertes.delete(a.nom)) ouvertes.add(nom);
    sel = { action: nom }; relire();
  }
  async function dupliquer() {
    const a = actionChoisie();
    if (!a) return;
    const nom = nomCopie(a.nom, actionsDe(arbre).map((x) => x.nom), T("photolab.actions.suffixe_copie"));
    try { await PL.post("/actions/dupliquer", { action: a.nom, name: nom }); sel = { action: nom }; } catch (e) { /* signalé */ }
    relire();
  }
  async function effacerTout() {
    const acts = actionsDe(arbre);
    if (!(await confirmer(T("photolab.actions.effacer_q", { n: acts.length }), T("photolab.actions.menu.effacer"), T("commun.action.supprimer")))) return;
    for (const a of acts) await cmd("actions.delete", { action: a.nom }, false);
    sel = null; jeuxVides.length = 0; relire();
  }
  // Insérer : à la suite de l'étape choisie (ou en fin d'action). `remplacer` : Modifier l'étape (rang de l'étape).
  async function inserer(id, params, remplacer = null) {
    const a = actionChoisie();
    if (!a) return null;
    const at = remplacer != null ? remplacer : rangInsertion(sel, a);
    const p = { action: a.nom, id, params, at };
    if (remplacer != null) p.replace = true;
    const r = await cmd("actions.insert", p);
    if (r) { ouvertes.add(a.nom); sel = { action: a.nom, step: at }; dessiner(); }
    return r;
  }
  function dialogueArret(etape = null) {
    if (!actionChoisie()) return;
    let zone, caseC;
    return ouvrirDialogue(PL, { titre: T("photolab.actions.arret_titre"), classe: "ac-dialogue",
      construire: ({ corps: c }) => {
        zone = champ(c, "photolab.actions.arret_message", brut(Object.assign(el("textarea"), { rows: 4, maxLength: MAX_MESSAGE, value: etape ? etape.params.message || "" : "" })));
        caseC = Object.assign(el("input"), { type: "checkbox", checked: etape ? !!etape.params.allowContinue : false });
        const l = el("label", "ac-case-champ"); l.append(caseC, document.createTextNode(" " + T("photolab.actions.arret_continuer"))); c.appendChild(l);
        setTimeout(() => zone.focus(), 0);
        return () => messageValide(zone.value) !== null;
      },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.valider"), principal: true }] })
      .then((role) => (role === "ok" ? inserer(ARRET, { message: messageValide(zone.value), allowContinue: caseC.checked }, etape ? etape.index : null) : null));
  }
  function dialogueCondition(etape = null) {
    if (!actionChoisie()) return;
    const noms = actionsDe(arbre).map((a) => a.nom);
    let sSi, sAlors, sSinon;
    const choixAction = (v) => {
      const s = el("select"); const o0 = el("option", null, T("photolab.actions.aucune")); o0.value = ""; s.appendChild(o0);
      for (const n of noms) { const o = brut(el("option", null, n)); o.value = n; s.appendChild(o); }
      s.value = v || ""; return s;
    };
    const p0 = etape ? etape.params : {};
    return ouvrirDialogue(PL, { titre: T("photolab.actions.condition_titre"), classe: "ac-dialogue",
      construire: ({ corps: c }) => {
        sSi = el("select");
        for (const k of CONDITIONS) { const o = el("option", null, T(cleCondition(k))); o.value = k; sSi.appendChild(o); }
        sSi.value = p0.if || "isOpen";
        champ(c, "photolab.actions.condition_si", sSi);
        sAlors = champ(c, "photolab.actions.condition_alors", choixAction(p0.then));
        sSinon = champ(c, "photolab.actions.condition_sinon", choixAction(p0.else));
      },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("commun.action.valider"), principal: true }] })
      .then((role) => (role === "ok" ? inserer(CONDITION, { if: sSi.value, then: sAlors.value || null, else: sSinon.value || null }, etape ? etape.index : null) : null));
  }
  // Dialogue d'une commande du registre, sans aperçu : sa validation INSÈRE (ou remplace) l'étape au lieu de l'appliquer.
  function dialogueCommande(id, initiales, remplacer = null) {
    const r = entreeRegistre(id);
    const e = catalogue && catalogue.get(id);
    const lib = e ? String((lang() === "en" ? e.libelle_en : e.libelle_fr) || id).replace(/…$/, "") : id;
    if (!r || !champsVisibles(r.champs || []).length) return inserer(id, initiales || {}, remplacer);
    return new Promise((res) => PL.ouvrirReglage({ id, libelle: lib, champs: r.champs }, {
      initiales: initiales || undefined, apercu: false,
      valider: async (c) => ({ ok: !!(await inserer(c.command, c.params, remplacer)) }),
      apres: (role, x) => res(role === "ok" ? x : null),
    }));
  }
  function insererMenu() {
    const a = actionChoisie();
    if (!a) return;
    const toutes = commandesInserables(catalogueBrut, registre(), lang());
    let choisie = null;
    ouvrirDialogue(PL, { titre: T("photolab.actions.menu_titre"), classe: "large ac-dlg-menu",
      construire: ({ corps: c, fermer }) => {
        const q = Object.assign(el("input"), { type: "search", placeholder: T("commun.action.rechercher") }); q.className = "lib-recherche";
        const l = el("div", "ac-cmd-liste"); l.setAttribute("role", "listbox");
        c.append(el("p", "ac-aide", T("photolab.actions.menu_aide")), q, l);
        const peindre = () => {
          l.textContent = "";
          const vues = filtrerCommandes(toutes, q.value).slice(0, 300);
          if (!vues.length) l.appendChild(el("p", "ac-vide", T("commun.etat.aucun_resultat")));
          for (const x of vues) {
            const b = el("button", "ac-cmd", x.chemin); b.type = "button"; b.setAttribute("role", "option"); b.dataset.id = x.id;
            b.addEventListener("click", () => { choisie = x.id; fermer("ok"); });
            l.appendChild(b);
          }
        };
        q.addEventListener("input", peindre); peindre(); setTimeout(() => q.focus(), 0);
      },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }] })
      .then((role) => { if (role === "ok" && choisie) dialogueCommande(choisie, null); });
  }
  function modifierEtape() {
    const a = actionChoisie();
    if (!a || !sel || !Number.isInteger(sel.step) || donnees.recording) return;
    const e = a.etapes[sel.step];
    if (!e) return;
    if (e.id === ARRET) return dialogueArret(e);
    if (e.id === CONDITION) return dialogueCondition(e);
    if (e.id === JOUER || e.id === ETAPE_PS || !aDialogue(e.id)) { PL.signaler(T("photolab.actions.rien_a_regler")); return; }
    return dialogueCommande(e.id, e.params, e.index);
  }

  /* ── .atn : charger / remplacer / enregistrer (en DONNÉES) ── */
  const fichierAtn = Object.assign(el("input"), { type: "file", accept: ".atn" }); fichierAtn.hidden = true; corps.appendChild(fichierAtn);
  let remplacerAuChargement = false;
  function charger(remplacer) { remplacerAuChargement = remplacer; fichierAtn.value = ""; fichierAtn.click(); }
  fichierAtn.addEventListener("change", async () => {
    const f = fichierAtn.files && fichierAtn.files[0];
    if (!f) return;
    const c = controleAtn(f.name, f.size);
    if (c.erreur) { PL.signaler(T(c.erreur), true); return; }
    const data = versBase64(new Uint8Array(await f.arrayBuffer()));
    if (remplacerAuChargement) {
      const acts = actionsDe(arbre);
      if (acts.length && !(await confirmer(T("photolab.actions.remplacer_q", { n: acts.length }), T("photolab.actions.menu.remplacer"), T("photolab.actions.menu.remplacer")))) return;
      for (const a of acts) await cmd("actions.delete", { action: a.nom }, false);
    }
    // Charger AJOUTE (un jeu du même nom n'est pas écrasé : le moteur renomme) ; Remplacer a tout effacé avant
    const r = await cmd("actions.load", { data, replace: false });
    if (!r) return;
    PL.signaler(T("photolab.actions.charge", { n: (r.actions || []).length, jeu: r.set || "" }));
    if ((r.unsupported || []).length) PL.signaler(T("photolab.actions.sans_equivalent", { n: r.unsupported.length }), true);
    signalerEteintes(r);
    for (const n of r.actions || []) ouvertes.delete(n);
  });
  async function sauverAtn() {
    const a = actionChoisie();
    const jeu = (sel && sel.jeu) || (a && a.jeu) || null;
    const params = jeu ? { set: jeu, skipUnsupported: true } : a ? { action: a.nom, skipUnsupported: true } : { skipUnsupported: true };
    const r = await cmd("actions.save", params, false);
    if (!r || !r.data) return;
    const url = URL.createObjectURL(new Blob([depuisBase64(r.data)], { type: "application/octet-stream" }));
    const lien = el("a"); lien.href = url; lien.download = nomFichierAtn(jeu || (a && a.nom) || r.set); document.body.appendChild(lien); lien.click(); lien.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
    PL.signaler(T("photolab.actions.sauve", { n: (r.actions || []).length }));
    if ((r.skipped || []).length) PL.signaler(T("photolab.actions.sautees", { n: r.skipped.length }), true);
  }

  /* ── lecture (pas à pas quand un dialogue ou un Arrêt l'exige) ── */
  function montrerArret(op) {
    return ouvrirDialogue(PL, { titre: T("photolab.actions.arret_titre"), classe: "ac-dialogue",
      construire: ({ corps: c }) => { c.appendChild(brut(el("p", "ac-message", op.message))); },
      boutons: op.continuer ? [{ role: "annuler", libelle: T("photolab.actions.arreter_court") }, { role: "continuer", libelle: T("photolab.actions.continuer"), principal: true }]
        : [{ role: "annuler", libelle: T("photolab.actions.arreter_court"), principal: true }] });
  }
  function dialogueLecture(action, step) {
    const e = action.etapes[step];
    const r = entreeRegistre(e.id);
    const cat = catalogue && catalogue.get(e.id);
    const lib = cat ? String((lang() === "en" ? cat.libelle_en : cat.libelle_fr) || e.id).replace(/…$/, "") : e.id;
    return new Promise((res) => PL.ouvrirReglage({ id: e.id, libelle: lib, champs: r.champs }, { initiales: e.params, apres: (role, x) => res(role === "ok" && !!(x && x.ok)) }));
  }
  async function jouer(nom, depuis = 0) {
    if (lecture || donnees.recording) return;
    const action = actionsDe(arbre).find((a) => a.nom === nom);
    if (!action) return;
    lecture = true; arreterLecture = false; dessiner();
    let joue = false;
    try {
      for (const op of planLecture(action, depuis, aDialogue)) {
        if (arreterLecture) break;
        if (op.type === "segment") {
          let r = null;
          try { r = await PL.post("/executer", { command: "actions.play", params: paramsSegment(nom, op) }); } catch (e) { break; }      // signalé (refus du pont)
          joue = true;
          if (r && r.failed) { PL.signaler(T("photolab.actions.echec", { nom, n: r.failed.step + 1, erreur: r.failed.error || "" }), true); break; }
        } else if (op.type === "arret") {
          if ((await montrerArret(op)) !== "continuer") { PL.signaler(T("photolab.actions.lecture_arretee", { nom })); break; }
        } else if (op.type === "dialogue") {
          if (!PL.etat.doc) { PL.signaler(T("photolab.actions.dialogue_sans_doc"), true); break; }
          if (!(await dialogueLecture(action, op.step))) { PL.signaler(T("photolab.actions.lecture_arretee", { nom })); break; }
          joue = true;
        }
      }
    } finally {
      lecture = false;
      if (joue) { if (PL.etat.doc) await PL.cycle(); else if (PL.documentOuvert) await PL.documentOuvert(); }
      relire();
    }
  }

  /* ── Fichier › Automatisation › Traitement par lots ── */
  async function traitementParLots() {
    await relire();
    const acts = actionsDe(arbre);
    if (!acts.length) { PL.signaler(T("photolab.actions.vide"), true); return; }
    const a0 = actionChoisie() || acts[0];
    const s = { jeu: a0.jeu || "", action: a0.nom, images: [], format: "png", quality: 90, suffixe: a0.nom, continuer: false };
    let images = [];
    try { const d = await (await fetch("/api/images")).json(); images = ((d && d.images) || []).slice().sort((x, y) => (y.mtime || 0) - (x.mtime || 0)); } catch (e) { images = []; }
    let erreur;
    const role = await ouvrirDialogue(PL, { titre: T("photolab.actions.lot_titre"), classe: "large ac-dlg-lot",
      construire: ({ corps: c }) => {
        const tete = el("div", "ac-lot-tete");
        const sJeu = el("select"); const sAct = el("select");
        const jeux = [""].concat(jeuxDe(arbre).filter((j) => acts.some((x) => x.jeu === j)));
        for (const j of jeux) { const o = j ? brut(el("option", null, j)) : el("option", null, T("photolab.actions.sans_jeu")); o.value = j; sJeu.appendChild(o); }
        const remplirActions = () => {
          sAct.textContent = "";
          for (const x of acts.filter((y) => (y.jeu || "") === sJeu.value)) { const o = brut(el("option", null, x.nom)); o.value = x.nom; sAct.appendChild(o); }
          if ([...sAct.options].some((o) => o.value === s.action)) sAct.value = s.action; else { s.action = sAct.value; s.suffixe = sAct.value || ""; iSuf.value = s.suffixe; }
        };
        sJeu.value = s.jeu;
        const iSuf = brut(Object.assign(el("input"), { type: "text", maxLength: 40, value: s.suffixe }));
        sJeu.addEventListener("change", () => { s.jeu = sJeu.value; remplirActions(); });
        sAct.addEventListener("change", () => { s.action = sAct.value; s.suffixe = sAct.value; iSuf.value = s.suffixe; });
        iSuf.addEventListener("input", () => { s.suffixe = iSuf.value; });
        const sFmt = el("select");
        for (const f of ["png", "jpg"]) { const o = el("option", null, f.toUpperCase()); o.value = f; sFmt.appendChild(o); }
        const iQ = Object.assign(el("input"), { type: "number", min: 1, max: 100, value: 90 });
        const lq = el("label", "ac-champ"); lq.append(el("span", null, T("photolab.export.qualite")), iQ); lq.hidden = true;
        sFmt.addEventListener("change", () => { s.format = sFmt.value; lq.hidden = s.format !== "jpg"; });
        iQ.addEventListener("input", () => { s.quality = iQ.value; });
        const sErr = el("select");
        for (const [v, k] of [["arreter", "photolab.actions.lot_erreur_arreter"], ["continuer", "photolab.actions.lot_erreur_continuer"]]) { const o = el("option", null, T(k)); o.value = v; sErr.appendChild(o); }
        sErr.addEventListener("change", () => { s.continuer = sErr.value === "continuer"; });
        champ(tete, "photolab.actions.jeu", sJeu); champ(tete, "photolab.actions.action", sAct);
        champ(tete, "photolab.actions.lot_format", sFmt); tete.appendChild(lq);
        champ(tete, "photolab.actions.lot_suffixe", iSuf); champ(tete, "photolab.actions.lot_erreurs", sErr);
        c.appendChild(tete);
        remplirActions();
        const barre = el("div", "ac-lot-barre");
        const q = Object.assign(el("input"), { type: "search", placeholder: T("commun.action.rechercher") }); q.className = "lib-recherche";
        const compte = el("span", "ac-lot-compte");
        const bTout = el("button", "pl-bouton", T("photolab.actions.lot_tout")); bTout.type = "button";
        const bAucun = el("button", "pl-bouton", T("photolab.actions.lot_aucun")); bAucun.type = "button";
        barre.append(q, bTout, bAucun, compte);
        const grille = el("div", "lib-grille ac-lot-grille");
        c.append(el("p", "ac-aide", T("photolab.actions.lot_aide")), barre, grille);
        erreur = el("p", "ac-erreur"); c.appendChild(erreur);
        const choisies = new Set();
        const vues = () => images.filter((i) => !q.value.trim() || String(i.filename).toLowerCase().includes(q.value.trim().toLowerCase()));
        const peindre = () => {
          grille.textContent = "";
          const v = vues();
          if (!v.length) grille.appendChild(el("p", "ac-vide", T("commun.etat.aucun_resultat")));
          for (const i of v) {
            const b = brut(el("button", "lib-carte ac-lot-carte" + (choisies.has(i.filename) ? " choisie" : ""))); b.type = "button"; b.title = i.filename;
            b.setAttribute("aria-pressed", choisies.has(i.filename) ? "true" : "false"); b.dataset.nom = i.filename;
            const im = el("img"); im.loading = "lazy"; im.alt = ""; im.src = "/api/images/" + encodeURIComponent(i.filename);
            b.append(im, el("span", null, i.filename));
            b.addEventListener("click", () => { if (choisies.has(i.filename)) choisies.delete(i.filename); else choisies.add(i.filename); s.images = [...choisies]; peindre(); });
            grille.appendChild(b);
          }
          compte.textContent = T("photolab.actions.lot_compte", { n: choisies.size });
        };
        bTout.addEventListener("click", () => { for (const i of vues()) choisies.add(i.filename); s.images = [...choisies]; peindre(); });
        bAucun.addEventListener("click", () => { choisies.clear(); s.images = []; peindre(); });
        q.addEventListener("input", peindre); peindre();
        return () => { const p = paramsLot(s); erreur.textContent = p.erreur ? T(p.erreur) : ""; return !p.erreur; };
      },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: T("photolab.actions.lot_lancer"), principal: true }] });
    if (role !== "ok") return;
    lancerLot(paramsLot(s));
  }
  async function lancerLot(p) {
    let stop = false, faites = 0;
    const erreurs = [];
    let ligne, fermerAvance = null;
    ouvrirDialogue(PL, { titre: T("photolab.actions.lot_titre"), classe: "ac-dialogue",
      construire: ({ corps: c, fermer }) => { fermerAvance = fermer; ligne = el("p", "ac-lot-avance", T("photolab.actions.lot_avance", { i: 0, n: p.images.length })); c.appendChild(ligne); },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }] }).then(() => { stop = true; });
    lecture = true; dessiner();
    try {
      for (let i = 0; i < p.images.length && !stop; i++) {
        if (ligne) ligne.textContent = T("photolab.actions.lot_avance", { i: i + 1, n: p.images.length });
        try { await PL.api("POST", "/actions/lot", corpsLot(p, p.images[i]), 0, true); faites++; }
        catch (e) { erreurs.push(p.images[i] + " : " + (e && e.message ? e.message : "")); if (!p.continuer) break; }
      }
    } finally {
      lecture = false;
      if (fermerAvance) fermerAvance("fini");
      PL.signaler(T("photolab.actions.lot_fini", { n: faites }), !!erreurs.length);
      if (erreurs.length) PL.signaler(T("photolab.actions.lot_erreurs_n", { n: erreurs.length }) + " — " + erreurs[0], true);
      relire();
    }
  }

  PL.actions = PL.actions || {};
  PL.actions["file.automate.batch"] = traitementParLots;
  PL.actionsPanneau = { relire, jouer, etat: () => donnees, arbre: () => arbre };
  relire();
}
