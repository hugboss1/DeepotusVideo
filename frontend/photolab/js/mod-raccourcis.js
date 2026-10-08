// mod-raccourcis.js — raccourcis clavier des commandes : ceux du catalogue de photocraft (lus dans l'arbre des menus
// générés, donc jamais recopiés à la main) et trois que l'écran ajoute (Ctrl+Z, Ctrl+Maj+Z, Ctrl+Maj+I, absents du
// catalogue). Les lettres seules restent aux outils (mod-outils), les touches de zoom à la vue (mod-vue).
// Fonctions PURES exportées (qa/raccourcis.test.mjs).

const ORDRE = ["ctrl", "alt", "shift"];
const ALIAS = { cmd: "ctrl", meta: "ctrl", control: "ctrl", maj: "shift", option: "alt" };

// « Cmd+Shift+N », « Ctrl+Maj+N », « Shift+Cmd+N » -> « ctrl+shift+n » (modificateurs dans un ordre fixe).
export function normaliser(s) {
  if (!s) return "";
  const parts = String(s).split("+").map((p) => p.trim().toLowerCase()).filter(Boolean);
  if (!parts.length) return "";
  const touche = parts.pop();
  const mods = new Set(parts.map((p) => ALIAS[p] || p));
  return [...ORDRE.filter((m) => mods.has(m)), touche].join("+");
}

// Événement clavier -> forme canonique ; "" pour une touche de modification seule.
export function comboDe(ev) {
  let k = ev.key || "";
  if (/^(Control|Shift|Alt|Meta|AltGraph|OS)$/.test(k)) return "";
  if (k.length !== 1 && !/^F\d{1,2}$/.test(k)) {
    // touche morte ou inconnue : la position physique (KeyE -> e, Digit1 -> 1)
    const m = /^(?:Key([A-Z])|Digit(\d))$/.exec(ev.code || "");
    if (m) k = m[1] || m[2];
  }
  if (!k) return "";
  const mods = [];
  if (ev.ctrlKey || ev.metaKey) mods.push("ctrl");
  if (ev.altKey) mods.push("alt");
  if (ev.shiftKey) mods.push("shift");
  return [...mods, k.toLowerCase()].join("+");
}

// L'écran ne prend que les combinaisons avec Ctrl ou Alt, et les touches de fonction : une lettre seule (ou Maj+lettre)
// choisit un outil.
export function aIntercepter(combo) {
  if (!combo) return false;
  const parts = combo.split("+");
  const touche = parts[parts.length - 1];
  return parts.includes("ctrl") || parts.includes("alt") || /^f\d{1,2}$/.test(touche);
}

// Arbre de construireMenus -> Map(combo -> entrée de commande).
export function indexRaccourcis(menus) {
  const idx = new Map();
  const voir = (entrees) => {
    for (const e of entrees || []) {
      if (e.type === "sous-menu") voir(e.entrees);
      else if (e.type === "commande" && e.raccourci) {
        const c = normaliser(e.raccourci);
        if (c && !idx.has(c)) idx.set(c, e);
      }
    }
  };
  for (const m of menus || []) voir(m.entrees);
  return idx;
}

// Ajouts de l'écran (usage courant des retoucheurs) ; le banc vérifie qu'aucun ne masque une combinaison du catalogue.
export const RACCOURCIS_ECRAN = {
  "ctrl+z": "edit.undo",
  "ctrl+shift+z": "edit.redo",
  "ctrl+shift+i": "select.inverse",
};

/* ───────────── côté DOM ───────────── */

export function initRaccourcis(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const enSaisie = (ev) => ev.target && (/^(INPUT|TEXTAREA|SELECT)$/.test(ev.target.tagName || "") || ev.target.isContentEditable);
  const sansDocument = new Set(["file.new", "file.open"]);
  let arbre = null, idx = new Map();

  document.addEventListener("keydown", (ev) => {
    // La vue a déjà pris ses touches de zoom (preventDefault), les menus ouverts prennent les leurs en capture ; un
    // dialogue garde ses touches ; un champ de saisie garde Ctrl+A / Ctrl+Z pour son texte.
    // Répétition de touche : seulement Ctrl+Z / Ctrl+Maj+Z (cumulés par PL.historique), jamais une autre commande.
    if (ev.defaultPrevented || (ev.repeat && !/^z$/i.test(ev.key || "")) || enSaisie(ev)) return;
    if (document.querySelector(".pl-voile, .dz-dialogue, .menu-panneau")) return;
    const combo = comboDe(ev);
    if (!aIntercepter(combo)) return;
    const doc = PL.etat.doc;
    const ecran = RACCOURCIS_ECRAN[combo];
    if (ecran) {
      ev.preventDefault();
      if (!doc) return;
      // Annuler / rétablir : cumulés pendant qu'une requête vole (touche tenue), et sans tester un canUndo qui peut
      // dater du cycle précédent — /historique compte ce qu'il n'a pas pu faire sans échouer (mod-cycle).
      if (ecran === "edit.undo") { PL.historique(-1); return; }
      if (ecran === "edit.redo") { PL.historique(1); return; }
      PL.executer(ecran, {});
      return;
    }
    if (!PL.menus) return;
    if (PL.menus.arbre !== arbre) { arbre = PL.menus.arbre; idx = indexRaccourcis(arbre); }
    const e = idx.get(combo);
    if (!e) return;
    ev.preventDefault();
    if (!doc && !sansDocument.has(e.id)) return;
    if (e.etat === "bientot") { PL.signaler(T("photolab.menu.bientot")); return; }
    // « inactif » vient du registre, relu après le dernier cycle : il peut retarder d'un geste (sélection qui vient
    // d'apparaître). Le moteur reste juge : on tente, il refuse au besoin.
    PL.menus.activer(e.etat === "inactif" ? { ...e, etat: "actif" } : e);
  });
}
