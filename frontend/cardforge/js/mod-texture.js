/* ═══════════════════════════════════════════════════════════════════════════
   Card Forge — piece 06 · Matières   [P6]
   Proprietaire exclusif de : doc.texture · z 10, 30 · /api/cards/<did>/texture/*
   Prefixe DOM impose : id="cf-texture-..."   ·   feuille : css/mod-texture.css

   DEUX COUCHES ET HUIT MAPS.
   z=10  la matiere du support : 30 matieres PROCEDURALES (aucun PNG, donc
         aucun plafond de resolution — la barre livre ses maps derivees en
         512 px, mesure faite sur ses propres fichiers). Chaque tuile est
         PERIODIQUE par construction et son raccord est MESURE a l'ecran
         (bouton « Verifier le raccord des 30 »), pas promis.
   z=30  ce qui passe par-dessus l'illustration et sous le cadre : grain,
         foil, holographique, poussiere, givre… plus l'usure des bords et le
         vernis selectif, qui sont des couches INDEPENDANTES (chacune son mode
         de fusion : l'usure multiplie, le vernis eclaircit — les melanger
         dans une seule couche aurait donne un vernis gris).

   Les maps PBR ne sont pas dessinees ici : elles sont DERIVEES de la carte
   telle qu'elle est rendue (CF.cardBlob, le moteur unique), par
   `pbr_service.derive_maps` cote backend. On reutilise, on ne reecrit pas.
   Ce qui s'affiche sous chaque vignette est une MESURE relue sur les octets
   PNG ecrits (`map_report` + `effective_levels`), jamais la position d'un
   curseur.

   RIEN N'EST CHARGE DU RESEAU : pas une police, pas une image, pas un CDN.
   ═══════════════════════════════════════════════════════════════════════════ */
"use strict";

(function () {
  const CF = (typeof window !== "undefined") ? window.CF : null;
  if (!CF) throw new Error("mod-texture: js/core.js doit etre charge avant ce fichier");

  /* ═══════════════════════════════════════════════════════════════════════
     1. LE CATALOGUE — 30 matieres, procedurales, servies en local.
     Le bloc encadre est LU PAR LE TEST (`test_cards_texture.py`) : il compte
     les entrees et refuse la moindre URL. Un catalogue « livre en local »
     qui pointerait vers le reseau ne serait pas un catalogue livre.
     `gen` = recette, `rgb` = teinte de base, `rgb2` = teinte secondaire
     (veines, flocons, patine), `amp` = amplitude du relief visible.

     `mtl` et `rgh` = LA MATIERE, PHYSIQUEMENT : metallicite et rugosite du
     support. CE QUE CELA CORRIGE : le catalogue proposait « Or brosse » et
     rien ne reliait ce choix a la map metallique — on exportait une metallic
     a 0,000, c'est-a-dire du plastique dore. Choisir une matiere aligne
     desormais les deux niveaux cuits, et l'ecran le dit.
     ═══════════════════════════════════════════════════════════════════════ */
  /* ═══ CF-TEXTURE-CATALOG-BEGIN ═══ */
  const MATS = [
    { id: "velin", label: "Vélin ivoire", cat: "papier", gen: "grain", rgb: [247, 243, 233], amp: 0.10, p: { fine: 1.0 }, mtl: 0, rgh: 0.92 },
    { id: "offset", label: "Offset blanc", cat: "papier", gen: "grain", rgb: [252, 251, 249], amp: 0.055, p: { fine: 1.5 }, mtl: 0, rgh: 0.90 },
    { id: "bristol", label: "Bristol lisse", cat: "papier", gen: "grain", rgb: [255, 254, 251], amp: 0.03, p: { fine: 2.2 }, mtl: 0, rgh: 0.78 },
    { id: "verge", label: "Vergé crème", cat: "papier", gen: "laid", rgb: [243, 236, 219], amp: 0.11, p: { chain: 26, laid: 3 }, mtl: 0, rgh: 0.90 },
    { id: "kraft", label: "Kraft brun", cat: "papier", gen: "speckle", rgb: [186, 148, 104], rgb2: [126, 92, 58], amp: 0.16, p: { dots: 900 }, mtl: 0, rgh: 0.95 },
    { id: "recycle", label: "Recyclé gris", cat: "papier", gen: "speckle", rgb: [216, 210, 197], rgb2: [140, 132, 116], amp: 0.13, p: { dots: 1400 }, mtl: 0, rgh: 0.94 },
    { id: "aquarelle", label: "Papier aquarelle", cat: "papier", gen: "crumple", rgb: [249, 246, 238], amp: 0.17, p: { ridge: 0.55, fine: 0.9 }, mtl: 0, rgh: 0.95 },
    { id: "parchemin", label: "Parchemin", cat: "papier", gen: "crumple", rgb: [232, 217, 184], rgb2: [193, 168, 121], amp: 0.22, p: { ridge: 0.8, fine: 0.6 }, mtl: 0, rgh: 0.88 },
    { id: "journal", label: "Papier journal", cat: "papier", gen: "grain", rgb: [231, 226, 208], rgb2: [196, 188, 164], amp: 0.14, p: { fine: 0.8 }, mtl: 0, rgh: 0.96 },
    { id: "carton_noir", label: "Carton noir mat", cat: "papier", gen: "grain", rgb: [34, 32, 30], amp: 0.22, p: { fine: 1.1 }, mtl: 0, rgh: 0.97 },
    { id: "lin", label: "Lin naturel", cat: "textile", gen: "fiber", rgb: [230, 221, 202], amp: 0.20, p: { dir: 0, tight: 5 }, mtl: 0, rgh: 0.94 },
    { id: "toile", label: "Toile de coton", cat: "textile", gen: "weave", rgb: [236, 229, 214], amp: 0.20, p: { thread: 6 }, mtl: 0, rgh: 0.93 },
    { id: "canvas", label: "Canvas peintre", cat: "textile", gen: "weave", rgb: [226, 214, 190], amp: 0.28, p: { thread: 11 }, mtl: 0, rgh: 0.95 },
    { id: "jute", label: "Toile de jute", cat: "textile", gen: "weave", rgb: [201, 168, 112], amp: 0.34, p: { thread: 17 }, mtl: 0, rgh: 0.98 },
    { id: "soie", label: "Soie sauvage", cat: "textile", gen: "fiber", rgb: [238, 232, 226], amp: 0.12, p: { dir: 1, tight: 9 }, mtl: 0, rgh: 0.42 },
    { id: "denim", label: "Denim", cat: "textile", gen: "twill", rgb: [58, 82, 120], rgb2: [206, 214, 226], amp: 0.26, p: { thread: 7 }, mtl: 0, rgh: 0.90 },
    { id: "feutre", label: "Feutrine", cat: "textile", gen: "fiber", rgb: [150, 60, 62], amp: 0.24, p: { dir: 2, tight: 3 }, mtl: 0, rgh: 0.99 },
    { id: "ardoise", label: "Ardoise", cat: "minéral", gen: "crumple", rgb: [66, 70, 76], rgb2: [40, 43, 47], amp: 0.26, p: { ridge: 0.7, fine: 1.4 }, mtl: 0, rgh: 0.86 },
    { id: "marbre", label: "Marbre blanc", cat: "minéral", gen: "marble", rgb: [242, 240, 236], rgb2: [150, 150, 148], amp: 0.12, p: { veins: 3.0 }, mtl: 0, rgh: 0.28 },
    /* veins ENTIER — 4,5 donnait une demi-periode de decalage d'un bord a
       l'autre, mesure 9,92x la pire marche interne (voir RECIPES.marble). */
    { id: "marbre_noir", label: "Marbre noir", cat: "minéral", gen: "marble", rgb: [30, 30, 33], rgb2: [176, 168, 140], amp: 0.16, p: { veins: 4 }, mtl: 0, rgh: 0.24 },
    { id: "beton", label: "Béton ciré", cat: "minéral", gen: "concrete", rgb: [176, 174, 168], amp: 0.16, p: { pores: 1500 }, mtl: 0, rgh: 0.82 },
    { id: "granit", label: "Granit moucheté", cat: "minéral", gen: "speckle", rgb: [148, 146, 150], rgb2: [58, 56, 60], amp: 0.20, p: { dots: 4200 }, mtl: 0, rgh: 0.62 },
    { id: "or_brosse", label: "Or brossé", cat: "métal", gen: "brush", rgb: [206, 168, 78], rgb2: [255, 233, 168], amp: 0.20, p: { spec: 0.9 }, mtl: 1, rgh: 0.34 },
    { id: "argent_brosse", label: "Argent brossé", cat: "métal", gen: "brush", rgb: [188, 190, 195], rgb2: [244, 246, 250], amp: 0.20, p: { spec: 1.0 }, mtl: 1, rgh: 0.28 },
    { id: "cuivre", label: "Cuivre patiné", cat: "métal", gen: "brush", rgb: [172, 104, 66], rgb2: [96, 148, 128], amp: 0.26, p: { spec: 0.6, patina: 1 }, mtl: 1, rgh: 0.46 },
    { id: "acier", label: "Acier peigné", cat: "métal", gen: "brush", rgb: [122, 126, 132], rgb2: [186, 192, 200], amp: 0.17, p: { spec: 0.8 }, mtl: 1, rgh: 0.32 },
    { id: "carbone", label: "Fibre de carbone", cat: "métal", gen: "twill", rgb: [30, 31, 34], rgb2: [92, 96, 104], amp: 0.30, p: { thread: 9 }, mtl: 0, rgh: 0.38 },
    { id: "cuir", label: "Cuir grainé", cat: "organique", gen: "leather", rgb: [104, 62, 40], rgb2: [58, 32, 20], amp: 0.24, p: { cell: 13 }, mtl: 0, rgh: 0.72 },
    { id: "bois", label: "Bois clair", cat: "organique", gen: "wood", rgb: [199, 158, 106], rgb2: [150, 108, 62], amp: 0.18, p: { rings: 7 }, mtl: 0, rgh: 0.66 },
    { id: "ebene", label: "Ébène", cat: "organique", gen: "wood", rgb: [58, 42, 33], rgb2: [26, 18, 14], amp: 0.20, p: { rings: 11 }, mtl: 0, rgh: 0.58 },
  ];
  /* ═══ CF-TEXTURE-CATALOG-END ═══ */

  /* effets de dessus (z=30). `k` = recette, `d` = mode de fusion conseille. */
  const OVERS = [
    { id: "none", label: "Aucun", k: "none", d: "normal", o: 0 },
    { id: "grain", label: "Grain de la matière", k: "grain", d: "soft-light", o: 0.5 },
    { id: "toile30", label: "Trame toile", k: "weave", d: "multiply", o: 0.22 },
    { id: "foil_or", label: "Foil or", k: "foil", d: "screen", o: 0.42, rgb: [255, 214, 122] },
    { id: "foil_argent", label: "Foil argent", k: "foil", d: "screen", o: 0.38, rgb: [226, 236, 248] },
    { id: "holo", label: "Holographique", k: "holo", d: "overlay", o: 0.46 },
    { id: "irise", label: "Irisé", k: "iris", d: "overlay", o: 0.40 },
    { id: "givre", label: "Givre", k: "frost", d: "screen", o: 0.30 },
    { id: "poussiere", label: "Poussière & rayures", k: "dust", d: "screen", o: 0.35 },
    { id: "vignette", label: "Vignettage", k: "vig", d: "multiply", o: 0.45 },
  ];

  const BLENDS = ["normal", "multiply", "screen", "overlay", "soft-light",
    "hard-light", "darken", "lighten", "color-burn", "color-dodge",
    "difference", "exclusion", "hue", "saturation", "color", "luminosity"];

  /* Les bornes de la derivation. MIROIR de pbr_service.DERIVE_DEFAULTS /
     DERIVE_RANGES — le backend fait autorite et `/defaults` les rapatrie au
     demarrage ; ce tableau n'existe que pour que la piece soit demontrable
     SEULE (backend muet). `test_cards_texture.py` compare les deux : une
     derive silencieuse entre l'ecran et le service serait un curseur qui ment. */
  const DERIVE_UI = [
    { k: "normal_strength", label: "Force de la normale", min: 0, max: 4, step: 0.05, def: 0.8 },
    { k: "normal_invert_y", label: "Inverser Y (DirectX)", type: "bool", def: false },
    { k: "height_detail", label: "Détail de la hauteur", min: 0, max: 1, step: 0.01, def: 0.5 },
    { k: "roughness_source", label: "Source de rugosité", type: "enum", opts: ["micro", "albedo"], def: "micro" },
    { k: "roughness_bias", label: "Biais de rugosité", min: 0, max: 1, step: 0.01, def: 0.5 },
    { k: "roughness_contrast", label: "Contraste de rugosité", min: 0, max: 1, step: 0.01, def: 0.5 },
    { k: "roughness_invert", label: "Inverser la rugosité", type: "bool", def: false },
    { k: "ao_strength", label: "Force de l'occlusion", min: 0, max: 4, step: 0.05, def: 1.0 },
    { k: "ao_radius", label: "Rayon d'occlusion", min: 0.5, max: 32, step: 0.5, def: 4.0, unit: "px" },
    { k: "metallic_mode", label: "Mode métallique", type: "enum", opts: ["auto", "none", "luminance"], def: "auto" },
    { k: "metallic_threshold", label: "Seuil métallique", min: 0, max: 1, step: 0.01, def: 0.5 },
    { k: "emissive_threshold", label: "Seuil d'émission", min: 0, max: 1, step: 0.01, def: 0.85 },
  ];

  const KINDS = ["basecolor", "normal", "roughness", "metallic", "ao", "height", "emissive", "orm"];
  const KIND_FR = {
    basecolor: "Base color", normal: "Normale", roughness: "Rugosité",
    metallic: "Métallique", ao: "Occlusion (AO)", height: "Hauteur",
    emissive: "Émission", orm: "ORM (packée)",
  };
  const RES_CHOICES = [1024, 2048, 4096];

  /* ═══════════════════════════════════════════════════════════════════════
     2. L'ETAT — le schema declare a l'enregistrement.
     `pbr` est le seul sous-arbre LU PAR UNE AUTRE PIECE (P8, export 3D) :
     il porte les reglages de derivation, les niveaux cuits et la definition.
     ═══════════════════════════════════════════════════════════════════════ */
  const DERIVE_DEF = {};
  DERIVE_UI.forEach((d) => { DERIVE_DEF[d.k] = d.def; });

  const DEF = {
    paper: "velin", tint: "#ffffff", opacity: 1, blend: "normal", scale: 1, angle: 0,
    over: "grain", over_opacity: 0.5, over_blend: "soft-light", over_scale: 1,
    wear: 0, varnish: 0, custom: "", seed: 7,
    /* `pbr` porte les douze reglages DEUX FOIS : sous `derive`, ou cet ecran
       les lit, et A PLAT, ou `pbr_service.normalize_derive` les cherche quand
       P8 lui passe ce sous-arbre entier. Voir `pbrOut` : c'est le meme geste,
       ici pour l'etat declare a l'enregistrement. */
    pbr: Object.assign({
      derive: JSON.parse(JSON.stringify(DERIVE_DEF)),
      /* les niveaux par defaut sont ceux de la matiere par defaut (velin
         ivoire) : un panneau qui s'ouvre en se contredisant lui-meme n'a pas
         de raison de le faire. */
      levels: { metallic: 0.0, roughness: 0.92 },
      res: 2048, bits16: true, square: false,
      ready: false, informative: 0, updated: "",
    }, DERIVE_DEF),
  };

  const clone = (v) => JSON.parse(JSON.stringify(v));
  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
  const num = (v, d) => { const n = Number(v); return isFinite(n) ? n : d; };

  /** L'etat complet, defauts compris : un sous-arbre venu du disque peut etre
      partiel (document d'une version anterieure). Aucun painter ne doit avoir
      a se demander si une cle existe. */
  function st(doc) {
    const raw = (doc && doc.texture) || {};
    const s = {};
    Object.keys(DEF).forEach((k) => {
      s[k] = (raw[k] === undefined || raw[k] === null) ? clone(DEF[k]) : raw[k];
    });
    const p = Object.assign({}, clone(DEF.pbr), s.pbr || {});
    p.derive = Object.assign({}, DERIVE_DEF, p.derive || {});
    p.levels = Object.assign({}, DEF.pbr.levels, p.levels || {});
    /* `.derive` fait AUTORITE, et le miroir a plat est recalcule a chaque
       lecture : un document ecrit par une version anterieure (qui ne portait
       que `.derive`) ne peut donc pas laisser un miroir perime derriere lui.
       Une seule verite, recopiee — jamais deux. */
    Object.assign(p, p.derive);
    s.pbr = p;
    s.opacity = clamp(num(s.opacity, 1), 0, 1);
    s.over_opacity = clamp(num(s.over_opacity, DEF.over_opacity), 0, 1);
    s.scale = clamp(num(s.scale, 1), 0.1, 8);
    s.over_scale = clamp(num(s.over_scale, 1), 0.1, 8);
    s.wear = clamp(num(s.wear, 0), 0, 1);
    s.varnish = clamp(num(s.varnish, 0), 0, 1);
    s.angle = clamp(num(s.angle, 0), -180, 180);
    s.seed = Math.round(clamp(num(s.seed, 7), 1, 9999));
    return s;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     3. BRUIT — periodique par construction.
     Un bruit a treillis dont le pas divise la tuile se raccorde exactement :
     c'est ce qui rend le motif repetable sans couture, sans avoir a corriger
     une jonction apres coup.
     ═══════════════════════════════════════════════════════════════════════ */
  function rng(seed) {
    let a = (seed >>> 0) || 1;
    return function () {
      a += 0x6D2B79F5;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function lattice(nx, ny, r) {
    const a = new Float32Array(nx * ny);
    for (let i = 0; i < a.length; i++) a[i] = r();
    return a;
  }
  function sample(a, nx, ny, x, y) {
    const xi = Math.floor(x), yi = Math.floor(y);
    let xf = x - xi, yf = y - yi;
    xf = xf * xf * (3 - 2 * xf); yf = yf * yf * (3 - 2 * yf);
    const x0 = ((xi % nx) + nx) % nx, y0 = ((yi % ny) + ny) % ny;
    const x1 = (x0 + 1) % nx, y1 = (y0 + 1) % ny;
    const t = a[y0 * nx + x0] + (a[y0 * nx + x1] - a[y0 * nx + x0]) * xf;
    const b = a[y1 * nx + x0] + (a[y1 * nx + x1] - a[y1 * nx + x0]) * xf;
    return t + (b - t) * yf;
  }
  /** fbm periodique. `octs` = [[nx, ny, amplitude], …] ; nx/ny sont des
      NOMBRES DE CELLULES sur la tuile, donc entiers : le raccord est exact. */
  function fbm(size, octs, seed) {
    const r = rng(seed), out = new Float32Array(size * size);
    let tot = 0;
    for (let o = 0; o < octs.length; o++) {
      const nx = octs[o][0], ny = octs[o][1], amp = octs[o][2];
      const a = lattice(nx, ny, r), kx = nx / size, ky = ny / size;
      for (let y = 0; y < size; y++) {
        const yy = y * ky, row = y * size;
        for (let x = 0; x < size; x++) out[row + x] += amp * sample(a, nx, ny, x * kx, yy);
      }
      tot += amp;
    }
    for (let i = 0; i < out.length; i++) out[i] /= tot;
    return out;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     4. LES RECETTES — chacune rend {v, t} : v = relief (0..1), t = melange
     vers la teinte secondaire (0..1). La couleur se compose ensuite au meme
     endroit pour toutes : une seule regle de colorisation, donc un catalogue
     coherent.
     ═══════════════════════════════════════════════════════════════════════ */
  const RECIPES = {
    grain(S, m, seed) {
      const f = (m.p && m.p.fine) || 1;
      const v = fbm(S, [[8, 8, 0.35], [32, 32, 0.30], [Math.round(64 * f), Math.round(64 * f), 0.55],
      [Math.round(128 * f), Math.round(128 * f), 0.5]], seed);
      return { v: v, t: fbm(S, [[4, 4, 1]], seed + 91) };
    },
    laid(S, m, seed) {
      const chain = (m.p && m.p.chain) || 26, laid = (m.p && m.p.laid) || 3;
      const g = fbm(S, [[16, 16, 0.4], [64, 64, 0.6]], seed);
      const v = new Float32Array(S * S);
      const cN = Math.max(1, Math.round(S / chain)), lN = Math.max(1, Math.round(S / laid));
      for (let y = 0; y < S; y++) {
        const ly = 0.5 + 0.5 * Math.cos(2 * Math.PI * y * lN / S);
        for (let x = 0; x < S; x++) {
          const cx = 0.5 + 0.5 * Math.cos(2 * Math.PI * x * cN / S);
          v[y * S + x] = 0.42 * g[y * S + x] + 0.34 * ly + 0.24 * cx;
        }
      }
      return { v: v, t: g };
    },
    fiber(S, m, seed) {
      const tight = (m.p && m.p.tight) || 5, dir = (m.p && m.p.dir) || 0;
      const a = Math.max(2, Math.round(S / (tight * 8))), b = Math.round(S / 2);
      const o = (dir === 1) ? [[b, a, 0.7], [Math.round(b / 2), Math.round(a * 2), 0.3]]
        : (dir === 2) ? [[64, 64, 0.5], [128, 128, 0.5]]
          : [[a, b, 0.7], [Math.round(a * 2), Math.round(b / 2), 0.3]];
      const v = fbm(S, o.concat([[96, 96, 0.22]]), seed);
      return { v: v, t: fbm(S, [[8, 8, 1]], seed + 17) };
    },
    weave(S, m, seed) {
      const T = Math.max(2, (m.p && m.p.thread) || 6);
      const per = Math.max(1, Math.round(S / (2 * T))) * 2 * T;   /* divise la tuile */
      const g = fbm(S, [[64, 64, 0.6], [128, 128, 0.4]], seed);
      const v = new Float32Array(S * S), t = new Float32Array(S * S);
      const step = per / S;
      for (let y = 0; y < S; y++) {
        const yy = y * step / T, by = Math.floor(yy) & 1, fy = yy - Math.floor(yy);
        for (let x = 0; x < S; x++) {
          const xx = x * step / T, bx = Math.floor(xx) & 1, fx = xx - Math.floor(xx);
          const up = (bx + by) & 1;
          const bump = up ? Math.sin(Math.PI * fx) : Math.sin(Math.PI * fy);
          v[y * S + x] = clamp(0.22 + 0.62 * bump + 0.22 * (g[y * S + x] - 0.5), 0, 1);
          t[y * S + x] = up ? 0.15 : 0.85;
        }
      }
      return { v: v, t: t };
    },
    /* LE SERGE NE SE REFERMAIT PAS EN Y, ET C'ETAIT MESURABLE. Deux conditions
       pour qu'il se repete : le NOMBRE DE BLOCS du damier doit etre entier ET
       PAIR (`bx + by` change de parite a chaque bloc), et le pas de la
       diagonale doit diviser la tuile un nombre PAIR de fois — d'un bord a
       l'autre, `dia` gagne S, et `(S / T) % 2` doit valoir 0. Les deux se
       satisfont d'un coup en CHOISISSANT le nombre de blocs d'abord, pair, et
       en deduisant le pas. `thread` reste la largeur VISEE, au pixel pres.
       MESURE, « Fibre de carbone » (thread 9 : 512 / 18 = 28,44 blocs, donc ni
       entier ni pair) : marche au raccord 23,51 en vertical pour une pire
       marche interne de 13,95, soit 1,68 fois plus — une couture reelle.
       Avec 28 blocs (pas 9,143 au lieu de 9) : 12,83 contre 12,92, soit 0,99. */
    twill(S, m, seed) {
      const T0 = Math.max(2, (m.p && m.p.thread) || 8);
      const blocs = Math.max(2, 2 * Math.round(S / (4 * T0)));
      const T = S / (2 * blocs);
      const g = fbm(S, [[64, 64, 0.5], [128, 128, 0.5]], seed);
      const v = new Float32Array(S * S), t = new Float32Array(S * S);
      for (let y = 0; y < S; y++) {
        for (let x = 0; x < S; x++) {
          const bx = Math.floor(x / (T * 2)), by = Math.floor(y / (T * 2));
          const dia = ((bx + by) & 1) ? (x + y) : (x - y + S);
          const f = (((dia / T) % 2) + 2) % 2;
          const bump = Math.sin(Math.PI * (f > 1 ? 2 - f : f));
          v[y * S + x] = clamp(0.20 + 0.66 * bump + 0.20 * (g[y * S + x] - 0.5), 0, 1);
          t[y * S + x] = 0.30 + 0.55 * bump;
        }
      }
      return { v: v, t: t };
    },
    speckle(S, m, seed) {
      const base = RECIPES.grain(S, m, seed);
      const r = rng(seed + 313), t = new Float32Array(S * S);
      const n = Math.round(((m.p && m.p.dots) || 900) * (S * S) / (512 * 512));
      for (let i = 0; i < n; i++) {
        const cx = Math.floor(r() * S), cy = Math.floor(r() * S);
        const rad = 1 + Math.floor(r() * 2.6), w = 0.55 + 0.45 * r();
        for (let dy = -rad; dy <= rad; dy++) {
          const y = ((cy + dy) % S + S) % S;
          for (let dx = -rad; dx <= rad; dx++) {
            if (dx * dx + dy * dy > rad * rad) continue;
            const x = ((cx + dx) % S + S) % S;
            t[y * S + x] = Math.max(t[y * S + x], w);
            base.v[y * S + x] = clamp(base.v[y * S + x] * (1 - 0.35 * w), 0, 1);
          }
        }
      }
      return { v: base.v, t: t };
    },
    crumple(S, m, seed) {
      const ridge = (m.p && m.p.ridge) || 0.6, fine = (m.p && m.p.fine) || 1;
      const a = fbm(S, [[6, 6, 0.5], [12, 12, 0.3], [24, 24, 0.2]], seed);
      const b = fbm(S, [[Math.round(64 * fine), Math.round(64 * fine), 0.6],
      [Math.round(128 * fine), Math.round(128 * fine), 0.4]], seed + 7);
      const v = new Float32Array(S * S);
      for (let i = 0; i < v.length; i++) {
        const r = 1 - Math.abs(2 * a[i] - 1);
        v[i] = clamp((1 - ridge) * b[i] + ridge * (0.25 + 0.75 * r * r), 0, 1);
      }
      return { v: v, t: a };
    },
    /* LA SEULE VRAIE COUTURE DES TRENTE, ET ELLE TENAIT A UNE VIRGULE.
       `veins` est un NOMBRE DE PERIODES sur la diagonale de la tuile : il doit
       etre ENTIER, sinon `sin(2 pi veins (x + y) / S)` ne reprend pas la meme
       valeur en x + S et les deux bords opposes tombent sur deux phases
       differentes — la tuile porte alors une couture PAR CONSTRUCTION, quoi
       qu'on fasse ensuite. « Marbre noir » etait regle a 4,5, c'est-a-dire une
       DEMI-periode de decalage : le pire cas possible. MESURE : marche au
       raccord 65,78 pour une pire marche interne de 6,63, soit 9,92 fois plus.
       Arrondi a 4 : 3,00 contre 5,77, soit 0,52. Le catalogue ne peut plus
       accepter un reglage qui casse le raccord, meme si quelqu'un l'y ecrit. */
    marble(S, m, seed) {
      const veins = Math.max(1, Math.round((m.p && m.p.veins) || 3));
      const w = fbm(S, [[4, 4, 0.6], [12, 12, 0.3], [32, 32, 0.1]], seed);
      const g = fbm(S, [[96, 96, 1]], seed + 5);
      const v = new Float32Array(S * S), t = new Float32Array(S * S);
      for (let y = 0; y < S; y++) {
        for (let x = 0; x < S; x++) {
          const i = y * S + x;
          const band = 0.5 + 0.5 * Math.sin(2 * Math.PI * (veins * (x + y) / S + 2.6 * (w[i] - 0.5)));
          const vein = Math.pow(band, 7);
          v[i] = clamp(0.72 + 0.2 * g[i] - 0.3 * vein, 0, 1);
          t[i] = vein;
        }
      }
      return { v: v, t: t };
    },
    concrete(S, m, seed) {
      const base = fbm(S, [[8, 8, 0.4], [24, 24, 0.3], [64, 64, 0.2], [160, 160, 0.3]], seed);
      const r = rng(seed + 77), t = new Float32Array(S * S);
      const n = Math.round(((m.p && m.p.pores) || 1500) * (S * S) / (512 * 512));
      for (let i = 0; i < n; i++) {
        const x = Math.floor(r() * S), y = Math.floor(r() * S);
        base[y * S + x] = clamp(base[y * S + x] * 0.45, 0, 1);
      }
      return { v: base, t: t };
    },
    brush(S, m, seed) {
      const spec = (m.p && m.p.spec) || 0.8;
      const v = fbm(S, [[256, 2, 0.55], [128, 6, 0.25], [512, 1, 0.20]], seed);
      const t = new Float32Array(S * S);
      for (let y = 0; y < S; y++) {
        const ramp = 0.5 + 0.5 * Math.cos(2 * Math.PI * y / S);
        for (let x = 0; x < S; x++) {
          const i = y * S + x;
          t[i] = clamp(spec * (0.35 * ramp + 0.65 * v[i]), 0, 1);
          v[i] = clamp(0.35 + 0.65 * v[i], 0, 1);
        }
      }
      if (m.p && m.p.patina) {
        const pa = fbm(S, [[5, 5, 0.6], [17, 17, 0.4]], seed + 41);
        for (let i = 0; i < t.length; i++) t[i] = clamp(t[i] * 0.4 + Math.pow(pa[i], 2.2), 0, 1);
      }
      return { v: v, t: t };
    },
    leather(S, m, seed) {
      const cell = (m.p && m.p.cell) || 13;
      const n = Math.max(3, Math.round(S / cell));
      const a = fbm(S, [[n, n, 1]], seed), b = fbm(S, [[n * 2, n * 2, 1]], seed + 3);
      const g = fbm(S, [[192, 192, 1]], seed + 9);
      const v = new Float32Array(S * S), t = new Float32Array(S * S);
      for (let i = 0; i < v.length; i++) {
        const crack = 1 - Math.abs(2 * a[i] - 1);
        const pebble = 0.35 + 0.65 * b[i];
        v[i] = clamp(0.30 + 0.55 * pebble - 0.45 * Math.pow(crack, 3) + 0.14 * (g[i] - 0.5), 0, 1);
        t[i] = clamp(Math.pow(crack, 2.5), 0, 1);
      }
      return { v: v, t: t };
    },
    wood(S, m, seed) {
      const rings = (m.p && m.p.rings) || 7;
      const w = fbm(S, [[3, 12, 0.6], [7, 32, 0.4]], seed);
      const g = fbm(S, [[6, 220, 1]], seed + 2);
      const v = new Float32Array(S * S), t = new Float32Array(S * S);
      for (let y = 0; y < S; y++) {
        for (let x = 0; x < S; x++) {
          const i = y * S + x;
          const band = 0.5 + 0.5 * Math.sin(2 * Math.PI * (rings * x / S + 1.8 * (w[i] - 0.5)));
          v[i] = clamp(0.42 + 0.42 * band + 0.16 * (g[i] - 0.5), 0, 1);
          t[i] = Math.pow(1 - band, 2);
        }
      }
      return { v: v, t: t };
    },
  };

  const MAT_BY_ID = {};
  MATS.forEach((m) => { MAT_BY_ID[m.id] = m; });
  const OVER_BY_ID = {};
  OVERS.forEach((o) => { OVER_BY_ID[o.id] = o; });

  /* ═══════════════════════════════════════════════════════════════════════
     5. TUILES ET COUCHES — le calcul lourd ne se fait qu'une fois.
     Les painters ne recoivent AUCUNE echelle (contrat) : la tuile est donc
     produite en pixels de TOILE, 1:1. Ce qui est a l'ecran est ce qui part a
     l'imprimeur — a l'octet.
     ═══════════════════════════════════════════════════════════════════════ */
  const TILE = 512;
  const tileCache = new Map();      /* id|seed|size -> canvas */
  const layerCache = new Map();     /* cle d'etat -> canvas */
  const imgCache = new Map();       /* url -> {img, promise} */

  function mk(w, h) {
    const c = document.createElement("canvas");
    c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h));
    return c;
  }
  function colorize(S, m, out) {
    const d = new ImageData(S, S);
    const px = d.data, c1 = m.rgb, c2 = m.rgb2 || m.rgb, amp = m.amp === undefined ? 0.16 : m.amp;
    for (let i = 0, j = 0; i < out.v.length; i++, j += 4) {
      const shade = 1 + (out.v[i] - 0.5) * 2 * amp;
      const t = out.t ? out.t[i] : 0;
      px[j] = clamp((c1[0] + (c2[0] - c1[0]) * t) * shade, 0, 255);
      px[j + 1] = clamp((c1[1] + (c2[1] - c1[1]) * t) * shade, 0, 255);
      px[j + 2] = clamp((c1[2] + (c2[2] - c1[2]) * t) * shade, 0, 255);
      px[j + 3] = 255;
    }
    return d;
  }
  function tileOf(matId, seed, size) {
    const S = size || TILE;
    const key = matId + "|" + seed + "|" + S;
    let c = tileCache.get(key);
    if (c) return c;
    const m = MAT_BY_ID[matId] || MATS[0];
    const rec = RECIPES[m.gen] || RECIPES.grain;
    const cv = mk(S, S);
    cv.getContext("2d").putImageData(colorize(S, m, rec(S, m, seed * 977 + 13)), 0, 0);
    if (tileCache.size > 64) tileCache.clear();
    tileCache.set(key, cv);
    return cv;
  }
  function loadImg(url) {
    let e = imgCache.get(url);
    if (e) return e.promise;
    const img = new Image();
    const promise = new Promise((res) => {
      img.onload = () => { e.ok = true; res(img); };
      img.onerror = () => { e.ok = false; res(null); };
      img.src = url;
    });
    e = { img: img, ok: false, promise: promise };
    imgCache.set(url, e);
    return promise;
  }

  function patternFill(c, tile, W, H, scale, angle) {
    const p = c.createPattern(tile, "repeat");
    if (!p) return;
    c.save();
    c.translate(W / 2, H / 2);
    c.rotate(angle * Math.PI / 180);
    c.scale(scale, scale);
    const R = Math.hypot(W, H) / (2 * Math.max(0.05, scale)) + 8;
    c.fillStyle = p;
    c.fillRect(-R, -R, 2 * R, 2 * R);
    c.restore();
  }

  /* ═══════════════════════════════════════════════════════════════════════
     5 bis. LE RACCORD DE TUILE — et LA MESURE QUI ETAIT FAUSSE.

     CE QUE CE PANNEAU AFFICHAIT, ET POURQUOI C'ETAIT UN VERDICT FAUX. La
     marche au raccord etait divisee par la marche MEDIANE a l'interieur de la
     tuile, et le verdict tombait au-dessus de 2,0x. Sur une matiere a
     structure — un tissage, un serge — la mediane est prise entre deux
     colonnes quelconques, c'est-a-dire le plus souvent A L'INTERIEUR d'un fil,
     la ou rien ne se passe ; la marche au raccord, elle, tombe sur un BORD DE
     FIL. On comparait donc une transition franche a une non-transition, et le
     rapport gonflait tout seul. Les chiffres publies : Toile de coton 2,35x,
     Canvas peintre 4,86x, Toile de jute 7,28x — « couture visible », et
     « 26 / 30 » en bas de page.

     LES OCTETS DISENT AUTRE CHOSE. Marche au raccord de la toile de jute :
     40,27. PIRE marche interne de la meme tuile : 40,25. Le raccord n'est pas
     une couture, c'est un bord de fil comme les 85 autres. Trois des quatre
     « echecs » etaient des faux. Le quatrieme, lui, etait vrai et l'est
     reste : Marbre noir, 65,78 au raccord contre 6,63 pour la pire marche
     interne — dix fois pire que tout ce que la tuile contient. Il est corrige
     a la racine (voir RECIPES.marble), et un cinquieme a ete trouve en
     cherchant : Fibre de carbone, 1,68 (voir RECIPES.twill).

     LA MESURE, MAINTENANT. On compare la marche au raccord a la PIRE marche
     interne, sur les 511 paires de colonnes et les 511 paires de lignes — pas
     sur 24 sondages. « exces = 1,00 » veut dire : le raccord ne fait rien de
     pire que ce que la matiere fait deja quelque part a l'interieur. C'est
     verifiable, ca ne depend d'aucun seuil arbitraire, et ca ne peut pas etre
     flatte par une matiere lisse. Les deux axes sont separes : une tuile peut
     se refermer en largeur et pas en hauteur, et l'ancien scalaire unique le
     cachait. L'ancien rapport reste publie a cote, sous son nom, parce qu'un
     chiffre qu'on retire sans le dire est un chiffre qu'on cache.
     ═══════════════════════════════════════════════════════════════════════ */
  const SEAM_GRADES = [[1.0, "invisible"], [1.5, "discret"], [3.0, "visible"]];
  const seamCache = new Map();

  function seamGrade(r) {
    for (let i = 0; i < SEAM_GRADES.length; i++) if (r <= SEAM_GRADES[i][0]) return SEAM_GRADES[i][1];
    return "cassé";
  }
  function median(a) { const b = a.slice().sort((x, y) => x - y); return b[b.length >> 1] || 1e-6; }
  function maxi(a) { let v = 0; for (let i = 0; i < a.length; i++) if (a[i] > v) v = a[i]; return v; }

  /** La mesure de raccord d'une luminance carree S x S. Isolee ici parce que
      la MEME fonction sert a la tuile peinte a l'ecran et au PNG relu par le
      backend : deux calculs differents auraient produit deux verites. */
  function seamOfLum(L, S) {
    const colStep = (x0, x1) => {
      let s = 0;
      for (let y = 0; y < S; y++) s += Math.abs(L[y * S + x0] - L[y * S + x1]);
      return s / S;
    };
    const rowStep = (y0, y1) => {
      let s = 0;
      const a = y0 * S, b = y1 * S;
      for (let x = 0; x < S; x++) s += Math.abs(L[a + x] - L[b + x]);
      return s / S;
    };
    const inX = new Float64Array(S - 1), inY = new Float64Array(S - 1);
    for (let k = 1; k < S; k++) { inX[k - 1] = colStep(k - 1, k); inY[k - 1] = rowStep(k - 1, k); }
    const eX = colStep(S - 1, 0), eY = rowStep(S - 1, 0);
    const mxX = Math.max(1e-6, maxi(inX)), mxY = Math.max(1e-6, maxi(inY));
    const mdX = Math.max(1e-6, median(Array.from(inX))), mdY = Math.max(1e-6, median(Array.from(inY)));
    const exX = eX / mxX, exY = eY / mxY;
    const exces = Math.max(exX, exY);
    /* LE VERDICT SE PREND SUR LE NOMBRE PUBLIE, a la precision ou il est
       publie. Sans cela, la vignette d'une toile affiche « 1,00x » pendant que
       le compte la classe en echec parce qu'elle vaut 1,0019 : le badge et le
       total se contrediraient sur le meme octet, et c'est exactement le defaut
       qu'on repare. On n'echoue pas sur un ecart qu'on ne montre pas. La
       valeur pleine reste rendue (`exces_brut`) — c'est elle que le backend
       doit retrouver a l'octet pres sur le fichier exporte. */
    const publie = Math.round(exces * 100) / 100;
    return {
      px: S,
      x: { edge: eX, med: mdX, max: mxX, exces: exX },
      y: { edge: eY, med: mdY, max: mxY, exces: exY },
      exces: publie, exces_brut: exces, grade: seamGrade(publie),
      /* l'ANCIEN rapport, garde et nomme : marche au raccord sur marche
         MEDIANE. Il n'est pas faux, il repond a une autre question. */
      ratio_median: Math.max(eX / mdX, eY / mdY),
    };
  }

  /** La luminance de la tuile TELLE QU'ELLE EST PEINTE (512 px), meme formule
      que celle que le backend applique aux octets du PNG exporte. */
  function lumOfTile(matId, seed, S) {
    const px = tileOf(matId, seed, S).getContext("2d").getImageData(0, 0, S, S).data;
    const L = new Float64Array(S * S);
    for (let i = 0, j = 0; i < L.length; i++, j += 4) {
      L[i] = 0.299 * px[j] + 0.587 * px[j + 1] + 0.114 * px[j + 2];
    }
    return L;
  }

  function seamOf(matId, seed) {
    const key = matId + "|" + seed;
    const hit = seamCache.get(key);
    if (hit) return hit;
    const out = seamOfLum(lumOfTile(matId, seed, TILE), TILE);
    if (seamCache.size > 80) seamCache.clear();
    seamCache.set(key, out);
    return out;
  }
  /** Ce qui est DEJA mesure, sans rien calculer. */
  function seamPeek(matId, seed) { return seamCache.get(matId + "|" + seed) || null; }

  /* ── couche z=10 : le support ──────────────────────────────────────────── */
  function buildUnder(g, s, custom) {
    const W = g.canvas_px[0], H = g.canvas_px[1];
    const cv = mk(W, H), c = cv.getContext("2d");
    c.fillStyle = s.tint || "#ffffff";
    c.fillRect(0, 0, W, H);
    if (s.paper === "__import" && custom) {
      const k = Math.max(W / custom.width, H / custom.height);
      const w = custom.width * k, h = custom.height * k;
      c.globalCompositeOperation = "multiply";
      c.drawImage(custom, (W - w) / 2, (H - h) / 2, w, h);
    } else if (s.paper !== "none" && MAT_BY_ID[s.paper]) {
      c.globalCompositeOperation = "multiply";
      patternFill(c, tileOf(s.paper, s.seed), W, H, s.scale, s.angle);
    }
    return cv;
  }

  /* ── couche z=30 : l'effet ─────────────────────────────────────────────── */
  function buildOver(g, s) {
    const W = g.canvas_px[0], H = g.canvas_px[1];
    const o = OVER_BY_ID[s.over] || OVER_BY_ID.none;
    const cv = mk(W, H), c = cv.getContext("2d");
    const D = Math.hypot(W, H);
    if (o.k === "grain") {
      /* le grain de dessus est celui de LA MATIERE CHOISIE : sur une vraie
         carte, la fibre du support se voit A TRAVERS l'encre. Choisir « toile
         de jute » et ne la voir que sous l'illustration n'aurait aucun sens
         physique — et l'illustration couvre tout. */
      const src = (s.paper !== "none" && s.paper !== "__import") ? s.paper : "velin";
      patternFill(c, tileOf(src, s.seed), W, H, s.over_scale, s.angle);
    } else if (o.k === "weave") {
      patternFill(c, tileOf("toile", s.seed + 9), W, H, s.over_scale, 0);
    } else if (o.k === "foil") {
      const gr = c.createLinearGradient(0, 0, W, H);
      const col = o.rgb || [255, 214, 122];
      for (let i = 0; i <= 12; i++) {
        const t = i / 12, w = 0.5 + 0.5 * Math.sin(t * 26 + 1.2);
        gr.addColorStop(t, "rgba(" + col[0] + "," + col[1] + "," + col[2] + "," + (0.10 + 0.9 * Math.pow(w, 2.4)).toFixed(3) + ")");
      }
      c.fillStyle = gr; c.fillRect(0, 0, W, H);
      c.globalCompositeOperation = "multiply";
      patternFill(c, tileOf("argent_brosse", s.seed + 3), W, H, s.over_scale * 1.5, 32);
    } else if (o.k === "holo" || o.k === "iris") {
      const gr = (o.k === "holo")
        ? c.createLinearGradient(0, H, W, 0)
        : c.createRadialGradient(W * 0.42, H * 0.36, D * 0.02, W * 0.5, H * 0.5, D * 0.62);
      /* PLUSIEURS passes d'arc-en-ciel, pas une seule : un film holographique
         rebat le spectre tous les quelques millimetres. Une passe unique
         donnait un lavis turquoise, pas un holo. */
      const hues = [292, 258, 196, 154, 62, 24, 340];
      const passes = o.k === "holo" ? 3 : 2;
      const n = hues.length * passes;
      for (let i = 0; i <= n; i++) {
        gr.addColorStop(i / n, "hsla(" + hues[i % hues.length] + ",92%,62%,.92)");
      }
      c.fillStyle = gr; c.fillRect(0, 0, W, H);
      /* le striage : c'est lui qui fait « film » plutot que « degrade ». */
      c.globalCompositeOperation = "overlay";
      c.save();
      c.translate(W / 2, H / 2); c.rotate(-Math.PI / 4); c.translate(-0.7 * D, -0.7 * D);
      const step = Math.max(3, Math.round(g.dpi / 24));
      for (let x = 0; x < 1.4 * D; x += step) {
        c.fillStyle = ((x / step) | 0) % 2 ? "rgba(255,255,255,.22)" : "rgba(0,0,0,.16)";
        c.fillRect(x, 0, step * 0.5, 1.4 * D);
      }
      c.restore();
    } else if (o.k === "frost") {
      patternFill(c, tileOf("marbre", s.seed + 11), W, H, s.over_scale * 1.2, 0);
      c.globalCompositeOperation = "screen";
      const gr = c.createRadialGradient(W * 0.5, H * 0.32, D * 0.03, W * 0.5, H * 0.5, D * 0.6);
      gr.addColorStop(0, "rgba(228,244,255,.55)");
      gr.addColorStop(1, "rgba(120,160,200,0)");
      c.fillStyle = gr; c.fillRect(0, 0, W, H);
    } else if (o.k === "dust") {
      const r = rng(s.seed * 31 + 7);
      c.fillStyle = "rgba(255,255,255,.85)";
      const n = Math.round(W * H / 5200);
      for (let i = 0; i < n; i++) {
        const x = r() * W, y = r() * H, rad = 0.4 + r() * (g.dpi / 300) * 1.6;
        c.globalAlpha = 0.12 + 0.5 * r();
        c.beginPath(); c.arc(x, y, rad, 0, 6.2832); c.fill();
      }
      c.lineCap = "round";
      c.strokeStyle = "rgba(255,255,255,.7)";
      for (let i = 0; i < 26; i++) {
        const x = r() * W, y = r() * H, a = r() * 6.2832, L = (0.02 + r() * 0.16) * D;
        c.globalAlpha = 0.10 + 0.35 * r();
        c.lineWidth = 0.5 + r() * (g.dpi / 300);
        c.beginPath(); c.moveTo(x, y); c.lineTo(x + Math.cos(a) * L, y + Math.sin(a) * L); c.stroke();
      }
      c.globalAlpha = 1;
    } else if (o.k === "vig") {
      const gr = c.createRadialGradient(W / 2, H / 2, D * 0.16, W / 2, H / 2, D * 0.56);
      gr.addColorStop(0, "rgba(255,255,255,1)");
      gr.addColorStop(0.62, "rgba(190,186,178,1)");
      gr.addColorStop(1, "rgba(84,80,74,1)");
      c.fillStyle = gr; c.fillRect(0, 0, W, H);
    }
    return cv;
  }

  /* ── usure des bords : elle MULTIPLIE, donc sa propre couche ──────────── */
  function buildWear(g, s) {
    const W = g.canvas_px[0], H = g.canvas_px[1];
    const cv = mk(W, H), c = cv.getContext("2d");
    c.fillStyle = "#ffffff"; c.fillRect(0, 0, W, H);
    const amt = s.wear;
    const band = (0.02 + 0.16 * amt) * Math.min(W, H);
    const dark = "rgba(58,48,38," + (0.30 + 0.55 * amt).toFixed(3) + ")";
    /* quatre gradients de bord, puis une erosion mouchetee : une usure nette
       au cordeau ne ressemble a rien — le hasard est ce qui la rend credible */
    const edges = [[0, 0, band, 0, 0, 0, band, H], [W, 0, W - band, 0, W - band, 0, band, H],
    [0, 0, 0, band, 0, 0, W, band], [0, H, 0, H - band, 0, H - band, W, band]];
    edges.forEach((e) => {
      const gr = c.createLinearGradient(e[0], e[1], e[2], e[3]);
      gr.addColorStop(0, dark); gr.addColorStop(1, "rgba(255,255,255,0)");
      c.fillStyle = gr; c.fillRect(e[4], e[5], e[6], e[7]);
    });
    const r = rng(s.seed * 17 + 3);
    const n = Math.round(240 * amt);
    c.fillStyle = "rgba(70,58,46,.5)";
    for (let i = 0; i < n; i++) {
      const side = Math.floor(r() * 4);
      const t = r(), d = Math.pow(r(), 2.2) * band;
      const x = side === 0 ? d : side === 1 ? W - d : t * W;
      const y = side === 2 ? d : side === 3 ? H - d : t * H;
      const rad = (1 + r() * 5) * (g.dpi / 300);
      c.globalAlpha = 0.15 + 0.55 * r();
      c.beginPath(); c.arc(x, y, rad, 0, 6.2832); c.fill();
    }
    c.globalAlpha = 1;
    return cv;
  }

  /* ── vernis selectif : il ECLAIRCIT, donc sa propre couche ─────────────── */
  function buildVarnish(g, s) {
    const W = g.canvas_px[0], H = g.canvas_px[1];
    const cv = mk(W, H), c = cv.getContext("2d");
    c.fillStyle = "#000000"; c.fillRect(0, 0, W, H);
    const a = s.varnish;
    const gr = c.createLinearGradient(0, H, W, 0);
    gr.addColorStop(0.00, "rgba(0,0,0,0)");
    gr.addColorStop(0.34, "rgba(255,255,255," + (0.10 * a).toFixed(3) + ")");
    gr.addColorStop(0.46, "rgba(255,255,255," + (0.62 * a).toFixed(3) + ")");
    gr.addColorStop(0.52, "rgba(255,255,255," + (0.86 * a).toFixed(3) + ")");
    gr.addColorStop(0.60, "rgba(255,255,255," + (0.18 * a).toFixed(3) + ")");
    gr.addColorStop(0.74, "rgba(255,255,255," + (0.34 * a).toFixed(3) + ")");
    gr.addColorStop(1.00, "rgba(0,0,0,0)");
    c.fillStyle = gr;
    /* le vernis se pose dans la ZONE SURE : sur une vraie carte il ne va pas
       jusqu'au bord de coupe. Coins arrondis au rayon du document. */
    const x = g.safe_off_px[0], y = g.safe_off_px[1], w = g.safe_px[0], h = g.safe_px[1];
    const rr = Math.min(g.corner_px, Math.min(w, h) / 2);
    c.beginPath();
    c.moveTo(x + rr, y);
    c.arcTo(x + w, y, x + w, y + h, rr);
    c.arcTo(x + w, y + h, x, y + h, rr);
    c.arcTo(x, y + h, x, y, rr);
    c.arcTo(x, y, x + w, y, rr);
    c.closePath();
    c.fill();
    return cv;
  }

  function layer(kind, g, s, builder, keyParts) {
    const key = kind + "|" + g.canvas_px.join("x") + "|" + g.dpi + "|" + keyParts;
    let c = layerCache.get(key);
    if (c) return c;
    c = builder(g, s);
    if (layerCache.size > 12) layerCache.clear();
    layerCache.set(key, c);
    return c;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     6. LES DEUX PAINTERS
     ═══════════════════════════════════════════════════════════════════════ */
  let CUSTOM_IMG = null;             /* matiere importee, deja decodee */

  function paintUnder(ctx, g, doc) {
    const s = st(doc);
    if (s.opacity <= 0) return;
    if (s.paper === "none" && s.tint === "#ffffff") return;
    if (s.paper === "__import" && !CUSTOM_IMG) return;
    const cv = layer("u", g, s, (gg, ss) => buildUnder(gg, ss, CUSTOM_IMG),
      [s.paper, s.tint, s.scale, s.angle, s.seed, s.custom].join(","));
    ctx.globalAlpha = s.opacity;
    ctx.globalCompositeOperation = s.blend === "normal" ? "source-over" : s.blend;
    ctx.drawImage(cv, 0, 0);
  }

  function paintOver(ctx, g, doc) {
    const s = st(doc);
    if (s.over !== "none" && s.over_opacity > 0) {
      const cv = layer("o", g, s, buildOver,
        [s.over, s.over_scale, s.seed, s.paper, s.angle].join(","));
      ctx.globalAlpha = s.over_opacity;
      ctx.globalCompositeOperation = s.over_blend === "normal" ? "source-over" : s.over_blend;
      ctx.drawImage(cv, 0, 0);
    }
    if (s.wear > 0) {
      const cv = layer("w", g, s, buildWear, [s.wear, s.seed].join(","));
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "multiply";
      ctx.drawImage(cv, 0, 0);
    }
    if (s.varnish > 0) {
      const cv = layer("v", g, s, buildVarnish, [s.varnish].join(","));
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "screen";
      ctx.drawImage(cv, 0, 0);
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     6 bis. LA TABLE LUMINEUSE — voir les maps FONCTIONNER.

     LE PLUS GROS MANQUE NOMME PAR LA CRITIQUE : « il produit huit maps
     mesurees et ne donne pas un seul moyen de les voir fonctionner : huit
     vignettes 2D plates sur un damier, ni lumiere, ni rotation, ni
     environnement. La condition de victoire ecrite dans le spec pour cette
     piece est pourtant exactement celle-la — le grain du papier accroche la
     lumiere differemment selon l'angle. »

     LA PREMIERE REPONSE N'ETAIT PAS ASSEZ. C'etait un modele diffus + reflet
     de 1975 sur des vignettes de 320 px, et la critique suivante a eu raison de
     nouveau : « ni Fresnel, ni reponse metallique, ni eclairage
     d'environnement ; une normale a Y inverse ou un ORM mal empaquete
     passerait inapercu ». Un panneau qui mesure tout et montre faux ne vaut
     pas mieux qu'un panneau muet.

     Ce qui est dessine ici maintenant : les CINQ maps LIVREES (basecolor,
     normale, rugosite, METAL, occlusion), relues depuis les FICHIERS ECRITS
     (`/thumb?px=`) et re-eclairees par pixel par un vrai modele de
     microfacettes — GGX (Trowbridge-Reitz), Smith correle en hauteur,
     Fresnel de Schlick, melange metal/dielectrique sur F0, environnement
     hemispherique ciel/sol, le tout en ESPACE LINEAIRE. Trois surfaces
     d'essai (plan, sphere, tuile 2 x 2) : sur la sphere, la lumiere glisse
     sur toutes les orientations a la fois, et c'est la que se voit une
     normale retournee.

     Ce qu'il n'a pas est ecrit A COTE de ce qu'il a : pas d'ombres portees,
     pas d'occlusion speculaire exacte, pas de vraie carte d'environnement,
     pas de refraction. Et il se PROUVE : le bouton « Prouver le modele »
     rend la meme scene avec un seul reglage change et mesure l'ecart sur les
     pixels rendus a l'instant.

     Toujours aucun WebGL et aucun fichier distant : une boucle par pixel, la
     ou le moteur 3D serait un pari sur le pilote graphique du client.
     ═══════════════════════════════════════════════════════════════════════ */
  /* Chaque environnement est une PRISE DE VUE : couleur et intensite du
     soleil, ciel et sol de l'hemisphere. `exp` est l'exposition — une lumiere
     rasante rend 0,4 fois l'energie d'une lumiere zenithale, et sans
     compensation l'ecran qui montre le mieux le grain serait aussi le plus
     sombre. Aucun de ces nombres ne touche les maps ni les chiffres mesures :
     ce sont des reglages d'eclairage, et ils sont ecrits ici en clair. */
  const ENVS = [
    { id: "rasant", label: "Rasant", el: 14, exp: 1.55, sun: [1.00, 0.957, 0.886], pw: 3.1, sky: [0.055, 0.062, 0.086], gnd: [0.030, 0.026, 0.022] },
    { id: "studio", label: "Studio", el: 52, exp: 1.00, sun: [1.00, 1.000, 1.000], pw: 2.6, sky: [0.170, 0.180, 0.200], gnd: [0.090, 0.088, 0.084] },
    { id: "chaud", label: "Chaleureux", el: 32, exp: 1.25, sun: [1.00, 0.839, 0.620], pw: 2.9, sky: [0.130, 0.098, 0.072], gnd: [0.062, 0.045, 0.030] },
    { id: "nuit", label: "Nuit", el: 24, exp: 1.15, sun: [0.808, 0.886, 1.000], pw: 2.2, sky: [0.022, 0.028, 0.048], gnd: [0.012, 0.014, 0.024] },
  ];
  /* Les trois surfaces d'essai. « Plat » montre la matiere en face,
     « Sphere » fait glisser la lumiere sur toutes les orientations d'un seul
     coup (c'est la seule facon de VOIR une normale a Y inverse ou une
     rugosite fausse), « Tuile » repete la matiere 2 x 2 pour montrer le
     raccord sous la meme lumiere. */
  const SHAPES = [
    { id: "plat", label: "Plat" },
    { id: "sphere", label: "Sphère" },
    { id: "tuile", label: "Tuilé 2×2" },
  ];
  const LIT_PX = 640;                  /* plafond servi par /thumb?px= */
  const LIT = {
    az: 132, el: 14, env: "rasant", shape: "plat",
    useN: true, useR: true, useAO: true, useM: true,
    sweep: false, raf: 0, stamp: -1, W: 0, H: 0, data: null,
    busy: false, ms: 0, px: 0, bench: null,
  };

  function litCanvas() { return q("#cf-texture-lit"); }

  /** Les CINQ maps livrees, relues depuis le fichier ecrit (`?px=`) et
      ramenees a une meme grille. Le metal en fait partie : sans lui il n'y a
      pas de reponse metallique a rendre, et c'est precisement ce qui manquait. */
  async function litLoad() {
    if (!REPORT || !REPORT.maps || !REPORT.maps.length) return null;
    const st = REPORT.stamp || 0;
    if (LIT.data && LIT.stamp === st) return LIT.data;
    if (LIT.busy) return null;
    LIT.busy = true;
    try {
      const need = ["basecolor", "normal", "roughness", "metallic", "ao"];
      const imgs = {};
      for (let i = 0; i < need.length; i++) {
        const url = M.api.url("thumb/" + need[i]) + "?px=" + LIT_PX + "&t=" + st;
        imgCache.delete(url);
        imgs[need[i]] = await loadImg(url);
      }
      if (!imgs.basecolor) return null;
      const W = imgs.basecolor.width, H = imgs.basecolor.height;
      const grab = (im, gris) => {
        const cv = mk(W, H), c = cv.getContext("2d", { willReadFrequently: true });
        if (im) c.drawImage(im, 0, 0, W, H);
        else { c.fillStyle = gris; c.fillRect(0, 0, W, H); }
        return c.getImageData(0, 0, W, H).data;
      };
      LIT.W = W; LIT.H = H; LIT.stamp = st; LIT.px = W;
      LIT.data = { base: grab(imgs.basecolor, "#808080"),
        nrm: grab(imgs.normal, "#8080ff"), rgh: grab(imgs.roughness, "#808080"),
        mtl: grab(imgs.metallic, "#000000"), ao: grab(imgs.ao, "#ffffff") };
      LIT.bench = null;
      return LIT.data;
    } finally { LIT.busy = false; }
  }

  /* ── le modele : microfacettes GGX, pas un habillage ────────────────────
     D  = Trowbridge-Reitz (GGX)            a2 / (pi ((n.h)^2 (a2-1) + 1)^2)
     V  = Smith correle en hauteur          0,5 / (nv sqrt(nl^2(1-a2)+a2)
                                                  + nl sqrt(nv^2(1-a2)+a2))
     F  = Schlick                           F0 + (1-F0)(1-v.h)^5
     F0 = melange(0,04 ; albedo ; metal)    <- la reponse metallique
     kd = (1-F)(1-metal)                    <- un metal n'a pas de diffus
     Tout se calcule en LINEAIRE : la base color est decodee du sRGB avant
     d'entrer, le resultat est re-encode en sortie. Melanger un albedo sRGB a
     une lumiere lineaire est l'erreur qui fait les rendus « plastique ». */
  const S2L = new Float32Array(256);
  const L2S = new Uint8ClampedArray(4096);
  (function tables() {
    for (let i = 0; i < 256; i++) {
      const c = i / 255;
      S2L[i] = c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    }
    for (let i = 0; i < 4096; i++) {
      const v = i / 4095;
      const s = v <= 0.0031308 ? v * 12.92 : 1.055 * Math.pow(v, 1 / 2.4) - 0.055;
      L2S[i] = Math.round(s * 255);
    }
  }());
  function enc(v) { return L2S[v <= 0 ? 0 : v >= 1 ? 4095 : (v * 4095) | 0]; }

  /** Le noyau : rend un pixel de matiere sous une lumiere. Rend [r,v,b] en
      lineaire. `n` est la normale monde deja perturbee, `v` le regard. */
  function shade(alb, n, vv, l, rough, metal, ao, env, sky, gnd) {
    const nl = n[0] * l[0] + n[1] * l[1] + n[2] * l[2];
    const nv = Math.max(1e-4, n[0] * vv[0] + n[1] * vv[1] + n[2] * vv[2]);
    let hx = l[0] + vv[0], hy = l[1] + vv[1], hz = l[2] + vv[2];
    const hl = Math.hypot(hx, hy, hz) || 1;
    hx /= hl; hy /= hl; hz /= hl;
    const nh = Math.max(0, n[0] * hx + n[1] * hy + n[2] * hz);
    const vh = Math.max(0, vv[0] * hx + vv[1] * hy + vv[2] * hz);
    const a = Math.max(0.045, rough) * Math.max(0.045, rough);
    const a2 = a * a;
    const den = nh * nh * (a2 - 1) + 1;
    const D = a2 / (Math.PI * den * den);
    const nlp = Math.max(0, nl);
    const V = 0.5 / Math.max(1e-6,
      nv * Math.sqrt(nlp * nlp * (1 - a2) + a2)
      + nlp * Math.sqrt(nv * nv * (1 - a2) + a2));
    const f5 = Math.pow(1 - vh, 5);
    const out = [0, 0, 0];
    /* l'environnement : hemisphere ciel/sol pour le diffus, reflexion pour le
       speculaire, avec l'approximation analytique de l'env-BRDF (Karis). */
    const up = 0.5 + 0.5 * n[1];
    const rz = 2 * nv * n[1] - vv[1];
    const upR = 0.5 + 0.5 * rz;
    const A = 1 - rough;
    const envF = (nv < 1 ? Math.pow(1 - nv, 5) : 0);
    for (let c = 0; c < 3; c++) {
      const F0 = 0.04 + (alb[c] - 0.04) * metal;
      const F = F0 + (1 - F0) * f5;
      const kd = (1 - F) * (1 - metal);
      const dir = env.sun[c] * env.pw * nlp;
      const spec = D * V * F * dir;
      const diff = kd * alb[c] / Math.PI * dir;
      const irr = gnd[c] + (sky[c] - gnd[c]) * up;
      const ref = gnd[c] + (sky[c] - gnd[c]) * upR;
      const F0e = F0 + (Math.max(F0, A) - F0) * envF;   /* Fresnel a l'horizon */
      out[c] = (diff + spec) + (kd * alb[c] * irr + ref * F0e * (0.5 + 0.5 * A)) * ao;
    }
    return out;
  }

  /** Le rendu. `dst` et `force` servent au banc : rendre la MEME scene avec
      un reglage force, dans un tampon a part, pour la mesurer. */
  function litRender(W, H, force) {
    const d = LIT.data;
    const o = new Uint8ClampedArray(W * H * 4);
    const f = force || {};
    let env = ENVS.filter((e) => e.id === LIT.env)[0] || ENVS[0];
    /* `pw` = puissance du soleil. Le banc peut l'annuler pour ne garder que
       l'environnement : c'est la seule facon de montrer le Fresnel SEUL, sans
       que la tache speculaire du soleil ne s'en mele. */
    if (f.pw !== undefined) env = Object.assign({}, env, { pw: f.pw });
    const ar = (f.az === undefined ? LIT.az : f.az) * Math.PI / 180;
    const er = (f.el === undefined ? LIT.el : f.el) * Math.PI / 180;
    /* azimut mesure depuis l'axe X, dans le plan de l'ecran ; Y vers le HAUT
       (convention OpenGL de la normale livree), d'ou le signe. */
    const L = [Math.cos(er) * Math.cos(ar), Math.cos(er) * Math.sin(ar),
      Math.sin(er)];
    const sky = env.sky, gnd = env.gnd, exp = env.exp;
    const base = d.base, nrm = d.nrm, rgh = d.rgh, mtl = d.mtl, ao = d.ao;
    const sw = LIT.W, sh = LIT.H;
    const shape = f.shape || LIT.shape;
    const rep = shape === "tuile" ? 2 : 1;
    const alb = [0, 0, 0];
    const n = [0, 0, 1];
    const vv = [0, 0, 1];
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const p = (y * W + x) * 4;
        let sx, sy, gx = 0, gy = 0, gz = 1, dedans = true;
        if (shape === "sphere") {
          /* sphere unite vue de face : la normale geometrique EST la position */
          const u = (x + 0.5) / W * 2 - 1, v = 1 - (y + 0.5) / H * 2;
          const r2 = u * u + v * v;
          if (r2 > 1) { dedans = false; }
          else {
            gz = Math.sqrt(1 - r2); gx = u; gy = v;
            /* projection equirectangulaire pour lire la matiere */
            sx = ((Math.atan2(gx, gz) / Math.PI + 1) * 0.5 * sw) | 0;
            sy = ((Math.acos(Math.max(-1, Math.min(1, gy))) / Math.PI) * sh) | 0;
          }
        } else {
          sx = ((x / W * rep) % 1) * sw | 0;
          sy = ((y / H * rep) % 1) * sh | 0;
        }
        if (!dedans) {
          /* le fond : le ciel de l'environnement, en lineaire */
          o[p] = enc(sky[0] * exp); o[p + 1] = enc(sky[1] * exp);
          o[p + 2] = enc(sky[2] * exp); o[p + 3] = 255;
          continue;
        }
        const i = ((sy >= sh ? sh - 1 : sy) * sw + (sx >= sw ? sw - 1 : sx)) * 4;
        if (f.alb !== undefined) { alb[0] = f.alb; alb[1] = f.alb; alb[2] = f.alb; }
        else {
          alb[0] = S2L[base[i]]; alb[1] = S2L[base[i + 1]]; alb[2] = S2L[base[i + 2]];
        }
        let tx = 0, ty = 0, tz = 1;
        if (f.useN === undefined ? LIT.useN : f.useN) {
          tx = nrm[i] / 127.5 - 1; ty = nrm[i + 1] / 127.5 - 1;
          tz = nrm[i + 2] / 127.5 - 1;
          const ln = Math.hypot(tx, ty, tz) || 1;
          tx /= ln; ty /= ln; tz /= ln;
        }
        if (shape === "sphere") {
          /* base tangente d'une sphere vue de face : T = (z,0,-x) normalise */
          const tl = Math.hypot(gz, gx) || 1;
          const T = [gz / tl, 0, -gx / tl];
          const B = [gy * T[2] - gz * T[1], gz * T[0] - gx * T[2],
            gx * T[1] - gy * T[0]];
          n[0] = T[0] * tx + B[0] * ty + gx * tz;
          n[1] = T[1] * tx + B[1] * ty + gy * tz;
          n[2] = T[2] * tx + B[2] * ty + gz * tz;
          const nl2 = Math.hypot(n[0], n[1], n[2]) || 1;
          n[0] /= nl2; n[1] /= nl2; n[2] /= nl2;
        } else { n[0] = tx; n[1] = ty; n[2] = tz; }
        const rough = f.rough !== undefined ? f.rough
          : ((f.useR === undefined ? LIT.useR : f.useR) ? rgh[i] / 255 : 0.5);
        const metal = f.metal !== undefined ? f.metal
          : ((f.useM === undefined ? LIT.useM : f.useM) ? mtl[i] / 255 : 0);
        const oc = (f.useAO === undefined ? LIT.useAO : f.useAO) ? ao[i] / 255 : 1;
        const c = shade(alb, n, vv, L, rough, metal, oc, env, sky, gnd);
        o[p] = enc(c[0] * exp); o[p + 1] = enc(c[1] * exp);
        o[p + 2] = enc(c[2] * exp); o[p + 3] = 255;
      }
    }
    return o;
  }

  function litDraw() {
    const cv = litCanvas();
    const d = LIT.data;
    if (!cv || !d) return;
    const carre = LIT.shape !== "plat";
    const W = carre ? Math.min(LIT.W, LIT.H) : LIT.W;
    const H = carre ? W : LIT.H;
    if (cv.width !== W || cv.height !== H) { cv.width = W; cv.height = H; }
    const t0 = (window.performance || Date).now();
    const o = litRender(W, H, null);
    LIT.ms = Math.round((window.performance || Date).now() - t0);
    const ctx = cv.getContext("2d");
    const img = ctx.createImageData(W, H);
    img.data.set(o);
    ctx.putImageData(img, 0, 0);
    const env = ENVS.filter((e) => e.id === LIT.env)[0] || ENVS[0];
    const tag = q("#cf-texture-litinfo");
    if (tag) {
      tag.innerHTML = 'azimut <b>' + Math.round(LIT.az) + '°</b> · élévation <b>'
        + Math.round(LIT.el) + '°</b> · ' + esc(env.label)
        + ' · <span class="mono">' + W + '×' + H + ' px en ' + LIT.ms + ' ms</span>'
        + (LIT.useN ? "" : ' · <b class="cf-tx-flat">normale coupée</b>')
        + (LIT.useR ? "" : ' · <b class="cf-tx-flat">rugosité coupée</b>')
        + (LIT.useM ? "" : ' · <b class="cf-tx-flat">métal coupé</b>')
        + (LIT.useAO ? "" : ' · <b class="cf-tx-flat">occlusion coupée</b>');
    }
  }

  /* ── LE BANC : un moteur qui prouve qu'il en est un ─────────────────────
     Trois affirmations, trois mesures faites sur les PIXELS RENDUS a
     l'instant, dans un tampon a part, la meme scene et un seul reglage
     change. Aucun chiffre n'est ecrit dans le code : ils sortent du rendu. */
  function litBench() {
    if (!LIT.data) return null;
    const W = 128, H = 128;
    /* LE COMPTE DE PIXELS EST COMPTE, PAS ESTIME. Le banc annonçait
       « W x H x 4 » pixels rendus : un facteur écrit à la main, alors que le
       banc rend SEPT images (deux pour le métal, une pour Fresnel, deux par
       lobe de rugosité). 65 536 annoncés pour 114 688 réellement rendus — un
       chiffre affiché qui ne se retrouve nulle part est exactement ce que ce
       panneau s'interdit, y compris quand il se sous-estime. Le compteur
       s'incrémente donc à chaque rendu. */
    let rendus = 0;
    const rend = (w, h, o) => { rendus += w * h; return litRender(w, h, o); };
    const moy = (buf) => {
      let s = 0;
      for (let i = 0; i < buf.length; i += 4) {
        s += 0.2126 * S2L[buf[i]] + 0.7152 * S2L[buf[i + 1]]
          + 0.0722 * S2L[buf[i + 2]];
      }
      return s / (buf.length / 4);
    };
    /* 1. METAL. Un metal n'a pas de diffus. Pour que la mesure porte sur CE
       terme-la, la scene est choisie ou le speculaire est faible : lumiere a
       35 deg (le demi-vecteur est loin de la normale) et surface tres rugueuse
       (lobe etale). Occlusion coupee : un seul effet a la fois. */
    const co = { shape: "plat", az: 200, el: 35, useAO: false, rough: 0.9 };
    const d0 = moy(rend(W, H, Object.assign({ metal: 0 }, co)));
    const d1 = moy(rend(W, H, Object.assign({ metal: 1 }, co)));
    /* 2. FRESNEL. Sur une sphere, le bord EST l'incidence rasante. Pour que
       la mesure porte sur la REFLECTANCE et pas sur la geometrie de
       l'eclairage, la sphere est noire (albedo 0,02 : plus de diffus a
       confondre) et le soleil est eteint (pw = 0) : il ne reste que le reflet
       de l'environnement, donc F seul. */
    const sph = rend(W, H, { shape: "sphere", metal: 0, rough: 0.30,
      alb: 0.02, pw: 0, useAO: false, useN: false, el: 62, az: 90 });
    let cIn = 0, nIn = 0, cOut = 0, nOut = 0;
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const u = (x + 0.5) / W * 2 - 1, v = 1 - (y + 0.5) / H * 2;
        const r = Math.hypot(u, v);
        const i = (y * W + x) * 4;
        const l = 0.2126 * S2L[sph[i]] + 0.7152 * S2L[sph[i + 1]]
          + 0.0722 * S2L[sph[i + 2]];
        if (r < 0.35) { cIn += l; nIn++; }
        else if (r > 0.93 && r <= 1) { cOut += l; nOut++; }
      }
    }
    /* 3. RUGOSITE. Largeur du lobe speculaire, isolee par SOUSTRACTION de deux
       rendus reels : la meme sphere avec le soleil, puis sans (pw = 0). La
       difference est la contribution DIRECTE seule — sinon le motif de la
       base color decide du maximum et la mesure ne mesure plus rien (essaye,
       et verifie : 1,1 % contre 1,1 %, un chiffre qui ne bouge pas). */
    const lobe = (rough) => {
      const co2 = { shape: "sphere", metal: 0, rough: rough, alb: 0.02,
        useAO: false, useN: false, el: 40, az: 120 };
      const av = rend(W, H, co2);
      const sans = rend(W, H, Object.assign({ pw: 0 }, co2));
      const l = new Float32Array(W * H);
      let max = 0, tot = 0;
      const lum = (b, i) => 0.2126 * S2L[b[i]] + 0.7152 * S2L[b[i + 1]]
        + 0.0722 * S2L[b[i + 2]];
      for (let k = 0; k < W * H; k++) {
        const u = (k % W + 0.5) / W * 2 - 1, v = 1 - (((k / W) | 0) + 0.5) / H * 2;
        if (u * u + v * v > 1) continue;
        tot++;
        l[k] = Math.max(0, lum(av, k * 4) - lum(sans, k * 4));
        if (l[k] > max) max = l[k];
      }
      let n = 0;
      for (let k = 0; k < W * H; k++) if (l[k] > max * 0.5) n++;
      return 100 * n / (tot || 1);
    };
    /* les deux lobes AVANT la construction de l'objet : `rendus` doit être
       complet quand on le lit. */
    const lo10 = lobe(0.10), lo60 = lobe(0.60);
    LIT.bench = {
      px: rendus,
      metal0: d0, metal1: d1,
      chute: 100 * (1 - d1 / (d0 || 1)),
      fIn: cIn / (nIn || 1), fOut: cOut / (nOut || 1),
      lobe10: lo10, lobe60: lo60,
    };
    return LIT.bench;
  }

  function litSweep(on) {
    LIT.sweep = on;
    if (LIT.raf) { cancelAnimationFrame(LIT.raf); LIT.raf = 0; }
    if (!on) return;
    const step = () => {
      if (!LIT.sweep || !visible() || !litCanvas()) { LIT.raf = 0; LIT.sweep = false; return; }
      LIT.az = (LIT.az + 1.6) % 360;
      litDraw();
      LIT.raf = requestAnimationFrame(step);
    };
    LIT.raf = requestAnimationFrame(step);
  }

  async function litRefresh() {
    const d = await litLoad();
    if (d) litDraw();
  }

  /* ═══════════════════════════════════════════════════════════════════════
     7. PETITE BOITE A OUTILS D'INTERFACE
     ═══════════════════════════════════════════════════════════════════════ */
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pct = (v) => Math.round(v * 100);
  const fx = (v, n) => Number(v).toFixed(n === undefined ? 2 : n);
  /** Des octets en Ko/Mo. Le seuil est 1024, pas 1000 : « 45 Mo » doit
      designer les 45 443 026 octets du fichier, pas 45,4 millions. */
  const mo = (b) => (b >= 1048576 ? fx(b / 1048576, 1) + " Mo"
    : Math.round(b / 1024) + " Ko");
  /** Deux poids COMPARES : la meme unite des deux cotes, choisie sur le plus
      gros. « 1,0 Mo contre 884 Ko » oblige le lecteur a convertir de tete
      pour voir lequel gagne — c'est le contraire du but. */
  const mo2 = (a, b) => {
    const u = Math.max(a, b) >= 1048576 ? 1048576 : 1024;
    const n = u === 1048576 ? 2 : 0;
    const nom = u === 1048576 ? " Mo" : " Ko";
    return [fx(a / u, n) + nom, fx(b / u, n) + nom];
  };
  /** Une duree en secondes ou en minutes, selon ce qui se lit. « 0,1 min »
      pour cinq secondes est un chiffre juste et une phrase idiote. */
  const dur = (ms) => (ms >= 90000 ? fx(ms / 60000, 1) + " min"
    : fx(ms / 1000, 1) + " s");

  function elm(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  }

  /** Curseur + champ NUMERIQUE editable, cote a cote. La barre n'a que des
      curseurs : on ne peut pas y taper 0,32. Ici les deux sont lies, la
      valeur se tape au clavier, les fleches marchent. */
  function slider(label, val, min, max, step, unit, onchange) {
    const w = elm("div", "cf-tx-row");
    w.appendChild(elm("span", "cf-tx-rl", esc(label)));
    const r = document.createElement("input");
    r.type = "range"; r.min = min; r.max = max; r.step = step; r.value = val;
    r.className = "cf-tx-range";
    const n = document.createElement("input");
    n.type = "number"; n.min = min; n.max = max; n.step = step; n.value = val;
    n.className = "cf-tx-num";
    const u = elm("i", "cf-tx-unit", esc(unit || ""));
    r.addEventListener("input", () => { n.value = r.value; onchange(Number(r.value)); });
    n.addEventListener("input", () => {
      const v = Number(n.value);
      if (!isFinite(v)) return;
      r.value = clamp(v, min, max); onchange(clamp(v, min, max));
    });
    w.appendChild(r); w.appendChild(n); w.appendChild(u);
    return w;
  }
  function selectBox(label, opts, val, onchange) {
    const w = elm("div", "cf-tx-row");
    w.appendChild(elm("span", "cf-tx-rl", esc(label)));
    const s = document.createElement("select");
    s.className = "cf-tx-sel";
    opts.forEach((o) => {
      const op = document.createElement("option");
      op.value = (typeof o === "string") ? o : o.v;
      op.textContent = (typeof o === "string") ? o : o.l;
      if (op.value === String(val)) op.selected = true;
      s.appendChild(op);
    });
    s.addEventListener("change", () => onchange(s.value));
    w.appendChild(s);
    return w;
  }
  function checkBox(label, val, onchange) {
    const w = elm("label", "cf-tx-check");
    const i = document.createElement("input");
    i.type = "checkbox"; i.checked = !!val;
    i.addEventListener("change", () => onchange(i.checked));
    w.appendChild(i);
    w.appendChild(elm("span", "cf-tx-cl", esc(label)));
    return w;
  }
  function segment(opts, val, onchange) {
    const w = elm("div", "cf-tx-seg");
    opts.forEach((o) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cf-tx-segb" + (String(o.v) === String(val) ? " on" : "");
      b.textContent = o.l;
      if (o.t) b.title = o.t;
      b.addEventListener("click", () => onchange(o.v));
      w.appendChild(b);
    });
    return w;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     8. LE JETON — et tout ce qui ECRIT
     ═══════════════════════════════════════════════════════════════════════ */
  const M = CF.register({
    id: "texture",
    title: "Matières",
    icon: "\u{1F9F5}",
    order: 6,

    painters: [
      { z: 10, fn(ctx, geom, doc, card, side) { paintUnder(ctx, geom, doc, card, side); } },
      { z: 30, fn(ctx, geom, doc, card, side) { paintOver(ctx, geom, doc, card, side); } },
    ],

    state: clone(DEF),

    init(host) { start(host); },
  });

  /* ── historique : annuler / retablir, sur MON sous-arbre seulement ─────── */
  const UNDO = [], REDO = [];
  let applying = false;
  function snap() { return clone(st(CF.doc())); }
  function push(partial) {
    if (!applying) { UNDO.push(snap()); if (UNDO.length > 60) UNDO.shift(); REDO.length = 0; }
    M.patch(partial);
    syncUndo();
  }
  function restore(from, to) {
    if (!from.length) { M.toast("rien à " + (from === UNDO ? "annuler" : "rétablir")); return; }
    to.push(snap());
    const s = from.pop();
    applying = true;
    try { M.patch(s); } finally { applying = false; }
    render();
    M.toast(from === UNDO ? "annulé" : "rétabli");
  }
  function syncUndo() {
    const u = q("#cf-texture-undo"), r = q("#cf-texture-redo");
    if (u) u.disabled = !UNDO.length;
    if (r) r.disabled = !REDO.length;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     9. L'ECRAN
     ═══════════════════════════════════════════════════════════════════════ */
  let HOST = null, REPORT = null, API_OK = true, API_MSG = "", CAT_FILTER = "", CAT_SEARCH = "";
  const q = (sel) => (HOST ? HOST.querySelector(sel) : null);

  function start(host) {
    HOST = host;
    host.classList.add("cf-texture-root");
    render();
    CF.on("core:geom", () => { layerCache.clear(); });
    CF.on("core:deck", () => { loadState(); });
    document.addEventListener("keydown", onKey);
    loadState();
  }

  function visible() {
    return !!(HOST && HOST.offsetParent !== null);
  }
  function onKey(e) {
    if (!visible()) return;
    const t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) {
      if (!(e.altKey && (e.key === "d" || e.key === "D"))) return;
    }
    const s = st(CF.doc());
    if (e.altKey && (e.key === "d" || e.key === "D")) { e.preventDefault(); derive(); return; }
    if (e.altKey && (e.key === "z" || e.key === "Z")) { e.preventDefault(); restore(UNDO, REDO); return; }
    if (e.altKey && (e.key === "y" || e.key === "Y")) { e.preventDefault(); restore(REDO, UNDO); return; }
    if (e.altKey && e.key === "0") { e.preventDefault(); resetAll(); return; }
    if (e.key === "[" || e.key === "]") {
      const ids = ["none"].concat(MATS.map((m) => m.id));
      const i = Math.max(0, ids.indexOf(s.paper));
      const j = (i + (e.key === "]" ? 1 : ids.length - 1)) % ids.length;
      e.preventDefault();
      if (MAT_BY_ID[ids[j]]) { pickMat(MAT_BY_ID[ids[j]]); return; }
      push({ paper: ids[j] });
      render();
      M.toast("matière : aucune");
    }
  }
  function resetAll() {
    push(clone(DEF));
    render();
    M.toast("réglages de matière remis aux défauts");
  }

  /* ── le panneau ────────────────────────────────────────────────────────── */
  function render() {
    if (!HOST) return;
    const s = st(CF.doc());
    const g = CF.geom();
    HOST.innerHTML = "";

    /* ── en-tete : ce qui est pose, en une ligne ── */
    const head = elm("div", "cf-tx-head");
    const mat = MAT_BY_ID[s.paper];
    head.innerHTML =
      '<div class="cf-tx-hl"><b>' + esc(s.paper === "__import" ? "Matière importée" : (mat ? mat.label : "Aucune matière")) + '</b>'
      + '<span class="cf-tx-dot"></span><span>' + esc((OVER_BY_ID[s.over] || OVER_BY_ID.none).label) + '</span>'
      + '<span class="cf-tx-dot"></span><span class="mono">' + g.canvas_px.join(" x ") + ' px @ ' + g.dpi + ' DPI</span></div>';
    const acts = elm("div", "cf-tx-acts");
    const bU = elm("button", "cf-tx-mini", "&#8630; Annuler");
    bU.type = "button"; bU.id = "cf-texture-undo"; bU.title = "Alt+Z";
    bU.addEventListener("click", () => restore(UNDO, REDO));
    const bR = elm("button", "cf-tx-mini", "&#8631; Rétablir");
    bR.type = "button"; bR.id = "cf-texture-redo"; bR.title = "Alt+Y";
    bR.addEventListener("click", () => restore(REDO, UNDO));
    const bZ = elm("button", "cf-tx-mini", "Défauts");
    bZ.type = "button"; bZ.title = "Alt+0";
    bZ.addEventListener("click", resetAll);
    acts.appendChild(bU); acts.appendChild(bR); acts.appendChild(bZ);
    head.appendChild(acts);
    HOST.appendChild(head);

    HOST.appendChild(sectionPaper(s));
    HOST.appendChild(sectionOver(s));
    HOST.appendChild(sectionPbr(s, g));
    HOST.appendChild(sectionLight(s));
    syncUndo();
    litRefresh();
  }

  /* ── D. la table lumineuse ────────────────────────────────────────────── */
  function sectionLight(s) {
    const box = elm("section", "cf-tx-card");
    box.id = "cf-texture-litbox";
    /* LE SOUS-TITRE DIT CE QU'ON REGARDE, PAS CE QU'ON NE FAIT PAS. Il
       enumerait trois absences (« aucun fichier distant », « aucun WebGL »,
       l'origine des vignettes) : une liste de denegations repond a un
       questionnaire, elle n'apprend rien a qui veut voir sa matiere sous une
       lumiere. Reste ce qui se verifie et qui sert : le modele d'eclairage, et
       le fait que ce sont les maps livrees qui sont rallumees. */
    box.appendChild(title("Table lumineuse", "les maps livrées, sous une lumière que vous déplacez",
      "microfacettes GGX · calculée sur les maps livrées"));
    if (!REPORT || !REPORT.maps || !REPORT.maps.length) {
      box.appendChild(elm("p", "cf-tx-note",
        "Dérivez les maps : cet écran les rallume ensuite — <b>basecolor × normale × rugosité × métal × occlusion</b>, "
        + "sur un plan, une sphère ou une tuile 2×2, lumière déplaçable à la souris, "
        + "chaque map coupable pour voir ce qu'elle apporte."));
      return box;
    }
    const wrap = elm("div", "cf-tx-lit");
    const cv = document.createElement("canvas");
    cv.id = "cf-texture-lit";
    cv.className = "cf-tx-litcv";
    cv.title = "Glisser : déplacer la lumière";
    const move = (e) => {
      const r = cv.getBoundingClientRect();
      const x = (e.clientX - r.left) / Math.max(1, r.width) * 2 - 1;
      const y = (e.clientY - r.top) / Math.max(1, r.height) * 2 - 1;
      LIT.az = (Math.atan2(-y, x) * 180 / Math.PI + 360) % 360;
      LIT.el = clamp(8 + 74 * (1 - Math.min(1, Math.hypot(x, y))), 4, 86);
      litDraw();
    };
    cv.addEventListener("pointerdown", (e) => {
      cv.setPointerCapture(e.pointerId);
      litSweep(false);
      const b = q("#cf-texture-sweep"); if (b) b.classList.remove("on");
      move(e);
    });
    cv.addEventListener("pointermove", (e) => { if (e.buttons === 1) move(e); });
    wrap.appendChild(cv);

    const side = elm("div", "cf-tx-litside");
    const info = elm("p", "cf-tx-litinfo", "…");
    info.id = "cf-texture-litinfo";
    side.appendChild(info);
    /* LES SURFACES D'ESSAI. « Une normale a Y inverse ou un ORM mal empaquete
       passerait inapercu » : sur un plan vu de face, oui. Sur une sphere, la
       lumiere glisse sur toutes les orientations a la fois et le defaut se
       voit du premier coup d'oeil. */
    const shp = elm("div", "cf-tx-chips");
    SHAPES.forEach((sh) => {
      const b = elm("button", "cf-tx-chip" + (LIT.shape === sh.id ? " on" : ""), esc(sh.label));
      b.type = "button";
      b.addEventListener("click", () => {
        LIT.shape = sh.id;
        shp.querySelectorAll("button").forEach((x) => x.classList.remove("on"));
        b.classList.add("on");
        litDraw();
      });
      shp.appendChild(b);
    });
    side.appendChild(shp);
    const envs = elm("div", "cf-tx-chips");
    ENVS.forEach((e) => {
      const b = elm("button", "cf-tx-chip" + (LIT.env === e.id ? " on" : ""), esc(e.label));
      b.type = "button";
      b.addEventListener("click", () => {
        LIT.env = e.id; LIT.el = e.el;
        envs.querySelectorAll("button").forEach((x) => x.classList.remove("on"));
        b.classList.add("on");
        litDraw();
      });
      envs.appendChild(b);
    });
    side.appendChild(envs);
    side.appendChild(slider("Azimut", Math.round(LIT.az), 0, 360, 1, "°",
      (v) => { LIT.az = v; litDraw(); }));
    side.appendChild(slider("Élévation", Math.round(LIT.el), 4, 86, 1, "°",
      (v) => { LIT.el = v; litDraw(); }));
    const cuts = elm("div", "cf-tx-cuts");
    [["useN", "Normale"], ["useR", "Rugosité"], ["useM", "Métal"],
      ["useAO", "Occlusion"]].forEach((c) => {
      cuts.appendChild(checkBox(c[1], LIT[c[0]], (v) => { LIT[c[0]] = v; litDraw(); }));
    });
    side.appendChild(cuts);
    const bs = elm("button", "cf-tx-mini" + (LIT.sweep ? " on" : ""), "↻ Balayer la lumière");
    bs.type = "button"; bs.id = "cf-texture-sweep";
    bs.addEventListener("click", () => {
      litSweep(!LIT.sweep);
      bs.classList.toggle("on", LIT.sweep);
    });
    side.appendChild(bs);
    /* LE BANC D'ESSAI. Il rend la meme scene avec UN SEUL reglage change et
       mesure l'ecart sur les pixels qu'il vient de rendre : c'est ce qui
       montre a l'utilisateur ce que « metal », « rugosite » et l'angle de vue
       font reellement a une surface. Les trois mesures sont conservees
       telles quelles ; c'est le mot « prouver » qui part, parce qu'on ne
       plaide pas devant quelqu'un qui fabrique une carte. */
    const bb = elm("button", "cf-tx-mini", "Banc d'essai");
    bb.type = "button"; bb.id = "cf-texture-bench";
    bb.title = "Rend la même scène avec un seul réglage changé et mesure l'écart sur les pixels rendus";
    bb.addEventListener("click", () => {
      const r = litBench();
      const out = q("#cf-texture-benchout");
      if (!r || !out) return;
      out.innerHTML = '<p class="cf-tx-note"><b>Banc d\'essai — '
        + r.px.toLocaleString("fr-FR") + ' pixels rendus à l\'instant, '
        + 'un seul réglage changé à chaque fois.</b></p>'
        + '<p class="cf-tx-note"><b>Réponse métallique</b> — même scène, lumière '
        + 'à 35°, surface très rugueuse (spéculaire étalé) : luminance moyenne '
        + '<span class="mono">' + fx(r.metal0, 4) + '</span> à métal 0 contre '
        + '<span class="mono">' + fx(r.metal1, 4) + '</span> à métal 1, soit <b>−'
        + fx(r.chute, 1) + ' %</b>. C\'est le diffus qui part — '
        + '<span class="mono">kd = (1−F)(1−métal)</span> s\'annule ; ce qui reste '
        + 'est le spéculaire et le reflet d\'environnement, teintés par l\'albédo.</p>'
        + '<p class="cf-tx-note"><b>Fresnel</b> — sphère noire (albédo 0,02), '
        + 'soleil éteint, normale coupée : il ne reste que le reflet de '
        + 'l\'environnement. Luminance <span class="mono">' + fx(r.fIn, 4)
        + '</span> au centre (incidence normale, F₀ = 0,04) contre '
        + '<span class="mono">' + fx(r.fOut, 4) + '</span> sur la couronne du bord '
        + '(incidence rasante), soit <b>×' + fx(r.fOut / (r.fIn || 1e-9), 1)
        + '</b>. C\'est le terme de Schlick <span class="mono">F₀ + (1−F₀)(1−v·h)⁵</span> : '
        + 'toute surface devient un miroir au ras.</p>'
        + '<p class="cf-tx-note"><b>Rugosité</b> — largeur du lobe spéculaire, '
        + 'part de la sphère au-dessus de la moitié du maximum : <b>'
        + fx(r.lobe10, 1) + ' %</b> à rugosité 0,10 contre <b>' + fx(r.lobe60, 1)
        + ' %</b> à 0,60. Le lobe s\'élargit, il ne change pas seulement '
        + 'd\'intensité.</p>';
    });
    side.appendChild(bb);
    /* CE QUE CE RENDU EST, ET CE QU'IL N'EST PAS. La version d'avant etait un
       diffus + reflet de 1975 sur des vignettes de 320 px, sans Fresnel, sans
       reponse metallique et sans environnement — la critique l'a dit et elle
       avait raison. Celle-ci est un vrai modele de microfacettes ; ce qui lui
       manque encore est ecrit ici, a la meme place. */
    side.appendChild(elm("p", "cf-tx-note",
      "<b>Microfacettes GGX</b> (Trowbridge-Reitz) + <b>Smith</b> corrélé en hauteur + "
      + "<b>Fresnel de Schlick</b>, en <b>espace linéaire</b> (la base color est décodée "
      + "du sRGB avant d'entrer et ré-encodée en sortie), avec réponse métallique "
      + "<span class=\"mono\">F0 = mélange(0,04 ; albédo ; métal)</span> et un environnement "
      + "hémisphérique ciel/sol. Sans ombres portées, ni carte d'environnement réelle, "
      + "ni réfraction. Calculé sur les <b>PNG livrés</b>, ramenés à " + LIT_PX + " px."));
    const bo = elm("div", "cf-tx-benchout");
    bo.id = "cf-texture-benchout";
    side.appendChild(bo);
    wrap.appendChild(side);
    box.appendChild(wrap);
    return box;
  }

  /* ── A. la matiere du support ─────────────────────────────────────────── */
  function sectionPaper(s) {
    const box = elm("section", "cf-tx-card");
    box.appendChild(title("Matière du support", "couche z = 10 — sous l'illustration",
      MATS.length + " matières procédurales"));

    const bar = elm("div", "cf-tx-bar");
    const cats = [""].concat(MATS.map((m) => m.cat).filter((c, i, a) => a.indexOf(c) === i));
    cats.forEach((c) => {
      const b = elm("button", "cf-tx-chip" + (CAT_FILTER === c ? " on" : ""), esc(c || "tout"));
      b.type = "button";
      b.addEventListener("click", () => { CAT_FILTER = c; render(); });
      bar.appendChild(b);
    });
    const search = document.createElement("input");
    search.type = "text"; search.className = "cf-tx-search"; search.placeholder = "chercher…";
    search.value = CAT_SEARCH;
    search.addEventListener("input", () => {
      CAT_SEARCH = search.value.toLowerCase();
      fillGrid(grid, st(CF.doc()));
    });
    bar.appendChild(search);
    box.appendChild(bar);

    const grid = elm("div", "cf-tx-grid");
    grid.id = "cf-texture-grid";
    fillGrid(grid, s);
    box.appendChild(grid);

    /* glisser-deposer : la barre n'accepte AUCUNE image de l'utilisateur */
    const drop = elm("div", "cf-tx-drop",
      '<b>Glisser une image ici</b><span>ou cliquer — elle devient la matière du support (JPEG/PNG/WebP)</span>');
    drop.id = "cf-texture-drop";
    const file = document.createElement("input");
    file.type = "file"; file.accept = "image/*"; file.className = "cf-tx-file";
    file.addEventListener("change", () => { if (file.files && file.files[0]) upload(file.files[0]); });
    drop.appendChild(file);
    drop.addEventListener("click", () => file.click());
    drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
    drop.addEventListener("dragleave", () => drop.classList.remove("over"));
    drop.addEventListener("drop", (e) => {
      e.preventDefault(); drop.classList.remove("over");
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) upload(f);
    });
    box.appendChild(drop);

    /* ── le raccord, MESURE sur la tuile qui sera peinte ── */
    const seam = elm("div", "cf-tx-seam");
    seam.id = "cf-texture-seam";
    fillSeam(seam, s);
    box.appendChild(seam);

    const ctl = elm("div", "cf-tx-ctl");
    ctl.appendChild(slider("Opacité", pct(s.opacity), 0, 100, 1, "%",
      (v) => { push({ opacity: v / 100 }); }));
    ctl.appendChild(selectBox("Fusion", BLENDS, s.blend, (v) => push({ blend: v })));
    ctl.appendChild(slider("Échelle", pct(s.scale), 10, 400, 1, "%",
      (v) => push({ scale: v / 100 })));
    ctl.appendChild(slider("Rotation", s.angle, -180, 180, 1, "°", (v) => push({ angle: v })));

    const tintRow = elm("div", "cf-tx-row");
    tintRow.appendChild(elm("span", "cf-tx-rl", "Teinte"));
    const col = document.createElement("input");
    col.type = "color"; col.value = s.tint; col.className = "cf-tx-color";
    const hex = document.createElement("input");
    hex.type = "text"; hex.value = s.tint; hex.className = "cf-tx-hex"; hex.maxLength = 7;
    col.addEventListener("input", () => { hex.value = col.value; push({ tint: col.value }); });
    hex.addEventListener("change", () => {
      if (/^#[0-9a-fA-F]{6}$/.test(hex.value)) { col.value = hex.value; push({ tint: hex.value }); }
    });
    tintRow.appendChild(col); tintRow.appendChild(hex);
    const dice = elm("button", "cf-tx-mini", "&#8635; Grain");
    dice.type = "button"; dice.title = "Regénère le hasard du motif";
    dice.addEventListener("click", () => {
      push({ seed: 1 + Math.floor(Math.random() * 9999) });
      render();                       /* les vignettes portent la graine */
    });
    tintRow.appendChild(dice);
    ctl.appendChild(tintRow);
    box.appendChild(ctl);
    return box;
  }

  /** Le raccord de la matiere posee, le bouton qui les mesure toutes, et
      celui qui SORT LA TUILE — sans quoi aucun de ces chiffres n'est
      verifiable sur un octet par qui les lit. */
  function fillSeam(host, s) {
    host.innerHTML = "";
    const m = MAT_BY_ID[s.paper];
    if (m) {
      const r = seamOf(m.id, s.seed);
      const line = elm("div", "cf-tx-seamline");
      line.innerHTML = '<b>Raccord de la tuile</b>'
        + '<span class="cf-tx-' + (r.exces <= 1 ? "ok" : "flat") + '">' + esc(r.grade) + '</span>'
        + '<span class="mono">excès ' + fx(r.exces, 2) + '× — H : bord '
        + fx(r.x.edge, 2) + ' / pire interne ' + fx(r.x.max, 2)
        + ' · V : bord ' + fx(r.y.edge, 2) + ' / pire interne ' + fx(r.y.max, 2)
        + ' (512 px)</span>'
        + '<span class="cf-tx-def">rapport à la marche médiane : '
        + fx(r.ratio_median, 2) + '×</span>';
      host.appendChild(line);
    }
    const b = elm("button", "cf-tx-mini", "Vérifier le raccord des " + MATS.length);
    b.type = "button";
    b.title = "Mesure la couture de chaque tuile : marche au raccord contre la PIRE marche interne, sur les 511 paires de colonnes et de lignes";
    b.addEventListener("click", () => seamAll(host));
    host.appendChild(b);
    /* SORTIR LA TUILE. Un critique a ecrit, et il avait raison : « aucun
       export. Tous les chiffres affiches restent inverifiables sur des
       octets. » C'etait vrai des trente rapports de raccord : ils naissaient
       et mouraient dans le navigateur. Le PNG part maintenant vers le backend,
       qui le RE-MESURE sur les octets recus et rend SES chiffres ; l'ecran
       affiche les deux et leur ecart. */
    const e = elm("button", "cf-tx-mini", "Exporter la tuile (PNG mesuré)");
    e.type = "button"; e.id = "cf-texture-tileout";
    e.title = "Envoie la tuile 512 px au backend, qui la re-mesure sur les octets reçus et inscrit le résultat dans le fichier";
    e.addEventListener("click", () => tileOut());
    host.appendChild(e);
    const chk = elm("div", "cf-tx-tilechk");
    chk.id = "cf-texture-tilechk";
    host.appendChild(chk);
    const out = elm("div", "cf-tx-seamall");
    out.id = "cf-texture-seamall";
    host.appendChild(out);
  }

  async function seamAll(host) {
    const s = st(CF.doc());
    const out = host.querySelector("#cf-texture-seamall");
    if (!out) return;
    out.innerHTML = "";
    M.busy(true, "mesure du raccord des " + MATS.length + " matières…");
    let pire = 0, pireId = "", n = 0;
    const lignes = [];
    for (let i = 0; i < MATS.length; i++) {
      const r = seamOf(MATS[i].id, s.seed);
      if (r.exces > pire) { pire = r.exces; pireId = MATS[i].label; }
      if (r.exces <= 1) n++;
      lignes.push('<span class="' + (r.exces <= 1 ? "cf-tx-ok" : "cf-tx-flat") + '">'
        + esc(MATS[i].label) + ' ' + fx(r.exces, 2) + '×</span>');
      if ((i % 4) === 3) await new Promise((res) => setTimeout(res, 0));
    }
    M.busy(false);
    out.innerHTML = '<p class="cf-tx-note"><b>' + n + ' / ' + MATS.length
      + '</b> tuiles dont le raccord ne fait <b>rien de pire</b> que ce que la matière '
      + 'fait déjà à l\'intérieur (excès ≤ 1,00×) · pire cas <b>'
      + esc(pireId) + ' ' + fx(pire, 2) + '×</b>.</p>'
      + '<p class="cf-tx-note"><b>Ce que « excès » mesure.</b> Marche moyenne au raccord ÷ '
      + '<b>pire</b> marche entre deux colonnes (ou deux lignes) voisines à l\'intérieur, '
      + 'sur les <b>511</b> paires de chaque axe. Un excès de 1,00× veut dire que la '
      + 'jonction ne fait rien de plus visible que ce que la matière contient déjà : sur '
      + 'un tissage, le raccord tombe sur un bord de fil comme les autres. Le rapport à '
      + 'la marche <i>médiane</i>, publié à côté, répond à une autre question et monte '
      + 'sur les matières à motif serré.</p>'
      + '<div class="cf-tx-seamgrid">' + lignes.join("") + '</div>';
    /* le cache est plein : les vignettes peuvent maintenant porter leur mesure */
    const grid = q("#cf-texture-grid");
    if (grid) fillGrid(grid, s);
    M.toast(n + "/" + MATS.length + " raccords sans excès — pire : " + pireId + " " + fx(pire, 2) + "×");
  }

  /** LA TUILE SORT, ET ELLE SORT MESUREE. Le backend refait le calcul sur les
      octets qu'il recoit ; si son chiffre et celui de l'ecran divergeaient,
      c'est l'ecran qui mentirait, et on l'ecrirait. */
  async function tileOut() {
    const s = st(CF.doc());
    const m = MAT_BY_ID[s.paper];
    const box = q("#cf-texture-tilechk");
    if (!m) { M.toast("choisir une matière du catalogue avant d'exporter sa tuile", true); return; }
    try {
      M.busy(true, "export de la tuile " + m.label + "…");
      const cv = tileOf(m.id, s.seed, TILE);
      const blob = await new Promise((res) => cv.toBlob(res, "image/png"));
      if (!blob) throw new Error("le navigateur n'a pas produit de PNG");
      const ecran = seamOf(m.id, s.seed);
      const resp = await M.api.raw("POST",
        "tile?mat=" + encodeURIComponent(m.id) + "&seed=" + s.seed, blob);
      if (resp.status === 404) { const x = new Error("route absente"); x.missing = true; throw x; }
      const d = await resp.json().catch(() => null);
      if (!resp.ok) throw new Error((d && d.detail) || (resp.status + " " + resp.statusText));
      const t = d && d.tile;
      const f = await M.api.blob("GET", "tile");
      M.download(f, "tuile_" + m.id + ".png");
      if (box && t && t.seam) {
        /* la comparaison porte sur la valeur PLEINE, pas sur l'arrondi publie :
           deux nombres arrondis a deux decimales coincideraient meme si les
           calculs divergeaient au troisieme chiffre. */
        const ecart = Math.abs(t.seam.exces_brut - ecran.exces_brut);
        box.innerHTML = '<p class="' + (ecart <= 0.001 ? "cf-tx-mu" : "cf-tx-mn") + '">'
          + '<b>' + esc(m.label) + ' — mesuré sur le fichier livré.</b> '
          + 'À l\'écran excès <span class="mono">' + fx(ecran.exces_brut, 4) + '×</span> · '
          + 'dans le PNG <span class="mono">' + fx(t.seam.exces_brut, 4) + '×</span> · écart '
          + '<span class="mono">' + fx(ecart, 4) + '</span>. '
          + 'H : bord ' + fx(t.seam.x.edge, 2) + ' / pire interne ' + fx(t.seam.x.max, 2)
          + ' · V : bord ' + fx(t.seam.y.edge, 2) + ' / pire interne ' + fx(t.seam.y.max, 2)
          + '. Fichier <span class="mono">' + t.w + ' × ' + t.h + ' px, '
          + Math.round(t.bytes / 1024) + ' Ko</span>, chunks '
          + '<span class="mono">' + esc((t.chunks || []).filter((c, i, a) => a.indexOf(c) === i).join(" ")) + '</span>'
          + (t.dpi && t.dpi[0] ? ' · ' + dpiTxt(t.dpi) : '')
          + '. Les mesures sont écrites dans ses chunks <span class="mono">tEXt</span>, '
          + 'avec la formule qui les produit.</p>';
      }
      M.toast("tuile exportée et re-mesurée sur le fichier : excès "
        + fx(t && t.seam ? t.seam.exces_brut : 0, 4) + "×");
    } catch (e) {
      M.toast(e && e.missing
        ? "backend absent : l'export de tuile exige /api/cards"
        : String(e && e.message || e), true);
    } finally { M.busy(false); }
  }

  function fillGrid(grid, s) {
    grid.innerHTML = "";
    const none = matCell({ id: "none", label: "Aucune", cat: "", gen: "none", rgb: [255, 255, 255], amp: 0 }, s, true);
    grid.appendChild(none);
    MATS.forEach((m) => {
      if (CAT_FILTER && m.cat !== CAT_FILTER) return;
      if (CAT_SEARCH && (m.label + " " + m.cat).toLowerCase().indexOf(CAT_SEARCH) < 0) return;
      grid.appendChild(matCell(m, s, false));
    });
    if (s.custom) {
      grid.appendChild(matCell({ id: "__import", label: "Importée", cat: "", gen: "none", rgb: [200, 200, 200], amp: 0 }, s, true));
    }
  }
  function matCell(m, s, plain) {
    const b = elm("button", "cf-tx-mat" + (s.paper === m.id ? " on" : ""));
    b.type = "button";
    b.title = m.label + (m.cat ? " · " + m.cat : "");
    const cv = mk(52, 52);
    const c = cv.getContext("2d");
    if (m.id === "none") {
      c.fillStyle = "#ffffff"; c.fillRect(0, 0, 52, 52);
      c.strokeStyle = "#cfcac0"; c.lineWidth = 1;
      c.beginPath(); c.moveTo(0, 52); c.lineTo(52, 0); c.stroke();
    } else if (m.id === "__import") {
      if (CUSTOM_IMG) {
        const k = Math.max(52 / CUSTOM_IMG.width, 52 / CUSTOM_IMG.height);
        c.drawImage(CUSTOM_IMG, (52 - CUSTOM_IMG.width * k) / 2, (52 - CUSTOM_IMG.height * k) / 2,
          CUSTOM_IMG.width * k, CUSTOM_IMG.height * k);
      } else { c.fillStyle = "#8a8378"; c.fillRect(0, 0, 52, 52); }
    } else {
      c.drawImage(tileOf(m.id, s.seed, 64), 0, 0, 52, 52);
    }
    b.appendChild(cv);
    b.appendChild(elm("span", "cf-tx-matl", esc(m.label)));
    /* L'AVERTISSEMENT SUR LA VIGNETTE QU'ON CLIQUE. Le reproche etait exact :
       « les matieres qui echouent au propre seuil de l'outil restent dans la
       grille au meme rang que les autres ; la vignette elle-meme ne porte
       aucun avertissement ». Le rapport en bas de page ne suffit pas — on
       choisit dans la grille. La mesure est portee par l'infobulle de CHAQUE
       tuile, et une pastille apparait des que le raccord fait pire que la
       matiere elle-meme. */
    /* La mesure coute une tuile 512 px complete par matiere : on ne la LANCE
       pas au dessin de la grille (ce serait trente fbm a chaque frappe dans le
       champ de recherche), on lit seulement ce qui a deja ete mesure. Le
       bouton « Vérifier le raccord des 30 » remplit le cache, puis redessine
       la grille — et alors chaque vignette porte son chiffre. */
    const r = plain ? null : seamPeek(m.id, s.seed);
    if (r) {
      b.title += " · raccord : excès " + fx(r.exces, 2) + "× (" + r.grade
        + ") — bord H " + fx(r.x.edge, 2) + " / pire interne " + fx(r.x.max, 2)
        + ", bord V " + fx(r.y.edge, 2) + " / pire interne " + fx(r.y.max, 2);
      if (r.exces > 1) {
        const w = elm("i", "cf-tx-matseam", "⚠ " + fx(r.exces, 1) + "×");
        w.title = "le raccord de cette tuile fait pire que la matière elle-même";
        b.appendChild(w);
      }
    }
    b.addEventListener("click", () => { pickMat(m); });
    if (plain) { /* pas de vignette procedurale a regenerer */ }
    return b;
  }

  /** Choisir une matiere ALIGNE les niveaux cuits sur sa physique.
      CE QUE CELA CORRIGE : « le catalogue propose Or brossé, Argent brossé,
      Cuivre patiné et Acier peigné, et rien ne relie le choix d'un support
      métallique à une map metallic non nulle. Le jour où un utilisateur
      choisit Or brossé et exporte une metallic à zéro, il exporte du
      plastique doré. » Les niveaux restent modifiables : ce sont des
      curseurs, et la mesure sous la map dira toujours ce qui a été écrit. */
  function pickMat(m) {
    const s = st(CF.doc());
    const part = { paper: m.id };
    if (m && m.mtl !== undefined) {
      part.pbr = pbrOut(Object.assign({}, s.pbr, {
        levels: { metallic: m.mtl, roughness: m.rgh },
      }));
    }
    push(part);
    render();
    if (m && m.mtl !== undefined) {
      M.toast(m.label + " — niveaux alignés : métal " + fx(m.mtl, 2)
        + ", rugosité " + fx(m.rgh, 2));
    }
  }

  async function upload(f) {
    if (!f || !/^image\//.test(f.type)) { M.toast("ce fichier n'est pas une image", true); return; }
    try {
      M.busy(true, "import de la matière…");
      const resp = await M.api.raw("POST", "paper", f);
      if (resp.status === 404) { const x = new Error("route absente"); x.missing = true; throw x; }
      const d = await resp.json().catch(() => null);
      if (!resp.ok) throw new Error((d && d.detail) || (resp.status + " " + resp.statusText));
      /* le backend a repondu : on relit l'image SERVIE, pas le fichier local —
         c'est elle que le painter dessinera, et c'est elle qui partira dans la
         derivation PBR. Une divergence entre les deux serait invisible. */
      const url = M.api.url("paper") + "?t=" + Date.now();
      imgCache.delete(url);
      CUSTOM_IMG = await loadImg(url);
      layerCache.clear();
      push({ custom: "paper.png", paper: "__import" });
      render();
      M.toast("matière importée — " + ((d && d.paper) ? d.paper.w + " x " + d.paper.h + " px" : "OK"));
    } catch (e) {
      M.toast(e && e.missing ? "backend absent : l'import exige /api/cards" : String(e && e.message || e), true);
    } finally { M.busy(false); }
  }

  /* ── B. l'effet de dessus ─────────────────────────────────────────────── */
  function sectionOver(s) {
    const box = elm("section", "cf-tx-card");
    /* (OVERS.length - 1) : « Aucun » n'est pas un effet. Compter le contenant
       est exactement le péché qu'on reproche au badge « 16 bits ». */
    box.appendChild(title("Effet de dessus", "couche z = 30 — sur l'illustration, sous le cadre",
      (OVERS.length - 1) + " effets"));
    const chips = elm("div", "cf-tx-chips");
    OVERS.forEach((o) => {
      const b = elm("button", "cf-tx-chip" + (s.over === o.id ? " on" : ""), esc(o.label));
      b.type = "button";
      b.addEventListener("click", () => {
        push({ over: o.id, over_blend: o.d, over_opacity: o.o });
        render();
      });
      chips.appendChild(b);
    });
    box.appendChild(chips);
    const ctl = elm("div", "cf-tx-ctl");
    ctl.appendChild(slider("Opacité", pct(s.over_opacity), 0, 100, 1, "%",
      (v) => push({ over_opacity: v / 100 })));
    ctl.appendChild(selectBox("Fusion", BLENDS, s.over_blend, (v) => push({ over_blend: v })));
    ctl.appendChild(slider("Échelle", pct(s.over_scale), 10, 400, 1, "%",
      (v) => push({ over_scale: v / 100 })));
    ctl.appendChild(elm("div", "cf-tx-sep"));
    ctl.appendChild(slider("Usure des bords", pct(s.wear), 0, 100, 1, "%", (v) => push({ wear: v / 100 })));
    ctl.appendChild(slider("Vernis sélectif", pct(s.varnish), 0, 100, 1, "%", (v) => push({ varnish: v / 100 })));
    box.appendChild(ctl);
    box.appendChild(elm("p", "cf-tx-note",
      "Usure et vernis sont des couches <b>indépendantes</b> : l'usure multiplie, le vernis éclaircit. "
      + "Fondus dans une seule couche, le vernis serait gris."));
    return box;
  }

  /* ── C. les 8 maps ────────────────────────────────────────────────────── */
  function sectionPbr(s, g) {
    const box = elm("section", "cf-tx-card");
    /* la section porte un id parce qu'elle se REMPLACE en entier quand le
       rapport arrive : voir `refreshMaps`. */
    box.id = "cf-texture-pbr";
    box.appendChild(title("Les 8 maps PBR", "dérivées de la carte rendue à l'échelle 1",
      "basecolor · normal · roughness · metallic · ao · height · emissive · orm"));

    if (!API_OK) {
      box.appendChild(elm("p", "cf-tx-warn", esc(API_MSG)));
    }

    const run = elm("div", "cf-tx-run");
    const b = elm("button", "btn strong", "Dériver les 8 maps");
    b.type = "button"; b.id = "cf-texture-derive"; b.title = "Alt+D";
    b.addEventListener("click", derive);
    run.appendChild(b);
    /* L'INFOBULLE DIT LA SORTIE REELLE. Elle annonçait « 4096 x 4096 px »
       même quand « carré (atlas) » était décoché — la sortie faisait alors
       3008 x 4096. Un chiffre affiché doit être vrai, y compris dans un
       titre de bouton. */
    run.appendChild(segment(RES_CHOICES.map((r) => ({
      v: r, l: (r / 1024) + "k", t: outPx(g, r, s.pbr.square).join(" x ") + " px",
    })), s.pbr.res, (v) => { patchPbr({ res: Number(v) }); render(); }));
    /* HOMONYME, ET IL PIEGE. `doc.texture.pbr.bits16` (cette case) et
       `doc.gltf.bits16` (celle de l'ecran Export 3D) sont deux reglages
       independants qui portent le meme nom. Cocher ici ne coche pas la-bas.
       On le DIT dans le libelle plutot que de laisser l'utilisateur le
       decouvrir en ouvrant le ZIP. */
    /* « 16 bits RÉELS » PROMETTAIT SUR UNE CASE À COCHER. Cette case est une
       DEMANDE ; ce qui est réellement écrit se mesure ensuite, map par map,
       sous chaque vignette (et une map qui n'a rien à porter sur seize bits
       repart en huit, en le disant). L'adjectif annonçait donc un résultat au
       moment où l'on formule le souhait. */
    run.appendChild(checkBox("16 bits (hauteur + normale) — maps de cet écran",
      s.pbr.bits16, (v) => { patchPbr({ bits16: v }); render(); }));
    run.appendChild(checkBox("carré (atlas)", s.pbr.square, (v) => { patchPbr({ square: v }); render(); }));
    box.appendChild(run);

    const dim = outPx(g, s.pbr.res, s.pbr.square);
    const dpi = outDpi(g, dim);
    const src = elm("p", "cf-tx-note",
      "Source : la carte " + (CF.current() + 1) + " rendue par le moteur unique, "
      + "<b>" + g.canvas_px.join(" x ") + " px</b> à " + g.dpi + " DPI. Sortie "
      + "<b>" + dim.join(" x ") + " px</b>"
      + (s.pbr.square ? " (atlas carré)" : " (format de la carte)")
      + ", soit <b>" + dpiTxt(dpi) + "</b> "
      + "inscrits dans le chunk <span class=\"mono\">pHYs</span> de chaque PNG — "
      + "fond perdu compris"
      /* n'expliquer l'ecart QUE quand il vient de l'atlas carre : hors atlas,
         les deux axes peuvent differer d'un DPI par le seul arrondi de la
         toile au pixel, et parler d'atlas la serait faux. */
      + (s.pbr.square && Math.abs(dpi[0] - dpi[1]) > 1
        ? " (l'atlas carré rend les pixels rectangulaires : la densité n'est "
          + "pas la même en largeur et en hauteur)" : "")
      /* LA LIGNE NE SE VANTE PLUS DE CE QU'ELLE NE FAIT PAS. « Aucun credit,
         aucun compte, aucun envoi » etait une reponse a la question d'un
         controle, pas un renseignement pour celui qui fabrique une carte : ce
         qu'il lui faut savoir — combien de temps, combien de pixels, quelle
         densite — est ecrit juste au-dessus et juste en dessous, en chiffres
         mesures. */
      + ".");
    box.appendChild(src);
    /* LE PRIX, AVANT LE CLIC. « 22 secondes de calcul et une normale de 45 Mo
       sans le moindre avertissement de poids ou de duree avant le clic » : le
       reproche est fonde, et il n'a qu'une reponse honnete. On ne peut pas
       MESURER ce qu'un calcul n'a pas encore fait ; on publie donc ce que le
       DERNIER lot a reellement coute, on pose le rapport de pixels — qui est
       de l'arithmetique exacte — et on ETIQUETTE l'extrapolation comme telle.
       Rien n'est affiche tant qu'aucun lot n'a ete mesure. */
    if (REPORT && REPORT.bytes_total && REPORT.out_mpx) {
      const mpx = dim[0] * dim[1] / 1e6;
      const k = mpx / REPORT.out_mpx;
      /* LE BUDGET DU JEU, ET PAS SEULEMENT CELUI DE LA CARTE. Le reproche est
         litteral : « aucun budget de poids, aucune alerte, aucune estimation
         pour un deck. A 60 cartes on depasse le gigaoctet sans que rien ne
         previenne. » Le nombre de cartes DISTINCTES est exact (les copies
         d'une meme carte partagent ses maps, c'est le meme rendu) ; le poids
         par carte est mesure sur les fichiers ecrits ; le produit des deux
         est etiquete comme une regle de trois, pas comme une mesure. */
      const n = Math.max(1, (CF.cards() || []).length);
      const jeu = REPORT.bytes_total * k * n;
      const lourd = REPORT.bytes_total * k > 60 * 1024 * 1024
        || (REPORT.ms || 0) * k > 20000
        || jeu > 1024 * 1024 * 1024;
      box.appendChild(elm("p", lourd ? "cf-tx-warn" : "cf-tx-note",
        "Coût : le dernier lot a pesé <b>" + mo(REPORT.bytes_total) + "</b> en <b>"
        + fx((REPORT.ms || 0) / 1000, 1) + " s</b> pour " + fx(REPORT.out_mpx, 2)
        + " Mpx (" + esc(REPORT.out_px || "") + "). Cette sélection en fait <b>"
        + fx(k, 2) + " ×</b> — soit ≈ <b>" + mo(REPORT.bytes_total * k)
        + "</b> et ≈ <b>" + dur((REPORT.ms || 0) * k) + "</b> par carte"
        + (n > 1
          ? ", et pour les <b>" + n + " cartes distinctes</b> de ce jeu ≈ <b>"
          : ", et pour la <b>seule carte</b> de ce jeu ≈ <b>")
        + (jeu >= 1073741824 ? fx(jeu / 1073741824, 2) + " Go" : mo(jeu))
        + "</b> et ≈ <b>" + dur((REPORT.ms || 0) * k * n)
        + "</b>. Les « ≈ » sont une règle de trois à coût par pixel constant, "
        + "à partir du poids et du temps du dernier lot."));
    }
    /* LE SEUIL DU CAHIER DES CHARGES, verifie a l'ecran, SUR LE PLUS PETIT DES
       DEUX AXES. Il se jugeait sur la seule largeur : un atlas carre 1024 sur
       une carte 69 x 94 mm affichait 377 DPI, ne declenchait rien, et ecrivait
       377 x 277 dans les octets. Le taire coute un livrable non imprimable. */
    const bas = Math.min(dpi[0], dpi[1]);
    if (bas < 300) {
      const axe = dpi[0] <= dpi[1] ? "largeur" : "hauteur";
      /* NE PROPOSER QUE CE QUI TIENT LE PLANCHER. La version d'avant proposait
         « décochez carré (atlas) » sans vérifier : sur cette carte, 1k décoché
         donne 277 DPI sur les DEUX axes — un remède qui ne soigne rien. On
         mesure donc chaque combinaison avant de la conseiller. */
      const bons = [];
      RES_CHOICES.forEach((r) => {
        [true, false].forEach((sq) => {
          if (r === s.pbr.res && sq === s.pbr.square) return;
          const d = outDpi(g, outPx(g, r, sq));
          if (Math.min(d[0], d[1]) >= 300) {
            bons.push((r / 1024) + "k" + (sq ? " carré" : " au format de la carte")
              + " (" + dpiTxt(d) + ")");
          }
        });
      });
      box.appendChild(elm("p", "cf-tx-warn",
        "<b>" + bas + " DPI en " + axe + "</b> : sous les 300 DPI d'une impression "
        + "pour une carte de " + fx(g.trim_mm[0] + 2 * g.bleed_mm, 1) + " × "
        + fx(g.trim_mm[1] + 2 * g.bleed_mm, 1) + " mm fond perdu compris. "
        + (bons.length
          ? "Passent les 300 DPI sur les deux axes : <b>" + bons.slice(0, 3).join("</b>, <b>") + "</b>."
          : "Aucune définition proposée n'atteint 300 DPI sur ce format.")));
    }

    /* UN REGLAGE QUI NE PEUT RIEN ALLUMER LE DIT AVANT LE CLIC, PAS APRES.
       Le reproche etait exact : « le controle existe, le resultat est noir ;
       un reglage qui ne produit rien devrait le dire AVANT l'export ». La
       note sous la vignette l'expliquait — mais elle n'existe qu'une fois le
       lot calcule, donc APRES avoir paye les 21 secondes. Ici la comparaison
       est faite au-dessus du bouton, avec les deux nombres qui la fondent :
       le seuil regle et la luminance MAXIMALE MESUREE sur l'image reellement
       derivee (pas sur source.png : le reechantillonnage LANCZOS depasse).
       Et le remede est un clic sur un nombre mesure — le centile 80, pas le
       99 : mesure faite sur deux cartes tres differentes, un seuil pose sur
       le p99 rend une emissive de moyenne 0,22 et 0,10 sur 255, c'est-a-dire
       « neutre » des deux cotes ; pose sur le p80, moyenne 11,50 (amplitude
       87) et 3,52 (amplitude 28), informative des deux cotes. Proposer un
       reglage qui ne produit rien serait le defaut qu'on repare. */
    const sl = REPORT && REPORT.source_lum;
    const seuilEm = num(s.pbr.derive.emissive_threshold, 0.85);
    if (sl && sl.max && seuilEm > sl.max) {
      const cible = Math.max(0, Math.floor(
        Math.min(num(sl.p80, sl.p99), sl.max - 0.005) * 100) / 100);
      const w = elm("p", "cf-tx-warn",
        "<b>Seuil d'émission " + fx(seuilEm, 2) + " &gt; " + fx(sl.max, 2)
        + "</b> — la luminance de l'image dérivée ne dépasse jamais "
        + fx(sl.max, 2) + " (sur " + (sl.px || 0).toLocaleString("fr-FR")
        + " pixels au dernier calcul) : l'émission sortira <b>noire</b>. ");
      if (cible > 0) {
        const fix = elm("button", "cf-tx-mini",
          "Régler le seuil sur " + fx(cible, 2) + " (p80 mesuré)");
        fix.type = "button";
        fix.title = "Le centile 80 de la luminance de l'image dérivée : un "
          + "pixel sur cinq passe alors le seuil. Ce que la map porte "
          + "ensuite est mesuré sous sa vignette, comme le reste.";
        fix.addEventListener("click", () => {
          patchDerive("emissive_threshold", cible);
          render();
        });
        w.appendChild(fix);
      }
      box.appendChild(w);
    }

    /* la matiere choisie et les niveaux cuits disent-ils la meme chose ?
       ROUGE seulement quand la METALLICITE diverge : c'est le seul cas qui
       fabrique un mensonge physique (de l'or exporte en plastique dore).
       Un ecart de rugosite est un choix, pas une faute. */
    const mm = MAT_BY_ID[s.paper];
    const dMtl = mm && mm.mtl !== undefined ? Math.abs(s.pbr.levels.metallic - mm.mtl) : 0;
    const dRgh = mm && mm.rgh !== undefined ? Math.abs(s.pbr.levels.roughness - mm.rgh) : 0;
    if (mm && mm.mtl !== undefined && (dMtl > 0.02 || dRgh > 0.02)) {
      const grave = dMtl > 0.02;
      const w = elm("p", grave ? "cf-tx-warn" : "cf-tx-note",
        "<b>" + esc(mm.label) + "</b> : " + (mm.mtl >= 0.5 ? "métal" : "diélectrique")
        + " " + fx(mm.mtl, 2) + " / rugosité " + fx(mm.rgh, 2)
        + " — niveaux cuits actuels métal " + fx(s.pbr.levels.metallic, 2)
        + ", rugosité " + fx(s.pbr.levels.roughness, 2)
        + (grave && mm.mtl >= 0.5
          ? ". Exporté tel quel, ce support sortira en <b>plastique doré</b>." : "."));
      const fix = elm("button", "cf-tx-mini", "Aligner sur la matière");
      fix.type = "button";
      fix.addEventListener("click", () => {
        patchPbr({ levels: { metallic: mm.mtl, roughness: mm.rgh } });
        render();
      });
      w.appendChild(fix);
      box.appendChild(w);
    }

    /* les curseurs de derivation, replies : ils ne servent qu'a qui les cherche */
    const det = document.createElement("details");
    det.className = "cf-tx-det";
    const sum = document.createElement("summary");
    /* le compte se LIT sur la liste qui sera dessinee juste en dessous : un
       « (12) » ecrit a la main survit a la disparition d'un reglage. */
    sum.textContent = "Réglages de dérivation (" + DERIVE_UI.length
      + ") et niveaux cuits (2)";
    det.appendChild(sum);
    const body = elm("div", "cf-tx-ctl");
    DERIVE_UI.forEach((d) => {
      const cur = s.pbr.derive[d.k];
      if (d.type === "bool") body.appendChild(checkBox(d.label, cur, (v) => patchDerive(d.k, v)));
      else if (d.type === "enum") body.appendChild(selectBox(d.label, d.opts, cur, (v) => patchDerive(d.k, v)));
      else body.appendChild(slider(d.label, cur, d.min, d.max, d.step, d.unit || "", (v) => patchDerive(d.k, v)));
    });
    body.appendChild(elm("div", "cf-tx-sep"));
    /* les deux niveaux relisent l'etat COURANT : la fermeture de rendu est
       perimee des le premier patch, et regler la rugosite aurait remis le
       metal a sa valeur d'il y a trois secondes. */
    body.appendChild(slider("Niveau métallique (cuit)", s.pbr.levels.metallic, 0, 1, 0.01, "",
      (v) => patchLevel("metallic", v)));
    body.appendChild(slider("Niveau de rugosité (cuit)", s.pbr.levels.roughness, 0, 1, 0.01, "",
      (v) => patchLevel("roughness", v)));
    /* CE QUE CETTE PHRASE PROMETTAIT DE TROP. Elle disait « c'est ce que le
       moteur verra » — vrai d'un moteur qui charge LES FICHIERS DE CET ECRAN,
       faux du ZIP de l'écran Export 3D, qui re-cuit ses niveaux depuis SA
       finition et ne lit pas ces deux nombres-là. Deux réglages du même nom,
       deux propriétaires : le taire, c'est le défaut qu'on vient de réparer,
       à l'envers. Mesuré : avec métal 1,00 réglé ici, metallic.png écrit par
       cet écran a une moyenne de 1,000 sur 3 080 192 pixels (relue sur les
       octets) ; le même réglage ne change pas d'un octet la métallique du lot
       exporté par la pièce 08. */
    body.appendChild(elm("p", "cf-tx-note",
      "Le niveau vit dans la MAP, pas dans un facteur : <b>moyenne mesurée = niveau réglé</b>, "
      + "relue sur le PNG écrit (glTF : rugosité = facteur × canal V). "
      + "<b>Portée :</b> ces deux niveaux sont cuits dans les maps de <i>cet</i> écran — "
      + "celles que téléchargent « PNG », « Planche » et le manifeste. L'écran <b>Export 3D</b> "
      + "cuit les siens depuis sa propre <b>finition</b> : il ne relit pas ces deux nombres. "
      + "Les douze réglages de dérivation ci-dessus, eux, sont bien repris par lui."));
    det.appendChild(body);
    box.appendChild(det);

    box.appendChild(mapsBlock(s));
    return box;
  }

  /** La sortie REELLE pour une résolution et un mode donnés : c'est le grand
      côté qui vaut `res`, pas les deux, tant que « carré » est décoché. */
  function outPx(g, res, square) {
    if (square) return [res, res];
    const w = g.canvas_px[0], h = g.canvas_px[1];
    const k = res / Math.max(w, h);
    return [Math.max(1, Math.round(w * k)), Math.max(1, Math.round(h * k))];
  }

  /** La densité des DEUX axes, calculée EXACTEMENT comme le backend l'écrit
      (`texture._physical` : ppm = arrondi(px x 1000 / mm), DPI = arrondi(ppm x
      0,0254)) — même formule, même double arrondi, donc même chiffre que celui
      qu'on lira dans le chunk `pHYs` du fichier.

      CE QUE CELA CORRIGE, mesuré sur les octets : un atlas CARRÉ posé sur une
      carte qui ne l'est pas donne des pixels RECTANGULAIRES. 1024 x 1024 sur
      une carte de 69 x 94 mm (fond perdu compris) écrit pHYs = 14841 x 10894
      px/m, soit 377 x 277 DPI. Le panneau annonçait « soit 377 DPI inscrits
      dans le chunk pHYs de chaque PNG », chaque vignette répétait « 377 DPI »,
      et l'avertissement « sous 300 DPI » restait muet — alors que la moitié
      verticale du livrable tombe à 277, sous le plancher du cahier des
      charges. Un seul chiffre pour deux axes, c'est un chiffre faux. */
  function outDpi(g, dim) {
    /* les MILLIMETRES DECLARES du format, pas la toile en pixels redivisee
       par les DPI : la toile est arrondie au pixel, et cet arrondi suffisait a
       decaler la prediction d'un DPI par rapport au chunk ecrit (554 annonce,
       553 dans le fichier, mesure sur une sortie 1504 x 2048). */
    const mmW = g.trim_mm[0] + 2 * g.bleed_mm, mmH = g.trim_mm[1] + 2 * g.bleed_mm;
    return [Math.round(Math.round(dim[0] * 1000 / mmW) * 0.0254),
      Math.round(Math.round(dim[1] * 1000 / mmH) * 0.0254)];
  }
  /** « 377 x 277 DPI » quand les pixels ne sont pas carrés, « 553 DPI » sinon. */
  function dpiTxt(d) {
    return (d[0] === d[1]) ? (d[0] + " DPI") : (d[0] + " × " + d[1] + " DPI");
  }

  function mapsBlock(s) {
    const wrap = elm("div", "cf-tx-maps");
    wrap.id = "cf-texture-maps";
    if (!REPORT || !REPORT.maps || !REPORT.maps.length) {
      const e = elm("div", "cf-tx-empty",
        "<b>Aucune map dérivée pour l'instant.</b>"
        + "<span>La carte affichée porte déjà sa matière : un clic la transforme en 8 maps PBR "
        + "mesurées — relief, rugosité, occlusion, hauteur.</span>");
      const go = elm("button", "btn strong", "Dériver maintenant");
      go.type = "button";
      go.addEventListener("click", derive);
      e.appendChild(go);
      wrap.appendChild(e);
      return wrap;
    }
    const head = elm("div", "cf-tx-mhead");
    const eff = REPORT.effective || {};
    const ph = REPORT.phys || {};
    /* LE COMPTE DIT CE QUI MANQUE, PAS CE QUI VA. « 6 / 8 informatives » est
       une note qu'on se donne ; « 2 maps constantes » est un fait qui envoie
       l'utilisateur regarder LESQUELLES. Le nombre est le meme, releve sur
       les memes octets. */
    const plates = REPORT.total - REPORT.informative;
    head.innerHTML = '<b>' + REPORT.maps.length + ' maps</b>'
      + (plates > 0 ? '<span class="cf-tx-flat">' + plates + ' constante'
        + (plates > 1 ? 's' : '') + '</span>' : '')
      + '<span class="mono">rugosité effective ' + fx(eff.roughness === undefined ? 0 : eff.roughness, 3)
      + ' · métal ' + fx(eff.metallic === undefined ? 0 : eff.metallic, 3) + '</span>'
      + '<span class="mono">' + esc(REPORT.out_px || "") + ' · dérivé à ' + esc(REPORT.work_px || "")
      + ' · ' + (REPORT.ms || 0) + ' ms</span>'
      + (ph.ok ? '<span class="mono">pHYs ' + ph.dpi[0] + '×' + ph.dpi[1] + ' DPI · carte '
        + ph.mm[0] + '×' + ph.mm[1] + ' mm (fond perdu ' + ph.bleed_mm
        + ', zone sûre ' + ph.safe_mm + ')</span>'
        /* L'ALERTE QUAND LA DENSITE NE PASSE PAS, sur le plus petit des deux
           axes et sur les octets ecrits. Rien quand elle passe : la densite
           mesuree est deja affichee juste avant, et se feliciter a l'ecran
           n'apprend rien a personne. */
        + (Math.min(ph.dpi[0], ph.dpi[1]) >= 300 ? ''
          : '<span class="cf-tx-flat">sous 300 DPI : '
            + Math.min(ph.dpi[0], ph.dpi[1]) + " DPI en "
            + (ph.dpi[0] <= ph.dpi[1] ? "largeur" : "hauteur") + '</span>') : '');
    const dl = elm("button", "cf-tx-mini", "Planche PNG");
    dl.type = "button";
    dl.title = "Les 8 maps sur une seule image, avec les mesures écrites dessous";
    dl.addEventListener("click", sheet);
    head.appendChild(dl);
    const mf = elm("button", "cf-tx-mini", "Manifeste JSON");
    mf.type = "button";
    mf.title = "Espaces colorimétriques, densité physique, conventions, SHA-256 de chaque fichier";
    mf.addEventListener("click", manifest);
    head.appendChild(mf);
    wrap.appendChild(head);

    const grid = elm("div", "cf-tx-mgrid");
    REPORT.maps.forEach((m) => grid.appendChild(mapCell(m)));
    wrap.appendChild(grid);
    /* LA DENSITE DE TEXTE ETAIT ELLE AUSSI UN REPROCHE, et il etait fonde :
       « la definition de moy et ampl. occupe deux paragraphes serres ; le
       chiffre juste est la, mais l'effort de lecture demande est important ».
       On ne retire pas une definition — c'est elle qui rend le nombre
       reproductible — on la RANGE : chaque vignette garde son etiquette
       courte collee sous son chiffre, et les formules exactes tiennent dans
       un depliant, a un clic. */
    const defs = document.createElement("details");
    defs.className = "cf-tx-det";
    defs.id = "cf-texture-defs";
    const dsum = document.createElement("summary");
    dsum.textContent = "Comment lire ces chiffres — les définitions exactes, arrondis compris";
    defs.appendChild(dsum);
    defs.appendChild(elm("p", "cf-tx-note",
      "Les chiffres de cet écran sont <b>lus sur les octets des PNG écrits</b>, la profondeur "
      + "comprise. <b>niveaux</b> = combien de valeurs différentes le canal mesuré contient "
      + "réellement, sur ce que sa profondeur autorise (256 en 8 bits, 65 536 en 16) : c'est "
      + "ce compte, et pas l'étiquette du fichier, qui décide si un dégradé sortira lisse ou "
      + "en marches. Sur une map 16 bits, deux chiffres disent ce que le second octet "
      + "apporte : la part des points <b>trop fins pour un octet</b>, et l'<b>information "
      + "qu'il porte</b>, sur 8. Quand ces deux-là tombent à zéro, la map est écrite en "
      + "8 bits, elle pèse moins, et l'étiquette le dit."));
    /* LA DEFINITION VOYAGE AVEC LE NOMBRE. Rappel groupe, en plus de
       l'etiquette collee sous chaque chiffre : un acheteur qui recalcule doit
       pouvoir retrouver la formule EXACTE, arrondi compris. */
    /* LES DEUX EXEMPLES CHIFFRES SONT PARTIS. « tronquee elle vaudrait 0,2349
       au lieu de 0,2368 » et « 244 contre 243,30 » etaient de vraies mesures,
       faites une fois sur un autre lot : rien, a l'ecran, ne permet de les
       refaire sur CE lot. Un chiffre affiche que le lecteur ne peut pas
       retrouver dans ce qu'on lui livre n'a rien a faire ici, meme quand il
       est juste. La formule, elle, reste : c'est elle qui rend les chiffres du
       lot reproductibles. */
    defs.appendChild(elm("p", "cf-tx-note",
      "<b>Ce que « moy », « ampl. » et « é.-t. » veulent dire</b> — et ce n'est pas la même "
      + "chose d'une map à l'autre, d'où l'étiquette sous chaque chiffre. <b>moy</b> = moyenne "
      + "du canal nommé ; sur la base color et l'émission c'est la <b>luminance Rec.601</b>, "
      + "<span class=\"mono\">(R×19595 + V×38470 + B×7471 + 32768) &gt;&gt; 16</span>, "
      + "<b>arrondie</b>. Sur une map 16 bits elle se lit sur seize bits, puis se ramène "
      + "sur l'échelle 0-255. "
      + "<b>ampl.</b> = <b>p95 − p5</b> du même canal, sur 255 — pas max moins min ; "
      + "sur une map 16 bits, les centiles sont pris sur les <b>65 536 classes réelles</b> "
      + "et ramenés sur l'échelle 0-255, et c'est un décimal. "
      + "<b>é.-t.</b> = écart-type du même canal, sur la même échelle : c'est lui qui sépare "
      + "une map qui varie partout d'une map constante sur 90 % de sa surface. "
      + "Le manifeste porte ces définitions par ligne (<span class=\"mono\">canal_mesure</span>, "
      + "<span class=\"mono\">amplitude_mesure</span>)."));
    wrap.appendChild(defs);
    return wrap;
  }

  function mapCell(m) {
    const c = elm("div", "cf-tx-map" + (m.informative ? "" : " flat"));
    const img = document.createElement("img");
    img.src = M.api.url("thumb/" + m.kind) + "?t=" + (REPORT.stamp || 0);
    img.alt = m.kind;
    img.loading = "lazy";
    c.appendChild(img);
    const t = elm("div", "cf-tx-mt");
    /* LA PROFONDEUR, MESUREE. Le badge « 16 bits » était le seul chiffre du
       panneau jamais confronté aux octets : l'encodage dupliquait l'octet
       (v x 257), donc conteneur 16 bits et charge utile 8 bits. Il porte
       maintenant sa mesure, ou tombe à 8 bits en le disant. */
    /* LE BADGE REDEVIENT UNE ETIQUETTE, PAS UN PLAIDOYER. Il portait ses deux
       mesures de profondeur en gros a cote du nom de la map, redigees comme
       une demonstration. AUCUN CHIFFRE NE DISPARAIT : ils descendent d'une
       ligne, parmi les autres mesures de la vignette, chacun avec son
       etiquette de definition — c'est la forme que tout le reste du panneau
       emploie deja (moy, ampl., e.-t.), et elle se lit sans avoir a plaider.
       Le nombre d'echantillons (`m.ech` : trois canaux pour la normale, un
       pour la hauteur) reste colle au pourcentage : sans lui, « 90,7 % » ne
       dit pas de quoi il est le pourcentage. */
    const prof = (m.bits === 16)
      ? '<i class="cf-tx-b16">16 bits</i>'
      : '<i' + (m.bits_asked === 16 ? ' class="cf-tx-warnb" title="' + esc(m.note16 || "") + '"' : '')
        + '>8 bits' + (m.bits_asked === 16 ? ' (16 demandés)' : '') + '</i>';
    t.innerHTML = '<b>' + esc(KIND_FR[m.kind] || m.kind) + '</b>' + prof;
    c.appendChild(t);
    const v = elm("div", "cf-tx-mv");
    /* LA CONVENTION COLLEE AU CHIFFRE. « moy » ne veut pas dire la meme chose
       d'une map a l'autre : luminance Rec.601 sur basecolor et emissive,
       canal R sur la normale, canal V sur l'ORM, canal unique ailleurs. Les
       chiffres etaient JUSTES — un decodeur PNG independant a reverifie 102
       valeurs affichees sans une divergence — mais la definition vivait sur
       une autre ligne, et un lecteur qui recalcule naivement conclut au
       mensonge. Mesure en le refaisant : une luminance Rec.601 TRONQUEE au
       lieu d'etre arrondie donne 0,2349 la ou le panneau affiche 0,2368. */
    const def = esc(m.mesure_sur || "");
    /* L'AMPLITUDE D'UNE MAP 16 BITS N'EST PAS UN ENTIER. Elle etait mesuree
       sur une VUE 8 bits de la map — et pas la meme selon la map : octet fort
       pour un RVB 16 bits, `v/257` arrondi pour un gris 16 bits. Deux
       reductions, deux resultats sur les memes octets (244 contre 243,
       mesure). Elle se lit maintenant sur seize bits et se ramene sur 255 :
       c'est un decimal, et il s'affiche comme tel. */
    const amp = (typeof m.span === "number" && !Number.isInteger(m.span))
      ? fx(m.span, 2) : String(m.span);
    /* TROIS CHIFFRES, PLUS UN MOT QUAND IL Y A QUELQUE CHOSE A DIRE. Une
       moyenne et une amplitude p95 − p5 ne separent pas une map qui varie
       partout d'une map constante sur 90 % de sa surface qui saute sur les
       10 % restants : l'ECART-TYPE le fait, il se lit sur le meme canal, et
       il se recalcule sur les octets comme les deux autres. Le mot n'est
       ecrit que pour une map qui ne varie pas — il n'y a rien a annoncer sur
       une map qui fait son travail. */
    /* LE COMPTE DE NIVEAUX. Une profondeur annoncee dit ce que le fichier PEUT
       porter ; ce compte dit ce qu'il porte. C'est le chiffre qui repond a la
       question que se pose celui qui fabrique une carte — mon degrade va-t-il
       sortir lisse ou en marches — et une normale « 16 bits » authentique mais
       qui ne contient que 66 valeurs distinctes se voit ici, pas ailleurs. */
    const niv = (m.niveaux === undefined || m.niveaux === null) ? 0 : m.niveaux;
    const nivMax = m.niveaux_max || 256;
    v.innerHTML = '<span class="mono">moy <b>' + fx(m.mean, 3) + '</b>'
      + (def ? '<i class="cf-tx-def">' + def + '</i>' : '') + '</span>'
      + '<span class="mono">ampl. ' + amp + '/255'
      + '<i class="cf-tx-def">' + esc(m.span_def || "p95 − p5") + '</i></span>'
      + '<span class="mono">é.-t. ' + fx(m.sd === undefined ? 0 : m.sd, 2) + '/255'
      + '<i class="cf-tx-def">écart-type du même canal</i></span>'
      + (niv ? '<span class="mono">niveaux ' + niv.toLocaleString("fr-FR")
        + '/' + nivMax.toLocaleString("fr-FR")
        + '<i class="cf-tx-def">valeurs distinctes du même canal</i></span>' : '')
      + (m.bits === 16
        ? '<span class="mono">hors 8 bits ' + fx(m.sub === undefined ? 0 : m.sub, 1) + ' %'
          + '<i class="cf-tx-def">points trop fins pour un octet'
          + (m.ech ? ', sur ' + m.ech.toLocaleString("fr-FR") : '') + '</i></span>'
          + '<span class="mono">second octet '
          + fx(m.low_bits === undefined ? 0 : m.low_bits, 2) + '/8'
          + '<i class="cf-tx-def">information qu\'il porte</i></span>'
        : '')
      + (m.informative ? '' : '<span class="cf-tx-flat">constante</span>');
    c.appendChild(v);
    /* LES DEUX AXES, comme dans le pHYs du fichier : « 377 DPI » seul cachait
       les 277 DPI verticaux d'un atlas carré.
       ET L'ESPACE TEL QUE LES OCTETS LE DECLARENT (`space_decl`, lu dans les
       chunks gAMA/sRGB du fichier relu) plutot que le mot pris dans une table
       du code : « le manifeste dit lineaire » et « le fichier declare
       lineaire » sont deux affirmations differentes, et une seule se mesure. */
    c.appendChild(elm("p", "cf-tx-mc",
      m.w + " × " + m.h + " · " + esc(m.space_decl || m.space || "")
      + (m.dpi && m.dpi[0] ? " · " + dpiTxt(m.dpi) : "")));
    /* LES DEUX CORRELATIONS, ETIQUETEES. Le « r = +0,97 » d'avant venait de
       `pbr_service.correlation`, qui réduit en blocs 192² avant Pearson : vrai,
       mais introuvable pour qui recalcule à pleine résolution. */
    if (m.kind !== "basecolor" && m.informative
        && (Math.abs(m.corr_lum) > 0.01 || Math.abs(m.corr_full || 0) > 0.01)) {
      c.appendChild(elm("p", "cf-tx-mc",
        "r = " + (m.corr_lum >= 0 ? "+" : "") + fx(m.corr_lum, 3) + " (blocs 192²) · "
        + ((m.corr_full || 0) >= 0 ? "+" : "") + fx(m.corr_full || 0, 3)
        + " (pleine résolution) avec la luminance de la base color"));
    }
    if (m.kind === "normal" && REPORT.unit_normal && REPORT.unit_normal.px) {
      const u = REPORT.unit_normal;
      c.appendChild(elm("p", "cf-tx-mu",
        "normale unitaire " + fx(u.unit_pct, 1) + " % · |n| moy " + fx(u.mean, 5)
        + " (" + fx(u.min, 4) + " – " + fx(u.max, 4) + ") · " + u.zneg + " pixel(s) à z<0"
        + " · décodé sur " + (u.bits || 8) + " bits"));
    }
    /* L'EMPAQUETAGE DE L'ORM, MESURE — pas annonce. Le panneau ECRIVAIT
       « R = AO, V = rugosite, B = metal » sans jamais le verifier : c'est un
       critique qui a du rouvrir les quatre PNG pour constater l'ecart maximum
       de 0. Une convention annoncee et non mesuree est exactement le genre de
       mention que ce panneau s'interdit. Et le prix de la redondance est
       publie avec : l'ORM n'apporte aucune valeur nouvelle. */
    if (m.kind === "orm" && REPORT.orm_pack && REPORT.orm_pack.px) {
      const p = REPORT.orm_pack, e = p.ecarts || {};
      const FR = { ao: "occlusion", roughness: "rugosité", metallic: "métal" };
      const trois = ["ao", "roughness", "metallic"].map((k, i) =>
        "RVB".charAt(i) + " = " + FR[k] + " (écart max "
        + (e[k] === null || e[k] === undefined ? "non mesurable" : e[k]) + ")");
      c.appendChild(elm("p", p.ok ? "cf-tx-mu" : "cf-tx-mn",
        (p.ok ? "reprend les trois maps séparées, valeur pour valeur, sur "
          : "S'ÉCARTE des trois maps séparées sur ")
        + p.px.toLocaleString("fr-FR") + " pixels — " + trois.join(" · ")
        + (p.octets ? " · " + Math.round(p.octets / 1024) + " Ko" : "")));
      /* « SANS OPTION POUR LIVRER L'ORM A LA PLACE DES TROIS SEPAREES » — le
         reproche revient dans les deux duels, et il suppose que l'echange
         ferait maigrir le lot. On ne le suppose plus : on PESE les deux
         paquets sur les fichiers ecrits, et le resultat DEPEND DU CONTENU,
         donc aucune phrase generale n'est permise ici. Mesure : lot 2048
         reel 2 183 Ko (ORM) contre 1 918 Ko (les trois) — l'ORM est plus
         lourd de 265 Ko ; carte de synthese 1024 pauvre en detail, 155 999
         contre 156 760 — l'ORM est plus leger de 761 octets. La deflate
         compresse trois plans correles cote a cote tantot mieux, tantot
         moins bien que trois gris separes. La ligne ci-dessous n'annonce
         donc pas le signe : elle le LIT sur les deux poids du lot affiche. */
      if (p.octets && p.octets_trois) {
        const d = p.octets - p.octets_trois;
        const deux = mo2(p.octets, p.octets_trois);
        c.appendChild(elm("p", "cf-tx-mc",
          "livrer l'ORM <b>à la place</b> des trois séparées : "
          + deux[0] + " contre " + deux[1]
          + " — " + (d > 0
            ? "le lot <b>grossirait</b> de " + mo(d)
              + " (la déflate compresse trois plans corrélés côte à côte moins "
              + "bien que trois gris séparés)"
            : d < 0
              ? "le lot maigrirait de " + mo(-d)
              : "même poids") + ", mesuré sur les fichiers écrits"));
      }
    }
    if (m.note) c.appendChild(elm("p", "cf-tx-mn", esc(m.note)));
    /* POURQUOI elle est vide, et QUOI REGLER — avant l'export, pas apres. Le
       seuil d'emission par defaut (0,85) ne peut rien allumer sur une carte
       dont la luminance plafonne a 0,63 : la map etait annoncee « eteinte »
       sans jamais dire que le SEUIL etait hors de portee de l'image. */
    if (m.hint) c.appendChild(elm("p", "cf-tx-hint", esc(m.hint)));
    if (m.bits_asked === 16 && m.bits === 8 && m.note16) {
      c.appendChild(elm("p", "cf-tx-mn", esc(m.note16)));
    }
    const row = elm("div", "cf-tx-mrow");
    const d = elm("button", "cf-tx-mini", "PNG " + Math.round(m.bytes / 1024) + " Ko");
    d.type = "button";
    d.addEventListener("click", () => grab(m.kind));
    row.appendChild(d);
    c.appendChild(row);
    return c;
  }

  function title(t, sub, right) {
    const h = elm("div", "cf-tx-th");
    h.innerHTML = '<b>' + esc(t) + '</b><span>' + esc(sub) + '</span><i>' + esc(right) + '</i>';
    return h;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     10. ECRITURES ET RESEAU
     ═══════════════════════════════════════════════════════════════════════ */
  /** LE SOUS-ARBRE `doc.texture.pbr` TEL QUE LE LECTEUR LE LIT.

      `doc.texture.pbr` est le seul sous-arbre de cette pièce lu par une autre
      (P8, export 3D). Il m'appartient, donc sa FORME m'appartient — et sa forme
      était fausse.

      LE DÉFAUT, reproduit avant d'être corrigé : le lecteur passe l'enveloppe
      `doc.texture.pbr` entière à `pbr_service.normalize_derive`, qui cherche
      `normal_strength`, `ao_strength`, `ao_radius`… au PREMIER niveau. Ici, ils
      étaient écrits un cran plus bas, sous `.derive`. `normalize_derive` ignore
      les clés inconnues sans un mot : le lecteur recevait donc les DÉFAUTS,
      toujours, quels que soient les douze réglages. Mesuré : avec
      normal_strength 4,0 / ao_strength 4,0 / ao_radius 32 / roughness_invert
      vrai, `normalize_derive(doc.texture.pbr)` rendait exactement
      `DERIVE_DEFAULTS` — les douze curseurs étaient décoratifs pour le fichier
      exporté, alors que l'aperçu de CE panneau, lui, les respecte (il les passe
      dans le CORPS de la requête). L'écran et le fichier divergeaient : le
      risque nommé par la spec.

      LA CORRECTION tient en une ligne et ne touche aucun fichier voisin : les
      douze réglages sont écrits AUX DEUX niveaux — sous `.derive`, que cet
      écran lit, et à plat, où le lecteur les cherche. Une seule source (`.derive`),
      recopiée à chaque écriture, donc jamais deux vérités. */
  function pbrOut(pbr) {
    return Object.assign({}, pbr, pbr.derive || {});
  }
  function patchPbr(part) {
    const s = st(CF.doc());
    push({ pbr: pbrOut(Object.assign({}, s.pbr, part)) });
  }
  function patchDerive(k, v) {
    const s = st(CF.doc());
    const d = Object.assign({}, s.pbr.derive);
    d[k] = v;
    push({ pbr: pbrOut(Object.assign({}, s.pbr, { derive: d })) });
  }
  function patchLevel(k, v) {
    const s = st(CF.doc());
    const l = Object.assign({}, s.pbr.levels);
    l[k] = v;
    push({ pbr: pbrOut(Object.assign({}, s.pbr, { levels: l })) });
  }

  async function loadState() {
    try {
      const r = await M.api.get("state");
      API_OK = true;
      const t = r && r.texture;
      if (t && t.maps && t.maps.length) { REPORT = t; refreshMaps(); }
      if (t && t.source && t.source.custom) {
        CUSTOM_IMG = await loadImg(M.api.url("paper") + "?t=" + (t.source.stamp || 0));
        layerCache.clear();
        M.invalidate();
      }
      /* les bornes viennent du service, pas d'une copie */
      const d = await M.api.get("defaults");
      if (d && d.defaults) {
        DERIVE_UI.forEach((u) => {
          if (u.k in d.defaults) u.def = d.defaults[u.k];
          if (d.ranges && d.ranges[u.k]) { u.min = d.ranges[u.k][0]; u.max = d.ranges[u.k][1]; }
        });
      }
    } catch (e) {
      API_OK = false;
      API_MSG = e && e.missing
        ? "Backend /api/cards/…/texture absent : les deux couches 2D fonctionnent, la dérivation PBR non."
        : "Backend : " + String(e && e.message || e);
      render();
    }
  }

  function refreshMaps() {
    /* LE RAPPORT ARRIVE APRES LE PREMIER RENDU, ET LA MOITIE DE CE PANNEAU EN
       DEPEND. Cette fonction ne remplaçait que la GRILLE des huit vignettes —
       les lignes de la section PBR qui vivent du même rapport restaient donc
       à leur état « rien n'a encore été mesuré ». MESURE, en ouvrant un jeu
       déjà dérivé et en relevant le DOM : huit vignettes présentes, et la
       ligne de coût du lot ABSENTE du document, comme l'avertissement de
       seuil d'émission. Elles ne réapparaissaient qu'à la première
       interaction qui redéclenche `render()` — un panneau qui dit la vérité
       seulement après qu'on l'a touché. On remplace donc la SECTION entière
       (elle contient la grille), et non plus la grille seule. */
    const old = q("#cf-texture-pbr");
    if (!old) { render(); return; }
    const s = st(CF.doc());
    old.replaceWith(sectionPbr(s, CF.geom()));
    /* la table lumineuse vit du MEME rapport : la laisser sur son etat vide
       pendant que la grille affiche huit maps serait le genre d'incoherence
       qui fait douter du reste. */
    const lit = q("#cf-texture-litbox");
    if (lit) lit.replaceWith(sectionLight(s));
    litRefresh();
  }

  async function derive() {
    const s = st(CF.doc());
    const g = CF.geom();
    const b = q("#cf-texture-derive");
    if (b) b.disabled = true;
    try {
      M.busy(true, "rendu de la carte à l'échelle 1…");
      const blob = await CF.cardBlob(CF.current(), {});
      M.busy(true, "envoi de la source (" + Math.round(blob.size / 1024) + " Ko)…");
      await M.api.blob("POST", "source", blob);
      M.busy(true, "dérivation des 8 maps " + (s.pbr.square ? s.pbr.res + " x " + s.pbr.res : "à " + s.pbr.res + " px") + "…");
      const t0 = Date.now();
      const r = await M.api.post("derive", {
        derive: s.pbr.derive, levels: s.pbr.levels,
        res: s.pbr.res, bits16: s.pbr.bits16, square: s.pbr.square,
      });
      REPORT = r && r.texture;
      API_OK = true;
      patchPbr({
        ready: true, informative: (REPORT && REPORT.informative) || 0,
        updated: (REPORT && REPORT.updated) || "",
      });
      render();
      M.emit("maps-ready", { informative: REPORT ? REPORT.informative : 0, res: s.pbr.res });
      /* LE MEME COMPTE QUE L'EN-TETE, DIT DE LA MEME FACON : ce qui manque,
         pas la note qu'on se donne. */
      const plates = REPORT ? (REPORT.total - REPORT.informative) : 0;
      M.toast((REPORT ? REPORT.maps.length : 0) + " maps dérivées en "
        + ((Date.now() - t0) / 1000).toFixed(1) + " s"
        + (plates > 0 ? " — " + plates + " constante" + (plates > 1 ? "s" : "") : ""));
    } catch (e) {
      API_OK = !(e && e.missing);
      API_MSG = e && e.missing
        ? "Backend /api/cards/…/texture absent : les deux couches 2D fonctionnent, la dérivation PBR non."
        : "Dérivation : " + String(e && e.message || e);
      M.toast(API_MSG, true);
      render();
    } finally {
      M.busy(false);
      const bb = q("#cf-texture-derive");
      if (bb) bb.disabled = false;
    }
  }

  async function grab(kind) {
    try {
      M.busy(true, "téléchargement de " + kind + "…");
      const b = await M.api.blob("GET", "map/" + kind);
      M.download(b, kind + ".png");
    } catch (e) { M.toast(String(e && e.message || e), true); }
    finally { M.busy(false); }
  }
  async function sheet() {
    try {
      M.busy(true, "planche des 8 maps…");
      const b = await M.api.blob("GET", "sheet");
      M.download(b, "maps_8.png");
    } catch (e) { M.toast(String(e && e.message || e), true); }
    finally { M.busy(false); }
  }
  /** Le contrat du lot : sans lui, les noms de fichiers sont le seul contrat. */
  async function manifest() {
    try {
      M.busy(true, "manifeste du lot…");
      const b = await M.api.blob("GET", "manifest");
      M.download(b, "manifest.json");
      M.toast("manifeste : espaces colorimétriques, densité physique, conventions, SHA-256");
    } catch (e) { M.toast(String(e && e.message || e), true); }
    finally { M.busy(false); }
  }
})();
