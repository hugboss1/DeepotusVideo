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
      + '<details class="grp" open><summary>Table virtuelle — Tabletop Simulator, Tabletopia</summary>'
      + '<div class="grp-body">'
      + '<div class="cf-edition-cibles" data-role="cibles"></div>'
      + '<p class="hint">Chaque cible dit ce que son éditeur publie (relu le 04/10/2026) : '
      + 'la carte est exportée telle que le Card Forge la rend, à la coupe.</p>'
      + '<div class="cf-edition-actions" data-role="tts">'
      + '<button type="button" class="btn strong" data-act="tts" title="Planches 10 x 7 à la coupe (4096 px au plus) et objet sauvegardé qui pointe vers elles, sur ce PC — un ZIP de tout">' + ICO("dz-action-exporter", 16, "cf-ic") + 'Exporter pour Tabletop Simulator (.zip)</button>'
      + '<button type="button" class="btn" data-act="tts-poser" title="Copier le dernier objet exporté dans Documents\\My Games\\Tabletop Simulator\\Saves\\Saved Objects\\Deepotus">' + ICO("dz-action-envoyer-vers", 16, "cf-ic") + 'Poser dans Tabletop Simulator</button>'
      + '</div>'
      + '<p class="cf-edition-etat" data-role="tts-etat"></p>'
      + '<div class="cf-edition-actions" data-role="tabletopia">'
      + '<button type="button" class="btn strong" data-act="tabletopia" title="Un JPEG par face à la coupe (2000 px au plus, jamais agrandi), un seul dos s’il est commun, et le manifeste — à charger dans l’éditeur de Tabletopia">' + ICO("dz-action-exporter", 16, "cf-ic") + 'Exporter pour Tabletopia (.zip)</button>'
      + '</div>'
      + '</div></details>'

      /* LIVRET (tache #87 PR C, plan-cartes T18) : l'ecart est DIT ici, et dans l'en-tete du fichier. */
      + '<details class="grp"><summary>Livret de règles (PDF)</summary><div class="grp-body">'
      + '<input class="cf-edition-champ" data-k="livret_titre" placeholder="Titre (par défaut : le nom du jeu)" title="Titre de la première page">'
      + '<textarea class="cf-edition-texte" data-k="livret_texte" rows="10" placeholder="# But du jeu&#10;Le texte des règles…" title="Le texte du livret ; une ligne qui commence par « # » est un intertitre"></textarea>'
      + '<div class="cf-edition-actions">'
      + '<select data-k="livret_feuille" title="Format des pages du livret"><option value="a5">A5</option><option value="a4">A4</option><option value="carre">Carré 210 mm</option></select>'
      + '<select data-k="livret_fonte" data-role="polices" title="Fonte du livret (les fontes servies par l’application)"></select>'
      + '<label title="Une planche des cartes en fin de livret (rendues comme le Card Forge les montre)"><input type="checkbox" data-k="livret_planche"> planche des cartes</label>'
      + '<button type="button" class="btn strong" data-act="livret" title="Composer le livret en PDF (pages à 300 DPI)">Livret PDF</button>'
      + '</div>'
      + '<p class="hint">Le livret est composé à <b>300 DPI</b> : le texte n’est pas sélectionnable dans le PDF '
      + '(aucune police n’est embarquée par ce logiciel). Sans conséquence <b>pour l’impression</b> ; à savoir si le PDF est lu à l’écran.</p>'
      + '<p class="cf-edition-etat" data-role="livret-etat"></p>'
      + '</div></details>'

      /* MOCKUP ET FICHE (tache #87 PR C, plan-cartes T19) */
      + '<details class="grp"><summary>Mockup et fiche produit</summary><div class="grp-body">'
      + '<div class="cf-edition-actions">'
      + '<select data-k="mockup_cible" title="Format du visuel : carré, story (9:16) ou paysage (16:9)"><option value="carre">Carré 1080</option>'
      + '<option value="story">Story 1080 x 1920</option><option value="paysage">Paysage 1600 x 900</option></select>'
      + '<input class="cf-edition-champ" data-k="mockup_titre" placeholder="Titre (par défaut : le nom du jeu)" title="Titre du visuel">'
      + '<input class="cf-edition-champ" data-k="mockup_sous_titre" placeholder="Sous-titre" title="Sous-titre du visuel">'
      + '<button type="button" class="btn strong" data-act="mockup" title="Un éventail des cinq premières cartes, en PNG">Mockup PNG</button>'
      + '<button type="button" class="btn" data-act="fiche" title="Les chiffres du jeu : format, dimensions, paquet, boîte, langues">Fiche produit</button>'
      + '</div>'
      + '<p class="hint">Un éventail 2D des cartes déjà rendues (cinq au plus). La carte qui tourne en 3D, c’est la tournette '
      + 'de la pièce 05 (Volume) ; le Forge 3D (pièce 09) construit les objets.</p>'
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
    if (sel) sel.innerHTML = '<option value="">fonte par défaut</option>'
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
    if (!String(e.livret_texte || "").trim()) { CF.toast("Écrivez d’abord le texte des règles", true); return; }
    VERROU = true;
    try {
      const fd = new FormData();
      fd.append("spec", JSON.stringify({ titre: e.livret_titre || CF.doc().name || "", texte: e.livret_texte,
                                         feuille: e.livret_feuille, fonte: e.livret_fonte }));
      const cards = e.livret_planche ? CF.cards().slice(0, 120) : [];
      for (let i = 0; i < cards.length; i++) {
        CF.busy(true, "rendu " + (i + 1) + " / " + cards.length + " pour la planche…");
        fd.append("images", await CF.cardBlob(i, { face: "front" }), "c" + (i + 1) + ".png");
      }
      CF.busy(true, "composition du livret…");
      const out = await M.api.blob("POST", "livret", fd);
      CF.download(out, slugJeu() + "_livret.pdf");
      etatDe("livret-etat", "Livret composé (" + slugJeu() + "_livret.pdf)" + (cards.length ? " avec la planche de "
        + cards.length + " carte(s)" : "") + " — texte en image à 300 DPI.");
    } catch (er) {
      CF.toast("Livret impossible : " + String((er && er.message) || er), true);
    } finally { CF.busy(false); VERROU = false; }
  }
  async function mockupPng() {
    if (VERROU) return;
    const cards = CF.cards();
    if (!cards.length) { CF.toast("Aucune carte à montrer", true); return; }
    VERROU = true;
    try {
      const e = ed();
      const n = Math.min(5, cards.length);
      const fd = new FormData();
      fd.append("spec", JSON.stringify({ cible: e.mockup_cible, titre: e.mockup_titre || CF.doc().name || "",
                                         sous_titre: e.mockup_sous_titre, fonte: e.livret_fonte }));
      for (let i = 0; i < n; i++) {
        CF.busy(true, "rendu " + (i + 1) + " / " + n + "…");
        fd.append("images", await CF.cardBlob(i, { face: "front" }), "c" + (i + 1) + ".png");
      }
      CF.busy(true, "mockup…");
      const out = await M.api.blob("POST", "mockup", fd);
      CF.download(out, slugJeu() + "_mockup_" + e.mockup_cible + ".png");
      etatDe("mockup-etat", "Mockup " + e.mockup_cible + " : " + n + " carte(s) en éventail"
        + (cards.length > n ? " (les " + n + " premières sur " + cards.length + ")" : "") + ".");
    } catch (er) {
      CF.toast("Mockup impossible : " + String((er && er.message) || er), true);
    } finally { CF.busy(false); VERROU = false; }
  }
  async function ficheProduit() {
    if (VERROU) return;
    VERROU = true;
    try {
      FICHE = await M.api.post("fiche", { cartes: CF.cards().length || 1 });
      paintFiche();
    } catch (er) {
      CF.toast("Fiche impossible : " + String((er && er.message) || er), true);
    } finally { VERROU = false; }
  }
  function paintFiche() {
    const box = HOST && HOST.querySelector('[data-role="fiche"]');
    if (!box || !FICHE) return;
    const f = FICHE, mm = (v) => String(v).replace(".", ",");
    box.innerHTML = '<table class="cf-edition-fiche"><tbody>'
      + "<tr><th>Cartes</th><td>" + f.cartes + "</td></tr>"
      + "<tr><th>Format</th><td>" + esc(f.format) + " — " + mm(f.dimensions_mm[0]) + " x " + mm(f.dimensions_mm[1]) + " mm</td></tr>"
      + "<tr><th>Paquet</th><td>" + mm(f.epaisseur_deck_mm) + " mm (" + mm(f.epaisseur_carte_mm) + " mm par carte, pièce 05)</td></tr>"
      + "<tr><th>Boîte</th><td>" + (f.boite_mm ? f.boite_mm.map(mm).join(" x ") + " mm" : "—") + "</td></tr>"
      + "<tr><th>Langues</th><td>" + (f.langues.length ? esc(f.langues.join(", ")) : "non précisées (aucune colonne par langue)") + "</td></tr>"
      + "</tbody></table>"
      + '<textarea class="cf-edition-texte" rows="3" readonly title="Le texte de la fiche, à recopier">' + esc(f.texte) + "</textarea>";
  }

  function paintCibles() {
    const box = HOST && HOST.querySelector('[data-role="cibles"]');
    if (!box) return;
    const cur = CF.doc().edition && CF.doc().edition.cible || DEFAULTS.cible;
    box.innerHTML = CIBLES.map((c) =>
      '<button type="button" class="cf-edition-cible' + (c.id === cur ? " on" : "")
      + '" data-act="cible" data-v="' + esc(c.id) + '" title="' + esc("Exporter pour " + c.label
        + " — relu le " + c.verifie) + '"><b>' + esc(c.label) + '</b><i>' + esc(c.note) + '</i></button>').join("");
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
    if (!cards.length) { CF.toast("Aucune carte à exporter", true); return; }
    VERROU = true;
    try {
      const fd = new FormData();
      fd.append("spec", JSON.stringify({ noms: cards.map(cardName) }));
      for (let i = 0; i < cards.length; i++) {
        CF.busy(true, "rendu " + (i + 1) + " / " + cards.length + " (recto + verso)…");
        fd.append("fronts", await CF.cardBlob(i, { face: "front" }), "f" + (i + 1) + ".png");
        fd.append("backs", await CF.cardBlob(i, { face: "back" }), "b" + (i + 1) + ".png");
      }
      CF.busy(true, "planches Tabletop Simulator…");
      const out = await M.api.blob("POST", "tts", fd);
      const nom = slugJeu() + "_tts.zip";
      CF.download(out, nom);
      DERNIER = { cartes: cards.length, nom: nom };
      etat(cards.length + " carte(s) exportée(s) : planches et objet écrits sur ce PC (" + nom + "). "
        + "« Poser dans Tabletop Simulator » le range dans ses Saved Objects.");
      CF.toast("Tabletop Simulator : " + cards.length + " carte(s)");
    } catch (e) {
      CF.toast("Export Tabletop Simulator impossible : " + String((e && e.message) || e), true);
    } finally { CF.busy(false); VERROU = false; paintTts(); }
  }
  /* TABLETOPIA : meme rendu (recto + verso), un fichier par face cote backend. */
  async function exporterTabletopia() {
    if (VERROU) return;
    const cards = CF.cards();
    if (!cards.length) { CF.toast("Aucune carte à exporter", true); return; }
    VERROU = true;
    try {
      const fd = new FormData();
      fd.append("spec", JSON.stringify({ noms: cards.map(cardName) }));
      for (let i = 0; i < cards.length; i++) {
        CF.busy(true, "rendu " + (i + 1) + " / " + cards.length + " (recto + verso)…");
        fd.append("fronts", await CF.cardBlob(i, { face: "front" }), "f" + (i + 1) + ".png");
        fd.append("backs", await CF.cardBlob(i, { face: "back" }), "b" + (i + 1) + ".png");
      }
      CF.busy(true, "images Tabletopia…");
      const out = await M.api.blob("POST", "tabletopia", fd);
      const nom = slugJeu() + "_tabletopia.zip";
      CF.download(out, nom);
      etat(cards.length + " carte(s) exportée(s) pour Tabletopia (" + nom + ") : un fichier par face, à charger "
        + "dans l’éditeur de Tabletopia — recto et verso séparés, comme il le demande.");
      CF.toast("Tabletopia : " + cards.length + " carte(s)");
    } catch (e) {
      CF.toast("Export Tabletopia impossible : " + String((e && e.message) || e), true);
    } finally { CF.busy(false); VERROU = false; }
  }
  async function poserTts() {
    if (VERROU || !DERNIER) return;
    VERROU = true;
    try {
      const r = await M.api.post("tts/poser", {});
      etat("Posé dans Tabletop Simulator : " + r.chemin + " — dans le jeu, Objects > Saved Objects > Deepotus.");
      CF.toast("objet posé dans Tabletop Simulator");
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
    title: "Édition",
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
