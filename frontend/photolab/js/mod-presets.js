// mod-presets.js — t153 (parité L3) : les panneaux Dégradés et Motifs, onglets du groupe Couleur. Un même navigateur
// (amont preset_panels.rs, référence relevée le 08/10) : recherche, groupes repliables, vignettes ; clic = choisir
// (gradient|pattern.presets.select, hors historique), double-clic = calque de remplissage (…presets.apply), clic droit =
// renommer / supprimer, pied = nouveau groupe, nouveau, supprimer (…presets.new / …presets.edit). Les listes viennent
// du moteur (…presets.list) ; les vignettes de motif sont rendues par le pont (/motifs/<id>.png). Fonctions PURES
// exportées (qa/panneaux3.test.mjs).
import { demanderNom } from "./mod-nommer.js";

// Noms intégrés du moteur (anglais) -> clés : les groupes et préréglages fournis s'affichent dans la langue de l'écran ;
// un nom donné par l'utilisateur s'affiche tel quel (data-dz-brut).
export const NOMS_INTEGRES = {
  "Basics": "photolab.presets.basiques", "Blues": "photolab.presets.bleus", "Purples": "photolab.presets.violets",
  "Pinks": "photolab.presets.roses", "Reds": "photolab.presets.rouges", "Oranges": "photolab.presets.oranges",
  "Greens": "photolab.presets.verts", "Browns": "photolab.presets.bruns", "Grays": "photolab.presets.tons_gris", "Geometric": "photolab.presets.geometriques",
  "Textures": "photolab.presets.textures", "Patterns": "photolab.presets.motifs",
  "Foreground to Background": "photolab.presets.pp_ap", "Foreground to Transparent": "photolab.presets.pp_transparent",
  "Black, White": "photolab.presets.noir_blanc", "Checkerboard": "photolab.presets.damier",
  "Diagonal Lines": "photolab.presets.diagonales", "Dots": "photolab.presets.points", "Grid": "photolab.presets.grille",
  "Bricks": "photolab.presets.briques", "Weave": "photolab.presets.tissage", "Paper Noise": "photolab.presets.papier",
};
// « Blue 03 » -> clé de « Bleu » + « 03 ».
export const PREFIXES_INTEGRES = { Blue: "photolab.presets.bleu", Purple: "photolab.presets.violet", Pink: "photolab.presets.rose",
  Red: "photolab.presets.rouge", Orange: "photolab.presets.orange", Green: "photolab.presets.vert", Brown: "photolab.presets.brun",
  Gray: "photolab.presets.gris" };
// -> {texte, brut} : brut = nom donné par l'utilisateur (non traduit).
export function nomAffiche(nom, t) {
  if (NOMS_INTEGRES[nom]) return { texte: t(NOMS_INTEGRES[nom]), brut: false };
  const m = /^(Blue|Purple|Pink|Red|Orange|Green|Brown|Gray) (\d{2})$/.exec(String(nom));
  if (m) return { texte: t(PREFIXES_INTEGRES[m[1]]) + " " + m[2], brut: false };
  return { texte: String(nom), brut: true };
}

// Réponse de …presets.list -> [{nom, items:[{cle, nom, …}]}] ; `cle` = ce que select / apply attendent (nom du
// dégradé, id du motif).
export function groupesDe(genre, r) {
  const gs = (r && Array.isArray(r.groups)) ? r.groups : [];
  return gs.map((g) => ({ nom: g.name, items: (genre === "degrades" ? g.presets : g.patterns || []).map((p) =>
    genre === "degrades" ? { cle: p.name, nom: p.name, stops: p.stops, transparency: p.transparency }
      : { cle: p.id, nom: p.name, largeur: p.width, hauteur: p.height }) }));
}
export function courantDe(genre, r) {
  const c = r && r.current;
  if (!c) return null;
  return genre === "degrades" ? c.name : (typeof c === "object" ? c.id : c);
}
export function filtrerGroupes(groupes, texte, t) {
  const q = String(texte || "").trim().toLowerCase();
  if (!q) return groupes;
  return groupes.map((g) => ({ ...g, items: g.items.filter((p) => p.nom.toLowerCase().includes(q)
    || nomAffiche(p.nom, t).texte.toLowerCase().includes(q)) })).filter((g) => g.items.length);
}

const hex2 = (n) => Math.round(Math.max(0, Math.min(255, n))).toString(16).padStart(2, "0");
const lireCouleur = (c, fg, bg) => {
  if (c === "foreground") return fg;
  if (c === "background") return bg;
  if (Array.isArray(c)) return "#" + c.slice(0, 3).map((v) => hex2(v <= 1 ? v * 255 : v)).join("");
  return String(c).slice(0, 7);
};
// Opacité (0..1) à la position t d'après les arrêts de transparence [[t, 0..100]] (interpolation linéaire ; aucun = 1).
export function opaciteA(transparency, t) {
  const tr = Array.isArray(transparency) ? transparency : [];
  if (!tr.length) return 1;
  if (t <= tr[0][0]) return tr[0][1] / 100;
  for (let i = 1; i < tr.length; i++) {
    if (t <= tr[i][0]) {
      const [a, oa] = tr[i - 1], [b, ob] = tr[i];
      const k = b === a ? 0 : (t - a) / (b - a);
      return (oa + (ob - oa) * k) / 100;
    }
  }
  return tr[tr.length - 1][1] / 100;
}
// Arrêts du moteur -> fond CSS (linear-gradient à 90°), premier et arrière-plan résolus avec les couleurs courantes.
export function cssDegrade(stops, transparency, fg = "#000000", bg = "#ffffff") {
  const s = (Array.isArray(stops) ? stops : []).map(([t, c]) => {
    const h = lireCouleur(c, fg, bg);
    const a = opaciteA(transparency, t);
    const rgb = [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
    return `rgba(${rgb.join(", ")}, ${Math.round(a * 1000) / 1000}) ${Math.round(t * 1000) / 10}%`;
  });
  if (!s.length) return "none";
  if (s.length === 1) s.push(s[0]);
  return "linear-gradient(90deg, " + s.join(", ") + ")";
}

// Commandes du moteur par genre.
export const COMMANDES = {
  degrades: { lister: "gradient.presets.list", choisir: "gradient.presets.select", appliquer: "gradient.presets.apply",
    nouveau: "gradient.presets.new", editer: "gradient.presets.edit", champ: "preset" },
  motifs: { lister: "pattern.presets.list", choisir: "pattern.presets.select", appliquer: "pattern.presets.apply",
    nouveau: "pattern.presets.new", editer: "pattern.presets.edit", champ: "pattern" },
};
// Paramètres de …presets.edit pour une action du panneau (le moteur désigne un préréglage par son NOM, aussi pour un
// motif : `preset` = nom, `group` pour lever l'ambiguïté).
export function paramsEdition(action, item, groupe, nom) {
  if (action === "renommer") return { action: "rename", preset: item.nom, group: groupe, name: nom };
  if (action === "supprimer") return { action: "delete", preset: item.nom, group: groupe };
  if (action === "nouveauGroupe") return { action: "newGroup", name: nom };
  if (action === "renommerGroupe") return { action: "renameGroup", group: groupe, name: nom };
  if (action === "supprimerGroupe") return { action: "deleteGroup", group: groupe };
  return null;
}

export function initPresets(PL, genre) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const C = COMMANDES[genre];
  const corps = PL.$(genre === "degrades" ? "#corpsDegrades" : "#corpsMotifs");
  if (!corps) return;
  let groupes = [], courant = null, sel = null;          // sel = {groupe, item?}
  const replies = new Set();
  let premiers = true;
  let fg = "#000000", bg = "#ffffff";

  const barre = document.createElement("div"); barre.className = "pr-courant";
  const recherche = document.createElement("input");
  recherche.type = "search"; recherche.className = "pr-recherche";
  recherche.placeholder = T(genre === "degrades" ? "photolab.presets.rechercher_degrades" : "photolab.presets.rechercher_motifs");
  recherche.setAttribute("aria-label", recherche.placeholder);
  const liste = document.createElement("div"); liste.className = "pr-liste";
  const pied = document.createElement("div"); pied.className = "pr-pied";
  const bouton = (icone, cle, fn) => {
    const b = document.createElement("button"); b.type = "button"; b.className = "pr-btn"; b.dataset.icone = icone;
    b.title = T(cle); b.setAttribute("aria-label", b.title); b.addEventListener("click", fn); pied.appendChild(b); return b;
  };
  bouton("folder-plus", "photolab.presets.nouveau_groupe", async () => {
    const nom = await demanderNom(PL, T("photolab.presets.nouveau_groupe"));
    if (nom) await commande(C.editer, paramsEdition("nouveauGroupe", null, null, nom));
  });
  const bNouveau = bouton("plus", genre === "degrades" ? "photolab.presets.nouveau_degrade" : "photolab.presets.definir_motif", async () => {
    if (genre === "degrades") {
      const nom = await demanderNom(PL, T("photolab.presets.nouveau_degrade"), T("photolab.presets.perso"));
      if (nom) await commande(C.nouveau, { name: nom, ...(sel && sel.groupe ? { group: sel.groupe } : {}) });
    } else {
      // Définir un motif : depuis la sélection (sinon le document entier) du document ouvert.
      if (!PL.etat.doc) return;
      const nom = await demanderNom(PL, T("photolab.presets.definir_motif"), T("photolab.presets.motif"));
      if (nom) await commande(C.nouveau, { name: nom, ...(sel && sel.groupe ? { group: sel.groupe } : {}) });
    }
  });
  const bSuppr = bouton("trash-2", "photolab.presets.supprimer", async () => {
    if (!sel) return;
    await commande(C.editer, sel.item ? paramsEdition("supprimer", sel.item, sel.groupe) : paramsEdition("supprimerGroupe", null, sel.groupe));
    sel = null;
  });
  if (genre === "degrades") corps.appendChild(barre);
  corps.append(recherche, liste, pied);
  if (PL.hydraterIcones) PL.hydraterIcones(pied);
  recherche.addEventListener("input", dessiner);

  // Les préréglages vivent dans la session du moteur : /executer direct (comme les couleurs), sans document.
  async function commande(cid, params) {
    let r;
    try { r = await PL.post("/executer", { command: cid, params }); } catch (e) { return null; }
    await relire();
    return r;
  }
  async function relire() {
    let r;
    try { r = await PL.post("/executer", { command: C.lister, params: {} }); } catch (e) { return; }
    groupes = groupesDe(genre, r);
    courant = courantDe(genre, r);
    if (premiers) { premiers = false; groupes.slice(1).forEach((g) => replies.add(g.nom)); }   // seul le premier groupe ouvert (amont)
    dessiner();
  }
  function vignette(item) {
    const v = document.createElement("span"); v.className = "pr-vignette";
    if (genre === "degrades") v.style.background = cssDegrade(item.stops, item.transparency, fg, bg) + ", var(--damier, #888)";
    else { const im = document.createElement("img"); im.alt = ""; im.loading = "lazy"; im.src = "/api/photolab/motifs/" + item.cle + ".png"; v.appendChild(im); }
    return v;
  }
  async function menuContextuel(ev, item, groupe) {
    ev.preventDefault();
    sel = { groupe, item }; dessiner();
    const nom = await demanderNom(PL, T("commun.action.renommer"), nomAffiche(item.nom, T).texte);
    if (nom) await commande(C.editer, paramsEdition("renommer", item, groupe, nom));
  }
  function dessiner() {
    if (genre === "degrades") {
      const g = groupes.flatMap((x) => x.items).find((p) => p.cle === courant);
      barre.style.background = g ? cssDegrade(g.stops, g.transparency, fg, bg) : "none";
      barre.title = g ? nomAffiche(g.nom, T).texte : "";
    }
    liste.textContent = "";
    for (const g of filtrerGroupes(groupes, recherche.value, T)) {
      const tete = document.createElement("div");
      tete.className = "pr-groupe" + (sel && sel.groupe === g.nom && !sel.item ? " choisi" : "");
      const fl = document.createElement("button"); fl.type = "button"; fl.className = "pr-fleche"; fl.textContent = replies.has(g.nom) ? "▸" : "▾";
      fl.setAttribute("aria-label", T(replies.has(g.nom) ? "photolab.presets.deplier" : "photolab.presets.replier"));
      fl.addEventListener("click", () => { if (replies.has(g.nom)) replies.delete(g.nom); else replies.add(g.nom); dessiner(); });
      const n = nomAffiche(g.nom, T);
      const nom = document.createElement("span"); nom.className = "pr-nom"; nom.textContent = n.texte;
      if (n.brut) nom.setAttribute("data-dz-brut", "");
      nom.addEventListener("click", () => { sel = { groupe: g.nom }; dessiner(); });
      nom.addEventListener("dblclick", async () => {
        const v = await demanderNom(PL, T("commun.action.renommer"), n.texte);
        if (v) await commande(C.editer, paramsEdition("renommerGroupe", null, g.nom, v));
      });
      tete.append(fl, nom);
      liste.appendChild(tete);
      if (replies.has(g.nom)) continue;
      const grille = document.createElement("div"); grille.className = "pr-grille";
      for (const p of g.items) {
        const b = document.createElement("button"); b.type = "button";
        b.className = "pr-item" + (p.cle === courant ? " courant" : "") + (sel && sel.item && sel.item.cle === p.cle ? " choisi" : "");
        const na = nomAffiche(p.nom, T);
        b.title = na.texte + (genre === "motifs" && p.largeur ? " (" + p.largeur + " × " + p.hauteur + ")" : "");
        b.setAttribute("aria-label", b.title);
        if (na.brut) b.setAttribute("data-dz-brut", "");
        b.appendChild(vignette(p));
        b.addEventListener("click", () => { sel = { groupe: g.nom, item: p }; commande(C.choisir, { [C.champ]: p.cle }); });
        // Double-clic : un calque de remplissage dans le document ouvert (historique : New Gradient / Pattern Fill Layer).
        b.addEventListener("dblclick", () => { if (PL.etat.doc) PL.executer(C.appliquer, { [C.champ]: p.cle }); });
        b.addEventListener("contextmenu", (ev) => menuContextuel(ev, p, g.nom));
        grille.appendChild(b);
      }
      liste.appendChild(grille);
    }
    bSuppr.disabled = !sel;
    if (genre === "motifs") bNouveau.disabled = !PL.etat.doc;
  }
  PL.surCouleurs = PL.surCouleurs || [];
  PL.surCouleurs.push((c) => { if (c && c.fg) { fg = c.fg; bg = c.bg || bg; if (genre === "degrades") dessiner(); } });
  if (PL.surDoc) PL.surDoc.push(() => { if (genre === "motifs") bNouveau.disabled = !PL.etat.doc; });
  PL.presets = PL.presets || {};
  PL.presets[genre] = { relire, groupes: () => groupes, courant: () => courant };
}
