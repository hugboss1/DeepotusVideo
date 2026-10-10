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
  // t156 : formes personnalisées et styles de calque fournis par le moteur
  "Symbols": "photolab.presets.f_symbols",
  "Heart": "photolab.presets.f_heart",
  "Star": "photolab.presets.f_star",
  "Six-Point Star": "photolab.presets.f_six_point_star",
  "Burst": "photolab.presets.f_burst",
  "Check Mark": "photolab.presets.f_check_mark",
  "Cross": "photolab.presets.f_cross",
  "Plus": "photolab.presets.f_plus",
  "Ring": "photolab.presets.f_ring",
  "Lightning": "photolab.presets.f_lightning",
  "Diamond": "photolab.presets.f_diamond",
  "Arrows": "photolab.presets.f_arrows",
  "Arrow Right": "photolab.presets.f_arrow_right",
  "Arrow Left": "photolab.presets.f_arrow_left",
  "Arrow Up": "photolab.presets.f_arrow_up",
  "Arrow Down": "photolab.presets.f_arrow_down",
  "Double Arrow": "photolab.presets.f_double_arrow",
  "Chevron": "photolab.presets.f_chevron",
  "Curved Arrow": "photolab.presets.f_curved_arrow",
  "Speech Bubbles": "photolab.presets.f_speech_bubbles",
  "Speech Bubble": "photolab.presets.f_speech_bubble",
  "Round Bubble": "photolab.presets.f_round_bubble",
  "Thought Bubble": "photolab.presets.f_thought_bubble",
  "Shout Bubble": "photolab.presets.f_shout_bubble",
  "Nature": "photolab.presets.f_nature",
  "Leaf": "photolab.presets.f_leaf",
  "Sun": "photolab.presets.f_sun",
  "Crescent Moon": "photolab.presets.f_crescent_moon",
  "Cloud": "photolab.presets.f_cloud",
  "Raindrop": "photolab.presets.f_raindrop",
  "Flower": "photolab.presets.f_flower",
  "Tree": "photolab.presets.f_tree",
  "Animals": "photolab.presets.f_animals",
  "Fish": "photolab.presets.f_fish",
  "Cat": "photolab.presets.f_cat",
  "Bird": "photolab.presets.f_bird",
  "Butterfly": "photolab.presets.f_butterfly",
  "Paw Print": "photolab.presets.f_paw_print",
  "Rabbit": "photolab.presets.f_rabbit",
  "Default Style (None)": "photolab.presets.s_default_style_none",
  "Drop Shadow": "photolab.presets.s_drop_shadow",
  "Soft Shadow": "photolab.presets.s_soft_shadow",
  "Black Stroke": "photolab.presets.s_black_stroke",
  "White Stroke": "photolab.presets.s_white_stroke",
  "Inner Shadow": "photolab.presets.s_inner_shadow",
  "Outer Glow": "photolab.presets.s_outer_glow",
  "Emboss": "photolab.presets.s_emboss",
  "Text Effects": "photolab.presets.s_text_effects",
  "Neon Blue": "photolab.presets.s_neon_blue",
  "Neon Pink": "photolab.presets.s_neon_pink",
  "Chrome": "photolab.presets.s_chrome",
  "Gold": "photolab.presets.s_gold",
  "Comic Outline": "photolab.presets.s_comic_outline",
  "Letterpress": "photolab.presets.s_letterpress",
  "Hollow": "photolab.presets.s_hollow",
  "Buttons": "photolab.presets.s_buttons",
  "Glass": "photolab.presets.s_glass",
  "Gel Green": "photolab.presets.s_gel_green",
  "Pressed": "photolab.presets.s_pressed",
  "Pill Red": "photolab.presets.s_pill_red",
  "Flat Shadow": "photolab.presets.s_flat_shadow",
  "Satin Plum": "photolab.presets.s_satin_plum",
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
  const liste = (g) => (genre === "degrades" || genre === "styles" ? g.presets : genre === "formes" ? g.shapes : g.patterns) || [];
  return gs.map((g) => ({ nom: g.name, items: liste(g).map((p) =>
    genre === "degrades" ? { cle: p.name, nom: p.name, stops: p.stops, transparency: p.transparency }
      : genre === "motifs" ? { cle: p.id, nom: p.name, largeur: p.width, hauteur: p.height }
        : { cle: p.name, nom: p.name, groupe: g.name }) }));
}
export function courantDe(genre, r) {
  const c = r && r.current;
  if (!c) return null;
  if (genre === "formes" || genre === "styles") return null;           // pas de « courant » au moteur : l'écran le garde
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
  // t156 : Formes (formes personnalisées) et Styles (styles de calque). Une forme se choisit à l'écran (l'outil Forme
  // personnalisée la place) ; un style s'applique au clic aux calques sélectionnés (Maj = ajouter aux effets).
  formes: { lister: "shape.presets.list", choisir: null, appliquer: "shape.presets.place", nouveau: "shape.presets.new",
    editer: "shape.presets.edit", champ: "preset" },
  styles: { lister: "style.presets.list", choisir: null, appliquer: "style.presets.apply", nouveau: "style.presets.new",
    editer: "style.presets.edit", champ: "preset" },
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

// Écran de chaque genre : corps, textes du champ de recherche et du bouton « nouveau », document requis pour « nouveau ».
export const ECRANS = {
  degrades: { corps: "#corpsDegrades", rechercher: "photolab.presets.rechercher_degrades", nouveau: "photolab.presets.nouveau_degrade",
    defaut: "photolab.presets.perso", doc: false },
  motifs: { corps: "#corpsMotifs", rechercher: "photolab.presets.rechercher_motifs", nouveau: "photolab.presets.definir_motif",
    defaut: "photolab.presets.motif", doc: true },
  formes: { corps: "#corpsFormes", rechercher: "photolab.presets.rechercher_formes", nouveau: "photolab.presets.definir_forme",
    defaut: "photolab.presets.forme", doc: true },
  styles: { corps: "#corpsStyles", rechercher: "photolab.presets.rechercher_styles", nouveau: "photolab.presets.nouveau_style",
    defaut: "photolab.presets.style", doc: true },
};
// Vignette d'un préréglage : dégradé en CSS ; motif, forme et style rendus par le pont (document temporaire).
export function urlVignette(genre, item) {
  if (genre === "motifs") return "/api/photolab/motifs/" + item.cle + ".png";
  const g = genre === "formes" ? "forme" : genre === "styles" ? "style" : null;
  if (!g) return null;
  return "/api/photolab/presets/" + g + "/vignette.png?cle=" + encodeURIComponent(item.cle) + (item.groupe ? "&groupe=" + encodeURIComponent(item.groupe) : "");
}

export function initPresets(PL, genre) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const C = COMMANDES[genre], E = ECRANS[genre];
  const corps = PL.$(E.corps);
  if (!corps) return;
  let groupes = [], courant = null, sel = null;          // sel = {groupe, item?}
  const replies = new Set();
  let premiers = true;
  let fg = "#000000", bg = "#ffffff";

  const barre = document.createElement("div"); barre.className = "pr-courant";
  const recherche = document.createElement("input");
  recherche.type = "search"; recherche.className = "pr-recherche";
  recherche.placeholder = T(E.rechercher);
  recherche.setAttribute("aria-label", recherche.placeholder);
  const liste = document.createElement("div"); liste.className = "pr-liste";
  const pied = document.createElement("div"); pied.className = "pr-pied";
  const bouton = (icone, cle, fn) => {
    const b = document.createElement("button"); b.type = "button"; b.className = "pr-btn"; b.dataset.icone = icone;
    b.title = T(cle); b.setAttribute("aria-label", b.title); b.addEventListener("click", fn); pied.appendChild(b); return b;
  };
  bouton("dz-action-nouveau-dossier", "photolab.presets.nouveau_groupe", async () => {
    const nom = await demanderNom(PL, T("photolab.presets.nouveau_groupe"));
    if (nom) await commande(C.editer, paramsEdition("nouveauGroupe", null, null, nom));
  });
  // Nouveau : dégradé = le dégradé courant ; motif = la sélection (sinon le document) ; forme = le tracé de travail, la
  // forme active ou le masque vectoriel ; style = les effets du calque actif.
  const bNouveau = bouton("dz-action-ajouter", E.nouveau, async () => {
    if (E.doc && !PL.etat.doc) return;
    const nom = await demanderNom(PL, T(E.nouveau), T(E.defaut));
    if (nom) await commande(C.nouveau, { name: nom, ...(sel && sel.groupe ? { group: sel.groupe } : {}) });
  });
  const bSuppr = bouton("dz-action-supprimer", "photolab.presets.supprimer", async () => {
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
  // t159 : le gestionnaire de préréglages (mod-gestionnaire) renomme, supprime, déplace : chaque panneau se relit
  PL.relirePresets = PL.relirePresets || [];
  PL.relirePresets.push(relire);
  function vignette(item) {
    const v = document.createElement("span"); v.className = "pr-vignette";
    if (genre === "degrades") v.style.background = cssDegrade(item.stops, item.transparency, fg, bg) + ", var(--damier, #888)";
    else { const im = document.createElement("img"); im.alt = ""; im.loading = "lazy"; im.src = urlVignette(genre, item); v.appendChild(im); }
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
      const fl = document.createElement("button"); fl.type = "button"; fl.className = "pr-fleche" + (replies.has(g.nom) ? " pl-replie" : ""); fl.innerHTML = PL.icone("dz-action-deplier");
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
        b.addEventListener("click", (ev) => {
          sel = { groupe: g.nom, item: p };
          if (genre === "formes") { courant = p.cle; PL.formePersonnalisee = { preset: p.cle, group: g.nom }; dessiner();
            if (PL.choisirOutil && PL.etat.outil !== "customShape") PL.choisirOutil("customShape"); return; }
          if (genre === "styles") { if (PL.etat.doc) PL.executer(C.appliquer, { preset: p.cle, group: g.nom, ...(ev.shiftKey ? { add: true } : {}) }); dessiner(); return; }
          commande(C.choisir, { [C.champ]: p.cle });
        });
        // Double-clic : un calque de remplissage (dégradé, motif) ou la forme placée au centre (formes).
        b.addEventListener("dblclick", () => {
          if (!PL.etat.doc || genre === "styles") return;
          if (genre === "formes") PL.executer(C.appliquer, { preset: p.cle, group: g.nom, fill: fg });
          else PL.executer(C.appliquer, { [C.champ]: p.cle });
        });
        b.addEventListener("contextmenu", (ev) => menuContextuel(ev, p, g.nom));
        grille.appendChild(b);
      }
      liste.appendChild(grille);
    }
    bSuppr.disabled = !sel;
    if (E.doc) bNouveau.disabled = !PL.etat.doc;
  }
  PL.surCouleurs = PL.surCouleurs || [];
  PL.surCouleurs.push((c) => { if (c && c.fg) { fg = c.fg; bg = c.bg || bg; if (genre === "degrades") dessiner(); } });
  if (PL.surDoc) PL.surDoc.push(() => { if (E.doc) bNouveau.disabled = !PL.etat.doc; });
  PL.presets = PL.presets || {};
  PL.nomPreset = (n) => nomAffiche(n, T).texte;            // t156 : nom affiché d'une forme (barre de l'outil Forme personnalisée)
  PL.presets[genre] = { relire, groupes: () => groupes, courant: () => courant };
}
