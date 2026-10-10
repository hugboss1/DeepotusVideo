/* ═══════════════════════════════════════════════════════════════════════════
   Card Forge — piece 11 · Edition   [P11]   (tache #84, plan-cartes T5)
   Proprietaire exclusif de : doc.edition · aucun z · /api/cards/<did>/edition/*
   Prefixe DOM impose : id="cf-edition-..."   ·   feuille : css/mod-edition.css
   (tout selecteur y contient .cf-edition)

   CE QUE CETTE PIECE NE FAIT PAS : dessiner une carte. Elle ASSEMBLE des
   cartes rendues par CF.renderCard (via CF.cardBlob) et les televerse. Elle
   livre ce qui entoure le jeu : la table virtuelle (Tabletop Simulator,
   Tabletopia), le livret de regles, le mockup et la fiche produit (tache #87).
   ═══════════════════════════════════════════════════════════════════════════ */
"use strict";

(function () {
  const CF = (typeof window !== "undefined") ? window.CF : null;
  if (!CF) throw new Error("mod-edition: js/core.js doit etre charge avant ce fichier");

  /* icônes G2 (10/10/2026) : la suite « Deepotus Glyph » passe par le CORE
     (CF.icone), gardé `typeof` comme CF.chevronSVG — un CF de paille (bancs
     node) rend un marqueur qui porte la clé. */
  const ICO = (k, t, c) => (typeof CF.icone === "function" ? CF.icone(k, t, c)
    : '<i class="dzi" data-cle="' + k + '"></i>');

  const esc = (s) => String(s == null ? "" : s).replace(/&/g, "&amp;")
    .replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

  let M = null, HOST = null, CIBLES = [], DERNIER = null, VERROU = false;

  const DEFAULTS = {
    cible: "tts",      /* tts | tabletopia */
    /* tache #87 PR C : livret, mockup — les reglages restent avec le jeu */
    livret_titre: "", livret_texte: "", livret_feuille: "a5", livret_fonte: "", livret_planche: true,
    mockup_cible: "carre", mockup_titre: "", mockup_sous_titre: "",
  };
  let POLICES = [], FICHE = null;

  function shell() {
    HOST.innerHTML = ''
      + '<details class="grp" open><summary>' + dzT("cartes.edition.table_virtuelle") + '</summary>'
      + '<div class="grp-body">'
      + '<div class="cf-edition-cibles" data-role="cibles"></div>'
      + '<p class="hint">' + dzT("cartes.edition.cibles_hint") + '</p>'
      + '<div class="cf-edition-actions" data-role="tts">'
      + '<button type="button" class="btn strong" data-act="tts" title="' + dzT("cartes.edition.tts_t") + '">' + ICO("dz-action-exporter", 16, "cf-ic") + dzT("cartes.edition.tts") + '</button>'
      + '<button type="button" class="btn" data-act="tts-poser" title="' + dzT("cartes.edition.poser_t") + '">' + ICO("dz-action-envoyer-vers", 16, "cf-ic") + dzT("cartes.edition.poser") + '</button>'
      + '</div>'
      + '<p class="cf-edition-etat" data-role="tts-etat"></p>'
      + '<div class="cf-edition-actions" data-role="tabletopia">'
      + '<button type="button" class="btn strong" data-act="tabletopia" title="' + dzT("cartes.edition.tabletopia_t") + '">' + ICO("dz-action-exporter", 16, "cf-ic") + dzT("cartes.edition.tabletopia") + '</button>'
      + '</div>'
      + '</div></details>'

      /* LIVRET (tache #87 PR C, plan-cartes T18) : l'ecart est DIT ici, et dans l'en-tete du fichier. */
      + '<details class="grp"><summary>' + dzT("cartes.edition.livret_titre") + '</summary><div class="grp-body">'
      + '<input class="cf-edition-champ" data-k="livret_titre" placeholder="' + dzT("cartes.edition.titre_ph") + '" title="' + dzT("cartes.edition.titre_page") + '">'
      + '<textarea class="cf-edition-texte" data-k="livret_texte" rows="10" placeholder="' + dzT("cartes.edition.texte_ph") + '" title="' + dzT("cartes.edition.texte_t") + '"></textarea>'
      + '<div class="cf-edition-actions">'
      + '<select data-k="livret_feuille" title="' + dzT("cartes.edition.feuille_t") + '"><option value="a5">A5</option><option value="a4">A4</option><option value="carre">' + dzT("cartes.edition.carre_210") + '</option></select>'
      + '<select data-k="livret_fonte" data-role="polices" title="' + dzT("cartes.edition.fonte_t") + '"></select>'
      + '<label title="' + dzT("cartes.edition.planche_t") + '"><input type="checkbox" data-k="livret_planche"> ' + dzT("cartes.edition.planche") + '</label>'
      + '<button type="button" class="btn strong" data-act="livret" title="' + dzT("cartes.edition.livret_t") + '">' + dzT("cartes.edition.livret_pdf") + '</button>'
      + '</div>'
      + '<p class="hint">' + dzT("cartes.edition.livret_hint") + '</p>'
      + '<p class="cf-edition-etat" data-role="livret-etat"></p>'
      + '</div></details>'

      /* MOCKUP ET FICHE (tache #87 PR C, plan-cartes T19) */
      + '<details class="grp"><summary>' + dzT("cartes.edition.mockup_titre") + '</summary><div class="grp-body">'
      + '<div class="cf-edition-actions">'
      + '<select data-k="mockup_cible" title="' + dzT("cartes.edition.visuel_t") + '"><option value="carre">' + dzT("cartes.edition.carre_1080") + '</option>'
      + '<option value="story">Story 1080 x 1920</option><option value="paysage">' + dzT("cartes.edition.paysage") + '</option></select>'
      + '<input class="cf-edition-champ" data-k="mockup_titre" placeholder="' + dzT("cartes.edition.titre_ph") + '" title="' + dzT("cartes.edition.titre_visuel") + '">'
      + '<input class="cf-edition-champ" data-k="mockup_sous_titre" placeholder="' + dzT("cartes.edition.sous_titre") + '" title="' + dzT("cartes.edition.sous_titre_t") + '">'
      + '<button type="button" class="btn strong" data-act="mockup" title="' + dzT("cartes.edition.mockup_t") + '">Mockup PNG</button>'
      + '<button type="button" class="btn" data-act="fiche" title="' + dzT("cartes.edition.fiche_t") + '">' + dzT("cartes.edition.fiche") + '</button>'
      + '</div>'
      + '<p class="hint">' + dzT("cartes.edition.mockup_hint") + '</p>'
      + '<p class="cf-edition-etat" data-role="mockup-etat"></p>'
      + '<div data-role="fiche"></div>'
      + '</div></details>';
  }

  /* ══ LIVRET, MOCKUP, FICHE (tache #87 PR C) ══════════════════════════════ */
  function ed() { return Object.assign({}, DEFAULTS, CF.doc().edition || {}); }
  function etatDe(role, txt) {
    const p = HOST && HOST.querySelector('[data-role="' + role + '"]');
    if (p) p.textContent = txt || "";
  }
  function paintReglages() {
    const e = ed();
    const sel = HOST && HOST.querySelector('[data-role="polices"]');
    if (sel) sel.innerHTML = '<option value="">' + dzT("cartes.edition.fonte_defaut") + '</option>'
      + POLICES.map((f) => '<option value="' + esc(f) + '"' + (f === e.livret_fonte ? " selected" : "") + ">"
        + esc(f.replace(/\.(ttf|otf)$/i, "")) + "</option>").join("");
    (HOST ? HOST.querySelectorAll("[data-k]") : []).forEach((el) => {
      const k = el.getAttribute("data-k");
      if (el.type === "checkbox") el.checked = !!e[k];
      else if (document.activeElement !== el && k !== "livret_fonte") el.value = e[k] == null ? "" : String(e[k]);
    });
  }
  function reglage(el) {
    const k = el.getAttribute("data-k");
    if (!Object.prototype.hasOwnProperty.call(DEFAULTS, k)) return;
    const v = el.type === "checkbox" ? !!el.checked : String(el.value || "");
    const o = {}; o[k] = v;
    M.patch(o);
  }
  async function livretPdf() {
    if (VERROU) return;
    const e = ed();
    if (!String(e.livret_texte || "").trim()) { CF.toast(dzT("cartes.edition.texte_requis"), true); return; }
    VERROU = true;
    try {
      const fd = new FormData();
      fd.append("spec", JSON.stringify({ titre: e.livret_titre || CF.doc().name || "", texte: e.livret_texte,
                                         feuille: e.livret_feuille, fonte: e.livret_fonte }));
      const cards = e.livret_planche ? CF.cards().slice(0, 120) : [];
      for (let i = 0; i < cards.length; i++) {
        CF.busy(true, dzT("cartes.edition.rendu_planche", { n: i + 1, total: cards.length }));
        fd.append("images", await CF.cardBlob(i, { face: "front" }), "c" + (i + 1) + ".png");
      }
      CF.busy(true, dzT("cartes.edition.composition"));
      const out = await M.api.blob("POST", "livret", fd);
      CF.download(out, slugJeu() + "_livret.pdf");
      etatDe("livret-etat", (cards.length ? dzT("cartes.edition.livret_ok_planche", { fichier: slugJeu() + "_livret.pdf", n: cards.length }) : dzT("cartes.edition.livret_ok", { fichier: slugJeu() + "_livret.pdf" })));
    } catch (er) {
      CF.toast(dzT("cartes.edition.livret_ko", { err: String((er && er.message) || er) }), true);
    } finally { CF.busy(false); VERROU = false; }
  }
  async function mockupPng() {
    if (VERROU) return;
    const cards = CF.cards();
    if (!cards.length) { CF.toast(dzT("cartes.edition.rien_a_montrer"), true); return; }
    VERROU = true;
    try {
      const e = ed();
      const n = Math.min(5, cards.length);
      const fd = new FormData();
      fd.append("spec", JSON.stringify({ cible: e.mockup_cible, titre: e.mockup_titre || CF.doc().name || "",
                                         sous_titre: e.mockup_sous_titre, fonte: e.livret_fonte }));
      for (let i = 0; i < n; i++) {
        CF.busy(true, dzT("cartes.edition.rendu_n", { n: i + 1, total: n }));
        fd.append("images", await CF.cardBlob(i, { face: "front" }), "c" + (i + 1) + ".png");
      }
      CF.busy(true, "mockup…");
      const out = await M.api.blob("POST", "mockup", fd);
      CF.download(out, slugJeu() + "_mockup_" + e.mockup_cible + ".png");
      etatDe("mockup-etat", dzT("cartes.edition.mockup_ok", { cible: e.mockup_cible, n: n })
        + (cards.length > n ? dzT("cartes.edition.mockup_premieres", { n: n, total: cards.length }) : "") + ".");
    } catch (er) {
      CF.toast(dzT("cartes.edition.mockup_ko", { err: String((er && er.message) || er) }), true);
    } finally { CF.busy(false); VERROU = false; }
  }
  async function ficheProduit() {
    if (VERROU) return;
    VERROU = true;
    try {
      FICHE = await M.api.post("fiche", { cartes: CF.cards().length || 1 });
      paintFiche();
    } catch (er) {
      CF.toast(dzT("cartes.edition.fiche_ko", { err: String((er && er.message) || er) }), true);
    } finally { VERROU = false; }
  }
  function paintFiche() {
    const box = HOST && HOST.querySelector('[data-role="fiche"]');
    if (!box || !FICHE) return;
    const f = FICHE, mm = (v) => String(v).replace(".", ",");
    box.innerHTML = '<table class="cf-edition-fiche"><tbody>'
      + "<tr><th>" + dzT("cartes.edition.th_cartes") + "</th><td>" + f.cartes + "</td></tr>"
      + "<tr><th>Format</th><td>" + esc(f.format) + " — " + mm(f.dimensions_mm[0]) + " x " + mm(f.dimensions_mm[1]) + " mm</td></tr>"
      + "<tr><th>" + dzT("cartes.edition.th_paquet") + "</th><td>" + mm(f.epaisseur_deck_mm) + " mm (" + mm(f.epaisseur_carte_mm) + " mm " + dzT("cartes.edition.par_carte") + ")</td></tr>"
      + "<tr><th>" + dzT("cartes.edition.th_boite") + "</th><td>" + (f.boite_mm ? f.boite_mm.map(mm).join(" x ") + " mm" : "—") + "</td></tr>"
      + "<tr><th>" + dzT("cartes.edition.th_langues") + "</th><td>" + (f.langues.length ? esc(f.langues.join(", ")) : dzT("cartes.edition.langues_absentes")) + "</td></tr>"
      + "</tbody></table>"
      + '<textarea class="cf-edition-texte" rows="3" readonly title="' + dzT("cartes.edition.fiche_texte_t") + '">' + esc(f.texte) + "</textarea>";
  }

  function paintCibles() {
    const box = HOST && HOST.querySelector('[data-role="cibles"]');
    if (!box) return;
    const cur = CF.doc().edition && CF.doc().edition.cible || DEFAULTS.cible;
    box.innerHTML = CIBLES.map((c) =>
      '<button type="button" class="cf-edition-cible' + (c.id === cur ? " on" : "")
      + '" data-act="cible" data-v="' + esc(c.id) + '" title="' + esc(dzT("cartes.edition.cible_t", { cible: c.label, date: c.verifie })) + '"><b>' + esc(c.label) + '</b><i>' + esc(c.note) + '</i></button>').join("");
  }

  /* Le nom d'une carte, pour le surnom TTS. RECOPIE (regle 8) de mod-print.js,
     plus un repli mesure sur 8799 : une carte sans donnee montre le texte par
     defaut du bloc « title » de P3 — c'est lui qu'on lit (lecture seule), pas
     son identifiant. */
  function cardName(c) {
    const f = c.fields || {};
    const t = CF.doc().type, s = (t && Array.isArray(t.slots)) ? t.slots.filter((x) => x && x.id === "title")[0] : null;
    return String(f.title || f.name || f.nom || (s && s.text) || c.id || ("carte " + (c.i + 1)));
  }
  function slugJeu() {
    return String(CF.doc().name || "jeu").normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
      .replace(/[^A-Za-z0-9]+/g, "-").replace(/^-+|-+$/g, "").toLowerCase().slice(0, 48) || "jeu";
  }
  function etat(txt) {
    const p = HOST && HOST.querySelector('[data-role="tts-etat"]');
    if (p) p.textContent = txt || "";
  }
  function paintTts() {
    const box = HOST && HOST.querySelector('[data-role="tts"]');
    const cur = CF.doc().edition && CF.doc().edition.cible || DEFAULTS.cible;
    if (box) box.classList.toggle("hidden", cur !== "tts");
    const tt = HOST && HOST.querySelector('[data-role="tabletopia"]');
    if (tt) tt.classList.toggle("hidden", cur !== "tabletopia");
    const pose = HOST && HOST.querySelector('[data-act="tts-poser"]');
    if (pose) pose.disabled = !DERNIER;
  }
  /* TABLETOP SIMULATOR : le navigateur rend (recto + verso), le backend coupe,
     assemble et ecrit. Un verrou : un double clic ne lance pas deux exports. */
  async function exporterTts() {
    if (VERROU) return;
    const cards = CF.cards();
    if (!cards.length) { CF.toast(dzT("cartes.edition.rien_a_exporter"), true); return; }
    VERROU = true;
    try {
      const fd = new FormData();
      fd.append("spec", JSON.stringify({ noms: cards.map(cardName) }));
      for (let i = 0; i < cards.length; i++) {
        CF.busy(true, dzT("cartes.edition.rendu_rv", { n: i + 1, total: cards.length }));
        fd.append("fronts", await CF.cardBlob(i, { face: "front" }), "f" + (i + 1) + ".png");
        fd.append("backs", await CF.cardBlob(i, { face: "back" }), "b" + (i + 1) + ".png");
      }
      CF.busy(true, dzT("cartes.edition.planches_tts"));
      const out = await M.api.blob("POST", "tts", fd);
      const nom = slugJeu() + "_tts.zip";
      CF.download(out, nom);
      DERNIER = { cartes: cards.length, nom: nom };
      etat(dzT("cartes.edition.tts_ok", { n: cards.length, nom: nom }));
      CF.toast(dzT("cartes.edition.tts_n", { n: cards.length }));
    } catch (e) {
      CF.toast(dzT("cartes.edition.tts_ko", { err: String((e && e.message) || e) }), true);
    } finally { CF.busy(false); VERROU = false; paintTts(); }
  }
  /* TABLETOPIA : meme rendu (recto + verso), un fichier par face cote backend. */
  async function exporterTabletopia() {
    if (VERROU) return;
    const cards = CF.cards();
    if (!cards.length) { CF.toast(dzT("cartes.edition.rien_a_exporter"), true); return; }
    VERROU = true;
    try {
      const fd = new FormData();
      fd.append("spec", JSON.stringify({ noms: cards.map(cardName) }));
      for (let i = 0; i < cards.length; i++) {
        CF.busy(true, dzT("cartes.edition.rendu_rv", { n: i + 1, total: cards.length }));
        fd.append("fronts", await CF.cardBlob(i, { face: "front" }), "f" + (i + 1) + ".png");
        fd.append("backs", await CF.cardBlob(i, { face: "back" }), "b" + (i + 1) + ".png");
      }
      CF.busy(true, dzT("cartes.edition.images_tabletopia"));
      const out = await M.api.blob("POST", "tabletopia", fd);
      const nom = slugJeu() + "_tabletopia.zip";
      CF.download(out, nom);
      etat(dzT("cartes.edition.tabletopia_ok", { n: cards.length, nom: nom }));
      CF.toast(dzT("cartes.edition.tabletopia_n", { n: cards.length }));
    } catch (e) {
      CF.toast(dzT("cartes.edition.tabletopia_ko", { err: String((e && e.message) || e) }), true);
    } finally { CF.busy(false); VERROU = false; }
  }
  async function poserTts() {
    if (VERROU || !DERNIER) return;
    VERROU = true;
    try {
      const r = await M.api.post("tts/poser", {});
      etat(dzT("cartes.edition.pose", { chemin: r.chemin }));
      CF.toast(dzT("cartes.edition.pose_court"));
    } catch (e) {
      etat(String((e && e.message) || e));
      CF.toast(String((e && e.message) || e), true);
    } finally { VERROU = false; }
  }

  function wire() {
    HOST.addEventListener("click", (ev) => {
      const t = ev.target.closest("[data-act]");
      if (!t) return;
      if (t.dataset.act === "cible") { M.patch({ cible: String(t.dataset.v) }); paintCibles(); paintTts(); }
      else if (t.dataset.act === "tts") exporterTts();
      else if (t.dataset.act === "tts-poser") poserTts();
      else if (t.dataset.act === "tabletopia") exporterTabletopia();
      else if (t.dataset.act === "livret") livretPdf();
      else if (t.dataset.act === "mockup") mockupPng();
      else if (t.dataset.act === "fiche") ficheProduit();
    });
    HOST.addEventListener("change", (ev) => {
      const el = ev.target.closest ? ev.target.closest("[data-k]") : null;
      if (el) reglage(el);
    });
  }

  M = CF.register({
    id: "edition",
    title: dzT("cartes.edition.titre"),
    icon: "dz-nav-cf-edition",
    order: 11,

    /* Aucun z n'est alloue a cette piece : elle ne dessine pas la carte. */
    painters: [],

    /* LE SCHEMA : ces cles sont les SEULES que M.patch({...}) acceptera. */
    state: Object.assign({}, DEFAULTS),

    async init(host) {
      HOST = host;
      shell();
      wire();
      try {
        const r = await M.api.get("cibles");
        if (r && Array.isArray(r.cibles)) CIBLES = r.cibles;
      } catch (e) {
        if (!(e && e.missing)) console.warn("cardforge/edition: cibles", e);
      }
      try {
        const r = await M.api.get("polices");
        if (r && Array.isArray(r.polices)) POLICES = r.polices;
      } catch (e) {
        if (!(e && e.missing)) console.warn("cardforge/edition: polices", e);
      }
      paintCibles();
      paintTts();
      paintReglages();
      CF.on("core:doc", (p) => { if (!p || p.id === "edition") { paintCibles(); paintTts(); paintReglages(); } });
      M.emit("ready", {});
    },
  });
})();
