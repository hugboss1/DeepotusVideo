/* ═══════════════════════════════════════════════════════════════════════════
   js/depuis-images.js — t421 (cartes hexagonales, 07/11/2026, tâche 5)
   Le dialogue « Nouveau jeu depuis des images », ouvert par l'entrée du même
   nom de la galerie (core.js:galImages). Quatre temps (spec 2026-11-07,
   « L'écran de création ») :
     1. nom et format ;
     2. les images : grille de la Bibliothèque, recherche, filtre par projet,
        « Tout sélectionner », import depuis l'ordinateur (fichiers multiples) ;
     3. le verso : aucun, une image commune, ou l'appariement automatique ;
     4. le récapitulatif (cartes, écarts de rapport, rectos sans verso, versos
        orphelins, case « Mon fichier inclut le fond perdu » et l'avertissement
        de liseré quand elle est décochée), puis la création et l'ouverture.
   Le réseau est au CORE (§8 : aucun fetch dans une pièce) : CF.bibliotheque
   (images, projets, projet, importer, url) et CF.deckDepuisImages, qui crée
   le deck par POST /api/cards/decks/depuis-images puis l'ouvre par ?deck=.
   La logique pure (tri, appariement, rapports) est dans
   js/depuis-images-logique.js (window.CFImages).
   Le dialogue n'a pas l'API de window.__dzDialogue (messages seulement) : il
   reprend la structure de la galerie (voile fixe, boîte, tête, corps, pied).
   Tout texte affiché passe par dzT (cartes.depuis.*) ; tout ce qui vient du
   serveur (noms de fichiers, de projets, phrases d'erreur) par textContent.
   Aucun innerHTML.
   ═══════════════════════════════════════════════════════════════════════════ */
(function (g) {
  "use strict";
  const CF = g.CF, L = g.CFImages;
  if (!CF || !L) {
    console.error("depuis-images: js/core.js et js/depuis-images-logique.js doivent etre charges avant ce fichier");
    return;
  }
  const MAX = 500;                     /* le plafond de la route (IMAGES_MAX) */
  const SVG = "http://www.w3.org/2000/svg";
  let E = null;                        /* l'état du dialogue ouvert */

  /* ── petits outils de DOM ───────────────────────────────────────────────── */
  function el(tag, cls, txt) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = String(txt);
    return e;
  }
  function vider(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function icone(cle) {
    const s = document.createElementNS(SVG, "svg");
    s.setAttribute("class", "dzi dzi--16 cf-ic");
    s.setAttribute("aria-hidden", "true");
    s.setAttribute("focusable", "false");
    const u = document.createElementNS(SVG, "use");
    u.setAttribute("href", "/shared/icons/dz-icons.svg#" + cle);
    s.appendChild(u);
    return s;
  }
  function bouton(cls, txt, ic) {
    const b = el("button", "btn sm" + (cls ? " " + cls : ""));
    b.type = "button";
    if (ic) b.appendChild(icone(ic));
    b.appendChild(document.createTextNode(String(txt)));
    return b;
  }
  const msgErr = (e) => String((e && e.message) || e);
  /* un nombre dans la langue de l'interface : « 3,175 » en français, « 3.175 » en anglais */
  const nombre = (v) => Number(v).toLocaleString(typeof dzLang === "function" && dzLang() === "en" ? "en" : "fr",
    { maximumFractionDigits: 3 });
  /* recherche sans accent ni casse : « brisé » se trouve en tapant « brise » */
  const plat = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

  /* ── les formats ────────────────────────────────────────────────────────── */
  function fmtObj(id) {
    const f = CF.FORMATS.find((x) => x.id === id);
    return f ? { id: f.id, trim_mm: f.trim_mm, bleed_mm: CF.nativeBleed(f.id), forme: f.forme || "rect" } : null;
  }
  const FMTS = () => CF.FORMATS.map((f) => fmtObj(f.id));
  function fmtDepart() {
    let id = "";
    try { const d = CF.doc(); id = d && d.format && d.format.fmt; } catch (e) { id = ""; }
    return fmtObj(id) ? id : CF.FORMATS[0].id;
  }

  /* ── l'état ─────────────────────────────────────────────────────────────── */
  function etatNeuf() {
    return {
      etape: 1, nom: dzT("cartes.depuis.nom_defaut"), fmt: fmtDepart(), fmtManuel: false, fmtPropose: false,
      inclut: null,                      /* null = d'office (rapport des images) */
      biblio: [], parNom: {}, charge: false, erreurBiblio: "",
      sel: [], recherche: "", projet: "", projetRefs: null, projets: [],
      verso: "aucun", commun: "",
      importEnCours: false, importMsg: "", importErr: [],
      msg: "", creation: false, tuiles: {}, dom: null,
    };
  }
  const estChoisie = (n) => E.sel.indexOf(n) >= 0;
  function dimsDe(n) {
    const i = E.parNom[n];
    return { nom: n, w: i ? i.width : null, h: i ? i.height : null };
  }

  /* LE PLAN : ce que la route recevra, et ce que le récapitulatif en dit. */
  function plan() {
    const fmt = fmtObj(E.fmt);
    const choisies = L.triNaturel(E.sel);
    let images, versos = null, sansVerso = [], orphelins = [];
    if (E.verso === "apparie") {
      const P = L.apparier(choisies);
      images = P.cartes.map((c) => c.recto);
      versos = P.cartes.map((c) => c.verso);
      sansVerso = P.sansVerso;
      orphelins = P.orphelins;
    } else {
      /* le verso commun n'est pas une carte, même s'il est aussi coché */
      images = choisies.filter((n) => !(E.verso === "commun" && n === E.commun));
    }
    const dims = images.map(dimsDe);
    const r = L.rapportMedian(dims);
    const inclutAuto = r != null && L.inclutFondPerdu(r, 1, fmt, fmt.bleed_mm);
    const inclut = E.inclut == null ? inclutAuto : E.inclut;
    const corps = { name: String(E.nom || "").trim(), format: E.fmt, images: images, fond_perdu: inclut };
    if (versos) corps.versos = versos;
    if (E.verso === "commun" && E.commun) corps.verso_commun = E.commun;
    return {
      corps: corps, fmt: fmt, inclut: inclut, sansVerso: sansVerso, orphelins: orphelins,
      ecarts: L.ecarts(dims, fmt, inclut), avecVerso: versos ? versos.filter(Boolean).length : 0,
    };
  }
  function proposerFormat() {
    if (E.fmtManuel) return;
    const id = L.formatPropose(E.sel.map(dimsDe), FMTS());
    if (id && id !== E.fmt) { E.fmt = id; E.inclut = null; }
    E.fmtPropose = !!id;
  }

  /* ── ouvrir / fermer ────────────────────────────────────────────────────── */
  function surTouche(ev) {
    if (ev && ev.key === "Escape" && E && !E.creation) { ev.preventDefault(); fermer(); }
  }
  function fermer() {
    if (!E) return;
    if (E.dom && E.dom.root && E.dom.root.parentNode) E.dom.root.parentNode.removeChild(E.dom.root);
    document.removeEventListener("keydown", surTouche);
    E = null;
  }
  function ouvrir() {
    fermer();
    E = etatNeuf();
    construire();
    document.addEventListener("keydown", surTouche);
    rendre();
    chargerBiblio();
    CF.bibliotheque.projets().then((l) => { if (E) { E.projets = l; if (E.etape === 2) rendre(); } },
      () => { /* sans projets, le filtre reste sur toute la Bibliothèque */ });
    return true;
  }
  function chargerBiblio() {
    const moi = E;
    return CF.bibliotheque.images().then((l) => {
      if (E !== moi) return;
      E.biblio = l;
      E.parNom = {};
      l.forEach((i) => { E.parNom[i.filename] = i; });
      E.sel = E.sel.filter((n) => E.parNom[n]);
      E.charge = true;
      E.erreurBiblio = "";
      E.tuiles = {};
      E.dom.grille = null;
      rendre();
    }, (e) => {
      if (E !== moi) return;
      E.charge = true;
      E.erreurBiblio = msgErr(e);
      E.dom.grille = null;
      rendre();
    });
  }

  /* ── la boîte ───────────────────────────────────────────────────────────── */
  const ETAPES = () => [dzT("cartes.depuis.e1"), dzT("cartes.depuis.e2"), dzT("cartes.depuis.e3"), dzT("cartes.depuis.e4")];
  function construire() {
    const root = el("div", "cf-di");
    const box = el("div", "cf-di-box");
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", dzT("cartes.depuis.gal_titre"));
    const head = el("div", "cf-di-head");
    head.appendChild(el("b", null, dzT("cartes.depuis.gal_titre")));
    const etapes = el("ol", "cf-di-etapes");
    head.appendChild(etapes);
    const x = el("button", "btn ghost sm cf-di-fermer");
    x.type = "button";
    x.title = dzT("cartes.core.fermer_echap");
    x.setAttribute("aria-label", dzT("cartes.core.fermer_echap"));
    x.appendChild(icone("dz-action-fermer"));
    x.addEventListener("click", () => { if (!E.creation) fermer(); });
    head.appendChild(x);
    const corps = el("div", "cf-di-corps");
    const pied = el("div", "cf-di-pied");
    const msg = el("span", "cf-di-msg");
    msg.setAttribute("role", "status");
    const prec = bouton("ghost", dzT("cartes.depuis.precedent"));
    const suiv = bouton("strong", dzT("cartes.depuis.suivant"));
    prec.addEventListener("click", () => aller(E.etape - 1));
    suiv.addEventListener("click", () => { if (E.etape < 4) aller(E.etape + 1); else creer(); });
    pied.appendChild(msg);
    pied.appendChild(el("span", "tb-spacer"));
    pied.appendChild(prec);
    pied.appendChild(suiv);
    box.appendChild(head);
    box.appendChild(corps);
    box.appendChild(pied);
    root.appendChild(box);
    document.body.appendChild(root);
    E.dom = { root: root, etapes: etapes, corps: corps, msg: msg, prec: prec, suiv: suiv };
  }

  /* ce qui empêche de quitter une étape (null = rien) */
  function blocage(etape) {
    if (etape === 2) {
      if (!E.sel.length) return dzT("cartes.depuis.aucune_image");
      if (E.sel.length > MAX) return dzT("cartes.depuis.trop", { n: E.sel.length, max: MAX });
      if (E.importEnCours) return dzT("cartes.depuis.import_attendre");
    }
    if (etape === 3) {
      if (E.verso === "commun" && !E.commun) return dzT("cartes.depuis.verso_manque");
      if (!plan().corps.images.length) return dzT("cartes.depuis.aucune_carte");
    }
    return null;
  }
  function aller(n) {
    if (!E || n < 1 || n > 4) return;
    for (let k = E.etape; k < n; k++) {
      const b = blocage(k);
      if (b) { E.msg = b; rendre(); return; }
      if (k === 2) proposerFormat();
    }
    E.msg = "";
    E.etape = n;
    rendre();
  }

  function rendre() {
    if (!E || !E.dom) return;
    const D = E.dom;
    vider(D.etapes);
    ETAPES().forEach((t, i) => {
      const li = el("li", i + 1 === E.etape ? "cur" : i + 1 < E.etape ? "fait" : "");
      const b = el("button", "cf-di-etape");
      b.type = "button";
      b.appendChild(el("i", "mono", String(i + 1)));
      b.appendChild(document.createTextNode(t));
      b.disabled = E.creation;
      b.addEventListener("click", () => aller(i + 1));
      li.appendChild(b);
      D.etapes.appendChild(li);
    });
    /* l'étape 2 garde sa grille d'un rendu à l'autre (cocher une image ne
       recharge pas cinq cents vignettes) ; toute autre étape se refait. */
    if (E.etape !== 2 || !D.grille) {
      vider(D.corps);
      D.grille = null;
    }
    [null, etape1, etape2, etape3, etape4][E.etape](D.corps);
    D.msg.textContent = E.msg || "";
    D.msg.className = "cf-di-msg" + (E.msg ? " ko" : "");
    D.prec.disabled = E.etape === 1 || E.creation;
    vider(D.suiv);
    if (E.etape < 4) D.suiv.appendChild(document.createTextNode(dzT("cartes.depuis.suivant")));
    else { D.suiv.appendChild(icone("dz-action-ajouter")); D.suiv.appendChild(document.createTextNode(dzT("cartes.depuis.creer"))); }
    D.suiv.disabled = E.creation;
  }

  /* ── 1. nom et format ───────────────────────────────────────────────────── */
  function etape1(c) {
    const f1 = el("label", "cf-di-champ");
    f1.appendChild(el("span", "lbl", dzT("cartes.depuis.nom")));
    const nom = el("input");
    nom.type = "text";
    nom.maxLength = 80;
    nom.value = E.nom;
    nom.addEventListener("input", () => { E.nom = nom.value; });
    f1.appendChild(nom);
    c.appendChild(f1);
    const f2 = el("label", "cf-di-champ");
    f2.appendChild(el("span", "lbl", dzT("cartes.depuis.format")));
    const sel = el("select");
    [["hex", dzT("cartes.depuis.groupe_hex")], ["rect", dzT("cartes.depuis.groupe_rect")]].forEach(([forme, t]) => {
      const og = el("optgroup");
      og.label = t;
      CF.FORMATS.filter((f) => (f.forme || "rect") === forme).forEach((f) => {
        const o = el("option", null, CF.libelleFormat(f.id));
        o.value = f.id;
        og.appendChild(o);
      });
      sel.appendChild(og);
    });
    sel.value = E.fmt;
    sel.addEventListener("change", () => { E.fmt = sel.value; E.fmtManuel = true; E.fmtPropose = false; E.inclut = null; rendre(); });
    f2.appendChild(sel);
    c.appendChild(f2);
    if (E.fmtPropose) c.appendChild(el("p", "cf-di-note", dzT("cartes.depuis.format_propose", { format: CF.libelleFormat(E.fmt) })));
    c.appendChild(el("p", "cf-di-note", dzT("cartes.depuis.format_aide")));
    try { nom.focus(); } catch (e) { /* pas de focus */ }
  }

  /* ── 2. les images ──────────────────────────────────────────────────────── */
  function visible(i) {
    if (E.projetRefs && !E.projetRefs.has(i.filename)) return false;
    const q = plat(E.recherche).trim();
    return !q || plat(i.filename).indexOf(q) >= 0;
  }
  function tuile(i) {
    const b = el("button", "cf-di-tuile");
    b.type = "button";
    b.title = i.filename;
    const im = el("img");
    im.loading = "lazy";
    im.decoding = "async";
    im.alt = "";
    im.src = CF.bibliotheque.url(i.filename);
    b.appendChild(im);
    b.appendChild(el("span", "cf-di-nom", i.filename));
    if (i.width && i.height) b.appendChild(el("span", "cf-di-dims mono", dzT("cartes.depuis.dims", { w: i.width, h: i.height })));
    b.addEventListener("click", () => {
      const k = E.sel.indexOf(i.filename);
      if (k >= 0) E.sel.splice(k, 1); else E.sel.push(i.filename);
      E.msg = "";
      majTuile(b, i.filename);
      majCompte();
    });
    majTuile(b, i.filename);
    return b;
  }
  function majTuile(b, n) {
    const on = estChoisie(n);
    b.classList.toggle("on", on);
    b.setAttribute("aria-pressed", on ? "true" : "false");
  }
  function majCompte() {
    const D = E.dom;
    if (D.compte) D.compte.textContent = dzT("cartes.depuis.selection", { n: E.sel.length, total: E.biblio.length });
    if (D.msg) { D.msg.textContent = E.msg || ""; D.msg.className = "cf-di-msg" + (E.msg ? " ko" : ""); }
  }
  function filtrer() {
    const D = E.dom;
    let n = 0;
    E.biblio.forEach((i) => {
      const t = E.tuiles[i.filename];
      if (!t) return;
      const v = visible(i);
      t.hidden = !v;
      if (v) n++;
    });
    if (D.vide) D.vide.hidden = n > 0 || !E.biblio.length;
  }
  function etape2(c) {
    const D = E.dom;
    if (D.grille) {                    /* la grille reste : seuls les comptes et les filtres bougent */
      majOutils();
      majCompte();
      filtrer();
      return;
    }
    const outils = el("div", "cf-di-outils");
    const q = el("input", "cf-di-recherche");
    q.type = "search";
    q.placeholder = dzT("cartes.depuis.recherche_ph");
    q.setAttribute("aria-label", dzT("cartes.depuis.recherche_ph"));
    q.value = E.recherche;
    q.addEventListener("input", () => { E.recherche = q.value; filtrer(); });
    outils.appendChild(q);
    const pj = el("select", "cf-di-projet");
    pj.setAttribute("aria-label", dzT("cartes.depuis.projet"));
    pj.addEventListener("change", () => choisirProjet(pj.value));
    outils.appendChild(pj);
    const tout = bouton("", dzT("cartes.depuis.tout"));
    tout.addEventListener("click", () => {
      E.biblio.forEach((i) => { if (visible(i) && !estChoisie(i.filename)) E.sel.push(i.filename); });
      E.msg = "";
      Object.keys(E.tuiles).forEach((n) => majTuile(E.tuiles[n], n));
      majCompte();
    });
    outils.appendChild(tout);
    const rien = bouton("ghost", dzT("cartes.depuis.rien"));
    rien.addEventListener("click", () => {
      E.sel = [];
      Object.keys(E.tuiles).forEach((n) => majTuile(E.tuiles[n], n));
      majCompte();
    });
    outils.appendChild(rien);
    const fic = el("input", "cf-di-fichiers");
    fic.type = "file";
    fic.multiple = true;
    fic.accept = "image/png,image/jpeg,image/webp";
    fic.hidden = true;
    fic.addEventListener("change", () => { const l = Array.prototype.slice.call(fic.files || []); fic.value = ""; importer(l); });
    const imp = bouton("", dzT("cartes.depuis.importer"), "dz-action-importer");
    imp.addEventListener("click", () => fic.click());
    outils.appendChild(imp);
    outils.appendChild(fic);
    c.appendChild(outils);
    const ligne = el("div", "cf-di-ligne");
    D.compte = el("span", "cf-di-compte");
    D.etatImport = el("span", "cf-di-import");
    ligne.appendChild(D.compte);
    ligne.appendChild(D.etatImport);
    c.appendChild(ligne);
    D.projetSel = pj;
    D.importBtn = imp;
    const grille = el("div", "cf-di-grille");
    D.grille = grille;
    if (!E.charge) grille.appendChild(el("p", "cf-di-note", dzT("cartes.depuis.chargement")));
    else if (E.erreurBiblio) grille.appendChild(el("p", "cf-di-note ko", dzT("cartes.depuis.biblio_indispo", { err: E.erreurBiblio })));
    else if (!E.biblio.length) grille.appendChild(el("p", "cf-di-note", dzT("cartes.depuis.biblio_vide")));
    else {
      L.triNaturel(E.biblio.map((i) => i.filename)).forEach((n) => {
        const t = tuile(E.parNom[n]);
        E.tuiles[n] = t;
        grille.appendChild(t);
      });
    }
    D.vide = el("p", "cf-di-note", dzT("cartes.depuis.aucune_correspondance"));
    D.vide.hidden = true;
    c.appendChild(grille);
    c.appendChild(D.vide);
    majOutils();
    majCompte();
    filtrer();
  }
  function majOutils() {
    const D = E.dom;
    if (D.projetSel) {
      vider(D.projetSel);
      const o0 = el("option", null, dzT("cartes.depuis.projet_tous"));
      o0.value = "";
      D.projetSel.appendChild(o0);
      E.projets.forEach((p) => {
        const o = el("option", null, p.nom + " (" + p.n + ")");
        o.value = p.id;
        D.projetSel.appendChild(o);
      });
      D.projetSel.value = E.projet;
    }
    if (D.importBtn) D.importBtn.disabled = E.importEnCours;
    if (D.etatImport) {
      D.etatImport.textContent = E.importMsg;
      D.etatImport.className = "cf-di-import" + (E.importErr.length ? " ko" : "");
      D.etatImport.title = E.importErr.join("\n");
    }
  }
  function choisirProjet(id) {
    E.projet = id;
    if (!id) { E.projetRefs = null; filtrer(); return; }
    const moi = E;
    CF.bibliotheque.projet(id).then((p) => {
      if (E !== moi || E.projet !== id) return;
      E.projetRefs = new Set(p.refs);
      filtrer();
    }, (e) => {
      if (E !== moi) return;
      E.msg = dzT("cartes.depuis.projet_indispo", { err: msgErr(e) });
      E.projet = "";
      E.projetRefs = null;
      rendre();
    });
  }
  /* un fichier par appel (la route d'import n'en prend qu'un) ; le nom RENDU
     fait foi : un homonyme devient « nom-1.png ». La liste est relue à la fin
     (dimensions comprises) et les images importées sont cochées. */
  async function importer(fichiers) {
    if (!E || !fichiers.length || E.importEnCours) return;
    const moi = E;
    E.importEnCours = true;
    E.importErr = [];
    const noms = [];
    for (let k = 0; k < fichiers.length; k++) {
      if (E !== moi) return;
      E.importMsg = dzT("cartes.depuis.import_cours", { i: k + 1, n: fichiers.length });
      majOutils();
      try {
        const r = await CF.bibliotheque.importer(fichiers[k]);
        if (r && r.filename) noms.push(r.filename);
      } catch (e) {
        E.importErr.push(dzT("cartes.depuis.import_echec", { nom: String(fichiers[k] && fichiers[k].name), err: msgErr(e) }));
      }
    }
    if (E !== moi) return;
    E.importEnCours = false;
    E.importMsg = E.importErr.length
      ? dzT("cartes.depuis.import_bilan_ko", { n: noms.length, ko: E.importErr.length })
      : dzT("cartes.depuis.import_bilan", { n: noms.length });
    noms.forEach((n) => { if (!estChoisie(n)) E.sel.push(n); });
    await chargerBiblio();             /* la grille se refait avec les nouvelles */
    if (E === moi) majOutils();
  }

  /* ── 3. le verso ────────────────────────────────────────────────────────── */
  function etape3(c) {
    const modes = [
      ["aucun", dzT("cartes.depuis.verso_aucun"), dzT("cartes.depuis.verso_aucun_aide")],
      ["commun", dzT("cartes.depuis.verso_commun"), dzT("cartes.depuis.verso_commun_aide")],
      ["apparie", dzT("cartes.depuis.verso_apparie"), dzT("cartes.depuis.verso_apparie_aide")],
    ];
    const fs = el("div", "cf-di-modes");
    fs.setAttribute("role", "radiogroup");
    fs.setAttribute("aria-label", dzT("cartes.depuis.e3"));
    modes.forEach(([v, t, aide]) => {
      const lab = el("label", "cf-di-mode" + (E.verso === v ? " on" : ""));
      const r = el("input");
      r.type = "radio";
      r.name = "cfDiVerso";
      r.value = v;
      r.checked = E.verso === v;
      r.addEventListener("change", () => { E.verso = v; E.msg = ""; rendre(); });
      lab.appendChild(r);
      const tx = el("span", "cf-di-mode-t");
      tx.appendChild(el("b", null, t));
      tx.appendChild(el("span", "cf-di-note", aide));
      lab.appendChild(tx);
      fs.appendChild(lab);
    });
    c.appendChild(fs);
    if (E.verso === "commun") {
      const f = el("label", "cf-di-champ");
      f.appendChild(el("span", "lbl", dzT("cartes.depuis.verso_image")));
      const s = el("select");
      const o0 = el("option", null, dzT("cartes.depuis.verso_choisir"));
      o0.value = "";
      s.appendChild(o0);
      L.triNaturel(E.biblio.map((i) => i.filename)).forEach((n) => {
        const o = el("option", null, n);
        o.value = n;
        s.appendChild(o);
      });
      s.value = E.commun;
      s.addEventListener("change", () => { E.commun = s.value; E.msg = ""; rendre(); });
      f.appendChild(s);
      c.appendChild(f);
      if (E.commun) {
        const im = el("img", "cf-di-apercu");
        im.alt = "";
        im.src = CF.bibliotheque.url(E.commun);
        c.appendChild(im);
      }
    }
    if (E.verso === "apparie") {
      const P = plan();
      c.appendChild(el("p", "cf-di-note", dzT("cartes.depuis.apparie_bilan", { n: P.corps.images.length, p: P.avecVerso })));
      liste(c, dzT("cartes.depuis.sans_verso", { n: P.sansVerso.length }), P.sansVerso, "");
      liste(c, dzT("cartes.depuis.orphelins", { n: P.orphelins.length }), P.orphelins, "");
    }
  }
  /* une liste de noms repliable ; rien si elle est vide */
  function liste(c, titre, noms, cls) {
    if (!noms.length) return;
    const d = el("details", "cf-di-liste" + (cls ? " " + cls : ""));
    d.appendChild(el("summary", null, titre));
    const ul = el("ul");
    noms.forEach((n) => ul.appendChild(el("li", "mono", n)));
    d.appendChild(ul);
    c.appendChild(d);
  }

  /* ── 4. le récapitulatif ────────────────────────────────────────────────── */
  /* Le gabarit de dessin d'un format hexagonal (GET /api/cards/gabarit/{format}.{png|svg}) : un PNG
     transparent et un SVG en mm, avec la coupe, le fond perdu, la zone sûre et le milieu des côtés. Deux
     liens de téléchargement, pas des appels : le fond fait 0 mm si le fichier de l'utilisateur n'en a pas. */
  function lienGabarit(fmtId, ext, avecFondPerdu) {
    const a = el("a", "btn sm");
    a.setAttribute("href", CF.gabaritUrl(fmtId, ext, avecFondPerdu ? null : { bleed_mm: 0 }));
    a.setAttribute("download", "");
    a.appendChild(icone("dz-action-telecharger"));
    a.appendChild(document.createTextNode(ext === "svg" ? dzT("cartes.depuis.gabarit_svg") : dzT("cartes.depuis.gabarit_png")));
    return a;
  }
  function blocGabarit(fmtId, avecFondPerdu) {
    const b = el("div", "cf-di-gabarit");
    b.appendChild(el("b", null, dzT("cartes.depuis.gabarit_titre")));
    b.appendChild(el("span", "cf-di-note", dzT("cartes.depuis.gabarit_aide")));
    const l = el("div", "cf-di-gabarit-liens");
    l.appendChild(lienGabarit(fmtId, "png", avecFondPerdu));
    l.appendChild(lienGabarit(fmtId, "svg", avecFondPerdu));
    b.appendChild(l);
    return b;
  }

  function etape4(c) {
    const P = plan();
    const dl = el("dl", "cf-di-recap");
    const ligne = (k, v) => { dl.appendChild(el("dt", null, k)); dl.appendChild(el("dd", null, v)); };
    ligne(dzT("cartes.depuis.recap_nom"), P.corps.name || dzT("cartes.depuis.nom_defaut"));
    ligne(dzT("cartes.depuis.recap_cartes"), String(P.corps.images.length));
    ligne(dzT("cartes.depuis.format"), CF.libelleFormat(E.fmt));
    const mode = { aucun: dzT("cartes.depuis.verso_aucun"), commun: dzT("cartes.depuis.verso_commun"),
                   apparie: dzT("cartes.depuis.verso_apparie") }[E.verso];
    ligne(dzT("cartes.depuis.e3"), E.verso === "commun" ? mode + " — " + E.commun : mode);
    c.appendChild(dl);
    if (P.fmt.forme === "hex") c.appendChild(blocGabarit(P.fmt.id, P.inclut));
    if (E.fmtPropose) c.appendChild(el("p", "cf-di-note", dzT("cartes.depuis.format_propose", { format: CF.libelleFormat(E.fmt) })));
    const fp = el("label", "cf-di-case");
    const cb = el("input");
    cb.type = "checkbox";
    cb.checked = P.inclut;
    cb.addEventListener("change", () => { E.inclut = !!cb.checked; rendre(); });
    fp.appendChild(cb);
    const t = el("span");
    t.appendChild(el("b", null, dzT("cartes.depuis.fond_perdu")));
    t.appendChild(el("span", "cf-di-note", dzT("cartes.depuis.fond_perdu_aide", { mm: nombre(P.fmt.bleed_mm) })));
    fp.appendChild(t);
    c.appendChild(fp);
    if (!P.inclut) c.appendChild(el("p", "cf-di-avert", dzT("cartes.depuis.lisere")));
    liste(c, dzT("cartes.depuis.ecarts", { n: P.ecarts.length }), L.triNaturel(P.ecarts), "avert");
    liste(c, dzT("cartes.depuis.sans_verso", { n: P.sansVerso.length }), P.sansVerso, "avert");
    liste(c, dzT("cartes.depuis.orphelins", { n: P.orphelins.length }), P.orphelins, "avert");
    /* l'ordre des cartes, tel que le deck le recevra (il se reprend dans Données) */
    const d = el("details", "cf-di-liste");
    d.appendChild(el("summary", null, dzT("cartes.depuis.ordre", { n: P.corps.images.length })));
    const ol = el("ol");
    P.corps.images.forEach((n) => ol.appendChild(el("li", null, L.nomCarte(n))));
    d.appendChild(ol);
    c.appendChild(d);
  }

  async function creer() {
    if (!E || E.creation) return;
    const b = blocage(2) || blocage(3);
    if (b) { E.msg = b; rendre(); return; }
    const P = plan();
    E.creation = true;
    E.msg = "";
    rendre();
    try {
      CF.busy(true, dzT("cartes.depuis.creation", { n: P.corps.images.length }));
      await CF.deckDepuisImages(P.corps);  /* le CORE ouvre le deck : la page part */
    } catch (e) {
      CF.busy(false);
      if (!E) return;
      E.creation = false;
      E.msg = msgErr(e);
      rendre();
    }
  }

  g.CFDepuisImages = Object.freeze({ ouvrir: ouvrir, fermer: fermer, ouvert: () => !!E });
})(window);
