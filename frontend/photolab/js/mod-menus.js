// mod-menus.js — la barre de menus du Photolab (B4), GÉNÉRÉE : l'arbre vient du catalogue de photocraft
// (donnees/menus.json : chemin, id, libellés fr/en, raccourci) croisé avec le registre du moteur
// (GET /api/photolab/commandes : quelles commandes existent, lesquelles sont actives, lesquelles ont des paramètres).
// Une entrée que le moteur ne connaît pas, ou que le pont refuse, reste affichée mais « bientôt » : la barre ressemble
// à celle de photocraft sans promettre ce qui n'est pas là. Toute la construction est PURE (qa/menus.test.mjs).

// Copie, en minuscules, de PREFIXES_REFUSES (backend/app/services/photolab_moteur.py) : le pont refuse ces commandes
// (fichiers, scripts, préférences…), l'écran les traite lui-même ou les marque « bientôt ». Un banc relit le source
// Python et compare : toute dérive rougit.
export const REFUSES = ["file.", "app.", "automate.", "plugin.", "script", "window.", "help.", "edit.preferences",
  "edit.presets", "edit.keyboardshortcuts", "edit.menus"];

// Entrées de fichier que l'écran exécute LUI-MÊME par ses routes (nouveau, ouvrir depuis la Bibliothèque, fermer,
// enregistrer, exporter) : actives même si le pont refuserait la commande moteur de ce nom.
export const TRAITES_PAR_ECRAN = new Set(["file.new", "file.open", "file.close", "file.save", "file.saveAs", "file.export.exportAs"]);
// … dont celles qui n'ont de sens qu'avec un document ouvert (grisées sur l'écran d'accueil).
export const NECESSITE_DOC = new Set(["file.close", "file.save", "file.saveAs", "file.export.exportAs"]);

// Le registre arrive en tableau ; on tolère {commands:[…]}.
export function indexRegistre(registre) {
  const liste = Array.isArray(registre) ? registre : (registre && Array.isArray(registre.commands) ? registre.commands : []);
  const m = new Map();
  for (const c of liste) if (c && c.id) m.set(c.id, c);
  return m;
}

// « {} », vide ou absent = aucun paramètre ; « {radius} » = des paramètres à saisir (dialogues générés en P3).
export function parametresRequis(texte) {
  const s = String(texte == null ? "" : texte).replace(/\s+/g, "");
  return s !== "" && s !== "{}";
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

// catalogue = donnees/menus.json ; registre = GET /api/photolab/commandes ; refuses = REFUSES ; lang = "fr"|"en" ;
// t = traducteur (dzT) pour le menu « Aide » ajouté en dernier (le catalogue s'arrête à Window).
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
      libelle: (lang === "fr" ? e.libelle_fr || e.libelle_en : e.libelle_en || e.libelle_fr) || e.id,
      raccourci: raccourciAffiche(e.raccourci, lang),
      etat: etatDe(e.id, idx, refuses),
      parametres: r ? parametresRequis(r.params) : false,
    });
  }
  for (const m of menus) m.entrees = nettoyer(m.entrees);
  menus.push({
    nom: "Aide", nom_affiche: t("photolab.menu.aide"),
    entrees: [{ type: "commande", id: "pl.apropos", libelle: t("photolab.menu.apropos"), raccourci: "", etat: "actif", parametres: false }],
  });
  return menus.filter((m) => m.entrees.length);
}

// Que fait un clic sur cette entrée ? ecran | apropos | executer | dialogue | rien
export function actionEntree(entree) {
  if (!entree || entree.type === "separateur") return "rien";
  if (entree.id === "pl.apropos") return "apropos";
  if (entree.etat !== "actif") return "rien";
  if (TRAITES_PAR_ECRAN.has(entree.id)) return "ecran";
  return entree.parametres ? "dialogue" : "executer";
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
    // Relit le registre (l'état « actif » des commandes dépend du document ouvert) puis reconstruit l'arbre.
    async rafraichir() {
      // Silencieux : un rafraîchissement d'arrière-plan n'a pas à ouvrir un toast (moteur absent = menus « bientôt »).
      try { registre = await PL.get("/commandes", true); dernierRegistre = Date.now(); } catch (e) { /* menus sans registre */ }
      reconstruire();
    },
    // Active une entrée de commande comme un clic (raccourcis clavier, C1) : même chemin que la souris.
    activer(entree) { return activer(null, { entree }); },
  };

  function reconstruire() {
    if (!catalogue) return;
    if (ouvert >= 0) { aReconstruire = true; return; }      // jamais sous les doigts de l'utilisateur
    menus = construireMenus(catalogue, registre, REFUSES, lang(), T);
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
        if (f) f(); else PL.signaler(T("photolab.menu.bientot"));
        break;
      }
      case "apropos": apropos(); break;
      case "executer":
        try { await PL.post("/executer", { command: e.id, params: {} }); } catch (err) { return; }     // signalé par mod-api
        if (PL.cycle) PL.cycle(); else PL.menus.rafraichir();
        break;
      case "dialogue":
        informer(T("photolab.menu.p3", { nom: e.libelle.replace(/…$/, "") }));
        break;
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
