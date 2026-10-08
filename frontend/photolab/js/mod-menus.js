// mod-menus.js — la barre de menus du Photolab (B4), GÉNÉRÉE : l'arbre vient du catalogue de photocraft
// (donnees/menus.json : chemin, id, libellés fr/en, raccourci) croisé avec le registre du moteur
// (GET /api/photolab/commandes : quelles commandes existent, lesquelles sont actives, lesquelles ont des paramètres).
// Une entrée que le moteur ne connaît pas, ou que le pont refuse, reste affichée mais « bientôt » : la barre ressemble
// à celle de photocraft sans promettre ce qui n'est pas là. Toute la construction est PURE (qa/menus.test.mjs).

import { champsVisibles, sansEcran, D9, SANS_EDITEUR, OPAQUES, CLES_CACHEES } from "./mod-champs.js";

// Copie, en minuscules, de PREFIXES_REFUSES (backend/app/services/photolab_moteur.py) : le pont refuse ces commandes
// (fichiers, scripts, préférences…), l'écran les traite lui-même ou les marque « bientôt ». Un banc relit le source
// Python et compare : toute dérive rougit.
export const REFUSES = ["file.", "app.", "automate.", "plugin.", "script", "window.", "help.", "edit.preferences",
  "edit.presets", "edit.keyboardshortcuts", "edit.menus", "image.mode.", "brush.presets.import",
  "gradient.presets.import", "prefs.", "measurementlog.export"];

// Entrées de fichier que l'écran exécute LUI-MÊME par ses routes (nouveau, ouvrir depuis la Bibliothèque, fermer,
// enregistrer, exporter) : actives même si le pont refuserait la commande moteur de ce nom.
// t139 : `pl.envoyer` (« Envoyer vers… ») n'est pas du catalogue amont — l'écran l'insère après « Revenir ».
export const TRAITES_PAR_ECRAN = new Set(["file.new", "file.open", "file.close", "file.save", "file.saveAs", "file.export.exportAs",
  "pl.envoyer", "pl.natif.ouvrir", "pl.natif.reprendre",
  // t155 : le groupe Pinceaux (mod-pinceaux, PL.actions) ; window.* reste refusé au moteur
  "window.panel.brushes", "window.panel.brushSettings", "window.panel.cloneSource", "window.panel.toolPresets",
  // t151 : espaces de travail et Fenêtre › <panneau> (mod-espaces : ACTIONS_ESPACE, PANNEAUX, BARRES — banc espaces 5.9)
  "window.workspace.essentials", "window.workspace.photography", "window.workspace.painting", "window.workspace.pixelArt",
  "window.workspace.graphicAndWeb", "window.workspace.motion", "window.workspace.resetWorkspace", "window.workspace.newWorkspace",
  "window.workspace.deleteWorkspace", "window.workspace.lockWorkspace",
  "window.panel.color", "window.panel.properties", "window.panel.adjustments", "window.panel.layers", "window.panel.history",
  "window.panel.navigator", "window.panel.options", "window.panel.tools",
  // t153 : panneaux Nuancier, Dégradés, Motifs, Compositions, Couches, Histogramme, Infos (mod-espaces : PANNEAUX)
  "window.panel.swatches", "window.panel.gradients", "window.panel.patterns", "window.panel.layerComps", "window.panel.channels",
  "window.panel.histogram", "window.panel.info",
  // t154 : transformation manuelle et ses sous-modes (mod-transformer : MODES) ; la validation passe par edit.transform
  "edit.freeTransform", "edit.transform.scale", "edit.transform.rotate", "edit.transform.skew", "edit.transform.distort",
  "edit.transform.perspective",
  // t152 : menu Affichage (mod-affichage : IDS_AFFICHAGE — banc affichage 7.4) ; les commandes moteur des repères
  // (Nouveau repère…, Effacer les repères…) restent au moteur
  "view.zoomIn", "view.zoomOut", "view.fitOnScreen", "view.fitLayersOnScreen", "view.actualPixels", "view.twoHundredPercent",
  "view.printSize", "view.flipHorizontal", "view.screenMode.standard", "view.screenMode.fullScreenWithMenuBar", "view.screenMode.fullScreen",
  "view.extras", "view.show.layerEdges", "view.show.selectionEdges", "view.show.grid", "view.show.guides", "view.show.canvasGuides",
  "view.show.pixelGrid", "view.show.brushPreview", "view.show.all", "view.show.showExtrasOptions", "view.rulers", "view.snap",
  "view.snapTo.guides", "view.snapTo.grid", "view.snapTo.layers", "view.snapTo.documentBounds", "view.snapTo.all", "view.lockGuides",
  "view.pixelArtPreview"]);
// … dont celles qui n'ont de sens qu'avec un document ouvert (grisées sur l'écran d'accueil).
export const NECESSITE_DOC = new Set(["file.close", "file.save", "file.saveAs", "file.export.exportAs", "pl.envoyer", "pl.natif.ouvrir",
  // t152 : les zooms d'Affichage
  "view.zoomIn", "view.zoomOut", "view.fitOnScreen", "view.fitLayersOnScreen", "view.actualPixels", "view.twoHundredPercent", "view.printSize",
  // t154 : la transformation manuelle vise le calque actif
  "edit.freeTransform", "edit.transform.scale", "edit.transform.rotate", "edit.transform.skew", "edit.transform.distort",
  "edit.transform.perspective"]);

// Le registre arrive en tableau ; on tolère {commands:[…]}.
export function indexRegistre(registre) {
  const liste = Array.isArray(registre) ? registre : (registre && Array.isArray(registre.commands) ? registre.commands : []);
  const m = new Map();
  for (const c of liste) if (c && c.id) m.set(c.id, c);
  return m;
}

// Champs d'une entrée du registre (t138 : GET /commandes les structure). Un pont plus ancien ne les envoie pas : une
// description vide ou « {} » vaut alors « aucun champ », toute autre vaut null (inconnu -> dialogue, jamais une
// exécution à l'aveugle avec les défauts du moteur).
function champsDe(r) {
  if (!r) return null;
  if (Array.isArray(r.champs)) return r.champs;
  const s = String(r.params == null ? "" : r.params).replace(/\s+/g, "");
  return s === "" || s === "{}" ? [] : null;
}

// Styles de calque à dialogue sur mesure (B6) : les 10 effets et les options de fusion. Les autres layer.layerStyle.*
// (effacer, copier, coller, lumière globale…) restent des commandes ordinaires.
export const STYLES = new Set(["dropShadow", "innerShadow", "outerGlow", "innerGlow", "stroke", "colorOverlay", "gradientOverlay",
  "patternOverlay", "bevelEmboss", "satin", "blendingOptions"]);
const PREFIXE_REGLAGE = "layer.newAdjustmentLayer.";
const PREFIXE_STYLE = "layer.layerStyle.";

// Familles à éditeur sur mesure, aiguillées AVANT le dialogue générique : courbes | niveaux | reglage | style | generique.
export function aiguillage(id) {
  const s = typeof id === "string" ? id : "";
  if (s === "image.adjustments.curves") return "courbes";
  if (s === "image.adjustments.levels") return "niveaux";
  if (s.startsWith(PREFIXE_REGLAGE) && s.length > PREFIXE_REGLAGE.length) return "reglage";
  if (s.startsWith(PREFIXE_STYLE) && STYLES.has(s.slice(PREFIXE_STYLE.length))) return "style";
  return "generique";
}

// Fonction de l'écran qui ouvre chaque famille (définies par B2-B6, absentes avant).
const OUVREURS = { courbes: "ouvrirCourbes", niveaux: "ouvrirNiveaux", reglage: "creerReglage", style: "ouvrirStyles", generique: "ouvrirReglage" };

// Où va une entrée « dialogue », selon les fonctions que l'écran possède (dispo = PL) : la famille sur mesure si son
// éditeur existe ; sinon le dialogue générique s'il existe et qu'il y a quelque chose à y montrer ; sinon « bientot »
// (le même message que les entrées grisées).
export function cibleDialogue(entree, dispo) {
  const d = dispo || {};
  const a = aiguillage(entree && entree.id);
  if (a !== "generique" && d[OUVREURS[a]]) return a;
  const champs = entree && entree.champs;
  // champs inconnus (pont ancien) : le générique ne saurait quoi montrer
  if (d.ouvrirReglage && Array.isArray(champs) && champsVisibles(champs).length) return "generique";
  return "bientot";
}

// "Cmd+Shift+N" -> "Ctrl+Maj+N" (fr) / "Ctrl+Shift+N" (en). L'ordre des touches de photocraft est conservé.
export function raccourciAffiche(s, lang = "fr") {
  if (!s) return "";
  return String(s).split("+").map((p) => (p === "Cmd" ? "Ctrl" : p === "Shift" && lang === "fr" ? "Maj" : p)).join("+");
}

function etatDe(id, idx, refuses) {
  if (TRAITES_PAR_ECRAN.has(id)) return "actif";
  const bas = String(id).toLowerCase();
  if (refuses.some((p) => bas.startsWith(p))) return "bientot";
  const r = idx.get(id);
  if (!r) return "bientot";
  // Rien que l'écran sache éditer (D9, autre document requis, que des opaques) -> « bientôt ». Les familles sur mesure
  // en sont exemptées : leurs éditeurs (Courbes, Niveaux, Réglages, Styles) écrivent eux-mêmes les champs opaques.
  // D9 est testé À PART, hors de cette exemption (sansEcran le teste aussi, mais seulement pour le générique) : une
  // interface lourde écartée reste grisée même si une famille sur mesure venait à couvrir son id. SANS_EDITEUR de même :
  // ces commandes sont nommées une à une, aucune exemption ne doit les rouvrir.
  if (D9.has(id) || SANS_EDITEUR.has(id) || (aiguillage(id) === "generique" && sansEcran(id, champsDe(r)))) return "bientot";
  return r.enabled === false ? "inactif" : "actif";
}

// Supprime, récursivement, les sous-menus vides, puis les séparateurs en tête, en queue ou doublés.
function nettoyer(entrees) {
  const sortie = [];
  for (const e of entrees) {
    if (e.type === "sous-menu") { e.entrees = nettoyer(e.entrees); if (!e.entrees.length) continue; }
    if (e.type === "separateur" && (!sortie.length || sortie[sortie.length - 1].type === "separateur")) continue;
    sortie.push(e);
  }
  while (sortie.length && sortie[sortie.length - 1].type === "separateur") sortie.pop();
  return sortie;
}

// Libellé d'une entrée Calque › Style de calque : le catalogue amont s'écarte par endroits du vocabulaire usuel des
// retoucheurs en français (« Contourner… », « Biseau et relief… ») ; le dialogue Style de calque (mod-styles.js libelleStyle) dit
// déjà « Contour », « Biseautage et estampage ». Le menu prend la MÊME clé photolab.styles.<k minuscule>
// (photolab.styles.options_fusion pour blendingOptions) quand le dictionnaire l'a, et garde la ponctuation du
// catalogue (« … » : l'entrée ouvre un dialogue). Sans clé : le catalogue tel quel. menus.json n'est jamais touché.
function libelleCatalogue(e, lang, t) {
  const lib = (lang === "fr" ? e.libelle_fr || e.libelle_en : e.libelle_en || e.libelle_fr) || e.id;
  if (typeof e.id !== "string" || !e.id.startsWith(PREFIXE_STYLE) || typeof t !== "function") return lib;
  const k = e.id.slice(PREFIXE_STYLE.length);
  const cle = k === "blendingOptions" ? "photolab.styles.options_fusion" : "photolab.styles." + k.toLowerCase();
  const r = t(cle);
  if (typeof r !== "string" || r === "" || r === cle) return lib;          // dzT rend la clé elle-même quand elle manque
  return /…$/.test(lib) ? r + "…" : r;
}

// catalogue = donnees/menus.json ; registre = GET /api/photolab/commandes ; refuses = REFUSES ; lang = "fr"|"en" ;
// t = traducteur (dzT) pour le menu « Aide » ajouté en dernier (le catalogue s'arrête à Window) et les styles de calque.
export function construireMenus(catalogue, registre, refuses, lang, t = (c) => c) {
  const idx = indexRegistre(registre);
  const noms = (catalogue && catalogue.menus_fr) || {};
  const affiche = (nom) => (lang === "fr" ? noms[nom] || nom : nom);
  const menus = [];
  for (const e of (catalogue && catalogue.entrees) || []) {
    const [haut, ...reste] = e.chemin;
    let menu = menus.find((m) => m.nom === haut);
    if (!menu) { menu = { nom: haut, nom_affiche: affiche(haut), entrees: [] }; menus.push(menu); }
    let liste = menu.entrees;
    for (const nom of reste) {
      // un sous-menu naît à la position de son premier enfant et garde cet ordre
      let sm = liste.find((x) => x.type === "sous-menu" && x.nom === nom);
      if (!sm) { sm = { type: "sous-menu", nom, nom_affiche: affiche(nom), entrees: [] }; liste.push(sm); }
      liste = sm.entrees;
    }
    if (e.separateur) { liste.push({ type: "separateur" }); continue; }
    const r = idx.get(e.id);
    liste.push({
      type: "commande", id: e.id,
      libelle: libelleCatalogue(e, lang, t),
      raccourci: raccourciAffiche(e.raccourci, lang),
      etat: etatDe(e.id, idx, refuses),
      champs: champsDe(r),               // null : commande absente du registre, ou pont sans `champs`
    });
  }
  for (const m of menus) m.entrees = nettoyer(m.entrees);
  // t139 : « Envoyer vers… » (Bibliothèque puis le menu de l'application) clôt le groupe des enregistrements du Fichier.
  const fichier = menus.find((m) => m.nom === "File");
  if (fichier) {
    const k = fichier.entrees.findIndex((e) => e.id === "file.revert");
    const pos = k >= 0 ? k + 1 : fichier.entrees.length;
    fichier.entrees.splice(pos, 0, { type: "commande", id: "pl.envoyer", libelle: t("photolab.menu.envoyer"), raccourci: "", etat: "actif", champs: [] },
      // t140 (D10) : le repli « app native » (photocraft.exe), pour ce que l'écran ne fait pas encore
      { type: "commande", id: "pl.natif.ouvrir", libelle: t("photolab.menu.natif_ouvrir"), raccourci: "", etat: "actif", champs: [] },
      { type: "commande", id: "pl.natif.reprendre", libelle: t("photolab.menu.natif_reprendre"), raccourci: "", etat: "actif", champs: [] });
  }
  menus.push({
    nom: "Aide", nom_affiche: t("photolab.menu.aide"),
    entrees: [{ type: "commande", id: "pl.apropos", libelle: t("photolab.menu.apropos"), raccourci: "", etat: "actif", champs: [] }],
  });
  return menus.filter((m) => m.entrees.length);
}

// Que fait un clic sur cette entrée ? ecran | apropos | executer | dialogue | rien
// « dialogue » : un champ visible, ou une famille sur mesure qui a des champs opaques à éditer (Courbes) ; une commande
// dont tous les champs sont cachés (layer.layerMask.revealAll {layer?}) ou qui n'en a aucun s'exécute directement.
export function actionEntree(entree) {
  if (!entree || entree.type === "separateur") return "rien";
  if (entree.id === "pl.apropos") return "apropos";
  if (entree.etat !== "actif") return "rien";
  // t151 : une entrée « pl.* » est une entrée de l'écran (Base, espaces personnels) : jamais une commande du moteur.
  if (TRAITES_PAR_ECRAN.has(entree.id) || String(entree.id).startsWith("pl.")) return "ecran";
  const champs = entree.champs;
  if (!Array.isArray(champs)) return "dialogue";
  if (champsVisibles(champs).length) return "dialogue";
  if (aiguillage(entree.id) !== "generique" && champs.some((c) => c && OPAQUES.has(c.type) && !CLES_CACHEES.has(c.cle))) return "dialogue";
  return "executer";
}

export function rechercherEntree(menus, id) {
  const voir = (entrees) => {
    for (const e of entrees) {
      if (e.id === id) return e;
      if (e.entrees) { const r = voir(e.entrees); if (r) return r; }
    }
    return null;
  };
  for (const m of menus) { const r = voir(m.entrees); if (r) return r; }
  return null;
}

// Position d'un panneau de menu dans la fenêtre. ancre = {gauche, droite, haut, bas} du bouton ou de la ligne parente ;
// mode "bas" : sous le bouton de la barre ; mode "droite" : sous-menu à droite de sa ligne, RETOURNÉ à gauche s'il
// déborde. Le haut et la hauteur maximale restent dans la fenêtre (défilement interne au-delà).
export function placerPanneau(ancre, taille, fenetre, mode, marge = 2) {
  if (mode === "bas") {
    const y = ancre.bas;
    return { x: Math.max(marge, Math.min(ancre.gauche, fenetre.w - taille.w - marge)), y, maxH: Math.max(120, fenetre.h - y - 8) };
  }
  let x = ancre.droite - 2;
  if (x + taille.w > fenetre.w - marge) x = ancre.gauche - taille.w + 2;
  x = Math.max(0, x);
  const maxH = Math.max(0, fenetre.h - 16);
  const h = Math.min(taille.h, maxH);
  let y = ancre.haut - 4;
  if (y + h > fenetre.h - 8) y = Math.max(8, fenetre.h - 8 - h);
  y = Math.max(8, y);
  return { x, y, maxH };
}

/* ───────────── côté DOM ───────────── */

export function initMenus(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const lang = () => (window.dzLang ? window.dzLang() : "fr");
  const barre = PL.$("#menubar");
  let catalogue = null, registre = [], menus = [];
  let panneaux = [];            // pile des panneaux ouverts : {el, entrees, lignes, courante}
  let ouvert = -1;              // index du menu de la barre ouvert
  let aReconstruire = false;    // un rafraîchissement est arrivé pendant qu'un menu était ouvert : on l'applique à la fermeture
  let focus = null;             // panneau qui reçoit les flèches (celui où la dernière sélection a eu lieu)
  let dernierRegistre = 0;
  PL.actions = PL.actions || {};   // id d'entrée traitée par l'écran -> fonction (branchée par mod-fichier, C1)

  PL.menus = {
    get arbre() { return menus; },
    // Dernier registre lu (t138 B5 : champs de layer.newAdjustmentLayer.<kind> pour l'éditeur du calque de réglage).
    get registre() { return registre; },
    // Relit le registre (l'état « actif » des commandes dépend du document ouvert) puis reconstruit l'arbre.
    async rafraichir() {
      // Silencieux : un rafraîchissement d'arrière-plan n'a pas à ouvrir un toast (moteur absent = menus « bientôt »).
      try { registre = await PL.get("/commandes", true); dernierRegistre = Date.now(); } catch (e) { /* menus sans registre */ }
      reconstruire();
    },
    // Active une entrée de commande comme un clic (raccourcis clavier, C1) : même chemin que la souris.
    activer(entree) { return activer(null, { entree }); },
    // t151 : reconstruit l'arbre sans relire le registre (coches des espaces et des panneaux).
    redessiner() { reconstruire(); },
  };

  function reconstruire() {
    if (!catalogue) return;
    if (ouvert >= 0) { aReconstruire = true; return; }      // jamais sous les doigts de l'utilisateur
    menus = construireMenus(catalogue, registre, REFUSES, lang(), T);
    if (PL.espaces) menus = PL.espaces.decorer(menus);      // t151 : sous-menu Espace de travail, coches de Fenêtre
    if (PL.affichage) menus = PL.affichage.decorer(menus);  // t152 : menu Affichage (états et coches)
    barre.textContent = "";
    menus.forEach((m, i) => {
      const b = document.createElement("button");
      b.type = "button"; b.className = "menu-bouton"; b.textContent = m.nom_affiche; b.dataset.menu = String(i);
      b.setAttribute("aria-haspopup", "menu"); b.setAttribute("aria-expanded", "false");
      b.addEventListener("click", () => (ouvert === i ? fermer() : ouvrir(i)));
      b.addEventListener("pointerenter", () => {
        if (ouvert >= 0 && ouvert !== i) ouvrir(i);
        if (ouvert < 0 && Date.now() - dernierRegistre > 5000) PL.menus.rafraichir();
      });
      barre.appendChild(b);
    });
  }

  // L'entrée est-elle réellement utilisable maintenant ? (certaines n'ont de sens qu'avec un document)
  function effective(e) {
    if (e.type === "commande" && NECESSITE_DOC.has(e.id) && !PL.etat.doc) return { ...e, etat: "inactif" };
    return e;
  }

  function fermer() {
    panneaux.forEach((p) => p.el.remove());
    panneaux = []; focus = null;
    PL.$$(".menu-bouton", barre).forEach((b) => { b.classList.remove("actif"); b.setAttribute("aria-expanded", "false"); });
    ouvert = -1;
    if (aReconstruire) { aReconstruire = false; reconstruire(); }
  }
  function fermerJusqua(niveau) {
    while (panneaux.length > niveau) panneaux.pop().el.remove();
    if (!panneaux.includes(focus)) focus = panneaux[panneaux.length - 1] || null;
  }

  function ouvrir(i) {
    fermer();
    ouvert = i;
    const b = PL.$$(".menu-bouton", barre)[i];
    b.classList.add("actif"); b.setAttribute("aria-expanded", "true");
    const r = b.getBoundingClientRect();
    ouvrirPanneau(menus[i].entrees, { gauche: r.left, droite: r.right, haut: r.top, bas: r.bottom - 1 }, "bas", 0);
  }

  function ouvrirPanneau(entrees, ancre, mode, niveau) {
    fermerJusqua(niveau);
    const el = document.createElement("div");
    el.className = "menu-panneau"; el.setAttribute("role", "menu");
    const p = { el, entrees, lignes: [], courante: -1, niveau };
    for (const brut of entrees) {
      if (brut.type === "separateur") { const s = document.createElement("div"); s.className = "menu-sep"; el.appendChild(s); continue; }
      const e = effective(brut);
      const l = document.createElement("div");
      l.className = "menu-ligne " + (e.type === "sous-menu" ? "actif" : e.etat);
      l.setAttribute("role", "menuitem");
      if (e.type !== "sous-menu" && e.etat !== "actif") l.setAttribute("aria-disabled", "true");
      if (e.type === "sous-menu") l.setAttribute("aria-haspopup", "menu");
      const lib = document.createElement("span"); lib.className = "menu-lib";
      lib.textContent = e.type === "sous-menu" ? e.nom_affiche : e.libelle;
      if (e.brut) lib.setAttribute("data-dz-brut", "");          // t151 : nom d'un espace donné par l'utilisateur
      if (typeof e.coche === "boolean") {
        // t151 : entrée à coche (espace actif, verrou, panneau visible)
        const co = document.createElement("span"); co.className = "menu-coche"; co.textContent = e.coche ? "✓" : "";
        l.classList.add("cochable"); l.setAttribute("role", "menuitemcheckbox"); l.setAttribute("aria-checked", e.coche ? "true" : "false");
        l.appendChild(co);
      }
      const droite = document.createElement("span"); droite.className = "menu-droite";
      droite.textContent = e.type === "sous-menu" ? "▸" : e.raccourci || "";
      l.append(lib, droite);
      if (e.etat === "bientot") l.title = T("photolab.menu.bientot");
      l.addEventListener("pointerenter", () => selectionner(p, p.lignes.findIndex((x) => x.el === l)));
      l.addEventListener("click", (ev) => { ev.stopPropagation(); activer(p, p.lignes.find((x) => x.el === l)); });
      p.lignes.push({ el: l, entree: e });
      el.appendChild(l);
    }
    document.body.appendChild(el);
    const pos = placerPanneau(ancre, { w: el.offsetWidth, h: el.offsetHeight }, { w: innerWidth, h: innerHeight }, mode);
    el.style.left = pos.x + "px"; el.style.top = pos.y + "px";
    el.style.maxHeight = pos.maxH + "px";                   // défilement si trop haut
    panneaux.push(p);
    return p;
  }

  function selectionner(p, n) {
    p.courante = n;
    focus = p;
    p.lignes.forEach((l, k) => l.el.classList.toggle("survol", k === n));
    fermerJusqua(p.niveau + 1);
    const l = p.lignes[n];
    if (l && l.entree.type === "sous-menu") {
      const r = l.el.getBoundingClientRect();
      ouvrirPanneau(l.entree.entrees, { gauche: r.left, droite: r.right, haut: r.top, bas: r.bottom }, "droite", p.niveau + 1);
    }
  }

  async function activer(p, ligne) {
    if (!ligne) return;
    const e = ligne.entree;
    if (e.type === "sous-menu") { selectionner(p, p.lignes.indexOf(ligne)); return; }
    fermer();
    switch (actionEntree(e)) {
      case "ecran": {
        const f = PL.actions[e.id];
        if (f) f();
        else if (!(PL.actionEspace && PL.actionEspace(e.id))) PL.signaler(T("photolab.menu.bientot"));     // t151 : espaces personnels
        break;
      }
      case "apropos": PL.apropos(); break;
      case "executer": {
        // Par la file FIFO de mod-cycle : l'ordre des gestes reste l'ordre d'exécution, et le cycle qui suit relit
        // l'état (le cycle rafraîchit aussi les menus). Échec : déjà signalé par mod-api.
        const r = await PL.executer(e.id, {});
        if (r && r.ok && !PL.cycle) PL.menus.rafraichir();
        break;
      }
      case "dialogue": {
        const cible = cibleDialogue(e, PL);
        const suffixe = e.id.slice(e.id.lastIndexOf(".") + 1);
        if (cible === "courbes") PL.ouvrirCourbes(e);
        else if (cible === "niveaux") PL.ouvrirNiveaux(e);
        else if (cible === "reglage") PL.creerReglage(suffixe);
        else if (cible === "style") PL.ouvrirStyles(suffixe);
        else if (cible === "generique") PL.ouvrirReglage(e);
        else PL.signaler(T("photolab.menu.bientot"));       // éditeur absent (pont ancien sans champs, module non chargé)
        break;
      }
      default:
        if (e.etat === "bientot") PL.signaler(T("photolab.menu.bientot"));
    }
  }

  function informer(texte) {
    if (window.__dzDialogue && window.__dzDialogue.informer) return window.__dzDialogue.informer(texte);
    PL.signaler(texte);
    return Promise.resolve();
  }
  // Crédits : le moteur et les icônes ne sont pas à nous.
  function apropos() {
    informer([T("photolab.apropos.titre"), "", T("photolab.apropos.moteur"), T("photolab.apropos.icones")].join("\n"));
  }
  PL.apropos = apropos;

  /* clavier : ↑ ↓ → ← ↩ Échap */
  document.addEventListener("keydown", (ev) => {
    if (ouvert < 0) return;
    const p = focus || panneaux[panneaux.length - 1];
    if (!p) return;
    const dispo = p.lignes.map((l, k) => k).filter((k) => p.lignes[k].entree.type === "sous-menu" || p.lignes[k].entree.etat !== "inactif");
    const aller = (pas) => {
      if (!dispo.length) return;
      const pos = dispo.indexOf(p.courante);
      const n = dispo[(pos < 0 ? (pas > 0 ? 0 : dispo.length - 1) : (pos + pas + dispo.length) % dispo.length)];
      selectionner(p, n);
      p.lignes[n].el.scrollIntoView({ block: "nearest" });
    };
    const k = ev.key;
    if (k === "ArrowDown") aller(+1);
    else if (k === "ArrowUp") aller(-1);
    else if (k === "ArrowRight") {
      const l = p.lignes[p.courante];
      const fils = l && l.entree.type === "sous-menu" ? panneaux[p.niveau + 1] : null;
      if (fils) selectionner(fils, fils.lignes.findIndex((x) => x.entree.etat !== "inactif"));
      else ouvrir((ouvert + 1) % menus.length);
    } else if (k === "ArrowLeft") {
      if (p.niveau > 0) fermerJusqua(p.niveau); else ouvrir((ouvert - 1 + menus.length) % menus.length);
    } else if (k === "Enter") { if (p.courante >= 0) activer(p, p.lignes[p.courante]); }
    else if (k === "Escape") { if (p.niveau > 0) fermerJusqua(p.niveau); else fermer(); }
    else return;
    ev.preventDefault(); ev.stopPropagation();
  }, true);
  document.addEventListener("pointerdown", (ev) => {
    if (ouvert >= 0 && !ev.target.closest(".menu-panneau") && !ev.target.closest(".menu-bouton")) fermer();
  }, true);
  window.addEventListener("blur", fermer);

  // Chargement : catalogue statique puis registre (les menus s'affichent dès que le catalogue est là).
  fetch("donnees/menus.json").then((r) => r.json()).then((c) => { catalogue = c; reconstruire(); PL.menus.rafraichir(); })
    .catch(() => PL.signaler(T("photolab.menu.catalogue_absent"), true));
}
