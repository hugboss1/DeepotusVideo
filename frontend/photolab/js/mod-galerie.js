// mod-galerie.js — Filtre › Galerie de filtres (t157) : dossiers de catégories à vignettes, liste des filtres, réglages
// de l'effet choisi et PILE d'effets (œil, nouveau, supprimer, ordre), comme l'amont (gallery_ui.rs) et la référence.
// L'aperçu est celui des autres dialogues : le MOTEUR joue filter.filterGallery sur une copie (POST /apercu), l'image est
// posée sur la toile (zoomable). Les vignettes sont rendues par le moteur (GET /galerie/vignettes). Rouverte depuis un
// filtre dynamique, la galerie reprend sa pile et valide par layer.smartFilter.setParams (l'amont ne le sait pas).
// Fonctions PURES exportées (qa/masques.test.mjs).

import { champsVisibles, coercer, valeurInitiale } from "./mod-champs.js";
import { coquilleReglage, fabriquerControle, derniereGagne, chargerImage, identiteDocument, DELAI_APERCU } from "./mod-dialogue-reglage.js";
import { maxSideRequete } from "./mod-cycle.js";

const snake = (s) => String(s).replace(/[A-Z]/g, (c) => "_" + c.toLowerCase());
export const CATEGORIES = ["Artistic", "Brush Strokes", "Distort", "Sketch", "Stylize", "Texture"];
// « Brush Strokes » -> brush_strokes (un nom de catégorie est en mots, pas en camelCase).
export const cleCategorie = (c) => "photolab.galerie.cat." + String(c).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
export const cleFiltre = (k) => "photolab.galerie.f." + snake(k);
export const MAX_EFFETS = 20;                       // MAX_EFFETS_GALERIE du pont
export const FILTRE_DEPART = "coloredPencil";       // amont : la pile commence par Crayon de couleur
// Couleurs d'un effet : l'écran envoie celles de premier / arrière-plan au niveau de la commande, jamais par effet.
const CLES_COULEUR = new Set(["foreground", "background"]);

// Un effet : {filter, params, visible}. La pile est rangée comme le moteur l'applique : pile[0] d'abord (en BAS de la
// liste affichée).
export function effet(filter, params = {}, visible = true) { return { filter, params: { ...params }, visible }; }

// Nouveau calque d'effet : copie de l'effet choisi posée AU-DESSUS, et choisie (amont 110-115). Plein : rien.
export function nouvelEffet(pile, i) {
  if (!Array.isArray(pile) || !pile[i] || pile.length >= MAX_EFFETS) return { pile, i };
  const p = pile.slice();
  p.splice(i + 1, 0, effet(pile[i].filter, pile[i].params, pile[i].visible));
  return { pile: p, i: i + 1 };
}
// Supprimer : jamais le dernier effet (amont 117-121) ; la sélection passe à l'effet du dessous.
export function supprimerEffet(pile, i) {
  if (!Array.isArray(pile) || pile.length <= 1 || !pile[i]) return { pile, i };
  const p = pile.slice();
  p.splice(i, 1);
  return { pile: p, i: Math.max(0, Math.min(i - 1 < 0 ? 0 : i - 1, p.length - 1)) };
}
// Monter (+1, vers le haut de la liste = appliqué plus tard) ou descendre (-1).
export function deplacerEffet(pile, i, sens) {
  const j = i + sens;
  if (!Array.isArray(pile) || !pile[i] || j < 0 || j >= pile.length) return { pile, i };
  const p = pile.slice();
  [p[i], p[j]] = [p[j], p[i]];
  return { pile: p, i: j };
}
export function basculerEffet(pile, i) {
  if (!Array.isArray(pile) || !pile[i]) return pile;
  return pile.map((e, k) => (k === i ? { ...e, visible: !e.visible } : e));
}
// Changer le filtre de l'effet choisi : réglages remis aux défauts du nouveau filtre, visibilité gardée (amont 103-108).
export function changerFiltre(pile, i, cle) {
  if (!Array.isArray(pile) || !pile[i]) return pile;
  return pile.map((e, k) => (k === i ? effet(cle, {}, e.visible) : e));
}
export const auMoinsUnVisible = (pile) => Array.isArray(pile) && pile.some((e) => e && e.visible !== false);

// Champs ÉDITABLES d'un filtre de la galerie : les visibles du registre, plus glowColor (json : couleur de la lueur).
export function champsEffet(champs) {
  const vis = champsVisibles(champs);
  const lueur = (Array.isArray(champs) ? champs : []).find((c) => c && c.cle === "glowColor");
  return lueur ? [...vis, { ...lueur, type: "color", lueur: true }] : vis;
}
// [r, g, b(, a)] en 0..1 <-> « #rrggbb ».
export function lueurVersHex(v) {
  if (!Array.isArray(v) || v.length < 3) return "#ffffff";
  return "#" + v.slice(0, 3).map((x) => Math.round(Math.min(1, Math.max(0, Number(x) || 0)) * 255).toString(16).padStart(2, "0")).join("");
}
export function hexVersLueur(h) {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(h || ""));
  if (!m) return [1, 1, 1, 1];
  const n = parseInt(m[1], 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255, 1].map((x) => Math.round(x * 10000) / 10000);
}

// La pile telle que le pont l'admet : chaque valeur COERCÉE dans les bornes du registre (le moteur ramènerait en silence
// une valeur hors bornes au défaut du filtre), clés inconnues et couleurs d'effet retirées. champsDe(cle) -> champs du
// registre de filter.gallery.<cle>.
export function effetsEnvoyes(pile, champsDe) {
  return (Array.isArray(pile) ? pile : []).map((e) => {
    const champs = champsEffet(champsDe(e.filter));
    const params = {};
    for (const c of champs) {
      if (CLES_COULEUR.has(c.cle) || !(c.cle in (e.params || {}))) continue;
      const v = e.params[c.cle];
      params[c.cle] = c.lueur ? (Array.isArray(v) ? hexVersLueur(lueurVersHex(v)) : hexVersLueur(v)) : coercer(c, v, e.params);
    }
    return { filter: e.filter, params, visible: e.visible !== false };
  });
}
// Valeurs d'un effet pour le formulaire : défauts du registre complétés par ce que l'effet porte.
export function valeursEffet(e, champs) {
  const v = {};
  for (const c of champsEffet(champs)) {
    const connue = e && e.params ? e.params[c.cle] : undefined;
    v[c.cle] = c.lueur ? lueurVersHex(connue === undefined ? hexVersLueur(String(c.defaut || "#ffffff")) : connue)
      : valeurInitiale(c, connue, v);
  }
  return v;
}
// Une pile lue dans un filtre dynamique (params.effects du moteur : {filter, params|values, visible}) -> pile d'écran.
export function pileDepuis(effects) {
  const l = (Array.isArray(effects) ? effects : []).filter((e) => e && typeof e.filter === "string")
    .map((e) => effet(e.filter, e.params || e.values || {}, e.visible !== false));
  return l.length ? l : [effet(FILTRE_DEPART)];
}
// Catalogue du moteur ({categories, filters}) -> [{categorie, filtres: [{key, name}]}] dans l'ordre des catégories.
export function dossiers(catalogue) {
  const f = catalogue && Array.isArray(catalogue.filters) ? catalogue.filters : [];
  const cats = catalogue && Array.isArray(catalogue.categories) && catalogue.categories.length ? catalogue.categories : CATEGORIES;
  return cats.map((categorie) => ({ categorie, filtres: f.filter((x) => x.category === categorie).map((x) => ({ key: x.key, name: x.name })) }));
}

/* ───────────── côté DOM ───────────── */

export function initGalerie(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  let catalogue = null;
  let dernierePile = null;                // la pile de la dernière validation (l'amont reprend celle du journal)
  const vignettes = {};                   // révision -> {clé: data-URL}

  const nomFiltre = (k, nom) => { const r = T(cleFiltre(k)); return r && r !== cleFiltre(k) ? r : nom || k; };
  const champsDe = (cle) => {
    const r = (PL.menus && PL.menus.registre) || [];
    const e = (Array.isArray(r) ? r : []).find((x) => x && x.id === "filter.gallery." + cle);
    return e && Array.isArray(e.champs) ? e.champs : [];
  };
  async function lireCatalogue() {
    if (!catalogue) catalogue = await PL.get("/galerie");
    return catalogue;
  }

  // options : {pile, filtreDynamique: {layer, index}} (réédition depuis le panneau Calques).
  PL.ouvrirGalerie = async function ouvrirGalerie(options = {}) {
    if (!PL.etat.doc) return;
    let cat;
    try { cat = await lireCatalogue(); } catch (e) { return; }           // déjà signalé par mod-api
    construire(cat, options);
  };

  function construire(cat, options) {
    const fd = options.filtreDynamique || null;
    let pile = options.pile ? pileDepuis(options.pile) : dernierePile ? dernierePile.map((e) => effet(e.filter, e.params, e.visible)) : [effet(FILTRE_DEPART)];
    let choisi = pile.length - 1;
    let fini = false, apercuPose = false, minuterie = null;
    const etat = { identite: identiteDocument(PL.etat.doc, PL.etat.generation) };
    const coq = coquilleReglage(PL, {
      titre: T("photolab.galerie.titre"), classe: "pl-galerie", avecApercu: true,
      valider: () => fermer("ok"), annuler: () => fermer("annuler"),
      reinitialiser: () => { pile = [effet(FILTRE_DEPART)]; choisi = 0; tout(); planifier(); },
      surCaseApercu: (coche) => { if (coche) planifier(); else { demander.annuler(); if (apercuPose) { apercuPose = false; PL.cycle(); } } },
    });
    const el = (tag, classe, texte) => { const e = document.createElement(tag); if (classe) e.className = classe; if (texte != null) e.textContent = texte; return e; };
    const gauche = el("div", "gal-dossiers"), droite = el("div", "gal-reglages");
    const corpsG = el("div", "gal-corps");
    corpsG.append(gauche, droite);
    coq.corps.append(corpsG, coq.erreur);

    /* dossiers à vignettes */
    const revision = () => (PL.etat.doc ? PL.etat.doc.revision : 0);
    for (const d of dossiers(cat)) {
      const det = el("details", "gal-dossier");
      det.dataset.categorie = d.categorie;
      const sum = el("summary", "", T(cleCategorie(d.categorie)));
      const grille = el("div", "gal-grille");
      for (const f of d.filtres) {
        const b = el("button", "gal-vignette");
        b.type = "button"; b.dataset.cle = f.key;
        const im = el("img"); im.alt = "";
        b.append(im, el("span", "gal-nom", nomFiltre(f.key, f.name)));
        b.addEventListener("click", () => { pile = changerFiltre(pile, choisi, f.key); tout(); planifier(); });
        grille.appendChild(b);
      }
      det.append(sum, grille);
      det.addEventListener("toggle", () => { if (det.open) chargerVignettes(grille, d.filtres.map((f) => f.key)); });
      gauche.appendChild(det);
    }
    async function chargerVignettes(grille, cles) {
      const r = revision();
      const deja = vignettes[r] || (vignettes[r] = {});
      const manquent = cles.filter((k) => !deja[k]);
      for (let k = 0; k < manquent.length; k += 16) {
        try {
          const j = await PL.get("/galerie/vignettes?cles=" + encodeURIComponent(manquent.slice(k, k + 16).join(",")), true);
          Object.assign(deja, (j && j.vignettes) || {});
        } catch (e) { /* vignettes facultatives */ }
      }
      for (const b of grille.querySelectorAll(".gal-vignette")) {
        const u = deja[b.dataset.cle];
        if (u) b.querySelector("img").src = u;
      }
    }

    /* réglages de l'effet choisi + pile */
    const liste = el("select", "gal-liste");
    liste.setAttribute("aria-label", T("photolab.galerie.filtre"));
    for (const d of dossiers(cat)) {
      const g = el("optgroup"); g.label = T(cleCategorie(d.categorie));
      for (const f of d.filtres) { const o = el("option", "", nomFiltre(f.key, f.name)); o.value = f.key; g.appendChild(o); }
      liste.appendChild(g);
    }
    liste.addEventListener("change", () => { pile = changerFiltre(pile, choisi, liste.value); tout(); planifier(); });
    const reglages = el("div", "gal-params");
    const note = el("p", "gal-note");
    const pileEl = el("div", "gal-pile"); pileEl.setAttribute("role", "listbox"); pileEl.setAttribute("aria-label", T("photolab.galerie.pile"));
    const pied = el("div", "gal-pile-pied");
    const bouton = (ico, cle, f) => {
      const b = el("button", "pl-bouton-icone"); b.type = "button"; b.title = T(cle); b.setAttribute("aria-label", b.title);
      b.dataset.icone = ico; b.innerHTML = PL.icone(ico);
      b.addEventListener("click", f); return b;
    };
    const bMonter = bouton("dz-edit-monter", "photolab.galerie.monter", () => { ({ pile, i: choisi } = deplacerEffet(pile, choisi, 1)); tout(); planifier(); });
    const bDescendre = bouton("dz-edit-descendre", "photolab.galerie.descendre", () => { ({ pile, i: choisi } = deplacerEffet(pile, choisi, -1)); tout(); planifier(); });
    const bNouveau = bouton("dz-action-ajouter", "photolab.galerie.nouvel_effet", () => { ({ pile, i: choisi } = nouvelEffet(pile, choisi)); tout(); planifier(); });
    const bSupprimer = bouton("dz-action-supprimer", "photolab.galerie.supprimer_effet", () => { ({ pile, i: choisi } = supprimerEffet(pile, choisi)); tout(); planifier(); });
    pied.append(bMonter, bDescendre, el("span", "gal-espace"), bNouveau, bSupprimer);
    droite.append(liste, reglages, note, el("div", "gal-titre-pile", T("photolab.galerie.pile")), pileEl, pied);

    function dessinerReglages() {
      const e = pile[choisi];
      liste.value = e.filter;
      reglages.textContent = "";
      const champs = champsDe(e.filter);
      const effetChamps = champsEffet(champs);
      let valeurs = valeursEffet(e, champs);
      const ctx = {
        T, valeurs: () => valeurs,
        poser(c, brut, final) {
          const v = c.lueur ? String(brut) : coercer(c, brut, valeurs);
          valeurs = { ...valeurs, [c.cle]: v };
          pile = pile.map((x, k) => (k === choisi ? { ...x, params: { ...x.params, [c.cle]: c.lueur ? hexVersLueur(v) : v } } : x));
          const ctl = ctls.find((x) => x.c === c);
          if (ctl) ctl.ecrire(true);
          if (final) planifier();
        },
      };
      const ctls = [];
      for (const c of effetChamps) {
        const ctl = fabriquerControle(c.lueur ? { ...c, cleLibelle: "photolab.param.glowcolor" } : c, ctx);
        if (ctl) { ctls.push(ctl); reglages.appendChild(ctl.el); }
      }
      // le filtre se sert des couleurs de premier / arrière-plan (amont : note sous les réglages)
      note.textContent = champs.some((c) => CLES_COULEUR.has(c.cle)) ? T("photolab.galerie.note_couleurs") : "";
      note.hidden = !note.textContent;
    }
    function dessinerPile() {
      pileEl.textContent = "";
      for (let k = pile.length - 1; k >= 0; k--) {             // le haut de la pile en haut de la liste
        const e = pile[k];
        const l = el("div", "gal-effet" + (k === choisi ? " choisi" : "") + (e.visible === false ? " cache" : ""));
        l.setAttribute("role", "option"); l.setAttribute("aria-selected", k === choisi ? "true" : "false");
        l.dataset.index = String(k);
        const oeil = el("button", "gal-oeil"); oeil.type = "button";
        oeil.title = T(e.visible === false ? "photolab.calques.montrer" : "photolab.calques.masquer");
        oeil.setAttribute("aria-label", oeil.title);
        oeil.innerHTML = PL.icone(e.visible === false ? "dz-etat-cache" : "dz-etat-visible");
        oeil.addEventListener("click", (ev) => { ev.stopPropagation(); pile = basculerEffet(pile, k); tout(); planifier(); });
        l.append(oeil, el("span", "gal-effet-nom", nomFiltre(e.filter)));
        l.addEventListener("click", () => { choisi = k; tout(); });
        pileEl.appendChild(l);
      }
      bSupprimer.disabled = pile.length <= 1;
      bNouveau.disabled = pile.length >= MAX_EFFETS;
      bMonter.disabled = choisi >= pile.length - 1;
      bDescendre.disabled = choisi <= 0;
      for (const b of gauche.querySelectorAll(".gal-vignette")) b.classList.toggle("choisi", b.dataset.cle === pile[choisi].filter);
    }
    function tout() { dessinerReglages(); dessinerPile(); }

    /* aperçu du moteur */
    const demander = derniereGagne((c) => PL.api("POST", "/apercu", c, 0, true));
    const apercuActif = () => coq.caseApercu && coq.caseApercu.checked && !fini && !!PL.etat.doc;
    const commande = () => {
      const p = { effects: effetsEnvoyes(pile, champsDe), foreground: PL.etat.couleurs.fg, background: PL.etat.couleurs.bg };
      return fd ? { command: "layer.smartFilter.setParams", params: { layer: fd.layer, index: fd.index, params: p } } : { command: "filter.filterGallery", params: p };
    };
    function planifier() {
      clearTimeout(minuterie);
      if (!apercuActif()) return;
      minuterie = setTimeout(lancer, DELAI_APERCU);
    }
    async function lancer() {
      if (!apercuActif()) return;
      if (!auMoinsUnVisible(pile)) {                          // aucun effet visible : l'image telle quelle
        demander.annuler(); if (apercuPose) { apercuPose = false; PL.cycle(); } return;
      }
      const voulu = PL.vue.maxSideVoulu();
      coq.occupe(true);
      const r = await demander({ etapes: [commande()], maxSide: maxSideRequete(voulu, PL.etat.doc) });
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
    etat.surRenduReel = () => { if (apercuActif()) { apercuPose = false; planifier(); } };

    function fermer(role) {
      if (fini) return;
      fini = true;
      clearTimeout(minuterie);
      demander.annuler();
      coq.retirer();
      PL.libererReglage(etat);
      if (role === "ok") {
        if (!auMoinsUnVisible(pile)) { if (apercuPose) PL.cycle(); return; }      // amont : rien à appliquer
        dernierePile = pile.map((e) => effet(e.filter, e.params, e.visible));
        const c = commande();
        const efface = apercuPose;
        PL.executer(c.command, c.params).then((r) => { if (!(r && r.ok) && efface) PL.cycle(); });
      } else if (apercuPose) PL.cycle();
    }
    etat.fermer = fermer;
    PL.prendreReglage(etat);

    tout();
    coq.placer();
    const det = gauche.querySelector(`.gal-dossier[data-categorie="${(cat.filters.find((f) => f.key === pile[choisi].filter) || {}).category}"]`);
    if (det) det.open = true;                                 // le dossier du filtre choisi, ouvert (vignettes chargées)
    planifier();
  }

  // Filtre › Galerie de filtres… : l'entrée de menu (aiguillage « galerie » de mod-menus).
  PL.actions = PL.actions || {};
}
