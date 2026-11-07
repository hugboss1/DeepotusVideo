"""t421 (cartes hexagonales, 07/11/2026, tâche 3) — l'APERÇU hexagonal, le verso sans cadre et les pièces hors
périmètre, posés APRÈS L7 (comme t421.py pour la tâche 2).

core.js :
- `hexChemin` (polygone en mm, sommets arrondis de corner_mm), `hexMasque` (en fin de rendu, composition
  `destination-in` du polygone du FOND PERDU : hors de lui la toile est transparente), `guidesHex` (coupe, fond perdu
  et zone sûre hexagonaux, à la place des rectangles) ; la vignette de galerie d'un hexagone en a la silhouette ;
  l'aperçu d'un hexagone porte la classe `hex` (ombre portée qui suit l'alpha, cardforge.css) ;
- `CF.horsHex(id)` et la table HORS_HEX des pièces qui ne gèrent pas encore l'hexagone ; `syncHorsHex` marque leur
  entrée de rail et pose dans leur panneau la phrase cartes.hexa.non_gere (appelée par syncFormatWidget : chargement
  et chaque changement de format).
mod-frame.js :
- `paintBack` : sans cadre (famille « none », ou carte hexagonale dont le cadre dort), le verso est l'image de la
  carte (`card.back`, colonne « dos »), sinon rien ; la branche du deck à cadre reste intacte ;
- le painter du Cadre, sur un hexagone, ne peint ni ne publie rien (le document n'est pas touché : le cadre revient
  tel quel si le deck repasse en rectangle) ; seul le verso image passe.
Un rectangle ne change d'aucun pixel : chaque branche neuve est gardée par `forme === "hex"` ou par la famille
« none » (qui ne peignait rien). Les sauts de ligne des insertions sont CRLF, comme la source.
"""
from outils import S

C = "js/core.js"
F = "js/mod-frame.js"


def _crlf(t):
    return t.replace("\n", "\r\n")


_NON_GERE = {"cartes.hexa.non_gere": ("Cette pièce ne gère pas encore les cartes hexagonales.",
                                      "This part does not handle hexagonal cards yet.")}

_BLOC = r"""/* ═══ t421 : L'APERCU HEXAGONAL ═══════════════════════════════════════════
     Le rendu reste rectangulaire (la toile du contrat) ; un hexagone est
     ensuite DECOUPE : hors du polygone du fond perdu, la toile est
     transparente. Les polygones viennent de hexContours (repere toile, mm). */
  /* le chemin d'un polygone en mm (k = px par mm), sommets arrondis de r mm ;
     le rayon est borne pour que deux arrondis ne se croisent pas sur un cote */
  function hexChemin(ctx, pts, r, k) {
    ctx.beginPath();
    const n = pts.length;
    if (n < 3) return;
    const P = pts.map((p) => [p[0] * k, p[1] * k]);
    const R = (r > 0) ? r * k : 0;
    if (!R) {
      ctx.moveTo(P[0][0], P[0][1]);
      for (let i = 1; i < n; i++) ctx.lineTo(P[i][0], P[i][1]);
      ctx.closePath();
      return;
    }
    ctx.moveTo((P[n - 1][0] + P[0][0]) / 2, (P[n - 1][1] + P[0][1]) / 2);
    for (let i = 0; i < n; i++) {
      const a = P[i], b = P[(i + 1) % n], z = P[(i + n - 1) % n];
      const la = Math.hypot(a[0] - z[0], a[1] - z[1]), lb = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (la < 1e-9 || lb < 1e-9) { ctx.lineTo(a[0], a[1]); continue; }
      const cos = ((z[0] - a[0]) * (b[0] - a[0]) + (z[1] - a[1]) * (b[1] - a[1])) / (la * lb);
      const t = Math.tan(Math.acos(Math.max(-1, Math.min(1, cos))) / 2);
      ctx.arcTo(a[0], a[1], b[0], b[1], Math.min(R, Math.min(la, lb) / 2 * t));
    }
    ctx.closePath();
  }
  /* rayons : la coupe suit corner_mm du DOCUMENT ; son decale de d garde les
     memes tangentes avec un rayon r + d (0 reste 0 : un hexagone vif) */
  function hexRayon(g, d) {
    const r = Math.max(0, Number(g.corner_mm) || 0);
    return r > 0 ? Math.max(0, r + d) : 0;
  }
  /* en fin de rendu : la toile est decoupee au polygone du fond perdu */
  function hexMasque(ctx, g) {
    const c = hexContours(g);
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalCompositeOperation = "destination-in";
    ctx.globalAlpha = 1;
    ctx.fillStyle = "#000000";
    hexChemin(ctx, c.fond, hexRayon(g, g.bleed_mm), g.dpi / 25.4);
    ctx.fill();
    ctx.restore();
  }
  /* les reperes d'un hexagone : memes couleurs et memes traits que les
     rectangles de guidesPainter */
  function guidesHex(ctx, g, u) {
    const c = hexContours(g), k = g.dpi / 25.4;
    ctx.save();
    ctx.lineWidth = u;
    ctx.strokeStyle = "#00b7ff";                   /* fond perdu */
    ctx.setLineDash([6 * u, 5 * u]);
    hexChemin(ctx, c.fond, hexRayon(g, g.bleed_mm), k); ctx.stroke();
    ctx.setLineDash([]);
    ctx.strokeStyle = "#ff2d92";                   /* coupe */
    hexChemin(ctx, c.coupe, hexRayon(g, 0), k); ctx.stroke();
    if (c.sur.length) {
      ctx.setLineDash([9 * u, 6 * u]);
      ctx.strokeStyle = "#33d18b";                 /* zone sure */
      hexChemin(ctx, c.sur, hexRayon(g, -g.safe_mm), k); ctx.stroke();
    }
    ctx.restore();
  }
  /* les pieces qui ne gerent PAS ENCORE l'hexagone : elles restent au rail et
     le disent (leurs routes de production refusent un deck hexagonal en 409) */
  const HORS_HEX = Object.freeze(["frame", "solid", "texture", "gltf", "forge3d", "edition", "capture"]);
  function horsHex(id) { return HORS_HEX.indexOf(id) >= 0; }
  function syncHorsHex() {
    if (!hasDOM) return;
    const hex = geom().forme === "hex";
    Array.prototype.forEach.call(document.querySelectorAll(".rail-item"), (b) => {
      const id = b.dataset.mod, on = hex && horsHex(id), m = REG[id];
      const nom = m ? m.title : dzT("cartes.core.module_absent", { id: id });
      b.classList.toggle("hors-hex", on);
      b.title = on ? nom + " — " + dzT("cartes.hexa.non_gere") : nom;
    });
    Array.prototype.forEach.call(document.querySelectorAll(".cf-panel"), (s) => {
      const on = hex && horsHex(s.dataset.mod);
      let n = s.querySelector(".cf-hors-hex");
      if (on && !n) {
        n = document.createElement("p");
        n.className = "cf-hors-hex";
        n.setAttribute("role", "status");
        const h = s.querySelector(".panel-head");
        s.insertBefore(n, h ? h.nextSibling : s.firstChild);
      }
      if (n) { n.textContent = on ? dzT("cartes.hexa.non_gere") : ""; n.hidden = !on; }
    });
  }
  /* ═══ fin t421 ═══ */

"""

_THUMB_HEX = r"""    /* t421 : la vignette d'un hexagone en a la silhouette (decoupe, puis trait) */
    const hexV = fmt.forme === "hex" ? hexSommets(fmt.trim_mm, fmt.orientation) : null;
    if (hexV) {
      c.globalCompositeOperation = "destination-in";
      hexChemin(c, hexV, 0, k); c.fill();
      c.globalCompositeOperation = "source-over";
    }
    c.globalAlpha = 0.5;
    c.strokeStyle = galColor(pal.ink, "#000000");
    c.lineWidth = 1;
    if (hexV) { hexChemin(c, hexV, 0, k); c.stroke(); }
    else c.strokeRect(0.5, 0.5, W - 1, H - 1);"""

_VERSO = r"""
  /* t421 : LE VERSO D'UNE CARTE SANS CADRE — famille « none », ou carte
     hexagonale dont le cadre dort — est l'image de la carte (`card.back`, la
     colonne « dos » des Donnees), lue dans le magasin d'images de
     l'application, comme son recto (`card.art`, piece 01). Un id de motif du
     catalogue n'est pas une image : il n'a de sens qu'avec un cadre. */
  function versoImage(card) {
    const v = card && typeof card.back === "string" ? card.back : "";
    if (!v || byId(BACKS, v)) return "";
    return v.indexOf("img:") === 0 ? v.slice(4) : v;
  }
  function sansCadre(g, f) { return f.family === "none" || g.forme === "hex"; }
  /* le verso image de la carte COURANTE : l'arrivee tardive le redemande */
  function versoCourant() {
    try { const v = versoImage(CF.card(CF.current())); return v ? [v] : []; }
    catch (e) { return []; }
  }
  /* couvre la TOILE (fond perdu compris), comme le verso personnalise ;
     sans image, rien n'est peint : la face reste blanche */
  function paintVersoImage(ctx, g, card) {
    const file = versoImage(card);
    if (!file) return;
    const W = g.canvas_px[0], H = g.canvas_px[1];
    const rec = frameImgRec(file, "app");
    if (rec && rec.ok && rec.img) {
      const c = backCover(rec.img.naturalWidth || rec.img.width, rec.img.naturalHeight || rec.img.height, W, H);
      ctx.drawImage(rec.img, c[0], c[1], c[2], c[3]);
    } else {
      backDamier(ctx, 0, 0, W, H, file, "image du dos manquante");
    }
  }"""

ENTREES = [
    # ── core.js ──
    S(C, 612, "function guidesPainter(ctx, g) {", _crlf(_BLOC) + "  function guidesPainter(ctx, g) {", _NON_GERE),
    S(C, 619, "const u = Math.max(1, g.dpi / 300);           /* epaisseur constante a l'oeil */",
      "const u = Math.max(1, g.dpi / 300);           /* epaisseur constante a l'oeil */\r\n"
      "    if (g.forme === \"hex\") { guidesHex(ctx, g, u); return; }    /* t421 */", {}),
    S(C, 712, "if (guides) {",
      "/* t421 : la carte hexagonale est decoupee au fond perdu, AVANT les reperes */\r\n"
      "    if (g.forme === \"hex\") hexMasque(ctx, g);\r\n"
      "    if (guides) {", {}),
    S(C, 1215, "c2.drawImage(FULL, 0, 0, out.width, out.height);",
      "c2.drawImage(FULL, 0, 0, out.width, out.height);\r\n"
      "      out.classList.toggle(\"hex\", g.forme === \"hex\");     /* t421 : ombre qui suit l'alpha */", {}),
    S(C, 1274, "if (!hasDOM) return;\r\n    const g = geom(), f = DOC.format;",
      "if (!hasDOM) return;\r\n    syncHorsHex();                     /* t421 */\r\n    const g = geom(), f = DOC.format;", {}),
    S(C, 1950, "c.globalAlpha = 0.5;\r\n    c.strokeStyle = galColor(pal.ink, \"#000000\");\r\n    c.lineWidth = 1;\r\n"
               "    c.strokeRect(0.5, 0.5, W - 1, H - 1);",
      _crlf(_THUMB_HEX).lstrip(" "), {}),
    S(C, 2605, "cards: cards, card: card,",
      "cards: cards, card: card,\r\n    /* t421 : les pieces qui ne gerent pas encore l'hexagone */\r\n    horsHex: horsHex,", {}),
    # ── mod-frame.js ──
    S(F, 3267, "return mag === \"app\" ? decorFiles(f0) : backFiles(f0);",
      "return mag === \"app\" ? decorFiles(f0).concat(versoCourant()) : backFiles(f0);   /* t421 : + le verso image */", {}),
    S(F, 3317, "function backImgRec(file) { return frameImgRec(file, \"deck\"); }",
      "function backImgRec(file) { return frameImgRec(file, \"deck\"); }" + _crlf(_VERSO), {}),
    S(F, 3521, "function paintBack(ctx, g, f, card, d) {\r\n    if (f.family === \"none\") return;",
      "function paintBack(ctx, g, f, card, d) {\r\n"
      "    /* t421 : sans cadre, le verso est l'image de la carte (ou rien) ; le deck a cadre ne passe pas ici */\r\n"
      "    if (sansCadre(g, f)) { paintVersoImage(ctx, g, card); return; }", {}),
    S(F, 3747, "const f = st(doc);\r\n          publishWindow(geom, f);",
      "const f = st(doc);\r\n"
      "          /* t421 : le Cadre ne gere pas l'hexagone. Il DORT : ni peinture, ni\r\n"
      "             publication (le document n'est pas touche, le cadre revient tel\r\n"
      "             quel en rectangle) ; seul le verso image d'une carte passe. */\r\n"
      "          if (geom.forme === \"hex\") {\r\n"
      "            if (side !== \"back\") return;\r\n"
      "            const vh = versoImage(card);\r\n"
      "            if (vh) await ensureFrameImgs([vh], \"app\");\r\n"
      "            paintBack(ctx, geom, f, card, doc);\r\n"
      "            return;\r\n"
      "          }\r\n"
      "          publishWindow(geom, f);", {}),
    S(F, 3770, "if (backOf(f, card) === \"custom\") {",
      "/* t421 : le verso image d'une carte sans cadre, attendu de meme */\r\n"
      "          const vi = sansCadre(geom, f) ? versoImage(card) : \"\";\r\n"
      "          if (vi) await ensureFrameImgs([vi], \"app\");\r\n"
      "          if (backOf(f, card) === \"custom\") {", {}),
    S(F, 3779, "paintTop(ctx, geom, st(doc), card, side);",
      "if (geom.forme !== \"hex\") paintTop(ctx, geom, st(doc), card, side);   /* t421 : le Cadre dort */", {}),
]
