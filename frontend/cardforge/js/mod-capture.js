/* ═══════════════════════════════════════════════════════════════════════════
   Card Forge — piece 10 · Import   [P10]
   Proprietaire exclusif de : doc.capture · aucun z · /api/cards/<did>/capture/*
   Prefixe DOM impose : id="cf-capture-..."   ·   feuille : css/mod-capture.css
   (tout selecteur y contient .cf-capture)

   L'ID EST « capture », LE LIBELLE EST « Import ». `import.py` serait
   inimportable (mot reserve Python) et la regle 1 exige que la piece porte
   son id sur ses quatre fichiers : l'id se tait, le libelle parle.

   CE QUE FAIT CETTE PIECE
   ──────────────────────
   Elle reprend une carte QUI EXISTE DEJA — une photo, un scan, un PNG de
   production — et en fait de la matiere pour les neuf autres. Ce fichier-ci
   tient le DEPOT (recto/verso), l'apercu de ce qui est range cote serveur et
   l'etat de la capture. Les MESURES (bordure, zones, fond, palette, et la
   confiance chiffree de chacune) arrivent juste apres et s'afficheront ici.

   ELLE NE DESSINE RIEN. Aucun painter, aucun z : la carte importee n'est pas
   la carte du jeu — elle est son MODELE. Ce sont les pieces qui l'adoptent
   (P1 l'illustration, P2 la bordure, P3 les zones) qui touchent au dessin, et
   chacune chez elle.

   L'ETAT EST LU AVEC TOLERANCE. `doc.capture` peut etre vide, partiel, ou
   porter des cles qu'une version plus recente aura ecrites : rien ici ne
   suppose sa forme. « Analysee » se DERIVE de `doc.capture.analyzed` — un
   ecran qui garderait son propre drapeau afficherait « analysee » sur un
   document qui ne l'est pas.
   ═══════════════════════════════════════════════════════════════════════════ */
"use strict";

(function () {
  const CF = (typeof window !== "undefined") ? window.CF : null;
  if (!CF) throw new Error("mod-capture: js/core.js doit etre charge avant ce fichier");

  /* Les deux cotes, dans l'ordre ou on les depose. Le backend porte la meme
     liste (capture.py:SIDES) et c'est LUI qui refuse un troisieme nom : cette
     copie-ci ne sert qu'a peindre deux boutons. */
  const SIDES = [
    { id: "recto", label: "Recto", nom: "source_recto.png" },
    { id: "verso", label: "Verso", nom: "source_verso.png" },
  ];

  /* Le cote MONTRE par le panneau. De la PRESENTATION : il ne va pas au
     document (deux onglets ouverts sur le meme jeu n'ont pas a se pousser du
     coude pour regarder chacun un cote). */
  let SIDE = "recto";
  let BUSY = false;

  const M = CF.register({
    id: "capture",
    title: "Import",
    icon: "\u{1F4E5}",
    order: 10,

    /* Aucun z n'est alloue a cette piece : elle ne dessine pas la carte.
       Enregistrer un painter ici leve — c'est voulu (spec §9.4). */
    painters: [],

    /* LE SCHEMA : ces cles sont les SEULES que M.patch({...}) acceptera.
       Il porte deja les champs de l'analyse (spec §7.1.4) alors que rien ne
       les remplit encore : le schema est GELE a l'enregistrement, et une cle
       ajoutee plus tard serait refusee par le CORE sur les documents deja
       ouverts. Les declarer maintenant coute zero octet dans un document
       neuf — `default_doc` seme `{}` — et evite une migration. */
    state: {
      sources: {},        /* {recto: {w, h, bytes, stamp}, verso: {…}} */
      analyzed: null,     /* horodatage de la derniere analyse, ou null */
      border: null,       /* {mm, color, radius_mm, confidence} */
      boxes: [],          /* [{x_mm, y_mm, w_mm, h_mm, …}] — en MILLIMETRES */
      bg: null,           /* {color, confidence} ou le refus mesure */
      palette: [],        /* couleurs dominantes */
      layers: {},         /* les PNG isoles ranges cote serveur */
    },

    init(host) {
      host.innerHTML = shell();
      wire(host);
      paint();
      /* Le document peut changer sous nos pieds : un autre onglet, une
         adoption, un jeu rouvert. On repeint sur l'evenement, jamais sur une
         copie gardee au chaud. */
      CF.on("core:doc", (e) => {
        if (!e || e.id === "capture" || e.id === "name") paint();
      });
      CF.on("core:deck", () => paint());
    },
  });

  /* ═══════════════════════════════════════════════════════════════════════
     1. PETITS OUTILS
     ═══════════════════════════════════════════════════════════════════════ */
  const $ = (sel) => (M.slot() ? M.slot().querySelector(sel) : null);

  function isPlain(v) {
    return !!v && typeof v === "object" && !Array.isArray(v);
  }

  /* L'ETAT, LU AVEC TOLERANCE — jamais une supposition de forme. */
  function st() {
    const d = CF.doc();
    return isPlain(d) && isPlain(d.capture) ? d.capture : {};
  }
  function sources() {
    const s = st().sources;
    return isPlain(s) ? s : {};
  }
  function info(side) {
    const s = sources()[side];
    return isPlain(s) ? s : null;
  }
  function analysee() {
    const a = st().analyzed;
    return !!a;                       /* true, un horodatage, une date : tout dit oui */
  }
  function sideDef(id) {
    return SIDES.filter((s) => s.id === id)[0] || SIDES[0];
  }

  /* Poids lisible, l'octet exact garde en infobulle (patron de P8). */
  function weight(n) {
    const v = Number(n) || 0;
    if (v < 1024) return v + " o";
    if (v < 1024 * 1024) return (v / 1024).toFixed(v < 10240 ? 1 : 0) + " Kio";
    return (v / 1048576).toFixed(2) + " Mio";
  }

  function txt(sel, s, title) {
    const e = $(sel);
    if (!e) return;
    e.textContent = String(s == null ? "" : s);
    if (title != null) e.title = String(title);
  }

  /* ═══════════════════════════════════════════════════════════════════════
     2. LE PANNEAU

     Le squelette est un LITTERAL sans interpolation : rien de ce qui vient du
     backend ou du document n'y entre. Tout ce qui varie est pose par
     `textContent` ou par `img.src`, jamais par innerHTML — c'est la regle 14,
     et elle se tient sans effort quand le HTML ne porte aucune donnee.
     ═══════════════════════════════════════════════════════════════════════ */
  function shell() {
    return ''
      + '<div class="cf-capture-wrap">'

      + '<section class="cf-capture-card">'
      + '<header class="cf-capture-h"><b>Reprendre une carte</b>'
      + '<span class="cf-capture-sub">un fichier par côté — le second dépôt remplace le premier</span>'
      + '<span class="cf-capture-spacer"></span>'
      + '<div class="seg sm" id="cf-capture-seg"></div>'
      + '</header>'

      + '<div class="cf-capture-body">'

      + '<div class="cf-capture-drop" id="cf-capture-drop">'
      + '<div class="cf-capture-preview">'
      + '<img class="cf-capture-img hidden" id="cf-capture-img" alt="" draggable="false">'
      + '<p class="cf-capture-empty" id="cf-capture-empty">Déposez ici l\'image de la carte, ou choisissez un fichier.</p>'
      + '</div>'
      + '<div class="cf-capture-actions">'
      + '<input type="file" accept="image/*" class="cf-capture-file" id="cf-capture-file">'
      + '<button class="btn strong sm" id="cf-capture-pick" type="button" title="PNG, JPEG ou WebP — l\'image est réduite à 4096 px de côté par le serveur">Choisir un fichier…</button>'
      + '<button class="btn ghost sm hidden" id="cf-capture-replace" type="button" title="Déposer une autre image à la place de celle-ci">Remplacer</button>'
      + '</div>'
      + '</div>'

      + '<div class="cf-capture-side">'
      + '<span class="cf-capture-state" id="cf-capture-state">pas de capture</span>'
      + '<dl class="cf-capture-read" id="cf-capture-read">'
      + '<dt>Côté</dt><dd id="cf-capture-r-side">—</dd>'
      + '<dt>Trame</dt><dd id="cf-capture-r-px">—</dd>'
      + '<dt>Fichier</dt><dd id="cf-capture-r-bytes">—</dd>'
      + '<dt>Analyse</dt><dd id="cf-capture-r-an">—</dd>'
      + '</dl>'
      + '<p class="hint" id="cf-capture-note"></p>'
      + '</div>'

      + '</div></section>'
      + '</div>';
  }

  function segDraw() {
    const seg = $("#cf-capture-seg");
    if (!seg) return;
    seg.innerHTML = "";
    SIDES.forEach((s) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "seg-b" + (s.id === SIDE ? " active" : "");
      b.textContent = s.label + (info(s.id) ? " •" : "");
      b.title = info(s.id) ? s.label + " : une capture est déposée"
        : s.label + " : rien encore";
      b.addEventListener("click", () => { SIDE = s.id; paint(); });
      seg.appendChild(b);
    });
  }

  function paint() {
    if (!M.slot()) return;
    segDraw();
    const d = sideDef(SIDE);
    const i = info(SIDE);
    const img = $("#cf-capture-img");
    const vide = $("#cf-capture-empty");
    const rempl = $("#cf-capture-replace");

    if (img) {
      if (i) {
        /* On relit l'image SERVIE, pas le fichier local : c'est elle que
           l'analyse mesurera, et une divergence entre les deux serait
           invisible. Le `stamp` casse le cache du navigateur — sans lui, un
           remplacement afficherait encore l'ancienne. */
        img.src = M.api.url(d.nom) + "?t=" + (Number(i.stamp) || 0);
        img.alt = "capture " + d.label;
        img.classList.remove("hidden");
      } else {
        img.removeAttribute("src");
        img.classList.add("hidden");
      }
    }
    if (vide) vide.classList.toggle("hidden", !!i);
    if (rempl) rempl.classList.toggle("hidden", !i);

    const etat = $("#cf-capture-state");
    if (etat) {
      const quoi = !i ? "pas de capture"
        : (analysee() ? "analysée" : "capture déposée");
      etat.textContent = quoi;
      etat.className = "cf-capture-state"
        + (!i ? "" : (analysee() ? " ok" : " on"));
    }

    txt("#cf-capture-r-side", d.label);
    txt("#cf-capture-r-px", i ? (i.w + " × " + i.h + " px") : "—");
    txt("#cf-capture-r-bytes", i ? weight(i.bytes) : "—",
      i ? (Number(i.bytes) || 0).toLocaleString("fr-FR") + " octets" : "");
    txt("#cf-capture-r-an", analysee() ? String(st().analyzed) : "pas encore");
    txt("#cf-capture-note", i
      ? "Les mesures de l'analyse s'affichent ici dès que le document en porte : "
        + "cet écran les LIT, il ne les garde pas."
      : "PNG, JPEG ou WebP. L'image est ramenée à 4096 px de côté par le "
        + "serveur, qui répond ses dimensions réelles.");
  }

  /* ═══════════════════════════════════════════════════════════════════════
     3. LE DEPOT
     ═══════════════════════════════════════════════════════════════════════ */
  function wire(host) {
    const pick = host.querySelector("#cf-capture-pick");
    const rempl = host.querySelector("#cf-capture-replace");
    const file = host.querySelector("#cf-capture-file");
    const drop = host.querySelector("#cf-capture-drop");
    const ouvre = () => { if (file) { file.value = ""; file.click(); } };
    if (pick) pick.addEventListener("click", ouvre);
    if (rempl) rempl.addEventListener("click", ouvre);
    if (file) {
      file.addEventListener("change", () => {
        const f = file.files && file.files[0];
        if (f) upload(f, SIDE);
      });
    }
    if (drop) {
      ["dragenter", "dragover"].forEach((n) => {
        drop.addEventListener(n, (e) => {
          e.preventDefault();
          drop.classList.add("over");
        });
      });
      ["dragleave", "drop"].forEach((n) => {
        drop.addEventListener(n, () => drop.classList.remove("over"));
      });
      drop.addEventListener("drop", (e) => {
        e.preventDefault();
        const dt = e.dataTransfer;
        const f = dt && dt.files && dt.files[0];
        if (f) upload(f, SIDE);
      });
    }
  }

  async function upload(f, side) {
    if (BUSY) { M.toast("un import est déjà en cours"); return; }
    if (!f) return;
    /* Le type MIME du navigateur est un indice, pas une preuve : le refus qui
       compte est celui du serveur, qui ouvre les octets. Celui-ci evite juste
       un aller-retour de 60 Mo sur un .zip depose par megarde. */
    if (f.type && !/^image\//.test(f.type)) {
      M.toast("ce fichier n'est pas une image (" + (f.type || "type inconnu") + ")", true);
      return;
    }
    BUSY = true;
    try {
      M.busy(true, "import de la carte…");
      const resp = await M.api.raw("POST",
        "card?side=" + encodeURIComponent(side), f);
      if (resp.status === 404) {
        const x = new Error("route absente");
        x.missing = true;
        throw x;
      }
      const d = await resp.json().catch(() => null);
      if (!resp.ok) {
        throw new Error((d && d.detail) || (resp.status + " " + resp.statusText));
      }
      const maj = {};
      Object.keys(sources()).forEach((k) => { maj[k] = sources()[k]; });
      maj[side] = { w: d.w, h: d.h, bytes: d.bytes, stamp: d.stamp };
      /* L'ANALYSE PRECEDENTE NE DECRIT PLUS CE QUI EST SUR LE DISQUE. La
         garder afficherait « analysée » au-dessus d'une image que personne
         n'a mesuree — exactement le genre de certitude que cette piece
         s'interdit. On la retire ; c'est le seul effacement que ce depot
         fait, et il est nomme. */
      M.patch({ sources: maj, analyzed: null, border: null, boxes: [],
                bg: null, palette: [], layers: {} });
      paint();
      M.toast("carte importée — " + d.w + " × " + d.h + " px, " + weight(d.bytes));
    } catch (e) {
      M.toast(e && e.missing
        ? "backend absent : l'import exige /api/cards"
        : String((e && e.message) || e), true);
    } finally {
      BUSY = false;
      M.busy(false);
    }
  }

})();
