// mod-dialogue-reglage.js — le dialogue générique des filtres et réglages (t138 B2), fabriqué depuis les champs du
// registre du moteur (mod-champs.js). Look du « Flou gaussien » de photocraft (inventaire A6) : titre, libellé + champ
// numérique + unité au-dessus d'un curseur, case « Aperçu », Annuler / OK. Boîte NON modale (pas de voile : on doit
// pouvoir zoomer et regarder l'image pendant qu'on règle), placée en haut à droite de la scène, déplaçable par sa tête.
// L'aperçu est calculé par le MOTEUR sur une copie du document (POST /apercu) : l'écran n'invente aucun pixel.
// Les fonctions PURES sont exportées (qa/dialogue.test.mjs).

import { champsVisibles, controleDe, valeursDe, valeurInitiale, coercer, parametres, bornesEffectives, libelleParam,
  libelleValeur, humaniser, pasDe } from "./mod-champs.js";
import { MODES_FUSION, MODE_TRANSFERT } from "./mod-calques.js";
import { maxSideRequete } from "./mod-cycle.js";

// Copie de FILTRES_HORS_APERCU / REGLAGES_HORS_APERCU du pont (photolab_moteur.py) : le pont refuse l'aperçu de ces
// commandes (400) ; un banc relit le source Python et compare.
export const FILTRES_HORS_APERCU = new Set(["filter.convertForSmartFilters", "filter.lastFilter", "filter.filterGallery",
  "filter.cameraRaw", "filter.liquify", "filter.vanishingPoint", "filter.adaptiveWideAngle"]);
export const REGLAGES_HORS_APERCU = new Set(["image.adjustments.colorLookup.list"]);
// Attente après le dernier changement avant de demander un aperçu : un curseur qu'on manie au clavier ne lance pas
// une copie du document à chaque cran.
export const DELAI_APERCU = 250;

// Seules les familles filter.* et image.adjustments.* ont un aperçu dans le dialogue générique (les styles et les
// calques de réglage ont leurs éditeurs sur mesure).
export function estFamilleApercu(id) {
  if (typeof id !== "string") return false;
  if (id.startsWith("filter.")) return !FILTRES_HORS_APERCU.has(id);
  if (id.startsWith("image.adjustments.")) return !REGLAGES_HORS_APERCU.has(id);
  return false;
}

// Une seule requête en vol, la plus récente gagne. demander(x) -> Promise<{perime: true} | {perime: false, valeur} |
// {perime: false, erreur}> : une demande arrivée pendant le vol REMPLACE celle qui attendait (jamais lancée) et rend
// périmé le résultat en vol ; à son retour, seule la dernière demande part. annuler() périme tout (fermeture du
// dialogue : un aperçu tardif ne doit pas recouvrir le rendu réel). enVol() dit si une requête vole (indicateur
// « occupé » des dialogues).
export function derniereGagne(tache) {
  let numero = 0;
  let enVol = null;
  let attente = null;            // {x, n, resoudre}
  function lancer(x, n, resoudre) {
    let p;
    try { p = Promise.resolve(tache(x)); } catch (e) { p = Promise.reject(e); }
    enVol = p;
    const fin = (r) => {
      resoudre(n !== numero ? { perime: true } : r);
      enVol = null;
      if (attente) { const a = attente; attente = null; lancer(a.x, a.n, a.resoudre); }
    };
    p.then((valeur) => fin({ perime: false, valeur }), (erreur) => fin({ perime: false, erreur }));
  }
  function demander(x) {
    const n = ++numero;
    return new Promise((resoudre) => {
      if (!enVol) { lancer(x, n, resoudre); return; }
      if (attente) attente.resoudre({ perime: true });
      attente = { x, n, resoudre };
    });
  }
  demander.annuler = () => {
    numero++;
    if (attente) { attente.resoudre({ perime: true }); attente = null; }
  };
  demander.enVol = () => !!enVol;
  return demander;
}

// Position de départ (coordonnées de la fenêtre) : en haut à droite de la scène, à `marge` px des bords ; jamais à
// gauche du bord gauche de la scène (scène plus étroite que la boîte). scene = {left, top, width, height}.
export function positionInitiale(scene, boite, marge = 12) {
  if (!scene) return { x: marge, y: marge };
  const x = Math.max(scene.left + marge, scene.left + scene.width - boite.w - marge);
  return { x, y: scene.top + marge };
}

// Déplacement par la tête : la boîte reste entière dans la fenêtre (coin haut gauche si elle est plus grande).
export function bornerPosition(x, y, boite, fenetre) {
  return {
    x: Math.min(Math.max(0, x), Math.max(0, fenetre.w - boite.w)),
    y: Math.min(Math.max(0, y), Math.max(0, fenetre.h - boite.h)),
  };
}

// Valeurs que le moteur a réellement appliquées (resultats[0].filter : il borne en silence) -> correctifs à poser
// dans le formulaire. Une valeur que l'utilisateur a changée depuis l'envoi n'est jamais écrasée.
export function valeursAppliquees(champs, envoyes, actuelles, filtre) {
  const patch = {};
  if (!filtre || typeof filtre !== "object" || Array.isArray(filtre)) return patch;
  const e = envoyes || {}, a = actuelles || {};
  for (const c of champsVisibles(champs)) {
    if (!Object.prototype.hasOwnProperty.call(filtre, c.cle)) continue;
    const v = coercer(c, filtre[c.cle], a);
    if (v !== undefined && v !== e[c.cle] && a[c.cle] === e[c.cle]) patch[c.cle] = v;
  }
  return patch;
}

// Valeurs de départ des champs visibles. Deux passes : la seconde relit les bornes qui dépendent d'autres valeurs
// (Teinte/Saturation en colorisation : hue 0..360 seulement si la case est cochée).
export function valeursInitiales(champs) {
  const vis = champsVisibles(champs);
  const v = {};
  for (const c of vis) v[c.cle] = valeurInitiale(c, undefined, {});
  for (const c of vis) v[c.cle] = valeurInitiale(c, undefined, v);
  return v;
}

// Unité affichée à droite du champ numérique.
const UNITES = { deg: "°", ev: "EV" };
export function uniteAffichee(u) {
  if (!u) return "";
  return UNITES[u] || String(u);
}

// Libellé d'une option de liste : un mode de fusion prend la clé de MODES_FUSION ou de MODE_TRANSFERT (photolab.fusion.*,
// celles du panneau Calques ; Transfert pour les options de fusion d'un groupe, t138 B6), toute autre valeur passe par
// libelleValeur (photolab.valeur.*, sinon humanisée).
export function libelleOption(c, v, t) {
  if (c && String(c.cle).toLowerCase() === "blend") {
    const m = [MODE_TRANSFERT, ...MODES_FUSION].find((x) => x.id === v);
    const r = m && typeof t === "function" ? t(m.cle) : null;
    return r && r !== (m && m.cle) ? r : humaniser(v);
  }
  return libelleValeur(v, t);
}

// Le titre est le libellé de l'entrée de menu sans ses points de suspension.
export function titreDialogue(libelle) {
  return String(libelle == null ? "" : libelle).replace(/\s*(…|\.\.\.)\s*$/, "");
}

// Curseur non linéaire : un champ borné de grande étendue (max/min > 100 : rayon 0.1..1000, distance 1..2000) aurait
// toutes les valeurs utiles (quelques pixels) dans le premier pour cent de la course. La POSITION du <input type=range>
// suit alors une échelle de puissance (valeur = min + (max-min)·t³, t sur CRANS_CURSEUR crans) ; le champ numérique,
// lui, reste exact. Ailleurs le curseur porte la valeur elle-même (linéaire).
export const CRANS_CURSEUR = 1000;
const PUISSANCE = 3;
export function curseurPuissance(c, valeurs) {
  if (!c || controleDe(c) !== "curseur") return false;
  const b = bornesEffectives(c, valeurs);
  return typeof b.min === "number" && typeof b.max === "number" && b.min > 0 && b.max / b.min > 100;
}
// Valeur -> position du curseur (0..CRANS_CURSEUR en puissance ; la valeur elle-même sinon).
export function versCurseur(c, v, valeurs) {
  if (!curseurPuissance(c, valeurs)) return v;
  const b = bornesEffectives(c, valeurs);
  const n = Number(v);
  if (!Number.isFinite(n)) return 0;
  const f = Math.min(1, Math.max(0, (n - b.min) / (b.max - b.min)));
  return Math.round(Math.cbrt(f) * CRANS_CURSEUR);
}
// Position du curseur -> valeur coercée, arrondie au pas du champ (jamais une queue de décimales flottantes).
export function depuisCurseur(c, t, valeurs) {
  if (!curseurPuissance(c, valeurs)) return coercer(c, t, valeurs);
  const b = bornesEffectives(c, valeurs);
  const k = Math.min(1, Math.max(0, Number(t) / CRANS_CURSEUR || 0));
  const brut = b.min + (b.max - b.min) * k ** PUISSANCE;
  const pas = pasDe(c, valeurs);
  const dec = pas < 1 ? Math.min(4, Math.max(0, Math.ceil(-Math.log10(pas) - 1e-9))) : 0;
  return coercer(c, Number((Math.round(brut / pas) * pas).toFixed(dec)), valeurs);
}

// Identité du document visé par le dialogue : un autre document actif (nom, index) ou un moteur relancé (génération)
// rend le réglage sans objet.
export function identiteDocument(doc, generation) {
  if (!doc) return null;
  return [doc.name == null ? "" : doc.name, doc.index == null ? "" : doc.index, generation == null ? "" : generation].join("|");
}

/* ───────────── côté DOM ───────────── */

// Chargement d'une image d'aperçu : onload, pas decode() (suspendu en onglet masqué, relevé sur le Spritelab).
export function chargerImage(url) {
  return new Promise((ok, ko) => {
    const im = new Image();
    im.onload = () => ok(im);
    im.onerror = () => ko(new Error(url));
    im.src = url;
  });
}

let numeroId = 0;

// La COQUILLE d'un dialogue de réglage non modal, partagée par le dialogue générique et les éditeurs sur mesure
// (Courbes, Niveaux — mod-courbes.js) : boîte, tête déplaçable avec indicateur de calcul, corps, zone d'erreur, pied
// (case « Aperçu » si avecApercu, Annuler/Réinitialiser au clic Alt, OK), touches stoppées (Échap = annuler, Entrée =
// valider), pose en haut à droite de la scène. Le contenu du corps et la logique d'aperçu restent à l'appelant.
// rappels : valider(), annuler(), reinitialiser(), surCaseApercu(coche).
export function coquilleReglage(PL, { titre, classe = "", avecApercu = false, valider, annuler, reinitialiser, surCaseApercu } = {}) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const boite = document.createElement("div");
  boite.className = "pl-dlg pl-reglage" + (classe ? " " + classe : "");
  boite.setAttribute("role", "dialog");
  const tete = document.createElement("header"); tete.className = "pl-dlg-tete pl-reglage-tete";
  const titreEl = document.createElement("span"); titreEl.className = "pl-reglage-titre"; titreEl.textContent = titre;
  titreEl.id = "plrg-titre-" + (++numeroId);
  boite.setAttribute("aria-labelledby", titreEl.id);
  const calcul = document.createElement("span"); calcul.className = "pl-reglage-calcul"; calcul.hidden = true;
  calcul.textContent = T("photolab.reglage.calcul");
  tete.append(titreEl, calcul);
  const corps = document.createElement("div"); corps.className = "pl-dlg-corps pl-reglage-corps";
  const erreur = document.createElement("p"); erreur.className = "pl-erreur"; erreur.hidden = true;
  erreur.setAttribute("role", "alert");
  const pied = document.createElement("footer"); pied.className = "pl-dlg-pied pl-reglage-pied";
  boite.append(tete, corps, pied);

  /* pied : case Aperçu à gauche, Annuler / OK à droite (A6) */
  let caseApercu = null;
  if (avecApercu) {
    const lab = document.createElement("label"); lab.className = "pl-rg-apercu";
    caseApercu = document.createElement("input"); caseApercu.type = "checkbox"; caseApercu.checked = true;
    const s = document.createElement("span"); s.textContent = T("photolab.reglage.apercu");
    lab.append(caseApercu, s);
    caseApercu.addEventListener("change", () => { if (surCaseApercu) surCaseApercu(caseApercu.checked); });
    pied.appendChild(lab);
  }
  const boutons = document.createElement("div"); boutons.className = "pl-reglage-boutons";
  const bAnnuler = document.createElement("button");
  bAnnuler.type = "button"; bAnnuler.className = "pl-bouton";
  const bOk = document.createElement("button");
  bOk.type = "button"; bOk.className = "pl-bouton principal"; bOk.textContent = T("photolab.reglage.ok");
  boutons.append(bAnnuler, bOk);
  pied.appendChild(boutons);

  // Alt enfoncé : « Annuler » devient « Réinitialiser » (comme photocraft et Photoshop).
  let alt = false;
  function majAlt(oui) {
    alt = !!oui;
    bAnnuler.textContent = T(alt ? "photolab.reglage.reinitialiser" : "photolab.reglage.annuler");
  }
  majAlt(false);
  const surTouche = (ev) => { if (ev.key === "Alt") majAlt(ev.type === "keydown"); };
  const surFlou = () => majAlt(false);
  window.addEventListener("keydown", surTouche, true);
  window.addEventListener("keyup", surTouche, true);
  window.addEventListener("blur", surFlou);

  bOk.addEventListener("click", () => valider && valider());
  bAnnuler.addEventListener("click", (ev) => {
    if (ev.altKey || alt) { if (reinitialiser) reinitialiser(); } else if (annuler) annuler();
  });

  // Les touches ne fuient pas vers les raccourcis (une lettre ne change pas d'outil). Échap = Annuler, Entrée = OK
  // (sauf sur un bouton, qui garde son propre clic).
  boite.addEventListener("keydown", (ev) => {
    ev.stopPropagation();
    if (ev.key === "Alt") { ev.preventDefault(); majAlt(true); return; }
    if (ev.key === "Escape") { ev.preventDefault(); if (annuler) annuler(); }
    else if (ev.key === "Enter" && !(ev.target && ev.target.tagName === "BUTTON")) { ev.preventDefault(); if (valider) valider(); }
  });
  boite.addEventListener("keyup", (ev) => { ev.stopPropagation(); if (ev.key === "Alt") majAlt(false); });

  /* déplacement par la tête */
  let glisse = null;
  tete.addEventListener("pointerdown", (ev) => {
    if (ev.button !== 0) return;
    const r = boite.getBoundingClientRect();
    glisse = { dx: ev.clientX - r.left, dy: ev.clientY - r.top };
    tete.setPointerCapture(ev.pointerId);
    ev.preventDefault();
  });
  tete.addEventListener("pointermove", (ev) => {
    if (!glisse) return;
    const p = bornerPosition(ev.clientX - glisse.dx, ev.clientY - glisse.dy,
      { w: boite.offsetWidth, h: boite.offsetHeight }, { w: innerWidth, h: innerHeight });
    boite.style.left = p.x + "px"; boite.style.top = p.y + "px";
  });
  const finGlisse = (ev) => {
    if (!glisse) return;
    glisse = null;
    try { tete.releasePointerCapture(ev.pointerId); } catch (e) { /* capture déjà perdue */ }
  };
  tete.addEventListener("pointerup", finGlisse);
  tete.addEventListener("pointercancel", finGlisse);

  return {
    boite, tete, corps, pied, erreur, caseApercu,
    occupe(oui) { calcul.hidden = !oui; tete.setAttribute("aria-busy", oui ? "true" : "false"); },
    montrerErreur(texte) { erreur.textContent = texte || ""; erreur.hidden = !texte; },
    // Pose : en haut à droite de la scène, puis le premier champ prend le focus.
    placer() {
      document.body.appendChild(boite);
      const scene = PL.$("#scene");
      const rs = scene ? scene.getBoundingClientRect() : null;
      const pos = positionInitiale(rs ? { left: rs.left, top: rs.top, width: rs.width, height: rs.height } : null,
        { w: boite.offsetWidth, h: boite.offsetHeight });
      const b = bornerPosition(pos.x, pos.y, { w: boite.offsetWidth, h: boite.offsetHeight }, { w: innerWidth, h: innerHeight });
      boite.style.left = b.x + "px"; boite.style.top = b.y + "px";
      const premier = boite.querySelector(".pl-reglage-corps input, .pl-reglage-corps select, button.principal");
      if (premier) premier.focus();
    },
    retirer() {
      window.removeEventListener("keydown", surTouche, true);
      window.removeEventListener("keyup", surTouche, true);
      window.removeEventListener("blur", surFlou);
      boite.remove();
    },
  };
}

function idChamp() { return "plrg-" + (++numeroId); }

// Bornes et pas d'un champ numérique selon les valeurs COURANTES (colorisation), posés sur l'élément.
function poserBornes(el, c, ctx) {
  const b = bornesEffectives(c, ctx.valeurs());
  if (typeof b.min === "number") el.min = String(b.min); else el.removeAttribute("min");
  if (typeof b.max === "number") el.max = String(b.max); else el.removeAttribute("max");
  el.step = String(pasDe(c, ctx.valeurs()));
}

// La FABRIQUE d'un contrôle de formulaire (t138 B5 : partagée par le dialogue générique et l'éditeur des calques de
// réglage du panneau Propriétés, mod-reglages.js). Un champ du registre (mod-champs) -> {c, el, ecrire, lire} ;
// ctx = {T, valeurs() : valeurs COURANTES du formulaire (bornes de la colorisation), poser(c, brut, final,
// depuisLeCurseur) : rangement de la saisie (final = relâchement / « change »)}. `c.cleLibelle` (champ fabriqué par
// l'écran, sans clé de registre) remplace le libellé photolab.param.*.
export function fabriquerControle(c, ctx) {
  const T = ctx.T || ((cle) => cle);
  const sorte = controleDe(c);
  const ligne = document.createElement("div");
  ligne.className = "pl-rg-champ sorte-" + sorte;
  ligne.dataset.cle = c.cle;
  const lib = document.createElement("label");
  lib.className = "pl-rg-lib";
  lib.textContent = c.cleLibelle ? T(c.cleLibelle) : libelleParam(c.cle, T);
  const ident = idChamp();
  lib.htmlFor = ident;
  const unite = uniteAffichee(c.unite);
  const uniteEl = () => { const u = document.createElement("span"); u.className = "pl-unite"; u.textContent = unite; return u; };

  if (sorte === "curseur" || sorte === "nombre") {
    const nombre = document.createElement("input");
    nombre.type = "number"; nombre.id = ident; nombre.className = "pl-rg-nombre";
    const haut = document.createElement("div"); haut.className = "pl-rg-haut";
    const valeur = document.createElement("span"); valeur.className = "pl-rg-valeur";
    valeur.appendChild(nombre);
    if (unite) valeur.appendChild(uniteEl());
    haut.append(lib, valeur);
    ligne.appendChild(haut);
    let curseur = null;
    if (sorte === "curseur") {
      curseur = document.createElement("input");
      curseur.type = "range"; curseur.className = "pl-rg-curseur";
      curseur.setAttribute("aria-label", lib.textContent);
      ligne.appendChild(curseur);
      // Pendant le glisser : le champ numérique suit, sans aperçu ; au relâchement (change) : aperçu.
      // Le curseur lui-même n'est pas réécrit depuis la valeur pendant qu'on le tient (en puissance, l'aller-retour
      // position -> valeur -> position ferait sautiller le pouce d'un cran).
      curseur.addEventListener("input", () => { ctx.poser(c, depuisCurseur(c, curseur.value, ctx.valeurs()), false, true); });
      curseur.addEventListener("change", () => { ctx.poser(c, depuisCurseur(c, curseur.value, ctx.valeurs()), true, true); });
    }
    nombre.addEventListener("change", () => { ctx.poser(c, nombre.value, true); });
    const majBornes = () => {
      poserBornes(nombre, c, ctx);
      if (!curseur) return;
      if (curseurPuissance(c, ctx.valeurs())) { curseur.min = "0"; curseur.max = String(CRANS_CURSEUR); curseur.step = "1"; }
      else poserBornes(curseur, c, ctx);
    };
    // L'ordre compte pour un <input type=range> : bornes et pas AVANT la valeur, sinon elle est ramenée dans les
    // bornes par défaut (0..100) et arrondie au mauvais pas.
    const ecrire = (sansCurseur = false) => {
      majBornes();
      const v = ctx.valeurs()[c.cle];
      nombre.value = v === undefined ? "" : String(v);
      if (curseur && v !== undefined && !sansCurseur) curseur.value = String(versCurseur(c, v, ctx.valeurs()));
    };
    ecrire();
    return { c, el: ligne, ecrire, lire: () => ctx.poser(c, nombre.value, false) };
  }

  if (sorte === "liste") {
    const sel = document.createElement("select");
    sel.id = ident; sel.className = "pl-rg-choix";
    let vals = valeursDe(c);
    const cour = ctx.valeurs()[c.cle];
    // Énumération ouverte (« Multiply|… ») : la valeur courante peut ne pas être dans la liste, on l'ajoute.
    if (cour !== undefined && cour !== "" && !vals.some((x) => String(x) === String(cour))) vals = [cour, ...vals];
    for (const v of vals) {
      const o = document.createElement("option");
      o.value = String(v); o.textContent = libelleOption(c, v, T);
      sel.appendChild(o);
    }
    sel.addEventListener("change", () => { ctx.poser(c, sel.value, true); });
    ligne.append(lib, sel);
    const ecrire = () => { const v = ctx.valeurs()[c.cle]; sel.value = v === undefined ? "" : String(v); };
    ecrire();
    return { c, el: ligne, ecrire, lire: () => ctx.poser(c, sel.value, false) };
  }

  if (sorte === "case") {
    const k = document.createElement("input");
    k.type = "checkbox"; k.id = ident; k.className = "pl-rg-coche";
    k.addEventListener("change", () => { ctx.poser(c, k.checked, true); });
    ligne.append(k, lib);
    const ecrire = () => { k.checked = ctx.valeurs()[c.cle] === true; };
    ecrire();
    return { c, el: ligne, ecrire, lire: () => ctx.poser(c, k.checked, false) };
  }

  if (sorte === "couleur") {
    const k = document.createElement("input");
    k.type = "color"; k.id = ident; k.className = "pl-rg-teinte";
    // input : la valeur suit le sélecteur ; change (sélecteur refermé) : aperçu.
    k.addEventListener("input", () => { ctx.poser(c, k.value, false); });
    k.addEventListener("change", () => { ctx.poser(c, k.value, true); });
    ligne.append(lib, k);
    const ecrire = () => { k.value = ctx.valeurs()[c.cle] || "#000000"; };
    ecrire();
    return { c, el: ligne, ecrire, lire: () => ctx.poser(c, k.value, false) };
  }

  if (sorte === "texte") {
    const k = document.createElement("input");
    k.type = "text"; k.id = ident; k.className = "pl-rg-saisie"; k.spellcheck = false;
    k.addEventListener("change", () => { ctx.poser(c, k.value, true); });
    ligne.append(lib, k);
    const ecrire = () => { k.value = ctx.valeurs()[c.cle] == null ? "" : String(ctx.valeurs()[c.cle]); };
    ecrire();
    return { c, el: ligne, ecrire, lire: () => ctx.poser(c, k.value, false) };
  }
  return null;                                    // « aucun » : opaque, jamais montré
}

export function initDialogueReglage(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  let ouvert = null;             // le dialogue affiché (générique OU sur mesure) : {fermer(role), identite, surRenduReel}

  // Un seul dialogue de réglage à la fois, tous éditeurs confondus : les éditeurs sur mesure (mod-courbes.js) passent
  // par ces deux fonctions pour profiter des mêmes crochets (rendu réel, document changé).
  PL.prendreReglage = function prendreReglage(etat) {
    if (ouvert && ouvert !== etat) ouvert.fermer("annuler");   // l'ancien s'annule (et rend le rendu réel)
    ouvert = etat;
  };
  PL.libererReglage = function libererReglage(etat) { if (ouvert === etat) ouvert = null; };

  // L'aperçu posé est remplacé par le rendu réel dès que le cycle repasse (zoom, autre commande) : on le redemande à
  // la nouvelle taille tant que le dialogue est ouvert et la case cochée.
  PL.surRendu.push(() => { if (ouvert && ouvert.surRenduReel) ouvert.surRenduReel(); });
  // Document fermé, autre document actif ou moteur relancé : le dialogue n'a plus de cible.
  if (PL.surDoc) PL.surDoc.push((doc) => {
    if (ouvert && identiteDocument(doc, PL.etat.generation) !== ouvert.identite) ouvert.fermer("orphelin");
  });

  PL.ouvrirReglage = function ouvrirReglage(entree) {
    if (!entree || !entree.id) return;
    if (ouvert) ouvert.fermer("annuler");          // un seul à la fois : l'ancien s'annule (et rend le rendu réel)
    ouvert = construire(entree);
  };

  function construire(entree) {
    const id = entree.id;
    const champs = Array.isArray(entree.champs) ? entree.champs : [];
    const visibles = champsVisibles(champs);
    const avecApercu = estFamilleApercu(id);
    const initiales = valeursInitiales(champs);
    let valeurs = { ...initiales };
    let apercuPose = false;      // une image d'aperçu est à l'écran (Annuler doit rendre le rendu réel)
    let minuterie = null;
    let fini = false;
    const etat = { identite: identiteDocument(PL.etat.doc, PL.etat.generation) };

    const titre = titreDialogue(entree.libelle || humaniser(id.slice(id.lastIndexOf(".") + 1)));
    const coq = coquilleReglage(PL, {
      titre, avecApercu,
      valider: () => valider(),
      annuler: () => fermer("annuler"),
      reinitialiser: () => reinitialiser(),
      surCaseApercu: (coche) => surCaseApercu(coche),
    });
    const { corps, erreur } = coq;

    // `poser` est une déclaration de fonction (hissée) ; `valeurs` est relu à chaque appel (poser le remplace).
    const ctxControles = { T, valeurs: () => valeurs, poser };
    const controle = (c) => fabriquerControle(c, ctxControles);

    /* contrôles : un par champ visible ; chacun sait se réécrire depuis `valeurs` et relire ses bornes */
    const controles = [];
    for (const c of visibles) {
      const ctl = controle(c);
      if (ctl) { controles.push(ctl); corps.appendChild(ctl.el); }
    }
    corps.appendChild(erreur);

    // Une saisie : coercée puis rangée ; une case peut changer les bornes d'autres champs (colorisation) : tous les
    // champs numériques relisent alors leurs bornes et leur valeur est ramenée dedans.
    function poser(c, brut, apercu, depuisLeCurseur = false) {
      const avant = valeurs[c.cle];
      valeurs = { ...valeurs, [c.cle]: coercer(c, brut, valeurs) };
      if (controleDe(c) === "case" && avant !== valeurs[c.cle]) {
        for (const x of controles) {
          const s = controleDe(x.c);
          if (s === "curseur" || s === "nombre") valeurs[x.c.cle] = coercer(x.c, valeurs[x.c.cle], valeurs);
        }
        controles.forEach((x) => x.ecrire());
      } else {
        // Le champ qui vient d'être saisi affiche la valeur coercée (« 3,7 » -> 3.7, 5000 -> 1000) ; pendant le glisser
        // d'un curseur, son champ numérique suit.
        const ctl = controles.find((x) => x.c === c);
        if (ctl) ctl.ecrire(depuisLeCurseur);
      }
      if (apercu) planifier();
    }

    /* aperçu moteur */
    const demander = derniereGagne((corpsApercu) => PL.api("POST", "/apercu", corpsApercu, 0, true));
    const caseApercu = coq.caseApercu;
    const occupe = coq.occupe;
    const montrerErreur = coq.montrerErreur;
    function apercuActif() { return avecApercu && caseApercu && caseApercu.checked && !fini && !!PL.etat.doc; }

    function planifier() {
      clearTimeout(minuterie);
      if (!apercuActif()) return;
      minuterie = setTimeout(lancerApercu, DELAI_APERCU);
    }


    async function lancerApercu() {
      if (!apercuActif()) return;
      const envoyes = parametres(champs, valeurs);
      const voulu = PL.vue.maxSideVoulu();             // gardé : la vue a pu zoomer pendant le calcul
      const maxSide = maxSideRequete(voulu, PL.etat.doc);
      occupe(true);
      const r = await demander({ etapes: [{ command: id, params: envoyes }], maxSide });
      if (r.perime) return;                             // une demande plus récente (ou la fermeture) a pris la main
      occupe(demander.enVol());
      if (fini || !apercuActif()) return;
      if (r.erreur) { montrerErreur(T("photolab.reglage.erreur_apercu") + " " + (r.erreur.message || "")); return; }
      let image;
      try { image = await chargerImage(r.valeur.url); } catch (e) {
        montrerErreur(T("photolab.reglage.erreur_apercu")); return;
      }
      if (fini || !apercuActif()) return;
      montrerErreur("");
      PL.vue.poserApercu(image, voulu);
      apercuPose = true;
      // Le moteur borne en silence (rayon 5000 -> 1000) : le formulaire montre ce qui a été appliqué.
      const res = r.valeur && Array.isArray(r.valeur.resultats) ? r.valeur.resultats[0] : null;
      const patch = valeursAppliquees(champs, envoyes, valeurs, res && res.filter);
      if (Object.keys(patch).length) {
        valeurs = { ...valeurs, ...patch };
        controles.forEach((x) => { if (x.c.cle in patch) x.ecrire(); });
      }
    }

    etat.surRenduReel = () => {
      // Le rendu réel vient de recouvrir l'aperçu : on le redemande (à la taille de la vue courante).
      if (!apercuActif()) return;
      apercuPose = false;
      planifier();
    };

    function surCaseApercu(coche) {
      if (coche) { planifier(); return; }
      clearTimeout(minuterie);
      demander.annuler();
      occupe(false);
      montrerErreur("");
      if (apercuPose) { apercuPose = false; PL.cycle(); }      // rendu réel
    }

    function reinitialiser() {
      valeurs = { ...initiales };
      controles.forEach((x) => x.ecrire());
      montrerErreur("");
      planifier();
    }

    function fermer(role) {
      if (fini) return;
      fini = true;
      clearTimeout(minuterie);
      demander.annuler();
      coq.retirer();
      if (ouvert === etat) ouvert = null;
      if (role === "ok") {
        // Par la file FIFO TOUT DE SUITE (l'aperçu en vol est déjà périmé par annuler()) : un Ctrl+Z tapé juste après
        // passe derrière le filtre. Le cycle qui suit pose le rendu réel ; en cas d'échec il n'y a pas de cycle, et un
        // aperçu resté à l'écran ferait croire le filtre appliqué : on relit le vrai document.
        const p = parametres(champs, valeurs);
        const apercuAEffacer = apercuPose;
        PL.executer(id, p).then((r) => { if (!(r && r.ok) && apercuAEffacer) PL.cycle(); });
      } else if (role === "annuler" && apercuPose) {
        PL.cycle();
      }
    }
    etat.fermer = fermer;

    function valider() {
      controles.forEach((x) => x.lire());            // une saisie en cours (Entrée sans « change ») compte
      fermer("ok");
    }

    /* pose : en haut à droite de la scène */
    coq.placer();

    planifier();                                       // aperçu des valeurs de départ, comme photocraft
    return etat;
  }
}
