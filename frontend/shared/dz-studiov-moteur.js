// dz-studiov-moteur.js — SV1 + SVH (14/11/2026, studio virtuel 3D), le MOTEUR D'AFFICHAGE du studio : il lit une recette
// (backend/app/services/studiov.py) et la construit en three.js — pièce, matières (motif dessiné ou VRAIE texture :
// couleur, normale, rugosité, répétées en mètres), reflets d'ambiance, lumières, objets du catalogue (niveau « direct » :
// volumes simples), rubans LED, néons à typographie, lettres rétroéclairées, écrans du décor, enseigne, présentateur —
// puis la rend à chaque image vue par la caméra courante.
// Conception docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md.
// SOURCE : frontend/shared ; copie OCTET POUR OCTET : frontend/dist/shared. Banc : backend/tests/test_studiov_ecran.py.
//
//   const m = creerMoteur(THREE, {largeur, hauteur, decor, contexte, qualite: "legere" | "haute", logo, apercu, textures});
//   m.canvas                       le canevas WebGL (dessiné par le calque « studiov » de la scène de capture)
//   m.maj(decor)                   reconstruit le décor (décorateur, changement de décor)
//   m.rendre(t, {ecran, camera})   une image : `ecran` = le canevas DÉJÀ CAVIARDÉ de la scène (jamais la source brute),
//                                  `camera` = la vidéo de la webcam (mode fond vert) ; t en ms
//   m.camera(i) ; m.cameras() ; m.courante() ; m.detruire()
// Atelier du décor (lot SVA) — l'écran s'en sert pour placer et choisir :
//   m.vueLibre(true | false)       quitte les caméras de la recette pour une vue qu'on tourne à la main ;
//   m.orbiter(dAz, dEl) ; m.zoomer(k) ; m.glisser(dx, dy) ; m.poseLibre() -> {x, y, z, vers, focale}
//   m.viser(nx, ny)                ce qu'il y a sous le pointeur (coordonnées -1..1) : {genre: "objet" | "surface" |
//                                  "lumiere" | "camera" | "ecran" | "enseigne", index | pan} ou null
//   m.choisir(cible | null)        entoure ce qui est choisi ; m.empreintes() -> l'emprise au sol de chaque objet
// Objets importés (lot SVO) : `objets` = {ref: fiche} (l'index de la bibliothèque) et `chargeur` = {classe: GLTFLoader} ;
// un objet de type « modele » y trouve son fichier — jamais une adresse écrite dans la recette.
// Images de la Bibliothèque (lot SVB) : `images` = {ref: {url, l, h, alpha}} ; un tableau, un logo mural, un kakémono,
// un écran du décor ou l'enseigne y trouvent leur image.
// `textures` = {ref: {cartes: {basecolor, normal, roughness}, taille_m, moyenne}} : l'index servi par
// le catalogue d'habillage du serveur. Le moteur ne fabrique JAMAIS une adresse depuis la recette : une référence absente de
// l'index retombe sur le motif dessiné.
// Les objets sont bâtis à l'ORIGINE de leur groupe : au sol (base à y = 0) ou, pour ce qui s'accroche au mur (cadre,
// panneau, néon, ruban, enseigne à mot, miroir, lattes…), centrés sur leur point de pose, le dos à z = 0.
import { palette, couleur, entier, regie, budgetLumieres, TYPES, borne, repetition } from "./dz-studiov-logique.js";

const K_SPOT = 26, K_NEON = 5, K_AMBIANCE = 1.0;         // intensités de la recette -> unités de three.js

// un tirage reproductible (les livres d'une bibliothèque ne changent pas d'une image à l'autre)
function alea(graine) { let s = graine >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
const octets = (hex) => { const n = entier(hex); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
const versHex = (r, g, b) => "#" + [r, g, b].map((v) => Math.round(borne(v, 0, 255)).toString(16).padStart(2, "0")).join("");
// le mélange de deux couleurs (k = 0 : a, k = 1 : b)
const melange = (a, b, k) => { const A = octets(a), B = octets(b); return versHex(A[0] + (B[0] - A[0]) * k, A[1] + (B[1] - A[1]) * k, A[2] + (B[2] - A[2]) * k); };

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
  const INDEX = O.textures || {}, OBJETS = O.objets || {}, IMAGES = O.images || {};
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
  let generation = 0, detruit = false;                   // une image qui arrive après une reconstruction est ignorée
  const jetables = [];                                   // géométries, matières, textures du décor courant
  const garder = (x) => { jetables.push(x); return x; };
  const durables = [];                                   // ce qui survit aux reconstructions (halos, reflets)
  const anisotropie = Math.min(8, rendu.capabilities.getMaxAnisotropy ? rendu.capabilities.getMaxAnisotropy() : 4);

  // ── images des vraies textures : chargées une fois, gardées d'une reconstruction à l'autre ──
  const images = new Map(), teintes = new Map(), gpu = new Map();
  function image(url) {
    if (!images.has(url)) images.set(url, new Promise((res) => {
      const im = new (doc.defaultView || window).Image();
      im.onload = () => res(im); im.onerror = () => res(null); im.src = url;
    }));
    return images.get(url);
  }
  // une carte de couleur ramenée à son RELIEF (clair / sombre autour de sa moyenne) puis peinte dans une couleur :
  // n'importe quelle matière dans n'importe quelle teinte (enduit blanc, cuir noir, velours bleu…)
  function teinter(im, url, hex) {
    const id = url + "|" + hex;
    if (teintes.has(id)) return teintes.get(id);
    const c = doc.createElement("canvas"); c.width = im.naturalWidth || im.width; c.height = im.naturalHeight || im.height;
    const x = c.getContext("2d", { willReadFrequently: true }); x.drawImage(im, 0, 0);
    let d;
    try { d = x.getImageData(0, 0, c.width, c.height); } catch (e) { return im; }
    const p = d.data, [R, G, B] = octets(hex);
    let s = 0;
    for (let i = 0; i < p.length; i += 16) s += p[i] * 0.299 + p[i + 1] * 0.587 + p[i + 2] * 0.114;
    const moy = Math.max(8, s / (p.length / 16));
    for (let i = 0; i < p.length; i += 4) {
      const k = (p[i] * 0.299 + p[i + 1] * 0.587 + p[i + 2] * 0.114) / moy;
      p[i] = Math.min(255, R * k); p[i + 1] = Math.min(255, G * k); p[i + 2] = Math.min(255, B * k);
    }
    x.putImageData(d, 0, 0);
    if (teintes.size > 24) teintes.delete(teintes.keys().next().value);
    teintes.set(id, c);
    return c;
  }

  // ── matières ──
  let cache = new Map();
  function texMotif(nom, hex, rep) {
    const t = garder(new THREE.CanvasTexture(motif(doc, nom, hex)));
    t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rep, rep);
    t.anisotropy = anisotropie;
    return t;
  }
  // les cartes d'une vraie texture, posées dès qu'elles arrivent (d'ici là : la couleur moyenne)
  function poserCartes(mat, T, m, hex, teinte) {
    const g0 = generation, rep = repetition(T.taille_m, m.echelle), C = T.cartes || {};
    const pose = (url, champ, srgb, apres) => { if (url) image(url).then((im) => {
      if (!im || g0 !== generation || detruit) return;
      // la texture GPU est gardée d'une reconstruction à l'autre (le décorateur reconstruit à chaque retouche)
      const peinte = champ === "map" && teinte, id = [url, rep.toFixed(4), peinte ? hex : ""].join("|");
      let t = gpu.get(id);
      if (!t) {
        const src = peinte ? teinter(im, url, hex) : im;
        t = src === im ? new THREE.Texture(im) : new THREE.CanvasTexture(src);
        t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rep, rep); t.anisotropy = anisotropie;
        if (srgb) t.colorSpace = THREE.SRGBColorSpace;
        t.needsUpdate = true; gpu.set(id, t);
      }
      t.userData.vue = generation; mat[champ] = t; apres(); mat.needsUpdate = true;
    }); };
    pose(C.basecolor, "map", true, () => mat.color.set(0xffffff));
    pose(C.normal, "normalMap", false, () => {});
    pose(C.roughness, "roughnessMap", false, () => { mat.roughness = Math.min(1, m.rugosite * 1.25); });
  }
  // une image de la Bibliothèque posée sur une matière : `cadre` = [l, h] du support (l'image le COUVRE, centrée, sans se
  // déformer) ; `eclaire` = elle garde un peu de sa propre lumière (une affiche reste lisible dans un décor sombre)
  const imgPretes = new Map();
  function poserImage(mat, ref, eclaire, cadre) {
    const I = IMAGES[ref]; if (!I) return;
    const g0 = generation;
    image(I.url).then((im) => {
      if (!im || g0 !== generation || detruit) return;
      const id = ["img", I.url, cadre ? cadre.join("x") : ""].join("|");
      let t = gpu.get(id);
      if (!t) {
        t = new THREE.Texture(im); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = anisotropie;
        if (cadre) {
          const ri = (im.naturalWidth || im.width) / (im.naturalHeight || im.height), rc = cadre[0] / cadre[1];
          if (ri > rc) { t.repeat.set(rc / ri, 1); t.offset.set((1 - rc / ri) / 2, 0); } else { t.repeat.set(1, ri / rc); t.offset.set(0, (1 - ri / rc) / 2); }
        }
        t.needsUpdate = true; gpu.set(id, t);
      }
      t.userData.vue = generation; mat.map = t; mat.color.set(0xffffff);
      if (eclaire) { mat.emissive = new THREE.Color(0xffffff); mat.emissiveMap = t; mat.emissiveIntensity = 0.22; }
      mat.needsUpdate = true;
    });
  }
  // les dimensions d'une image posée au mur : son plus grand côté fait 1 m (la taille de l'objet fait le reste)
  const formatImage = (ref) => { const I = IMAGES[ref], r = I && I.h ? I.l / I.h : 1.4; return r >= 1 ? [1, 1 / r] : [r, 1]; };
  // la matière d'une clé de la recette ; `coul` (la couleur propre d'un objet) repeint la matière. Ses UV sont en
  // MÈTRES (userData.metres) : la même matière sert un sol de 40 m² et un plateau de bureau, au même grain.
  function matiere(cle, coul) {
    const m = (cle && decor.matieres[cle]) || null;
    const hex = couleur(coul || (m && m.couleur), pal, "#808890");
    const id = [cle || "", hex].join("|");
    if (cache.has(id)) return cache.get(id);
    const T = m && m.texture ? INDEX[m.texture] : null;
    const p = { color: entier(hex), roughness: m ? m.rugosite : 0.7, metalness: m ? m.metal : 0 };
    if (T) { if (!(m.teinte || coul)) p.color = entier(T.moyenne || hex); } else if (m && m.motif !== "uni") { p.color = 0xffffff; p.map = texMotif(m.motif, hex, 1 / m.echelle); }
    if (m && m.emission > 0) { p.emissive = entier(hex); p.emissiveIntensity = m.emission; }
    const mat = garder(new THREE.MeshStandardMaterial(p));
    mat.userData.metres = !!(T || p.map);
    if (T) poserCartes(mat, T, m, hex, !!(m.teinte || coul));
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

  // ── volumes de base (y = le BAS du volume) ; UV en mètres pour les matières qui le demandent ──
  const ombres = (m) => { m.castShadow = m.receiveShadow = qualite === "haute"; return m; };
  const metres = (geo, mat, f) => { if (mat && mat.userData && mat.userData.metres) { const uv = geo.attributes.uv; for (let i = 0; i < uv.count; i++) { const k = f(i); uv.setXY(i, uv.getX(i) * k[0], uv.getY(i) * k[1]); } } return geo; };
  function bx(g, mat, l, h, p, x, y, z, ry) {
    const F = [[p, h], [p, h], [l, p], [l, p], [l, h], [l, h]];
    const m = ombres(new THREE.Mesh(metres(garder(new THREE.BoxGeometry(l, h, p)), mat, (i) => F[i >> 2]), mat));
    m.position.set(x || 0, (y || 0) + h / 2, z || 0); if (ry) m.rotation.y = ry; g.add(m); return m;
  }
  function cy(g, mat, r, h, x, y, z, rHaut, seg) {
    const k = [2 * Math.PI * r, h];
    const m = ombres(new THREE.Mesh(metres(garder(new THREE.CylinderGeometry(rHaut == null ? r : rHaut, r, h, seg || 20)), mat, () => k), mat));
    m.position.set(x || 0, (y || 0) + h / 2, z || 0); g.add(m); return m;
  }
  function sp(g, mat, r, x, y, z, sx, sy, sz) {
    const k = [2 * Math.PI * r, Math.PI * r];
    const m = ombres(new THREE.Mesh(metres(garder(new THREE.SphereGeometry(r, 20, 14)), mat, () => k), mat));
    m.position.set(x || 0, y || 0, z || 0); if (sx) m.scale.set(sx, sy || 1, sz || 1); g.add(m); return m;
  }
  function tore(g, mat, r, e, x, y, z, arc) {
    const m = ombres(new THREE.Mesh(garder(new THREE.TorusGeometry(r, e, 10, 36, arc || Math.PI * 2)), mat));
    m.position.set(x || 0, y || 0, z || 0); g.add(m); return m;
  }
  function plan(g, mat, l, h, x, y, z) {
    const k = [l, h];
    const m = new THREE.Mesh(metres(garder(new THREE.PlaneGeometry(l, h)), mat, () => k), mat); m.position.set(x || 0, y || 0, z || 0); g.add(m); return m;
  }
  // un disque d'épaisseur e, face vers +z, centré sur (x, y, z)
  function dq(g, mat, r, e, x, y, z, seg) { const m = cy(g, mat, r, e, 0, 0, 0, null, seg || 28); m.rotation.x = Math.PI / 2; m.position.set(x || 0, y || 0, z || 0); return m; }
  // un sous-groupe incliné : ce qu'on y bâtit tourne autour de (x, y, z)
  function pivot(g, x, y, z, rx, ry, rz) { const p = new THREE.Group(); p.position.set(x || 0, y || 0, z || 0); p.rotation.set(rx || 0, ry || 0, rz || 0); g.add(p); return p; }
  const pieds = (g, mat, dx, dz, h, e) => { for (const sx of [-1, 1]) for (const sz of [-1, 1]) bx(g, mat, e || 0.05, h, e || 0.05, sx * dx, 0, sz * dz); };

  // ── la lumière qui déborde : des halos additifs, sans aucun calcul d'éclairage (carte intégrée) ──
  // « rond » : un dégradé rond (étiré par le plan : ovale) ; « bande » : vif en bas, fondu vers le haut ; « disque » : bord net
  const formes = new Map();
  function texHalo(forme) {
    if (formes.has(forme)) return formes.get(forme);
    const c = doc.createElement("canvas"); c.width = c.height = 128;
    const x = c.getContext("2d");
    if (forme === "bande") {
      const g = x.createLinearGradient(0, 128, 0, 0); g.addColorStop(0, "rgba(255,255,255,1)"); g.addColorStop(0.18, "rgba(255,255,255,.55)"); g.addColorStop(0.5, "rgba(255,255,255,.18)"); g.addColorStop(1, "rgba(255,255,255,0)");
      x.fillStyle = g; x.fillRect(0, 0, 128, 128);
      x.globalCompositeOperation = "destination-in";
      const b = x.createLinearGradient(0, 0, 128, 0); b.addColorStop(0, "rgba(0,0,0,0)"); b.addColorStop(0.1, "rgba(0,0,0,.35)"); b.addColorStop(0.28, "rgba(0,0,0,1)"); b.addColorStop(0.72, "rgba(0,0,0,1)"); b.addColorStop(0.9, "rgba(0,0,0,.35)"); b.addColorStop(1, "rgba(0,0,0,0)");
      x.fillStyle = b; x.fillRect(0, 0, 128, 128);
    } else {
      const g = x.createRadialGradient(64, 64, 0, 64, 64, 64);
      if (forme === "disque") { g.addColorStop(0, "rgba(255,255,255,1)"); g.addColorStop(0.78, "rgba(255,255,255,.92)"); g.addColorStop(0.9, "rgba(255,255,255,.25)"); g.addColorStop(1, "rgba(255,255,255,0)"); }
      else { g.addColorStop(0, "rgba(255,255,255,1)"); g.addColorStop(0.3, "rgba(255,255,255,.45)"); g.addColorStop(0.65, "rgba(255,255,255,.12)"); g.addColorStop(1, "rgba(255,255,255,0)"); }
      x.fillStyle = g; x.fillRect(0, 0, 128, 128);
    }
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; durables.push(t);
    formes.set(forme, t);
    return t;
  }
  const additif = (hex, force, carte) => garder(new THREE.MeshBasicMaterial({ map: carte, color: new THREE.Color(entier(hex)).multiplyScalar(force == null ? 0.6 : force),
    transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false, side: THREE.DoubleSide }));
  // un halo posé à plat (sur un mur, un sol) : plan l × h centré sur (x, y, z), face vers +z
  function halo(g, hex, l, h, x, y, z, force, forme) { const m = plan(g, additif(hex, force, texHalo(forme || "rond")), l, h, x, y, z); m.renderOrder = 3; m.userData.halo = true; return m; }
  // la lueur d'une source ponctuelle (lampe, bougie) : toujours face à la caméra
  function eclat(g, hex, taille, x, y, z, force) {
    const s = new THREE.Sprite(garder(new THREE.SpriteMaterial({ map: texHalo("rond"), color: new THREE.Color(entier(hex)).multiplyScalar(force == null ? 0.5 : force),
      transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false })));
    s.scale.set(taille, taille, 1); s.position.set(x || 0, y || 0, z || 0); s.renderOrder = 3; s.userData.halo = true; g.add(s); return s;
  }

  // ── images dessinées : mots, écran en attente, enseigne, silhouette, ombre ──
  function toile(l, h, dessin) { const c = doc.createElement("canvas"); c.width = l; c.height = h; dessin(c.getContext("2d"), l, h); return c; }
  const texture = (c) => { const t = garder(new THREE.CanvasTexture(c)); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t; };
  // les polices embarquées (/fonts) : chargées à la demande ; un mot déjà peint est repeint quand sa police arrive
  const polices = new Map();
  let aRepeindre = [];
  function police(nom) {
    if (!/^[A-Za-z0-9]{2,24}$/.test(nom || "")) return;
    if (polices.has(nom)) return;
    const FF = (doc.defaultView || window).FontFace;
    if (!FF || !doc.fonts) { polices.set(nom, false); return; }
    polices.set(nom, false);
    new FF("DZ " + nom, `url(/fonts/${nom}.ttf)`).load().then((f) => {
      doc.fonts.add(f); polices.set(nom, true);
      for (const r of aRepeindre) if (r.police === nom && !detruit) { r.peindre(); r.tex.needsUpdate = true; }
    }).catch(() => { /* police absente : la police du système reste */ });
  }
  const fonte = (nom, px) => `${px}px "DZ ${nom}", system-ui, sans-serif`;
  // un mot centré dans la toile, réduit s'il déborde ; style : neon (tube clair + lueur), halo (la lueur seule),
  // plein (lettres pleines), creux (lettres sombres sur fond lumineux)
  function peindreMot(x, l, h, texte, nom, style, hex, fond) {
    x.clearRect(0, 0, l, h);
    if (fond) { x.fillStyle = fond; x.fillRect(0, 0, l, h); }
    let px = Math.round(h * 0.54);
    x.font = fonte(nom, px);
    const dispo = l - h * 0.5, w = x.measureText(texte).width;
    if (w > dispo) { px = Math.max(10, Math.floor((px * dispo) / w)); x.font = fonte(nom, px); }
    x.textAlign = "center"; x.textBaseline = "middle";
    const ecrire = () => x.fillText(texte, l / 2, h / 2 + px * 0.04);
    if (style === "neon" || style === "halo") {
      x.shadowColor = hex; x.fillStyle = hex;
      for (const b of (style === "halo" ? [h * 0.34, h * 0.2, h * 0.1] : [h * 0.2, h * 0.1, h * 0.04])) { x.shadowBlur = b; ecrire(); }
      x.shadowBlur = 0;
      if (style === "neon") { x.fillStyle = melange(hex, "#ffffff", 0.78); ecrire(); }
    } else { x.shadowBlur = 0; x.fillStyle = hex; ecrire(); }
  }
  // le plan d'un mot : 4 de large pour 1 de haut ; `additive` = ne fait qu'ajouter de la lumière (lueur sur le mur)
  function mot(g, texte, nom, style, hex, l, x, y, z, additive, fond) {
    police(nom);
    const c = toile(1024, 256, () => {}), ctx = c.getContext("2d");
    const peindre = () => peindreMot(ctx, 1024, 256, texte, nom, style, hex, fond);
    peindre();
    const tex = texture(c);
    aRepeindre.push({ police: nom, peindre, tex });
    const mat = garder(new THREE.MeshBasicMaterial(additive
      ? { map: tex, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false }
      : { map: tex, transparent: !fond, depthWrite: !!fond, toneMapped: false, alphaTest: fond ? 0 : 0.02 }));
    const m = plan(g, mat, l, l / 4, x, y, z); m.renderOrder = additive ? 3 : 4; if (additive) m.userData.halo = true;
    return m;
  }

  // ── le catalogue : type -> constructeur(g, m) ; m.p = la matière propre de l'objet, m.s = sa matière secondaire
  // (piètement, structure : null = le noir d'usage), m.c = sa couleur, m.t = son mot, m.f = sa police ──
  const NOIR = "#14161a", ACIER = "#8c949c", BLANC = "#eef0f2", CHAUD = "#ffcf8a", LAITON = "#b8923a";
  const B = {
    bureau(g, m) { bx(g, m.p, 1.6, 0.04, 0.7, 0, 0.71); bx(g, m.s || m.p, 0.04, 0.71, 0.64, -0.76, 0); bx(g, m.s || m.p, 0.04, 0.71, 0.64, 0.76, 0); bx(g, m.s || uni(NOIR), 1.48, 0.3, 0.02, 0, 0.38, -0.3); },
    table(g, m) { bx(g, m.p, 1.2, 0.04, 0.7, 0, 0.71); pieds(g, m.s || uni(NOIR, 0.4, 0.5), 0.54, 0.29, 0.71); },
    table_ronde(g, m) { cy(g, m.p, 0.62, 0.04, 0, 0.7, 0, null, 40); cy(g, m.s || uni(NOIR, 0.4, 0.6), 0.05, 0.68, 0, 0.02); cy(g, m.s || uni(NOIR, 0.4, 0.6), 0.32, 0.02, 0, 0, 0, null, 32); },
    pupitre(g, m) { bx(g, m.p, 0.5, 0.98, 0.4, 0, 0); bx(g, m.s || m.p, 0.62, 0.03, 0.5, 0, 0.98); bx(g, lueur(pal.principale, 1.2), 0.5, 0.02, 0.01, 0, 0.6, 0.205); },
    etabli(g, m) { bx(g, m.p, 3.2, 0.06, 0.7, 0, 0.84); pieds(g, m.s || uni(ACIER, 0.4, 0.8), 1.5, 0.29, 0.84, 0.06); bx(g, m.p, 3.1, 0.03, 0.6, 0, 0.3); },
    bureau_angle(g, m) { const s = m.s || uni(NOIR, 0.4, 0.5); bx(g, m.p, 1.6, 0.04, 0.7, 0, 0.71); bx(g, m.p, 0.7, 0.04, 1.0, 0.45, 0.71, 0.85); bx(g, s, 0.04, 0.71, 0.64, -0.76, 0); bx(g, s, 0.04, 0.71, 0.64, 0.76, 0, 0); bx(g, s, 0.64, 0.71, 0.04, 0.45, 0, 1.31); bx(g, s, 1.48, 0.3, 0.02, 0, 0.38, -0.3); },
    table_basse(g, m) { bx(g, m.p, 1.0, 0.04, 0.55, 0, 0.36); bx(g, m.p, 0.9, 0.02, 0.45, 0, 0.12); pieds(g, m.s || uni(NOIR, 0.4, 0.5), 0.46, 0.235, 0.36, 0.035); },
    console(g, m) { const s = m.s || uni(NOIR, 0.4, 0.5); bx(g, m.p, 1.6, 0.5, 0.42, 0, 0.14); bx(g, m.p, 1.64, 0.03, 0.45, 0, 0.64); for (const x of [-0.4, 0, 0.4]) bx(g, s, 0.006, 0.44, 0.006, x, 0.17, 0.212); for (const x of [-0.6, -0.2, 0.2, 0.6]) bx(g, uni(LAITON, 0.35, 1), 0.012, 0.09, 0.014, x, 0.36, 0.216); pieds(g, s, 0.72, 0.16, 0.14, 0.035); },
    comptoir(g, m) { bx(g, m.p, 2.4, 1.0, 0.55, 0, 0); bx(g, m.s || uni(NOIR, 0.3, 0.3), 2.5, 0.05, 0.66, 0, 1.0); bx(g, lueur(m.c || pal.principale, 2.0), 2.4, 0.03, 0.01, 0, 0.1, 0.281); bx(g, lueur(m.c || pal.principale, 2.0), 2.4, 0.02, 0.01, 0, 0.94, 0.281); const h = halo(g, m.c || pal.principale, 2.9, 0.9, 0, 0.006, 0.7, 0.35, "bande"); h.rotation.x = Math.PI / 2; },
    chaise(g, m) { bx(g, m.p, 0.44, 0.04, 0.44, 0, 0.44); bx(g, m.p, 0.44, 0.44, 0.04, 0, 0.5, -0.2); pieds(g, m.s || uni(NOIR), 0.19, 0.19, 0.44, 0.035); },
    fauteuil(g, m) { const s = m.s || uni(NOIR, 0.4, 0.6); bx(g, m.p, 0.6, 0.14, 0.58, 0, 0.36); bx(g, m.p, 0.6, 0.62, 0.12, 0, 0.44, -0.26); bx(g, m.p, 0.08, 0.2, 0.5, -0.32, 0.46); bx(g, m.p, 0.08, 0.2, 0.5, 0.32, 0.46); cy(g, s, 0.04, 0.34, 0, 0.02); cy(g, s, 0.3, 0.03, 0, 0, 0, null, 5); },
    canape(g, m) { bx(g, m.p, 2.0, 0.3, 0.85, 0, 0.12); bx(g, m.p, 2.0, 0.5, 0.2, 0, 0.4, -0.33); bx(g, m.p, 0.2, 0.5, 0.85, -1.0, 0.12); bx(g, m.p, 0.2, 0.5, 0.85, 1.0, 0.12); for (const x of [-0.46, 0.46]) bx(g, m.p, 0.88, 0.12, 0.6, x, 0.42, 0.1); pieds(g, m.s || uni(NOIR), 0.95, 0.36, 0.12, 0.06); },
    banc(g, m) { bx(g, m.p, 1.4, 0.06, 0.4, 0, 0.42); pieds(g, m.s || uni(NOIR, 0.4, 0.5), 0.6, 0.15, 0.42); },
    chaise_bureau(g, m) { const s = m.s || uni(NOIR, 0.4, 0.5); bx(g, m.p, 0.48, 0.08, 0.46, 0, 0.42); bx(g, m.p, 0.44, 0.52, 0.06, 0, 0.56, -0.23); bx(g, s, 0.05, 0.1, 0.05, 0, 0.5, -0.24); for (const x of [-0.27, 0.27]) { bx(g, s, 0.04, 0.2, 0.04, x, 0.46, -0.05); bx(g, s, 0.05, 0.025, 0.26, x, 0.65, 0); } cy(g, s, 0.03, 0.3, 0, 0.1); for (let i = 0; i < 5; i++) { const a = (i * Math.PI * 2) / 5; const b = bx(g, s, 0.3, 0.03, 0.045, Math.cos(a) * 0.15, 0.07, Math.sin(a) * 0.15); b.rotation.y = -a; sp(g, uni(NOIR, 0.5), 0.03, Math.cos(a) * 0.29, 0.03, Math.sin(a) * 0.29); } },
    chaise_gaming(g, m) { const s = uni(NOIR, 0.4, 0.5), c = uni(m.c || pal.principale, 0.5); bx(g, m.p, 0.5, 0.1, 0.48, 0, 0.42); bx(g, m.p, 0.5, 0.86, 0.08, 0, 0.52, -0.24); for (const x of [-0.21, 0.21]) { bx(g, c, 0.07, 0.8, 0.086, x, 0.54, -0.238); bx(g, c, 0.07, 0.104, 0.46, x, 0.42, 0.01); bx(g, s, 0.05, 0.03, 0.26, x * 1.38, 0.66, 0); bx(g, s, 0.04, 0.16, 0.04, x * 1.38, 0.5, -0.05); } bx(g, c, 0.26, 0.14, 0.05, 0, 1.2, -0.19); cy(g, s, 0.03, 0.3, 0, 0.1); for (let i = 0; i < 5; i++) { const a = (i * Math.PI * 2) / 5; const b = bx(g, s, 0.32, 0.03, 0.045, Math.cos(a) * 0.16, 0.07, Math.sin(a) * 0.16); b.rotation.y = -a; sp(g, c, 0.03, Math.cos(a) * 0.31, 0.03, Math.sin(a) * 0.31); } },
    tabouret(g, m) { const s = m.s || uni(NOIR, 0.4, 0.6); cy(g, m.p, 0.18, 0.045, 0, 0.68, 0, null, 28); for (let i = 0; i < 4; i++) { const a = Math.PI / 4 + (i * Math.PI) / 2, p = pivot(g, Math.cos(a) * 0.12, 0.68, Math.sin(a) * 0.12, Math.sin(a) * 0.14, 0, -Math.cos(a) * 0.14); bx(p, s, 0.025, 0.7, 0.025, 0, -0.7, 0); } tore(g, s, 0.17, 0.008, 0, 0.26, 0).rotation.x = Math.PI / 2; },
    pouf(g, m) { cy(g, m.p, 0.3, 0.34, 0, 0, 0, null, 28); sp(g, m.p, 0.3, 0, 0.34, 0, 1, 0.28, 1); },
    etagere(g, m) { for (const x of [-0.5, 0.5]) bx(g, m.p, 0.03, 2.0, 0.3, x, 0); for (const y of [0.03, 0.43, 0.83, 1.23, 1.63, 1.97]) bx(g, m.p, 1.0, 0.04, 0.3, 0, y); bx(g, m.s || uni(NOIR, 0.9), 1.0, 2.0, 0.01, 0, 0, -0.15); },
    bibliotheque(g, m) {
      B.etagere(g, m); const r = alea(41), tons = ["#8b3a3a", "#2f5d8a", "#d9c7a0", "#3d6b4f", "#b5762e", "#4a4458", "#c9c9c9"];
      for (const y of [0.07, 0.47, 0.87, 1.27, 1.67]) { let x = -0.46; while (x < 0.4) { const e = 0.03 + r() * 0.04, h = 0.2 + r() * 0.12; bx(g, uni(tons[(r() * tons.length) | 0], 0.8), e, h, 0.2, x + e / 2, y, 0.02); x += e + 0.004; if (r() < 0.12) x += 0.1; } }
    },
    vitrine(g, m) { B.etagere(g, m); bx(g, lueur("#ffe2b0", 1.4), 0.96, 0.015, 0.03, 0, 1.955, 0.12); bx(g, lueur("#ffe2b0", 1.0), 0.96, 0.012, 0.02, 0, 1.215, 0.13); bx(g, lueur("#ffe2b0", 1.0), 0.96, 0.012, 0.02, 0, 0.815, 0.13); },
    casier(g, m) { bx(g, m.p, 0.6, 1.9, 0.5, 0, 0); bx(g, uni(NOIR, 0.5, 0.5), 0.01, 1.8, 0.01, 0, 0.05, 0.255); for (const y of [1.6, 1.66, 1.72]) bx(g, uni(NOIR), 0.3, 0.015, 0.01, 0, y, 0.255); bx(g, uni(ACIER, 0.3, 0.9), 0.02, 0.1, 0.03, 0.2, 1.0, 0.26); },
    etagere_murale(g, m) { bx(g, m.p, 1.0, 0.035, 0.22, 0, -0.0175, 0.11); for (const x of [-0.38, 0.38]) bx(g, m.s || uni(NOIR, 0.4, 0.6), 0.02, 0.1, 0.16, x, -0.118, 0.08); },
    cube_rangement(g, m) { for (let i = 0; i < 5; i++) { bx(g, m.p, 0.036, 1.52, 0.38, -0.742 + i * 0.371, 0); bx(g, m.p, 1.52, 0.036, 0.38, 0, i * 0.371); } bx(g, m.s || uni(NOIR, 0.9), 1.5, 1.5, 0.008, 0, 0.01, -0.186); },
    meuble_tv(g, m) { const s = m.s || uni(NOIR, 0.4, 0.5); bx(g, m.p, 1.8, 0.035, 0.4, 0, 0.47); bx(g, m.p, 1.8, 0.035, 0.4, 0, 0.12); for (const x of [-0.885, -0.3, 0.3, 0.885]) bx(g, m.p, 0.03, 0.32, 0.4, x, 0.155); bx(g, s, 0.57, 0.31, 0.012, -0.59, 0.158, 0.19); bx(g, s, 0.57, 0.31, 0.012, 0.59, 0.158, 0.19); pieds(g, s, 0.82, 0.15, 0.12, 0.03); },
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
    enceinte(g, m) { const n = m.s || uni(NOIR, 0.6, 0.1); bx(g, n, 0.2, 0.32, 0.24, 0, 0); dq(g, uni("#2a2d33", 0.5, 0.3), 0.075, 0.02, 0, 0.12, 0.122); dq(g, uni(m.c || "#d9a941", 0.3, 0.8), 0.03, 0.024, 0, 0.12, 0.124); dq(g, uni("#2a2d33", 0.4, 0.5), 0.028, 0.02, 0, 0.255, 0.122); bx(g, lueur("#ffffff", 1.4), 0.008, 0.008, 0.004, 0.07, 0.02, 0.121); },
    table_mixage(g, m) { const p = pivot(g, 0, 0, 0.15, 0.16); bx(p, uni(NOIR, 0.5, 0.4), 0.5, 0.05, 0.32, 0, 0, -0.16); const r = alea(11), tons = [pal.principale, pal.accent, "#e5484d", "#f0b429"]; for (let i = 0; i < 8; i++) { bx(p, uni("#d8dade", 0.5), 0.012, 0.014, 0.03, -0.21 + i * 0.06, 0.05, -0.08 - r() * 0.06); cy(p, uni(tons[i % 4], 0.4), 0.011, 0.016, -0.21 + i * 0.06, 0.05, -0.24, null, 10); cy(p, uni("#3a3e46", 0.4), 0.009, 0.014, -0.21 + i * 0.06, 0.05, -0.285, null, 10); } bx(p, lueur(m.c || pal.accent, 1.2), 0.06, 0.004, 0.04, 0.2, 0.05, -0.2); },
    anneau_lumineux(g, m) { const n = uni(NOIR, 0.4, 0.5); cy(g, n, 0.012, 1.42, 0, 0); for (const a of [0, 2.1, 4.2]) { const p = bx(g, n, 0.012, 0.5, 0.012, Math.cos(a) * 0.14, 0, Math.sin(a) * 0.14); p.rotation.set(Math.sin(a) * 0.55, 0, -Math.cos(a) * 0.55); } tore(g, lueur(m.c || "#fff2dc", 2.4), 0.23, 0.028, 0, 1.62, 0); eclat(g, m.c || "#fff2dc", 1.1, 0, 1.62, 0, 0.35); },
    ordinateur_portable(g) { const n = uni("#a8aeb6", 0.35, 0.8); bx(g, n, 0.34, 0.014, 0.24, 0, 0); bx(g, uni(NOIR, 0.6), 0.3, 0.002, 0.12, 0, 0.014, -0.03); const p = pivot(g, 0, 0.014, -0.118, -0.28); bx(p, n, 0.34, 0.22, 0.008, 0, 0, 0); bx(p, lueur(pal.accent, 0.5), 0.32, 0.2, 0.002, 0, 0.01, 0.005); },
    clavier(g, m) { bx(g, uni(NOIR, 0.5, 0.3), 0.44, 0.018, 0.14, 0, 0); for (let i = 0; i < 4; i++) bx(g, uni("#2a2d33", 0.6), 0.41, 0.008, 0.026, 0, 0.018, -0.048 + i * 0.032); bx(g, lueur(m.c || pal.principale, 1.6), 0.44, 0.004, 0.004, 0, 0.002, 0.071); },
    tour_pc(g, m) { const c = m.c || pal.accent; bx(g, uni(NOIR, 0.4, 0.4), 0.21, 0.45, 0.44, 0, 0); bx(g, uni("#0a0c10", 0.05, 0.6), 0.004, 0.4, 0.39, 0.106, 0.025); for (const y of [0.1, 0.225, 0.35]) tore(g, lueur(c, 2.0), 0.048, 0.006, 0, y, 0.222); bx(g, lueur(c, 1.4), 0.004, 0.36, 0.01, 0.108, 0.045, 0.1); bx(g, lueur(pal.principale, 1.4), 0.004, 0.01, 0.3, 0.108, 0.3, 0); },
    appareil_photo(g) { const n = uni(NOIR, 0.5, 0.3); bx(g, n, 0.13, 0.085, 0.06, 0, 0); bx(g, n, 0.05, 0.025, 0.05, 0, 0.085); dq(g, uni("#22252b", 0.3, 0.6), 0.036, 0.06, 0, 0.042, 0.06); dq(g, uni("#0a0f18", 0.05, 0.9), 0.027, 0.004, 0, 0.042, 0.092); bx(g, uni("#c9ccd2", 0.3, 0.9), 0.016, 0.008, 0.016, 0.045, 0.085); },
    lampe(g, m) { const n = uni(NOIR, 0.4, 0.6), c = m.c || CHAUD; cy(g, n, 0.07, 0.015, 0, 0); cy(g, n, 0.008, 0.32, 0, 0.015); cy(g, lueur(c, 1.8), 0.09, 0.11, 0, 0.3, 0, 0.05); eclat(g, c, 0.7, 0, 0.35, 0, 0.32); },
    lampadaire(g, m) { const n = uni(NOIR, 0.4, 0.6), c = m.c || CHAUD; cy(g, n, 0.16, 0.02, 0, 0, 0, null, 28); cy(g, n, 0.012, 1.55, 0, 0.02); cy(g, lueur(c, 1.7), 0.17, 0.26, 0, 1.5, 0, 0.12, 28); eclat(g, c, 1.5, 0, 1.62, 0, 0.3); },
    neon_barre(g, m) { const c = m.c || pal.principale, t = cy(g, lueur(c, 2.4), 0.018, 1.2, 0, -0.6, 0); t.rotation.z = Math.PI / 2; t.position.set(0, 0, 0.02); halo(g, c, 1.7, 0.55, 0, 0, 0.005, 0.5); },
    neon_anneau(g, m) { const c = m.c || pal.principale; tore(g, lueur(c, 2.4), 0.36, 0.02, 0, 0, 0.03); halo(g, c, 1.3, 1.3, 0, 0, 0.005, 0.32); },
    guirlande(g) { for (let i = 0; i <= 24; i++) { const u = i / 24 - 0.5; sp(g, lueur("#ffd9a0", 2.2), 0.022, u * 4.2, -Math.cos(u * Math.PI) * 0.22 * (1 + 0.3 * Math.cos(u * 12)), 0.04); } halo(g, "#ffd9a0", 4.6, 0.7, 0, -0.12, 0.005, 0.16); },
    tube_lumineux(g, m) { const c = m.c || pal.principale; cy(g, uni(NOIR, 0.4, 0.6), 0.09, 0.06, 0, 0); cy(g, lueur(c, 2.4), 0.035, 2.3, 0, 0.06, 0, null, 14); cy(g, uni(NOIR, 0.4, 0.6), 0.06, 0.04, 0, 2.36); const s = eclat(g, c, 1.0, 0, 1.2, 0, 0.3); s.scale.set(0.9, 2.9, 1); },
    ruban_led(g, m) { const c = m.c || pal.principale; bx(g, lueur(c, 2.6), 1.0, 0.012, 0.008, 0, -0.006, 0.004); halo(g, c, 1.5, 0.8, 0, 0.4, 0.006, 0.8, "bande"); const b = halo(g, c, 1.5, 0.22, 0, -0.11, 0.006, 0.45, "bande"); b.rotation.z = Math.PI; },
    ruban_led_sol(g, m) { const c = m.c || pal.principale; bx(g, lueur(c, 2.6), 1.0, 0.008, 0.012, 0, 0.012, 0); const h = halo(g, c, 1.5, 0.85, 0, 0.007, 0.425, 0.75, "bande"); h.rotation.x = Math.PI / 2; },
    panneau_hexa(g, m) { const c = m.c || pal.principale, tons = [c, pal.accent, melange(c, pal.accent, 0.5), c, melange(c, "#ffffff", 0.35), pal.accent, c]; [[0, 0], [0.213, 0], [0.1065, 0.1845], [-0.1065, 0.1845], [0.3195, 0.1845], [-0.213, 0], [0.1065, -0.1845]].forEach(([x, y], i) => { const d = dq(g, lueur(tons[i], 1.5), 0.118, 0.014, x, y, 0.012, 6); d.rotation.y = Math.PI / 6; }); halo(g, c, 1.5, 1.2, 0.05, 0.02, 0.004, 0.4); },
    barre_led(g, m) { const c = m.c || pal.principale; cy(g, uni(NOIR, 0.4, 0.5), 0.05, 0.012, 0, 0, 0, null, 20); bx(g, uni(NOIR, 0.4, 0.5), 0.034, 0.42, 0.02, 0, 0.012, 0.012); bx(g, lueur(c, 2.4), 0.03, 0.4, 0.012, 0, 0.022, -0.006); const s = eclat(g, c, 1.0, 0, 0.25, -0.1, 0.4); s.scale.set(0.9, 1.3, 1); },
    suspension(g, m) { const c = m.c || "#ffb060", n = m.s || uni(NOIR, 0.4, 0.6); cy(g, uni(NOIR, 0.6), 0.004, 0.8, 0, -0.8, 0, null, 6); cy(g, n, 0.04, 0.02, 0, -0.02, 0, null, 16); cy(g, n, 0.17, 0.13, 0, -0.93, 0, 0.04, 24); sp(g, lueur(c, 2.4), 0.045, 0, -0.93, 0, 1, 1.25, 1); eclat(g, c, 0.9, 0, -0.95, 0, 0.42); },
    applique(g, m) { const c = m.c || CHAUD; bx(g, uni(LAITON, 0.35, 1), 0.07, 0.16, 0.02, 0, -0.08, 0.01); cy(g, lueur(c, 2.0), 0.045, 0.16, 0, -0.08, 0.07, null, 16); halo(g, c, 0.9, 1.3, 0, 0.5, 0.004, 0.42); halo(g, c, 0.9, 1.1, 0, -0.45, 0.004, 0.32); },
    lampe_coucher(g, m) { const c = m.c || "#ff6a3d"; halo(g, c, 1.3, 1.3, 0, 0, 0.004, 0.55, "disque"); halo(g, melange(c, "#ffd23f", 0.6), 0.8, 0.8, 0.12, -0.1, 0.005, 0.5, "disque"); halo(g, c, 2.4, 2.4, 0, 0, 0.003, 0.2); },
    lampe_lave(g, m) { const c = m.c || "#ff3d7f", n = uni("#b8bcc4", 0.3, 0.9); cy(g, n, 0.06, 0.08, 0, 0, 0, 0.035, 20); cy(g, lueur(c, 1.3), 0.04, 0.2, 0, 0.08, 0, 0.026, 20); for (const [y, r] of [[0.12, 0.022], [0.18, 0.016], [0.23, 0.012]]) sp(g, lueur(melange(c, "#ffffff", 0.4), 1.8), r, 0, y, 0); cy(g, n, 0.026, 0.04, 0, 0.28, 0, 0.015, 20); eclat(g, c, 0.55, 0, 0.18, 0, 0.3); },
    bougie(g, m) { cy(g, uni(m.c || "#f1e9d8", 0.8), 0.03, 0.09, 0, 0, 0, null, 16); sp(g, lueur("#ffb050", 2.6), 0.011, 0, 0.108, 0, 1, 1.7, 1); eclat(g, "#ffb050", 0.34, 0, 0.11, 0, 0.5); },
    neon_texte(g, m) { const c = m.c || pal.principale; halo(g, c, 1.7, 0.75, 0, 0, 0.004, 0.42); mot(g, m.t || "HELLO", m.f, "neon", c, 1.4, 0, 0, 0.03); },
    lettres_retro(g, m) { const c = m.c || pal.principale; mot(g, m.t || "STUDIO", m.f, "halo", c, 1.5, 0, 0, 0.004, true); mot(g, m.t || "STUDIO", m.f, "plein", m.s ? "#" + m.s.color.getHexString() : "#15171c", 1.4, 0, 0, 0.045); },
    caisson_lumineux(g, m) { const c = m.c || "#fff4e0"; bx(g, m.s || uni(NOIR, 0.4, 0.4), 1.24, 0.35, 0.07, 0, -0.175, 0.035); halo(g, c, 1.9, 0.95, 0, 0, 0.004, 0.3); mot(g, m.t || "LIVE", m.f, "plein", "#15171c", 1.2, 0, 0, 0.072, false, melange(c, "#ffffff", 0.75)); },
    panneau_direct(g, m) { const c = m.c || "#ff2b2b"; bx(g, uni(NOIR, 0.4, 0.4), 0.66, 0.22, 0.07, 0, -0.11, 0.035); halo(g, c, 1.2, 0.7, 0, 0, 0.004, 0.4); mot(g, m.t || "ON AIR", m.f, "neon", c, 0.62, 0, 0, 0.072, false, "#120405"); },
    cadre(g, m) { bx(g, uni("#1b1d21", 0.5), 0.6, 0.8, 0.03, 0, -0.4, 0.015); bx(g, uni(BLANC, 0.9), 0.52, 0.72, 0.005, 0, -0.36, 0.032); bx(g, uni(m.c || pal.principale, 0.8), 0.3, 0.36, 0.004, 0.03, -0.2, 0.036); bx(g, uni(pal.accent, 0.8), 0.18, 0.18, 0.004, -0.1, 0.04, 0.038); },
    horloge(g) { const d = cy(g, uni(BLANC, 0.6), 0.2, 0.03, 0, 0, 0.015, null, 32); d.rotation.x = Math.PI / 2; d.position.y = 0; const c = tore(g, uni(NOIR, 0.4, 0.5), 0.2, 0.014, 0, 0, 0.03); c.rotation.set(0, 0, 0); bx(g, uni(NOIR), 0.012, 0.13, 0.006, 0, 0, 0.034); bx(g, uni(NOIR), 0.1, 0.012, 0.006, 0.05, -0.006, 0.034); },
    fenetre(g) { bx(g, uni(BLANC, 0.7), 1.7, 1.9, 0.06, 0, -0.95, 0); bx(g, lueur("#fff6e0", 3.0), 1.56, 1.76, 0.01, 0, -0.88, 0.03); bx(g, uni(BLANC, 0.7), 0.04, 1.76, 0.03, 0, -0.88, 0.035); bx(g, uni(BLANC, 0.7), 1.56, 0.04, 0.03, 0, -0.02, 0.035); },
    affiche(g, m) { const c = m.c || pal.principale; bx(g, uni(melange(c, "#000000", 0.72), 0.8), 0.5, 0.7, 0.008, 0, -0.35, 0.004); dq(g, uni(pal.accent, 0.8), 0.15, 0.004, 0.04, 0.1, 0.01, 40); dq(g, uni(c, 0.8), 0.1, 0.004, -0.08, 0.02, 0.012, 40); bx(g, uni(BLANC, 0.8), 0.34, 0.05, 0.004, 0, -0.26, 0.01); bx(g, uni(BLANC, 0.8), 0.22, 0.018, 0.004, -0.06, -0.3, 0.01); },
    miroir(g, m) { dq(g, m.s || uni(LAITON, 0.3, 1), 0.33, 0.024, 0, 0, 0.012, 48); dq(g, uni("#dfe6ee", 0.03, 1.0), 0.305, 0.026, 0, 0, 0.013, 48); },
    vinyle_mural(g, m) { bx(g, uni("#1b1d21", 0.5), 0.38, 0.38, 0.02, 0, -0.19, 0.01); bx(g, uni("#f1ede4", 0.9), 0.34, 0.34, 0.004, 0, -0.17, 0.021); dq(g, uni("#0c0c0e", 0.3, 0.2), 0.15, 0.004, 0, 0, 0.026, 48); for (const r of [0.13, 0.11, 0.09]) tore(g, uni("#26262a", 0.3, 0.4), r, 0.0015, 0, 0, 0.029); dq(g, uni(m.c || pal.principale, 0.6), 0.05, 0.005, 0, 0, 0.027, 32); },
    mur_lattes(g, m) { bx(g, m.s || uni("#0c0c0e", 1.0), 1.2, 2.4, 0.012, 0, -1.2, 0.006); for (let i = 0; i < 20; i++) bx(g, m.p, 0.036, 2.4, 0.024, -0.57 + i * 0.06, -1.2, 0.024); },
    panneau_perfore(g, m) { bx(g, m.p, 1.0, 0.8, 0.012, 0, -0.4, 0.006); const n = uni(NOIR, 0.5, 0.3); for (let j = 0; j < 7; j++) for (let i = 0; i < 9; i++) dq(g, n, 0.006, 0.002, -0.4 + i * 0.1, -0.3 + j * 0.1, 0.0125, 8); bx(g, m.s || uni("#c9a36a", 0.6), 0.34, 0.016, 0.1, -0.28, -0.22, 0.062); bx(g, uni(pal.principale, 0.6), 0.07, 0.1, 0.07, -0.36, -0.204, 0.06); bx(g, uni(pal.accent, 0.6), 0.05, 0.14, 0.05, -0.24, -0.204, 0.06); for (const x of [0.1, 0.22, 0.34]) { dq(g, uni(ACIER, 0.3, 0.9), 0.005, 0.05, x, 0.2, 0.037, 8); bx(g, uni(x > 0.2 ? "#e5484d" : ACIER, 0.5, 0.4), 0.03, 0.2, 0.012, x, -0.02, 0.05); } tore(g, n, 0.07, 0.01, 0.3, -0.22, 0.04, Math.PI); },
    rideau(g, m) { for (let i = 0; i < 16; i++) { const c = cy(g, m.p, 0.068, 2.6, -0.94 + i * 0.125, 0, 0.05, null, 10); c.scale.z = 0.6; } const t = cy(g, m.s || uni(LAITON, 0.35, 1), 0.012, 2.1, 0, 0, 0.06, null, 8); t.rotation.z = Math.PI / 2; t.position.set(0, 2.62, 0.06); },
    plante(g) { cy(g, uni("#b9a48c", 0.9), 0.14, 0.28, 0, 0, 0, 0.17); const v = uni("#3c7a45", 0.8), v2 = uni("#2d6338", 0.8), r = alea(7); cy(g, uni("#4a3a28", 0.9), 0.012, 0.5, 0, 0.26); for (let i = 0; i < 9; i++) { const a = i * 0.7, h = 0.45 + r() * 0.45, d = 0.08 + r() * 0.16; const f = sp(g, i % 2 ? v : v2, 0.13, Math.cos(a) * d, h, Math.sin(a) * d, 0.55, 1.5, 0.3); f.rotation.set(Math.sin(a) * 0.5, a, -Math.cos(a) * 0.5); } },
    cactus(g, m) { const v = uni(m.c || "#3f7d4a", 0.8); cy(g, uni("#c2673f", 0.9), 0.06, 0.09, 0, 0, 0, 0.075, 18); cy(g, v, 0.045, 0.24, 0, 0.08, 0, null, 12); sp(g, v, 0.045, 0, 0.32, 0); cy(g, v, 0.022, 0.07, 0.075, 0.2, 0, null, 10); sp(g, v, 0.022, 0.075, 0.27, 0); const b = cy(g, v, 0.02, 0.06, 0.05, 0.19, 0, null, 8); b.rotation.z = Math.PI / 2; b.position.set(0.055, 0.2, 0); cy(g, v, 0.02, 0.05, -0.07, 0.15, 0, null, 10); sp(g, v, 0.02, -0.07, 0.2, 0); },
    plante_tombante(g) { cy(g, uni("#e9e4da", 0.8), 0.075, 0.11, 0, 0, 0, 0.09, 18); const v = uni("#3c7a45", 0.8), v2 = uni("#58994f", 0.8), r = alea(23); for (let i = 0; i < 7; i++) { const a = i * 0.9; sp(g, i % 2 ? v : v2, 0.05, Math.cos(a) * 0.06, 0.13 + r() * 0.05, Math.sin(a) * 0.06, 1, 0.5, 0.8); } for (let k = 0; k < 4; k++) { const x = -0.07 + k * 0.045, n = 4 + ((r() * 4) | 0); for (let j = 0; j < n; j++) sp(g, (j + k) % 2 ? v : v2, 0.03, x + Math.sin(j * 1.3 + k) * 0.015, 0.08 - j * 0.07, 0.1, 1, 0.6, 0.5); } },
    vase(g, m) { const c = m.p; cy(g, c, 0.045, 0.12, 0, 0, 0, 0.08, 24); cy(g, c, 0.08, 0.1, 0, 0.12, 0, 0.03, 24); cy(g, c, 0.03, 0.05, 0, 0.22, 0, 0.038, 24); const t = uni("#4f7a3c", 0.8); for (const [x, z, h] of [[0.01, 0, 0.26], [-0.015, 0.01, 0.2], [0.02, -0.012, 0.16]]) { cy(g, t, 0.003, h, x, 0.25, z, null, 5); sp(g, uni(m.c || "#f0b6c8", 0.8), 0.028, x, 0.25 + h, z, 1, 0.7, 1); } },
    livres(g) { const tons = ["#8b3a3a", "#2f5d8a", "#d9c7a0", "#3d6b4f", "#b5762e"]; bx(g, uni(tons[0], 0.8), 0.24, 0.035, 0.17, 0, 0, 0, 0.1); bx(g, uni(tons[1], 0.8), 0.22, 0.03, 0.16, 0.01, 0.035, 0, -0.12); bx(g, uni(tons[2], 0.8), 0.2, 0.025, 0.15, -0.005, 0.065, 0, 0.3); for (let i = 0; i < 3; i++) bx(g, uni(tons[i + 2], 0.8), 0.03, 0.2 - i * 0.015, 0.14, 0.19 + i * 0.034, 0, 0); },
    globe(g, m) { const n = m.s || uni(LAITON, 0.35, 1); cy(g, n, 0.06, 0.012, 0, 0, 0, null, 24); cy(g, n, 0.006, 0.05, 0, 0.012); const p = pivot(g, 0, 0.16, 0, 0, 0, 0.4); tore(p, n, 0.105, 0.005, 0, 0, 0, Math.PI).rotation.z = -Math.PI / 2; sp(p, uni("#2f6ea8", 0.5), 0.092, 0, 0, 0); for (const [a, b, s] of [[0.4, 0.5, 0.05], [2.2, 0.2, 0.06], [3.6, -0.3, 0.045], [5.0, 0.6, 0.04], [1.2, -0.5, 0.035]]) sp(p, uni("#4f8a4a", 0.7), s, Math.cos(a) * Math.cos(b) * 0.066, Math.sin(b) * 0.066, Math.sin(a) * Math.cos(b) * 0.066, 1, 1, 1); },
    sablier(g, m) { const n = m.s || uni(LAITON, 0.35, 1); cy(g, n, 0.045, 0.01, 0, 0, 0, null, 20); cy(g, n, 0.045, 0.01, 0, 0.17, 0, null, 20); for (const a of [0, 2.1, 4.2]) cy(g, n, 0.003, 0.16, Math.cos(a) * 0.038, 0.01, Math.sin(a) * 0.038, null, 5); const v = uni("#dfe9f0", 0.08, 0.2); cy(g, v, 0.034, 0.078, 0, 0.012, 0, 0.005, 18); cy(g, v, 0.005, 0.078, 0, 0.09, 0, 0.034, 18); cy(g, uni(m.c || "#e0b060", 0.9), 0.028, 0.03, 0, 0.014, 0, 0.016, 14); },
    cadre_photo(g, m) { const p = pivot(g, 0, 0, 0, -0.22); bx(p, m.s || uni("#1b1d21", 0.5), 0.17, 0.22, 0.014, 0, 0, 0); bx(p, uni(BLANC, 0.9), 0.14, 0.19, 0.003, 0, 0.015, 0.008); bx(p, uni(m.c || pal.principale, 0.8), 0.1, 0.09, 0.003, 0, 0.08, 0.01); bx(p, uni(pal.accent, 0.8), 0.1, 0.04, 0.003, 0, 0.035, 0.01); const b = bx(g, uni(NOIR, 0.6), 0.02, 0.16, 0.01, 0, 0, -0.05); b.rotation.x = 0.35; },
    tasse(g, m) { const c = uni(m.c || BLANC, 0.35); cy(g, c, 0.036, 0.09, 0, 0, 0, 0.042, 20); cy(g, uni("#2a1a12", 0.4), 0.036, 0.003, 0, 0.088, 0, null, 20); const a = tore(g, c, 0.026, 0.006, 0.05, 0.048, 0, Math.PI); a.rotation.z = -Math.PI / 2; },
    sculpture(g, m) { bx(g, uni(NOIR, 0.4, 0.2), 0.1, 0.04, 0.1, 0, 0); const s = ombres(new THREE.Mesh(garder(new THREE.TorusKnotGeometry(0.07, 0.022, 72, 10)), m.s || uni(m.c || "#d9a941", 0.22, 1.0))); s.position.y = 0.16; g.add(s); },
    tapis(g, m) { bx(g, m.p, 2.0, 0.012, 1.4, 0, 0); },
    colonne(g, m) { cy(g, m.p, 0.2, 0.12, 0, 0, 0, null, 24); cy(g, m.p, 0.15, 3.0, 0, 0.12, 0, null, 24); cy(g, lueur(pal.principale, 1.8), 0.155, 0.03, 0, 1.6, 0, null, 24); },
    arche(g, m) { bx(g, m.p, 0.22, 2.4, 0.22, -1.25, 0); bx(g, m.p, 0.22, 2.4, 0.22, 1.25, 0); bx(g, m.p, 2.72, 0.22, 0.22, 0, 2.4); },
    caisse(g, m) { bx(g, m.p, 0.6, 0.6, 0.6, 0, 0); const n = uni(NOIR, 0.5, 0.5); for (const y of [0.0, 0.57]) for (const z of [-0.29, 0.29]) bx(g, n, 0.62, 0.03, 0.04, 0, y, z); },
    paravent(g, m) { for (let i = -1; i <= 1; i++) { const p = pivot(g, i * 0.56, 0, i === 0 ? 0.06 : -0.06, 0, i * -0.42); bx(p, m.s || uni(NOIR, 0.5, 0.4), 0.6, 1.8, 0.035, 0, 0, 0); bx(p, m.p, 0.52, 1.66, 0.04, 0, 0.07, 0); } },
    estrade(g, m) { const c = m.c || pal.principale; bx(g, m.p, 2.4, 0.18, 1.6, 0, 0); bx(g, lueur(c, 2.2), 2.4, 0.016, 0.008, 0, 0.02, 0.804); const h = halo(g, c, 2.8, 0.7, 0, 0.006, 1.15, 0.5, "bande"); h.rotation.x = Math.PI / 2; },
    imprimante3d(g, m) { const n = uni(NOIR, 0.5, 0.4), c = m.c || "#f0b429"; bx(g, n, 0.4, 0.03, 0.4, 0, 0); for (const x of [-0.18, 0.18]) bx(g, n, 0.03, 0.45, 0.03, x, 0.03, -0.1); bx(g, n, 0.4, 0.03, 0.05, 0, 0.46, -0.1); bx(g, uni(ACIER, 0.3, 0.8), 0.38, 0.015, 0.02, 0, 0.26, -0.1); bx(g, uni(c, 0.5), 0.07, 0.07, 0.07, 0.03, 0.2, -0.07); bx(g, uni("#2b2f36", 0.3, 0.6), 0.26, 0.012, 0.26, 0, 0.05, 0.04); cy(g, uni(c, 0.6), 0.035, 0.09, 0.02, 0.062, 0.04, 0.02); bx(g, lueur(pal.accent, 1.2), 0.08, 0.04, 0.005, -0.12, 0.005, 0.2); },
    bobine(g, m) { const c = cy(g, uni(m.c || pal.principale, 0.5), 0.085, 0.06, 0, 0, 0, null, 28); c.rotation.x = Math.PI / 2; c.position.y = 0.1; for (const z of [-0.035, 0.035]) { const f = cy(g, uni(NOIR, 0.5), 0.1, 0.008, 0, 0, z, null, 28); f.rotation.x = Math.PI / 2; f.position.y = 0.1; } },
    figurine(g, m) { const c = uni(m.c || "#cfd3d8", 0.6); cy(g, uni(NOIR, 0.5), 0.05, 0.012, 0, 0); cy(g, c, 0.035, 0.1, 0, 0.012, 0, 0.028); sp(g, c, 0.033, 0, 0.145, 0); bx(g, c, 0.1, 0.02, 0.02, 0, 0.08); },
    boite_jeu(g, m) { bx(g, uni(m.c || pal.principale, 0.6), 0.3, 0.3, 0.075, 0, 0); bx(g, uni(BLANC, 0.6), 0.22, 0.07, 0.003, 0, 0.19, 0.038); bx(g, uni(NOIR, 0.6), 0.16, 0.09, 0.003, 0, 0.06, 0.038); },
    plateau_jeu(g) { for (let i = 0; i < 6; i++) for (let j = 0; j < 6; j++) bx(g, uni((i + j) % 2 ? "#e9dcc0" : pal.principale, 0.7), 0.1, 0.012, 0.1, (i - 2.5) * 0.1, 0, (j - 2.5) * 0.1); bx(g, uni("#3a2a1e", 0.6), 0.66, 0.008, 0.66, 0, 0); },
    pion(g, m) { const c = uni(m.c || "#e5484d", 0.4); cy(g, c, 0.018, 0.045, 0, 0, 0, 0.006); sp(g, c, 0.014, 0, 0.052, 0); },
    de(g) { bx(g, uni(BLANC, 0.4), 0.035, 0.035, 0.035, 0, 0); sp(g, uni(NOIR), 0.004, 0, 0.036, 0); },
    manette(g, m) { const c = uni(m.c || "#e9ecef", 0.45), n = uni(NOIR, 0.5); bx(g, c, 0.1, 0.03, 0.055, 0, 0.012); for (const s of [-1, 1]) { sp(g, c, 0.034, s * 0.058, 0.026, 0.012, 1, 0.75, 1.35); cy(g, n, 0.009, 0.012, s * 0.028, 0.042, 0.012, null, 10); } for (const [x, z, k] of [[0.05, -0.012, "#e5484d"], [0.064, 0, "#3fb950"], [0.05, 0.012, "#2f81f7"], [0.036, 0, "#f0b429"]]) cy(g, uni(k, 0.4), 0.005, 0.006, x, 0.042, z - 0.012, null, 8); bx(g, n, 0.024, 0.004, 0.008, -0.05, 0.042, -0.012); bx(g, n, 0.008, 0.004, 0.024, -0.05, 0.042, -0.012); },
    borne_arcade(g, m) { const c = m.c || pal.principale, n = m.s || uni(NOIR, 0.5, 0.3); bx(g, n, 0.62, 0.9, 0.62, 0, 0); bx(g, n, 0.62, 0.7, 0.42, 0, 0.9, -0.1); bx(g, lueur(c, 1.7), 0.6, 0.15, 0.1, 0, 1.6, 0.07); bx(g, n, 0.62, 0.04, 0.5, 0, 1.75, -0.06); const p = pivot(g, 0, 0.9, 0.13, -0.5); bx(p, uni("#1c1f25", 0.5), 0.6, 0.03, 0.26, 0, 0, 0.1); cy(p, uni(NOIR, 0.4), 0.007, 0.06, -0.16, 0.03, 0.1, null, 8); sp(p, uni("#e5484d", 0.4), 0.02, -0.16, 0.1, 0.1); for (const [x, k] of [[0.02, "#f0b429"], [0.09, "#3fb950"], [0.16, "#2f81f7"]]) cy(p, uni(k, 0.4), 0.016, 0.012, x, 0.03, 0.1, null, 12); const e = pivot(g, 0, 1.02, 0.115, -0.16); bx(e, lueur(pal.accent, 0.55), 0.5, 0.4, 0.004, 0, 0, 0); for (const x of [-0.312, 0.312]) bx(g, uni(c, 0.5), 0.006, 1.5, 0.05, x, 0.1, 0.22); },
    console_jeu(g, m) { const c = m.c || pal.accent; bx(g, uni("#e9ecef", 0.4), 0.26, 0.05, 0.19, 0, 0); bx(g, uni(NOIR, 0.3, 0.3), 0.262, 0.012, 0.192, 0, 0.019); bx(g, lueur(c, 1.8), 0.1, 0.004, 0.003, -0.06, 0.036, 0.096); },
    casque_vr(g) { const b = uni("#eef0f2", 0.4); bx(g, b, 0.17, 0.09, 0.08, 0, 0.02, 0.03); sp(g, b, 0.05, -0.05, 0.065, 0.065, 1, 0.9, 0.5); sp(g, b, 0.05, 0.05, 0.065, 0.065, 1, 0.9, 0.5); bx(g, uni(NOIR, 0.3, 0.3), 0.16, 0.06, 0.004, 0, 0.035, 0.071); const s = tore(g, uni("#2a2d33", 0.8), 0.085, 0.012, 0, 0.065, -0.02, Math.PI); s.rotation.set(Math.PI / 2, 0, Math.PI); },
    guitare(g, m) { const c = uni(m.c || "#b5651d", 0.35), n = uni("#2a1a12", 0.6); dq(g, c, 0.17, 0.05, 0, -0.3, 0.035, 36); dq(g, c, 0.13, 0.05, 0, -0.1, 0.035, 36); dq(g, n, 0.045, 0.004, 0, -0.17, 0.061, 24); bx(g, n, 0.09, 0.016, 0.01, 0, -0.39, 0.06); bx(g, uni("#3a2618", 0.6), 0.046, 0.52, 0.022, 0, 0, 0.05); bx(g, uni("#3a2618", 0.6), 0.07, 0.13, 0.02, 0, 0.52, 0.045); for (let i = 0; i < 4; i++) bx(g, uni("#d8dade", 0.3, 0.9), 0.0015, 0.9, 0.0015, -0.012 + i * 0.008, -0.38, 0.064); },
    platine(g, m) { bx(g, m.p, 0.42, 0.07, 0.34, 0, 0); cy(g, uni("#b8bcc4", 0.3, 0.9), 0.15, 0.012, -0.04, 0.07, 0, null, 40); cy(g, uni("#0c0c0e", 0.3, 0.2), 0.145, 0.004, -0.04, 0.082, 0, null, 40); cy(g, uni(m.c || pal.principale, 0.6), 0.045, 0.002, -0.04, 0.086, 0, null, 24); cy(g, uni("#b8bcc4", 0.3, 0.9), 0.014, 0.03, 0.16, 0.07, -0.12, null, 12); const b = bx(g, uni("#b8bcc4", 0.3, 0.9), 0.008, 0.008, 0.2, 0.13, 0.095, -0.03); b.rotation.y = 0.3; },
    clap(g) { const n = uni(NOIR, 0.6), b = uni(BLANC, 0.6); bx(g, n, 0.28, 0.19, 0.012, 0, 0); for (const y of [0.05, 0.1]) bx(g, b, 0.26, 0.004, 0.002, 0, y, 0.007); bx(g, b, 0.004, 0.1, 0.002, 0, 0.004, 0.007); bx(g, n, 0.28, 0.035, 0.014, 0, 0.19); const p = pivot(g, -0.14, 0.232, 0, 0, 0, 0.2); bx(p, n, 0.28, 0.035, 0.014, 0.14, 0, 0); for (let i = 0; i < 4; i++) { bx(g, b, 0.035, 0.035, 0.002, -0.105 + i * 0.07, 0.19, 0.008); bx(p, b, 0.035, 0.035, 0.002, 0.035 + i * 0.07, 0, 0.008); } },
    console_scifi(g, m) { bx(g, m.p, 1.9, 0.78, 0.5, 0, 0); const t = bx(g, m.p, 1.9, 0.05, 0.62, 0, 0.8, 0.04); t.rotation.x = -0.22; for (const x of [-0.6, 0, 0.6]) { const e = bx(g, lueur("#18e0ff", 1.2), 0.46, 0.006, 0.3, x, 0.845, 0.06); e.rotation.x = -0.22; } bx(g, lueur("#18e0ff", 2.0), 1.9, 0.02, 0.01, 0, 0.3, 0.255); bx(g, lueur("#ff7a18", 2.0), 1.9, 0.012, 0.01, 0, 0.1, 0.255); },
    hublot(g) { tore(g, uni("#39434f", 0.3, 0.9), 0.46, 0.05, 0, 0, 0.03); const d = cy(g, uni("#02040a", 0.1), 0.44, 0.01, 0, 0, 0.012, null, 40); d.rotation.x = Math.PI / 2; d.position.y = 0; const r = alea(99); for (let i = 0; i < 26; i++) { const a = r() * 6.28, q = Math.sqrt(r()) * 0.4; sp(g, lueur("#dff3ff", 2.5), 0.004 + r() * 0.006, Math.cos(a) * q, Math.sin(a) * q, 0.02); } sp(g, uni("#3b6ea8", 0.8), 0.13, 0.16, -0.1, -0.05); },
    hologramme(g, m) { const c = m.c || "#18e0ff"; cy(g, uni("#2b3542", 0.3, 0.8), 0.32, 0.1, 0, 0, 0, 0.28, 28); cy(g, lueur(c, 2.2), 0.24, 0.012, 0, 0.1, 0, null, 28); const f = garder(new THREE.MeshBasicMaterial({ color: entier(c), wireframe: true, transparent: true, opacity: 0.55, toneMapped: false })); const s = new THREE.Mesh(garder(new THREE.IcosahedronGeometry(0.3, 1)), f); s.position.y = 1.05; s.userData.tourne = 0.4; g.add(s); const k = garder(new THREE.MeshBasicMaterial({ color: entier(c), transparent: true, opacity: 0.1, side: THREE.DoubleSide, depthWrite: false, toneMapped: false })); const cone = new THREE.Mesh(garder(new THREE.CylinderGeometry(0.42, 0.2, 1.3, 24, 1, true)), k); cone.position.y = 0.76; g.add(cone); },
    nuage(g) { const b = uni("#ffffff", 1.0); sp(g, b, 0.28, 0, 0, 0, 1, 0.8, 0.5); sp(g, b, 0.22, -0.3, -0.04, 0, 1, 0.8, 0.5); sp(g, b, 0.2, 0.3, -0.05, 0, 1, 0.8, 0.5); sp(g, b, 0.16, 0.12, 0.14, 0, 1, 0.8, 0.5); },
    arbre_cartoon(g, m) { cy(g, uni("#8a5a3a", 0.9), 0.13, 1.1, 0, 0, 0, 0.09); const v = uni(m.c || "#43c463", 0.9); sp(g, v, 0.62, 0, 1.55, 0); sp(g, v, 0.42, -0.42, 1.3, 0.05); sp(g, v, 0.4, 0.44, 1.35, -0.05); },
    champignon(g, m) { cy(g, uni("#fff3dc", 0.9), 0.09, 0.3, 0, 0, 0, 0.07); const c = sp(g, uni(m.c || "#ff5a5f", 0.8), 0.26, 0, 0.3, 0, 1, 0.62, 1); c.geometry = garder(new THREE.SphereGeometry(0.26, 20, 10, 0, Math.PI * 2, 0, Math.PI / 2)); for (const [x, y, z] of [[0.1, 0.42, 0.14], [-0.14, 0.4, 0.08], [0, 0.455, -0.05], [0.16, 0.39, -0.1]]) sp(g, uni("#ffffff", 0.9), 0.035, x, y, z, 1, 0.5, 1); },
    etoile(g, m) { const f = new THREE.Shape(); for (let i = 0; i < 10; i++) { const a = (i * Math.PI) / 5 + Math.PI / 2, r = i % 2 ? 0.1 : 0.24; if (i) f.lineTo(Math.cos(a) * r, Math.sin(a) * r); else f.moveTo(Math.cos(a) * r, Math.sin(a) * r); } const e = new THREE.Mesh(garder(new THREE.ExtrudeGeometry(f, { depth: 0.04, bevelEnabled: false })), lueur(m.c || "#ffd23f", 1.3)); g.add(e); },
    but_foot(g, m) { const b = m.p; cy(g, b, 0.04, 2.0, -1.5, 0, 0, null, 12); cy(g, b, 0.04, 2.0, 1.5, 0, 0, null, 12); const t = cy(g, b, 0.04, 3.08, 0, 0, 0, null, 12); t.rotation.z = Math.PI / 2; t.position.set(0, 2.0, 0); const f = garder(new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true, transparent: true, opacity: 0.35 })); const filet = new THREE.Mesh(garder(new THREE.BoxGeometry(3.0, 2.0, 0.8, 14, 10, 4)), f); filet.position.set(0, 1.0, -0.42); g.add(filet); },
    ballon_foot(g) { sp(g, uni("#f4f4f4", 0.5), 0.11, 0, 0, 0); for (const [x, y, z] of [[0, 0.11, 0], [0.09, 0.03, 0.05], [-0.08, 0.02, 0.07], [0.02, -0.03, 0.105], [-0.03, 0.06, -0.09]]) sp(g, uni(NOIR, 0.5), 0.034, x * 0.93, y * 0.93, z * 0.93, 1, 1, 1); },
    gradin(g, m) { const r = alea(5), tons = [pal.principale, pal.accent, "#e9edf2", "#1c2c4a"]; for (let i = 0; i < 4; i++) { bx(g, m.p, 8.4, 0.32 * (i + 1), 0.45, 0, 0, 0.68 - i * 0.45); for (let k = 0; k < 28; k++) bx(g, uni(tons[(r() * tons.length) | 0], 0.7), 0.22, 0.26, 0.06, (k - 13.5) * 0.29, 0.32 * (i + 1), 0.52 - i * 0.45); } },
    tableau_tactique(g) { const n = uni(NOIR, 0.4, 0.4); for (const x of [-0.4, 0.4]) bx(g, n, 0.03, 1.7, 0.03, x, 0, -0.1).rotation.x = -0.12; bx(g, uni("#2f8a3a", 0.8), 1.0, 0.68, 0.02, 0, 0.9, 0); const b = uni(BLANC, 0.7); bx(g, b, 0.92, 0.006, 0.004, 0, 0.94, 0.012); bx(g, b, 0.92, 0.006, 0.004, 0, 1.53, 0.012); bx(g, b, 0.006, 0.6, 0.004, 0, 0.94, 0.012); bx(g, b, 0.006, 0.6, 0.004, -0.46, 0.94, 0.012); bx(g, b, 0.006, 0.6, 0.004, 0.46, 0.94, 0.012); tore(g, b, 0.09, 0.004, 0, 1.24, 0.012); for (const [x, y, c] of [[-0.25, 1.1, "#e5484d"], [-0.15, 1.38, "#e5484d"], [0.2, 1.2, "#f0b429"], [0.3, 1.42, "#f0b429"]]) sp(g, uni(c, 0.5), 0.022, x, y, 0.014, 1, 1, 0.3); },
    fanion(g, m) { cy(g, uni(BLANC, 0.5), 0.015, 2.2, 0, 0); const d = bx(g, uni(m.c || pal.principale, 0.8), 0.6, 0.4, 0.008, 0.31, 1.78, 0); d.material.side = THREE.DoubleSide; },
    maillot(g, m) { const c = uni(m.c || pal.principale, 0.9); bx(g, c, 0.46, 0.6, 0.03, 0, -0.3, 0.015); for (const s of [-1, 1]) { const a = bx(g, c, 0.2, 0.26, 0.03, s * 0.3, 0.02, 0.015); a.rotation.z = s * 0.5; } bx(g, uni(BLANC, 0.9), 0.14, 0.2, 0.004, 0, -0.14, 0.032); bx(g, uni(BLANC, 0.9), 0.2, 0.03, 0.004, 0, 0.27, 0.032); },
    echarpe(g, m) { const c = m.c || pal.principale, a = uni(c, 0.95), b = uni(pal.accent === c ? BLANC : pal.accent, 0.95); bx(g, a, 1.3, 0.17, 0.012, 0, -0.085, 0.006); bx(g, uni(BLANC, 0.95), 1.3, 0.03, 0.002, 0, -0.015, 0.013); for (const s of [-1, 1]) { bx(g, b, 0.14, 0.17, 0.002, s * 0.52, -0.085, 0.013); for (let i = 0; i < 8; i++) bx(g, a, 0.006, 0.05, 0.004, s * 0.655, -0.08 + i * 0.02 - 0.003, 0.006).rotation.z = Math.PI / 2; } },
    crampons(g, m) { const c = uni(m.c || pal.principale, 0.4), n = uni(NOIR, 0.5); for (const s of [-1, 1]) { const x = s * 0.07; bx(g, n, 0.085, 0.014, 0.27, x, 0.014, 0); sp(g, c, 0.05, x, 0.06, 0.045, 0.85, 0.7, 1.9); sp(g, c, 0.05, x, 0.075, -0.07, 0.85, 1.0, 1.0); bx(g, uni(BLANC, 0.5), 0.03, 0.004, 0.09, x, 0.092, 0.05); for (const z of [-0.1, -0.03, 0.06, 0.11]) cy(g, uni(ACIER, 0.3, 0.9), 0.007, 0.014, x, 0, z, 0.01, 8); } },
    plot(g, m) { const c = uni(m.c || "#ff6a1a", 0.6); bx(g, c, 0.2, 0.012, 0.2, 0, 0); cy(g, c, 0.085, 0.24, 0, 0.012, 0, 0.018, 20); cy(g, uni(BLANC, 0.6), 0.058, 0.04, 0, 0.1, 0, 0.046, 20); },
    panier_basket(g) { const n = uni(NOIR, 0.4, 0.5); cy(g, n, 0.05, 2.6, 0, 0, -0.5); bx(g, n, 0.05, 0.05, 0.5, 0, 2.5, -0.25); bx(g, uni(BLANC, 0.3), 0.95, 0.62, 0.03, 0, 2.2, 0); bx(g, uni("#e5484d", 0.5), 0.3, 0.22, 0.004, 0, 2.3, 0.018); const t = tore(g, uni("#f26a1b", 0.4, 0.3), 0.2, 0.012, 0, 2.3, 0.23); t.rotation.x = Math.PI / 2; const f = garder(new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true, transparent: true, opacity: 0.5 })); const filet = new THREE.Mesh(garder(new THREE.CylinderGeometry(0.2, 0.12, 0.3, 12, 4, true)), f); filet.position.set(0, 2.15, 0.23); g.add(filet); },
    ballon_basket(g) { sp(g, uni("#e2701e", 0.7), 0.12, 0, 0, 0); tore(g, uni(NOIR), 0.121, 0.004, 0, 0, 0); tore(g, uni(NOIR), 0.121, 0.004, 0, 0, 0).rotation.y = Math.PI / 2; },
    ballon_ovale(g) { sp(g, uni("#7a4320", 0.7), 0.09, 0, 0.09, 0, 1.65, 1, 1); bx(g, uni(BLANC), 0.1, 0.006, 0.012, 0, 0.176, 0); },
    batte(g) { const b = cy(g, uni("#c9a36a", 0.5), 0.016, 0.86, 0, 0, 0, 0.032, 12); b.rotation.z = -0.18; b.position.x = 0.08; },
    casque_foot_us(g, m) { const c = uni(m.c || pal.principale, 0.25, 0.2), a = uni(ACIER, 0.3, 0.9); bx(g, uni(NOIR, 0.4), 0.2, 0.02, 0.2, 0, 0); sp(g, c, 0.125, 0, 0.14, 0, 1, 1, 1.12); const r = tore(g, uni(BLANC, 0.4), 0.131, 0.012, 0, 0.14, 0, Math.PI); r.rotation.y = Math.PI / 2; r.scale.set(1.12, 1, 1); for (const y of [0.1, 0.06]) { const t = tore(g, a, 0.11, 0.006, 0, y, 0.06, Math.PI); t.rotation.set(Math.PI / 2, 0, 0); } bx(g, a, 0.008, 0.07, 0.008, 0, 0.045, 0.168); },
    raquette(g, m) { const c = uni(m.c || pal.principale, 0.4, 0.3), f = uni(BLANC, 0.6); const t = tore(g, c, 0.11, 0.008, 0, 0.2, 0.012); t.scale.set(1, 1.28, 1); for (let i = -3; i <= 3; i++) { bx(g, f, 0.0015, 0.26 - Math.abs(i) * 0.02, 0.0015, i * 0.027, 0.07 + Math.abs(i) * 0.01, 0.012); bx(g, f, 0.2 - Math.abs(i) * 0.02, 0.0015, 0.0015, 0, 0.2 + i * 0.035, 0.012); } for (const s of [-1, 1]) { const b = bx(g, c, 0.008, 0.13, 0.008, s * 0.03, -0.04, 0.012); b.rotation.z = s * 0.3; } bx(g, uni(NOIR, 0.8), 0.03, 0.24, 0.022, 0, -0.28, 0.012); },
    balle_tennis(g) { sp(g, uni("#c8e03a", 0.9), 0.033, 0, 0.033, 0); const t = tore(g, uni(BLANC, 0.8), 0.0325, 0.002, 0, 0.033, 0); t.rotation.set(0.6, 0.4, 0); },
    haltere(g, m) { const n = m.s || uni(NOIR, 0.6, 0.3), a = uni(ACIER, 0.3, 0.9); const b = cy(g, a, 0.012, 0.32, 0, 0, 0, null, 10); b.rotation.z = Math.PI / 2; b.position.set(0, 0.065, 0); for (const x of [-0.13, -0.08, 0.08, 0.13]) { const d = cy(g, n, 0.065, 0.04, 0, 0, 0, null, 24); d.rotation.z = Math.PI / 2; d.position.set(x, 0.065, 0); } },
    gant_boxe(g, m) { const c = uni(m.c || "#c0162c", 0.35); sp(g, c, 0.085, 0, 0.17, 0.01, 1, 1.15, 1.05); sp(g, c, 0.04, 0.075, 0.15, 0.03, 1, 1.4, 1); cy(g, c, 0.06, 0.08, 0, 0, 0, 0.066, 18); cy(g, uni(BLANC, 0.6), 0.062, 0.02, 0, 0.03, 0, 0.064, 18); },
    skateboard(g, m) { const c = uni(m.c || pal.principale, 0.5); bx(g, c, 0.2, 0.6, 0.012, 0, -0.3, 0.02); dq(g, c, 0.1, 0.012, 0, 0.3, 0.02, 28); dq(g, c, 0.1, 0.012, 0, -0.3, 0.02, 28); bx(g, uni(pal.accent, 0.5), 0.2, 0.08, 0.002, 0, 0.05, 0.027); bx(g, uni(BLANC, 0.5), 0.2, 0.02, 0.002, 0, -0.03, 0.027); for (const y of [-0.24, 0.24]) { bx(g, uni(ACIER, 0.3, 0.9), 0.14, 0.03, 0.02, 0, y - 0.015, 0.036); for (const x of [-0.085, 0.085]) { const w = cy(g, uni("#f1ede4", 0.6), 0.026, 0.03, 0, 0, 0, null, 14); w.rotation.z = Math.PI / 2; w.position.set(x, y, 0.05); } } },
    modele(g, m) {
      const F = OBJETS[m.ref], attente = bx(g, garder(new THREE.MeshBasicMaterial({ color: 0x8a94a0, wireframe: true })), 0.5, 0.5, 0.5, 0, 0, 0);
      if (!F || !(O.chargeur && O.chargeur.classe)) return;
      const g0 = generation;
      modeleDe(F).then((src) => {
        if (!src || g0 !== generation || detruit) return;
        const c = src.clone(true);
        c.traverse((x) => { if (x.isMesh) { ombres(x); if (m.forcer) x.material = m.p; } });
        g.remove(attente); g.add(c); g.userData.boite = boiteLocale(g);
        marquer(); if (O.surChange) O.surChange();
      });
    },
    tableau(g, m) { const [l, h] = formatImage(m.image), mat = garder(new THREE.MeshStandardMaterial({ color: 0x8a94a0, roughness: 0.85 })); bx(g, m.s || uni("#1b1d21", 0.5), l + 0.06, h + 0.06, 0.03, 0, -(h + 0.06) / 2, 0.015); plan(g, mat, l, h, 0, 0, 0.0315); poserImage(mat, m.image, true); },
    logo_mural(g, m) { const [l, h] = formatImage(m.image), mat = garder(new THREE.MeshBasicMaterial({ color: 0x8a94a0, transparent: true, alphaTest: 0.02, toneMapped: false })); if (m.c) halo(g, m.c, l * 1.8, h * 1.8, 0, 0, 0.004, 0.45); const p = plan(g, mat, l, h, 0, 0, 0.03); p.renderOrder = 4; poserImage(mat, m.image, false); },
    kakemono(g, m) { const n = m.s || uni(ACIER, 0.35, 0.8), mat = garder(new THREE.MeshStandardMaterial({ color: 0x8a94a0, roughness: 0.8, side: THREE.DoubleSide })); bx(g, n, 0.86, 0.03, 0.3, 0, 0, 0); cy(g, n, 0.012, 2.06, 0, 0.03, -0.03, null, 8); bx(g, n, 0.84, 0.03, 0.03, 0, 2.06, 0); plan(g, mat, 0.8, 2.0, 0, 1.05, 0); poserImage(mat, m.image, true, [0.8, 2.0]); },
    trophee(g, m) { const o = uni(m.c || "#f0c040", 0.25, 1.0); bx(g, uni(NOIR, 0.4), 0.14, 0.05, 0.14, 0, 0); cy(g, o, 0.02, 0.1, 0, 0.05); cy(g, o, 0.035, 0.14, 0, 0.15, 0, 0.085); tore(g, o, 0.05, 0.008, -0.1, 0.23, 0); tore(g, o, 0.05, 0.008, 0.1, 0.23, 0); },
    coupe(g, m) { const o = uni(m.c || "#e9c04a", 0.32, 0.9); bx(g, uni("#2a1a12", 0.5), 0.2, 0.07, 0.2, 0, 0); bx(g, uni(LAITON, 0.35, 1), 0.12, 0.03, 0.003, 0, 0.02, 0.1); cy(g, o, 0.06, 0.03, 0, 0.07, 0, 0.03, 24); cy(g, o, 0.022, 0.12, 0, 0.1, 0, null, 16); sp(g, o, 0.03, 0, 0.16, 0); cy(g, o, 0.035, 0.22, 0, 0.22, 0, 0.14, 28); cy(g, o, 0.145, 0.015, 0, 0.44, 0, null, 28); for (const s of [-1, 1]) { const t = tore(g, o, 0.075, 0.01, s * 0.14, 0.34, 0, Math.PI); t.rotation.z = s > 0 ? -Math.PI / 2 : Math.PI / 2; } },
    medaille(g, m) { const c = uni(m.c || pal.principale, 0.9); for (const s of [-1, 1]) { const b = bx(g, c, 0.035, 0.26, 0.004, s * 0.045, -0.13, 0.004); b.rotation.z = s * 0.34; } dq(g, uni("#e9c04a", 0.22, 1.0), 0.055, 0.008, 0, -0.17, 0.008, 32); dq(g, uni("#b8923a", 0.3, 1.0), 0.038, 0.01, 0, -0.17, 0.009, 32); },
    plaque_createur(g, m) { const o = uni(m.c || "#cfd4da", 0.18, 1.0); bx(g, uni("#17181c", 0.5), 0.32, 0.42, 0.03, 0, -0.21, 0.015); bx(g, uni("#0c0c0e", 0.8), 0.27, 0.37, 0.004, 0, -0.185, 0.031); bx(g, o, 0.2, 0.14, 0.014, 0, -0.03, 0.04); const f = new THREE.Shape(); f.moveTo(-0.022, -0.03); f.lineTo(0.034, 0); f.lineTo(-0.022, 0.03); f.closePath(); const t = new THREE.Mesh(garder(new THREE.ExtrudeGeometry(f, { depth: 0.006, bevelEnabled: false })), uni("#17181c", 0.4, 0.4)); t.position.set(0, 0.04, 0.054); g.add(t); bx(g, o, 0.16, 0.012, 0.004, 0, -0.1, 0.034); bx(g, o, 0.1, 0.008, 0.004, 0, -0.125, 0.034); },
  };

  // ── les modèles importés : chargés une fois, posés au sol (centrés, la base à y = 0), clonés à chaque emploi ──
  const modeles = new Map();
  function modeleDe(F) {
    if (!modeles.has(F.ref)) modeles.set(F.ref, new Promise((res) => {
      try {
        new O.chargeur.classe().load(F.modele, (gltf) => {
          const sc = gltf.scene, b = new THREE.Box3().setFromObject(sc), c = b.getCenter(new THREE.Vector3()), pose = new THREE.Group();
          sc.position.set(-c.x, -b.min.y, -c.z); pose.add(sc); res(pose);
        }, undefined, () => res(null));
      } catch (e) { res(null); }
    }));
    return modeles.get(F.ref);
  }
  // la boîte d'un groupe dans SON repère (sans sa place, son tour ni sa taille), halos exclus
  function boiteLocale(g) {
    const b = new THREE.Box3(), inv = new THREE.Matrix4(), m4 = new THREE.Matrix4();
    g.updateWorldMatrix(true, true); inv.copy(g.matrixWorld).invert();
    g.traverse((x) => {
      if (!x.isMesh || x.userData.halo || !x.geometry) return;
      if (!x.geometry.boundingBox) x.geometry.computeBoundingBox();
      b.union(x.geometry.boundingBox.clone().applyMatrix4(m4.multiplyMatrices(inv, x.matrixWorld)));
    });
    return b.isEmpty() ? null : b;
  }

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
  // l'enseigne : `couche` = "face" (ce qu'on lit) ou "halo" (la lueur seule, pour le rétroéclairage)
  function peindreEnseigne(x, l, h, e, couche) {
    const large = e.source === "texte" && e.texte, c = couleur(e.couleur, pal), halo2 = couche === "halo";
    const LG = e.source === "image" ? imgPretes.get((IMAGES[e.image] || {}).url) : O.logo;       // l'image choisie, sinon le logo de l'espace
    x.clearRect(0, 0, l, h); x.shadowBlur = 0;
    if (!halo2 && (e.style === "panneau" || e.style === "ecran" || e.style === "caisson")) {
      x.fillStyle = e.style === "ecran" ? "#05070b" : e.style === "caisson" ? melange(c, "#ffffff", 0.82) : "#f4f1ea"; x.fillRect(0, 0, l, h);
      if (e.style !== "caisson") { x.strokeStyle = c; x.lineWidth = l / 40; x.strokeRect(l / 80, l / 80, l - l / 40, h - l / 40); }
    }
    const marge = h * 0.14, neon = e.style === "neon", lueurs = halo2 ? [h * 0.3, h * 0.18, h * 0.09] : neon ? [h * 0.16, h * 0.07] : [];
    if (large) {
      let px = Math.round(h * 0.5); x.font = fonte(e.police, px);
      const w = x.measureText(e.texte).width; if (w > l - 2 * marge) { px = Math.max(10, Math.floor((px * (l - 2 * marge)) / w)); x.font = fonte(e.police, px); }
      x.textAlign = "center"; x.textBaseline = "middle";
      x.shadowColor = c; x.fillStyle = c;
      for (const b of lueurs) { x.shadowBlur = b; x.fillText(e.texte, l / 2, h / 2); }
      x.shadowBlur = 0;
      if (!halo2) { x.fillStyle = neon ? melange(c, "#ffffff", 0.78) : e.style === "retro" ? "#f2f3f5" : e.style === "caisson" ? "#15171c" : c; x.fillText(e.texte, l / 2, h / 2); }
    } else if (LG && (LG.naturalWidth || LG.width)) {
      const w = LG.naturalWidth || LG.width, hh = LG.naturalHeight || LG.height, k = Math.min((l - 2 * marge) / w, (h - 2 * marge) / hh);
      const poser = () => x.drawImage(LG, (l - w * k) / 2, (h - hh * k) / 2, w * k, hh * k);
      x.shadowColor = c; for (const b of lueurs) { x.shadowBlur = b; poser(); }
      x.shadowBlur = 0; if (!halo2) poser();
    } else {                                     // ni texte ni logo : un anneau à la couleur de l'espace
      x.strokeStyle = neon ? "#ffffff" : c; x.lineWidth = h * 0.06; x.shadowColor = c;
      const tracer = () => { x.beginPath(); x.arc(l / 2, h / 2, h * 0.28, 0, Math.PI * 2); x.stroke(); };
      for (const b of lueurs) { x.shadowBlur = b; tracer(); }
      x.shadowBlur = 0; if (!halo2) tracer();
    }
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

  // ── les reflets : une petite pièce lumineuse rendue une fois (PMREM) ; les métaux, les laques et les sols cirés y
  // trouvent quoi refléter. Refaite seulement quand les lumières ou les murs changent. ──
  let refletCle = "", refletCible = null;
  function reflets(d) {
    const P = d.piece, mur = d.matieres[P.fond || P.mur] || {}, T = mur.texture && INDEX[mur.texture];
    const teinteMur = (T && !mur.teinte && T.moyenne) || couleur(mur.couleur, pal, "#2a2f36");
    const sol = d.matieres[P.sol] || {}, Ts = sol.texture && INDEX[sol.texture];
    const teinteSol = (Ts && !sol.teinte && Ts.moyenne) || couleur(sol.couleur, pal, "#3a3f47");
    const cle = JSON.stringify([teinteMur, teinteSol, pal.principale, pal.accent, P.l, P.p, P.h, d.lumieres.map((l) => [l.type, l.couleur, l.intensite, l.x, l.y, l.z, l.l])]);
    if (cle === refletCle && refletCible) return;
    const env = new THREE.Scene(), tmp = [];
    const boite = (hex, force, l, h, p, x, y, z, dedans) => {
      const geo = new THREE.BoxGeometry(l, h, p), mat = new THREE.MeshBasicMaterial({ color: new THREE.Color(entier(hex)).multiplyScalar(force), side: dedans ? THREE.BackSide : THREE.FrontSide });
      const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); env.add(m); tmp.push(geo, mat);
    };
    boite(melange(teinteMur, "#8a8f98", 0.25), 0.8, P.l + 4, P.h, P.p + 6, 0, P.h / 2, 2, true);
    boite(melange(teinteSol, "#8a8f98", 0.25), 0.9, P.l + 3.9, 0.04, P.p + 5.9, 0, 0.03, 2);
    boite("#fff6ea", 1.6, 2.4, 0.04, 1.6, 0, P.h - 0.06, 1.6);
    for (const l of d.lumieres) {
      const c = couleur(l.couleur, pal, "#ffffff");
      if (l.type === "ambiance") boite(c, 0.6 * l.intensite, P.l, 0.05, P.p, 0, P.h - 0.1, 0);
      else if (l.type === "neon") boite(c, 4.5, l.l, 0.12, 0.12, l.x, l.y, l.z);
      else boite(c, 2.2 * l.intensite, l.type === "fenetre" ? l.l : 1.0, l.type === "fenetre" ? l.h : 0.7, 0.1, l.x, l.y, l.z);
    }
    const pm = new THREE.PMREMGenerator(rendu), cible = pm.fromScene(env, 0.03);
    pm.dispose(); for (const x of tmp) x.dispose();
    if (refletCible) refletCible.dispose();
    refletCible = cible; refletCle = cle;
    scene.environment = cible.texture;
    if ("environmentIntensity" in scene) scene.environmentIntensity = 0.45;
  }

  // ── construction ──
  function vider() {
    generation++;
    if (racine) scene.remove(racine);
    for (const x of jetables.splice(0)) { try { x.dispose(); } catch (e) { /* déjà libéré */ } }
    cache = new Map(); texEcrans = []; perso = null; texVideo = null; videoVue = null; racine = null; aRepeindre = [];
    groupes = []; pans = {}; outils = null; reperes = { lumiere: [], camera: [], ecran: [], enseigne: [] }; marque = null;
    if (gpu.size > 40) for (const [id, t] of gpu) if (t.userData.vue < generation - 1) { t.dispose(); gpu.delete(id); }
  }
  function construire(d) {
    vider();
    decor = d; pal = palette(O.contexte); reg = regie(d.cameras.length);
    racine = new THREE.Group();
    const P = d.piece, A = d.ambiance;
    scene.background = new THREE.Color(entier(couleur(A.fond, pal, "#0b0f14")));
    scene.fog = A.brouillard > 0 ? new THREE.FogExp2(scene.background.getHex(), A.brouillard) : null;
    rendu.toneMappingExposure = A.exposition;
    try { reflets(d); } catch (e) { scene.environment = null; }
    // la pièce : sol prolongé vers la caméra, mur du fond, murs de côté et plafond (sauf pièce ouverte)
    const av = 5;                                   // mètres de sol et de murs devant la pièce (côté caméra)
    const pan = (nom, m) => { m.userData.cible = { genre: "surface", pan: nom }; pans[nom] = m; return m; };
    const sol = pan("sol", plan(racine, matiere(P.sol), P.l + 4, P.p + av, 0, 0, av / 2));
    sol.rotation.x = -Math.PI / 2; sol.receiveShadow = qualite === "haute";
    pan("fond", plan(racine, matiere(P.fond || P.mur), P.l + 4, P.h, 0, P.h / 2, -P.p / 2));
    if (!P.ouvert) {
      pan("gauche", plan(racine, matiere(P.gauche || P.mur), P.p + av, P.h, -P.l / 2, P.h / 2, av / 2)).rotation.y = Math.PI / 2;
      pan("droite", plan(racine, matiere(P.droite || P.mur), P.p + av, P.h, P.l / 2, P.h / 2, av / 2)).rotation.y = -Math.PI / 2;
      pan("plafond", plan(racine, matiere(P.plafond), P.l, P.p + av, 0, P.h, av / 2)).rotation.x = Math.PI / 2;
    }
    if (P.plinthe && !P.ouvert) bx(racine, uni("#0e0f12", 0.6), P.l, 0.08, 0.02, 0, 0, -P.p / 2 + 0.01);
    // les objets
    d.objets.forEach((ob, i) => {
      const f = B[ob.type], g = new THREE.Group(), c = ob.couleur ? couleur(ob.couleur, pal) : null;
      groupes[i] = g; g.userData.cible = { genre: "objet", index: i };
      if (!f) return;
      f(g, { p: ob.matiere ? matiere(ob.matiere, c) : uni(c || "#3a3f47", 0.6), s: ob.matiere2 ? matiere(ob.matiere2) : null, c,
        t: (ob.texte || "").trim(), f: ob.police || "Inter", ref: ob.ref, forcer: !!ob.matiere, image: ob.image });
      g.userData.boite = boiteLocale(g);                     // l'emprise de l'objet, avant sa place et sa taille
      g.position.set(ob.x, ob.y, ob.z); g.rotation.y = (ob.ry * Math.PI) / 180; g.scale.setScalar(ob.e);
      racine.add(g);
    });
    // les outils de l'atelier : un repère par lumière et par caméra, visibles (et cliquables) en vue libre seulement
    outils = new THREE.Group(); outils.visible = !!libre; racine.add(outils);
    const repere = (genre, index, objet) => { objet.userData.cible = { genre, index }; reperes[genre][index] = objet; return objet; };
    d.cameras.forEach((cm, i) => {
      const g = repere("camera", i, new THREE.Group()), noir = garder(new THREE.MeshBasicMaterial({ color: 0x1b1d21 })), clair = garder(new THREE.MeshBasicMaterial({ color: 0xf0b429, toneMapped: false }));
      const corps = new THREE.Mesh(garder(new THREE.BoxGeometry(0.14, 0.1, 0.18)), noir); g.add(corps);
      const geo = garder(new THREE.ConeGeometry(0.09, 0.14, 4)); geo.rotateX(-Math.PI / 2); geo.rotateZ(Math.PI / 4);
      const cone = new THREE.Mesh(geo, clair); cone.position.z = 0.15; g.add(cone);
      g.position.set(cm.x, cm.y, cm.z); g.lookAt(cm.vers[0], cm.vers[1], cm.vers[2]); outils.add(g);
    });
    // les lumières
    const allumees = budgetLumieres(d.lumieres, qualite);
    racine.add(new THREE.AmbientLight(0xffffff, 0.12));
    let ombrePosee = false;
    d.lumieres.forEach((l, i) => {
      const hex = couleur(l.couleur, pal, "#ffffff"), c = entier(hex);
      if (l.type !== "ambiance" && l.type !== "neon") {
        const g = repere("lumiere", i, new THREE.Group());
        g.add(new THREE.Mesh(garder(new THREE.SphereGeometry(0.075, 14, 10)), garder(new THREE.MeshBasicMaterial({ color: c, toneMapped: false }))));
        const trait = garder(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(l.vers[0] - l.x, l.vers[1] - l.y, l.vers[2] - l.z)]));
        const ligne = new THREE.Line(trait, garder(new THREE.LineBasicMaterial({ color: c, transparent: true, opacity: 0.55 }))); ligne.userData.halo = true; g.add(ligne);
        g.position.set(l.x, l.y, l.z); outils.add(g);
      }
      if (l.type === "ambiance") { racine.add(new THREE.HemisphereLight(c, entier(couleur(decor.matieres[P.sol].couleur, pal, "#333333")), l.intensite * K_AMBIANCE)); return; }
      if (l.type === "neon") {
        const g = new THREE.Group(), t = cy(g, lueur(hex, 2.6), 0.022, l.l, 0, -l.l / 2, 0, null, 10);
        t.rotation.x = Math.PI / 2; t.position.y = 0; t.castShadow = false;
        // la lueur du tube sur ce qui l'entoure : deux plans croisés le long du tube (mur et sol), vus selon l'angle
        const f = Math.min(0.55, 0.14 * l.intensite), a = halo(g, hex, 0.6, l.l * 1.25, 0, 0, 0, f), b = halo(g, hex, 0.6, l.l * 1.25, 0, 0, 0, f);
        a.rotation.set(Math.PI / 2, Math.PI / 2, 0); b.rotation.x = Math.PI / 2;
        g.position.set(l.x, l.y, l.z); g.rotation.y = (l.ry * Math.PI) / 180; racine.add(g);
        repere("lumiere", i, g);
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
    d.ecrans.forEach((e, i) => {
      const g = repere("ecran", i, new THREE.Group());
      bx(g, uni(couleur(e.bord, pal, "#0c0d10"), 0.4, 0.3), e.l + 0.08, e.h + 0.08, 0.05, 0, -(e.h + 0.08) / 2, 0.025);
      const tex = texture(attente(e.source)), mat = garder(new THREE.MeshBasicMaterial({ map: tex, toneMapped: false }));
      plan(g, mat, e.l, e.h, 0, 0, 0.052);
      if (e.source !== "eteint") halo(g, pal.principale, e.l * 1.5, e.h * 1.7, 0, 0, 0.003, 0.14);
      if (e.source === "ecran") texEcrans.push({ mat, attente: tex, vive: null });
      if (e.source === "image") poserImage(mat, e.image, false, [e.l, e.h]);       // une image de la Bibliothèque, qui couvre la dalle
      g.position.set(e.x, e.y, e.z); g.rotation.y = (e.ry * Math.PI) / 180; racine.add(g);
    });
    // l'enseigne : néon (tube clair et lueur), panneau, écran, rétroéclairée (lueur sur le mur, face détachée),
    // caisson lumineux
    const E = d.enseigne;
    if (E.actif) {
      const g = repere("enseigne", 0, new THREE.Group()), large = E.source === "texte" && E.texte, h = large ? E.l / 4 : E.l, hexE = couleur(E.couleur, pal);
      const tl = large ? 1024 : 512, th = large ? 256 : 512;
      const urlE = E.source === "image" && IMAGES[E.image] ? IMAGES[E.image].url : null;
      const couche = (nom) => { const c = toile(tl, th, () => {}), x = c.getContext("2d"), peindre = () => peindreEnseigne(x, tl, th, E, nom); peindre(); const tex = texture(c); aRepeindre.push({ police: E.police, peindre, tex, image: urlE }); return tex; };
      if (urlE && !imgPretes.has(urlE)) { const g0 = generation; image(urlE).then((im) => { if (!im || detruit) return; imgPretes.set(urlE, im); if (g0 === generation) for (const r of aRepeindre) if (r.image === urlE) { r.peindre(); r.tex.needsUpdate = true; } }); }
      if (large) police(E.police);
      const plein = E.style === "panneau" || E.style === "ecran" || E.style === "caisson";
      if (E.style === "retro") { const hl = plan(g, garder(new THREE.MeshBasicMaterial({ map: couche("halo"), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false })), E.l * 1.12, h * 1.12, 0, 0, 0.004); hl.renderOrder = 3; halo(g, hexE, E.l * 1.9, h * 1.9, 0, 0, 0.003, 0.22); }
      if (E.style === "caisson") halo(g, hexE, E.l * 1.8, h * 1.8, 0, 0, 0.003, 0.25);
      if (E.style === "neon") halo(g, hexE, E.l * 1.6, h * 1.6, 0, 0, 0.003, 0.3);
      const mat = garder(new THREE.MeshBasicMaterial({ map: couche("face"), transparent: !plein, toneMapped: false, depthWrite: plein, alphaTest: plein ? 0 : 0.02 }));
      if (plein) bx(g, uni("#101216", 0.5), E.l + 0.04, h + 0.04, E.style === "caisson" ? 0.07 : 0.03, 0, -(h + 0.04) / 2, E.style === "caisson" ? 0.035 : 0.015);
      const face = plan(g, mat, E.l, h, 0, 0, E.style === "caisson" ? 0.072 : E.style === "retro" ? 0.05 : plein ? 0.032 : 0.03); face.renderOrder = 4;
      g.position.set(E.x, E.y, E.z); g.rotation.y = (E.ry * Math.PI) / 180; racine.add(g);
      if (E.style === "neon" || E.style === "retro" || E.style === "caisson") { const p = new THREE.PointLight(entier(hexE), 1.6, 4, 2); p.position.set(E.x, E.y, E.z + 0.3); racine.add(p); }
    }
    // le présentateur : silhouette en aperçu ; vidéo incrustée en mode fond vert (posée par `rendre`)
    // le plan du présentateur : un buste (0,95 m) pour qui est assis, la personne jusqu'au sol pour qui est debout
    const R = d.presentateur, hp = R.assis ? 0.95 : R.h + 0.08, lp = R.assis ? hp * 0.75 : hp * 0.42;
    perso = new THREE.Group(); perso.position.set(R.x, 0, R.z); perso.visible = false; perso.userData.ignorer = true; racine.add(perso);
    perso.userData = { h: R.h, hp, lp };
    const contre = d.lumieres.find((l) => l.type === "contre");
    perso.userData.teinte = contre ? couleur(contre.couleur, pal, "#ffffff") : "#ffffff";
    const corps = plan(perso, matierePresentateur(texture(silhouette()), false, R.teinte, perso.userData.teinte), lp, hp, 0, R.h + 0.08 - hp / 2, 0);
    corps.name = "corps"; corps.renderOrder = 5;
    if (R.ombre) { const so = plan(perso, garder(new THREE.MeshBasicMaterial({ map: texture(ombreSol()), transparent: true, depthWrite: false })), 1.1, 0.7, 0, 0.012, 0); so.rotation.x = -Math.PI / 2; }
    perso.visible = !!O.apercu;
    scene.add(racine);
    marquer();
  }

  // ── l'atelier : vue libre, pointeur, choix ──
  let groupes = [], pans = {}, outils = null, reperes = { lumiere: [], camera: [], ecran: [], enseigne: [] }, marque = null;
  let libre = null, selection = null;
  const rayon = new THREE.Raycaster(); rayon.params.Line = { threshold: 0.03 };
  const point = new THREE.Vector2();
  function vueLibre(oui) {
    if (!oui) { libre = null; if (outils) outils.visible = false; return; }
    if (!libre) {
      const p = reg.pose(decor.cameras, performance.now()), dx = p.x - p.vers[0], dy = p.y - p.vers[1], dz = p.z - p.vers[2], d = Math.hypot(dx, dy, dz) || 3;
      libre = { cible: new THREE.Vector3(p.vers[0], p.vers[1], p.vers[2]), d: borne(d * 1.35, 1.5, 25), az: Math.atan2(dx, dz), el: borne(Math.asin(dy / d) + 0.25, -0.1, 1.5), champ: 45 };
    }
    if (outils) outils.visible = true;
  }
  const orbiter = (dAz, dEl) => { if (libre) { libre.az -= dAz; libre.el = borne(libre.el + dEl, -0.1, 1.52); } };
  const zoomer = (k) => { if (libre) libre.d = borne(libre.d * k, 0.6, 30); };
  function glisser(dx, dy) {                       // déplace le point visé, à plat (dx : vers la droite de l'œil ; dy : vers le fond)
    if (!libre) return;
    const ca = Math.cos(libre.az), sa = Math.sin(libre.az), k = libre.d * 0.0016;
    libre.cible.x = borne(libre.cible.x - (dx * ca + dy * sa) * k, -10, 10);
    libre.cible.z = borne(libre.cible.z + (dx * sa - dy * ca) * k, -10, 12);
  }
  function oeilLibre() {
    const c = Math.cos(libre.el);
    return { x: libre.cible.x + libre.d * c * Math.sin(libre.az), y: libre.cible.y + libre.d * Math.sin(libre.el), z: libre.cible.z + libre.d * c * Math.cos(libre.az) };
  }
  // la vue libre, dite comme une caméra de la recette (« garder cette vue comme caméra »)
  function poseLibre() {
    if (!libre) return null;
    const o = oeilLibre(), r = (v) => Math.round(v * 100) / 100;
    return { x: r(o.x), y: r(Math.max(0.2, o.y)), z: r(o.z), vers: [r(libre.cible.x), r(libre.cible.y), r(libre.cible.z)], focale: Math.round(12 / Math.tan((libre.champ * Math.PI) / 360)) };
  }
  // ce qu'il y a sous le pointeur : le premier maillage touché qui appartient à une cible (halos et présentateur exclus)
  function viser(nx, ny) {
    if (!racine) return null;
    point.set(nx, ny); rayon.setFromCamera(point, oeil);
    for (const t of rayon.intersectObjects(racine.children, true)) {
      let x = t.object, cible = null, ignore = !!(x.userData.halo || x.isSprite);
      for (; x && !ignore; x = x.parent) { if (x.userData.ignorer || x === marque) ignore = true; else if (!cible && x.userData.cible) cible = x.userData.cible; }
      if (!ignore && cible && (cible.genre === "surface" || cible.genre === "objet" || !outils || outils.visible || cible.genre === "ecran" || cible.genre === "enseigne")) return { ...cible };
    }
    return null;
  }
  function marquer() {
    if (marque) { if (marque.parent) marque.parent.remove(marque); marque = null; }
    for (const g of reperes.lumiere.concat(reperes.camera)) if (g && g.parent === outils) g.scale.setScalar(1);
    const S2 = selection; if (!S2 || !racine) return;
    const jaune = 0xf0b429;
    if (S2.genre === "surface" && pans[S2.pan]) {
      const p = pans[S2.pan];
      marque = new THREE.Mesh(p.geometry, garder(new THREE.MeshBasicMaterial({ color: jaune, transparent: true, opacity: 0.2, depthWrite: false, toneMapped: false })));
      marque.position.copy(p.position); marque.rotation.copy(p.rotation); marque.translateZ(0.006); marque.renderOrder = 6; marque.userData.halo = true; racine.add(marque);
      return;
    }
    const g = S2.genre === "objet" ? groupes[S2.index] : (reperes[S2.genre] || [])[S2.index || 0];
    if (!g) return;
    if ((S2.genre === "lumiere" || S2.genre === "camera") && g.parent === outils) { g.scale.setScalar(1.7); return; }
    const b = g.userData.boite || boiteLocale(g); if (!b) return;
    marque = new THREE.Box3Helper(b.clone().expandByScalar(0.015), jaune); marque.material.toneMapped = false; marque.material.depthTest = false; marque.renderOrder = 7;
    marque.userData.halo = true; garder(marque.geometry); garder(marque.material); g.add(marque);
  }
  function empreintes() {
    return decor.objets.map((ob, i) => {
      const b = groupes[i] && groupes[i].userData.boite; if (!b) return null;
      return { x0: b.min.x * ob.e, x1: b.max.x * ob.e, z0: b.min.z * ob.e, z1: b.max.z * ob.e, y0: b.min.y * ob.e, y1: b.max.y * ob.e };
    });
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
    let p = reg.pose(decor.cameras, t);
    if (libre) { const o2 = oeilLibre(); p = { x: o2.x, y: o2.y, z: o2.z, champ: libre.champ, vers: [libre.cible.x, libre.cible.y, libre.cible.z] }; }
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
    vueLibre, orbiter, zoomer, glisser, poseLibre, viser, empreintes,
    libre: () => !!libre,
    choisir(c) { selection = c || null; marquer(); },
    detruire() {
      detruit = true; vider();
      for (const x of durables.splice(0)) { try { x.dispose(); } catch (e) { /* déjà libéré */ } }
      for (const t of gpu.values()) { try { t.dispose(); } catch (e) { /* déjà libéré */ } }
      gpu.clear();
      for (const pr of modeles.values()) pr.then((m) => { if (m) m.traverse((x) => { if (x.isMesh) { try { x.geometry.dispose(); for (const mt of [].concat(x.material)) { for (const k of ["map", "normalMap", "roughnessMap", "metalnessMap", "emissiveMap", "aoMap"]) if (mt[k]) mt[k].dispose(); mt.dispose(); } } catch (e) { /* déjà libéré */ } } }); });
      modeles.clear();
      if (refletCible) { try { refletCible.dispose(); } catch (e) { /* déjà libéré */ } refletCible = null; }
      try { rendu.dispose(); } catch (e) { /* contexte déjà perdu */ }
    },
  };
}

// les types que le moteur sait bâtir : égal au catalogue de la logique et du serveur (banc)
export const TYPES_MOTEUR = TYPES;
export { borne };
