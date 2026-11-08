"""t421 (cartes hexagonales, 08/11/2026, tâche 8) — l'ÉCRAN D'IMPRESSION HEXAGONAL de mod-print.js, posé APRÈS L7
(comme t421.py et t421_gabarit.py).

Un jeu hexagonal a SON panneau (`shellHex`, bloc `data-role="hex"`) : le gabarit de dessin de la tâche 6 (déplacé ici,
le panneau rectangulaire ne le porte plus), feuille A4 / Letter / A3, marge, gouttière (par défaut 2 × fond perdu),
recto verso, trait de coupe imprimé, aperçu de page dessiné depuis le plan du SERVEUR (POST hex/plan), message d'un
refus affiché tel quel, et deux téléchargements : « PDF d'impression » (POST hex/pdf, cartes rendues par CF.cardBlob
via `renderAll`, comme l'export rectangulaire) et « Fichier de coupe (ZIP) » (POST hex/coupe). Rappel : couper recto
dessus. Les réglages vivent sous la seule clé `doc.print.hexa` (hors DEFAULTS : `st()` et la spec rectangulaire ne
la voient pas).

Le panneau hexagonal n'appelle ni `layoutOf`, ni `layout`, ni `preflight` : `refresh`, `verify`,
`schedulePreflight` et `preflight` rendent la main en tête quand HEXA est vrai. Le chemin rectangulaire n'a aucune
ligne modifiée : `shell()` ne se détourne que pour un hexagone ; `core:geom` rebâtit le panneau quand la forme change.

Constat différé de la tâche 5 corrigé : la table des formats nommait les huit hexagones « Hexagone » (le libellé
français coupé au premier chiffre, même en anglais) ; une ligne hexagonale prend désormais CF.libelleFormat, les
lignes rectangulaires sont inchangées.
Les sauts de ligne des insertions sont CRLF, comme la source.
"""
from outils import S

F = "js/mod-print.js"


def _crlf(t):
    return t.replace("\n", "\r\n")


_GABHEX = {
    "cartes.print.gabhex_titre": ("Gabarit de dessin", "Drawing template"),
    "cartes.print.gabhex_png": ("Télécharger le gabarit (PNG)", "Download the template (PNG)"),
    "cartes.print.gabhex_svg": ("Télécharger le gabarit (SVG)", "Download the template (SVG)"),
    "cartes.print.gabhex_aide": (
        "Un PNG transparent à la taille de la toile et un SVG en millimètres montrent la coupe, le fond perdu, "
        "la zone sûre et le milieu de chaque côté, où placer vos symboles de liens. Ouvrez-le dans le Photolab "
        "ou le Vectorlab pour dessiner par-dessus.",
        "A transparent PNG at canvas size and an SVG in millimetres show the cut line, the bleed, the safe zone "
        "and the middle of each side, where your link symbols go. Open it in the Photolab or the Vectorlab to "
        "draw over it."),
}

_HEX = {
    "cartes.print.hex_titre": ("Planche hexagonale", "Hexagonal sheet"),
    "cartes.print.hex_format": ("{format} · fond perdu {b} mm · gouttière minimale {g} mm",
                                "{format} · bleed {b} mm · minimum gutter {g} mm"),
    "cartes.print.hex_trait": ("Trait de coupe imprimé", "Printed cut line"),
    "cartes.print.hex_btn_pdf": ("PDF d'impression", "Print PDF"),
    "cartes.print.hex_btn_coupe": ("Fichier de coupe (ZIP)", "Cut file (ZIP)"),
    "cartes.print.hex_aide_gouttiere": (
        "Les cartes se posent en nid d'abeilles, rangées décalées d'une demi-case. La gouttière ne descend pas sous "
        "deux fonds perdus : les fonds perdus de deux voisines ne se chevauchent jamais. La marge loge les trois "
        "repères de calage.",
        "Cards are laid out in a honeycomb, rows offset by half a cell. The gutter never goes below twice the bleed, "
        "so the bleeds of neighbouring cards never overlap. The margin holds the three registration marks."),
    "cartes.print.hex_aide_duplex": (
        "Recto verso : chaque page recto est suivie de son verso, en miroir pour un retournement sur le grand côté ; "
        "une carte sans verso laisse sa case blanche.",
        "Duplex: each front page is followed by its back, mirrored for a long-edge flip; a card without a back "
        "leaves its cell blank."),
    "cartes.print.hex_aide_coupe": (
        "Coupez recto dessus : le fichier de coupe (SVG et DXF en millimètres, un par page) suit la page recto. "
        "Calez la machine sur les trois repères imprimés.",
        "Cut face up: the cut file (SVG and DXF in millimetres, one per page) follows the front page. Align the "
        "machine on the three printed registration marks."),
    "cartes.print.hex_par_page": ("par page", "per page"),
    "cartes.print.hex_cartes": ("cartes du jeu", "deck cards"),
    "cartes.print.hex_pages": ("pages recto", "front pages"),
    "cartes.print.hex_pages_pdf": ("pages du PDF", "PDF pages"),
    "cartes.print.hex_feuille": ("feuille", "sheet", "contexte"),
    "cartes.print.hex_aucun_plan": ("pas encore de plan", "no layout yet"),
    "cartes.print.hex_attente": ("Le format vient de changer : le plan suit dès que le jeu est enregistré.",
                                 "The format just changed: the layout follows as soon as the deck is saved."),
    "cartes.print.hex_busy_coupe": ("écriture du fichier de coupe…", "writing the cut file…"),
    "cartes.print.hex_log_pdf": ("{n} cartes · {p} pages · {pp} par page", "{n} cards · {p} pages · {pp} per page"),
    "cartes.print.hex_log_coupe": ("{p} pages recto · SVG + DXF", "{p} front pages · SVG + DXF"),
    "cartes.print.hex_toast_pdf": ("PDF hexagonal écrit : {n} cartes, {p} pages.",
                                   "Hexagonal PDF written: {n} cards, {p} pages."),
    "cartes.print.hex_err_pdf": ("PDF d'impression refusé : {e}", "Print PDF refused: {e}"),
    "cartes.print.hex_err_coupe": ("Fichier de coupe refusé : {e}", "Cut file refused: {e}"),
    "cartes.print.hex_toast_coupe": ("Fichier de coupe écrit : {p} pages, SVG et DXF.",
                                     "Cut file written: {p} pages, SVG and DXF."),
}

_BLOC = r"""/* ══ t421 (tâche 8) : L'IMPRESSION HEXAGONALE ══════════════════════════════
     Un jeu hexagonal a SON panneau : feuille, marge, gouttière, recto verso,
     trait de coupe imprimé, un aperçu de page dessiné depuis le plan du
     SERVEUR (POST hex/plan) et deux téléchargements, le PDF d'impression
     (hex/pdf) et le fichier de coupe (hex/coupe : un ZIP de SVG + DXF). Ce
     panneau n'appelle ni layoutOf, ni layout, ni preflight : ils ne savent
     que la grille rectangulaire. Le panneau rectangulaire reste tel quel —
     `shell` ne se détourne que pour un hexagone. Les réglages vivent sous la
     seule clé `doc.print.hexa`, hors DEFAULTS : `st()` et la spec
     rectangulaire ne la voient pas. ══════════════════════════════════════ */
  let HEXA = false, HEXPLAN = null, HEXERR = "", HEXATTENTE = false, HEXSEQ = 0, HEXRETRY = 0;
  let HEXBUSY = false, hxtimer = null;
  const HEX_FEUILLES = [["a4", "A4"], ["letter", "Letter"], ["a3", "A3"]];
  function estHex() { const g = CF.geom(); return !!g && g.forme === "hex"; }
  function hexStocke() { const p = CF.doc().print; return (p && p.hexa) || {}; }
  function hexReglages() {
    const h = hexStocke(), b = Number(CF.geom().bleed_mm) || 0;
    const nb = (v, d) => (v != null && v !== "" && isFinite(Number(v)) ? Number(v) : d);
    return {
      sheet: HEX_FEUILLES.some((f) => f[0] === h.sheet) ? h.sheet : "a4",
      marge_mm: nb(h.marge_mm, 12),
      /* LA GOUTTIÈRE PAR DÉFAUT VAUT DEUX FONDS PERDUS : en dessous, le
         serveur refuse (les fonds perdus de deux voisines se
         chevaucheraient). Celle du panneau rectangulaire (4 mm) serait
         refusée pour 3 mm de fond perdu. */
      gouttiere_mm: nb(h.gouttiere_mm, Math.round(2 * b * 1000) / 1000),
      trait: !!h.trait, duplex: !!h.duplex,
    };
  }
  /* le corps des trois routes hex/* : le MÊME pour le plan, le PDF et la coupe */
  function hexCorps() {
    const r = hexReglages();
    return { sheet: r.sheet, marge_mm: r.marge_mm, gouttiere_mm: r.gouttiere_mm,
      n_cards: CF.cards().length, trait: r.trait, duplex: r.duplex };
  }
  function setHex(partial) { M.patch({ hexa: Object.assign({}, hexStocke(), partial) }); }

  function shellHex() {
    const h = hexReglages();
    const num = (k, label, min, max, step) => '<label class="fld"><span class="lbl">' + esc(label) + '</span>'
      + '<span class="cf-print-num"><input type="number" data-hx="' + k + '" min="' + min + '" max="' + max
      + '" step="' + step + '" value="' + esc(h[k]) + '"><i class="cf-print-px">mm</i></span></label>';
    const chk = (k, label) => '<label class="check tiny"><input type="checkbox" data-hx="' + k + '"'
      + (h[k] ? " checked" : "") + '><span>' + esc(label) + '</span></label>';
    HOST.innerHTML = ''
      + '<div class="cf-print-top">'
      + '<span class="cf-print-free">' + dzT("cartes.print.gratuit") + '</span>'
      + '</div>'

      /* ── GABARIT DE DESSIN (tâche 6) ── */
      + '<div class="cf-print-gabhex" data-role="gabhex" hidden>'
      + '<details class="grp" open><summary>' + dzT("cartes.print.gabhex_titre") + '</summary><div class="grp-body">'
      + '<div class="btn-row">'
      + '<a class="btn sm" data-role="gabhex-png" href="#" download>' + ICO("dz-action-telecharger", 16, "cf-ic") + dzT("cartes.print.gabhex_png") + '</a>'
      + '<a class="btn sm" data-role="gabhex-svg" href="#" download>' + ICO("dz-action-telecharger", 16, "cf-ic") + dzT("cartes.print.gabhex_svg") + '</a>'
      + '</div>'
      + '<p class="hint">' + dzT("cartes.print.gabhex_aide") + '</p>'
      + '</div></details></div>'

      /* ── LA PLANCHE EN NID D'ABEILLES ── */
      + '<div class="cf-print-hex" data-role="hex">'
      + '<details class="grp" open><summary>' + dzT("cartes.print.hex_titre") + '</summary><div class="grp-body">'
      + '<p class="hint" data-role="hex-format"></p>'
      + '<label class="fld"><span class="lbl">' + dzT("cartes.print.planche") + '</span>'
      + '<div class="seg sm" data-hxseg="sheet">' + HEX_FEUILLES.map((f) => '<button class="seg-b'
        + (f[0] === h.sheet ? " active" : "") + '" type="button" data-v="' + f[0] + '">' + f[1] + '</button>').join("")
      + '</div></label>'
      + '<div class="grid2">' + num("marge_mm", dzT("cartes.print.marge"), 0, 60, 0.5)
      + num("gouttiere_mm", dzT("cartes.print.gouttiere"), 0, 40, 0.5) + '</div>'
      + '<div class="grid2">' + chk("duplex", dzT("cartes.print.recto_verso"))
      + chk("trait", dzT("cartes.print.hex_trait")) + '</div>'
      + '<div class="cf-print-plan">'
      + '<canvas class="cf-print-canvas" data-role="hex-plan" width="264" height="330"></canvas>'
      + '<div class="cf-print-side">'
      + '<dl class="cf-print-read" data-role="hex-read"></dl>'
      + '<div class="cf-print-warns" data-role="hex-err"></div>'
      + '</div></div>'
      + '<div class="btn-row">'
      + '<button class="btn strong" type="button" data-act="hexpdf">' + dzT("cartes.print.hex_btn_pdf") + '</button>'
      + '<button class="btn strong" type="button" data-act="hexcoupe">' + dzT("cartes.print.hex_btn_coupe") + '</button>'
      + '</div>'
      + '<p class="hint cf-print-hex-rappel">' + dzT("cartes.print.hex_aide_coupe") + '</p>'
      + '<p class="hint">' + dzT("cartes.print.hex_aide_gouttiere") + '</p>'
      + '<p class="hint">' + dzT("cartes.print.hex_aide_duplex") + '</p>'
      + '</div></details></div>'

      /* ── JOURNAL (le même que le panneau rectangulaire) ── */
      + '<details class="grp"><summary>' + dzT("cartes.print.titre_journal") + '</summary><div class="grp-body">'
      + '<div class="cf-print-log" data-role="log"></div></div></details>';
  }

  /* les champs suivent le document (annulation, autre onglet, format) */
  function syncHex() {
    const h = hexReglages(), g = CF.geom(), f = q('[data-role="hex-format"]');
    if (f) {
      const lib = typeof CF.libelleFormat === "function" ? CF.libelleFormat(g.fmt) : g.fmt;
      f.innerHTML = dzT("cartes.print.hex_format", { format: esc(lib), b: nf(g.bleed_mm, 2), g: nf(2 * g.bleed_mm, 2) });
    }
    ["marge_mm", "gouttiere_mm"].forEach((k) => { const i = q('[data-hx="' + k + '"]'); if (i) i.value = h[k]; });
    ["duplex", "trait"].forEach((k) => { const i = q('[data-hx="' + k + '"]'); if (i) i.checked = !!h[k]; });
    const sg = q('[data-hxseg="sheet"]');
    if (sg) sg.querySelectorAll(".seg-b").forEach((b) => { b.classList.toggle("active", b.dataset.v === h.sheet); });
  }

  function schedulePlanHex(ms) {
    clearTimeout(hxtimer);
    hxtimer = setTimeout(() => { planHex().catch(() => { }); }, ms == null ? 250 : ms);
  }
  /* L'ENREGISTREMENT DU CORE EST DIFFÉRÉ DE 900 ms et le serveur lit la
     géométrie du jeu ENREGISTRÉ : juste après un changement de format, il
     sert encore le plan de l'ancien. Un tel plan n'est ni montré ni
     exporté — on redemande. */
  function hexPlanAJour(p) {
    const g = CF.geom(), pg = (p && p.geom) || {};
    return pg.fmt === g.fmt && Number(pg.dpi) === Number(g.dpi) && String(pg.canvas_px) === String(g.canvas_px);
  }
  /* LE PLAN DU SERVEUR, ou SA phrase : un refus (gouttière < 2 × fond
     perdu, marge trop petite pour les repères…) est affiché tel quel. */
  async function planHex() {
    const seq = ++HEXSEQ;
    let p = null, err = "";
    try { p = await M.api.post("hex/plan", hexCorps()); } catch (e) { err = String((e && e.message) || e); }
    if (seq !== HEXSEQ || !HEXA) return null;
    if (p && !hexPlanAJour(p)) {
      HEXPLAN = null; HEXERR = ""; HEXATTENTE = true;
      if (HEXRETRY++ < 5) schedulePlanHex(1000);
      paintHex();
      return null;
    }
    HEXRETRY = 0; HEXATTENTE = false;
    HEXPLAN = p; HEXERR = err;
    paintHex();
    return p;
  }
  function paintHex() {
    const p = HEXPLAN, d = q('[data-role="hex-read"]'), w = q('[data-role="hex-err"]');
    const ligne = (dt, v) => '<dt>' + dt + '</dt><dd class="big">' + v + '</dd>';
    if (d) {
      d.innerHTML = p ? ligne(dzT("cartes.print.hex_par_page"), p.par_page) + ligne(dzT("cartes.print.hex_cartes"), p.n_cartes)
        + ligne(dzT("cartes.print.hex_pages"), p.pages) + ligne(dzT("cartes.print.hex_pages_pdf"), p.out_pages)
        + ligne(dzT("cartes.print.hex_feuille"), nf(p.size_mm[0], 1) + " x " + nf(p.size_mm[1], 1) + " mm")
        : '<dt>' + dzT("cartes.print.dt_plan") + '</dt><dd class="dim">' + dzT("cartes.print.hex_aucun_plan") + '</dd>';
    }
    if (w) {
      w.innerHTML = HEXERR ? '<div class="cf-print-w err"><span>' + esc(HEXERR) + '</span></div>'
        : HEXATTENTE ? '<div class="cf-print-w info"><span>' + dzT("cartes.print.hex_attente") + '</span></div>' : '';
    }
    qa('[data-act="hexpdf"], [data-act="hexcoupe"]').forEach((b) => { b.disabled = !p; });
    dessinePlanHex();
  }
  /* L'APERÇU : la page 1 recto, à l'échelle, d'après les cases, le contour
     et les repères SERVIS — aucun pas de nid d'abeilles n'est calculé ici. */
  function dessinePlanHex() {
    const cv = q('[data-role="hex-plan"]'), p = HEXPLAN;
    if (!cv || typeof cv.getContext !== "function") return;
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, cv.width, cv.height);
    if (!p) return;
    const sc = Math.min(264 / p.size_mm[0], 330 / p.size_mm[1]);
    const dpr = Math.min(2, (typeof devicePixelRatio === "number" ? devicePixelRatio : 1) || 1);
    const wCss = Math.round(p.size_mm[0] * sc), hCss = Math.round(p.size_mm[1] * sc);
    cv.width = Math.round(wCss * dpr); cv.height = Math.round(hCss * dpr);
    cv.style.width = wCss + "px"; cv.style.height = hCss + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const soft = tone("--ink-muted", "#888"), acc = tone("--accent", "#e8a33d");
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, wCss, hCss);
    ctx.lineWidth = 1; ctx.strokeStyle = soft;
    ctx.strokeRect(0.5, 0.5, wCss - 1, hCss - 1);
    const contour = (p.geom && p.geom.contour_mm) || [];
    const pleines = Math.min(p.par_page, p.n_cartes);
    (p.cases || []).forEach((c, k) => {
      ctx.beginPath();
      contour.forEach((s, i) => {
        const x = (c[0] + s[0]) * sc, y = (c[1] + s[1]) * sc;
        if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y);
      });
      ctx.closePath();
      if (k < pleines) {
        ctx.setLineDash([]);
        ctx.globalAlpha = 0.3; ctx.fillStyle = acc; ctx.fill(); ctx.globalAlpha = 1;
        ctx.strokeStyle = p.trait ? "#111111" : acc;
      } else {
        ctx.setLineDash([3, 3]); ctx.strokeStyle = soft;
      }
      ctx.stroke();
    });
    ctx.setLineDash([]);
    ctx.fillStyle = "#111111";
    const r = (Number(p.repere_diametre_mm) || 5) / 2 * sc;
    (p.reperes_mm || []).forEach((m) => {
      ctx.beginPath(); ctx.arc(m[0] * sc, m[1] * sc, r, 0, Math.PI * 2); ctx.fill();
    });
  }

  /* LE PDF : les cartes rendues par CF.cardBlob (renderAll, comme l'export
     rectangulaire), versos compris en recto verso, puis POST hex/pdf. Le
     plan est redemandé d'abord : un refus du serveur arrive avec SA phrase,
     avant le moindre rendu. */
  /* M.api.blob ne garde d'un refus que « 400 Bad Request » : la PHRASE du
     serveur (taille de carte, recto verso sans verso, PDF impossible…) est
     relue sur la MÊME demande par M.api.raw. Le fichier, lui, ne part que par
     M.api.blob : c'est le seul blob que CF.download accepte (provenance). */
  async function blobHex(sub, corps) {
    try { return await M.api.blob("POST", sub, corps); } catch (e) {
      if (e && e.missing) throw e;
      let detail = "";
      try {
        const r = await M.api.raw("POST", sub, corps);
        if (!r.ok) {
          const d = await r.json();
          const x = d && (d.detail != null ? d.detail : d.error);
          detail = x == null ? "" : (typeof x === "string" ? x : JSON.stringify(x));
        }
      } catch (e2) { /* pas de JSON : on garde le code HTTP */ }
      throw new Error(detail || String((e && e.message) || e));
    }
  }
  /* un export refusé : la phrase, encadrée par l'action, dans le panneau ET le toast */
  function refusHex(cle, e) {
    HEXERR = dzT(cle, { e: String((e && e.message) || e) });
    paintHex();
    CF.toast(HEXERR, true);
  }
  async function exportHexPdf() {
    if (HEXBUSY) return;
    HEXBUSY = true;
    try {
      const p = await planHex();
      if (!p) { CF.toast(HEXERR || dzT("cartes.print.hex_attente"), true); return; }
      const corps = hexCorps();
      const r = await renderAll(!!corps.duplex);
      CF.busy(true, dzT("cartes.print.busy_pdf"));
      const out = await blobHex("hex/pdf", formData(corps, r.fronts, r.backs));
      const name = deckSlug() + "_planches_hex.pdf";
      CF.download(out, name);
      logLine(name, out.size, dzT("cartes.print.hex_log_pdf", { n: r.fronts.length, p: p.out_pages, pp: p.par_page }));
      CF.toast(dzT("cartes.print.hex_toast_pdf", { n: r.fronts.length, p: p.out_pages }));
    } catch (e) { refusHex("cartes.print.hex_err_pdf", e); }
    finally { CF.busy(false); HEXBUSY = false; }
  }
  /* LE FICHIER DE COUPE : un ZIP (page-01.svg, page-01.dxf…), en mm, qui
     suit la page RECTO — on coupe recto dessus. */
  async function exportHexCoupe() {
    if (HEXBUSY) return;
    HEXBUSY = true;
    try {
      const p = await planHex();
      if (!p) { CF.toast(HEXERR || dzT("cartes.print.hex_attente"), true); return; }
      CF.busy(true, dzT("cartes.print.hex_busy_coupe"));
      const out = await blobHex("hex/coupe", hexCorps());
      const name = deckSlug() + "_coupe.zip";
      CF.download(out, name);
      logLine(name, out.size, dzT("cartes.print.hex_log_coupe", { p: p.pages }));
      CF.toast(dzT("cartes.print.hex_toast_coupe", { p: p.pages }));
    } catch (e) { refusHex("cartes.print.hex_err_coupe", e); }
    finally { CF.busy(false); HEXBUSY = false; }
  }

  function clicHex(ev) {
    if (!HEXA) return false;
    const sb = ev.target.closest("[data-hxseg] .seg-b");
    if (sb) {
      if (sb.closest("[data-hxseg]").dataset.hxseg === "sheet") setHex({ sheet: String(sb.dataset.v) });
      return true;
    }
    const act = ev.target.closest("[data-act]"), a = act && act.dataset.act;
    if (a === "hexpdf") { exportHexPdf(); return true; }
    if (a === "hexcoupe") { exportHexCoupe(); return true; }
    return false;
  }
  function changeHex(t) {
    if (!HEXA || !t || !t.dataset || !t.dataset.hx) return false;
    const k = t.dataset.hx, o = {};
    if (k === "duplex" || k === "trait") o[k] = !!t.checked;
    else {
      const v = Number(t.value);
      if (t.value === "" || !isFinite(v)) { syncHex(); return true; }
      o[k] = v;
    }
    setHex(o);
    return true;
  }
  /* LA FORME CHANGE : le panneau se rebâtit (rectangle <-> hexagone). Rend
     vrai si le jeu est hexagonal — le reste de `core:geom` est alors sauté. */
  function geomHex() {
    const h = estHex();
    if (h !== HEXA) {
      HEXA = h; HEXPLAN = null; HEXERR = ""; HEXATTENTE = false; HEXRETRY = 0;
      PROBE = null; PF = null;     /* la sonde de couleur et le contrôle avant vol datent de l'ancien panneau */
      shell();
      paintIntents(); paintFormats(); paintIcc(); paintAudit(); paintPreflight(); paintGabarits();
      if (!h) wirePlanDrag();
    }
    if (!HEXA) return false;
    sync();
    refresh();
    return true;
  }

  """

ENTREES = [
    # la table des formats : un hexagone a son libellé traduit (la ligne rectangulaire est inchangée)
    S(F, 1006, 'esc(f.label.replace(/\\s*\\d.*$/, ""))',
      'esc(f.forme === "hex" && typeof CF.libelleFormat === "function" ? CF.libelleFormat(f.id)'
      ' : f.label.replace(/\\s*\\d.*$/, ""))', {}),
    S(F, 707, "function shell() {", _crlf("function shell() {\n    if (HEXA) { shellHex(); return; }"), {}),
    S(F, 1669, "function refresh(light) {",
      _crlf("function refresh(light) {\n    if (HEXA) { syncHex(); schedulePlanHex(); return; }"), {}),
    S(F, 1680, "async function verify() {", _crlf("async function verify() {\n    if (HEXA) return;"), {}),
    S(F, 1828, "function schedulePreflight() {", _crlf("function schedulePreflight() {\n    if (HEXA) return;"), {}),
    S(F, 1832, "async function preflight() {", _crlf("async function preflight() {\n    if (HEXA) return;"), {}),
    S(F, 2313, "function wire() {", _crlf(_BLOC) + "function wire() {", dict(_GABHEX, **_HEX)),
    S(F, 2314, 'HOST.addEventListener("click", (ev) => {',
      _crlf('HOST.addEventListener("click", (ev) => {\n      if (clicHex(ev)) return;'), {}),
    S(F, 2345, 'HOST.addEventListener("change", (ev) => {',
      _crlf('HOST.addEventListener("change", (ev) => {\n      if (changeHex(ev.target)) return;'), {}),
    S(F, 2392, "if (!visible()) return;", "if (!visible() || HEXA) return;", {}),
    S(F, 2475, "state: Object.assign({}, DEFAULTS),",
      _crlf("/* t421 : `hexa` = les réglages de la planche hexagonale, HORS DEFAULTS */\n"
            "    state: Object.assign({}, DEFAULTS, { hexa: {} }),"), {}),
    S(F, 2478, "HOST = host;", _crlf("HOST = host;\n      HEXA = estHex();"), {}),
    S(F, 2504, 'CF.on("core:geom", () => { paintFormats();',
      'CF.on("core:geom", () => { if (geomHex()) return; paintFormats();', {}),
]
