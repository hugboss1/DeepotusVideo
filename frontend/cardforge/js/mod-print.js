/* ═══════════════════════════════════════════════════════════════════════════
   Card Forge — piece 07 · Impression   [P7]
   Proprietaire exclusif de : doc.print · aucun z · /api/cards/<did>/print/*
   Prefixe DOM impose : id="cf-print-..."   ·   feuille : css/mod-print.css

   CE QUE CETTE PIECE NE FAIT PAS : dessiner une carte. Elle IMPOSE des cartes
   rendues par CF.renderCard (via CF.cardBlob), les televerse, et le backend
   n'assemble que la planche. Le navigateur rend, le backend imprime : c'est la
   garantie WYSIWYG de la spec, et le backend la fait respecter mecaniquement
   en refusant tout bitmap dont la taille n'est pas geom.canvas_px.

   SEULE piece dont le JETON porte setFormat({fmt,dpi,bleed_mm,safe_mm,corner_mm}) :
   le selecteur de format nomme est ici. Il montre les DOUZE formats avec leurs
   millimetres, leurs pouces ET leurs pixels en permanence — nanDECK demande
   « CARDSIZE = 6.35, 8.89 » en centimetres, tape a la main, sans jamais dire
   combien de pixels cela fera.
   ═══════════════════════════════════════════════════════════════════════════ */
"use strict";

(function () {
  const CF = (typeof window !== "undefined") ? window.CF : null;
  if (!CF) throw new Error("mod-print: js/core.js doit etre charge avant ce fichier");

  /* icônes G2 (10/10/2026) : la suite « Deepotus Glyph » passe par le CORE
     (CF.icone), gardé `typeof` comme CF.chevronSVG — un CF de paille (bancs
     node) rend un marqueur qui porte la clé. */
  const ICO = (k, t, c) => (typeof CF.icone === "function" ? CF.icone(k, t, c)
    : '<i class="dzi" data-cle="' + k + '"></i>');

  /* ══ aides ═══════════════════════════════════════════════════════════════ */
  const esc = (s) => String(s == null ? "" : s).replace(/&/g, "&amp;")
    .replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  /* LE MEME ARRONDI QUE LE CONTRAT (floor(x+0.5), quantifie a 1e-9). Il ne
     sert QU'AU repli hors ligne des planches : toutes les dimensions de carte
     viennent de CF.geom()/CF.geomOf, jamais d'ici. */
  const R = (x) => Math.floor(Number(Number(x).toFixed(9)) + 0.5);
  const mmpx = (mm, dpi) => Number(mm) / 25.4 * Number(dpi);
  const px2pt = (v, dpi) => Number(v) * 72 / Number(dpi);
  const fx = (v, n) => Number(v).toFixed(n);
  /* nombre a la francaise, zeros de queue otes — et SEULEMENT ceux d'apres la
     virgule : un `replace(/\.?0+$/)` naif rend « 1 » pour 100. */
  const nf = (v, n) => {
    let s = Number(v).toFixed(n);
    if (s.indexOf(".") >= 0) s = s.replace(/0+$/, "").replace(/\.$/, "");
    return s.replace(".", ",");
  };
  /* UNE MESURE GARDE SES DECIMALES. « 0 µm » et « 0,0 µm » ne disent pas la
     meme chose : le second annonce la precision a laquelle on a mesure, le
     premier ressemble a un arrondi de confort. Meme regle que « 2 » contre
     « 2,00 » mm pour le fond perdu, deja appliquee plus bas. */
  const nfx = (v, n) => Number(v).toFixed(n).replace(".", ",");
  /* UN ECART SE LIT AVEC SON SIGNE, ET SUR LES DEUX AXES. Le panneau ecrivait
     « 26,7 µm SOUS le format nominal » a partir d'un maximum en valeur
     absolue : mesure sur les octets du PDF, la largeur est bien 26,7 µm en
     dessous, mais la hauteur est 10,7 µm AU-DESSUS. Le mot « sous » etait
     faux d'un axe sur deux. `xy` vient du backend ; `secours` n'est utilise
     que si le backend n'a pas encore repondu, et il est alors NON SIGNE. */
  const sgn = (v) => (Number(v) > 0 ? "+" : Number(v) < 0 ? "−" : "")
    + Number(Math.abs(Number(v))).toFixed(1).replace(".", ",");
  function signedUm(xy, secours) {
    if (!xy || xy.length < 2) return nfx(secours || 0, 1) + dzT("cartes.print.ecart_maximal");
    return sgn(xy[0]) + " / " + sgn(xy[1]) + dzT("cartes.print.ecart_lh");
  }
  const ko = (b) => (b < 1024 ? b + dzT("cartes.print.unite_o")
    : b < 1048576 ? (b / 1024).toFixed(1).replace(".", ",") + dzT("cartes.print.unite_ko")
      : (b / 1048576).toFixed(2).replace(".", ",") + dzT("cartes.print.unite_mo"));

  /* ══ etat local (hors document : rien de tout cela ne se sauvegarde) ═════ */
  let M = null, HOST = null, SHEETS = null, PLAN = null, BPLAN = null;
  let PF = null, PFBUSY = false, ICC = null, CAT = null;
  /* AUDIT : ce que le backend a LU dans les octets d'un PDF reellement ecrit.
     Aucun badge de ce panneau ne sort d'ailleurs. */
  let AUDIT = null;
  /* PFBODY : le corps EXACT du dernier controle avant vol. Il repart avec
     l'export, pour que la porte de la route juge ce que l'ecran a montre.
     FORCE : le passage en force, remis a faux apres CHAQUE export — un « oui »
     vaut pour un fichier, jamais pour la session. */
  let PFBODY = null, FORCE = false;
  /* La definition du repli raster du masque de foil. HORS DOCUMENT, comme
     FORCE : `doc.print` a un schema ferme cote CORE, et une definition de
     masque n'est pas un reglage d'imposition — c'est le choix d'un seul
     telechargement. Les valeurs admises viennent du backend (plan.foil). */
  let FOILDPI = 600;
  const LOG = [];
  const UNDO = [];
  const ARTS = new Map();          /* nom de fichier -> {w,h} | null */
  let VERIFY = { cls: "", txt: dzT("cartes.print.plan_non_verifie") };
  let vtimer = null, drag = null, PROBE = null;

  /* Repli hors ligne des planches : la table de contract.SHEETS, et la meme
     regle d'arrondi. Des que GET sheets repond, c'est SA reponse qui sert —
     et le bandeau de verification compare les deux. */
  const SHEET_FALLBACK = [
    { id: "a4", label: "A4 210 x 297 mm", size_mm: [210, 297] },
    { id: "letter", label: "Letter 8,5 x 11 in", size_mm: [215.9, 279.4] },
    { id: "a3", label: "A3 297 x 420 mm", size_mm: [297, 420] },
  ];
  const SHEET_CARD = { id: "card", label: "1 carte / page (boîtes exactes)" };
  const MARK_LABEL = { none: dzT("cartes.print.marques_aucun"), crop: dzT("cartes.print.marques_traits"), cross: dzT("cartes.print.marques_croix"), line: dzT("cartes.print.marques_lignes") };

  /* ══ LE PLAN D'IMPOSITION — miroir exact de build_plan() dans cards/print.py
     L'ecran ne peut pas attendre le reseau a chaque reglage : il calcule. Il
     CONFRONTE ensuite sa reponse a POST layout, et le moindre ecart devient
     une alarme visible — le meme dispositif que le CORE pour la geometrie de
     la carte. ═══════════════════════════════════════════════════════════════ */
  function sheetSize(id, dpi) {
    if (SHEETS) {
      const s = SHEETS.filter((x) => x.id === id)[0];
      if (s && s.px && s.px[String(dpi)]) return s.px[String(dpi)].slice();
    }
    const f = SHEET_FALLBACK.filter((x) => x.id === id)[0];
    return f ? [R(f.size_mm[0] / 25.4 * dpi), R(f.size_mm[1] / 25.4 * dpi)] : null;
  }

  function layoutOf(st, g, n) {
    const dpi = g.dpi, cw = g.trim_px[0], ch = g.trim_px[1];
    const warn = [];
    let sw, sh, cols, rows, gut, marge, ox, oy;
    if (st.sheet === "card") {
      sw = g.canvas_px[0]; sh = g.canvas_px[1];
      cols = 1; rows = 1; gut = 0; marge = 0;
      ox = g.bleed_off_px[0]; oy = g.bleed_off_px[1];
    } else {
      const s = sheetSize(st.sheet, dpi);
      if (!s) return null;
      sw = s[0]; sh = s[1];
      if (st.orient === "paysage") { const t = sw; sw = sh; sh = t; }
      gut = mmpx(st.gutter_mm, dpi); marge = mmpx(st.margin_mm, dpi);
      cols = Math.floor((sw - 2 * marge + gut) / (cw + gut));
      rows = Math.floor((sh - 2 * marge + gut) / (ch + gut));
      if (!(cols >= 1) || !(rows >= 1)) {
        return { fail: true, sheet_px: [sw, sh], cell_px: [cw, ch], cols: 0, rows: 0,
          per_page: 0, pages: 0, out_pages: 0, warnings: [{ level: "err", kind: "trop_grande",
            message: dzT("cartes.print.w_trop_grande", { cw: cw, ch: ch, sw: sw, sh: sh, marge: nf(st.margin_mm, 1) }) }] };
      }
      const cwid = cols * cw + (cols - 1) * gut, chei = rows * ch + (rows - 1) * gut;
      ox = st.center ? (sw - cwid) / 2 : marge;
      oy = st.center ? (sh - chei) / 2 : marge;
    }
    const per = cols * rows;
    const pages = (n && per) ? Math.ceil(n / per) : (per ? 1 : 0);
    const inner = cols > 1 ? Math.min(g.bleed_off_px[0], gut / 2) : g.bleed_off_px[0];
    if (st.sheet !== "card" && cols > 1 && gut < 2 * mmpx(g.bleed_mm, dpi) - 1e-9) {
      warn.push({ level: "warn", kind: "gouttiere_courte",
        message: dzT("cartes.print.w_gouttiere_courte", { g: nf(st.gutter_mm, 2), fp: nf(g.bleed_mm, 2), besoin: nf(2 * g.bleed_mm, 2), rogne: nf(gut / 2 / dpi * 25.4, 2) }),
        fix: { gutter_mm: Math.min(40, Math.round(2 * g.bleed_mm * 100) / 100),
          label: dzT("cartes.print.fix_porter_a", { v: nf(2 * g.bleed_mm, 2) }) } });
    }
    if (st.sheet !== "card" && marge < mmpx(g.bleed_mm, dpi) - 1e-9) {
      warn.push({ level: "warn", kind: "marge_courte",
        message: dzT("cartes.print.w_marge_courte", { m: nf(st.margin_mm, 2), fp: nf(g.bleed_mm, 2) }),
        fix: { margin_mm: Math.max(st.margin_mm, Math.ceil(g.bleed_mm)), label: dzT("cartes.print.fix_porter_a", { v: nf(Math.ceil(g.bleed_mm), 0) }) } });
    }
    if (st.sheet !== "card" && st.marks === "crop"
        && st.mark_off_mm < g.bleed_mm - 1e-9) {
      warn.push({ level: "warn", kind: "reperes_dans_le_fond_perdu",
        message: dzT("cartes.print.w_reperes_fp", { r: nf(st.mark_off_mm, 2), fp: nf(g.bleed_mm, 2) }),
        fix: { mark_off_mm: Math.round((g.bleed_mm + 0.5) * 100) / 100,
          label: dzT("cartes.print.fix_retrait", { v: nf(g.bleed_mm + 0.5, 2) }) } });
    }
    if (n && per && (n % per)) {
      warn.push({ level: "info", kind: "derniere_page_incomplete",
        message: dzT("cartes.print.w_derniere_page", { n: n % per, per: per }) });
    }
    /* LA DERIVE TOLEREE : MESUREE, PLUS AFFIRMEE. Elle etait annoncee egale au
       fond perdu restant en gouttiere (« 2,00 mm »). Mesure sur la geometrie
       ecrite : le trait allait d'une ligne de coupe a l'autre, donc la
       distance encre -> carte valait 0,0000 mm — et la croix, centree sur le
       coin, entrait de 2 mm DANS la carte. Le chiffre est desormais relu sur
       les segments rendus, exactement comme le backend le relit. */
    if (st.marks !== "none") {
      const pm = { cols: cols, rows: rows, cell_px: [cw, ch], gutter_px: gut,
        origin_px: [ox, oy], sheet_px: [sw, sh], per_page: per, dpi: dpi,
        fail: false };
      const segs = markSegs(pm, st), clr = markClearance(pm, st);
      const touche = markTouch(pm, st);
      if (segs.length && clr >= 0) {
        /* les deux fonds perdus viennent de la MEME fonction que l'affichage
           et que le backend (bleedReal), pas d'une approximation locale. */
        const br = bleedReal(pm, g, false);
        const bord = br[0] / dpi * 25.4, mmi = br[1] / dpi * 25.4;
        if (touche) {
          warn.push({ level: "err", kind: "reperes_sur_la_carte",
            message: dzT("cartes.print.w_reperes_touchent", { n: touche }),
            /* le correctif doit CORRIGER : porter la gouttiere a 6 mm laissait
               la distance a 0,0000 mm (mesure). */
            fix: (st.mark_safe === false
              ? { mark_safe: true, label: dzT("cartes.print.fix_reperes_hors_carte") }
              : { mark_off_mm: 1, label: dzT("cartes.print.fix_retrait_1mm") }) });
        } else {
          warn.push({ level: "ok", kind: "reperes_hors_carte",
            message: dzT("cartes.print.w_reperes_ok", { d: nf(clr / dpi * 25.4, 2), n: segs.length, g: gutterMarks(pm, st), bord: nf(bord, 2) })
              + (per < 2 ? "."
                : mmi > 0.005
                  ? dzT("cartes.print.w_reperes_ok_entre", { v: nf(mmi, 2) })
                  : dzT("cartes.print.w_reperes_ok_aucun")) });
        }
      }
    }
    /* hygiene de fichier d'impression — les memes regles que build_plan(),
       et le meme texte : c'est ce que le contrôle avant vol affichera. */
    if (st.intent === "none") {
      warn.push({ level: "warn", kind: "sans_intention_de_sortie",
        message: dzT("cartes.print.w_sans_intention"),
        fix: { intent: "srgb", label: dzT("cartes.print.fix_declarer_srgb") } });
    }
    if (st.mark_space === "rgb" && st.marks !== "none") {
      warn.push({ level: "warn", kind: "reperes_hors_reperage",
        message: dzT("cartes.print.w_reperes_rvb"),
        fix: { mark_space: "registration", label: dzT("cartes.print.fix_reperage") } });
    }
    if (st.color === "cmyk_device") {
      warn.push({ level: "warn", kind: "cmyk_sans_profil",
        message: dzT("cartes.print.w_cmyk_appareil") });
    }
    /* CE QUE LES CALQUES COUTENT, DIT AVANT L'EXPORT. Le contenu optionnel
       est une construction PDF 1.5 ; PDF/X-3:2003 est bati sur PDF 1.4 et ne
       l'admet pas. On ne peut pas avoir les deux, et on ne pretend pas le
       contraire. */
    if (st.layers && pdfxCapable(st)) {
      warn.push({ level: "warn", kind: "calques_contre_pdfx",
        message: dzT("cartes.print.w_calques_pdfx"),
        fix: { layers: false, label: dzT("cartes.print.fix_sans_calques") } });
    }
    const p0 = {
      sheet: st.sheet, orient: st.orient, dpi: dpi, sheet_px: [sw, sh],
      cols: cols, rows: rows, per_page: per, cell_px: [cw, ch],
      gutter_px: gut, margin_px: marge, origin_px: [ox, oy],
      content_px: [cols * cw + (cols - 1) * gut, rows * ch + (rows - 1) * gut],
      gutter_pt: px2pt(gut, dpi),
      n_cards: n, pages: pages, out_pages: pages * (st.duplex ? 2 : 1),
      inner_bleed_px: inner, warnings: warn, fail: false,
    };
    p0.page_pt = pagePt(p0, st);
    p0.iso_um = isoUm(p0, st);
    p0.iso_um_xy = isoUmXY(p0, st);
    Object.assign(p0, writtenMm(g));
    p0.mirror_um = mirrorUm(p0, st);
    return p0;
  }
  /* L'intention peut-elle porter une revendication PDF/X ? Les six conditions
     normalisees du registre ICC sont des conditions de PRESSE ; sRGB decrit la
     source. Pour un profil televerse, seul le backend a lu la classe dans les
     octets (« prtr » ou « mntr ») — on ne devine pas. */
  function pdfxCapable(s) {
    if (s.intent === "icc") {
      return !!(BPLAN && BPLAN.out_intent && BPLAN.out_intent.pdfx);
    }
    const list = (CAT && CAT.intents) || INTENT_FALLBACK;
    const it = list.filter((x) => x.id === s.intent)[0];
    return !!(it && it.space === "CMYK");
  }

  function cellRect(p, r, c) {
    return [p.origin_px[0] + c * (p.cell_px[0] + p.gutter_px),
      p.origin_px[1] + r * (p.cell_px[1] + p.gutter_px), p.cell_px[0], p.cell_px[1]];
  }
  /* ── LE VERSO EST LE MIROIR PHYSIQUE DU RECTO ───────────────────────────
     Inverser l'INDEX de colonne dit quelle carte va ou. Encore faut-il que la
     colonne inversee tombe a la position MIROIR : elle n'y tombe que si la
     grille est symetrique par rapport a l'axe de pliage, donc seulement quand
     l'imposition est CENTREE. Sans centrage, le verso partait avec tout
     l'espace reste de l'autre cote — 708,54 px = 59,99 mm mesures sur une A4
     a 10 mm de marge. Miroir de origin_for()/side_plan() cote backend ; le
     dessin et le fichier sortent donc de la meme regle. */
  function sidePlan(p, s, side) {
    if (!p || p.fail || side !== "back" || s.sheet === "card") return p;
    const o = [p.origin_px[0], p.origin_px[1]];
    if (s.flip === "long") o[0] = p.sheet_px[0] - p.origin_px[0] - p.content_px[0];
    else o[1] = p.sheet_px[1] - p.origin_px[1] - p.content_px[1];
    if (Math.abs(o[0] - p.origin_px[0]) < 1e-12
      && Math.abs(o[1] - p.origin_px[1]) < 1e-12) return p;
    const q2 = {};
    Object.keys(p).forEach((k) => { q2[k] = p[k]; });
    q2.origin_px = o;
    return q2;
  }
  /* L'ECART AU MIROIR PARFAIT, EN MICRONS, mesure case par case sur la
     geometrie qui sera ECRITE. 0 = le verso tombe derriere son recto. C'est
     le critere 9 du cahier des charges, et c'est la seule chose qui compte
     quand on retourne la feuille. */
  function mirrorUm(p, s) {
    if (!p || p.fail || !s.duplex || s.sheet === "card" || p.per_page < 1) return 0;
    const pf = sidePlan(p, s, "front"), pb = sidePlan(p, s, "back");
    let worst = 0;
    for (let i = 0; i < p.per_page; i++) {
      const r = Math.floor(i / p.cols), c = i % p.cols;
      const f = cellRect(pf, r, c);
      const b = s.flip === "long" ? cellRect(pb, r, p.cols - 1 - c)
        : cellRect(pb, p.rows - 1 - r, c);
      worst = s.flip === "long"
        ? Math.max(worst, Math.abs(b[0] - (p.sheet_px[0] - (f[0] + f[2]))),
          Math.abs(b[1] - f[1]))
        : Math.max(worst, Math.abs(b[1] - (p.sheet_px[1] - (f[1] + f[3]))),
          Math.abs(b[0] - f[0]));
    }
    return Math.round(worst / p.dpi * 25.4 * 10000) / 10;
  }
  function keepBleed(p, g, r, c) {
    const rc = cellRect(p, r, c);
    const l = c > 0 ? p.gutter_px / 2 : rc[0];
    const rr = c < p.cols - 1 ? p.gutter_px / 2 : (p.sheet_px[0] - (rc[0] + rc[2]));
    const t = r > 0 ? p.gutter_px / 2 : rc[1];
    const b = r < p.rows - 1 ? p.gutter_px / 2 : (p.sheet_px[1] - (rc[1] + rc[3]));
    return [Math.max(0, Math.min(g.bleed_off_px[0], l)), Math.max(0, Math.min(g.bleed_off_px[1], t)),
      Math.max(0, Math.min(g.bleed_off_px[0], rr)), Math.max(0, Math.min(g.bleed_off_px[1], b))];
  }
  /* LE FOND PERDU REELLEMENT POSE, en px : [bord de planche, gouttiere].
     Miroir de bleed_px_real() cote backend. `raster` rend la valeur de la
     planche PNG, ou tout tombe sur un pixel entier ; sinon celle du PDF, ou
     le chemin de rognage est a la coordonnee exacte. Les DEUX sont
     affichees : c'est le seul ecart entre les deux livrables du meme
     travail, et il vaut un demi-pixel. */
  function bleedReal(p, g, raster) {
    if (!p || p.fail) return [0, 0];
    const bx = g.bleed_off_px[0], by = g.bleed_off_px[1];
    const cw = p.cell_px[0], ch = p.cell_px[1];
    const outer = [], inner = [];
    for (let r = 0; r < Math.max(1, p.rows); r++) {
      for (let c = 0; c < Math.max(1, p.cols); c++) {
        const kb = keepBleed(p, g, r, c);
        let l = kb[0], t = kb[1], rr = kb[2], bo = kb[3];
        if (raster) {
          l = bx - R(bx - kb[0]); t = by - R(by - kb[1]);
          rr = R(bx + cw + kb[2]) - (bx + cw); bo = R(by + ch + kb[3]) - (by + ch);
        }
        (c > 0 ? inner : outer).push(l);
        (c < p.cols - 1 ? inner : outer).push(rr);
        (r > 0 ? inner : outer).push(t);
        (r < p.rows - 1 ? inner : outer).push(bo);
      }
    }
    const e = outer.length ? Math.min.apply(null, outer) : 0;
    return [e, inner.length ? Math.min.apply(null, inner) : e];
  }
  /* PIRE CAS DES DEUX COTES. Hors centrage, le verso n'a pas les memes marges
     que le recto : annoncer la mesure du recto sur un fichier recto-verso
     serait annoncer la meilleure des deux. Miroir de bleed_mm_sides(). */
  function bleedSides(p, g, s, raster) {
    const a = bleedReal(p, g, raster);
    if (!s.duplex || s.sheet === "card") return a;
    const b = bleedReal(sidePlan(p, s, "back"), g, raster);
    return [Math.min(a[0], b[0]), Math.min(a[1], b[1])];
  }
  /* La page PDF telle qu'elle sera ECRITE, en points, et son ecart au format
     nominal en microns. 2480 px a 300 DPI valent 595,2 pt ; l'A4 vaut
     595,2756 : 27 um d'ecart, releves par les deux controles. Le choix est
     desormais explicite, et le chiffre est affiche des deux cotes. */
  function sheetNominalPt(s) {
    if (s.sheet === "card") return null;
    const f = SHEET_FALLBACK.filter((x) => x.id === s.sheet)[0];
    const src = (SHEETS && SHEETS.filter((x) => x.id === s.sheet)[0]) || f;
    const mm = (src && src.size_mm) || (f && f.size_mm);
    if (!mm) return null;
    const w = mm[0] / 25.4 * 72, h = mm[1] / 25.4 * 72;
    return s.orient === "paysage" ? [h, w] : [w, h];
  }
  function pagePt(p, s) {
    const nom = s.page_iso ? sheetNominalPt(s) : null;
    return nom || [px2pt(p.sheet_px[0], p.dpi), px2pt(p.sheet_px[1], p.dpi)];
  }
  function isoUm(p, s) {
    const nom = sheetNominalPt(s);
    if (!nom) return 0;
    const pp = pagePt(p, s);
    return Math.max(Math.abs(pp[0] - nom[0]), Math.abs(pp[1] - nom[1])) / 72 * 25400;
  }
  /* ── LES TROIS MESURES « ECRITES », CALCULEES ICI AUSSI ──────────────────
     Elles etaient AFFICHEES depuis des cles que seul le backend remplit —
     lues sur PLAN, qui est le plan LOCAL : la ligne « rogne ecrite » sortait
     donc « 744 x 1039 px = ? mm », et l'ecart a l'ISO retombait sur le repli
     « ecart maximal » au lieu du signe par axe que le commentaire promettait.
     Un chiffre qu'on affiche, on le CALCULE — puis verify() le confronte au
     backend comme le reste du plan. */
  function isoUmXY(p, s) {
    const nom = sheetNominalPt(s);
    if (!nom) return null;
    const pp = pagePt(p, s);
    return [Math.round((pp[0] - nom[0]) / 72 * 25400 * 10) / 10,
      Math.round((pp[1] - nom[1]) / 72 * 25400 * 10) / 10];
  }
  function writtenMm(g) {
    const k = 25.4 / g.dpi;
    return {
      trim_mm_written: [g.trim_px[0] * k, g.trim_px[1] * k],
      trim_um_xy: [Math.round((g.trim_px[0] * k - g.trim_mm[0]) * 10000) / 10,
        Math.round((g.trim_px[1] * k - g.trim_mm[1]) * 10000) / 10],
      safe_mm_written: [g.safe_px[0] * k, g.safe_px[1] * k],
      safe_inset_mm: [(g.trim_px[0] - g.safe_px[0]) / 2 * k,
        (g.trim_px[1] - g.safe_px[1]) / 2 * k],
      safe_um_xy: [Math.round(((g.trim_px[0] - g.safe_px[0]) / 2 * k - g.safe_mm) * 10000) / 10,
        Math.round(((g.trim_px[1] - g.safe_px[1]) / 2 * k - g.safe_mm) * 10000) / 10],
    };
  }

  /* ══ LE RETRAIT DES REPERES — miroir exact de mark_keepout_px() ═══════════
     Le trait de gouttiere allait d'une ligne de coupe a l'autre : mesure sur
     la geometrie ecrite, la distance encre -> carte valait 0,0000 mm, et
     l'ecran annoncait 2 mm de derive toleree. La croix, elle, mordait 2 mm
     DANS la carte. Le retrait est donc calcule, applique aux trois styles, et
     RELU (markClearance) au lieu d'etre promis. */
  function markKeepout(p, st) {
    if (!p || p.fail || st.mark_safe === false) return 0;
    const off = mmpx(st.mark_off_mm, p.dpi), len = mmpx(st.mark_len_mm, p.dpi);
    const g = Number(p.gutter_px) || 0;
    if ((p.cols <= 1 && p.rows <= 1) || g <= 0) return Math.max(0, off);
    return Math.max(0, Math.min(off, (g - Math.min(len, g / 2)) / 2));
  }
  /* Retire de chaque segment ce dont l'ENCRE approcherait une carte a moins du
     retrait — l'encre deborde d'un demi-filet (bout rond), et ce demi-filet
     compte. Un segment qui traverse une carte ressort en DEUX morceaux. */
  function keepOff(segs, p, st, keep) {
    if (!(keep > 0) || p.per_page < 1) return segs;
    const demi = mmpx(st.mark_w_mm, p.dpi) / 2, cells = [];
    for (let r = 0; r < p.rows; r++) {
      for (let c = 0; c < p.cols; c++) cells.push(cellRect(p, r, c));
    }
    const out = [];
    segs.forEach((sg) => {
      const vert = Math.abs(sg[0] - sg[2]) < 1e-6;
      const fixe = vert ? sg[0] : sg[1];
      let vivants = [[Math.min(vert ? sg[1] : sg[0], vert ? sg[3] : sg[2]),
        Math.max(vert ? sg[1] : sg[0], vert ? sg[3] : sg[2])]];
      for (let i = 0; i < cells.length && vivants.length; i++) {
        const cl = cells[i];
        const f0 = (vert ? cl[0] : cl[1]) - keep;
        const f1 = (vert ? cl[0] + cl[2] : cl[1] + cl[3]) + keep;
        if (!(fixe + demi > f0 + 1e-9 && fixe - demi < f1 - 1e-9)) continue;
        const t0 = (vert ? cl[1] : cl[0]) - keep - demi;
        const t1 = (vert ? cl[1] + cl[3] : cl[0] + cl[2]) + keep + demi;
        const reste = [];
        vivants.forEach((v) => {
          if (v[1] <= t0 + 1e-9 || v[0] >= t1 - 1e-9) { reste.push(v); return; }
          if (v[0] < t0 - 1e-9) reste.push([v[0], t0]);
          if (v[1] > t1 + 1e-9) reste.push([t1, v[1]]);
        });
        vivants = reste;
      }
      vivants.forEach((v) => {
        if (v[1] - v[0] <= 1e-6) return;
        out.push(vert ? [fixe, v[0], fixe, v[1]] : [v[0], fixe, v[1], fixe]);
      });
    });
    return out;
  }
  /* LA DERIVE TOLEREE, RELUE sur les segments rendus : distance minimale entre
     l'encre et la rogne la plus proche. -1 = aucun repere. */
  function markClearance(p, st) {
    const segs = markSegs(p, st);
    if (!segs.length || !p || p.per_page < 1) return -1;
    const demi = mmpx(st.mark_w_mm, p.dpi) / 2;
    let pire = Infinity;
    for (let i = 0; i < segs.length; i++) {
      const s = segs[i];
      const ax0 = Math.min(s[0], s[2]) - demi, ax1 = Math.max(s[0], s[2]) + demi;
      const ay0 = Math.min(s[1], s[3]) - demi, ay1 = Math.max(s[1], s[3]) + demi;
      for (let r = 0; r < p.rows; r++) {
        for (let c = 0; c < p.cols; c++) {
          const cl = cellRect(p, r, c);
          const dx = Math.max(cl[0] - ax1, ax0 - (cl[0] + cl[2]), 0);
          const dy = Math.max(cl[1] - ay1, ay0 - (cl[1] + cl[3]), 0);
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < pire) { pire = d; if (pire <= 0) return 0; }
        }
      }
    }
    return pire === Infinity ? -1 : pire;
  }
  /* COMBIEN DE TRAITS TOUCHENT UNE CARTE. Zero est la seule valeur acceptable
     pour un fichier d'impression. Miroir de mark_touch() cote backend. */
  function markTouch(p, st) {
    const segs = markSegs(p, st);
    if (!segs.length || !p || p.per_page < 1) return 0;
    const demi = mmpx(st.mark_w_mm, p.dpi) / 2;
    let n = 0;
    segs.forEach((s) => {
      const ax0 = Math.min(s[0], s[2]) - demi, ax1 = Math.max(s[0], s[2]) + demi;
      const ay0 = Math.min(s[1], s[3]) - demi, ay1 = Math.max(s[1], s[3]) + demi;
      for (let r = 0; r < p.rows; r++) {
        for (let c = 0; c < p.cols; c++) {
          const cl = cellRect(p, r, c);
          if (ax1 > cl[0] + 1e-9 && ax0 < cl[0] + cl[2] - 1e-9
            && ay1 > cl[1] + 1e-9 && ay0 < cl[1] + cl[3] - 1e-9) { n++; return; }
        }
      }
    });
    return n;
  }

  /* les memes bandes que mark_segments() cote backend : ce qui se dessine ici
     est ce qui sortira dans le PDF, pas une illustration approchante. */
  function markSegs(p, st) {
    if (!p || p.fail || st.marks === "none" || p.per_page < 1) return [];
    const xs = [], ys = [];
    for (let c = 0; c < p.cols; c++) { const x = cellRect(p, 0, c)[0]; xs.push(x, x + p.cell_px[0]); }
    for (let r = 0; r < p.rows; r++) { const y = cellRect(p, r, 0)[1]; ys.push(y, y + p.cell_px[1]); }
    xs.sort((a, b) => a - b); ys.sort((a, b) => a - b);
    const sw = p.sheet_px[0], sh = p.sheet_px[1], out = [];
    const off = mmpx(st.mark_off_mm, p.dpi), len = mmpx(st.mark_len_mm, p.dpi);
    /* le meme _fini() que le backend : on ecarte l'encre des cartes, puis on
       pince a la planche. Les trois styles y passent, aucun n'est oublie. */
    const fini = (segs) => keepOff(segs, p, st, markKeepout(p, st)).filter(
      (s) => Math.abs(s[2] - s[0]) > 1e-6 || Math.abs(s[3] - s[1]) > 1e-6);
    if (st.marks === "line") {
      xs.forEach((x) => out.push([x, 0, x, sh]));
      ys.forEach((y) => out.push([0, y, sw, y]));
      return fini(out);
    }
    if (st.marks === "cross") {
      xs.forEach((x) => ys.forEach((y) => {
        out.push([x - len / 2, y, x + len / 2, y]); out.push([x, y - len / 2, x, y + len / 2]);
      }));
      return fini(out);
    }
    const bands = (lo, hi, span) => {
      const b = [[0, lo[0], false]];
      for (let i = 0; i < hi.length - 1; i++) b.push([hi[i], lo[i + 1], true]);
      b.push([hi[hi.length - 1], span, false]);
      return b.filter((x) => x[1] - x[0] > 1e-6);
    };
    const xlo = [], xhi = [], ylo = [], yhi = [];
    for (let c = 0; c < p.cols; c++) { const x = cellRect(p, 0, c)[0]; xlo.push(x); xhi.push(x + p.cell_px[0]); }
    for (let r = 0; r < p.rows; r++) { const y = cellRect(p, r, 0)[1]; ylo.push(y); yhi.push(y + p.cell_px[1]); }
    xs.forEach((x) => bands(ylo, yhi, sh).forEach((b) => {
      if (b[2]) out.push([x, b[0], x, b[1]]);
      else if (b[0] === 0) out.push([x, Math.max(b[0], b[1] - off - len), x, b[1] - off]);
      else out.push([x, b[0] + off, x, Math.min(b[1], b[0] + off + len)]);
    }));
    ys.forEach((y) => bands(xlo, xhi, sw).forEach((b) => {
      if (b[2]) out.push([b[0], y, b[1], y]);
      else if (b[0] === 0) out.push([Math.max(b[0], b[1] - off - len), y, b[1] - off, y]);
      else out.push([b[0] + off, y, Math.min(b[1], b[0] + off + len), y]);
    }));
    return fini(out);
  }

  /* COMBIEN DE TRAITS TRAVERSENT UNE GOUTTIERE, par page. Miroir exact de
     gutter_marks() cote backend : un trait de gouttiere est un segment
     ENTIEREMENT contenu dans une bande sans carte. */
  function gutterMarks(p, s) {
    if (!p || p.fail || p.cols < 1 || p.rows < 1 || s.marks === "none") return 0;
    const xlo = [], xhi = [], ylo = [], yhi = [];
    for (let c = 0; c < p.cols; c++) {
      const x = p.origin_px[0] + c * (p.cell_px[0] + p.gutter_px);
      xlo.push(x); xhi.push(x + p.cell_px[0]);
    }
    for (let r = 0; r < p.rows; r++) {
      const y = p.origin_px[1] + r * (p.cell_px[1] + p.gutter_px);
      ylo.push(y); yhi.push(y + p.cell_px[1]);
    }
    const bx = [], by = [];
    for (let i = 0; i < xlo.length - 1; i++) bx.push([xhi[i], xlo[i + 1]]);
    for (let i = 0; i < ylo.length - 1; i++) by.push([yhi[i], ylo[i + 1]]);
    let n = 0;
    markSegs(p, s).forEach((sg) => {
      const vert = Math.abs(sg[0] - sg[2]) < 1e-6;
      const lo = vert ? Math.min(sg[1], sg[3]) : Math.min(sg[0], sg[2]);
      const hi = vert ? Math.max(sg[1], sg[3]) : Math.max(sg[0], sg[2]);
      const bandes = vert ? by : bx;
      for (let i = 0; i < bandes.length; i++) {
        if (lo >= bandes[i][0] - 1e-6 && hi <= bandes[i][1] + 1e-6) { n++; break; }
      }
    });
    return n;
  }

  /* ══ document ════════════════════════════════════════════════════════════ */
  function st() {
    const d = CF.doc().print || {};
    const o = {};
    Object.keys(DEFAULTS).forEach((k) => { o[k] = (k in d) ? d[k] : DEFAULTS[k]; });
    return o;
  }
  const DEFAULTS = {
    sheet: "a4", orient: "portrait", margin_mm: 10, gutter_mm: 4, center: true,
    marks: "crop", mark_len_mm: 4, mark_off_mm: 3.5, mark_w_mm: 0.25,
    mark_color: "#e01b24", slug: true, duplex: false, flip: "long",
    duplex_order: "interleave", trimbox: "cards", artbox: "safe",
    /* SANS PERTE PAR DEFAUT : un master d'impression se degrade sur demande,
       jamais par defaut. Le reglage inverse coutait 2,1 % des pixels a plus
       de 8 niveaux d'ecart et un sous-echantillonnage chroma 4:2:0. */
    lossless: true,
    jpeg_quality: 95, card_fmt: "png", card_bits: 8, card_alpha: true, min_dpi: 300,
    /* prepresse : encre des reperes, espace des visuels, intention de sortie */
    mark_space: "registration", color: "rgb", intent: "srgb",
    /* L'ENCRE DE REPERAGE NE TOUCHE PAS LE PRODUIT. Coche, tout repere garde
       un retrait MESURE de la rogne ; decoche, le controle avant vol leve une
       erreur bloquante avec le chiffre (0,00 mm de derive toleree). */
    mark_safe: true,
    /* CALQUES PAR DEFAUT : l'imprimeur decoche les reperes et le cartouche
       sans editer le flux. Le prix est un en-tete %PDF-1.5, qui exclut la
       revendication PDF/X-3 (batie sur PDF 1.4) — c'est dit, avec le bouton
       pour decocher. */
    layers: true,
    /* La page PDF suit la grille du raster (595,2 pt pour 2480 px a 300 DPI) :
       PDF et planche PNG decrivent alors la MEME feuille. `page_iso` donne la
       page au format nominal exact, imposition centree dedans. */
    page_iso: false,
    /* GABARIT D'IMPRIMEUR (tache #83) : « maison » = le comportement
       historique. `profile_avant` retient, en JSON, le format et les reglages
       d'avant le gabarit pour les rendre au retour a « maison ». */
    profile: "maison", profile_avant: "",
  };
  /* Le libelle des intentions vient du backend (GET sheets) ; ceci n'est que
     le repli hors ligne, et il porte les MEMES identifiants de registre. */
  const INTENT_FALLBACK = [
    { id: "none", label: dzT("cartes.print.intent_aucune"), space: null },
    /* Le profil embarque est celui que littleCMS construit (588 o, tag desc
       « sRGB built-in ») : la colorimetrie est bien celle de sRGB, l'identite
       du fichier non. Il s'annoncait « sRGB IEC61966-2.1 » — reproche mesure
       et fonde. */
    { id: "srgb", label: dzT("cartes.print.intent_srgb"),
      space: "RGB" },
    { id: "fogra39", label: dzT("cartes.print.intent_fogra39"), space: "CMYK" },
    { id: "fogra51", label: dzT("cartes.print.intent_fogra51"), space: "CMYK" },
    { id: "fogra52", label: dzT("cartes.print.intent_fogra52"), space: "CMYK" },
    { id: "gracol", label: "CGATS TR 006 - GRACoL 2006", space: "CMYK" },
    { id: "swop", label: "CGATS TR 003 - SWOP 2006", space: "CMYK" },
    { id: "japan", label: "JC200103 - Japan Color 2001", space: "CMYK" },
    { id: "icc", label: dzT("cartes.print.intent_icc"), space: "ICC" },
  ];
  const MARK_SPACE_LABEL = {
    registration: dzT("cartes.print.encre_reperage"), cmyk_black: dzT("cartes.print.encre_noir"),
    rgb: dzT("cartes.print.encre_rvb"),
  };
  /* La couleur MONTREE pour chaque encre. Le repérage (100 % des quatre
     encres) se voit comme un noir tres dense : le dire en RVB sur un apercu,
     c'est WYSIWYG. Le PDF, lui, porte l'espace reel. */
  function markShown(s) {
    return s.mark_space === "registration" ? "#111111"
      : s.mark_space === "cmyk_black" ? "#000000" : s.mark_color;
  }

  function set(partial, quiet) {
    if (!quiet) UNDO.push(JSON.parse(JSON.stringify(st())));
    if (UNDO.length > 40) UNDO.shift();
    M.patch(partial);
  }
  function undo() {
    if (!UNDO.length) { CF.toast(dzT("cartes.print.rien_a_annuler")); return; }
    const prev = UNDO.pop();
    M.patch(prev);
    CF.toast(dzT("cartes.print.reglage_annule"));
  }

  /* ══ couleurs : les tokens, resolus par une sonde — le canvas ne sait pas
     lire var(--x), et coder une couleur en dur casserait le theme clair. ══ */
  function tone(name, fallback) {
    try {
      if (!PROBE) {
        PROBE = document.createElement("span");
        PROBE.style.cssText = "position:absolute;visibility:hidden;pointer-events:none";
        (HOST || document.body).appendChild(PROBE);
      }
      PROBE.style.color = "var(" + name + ")";
      const c = getComputedStyle(PROBE).color;
      return c || fallback;
    } catch (e) { return fallback; }
  }

  /* ══════════════════════════════════════════════════════════════════════════
     UI
     ══════════════════════════════════════════════════════════════════════════ */
  const q = (sel) => (HOST ? HOST.querySelector(sel) : null);
  const qa = (sel) => (HOST ? Array.prototype.slice.call(HOST.querySelectorAll(sel)) : []);

  function segHTML(id, opts, cur) {
    return '<div class="seg sm" data-seg="' + id + '">' + opts.map((o) =>
      '<button class="seg-b' + (String(o[0]) === String(cur) ? " active" : "")
      + '" type="button" data-v="' + esc(o[0]) + '">' + esc(o[1]) + "</button>").join("") + "</div>";
  }
  function numHTML(key, label, min, max, step, unit) {
    return '<label class="fld"><span class="lbl">' + esc(label) + '</span>'
      + '<span class="cf-print-num"><input type="number" data-num="' + key + '" min="' + min
      + '" max="' + max + '" step="' + step + '"><i class="cf-print-px" data-px="' + key + '">'
      + esc(unit || "") + "</i></span></label>";
  }
  function checkHTML(key, label) {
    return '<label class="check tiny"><input type="checkbox" data-chk="' + key + '"><span>'
      + esc(label) + "</span></label>";
  }

  function shell() {
    const s = st();
    HOST.innerHTML = ''
      + '<div class="cf-print-top">'
      + '<span class="cf-print-free">' + dzT("cartes.print.gratuit") + '</span>'
      + '<span class="cf-print-chk" data-role="verify">' + dzT("cartes.print.plan_non_verifie") + '</span>'
      + '<span class="tb-spacer"></span>'
      + '<button class="btn sm" type="button" data-act="guides" title="' + dzT("cartes.print.reperes_titre") + '">' + ICO("dz-edit-reperes", 16, "cf-ic") + dzT("cartes.print.reperes") + '</button>'
      + '<button class="btn sm" type="button" data-act="undo" title="' + dzT("cartes.print.annuler_titre") + '" aria-label="' + dzT("cartes.print.annuler_titre") + '">' + ICO("dz-action-annuler", 16) + '</button>'
      + '</div>'

      /* ── GABARIT D'IMPRIMEUR (tache #83) : le choix qui regle tout le reste ── */
      + '<details class="grp" open><summary>' + dzT("cartes.print.titre_gabarit") + '</summary><div class="grp-body">'
      + '<div class="cf-print-gabs" data-role="gabs"></div>'
      + '<p class="cf-print-ecart hidden" data-role="gab-ecart"></p>'
      + '<div class="btn-row">'
      + '<button class="btn strong hidden" type="button" data-act="pack" title="' + dzT("cartes.print.paquet_titre") + '">' + ICO("dz-action-telecharger", 16, "cf-ic") + dzT("cartes.print.paquet") + '</button>'
      + '</div>'
      + '<p class="hint">' + dzT("cartes.print.aide_gabarit") + '</p>'
      + '</div></details>'

      /* ── 0. CONTROLE AVANT VOL — AU-DESSUS DE LA LIGNE DE FLOTTAISON.
            Il etait annonce dans un sous-titre et enterre a 44 % de
            defilement : « annonce, pas montre ». Il est maintenant le
            premier bloc, et il se lance tout seul. ────────────────────── */
      + '<details class="grp" open><summary>' + dzT("cartes.print.titre_pf") + '</summary><div class="grp-body">'
      + '<div class="cf-print-pf" data-role="pf"></div>'
      + '<div class="btn-row">'
      + '<button class="btn strong" type="button" data-act="pf">' + dzT("cartes.print.recontroler") + ' <b>(V)</b></button>'
      + '<button class="btn" type="button" data-act="bench" title="' + dzT("cartes.print.banc_titre") + '">' + dzT("cartes.print.banc") + '</button>'
      + '</div>'
      + '<p class="hint">' + dzT("cartes.print.aide_pf1")
      /* CE QU'ON NE PEUT PAS REMESURER ICI, ON NE L'AFFICHE PLUS. Cette phrase
         comptait les occurrences d'un mot dans le manuel d'un autre produit :
         invérifiable depuis ce panneau, donc retirée. Un chiffre qu'on ne peut
         pas refaire vaut moins que pas de chiffre. */
      + dzT("cartes.print.aide_pf2") + '</p>'
      + '</div></details>'

      /* ── 1. FORMAT ─────────────────────────────────────────────────────── */
      + '<details class="grp" open><summary>' + dzT("cartes.print.titre_format", { n: '<b data-role="fmtn">12</b>' }) + '</summary>'
      + '<div class="grp-body">'
      + '<div class="cf-print-fmt"><div class="cf-print-head">'
      + '<span>format</span><span title="' + dzT("cartes.print.format_nominal") + '">' + dzT("cartes.print.col_rogne_mm") + '</span><span>' + dzT("cartes.print.col_rogne_in") + '</span>'
      + '<span title="' + dzT("cartes.print.col_rogne_px_titre") + '">'
      + dzT("cartes.print.col_rogne_px") + '</span><span>' + dzT("cartes.print.col_toile_px") + '</span><span class="cf-print-hide-sm">' + dzT("cartes.print.col_zone_sure") + '</span>'
      + '</div><div class="cf-print-fmt-scroll" data-role="fmts"></div></div>'
      + '<div class="grid2">'
      + '<label class="fld"><span class="lbl">' + dzT("cartes.print.definition") + '</span>'
      + segHTML("dpi", CF.DPIS.map((d) => [d, d + " DPI"]), CF.geom().dpi) + '</label>'
      + numHTML("bleed_mm", dzT("cartes.print.fond_perdu"), 0, 10, 0.5, "mm")
      + '</div><div class="grid2">'
      + numHTML("safe_mm", dzT("cartes.print.zone_sure"), 0, 10, 0.5, "mm")
      + numHTML("corner_mm", dzT("cartes.print.rayon_coin"), 0, 10, 0.5, "mm")
      + '</div>'
      + '<p class="hint">' + dzT("cartes.print.aide_fond_perdu")
      /* MESURE, PAS COMPARAISON : sur les 12 formats, 7 tombent sur des pixels
         entiers a 300 comme a 600 DPI (3 seulement a 150) — ce sont les
         imperiaux. Les 5 metriques laissent quelques microns, et l'infobulle
         de chaque ligne les chiffre au lieu de les taire. */
      + dzT("cartes.print.aide_formats") + '</p>'
      + '</div></details>'

      /* ── 2. PLANCHE ────────────────────────────────────────────────────── */
      + '<details class="grp" open><summary>' + dzT("cartes.print.titre_planche") + '</summary><div class="grp-body">'
      + '<div class="grid2">'
      + '<label class="fld"><span class="lbl">' + dzT("cartes.print.planche") + '</span>'
      + segHTML("sheet", [["a4", "A4"], ["letter", "Letter"], ["a3", "A3"], ["card", dzT("cartes.print.une_carte")]], s.sheet) + '</label>'
      + '<label class="fld"><span class="lbl">Orientation</span>'
      + segHTML("orient", [["portrait", "Portrait"], ["paysage", dzT("cartes.print.paysage")]], s.orient) + '</label>'
      + '</div>'
      + '<div class="grid2">' + numHTML("margin_mm", dzT("cartes.print.marge"), 0, 60, 0.5, "mm")
      + numHTML("gutter_mm", dzT("cartes.print.gouttiere"), 0, 40, 0.5, "mm") + '</div>'
      + '<div class="cf-print-plan">'
      + '<canvas class="cf-print-canvas" data-role="plan" width="264" height="330"></canvas>'
      + '<div class="cf-print-side">'
      + '<dl class="cf-print-read" data-role="read"></dl>'
      + '<div class="cf-print-warns" data-role="warns"></div>'
      + '</div></div>'
      + '<p class="hint">' + dzT("cartes.print.aide_poignees") + '</p>'
      + '<div class="sep"></div>'
      + '<div class="grid2">'
      + '<label class="fld"><span class="lbl">' + dzT("cartes.print.reperes_marques") + '</span>'
      + segHTML("marks", [["crop", dzT("cartes.print.seg_traits")], ["cross", dzT("cartes.print.seg_croix")], ["line", dzT("cartes.print.seg_lignes")], ["none", dzT("cartes.print.seg_aucun")]], s.marks) + '</label>'
      + '<label class="fld"><span class="lbl" data-role="colorlbl">' + dzT("cartes.print.couleur_reperes") + '</span>'
      + '<input class="cf-print-color" type="color" data-color="mark_color"></label>'
      + '</div>'
      + '<div class="cf-print-3">' + numHTML("mark_len_mm", dzT("cartes.print.longueur"), 0, 20, 0.5, "mm")
      + numHTML("mark_off_mm", dzT("cartes.print.retrait"), 0, 20, 0.5, "mm")
      + numHTML("mark_w_mm", dzT("cartes.print.epaisseur"), 0.02, 2, 0.05, "mm") + '</div>'
      + '<div class="grid2">' + checkHTML("center", dzT("cartes.print.centrer"))
      + checkHTML("slug", dzT("cartes.print.cartouche")) + '</div>'
      /* LE RETRAIT DES REPERES : un reglage, parce que le trait de gouttiere
         touchait la carte et que la derive toleree valait 0,00 mm pendant que
         l'ecran en annoncait 2,00. Decoche, le controle avant vol REFUSE. */
      + '<div class="grid2">'
      + checkHTML("mark_safe", dzT("cartes.print.reperes_hors_carte")) + '</div>'
      + '<div class="sep"></div>'

      /* ── recto-verso, avec la PREUVE du miroir affichee ─────────────────── */
      + '<div class="grid2">' + checkHTML("duplex", dzT("cartes.print.recto_verso"))
      + checkHTML("lossless", dzT("cartes.print.sans_perte")) + '</div>'
      + '<div class="grid2">'
      + '<label class="fld"><span class="lbl">' + dzT("cartes.print.retournement") + '</span>'
      + segHTML("flip", [["long", dzT("cartes.print.bord_long")], ["short", dzT("cartes.print.bord_court")]], s.flip) + '</label>'
      + '<label class="fld"><span class="lbl">' + dzT("cartes.print.ordre_pages") + '</span>'
      + segHTML("duplex_order", [["interleave", dzT("cartes.print.rv_alterne")], ["grouped", dzT("cartes.print.rectos_versos")]], s.duplex_order) + '</label>'
      + '</div>'
      + '<div class="cf-print-duplex" data-role="duplex"></div>'
      + '<div class="grid2">'
      + '<label class="fld"><span class="lbl">' + dzT("cartes.print.trimbox") + '</span>'
      + segHTML("trimbox", [["cards", dzT("cartes.print.emprise_cartes")], ["page", dzT("cartes.print.page_entiere")]], s.trimbox) + '</label>'
      + '<label class="fld"><span class="lbl">' + dzT("cartes.print.artbox") + '</span>'
      + segHTML("artbox", [["safe", dzT("cartes.print.zone_sure")], ["trim", "= TrimBox"]], s.artbox) + '</label>'
      + '</div>'
      /* ── DEUX CHOIX QUE L'IMPRIMEUR RECLAMAIT, ET QUI SE MESURENT ─────── */
      + '<div class="grid2">'
      + checkHTML("layers", dzT("cartes.print.calques"))
      + checkHTML("page_iso", dzT("cartes.print.page_iso"))
      + '</div>'
      + '<p class="hint">' + dzT("cartes.print.aide_calques") + '</p>'
      + '<div class="btn-row">'
      + '<button class="btn strong" type="button" data-act="png">' + dzT("cartes.print.btn_planche_png") + ' <b>(P)</b></button>'
      + '<button class="btn strong" type="button" data-act="pdf">' + dzT("cartes.print.btn_pdf") + ' <b>(D)</b></button>'
      + '<button class="btn" type="button" data-act="mire" title="' + dzT("cartes.print.mire_titre") + '">' + ICO("dz-action-telecharger", 16, "cf-ic") + dzT("cartes.print.mire") + '</button>'
      + '</div>'
      + '<p class="hint">' + dzT("cartes.print.aide_cadres") + '</p>'
      + '</div></details>'

      /* ── 2 bis. PREPRESSE : COULEUR ────────────────────────────────────── */
      + '<details class="grp" open><summary>' + dzT("cartes.print.titre_couleur") + '</summary>'
      + '<div class="grp-body">'
      + '<label class="fld"><span class="lbl">' + dzT("cartes.print.intention") + '</span>'
      + '<select class="cf-print-sel" data-sel="intent"></select></label>'
      + '<p class="hint" data-role="intentread"></p>'
      + '<div class="grid2">'
      + '<label class="fld"><span class="lbl">' + dzT("cartes.print.espace_visuels") + '</span>'
      + segHTML("color", [["rgb", dzT("cartes.print.rvb_etiquete")], ["cmyk_device", dzT("cartes.print.cmyk_appareil")],
        ["cmyk_icc", dzT("cartes.print.cmyk_profil")]], s.color) + '</label>'
      + '<label class="fld"><span class="lbl">' + dzT("cartes.print.encre_reperes") + '</span>'
      + segHTML("mark_space", [["registration", dzT("cartes.print.seg_reperage")], ["cmyk_black", dzT("cartes.print.seg_noir")],
        ["rgb", dzT("cartes.print.seg_rvb")]], s.mark_space) + '</label>'
      + '</div>'
      + '<div class="cf-print-icc" data-role="icc"></div>'
      + '<div class="btn-row">'
      + '<label class="btn sm" for="cf-print-iccfile">' + dzT("cartes.print.charger_icc") + '</label>'
      + '<input id="cf-print-iccfile" class="cf-print-file" type="file" accept=".icc,.icm">'
      + '<button class="btn sm" type="button" data-act="iccdel">' + dzT("cartes.print.retirer_icc") + '</button>'
      + '</div>'
      /* ── L'AUDIT DES OCTETS. Le panneau n'a le droit d'afficher que ce
            qu'un fichier reellement ecrit porte : ce bloc est la preuve, et
            il est vide tant que personne n'a mesure. ────────────────────── */
      + '<div class="sep"></div>'
      + '<div class="cf-print-pf" data-role="audit"></div>'
      + '<div class="btn-row">'
      + '<button class="btn" type="button" data-act="audit" title="' + dzT("cartes.print.audit_titre") + '">' + dzT("cartes.print.auditer") + '</button>'
      + '</div>'
      + '<p class="hint">' + dzT("cartes.print.aide_audit") + '</p>'
      + '<p class="hint">' + dzT("cartes.print.aide_reperage") + ' '
      /* « une vingtaine » etait un chiffre qu'aucun ecran ne peut verifier (le
         navigateur ne lit pas ce dossier) et qui depend du poste : releve du
         12/08 sur cette machine, 31 fichiers. Les TROIS noms cites, eux, sont
         verifiables un par un — on garde les noms, on retire le compte. */
      + dzT("cartes.print.aide_windows_icc", { chemin: '<span class="mono">C:\\Windows\\System32\\spool\\drivers\\color</span>' }) + '</p>'
      + '</div></details>'

      /* ── 2 ter. MASQUE DE FOIL ─────────────────────────────────────────────
            Le Sceau prismatique appartient au panneau CADRE ; ce bloc n'en
            tire que la plaque, et il DIT tout ce que le controle avant vol
            dirait — avant l'export, pas apres le refus. C'est le defaut de
            forme que la tache 1 a nomme : refuser sans donner la sortie. */
      + '<details class="grp" open><summary>' + dzT("cartes.print.titre_foil") + '</summary>'
      + '<div class="grp-body">'
      + '<div class="cf-print-pf" data-role="foil"></div>'
      + '<div class="grid2">'
      + '<label class="fld"><span class="lbl">' + dzT("cartes.print.foil_definition") + '</span>'
      + segHTML("foil_dpi", [[600, "600 dpi"], [1200, "1200 dpi"]], FOILDPI) + '</label>'
      + '</div>'
      + '<div class="btn-row">'
      + '<button class="btn strong" type="button" data-act="foilmask">' + dzT("cartes.print.btn_foil") + '</button>'
      + '</div>'
      + '<p class="hint">' + dzT("cartes.print.aide_foil1") + '</p>'
      + '<p class="hint">' + dzT("cartes.print.aide_foil2") + '</p>'
      + '</div></details>'

      /* ── 3. CARTE SEULE ────────────────────────────────────────────────── */
      + '<details class="grp"><summary>' + dzT("cartes.print.titre_carte") + '</summary><div class="grp-body">'
      + '<div class="grid2">'
      + '<label class="fld"><span class="lbl">' + dzT("cartes.print.fichier") + '</span>'
      + segHTML("card_fmt", [["png", "PNG"], ["jpeg", "JPEG q95"]], s.card_fmt) + '</label>'
      + '<label class="fld"><span class="lbl">' + dzT("cartes.print.profondeur") + '</span>'
      + segHTML("card_bits", [[8, "8 bits"], [16, "16 bits"]], s.card_bits) + '</label>'
      + '</div>'
      + checkHTML("card_alpha", dzT("cartes.print.transparence"))
      + '<div class="btn-row">'
      + '<button class="btn strong" type="button" data-act="card">' + dzT("cartes.print.exporter_carte") + ' <b>(C)</b></button>'
      + '<button class="btn strong" type="button" data-act="cards">' + dzT("cartes.print.toutes_cartes") + '</button>'
      + '</div>'
      + '<p class="hint" data-role="cardread"></p>'
      + '</div></details>'

      /* ── 5. JOURNAL ────────────────────────────────────────────────────── */
      + '<details class="grp"><summary>' + dzT("cartes.print.titre_journal") + '</summary><div class="grp-body">'
      + '<div class="cf-print-log" data-role="log"></div></div></details>'

      + '<div class="cf-print-keys">'
      + '<span><kbd>R</kbd> ' + dzT("cartes.print.k_reperes") + '</span><span><kbd>P</kbd> ' + dzT("cartes.print.k_planche") + '</span>'
      + '<span><kbd>D</kbd> PDF</span><span><kbd>C</kbd> ' + dzT("cartes.print.k_carte") + '</span>'
      + '<span><kbd>V</kbd> ' + dzT("cartes.print.k_controle") + '</span><span><kbd>&#8593;</kbd><kbd>&#8595;</kbd> format</span>'
      + '<span><kbd>Ctrl</kbd>+<kbd>Z</kbd> ' + dzT("cartes.print.k_annuler") + '</span></div>';
  }

  /* ── le menu des intentions de sortie ──────────────────────────────────── */
  function paintIntents() {
    const sel = q('[data-sel="intent"]');
    if (!sel) return;
    const list = (CAT && CAT.intents) || INTENT_FALLBACK;
    const cur = st().intent;
    sel.innerHTML = list.map((x) => '<option value="' + esc(x.id) + '"'
      + (x.id === cur ? " selected" : "") + '>' + esc(x.label) + '</option>').join("");
  }

  /* ── la table des formats ──────────────────────────────────────────────── */
  function paintFormats() {
    const host = q('[data-role="fmts"]');
    if (!host) return;
    const cur = CF.geom(), f0 = CF.doc().format;
    const cnt = q('[data-role="fmtn"]');
    /* le titre dit « les N » : N est COMPTE, pas ecrit a la main. La table
       en annoncait 12 et le panneau n'en laissait voir que 9. */
    if (cnt) cnt.textContent = String(CF.FORMATS.length);
    host.innerHTML = CF.FORMATS.map((f) => {
      /* CF.geomOf : la geometrie du CORE, au fond perdu NATIF du format —
         aucun pixel n'est calcule ici. */
      const g = CF.geomOf(f.id, cur.dpi, CF.nativeBleed(f.id), CF.nativeBleed(f.id), f0.corner_mm);
      /* LA COLONNE « rogne mm » EST LE NOMINAL, LA COLONNE « rogne px » EST
         CE QUI PART DANS LA /TrimBox. Les deux ne coincident que sur les sept
         formats imperiaux ; ailleurs la grille de 300 DPI laisse quelques
         microns, et l'infobulle les chiffre au lieu de les taire. */
      const ew = g.trim_px[0] / cur.dpi * 25.4, eh = g.trim_px[1] / cur.dpi * 25.4;
      const dx = (ew - g.trim_mm[0]) * 1000, dy = (eh - g.trim_mm[1]) * 1000;
      const tip = f.label + dzT("cartes.print.tip_rogne_ecrite", { w: fx(ew, 4), h: fx(eh, 4) })
        + (Math.max(Math.abs(dx), Math.abs(dy)) < 0.05 ? dzT("cartes.print.tip_nominal_exact")
          : dzT("cartes.print.tip_ecart", { dx: sgn(dx), dy: sgn(dy) }));
      return '<button class="cf-print-row' + (f.id === cur.fmt ? " on" : "") + '" type="button"'
        + ' data-fmt="' + esc(f.id) + '" title="' + esc(tip) + '">'
        + '<span class="cf-print-nm">' + esc(f.label.replace(/\s*\d.*$/, "")) + '</span>'
        + '<span class="mono">' + nf(g.trim_mm[0], 2) + " x " + nf(g.trim_mm[1], 2) + '</span>'
        + '<span class="mono">' + fx(g.trim_in[0], 2) + " x " + fx(g.trim_in[1], 2) + '</span>'
        + '<b class="mono">' + g.trim_px[0] + " x " + g.trim_px[1] + '</b>'
        + '<b class="mono">' + g.canvas_px[0] + " x " + g.canvas_px[1] + '</b>'
        + '<span class="mono cf-print-hide-sm">' + g.safe_px[0] + " x " + g.safe_px[1] + '</span>'
        + '</button>';
    }).join("");
  }

  /* ── lecture du plan ───────────────────────────────────────────────────── */
  function paintRead() {
    const p = PLAN, g = CF.geom(), s = st(), d = q('[data-role="read"]');
    if (!d) return;
    if (!p || p.fail) {
      d.innerHTML = '<dt>' + dzT("cartes.print.dt_plan") + '</dt><dd class="big">' + dzT("cartes.print.impossible") + '</dd>';
    } else {
      const n = CF.cards().length;
      const bp = bleedSides(p, g, s, false), br = bleedSides(p, g, s, true);
      /* deux decimales TOUJOURS : « 2 » et « 2,00 » ne disent pas la meme
         chose a un imprimeur. */
      const mm = (v) => Number(v / p.dpi * 25.4).toFixed(2).replace(".", ",");
      /* les deux livrables, cote a cote : le PDF detoure a la coordonnee
         exacte, la planche PNG tombe au pixel. L'ecart vaut un demi-pixel et
         il est ECRIT, pas tu. */
      const memes = Math.abs(bp[0] - br[0]) < 1e-9 && Math.abs(bp[1] - br[1]) < 1e-9;
      const cut = (arr) => arr.map(mm).join(" · ");
      /* la derive toleree : MESUREE ici, et confrontee a la mesure du backend
         (verify() la met dans BPLAN.mark_clearance_mm). */
      const clr = markClearance(p, s);
      const bclr = (BPLAN && typeof BPLAN.mark_clearance_mm === "number"
        && BPLAN.mark_clearance_mm >= 0) ? BPLAN.mark_clearance_mm : null;
      const xs = [], ys = [];
      markSegs(p, s).forEach((sg) => {
        if (Math.abs(sg[0] - sg[2]) < 1e-6 && xs.indexOf(sg[0]) < 0) xs.push(sg[0]);
        if (Math.abs(sg[1] - sg[3]) < 1e-6 && ys.indexOf(sg[1]) < 0) ys.push(sg[1]);
      });
      xs.sort((a, b) => a - b); ys.sort((a, b) => a - b);
      d.innerHTML = ''
        + '<dt>' + dzT("cartes.print.dt_grille") + '</dt><dd class="big">' + p.cols + ' x ' + p.rows + ' = ' + p.per_page + ' /page</dd>'
        + '<dt>' + dzT("cartes.print.dt_planche") + '</dt><dd>' + p.sheet_px[0] + ' x ' + p.sheet_px[1] + ' px</dd>'
        /* LA PAGE, ET SON ECART AU FORMAT NOMINAL — les deux controles ont
           releve que 595,2 pt n'est pas l'A4 de l'ISO (595,2756). L'ecart
           n'est plus subi en silence : il est chiffre, dans les deux sens. */
        /* SIGNE, ET PAR AXE. « 26,7 µm sous le format nominal » etait faux
           d'un axe sur deux : mesure sur les octets, la largeur est 26,7 µm
           EN DESSOUS et la hauteur 10,7 µm AU-DESSUS. Un maximum en valeur
           absolue cachait l'autre moitie de la mesure. */
        + '<dt>' + dzT("cartes.print.dt_page_pdf") + '</dt><dd>' + fx(p.page_pt[0], 4) + ' x ' + fx(p.page_pt[1], 4) + ' pt'
        + (s.sheet === "card" ? ''
          : p.iso_um < 0.05
            ? ' · <b>' + dzT("cartes.print.nominal_exact") + '</b>'
            : ' · <span class="dim">' + signedUm(p.iso_um_xy, p.iso_um)
              + dzT("cartes.print.du_nominal_raster") + '</span>') + '</dd>'
        /* LA ROGNE ECRITE, PAS LA ROGNE NOMINALE. La table affiche
           63,00 x 88,00 mm a cote de 744 x 1039 px : ces deux colonnes ne
           disent pas la meme chose, et l'ecart etait tu. */
        + '<dt>' + dzT("cartes.print.dt_rogne") + '</dt><dd>' + g.trim_px[0] + ' x ' + g.trim_px[1] + ' px = '
        + (p.trim_mm_written ? nfx(p.trim_mm_written[0], 3) + ' x '
          + nfx(p.trim_mm_written[1], 3) : '?') + ' mm'
        + (p.trim_um_xy && Math.max(Math.abs(p.trim_um_xy[0]), Math.abs(p.trim_um_xy[1])) >= 0.05
          ? ' · <span class="dim">' + signedUm(p.trim_um_xy, 0) + dzT("cartes.print.du_nominal_esp")
            + nf(g.trim_mm[0], 2) + ' x ' + nf(g.trim_mm[1], 2) + '</span>'
          : ' · <b>' + dzT("cartes.print.nominal_exact") + '</b>') + '</dd>'
        + '<dt>' + dzT("cartes.print.dt_gouttiere") + '</dt><dd>' + fx(p.gutter_pt, 2).replace(".", ",") + ' pt · '
        + fx(p.gutter_px, 2).replace(".", ",") + ' px</dd>'
        + '<dt>' + dzT("cartes.print.dt_fond_perdu") + '</dt><dd>' + dzT("cartes.print.fp_regle_pose", { r: nf(g.bleed_mm, 2), bord: mm(bp[0]), gout: mm(bp[1]) }) + '</dd>'
        + (memes ? '' : '<dt></dt><dd class="dim">' + dzT("cartes.print.fp_png", { a: mm(br[0]), b: mm(br[1]) }) + '</dd>')
        /* LA ZONE SURE ECRITE, PAS LA ZONE SURE REGLEE. Le meme traitement
           que la rogne juste au-dessus : « zone sure 3 mm » s'affichait a
           cote d'une /ArtBox qui pose 2,963 mm de retrait sur la hauteur —
           37 microns de marge annonces que le fichier ne porte pas. Le
           chiffre vient du BACKEND (le plan verifie), et il est signe. */
        + '<dt>' + dzT("cartes.print.col_zone_sure") + '</dt><dd>' + g.safe_px[0] + ' x ' + g.safe_px[1] + ' px'
        + (p.safe_mm_written ? ' = ' + nfx(p.safe_mm_written[0], 3) + ' x '
          + nfx(p.safe_mm_written[1], 3) + ' mm' : '')
        + (s.artbox === "safe" ? dzT("cartes.print.ecrite_artbox") : '') + '</dd>'
        + (p.safe_inset_mm
          ? '<dt></dt><dd class="dim">' + dzT("cartes.print.zs_retrait", { a: nfx(p.safe_inset_mm[0], 3), b: nfx(p.safe_inset_mm[1], 3), r: nf(g.safe_mm, 2) })
            + (p.safe_um_xy && Math.max(Math.abs(p.safe_um_xy[0]), Math.abs(p.safe_um_xy[1])) >= 0.5
              ? ' · ' + signedUm(p.safe_um_xy, 0) : ' · <b>exact</b>') + '</dd>'
          : '')
        + '<dt>' + dzT("cartes.print.dt_cartes") + '</dt><dd>' + dzT("cartes.print.cartes_pages", { n: n, p: p.pages })
        + (s.duplex ? dzT("cartes.print.x2_rv") : '') + '</dd>'
        + '<dt>' + dzT("cartes.print.dt_coupe") + '</dt><dd>' + MARK_LABEL[s.marks] + ' · ' + markSegs(p, s).length
        + dzT("cartes.print.traits_sep") + esc(MARK_SPACE_LABEL[s.mark_space]) + '</dd>'
        /* LA DERIVE TOLEREE : DISTANCE MESUREE entre l'encre et la rogne la
           plus proche, sur les segments rendus — jamais la valeur d'un
           reglage. Elle etait annoncee egale au fond perdu restant (2 mm)
           alors qu'elle valait 0,0000 mm : le trait de gouttiere touchait la
           carte. Le chiffre est confronte au backend par verify(). */
        + (s.marks === "none" || clr < 0 ? ''
          : '<dt>' + dzT("cartes.print.derive") + '</dt><dd>' + (clr < 1e-9
            ? '<b class="cf-print-bad">' + dzT("cartes.print.derive_touche", { n: markTouch(p, s) }) + '</b>'
            : '<b>' + nfx(clr / p.dpi * 25.4, 2) + ' mm</b>'
              + ' <span class="dim">' + dzT("cartes.print.derive_avant") + '</span>')
          + (bclr !== null && Math.abs(bclr - clr / p.dpi * 25.4) < 0.006
            ? ' <span class="dim">· ' + dzT("cartes.print.mesure_backend") + '</span>' : '') + '</dd>')
        + (xs.length ? '<dt>' + dzT("cartes.print.dt_colonnes") + '</dt><dd class="dim">' + cut(xs) + ' mm</dd>' : '')
        + (ys.length ? '<dt>' + dzT("cartes.print.dt_rangees") + '</dt><dd class="dim">' + cut(ys) + ' mm</dd>' : '');
    }
    paintDuplex();
    paintIntentRead();
    paintFoil();
    const w = q('[data-role="warns"]');
    if (w) {
      const ws = (p && p.warnings) || [];
      w.innerHTML = ws.length ? ws.map((x, i) => '<div class="cf-print-w ' + x.level + '">'
        + '<span>' + esc(x.message) + '</span>'
        + (x.fix ? '<button class="lnk cf-print-fix" type="button" data-fix="' + i + '">'
          + esc(x.fix.label) + '</button>' : '') + '</div>').join("")
        : '<div class="cf-print-w info">' + dzT("cartes.print.plan_sain") + '</div>';
      w.querySelectorAll("[data-fix]").forEach((b) => b.addEventListener("click", () => {
        const fx2 = ws[Number(b.dataset.fix)].fix;
        const o = {}; Object.keys(fx2).forEach((k) => { if (k !== "label") o[k] = fx2[k]; });
        set(o);
      }));
    }
    const cr = q('[data-role="cardread"]');
    if (cr) {
      /* LA DENSITE ECRITE, PAS LA DENSITE REGLEE. L'unite du chunk pHYs est
         le METRE ENTIER : 300 DPI vaudrait 11811,0236 px/m, la grille
         n'accepte que 11811, et 11811 px/m REDONNE 299,9994 DPI. Ecrire
         « 300 DPI » a cote de « pHYs 11811 » affirme une egalite fausse — un
         audit l'a releve sur une autre piece, il valait pour celle-ci.
         Les deux chiffres viennent du BACKEND (plan verifie), pas d'un
         arrondi local. */
      const ppm = BPLAN ? BPLAN.phys_ppm : null;
      const pdpi = BPLAN ? BPLAN.phys_dpi : null;
      cr.innerHTML = dzT("cartes.print.cr_rendu", { w: g.canvas_px[0], h: g.canvas_px[1], dpi: g.dpi })
        + (ppm
          ? dzT("cartes.print.cr_densite", { ppm: ppm, dpi: String(pdpi).replace(".", ","), cible: g.dpi })
          : dzT("cartes.print.cr_densite_nv"))
        + dzT("cartes.print.cr_espace")
        /* LE 16 BITS N'EST PLUS UNE PHRASE, C'EST UNE MESURE. Un audit a
           prouve ailleurs qu'un badge « 16 bits » peut etre faux alors que
           l'IHDR le confirme : les echantillons tombaient tous sur le reseau
           k x 257. Ici l'elargissement est VOULU — et il se demontre : le
           bouton d'audit encode la meme rampe de 256 niveaux en 8 et en 16
           bits, decompresse les deux fichiers et compte. */
        + (AUDIT && AUDIT.depth && AUDIT.depth["16"] && AUDIT.depth["16"].exact
          ? dzT("cartes.print.cr_16_mesure", { octets: AUDIT.depth["16"].bytes, ech: AUDIT.depth["16"].samples.toLocaleString("fr-FR"), dist: AUDIT.depth["16"].distinct, utiles: nfx(AUDIT.depth["16"].useful_bits, 2) })
            + (AUDIT.depth["16"].lattice_257
              ? dzT("cartes.print.cr_257")
              : dzT("cartes.print.cr_vraies_16"))
          : dzT("cartes.print.cr_16_conteneur"));
    }
    const v = q('[data-role="verify"]');
    if (v) { v.className = "cf-print-chk " + VERIFY.cls; v.textContent = VERIFY.txt; }
  }

  /* ── LE MIROIR DUPLEX : UNE MESURE, PLUS UN BADGE ───────────────────────
     Ce bandeau disait « Miroir vérifié » et ne vérifiait RIEN : il se
     contentait de réciter l'inversion des index — la même que celle qui
     posait le verso 59,99 mm à côté de son recto dès que l'imposition
     n'était pas centrée. Il affiche maintenant l'ÉCART MESURÉ en microns
     entre chaque verso et la position miroir de son recto, et le mot
     « vérifié » n'apparaît que quand le backend a rendu le même chiffre sur
     la géométrie qu'il écrira. */
  function duplexMap(p, s) {
    const out = [];
    for (let i = 0; i < p.per_page; i++) {
      let r = Math.floor(i / p.cols), c = i % p.cols;
      if (s.flip === "long") c = p.cols - 1 - c; else r = p.rows - 1 - r;
      out.push([i + 1, r + 1, c + 1]);
    }
    return out;
  }
  function paintDuplex() {
    const box = q('[data-role="duplex"]'), p = PLAN, s = st();
    if (!box) return;
    if (!p || p.fail || !s.duplex) { box.innerHTML = ""; return; }
    const m = duplexMap(p, s);
    const um = Number(p.mirror_um || 0);
    const bum = (BPLAN && typeof BPLAN.mirror_um === "number") ? BPLAN.mirror_um : null;
    const accord = bum !== null && Math.abs(bum - um) < 0.15;
    const bon = um < 1 && (bum === null || bum < 1);
    box.innerHTML = '<div class="cf-print-dx' + (bon ? '' : ' ko') + '"><b>'
      + (bon ? dzT("cartes.print.dx_ok", { um: nfx(um, 1) }) : dzT("cartes.print.dx_faux", { um: nfx(um, 1) })) + '</b> — ' + dzT("cartes.print.dx_retournement") + ' '
      + (s.flip === "long" ? dzT("cartes.print.dx_long")
        : dzT("cartes.print.dx_court")) + ' : '
      + m.slice(0, 6).map((x) => 'F' + x[0] + '&#8596;B(' + x[1] + ',' + x[2] + ')').join(" · ")
      + (m.length > 6 ? " …" : "") + '. '
      + (bon
        ? dzT("cartes.print.dx_bon")
        : dzT("cartes.print.dx_mauvais"))
      + (accord ? dzT("cartes.print.dx_accord", { um: nfx(bum, 1) })
        : bum === null ? dzT("cartes.print.dx_pas_confirme")
          : dzT("cartes.print.dx_backend", { um: nfx(bum, 1) }))
      + '</div>';
  }

  /* ══ LE MASQUE DE FOIL — CE QUE L'ECRAN DIT AVANT L'EXPORT ═══════════════
     LECTURE D'ETAT PARTAGE, PAS UN IMPORT. `doc.frame.seal` appartient a P2 ;
     P7 le LIT par CF.get (le document est partage, le CODE ne l'est pas —
     regle 8), exactement comme la liste des calques lit `type.slots`.
     LES MILLIMETRES, EUX, VIENNENT DU BACKEND (`plan.foil`). Ils ne sont PAS
     recalcules ici : mod-frame.js tient deja l'unique implementation d'ecran
     de la borne du Sceau, et une TROISIEME copie dans P7 serait exactement le
     « piege des deux cadres » que la spec nomme — trois rasterisations d'un
     meme contour qui ne tomberaient plus au meme endroit. */
  function paintFoil() {
    const box = q('[data-role="foil"]');
    if (!box) return;
    const s = CF.get("frame.seal", null);
    const on = !!(s && s.on), pr = !!(s && s.scope && s.scope.print);
    const f = (BPLAN && BPLAN.foil) || null;
    const btn = q('[data-act="foilmask"]');
    /* IL FAUT QUE LES DEUX SOIENT D'ACCORD. Le plan vient du backend et peut
       DATER : entre le clic qui decoche « impression » et la reponse de
       /layout, `f.live` vaut encore vrai. Ne regarder que lui laissait le
       bouton actif sous un panneau qui ecrit « hors portee impression » — et
       le clic partait chercher un masque que la route refuse en 409. */
    if (btn) btn.disabled = !(on && pr && f && f.live);
    if (!on || !pr) {
      box.innerHTML = '<div class="cf-print-pf-ok muted">'
        + (on
          ? dzT("cartes.print.foil_hors_portee")
          : dzT("cartes.print.foil_aucun")) + '</div>';
      return;
    }
    if (!f) {
      box.innerHTML = '<div class="cf-print-pf-ok muted">' + dzT("cartes.print.foil_attente") + '</div>';
      return;
    }
    const rows = [];
    /* LE DOCUMENT AVOUE AVANT LE RESTE : un retrait negatif ne peut venir que
       d'un fichier edite a la main (les deux surfaces de P2 le tiennent dans
       [0 ; 8]) et il ferait tomber la dorure sur la carte VOISINE. La plaque
       est ramenee au trait de coupe ; le document, lui, est nomme. */
    if (Number(f.edge_asked_mm) < 0) {
      rows.push(["err", dzT("cartes.print.foil_negatif", { v: nfx(f.edge_asked_mm, 2) })]);
    }
    if (!f.live) {
      /* DEUX CAUSES ETRANGERES l'une a l'autre, et deux remedes differents :
         la PLACE (fenetre trop pres du filet) ou la LARGEUR ECRITE dans le
         document. Les confondre faisait ecrire « il ne reste que 5,00 mm,
         sous le trait minimal de 0,2 mm » — un chiffre qui refute sa phrase. */
      rows.push(["warn", dzT("cartes.print.foil_pas_anneau")
        + (Number(f.cap_mm) < Number(f.min_mm)
          ? dzT("cartes.print.foil_place", { edge: nfx(f.edge_mm, 2), cap: nfx(f.cap_mm, 2), min: nf(f.min_mm, 1) })
          : dzT("cartes.print.foil_largeur", { asked: nfx(f.asked_mm, 2), cap: nfx(f.cap_mm, 2) }))
        + dzT("cartes.print.foil_sans_masque")]);
    } else {
      if (f.width_mm < f.min_mm) {
        rows.push(["err", dzT("cartes.print.foil_trait_min", { w: nfx(f.width_mm, 2), min: nf(f.min_mm, 1) })]);
      }
      const proche = f.edge_mm < f.trim_mm;
      rows.push([proche ? "warn" : "ok", dzT("cartes.print.foil_anneau", { kind: esc(f.kind), w: nfx(f.width_mm, 2), edge: nfx(f.edge_mm, 2) })
        + (proche
          ? dzT("cartes.print.foil_proche", { t: nf(f.trim_mm, 1), variance: esc(f.variance) })
          : dzT("cartes.print.foil_audela", { t: nf(f.trim_mm, 1) }))]);
      rows.push(["ok", dzT("cartes.print.foil_pdf", { calque: esc(f.layer) })
        + (st().layers ? '' : dzT("cartes.print.foil_sans_calques"))
        + dzT("cartes.print.foil_repli", { dpi: FOILDPI })]);
    }
    box.innerHTML = rows.map((r) => '<div class="cf-print-pf-row ' + r[0] + '">'
      + '<span class="cf-print-c">foil</span>'
      + '<span class="cf-print-m">' + r[1] + '</span>'
      + '<span class="cf-print-v">' + (r[0] === "ok" ? ICO("dz-etat-succes", 16) : "&#8212;")
      + '</span></div>').join("");
  }

  function paintIntentRead() {
    const el = q('[data-role="intentread"]');
    if (!el) return;
    const s = st();
    const list = (CAT && CAT.intents) || INTENT_FALLBACK;
    const it = list.filter((x) => x.id === s.intent)[0];
    if (!it || !it.space) {
      el.innerHTML = '<span class="cf-print-bad">' + dzT("cartes.print.ir_aucune") + '</span>';
      return;
    }
    const bpf = (BPLAN && BPLAN.out_intent) || null;
    /* CE QUI SERA ECRIT, AVEC SON SOUS-TYPE. « /S /GTS_PDFX » est le
       sous-type DEFINI PAR PDF/X : le poser sur un fichier qui n'a ni
       /GTS_PDFXVersion, ni XMP, ni /Trapped, c'est se presenter comme ce
       qu'on n'est pas — deux controles independants l'ont releve sur les
       octets. Le panneau annonce donc le sous-type REEL, et la revendication
       n'est affichee que lorsque la structure complete l'accompagne. */
    el.innerHTML = dzT("cartes.print.ir_ecrit") + '<b class="mono">'
      + esc((bpf && bpf.subtype) || "?") + '</b> · ' + dzT("cartes.print.ir_identifiant") + ' <b>'
      + esc((bpf && bpf.id) || it.icc || it.label) + '</b>'
      + (bpf && bpf.profile_bytes
        ? dzT("cartes.print.ir_profil", { n: bpf.profile_bytes })
          + (bpf.cls ? dzT("cartes.print.ir_classe", { cls: esc(bpf.cls) }) : '')
        : dzT("cartes.print.ir_condition"))
      + (bpf
        ? (bpf.claim
          ? dzT("cartes.print.ir_claim", { v: esc(bpf.version) })
          : dzT("cartes.print.ir_sans_claim")
            + (bpf.pdfx
              ? dzT("cartes.print.ir_calques")
              : bpf.press ? dzT("cartes.print.ir_inexploitable")
                : dzT("cartes.print.ir_source"))
            + dzT("cartes.print.ir_honnete"))
        : dzT("cartes.print.ir_non_confirme"));
  }

  /* ══ L'AUDIT DU FICHIER : LA SEULE SOURCE DES CHIFFRES AFFICHES ══════════
     Un badge peut etre faux alors que l'en-tete le confirme : il suffit de
     s'arreter a l'en-tete. Ce bouton fabrique un VRAI PDF avec le plan
     courant, le relit OCTET PAR OCTET cote backend, et affiche la mesure a
     cote de chaque affirmation. Rien ici ne vient d'un reglage. */
  async function runAudit() {
    const box = q('[data-role="audit"]');
    if (box) box.innerHTML = '<div class="cf-print-pf-ok">' + dzT("cartes.print.audit_en_cours") + '</div>';
    try {
      const r = await M.api.post("audit", specNow({}));
      AUDIT = (r && r.audit) || null;
    } catch (e) {
      AUDIT = null;
      if (box) {
        box.innerHTML = '<div class="cf-print-pf-ok ko">'
          + esc(String((e && e.message) || e)) + '</div>';
      }
      return;
    }
    paintAudit();
    /* la phrase du panneau « Carte seule » porte desormais la profondeur
       MESUREE : elle doit se rafraichir avec l'audit. */
    paintRead();
  }
  function paintAudit() {
    const box = q('[data-role="audit"]');
    if (!box) return;
    if (!AUDIT) {
      box.innerHTML = '<div class="cf-print-pf-ok muted">' + dzT("cartes.print.audit_aucun") + '</div>';
      return;
    }
    const a = AUDIT;
    const ligne = (quoi, mesure, bon) => '<div class="cf-print-pf-row '
      + (bon ? "ok" : "warn") + '"><span class="cf-print-c">' + esc(quoi)
      + '</span><span class="cf-print-m mono">' + esc(mesure)
      + '</span><span class="cf-print-v">' + (bon ? ICO("dz-etat-succes", 16) : "&#8212;")
      + '</span></div>';
    box.innerHTML = '<div class="cf-print-pf-sum"><b class="'
      + (a.pdfx ? "ok" : "") + '">' + (a.pdfx || dzT("cartes.print.al_sans_claim"))
      + '</b><span>' + a.bytes + ' ' + dzT("cartes.print.audit_octets") + '</span></div>'
      /* ── LES DEUX MESURES QUI JUGENT LES AUTRES, EN PREMIER ────────────
         Mesure du 12/08 : ajoutees en fin de boite, elles tombaient sous la
         ligne de flottaison (scrollHeight 450 px pour clientHeight 378 px) —
         exactement le defaut qu'on reprochait au controle avant vol
         (« annonce, pas montre »). La profondeur REELLE et le verdict ECRIT
         DANS LE FICHIER passent donc devant. */
      + (a.depth && a.depth["16"] && a.depth["16"].exact
        ? ligne(dzT("cartes.print.al_profondeur"),
          dzT("cartes.print.al_profondeur_v", { d8: a.depth["8"].distinct, u8: nfx(a.depth["8"].useful_bits, 2), d16: a.depth["16"].distinct, u16: nfx(a.depth["16"].useful_bits, 2) })
          + (a.depth["16"].lattice_257
            ? dzT("cartes.print.al_257")
            : dzT("cartes.print.al_vraies_16")),
          true)
        : "")
      + ligne(dzT("cartes.print.al_controle"), a.control
        ? (a.control.length > 150 ? a.control.slice(0, 150) + "…" : a.control)
        : dzT("cartes.print.al_sans_verdict"),
        !!a.control && !a.control_forced
        && a.control.indexOf("controle avant vol") === 0)
      /* ── LES MESURES D'IMPRIMEUR ENSUITE, ET SANS DEFILER ──────────────
         Le miroir recto-verso et le format de page sont ce qu'un atelier
         regarde en premier ; ils etaient les trois dernieres lignes d'une
         boite qui n'en montrait que huit. */
      + ligne(dzT("cartes.print.al_boites"), dzT("cartes.print.al_boites_v", { n: a.pages_4_boites, total: a.pages, emb: a.pages_boites_emboitees }), a.pages_4_boites === a.pages)
      + ligne("page", (a.media_pt
        ? fx(a.media_pt[2] - a.media_pt[0], 4) + " x "
          + fx(a.media_pt[3] - a.media_pt[1], 4) + " pt" : "?")
        + (a.iso_um >= 0 ? " · " + signedUm(a.iso_um_xy, a.iso_um)
          + dzT("cartes.print.du_nominal_fmt") : dzT("cartes.print.hors_table")),
        a.iso_um >= 0 && a.iso_um < 0.05)
      /* LA ROGNE, DEDUITE DES SEULS OCTETS : /TrimBox moins (n-1) pas de
         grille relus dans les matrices `cm` du flux. C'est la mesure qui
         repond a « la TrimBox declare 62,992 x 87,9687 mm, pas 63 x 88 ». */
      + ligne(dzT("cartes.print.al_rogne"), (a.trim_cell_mm && a.trim_cell_mm.length
        ? nfx(a.trim_cell_mm[0], 4) + " x " + nfx(a.trim_cell_mm[1], 4) + " mm"
          + (a.trim_fmt ? " · " + esc(a.trim_fmt) : "")
          + (a.trim_um_xy && a.trim_um_xy.length
            ? " · " + signedUm(a.trim_um_xy, 0) + dzT("cartes.print.du_nominal") : "")
        : dzT("cartes.print.al_trim_page")),
        !!(a.trim_um_xy && a.trim_um_xy.length
          && Math.abs(a.trim_um_xy[0]) < 0.05 && Math.abs(a.trim_um_xy[1]) < 0.05))
      /* LA DÉRIVE TOLÉRÉE, RELUE DANS LES OCTETS DU TÉMOIN — c'est le chiffre
         qui était AFFIRMÉ (2 mm, le fond perdu restant) là où le fichier en
         portait 0 : le trait de gouttière touchait la carte. */
      + ligne(dzT("cartes.print.derive"), a.mark_clearance_mm >= 0
        ? dzT("cartes.print.al_derive_v", { d: nfx(a.mark_clearance_mm, 2), n: a.marks_n, t: a.mark_touch })
        : dzT("cartes.print.al_sans_reperes"),
        a.mark_clearance_mm < 0 ? true : (a.mark_touch === 0 && a.mark_clearance_mm > 0))
      + ligne(dzT("cartes.print.al_miroir"), a.mirror_um >= 0
        ? nfx(a.mirror_um, 1) + dzT("cartes.print.al_miroir_v")
        : dzT("cartes.print.al_miroir_so"),
        a.mirror_um >= 0 ? a.mirror_um < 1 : true)
      + ligne(dzT("cartes.print.al_calques"), a.ocg_count
        ? a.ocg_count + " /OCG : " + a.ocg_names.join(" · ")
        : dzT("cartes.print.al_sans_ocp"), a.ocg_count > 0)
      + ligne(dzT("cartes.print.al_entete"), a.header, a.header >= "%PDF-1.4")
      + ligne(dzT("cartes.print.al_sous_type"), a.intent_subtype + (a.intent_version
        ? " · " + a.intent_version : dzT("cartes.print.al_sans_rev")), true)
      + ligne("condition", a.intent_id + (a.profile_bytes
        ? dzT("cartes.print.al_profil", { n: a.profile_bytes, cls: a.profile_class })
        : dzT("cartes.print.al_registre") + (a.intent_registry || "—")), true)
      + ligne("XMP", a.xmp_blocks + dzT("cartes.print.al_blocs") + (a.xmp_pdfx ? " · pdfxid" : ""),
        a.xmp_blocks > 0)
      + ligne("/Trapped", a.trapped || "absent", !!a.trapped)
      + ligne(dzT("cartes.print.al_polices"), a.font_hits + dzT("cartes.print.al_polices_v"),
        a.font_hits === 0)
      + ligne(dzT("cartes.print.al_etiquetage"), a.iccbased_hits + " /ICCBased · " + a.devicergb_hits
        + dzT("cartes.print.al_devicergb"), a.devicergb_hits === 0)
      + ligne(dzT("cartes.print.al_chiffrement"), a.encrypted ? dzT("cartes.print.oui") : dzT("cartes.print.al_aucun"), !a.encrypted)
      + (a.pdfx_manques.length
        ? '<div class="cf-print-pf-row err"><span class="cf-print-c">' + dzT("cartes.print.al_manques") + '</span>'
          + '<span class="cf-print-m">' + esc(a.pdfx_manques.join(" · "))
          + '</span><span class="cf-print-v">&#8212;</span></div>'
        : "");
  }

  function paintIcc() {
    const box = q('[data-role="icc"]');
    if (!box) return;
    if (!ICC) {
      box.innerHTML = '<div class="cf-print-iccl muted">' + dzT("cartes.print.icc_aucun") + '</div>';
      return;
    }
    /* tout ce qui est affiche ici est LU SUR LES OCTETS du profil par le
       backend (signature acsp, espace, canaux, tag desc) — jamais sur le nom
       du fichier. */
    box.innerHTML = '<div class="cf-print-iccl"><b>'
      + esc(ICC.desc || ICC.name || "profil.icc") + '</b>'
      + '<span>' + esc(ICC.space) + dzT("cartes.print.icc_info", { n: ICC.n, cls: esc(ICC.cls), octets: ICC.bytes }) + '</span></div>';
  }

  /* ── le plan, dessine ──────────────────────────────────────────────────── */
  function drawPlan() {
    const cv = q('[data-role="plan"]'), p = PLAN, g = CF.geom(), s = st();
    if (!cv || !p) return;
    const dup = s.duplex && !p.fail;
    const maxW = 264, maxH = 336;
    const cols = dup ? 2 : 1;
    const gapPx = 8;
    const sc = Math.min((maxW - (dup ? gapPx : 0)) / (p.sheet_px[0] * cols),
      maxH / p.sheet_px[1]);
    const dpr = Math.min(2, (typeof devicePixelRatio === "number" ? devicePixelRatio : 1) || 1);
    const wCss = Math.max(60, Math.round(p.sheet_px[0] * sc * cols + (dup ? gapPx : 0)));
    const hCss = Math.max(60, Math.round(p.sheet_px[1] * sc));
    cv.width = Math.round(wCss * dpr); cv.height = Math.round(hCss * dpr);
    cv.style.width = wCss + "px"; cv.style.height = hCss + "px";
    const ctx = cv.getContext("2d");
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    const ink = tone("--ink-strong", "#eee"), soft = tone("--ink-muted", "#888");
    const acc = tone("--accent", "#e8a33d");
    const one = 1 / (sc * dpr);

    const sides = dup ? ["front", "back"] : ["front"];
    sides.forEach((side, k) => {
      ctx.setTransform(sc * dpr, 0, 0, sc * dpr,
        k * (p.sheet_px[0] * sc + gapPx) * dpr, 0);
      /* le papier */
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, p.sheet_px[0], p.sheet_px[1]);
      ctx.lineWidth = one; ctx.strokeStyle = soft;
      ctx.strokeRect(one / 2, one / 2, p.sheet_px[0] - one, p.sheet_px[1] - one);
      if (p.fail) {
        ctx.fillStyle = "rgba(200,40,40,.85)";
        ctx.font = "600 " + (p.sheet_px[0] / 16) + "px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(dzT("cartes.print.ne_tient_pas"), p.sheet_px[0] / 2, p.sheet_px[1] / 2);
        return;
      }
      /* marge */
      if (p.margin_px > 0) {
        ctx.setLineDash([6 * one * 2, 5 * one * 2]);
        ctx.strokeStyle = "rgba(120,120,120,.7)"; ctx.lineWidth = one;
        ctx.strokeRect(p.margin_px, p.margin_px,
          p.sheet_px[0] - 2 * p.margin_px, p.sheet_px[1] - 2 * p.margin_px);
        ctx.setLineDash([]);
      }
      /* LE VERSO SE DESSINE OU LE FICHIER LE POSE : plan du cote, origine
         miroir comprise. Sans cela l'apercu montrerait le verso a une place
         que le PDF ne lui donne pas — exactement le divorce ecran/fichier que
         cette piece existe pour interdire. */
      const ps = sidePlan(p, s, side);
      const cells = [];
      for (let i = 0; i < p.per_page; i++) {
        let r = Math.floor(i / p.cols), c = i % p.cols;
        const n0 = i + 1;
        if (side === "back") { if (s.flip === "long") c = p.cols - 1 - c; else r = p.rows - 1 - r; }
        cells.push([r, c, n0]);
      }
      cells.forEach((cc) => {
        const r = cc[0], c = cc[1], rc = cellRect(ps, r, c);
        const kb = keepBleed(ps, g, r, c);
        ctx.fillStyle = "rgba(232,163,61,.20)";
        ctx.fillRect(rc[0] - kb[0], rc[1] - kb[1], rc[2] + kb[0] + kb[2], rc[3] + kb[1] + kb[3]);
        ctx.fillStyle = "rgba(120,120,120,.14)";
        ctx.fillRect(rc[0], rc[1], rc[2], rc[3]);
        ctx.strokeStyle = "rgba(40,40,40,.65)"; ctx.lineWidth = one;
        ctx.strokeRect(rc[0], rc[1], rc[2], rc[3]);
        /* zone sure : le troisieme cadre, celui que la barre n'a pas */
        const so = [g.safe_off_px[0] - g.bleed_off_px[0], g.safe_off_px[1] - g.bleed_off_px[1]];
        ctx.setLineDash([9 * one * 2, 6 * one * 2]);
        ctx.strokeStyle = "rgba(51,209,139,.9)";
        ctx.strokeRect(rc[0] + so[0], rc[1] + so[1], g.safe_px[0], g.safe_px[1]);
        ctx.setLineDash([]);
        ctx.fillStyle = "rgba(40,40,40,.55)";
        ctx.font = "600 " + Math.max(24, p.cell_px[0] / 6) + "px sans-serif";
        ctx.textAlign = "center"; ctx.textBaseline = "middle";
        ctx.fillText(String(cc[2]), rc[0] + rc[2] / 2, rc[1] + rc[3] / 2);
      });
      /* les repères, exactement ceux du fichier — de CE côté */
      const segs = markSegs(ps, s);
      if (segs.length) {
        ctx.strokeStyle = markShown(s);
        ctx.lineWidth = Math.max(one, mmpx(s.mark_w_mm, p.dpi));
        ctx.beginPath();
        segs.forEach((sg) => { ctx.moveTo(sg[0], sg[1]); ctx.lineTo(sg[2], sg[3]); });
        ctx.stroke();
      }
      /* poignées */
      if (k === 0 && s.sheet !== "card") {
        const hs = 9 / sc;
        ctx.fillStyle = acc;
        ctx.fillRect(p.margin_px - hs / 2, p.sheet_px[1] / 2 - hs / 2, hs, hs);
        if (p.cols > 1) {
          const gx = cellRect(p, 0, 0)[0] + p.cell_px[0] + p.gutter_px / 2;
          ctx.fillRect(gx - hs / 2, p.sheet_px[1] * 0.22 - hs / 2, hs, hs);
        }
      }
      if (dup) {
        ctx.fillStyle = ink;
        ctx.font = "600 " + (p.sheet_px[0] / 22) + "px sans-serif";
        ctx.textAlign = "left"; ctx.textBaseline = "top";
        ctx.fillText(side === "front" ? dzT("cartes.print.cv_recto") : dzT("cartes.print.cv_verso"),
          p.margin_px || 10, (p.margin_px || 10) * 0.25);
      }
    });
    ctx.setTransform(1, 0, 0, 1, 0, 0);
  }

  /* ── glisser sur le plan : marge et gouttière ──────────────────────────── */
  function wirePlanDrag() {
    const cv = q('[data-role="plan"]');
    if (!cv) return;
    const toSheet = (ev) => {
      const b = cv.getBoundingClientRect(), p = PLAN;
      if (!p) return null;
      const sc = b.width / (p.sheet_px[0] * (st().duplex ? 2 : 1) + (st().duplex ? 8 : 0));
      return [(ev.clientX - b.left) / sc, (ev.clientY - b.top) / sc];
    };
    const hit = (pt) => {
      const p = PLAN, s = st();
      if (!p || p.fail || !pt || s.sheet === "card") return null;
      const tol = 14 * (p.sheet_px[0] / cv.getBoundingClientRect().width);
      if (Math.abs(pt[0] - p.margin_px) < tol) return "margin";
      if (p.cols > 1) {
        const gx = cellRect(p, 0, 0)[0] + p.cell_px[0] + p.gutter_px / 2;
        if (Math.abs(pt[0] - gx) < tol) return "gutter";
      }
      return null;
    };
    cv.addEventListener("pointermove", (ev) => {
      if (!drag) { cv.style.cursor = hit(toSheet(ev)) ? "ew-resize" : "crosshair"; return; }
      const pt = toSheet(ev);
      if (!pt) return;
      const p = PLAN;
      if (drag === "margin") {
        drag_mm = Math.max(0, Math.min(60, Math.round(pt[0] / p.dpi * 25.4 * 2) / 2));
        preview({ margin_mm: drag_mm });
      } else {
        const left = cellRect(p, 0, 0)[0] + p.cell_px[0];
        drag_mm = Math.max(0, Math.min(40, Math.round((pt[0] - left) * 2 / p.dpi * 25.4 * 2) / 2));
        preview({ gutter_mm: drag_mm });
      }
    });
    cv.addEventListener("pointerdown", (ev) => {
      const h = hit(toSheet(ev));
      if (!h) return;
      drag = h; drag_mm = null;
      cv.setPointerCapture(ev.pointerId);
      ev.preventDefault();
    });
    const stop = () => {
      if (!drag) return;
      const k = drag === "margin" ? "margin_mm" : "gutter_mm";
      drag = null;
      if (drag_mm != null) { const o = {}; o[k] = drag_mm; set(o); }
      OVER = null;
      refresh();
    };
    cv.addEventListener("pointerup", stop);
    cv.addEventListener("pointercancel", stop);
    cv.addEventListener("pointerleave", () => { if (drag) stop(); });
  }
  let drag_mm = null, OVER = null;
  function preview(partial) {      /* pendant le glisser : on ne patche pas a
                                      chaque frame, on dessine. */
    OVER = partial;
    refresh(true);
  }

  /* ══ recalcul + verification backend ═════════════════════════════════════ */
  function currentState() {
    const s = st();
    if (OVER) Object.keys(OVER).forEach((k) => { s[k] = OVER[k]; });
    return s;
  }
  function refresh(light) {
    const s = currentState();
    PLAN = layoutOf(s, CF.geom(), CF.cards().length);
    drawPlan();
    paintRead();
    if (!light) scheduleVerify();
  }
  function scheduleVerify() {
    clearTimeout(vtimer);
    vtimer = setTimeout(() => { verify().catch(() => { }); }, 320);
  }
  async function verify() {
    const g = CF.geom();
    let r;
    try {
      r = await M.api.post("layout", specNow({ n_cards: CF.cards().length }));
    } catch (e) {
      VERIFY = { cls: "", txt: e && e.missing ? dzT("cartes.print.hors_ligne") : dzT("cartes.print.plan_non_verifie") };
      BPLAN = null; paintRead(); return;
    }
    BPLAN = r && r.plan;
    if (!BPLAN || !PLAN) return;
    const bad = [];
    [["cols"], ["rows"], ["per_page"], ["pages"], ["sheet_px"], ["cell_px"]].forEach((k) => {
      if (JSON.stringify(PLAN[k[0]]) !== JSON.stringify(BPLAN[k[0]]))
        bad.push(k[0] + dzT("cartes.print.ecran_egal") + JSON.stringify(PLAN[k[0]]) + " backend=" + JSON.stringify(BPLAN[k[0]]));
    });
    [["gutter_px"], ["margin_px"]].forEach((k) => {
      if (Math.abs(PLAN[k[0]] - BPLAN[k[0]]) > 0.001)
        bad.push(k[0] + dzT("cartes.print.ecran_egal") + PLAN[k[0]] + " backend=" + BPLAN[k[0]]);
    });
    for (let i = 0; i < 2; i++) {
      if (Math.abs(PLAN.origin_px[i] - BPLAN.origin_px[i]) > 0.001)
        bad.push("origin_px[" + i + "]" + dzT("cartes.print.ecran_egal") + PLAN.origin_px[i] + " backend=" + BPLAN.origin_px[i]);
    }
    /* LE MIROIR ET LA PAGE SONT DES CHIFFRES AFFICHES : ils sont donc
       confrontes comme le reste. Un ecart ici veut dire que l'ecran promet un
       repérage recto-verso ou un format de page que le fichier n'aura pas. */
    if (typeof BPLAN.mirror_um === "number"
      && Math.abs((PLAN.mirror_um || 0) - BPLAN.mirror_um) > 0.15) {
      bad.push("mirror_um" + dzT("cartes.print.ecran_egal") + PLAN.mirror_um + " backend=" + BPLAN.mirror_um);
    }
    /* LE COMPTE DE TRAITS ET LA DERIVE TOLEREE SONT DES CHIFFRES AFFICHES :
       ils sont donc confrontes comme le reste. Sans cela, l'ecran pouvait
       annoncer 34 traits et un retrait d'un millimetre pendant que le fichier
       en portait d'autres — c'est exactement le defaut que cette piece a paye. */
    const sNow = currentState();
    const nLoc = markSegs(PLAN, sNow).length;
    if (typeof BPLAN.marks_n === "number" && nLoc !== BPLAN.marks_n) {
      bad.push("marks_n" + dzT("cartes.print.ecran_egal") + nLoc + " backend=" + BPLAN.marks_n);
    }
    if (typeof BPLAN.mark_clearance_mm === "number" && BPLAN.mark_clearance_mm >= 0) {
      const cLoc = markClearance(PLAN, sNow) / PLAN.dpi * 25.4;
      if (Math.abs(cLoc - BPLAN.mark_clearance_mm) > 0.006) {
        bad.push("mark_clearance_mm" + dzT("cartes.print.ecran_egal") + cLoc.toFixed(4)
          + " backend=" + BPLAN.mark_clearance_mm);
      }
    }
    if (typeof BPLAN.mark_touch === "number"
      && markTouch(PLAN, sNow) !== BPLAN.mark_touch) {
      bad.push("mark_touch" + dzT("cartes.print.ecran_egal") + markTouch(PLAN, sNow) + " backend=" + BPLAN.mark_touch);
    }
    if (BPLAN.page_pt && PLAN.page_pt
      && (Math.abs(PLAN.page_pt[0] - BPLAN.page_pt[0]) > 0.001
        || Math.abs(PLAN.page_pt[1] - BPLAN.page_pt[1]) > 0.001)) {
      bad.push("page_pt" + dzT("cartes.print.ecran_egal") + JSON.stringify(PLAN.page_pt)
        + " backend=" + JSON.stringify(BPLAN.page_pt));
    }
    /* LA ROGNE ET LA ZONE SURE ECRITES SONT AFFICHEES : elles sont donc
       confrontees, au micron. C'est la regle de la piece — l'ecran calcule,
       le backend mesure, et un ecart devient une alarme visible au lieu d'un
       chiffre qu'on croit. */
    [["trim_mm_written", 0.0005], ["safe_mm_written", 0.0005],
      ["safe_inset_mm", 0.0005], ["iso_um_xy", 0.15], ["safe_um_xy", 0.15],
      ["trim_um_xy", 0.15]].forEach((k) => {
      const a = PLAN[k[0]], b = BPLAN[k[0]];
      if (!a || !b || a.length !== b.length) return;
      for (let i = 0; i < a.length; i++) {
        if (Math.abs(a[i] - b[i]) > k[1]) {
          bad.push(k[0] + dzT("cartes.print.ecran_egal") + JSON.stringify(a) + " backend=" + JSON.stringify(b));
          return;
        }
      }
    });
    if (bad.length) {
      VERIFY = { cls: "ko", txt: dzT("cartes.print.plan_divergent", { d: bad[0] }) };
      console.error("cardforge/print: PLAN DIVERGENT", bad);
    } else {
      VERIFY = { cls: "ok", txt: dzT("cartes.print.plan_verifie", { w: BPLAN.sheet_px[0], h: BPLAN.sheet_px[1], g: fx(BPLAN.gutter_pt, 2).replace(".", ","), toile: g.canvas_px.join("x") })
        + (BPLAN.duplex ? dzT("cartes.print.plan_verifie_miroir", { um: nfx(BPLAN.mirror_um, 1) }) : "") };
    }
    paintRead();
  }

  /* ══ contrôle avant vol ══════════════════════════════════════════════════ */
  function artSize(fname) {
    if (!fname) return Promise.resolve(null);
    if (ARTS.has(fname)) return Promise.resolve(ARTS.get(fname));
    return new Promise((res) => {
      const im = new Image();
      let done = false;
      const end = (v) => { if (done) return; done = true; ARTS.set(fname, v); res(v); };
      im.onload = () => end({ w: im.naturalWidth, h: im.naturalHeight });
      im.onerror = () => end(null);
      setTimeout(() => end(null), 6000);
      im.src = CF.imageURL(fname);
    });
  }
  function cardName(c) {
    const f = c.fields || {};
    return String(f.title || f.name || f.nom || c.id || ("carte " + (c.i + 1)));
  }

  /* ══ CE QUE LE FICHIER IMPORTE PORTE ET QU'AUCUN BLOC N'IMPRIME ══════════
     LE MANQUE QUE LES DEUX CONTROLES ONT NOMME : « le controle avant tirage
     n'audite que la FEUILLE, jamais le CONTENU des cartes — et c'est par ce
     trou que passe sa faute la plus grave : les 12 cartes portent le bandeau
     RARE alors que le CSV declare commune x5 [...] Rien ne le signale. »

     Couplage P4 -> P7, en LECTURE et tolerant a l'absence (spec 2.3) :
     doc.data.{columns, rows, map, qty_col}. Une colonne du fichier importe
     qui n'est mappee sur AUCUN bloc voyage avec la carte — filtree, triee,
     dupliquee par les quantites — et sort du tirage sans un mot. On envoie
     donc au controle, POUR CHAQUE CARTE, la valeur exacte de ces colonnes :
     c'est ce qui permet de nommer la carte ET de citer la valeur, la forme
     que le critere 11 exige.

     `card.row` est l'index de la ligne source, ecrit par P4 (data.py:1333) :
     c'est lui qui relie une carte dupliquee a sa ligne du CSV. */
  function orphanCols() {
    const d = CF.get("data", {}) || {};
    const cols = Array.isArray(d.columns) ? d.columns.map(String) : [];
    if (!cols.length) return null;
    const map = (d.map && typeof d.map === "object" && !Array.isArray(d.map)) ? d.map : {};
    const qty = (typeof d.qty_col === "string") ? d.qty_col : null;
    const idx = [];
    cols.forEach((c, j) => {
      if (c === qty || map[c]) return;     /* quantite ou bloc : elle sert */
      idx.push([j, c]);
    });
    if (!idx.length) return null;
    return { rows: Array.isArray(d.rows) ? d.rows : [], idx: idx };
  }
  function orphansOf(oc, card) {
    if (!oc) return null;
    const r = Number(card && card.row);
    if (!isFinite(r) || r < 0 || r >= oc.rows.length) return null;
    const row = oc.rows[r] || [];
    const out = {};
    let n = 0;
    oc.idx.forEach((p) => {
      const v = String(row[p[0]] == null ? "" : row[p[0]]).trim();
      if (v) { out[p[1]] = v; n++; }
    });
    return n ? out : null;
  }
  let pftimer = null;
  function schedulePreflight() {
    clearTimeout(pftimer);
    pftimer = setTimeout(() => { preflight().catch(() => { }); }, 420);
  }
  async function preflight() {
    if (PFBUSY) return;
    PFBUSY = true;
    const box = q('[data-role="pf"]');
    if (box) box.innerHTML = '<div class="cf-print-pf-ok">' + dzT("cartes.print.pf_en_cours") + '</div>';
    try {
      const cards = CF.cards();
      /* COUPLAGE EN LECTURE, ET TOLERANT A L'ABSENCE (spec 2.3) :
         - doc.type.slots[] : les boites de texte, en mm depuis le coin de rogne ;
         - doc.face.eff_dpi : le DPI EFFECTIF que la piece 01 a MESURE sur
           l'illustration posee (-1 = vectoriel, donc jamais sous-defini). On le
           prefere a notre propre calcul : elle, elle connait le recadrage,
           l'echelle et la rotation. Il ne vaut que pour les cartes qui n'ont
           pas leur PROPRE illustration.
         Sans les pieces 01 et 03, tout cela vaut null et le controle se
         rabat sur la taille naturelle du fichier. */
      const propre = (c) => c.art || (c.fields && c.fields.art) || null;
      const arts = await Promise.all(cards.map((c) =>
        artSize(propre(c) || CF.get("face.default_art", null))));
      const eff = Number(CF.get("face.eff_dpi", 0) || 0);
      const src = CF.get("face.src", null);
      /* LE PLAN VOYAGE AVEC LA DEMANDE : sans lui, les regles de FICHIER
         (intention de sortie, compression, gouttiere) seraient controlees sur
         le document sauvegarde — or l'autosave du CORE est differee de
         900 ms, donc sur l'ETAT D'AVANT. */
      const oc = orphanCols();
      const body = specNow({
        slots: CF.get("type.slots", []) || [],
        min_dpi: st().min_dpi,
        n_cards: cards.length,
        cards: cards.map((c, i) => ({
          i: c.i, name: cardName(c), fields: c.fields || {}, art: arts[i],
          has_art: !!(propre(c) || arts[i] || src || eff),
          eff_dpi: propre(c) ? 0 : eff,
          /* les colonnes importees qu'aucun bloc n'imprime, AVEC leur valeur
             pour CETTE carte (contrat P4 -> P7, absent = rien a dire) */
          orphans: orphansOf(oc, c),
        })),
      });
      /* LE MEME CORPS PART AVEC L'EXPORT : la porte de la route contrôle
         EXACTEMENT ce que l'écran a montré, pas une version appauvrie. */
      PFBODY = { slots: body.slots, cards: body.cards, min_dpi: body.min_dpi };
      PF = await M.api.post("preflight", body);
    } catch (e) {
      PF = { rows: [], errors: 0, warnings: 0, offline: true,
        message: String((e && e.message) || e) };
    } finally { PFBUSY = false; }
    paintPreflight();
  }
  function paintPreflight() {
    const box = q('[data-role="pf"]');
    if (!box) return;
    if (!PF) {
      box.innerHTML = '<div class="cf-print-pf-ok muted">' + dzT("cartes.print.pf_aucun", { n: CF.cards().length }) + '</div>';
      return;
    }
    if (PF.offline) {
      box.innerHTML = '<div class="cf-print-pf-ok ko">' + esc(PF.message) + '</div>';
      return;
    }
    if (!PF.rows.length) {
      box.innerHTML = '<div class="cf-print-pf-ok">' + ICO("dz-etat-succes", 16, "cf-ic") + dzT("cartes.print.pf_rien", { n: PF.checked ? PF.checked.cards : 0, s: PF.checked ? PF.checked.slots : 0, zs: (PF.safe_px || []).join(" x ") }) + '</div>';
      return;
    }
    const tete = '<div class="cf-print-pf-sum">'
      + '<b class="' + (PF.errors ? "ko" : "ok") + '">' + dzT("cartes.print.pf_erreurs", { n: PF.errors }) + '</b>'
      + '<span>' + dzT("cartes.print.pf_avert", { n: PF.warnings }) + '</span>'
      + '<span class="ok">' + dzT("cartes.print.pf_tenues", { n: PF.passed || 0 }) + '</span>'
      + '<span>' + dzT("cartes.print.pf_compte", { n: (PF.checked && PF.checked.cards) || 0, l: (PF.checked && PF.checked.rules) || PF.rows.length }) + '</span></div>';
    box.innerHTML = tete
      + PF.rows.slice(0, 200).map((r) => '<div class="cf-print-pf-row ' + r.level + '">'
        + '<span class="cf-print-c">' + esc(r.card) + '</span>'
        + '<span class="cf-print-m">' + esc(r.message) + '</span>'
        + '<span class="cf-print-v">' + (r.kind === "image_sous_definie" ? r.value + " DPI"
          : r.kind === "texte_hors_zone_sure" ? "+" + r.value + " px"
            : r.kind === "colonne_non_imprimee" ? esc(r.slot)
              : r.kind === "champ_sans_bloc" ? esc(r.slot)
                : r.kind === "bloc_vide" ? r.value + "/" + r.limit
                  : r.level === "ok" ? ICO("dz-etat-succes", 16) : "&#8212;") + '</span></div>').join("")
      + (PF.rows.length > 200 ? '<div class="cf-print-pf-ok muted">' + dzT("cartes.print.pf_autres", { n: PF.rows.length - 200 }) + '</div>' : "");
  }

  /* ══ profil ICC de sortie ════════════════════════════════════════════════
     Depose UNE fois sur le jeu, relu par /layout, /sheet et /pdf : le plan
     affiche est donc calcule avec le profil qui sera reellement embarque.
     Les chiffres montres (espace, canaux, octets) sont lus SUR LES OCTETS du
     fichier par le backend, jamais sur son nom. ════════════════════════════ */
  async function loadIcc() {
    try {
      const r = await M.api.get("icc");
      ICC = (r && r.icc) || null;
    } catch (e) { ICC = null; }
    paintIcc();
  }
  async function sendIcc(file) {
    const fd = new FormData();
    fd.append("file", file, file.name || "profil.icc");
    try {
      CF.busy(true, dzT("cartes.print.lecture_icc"));
      const r = await M.api.post("icc", fd);
      ICC = (r && r.icc) || null;
      CF.toast(dzT("cartes.print.icc_charge", { d: ICC ? dzT("cartes.print.icc_charge_d", { esp: ICC.space, n: ICC.bytes }) : "" }));
      if (ICC && ICC.space === "CMYK" && st().intent !== "icc") set({ intent: "icc" });
    } catch (e) {
      CF.toast(String((e && e.message) || e), true);
    } finally { CF.busy(false); paintIcc(); refresh(); paintGabarits(); }
  }
  async function delIcc() {
    try { await M.api.del("icc"); } catch (e) { /* deja absent */ }
    ICC = null;
    if (st().intent === "icc") set({ intent: "srgb" });
    if (st().color === "cmyk_icc") set({ color: gabCourant() === "dtc" ? "cmyk_device" : "rgb" });
    paintIcc(); refresh(); paintGabarits();
  }

  /* ══ exports ═════════════════════════════════════════════════════════════ */
  function logLine(name, bytes, note) {
    LOG.unshift({ name: name, bytes: bytes, note: note, t: new Date() });
    if (LOG.length > 12) LOG.pop();
    const l = q('[data-role="log"]');
    if (l) {
      l.innerHTML = LOG.map((x) => '<div class="cf-print-log-l"><b>' + esc(x.name) + '</b>'
        + '<span>' + esc(x.note || "") + '</span><span>' + ko(x.bytes) + '</span></div>').join("");
    }
  }
  function deckSlug() {
    return String(CF.doc().name || "jeu").replace(/[^\w\-]+/g, "_").slice(0, 40) || "jeu";
  }
  async function renderAll(withBacks, limit) {
    const n = limit || CF.cards().length;
    const fronts = [], backs = [];
    const t0 = (typeof performance !== "undefined" ? performance.now() : Date.now());
    for (let i = 0; i < n; i++) {
      CF.busy(true, dzT("cartes.print.busy_rendu", { i: i + 1, n: n, px: CF.geom().canvas_px.join(" x ") }));
      const k = limit ? 0 : i;
      fronts.push(await CF.cardBlob(k, { face: "front" }));
      if (withBacks) backs.push(await CF.cardBlob(k, { face: "back" }));
    }
    const t1 = (typeof performance !== "undefined" ? performance.now() : Date.now());
    return { fronts: fronts, backs: backs, ms: t1 - t0 };
  }
  function formData(spec, fronts, backs) {
    const fd = new FormData();
    fd.append("spec", JSON.stringify(spec));
    fronts.forEach((b, i) => fd.append("fronts", b, "f" + (i + 1) + ".png"));
    (backs || []).forEach((b, i) => fd.append("backs", b, "b" + (i + 1) + ".png"));
    return fd;
  }
  /* LA GEOMETRIE VOYAGE AVEC LA DEMANDE, toujours. Le backend saurait la
     relire dans meta.json, mais l'autosave du CORE est differee de 900 ms :
     changer de definition puis exporter dans la seconde faisait imposer
     l'ANCIEN format — le backend refusait les bitmaps (« la carte mesure
     1650x2250, la geometrie impose 825x1125 ») et le plan s'annoncait
     divergent alors qu'aucune formule ne divergeait. Mesure du 11/08. */
  function specNow(extra) {
    const g = CF.geom(), f = CF.doc().format;
    return Object.assign({}, currentState(), {
      fmt: f.fmt, dpi: g.dpi, bleed_mm: f.bleed_mm, safe_mm: f.safe_mm,
      corner_mm: f.corner_mm,
    }, extra || {});
  }
  /* LE CORPS D'UN EXPORT porte le controle avant vol AVEC lui : la route
     re-mesure et refuse en 409 si des erreurs subsistent, sauf `force`
     explicite. Un client qui saute cet ecran rencontre la meme porte. */
  function exportSpec(extra) {
    return specNow(Object.assign({}, PFBODY || {},
      { force: !!FORCE }, extra || {}));
  }

  /* ══ LA PORTE ════════════════════════════════════════════════════════════
     « Le controle avant vol DETECTE parfaitement mais ne REFUSE rien : avec
     6 erreurs rouges a l'ecran, le PDF part quand meme, sans confirmation. »
     Un controle qui ne refuse rien ne controle rien — c'est un commentaire.

     La porte est ICI *et* dans la route (409 sans `force`) : un client qui
     saute l'interface la rencontre aussi. Elle ne cede qu'a un OUI explicite,
     et le journal garde la trace du passage en force. */
  async function gate(quoi) {
    /* on RE-MESURE avant de laisser partir : PF peut dater d'avant le dernier
       reglage, et un fichier part chez l'imprimeur, pas dans un cache. */
    await preflight();
    const n = (PF && !PF.offline) ? (PF.errors || 0) : 0;
    if (!n) return true;
    const lignes = PF.rows.filter((r) => r.level === "err").slice(0, 6)
      .map((r) => "  · " + r.card + " — " + r.message).join("\n");
    const ok = await window.__dzDialogue.confirmer(
      dzT("cartes.print.gate_titre", { n: n }) + "\n\n" + lignes
      + (n > 6 ? "\n  " + dzT("cartes.print.gate_autres", { n: n - 6 }) : "")
      + "\n\n" + dzT("cartes.print.gate_defauts") + "\n"
      + dzT("cartes.print.gate_question", { quoi: quoi }));
    if (!ok) {
      CF.toast(dzT("cartes.print.gate_refuse", { n: n }), true);
      return false;
    }
    FORCE = true;
    return true;
  }

  async function exportCard(all) {
    const s = currentState();
    if (!(await gate(dzT("cartes.print.quoi_cartes")))) return;
    try {
      const idx = all ? null : CF.current();
      const list = all ? CF.cards().map((c) => c.i) : [idx];
      for (let k = 0; k < list.length; k++) {
        CF.busy(true, dzT("cartes.print.busy_carte", { k: k + 1, n: list.length }));
        const blob = await CF.cardBlob(list[k], { face: "front" });
        const fd = new FormData();
        fd.append("spec", JSON.stringify(exportSpec({})));
        fd.append("file", blob, "carte.png");
        let out, name;
        try {
          out = await M.api.blob("POST", "card", fd);
          name = deckSlug() + "_" + (list[k] + 1) + "." + (s.card_fmt === "jpeg" ? "jpg" : "png");
        } catch (e) {
          if (!(e && e.missing)) throw e;
          out = blob; name = deckSlug() + "_" + (list[k] + 1) + ".png";
          CF.toast(dzT("cartes.print.backend_absent"), true);
        }
        CF.download(out, name);
        logLine(name, out.size, CF.geom().canvas_px.join(" x ") + " px · "
          + (s.card_fmt === "jpeg" ? "JPEG q" + s.jpeg_quality : "PNG " + s.card_bits + " bits"));
      }
      CF.toast(dzT("cartes.print.toast_cartes", { n: list.length, px: CF.geom().canvas_px.join(" x ") }));
    } catch (e) { CF.toast(String((e && e.message) || e), true); }
    finally { CF.busy(false); FORCE = false; }
  }

  /* LE REPLI RASTER, TELECHARGE. Pas de porte de controle avant vol ici : ce
     fichier ne contient AUCUNE carte — c'est une plaque derivee du seul cadre,
     et la refuser parce qu'une illustration est sous-definie n'aurait aucun
     sens. Les deux refus qui le concernent (pas de portee impression, pas
     d'anneau) sont dits par le bloc ci-dessus AVANT le clic, et le bouton est
     desactive dans ces cas-la. */
  async function exportFoilMask() {
    try {
      CF.busy(true, dzT("cartes.print.busy_foil"));
      const out = await M.api.blob("GET", "foil-mask?dpi=" + FOILDPI);
      const name = deckSlug() + "_masque-foil_" + FOILDPI + "dpi_noir.png";
      CF.download(out, name);
      const f = (BPLAN && BPLAN.foil) || null;
      logLine(name, out.size, dzT("cartes.print.log_foil", { dpi: FOILDPI })
        + (f ? dzT("cartes.print.log_foil_anneau", { w: nfx(f.width_mm, 2), e: nfx(f.edge_mm, 2) }) : ""));
      CF.toast(dzT("cartes.print.toast_foil"));
    } catch (e) {
      const m = String((e && e.message) || e);
      CF.toast(/\b409\b/.test(m)
        ? dzT("cartes.print.foil_409") : m, true);
    } finally { CF.busy(false); }
  }

  /* LA MIRE (tache #85) : mirror_um mesure le FICHIER, la mire la MACHINE. A la
     taille de la feuille choisie (A4 si « 1 carte / page »). */
  let MIREV = false;
  async function exportMire() {
    if (MIREV) return;
    MIREV = true;
    const s = st().sheet === "card" ? "a4" : st().sheet;
    try {
      CF.busy(true, dzT("cartes.print.busy_mire"));
      const out = await M.api.blob("GET", "mire?sheet=" + encodeURIComponent(s));
      const name = "mire_recto_verso_" + s + ".pdf";
      CF.download(out, name);
      logLine(name, out.size, dzT("cartes.print.log_mire"));
      CF.toast(dzT("cartes.print.toast_mire", { s: s.toUpperCase() }));
    } catch (e) { CF.toast(dzT("cartes.print.err_mire", { e: String((e && e.message) || e) }), true); }
    finally { CF.busy(false); MIREV = false; }
  }

  async function exportSheet() {
    if (!(await gate(dzT("cartes.print.quoi_planche")))) return;
    try {
      const r = await renderAll(false);
      CF.busy(true, dzT("cartes.print.busy_planche"));
      const fd = formData(exportSpec({ page: 0, side: "front" }), r.fronts, []);
      const out = await M.api.blob("POST", "sheet", fd);
      const name = deckSlug() + "_planche_1.png";
      CF.download(out, name);
      logLine(name, out.size, (PLAN ? PLAN.sheet_px.join(" x ") + " px · "
        + PLAN.cols + "x" + PLAN.rows : ""));
      CF.toast(dzT("cartes.print.toast_planche", { px: PLAN ? PLAN.sheet_px.join(" x ") : "?" })
        + (PLAN && PLAN.pages > 1 ? dzT("cartes.print.toast_planche_pages", { n: PLAN.pages }) : ""));
    } catch (e) { CF.toast(String((e && e.message) || e), true); }
    finally { CF.busy(false); FORCE = false; }
  }

  async function exportPdf(limit) {
    const s = currentState();
    if (!(await gate(limit ? dzT("cartes.print.quoi_banc") : dzT("cartes.print.quoi_pdf")))) return;
    const t0 = (typeof performance !== "undefined" ? performance.now() : Date.now());
    try {
      const r = await renderAll(!!s.duplex, limit);
      CF.busy(true, dzT("cartes.print.busy_pdf"));
      const fd = formData(exportSpec({}), r.fronts, r.backs);
      const out = await M.api.blob("POST", "pdf", fd);
      const t1 = (typeof performance !== "undefined" ? performance.now() : Date.now());
      const name = deckSlug() + "_planches.pdf";
      CF.download(out, name);
      /* le compte de pages se calcule sur les cartes REELLEMENT envoyees, pas
         sur PLAN : le banc d'essai en envoie 60 alors que le jeu n'en a
         qu'une, et le journal annoncait « 1 page » pour un PDF de 10. */
      const pages = PLAN && PLAN.per_page
        ? Math.ceil(r.fronts.length / PLAN.per_page) * (s.duplex ? 2 : 1) : 0;
      const note = dzT("cartes.print.log_pdf", { n: r.fronts.length, p: pages })
        + (PLAN ? " · " + PLAN.cols + "x" + PLAN.rows + dzT("cartes.print.log_gouttiere")
          + fx(PLAN.gutter_pt, 2).replace(".", ",") + " pt" : "")
        + dzT("cartes.print.log_temps", { r: (r.ms / 1000).toFixed(1).replace(".", ","), t: ((t1 - t0) / 1000).toFixed(1).replace(".", ",") })
        /* le passage en force LAISSE UNE TRACE : « exporte malgre 6 erreurs »
           n'est pas la meme phrase que « exporte ». */
        + (FORCE ? dzT("cartes.print.log_force", { n: (PF && PF.errors) || 0 }) : "");
      logLine(name, out.size, note);
      CF.toast(dzT("cartes.print.toast_pdf", { n: r.fronts.length, t: ((t1 - t0) / 1000).toFixed(1).replace(".", ",") }));
    } catch (e) { CF.toast(String((e && e.message) || e), true); }
    finally { CF.busy(false); FORCE = false; }
  }
  /* ══ GABARITS D'IMPRIMEUR (tache #83, plan-cartes T4, 04/10/2026) ═════════
     Le catalogue vient du backend (GET gabarits) : cet ecran ne DERIVE aucun
     pixel. Les chiffres affiches sont ceux de `contract.profile_geom`.

     DECISION DE L'UTILISATEUR (04/10) : choisir MPC / TGC / DTC regle le
     format du jeu (fond perdu, zone sure, DPI) et les reglages d'impression
     que le gabarit impose (planche « card », sans traits ni cartouche, CMJN
     pour DTC) — pour que le moteur rende aux pixels de l'imprimeur. Ce qu'il
     y avait AVANT est retenu dans `profile_avant` et revient tel quel quand
     on repasse a « maison ». ══════════════════════════════════════════════ */
  let GAB = [], GABFMT = "";
  const GAB_NOTE = {
    mpc: dzT("cartes.print.gab_mpc"),
    tgc: dzT("cartes.print.gab_tgc"),
    dtc: dzT("cartes.print.gab_dtc"),
    maison: dzT("cartes.print.gab_maison"),
  };
  /* Les reglages d'impression qu'un gabarit impose, et qu'il faut donc
     pouvoir rendre a l'identique en revenant a « maison ». */
  const GAB_CLES = ["sheet", "marks", "slug", "color", "layers", "intent"];
  function gabCourant() { return st().profile || "maison"; }
  function gabRow(id) { return GAB.filter((x) => x.id === id)[0] || null; }
  /* L'ECART, DIT A L'ECRAN. Le fichier part quand meme — aux bonnes
     dimensions — mais il ne promet pas ce qu'il ne tient pas. */
  function ecartPdfx(g) {
    if (!g || g.pdfx !== "PDF/X-1a:2001") return "";
    if (ICC && ICC.space === "CMYK" && ICC.cls === "prtr") {
      return dzT("cartes.print.ec_presse", { p: ICC.desc || ICC.name || dzT("cartes.print.profil_icc") });
    }
    return dzT("cartes.print.ec_device");
  }
  function paintGabarits() {
    const box = q('[data-role="gabs"]');
    if (!box) return;
    const cur = gabCourant();
    box.innerHTML = GAB.map((g) => {
      const on = g.id === cur, ko = !g.geom;
      const px = g.geom
        ? dzT("cartes.print.gab_px", { w: g.geom.canvas_px[0], h: g.geom.canvas_px[1], fp: fx(g.geom.bleed_off_px[0], 1).replace(".", ","), zs: fx(g.geom.safe_off_px[0], 1).replace(".", ",") })
        : dzT("cartes.print.gab_ne_sert_pas", { fmt: GABFMT, servis: g.fmts.join(", ") });
      const titre = ko ? dzT("cartes.print.gab_titre_ko", { fmt: GABFMT })
        : dzT("cartes.print.gab_titre", { g: g.label }) + (g.verifie ? dzT("cartes.print.gab_verifie", { d: g.verifie }) : "");
      return '<button type="button" class="cf-print-gab' + (on ? " on" : "") + (ko ? " ko" : "")
        + '" data-act="profile" data-v="' + esc(g.id) + '" title="' + esc(titre) + '"'
        + (ko ? " disabled" : "") + '>'
        + '<b>' + esc(g.label) + '</b>'
        + '<i class="px">' + esc(px) + '</i>'
        + '<i class="note">' + esc(GAB_NOTE[g.id] || g.note) + '</i>'
        + (g.pdfx && g.id !== "maison" ? '<i class="pdfx">' + esc(g.pdfx) + '</i>' : "")
        + '</button>';
    }).join("");
    const g = gabRow(cur);
    const w = q('[data-role="gab-ecart"]');
    if (w) {
      const txt = (g && !g.geom)
        ? dzT("cartes.print.gab_ecart", { fmt: GABFMT, servis: g.fmts.join(", ") })
        : ecartPdfx(g);
      w.textContent = txt;
      w.classList.toggle("hidden", !txt);
    }
    const zip = !!(g && g.delivery === "png_zip");
    const bp = q('[data-act="pack"]');
    if (bp) bp.classList.toggle("hidden", !zip);
    qa('[data-act="pdf"], [data-act="png"], [data-act="bench"]').forEach((b) => {
      b.classList.toggle("hidden", zip);
    });
  }
  async function loadGabarits() {
    const fmt = CF.doc().format.fmt;
    try {
      const r = await M.api.get("gabarits?fmt=" + encodeURIComponent(fmt));
      if (r && Array.isArray(r.gabarits)) { GAB = r.gabarits; GABFMT = r.fmt || fmt; }
    } catch (e) {
      if (!(e && e.missing)) console.warn("cardforge/print: gabarits", e);
    }
    /* Un format change SOUS un gabarit ramene le fond perdu natif (regle du
       CORE) : on remet celui du gabarit, sinon le moteur rendrait a cote des
       pixels de l'imprimeur et le backend refuserait chaque carte. */
    const g = gabRow(gabCourant()), f = CF.doc().format;
    if (g && g.id !== "maison" && g.geom
        && (f.bleed_mm !== g.geom.bleed_mm || f.safe_mm !== g.geom.safe_mm || f.dpi !== g.geom.dpi)) {
      M.setFormat({ bleed_mm: g.geom.bleed_mm, safe_mm: g.geom.safe_mm, dpi: g.geom.dpi });
    }
    paintGabarits();
  }
  function choisirGabarit(id) {
    const g = gabRow(id), cur = gabCourant();
    if (!g || !g.geom || id === cur) return;
    const f = CF.doc().format, s = st();
    if (id === "maison") {
      let av = null;
      try { av = s.profile_avant ? JSON.parse(s.profile_avant) : null; } catch (e) { av = null; }
      const rendu = { profile: "maison", profile_avant: "" };
      if (av && av.print) GAB_CLES.forEach((k) => { if (k in av.print) rendu[k] = av.print[k]; });
      set(rendu);
      if (av && av.format) M.setFormat(av.format);
      CF.toast(dzT("cartes.print.toast_maison"));
    } else {
      const o = { profile: id };
      /* on ne retient l'« avant » qu'en QUITTANT maison : passer de MPC a TGC
         ne doit pas effacer ce qu'il faudra rendre. */
      if (cur === "maison") {
        const pr = {};
        GAB_CLES.forEach((k) => { pr[k] = s[k]; });
        o.profile_avant = JSON.stringify({
          format: { bleed_mm: f.bleed_mm, safe_mm: f.safe_mm, dpi: f.dpi }, print: pr });
      }
      o.sheet = g.sheet; o.marks = g.marks; o.slug = false;
      if (g.pdfx === "PDF/X-1a:2001") {
        o.layers = false;
        const presse = !!(ICC && ICC.space === "CMYK" && ICC.cls === "prtr");
        o.color = presse ? "cmyk_icc" : "cmyk_device";
        if (presse) o.intent = "icc";
      } else {
        o.color = g.color;
      }
      set(o);
      M.setFormat({ bleed_mm: g.geom.bleed_mm, safe_mm: g.geom.safe_mm, dpi: g.geom.dpi });
      CF.toast(dzT("cartes.print.toast_gab", { g: g.label, px: g.geom.canvas_px.join(" x ") }));
    }
    paintGabarits(); refresh(); schedulePreflight();
  }
  /* Le paquet : le navigateur rend, le backend nomme et archive. */
  async function exportPack() {
    const g = gabRow(gabCourant());
    if (!g || g.delivery !== "png_zip") return;
    if (!CF.cards().length) { CF.toast(dzT("cartes.print.aucune_carte_paquet"), true); return; }
    if (!(await gate(dzT("cartes.print.quoi_paquet", { g: g.label })))) return;
    try {
      const r = await renderAll(true);
      CF.busy(true, dzT("cartes.print.busy_paquet", { g: g.id.toUpperCase() }));
      const fd = formData(exportSpec({}), r.fronts, r.backs);
      const out = await M.api.blob("POST", "pack", fd);
      const name = deckSlug() + "_paquet_" + g.id + ".zip";
      CF.download(out, name);
      logLine(name, out.size, dzT("cartes.print.log_paquet", { n: r.fronts.length, px: g.geom.canvas_px.join(" x ") }));
      CF.toast(dzT("cartes.print.toast_paquet", { g: g.id.toUpperCase(), n: r.fronts.length, px: g.geom.canvas_px.join(" x ") }));
    } catch (e) { CF.toast(dzT("cartes.print.err_paquet", { e: String((e && e.message) || e) }), true); }
    finally { CF.busy(false); FORCE = false; }
  }

  /* ══ cablage ═════════════════════════════════════════════════════════════ */
  function wire() {
    HOST.addEventListener("click", (ev) => {
      const row = ev.target.closest("[data-fmt]");
      if (row) { M.setFormat({ fmt: row.dataset.fmt }); return; }
      const sb = ev.target.closest("[data-seg] .seg-b");
      if (sb) {
        const key = sb.closest("[data-seg]").dataset.seg, v = sb.dataset.v;
        /* HORS DOCUMENT : la definition du masque de foil n'est pas un reglage
           d'imposition, elle ne passe donc pas par `set()`. */
        if (key === "foil_dpi") { FOILDPI = Number(v); sync(); paintFoil(); return; }
        if (key === "dpi") M.setFormat({ dpi: Number(v) });
        else { const o = {}; o[key] = (key === "card_bits") ? Number(v) : v; set(o); }
        return;
      }
      const act = ev.target.closest("[data-act]");
      if (!act) return;
      const a = act.dataset.act;
      if (a === "png") exportSheet();
      else if (a === "pdf") exportPdf(0);
      else if (a === "card") exportCard(false);
      else if (a === "cards") exportCard(true);
      else if (a === "pf") preflight();
      else if (a === "bench") exportPdf(60);
      else if (a === "guides") toggleGuides();
      else if (a === "undo") undo();
      else if (a === "iccdel") delIcc();
      else if (a === "foilmask") exportFoilMask();
      else if (a === "audit") runAudit();
      else if (a === "mire") exportMire();
      else if (a === "profile") choisirGabarit(String(act.dataset.v));
      else if (a === "pack") exportPack();
    });
    HOST.addEventListener("change", (ev) => {
      const t = ev.target;
      if (t.dataset && t.dataset.sel === "intent") {
        set({ intent: String(t.value) });
        return;
      }
      if (t.id === "cf-print-iccfile") {
        const f = t.files && t.files[0];
        t.value = "";
        if (f) sendIcc(f);
        return;
      }
      if (t.dataset && t.dataset.num) {
        const k = t.dataset.num, v = Number(t.value);
        if (!isFinite(v)) { sync(); return; }
        try {
          if (k === "bleed_mm" || k === "safe_mm" || k === "corner_mm") {
            const o = {}; o[k] = v; M.setFormat(o);
          } else { const o = {}; o[k] = v; set(o); }
        } catch (e) { CF.toast(String((e && e.message) || e), true); sync(); }
      } else if (t.dataset && t.dataset.chk) {
        const o = {}; o[t.dataset.chk] = !!t.checked; set(o);
      } else if (t.dataset && t.dataset.color) {
        const o = {}; o[t.dataset.color] = String(t.value); set(o);
      }
    });
    HOST.addEventListener("keydown", (ev) => {
      const row = ev.target.closest && ev.target.closest("[data-fmt]");
      if (!row) return;
      if (ev.key !== "ArrowDown" && ev.key !== "ArrowUp") return;
      ev.preventDefault();
      const rows = qa("[data-fmt]"), i = rows.indexOf(row);
      const nx = rows[Math.max(0, Math.min(rows.length - 1, i + (ev.key === "ArrowDown" ? 1 : -1)))];
      if (nx) { M.setFormat({ fmt: nx.dataset.fmt }); setTimeout(() => {
        const again = qa("[data-fmt]")[rows.indexOf(nx)];
        if (again) again.focus();
      }, 0); }
    });
    wirePlanDrag();
    document.addEventListener("keydown", onKey);
  }

  function visible() {
    const p = HOST && HOST.closest(".cf-panel");
    return !!(p && p.classList.contains("on"));
  }
  function onKey(ev) {
    if (!visible()) return;
    const t = ev.target;
    const tag = t && t.tagName ? t.tagName.toLowerCase() : "";
    if (tag === "input" || tag === "textarea" || tag === "select") {
      if (!(ev.key.toLowerCase() === "z" && (ev.ctrlKey || ev.metaKey))) return;
    }
    const k = ev.key.toLowerCase();
    if ((ev.ctrlKey || ev.metaKey) && k === "z") { ev.preventDefault(); undo(); return; }
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (k === "r") { ev.preventDefault(); toggleGuides(); }
    else if (k === "p") { ev.preventDefault(); exportSheet(); }
    else if (k === "d") { ev.preventDefault(); exportPdf(0); }
    else if (k === "c") { ev.preventDefault(); exportCard(false); }
    else if (k === "v") { ev.preventDefault(); preflight(); }
  }

  /* Les reperes appartiennent au CORE (couche z=90) et sa scene porte deja le
     bouton : on ne duplique pas la couche, on actionne SON interrupteur — et
     on en refléte l'etat ici, pour que « masquable d'un clic » soit vrai
     depuis le panneau d'impression aussi. */
  function guidesBtn() { return document.getElementById("guidesBtn"); }
  function toggleGuides() {
    const b = guidesBtn();
    if (!b) { CF.toast(dzT("cartes.print.reperes_indispo"), true); return; }
    b.click();
    syncGuides();
  }
  function syncGuides() {
    const b = guidesBtn(), mine = q('[data-act="guides"]');
    if (!b || !mine) return;
    const on = b.classList.contains("active");
    mine.classList.toggle("strong", on);
    mine.innerHTML = ICO("dz-edit-reperes", 16, "cf-ic") + dzT("cartes.print.reperes") + (on ? "" : dzT("cartes.print.masques"));
  }

  function sync() {
    const s = currentState(), f = CF.doc().format, g = CF.geom();
    qa("[data-num]").forEach((i) => {
      const k = i.dataset.num;
      i.value = (k in f) ? f[k] : s[k];
    });
    qa("[data-px]").forEach((i) => {
      const k = i.dataset.px;
      const mm = (k in f) ? f[k] : s[k];
      i.textContent = "mm · " + nf(mmpx(mm, g.dpi), 1) + " px";
    });
    qa("[data-chk]").forEach((i) => { i.checked = !!s[i.dataset.chk]; });
    qa("[data-color]").forEach((i) => { i.value = s[i.dataset.color]; });
    qa("[data-sel]").forEach((i) => { i.value = s[i.dataset.sel]; });
    /* Le nuancier ne sert QU'EN RVB : en repérage ou en noir 100 %, l'encre
       est imposee par l'espace, et laisser un rouge vif cliquable ferait
       croire a un reglage qui n'a aucun effet sur le fichier. */
    const rvb = s.mark_space === "rgb";
    qa("[data-color]").forEach((i) => { i.disabled = !rvb; });
    const cl = q('[data-role="colorlbl"]');
    if (cl) {
      cl.textContent = rvb ? dzT("cartes.print.couleur_reperes")
        : dzT("cartes.print.couleur_inutilisee", { e: MARK_SPACE_LABEL[s.mark_space] });
    }
    qa("[data-seg]").forEach((sg) => {
      const k = sg.dataset.seg;
      const cur = (k === "dpi") ? g.dpi : (k === "foil_dpi") ? FOILDPI : s[k];
      sg.querySelectorAll(".seg-b").forEach((b) => {
        b.classList.toggle("active", String(b.dataset.v) === String(cur));
      });
    });
    syncGuides();
  }

  /* ══════════════════════════════════════════════════════════════════════════
     ENREGISTREMENT
     ══════════════════════════════════════════════════════════════════════════ */
  M = CF.register({
    id: "print",
    title: dzT("cartes.print.titre"),
    icon: "dz-nav-cf-impression",
    order: 7,

    /* Aucun z n'est alloue a cette piece : elle ne dessine pas la carte.
       Enregistrer un painter ici leve — c'est voulu. */
    painters: [],

    /* LE SCHEMA : ces cles sont les SEULES que M.patch({...}) acceptera. */
    state: Object.assign({}, DEFAULTS),

    async init(host) {
      HOST = host;
      shell();
      paintIntents();
      paintFormats();
      paintIcc();
      paintAudit();
      sync();
      wire();
      refresh();
      paintPreflight();
      /* le catalogue des planches, calcule par contract.sheet_px — l'ecran ne
         derive aucun pixel de planche tant que le backend repond. */
      try {
        const r = await M.api.get("sheets");
        if (r && Array.isArray(r.sheets)) { CAT = r; SHEETS = r.sheets; }
      } catch (e) {
        if (!(e && e.missing)) console.warn("cardforge/print: sheets", e);
      }
      paintIntents();
      refresh();
      loadIcc().then(paintGabarits).catch(() => { });
      loadGabarits();
      /* LE CONTROLE AVANT VOL SE LANCE TOUT SEUL. Annonce mais jamais montre,
         il ne valait rien : il est maintenant le premier bloc du panneau, et
         il est deja rempli quand on arrive dessus. */
      schedulePreflight();
      CF.on("core:geom", () => { paintFormats(); sync(); refresh(); schedulePreflight(); loadGabarits(); });
      CF.on("core:cards", () => { PF = null; paintPreflight(); refresh(); schedulePreflight(); });
      CF.on("core:doc", (p) => {
        if (!p || p.id === "print" || p.id === "format") {
          sync(); refresh(); schedulePreflight();
        }
        if (p && p.id === "type") { PF = null; paintPreflight(); schedulePreflight(); }
      });
      CF.on("core:render", () => { syncGuides(); });
      M.emit("ready", { plan: PLAN });
    },
  });
})();
