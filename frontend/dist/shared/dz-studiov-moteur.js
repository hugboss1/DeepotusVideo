// dz-studiov-moteur.js — SV1 (14/11/2026, studio virtuel 3D), le MOTEUR D'AFFICHAGE du studio : il lit une recette
// (backend/app/services/studiov.py) et la construit en three.js — pièce, matières à motif, lumières, objets du
// catalogue (niveau « direct » : volumes simples), écrans du décor, enseigne, présentateur — puis la rend à chaque
// image vue par la caméra courante. Conception docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md.
// SOURCE : frontend/shared ; copie OCTET POUR OCTET : frontend/dist/shared. Banc : backend/tests/test_studiov_ecran.py.
//
//   const m = creerMoteur(THREE, {largeur, hauteur, decor, contexte, qualite: "legere" | "haute", logo, apercu});
//   m.canvas                       le canevas WebGL (dessiné par le calque « studiov » de la scène de capture)
//   m.maj(decor)                   reconstruit le décor (éditeur, changement de décor)
//   m.rendre(t, {ecran, camera})   une image : `ecran` = le canevas DÉJÀ CAVIARDÉ de la scène (jamais la source brute),
//                                  `camera` = la vidéo de la webcam (mode fond vert) ; t en ms
//   m.camera(i) ; m.cameras() ; m.courante() ; m.detruire()
// Les objets sont bâtis à l'ORIGINE de leur groupe : au sol (base à y = 0) ou, pour ce qui s'accroche au mur (cadre,
// panneau, néon, hublot, fenêtre, horloge, maillot, étoile, nuage, ballons), centrés sur leur point de pose.
import { palette, couleur, entier, regie, budgetLumieres, TYPES, borne } from "./dz-studiov-logique.js";

const K_SPOT = 26, K_NEON = 5, K_AMBIANCE = 1.0;         // intensités de la recette -> unités de three.js

// un tirage reproductible (les livres d'une bibliothèque ne changent pas d'une image à l'autre)
function alea(graine) { let s = graine >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

// ── motifs : une texture de 256 px dessinée une fois par matière ──
function motif(doc, nom, hex) {
  const c = doc.createElement("canvas"); c.width = c.height = 256;
  const x = c.getContext("2d"), r = alea(nom.length * 7919 + entier(hex));
  x.fillStyle = hex; x.fillRect(0, 0, 256, 256);
  const trait = (a) => { x.strokeStyle = `rgba(0,0,0,${a})`; }, clair = (a) => { x.fillStyle = `rgba(255,255,255,${a})`; };
  const sombre = (a) => { x.fillStyle = `rgba(0,0,0,${a})`; };
  if (nom === "bois" || nom === "parquet" || nom === "lattes") {
    const n = nom === "bois" ? 1 : nom === "parquet" ? 8 : 16, h = 256 / n;
    for (let i = 0; i < n; i++) {
      sombre(r() * 0.16); x.fillRect(0, i * h, 256, h);
      for (let k = 0; k < 14 / Math.sqrt(n); k++) { trait(0.05 + r() * 0.1); x.lineWidth = 1; x.beginPath(); const y = i * h + r() * h; x.moveTo(0, y); x.bezierCurveTo(80, y + r() * 4 - 2, 170, y + r() * 4 - 2, 256, y); x.stroke(); }
      if (n > 1) { sombre(nom === "lattes" ? 0.55 : 0.3); x.fillRect(0, i * h, 256, nom === "lattes" ? h * 0.3 : 1.5); if (nom === "parquet") x.fillRect(((i * 97) % 256), i * h, 1.5, h); }
    }
  } else if (nom === "brique") {
    const h = 32, l = 64;
    for (let j = 0; j < 8; j++) for (let i = -1; i < 5; i++) {
      const ox = i * l + (j % 2 ? l / 2 : 0); sombre(r() * 0.22); x.fillRect(ox, j * h, l, h); clair(r() * 0.06); x.fillRect(ox, j * h, l, h);
    }
    x.fillStyle = "rgba(225,215,200,.5)";
    for (let j = 0; j < 8; j++) { x.fillRect(0, j * h, 256, 3); for (let i = -1; i < 5; i++) x.fillRect(i * l + (j % 2 ? l / 2 : 0), j * h, 3, h); }
  } else if (nom === "beton" || nom === "tissu" || nom === "pelouse") {
    const n = nom === "beton" ? 900 : 2600;
    for (let i = 0; i < n; i++) {
      if (r() < 0.5) sombre(r() * (nom === "pelouse" ? 0.22 : 0.1)); else clair(r() * (nom === "pelouse" ? 0.14 : 0.07));
      const px = r() * 256, py = r() * 256;
      if (nom === "beton") x.fillRect(px, py, 2 + r() * 14, 2 + r() * 14); else if (nom === "pelouse") x.fillRect(px, py, 1.5, 3 + r() * 5); else x.fillRect(px, py, r() < 0.5 ? 6 : 1, r() < 0.5 ? 1 : 6);
    }
    if (nom === "pelouse") { clair(0.06); for (let i = 0; i < 4; i += 2) x.fillRect(0, i * 64, 256, 64); }
  } else if (nom === "grille" || nom === "carreaux") {
    const n = nom === "grille" ? 8 : 4, p = 256 / n;
    for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) {
      if (nom === "carreaux") { if ((i + j) % 2) { sombre(0.28); x.fillRect(i * p, j * p, p, p); } } else { sombre(r() * 0.12); x.fillRect(i * p, j * p, p, p); }
    }
    sombre(0.5); for (let i = 0; i <= n; i++) { x.fillRect(i * p - 1, 0, 2, 256); x.fillRect(0, i * p - 1, 256, 2); }
  } else if (nom === "metal") {
    for (let i = 0; i < 256; i++) { if (r() < 0.5) sombre(r() * 0.1); else clair(r() * 0.1); x.fillRect(0, i, 256, 1); }
    sombre(0.35); x.fillRect(0, 0, 256, 2); x.fillRect(0, 127, 256, 2);
  }
  return c;
}

export function creerMoteur(THREE, o) {
  const O = o || {}, doc = O.doc || document;
  const L = Math.max(2, Math.round(O.largeur || 1280)), H = Math.max(2, Math.round(O.hauteur || 720));
  const qualite = O.qualite === "haute" ? "haute" : "legere";
  const canvas = O.canvas || doc.createElement("canvas");
  const rendu = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: "high-performance" });
  rendu.setPixelRatio(1);
  rendu.setSize(L, H, false);
  rendu.outputColorSpace = THREE.SRGBColorSpace;
  rendu.toneMapping = THREE.ACESFilmicToneMapping;
  rendu.shadowMap.enabled = qualite === "haute";
  if (rendu.shadowMap.enabled) rendu.shadowMap.type = THREE.PCFSoftShadowMap;
  const scene = new THREE.Scene();
  const oeil = new THREE.PerspectiveCamera(40, L / H, 0.05, 60);
  let racine = null, decor = null, pal = palette(O.contexte), reg = regie(1);
  let texEcrans = [], canvasEcran = null, perso = null, texVideo = null, videoVue = null;
  const jetables = [];                                   // géométries, matières, textures du décor courant
  const garder = (x) => { jetables.push(x); return x; };

  // ── matières ──
  let cache = new Map();
  function texMotif(nom, hex, ru, rv) {
    const t = garder(new THREE.CanvasTexture(motif(doc, nom, hex)));
    t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(ru || 1, rv || 1);
    t.anisotropy = 4;
    return t;
  }
  // la matière d'une clé de la recette (ou une couleur seule), avec le motif répété ru × rv fois
  function matiere(cle, coul, ru, rv) {
    const m = (cle && decor.matieres[cle]) || null;
    const hex = couleur(coul || (m && m.couleur), pal, "#808890");
    const id = [cle || "", hex, ru || 1, rv || 1].join("|");
    if (cache.has(id)) return cache.get(id);
    const p = { color: 0xffffff, roughness: m ? m.rugosite : 0.7, metalness: m ? m.metal : 0 };
    if (m && m.motif !== "uni") p.map = texMotif(m.motif, hex, (ru || 1) / m.echelle, (rv || 1) / m.echelle);
    else p.color = entier(hex);
    if (m && m.emission > 0) { p.emissive = entier(hex); p.emissiveIntensity = m.emission; }
    const mat = garder(new THREE.MeshStandardMaterial(p));
    cache.set(id, mat);
    return mat;
  }
  const uni = (hex, rug, metal) => {
    const id = "u|" + hex + "|" + rug + "|" + metal;
    if (!cache.has(id)) cache.set(id, garder(new THREE.MeshStandardMaterial({ color: entier(hex), roughness: rug == null ? 0.6 : rug, metalness: metal || 0 })));
    return cache.get(id);
  };
  // une matière lumineuse (néon, abat-jour, écran) : jamais assombrie par le rendu des tons
  const lueur = (hex, force) => {
    const id = "e|" + hex + "|" + force;
    if (!cache.has(id)) {
      const c = new THREE.Color(entier(hex)).multiplyScalar(force == null ? 1.6 : force);
      cache.set(id, garder(new THREE.MeshBasicMaterial({ color: c, toneMapped: false })));
    }
    return cache.get(id);
  };

  // ── volumes de base (y = le BAS du volume) ──
  const ombres = (m) => { m.castShadow = m.receiveShadow = qualite === "haute"; return m; };
  function bx(g, mat, l, h, p, x, y, z, ry) {
    const m = ombres(new THREE.Mesh(garder(new THREE.BoxGeometry(l, h, p)), mat));
    m.position.set(x || 0, (y || 0) + h / 2, z || 0); if (ry) m.rotation.y = ry; g.add(m); return m;
  }
  function cy(g, mat, r, h, x, y, z, rHaut, seg) {
    const m = ombres(new THREE.Mesh(garder(new THREE.CylinderGeometry(rHaut == null ? r : rHaut, r, h, seg || 20)), mat));
    m.position.set(x || 0, (y || 0) + h / 2, z || 0); g.add(m); return m;
  }
  function sp(g, mat, r, x, y, z, sx, sy, sz) {
    const m = ombres(new THREE.Mesh(garder(new THREE.SphereGeometry(r, 20, 14)), mat));
    m.position.set(x || 0, y || 0, z || 0); if (sx) m.scale.set(sx, sy || 1, sz || 1); g.add(m); return m;
  }
  function tore(g, mat, r, e, x, y, z, arc) {
    const m = ombres(new THREE.Mesh(garder(new THREE.TorusGeometry(r, e, 10, 36, arc || Math.PI * 2)), mat));
    m.position.set(x || 0, y || 0, z || 0); g.add(m); return m;
  }
  function plan(g, mat, l, h, x, y, z) {
    const m = new THREE.Mesh(garder(new THREE.PlaneGeometry(l, h)), mat); m.position.set(x || 0, y || 0, z || 0); g.add(m); return m;
  }
  const pieds = (g, mat, dx, dz, h, e) => { for (const sx of [-1, 1]) for (const sz of [-1, 1]) bx(g, mat, e || 0.05, h, e || 0.05, sx * dx, 0, sz * dz); };

  // ── le catalogue : type -> constructeur(g, m) ; m.p = la matière propre de l'objet, m.c = sa couleur ──
  const NOIR = "#14161a", ACIER = "#8c949c", BLANC = "#eef0f2";
  const B = {
    bureau(g, m) { bx(g, m.p, 1.6, 0.04, 0.7, 0, 0.71); bx(g, m.p, 0.04, 0.71, 0.64, -0.76, 0); bx(g, m.p, 0.04, 0.71, 0.64, 0.76, 0); bx(g, uni(NOIR), 1.48, 0.3, 0.02, 0, 0.38, -0.3); },
    table(g, m) { bx(g, m.p, 1.2, 0.04, 0.7, 0, 0.71); pieds(g, uni(NOIR, 0.4, 0.5), 0.54, 0.29, 0.71); },
    table_ronde(g, m) { cy(g, m.p, 0.62, 0.04, 0, 0.7, 0, null, 40); cy(g, uni(NOIR, 0.4, 0.6), 0.05, 0.68, 0, 0.02); cy(g, uni(NOIR, 0.4, 0.6), 0.32, 0.02, 0, 0, 0, null, 32); },
    chaise(g, m) { bx(g, m.p, 0.44, 0.04, 0.44, 0, 0.44); bx(g, m.p, 0.44, 0.44, 0.04, 0, 0.5, -0.2); pieds(g, uni(NOIR), 0.19, 0.19, 0.44, 0.035); },
    fauteuil(g, m) { bx(g, m.p, 0.6, 0.14, 0.58, 0, 0.36); bx(g, m.p, 0.6, 0.62, 0.12, 0, 0.44, -0.26); bx(g, m.p, 0.08, 0.2, 0.5, -0.32, 0.46); bx(g, m.p, 0.08, 0.2, 0.5, 0.32, 0.46); cy(g, uni(NOIR, 0.4, 0.6), 0.04, 0.34, 0, 0.02); cy(g, uni(NOIR, 0.4, 0.6), 0.3, 0.03, 0, 0, 0, null, 5); },
    canape(g, m) { bx(g, m.p, 2.0, 0.3, 0.85, 0, 0.12); bx(g, m.p, 2.0, 0.5, 0.2, 0, 0.4, -0.33); bx(g, m.p, 0.2, 0.5, 0.85, -1.0, 0.12); bx(g, m.p, 0.2, 0.5, 0.85, 1.0, 0.12); for (const x of [-0.46, 0.46]) bx(g, m.p, 0.88, 0.12, 0.6, x, 0.42, 0.1); pieds(g, uni(NOIR), 0.95, 0.36, 0.12, 0.06); },
    etagere(g, m) { for (const x of [-0.5, 0.5]) bx(g, m.p, 0.03, 2.0, 0.3, x, 0); for (const y of [0.03, 0.43, 0.83, 1.23, 1.63, 1.97]) bx(g, m.p, 1.0, 0.04, 0.3, 0, y); bx(g, uni(NOIR, 0.9), 1.0, 2.0, 0.01, 0, 0, -0.15); },
    bibliotheque(g, m) {
      B.etagere(g, m); const r = alea(41), tons = ["#8b3a3a", "#2f5d8a", "#d9c7a0", "#3d6b4f", "#b5762e", "#4a4458", "#c9c9c9"];
      for (const y of [0.07, 0.47, 0.87, 1.27, 1.67]) { let x = -0.46; while (x < 0.4) { const e = 0.03 + r() * 0.04, h = 0.2 + r() * 0.12; bx(g, uni(tons[(r() * tons.length) | 0], 0.8), e, h, 0.2, x + e / 2, y, 0.02); x += e + 0.004; if (r() < 0.12) x += 0.1; } }
    },
    tapis(g, m) { bx(g, m.p, 2.0, 0.012, 1.4, 0, 0); },
    pupitre(g, m) { bx(g, m.p, 0.5, 0.98, 0.4, 0, 0); bx(g, m.p, 0.62, 0.03, 0.5, 0, 0.98); bx(g, lueur(pal.principale, 1.2), 0.5, 0.02, 0.01, 0, 0.6, 0.205); },
    vitrine(g, m) { B.etagere(g, m); bx(g, lueur("#ffe2b0", 1.4), 0.96, 0.015, 0.03, 0, 1.955, 0.12); bx(g, lueur("#ffe2b0", 1.0), 0.96, 0.012, 0.02, 0, 1.215, 0.13); bx(g, lueur("#ffe2b0", 1.0), 0.96, 0.012, 0.02, 0, 0.815, 0.13); },
    etabli(g, m) { bx(g, m.p, 3.2, 0.06, 0.7, 0, 0.84); pieds(g, uni(ACIER, 0.4, 0.8), 1.5, 0.29, 0.84, 0.06); bx(g, m.p, 3.1, 0.03, 0.6, 0, 0.3); },
    casier(g, m) { bx(g, m.p, 0.6, 1.9, 0.5, 0, 0); bx(g, uni(NOIR, 0.5, 0.5), 0.01, 1.8, 0.01, 0, 0.05, 0.255); for (const y of [1.6, 1.66, 1.72]) bx(g, uni(NOIR), 0.3, 0.015, 0.01, 0, y, 0.255); bx(g, uni(ACIER, 0.3, 0.9), 0.02, 0.1, 0.03, 0.2, 1.0, 0.26); },
    banc(g, m) { bx(g, m.p, 1.4, 0.06, 0.4, 0, 0.42); pieds(g, uni(NOIR, 0.4, 0.5), 0.6, 0.15, 0.42); },
    ecran_bureau(g) { cy(g, uni(NOIR, 0.4, 0.4), 0.11, 0.015, 0, 0, 0, null, 24); bx(g, uni(NOIR, 0.4, 0.4), 0.03, 0.14, 0.03, 0, 0.01); bx(g, uni(NOIR, 0.35, 0.3), 0.62, 0.37, 0.025, 0, 0.12); bx(g, lueur(pal.accent, 0.35), 0.59, 0.34, 0.004, 0, 0.135, 0.014); bx(g, lueur(pal.principale, 0.9), 0.3, 0.012, 0.004, -0.1, 0.38, 0.016); },
    micro_bras(g) {
      const n = uni(NOIR, 0.4, 0.6); cy(g, n, 0.03, 0.06, 0, 0); const a = bx(g, n, 0.02, 0.5, 0.02, -0.08, 0.04); a.rotation.z = 0.35; const b = bx(g, n, 0.02, 0.45, 0.02, -0.02, 0.44); b.rotation.z = -0.9;
      const c = cy(g, uni("#2a2d33", 0.3, 0.8), 0.028, 0.15, 0.2, 0.52, 0.05); c.rotation.x = 1.2; sp(g, uni("#3a3e46", 0.9), 0.036, 0.2, 0.6, 0.12);
    },
    micro_table(g) { cy(g, uni(NOIR, 0.4, 0.6), 0.06, 0.012, 0, 0); cy(g, uni(NOIR, 0.4, 0.6), 0.008, 0.16, 0, 0.012); cy(g, uni("#2a2d33", 0.3, 0.8), 0.026, 0.12, 0, 0.16); },
    casque(g) { const n = uni(NOIR, 0.5, 0.2); const t = tore(g, n, 0.085, 0.012, 0, 0.1, 0, Math.PI); t.rotation.z = 0; cy(g, n, 0.045, 0.035, -0.085, 0.03, 0).rotation.z = Math.PI / 2; cy(g, n, 0.045, 0.035, 0.085, 0.03, 0).rotation.z = Math.PI / 2; },
    softbox(g) { const n = uni(NOIR, 0.5, 0.3); cy(g, n, 0.012, 1.7, 0, 0); for (const a of [0, 2.1, 4.2]) { const p = bx(g, n, 0.012, 0.5, 0.012, Math.cos(a) * 0.14, 0, Math.sin(a) * 0.14); p.rotation.set(Math.sin(a) * 0.55, 0, -Math.cos(a) * 0.55); } bx(g, n, 0.62, 0.82, 0.16, 0, 1.4); bx(g, lueur("#fff6e6", 2.2), 0.56, 0.76, 0.01, 0, 1.43, 0.085); },
    projecteur(g) { const n = uni(NOIR, 0.4, 0.5); cy(g, n, 0.012, 0.25, 0, -0.25); const c = cy(g, n, 0.09, 0.22, 0, -0.42, 0.04, 0.07); c.rotation.x = 0.9; const l = cy(g, lueur("#fff4dc", 2.6), 0.07, 0.01, 0, -0.42, 0.14); l.rotation.x = 0.9; },
    camera_pied(g) { const n = uni(NOIR, 0.4, 0.4); for (const a of [0, 2.1, 4.2]) { const p = bx(g, n, 0.02, 1.35, 0.02, Math.cos(a) * 0.22, 0, Math.sin(a) * 0.22); p.rotation.set(Math.sin(a) * 0.32, 0, -Math.cos(a) * 0.32); } bx(g, n, 0.16, 0.12, 0.24, 0, 1.3); cy(g, uni("#22252b", 0.2, 0.8), 0.05, 0.12, 0, 1.3, 0.17).rotation.x = Math.PI / 2; bx(g, lueur("#e5484d", 1.5), 0.012, 0.012, 0.005, 0.06, 1.39, 0.122); },
    panneau_acoustique(g, m) { for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) bx(g, m.p, 0.31, 0.31, 0.05 + ((i + j + 2) % 2) * 0.02, i * 0.33, j * 0.33 - 0.155, 0.03); },
    lampe(g, m) { const n = uni(NOIR, 0.4, 0.6); cy(g, n, 0.07, 0.015, 0, 0); cy(g, n, 0.008, 0.32, 0, 0.015); cy(g, lueur(m.c || "#ffcf8a", 1.8), 0.09, 0.11, 0, 0.3, 0, 0.05); },
    lampadaire(g, m) { const n = uni(NOIR, 0.4, 0.6); cy(g, n, 0.16, 0.02, 0, 0, 0, null, 28); cy(g, n, 0.012, 1.55, 0, 0.02); cy(g, lueur(m.c || "#ffcf8a", 1.7), 0.17, 0.26, 0, 1.5, 0, 0.12, 28); },
    neon_barre(g, m) { const t = cy(g, lueur(m.c || pal.principale, 2.4), 0.018, 1.2, 0, -0.6, 0); t.rotation.z = Math.PI / 2; t.position.y = 0; },
    neon_anneau(g, m) { tore(g, lueur(m.c || pal.principale, 2.4), 0.36, 0.02, 0, 0, 0.03); },
    guirlande(g) { for (let i = 0; i <= 24; i++) { const u = i / 24 - 0.5; sp(g, lueur("#ffd9a0", 2.2), 0.022, u * 4.2, -Math.cos(u * Math.PI) * 0.22 * (1 + 0.3 * Math.cos(u * 12)), 0.04); } },
    plante(g) { cy(g, uni("#b9a48c", 0.9), 0.14, 0.28, 0, 0, 0, 0.17); const v = uni("#3c7a45", 0.8), v2 = uni("#2d6338", 0.8), r = alea(7); cy(g, uni("#4a3a28", 0.9), 0.012, 0.5, 0, 0.26); for (let i = 0; i < 9; i++) { const a = i * 0.7, h = 0.45 + r() * 0.45, d = 0.08 + r() * 0.16; const f = sp(g, i % 2 ? v : v2, 0.13, Math.cos(a) * d, h, Math.sin(a) * d, 0.55, 1.5, 0.3); f.rotation.set(Math.sin(a) * 0.5, a, -Math.cos(a) * 0.5); } },
    cadre(g, m) { bx(g, uni("#1b1d21", 0.5), 0.6, 0.8, 0.03, 0, -0.4, 0.015); bx(g, uni(BLANC, 0.9), 0.52, 0.72, 0.005, 0, -0.36, 0.032); bx(g, uni(m.c || pal.principale, 0.8), 0.3, 0.36, 0.004, 0.03, -0.2, 0.036); bx(g, uni(pal.accent, 0.8), 0.18, 0.18, 0.004, -0.1, 0.04, 0.038); },
    colonne(g, m) { cy(g, m.p, 0.2, 0.12, 0, 0, 0, null, 24); cy(g, m.p, 0.15, 3.0, 0, 0.12, 0, null, 24); cy(g, lueur(pal.principale, 1.8), 0.155, 0.03, 0, 1.6, 0, null, 24); },
    arche(g, m) { bx(g, m.p, 0.22, 2.4, 0.22, -1.25, 0); bx(g, m.p, 0.22, 2.4, 0.22, 1.25, 0); bx(g, m.p, 2.72, 0.22, 0.22, 0, 2.4); },
    caisse(g, m) { bx(g, m.p, 0.6, 0.6, 0.6, 0, 0); const n = uni(NOIR, 0.5, 0.5); for (const y of [0.0, 0.57]) for (const z of [-0.29, 0.29]) bx(g, n, 0.62, 0.03, 0.04, 0, y, z); },
    horloge(g) { const d = cy(g, uni(BLANC, 0.6), 0.2, 0.03, 0, 0, 0.015, null, 32); d.rotation.x = Math.PI / 2; d.position.y = 0; const c = tore(g, uni(NOIR, 0.4, 0.5), 0.2, 0.014, 0, 0, 0.03); c.rotation.set(0, 0, 0); bx(g, uni(NOIR), 0.012, 0.13, 0.006, 0, 0, 0.034); bx(g, uni(NOIR), 0.1, 0.012, 0.006, 0.05, -0.006, 0.034); },
    fenetre(g) { bx(g, uni(BLANC, 0.7), 1.7, 1.9, 0.06, 0, -0.95, 0); bx(g, lueur("#fff6e0", 3.0), 1.56, 1.76, 0.01, 0, -0.88, 0.03); bx(g, uni(BLANC, 0.7), 0.04, 1.76, 0.03, 0, -0.88, 0.035); bx(g, uni(BLANC, 0.7), 1.56, 0.04, 0.03, 0, -0.02, 0.035); },
    imprimante3d(g, m) { const n = uni(NOIR, 0.5, 0.4), c = m.c || "#f0b429"; bx(g, n, 0.4, 0.03, 0.4, 0, 0); for (const x of [-0.18, 0.18]) bx(g, n, 0.03, 0.45, 0.03, x, 0.03, -0.1); bx(g, n, 0.4, 0.03, 0.05, 0, 0.46, -0.1); bx(g, uni(ACIER, 0.3, 0.8), 0.38, 0.015, 0.02, 0, 0.26, -0.1); bx(g, uni(c, 0.5), 0.07, 0.07, 0.07, 0.03, 0.2, -0.07); bx(g, uni("#2b2f36", 0.3, 0.6), 0.26, 0.012, 0.26, 0, 0.05, 0.04); cy(g, uni(c, 0.6), 0.035, 0.09, 0.02, 0.062, 0.04, 0.02); bx(g, lueur(pal.accent, 1.2), 0.08, 0.04, 0.005, -0.12, 0.005, 0.2); },
    bobine(g, m) { const c = cy(g, uni(m.c || pal.principale, 0.5), 0.085, 0.06, 0, 0, 0, null, 28); c.rotation.x = Math.PI / 2; c.position.y = 0.1; for (const z of [-0.035, 0.035]) { const f = cy(g, uni(NOIR, 0.5), 0.1, 0.008, 0, 0, z, null, 28); f.rotation.x = Math.PI / 2; f.position.y = 0.1; } },
    figurine(g, m) { const c = uni(m.c || "#cfd3d8", 0.6); cy(g, uni(NOIR, 0.5), 0.05, 0.012, 0, 0); cy(g, c, 0.035, 0.1, 0, 0.012, 0, 0.028); sp(g, c, 0.033, 0, 0.145, 0); bx(g, c, 0.1, 0.02, 0.02, 0, 0.08); },
    boite_jeu(g, m) { bx(g, uni(m.c || pal.principale, 0.6), 0.3, 0.3, 0.075, 0, 0); bx(g, uni(BLANC, 0.6), 0.22, 0.07, 0.003, 0, 0.19, 0.038); bx(g, uni(NOIR, 0.6), 0.16, 0.09, 0.003, 0, 0.06, 0.038); },
    plateau_jeu(g) { for (let i = 0; i < 6; i++) for (let j = 0; j < 6; j++) bx(g, uni((i + j) % 2 ? "#e9dcc0" : pal.principale, 0.7), 0.1, 0.012, 0.1, (i - 2.5) * 0.1, 0, (j - 2.5) * 0.1); bx(g, uni("#3a2a1e", 0.6), 0.66, 0.008, 0.66, 0, 0); },
    pion(g, m) { const c = uni(m.c || "#e5484d", 0.4); cy(g, c, 0.018, 0.045, 0, 0, 0, 0.006); sp(g, c, 0.014, 0, 0.052, 0); },
    de(g) { bx(g, uni(BLANC, 0.4), 0.035, 0.035, 0.035, 0, 0); sp(g, uni(NOIR), 0.004, 0, 0.036, 0); },
    console_scifi(g, m) { bx(g, m.p, 1.9, 0.78, 0.5, 0, 0); const t = bx(g, m.p, 1.9, 0.05, 0.62, 0, 0.8, 0.04); t.rotation.x = -0.22; for (const x of [-0.6, 0, 0.6]) { const e = bx(g, lueur("#18e0ff", 1.2), 0.46, 0.006, 0.3, x, 0.845, 0.06); e.rotation.x = -0.22; } bx(g, lueur("#18e0ff", 2.0), 1.9, 0.02, 0.01, 0, 0.3, 0.255); bx(g, lueur("#ff7a18", 2.0), 1.9, 0.012, 0.01, 0, 0.1, 0.255); },
    hublot(g) { tore(g, uni("#39434f", 0.3, 0.9), 0.46, 0.05, 0, 0, 0.03); const d = cy(g, uni("#02040a", 0.1), 0.44, 0.01, 0, 0, 0.012, null, 40); d.rotation.x = Math.PI / 2; d.position.y = 0; const r = alea(99); for (let i = 0; i < 26; i++) { const a = r() * 6.28, q = Math.sqrt(r()) * 0.4; sp(g, lueur("#dff3ff", 2.5), 0.004 + r() * 0.006, Math.cos(a) * q, Math.sin(a) * q, 0.02); } sp(g, uni("#3b6ea8", 0.8), 0.13, 0.16, -0.1, -0.05); },
    tube_lumineux(g, m) { cy(g, uni(NOIR, 0.4, 0.6), 0.09, 0.06, 0, 0); cy(g, lueur(m.c || pal.principale, 2.4), 0.035, 2.3, 0, 0.06, 0, null, 14); cy(g, uni(NOIR, 0.4, 0.6), 0.06, 0.04, 0, 2.36); },
    hologramme(g, m) { const c = m.c || "#18e0ff"; cy(g, uni("#2b3542", 0.3, 0.8), 0.32, 0.1, 0, 0, 0, 0.28, 28); cy(g, lueur(c, 2.2), 0.24, 0.012, 0, 0.1, 0, null, 28); const f = garder(new THREE.MeshBasicMaterial({ color: entier(c), wireframe: true, transparent: true, opacity: 0.55, toneMapped: false })); const s = new THREE.Mesh(garder(new THREE.IcosahedronGeometry(0.3, 1)), f); s.position.y = 1.05; s.userData.tourne = 0.4; g.add(s); const k = garder(new THREE.MeshBasicMaterial({ color: entier(c), transparent: true, opacity: 0.1, side: THREE.DoubleSide, depthWrite: false, toneMapped: false })); const cone = new THREE.Mesh(garder(new THREE.CylinderGeometry(0.42, 0.2, 1.3, 24, 1, true)), k); cone.position.y = 0.76; g.add(cone); },
    nuage(g) { const b = uni("#ffffff", 1.0); sp(g, b, 0.28, 0, 0, 0, 1, 0.8, 0.5); sp(g, b, 0.22, -0.3, -0.04, 0, 1, 0.8, 0.5); sp(g, b, 0.2, 0.3, -0.05, 0, 1, 0.8, 0.5); sp(g, b, 0.16, 0.12, 0.14, 0, 1, 0.8, 0.5); },
    arbre_cartoon(g, m) { cy(g, uni("#8a5a3a", 0.9), 0.13, 1.1, 0, 0, 0, 0.09); const v = uni(m.c || "#43c463", 0.9); sp(g, v, 0.62, 0, 1.55, 0); sp(g, v, 0.42, -0.42, 1.3, 0.05); sp(g, v, 0.4, 0.44, 1.35, -0.05); },
    champignon(g, m) { cy(g, uni("#fff3dc", 0.9), 0.09, 0.3, 0, 0, 0, 0.07); const c = sp(g, uni(m.c || "#ff5a5f", 0.8), 0.26, 0, 0.3, 0, 1, 0.62, 1); c.geometry = garder(new THREE.SphereGeometry(0.26, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2)); for (const [x, y, z] of [[0.1, 0.42, 0.14], [-0.14, 0.4, 0.08], [0, 0.455, -0.05], [0.16, 0.39, -0.1]]) sp(g, uni("#ffffff", 0.9), 0.035, x, y, z, 1, 0.5, 1); },
    etoile(g, m) { const f = new THREE.Shape(); for (let i = 0; i < 10; i++) { const a = (i * Math.PI) / 5 + Math.PI / 2, r = i % 2 ? 0.1 : 0.24; if (i) f.lineTo(Math.cos(a) * r, Math.sin(a) * r); else f.moveTo(Math.cos(a) * r, Math.sin(a) * r); } const e = new THREE.Mesh(garder(new THREE.ExtrudeGeometry(f, { depth: 0.04, bevelEnabled: false })), lueur(m.c || "#ffd23f", 1.3)); g.add(e); },
    but_foot(g, m) { const b = m.p; cy(g, b, 0.04, 2.0, -1.5, 0, 0, null, 12); cy(g, b, 0.04, 2.0, 1.5, 0, 0, null, 12); const t = cy(g, b, 0.04, 3.08, 0, 0, 0, null, 12); t.rotation.z = Math.PI / 2; t.position.set(0, 2.0, 0); const f = garder(new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true, transparent: true, opacity: 0.35 })); const filet = new THREE.Mesh(garder(new THREE.BoxGeometry(3.0, 2.0, 0.8, 14, 10, 4)), f); filet.position.set(0, 1.0, -0.42); g.add(filet); },
    ballon_foot(g) { sp(g, uni("#f4f4f4", 0.5), 0.11, 0, 0, 0); for (const [x, y, z] of [[0, 0.11, 0], [0.09, 0.03, 0.05], [-0.08, 0.02, 0.07], [0.02, -0.03, 0.105], [-0.03, 0.06, -0.09]]) sp(g, uni(NOIR, 0.5), 0.034, x * 0.93, y * 0.93, z * 0.93, 1, 1, 1); },
    gradin(g, m) { const r = alea(5), tons = [pal.principale, pal.accent, "#e9edf2", "#1c2c4a"]; for (let i = 0; i < 4; i++) { bx(g, m.p, 8.4, 0.32 * (i + 1), 0.45, 0, 0, 0.68 - i * 0.45); for (let k = 0; k < 28; k++) bx(g, uni(tons[(r() * tons.length) | 0], 0.7), 0.22, 0.26, 0.06, (k - 13.5) * 0.29, 0.32 * (i + 1), 0.52 - i * 0.45); } },
    panier_basket(g) { const n = uni(NOIR, 0.4, 0.5); cy(g, n, 0.05, 2.6, 0, 0, -0.5); bx(g, n, 0.05, 0.05, 0.5, 0, 2.5, -0.25); bx(g, uni(BLANC, 0.3), 0.95, 0.62, 0.03, 0, 2.2, 0); bx(g, uni("#e5484d", 0.5), 0.3, 0.22, 0.004, 0, 2.3, 0.018); const t = tore(g, uni("#f26a1b", 0.4, 0.3), 0.2, 0.012, 0, 2.3, 0.23); t.rotation.x = Math.PI / 2; const f = garder(new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true, transparent: true, opacity: 0.5 })); const filet = new THREE.Mesh(garder(new THREE.CylinderGeometry(0.2, 0.12, 0.3, 12, 4, true)), f); filet.position.set(0, 2.15, 0.23); g.add(filet); },
    ballon_basket(g) { sp(g, uni("#e2701e", 0.7), 0.12, 0, 0, 0); tore(g, uni(NOIR), 0.121, 0.004, 0, 0, 0); tore(g, uni(NOIR), 0.121, 0.004, 0, 0, 0).rotation.y = Math.PI / 2; },
    ballon_ovale(g) { sp(g, uni("#7a4320", 0.7), 0.09, 0, 0.09, 0, 1.65, 1, 1); bx(g, uni(BLANC), 0.1, 0.006, 0.012, 0, 0.176, 0); },
    batte(g) { const b = cy(g, uni("#c9a36a", 0.5), 0.016, 0.86, 0, 0, 0, 0.032, 12); b.rotation.z = -0.18; b.position.x = 0.08; },
    trophee(g, m) { const o = uni(m.c || "#f0c040", 0.25, 1.0); bx(g, uni(NOIR, 0.4), 0.14, 0.05, 0.14, 0, 0); cy(g, o, 0.02, 0.1, 0, 0.05); cy(g, o, 0.035, 0.14, 0, 0.15, 0, 0.085); tore(g, o, 0.05, 0.008, -0.1, 0.23, 0); tore(g, o, 0.05, 0.008, 0.1, 0.23, 0); },
    tableau_tactique(g) { const n = uni(NOIR, 0.4, 0.4); for (const x of [-0.4, 0.4]) bx(g, n, 0.03, 1.7, 0.03, x, 0, -0.1).rotation.x = -0.12; bx(g, uni("#2f8a3a", 0.8), 1.0, 0.68, 0.02, 0, 0.9, 0); const b = uni(BLANC, 0.7); bx(g, b, 0.92, 0.006, 0.004, 0, 0.94, 0.012); bx(g, b, 0.92, 0.006, 0.004, 0, 1.53, 0.012); bx(g, b, 0.006, 0.6, 0.004, 0, 0.94, 0.012); bx(g, b, 0.006, 0.6, 0.004, -0.46, 0.94, 0.012); bx(g, b, 0.006, 0.6, 0.004, 0.46, 0.94, 0.012); tore(g, b, 0.09, 0.004, 0, 1.24, 0.012); for (const [x, y, c] of [[-0.25, 1.1, "#e5484d"], [-0.15, 1.38, "#e5484d"], [0.2, 1.2, "#f0b429"], [0.3, 1.42, "#f0b429"]]) sp(g, uni(c, 0.5), 0.022, x, y, 0.014, 1, 1, 0.3); },
    fanion(g, m) { cy(g, uni(BLANC, 0.5), 0.015, 2.2, 0, 0); const d = bx(g, uni(m.c || pal.principale, 0.8), 0.6, 0.4, 0.008, 0.31, 1.78, 0); d.material.side = THREE.DoubleSide; },
    maillot(g, m) { const c = uni(m.c || pal.principale, 0.9); bx(g, c, 0.46, 0.6, 0.03, 0, -0.3, 0.015); for (const s of [-1, 1]) { const a = bx(g, c, 0.2, 0.26, 0.03, s * 0.3, 0.02, 0.015); a.rotation.z = s * 0.5; } bx(g, uni(BLANC, 0.9), 0.14, 0.2, 0.004, 0, -0.14, 0.032); bx(g, uni(BLANC, 0.9), 0.2, 0.03, 0.004, 0, 0.27, 0.032); },
  };

  // ── images dessinées : écran en attente, enseigne, silhouette, ombre ──
  function toile(l, h, dessin) { const c = doc.createElement("canvas"); c.width = l; c.height = h; dessin(c.getContext("2d"), l, h); return c; }
  const texture = (c) => { const t = garder(new THREE.CanvasTexture(c)); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t; };
  function attente(source) {
    return toile(640, 360, (x, l, h) => {
      const g = x.createLinearGradient(0, 0, l, h); g.addColorStop(0, source === "eteint" ? "#050608" : "#0e1320"); g.addColorStop(1, source === "eteint" ? "#0b0d11" : pal.principale);
      x.fillStyle = g; x.fillRect(0, 0, l, h);
      if (source === "eteint") return;
      x.fillStyle = "rgba(255,255,255,.14)"; for (let i = 0; i < 5; i++) x.fillRect(40, 60 + i * 44, 300 - i * 34, 18);
      x.fillStyle = pal.accent; x.fillRect(40, 300, 180, 10);
      x.fillStyle = "rgba(255,255,255,.2)"; x.fillRect(400, 60, 200, 200);
    });
  }
  function toileEnseigne(e) {
    const large = e.source === "texte" && e.texte, c = couleur(e.couleur, pal);
    return toile(large ? 1024 : 512, large ? 256 : 512, (x, l, h) => {
      x.clearRect(0, 0, l, h);
      if (e.style !== "neon") { x.fillStyle = e.style === "ecran" ? "#05070b" : "#f4f1ea"; x.fillRect(0, 0, l, h); x.strokeStyle = c; x.lineWidth = l / 40; x.strokeRect(l / 80, l / 80, l - l / 40, h - l / 40); }
      const marge = h * 0.14;
      if (large) {
        x.font = `700 ${Math.round(h * 0.5)}px system-ui, sans-serif`; x.textAlign = "center"; x.textBaseline = "middle";
        if (e.style === "neon") { x.shadowColor = c; x.shadowBlur = h * 0.18; }
        x.fillStyle = e.style === "panneau" ? c : (e.style === "neon" ? "#ffffff" : c);
        x.fillText(e.texte, l / 2, h / 2, l - 2 * marge);
      } else if (O.logo && (O.logo.naturalWidth || O.logo.width)) {
        const w = O.logo.naturalWidth || O.logo.width, hh = O.logo.naturalHeight || O.logo.height, k = Math.min((l - 2 * marge) / w, (h - 2 * marge) / hh);
        if (e.style === "neon") { x.shadowColor = c; x.shadowBlur = h * 0.08; }
        x.drawImage(O.logo, (l - w * k) / 2, (h - hh * k) / 2, w * k, hh * k);
      } else {                                     // ni texte ni logo : un anneau à la couleur de l'espace
        x.strokeStyle = e.style === "neon" ? "#ffffff" : c; x.lineWidth = h * 0.06;
        if (e.style === "neon") { x.shadowColor = c; x.shadowBlur = h * 0.12; }
        x.beginPath(); x.arc(l / 2, h / 2, h * 0.28, 0, Math.PI * 2); x.stroke();
      }
    });
  }
  const silhouette = () => toile(360, 480, (x, l, h) => {
    x.clearRect(0, 0, l, h); const g = x.createLinearGradient(0, 0, 0, h); g.addColorStop(0, "#c9ced6"); g.addColorStop(1, "#7d858f"); x.fillStyle = g;
    x.beginPath(); x.arc(l / 2, h * 0.22, h * 0.14, 0, Math.PI * 2); x.fill();
    x.beginPath(); x.moveTo(l * 0.14, h); x.lineTo(l * 0.08, h * 0.62); x.bezierCurveTo(l * 0.08, h * 0.46, l * 0.3, h * 0.4, l / 2, h * 0.4); x.bezierCurveTo(l * 0.7, h * 0.4, l * 0.92, h * 0.46, l * 0.92, h * 0.62); x.lineTo(l * 0.86, h); x.fill();
  });
  const ombreSol = () => toile(128, 128, (x) => { const g = x.createRadialGradient(64, 64, 4, 64, 64, 62); g.addColorStop(0, "rgba(0,0,0,.55)"); g.addColorStop(1, "rgba(0,0,0,0)"); x.fillStyle = g; x.fillRect(0, 0, 128, 128); });

  // le présentateur : un plan face à la caméra ; `cle` = 1 : incrustation du fond vert, 0 : l'alpha de l'image
  function matierePresentateur(tex, cle, teinte, coulTeinte) {
    return garder(new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, toneMapped: false,
      uniforms: { carte: { value: tex }, cle: { value: cle ? 1 : 0 }, teinte: { value: teinte }, lum: { value: new THREE.Color(entier(coulTeinte)) } },
      vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
      fragmentShader: [
        "uniform sampler2D carte; uniform float cle; uniform float teinte; uniform vec3 lum; varying vec2 vUv;",
        "void main(){ vec4 c = texture2D(carte, vUv); float a = c.a;",
        "  if (cle > 0.5) { float v = c.g - max(c.r, c.b); a = 1.0 - smoothstep(0.06, 0.22, v); c.g = min(c.g, max(c.r, c.b) + 0.04); }",
        "  if (a < 0.01) discard;",
        "  vec3 k = mix(c.rgb, c.rgb * (0.55 + lum), teinte * 0.5);",
        "  gl_FragColor = vec4(k, a); }"].join("\n"),
    }));
  }

  // ── construction ──
  function vider() {
    if (racine) scene.remove(racine);
    for (const x of jetables.splice(0)) { try { x.dispose(); } catch (e) { /* déjà libéré */ } }
    cache = new Map(); texEcrans = []; perso = null; texVideo = null; videoVue = null; racine = null;
  }
  function construire(d) {
    vider();
    decor = d; pal = palette(O.contexte); reg = regie(d.cameras.length);
    racine = new THREE.Group();
    const P = d.piece, A = d.ambiance;
    scene.background = new THREE.Color(entier(couleur(A.fond, pal, "#0b0f14")));
    scene.fog = A.brouillard > 0 ? new THREE.FogExp2(scene.background.getHex(), A.brouillard) : null;
    rendu.toneMappingExposure = A.exposition;
    // la pièce : sol prolongé vers la caméra, mur du fond, murs de côté et plafond (sauf pièce ouverte)
    const av = 5;                                   // mètres de sol et de murs devant la pièce (côté caméra)
    const sol = plan(racine, matiere(P.sol, null, P.l + 4, P.p + av), P.l + 4, P.p + av, 0, 0, av / 2);
    sol.rotation.x = -Math.PI / 2; sol.receiveShadow = qualite === "haute";
    plan(racine, matiere(P.mur, null, P.l + 4, P.h), P.l + 4, P.h, 0, P.h / 2, -P.p / 2);
    if (!P.ouvert) {
      const g = plan(racine, matiere(P.mur, null, P.p + av, P.h), P.p + av, P.h, -P.l / 2, P.h / 2, av / 2); g.rotation.y = Math.PI / 2;
      const dr = plan(racine, matiere(P.mur, null, P.p + av, P.h), P.p + av, P.h, P.l / 2, P.h / 2, av / 2); dr.rotation.y = -Math.PI / 2;
      const pf = plan(racine, matiere(P.plafond, null, P.l, P.p + av), P.l, P.p + av, 0, P.h, av / 2); pf.rotation.x = Math.PI / 2;
    }
    if (P.plinthe && !P.ouvert) bx(racine, uni("#0e0f12", 0.6), P.l, 0.08, 0.02, 0, 0, -P.p / 2 + 0.01);
    // les objets
    for (const ob of d.objets) {
      const f = B[ob.type]; if (!f) continue;
      const g = new THREE.Group(), c = ob.couleur ? couleur(ob.couleur, pal) : null;
      f(g, { p: ob.matiere ? matiere(ob.matiere, c) : uni(c || "#3a3f47", 0.6), c });
      g.position.set(ob.x, ob.y, ob.z); g.rotation.y = (ob.ry * Math.PI) / 180; g.scale.setScalar(ob.e);
      racine.add(g);
    }
    // les lumières
    const allumees = budgetLumieres(d.lumieres, qualite);
    racine.add(new THREE.AmbientLight(0xffffff, 0.12));
    let ombrePosee = false;
    d.lumieres.forEach((l, i) => {
      const c = entier(couleur(l.couleur, pal, "#ffffff"));
      if (l.type === "ambiance") { racine.add(new THREE.HemisphereLight(c, entier(couleur(decor.matieres[P.sol].couleur, pal, "#333333")), l.intensite * K_AMBIANCE)); return; }
      if (l.type === "neon") {
        const g = new THREE.Group(), t = cy(g, lueur(couleur(l.couleur, pal, "#ffffff"), 2.6), 0.022, l.l, 0, -l.l / 2, 0, null, 10);
        t.rotation.x = Math.PI / 2; t.position.y = 0; t.castShadow = false;
        g.position.set(l.x, l.y, l.z); g.rotation.y = (l.ry * Math.PI) / 180; racine.add(g);
        if (allumees.has(i)) { const p = new THREE.PointLight(c, l.intensite * K_NEON, 7, 2); p.position.set(l.x, l.y, l.z); const vers = new THREE.Vector3(-l.x, 1.2 - l.y, -l.z).normalize().multiplyScalar(0.25); p.position.add(vers); racine.add(p); }
        return;
      }
      if (!allumees.has(i)) return;
      const s = new THREE.SpotLight(c, l.intensite * K_SPOT, 0, l.type === "fenetre" ? 1.05 : 0.85, 0.85, 2);
      s.position.set(l.x, l.y, l.z); s.target.position.set(l.vers[0], l.vers[1], l.vers[2]);
      if (qualite === "haute" && !ombrePosee && (l.type === "cle" || l.type === "fenetre")) { s.castShadow = true; s.shadow.mapSize.set(1024, 1024); s.shadow.bias = -0.0005; ombrePosee = true; }
      racine.add(s); racine.add(s.target);
    });
    // les écrans du décor
    d.ecrans.forEach((e) => {
      const g = new THREE.Group();
      bx(g, uni(couleur(e.bord, pal, "#0c0d10"), 0.4, 0.3), e.l + 0.08, e.h + 0.08, 0.05, 0, -(e.h + 0.08) / 2, 0.025);
      const tex = texture(attente(e.source)), mat = garder(new THREE.MeshBasicMaterial({ map: tex, toneMapped: false }));
      plan(g, mat, e.l, e.h, 0, 0, 0.052);
      if (e.source === "ecran") texEcrans.push({ mat, attente: tex, vive: null });
      g.position.set(e.x, e.y, e.z); g.rotation.y = (e.ry * Math.PI) / 180; racine.add(g);
    });
    // l'enseigne
    const E = d.enseigne;
    if (E.actif) {
      const g = new THREE.Group(), large = E.source === "texte" && E.texte, h = large ? E.l / 4 : E.l;
      const mat = garder(new THREE.MeshBasicMaterial({ map: texture(toileEnseigne(E)), transparent: E.style === "neon", toneMapped: false, depthWrite: E.style !== "neon" }));
      if (E.style !== "neon") bx(g, uni("#101216", 0.5), E.l + 0.04, h + 0.04, 0.03, 0, -(h + 0.04) / 2, 0.015);
      plan(g, mat, E.l, h, 0, 0, E.style === "neon" ? 0.03 : 0.032);
      g.position.set(E.x, E.y, E.z); g.rotation.y = (E.ry * Math.PI) / 180; racine.add(g);
      if (E.style === "neon") { const p = new THREE.PointLight(entier(couleur(E.couleur, pal)), 1.6, 4, 2); p.position.set(E.x, E.y, E.z + 0.3); racine.add(p); }
    }
    // le présentateur : silhouette en aperçu ; vidéo incrustée en mode fond vert (posée par `rendre`)
    // le plan du présentateur : un buste (0,95 m) pour qui est assis, la personne jusqu'au sol pour qui est debout
    const R = d.presentateur, hp = R.assis ? 0.95 : R.h + 0.08, lp = R.assis ? hp * 0.75 : hp * 0.42;
    perso = new THREE.Group(); perso.position.set(R.x, 0, R.z); perso.visible = false; racine.add(perso);
    perso.userData = { h: R.h, hp, lp };
    const contre = d.lumieres.find((l) => l.type === "contre");
    perso.userData.teinte = contre ? couleur(contre.couleur, pal, "#ffffff") : "#ffffff";
    const corps = plan(perso, matierePresentateur(texture(silhouette()), false, R.teinte, perso.userData.teinte), lp, hp, 0, R.h + 0.08 - hp / 2, 0);
    corps.name = "corps"; corps.renderOrder = 5;
    if (R.ombre) { const so = plan(perso, garder(new THREE.MeshBasicMaterial({ map: texture(ombreSol()), transparent: true, depthWrite: false })), 1.1, 0.7, 0, 0.012, 0); so.rotation.x = -Math.PI / 2; }
    perso.visible = !!O.apercu;
    scene.add(racine);
  }

  function poserVideo(video) {
    if (!perso || video === videoVue) return;
    videoVue = video;
    const corps = perso.getObjectByName("corps"), R = decor.presentateur;
    if (!video || R.mode !== "fondvert") { perso.visible = !!O.apercu; return; }
    texVideo = garder(new THREE.VideoTexture(video)); texVideo.colorSpace = THREE.SRGBColorSpace;
    corps.material = matierePresentateur(texVideo, true, R.teinte, perso.userData.teinte);
    const r = (video.videoWidth || 16) / (video.videoHeight || 9);
    corps.scale.set((perso.userData.hp * r) / perso.userData.lp, 1, 1);
    perso.visible = true;
  }

  const cible = new THREE.Vector3();
  function rendre(t, src) {
    if (!decor) return;
    const S = src || {};
    if (S.ecran && S.ecran !== canvasEcran) {
      canvasEcran = S.ecran;
      for (const e of texEcrans) { e.vive = texture(S.ecran); e.mat.map = e.vive; e.mat.needsUpdate = true; }
    }
    if (canvasEcran && S.ecran) for (const e of texEcrans) if (e.vive) e.vive.needsUpdate = true;
    poserVideo(S.camera || null);
    const p = reg.pose(decor.cameras, t);
    oeil.position.set(p.x, p.y, p.z); oeil.fov = p.champ; oeil.updateProjectionMatrix();
    cible.set(p.vers[0], p.vers[1], p.vers[2]); oeil.lookAt(cible);
    if (perso && perso.visible) perso.rotation.y = Math.atan2(p.x - perso.position.x, p.z - perso.position.z);
    racine.traverse((x) => { if (x.userData && x.userData.tourne) x.rotation.y = (t / 1000) * x.userData.tourne; });
    rendu.render(scene, oeil);
  }

  construire(O.decor);
  return {
    canvas, rendre,
    maj(d) { construire(d); canvasEcran = null; },
    camera(i, t) { return reg.basculer(i, t == null ? performance.now() : t); },
    cameras: () => decor.cameras.map((c) => c.nom),
    courante: () => reg.courante,
    taille(l, h) { rendu.setSize(Math.max(2, Math.round(l)), Math.max(2, Math.round(h)), false); oeil.aspect = l / h; oeil.updateProjectionMatrix(); },
    types: () => Object.keys(B),
    detruire() { vider(); try { rendu.dispose(); } catch (e) { /* contexte déjà perdu */ } },
  };
}

// les types que le moteur sait bâtir : égal au catalogue de la logique et du serveur (banc)
export const TYPES_MOTEUR = TYPES;
export { borne };
