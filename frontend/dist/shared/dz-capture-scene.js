// dz-capture-scene.js — t315 (28/10/2026, lot D1), le COMPOSITEUR COMMUN de la capture : une scène canvas faite de
// calques, qui alimente l'enregistrement (t315) ET le live (t318), et que les skins (t316) habillent (spec boîte à
// outils §8.3, choix de Claude 8). SOURCE : frontend/shared ; copie OCTET POUR OCTET : frontend/dist/shared (banc
// backend/tests/test_capture_ecran.py, qui le joue sous node avec un faux canvas).
//
// Contrat (plan 2026-10-28-t315-capture.md, « Contrat pour t316-t319 ») :
//   const scene = creerScene({largeur, hauteur, fps, doc, horloge, maintenant});
//   scene.source("ecran" | "camera" | …, video | null)      une source vidéo (HTMLVideoElement prêt à lire)
//   scene.ajouterCalque({id, z, dessiner(ctx, s)})           s = {t, largeur, hauteur, sources, etat, vue}
//   scene.retirerCalque(id) ; scene.calques()                 triés par z croissant
//   scene.etat                                                 {encart, zoom, clics, secrets, textes, …} partagé
//   creerScene({…, secrets: () => [{x, y, l, h, ecran}]})    la MESURE des rectangles secrets (px de scène), donnée
//                                                              à la création, appelée à chaque image APRÈS les
//                                                              crochets : rien ne peut la remplacer ni la figer
//   scene.surImage(fn) -> retirer                              un crochet (skin, live) appelé avant chaque image
//   scene.dessiner(t) ; scene.demarrer() ; scene.arreter() ; scene.flux(fps) -> MediaStream (une fois)
// Le calque « caviardage » est posé par creerScene lui-même et ne se retire pas.
// Ordre des calques : fond / cadre < 100 ; écran 100 ; effets de clic 500 ; encart caméra 600 ; skin 700-800 ;
// CAVIARDAGE 900, toujours au-dessus : aucun autre calque ne peut prendre z ≥ 900 (le secret n'est jamais recouvert
// par un dessin qui le laisserait voir, ni découvert par un calque posé après).
// `vue` = {k, ox, oy} : le zoom en direct ; les calques écran, clics et caviardage l'appliquent, l'encart et le skin non.
// t316 : `etat.cadre` {marge} (posé par un skin) réduit l'écran ; `vue` = cadre ∘ zoom, `s.cadre` = le rectangle de
// l'écran (px de scène) : l'écran et les clics y sont rognés, le CAVIARDAGE suit la même `vue` et n'est jamais rogné.
import { vueZoom, composerCadre, rectCadre } from "./dz-capture-logique.js";

export const Z_ECRAN = 100, Z_CLICS = 500, Z_ENCART = 600, Z_CAVIARDAGE = 900;
export const DUREE_HALO = 650;

const horlogeParDefaut = {
  // pas requestAnimationFrame : il dort quand la fenêtre est masquée, la scène s'arrêterait
  demarrer: (f, ms) => setInterval(f, ms),
  arreter: (id) => clearInterval(id),
};

export function creerScene({ largeur, hauteur, fps = 30, doc, horloge = horlogeParDefaut, maintenant, secrets } = {}) {
  const d = doc || document;
  const ici = maintenant || (() => (typeof performance !== "undefined" ? performance.now() : Date.now()));
  const canvas = d.createElement("canvas");
  canvas.width = Math.max(2, Math.round(largeur || 1280));
  canvas.height = Math.max(2, Math.round(hauteur || 720));
  const ctx = canvas.getContext("2d");
  const sources = {};
  let calques = [];
  const crochets = [];
  const mesure = typeof secrets === "function" ? secrets : () => [];
  let minuterie = null, flux = null;
  const etat = { encart: null, forme: "cercle", zoom: null, clics: [], secrets: [], textes: {}, debut: 0, cadre: null };

  function trier() { calques.sort((a, b) => a.z - b.z || (a.ordre - b.ordre)); }
  let ordre = 0;
  const scene = {
    canvas, etat, sources,
    get largeur() { return canvas.width; },
    get hauteur() { return canvas.height; },
    source(nom, video) { if (video) sources[nom] = video; else delete sources[nom]; return scene; },
    ajouterCalque(c) {
      if (!c || typeof c.id !== "string" || typeof c.dessiner !== "function") throw new Error("calque invalide");
      const z = Number(c.z) || 0;
      if (z >= Z_CAVIARDAGE && c.id !== "caviardage") throw new Error("z réservé au caviardage");
      if (c.id === "caviardage" && calques.some((x) => x.id === "caviardage")) throw new Error("caviardage déjà posé");
      calques = calques.filter((x) => x.id !== c.id);
      calques.push({ id: c.id, z, dessiner: c.dessiner, ordre: ordre++ });
      trier();
      return scene;
    },
    retirerCalque(id) { if (id !== "caviardage") calques = calques.filter((x) => x.id !== id); return scene; },
    surImage(fn) {
      if (typeof fn !== "function") throw new Error("crochet invalide");
      crochets.push(fn);
      return () => { const i = crochets.indexOf(fn); if (i >= 0) crochets.splice(i, 1); };
    },
    calques: () => calques.map((c) => ({ id: c.id, z: c.z })),
    dessiner(t) {
      const tt = t == null ? ici() : t;
      const vue = composerCadre(vueZoom(etat.zoom, tt, canvas.width, canvas.height), etat.cadre, canvas.width, canvas.height);
      const cadre = rectCadre(etat.cadre, canvas.width, canvas.height);
      const s = { t: tt, largeur: canvas.width, hauteur: canvas.height, sources, etat, vue, cadre };
      for (const f of crochets.slice()) { try { f(s); } catch (e) { /* un crochet en panne est sauté */ } }
      // la mesure passe APRÈS les crochets : un skin ne peut ni la remplacer ni figer etat.secrets
      try { const m = mesure(s); etat.secrets = Array.isArray(m) ? m : null; }
      catch (e) { etat.secrets = null; }          // mesure en panne : le caviardage noircit toute l'image
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.fillStyle = "#000";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      for (const c of calques) {
        ctx.save();
        try { c.dessiner(ctx, s); }
        catch (e) {
          // un calque en panne est sauté ; une panne du CAVIARDAGE noircit toute l'image (jamais un secret à nu)
          if (c.id === "caviardage") { ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = "#000"; ctx.fillRect(0, 0, canvas.width, canvas.height); }
        }
        ctx.restore();
      }
      return s;
    },
    demarrer() {
      if (minuterie != null) return scene;
      etat.debut = ici();
      minuterie = horloge.demarrer(() => scene.dessiner(), Math.round(1000 / fps));
      return scene;
    },
    arreter() {
      if (minuterie != null) { horloge.arreter(minuterie); minuterie = null; }
      return scene;
    },
    actif: () => minuterie != null,
    flux(f) {
      if (!flux) flux = canvas.captureStream(f || fps);
      return flux;
    },
  };
  scene.ajouterCalque(calqueCaviardage());
  return scene;
}

// ── calques de départ ──

// t316 : l'écran et les clics restent dans le rectangle du cadre (rien ne déborde sur le fond du skin) ; le caviardage,
// lui, n'est jamais rogné
export function rogner(ctx, s) {
  const c = s.cadre;
  if (!c || (c.x <= 0 && c.y <= 0)) return;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.beginPath();
  ctx.rect(c.x, c.y, c.l, c.h);
  ctx.clip();
}

// la capture de l'app, plein cadre (la scène a les proportions de la piste écran), zoom en direct appliqué
export function calqueEcran() {
  return {
    id: "ecran", z: Z_ECRAN,
    dessiner(ctx, s) {
      const v = s.sources.ecran;
      if (!v || !(v.readyState >= 2)) return;
      rogner(ctx, s);
      ctx.setTransform(s.vue.k, 0, 0, s.vue.k, s.vue.ox, s.vue.oy);
      ctx.drawImage(v, 0, 0, s.largeur, s.hauteur);
    },
  };
}

// le halo de chaque clic récent (etat.clics : [{x, y, debut}] en px de scène), qui s'élargit et s'efface
export function calqueClics(couleur = "rgba(240,180,41,") {
  return {
    id: "clics", z: Z_CLICS,
    dessiner(ctx, s) {
      s.etat.clics = s.etat.clics.filter((c) => s.t - c.debut <= DUREE_HALO);
      rogner(ctx, s);
      ctx.setTransform(s.vue.k, 0, 0, s.vue.k, s.vue.ox, s.vue.oy);
      const base = Math.max(14, s.largeur / 70);
      for (const c of s.etat.clics) {
        const p = Math.max(0, Math.min(1, (s.t - c.debut) / DUREE_HALO));
        ctx.beginPath();
        ctx.arc(c.x, c.y, base * (0.6 + 1.4 * p), 0, Math.PI * 2);
        ctx.lineWidth = Math.max(3, base / 4);
        ctx.strokeStyle = couleur + (0.9 * (1 - p)).toFixed(3) + ")";
        ctx.stroke();
      }
    },
  };
}

// l'encart caméra : etat.encart {x, y, l, h} normalisé, etat.forme cercle | carre | vif ; rien sans source camera
export function calqueEncart(bord = "#f0b429") {
  return {
    id: "encart", z: Z_ENCART,
    dessiner(ctx, s) {
      const v = s.sources.camera, e = s.etat.encart;
      if (!v || !e || !(v.readyState >= 2)) return;
      const x = e.x * s.largeur, y = e.y * s.hauteur, l = e.l * s.largeur, h = e.h * s.hauteur;
      ctx.beginPath();
      if (s.etat.forme === "cercle") { const r = Math.min(l, h) / 2; ctx.arc(x + l / 2, y + h / 2, r, 0, Math.PI * 2); }
      else if (s.etat.forme === "carre" && typeof ctx.roundRect === "function") ctx.roundRect(x, y, l, h, Math.min(l, h) * 0.12);
      else ctx.rect(x, y, l, h);
      ctx.save();
      ctx.clip();
      // couvre l'encart en gardant les proportions de la caméra (recadrage au centre)
      const vw = v.videoWidth || l, vh = v.videoHeight || h, k = Math.max(l / vw, h / vh);
      ctx.drawImage(v, x + (l - vw * k) / 2, y + (h - vh * k) / 2, vw * k, vh * k);
      ctx.restore();
      ctx.lineWidth = Math.max(2, s.largeur / 400);
      ctx.strokeStyle = bord;
      ctx.stroke();
    },
  };
}

// le CAVIARDAGE : un cache opaque sur chaque rectangle secret (etat.secrets : [{x, y, l, h, ecran}] en px de scène),
// au-dessus de tout ; un écran entier porte le texte etat.textes.masque. Défense en profondeur : la page floute déjà
// ces éléments (CSS_MASQUE), la piste brute n'a que ce flou.
export function calqueCaviardage() {
  return {
    id: "caviardage", z: Z_CAVIARDAGE,
    dessiner(ctx, s) {
      if (!Array.isArray(s.etat.secrets)) throw new Error("secrets inconnus");     // -> image noire (creerScene)
      ctx.setTransform(s.vue.k, 0, 0, s.vue.k, s.vue.ox, s.vue.oy);
      for (const r of s.etat.secrets) {
        const m = Math.max(6, s.largeur / 200);          // le flou CSS déborde un peu de la boîte
        ctx.fillStyle = "#15181d";
        ctx.fillRect(r.x - m, r.y - m, r.l + 2 * m, r.h + 2 * m);
        ctx.strokeStyle = "rgba(240,180,41,.55)";
        ctx.lineWidth = 2;
        ctx.strokeRect(r.x - m, r.y - m, r.l + 2 * m, r.h + 2 * m);
        if (r.ecran && s.etat.textes.masque && r.l > 120 && r.h > 40) {
          ctx.fillStyle = "#cfd6e2";
          ctx.font = Math.round(Math.max(14, s.largeur / 90)) + "px system-ui, sans-serif";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(s.etat.textes.masque, r.x + r.l / 2, r.y + Math.min(r.h / 2, 80));
        }
      }
    },
  };
}
