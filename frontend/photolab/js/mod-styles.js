// mod-styles.js — le dialogue Style de calque (t138 B6), d'après celui de photocraft (crates/ui-egui/src/layer_style.rs) :
// colonne de gauche « Options de fusion » + les 10 effets avec leur case, colonne de droite les paramètres de l'effet
// choisi. Boîte NON modale (la coquille de mod-dialogue-reglage.js), aperçu calculé par le MOTEUR sur une copie
// (POST /apercu {etapes}), OK -> les étapes en séquence dans UNE tâche de la file FIFO, puis un cycle.
//
// Ce que le moteur impose (relevé du 08/10, « Faits établis » du plan) :
//   - doc.inspect ne rend que effects.items [{kind: "Drop Shadow", enabled}], AUCUN paramètre : l'écran garde les
//     siens dans PL.etat.styles[nom|génération][id du calque][kind] = {actif, params} ;
//   - ré-appeler layer.layerStyle.<kind> REMPLACE l'effet par les défauts du moteur + les clés reçues : un effet
//     modifié renvoie donc TOUS ses paramètres, et l'éteindre se fait par enabled:false + tous ses paramètres.
// Les champs et leurs défauts sont ceux du dialogue de photocraft (spec()/defaults()), pas tout le registre : le
// registre décrit aussi from/to du contour (leur seule présence passe le contour en DÉGRADÉ), technique, contour,
// texture… que le dialogue amont ne montre pas. Les fonctions PURES sont exportées (qa/styles.test.mjs).

import { coercer, valeurInitiale } from "./mod-champs.js";
import { idFusion, trouverCalque } from "./mod-calques.js";
import { coquilleReglage, fabriquerControle, derniereGagne, chargerImage, identiteDocument, titreDialogue, DELAI_APERCU }
  from "./mod-dialogue-reglage.js";
import { maxSideRequete, brut } from "./mod-cycle.js";

export const OPTIONS_FUSION = "blendingOptions";
const PREFIXE = "layer.layerStyle.";

// Champs au format du registre structuré (mod-champs) : la coercition, les contrôles et les bornes du dialogue
// générique servent tels quels. Curseurs entiers comme photocraft (slider_row arrondit : `v.round()`).
const curseur = (cle, min, max, unite, defaut) => ({ cle, type: "number", min, max, entier: true, unite, defaut, optionnel: false });
const couleur = (cle, defaut) => ({ cle, type: "color", formes: ["hex"], defaut, optionnel: false });
const fusion = (defaut) => ({ cle: "blend", type: "str", defaut, optionnel: false });
const choix = (cle, valeurs, defaut) => ({ cle, type: "enum", valeurs, defaut, optionnel: false });
const coche = (cle, defaut) => ({ cle, type: "bool", defaut, optionnel: false });
const opacite = (defaut) => curseur("opacity", 0, 100, "%", defaut);
const angle = (defaut) => curseur("angle", -180, 180, "deg", defaut);

// Ordre de la liste du dialogue amont (KINDS), options de fusion en tête ; `moteur` = libellé rendu par doc.inspect
// (photocraft_doc::Effect::label). Défauts du dialogue amont (layer_style.rs:142-166), modes en ids camelCase (le
// pont n'admet que les 28 ids pour une clé `blend`). `cle` : libellé du dictionnaire quand celui du catalogue amont
// s'écarte du vocabulaire de Photoshop en français (« Contourner », « Superposition de couleur »…) ; Satin, Ombre
// portée et Options de fusion gardent le catalogue, qui est juste.
export const STYLES = [
  { kind: OPTIONS_FUSION, moteur: null, champs: [fusion("normal"), opacite(100), curseur("fillOpacity", 0, 100, "%", 100)] },
  { kind: "bevelEmboss", moteur: "Bevel & Emboss", cle: "photolab.styles.bevelemboss", champs: [choix("style", ["inner", "outer", "emboss", "pillow"], "inner"),
    curseur("depth", 1, 1000, "%", 100), choix("direction", ["up", "down"], "up"), curseur("size", 0, 250, "px", 5),
    curseur("soften", 0, 16, "px", 0), angle(120), curseur("altitude", 0, 90, "deg", 30)] },
  { kind: "stroke", moteur: "Stroke", cle: "photolab.styles.stroke", champs: [curseur("size", 1, 250, "px", 3), choix("position", ["outside", "inside", "center"], "outside"),
    fusion("normal"), opacite(100), couleur("color", "#000000")] },
  { kind: "innerShadow", moteur: "Inner Shadow", cle: "photolab.styles.innershadow", champs: [fusion("multiply"), couleur("color", "#000000"), opacite(75), angle(120),
    curseur("distance", 0, 300, "px", 5), curseur("choke", 0, 100, "%", 0), curseur("size", 0, 250, "px", 5)] },
  { kind: "innerGlow", moteur: "Inner Glow", cle: "photolab.styles.innerglow", champs: [fusion("screen"), opacite(75), couleur("color", "#ffffbe"),
    choix("source", ["edge", "center"], "edge"), curseur("choke", 0, 100, "%", 0), curseur("size", 0, 250, "px", 5)] },
  { kind: "satin", moteur: "Satin", champs: [fusion("multiply"), couleur("color", "#000000"), opacite(50), angle(19),
    curseur("distance", 0, 250, "px", 11), curseur("size", 0, 250, "px", 14), coche("invert", true)] },
  { kind: "colorOverlay", moteur: "Color Overlay", cle: "photolab.styles.coloroverlay", champs: [fusion("normal"), couleur("color", "#ff0000"), opacite(100)] },
  { kind: "gradientOverlay", moteur: "Gradient Overlay", cle: "photolab.styles.gradientoverlay", champs: [fusion("normal"), opacite(100), couleur("from", "#000000"),
    couleur("to", "#ffffff"), coche("reverse", false), choix("style", ["linear", "radial", "angle", "reflected", "diamond"], "linear"),
    angle(90), curseur("scale", 10, 150, "%", 100)] },
  // Motif : le choix du motif (union id|nom, liste à part) n'est pas montré ; le moteur prend le premier de sa
  // bibliothèque, comme le dialogue amont quand `pattern` est vide.
  { kind: "patternOverlay", moteur: "Pattern Overlay", cle: "photolab.styles.patternoverlay", champs: [fusion("normal"), opacite(100), angle(0),
    curseur("scale", 1, 1000, "%", 100), coche("link", true)] },
  { kind: "outerGlow", moteur: "Outer Glow", cle: "photolab.styles.outerglow", champs: [fusion("screen"), opacite(75), couleur("color", "#ffffbe"),
    curseur("spread", 0, 100, "%", 0), curseur("size", 0, 250, "px", 5), curseur("range", 1, 100, "%", 50)] },
  { kind: "dropShadow", moteur: "Drop Shadow", champs: [fusion("multiply"), couleur("color", "#000000"), opacite(75), angle(120),
    curseur("distance", 0, 300, "px", 5), curseur("spread", 0, 100, "%", 0), curseur("size", 0, 250, "px", 5), coche("knocksOut", true)] },
];
export const EFFETS = STYLES.filter((s) => s.kind !== OPTIONS_FUSION);

export function infoStyle(kind) { return STYLES.find((s) => s.kind === kind) || null; }

export function defautsStyle(kind) {
  const s = infoStyle(kind);
  const v = {};
  if (s) for (const c of s.champs) v[c.cle] = valeurInitiale(c);
  return v;
}

// Paramètres complets et coercés d'un style : chaque champ du dialogue (absent ou illisible -> défaut), rien d'autre
// (ni layer, ni add, ni clé inconnue). Options de fusion : passThrough GARDÉ (un groupe ; coercer le refuse parce
// qu'un effet ne le prend jamais) et toute autre saisie lue par idFusion.
export function normaliserParams(kind, params) {
  const s = infoStyle(kind);
  const p = params && typeof params === "object" ? params : {};
  const v = {};
  if (!s) return v;
  for (const c of s.champs) {
    if (kind === OPTIONS_FUSION && c.cle === "blend") v.blend = (typeof p.blend === "string" && idFusion(p.blend)) || "normal";
    else v[c.cle] = coercer(c, p[c.cle], p);
  }
  return v;
}

export function egalParams(kind, a, b) {
  const x = normaliserParams(kind, a), y = normaliserParams(kind, b);
  return Object.keys(x).every((k) => x[k] === y[k]);
}

// « Drop Shadow », « Bevel & Emboss », « dropShadow » -> même forme (le pont ou une version du moteur peut rendre l'id).
const normNom = (s) => String(s == null ? "" : s).toLowerCase().replace(/[^a-z]/g, "");
// 0..1 de doc.inspect -> 0..100 du dialogue ; absent = opaque.
const pct = (x) => (typeof x === "number" && Number.isFinite(x) ? Math.round(x * 100) : 100);

// État du dialogue pour un calque -> {<kind>: {actif, present, params, inconnu?}} (les 11 entrées de STYLES).
// memoire = PL.etat.styles[cle du document][id du calque] ; effets = calque.effects de doc.inspect ({enabled, items}
// ou items seuls) ; calque = la ligne de doc.inspect (options de fusion : blend, opacity, fill).
// - au moteur ET en mémoire : actif selon le moteur (il fait foi), paramètres de la mémoire ;
// - au moteur seulement (document rouvert, moteur relancé) : défauts affichés, `inconnu` (l'écran ne peut pas relire) ;
// - en mémoire seulement (effacé, annulé) : éteint, paramètres gardés comme point de départ.
export function etatStyles(memoire, effets, calque) {
  const mem = memoire && typeof memoire === "object" ? memoire : {};
  const items = Array.isArray(effets) ? effets : effets && Array.isArray(effets.items) ? effets.items : [];
  const c = calque && typeof calque === "object" ? calque : null;
  const etat = {
    [OPTIONS_FUSION]: { actif: true, present: true,
      params: normaliserParams(OPTIONS_FUSION, c ? { blend: c.blend, opacity: pct(c.opacity), fillOpacity: pct(c.fill) } : {}) },
  };
  for (const s of EFFETS) {
    const item = items.find((it) => it && (normNom(it.kind) === normNom(s.moteur) || normNom(it.kind) === normNom(s.kind)));
    const m = mem[s.kind] && typeof mem[s.kind] === "object" ? mem[s.kind] : null;
    const params = normaliserParams(s.kind, m && m.params);
    if (item) etat[s.kind] = m ? { actif: item.enabled !== false, present: true, params } : { actif: item.enabled !== false, present: true, params, inconnu: true };
    else etat[s.kind] = { actif: false, present: false, params };
  }
  return etat;
}

// Étapes MINIMALES pour passer de `avant` à `apres` (états d'etatStyles) sur le calque idCalque (null : le moteur
// prend le calque actif) -> [{command, params}] :
// - options de fusion changées : layer.layerStyle.blendingOptions {layer, blend, opacity, fillOpacity}, EN TÊTE
//   (photocraft les applique avant les effets) ;
// - effet coché (nouveau, rallumé ou modifié) : layer.layerStyle.<kind> {layer, ...tous ses paramètres} ;
// - effet décoché alors qu'il était actif, ou éteint au moteur et modifié : {layer, enabled:false, ...tous} ;
// - un effet qui n'existe pas au moteur et reste décoché : rien.
export function etapesStyles(avant, apres, idCalque) {
  const a = avant || {}, b = apres || {};
  const cible = idCalque == null ? {} : { layer: idCalque };
  const etapes = [];
  const bo = (e) => (e && e[OPTIONS_FUSION] ? e[OPTIONS_FUSION].params : {});
  if (!egalParams(OPTIONS_FUSION, bo(a), bo(b))) {
    etapes.push({ command: PREFIXE + OPTIONS_FUSION, params: { ...cible, ...normaliserParams(OPTIONS_FUSION, bo(b)) } });
  }
  for (const s of EFFETS) {
    const x = a[s.kind] || { actif: false, present: false, params: {} };
    const y = b[s.kind];
    if (!y) continue;
    const memes = egalParams(s.kind, x.params, y.params);
    const p = normaliserParams(s.kind, y.params);
    if (y.actif) {
      if (!x.actif || !memes) etapes.push({ command: PREFIXE + s.kind, params: { ...cible, ...p } });
    } else if (x.actif || (x.present && !memes)) {
      etapes.push({ command: PREFIXE + s.kind, params: { ...cible, enabled: false, ...p } });
    }
  }
  return etapes;
}

// Mémoire après un OK réussi : seuls les effets ENVOYÉS y entrent (un effet `inconnu` laissé tel quel garde ses vrais
// paramètres au moteur, que l'écran ne connaît pas) ; les options de fusion n'y vont jamais (doc.inspect les relit).
export function memoriser(memoire, apres, etapes) {
  const m = { ...(memoire && typeof memoire === "object" ? memoire : {}) };
  for (const e of etapes || []) {
    const kind = String(e.command).slice(PREFIXE.length);
    if (kind === OPTIONS_FUSION || !infoStyle(kind) || !apres || !apres[kind]) continue;
    m[kind] = { actif: !!apres[kind].actif, params: normaliserParams(kind, apres[kind].params) };
  }
  return m;
}

// Repère d'historique posé avec la mémoire (doc.history relu APRÈS le cycle qui suit OK) : sa longueur et son dernier
// libellé (« Layer Style: Drop Shadow »). null si le pont ne rend pas d'historique.
export function marqueHistorique(history) {
  if (!Array.isArray(history) || !history.length) return null;
  return { n: history.length, libelle: history[history.length - 1] };
}

// La mémoire d'un calque vaut-elle encore ? Le moteur ne rend pas les paramètres des effets : après un Ctrl+Z (historique
// plus court que le repère) ou un Ctrl+Z suivi d'un autre geste (l'entrée repérée n'est plus à sa place), les
// paramètres gardés ne sont plus ceux du moteur. Sans repère ni historique (pont ancien) : rien pour en douter.
// entree = {effets, marque} de PL.etat.styles[cle][id].
export function memoireValide(entree, history) {
  if (!entree || typeof entree !== "object") return false;
  const m = entree.marque;
  if (!m) return !Array.isArray(history);
  return Array.isArray(history) && history.length >= m.n && history[m.n - 1] === m.libelle;
}

// Effets de la mémoire à donner à etatStyles : ceux de l'entrée si elle vaut encore, sinon rien (les effets présents au
// moteur s'affichent alors `inconnu` : défauts et mention « non relisible »).
export function memoireDuCalque(entree, history) {
  return memoireValide(entree, history) && entree.effets && typeof entree.effets === "object" ? entree.effets : {};
}

// Ouverture : la page demandée (menu Calque › Style de calque › X) est choisie ET cochée, comme photocraft
// (initial_fields(select)) ; sans demande (bouton fx, badge), le premier effet présent, sinon l'ombre portée, sans
// rien cocher. -> {selection, etat} (état copié : celui d'avant reste la référence des étapes).
export function ouvertureStyles(etat, demande) {
  const e = JSON.parse(JSON.stringify(etat || {}));
  if (demande && infoStyle(demande)) {
    if (demande !== OPTIONS_FUSION && e[demande]) e[demande].actif = true;
    return { selection: demande, etat: e };
  }
  const premier = EFFETS.find((s) => e[s.kind] && e[s.kind].present);
  return { selection: premier ? premier.kind : "dropShadow", etat: e };
}

// Libellé d'un style : la clé du dictionnaire du style s'il en a une (vocabulaire de Photoshop), sinon celui du
// catalogue des menus (Calque › Style de calque, fr ou en selon la langue de l'arbre) sans « … » ; options de fusion :
// photolab.styles.options_fusion ; à défaut le libellé du moteur (jamais vide).
export function libelleStyle(kind, arbre, t) {
  const info = infoStyle(kind);
  const cleDico = kind === OPTIONS_FUSION ? "photolab.styles.options_fusion" : info && info.cle;
  if (cleDico && typeof t === "function") {
    const r = t(cleDico);
    if (r && r !== cleDico) return r;
  }
  const id = PREFIXE + kind;
  const chercher = (liste) => {
    for (const e of liste || []) {
      if (e && e.type === "commande" && e.id === id && e.libelle) return e.libelle;
      const r = e && Array.isArray(e.entrees) ? chercher(e.entrees) : null;
      if (r) return r;
    }
    return null;
  };
  let trouve = null;
  for (const m of Array.isArray(arbre) ? arbre : []) { trouve = chercher(m.entrees); if (trouve) break; }
  if (trouve) return titreDialogue(trouve);
  const s = infoStyle(kind);
  return (s && s.moteur) || kind;
}

/* ───────────── côté DOM ───────────── */

export function initStyles(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  PL.etat.styles = PL.etat.styles || {};
  let actuel = null;                   // le dialogue ouvert : {fermer, surDoc}

  // Le calque visé change pendant que le dialogue est ouvert (opacité, mode changés au panneau Calques, Ctrl+Z) : les
  // options de fusion de référence sont relues ; le calque a disparu : le dialogue n'a plus d'objet.
  if (PL.surDoc) PL.surDoc.push((doc) => { if (actuel) actuel.surDoc(doc); });

  PL.ouvrirStyles = function ouvrirStyles(demande) {
    const doc = PL.etat.doc;
    if (!doc) return null;
    // Calque visé FIGÉ à l'ouverture : un clic dans le panneau Calques pendant le réglage ne déplace pas les effets.
    const idCalque = doc.activeLayer == null ? null : doc.activeLayer;
    const calque = idCalque == null ? null : trouverCalque(doc.layers, idCalque);
    // Clé de la mémoire = identité du document du dialogue générique (nom|index|génération) : deux « Sans titre-1 »
    // ne partagent rien, un moteur relancé (qui renumérote tout) repart de zéro.
    const cle = identiteDocument(doc, PL.etat.generation);
    const parDoc = PL.etat.styles[cle] || {};
    const memoire = idCalque == null ? {} : memoireDuCalque(parDoc[idCalque], doc.history);
    let initial = etatStyles(memoire, calque && calque.effects, calque);
    const depart = ouvertureStyles(initial, demande);
    let courant = depart.etat;
    let selection = depart.selection;
    const groupe = !!(calque && Array.isArray(calque.children));

    const etatDlg = { identite: cle };
    PL.prendreReglage(etatDlg);          // un seul dialogue de réglage à la fois (l'ancien s'annule)
    let apercuPose = false, fini = false, minuterie = null;
    const demander = derniereGagne((corps) => PL.api("POST", "/apercu", corps, 0, true));
    const arbre = () => (PL.menus && PL.menus.arbre) || [];

    const coq = coquilleReglage(PL, {
      titre: T("photolab.calques.style"), classe: "pl-styles", avecApercu: true,
      valider: () => { controles.forEach((x) => x.lire()); fermer("ok"); },
      annuler: () => fermer("annuler"),
      reinitialiser: () => { courant = ouvertureStyles(initial, demande).etat; dessinerListe(); dessinerPage(); coq.montrerErreur(""); planifier(); },
      surCaseApercu: (oui) => {
        if (oui) { planifier(); return; }
        clearTimeout(minuterie); demander.annuler(); coq.occupe(false); coq.montrerErreur("");
        if (apercuPose) { apercuPose = false; PL.cycle(); }
      },
    });

    const el = (tag, classe, texte) => { const e = document.createElement(tag); if (classe) e.className = classe; if (texte != null) e.textContent = texte; return e; };
    // Titre « Style de calque — <nom> » : le nom est une donnée de l'utilisateur, la surcouche n'y touche pas.
    const titreEl = coq.tete.children[0];
    if (titreEl && calque) {
      titreEl.textContent = T("photolab.calques.style") + " — ";
      titreEl.appendChild(brut(el("span", "st-calque", calque.name == null ? "" : String(calque.name))));
    }
    const cols = el("div", "st-cols");
    const liste = el("div", "st-liste");
    liste.setAttribute("role", "listbox");
    const page = el("div", "st-page");
    const titrePage = el("h3", "st-titre");
    const note = el("p", "st-note", T("photolab.styles.non_relisible"));
    const zone = el("div", "st-champs");
    page.append(titrePage, note, zone);
    cols.append(liste, page);
    coq.corps.append(cols, coq.erreur);

    /* colonne de gauche : Options de fusion, puis les 10 effets (case = allumé ; clic sur le nom = page + cochée,
       comme photocraft) */
    const lignes = new Map();          // kind -> {ligne, caseEl}
    for (const s of STYLES) {
      const ligne = el("div", "st-item");
      ligne.dataset.kind = s.kind;
      ligne.setAttribute("role", "option");
      const nom = el("button", "st-nom", libelleStyle(s.kind, arbre(), T));
      nom.type = "button";
      let caseEl = null;
      if (s.kind !== OPTIONS_FUSION) {
        caseEl = el("input", "st-case");
        caseEl.type = "checkbox";
        caseEl.setAttribute("aria-label", nom.textContent);
        caseEl.addEventListener("change", () => {
          courant = { ...courant, [s.kind]: { ...courant[s.kind], actif: !!caseEl.checked } };
          selection = s.kind;
          dessinerListe(); dessinerPage(); planifier();
        });
        ligne.appendChild(caseEl);
      } else ligne.classList.add("st-options");
      nom.addEventListener("click", () => {
        selection = s.kind;
        if (s.kind !== OPTIONS_FUSION && !courant[s.kind].actif) {
          courant = { ...courant, [s.kind]: { ...courant[s.kind], actif: true } };
          planifier();
        }
        dessinerListe(); dessinerPage();
      });
      ligne.appendChild(nom);
      liste.appendChild(ligne);
      lignes.set(s.kind, { ligne, caseEl });
    }

    function dessinerListe() {
      for (const [kind, { ligne, caseEl }] of lignes) {
        const choisi = kind === selection;
        ligne.classList.toggle("choisi", choisi);
        ligne.setAttribute("aria-selected", choisi ? "true" : "false");
        if (caseEl) { caseEl.checked = !!courant[kind].actif; ligne.classList.toggle("actif", !!courant[kind].actif); }
      }
    }

    /* colonne de droite : les champs du style choisi, fabriqués comme ceux du dialogue générique */
    let controles = [];
    function poser(c, brutV, final, depuisLeCurseur = false) {
      const s = courant[selection];
      const v = selection === OPTIONS_FUSION && c.cle === "blend"
        ? (typeof brutV === "string" && idFusion(brutV)) || "normal"
        : coercer(c, brutV, s.params);
      courant = { ...courant, [selection]: { ...s, params: { ...s.params, [c.cle]: v } } };
      const ctl = controles.find((x) => x.c === c);
      if (ctl) ctl.ecrire(depuisLeCurseur);
      if (final) planifier();
    }
    const ctx = { T, valeurs: () => courant[selection].params, poser };
    function dessinerPage() {
      titrePage.textContent = libelleStyle(selection, arbre(), T);
      note.hidden = !courant[selection].inconnu;
      zone.textContent = "";
      controles = [];
      for (const c0 of infoStyle(selection).champs) {
        // Groupe : Transfert reste TOUJOURS dans la liste des options de fusion (pas seulement tant qu'il est choisi).
        const c = selection === OPTIONS_FUSION && c0.cle === "blend" && groupe ? { ...c0, transfert: true } : c0;
        const ctl = fabriquerControle(c, ctx);
        if (ctl) { controles.push(ctl); zone.appendChild(ctl.el); }
      }
    }

    /* aperçu moteur : les étapes du dialogue rejouées sur une copie du document */
    const apercuActif = () => coq.caseApercu && coq.caseApercu.checked && !fini && !!PL.etat.doc;
    function planifier() {
      clearTimeout(minuterie);
      if (!apercuActif()) return;
      minuterie = setTimeout(lancerApercu, DELAI_APERCU);
    }
    async function lancerApercu() {
      if (!apercuActif()) return;
      const etapes = etapesStyles(initial, courant, idCalque);
      if (!etapes.length) {
        // Rien de changé : le rendu réel EST l'aperçu (et un aperçu resté à l'écran doit lui céder la place).
        demander.annuler(); coq.occupe(false); coq.montrerErreur("");
        if (apercuPose) { apercuPose = false; PL.cycle(); }
        return;
      }
      const voulu = PL.vue.maxSideVoulu();
      coq.occupe(true);
      const r = await demander({ etapes, maxSide: maxSideRequete(voulu, PL.etat.doc) });
      if (r.perime) return;
      coq.occupe(demander.enVol());
      if (fini || !apercuActif()) return;
      if (r.erreur) { coq.montrerErreur(T("photolab.reglage.erreur_apercu") + " " + (r.erreur.message || "")); return; }
      let im;
      try { im = await chargerImage(r.valeur.url); } catch (e) { coq.montrerErreur(T("photolab.reglage.erreur_apercu")); return; }
      if (fini || !apercuActif()) return;
      coq.montrerErreur("");
      PL.vue.poserApercu(im, voulu);
      apercuPose = true;
    }
    etatDlg.surRenduReel = () => {
      // Le rendu réel (zoom, autre commande) a recouvert l'aperçu : plus rien à effacer ; on le redemande à la taille
      // de la vue.
      apercuPose = false;
      if (!apercuActif()) return;
      planifier();
    };

    // Nouveau doc.inspect pendant que le dialogue est ouvert.
    function surDoc(d) {
      if (fini || !d) return;
      const c = idCalque == null ? null : trouverCalque(d.layers, idCalque);
      if (idCalque != null && !c) { fermer("orphelin"); return; }
      const avant = initial[OPTIONS_FUSION];
      const relu = etatStyles({}, undefined, c)[OPTIONS_FUSION];
      if (egalParams(OPTIONS_FUSION, avant.params, relu.params)) return;
      // Options de fusion changées hors du dialogue : elles deviennent la référence ; si l'utilisateur n'y avait pas
      // touché dans le dialogue, elles y sont reprises (sinon sa saisie l'emporte et partira à OK).
      const intact = egalParams(OPTIONS_FUSION, avant.params, courant[OPTIONS_FUSION].params);
      initial = { ...initial, [OPTIONS_FUSION]: relu };
      if (intact) {
        courant = { ...courant, [OPTIONS_FUSION]: relu };
        if (selection === OPTIONS_FUSION) dessinerPage();
      }
    }

    function fermer(role) {
      if (fini) return;
      fini = true;
      clearTimeout(minuterie);
      demander.annuler();
      coq.retirer();
      PL.libererReglage(etatDlg);
      if (actuel && actuel.etat === etatDlg) actuel = null;
      if (role === "ok") {
        const etapes = etapesStyles(initial, courant, idCalque);
        appliquer(etapes, apercuPose);
      } else if (apercuPose) {
        PL.cycle();
      }
    }
    etatDlg.fermer = fermer;

    // Toutes les étapes dans UNE SEULE tâche de la file FIFO, envoyées l'une après l'autre : un Ctrl+Z tapé juste
    // après OK (PL.historique passe aussi par PL.file) arrive après la DERNIÈRE étape, jamais entre deux — une tâche
    // par étape le laisserait s'intercaler et annuler un style à moitié posé. La première qui échoue arrête la suite
    // (déjà signalée par mod-api) ; puis un seul cycle. Les étapes RÉUSSIES sont au moteur : elles entrent en mémoire,
    // avec le repère d'historique relu par le cycle (un Ctrl+Z ultérieur les rendra « non relisibles »).
    async function appliquer(etapes, apercuAEffacer) {
      let reussies = 0;
      if (etapes.length) {
        await PL.file(async () => {
          for (const e of etapes) {
            if (!PL.etat.doc) break;                 // document fermé entre-temps : plus rien à styler
            try { await PL.post("/executer", { command: e.command, params: e.params }); } catch (err) { break; }
            reussies++;
          }
        }).catch(() => {});
      }
      const d = etapes.length || apercuAEffacer ? await PL.cycle() : null;
      if (!reussies || cle == null || idCalque == null) return;
      const m = PL.etat.styles[cle] || (PL.etat.styles[cle] = {});
      const avantEntree = m[idCalque];
      m[idCalque] = {
        effets: memoriser(memoireValide(avantEntree, doc.history) ? avantEntree.effets : {}, courant, etapes.slice(0, reussies)),
        marque: marqueHistorique(d && d.history),
      };
    }

    actuel = { etat: etatDlg, surDoc };
    dessinerListe();
    dessinerPage();
    coq.placer();
    planifier();                       // page demandée cochée à l'ouverture : son aperçu, comme photocraft
    return etatDlg;
  };
}
