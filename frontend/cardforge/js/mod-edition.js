/* ═══════════════════════════════════════════════════════════════════════════
   Card Forge — piece 11 · Edition   [P11]   (tache #84, plan-cartes T5)
   Proprietaire exclusif de : doc.edition · aucun z · /api/cards/<did>/edition/*
   Prefixe DOM impose : id="cf-edition-..."   ·   feuille : css/mod-edition.css
   (tout selecteur y contient .cf-edition)

   CE QUE CETTE PIECE NE FAIT PAS : dessiner une carte. Elle ASSEMBLE des
   cartes rendues par CF.renderCard (via CF.cardBlob) et les televerse. Elle
   livre ce qui entoure le jeu : la table virtuelle (Tabletop Simulator,
   Tabletopia) ; plus tard le livret, le mockup, la fiche produit.
   ═══════════════════════════════════════════════════════════════════════════ */
"use strict";

(function () {
  const CF = (typeof window !== "undefined") ? window.CF : null;
  if (!CF) throw new Error("mod-edition: js/core.js doit etre charge avant ce fichier");

  const esc = (s) => String(s == null ? "" : s).replace(/&/g, "&amp;")
    .replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

  let M = null, HOST = null, CIBLES = [];

  const DEFAULTS = {
    cible: "tts",      /* tts | tabletopia */
  };

  function shell() {
    HOST.innerHTML = ''
      + '<details class="grp" open><summary>Table virtuelle — Tabletop Simulator, Tabletopia</summary>'
      + '<div class="grp-body">'
      + '<div class="cf-edition-cibles" data-role="cibles"></div>'
      + '<p class="hint">Chaque cible dit ce que son éditeur publie (relu le 04/10/2026) : '
      + 'la carte est exportée telle que le Card Forge la rend, à la coupe.</p>'
      + '</div></details>';
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

  function wire() {
    HOST.addEventListener("click", (ev) => {
      const t = ev.target.closest("[data-act]");
      if (!t) return;
      if (t.dataset.act === "cible") { M.patch({ cible: String(t.dataset.v) }); paintCibles(); }
    });
  }

  M = CF.register({
    id: "edition",
    title: "Édition",
    icon: "\u{1F4E6}",
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
      paintCibles();
      CF.on("core:doc", (p) => { if (!p || p.id === "edition") paintCibles(); });
      M.emit("ready", {});
    },
  });
})();
