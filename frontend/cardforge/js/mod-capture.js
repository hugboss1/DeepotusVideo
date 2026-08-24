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
   tient le DEPOT (recto/verso), l'apercu de ce qui est range cote serveur,
   le geste « Analyser » et l'AFFICHAGE DES MESURES (bordure, zones, fond,
   palette).

   CHAQUE MESURE SORT AVEC SON CHIFFRE DE CONFIANCE, et jamais sans (spec
   §7.1.2 : « l'ecran affiche le chiffre, jamais une certitude »). Une
   detection qui n'a rien trouve le DIT — elle n'affiche pas un zero
   rassurant —, et la note du backend explique pourquoi.

   C'EST LA PIECE QUI PUBLIE, PAS LA ROUTE (plan D3). Le POST /analyse REPOND
   le releve ; c'est `M.patch` qui l'ecrit dans `doc.capture`, par la voie
   d'autosave unique. Une seule main sur le document.

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
  /* L'incrustation des boites sur l'apercu se replie : elle recouvre le
     dessin, et on veut pouvoir regarder la carte. De la PRESENTATION, donc
     pas du document — comme SIDE. */
  let BOITES = true;

  const M = CF.register({
    id: "capture",
    title: "Import",
    icon: "\u{1F4E5}",
    order: 10,

    /* Aucun z n'est alloue a cette piece : elle ne dessine pas la carte.
       Enregistrer un painter ici leve — c'est voulu (spec §9.4). */
    painters: [],

    /* LE SCHEMA : ces cles sont les SEULES que M.patch({...}) acceptera.
       `register()` refait `SCHEMA[id]` a CHAQUE chargement de page — une cle
       ajoutee ici est acceptee des le lendemain sur les documents deja
       ecrits, et une cle stockee inconnue est simplement ignoree avec un
       avertissement en console. Ce qui OBLIGE a les declarer toutes est
       ailleurs : `upload()` et `analyser()` ecrivent en un seul patch, et
       `patchAs` LEVE sur une cle hors schema. Une cle de mesure oubliee ici
       ne « manque » pas : elle casse le geste entier. */
    state: {
      sources: {},        /* {recto: {w, h, bytes, stamp}, verso: {…}} */
      analyzed: null,     /* horodatage ms de la derniere analyse, ou null */
      /* L'ECHELLE EST RANGEE AVEC LES MESURES, ET CE N'EST PAS DU CONFORT :
         un millimetre de `boxes` ne veut rien dire sans le facteur qui l'a
         produit. Change le format du jeu apres l'analyse et les mm d'hier
         decrivent une autre carte — `echelle` garde le cadre de reference
         (mm/px, taille de l'image, format, les deux ratios) avec le releve
         qui en depend. C'est aussi lui qui place l'incrustation. */
      echelle: null,      /* {mm_par_px, image_px, carte_mm, fmt, ratio_*} */
      ecart_ratio: null,  /* ratio image / ratio format − 1, SIGNE */
      border: null,       /* {mm, color, radius_mm, confidence, …} ou null */
      boxes: [],          /* [{x, y, w, h, densite, nettete}] — en MILLIMETRES */
      bg: null,           /* {color, confidence} ou le refus mesure */
      palette: [],        /* [{hex, part}] dominantes */
      notes: [],          /* ce que l'analyse n'a PAS pu mesurer, et pourquoi */
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

  /* UN NOMBRE, ET PAS CE QUE `Number()` EN FERAIT. `Number(null)` vaut ZERO
     et passe `isFinite` : une mesure ABSENTE s'affichait alors « 0,00 » —
     un chiffre inventé, exactement ce que la spec §7.1.2 interdit (le rayon
     de coin non suivi devenait « rayon 0,00 mm », qui est une VRAIE valeur
     possible pour un coin carre). Le test de la piece joue `conf(null)` dans
     node ; c'est lui qui a trouve ce trou. On exige donc un `number`. */
  function estNombre(v) {
    return typeof v === "number" && isFinite(v);
  }

  /* Un nombre a la francaise : virgule decimale, et un nombre de decimales
     CHOISI par l'appelant. Les mesures ne s'arrondissent pas ici — le backend
     les a deja arrondies a la precision qu'il assume ; cette fonction ne fait
     que les ECRIRE. */
  function num(v, n) {
    if (!estNombre(v)) return "—";
    return v.toFixed(n == null ? 2 : n).replace(".", ",");
  }
  /* Une confiance s'ecrit TOUJOURS avec son chiffre (spec §7.1.2). Pas de
     « bonne », pas de « fiable » : deux decimales, et le lecteur juge. Une
     confiance qu'on n'a pas se DIT inconnue — elle ne vaut pas zero. */
  function conf(v) {
    return estNombre(v) ? "confiance " + num(v, 2) : "confiance inconnue";
  }
  function quand(ms) {
    const n = Number(ms);
    if (!isFinite(n) || n <= 0) return "—";
    try { return new Date(n).toLocaleString("fr-FR"); }
    catch (e) { return String(ms); }
  }

  /* Un bloc de mesure : un titre, des lignes, et — s'il y a lieu — la
     pastille de confiance. Construit par createElement/textContent (regle 14)
     parce que son contenu VIENT du document ; le squelette, lui, reste un
     litteral sans interpolation. */
  function bloc(sel, titre, lignes, confiance, classe) {
    const hote = $(sel);
    if (!hote) return null;
    while (hote.firstChild) hote.removeChild(hote.firstChild);
    hote.className = "cf-capture-mes" + (classe ? " " + classe : "");
    const t = document.createElement("b");
    t.textContent = String(titre);
    hote.appendChild(t);
    if (confiance != null) {
      const c = document.createElement("span");
      c.className = "cf-capture-conf";
      c.textContent = conf(confiance);
      t.appendChild(c);
    }
    (lignes || []).forEach((l) => {
      if (l == null) return;
      const d = document.createElement("div");
      d.className = "cf-capture-l";
      d.textContent = String(l);
      hote.appendChild(d);
    });
    return hote;
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
      /* LE CADRE SE SERRE SUR L'IMAGE. L'incrustation des boites est posee en
         POURCENTAGES de la carte : elle doit donc recouvrir l'<img> EXACTEMENT,
         pas la boite de centrage qui l'entoure. Un `inline-block` autour de la
         seule image prend sa taille rendue, quels que soient les `max-*`. */
      + '<span class="cf-capture-frame hidden" id="cf-capture-frame">'
      + '<img class="cf-capture-img hidden" id="cf-capture-img" alt="" draggable="false">'
      + '<span class="cf-capture-boxes hidden" id="cf-capture-boxes"></span>'
      + '</span>'
      + '<p class="cf-capture-empty" id="cf-capture-empty">Déposez ici l\'image de la carte, ou choisissez un fichier.</p>'
      + '</div>'
      + '<div class="cf-capture-actions">'
      /* LE FILTRE EST UNE PROMESSE. `image/*` ouvrait le selecteur sur HEIC,
         SVG, AVIF et TIFF — que la route refuse en « corps illisible ». On ne
         propose que ce que PIL sait ouvrir de l'autre cote. */
      + '<input type="file" accept="image/png,image/jpeg,image/webp" class="cf-capture-file" id="cf-capture-file">'
      + '<button class="btn strong sm" id="cf-capture-pick" type="button" title="PNG, JPEG ou WebP — le serveur réduit l\'image au-delà du plafond d\'import">Choisir un fichier…</button>'
      + '<button class="btn ghost sm hidden" id="cf-capture-replace" type="button" title="Déposer une autre image à la place de celle-ci">Remplacer</button>'
      + '<span class="cf-capture-spacer"></span>'
      + '<button class="btn sm hidden" id="cf-capture-analyse" type="button" title="Mesurer le recto déposé : bordure, zones, fond, palette. Gratuit, local, sans aucun appel payant — et rejouable autant de fois qu\'on veut.">Analyser</button>'
      + '<button class="btn ghost sm hidden" id="cf-capture-boxtog" type="button" title="Afficher ou masquer les zones candidates par-dessus l\'aperçu">Masquer les zones</button>'
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

      /* ── LE RELEVÉ ──────────────────────────────────────────────────────
         Cinq blocs, et pas un mot d'appréciation : ce qui a été mesuré, avec
         le chiffre de confiance de la détection qui l'a produit. Ce qui n'a
         PAS pu être mesuré descend dans les notes, avec son motif. */
      + '<section class="cf-capture-card cf-capture-mesures hidden" id="cf-capture-mesures">'
      + '<header class="cf-capture-h"><b>Mesures du recto</b>'
      + '<span class="cf-capture-sub">chaque détection porte sa confiance chiffrée — analyse locale, gratuite, rejouable</span>'
      + '<span class="cf-capture-spacer"></span>'
      + '<span class="cf-capture-state" id="cf-capture-m-when">—</span>'
      + '</header>'
      + '<div class="cf-capture-mgrid">'
      + '<div class="cf-capture-mes" id="cf-capture-m-echelle"></div>'
      + '<div class="cf-capture-mes" id="cf-capture-m-bord"></div>'
      + '<div class="cf-capture-mes" id="cf-capture-m-zones"></div>'
      + '<div class="cf-capture-mes" id="cf-capture-m-fond"></div>'
      + '<div class="cf-capture-mes" id="cf-capture-m-pal"></div>'
      + '</div>'
      + '<ul class="cf-capture-notes hidden" id="cf-capture-notes"></ul>'
      + '</section>'

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
    const cadre = $("#cf-capture-frame");
    const vide = $("#cf-capture-empty");
    const rempl = $("#cf-capture-replace");
    if (cadre) cadre.classList.toggle("hidden", !i);

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
      : (analysee() ? quand(st().analyzed) : "pas encore"));
    txt("#cf-capture-note", !i
      ? "PNG, JPEG ou WebP. Au-delà de " + MAX_IMPORT_PX + " px de côté, le "
        + "serveur réduit l'image et répond ses dimensions réelles."
      : (SIDE === "recto"
        ? "« Analyser » mesure ce recto sur le serveur : bordure, zones, fond, "
          + "palette. C'est local et gratuit — aucun appel payant — et ça se "
          + "rejoue autant de fois qu'on veut."
        : "L'analyse porte sur le RECTO — bordure, zones et fond s'y mesurent. "
          + "Déposer un verso ne l'efface pas : il sert au dos de carte et à "
          + "l'objet 3D."));

    /* Le bouton n'existe que s'il y a de quoi mesurer, et il dit ce qu'il
       fera : ANALYSER une premiere fois, REMESURER ensuite. */
    const ana = $("#cf-capture-analyse");
    if (ana) {
      const recto = !!info("recto");
      ana.classList.toggle("hidden", !recto);
      ana.textContent = analysee() ? "Remesurer" : "Analyser";
    }
    const tog = $("#cf-capture-boxtog");
    if (tog) {
      const bs = st().boxes;
      tog.classList.toggle("hidden",
        !(SIDE === "recto" && !!i && Array.isArray(bs) && bs.length));
      tog.textContent = BOITES ? "Masquer les zones" : "Montrer les zones";
    }
    mesures();
    dessineBoites();
  }

  /* ═══════════════════════════════════════════════════════════════════════
     2bis. LE RELEVE — des chiffres, jamais un adjectif

     La regle de la spec §7.1.2 tient en une phrase : « l'ecran affiche le
     chiffre, jamais une certitude ». Il n'y a donc ici ni « bonne detection »
     ni « fond OK » : une epaisseur en mm et une confiance a deux decimales,
     un refus et la mesure qui l'a cause. Ce que l'analyse n'a pas su mesurer
     est ABSENT du releve et PRESENT dans les notes.
     ═══════════════════════════════════════════════════════════════════════ */
  function mesures() {
    const carte = $("#cf-capture-mesures");
    if (!carte) return;
    const s = st();
    const on = analysee() && SIDE === "recto";
    carte.classList.toggle("hidden", !on);
    if (!on) return;
    txt("#cf-capture-m-when", "mesuré le " + quand(s.analyzed));

    const e = isPlain(s.echelle) ? s.echelle : {};
    const px = Array.isArray(e.image_px) ? e.image_px : [];
    const mm = Array.isArray(e.carte_mm) ? e.carte_mm : [];
    const ec = s.ecart_ratio;
    bloc("#cf-capture-m-echelle", "Échelle", [
      px.length === 2 ? px[0] + " × " + px[1] + " px" : null,
      mm.length === 2 ? num(mm[0], 1) + " × " + num(mm[1], 1) + " mm"
        + (e.fmt ? " (format " + e.fmt + ")" : "") : null,
      estNombre(e.mm_par_px)
        ? num(e.mm_par_px * 1000, 3) + " µm par pixel" : null,
      /* L'ECART DE RATIO EST UNE MESURE, PAS UN ECHEC : les mm sont cales sur
         la LARGEUR, et cet ecart dit de combien la hauteur les dement. */
      estNombre(ec)
        ? "ratio image " + num(e.ratio_image, 4) + " contre "
          + num(e.ratio_format, 4) + " au format — écart "
          + (ec >= 0 ? "+" : "−") + num(Math.abs(ec) * 100, 1) + " %"
        : null,
    ], null);

    const b = isPlain(s.border) ? s.border : null;
    bloc("#cf-capture-m-bord", "Bordure", b ? [
      "bande de " + num(b.mm, 2) + " mm — " + String(b.color || "?"),
      estNombre(b.radius_mm)
        ? "rayon de coin estimé " + num(b.radius_mm, 2) + " mm"
        : "rayon de coin : non mesuré",
      Array.isArray(b.epaisseurs_mm) && b.epaisseurs_mm.length
        ? "les quatre bords : "
          + b.epaisseurs_mm.map((v) => num(v, 2)).join(" / ") + " mm"
        : null,
      "régularité " + num(b.regularite, 2) + " · netteté " + num(b.nettete, 2),
    ] : ["aucune bordure mesurable sur cette carte"],
      b ? b.confidence : null, b ? "" : "vide");

    const bx = Array.isArray(s.boxes) ? s.boxes : [];
    bloc("#cf-capture-m-zones", "Zones occupées",
      bx.length
        ? [bx.length + (bx.length > 1 ? " zones candidates" : " zone candidate")]
          .concat(bx.map((z, k) => isPlain(z)
            ? (k + 1) + " · " + num(z.w, 1) + " × " + num(z.h, 1) + " mm"
              + " en (" + num(z.x, 1) + " ; " + num(z.y, 1) + ") — densité "
              + num(z.densite, 2) + " · netteté " + num(z.nettete, 2)
            : null))
        : ["aucune zone candidate"],
      null, bx.length ? "" : "vide");

    const g = isPlain(s.bg) ? s.bg : null;
    if (g && g.bg_failed) {
      bloc("#cf-capture-m-fond", "Fond", [
        "détourage local refusé — " + String(g.motif || "mesure hors bornes"),
        "uniformité du pourtour " + num(g.uniformite, 2) + " pour un plancher "
          + "de " + num(g.seuil, 2),
        estNombre(g.couverture)
          ? "couverture retirée " + num(g.couverture * 100, 1) + " %"
          : null,
        String(g.option_ia || ""),
      ], null, "ko");
    } else if (g) {
      bloc("#cf-capture-m-fond", "Fond", [
        "pourtour " + String(g.color || "?"),
        estNombre(g.couverture)
          ? "le détourage garderait " + num(g.couverture * 100, 1)
            + " % de l'image" : null,
      ], g.confidence);
    } else {
      bloc("#cf-capture-m-fond", "Fond", ["non mesuré"], null, "vide");
    }

    const pal = Array.isArray(s.palette) ? s.palette : [];
    const hote = bloc("#cf-capture-m-pal", "Palette",
      [pal.length ? pal.length + " teintes dominantes" : "non mesurée"],
      null, pal.length ? "" : "vide");
    if (hote && pal.length) {
      const rang = document.createElement("div");
      rang.className = "cf-capture-pastilles";
      pal.forEach((c) => {
        if (!isPlain(c) || !/^#[0-9a-f]{6}$/i.test(String(c.hex))) return;
        const p = document.createElement("span");
        p.className = "cf-capture-pastille";
        /* La couleur vient du document : elle passe par `style`, jamais par
           une chaine de HTML (regle 14), et seulement apres le motif ci-dessus. */
        p.style.background = String(c.hex);
        p.title = String(c.hex)
          + (estNombre(c.part) ? " — " + num(c.part * 100, 1) + " %" : "");
        rang.appendChild(p);
      });
      hote.appendChild(rang);
    }

    const notes = Array.isArray(s.notes) ? s.notes : [];
    const ul = $("#cf-capture-notes");
    if (ul) {
      while (ul.firstChild) ul.removeChild(ul.firstChild);
      ul.classList.toggle("hidden", !notes.length);
      notes.forEach((n) => {
        const li = document.createElement("li");
        li.textContent = String(n);
        ul.appendChild(li);
      });
    }
  }

  /* L'INCRUSTATION DES BOITES — de l'HTML par-dessus l'<img>, PAS un painter.
     P10 n'a aucun z (spec §9.4) : elle ne dessine pas la carte du jeu, et la
     carte importee n'est pas cette carte-la. Les rectangles sont poses en
     POURCENTAGES de `echelle.carte_mm`, donc dans la meme unite que `boxes` —
     aucune conversion de pixels d'ecran, aucune mesure de mise en page. */
  function dessineBoites() {
    const hote = $("#cf-capture-boxes");
    if (!hote) return;
    while (hote.firstChild) hote.removeChild(hote.firstChild);
    const s = st();
    const e = isPlain(s.echelle) ? s.echelle : null;
    const bs = Array.isArray(s.boxes) ? s.boxes : [];
    const mm = e && Array.isArray(e.carte_mm) ? e.carte_mm : null;
    const lw = mm ? Number(mm[0]) : 0;
    const lh = mm ? Number(mm[1]) : 0;
    const on = BOITES && SIDE === "recto" && !!info("recto") && analysee()
      && bs.length > 0 && lw > 0 && lh > 0;
    hote.classList.toggle("hidden", !on);
    if (!on) return;
    bs.forEach((b, k) => {
      if (!isPlain(b)) return;
      const el = document.createElement("span");
      el.className = "cf-capture-box";
      el.style.left = (100 * (Number(b.x) || 0) / lw) + "%";
      el.style.top = (100 * (Number(b.y) || 0) / lh) + "%";
      el.style.width = (100 * (Number(b.w) || 0) / lw) + "%";
      el.style.height = (100 * (Number(b.h) || 0) / lh) + "%";
      el.title = "zone " + (k + 1) + " — " + num(b.w, 1) + " × " + num(b.h, 1)
        + " mm, densité " + num(b.densite, 2);
      const n = document.createElement("i");
      n.textContent = String(k + 1);
      el.appendChild(n);
      hote.appendChild(el);
    });
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
      analyzed: null, echelle: null, ecart_ratio: null,
      border: null, boxes: [], bg: null, palette: [], notes: [],
      layers: {},
    };
  }

  /* CE QU'UN RELEVE DU BACKEND DEVIENT DANS LE DOCUMENT — et rien d'autre.
     `patchAs` LEVE sur une cle hors schema : recopier la reponse telle quelle
     ferait tomber le geste entier le jour ou le backend en publierait une de
     plus. On CHOISIT les cles, et on donne a chacune un defaut du bon type
     (une valeur `undefined` ne serait meme pas serialisable). */
  function releve(d) {
    const r = isPlain(d) ? d : {};
    const n = Number(r.analyzed);
    return {
      analyzed: isFinite(n) && n > 0 ? n : Date.now(),
      echelle: isPlain(r.echelle) ? r.echelle : null,
      ecart_ratio: estNombre(r.ecart_ratio) ? r.ecart_ratio : null,
      border: isPlain(r.border) ? r.border : null,
      boxes: Array.isArray(r.boxes) ? r.boxes : [],
      bg: isPlain(r.bg) ? r.bg : null,
      palette: Array.isArray(r.palette) ? r.palette : [],
      notes: Array.isArray(r.notes) ? r.notes.map(String) : [],
    };
  }
  function wire(host) {
    const pick = host.querySelector("#cf-capture-pick");
    const rempl = host.querySelector("#cf-capture-replace");
    const file = host.querySelector("#cf-capture-file");
    const drop = host.querySelector("#cf-capture-drop");
    const ana = host.querySelector("#cf-capture-analyse");
    const tog = host.querySelector("#cf-capture-boxtog");
    const ouvre = () => { if (file) { file.value = ""; file.click(); } };
    if (pick) pick.addEventListener("click", ouvre);
    if (rempl) rempl.addEventListener("click", ouvre);
    if (ana) ana.addEventListener("click", () => { analyser(); });
    if (tog) tog.addEventListener("click", () => { BOITES = !BOITES; paint(); });
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

  /* UNE ROUTE ABSENTE N'EST PAS UN REFUS NOMME, et le code HTTP ne les
     distingue pas : ces routes rendent un 404 « Deck introuvable » quand le
     jeu a ete supprime dans un autre onglet. Traduire tout 404 en « backend
     absent » declarait le domaine ETEINT parce qu'un jeu avait disparu — le
     CORE a deja paye ce bug et ecrit son remede (core.js:jsonNamed, §9bis) :
     la question se tranche sur le TYPE DE REPONSE. Du HTML (le catch-all
     SPA) = il n'y a pas de route ; du JSON = le backend parle, et c'est SA
     phrase qui doit arriver.

     UN SEUL ENDROIT POUR DEUX APPELS. La regle vivait dans `upload()` ; T2 a
     ajoute `analyser()`, et une regle recopiee est une regle qui derive — le
     deuxieme appel aurait pu perdre la nuance sans que rien ne rougisse. */
  async function lireJson(resp) {
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
    return d || {};
  }

  function panne(e, quoi) {
    return e && e.missing ? "backend absent : " + quoi + " exige /api/cards"
      : String((e && e.message) || e);
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
      const d = await lireJson(await M.api.raw(
        "POST", "card?side=" + encodeURIComponent(side), f));
      const maj = {};
      Object.keys(sources()).forEach((k) => { maj[k] = sources()[k]; });
      maj[side] = { w: d.w, h: d.h, bytes: d.bytes, stamp: d.stamp };
      M.patch(Object.assign({ sources: maj }, effacements(side)));
      paint();
      M.toast("carte importée — " + d.w + " × " + d.h + " px, " + weight(d.bytes));
    } catch (e) {
      M.toast(panne(e, "l'import"), true);
    } finally {
      BUSY = false;
      M.busy(false);
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     4. LE GESTE « ANALYSER »

     Un geste EXPLICITE, et separe du depot (plan D3 precise T2) : deposer une
     image ne declenche aucun calcul, et l'analyse se rejoue sans redeposer —
     elle court sur le recto STOCKE.

     C'EST ICI QUE LE DOCUMENT S'ECRIT. La route repond, la piece publie :
     `M.patch` passe par la voie d'autosave unique du CORE, une seule main sur
     `doc.capture`. Le meme verrou BUSY que l'import : mesurer pendant qu'un
     fichier monte mesurerait l'image d'avant.
     ═══════════════════════════════════════════════════════════════════════ */
  async function analyser() {
    if (BUSY) { M.toast("un traitement est déjà en cours"); return; }
    if (!info("recto")) {
      M.toast("déposez d'abord un recto : l'analyse porte sur lui", true);
      return;
    }
    BUSY = true;
    try {
      M.busy(true, "analyse du recto…");
      const r = releve(await lireJson(await M.api.raw("POST", "analyse")));
      M.patch(r);
      paint();
      const b = isPlain(r.border) ? r.border : null;
      M.toast("recto analysé — "
        + (b ? "bordure " + num(b.mm, 2) + " mm (" + conf(b.confidence) + ")"
             : "aucune bordure mesurable")
        + ", " + r.boxes.length + " zone" + (r.boxes.length > 1 ? "s" : "")
        + ", " + r.palette.length + " teintes");
    } catch (e) {
      M.toast(panne(e, "l'analyse"), true);
    } finally {
      BUSY = false;
      M.busy(false);
    }
  }

})();
