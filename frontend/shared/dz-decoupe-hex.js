// Plateau hexagonal, lot 1 (tâche 5) — le dialogue partagé « Découper en hexagones ».
//
// Un lab (Photolab, Vectorlab) l'ouvre avec son image : l'utilisateur choisit le format d'hexagone, le nombre de
// colonnes et de rangées, cadre l'image (glisser, molette ou curseur), nomme le jeu, puis « Créer le jeu plateau ».
// Au clic, le lab fournit l'image dans la Bibliothèque (`fournirImage`), la route POST /api/cards/decks/plateau
// découpe et crée le jeu, et le Card Forge s'ouvre dessus.
//
//   ouvrirDecoupeHex({ largeur, hauteur, apercu, nomImage, fournirImage, T, fetch?, depart? })
//     -> Promise<{ deck, tuiles } | null>   (null : fermé sans créer)
//
// `largeur`, `hauteur` : pixels de l'image du lab. `apercu` : canvas ou ImageBitmap dessinable (n'importe quelle
// taille, même rapport). `fournirImage({ largeurMm, hauteurMm })` : rend le nom de l'image dans la Bibliothèque ;
// appelé au clic sur « Créer » seulement, et pas deux fois pour la même étendue (un nouvel essai après une erreur du
// serveur réutilise l'image déjà rangée). `T(clé, vars)` : le traducteur du lab. `depart` (facultatif) :
// { format, colonnes, rangees, zoom, x, y } pour rouvrir avec les derniers réglages.
//
// Tout texte passe par T (clés decoupehex.*, frontend/shared/i18n/decoupehex.json, dans le dictionnaire assemblé que
// chaque lab charge déjà). Le `detail` des refus du serveur arrive déjà traduit (L10) : il est affiché tel quel.
// Pas d'innerHTML : tout ce qui vient du serveur ou du lab passe par textContent. La feuille est posée par le module.

import { FORMATS_HEX, COTE_MAX, TUILES_MAX, PIXELS_MAX, grille, cadrageCouvrant, pppEffectif } from "./dz-decoupe-hex-logique.js";

const FORMAT_DEFAUT = "hex_p90";
const DPI_TRAVAIL = 300;        // le dpi par défaut de la route : le plafond de pixels se juge à ce dpi
const PPP_MIN = 300;
const ZOOM_MAX = 8;
const APERCU_MAX = 480;         // plus grand côté du canvas d'aperçu, en pixels
const VITESSE_MOLETTE = 0.002;
const PAS_CLAVIER = 0.02;       // fraction de la course du cadre, par appui sur une flèche
const ROUTE = "/api/cards/decks/plateau";
const FEUILLE = new URL("./dz-decoupe-hex.css", import.meta.url).href;

let courant = null;             // un seul dialogue à la fois : { fin, occupe(), promesse }

/** Pixels de l'image de travail d'une grille au dpi par défaut (même formule que plateau.pixels_travail). */
function pixelsTravail(g) {
  return Math.max(1, Math.round(g.largeurMm / 25.4 * DPI_TRAVAIL)) * Math.max(1, Math.round(g.hauteurMm / 25.4 * DPI_TRAVAIL));
}

const entierBorne = (v) => Number.isInteger(v) && v >= 1 && v <= COTE_MAX;
const borner = (v, a, b) => Math.min(b, Math.max(a, v));

/** La grille de l'état, ou la clé de la phrase qui explique pourquoi elle est refusée. */
function verifier(S) {
  if (!entierBorne(S.colonnes) || !entierBorne(S.rangees)) return { cle: "decoupehex.grille.borne", vars: { max: COTE_MAX } };
  const total = S.colonnes * S.rangees;
  if (total > TUILES_MAX) return { cle: "decoupehex.grille.tuiles_max", vars: { n: total, max: TUILES_MAX } };
  const g = grille(S.format, S.colonnes, S.rangees);
  const px = pixelsTravail(g);
  if (px > PIXELS_MAX) {
    return { cle: "decoupehex.grille.pixels_max", vars: { mpx: Math.ceil(px / 1e6), max: Math.floor(PIXELS_MAX / 1e6) } };
  }
  return { g };
}

/** Le `detail` d'un refus du serveur (chaîne, ou objet { message | texte }). */
function detailDe(j) {
  const d = j && j.detail;
  if (typeof d === "string") return d;
  return d && (d.message || d.texte) ? String(d.message || d.texte) : "";
}

function el(tag, cls) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  return e;
}
const marque = (e, nom) => { e.setAttribute("data-dh", nom); return e; };

function poserFeuille() {
  if (document.getElementById("dz-dh-css")) return;
  const l = el("link");
  l.id = "dz-dh-css";
  l.setAttribute("rel", "stylesheet");
  l.href = FEUILLE;
  document.head.appendChild(l);
}

/** Sommets (px canvas) de l'hexagone de centre (cx, cy) ; rayon `r` ; pointe en haut ou côté plat en haut. */
function sommets(cx, cy, r, pointe) {
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const a = (pointe ? -90 : 0) * Math.PI / 180 + i * Math.PI / 3;
    pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
  }
  return pts;
}

export async function ouvrirDecoupeHex({ largeur, hauteur, apercu, nomImage, fournirImage, T, fetch = (...a) => window.fetch(...a), depart } = {}) {
  // une création en cours (image rangée, POST parti) ne se remplace pas : on rend la promesse du dialogue ouvert
  if (courant && courant.occupe()) return courant.promesse;
  if (courant) courant.fin(null);
  poserFeuille();
  const avant = document.activeElement;      // rendu à la fermeture

  const d = depart || {};
  const S = {
    format: FORMATS_HEX[d.format] ? d.format : FORMAT_DEFAUT,
    colonnes: Number.isInteger(d.colonnes) ? d.colonnes : 4,
    rangees: Number.isInteger(d.rangees) ? d.rangees : 3,
    zoom: borner(Number(d.zoom) || 1, 1, ZOOM_MAX),
    x: borner(d.x == null ? 0.5 : Number(d.x), 0, 1),
    y: borner(d.y == null ? 0.5 : Number(d.y), 0, 1),
    occupe: false,
    cree: false,                 // le jeu existe : plus rien ne doit relancer la création
  };
  const dejaRangees = {};        // étendue -> nom de l'image déjà rangée dans la Bibliothèque

  /* ── le DOM ── */
  const voile = el("div", "dz-dh");
  voile.setAttribute("role", "dialog");
  voile.setAttribute("aria-modal", "true");
  voile.setAttribute("aria-label", T("decoupehex.dialogue.titre"));
  const boite = el("div", "dz-dh-box");
  const tete = el("div", "dz-dh-head");
  const titre = el("b");
  titre.textContent = T("decoupehex.dialogue.titre");
  const croix = marque(el("button", "dz-dh-btn dz-dh-fermer"), "fermer");
  croix.type = "button";
  croix.textContent = "×";
  croix.setAttribute("aria-label", T("decoupehex.dialogue.fermer"));
  croix.title = T("decoupehex.dialogue.fermer");
  tete.appendChild(titre);
  tete.appendChild(croix);

  const corps = el("div", "dz-dh-corps");
  const gauche = el("div", "dz-dh-vue");
  const canvas = marque(el("canvas", "dz-dh-apercu"), "apercu");
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", T("decoupehex.cadrage.apercu"));
  canvas.setAttribute("tabindex", "0");
  canvas.title = T("decoupehex.cadrage.apercu");
  const compteur = marque(el("div", "dz-dh-note"), "tuiles");
  gauche.appendChild(canvas);
  gauche.appendChild(compteur);

  const droite = el("div", "dz-dh-regl");
  const ligne = (texte, controle) => {
    const l = el("label", "dz-dh-champ");
    const s = el("span");
    s.textContent = texte;
    l.appendChild(s);
    l.appendChild(controle);
    droite.appendChild(l);
    return controle;
  };
  const selFormat = marque(el("select", "dz-dh-in"), "format");
  Object.keys(FORMATS_HEX).forEach((id) => {
    const o = el("option");
    o.value = id;
    o.textContent = T("decoupehex.format." + id);
    selFormat.appendChild(o);
  });
  selFormat.value = S.format;
  ligne(T("decoupehex.format.libelle"), selFormat);
  const nombre = (nom, texte, valeur) => {
    const i = marque(el("input", "dz-dh-in"), nom);
    i.type = "number";
    i.setAttribute("min", "1");
    i.setAttribute("max", String(COTE_MAX));
    i.setAttribute("step", "1");
    i.value = String(valeur);
    ligne(texte, i);
    return i;
  };
  const inCol = nombre("colonnes", T("decoupehex.grille.colonnes"), S.colonnes);
  const inRan = nombre("rangees", T("decoupehex.grille.rangees"), S.rangees);
  const inZoom = marque(el("input", "dz-dh-in"), "zoom");
  inZoom.type = "range";
  inZoom.setAttribute("min", "1");
  inZoom.setAttribute("max", String(ZOOM_MAX));
  inZoom.setAttribute("step", "0.01");
  inZoom.value = String(S.zoom);
  ligne(T("decoupehex.cadrage.zoom"), inZoom);
  const nomDefaut = T("decoupehex.jeu.nom_defaut", { nom: nomImage });
  const inNom = marque(el("input", "dz-dh-in"), "nom");
  inNom.type = "text";
  inNom.value = nomDefaut;
  ligne(T("decoupehex.jeu.nom"), inNom);
  const inVerso = marque(el("input", "dz-dh-in"), "verso");
  inVerso.type = "text";
  inVerso.setAttribute("placeholder", T("decoupehex.jeu.verso_aide"));
  ligne(T("decoupehex.jeu.verso"), inVerso);

  const infoPpp = marque(el("div", "dz-dh-note"), "ppp");
  const alerte = marque(el("div", "dz-dh-note dz-dh-alerte"), "alerte");
  const borneMsg = marque(el("div", "dz-dh-note dz-dh-ko"), "borne");
  borneMsg.setAttribute("role", "alert");
  droite.appendChild(infoPpp);
  droite.appendChild(alerte);
  droite.appendChild(borneMsg);
  corps.appendChild(gauche);
  corps.appendChild(droite);

  const pied = el("div", "dz-dh-pied");
  const message = marque(el("span", "dz-dh-msg"), "message");
  message.setAttribute("role", "status");
  const annuler = marque(el("button", "dz-dh-btn"), "annuler");
  annuler.type = "button";
  annuler.textContent = T("commun.action.annuler");
  const creer = marque(el("button", "dz-dh-btn dz-dh-fort"), "creer");
  creer.type = "button";
  creer.textContent = T("decoupehex.dialogue.creer");
  pied.appendChild(message);
  pied.appendChild(annuler);
  pied.appendChild(creer);

  boite.appendChild(tete);
  boite.appendChild(corps);
  boite.appendChild(pied);
  voile.appendChild(boite);
  document.body.appendChild(voile);

  /* ── le cadrage courant et l'aperçu ── */
  const etendue = () => { const v = verifier(S); return v.g || null; };
  const rectCourant = (g) => cadrageCouvrant(largeur, hauteur, g.largeurMm, g.hauteurMm, S.zoom, S.x, S.y);

  let accent = null;             // lu une fois (jeton de la charte)

  function dessiner(g) {
    const k = Math.min(APERCU_MAX / g.largeurMm, APERCU_MAX / g.hauteurMm);
    canvas.width = Math.max(1, Math.round(g.largeurMm * k));
    canvas.height = Math.max(1, Math.round(g.hauteurMm * k));
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const r = rectCourant(g);
    const ex = apercu.width / largeur, ey = apercu.height / hauteur;
    ctx.drawImage(apercu, r.x * ex, r.y * ey, r.w * ex, r.h * ey, 0, 0, canvas.width, canvas.height);
    const f = FORMATS_HEX[S.format];
    const rayon = f.p / Math.sqrt(3) * (canvas.width / g.largeurMm);
    const pxMm = canvas.width / g.largeurMm;
    if (accent === null) {
      try { accent = String(window.getComputedStyle(voile).getPropertyValue("--accent") || "").trim(); } catch (e) { accent = ""; }
    }
    // chaque contour, plein : un trait sombre sous le trait clair (lisible sur toute image) ; le fond perdu n'est pas dessiné
    const trait = accent || "#ffffff";
    if (ctx.setLineDash) ctx.setLineDash([]);
    g.centres.forEach((c) => {
      const pts = sommets(c.x * pxMm, c.y * pxMm, rayon, f.o === "pointe");
      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      for (let i = 1; i < 6; i++) ctx.lineTo(pts[i][0], pts[i][1]);
      ctx.closePath();
      ctx.strokeStyle = "rgba(0,0,0,0.65)";
      ctx.lineWidth = 3.5;
      ctx.stroke();
      ctx.strokeStyle = trait;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    });
  }

  function rafraichir() {
    const v = verifier(S);
    borneMsg.textContent = v.g ? "" : T(v.cle, v.vars);
    creer.disabled = !v.g || S.occupe || S.cree;
    if (!v.g) {
      compteur.textContent = "";
      infoPpp.textContent = "";
      alerte.textContent = "";
      alerte.hidden = true;
      return;
    }
    compteur.textContent = T("decoupehex.grille.tuiles", { n: v.g.centres.length });
    const ppp = Math.round(pppEffectif(rectCourant(v.g).w, v.g.largeurMm));
    infoPpp.textContent = T("decoupehex.cadrage.ppp", { ppp });
    const faible = ppp < PPP_MIN;
    alerte.textContent = faible ? T("decoupehex.cadrage.ppp_faible", { min: PPP_MIN }) : "";
    alerte.hidden = !faible;
    dessiner(v.g);
  }

  const poserZoom = (z) => {
    S.zoom = borner(Number.isFinite(z) ? z : 1, 1, ZOOM_MAX);
    inZoom.value = String(S.zoom);
    rafraichir();
  };

  /* ── les gestes ── */
  selFormat.addEventListener("change", () => { if (FORMATS_HEX[selFormat.value]) { S.format = selFormat.value; rafraichir(); } });
  const surGrille = () => { S.colonnes = Number(inCol.value); S.rangees = Number(inRan.value); rafraichir(); };
  ["input", "change"].forEach((t) => { inCol.addEventListener(t, surGrille); inRan.addEventListener(t, surGrille); });
  ["input", "change"].forEach((t) => inZoom.addEventListener(t, () => poserZoom(Number(inZoom.value))));
  canvas.addEventListener("wheel", (ev) => {
    ev.preventDefault();
    if (S.cree) return;
    poserZoom(S.zoom * Math.exp(-ev.deltaY * VITESSE_MOLETTE));
  });
  let prise = null;
  canvas.addEventListener("pointerdown", (ev) => {
    const g = etendue();
    if (!g || S.cree) return;
    prise = { px: ev.clientX, py: ev.clientY, r: rectCourant(g), x: S.x, y: S.y };
    if (canvas.setPointerCapture && ev.pointerId != null) { try { canvas.setPointerCapture(ev.pointerId); } catch (e) { /* capture refusée : le glisser continue dans le canvas */ } }
  });
  canvas.addEventListener("pointermove", (ev) => {
    if (!prise) return;
    const rect = canvas.getBoundingClientRect ? canvas.getBoundingClientRect() : null;
    const cw = (rect && rect.width) || canvas.width, ch = (rect && rect.height) || canvas.height;
    // l'image suit le doigt : le cadre source se déplace en sens inverse ; une fraction n'a de sens que si l'image
    // dépasse le cadre sur cet axe
    const jeuX = largeur - prise.r.w, jeuY = hauteur - prise.r.h;
    S.x = prise.x;
    S.y = prise.y;
    if (jeuX > 1e-9 && ev.clientX !== prise.px) S.x = borner((prise.r.x - (ev.clientX - prise.px) * prise.r.w / cw) / jeuX, 0, 1);
    if (jeuY > 1e-9 && ev.clientY !== prise.py) S.y = borner((prise.r.y - (ev.clientY - prise.py) * prise.r.h / ch) / jeuY, 0, 1);
    rafraichir();
  });
  const lacher = () => { prise = null; };
  canvas.addEventListener("pointerup", lacher);
  // clavier : les flèches déplacent le cadre d'un petit pas (même sens que le glisser : l'image suit la flèche)
  canvas.addEventListener("keydown", (ev) => {
    const pas = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[ev.key];
    if (!pas || S.cree) return;
    ev.preventDefault();
    S.x = borner(S.x - pas[0] * PAS_CLAVIER, 0, 1);
    S.y = borner(S.y - pas[1] * PAS_CLAVIER, 0, 1);
    rafraichir();
  });
  canvas.addEventListener("pointercancel", lacher);

  const promesse = new Promise((resoudre) => {
    let clos = false;
    const fin = (valeur) => {
      if (clos) return;
      clos = true;
      document.removeEventListener("keydown", surTouche);
      voile.remove();
      if (courant && courant.fin === fin) courant = null;
      try { if (avant && avant.focus) avant.focus(); } catch (e) { /* l'élément n'existe plus : rien à rendre */ }
      resoudre(valeur);
    };
    function surTouche(ev) {
      if (!ev) return;
      if (ev.key === "Escape" && !S.occupe) { ev.preventDefault(); fin(null); }
      else if (ev.key === "Tab") {                       // le Tab reste dans le dialogue (aria-modal)
        const f = Array.prototype.slice.call(voile.querySelectorAll("input, select, button, a, canvas[tabindex]"))
          .filter((x) => !x.disabled && !x.hidden);
        if (!f.length) return;
        ev.preventDefault();
        const i = f.indexOf(document.activeElement);
        f[((ev.shiftKey ? (i < 0 ? 0 : i - 1) : i + 1) + f.length) % f.length].focus();
      }
    }
    courant = { fin, occupe: () => S.occupe, promesse: null };
    document.addEventListener("keydown", surTouche);
    croix.addEventListener("click", () => { if (!S.occupe) fin(null); });
    annuler.addEventListener("click", () => { if (!S.occupe) fin(null); });

    async function lancer() {
      const v = verifier(S);
      if (!v.g || S.occupe || S.cree) return;
      S.occupe = true;
      message.textContent = T("decoupehex.dialogue.creation");
      message.className = "dz-dh-msg";
      rafraichir();
      try {
        const cle = v.g.largeurMm + "x" + v.g.hauteurMm;
        if (!dejaRangees[cle]) dejaRangees[cle] = await fournirImage({ largeurMm: v.g.largeurMm, hauteurMm: v.g.hauteurMm });
        const corpsPost = {
          image: dejaRangees[cle], format: S.format, colonnes: S.colonnes, rangees: S.rangees,
          cadrage: { zoom: S.zoom, x: S.x, y: S.y },
        };
        const nom = inNom.value.trim();
        if (nom) corpsPost.name = nom;
        const verso = inVerso.value.trim();
        if (verso) corpsPost.verso_commun = verso;
        let rep;
        try {
          rep = await fetch(ROUTE, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpsPost) });
        } catch (e) {
          throw new Error(T("decoupehex.erreur.reseau"));     // le texte du navigateur est en anglais : on donne le nôtre
        }
        const j = await rep.json().catch(() => ({}));
        if (!rep.ok) throw new Error(detailDe(j) || T("decoupehex.erreur.http", { code: rep.status }));
        const adresse = "/cardforge/?deck=" + encodeURIComponent(j.deck.id);
        const fenetre = window.open(adresse);
        if (fenetre) { fin({ deck: j.deck, tuiles: j.tuiles }); return; }
        // popup bloquée (la création a pris du temps) : le jeu existe, un lien l'ouvre
        message.textContent = T("decoupehex.dialogue.ouvert_bloque") + " ";
        const lien = marque(el("a", "dz-dh-lien"), "lien");
        lien.href = adresse;
        lien.setAttribute("target", "_blank");
        lien.setAttribute("rel", "noopener");
        lien.textContent = T("decoupehex.dialogue.ouvrir_lien");
        message.appendChild(lien);
        S.occupe = false;
        S.cree = true;
        [selFormat, inCol, inRan, inZoom, inNom, inVerso].forEach((c) => { c.disabled = true; });
        rafraichir();
        resoudre({ deck: j.deck, tuiles: j.tuiles });
      } catch (e) {
        S.occupe = false;
        message.textContent = String((e && e.message) || e);
        message.className = "dz-dh-msg dz-dh-ko";
        rafraichir();
      }
    }
    creer.addEventListener("click", lancer);
    rafraichir();
    try { selFormat.focus(); } catch (e) { /* pas de focus : le dialogue reste utilisable */ }
  });
  courant.promesse = promesse;
  return promesse;
}
