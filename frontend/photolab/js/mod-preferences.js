// mod-preferences.js — t159 (parité L9) : Édition › Préférences. Un dialogue à sections (l'ordre du menu), chaque
// entrée ouvre SA section ; OK enregistre par PUT /api/photolab/preferences (dossier de données Deepotus), Annuler ne
// change rien. Aucune préférence n'est envoyée au moteur (prefs.* reste refusé) : ce sont des réglages d'ÉCRAN, lus par
// les modules au moment où ils servent (PL.prefs.v). Sections et clés reprennent les noms de photocraft (prefs.get),
// énumérations et bornes celles que prefs.set annonce — copie de backend/app/services/photolab_preferences.py (SCHEMA),
// comparée par le banc test_photolab_preferences. Fonctions PURES exportées (qa/preferences.test.mjs).
import { ouvrirDialogue } from "./mod-fichier.js";

const UNITES = ["pixels", "inches", "cm", "mm", "points", "picas", "percent"];
const STYLES_TRAIT = ["lines", "dashedLines", "dots"];
// [type, défaut, valeurs | bornes] ; « couleur » = #rrggbb.
export const SCHEMA = {
  general: {
    zoomWithScrollWheel: ["bool", false],
    resizeImageDuringPlace: ["bool", true],
    alwaysCreateSmartObjectsWhenPlacing: ["bool", true],
  },
  interface: {
    canvasColor: ["enum", "default", ["default", "black", "darkGray", "mediumGray", "lightGray", "custom"]],
    canvasCustomColor: ["couleur", "#282828"],
    canvasBorder: ["enum", "line", ["dropShadow", "line", "none"]],
    showTooltips: ["bool", true],
    showMenuColors: ["bool", true],
  },
  workspace: {
    largeTabs: ["bool", false],
    rememberWorkspaceChanges: ["bool", true],
  },
  tools: {
    useShiftKeyForToolSwitch: ["bool", false],
    overscroll: ["bool", true],
    zoomClickedPointToCenter: ["bool", false],
  },
  fileHandling: {
    lowercaseExtension: ["bool", true],
  },
  export: {
    quickExportFormat: ["enum", "png", ["png", "jpg", "webp"]],
    jpegQuality: ["int", 85, [1, 100]],
    quickExportLocation: ["enum", "download", ["ask", "download", "library"]],
  },
  cursors: {
    painting: ["enum", "normalTip", ["standard", "precise", "normalTip", "fullSizeTip"]],
    other: ["enum", "standard", ["standard", "precise"]],
    showCrosshairInBrushTip: ["bool", false],
    showOnlyCrosshairWhilePainting: ["bool", false],
  },
  transparencyAndGamut: {
    gridSize: ["enum", "medium", ["none", "small", "medium", "large"]],
    gridColors: ["enum", "theme", ["theme", "light", "medium", "dark", "red", "orange", "green", "blue", "purple", "custom"]],
    customLight: ["couleur", "#ffffff"],
    customDark: ["couleur", "#cccccc"],
  },
  unitsAndRulers: {
    rulers: ["enum", "pixels", UNITES],
  },
  guidesGridAndSlices: {
    guideColor: ["couleur", "#4affff"],
    guideStyle: ["enum", "lines", STYLES_TRAIT],
    gridColor: ["couleur", "#8c8c8c"],
    gridStyle: ["enum", "lines", STYLES_TRAIT],
    gridlineEvery: ["num", 1.0, [0.001, 10000]],
    gridUnit: ["enum", "inches", UNITES],
    subdivisions: ["int", 4, [1, 100]],
  },
  type: {
    fontPreview: ["enum", "medium", ["small", "medium", "large", "extraLarge", "huge"]],
    useEscToCommit: ["bool", true],
  },
};
// Les 18 sections dans l'ordre du menu Édition › Préférences ; celles hors SCHEMA sont explicatives (décision Q1 du
// 09/10/2026 : elles disent en une phrase qui s'en charge).
export const SECTIONS = [
  ["edit.preferences.general", "general"], ["edit.preferences.integrations", "integrations"],
  ["edit.preferences.interface", "interface"], ["edit.preferences.workspace", "workspace"],
  ["edit.preferences.tools", "tools"], ["edit.preferences.historyLog", "historyLog"],
  ["edit.preferences.fileHandling", "fileHandling"], ["edit.preferences.export", "export"],
  ["edit.preferences.performance", "performance"], ["edit.preferences.scratchDisks", "scratchDisks"],
  ["edit.preferences.cursors", "cursors"], ["edit.preferences.transparencyAndGamut", "transparencyAndGamut"],
  ["edit.preferences.unitsAndRulers", "unitsAndRulers"], ["edit.preferences.guidesGridAndSlices", "guidesGridAndSlices"],
  ["edit.preferences.plugIns", "plugIns"], ["edit.preferences.type", "type"],
  ["edit.preferences.enhancedControls", "enhancedControls"], ["edit.preferences.rawDefaults", "rawDefaults"],
];
export const IDS_PREFERENCES = SECTIONS.map(([id]) => id);
// Champs montrés seulement quand une autre valeur les rend utiles (clé -> [clé qui décide, valeur]).
export const SI = {
  "interface.canvasCustomColor": ["interface.canvasColor", "custom"],
  "transparencyAndGamut.customLight": ["transparencyAndGamut.gridColors", "custom"],
  "transparencyAndGamut.customDark": ["transparencyAndGamut.gridColors", "custom"],
  "export.jpegQuality": ["export.quickExportFormat", "jpg"],
};
export const LANGUES_TEXTE = ["type.languageOptions.defaultFeatures", "type.languageOptions.eastAsianFeatures",
  "type.languageOptions.middleEasternFeatures"];

const copie = (o) => JSON.parse(JSON.stringify(o));
// Clés du dictionnaire en minuscules (test_i18n_l0) : zoomWithScrollWheel -> zoom_with_scroll_wheel.
export const snake = (s) => String(s).replace(/[A-Z]/g, (c) => "_" + c.toLowerCase());
export const cleSection = (s) => `photolab.pref.section.${snake(s)}`;
export const clePref = (s, k, v) => `photolab.pref.${snake(s)}.${snake(k)}` + (v === undefined ? "" : `.${snake(v)}`);
export const cleExplication = (s) => `photolab.pref.${snake(s)}.texte`;
// Toutes les clés que le dialogue compose (qa/preferences : chacune existe en fr et en en).
export function clesTextes() {
  const L = SECTIONS.map(([, s]) => cleSection(s));
  for (const [, s] of SECTIONS) if (!SCHEMA[s]) L.push(cleExplication(s));
  for (const [s, cles] of Object.entries(SCHEMA)) for (const [k, spec] of Object.entries(cles)) {
    L.push(clePref(s, k));
    if (spec[0] === "enum") for (const v of spec[2]) L.push(clePref(s, k, v));
  }
  return L;
}

export function etatDefaut() {
  const prefs = {};
  for (const [s, cles] of Object.entries(SCHEMA)) { prefs[s] = {}; for (const [k, spec] of Object.entries(cles)) prefs[s][k] = spec[1]; }
  return { version: 1, prefs, raccourcis: { commandes: {}, outils: {} }, menus: { masques: [], couleurs: {} }, affichage: null,
    texte: { langue: LANGUES_TEXTE[0], composeur: false } };
}

// Une valeur admise par sa spécification (mêmes règles que le pont) ?
export function valeurAdmise(spec, v) {
  const [t, , extra] = spec;
  if (t === "bool") return typeof v === "boolean";
  if (t === "enum") return extra.includes(v);
  if (t === "couleur") return typeof v === "string" && /^#[0-9a-f]{6}$/.test(v);
  if (typeof v !== "number" || !Number.isFinite(v) || (t === "int" && !Number.isInteger(v))) return false;
  return v >= extra[0] && v <= extra[1];
}

// État lu (serveur, autre version, valeur abîmée) -> état complet : toute valeur refusée prend son défaut. Les
// raccourcis, menus, affichage et texte passent tels quels quand ils ont la bonne forme (le pont les a validés).
export function normaliser(brut) {
  const e = etatDefaut();
  if (!brut || typeof brut !== "object") return e;
  const p = brut.prefs || {};
  for (const [s, cles] of Object.entries(SCHEMA)) {
    for (const [k, spec] of Object.entries(cles)) {
      let v = p[s] && p[s][k];
      if (spec[0] === "couleur" && typeof v === "string") v = v.toLowerCase();
      if (v !== undefined && valeurAdmise(spec, v)) e.prefs[s][k] = v;
    }
  }
  const r = brut.raccourcis || {};
  if (r.commandes && typeof r.commandes === "object") e.raccourcis.commandes = { ...r.commandes };
  if (r.outils && typeof r.outils === "object") e.raccourcis.outils = { ...r.outils };
  const m = brut.menus || {};
  if (Array.isArray(m.masques)) e.menus.masques = m.masques.filter((x) => typeof x === "string");
  if (m.couleurs && typeof m.couleurs === "object") e.menus.couleurs = { ...m.couleurs };
  if (brut.affichage && typeof brut.affichage === "object") e.affichage = copie(brut.affichage);
  const t = brut.texte || {};
  if (LANGUES_TEXTE.includes(t.langue)) e.texte.langue = t.langue;
  if (typeof t.composeur === "boolean") e.texte.composeur = t.composeur;
  return e;
}

/* ── ce que les modules lisent ── */

// Transparence : taille d'une case du damier (0 = pas de damier, fond blanc) et ses deux couleurs ; null = le thème.
export const TAILLES_DAMIER = { none: 0, small: 4, medium: 8, large: 16 };
export const COULEURS_DAMIER = {
  theme: null, light: ["#ffffff", "#cccccc"], medium: ["#b3b3b3", "#808080"], dark: ["#666666", "#333333"],
  red: ["#ffffff", "#ffcccc"], orange: ["#ffffff", "#ffe0c2"], green: ["#ffffff", "#ccf2cc"], blue: ["#ffffff", "#cce0ff"],
  purple: ["#ffffff", "#e6ccff"],
};
export function damier(prefs) {
  const t = prefs.transparencyAndGamut;
  const c = t.gridColors === "custom" ? [t.customLight, t.customDark] : COULEURS_DAMIER[t.gridColors] || null;
  return { taille: TAILLES_DAMIER[t.gridSize] ?? 8, c1: c ? c[0] : null, c2: c ? c[1] : null };
}

// Couleur du fond autour du document (null = le thème).
export const FONDS = { default: null, black: "#000000", darkGray: "#282828", mediumGray: "#535353", lightGray: "#a0a0a0" };
export const fondToile = (prefs) => (prefs.interface.canvasColor === "custom" ? prefs.interface.canvasCustomColor : FONDS[prefs.interface.canvasColor] ?? null);

// Pixels du document pour UNE unité (la résolution du document en ppi, sa largeur pour le pourcentage).
export function pxParUnite(unite, ppi, largeur) {
  const p = ppi > 0 ? ppi : 72;
  switch (unite) {
    case "inches": return p;
    case "cm": return p / 2.54;
    case "mm": return p / 25.4;
    case "points": return p / 72;
    case "picas": return p / 6;
    case "percent": return largeur > 0 ? largeur / 100 : 1;
    default: return 1;
  }
}
// Grille : une ligne toutes les N unités, coupée en S subdivisions.
export function pasGrillePrefs(prefs, ppi, largeur) {
  const g = prefs.guidesGridAndSlices;
  const majeur = g.gridlineEvery * pxParUnite(g.gridUnit, ppi, largeur);
  return { majeur, mineur: majeur / g.subdivisions };
}
// Style d'un trait (repères, grille) -> stroke-dasharray SVG ("" = trait plein).
export const tirets = (style) => (style === "dashedLines" ? "6 4" : style === "dots" ? "1 3" : "");

// Défilement au-delà du document désactivé : le document ne quitte pas la vue (centré s'il tient, bords collés sinon).
export function bornerVue(v, doc, vue) {
  const borne = (o, taille, ecran) => (taille <= ecran ? (ecran - taille) / 2 : Math.min(0, Math.max(ecran - taille, o)));
  return { z: v.z, ox: borne(v.ox, doc.w * v.z, vue.w), oy: borne(v.oy, doc.h * v.z, vue.h) };
}
// Zoom sur le point cliqué au centre : la vue v2 (déjà zoomée autour du point) décalée pour l'amener au centre.
export function centrerSur(v2, px, py, vue) {
  return { z: v2.z, ox: v2.ox + (vue.w / 2 - px), oy: v2.oy + (vue.h / 2 - py) };
}

// Curseur des outils de peinture : { css, cercle, reticule } — cercle = facteur du diamètre de la pointe (0 = aucun).
// « normalTip » : la zone où la pointe peint à plus de la moitié de son opacité (dureté 1 = toute la pointe).
export function curseurPeinture(prefs, durete = 1, enTrait = false) {
  const c = prefs.cursors;
  if (c.painting === "standard") return { css: "default", cercle: 0, reticule: false };
  if (c.painting === "precise") return { css: "crosshair", cercle: 0, reticule: false };
  if (enTrait && c.showOnlyCrosshairWhilePainting) return { css: "crosshair", cercle: 0, reticule: false };
  const d = Math.min(1, Math.max(0, Number.isFinite(durete) ? durete : 1));
  return { css: "none", cercle: c.painting === "fullSizeTip" ? 1 : 0.5 + 0.5 * d, reticule: c.showCrosshairInBrushTip };
}
// Curseur des autres outils : « precise » = réticule partout où l'outil n'a pas de curseur propre.
export const curseurAutre = (prefs, css) => (prefs.cursors.other === "precise" && ["default", "zoom-in", ""].includes(css) ? "crosshair" : css);

// Exportation rapide : extension selon la préférence de casse.
export const extension = (prefs, format) => (prefs.fileHandling.lowercaseExtension ? format.toLowerCase() : format.toUpperCase());

// Reprise de ce que le navigateur gardait avant t159 (mod-affichage, mod-texte) dans un état neuf.
export const APERCU_ID = { small: "type.fontPreviewSize.small", medium: "type.fontPreviewSize.medium", large: "type.fontPreviewSize.large",
  extraLarge: "type.fontPreviewSize.extraLarge", huge: "type.fontPreviewSize.huge" };
export function reprendre(etat, affichage, texte) {
  const e = copie(etat);
  if (affichage && typeof affichage === "object") e.affichage = copie(affichage);
  if (texte && typeof texte === "object") {
    const apercu = Object.keys(APERCU_ID).find((k) => APERCU_ID[k] === texte.apercu);
    if (apercu) e.prefs.type.fontPreview = apercu;
    if (LANGUES_TEXTE.includes(texte.langue)) e.texte.langue = texte.langue;
    if (typeof texte.composeur === "boolean") e.texte.composeur = texte.composeur;
  }
  return e;
}

/* ───────────── côté DOM ───────────── */

export function initPreferences(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  let etat = etatDefaut();
  const surChange = [];
  const notifier = () => { for (const f of surChange) { try { f(etat); } catch (e) { console.error(e); } } };

  async function enregistrer(nouveau) {
    const r = await PL.api("PUT", "/preferences", nouveau);
    etat = normaliser(r);
    notifier();
    return etat;
  }
  PL.prefs = {
    get etat() { return etat; },
    get p() { return etat.prefs; },
    v: (section, cle) => etat.prefs[section][cle],
    surChange,
    enregistrer,
    // Un morceau de l'état (raccourcis, menus, affichage, texte) remplacé puis enregistré.
    modifier: (champ, valeur) => enregistrer({ ...copie(etat), [champ]: valeur }),
    // Ce que les modules lisent, calculé sur l'état courant (aucun import croisé : mod-vue, mod-affichage, mod-peinture).
    damier: () => damier(etat.prefs),
    bornerVue: (v, doc, vue) => (etat.prefs.tools.overscroll ? v : bornerVue(v, doc, vue)),
    centrerSur: (v2, px, py, vue) => (etat.prefs.tools.zoomClickedPointToCenter ? centrerSur(v2, px, py, vue) : v2),
    pasGrille: (ppi, largeur) => pasGrillePrefs(etat.prefs, ppi, largeur),
    pxParUnite: (unite, ppi, largeur) => pxParUnite(unite, ppi, largeur),
    tirets,
    curseurPeinture: (durete, enTrait) => curseurPeinture(etat.prefs, durete, enTrait),
    curseurAutre: (css) => curseurAutre(etat.prefs, css),
    extension: (format) => extension(etat.prefs, format),
  };

  async function charger() {
    let r;
    try { r = await PL.get("/preferences"); } catch (e) { return; }
    etat = normaliser(r && r.etat);
    if (r && r.enregistre === false) {
      // t159 : ce que le navigateur gardait (Affichage, Texte) passe une fois dans le dossier de données
      const lire = (k) => { try { return JSON.parse(localStorage.getItem(k) || "null"); } catch (e) { return null; } };
      const affichage = lire("dz-photolab-affichage"), texte = lire("dz-photolab-texte");
      if (affichage || texte) {
        try { await enregistrer(reprendre(etat, affichage, texte)); return; } catch (e) { /* reste au défaut */ }
      }
    }
    notifier();
  }
  PL.prefs.pret = charger();

  /* infobulles : coupées en déplaçant `title` le temps du survol (rendu à la sortie) */
  document.addEventListener("pointerover", (ev) => {
    if (etat.prefs.interface.showTooltips) return;
    const el = ev.target && ev.target.closest ? ev.target.closest("[title]") : null;
    if (!el || !el.title) return;
    el.dataset.dzTitre = el.title;
    el.removeAttribute("title");
    el.addEventListener("pointerout", () => { if (el.dataset.dzTitre != null) { el.title = el.dataset.dzTitre; delete el.dataset.dzTitre; } }, { once: true });
  }, true);

  /* classes et variables d'écran (fond, onglets) */
  surChange.push(() => {
    const p = etat.prefs, racine = document.documentElement;
    const fond = fondToile(p);
    if (fond) racine.style.setProperty("--pl-fond-toile", fond); else racine.style.removeProperty("--pl-fond-toile");
    document.body.classList.toggle("pl-grands-onglets", p.workspace.largeTabs);
    PL.etat.prefMaj = p.tools.useShiftKeyForToolSwitch;
    if (PL.vue && PL.vue.dessiner) PL.vue.dessiner();
    if (PL.curseur) PL.curseur();
    if (PL.menus && PL.menus.redessiner) PL.menus.redessiner();
  });

  /* le dialogue */
  async function confirmer(question, titre, ok) {
    const d = window.__dzDialogue;
    if (d) return d.confirmer(question, { titre, ok });
    return (await ouvrirDialogue(PL, {
      titre,
      construire({ corps }) { const p = document.createElement("p"); p.textContent = question; corps.appendChild(p); },
      boutons: [{ role: "annuler", libelle: T("commun.action.annuler") }, { role: "ok", libelle: ok, principal: true }],
    })) === "ok";
  }
  const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };

  function champ(section, cle, spec, brouillon, rafraichir) {
    const [t, , extra] = spec;
    const lib = T(clePref(section, cle));
    const ligne = el("label", "pl-champ" + (t === "bool" ? " pl-case" : ""));
    ligne.dataset.cle = `${section}.${cle}`;
    let input;
    if (t === "bool") {
      input = el("input"); input.type = "checkbox"; input.checked = brouillon[section][cle];
      input.addEventListener("change", () => { brouillon[section][cle] = input.checked; rafraichir(); });
      ligne.append(input, el("span", null, lib));
      return ligne;
    }
    if (t === "enum") {
      input = el("select");
      for (const v of extra) { const o = el("option", null, T(clePref(section, cle, v))); o.value = v; input.appendChild(o); }
      input.value = brouillon[section][cle];
      input.addEventListener("change", () => { brouillon[section][cle] = input.value; rafraichir(); });
    } else if (t === "couleur") {
      input = el("input"); input.type = "color"; input.value = brouillon[section][cle];
      input.addEventListener("input", () => { brouillon[section][cle] = input.value.toLowerCase(); });
    } else {
      input = el("input"); input.type = "number"; input.min = String(extra[0]); input.max = String(extra[1]);
      input.step = t === "int" ? "1" : "any"; input.value = String(brouillon[section][cle]);
      input.addEventListener("input", () => {
        const n = Number(input.value);
        const ok = input.value !== "" && valeurAdmise(spec, n);
        input.classList.toggle("pl-invalide", !ok);
        if (ok) brouillon[section][cle] = n;
      });
    }
    ligne.append(el("span", null, lib), input);
    return ligne;
  }

  async function ouvrir(sectionInitiale) {
    const brouillon = copie(etat.prefs);
    let section = sectionInitiale || "general";
    let role = null;
    role = await ouvrirDialogue(PL, {
      titre: T("photolab.pref.titre"), classe: "large pl-preferences",
      boutons: [
        { role: "reinitialiser", libelle: T("photolab.pref.reinitialiser") },
        { role: "annuler", libelle: T("commun.action.annuler") },
        { role: "ok", libelle: T("commun.action.valider"), principal: true },
      ],
      construire({ corps }) {
        const nav = el("nav", "pf-sections"), zone = el("div", "pf-zone");
        corps.append(nav, zone);
        const boutons = {};
        for (const [, s] of SECTIONS) {
          const b = el("button", "pf-section", T(cleSection(s))); b.type = "button"; b.dataset.section = s;
          b.addEventListener("click", () => { section = s; dessiner(); });
          boutons[s] = b; nav.appendChild(b);
        }
        const visibles = () => {
          for (const ligne of zone.querySelectorAll(".pl-champ")) {
            const si = SI[ligne.dataset.cle];
            if (si) { const [sec, k] = si[0].split("."); ligne.hidden = brouillon[sec][k] !== si[1]; }
          }
        };
        function dessiner() {
          for (const [s, b] of Object.entries(boutons)) b.classList.toggle("actif", s === section);
          zone.replaceChildren(el("h3", "pf-titre", T(cleSection(section))));
          if (SCHEMA[section]) {
            for (const [k, spec] of Object.entries(SCHEMA[section])) zone.appendChild(champ(section, k, spec, brouillon, visibles));
            if (section === "interface") zone.appendChild(el("p", "pf-note", T("photolab.pref.interface.note")));
            if (section === "export") zone.appendChild(el("p", "pf-note", T("photolab.pref.export.note")));
          } else {
            zone.appendChild(el("p", "pf-note", T(cleExplication(section))));
          }
          visibles();
        }
        dessiner();
        return async (r) => {
          if (r === "reinitialiser") {
            if (!(await confirmer(T("photolab.pref.reinitialiser_q"), T("photolab.pref.reinitialiser"), T("commun.action.reinitialiser")))) return false;
            try { etat = normaliser(await PL.post("/preferences/reinitialiser", {})); notifier(); }
            catch (e) { PL.signaler(e.message || String(e), true); return false; }
            PL.signaler(T("photolab.pref.reinitialisees"));
            return true;
          }
          if (zone.querySelector(".pl-invalide")) { PL.signaler(T("photolab.pref.invalide"), true); return false; }
          try { await enregistrer({ ...copie(etat), prefs: brouillon }); }
          catch (e) { PL.signaler(e.message || String(e), true); return false; }
          return true;
        };
      },
    });
    return role;
  }
  PL.preferences = { ouvrir };
  PL.actions = PL.actions || {};
  for (const [id, s] of SECTIONS) PL.actions[id] = () => ouvrir(s);
}
