// dz-capture-logique.js — t315 (28/10/2026, lot D1 « capture façon streaming »), la LOGIQUE PURE de l'enregistreur de
// l'app (plan docs/superpowers/plans/2026-10-28-t315-capture.md, spec 2026-10-25-boite-a-outils-design.md §8.1-8.3).
// SOURCE : frontend/shared ; copie OCTET POUR OCTET : frontend/dist/shared (banc backend/tests/test_capture_ecran.py,
// qui joue ce module sous node). Aucun accès au DOM global : tout arrive en paramètre.
//
// Contrat pour t316-t319 (skins, montage, live, tutoriels) : SELECTEURS_SECRETS et CSS_MASQUE sont la SEULE définition
// du masquage ; la piste des clics suit le format du plan (§« Contrat pour t316-t319 »).

// ── masquage (spec §8.2) : tout élément marqué data-dz-secret, et tout champ mot de passe, même non marqué ──
export const SELECTEURS_SECRETS = '[data-dz-secret], input[type="password"]';
export const ATTR_CAPTURE = "data-dz-capture";            // posé sur <html> le temps d'une capture
// flou DOM : la piste brute « écran » ne voit jamais le secret ; un ÉCRAN secret (data-dz-secret="ecran") est en plus
// rendu inerte (on n'y travaille pas pendant qu'on filme) et grisé
export const CSS_MASQUE = [
  'html[data-dz-capture] [data-dz-secret], html[data-dz-capture] input[type="password"]{filter:blur(16px)!important}',
  'html[data-dz-capture] [data-dz-secret="ecran"]{filter:blur(22px) grayscale(1)!important;pointer-events:none!important;user-select:none!important}',
].join("\n");

// un élément (ou un de ses parents) est-il secret ? `el.closest` absent (nœud texte) : on remonte au parent
export function estSecret(el) {
  let x = el;
  while (x && typeof x.closest !== "function") x = x.parentNode || x.parentElement || null;
  if (!x) return false;
  try { return !!x.closest(SELECTEURS_SECRETS); } catch (e) { return false; }
}

// ── l'élément cliqué : {balise, role, t, i}, comme le relevé de « Demander » (dz-agent-logique.js) ──
// t = le libellé d'un CONTRÔLE (première ligne non vide, ≤ 40 caractères, sinon vide) ; un champ ne donne JAMAIS son
// texte ni sa valeur ; i = title, aria-label ou placeholder (≤ 80). Aucune touche, aucune valeur saisie.
export const MAX_LIBELLE = 40;
export const MAX_INFOBULLE = 80;
const CIBLES = 'button, a[href], [role="button"], [role="tab"], [role="menuitem"], [role="option"], [role="checkbox"], '
  + '[role="switch"], input, select, textarea, label, summary, [title], [aria-label]';
const ROLES_CONTROLE = new Set(["button", "tab", "menuitem", "option", "checkbox", "switch"]);
const balise = (x) => String((x && x.tagName) || "").toLowerCase();
const court = (s, n) => String(s || "").replace(/\s+/g, " ").trim().slice(0, n);

function estChamp(x) {
  const g = balise(x), ce = x.getAttribute ? x.getAttribute("contenteditable") : null;
  return g === "input" || g === "textarea" || g === "select" || x.isContentEditable === true
    || (ce != null && ce !== "false");
}
function estControle(x) {
  const g = balise(x), role = x.getAttribute ? x.getAttribute("role") : null;
  return g === "button" || g === "summary" || (g === "a" && x.getAttribute("href") != null) || ROLES_CONTROLE.has(role);
}

export function cibleClic(el) {
  let x = el;
  while (x && typeof x.closest !== "function") x = x.parentNode || null;
  if (!x) return { balise: "", role: "", t: "", i: "" };
  let c = null;
  try { c = x.closest(CIBLES); } catch (e) { c = null; }
  c = c || x;
  const attr = (k) => (c.getAttribute ? c.getAttribute(k) : null) || "";
  let t = "";
  if (!estChamp(c) && estControle(c)) {
    const brut = typeof c.innerText === "string" ? c.innerText : String(c.textContent || "");
    const ligne = brut.split("\n").map((l) => l.replace(/\s+/g, " ").trim()).find((l) => l) || "";
    t = ligne.length > MAX_LIBELLE ? "" : ligne;
  }
  const i = court(attr("title") || attr("aria-label") || attr("placeholder"), MAX_INFOBULLE);
  return { balise: balise(c), role: court(attr("role"), 20), t, i };
}

// ── géométrie : le cadre filmé (rectangle de la fenêtre, px CSS) ↔ la scène (px du canvas) ──
export const borne = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
// un point de la fenêtre -> 0..1 dans le cadre filmé
export function normaliser(x, y, cadre) {
  const l = cadre.l > 0 ? cadre.l : 1, h = cadre.h > 0 ? cadre.h : 1;
  return { x: Math.round(borne((x - cadre.x) / l, 0, 1) * 1e4) / 1e4, y: Math.round(borne((y - cadre.y) / h, 0, 1) * 1e4) / 1e4 };
}
// un rectangle de la fenêtre -> px de la scène (largeur × hauteur), rogné au cadre ; null s'il est hors cadre
export function versScene(r, cadre, largeur, hauteur) {
  const kx = largeur / (cadre.l || 1), ky = hauteur / (cadre.h || 1);
  const x0 = borne(r.x - cadre.x, 0, cadre.l), y0 = borne(r.y - cadre.y, 0, cadre.h);
  const x1 = borne(r.x + r.l - cadre.x, 0, cadre.l), y1 = borne(r.y + r.h - cadre.y, 0, cadre.h);
  if (x1 - x0 < 1 || y1 - y0 < 1) return null;
  return { x: x0 * kx, y: y0 * ky, l: (x1 - x0) * kx, h: (y1 - y0) * ky };
}
// l'encart caméra, normalisé 0..1 : taille entre min et max, tenu dans le cadre
export const ENCART_MIN = 0.08, ENCART_MAX = 0.6;
export function bornerEncart(e) {
  const l = borne(Number(e && e.l) || 0.22, ENCART_MIN, ENCART_MAX), h = borne(Number(e && e.h) || 0.22, ENCART_MIN, ENCART_MAX);
  return { x: borne(Number(e && e.x) || 0, 0, 1 - l), y: borne(Number(e && e.y) || 0, 0, 1 - h), l, h };
}
export const FORMES = ["cercle", "carre", "vif"];
export const formeLue = (v) => (FORMES.includes(v) ? v : "cercle");

// ── zoom en direct (désactivable) : 1 → K_ZOOM → 1 autour du clic, en DUREE_ZOOM ms ; vue = {k, ox, oy} ──
export const K_ZOOM = 1.5, DUREE_ZOOM = 1800;
// t316 : le STYLE du zoom vient du skin — zoom.k (1,1..2,5) et zoom.duree (800..4 000 ms), sinon les valeurs ci-dessus
export function vueZoom(zoom, t, largeur, hauteur) {
  const K = zoom && Number.isFinite(zoom.k) ? borne(zoom.k, 1.1, 2.5) : K_ZOOM;
  const D = zoom && Number.isFinite(zoom.duree) ? borne(zoom.duree, 800, 4000) : DUREE_ZOOM;
  if (!zoom || !(t >= zoom.debut) || t > zoom.debut + D) return { k: 1, ox: 0, oy: 0 };
  const p = (t - zoom.debut) / D;
  const montee = Math.min(1, p / 0.25), descente = Math.min(1, (1 - p) / 0.25);
  const e = Math.min(montee, descente), lisse = e * e * (3 - 2 * e);
  const k = 1 + (K - 1) * lisse;
  const ox = borne(zoom.cx - k * zoom.cx, largeur - k * largeur, 0), oy = borne(zoom.cy - k * zoom.cy, hauteur - k * hauteur, 0);
  return { k, ox, oy };
}

// t316 : le CADRE d'un skin — l'écran réduit d'une marge (0..0,12 de chaque côté) et centré, le fond du skin autour.
// rectCadre -> {x, y, l, h, k} en px de scène ; composerCadre(vue, cadre) = cadre ∘ zoom, la transformation que
// suivent l'écran, les clics ET le caviardage (contrat t315 : « étendre le caviardage d'abord »).
export const MARGE_MAX = 0.12;
export function rectCadre(cadre, largeur, hauteur) {
  const m = borne(Number(cadre && cadre.marge) || 0, 0, MARGE_MAX), k = 1 - 2 * m;
  return { x: m * largeur, y: m * hauteur, l: k * largeur, h: k * hauteur, k };
}
export function composerCadre(vue, cadre, largeur, hauteur) {
  const r = rectCadre(cadre, largeur, hauteur);
  return { k: vue.k * r.k, ox: vue.ox * r.k + r.x, oy: vue.oy * r.k + r.y };
}

// ── format d'enregistrement : MP4 (H.264) si le navigateur le donne, sinon WebM ; genre scene | video | audio ──
const CANDIDATS = {
  scene: ["video/mp4;codecs=avc1.42E01E,mp4a.40.2", "video/mp4", "video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"],
  video: ["video/mp4;codecs=avc1.42E01E", "video/mp4", "video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"],
  audio: ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4", "audio/webm"],
};
export function choisirMime(estSupporte, genre) {
  for (const m of CANDIDATS[genre] || []) {
    try { if (estSupporte(m)) return m; } catch (e) { /* navigateur sans isTypeSupported */ }
  }
  return "";
}

// ── la surface partagée : l'onglet de l'app, rien d'autre (spec §2 : jamais le bureau) ──
// settings = track.getSettings() ; poignee = track.getCaptureHandle() (ou null) ; jeton = celui que la page a posé ;
// lisible = la page a posé sa poignée ET le navigateur sait la relire : alors un onglet SANS poignée est un autre onglet
// (Gmail, un gestionnaire de mots de passe… n'en posent pas). « inconnu » : seul Element Capture peut encore prouver
// l'auto-capture, sinon l'enregistreur refuse (revue finale t315, C1).
export function verifierSurface(settings, poignee, jeton, lisible = false) {
  if (!settings || settings.displaySurface !== "browser") return "pas_onglet";
  if (poignee && typeof poignee.handle === "string") return poignee.handle === jeton ? "ok" : "autre_onglet";
  return lisible ? "autre_onglet" : "inconnu";
}

// ── la piste des clics (format du plan, version 1) : t = ms depuis le début ──
export function creerPiste(maintenant) {
  const evenements = [];
  let debut = 0, dernierEcran = "";
  return {
    debut() { debut = maintenant(); evenements.length = 0; dernierEcran = ""; return debut; },
    t() { return Math.max(0, Math.round(maintenant() - debut)); },
    clic(x) {
      const e = { type: "clic", t: this.t(), x: x.x, y: x.y, bouton: [0, 1, 2].includes(x.bouton) ? x.bouton : 0,
        ecran: String(x.ecran || "").slice(0, 40) };
      if (x.secret) { e.secret = true; e.cible = { balise: x.cible.balise, role: x.cible.role, t: "", i: "" }; }
      else e.cible = x.cible;
      evenements.push(e);
      return e;
    },
    ecran(v) {
      v = String(v || "").slice(0, 40);
      if (!v || v === dernierEcran) return null;
      dernierEcran = v;
      const e = { type: "ecran", t: this.t(), ecran: v };
      evenements.push(e);
      return e;
    },
    evenements: () => evenements.slice(),
    json: () => ({ version: 1, evenements: evenements.slice() }),
  };
}

export function duree(ms) {
  const s = Math.max(0, Math.floor(ms / 1000));
  return String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0");
}
