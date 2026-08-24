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

  /* Le cote long au-dela duquel le SERVEUR reduit une image importee. MEME
     CHIFFRE que cards/capture.py:MAX_IMPORT_PX, et que les sept autres
     copies du lab (face/frame/type, en py comme en js) : la regle 8 interdit
     de partager une constante entre pieces, alors on la RECOPIE et on
     l'AVOUE. Le chiffre etait ici EN TOUTES LETTRES dans deux phrases
     d'ecran — une huitieme copie que rien ne confrontait. Le test de la piece
     lit maintenant les HUIT sur les fichiers, et refuse tout nombre nu. Cet
     ecran ne reduit rien : il ne fait que dire ce que le serveur fera. */
  const MAX_IMPORT_PX = 4096;

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
       POURQUOI LES CHAMPS DE L'ANALYSE SONT LA ALORS QUE RIEN NE LES REMPLIT
       ENCORE — et ce n'est PAS « pour eviter une migration » (la premiere
       version de ce commentaire le disait ; verifie a la source, c'est faux :
       `register()` refait `SCHEMA[id]` a CHAQUE chargement de page, une cle
       ajoutee demain serait acceptee des le lendemain sur les documents deja
       ecrits, et une cle stockee inconnue est simplement ignoree avec un
       avertissement en console). La vraie raison est immediate : `upload()`
       remet l'analyse a zero en patchant `analyzed/border/boxes/bg/palette/
       layers`, et `patchAs` LEVE sur une cle hors schema. Sans ces sept
       lignes, le premier depot d'un recto casse. Les mesures de T2 tomberont
       dans les memes cles, sans rien a changer ici. */
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
      /* LE FILTRE EST UNE PROMESSE. `image/*` ouvrait le selecteur sur HEIC,
         SVG, AVIF et TIFF — que la route refuse en « corps illisible ». On ne
         propose que ce que PIL sait ouvrir de l'autre cote. */
      + '<input type="file" accept="image/png,image/jpeg,image/webp" class="cf-capture-file" id="cf-capture-file">'
      + '<button class="btn strong sm" id="cf-capture-pick" type="button" title="PNG, JPEG ou WebP — le serveur réduit l\'image au-delà du plafond d\'import">Choisir un fichier…</button>'
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
           remplacement afficherait encore l'ancienne. Il est en
           MILLISECONDES (backend) : en secondes, deux imports de la meme
           seconde rendaient la MEME URL et le cache resservait l'ancienne
           image — le remplacement etait dans le fichier et pas a l'ecran. */
        /* UN APERCU QUI ECHOUE DOIT SE VOIR. Une <img> sans `onerror` qui
           perd son fichier laisse le cadre vide pendant que l'etat annonce
           « capture deposee » (gotcha des vignettes du dock : un onError
           absent = une visibilite perimee). */
        img.onerror = () => {
          img.classList.add("hidden");
          if (vide) {
            vide.classList.remove("hidden");
            vide.textContent = "L'image de cette capture ne se charge plus "
              + "(fichier absent côté serveur). Déposez-la à nouveau.";
          }
          const e2 = $("#cf-capture-state");
          if (e2) { e2.textContent = "capture illisible"; e2.className = "cf-capture-state ko"; }
        };
        img.onload = () => { img.classList.remove("hidden"); };
        img.src = M.api.url("file/" + d.nom) + "?t=" + (Number(i.stamp) || 0);
        img.alt = "capture " + d.label;
        img.classList.remove("hidden");
      } else {
        img.onerror = null;
        img.onload = null;
        img.removeAttribute("src");
        img.classList.add("hidden");
      }
    }
    if (vide) {
      /* le texte d'accueil est REPOSE a chaque peinture : `onerror` l'a
         peut-etre remplace par son message d'echec au tour precedent. */
      vide.textContent = "Déposez ici l'image de la carte, ou choisissez un fichier.";
      vide.classList.toggle("hidden", !!i);
    }
    if (rempl) rempl.classList.toggle("hidden", !i);

    /* L'ANALYSE EST UNE PROPRIETE DU RECTO (plan D3 amende). Afficher
       « analysee » en regardant le verso dirait que les mesures portent sur
       l'image montree — elles portent sur l'autre. */
    const mesure = analysee() && SIDE === "recto";
    const etat = $("#cf-capture-state");
    if (etat) {
      etat.textContent = !i ? "pas de capture"
        : (mesure ? "analysée" : "capture déposée");
      etat.className = "cf-capture-state" + (!i ? "" : (mesure ? " ok" : " on"));
    }

    txt("#cf-capture-r-side", d.label);
    txt("#cf-capture-r-px", i ? (i.w + " × " + i.h + " px") : "—");
    txt("#cf-capture-r-bytes", i ? weight(i.bytes) : "—",
      i ? (Number(i.bytes) || 0).toLocaleString("fr-FR") + " octets" : "");
    txt("#cf-capture-r-an", SIDE !== "recto" ? "propriété du recto"
      : (analysee() ? String(st().analyzed) : "pas encore"));
    txt("#cf-capture-note", !i
      ? "PNG, JPEG ou WebP. Au-delà de " + MAX_IMPORT_PX + " px de côté, le "
        + "serveur réduit l'image et répond ses dimensions réelles."
      : (SIDE === "recto"
        ? "Les mesures de l'analyse s'affichent ici dès que le document en porte : "
          + "cet écran les LIT, il ne les garde pas."
        : "L'analyse porte sur le RECTO — bordure, zones et fond s'y mesurent. "
          + "Déposer un verso ne l'efface pas : il sert au dos de carte et à "
          + "l'objet 3D."));
  }

  /* ═══════════════════════════════════════════════════════════════════════
     3. LE DEPOT
     ═══════════════════════════════════════════════════════════════════════ */

  /* CE QU'UN DEPOT EFFACE — une fonction PURE, et c'est deliberé : la regle
     tient en trois lignes, elle ne touche a rien, et le test de la piece
     l'EXECUTE (node, sur cette source-ci) au lieu de lire sa forme. Un
     controle qui lit du texte ne voit pas un `|| true` glisse dans la garde ;
     celui-la le voit.

     UN NOUVEAU RECTO PERIME L'ANALYSE : elle decrit une image qui n'est plus
     sur le disque, et la garder afficherait « analysee » au-dessus d'une
     image que personne n'a mesuree.
     UN VERSO, NON (plan D3 amende) : l'analyse est une propriete du RECTO —
     les adoptions §7.1.5 sont des gestes de recto, le verso est stocke pour
     le dos de carte et l'objet 3D (§6.2ter). Sans cette asymetrie, importer
     son verso effacait les mesures du recto sans un mot. */
  function effacements(side) {
    if (side !== "recto") return {};
    return {
      analyzed: null, border: null, boxes: [],
      bg: null, palette: [], layers: {},
    };
  }
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
      /* UNE ROUTE ABSENTE N'EST PAS UN REFUS NOMME, et le code ne les
         distingue pas : cette route rend un 404 « Deck introuvable » quand le
         jeu a ete supprime dans un autre onglet. Traduire tout 404 en
         « backend absent » declarait le domaine ETEINT parce qu'un jeu avait
         disparu — le CORE a deja paye ce bug et ecrit son remede
         (core.js:jsonNamed, §9bis) : la question se tranche sur le TYPE DE
         REPONSE. Du HTML (le catch-all SPA) = il n'y a pas de route ; du
         JSON = le backend parle, et c'est SA phrase qui doit arriver. */
      const ct = (resp.headers.get("content-type") || "").toLowerCase();
      if (ct.indexOf("json") < 0) {
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
      M.patch(Object.assign({ sources: maj }, effacements(side)));
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
