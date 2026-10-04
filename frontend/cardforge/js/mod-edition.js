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

  let M = null, HOST = null, CIBLES = [], DERNIER = null, VERROU = false;

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
      + '<div class="cf-edition-actions" data-role="tts">'
      + '<button type="button" class="btn strong" data-act="tts" title="Planches 10 x 7 à la coupe (4096 px au plus) et objet sauvegardé qui pointe vers elles, sur ce PC — un ZIP de tout">Exporter pour Tabletop Simulator (.zip)</button>'
      + '<button type="button" class="btn" data-act="tts-poser" title="Copier le dernier objet exporté dans Documents\\My Games\\Tabletop Simulator\\Saves\\Saved Objects\\Deepotus">Poser dans Tabletop Simulator</button>'
      + '</div>'
      + '<p class="cf-edition-etat" data-role="tts-etat"></p>'
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
      paintTts();
      CF.on("core:doc", (p) => { if (!p || p.id === "edition") { paintCibles(); paintTts(); } });
      M.emit("ready", {});
    },
  });
})();
