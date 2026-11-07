"""t421 (cartes hexagonales, 07/11/2026) — changements FONCTIONNELS de core.js posés APRÈS L7.

Huit formats hexagonaux : la table FORMATS gagne `forme` / `orientation`, le CORE porte le bloc CF-HEX (miroir de
backend/app/services/cards/hexa.py, comparé sous node par test_cards_hexa.py), `geomOf` rend forme / orientation /
contour_mm, `CF.hexContours` l'expose, et le coin par défaut d'un hexagone est 0 (comme normalize_format du backend).
Les libellés des huit formats passent par dzT (cartes.core.fmt_hex_*), via `hexLabel`, branchée dans le sélecteur de
format par l'entrée « esc(f.label) » du groupe coque (même ligne, même édition).
La table réversible L7 exige : source du poste == base f788790b + éditions ; d'où cette saisie (comme t183).
Les sauts de ligne des insertions multi-lignes sont CRLF, comme la source.
"""
from outils import S

C = "js/core.js"


def _crlf(t):
    return t.replace("\n", "\r\n")


_ROWS = r"""    /* t421 : les huit hexagones. `trim_mm` est le rectangle qui englobe l'hexagone ;
       forme/orientation sont absentes des douze rectangles (absence = "rect"). */
    { id: "hex_p50", label: "Hexagone 50 mm, pointe en haut", unit: "mm", trim_mm: [50.0, 57.735], forme: "hex", orientation: "pointe" },
    { id: "hex_p635", label: "Hexagone 63,5 mm, pointe en haut", unit: "mm", trim_mm: [63.5, 73.323], forme: "hex", orientation: "pointe" },
    { id: "hex_p75", label: "Hexagone 75 mm, pointe en haut", unit: "mm", trim_mm: [75.0, 86.603], forme: "hex", orientation: "pointe" },
    { id: "hex_p90", label: "Hexagone 90 mm, pointe en haut", unit: "mm", trim_mm: [90.0, 103.923], forme: "hex", orientation: "pointe" },
    { id: "hex_f50", label: "Hexagone 50 mm, côté plat en haut", unit: "mm", trim_mm: [57.735, 50.0], forme: "hex", orientation: "plat" },
    { id: "hex_f635", label: "Hexagone 63,5 mm, côté plat en haut", unit: "mm", trim_mm: [73.323, 63.5], forme: "hex", orientation: "plat" },
    { id: "hex_f75", label: "Hexagone 75 mm, côté plat en haut", unit: "mm", trim_mm: [86.603, 75.0], forme: "hex", orientation: "plat" },
    { id: "hex_f90", label: "Hexagone 90 mm, côté plat en haut", unit: "mm", trim_mm: [103.923, 90.0], forme: "hex", orientation: "plat" },
"""

_HEX = r"""/* ═══ CF-HEX-BEGIN ═══ */
  /* t421 : le contour des cartes hexagonales, en mm.
     MIROIR EXACT de backend/app/services/cards/hexa.py (et des proprietes de
     CardGeom). `test_cards_hexa.py` extrait ce bloc, l'execute sous node et le
     compare au Python a 0,001 mm pres. Autonome : aucune variable du fichier. */
  /* sommets de la coupe, repere coin haut-gauche, sens horaire (y vers le bas) */
  function hexSommets(trim_mm, orientation) {
    const w = trim_mm[0], h = trim_mm[1];
    if (orientation === "pointe") return [[w / 2, 0], [w, h / 4], [w, 3 * h / 4], [w / 2, h], [0, 3 * h / 4], [0, h / 4]];
    if (orientation === "plat") return [[w / 4, 0], [3 * w / 4, 0], [w, h / 2], [3 * w / 4, h], [w / 4, h], [0, h / 2]];
    return [[0, 0], [w, 0], [w, h], [0, h]];
  }
  /* decalage perpendiculaire d'un polygone convexe ; d > 0 vers l'exterieur ;
     [] si le decalage retourne le polygone */
  function hexDecale(pts, d) {
    const n = pts.length;
    if (n < 3) return [];
    let cx = 0, cy = 0;
    pts.forEach((p) => { cx += p[0]; cy += p[1]; });
    cx /= n; cy /= n;
    const L = [];
    for (let i = 0; i < n; i++) {
      const a = pts[i], b = pts[(i + 1) % n];
      const dx = b[0] - a[0], dy = b[1] - a[1], ln = Math.sqrt(dx * dx + dy * dy);
      const ux = dx / ln, uy = dy / ln;
      let nx = uy, ny = -ux;
      if (((a[0] + b[0]) / 2 - cx) * nx + ((a[1] + b[1]) / 2 - cy) * ny < 0) { nx = -nx; ny = -ny; }
      L.push([a[0] + nx * d, a[1] + ny * d, ux, uy]);
    }
    const out = [];
    for (let i = 0; i < n; i++) {
      const P = L[(i + n - 1) % n], Q = L[i];
      const den = P[2] * Q[3] - P[3] * Q[2];
      if (Math.abs(den) < 1e-12) return [];
      const t = ((Q[0] - P[0]) * Q[3] - (Q[1] - P[1]) * Q[2]) / den;
      out.push([P[0] + P[2] * t, P[1] + P[3] * t]);
    }
    for (let i = 0; i < n; i++) {
      const a = pts[i], b = pts[(i + 1) % n], c = out[i], e = out[(i + 1) % n];
      if ((b[0] - a[0]) * (e[0] - c[0]) + (b[1] - a[1]) * (e[1] - c[1]) <= 0) return [];
    }
    return out;
  }
  /* Sutherland-Hodgman contre le rectangle [0, w] x [0, h] */
  function hexDecoupe(poly, w, h) {
    const coupe = (pts, dedans, croise) => {
      const res = [];
      for (let i = 0; i < pts.length; i++) {
        const cur = pts[i], prev = pts[(i + pts.length - 1) % pts.length];
        const a = dedans(prev), b = dedans(cur);
        if (a && b) res.push(cur);
        else if (a && !b) res.push(croise(prev, cur));
        else if (b && !a) { res.push(croise(prev, cur)); res.push(cur); }
      }
      return res;
    };
    const surX = (x0) => (p, q) => [x0, p[1] + (q[1] - p[1]) * (x0 - p[0]) / (q[0] - p[0])];
    const surY = (y0) => (p, q) => [p[0] + (q[0] - p[0]) * (y0 - p[1]) / (q[1] - p[1]), y0];
    let pts = poly.slice();
    [[(p) => p[0] >= 0, surX(0)], [(p) => p[0] <= w, surX(w)], [(p) => p[1] >= 0, surY(0)], [(p) => p[1] <= h, surY(h)]].forEach((c) => {
      if (pts.length) pts = coupe(pts, c[0], c[1]);
    });
    return pts;
  }
  /* g : une geometrie de geomOf() d'un hexagone. Tout est rendu dans le repere
     de la TOILE (coin haut-gauche de l'image, fond perdu compris), en mm :
     coupe, fond (fond perdu tronque a la toile), sur (zone sure), milieux (des
     six cotes de la coupe). */
  function hexContours(g) {
    const k = 25.4 / g.dpi, ox = g.bleed_off_px[0] * k, oy = g.bleed_off_px[1] * k;
    const vers = (pts) => pts.map((p) => [p[0] + ox, p[1] + oy]);
    const w = g.canvas_px[0] * k, h = g.canvas_px[1] * k, tol = k / 2;
    /* le depassement d'un demi-pixel est du bruit de quantification de la toile :
       on le ramene au bord ; celui des pointes (0,46 mm pour 3 mm) reste tronque. */
    const cale = (v, hi) => (v >= -tol && v <= hi + tol ? Math.min(Math.max(v, 0), hi) : v);
    const coupe = vers(g.contour_mm);
    const fond = hexDecoupe(vers(hexDecale(g.contour_mm, g.bleed_mm)).map((p) => [cale(p[0], w), cale(p[1], h)]), w, h);
    const sur = vers(hexDecale(g.contour_mm, -g.safe_mm));
    const milieux = coupe.map((p, i) => { const q = coupe[(i + 1) % coupe.length]; return [(p[0] + q[0]) / 2, (p[1] + q[1]) / 2]; });
    return { coupe: coupe, fond: fond, sur: sur, milieux: milieux };
  }
  /* ═══ CF-HEX-END ═══ */

"""

_GEOM_RET = r"""      /* t421 : contour de coupe arrondi a 3 decimales, comme to_dict() du backend
         (qui ne l'ajoute qu'aux hexagones ; ici un rectangle rend ses 4 coins). */
      forme: F.forme || "rect", orientation: F.orientation || null,
      contour_mm: hexSommets(F.trim_mm, F.orientation).map((p) => [rnd(p[0], 3), rnd(p[1], 3)]),
"""

_HEXLABEL = r"""  /* t421 : libelles des hexagones, traduits (cles statiques, une par format) */
  function hexLabel(id) {
    return ({
      hex_p50: dzT("cartes.core.fmt_hex_p50"), hex_p635: dzT("cartes.core.fmt_hex_p635"),
      hex_p75: dzT("cartes.core.fmt_hex_p75"), hex_p90: dzT("cartes.core.fmt_hex_p90"),
      hex_f50: dzT("cartes.core.fmt_hex_f50"), hex_f635: dzT("cartes.core.fmt_hex_f635"),
      hex_f75: dzT("cartes.core.fmt_hex_f75"), hex_f90: dzT("cartes.core.fmt_hex_f90"),
    })[id];
  }

"""

_COIN = r"""        /* t421 : meme regle que normalize_format du backend — un hexagone naît a coin 0,
           et le quitter rend au rectangle son coin par defaut ; un corner_mm explicite
           de l'appel, lu plus bas, l'emporte. */
        const hexN = FMT_BY_ID[out.fmt].forme === "hex", hexA = FMT_BY_ID[f.fmt].forme === "hex";
        if (hexN && !hexA) out.corner_mm = 0;
        else if (!hexN && hexA) out.corner_mm = 3;
"""

_LIBELLES = {
    "cartes.core.fmt_hex_p50": ("Hexagone 50 mm, pointe en haut", "Hexagon 50 mm, point up"),
    "cartes.core.fmt_hex_p635": ("Hexagone 63,5 mm, pointe en haut", "Hexagon 63,5 mm, point up"),
    "cartes.core.fmt_hex_p75": ("Hexagone 75 mm, pointe en haut", "Hexagon 75 mm, point up"),
    "cartes.core.fmt_hex_p90": ("Hexagone 90 mm, pointe en haut", "Hexagon 90 mm, point up"),
    "cartes.core.fmt_hex_f50": ("Hexagone 50 mm, côté plat en haut", "Hexagon 50 mm, flat side up"),
    "cartes.core.fmt_hex_f635": ("Hexagone 63,5 mm, côté plat en haut", "Hexagon 63,5 mm, flat side up"),
    "cartes.core.fmt_hex_f75": ("Hexagone 75 mm, côté plat en haut", "Hexagon 75 mm, flat side up"),
    "cartes.core.fmt_hex_f90": ("Hexagone 90 mm, côté plat en haut", "Hexagon 90 mm, flat side up"),
}

ENTREES = [
    # la table FORMATS : huit lignes après `micro`
    S(C, 124, "trim_mm: [31.75, 44.45] },",
      "trim_mm: [31.75, 44.45] },\r\n" + _crlf(_ROWS).rstrip("\r\n"), {}),
    # le bloc CF-HEX, juste avant geomOf
    S(C, 270, "function geomOf(fmt, dpi, bleed_mm, safe_mm, corner_mm) {",
      _crlf(_HEX) + "  function geomOf(fmt, dpi, bleed_mm, safe_mm, corner_mm) {", {}),
    # geomOf : forme / orientation / contour_mm
    S(C, 325, "mm2px: mm2px, px2mm: px2mm,",
      _crlf(_GEOM_RET).lstrip(" ") + "      mm2px: mm2px, px2mm: px2mm,", {}),
    # coin par défaut d'un hexagone : 0
    S(C, 345, "safe_mm: b, corner_mm: 3 };", 'safe_mm: b, corner_mm: F.forme === "hex" ? 0 : 3 };', {}),
    S(C, 410, "out.bleed_mm = nat; out.safe_mm = nat;",
      "out.bleed_mm = nat; out.safe_mm = nat;\r\n" + _crlf(_COIN).rstrip("\r\n"), {}),
    # hexLabel (libellés traduits des huit formats), avant MM_PER_INCH
    S(C, 129, "const MM_PER_INCH = 25.4;",
      _crlf(_HEXLABEL).lstrip(" ") + "  const MM_PER_INCH = 25.4;", _LIBELLES),
    # CF.hexContours
    S(C, 2604, "geom: geom, geomOf: geomOf, nativeBleed: nativeBleed,",
      "geom: geom, geomOf: geomOf, nativeBleed: nativeBleed, hexContours: hexContours,", {}),
]
