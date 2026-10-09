// mod-outils.js — la barre d'outils de gauche (B3) : 20 emplacements en 4 sections (ordre de `Tool::ALL` de photocraft,
// inventaire B §2), flyouts des emplacements groupés, lettres au clavier, pastilles de couleur et barre d'options.
// Données et règles PURES exportées (qa/outils.test.mjs) ; initOutils(PL) les branche sur le DOM.
import { optionsPeinture } from "./mod-peinture.js";
import { MODES_FUSION } from "./mod-calques.js";

// Chaque outil : {id, lettre, icone (fichier de icones/), p2 (actif dans cet écran ; sinon visible, grisé, « bientôt »)}.
// Les noms d'icônes sont ceux des fichiers de icones/ (copiés de photocraft, avec les substitutions de B1 :
// hash.svg, history.svg, trash-2.svg, sliders.svg) ; le banc vérifie que chacun existe.
export const EMPLACEMENTS = [
  // section 1 : déplacement, sélections, recadrage, mesure
  [{ id: "move", lettre: "V", icone: "move", p2: true }],
  [{ id: "rectMarquee", lettre: "M", icone: "rectangle-horizontal", p2: true }, { id: "ellipseMarquee", lettre: "M", icone: "circle", p2: true }],
  [{ id: "lasso", lettre: "L", icone: "lasso", p2: true }, { id: "polygonLasso", lettre: "L", icone: "pentagon", p2: true }],
  [{ id: "magicWand", lettre: "W", icone: "wand", p2: true }, { id: "quickSelection", lettre: "W", icone: "lasso-select", p2: true }, { id: "objectSelection", lettre: "W", icone: "scan", p2: false }],
  [{ id: "crop", lettre: "C", icone: "crop", p2: true }, { id: "slice", lettre: "C", icone: "scissors", p2: false }, { id: "sliceSelect", lettre: "C", icone: "mouse-pointer-2", p2: false }],
  [{ id: "eyedropper", lettre: "I", icone: "pipette", p2: true }, { id: "ruler", lettre: "I", icone: "ruler", p2: false }, { id: "note", lettre: "I", icone: "message-square", p2: false }, { id: "count", lettre: "I", icone: "hash", p2: false }],
  // section 2 : peinture et retouche (P3b)
  [{ id: "spotHealing", lettre: "J", icone: "bandage", p2: true }, { id: "healing", lettre: "J", icone: "bandage", p2: true }, { id: "patch", lettre: "J", icone: "bandage", p2: false }],
  [{ id: "brush", lettre: "B", icone: "brush", p2: true }, { id: "pencil", lettre: "B", icone: "pencil", p2: true }, { id: "mixerBrush", lettre: "B", icone: "brush", p2: true }],
  [{ id: "cloneStamp", lettre: "S", icone: "stamp", p2: true }],
  [{ id: "historyBrush", lettre: "Y", icone: "history", p2: true }],
  [{ id: "eraser", lettre: "E", icone: "eraser", p2: true }, { id: "backgroundEraser", lettre: "E", icone: "eraser-background", p2: true }, { id: "magicEraser", lettre: "E", icone: "eraser-magic", p2: true }],
  [{ id: "gradient", lettre: "G", icone: "blend", p2: true }, { id: "paintBucket", lettre: "G", icone: "paint-bucket", p2: true }],
  [{ id: "blur", lettre: "", icone: "droplet", p2: true }, { id: "sharpen", lettre: "", icone: "triangle", p2: true }, { id: "smudge", lettre: "", icone: "pointer", p2: true }],
  [{ id: "dodge", lettre: "O", icone: "sun", p2: true }, { id: "burn", lettre: "O", icone: "flame", p2: true }, { id: "sponge", lettre: "O", icone: "cloud", p2: true }],
  // section 3 : tracés, texte, formes
  // t156 : plume, texte, sélection de tracé et formes (mod-trace, mod-texte, mod-formes)
  [{ id: "pen", lettre: "P", icone: "pen-tool", p2: true }],
  [{ id: "type", lettre: "T", icone: "type", p2: true }],
  [{ id: "pathSelection", lettre: "A", icone: "mouse-pointer-2", p2: true }],
  [{ id: "rectangle", lettre: "U", icone: "rectangle-horizontal", p2: true }, { id: "ellipseShape", lettre: "U", icone: "circle", p2: true }, { id: "triangle", lettre: "U", icone: "triangle", p2: true }, { id: "polygon", lettre: "U", icone: "pentagon", p2: true }, { id: "line", lettre: "U", icone: "minus", p2: true }, { id: "customShape", lettre: "U", icone: "diamond", p2: true }],
  // section 4 : navigation
  [{ id: "hand", lettre: "H", icone: "hand", p2: true }],
  [{ id: "zoom", lettre: "Z", icone: "search", p2: true }],
];
// t140 : l'id DOM d'un emplacement, d'après son outil PRINCIPAL (le premier) : stable quand le flyout change l'outil montré.
export function idEmplacement(i) { return "pl-outil-" + EMPLACEMENTS[i][0].id; }
export const SECTIONS = [6, 8, 4, 2];          // nombre d'emplacements par section (somme 20)

const TOUS = EMPLACEMENTS.flat();
export const outilDe = (id) => TOUS.find((o) => o.id === id) || null;
export const emplacementDe = (id) => EMPLACEMENTS.findIndex((e) => e.some((o) => o.id === id));
// Clés du dictionnaire en snake_case (test_i18n_l0 : minuscules, chiffres, _) : rectMarquee -> rect_marquee.
const snake = (s) => s.replace(/[A-Z]/g, (c) => "_" + c.toLowerCase());
export const cleNom = (id) => "photolab.outil." + snake(id);

// Tous les outils qui partagent une lettre, dans l'ordre de la barre (la lettre « » n'en forme aucun).
export function groupeDeLettre(lettre) {
  const L = String(lettre || "").toUpperCase();
  return L ? TOUS.filter((o) => o.lettre === L) : [];
}

// Cyclage de photocraft (shortcuts.rs:327-340) : la lettre du groupe de l'outil courant passe à l'outil SUIVANT du
// groupe (si !prefMaj ou Maj tenu) ; sinon, une lettre d'un autre groupe choisit le PREMIER outil du groupe. Les
// outils p2:false sont sautés (cycle circulaire parmi les p2:true) ; aucun outil disponible -> null.
export function outilParLettre(lettre, courant, maj, prefMaj = false) {
  const groupe = groupeDeLettre(lettre);
  if (!groupe.length) return null;
  const dispo = groupe.filter((o) => o.p2);
  if (!dispo.length) return null;
  const i = dispo.findIndex((o) => o.id === courant);
  if (i < 0) return dispo[0].id;                        // autre groupe (ou outil courant non disponible) : premier outil
  if (prefMaj && !maj) return dispo[i].id;              // préférence « Maj pour cycler » : on garde l'outil
  return dispo[(i + 1) % dispo.length].id;
}

// Infobulle : « Nom (V) », « Nom — bientôt » pour un outil à venir. `t` = traducteur (dzT) injecté.
export function infobulle(outil, t = (c) => c) {
  const nom = t(cleNom(outil.id));
  if (!outil.p2) return nom + " — " + t("photolab.outil.bientot");
  return outil.lettre ? nom + " (" + outil.lettre + ")" : nom;
}

/* ───────────── barre d'options ───────────── */

export const MODES_SELECTION = ["replace", "add", "subtract", "intersect"];
// Valeurs initiales (relevé du moteur + plan) : tolérance 32, taille 30, contiguë, recadrage destructif.
export const OPTIONS_DEFAUT = {
  mode: "replace", feather: 0, antiAlias: true,
  tolerance: 32, contiguous: true, sampleAllLayers: false,
  size: 30, deleteCroppedPixels: true,
  autoSelect: false, autoCible: "layer",
};
const opt = (type, cle, extra = {}) => ({ type, cle, libelle: "photolab.option." + snake(cle), ...extra });
const MODE = opt("mode", "mode", { valeurs: MODES_SELECTION });
const CONTOUR = opt("nombre", "feather", { min: 0, max: 250, pas: 1, unite: "px" });
const LISSAGE = opt("case", "antiAlias");
const OPTIONS = {
  rectMarquee: [MODE, CONTOUR, LISSAGE],
  ellipseMarquee: [MODE, CONTOUR, LISSAGE],
  lasso: [MODE, CONTOUR, LISSAGE],
  polygonLasso: [MODE, CONTOUR, LISSAGE],
  magicWand: [MODE, opt("nombre", "tolerance", { min: 0, max: 255, pas: 1 }), LISSAGE, opt("case", "contiguous"), opt("case", "sampleAllLayers")],
  quickSelection: [MODE, opt("nombre", "size", { min: 1, max: 200, pas: 1, unite: "px" }), opt("case", "sampleAllLayers")],
  crop: [opt("case", "deleteCroppedPixels")],
  move: [opt("case", "autoSelect"), opt("choix", "autoCible", { valeurs: ["layer", "group"] })],
};
export const optionsPour = (id) => OPTIONS[id] || [];

// Couleur du moteur (RGBA flottant 0..1) -> « #rrggbb » (bornée, arrondie ; toute entrée invalide = noir).
export function rgbaVersHex(c) {
  if (!Array.isArray(c) || c.length < 3) return "#000000";
  return "#" + [0, 1, 2].map((i) => {
    const x = Number(c[i]);
    const n = Math.round(Math.min(1, Math.max(0, Number.isFinite(x) ? x : 0)) * 255);
    return n.toString(16).padStart(2, "0");
  }).join("");
}

/* ───────────── côté DOM ───────────── */

export function initOutils(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const zone = PL.$("#outils");
  const barre = PL.$("#options");
  PL.etat.options = { ...OPTIONS_DEFAUT };
  PL.etat.prefMaj = false;                       // « Maj pour cycler entre les outils d'une lettre » (Réglages, plus tard)
  PL.etat.couleurs = { fg: "#000000", bg: "#ffffff" };
  PL.surOutil = [];                              // crochets (id) appelés au changement d'outil
  let minutLong = null;                          // minuterie de l'appui long (flyout), UNE à la fois pour toute la barre
  const annulerLong = () => { clearTimeout(minutLong); minutLong = null; };
  const montre = {};                             // index d'emplacement -> id de l'outil affiché
  EMPLACEMENTS.forEach((e, i) => { montre[i] = (e.find((o) => o.p2) || e[0]).id; });

  /* barre d'outils */
  zone.textContent = "";
  let idx = 0;
  const boutons = [];
  SECTIONS.forEach((n, s) => {
    if (s > 0) { const sep = document.createElement("div"); sep.className = "sep"; zone.appendChild(sep); }
    for (let k = 0; k < n; k++, idx++) {
      const i = idx;
      const b = document.createElement("button");
      b.type = "button"; b.dataset.emplacement = String(i);
      b.id = idEmplacement(i);                                 // t140 : id stable (fiches didactiques), d'après l'outil principal
      if (EMPLACEMENTS[i].length > 1) b.classList.add("groupe-outils");     // marque d'angle (CSS) : un flyout existe
      b.innerHTML = '<span class="ico"></span>';
      zone.appendChild(b);
      boutons.push(b);
      gestes(b, i);
    }
  });
  rafraichirBoutons();

  function rafraichirBoutons() {
    boutons.forEach((b, i) => {
      const o = outilDe(montre[i]);
      b.dataset.outil = o.id;
      b.title = infobulle(o, T);
      b.setAttribute("aria-label", b.title);
      b.setAttribute("aria-pressed", o.id === PL.etat.outil ? "true" : "false");
      b.classList.toggle("bientot", !o.p2);
      b.classList.toggle("actif", o.id === PL.etat.outil);
      const ico = b.querySelector(".ico");
      if (ico.dataset.nomIcone !== o.icone) {
        ico.dataset.nomIcone = o.icone; ico.textContent = "";
        PL.icone(o.icone).then((svg) => { if (ico.dataset.nomIcone === o.icone) ico.innerHTML = svg; });
      }
    });
  }

  // Clic = outil de l'emplacement ; clic droit ou appui > 350 ms sur un emplacement groupé = flyout.
  function gestes(b, i) {
    let long = false;
    b.addEventListener("pointerdown", (ev) => {
      if (ev.button !== 0) return;
      long = false; annulerLong();
      if (EMPLACEMENTS[i].length > 1) minutLong = setTimeout(() => { minutLong = null; long = true; ouvrirFlyout(i, b); }, 350);
    });
    // M4 : pointercancel (geste repris par le navigateur) annule aussi l'appui long
    for (const nom of ["pointerup", "pointerleave", "pointercancel"]) b.addEventListener(nom, annulerLong);
    b.addEventListener("click", () => { if (long) { long = false; return; } choisir(montre[i], true); });
    b.addEventListener("contextmenu", (ev) => {
      ev.preventDefault();
      if (EMPLACEMENTS[i].length > 1) ouvrirFlyout(i, b);
    });
  }

  // Choisir un outil. Un outil « bientôt » reste sélectionnable dans le flyout mais ne devient pas l'outil courant.
  function choisir(id, depuisClic = false) {
    const o = outilDe(id);
    if (!o) return false;
    if (!o.p2) { if (depuisClic) PL.signaler(infobulle(o, T)); return false; }
    PL.etat.outil = id;
    montre[emplacementDe(id)] = id;
    rafraichirBoutons();
    construireOptions();
    curseur();
    PL.surOutil.forEach((f) => f(id));
    return true;
  }
  PL.choisirOutil = choisir;

  // Curseur du canevas pour l'outil courant (la main temporaire — Espace tenu — prime). Exposé : la vue le rappelle
  // après un panoramique ou le relâchement d'Espace.
  function curseur() {
    const c = PL.$("#toile");
    if (!c) return;
    const o = PL.etat.outil;
    c.style.cursor = PL.vue && PL.vue.mainTemporaire ? "grab"
      : o === "hand" ? "grab" : o === "zoom" ? "zoom-in" : o === "move" ? "default" : "crosshair";
  }
  PL.curseur = curseur;

  /* flyout */
  let flyout = null;
  function fermerFlyout() { annulerLong(); if (flyout) { flyout.remove(); flyout = null; } }
  function ouvrirFlyout(i, bouton) {
    fermerFlyout();
    const f = document.createElement("div");
    f.className = "flyout"; f.setAttribute("role", "menu");
    EMPLACEMENTS[i].forEach((o) => {
      const l = document.createElement("button");
      l.type = "button"; l.className = "flyout-ligne" + (o.p2 ? "" : " bientot");
      l.setAttribute("role", "menuitem");
      l.innerHTML = '<span class="puce"></span><span class="ico"></span><span class="nom"></span><span class="lettre"></span>';
      l.querySelector(".puce").textContent = o.id === PL.etat.outil ? "●" : "";
      l.querySelector(".nom").textContent = T(cleNom(o.id)) + (o.p2 ? "" : " — " + T("photolab.outil.bientot"));
      l.querySelector(".lettre").textContent = o.lettre;
      PL.icone(o.icone).then((svg) => { l.querySelector(".ico").innerHTML = svg; });
      l.addEventListener("click", () => {
        if (o.p2) choisir(o.id); else PL.signaler(infobulle(o, T));
        fermerFlyout();
      });
      f.appendChild(l);
    });
    document.body.appendChild(f);
    const r = bouton.getBoundingClientRect();
    f.style.left = Math.round(r.right + 6) + "px";
    f.style.top = Math.min(Math.round(r.top), Math.max(6, innerHeight - f.offsetHeight - 6)) + "px";
    flyout = f;
  }
  document.addEventListener("pointerdown", (ev) => { if (flyout && !flyout.contains(ev.target)) fermerFlyout(); }, true);
  document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") fermerFlyout(); });
  window.addEventListener("blur", fermerFlyout);

  /* lettres au clavier (hors champ de saisie, hors raccourcis Ctrl/Alt/Cmd) */
  const enSaisie = (ev) => ev.target && (/^(INPUT|TEXTAREA|SELECT)$/.test(ev.target.tagName || "") || ev.target.isContentEditable);
  document.addEventListener("keydown", (ev) => {
    // M5 : pas de répétition automatique de touche, ni pendant qu'un menu ou un flyout est ouvert
    if (ev.repeat || enSaisie(ev) || ev.ctrlKey || ev.metaKey || ev.altKey || ev.key.length !== 1) return;
    if (document.querySelector(".menu-panneau, .flyout")) return;
    const k = ev.key.toUpperCase();
    if (k === "X") { ev.preventDefault(); echanger(); return; }
    if (k === "D") { ev.preventDefault(); parDefaut(); return; }
    const id = outilParLettre(k, PL.etat.outil, ev.shiftKey, PL.etat.prefMaj);
    if (id) { ev.preventDefault(); choisir(id); }
  });

  /* pastilles de couleur */
  const pastilles = document.createElement("div");
  pastilles.className = "pastilles";
  pastilles.innerHTML = '<button type="button" class="pastille-bg"></button><button type="button" class="pastille-fg"></button>'
    + '<button type="button" class="pastille-x" title=""></button>'
    + '<button type="button" class="pastille-d" title=""></button>'
    + '<input type="color" class="pastille-choix" tabindex="-1" aria-hidden="true">';
  zone.appendChild(pastilles);
  const pFg = PL.$(".pastille-fg", pastilles), pBg = PL.$(".pastille-bg", pastilles);
  const pX = PL.$(".pastille-x", pastilles), pD = PL.$(".pastille-d", pastilles), choix = PL.$(".pastille-choix", pastilles);
  pFg.title = T("photolab.couleur.avant"); pBg.title = T("photolab.couleur.arriere");
  pX.title = T("photolab.couleur.echanger") + " (X)"; pD.title = T("photolab.couleur.defaut") + " (D)";
  for (const b of [pFg, pBg, pX, pD]) b.setAttribute("aria-label", b.title);
  pX.textContent = "⇄"; pD.textContent = "◧";
  function dessinerPastilles() {
    pFg.style.background = PL.etat.couleurs.fg; pBg.style.background = PL.etat.couleurs.bg;
  }
  dessinerPastilles();
  PL.relireCouleurs = async function relireCouleurs() {
    try {
      const s = await PL.get("/session");
      if (s && s.foreground) PL.etat.couleurs.fg = rgbaVersHex(s.foreground);
      if (s && s.background) PL.etat.couleurs.bg = rgbaVersHex(s.background);
      dessinerPastilles();
      (PL.surCouleurs || []).forEach((f) => f(PL.etat.couleurs));     // panneau Couleur (C2)
    } catch (e) { /* le moteur a déjà été signalé par mod-api */ }
  };
  async function commande(command, params = {}) {
    try { await PL.post("/executer", { command, params }); await PL.relireCouleurs(); } catch (e) { /* signalé par mod-api */ }
  }
  const echanger = () => commande("tools.swapColors");
  const parDefaut = () => commande("tools.defaultColors");
  pX.addEventListener("click", echanger);
  pD.addEventListener("click", parDefaut);
  let cible = "foreground";
  function choisirCouleur(quelle) {
    cible = quelle;
    choix.value = quelle === "foreground" ? PL.etat.couleurs.fg : PL.etat.couleurs.bg;
    // M8 : un <input hidden> n'a pas de boîte, donc pas de sélecteur ; il reste RENDU (invisible, 1 px) et est replacé près
    // de la pastille. showPicker() d'abord, click() en repli (navigateurs anciens).
    const r = (quelle === "foreground" ? pFg : pBg).getBoundingClientRect();
    choix.style.left = Math.round(r.right) + "px"; choix.style.top = Math.round(r.bottom) + "px";
    try { choix.showPicker(); } catch (e) { choix.click(); }
  }
  pFg.addEventListener("click", () => choisirCouleur("foreground"));
  pBg.addEventListener("click", () => choisirCouleur("background"));
  choix.addEventListener("change", () => commande("tools.setColors", { [cible]: choix.value }));

  /* barre d'options selon l'outil */
  // t155 : un outil de peinture a SES réglages (PL.optionsPeintureDe, mod-peinture), comme dans l'application de
  // référence où chaque outil garde sa taille ; les autres partagent PL.etat.options.
  function construireOptions() {
    barre.textContent = "";
    const nom = document.createElement("span");
    nom.className = "opt-nom"; nom.textContent = T(cleNom(PL.etat.outil));
    barre.appendChild(nom);
    // t156 : un module qui a sa propre barre (formes, texte, plume) la déclare dans PL.barresOutils.
    if (PL.barresOutils && PL.barresOutils[PL.etat.outil]) { PL.barresOutils[PL.etat.outil](barre); return; }
    const peint = optionsPeinture(PL.etat.outil);
    if (peint.length && PL.optionsPeintureDe) {
      const store = PL.optionsPeintureDe(PL.etat.outil);
      for (const o of peint) barre.appendChild(champ(o, store));
      return;
    }
    for (const o of optionsPour(PL.etat.outil)) barre.appendChild(champ(o, PL.etat.options));
  }
  PL.reconstruireOptions = construireOptions;
  // t156 : outils actifs pour Édition › Rechercher (nom affiché).
  PL.outilsCherchables = () => EMPLACEMENTS.flat().filter((o) => o.p2).map((o) => ({ id: o.id, nom: T(cleNom(o.id)) }));
  function champ(o, store) {
    // M3 : <label> seulement pour un contrôle unique (case, nombre, liste) ; un groupe de boutons n'est pas « étiqueté » par un clic.
    const w = document.createElement(o.type === "case" || o.type === "nombre" || o.type === "liste" ? "label" : "div");
    w.className = "opt opt-" + o.type;
    w.dataset.cle = o.cle;
    const lib = document.createElement("span");
    lib.textContent = T(o.libelle);
    const val = store[o.cle];
    if (o.type === "case") {
      const c = document.createElement("input"); c.type = "checkbox"; c.checked = !!val;
      c.addEventListener("change", () => { store[o.cle] = c.checked; });
      w.append(c, lib);
    } else if (o.type === "nombre") {
      const n = document.createElement("input"); n.type = "number";
      n.min = o.min; n.max = o.max; n.step = o.pas; n.value = val;
      n.addEventListener("change", () => {
        const x = Math.min(o.max, Math.max(o.min, Math.round(Number(n.value)) || 0));
        n.value = x; store[o.cle] = x;
      });
      w.append(lib, n);
      if (o.unite) { const u = document.createElement("span"); u.className = "opt-unite"; u.textContent = o.unite; w.append(u); }
    } else if (o.type === "liste") {
      // t155 : sélecteur (mode de fusion, échantillon, gamme…) ; la fusion reprend les libellés du panneau Calques.
      const s = document.createElement("select");
      for (const v of o.valeurs) {
        const op = document.createElement("option"); op.value = v;
        op.textContent = o.fusion ? T(MODES_FUSION.find((m) => m.id === v).cle) : T(o.libelle + "." + snake(v));
        s.appendChild(op);
      }
      s.value = val;
      s.addEventListener("change", () => { store[o.cle] = s.value; });
      w.append(lib, s);
    } else {
      // mode (4 boutons exclusifs) ou choix (liste)
      const g = document.createElement("span"); g.className = "opt-groupe";
      for (const v of o.valeurs) {
        const b = document.createElement("button"); b.type = "button";
        b.textContent = T(o.libelle + "." + snake(v));
        b.classList.toggle("actif", val === v);
        b.addEventListener("click", () => {
          store[o.cle] = v;
          PL.$$("button", g).forEach((x) => x.classList.toggle("actif", x === b));
        });
        g.appendChild(b);
      }
      w.append(lib, g);
    }
    return w;
  }

  construireOptions();
  curseur();
  // Pas d'écouteur de langue : dzSetLang recharge la page, les textes sont donc relus à chaque montage.
}
