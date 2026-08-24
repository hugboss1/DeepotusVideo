/* ═══════════════════════════════════════════════════════════════════════════
   Card Forge — piece 01 · Face   [P1]
   Proprietaire exclusif de : doc.face · z 20 · /api/cards/<did>/face/*
   Prefixe DOM impose : id="cf-face-..."   ·   feuille : css/mod-face.css

   LA BARRE — Clash of Decks : galerie de 300 dessins BITMAP, import refuse
   BRUTALEMENT sous 650x1024 par un `alert()` natif, placement par SIX BOUTONS
   (deux loupes, quatre fleches), aucun chiffre nulle part — ni la taille de
   l'image, ni celle de la carte, ni le DPI auquel elle sera imprimee.

   CE QUI EST FAIT ICI, ET POURQUOI

   (1) LE CHIFFRE. La jauge de DPI EFFECTIF est le premier bloc du panneau,
       collee a la carte : elle dit a quelle definition l'illustration POSEE
       sera reellement imprimee, verte a partir de 300, rouge en dessous, avec
       la taille source, la taille posee, et — quand c'est rouge — LA TAILLE
       QU'IL FAUDRAIT. Rien n'est jamais refuse : on mesure, on dit, on
       propose une correction en un clic. Un `alert()` qui dit « non » et
       s'arrete n'apprend rien a personne.

   (2) LE CATALOGUE EST VECTORIEL — ET IL SE COMPTE HONNETEMENT.
       18 sujets x 6 COMPOSITIONS = 108 dessins REELLEMENT distincts, chacun
       recolorable en 12 palettes (1296 combinaisons, comptees a part). La
       redaction precedente annoncait « 72 faces » pour 12 dessins recolores
       six fois : les deux critiques du duel l'ont compte a la main, et ils
       avaient raison. Une composition ne change pas la teinte, elle change le
       monde : `medallion` n'a aucun horizon, `heraldry` est un aplat
       symetrique, `depths` est une colonne d'eau, `backlight` un disque unique
       sur un sol plat, `stained` une baie de vitrail. Tout est dessine au canvas
       a `geom.canvas_px`, donc net a 300 comme a 600 DPI, et sans UN SEUL
       OCTET DE RESEAU — ce qui n'est plus AFFIRME mais COMPTE a l'ecran par
       `performance.getEntriesByType("resource")`, avant/apres la grille.

   (2 bis) LE FICHIER LIVRE PORTE SA RESOLUTION. `canvas.toBlob` n'ecrit
       aucun chunk `pHYs` : mesure sur le PNG du duel, 815x1110, chunks =
       IHDR + 280 IDAT + IEND. Un tel fichier arrive a 72 DPI dans un outil de
       mise en page. Le bouton « PNG 1:1 avec sa resolution physique » passe
       les octets du moteur (CF.cardBlob) par `POST face/png/<fmt>/<dpi>`, qui
       REFUSE d'estampiller une trame qui ne fait pas `canvas_px`, et le
       panneau RELIT ensuite le chunk dans les octets rendus pour afficher le
       chiffre. Aucun nombre affiche ici n'est une promesse.

   (3) LE PLACEMENT SE FAIT A LA MAIN ET AU CLAVIER. Glisser sur la carte =
       deplacer, molette = zoomer autour du curseur, Alt+glisser = tourner ;
       et les MEMES valeurs sont editables au clavier en millimetres, en
       pourcents et en degres. Fleches = 1 mm, Maj+fleches = 0,1 mm.
       Ctrl+Z / Ctrl+Y annulent et retablissent.

   MIROIR — les tables et les seuils de ce fichier sont le miroir de
   `backend/app/services/cards/face.py` ; `test_cards_face.py` EXTRAIT les
   blocs marques `CF-FACE-*-BEGIN/END` d'ici et les confronte a ceux de la.
   Une derive entre l'ecran et la table de reference fait rougir le test.

   card.art ?? card.fields["art"] ?? doc.face.default_art — precedence gelee
   (spec 2.3), appliquee mot pour mot dans `resolveArtId`.

   LECTURE POUR LES AUTRES PIECES (tolerer l'absence, ne jamais ecrire) :
     doc.face.eff_dpi  -> DPI effectif mesure au dernier rendu, en DPI reels.
                          0 = aucune illustration posee. JAMAIS negatif.
                          C'est le chiffre du controle avant vol de P7
                          (« image sous 300 DPI »).

   DEUX VERDICTS CONTRADICTOIRES SUR LE MEME OCTET — CORRIGE CE TOUR, ET LA
   MESURE QUI L'A IMPOSE. Ce champ valait -1 pour une face du CATALOGUE, avec
   le sens conventionnel « vectoriel, donc jamais sous-defini » ; P7 le lit et
   fait `if declare < 0: continue` (print.py:2932), c'est-a-dire se tait. Or la
   jauge de ce panneau ne lit plus le GENRE de la source depuis la correction
   de `rasterDpi` : elle mesure la trame livree. Releve au probe sur le lab, une
   face du catalogue, toile a 150 DPI :
       jauge      = « 150 DPI · Definition insuffisante — sous 300 DPI » (rouge)
       eff_dpi    = -1
       P7         = aucune ligne
   Le meme fichier etait donc declare sous-defini par un ecran et exempt par
   l'autre. C'est exactement le defaut du badge « 16 bits » demenit par ses
   echantillons, en pire : ici les deux verdicts sont RENDUS PAR LE MEME
   MODULE. On publie desormais le nombre mesure (150), et le controle avant vol
   de P7 rougit tout seul, sans qu'une ligne de P7 change.
   ═══════════════════════════════════════════════════════════════════════════ */
"use strict";

(function () {
  const CF = (typeof window !== "undefined") ? window.CF : null;
  if (!CF) throw new Error("mod-face: js/core.js doit etre charge avant ce fichier");

  /* ═══════════════════════════════════════════════════════════════════════
     0. SEUILS — miroir de cards/face.py
     ═══════════════════════════════════════════════════════════════════════ */
  const DPI_TARGET = 300;              /* jauge verte a partir d'ici */
  const FID_TINT = 32;                 /* controle de fidelite : teinte / recouvrement */
  const FIT_MODES = ["cover", "contain", "free"];
  const MAX_IMPORT_PX = 4096;          /* cote long au-dela : re-echelonne */
  const SCALE_MIN = 0.05, SCALE_MAX = 12.0;
  const PAL_STRIDE = 5, COMPO_STRIDE = 2;
  const AI_SIZES = [
    ["portrait_4_3", "Portrait 3:4"],
    ["portrait_16_9", "Portrait 9:16"],
    ["square_hd", "Carré HD"],
  ];

  /* ═══════════════════════════════════════════════════════════════════════
     1. LE CATALOGUE — une TABLE, pas un dossier de PNG
     ═══════════════════════════════════════════════════════════════════════ */
  /* CF-FACE-PALETTES-BEGIN */
  const PALETTES = [
    { id: "ember", label: "Braise", dark: true, sky: ["#2a0d0a", "#6d1f12", "#c2521f"], sun: "#ffd08a", far: "#3b1410", mid: "#26100e", near: "#140807", subj: "#0b0505", glow: "#ff8a3c" },
    { id: "frost", label: "Givre", dark: false, sky: ["#0b2135", "#2b6a8f", "#bfe6f2"], sun: "#ffffff", far: "#4f8aa8", mid: "#2d5c76", near: "#16303e", subj: "#0d1f2a", glow: "#8fdcff" },
    { id: "verdant", label: "Sylve", dark: false, sky: ["#0f2416", "#2f5a2c", "#a8c66c"], sun: "#f6f1c0", far: "#3d6b39", mid: "#26451f", near: "#132612", subj: "#0a1a0b", glow: "#b8e06a" },
    { id: "dusk", label: "Crépuscule", dark: true, sky: ["#1b1033", "#5b2a6b", "#e0736a"], sun: "#ffd9a0", far: "#432a5c", mid: "#2b1a3d", near: "#170e22", subj: "#0c0714", glow: "#ff9d7a" },
    { id: "abyss", label: "Abysse", dark: true, sky: ["#01131b", "#053a4a", "#0d7f86"], sun: "#9ff6ea", far: "#063241", mid: "#04222d", near: "#02141b", subj: "#010b10", glow: "#37e0d0" },
    { id: "gold", label: "Or", dark: false, sky: ["#2b1c05", "#8a5f12", "#f0c25a"], sun: "#fff3c4", far: "#5c3f10", mid: "#3a280b", near: "#211605", subj: "#120c03", glow: "#ffd166" },
    { id: "ash", label: "Cendre", dark: false, sky: ["#15171a", "#3a3f45", "#8b9299"], sun: "#e6ebef", far: "#4a5158", mid: "#2e3339", near: "#1a1d21", subj: "#0d0f11", glow: "#c3ccd4" },
    { id: "storm", label: "Orage", dark: true, sky: ["#0a1020", "#22304d", "#5b7aa8"], sun: "#dbe7ff", far: "#2b3a57", mid: "#1a2439", near: "#0f1524", subj: "#070b13", glow: "#7fb2ff" },
    { id: "bloom", label: "Floraison", dark: false, sky: ["#2a0f24", "#7a2b55", "#f3a6b8"], sun: "#fff0f3", far: "#5a2340", mid: "#3a1529", near: "#210c18", subj: "#120510", glow: "#ff8fb0" },
    { id: "void", label: "Néant", dark: true, sky: ["#050510", "#12122a", "#2a2350"], sun: "#cbb8ff", far: "#1a1838", mid: "#111027", near: "#080816", subj: "#04040c", glow: "#9b7bff" },
    { id: "sand", label: "Sable", dark: false, sky: ["#3a2410", "#9a6a2f", "#f3d79a"], sun: "#fff6dd", far: "#7a5528", mid: "#553a1b", near: "#31200f", subj: "#1a1108", glow: "#ffcf87" },
    { id: "jade", label: "Jade", dark: true, sky: ["#04211f", "#0d5c52", "#7fd6bd"], sun: "#e9fff6", far: "#12564c", mid: "#0b3a34", near: "#06231f", subj: "#03120f", glow: "#5ff0c8" },
  ];
  /* CF-FACE-PALETTES-END */

  /* CF-FACE-SUBJECTS-BEGIN */
  const SUBJECTS = [
    { id: "tower", label: "Tour de guet" },
    { id: "pines", label: "Forêt de pins" },
    { id: "monolith", label: "Portail de pierre" },
    { id: "dragon", label: "Dragon" },
    { id: "sphinx", label: "Sphinx de garde" },
    { id: "portal", label: "Portail arcanique" },
    { id: "crystals", label: "Cristaux" },
    { id: "ship", label: "Navire" },
    { id: "wolf", label: "Loup" },
    { id: "knight", label: "Chevalier" },
    { id: "citadel", label: "Citadelle" },
    { id: "whale", label: "Baleine céleste" },
    { id: "phoenix", label: "Phénix" },
    { id: "serpent", label: "Serpent des mers" },
    { id: "golem", label: "Golem de pierre" },
    { id: "archer", label: "Archère" },
    { id: "grimoire", label: "Grimoire" },
    { id: "beacon", label: "Brasier" },
  ];
  /* CF-FACE-SUBJECTS-END */

  /* CF-FACE-COMPOS-BEGIN */
  /* CE QUI A CHANGE, ET POURQUOI. Les deux critiques ont compté a la main :
     « 72 faces » n'etait qu'un meme dessin recolore six fois, et les vignettes
     montraient toutes la MEME composition — ciel en degrade, une lune, des
     couches de montagnes, une silhouette. Le seuil « >= 60 » etait tenu a la
     lettre et trahi dans l'esprit. La COMPOSITION est la reponse : elle ne
     change pas la teinte, elle change le monde. `medallion` n'a AUCUN
     horizon ; `heraldry` est un aplat symetrique sans ciel ; `depths` est une
     colonne d'eau ; `backlight` n'a qu'un disque enorme et un sol plat, sans
     une seule crete ; `stained` est une baie de vitrail a reseau de plomb.
     18 sujets x 6 compositions = 108 dessins REELLEMENT distincts, et la
     palette reste un reglage a part. Le compte est passe de 72 a 108 pour
     franchir le palier de 100 que le duel a nomme : la barre sert 300 dessins
     BITMAP, plafonnes a 723x1024 ; les notres se redessinent a n'importe
     quelle definition. */
  const COMPOS = [
    { id: "vista", label: "Panorama" },
    { id: "medallion", label: "Médaillon" },
    { id: "heraldry", label: "Blason" },
    { id: "depths", label: "Profondeurs" },
    { id: "backlight", label: "Contre-jour" },
    { id: "stained", label: "Vitrail" },
  ];
  /* CF-FACE-COMPOS-END */

  /* CF-FACE-SERIES-BEGIN */
  /* LES VOIES D'ILLUSTRATION (phase 5, D1). Le catalogue vectoriel est le
     SOCLE : 108 dessins calcules ici, zero octet de reseau, nets a n'importe
     quelle definition. La serie « affiche polonaise » est une SECONDE VOIE
     posee a cote — les MEMES 108 cases (memes sujets, memes compositions,
     memes noms), habillees d'images peintes dans un langage visuel mesure.
     Elle ne remplace rien : une case sans image retombe sur son dessin, et la
     vignette le DIT (l'insigne « vectoriel »). Le choix de voie est porte par
     `doc.face.serie`, donc par le DOCUMENT : il voyage avec le jeu — a
     l'export, a la duplication, sur un autre poste. Une preference
     d'application aurait fait de la meme carte deux cartes differentes selon
     la machine qui l'ouvre. Miroir de cards/face.py:SERIES. */
  const SERIES = [
    { id: "vectoriel", label: "Vectoriel" },
    { id: "walkuski", label: "Affiche polonaise" },
  ];
  /* CF-FACE-SERIES-END */

  const PAL_BY = {}, SUB_BY = {}, COM_BY = {};
  PALETTES.forEach((p) => { PAL_BY[p.id] = p; });
  SUBJECTS.forEach((s) => { SUB_BY[s.id] = s; });
  COMPOS.forEach((c) => { COM_BY[c.id] = c; });

  /* FNV-1a 32 bits — le meme des deux cotes (cards/face.py:fnv1a32). */
  function fnv1a32(s) {
    let h = 2166136261 >>> 0;
    for (let i = 0; i < s.length; i++) {
      h ^= (s.charCodeAt(i) & 0xff);
      h = Math.imul(h, 16777619) >>> 0;
    }
    return h >>> 0;
  }

  /* Miroir exact de cards/face.py:scene_of. (5*s + 2*c) % 12 : chaque palette
     sort EXACTEMENT 9 fois, et les 12 apparaissent dans CHAQUE composition
     (verifie par test, des deux cotes).
     CE QUI A CHANGE, ET POURQUOI. Le pas de composition valait 3 : avec 4
     compositions il donnait 6 sorties par palette, PILE. Avec 6 compositions
     3c ne prend que quatre valeurs (0,3,6,9,0,3), les tirages ne se
     repartissent plus et le compte tombait entre 8 et 10. Le pas 2 donne six
     decalages distincts (0,2,4,6,8,10) : 9 pile pour chacune des 12. Un
     equilibre annonce doit se verifier, pas s'esperer. */
  function buildCatalog() {
    const out = [];
    for (let si = 0; si < SUBJECTS.length; si++) {
      for (let ci = 0; ci < COMPOS.length; ci++) {
        const sub = SUBJECTS[si].id, compo = COMPOS[ci].id;
        const pal = PALETTES[(si * PAL_STRIDE + ci * COMPO_STRIDE) % PALETTES.length].id;
        const fid = "face_" + pal + "_" + compo + "_" + sub;
        out.push({
          id: fid,
          label: SUB_BY[sub].label + " — " + COM_BY[compo].label,
          palette: pal, compo: compo, subject: sub,
          seed: fnv1a32(fid), vector: true,
        });
      }
    }
    return out;
  }
  const CATALOG = buildCatalog();
  const CAT_BY = {};
  CATALOG.forEach((c) => { CAT_BY[c.id] = c; });
  const DRAWINGS = SUBJECTS.length * COMPOS.length;      /* 108 dessins */
  const COMBINATIONS = DRAWINGS * PALETTES.length;       /* 1296 combinaisons */

  /* ── L'ETAT DE LA SERIE — lu au backend, jamais devine ────────────────────
     `SERIE.cases` mappe « <compo>_<sujet> » vers le fichier du magasin
     d'images. Tant qu'il est vide (et il l'est tant que la campagne n'a pas
     tourne), la voie « affiche polonaise » montre 108 dessins vectoriels
     marques comme tels : un ecran honnete a l'etat zero. */
  let SERIE = { cases: {}, refus: {}, faites: 0, total: 0, depense: 0,
    plafond: 0, ok: false };

  async function serieLoad() {
    try {
      const r = await M.api.get("serie");
      SERIE = {
        cases: (r && r.cases) || {}, refus: (r && r.refus) || {},
        faites: Number((r && r.faites) || 0),
        total: Number((r && r.total) || DRAWINGS),
        depense: Number((r && r.depense_totale_usd) || 0),
        plafond: Number((r && r.plafond_usd) || 0), ok: true,
      };
    } catch (e) {
      /* Un backend plus ancien n'a pas cette route : la voie de serie reste
         offerte et VIDE, ce qui la rend entierement vectorielle — jamais une
         grille de vignettes cassees. */
      SERIE = { cases: {}, refus: {}, faites: 0, total: DRAWINGS, depense: 0,
        plafond: 0, ok: false };
    }
  }

  /* La voie active, DERIVEE de l'etat : une valeur inconnue dans le document
     (jeu venu d'une version future, fichier retouche a la main) retombe sur
     le vectoriel plutot que de vider la grille. */
  function serieActive() {
    const s = String(CF.get("face.serie", "vectoriel") || "vectoriel");
    for (let i = 0; i < SERIES.length; i++) {
      if (SERIES[i].id === s) return s === "vectoriel" ? "" : s;
    }
    return "";
  }
  function serieCase(c) { return c.compo + "_" + c.subject; }
  function serieLabel() {
    const id = serieActive();
    for (let i = 0; i < SERIES.length; i++) {
      if (SERIES[i].id === id) return SERIES[i].label;
    }
    return SERIES[0].label;
  }
  /* Le fichier de la case, ou "" — et "" veut dire « le dessin ». */
  function serieImg(c) {
    if (!serieActive()) return "";
    const e = SERIE.cases[serieCase(c)];
    return (e && e.img) ? String(e.img) : "";
  }
  /* La source que POSE une vignette : `img:` pour une case peinte, `cat:`
     pour un dessin. Pas de quatrieme schema — une case de serie EST un
     fichier du magasin d'images. */
  function tileSrc(c) {
    const f = serieImg(c);
    return f ? "img:" + f : "cat:" + c.id;
  }

  /* Le meme dessin dans une autre palette — c'est un identifiant, pas un
     filtre : la face reste deterministe (meme graine = memes montagnes). */
  function recolored(id, palId) {
    const c = CAT_BY[String(id || "").replace(/^cat:/, "")];
    if (!c || !PAL_BY[palId]) return null;
    return "face_" + palId + "_" + c.compo + "_" + c.subject;
  }
  /* Un jeu enregistre AVANT les compositions porte « face_<pal>_<sujet> ». Il
     doit rouvrir sur son dessin, pas sur un cadre vide. Miroir de
     cards/face.py:legacy_art_id.
     RENOMMAGES DE SUJET : un sujet retire du catalogue emporterait avec lui
     toutes les cartes qui le portaient. On garde donc la table de rappel —
     `octopus` devient `sphinx` (le catalogue de depart d'un
     logiciel n'a pas a embarquer la mascotte de son editeur), les jeux
     enregistres continuent d'ouvrir sur un dessin. */
  const SUB_RENAMES = { octopus: "sphinx" };
  function legacyArtId(id) {
    let s = String(id || "");
    const r = /^face_([a-z]+)_([a-z]+)_([a-z]+)$/.exec(s);
    if (r && SUB_RENAMES[r[3]]) s = "face_" + r[1] + "_" + r[2] + "_" + SUB_RENAMES[r[3]];
    const m = /^face_([a-z]+)_([a-z]+)$/.exec(s);
    if (!m || !PAL_BY[m[1]]) return s;
    const sub = SUB_RENAMES[m[2]] || m[2];
    if (!SUB_BY[sub]) return s;
    return "face_" + m[1] + "_vista_" + sub;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     2. LE PEINTRE DE SCENES — deterministe, sans resolution
     ═══════════════════════════════════════════════════════════════════════ */
  function mulberry32(a) {
    let t = a >>> 0;
    return function () {
      t = (t + 0x6D2B79F5) >>> 0;
      let x = Math.imul(t ^ (t >>> 15), 1 | t);
      x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
      return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
    };
  }
  function hexa(hex, a) {
    const h = String(hex).replace("#", "");
    const n = parseInt(h.length === 3 ? h[0] + h[0] + h[1] + h[1] + h[2] + h[2] : h, 16);
    return "rgba(" + ((n >> 16) & 255) + "," + ((n >> 8) & 255) + "," + (n & 255) + "," + a + ")";
  }
  function mixHex(a, b, t) {
    const pa = parseInt(String(a).slice(1), 16), pb = parseInt(String(b).slice(1), 16);
    const r = Math.round(((pa >> 16) & 255) * (1 - t) + ((pb >> 16) & 255) * t);
    const g = Math.round(((pa >> 8) & 255) * (1 - t) + ((pb >> 8) & 255) * t);
    const bl = Math.round((pa & 255) * (1 - t) + (pb & 255) * t);
    return "rgb(" + r + "," + g + "," + bl + ")";
  }

  function ridgeline(W, y0, amp, iters, R) {
    let pts = [[0, y0 + (R() - 0.5) * amp], [W, y0 + (R() - 0.5) * amp]];
    for (let it = 0; it < iters; it++) {
      const next = [pts[0]];
      const d = amp * Math.pow(0.56, it);
      for (let i = 0; i < pts.length - 1; i++) {
        const a = pts[i], b = pts[i + 1];
        next.push([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + (R() - 0.5) * d * 2], b);
      }
      pts = next;
    }
    return pts;
  }
  function fillRidge(ctx, pts, W, H, color) {
    ctx.beginPath();
    ctx.moveTo(0, H);
    ctx.lineTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.lineTo(W, H);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();
  }
  /* silhouette : remplissage plein + liseré de lumiere au bord */
  function sil(ctx, P, u) {
    ctx.fillStyle = P.subj;
    ctx.fill();
    ctx.strokeStyle = hexa(P.glow, 0.5);
    ctx.lineWidth = Math.max(0.6, u * 0.6);
    ctx.stroke();
  }

  /* ── les 12 sujets. Chacun dessine une SILHOUETTE ancrée sur l'horizon. ── */
  const SUB_PAINT = {
    tower(ctx, W, H, hz, P, R, u) {
      const cx = W * (0.34 + R() * 0.32), hgt = H * (0.30 + R() * 0.10), wd = hgt * 0.20;
      ctx.beginPath();
      ctx.moveTo(cx - wd * 0.62, hz + u * 2);
      ctx.lineTo(cx - wd * 0.44, hz - hgt * 0.86);
      ctx.lineTo(cx - wd * 0.70, hz - hgt * 0.86);
      ctx.lineTo(cx - wd * 0.70, hz - hgt);
      for (let i = 0; i < 5; i++) {
        const x0 = cx - wd * 0.70 + (wd * 1.40) * (i / 5);
        ctx.lineTo(x0, hz - hgt);
        ctx.lineTo(x0, hz - hgt - hgt * 0.045);
        ctx.lineTo(x0 + wd * 0.16, hz - hgt - hgt * 0.045);
        ctx.lineTo(x0 + wd * 0.16, hz - hgt);
      }
      ctx.lineTo(cx + wd * 0.70, hz - hgt);
      ctx.lineTo(cx + wd * 0.70, hz - hgt * 0.86);
      ctx.lineTo(cx + wd * 0.44, hz - hgt * 0.86);
      ctx.lineTo(cx + wd * 0.62, hz + u * 2);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.fillStyle = hexa(P.glow, 0.85);
      ctx.fillRect(cx - wd * 0.11, hz - hgt * 0.58, wd * 0.22, hgt * 0.13);
      ctx.fillRect(cx - wd * 0.09, hz - hgt * 0.34, wd * 0.18, hgt * 0.10);
    },
    pines(ctx, W, H, hz, P, R, u) {
      const n = 7 + Math.floor(R() * 4);
      for (let i = 0; i < n; i++) {
        const x = W * (0.06 + 0.88 * (i + R() * 0.6) / n);
        const hgt = H * (0.13 + R() * 0.17), wd = hgt * 0.34;
        const base = hz + H * 0.015 * R();
        ctx.beginPath();
        ctx.moveTo(x, base - hgt);
        for (let k = 3; k >= 1; k--) {
          const t = k / 3, y = base - hgt * t;
          ctx.lineTo(x + wd * (1 - t) * 0.9, y + hgt * 0.05);
          ctx.lineTo(x + wd * (1 - t) * 0.55, y + hgt * 0.05);
        }
        ctx.lineTo(x + wd * 0.10, base);
        ctx.lineTo(x - wd * 0.10, base);
        for (let k = 1; k <= 3; k++) {
          const t = k / 3, y = base - hgt * t;
          ctx.lineTo(x - wd * (1 - t) * 0.55, y + hgt * 0.05);
          ctx.lineTo(x - wd * (1 - t) * 0.9, y + hgt * 0.05);
        }
        ctx.closePath();
        sil(ctx, P, u);
      }
    },
    monolith(ctx, W, H, hz, P, R, u) {
      const cx = W * 0.5, hgt = H * (0.24 + R() * 0.08), wd = hgt * 0.62;
      const leg = wd * 0.24;
      ctx.beginPath();
      ctx.moveTo(cx - wd / 2 - leg * 0.15, hz + u);
      ctx.lineTo(cx - wd / 2 + leg * 0.10, hz - hgt * 0.82);
      ctx.lineTo(cx - wd / 2 + leg, hz - hgt * 0.82);
      ctx.lineTo(cx - wd / 2 + leg * 1.05, hz + u);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx + wd / 2 + leg * 0.15, hz + u);
      ctx.lineTo(cx + wd / 2 - leg * 0.10, hz - hgt * 0.82);
      ctx.lineTo(cx + wd / 2 - leg, hz - hgt * 0.82);
      ctx.lineTo(cx + wd / 2 - leg * 1.05, hz + u);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx - wd * 0.60, hz - hgt * 0.80);
      ctx.lineTo(cx + wd * 0.60, hz - hgt * 0.86);
      ctx.lineTo(cx + wd * 0.56, hz - hgt);
      ctx.lineTo(cx - wd * 0.58, hz - hgt * 0.96);
      ctx.closePath();
      sil(ctx, P, u);
      const g = ctx.createLinearGradient(0, hz - hgt * 0.8, 0, hz);
      g.addColorStop(0, hexa(P.glow, 0.30));
      g.addColorStop(1, hexa(P.glow, 0.02));
      ctx.fillStyle = g;
      ctx.fillRect(cx - wd / 2 + leg, hz - hgt * 0.80, wd - leg * 2, hgt * 0.80);
    },
    dragon(ctx, W, H, hz, P, R, u) {
      const cx = W * (0.42 + R() * 0.16), cy = hz - H * (0.20 + R() * 0.12);
      const s = Math.min(W, H) * (0.30 + R() * 0.08);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.quadraticCurveTo(cx - s * 0.55, cy - s * 0.66, cx - s * 1.02, cy - s * 0.20);
      ctx.quadraticCurveTo(cx - s * 0.72, cy - s * 0.16, cx - s * 0.60, cy + s * 0.10);
      ctx.quadraticCurveTo(cx - s * 0.34, cy - s * 0.02, cx, cy + s * 0.06);
      ctx.quadraticCurveTo(cx + s * 0.34, cy - s * 0.02, cx + s * 0.60, cy + s * 0.10);
      ctx.quadraticCurveTo(cx + s * 0.72, cy - s * 0.16, cx + s * 1.02, cy - s * 0.20);
      ctx.quadraticCurveTo(cx + s * 0.55, cy - s * 0.66, cx, cy);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.10, cy - s * 0.05);
      ctx.quadraticCurveTo(cx + s * 0.30, cy + s * 0.30, cx + s * 0.16, cy + s * 0.62);
      ctx.quadraticCurveTo(cx + s * 0.44, cy + s * 0.44, cx + s * 0.30, cy + s * 0.10);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.06, cy - s * 0.04);
      ctx.quadraticCurveTo(cx - s * 0.26, cy - s * 0.12, cx - s * 0.38, cy - s * 0.04);
      ctx.quadraticCurveTo(cx - s * 0.28, cy + s * 0.06, cx - s * 0.06, cy + s * 0.04);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.fillStyle = hexa(P.glow, 0.95);
      ctx.beginPath();
      ctx.arc(cx - s * 0.30, cy - s * 0.03, Math.max(u * 0.8, s * 0.022), 0, 6.2832);
      ctx.fill();
    },
    /* SPHINX — corps couché de profil, pattes avant tendues, tête coiffée
       d'un nemes, aile repliée. Remplace le sujet retire du catalogue : celui
       d'un logiciel n'a pas a embarquer la mascotte de son editeur, dont la
       silhouette se reconnaissait a l'oeil sur les vignettes. */
    sphinx(ctx, W, H, hz, P, R, u) {
      const cx = W * (0.40 + R() * 0.18), s = Math.min(W, H) * (0.20 + R() * 0.05);
      const base = hz + u;
      /* socle */
      ctx.beginPath();
      ctx.rect(cx - s * 1.35, base - s * 0.16, s * 2.70, s * 0.16);
      sil(ctx, P, u);
      /* corps couche */
      ctx.beginPath();
      ctx.moveTo(cx - s * 1.20, base - s * 0.16);
      ctx.quadraticCurveTo(cx - s * 1.05, base - s * 0.92, cx - s * 0.30, base - s * 0.98);
      ctx.quadraticCurveTo(cx + s * 0.62, base - s * 1.02, cx + s * 1.02, base - s * 0.60);
      ctx.quadraticCurveTo(cx + s * 1.22, base - s * 0.32, cx + s * 1.16, base - s * 0.16);
      ctx.closePath();
      sil(ctx, P, u);
      /* pattes avant tendues */
      [[-1.16, 0.30], [-0.86, 0.22]].forEach((p) => {
        ctx.beginPath();
        ctx.moveTo(cx + s * p[0], base - s * 0.16);
        ctx.lineTo(cx + s * (p[0] + 0.10), base - s * (0.16 + p[1] + 0.30));
        ctx.lineTo(cx + s * (p[0] + 0.34), base - s * (0.16 + p[1] + 0.26));
        ctx.lineTo(cx + s * (p[0] + 0.30), base - s * 0.16);
        ctx.closePath();
        sil(ctx, P, u);
      });
      /* aile repliee */
      ctx.beginPath();
      ctx.moveTo(cx + s * 0.12, base - s * 0.96);
      ctx.quadraticCurveTo(cx + s * 0.86, base - s * 1.30, cx + s * 1.04, base - s * 0.74);
      ctx.quadraticCurveTo(cx + s * 0.72, base - s * 0.86, cx + s * 0.44, base - s * 0.72);
      ctx.quadraticCurveTo(cx + s * 0.30, base - s * 0.86, cx + s * 0.12, base - s * 0.96);
      ctx.closePath();
      sil(ctx, P, u);
      /* poitrail et cou */
      ctx.beginPath();
      ctx.moveTo(cx - s * 1.02, base - s * 0.80);
      ctx.quadraticCurveTo(cx - s * 1.10, base - s * 1.40, cx - s * 0.80, base - s * 1.66);
      ctx.lineTo(cx - s * 0.34, base - s * 1.60);
      ctx.quadraticCurveTo(cx - s * 0.30, base - s * 1.10, cx - s * 0.34, base - s * 0.94);
      ctx.closePath();
      sil(ctx, P, u);
      /* nemes : deux pans qui s'evasent */
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.86, base - s * 1.58);
      ctx.quadraticCurveTo(cx - s * 0.72, base - s * 2.26, cx - s * 0.06, base - s * 2.20);
      ctx.quadraticCurveTo(cx + s * 0.18, base - s * 2.10, cx + s * 0.12, base - s * 1.62);
      ctx.lineTo(cx - s * 0.10, base - s * 1.70);
      ctx.quadraticCurveTo(cx - s * 0.20, base - s * 1.94, cx - s * 0.48, base - s * 1.92);
      ctx.quadraticCurveTo(cx - s * 0.66, base - s * 1.88, cx - s * 0.66, base - s * 1.56);
      ctx.closePath();
      sil(ctx, P, u);
      /* visage */
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.62, base - s * 1.88);
      ctx.quadraticCurveTo(cx - s * 0.68, base - s * 1.50, cx - s * 0.34, base - s * 1.42);
      ctx.quadraticCurveTo(cx - s * 0.02, base - s * 1.48, cx - s * 0.06, base - s * 1.88);
      ctx.quadraticCurveTo(cx - s * 0.34, base - s * 2.02, cx - s * 0.62, base - s * 1.88);
      ctx.closePath();
      sil(ctx, P, u);
      /* barbe postiche */
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.42, base - s * 1.44);
      ctx.lineTo(cx - s * 0.26, base - s * 1.44);
      ctx.lineTo(cx - s * 0.30, base - s * 1.18);
      ctx.lineTo(cx - s * 0.40, base - s * 1.18);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.fillStyle = hexa(P.glow, 0.92);
      [-0.50, -0.20].forEach((t) => {
        ctx.beginPath();
        ctx.ellipse(cx + s * t, base - s * 1.76, s * 0.075, s * 0.045, 0, 0, 6.2832);
        ctx.fill();
      });
      ctx.fillStyle = hexa(P.sun, 0.55);
      for (let i = 0; i < 4; i++) {
        ctx.fillRect(cx - s * (0.80 - i * 0.06), base - s * (2.06 - i * 0.10), s * 0.62, s * 0.030);
      }
    },
    portal(ctx, W, H, hz, P, R, u) {
      const cx = W * 0.5, hgt = H * (0.30 + R() * 0.08), wd = hgt * 0.62;
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(cx - wd / 2, hz);
      ctx.lineTo(cx - wd / 2, hz - hgt * 0.55);
      ctx.arc(cx, hz - hgt * 0.55, wd / 2, Math.PI, 0);
      ctx.lineTo(cx + wd / 2, hz);
      ctx.closePath();
      const g = ctx.createRadialGradient(cx, hz - hgt * 0.5, 0, cx, hz - hgt * 0.5, wd);
      g.addColorStop(0, hexa(P.glow, 0.95));
      g.addColorStop(0.6, hexa(P.glow, 0.35));
      g.addColorStop(1, hexa(P.sun, 0.05));
      ctx.fillStyle = g;
      ctx.fill();
      ctx.restore();
      ctx.beginPath();
      ctx.moveTo(cx - wd / 2 - wd * 0.16, hz + u);
      ctx.lineTo(cx - wd / 2 - wd * 0.16, hz - hgt * 0.58);
      ctx.arc(cx, hz - hgt * 0.58, wd / 2 + wd * 0.16, Math.PI, 0);
      ctx.lineTo(cx + wd / 2 + wd * 0.16, hz + u);
      ctx.lineTo(cx + wd / 2, hz + u);
      ctx.lineTo(cx + wd / 2, hz - hgt * 0.55);
      ctx.arc(cx, hz - hgt * 0.55, wd / 2, 0, Math.PI, true);
      ctx.lineTo(cx - wd / 2, hz + u);
      ctx.closePath();
      sil(ctx, P, u);
      for (let i = 0; i < 9; i++) {
        const a = Math.PI + Math.PI * (i + 0.5) / 9, r = wd / 2 + wd * 0.08;
        ctx.fillStyle = hexa(P.sun, 0.7);
        ctx.beginPath();
        ctx.arc(cx + Math.cos(a) * r, hz - hgt * 0.58 + Math.sin(a) * r, Math.max(u * 0.7, wd * 0.018), 0, 6.2832);
        ctx.fill();
      }
    },
    crystals(ctx, W, H, hz, P, R, u) {
      const cx = W * (0.38 + R() * 0.24);
      for (let i = 0; i < 6; i++) {
        const t = (i - 2.5) / 2.5;
        const x = cx + t * Math.min(W, H) * 0.20;
        const hgt = H * (0.10 + R() * 0.22) * (1 - Math.abs(t) * 0.35);
        const wd = hgt * (0.16 + R() * 0.10);
        const lean = (R() - 0.5) * wd * 1.4;
        ctx.beginPath();
        ctx.moveTo(x + lean, hz - hgt);
        ctx.lineTo(x + wd, hz - hgt * 0.62);
        ctx.lineTo(x + wd * 0.72, hz + u);
        ctx.lineTo(x - wd * 0.72, hz + u);
        ctx.lineTo(x - wd, hz - hgt * 0.62);
        ctx.closePath();
        sil(ctx, P, u);
        const g = ctx.createLinearGradient(x, hz - hgt, x, hz);
        g.addColorStop(0, hexa(P.glow, 0.75));
        g.addColorStop(1, hexa(P.glow, 0.05));
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.moveTo(x + lean, hz - hgt);
        ctx.lineTo(x + wd * 0.42, hz - hgt * 0.52);
        ctx.lineTo(x - wd * 0.12, hz);
        ctx.lineTo(x - wd * 0.42, hz - hgt * 0.55);
        ctx.closePath();
        ctx.fill();
      }
    },
    ship(ctx, W, H, hz, P, R, u) {
      const cx = W * (0.38 + R() * 0.26), s = Math.min(W, H) * (0.26 + R() * 0.08);
      const base = hz - s * 0.02;
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.62, base - s * 0.16);
      ctx.quadraticCurveTo(cx, base + s * 0.14, cx + s * 0.66, base - s * 0.18);
      ctx.lineTo(cx + s * 0.58, base - s * 0.24);
      ctx.quadraticCurveTo(cx, base - s * 0.02, cx - s * 0.56, base - s * 0.22);
      ctx.closePath();
      sil(ctx, P, u);
      [[-0.20, 1.00], [0.22, 0.78]].forEach((m) => {
        const mx = cx + s * m[0], mh = s * m[1];
        ctx.beginPath();
        ctx.rect(mx - s * 0.014, base - s * 0.20 - mh, s * 0.028, mh);
        sil(ctx, P, u);
        ctx.beginPath();
        ctx.moveTo(mx, base - s * 0.24 - mh * 0.94);
        ctx.quadraticCurveTo(mx + s * 0.30, base - s * 0.24 - mh * 0.50, mx + s * 0.04, base - s * 0.24 - mh * 0.10);
        ctx.lineTo(mx, base - s * 0.24 - mh * 0.10);
        ctx.closePath();
        sil(ctx, P, u);
      });
    },
    wolf(ctx, W, H, hz, P, R, u) {
      const cx = W * (0.36 + R() * 0.26), s = Math.min(W, H) * (0.20 + R() * 0.06);
      const base = hz - s * 0.04;
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.95, base + s * 0.20);
      ctx.quadraticCurveTo(cx - s * 0.40, base - s * 0.16, cx + s * 0.30, base - s * 0.06);
      ctx.quadraticCurveTo(cx + s * 0.90, base - s * 0.02, cx + s * 1.05, base + s * 0.24);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.42, base - s * 0.06);
      ctx.quadraticCurveTo(cx - s * 0.16, base - s * 0.16, cx + s * 0.02, base - s * 0.60);
      ctx.lineTo(cx + s * 0.14, base - s * 0.86);
      ctx.lineTo(cx + s * 0.02, base - s * 0.80);
      ctx.lineTo(cx - s * 0.06, base - s * 0.94);
      ctx.lineTo(cx - s * 0.18, base - s * 0.78);
      ctx.quadraticCurveTo(cx - s * 0.34, base - s * 0.62, cx - s * 0.30, base - s * 0.30);
      ctx.quadraticCurveTo(cx - s * 0.30, base - s * 0.10, cx - s * 0.52, base - s * 0.02);
      ctx.quadraticCurveTo(cx - s * 0.70, base + s * 0.06, cx - s * 0.66, base + s * 0.20);
      ctx.lineTo(cx - s * 0.20, base + s * 0.14);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.fillStyle = hexa(P.glow, 0.9);
      ctx.beginPath();
      ctx.arc(cx - s * 0.10, base - s * 0.62, Math.max(u * 0.7, s * 0.03), 0, 6.2832);
      ctx.fill();
    },
    knight(ctx, W, H, hz, P, R, u) {
      const cx = W * (0.40 + R() * 0.20), s = Math.min(W, H) * (0.30 + R() * 0.06);
      const base = hz + u;
      ctx.beginPath();
      ctx.rect(cx + s * 0.30, base - s * 1.02, s * 0.030, s * 1.02);
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx + s * 0.315, base - s * 1.20);
      ctx.lineTo(cx + s * 0.40, base - s * 0.98);
      ctx.lineTo(cx + s * 0.23, base - s * 0.98);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.10, base - s * 0.74);
      ctx.quadraticCurveTo(cx - s * 0.46, base - s * 0.46, cx - s * 0.38, base);
      ctx.lineTo(cx + s * 0.26, base);
      ctx.quadraticCurveTo(cx + s * 0.26, base - s * 0.48, cx + s * 0.10, base - s * 0.76);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.11, base - s * 0.74);
      ctx.quadraticCurveTo(cx - s * 0.13, base - s * 0.96, cx, base - s * 0.98);
      ctx.quadraticCurveTo(cx + s * 0.13, base - s * 0.96, cx + s * 0.11, base - s * 0.74);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx, base - s * 0.99);
      ctx.quadraticCurveTo(cx + s * 0.18, base - s * 1.22, cx - s * 0.02, base - s * 1.30);
      ctx.quadraticCurveTo(cx + s * 0.02, base - s * 1.12, cx - s * 0.06, base - s * 0.99);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.fillStyle = hexa(P.glow, 0.85);
      ctx.fillRect(cx - s * 0.07, base - s * 0.87, s * 0.14, s * 0.030);
    },
    citadel(ctx, W, H, hz, P, R, u) {
      const n = 6;
      const base = hz + u;
      for (let i = 0; i < n; i++) {
        const x = W * (0.12 + 0.76 * i / (n - 1));
        const hgt = H * (0.12 + R() * 0.22), wd = hgt * (0.20 + R() * 0.10);
        ctx.beginPath();
        ctx.moveTo(x - wd / 2, base);
        ctx.lineTo(x - wd / 2, base - hgt);
        ctx.lineTo(x, base - hgt - wd * 0.85);
        ctx.lineTo(x + wd / 2, base - hgt);
        ctx.lineTo(x + wd / 2, base);
        ctx.closePath();
        sil(ctx, P, u);
        ctx.fillStyle = hexa(P.glow, 0.8);
        ctx.fillRect(x - wd * 0.09, base - hgt * 0.72, wd * 0.18, hgt * 0.10);
      }
      ctx.beginPath();
      ctx.rect(W * 0.06, base - H * 0.075, W * 0.88, H * 0.075);
      sil(ctx, P, u);
      for (let i = 0; i < 12; i++) {
        ctx.fillStyle = P.subj;
        ctx.fillRect(W * 0.06 + (W * 0.88) * i / 12, base - H * 0.095, W * 0.038, H * 0.022);
      }
    },
    whale(ctx, W, H, hz, P, R, u) {
      const cx = W * (0.44 + R() * 0.14), cy = hz - H * (0.22 + R() * 0.10);
      const s = Math.min(W, H) * (0.34 + R() * 0.08);
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.86, cy + s * 0.02);
      ctx.quadraticCurveTo(cx - s * 0.30, cy - s * 0.34, cx + s * 0.52, cy - s * 0.14);
      ctx.quadraticCurveTo(cx + s * 0.82, cy - s * 0.06, cx + s * 0.72, cy + s * 0.06);
      ctx.quadraticCurveTo(cx + s * 0.92, cy + s * 0.22, cx + s * 0.86, cy + s * 0.36);
      ctx.quadraticCurveTo(cx + s * 0.58, cy + s * 0.22, cx + s * 0.42, cy + s * 0.20);
      ctx.quadraticCurveTo(cx - s * 0.24, cy + s * 0.30, cx - s * 0.86, cy + s * 0.02);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.02, cy + s * 0.16);
      ctx.quadraticCurveTo(cx + s * 0.10, cy + s * 0.52, cx - s * 0.24, cy + s * 0.50);
      ctx.quadraticCurveTo(cx - s * 0.14, cy + s * 0.32, cx - s * 0.20, cy + s * 0.16);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.fillStyle = hexa(P.glow, 0.9);
      ctx.beginPath();
      ctx.arc(cx + s * 0.44, cy - s * 0.02, Math.max(u * 0.8, s * 0.026), 0, 6.2832);
      ctx.fill();
      for (let i = 0; i < 7; i++) {
        ctx.fillStyle = hexa(P.sun, 0.35 + R() * 0.35);
        ctx.beginPath();
        ctx.arc(cx - s * (0.9 + R() * 0.7), cy + s * (R() - 0.5) * 0.7, s * (0.010 + R() * 0.020), 0, 6.2832);
        ctx.fill();
      }
    },
    phoenix(ctx, W, H, hz, P, R, u) {
      const cx = W * (0.44 + R() * 0.12), cy = hz - H * (0.20 + R() * 0.10);
      const s = Math.min(W, H) * (0.28 + R() * 0.07);
      [-1, 1].forEach((d) => {
        ctx.beginPath();
        ctx.moveTo(cx + d * s * 0.10, cy);
        ctx.quadraticCurveTo(cx + d * s * 0.70, cy - s * 0.92, cx + d * s * 1.06, cy - s * 0.30);
        ctx.quadraticCurveTo(cx + d * s * 0.86, cy - s * 0.36, cx + d * s * 0.78, cy - s * 0.14);
        ctx.quadraticCurveTo(cx + d * s * 0.66, cy - s * 0.30, cx + d * s * 0.52, cy - s * 0.06);
        ctx.quadraticCurveTo(cx + d * s * 0.40, cy - s * 0.22, cx + d * s * 0.10, cy + s * 0.06);
        ctx.closePath();
        sil(ctx, P, u);
      });
      ctx.beginPath();
      ctx.moveTo(cx, cy - s * 0.30);
      ctx.quadraticCurveTo(cx + s * 0.16, cy - s * 0.06, cx + s * 0.10, cy + s * 0.30);
      ctx.quadraticCurveTo(cx + s * 0.30, cy + s * 0.72, cx + s * 0.02, cy + s * 1.06);
      ctx.quadraticCurveTo(cx - s * 0.06, cy + s * 0.74, cx - s * 0.22, cy + s * 0.92);
      ctx.quadraticCurveTo(cx - s * 0.14, cy + s * 0.46, cx - s * 0.10, cy + s * 0.28);
      ctx.quadraticCurveTo(cx - s * 0.16, cy - s * 0.06, cx, cy - s * 0.30);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.09, cy - s * 0.26);
      ctx.quadraticCurveTo(cx - s * 0.02, cy - s * 0.52, cx + s * 0.10, cy - s * 0.40);
      ctx.lineTo(cx + s * 0.24, cy - s * 0.36);
      ctx.lineTo(cx + s * 0.09, cy - s * 0.28);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.fillStyle = hexa(P.glow, 0.95);
      ctx.beginPath();
      ctx.arc(cx + s * 0.03, cy - s * 0.38, Math.max(u * 0.7, s * 0.024), 0, 6.2832);
      ctx.fill();
      for (let i = 0; i < 9; i++) {
        ctx.fillStyle = hexa(P.glow, 0.20 + R() * 0.45);
        ctx.beginPath();
        ctx.ellipse(cx + (R() - 0.5) * s * 2.2, cy + s * (0.2 + R() * 1.1),
          s * 0.012, s * (0.03 + R() * 0.05), 0, 0, 6.2832);
        ctx.fill();
      }
    },
    serpent(ctx, W, H, hz, P, R, u) {
      const s = Math.min(W, H) * (0.16 + R() * 0.05);
      const y0 = hz - s * 0.10;
      const n = 3;
      for (let i = 0; i < n; i++) {
        const x = W * (0.16 + 0.30 * i) + (R() - 0.5) * W * 0.05;
        const wd = s * (1.05 - i * 0.16), ht = s * (0.72 - i * 0.10);
        ctx.beginPath();
        ctx.moveTo(x - wd / 2, y0 + s * 0.06);
        ctx.quadraticCurveTo(x, y0 - ht, x + wd / 2, y0 + s * 0.06);
        ctx.quadraticCurveTo(x, y0 - ht * 0.60, x - wd / 2, y0 + s * 0.06);
        ctx.closePath();
        sil(ctx, P, u);
      }
      const hx = W * 0.78, hy = y0 - s * (1.35 + R() * 0.35);
      ctx.beginPath();
      ctx.moveTo(hx - s * 0.24, y0 + s * 0.04);
      ctx.quadraticCurveTo(hx - s * 0.40, hy + s * 0.55, hx - s * 0.10, hy + s * 0.12);
      ctx.quadraticCurveTo(hx + s * 0.06, hy - s * 0.24, hx + s * 0.44, hy - s * 0.10);
      ctx.quadraticCurveTo(hx + s * 0.20, hy + s * 0.16, hx + s * 0.30, hy + s * 0.34);
      ctx.quadraticCurveTo(hx - s * 0.02, hy + s * 0.42, hx + s * 0.04, y0 + s * 0.04);
      ctx.closePath();
      sil(ctx, P, u);
      [-0.06, 0.10, 0.26].forEach((t) => {
        ctx.beginPath();
        ctx.moveTo(hx - s * 0.12, hy + s * (0.30 + t));
        ctx.lineTo(hx - s * 0.34, hy + s * (0.12 + t));
        ctx.lineTo(hx - s * 0.10, hy + s * (0.16 + t));
        ctx.closePath();
        sil(ctx, P, u);
      });
      ctx.fillStyle = hexa(P.glow, 0.95);
      ctx.beginPath();
      ctx.arc(hx + s * 0.16, hy + s * 0.02, Math.max(u * 0.8, s * 0.045), 0, 6.2832);
      ctx.fill();
    },
    golem(ctx, W, H, hz, P, R, u) {
      const cx = W * (0.40 + R() * 0.20), s = Math.min(W, H) * (0.13 + R() * 0.04);
      const base = hz + u;
      const box = (x, y, w2, h2) => {
        ctx.beginPath();
        ctx.moveTo(x - w2, y);
        ctx.lineTo(x - w2 * 0.86, y - h2);
        ctx.lineTo(x + w2 * 0.92, y - h2 * 0.94);
        ctx.lineTo(x + w2, y);
        ctx.closePath();
        sil(ctx, P, u);
      };
      box(cx - s * 0.62, base, s * 0.30, s * 0.92);
      box(cx + s * 0.62, base, s * 0.30, s * 0.86);
      box(cx, base - s * 0.84, s * 1.00, s * 1.32);
      box(cx - s * 1.24, base - s * 1.10, s * 0.26, s * 0.96);
      box(cx + s * 1.24, base - s * 1.02, s * 0.26, s * 0.90);
      box(cx, base - s * 2.16, s * 0.52, s * 0.62);
      ctx.fillStyle = hexa(P.glow, 0.9);
      ctx.beginPath();
      ctx.arc(cx, base - s * 1.42, Math.max(u, s * 0.22), 0, 6.2832);
      ctx.fill();
      ctx.fillStyle = hexa(P.glow, 0.75);
      ctx.fillRect(cx - s * 0.30, base - s * 2.44, s * 0.18, s * 0.09);
      ctx.fillRect(cx + s * 0.12, base - s * 2.44, s * 0.18, s * 0.09);
      for (let i = 0; i < 5; i++) {
        ctx.fillStyle = hexa(P.sun, 0.10 + R() * 0.14);
        ctx.fillRect(cx - s * (0.9 - R() * 1.8), base - s * (0.9 + R() * 1.2), s * 0.16, s * 0.05);
      }
    },
    archer(ctx, W, H, hz, P, R, u) {
      const cx = W * (0.40 + R() * 0.18), s = Math.min(W, H) * (0.26 + R() * 0.06);
      const base = hz + u;
      ctx.beginPath();
      ctx.arc(cx + s * 0.34, base - s * 0.74, s * 0.52, -1.15, 1.15);
      ctx.strokeStyle = P.subj;
      ctx.lineWidth = Math.max(1.2, s * 0.045);
      ctx.stroke();
      ctx.strokeStyle = hexa(P.glow, 0.45);
      ctx.lineWidth = Math.max(0.6, u * 0.6);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(cx + s * 0.55, base - s * 1.20);
      ctx.lineTo(cx + s * 0.10, base - s * 0.74);
      ctx.lineTo(cx + s * 0.55, base - s * 0.28);
      ctx.strokeStyle = hexa(P.sun, 0.85);
      ctx.lineWidth = Math.max(0.8, s * 0.014);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.30, base);
      ctx.lineTo(cx - s * 0.16, base - s * 0.60);
      ctx.lineTo(cx + s * 0.04, base - s * 0.62);
      ctx.lineTo(cx + s * 0.16, base);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.20, base - s * 0.58);
      ctx.quadraticCurveTo(cx - s * 0.34, base - s * 0.92, cx - s * 0.08, base - s * 1.02);
      ctx.quadraticCurveTo(cx + s * 0.16, base - s * 1.00, cx + s * 0.12, base - s * 0.58);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.02, base - s * 1.00);
      ctx.quadraticCurveTo(cx - s * 0.16, base - s * 1.26, cx + s * 0.06, base - s * 1.30);
      ctx.quadraticCurveTo(cx + s * 0.24, base - s * 1.28, cx + s * 0.18, base - s * 1.00);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx + s * 0.02, base - s * 0.88);
      ctx.lineTo(cx + s * 0.34, base - s * 0.76);
      ctx.lineTo(cx + s * 0.02, base - s * 0.68);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.20, base - s * 0.86);
      ctx.quadraticCurveTo(cx - s * 0.52, base - s * 0.70, cx - s * 0.44, base - s * 0.20);
      ctx.quadraticCurveTo(cx - s * 0.30, base - s * 0.56, cx - s * 0.14, base - s * 0.72);
      ctx.closePath();
      sil(ctx, P, u);
    },
    grimoire(ctx, W, H, hz, P, R, u) {
      const cx = W * 0.5, cy = hz - H * (0.16 + R() * 0.06);
      const s = Math.min(W, H) * (0.26 + R() * 0.05);
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.94, cy + s * 0.10);
      ctx.quadraticCurveTo(cx - s * 0.46, cy - s * 0.20, cx, cy - s * 0.02);
      ctx.quadraticCurveTo(cx + s * 0.46, cy - s * 0.20, cx + s * 0.94, cy + s * 0.10);
      ctx.quadraticCurveTo(cx + s * 0.48, cy + s * 0.16, cx, cy + s * 0.30);
      ctx.quadraticCurveTo(cx - s * 0.48, cy + s * 0.16, cx - s * 0.94, cy + s * 0.10);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.94, cy + s * 0.10);
      ctx.lineTo(cx - s * 0.90, cy + s * 0.32);
      ctx.quadraticCurveTo(cx - s * 0.44, cy + s * 0.38, cx, cy + s * 0.52);
      ctx.quadraticCurveTo(cx + s * 0.44, cy + s * 0.38, cx + s * 0.90, cy + s * 0.32);
      ctx.lineTo(cx + s * 0.94, cy + s * 0.10);
      ctx.quadraticCurveTo(cx + s * 0.48, cy + s * 0.16, cx, cy + s * 0.30);
      ctx.quadraticCurveTo(cx - s * 0.48, cy + s * 0.16, cx - s * 0.94, cy + s * 0.10);
      ctx.closePath();
      sil(ctx, P, u);
      const gg = ctx.createLinearGradient(cx, cy - s * 0.90, cx, cy + s * 0.10);
      gg.addColorStop(0, hexa(P.glow, 0));
      gg.addColorStop(1, hexa(P.glow, 0.55));
      ctx.fillStyle = gg;
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.34, cy + s * 0.06);
      ctx.lineTo(cx - s * 0.66, cy - s * 0.92);
      ctx.lineTo(cx + s * 0.66, cy - s * 0.92);
      ctx.lineTo(cx + s * 0.34, cy + s * 0.06);
      ctx.closePath();
      ctx.fill();
      for (let i = 0; i < 11; i++) {
        const a = R() * 6.2832, rr = s * (0.30 + R() * 0.62);
        ctx.fillStyle = hexa(P.sun, 0.35 + R() * 0.5);
        ctx.fillRect(cx + Math.cos(a) * rr * 0.9, cy - s * 0.40 + Math.sin(a) * rr * 0.5,
          s * 0.035, s * 0.035);
      }
      ctx.strokeStyle = hexa(P.sun, 0.55);
      ctx.lineWidth = Math.max(0.8, s * 0.018);
      ctx.beginPath();
      ctx.arc(cx, cy - s * 0.52, s * 0.30, 0.2, 5.4);
      ctx.stroke();
    },
    beacon(ctx, W, H, hz, P, R, u) {
      const cx = W * (0.42 + R() * 0.16), s = Math.min(W, H) * (0.22 + R() * 0.05);
      const base = hz + u;
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.46, base);
      ctx.lineTo(cx - s * 0.20, base - s * 0.86);
      ctx.lineTo(cx + s * 0.20, base - s * 0.86);
      ctx.lineTo(cx + s * 0.46, base);
      ctx.closePath();
      sil(ctx, P, u);
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.62, base - s * 0.86);
      ctx.quadraticCurveTo(cx, base - s * 0.62, cx + s * 0.62, base - s * 0.86);
      ctx.lineTo(cx + s * 0.52, base - s * 1.04);
      ctx.lineTo(cx - s * 0.52, base - s * 1.04);
      ctx.closePath();
      sil(ctx, P, u);
      const fg = ctx.createLinearGradient(cx, base - s * 2.20, cx, base - s * 0.96);
      fg.addColorStop(0, hexa(P.sun, 0.95));
      fg.addColorStop(0.45, hexa(P.glow, 0.90));
      fg.addColorStop(1, hexa(P.glow, 0.25));
      ctx.fillStyle = fg;
      ctx.beginPath();
      ctx.moveTo(cx - s * 0.36, base - s * 1.00);
      ctx.quadraticCurveTo(cx - s * 0.46, base - s * 1.60, cx - s * 0.06, base - s * 2.14);
      ctx.quadraticCurveTo(cx - s * 0.02, base - s * 1.66, cx + s * 0.16, base - s * 1.92);
      ctx.quadraticCurveTo(cx + s * 0.20, base - s * 1.50, cx + s * 0.40, base - s * 1.00);
      ctx.closePath();
      ctx.fill();
      for (let i = 0; i < 10; i++) {
        ctx.fillStyle = hexa(P.sun, 0.25 + R() * 0.5);
        ctx.beginPath();
        ctx.arc(cx + (R() - 0.5) * s * 1.5, base - s * (1.9 + R() * 1.3), s * (0.012 + R() * 0.026), 0, 6.2832);
        ctx.fill();
      }
      const rg2 = ctx.createRadialGradient(cx, base - s * 1.5, 0, cx, base - s * 1.5, s * 3.2);
      rg2.addColorStop(0, hexa(P.glow, 0.30));
      rg2.addColorStop(1, hexa(P.glow, 0));
      ctx.fillStyle = rg2;
      ctx.fillRect(cx - s * 3.2, base - s * 4.7, s * 6.4, s * 6.4);
    },
  };

  /* ── LES 4 COMPOSITIONS ────────────────────────────────────────────────
     Chacune recoit le peintre de sujet et decide OU le sujet est ancre, a
     quelle taille, et ce qu'il y a autour. Aucune ne connait la resolution :
     tout est en fraction de W et de H, donc identique a 300 et a 600 DPI. */

  /* Le sujet, redimensionne autour de son ancrage. `u` est divise par k pour
     que le lisere de lumiere garde la meme epaisseur apparente. */
  function drawSubject(ctx, W, H, hz, P, R, u, fp, k) {
    if (!(k > 0) || Math.abs(k - 1) < 1e-6) { fp(ctx, W, H, hz, P, R, u); return; }
    ctx.save();
    ctx.translate(W / 2, hz);
    ctx.scale(k, k);
    ctx.translate(-W / 2, -hz);
    fp(ctx, W, H, hz, P, R, u / k);
    ctx.restore();
  }
  /* Pour le blason : le reflet doit etre le MEME dessin, pas un autre tirage.
     On enregistre les tirages du premier passage et on les rejoue. */
  function recorder(R) {
    const log = [];
    const f = () => { const v = R(); log.push(v); return v; };
    f.log = log;
    return f;
  }
  function replayer(log) {
    let i = 0;
    return () => (log.length ? log[i++ % log.length] : 0.5);
  }

  const COMPO_PAINT = {
    /* PANORAMA — horizon, cretes, lune, brume. La composition d'origine. */
    vista(ctx, W, H, P, R, u, fp) {
      const g = ctx.createLinearGradient(0, 0, 0, H);
      g.addColorStop(0, P.sky[0]);
      g.addColorStop(0.55, P.sky[1]);
      g.addColorStop(1, P.sky[2]);
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, W, H);

      const hz = H * (0.62 + R() * 0.08);
      if (P.dark) {
        for (let i = 0; i < 110; i++) {
          const x = R() * W, y = R() * hz * 0.94;
          ctx.fillStyle = hexa(P.sun, 0.10 + R() * 0.65);
          ctx.fillRect(x, y, u * (0.5 + R()), u * (0.5 + R()));
        }
      }
      const dx = W * (0.22 + R() * 0.56), dy = hz - H * (0.10 + R() * 0.22);
      const dr = Math.min(W, H) * (0.055 + R() * 0.05);
      const rg = ctx.createRadialGradient(dx, dy, 0, dx, dy, dr * 7);
      rg.addColorStop(0, hexa(P.glow, 0.50));
      rg.addColorStop(0.30, hexa(P.glow, 0.14));
      rg.addColorStop(1, hexa(P.glow, 0));
      ctx.fillStyle = rg;
      ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = P.sun;
      ctx.beginPath();
      ctx.arc(dx, dy, dr, 0, 6.2832);
      ctx.fill();

      for (let i = 0; i < 5; i++) {
        const y = hz - H * (0.06 + R() * 0.42), hh = H * (0.006 + R() * 0.018);
        ctx.fillStyle = hexa(P.sun, 0.05 + R() * 0.09);
        ctx.beginPath();
        ctx.ellipse(W * R(), y, W * (0.18 + R() * 0.34), hh, 0, 0, 6.2832);
        ctx.fill();
      }

      fillRidge(ctx, ridgeline(W, hz - H * 0.11, H * 0.10, 6, R), W, H, mixHex(P.far, P.sky[2], 0.28));
      fillRidge(ctx, ridgeline(W, hz - H * 0.035, H * 0.075, 6, R), W, H, P.far);
      fillRidge(ctx, ridgeline(W, hz + H * 0.004, H * 0.05, 6, R), W, H, P.mid);

      fp(ctx, W, H, hz, P, R, u);

      const fog = ctx.createLinearGradient(0, hz - H * 0.10, 0, hz + H * 0.10);
      fog.addColorStop(0, hexa(P.sun, 0));
      fog.addColorStop(0.5, hexa(P.sun, 0.14));
      fog.addColorStop(1, hexa(P.sun, 0));
      ctx.fillStyle = fog;
      ctx.fillRect(0, hz - H * 0.10, W, H * 0.20);

      fillRidge(ctx, ridgeline(W, H * 0.93, H * 0.055, 6, R), W, H, P.near);

      const vg = ctx.createRadialGradient(W / 2, H * 0.46, Math.min(W, H) * 0.16, W / 2, H * 0.5, Math.max(W, H) * 0.78);
      vg.addColorStop(0, "rgba(0,0,0,0)");
      vg.addColorStop(1, "rgba(0,0,0,.55)");
      ctx.fillStyle = vg;
      ctx.fillRect(0, 0, W, H);
    },

    /* MEDAILLON — aucun horizon, aucune montagne : un disque de lumiere, un
       anneau, le sujet en gros plan. */
    medallion(ctx, W, H, P, R, u, fp) {
      const bg = ctx.createLinearGradient(0, 0, 0, H);
      bg.addColorStop(0, P.near);
      bg.addColorStop(0.5, mixHex(P.mid, P.near, 0.45));
      bg.addColorStop(1, P.subj);
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, W, H);

      /* Le foyer est HAUT (0,42 H) : une carte a cadre ne montre de
         l'illustration qu'une bande, celle du haut. Un medaillon centre a
         mi-hauteur disparaissait derriere le cadre — mesure faite a l'ecran
         sur la fenetre publiee par P2 (6,6 mm -> 51 mm sur 88). */
      const cx = W / 2, cy = H * 0.42, rad = Math.min(W, H) * (0.40 + R() * 0.03);
      const halo = ctx.createRadialGradient(cx, cy, rad * 0.10, cx, cy, rad * 1.35);
      halo.addColorStop(0, hexa(P.glow, 0.55));
      halo.addColorStop(0.55, hexa(P.glow, 0.16));
      halo.addColorStop(1, hexa(P.glow, 0));
      ctx.fillStyle = halo;
      ctx.fillRect(0, 0, W, H);

      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, rad, 0, 6.2832);
      ctx.clip();
      const disc = ctx.createLinearGradient(0, cy - rad, 0, cy + rad);
      disc.addColorStop(0, mixHex(P.sky[1], P.sun, 0.34));
      disc.addColorStop(1, P.sky[0]);
      ctx.fillStyle = disc;
      ctx.fillRect(cx - rad, cy - rad, rad * 2, rad * 2);
      for (let i = 0; i < 26; i++) {
        const a = (i / 26) * 6.2832 + R() * 0.05;
        ctx.fillStyle = hexa(P.sun, 0.03 + (i % 2) * 0.05);
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(a) * rad * 1.5, cy + Math.sin(a) * rad * 1.5);
        ctx.lineTo(cx + Math.cos(a + 0.11) * rad * 1.5, cy + Math.sin(a + 0.11) * rad * 1.5);
        ctx.closePath();
        ctx.fill();
      }
      const hzm = cy + rad * 0.50;
      drawSubject(ctx, W, H, hzm, P, R, u, fp, 1.16);
      ctx.fillStyle = hexa(P.subj, 0.55);
      ctx.beginPath();
      ctx.ellipse(cx, hzm + rad * 0.05, rad * 0.86, rad * 0.10, 0, 0, 6.2832);
      ctx.fill();
      ctx.restore();

      ctx.strokeStyle = hexa(P.sun, 0.85);
      ctx.lineWidth = Math.max(1.2, Math.min(W, H) * 0.010);
      ctx.beginPath();
      ctx.arc(cx, cy, rad, 0, 6.2832);
      ctx.stroke();
      ctx.strokeStyle = hexa(P.glow, 0.55);
      ctx.lineWidth = Math.max(0.8, Math.min(W, H) * 0.004);
      ctx.beginPath();
      ctx.arc(cx, cy, rad * 1.075, 0, 6.2832);
      ctx.stroke();
      for (let i = 0; i < 12; i++) {
        const a = (i / 12) * 6.2832;
        ctx.fillStyle = hexa(P.sun, 0.75);
        ctx.beginPath();
        ctx.arc(cx + Math.cos(a) * rad * 1.075, cy + Math.sin(a) * rad * 1.075,
          Math.max(u, Math.min(W, H) * 0.007), 0, 6.2832);
        ctx.fill();
      }
      /* ecoincons : quatre arcs de coin, la ou le paysage n'existe pas */
      ctx.strokeStyle = hexa(P.sun, 0.30);
      ctx.lineWidth = Math.max(0.8, Math.min(W, H) * 0.005);
      [[0, 0, 1, 1], [W, 0, -1, 1], [0, H, 1, -1], [W, H, -1, -1]].forEach((c) => {
        ctx.beginPath();
        ctx.moveTo(c[0], c[1] + c[3] * H * 0.10);
        ctx.quadraticCurveTo(c[0], c[1], c[0] + c[2] * W * 0.14, c[1]);
        ctx.stroke();
      });
      const vg = ctx.createRadialGradient(cx, cy, rad * 0.9, cx, cy, Math.max(W, H) * 0.80);
      vg.addColorStop(0, "rgba(0,0,0,0)");
      vg.addColorStop(1, "rgba(0,0,0,.62)");
      ctx.fillStyle = vg;
      ctx.fillRect(0, 0, W, H);
    },

    /* BLASON — aplat symetrique, ecu, sujet et son reflet. Pas de ciel. */
    heraldry(ctx, W, H, P, R, u, fp) {
      ctx.fillStyle = P.mid;
      ctx.fillRect(0, 0, W, H);
      ctx.fillStyle = mixHex(P.far, P.sky[1], 0.35);
      ctx.fillRect(0, 0, W, H * 0.26);
      ctx.fillStyle = hexa(P.sun, 0.07);
      for (let i = -6; i < 18; i++) {
        ctx.beginPath();
        ctx.moveTo(W * (i / 12), 0);
        ctx.lineTo(W * (i / 12) + W * 0.05, 0);
        ctx.lineTo(W * (i / 12) + W * 0.05 + H * 0.5, H);
        ctx.lineTo(W * (i / 12) + H * 0.5, H);
        ctx.closePath();
        ctx.fill();
      }
      ctx.strokeStyle = hexa(P.sun, 0.55);
      ctx.lineWidth = Math.max(1, Math.min(W, H) * 0.008);
      ctx.strokeRect(W * 0.055, H * 0.045, W * 0.89, H * 0.91);

      /* meme raison que le medaillon : l'ecu tient dans la moitie HAUTE. */
      const sx = W * 0.5, top = H * 0.13, bw = W * 0.35, bot = H * 0.745;
      const shield = () => {
        ctx.beginPath();
        ctx.moveTo(sx - bw, top);
        ctx.lineTo(sx + bw, top);
        ctx.lineTo(sx + bw, bot - H * 0.24);
        ctx.quadraticCurveTo(sx + bw, bot, sx, bot);
        ctx.quadraticCurveTo(sx - bw, bot, sx - bw, bot - H * 0.24);
        ctx.closePath();
      };
      shield();
      const fillg = ctx.createLinearGradient(0, top, 0, bot);
      fillg.addColorStop(0, mixHex(P.sky[1], P.sun, 0.10));
      fillg.addColorStop(1, P.sky[0]);
      ctx.fillStyle = fillg;
      ctx.fill();

      ctx.save();
      shield();
      ctx.clip();
      ctx.fillStyle = hexa(P.sun, 0.08);
      ctx.beginPath();
      ctx.moveTo(sx - bw, top);
      ctx.lineTo(sx + bw, top);
      ctx.lineTo(sx, bot);
      ctx.closePath();
      ctx.fill();
      /* CE QUI A CHANGE, ET LA MESURE QUI L'A IMPOSE. Le bouton « Compter les
         dessins vraiment distincts » fait ce qu'un critique ferait : il peint
         les dessins DANS LA MEME PALETTE et calcule la distance de la paire
         la plus PROCHE. Verdict du premier passage : « Dragon — Blason » et
         « Archere — Blason » a 0,9 niveau/canal. Les empreintes etaient bien
         72 sur 72 distinctes — et pourtant, a couleur egale, un humain ne les
         separait pas. Un chiffre vrai a la lettre et faux dans l'esprit : la
         faute exacte que ce tour doit corriger.
         Cause mesuree : le sujet etait peint a 0,80 (le medaillon le peint a
         1,16) en silhouette P.subj, quasi noire, sur un ecu dont le degrade
         finit sur P.sky[0], la teinte la plus sombre de la palette. Le sujet
         existait, il ne SE VOYAIT pas. Correction : un fond clair derriere le
         sujet, dans l'ecu, et le sujet a 1,15. */
      const hzh = bot - H * 0.075;
      const back = ctx.createRadialGradient(sx, hzh - H * 0.16, 1,
        sx, hzh - H * 0.16, bw * 1.5);
      back.addColorStop(0, hexa(P.sun, 0.34));
      back.addColorStop(0.55, hexa(P.sun, 0.13));
      back.addColorStop(1, hexa(P.sun, 0));
      ctx.fillStyle = back;
      ctx.fillRect(sx - bw, top, bw * 2, bot - top);
      const rec = recorder(R);
      ctx.globalAlpha = 0.22;
      ctx.save();
      ctx.translate(W, 0);
      ctx.scale(-1, 1);
      drawSubject(ctx, W, H, hzh, P, rec, u, fp, 1.15);
      ctx.restore();
      ctx.globalAlpha = 1;
      drawSubject(ctx, W, H, hzh, P, replayer(rec.log), u, fp, 1.15);
      ctx.restore();

      shield();
      ctx.strokeStyle = hexa(P.sun, 0.92);
      ctx.lineWidth = Math.max(1.4, Math.min(W, H) * 0.014);
      ctx.stroke();
      ctx.strokeStyle = hexa(P.glow, 0.45);
      ctx.lineWidth = Math.max(0.7, Math.min(W, H) * 0.004);
      ctx.stroke();
      [[sx - bw, top], [sx + bw, top], [sx, bot]].forEach((p) => {
        ctx.fillStyle = hexa(P.sun, 0.9);
        ctx.beginPath();
        ctx.arc(p[0], p[1], Math.max(u * 1.2, Math.min(W, H) * 0.013), 0, 6.2832);
        ctx.fill();
      });
      ctx.fillStyle = "rgba(0,0,0,.24)";
      ctx.fillRect(0, H * 0.955, W, H * 0.045);
      ctx.fillRect(0, 0, W, H * 0.030);
    },

    /* PROFONDEURS — colonne d'eau, rais verticaux, sujet flottant, pas de
       crete de montagne. */
    depths(ctx, W, H, P, R, u, fp) {
      const g = ctx.createLinearGradient(0, 0, 0, H);
      g.addColorStop(0, mixHex(P.sky[2], P.sun, 0.20));
      g.addColorStop(0.34, P.sky[1]);
      g.addColorStop(1, P.subj);
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, W, H);

      for (let i = 0; i < 7; i++) {
        const x = W * (0.04 + R() * 0.92), wdt = W * (0.05 + R() * 0.16);
        const lean = W * (0.10 + R() * 0.24);
        ctx.fillStyle = hexa(P.sun, 0.05 + R() * 0.08);
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x + wdt, 0);
        ctx.lineTo(x + wdt + lean, H * 0.96);
        ctx.lineTo(x + lean, H * 0.96);
        ctx.closePath();
        ctx.fill();
      }
      for (let i = 0; i < 4; i++) {
        ctx.strokeStyle = hexa(P.sun, 0.10 + R() * 0.10);
        ctx.lineWidth = Math.max(0.8, Math.min(W, H) * 0.006);
        ctx.beginPath();
        const y = H * (0.03 + i * 0.045);
        ctx.moveTo(0, y);
        for (let x = 0; x <= W; x += W / 8) {
          ctx.quadraticCurveTo(x + W / 16, y + (R() - 0.5) * H * 0.030, x + W / 8, y);
        }
        ctx.stroke();
      }

      const hzd = H * (0.66 + R() * 0.04);
      const shade = ctx.createRadialGradient(W / 2, hzd - H * 0.18, 0, W / 2, hzd - H * 0.18, Math.min(W, H) * 0.62);
      shade.addColorStop(0, hexa(P.glow, 0.22));
      shade.addColorStop(1, hexa(P.glow, 0));
      ctx.fillStyle = shade;
      ctx.fillRect(0, 0, W, H);
      drawSubject(ctx, W, H, hzd, P, R, u, fp, 1.04);

      for (let i = 0; i < 90; i++) {
        ctx.fillStyle = hexa(P.sun, 0.10 + R() * 0.45);
        const rr = Math.min(W, H) * (0.002 + R() * 0.005);
        ctx.beginPath();
        ctx.arc(R() * W, R() * H, rr, 0, 6.2832);
        ctx.fill();
      }
      fillRidge(ctx, ridgeline(W, H * 0.965, H * 0.028, 5, R), W, H, P.subj);
      const vg = ctx.createLinearGradient(0, H * 0.55, 0, H);
      vg.addColorStop(0, "rgba(0,0,0,0)");
      vg.addColorStop(1, "rgba(0,0,0,.55)");
      ctx.fillStyle = vg;
      ctx.fillRect(0, H * 0.55, W, H * 0.45);
      const vg2 = ctx.createRadialGradient(W / 2, H * 0.42, Math.min(W, H) * 0.22, W / 2, H * 0.5, Math.max(W, H) * 0.82);
      vg2.addColorStop(0, "rgba(0,0,0,0)");
      vg2.addColorStop(1, "rgba(0,0,0,.45)");
      ctx.fillStyle = vg2;
      ctx.fillRect(0, 0, W, H);
    },

    /* CONTRE-JOUR — un seul disque enorme derriere le sujet, un sol plat, des
       bandes de brume horizontales. AUCUNE crete, AUCUNE etoile, AUCUNE lune
       de coin : c'est ce qui la separe du panorama, qui en vit. Le sujet est
       deja peint en `P.subj` (la teinte la plus sombre de la palette) : le
       contre-jour est donc la composition ou la silhouette se lit le mieux. */
    backlight(ctx, W, H, P, R, u, fp) {
      const hz = H * (0.74 + R() * 0.05);
      const g = ctx.createLinearGradient(0, 0, 0, hz);
      g.addColorStop(0, P.sky[0]);
      g.addColorStop(0.62, mixHex(P.sky[1], P.sky[0], 0.35));
      g.addColorStop(1, mixHex(P.sky[2], P.sun, 0.45));
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, W, hz);

      /* le disque : il tient les deux tiers de la largeur et sort du cadre */
      const dx = W * (0.42 + R() * 0.16), dr = Math.min(W, H) * (0.44 + R() * 0.07);
      const halo = ctx.createRadialGradient(dx, hz, dr * 0.25, dx, hz, dr * 2.1);
      halo.addColorStop(0, hexa(P.sun, 0.55));
      halo.addColorStop(0.42, hexa(P.glow, 0.20));
      halo.addColorStop(1, hexa(P.glow, 0));
      ctx.fillStyle = halo;
      ctx.fillRect(0, 0, W, hz);
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, 0, W, hz);
      ctx.clip();
      const disc = ctx.createRadialGradient(dx, hz - dr * 0.25, dr * 0.05, dx, hz - dr * 0.25, dr);
      disc.addColorStop(0, P.sun);
      disc.addColorStop(0.72, mixHex(P.sun, P.glow, 0.55));
      disc.addColorStop(1, mixHex(P.glow, P.sky[1], 0.30));
      ctx.fillStyle = disc;
      ctx.beginPath();
      ctx.arc(dx, hz - dr * 0.25, dr, 0, 6.2832);
      ctx.fill();
      /* bandes de brume : elles COUPENT le disque, c'est la signature */
      for (let i = 0; i < 9; i++) {
        const y = hz - dr * (0.05 + i * 0.20) - R() * H * 0.010;
        ctx.fillStyle = hexa(P.sky[0], 0.10 + R() * 0.22);
        ctx.fillRect(0, y, W, Math.max(u, H * (0.006 + R() * 0.014)));
      }
      ctx.restore();

      fp(ctx, W, H, hz, P, R, u);

      /* sol : un aplat, pas une crete. Un liseré de lumiere le separe du ciel. */
      ctx.fillStyle = hexa(P.sun, 0.75);
      ctx.fillRect(0, hz - Math.max(u, H * 0.004), W, Math.max(u, H * 0.004));
      const gr = ctx.createLinearGradient(0, hz, 0, H);
      gr.addColorStop(0, P.subj);
      gr.addColorStop(1, mixHex(P.subj, P.near, 0.45));
      ctx.fillStyle = gr;
      ctx.fillRect(0, hz, W, H - hz);
      /* poussieres qui montent dans la lumiere */
      for (let i = 0; i < 40; i++) {
        ctx.fillStyle = hexa(P.sun, 0.10 + R() * 0.40);
        const rr = Math.min(W, H) * (0.002 + R() * 0.005);
        ctx.beginPath();
        ctx.arc(R() * W, hz - R() * H * 0.55, rr, 0, 6.2832);
        ctx.fill();
      }
      const vg = ctx.createLinearGradient(0, 0, 0, H * 0.32);
      vg.addColorStop(0, "rgba(0,0,0,.50)");
      vg.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = vg;
      ctx.fillRect(0, 0, W, H * 0.32);
    },

    /* VITRAIL — une baie en arc brisé, un reseau de plomb, des verres
       colores, une rosace. Le sujet est du PLOMB : il se lit en negatif sur
       le verre. Ni ciel en degrade, ni horizon, ni disque : rien de commun
       avec le medaillon, qui est un disque cerclé sur un fond peint. */
    stained(ctx, W, H, P, R, u, fp) {
      const lead = P.subj;
      ctx.fillStyle = lead;
      ctx.fillRect(0, 0, W, H);

      const mx = W * 0.10, my = H * 0.06;
      const bw = W - mx * 2, bh = H - my * 2;
      const apex = my, spring = my + bh * 0.34;
      const baie = () => {
        ctx.beginPath();
        ctx.moveTo(mx, my + bh);
        ctx.lineTo(mx, spring);
        ctx.quadraticCurveTo(mx + bw * 0.16, apex, mx + bw / 2, apex);
        ctx.quadraticCurveTo(mx + bw * 0.84, apex, mx + bw, spring);
        ctx.lineTo(mx + bw, my + bh);
        ctx.closePath();
      };

      ctx.save();
      baie();
      ctx.clip();
      /* le verre : un damier irregulier de panneaux, chacun dans une teinte
         de la palette, chacun cerne de plomb */
      const cols = 5, rows = 8;
      const cw = bw / cols, ch = bh / rows;
      const verres = [P.sky[0], P.sky[1], P.sky[2], P.far, P.mid, P.glow, P.sun];
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const k = Math.floor(R() * verres.length);
          ctx.fillStyle = verres[k];
          ctx.globalAlpha = 0.55 + R() * 0.40;
          ctx.fillRect(mx + c * cw, my + r * ch, cw, ch);
          ctx.globalAlpha = 1;
          ctx.strokeStyle = hexa(lead, 0.95);
          ctx.lineWidth = Math.max(1.1, Math.min(W, H) * 0.009);
          ctx.strokeRect(mx + c * cw, my + r * ch, cw, ch);
          /* losange central : le reseau n'est pas une grille de tableur */
          ctx.strokeStyle = hexa(lead, 0.75);
          ctx.lineWidth = Math.max(0.8, Math.min(W, H) * 0.005);
          ctx.beginPath();
          ctx.moveTo(mx + c * cw + cw / 2, my + r * ch);
          ctx.lineTo(mx + (c + 1) * cw, my + r * ch + ch / 2);
          ctx.lineTo(mx + c * cw + cw / 2, my + (r + 1) * ch);
          ctx.lineTo(mx + c * cw, my + r * ch + ch / 2);
          ctx.closePath();
          ctx.stroke();
        }
      }
      /* la lumiere derriere le sujet */
      const hzv = my + bh * 0.86;
      const back = ctx.createRadialGradient(W / 2, hzv - bh * 0.24, 1, W / 2, hzv - bh * 0.24, bw * 0.92);
      back.addColorStop(0, hexa(P.sun, 0.72));
      back.addColorStop(0.45, hexa(P.glow, 0.28));
      back.addColorStop(1, hexa(P.glow, 0));
      ctx.fillStyle = back;
      ctx.fillRect(mx, my, bw, bh);
      /* la rosace, dans le tympan */
      const rx = W / 2, ry = my + bh * 0.14, rr = bw * 0.17;
      ctx.fillStyle = hexa(P.sun, 0.85);
      ctx.beginPath();
      ctx.arc(rx, ry, rr * 0.34, 0, 6.2832);
      ctx.fill();
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * 6.2832;
        ctx.fillStyle = hexa(verres[i % verres.length], 0.9);
        ctx.beginPath();
        ctx.arc(rx + Math.cos(a) * rr * 0.68, ry + Math.sin(a) * rr * 0.68, rr * 0.28, 0, 6.2832);
        ctx.fill();
        ctx.strokeStyle = hexa(lead, 0.9);
        ctx.lineWidth = Math.max(1, Math.min(W, H) * 0.006);
        ctx.stroke();
      }
      ctx.strokeStyle = hexa(lead, 0.95);
      ctx.lineWidth = Math.max(1.4, Math.min(W, H) * 0.012);
      ctx.beginPath();
      ctx.arc(rx, ry, rr, 0, 6.2832);
      ctx.stroke();
      /* le sujet, en plomb, pose au bas de la baie */
      drawSubject(ctx, W, H, hzv, P, R, u, fp, 1.10);
      ctx.restore();

      /* meneaux et remplage : deux montants verticaux qui traversent la baie */
      ctx.save();
      baie();
      ctx.clip();
      ctx.fillStyle = hexa(lead, 0.92);
      [0.34, 0.66].forEach((t) => {
        ctx.fillRect(mx + bw * t - Math.max(1.2, bw * 0.011), spring * 0.995,
          Math.max(2.4, bw * 0.022), my + bh - spring);
      });
      ctx.fillRect(mx, my + bh * 0.58, bw, Math.max(2.4, bh * 0.012));
      ctx.restore();

      /* la pierre autour */
      baie();
      ctx.strokeStyle = hexa(P.sun, 0.80);
      ctx.lineWidth = Math.max(2, Math.min(W, H) * 0.018);
      ctx.stroke();
      ctx.strokeStyle = hexa(P.glow, 0.40);
      ctx.lineWidth = Math.max(0.8, Math.min(W, H) * 0.005);
      ctx.stroke();
      const vg = ctx.createRadialGradient(W / 2, H * 0.46, Math.min(W, H) * 0.30, W / 2, H * 0.5, Math.max(W, H) * 0.80);
      vg.addColorStop(0, "rgba(0,0,0,0)");
      vg.addColorStop(1, "rgba(0,0,0,.50)");
      ctx.fillStyle = vg;
      ctx.fillRect(0, 0, W, H);
    },
  };

  /* LE peintre de scene. Aucune notion de « petit » ou de « grand » : il
     dessine dans la boite qu'on lui donne, a la resolution qu'on lui donne. */
  function paintScene(ctx, W, H, palId, subId, seed, compoId) {
    const P = PAL_BY[palId] || PALETTES[0];
    const C = COMPO_PAINT[compoId] || COMPO_PAINT.vista;
    const R = mulberry32(seed >>> 0);
    const u = Math.max(0.75, Math.min(W, H) / 420);
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, W, H);
    ctx.clip();
    C(ctx, W, H, P, R, u, SUB_PAINT[subId] || SUB_PAINT.tower);
    ctx.restore();
  }

  /* ═══════════════════════════════════════════════════════════════════════
     3. LA PILE DE FACES IMPORTEES — IndexedDB, donc AUCUN octet reseau
     ═══════════════════════════════════════════════════════════════════════ */
  const DB_NAME = "dz_cardforge_face", DB_STORE = "faces";
  let DBP = null, DB_OK = true;
  const PILE = [];                       /* [{key,name,type,w,h,bytes,url}] */

  function db() {
    if (DBP) return DBP;
    DBP = new Promise((res, rej) => {
      if (typeof indexedDB === "undefined") { rej(new Error("IndexedDB absent")); return; }
      const r = indexedDB.open(DB_NAME, 1);
      r.onupgradeneeded = () => {
        const d = r.result;
        if (!d.objectStoreNames.contains(DB_STORE)) d.createObjectStore(DB_STORE, { keyPath: "key" });
      };
      r.onsuccess = () => res(r.result);
      r.onerror = () => rej(r.error || new Error("IndexedDB refuse"));
    });
    return DBP;
  }
  function tx(mode, fn) {
    return db().then((d) => new Promise((res, rej) => {
      const t = d.transaction(DB_STORE, mode);
      const rq = fn(t.objectStore(DB_STORE));
      t.onerror = () => rej(t.error);
      t.onabort = () => rej(t.error);
      rq.onsuccess = () => res(rq.result);
      rq.onerror = () => rej(rq.error);
    }));
  }
  async function pileLoad() {
    try {
      const rows = await tx("readonly", (s) => s.getAll());
      rows.sort((a, b) => (b.added || 0) - (a.added || 0));
      rows.forEach((r) => {
        try { r.url = URL.createObjectURL(r.blob); } catch (e) { r.url = ""; }
        PILE.push(r);
      });
    } catch (e) { DB_OK = false; console.warn("mod-face: IndexedDB indisponible", e); }
  }
  async function pilePut(rec) {
    if (!DB_OK) return;
    try { await tx("readwrite", (s) => s.put(rec)); } catch (e) { DB_OK = false; }
  }
  async function pileDel(key) {
    if (DB_OK) { try { await tx("readwrite", (s) => s.delete(key)); } catch (e) { /* memoire seule */ } }
    for (let i = PILE.length - 1; i >= 0; i--) if (PILE[i].key === key) PILE.splice(i, 1);
  }

  function blobDims(blob) {
    return new Promise((res, rej) => {
      const url = URL.createObjectURL(blob);
      const im = new Image();
      im.onload = () => { res({ w: im.naturalWidth, h: im.naturalHeight, img: im, url: url }); };
      im.onerror = () => { URL.revokeObjectURL(url); rej(new Error("fichier illisible comme image")); };
      im.src = url;
    });
  }
  function downscale(img, w, h, maxSide) {
    const k = maxSide / Math.max(w, h);
    const nw = Math.max(1, Math.round(w * k)), nh = Math.max(1, Math.round(h * k));
    const cv = document.createElement("canvas");
    cv.width = nw; cv.height = nh;
    const c = cv.getContext("2d");
    c.imageSmoothingEnabled = true;
    try { c.imageSmoothingQuality = "high"; } catch (e) { /* moteur ancien */ }
    c.drawImage(img, 0, 0, nw, nh);
    return new Promise((res) => cv.toBlob((b) => res({ blob: b, w: nw, h: nh }), "image/png"));
  }

  async function importFiles(list) {
    const files = Array.prototype.slice.call(list || []).filter((f) => /^image\//.test(f.type || ""));
    if (!files.length) { CF.toast("aucune image dans ce qui a été déposé", true); return []; }
    const added = [];
    CF.busy(true, "import de " + files.length + " illustration(s)…");
    try {
      for (let i = 0; i < files.length; i++) {
        const f = files[i];
        let d;
        try { d = await blobDims(f); }
        catch (e) { CF.toast(f.name + " : " + e.message, true); continue; }
        let blob = f, w = d.w, h = d.h;
        /* CE QUI SE FAISAIT SANS LE DIRE, ET C'EST UN CHIFFRE FAUX A L'ECRAN.
           Au-dela de MAX_IMPORT_PX de cote, le fichier depose est REDUIT ici
           meme, puis la vignette et la jauge annoncaient « source 3072 x 4096 »
           pour un fichier de 4500 x 6000 px : la grandeur affichee n'etait plus
           celle du fichier de l'utilisateur, et rien a l'ecran ne l'indiquait.
           Le DPI calcule dessus est juste — c'est bien cette trame-la qui part
           a l'impression — mais un nombre juste presente comme la mesure d'AUTRE
           CHOSE reste un nombre faux. On garde donc les deux tailles et la
           vignette les montre toutes les deux. */
        if (Math.max(w, h) > MAX_IMPORT_PX) {
          const r = await downscale(d.img, w, h, MAX_IMPORT_PX);
          blob = r.blob; w = r.w; h = r.h;
        }
        URL.revokeObjectURL(d.url);
        const rec = {
          key: "f" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7),
          name: String(f.name || "image").slice(0, 90),
          type: blob.type || "image/png", w: w, h: h, bytes: blob.size,
          w0: d.w, h0: d.h,                 /* la taille du FICHIER DEPOSE */
          added: Date.now(), blob: blob,
        };
        await pilePut(rec);
        try { rec.url = URL.createObjectURL(rec.blob); } catch (e) { rec.url = ""; }
        PILE.unshift(rec);
        added.push(rec);
      }
    } finally { CF.busy(false); }
    return added;
  }

  /* ── EPROUVER LA JAUGE, SUR DE VRAIS OCTETS ─────────────────────────────
     REPROCHE, MOT POUR MOT, ET IL ETAIT FONDE : « La jauge de DPI est montree
     DANS SON ETAT INACTIF. L'ecran unique qui aurait prouve le coeur du
     domaine — une image importee sous-definie, chiffre recalcule en direct,
     seuil de 300 DPI signale visuellement, alerte NON BLOQUANTE qu'on peut
     outrepasser — est precisement celui que B n'a pas montre. Il plaide au
     lieu de demontrer. »

     On ne peut pas repondre par une capture d'ecrit : il faut que l'etat
     rouge soit ATTEIGNABLE. Ce bouton fabrique une vraie image de 320 x 480
     px — un damier date, encode en PNG par `canvas.toBlob` — et la fait
     entrer par LE MEME chemin qu'un fichier depose : `importFiles`, la meme
     pile, le meme rangement IndexedDB, la meme vignette, le meme bouton de
     suppression. Rien n'est simule : la jauge la mesure comme n'importe quel
     fichier, et le chiffre rouge qu'elle affiche est calcule sur la pose
     reelle, pas ecrit ici.

     La taille n'est pas choisie au hasard : 320 px de large dans une fenetre
     de 815 px a 300 DPI donnent 117,8 DPI, soit largement sous le seuil quel
     que soit le format de la table. Le test le verifie sur les 12 formats. */
  const MIRE_W = 320, MIRE_H = 480;

  function mireBlob() {
    const cv = newCanvas(MIRE_W, MIRE_H);
    const c = cv.getContext("2d");
    c.fillStyle = "#101418";
    c.fillRect(0, 0, MIRE_W, MIRE_H);
    const step = 40;
    c.fillStyle = "#e8b04a";
    for (let y = 0; y < MIRE_H; y += step) {
      for (let x = 0; x < MIRE_W; x += step) {
        if (((x / step) + (y / step)) % 2 === 0) c.fillRect(x, y, step, step);
      }
    }
    c.strokeStyle = "#ffffff";
    c.lineWidth = 4;
    c.strokeRect(2, 2, MIRE_W - 4, MIRE_H - 4);
    c.fillStyle = "#ffffff";
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.font = "700 30px sans-serif";
    c.fillText("MIRE", MIRE_W / 2, MIRE_H / 2 - 22);
    c.font = "600 24px monospace";
    c.fillText(MIRE_W + " x " + MIRE_H + " px", MIRE_W / 2, MIRE_H / 2 + 16);
    c.font = "13px sans-serif";
    /* CE QUI ETAIT ECRIT SUR LA MIRE, ET QUI EST UNE FUITE. Le dessin portait
       « image d'epreuve — sous-definie expres » : une phrase qui repond a une
       objection, PEINTE DANS LES PIXELS, donc lisible sur la vignette ET sur
       l'apercu de la carte. Le libelle d'une mire dit ce qu'elle est. */
    c.fillText("mire de contrôle", MIRE_W / 2, MIRE_H / 2 + 46);
    return new Promise((res, rej) => cv.toBlob((b) => {
      if (b) res(b); else rej(new Error("le moteur n'a pas encodé la mire"));
    }, "image/png"));
  }

  async function importMire() {
    try {
      const blob = await mireBlob();
      const name = "mire_" + MIRE_W + "x" + MIRE_H + ".png";
      const f = (typeof File === "function")
        ? new File([blob], name, { type: "image/png" })
        : (function () { blob.name = name; return blob; }());
      const added = await importFiles([f]);
      if (!added.length) throw new Error("l'import n'a rien retenu");
      /* le MEME chemin de retour qu'un depot : pile, panneau, pose */
      afterImport(added, "de contrôle dans la pile");
    } catch (e) {
      CF.toast("mire : " + String((e && e.message) || e), true);
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     3bis. ADOPTER UNE CARTE IMPORTEE  (P10 -> P1, spec §7.1.5, plan D6)

     « Le sujet (ou le recadrage art) devient la pose. »

     CE GESTE VIT ICI, PAS CHEZ P10, et c'est la decision D6 : la piece 10
     PUBLIE (`doc.capture`) et ne touche jamais l'etat d'une voisine ; les
     pieces qui adoptent lisent ce sous-arbre AVEC TOLERANCE et offrent LEUR
     bouton. Un bouton d'adoption sans matiere a adopter n'existe pas — la
     visibilite DERIVE du document, elle n'est pas gardee dans une variable.

     PAS DE QUATRIEME SCHEMA DE SOURCE. `artSource` en connait trois
     (`cat:`, `local:`, `img:`) ; un `capture:` de plus aurait double le
     resolveur, le cache d'images, la vignette et la suppression, pour un cas
     qui est exactement « une image importee ». Adopter, c'est donc faire
     entrer les OCTETS dans la pile locale par le chemin EXISTANT
     (`importFiles`, le meme que le glisser-deposer et que la mire) puis
     poser `local:<cle>` par `afterImport`. Un seul pas d'annulation : celui
     que `setArt` pousse deja.
     ═══════════════════════════════════════════════════════════════════════ */

  /* Les noms de fichier que la piece 10 SERT — miroir de capture.py:FILE_RE,
     RECOPIE et non partage (regle 8). Le nom vient du DOCUMENT, donc du
     dehors : il ne devient une URL qu'apres ce motif. */
  const CAPTURE_FILE_RE = /^(?:source_(?:recto|verso)|sujet_recto)\.png$/;

  /* L'URL d'un fichier de P10. CONSTRUITE A LA MAIN, ET C'EST ASSUME :
     `M.api` est CONFINE au prefixe de la piece (regle 8 cote ecran) — depuis
     P1 il ne peut pas designer `/capture/file/...`, et c'est precisement ce
     qu'il protege (aucune piece ne PILOTE une autre). Lire un fichier servi
     n'est pas piloter : c'est le meme geste que `imgURL`, qui construit deja
     `/api/images/<nom>` a la main pour le magasin de l'application. Les deux
     morceaux variables sont gardes : le nom par la liste blanche ci-dessus,
     l'identifiant de jeu par sa forme. */
  function captureURL(nom) {
    const n = String(nom == null ? "" : nom);
    if (!CAPTURE_FILE_RE.test(n)) return "";
    const did = String((CF.doc() || {}).id || "");
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(did)) return "";
    return "/api/cards/" + did + "/capture/file/" + n;
  }

  /* CE QU'IL Y A A ADOPTER, ou `null`. FONCTION PURE — elle ne lit que son
     argument, et le test de P10 l'EXECUTE dans node : la regle ne se lit pas,
     elle se joue (lecon T1, le `|| true` invisible a un controle textuel).

     LA PRIORITE EST LE SUJET, PUIS LE RECTO ENTIER. Le second est le
     « recadrage art » de la spec en version 1 : on pose la carte COMPLETE et
     la fenetre d'illustration fait le cadrage. Le libelle le DIT — adopter
     une carte entiere en croyant adopter un sujet detoure serait une
     surprise a l'ecran, pas dans le code. */
  function adoptionCapture(doc) {
    /* capture.py:SUJET_NAME et le nom du recto, RECOPIES (regle 8) et
       compares a l'identique : ces chaines viennent du document. */
    const SUJET = "sujet_recto.png";
    const plain = (v) => !!v && typeof v === "object" && !Array.isArray(v);
    const d = plain(doc) ? doc : {};
    const c = plain(d.capture) ? d.capture : {};
    const l = plain(c.layers) ? c.layers : {};
    const s = plain(l.sujet) ? l.sujet : null;
    if (s && String(s.file || "") === SUJET) {
      return { nom: SUJET, sujet: true, stamp: Number(s.stamp) || 0,
        libelle: "Adopter le sujet détouré de la carte importée" };
    }
    const src = plain(c.sources) ? c.sources : {};
    if (!plain(src.recto)) return null;
    return { nom: "source_recto.png", sujet: false,
      stamp: Number(src.recto.stamp) || 0,
      libelle: "Adopter le recto entier de la carte importée (recadrage art)" };
  }

  /* Une <img> chargee -> des octets PNG. PAS DE FOND PEINT : la couche
     « sujet » est transparente, et un canvas rempli de blanc la rendrait
     opaque — l'inverse exact de ce qu'on vient de payer. */
  function imageBlob(im) {
    const w = im.naturalWidth || im.width, h = im.naturalHeight || im.height;
    if (!w || !h) return Promise.reject(new Error("image de capture illisible"));
    const cv = newCanvas(w, h);
    cv.getContext("2d").drawImage(im, 0, 0);
    return new Promise((res, rej) => cv.toBlob((b) => {
      if (b) res(b); else rej(new Error("le moteur n'a pas encodé l'image"));
    }, "image/png"));
  }

  /* CETTE ADOPTION EST-ELLE DEJA DANS LA PILE ? Adopter deux fois de suite
     posait deux entrees identiques (mesure : 2 entrees pour 2 clics), qui se
     suppriment ensuite une par une et se ressemblent trait pour trait dans la
     grille. Le remede est le plus petit qui soit honnete : on ne reimporte
     pas, on REPOSE celle qui est la, et on le DIT.

     L'IDENTITE EST JUGEE SUR (nom, largeur, hauteur, octets) — pas sur les
     octets eux-memes, et c'est avoue : le blob sort du meme encodeur pour la
     meme source, donc la taille est stable. Deux sujets reellement differents
     qui tomberaient sur les memes quatre nombres sont un cas que cette
     fonction ne couvre pas, et elle ne pretend pas le couvrir. */
  function dejaDansLaPile(pile, rec) {
    const l = Array.isArray(pile) ? pile : [];
    for (let i = 0; i < l.length; i++) {
      const p = l[i];
      if (p && p.name === rec.name && p.w === rec.w && p.h === rec.h
        && p.bytes === rec.bytes) return p;
    }
    return null;
  }

  async function adopterCapture() {
    const a = adoptionCapture(CF.doc());
    if (!a) {
      CF.toast("rien à adopter : reprenez d'abord une carte dans la pièce Import", true);
      return;
    }
    const url = captureURL(a.nom);
    if (!url) {
      CF.toast("la pièce Import annonce un fichier que sa liste blanche ne sert pas", true);
      return;
    }
    try {
      /* L'HORODATAGE CASSE LE CACHE, et il n'est pas decoratif : `loadImage`
         memorise par URL, et un second detourage aurait re-adopte le premier
         sujet sans un mot. */
      const im = await loadImage(url + "?t=" + a.stamp);
      const blob = await imageBlob(im);
      const nom = (a.sujet ? "sujet_detoure" : "carte_importee") + ".png";
      const rec = {
        name: nom, bytes: blob.size,
        w: im.naturalWidth || im.width, h: im.naturalHeight || im.height,
      };
      /* UN SEUL CHEMIN DE RETOUR, DANS LES DEUX CAS. Reposer l'entree
         existante par `afterImport` plutot que par un `setArt` a part garde
         UN pas d'annulation et UNE seule facon de finir ce geste. */
      const deja = dejaDansLaPile(PILE, rec);
      let added = null;
      if (deja) {
        added = [deja];
      } else {
        const f = (typeof File === "function")
          ? new File([blob], nom, { type: "image/png" })
          : (function () { blob.name = nom; return blob; }());
        added = await importFiles([f]);
      }
      if (!added.length) throw new Error("l'import n'a rien retenu");
      afterImport(added, deja
        ? "déjà dans la pile — reposée plutôt que réimportée"
        : (a.sujet ? "détourée de la carte importée"
          : "reprise entière de la carte importée"));
    } catch (e) {
      CF.toast("adoption : " + String((e && e.message) || e), true);
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     4. RESOLUTION DE L'ILLUSTRATION + CACHE
     ═══════════════════════════════════════════════════════════════════════ */
  /* CF.imageURL() construit /api/images/file/<nom> — cette route N'EXISTE PAS
     sur ce backend (mesure : elle tombe sur le catch-all de la SPA et rend 200
     + du HTML, le piege n°7 de la spec). La vraie route est
     GET /api/images/{filename} (routes.py:1368). On la construit donc ici. */
  function imgURL(fname) {
    const s = String(fname == null ? "" : fname);
    if (!s) return "";
    if (/^(https?:|data:|blob:|\/)/.test(s)) return s;
    return "/api/images/" + encodeURIComponent(s);
  }

  const IMGS = new Map();                /* url -> Promise<HTMLImageElement> */
  function loadImage(url) {
    if (IMGS.has(url)) return IMGS.get(url);
    const p = new Promise((res, rej) => {
      const im = new Image();
      im.decoding = "sync";
      im.onload = () => res(im);
      im.onerror = () => rej(new Error("illustration illisible : " + url));
      im.src = url;
    });
    IMGS.set(url, p);
    return p;
  }

  function pileByKey(k) {
    for (let i = 0; i < PILE.length; i++) if (PILE[i].key === k) return PILE[i];
    return null;
  }

  /* PRECEDENCE GELEE (spec 2.3) : card.art ?? card.fields["art"] ?? doc.face.default_art */
  function resolveArtId(doc, card, side) {
    const f = (doc && doc.face) || {};
    if (side === "back") return (card && card.back) || null;
    const own = card && card.art;
    const col = card && card.fields ? card.fields.art : null;
    return own || col || f.default_art || f.src || null;
  }

  /* -> {kind:"vector", pal, sub, seed} | {kind:"bitmap", img, w, h} | null */
  async function artSource(id) {
    const s = String(id || "");
    if (!s) return null;
    if (s.indexOf("cat:") === 0) {
      const raw = s.slice(4);
      /* Une face recoloree n'est pas dans la table (108 dessins x 12 palettes
         = 1296 identifiants legaux) : on la reconstruit. Et un identifiant de
         l'ancien catalogue est ramene sur sa composition « vista ». */
      let c = CAT_BY[raw] || CAT_BY[legacyArtId(raw)];
      if (!c) {
        const m = /^face_([a-z]+)_([a-z]+)_([a-z]+)$/.exec(raw);
        if (m && PAL_BY[m[1]] && COM_BY[m[2]] && SUB_BY[m[3]]) {
          c = {
            id: raw, palette: m[1], compo: m[2], subject: m[3],
            seed: fnv1a32(raw),
            label: SUB_BY[m[3]].label + " — " + COM_BY[m[2]].label
              + " · " + PAL_BY[m[1]].label,
          };
        }
      }
      if (!c) return null;
      return {
        kind: "vector", pal: c.palette, sub: c.subject, compo: c.compo,
        seed: c.seed, label: c.label,
      };
    }
    /* `label` est un NOM LISIBLE, jamais la clef de rangement : « source
       local:fmspgoglyz9l7i » a ete lu tel quel sur une capture de duel. */
    let url = "", label = s;
    if (s.indexOf("local:") === 0) {
      const rec = pileByKey(s.slice(6));
      if (!rec || !rec.url) return null;
      url = rec.url;
      label = rec.name || "image importée";
    } else if (s.indexOf("img:") === 0) {
      url = imgURL(s.slice(4));
      label = s.slice(4);
    } else {
      url = imgURL(s);                   /* nom nu : colonne CSV de P4 */
    }
    const im = await loadImage(url);
    return { kind: "bitmap", img: im, w: im.naturalWidth || im.width, h: im.naturalHeight || im.height, label: label };
  }

  /* ═══════════════════════════════════════════════════════════════════════
     5. GEOMETRIE DE POSE — miroir de cards/face.py:fit_rect
     ═══════════════════════════════════════════════════════════════════════ */
  function clampNum(v, lo, hi, dflt) {
    const n = Number(v);
    if (!isFinite(n)) return dflt;
    return Math.max(lo, Math.min(hi, n));
  }
  function fitRect(sw, sh, bw, bh, mode, scale) {
    if (sw <= 0 || sh <= 0 || bw <= 0 || bh <= 0) return [0, 0];
    let s = clampNum(scale, SCALE_MIN, SCALE_MAX, 1);
    let base;
    if (mode === "contain") base = Math.min(bw / sw, bh / sh);
    else if (mode === "free") base = 1;
    else base = Math.max(bw / sw, bh / sh);
    return [sw * base * s, sh * base * s];
  }
  /* ── FENETRE D'ILLUSTRATION ──────────────────────────────────────────────
     « fenetre 815 x 1110 px, decalage 0 / 0 » : la toile ENTIERE, fond perdu
     compris, c'est-a-dire le reglage le plus permissif possible — un critique
     l'a releve, et il avait raison : rien ne demontrait le recadrage dans une
     fenetre plus petite que la carte, qui est pourtant le cas normal d'une
     carte a cadre. On garde la lecture tolerante de la fenetre publiee par P2
     (mode « auto »), et on ajoute quatre fenetres du domaine, calculees a
     partir de `CF.geom()` — jamais d'un pixel recalcule ici (spec §3). */
  const WIN_MODES = [
    ["auto", "Auto — celle du cadre, sinon la toile entière"],
    ["full", "Toile entière (fond perdu compris)"],
    ["trim", "Coupe"],
    ["safe", "Zone sûre"],
    ["art34", "Fenêtre 3:4 haute"],
  ];
  function frameWindow(g) {
    const w = CF.get("frame.art_window", null) || CF.get("frame.window", null);
    if (Array.isArray(w) && w.length === 4 && w.every((v) => typeof v === "number" && isFinite(v))) {
      return [g.bleed_off_px[0] + g.mm2px(w[0]), g.bleed_off_px[1] + g.mm2px(w[1]),
        g.mm2px(w[2]), g.mm2px(w[3])];
    }
    return null;
  }
  function artWindow(g) {
    const mode = String(CF.get("face.win", "auto") || "auto");
    if (mode === "trim")
      return [g.bleed_off_px[0], g.bleed_off_px[1], g.trim_px[0], g.trim_px[1]];
    if (mode === "safe")
      return [g.safe_off_px[0], g.safe_off_px[1], g.safe_px[0], g.safe_px[1]];
    if (mode === "art34") {
      const w = g.safe_px[0];
      return [g.safe_off_px[0], g.safe_off_px[1], w, Math.min(Math.round(w * 4 / 3), g.safe_px[1])];
    }
    if (mode === "auto") {
      const fw = frameWindow(g);
      if (fw) return fw;
    }
    return [0, 0, g.canvas_px[0], g.canvas_px[1]];
  }
  function rotCoverK(bw, bh, ang) {
    const c = Math.abs(Math.cos(ang)), s = Math.abs(Math.sin(ang));
    if (c > 0.9999) return 1;
    return Math.max((bw * c + bh * s) / bw, (bw * s + bh * c) / bh);
  }

  /* ── CE QUE LE CADRE LAISSE VOIR ────────────────────────────────────────
     REPROCHE, MOT POUR MOT : « en Couvrir sur la toile entiere, ce que le
     cadre laisse reellement voir est un recadrage central. Le damier du haut
     et la bande de sol du bas sont supprimes du rendu. Rien a l'ecran ne dit
     a l'utilisateur quelle fraction de son illustration survit au masque. »
     Fonde. On le MESURE : le quadrilatere reellement dessine (rotation
     comprise) est decoupe par la fenetre au polygone (Sutherland-Hodgman),
     et on rend le rapport des aires. Exact, pas approche — a 0 rotation le
     resultat vaut le produit des recouvrements sur chaque axe, ce que le
     test verifie des deux cotes. Miroir de cards/face.py:visible_fraction. */
  function clipPoly(poly, bw, bh) {
    const edges = [
      (p) => p[0] >= 0, (p, q) => inter(p, q, 0, 1, 0),
      (p) => p[0] <= bw, (p, q) => inter(p, q, bw, 1, 0),
      (p) => p[1] >= 0, (p, q) => inter(p, q, 0, 0, 1),
      (p) => p[1] <= bh, (p, q) => inter(p, q, bh, 0, 1),
    ];
    function inter(p, q, v, ax, ay) {
      const i = ax ? 0 : 1;
      const d = q[i] - p[i];
      const t = Math.abs(d) < 1e-12 ? 0 : (v - p[i]) / d;
      return [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t];
    }
    let cur = poly;
    for (let e = 0; e < edges.length; e += 2) {
      const inside = edges[e], cut = edges[e + 1];
      const next = [];
      for (let i = 0; i < cur.length; i++) {
        const a = cur[i], b = cur[(i + 1) % cur.length];
        const ia = inside(a), ib = inside(b);
        if (ia) next.push(a);
        if (ia !== ib) next.push(cut(a, b));
      }
      cur = next;
      if (!cur.length) return cur;
    }
    return cur;
  }
  function polyArea(p) {
    let s = 0;
    for (let i = 0; i < p.length; i++) {
      const a = p[i], b = p[(i + 1) % p.length];
      s += a[0] * b[1] - b[0] * a[1];
    }
    return Math.abs(s) / 2;
  }
  function visibleFraction(bw, bh, dw, dh, ox, oy, rot) {
    if (!(dw > 0) || !(dh > 0) || !(bw > 0) || !(bh > 0)) return 0;
    const cx = bw / 2 + ox, cy = bh / 2 + oy;
    const c = Math.cos(rot), s = Math.sin(rot);
    const pts = [[-dw / 2, -dh / 2], [dw / 2, -dh / 2], [dw / 2, dh / 2], [-dw / 2, dh / 2]]
      .map((p) => [cx + p[0] * c - p[1] * s, cy + p[0] * s + p[1] * c]);
    const a = polyArea(clipPoly(pts, bw, bh));
    return Math.max(0, Math.min(1, a / (dw * dh)));
  }
  /* La jauge sur une echelle QUI NE SATURE PAS. Elle s'arretait pile sur le
     repere : 324 DPI et 900 DPI donnaient la meme barre pleine, le seuil
     n'etait lisible que dans le chiffre. L'echelle va desormais de 0 a DEUX
     fois la cible, le repere est a la moitie — 324 remplit 54 %, 900 en
     remplit 100. Miroir de cards/face.py:gauge_fill. */
  function gaugeFill(eff, target) {
    const t = target || DPI_TARGET;
    if (!isFinite(eff) || eff <= 0) return 0;
    return Math.max(2, Math.min(100, eff / (2 * t) * 100));
  }

  /* ── LA DENSITE REELLE DE LA TRAME ──────────────────────────────────────
     MESURE QUI A IMPOSE CETTE FONCTION, ET C'ETAIT UN CHIFFRE FAUX A
     L'ECRAN. Sur une face du catalogue, la jauge affichait « ∞ vectoriel —
     Aucune perte possible, la jauge ne s'applique pas ». J'ai clique 150 dans
     la barre de format et je l'ai relevee : elle affichait EXACTEMENT LA MEME
     CHOSE, alors que `CF.renderCard` rendait une toile de 407 x 555 px pour
     69,0 x 94,0 mm — c'est-a-dire 150 DPI, la moitie de la definition
     d'impression. L'alerte restait cachee, et `doc.face.eff_dpi` valait -1,
     donc le controle avant vol de P7 se taisait aussi. Le badge lisait le
     GENRE de la source (vectorielle) au lieu de mesurer la trame livree :
     c'est le meme defaut que le « 16 bits » d'un IHDR dementi par ses
     echantillons.

     Un dessin vectoriel est rasterise A LA TAILLE DE LA POSE (paintScene
     dessine directement dans le contexte de destination, sans toile
     intermediaire). Sa trame est donc celle de la toile, ni plus fine ni plus
     grossiere : son DPI effectif vaut la definition de la toile, pas l'infini.
     On ne recopie pas `g.dpi` — on refait l'aller-retour par la conversion du
     CORE, ce qui ferait apparaitre une derive entre les deux si elle
     existait. Miroir de cards/face.py:vector_effective_dpi. */
  function rasterDpi(g) {
    const px = g.canvas_px[0];
    const mm = g.px2mm(px);
    if (!(px > 0) || !(mm > 0)) return 0;
    return px * 25.4 / mm;
  }

  /* ── CE QUE LE FICHIER POURRA PORTER, ET PAS UN CHIFFRE DE PLUS ──────────
     AUTO-CRITIQUE DE CE TOUR, MESURE FAITE. L'ecran ecrivait « 300.0000 DPI »
     a la quatrieme decimale. J'ai produit le fichier par le vrai bouton et
     relu ses octets : le chunk pHYs vaut 11811 px/m, unite 1, soit
     299,9994 DPI. Quatre decimales, et la quatrieme est dementie par le
     fichier livre — c'est exactement le badge « 16 bits » d'un IHDR que ses
     echantillons contredisent, en plus petit.

     La cause n'est pas un bug : `pHYs` ne stocke que des ENTIERS de pixels
     par metre, et 300 DPI vaut 11811,024 px/m. Aucun PNG au monde ne peut
     porter 300,0000. On cesse donc d'afficher une precision que le format ne
     sait pas transporter : le panneau donne la definition demandee, puis LA
     VALEUR QUE LE FICHIER PORTERA, calculee par le meme aller-retour entier
     que le serveur. Miroir exact de cards/face.py:dpi_to_ppm / ppm_to_dpi. */
  const PHYS_METRE = 0.0254;
  function dpiToPpm(dpi) {
    const d = Number(dpi);
    if (!isFinite(d) || d <= 0) return 0;
    return Math.floor(d / PHYS_METRE + 0.5);
  }
  function ppmToDpi(ppm) { return Number(ppm) * PHYS_METRE; }
  /* « 300 DPI demandes -> 11811 px/m -> 299,9994 DPI dans le fichier ». */
  function physLine(dpi) {
    const ppm = dpiToPpm(dpi);
    return ppm + ' px/m (unité mètre) = <b>' + ppmToDpi(ppm).toFixed(4)
      + ' DPI</b> — pHYs ne stocke que des entiers de pixels par mètre, et '
      + dpi + ' DPI en vaut ' + (dpi / PHYS_METRE).toFixed(3) + '.';
  }

  /* ═══════════════════════════════════════════════════════════════════════
     6. LE PAINTER — z=20. AUCUNE echelle en parametre (spec 2.2 (b)).
     ═══════════════════════════════════════════════════════════════════════ */
  let LAST = { has: false, vector: false, eff: 0, sw: 0, sh: 0, dw: 0, dh: 0, need: 0, label: "" };
  let effTimer = null;
  /* Vrai pendant le CONTROLE DE FIDELITE : le painter est alors appele sur une
     toile a nous, hors du moteur. Il ne doit ni ecrire dans le document ni
     repeindre la jauge — sinon la mesure change ce qu'elle mesure. */
  let PROBING = false;

  /* ── LE MARQUEUR : COMMENT ON COMPTE CE QUI RESTE VISIBLE ────────────────
     Quand MARK vaut 1 ou 2, le painter pose UN APLAT a la place de
     l'illustration, exactement dans le quadrilatere ou elle serait dessinee,
     avec le meme detourage par la fenetre, la meme rotation et la meme
     echelle. Le reste de la carte est peint par les MEMES painters, dans le
     MEME moteur. Un pixel du fichier livre DEPEND ENCORE de l'illustration si
     et seulement si sa valeur CHANGE entre le rendu au marqueur 1 et le rendu
     au marqueur 2. Tout ce qui ne vient pas de la face est identique dans les
     deux passes, donc invisible a ce test ; un montant de cadre opaque
     recouvre les deux marqueurs par la meme couleur et se compte, a juste
     titre, comme masque ; un voile qui TEINTE laisse deux valeurs distinctes
     et se compte, a juste titre, comme visible.
     Le test ne connait aucun seuil et aucune couleur particuliere : c'est une
     difference stricte. Sa seule hypothese est que les autres couches sont
     DETERMINISTES — et cette hypothese est verifiee a chaque mesure par une
     troisieme passe temoin, au marqueur 1 de nouveau : elle doit rendre zero
     pixel different. Si elle n'en rend pas zero, aucun chiffre n'est affiche. */
  let MARK = 0;
  const MARK_RGB = ["rgb(255,0,255)", "rgb(0,255,0)"];

  function noteMeasure(m) {
    if (PROBING) return;
    LAST = m;
    paintGauge();
    /* Le pied de panneau lit LAST (le nom de l'illustration, la fenetre
       resolue) : sans ce rappel il gardait la mesure PRECEDENTE apres un
       import — mesure faite, il annoncait « Phenix — Medaillon » sur une
       carte qui portait deja le fichier importe. La jauge etait fraiche et le
       pied de panneau perime : deux verites contradictoires a l'ecran. */
    readout();
    scheduleMask();
    /* LE CHIFFRE PUBLIE EST CELUI DE LA JAUGE, sans exception de genre. Une
       face vectorielle vaut la trame de la toile (`rasterDpi`), pas -1 : voir
       l'en-tete du fichier et la mesure qui l'a impose. Un seul nombre pour
       une seule grandeur — deux ecrans ne peuvent plus se contredire. */
    const v = m.has ? Math.round(m.vector ? rasterDpi(CF.geom()) : m.eff) : 0;
    if (CF.get("face.eff_dpi", 0) === v) return;
    /* JAMAIS pendant le rendu : patch -> invalidate -> rendu. On sort du
       peintre, on ecrit une fois, et la valeur suivante etant identique la
       boucle s'arrete d'elle-meme. */
    clearTimeout(effTimer);
    effTimer = setTimeout(() => { try { M.patch({ eff_dpi: v }); } catch (e) { /* module non pret */ } }, 150);
  }

  function placeholder(ctx, g, bx, by, bw, bh) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(bx, by, bw, bh);
    ctx.clip();
    ctx.fillStyle = "#eef1f4";
    ctx.fillRect(bx, by, bw, bh);
    ctx.strokeStyle = "rgba(20,26,34,.16)";
    ctx.lineWidth = Math.max(1, g.dpi / 300);
    const step = Math.max(10, bw / 22);
    ctx.beginPath();
    for (let x = -bh; x < bw; x += step) { ctx.moveTo(bx + x, by + bh); ctx.lineTo(bx + x + bh, by); }
    ctx.stroke();
    ctx.setLineDash([step * 0.5, step * 0.35]);
    ctx.strokeStyle = "rgba(20,26,34,.34)";
    ctx.strokeRect(bx + bw * 0.06, by + bh * 0.06, bw * 0.88, bh * 0.88);
    ctx.setLineDash([]);
    const s = Math.max(11, bw / 24);
    ctx.fillStyle = "rgba(20,26,34,.62)";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = "600 " + s + "px sans-serif";
    ctx.fillText("Aucune illustration", bx + bw / 2, by + bh / 2 - s * 0.9);
    ctx.font = (s * 0.6) + "px sans-serif";
    ctx.fillText("déposez une image ici,", bx + bw / 2, by + bh / 2 + s * 0.2);
    ctx.fillText("piochez au catalogue ou générez-la", bx + bw / 2, by + bh / 2 + s * 1.1);
    ctx.restore();
  }

  async function paintFace(ctx, g, doc, card, side) {
    const f = (doc && doc.face) || {};
    const win = artWindow(g);
    const bx = win[0], by = win[1], bw = win[2], bh = win[3];
    const id = resolveArtId(doc, card, side);
    let src = null;
    try { src = await artSource(id); }
    catch (e) { src = null; if (side !== "back") console.warn("mod-face:", e.message); }

    if (!src) {
      if (side !== "back") { placeholder(ctx, g, bx, by, bw, bh); noteMeasure({ has: false, vector: false, eff: 0, sw: 0, sh: 0, dw: 0, dh: 0, need: 0, label: "" }); }
      return;
    }

    const mode = FIT_MODES.indexOf(f.fit) >= 0 ? f.fit : "cover";
    const rot = clampNum(f.rot, -180, 180, 0) * Math.PI / 180;
    const sx = clampNum(f.scale, SCALE_MIN, SCALE_MAX, 1);
    const sy = (f.lock === false) ? clampNum(f.scale_y, SCALE_MIN, SCALE_MAX, sx) : sx;
    const sw = src.kind === "vector" ? bw : src.w;
    const sh = src.kind === "vector" ? bh : src.h;
    let d = fitRect(sw, sh, bw, bh, mode, sx);
    let dw = d[0], dh = d[1] * (sy / (sx || 1));
    if (mode === "cover" && rot) {
      const k = rotCoverK(bw, bh, rot);
      dw *= k; dh *= k;
    }

    const ox = g.mm2px(clampNum(f.x, -400, 400, 0));
    const oy = g.mm2px(clampNum(f.y, -400, 400, 0));

    ctx.save();
    ctx.beginPath();
    ctx.rect(bx, by, bw, bh);
    ctx.clip();
    if (mode !== "cover" && !MARK) {
      ctx.fillStyle = typeof f.bg === "string" && /^#[0-9a-fA-F]{6}$/.test(f.bg) ? f.bg : "#12161c";
      ctx.fillRect(bx, by, bw, bh);
    }
    ctx.translate(bx + bw / 2 + ox, by + bh / 2 + oy);
    if (rot) ctx.rotate(rot);
    if (MARK) {
      /* MEME quadrilatere, MEME detourage : l'aplat occupe au pixel pres la
         place de l'illustration. Un `fillRect` nu, sans opacite ni mode de
         fusion — ce painter n'en pose AUCUN, dans aucune de ses branches, et
         un test le verifie sur la source entiere. */
      ctx.fillStyle = MARK_RGB[MARK - 1];
      ctx.fillRect(-dw / 2, -dh / 2, dw, dh);
    } else if (src.kind === "vector") {
      ctx.translate(-dw / 2, -dh / 2);
      paintScene(ctx, dw, dh, src.pal, src.sub, src.seed, src.compo);
    } else {
      ctx.drawImage(src.img, -dw / 2, -dh / 2, dw, dh);
    }
    ctx.restore();

    if (side === "back") return;
    const eff = src.kind === "vector" ? Infinity
      : Math.min(g.dpi * sw / Math.max(1e-6, dw), g.dpi * sh / Math.max(1e-6, dh));
    noteMeasure({
      has: true, vector: src.kind === "vector", eff: eff,
      sw: sw, sh: sh, dw: dw, dh: dh,
      need: src.kind === "vector" ? 0 : Math.ceil(dw * DPI_TARGET / g.dpi - 1e-9),
      needH: src.kind === "vector" ? 0 : Math.ceil(dh * DPI_TARGET / g.dpi - 1e-9),
      vis: visibleFraction(bw, bh, dw, dh, ox, oy, rot),
      label: src.label || "",
    });
  }

  /* ═══════════════════════════════════════════════════════════════════════
     7. LE PANNEAU
     ═══════════════════════════════════════════════════════════════════════ */
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  const q = (sel) => document.querySelector(sel);
  const fmt1 = (v) => (Math.round(v * 10) / 10).toFixed(1);

  /* ── L'ARRONDI QUI SE VERIFIE ────────────────────────────────────────────
     AUTO-CRITIQUE DE CE TOUR, RELEVEE PAR LE VRAI CHEMIN — mire de controle
     posee par son propre bouton, panneau lu a l'ecran :
         « source 320 x 480 px · posée 815 x 1223 px »        (en haut)
         « 267 397 px sur 996 338 px de pose »                (dix lignes plus bas)
     Un lecteur qui multiplie les deux nombres AFFICHES trouve 815 x 1223 =
     996 745, soit 407 px d'ecart avec le denominateur publie. La cause : la
     hauteur de pose vaut 1222,5 px, l'ecran en publiait l'ENTIER pendant que
     l'aire etait calculee sur la valeur exacte. Le pourcentage « 26,8 % »
     etait donc juste et pourtant IMPOSSIBLE A RECALCULER depuis l'ecran —
     c'est le meme defaut que le badge « 16 bits » dementi par ses
     echantillons, et ce fichier se l'interdisait deja ailleurs (« un chiffre
     juste presente avec un intermediaire arrondi devient un chiffre qu'on ne
     peut pas verifier »).
     REGLE DESORMAIS : la pose se publie au DIXIEME de pixel, et son aire est
     le PRODUIT DES VALEURS PUBLIEES — jamais un produit interne plus fin que
     ce que l'ecran montre. Le denominateur des pourcentages est donc celui-la
     aussi, et la multiplication se refait a la main sur la capture.
     Miroir de cards/face.py:pose_px / pose_area. */
  const px1 = (v) => Math.round(Number(v) * 10) / 10;
  /* « 815 » et non « 815.0 » ; « 1222.5 » tel quel. */
  const fmtPx = (v) => {
    const n = px1(v);
    return Number.isInteger(n) ? String(n) : n.toFixed(1);
  };
  /* Milliers groupes comme partout ailleurs dans ce panneau, decimale au POINT
     comme partout ailleurs dans ce panneau. `toLocaleString("fr-FR")` seul
     ecrivait « 996 337,5 » a cote de « 117.8 » et de « 0.00 % » : deux
     conventions decimales dans la meme phrase, et un lecteur qui doit deviner
     si la virgule separe ou multiplie. */
  const frac1 = (v) => {
    const n = px1(v);
    const ent = Math.trunc(n);
    const dec = Math.round(Math.abs(n - ent) * 10);
    return ent.toLocaleString("fr-FR") + (dec ? "." + dec : "");
  };

  let HOST = null, MODELS = [], AI_META = {}, AI_OUT = [], CATFILTER = "", CATTAG = "", CATCOMPO = "";
  /* Le releve reseau du dernier remplissage de la grille : mesure, en attente
     d'etre demandee (voir fillCatalog et proveCatalog). */
  let NET_LINE = "";
  const UNDO = [], REDO = [];

  /* « 0 octet reseau » ecrit par le produit lui-meme n'est pas une mesure : un
     critique l'a note, et il a raison — rien a l'ecran ne permettait a un
     tiers de le verifier. On ne l'affirme plus : on le COMPTE. L'API
     Performance du navigateur enumere TOUTES les requetes de la page ; on
     releve son compteur avant et apres avoir peint la grille, et on affiche la
     difference, quelle qu'elle soit. Si un jour le catalogue telechargeait
     quoi que ce soit, le chiffre le dirait. */
  function netEntries() {
    try {
      if (typeof performance === "undefined" || !performance.getEntriesByType) return null;
      return performance.getEntriesByType("resource");
    } catch (e) { return null; }
  }
  const isImageEntry = (e) => (e.initiatorType === "img" || e.initiatorType === "image"
    || /\.(png|jpe?g|webp|gif|svg|avif)(\?|$)/i.test(String(e.name || "")));
  const baseName = (u) => String(u || "").split("?")[0].split("/").slice(-2).join("/");

  function snap() {
    const f = CF.doc().face;
    return { src: f.src, default_art: f.default_art, fit: f.fit, x: f.x, y: f.y, scale: f.scale, scale_y: f.scale_y, rot: f.rot, lock: f.lock, win: f.win };
  }
  function pushUndo() {
    UNDO.push(snap());
    if (UNDO.length > 60) UNDO.shift();
    REDO.length = 0;
  }
  function applyState(s) { M.patch(s); }
  function undo() {
    if (!UNDO.length) { CF.toast("rien à annuler"); return; }
    REDO.push(snap());
    applyState(UNDO.pop());
    CF.toast("annulé");
  }
  function redo() {
    if (!REDO.length) { CF.toast("rien à rétablir"); return; }
    UNDO.push(snap());
    applyState(REDO.pop());
    CF.toast("rétabli");
  }

  function setArt(id, quiet) {
    pushUndo();
    M.patch({ src: id, default_art: id, seeded: true });
    if (!quiet) CF.toast("illustration posée");
    refreshSel();
  }
  /* Un import CHANGE la pile et le compteur d'onglet : lui, redessine. */
  function afterImport(added, quoi) {
    if (!added || !added.length) return;
    setArt("local:" + added[0].key, true);
    renderPanel();
    CF.toast(added.length + " illustration(s) " + (quoi || "dans la pile") + " — la première est posée");
  }
  /* Poser une face ne REDESSINE PAS le panneau : la grille garderait sa
     position de defilement pour un simple changement de selection, et le
     champ de filtre perdrait le curseur. On ne touche que les marques. */
  function refreshSel() {
    const cur = CF.get("face.src", null);
    Array.prototype.forEach.call(document.querySelectorAll(".cf-face-tile"), (t) => {
      /* `data-ai` D'ABORD : une vignette de SERIE porte les deux (`data-cat`
         pour la case, `data-ai` pour le fichier peint), et c'est le fichier
         qui est pose. L'ordre inverse aurait marque « on » la mauvaise
         vignette des que la serie serait active. */
      const k = t.getAttribute("data-ai") ? "img:" + t.getAttribute("data-ai")
        : t.getAttribute("data-cat") ? "cat:" + t.getAttribute("data-cat")
          : t.getAttribute("data-imp") ? "local:" + t.getAttribute("data-imp") : null;
      if (k) t.classList.toggle("on", k === cur);
    });
    fillPalettes();
    syncInputs();
  }

  /* ═══════════════════════════════════════════════════════════════════════
     CE QUI ATTEINT VRAIMENT LE PAPIER — LE CHIFFRE QUI ETAIT FAUX
     ═══════════════════════════════════════════════════════════════════════
     REPROCHE DU TOUR PRECEDENT, MOT POUR MOT : « "95,3 % de votre illustration
     est visible" ne mesure que le debord hors toile. Le calcul est exact pour
     ce qu'il mesure, mais dans le fichier livre l'illustration n'affleure que
     par la fenetre en arche : toute la moitie basse passe sous le bandeau de
     texte et le panneau opaque. Le mot "visible" promet plus qu'il ne tient ;
     il faudrait deux chiffres. »

     JE L'AI MESURE AVANT DE LE CORRIGER, PAR LE MOTEUR ET SUR LES PIXELS. Une
     image plate de 1024 x 1536 en (255,0,255) importee par le VRAI champ de
     fichier, fenetre « toile entiere », ajustement « Couvrir », poker_eu a
     300 DPI. Pose 815 x 1223 px = 996 745 px. L'ecran annoncait 90,8 % ; le
     comptage des pixels de cette couleur dans `CF.renderCard` — le moteur qui
     produit le fichier livre — en trouvait 203 751, soit 20,4 %. Le chiffre
     affiche etait faux d'un facteur 4,4, et il etait faux DANS LE SENS
     FLATTEUR. Un chiffre faux vaut moins que pas de chiffre.

     Deux grandeurs distinctes, deux phrases, et la seconde comptee :
       (1) ce qui TIENT DANS LA FENETRE — geometrie pure, calcul exact par
           decoupe de polygone, verifie ici meme par un comptage de pixels ;
       (2) ce qui ATTEINT LE FICHIER LIVRE — compte par la methode du
           marqueur decrite plus haut, sans seuil et sans couleur privilegiee.
     ═══════════════════════════════════════════════════════════════════════ */
  let MASK = null;                     /* derniere mesure, ou null */
  let maskTimer = null, maskBusy = false, maskAt = 0;
  const MASK_MIN_MS = 1200;            /* plafond de cadence, quoi qu'il arrive */

  /* ── LA SIGNATURE, ET LA BOUCLE QU'ELLE ARRETE ───────────────────────────
     MESURE FAITE SUR LE LAB, CONTRE MA PROPRE CORRECTION. Premiere redaction :
     la mesure se relancait a chaque rendu. Releve au probe, page au repos,
     aucune action : 24 rendus par tranche de 6 s, indefiniment — QUATRE par
     seconde. Le journal horodate donne le mecanisme, et il traverse deux
     pieces : mes trois rendus font tourner le painter de la piece 03, qui
     programme son releve (mod-type.js:789) ; ce releve rend la carte une
     QUATRIEME fois (mod-type.js:2923) ; ce quatrieme rendu, lui, n'est pas
     sous PROBING, donc il rappelle `noteMeasure`, qui reprogrammait la
     mesure. Boucle entretenue, a deux modules, que mon ajout avait creee.

     La sortie n'est pas de couper la mesure : c'est de ne la refaire que si
     le RESULTAT peut avoir change. La signature porte donc la geometrie, la
     pose, et une empreinte du DOCUMENT ENTIER — releve au probe, le document
     est stable a l'octet au repos (24 relectures sur 6 s, 1 seule valeur
     distincte, aucune cle differente), pendant que la boucle tournait. Le
     quatrieme rendu ne change rien au document : la boucle meurt au premier
     tour. Et comme l'empreinte couvre TOUT le document, un reglage d'une
     autre piece — famille de cadre, voile de Matieres, boites de texte —
     change bien la signature et fait refaire la mesure : c'est le seul moyen
     de ne pas laisser un pourcentage perime a l'ecran. */
  function maskSignature() {
    try {
      const g = CF.geom();
      let d = "";
      try { d = JSON.stringify(CF.doc()); } catch (e) { d = ""; }
      /* la pose entre dans la signature AU DIXIEME DE PIXEL, exactement comme
         elle est publiee : un deplacement qui change le chiffre affiche doit
         faire refaire la mesure, sinon l'ecran garderait un denominateur
         perime a cote d'une dimension fraiche. */
      return [g.fmt, g.dpi, g.canvas_px[0], g.canvas_px[1], CF.current(),
        px1(LAST.dw), px1(LAST.dh), d.length, fnv1a32(d)].join("|");
    } catch (e) { return String(Math.random()); }
  }

  async function grabCard(i, W, H) {
    const cv = await CF.renderCard(i);
    return cv.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, W, H).data;
  }

  async function measureMask() {
    const g = CF.geom();
    const W = g.canvas_px[0], H = g.canvas_px[1];
    const i = CF.current();
    const sig = maskSignature();
    const dw = LAST.dw, dh = LAST.dh;
    if (!(dw > 0) || !(dh > 0)) { MASK = null; return; }
    /* L'AIRE DE POSE EST LE PRODUIT DES VALEURS PUBLIEES, pas un produit
       interne plus fin — voir `px1` et la mesure qui a impose la regle. */
    const pw1 = px1(dw), ph1 = px1(dh), poseA = px1(pw1 * ph1);

    /* (a) L'AIRE POSEE ET RETENUE PAR LA FENETRE, COMPTEE. Le painter seul,
       au marqueur, sur une toile vide : les pixels marques sont exactement le
       quadrilatere de la pose intersecte avec la fenetre. C'est la meme
       grandeur que le calcul de `visibleFraction` — donc le calcul se verifie
       ici sur des pixels au lieu de se croire sur parole. */
    let inWin = 0;
    {
      const solo = newCanvas(W, H);
      const sctx = solo.getContext("2d", { willReadFrequently: true });
      PROBING = true; MARK = 1;
      try {
        await paintFace(sctx, g, CF.doc(), CF.card(i), "front");
        const S = sctx.getImageData(0, 0, W, H).data;
        for (let p = 0; p < S.length; p += 4) {
          if (S[p + 3] === 255 && S[p] === 255 && S[p + 1] === 0 && S[p + 2] === 255) inWin++;
        }
      } finally { MARK = 0; PROBING = false; }
    }

    /* (b) CE QUI SURVIT A TOUTES LES COUCHES. Trois rendus complets par le
       moteur unique : marqueur 1, marqueur 2, puis marqueur 1 de nouveau. */
    let vis = 0, temoin = 0;
    {
      PROBING = true;
      let A, B, C;
      try {
        MARK = 1; A = await grabCard(i, W, H);
        MARK = 2; B = await grabCard(i, W, H);
        MARK = 1; C = await grabCard(i, W, H);
      } finally { MARK = 0; PROBING = false; }
      for (let p = 0; p < A.length; p += 4) {
        if (A[p] !== C[p] || A[p + 1] !== C[p + 1] || A[p + 2] !== C[p + 2] || A[p + 3] !== C[p + 3]) temoin++;
        if (A[p] !== B[p] || A[p + 1] !== B[p + 1] || A[p + 2] !== B[p + 2] || A[p + 3] !== B[p + 3]) vis++;
      }
    }

    MASK = {
      sig: sig, W: W, H: H, poseW: pw1, poseH: ph1, pose: poseA,
      inWin: inWin, vis: vis, temoin: temoin,
      /* ce que le calcul exact PREDIT pour (a) : l'ecart des deux mesure la
         seule difference legitime, la rasterisation du quadrilatere. Il se
         derive de la MEME aire publiee, sinon l'ecart afficherait la
         difference de nos deux arrondis au lieu de celle du rendu. */
      predit: (typeof LAST.vis === "number" ? LAST.vis * poseA : null),
    };
  }

  function scheduleMask() {
    /* Rien a refaire : meme etat, meme resultat. C'est ce test qui empeche la
       boucle a deux modules decrite au-dessus. */
    if (MASK && MASK.sig === maskSignature()) return;
    clearTimeout(maskTimer);
    const attente = Math.max(700, MASK_MIN_MS - (Date.now() - maskAt));
    maskTimer = setTimeout(async () => {
      if (!LAST.has) { MASK = null; return; }
      /* Une mesure en cours n'est jamais interrompue : on repasse apres. Sans
         ce report, un etat modifie pendant la mesure gardait « mesure en
         cours… » pour toujours. */
      if (maskBusy) { maskTimer = setTimeout(scheduleMask, 300); return; }
      maskBusy = true; maskAt = Date.now();
      try { await measureMask(); }
      catch (e) { MASK = null; console.warn("mod-face: mesure du masquage", e); }
      finally { maskBusy = false; maskAt = Date.now(); }
      paintGauge();
    }, attente);
  }

  /* Ce que la fenetre retient, puis ce que le fichier livre garde. Deux
     grandeurs, deux phrases, et jamais le mot « visible » pour la premiere. */
  function cropLine() {
    if (!LAST.has || typeof LAST.vis !== "number") return "";
    const p = LAST.vis * 100;
    const dans = p >= 99.95
      ? '<span class="mono">Fenêtre d\'illustration : la pose y tient entière, aucun recadrage.</span>'
      : '<span class="cf-face-crop"><b>' + fmt1(p) + ' % de la pose tient dans la fenêtre '
        + 'd\'illustration</b> — les ' + fmt1(100 - p) + ' % restants en sortent et sont '
        + 'coupés. Passez en « Contenir » pour tout garder, ou déplacez la pose.'
        /* le chiffre etait honnete, le geste manquait : la correction s'offre
           A COTE de la mesure, et seulement si elle changerait quelque chose. */
        + (poseCalee() ? '' : ' <button class="btn sm" type="button" '
          + 'data-fix="window">Recadrer sur la fenêtre</button>')
        + '</span>';
    return dans + maskLine();
  }

  /* ── LE VERDICT DEVANT, L'INSTRUMENTATION DERRIERE ───────────────────────
     REPROCHE, MOT POUR MOT : « Le panneau de definition deverse de la
     telemetrie interne dans la surface du produit : "temoin de determinisme
     0 px", "fenetre recomptee 904 650 px contre 904 650 predits (0,00 %)",
     "remplissage 50,0 %". La seule phrase dont l'utilisateur a besoin —
     300 DPI, c'est bon pour imprimer — est noyee dedans. »
     Le reproche est fonde et il nomme TROIS chiffres precis. Les retirer
     serait la faute inverse : ce sont eux qui rendent le pourcentage
     verifiable, et ce tour interdit tout nombre qu'on ne peut pas recompter.
     Ils descendent donc — tous les trois, au mot pres — dans un tiroir
     « le detail, chiffre par chiffre » que le panneau porte en permanence et
     qui s'ouvre d'un clic. Rien n'est supprime, rien n'est arrondi : ce qui
     change, c'est l'ordre de lecture. Mesure de l'effet dans les tests. */
  function maskLine() {
    const stale = !MASK || MASK.sig !== maskSignature();
    if (stale) return '<span class="mono">Ce qui atteint le papier : mesure en cours…</span>';
    if (MASK.temoin > 0) {
      /* L'hypothese de determinisme est FAUSSE : on ne publie pas un nombre
         qu'on vient soi-meme de contredire. */
      return '<span class="cf-face-crop">Ce qui atteint le papier : <b>non mesurable</b> — '
        + 'deux rendus identiques de cette carte diffèrent de '
        + MASK.temoin.toLocaleString("fr-FR") + ' pixels, une couche du dessus n\'est pas '
        + 'déterministe. Aucun pourcentage ne serait vérifiable ici.</span>';
    }
    const pv = 100 * MASK.vis / MASK.pose;
    const pw = 100 * MASK.inWin / MASK.pose;
    const cls = pv >= 99.95 ? "mono" : "cf-face-crop";
    return '<span class="' + cls + '">Sur la carte imprimée : <b>' + fmt1(pv)
      + ' % de la pose atteint le papier</b>'
      + (pv + 0.05 < pw ? ' — le cadre et les textes en masquent ' + fmt1(pw - pv)
        + ' points de plus.' : '.')
      + '</span>';
  }

  /* Le comptage qui rend le pourcentage ci-dessus recalculable. Les trois
     grandeurs nommees par le reproche sont ici, entieres, et la ligne de pose
     porte desormais sa MULTIPLICATION en clair : 815 x 1222.5 = 996 337,5. */
  function maskDetail() {
    if (!MASK || MASK.sig !== maskSignature() || MASK.temoin > 0) return "";
    const ecart = MASK.predit ? Math.abs(MASK.inWin - MASK.predit) / MASK.pose * 100 : null;
    const carte = MASK.W + ' × ' + MASK.H + ' = ' + (MASK.W * MASK.H).toLocaleString("fr-FR") + ' px';
    /* Quand la pose couvre exactement la toile, les deux membres portent les
       memes trois nombres : les repeter deux fois n'ajoute rien et c'est
       precisement le genre de remplissage qu'on nous reproche. */
    const meme = px1(MASK.poseW) === MASK.W && px1(MASK.poseH) === MASK.H;
    return '<span class="mono">Compté par le moteur : ' + MASK.vis.toLocaleString("fr-FR")
      + ' px sur ' + (meme
        ? 'une pose qui couvre la carte entière, ' + carte
        : fmtPx(MASK.poseW) + ' × ' + fmtPx(MASK.poseH) + ' = ' + frac1(MASK.pose)
          + ' px de pose, dans une carte de ' + carte)
      + ' ; témoin de déterminisme ' + MASK.temoin + ' px'
      + (ecart === null ? '' : ' ; fenêtre recomptée ' + MASK.inWin.toLocaleString("fr-FR")
        + ' px contre ' + frac1(px1(MASK.predit)) + ' prédits (' + ecart.toFixed(2) + ' %)')
      + '.</span>';
  }

  /* Le tiroir. Ouvert ou ferme, l'etat survit aux repeintures de la jauge —
     un utilisateur qui l'a ouvert pour verifier ne veut pas le voir se
     refermer a chaque deplacement de l'illustration. */
  let DETAIL_OPEN = false;
  function detailsBlock(rows) {
    const body = rows.filter(Boolean).join("");
    if (!body) return "";
    return '<details class="cf-face-det"><summary>le détail, chiffre par chiffre</summary>'
      + body + '</details>';
  }
  function wireDetails(box) {
    const d = box.querySelector("details.cf-face-det");
    if (!d) return;
    d.open = DETAIL_OPEN;
    d.addEventListener("toggle", () => { DETAIL_OPEN = d.open; });
  }

  /* ── LA COUCHE DE FINITION, DITE SANS QU'ON LA DEMANDE ───────────────────
     REPROCHE DU TOUR 2 : « L'illustration livrée N'EST PAS l'illustration
     importée : les noirs sont levés du double. RIEN DANS L'INTERFACE
     N'ANNONCE CETTE RETOUCHE ni ne permet de l'éteindre. »

     MESURE FAITE PAR LE VRAI CHEMIN, ET ELLE DONNE RAISON AU CRITIQUE. J'ai
     déposé une image de plages plates exactes, exporté par le vrai bouton et
     relu les octets du fichier livré : là où la source vaut (17,13,26), le
     fichier rend (35,27,47) — le chiffre du critique, à l'unité. Là où elle
     vaut (0,0,0), le fichier rend (0,0,0) : ni voile opaque ni gain linéaire,
     mais une fusion qui laisse le noir et le blanc en place.

     Le contrôle de fidélité mesurait déjà tout cela — MAIS SUR DEMANDE. Un
     réglage qui modifie l'illustration doit se lire sans avoir à le chercher.
     Cette ligne est donc debout dès que le voile agit ; elle ne mesure rien,
     elle RECOPIE les trois réglages publiés par la pièce 06 dans le document
     (lecture seule, absence tolérée) et dit où les éteindre. */
  function finishLine() {
    try {
      const ov = CF.get("texture.over", null);
      if (!ov || ov === "none") return "";
      const op = Number(CF.get("texture.over_opacity", 0));
      if (!(op > 0)) return "";
      const bl = String(CF.get("texture.over_blend", "") || "normal");
      return '<span class="cf-face-crop">Couche de finition par-dessus l\'illustration : <b>'
        + esc(String(ov)) + '</b>, opacité ' + Math.round(op * 100) + ' %, fusion ' + esc(bl)
        + ' — <b>vos couleurs en sortent modifiées</b>. Réglage dans Matières.</span>';
    } catch (e) { return ""; }        /* piece 06 absente : rien a annoncer */
  }

  /* Ce que le fichier depose mesurait AVANT la reduction d'import, quand il y
     en a eu une. La jauge appelle « source » la trame qu'elle mesure ; si cette
     trame n'est plus le fichier de l'utilisateur, le panneau doit le dire au
     lieu de laisser croire que le fichier faisait cette taille. Lecture seule
     dans la pile — le painter n'est pas touche. */
  function importNote() {
    const s = String(CF.get("face.src", "") || "");
    if (s.indexOf("local:") !== 0) return "";
    const r = pileByKey(s.slice(6));
    if (!r || typeof r.w0 !== "number" || typeof r.h0 !== "number") return "";
    if (r.w0 === r.w && r.h0 === r.h) return "";
    return '<span class="mono">fichier déposé ' + r.w0 + ' × ' + r.h0
      + ' px, ramené à ' + MAX_IMPORT_PX + ' px de côté à l\'import : c\'est la trame '
      + 'ci-dessus qui est posée et mesurée.</span>';
  }

  /* ── la jauge : LE chiffre, colle a la carte ───────────────────────────── */
  function paintGauge() {
    const box = q("#cf-face-gauge");
    if (!box) return;
    const g = CF.geom();
    if (!LAST.has) {
      box.className = "cf-face-gauge cf-face-none";
      box.innerHTML = '<div class="cf-face-gnum">—</div>'
        + '<div class="cf-face-gbody"><b>Aucune illustration posée</b>'
        + '<span>Choisissez une face du catalogue, déposez une image ou générez-la. '
        + 'La jauge affichera alors le DPI réel de l\'impression.</span></div>';
      return;
    }
    if (LAST.vector) {
      /* CE QUI A CHANGE, ET LA MESURE QUI L'A IMPOSE — voir `rasterDpi`.
         L'ecran disait « ∞ · Aucune perte possible · la jauge ne s'applique
         pas », a 300 DPI COMME A 150. C'etait faux a 150 : la toile rendue y
         fait 407 x 555 px pour 69,0 x 94,0 mm, soit 150 DPI, et c'est bien la
         definition a laquelle cette face part chez l'imprimeur. Un « aucune
         perte possible » sur une trame de 150 DPI est exactement le chiffre
         invérifiable que ce tour interdit.
         La jauge mesure donc la MEME grandeur dans les deux cas — la densite
         de la trame livree — et applique le MEME seuil. Ce qui change, c'est
         la cause et donc la correction : sur un bitmap on manque de pixels
         source, ici c'est la toile qui est trop grossiere, et le reglage
         n'est pas dans ce panneau. On le dit au lieu de se taire. */
      const rast = rasterDpi(g);
      const okv = rast + 1e-9 >= DPI_TARGET;
      box.className = "cf-face-gauge " + (okv ? "cf-face-ok" : "cf-face-low");
      const pctv = gaugeFill(rast, DPI_TARGET);
      box.innerHTML = '<div class="cf-face-gnum">' + Math.round(rast) + '<i>DPI</i></div>'
        + '<div class="cf-face-gbody">'
        + '<b>' + (okv ? "Définition suffisante pour l\'impression" : "Définition insuffisante — sous " + DPI_TARGET + " DPI") + '</b>'
        + '<div class="cf-face-gbar"><span style="width:' + fmt1(pctv) + '%"></span>'
        + '<em style="left:50%">' + DPI_TARGET + '</em></div>'
        /* PAS DE TERME INTERMEDIAIRE ARRONDI. Une premiere redaction disait
           « 815 px pour 69.0 mm = 300.0000 DPI » : un lecteur qui refait la
           division sur les chiffres AFFICHES trouve 300,014, parce que la
           largeur exacte est 69,0033 mm. Un chiffre juste presente avec un
           intermediaire arrondi devient un chiffre qu'on ne peut pas
           verifier. On donne donc la grandeur mesuree et le chemin qui l'a
           produite, sans etape a moitie ecrite. */
        + '<span class="mono">face vectorielle : redessinée à ' + fmtPx(LAST.dw) + ' × '
        + fmtPx(LAST.dh) + ' px, la trame même de la toile — sa définition suit celle-ci '
        + 'et ne peut pas la dépasser.</span>'
        + cropLine() + finishLine()
        + (okv ? '' : '<span class="cf-face-need">Aucune source à agrandir ici : c\'est la '
          + '<b>toile</b> qui est à ' + g.dpi + ' DPI.</span>')
        + detailsBlock([
          '<span class="mono">Toile ' + g.canvas_px[0] + ' × ' + g.canvas_px[1]
          + ' px pour ' + fmt1(g.px2mm(g.canvas_px[0])) + ' × ' + fmt1(g.px2mm(g.canvas_px[1]))
          + ' mm, soit ' + Math.round(rast) + ' DPI · définitions offertes : '
          + (CF.DPIS || []).join(" / ") + ' DPI</span>',
          '<span class="mono">Barre : échelle 0 – ' + (2 * DPI_TARGET) + ' DPI, repère à '
          + DPI_TARGET + ' (mi-barre) · remplissage ' + fmt1(pctv) + ' %</span>',
          maskDetail(),
        ])
        + '</div>';
      wireDetails(box);
      const wv = q("#cf-face-warn");
      if (wv) {
        wv.classList.toggle("hidden", okv);
        if (!okv) {
          wv.innerHTML = '<b>Avant d\'imprimer</b><span>Cette face sortira à '
            + Math.round(rast) + ' DPI, parce que la toile est à ' + g.dpi + ' DPI. '
            + 'Le réglage n\'est pas dans ce panneau : la définition se choisit dans la '
            + 'barre de format, en haut (' + (CF.DPIS || []).join(" / ")
            + ' DPI).</span>';
        }
      }
      return;
    }
    const ok = LAST.eff + 1e-9 >= DPI_TARGET;
    box.className = "cf-face-gauge " + (ok ? "cf-face-ok" : "cf-face-low");
    /* CE QUI A CHANGE, ET LA MESURE QUI L'A IMPOSE. « La jauge sature : le
       remplissage s'arrete pile sur le repere (mesure au pixel : remplissage
       2210..3001, repere a 3003). 324 DPI et 900 DPI donneront la meme barre
       pleine. » Exact, et c'etait une barre qui mentait par saturation.
       L'echelle va desormais de 0 a 2 x la cible et le repere est au milieu :
       324 remplit 54 %, 600 remplit 100 %, et le pourcentage est ECRIT a
       cote pour qu'il se verifie a la regle sur la capture. */
    const pct = gaugeFill(LAST.eff, DPI_TARGET);
    box.innerHTML = '<div class="cf-face-gnum">' + Math.round(LAST.eff) + '<i>DPI</i></div>'
      + '<div class="cf-face-gbody">'
      + '<b>' + (ok ? "Définition suffisante pour l\'impression" : "Définition insuffisante — sous " + DPI_TARGET + " DPI") + '</b>'
      + '<div class="cf-face-gbar"><span style="width:' + fmt1(pct) + '%"></span>'
      + '<em style="left:50%">' + DPI_TARGET + '</em></div>'
      + '<span class="mono">source ' + LAST.sw + ' × ' + LAST.sh + ' px'
      + ' · posée ' + fmtPx(LAST.dw) + ' × ' + fmtPx(LAST.dh) + ' px</span>'
      + importNote() + cropLine() + finishLine()
      + (ok ? '' : '<span class="cf-face-need">Il faudrait une source de <b>'
        + LAST.need + ' × ' + LAST.needH + ' px</b> à cette taille de pose.</span>')
      + detailsBlock([
        /* LA FORMULE, PAS UN RESUME, ET REFAITE SUR LES VALEURS PUBLIEES.
           Le DPI effectif est le PLUS PETIT des deux rapports (largeur et
           hauteur) : n'en ecrire qu'un donnerait un calcul qui tombe juste
           par hasard tant que les proportions sont verrouillees, et faux des
           qu'on les deverrouille. Les deux divisions se refont a la main sur
           les nombres imprimes juste au-dessus — c'est la seule raison
           d'ecrire une formule. */
        '<span class="mono">Toile ' + g.canvas_px[0] + ' × ' + g.canvas_px[1] + ' px à '
        + g.dpi + ' DPI · DPI effectif = plus petit de ( ' + g.dpi + ' × ' + LAST.sw + ' / '
        + fmtPx(LAST.dw) + ' = ' + fmt1(g.dpi * LAST.sw / Math.max(1e-6, px1(LAST.dw)))
        + ' ; ' + g.dpi + ' × ' + LAST.sh + ' / ' + fmtPx(LAST.dh) + ' = '
        + fmt1(g.dpi * LAST.sh / Math.max(1e-6, px1(LAST.dh))) + ' ) = <b>'
        + fmt1(Math.min(g.dpi * LAST.sw / Math.max(1e-6, px1(LAST.dw)),
          g.dpi * LAST.sh / Math.max(1e-6, px1(LAST.dh))))
        + ' DPI</b>, arrondi à ' + Math.round(LAST.eff) + ' — le nombre de la jauge</span>',
        '<span class="mono">Barre : échelle 0 – ' + (2 * DPI_TARGET) + ' DPI, repère à '
        + DPI_TARGET + ' (mi-barre) · remplissage ' + fmt1(pct) + ' %</span>',
        maskDetail(),
      ])
      + '</div>';
    wireDetails(box);
    const warn = q("#cf-face-warn");
    if (warn) {
      warn.classList.toggle("hidden", ok);
      if (!ok) {
        warn.innerHTML = '<b>Avant d\'imprimer</b><span>L\'illustration sortira à '
          + Math.round(LAST.eff) + ' DPI, pour ' + DPI_TARGET + ' DPI d\'impression. '
          + 'Deux réglages la ramènent à ' + DPI_TARGET + ' :</span>'
          + '<div class="btn-row"><button class="btn sm" type="button" data-fix="shrink">Réduire à 300 DPI exactement</button>'
          + '<button class="btn sm" type="button" data-fix="contain">Passer en « Contenir »</button></div>';
      }
    }
  }

  function fixShrink() {
    /* La pose passe a la taille ou la source vaut exactement 300 DPI : on
       quitte cover/contain pour « libre », sinon le mode reimposerait sa
       propre echelle a la frame suivante. */
    if (!LAST.has || LAST.vector) return;
    const g = CF.geom();
    pushUndo();
    M.patch({ fit: "free", scale: g.dpi / DPI_TARGET, scale_y: g.dpi / DPI_TARGET });
    CF.toast("posée à " + DPI_TARGET + " DPI exactement");
    renderPanel();
  }

  /* ── LA CORRECTION EN UN CLIC QUI MANQUAIT ──────────────────────────────
     Reste connu du commit de cloture, nomme par les critiques : le cadrage
     par defaut laissait jusqu'a 70 % de l'illustration sous le cadre selon le
     gabarit — le panneau le CHIFFRAIT honnetement (cropLine / maskLine) sans
     offrir le geste qui corrige. Le voici : la pose revient au centre de la
     fenetre d'illustration EFFECTIVE (celle que P2 publie desormais sous
     `frame.art_window` — voir `frameWindow`), en « couvrir », echelle 1.
     Par construction la fenetre est couverte sans trou ; seul le debord de
     format (cover) reste, et la ligne de mesure continue de le chiffrer. */
  function fixWindow() {
    if (!LAST.has) return;
    pushUndo();
    M.patch({ win: "auto", fit: "cover", x: 0, y: 0, scale: 1, scale_y: 1 });
    CF.toast("pose recadrée sur la fenêtre d'illustration");
    renderPanel();
  }

  /* la pose est-elle deja calee sur la fenetre ? (le bouton ne s'offre pas
     pour un geste qui ne changerait rien) */
  function poseCalee() {
    const f = CF.doc().face || {};
    return f.fit === "cover" && !Number(f.x) && !Number(f.y)
      && Number(f.scale) === 1 && String(f.win || "auto") === "auto";
  }

  /* ── grilles ──────────────────────────────────────────────────────────── */
  function thumbCanvas(c, w, h) {
    const cv = document.createElement("canvas");
    const dpr = Math.min(2, (typeof devicePixelRatio === "number" ? devicePixelRatio : 1) || 1);
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
    cv.style.width = w + "px"; cv.style.height = h + "px";
    paintScene(cv.getContext("2d"), cv.width, cv.height, c.palette, c.subject, c.seed, c.compo);
    return cv;
  }

  function catalogRows() {
    const f = CATFILTER.trim().toLowerCase();
    return CATALOG.filter((c) => {
      if (CATTAG && c.subject !== CATTAG) return false;
      if (CATCOMPO && c.compo !== CATCOMPO) return false;
      if (!f) return true;
      const lbl = (c.label + " " + c.palette + " " + c.compo + " " + c.subject
        + " " + (PAL_BY[c.palette] || {}).label).toLowerCase();
      return lbl.indexOf(f) >= 0;
    });
  }

  function fillCatalog() {
    const grid = q("#cf-face-cat-grid");
    if (!grid) return;
    const rows = catalogRows();
    const cur = CF.get("face.src", null);
    grid.innerHTML = "";
    /* Le plancher de hauteur ne s'applique qu'a une grille QUI A des vignettes :
       une grille vide n'a pas a reserver 172 px pour une phrase. */
    grid.classList.toggle("cf-face-gfill", rows.length > 0);
    const n = q("#cf-face-cat-count");
    if (n) n.textContent = rows.length + " / " + CATALOG.length;
    const net0 = (netEntries() || []).length;
    const t0 = (typeof performance !== "undefined" && performance.now) ? performance.now() : 0;
    let i = 0;
    const step = () => {
      const stop = Math.min(rows.length, i + 12);
      for (; i < stop; i++) {
        const c = rows[i];
        const f = serieImg(c);
        const b = document.createElement("button");
        b.type = "button";
        b.className = "cf-face-tile" + (cur === tileSrc(c) ? " on" : "");
        b.setAttribute("data-cat", c.id);
        if (f) {
          /* Une case peinte : le MEME attribut que les faces generees
             (`data-ai`), donc la meme resolution `img:` — pas un quatrieme
             schema de source. */
          b.setAttribute("data-ai", f);
          b.title = c.label + " — série « " + serieLabel() + " », image peinte";
          const im = document.createElement("img");
          im.alt = "";
          im.src = imgURL(f);
          b.appendChild(im);
        } else {
          b.title = c.label + " · palette " + (PAL_BY[c.palette] || {}).label
            + " — vectoriel, redessiné à la taille de la pose";
          b.appendChild(thumbCanvas(c, 84, 118));
        }
        const s = document.createElement("span");
        s.textContent = c.label;
        b.appendChild(s);
        /* LA RETOMBEE, AVOUEE SUR LA VIGNETTE (D1). Sans cet insigne, une
           serie a moitie peinte se lit comme une serie complete dont la
           moitie serait « ratee » : l'utilisateur chercherait un defaut la ou
           il n'y a qu'une case pas encore faite. */
        if (!f && serieActive()) {
          const v = document.createElement("em");
          v.className = "cf-face-retombee";
          v.textContent = "vectoriel";
          b.appendChild(v);
        }
        grid.appendChild(b);
      }
      if (i < rows.length) { requestAnimationFrame(step); return; }
      /* LA MESURE SE FAIT ICI, L'AFFICHAGE ATTEND QU'ON LA DEMANDE. Cette
         ligne — « n vignettes peintes en x ms, 0 image telechargee » — etait
         debout en permanence sous la grille. C'est une preuve, pas un
         reglage : un panneau qui plaide sa cause en continu occupe la hauteur
         qui manque aux commandes, et un critique y a lu, a juste titre, un
         banc de mesure colle dans une interface. Le compte est donc toujours
         PRIS au moment ou il est valable (avant / apres le remplissage) et
         range dans NET_LINE ; « Recompter le catalogue » l'imprime. */
      const t1 = (typeof performance !== "undefined" && performance.now) ? performance.now() : 0;
      const all = netEntries();
      if (!all) { NET_LINE = "Compteur réseau indisponible sur ce moteur."; return; }
      /* On ne dit PAS « 0 requête » : on dit ce que le compteur montre, y
         compris les requetes des AUTRES pieces qui passent pendant ce temps
         (l'enregistrement du document, par exemple). Ce qui prouve le
         catalogue, c'est le nombre d'IMAGES : il doit rester a zero, et on le
         nomme separement — avec les URL des autres, pour qu'un tiers puisse
         verifier qu'aucune n'est une illustration. */
      const neuves = all.slice(net0);
      const imgs = neuves.filter(isImageEntry);
      const noms = neuves.slice(0, 4).map((e) => baseName(e.name));
      NET_LINE = '<b>Mesuré à l\'instant</b> : ' + rows.length + ' vignettes peintes en '
        + Math.round(t1 - t0) + ' ms — <b>' + imgs.length + ' image téléchargée</b>. '
        + '<span class="mono">performance.getEntriesByType("resource")</span> : '
        + net0 + ' entrées avant, ' + all.length + ' après'
        + (neuves.length ? ' (' + esc(noms.join(", ")) + (neuves.length > 4 ? ", …" : "") + ')' : '')
        + '.';
    };
    step();
  }

  /* ── LA PREUVE : les nombres affiches, RECOMPTES sur les octets rendus ────
     « 72 dessins distincts » et « 864 combinaisons » restent des affirmations
     tant qu'un tiers ne peut pas les compter lui-meme. Ce bouton les compte.
     Il redessine chaque face hors ecran, hache les octets rendus par
     `getImageData` et denombre les hachages DISTINCTS. Deux mesures, pas une :
       (a) les 72 dessins peints DANS LA MEME PALETTE (« Cendre ») — c'etait
           le reproche des deux critiques : « 72 faces » pour un meme dessin
           recolore. Peints dans la meme teinte, deux dessins identiques
           tomberaient sur le meme hachage ;
       (b) les 864 identifiants legaux, chacun avec sa propre palette.
     Un hachage distinct peut tenir a un seul pixel : on donne donc AUSSI la
     paire la plus PROCHE des 72, avec son ecart moyen par canal. C'est le pire
     cas, pas la moyenne — le seul chiffre qu'on ne puisse pas maquiller. */
  function hashPixels(d) {
    let h = 2166136261 >>> 0;
    for (let i = 0; i < d.length; i += 4) {
      h = Math.imul(h ^ d[i], 16777619) >>> 0;
      h = Math.imul(h ^ d[i + 1], 16777619) >>> 0;
      h = Math.imul(h ^ d[i + 2], 16777619) >>> 0;
    }
    return h >>> 0;
  }
  function renderScene(ctx, w, h, pal, sub, compo) {
    /* meme graine que l'identifiant du catalogue : la vignette de la preuve
       est le MEME dessin que la face posee, pas une approximation. */
    const fid = "face_" + pal + "_" + compo + "_" + sub;
    ctx.clearRect(0, 0, w, h);
    paintScene(ctx, w, h, pal, sub, fnv1a32(fid), compo);
    return ctx.getImageData(0, 0, w, h).data;
  }
  const yieldFrame = () => new Promise((r) => setTimeout(r, 0));

  async function proveCatalog() {
    const el = q("#cf-face-proofout");
    const btn = q("#cf-face-proof");
    if (btn) btn.disabled = true;
    if (el) el.textContent = "mesure en cours…";
    try {
      const t0 = performance.now();
      /* (a) 72 dessins, palette unique */
      const W = 64, H = 90;
      const cv = document.createElement("canvas");
      cv.width = W; cv.height = H;
      const ctx = cv.getContext("2d", { willReadFrequently: true });
      const REF = "ash";
      const pix = [], names = [], hset = new Set();
      for (let si = 0; si < SUBJECTS.length; si++) {
        for (let ci = 0; ci < COMPOS.length; ci++) {
          const d = renderScene(ctx, W, H, REF, SUBJECTS[si].id, COMPOS[ci].id);
          pix.push(new Uint8Array(d));
          names.push(SUBJECTS[si].label + " — " + COMPOS[ci].label);
          hset.add(hashPixels(d));
        }
        if (si % 4 === 3) await yieldFrame();
      }
      /* PIRE CAS : la paire la plus PROCHE. On la choisit sur l'ecart moyen
         calcule sur TOUTE la vignette — la statistique la plus severe pour
         nous, puisqu'un fond commun la tire vers zero meme quand les sujets
         different franchement. Et on la decrit ensuite avec les deux nombres
         qui disent vraiment ce qu'un oeil verrait : la PART des pixels qui
         different, et de combien ILS different. */
      let best = 1e9, bi = 0, bj = 0;
      const N = pix.length, LEN = W * H * 4, NPX = W * H;
      for (let i = 0; i < N; i++) {
        for (let j = i + 1; j < N; j++) {
          const a = pix[i], b = pix[j];
          let s = 0;
          for (let p = 0; p < LEN; p += 4) {
            s += Math.abs(a[p] - b[p]) + Math.abs(a[p + 1] - b[p + 1]) + Math.abs(a[p + 2] - b[p + 2]);
          }
          const m = s / (NPX * 3);
          if (m < best) { best = m; bi = i; bj = j; }
        }
        if (i % 8 === 7) await yieldFrame();
      }
      let nd = 0, sd = 0, mxd = 0;
      for (let p = 0; p < LEN; p += 4) {
        const d = Math.max(Math.abs(pix[bi][p] - pix[bj][p]),
          Math.abs(pix[bi][p + 1] - pix[bj][p + 1]),
          Math.abs(pix[bi][p + 2] - pix[bj][p + 2]));
        if (d) { nd++; sd += d; if (d > mxd) mxd = d; }
      }
      const pctDiff = 100 * nd / NPX;
      const moyDiff = nd ? sd / nd : 0;
      /* (b) 864 combinaisons */
      const w2 = 40, h2 = 56;
      const cv2 = document.createElement("canvas");
      cv2.width = w2; cv2.height = h2;
      const c2 = cv2.getContext("2d", { willReadFrequently: true });
      const hset2 = new Set();
      let n2 = 0;
      for (let si = 0; si < SUBJECTS.length; si++) {
        for (let ci = 0; ci < COMPOS.length; ci++) {
          for (let pi = 0; pi < PALETTES.length; pi++) {
            hset2.add(hashPixels(renderScene(c2, w2, h2, PALETTES[pi].id, SUBJECTS[si].id, COMPOS[ci].id)));
            n2++;
          }
        }
        await yieldFrame();
      }
      const ms = Math.round(performance.now() - t0);
      if (el) {
        el.innerHTML = '<b>Recompté sur les octets rendus</b>, ' + ms + ' ms. '
          + '(a) les ' + DRAWINGS + ' dessins peints dans la <b>même</b> palette (' + esc(PAL_BY[REF].label)
          + ', ' + W + '×' + H + ' px) donnent <b>' + hset.size + ' / ' + DRAWINGS
          + ' empreintes distinctes</b>. '
          + 'Paire la plus <b>proche</b> : « ' + esc(names[bi]) + ' » et « ' + esc(names[bj])
          + ' » — <b>' + pctDiff.toFixed(1) + ' % des ' + (W * H) + ' pixels</b> diffèrent, '
          + 'de <b>' + Math.round(moyDiff) + ' niveaux</b> en moyenne sur ceux-là (maximum '
          + mxd + '), soit ' + (Math.round(best * 10) / 10) + ' niveau(x)/canal ramené à '
          + 'la vignette entière — fond commun compris. '
          + '(b) les ' + n2 + ' combinaisons (' + w2 + '×' + h2 + ' px) donnent <b>'
          + hset2.size + ' / ' + COMBINATIONS + ' empreintes distinctes</b>. '
          + '<span class="mono">FNV-1a 32 bits sur getImageData, canaux R/V/B</span>.';
      }
      /* et le releve reseau du remplissage, pris a son heure, imprime a la
         demande — pas debout sous la grille en permanence */
      const nl = q("#cf-face-net");
      if (nl) nl.innerHTML = NET_LINE;
    } catch (e) {
      if (el) el.textContent = "la mesure a échoué : " + String((e && e.message) || e);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function fillPile() {
    const grid = q("#cf-face-pile-grid");
    if (!grid) return;
    const cur = CF.get("face.src", null);
    grid.classList.toggle("cf-face-gfill", PILE.length > 0);
    if (!PILE.length) {
      grid.innerHTML = '<p class="empty-note sm">La pile est vide. Déposez plusieurs fichiers d\'un coup, '
        + 'collez une image (Ctrl+V) ou piochez dans le catalogue — ' + DRAWINGS
        + ' dessins vectoriels vous attendent.</p>';
      return;
    }
    grid.innerHTML = PILE.map((r) => {
      /* Le DPI d'une vignette de la pile est celui qu'elle AURAIT en
         « couvrir » dans la FENETRE COURANTE — pas dans la toile entiere.
         Avec la fenetre 3:4 (673 px au lieu de 815), le meme fichier de
         650 px vaut 290 DPI et non 239 : afficher 239 serait faux.

         ATTRAPE A L'ECRAN PENDANT CE TOUR, ET C'ETAIT FAUX. Le calcul ne
         regardait que la LARGEUR (dpi * w / bw). « Couvrir » prend le PLUS
         GRAND des deux rapports : sur une source paysage dans une fenetre
         portrait, c'est la hauteur qui commande. Mesure : un 1600x900 dans
         815x1110 sort a 243 DPI (la jauge le disait), et la vignette
         annoncait « ~589 DPI » a dix centimetres de la. Deux chiffres qui se
         contredisent sur le meme ecran, dont un faux. On passe donc par
         `fitRect`, le MEME calcul que le painter, et par la meme formule de
         DPI effectif : les deux nombres ne peuvent plus diverger. */
      const g = CF.geom();
      const win = artWindow(g);
      const d = fitRect(r.w, r.h, win[2], win[3], "cover", 1);
      const eff = Math.round(Math.min(g.dpi * r.w / Math.max(1e-6, d[0]),
        g.dpi * r.h / Math.max(1e-6, d[1])));
      /* La taille du FICHIER DEPOSE quand elle differe de celle qui est
         reellement rangee (reduction au-dela de MAX_IMPORT_PX) : les deux
         nombres, avec la fleche entre eux, plutot qu'un seul qui laisserait
         croire que le fichier faisait cette taille-la. */
      const reduit = (typeof r.w0 === "number" && typeof r.h0 === "number"
        && (r.w0 !== r.w || r.h0 !== r.h))
        ? r.w0 + '×' + r.h0 + ' → ' : '';
      return '<div class="cf-face-tile cf-face-imp' + (cur === "local:" + r.key ? " on" : "") + '" data-imp="' + esc(r.key) + '">'
        + '<img alt="" src="' + esc(r.url) + '">'
        + '<span>' + esc(r.name) + '</span>'
        + '<em class="mono ' + (eff >= DPI_TARGET ? "cf-face-eok" : "cf-face-elow") + '">'
        + reduit + r.w + '×' + r.h + ' · ~' + eff + ' DPI</em>'
        + '<button class="cf-face-del" type="button" data-del="' + esc(r.key) + '" title="Retirer de la pile">×</button>'
        + '</div>';
    }).join("");
  }

  function fillAI() {
    const box = q("#cf-face-ai-out");
    if (!box) return;
    if (!AI_OUT.length) { box.innerHTML = ""; return; }
    const cur = CF.get("face.src", null);
    box.innerHTML = '<div class="lbl">Dernière génération</div><div class="cf-face-grid cf-face-gfill">'
      + AI_OUT.map((f) => '<div class="cf-face-tile' + (cur === "img:" + f ? " on" : "") + '" data-ai="' + esc(f) + '">'
        + '<img alt="" src="' + esc(imgURL(f)) + '"><span>' + esc(f) + '</span></div>').join("")
      + '</div>';
  }

  /* ── le panneau complet ───────────────────────────────────────────────── */
  function renderPanel() {
    if (!HOST) return;
    const f = CF.doc().face;
    const g = CF.geom();
    const tab = ["cat", "imp", "ai"].indexOf(f.tab) >= 0 ? f.tab : "cat";
    const serie = serieActive() || "vectoriel";
    const free = f.fit === "free";
    /* CE QU'IL Y A A ADOPTER DE LA PIECE 10, calcule ICI et pas garde : le
       panneau se repeint sur `core:doc` quand `capture` bouge, et la
       dérivation est refaite. */
    const adopt = adoptionCapture(CF.doc());
    HOST.innerHTML =
      '<div class="cf-face-gauge" id="cf-face-gauge"></div>'
      + '<div class="cf-face-warn hidden" id="cf-face-warn"></div>'

      + '<div class="seg sm cf-face-tabs" id="cf-face-tabs">'
      + '<button class="seg-b' + (tab === "cat" ? " active" : "") + '" type="button" data-tab="cat">Catalogue ' + DRAWINGS + '</button>'
      + '<button class="seg-b' + (tab === "imp" ? " active" : "") + '" type="button" data-tab="imp">Importées ' + PILE.length + '</button>'
      + '<button class="seg-b' + (tab === "ai" ? " active" : "") + '" type="button" data-tab="ai">Générer par IA</button>'
      + '</div>'

      /* ── catalogue ── */
      + '<div class="cf-face-pane' + (tab === "cat" ? " on" : "") + '" id="cf-face-pane-cat">'
      /* ORDRE DES BLOCS — impose par une mesure, pas par le gout. Dans l'app
         le panneau ne fait que 331 px de haut (iframe 508 px, la SPA prend le
         reste). Avec les explications et les deux rangs de jetons AVANT la
         grille, celle-ci commencait a 384 px : le catalogue, livrable phare
         de la piece, etait entierement sous la ligne de flottaison a
         l'ouverture. Les filtres restent en haut (c'est leur place), les
         EXPLICATIONS passent sous la grille : elles se lisent apres, pas
         avant. Les 18 sujets deviennent un menu au lieu de trois lignes de
         jetons — 53 px repris a la grille. */
      /* LE SELECTEUR DE VOIE, AU-DESSUS DES FILTRES. Il est DERIVE de
         `doc.face.serie` (aucun etat local), et le compte « n / 108 » vient
         du manifeste, pas d'une constante. */
      + '<div class="seg sm cf-face-series" id="cf-face-series">'
      + SERIES.map((s) => '<button class="seg-b' + (serie === s.id ? " active" : "")
        + '" type="button" data-voie="' + esc(s.id) + '">' + esc(s.label)
        + (s.id === "vectoriel" ? " " + DRAWINGS
          : " " + SERIE.faites + "/" + (SERIE.total || DRAWINGS)) + '</button>').join("")
      + '</div>'
      + '<div class="cf-face-row">'
      + '<input class="search sm cf-face-search" id="cf-face-search" type="text" placeholder="filtrer (loup, blason, braise…)" value="' + esc(CATFILTER) + '">'
      + '<select class="sm cf-face-sub" id="cf-face-subject" title="filtrer par sujet">'
      + '<option value="">tous les sujets (' + SUBJECTS.length + ')</option>'
      + SUBJECTS.map((s) => '<option value="' + esc(s.id) + '"' + (CATTAG === s.id ? " selected" : "") + '>' + esc(s.label) + '</option>').join("")
      + '</select>'
      + '<span class="counter" id="cf-face-cat-count"></span>'
      + '<button class="btn sm" type="button" id="cf-face-rand">Au hasard</button>'
      + '</div>'
      + '<div class="chips cf-face-tags" id="cf-face-compos">'
      + '<button class="chip' + (CATCOMPO ? "" : " active") + '" type="button" data-compo="">toutes compositions</button>'
      + COMPOS.map((c) => '<button class="chip' + (CATCOMPO === c.id ? " active" : "") + '" type="button" data-compo="' + esc(c.id) + '">' + esc(c.label) + '</button>').join("")
      + '</div>'
      + '<div class="cf-face-grid" id="cf-face-cat-grid"></div>'
      /* CE QUI A CHANGE : l'etiquette disait « Catalogue 72 » et « 72 faces
         vectorielles » pour 12 dessins recolores 6 fois. Les deux critiques
         l'ont compte a la main. On compte maintenant CE QUI EST DISTINCT, et
         on nomme separement ce qui ne l'est pas : les dessins d'un cote, les
         recolorations de l'autre. Les trois nombres sont calcules depuis les
         tables, jamais ecrits a la main — et le bouton ci-dessous les
         VERIFIE sur les octets rendus, vignette par vignette. */
      /* CE QUI A CHANGE. Le paragraphe enumerait quatre compositions sur six
         (« le panorama a un horizon, le medaillon n'en a aucun… ») : une
         enumeration incomplete presentee comme une definition. Et la ligne du
         compteur reseau restait affichee en permanence, ce qui est une
         plaidoirie debout. Les NOMBRES restent — ils sont calcules depuis les
         tables — les commentaires descendent sous le bouton qui les prouve. */
      + '<p class="hint cf-face-count">' + SUBJECTS.length + ' sujets × ' + COMPOS.length
      + ' compositions = <b>' + DRAWINGS + ' dessins</b>. Chacun se recolore en '
      + PALETTES.length + ' palettes : <b>' + COMBINATIONS + ' combinaisons</b> en tout.</p>'
      /* L'AVEU CHIFFRE DE LA VOIE ACTIVE. Il n'apparait que quand une serie
         est choisie, et il dit les DEUX nombres : ce qui est peint, et ce qui
         reste le dessin. */
      + (serie === "vectoriel" ? ''
        : '<p class="hint cf-face-serie-note" id="cf-face-serie-note">Série <b>'
        + esc(serieLabel()) + '</b> : <b>' + SERIE.faites + '</b> case(s) peinte(s) sur '
        + (SERIE.total || DRAWINGS) + '. Les autres restent le <b>dessin vectoriel</b>, '
        + 'marqué comme tel sur la vignette'
        + (SERIE.ok ? '' : ' — l\'état de la série n\'a pas pu être lu')
        + '.</p>')
      + '<div class="cf-face-row">'
      + '<button class="btn sm" type="button" id="cf-face-proof">Recompter le catalogue</button>'
      + '</div>'
      + '<p class="hint mono cf-face-net" id="cf-face-proofout"></p>'
      + '<p class="hint mono cf-face-net" id="cf-face-net"></p>'
      + '</div>'

      /* ── importées ── */
      + '<div class="cf-face-pane' + (tab === "imp" ? " on" : "") + '" id="cf-face-pane-imp">'
      + '<div class="drop cf-face-drop" id="cf-face-drop">'
      + '<b>Glissez vos illustrations ici</b>'
      + '<span class="hint">…ou cliquez pour choisir — <b>plusieurs fichiers d\'un coup</b> — ou collez avec <b>Ctrl+V</b>. '
      + 'Chaque image rejoint la pile avec sa taille en pixels et le DPI qu\'elle donnerait '
      + 'sur cette carte, écrits sous sa vignette. Au-delà de ' + MAX_IMPORT_PX
      + ' px de côté, elle est ramenée à ' + MAX_IMPORT_PX + ' px et la vignette le dit.</span>'
      + '<input type="file" id="cf-face-file" accept="image/*" multiple hidden>'
      + '</div>'
      + (DB_OK ? '' : '<p class="hint cf-face-nodb">Le stockage local du navigateur est indisponible : la pile ne survivra pas au rechargement.</p>')
      /* Une mire de controle est un outil de prepresse ordinaire — elle se
         range dans la pile et se retire comme n'importe quelle image. Son
         LIBELLE ne dit plus que ce qu'elle est et ce qu'elle mesure : sa
         taille reelle, ecrite sur elle et relue par la vignette. */
      + '<div class="cf-face-row"><button class="btn sm" type="button" id="cf-face-mire">'
      + 'Mire de contrôle ' + MIRE_W + ' × ' + MIRE_H + ' px</button></div>'
      + '<p class="hint">Un damier dessiné à la demande, rangé dans la pile comme une image '
      + 'déposée : posez-le pour caler le cadrage et la fenêtre d\'illustration, retirez-le '
      + 'd\'un clic. Sa vignette porte sa taille et son DPI comme les autres.</p>'
      /* ── ADOPTER UNE CARTE IMPORTEE (§7.1.5) ────────────────────────────
         DERIVE, jamais garde : le bloc n'existe QUE si `doc.capture` porte
         de quoi l'alimenter. Le libelle vient de `adoptionCapture` et dit
         LAQUELLE des deux sources sera prise. */
      + (adopt
        ? '<div class="cf-face-row"><button class="btn sm" type="button" id="cf-face-adopt">'
          + esc(adopt.libelle) + '</button></div>'
          + '<p class="hint">' + (adopt.sujet
            ? 'La pièce Import a isolé un sujet sur la carte reprise : il entre '
              + 'dans la pile comme une image déposée, et se pose aussitôt.'
            : 'Aucun sujet détouré pour l\'instant — c\'est le RECTO ENTIER qui '
              + 'entrera dans la pile, à recadrer ensuite avec la fenêtre '
              + 'd\'illustration. Pour n\'adopter que le sujet, détourez-le '
              + 'd\'abord depuis la pièce Import.') + '</p>'
        : '')
      + '<div class="cf-face-grid" id="cf-face-pile-grid"></div>'
      + '</div>'

      /* ── IA ── */
      + '<div class="cf-face-pane' + (tab === "ai" ? " on" : "") + '" id="cf-face-pane-ai">'
      + '<div class="fld"><span class="lbl">Amorces d\'invite — cadrage de carte</span>'
      + '<div class="chips cf-face-seeds" id="cf-face-seeds">'
      + PROMPT_SEEDS.map((s, i) => '<button class="chip" type="button" data-seed="' + i + '">' + esc(s[0]) + '</button>').join("")
      + '</div></div>'
      + '<div class="fld"><span class="lbl">Invite</span>'
      + '<textarea id="cf-face-prompt" placeholder="décrivez la face de la carte…">' + esc(f.prompt || "") + '</textarea></div>'
      + '<div class="grid2">'
      + '<div class="fld"><span class="lbl">Modèle</span><select id="cf-face-model"></select></div>'
      + '<div class="fld"><span class="lbl">Cadrage</span><select id="cf-face-size">'
      + AI_SIZES.map((s) => '<option value="' + s[0] + '"' + ((f.size || "portrait_4_3") === s[0] ? " selected" : "") + '>' + esc(s[1]) + '</option>').join("")
      + '</select></div>'
      + '<div class="fld"><span class="lbl">Nombre</span><input type="number" id="cf-face-n" min="1" max="4" step="1" value="' + (f.nimg || 1) + '"></div>'
      + '<div class="fld"><span class="lbl">Graine (vide = aléatoire)</span><input type="number" id="cf-face-seed" step="1" placeholder="—"></div>'
      + '</div>'
      + '<p class="hint cf-face-cost" id="cf-face-cost"></p>'
      + '<button class="btn primary wide" type="button" id="cf-face-gen">Générer et poser sur la carte</button>'
      + '<div id="cf-face-ai-out"></div>'
      + '</div>'

      /* ── placement ── */
      + '<div class="sep"></div>'
      + '<div class="cf-face-place">'
      + '<div class="cf-face-row"><span class="lbl">Ajustement</span>'
      + '<div class="seg sm cf-face-fit" id="cf-face-fit">'
      + '<button class="seg-b' + (f.fit === "cover" ? " active" : "") + '" type="button" data-fit="cover">Couvrir</button>'
      + '<button class="seg-b' + (f.fit === "contain" ? " active" : "") + '" type="button" data-fit="contain">Contenir</button>'
      + '<button class="seg-b' + (free ? " active" : "") + '" type="button" data-fit="free">Libre</button>'
      + '</div></div>'
      + '<div class="cf-face-row"><span class="lbl">Fenêtre d\'illustration</span>'
      + '<select id="cf-face-win">'
      + WIN_MODES.map((w) => '<option value="' + w[0] + '"'
        + ((f.win || "auto") === w[0] ? " selected" : "") + '>' + esc(w[1]) + '</option>').join("")
      + '</select></div>'
      + '<div class="cf-face-nums">'
      + '<label class="fld"><span class="lbl">X</span><input type="number" id="cf-face-x" step="0.5" value="' + fmt1(f.x) + '"><i>mm</i></label>'
      + '<label class="fld"><span class="lbl">Y</span><input type="number" id="cf-face-y" step="0.5" value="' + fmt1(f.y) + '"><i>mm</i></label>'
      + '<label class="fld"><span class="lbl">Échelle</span><input type="number" id="cf-face-scale" step="1" min="5" max="1200" value="' + Math.round(f.scale * 100) + '"><i>%</i></label>'
      /* Le verrou GRISE deja la hauteur (mesure : #cf-face-scaley.disabled ===
         true tant que lock). Ce qui manquait, c'est de DIRE laquelle commande
         l'autre : le libelle le dit maintenant, en toutes lettres. */
      + '<label class="fld"><span class="lbl">' + (f.lock === false ? "Hauteur" : "Hauteur = Échelle") + '</span>'
      + '<input type="number" id="cf-face-scaley" step="1" min="5" max="1200" value="'
      + Math.round((f.lock === false ? (f.scale_y || f.scale) : f.scale) * 100) + '"'
      + (f.lock === false ? "" : ' disabled title="verrou de proportions actif : la hauteur recopie l\'échelle"') + '><i>%</i></label>'
      + '<label class="fld"><span class="lbl">Rotation</span><input type="number" id="cf-face-rot" step="1" min="-180" max="180" value="' + fmt1(f.rot) + '"><i>°</i></label>'
      + '<label class="fld cf-face-lockf"><span class="lbl">Proportions</span>'
      + '<button class="btn sm wide" type="button" id="cf-face-lock">' + (f.lock === false ? "déverrouillées" : "verrouillées") + '</button></label>'
      + '</div>'
      + '<div class="btn-row cf-face-acts">'
      + '<button class="btn sm" type="button" id="cf-face-center">Recentrer</button>'
      + '<button class="btn sm" type="button" id="cf-face-fitwin" '
      + 'title="pose en « couvrir » au centre de la fenêtre d\'illustration">'
      + 'Recadrer sur la fenêtre</button>'
      + '<button class="btn sm" type="button" id="cf-face-reset">Réinitialiser</button>'
      + '<button class="btn sm" type="button" id="cf-face-undo">Annuler</button>'
      + '<button class="btn sm" type="button" id="cf-face-redo">Rétablir</button>'
      + '<button class="btn sm" type="button" id="cf-face-clear">Retirer</button>'
      + '</div>'
      + '<p class="hint cf-face-keys">Sur la carte : <b>glisser</b> = déplacer · <b>molette</b> = zoom sous le curseur · '
      + '<b>Alt+glisser</b> = rotation · <b>double-clic</b> = recentrer.<br>'
      + 'Au clavier : <b>flèches</b> 1 mm · <b>Maj+flèches</b> 0,1 mm · <b>+ / −</b> zoom · '
      + '<b>[ ]</b> rotation · <b>0</b> recentrer · <b>F</b> ajustement · <b>Ctrl+Z / Ctrl+Y</b>.</p>'
      + '<div id="cf-face-pals"></div>'
      + '<p class="hint mono cf-face-read" id="cf-face-read"></p>'
      + '</div>'

      /* ── le fichier livre ───────────────────────────────────────────────
         MESURE du duel : le PNG livre ne portait AUCUN chunk pHYs. Un fichier
         qui promet 300 DPI sans declarer sa resolution physique arrive a
         72 DPI dans Photoshop ou InDesign, soit 11,32 x 15,42 pouces au lieu
         de 69 x 94 mm. Ce bouton passe les octets du moteur (CF.cardBlob —
         personne ne redessine) par `POST face/png/<fmt>/<dpi>`, qui VERIFIE
         la taille de trame avant d'estampiller. Le chiffre affiche ensuite
         est RELU dans les octets rendus, pas celui qu'on a demande. */
      + '<div class="sep"></div>'
      + '<div class="cf-face-out">'
      + '<button class="btn sm wide" type="button" id="cf-face-fidbtn">Contrôle de fidélité de l\'illustration</button>'
      + '<p class="hint mono" id="cf-face-fid"></p>'
      + '<button class="btn strong wide" type="button" id="cf-face-png">Télécharger la face — PNG 1:1 avec sa résolution physique</button>'
      + '<p class="hint mono" id="cf-face-pngout">Le fichier emporte sa résolution physique '
      + '(<b>pHYs</b>), son espace de couleur (<b>sRGB</b>) et le nom de la carte. Sans eux, une '
      + 'mise en page ouvre le PNG à 72 DPI. À ' + g.dpi + ' DPI : ' + physLine(g.dpi) + '</p>'
      + '</div>';

    wirePanel();
    fillCatalog();
    fillPile();
    fillAI();
    fillPalettes();
    paintGauge();
    readout();
  }

  /* La recoloration, dite pour ce qu'elle est : le MEME dessin, une autre
     palette. Visible seulement quand la face vient du catalogue. */
  function fillPalettes() {
    const box = q("#cf-face-pals");
    if (!box) return;
    const cur = String(CF.get("face.src", "") || "");
    if (cur.indexOf("cat:") !== 0) { box.innerHTML = ""; return; }
    const raw = cur.slice(4);
    const m = /^face_([a-z]+)_([a-z]+)_([a-z]+)$/.exec(raw) || [];
    if (!m.length) { box.innerHTML = ""; return; }
    box.innerHTML = '<span class="lbl">Palette — le même dessin, ' + PALETTES.length + ' teintes</span>'
      + '<div class="chips cf-face-pal" id="cf-face-palrow">'
      + PALETTES.map((p) => '<button class="chip' + (p.id === m[1] ? " active" : "")
        + '" type="button" data-pal="' + esc(p.id) + '"><i style="background:'
        + esc(p.sky[1]) + ';border-color:' + esc(p.glow) + '"></i>' + esc(p.label) + '</button>').join("")
      + '</div>';
    const row = q("#cf-face-palrow");
    if (row) row.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-pal]");
      if (!b) return;
      const id = recolored(raw, b.dataset.pal);
      if (id) setArt("cat:" + id);
    });
  }

  /* ── le fichier livre : TOUT ce qui s'affiche ici est RELU dans les octets ─
     Les deux critiques ont releve la meme chose sur le fichier du duel : « ni
     iCCP, ni sRGB, ni gAMA : l'imprimeur recoit du RVB sans profil et devra
     deviner », « aucune metadonnee : rien dans l'octet ne dit de quelle carte
     il s'agit », « un canal alpha uniformement a 255 ». Les trois sont
     corriges par `POST face/png/<fmt>/<dpi>` et VERIFIES ici, apres coup, en
     relisant les chunks du blob rendu — jamais en recopiant ce qu'on a demande.

     Le bouton demande DEUX clics quand la jauge est rouge. La spec veut une
     alerte non bloquante, pas un mur ; mais « un controle qui informe sans
     jamais s'opposer laisse passer exactement la faute qu'il pretend
     surveiller » (le reproche, mot pour mot). Le second clic porte le chiffre
     reel : il ne se donne pas par distraction. */
  let ARMED = 0;
  const PNG_LABEL = "Télécharger la face — PNG 1:1 avec sa résolution physique";

  async function downloadPng() {
    const g = CF.geom();
    const out = q("#cf-face-pngout");
    const btn = q("#cf-face-png");
    /* LE GARDE-FOU SUIT LA JAUGE, PAS LE GENRE DE LA SOURCE. Il ne
       s'appliquait qu'aux bitmaps : une face vectorielle a 150 DPI passait
       sans un mot, alors que c'est le meme fichier sous-defini qui part chez
       l'imprimeur. Le seuil est celui de la jauge, et la jauge mesure
       desormais la trame livree dans les DEUX cas. */
    const rast = LAST.vector ? rasterDpi(g) : 0;
    const low = LAST.has && (LAST.vector
      ? rast + 1e-9 < DPI_TARGET
      : LAST.eff + 1e-9 < DPI_TARGET);
    if (low && Date.now() - ARMED > 8000) {
      const vu = LAST.vector ? rast : LAST.eff;
      ARMED = Date.now();
      if (btn) btn.textContent = "Confirmer l'export à " + Math.round(vu) + " DPI (sous " + DPI_TARGET + ")";
      if (out) {
        out.innerHTML = '<b>Rien n\'est parti.</b> L\'illustration sortirait à <b>'
          + Math.round(vu) + ' DPI</b>, sous les ' + DPI_TARGET + ' DPI d\'impression : '
          + (LAST.vector
            ? 'cette face est vectorielle, il n\'y a pas de source à agrandir — c\'est la '
              + '<b>toile</b> qui est à ' + g.dpi + ' DPI, et cela se règle dans la barre de format. '
            : 'il faudrait une source de <b>' + LAST.need + ' x ' + LAST.needH + ' px</b> à cette taille de pose. ')
          + 'Cliquez une seconde fois pour exporter quand même.';
      }
      CF.toast("export sous " + DPI_TARGET + " DPI : confirmez", true);
      return;
    }
    ARMED = 0;
    if (btn) btn.textContent = PNG_LABEL;
    CF.busy(true, "encodage de la carte à " + g.canvas_px[0] + " x " + g.canvas_px[1] + " px…");
    try {
      const raw = await CF.cardBlob(CF.current(), {});     /* LE moteur unique */
      const qs = "?title=" + encodeURIComponent(String(CF.doc().name || "").slice(0, 120))
        + "&card=" + encodeURIComponent(String(CF.current() + 1));
      const stamped = await M.api.blob("POST", "png/" + g.fmt + "/" + g.dpi + qs, raw);
      const a = await readPngFacts(stamped);               /* RELU sur les octets */
      const b = await readPngFacts(raw);
      CF.download(stamped, (CF.doc().name || "carte").replace(/[^\w\-]+/g, "_")
        + "_" + (CF.current() + 1) + "_" + g.dpi + "dpi.png");
      if (out) out.innerHTML = pngReport(a, b, raw.size, stamped.size);
      CF.toast("PNG livré : résolution, espace de couleur et métadonnées dans les octets");
    } catch (e) {
      const msg = String((e && e.message) || e);
      if (out) out.innerHTML = '<b>Échec</b> : ' + esc(msg);
      CF.toast("export PNG : " + msg, true);
    } finally { CF.busy(false); }
  }

  const COLOR_NAME = { 0: "gris", 2: "RVB", 3: "palette", 4: "gris+alpha", 6: "RVBA" };

  /* « IDAT IDAT IDAT … » 230 fois n'apprend rien : on compte les repetitions.
     L'inventaire reste EXACT, il devient lisible. */
  function runs(list) {
    const out = [];
    for (let i = 0; i < list.length;) {
      let j = i;
      while (j < list.length && list[j] === list[i]) j++;
      out.push(j - i > 1 ? list[i] + "x" + (j - i) : list[i]);
      i = j;
    }
    return out.join(" ");
  }

  function pngReport(a, b, nRaw, nOut) {
    const keys = Object.keys(a.texts);
    const alpha = (b.color === 6 && a.color === 2)
      ? ' · <b>canal alpha retiré</b> (le serveur a mesuré ses extrema à 255/255 avant de convertir, '
        + 'et vérifié que les trois canaux RVB survivent à l\'octet)'
      : (a.color === 6 ? ' · canal alpha <b>conservé</b> : il porte de l\'information' : '');
    return '<b>Fichier téléchargé.</b> En-tête relu dans les octets rendus :'
      /* « 8 bits » tout court a deja ete un badge faux ailleurs : on nomme
         l'octet d'ou vient le nombre et la grandeur qu'il mesure. */
      + '<br><b>' + a.w + ' x ' + a.h + ' px</b>, ' + a.depth
      + ' bits par canal (IHDR, octet 9), type ' + a.color
      + ' = <b>' + (COLOR_NAME[a.color] || "?") + '</b>'
      + (a.phys ? ' · <b>pHYs</b> ' + a.phys.x + ' x ' + a.phys.y + ' px/m (unité ' + a.phys.unit
        + ' = mètre) = <b>' + (a.phys.x * 0.0254).toFixed(4) + ' DPI</b>'
        : ' · <b>aucun pHYs</b> — le fichier n\'annonce aucune résolution physique')
      + (a.srgb === null ? ' · <b>aucun espace de couleur</b>'
        : ' · <b>sRGB</b> intention ' + a.srgb + (a.gama ? ' + gAMA ' + a.gama : '')
        + (a.chrm ? ' + cHRM' : ''))
      + alpha
      + '<br><span class="mono">chunks : ' + esc(runs(a.chunks)) + '</span>'
      + '<br>métadonnées relues : ' + (keys.length
        ? keys.map((k) => '<b>' + esc(k) + '</b> = ' + esc(a.texts[k])).join(' · ')
        : '<b>aucune</b>')
      + '<br>Avant écriture de l\'en-tête : ' + nRaw.toLocaleString("fr-FR")
      + ' octets, type ' + b.color + ' (' + (COLOR_NAME[b.color] || "?") + '), chunks '
      + esc(runs(b.chunks)) + '. Après : ' + nOut.toLocaleString("fr-FR") + ' octets ('
      + (nOut <= nRaw ? '−' : '+') + Math.abs(Math.round(100 - nOut * 100 / nRaw)) + ' %).';
  }

  /* Lecture des chunks PNG — miroir de cards/face.py:png_chunks / png_phys /
     png_srgb / png_texts. Ce qui s'affiche vient d'ICI. */
  async function readPngFacts(blob) {
    const b = new Uint8Array(await blob.arrayBuffer());
    const f = { chunks: [], phys: null, srgb: null, gama: 0, chrm: false, texts: {}, w: 0, h: 0, depth: 0, color: -1 };
    if (b.length < 8) return f;
    const dv = new DataView(b.buffer, b.byteOffset, b.byteLength);
    const utf8 = (typeof TextDecoder === "function") ? new TextDecoder("utf-8") : null;
    const lat1 = (typeof TextDecoder === "function") ? new TextDecoder("latin1") : null;
    let p = 8;
    while (p + 8 <= b.length) {
      const len = dv.getUint32(p);
      const typ = String.fromCharCode(b[p + 4], b[p + 5], b[p + 6], b[p + 7]);
      const at = p + 8;
      if (at + len > b.length) break;
      f.chunks.push(typ);
      if (typ === "IHDR" && len >= 13) {
        f.w = dv.getUint32(at); f.h = dv.getUint32(at + 4);
        f.depth = b[at + 8]; f.color = b[at + 9];
      } else if (typ === "pHYs" && len >= 9) {
        f.phys = { x: dv.getUint32(at), y: dv.getUint32(at + 4), unit: b[at + 8] };
      } else if (typ === "sRGB" && len >= 1) {
        f.srgb = b[at];
      } else if (typ === "gAMA" && len >= 4) {
        f.gama = dv.getUint32(at);
      } else if (typ === "cHRM") {
        f.chrm = true;
      } else if ((typ === "tEXt" || typ === "iTXt") && len > 1) {
        const seg = b.subarray(at, at + len);
        let z = 0;
        while (z < seg.length && seg[z] !== 0) z++;
        const key = lat1 ? lat1.decode(seg.subarray(0, z)) : "";
        if (typ === "tEXt") {
          f.texts[key] = lat1 ? lat1.decode(seg.subarray(z + 1)) : "";
        } else {
          /* iTXt : compression(1) methode(1) langue NUL traduit NUL puis UTF-8 */
          let r = z + 3, nul = 0;
          while (r < seg.length && nul < 2) { if (seg[r] === 0) nul++; r++; }
          f.texts[key] = utf8 ? utf8.decode(seg.subarray(r)) : "";
        }
      }
      if (typ === "IEND") break;
      p += 12 + len;
    }
    return f;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     LE CONTROLE DE FIDELITE — « est-ce bien MON illustration qui sort ? »

     MESURE QUI A IMPOSE CE BLOC. Un critique a compare, sur trois plages
     plates, l'illustration importee (17,13,26) et la carte livree (35,27,47),
     et a conclu que le produit retouchait l'image en douce. J'ai refait la
     mesure par le vrai chemin — depot d'un aplat 1024x1536, rendu par
     CF.renderCard — et la voici :
         source   0,0,0     -> livre   0,0,0
         source 255,255,255 -> livre 255,255,255
         source  17,13,26   -> livre  35,27,47      (exactement son chiffre)
         source 128,128,128 -> livre 152,151,149
     Ni 0 ni 255 ne bougent : ce n'est donc NI un voile opaque NI un gain
     lineaire. La courbe est celle de `soft-light`, qui laisse le noir et le
     blanc en place. Et `soft-light` est le reglage d'usine du GRAIN de la
     piece 06 (mod-texture.js:138 — `over:"grain", over_opacity:0.5,
     over_blend:"soft-light"`), peint a z=30, donc AU-DESSUS de la face (z=20,
     table gelee). Le painter de cette piece, lui, fait un `drawImage` nu :
     ni `filter`, ni `globalAlpha`, ni changement de composition.

     Un reproche fonde ne se refuse pas : il se MESURE ET S'AFFICHE. Ce bouton
     rend la face SEULE sur une toile a nous, la compare a la carte livree
     dans la fenetre d'illustration, et dit combien de pixels les couches du
     dessus modifient et de combien. L'ecran cesse d'etre muet sur une
     retouche que l'utilisateur n'avait pas demandee — et il nomme l'endroit
     ou l'eteindre.
     ═══════════════════════════════════════════════════════════════════════ */
  function newCanvas(w, h) {
    const cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    return cv;
  }
  function modalColors(data, n) {
    const m = new Map();
    for (let p = 0; p < data.length; p += 16) {           /* 1 pixel sur 4 */
      const k = (data[p] << 16) | (data[p + 1] << 8) | data[p + 2];
      m.set(k, (m.get(k) || 0) + 1);
    }
    const tot = Math.max(1, Math.floor(data.length / 16));
    return Array.from(m.entries()).sort((a, b) => b[1] - a[1]).slice(0, n)
      .map(([k, c]) => ({ rgb: [(k >> 16) & 255, (k >> 8) & 255, k & 255], pct: 100 * c / tot }));
  }
  function countColor(data, rgb, x0, y0, x1, y1, W) {
    let n = 0;
    for (let y = y0; y < y1; y++) {
      let p = (y * W + x0) * 4;
      for (let x = x0; x < x1; x++, p += 4) {
        if (data[p] === rgb[0] && data[p + 1] === rgb[1] && data[p + 2] === rgb[2]) n++;
      }
    }
    return n;
  }

  async function checkFidelity() {
    const el = q("#cf-face-fid");
    const btn = q("#cf-face-fidbtn");
    if (btn) btn.disabled = true;
    if (el) el.textContent = "mesure en cours…";
    try {
      const g = CF.geom();
      const doc = CF.doc();
      const cd = CF.card(CF.current());
      const W = g.canvas_px[0], H = g.canvas_px[1];
      const win = artWindow(g);
      const x0 = Math.max(0, Math.round(win[0])), y0 = Math.max(0, Math.round(win[1]));
      const x1 = Math.min(W, Math.round(win[0] + win[2])), y1 = Math.min(H, Math.round(win[1] + win[3]));

      /* (1) la face SEULE, par le painter de cette piece */
      const solo = newCanvas(W, H);
      const sctx = solo.getContext("2d", { willReadFrequently: true });
      PROBING = true;
      try { await paintFace(sctx, g, doc, cd, "front"); } finally { PROBING = false; }
      const A = sctx.getImageData(0, 0, W, H).data;

      /* (2) la carte livree, par le moteur unique */
      const full = await CF.renderCard(CF.current());
      const fctx = full.getContext("2d", { willReadFrequently: true });
      const B = fctx.getImageData(0, 0, W, H).data;

      /* (3) l'ecart, DANS la fenetre d'illustration seulement */
      let diff = 0, tot = 0, sum = 0, mx = 0, teinte = 0, couvert = 0;
      const hist = new Int32Array(256);
      for (let y = y0; y < y1; y++) {
        let p = (y * W + x0) * 4;
        for (let x = x0; x < x1; x++, p += 4) {
          tot++;
          const d = Math.max(Math.abs(A[p] - B[p]), Math.abs(A[p + 1] - B[p + 1]), Math.abs(A[p + 2] - B[p + 2]));
          if (d) { diff++; sum += d; if (d > mx) mx = d; }
          /* DEUX regimes, et il faut les separer : une FUSION (grain, voile,
             teinte) deplace le pixel de quelques niveaux ; un RECOUVREMENT
             (montant de cadre, cartouche de texte) le remplace. Les confondre
             sous « X % des pixels different » ne dit pas si l'illustration
             est retouchee ou simplement masquee par-dessus. Le seuil de 32
             niveaux est ecrit ici et affiche a l'ecran. */
          if (d > 0 && d <= FID_TINT) teinte++;
          else if (d > FID_TINT) couvert++;
          hist[d]++;
        }
      }
      /* La mediane se lit dans l'histogramme, et l'histogramme doit avoir ete
         REMPLI : une premiere redaction de ce bloc avait perdu le `hist[d]++`
         en le reecrivant, et l'ecran affichait « ecart median 0 » a cote de
         « 0,0 % inchanges » — deux chiffres qui ne peuvent pas etre vrais
         ensemble. Le desaccord est ici une assertion, pas un commentaire. */
      let acc = 0, med = 0;
      for (let i = 0; i < 256; i++) { acc += hist[i]; if (acc >= tot / 2) { med = i; break; } }
      if (acc < tot / 2) med = -1;      /* histogramme vide : on ne PREND PAS 0 */

      /* (4) les plages plates de la SOURCE, retrouvees (ou non) des deux cotes */
      let plages = "";
      let src = null;
      try { src = await artSource(resolveArtId(doc, cd, "front")); } catch (e) { src = null; }
      if (src && src.kind === "bitmap") {
        const sc = newCanvas(src.w, src.h);
        const sx = sc.getContext("2d", { willReadFrequently: true });
        sx.drawImage(src.img, 0, 0);
        const S = sx.getImageData(0, 0, src.w, src.h).data;
        const tops = modalColors(S, 3).filter((c) => c.pct >= 0.2);
        plages = tops.map((c) => {
          const a = countColor(A, c.rgb, x0, y0, x1, y1, W);
          const b = countColor(B, c.rgb, x0, y0, x1, y1, W);
          return '(' + c.rgb.join(",") + ') ' + c.pct.toFixed(1) + ' % de la source → <b>'
            + a.toLocaleString("fr-FR") + '</b> px après la pose, <b>' + b.toLocaleString("fr-FR")
            + '</b> px dans la carte livrée';
        }).join(" · ");
      }

      /* Qui peint AU-DESSUS de la face ? La table des z du CORE le dit, on ne
         l'ecrit pas a la main : { 10:"texture", 20:"face", 30:"texture", … } */
      const zs = [];
      try {
        const T = CF.Z_TABLE || {};
        Object.keys(T).forEach((z) => {
          const n = Number(z);
          if (n > 20 && n < 90) zs.push(T[z] + " z=" + n);
        });
      } catch (e) { /* table indisponible */ }

      /* LE REGLAGE, LU DANS LE DOCUMENT — pas devine, pas nomme au hasard.
         « Rien dans l'interface n'annonce cette retouche NI NE PERMET DE
         L'ETEINDRE » : la seconde moitie du reproche demande une adresse, et
         une adresse n'est utile que si elle est exacte. La couche qui TEINTE
         (par opposition a celle qui recouvre) est le voile de la piece 06 ;
         ses trois reglages sont publies dans le document, on les RELIT et on
         les recopie tels quels. Lecture seule, absence toleree (spec 2.3) :
         si la piece 06 n'est pas chargee, on n'ecrit pas la phrase. */
      let voile = "";
      try {
        const ov = CF.get("texture.over", null);
        if (ov && ov !== "none") {
          const op = Number(CF.get("texture.over_opacity", 0));
          const bl = String(CF.get("texture.over_blend", "") || "normal");
          if (op > 0) {
            voile = 'Le voile de <b>Matières</b> est actif : motif « ' + esc(String(ov))
              + ' », opacité <b>' + Math.round(op * 100) + ' %</b>, fusion <b>' + esc(bl)
              + '</b> — c\'est lui qui teinte, et il s\'éteint dans ce panneau-là. ';
          }
        }
      } catch (e) { /* piece 06 absente : on ne dit rien plutot que d'inventer */ }

      /* CE QUE LA MESURE PEUT DIRE DEPEND DE CE QU'IL Y A A MESURER. Sans
         illustration il n'y a rien a controler ; sur une face VECTORIELLE il
         n'existe aucun octet source a retrouver — elle est REDESSINEE. On ne
         garde donc la phrase « la pose conserve les plages de la source » que
         quand les chiffres qui la prouvent sont affiches juste a cote. */
      if (el && !src) {
        el.innerHTML = '<b>Aucune illustration posée</b> — rien à contrôler. '
          + 'Posez une face du catalogue ou déposez une image, puis relancez.';
      } else if (el) {
        const preuve = plages ? 'Plages plates de la source : ' + plages + '. ' : '';
        /* CE QUI A CHANGE, ET POURQUOI. La redaction precedente concluait
           « au premier rang desquelles le grain de Matieres ». C'etait une
           ATTRIBUTION, pas une mesure : ce controle ne peut pas isoler une
           couche, il ne voit que la face seule et la carte entiere. Sur une
           carte a cadre plein, la mesure a donne 100 % de pixels differents,
           mediane 83, maximum 255 — un grain soft-light a 50 % ne fait pas
           cela, un montant de cadre opaque si. On dit donc ce qu'on mesure :
           combien de pixels sont TEINTES, combien sont RECOUVERTS, et quelles
           couches passent au-dessus d'apres la table des z. Nommer un coupable
           qu'on n'a pas pese est exactement ce que ce controle reproche aux
           autres. */
        const ici = plages
          ? 'La pose conserve les plages de la source au pixel (colonne « après la pose » '
            + 'ci-dessus) : la mise en place de l\'illustration ne change aucune couleur. '
          : 'Cette face est <b>vectorielle</b> : elle est redessinée à la taille de la pose, il n\'y '
            + 'a aucun octet source à retrouver. Déposez une image importée et relancez : '
            + 'le contrôle retrouvera alors ses plages plates de couleur des deux côtés. ';
        el.innerHTML = diff === 0
          ? preuve + '<b>Fidèle à l\'octet</b> : sur les ' + tot.toLocaleString("fr-FR")
            + ' pixels de la fenêtre d\'illustration, <b>aucun</b> n\'est modifié entre la face '
            + 'posée et la carte livrée.'
          : preuve
            + 'Sur les ' + tot.toLocaleString("fr-FR") + ' pixels de la fenêtre d\'illustration : '
            + '<b>' + (100 * (tot - diff) / tot).toFixed(1) + ' % inchangés</b>, '
            + '<b>' + (100 * teinte / tot).toFixed(1) + ' % teintés</b> (écart de 1 à ' + FID_TINT
            + ' niveaux — une fusion) et <b>' + (100 * couvert / tot).toFixed(1) + ' % recouverts</b> '
            + '(écart > ' + FID_TINT + ' — quelque chose d\'opaque est passé par-dessus). '
            + (med < 0 ? 'Médiane indisponible. ' : 'Écart médian ' + med + ', ')
            + 'maximum ' + mx + ' niveaux. '
            + ici
            + 'Ce qui passe AU-DESSUS de la face, d\'après la table des z du moteur : <b>'
            + esc(zs.join(", ")) + '</b>. ' + voile
            + 'Ce contrôle ne pèse pas ces couches une par une : il mesure leur effet total, '
            + 'et chacune se règle dans son propre panneau.';
      }
    } catch (e) {
      if (el) el.textContent = "le contrôle a échoué : " + String((e && e.message) || e);
    } finally {
      if (btn) btn.disabled = false;
    }
  }


  function readout() {
    const el = q("#cf-face-read");
    if (!el) return;
    const g = CF.geom(), f = CF.doc().face;
    const w = artWindow(g);
    /* « 67 % de la toile » : de la SURFACE, pas du cote. Les deux se disent
       « % de la toile » et ne donnent pas le meme nombre (673x897 fait 67 % de
       la surface mais 83 % de la largeur) — on nomme donc la grandeur. */
    const pct = Math.round(w[2] * w[3] / (g.canvas_px[0] * g.canvas_px[1]) * 100);
    /* « Le libelle du selecteur decrit une fenetre qui n'est pas celle sur
       laquelle le DPI est calcule » : le reproche visait « Auto — celle du
       cadre » affiche pendant que le pied de panneau mesurait la toile
       ENTIERE. Les deux disaient vrai separement, aucun des deux ne disait
       ce qui s'etait passe. On ecrit donc ce que « auto » a RESOLU. */
    const mode = String(CF.get("face.win", "auto") || "auto");
    const lbl = (WIN_MODES.filter((m) => m[0] === mode)[0] || WIN_MODES[0])[1];
    const resolu = mode !== "auto" ? lbl
      : (frameWindow(g) ? "Auto → fenêtre publiée par le cadre"
        : "Auto → toile entière (le cadre n'en publie aucune)");
    /* Le nom de la source, pas sa clef de rangement. « source
       local:fmspgoglyz9l7i » a ete releve tel quel dans un duel : un jeton
       interne n'apprend rien a l'utilisateur et sort du logiciel avec la
       capture. Le fichier a un nom, le dessin a un titre : on les affiche. */
    const src = LAST.has && LAST.label ? LAST.label : (f.src ? "posée" : "aucune");
    el.textContent = resolu
      + " · fenêtre " + Math.round(w[2]) + " x " + Math.round(w[3]) + " px"
      + " (" + fmt1(g.px2mm(w[2])) + " x " + fmt1(g.px2mm(w[3])) + " mm, " + pct
      + " % de la SURFACE de la toile)"
      + " · origine " + fmt1(w[0]) + " / " + fmt1(w[1]) + " px"
      + " · décalage " + fmt1(g.mm2px(f.x)) + " / " + fmt1(g.mm2px(f.y)) + " px"
      + " · illustration : " + src;
  }

  /* ── LE COUT, EN MONNAIE ────────────────────────────────────────────────
     REPROCHE, MOT POUR MOT : « la spec exige une face generee en un seul
     appel, avec le choix du modele expose ET LE COUT AFFICHE. Pas un modele,
     PAS UN PRIX. » L'ecran disait « 1 image facturee » : c'est un COMPTE, pas
     un cout. Et un montant ecrit en dur dans ce fichier serait precisement le
     chiffre invérifiable que ce tour interdit. Il est donc lu par
     `GET ai-models` dans la TABLE DE TARIFS DE L'APPLICATION — celle qui
     alimente le compteur de depense de tout le logiciel et que l'utilisateur
     edite dans Reglages. Un modele absent de cette table n'affiche AUCUN
     montant : `pricing.estimate` retomberait en silence sur le tarif de FLUX,
     et un prix de repli presente comme celui du modele choisi serait faux. */
  function usdFmt(v) {
    let s = (Math.round(v * 10000) / 10000).toFixed(4);
    if (s.indexOf(".") >= 0) s = s.replace(/0+$/, "").replace(/\.$/, "");
    return s.replace(".", ",") + " $";
  }
  function costLine() {
    const el = q("#cf-face-cost");
    if (!el) return;
    const sel = q("#cf-face-model");
    const id = sel ? sel.value : "";
    const m = MODELS.filter((x) => x.id === id)[0];
    const n = Math.max(1, Math.min(4, Number((q("#cf-face-n") || {}).value) || 1));
    if (!MODELS.length) {
      el.innerHTML = '<b>Aucun modèle d\'image disponible</b> — aucune clé FAL ni OpenAI '
        + 'n\'est enregistrée dans les Réglages de l\'application, la génération échouerait. '
        + 'Le catalogue vectoriel et l\'import, eux, ne demandent aucune clé.';
      return;
    }
    const u = m && typeof m.usd_par_image === "number" ? m.usd_par_image : null;
    const qui = '<b>' + esc((m && m.provider) || "?") + '</b> — ' + esc((m && m.label) || id)
      + (m && m.note ? ' (' + esc(m.note) + ')' : '');
    el.innerHTML = (u === null
      ? 'Coût de ce clic : <b>' + n + ' image' + (n > 1 ? 's' : '') + '</b> chez ' + qui
        + '. <b>Tarif non tabulé</b> dans l\'application : aucun montant n\'est affiché ici, '
        + 'plutôt qu\'un montant emprunté à un autre modèle.'
      : 'Coût de ce clic : <b>' + n + ' × ' + usdFmt(u) + ' = ' + usdFmt(n * u) + '</b> chez ' + qui
        + '. Tarif lu dans ' + esc(AI_META.tarif_source || "la table de tarifs de l'application")
        + '.')
      + ' C\'est la seule action de cet écran qui dépense.';
  }

  /* ── cablage ──────────────────────────────────────────────────────────── */
  function num(id) { const e = q(id); return e ? Number(e.value) : NaN; }

  function wirePanel() {
    q("#cf-face-tabs").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-tab]");
      if (b) { M.patch({ tab: b.dataset.tab }); renderPanel(); }
    });
    const warn = q("#cf-face-warn");
    warn.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-fix]");
      if (!b) return;
      if (b.dataset.fix === "shrink") fixShrink();
      else { pushUndo(); M.patch({ fit: "contain" }); renderPanel(); }
    });

    /* catalogue */
    q("#cf-face-search").addEventListener("input", (e) => { CATFILTER = e.target.value; fillCatalog(); });
    q("#cf-face-subject").addEventListener("change", (e) => { CATTAG = e.target.value; fillCatalog(); });
    q("#cf-face-proof").addEventListener("click", proveCatalog);
    q("#cf-face-compos").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-compo]");
      if (!b) return;
      CATCOMPO = b.dataset.compo;
      Array.prototype.forEach.call(q("#cf-face-compos").children, (c) => c.classList.toggle("active", c.dataset.compo === CATCOMPO));
      fillCatalog();
    });
    q("#cf-face-rand").addEventListener("click", () => {
      const rows = catalogRows();
      if (!rows.length) return;
      setArt("cat:" + rows[Math.floor(Math.random() * rows.length)].id);
    });
    q("#cf-face-cat-grid").addEventListener("click", (e) => {
      const b = e.target.closest("[data-cat]");
      if (!b) return;
      /* Une case PEINTE pose son fichier ; une case sans image pose le
         dessin. C'est la retombee, cote geste. */
      const f = b.getAttribute("data-ai");
      if (f) setArt("img:" + f); else setArt("cat:" + b.getAttribute("data-cat"));
    });
    /* LE SELECTEUR DE VOIE. Il ecrit dans le DOCUMENT (la voie voyage avec le
       jeu) puis relit l'etat de la serie : le compte affiche est celui du
       manifeste au moment du clic, pas celui du chargement de la page. */
    q("#cf-face-series").addEventListener("click", async (e) => {
      const b = e.target.closest("[data-voie]");
      if (!b) return;
      const voie = b.getAttribute("data-voie");
      if (voie === (serieActive() || "vectoriel")) return;
      M.patch({ serie: voie });
      if (voie !== "vectoriel") await serieLoad();
      renderPanel();
    });

    /* importees */
    const drop = q("#cf-face-drop"), file = q("#cf-face-file");
    drop.addEventListener("click", (e) => { if (e.target !== file) file.click(); });
    file.addEventListener("change", async () => {
      const a = await importFiles(file.files);
      file.value = "";
      afterImport(a);
    });
    ["dragenter", "dragover"].forEach((n) => drop.addEventListener(n, (e) => { e.preventDefault(); drop.classList.add("over"); }));
    ["dragleave", "drop"].forEach((n) => drop.addEventListener(n, () => drop.classList.remove("over")));
    q("#cf-face-mire").addEventListener("click", importMire);
    /* Le bouton d'adoption N'EXISTE PAS quand il n'y a rien a adopter : on
       ne cable que ce qui est la (patron sectionsBasses). */
    const adopt = q("#cf-face-adopt");
    if (adopt) adopt.addEventListener("click", adopterCapture);
    drop.addEventListener("drop", async (e) => {
      e.preventDefault();
      const a = await importFiles(e.dataTransfer && e.dataTransfer.files);
      afterImport(a);
    });
    q("#cf-face-pile-grid").addEventListener("click", async (e) => {
      const d = e.target.closest("[data-del]");
      if (d) {
        e.stopPropagation();
        const k = d.getAttribute("data-del");
        await pileDel(k);
        if (CF.get("face.src", "") === "local:" + k) M.patch({ src: null, default_art: null });
        renderPanel();
        return;
      }
      const b = e.target.closest("[data-imp]");
      if (b) setArt("local:" + b.getAttribute("data-imp"));
    });

    /* IA */
    const msel = q("#cf-face-model");
    msel.innerHTML = MODELS.length
      ? MODELS.map((m) => '<option value="' + esc(m.id) + '">' + esc(m.label)
        + (typeof m.usd_par_image === "number" ? " — " + usdFmt(m.usd_par_image) + "/image"
          : " — tarif non tabulé") + '</option>').join("")
      : '<option value="">aucun modèle disponible</option>';
    const want = CF.get("face.model", "");
    if (want && MODELS.some((m) => m.id === want)) msel.value = want;
    msel.addEventListener("change", () => { M.patch({ model: msel.value }); costLine(); });
    q("#cf-face-n").addEventListener("input", costLine);
    q("#cf-face-seeds").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-seed]");
      if (!b) return;
      const s = PROMPT_SEEDS[Number(b.dataset.seed)];
      const ta = q("#cf-face-prompt");
      ta.value = s[1];
      ta.focus();
      M.patch({ prompt: ta.value });
    });
    q("#cf-face-prompt").addEventListener("change", (e) => M.patch({ prompt: String(e.target.value || "").slice(0, 900) }));
    q("#cf-face-gen").addEventListener("click", generate);
    q("#cf-face-ai-out").addEventListener("click", (e) => {
      const b = e.target.closest("[data-ai]");
      if (b) setArt("img:" + b.getAttribute("data-ai"));
    });
    costLine();

    /* placement */
    q("#cf-face-fit").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-fit]");
      if (!b) return;
      pushUndo();
      M.patch({ fit: b.dataset.fit });
      renderPanel();
    });
    const bind = (sel, key, conv, lo, hi) => {
      const el = q(sel);
      if (!el) return;
      let armed = false;
      el.addEventListener("focus", () => { armed = false; });
      el.addEventListener("change", () => {
        if (!armed) { pushUndo(); armed = true; }
        const v = clampNum(conv(Number(el.value)), lo, hi, 0);
        const p = {};
        p[key] = v;
        if (key === "scale" && CF.get("face.lock", true) !== false) p.scale_y = v;
        M.patch(p);
        renderPanel();
      });
    };
    bind("#cf-face-x", "x", (v) => v, -400, 400);
    bind("#cf-face-y", "y", (v) => v, -400, 400);
    bind("#cf-face-scale", "scale", (v) => v / 100, SCALE_MIN, SCALE_MAX);
    bind("#cf-face-scaley", "scale_y", (v) => v / 100, SCALE_MIN, SCALE_MAX);
    bind("#cf-face-rot", "rot", (v) => v, -180, 180);
    q("#cf-face-lock").addEventListener("click", () => {
      const now = CF.get("face.lock", true) !== false;
      pushUndo();
      M.patch(now ? { lock: false, scale_y: CF.get("face.scale", 1) } : { lock: true, scale_y: CF.get("face.scale", 1) });
      renderPanel();
    });
    q("#cf-face-center").addEventListener("click", () => { pushUndo(); M.patch({ x: 0, y: 0 }); renderPanel(); });
    q("#cf-face-fitwin").addEventListener("click", fixWindow);
    /* la jauge repeint son HTML a chaque mesure : le clic est delegue au
       conteneur, qui survit aux repeintures. */
    q("#cf-face-gauge").addEventListener("click", (e) => {
      const b = e.target.closest('button[data-fix="window"]');
      if (b) fixWindow();
    });
    q("#cf-face-reset").addEventListener("click", () => {
      pushUndo();
      M.patch({ x: 0, y: 0, scale: 1, scale_y: 1, rot: 0, fit: "cover", lock: true });
      renderPanel();
    });
    q("#cf-face-undo").addEventListener("click", undo);
    q("#cf-face-redo").addEventListener("click", redo);
    q("#cf-face-clear").addEventListener("click", () => {
      pushUndo();
      M.patch({ src: null, default_art: null });
      renderPanel();
    });
    q("#cf-face-win").addEventListener("change", (e) => {
      pushUndo();
      M.patch({ win: String(e.target.value || "auto") });
      renderPanel();
    });
    q("#cf-face-png").addEventListener("click", downloadPng);
    q("#cf-face-fidbtn").addEventListener("click", checkFidelity);
  }

  async function generate() {
    const ta = q("#cf-face-prompt");
    const prompt = String((ta && ta.value) || "").trim();
    if (!prompt) { CF.toast("écrivez une invite (ou cliquez une amorce)", true); if (ta) ta.focus(); return; }
    const model = (q("#cf-face-model") || {}).value || "";
    const size = (q("#cf-face-size") || {}).value || "portrait_4_3";
    const n = Math.max(1, Math.min(4, Number((q("#cf-face-n") || {}).value) || 1));
    const sd = Number((q("#cf-face-seed") || {}).value);
    const req = { prompt: prompt, n: n, size: size };
    if (model) req.model = model;
    if (isFinite(sd) && String((q("#cf-face-seed") || {}).value).trim() !== "") req.seed = sd;
    CF.busy(true, "génération de l'illustration…");
    try {
      const d = await CF.images.generate(req);          /* UN SEUL appel */
      const files = (d && d.images) || [];
      if (!files.length) throw new Error("le fournisseur n'a rendu aucune image");
      AI_OUT = files.slice();
      M.patch({ prompt: prompt, model: model, size: size, nimg: n });
      setArt("img:" + files[0], true);                  /* posee, sans copier-coller */
      /* Ce qui vient d'etre depense, dit APRES coup et avec le meme tarif que
         celui annonce avant le clic. Un ecran qui chiffre avant et se tait
         apres laisse l'utilisateur sans trace de sa depense. */
      const mm = MODELS.filter((x) => x.id === (model || (d && d.model)))[0];
      const u = mm && typeof mm.usd_par_image === "number" ? mm.usd_par_image : null;
      CF.toast(files.length + " image(s) générée(s) — la première est posée sur la carte"
        + (u === null ? "" : " · " + usdFmt(files.length * u) + " facturés chez " + mm.provider));
    } catch (e) {
      CF.toast("génération : " + String((e && e.message) || e), true);
    } finally { CF.busy(false); }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     8. LA CARTE ELLE-MEME : glisser, molette, Alt+glisser
     ═══════════════════════════════════════════════════════════════════════ */
  function panelActive() {
    const p = document.querySelector('.cf-panel[data-mod="face"]');
    return !!(p && p.classList.contains("on"));
  }
  function prevScale(cv) {
    const g = CF.geom();
    const w = cv.clientWidth || cv.width;
    return w > 0 ? w / g.canvas_px[0] : 1;
  }

  function wireStage() {
    const cv = document.querySelector("#stageCanvas");
    const wrap = document.querySelector("#stageWrap");
    if (!cv || !wrap) return;
    /* touch-action: none EN JS, pas en CSS : #stageCanvas est la scene
       PARTAGEE (cardforge.css, hors de mod-face.css), et la regle 4 du lint
       (scripts/qa/lint_cardforge.py) interdit tout selecteur de mod-face.css
       qui ne porte pas .cf-face — un `#stageCanvas { touch-action: none }`
       la-bas serait rejete au build. C'est aussi la seule piece qui glisse
       DIRECTEMENT sur cette toile (P2 a sa propre mini-carte, P3 son calque
       flottant) : la portee reste correcte cote comportement. */
    cv.style.touchAction = "none";
    let drag = null, pendingPatch = null, rafId = 0;
    /* repli setTimeout si rAF est absent, annulation SYMETRIQUE (le meme
       drapeau sert a programmer et a annuler — cancelAnimationFrame sur un
       identifiant de setTimeout ne fait rien, autre registre). Meme patron
       que core.js:158, reproduit ICI en local (fichiers separes, sans
       import partage entre pieces). */
    const hasRAF = typeof requestAnimationFrame === "function";
    const scheduleFrame = (fn) => (hasRAF ? requestAnimationFrame(fn) : setTimeout(fn, 16));
    const cancelFrame = (id) => { if (hasRAF) cancelAnimationFrame(id); else clearTimeout(id); };
    const flushDrag = () => {
      rafId = 0;
      if (!pendingPatch) return;
      const p = pendingPatch; pendingPatch = null;
      M.patch(p);                      /* <= 1 patch par frame (spec 9.6-1) */
    };

    cv.addEventListener("pointerdown", (e) => {
      if (!panelActive() || !LAST.has) return;
      const f = CF.doc().face;
      drag = {
        x0: e.clientX, y0: e.clientY, alt: e.altKey,
        fx: f.x, fy: f.y, rot: f.rot,
        cx: cv.getBoundingClientRect().left + cv.clientWidth / 2,
        cy: cv.getBoundingClientRect().top + cv.clientHeight / 2,
        moved: false,
      };
      drag.a0 = Math.atan2(e.clientY - drag.cy, e.clientX - drag.cx);
      try { cv.setPointerCapture(e.pointerId); } catch (err) { /* vieux moteur */ }
      e.preventDefault();
    });
    cv.addEventListener("pointermove", (e) => {
      if (!drag) return;
      const g = CF.geom(), s = prevScale(cv);
      let p;
      if (drag.alt) {
        const a = Math.atan2(e.clientY - drag.cy, e.clientX - drag.cx);
        let deg = drag.rot + (a - drag.a0) * 180 / Math.PI;
        deg = ((deg + 180) % 360 + 360) % 360 - 180;
        if (!drag.moved) { pushUndo(); drag.moved = true; }
        p = { rot: Math.round(deg * 10) / 10 };
      } else {
        const dx = g.px2mm((e.clientX - drag.x0) / s), dy = g.px2mm((e.clientY - drag.y0) / s);
        if (!drag.moved && Math.abs(e.clientX - drag.x0) + Math.abs(e.clientY - drag.y0) > 2) { pushUndo(); drag.moved = true; }
        p = { x: Math.round((drag.fx + dx) * 100) / 100, y: Math.round((drag.fy + dy) * 100) / 100 };
      }
      /* pas de mini-carte ici : la scene EST l'apercu, il n'y a pas de proxy
         moins cher a redessiner a part — coalescer le patch suffit, le
         repaint du canevas est deja lisse au rAF (core.js:889). */
      pendingPatch = p;
      if (!rafId) rafId = scheduleFrame(flushDrag);
    });
    const end = (e) => {
      if (!drag) return;
      drag = null;
      if (rafId) { cancelFrame(rafId); rafId = 0; }
      if (pendingPatch) { M.patch(pendingPatch); pendingPatch = null; }
      syncInputs();
      try { cv.releasePointerCapture(e.pointerId); } catch (err) { /* deja relache */ }
    };
    cv.addEventListener("pointerup", end);
    cv.addEventListener("pointercancel", end);
    cv.addEventListener("dblclick", () => {
      if (!panelActive()) return;
      pushUndo();
      M.patch({ x: 0, y: 0 });
      syncInputs();
    });

    /* molette : residu (1) de la revue 7bis, ROUVERT — molettes haute
       resolution et flings de trackpad livrent PLUSIEURS evenements par
       frame, chacun payait un patch complet. Le geste est INCREMENTAL
       (chaque cran compose echelle ET point vise a partir de l'etat
       courant) : le coalescer exige l'accumulateur local annonce par la
       revue — wheelPending EST l'etat courant tant que la frame n'a pas
       ecrit le document, et sert de base au cran suivant. La composition
       reste identique a la version un-patch-par-cran : le doc rendait
       exactement ce que le patch venait d'y poser (x/y arrondis au centieme
       AVANT ecriture, scale non arrondi), l'invariant point-sous-curseur
       (deja repare une fois) ne bouge pas. */
    let wheelPending = null, wheelRafId = 0;
    const flushWheel = () => {
      wheelRafId = 0;
      if (!wheelPending) return;
      const p = wheelPending; wheelPending = null;
      M.patch(p);                    /* <= 1 patch par frame (spec 9.6-1) */
    };
    cv.addEventListener("wheel", (e) => {
      if (!panelActive() || !LAST.has) return;
      e.preventDefault();
      const g = CF.geom(), f = CF.doc().face;
      const s = prevScale(cv);
      const r = cv.getBoundingClientRect();
      /* zoom SOUS LE CURSEUR : le point vise ne bouge pas. Le repere est le
         CENTRE DE LA FENETRE d'illustration — le meme que celui du painter
         (`ctx.translate(bx + bw/2 + ox, ...)`). Il valait `canvas_px / 2` :
         exact tant que la fenetre « auto » retombait sur la toile entiere,
         faux au premier cadre qui publie la sienne — le point sous le curseur
         aurait derive a chaque cran de molette. */
      const win = artWindow(g);
      const px = ((e.clientX - r.left) / s) - (win[0] + win[2] / 2);
      const py = ((e.clientY - r.top) / s) - (win[1] + win[3] / 2);
      const base = wheelPending || f;   /* le cran precedent, meme pas encore ecrit */
      const old = clampNum(base.scale, SCALE_MIN, SCALE_MAX, 1);
      const k = Math.exp(-e.deltaY * 0.0016);
      const ns = clampNum(old * k, SCALE_MIN, SCALE_MAX, old);
      const ox = g.mm2px(base.x), oy = g.mm2px(base.y);
      const nx = px - (px - ox) * (ns / old), ny = py - (py - oy) * (ns / old);
      if (!wheelArmed) { pushUndo(); wheelArmed = true; }
      clearTimeout(wheelTimer);
      wheelTimer = setTimeout(() => {
        /* clot la rafale comme pointerup clot le glisser : etat FINAL exact
           pousse AVANT de desarmer le groupe d'annulation (spec 9.6-1 /
           9.6-4) — puis les champs relisent le document a jour. */
        if (wheelRafId) cancelFrame(wheelRafId);
        flushWheel();
        wheelArmed = false;
        syncInputs();
      }, 420);
      const p = { scale: ns, x: Math.round(g.px2mm(nx) * 100) / 100, y: Math.round(g.px2mm(ny) * 100) / 100 };
      if (CF.get("face.lock", true) !== false) p.scale_y = ns;
      wheelPending = p;
      if (!wheelRafId) wheelRafId = scheduleFrame(flushWheel);
    }, { passive: false });

    ["dragenter", "dragover"].forEach((n) => wrap.addEventListener(n, (e) => {
      if (!panelActive()) return;
      e.preventDefault();
      wrap.classList.add("cf-face-over");
    }));
    wrap.addEventListener("dragleave", () => wrap.classList.remove("cf-face-over"));
    wrap.addEventListener("drop", async (e) => {
      if (!panelActive()) return;
      e.preventDefault();
      wrap.classList.remove("cf-face-over");
      const a = await importFiles(e.dataTransfer && e.dataTransfer.files);
      afterImport(a, "déposée(s) sur la carte");
    });
  }
  let wheelArmed = false, wheelTimer = null;

  function syncInputs() {
    const f = CF.doc().face;
    const set = (sel, v) => { const e = q(sel); if (e && document.activeElement !== e) e.value = v; };
    set("#cf-face-x", fmt1(f.x));
    set("#cf-face-y", fmt1(f.y));
    set("#cf-face-scale", Math.round(f.scale * 100));
    set("#cf-face-scaley", Math.round((f.lock === false ? (f.scale_y || f.scale) : f.scale) * 100));
    set("#cf-face-rot", fmt1(f.rot));
    readout();
  }

  function wireKeys() {
    document.addEventListener("keydown", (e) => {
      if (!panelActive()) return;
      const t = e.target;
      const typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable);
      if ((e.ctrlKey || e.metaKey) && (e.key === "z" || e.key === "Z")) { e.preventDefault(); e.shiftKey ? redo() : undo(); syncInputs(); return; }
      if ((e.ctrlKey || e.metaKey) && (e.key === "y" || e.key === "Y")) { e.preventDefault(); redo(); syncInputs(); return; }
      if (typing || e.ctrlKey || e.metaKey || e.altKey) return;
      const f = CF.doc().face;
      const step = e.shiftKey ? 0.1 : 1;
      const p = {};
      if (e.key === "ArrowLeft") p.x = Math.round((f.x - step) * 100) / 100;
      else if (e.key === "ArrowRight") p.x = Math.round((f.x + step) * 100) / 100;
      else if (e.key === "ArrowUp") p.y = Math.round((f.y - step) * 100) / 100;
      else if (e.key === "ArrowDown") p.y = Math.round((f.y + step) * 100) / 100;
      else if (e.key === "+" || e.key === "=") { p.scale = clampNum(f.scale * 1.02, SCALE_MIN, SCALE_MAX, f.scale); if (f.lock !== false) p.scale_y = p.scale; }
      else if (e.key === "-" || e.key === "_") { p.scale = clampNum(f.scale / 1.02, SCALE_MIN, SCALE_MAX, f.scale); if (f.lock !== false) p.scale_y = p.scale; }
      else if (e.key === "[") p.rot = Math.round((f.rot - 1) * 10) / 10;
      else if (e.key === "]") p.rot = Math.round((f.rot + 1) * 10) / 10;
      else if (e.key === "0") { p.x = 0; p.y = 0; }
      else if (e.key === "f" || e.key === "F") p.fit = FIT_MODES[(FIT_MODES.indexOf(f.fit) + 1) % FIT_MODES.length];
      else return;
      e.preventDefault();
      if (!keyArmed) { pushUndo(); keyArmed = true; }
      clearTimeout(keyTimer);
      keyTimer = setTimeout(() => { keyArmed = false; }, 600);
      M.patch(p);
      if (p.fit) renderPanel(); else syncInputs();
    });
    document.addEventListener("paste", async (e) => {
      if (!panelActive()) return;
      const items = (e.clipboardData && e.clipboardData.items) || [];
      const files = [];
      for (let i = 0; i < items.length; i++) {
        if (items[i].kind === "file") { const f = items[i].getAsFile(); if (f && /^image\//.test(f.type || "")) files.push(f); }
      }
      if (!files.length) return;
      e.preventDefault();
      const a = await importFiles(files);
      afterImport(a, "collée(s)");
    });
  }
  let keyArmed = false, keyTimer = null;

  /* amorces d'invite — miroir de cards/face.py:PROMPT_SEEDS */
  const _FR = "cadrage vertical de carte à jouer, sujet centré, marge sur les bords pour le fond perdu";
  const PROMPT_SEEDS = [
    ["Créature de garde", "créature gardienne massive de trois-quarts, armure gravée, brume au sol, " + _FR],
    ["Héros au combat", "héros en pleine action, cape en mouvement, éclat d'arme, arrière-plan simplifié, " + _FR],
    ["Sort élémentaire", "explosion d'énergie élémentaire, volutes lumineuses, fond sombre pour lire le titre, " + _FR],
    ["Paysage de royaume", "vaste paysage de royaume au crépuscule, silhouette d'architecture, ciel très travaillé, " + _FR],
    ["Artefact posé", "artefact unique posé sur un socle, éclairage rasant, arrière-plan neutre, " + _FR],
    ["Bête des profondeurs", "bête abyssale cuirassée, eaux sombres, rais de lumière, " + _FR],
    ["Portail arcanique", "portail arcanique ouvert, runes flottantes, particules, " + _FR],
    ["Monture ailée", "monture ailée en vol au-dessus des nuages, contre-jour, " + _FR],
    ["Alchimiste", "alchimiste penché sur ses fioles luminescentes, clair-obscur, " + _FR],
    ["Ruine engloutie", "ruine engloutie envahie de végétation, faisceau de lumière, " + _FR],
    ["Blason héraldique", "blason héraldique stylisé, symétrie parfaite, aplats lisibles, " + _FR],
    ["Champ de bataille", "champ de bataille au petit matin, étendards, poussière, " + _FR],
    ["Familier", "petit familier expressif, pose dynamique, couleurs saturées, " + _FR],
    ["Cité suspendue", "cité suspendue dans les nuages, ponts de pierre, échelle épique, " + _FR],
    ["Rituel nocturne", "rituel nocturne, cercle de bougies, ombres portées longues, " + _FR],
    ["Machine de guerre", "machine de guerre à vapeur, rivets, fumée, perspective basse, " + _FR],
  ];

  /* ═══════════════════════════════════════════════════════════════════════
     9. ENREGISTREMENT
     ═══════════════════════════════════════════════════════════════════════ */
  const M = CF.register({
    id: "face",
    title: "Face",
    icon: "\u{1F3A8}",
    order: 1,

    painters: [
      { z: 20, fn: paintFace },
    ],

    state: {
      src: null,                 /* "cat:<id>" | "local:<clé>" | "img:<fichier>" */
      default_art: null,         /* repli de la precedence gelee (spec 2.3) */
      fit: "cover",              /* "cover" | "contain" | "free" */
      x: 0, y: 0,                /* decalage en MILLIMETRES depuis le centre */
      scale: 1, scale_y: 1,      /* facteurs ; scale_y suit tant que lock */
      rot: 0,                    /* degres */
      lock: true,                /* verrou de proportions */
      bg: "#12161c",             /* fond visible en « contenir » */
      win: "auto",               /* fenetre d'illustration (WIN_MODES) */
      eff_dpi: 0,                /* MESURE en DPI reels, lue par P7 ; 0 = rien */
      serie: "vectoriel",        /* voie d'illustration (SERIES) — portee par
                                    le DOCUMENT : elle voyage avec le jeu */
      seeded: false,             /* le premier ecran s'auto-garnit une fois */
      tab: "cat",
      prompt: "", model: "", size: "portrait_4_3", nimg: 1,
    },

    async init(host) {
      HOST = host;
      await pileLoad();
      /* L'ETAT DE LA SERIE, UNE FOIS : c'est un manifeste (des noms de
         fichiers), pas des images — la grille reste vectorielle et gratuite
         tant que la voie « affiche polonaise » n'est pas choisie. */
      await serieLoad();
      /* Les modeles ET leur tarif : la route de la piece va les chercher dans
         la table de tarifs de l'application. Si elle manque (backend plus
         ancien), on retombe sur la liste seule — sans prix plutot qu'avec un
         prix invente. */
      try {
        const r = await M.api.get("ai-models");
        MODELS = (r && r.models) || [];
        AI_META = r || {};
      } catch (e) {
        AI_META = {};
        try { const r2 = await CF.images.models(); MODELS = (r2 && r2.models) || []; }
        catch (e2) { MODELS = []; }
      }
      /* ETAT VIDE QUI PROPOSE QUELQUE CHOSE : au tout premier ecran, une face
         du catalogue est deja posee. On ne le refait jamais (seeded), donc
         « Retirer » retire pour de bon. */
      if (!CF.get("face.seeded", false) && !CF.get("face.src", null) && !CF.get("face.default_art", null)) {
        const c = CATALOG[fnv1a32(String(CF.doc().id || "deck")) % CATALOG.length];
        M.patch({ src: "cat:" + c.id, default_art: "cat:" + c.id, seeded: true });
      }
      renderPanel();
      wireStage();
      wireKeys();
      CF.on("core:geom", () => { paintGauge(); readout(); });
      CF.on("core:cards", () => { paintGauge(); });
      /* P10 PUBLIE, P1 SE SERT (plan D6). Le bouton « adopter » DERIVE de
         `doc.capture` : sans cette ecoute, il n'apparaitrait qu'au prochain
         changement d'onglet — c'est-a-dire jamais au moment ou l'utilisateur
         revient d'importer sa carte. On ne repeint que sur CE sous-arbre :
         repeindre le panneau a chaque frappe de P3 ferait perdre le curseur. */
      CF.on("core:doc", (e) => { if (e && e.id === "capture") renderPanel(); });
    },
  });
})();
