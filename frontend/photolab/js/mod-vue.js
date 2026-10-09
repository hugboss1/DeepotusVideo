// mod-vue.js — le canevas du Photolab (B2) : zoom, main, conversions écran <-> document, taille de rendu.
// Tout ce qui se calcule est une fonction PURE exportée (bancable sous node, qa/vue.test.mjs) ; initVue(PL) ne fait que
// brancher ces fonctions sur le DOM. L'écran n'invente aucun pixel : le canevas ne fait que dessiner le dernier rendu
// du moteur (/api/photolab/rendu), mis à l'échelle de la vue.

// Zoom par paliers de photocraft (canvas.rs:353-358, inventaire B §8) : 1 % … 6400 %.
export const PALIERS = [0.01, 0.02, 0.03, 0.04, 0.05, 0.0625, 0.0833, 0.125, 0.1667, 0.25, 0.3333, 0.5, 0.6667, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 32, 64];
export const ZOOM_MIN = 0.01;
export const ZOOM_MAX = 64;
const EPS = 1e-6;   // 0.6667 saisi à la main ne doit pas se voir « avant » le palier 0.6667 à cause d'un arrondi flottant

const borner = (z) => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, z));

// sens +1 : premier palier strictement > z ; -1 : dernier strictement < z ; borné aux extrêmes.
export function palier(z, sens) {
  if (sens > 0) {
    for (const p of PALIERS) if (p > z + EPS) return p;
    return PALIERS[PALIERS.length - 1];
  }
  for (let i = PALIERS.length - 1; i >= 0; i--) if (PALIERS[i] < z - EPS) return PALIERS[i];
  return PALIERS[0];
}

// Zoom qui fait tenir doc {w,h} dans vue {w,h}, avec `marge` px LIBRES de chaque côté.
// (Le plan donnait 0.5389 pour 1920×1080 dans 1000×600 : valeur qui déborde la largeur — 1920 × 0.5389 > 1000 —
//  donc inatteignable par un « ajuster » ; le banc fixe la formule saine min((W-2m)/w, (H-2m)/h).)
export function ajuster(doc, vue, marge = 16) {
  const libreW = vue.w - 2 * marge, libreH = vue.h - 2 * marge;
  if (!(libreW > 0) || !(libreH > 0) || !(doc.w > 0) || !(doc.h > 0)) return ZOOM_MIN;
  return borner(Math.min(libreW / doc.w, libreH / doc.h));
}

// écran -> document : ((x - ox) / z, (y - oy) / z). t152 : en miroir (Affichage › Symétrie horizontale, v.miroir, v.dw =
// largeur du document), x document = dw - (x - ox) / z — la VUE seule est retournée, jamais le document.
export function versDoc(v, x, y) {
  const dx = (x - v.ox) / v.z;
  return { x: v.miroir ? v.dw - dx : dx, y: (y - v.oy) / v.z };
}
// document -> écran
export function versEcran(v, x, y) { return { x: (v.miroir ? v.dw - x : x) * v.z + v.ox, y: y * v.z + v.oy }; }
// Rectangle document {x, y, w, h} -> rectangle écran à largeur positive (miroir compris).
export function rectVersEcran(v, x, y, w, h) {
  const a = versEcran(v, x, y), b = versEcran(v, x + w, y + h);
  return { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), w: Math.abs(b.x - a.x), h: Math.abs(b.y - a.y) };
}

// Nouveau v {z, ox, oy} qui garde le point écran (px,py) fixe. Le zoom est borné AVANT de calculer l'origine, sinon le
// point dérive quand on bute sur une borne.
export function zoomAutour(v, z2, px, py) {
  const z = borner(z2);
  const k = z / v.z;
  return { z, ox: px - (px - v.ox) * k, oy: py - (py - v.oy) * k };
}

export function panoramique(v, dx, dy) { return { z: v.z, ox: v.ox + dx, oy: v.oy + dy }; }

// maxSide à demander au moteur pour un zoom donné. 0 = taille réelle (le moteur n'accepte que 2048 au plus,
// sauf 0) : utile quand on zoome au-delà de 200 % sur un document pas trop grand.
export function tailleRendu(doc, z, dpr = 1) {
  const grand = Math.max(doc.w, doc.h);
  const besoin = Math.ceil(grand * z * dpr);
  if (besoin > 2048) return grand <= 4096 ? 0 : 2048;      // au-delà : flou assumé, dit dans le statut
  return Math.min(Math.max(besoin, 64), grand);            // jamais plus que le document, jamais moins de 64
}

// Faut-il redemander un rendu ? Oui quand la taille demandée change de plus de `seuil` (25 %) par rapport à celle du
// rendu affiché. 0 (taille réelle) n'est comparable à rien : on ne divise jamais par 0.
// `grand` (facultatif) = grand côté du document : 0 vaut alors `grand`, ce qui évite un rendu redondant quand le zoom
// repasse de la taille réelle à un maxSide égal au document.
export function changementSensible(ancien, nouveau, seuil = 0.25, grand = 0) {
  if (ancien == null) return true;
  if (grand > 0) { if (ancien === 0) ancien = grand; if (nouveau === 0) nouveau = grand; }
  if (ancien === nouveau) return false;
  if (ancien === 0 || nouveau === 0) return true;
  return Math.abs(nouveau - ancien) / ancien > seuil;
}

// Interprétation d'un événement molette : Ctrl (ou pincement, que le navigateur rapporte avec ctrlKey) = zoom continu ;
// Alt = ×1,05 par cran ; sinon panoramique, Maj = horizontal. t159 : préférence « Zoom avec la molette » — la molette
// seule zoome, Maj garde le panoramique horizontal.
export function gesteMolette(e, zoomMolette = false) {
  const dx = e.deltaX || 0, dy = e.deltaY || 0;
  if (e.ctrlKey || (zoomMolette && !e.shiftKey && !e.altKey)) return { type: "zoom", facteur: Math.exp(-dy * 0.0015) };
  if (e.altKey) return { type: "zoom", facteur: dy < 0 ? 1.05 : dy > 0 ? 1 / 1.05 : 1 };
  if (e.shiftKey) return { type: "pan", dx: -(dy || dx), dy: 0 };
  return { type: "pan", dx: -dx, dy: -dy };
}

// Tuiles du damier réellement visibles : intersection du document (origine v.ox/v.oy, taille doc × zoom) avec la vue.
// Indices relatifs à l'origine du document, bornes incluses ; i1 < i0 = rien à dessiner. Le nombre de tuiles est borné
// par la taille de la vue, jamais par celle du document (à 6400 % un document de 1920 px fait 122880 px de large).
export function tuilesVisibles(v, doc, vue, t = 8) {
  const W = doc.w * v.z, H = doc.h * v.z;
  const xa = Math.max(v.ox, 0), xb = Math.min(v.ox + W, vue.w);
  const ya = Math.max(v.oy, 0), yb = Math.min(v.oy + H, vue.h);
  if (!(xa < xb) || !(ya < yb)) return { i0: 0, i1: -1, j0: 0, j1: -1 };
  return {
    i0: Math.floor((xa - v.ox) / t), i1: Math.ceil((xb - v.ox) / t) - 1,
    j0: Math.floor((ya - v.oy) / t), j1: Math.ceil((yb - v.oy) / t) - 1,
  };
}

// Raccourcis de zoom par e.code (position physique : « 0 » est « à » en AZERTY), e.key en repli quand le code manque
// ou n'est pas l'un des nôtres. -> "ajuster" | "cent" | "plus" | "moins" | null
const CODES_ZOOM = { Digit0: "ajuster", Numpad0: "ajuster", Digit1: "cent", Numpad1: "cent", Equal: "plus", NumpadAdd: "plus", Minus: "moins", NumpadSubtract: "moins" };
const TOUCHES_ZOOM = { "0": "ajuster", "1": "cent", "=": "plus", "+": "plus", "-": "moins", "_": "moins" };
export function toucheZoom(e) {
  if (e.code && CODES_ZOOM[e.code]) return CODES_ZOOM[e.code];
  return TOUCHES_ZOOM[e.key] || null;
}

// « 50 % » en français (virgule décimale), « 50% » en anglais.
export function formaterZoom(z, lang = "fr") {
  const pct = Math.round(z * 10000) / 100;
  return lang === "fr" ? String(pct).replace(".", ",") + " %" : pct + "%";
}

// Un Ctrl+molette ne doit jamais zoomer la page, où que se trouve le pointeur dans le lab.
export const ctrlSurPage = (e) => !!(e && e.ctrlKey);

/* ───────────── côté DOM ───────────── */

export function initVue(PL) {
  const toile = PL.$("#toile");
  const scene = PL.$("#scene");
  const ctx = toile.getContext("2d");
  const v = { z: 1, ox: 0, oy: 0 };
  const vue = {
    v,                       // lecture seule pour les autres modules (outils : versDoc via PL.vue.versDoc)
    rendu: null,             // {image, maxSide} : dernier rendu dessiné
    mainTemporaire: false,   // Espace tenu
  };
  PL.vue = vue;

  const dims = () => {
    const d = PL.etat.doc;
    return d && d.width > 0 ? { w: d.width, h: d.height } : null;
  };
  const taillePx = () => ({ w: toile.clientWidth, h: toile.clientHeight });
  const dpr = () => (window.devicePixelRatio || 1);
  const lang = () => (window.dzLang ? window.dzLang() : "fr");
  // Les jetons sont lus UNE fois par redessin (getComputedStyle est cher) ; le repli neutre ne sert que si la feuille de
  // jetons ne s'est pas chargée (page ouverte hors de l'application).
  const REPLI = "#808080";
  let jetons = null;
  const lireJetons = () => {
    const cs = getComputedStyle(document.documentElement);
    const lire = (n) => cs.getPropertyValue(n).trim() || REPLI;
    jetons = { c1: lire("--bg-panel"), c2: lire("--bg-panel-2"), trait: lire("--stroke-strong") };
  };
  // Curseur de l'outil courant (mod-outils le définit) ; repli si les outils ne sont pas montés.
  const curseur = () => {
    if (PL.curseur) PL.curseur();
    else toile.style.cursor = vue.mainActive() ? "grab" : "";
  };

  vue.versDoc = (x, y) => versDoc(v, x, y);
  vue.versEcran = (x, y) => versEcran(v, x, y);
  // Coordonnées d'un événement souris dans le repère CSS du canevas.
  vue.pointeur = (ev) => { const r = toile.getBoundingClientRect(); return { x: ev.clientX - r.left, y: ev.clientY - r.top }; };

  // Damier de transparence : seules les tuiles de l'intersection document ∩ vue sont dessinées (borné par la vue).
  const T_DAMIER = 8;
  function damier(x, y, w, h, d, taille) {
    // t159 : Préférences › Transparence — taille des cases (aucune = fond blanc) et couleurs (null = le thème)
    const p = PL.prefs ? PL.prefs.damier() : { taille: T_DAMIER, c1: null, c2: null };
    const t = p.taille;
    const xa = Math.max(x, 0), ya = Math.max(y, 0);
    const xb = Math.min(x + w, taille.w), yb = Math.min(y + h, taille.h);
    if (!t) { if (xb > xa && yb > ya) { ctx.fillStyle = "#ffffff"; ctx.fillRect(xa, ya, xb - xa, yb - ya); } return; }
    const r = tuilesVisibles(v, d, taille, t);
    if (r.i1 < r.i0) return;
    ctx.fillStyle = p.c1 || jetons.c1; ctx.fillRect(xa, ya, xb - xa, yb - ya);
    ctx.fillStyle = p.c2 || jetons.c2;
    for (let j = r.j0; j <= r.j1; j++) for (let i = r.i0; i <= r.i1; i++) {
      if (!((i + j) % 2)) continue;
      const tx = Math.max(x + i * t, xa), ty = Math.max(y + j * t, ya);
      const tx2 = Math.min(x + (i + 1) * t, xb), ty2 = Math.min(y + (j + 1) * t, yb);
      ctx.fillRect(tx, ty, tx2 - tx, ty2 - ty);
    }
  }

  vue.dessiner = function dessiner() {
    const k = dpr();
    const taille = taillePx();
    const { w, h } = taille;
    if (toile.width !== Math.round(w * k) || toile.height !== Math.round(h * k)) {
      toile.width = Math.round(w * k); toile.height = Math.round(h * k);
    }
    ctx.setTransform(k, 0, 0, k, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const d = dims();
    if (!d) return;
    lireJetons();
    v.dw = d.w;                                 // t152 : largeur du document pour la vue en miroir (versEcran / versDoc)
    const x = v.ox, y = v.oy, W = d.w * v.z, H = d.h * v.z;
    const bord = PL.prefs ? PL.prefs.v("interface", "canvasBorder") : "line";
    if (bord === "dropShadow") {
      // t159 : Préférences › Interface › Bordure : ombre portée sous le document
      ctx.save(); ctx.shadowColor = "rgba(0,0,0,.6)"; ctx.shadowBlur = 12; ctx.shadowOffsetY = 3;
      ctx.fillStyle = jetons.c1; ctx.fillRect(x, y, W, H); ctx.restore();
    }
    damier(x, y, W, H, d, taille);
    if (vue.rendu && vue.rendu.image) {
      // t153 : vue d'une ou plusieurs couches (doc.render rend toujours le composite) — composée par mod-couches
      const image = vue.filtre ? vue.filtre(vue.rendu.image) : vue.rendu.image;
      // pixels francs au-delà de 100 %, lissé en réduction ; t152 : Aperçu pixel art = pixels francs à tout zoom
      ctx.imageSmoothingEnabled = v.z < 1 && !vue.pixelArt;
      if (v.miroir) {
        // t152 : Symétrie horizontale = la VUE retournée (le document du moteur ne change pas)
        ctx.save(); ctx.translate(x + W, y); ctx.scale(-1, 1);
        ctx.drawImage(image, 0, 0, W, H);
        ctx.restore();
      } else ctx.drawImage(image, x, y, W, H);
    }
    if (bord === "line") {
      ctx.strokeStyle = jetons.trait;
      ctx.lineWidth = 1;
      ctx.strokeRect(x - 0.5, y - 0.5, W + 1, H + 1);
    }
    if (PL.surVue) PL.surVue.forEach((f) => f(v));
  };
  PL.surVue = [];          // crochets appelés après chaque redessin (sélection animée, navigateur…)

  function statut() {
    const el = PL.$("#stZoom");
    if (!el) return;
    el.textContent = formaterZoom(v.z, lang());
    // Flou assumé au très fort zoom (rendu plafonné à 2048) : on le dit.
    const d = dims();
    const flou = d && tailleRendu(d, v.z, dpr()) === 2048 && Math.max(d.w, d.h) * v.z * dpr() > 2048;
    el.title = flou ? (window.dzT ? window.dzT("photolab.vue.flou") : "photolab.vue.flou") : "";
  }

  function appliquer(nouveau, redemanderRendu = true) {
    // t159 : Préférences › Outils › Défilement au-delà du document (coupé : le document ne quitte pas la vue)
    const d = dims();
    if (d && PL.prefs) nouveau = PL.prefs.bornerVue(nouveau, d, taillePx());
    v.z = nouveau.z; v.ox = nouveau.ox; v.oy = nouveau.oy;
    vue.dessiner(); statut();
    if (redemanderRendu) planifierRendu();
  }

  vue.centrer = function centrer(z) {
    const d = dims(); if (!d) return;
    const { w, h } = taillePx();
    appliquer({ z, ox: (w - d.w * z) / 2, oy: (h - d.h * z) / 2 });
  };
  vue.ajuster = () => { const d = dims(); if (d) vue.centrer(ajuster(d, taillePx())); };
  vue.cent = () => vue.centrer(1);
  vue.zoomPalier = (sens) => {
    const { w, h } = taillePx();
    appliquer(zoomAutour(v, palier(v.z, sens), w / 2, h / 2));
  };
  vue.zoomAutour = (z, px, py) => appliquer(zoomAutour(v, z, px, py));
  // Aller à une vue donnée (Navigateur, C2) : un rendu n'est redemandé que si le zoom change.
  vue.allerA = (n) => appliquer(n, n.z !== v.z);

  // Rendu : le dernier rendu est dessiné tel quel. poserRendu accepte aussi un faux rendu (banc, ou avant la phase C
  // qui branche les documents) : {image: CanvasImageSource, maxSide}.
  vue.poserRendu = function poserRendu(rendu) { vue.rendu = rendu; vue.dessiner(); };
  // Aperçu d'un dialogue de réglage (t138 B2) : l'image calculée par le moteur sur une COPIE du document prend la place
  // du rendu, sans rien changer à PL.etat.doc (l'original n'a pas bougé). maxSide = taille demandée, pour que le
  // rendu suivant (zoom) se compare juste ; à défaut, celle du rendu en place. Le prochain cycle reposera le rendu réel.
  vue.poserApercu = function poserApercu(image, maxSide) {
    const m = maxSide != null ? maxSide : (vue.rendu ? vue.rendu.maxSide : 0);
    vue.rendu = { image, maxSide: m, apercu: true };
    vue.dessiner();
  };
  let minuterie = null;
  function planifierRendu() {
    const d = dims();
    if (!d || !PL.rendre) return;
    clearTimeout(minuterie);
    minuterie = setTimeout(() => {
      const voulu = tailleRendu(d, v.z, dpr());
      if (changementSensible(vue.rendu ? vue.rendu.maxSide : null, voulu, 0.25, Math.max(d.w, d.h))) PL.rendre(voulu);
    }, 150);
  }
  vue.maxSideVoulu = () => { const d = dims(); return d ? tailleRendu(d, v.z, dpr()) : 960; };

  // Un nouveau document (ou un document recadré) : on recadre la vue dessus.
  vue.surNouveauDoc = () => { vue.rendu = null; vue.ajuster(); };

  new ResizeObserver(() => { vue.dessiner(); statut(); }).observe(scene);

  /* molette sur le canevas */
  toile.addEventListener("wheel", (ev) => {
    if (!dims()) return;
    ev.preventDefault();
    const g = gesteMolette(ev, !!(PL.prefs && PL.prefs.v("general", "zoomWithScrollWheel")));
    const p = vue.pointeur(ev);
    if (g.type === "zoom") appliquer(zoomAutour(v, v.z * g.facteur, p.x, p.y));
    else appliquer(panoramique(v, g.dx, g.dy), false);
  }, { passive: false });
  // M1 : Ctrl+molette (ou pincement) ne zoome JAMAIS la page du navigateur, où que soit le pointeur dans le lab.
  window.addEventListener("wheel", (ev) => { if (ctrlSurPage(ev)) ev.preventDefault(); }, { passive: false });

  /* main : bouton du milieu, outil Main, ou Espace tenu */
  let glisse = null;
  const enSaisie = (ev) => ev.target && (/^(INPUT|TEXTAREA|SELECT)$/.test(ev.target.tagName || "") || ev.target.isContentEditable);
  const mainActive = (ev) => ev.button === 1 || vue.mainActive();
  vue.mainActive = () => vue.mainTemporaire || PL.etat.outil === "hand";

  // I3 : fin du glisser, quelle qu'en soit la cause (relâchement, capture perdue, fenêtre quittée, bouton déjà relevé).
  function finGlisse(ev) {
    if (!glisse) return;
    glisse = null;
    if (ev && ev.pointerId != null) { try { toile.releasePointerCapture(ev.pointerId); } catch (e) { /* capture déjà perdue */ } }
    curseur();
  }

  toile.addEventListener("pointerdown", (ev) => {
    if (!dims()) return;
    if (ev.button === 1 || (ev.button === 0 && mainActive(ev))) {
      ev.preventDefault();
      glisse = { x: ev.clientX, y: ev.clientY, ox: v.ox, oy: v.oy };
      toile.setPointerCapture(ev.pointerId);
      toile.style.cursor = "grabbing";
    } else if (ev.button === 0 && PL.etat.outil === "zoom") {
      // Outil Zoom : clic = palier suivant, Alt+clic = précédent (le glisser-zoom viendra avec les outils de C3).
      const p = vue.pointeur(ev);
      const z = zoomAutour(v, palier(v.z, ev.altKey ? -1 : +1), p.x, p.y);
      // t159 : Préférences › Outils › Zoom : point cliqué au centre
      appliquer(PL.prefs ? PL.prefs.centrerSur(z, p.x, p.y, taillePx()) : z);
    }
  });
  toile.addEventListener("pointermove", (ev) => {
    if (!glisse) return;
    if (!(ev.buttons & 5)) { finGlisse(ev); return; }       // bouton gauche (1) ou milieu (4) déjà relevé hors de la page
    appliquer({ z: v.z, ox: glisse.ox + ev.clientX - glisse.x, oy: glisse.oy + ev.clientY - glisse.y }, false);
  });
  toile.addEventListener("pointerup", finGlisse);
  toile.addEventListener("pointercancel", finGlisse);
  toile.addEventListener("lostpointercapture", finGlisse);
  toile.addEventListener("auxclick", (ev) => { if (ev.button === 1) ev.preventDefault(); });

  /* clavier : Ctrl+0 / 1 / = / - (par e.code, AZERTY compris) ; Espace tenu = main temporaire */
  const fenetreOuverte = () => !!document.querySelector(".menu-panneau, .flyout");
  document.addEventListener("keydown", (ev) => {
    // Les touches de zoom passent AVANT le test de saisie : Ctrl+= / Ctrl+- ne doivent pas zoomer la page, même dans un
    // champ numérique de la barre d'options.
    if ((ev.ctrlKey || ev.metaKey) && !ev.altKey) {
      const a = toucheZoom(ev);
      if (a) {
        ev.preventDefault();
        if (!dims()) return;
        if (a === "ajuster") vue.ajuster(); else if (a === "cent") vue.cent(); else vue.zoomPalier(a === "plus" ? +1 : -1);
      }
      return;
    }
    if (enSaisie(ev) || fenetreOuverte()) return;
    if (ev.code === "Space" && !ev.altKey) {
      // I4 : Espace ne prend la main que si le focus n'est pas sur un contrôle (un bouton reste activable à Espace).
      if (ev.target && ev.target.closest && ev.target.closest("button, [role=menuitem], a, summary")) return;
      if (!vue.mainTemporaire) { vue.mainTemporaire = true; curseur(); }
      ev.preventDefault();
    }
  });
  const relacherMain = () => { if (vue.mainTemporaire) { vue.mainTemporaire = false; if (!glisse) curseur(); } };
  document.addEventListener("keyup", (ev) => { if (ev.code === "Space") relacherMain(); });
  window.addEventListener("blur", () => { relacherMain(); finGlisse(null); });

  statut();
}
