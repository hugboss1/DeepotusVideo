/* ═══════════════════════════════════════════════════════════════════════════
   Card Forge — piece 02 · Cadre   [P2]
   Proprietaire exclusif de : doc.frame · z 40, 70 · /api/cards/<did>/frame/*
   Prefixe DOM impose : id="cf-frame-..."   ·   feuille : css/mod-frame.css

   LA BARRE (Clash of Decks) sert TROIS PNG de 638 x 1004 px qui sont le meme
   cadre avec un mot different. 638 px sur 2,5 pouces = 255 DPI : agrandi, il
   pixelise, et il ne peut PAS suivre un changement de format ou de definition.
   Ici il n'y a aucun bitmap : le cadre est une DESCRIPTION (famille, rarete,
   filets, marges, fenetre, ornements) que l'on redessine a geom.canvas_px a
   chaque rendu. A 600 DPI il est net ; sur un tarot il se re-proportionne ;
   et il y a un DOS, que la barre n'a pas du tout.

   7 familles graphiques x 6 raretes = 42 combinaisons (la barre : 3).

   doc.format.corner_mm donne le rayon de la coupe : le cadre ne le redecide
   pas, il le SUIT (le filet exterieur epouse le meme arrondi). La fenetre
   d'illustration, elle, a son propre rayon — c'est un dessin, pas une decoupe.
   ═══════════════════════════════════════════════════════════════════════════ */
"use strict";

(function () {
  const CF = (typeof window !== "undefined") ? window.CF : null;
  if (!CF) throw new Error("mod-frame: js/core.js doit etre charge avant ce fichier");

  /* ═══════════════════════════════════════════════════════════════════════
     LE CATALOGUE. Bloc EXTRAIT et compare a `cards/frame.py` par
     `test_cards_frame.py` : deux listes qui derivent en silence, c'est un
     menu qui propose un cadre que le backend ne connait pas. Meme doctrine
     que le bloc de geometrie de core.js / contract.py.
     ═══════════════════════════════════════════════════════════════════════ */
  /* ═══ CF-FRAME-CATALOG-BEGIN ═══ */
  const FAMILIES = [
    { id: "runic", label: "Runique", hint: "gravure fine, équerres, tirets runiques" },
    { id: "arcane", label: "Arcane", hint: "volutes, fenêtre en arc, filigrane" },
    { id: "timber", label: "Bois sculpté", hint: "veines, rivets, bande épaisse" },
    { id: "deco", label: "Art déco", hint: "chevrons étagés, éventails, coins coupés" },
    { id: "neon", label: "Néon", hint: "double trait lumineux, coins coupés" },
    { id: "sable", label: "Épure", hint: "un seul filet, grande marge, rien d'autre" },
    { id: "gravure", label: "Gravure", hint: "marge ivoire, aplat de pochoir décalé, repères" },
  ];
  const RARITIES = [
    { id: "common", label: "Commune" },
    { id: "uncommon", label: "Peu commune" },
    { id: "rare", label: "Rare" },
    { id: "epic", label: "Épique" },
    { id: "legendary", label: "Légendaire" },
    { id: "mythic", label: "Mythique" },
  ];
  const BACKS = [
    { id: "mirror", label: "Miroir du recto" },
    { id: "lattice", label: "Treillis" },
    { id: "guilloche", label: "Guilloché" },
    { id: "sunburst", label: "Soleil" },
    { id: "scales", label: "Écailles" },
    { id: "chevron", label: "Chevrons" },
    { id: "runes", label: "Runes" },
    /* LE VERSO PERSONNALISE (spec §6.2ter) — pas un motif de plus : le dos
       devient une IMAGE importee plus une pile de calques. Il arrive EN
       DERNIER pour que les sept motifs gardent leur rang (`card.back` et les
       sept habillages en portent deja les identifiants). */
    { id: "custom", label: "Personnalisé" },
  ];
  /* les modes de fusion d'un calque de verso — CEUX QUI EMPILENT, et rien
     d'autre (§6.2ter). Le `multiply` n'est jamais demande au compositeur : il
     est PRECOMPOSE dans les pixels du calque (voir `drawBackLayer`), sans quoi
     la couche « cadre » du rendu par couches cesserait d'etre isolee (§4.2). */
  const BACK_BLENDS = [
    { id: "normal", label: "Normal" },
    { id: "multiply", label: "Multiplier" },
  ];
  const BACK_LAYERS_MAX = 6;   /* spec §6.2ter, plan 3c decision 5 */
  const BACK_IMAGES_MAX = 8;   /* images de verso par jeu (meme decision) */
  const BACK_LAYER_DEFAULTS = { src: "", opacity: 1, scale: 1, blend: "normal" };
  /* le motif du VOCABULAIRE : ce qu'un document a le droit de nommer. Il est
     ANCRE des deux bouts — le piege du `$` sans ancre de tete a deja ete paye
     trois fois dans ce depot. Jumeau de `BACK_SRC_RE` de cards/frame.py. */
  const BACK_SRC_RE = /^(|img:img_\d+\.png)$/;
  const CORNERS = [
    { id: "none", label: "Aucun" },
    { id: "bracket", label: "Équerre" },
    { id: "scroll", label: "Volute" },
    { id: "stud", label: "Rivet" },
    { id: "fleuron", label: "Fleuron" },
    { id: "spike", label: "Pointe" },
  ];
  /* LE SCEAU PRISMATIQUE (spec §6.2bis) — pas un archetype de mise en page :
     un CONTOUR holographique combinable avec tout archetype. Deux recettes,
     les memes que le materiau 3D de la phase 2b (argent / dorure). */
  const SEAL_KINDS = [
    { id: "argent", label: "Argent holographique" },
    { id: "dorure", label: "Dorure holographique" },
  ];
  const METALS = [
    { id: "gold", label: "Or" },
    { id: "silver", label: "Argent" },
    { id: "copper", label: "Cuivre" },
    { id: "steel", label: "Acier" },
    { id: "rose", label: "Or rose" },
  ];
  const PRESETS = [
    { id: "sobre", label: "Runique sobre", set: { family: "runic", rarity: "common", line_mm: 0.6, inner_mm: 4.5, metal: false, corner: "bracket", banner: false } },
    { id: "heroique", label: "Arcane légendaire", set: { family: "arcane", rarity: "legendary", line_mm: 1.1, inner_mm: 6, metal: true, metal_tone: "gold", corner: "scroll", banner: true, gem: true } },
    { id: "cyber", label: "Néon épique", set: { family: "neon", rarity: "epic", line_mm: 0.5, double: true, gap_mm: 1.2, inner_mm: 4, metal: false, corner: "bracket", banner: true } },
    { id: "taverne", label: "Bois commun", set: { family: "timber", rarity: "uncommon", line_mm: 1.4, inner_mm: 7, metal: true, metal_tone: "copper", corner: "stud", banner: true } },
    { id: "musee", label: "Épure rare", set: { family: "sable", rarity: "rare", line_mm: 0.35, double: false, inner_mm: 9, metal: false, corner: "none", banner: false, gem: false, plate: true } },
  ];
  const LIMITS = {
    /* `edge_mm` allait de 0 a 6 quand `line_mm` va de 0 a 8 : un filet de 8 mm
       ne pouvait pas etre rentre de plus de 6 mm, et la combinaison des deux
       curseurs etait amputee sans que rien ne le dise. Meme borne haute. */
    line_mm: [0, 8], gap_mm: [0, 4], edge_mm: [0, 8], inner_mm: [0, 20],
    win_r_mm: [0, 8], corner_mm: [0, 8], plate_alpha: [0, 1], grad_angle: [0, 360],
    socle_alpha: [0, 1],
    /* la LARGEUR DE BANDE du filigrane (§6.2bis-d). Le plancher n'est pas un
       chiffre rond : 0,2 mm est le trait minimal qu'un imprimeur foil accepte
       (§6.2bis-b). Le plafond est un choix ; la borne qui MORD vraiment est
       celle du format, plus bas. */
    seal_width_mm: [0.2, 6],
    /* LE VERSO PERSONNALISE (§6.2ter) : l'opacite et l'echelle d'un calque.
       L'echelle part de 0,25 et non de 0 — un calque a l'echelle nulle n'est
       pas un reglage, c'est un calque qu'on aurait du eteindre (l'opacite,
       elle, va bien jusqu'a 0 : c'est exactement ce qu'elle veut dire). */
    back_opacity: [0, 1],
    back_scale: [0.25, 4],
  };
  /* ── LA BORNE QUE LE FORMAT IMPOSE, ET QU'IL MANQUAIT ─────────────────────
     BUG TROUVE PAR LE BALAYAGE DES DOUZE FORMATS, mesure avant correction :
     format `micro` (31,75 x 44,45 mm), marge interieure au maximum du curseur
     (20 mm). La bande vaut alors `tw - 2 x inner` = 31,75 - 40 = -8,25 mm,
     soit -97 px de large a 300 DPI. `rrPath` trace un rectangle RETOURNE,
     `outerRing` decoupe donc en « pair-impair » une region qui n'est plus un
     anneau, et l'encre de la bande sort sur toute la toile : le cadre est
     entierement faux, sans une seule exception ni une seule erreur de rendu.
     Capture a l'appui — la carte n'a plus ni anneau ni plaque.

     Les bornes des curseurs sont en MILLIMETRES ABSOLUS ; une carte, non. La
     borne reelle se DEDUIT du format : la plaque de texte est posee a
     `band.x + 1,2 mm` et large de `band.w - 2,4 mm`, donc la bande doit garder
     au moins ces 2,4 mm plus de quoi l'y voir. BAND_MIN_MM = 4 mm d'ouverture
     minimale laisse 1,6 mm de plaque — le plancher, pas un confort.

     Sur les douze formats livres, cette borne ne MORD que sur `micro`
     (13,87 mm au lieu de 20) : partout ailleurs `min(tw,th)/2 - 2` depasse
     deja 20 mm, et pas un pixel des mesures precedentes ne bouge. Une borne
     qui n'entre en jeu que la ou la geometrie casse. */
  const BAND_MIN_MM = 4;
  function bandMaxMM(tw, th) {
    const v = Math.min(Number(tw) || 0, Number(th) || 0) / 2 - BAND_MIN_MM / 2;
    return v > 0 ? Math.round(v * 100) / 100 : 0;
  }

  /* ── LA BORNE DU SCEAU, AU MEME PATRON ────────────────────────────────────
     Le Sceau est un ANNEAU : bord exterieur sur `m.outer` (la coupe rentree
     de `edge_mm`), creuse vers l'interieur sur `width_mm`. Deux choses le
     bornent, et aucune n'est un millimetre absolu : LA FENETRE (au-dela,
     l'anneau n'est plus un contour mais une plaque sur l'illustration) et LE
     FORMAT (comme la bande, l'anneau s'INVERSE si sa largeur passe la
     demi-carte, et le decoupage en pair-impair rend alors l'encre sur toute
     la toile — le defaut mesure sur `micro`, voir BAND_MIN_MM). `SEAL_MIN_MM`
     est le trait minimal d'un imprimeur foil (spec §6.2bis-b).

     ET LE PLANCHER S'APPLIQUE AU RESULTAT, PAS SEULEMENT AU CURSEUR. Defaut
     de la ronde 1 : la borne rabotait la largeur a la place disponible sans
     jamais la confronter au plancher qu'elle pretendait tenir. Mesure — poker,
     fenetre posee a 1,61 mm de la coupe : place = 0,01 mm, et l'ecran
     DESSINAIT une bande de 0,01 mm (0,118 px a 300 DPI), le panneau lisait
     « 0.01 mm » et /metrics le publiait. C'est la largeur meme que le
     preflight de l'imprimeur refuse : l'ecran dessinait ce que la presse
     rejette. Sous le plancher il n'y a pas un anneau etroit, il n'y a PAS
     D'ANNEAU — et la ligne d'etat le dit. */
  const SEAL_MIN_MM = 0.2;
  function sealMaxMM(tw, th, edgeMM, wm) {
    const e = Number(edgeMM) || 0;
    const W = Number(tw) || 0, H = Number(th) || 0;
    const w = wm || { x: 0, y: 0, w: W, h: H };
    const fen = Math.min(w.x, w.y, W - (w.x + w.w), H - (w.y + w.h)) - e;
    const carte = (Math.min(W, H) - 2 * e - SEAL_MIN_MM) / 2;
    const v = Math.min(fen, carte);
    /* la comparaison porte sur la valeur NON ARRONDIE : 0,196 mm s'arrondit a
       0,20 et passerait le plancher en publiant une largeur que la place ne
       porte pas. */
    return v >= SEAL_MIN_MM ? Math.round(v * 100) / 100 : 0;
  }

  /* le schema du Sceau : la SEULE description de `doc.frame.seal`, miroir de
     `SEAL_DEFAULTS` de cards/frame.py. Eteint par defaut — sinon tous les jeux
     deja enregistres changeraient d'aspect au premier chargement. */
  const SEAL_DEFAULTS = {
    on: false, kind: "argent", width_mm: 1.2,
    scope: { screen: true, print: false, mesh: false },
  };
  /* ═══ CF-FRAME-CATALOG-END ═══ */

  /* la borne du format courant, la SEULE porte par laquelle passent le dessin,
     l'interface, le modele d'occupation et les chiffres publies. */
  function capOf(g) { return bandMaxMM(g.trim_mm[0], g.trim_mm[1]); }

  /* Les valeurs par defaut SONT le schema : `patch` n'acceptera aucune autre
     cle. `window: null` vaut « automatique » — la fenetre se recalcule en
     proportion du format, ce qui rend la piece juste sur les 12 formats sans
     rien demander a personne. */
  const DEFAULTS = {
    family: "arcane", rarity: "rare",
    line_mm: 0.9, double: true, gap_mm: 1.1, edge_mm: 1.6, inner_mm: 5.5,
    line_color: "", metal: true, metal_tone: "gold",
    grad: true, grad_angle: 118,
    corner: "scroll", gem: true, banner: true, banner_text: "",
    plate: true, plate_alpha: 0.92,
    window: null, win_lock: false,
    /* la fenetre EFFECTIVE, publiee pour les autres pieces : [x, y, w, h] en
       mm depuis la coupe, ou null quand aucun cadre ne masque rien. C'est le
       contrat que P1 lit (`frame.art_window`) depuis le premier jour — la
       cle n'existait pas, la lecture tombait toujours sur la toile entiere,
       et la pose par defaut laissait jusqu'a 70 % de l'illustration sous le
       cadre. Publiee par `publishWindow`, jamais saisie a la main. */
    art_window: null,
    back: "guilloche", back_same: true, back_label: true,
    /* LE VERSO PERSONNALISE — l'image de fond et LA PREMIERE PILE ORDONNEE de
       P2 (tout le reste y est booleen ou enumere). `st()` leur donne donc
       leurs propres branches de validation, au patron de `sealOf` : rendre
       `DEFAULTS.back_layers` tel quel ferait d'un `push` d'utilisateur une
       ecriture dans le SCHEMA remis au registre du CORE. */
    back_image: "", back_layers: [],
    /* LE SCEAU — le PREMIER sous-objet de `doc.frame` (toutes les autres cles
       sont plates). `st()` lui donne donc sa propre branche de validation, au
       patron de `winMM` : `Object.keys(DEFAULTS)` ne descend pas d'un etage. */
    seal: SEAL_DEFAULTS,
    /* le modele d'occupation — actif par defaut : livrer un fichier ou la
       signature de l'artiste passe sous le ruban n'est pas un reglage. */
    fit: true, socles: true, seats: true, socle_alpha: 0.82,
  };

  /* palettes de rarete — le seul endroit ou une couleur de CARTE est ecrite.
     (L'INTERFACE, elle, n'a aucune couleur en dur : tokens seuls, regle 16.) */
  const PAL = {
    common: { base: ["#575e67", "#373d45", "#1f242a"], line: "#aab4c0", gem: "#cfd8e2", plate: "#1b1f25", glow: "#93a0ae" },
    uncommon: { base: ["#2f7050", "#1d4a33", "#10261b"], line: "#79dfa6", gem: "#57e08d", plate: "#112a1d", glow: "#3fcf80" },
    rare: { base: ["#2b5f96", "#1b3f68", "#0f2338"], line: "#7cc0f5", gem: "#4aa8f0", plate: "#101f30", glow: "#3b9ae8" },
    epic: { base: ["#5b3a91", "#3d2663", "#20143a"], line: "#c39bf5", gem: "#b07ef2", plate: "#1c1330", glow: "#9a6ef0" },
    legendary: { base: ["#8a6420", "#5c4113", "#2f200a"], line: "#f3d68a", gem: "#ffcf5c", plate: "#281e0c", glow: "#e8b53c" },
    mythic: { base: ["#8c2a2a", "#5c1919", "#2d0c0c"], line: "#ff9e86", gem: "#ff5f45", plate: "#290f0f", glow: "#ff5a3c" },
  };
  const METAL_STOPS = {
    gold: ["#6b4c12", "#f7e6a8", "#c9992f", "#fff8d8", "#7a5715"],
    silver: ["#5c646d", "#eef3f8", "#a8b3bf", "#ffffff", "#6a727b"],
    copper: ["#6d3a1c", "#f0b98c", "#b96a35", "#ffe0c4", "#7a4020"],
    steel: ["#39434f", "#c9d6e4", "#7e8d9d", "#eaf2fb", "#44505e"],
    rose: ["#7a4046", "#f6cfd0", "#c98189", "#fff0f0", "#84484e"],
  };
  const WIN_SHAPE = { runic: "rect", arcane: "arch", timber: "rect", deco: "chamfer", neon: "chamfer", sable: "rect", gravure: "rect" };

  /* ═══════════════════════════════════════════════════════════════════════
     0. OUTILS
     ═══════════════════════════════════════════════════════════════════════ */
  const has = (o, k) => Object.prototype.hasOwnProperty.call(o || {}, k);
  const cl = (v, a, b) => (v < a ? a : (v > b ? b : v));
  const num = (v, d) => { const n = Number(v); return isFinite(n) ? n : d; };
  const r1 = (v) => Math.round(v * 10) / 10;
  const r2 = (v) => Math.round(v * 100) / 100;
  const byId = (arr, id) => { for (let i = 0; i < arr.length; i++) if (arr[i].id === id) return arr[i]; return null; };
  const idx = (arr, id) => { for (let i = 0; i < arr.length; i++) if (arr[i].id === id) return i; return 0; };

  function rgb(h) {
    const s = String(h || "").replace("#", "");
    const t = s.length === 3 ? s[0] + s[0] + s[1] + s[1] + s[2] + s[2] : s;
    const n = parseInt(t, 16);
    return isFinite(n) ? [(n >> 16) & 255, (n >> 8) & 255, n & 255] : [128, 128, 128];
  }
  function rgba(h, a) { const c = rgb(h); return "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + a + ")"; }
  function mix(h1, h2, t) {
    const a = rgb(h1), b = rgb(h2);
    const v = (i) => Math.round(a[i] + (b[i] - a[i]) * t);
    return "rgb(" + v(0) + "," + v(1) + "," + v(2) + ")";
  }
  /* bruit DETERMINISTE : une veine de bois qui frissonne d'un rendu a l'autre
     rendrait l'apercu et le fichier livre differents — le bug que tout le
     contrat cherche a rendre inexprimable. */
  function prng(seed) { let s = seed >>> 0 || 1; return () => { s ^= s << 13; s >>>= 0; s ^= s >> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; }; }

  /* ═══════════════════════════════════════════════════════════════════════
     1. ETAT ET MODELE GEOMETRIQUE — tout en pixels de TOILE, jamais en mm
     ═══════════════════════════════════════════════════════════════════════ */
  function st(d) {
    const s0 = (d && d.frame) ? d.frame : {};
    /* MIGRATION DU DOCUMENT DE LA COQUILLE. La piece 02 « en construction »
       declarait back:"none" et family:"none" — un dos qui n'existe dans aucun
       catalogue, et donc une empreinte qu'aucune version livree ne peut
       ecrire. Les jeux crees avant les builders portent ces sept cles sur le
       disque : les relire telles quelles rendait une carte SANS CADRE, non
       parce que quelqu'un l'avait voulu, mais parce qu'un gabarit vide avait
       ete enregistre. Un document jamais configure repart des defauts.
       L'empreinte ne peut PAS etre « il manque des cles » : le registre du
       CORE fusionne le state declare avant l'hydratation, donc doc.frame
       porte toujours les 31 cles. Elle tient a la SEULE valeur impossible :
       aucun dos ne s'appelle "none" dans le catalogue livre, et l'interface
       ne sait ecrire que des identifiants du catalogue. */
    const coquille = (s0.back === "none");
    const s = coquille ? {} : s0;
    const o = {};
    Object.keys(DEFAULTS).forEach((k) => { o[k] = has(s, k) && s[k] !== undefined ? s[k] : DEFAULTS[k]; });
    o.family = byId(FAMILIES, o.family) ? o.family : (o.family === "none" ? "none" : DEFAULTS.family);
    o.rarity = byId(RARITIES, o.rarity) ? o.rarity : DEFAULTS.rarity;
    o.back = byId(BACKS, o.back) ? o.back : DEFAULTS.back;
    o.corner = byId(CORNERS, o.corner) ? o.corner : DEFAULTS.corner;
    o.metal_tone = byId(METALS, o.metal_tone) ? o.metal_tone : DEFAULTS.metal_tone;
    o.line_mm = cl(num(o.line_mm, DEFAULTS.line_mm), LIMITS.line_mm[0], LIMITS.line_mm[1]);
    o.gap_mm = cl(num(o.gap_mm, DEFAULTS.gap_mm), LIMITS.gap_mm[0], LIMITS.gap_mm[1]);
    o.edge_mm = cl(num(o.edge_mm, DEFAULTS.edge_mm), LIMITS.edge_mm[0], LIMITS.edge_mm[1]);
    o.inner_mm = cl(num(o.inner_mm, DEFAULTS.inner_mm), LIMITS.inner_mm[0], LIMITS.inner_mm[1]);
    o.plate_alpha = cl(num(o.plate_alpha, DEFAULTS.plate_alpha), 0, 1);
    o.socle_alpha = cl(num(o.socle_alpha, DEFAULTS.socle_alpha), 0, 1);
    o.grad_angle = cl(num(o.grad_angle, DEFAULTS.grad_angle), 0, 360);
    o.seal = sealOf(s.seal);
    o.back_image = backImageOf(s.back_image);
    o.back_layers = backLayersOf(s.back_layers);
    return o;
  }

  /* ── LE VERSO PERSONNALISE, VALIDE — miroir d'execution de `back_image_of`
     et `back_layers_of` de cards/frame.py.

     CE MIROIR NORMALISE, IL NE REFUSE PAS, et la difference avec `seal` est
     VOULUE : `/metrics` RECOIT un sceau dans un corps de requete, donc une
     valeur folle y merite un 400 qui nomme la borne. AUCUNE route ne recoit
     `back_image` / `back_layers` : ces cles ne vivent que dans le document,
     ou la doctrine est celle de `st()` — on REPARE ce qu'on possede. */
  function backImageOf(raw) {
    const s = (typeof raw === "string") ? raw : "";
    return BACK_SRC_RE.test(s) ? s : "";
  }
  /* UNE LONGUEUR DE CALQUE, aux memes conditions que `float()` du miroir.
     Le generique `num()` ne convient PAS ici : il prend `Number(null) === 0`
     et `Number("") === 0`, la ou `float(None)` et `float("")` LEVENT et
     retombent au defaut. Deux valeurs pour un meme document = une pastille de
     verification rouge sans qu'un pixel bouge (la lecon `width_mm: null` de la
     T1, rejouee). On accepte donc un NOMBRE ou une chaine numerique, et rien
     d'autre. */
  function bnum(v, d) {
    if (typeof v === "number") return isFinite(v) ? v : d;
    if (typeof v === "boolean") return v ? 1 : 0;
    if (typeof v === "string" && v.trim() !== "") {
      const n = Number(v);
      return isFinite(n) ? n : d;
    }
    return d;
  }
  function backLayersOf(raw) {
    /* TOUJOURS un tableau NEUF, d'objets NEUFS. Ce qui n'est pas un objet est
       JETE : une entree `null` dans une liste ORDONNEE n'est pas un calque
       eteint, c'est un document abime — et un trou dans la pile decalerait
       tout ce qui suit. */
    const out = [];
    if (!Array.isArray(raw)) return out;
    for (let i = 0; i < raw.length && out.length < BACK_LAYERS_MAX; i++) {
      const e = raw[i];
      if (!e || typeof e !== "object" || Array.isArray(e)) continue;
      out.push({
        src: backImageOf(e.src),
        opacity: cl(bnum(e.opacity, BACK_LAYER_DEFAULTS.opacity),
          LIMITS.back_opacity[0], LIMITS.back_opacity[1]),
        scale: cl(bnum(e.scale, BACK_LAYER_DEFAULTS.scale),
          LIMITS.back_scale[0], LIMITS.back_scale[1]),
        blend: byId(BACK_BLENDS, e.blend) ? e.blend : BACK_LAYER_DEFAULTS.blend,
      });
    }
    return out;
  }

  /* LE SCEAU, VALIDE — branche IMBRIQUEE, au patron de `winMM`.
     Elle rend TOUJOURS un objet NEUF : `DEFAULTS.seal` est le meme objet que
     celui remis au registre du CORE (`state: DEFAULTS`), et un alias rendu ici
     ferait d'un reglage de carte une ecriture dans le schema. La borne de
     FORMAT, elle, ne s'applique pas ici — `st()` n'a pas de geometrie ; elle
     tombe au trace, comme `Math.min(f.edge_mm, cap)` dans `model()`. */
  function sealOf(raw) {
    const s = (raw && typeof raw === "object" && !Array.isArray(raw)) ? raw : {};
    const sc = (s.scope && typeof s.scope === "object" && !Array.isArray(s.scope)) ? s.scope : {};
    const b = (v, d) => (typeof v === "boolean" ? v : d);
    return {
      on: b(s.on, SEAL_DEFAULTS.on),
      kind: byId(SEAL_KINDS, s.kind) ? s.kind : SEAL_DEFAULTS.kind,
      /* `null` vaut ABSENT, pas zero. Le generique `num()` prend
         `Number(null) === 0` et ramenerait la largeur au PLANCHER (0,2) la ou
         `_len` du backend rend le DEFAUT (1,2) : deux valeurs pour un meme
         document, donc une pastille de verification rouge sans qu'un pixel
         bouge. La branche du Sceau tranche pour « absent ». */
      width_mm: (s.width_mm === null || s.width_mm === undefined)
        ? SEAL_DEFAULTS.width_mm
        : cl(num(s.width_mm, SEAL_DEFAULTS.width_mm),
          LIMITS.seal_width_mm[0], LIMITS.seal_width_mm[1]),
      scope: {
        screen: b(sc.screen, SEAL_DEFAULTS.scope.screen),
        print: b(sc.print, SEAL_DEFAULTS.scope.print),
        mesh: b(sc.mesh, SEAL_DEFAULTS.scope.mesh),
      },
    };
  }
  function pal(f) { return PAL[f.rarity] || PAL.common; }
  function lineInk(f) { return f.line_color ? f.line_color : pal(f).line; }

  /* fenetre d'illustration, EN MILLIMETRES depuis le coin de COUPE (la meme
     origine que les slots de texte de P3 — deux conventions differentes dans
     un meme document, c'est un decalage garanti). */
  function winMM(g, f) {
    const tw = g.trim_mm[0], th = g.trim_mm[1];
    const w = f.window;
    if (w && typeof w === "object") {
      const W = cl(num(w.w, tw * 0.79), 2, tw);
      const H = cl(num(w.h, th * 0.5), 2, th);
      return {
        x: cl(num(w.x, 0), 0, tw - W), y: cl(num(w.y, 0), 0, th - H),
        w: W, h: H, r: cl(num(w.r, 2.5), LIMITS.win_r_mm[0], LIMITS.win_r_mm[1]), auto: false,
      };
    }
    return { x: r2(tw * 0.105), y: r2(th * 0.075), w: r2(tw * 0.79), h: r2(th * 0.505), r: 2.5, auto: true };
  }

  /* ── LA FENETRE, PUBLIEE — le contrat que P1 attendait deja ──────────────
     `mod-face.js` lit `frame.art_window` pour caler la pose sur ce que le
     cadre laisse voir. La cle n'etait jamais ecrite : le mode « auto » de la
     pose retombait TOUJOURS sur la toile entiere, et une carte a cadre posait
     son illustration en cover sur 100 % de la toile pour n'en montrer que la
     fenetre. On publie donc la fenetre EFFECTIVE (auto ou manuelle, la meme
     que `winMM` fait dessiner), en mm depuis la coupe — une mesure du calcul
     qui peint, pas une seconde formule. Differee et gardee par comparaison :
     un painter qui patche sans garde serait une boucle de rendu. */
  let WINPUB = null;
  function publishWindow(g, f) {
    const w = (f.family === "none") ? null : winMM(g, f);
    const pub = w ? [r2(w.x), r2(w.y), r2(w.w), r2(w.h)] : null;
    const cur = CF.get("frame.art_window", null);
    const same = (pub === null)
      ? (cur === null || cur === undefined)
      : (Array.isArray(cur) && cur.length === 4
        && cur.every((v, i) => Math.abs(Number(v) - pub[i]) < 0.005));
    if (same) return;
    if (WINPUB) clearTimeout(WINPUB);
    WINPUB = setTimeout(() => {
      WINPUB = null;
      M.patch({ art_window: pub });
    }, 120);
  }

  function model(g, f) {
    const mm = g.mm2px;
    const W = g.canvas_px[0], H = g.canvas_px[1];
    const bx = g.bleed_off_px[0], by = g.bleed_off_px[1];
    const tw = g.trim_px[0], th = g.trim_px[1];
    const R = num(g.corner_px, 0);
    /* les deux longueurs qui creusent la carte sont bornees PAR LE FORMAT :
       au-dela, la bande s'inverse et le decoupage en anneau n'a plus de sens
       (voir BAND_MIN_MM). Le meme plafond est applique par `occupancy`, par
       `localMetrics` et par `frame_metrics` du backend — un seul nombre. */
    const cap = capOf(g);
    const line = mm(f.line_mm), gap = mm(f.gap_mm),
      edge = mm(Math.min(f.edge_mm, cap)), inner = mm(Math.min(f.inner_mm, cap));
    const u = mm(1);                                   /* 1 mm : l'unite de dessin */
    const trim = { x: bx, y: by, w: tw, h: th, r: R };
    const outer = { x: bx + edge, y: by + edge, w: tw - 2 * edge, h: th - 2 * edge, r: Math.max(0, R - edge) };
    const band = { x: bx + inner, y: by + inner, w: tw - 2 * inner, h: th - 2 * inner, r: Math.max(0, R - inner) };
    const wm = winMM(g, f);
    const win = { x: bx + mm(wm.x), y: by + mm(wm.y), w: mm(wm.w), h: mm(wm.h), r: mm(wm.r) };
    const pTop = win.y + win.h + 1.8 * u;
    const pBot = band.y + band.h - 1.2 * u;
    const plate = { x: band.x + 1.2 * u, y: pTop, w: band.w - 2.4 * u, h: pBot - pTop, r: 1.6 * u };
    return { W: W, H: H, u: u, line: line, gap: gap, edge: edge, inner: inner, trim: trim, outer: outer, band: band, win: win, wm: wm, plate: plate };
  }

  /* ═══════════════════════════════════════════════════════════════════════
     1 bis. LE MODELE D'OCCUPATION — ce qui manquait vraiment
     ───────────────────────────────────────────────────────────────────────
     Avant ce bloc, le cadre empilait ses ornements sans jamais verifier
     qu'ils ne s'ecrasaient pas entre eux. Mesure sur le document par defaut
     et sur le FICHIER LIVRE : le bandeau de rarete recouvrait 73,6 % de la
     boite `artist` (la signature ne se lisait plus que « ortain ») et 69,7 %
     de `num` ; la gemme recouvrait 73,5 % de `cost`. Aucun compteur ne le
     disait — le moteur declarait zero erreur de rendu sur ce fichier.

     Ici chaque meuble est une BOITE RESERVEE en millimetres depuis la COUPE,
     au meme titre que les mentions de `doc.type.slots` (piece 03, lues en
     lecture universelle — regle 3). Trois leviers, dans cet ordre :

       1. DEPLACER   le ruban descend dans une voie libre de sa colonne ;
                     la gemme essaie les quatre coins.
       2. AMINCIR    si la voie libre est plus etroite que le ruban, c'est le
                     ruban qui maigrit (jusqu'a BANNER_MIN_H_MM).
       3. RANGER     si aucun coin n'est libre, la gemme ne se pose pas SUR le
                     chiffre : elle DEVIENT son logement, en couche 40, sous
                     le texte. Un meuble de la couche 40 ne peut pas masquer
                     une mention : le recouvrement disparait par construction.

     Ce qui reste est COMPTE, affiche a l'ecran, et ecrit dans le PNG livre.

     Bloc EXTRAIT et compare a `cards/frame.py` par `test_cards_frame.py` :
     deux placements qui derivent, c'est un apercu qui ment sur le fichier.
     ═══════════════════════════════════════════════════════════════════════ */
  /* ═══ CF-FRAME-OCC-BEGIN ═══ */
  const CLEAR_MM = 0.8;
  const BANNER_H_MM = 5.2;
  const BANNER_MIN_H_MM = 3.0;
  const BANNER_CH_MM = 3.4;
  const BANNER_PAD_CH = 4;
  const BANNER_MAX_F = 0.62;
  const GEM_R_MM = 4.6;
  const GEM_OFF_F = 0.75;
  const PIP_STEP_MM = 1.5;
  const PIP_R_MM = 0.5;
  const SOCLE_PAD_MM = 0.7;
  const SEAT_PAD_MM = 0.8;
  const SEAT_MIN_FRAC = 0.30;
  const SOCLE_MIN_FRAC = 0.05;
  const GEM_SEAT_RATIO = 1.6;
  const TOL_MM2 = 0.5;
  const TOL_FRAC = 0.02;
  /* ═══ CF-FRAME-OCC-END ═══ */

  function ovBox(a, b) {
    const dx = Math.min(a[0] + a[2], b[0] + b[2]) - Math.max(a[0], b[0]);
    const dy = Math.min(a[1] + a[3], b[1] + b[3]) - Math.max(a[1], b[1]);
    return (dx > 0 && dy > 0) ? dx * dy : 0;
  }
  function box4(b) {
    if (!Array.isArray(b) || b.length < 4) return null;
    const v = [Number(b[0]), Number(b[1]), Number(b[2]), Number(b[3])];
    if (!v.every(isFinite) || v[2] <= 0 || v[3] <= 0) return null;
    return v;
  }
  /* Les mentions obligatoires. Un slot mal forme est ignore, jamais une
     exception : le cadre doit se dessiner meme si P3 ecrit n'importe quoi. */
  function mentionsOf(slots) {
    const out = [];
    if (!Array.isArray(slots)) return out;
    slots.forEach((s) => {
      if (!s || typeof s !== "object") return;
      const b = box4(s.box);
      if (b) out.push({ id: String(s.id || "slot"), box: b });
    });
    return out;
  }
  function freeLanes(occ, lo, hi) {
    const segs = occ.map((s) => [Math.max(lo, s[0]), Math.min(hi, s[1])])
      .filter((s) => s[1] > lo && s[0] < hi)
      .sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const lanes = [];
    let cur = lo;
    segs.forEach((s) => { if (s[0] > cur) lanes.push([cur, s[0]]); cur = Math.max(cur, s[1]); });
    if (cur < hi) lanes.push([cur, hi]);
    return lanes;
  }
  function placeBanner(tw, th, inner, edge, label, ms, wbox, fit) {
    const w = Math.min(tw * BANNER_MAX_F, BANNER_CH_MM * (label.length + BANNER_PAD_CH));
    let h = BANNER_H_MM;
    const x = tw / 2 - w / 2;
    const y0 = th - inner - h * 0.62;
    let y = y0, lane = "naturelle";
    if (fit) {
      const occ = ms.filter((m) => m.box[0] < x + w && m.box[0] + m.box[2] > x)
        .map((m) => [m.box[1] - CLEAR_MM, m.box[1] + m.box[3] + CLEAR_MM]);
      const lanes = freeLanes(occ, edge, th - edge).filter((l) => l[1] - l[0] >= BANNER_MIN_H_MM);
      let best = null;
      lanes.forEach((l) => {
        const hh = Math.min(BANNER_H_MM, l[1] - l[0]);
        const cand = Math.min(Math.max(y0, l[0]), l[1] - hh);
        const pen = ovBox([x, cand, w, hh], wbox) > 0 ? th * 0.5 : 0;
        const d = Math.abs((cand + hh / 2) - (y0 + BANNER_H_MM / 2)) + pen;
        if (!best || d < best[0] - 1e-9) best = [d, cand, hh];
      });
      if (best) {
        y = best[1]; h = best[2];
        lane = (Math.abs(y - y0) < 1e-9 && Math.abs(h - BANNER_H_MM) < 1e-9) ? "naturelle"
          : (h < BANNER_H_MM - 1e-9 ? "voie libre, ruban aminci" : "voie libre");
      } else lane = "aucune voie libre";
    }
    return { id: "banner", label: "bandeau de rareté", z: 70, movable: true, lane: lane,
      box: [r2(x), r2(y), r2(w), r2(h)] };
  }
  function placeGem(tw, th, inner, rank, ms, fit) {
    let r = GEM_R_MM;
    const reach = 1.5 * r + Math.max(0, rank - 1) * PIP_STEP_MM + PIP_R_MM;
    const off = inner + r * GEM_OFF_F;
    const cands = [["HG", off, off, 1], ["HD", tw - off, off, -1],
      ["BG", off, th - off, 1], ["BD", tw - off, th - off, -1]];
    let best = null;
    for (let i = 0; i < cands.length; i++) {
      const c = cands[i];
      const x = c[3] > 0 ? c[1] - r : c[1] - reach;
      const bx0 = [x, c[2] - r, r + reach, 2 * r];
      let cost = 0;
      ms.forEach((m) => { cost += ovBox(bx0, m.box); });
      if (!best || cost < best.cost - 1e-9) best = { cost: cost, name: c[0], box: bx0, cx: c[1], cy: c[2], dir: c[3] };
      if (!fit || cost <= 0) break;
    }
    let cx = best.cx, cy = best.cy, box = best.box, name = best.name;
    const seat = !!fit && best.cost > TOL_MM2;
    let host = null, shape = "disc";
    if (seat) {
      host = ms[0];
      let bestOv = -1;
      ms.forEach((m) => { const a = ovBox(box, m.box); if (a > bestOv) { bestOv = a; host = m; } });
      const hb = host.box;
      cx = hb[0] + hb[2] / 2; cy = hb[1] + hb[3] / 2;
      const lo = Math.min(hb[2], hb[3]), hi = Math.max(hb[2], hb[3]);
      if (hi <= GEM_SEAT_RATIO * lo) {
        r = hi / 2 + SEAT_PAD_MM;
        box = [cx - r, cy - r, 2 * r, 2 * r];
      } else {
        shape = "rect";
        r = lo / 2 + SEAT_PAD_MM;
        box = [hb[0] - SEAT_PAD_MM, hb[1] - SEAT_PAD_MM, hb[2] + 2 * SEAT_PAD_MM, hb[3] + 2 * SEAT_PAD_MM];
      }
      name = "logement de " + host.id;
    }
    return { id: "gem", label: seat ? ("gemme en logement de " + host.id) : "gemme de rareté",
      z: seat ? 40 : 70, movable: true, lane: name, dir: best.dir, seat: seat,
      shape: shape, pips: seat ? 0 : rank, cx: r2(cx), cy: r2(cy), r: r2(r),
      box: [r2(box[0]), r2(box[1]), r2(box[2]), r2(box[3])] };
  }
  /* Le plan complet. MEME resultat que POST /frame/occupancy — l'ecran le
     confronte au backend a chaque changement, comme les metriques. */
  function occupancy(g, fr, slots) {
    const tw = g.trim_mm[0], th = g.trim_mm[1];
    const cap = bandMaxMM(tw, th);
    const inner = Math.min(num(fr.inner_mm, 5.5), cap), edge = Math.min(num(fr.edge_mm, 1.6), cap);
    const fit = fr.fit !== false;
    const ms = mentionsOf(slots);
    const w = fr.window;
    const wbox = (w && typeof w === "object")
      ? [r2(num(w.x, 0)), r2(num(w.y, 0)), r2(num(w.w, tw)), r2(num(w.h, th))]
      : [r2(tw * 0.105), r2(th * 0.075), r2(tw * 0.79), r2(th * 0.505)];
    const boxes = [{ id: "window", label: "fenêtre d'illustration", z: 40, movable: false, lane: "posée", box: wbox }];
    const rank = idx(RARITIES, fr.rarity) + 1;
    if (fr.gem !== false) boxes.push(placeGem(tw, th, inner, rank, ms, fit));
    if (fr.banner !== false) {
      const lab = String(fr.banner_text || (byId(RARITIES, fr.rarity) || {}).label || "").trim().toUpperCase();
      if (lab) boxes.push(placeBanner(tw, th, inner, edge, lab, ms, wbox, fit));
    }
    const socles = [], seats = [];
    const band = [inner, inner, tw - 2 * inner, th - 2 * inner];
    /* la gemme rangee en ecrin EST le logement de son hote : un second
       contour autour du meme chiffre ferait double emploi. */
    let gemHost = null;
    boxes.forEach((b) => { if (b.id === "gem" && b.seat) gemHost = b.lane.slice("logement de ".length); });
    ms.forEach((m) => {
      const b = m.box, area = b[2] * b[3];
      if (fr.socles !== false && ovBox(b, wbox) > SOCLE_MIN_FRAC * area) {
        socles.push({ id: "socle:" + m.id, label: "socle de " + m.id, z: 40, movable: false, lane: "sous la mention",
          box: [r2(b[0] - SOCLE_PAD_MM), r2(b[1] - SOCLE_PAD_MM), r2(b[2] + 2 * SOCLE_PAD_MM), r2(b[3] + 2 * SOCLE_PAD_MM)] });
      }
      const ring = area - ovBox(b, band);
      if (fr.seats !== false && ring > SEAT_MIN_FRAC * area && m.id !== gemHost) {
        seats.push({ id: "seat:" + m.id, label: "logement de " + m.id, z: 40, movable: false, lane: "dans l'anneau",
          box: [r2(b[0] - SEAT_PAD_MM), r2(b[1] - SEAT_PAD_MM), r2(b[2] + 2 * SEAT_PAD_MM), r2(b[3] + 2 * SEAT_PAD_MM)] });
      }
    });
    const hits = [];
    boxes.forEach((fb) => {
      if (fb.z !== 70) return;
      ms.forEach((m) => {
        const a = ovBox(fb.box, m.box), area = m.box[2] * m.box[3];
        if (a > TOL_MM2 && a > TOL_FRAC * area)
          hits.push({ kind: "recouvrement", a: fb.id, b: m.id, mm2: r2(a), pct: r1(100 * a / area) });
      });
    });
    hits.sort((x, y) => y.mm2 - x.mm2);
    return { boxes: boxes.concat(socles, seats),
      mentions: ms.map((m) => ({ id: m.id, box: m.box.map(r2) })),
      collisions: hits, count: hits.length, socles: socles.length, seats: seats.length, fit: fit };
  }
  /* Le plan tel qu'il est DESSINE : meme fonction, memes entrees. Le painter
     et l'interface ne peuvent pas diverger, ils lisent la meme chose. */
  function planOf(g, fr) {
    return occupancy(g, fr, CF.get("type.slots", []) || []);
  }
  function findBox(plan, id) {
    for (let i = 0; i < plan.boxes.length; i++) if (plan.boxes[i].id === id) return plan.boxes[i];
    return null;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     2. CHEMINS
     ═══════════════════════════════════════════════════════════════════════ */
  function rrPath(ctx, x, y, w, h, r) {
    const k = Math.max(0, Math.min(r, Math.min(Math.abs(w), Math.abs(h)) / 2));
    ctx.moveTo(x + k, y);
    ctx.lineTo(x + w - k, y);
    ctx.arcTo(x + w, y, x + w, y + k, k);
    ctx.lineTo(x + w, y + h - k);
    ctx.arcTo(x + w, y + h, x + w - k, y + h, k);
    ctx.lineTo(x + k, y + h);
    ctx.arcTo(x, y + h, x, y + h - k, k);
    ctx.lineTo(x, y + k);
    ctx.arcTo(x, y, x + k, y, k);
    ctx.closePath();
  }
  function chamferPath(ctx, x, y, w, h, c) {
    const k = Math.max(0, Math.min(c, Math.min(w, h) / 2.2));
    ctx.moveTo(x + k, y);
    ctx.lineTo(x + w - k, y); ctx.lineTo(x + w, y + k);
    ctx.lineTo(x + w, y + h - k); ctx.lineTo(x + w - k, y + h);
    ctx.lineTo(x + k, y + h); ctx.lineTo(x, y + h - k);
    ctx.lineTo(x, y + k); ctx.closePath();
  }
  function archPath(ctx, x, y, w, h, r) {
    const a = Math.min(w / 2, h * 0.44);
    const k = Math.max(0, Math.min(r, Math.min(w, h) / 2));
    ctx.moveTo(x, y + h - k);
    ctx.lineTo(x, y + a);
    ctx.bezierCurveTo(x, y + a * 0.34, x + w * 0.155, y, x + w / 2, y);
    ctx.bezierCurveTo(x + w * 0.845, y, x + w, y + a * 0.34, x + w, y + a);
    ctx.lineTo(x + w, y + h - k);
    ctx.arcTo(x + w, y + h, x + w - k, y + h, k);
    ctx.lineTo(x + k, y + h);
    ctx.arcTo(x, y + h, x, y + h - k, k);
    ctx.closePath();
  }
  /* la fenetre, DILATEE de `d` pixels : c'est ce qui permet de remplir un
     anneau entre deux contours homothetiques (la moulure) sans redecrire la
     forme une seconde fois — donc sans qu'un arc et son encadrement puissent
     diverger. */
  function winPathAt(ctx, m, shape, d) {
    const w = m.win, x = w.x - d, y = w.y - d, ww = w.w + 2 * d, hh = w.h + 2 * d;
    if (ww <= 0 || hh <= 0) return;
    if (shape === "arch") archPath(ctx, x, y, ww, hh, Math.max(0, w.r + d));
    else if (shape === "chamfer") chamferPath(ctx, x, y, ww, hh, Math.max(w.r + d, m.u * 3.2));
    else rrPath(ctx, x, y, ww, hh, Math.max(0, w.r + d));
  }
  function winPath(ctx, m, shape) { winPathAt(ctx, m, shape, 0); }

  /* ═══════════════════════════════════════════════════════════════════════
     3. MATIERES
     ═══════════════════════════════════════════════════════════════════════ */
  function bandPaint(ctx, m, f) {
    const p = pal(f);
    if (!f.grad) return p.base[1];
    const a = (num(f.grad_angle, 118)) * Math.PI / 180;
    const L = Math.max(m.W, m.H);
    const cx = m.W / 2, cy = m.H / 2;
    const gr = ctx.createLinearGradient(cx - Math.cos(a) * L / 2, cy - Math.sin(a) * L / 2,
      cx + Math.cos(a) * L / 2, cy + Math.sin(a) * L / 2);
    gr.addColorStop(0, p.base[0]);
    gr.addColorStop(0.46, p.base[1]);
    gr.addColorStop(1, p.base[2]);
    return gr;
  }
  function metalPaint(ctx, m, f, vertical) {
    const s = METAL_STOPS[f.metal_tone] || METAL_STOPS.gold;
    const gr = vertical ? ctx.createLinearGradient(0, m.trim.y, 0, m.trim.y + m.trim.h)
      : ctx.createLinearGradient(m.trim.x, 0, m.trim.x + m.trim.w, 0);
    gr.addColorStop(0, s[0]); gr.addColorStop(0.22, s[1]); gr.addColorStop(0.5, s[2]);
    gr.addColorStop(0.74, s[3]); gr.addColorStop(1, s[4]);
    return gr;
  }
  function inkPaint(ctx, m, f, vertical) { return f.metal ? metalPaint(ctx, m, f, vertical) : lineInk(f); }

  /* ═══════════════════════════════════════════════════════════════════════
     4. LES 6 FAMILLES — chacune sa grammaire. Tout est trace, rien n'est
        echantillonne : c'est ce qui rend le cadre net a n'importe quel DPI.
     ═══════════════════════════════════════════════════════════════════════ */
  /* ── LE PROFIL DE BANDE : la signature STRUCTURELLE de chaque famille ─────
     Mesure avant ce bloc, sur les vignettes du selecteur (74 x 101 px, le
     format ou le choix se fait vraiment) : « Bois sculpte » et « Epure »
     differaient sur 0,04 % des pixels et sur 0 pixel de forte difference —
     deux entrees de menu pour un seul dessin. « Runique x Epure » 0,24 %,
     « Runique x Bois » 0,28 %. La raison est mecanique : les six familles ne
     se distinguaient que par des traits fins (0,12 a 0,3 mm) et par une
     dispersion d'alpha, et une vignette reduit la toile d'un facteur 0,28 —
     tout ce qui est plus fin qu'un pixel disparait.
     Le remede n'est pas de foncer les traits mais de donner a chaque famille
     une SILHOUETTE : une masse de 1,4 a 3 mm, donc >= 1 px meme reduite. */
  /* MESURE APRES la premiere passe (gris NORMALISE, vignette 74 x 101, rarete
     egale — la mesure exacte du critique) : « Runique x Bois » 0,82 / 255,
     « Arcane x Bois » 2,18, « Runique x Arcane » 2,36. Autrement dit six
     entrees de menu pour trois squelettes : le profil de bande ne pesait que
     dans l'anneau, soit 18 % de la surface, et TOUT l'interieur — moulure de
     fenetre, plaque de texte, matiere — etait identique d'une famille a
     l'autre. On ne corrige pas cela avec des palettes : il faut que chaque
     famille change de MASSE a un endroit different de la carte.

     CINQ signatures par famille, sur cinq zones disjointes :
       zone     la masse de l'anneau         (26 % de la carte — la plus lourde)
       kind     le profil de la bande        (l'anneau, ses reliefs)
       moulure  l'encadrement de la fenetre  (le plus gros contraste du dessin)
       plaque   la forme de la plaque        (le bas de la carte)
       hatch    la trame de matiere          (toute la surface, angle + pas)
     Aucune valeur n'est partagee par deux familles — le test le verrouille
     colonne par colonne, et la mesure au pixel est rendue par l'interface
     elle-meme (badge « silhouettes », mesure sur les vignettes affichees).

     `zone` pese plus que les quatre autres reunies : deux familles qui
     encrent l'anneau au meme endroit se ressemblent forcement, quelles que
     soient leurs fioritures. Une poutre horizontale, un montant vertical, un
     bloc d'angle, un anneau plein, un anneau vide, un anneau clair : six
     masses qu'on distingue de loin, et qu'un gris normalise separe. */
  const PROFILE = {
    runic: { kind: "notched", t: 1.9, moulure: "gradins", plaque: "encoche", hatch: 90, pitch: 0.9, zone: "anneau" },
    arcane: { kind: "pilaster", t: 2.4, moulure: "arc", plaque: "arc", hatch: 62, pitch: 1.2, zone: "cotes" },
    timber: { kind: "planks", t: 3.0, moulure: "madrier", plaque: "planche", hatch: 8, pitch: 0.7, zone: "haut-bas" },
    deco: { kind: "tiers", t: 2.6, moulure: "etages", plaque: "etage", hatch: 45, pitch: 1.5, zone: "coins" },
    neon: { kind: "chamfer", t: 1.4, moulure: "halo", plaque: "biseau", hatch: 118, pitch: 2.2, zone: "vide" },
    sable: { kind: "brackets", t: 1.6, moulure: "trait", plaque: "epure", hatch: 26, pitch: 3.4, zone: "clair" },
    /* LA SEPTIEME (phase 3a) : l'estampe. Sa zone est un anneau IVOIRE — du
       papier, pas une rarete eclaircie — et son plus gros contraste n'est pas
       dans l'anneau mais AUTOUR DE LA FENETRE : un aplat de pochoir LARGE DE
       2,6 mm (il court de 0,6 a 3,2 mm depuis le bord de la fenetre — deux
       grandeurs differentes, on les ecrit toutes les deux), decale de 0,2 mm.
       C'est ce qui la separe d'« Epure », l'autre anneau clair du catalogue,
       dont la moulure ne pese qu'un cheveu (0,14 u de large). */
    gravure: { kind: "burin", t: 2.1, moulure: "pochoir", plaque: "cartouche", hatch: 155, pitch: 1.9, zone: "ivoire" },
  };
  /* LE DECALAGE VOULU, en millimetres. Une estampe coloriee au pochoir pose
     ses aplats a la main : ils ne tombent jamais pile sur le trait, et c'est
     ce defaut-la qu'on reconnait (spec §6.2-7, « reperage decale 0,2 mm
     volontaire »). Le seul decalage deliberé du fichier — ecrit une fois,
     nomme, mesurable ; partout ailleurs un ecart de calage est un bug. */
  const POCHOIR_MM = 0.2;

  /* ═══════════════════════════════════════════════════════════════════════
     LA REGLE DU FOND PERDU — tout ce qui encre l'anneau se decoupe sur la
     TOILE, jamais sur la ROGNE.
     ───────────────────────────────────────────────────────────────────────
     MESURE AVANT, sur les fichiers rendus par le vrai chemin d'export, a
     300 DPI, rarete « Rare » : ressaut de luminance entre les 12 px juste
     DEHORS et les 12 px juste DEDANS du trait de coupe, moyenne sur les
     76 % centraux de chaque cote (les coins sont arrondis) —

         Epure    108,6 / 255      Arcane   57,9        Neon    22,8
         Bois      60,7            Art deco 26,6        Runique 13,5

     Le fichier DECLARE un BleedBox de 3 mm exacts et ne contenait pas la
     matiere de la carte : `ringZone`, `relief` et `engrave` se decoupaient
     tous les trois sur la rogne, si bien qu'au-dela de la coupe il ne restait
     que le degrade de fond. Une derive de massicot vers l'exterieur faisait
     donc apparaitre un aplat a la place du cadre — precisement le defaut que
     le fond perdu existe pour absorber, dans un fichier qui affirme par
     ecrit qu'il l'absorbe. Un fichier sans fond perdu du tout serait moins
     dangereux : personne ne s'y fierait.

     `outerRing` est le decoupage commun : de la TOILE entiere a la bande.
     Les degrades, eux, restent cales sur la rogne — hors de leur intervalle
     un degrade de canvas prolonge sa couleur d'extremite, donc l'encre sort
     de la coupe en CONTINUITE de ton, sans nouvelle transition.

     ET LE CHIFFRE QUI MONTE, PARCE QU'IL FAUT LE DIRE SOI-MEME. Sur ce
     releve-la — 12 px dehors contre 12 px dedans, soit 1 mm de chaque cote —
     le nombre AUGMENTE apres correction (Runique 13,5 -> 48,0). Ce n'est pas
     une regression : une fenetre de 1 mm est plus large que le biseau de
     moulure lui-meme (0,34 mm), donc elle compare le fond perdu a la MOYENNE
     du biseau, pas au ton de la coupe. La grandeur qui decide vraiment de ce
     qu'un imprimeur verra est l'ecart de teinte sur la FENETRE DE MASSICOT,
     +/- 0,5 mm autour de la lame : celle-la tombe de 41,9-149,5 a 1,1-5,6
     selon la famille, elle est mesuree sur les octets du fichier livre par
     `measureCut`, et c'est elle que le panneau publie.
     ═══════════════════════════════════════════════════════════════════════ */
  function outerRing(ctx, m) {
    ctx.beginPath();
    ctx.rect(0, 0, m.W, m.H);
    rrPath(ctx, m.band.x, m.band.y, m.band.w, m.band.h, m.band.r);
    ctx.clip("evenodd");
  }

  /* L'ANNEAU : la masse que l'oeil voit avant tout le reste. On l'encre par
     ZONES, chaque famille la sienne, en degrade (jamais un aplat). */
  function ringZone(ctx, m, f) {
    const pr = PROFILE[f.family];
    if (!pr || pr.zone === "vide") return;
    /* MESURE, deuxieme passe : avec des tons proches du fond (mid = base[1]
       assombri de 10 %), l'anneau plein de « Runique » ne se distinguait
       presque pas du degrade de fond — 4,30 / 255 contre « Bois ». Une zone
       ne separe deux familles que si elle CONTRASTE avec le fond ; on encre
       donc franchement, du tres sombre au tres clair selon la famille. */
    const p = pal(f), u = m.u, T = m.trim, B = m.band;
    const dark = mix(p.base[2], "#000000", 0.62);
    const mid = mix(p.base[2], "#000000", 0.34);
    const lite = mix(p.base[0], "#ffffff", 0.44);
    /* les quatre marges de fond perdu, en px : l'encre part du bord de TOILE */
    const RX = m.W - (B.x + B.w), RY = m.H - (B.y + B.h);
    ctx.save();
    outerRing(ctx, m);
    const grad = (x0, y0, x1, y1, a, b) => {
      const gr = ctx.createLinearGradient(x0, y0, x1, y1);
      gr.addColorStop(0, a); gr.addColorStop(1, b);
      return gr;
    };
    if (pr.zone === "haut-bas") {
      /* MESURE : deux poutres sombres en haut et en bas ne suffisaient pas a
         separer « Bois » de « Runique » (5,01 / 255) — l'anneau plein runique
         a les memes masses a ces endroits-la, et les COTES restaient
         identiques des deux cotes. Un cadre en bois assemble a d'ailleurs des
         montants d'une autre teinte que ses traverses : on encre donc les
         quatre cotes, sombre en haut et en bas, CLAIR sur les montants. */
      ctx.fillStyle = grad(T.x, 0, B.x, 0, mix(p.base[0], "#ffffff", 0.52), lite);
      ctx.fillRect(0, 0, B.x, m.H);
      ctx.fillStyle = grad(B.x + B.w, 0, T.x + T.w, 0, lite, mix(p.base[0], "#ffffff", 0.30));
      ctx.fillRect(B.x + B.w, 0, RX, m.H);
      ctx.fillStyle = grad(0, T.y, 0, B.y, mid, dark);
      ctx.fillRect(0, 0, m.W, B.y);
      ctx.fillStyle = grad(0, B.y + B.h, 0, T.y + T.h, dark, mid);
      ctx.fillRect(0, B.y + B.h, m.W, RY);
    } else if (pr.zone === "cotes") {
      /* l'arche : deux montants SOMBRES pleine hauteur, et des linteaux
         CLAIRS en haut et en bas. C'est l'inverse exact du bois — et c'est ce
         qui les separe a la mesure : chaque paire de familles a au moins une
         zone entiere de tonalite opposee. */
      ctx.fillStyle = grad(0, T.y, 0, B.y, mix(p.base[0], "#ffffff", 0.56), lite);
      ctx.fillRect(0, 0, m.W, B.y);
      ctx.fillStyle = grad(0, B.y + B.h, 0, T.y + T.h, lite, mix(p.base[0], "#ffffff", 0.32));
      ctx.fillRect(0, B.y + B.h, m.W, RY);
      ctx.fillStyle = grad(T.x, 0, B.x, 0, mid, dark);
      ctx.fillRect(0, 0, B.x, m.H);
      ctx.fillStyle = grad(B.x + B.w, 0, T.x + T.w, 0, dark, mid);
      ctx.fillRect(B.x + B.w, 0, RX, m.H);
    } else if (pr.zone === "coins") {
      /* quatre blocs d'angle, et rien au milieu des cotes : la grammaire de
         l'art deco. Les bras sont proportionnels a LEUR cote, sans quoi une
         carte tres allongee voit ses angles se rejoindre en haut et laisser
         ses montants nus. */
      /* les bras partent du bord de TOILE et non de la rogne : ils sont donc
         plus longs de la marge de fond perdu, et epais jusqu'a la bande. */
      const Lx = T.w * 0.36 + T.x, Ly = T.h * 0.34 + T.y;
      [[0, 0, 1, 1], [m.W, 0, -1, 1], [0, m.H, 1, -1], [m.W, m.H, -1, -1]]
        .forEach((c, i) => {
          ctx.save(); ctx.translate(c[0], c[1]); ctx.scale(c[2], c[3]);
          ctx.fillStyle = grad(0, 0, Lx, Ly, i % 2 ? mid : dark, i % 2 ? dark : mid);
          ctx.fillRect(0, 0, Lx, B.y);
          ctx.fillRect(0, 0, B.x, Ly);
          /* la marche : le bloc s'arrete en biseau, pas net */
          ctx.fillStyle = rgba(mix(p.base[0], "#ffffff", 0.5), 0.55);
          ctx.fillRect(Lx - u * 1.2, 0, u * 1.2, B.y);
          ctx.fillRect(0, Ly - u * 1.2, B.x, u * 1.2);
          ctx.restore();
        });
    } else if (pr.zone === "anneau") {
      /* l'anneau entier, grave dans la pierre : la grammaire runique */
      ctx.fillStyle = grad(T.x, T.y, T.x + T.w, T.y + T.h, mid, dark);
      ctx.fillRect(0, 0, m.W, m.H);
      /* la levre claire qui borde la gravure, cote bande */
      ctx.strokeStyle = rgba(mix(p.base[0], "#ffffff", 0.5), 0.5);
      ctx.lineWidth = Math.max(0.6, u * 0.5);
      ctx.beginPath(); rrPath(ctx, B.x, B.y, B.w, B.h, B.r); ctx.stroke();
    } else if (pr.zone === "clair") {
      /* l'anneau entier, mais CLAIR : le contraire exact du precedent */
      ctx.fillStyle = grad(T.x, T.y, T.x + T.w, T.y + T.h,
        mix(p.base[0], "#ffffff", 0.66), mix(p.base[1], "#ffffff", 0.34));
      ctx.fillRect(0, 0, m.W, m.H);
    } else if (pr.zone === "ivoire") {
      /* LE PAPIER. « Epure » eclaircit la rarete — son anneau reste bleu,
         vert ou rouge pale ; celui-ci va au PAPIER : un ivoire qui ne garde
         de la rarete qu'un dixieme. La rarete, chez cette famille, n'est plus
         la couleur du cadre mais celle de l'ENCRE — vermillon, bleu, ocre et
         vert de la spec §6.2-7 sont, dans l'ordre, `mythic`, `rare`,
         `legendary` et `uncommon`. */
      const ivoire = mix(p.base[0], "#f7f0dd", 0.9);
      ctx.fillStyle = grad(T.x, T.y, T.x + T.w, T.y + T.h,
        ivoire, mix(ivoire, "#000000", 0.09));
      ctx.fillRect(0, 0, m.W, m.H);
      /* LA CUVETTE, ET CE QU'ELLE PARTAGE. Le bord de la plaque de cuivre
         marque le papier : DEHORS le papier nu, DEDANS la surface encree.
         Deux tons dans un meme anneau — et c'est exactement ce qui manquait.
         MESURE : avec un anneau ivoire d'un seul ton, « Epure x Gravure »
         tombait a 4,61 / 255 sur la toile livree et devenait la paire la plus
         serree du catalogue (elle etait a 5,20 avant la septieme famille).
         Deux anneaux clairs uniformes ne peuvent pas se distinguer beaucoup :
         le gris normalise efface la teinte, il ne reste que la REPARTITION.
         Le partage en deux zones concentriques en cree une. */
      const cv = Math.max(u * 1.6, m.inner * 0.42);
      const cvp = (d) => rrPath(ctx, T.x + d, T.y + d, T.w - 2 * d, T.h - 2 * d,
        Math.max(0, T.r - d));
      ctx.beginPath();
      cvp(cv);
      rrPath(ctx, B.x, B.y, B.w, B.h, B.r);
      ctx.fillStyle = grad(T.x, T.y, T.x + T.w, T.y + T.h,
        mix(p.base[1], "#000000", 0.12), mix(p.base[2], "#000000", 0.34));
      ctx.fill("evenodd");
      ctx.strokeStyle = rgba(mix(p.base[2], "#000000", 0.25), 0.6);
      ctx.lineWidth = Math.max(0.8, u * 0.5);
      ctx.beginPath(); cvp(cv); ctx.stroke();
    }
    /* LE RELIEF : une levre claire pres du bord de coupe, une ombre portee au
       bord de la bande. C'est ce qui fait qu'un anneau parait EPAIS et non
       peint — et, contrairement au bruit, cela ajoute de vraies plages
       tonales.
       ELLE ETAIT A 0,3 mm DE LA COUPE, large de 0,55 mm : elle occupait donc
       [0,02 ; 0,58] mm depuis la lame, c'est-a-dire l'interieur meme de la
       fenetre de massicot. Mesure : avec le palier de moulure deja pose, le
       ton du bord variait encore de 24,6 / 255 sur +/- 0,5 mm, et c'etait
       elle. Un liseré clair pose sur la lame sort plus fin d'un cote de la
       planche que de l'autre — le defaut d'amateur que la zone sure et le
       fond perdu existent pour empecher. Elle est rentree a 1,2 mm : son
       encre occupe [0,92 ; 1,48] mm, franchement hors de la fenetre. */
    ctx.lineWidth = Math.max(0.6, u * 0.55);
    ctx.strokeStyle = "rgba(255,255,255,.16)";
    ctx.beginPath(); rrPath(ctx, T.x + u * 1.2, T.y + u * 1.2, T.w - u * 2.4, T.h - u * 2.4,
      Math.max(0, T.r - u * 1.2)); ctx.stroke();
    ctx.strokeStyle = "rgba(0,0,0,.30)";
    ctx.beginPath(); rrPath(ctx, B.x - u * 0.3, B.y - u * 0.3, B.w + u * 0.6, B.h + u * 0.6,
      Math.max(0, B.r + u * 0.3)); ctx.stroke();
    ctx.restore();
  }
  function famProfile(ctx, m, f) {
    const pr = PROFILE[f.family];
    if (!pr) return;
    ringZone(ctx, m, f);
    const p = pal(f), u = m.u, t = pr.t * u;
    const dark = mix(p.base[2], "#000000", 0.42);
    const lite = mix(p.base[0], "#ffffff", 0.20);
    const B = m.band;
    ctx.save();
    ctx.fillStyle = dark;
    if (pr.kind === "planks") {
      /* deux traverses pleine largeur : une bande de bois se lit de loin */
      ctx.fillRect(m.trim.x + m.edge, m.trim.y + m.inner - t, m.trim.w - 2 * m.edge, t);
      ctx.fillRect(m.trim.x + m.edge, m.trim.y + m.trim.h - m.inner, m.trim.w - 2 * m.edge, t);
      ctx.fillStyle = lite;
      for (let k = 0; k < 6; k++) {
        const x = m.trim.x + m.edge + u * 3 + k * (m.trim.w - 2 * m.edge - u * 6) / 5;
        ctx.beginPath(); ctx.arc(x, m.trim.y + m.inner - t / 2, t * 0.26, 0, Math.PI * 2); ctx.fill();
        ctx.beginPath(); ctx.arc(x, m.trim.y + m.trim.h - m.inner + t / 2, t * 0.26, 0, Math.PI * 2); ctx.fill();
      }
    } else if (pr.kind === "tiers") {
      /* gradins de COIN : la signature de l'art deco est l'escalier, et il
         occupe les angles — pas les mêmes zones que les traverses du bois ni
         que les creneaux runiques, ce qui rend les trois lisibles a 74 px. */
      const L = Math.min(B.w, B.h) * 0.34;
      [[B.x, B.y, 1, 1], [B.x + B.w, B.y, -1, 1], [B.x, B.y + B.h, 1, -1], [B.x + B.w, B.y + B.h, -1, -1]]
        .forEach((c) => {
          ctx.save(); ctx.translate(c[0], c[1]); ctx.scale(c[2], c[3]);
          for (let k = 0; k < 3; k++) {
            ctx.fillStyle = k % 2 ? lite : dark;
            const o = -t * (k + 1) * 0.95, len = L * (1 - k * 0.26);
            ctx.fillRect(o, o, len, t * 0.9);
            ctx.fillRect(o, o, t * 0.9, len);
          }
          ctx.restore();
        });
      /* et l'eventail central, en masse cette fois */
      ctx.fillStyle = dark;
      const cxx = m.trim.x + m.trim.w / 2;
      for (let k = 0; k < 3; k++) {
        const ww = t * (5.4 - k * 1.5);
        ctx.fillRect(cxx - ww / 2, m.trim.y + m.edge + k * t * 0.85, ww, t * 0.7);
        ctx.fillRect(cxx - ww / 2, m.trim.y + m.trim.h - m.edge - k * t * 0.85 - t * 0.7, ww, t * 0.7);
      }
    } else if (pr.kind === "pilaster") {
      /* deux montants pleins : la grammaire d'une arche */
      ctx.fillRect(m.trim.x + m.edge, B.y - t, t, B.h + 2 * t);
      ctx.fillRect(m.trim.x + m.trim.w - m.edge - t, B.y - t, t, B.h + 2 * t);
      ctx.fillStyle = lite;
      ctx.fillRect(m.trim.x + m.edge, B.y - t, t, t * 0.5);
      ctx.fillRect(m.trim.x + m.trim.w - m.edge - t, B.y - t, t, t * 0.5);
      ctx.fillRect(m.trim.x + m.edge, B.y + B.h + t * 0.5, t, t * 0.5);
      ctx.fillRect(m.trim.x + m.trim.w - m.edge - t, B.y + B.h + t * 0.5, t, t * 0.5);
    } else if (pr.kind === "notched") {
      /* creneaux : la gravure runique en MASSE, sur les quatre cotes */
      ctx.fillStyle = dark;
      const n = 11;
      for (let i = 0; i < n; i++) {
        const x = B.x + B.w * (i + 0.5) / n - t * 0.6;
        const hh = t * (i % 2 ? 0.7 : 1.35);
        ctx.fillRect(x, B.y - hh, t * 1.2, hh);
        ctx.fillRect(x, B.y + B.h, t * 1.2, hh);
      }
      const nv = 15;
      for (let i = 0; i < nv; i++) {
        const y = B.y + B.h * (i + 0.5) / nv - t * 0.6;
        const ww = t * (i % 2 ? 0.7 : 1.35);
        ctx.fillRect(B.x - ww, y, ww, t * 1.2);
        ctx.fillRect(B.x + B.w, y, ww, t * 1.2);
      }
      ctx.fillStyle = lite;
      ctx.fillRect(B.x - t * 0.6, B.y - t * 0.6, t * 1.2, t * 1.2);
      ctx.fillRect(B.x + B.w - t * 0.6, B.y - t * 0.6, t * 1.2, t * 1.2);
      ctx.fillRect(B.x - t * 0.6, B.y + B.h - t * 0.6, t * 1.2, t * 1.2);
      ctx.fillRect(B.x + B.w - t * 0.6, B.y + B.h - t * 0.6, t * 1.2, t * 1.2);
    } else if (pr.kind === "chamfer") {
      /* le neon n'a pas de masse : il a une DOUBLE arete coupee, tres claire */
      ctx.strokeStyle = lite; ctx.lineWidth = t;
      ctx.beginPath(); chamferPath(ctx, B.x, B.y, B.w, B.h, u * 4.5); ctx.stroke();
      /* LE HALO NE SE POSE PLUS SUR LE FILET DE L'UTILISATEUR. Mesure sur le
         fichier livre, ligne mediane : le halo etait trace a `trim + edge`,
         c'est-a-dire exactement sur l'AXE du filet exterieur, avec une largeur
         de 8,3 px tiree du profil de famille et non du curseur. Consequences,
         toutes deux verifiees : le filet cessait d'etre une arete isolable
         (les deux bords se fondaient dans le halo — la mesure du panneau
         d'octets annonçait 17 px pour 10,63 px demandes), et surtout le
         curseur « epaisseur du filet » ne changeait plus rien de visible a cet
         endroit chez « Neon ». Le halo se pose desormais au MILIEU de
         l'anneau ; s'il n'y a pas d'anneau (marge interieure <= retrait), il
         revient a sa place d'origine plutot que de sortir sur l'illustration. */
      const room = Math.max(0, m.inner - m.edge);
      const gOff = m.edge + (room > m.line * 0.5 + u * 0.8 ? room * 0.5 : 0);
      ctx.strokeStyle = rgba(p.glow, 0.85); ctx.lineWidth = t * 0.5;
      ctx.beginPath(); chamferPath(ctx, m.trim.x + gOff, m.trim.y + gOff,
        m.trim.w - 2 * gOff, m.trim.h - 2 * gOff, u * 6); ctx.stroke();
    } else if (pr.kind === "burin") {
      /* LA GRAMMAIRE DE LA TAILLE-DOUCE. Aux quatre coins de la bande, les
         CROIX DE REPERAGE de l'imprimeur — celles qui servent a caler les
         passages de couleur, et que le pochoir de cette famille rate de
         0,2 mm exprès. Les coins sont deja pris par « Art deco » (des blocs
         PLEINS) et par « Epure » (des equerres) : une croix ouverte n'a ni
         leur masse ni leur contour. Puis la TAILLE, dans la marge basse : la
         ou une estampe porte sa lettre. */
      const rc = t * 1.5;
      ctx.strokeStyle = dark; ctx.lineWidth = Math.max(0.6, t * 0.2);
      [[B.x, B.y], [B.x + B.w, B.y], [B.x, B.y + B.h], [B.x + B.w, B.y + B.h]]
        .forEach((c) => {
          ctx.beginPath();
          ctx.moveTo(c[0] - rc, c[1]); ctx.lineTo(c[0] + rc, c[1]);
          ctx.moveTo(c[0], c[1] - rc); ctx.lineTo(c[0], c[1] + rc);
          ctx.stroke();
          ctx.beginPath(); ctx.arc(c[0], c[1], rc * 0.5, 0, Math.PI * 2); ctx.stroke();
        });
      const yl = m.trim.y + m.trim.h - m.inner * 0.5;
      ctx.strokeStyle = rgba(mix(p.base[2], "#000000", 0.15), 0.55);
      ctx.lineWidth = Math.max(0.4, t * 0.13);
      for (let k = 0; k < 44; k++) {
        const x = m.trim.x + m.trim.w * (k + 0.5) / 44;
        ctx.beginPath();
        ctx.moveTo(x, yl - t * 0.85); ctx.lineTo(x + t * 0.5, yl + t * 0.85);
        ctx.stroke();
      }
    } else if (pr.kind === "brackets") {
      /* epure : l'anneau est CLAIR (zone « clair »), seules quatre equerres le
         tiennent. C'est le contraire exact des poutres du bois — deux
         silhouettes qu'on distingue meme reduites a 74 px de large. */
      ctx.fillStyle = dark;
      const L = Math.min(B.w, B.h) * 0.3;
      [[B.x, B.y, 1, 1], [B.x + B.w, B.y, -1, 1], [B.x, B.y + B.h, 1, -1], [B.x + B.w, B.y + B.h, -1, -1]]
        .forEach((c) => {
          ctx.save(); ctx.translate(c[0], c[1]); ctx.scale(c[2], c[3]);
          ctx.fillRect(0, -t, L, t * 1.6); ctx.fillRect(-t, 0, t * 1.6, L);
          ctx.restore();
        });
    }
    ctx.restore();
  }

  /* ── LA MOULURE DE FENETRE : la plus grosse masse du dessin ───────────────
     C'est ici que se joue la difference entre deux familles, parce que le
     contour de la fenetre est la seule ligne que l'oeil suit sur toute la
     hauteur de la carte. Chaque famille a sa grammaire, et chacune remplit un
     ANNEAU entre deux contours dilates de la meme forme. */
  function winMoulding(ctx, m, f, shape) {
    const pr = PROFILE[f.family];
    if (!pr) return;
    const p = pal(f), u = m.u;
    const dark = mix(p.base[2], "#000000", 0.30);
    const lite = mix(p.base[0], "#ffffff", 0.30);
    const ring = (d0, d1, paint) => {
      ctx.beginPath();
      winPathAt(ctx, m, shape, d1);
      winPathAt(ctx, m, shape, d0);
      ctx.fillStyle = paint;
      ctx.fill("evenodd");
    };
    /* le degrade de relief : clair en haut a gauche, sombre en bas a droite.
       Un aplat n'a jamais fait croire a un relief. */
    const bevel = () => {
      const gr = ctx.createLinearGradient(m.win.x, m.win.y, m.win.x + m.win.w, m.win.y + m.win.h);
      gr.addColorStop(0, lite);
      gr.addColorStop(0.42, mix(p.base[1], "#ffffff", 0.06));
      gr.addColorStop(1, dark);
      return gr;
    };
    ctx.save();
    if (pr.moulure === "gradins") {
      ring(u * 0.5, u * 2.3, bevel());
      ctx.strokeStyle = rgba(p.line, 0.55); ctx.lineWidth = Math.max(0.5, u * 0.2);
      ctx.beginPath(); winPathAt(ctx, m, shape, u * 2.3); ctx.stroke();
      /* encoches runiques taillees dans la moulure, en haut et en bas */
      ctx.fillStyle = dark;
      const n = 9, span = m.win.w * 0.86, x0 = m.win.x + m.win.w / 2 - span / 2;
      for (let i = 0; i < n; i++) {
        const x = x0 + span * i / (n - 1) - u * 0.45;
        ctx.fillRect(x, m.win.y - u * 2.3, u * 0.9, u * 1.1);
        ctx.fillRect(x, m.win.y + m.win.h + u * 1.2, u * 0.9, u * 1.1);
      }
    } else if (pr.moulure === "arc") {
      ring(u * 0.4, u * 2.6, bevel());
      /* colonnettes : deux montants pleins qui descendent de l'arc */
      ctx.fillStyle = mix(p.base[0], "#000000", 0.12);
      const cy = m.win.y + m.win.h * 0.42;
      [m.win.x - u * 2.6, m.win.x + m.win.w + u * 1.4].forEach((x) => {
        ctx.fillRect(x, cy, u * 1.2, m.win.h * 0.58 + u * 2.6);
      });
      ctx.fillStyle = rgba(p.gem, 0.9);
      const cx = m.win.x + m.win.w / 2;
      ctx.beginPath();
      ctx.moveTo(cx - u * 2.4, m.win.y - u * 1.2);
      ctx.lineTo(cx, m.win.y - u * 4.6);
      ctx.lineTo(cx + u * 2.4, m.win.y - u * 1.2);
      ctx.closePath(); ctx.fill();
    } else if (pr.moulure === "madrier") {
      ring(u * 0.3, u * 3.4, bevel());
      /* joints de madrier : la moulure est faite de quatre pieces */
      ctx.strokeStyle = mix(p.base[2], "#000000", 0.55); ctx.lineWidth = Math.max(0.6, u * 0.3);
      const X0 = m.win.x - u * 3.4, Y0 = m.win.y - u * 3.4;
      const X1 = m.win.x + m.win.w + u * 3.4, Y1 = m.win.y + m.win.h + u * 3.4;
      [[X0, Y0, m.win.x, m.win.y], [X1, Y0, m.win.x + m.win.w, m.win.y],
        [X0, Y1, m.win.x, m.win.y + m.win.h], [X1, Y1, m.win.x + m.win.w, m.win.y + m.win.h]]
        .forEach((s) => { ctx.beginPath(); ctx.moveTo(s[0], s[1]); ctx.lineTo(s[2], s[3]); ctx.stroke(); });
      /* rivets : quatre tetes de clou, avec leur reflet */
      [[X0 + u * 1.7, Y0 + u * 1.7], [X1 - u * 1.7, Y0 + u * 1.7],
        [X0 + u * 1.7, Y1 - u * 1.7], [X1 - u * 1.7, Y1 - u * 1.7]].forEach((c) => {
        ctx.fillStyle = f.metal ? metalPaint(ctx, m, f, false) : lineInk(f);
        ctx.beginPath(); ctx.arc(c[0], c[1], u * 0.95, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = "rgba(255,255,255,.42)";
        ctx.beginPath(); ctx.arc(c[0] - u * 0.28, c[1] - u * 0.3, u * 0.3, 0, Math.PI * 2); ctx.fill();
      });
    } else if (pr.moulure === "etages") {
      ring(u * 0.4, u * 1.3, lite);
      ring(u * 1.8, u * 2.6, mix(p.base[1], "#000000", 0.18));
      ring(u * 3.0, u * 3.6, dark);
    } else if (pr.moulure === "halo") {
      ctx.shadowColor = rgba(p.glow, 0.95); ctx.shadowBlur = u * 2.6;
      ctx.strokeStyle = rgba(p.glow, 0.9); ctx.lineWidth = Math.max(0.5, u * 0.3);
      ctx.beginPath(); winPathAt(ctx, m, shape, u * 1.4); ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = rgba(mix(p.line, "#ffffff", 0.4), 0.75); ctx.lineWidth = Math.max(0.4, u * 0.16);
      ctx.beginPath(); winPathAt(ctx, m, shape, u * 2.8); ctx.stroke();
    } else if (pr.moulure === "trait") {
      ctx.strokeStyle = rgba(p.line, 0.55); ctx.lineWidth = Math.max(0.4, u * 0.14);
      ctx.beginPath(); winPathAt(ctx, m, shape, u * 3.2); ctx.stroke();
    } else if (pr.moulure === "pochoir") {
      /* L'APLAT DE POCHOIR ET SON REPERAGE DECALE (POCHOIR_MM). L'aplat est
         une MASSE — 2,6 mm d'encre de LARGEUR, posee de 0,6 a 3,2 mm du bord
         de la fenetre — la ou l'autre
         famille a anneau clair ne pose qu'un cheveu de 0,14 u : c'est la que
         se joue l'ecart de silhouette entre les deux, et c'est aussi la que
         se lit le geste du pochoir, puisque le TRAIT, lui, reste a sa place.
         Le decalage se voit donc en negatif, sur deux bords opposes. */
      ctx.save();
      ctx.translate(u * POCHOIR_MM, u * POCHOIR_MM);
      ring(u * 0.6, u * 3.2, rgba(p.gem, 0.7));
      ctx.restore();
      ctx.strokeStyle = rgba(mix(p.base[2], "#000000", 0.4), 0.85);
      ctx.lineWidth = Math.max(0.5, u * 0.22);
      ctx.beginPath(); winPathAt(ctx, m, shape, u * 0.6); ctx.stroke();
      ctx.beginPath(); winPathAt(ctx, m, shape, u * 3.2); ctx.stroke();
    }
    ctx.restore();
  }

  /* ── LA PLAQUE : sa forme appartient a la famille ─────────────────────────
     Elle occupe le bas de la carte, la zone que ni le profil de bande ni la
     moulure ne touchent : trois signatures, trois zones disjointes. */
  function platePath(ctx, m, f) {
    const pr = PROFILE[f.family], u = m.u;
    const P = m.plate, k = pr ? pr.plaque : "encoche";
    ctx.beginPath();
    if (k === "arc") {
      const a = Math.min(P.w / 2, P.h * 0.34);
      ctx.moveTo(P.x, P.y + P.h);
      ctx.lineTo(P.x, P.y + a);
      ctx.bezierCurveTo(P.x, P.y + a * 0.3, P.x + P.w * 0.18, P.y, P.x + P.w / 2, P.y);
      ctx.bezierCurveTo(P.x + P.w * 0.82, P.y, P.x + P.w, P.y + a * 0.3, P.x + P.w, P.y + a);
      ctx.lineTo(P.x + P.w, P.y + P.h);
      ctx.closePath();
    } else if (k === "encoche") {
      const c = Math.min(u * 2.4, P.h / 3);
      ctx.moveTo(P.x + c, P.y);
      ctx.lineTo(P.x + P.w - c, P.y); ctx.lineTo(P.x + P.w, P.y + c);
      ctx.lineTo(P.x + P.w, P.y + P.h); ctx.lineTo(P.x, P.y + P.h);
      ctx.lineTo(P.x, P.y + c); ctx.closePath();
    } else if (k === "planche") {
      rrPath(ctx, P.x - u * 0.8, P.y, P.w + u * 1.6, P.h, u * 0.6);
    } else if (k === "etage") {
      const s = Math.min(u * 2.2, P.w / 8);
      ctx.moveTo(P.x + s, P.y);
      ctx.lineTo(P.x + P.w - s, P.y); ctx.lineTo(P.x + P.w - s, P.y + s);
      ctx.lineTo(P.x + P.w, P.y + s); ctx.lineTo(P.x + P.w, P.y + P.h);
      ctx.lineTo(P.x, P.y + P.h); ctx.lineTo(P.x, P.y + s);
      ctx.lineTo(P.x + s, P.y + s); ctx.closePath();
    } else if (k === "biseau") {
      chamferPath(ctx, P.x, P.y, P.w, P.h, u * 3.4);
    } else if (k === "cartouche") {
      /* le cartouche de l'estampe : le meme rectangle strict qu'« Epure »,
         mais a coins ENTAILLES — les reperes d'un cadre de composition. La
         difference est en NEGATIF (de la matiere en moins aux quatre coins),
         donc elle survit a la reduction en vignette. */
      const c = Math.min(u * 2.6, P.w / 10, P.h / 3);
      ctx.moveTo(P.x + c, P.y);
      ctx.lineTo(P.x + P.w - c, P.y); ctx.lineTo(P.x + P.w - c, P.y + c * 0.45);
      ctx.lineTo(P.x + P.w, P.y + c * 0.45);
      ctx.lineTo(P.x + P.w, P.y + P.h - c * 0.45);
      ctx.lineTo(P.x + P.w - c, P.y + P.h - c * 0.45);
      ctx.lineTo(P.x + P.w - c, P.y + P.h);
      ctx.lineTo(P.x + c, P.y + P.h); ctx.lineTo(P.x + c, P.y + P.h - c * 0.45);
      ctx.lineTo(P.x, P.y + P.h - c * 0.45); ctx.lineTo(P.x, P.y + c * 0.45);
      ctx.lineTo(P.x + c, P.y + c * 0.45); ctx.closePath();
    } else {  /* epure : un rectangle strict, sans rayon */
      ctx.rect(P.x, P.y, P.w, P.h);
    }
  }
  /* les ferrures de la plaque : ce qui distingue une planche d'un gradin */
  function plateTrim(ctx, m, f) {
    const pr = PROFILE[f.family];
    if (!pr) return;
    const p = pal(f), u = m.u, P = m.plate;
    ctx.save();
    if (pr.plaque === "planche") {
      ctx.fillStyle = f.metal ? metalPaint(ctx, m, f, false) : lineInk(f);
      [[P.x + u * 1.4, P.y + u * 1.4], [P.x + P.w - u * 1.4, P.y + u * 1.4],
        [P.x + u * 1.4, P.y + P.h - u * 1.4], [P.x + P.w - u * 1.4, P.y + P.h - u * 1.4]]
        .forEach((c) => { ctx.beginPath(); ctx.arc(c[0], c[1], u * 0.6, 0, Math.PI * 2); ctx.fill(); });
    } else if (pr.plaque === "etage") {
      ctx.strokeStyle = rgba(p.line, 0.5); ctx.lineWidth = Math.max(0.4, u * 0.16);
      ctx.beginPath();
      ctx.moveTo(P.x + u * 1.2, P.y + P.h - u * 1.2); ctx.lineTo(P.x + P.w - u * 1.2, P.y + P.h - u * 1.2);
      ctx.stroke();
    } else if (pr.plaque === "arc") {
      ctx.strokeStyle = rgba(p.line, 0.45); ctx.lineWidth = Math.max(0.4, u * 0.14);
      ctx.beginPath();
      ctx.arc(P.x + P.w / 2, P.y + P.h * 0.42, Math.min(P.w, P.h) * 0.3, Math.PI, 0);
      ctx.stroke();
    } else if (pr.plaque === "biseau") {
      ctx.strokeStyle = rgba(p.glow, 0.6); ctx.lineWidth = Math.max(0.4, u * 0.12);
      ctx.beginPath();
      ctx.moveTo(P.x + u * 1.0, P.y + u * 0.9); ctx.lineTo(P.x + P.w - u * 1.0, P.y + u * 0.9);
      ctx.stroke();
    } else if (pr.plaque === "encoche") {
      ctx.fillStyle = rgba(p.line, 0.4);
      ctx.fillRect(P.x + P.w * 0.5 - u * 3, P.y + P.h - u * 1.1, u * 6, u * 0.35);
    } else if (pr.plaque === "cartouche") {
      /* le double filet interieur du cartouche — le meme geste que le filet
         1,5/3 mm du bord, en reduction. Il ne se trace que s'il a la place :
         un `strokeRect` a hauteur negative se retourne et sort de la boite. */
      if (P.h > u * 5) {
        ctx.strokeStyle = rgba(p.line, 0.55); ctx.lineWidth = Math.max(0.4, u * 0.14);
        ctx.strokeRect(P.x + u * 1.1, P.y + u * 1.1, P.w - u * 2.2, P.h - u * 2.2);
        ctx.strokeRect(P.x + u * 1.8, P.y + u * 1.8, P.w - u * 3.6, P.h - u * 3.6);
      }
    }
    ctx.restore();
  }

  /* ── LE PROFIL DE MOULURE : ce qui manquait vraiment a la matiere ─────────
     MESURE, tour 2, sur le FICHIER LIVRE et non sur l'ecran : 12,9 a 16,4
     couleurs uniques par mm2 dans un coin de 14 x 14 mm REELS selon la
     famille — un cadre peint a la main en compte nettement plus au meme
     endroit. Le tour 1 avait ajoute des trames et de la patine : +3 / mm2. Le
     diagnostic etait incomplet. Ce qui separe un cadre peint d'un cadre
     dessine n'est pas le bruit, c'est le RELIEF : une moulure a un PROFIL, et
     un profil se lit comme une rampe continue de tons en travers de l'anneau
     — ombre au bord de coupe, arete claire, gorge, listel, ombre au pied.
     Une rampe continue sur 65 px, c'est 60 tons la ou un aplat en donne 1, et
     c'est ce que l'oeil appelle « du bois » ou « du metal ».

     Le profil est le MEME pour les six familles (l'ecart entre familles se
     joue ailleurs — zones, silhouettes — et un profil par famille le
     brouillerait). Il est trace en noir et blanc translucide, donc il obeit a
     la teinte de la rarete sans jamais la remplacer. */
  const MOULURE = [
    [0.00, "0,0,0", 0.34], [0.07, "255,255,255", 0.20], [0.20, "255,255,255", 0.05],
    [0.34, "0,0,0", 0.13], [0.50, "255,255,255", 0.12], [0.66, "0,0,0", 0.07],
    [0.82, "255,255,255", 0.15], [0.93, "0,0,0", 0.10], [1.00, "0,0,0", 0.36],
  ];
  function relief(ctx, m) {
    const T = m.trim;
    const w = m.inner;
    if (w <= 1) return;
    /* LE PALIER QUI ENJAMBE LA COUPE. Profil brut releve a mi-hauteur sur le
       fichier livre, colonnes 32 a 40 (le trait de coupe tombe a 35,5) :
       11,8 · 14,2 · 20,7 · 20,7 · 15,2 · 16,5 · 56,0 · 71,1 · 83,7 · 91,8.
       La marche d'ombre du profil de moulure — sa butee sombre — etait posee
       EXACTEMENT sur la ligne de coupe, et le ton grimpait de 73 niveaux en
       0,34 mm juste apres. Une derive de massicot de 0,25 mm, soit la moitie
       de la tolerance courante, changeait donc la teinte du bord visible du
       simple au triple. Le fond perdu peut bien etre parfait : si le dessin
       lui-meme place son arete la plus dure sur la lame, il n'absorbe rien.
       La rampe demarre maintenant `pl` a l'INTERIEUR de la coupe et le
       degrade prolonge sa couleur d'extremite vers le dehors : le ton est
       constant du bord de toile jusqu'a `pl` DANS la carte. La tolerance
       usuelle de massicot etant de +/- 0,5 mm, la fenetre de coupe entiere
       tombe dans le palier.

       OU S'ARRETE LE PALIER — ET POURQUOI PAS A UNE CONSTANTE. Pose a 0,8 mm,
       il creait sa PROPRE arete a 0,8 mm de la coupe : une marche de 32,7/255
       a 0,35 mm devant le filet de l'utilisateur, donc un second trait
       fantome, et la relecture d'octets s'y accrochait au lieu du filet (elle
       annonçait 14 px de large pour 10,63 demandes, bord exterieur a 46 px
       pour 49,08). Un correctif qui fabrique le defaut suivant n'est pas un
       correctif. Le palier s'arrete desormais SOUS le filet — a son arete
       exterieure, `edge - line/2` — de sorte que la seule marche de la zone
       est celle que l'utilisateur a demandee. Sans filet, 0,8 mm ; et jamais
       plus du tiers de la bande, sinon un anneau etroit perdrait sa moulure. */
    const pl = Math.min(Math.max(m.u * 0.8, m.edge - m.line / 2), w * 0.35);
    ctx.save();
    outerRing(ctx, m);
    /* quatre rampes, une par cote, chacune du bord de coupe vers la bande :
       le profil est donc toujours dans le bon sens, y compris en bas et a
       droite ou il s'inverse. Le PAVE, lui, va jusqu'au bord de toile. */
    const ramp = (x0, y0, x1, y1) => {
      const gr = ctx.createLinearGradient(x0, y0, x1, y1);
      MOULURE.forEach((s) => { gr.addColorStop(s[0], "rgba(" + s[1] + "," + s[2] + ")"); });
      return gr;
    };
    ctx.fillStyle = ramp(T.x + pl, 0, T.x + w, 0);
    ctx.fillRect(0, 0, T.x + w, m.H);
    ctx.fillStyle = ramp(T.x + T.w - pl, 0, T.x + T.w - w, 0);
    ctx.fillRect(T.x + T.w - w, 0, m.W - (T.x + T.w - w), m.H);
    ctx.fillStyle = ramp(0, T.y + pl, 0, T.y + w);
    ctx.fillRect(0, 0, m.W, T.y + w);
    ctx.fillStyle = ramp(0, T.y + T.h - pl, 0, T.y + T.h - w);
    ctx.fillRect(0, T.y + T.h - w, m.W, m.H - (T.y + T.h - w));
    ctx.restore();
  }

  /* ── LA GRAVURE : du detail plus fin que le pixel de 300 DPI ─────────────
     « L'independance de resolution est architecturalement reelle mais
     visuellement peu exploitee : le 600 DPI n'apporte que +15 % de transitions
     dures, parce que le dessin est surtout fait de degrades doux. » Le
     reproche est juste ; ce bloc y repond en partie, et voici EXACTEMENT ce
     qu'il apporte, mesure et pas suppose.

     Le pas et l'epaisseur sont en MILLIMETRES. L'epaisseur choisie — 0,055 mm
     — vaut 0,65 px a 300 DPI (elle ne remplit pas un pixel : elle s'etale en
     gris) et 1,30 px a 600 (elle en remplit un). Aucun plancher en pixels :
     un `Math.max(0.35, ...)` comme ailleurs dans ce fichier aurait ecrase la
     difference au lieu de la produire.

     MESURE, sur les deux fichiers rendus, dans une bande de l'anneau CHOISIE
     SANS FILET (3,9 a 5,3 mm de la coupe), signal moins sa moyenne glissante
     sur 0,55 mm — donc la seule haute frequence : contraste efficace 20,08 a
     300 DPI contre 21,90 a 600, soit +9 %, et crete 130,9 contre 137,9, +5 %.
     C'est un gain modeste et on l'ecrit tel quel : le 600 DPI de cette piece
     sert d'abord a ne pas etre flou, un peu a etre plus fin. Ce qui n'est PAS
     modeste, et qui est la vraie propriete, c'est qu'aucun de ces traits n'est
     echantillonne : la toile passe de 815 x 1110 a 1630 x 2220 et tout est
     retrace, la ou un cadre bitmap de 638 px plafonne a 257 DPI. */
  function engrave(ctx, m, f) {
    const pr = PROFILE[f.family];
    if (!pr || !pr.pitch) return;
    const T = m.trim, u = m.u;
    if (m.inner <= u * 1.2) return;
    const step = pr.pitch * 0.5 * u;
    const n = Math.min(28, Math.floor(m.inner / Math.max(1e-6, step)));
    if (n < 2) return;
    /* et AUTANT de contours vers l'exterieur qu'il faut pour traverser le fond
       perdu : la gravure ne s'arrete pas au trait de coupe, elle le franchit.
       Un contour de d negatif grandit — rayon T.r + |d| — donc l'arrondi de
       coupe se prolonge lui aussi vers le bord de toile. */
    const nOut = Math.min(24, Math.ceil(Math.max(T.x, T.y) / Math.max(1e-6, step)) + 1);
    const p = pal(f);
    ctx.save();
    outerRing(ctx, m);
    ctx.lineWidth = u * 0.055;
    for (let k = 1 - nOut; k < n; k++) {
      if (k === 0) continue;
      const d = k * step;
      /* alpha CONTINU le long de la serie : deux contours voisins ne partagent
         jamais leur ton, c'est ce qui fait la matiere plutot que la rayure. */
      const t = k / n;
      const a = 0.055 + 0.075 * (0.5 + 0.5 * Math.sin(t * Math.PI * 3.7 + idx(FAMILIES, f.family)));
      ctx.strokeStyle = rgba(k % 2 ? p.base[2] : mix(p.base[0], "#ffffff", 0.5), a);
      ctx.beginPath();
      rrPath(ctx, T.x + d, T.y + d, T.w - 2 * d, T.h - 2 * d, Math.max(0, T.r - d));
      ctx.stroke();
    }
    ctx.restore();
  }

  /* ── LA MATIERE ───────────────────────────────────────────────────────────
     MESURE AVANT : 2 170 couleurs uniques dans un coin de 14 x 14 mm REELS,
     soit 11,07 par mm2 — le compte d'un aplat, ou presque. Un aplat et
     deux degrades ne font pas une matiere. On ajoute trois choses, toutes
     DETERMINISTES (meme graine -> meme fichier, sinon l'apercu et le livre
     different) : une trame d'angle et de pas propres a la famille, des taches
     de patine, et quelques usures claires. Rien de tout cela n'est un bitmap :
     ce sont des traits, donc cela suit la definition. */
  function matter(ctx, m, f, shape) {
    const pr = PROFILE[f.family];
    if (!pr || !pr.pitch) return;
    const p = pal(f), u = m.u;
    const seed = 1013 + idx(FAMILIES, f.family) * 7919 + idx(RARITIES, f.rarity) * 104729;
    const rnd = prng(seed);
    relief(ctx, m);
    engrave(ctx, m, f);
    const a = pr.hatch * Math.PI / 180;
    const dx = Math.cos(a), dy = Math.sin(a);
    const L = Math.sqrt(m.W * m.W + m.H * m.H);
    const step = pr.pitch * u;
    const cx = m.W / 2, cy = m.H / 2;
    ctx.save();
    ctx.lineCap = "butt";
    const pass = (ang, pas, amp) => {
      const ca = Math.cos(ang), sa = Math.sin(ang);
      for (let s = -L / 2; s <= L / 2; s += pas) {
        const ox = cx - sa * s, oy = cy + ca * s;
        const t = rnd();
        ctx.strokeStyle = rgba(t > 0.5 ? p.base[0] : p.base[2], amp * (0.5 + t));
        ctx.lineWidth = Math.max(0.35, u * (0.09 + rnd() * 0.16));
        ctx.beginPath();
        ctx.moveTo(ox - ca * L / 2, oy - sa * L / 2);
        ctx.lineTo(ox + ca * L / 2, oy + sa * L / 2);
        ctx.stroke();
      }
    };
    pass(a, step, 0.085);
    /* seconde trame, croisee : une seule direction fait une rayure, deux font
       une matiere.
       MESURE, et ce qui a ete RETIRE apres mesure : une passe de 260 points
       de grain a coute 50 Ko au fichier livre et n'a rendu +0,01 couleur/mm2
       — du bruit, donc, pas de la matiere. On ne garde que ce qui se mesure :
       11,07 couleurs/mm2 au depart, 14,2 avec les deux trames et les
       degrades de relief. Un cadre peint a la main en compte davantage : on
       ne pretend pas l'egaler avec un algorithme, et on affiche la mesure
       telle quelle, sans la comparer a quoi que ce soit. */
    pass(a + 1.29, step * 1.6, 0.055);
    /* PATINE. MESURE : a trois taches de 9 a 22 mm, un coin de 14 mm n'en
       voyait souvent aucune — la moitie des cartes n'avait aucune variation
       locale la ou justement on mesure la matiere. Neuf taches de 4 a 16 mm
       couvrent la carte sans jamais devenir un motif : chacune est un cone de
       tons continu, et c'est la superposition de deux cones qui multiplie les
       teintes plutot que de les additionner. */
    for (let k = 0; k < 9; k++) {
      const px = m.trim.x + rnd() * m.trim.w, py = m.trim.y + rnd() * m.trim.h;
      const R = m.u * (4 + rnd() * 12);
      const gr = ctx.createRadialGradient(px, py, R * 0.05, px, py, R);
      gr.addColorStop(0, rgba(k % 2 ? p.base[2] : p.base[0], 0.13));
      gr.addColorStop(0.55, rgba(k % 3 ? p.base[1] : p.base[0], 0.05));
      gr.addColorStop(1, rgba(p.base[1], 0));
      ctx.fillStyle = gr;
      ctx.fillRect(px - R, py - R, 2 * R, 2 * R);
    }
    /* usures : de courtes rayures claires sur les aretes de la bande */
    ctx.strokeStyle = rgba(mix(p.base[0], "#ffffff", 0.55), 0.20);
    for (let k = 0; k < 11; k++) {
      const e = Math.floor(rnd() * 4);
      const t2 = 0.12 + rnd() * 0.76, len = u * (2.5 + rnd() * 6);
      let x0, y0, ux, uy;
      if (e === 0) { x0 = m.trim.x + m.trim.w * t2; y0 = m.trim.y + m.inner * (0.2 + rnd() * 0.7); ux = 1; uy = 0; }
      else if (e === 1) { x0 = m.trim.x + m.trim.w * t2; y0 = m.trim.y + m.trim.h - m.inner * (0.2 + rnd() * 0.7); ux = 1; uy = 0; }
      else if (e === 2) { x0 = m.trim.x + m.inner * (0.2 + rnd() * 0.7); y0 = m.trim.y + m.trim.h * t2; ux = 0; uy = 1; }
      else { x0 = m.trim.x + m.trim.w - m.inner * (0.2 + rnd() * 0.7); y0 = m.trim.y + m.trim.h * t2; ux = 0; uy = 1; }
      ctx.lineWidth = Math.max(0.4, u * (0.1 + rnd() * 0.14));
      ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x0 + ux * len, y0 + uy * len); ctx.stroke();
    }
    ctx.restore();
  }

  function famRunic(ctx, m, f) {
    const p = pal(f), u = m.u;
    ctx.save();
    ctx.strokeStyle = rgba(p.glow, 0.5); ctx.lineWidth = Math.max(0.4, u * 0.18);
    for (let i = 1; i <= 2; i++) {
      ctx.beginPath(); rrPath(ctx, m.band.x - i * u * 0.9, m.band.y - i * u * 0.9,
        m.band.w + i * u * 1.8, m.band.h + i * u * 1.8, Math.max(0, m.band.r + i * u * 0.9)); ctx.stroke();
    }
    /* tirets runiques le long des bords haut et bas */
    ctx.strokeStyle = rgba(p.line, 0.62); ctx.lineWidth = Math.max(0.6, u * 0.26); ctx.lineCap = "butt";
    const n = 13, span = m.band.w * 0.74, x0 = m.trim.x + m.trim.w / 2 - span / 2;
    for (let i = 0; i < n; i++) {
      const x = x0 + span * (i / (n - 1)), t = (i % 3 === 0) ? 1.5 : 0.85;
      ctx.beginPath(); ctx.moveTo(x, m.trim.y + m.edge + u * 0.9); ctx.lineTo(x, m.trim.y + m.edge + u * (0.9 + t)); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(x, m.trim.y + m.trim.h - m.edge - u * 0.9); ctx.lineTo(x, m.trim.y + m.trim.h - m.edge - u * (0.9 + t)); ctx.stroke();
    }
    ctx.restore();
  }
  function famArcane(ctx, m, f) {
    const p = pal(f), u = m.u;
    ctx.save();
    /* filigrane : volutes le long des montants */
    ctx.strokeStyle = rgba(p.line, 0.42); ctx.lineWidth = Math.max(0.5, u * 0.22);
    const yc = m.trim.y + m.trim.h * 0.5;
    [m.trim.x + m.inner * 0.5, m.trim.x + m.trim.w - m.inner * 0.5].forEach((x, s) => {
      const dir = s === 0 ? 1 : -1;
      for (let k = -3; k <= 3; k++) {
        const y = yc + k * u * 5.4;
        ctx.beginPath();
        ctx.moveTo(x, y - u * 2.2);
        ctx.bezierCurveTo(x + dir * u * 2.1, y - u * 1.4, x + dir * u * 2.1, y + u * 1.4, x, y + u * 2.2);
        ctx.stroke();
      }
    });
    /* clef de voute au-dessus de la fenetre */
    ctx.strokeStyle = rgba(p.line, 0.7); ctx.lineWidth = Math.max(0.6, u * 0.3);
    const cx = m.win.x + m.win.w / 2, ty = m.win.y;
    ctx.beginPath();
    ctx.moveTo(cx - u * 4.2, ty - u * 0.6);
    ctx.bezierCurveTo(cx - u * 1.6, ty - u * 3.4, cx + u * 1.6, ty - u * 3.4, cx + u * 4.2, ty - u * 0.6);
    ctx.stroke();
    ctx.beginPath(); ctx.arc(cx, ty - u * 2.6, u * 0.85, 0, Math.PI * 2);
    ctx.fillStyle = rgba(p.gem, 0.85); ctx.fill();
    ctx.restore();
  }
  function famTimber(ctx, m, f) {
    const p = pal(f), u = m.u, rnd = prng(9137);
    ctx.save();
    ctx.beginPath(); rrPath(ctx, m.trim.x, m.trim.y, m.trim.w, m.trim.h, m.trim.r);
    ctx.clip();
    ctx.lineCap = "round";
    for (let i = 0; i < 70; i++) {
      const y = m.trim.y + rnd() * m.trim.h;
      const x0 = m.trim.x + rnd() * m.trim.w * 0.5;
      const len = m.trim.w * (0.18 + rnd() * 0.5);
      ctx.strokeStyle = rgba(rnd() > 0.5 ? p.base[0] : p.base[2], 0.30 + rnd() * 0.25);
      ctx.lineWidth = Math.max(0.4, u * (0.12 + rnd() * 0.3));
      ctx.beginPath();
      ctx.moveTo(x0, y);
      ctx.bezierCurveTo(x0 + len * 0.33, y - u * 0.5, x0 + len * 0.66, y + u * 0.5, x0 + len, y);
      ctx.stroke();
    }
    ctx.restore();
    /* joints de planche : deux traits horizontaux dans la bande basse */
    ctx.save();
    ctx.strokeStyle = rgba(p.base[2], 0.6); ctx.lineWidth = Math.max(0.5, u * 0.22);
    [m.trim.y + m.inner, m.trim.y + m.trim.h - m.inner].forEach((y) => {
      ctx.beginPath(); ctx.moveTo(m.trim.x + m.edge, y); ctx.lineTo(m.trim.x + m.trim.w - m.edge, y); ctx.stroke();
    });
    ctx.restore();
  }
  function famDeco(ctx, m, f) {
    const p = pal(f), u = m.u;
    ctx.save();
    ctx.fillStyle = rgba(p.line, 0.5);
    const cx = m.trim.x + m.trim.w / 2;
    [[m.trim.y + m.edge + u * 0.4, 1], [m.trim.y + m.trim.h - m.edge - u * 0.4, -1]].forEach(([y, dir]) => {
      for (let i = 0; i < 4; i++) {
        const wgt = u * (7 - i * 1.5), hgt = u * 0.55;
        ctx.fillRect(cx - wgt / 2, y + dir * (i * u * 1.0), wgt, dir > 0 ? hgt : -hgt);
      }
    });
    /* eventails de coin */
    ctx.strokeStyle = rgba(p.line, 0.44); ctx.lineWidth = Math.max(0.4, u * 0.2);
    atCorners(ctx, m.outer, () => {
      for (let i = 1; i <= 5; i++) {
        ctx.beginPath(); ctx.arc(0, 0, u * (2 + i * 1.35), 0.06, Math.PI / 2 - 0.06); ctx.stroke();
      }
    });
    ctx.restore();
  }
  function famNeon(ctx, m, f) {
    const p = pal(f), u = m.u;
    ctx.save();
    ctx.shadowColor = rgba(p.glow, 0.9);
    ctx.shadowBlur = u * 1.9;
    ctx.strokeStyle = rgba(p.glow, 0.95); ctx.lineWidth = Math.max(0.5, u * 0.22);
    ctx.beginPath(); chamferPath(ctx, m.band.x, m.band.y, m.band.w, m.band.h, u * 4.5); ctx.stroke();
    ctx.shadowBlur = 0;
    /* PRISES DE CIRCUIT sur les montants. Elles partaient de `trim + edge`,
       c'est-a-dire de l'AXE du filet exterieur, et l'une d'elles tombe pile a
       mi-hauteur (i = 3 donne 0,50 de la bande) : le filet cessait d'avoir une
       arete interieure, et le panneau des octets ne pouvait plus l'isoler du
       tout. Elles partent maintenant de l'arete INTERIEURE du filet, plus un
       jeu — le trait de l'utilisateur reste un trait. */
    ctx.strokeStyle = rgba(p.line, 0.55);
    const dep = m.edge + m.line * 0.5 + u * 0.6;
    for (let i = 0; i < 7; i++) {
      const y = m.band.y + m.band.h * (0.14 + i * 0.12);
      [[m.trim.x + dep, 1], [m.trim.x + m.trim.w - dep, -1]].forEach(([x, d]) => {
        ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + d * m.inner * 0.55, y);
        ctx.lineTo(x + d * m.inner * 0.8, y + u * 0.9); ctx.stroke();
      });
    }
    ctx.restore();
  }
  function famSable(ctx, m, f) {
    const p = pal(f), u = m.u;
    ctx.save();
    ctx.strokeStyle = rgba(p.line, 0.5); ctx.lineWidth = Math.max(0.4, u * 0.16);
    const y = m.win.y + m.win.h + u * 0.9;
    ctx.beginPath(); ctx.moveTo(m.band.x + m.band.w * 0.5 - u * 6, y); ctx.lineTo(m.band.x + m.band.w * 0.5 + u * 6, y); ctx.stroke();
    ctx.restore();
  }
  /* LA SEPTIEME FAMILLE (phase 3a, archetype « Arcane gravee » §6.2-7).
     Ce qu'aucune des six ne savait faire : une marge de PAPIER (les six
     encrent l'anneau depuis `PAL`, dont les six raretes sont sombres) et un
     aplat de couleur au REPERAGE DECALE. Le « double filet 1,5/3 mm » de la
     spec, lui, sortait deja du moteur : `edge_mm 1,5` + `line_mm 0,5` +
     `gap_mm 1,1` posent le second filet a 3,00 mm pile — il n'a donc jamais
     ete la raison de cette famille, et la note de tache le dit. */
  function famGravure(ctx, m, f) {
    const p = pal(f), u = m.u, B = m.band;
    ctx.save();
    /* le cartouche des chiffres romains, en haut de la bande (spec : 4,4 sur
       55 x 8) — un filet double, les capitales espacees viennent de P3. */
    const hy = Math.max(u * 3.5, Math.min(u * 8, m.win.y - B.y - u * 1.4));
    ctx.strokeStyle = rgba(mix(p.base[2], "#000000", 0.35), 0.8);
    ctx.lineWidth = Math.max(0.5, u * 0.2);
    ctx.strokeRect(B.x + u * 0.8, B.y + u * 0.6, B.w - u * 1.6, hy);
    if (hy > u * 2.4) {
      ctx.strokeStyle = rgba(p.gem, 0.6);
      ctx.lineWidth = Math.max(0.4, u * 0.12);
      ctx.strokeRect(B.x + u * 1.4, B.y + u * 1.2, B.w - u * 2.8, hy - u * 1.2);
    }
    /* la taille du burin le long des montants : des hachures serrees en haut,
       ouvertes en bas — ce qu'un graveur fait pour modeler une ombre sans
       demi-teinte, et ce qu'aucune trame de matiere ne rend (elle, elle est
       reguliere par construction). */
    ctx.strokeStyle = rgba(mix(p.base[2], "#000000", 0.12), 0.45);
    ctx.lineWidth = Math.max(0.35, u * 0.1);
    for (let i = 0; i < 26; i++) {
      const t = i / 25, y = B.y + B.h * (0.08 + 0.84 * t), L = u * (2.4 - 1.5 * t);
      [[m.trim.x + m.inner * 0.5, 1], [m.trim.x + m.trim.w - m.inner * 0.5, -1]]
        .forEach((c) => {
          ctx.beginPath();
          ctx.moveTo(c[0], y); ctx.lineTo(c[0] + c[1] * L, y + u * 0.9);
          ctx.stroke();
        });
    }
    ctx.restore();
  }
  const FAM_FN = { runic: famRunic, arcane: famArcane, timber: famTimber, deco: famDeco, neon: famNeon, sable: famSable, gravure: famGravure };

  function atCorners(ctx, r, fn) {
    const cs = [[r.x, r.y, 1, 1], [r.x + r.w, r.y, -1, 1], [r.x, r.y + r.h, 1, -1], [r.x + r.w, r.y + r.h, -1, -1]];
    cs.forEach((c) => { ctx.save(); ctx.translate(c[0], c[1]); ctx.scale(c[2], c[3]); fn(ctx); ctx.restore(); });
  }

  /* ═══════════════════════════════════════════════════════════════════════
     5. ORNEMENTS DE COIN
     ═══════════════════════════════════════════════════════════════════════ */
  function cornerOrn(ctx, m, f) {
    if (f.corner === "none") return;
    const u = m.u;
    const ink = inkPaint(ctx, m, f, false);
    ctx.save();
    ctx.strokeStyle = ink; ctx.fillStyle = ink;
    ctx.lineWidth = Math.max(0.6, m.line * 0.9 || u * 0.3);
    ctx.lineJoin = "round"; ctx.lineCap = "round";
    const off = m.edge + u * 1.6;
    const R = { x: m.trim.x + off, y: m.trim.y + off, w: m.trim.w - 2 * off, h: m.trim.h - 2 * off };
    atCorners(ctx, R, (c) => {
      if (f.corner === "bracket") {
        c.beginPath(); c.moveTo(0, u * 7); c.lineTo(0, 0); c.lineTo(u * 7, 0); c.stroke();
        c.beginPath(); c.moveTo(u * 1.5, u * 4.2); c.lineTo(u * 1.5, u * 1.5); c.lineTo(u * 4.2, u * 1.5); c.stroke();
      } else if (f.corner === "scroll") {
        c.beginPath();
        c.moveTo(0, u * 9);
        c.bezierCurveTo(u * 0.2, u * 3.6, u * 3.6, u * 0.2, u * 9, 0);
        c.stroke();
        c.beginPath();
        c.moveTo(u * 2.2, u * 6.4);
        c.bezierCurveTo(u * 3.2, u * 3.2, u * 3.2, u * 3.2, u * 6.4, u * 2.2);
        c.stroke();
        c.beginPath(); c.arc(u * 2.0, u * 2.0, u * 0.9, 0, Math.PI * 2); c.fill();
      } else if (f.corner === "stud") {
        c.beginPath(); c.arc(u * 2.6, u * 2.6, u * 1.5, 0, Math.PI * 2); c.fill();
        c.save(); c.fillStyle = rgba("#ffffff", 0.4);
        c.beginPath(); c.arc(u * 2.2, u * 2.2, u * 0.5, 0, Math.PI * 2); c.fill(); c.restore();
      } else if (f.corner === "fleuron") {
        c.beginPath();
        c.moveTo(u * 1.2, u * 5.6);
        c.bezierCurveTo(u * 3.4, u * 5.2, u * 5.2, u * 3.4, u * 5.6, u * 1.2);
        c.bezierCurveTo(u * 3.8, u * 2.4, u * 2.4, u * 3.8, u * 1.2, u * 5.6);
        c.fill();
        c.beginPath(); c.arc(u * 1.4, u * 1.4, u * 0.8, 0, Math.PI * 2); c.fill();
      } else if (f.corner === "spike") {
        c.beginPath();
        c.moveTo(0, u * 8); c.lineTo(u * 1.6, u * 1.6); c.lineTo(u * 8, 0);
        c.lineTo(u * 5.4, u * 1.1); c.lineTo(u * 1.1, u * 5.4);
        c.closePath(); c.fill();
      }
    });
    ctx.restore();
  }

  /* ═══════════════════════════════════════════════════════════════════════
     5 bis. LE SCEAU PRISMATIQUE — le contour holographique (spec §6.2bis)
     ───────────────────────────────────────────────────────────────────────
     UNE SEULE SOURCE DE VERITE : le TRACE du contour. Ici il n'y a pas de
     bezier a porter ailleurs — l'anneau de coupe est un rectangle arrondi
     dans les SEPT familles (`rrPath`, la fenetre seule change de forme), donc
     le Sceau se resume a SIX NOMBRES (x, y, w, h, r, largeur). C'est ce qui
     permet aux trois rasterisations de la spec — ecran, masque d'imprimeur,
     texture 3D — de deriver des memes millimetres au lieu de se repasser un
     PNG : « le piege des deux cadres » (§6.2bis) devient inexprimable.

     DETERMINISTE A PHASE FIXEE. La phase du fichier livre est CANONIQUE :
     0,35, et toute sortie de `CF.renderCard` la porte, apercu compris —
     l'utilisateur voit litteralement la frame livree. Aucune horloge, aucun
     pointeur, aucun `Math.random` : la regle du `prng` de la piece, appliquee
     a un champ de paillettes SEME PAR CARTE.

     PORTEE PAR SURFACE (§6.2bis-d) : trois interrupteurs independants. Hors
     de la portee ECRAN le contour ne disparait pas — il retombe dans sa BASE
     CALME, le metal du kind, sans arc-en-ciel. « 3D uniquement » est une
     configuration de premier rang, pas une case oubliee.
     ═══════════════════════════════════════════════════════════════════════ */
  const SEAL_PHASE = 0.35;      /* LA PHASE CANONIQUE — celle du fichier livre */
  const SEAL_STOPS = 12;        /* arrets du degrade arc-en-ciel */
  /* l'axe du degrade, FIXE : il ne suit PAS `grad_angle`. Celui-la incline la
     matiere de la BANDE ; le Sceau est un contour pose par-dessus, et le faire
     tourner avec elle ferait bouger le fichier livre au reglage d'une autre
     grandeur. Un seul reglage, un seul effet. */
  const SEAL_ANGLE = 118;
  const SEAL_SPARKS = 260;      /* points du champ de paillettes */
  const SEAL_HASH_N = 24;       /* paliers de phase du hash d'allumage */
  const SEAL_LIT = 0.62;        /* au-dessus, la paillette s'allume */
  /* le metal de chaque recette, EMPRUNTE a la table deja ecrite : une seconde
     table de couleurs serait une seconde verite. */
  const SEAL_TONE = { argent: "silver", dorure: "gold" };

  /* la portee ECRAN est-elle active ? C'est la seule question que le peintre
     pose : le reste des portees appartient a l'imprimeur et au maillage. */
  function sealLive(f) {
    return !!(f.seal && f.seal.on && f.seal.scope && f.seal.scope.screen);
  }

  /* LES ARRETS DU DEGRADE, a phase donnee. Fonction PURE : c'est elle que le
     banc mesure, et c'est elle que le peintre pose — pas deux formules. */
  function sealStops(f, phase) {
    const out = [];
    if (!sealLive(f)) {
      /* LA BASE CALME : le metal du kind, aux memes cinq positions que
         `metalPaint` et AUX MEMES TONS — une seconde table de couleurs serait
         une seconde verite. Pas d'arc-en-ciel : l'ecran le DIT. */
      const st5 = METAL_STOPS[SEAL_TONE[f.seal.kind]] || METAL_STOPS.silver;
      const ts = [0, 0.22, 0.5, 0.74, 1];
      for (let i = 0; i < st5.length; i++) out.push([ts[i], st5[i]]);
      return out;
    }
    for (let i = 0; i <= SEAL_STOPS; i++) {
      const t = i / SEAL_STOPS;
      /* saturation 70-90 % (spec) : 80 +/- 8, jamais hors de la plage. */
      const sat = 80 + 8 * Math.cos(2 * Math.PI * (t * 3 + phase));
      const lig = 54 + 8 * Math.sin(2 * Math.PI * (t * 2 + phase));
      out.push([r2(t), "hsl(" + r1((((phase + t) * 360) % 360 + 360) % 360)
        + ", " + r1(sat) + "%, " + r1(lig) + "%)"]);
    }
    return out;
  }

  /* LA GRAINE, PAR CARTE (spec §6.2bis-a : « seed = id de carte »).
     La graine est L'IDENTITE de la carte, et rien de plus — CE QU'ELLE VAUT
     DEPEND DONC DE CETTE IDENTITE, ce qu'il faut dire honnetement : quand
     aucune colonne `id` n'est mappee (le DEFAUT), `cards/data.py` assigne un
     identifiant POSITIONNEL — la lettre « c » suivie du rang de la ligne ;
     deplacer une carte change alors son identifiant, donc son scintillement.
     MESURE : sans colonne mappee, 4 cartes sur 4 changent au deplacement ;
     avec, 0 sur 4. Mappez une colonne `id` et le scintillement suit la
     carte — c'est la seule promesse tenable.
     Le repli "c" + (i + 1) ci-dessous est du code MORT en pratique
     (`normCard` du CORE et `data.py` fournissent tous deux un id) : il est la
     pour qu'un `card` nu passe au banc, jamais pour servir en production.
     Ce qui reste vrai sans condition : ce n'est JAMAIS une constante — 200
     contours qui scintillent au meme endroit, ce n'est plus un foil, c'est un
     motif. */
  function sealSeed(card) {
    const i = (card && isFinite(Number(card.i))) ? (Number(card.i) | 0) : 0;
    const id = (card && typeof card.id === "string" && card.id) ? card.id : ("c" + (i + 1));
    let a = 2166136261;
    for (let k = 0; k < id.length; k++) { a ^= id.charCodeAt(k); a = Math.imul(a, 16777619) >>> 0; }
    return a >>> 0;
  }
  /* le champ de points, en coordonnees NORMALISEES [0, 1[ de la boite de
     l'anneau : il ne depend QUE de la graine, donc deux formats de carte
     portent le meme scintillement au meme endroit relatif.
     LA SPEC NOMME `mulberry32`, LA PIECE LIVRE `prng` (xorshift32) : meme
     famille de generateurs seedes, et c'est la REGLE DE LA PIECE qui prime —
     un second generateur dans le meme fichier serait une seconde source de
     hasard a auditer. Ce que la spec exige est l'esprit (seede, jamais
     `Math.random`), pas la marque. */
  function sealField(seed, n) {
    const rnd = prng(seed);
    const out = [];
    for (let i = 0; i < n; i++) out.push({ u: rnd(), v: rnd(), s: 0.3 + rnd() * 0.8 });
    return out;
  }
  /* l'allumage : hash(x, y, palier de phase). Le meme point s'allume ou non
     selon la phase — mais la phase du fichier est canonique, donc le fichier
     porte toujours le meme scintillement. */
  function sealSpark(u, v, k) {
    let a = 2166136261;
    a ^= Math.round(u * 65535) & 65535; a = Math.imul(a, 16777619) >>> 0;
    a ^= Math.round(v * 65535) & 65535; a = Math.imul(a, 16777619) >>> 0;
    a ^= (k | 0); a = Math.imul(a, 16777619) >>> 0;
    return (a >>> 8) / 16777216;
  }

  /* L'ANNEAU, EN PIXELS DE TOILE — la meme source de chemin que le filet
     exterieur (`m.outer`), dilatee vers l'INTERIEUR de `width_mm`. Rend
     `null` quand la largeur ne laisse plus d'anneau : mieux vaut ne rien
     peindre qu'un rectangle retourne (le defaut de `micro`, BAND_MIN_MM). */
  function sealRing(g, m, f) {
    const cap = capOf(g);
    const wmax = sealMaxMM(g.trim_mm[0], g.trim_mm[1], Math.min(f.edge_mm, cap), m.wm);
    const wmm = Math.min(num(f.seal.width_mm, SEAL_DEFAULTS.width_mm), wmax);
    const t = wmm * m.u;
    const O = m.outer;
    if (!(t > 0) || O.w - 2 * t <= 0 || O.h - 2 * t <= 0) return null;
    return {
      mm: r2(wmm), max_mm: wmax, t: t,
      x: O.x, y: O.y, w: O.w, h: O.h, r: O.r,
      ix: O.x + t, iy: O.y + t, iw: O.w - 2 * t, ih: O.h - 2 * t,
      ir: Math.max(0, O.r - t),
    };
  }

  /* LE PEINTRE. Pile de la spec §6.2bis-a : clip du contour (deux `rrPath`
     en pair-impair) → base arc-en-ciel (ou calme hors portee ecran) → bande
     de reflet blanc-transparent en `overlay` → paillettes au PRNG seme,
     allumees par hash(x, y, palier de phase). Les deux dernieres n'existent
     QUE dans la portee ecran : hors d'elle le contour est un metal, et la
     couche cadre reste source-over pure. */
  function paintSeal(ctx, g, m, f, card) {
    if (!f.seal || !f.seal.on) return;
    const ring = sealRing(g, m, f);
    if (!ring) return;
    ctx.save();
    ctx.beginPath();
    rrPath(ctx, ring.x, ring.y, ring.w, ring.h, ring.r);
    rrPath(ctx, ring.ix, ring.iy, ring.iw, ring.ih, ring.ir);
    ctx.clip("evenodd");   /* CF-SCEAU-CLIP */
    const a = SEAL_ANGLE * Math.PI / 180, L = Math.max(m.W, m.H);
    const cx = m.W / 2, cy = m.H / 2;
    const gr = ctx.createLinearGradient(cx - Math.cos(a) * L / 2, cy - Math.sin(a) * L / 2,
      cx + Math.cos(a) * L / 2, cy + Math.sin(a) * L / 2);
    const stops = sealStops(f, SEAL_PHASE);
    for (let i = 0; i < stops.length; i++) gr.addColorStop(stops[i][0], stops[i][1]);
    ctx.fillStyle = gr;
    /* le remplissage part du bord de TOILE : l'anneau porte donc son fond
       perdu comme le reste du cadre (la regle du §4 « fond perdu »). */
    ctx.fillRect(0, 0, m.W, m.H);
    if (sealLive(f)) {
      ctx.save();
      ctx.globalCompositeOperation = "overlay";
      const b0 = (SEAL_PHASE * 1.4) % 1;
      const bg = ctx.createLinearGradient(0, m.H * (b0 - 0.34), 0, m.H * (b0 + 0.34));
      bg.addColorStop(0, "rgba(255,255,255,0)");
      bg.addColorStop(0.5, "rgba(255,255,255,.72)");
      bg.addColorStop(1, "rgba(255,255,255,0)");
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, m.W, m.H);
      ctx.restore();
      const pts = sealField(sealSeed(card), SEAL_SPARKS);
      const k = Math.floor(SEAL_PHASE * SEAL_HASH_N);
      ctx.fillStyle = "#ffffff";
      for (let i = 0; i < pts.length; i++) {
        const p = pts[i];
        const lit = sealSpark(p.u, p.v, k);
        if (lit <= SEAL_LIT) continue;
        ctx.globalAlpha = (lit - SEAL_LIT) / (1 - SEAL_LIT);
        ctx.beginPath();
        ctx.arc(ring.x + p.u * ring.w, ring.y + p.v * ring.h,
          Math.max(0.4, p.s * m.u * 0.2), 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    }
    ctx.restore();
  }

  /* ═══════════════════════════════════════════════════════════════════════
     6. LE RECTO — z = 40
     ═══════════════════════════════════════════════════════════════════════ */
  function artOf(card, d) {
    if (card && card.art) return card.art;
    if (card && card.fields && card.fields.art) return card.fields.art;
    const dv = d && d.face ? d.face.default_art : "";
    return dv || "";
  }

  function paintFront(ctx, g, f, card, d) {
    if (f.family === "none") return;
    const m = model(g, f), p = pal(f), u = m.u;
    const shape = WIN_SHAPE[f.family] || "rect";
    const plan = planOf(g, f);

    /* 1. le corps : TOUT sauf la fenetre — fond perdu compris (la decoupe
       vient apres l'impression, l'encre doit aller jusqu'au bord de toile). */
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, m.W, m.H);
    winPath(ctx, m, shape);
    ctx.fillStyle = bandPaint(ctx, m, f);
    ctx.fill("evenodd");
    ctx.restore();

    /* 2. la signature de la famille */
    ctx.save();
    ctx.beginPath(); ctx.rect(0, 0, m.W, m.H); winPath(ctx, m, shape);
    ctx.clip("evenodd");
    famProfile(ctx, m, f);
    const fn = FAM_FN[f.family];
    if (fn) fn(ctx, m, f);
    /* la matiere par-dessus le profil, sous la moulure : elle doit passer sur
       les masses de la bande, sinon ce sont deux aplats voisins. */
    matter(ctx, m, f, shape);
    winMoulding(ctx, m, f, shape);
    ctx.restore();

    /* 3. la plaque de texte (P3 ecrit dessus a z=60) — sa FORME appartient a
       la famille : c'est la troisieme des quatre signatures. */
    if (f.plate && m.plate.h > u * 6) {
      ctx.save();
      ctx.globalAlpha = f.plate_alpha;
      const gr = ctx.createLinearGradient(0, m.plate.y, 0, m.plate.y + m.plate.h);
      gr.addColorStop(0, mix(p.plate, "#ffffff", 0.10));
      gr.addColorStop(1, p.plate);
      ctx.fillStyle = gr;
      platePath(ctx, m, f);
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.strokeStyle = rgba(p.line, 0.35); ctx.lineWidth = Math.max(0.5, u * 0.16);
      platePath(ctx, m, f); ctx.stroke();
      plateTrim(ctx, m, f);
      ctx.restore();
    }

    /* 4. reserve d'illustration : seulement s'il n'y a AUCUNE illustration.
       Elle disparait des que P1 en pose une — la piece se demontre seule
       sans jamais recouvrir le travail d'une autre. */
    if (!artOf(card, d)) {
      ctx.save();
      ctx.beginPath(); winPath(ctx, m, shape); ctx.clip();
      const gr = ctx.createLinearGradient(m.win.x, m.win.y, m.win.x, m.win.y + m.win.h);
      gr.addColorStop(0, mix(p.base[2], "#ffffff", 0.16));
      gr.addColorStop(1, mix(p.base[2], "#000000", 0.25));
      ctx.fillStyle = gr; ctx.fillRect(m.win.x, m.win.y, m.win.w, m.win.h);
      ctx.strokeStyle = rgba(p.glow, 0.16); ctx.lineWidth = Math.max(0.5, u * 0.14);
      for (let x = m.win.x - m.win.h; x < m.win.x + m.win.w; x += u * 4) {
        ctx.beginPath(); ctx.moveTo(x, m.win.y + m.win.h); ctx.lineTo(x + m.win.h, m.win.y); ctx.stroke();
      }
      ctx.restore();
    }

    /* 5. ombre portee du cadre sur l'illustration : elle « assoit » la face */
    ctx.save();
    ctx.beginPath(); winPath(ctx, m, shape); ctx.clip();
    ctx.shadowColor = "rgba(0,0,0,.55)"; ctx.shadowBlur = u * 2.2;
    ctx.strokeStyle = "rgba(0,0,0,.5)"; ctx.lineWidth = u * 1.2;
    ctx.beginPath(); winPath(ctx, m, shape); ctx.stroke();
    ctx.restore();

    /* 6. LES FILETS, ET LE SCEAU QUI PASSE DESSOUS.
          Le Sceau partage la source de chemin du filet exterieur (`m.outer`),
          et il se peint AVANT lui : le filet garde ainsi son arete nette POSEE
          SUR la bande holographique, au lieu d'etre a moitie recouvert. Deux
          reglages independants qui se lisent l'un sur l'autre.
          L'exterieur epouse le rayon de coupe, l'interieur borde la fenetre.
          Epaisseur = line_mm, convertie une seule fois. */
    paintSeal(ctx, g, m, f, card);
    if (m.line > 0) {
      const ink = inkPaint(ctx, m, f, false);
      ctx.save();
      ctx.strokeStyle = ink; ctx.lineWidth = m.line;
      ctx.beginPath(); rrPath(ctx, m.outer.x, m.outer.y, m.outer.w, m.outer.h, m.outer.r); ctx.stroke();
      if (f.double && m.gap > 0) {
        const o2 = m.edge + m.line * 0.5 + m.gap + m.line * 0.3;
        ctx.lineWidth = Math.max(0.4, m.line * 0.55);
        ctx.beginPath(); rrPath(ctx, m.trim.x + o2, m.trim.y + o2, m.trim.w - 2 * o2, m.trim.h - 2 * o2,
          Math.max(0, m.trim.r - o2)); ctx.stroke();
      }
      ctx.strokeStyle = inkPaint(ctx, m, f, true);
      ctx.lineWidth = Math.max(0.5, m.line * 0.8);
      ctx.beginPath(); winPath(ctx, m, shape); ctx.stroke();
      ctx.restore();
    }

    /* 7. ornements de coin */
    cornerOrn(ctx, m, f);

    /* 8. LES LOGEMENTS ET LES SOCLES — couche 40, donc SOUS le texte de P3.
       C'est ici que le cadre cesse d'etre un decor et devient une mise en
       page : une mention posee sur l'illustration recoit une plaque de fond
       (sans elle, « CREATURE LEGENDAIRE » ne tient que parce que le dessin de
       test est sombre) ; une mention qui deborde de la bande sur l'anneau
       recoit un logement (les chiffres cessent de chevaucher le filet). */
    paintSeats(ctx, m, f, plan);
  }

  /* socles + logements + gemme rangee en logement : tout ce qui passe SOUS le
     texte. Un meuble dessine ici ne peut, par construction, masquer aucune
     mention. */
  function paintSeats(ctx, m, f, plan) {
    const p = pal(f), u = m.u, mmx = (v) => m.trim.x + v * u, mmy = (v) => m.trim.y + v * u;
    plan.boxes.forEach((b) => {
      if (b.z !== 40 || b.id === "window") return;
      const x = mmx(b.box[0]), y = mmy(b.box[1]), w = b.box[2] * u, hh = b.box[3] * u;
      ctx.save();
      if (b.id === "gem") {
        /* la gemme devenue logement : un ecrin, sous le chiffre. Disque si la
           mention est a peu pres carree, cartouche sinon — un disque
           circonscrit a une signature de 17 x 3,7 mm sortirait de la carte. */
        const cx = mmx(b.cx), cy = mmy(b.cy), R = b.r * u;
        const rg = ctx.createRadialGradient(cx - R * 0.35, cy - R * 0.45, R * 0.08, cx, cy, R);
        rg.addColorStop(0, mix(p.gem, "#ffffff", 0.35));
        rg.addColorStop(0.6, mix(p.gem, "#000000", 0.35));
        rg.addColorStop(1, mix(p.base[2], "#000000", 0.2));
        const path = () => {
          ctx.beginPath();
          if (b.shape === "rect") rrPath(ctx, x, y, w, hh, Math.min(u * 1.6, hh / 2));
          else ctx.arc(cx, cy, R, 0, Math.PI * 2);
        };
        ctx.globalAlpha = f.socle_alpha;
        ctx.fillStyle = rg;
        path(); ctx.fill();
        ctx.globalAlpha = 1;
        ctx.strokeStyle = f.metal ? metalPaint(ctx, m, f, false) : lineInk(f);
        ctx.lineWidth = Math.max(0.7, u * 0.4);
        path(); ctx.stroke();
      } else if (b.id.indexOf("seat:") === 0) {
        ctx.globalAlpha = f.socle_alpha;
        const gr = ctx.createLinearGradient(0, y, 0, y + hh);
        gr.addColorStop(0, mix(p.base[2], "#000000", 0.35));
        gr.addColorStop(1, mix(p.base[1], "#000000", 0.1));
        ctx.fillStyle = gr;
        ctx.beginPath(); rrPath(ctx, x, y, w, hh, Math.min(u * 1.4, hh / 2)); ctx.fill();
        ctx.globalAlpha = 1;
        ctx.strokeStyle = f.metal ? metalPaint(ctx, m, f, true) : rgba(p.line, 0.75);
        ctx.lineWidth = Math.max(0.5, u * 0.24);
        ctx.beginPath(); rrPath(ctx, x, y, w, hh, Math.min(u * 1.4, hh / 2)); ctx.stroke();
      } else {
        ctx.globalAlpha = f.socle_alpha;
        ctx.fillStyle = mix(p.plate, "#000000", 0.12);
        ctx.beginPath(); rrPath(ctx, x, y, w, hh, Math.min(u * 1.1, hh / 2)); ctx.fill();
        ctx.globalAlpha = 1;
        ctx.strokeStyle = rgba(p.line, 0.3); ctx.lineWidth = Math.max(0.4, u * 0.14);
        ctx.beginPath(); rrPath(ctx, x, y, w, hh, Math.min(u * 1.1, hh / 2)); ctx.stroke();
      }
      ctx.restore();
    });
  }

  /* ═══════════════════════════════════════════════════════════════════════
     7. LE VERSO — z = 40 lui aussi ; c'est une AUTRE face, pas une couche
     ═══════════════════════════════════════════════════════════════════════ */
  function backOf(f, card) {
    if (!f.back_same && card && card.back && byId(BACKS, card.back)) return card.back;
    return f.back;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     7bis. LE VERSO PERSONNALISE (spec §6.2ter) — une image importee, plus
     une PILE ORDONNEE de calques. La premiere de P2.
     ═══════════════════════════════════════════════════════════════════════ */
  /* le nom de fichier derriere une source de document (`img:img_3.png`). */
  function backFile(src) {
    const s = String(src || "");
    return s.indexOf("img:") === 0 ? s.slice(4) : "";
  }
  /* les fichiers que le verso demande, SANS DOUBLON et dans l'ordre : c'est
     ce que le painter attend avant de peindre. */
  function backFiles(f) {
    const out = [];
    const add = (src) => {
      const fl = backFile(src);
      if (fl && out.indexOf(fl) < 0) out.push(fl);
    };
    add(f.back_image);
    const L = Array.isArray(f.back_layers) ? f.back_layers : [];
    for (let i = 0; i < L.length; i++) add(L[i] && L[i].src);
    return out;
  }

  /* ── LES IMAGES DU VERSO, CHARGEES UNE FOIS ──────────────────────────────
     Patron `IMGS` de mod-type (3b-T2), repris a l'identique et pour les memes
     raisons : le painter tourne a chaque frame, sans ce cache chaque frame
     redecoderait le PNG.

     L'ETAT EST RESOLU, JAMAIS REJETE. Une entree vaut `{img, ok}` : `ok:false`
     dit « ce fichier n'est pas arrive », ce qui est un ETAT de la carte (le
     damier), pas une panne du painter. Une promesse rejetee traverserait le
     painter et noircirait l'ecran des sept autres pieces.

     LA CLE EST LE SEUL NOM DE FICHIER, et ce n'est pas un oubli : `img_1.png`
     existe dans TOUS les jeux. Ce qui empeche le melange n'est pas ici — c'est
     `galGo()` du CORE, qui RECHARGE la page a chaque changement de jeu
     (`location.assign`, repli `location.reload`) : le cache meurt avec elle.
     Un test epingle ce fait chez le CORE ; le jour ou il echangerait le
     document en place, il rougit, et c'est la qu'une cle de jeu s'ajoute. */
  const BIMGS = new Map();          /* fichier -> {img, ok} ou Promise */
  const IMG_WAIT_MS = 2500;         /* le painter a 4 s : on garde de la marge */
  function backImgRec(file) {
    const v = BIMGS.get(file);
    return (v && !v.then) ? v : null;
  }
  function loadBackImg(file) {
    const known = BIMGS.get(file);
    if (known) return known.then ? known : Promise.resolve(known);
    let res = null;
    /* LA PROMESSE ENTRE DANS LE CACHE AVANT QUE LE CHARGEMENT COMMENCE, et
       l'ETAT ne la remplace qu'a la resolution : un echec SYNCHRONE ecrivait
       sinon l'etat, que le `set` d'apres ecrasait par la promesse — le cache
       ne rendait plus jamais d'etat lisible et le dos restait au damier pour
       toujours (le piege paye en 3b). */
    const p = new Promise((r) => { res = r; }).then((rec) => {
      BIMGS.set(file, rec);
      /* ARRIVEE TARDIVE : la course du painter est peut-etre finie et la carte
         peinte sans l'image. On redemande un rendu — sous garde : seulement si
         le verso VIVANT porte encore ce fichier. Le CORE coalesce. */
      if (rec.ok && backFiles(f()).indexOf(file) >= 0) M.invalidate();
      return rec;
    });
    BIMGS.set(file, p);
    let done = false;
    const fin = (ok, im) => {
      if (done) return;
      done = true;
      res({ img: ok ? im : null, ok: ok, file: file });
    };
    let url = "";
    try { url = M.api.url("image/" + encodeURIComponent(file)); }
    catch (e) { fin(false, null); return p; }
    const im = new Image();
    im.decoding = "sync";
    im.onload = () => fin(true, im);
    im.onerror = () => fin(false, null);
    im.src = url;
    return p;
  }
  function ensureBackImgs(files) {
    const todo = files.filter((x) => x && !backImgRec(x));
    if (!todo.length) return Promise.resolve();
    const all = Promise.all(todo.map(loadBackImg));
    return Promise.race([all, new Promise((r) => setTimeout(r, IMG_WAIT_MS))]);
  }

  /* LE CADRAGE « COVER », DEPUIS LE BORD DE TOILE et non depuis la coupe.
     La decoupe vient APRES l'impression : une image calee sur la seule rogne
     laisserait la matiere de bande dans les 3 mm de fond perdu, et un massicot
     decale d'un millimetre poserait ce lisere sur le bord de la carte livree.
     La toile CONTIENT la coupe, donc couvrir la toile couvre la coupe — c'est
     la meme regle que le remplissage de l'anneau du Sceau et que les motifs du
     catalogue, qui courent jusqu'au bord de fichier. */
  function backCover(sw, sh, W, H) {
    if (!(sw > 0) || !(sh > 0)) return [0, 0, W, H];
    const k = Math.max(W / sw, H / sh);
    const w = sw * k, h = sh * k;
    return [(W - w) / 2, (H - h) / 2, w, h];
  }

  /* LE DAMIER — l'etat « ce fichier n'est pas arrive », peint DANS LE FICHIER
     LIVRE et c'est voulu (patron de mod-type) : un trou laisserait partir une
     carte incomplete sans un mot, alors qu'un damier nomme est impossible a ne
     pas voir sur une epreuve. Une source VIDE, elle, ne salit rien — c'est un
     dos qu'on vient de choisir, et le panneau le montre deja.
     LA POLICE est la meme pile systeme que le nom du jeu au dos, deux lignes
     plus bas : P2 n'a pas de chargeur de fontes, et en ajouter un pour un etat
     d'erreur serait une seconde source de fontes a auditer. */
  function backDamier(ctx, x, y, w, h, file) {
    if (!(w > 0) || !(h > 0)) return;
    ctx.save();
    ctx.fillStyle = "#241f2b";
    ctx.fillRect(x, y, w, h);
    ctx.fillStyle = "#39323f";
    const n = Math.max(6, Math.round(Math.min(w, h) / 18));
    for (let j = 0; j < h; j += n) {
      for (let i = 0; i < w; i += n) {
        if ((((i / n) | 0) + ((j / n) | 0)) % 2) continue;
        ctx.fillRect(x + i, y + j, Math.min(n, w - i), Math.min(n, h - j));
      }
    }
    if (file) {
      ctx.fillStyle = "#e6dfd4";
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.font = "600 " + Math.max(8, Math.round(Math.min(w / 12, h / 3)))
        + 'px "Segoe UI", system-ui, sans-serif';
      ctx.fillText(file, x + w / 2, y + h / 2);
    }
    ctx.restore();
  }

  /* ── UN CALQUE, ET LE MULTIPLY CUIT DANS SES PIXELS ──────────────────────
     LE MECANISME, ET POURQUOI IL EST ECRIT AINSI. La preuve d'empilement de
     §4.2 juge une couche en la re-empilant en `source-over` : tout mode de
     fusion VIVANT pose sur la toile du CORE rend le resultat dependant de ce
     qui est dessous, et la couche « cadre » bascule alors en « empreinte »
     (une couche cuite, qu'on ne peut plus deplacer). Le `multiply` est donc
     calcule DANS LES PIXELS du calque, sur une toile de cuisson a part, puis
     pose en `source-over` : le compositeur du CORE ne recoit jamais autre
     chose que du source-over.

     LA FORMULE est celle du canvas, pas une approximation :
         cuit = Cs x (1 - alphaFond) + (Cs x Cfond) x alphaFond
     — le fond compte pour ce qu'il PESE. Sans le terme de gauche, multiplier
     par un fond ABSENT donnerait du NOIR (tout x 0 = 0), et le rendu par
     couches de P9, qui peint sur toile TRANSPARENTE a chaque appel, sortirait
     un verso noir. Sur le verso, `paintBack` remplit la toile avant d'appeler
     ici, donc le fond est opaque et le terme vaut zero — mais la propriete ne
     doit pas dependre de ce fait-la.

     CE QUE LA PRECOMPOSITION N'ACHETE PAS, ET C'EST MESURE. Elle ne change
     AUCUN PIXEL : un `globalCompositeOperation = "multiply"` vif donnerait
     exactement les memes octets, sur fond opaque comme sur fond transparent
     (banc RGBA, meme empreinte des deux cotes). Elle n'ameliore donc pas le
     VERDICT de la preuve d'empilement — sur ce verso-la, les deux ecritures
     rendent une couche « isolee ». Ce qu'elle achete est la SUITE
     D'OPERATIONS : la couche du cadre ne demande jamais au compositeur autre
     chose que du source-over, et c'est cela que §4.2 sait verifier (son banc
     REFUSE un mode qu'il ne modelise pas — un banc qui devine rend un verdict
     qui ne vaut rien) et que verifiera tout lecteur du flux d'operations. La
     phrase tenable est donc celle-la, pas « sans elle la preuve tombe ». Un
     test epingle l'egalite des pixels pour que cette phrase ne pourrisse pas.

     COUT ASSUME : une relecture de toile pleine par calque a multiply (borne
     a six). La toile de cuisson est REUTILISEE d'un calque a l'autre — lui
     re-affecter sa largeur l'efface, dans un navigateur comme au banc — et
     relachee a la fin, au patron de `release()` de core.js. */
  function drawBackLayer(ctx, m, l, get, cache) {
    const file = backFile(l && l.src);
    if (!file) return;                    /* calque qui vient de naitre */
    const op = cl(num(l.opacity, 1), 0, 1);
    const rec = get(file);
    if (!rec || !rec.ok || !rec.img) {
      /* un calque dont le FICHIER manque : le damier, dans la boite qu'il
         aurait occupee — pas sur toute la carte, sinon on effacerait l'image
         de fond qui, elle, est peut-etre la. */
      const b = backLayerRect(m, l, 1, 1);
      backDamier(ctx, b[0], b[1], b[2], b[3], file);
      return;
    }
    if (!(op > 0)) return;
    const b = backLayerRect(m, l, rec.img.width, rec.img.height);
    if (!(b[2] > 0) || !(b[3] > 0)) return;
    if (l.blend === "multiply") {
      const off = cache.off || (cache.off = document.createElement("canvas"));
      off.width = m.W; off.height = m.H;   /* re-affecter la largeur EFFACE */
      const oc = off.getContext("2d");
      oc.drawImage(rec.img, b[0], b[1], b[2], b[3]);
      const L = oc.getImageData(0, 0, m.W, m.H);
      const B = ctx.getImageData(0, 0, m.W, m.H);
      const a = L.data, d = B.data;
      for (let i = 0; i < a.length; i += 4) {
        const ab = d[i + 3] / 255;
        a[i] = Math.round(a[i] * (1 - ab) + a[i] * d[i] / 255 * ab);
        a[i + 1] = Math.round(a[i + 1] * (1 - ab) + a[i + 1] * d[i + 1] / 255 * ab);
        a[i + 2] = Math.round(a[i + 2] * (1 - ab) + a[i + 2] * d[i + 2] / 255 * ab);
      }
      oc.putImageData(L, 0, 0);
      ctx.save();
      ctx.globalAlpha = op;
      ctx.drawImage(off, 0, 0);
      ctx.restore();
      return;
    }
    ctx.save();
    ctx.globalAlpha = op;
    ctx.drawImage(rec.img, b[0], b[1], b[2], b[3]);
    ctx.restore();
  }
  /* la boite d'un calque : le cadrage « cover » de la toile, mis a l'echelle
     AUTOUR DU CENTRE — un calque a 0,5 laisse voir ce qu'il y a dessous sur
     tout le pourtour, un calque a 2 deborde de partout. */
  function backLayerRect(m, l, sw, sh) {
    const sc = cl(num(l && l.scale, 1), LIMITS.back_scale[0], LIMITS.back_scale[1]);
    const c = backCover(sw, sh, m.W, m.H);
    const w = c[2] * sc, h = c[3] * sc;
    return [(m.W - w) / 2, (m.H - h) / 2, w, h];
  }

  /* LE PEINTRE DU VERSO PERSONNALISE. `get` rend l'etat d'un fichier
     (`{img, ok}` ou null) : il est passe en PARAMETRE plutot que lu dans le
     cache du module, ce qui rend ce peintre jouable au banc sur un contexte
     raster minimal — le meme code que le fichier livre. */
  function paintBackCustom(ctx, m, f, get) {
    const cache = {};
    const file = backFile(f.back_image);
    if (file) {
      const rec = get(file);
      if (rec && rec.ok && rec.img) {
        const c = backCover(rec.img.width, rec.img.height, m.W, m.H);
        ctx.drawImage(rec.img, c[0], c[1], c[2], c[3]);
      } else {
        backDamier(ctx, 0, 0, m.W, m.H, file);
      }
    }
    const L = Array.isArray(f.back_layers) ? f.back_layers : [];
    for (let i = 0; i < L.length && i < BACK_LAYERS_MAX; i++) {
      drawBackLayer(ctx, m, L[i], get, cache);
    }
    /* la toile de cuisson relachee tout de suite, sans attendre le ramasse-
       miettes : en tarot 600 DPI elle pese ~21 Mo (regle de `release`,
       core.js). */
    if (cache.off) { cache.off.width = 0; cache.off.height = 0; }
  }
  function paintBack(ctx, g, f, card, d) {
    if (f.family === "none") return;
    const m = model(g, f), p = pal(f), u = m.u;
    const kind = backOf(f, card);
    ctx.save();
    ctx.fillStyle = bandPaint(ctx, m, f);
    ctx.fillRect(0, 0, m.W, m.H);
    ctx.restore();

    /* LE DOS AUSSI SORT DE LA ROGNE. Le motif etait decoupe sur la coupe : le
       verso livre avait donc, lui aussi, 3 mm de fond perdu qui ne prolongeait
       pas la carte. Le decoupage porte sur la TOILE et les motifs repetes
       courent jusqu'au bord de fichier. */
    ctx.save();
    ctx.beginPath(); ctx.rect(0, 0, m.W, m.H); ctx.clip();
    const ink = rgba(p.line, 0.4);
    ctx.strokeStyle = ink; ctx.lineWidth = Math.max(0.5, u * 0.2);
    const cx = m.trim.x + m.trim.w / 2, cy = m.trim.y + m.trim.h / 2;
    if (kind === "lattice") {
      const s = u * 5;
      for (let x = -m.H; x < m.W + m.H; x += s) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x + m.H, m.H); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x, m.H); ctx.lineTo(x + m.H, 0); ctx.stroke();
      }
    } else if (kind === "guilloche") {
      for (let k = 0; k < 34; k++) {
        const a = k / 34 * Math.PI * 2;
        ctx.beginPath();
        ctx.ellipse(cx + Math.cos(a) * u * 5, cy + Math.sin(a) * u * 5, m.trim.w * 0.31, m.trim.w * 0.16, a, 0, Math.PI * 2);
        ctx.stroke();
      }
    } else if (kind === "sunburst") {
      for (let k = 0; k < 48; k++) {
        const a = k / 48 * Math.PI * 2;
        ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * u * 6, cy + Math.sin(a) * u * 6);
        ctx.lineTo(cx + Math.cos(a) * (m.W + m.H), cy + Math.sin(a) * (m.W + m.H)); ctx.stroke();
      }
    } else if (kind === "scales") {
      const s = u * 4.4;
      for (let y = m.trim.y % (s * 0.62) - s, row = 0; y < m.H + s; y += s * 0.62, row++) {
        for (let x = -s; x < m.W + s; x += s) {
          ctx.beginPath(); ctx.arc(x + (row % 2 ? s / 2 : 0), y, s * 0.5, Math.PI, 0); ctx.stroke();
        }
      }
    } else if (kind === "chevron") {
      const s = u * 5.2;
      for (let y = m.trim.y % s - s; y < m.H + s; y += s) {
        ctx.beginPath();
        for (let x = -s; x < m.W + s; x += s) {
          ctx.moveTo(x, y); ctx.lineTo(x + s / 2, y + s * 0.45); ctx.lineTo(x + s, y);
        }
        ctx.stroke();
      }
    } else if (kind === "custom") {
      /* LE VERSO PERSONNALISE prend la place du MOTIF, pas celle du cadre :
         les filets, les ornements de coin et le nom du jeu (qui a son propre
         interrupteur) restent. Il est peint AVANT `matter()` parce que le
         carton est le meme des deux cotes de la carte — sa matiere passe donc
         sur l'illustration du dos exactement comme elle passe sur les motifs
         du catalogue. */
      paintBackCustom(ctx, m, f, backImgRec);
    } else if (kind === "runes") {
      const rr = prng(4242), s = u * 7;
      for (let y = m.trim.y % s; y < m.H; y += s) {
        for (let x = m.trim.x % s; x < m.W - s * 0.3; x += s) {
          ctx.beginPath();
          const n = 2 + Math.floor(rr() * 3);
          for (let i = 0; i < n; i++) {
            ctx.moveTo(x + (rr() - 0.5) * s * 0.6, y + (rr() - 0.5) * s * 0.6);
            ctx.lineTo(x + (rr() - 0.5) * s * 0.6, y + (rr() - 0.5) * s * 0.6);
          }
          ctx.stroke();
        }
      }
    } else {  /* mirror : la meme bande que le recto, fenetre pleine */
      famProfile(ctx, m, f);
      const fam = FAM_FN[f.family];
      if (fam) fam(ctx, m, f);
    }
    /* le verso porte la MEME matiere que le recto : deux faces d'une meme
       carte imprimee sur le meme carton. Sans cela, le dos sortait plus plat
       que la face — et c'est le dos qu'on voit le plus souvent sur une table. */
    matter(ctx, m, f, "rect");
    ctx.restore();

    /* medaillon central — MEUBLE DU CATALOGUE, donc absent du verso
       personnalise : le poser au milieu de l'image de l'utilisateur serait
       une decoration qu'il n'a pas demandee, et rien pour la retirer. */
    if (kind !== "custom") {
      ctx.save();
      const R = Math.min(m.trim.w, m.trim.h) * 0.19;
      const rg = ctx.createRadialGradient(cx - R * 0.3, cy - R * 0.4, R * 0.1, cx, cy, R);
      rg.addColorStop(0, mix(p.base[0], "#ffffff", 0.22));
      rg.addColorStop(1, p.base[2]);
      ctx.fillStyle = rg;
      ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = f.metal ? metalPaint(ctx, m, f, false) : lineInk(f);
      ctx.lineWidth = Math.max(0.8, m.line || u * 0.4);
      ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.stroke();
      ctx.beginPath(); ctx.arc(cx, cy, R * 0.78, 0, Math.PI * 2); ctx.stroke();
      ctx.fillStyle = rgba(p.gem, 0.92);
      for (let k = 0; k < 8; k++) {
        const a = k / 8 * Math.PI * 2;
        ctx.beginPath(); ctx.arc(cx + Math.cos(a) * R * 0.5, cy + Math.sin(a) * R * 0.5, R * 0.09, 0, Math.PI * 2); ctx.fill();
      }
      ctx.restore();
    }

    /* filets du dos : le meme reglage que le recto, la meme conversion */
    if (m.line > 0) {
      ctx.save();
      ctx.strokeStyle = inkPaint(ctx, m, f, false); ctx.lineWidth = m.line;
      ctx.beginPath(); rrPath(ctx, m.outer.x, m.outer.y, m.outer.w, m.outer.h, m.outer.r); ctx.stroke();
      if (f.double && m.gap > 0) {
        const o2 = m.edge + m.line * 0.5 + m.gap + m.line * 0.3;
        ctx.lineWidth = Math.max(0.4, m.line * 0.55);
        ctx.beginPath(); rrPath(ctx, m.trim.x + o2, m.trim.y + o2, m.trim.w - 2 * o2, m.trim.h - 2 * o2, Math.max(0, m.trim.r - o2)); ctx.stroke();
      }
      ctx.restore();
    }
    cornerOrn(ctx, m, f);

    if (f.back_label) {
      const name = String((d && d.name) || "").trim();
      if (name) {
        ctx.save();
        ctx.fillStyle = rgba(p.line, 0.72);
        ctx.textAlign = "center"; ctx.textBaseline = "alphabetic";
        ctx.font = "600 " + Math.max(6, u * 2.2) + 'px "Segoe UI", system-ui, sans-serif';
        try { ctx.letterSpacing = (u * 0.35) + "px"; } catch (e) { /* moteur ancien */ }
        ctx.fillText(name.toUpperCase().slice(0, 28), cx, m.trim.y + m.trim.h - m.inner - u * 1.2);
        ctx.restore();
      }
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     8. ORNEMENTS DE DESSUS — z = 70 (par-dessus le texte de P3)
     ═══════════════════════════════════════════════════════════════════════ */
  function paintTop(ctx, g, f, card, side) {
    if (f.family === "none") return;
    const m = model(g, f), p = pal(f), u = m.u;
    if (side === "back") return;
    /* LES PLACEMENTS VIENNENT DU PLAN, pas d'une constante. C'est ce qui rend
       « le ruban ne mange plus la signature » vrai dans le FICHIER, pas
       seulement a l'ecran : le painter et le compteur lisent le meme calcul. */
    const plan = planOf(g, f);
    const gemB = findBox(plan, "gem"), banB = findBox(plan, "banner");
    const mmx = (v) => m.trim.x + v * u, mmy = (v) => m.trim.y + v * u;

    if (f.gem && gemB && !gemB.seat) {
      const R = gemB.r * u;
      const gx = mmx(gemB.cx), gy = mmy(gemB.cy);
      const dir = gemB.dir < 0 ? -1 : 1;
      ctx.save();
      ctx.shadowColor = rgba(p.glow, 0.8); ctx.shadowBlur = u * 1.6;
      ctx.strokeStyle = f.metal ? metalPaint(ctx, m, f, false) : lineInk(f);
      ctx.lineWidth = Math.max(0.8, u * 0.55);
      ctx.beginPath(); ctx.arc(gx, gy, R, 0, Math.PI * 2); ctx.stroke();
      ctx.shadowBlur = 0;
      const rg = ctx.createRadialGradient(gx - R * 0.35, gy - R * 0.45, R * 0.08, gx, gy, R);
      rg.addColorStop(0, mix(p.gem, "#ffffff", 0.55));
      rg.addColorStop(0.55, p.gem);
      rg.addColorStop(1, mix(p.gem, "#000000", 0.55));
      ctx.fillStyle = rg;
      ctx.beginPath(); ctx.arc(gx, gy, R * 0.86, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "rgba(255,255,255,.55)";
      ctx.beginPath(); ctx.ellipse(gx - R * 0.3, gy - R * 0.36, R * 0.26, R * 0.17, -0.6, 0, Math.PI * 2); ctx.fill();
      /* rang de rarete : autant de crans que la rarete */
      const n = gemB.pips;
      ctx.fillStyle = rgba(p.gem, 0.95);
      for (let i = 0; i < n; i++) {
        ctx.beginPath();
        ctx.arc(gx + dir * (R * 1.5 + i * u * PIP_STEP_MM), gy, u * PIP_R_MM, 0, Math.PI * 2); ctx.fill();
      }
      ctx.restore();
    }

    if (f.banner && banB) {
      const label = String(f.banner_text || (byId(RARITIES, f.rarity) || {}).label || "").toUpperCase();
      if (label) {
        const bw = banB.box[2] * u;
        const bh = banB.box[3] * u;
        const bx = mmx(banB.box[0]);
        const by = mmy(banB.box[1]);
        ctx.save();
        ctx.fillStyle = f.metal ? metalPaint(ctx, m, f, true) : lineInk(f);
        ctx.beginPath();
        ctx.moveTo(bx, by);
        ctx.lineTo(bx + bw, by);
        ctx.lineTo(bx + bw - bh * 0.42, by + bh / 2);
        ctx.lineTo(bx + bw, by + bh);
        ctx.lineTo(bx, by + bh);
        ctx.lineTo(bx + bh * 0.42, by + bh / 2);
        ctx.closePath();
        ctx.fill();
        ctx.strokeStyle = rgba(p.base[2], 0.75); ctx.lineWidth = Math.max(0.5, u * 0.18); ctx.stroke();
        ctx.fillStyle = mix(p.base[2], "#000000", 0.25);
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.font = "700 " + Math.max(6, bh * 0.44) + 'px "Segoe UI", system-ui, sans-serif';
        try { ctx.letterSpacing = (u * 0.5) + "px"; } catch (e) { /* moteur ancien */ }
        ctx.fillText(label, bx + bw / 2, by + bh / 2 + bh * 0.03);
        ctx.restore();
      }
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     9. LE MODULE
     ═══════════════════════════════════════════════════════════════════════ */
  const M = CF.register({
    id: "frame",
    title: "Cadre",
    icon: "\u{1F5BC}",
    order: 2,

    painters: [
      {
        z: 40, async fn(ctx, geom, doc, card, side) {
          const f = st(doc);
          publishWindow(geom, f);
          if (side !== "back") { paintFront(ctx, geom, f, card, doc); return; }
          /* LES IMAGES DU VERSO, ATTENDUES ICI — le patron de `ensureImgs` de
             P3, et pour la meme raison : sans l'attente, la premiere frame
             peint un damier a la place d'une image qui existe, et cette
             premiere frame EST le fichier livre quand l'export part tout de
             suite. L'attente est BORNEE (le CORE laisse 4 s a un painter). */
          if (backOf(f, card) === "custom") {
            const files = backFiles(f);
            if (files.length) await ensureBackImgs(files);
          }
          paintBack(ctx, geom, f, card, doc);
        },
      },
      {
        z: 70, fn(ctx, geom, doc, card, side) {
          paintTop(ctx, geom, st(doc), card, side);
        },
      },
    ],

    state: DEFAULTS,

    init(host) { buildUI(host); },
  });

  /* ── ecriture + ANNULATION ───────────────────────────────────────────────
     La barre n'a pas d'annulation du tout : un clic malheureux sur un cadre
     et l'on recommence. Ici chaque ecriture empile l'ANCIENNE valeur des
     memes cles ; Ctrl+Z les rejoue. */
  const HIST = [], REDO = [];
  function set(partial, label) {
    const d = CF.doc().frame || {};
    const before = {};
    Object.keys(partial).forEach((k) => { before[k] = has(d, k) ? d[k] : DEFAULTS[k]; });
    HIST.push({ before: before, label: label || "" });
    if (HIST.length > 60) HIST.shift();
    REDO.length = 0;
    M.patch(partial);
    sync();
  }
  /* LE SCEAU S'ECRIT EN BLOC. `patch` remplace une cle par sa valeur : ecrire
     `{seal: {on: true}}` effacerait le metal, la largeur et les trois portees.
     On relit donc l'etat NORMALISE, on y applique le changement, et l'on
     repose l'objet entier — l'annulation (Ctrl+Z) empile la valeur d'avant
     comme pour n'importe quelle autre cle. */
  function setSeal(partial, lab) {
    const c = f().seal;
    const nxt = {
      on: c.on, kind: c.kind, width_mm: c.width_mm,
      scope: { screen: c.scope.screen, print: c.scope.print, mesh: c.scope.mesh },
    };
    if (has(partial, "on")) nxt.on = !!partial.on;
    if (has(partial, "kind")) nxt.kind = partial.kind;
    if (has(partial, "width_mm")) nxt.width_mm = partial.width_mm;
    if (partial.scope) {
      Object.keys(partial.scope).forEach((k) => {
        if (has(nxt.scope, k)) nxt.scope[k] = !!partial.scope[k];
      });
    }
    set({ seal: nxt }, lab);
  }

  function undo() {
    const h = HIST.pop();
    if (!h) { M.toast("rien à annuler"); return; }
    const d = CF.doc().frame || {};
    const after = {};
    Object.keys(h.before).forEach((k) => { after[k] = has(d, k) ? d[k] : DEFAULTS[k]; });
    REDO.push({ before: after, label: h.label });
    M.patch(h.before);
    sync();
    M.toast("annulé" + (h.label ? " : " + h.label : ""));
  }
  function redo() {
    const h = REDO.pop();
    if (!h) { M.toast("rien à rétablir"); return; }
    const d = CF.doc().frame || {};
    const after = {};
    Object.keys(h.before).forEach((k) => { after[k] = has(d, k) ? d[k] : DEFAULTS[k]; });
    HIST.push({ before: after, label: h.label });
    M.patch(h.before);
    sync();
  }

  /* ═══════════════════════════════════════════════════════════════════════
     10. INTERFACE
     ═══════════════════════════════════════════════════════════════════════ */
  const UI = {};
  let ROOT = null;

  function h(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function f() { return st(CF.doc()); }

  function buildUI(host) {
    ROOT = host;
    host.classList.add("cff");

    /* ── entete : compteur de combinaisons + annulation + verification ── */
    const top = h("div", "cff-top");
    UI.count = h("div", "cff-count");
    const acts = h("div", "cff-acts");
    UI.undo = h("button", "btn sm", "↶ Annuler");
    UI.redo = h("button", "btn sm", "↷");
    const reset = h("button", "btn sm", "Réinitialiser");
    /* LE COMPTEUR DE RECOUVREMENTS, a cote de la verification du backend :
       le meme endroit que la liste d'erreurs de rendu du CORE. Sans lui,
       chaque nouvelle famille est une occasion de couvrir une mention
       obligatoire sans que rien ne le dise. */
    UI.occ = h("button", "cff-occ", "occupation…");
    UI.occ.type = "button";
    UI.occ.addEventListener("click", () => { if (UI.occGrp) { UI.occGrp.open = true; UI.occGrp.scrollIntoView({ block: "nearest" }); } });
    /* LE BADGE DES SILHOUETTES. « 36 combinaisons » est un COMPTE d'entrees
       de menu ; on m'a reproche — mesure a l'appui — que six familles se
       reduisaient a trois squelettes (0,82 / 255 d'ecart entre Runique et
       Bois sur gris normalise). Un compte n'est pas une variete. Ce badge ne
       recite donc pas le catalogue : il MESURE les vignettes affichees a
       l'ecran, celles-la memes, et publie le pire ecart. */
    UI.sil = h("span", "cff-sil", "silhouettes…");
    UI.verify = h("span", "cff-verify", "vérification…");
    UI.undo.type = UI.redo.type = reset.type = "button";
    UI.undo.title = "Ctrl+Z"; UI.redo.title = "Ctrl+Maj+Z";
    UI.undo.addEventListener("click", undo);
    UI.redo.addEventListener("click", redo);
    reset.addEventListener("click", () => { set(JSON.parse(JSON.stringify(DEFAULTS)), "réinitialisation"); });
    acts.appendChild(UI.undo); acts.appendChild(UI.redo); acts.appendChild(reset);
    acts.appendChild(UI.occ); acts.appendChild(UI.sil); acts.appendChild(UI.verify);
    top.appendChild(UI.count); top.appendChild(acts);
    host.appendChild(top);

    /* ── etat vide : on PROPOSE, on ne laisse pas un ecran mort ── */
    UI.empty = h("div", "cff-empty hidden");
    UI.empty.appendChild(h("p", "hint", "Aucun cadre sur cette carte. Un modèle pour démarrer :"));
    const prow = h("div", "cff-presets");
    PRESETS.forEach((p) => {
      const b = h("button", "btn sm", esc(p.label));
      b.type = "button";
      b.addEventListener("click", () => set(JSON.parse(JSON.stringify(p.set)), "modèle " + p.label));
      prow.appendChild(b);
    });
    UI.empty.appendChild(prow);
    host.appendChild(UI.empty);

    const cols = h("div", "cff-cols");
    const A = h("div", "cff-colA"), B = h("div", "cff-colB");
    cols.appendChild(A); cols.appendChild(B);
    host.appendChild(cols);

    /* ── colonne A : le catalogue ── */
    A.appendChild(label("Famille graphique", FAMILIES.length + " familles"));
    UI.fam = h("div", "cff-grid");
    A.appendChild(UI.fam);
    A.appendChild(label("Rareté", RARITIES.length + " variantes"));
    UI.rar = h("div", "cff-grid");
    A.appendChild(UI.rar);

    /* LA GALERIE EST OUVERTE. Elle etait repliee, donc vide au chargement :
       0 enfant et 0 canvas dans l'etat par defaut, 36 seulement apres un
       clic. Un catalogue annonce mais non affiche n'est pas un catalogue —
       l'utilisateur qui n'ouvre jamais le volet ne voit que la promesse. */
    const all = h("details", "grp cff-all");
    all.open = true;
    all.appendChild(h("summary", null, "Les " + (FAMILIES.length * RARITIES.length) + " combinaisons"));
    UI.allBody = h("div", "grp-body cff-allgrid");
    all.appendChild(UI.allBody);
    all.addEventListener("toggle", () => { if (all.open) drawAll(); });
    A.appendChild(all);

    /* ── loupe : la demonstration du duel, a l'ecran ── */
    const lo = h("details", "grp cff-lo");
    lo.open = true;
    lo.appendChild(h("summary", null, "Loupe — le fichier livré, agrandi"));
    const lob = h("div", "grp-body");
    const lorow = h("div", "cff-row");
    UI.zoomSeg = seg(["2", "4", "8"], "4", (v) => { LO.zoom = Number(v); drawLoupe(); });
    UI.spotSeg = seg(["HG", "HD", "BG", "BD", "centre"], "HG", (v) => { LO.spot = v; drawLoupe(); });
    UI.loSide = seg(["Recto", "Verso"], "Recto", (v) => { LO.side = v === "Verso" ? "back" : "front"; drawLoupe(); });
    lorow.appendChild(field("Zoom", UI.zoomSeg.el));
    lorow.appendChild(field("Zone", UI.spotSeg.el));
    lorow.appendChild(field("Face", UI.loSide.el));
    lob.appendChild(lorow);
    UI.loupe = h("canvas", "cff-loupecv");
    lob.appendChild(UI.loupe);
    UI.loupeRead = h("p", "hint cff-lord");
    lob.appendChild(UI.loupeRead);
    lo.appendChild(lob);
    lo.addEventListener("toggle", () => { if (lo.open) drawLoupe(); });
    UI.loDetails = lo;
    /* EN TETE de la colonne : c'est la demonstration meme de la piece — le
       fichier livre, agrandi, sans un pixel mou. */
    A.insertBefore(lo, A.firstChild);

    /* ── colonne B : les reglages ── */
    const g1 = grp("Filets, bande et matière", true);
    UI.lineRow = numRow("Épaisseur du filet", "line_mm", LIMITS.line_mm[0], LIMITS.line_mm[1], 0.05);
    g1.body.appendChild(UI.lineRow.el);
    const dbl = h("div", "cff-row");
    UI.double = check("Double filet", (v) => set({ double: v }, "double filet"));
    dbl.appendChild(UI.double.el);
    UI.gapRow = numRow("Écart", "gap_mm", LIMITS.gap_mm[0], LIMITS.gap_mm[1], 0.05, true);
    dbl.appendChild(UI.gapRow.el);
    g1.body.appendChild(dbl);
    /* « Le libelle ne dit pas depuis quoi. La valeur porte le CENTRE du trait,
       pas son bord exterieur ; un conducteur de presse qui lit 1,6 mm attend
       le bord et se trompe d'un demi-filet. » Le libelle le dit maintenant, et
       la ligne dessous donne les TROIS distances, en mm et en px, recalculees
       a chaque changement — et le panneau des octets va les mesurer. */
    UI.edgeRow = numRow("Retrait du filet depuis la coupe — AXE du trait", "edge_mm",
      LIMITS.edge_mm[0], LIMITS.edge_mm[1], 0.1);
    g1.body.appendChild(UI.edgeRow.el);
    UI.edgeRead = h("p", "hint cff-edgeread");
    g1.body.appendChild(UI.edgeRead);
    UI.innerRow = numRow("Marge intérieure (bande)", "inner_mm", LIMITS.inner_mm[0], LIMITS.inner_mm[1], 0.1);
    g1.body.appendChild(UI.innerRow.el);

    const crow = h("div", "cff-row");
    UI.color = h("input", "cff-color");
    UI.color.type = "color";
    UI.color.addEventListener("input", () => set({ line_color: UI.color.value }, "couleur de filet"));
    const cauto = h("button", "lnk", "couleur de la rareté");
    cauto.type = "button";
    cauto.addEventListener("click", () => set({ line_color: "" }, "couleur automatique"));
    crow.appendChild(field("Couleur du filet", UI.color));
    crow.appendChild(field(" ", cauto));
    g1.body.appendChild(crow);

    const mrow = h("div", "cff-row");
    UI.metal = check("Liseré métallique", (v) => set({ metal: v }, "liseré métallique"));
    UI.metalTone = sel(METALS, (v) => set({ metal_tone: v }, "métal"));
    mrow.appendChild(UI.metal.el);
    mrow.appendChild(field("Métal", UI.metalTone));
    g1.body.appendChild(mrow);

    const grow = h("div", "cff-row");
    UI.grad = check("Dégradé de bande", (v) => set({ grad: v }, "dégradé"));
    UI.gradAngle = numRow("Angle", "grad_angle", 0, 360, 1, true, "°");
    grow.appendChild(UI.grad.el);
    grow.appendChild(UI.gradAngle.el);
    g1.body.appendChild(grow);
    B.appendChild(g1.el);

    /* ── LE SCEAU PRISMATIQUE (spec §6.2bis) — a cote des filets parce que
       c'est la meme grandeur : une bande posee sur le bord de la carte. Ses
       TROIS portees sont independantes, et la ligne d'etat dit toujours
       lesquelles sont declarees ET ce que CET ecran montre. */
    const g16 = grp("Sceau prismatique — contour holographique", false);
    const srow = h("div", "cff-row");
    UI.sealOn = check("Contour holographique", (v) => setSeal({ on: v }, "sceau"));
    UI.sealKind = sel(SEAL_KINDS, (v) => setSeal({ kind: v }, "métal du sceau"));
    srow.appendChild(UI.sealOn.el);
    srow.appendChild(field("Métal", UI.sealKind));
    g16.body.appendChild(srow);
    UI.sealW = numRow("Largeur de bande du filigrane", "seal_width_mm",
      LIMITS.seal_width_mm[0], LIMITS.seal_width_mm[1], 0.05, false, null,
      (n, lab) => setSeal({ width_mm: n }, lab));
    g16.body.appendChild(UI.sealW.el);
    g16.body.appendChild(label("Portée", "trois surfaces indépendantes"));
    const scoperow = h("div", "cff-row cff-scope");
    UI.sealScope = {};
    [["screen", "écran"], ["print", "impression"], ["mesh", "3D"]].forEach((kv) => {
      const c = check(kv[1], (v) => {
        const o = {}; o[kv[0]] = v;
        setSeal({ scope: o }, "portée " + kv[1]);
      });
      UI.sealScope[kv[0]] = c;
      scoperow.appendChild(c.el);
    });
    g16.body.appendChild(scoperow);
    UI.sealRead = h("p", "hint cff-sealread");
    g16.body.appendChild(UI.sealRead);
    B.appendChild(g16.el);

    /* ── fenetre d'illustration ── */
    const g2 = grp("Fenêtre d'illustration", true);
    const wrap = h("div", "cff-winwrap");
    UI.map = h("canvas", "cff-map");
    UI.map.tabIndex = 0;
    UI.map.title = "Glisser = déplacer · poignée = redimensionner · glisser sur le fond = redessiner · flèches = 1 mm (Maj = 0,2 mm) · double-clic = auto";
    wireMap(UI.map);
    wrap.appendChild(UI.map);
    const wf = h("div", "cff-winfields");
    UI.win = {};
    [["x", "X"], ["y", "Y"], ["w", "Largeur"], ["h", "Hauteur"], ["r", "Rayon"]].forEach((kv) => {
      const r = winField(kv[0], kv[1]);
      UI.win[kv[0]] = r;
      wf.appendChild(r.el);
    });
    UI.winLock = check("Verrou de proportions", (v) => set({ win_lock: v }, "verrou"));
    wf.appendChild(UI.winLock.el);
    const wbtns = h("div", "cff-row cff-wbtn");
    [["Auto", null], ["Plein cadre", "full"], ["Haut", "top"], ["Carré", "square"], ["Nombre d'or", "golden"]].forEach((kv) => {
      const b = h("button", "btn sm", esc(kv[0]));
      b.type = "button";
      b.addEventListener("click", () => applyWinPreset(kv[1]));
      wbtns.appendChild(b);
    });
    wf.appendChild(wbtns);
    wrap.appendChild(wf);
    g2.body.appendChild(wrap);
    UI.winRead = h("p", "hint cff-winread");
    g2.body.appendChild(UI.winRead);
    B.appendChild(g2.el);

    /* ── ornements ── */
    const g3 = grp("Ornements", false);
    const orow = h("div", "cff-row");
    UI.corner = sel(CORNERS, (v) => set({ corner: v }, "ornement de coin"));
    orow.appendChild(field("Coins", UI.corner));
    UI.gem = check("Gemme de rareté", (v) => set({ gem: v }, "gemme"));
    orow.appendChild(UI.gem.el);
    g3.body.appendChild(orow);
    const brow = h("div", "cff-row");
    UI.banner = check("Bandeau", (v) => set({ banner: v }, "bandeau"));
    UI.bannerText = h("input", "cff-txt");
    UI.bannerText.type = "text";
    UI.bannerText.placeholder = "nom de la rareté";
    UI.bannerText.maxLength = 24;
    UI.bannerText.addEventListener("change", () => set({ banner_text: UI.bannerText.value }, "texte du bandeau"));
    brow.appendChild(UI.banner.el);
    brow.appendChild(field("Texte", UI.bannerText));
    g3.body.appendChild(brow);
    const prow2 = h("div", "cff-row");
    UI.plate = check("Plaque de texte", (v) => set({ plate: v }, "plaque"));
    UI.plateA = numRow("Opacité", "plate_alpha", 0, 1, 0.01, true);
    prow2.appendChild(UI.plate.el);
    prow2.appendChild(UI.plateA.el);
    g3.body.appendChild(prow2);
    B.appendChild(g3.el);

    /* ── occupation du cadre : les boites reservees et le compteur ── */
    const g35 = grp("Occupation du cadre — meubles, logements, recouvrements", false);
    UI.occGrp = g35.el;
    const frow = h("div", "cff-row");
    UI.fit = check("Écarter les meubles des mentions", (v) => set({ fit: v }, "éviter les mentions"));
    UI.socles = check("Socle sous le texte posé sur l'illustration", (v) => set({ socles: v }, "socles"));
    frow.appendChild(UI.fit.el); frow.appendChild(UI.socles.el);
    g35.body.appendChild(frow);
    const frow2 = h("div", "cff-row");
    UI.seats = check("Logement des chiffres qui débordent de la bande", (v) => set({ seats: v }, "logements"));
    UI.socleA = numRow("Opacité des socles", "socle_alpha", 0, 1, 0.01, true);
    frow2.appendChild(UI.seats.el); frow2.appendChild(UI.socleA.el);
    g35.body.appendChild(frow2);
    UI.occTable = h("div", "cff-occtab");
    g35.body.appendChild(UI.occTable);
    UI.occRead = h("p", "hint cff-occread");
    g35.body.appendChild(UI.occRead);
    B.appendChild(g35.el);

    /* ── dos de carte ── */
    const g4 = grp("Dos de carte", false);
    UI.backGrid = h("div", "cff-grid cff-backs");
    g4.body.appendChild(UI.backGrid);
    const bkrow = h("div", "cff-row");
    UI.backSame = check("Dos commun à tout le jeu", (v) => set({ back_same: v }, "dos commun"));
    UI.backLabel = check("Nom du jeu au dos", (v) => set({ back_label: v }, "nom au dos"));
    bkrow.appendChild(UI.backSame.el); bkrow.appendChild(UI.backLabel.el);
    g4.body.appendChild(bkrow);
    const bexp = h("div", "cff-row");
    const bshow = h("button", "btn sm", "Voir le dos");
    bshow.type = "button";
    bshow.addEventListener("click", showBack);
    const bdl = h("button", "btn strong sm", "PNG dos 1:1 + pHYs");
    bdl.type = "button";
    bdl.title = "Rend le VERSO à geom.canvas_px, écrit le chunk pHYs (définition) et les boîtes de coupe en tEXt, puis télécharge — local, gratuit";
    bdl.addEventListener("click", exportBack);
    const fdl = h("button", "btn strong sm", "PNG recto 1:1 + pHYs");
    fdl.type = "button";
    fdl.title = "Le même fichier que l'aperçu, à geom.canvas_px, estampillé pHYs + tEXt";
    fdl.addEventListener("click", exportFront);
    bexp.appendChild(bshow); bexp.appendChild(bdl); bexp.appendChild(fdl);
    g4.body.appendChild(bexp);

    /* ── LE VERSO PERSONNALISE : la zone d'import et la pile de calques.
       Le bloc n'existe que pour le dos « Personnalisé » — un depot de fichier
       sous un motif de catalogue n'aurait nulle part ou aller. */
    UI.backCustom = h("div", "cff-backcustom hidden");
    UI.backDrop = h("div", "cff-drop");
    UI.backDrop.id = "cf-frame-backdrop";
    UI.backDrop.appendChild(h("span", null, "Déposez une image ici, collez-la (Ctrl+V)"));
    const bpick = h("button", "btn sm", "Choisir un fichier…");
    bpick.type = "button";
    bpick.addEventListener("click", () => pickBackFile(-1));
    UI.backDrop.appendChild(bpick);
    UI.backFile = h("input");
    UI.backFile.type = "file";
    UI.backFile.accept = "image/*";
    UI.backFile.className = "hidden";
    UI.backFile.id = "cf-frame-backfile";
    UI.backFile.addEventListener("change", () => {
      const fl = UI.backFile.files && UI.backFile.files[0];
      if (fl) importBackImage(fl, Number(UI.backFile.dataset.cible || -1));
    });
    ["dragenter", "dragover"].forEach((n) => UI.backDrop.addEventListener(n, (ev) => {
      ev.preventDefault(); UI.backDrop.classList.add("over");
    }));
    ["dragleave", "drop"].forEach((n) => UI.backDrop.addEventListener(n, () => UI.backDrop.classList.remove("over")));
    UI.backDrop.addEventListener("drop", (ev) => {
      ev.preventDefault();
      const fs = (ev.dataTransfer && ev.dataTransfer.files) || [];
      if (fs.length) importBackImage(fs[0], -1);
    });
    UI.backCustom.appendChild(UI.backDrop);
    UI.backCustom.appendChild(UI.backFile);
    const blhead = h("div", "cff-row");
    const bladd = h("button", "btn sm", "Ajouter un calque");
    bladd.type = "button";
    bladd.addEventListener("click", backLayerAdd);
    blhead.appendChild(bladd);
    UI.backCustom.appendChild(label("Calques du verso", "peints du haut vers le bas"));
    UI.backCustom.appendChild(blhead);
    UI.backList = h("div", "cff-bllist");
    UI.backCustom.appendChild(UI.backList);
    g4.body.appendChild(UI.backCustom);
    UI.backRead = h("p", "hint cff-backread");
    g4.body.appendChild(UI.backRead);

    UI.stampRead = h("p", "hint cff-stamp");
    g4.body.appendChild(UI.stampRead);
    g4.body.appendChild(h("p", "hint", "Dos par carte : décocher « dos commun » — le motif est alors lu dans <b>card.back</b> (colonne du CSV, pièce 04), avec repli sur le motif commun."));
    B.appendChild(g4.el);

    /* ── LA PREUVE SUR LES OCTETS ────────────────────────────────────────
       Tout ce panneau affiche des nombres. Celui-ci les REDESCEND dans le
       fichier : on rend, on relit, on defiltre, on compare. Une ligne rouge
       ici vaut plus qu'un badge vert partout ailleurs. */
    const g5 = grp("Preuve sur les octets — le fichier livré, redécodé à la main", true);
    const prow3 = h("div", "cff-row");
    const pv1 = h("button", "btn strong sm", "Relire le recto livré");
    const pv2 = h("button", "btn sm", "Relire le verso livré");
    pv1.type = pv2.type = "button";
    pv1.addEventListener("click", () => runProof("front"));
    pv2.addEventListener("click", () => runProof("back"));
    UI.pbadge = h("span", "cff-pbadge", "vérification automatique…");
    prow3.appendChild(pv1); prow3.appendChild(pv2); prow3.appendChild(UI.pbadge);
    g5.body.appendChild(prow3);
    UI.proofTab = h("div", "cff-prooftab");
    g5.body.appendChild(UI.proofTab);
    UI.proofRead = h("p", "hint cff-proofread");
    g5.body.appendChild(UI.proofRead);

    /* ── les DEUX definitions, dans le meme panneau que la preuve ── */
    g5.body.appendChild(h("div", "cff-sep", "Les deux définitions — 300 et 600, sur les octets"));
    const trow = h("div", "cff-row");
    const tv = h("button", "btn strong sm", "Rendre et relire les deux fichiers");
    tv.type = "button";
    tv.title = "Conduit le bouton 600 de la barre de format, rend et estampille les deux fichiers, "
      + "relit leurs octets, puis repose la définition d'origine";
    tv.addEventListener("click", runTwin);
    UI.tbadge = h("span", "cff-pbadge", "départ automatique…");
    UI.twinDl = h("button", "btn sm hidden", "Télécharger les deux fichiers mesurés");
    UI.twinDl.type = "button";
    UI.twinDl.addEventListener("click", twinDownload);
    trow.appendChild(tv); trow.appendChild(UI.tbadge); trow.appendChild(UI.twinDl);
    g5.body.appendChild(trow);
    UI.twinTab = h("div", "cff-prooftab");
    g5.body.appendChild(UI.twinTab);
    UI.twinRead = h("p", "hint cff-proofread",
      "Le même cadre, sorti <b>deux fois</b> par le chemin d'export normal : une fois en 300, une "
      + "fois en 600 DPI. La toile de chaque définition est recalculée à partir des millimètres — "
      + "jamais multipliée — et le filet garde la <b>même épaisseur en millimètres</b>. Les octets "
      + "des deux fichiers sont ensuite relus pour y chercher les <b>deux traces d'un "
      + "agrandissement</b> : un x2 au plus proche voisin recopie une ligne sur deux (<b>50 %</b>), "
      + "un x2 filtré rend chaque ligne impaire égale à la moyenne de ses voisines (<b>100 %</b>). "
      + "Un dessin refait à la bonne taille ne laisse ni l'une ni l'autre.");
    g5.body.appendChild(UI.twinRead);

    /* ── l'epreuve de controle ── */
    g5.body.appendChild(h("div", "cff-sep", "Épreuve de contrôle — traits de coupe et mires"));
    const crow2 = h("div", "cff-row");
    const cv2 = h("button", "btn strong sm", "Construire l'épreuve de contrôle");
    cv2.type = "button";
    cv2.title = "Pose la toile livrée sur " + CTRL_MARGE + " mm de papier, y trace les huit traits "
      + "de coupe alignés sur la rogne et quatre mires — hors du fond perdu, donc hors de l'encre";
    cv2.addEventListener("click", runControl);
    UI.cbadge = h("span", "cff-pbadge", "départ automatique…");
    UI.ctrlDl = h("button", "btn sm hidden", "Télécharger l'épreuve");
    UI.ctrlDl.type = "button";
    UI.ctrlDl.addEventListener("click", () => {
      if (!CTRL || !CTRL.blob) return;
      const g = CF.geom();
      M.download(CTRL.blob, "epreuve_controle_" + (CTRL.face === "back" ? "dos" : "recto")
        + "_" + CTRL.w + "x" + CTRL.h + "_" + g.dpi + "dpi.png");
    });
    crow2.appendChild(cv2); crow2.appendChild(UI.cbadge); crow2.appendChild(UI.ctrlDl);
    g5.body.appendChild(crow2);
    UI.ctrlTab = h("div", "cff-prooftab");
    g5.body.appendChild(UI.ctrlTab);
    UI.ctrlRead = h("p", "hint cff-proofread",
      "Le PNG livré ne porte <b>aucun trait de coupe</b>, et c'est voulu : du trait de coupe au bord "
      + "de toile il n'y a que du <b>fond perdu</b>, un repère y serait de l'encre sous la lame. "
      + "Un repère se pose hors du fond perdu — donc sur du papier en plus, donc dans un autre "
      + "fichier. C'est celui-ci, et il dit lui-même qu'il ne s'imprime pas.");
    g5.body.appendChild(UI.ctrlRead);
    /* ── LE BALAYAGE DE ROBUSTESSE ────────────────────────────────────────
       « Un seul format, une seule carte » : voici les douze, aux deux bornes
       du rayon, et les ornements et metaux sur les trois formats les plus
       hostiles. C'est ce panneau qui a trouve la bande inversee du format
       micro ; il est donc dans la colonne large, avec les autres preuves. */
    g5.body.appendChild(h("div", "cff-sep", "Robustesse — les 12 formats, les 2 bornes du rayon"));
    const swrow = h("div", "cff-row");
    const swb = h("button", "btn sm", "Relancer le balayage");
    swb.type = "button";
    swb.addEventListener("click", () => { SWEEP = null; drawSweep(); scheduleSweep(30); });
    UI.swbadge = h("span", "cff-pbadge", "départ automatique…");
    swrow.appendChild(swb); swrow.appendChild(UI.swbadge);
    g5.body.appendChild(swrow);
    UI.swTab = h("div", "cff-prooftab");
    g5.body.appendChild(UI.swTab);
    UI.swRead = h("p", "hint cff-proofread");
    g5.body.appendChild(UI.swRead);

    /* dans la colonne LARGE, et juste sous la loupe : les deux disent la meme
       chose — voici le fichier, regardez-le — l'une a l'oeil, l'autre a
       l'octet. Dans la colonne des reglages, le tableau etait a moitie hors
       champ. */
    A.insertBefore(g5.el, UI.loDetails.nextSibling);
    drawProof();
    drawTwin();
    drawControl();
    drawSweep();

    B.appendChild(h("p", "hint cff-kbd",
      "<b>Raccourcis</b> — <kbd>Ctrl+Z</kbd>/<kbd>Ctrl+Maj+Z</kbd> annuler / rétablir · "
      + "<kbd>[</kbd> <kbd>]</kbd> famille · <kbd>,</kbd> <kbd>.</kbd> rareté · "
      + "<kbd>D</kbd> double filet · <kbd>M</kbd> métal · <kbd>G</kbd> gemme · <kbd>V</kbd> recto/verso"));

    /* Le panneau est en display:none tant qu'une autre piece est active : ses
       canvas mesurent alors 0 px de large et les vignettes sortiraient floues
       a l'affichage. On redessine quand la largeur CHANGE — la comparaison
       evite la boucle (redessiner modifie la hauteur des canvas). */
    if (typeof ResizeObserver === "function") {
      let lastW = -1;
      new ResizeObserver(() => {
        const w = ROOT.clientWidth;
        if (w > 0 && w !== lastW) { lastW = w; sync(); }
      }).observe(ROOT);
    }

    document.addEventListener("keydown", onKey);
    document.addEventListener("paste", onPasteBack);
    CF.on("core:doc", (p) => { if (!p || p.id === "frame" || p.id === "format") sync(); });
    CF.on("core:geom", sync);
    CF.on("core:cards", sync);
    /* le fichier a change : la loupe le remontre, et la preuve le RE-LIT.
       Une preuve verte qui porte sur des octets perimes serait exactement le
       badge menteur que ce panneau existe pour rendre impossible. */
    CF.on("core:invalidate", () => { scheduleLoupe(); scheduleProof(); });
    CF.on("core:deck", () => { sync(); verify(); });

    sync();
    verify();
    scheduleProof(1200);
  }

  /* ── petites fabriques d'UI ─────────────────────────────────────────────── */
  function label(txt, right) {
    const e = h("div", "cff-lbl");
    e.appendChild(h("span", "lbl", esc(txt)));
    if (right) e.appendChild(h("i", null, esc(right)));
    return e;
  }
  function field(lbl, node) {
    const e = h("label", "fld cff-fld");
    e.appendChild(h("span", "lbl", lbl));
    e.appendChild(node);
    return e;
  }
  function grp(title, open) {
    const d = h("details", "grp cff-grp");
    d.open = !!open;
    d.appendChild(h("summary", null, esc(title)));
    const body = h("div", "grp-body");
    d.appendChild(body);
    return { el: d, body: body };
  }
  function check(lbl, on) {
    const e = h("label", "check cff-check");
    const i = h("input");
    i.type = "checkbox";
    i.addEventListener("change", () => on(i.checked));
    e.appendChild(i);
    e.appendChild(document.createTextNode(lbl));
    return { el: e, input: i };
  }
  function sel(list, on) {
    const s = h("select", "cff-sel");
    s.innerHTML = list.map((o) => '<option value="' + esc(o.id) + '">' + esc(o.label) + "</option>").join("");
    s.addEventListener("change", () => on(s.value));
    return s;
  }
  function seg(vals, cur, on) {
    const e = h("div", "seg sm cff-seg");
    e.innerHTML = vals.map((v) => '<button class="seg-b' + (v === cur ? " active" : "") + '" type="button" data-v="' + esc(v) + '">' + esc(v) + "</button>").join("");
    e.addEventListener("click", (ev) => {
      const b = ev.target.closest("button[data-v]");
      if (!b) return;
      Array.prototype.forEach.call(e.querySelectorAll(".seg-b"), (x) => x.classList.toggle("active", x === b));
      on(b.dataset.v);
    });
    return { el: e };
  }
  /* Le coeur de l'ergonomie : une valeur NUMERIQUE EDITABLE partout ou la
     barre n'a qu'un bouton — et le millimetre ET le pixel affiches ensemble,
     puisque c'est le pixel qui part chez l'imprimeur. */
  function numRow(lbl, key, min, max, step, compact, unit, on) {
    const el = h("div", "cff-num" + (compact ? " sm" : ""));
    const head = h("div", "cff-numhead");
    head.appendChild(h("span", "lbl", esc(lbl)));
    /* LES BORNES, ECRITES. Un critique n'a pas pu verifier le seuil
       « epaisseur reglable de 0 a 8 mm » parce que l'interface n'affichait
       que la valeur courante : la position du curseur etait compatible avec
       la plage sans la prouver. Trois mots, et le seuil devient lisible. */
    head.appendChild(h("i", "cff-bounds", r2(min) + " → " + r2(max) + (unit ? unit : (key === "plate_alpha" || key === "socle_alpha" ? "" : " mm"))));
    const rd = h("b", "cff-px");
    head.appendChild(rd);
    el.appendChild(head);
    const row = h("div", "cff-numrow");
    const rg = h("input", "cff-rng");
    rg.type = "range"; rg.min = min; rg.max = max; rg.step = step;
    const nb = h("input", "cff-nb");
    nb.type = "number"; nb.min = min; nb.max = max; nb.step = step;
    /* `on` : la porte de sortie des longueurs qui ne sont PAS une cle plate de
       `doc.frame` — la largeur du Sceau vit dans le sous-objet `seal`, et un
       `patch({seal_width_mm: …})` serait refuse par le schema du CORE. */
    const dflt = has(DEFAULTS, key) ? DEFAULTS[key] : min;
    const push = (v, lab) => {
      const n = cl(num(v, dflt), min, max);
      if (on) { on(n, lab); return; }
      const o = {}; o[key] = n; set(o, lab);
    };
    rg.addEventListener("input", () => { nb.value = rg.value; });
    rg.addEventListener("change", () => push(rg.value, lbl));
    nb.addEventListener("change", () => push(nb.value, lbl));
    row.appendChild(rg); row.appendChild(nb);
    if (unit) row.appendChild(h("i", "cff-unit", unit));
    el.appendChild(row);
    return { el: el, rg: rg, nb: nb, rd: rd, key: key, unit: unit };
  }
  function winField(k, lbl) {
    const el = h("label", "fld cff-wf");
    el.appendChild(h("span", "lbl", esc(lbl)));
    const i = h("input");
    i.type = "number"; i.step = 0.5;
    i.addEventListener("change", () => {
      const g = CF.geom(), w = winMM(g, f());
      const v = num(i.value, w[k]);
      patchWin({ x: w.x, y: w.y, w: w.w, h: w.h, r: w.r }, k, v);
    });
    el.appendChild(i);
    const px = h("i", "cff-px sm");
    el.appendChild(px);
    return { el: el, i: i, px: px };
  }

  function patchWin(base, k, v) {
    const g = CF.geom(), tw = g.trim_mm[0], th = g.trim_mm[1];
    const w = { x: base.x, y: base.y, w: base.w, h: base.h, r: base.r };
    if (k === "w" && f().win_lock) { const k2 = v / w.w; w.h = cl(w.h * k2, 2, th); }
    if (k === "h" && f().win_lock) { const k2 = v / w.h; w.w = cl(w.w * k2, 2, tw); }
    w[k] = v;
    w.w = cl(w.w, 2, tw); w.h = cl(w.h, 2, th);
    w.x = cl(w.x, 0, tw - w.w); w.y = cl(w.y, 0, th - w.h);
    w.r = cl(w.r, LIMITS.win_r_mm[0], LIMITS.win_r_mm[1]);
    ["x", "y", "w", "h", "r"].forEach((q) => { w[q] = r2(w[q]); });
    set({ window: w }, "fenêtre");
  }
  function applyWinPreset(kind) {
    if (!kind) { set({ window: null }, "fenêtre automatique"); return; }
    const g = CF.geom(), tw = g.trim_mm[0], th = g.trim_mm[1], f0 = f();
    const inn = Math.max(f0.inner_mm, 2);
    let w;
    if (kind === "full") w = { x: inn, y: inn, w: tw - 2 * inn, h: th - 2 * inn, r: 2.5 };
    else if (kind === "top") w = { x: inn, y: inn, w: tw - 2 * inn, h: (th - 2 * inn) * 0.52, r: 2.5 };
    else if (kind === "square") { const s = tw - 2 * inn; w = { x: inn, y: inn + 2, w: s, h: s, r: 2.5 }; }
    else { const ww = tw - 2 * inn; w = { x: inn, y: inn + 2, w: ww, h: ww / 1.618, r: 2.5 }; }
    ["x", "y", "w", "h", "r"].forEach((q) => { w[q] = r2(cl(w[q], 0, 999)); });
    w.h = cl(w.h, 2, th - w.y);
    set({ window: w }, "fenêtre " + kind);
  }

  /* ── carte miniature du plan (glisser-deposer) ─────────────────────────── */
  const MAP = { w: 168, h: 232 };
  let MAPDRAG = false;
  function mapGeom() {
    const g = CF.geom();
    const pad = 10;
    const s = Math.min((MAP.w - 2 * pad) / g.trim_mm[0], (MAP.h - 2 * pad) / g.trim_mm[1]);
    return { g: g, s: s, ox: (MAP.w - g.trim_mm[0] * s) / 2, oy: (MAP.h - g.trim_mm[1] * s) / 2 };
  }
  /* `w` est la fenetre A DESSINER, pas forcement celle du document : pendant
     un geste, l'appelant passe la fenetre CANDIDATE (locale) pour que la
     mini-carte suive chaque evenement sans attendre le patch coalesce au rAF
     (barre 9.6-2). `drawMap()` reste l'appel « etat courant du document ». */
  function drawMapWith(w) {
    const cv = UI.map;
    if (!cv) return;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    cv.width = MAP.w * dpr; cv.height = MAP.h * dpr;
    cv.style.width = MAP.w + "px"; cv.style.height = MAP.h + "px";
    const c = cv.getContext("2d");
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, MAP.w, MAP.h);
    const mg = mapGeom(), g = mg.g;
    const cs = getComputedStyle(document.documentElement);
    const ink = (cs.getPropertyValue("--ink-soft") || "#8b93a1").trim();
    const strong = (cs.getPropertyValue("--ink-strong") || "#fff").trim();
    const acc = (cs.getPropertyValue("--accent") || "#e0a33c").trim();
    const X = (mm) => mg.ox + mm * mg.s, Y = (mm) => mg.oy + mm * mg.s;
    c.strokeStyle = ink; c.lineWidth = 1;
    c.beginPath(); rrPath(c, X(0), Y(0), g.trim_mm[0] * mg.s, g.trim_mm[1] * mg.s, Math.max(0, g.corner_mm * mg.s)); c.stroke();
    c.strokeStyle = rgba("#33d18b", 0.75); c.setLineDash([3, 3]);
    const sm = g.safe_mm;
    c.strokeRect(X(sm), Y(sm), (g.trim_mm[0] - 2 * sm) * mg.s, (g.trim_mm[1] - 2 * sm) * mg.s);
    c.setLineDash([]);
    c.fillStyle = rgba(acc.charAt(0) === "#" ? acc : "#e0a33c", 0.20);
    c.strokeStyle = acc; c.lineWidth = 1.4;
    c.beginPath(); rrPath(c, X(w.x), Y(w.y), w.w * mg.s, w.h * mg.s, w.r * mg.s); c.fill(); c.stroke();
    c.fillStyle = strong;
    const hx = X(w.x + w.w), hy = Y(w.y + w.h);
    c.fillRect(hx - 5, hy - 5, 10, 10);
    c.fillStyle = ink;
    c.font = '9px ui-monospace, monospace';
    c.textAlign = "center";
    c.fillText(r1(w.w) + " x " + r1(w.h) + " mm", MAP.w / 2, MAP.h - 2);
  }
  function drawMap() { drawMapWith(winMM(CF.geom(), f())); }

  /* ── quelle prise la souris tient-elle ? UNE SEULE formule, relue au
        pointerdown ET au survol (curseur contextuel) : deux copies auraient
        fini par diverger (poignee agrandie d'un cote, oubliee de l'autre). */
  function mapHit(w, p, mg) {
    const hx = w.x + w.w, hy = w.y + w.h;
    /* poignee : zone de saisie 12 px a l'ecran (barre 9.6-3 ; etait 8 px). */
    if (Math.abs(p.x - hx) * mg.s < 12 && Math.abs(p.y - hy) * mg.s < 12) return "size";
    if (p.x > w.x && p.x < hx && p.y > w.y && p.y < hy) return "move";
    return "draw";
  }
  function wireMap(cv) {
    let drag = null, pendingWin = null, rafId = 0;
    /* repli setTimeout si rAF est absent (essais hors navigateur), et
       annulation SYMETRIQUE : cancelAnimationFrame sur un identifiant de
       setTimeout ne fait rien (autre registre) — le meme drapeau sert donc a
       programmer ET a annuler. Meme patron que le raf() de core.js:158,
       reproduit ICI en local : chaque piece est un fichier a part, sans
       import partage entre modules. */
    const hasRAF = typeof requestAnimationFrame === "function";
    const scheduleFrame = (fn) => (hasRAF ? requestAnimationFrame(fn) : setTimeout(fn, 16));
    const cancelFrame = (id) => { if (hasRAF) cancelAnimationFrame(id); else clearTimeout(id); };
    const toMM = (ev) => {
      const r = cv.getBoundingClientRect(), mg = mapGeom();
      return { x: (ev.clientX - r.left - mg.ox) / mg.s, y: (ev.clientY - r.top - mg.oy) / mg.s };
    };
    const flushWin = () => {
      rafId = 0;
      if (!pendingWin) return;
      const n = pendingWin; pendingWin = null;
      M.patch({ window: n });          /* <= 1 patch par frame (spec 9.6-1) */
    };
    cv.addEventListener("pointerdown", (ev) => {
      /* un second pointeur (tactile multi-doigts, desormais possible —
         touch-action: none l'autorise sur ce canevas) pendant un geste deja
         en cours : ignore, plutot que d'ecraser `drag` et faire basculer le
         MODE du glisser (redimensionner <-> deplacer <-> dessiner) au
         milieu du geste du premier. `isPrimary`, pas un garde d'etat
         (`if (drag) return;`, la version d'origine) : un garde d'etat ne se
         relache QUE si le geste en cours se termine proprement — un piege
         quelconque le laissant bloque aurait REFUSE tout glisser futur
         jusqu'au rechargement. `isPrimary` se lit sur l'EVENEMENT, jamais
         sur un etat qui pourrait rester coince (revue 7bis, re-revue,
         item 1). */
      if (!ev.isPrimary) return;
      const g = CF.geom(), w = winMM(g, f()), p = toMM(ev), mg = mapGeom();
      cv.setPointerCapture(ev.pointerId);
      const hit = mapHit(w, p, mg);
      if (hit === "size") drag = { mode: "size", w: w };
      else if (hit === "move") drag = { mode: "move", w: w, dx: p.x - w.x, dy: p.y - w.y };
      else drag = { mode: "draw", w: w, ox: p.x, oy: p.y };
      MAPDRAG = true;
      ev.preventDefault();
    });
    cv.addEventListener("pointermove", (ev) => {
      if (!drag) {
        /* hors geste : curseur contextuel seulement — handler LEGER, aucun
           patch, aucun redessin de la carte (spec 9.6-3). */
        const g = CF.geom(), w = winMM(g, f()), p = toMM(ev), mg = mapGeom();
        const hit = mapHit(w, p, mg);
        cv.style.cursor = hit === "size" ? "nwse-resize" : hit === "move" ? "move" : "crosshair";
        return;
      }
      const g = CF.geom(), tw = g.trim_mm[0], th = g.trim_mm[1], p = toMM(ev), w = drag.w;
      let n;
      if (drag.mode === "move") n = { x: p.x - drag.dx, y: p.y - drag.dy, w: w.w, h: w.h, r: w.r };
      else if (drag.mode === "size") {
        let nw = cl(p.x - w.x, 2, tw - w.x), nh = cl(p.y - w.y, 2, th - w.y);
        if (f().win_lock) { const k = Math.min(nw / w.w, nh / w.h); nw = w.w * k; nh = w.h * k; }
        n = { x: w.x, y: w.y, w: nw, h: nh, r: w.r };
      } else {
        n = { x: Math.min(drag.ox, p.x), y: Math.min(drag.oy, p.y), w: Math.abs(p.x - drag.ox), h: Math.abs(p.y - drag.oy), r: w.r };
      }
      n.w = cl(n.w, 2, tw); n.h = cl(n.h, 2, th);
      n.x = cl(n.x, 0, tw - n.w); n.y = cl(n.y, 0, th - n.h);
      ["x", "y", "w", "h", "r"].forEach((q) => { n[q] = r2(n[q]); });
      pendingWin = n;
      if (!rafId) rafId = scheduleFrame(flushWin);
      drawMapWith(n);                  /* retour local immediat (spec 9.6-2) */
    });
    const end = (ev) => {
      MAPDRAG = false;
      if (!drag) return;
      const prev = drag.w;
      drag = null;
      if (rafId) { cancelFrame(rafId); rafId = 0; }
      if (pendingWin) { M.patch({ window: pendingWin }); pendingWin = null; }
      /* une seule entree d'annulation par geste, pas une par pixel */
      HIST.push({ before: { window: { x: prev.x, y: prev.y, w: prev.w, h: prev.h, r: prev.r } }, label: "fenêtre" });
      REDO.length = 0;
      sync();
      if (ev) ev.preventDefault();
    };
    cv.addEventListener("pointerup", end);
    cv.addEventListener("pointercancel", end);
    cv.addEventListener("dblclick", () => set({ window: null }, "fenêtre automatique"));
    cv.addEventListener("keydown", (ev) => {
      const step = ev.shiftKey ? 0.2 : 1;
      const g = CF.geom(), w = winMM(g, f());
      const base = { x: w.x, y: w.y, w: w.w, h: w.h, r: w.r };
      const k = ev.key;
      if (k === "ArrowLeft") patchWin(base, ev.altKey ? "w" : "x", (ev.altKey ? w.w : w.x) - step);
      else if (k === "ArrowRight") patchWin(base, ev.altKey ? "w" : "x", (ev.altKey ? w.w : w.x) + step);
      else if (k === "ArrowUp") patchWin(base, ev.altKey ? "h" : "y", (ev.altKey ? w.h : w.y) - step);
      else if (k === "ArrowDown") patchWin(base, ev.altKey ? "h" : "y", (ev.altKey ? w.h : w.y) + step);
      else return;
      ev.preventDefault();
    });
  }

  /* ── vignettes : LE MEME code de dessin, a une autre definition. C'est la
        preuve la plus courte que le cadre n'est pas un bitmap. ─────────────── */
  function thumbGeom() {
    const g = CF.geom();
    return CF.geomOf(g.fmt, 96, g.bleed_mm, g.safe_mm, g.corner_mm);
  }
  /* Les vignettes montrent le CADRE, pas l'illustration de la carte courante :
     une carte deja illustree laissait une fenetre blanche au milieu de chaque
     vignette et on ne comparait plus rien. Carte vide -> reserve d'illustration
     dessinee, le cadre se lit. */
  const THUMB_CARD = { i: 0, id: "thumb", fields: {}, art: null, back: null };
  function thumbDoc() { const d = CF.doc(); return { name: d.name }; }
  function drawThumb(cv, over) {
    const g = thumbGeom();
    const f0 = Object.assign({}, f(), over);
    if (f0.family === "none") f0.family = DEFAULTS.family;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const cw = cv.clientWidth || 74, chh = Math.round(cw * g.canvas_px[1] / g.canvas_px[0]);
    cv.width = Math.round(cw * dpr); cv.height = Math.round(chh * dpr);
    cv.style.height = chh + "px";
    const off = document.createElement("canvas");
    off.width = g.canvas_px[0]; off.height = g.canvas_px[1];
    const oc = off.getContext("2d");
    oc.fillStyle = "#ffffff"; oc.fillRect(0, 0, off.width, off.height);
    try {
      paintFront(oc, g, f0, THUMB_CARD, thumbDoc());
      paintTop(oc, g, f0, THUMB_CARD, "front");
    } catch (e) { console.error("cardforge: vignette frame", e); }
    const c = cv.getContext("2d");
    c.imageSmoothingEnabled = true;
    try { c.imageSmoothingQuality = "high"; } catch (e) { /* moteurs anciens */ }
    c.clearRect(0, 0, cv.width, cv.height);
    c.drawImage(off, 0, 0, cv.width, cv.height);
  }
  function drawBackThumb(cv, backId) {
    const g = thumbGeom();
    const f0 = Object.assign({}, f(), { back: backId, back_same: true });
    if (f0.family === "none") f0.family = DEFAULTS.family;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const cw = cv.clientWidth || 74, chh = Math.round(cw * g.canvas_px[1] / g.canvas_px[0]);
    cv.width = Math.round(cw * dpr); cv.height = Math.round(chh * dpr);
    cv.style.height = chh + "px";
    const off = document.createElement("canvas");
    off.width = g.canvas_px[0]; off.height = g.canvas_px[1];
    const oc = off.getContext("2d");
    oc.fillStyle = "#ffffff"; oc.fillRect(0, 0, off.width, off.height);
    try { paintBack(oc, g, f0, THUMB_CARD, thumbDoc()); } catch (e) { console.error("cardforge: vignette dos", e); }
    const c = cv.getContext("2d");
    c.clearRect(0, 0, cv.width, cv.height);
    c.drawImage(off, 0, 0, cv.width, cv.height);
  }

  function cell(lbl, sub) {
    const e = h("button", "cff-cell");
    e.type = "button";
    const cv = h("canvas", "cff-thumb");
    e.appendChild(cv);
    e.appendChild(h("span", "cff-cn", esc(lbl)));
    if (sub) e.appendChild(h("i", "cff-cs", esc(sub)));
    return { el: e, cv: cv };
  }

  function buildGrids() {
    if (UI.fam.childNodes.length) return;
    const none = cell("Aucun cadre", "carte nue");
    none.el.classList.add("cff-none");
    none.cv.remove();
    none.el.addEventListener("click", () => set({ family: "none" }, "aucun cadre"));
    UI.famCells = {};
    FAMILIES.forEach((fa) => {
      const c = cell(fa.label, fa.hint);
      c.el.addEventListener("click", () => set({ family: fa.id }, "famille " + fa.label));
      UI.fam.appendChild(c.el);
      UI.famCells[fa.id] = c;
    });
    UI.fam.appendChild(none.el);
    UI.noneCell = none;
    UI.rarCells = {};
    RARITIES.forEach((ra) => {
      const c = cell(ra.label, "");
      c.el.addEventListener("click", () => set({ rarity: ra.id }, "rareté " + ra.label));
      UI.rar.appendChild(c.el);
      UI.rarCells[ra.id] = c;
    });
    UI.backCells = {};
    BACKS.forEach((bk) => {
      const c = cell(bk.label, "");
      c.el.addEventListener("click", () => set({ back: bk.id }, "dos " + bk.label));
      UI.backGrid.appendChild(c.el);
      UI.backCells[bk.id] = c;
    });
  }
  function drawGrids() {
    const f0 = f();
    FAMILIES.forEach((fa) => {
      const c = UI.famCells[fa.id];
      c.el.classList.toggle("on", f0.family === fa.id);
      drawThumb(c.cv, { family: fa.id });
    });
    UI.noneCell.el.classList.toggle("on", f0.family === "none");
    RARITIES.forEach((ra) => {
      const c = UI.rarCells[ra.id];
      c.el.classList.toggle("on", f0.rarity === ra.id);
      drawThumb(c.cv, { rarity: ra.id });
    });
    BACKS.forEach((bk) => {
      const c = UI.backCells[bk.id];
      c.el.classList.toggle("on", f0.back === bk.id);
      drawBackThumb(c.cv, bk.id);
    });
  }
  function drawAll() {
    if (!UI.allBody) return;
    if (!UI.allBody.childNodes.length) {
      FAMILIES.forEach((fa) => {
        RARITIES.forEach((ra) => {
          const c = cell(fa.label, byId(RARITIES, ra.id).label);
          c.el.dataset.fam = fa.id; c.el.dataset.rar = ra.id;
          c.el.addEventListener("click", () => set({ family: fa.id, rarity: ra.id }, fa.label + " " + ra.label));
          UI.allBody.appendChild(c.el);
        });
      });
    }
    const f0 = f();
    Array.prototype.forEach.call(UI.allBody.querySelectorAll(".cff-cell"), (el) => {
      el.classList.toggle("on", el.dataset.fam === f0.family && el.dataset.rar === f0.rarity);
      drawThumb(el.querySelector("canvas"), { family: el.dataset.fam, rarity: el.dataset.rar });
    });
  }

  /* ── LES SILHOUETTES, MESUREES SUR LES VIGNETTES AFFICHEES ──────────────
     La methode est celle du critique, reprise telle quelle : gris NORMALISE
     (contraste renormalise sur chaque vignette, ce qui fait s'effondrer vers
     zero une simple recoloration), a rarete EGALE, sur la vignette — le
     format ou le choix se fait vraiment. Les canvas sont deja dessines : on
     ne rend rien de plus, on lit ce que l'utilisateur voit. */
  let silTimer = null;
  function scheduleSil() { clearTimeout(silTimer); silTimer = setTimeout(measureSil, 650); }
  function grayNorm(cv) {
    const c = cv.getContext("2d");
    const im = c.getImageData(0, 0, cv.width, cv.height);
    const d = im.data, n = d.length / 4, o = new Float64Array(n);
    let mn = 1e9, mx = -1e9;
    for (let i = 0; i < n; i++) {
      const v = 0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2];
      o[i] = v; if (v < mn) mn = v; if (v > mx) mx = v;
    }
    const s = (mx - mn) || 1;
    for (let i = 0; i < n; i++) o[i] = (o[i] - mn) / s * 255;
    return o;
  }
  function sig(cv) {
    const c = cv.getContext("2d");
    const d = c.getImageData(0, 0, cv.width, cv.height).data;
    let a = 2166136261;
    for (let i = 0; i < d.length; i += 17) { a ^= d[i]; a = (a * 16777619) >>> 0; }
    return a;
  }
  function measureSil() {
    if (!UI.sil || !UI.allBody) return;
    try {
      const cells = UI.allBody.querySelectorAll(".cff-cell canvas");
      if (cells.length < FAMILIES.length * RARITIES.length) { UI.sil.textContent = "silhouettes…"; return; }
      const seen = {};
      let distinct = 0;
      Array.prototype.forEach.call(cells, (cv) => {
        if (!cv.width || !cv.height) return;
        const s = sig(cv);
        if (!seen[s]) { seen[s] = 1; distinct++; }
      });
      /* LA MESURE PORTE SUR LES SIX RARETES, PAS SUR CELLE QUI EST AFFICHEE.
         Elle ne portait que sur la rarete courante, et publiait « familles ≥
         9,2/255 » ; balayees les six, la pire paire du catalogue tombe a
         8,12/255 (Runique x Neon en Mythique). Le badge disait donc 1,1 de
         trop a qui le lisait comme une propriete du catalogue — ce que sa
         formulation invite a faire. Un chiffre qui ne vaut que pour la case
         ouverte doit dire de quelle case il parle, ou couvrir tout le tableau.
         Il couvre desormais tout le tableau : 126 paires (6 raretes x 21
         depuis la septieme famille ; 90 quand elles etaient six). */
      const gr = {}, dims = {};
      RARITIES.forEach((ra) => {
        FAMILIES.forEach((fa) => {
          const el = UI.allBody.querySelector('.cff-cell[data-fam="' + fa.id + '"][data-rar="' + ra.id + '"] canvas');
          if (el && el.width) { gr[ra.id + "/" + fa.id] = grayNorm(el); dims[fa.id] = [el.width, el.height]; }
        });
      });
      let worst = 1e9, wp = "", paires = 0;
      RARITIES.forEach((ra) => {
        for (let i = 0; i < FAMILIES.length; i++) {
          for (let j = i + 1; j < FAMILIES.length; j++) {
            const a = gr[ra.id + "/" + FAMILIES[i].id], b = gr[ra.id + "/" + FAMILIES[j].id];
            if (!a || !b || a.length !== b.length) continue;
            let s = 0;
            for (let k = 0; k < a.length; k++) s += Math.abs(a[k] - b[k]);
            const d = s / a.length;
            paires++;
            if (d < worst) { worst = d; wp = FAMILIES[i].label + " x " + FAMILIES[j].label + " en « " + ra.label + " »"; }
          }
        }
      });
      if (!paires) { UI.sil.textContent = "silhouettes…"; return; }
      const total = FAMILIES.length * RARITIES.length;
      const dim = dims[FAMILIES[0].id] || [0, 0];
      SILV = { distinct: distinct, total: total, worst: worst, wp: wp, paires: paires, dim: dim };
      drawSil();
      scheduleSilFile();
    } catch (e) {
      UI.sil.className = "cff-sil";
      UI.sil.textContent = "silhouettes : non mesurables";
      UI.sil.title = String((e && e.message) || e);
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     LE MEME ECART, MAIS SUR LA TOILE LIVREE — parce que c'est CELLE-LA qu'on
     mesurera contre nous
     ───────────────────────────────────────────────────────────────────────
     Le badge ne publiait qu'un chiffre de VIGNETTE (66 x 90 px) : « pire paire
     8,12 / 255 ». Mesure faite sur la toile livree, 815 x 1110, meme methode
     et meme gris normalise : 4,94 / 255. Les deux nombres sont exacts, ils ne
     parlent pas du meme objet — et celui que quiconque re-derivera est le
     second, puisque c'est le fichier. Un ecran qui publie le chiffre le plus
     flatteur des deux fait exactement ce qu'on reproche a un en-tete qui
     annonce 16 bits sur une carte 8 bits elargie.
     Les DEUX sont donc affiches, chacun avec sa surface.

     Le rendu se fait par `paintFront` + `paintTop` — les painters memes que le
     CORE appelle pour fabriquer le fichier — a `CF.geom()`, la toile du
     fichier. Il n'ecrit RIEN dans le document : la famille est passee en
     surcharge locale, comme pour les vignettes.

     POURQUOI DEUX SURFACES. La fenetre d'illustration occupe 34,1 % de la
     toile et ne porte aucune signature de famille — mesure : 0,09 / 255
     d'ecart entre deux familles a l'interieur. C'est voulu (un cadre ne
     repeint pas l'illustration), mais cela DILUE mecaniquement l'ecart d'un
     tiers. On publie donc le chiffre sur la toile entiere — celui qu'un
     auditeur obtiendra — et le meme hors fenetre, qui est celui qui parle du
     dessin. Aucun des deux n'est cache.
     ═══════════════════════════════════════════════════════════════════════ */
  let SILV = null, SILF = null;
  const SILFQ = { timer: null, busy: false, sig: "" };
  const SIL_SEUIL = 4;
  /* ── LE PIRE COUPLE, RELEVE A CHAQUE FAMILLE AJOUTEE ─────────────────────
     La QA de silhouettes est l'ARBITRE d'une famille nouvelle, et le seuil ne
     bouge pas : une famille qui passe sous SIL_SEUIL se REDESSINE. Les deux
     chiffres ci-dessous sont ceux du badge, releves dans un vrai navigateur
     sur ce fichier-ci — le panneau les recalcule sous les yeux de qui les
     lit, et `test_cards_frame.py` en fait un PLANCHER.

       AVANT la septieme famille — six familles, 90 paires, 36/36 signatures :
         toile livree 5,2 / 255 · vignettes 6,84 / 255, « Runique x Art deco
         en Mythique » des deux cotes.
       PREMIER JET de « Gravure » (anneau ivoire d'un seul ton), sept
       familles, 126 paires : toile 4,61 / 255 et la paire la plus serree
       devenait « Epure x Gravure en Rare ». Au-dessus du seuil, mais c'etait
       la famille neuve qui tirait le catalogue vers le bas : elle a ete
       REDESSINEE (anneau partage en deux par la cuvette, voir `ringZone`),
       pas le seuil deplace.
       APRES redessin — sept familles, 126 paires, 42/42 signatures :
         MESURE-3A-TOILE = 5.2 /255 « Runique x Art deco en Mythique »
         MESURE-3A-VIGNETTE = 6.84 /255 « Runique x Art deco en Mythique »

     La paire la plus serree est donc EXACTEMENT celle d'avant, a la meme
     valeur : la septieme famille n'a rien coute au catalogue. (Hors fenetre
     d'illustration : 7,88 / 255, la aussi inchange.) */
  function silSig() {
    try {
      const g = CF.geom(), d = CF.doc();
      const fr = Object.assign({}, d.frame || {});
      delete fr.family;                       /* les deux axes du balayage : ils */
      delete fr.rarity;                       /* ne comptent pas dans l'empreinte */
      return hash32(JSON.stringify([g.fmt, g.dpi, g.bleed_mm, g.safe_mm, g.corner_mm, fr]));
    } catch (e) { return "?" + Date.now(); }
  }
  function scheduleSilFile(ms) {
    clearTimeout(SILFQ.timer);
    SILFQ.timer = setTimeout(measureSilFile, ms == null ? 1400 : ms);
  }
  function grayNormOf(im) {
    const d = im.data, n = d.length / 4, o = new Float64Array(n);
    let mn = 1e9, mx = -1e9;
    for (let i = 0; i < n; i++) {
      const v = 0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2];
      o[i] = v; if (v < mn) mn = v; if (v > mx) mx = v;
    }
    const s = (mx - mn) || 1;
    for (let i = 0; i < n; i++) o[i] = (o[i] - mn) / s * 255;
    return o;
  }
  function paintFamAt(g, over) {
    const off = document.createElement("canvas");
    off.width = g.canvas_px[0]; off.height = g.canvas_px[1];
    const oc = off.getContext("2d");
    oc.fillStyle = "#ffffff"; oc.fillRect(0, 0, off.width, off.height);
    const f0 = Object.assign({}, f(), over);
    if (f0.family === "none") f0.family = DEFAULTS.family;
    paintFront(oc, g, f0, THUMB_CARD, thumbDoc());
    paintTop(oc, g, f0, THUMB_CARD, "front");
    return oc.getImageData(0, 0, off.width, off.height);
  }
  /* LE BALAYAGE COUVRE LES SIX RARETES, UNE PAR TOUR DE BOUCLE D'EVENEMENTS.
     Un chiffre releve sur la seule rarete ouverte serait le meme travers que
     celui deja corrige sur les vignettes : il se lit comme une propriete du
     catalogue et n'en est pas une. 36 rendus a 815 x 1110 coutent environ
     2,6 s d'un bloc — inacceptable dans un panneau vivant ; ils sont donc
     rendus rarete par rarete, le badge affiche l'avancement et le PIRE
     COURANT (jamais un chiffre plus flatteur que ce qui est deja connu). */
  const now = () => ((window.performance && performance.now) ? performance.now() : Date.now());
  function imageOf(cv, W, H) {
    const t = document.createElement("canvas");
    t.width = W; t.height = H;
    const c = t.getContext("2d");
    c.drawImage(cv, 0, 0);
    return c.getImageData(0, 0, W, H);
  }
  /* ── LE MASQUE DES COUCHES VOISINES ──────────────────────────────────────
     Le badge rendait les six familles avec les seules couches du cadre, et
     publiait un ecart 4 % plus grand que celui des fichiers reellement
     exportes — dans le sens flatteur. La cause est mecanique — sur le
     fichier, le texte de la piece 03 (couche 60) est peint PAR-DESSUS le
     cadre, donc ces pixels-la sont identiques d'une famille a l'autre et
     comptent pour 0. Un chiffre qui ne tient pas sur le fichier n'a rien a
     faire sur l'ecran : on releve la carte composee une fois, on marque les
     pixels ou une autre couche a recouvert le cadre, et on les compte pour 0
     comme le fichier le fait. Le nombre publie devient celui du fichier.
     Si le masque devorait plus de la moitie de la toile (une matiere opaque
     posee sur tout, par exemple), il est REFUSE et le badge le dit : mieux
     vaut un chiffre dont on connait le biais qu'un chiffre invente. */
  async function maskOf(g, W, H) {
    try {
      const compo = await CF.renderCard(CF.current(), { face: "front" });
      const a = imageOf(compo, W, H).data;
      const b = paintFamAt(g, {}).data;
      const m = new Uint8Array(W * H);
      let n = 0;
      for (let k = 0; k < W * H; k++) {
        const i = k * 4;
        const la = 0.299 * a[i] + 0.587 * a[i + 1] + 0.114 * a[i + 2];
        const lb = 0.299 * b[i] + 0.587 * b[i + 1] + 0.114 * b[i + 2];
        if (Math.abs(la - lb) > 2) { m[k] = 1; n++; }
      }
      const frac = n / (W * H);
      return frac > 0.55 ? { m: null, frac: frac, refus: true } : { m: m, frac: frac, refus: false };
    } catch (e) {
      return { m: null, frac: 0, refus: true, why: String((e && e.message) || e) };
    }
  }
  function measureSilFile() {
    if (!UI.sil || SILFQ.busy || !panelOn()) return;
    const s = silSig();
    if (SILF && SILF.sig === s && SILF.rangs === RARITIES.length) return;
    SILFQ.busy = true;
    const t0 = now();
    const g = CF.geom();
    const W = g.canvas_px[0], H = g.canvas_px[1];
    const f0 = f();
    /* le masque « hors fenetre d'illustration », en pixels de toile */
    const wm = winMM(g, f0), mm = g.mm2px;
    const wx0 = g.bleed_off_px[0] + mm(wm.x), wy0 = g.bleed_off_px[1] + mm(wm.y);
    const wx1 = wx0 + mm(wm.w), wy1 = wy0 + mm(wm.h);
    const acc = { sig: s, all: 1e9, out: 1e9, pire: "", w: W, h: H, paires: 0,
      part: 0, ms: 0, rangs: 0, total: RARITIES.length,
      masque: 0, masque_refus: false };
    let k = 0, MK = null;
    const tour = () => {
      if (silSig() !== s || !panelOn()) { SILFQ.busy = false; return; }
      try {
        const ra = RARITIES[k];
        const gr = {};
        FAMILIES.forEach((fa) => {
          gr[fa.id] = grayNormOf(paintFamAt(g, { family: fa.id, rarity: ra.id }));
        });
        for (let i = 0; i < FAMILIES.length; i++) {
          for (let j = i + 1; j < FAMILIES.length; j++) {
            const a = gr[FAMILIES[i].id], b = gr[FAMILIES[j].id];
            let sAll = 0, sOut = 0, cOut = 0;
            for (let y = 0; y < H; y++) {
              const dedans = (y >= wy0 && y < wy1);
              for (let x = 0; x < W; x++) {
                const q = y * W + x;
                const e = (MK && MK[q]) ? 0 : Math.abs(a[q] - b[q]);
                sAll += e;
                if (!(dedans && x >= wx0 && x < wx1)) { sOut += e; cOut++; }
              }
            }
            const dAll = sAll / (W * H), dOut = sOut / (cOut || 1);
            acc.paires++;
            acc.part = 1 - cOut / (W * H);
            if (dAll < acc.all) {
              acc.all = dAll;
              acc.pire = FAMILIES[i].label + " x " + FAMILIES[j].label + " en « " + ra.label + " »";
            }
            if (dOut < acc.out) acc.out = dOut;
          }
        }
        acc.rangs = k + 1;
        acc.ms = Math.round(now() - t0);
        SILF = Object.assign({}, acc);
        drawSil();
      } catch (e) {
        SILF = { sig: s, erreur: String((e && e.message) || e) };
        drawSil();
        SILFQ.busy = false;
        return;
      }
      k++;
      if (k < RARITIES.length) setTimeout(tour, 30);
      else SILFQ.busy = false;
    };
    maskOf(g, W, H).then((mk) => {
      if (silSig() !== s || !panelOn()) { SILFQ.busy = false; return; }
      MK = mk.m;
      acc.masque = mk.frac;
      acc.masque_refus = mk.refus;
      setTimeout(tour, 0);
    });
  }
  function drawSil() {
    if (!UI.sil || !SILV) return;
    const V = SILV;
    const F = (SILF && !SILF.erreur && SILF.sig === silSig()) ? SILF : null;
    const ok = V.distinct === V.total && (!F || F.all >= SIL_SEUIL);
    const fini = F && F.rangs === F.total;
    UI.sil.className = "cff-sil " + (ok ? "ok" : "ko");
    UI.sil.textContent = V.distinct + "/" + V.total + " distinctes · familles "
      + (F ? (r1(F.all) + "/255 sur la toile livrée"
        + (fini ? "" : " (" + F.rangs + "/" + F.total + " raretés…)"))
        : "sur la toile livrée…");
    /* CE QUE CETTE INFOBULLE A LE DROIT DE DIRE. Elle portait trois chiffres
       qui ne se relisent nulle part — un ecart releve une fois a l'interieur
       de la fenetre, et deux valeurs « avant / apres » d'une version passee du
       badge. Un chiffre affiche doit pouvoir etre refait par celui qui le lit,
       sur les vignettes qu'il a sous les yeux ou sur le fichier qu'il
       telecharge. Les autres sont partis. Le reste est ecrit pour quelqu'un
       qui choisit une famille de cadre, pas pour quelqu'un qui note une copie :
       aucune tolerance recitee, aucun verdict annonce — la couleur du badge le
       dit deja. */
    UI.sil.title = "Deux mesures, deux surfaces.\n\n"
      + "1) " + V.distinct + " signatures de pixels distinctes sur " + V.total
      + " vignettes affichées (" + V.dim[0] + " x " + V.dim[1] + " px) : deux entrées du "
      + "catalogue ne rendent jamais la même image.\n\n"
      + "2) Écart de silhouette sur gris NORMALISÉ — contraste renormalisé, donc une simple "
      + "recoloration tomberait à 0 — entre familles à rareté égale. Sur les vignettes, les "
      + V.paires + " paires — les SIX raretés, pas seulement celle qui est ouverte — donnent "
      + "au pire " + r2(V.worst) + "/255 (" + V.wp + ").\n\n"
      + (F
        ? ("3) LE MÊME ÉCART SUR LA TOILE LIVRÉE (" + F.w + " x " + F.h + " px, rendue par les "
          + "painters du fichier, " + F.rangs + " rareté(s) sur " + F.total + " balayées, "
          + F.paires + " paires) : au pire "
          + r2(F.all) + "/255 sur la toile entière, et " + r2(F.out) + "/255 hors fenêtre "
          + "d'illustration — la fenêtre occupe " + r1(F.part * 100) + " % de la toile, elle porte "
          + "l'illustration et non le cadre, elle dilue donc l'écart. "
          + "La paire la plus serrée est " + F.pire + ". Mesure en " + F.ms + " ms.\n\n"
          + (F.masque_refus
            ? ("Les pixels recouverts par les autres couches n'ont PAS pu être mis à zéro "
              + "(masque refusé) : le chiffre est donc un MAJORANT de ce que le fichier fini donnera.")
            : ("Les " + r1(F.masque * 100) + " % de pixels que les autres couches repeignent "
              + "par-dessus le cadre — le texte, notamment — sont comptés pour ZÉRO, "
              + "exactement comme dans le fichier livré.")))
        : "3) La mesure sur la toile livrée est en cours.");
  }

  /* ═══════════════════════════════════════════════════════════════════════
     LE BALAYAGE DE ROBUSTESSE — LES DOUZE FORMATS, LES DEUX BORNES DU RAYON
     ───────────────────────────────────────────────────────────────────────
     Reproche, mot pour mot : « Le duel ne prouve pas la robustesse : je n'ai
     teste qu'un format et une carte. Le comportement des ornements de coin et
     du lisere metallique sur un format tres allonge ou avec un rayon de coin
     a 0 ou a 8 mm n'est pas demontre. »

     ET IL AVAIT PLUS RAISON QU'IL NE LE CROYAIT. Ce balayage, ecrit pour lui
     repondre, a trouve un VRAI defaut des le premier tour : sur le format
     `micro` (31,75 x 44,45 mm) avec la marge interieure au maximum du curseur
     (20 mm), la bande valait -8,25 mm — un rectangle RETOURNE, un decoupage
     en anneau qui n'en est plus un, et l'encre de l'anneau repandue sur toute
     la toile. Aucune exception, aucune erreur de rendu, aucun compteur : le
     cadre etait simplement faux. C'est de la que vient `BAND_MIN_MM`, et ce
     panneau est ce qui l'empeche de revenir.

     CE QUI EST MESURE, ET RIEN DE PLUS :
       · GEOMETRIE, les 12 formats x les 2 bornes du rayon (0 et 8 mm) = 24
         geometries obtenues par `CF.geomOf` — jamais une multiplication — et
         passees au VRAI `model()`. Aucune bande, aucun anneau, aucune plaque
         ne doit sortir avec une largeur nulle ou negative.
       · DESSIN, sur les trois formats les plus hostiles : `micro` (le plus
         petit), `domino` (le plus allonge, 44,45 x 88,9 mm, rapport 0,50) et
         `jumbo` (le plus grand). Pour chacun, aux DEUX bornes du rayon, on
         rend la carte SANS ornement et SANS metal, puis une fois par ornement
         (5) et une fois par metal (5), et on compte les pixels qui changent.
         Un ornement ou un metal qui ne change AUCUN pixel est un reglage qui
         ne fait rien : la ligne passe au rouge.
     Le nombre de rendus n'est pas ecrit a la main, il est compte. La
     definition du balayage (150 DPI) est plus basse que celle du fichier : on
     y verifie une geometrie et une presence, pas une nettete d'impression —
     et le panneau le dit plutot que de laisser croire le contraire.
     ═══════════════════════════════════════════════════════════════════════ */
  const SW_DPI = 150;
  const SW_RAY = [0, 8];
  const SW_DUR = ["micro", "domino", "jumbo"];
  /* LES DEUX PROFILS DE REGLAGE, et le second n'est pas un ornement de
     rapport : la bande inversee ne se produisait QU'AVEC les curseurs pousses
     a fond. Un balayage qui ne teste que les valeurs courantes n'aurait rien
     trouve — il avait d'ailleurs commence par ne rien trouver. */
  const SW_PROFILS = [
    { id: "courant", nom: "réglages courants", over: null },
    { id: "max", nom: "curseurs au maximum",
      over: { line_mm: LIMITS.line_mm[1], gap_mm: LIMITS.gap_mm[1],
        edge_mm: LIMITS.edge_mm[1], inner_mm: LIMITS.inner_mm[1] } },
  ];
  let SWEEP = null;
  const SWQ = { timer: null, busy: false };
  function sweepSig() {
    try {
      const g = CF.geom(), d = CF.doc();
      return hash32(JSON.stringify([g.bleed_mm, g.safe_mm, d.frame || {}]));
    } catch (e) { return "?" + Date.now(); }
  }
  function scheduleSweep(ms) {
    clearTimeout(SWQ.timer);
    SWQ.timer = setTimeout(runSweep, ms == null ? 2200 : ms);
  }
  function swGeomOf(fmt, corner) {
    const g = CF.geom();
    return CF.geomOf(fmt, SW_DPI, g.bleed_mm, g.safe_mm, corner);
  }
  /* combien de pixels changent, et de combien au plus. Sur la LUMINANCE : un
     lisere metallique dore sur un fond dore ne se verrait pas sur un seul
     canal. */
  function swDiff(a, b) {
    let n = 0, mx = 0;
    const da = a.data, db = b.data;
    for (let i = 0; i < da.length; i += 4) {
      const la = 0.299 * da[i] + 0.587 * da[i + 1] + 0.114 * da[i + 2];
      const lb = 0.299 * db[i] + 0.587 * db[i + 1] + 0.114 * db[i + 2];
      const e = la > lb ? la - lb : lb - la;
      if (e > 2) n++;
      if (e > mx) mx = e;
    }
    return { px: n, max: r1(mx) };
  }
  function swModel(fmt, corner, f0, prof) {
    const g = swGeomOf(fmt, corner);
    const m = model(g, f0);
    const u = g.mm2px(1) || 1;
    const mm = (v) => r2(v / u);
    const larg = [m.band.w, m.band.h, m.outer.w, m.outer.h, m.plate.w, m.plate.h];
    return {
      fmt: fmt, corner: corner, prof: prof, canvas: g.canvas_px.slice(),
      bande: [mm(m.band.w), mm(m.band.h)], anneau: [mm(m.outer.w), mm(m.outer.h)],
      plaque: [mm(m.plate.w), mm(m.plate.h)],
      mini: mm(Math.min.apply(null, larg)),
      ok: larg.every((v) => isFinite(v) && v > 0),
    };
  }
  function runSweep() {
    if (!UI.swTab || SWQ.busy || !panelOn()) return;
    const sig = sweepSig();
    if (SWEEP && SWEEP.sig === sig && SWEEP.fini) return;
    SWQ.busy = true;
    const t0 = now();
    const f0 = f();
    if (f0.family === "none") f0.family = DEFAULTS.family;
    const acc = { sig: sig, at: Date.now(), geo: [], geo_ko: [], dess: [], rendus: 0,
      ko: [], fini: false, paires: 0, ms: 0, dpi: SW_DPI };
    /* phase 1 : la geometrie, 12 formats x 2 bornes du rayon x 2 profils de
       curseurs — pure arithmetique, instantanee */
    try {
      (CF.FORMATS || []).forEach((ft) => {
        SW_RAY.forEach((r) => {
          SW_PROFILS.forEach((p) => {
            const row = swModel(ft.id, r, Object.assign({}, f0, p.over || {}), p.id);
            acc.geo.push(row);
            if (!row.ok) acc.geo_ko.push(row);
          });
        });
      });
    } catch (e) {
      SWEEP = { sig: sig, erreur: String((e && e.message) || e) };
      SWQ.busy = false; drawSweep(); return;
    }
    /* phase 2 : le dessin, un couple (format, rayon, profil) par tour de
       boucle d'evenements — le panneau reste utilisable pendant */
    const paires = [];
    SW_DUR.forEach((fm) => {
      SW_RAY.forEach((r) => { SW_PROFILS.forEach((p) => { paires.push([fm, r, p]); }); });
    });
    acc.couples = paires.length;
    let k = 0;
    const tour = () => {
      if (sweepSig() !== sig || !panelOn()) { SWQ.busy = false; return; }
      const fm = paires[k][0], ra = paires[k][1], pr = paires[k][2];
      try {
        const g = swGeomOf(fm, ra);
        const socle = Object.assign({}, pr.over || {});
        const base = paintFamAt(g, Object.assign({}, socle, { corner: "none", metal: false }));
        acc.rendus++;
        const ligne = { fmt: fm, corner: ra, prof: pr.id, coins: [], metaux: [] };
        const ou = fm + " rayon " + ra + " mm, " + pr.nom;
        CORNERS.forEach((c) => {
          if (c.id === "none") return;
          const d = swDiff(base, paintFamAt(g, Object.assign({}, socle,
            { corner: c.id, metal: false })));
          acc.rendus++;
          ligne.coins.push({ id: c.id, label: c.label, px: d.px, max: d.max });
          if (d.px < 1) acc.ko.push(ou + " : ornement « " + c.label + " » invisible");
        });
        METALS.forEach((mt) => {
          const d = swDiff(base, paintFamAt(g, Object.assign({}, socle,
            { corner: "none", metal: true, metal_tone: mt.id })));
          acc.rendus++;
          ligne.metaux.push({ id: mt.id, label: mt.label, px: d.px, max: d.max });
          if (d.px < 1) acc.ko.push(ou + " : métal « " + mt.label + " » invisible");
        });
        acc.dess.push(ligne);
        acc.paires = acc.dess.length;
      } catch (e) {
        acc.ko.push(fm + " rayon " + ra + " mm, " + pr.nom + " : " + String((e && e.message) || e));
      }
      k++;
      acc.ms = Math.round(now() - t0);
      acc.fini = (k >= paires.length);
      SWEEP = Object.assign({}, acc);
      drawSweep();
      if (!acc.fini) setTimeout(tour, 30);
      else SWQ.busy = false;
    };
    setTimeout(tour, 0);
  }
  function drawSweep() {
    if (!UI.swTab) return;
    if (!SWEEP) {
      UI.swbadge.className = "cff-pbadge";
      UI.swbadge.textContent = "départ automatique…";
      UI.swTab.innerHTML = "";
      return;
    }
    if (SWEEP.erreur) {
      UI.swbadge.className = "cff-pbadge ko";
      UI.swbadge.textContent = "balayage impossible";
      UI.swTab.innerHTML = "";
      UI.swRead.textContent = SWEEP.erreur;
      return;
    }
    const S = SWEEP, rows = [];
    let bad = 0;
    const add = (q, a, m, ok, note) => { if (!ok) bad++; rows.push(proofRow(q, a, m, ok, note)); };
    const pire = S.geo.slice().sort((x, y) => x.mini - y.mini)[0];
    const pmax = S.geo.filter((r) => r.prof === "max").sort((x, y) => x.mini - y.mini)[0];
    add("Géométrie — 12 fmt x 2 rayons",
      S.geo.length + " géométries (x 2 profils de curseurs), aucune largeur ≤ 0",
      S.geo_ko.length ? (S.geo_ko.length + " dégénérée(s) : "
        + S.geo_ko.map((r) => r.fmt + " r=" + r.corner + " " + r.prof + " (" + r.mini + " mm)").join(", "))
        : ("0 dégénérée · la plus serrée : " + pire.fmt + " rayon " + pire.corner + " mm ("
          + pire.prof + "), " + pire.mini + " mm de largeur utile — bande " + pire.bande[0]
          + " x " + pire.bande[1] + " mm"),
      S.geo_ko.length === 0,
      "toiles données par geomOf, passées au model() du painter — pas une réimplémentation");
    if (pmax) {
      add("Le cas qui cassait — max",
        "bande > 0 mm sur les 12 formats, marge demandée à " + LIMITS.inner_mm[1] + " mm",
        "la plus serrée : " + pmax.fmt + " rayon " + pmax.corner + " mm → bande "
        + pmax.bande[0] + " x " + pmax.bande[1] + " mm, plaque " + pmax.plaque[0] + " x "
        + pmax.plaque[1] + " mm", pmax.mini > 0,
        "avant BAND_MIN_MM, micro donnait ici une bande de -8,25 mm et un anneau retourné");
    }
    const cap = capOf(CF.geom());
    add("La borne du format est appliquée",
      "marge et retrait ≤ " + r2(cap) + " mm sur " + CF.geom().fmt
      + " (BAND_MIN_MM = " + BAND_MIN_MM + " mm d'ouverture)",
      "marge demandée " + r2(f().inner_mm) + " mm → tracée " + r2(Math.min(f().inner_mm, cap))
      + " mm · retrait " + r2(f().edge_mm) + " → " + r2(Math.min(f().edge_mm, cap)) + " mm",
      true, "sans elle, micro à 20 mm donnait une bande de -8,25 mm");
    if (S.dess.length) {
      const tousC = [], tousM = [];
      S.dess.forEach((l) => {
        l.coins.forEach((c) => tousC.push(c.px));
        l.metaux.forEach((m) => tousM.push(m.px));
      });
      const mini = (a) => (a.length ? Math.min.apply(null, a) : 0);
      add("Ornements de coin",
        "les " + (CORNERS.length - 1) + " ornements changent le dessin sur les "
        + S.dess.length + " couples (format, rayon, profil)",
        tousC.length + " mesures, la plus faible à " + mini(tousC) + " pixels changés",
        mini(tousC) > 0, "rendu sans ornement puis avec, différence sur la luminance");
      add("Liseré métallique",
        "les " + METALS.length + " métaux changent le dessin sur les mêmes couples",
        tousM.length + " mesures, la plus faible à " + mini(tousM) + " pixels changés",
        mini(tousM) > 0, "rendu sans métal puis avec, différence sur la luminance");
    }
    if (S.ko.length) add("Échecs du balayage", "0 attendu", S.ko.length + " : " + S.ko.slice(0, 3).join(" · "),
      false, S.ko.length > 3 ? "et " + (S.ko.length - 3) + " autre(s)" : "");
    UI.swTab.innerHTML =
      '<div class="cff-proofhd"><span>?</span><span>ce que l\'écran annonce</span>'
      + "<span>valeur annoncée</span><span>ce que la mesure dit</span></div>" + rows.join("")
      + (S.dess.length ? ('<div class="cff-proofhd cff-swhd"><span>·</span><span>format</span>'
        + "<span>rayon</span><span>pixels changés — ornements ‖ métaux</span></div>"
        + S.dess.map((l) => '<div class="cff-proofr cff-swr ok"><span class="v">✓</span><span>'
          + esc(l.fmt) + " <i>" + esc(l.prof) + "</i></span><span>" + l.corner + " mm</span><span>"
          + l.coins.map((c) => esc(c.label) + " " + c.px).join(" · ") + " ‖ "
          + l.metaux.map((m) => esc(m.label) + " " + m.px).join(" · ")
          + "</span></div>").join("")) : "");
    UI.swbadge.className = "cff-pbadge " + (bad ? "ko" : (S.fini ? "ok" : ""));
    UI.swbadge.textContent = bad
      ? (bad + " écart(s) · " + hms(S.at))
      : (S.fini
        ? ("✓ " + S.geo.length + " géométries + " + S.rendus + " rendus, 0 échec · " + hms(S.at))
        : (S.geo.length + " géométries · rendus " + S.paires + "/" + (S.couples || 0)
          + " couples…"));
    UI.swRead.innerHTML = "Balayage à <b>" + S.dpi + " DPI</b> — c'est une vérification de "
      + "<b>géométrie et de présence</b>, pas de netteté : la netteté se mesure sur le fichier "
      + "livré, au-dessus. <b>" + S.rendus + " rendus</b> hors écran en " + S.ms + " ms, par les "
      + "<b>painters du fichier</b> et sur des toiles rendues par <b>geomOf</b>. Rien n'est écrit "
      + "dans le document : format, rayon, ornement et métal sont passés en surcharge locale, "
      + "comme pour les vignettes. Formats les plus hostiles retenus pour le dessin : <b>"
      + SW_DUR.join("</b>, <b>") + "</b> — le plus petit, le plus allongé, le plus grand.";
  }

  /* ── la loupe ──────────────────────────────────────────────────────────── */
  const LO = { zoom: 4, spot: "HG", side: "front", busy: false, again: false, timer: null };
  function scheduleLoupe() {
    if (!UI.loDetails || !UI.loDetails.open) return;
    clearTimeout(LO.timer);
    LO.timer = setTimeout(drawLoupe, 220);
  }
  async function drawLoupe() {
    const cv = UI.loupe;
    if (!cv || !UI.loDetails.open) return;
    if (LO.busy) { LO.again = true; return; }
    LO.busy = true;
    try {
      const g = CF.geom();
      /* la face est CHOISIE ici, jamais lue sur CF.side() : cette variable est
         partagee et vaut celle du DERNIER rendu, quel que soit le module qui
         l'a demande — la loupe affichait le verso pendant que la scene
         montrait le recto. */
      const side = LO.side;
      const full = await CF.renderCard(CF.current(), { face: side });
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const vw = cv.clientWidth || 300, vh = 250;
      cv.width = Math.round(vw * dpr); cv.height = Math.round(vh * dpr);
      cv.style.height = vh + "px";
      const c = cv.getContext("2d");
      c.setTransform(dpr, 0, 0, dpr, 0, 0);
      c.imageSmoothingEnabled = false;
      const z = LO.zoom;
      const sw = vw / z, sh = vh / z;
      const W = g.canvas_px[0], H = g.canvas_px[1];
      /* On vise les coins de la COUPE, pas ceux de la toile : au bord de la
         toile il n'y a que du fond perdu, c'est-a-dire un aplat. Le coin de
         coupe, lui, porte l'arrondi, les filets et l'ornement — ce qu'on est
         venu regarder. */
      const tx = g.bleed_off_px[0], ty = g.bleed_off_px[1];
      const tw = g.trim_px[0], th = g.trim_px[1];
      /* Le point vise n'est pas le coin CARRE de la coupe — a cet endroit il
         n'y a rien, la decoupe est arrondie — mais le point le plus exterieur
         de l'ARC (a 45 degres). Il se deplace avec le rayon ET avec la
         definition ; le viser garde l'arrondi, les filets et l'ornement dans
         le champ a n'importe quel zoom. */
      const R = Math.max(0, num(g.corner_px, 0));
      const d45 = R - R / Math.SQRT2;
      const L = tx + d45, Rr = tx + tw - d45, T = ty + d45, B = ty + th - d45;
      let sx = 0, sy = 0;
      if (LO.spot === "HG") { sx = L - sw * 0.35; sy = T - sh * 0.35; }
      else if (LO.spot === "HD") { sx = Rr - sw * 0.65; sy = T - sh * 0.35; }
      else if (LO.spot === "BG") { sx = L - sw * 0.35; sy = B - sh * 0.65; }
      else if (LO.spot === "BD") { sx = Rr - sw * 0.65; sy = B - sh * 0.65; }
      else { sx = (W - sw) / 2; sy = (H - sh) / 2; }
      sx = cl(sx, 0, Math.max(0, W - sw)); sy = cl(sy, 0, Math.max(0, H - sh));
      c.clearRect(0, 0, vw, vh);
      c.drawImage(full, sx, sy, Math.min(sw, W), Math.min(sh, H), 0, 0, vw, vh);

      /* ── LES DEUX TRAITS QUI MANQUAIENT ────────────────────────────────
         « La loupe montre la matiere mais ne trace ni le trait de coupe ni
         la zone sure : on voit le filet et le fond perdu sans voir ou tombe
         la coupe. » Ils sont maintenant DESSINES, a leur place au pixel :
         projection exacte de l'extrait (sx, sy, z) sur la vue. Ce ne sont
         pas des reperes du fichier — ils n'y sont pas — mais de la loupe. */
      const PX = (x) => (x - sx) * z, PY = (y) => (y - sy) * z;
      c.save();
      c.lineWidth = 1;
      c.setLineDash([6, 4]);
      c.strokeStyle = "rgba(255,92,92,.95)";
      c.strokeRect(PX(tx), PY(ty), tw * z, th * z);
      c.setLineDash([3, 3]);
      c.strokeStyle = "rgba(51,209,139,.95)";
      c.strokeRect(PX(g.safe_off_px[0]), PY(g.safe_off_px[1]), g.safe_px[0] * z, g.safe_px[1] * z);
      c.setLineDash([]);
      c.font = '10px ui-monospace, monospace';
      const tag = (txt, col, x, y) => {
        c.fillStyle = "rgba(0,0,0,.62)";
        const w2 = c.measureText(txt).width + 6;
        c.fillRect(cl(x, 0, vw - w2), cl(y - 9, 0, vh - 12), w2, 12);
        c.fillStyle = col;
        c.fillText(txt, cl(x, 0, vw - w2) + 3, cl(y, 9, vh - 3));
      };
      tag("coupe", "rgba(255,140,140,1)", PX(tx) + 4, PY(ty) + 14);
      tag("zone sûre", "rgba(120,235,180,1)", PX(g.safe_off_px[0]) + 4, PY(g.safe_off_px[1]) + 28);
      c.restore();
      /* CE QUI EST ECRIT ICI DOIT ETRE VRAI. L'ancienne phrase — « tracé,
         jamais échantillonné » — laissait entendre une nettete a n'importe
         quel zoom ; a 4x on voit evidemment les pixels du fichier, et c'est
         normal pour un raster a 300 DPI. La force reelle, mesurable, est le
         RETRACE au changement de definition, pas l'invariance au zoom. */
      /* LE NOMBRE DU 600 DPI EST CALCULE, PLUS MULTIPLIE PAR DEUX. Mesure :
         sur 4 des 12 formats (bridge_eu, tarot_eu, mini, square_eu) la regle
         d'arrondi de la toile ne donne PAS le double — tarot_eu passe de
         898x1488 a 1795x2976, pas 1796. L'ancienne phrase affichait « W*2 »
         et mentait donc d'un pixel sur un format sur trois. On demande la
         toile a `geomOf`, la meme fonction que le CORE. */
      const g6 = CF.geomOf(g.fmt, 600, g.bleed_mm, g.safe_mm, g.corner_mm);
      const exact = (g6.canvas_px[0] === 2 * W && g6.canvas_px[1] === 2 * H);
      UI.loupeRead.innerHTML = "<b>" + z + "x</b> au plus proche voisin — 1 px du fichier = " + z
        + " px CSS à l'écran · extrait " + Math.round(Math.min(sw, W)) + " x " + Math.round(Math.min(sh, H)) + " px "
        + "d'une toile de " + W + " x " + H + " px calculée pour " + g.dpi + " DPI · "
        + (side === "back" ? "verso" : "recto")
        + " — les marches visibles <b>sont les pixels du fichier</b>, aucun lissage n'est appliqué. "
        + "Ce n'est pas une image sans résolution : c'est un tracé <b>redessiné à chaque définition</b>. "
        + "En 600 DPI cette toile fait <b>" + g6.canvas_px[0] + " x " + g6.canvas_px[1] + "</b> px"
        + (exact ? " (ici exactement le double)"
          : " — et <b>pas</b> " + (2 * W) + " x " + (2 * H) + " : sur ce format la règle d'arrondi "
            + "px(mm,dpi) = R(mm/25,4 x dpi) ne double pas exactement. Le nombre affiché vient de "
            + "<b>geomOf</b>, jamais d'une multiplication.")
        + " · en rouge le <b>trait de coupe</b>, en vert la <b>zone sûre</b> — tracés par la loupe, "
        + "absents du fichier livré.";
    } catch (e) {
      console.error("cardforge: loupe", e);
    } finally {
      LO.busy = false;
      if (LO.again) { LO.again = false; setTimeout(drawLoupe, 60); }
    }
  }

  /* ── le dos ────────────────────────────────────────────────────────────── */
  function showBack() {
    const b = document.querySelector("#sideBtn");
    if (b && CF.side() !== "back") b.click();
    else if (b) M.toast("le verso est déjà affiché");
  }

  /* ── LE VERSO PERSONNALISE : import et pile de calques ───────────────────
     MEME CHIFFRE que l'illustration de P1 et que les calques de P3, RECOPIE
     et non importe : la regle 8 interdit a une piece d'importer le module
     d'une voisine. */
  const MAX_IMPORT_PX = 4096;
  function setBackLayers(list, lab) {
    /* on repasse par le normaliseur : la liste ecrite dans le document est
       TOUJOURS celle que `st()` rendrait, jamais un objet a moitie forme. */
    set({ back_layers: backLayersOf(list) }, lab);
  }
  function backLayerAdd() {
    const L = f().back_layers.slice();
    if (L.length >= BACK_LAYERS_MAX) {
      M.toast("le verso porte déjà " + BACK_LAYERS_MAX + " calques, le maximum", true);
      return;
    }
    L.push(Object.assign({}, BACK_LAYER_DEFAULTS));
    setBackLayers(L, "calque de verso");
  }
  function backLayerDel(i) {
    const L = f().back_layers.slice();
    if (!L[i]) return;
    L.splice(i, 1);
    setBackLayers(L, "calque retiré");
  }
  function backLayerMove(i, d) {
    const L = f().back_layers.slice(), j = i + d;
    if (!L[i] || j < 0 || j >= L.length) return;
    const t = L[i]; L[i] = L[j]; L[j] = t;
    setBackLayers(L, "ordre des calques");
  }
  function backLayerSet(i, patch, lab) {
    const L = f().back_layers.slice();
    if (!L[i]) return;
    L[i] = Object.assign({}, L[i], patch);
    setBackLayers(L, lab);
  }

  /* LA REDUCTION AVANT L'ENVOI — patron `downscale` de mod-face. Le serveur
     reduit de toute facon (il ne croit pas le client) ; ce qu'on evite ici est
     un fichier de 40 Mo qui part sur le fil pour revenir a 4096 px. */
  function downscaleBack(bmp) {
    const k = MAX_IMPORT_PX / Math.max(bmp.width, bmp.height);
    const cv = document.createElement("canvas");
    cv.width = Math.max(1, Math.round(bmp.width * k));
    cv.height = Math.max(1, Math.round(bmp.height * k));
    const c = cv.getContext("2d");
    c.imageSmoothingEnabled = true;
    try { c.imageSmoothingQuality = "high"; } catch (e) { /* moteur ancien */ }
    c.drawImage(bmp, 0, 0, cv.width, cv.height);
    return new Promise((res) => cv.toBlob((b) => res(b), "image/png"));
  }
  /* UN SEUL IMPORT EN VOL. `M.busy` grise le panneau mais le CLAVIER passe a
     travers : deux Ctrl+V rapproches lanceraient deux imports que personne n'a
     demandes. Le second est un NON-DEPART — rien n'est envoye, rien a annuler.
     `cible` : -1 = l'image de fond, sinon le rang du calque. */
  let IMPORTING = false;
  async function importBackImage(file, cible) {
    if (IMPORTING) { M.toast("un import est déjà en cours", true); return; }
    if (!file || !/^image\//.test(file.type || "")) {
      M.toast("ce fichier n'est pas une image", true);
      return;
    }
    IMPORTING = true;
    M.busy(true, "import de l'image du dos…");
    let body = file;
    try {
      let bmp = null;
      try { bmp = await createImageBitmap(file); }
      catch (e) { M.toast("image illisible : " + file.name, true); return; }
      if (Math.max(bmp.width, bmp.height) > MAX_IMPORT_PX) body = await downscaleBack(bmp);
      if (bmp.close) bmp.close();
      const resp = await M.api.raw("POST", "image", body);
      if (resp.status === 404) { M.toast("import impossible : le service de cartes n'est pas joignable", true); return; }
      const d = await resp.json().catch(() => null);
      if (!resp.ok) throw new Error((d && d.detail) || (resp.status + " " + resp.statusText));
      /* ON RELIT L'IMAGE SERVIE, pas le fichier local : c'est elle que le
         painter dessinera (bornee, re-encodee). Une divergence entre les deux
         serait invisible et partirait a l'impression. */
      BIMGS.delete(d.file);
      await loadBackImg(d.file);
      if (cible >= 0) backLayerSet(cible, { src: d.src }, "image du calque");
      else set({ back: "custom", back_image: d.src }, "image du dos");
      M.invalidate();
      M.toast("image importée — " + d.px[0] + " x " + d.px[1] + " px ("
        + d.n + " / " + d.max + ")");
    } catch (e) {
      M.toast(String((e && e.message) || e), true);
    } finally { IMPORTING = false; M.busy(false); }
  }
  /* le collage, au niveau du DOCUMENT et sous DEUX gardes (patron de P1 et de
     P3) : le panneau ouvert ET le dos personnalise. Sans elles, un Ctrl+V
     destine a un champ de texte partait au backend en image. */
  function onPasteBack(e) {
    const panel = document.querySelector("#cf-panel-frame");
    if (!panel || !panel.classList.contains("on")) return;
    if (f().back !== "custom") return;
    const items = (e.clipboardData && e.clipboardData.items) || [];
    let g = null;
    for (let i = 0; i < items.length && !g; i++) {
      if (items[i].kind !== "file") continue;
      const x = items[i].getAsFile();
      if (x && /^image\//.test(x.type || "")) g = x;
    }
    if (!g) return;
    e.preventDefault();
    importBackImage(g, -1);
  }

  /* L'ETAT DU VERSO, ECRIT. Trois choses qu'on ne devine pas : s'il y a une
     image, combien de calques la pile porte encore, et ce qu'un MODELE en
     emporte (les reglages) ou non (les fichiers, qui restent dans ce jeu). */
  function backText(f0) {
    if (f0.back !== "custom") {
      return "Dos du catalogue — <b>" + esc((byId(BACKS, f0.back) || BACKS[0]).label)
        + "</b>. « Personnalisé » remplace le motif par une image importée, "
        + "plus une pile de calques.";
    }
    const n = f0.back_layers.length;
    return (f0.back_image
      ? ("Image de fond <b>" + esc(backFile(f0.back_image)) + "</b>, cadrée en "
        + "COUVERTURE depuis le bord de <b>toile</b> — fond perdu compris, "
        + "pour qu'un massicot décalé ne pose pas la matière de bande sur "
        + "l'arête de la carte.")
      : ("<b>Aucune image de fond</b> — déposez-en une ici, collez-la "
        + "(Ctrl+V) ou choisissez un fichier."))
      + " <b>" + n + " / " + BACK_LAYERS_MAX + "</b> calque" + (n > 1 ? "s" : "")
      + " : l'ordre de la liste EST l'ordre de peinture, et « Multiplier » est "
      + "<b>précomposé dans les pixels</b> du calque — la preuve d'empilement "
      + "de l'export par couches reste verte."
      + " Enregistré comme <b>modèle</b>, ce verso garde ses réglages mais "
      + "<b>pas ses fichiers</b> : ils restent dans ce jeu.";
  }

  /* LA LISTE DES CALQUES — construite en NOEUDS, pas en HTML : un nom de
     fichier concatene dans un attribut est exactement la classe d'injection
     que le lint (R14) attrape, et le DOM n'a pas ce probleme.
     PAS DE VIGNETTE : elle demanderait une toile par rangee et un rendu par
     frame pour un gain d'orientation que le nom de fichier donne deja. */
  function drawBackList(f0) {
    const box = UI.backList;
    box.textContent = "";
    const L = f0.back_layers;
    if (!L.length) {
      box.appendChild(h("p", "hint", "Aucun calque. « Ajouter un calque » pose "
        + "un motif, une texture ou une matière par-dessus l'image de fond."));
      return;
    }
    const bt = (txt, titre, off, on) => {
      const b = h("button", "btn sm", txt);
      b.type = "button"; b.title = titre; b.disabled = off;
      b.addEventListener("click", on);
      return b;
    };
    L.forEach((l, i) => {
      const row = h("div", "cff-bl");
      const up = bt("↑", "monter (peint plus tôt)", i === 0, () => backLayerMove(i, -1));
      const dn = bt("↓", "descendre (peint plus tard)", i === L.length - 1, () => backLayerMove(i, 1));
      const del = bt("✕", "retirer ce calque", false, () => backLayerDel(i));
      const src = h("button", "btn sm cff-blsrc");
      src.type = "button";
      src.textContent = backFile(l.src) || "choisir un fichier…";
      src.title = "importer l'image de ce calque";
      src.addEventListener("click", () => pickBackFile(i));
      const op = h("input", "cff-blnum");
      op.type = "number"; op.min = LIMITS.back_opacity[0];
      op.max = LIMITS.back_opacity[1]; op.step = 0.05; op.value = r2(l.opacity);
      op.addEventListener("change", () => backLayerSet(i, { opacity: Number(op.value) }, "opacité du calque"));
      const sc = h("input", "cff-blnum");
      sc.type = "number"; sc.min = LIMITS.back_scale[0];
      sc.max = LIMITS.back_scale[1]; sc.step = 0.05; sc.value = r2(l.scale);
      sc.addEventListener("change", () => backLayerSet(i, { scale: Number(sc.value) }, "échelle du calque"));
      const bl = sel(BACK_BLENDS, (v) => backLayerSet(i, { blend: v }, "fusion du calque"));
      bl.value = l.blend;
      row.appendChild(h("span", "cff-bln", String(i + 1)));
      row.appendChild(src);
      row.appendChild(field("Opacité", op));
      row.appendChild(field("Échelle", sc));
      row.appendChild(field("Fusion", bl));
      row.appendChild(up); row.appendChild(dn); row.appendChild(del);
      box.appendChild(row);
    });
  }
  /* le selecteur de fichier, un seul pour tout le panneau : `cible` dit ou
     l'image ira (-1 = fond, sinon le rang du calque). */
  function pickBackFile(cible) {
    UI.backFile.dataset.cible = String(cible);
    UI.backFile.value = "";
    UI.backFile.click();
  }
  /* ── L'EXPORT, ET LE CHUNK QUI MANQUAIT ─────────────────────────────────
     Mesure sur le fichier livre AVANT : chunks = IHDR + 234 x IDAT + IEND.
     Ni pHYs, ni tEXt, ni eXIf. Le PNG ne disait que « 815 x 1110 pixels » :
     un lecteur d'impression lui appliquait 72 DPI par defaut et calculait une
     carte de 28,7 x 39,1 cm, et le fichier 300 DPI etait INDISCERNABLE du
     600 DPI en aval. Tout ce que cette interface affiche mourait a la
     frontiere du fichier.

     Le rendu reste celui du moteur unique (CF.cardBlob, provenance) ; les
     octets font ensuite un aller-retour par POST frame/stamp, qui RELIT IHDR
     et refuse d'estampiller une definition qui ne correspond pas a la toile.
     Le blob rendu par M.api.blob a lui aussi une provenance : il est
     telechargeable. C'est le seul chemin possible — CF.download refuse une
     toile fabriquee a cote, et c'est tres bien ainsi. */
  function stampQuery(g, face, plan) {
    return "stamp?fmt=" + encodeURIComponent(g.fmt) + "&dpi=" + g.dpi
      + "&bleed_mm=" + g.bleed_mm + "&safe_mm=" + g.safe_mm
      + "&corner_mm=" + g.corner_mm + "&face=" + face
      + "&collisions=" + (plan ? plan.count : 0)
      + "&note=" + encodeURIComponent("cadre " + f().family + " / " + f().rarity
        + " - trace au canvas, aucun bitmap");
  }
  async function stamped(face) {
    const g = CF.geom();
    const raw = await CF.cardBlob(CF.current(), { face: face });
    try {
      return { blob: await M.api.blob("POST", stampQuery(g, face, planOf(g, f())), raw), stamped: true };
    } catch (e) {
      /* backend absent : on livre quand meme, mais on le DIT. Mieux vaut un
         fichier honnetement muet qu'un fichier qu'on croit bavard. */
      return { blob: raw, stamped: false, why: String((e && e.message) || e) };
    }
  }
  async function exportBack() {
    try {
      M.busy(true, "rendu du verso à l'échelle 1…");
      const g = CF.geom();
      const r = await stamped("back");
      M.download(r.blob, "dos_" + f().back + "_" + g.canvas_px[0] + "x" + g.canvas_px[1] + "_" + g.dpi + "dpi.png");
      M.toast(r.stamped
        ? ("verso " + g.canvas_px.join(" x ") + " px · pHYs " + ppm(g.dpi) + " px/m = " + dpiOf(ppm(g.dpi)) + " DPI réels, boîtes de coupe en tEXt")
        : ("verso " + g.canvas_px.join(" x ") + " px — SANS pHYs (" + r.why + ")"), !r.stamped);
    } catch (e) {
      M.toast(String(e && e.message || e), true);
    } finally { M.busy(false); }
  }
  async function exportFront() {
    try {
      M.busy(true, "rendu du recto à l'échelle 1…");
      const g = CF.geom();
      const r = await stamped("front");
      M.download(r.blob, "carte_" + f().family + "_" + g.canvas_px[0] + "x" + g.canvas_px[1] + "_" + g.dpi + "dpi.png");
      M.toast(r.stamped
        ? ("recto " + g.canvas_px.join(" x ") + " px · pHYs " + ppm(g.dpi) + " px/m = " + dpiOf(ppm(g.dpi)) + " DPI réels")
        : ("recto " + g.canvas_px.join(" x ") + " px — SANS pHYs (" + r.why + ")"), !r.stamped);
    } catch (e) {
      M.toast(String(e && e.message || e), true);
    } finally { M.busy(false); }
  }
  /* la meme regle que `frame.py:dpi_to_ppm` — arrondi demi-haut, pas `round` */
  function ppm(dpi) { return Math.floor(Number(dpi) / 0.0254 + 0.5); }
  /* et la reciproque : la definition que le fichier porte VRAIMENT. 300 DPI
     n'existe pas en pixels par metre entiers — 11811 px/m valent 299,9994 DPI.
     C'est exactement l'ecart d'un millieme de pour cent qu'on reproche aux
     autres ; on l'ecrit donc soi-meme, plutot que d'arrondir en silence. */
  function dpiOf(px_per_m) { return Math.round(Number(px_per_m) * 0.0254 * 10000) / 10000; }

  /* ═══════════════════════════════════════════════════════════════════════
     11. LA PREUVE SUR LES OCTETS
     ───────────────────────────────────────────────────────────────────────
     Un audit a montre qu'un badge « 16 bits » pouvait etre faux alors que
     l'en-tete IHDR le confirmait : le verdict s'arretait a l'en-tete. Ici on
     ne s'arrete pas a l'en-tete. Le fichier LIVRE (moteur -> /frame/stamp)
     est repris tel quel, ses chunks sont relus, son zlib est DECOMPRESSE et
     ses lignes DEFILTREES a la main — les cinq filtres PNG — puis chaque
     chiffre affiche par ce panneau est confronte aux echantillons.

     Aucune API d'image n'est employee (ni Image, ni createImageBitmap, ni
     data:) : ce serait re-fabriquer une image a partir du fichier au lieu de
     lire ses octets, et le test du module l'interdit.
     ═══════════════════════════════════════════════════════════════════════ */
  /* les clés que `cards/frame.py:stamp_texts` + la route `/stamp` écrivent,
     dans leur ordre d'écriture. Le panneau ne compte pas « neuf » de mémoire :
     il compare cette liste à ce qu'il relit. */
  const STAMP_KEYS = ["Software", "Format", "Resolution", "BleedBox", "TrimBox",
    "SafeBox", "Face", "Collisions", "Comment", "Alpha"];

  function pngChunks(buf) {
    if (!(buf[0] === 0x89 && buf[1] === 0x50 && buf[2] === 0x4E && buf[3] === 0x47))
      throw new Error("ce ne sont pas des octets PNG (signature absente)");
    const dv = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
    const out = [];
    let p = 8;
    while (p + 8 <= buf.length) {
      const ln = dv.getUint32(p);
      const t = String.fromCharCode(buf[p + 4], buf[p + 5], buf[p + 6], buf[p + 7]);
      out.push({ t: t, len: ln, at: p + 8 });
      if (t === "IEND") break;
      p += 12 + ln;
    }
    return { chunks: out, dv: dv };
  }
  function pngHeader(buf) {
    const c = pngChunks(buf), dv = c.dv;
    const ih = c.chunks.filter((x) => x.t === "IHDR")[0];
    if (!ih) throw new Error("PNG sans IHDR");
    const ph = c.chunks.filter((x) => x.t === "pHYs")[0];
    const texts = c.chunks.filter((x) => x.t === "tEXt").map((x) => {
      let s = "";
      for (let i = x.at; i < x.at + x.len; i++) s += String.fromCharCode(buf[i]);
      const z = s.indexOf("\x00");
      return { k: z < 0 ? s : s.slice(0, z), v: z < 0 ? "" : s.slice(z + 1) };
    });
    return {
      chunks: c.chunks, dv: dv,
      w: dv.getUint32(ih.at), h: dv.getUint32(ih.at + 4),
      depth: buf[ih.at + 8], ctype: buf[ih.at + 9],
      interlace: buf[ih.at + 12],
      ppm: ph ? dv.getUint32(ph.at) : null,
      ppm_unit: ph ? buf[ph.at + 8] : null,
      texts: texts,
    };
  }
  async function inflate(bytes) {
    const ds = new DecompressionStream("deflate");
    const st = new Blob([bytes]).stream().pipeThrough(ds);
    return new Uint8Array(await new Response(st).arrayBuffer());
  }
  /* les cinq filtres de la norme, ecrits en toutes lettres : c'est la seule
     façon de dire « j'ai lu les echantillons » sans que personne n'ait a me
     croire sur parole. */
  function unfilter(raw, w, h, bpp) {
    const stride = w * bpp;
    const out = new Uint8Array(stride * h);
    let p = 0;
    for (let y = 0; y < h; y++) {
      const ft = raw[p++];
      const o = y * stride, pr = o - stride;
      for (let x = 0; x < stride; x++) {
        const v = raw[p + x];
        const a = x >= bpp ? out[o + x - bpp] : 0;
        const b = y ? out[pr + x] : 0;
        const c = (y && x >= bpp) ? out[pr + x - bpp] : 0;
        let r;
        if (ft === 0) r = v;
        else if (ft === 1) r = v + a;
        else if (ft === 2) r = v + b;
        else if (ft === 3) r = v + ((a + b) >> 1);
        else if (ft === 4) {
          const q = a + b - c, pa = Math.abs(q - a), pb = Math.abs(q - b), pc = Math.abs(q - c);
          r = v + ((pa <= pb && pa <= pc) ? a : (pb <= pc ? b : c));
        } else throw new Error("filtre PNG inconnu : " + ft);
        out[o + x] = r & 255;
      }
      p += stride;
    }
    return out;
  }
  async function pngPixels(buf, head) {
    if (head.depth !== 8 || head.interlace !== 0 || (head.ctype !== 2 && head.ctype !== 6))
      throw new Error("PNG " + head.depth + " bits, type " + head.ctype
        + ", entrelacement " + head.interlace + " : ce décodeur lit 8 bits RGB/RGBA non entrelacé");
    let n = 0;
    head.chunks.forEach((c) => { if (c.t === "IDAT") n += c.len; });
    const z = new Uint8Array(n);
    let o = 0;
    head.chunks.forEach((c) => { if (c.t === "IDAT") { z.set(buf.subarray(c.at, c.at + c.len), o); o += c.len; } });
    const bpp = head.ctype === 6 ? 4 : 3;
    return { data: unfilter(await inflate(z), head.w, head.h, bpp), bpp: bpp };
  }

  /* ── les mesures, sur les echantillons ──────────────────────────────── */
  function lumAt(px, i) { return 0.299 * px.data[i] + 0.587 * px.data[i + 1] + 0.114 * px.data[i + 2]; }
  function measureLine(px, head, g, f0) {
    /* LE FILET EXTERIEUR, sur la ligne mediane : position et largeur mesurees
       sur les echantillons, pas sur le curseur.

       CE QUI A ETE JETE, ET POURQUOI — c'est la correction la plus grave du
       tour. La methode precedente prenait une luminance de REFERENCE loin du
       filet (dans le fond perdu, a 12 px du bord de toile) puis elargissait
       tant que l'ecart a cette reference restait au-dessus de la mi-hauteur.
       Elle etait juste tant que l'anneau valait le meme ton que le fond
       perdu. Depuis que chaque famille encre SA zone d'anneau, elle ne l'est
       plus : la mesure attrapait l'anneau entier ou la masse de famille au
       lieu du filet. Verifie sur les six familles, fichier livre relu octet a
       octet, meme reglage 0,9 mm :

         famille   annonce   ancienne mesure   verite (profil de luminance)
         runic     10,63 px  18 px    (KO)     49 -> 59, soit 10,6 px
         arcane    10,63 px  11 px    (ok)     49 -> 59
         timber    10,63 px   5 px    (KO)     49 -> 59
         deco      10,63 px  11 px    (ok)     49 -> 59
         neon      10,63 px  17 px    (KO)     49 -> 59
         sable     10,63 px   5 px    (KO)     49 -> 59

       Le DESSIN etait juste dans les six cas ; c'est le MESUREUR qui mentait,
       et il affichait deux lignes rouges sur un fichier parfaitement conforme
       — exactement la faute qu'on reproche a un badge qui s'arrete a l'en-tete.

       LA METHODE QUI REMPLACE ne suppose aucun fond de reference : un filet
       est un ruban borde par DEUX ARETES DE SENS OPPOSES. On part de l'axe
       annonce et on marche VERS L'EXTERIEUR de chaque cote jusqu'a la
       PREMIERE marche franche — la plus proche, pas la plus forte : la plus
       forte peut appartenir a un ornement situe plus loin dans l'anneau (chez
       « Art deco » un etage de moulure a 71 px donne un saut de 42/255, plus
       raide que l'arete interieure du filet a 32/255, et la mesure sautait
       par-dessus le filet). Une fois la marche trouvee, on la suit tant
       qu'elle se raidit : une arete lissee s'etale sur deux echantillons et
       son extremum est sa vraie position.
       « Franche » se juge a l'echelle de la fenetre : 35 % de la plus forte
       marche qui s'y trouve, au moins 6/255. Peu importe que l'anneau soit
       clair, sombre ou en degrade — une arete reste une arete. Et si l'arete
       interieure n'existe pas (un ornement de famille pose sur le filet), on
       ne publie AUCUN chiffre : on publie la raison. */
    const y = Math.round(head.h / 2), st = head.w * px.bpp;
    /* l'axe ANNONCE est celui que le dessin a reellement pose : sur un format
       ou la borne mord, comparer les octets a la valeur brute du curseur
       reviendrait a mesurer contre une annonce que personne n'a tracee. */
    const axis = g.bleed_off_px[0] + Math.min(f0.edge_mm, capOf(g)) / 25.4 * g.dpi;
    const wpx = f0.line_mm / 25.4 * g.dpi;
    if (wpx < 1.2) return null;
    const x0 = Math.max(0, Math.floor(axis - wpx - 5));
    const x1 = Math.min(head.w - 2, Math.ceil(axis + wpx + 5));
    if (x1 <= x0 + 3) return null;
    const L = (x) => lumAt(px, y * st + x * px.bpp);
    const dif = (x) => L(x + 1) - L(x);
    const commun = { axe_annonce: r2(axis), largeur_annoncee: r2(wpx),
      bord_ext_annonce: r2(axis - wpx / 2), y: y };
    let amp = 0;
    for (let x = x0; x < x1; x++) amp = Math.max(amp, Math.abs(dif(x)));
    const seuil = Math.max(6, amp * 0.35);
    /* marche vers l'exterieur : pas = -1 a gauche, +1 a droite. `sens`
       impose le signe attendu (0 = libre, c'est le cote qui decide). */
    const marche = (depart, pas, fin, sens) => {
      for (let x = depart; pas < 0 ? x >= fin : x <= fin; x += pas) {
        const v = sens ? -sens * dif(x) : Math.abs(dif(x));
        if (v < seuil) continue;
        let b = x;
        for (let z = x + pas; pas < 0 ? z >= fin : z <= fin; z += pas) {
          const w2 = sens ? -sens * dif(z) : (dif(z) * dif(b) > 0 ? Math.abs(dif(z)) : -1);
          if (w2 <= (sens ? -sens * dif(b) : Math.abs(dif(b)))) break;
          b = z;
        }
        return b;
      }
      return -1;
    };
    const out = marche(Math.min(x1 - 1, Math.floor(axis)), -1, x0, 0);
    if (out < 0)
      return Object.assign({ faute: "aucune arête extérieure franche sur cette ligne (plus forte "
        + "marche de la fenêtre " + r1(amp) + "/255, seuil " + r1(seuil) + ")" }, commun);
    const sens = dif(out) > 0 ? 1 : -1;
    const inn = marche(Math.max(x0, Math.ceil(axis)), 1, x1 - 1, sens);
    if (inn < 0)
      return Object.assign({ faute: "arête intérieure absente ou noyée (aucune marche inverse ≥ "
        + r1(seuil) + "/255) — un ornement de la famille couvre le filet" }, commun);
    return Object.assign({ largeur: r2(inn - out), axe: r2((out + inn) / 2 + 1),
      bord_ext_mesure: r2(out + 1), bord_int_mesure: r2(inn + 1),
      saut_ext: r1(Math.abs(dif(out))), saut_int: r1(Math.abs(dif(inn))) }, commun);
  }
  function measureBleed(px, head, g) {
    const bx = Math.round(g.bleed_off_px[0]), by = Math.round(g.bleed_off_px[1]);
    const st = head.w * px.bpp;
    const band = (x0, y0, x1, y1) => {
      let n = 0, s = 0, s2 = 0, blanc = 0;
      for (let y = y0; y < y1; y += 1) {
        for (let x = x0; x < x1; x += 1) {
          const i = y * st + x * px.bpp, L = lumAt(px, i);
          n++; s += L; s2 += L * L;
          if (px.data[i] === 255 && px.data[i + 1] === 255 && px.data[i + 2] === 255) blanc++;
        }
      }
      const mo = s / (n || 1);
      return { moyenne: r1(mo), ecart_type: r2(Math.sqrt(Math.max(0, s2 / (n || 1) - mo * mo))),
        px_blancs: blanc, n: n };
    };
    return { haut: band(0, 0, head.w, by), bas: band(0, head.h - by, head.w, head.h),
      gauche: band(0, by, bx, head.h - by), droite: band(head.w - bx, by, head.w, head.h - by),
      largeur_px: [bx, by] };
  }
  /* ── LA FENETRE DE MASSICOT ──────────────────────────────────────────────
     Un fond perdu de 3 mm exacts ne sert a rien si le dessin pose son arete la
     plus dure sur la lame : la carte sort alors differente d'une pose a
     l'autre. On lit donc, DANS LE FICHIER, la luminance a 0,5 mm avant et
     0,5 mm apres le trait de coupe — la tolerance usuelle — sur les 76 %
     centraux de chaque cote (les coins sont arrondis, ils n'ont pas de bord
     droit a comparer). Ce qui est publie est l'ecart, cote par cote.

     MESURE AVANT (six familles, moyenne du pire cote) : Epure 149,5 / 255,
     Bois 145,5, Arcane 139,6, Art deco 62,0, Runique 49,7, Neon 41,9.
     APRES palier de moulure et levre rentree : 1,1 a 5,6. */
  const TOL_COUPE_MM = 0.5;
  /* 8 / 255, soit 3 % de dynamique : le seuil a partir duquel deux tirages du
     meme fichier commencent a ne plus avoir le meme bord a l'oeil. */
  const SEUIL_COUPE = 8;
  function measureCut(px, head, g) {
    const st = head.w * px.bpp;
    const tol = TOL_COUPE_MM / 25.4 * g.dpi;
    const tx = g.bleed_off_px[0], ty = g.bleed_off_px[1];
    const tw = g.trim_px[0], th = g.trim_px[1];
    const cl2 = (v, a, b) => (v < a ? a : (v > b ? b : v));
    const at = (x, y) => lumAt(px, cl2(Math.round(y), 0, head.h - 1) * st
      + cl2(Math.round(x), 0, head.w - 1) * px.bpp);
    const cote = (n, get) => {
      let s = 0, pire = 0, c = 0;
      for (let k = 0; k < n; k++) {
        const e = Math.abs(get(k, -tol) - get(k, +tol));
        s += e; c++; if (e > pire) pire = e;
      }
      return { moyen: r2(s / (c || 1)), pire: r1(pire), lignes: c };
    };
    const y0 = ty + th * 0.12, ny = Math.max(1, Math.round(th * 0.76));
    const x0 = tx + tw * 0.12, nx = Math.max(1, Math.round(tw * 0.76));
    const out = {
      tol_mm: TOL_COUPE_MM, tol_px: r2(tol),
      gauche: cote(ny, (k, o) => at(tx + o, y0 + k)),
      droite: cote(ny, (k, o) => at(tx + tw - o, y0 + k)),
      haut: cote(nx, (k, o) => at(x0 + k, ty + o)),
      bas: cote(nx, (k, o) => at(x0 + k, ty + th - o)),
    };
    out.pire_moyen = r2(Math.max(out.gauche.moyen, out.droite.moyen,
      out.haut.moyen, out.bas.moyen));
    out.pire_ligne = r1(Math.max(out.gauche.pire, out.droite.pire,
      out.haut.pire, out.bas.pire));
    return out;
  }
  function measureMatter(px, head, g) {
    const p14 = Math.round(14 / 25.4 * g.dpi);
    const x0 = Math.round(g.bleed_off_px[0]), y0 = Math.round(g.bleed_off_px[1]);
    const st = head.w * px.bpp, set = {};
    let n = 0;
    for (let y = y0; y < Math.min(head.h, y0 + p14); y++) {
      for (let x = x0; x < Math.min(head.w, x0 + p14); x++) {
        const i = y * st + x * px.bpp;
        set[(px.data[i] << 16) | (px.data[i + 1] << 8) | px.data[i + 2]] = 1;
        n++;
      }
    }
    const c = Object.keys(set).length;
    /* LA DEFINITION FAIT PARTIE DU CHIFFRE. Un comptage de couleurs uniques
       dans une surface PHYSIQUE fixe croit avec la definition : le meme coin
       de 14 x 14 mm du meme dessin ne donne pas le meme compte a 300 et a
       600 DPI — mesure faite sur les deux fichiers livres, decodes a la main.
       Publier ce compte sans dire a quelle definition il a ete pris serait un
       chiffre vrai qui ment, et deux relectures du meme cadre sembleraient se
       contredire. La definition part donc avec la mesure. */
    return { coin_mm: 14, coin_px: p14, couleurs: c, par_mm2: r1(c / 196),
      pixels: n, dpi: g.dpi };
  }
  function measureAlpha(px, head) {
    if (px.bpp !== 4) return { canaux: 3, note: "RGB : aucun canal alpha dans le fichier" };
    let mn = 255, mx = 0;
    for (let i = 3; i < px.data.length; i += 4) { const a = px.data[i]; if (a < mn) mn = a; if (a > mx) mx = a; }
    return { canaux: 4, alpha_min: mn, alpha_max: mx, constant: mn === mx,
      pixels: px.data.length / 4 };
  }

  /* ── LE CONTROLE : on rend le fichier, on le relit, on compare ────────── */
  let PROOF = null;
  async function runProof(face, auto) {
    if (!UI.proofTab) return;
    if (PA.running) return;
    PA.running = true;
    const sig = fileSig();
    try {
      if (!auto) M.busy(true, "rendu puis relecture des octets du " + (face === "back" ? "verso" : "recto") + "…");
      drawProof();
      const g = CF.geom(), f0 = f();
      const r = await stamped(face);
      const buf = new Uint8Array(await r.blob.arrayBuffer());
      const head = pngHeader(buf);
      const px = await pngPixels(buf, head);
      /* LA MEME MESURE SUR LE CADRE SEUL. Sur un format etroit, la marche la
         plus dure du bord droit n'etait pas la mienne : mesure sur les octets,
         format `micro`, ligne y=163 — une suite de traits creme (246,231,194)
         qui court de x=396 a x=435 alors que la coupe tombe a 412,5. C'est du
         TEXTE, couche 60, qui deborde de la carte. Le fichier livre porte bien
         une arete sous la lame et la ligne doit rester rouge — mais dire
         « ecart 8,96 » sans dire d'ou il vient laisse croire que le cadre
         encre la coupe. On rend donc le cadre SEUL, aux memes pixels, on lui
         applique la meme mesure, et on publie les deux : ce qui est a moi et
         ce qui vient d'au-dessus. Aucune des deux ne peut me blanchir : si
         c'est le cadre qui deborde, c'est ce chiffre-la qui monte. */
      let coupeCadre = null;
      try {
        const im = paintFamAt(g, {});
        coupeCadre = measureCut({ data: im.data, bpp: 4 },
          { w: g.canvas_px[0], h: g.canvas_px[1] }, g);
      } catch (e) { coupeCadre = null; }
      PROOF = {
        face: face, octets: buf.length, estampille: r.stamped, head: head,
        sig: sig, at: Date.now(), auto: !!auto,
        filet: measureLine(px, head, g, f0),
        fond: measureBleed(px, head, g),
        coupe: measureCut(px, head, g),
        coupe_cadre: coupeCadre,
        matiere: measureMatter(px, head, g),
        alpha: measureAlpha(px, head),
        geom: { canvas: g.canvas_px.slice(), dpi: g.dpi, ppm: ppm(g.dpi),
          safe: g.safe_px.slice(), safe_off: g.safe_off_px.slice(),
          trim: g.trim_px.slice(), bleed_off: g.bleed_off_px.slice() },
      };
      drawProof();
    } catch (e) {
      PROOF = { erreur: String((e && e.message) || e), face: face, sig: sig, at: Date.now() };
      drawProof();
    } finally {
      PA.running = false;
      if (!auto) M.busy(false);
      /* l'etat a pu bouger PENDANT le rendu : on ne laisse pas passer un vert
         qui porterait sur des octets deja perimes. */
      if (fileSig() !== sig) scheduleProof(900);
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     LA PREUVE TOURNE TOUTE SEULE, ET ELLE EST DATEE
     ───────────────────────────────────────────────────────────────────────
     Reproche du tour precedent, mot pour mot : « un produit qui a construit
     son propre verificateur et qui livre l'ecran avec le verificateur eteint
     fait exactement la moitie du chemin : il faut que la verification soit
     passee, datee et affichee en vert par defaut, sinon elle ne vaut pas
     mieux qu'une promesse. » Il avait raison, et le badge disait « non
     verifie » sur un fichier parfaitement conforme.

     Ce n'est plus un bouton : c'est le FICHIER qui declenche. Une empreinte
     du document + de la geometrie + de la carte courante est prise a chaque
     verification ; des que cette empreinte bouge, le badge passe en
     « perimee » et la relecture repart d'elle-meme. Le bouton reste, pour
     relancer a la main et pour choisir la face.
     ═══════════════════════════════════════════════════════════════════════ */
  /* `hold` : pendant que les DEUX definitions ou l'epreuve de controle
     tournent, la barre de format bouge et le fichier change deux fois. Une
     relecture automatique lancee la-dedans mesurerait un etat de passage et
     afficherait un vert qui ne parle de rien. On la retient, et elle repart
     apres — la definition d'origine reposee, l'empreinte a nouveau stable. */
  const PA = { timer: null, running: false, hold: 0, perime: false,
    busyTwin: false, busyCtrl: false };
  function hash32(s) {
    let a = 2166136261;
    for (let i = 0; i < s.length; i++) { a ^= s.charCodeAt(i); a = (a * 16777619) >>> 0; }
    return ("0000000" + a.toString(16)).slice(-8);
  }
  /* CE QUI FAIT LE FICHIER, ET RIEN D'AUTRE : la geometrie, la carte courante,
     et TOUT le document — donc aussi les pieces 01, 03, 04, 06, dont les
     couches sont dans la meme toile. `CF.side()` est exclu a dessein : c'est
     la face du DERNIER rendu, partagee, et la loupe la fait changer sans que
     le fichier bouge. */
  function fileSig() {
    try {
      const g = CF.geom();
      return hash32(JSON.stringify([g.fmt, g.dpi, g.bleed_mm, g.safe_mm, g.corner_mm,
        CF.current(), CF.doc()]));
    } catch (e) { return "?" + Date.now(); }
  }
  function panelOn() {
    const p = document.querySelector("#cf-panel-frame");
    return !!(p && p.classList.contains("on") && ROOT && ROOT.clientWidth > 0);
  }
  function scheduleProof(ms) {
    if (!UI.proofTab) return;
    clearTimeout(PA.timer);
    PA.timer = setTimeout(autoProof, ms == null ? 1500 : ms);
    /* LE BADGE REPEINT DANS LES DEUX SENS. Il ne repeignait qu'en devenant
       perime : revenu a l'etat verifie — ce qui arrive a chaque aller-retour
       de definition, donc apres CHAQUE passage sur les deux definitions — il
       restait bloque sur « perimee » alors que la relecture affichee portait
       exactement sur les octets courants. Un badge qui ment par pessimisme
       reste un badge qui ment. */
    /* LES TROIS BADGES REPEIGNENT DANS LES DEUX SENS, pas seulement celui de
       la relecture. MESURE qui l'a impose : `doc.face.eff_dpi` (piece 01) suit
       la definition et n'est reecrit qu'une a deux secondes APRES le retour a
       300 DPI. Les deux definitions capturaient donc leur empreinte avant, la
       dessinaient pendant, et restaient bloquees sur « perimee » alors que le
       document etait redevenu identique (verifie : apres l'aller-retour, la
       seule cle qui avait bouge — eff_dpi — retrouve sa valeur). Un badge qui
       ment par pessimisme reste un badge qui ment. */
    const p = PROOF && !PROOF.erreur ? (PROOF.sig !== fileSig()) : PA.perime;
    if (p !== PA.perime) drawProof();
    if (TWIN && !TWIN.erreur && TWIN.sig
      && (TWIN.sig !== fileSig()) !== !!TWIN.perime) { TWIN.perime = !TWIN.perime; drawTwin(); }
    if (CTRL && !CTRL.erreur && CTRL.sig
      && (CTRL.sig !== fileSig()) !== !!CTRL.perime) { CTRL.perime = !CTRL.perime; drawControl(); }
  }
  /* attend que l'empreinte du fichier soit STABLE avant de la retenir : une
     couche voisine peut ecrire une valeur derivee (eff_dpi) une seconde apres
     le retour de la definition. On retient l'etat REPOSE, celui que la mesure
     laisse derriere elle — et on dit s'il a bouge en route. */
  async function sigStable(calme, limite) {
    const t0 = now();
    let s = fileSig(), depuis = now();
    while (now() - t0 < (limite == null ? 6000 : limite)) {
      await new Promise((r) => setTimeout(r, 200));
      const v = fileSig();
      if (v !== s) { s = v; depuis = now(); continue; }
      if (now() - depuis >= (calme == null ? 1000 : calme)) return s;
    }
    return fileSig();
  }
  function autoProof() {
    /* panneau ferme : on ne rend rien pour personne. La ResizeObserver
       rappelle `sync()` — donc `scheduleProof` — des qu'il s'ouvre. */
    if (!UI.proofTab || !panelOn()) return;
    if (PA.running || PA.hold > 0) { scheduleProof(900); return; }
    if (PROOF && !PROOF.erreur && PROOF.sig === fileSig()) { scheduleAuto(1200); return; }
    runProof(PROOF && PROOF.face === "back" ? "back" : "front", true);
    scheduleAuto(2500);
  }

  /* ═══════════════════════════════════════════════════════════════════════
     LES DEUX AUTRES INSTRUMENTS PARTENT SEULS, EUX AUSSI
     ───────────────────────────────────────────────────────────────────────
     Reproche, mot pour mot : « B expose tout un appareil de preuve et ne l'a
     pas actionne : "Rendre et relire les deux fichiers" affiche NON LANCEE,
     "Construire l'epreuve de controle" affiche NON PRODUITE. Deux criteres
     [DUR] restent inverifiables, soit un quart du bareme mort — faute d'un
     clic. » La relecture d'octets partait deja seule ; ces deux-la non, et
     c'est exactement la moitie du chemin.

     Ils partent maintenant, dans cet ordre et sous conditions strictes :
       · le panneau doit etre OUVERT (dans l'app, l'onglet par defaut est
         « Face » : rien ne se declenche tant qu'on n'est pas venu ici) ;
       · la relecture d'octets doit etre passee et verte — inutile de rendre
         quatre fichiers si le premier est deja faux ;
       · un seul a la fois, jamais pendant un rendu ;
       · et pas plus d'une fois par AUTO_COOL : les deux definitions rendent
         une toile de 1630 x 2220 px, ce n'est pas une mesure qu'on refait a
         chaque pixel de curseur. Entre deux passages, le badge dit
         « perimee » avec son heure — jamais un vert sur des octets morts.
     Le declenchement automatique ne pose PAS le voile d'attente global
     (`M.busy`) : personne n'a rien demande, l'ecran doit rester utilisable.
     ═══════════════════════════════════════════════════════════════════════ */
  const AUTO = { timer: null, twin: 0, ctrl: 0 };
  const AUTO_COOL = 30000;
  function scheduleAuto(ms) {
    clearTimeout(AUTO.timer);
    AUTO.timer = setTimeout(autoInstruments, ms == null ? 2500 : ms);
  }
  function autoInstruments() {
    if (!UI.twinTab || !panelOn()) return;
    if (PA.running || PA.hold > 0 || PA.busyTwin || PA.busyCtrl) { scheduleAuto(1500); return; }
    /* la relecture d'octets fait foi : tant qu'elle n'est pas verte sur les
       octets courants, les deux gros instruments attendent. */
    if (!PROOF || PROOF.erreur || PROOF.sig !== fileSig()) { scheduleAuto(2000); return; }
    const t = Date.now(), sig = fileSig();
    if ((!TWIN || TWIN.erreur || TWIN.sig !== sig) && t - AUTO.twin > AUTO_COOL) {
      AUTO.twin = t;
      runTwin(true);
      scheduleAuto(4000);
      return;
    }
    if ((!CTRL || CTRL.erreur || CTRL.sig !== sig) && t - AUTO.ctrl > AUTO_COOL) {
      AUTO.ctrl = t;
      runControl(true);
      scheduleAuto(4000);
    }
  }
  function hms(t) {
    const d = new Date(t), p = (n) => (n < 10 ? "0" : "") + n;
    return p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds());
  }
  /* le VERDICT en premiere colonne : dans un panneau etroit, la table defile
     horizontalement, et une croix rouge hors champ ne sert a personne. */
  function proofRow(quoi, annonce, mesure, ok, note) {
    return '<div class="cff-proofr ' + (ok ? "ok" : "ko") + '"><span class="v">'
      + (ok ? "✓" : "✗") + "</span><span>" + esc(quoi)
      + "</span><span>" + esc(annonce) + "</span><span>" + esc(mesure)
      + (note ? " — " + esc(note) : "") + "</span></div>";
  }
  function drawProof() {
    if (!UI.proofTab) return;
    if (!PROOF) {
      UI.proofTab.innerHTML = "";
      UI.pbadge.className = "cff-pbadge";
      UI.pbadge.textContent = PA.running ? "relecture des octets…" : "vérification automatique…";
      UI.proofRead.innerHTML = "Elle part <b>toute seule</b> à l'ouverture et repart à chaque fois "
        + "que le fichier change — le fichier est rendu par le <b>vrai chemin d'export</b> (le même "
        + "que le bouton de téléchargement), puis ses octets sont relus ici : chunks, "
        + "<b>zlib décompressé</b> et lignes <b>défiltrées</b> à la main (les 5 filtres de la norme). "
        + "Chaque ligne ci-dessous confronte un chiffre de cet écran à ce que les échantillons disent.";
      return;
    }
    if (PROOF.erreur) {
      UI.pbadge.className = "cff-pbadge ko";
      UI.pbadge.textContent = "mesure impossible";
      UI.proofTab.innerHTML = "";
      UI.proofRead.textContent = PROOF.erreur;
      return;
    }
    const P = PROOF, h0 = P.head, G = P.geom;
    const rows = [];
    let bad = 0;
    const add = (q, a, m2, ok, note) => { if (!ok) bad++; rows.push(proofRow(q, a, m2, ok, note)); };

    add("Toile (IHDR)", G.canvas[0] + " x " + G.canvas[1] + " px",
      h0.w + " x " + h0.h + " px", h0.w === G.canvas[0] && h0.h === G.canvas[1],
      "lu dans IHDR");
    const dpiR = h0.ppm ? dpiOf(h0.ppm) : null;
    add("Définition (pHYs)", ppm(G.dpi) + " px/m = " + dpiOf(ppm(G.dpi)) + " DPI",
      h0.ppm ? (h0.ppm + " px/m, unité " + h0.ppm_unit + " = " + dpiR + " DPI") : "aucun chunk pHYs",
      !!h0.ppm && h0.ppm === ppm(G.dpi) && h0.ppm_unit === 1,
      h0.ppm ? "unité 1 = mètre" : "le fichier ne porte pas sa définition");
    add("Canaux (IHDR)", "RGB 8 bits — 3 canaux",
      "profondeur " + h0.depth + ", type couleur " + h0.ctype
      + (P.alpha.canaux === 4 ? (" · alpha " + P.alpha.alpha_min + "→" + P.alpha.alpha_max
        + (P.alpha.constant ? " (constant : 0 information sur " + P.alpha.pixels + " pixels)" : "")) : ""),
      h0.depth === 8 && (P.alpha.canaux === 3 || !P.alpha.constant),
      P.alpha.canaux === 3 ? "aucun octet perdu"
        : (P.alpha.constant ? "un quart du fichier ne transporte rien" : "alpha utile, conservé"));
    const keys = h0.texts.map((t) => t.k);
    const manque = STAMP_KEYS.filter((k) => keys.indexOf(k) < 0);
    add("tEXt", STAMP_KEYS.length + " clés nommées", keys.length + " : " + keys.join(", "),
      manque.length === 0 && keys.length === STAMP_KEYS.length,
      manque.length ? ("manque " + manque.join(", ")) : "clés relues dans le fichier");
    const alphaT = (h0.texts.filter((t) => t.k === "Alpha")[0] || {}).v || "";
    const trimT = (h0.texts.filter((t) => t.k === "TrimBox")[0] || {}).v || "";
    const safeT = (h0.texts.filter((t) => t.k === "SafeBox")[0] || {}).v || "";
    add("TrimBox (tEXt)", r2(G.bleed_off[0]) + "," + r2(G.bleed_off[1]) + " " + G.trim[0] + "x" + G.trim[1] + " px",
      trimT, trimT.indexOf(G.trim[0] + "x" + G.trim[1]) >= 0, "chaîne du fichier");
    add("SafeBox (tEXt)", r2(G.safe_off[0]) + "," + r2(G.safe_off[1]) + " " + G.safe[0] + "x" + G.safe[1] + " px",
      safeT, safeT.indexOf(G.safe[0] + "x" + G.safe[1]) >= 0, "chaîne du fichier");
    if (P.filet && P.filet.faute) {
      /* On ne publie pas un chiffre qu'on ne sait pas etablir : on publie la
         raison. Une ligne « non mesurable » vaut mieux qu'une ligne fausse, et
         elle ne compte pas comme un ecart — rien n'a ete affirme. */
      rows.push(proofRow("Filet extérieur", P.filet.largeur_annoncee + " px sur l'axe "
        + P.filet.axe_annonce + " px", "non isolable sur la ligne y=" + P.filet.y,
        true, P.filet.faute));
    } else if (P.filet) {
      const e1 = Math.abs(P.filet.axe - P.filet.axe_annonce);
      const e2 = Math.abs(P.filet.largeur - P.filet.largeur_annoncee);
      add("Filet extérieur — axe", P.filet.axe_annonce + " px du bord de toile",
        P.filet.axe + " px (milieu des deux arêtes, ligne y=" + P.filet.y + ")",
        e1 <= 1.0, "écart " + r2(e1) + " px = " + r2(e1 / CF.geom().dpi * 25.4) + " mm");
      add("Filet extérieur — largeur", P.filet.largeur_annoncee + " px",
        P.filet.largeur + " px entre les deux arêtes", e2 <= 1.6, "écart " + r2(e2) + " px");
      add("Filet extérieur — bord", P.filet.bord_ext_annonce + " px (axe − épaisseur/2)",
        P.filet.bord_ext_mesure + " px, arête extérieure (saut " + P.filet.saut_ext + "/255)",
        Math.abs(P.filet.bord_ext_mesure - P.filet.bord_ext_annonce) <= 1.6,
        "la valeur du curseur porte l'AXE ; arête intérieure à " + P.filet.bord_int_mesure
        + " px (saut " + P.filet.saut_int + "/255)");
    } else {
      rows.push(proofRow("Filet extérieur", "épaisseur " + r2(f().line_mm) + " mm",
        "trop fin pour une mesure à mi-hauteur (< 1,2 px)", true, "non mesurable, non affirmé"));
    }
    const B = P.fond;
    const mini = Math.min(B.haut.ecart_type, B.bas.ecart_type, B.gauche.ecart_type, B.droite.ecart_type);
    const blancs = B.haut.px_blancs + B.bas.px_blancs + B.gauche.px_blancs + B.droite.px_blancs;
    add("Fond perdu — matière", B.largeur_px[0] + " x " + B.largeur_px[1] + " px encrés sur les 4 bords",
      "écart-type de luminance " + B.haut.ecart_type + " / " + B.bas.ecart_type + " / "
      + B.gauche.ecart_type + " / " + B.droite.ecart_type + " (haut/bas/gauche/droite)",
      mini > 0.5, mini > 0.5 ? "dégradé continu, pas un aplat" : "un des bords est un aplat");
    add("Fond perdu — blanc pur", "0 pixel blanc dans les bandes",
      blancs + " pixel(s) blanc(s) sur " + (B.haut.n + B.bas.n + B.gauche.n + B.droite.n),
      blancs === 0, "l'encre va jusqu'au bord de toile");
    /* LA LIGNE QUI MANQUAIT. Un fond perdu aux bonnes dimensions ne prouve rien
       si le dessin place son arete la plus dure sur la lame : la teinte du bord
       change alors d'une pose a l'autre. Le seuil est la tolerance elle-meme —
       une derive de 0,5 mm ne doit pas se voir, et « ne pas se voir » vaut 8
       niveaux sur 255, soit 3 % de dynamique. */
    if (P.coupe) {
      const C = P.coupe, K = P.coupe_cadre;
      const cotes = (X) => X.gauche.moyen + " / " + X.droite.moyen + " / " + X.haut.moyen
        + " / " + X.bas.moyen;
      add("Fenêtre de massicot ± " + r1(C.tol_mm) + " mm",
        "fichier LIVRÉ : ≤ " + SEUIL_COUPE + "/255 d'écart de teinte, 4 côtés",
        "moyennes " + cotes(C) + " (g/d/h/b), pire ligne " + C.pire_ligne,
        C.pire_moyen <= SEUIL_COUPE,
        "lu à ± " + C.tol_px + " px du trait de coupe sur "
        + (C.gauche.lignes + C.droite.lignes + C.haut.lignes + C.bas.lignes) + " lignes"
        + (C.pire_moyen > SEUIL_COUPE && K && K.pire_moyen <= SEUIL_COUPE
          ? " — la marche ne vient PAS du cadre : voir la ligne suivante" : ""));
      if (K) {
        add("… la même, sur le CADRE SEUL",
          "≤ " + SEUIL_COUPE + "/255 — l'encre du cadre, sans les autres couches",
          "moyennes " + cotes(K) + ", pire ligne " + K.pire_ligne,
          K.pire_moyen <= SEUIL_COUPE,
          K.pire_moyen <= SEUIL_COUPE && C.pire_moyen > SEUIL_COUPE
            ? ("le cadre est à " + K.pire_moyen + " et le fichier composé à " + C.pire_moyen
              + " : l'écart est apporté par une couche posée AU-DESSUS (texte, illustration) "
              + "qui déborde de la coupe — le fichier reste fautif, la cause n'est pas ici")
            : "cadre rendu seul par ses painters, à la toile du fichier");
      }
    }
    /* PLUS DE POINT DE COMPARAISON EXTERIEUR SUR CETTE LIGNE.
       Elle publiait « X % » d'un chiffre releve une fois sur un cadre PEINT,
       a 300 DPI. Deux defauts, et le second suffit : (a) ce nombre-la, celui
       qui regarde l'ecran ne peut le refaire sur aucun fichier qu'il possede
       — on affiche donc une valeur qu'on ne peut pas lui prouver ; (b) un
       comptage de couleurs uniques dans une surface PHYSIQUE fixe croit avec
       la definition, si bien que la comparaison etait fausse des qu'on
       quittait 300 DPI. Ce qui reste est ce qui se relit sur les octets du
       fichier livre : le nombre de couleurs, la surface ou elles ont ete
       comptees, la definition. Un aplat n'en donnerait qu'une. */
    add("Matière du cadre",
      "un aplat ne donnerait qu'une seule couleur",
      P.matiere.couleurs + " couleurs uniques dans un coin de 14 x 14 mm réels ("
      + P.matiere.coin_px + " px) à " + P.matiere.dpi + " DPI = "
      + P.matiere.par_mm2 + " / mm²", P.matiere.couleurs > 1,
      "compté sur les échantillons défiltrés ; ce comptage porte sur une surface "
      + "physique fixe, il monte donc avec la définition");
    if (alphaT) {
      rows.push(proofRow("Quatrième canal", "retiré s'il est constant", alphaT, true,
        "écrit dans le fichier"));
    }
    UI.proofTab.innerHTML =
      '<div class="cff-proofhd"><span>?</span><span>ce que l\'écran annonce</span>'
      + "<span>valeur annoncée</span><span>ce que les octets disent</span></div>" + rows.join("");
    /* PERIMEE : l'etat a change depuis la relecture. On ne laisse pas un vert
       parler d'octets qui ne sont plus ceux du fichier courant — c'est
       exactement le badge menteur qu'on reproche aux autres. */
    const perime = PROOF.sig !== fileSig();
    PA.perime = perime;
    UI.pbadge.className = "cff-pbadge " + (bad ? "ko" : (perime ? "" : "ok"));
    UI.pbadge.textContent = bad
      ? (bad + " écart(s) sur " + rows.length + " · " + hms(P.at))
      : (perime ? "périmée depuis " + hms(P.at) + " — relecture…"
        : "✓ " + rows.length + " lignes vérifiées sur les octets · " + hms(P.at));
    UI.pbadge.title = "Empreinte vérifiée : " + PROOF.sig + " (géométrie + document + carte courante). "
      + "Relecture " + (PROOF.auto ? "automatique" : "demandée à la main") + " à " + hms(P.at)
      + (perime ? " — l'empreinte vaut maintenant " + fileSig() + ", la relecture repart." : "");
    /* la ligne du filet cite la mesure de coupe : elle doit la voir arriver.
       `sync` est coalescee par requestAnimationFrame et ne rappelle jamais
       `drawProof` — pas de boucle possible. */
    sync();
    UI.proofRead.innerHTML = "<b>" + (P.face === "back" ? "Verso" : "Recto") + "</b> — fichier de <b>"
      + P.octets.toLocaleString("fr-FR") + " octets</b>"
      + (P.estampille ? "" : " (backend absent : SANS pHYs)")
      + ", " + h0.w + " x " + h0.h + " px, " + (P.alpha.canaux === 3 ? "RGB" : "RGBA") + " 8 bits, "
      + h0.chunks.length + " chunks. Zlib décompressé et lignes défiltrées ici même — "
      + "aucune API d'image n'a été employée pour relire ce fichier. "
      + "<b>Relecture " + (PROOF.auto ? "automatique" : "manuelle") + " de " + hms(P.at) + "</b>, "
      + "empreinte " + PROOF.sig + " — elle repart seule dès que le fichier change.";
  }

  /* ═══════════════════════════════════════════════════════════════════════
     LES DEUX DEFINITIONS — ET LA PREUVE, SUR LES OCTETS, QUE 600 N'EST PAS
     UN AGRANDISSEMENT DE 300
     ───────────────────────────────────────────────────────────────────────
     Reproche du tour precedent : « Aucun fichier a 600 DPI ce tour-ci. Un
     unique PNG a 300 DPI ne peut pas demontrer l'independance de resolution ;
     j'ai du l'etablir INDIRECTEMENT, par l'absence de bitmap de cadre dans le
     DOM et par la mesure de pique. La preuve directe tenait en un second
     export. » Elle est ici, et elle est directe.

     Le bouton conduit la BARRE DE FORMAT du CORE — le meme bouton 600 qu'un
     utilisateur clique — puis rend, estampille et RELIT les deux fichiers.
     Il repose ensuite la definition d'origine. Les deux blobs sont gardes :
     ils se telechargent, ce sont eux qui ont ete mesures.

     DEUX MESURES, PARCE QU'IL Y A DEUX FAÇONS D'AGRANDIR — ET ELLES ONT ETE
     VALIDEES SUR DE VRAIS OCTETS, PAS SUPPOSEES.
       · au plus proche voisin, un x2 DUPLIQUE exactement une ligne sur deux
         et une colonne sur deux ;
       · au filtre lineaire, rien n'est duplique, mais chaque ligne impaire
         devient la MOYENNE EXACTE de ses deux voisines.
     Les deux tests ont ete passes sur le fichier livre a 300, sur le fichier
     livre a 600, puis sur ces memes 300 octets agrandis x2 dans les deux
     modes (toile 815x1110 -> 1630x2220) :

       fichier                  lignes dupliquees   lignes = moyenne des voisines
       300 livre                      0,0 %                    0,0 %
       600 LIVRE                      0,0 %                    0,0 %
       300 agrandi au plus proche    50,0 %                    0,0 %
       300 agrandi au lineaire        0,0 %                  100,0 %

     Le fichier 600 ne tombe dans aucun des deux pieges. Une troisieme ligne
     donne l'acuite imprimee (la meme arete, en millimetres, aux deux
     definitions) — c'est une mesure de FINESSE, pas une preuve de retrace,
     et elle le dit.

     CE QUI A ETE JETE, ET POURQUOI. Une version de ce panneau annonçait que
     la montee 10-90 % « plus fine en millimetres » prouvait l'absence
     d'agrandissement. C'est FAUX, et la mesure ci-dessus le montre : un
     agrandissement au plus proche voisin conserve la marche intacte et
     donnerait meme une montee PLUS fine en millimetres qu'un vrai retrace
     anti-aliase. Un argument qui se retourne n'est pas un argument.
     ═══════════════════════════════════════════════════════════════════════ */
  let TWIN = null;
  function dpiButton(v) { return document.querySelector('#dpiSeg button[data-v="' + v + '"]'); }
  async function setDpiByBar(v) {
    if (CF.geom().dpi === v) return true;
    const b = dpiButton(v);
    if (!b) throw new Error("la barre de format du CORE n'offre pas " + v + " DPI");
    b.click();
    for (let i = 0; i < 80; i++) {
      if (CF.geom().dpi === v) return true;
      await new Promise((r) => setTimeout(r, 50));
    }
    throw new Error("la définition n'est pas passée à " + v + " DPI");
  }
  /* LES DEUX SIGNATURES D'AGRANDISSEMENT, comptees sur les echantillons
     DEFILTRES — pas sur une miniature, pas sur un canvas.
       `lignes`  : identiques a leur voisine du dessus (plus proche voisin)
       `moyennes`: lignes impaires qui sont la moyenne exacte, a 1 niveau
                   pres, de leurs deux voisines (interpolation lineaire) */
  function dupRatio(px, head) {
    const st = head.w * px.bpp, d = px.data, bp = px.bpp;
    let li = 0, co = 0, mo = 0, imp = 0;
    for (let y = 1; y < head.h; y++) {
      const a = (y - 1) * st, b = y * st;
      let same = true;
      for (let x = 0; x < st; x++) { if (d[a + x] !== d[b + x]) { same = false; break; } }
      if (same) li++;
    }
    for (let x = 1; x < head.w; x++) {
      let same = true;
      for (let y = 0; y < head.h && same; y++) {
        const a = y * st + (x - 1) * bp, b = y * st + x * bp;
        for (let k = 0; k < bp; k++) if (d[a + k] !== d[b + k]) { same = false; break; }
      }
      if (same) co++;
    }
    for (let y = 1; y < head.h - 1; y += 2) {
      imp++;
      const a = (y - 1) * st, b = y * st, c = (y + 1) * st;
      let moy = true;
      for (let x = 0; x < st; x++) {
        if (Math.abs(d[b + x] - (d[a + x] + d[c + x]) / 2) > 1) { moy = false; break; }
      }
      if (moy) mo++;
    }
    return { lignes: li, colonnes: co, sur_l: head.h - 1, sur_c: head.w - 1,
      moyennes: mo, impaires: imp,
      pct_l: r1(100 * li / Math.max(1, head.h - 1)),
      pct_c: r1(100 * co / Math.max(1, head.w - 1)),
      pct_m: r1(100 * mo / Math.max(1, imp)) };
  }
  /* MONTEE 10-90 % D'UNE ARETE, ET POURQUOI ELLE SE LIT EN MILLIMETRES.
     ─────────────────────────────────────────────────────────────────────
     C'est la mesure d'acuite du critique, reprise telle quelle : « montee
     10-90 % des aretes fortes, ramenee au millimetre imprime ». Elle tranche
     seule la question de l'agrandissement, parce qu'AUCUN agrandissement ne
     peut la reduire :
       · un x2 au plus proche voisin transforme une montee de 2 px en 4 px —
         donc le MEME millimetre ;
       · un x2 filtre l'etale encore plus — donc PLUS de millimetres ;
       · un vrai retrace la laisse a 1 ou 2 echantillons, qui valent deux fois
         moins de millimetres quand l'echantillon est deux fois plus petit.
     Le nombre affiche est donc la montee EN MILLIMETRES, et la ligne passe si
     elle DIMINUE a 600.

     METHODE, ecrite pour qu'on puisse la refaire : plateaux releves sur trois
     echantillons de part et d'autre de la marche (serres, sinon on happe le
     degrade de l'anneau qui court sur un demi-millimetre et l'on mesure la
     matiere au lieu de l'arete), bande a 10 % et 90 % de la marche, puis on
     compte les echantillons CONTIGUS a la marche qui tombent dans la bande —
     contigus, sans quoi un echantillon de l'autre bord de l'anneau, qui passe
     par hasard dans la bande, compterait pour de la mollesse. */
  function riseOf(px, head, xhint) {
    const y = Math.round(head.h / 2), st = head.w * px.bpp;
    const L = (x) => lumAt(px, y * st + x * px.bpp);
    let bx = 1, bv = 0;
    /* LE MEME FRONT DES DEUX COTES. Sans indication, on prendrait « le plus
       fort saut de la ligne » — et rien ne garantit que ce soit le meme motif
       a 300 et a 600 : on comparerait deux aretes differentes, ce qui ne
       prouve rien. Quand la mesure du filet a trouve son arete exterieure, on
       mesure LA, au meme endroit physique aux deux definitions. */
    if (xhint != null && xhint >= 1 && xhint < head.w - 2) {
      bx = xhint; bv = Math.abs(L(bx + 1) - L(bx));
      for (let k = -2; k <= 2; k++) {
        const x = xhint + k;
        if (x < 1 || x >= head.w - 2) continue;
        const v = Math.abs(L(x + 1) - L(x));
        if (v > bv) { bv = v; bx = x; }
      }
    } else {
      for (let x = 1; x < head.w - 2; x++) {
        const v = Math.abs(L(x + 1) - L(x));
        if (v > bv) { bv = v; bx = x; }
      }
    }
    if (bv < 8) return null;
    const up = L(bx + 1) > L(bx);
    let lo = L(bx), hi = L(bx + 1);
    for (let k = 1; k <= 2 && bx - k >= 0; k++) { const v = L(bx - k); if (up ? v < lo : v > lo) lo = v; }
    for (let k = 1; k <= 2 && bx + 1 + k < head.w; k++) { const v = L(bx + 1 + k); if (up ? v > hi : v < hi) hi = v; }
    const a = lo + (hi - lo) * 0.1, b = lo + (hi - lo) * 0.9;
    const dedans = (v) => (up ? (v > a && v < b) : (v < a && v > b));
    let n = 1;                                   /* la marche elle-meme */
    for (let x = bx; x >= 0 && dedans(L(x)); x--) n++;
    for (let x = bx + 1; x < head.w && dedans(L(x)); x++) n++;
    return { largeur_px: n, marche: r1(Math.abs(hi - lo)), x: bx, y: y,
      vise: xhint == null ? null : xhint };
  }
  async function grabAt(face) {
    const g = CF.geom(), f0 = f();
    const r = await stamped(face);
    const buf = new Uint8Array(await r.blob.arrayBuffer());
    const head = pngHeader(buf);
    const px = await pngPixels(buf, head);
    const ln = measureLine(px, head, g, f0);
    return {
      dpi: g.dpi, fmt: g.fmt, octets: buf.length, blob: r.blob, estampille: r.stamped,
      attendu: CF.geomOf(g.fmt, g.dpi, g.bleed_mm, g.safe_mm, g.corner_mm).canvas_px.slice(),
      w: head.w, h: head.h, ppm: head.ppm, ppm_unit: head.ppm_unit,
      filet: ln, filet_mm: (ln && !ln.faute) ? r2(ln.largeur / g.dpi * 25.4) : null,
      /* la mesure du filet est QUANTIFIEE a l'echantillon entier : un pixel
         vaut 0,0847 mm a 300 DPI et 0,0423 mm a 600. On publie ce pas, sans
         quoi « 0,93 mm pour 0,9 annonces » passerait pour un defaut de trace
         alors que c'est la resolution de la mesure elle-meme. */
      pas_mm: r2(25.4 / g.dpi),
      annonce_mm: r2(f0.line_mm), dup: dupRatio(px, head),
      rise: riseOf(px, head, (ln && !ln.faute) ? Math.round(ln.bord_ext_mesure) - 1 : null),
    };
  }
  async function runTwin(auto) {
    if (!UI.twinTab) return;
    if (PA.busyTwin) return;
    PA.busyTwin = true;
    const face = LO.side === "back" ? "back" : "front";
    const dpi0 = CF.geom().dpi;
    const d1 = (dpi0 === 600) ? 300 : dpi0;
    const sig = fileSig();
    TWIN = { encours: true, auto: !!auto };
    drawTwin();
    PA.hold++;
    if (!auto) M.busy(true, "rendu et relecture des octets aux deux définitions…");
    let rendu = null;
    try {
      await setDpiByBar(d1);
      const a = await grabAt(face);
      await setDpiByBar(600);
      const b = await grabAt(face);
      rendu = { a: a, b: b, dpi0: dpi0, face: face, at: Date.now(), sig: sig, auto: !!auto };
    } catch (e) {
      rendu = { erreur: String((e && e.message) || e), sig: sig, auto: !!auto };
    } finally {
      try { await setDpiByBar(dpi0); }
      catch (e) { rendu.repli = String((e && e.message) || e); }
      const fin = await sigStable();
      rendu.bouge = (fin !== sig);
      rendu.sig = fin;
      TWIN = rendu;
      PA.hold--;
      PA.busyTwin = false;
      if (!auto) M.busy(false);
      drawTwin();
      scheduleProof(600);        /* la relecture repart sur l'etat repose */
    }
  }
  function drawTwin() {
    if (!UI.twinTab) return;
    if (!TWIN) {
      UI.twinTab.innerHTML = "";
      UI.tbadge.className = "cff-pbadge";
      UI.tbadge.textContent = "départ automatique…";
      UI.twinDl.classList.add("hidden");
      return;
    }
    if (TWIN.encours) {
      UI.tbadge.className = "cff-pbadge";
      UI.tbadge.textContent = (TWIN.auto ? "rendu automatique" : "rendu") + " des deux fichiers…";
      UI.twinTab.innerHTML = "";
      return;
    }
    if (TWIN.erreur) {
      UI.tbadge.className = "cff-pbadge ko";
      UI.tbadge.textContent = "impossible";
      UI.twinTab.innerHTML = "";
      UI.twinRead.textContent = TWIN.erreur;
      return;
    }
    const A = TWIN.a, B = TWIN.b, rows = [];
    let bad = 0;
    const add = (q, a, m, ok, note) => { if (!ok) bad++; rows.push(proofRow(q, a, m, ok, note)); };
    const exact2 = (B.attendu[0] === 2 * A.attendu[0] && B.attendu[1] === 2 * A.attendu[1]);
    add("Toile à " + A.dpi + " DPI", A.attendu[0] + " x " + A.attendu[1] + " px",
      A.w + " x " + A.h + " px lus dans IHDR", A.w === A.attendu[0] && A.h === A.attendu[1],
      "taille recalculée à partir des millimètres, jamais multipliée");
    add("Toile à " + B.dpi + " DPI", B.attendu[0] + " x " + B.attendu[1] + " px",
      B.w + " x " + B.h + " px lus dans IHDR", B.w === B.attendu[0] && B.h === B.attendu[1],
      exact2 ? "ici exactement le double" : "PAS le double de " + A.attendu[0] + " x " + A.attendu[1]
        + " : la règle d'arrondi px(mm,dpi) ne double pas sur ce format");
    add("Définition portée (pHYs)", ppm(B.dpi) + " px/m = " + dpiOf(ppm(B.dpi)) + " DPI",
      B.ppm ? (B.ppm + " px/m, unité " + B.ppm_unit + " = " + dpiOf(B.ppm) + " DPI") : "aucun chunk pHYs",
      !!B.ppm && B.ppm === ppm(B.dpi) && B.ppm_unit === 1, "relu dans le fichier 600");
    if (A.filet_mm != null && B.filet_mm != null) {
      const e = Math.abs(A.filet_mm - B.filet_mm);
      add("Épaisseur du filet, en MILLIMÈTRES", A.annonce_mm + " mm des deux côtés",
        A.filet_mm + " mm à " + A.dpi + " DPI (" + A.filet.largeur + " px) · "
        + B.filet_mm + " mm à " + B.dpi + " DPI (" + B.filet.largeur + " px)",
        e <= A.pas_mm + B.pas_mm,
        "écart " + r2(e) + " mm, pour un pas de mesure de " + A.pas_mm + " et " + B.pas_mm
        + " mm (un échantillon) : la mesure est quantifiée, pas le tracé");
    } else {
      rows.push(proofRow("Épaisseur du filet", A.annonce_mm + " mm",
        "non isolable à l'une des deux définitions", true,
        "aucun chiffre publié — voir la ligne du panneau au-dessus"));
    }
    add("Lignes identiques à leur voisine", "0 % — un x2 au plus proche voisin en donne 50,0 %",
      A.dup.pct_l + " % à " + A.dpi + " DPI (" + A.dup.lignes + "/" + A.dup.sur_l + ") · "
      + B.dup.pct_l + " % à " + B.dpi + " DPI (" + B.dup.lignes + "/" + B.dup.sur_l + ")",
      B.dup.pct_l < 25, "un x2 au plus proche voisin recopie exactement une ligne sur deux");
    add("Colonnes identiques à leur voisine", "0 % — même piège dans l'autre sens",
      A.dup.pct_c + " % · " + B.dup.pct_c + " %", B.dup.pct_c < 25,
      "un x2 au plus proche voisin duplique aussi une colonne sur deux");
    add("Lignes qui sont la MOYENNE de leurs voisines", "0 % — un x2 linéaire en donne 100 %",
      A.dup.pct_m + " % à " + A.dpi + " DPI (" + A.dup.moyennes + "/" + A.dup.impaires + ") · "
      + B.dup.pct_m + " % à " + B.dpi + " DPI (" + B.dup.moyennes + "/" + B.dup.impaires + ")",
      B.dup.pct_m < 5,
      "le second piège : un agrandissement filtré ne duplique rien, mais chaque ligne impaire y "
      + "est la moyenne exacte des deux autres. LIMITE ASSUMÉE : un dégradé parfaitement "
      + "linéaire est sa propre interpolation et ferait monter ce chiffre sans aucun "
      + "agrandissement. Il ne peut donc pas laisser passer un agrandissement, seulement "
      + "crier à tort");
    if (A.rise && B.rise) {
      const ma = r2(A.rise.largeur_px / A.dpi * 25.4), mb = r2(B.rise.largeur_px / B.dpi * 25.4);
      add("Acuité imprimée de l'arête du filet", "plus fine sur le papier à 600 DPI",
        A.rise.largeur_px + " échantillons = " + ma + " mm à " + A.dpi + " DPI · "
        + B.rise.largeur_px + " = " + mb + " mm à " + B.dpi + " DPI",
        mb < ma,
        "FINESSE, pas preuve de retracé : un x2 au plus proche voisin donnerait lui aussi "
        + "une arête fine. Ce sont les trois lignes au-dessus qui écartent l'agrandissement");
    }
    add("Poids des deux fichiers", "le 600 pèse plus : il porte 4 fois plus d'échantillons",
      A.octets.toLocaleString("fr-FR") + " octets · " + B.octets.toLocaleString("fr-FR") + " octets",
      B.octets > A.octets, "les deux sont téléchargeables ci-dessous, ce sont EUX qui ont été mesurés");
    UI.twinTab.innerHTML =
      '<div class="cff-proofhd"><span>?</span><span>ce que l\'écran annonce</span>'
      + "<span>valeur annoncée</span><span>ce que les octets disent</span></div>" + rows.join("");
    const vieux = TWIN.sig !== fileSig();
    TWIN.perime = vieux;
    UI.tbadge.className = "cff-pbadge " + (bad ? "ko" : (vieux ? "" : "ok"));
    UI.tbadge.textContent = bad ? (bad + " écart(s) sur " + rows.length + " · " + hms(TWIN.at))
      : ((vieux ? "périmée depuis " : "✓ " + rows.length + " lignes vérifiées sur les DEUX fichiers · ")
        + hms(TWIN.at));
    UI.tbadge.title = "Empreinte du document REPOSÉ, prise après le retour à " + TWIN.dpi0
      + " DPI et une seconde de calme : " + TWIN.sig
      + (TWIN.auto ? " · départ automatique" : " · lancée à la main")
      + (TWIN.bouge ? " — l'empreinte a bougé pendant la mesure (une couche voisine suit la "
        + "définition) ; les deux fichiers, eux, ont été rendus à la suite." : "")
      + (vieux ? " — le document vaut maintenant " + fileSig() + ", relance pour remesurer." : "");
    UI.twinDl.classList.remove("hidden");
    UI.twinRead.innerHTML = "Les deux fichiers ont été rendus par le <b>vrai chemin d'export</b>, "
      + "en conduisant le bouton <b>" + B.dpi + "</b> de la barre de format — celui qu'un utilisateur "
      + "clique — puis la définition d'origine (<b>" + TWIN.dpi0 + " DPI</b>) a été reposée"
      + (TWIN.repli ? " — <b>ÉCHEC du retour</b> : " + esc(TWIN.repli) : "") + ". "
      + "Leurs octets ont été décompressés et défiltrés ici même. "
      + "<b>Aucun bitmap de cadre n'intervient</b> : le cadre est retracé à la toile demandée, "
      + "c'est pour cela que la montée d'un front ne s'étale pas et qu'aucune ligne n'est dupliquée.";
  }
  async function twinDownload() {
    if (!TWIN || !TWIN.a || !TWIN.b) return;
    const nom = (x) => (TWIN.face === "back" ? "dos_" : "carte_") + f().family + "_"
      + x.w + "x" + x.h + "_" + x.dpi + "dpi.png";
    M.download(TWIN.a.blob, nom(TWIN.a));
    await new Promise((r) => setTimeout(r, 250));
    M.download(TWIN.b.blob, nom(TWIN.b));
    M.toast("les deux fichiers mesurés sont téléchargés : " + TWIN.a.dpi + " et " + TWIN.b.dpi + " DPI");
  }

  /* ═══════════════════════════════════════════════════════════════════════
     L'EPREUVE DE CONTROLE — DE VRAIS TRAITS DE COUPE, HORS DE L'ENCRE
     ───────────────────────────────────────────────────────────────────────
     Reproche du tour precedent : « Aucun trait de coupe ni repere de
     registration dans le fichier livre. » Le fichier d'impression n'en
     portera jamais, et c'est VOULU : du trait de coupe au bord de toile il
     n'y a que du fond perdu, c'est-a-dire de l'encre qui passe sous la lame ;
     un repere trace la-dedans est au mieux inutile. Un repere se pose HORS du
     fond perdu — il faut donc du papier en plus, donc un autre fichier.

     Celui-ci. Le backend pose la toile livree sur une marge de papier, y
     trace les huit traits de coupe alignes sur la rogne et quatre mires, et
     VERIFIE que pas un pixel de la carte n'a bouge. Puis on relit le fichier
     rendu ICI, on cherche ou tombent vraiment les colonnes noires, et on le
     dit : c'est la seule façon d'ecrire « alignes sur la coupe » sans
     demander qu'on nous croie.
     ═══════════════════════════════════════════════════════════════════════ */
  let CTRL = null;
  const CTRL_MARGE = 10;
  async function runControl(auto) {
    if (PA.busyCtrl) return;
    PA.busyCtrl = true;
    const face = LO.side === "back" ? "back" : "front";
    const g = CF.geom();
    const sig = fileSig();
    CTRL = { encours: true, auto: !!auto };
    drawControl();
    PA.hold++;
    if (!auto) M.busy(true, "épreuve de contrôle : traits de coupe et mires…");
    try {
      const raw = await CF.cardBlob(CF.current(), { face: face });
      const q = "control?fmt=" + encodeURIComponent(g.fmt) + "&dpi=" + g.dpi
        + "&bleed_mm=" + g.bleed_mm + "&safe_mm=" + g.safe_mm
        + "&corner_mm=" + g.corner_mm + "&face=" + face + "&margin_mm=" + CTRL_MARGE;
      const blob = await M.api.blob("POST", q, raw);
      const buf = new Uint8Array(await blob.arrayBuffer());
      const head = pngHeader(buf);
      const px = await pngPixels(buf, head);
      const marge = Math.round(CTRL_MARGE / 25.4 * g.dpi);
      /* OU SONT VRAIMENT LES TRAITS. On regarde LA BANDE QU'UN TRAIT DE COUPE
         OCCUPE — les 5 mm de papier qui touchent le bord de toile — et on
         retient les colonnes (puis les lignes) noires sur au moins 75 % de
         cette bande. Balayer la marge ENTIERE ratait les traits : ils font
         5 mm dans une marge de 10, donc exactement la moitie de la bande, et
         la mire de reperage, plus longue, etait seule detectee. On ne lit pas
         l'en-tete : on regarde les echantillons defiltres. */
      const st = head.w * px.bpp;
      const trait = Math.round(5 / 25.4 * g.dpi);
      const j0 = Math.max(0, marge - trait);
      const noir = (o) => px.data[o] < 40 && px.data[o + 1] < 40 && px.data[o + 2] < 40;
      const noires = (n, lecteur) => {
        const out = [];
        for (let i = 0; i < n; i++) {
          let k = 0;
          for (let j = j0; j < marge; j++) if (noir(lecteur(i, j))) k++;
          if (k >= (marge - j0) * 0.75) out.push(i);
        }
        return out;
      };
      const cols = noires(head.w, (x, y) => y * st + x * px.bpp);
      const lignes = noires(head.h, (y, x) => y * st + x * px.bpp);
      CTRL = {
        octets: buf.length, w: head.w, h: head.h, marge: marge, face: face, at: Date.now(),
        sig: sig, auto: !!auto, blob: blob, cols: cols, lignes: lignes,
        attendu_x: [r2(marge + g.bleed_off_px[0]), r2(marge + g.bleed_off_px[0] + g.trim_px[0])],
        attendu_y: [r2(marge + g.bleed_off_px[1]), r2(marge + g.bleed_off_px[1] + g.trim_px[1])],
        attendu_toile: [g.canvas_px[0] + 2 * marge, g.canvas_px[1] + 2 * marge],
        texts: head.texts, ppm: head.ppm,
      };
    } catch (e) {
      CTRL = { sig: sig, auto: !!auto,
        erreur: (e && e.missing) ? "backend absent : l'épreuve de contrôle est construite "
          + "par le domaine du cadre, elle ne peut pas être fabriquée dans le navigateur"
          : String((e && e.message) || e) };
    } finally { PA.hold--; PA.busyCtrl = false; if (!auto) M.busy(false); drawControl(); }
  }
  function drawControl() {
    if (!UI.ctrlTab) return;
    if (!CTRL) { UI.ctrlTab.innerHTML = ""; UI.cbadge.className = "cff-pbadge";
      UI.cbadge.textContent = "départ automatique…"; UI.ctrlDl.classList.add("hidden"); return; }
    if (CTRL.encours) { UI.cbadge.className = "cff-pbadge";
      UI.cbadge.textContent = (CTRL.auto ? "construction automatique…" : "construction…");
      UI.ctrlTab.innerHTML = ""; return; }
    if (CTRL.erreur) { UI.cbadge.className = "cff-pbadge ko"; UI.cbadge.textContent = "impossible";
      UI.ctrlTab.innerHTML = ""; UI.ctrlRead.textContent = CTRL.erreur;
      UI.ctrlDl.classList.add("hidden"); return; }
    const C = CTRL, rows = [];
    let bad = 0;
    const add = (q, a, m, ok, note) => { if (!ok) bad++; rows.push(proofRow(q, a, m, ok, note)); };
    const pres = (v, liste) => liste.some((k) => Math.abs(k - v) <= 1.01);
    add("Toile de l'épreuve", C.attendu_toile[0] + " x " + C.attendu_toile[1] + " px (toile livrée + "
      + CTRL_MARGE + " mm de papier de chaque côté)", C.w + " x " + C.h + " px lus dans IHDR",
      C.w === C.attendu_toile[0] && C.h === C.attendu_toile[1], "marge " + C.marge + " px");
    add("Traits de coupe verticaux", "sur x = " + C.attendu_x.join(" et ") + " px",
      C.cols.length + " colonne(s) noire(s) dans la bande du trait : " + C.cols.join(", "),
      pres(C.attendu_x[0], C.cols) && pres(C.attendu_x[1], C.cols),
      "cherchées dans les échantillons, pas dans l'en-tête — la coupe tombe entre deux pixels ("
      + C.attendu_x[0] + "), le trait est posé sur la colonne entière la plus proche");
    add("Traits de coupe horizontaux", "sur y = " + C.attendu_y.join(" et ") + " px",
      C.lignes.length + " ligne(s) noire(s) : " + C.lignes.join(", "),
      pres(C.attendu_y[0], C.lignes) && pres(C.attendu_y[1], C.lignes),
      "même méthode ; les colonnes et lignes en trop sont les quatre mires de repérage, "
      + "posées aux COINS du papier — le milieu du bas est réservé au cartouche");
    const pc = (C.texts.filter((t) => t.k === "PixelCheck")[0] || {}).v || "";
    add("La carte n'a pas bougé", "zone carte identique à la source, octet par octet",
      pc || "aucune mention PixelCheck", /identiques/.test(pc),
      "vérifié par le domaine du cadre APRÈS encodage, et écrit dans le fichier");
    const cm = (C.texts.filter((t) => t.k === "ControlProof")[0] || {}).v || "";
    add("Le fichier dit ce qu'il est", "« ÉPREUVE DE CONTRÔLE — NE PAS IMPRIMER »",
      cm.slice(0, 90) + (cm.length > 90 ? "…" : ""), /NE PAS IMPRIMER/.test(cm),
      "tEXt du fichier, relu ici");
    UI.ctrlTab.innerHTML =
      '<div class="cff-proofhd"><span>?</span><span>ce que l\'écran annonce</span>'
      + "<span>valeur annoncée</span><span>ce que les octets disent</span></div>" + rows.join("");
    const vieux = C.sig !== fileSig();
    C.perime = vieux;
    UI.cbadge.className = "cff-pbadge " + (bad ? "ko" : (vieux ? "" : "ok"));
    UI.cbadge.textContent = bad ? (bad + " écart(s) sur " + rows.length)
      : ((vieux ? "périmée depuis " : "✓ " + rows.length + " lignes vérifiées sur les octets · ")
        + hms(C.at));
    UI.cbadge.title = "Empreinte mesurée : " + C.sig + (C.auto ? " · départ automatique" : "")
      + (vieux ? " — le document a changé depuis." : "");
    UI.ctrlDl.classList.remove("hidden");
    UI.ctrlRead.innerHTML = "Épreuve de <b>" + C.octets.toLocaleString("fr-FR") + " octets</b>, "
      + C.w + " x " + C.h + " px. <b>Ce n'est pas le fichier d'impression</b> : elle porte du papier "
      + "en plus. Le fichier d'impression, lui, ne porte aucun repère — du trait de coupe au bord de "
      + "toile il n'y a que du <b>fond perdu</b>, et un repère y serait de l'encre sous la lame.";
  }

  /* ── verification par le backend : les millimetres de l'ecran et ceux du
        domaine /api/cards/<did>/frame doivent donner LES MEMES pixels. ────── */
  let vTimer = null;
  function scheduleVerify() { clearTimeout(vTimer); vTimer = setTimeout(verify, 500); }
  async function verify() {
    const el = UI.verify;
    if (!el) return;
    const g = CF.geom(), f0 = f(), w = winMM(g, f0);
    const local = localMetrics(g, f0, w);
    try {
      const r = await M.api.post("metrics", {
        fmt: g.fmt, dpi: g.dpi, bleed_mm: g.bleed_mm, safe_mm: g.safe_mm, corner_mm: g.corner_mm,
        line_mm: f0.line_mm, gap_mm: f0.gap_mm, edge_mm: f0.edge_mm, inner_mm: f0.inner_mm,
        window: { x: w.x, y: w.y, w: w.w, h: w.h, r: w.r },
        seal: f0.seal,
      });
      const b = r && r.metrics;
      if (!b) throw new Error("réponse vide");
      const bad = [];
      Object.keys(local).forEach((k) => {
        if (JSON.stringify(local[k]) !== JSON.stringify(b[k])) bad.push(k + " écran=" + JSON.stringify(local[k]) + " backend=" + JSON.stringify(b[k]));
      });
      /* LE PLAN D'OCCUPATION AUSSI. Deux placements differents, ce serait un
         apercu qui ment sur le fichier — exactement le bug WYSIWYG que tout
         le contrat cherche a rendre inexprimable. */
      const slots = CF.get("type.slots", []) || [];
      const ro = await M.api.post("occupancy", {
        fmt: g.fmt, dpi: g.dpi, bleed_mm: g.bleed_mm, safe_mm: g.safe_mm, corner_mm: g.corner_mm,
        frame: {
          inner_mm: f0.inner_mm, edge_mm: f0.edge_mm, rarity: f0.rarity, gem: f0.gem,
          banner: f0.banner, banner_text: f0.banner_text, window: f0.window,
          fit: f0.fit, socles: f0.socles, seats: f0.seats,
        },
        slots: slots,
      });
      const back = ro && ro.occupancy;
      const mine = occupancy(g, f0, slots);
      if (back) {
        const pick = (o) => ({ count: o.count, socles: o.socles, seats: o.seats,
          boxes: o.boxes.map((x) => [x.id, x.z, x.lane].concat(x.box)) });
        const A = JSON.stringify(pick(mine)), Bk = JSON.stringify(pick(back));
        if (A !== Bk) bad.push("occupation écran≠backend (" + mine.count + " vs " + back.count + " recouvrement(s))");
      }
      if (bad.length) {
        el.className = "cff-verify ko";
        el.textContent = "divergence : " + bad[0];
        el.title = bad.join(" · ");
      } else {
        el.className = "cff-verify ok";
        el.textContent = "filets + occupation vérifiés par le backend";
        el.title = "POST /api/cards/<did>/frame/metrics et /occupancy — mêmes millimètres, mêmes pixels, mêmes boîtes réservées";
      }
    } catch (e) {
      el.className = "cff-verify";
      el.textContent = (e && e.missing) ? "hors ligne — dessin local" : "vérification indisponible";
      el.title = String(e && e.message || e);
    }
  }
  function localMetrics(g, f0, w) {
    const mm = (v) => r2(v / 25.4 * g.dpi);
    /* les pixels PUBLIES sont ceux du DESSIN : si le format rabote la marge
       interieure, le chiffre affiche la suit. Un ecran qui annonce 20 mm quand
       le trace en pose 13,87 est exactement le badge menteur qu'on reproche
       aux autres. Le backend applique la meme borne, sans quoi la pastille de
       verification passerait au rouge sur le seul format concerne. */
    const cap = capOf(g);
    /* L'ANNEAU DU SCEAU, publie en NOMBRES PURS — deux TABLEAUX, pour la
       raison ecrite en face dans `frame_metrics`. La largeur publiee est
       celle qui sera TRACEE (bornee par le format), jamais celle du
       curseur : meme doctrine que la marge interieure ci-dessus. */
    const e = Math.min(f0.edge_mm, cap), epx = e / 25.4 * g.dpi;
    const smax = sealMaxMM(g.trim_mm[0], g.trim_mm[1], e, w);
    const swid = Math.min(f0.seal.width_mm, smax);
    return {
      line_px: mm(f0.line_mm), gap_px: mm(f0.gap_mm),
      edge_px: mm(Math.min(f0.edge_mm, cap)), inner_px: mm(Math.min(f0.inner_mm, cap)),
      corner_px: r2(g.corner_px),
      win_px: [r2(g.bleed_off_px[0] + w.x / 25.4 * g.dpi), r2(g.bleed_off_px[1] + w.y / 25.4 * g.dpi), mm(w.w), mm(w.h), mm(w.r)],
      seal_mm: [r2(swid), smax],
      seal_px: [mm(swid), r2(g.bleed_off_px[0] + epx), r2(g.bleed_off_px[1] + epx),
        r2(g.trim_px[0] - 2 * epx), r2(g.trim_px[1] - 2 * epx),
        r2(Math.max(0, g.corner_px - epx))],
      canvas_px: [g.canvas_px[0], g.canvas_px[1]],
    };
  }

  /* ── CE QUE L'ECRAN DIT DU SCEAU ─────────────────────────────────────────
     Spec §6.2bis-d : « L'ecran dit toujours quelle portee est active. » La
     ligne DECLARE les surfaces cochees, puis dit ce que CET ecran-ci montre —
     et rien d'autre. Elle ne promet pas ce que l'imprimeur ou le maillage
     feront de leur portee : une promesse ecrite ici serait fausse le jour ou
     l'utilisateur la lit. Ce qui est mesurable est dit ; le reste est tu. */
  function sealText(f0, g) {
    const s = f0.seal;
    if (!s.on) {
      return "Sceau <b>éteint</b> — le cadre est rendu exactement comme sans ce "
        + "réglage, et le fichier livré n'a pas un pixel de différence.";
    }
    const kind = (byId(SEAL_KINDS, s.kind) || SEAL_KINDS[0]).label;
    const act = [];
    if (s.scope.screen) act.push("écran");
    if (s.scope.print) act.push("impression");
    if (s.scope.mesh) act.push("3D");
    const w = winMM(g, f0);
    const cap = capOf(g);
    const smax = sealMaxMM(g.trim_mm[0], g.trim_mm[1], Math.min(f0.edge_mm, cap), w);
    const swid = Math.min(s.width_mm, smax);
    return "Portée déclarée : <b>" + (act.length ? esc(act.join(" + ")) : "aucune")
      + "</b>. " + (s.scope.screen
        ? ("Cet écran montre la surface <b>écran</b>, DANS la portée : contour "
          + "arc-en-ciel à la <b>phase canonique " + SEAL_PHASE + "</b> — l'aperçu "
          + "EST le fichier livré, au pixel.")
        : ("Cet écran montre la surface <b>écran</b>, HORS de la portée : le contour "
          + "y reste dans sa <b>base calme</b> (" + esc(kind.toLowerCase())
          + "), sans arc-en-ciel."))
      + (smax < SEAL_MIN_MM
        /* PAS D'ANNEAU DU TOUT — et l'ecran donne le remede, pas seulement le
           refus : entre le filet et la fenetre il n'y a plus la place du
           trait minimal d'un imprimeur foil. */
        ? (" Entre le filet extérieur et la fenêtre d'illustration, ce réglage "
          + "ne laisse pas les <b>" + SEAL_MIN_MM + " mm</b> qu'un imprimeur foil "
          + "exige : <b>aucun contour n'est dessiné</b>. Rapprocher le filet de "
          + "la coupe (retrait) ou reculer la fenêtre.")
        : (" Bande de <b>" + r2(swid) + " mm</b> (" + r1(swid / 25.4 * g.dpi)
          + " px), posée à <b>" + r2(Math.min(f0.edge_mm, cap))
          + " mm</b> de la coupe (l'axe du filet extérieur) et creusée vers l'intérieur"
          + (swid < s.width_mm
            ? (" — ramenée de " + r2(s.width_mm) + " mm par la <b>borne du format</b> : "
              + "au-delà, l'anneau mordrait sur la fenêtre d'illustration.")
            : ".")));
  }

  /* ── synchronisation de tout l'ecran ───────────────────────────────────── */
  let syncRaf = null;
  function sync() {
    if (!ROOT) return;
    if (syncRaf) return;
    syncRaf = requestAnimationFrame(() => { syncRaf = null; syncNow(); });
  }
  function syncNow() {
    const f0 = f(), g = CF.geom();
    buildGrids();
    const fam = byId(FAMILIES, f0.family);
    /* CE QUE CETTE LIGNE A LE DROIT DE DIRE. « 36 combinaisons » est un
       compte d'entrees, et c'est ainsi qu'elle le formule ; la VARIETE, elle,
       est mesuree a cote par le badge « silhouettes ». Et la definition n'est
       plus « 300 DPI » tout court : la toile est calculee pour 300, mais le
       fichier porte 11811 px/m, soit 299,9994 DPI — c'est ce nombre-la qu'un
       lecteur d'impression lira, et donc celui qu'on affiche. */
    UI.count.innerHTML = "<b>" + (FAMILIES.length * RARITIES.length) + "</b> combinaisons"
      + " <i>(</i>" + FAMILIES.length + " familles <i>x</i> " + RARITIES.length + " raretés<i>)</i>"
      + " <i>·</i> " + (fam ? esc(fam.label) : "aucun cadre")
      + " <i>x</i> " + esc((byId(RARITIES, f0.rarity) || {}).label || "")
      + " <i>·</i> toile <b>" + g.canvas_px[0] + " x " + g.canvas_px[1] + "</b> px calculée pour "
      + g.dpi + " DPI <i>·</i> le fichier porte <b>" + ppm(g.dpi) + " px/m = "
      + dpiOf(ppm(g.dpi)) + " DPI</b>";
    UI.count.title = "pHYs compte des pixels par MÈTRE entiers : 300 DPI exact n'y est pas "
      + "représentable. " + ppm(g.dpi) + " px/m est la valeur entière la plus proche, soit "
      + dpiOf(ppm(g.dpi)) + " DPI — un écart de "
      + r2(Math.abs(dpiOf(ppm(g.dpi)) - g.dpi) / g.dpi * 100 * 1000) + " millionièmes. On l'écrit.";
    UI.empty.classList.toggle("hidden", f0.family !== "none");
    UI.undo.disabled = !HIST.length;
    UI.redo.disabled = !REDO.length;
    UI.undo.textContent = "↶ Annuler" + (HIST.length ? " (" + HIST.length + ")" : "");

    /* millimetres ET pixels, cote a cote, sur CHAQUE longueur */
    const mmpx = (v) => r2(v) + " mm = " + r1(v / 25.4 * g.dpi) + " px";
    setNum(UI.lineRow, f0.line_mm, mmpx(f0.line_mm));
    setNum(UI.gapRow, f0.gap_mm, mmpx(f0.gap_mm));
    /* LA BORNE DU FORMAT, ECRITE ET APPLIQUEE AU CURSEUR. Elle ne vaut que
       lorsqu'elle est plus serree que la borne absolue — sur onze formats sur
       douze la ligne ne bouge pas d'un pixel. */
    const cap = capOf(g);
    const capE = Math.min(f0.edge_mm, cap), capI = Math.min(f0.inner_mm, cap);
    setNum(UI.edgeRow, capE, mmpx(capE));
    setNum(UI.innerRow, capI, mmpx(capI));
    [UI.edgeRow, UI.innerRow].forEach((row) => {
      const hi = Math.min(LIMITS[row.key][1], cap);
      row.rg.max = hi; row.nb.max = hi;
      const b = row.el.querySelector(".cff-bounds");
      if (b) {
        b.textContent = r2(LIMITS[row.key][0]) + " → " + r2(hi) + " mm"
          + (hi < LIMITS[row.key][1] ? " (borne du format)" : "");
        b.title = hi < LIMITS[row.key][1]
          ? ("Le curseur va jusqu'à " + LIMITS[row.key][1] + " mm, mais sur "
            + g.fmt + " (" + r2(g.trim_mm[0]) + " x " + r2(g.trim_mm[1])
            + " mm) au-delà de " + r2(cap) + " mm la bande garderait moins de "
            + BAND_MIN_MM + " mm d'ouverture — elle s'inverserait. Le dessin, "
            + "le modèle d'occupation et le backend appliquent tous les trois "
            + "cette borne : le nombre affiché est celui qui est tracé.")
          : "";
      }
    });
    /* les trois distances du filet exterieur, sans ambiguite possible */
    const px1 = (mm) => r1(mm / 25.4 * g.dpi);
    const eOut = capE - f0.line_mm / 2, eIn = capE + f0.line_mm / 2;
    UI.edgeRead.innerHTML = "Convention du <b>trait centré</b> : la valeur porte l'<b>axe</b>. "
      + "Avec un filet de " + r2(f0.line_mm) + " mm, l'encre occupe de <b>" + r2(eOut) + " mm</b> ("
      + px1(eOut) + " px) à <b>" + r2(eIn) + " mm</b> (" + px1(eIn) + " px) depuis le trait de coupe"
      + (eOut < 0 ? " — <b>le filet mord sur le fond perdu</b> : la coupe passe dedans." : "")
      + " · axe à " + r2(capE) + " mm = " + px1(capE) + " px de la coupe, soit "
      + r1(g.bleed_off_px[0] + capE / 25.4 * g.dpi) + " px du bord de <b>toile</b>."
      /* CE QUE LE PALIER FAIT, DIT A CELUI QUI REGLE LE FILET. Ce paragraphe
         est celui de l'utilisateur qui pose son filet : il dit ce que le
         reglage produit sur le papier. Le releve chiffre de la coupe a sa
         place — le tableau du fichier livre, plus bas — et il y est en
         entier ; le repeter ici avec son horloge et sa tolerance faisait de
         cette aide de reglage un cartouche d'auto-controle. Ce qui reste ici
         est ce qui SERT : l'anneau ne change pas d'aspect si la lame derive,
         et l'avertissement quand une autre couche deborde de la coupe. */
      + " Le fond de l'anneau garde le <b>même ton</b> de part et d'autre du trait de coupe : "
      + "si la lame passe à ± " + TOL_COUPE_MM + " mm, le bord de la carte a le même aspect "
      + "et l'arête du filet reste la seule de la zone."
      + ((PROOF && !PROOF.erreur && PROOF.coupe && PROOF.coupe_cadre
          && PROOF.coupe.pire_moyen > SEUIL_COUPE
          && PROOF.coupe_cadre.pire_moyen <= SEUIL_COUPE)
        ? " <b>Attention</b> : sur cette carte, une couche posée par-dessus le cadre "
          + "(texte ou illustration) déborde du trait de coupe."
        : "");
    /* LE SCEAU : sa largeur suit la MEME regle que le retrait et la marge —
       le curseur est ramene a la borne du format, et la borne est ECRITE. */
    const smax = sealMaxMM(g.trim_mm[0], g.trim_mm[1], capE, winMM(g, f0));
    const shi = Math.min(LIMITS.seal_width_mm[1], Math.max(LIMITS.seal_width_mm[0], smax));
    const swid = Math.min(f0.seal.width_mm, shi);
    setNum(UI.sealW, swid, mmpx(swid));
    UI.sealW.rg.max = shi; UI.sealW.nb.max = shi;
    const sb = UI.sealW.el.querySelector(".cff-bounds");
    if (sb) {
      sb.textContent = r2(LIMITS.seal_width_mm[0]) + " → " + r2(shi) + " mm"
        + (shi < LIMITS.seal_width_mm[1] ? " (borne du format)" : "");
    }
    UI.sealOn.input.checked = !!f0.seal.on;
    UI.sealKind.value = f0.seal.kind;
    Object.keys(UI.sealScope).forEach((k) => {
      UI.sealScope[k].input.checked = !!f0.seal.scope[k];
    });
    UI.sealRead.innerHTML = sealText(f0, g);
    setNum(UI.gradAngle, f0.grad_angle, f0.grad_angle + "°");
    setNum(UI.plateA, f0.plate_alpha, Math.round(f0.plate_alpha * 100) + " %");
    UI.double.input.checked = !!f0.double;
    UI.metal.input.checked = !!f0.metal;
    UI.grad.input.checked = !!f0.grad;
    UI.gem.input.checked = !!f0.gem;
    UI.banner.input.checked = !!f0.banner;
    UI.plate.input.checked = !!f0.plate;
    UI.winLock.input.checked = !!f0.win_lock;
    UI.backSame.input.checked = !!f0.back_same;
    UI.backLabel.input.checked = !!f0.back_label;
    /* le bloc du verso personnalise ne se decouvre que pour lui */
    UI.backCustom.classList.toggle("hidden", f0.back !== "custom");
    if (f0.back === "custom") drawBackList(f0);
    UI.backRead.innerHTML = backText(f0);
    UI.metalTone.value = f0.metal_tone;
    UI.corner.value = f0.corner;
    if (document.activeElement !== UI.bannerText) UI.bannerText.value = f0.banner_text || "";
    UI.color.value = f0.line_color || rgbHex(pal(f0).line);

    const w = winMM(g, f0);
    const wpx = localMetrics(g, f0, w).win_px;
    [["x", 0], ["y", 1], ["w", 2], ["h", 3], ["r", 4]].forEach((kv) => {
      const r = UI.win[kv[0]];
      if (document.activeElement !== r.i) r.i.value = r2(w[kv[0]]);
      r.px.textContent = r1(wpx[kv[1]]) + " px";
    });
    UI.winRead.innerHTML = "Fenêtre " + (w.auto ? "<b>automatique</b> (proportionnelle au format)" : "<b>manuelle</b>")
      + " — " + r2(w.w) + " x " + r2(w.h) + " mm = <b>" + r1(wpx[2]) + " x " + r1(wpx[3]) + " px</b>"
      + " · rayon de fenêtre " + r2(w.r) + " mm = " + r1(wpx[4]) + " px"
      + " · forme " + esc(WIN_SHAPE[f0.family] || "rect")
      /* DEUX LONGUEURS DIFFERENTES QUI VALENT TOUTES DEUX 3 mm, et deux
         nombres de pixels differents (35,4 et 35,5). On m'a reproche « deux
         chiffres pour un seul bord » : ce n'est pas un seul bord — l'un est
         l'arrondi du coin, l'autre la marge de papier autour de la rogne. Les
         DEUX chiffres restent affiches ; ce qui part, c'est la ligne de calcul
         qui les derivait a voix haute. Elle s'adressait a un correcteur : celui
         qui pose une fenetre veut la longueur, pas la demonstration. */
      + "<br><b>Rayon de coupe</b> " + r2(g.corner_mm) + " mm = <b>" + r1(g.corner_px) + " px</b>"
      + " <i>(l'arrondi des quatre coins de la carte)</i>"
      + " · <b>Décalage du fond perdu</b> " + r2(g.bleed_mm) + " mm = <b>" + r2(g.bleed_off_px[0]) + " x " + r2(g.bleed_off_px[1]) + " px</b>"
      + " <i>(l'encre en plus autour de la rogne, sur les quatre côtés)</i>"
      + " · <b>Zone sûre</b> " + r2(g.safe_mm) + " mm = <b>" + g.safe_px[0] + " x " + g.safe_px[1] + " px</b> à "
      + r2(g.safe_off_px[0]) + " x " + r2(g.safe_off_px[1]) + " px de la toile";

    drawOccupancy(g, f0);

    drawMap();
    /* pendant un glisser sur le plan, on ne rejoue ni les 19 vignettes ni la
       loupe a chaque pixel : la carte du haut suffit a suivre le geste. */
    if (MAPDRAG) return;
    drawGrids();
    drawAll();
    scheduleSil();
    scheduleLoupe();
    scheduleVerify();
    scheduleProof();
    scheduleSweep();
  }

  /* ── le compteur et la table des meubles ────────────────────────────────── */
  let LASTPLAN = null;
  function drawOccupancy(g, f0) {
    const plan = planOf(g, f0);
    LASTPLAN = plan;
    const n = plan.count;
    UI.occ.className = "cff-occ " + (n ? "ko" : "ok");
    UI.occ.textContent = n
      ? (n + " recouvrement" + (n > 1 ? "s" : "") + " de mention")
      : "0 recouvrement de mention";
    UI.occ.title = n
      ? plan.collisions.map((c) => c.a + " recouvre " + c.b + " sur " + c.mm2 + " mm² (" + c.pct + " % de la mention)").join(" · ")
      : "Aucun meuble de la couche 70 ne recouvre une mention de doc.type.slots — mesuré en mm² sur les boîtes réservées";
    UI.fit.input.checked = f0.fit !== false;
    UI.socles.input.checked = f0.socles !== false;
    UI.seats.input.checked = f0.seats !== false;
    setNum(UI.socleA, f0.socle_alpha, Math.round(f0.socle_alpha * 100) + " %");

    const rows = plan.boxes.filter((b) => b.id === "window" || b.id === "gem" || b.id === "banner"
      || b.id.indexOf("seat:") === 0 || b.id.indexOf("socle:") === 0);
    const mm2px = (v) => r1(v / 25.4 * g.dpi);
    UI.occTable.innerHTML =
      '<div class="cff-occhd"><span>meuble</span><span>couche</span><span>place</span><span>boîte (mm depuis la coupe)</span><span>en px</span></div>'
      + rows.map((b) => '<div class="cff-occr' + (b.z === 70 ? " top" : "") + '">'
        + "<span>" + esc(b.label) + "</span><span>z " + b.z + "</span><span>" + esc(b.lane) + "</span>"
        + "<span>" + b.box.map(r2).join(" · ") + "</span>"
        + "<span>" + b.box.map(mm2px).join(" · ") + "</span></div>").join("")
      + (plan.count ? plan.collisions.map((c) => '<div class="cff-occr bad"><span>' + esc(c.a)
        + "</span><span>recouvre</span><span>" + esc(c.b) + "</span><span>" + c.mm2
        + " mm²</span><span>" + c.pct + " % de la mention</span></div>").join("") : "");
    UI.occRead.innerHTML = "<b>" + plan.mentions.length + "</b> mention" + (plan.mentions.length > 1 ? "s" : "")
      + " lue" + (plan.mentions.length > 1 ? "s" : "") + " dans <b>doc.type.slots</b> (pièce 03) · "
      + "<b>" + plan.socles + "</b> socle" + (plan.socles > 1 ? "s" : "") + " · <b>" + plan.seats + "</b> logement"
      + (plan.seats > 1 ? "s" : "")
      + " · les meubles de la couche <b>40</b> passent sous le texte, ceux de la couche <b>70</b> par-dessus — "
      + "seuls ces derniers peuvent masquer une mention, et c'est eux que compte le badge.";
    /* AUCUN COMPTE QUE JE NE PEUX PAS TENIR. Cette ligne annonçait « six
       tEXt » alors que le fichier en porte neuf (Software, Format,
       Resolution, BleedBox, TrimBox, SafeBox, Face, Collisions, Comment) :
       un chiffre faux dans une interface dont tout l'argument est
       l'exactitude. On nomme les clés, elles sont vérifiables à l'octet. */
    UI.stampRead.innerHTML = "Le PNG livré porte <b>pHYs " + ppm(g.dpi) + " px/m</b> (soit <b>"
      + dpiOf(ppm(g.dpi)) + " DPI</b> réels — " + g.dpi + " DPI n'est pas représentable en pixels par "
      + "mètre entiers, et c'est la valeur entière la plus proche) et les "
      + "<b>tEXt</b> <i>Software · Format · Resolution · BleedBox · TrimBox · SafeBox · Face · "
      + "Collisions · Comment · Alpha</i> — BleedBox " + g.canvas_px[0] + "x" + g.canvas_px[1]
      + " px, TrimBox " + g.trim_px[0] + "x" + g.trim_px[1] + " px à " + r2(g.bleed_off_px[0]) + "," + r2(g.bleed_off_px[1])
      + " px, SafeBox " + g.safe_px[0] + "x" + g.safe_px[1] + " px. "
      + "Le backend relit IHDR avant d'estampiller : une toile qui ne fait pas " + g.canvas_px[0] + "x" + g.canvas_px[1]
      + " px est <b>refusée</b>, jamais estampillée d'une définition fausse."
      /* CE QUE CES BOITES NE SONT PAS. « Aucun RIP d'imprimeur ne lit un tEXt
         de PNG » — c'est exact, et le taire serait laisser croire a une
         intention d'impression lisible par une machine. Un PNG n'a pas de
         TrimBox : la norme n'en prevoit aucune. Seul pHYs est machine ; le
         reste est une indication humaine, et le seul chiffre qu'une machine
         lira vraiment ici, c'est la definition. */
      + "<br><b>Ce que ces boîtes ne sont pas.</b> La norme PNG ne prévoit <i>aucune</i> boîte de "
      + "coupe : <b>pHYs</b> est le seul chunk qu'une machine lira (la définition), les "
      + "<b>tEXt</b> sont une indication <b>humaine</b> — et le contrôle de cet écran. Les boîtes "
      + "<i>MediaBox / TrimBox / BleedBox</i> vraiment lues par un RIP n'existent que dans un "
      + "<b>PDF</b> : c'est la planche de la pièce 07 qui les porte, pas ce PNG. "
      + "Ce fichier-ci est une <b>carte</b>, pas une planche d'imposition.";
  }
  function setNum(row, v, read) {
    if (!row) return;
    if (document.activeElement !== row.nb) row.nb.value = r2(v);
    row.rg.value = v;
    row.rd.textContent = read;
  }
  function rgbHex(c) {
    const a = rgb(c);
    return "#" + a.map((x) => ("0" + x.toString(16)).slice(-2)).join("");
  }

  /* ── raccourcis clavier ────────────────────────────────────────────────── */
  function onKey(ev) {
    const panel = document.querySelector("#cf-panel-frame");
    if (!panel || !panel.classList.contains("on")) return;
    const t = ev.target;
    const typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT");
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === "z" || ev.key === "Z")) {
      ev.preventDefault();
      if (ev.shiftKey) redo(); else undo();
      return;
    }
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === "y" || ev.key === "Y")) { ev.preventDefault(); redo(); return; }
    if (typing || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    const f0 = f();
    const step = (list, id, d) => list[(idx(list, id) + d + list.length) % list.length].id;
    if (ev.key === "[") { set({ family: step(FAMILIES, f0.family, -1) }, "famille"); }
    else if (ev.key === "]") { set({ family: step(FAMILIES, f0.family, 1) }, "famille"); }
    else if (ev.key === ",") { set({ rarity: step(RARITIES, f0.rarity, -1) }, "rareté"); }
    else if (ev.key === ".") { set({ rarity: step(RARITIES, f0.rarity, 1) }, "rareté"); }
    else if (ev.key === "d" || ev.key === "D") { set({ double: !f0.double }, "double filet"); }
    else if (ev.key === "m" || ev.key === "M") { set({ metal: !f0.metal }, "métal"); }
    else if (ev.key === "g" || ev.key === "G") { set({ gem: !f0.gem }, "gemme"); }
    else if (ev.key === "v" || ev.key === "V") { const b = document.querySelector("#sideBtn"); if (b) b.click(); }
    else return;
    ev.preventDefault();
  }
})();
