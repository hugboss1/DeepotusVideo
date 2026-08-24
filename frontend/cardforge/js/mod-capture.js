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
  /* LES VOIES DE DETOURAGE DE CE POSTE, LUES UNE FOIS AU MONTAGE.
     De la CAPACITE DE MACHINE, pas du document : « rembg est-il installe
     ici ? une cle fal est-elle posee ? » n'a rien a faire dans un jeu de
     cartes qu'on peut ouvrir sur un autre ordinateur. Lu une fois par
     panneau, pas a chaque peinture : une requete par repeinture ferait une
     rafale a chaque evenement du document, et le prix clignoterait.
     `null` = on ne sait pas encore (ou on n'a pas pu savoir) ; l'ecran ne
     propose alors rien, ce qui est la bonne reponse dans les deux cas. */
  let IA = null;
  let IA_ERR = "";
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
      boxes: [],          /* [{x, y, w, h, densite, nettete, tronquee}] — en MM */
      /* La bande, EN MM, que la recherche de zones exclut le long des quatre
         bords (bordure + portee du filtre). Elle n'est pas un detail : une
         boite qui la touche est COUPEE, pas mesuree — elle porte `tronquee`,
         et l'ecran le dit avant que P3 en fasse un slot. */
      zones_bande_mm: null,
      bg: null,           /* {color, confidence} ou le refus mesure */
      palette: [],        /* [{hex, part}] dominantes */
      notes: [],          /* ce que l'analyse n'a PAS pu mesurer, et pourquoi */
      layers: {},         /* les PNG isoles ranges cote serveur */
    },

    init(host) {
      host.innerHTML = shell();
      wire(host);
      paint();
      /* LES OPTIONS PARTENT AVANT LA PREMIERE PEINTURE ET N'ATTENDENT PAS :
         l'ecran se peint tout de suite (sans le bloc IA), et le bloc apparait
         quand la reponse arrive. Attendre le reseau pour afficher un panneau
         d'import serait payer une capacite optionnelle avec le temps de
         chargement de tout le reste. */
      chargeOptions();
      /* Le document peut changer sous nos pieds : un autre onglet, une
         adoption, un jeu rouvert. On repeint sur l'evenement, jamais sur une
         copie gardee au chaud. */
      CF.on("core:doc", (e) => {
        if (!e || e.id === "capture" || e.id === "name" || e.id === "format") paint();
      });
      /* UN AUTRE JEU : ON REPEINT D'ABORD, ON RELIT ENSUITE — et l'ordre est
         une CORRECTION, pas un detail de style. `chargeOptions` ATTEND un
         fetch, et le fetch du CORE n'a pas de delai d'attente : sur un
         backend lent ou un processus orphelin (le scenario documente de ce
         depot), peindre APRES laissait a l'ecran l'apercu, les mesures ET LE
         SUJET du jeu PRECEDENT, sans fin. C'est exactement le defaut que
         `_oublie_sujet` venait de tuer cote serveur.
         Ce qui est local est instantane et passe devant ; ce qui depend du
         reseau arrive quand il arrive (les voies ne dependent pas du jeu,
         mais la CLE fal a pu etre posee dans les Reglages entre-temps, et
         c'est le seul moment ou l'ecran repasse par ici sans rechargement). */
      CF.on("core:deck", () => { paint(); chargeOptions(); });
      /* LE FORMAT PEUT BOUGER SOUS LES MESURES. Le CORE l'annonce
         (core.js:424) ; sans cette ligne, l'ecran gardait sa pastille verte et
         ses millimetres d'avant sur un jeu qui avait change de format. */
      CF.on("core:geom", () => paint());
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

  /* LE FORMAT A-T-IL BOUGE SOUS LES MESURES ? Une fonction PURE, et c'est
     delibere : le test l'execute au lieu de lire sa forme.

     Le releve porte le format sur lequel il a ete calcule (`echelle.fmt`) ;
     le document, lui, peut changer de format a tout moment par le widget de
     la barre. Apres un passage poker -> tarot, l'ecran continuait d'afficher
     « 63,0 x 88,0 mm (poker_eu) » sur un jeu tarot : des millimetres faux de
     11 %, presentes comme mesures. Le piege etait NOMME dans un commentaire
     et pas ferme — le CORE emet pourtant `core:geom` a chaque changement. */
  function divergence(echelle, doc) {
    if (!isPlain(echelle) || !isPlain(doc) || !isPlain(doc.format)) return null;
    const avant = String(echelle.fmt || "");
    const apres = String(doc.format.fmt || "");
    if (!avant || !apres || avant === apres) return null;
    return { avant: avant, apres: apres };
  }

  /* L'INCRUSTATION EST-ELLE POSSIBLE ? Une seule reponse pour deux endroits.
     La visibilite du bouton tenait au seul `boxes.length` quand le dessin,
     lui, exige AUSSI l'echelle : un document venu d'une version anterieure
     (des boites, pas d'echelle) montrait un bouton qui ne faisait rien. */
  function peutIncruster(s) {
    const e = isPlain(s) && isPlain(s.echelle) ? s.echelle : null;
    const bs = isPlain(s) && Array.isArray(s.boxes) ? s.boxes : [];
    const mm = e && Array.isArray(e.carte_mm) ? e.carte_mm : null;
    return !!(bs.length && mm && estNombre(mm[0]) && estNombre(mm[1])
      && mm[0] > 0 && mm[1] > 0);
  }

  /* LA LISTE BLANCHE DES NOMS SERVIS — miroir de capture.py:FILE_RE, RECOPIE
     et non partage (regle 8), et c'est la SECONDE copie d'ecran (mod-face.js
     porte l'autre, pour l'adoption P1). Ce que ce motif garde : le nom d'un
     fichier arrive par le DOCUMENT, donc du dehors — un document rapporte
     d'une autre machine, ecrit par une version plus ancienne, ou simplement
     abime. Il ne devient une URL qu'apres etre passe par ici. P1 se fait
     verifier cette garde par execution ; P10 doit tenir le meme standard. */
  const CAPTURE_FILE_RE = /^(?:source_(?:recto|verso)|sujet_recto)\.png$/;

  /* Le nom de fichier d'une couche du document, FILTRE — "" si le document
     dit n'importe quoi. */
  function fichierSujet(s) {
    const n = isPlain(s) ? String(s.file || "") : "";
    return CAPTURE_FILE_RE.test(n) ? n : "";
  }

  /* LA COUCHE « SUJET » RANGEE PAR LE BACKEND, lue avec tolerance. Le nom du
     fichier est SERVEUR (la liste blanche de capture.py le fabrique) : on ne
     le compose pas ici, on lit celui qui a ete publie — et on le repasse par
     la liste blanche avant d'en faire quoi que ce soit. */
  function sujetInfo() {
    const l = st().layers;
    const s = isPlain(l) ? l.sujet : null;
    return fichierSujet(s) ? s : null;
  }

  /* L'OFFRE DE DETOURAGE — une fonction PURE, et c'est delibere : le test de
     la piece l'EXECUTE dans node au lieu de lire sa forme (lecon T1, le
     `|| true` qu'un controle textuel ne voit pas).

     Elle repond a une seule question : « propose-t-on le bouton, et que
     dit-il ? ». Trois raisons de ne rien proposer, et chacune a son motif
     ecrit : on ne sait pas encore (ou on n'a pas pu savoir), aucune voie
     n'existe sur ce poste, ou il n'y a pas de recto a detourer.

     LE PRIX N'EST PAS ECRIT ICI. Il arrive dans `o.prix_usd`, que la route a
     lu dans la table de tarifs de l'application. Un tarif absent de la table
     ne devient PAS zero et ne devient pas un montant de repli : le bouton
     dit « tarif non tabule » et reste cliquable — le fournisseur facturera
     ce qu'il facture, et l'ecran ne pretend pas le savoir. */
  function offreIA(o, aRecto) {
    const s = isPlain(o) ? o : null;
    const voie = s && (s.voie === "local" || s.voie === "fal") ? s.voie : null;
    const off = { on: false, voie: voie, gratuit: voie === "local",
      libelle: "Détourer le sujet", motif: "" };
    if (!s) {
      off.motif = "les voies de détourage n'ont pas encore été lues sur ce poste";
      return off;
    }
    if (!voie) {
      off.motif = String(s.motif
        || "aucune voie de détourage n'est disponible sur ce poste");
      return off;
    }
    if (!aRecto) {
      off.motif = "déposez d'abord un recto : le sujet s'isole sur lui";
      return off;
    }
    /* SANS PRIX TABULE, LA VOIE PAYANTE N'EST PAS OFFERTE. §8 dit « prix
       AVANT » : un bouton payant sans chiffre n'est pas un libelle honnete,
       c'est un ecart de spec. La route tient deja cette regle ; l'ecran la
       tient AUSSI — un backend d'une version anterieure ne doit pas pouvoir
       faire naitre ce bouton-la. La voie GRATUITE, elle, ne depend d'aucun
       tarif. */
    if (voie === "fal" && !estNombre(s.prix_usd)) {
      off.voie = null;
      off.motif = "le tarif du détourage n'est pas dans la table de "
        + "l'application (Réglages → Tarifs et budget) : le prix se dit AVANT "
        + "l'appel, donc l'option payante n'est pas proposée";
      return off;
    }
    off.on = true;
    off.libelle = voie === "local"
      ? "Détourer le sujet — gratuit (local)"
      : "Détourer le sujet (fal, ~" + num(s.prix_usd, 3) + " $)";
    return off;
  }

  /* LES LIGNES DU BLOC « FOND », branchees sur la PORTE QUI A REFUSE.
     L'ecran posait toujours l'uniformite en tete : sur un refus par
     couverture on lisait « uniformite 1,00 pour un plancher de 0,60 » — un
     chiffre qui PASSE, donne pour cause du refus — puis la couverture sans
     ses bornes, alors que le backend les publie. Le JSON disait juste,
     l'ecran mentait ; c'est l'ecran qu'on corrige. */
  function lignesFond(g) {
    if (!isPlain(g)) return ["non mesuré"];
    if (!g.bg_failed) {
      return ["pourtour " + String(g.color || "?"),
        estNombre(g.couverture)
          ? "le détourage garderait " + num(g.couverture * 100, 1)
            + " % de l'image" : null];
    }
    const motif = String(g.motif || "mesure hors bornes");
    const bornes = Array.isArray(g.couverture_bornes) ? g.couverture_bornes : null;
    const tete = "détourage local refusé — " + motif;
    const uni = "uniformité du pourtour " + num(g.uniformite, 2)
      + " pour un plancher de " + num(g.seuil, 2);
    const couv = estNombre(g.couverture)
      ? "couverture retirée " + num(g.couverture * 100, 1) + " %"
        + (bornes && estNombre(bornes[0]) && estNombre(bornes[1])
          ? " — attendue entre " + num(bornes[0] * 100, 0) + " % et "
            + num(bornes[1] * 100, 0) + " %" : "")
      : null;
    /* La MESURE QUI A REFUSE vient en premier ; l'autre suit, pour situer. */
    const ordre = motif.indexOf("uni") === 0 || motif.indexOf("pourtour") === 0
      ? [uni, couv] : [couv, uni];
    /* LA PROMESSE A MAINTENANT UNE SUITE. T2 refusait le detourage local en
       annoncant « une option payante, proposee a part avec son prix » — et
       cette option n'existait nulle part. Elle existe : le bloc ci-dessous,
       qui dit les voies de CE poste et le prix venu de la table. Sans ce
       renvoi, la phrase envoyait chercher ailleurs. */
    return [tete].concat(ordre).concat(g.option_ia
      ? [String(g.option_ia),
        "Le bloc « Détourage IA », plus bas, dit ce que ce poste sait faire "
        + "et à quel prix."]
      : [null]);
  }

  /* ═══════════════════════════════════════════════════════════════════════
     1ter. LE PARCOURS GUIDE, ET LA PUBLICATION VERS LA 3D

     Quatre fonctions PURES, et c'est delibere : le test de la piece les
     EXECUTE dans node (lecon T1, le `|| true` qu'un controle textuel ne voit
     pas). Elles ne touchent ni au DOM ni au reseau — elles repondent a
     quatre questions, et rien d'autre.
     ═══════════════════════════════════════════════════════════════════════ */

  /* LES QUATRE ETAPES DU PARCOURS §7.2:564-570 — DES LIENS, PAS UN ASSISTANT.
     Le plan (D10) a tranche et l'avoue : un wizard modal serait du chrome
     sans substance. Les quatre capacites EXISTENT deja, chacune chez elle ;
     ce qui manquait n'etait pas une machine a etapes, c'etait de savoir OU
     ELLES SONT quand on arrive d'une carte qu'on vient de reprendre.

     LA TABLE EST DANS LA FONCTION, et pas a cote : elle voyage avec la regle
     que le test execute. Chaque etape porte la piece a ouvrir, les
     SELECTEURS de son ancre (le premier trouve gagne — une voisine peut
     n'en rendre qu'un selon son etat) et, s'il le faut, les commandes a
     CLIQUER pour deplier ce qui est escamote (un onglet, un repli).

     LE COUPLAGE EST AVOUE. Ces selecteurs appartiennent a P1 et P2 ; P10 ne
     les rend pas. C'est un contrat entre pieces, donc il se teste : le banc
     lit mod-face.js et mod-frame.js et exige que chaque aiguille y soit
     ecrite. Un lien mort ferait douter du clic — la lecon deja payee par le
     bouton des zones (T2).

     ET LE PARCOURS N'EXISTE QUE SI UNE CAPTURE EST PUBLIEE (D10). Quatre
     liens vers un travail qui n'a pas commence ne guident personne. */
  function parcours(s) {
    const d = isPlain(s) ? s : {};
    const src = isPlain(d.sources) ? d.sources : {};
    if (!isPlain(src.recto)) return [];
    return [
      { id: "illustration", piece: "face",
        titre: "Importer l'illustration",
        quoi: "la pile d'images de la pièce Illustration — ou, d'un clic, "
          + "« adopter » ce qui vient d'être repris ici",
        ouvre: ['#cf-face-tabs button[data-tab="imp"]'],
        cibles: ["#cf-face-adopt", "#cf-face-drop", "#cf-face-pane-imp"] },
      { id: "bordure", piece: "frame",
        titre: "Choisir ou importer la bordure",
        quoi: "le catalogue de familles, et « adopter la bordure » qui pose "
          + "les mesures relevées sur la carte reprise",
        ouvre: [],
        cibles: [".cff-adopt", ".cff-grid"] },
      { id: "sceau", piece: "frame",
        titre: "Régler le Sceau prismatique",
        quoi: "métal, largeur de bande, et les trois portées — écran, "
          + "impression, 3D — réglables séparément",
        ouvre: [],
        cibles: [".cff-grp-sceau"] },
      { id: "verso", piece: "frame",
        titre: "Éditer le verso",
        quoi: "le dos de carte : motif du catalogue, image importée et "
          + "calques de texture",
        ouvre: [],
        cibles: [".cff-grp-dos", "#cf-frame-backdrop"] },
    ];
  }

  /* LE BOUTON « PUBLIER VERS LA 3D » EXISTE-T-IL ? (dette R5 de T5.)

     Deux conditions, et chacune a sa raison : sans recto il n'y a rien a
     decrire, et sans MESURE le manifeste parlerait d'une face que personne
     n'a regardee. Le refus PORTE SON MOTIF — un bouton absent sans
     explication envoie chercher une panne. */
  function offrePublier(s) {
    const d = isPlain(s) ? s : {};
    const src = isPlain(d.sources) ? d.sources : {};
    const off = { on: false, motif: "" };
    if (!isPlain(src.recto)) {
      off.motif = "déposez d'abord un recto : c'est lui que la Forge 3D "
        + "recevra en couche.";
      return off;
    }
    if (!d.analyzed) {
      off.motif = "analysez le recto d'abord : le manifeste porte le format "
        + "et les millimètres de la mesure.";
      return off;
    }
    off.on = true;
    return off;
  }

  /* CE QUE LE BORDEREAU DE LA ROUTE DEVIENT COMME PHRASE. Le toast ne recite
     pas un texte appris : il REPREND ce que le serveur vient d'ecrire —
     combien de couches, lesquelles, sous quel nom de manifeste et a quel
     format. Une reponse vide se DIT vide plutot que d'annoncer un succes. */
  function bordereau(d) {
    const r = isPlain(d) ? d : {};
    const m = isPlain(r.layers) ? r.layers : {};
    const ls = Array.isArray(m.layers) ? m.layers : [];
    if (!isPlain(r.layers)) {
      return "publication terminée, mais le serveur n'a pas rendu de "
        + "bordereau : ouvrez la pièce Forge 3D pour voir ce qui a été écrit.";
    }
    const roles = [];
    ls.forEach((l) => { if (isPlain(l) && l.role) roles.push(String(l.role)); });
    const n = ls.length;
    if (!n) {
      return "aucune couche publiée : le manifeste est vide (redéposez le "
        + "recto, puis relancez).";
    }
    const toile = Array.isArray(m.canvas_px) ? m.canvas_px : null;
    return n + (n > 1 ? " couches publiées" : " couche publiée")
      + " vers la Forge 3D"
      + (roles.length ? " — " + roles.join(" · ") : "")
      + " (" + String(r.manifeste || "manifeste sans nom")
      + (m.format ? ", format " + String(m.format) : "")
      + (toile && toile.length === 2
        ? ", toile " + toile[0] + " × " + toile[1] + " px" : "")
      + ")";
  }

  /* DEPLIER CE QUI EST SUR LE CHEMIN. Une ancre sous un `<details>` ferme est
     une ancre invisible : le clic aurait l'air de n'avoir rien fait. On
     remonte donc la lignee et on ouvre.

     PURE AU SENS OU ELLE NE CONNAIT QUE `parentNode`, `tagName` et `open` :
     le test la joue dans node sur un arbre de mensonge, sans navigateur. Le
     garde-fou de profondeur n'est pas de la superstition — un `parentNode`
     circulaire (moteur exotique, arbre detache mal forme) ferait tourner la
     page a l'infini pour un lien de navigation. */
  function deplie(cible) {
    let n = cible;
    let ouverts = 0;
    let garde = 0;
    while (n && n.nodeType === 1 && garde++ < 64) {
      if (n.tagName === "DETAILS" && n.open === false) {
        n.open = true;
        ouverts++;
      }
      n = n.parentNode;
    }
    return ouverts;
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
      /* LE FORMAT A BOUGE : un bandeau, et pas une pastille discrete. Les
         millimetres du releve ne decrivent plus la carte du jeu. */
      + '<p class="cf-capture-alerte hidden" id="cf-capture-m-diverge"></p>'
      + '<div class="cf-capture-mgrid">'
      + '<div class="cf-capture-mes" id="cf-capture-m-echelle"></div>'
      + '<div class="cf-capture-mes" id="cf-capture-m-bord"></div>'
      + '<div class="cf-capture-mes" id="cf-capture-m-zones"></div>'
      + '<div class="cf-capture-mes" id="cf-capture-m-fond"></div>'
      + '<div class="cf-capture-mes" id="cf-capture-m-pal"></div>'
      + '</div>'
      + '<ul class="cf-capture-notes hidden" id="cf-capture-notes"></ul>'
      + '</section>'

      /* ── LE DÉTOURAGE IA (spec §7.1.3) ──────────────────────────────────
         OPT-IN, et la section n'existe QUE si une voie existe : proposer un
         bouton payant sur un poste sans clé, ou gratuit sans rembg, ce
         serait une promesse qui échoue au clic. Le libellé PORTE le prix
         quand la voie est payante — le tarif vient de la route (qui le lit
         dans pricing.json), jamais d'une copie écrite ici. */
      + '<section class="cf-capture-card hidden" id="cf-capture-ia">'
      + '<header class="cf-capture-h"><b>Détourage IA</b>'
      + '<span class="cf-capture-sub">isoler le sujet du recto — une option, jamais une étape obligée</span>'
      + '<span class="cf-capture-spacer"></span>'
      + '<span class="cf-capture-state" id="cf-capture-ia-etat">—</span>'
      + '</header>'
      + '<div class="cf-capture-body">'
      + '<div class="cf-capture-drop">'
      + '<div class="cf-capture-preview">'
      + '<span class="cf-capture-frame hidden" id="cf-capture-sujet-cadre">'
      + '<img class="cf-capture-img hidden" id="cf-capture-sujet" alt="" draggable="false">'
      + '</span>'
      + '<p class="cf-capture-empty" id="cf-capture-ia-vide">Le sujet détouré s\'affichera ici.</p>'
      + '</div>'
      + '<div class="cf-capture-actions">'
      + '<button class="btn sm" id="cf-capture-detour" type="button">Détourer le sujet</button>'
      + '<span class="cf-capture-spacer"></span>'
      + '</div>'
      + '</div>'
      + '<div class="cf-capture-side">'
      + '<p class="hint" id="cf-capture-ia-note"></p>'
      + '</div>'
      + '</div>'
      + '</section>'

      /* ── ET MAINTENANT (spec §7.2:564-570, plan D10) ────────────────────
         Les quatre capacités réelles du parcours, en LIENS. Pas de fenêtre
         modale, pas d'étapes à cocher : chacune ouvre la pièce concernée,
         déplie ce qui est escamoté et amène l'ancre sous les yeux.
         Et, dessous, le geste qui manquait à §7.1.6 : publier les couches
         importées vers la Forge 3D. */
      + '<section class="cf-capture-card cf-capture-suite hidden" id="cf-capture-suite">'
      + '<header class="cf-capture-h"><b>Et maintenant</b>'
      + '<span class="cf-capture-sub">quatre gestes, chacun chez la pièce qui le sait faire</span>'
      + '</header>'
      + '<ol class="cf-capture-etapes" id="cf-capture-etapes"></ol>'
      + '<div class="cf-capture-pub">'
      + '<button class="btn strong sm hidden" id="cf-capture-publier" type="button" title="Écrit les couches importées dans le manifeste que la pièce Forge 3D sait lire — local, gratuit, rejouable">Publier vers la 3D</button>'
      + '<p class="hint" id="cf-capture-pub-note"></p>'
      + '</div>'
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
      /* LA MEME CONDITION QUE LE DESSIN. Un bouton qui s'affiche sans pouvoir
         agir est pire qu'un bouton absent : il fait douter du clic. */
      tog.classList.toggle("hidden",
        !(SIDE === "recto" && !!i && peutIncruster(st())));
      tog.textContent = BOITES ? "Masquer les zones" : "Montrer les zones";
    }
    mesures();
    blocIA();
    suite();
    dessineBoites();
  }

  /* ═══════════════════════════════════════════════════════════════════════
     2quater. « ET MAINTENANT » — le parcours guidé et la publication 3D

     Tout se DERIVE du document (patron sectionsBasses) : ni la liste ni le
     bouton ne gardent un etat d'ecran. Un jeu rouvert sans capture n'a pas
     de section ; un recto sans mesure a la liste mais pas le bouton, et la
     note dit pourquoi.
     ═══════════════════════════════════════════════════════════════════════ */
  function suite() {
    const carte = $("#cf-capture-suite");
    if (!carte) return;
    const s = st();
    const pas = parcours(s);
    carte.classList.toggle("hidden", !pas.length);
    const ol = $("#cf-capture-etapes");
    if (ol) {
      while (ol.firstChild) ol.removeChild(ol.firstChild);
      pas.forEach((e) => {
        const li = document.createElement("li");
        li.className = "cf-capture-etape";
        const b = document.createElement("button");
        b.type = "button";
        b.className = "lnk cf-capture-go";
        b.textContent = e.titre;
        b.title = "Ouvre la pièce « " + String(e.piece) + " » et amène la "
          + "section sous les yeux";
        b.addEventListener("click", () => aller(e));
        li.appendChild(b);
        const q = document.createElement("span");
        q.className = "cf-capture-quoi";
        q.textContent = " — " + e.quoi;
        li.appendChild(q);
        ol.appendChild(li);
      });
    }
    const off = offrePublier(s);
    const b = $("#cf-capture-publier");
    if (b) {
      b.classList.toggle("hidden", !off.on);
      b.disabled = !!BUSY;
    }
    txt("#cf-capture-pub-note", off.on
      ? "Écrit le manifeste des couches importées dans le dossier de la "
        + "pièce Forge 3D : la face reprise (et le sujet détouré s'il "
        + "existe) deviennent des sources de nœuds. Local, gratuit, "
        + "rejouable — un nouveau format se republie."
      : off.motif);
  }

  /* UNE ETAPE-LIEN : ouvrir la piece, deplier ce qui la cache, poser l'ancre
     sous les yeux. Et le DIRE quand la destination n'existe pas dans cette
     version de l'ecran — une piece qui a change d'id ne doit pas se solder
     par un clic sans effet.

     LE DEPLI DU RAIL PASSE PAR SON PROPRE BOUTON. Le CORE n'expose pas
     `setFold` (c'est une preference d'ecran, pas un contrat de module) : on
     clique le chevron, exactement comme un humain — aucune API nouvelle,
     aucun etat duplique. */
  function aller(e) {
    if (!e || !e.piece) return;
    try { CF.show(e.piece); } catch (x) {
      M.toast("la pièce « " + String(e.piece) + " » n'existe pas sur cette "
        + "version : " + String((x && x.message) || x), true);
      return;
    }
    deplieRail();
    (e.ouvre || []).forEach((sel) => {
      const c = document.querySelector(sel);
      if (c && typeof c.click === "function") c.click();
    });
    let cible = null;
    (e.cibles || []).forEach((sel) => {
      if (!cible) cible = document.querySelector(sel);
    });
    if (!cible) {
      M.toast("la pièce est ouverte, mais la section « " + String(e.titre)
        + " » n'a pas été trouvée dans cette version de l'écran.", true);
      return;
    }
    /* DEPUIS LA CIBLE ELLE-MEME, et non depuis son parent : deux des quatre
       ancres SONT le `<details>` (le Sceau, le dos de carte). Deplier a
       partir du parent les aurait laisses fermes — le clic aurait defile
       jusqu'a un titre replie. */
    deplie(cible);
    if (typeof cible.scrollIntoView === "function") {
      cible.scrollIntoView({ block: "nearest" });
    }
    /* UN CLIGNOTEMENT COURT, pour que l'oeil retrouve OU il vient d'arriver.
       La classe se retire toute seule : un surlignage qui reste devient un
       etat, et un etat qu'on n'a pas demande.

       UN SEUL SURLIGNAGE A LA FOIS. Mesure au navigateur : deux etapes
       cliquees a moins de 1,4 s d'intervalle laissaient DEUX cibles cernees
       — celle qu'on regarde et celle d'avant, chez une autre piece. Le
       repere ne repere plus rien quand il y en a deux. */
    Array.prototype.forEach.call(
      document.querySelectorAll(".cf-capture-vise"),
      (e) => e.classList.remove("cf-capture-vise"));
    cible.classList.add("cf-capture-vise");
    setTimeout(() => cible.classList.remove("cf-capture-vise"), 1400);
  }

  function deplieRail() {
    const root = document.querySelector(".cf");
    const b = document.getElementById("railFoldBtn");
    if (root && b && root.classList.contains("rail-replie")
      && typeof b.click === "function") {
      b.click();
      return true;
    }
    return false;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     2ter. LE BLOC « DETOURAGE IA »

     Il ne lit RIEN du reseau : `IA` a ete rempli une fois au montage. Ce que
     cette fonction fait est de la peinture pure, sur deux sources — l'offre
     (capacite du poste) et la couche deja rangee (etat du jeu).
     ═══════════════════════════════════════════════════════════════════════ */
  function blocIA() {
    const carte = $("#cf-capture-ia");
    if (!carte) return;
    const off = offreIA(IA, !!info("recto"));
    const suj = sujetInfo();
    /* LA SECTION SE MONTRE DES QU'IL Y A QUELQUE CHOSE A DIRE : une offre,
       ou une couche deja produite. Un poste sans voie ne voit rien — sauf
       s'il en a produit une avant (jeu rapporte d'une autre machine), auquel
       cas la cacher effacerait une matiere que P1 peut encore adopter. */
    carte.classList.toggle("hidden", !off.on && !suj && !IA_ERR);

    const b = $("#cf-capture-detour");
    if (b) {
      b.classList.toggle("hidden", !off.on);
      b.textContent = suj ? off.libelle.replace("Détourer", "Redétourer")
        : off.libelle;
      b.title = off.on && off.gratuit
        ? "rembg tourne sur cette machine : aucun appel, aucune dépense"
        : "l'image part chez le fournisseur, qui facture directement — le "
          + "tarif affiché vient de Réglages → Tarifs et budget";
      b.disabled = !!BUSY;
    }
    const etat = $("#cf-capture-ia-etat");
    if (etat) {
      etat.textContent = suj ? "sujet isolé" : (off.on ? "disponible" : "indisponible");
      etat.className = "cf-capture-state" + (suj ? " ok" : (off.on ? " on" : ""));
    }
    const img = $("#cf-capture-sujet");
    const cadre = $("#cf-capture-sujet-cadre");
    const vide = $("#cf-capture-ia-vide");
    if (cadre) cadre.classList.toggle("hidden", !suj);
    if (vide) vide.classList.toggle("hidden", !!suj);
    if (img) {
      if (suj) {
        /* MEME PRECAUTION QUE L'APERCU DU RECTO : `onerror` avant `src`, et
           l'horodatage en millisecondes pour casser le cache — sans lui, un
           second detourage reafficherait le premier. */
        img.onerror = () => {
          img.classList.add("hidden");
          if (vide) {
            vide.classList.remove("hidden");
            vide.textContent = "La couche détourée ne se charge plus (fichier "
              + "absent côté serveur). Relancez le détourage.";
          }
        };
        img.onload = () => { img.classList.remove("hidden"); };
        /* LE NOM REPASSE PAR LA LISTE BLANCHE avant de devenir une URL : il
           vient du document, pas de nous (voir `fichierSujet`). */
        img.src = M.api.url("file/" + fichierSujet(suj))
          + "?t=" + (Number(suj.stamp) || 0);
        img.alt = "sujet détouré";
      } else {
        img.onerror = null;
        img.onload = null;
        img.removeAttribute("src");
        img.classList.add("hidden");
      }
    }
    const note = $("#cf-capture-ia-note");
    if (note) {
      const parts = [];
      if (IA_ERR) parts.push(IA_ERR);
      if (off.motif) parts.push(off.motif);
      if (off.on) {
        parts.push(off.gratuit
          ? "Le détourage tourne ICI : rien ne sort de la machine, rien n'est "
            + "facturé."
          : "L'image part chez fal.ai, qui facture directement. Le montant "
            + "affiché vient de la table de tarifs de l'application.");
      }
      if (suj) {
        parts.push("Couche « sujet » : " + suj.w + " × " + suj.h + " px, "
          + weight(suj.bytes)
          + (estNombre(suj.couverture)
            ? " — elle garde " + num(suj.couverture * 100, 1) + " % de l'image"
            : "")
          + (suj.voie ? " (voie " + String(suj.voie) + ")" : "")
          + ". La pièce Illustration peut l'adopter.");
      }
      note.textContent = parts.join(" ");
    }
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

    const div = divergence(s.echelle, CF.doc());
    const bandeau = $("#cf-capture-m-diverge");
    if (bandeau) {
      bandeau.classList.toggle("hidden", !div);
      if (div) {
        bandeau.textContent = "Le format du jeu a changé depuis cette mesure : "
          + div.avant + " → " + div.apres + ". Les millimètres ci-dessous "
          + "décrivent la carte d'avant — relancez « Remesurer ».";
      }
    }

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
      /* LES BORDS VUS, CHACUN AVEC LE SIEN. La ligne annonçait « les quatre
         bords » et alignait les valeurs TRIEES PAR TAILLE a cote d'une liste
         de noms triee par ALPHABET : trois valeurs sous une etiquette qui en
         promettait quatre, et l'appariement faux. Le backend rend maintenant
         un dictionnaire ; on l'ecrit tel quel. */
      isPlain(b.epaisseurs_mm) && Object.keys(b.epaisseurs_mm).length
        ? "les " + Object.keys(b.epaisseurs_mm).length + " bords vus : "
          + Object.keys(b.epaisseurs_mm).sort()
            .map((k) => k + " " + num(b.epaisseurs_mm[k], 2)).join(" · ") + " mm"
        : null,
      "régularité " + num(b.regularite, 2) + " · netteté " + num(b.nettete, 2),
    ] : ["aucune bordure mesurable sur cette carte"],
      b ? b.confidence : null, b ? "" : "vide");

    const bx = Array.isArray(s.boxes) ? s.boxes : [];
    /* LA BANDE EXCLUE SE DIT AVANT LES BOITES. Une boite `tronquee` bute sur
       la frontiere du masque : sa mesure est un MINIMUM, pas une taille, et
       celui qui l'adopte doit le lire avant d'en faire un slot. */
    bloc("#cf-capture-m-zones", "Zones occupées",
      (bx.length
        ? [bx.length + (bx.length > 1 ? " zones candidates" : " zone candidate")]
          .concat(bx.map((z, k) => isPlain(z)
            ? (k + 1) + " · " + num(z.w, 1) + " × " + num(z.h, 1) + " mm"
              + " en (" + num(z.x, 1) + " ; " + num(z.y, 1) + ") — densité "
              + num(z.densite, 2) + " · netteté " + num(z.nettete, 2)
              + (z.tronquee ? " — TRONQUÉE par la bande exclue" : "")
            : null))
        : ["aucune zone candidate"])
        .concat(estNombre(s.zones_bande_mm) && s.zones_bande_mm > 0
          ? ["bande exclue le long des bords : " + num(s.zones_bande_mm, 2)
             + " mm (bordure + portée du filtre)"] : []),
      null, bx.length ? "" : "vide");

    const g = isPlain(s.bg) ? s.bg : null;
    bloc("#cf-capture-m-fond", "Fond", lignesFond(g),
      g && !g.bg_failed ? g.confidence : null,
      g ? (g.bg_failed ? "ko" : "") : "vide");

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
    const bs = Array.isArray(s.boxes) ? s.boxes : [];
    const on = BOITES && SIDE === "recto" && !!info("recto") && analysee()
      && peutIncruster(s);
    hote.classList.toggle("hidden", !on);
    if (!on) return;
    const mm = s.echelle.carte_mm;
    const lw = mm[0];
    const lh = mm[1];
    bs.forEach((b, k) => {
      if (!isPlain(b)) return;
      const el = document.createElement("span");
      /* Une boite coupee par la bande exclue se VOIT : son trait est
         interrompu. Un rectangle plein dirait « voila la zone » d'un bord que
         personne n'a mesure. */
      el.className = "cf-capture-box" + (b.tronquee ? " tronquee" : "");
      el.style.left = (100 * (Number(b.x) || 0) / lw) + "%";
      el.style.top = (100 * (Number(b.y) || 0) / lh) + "%";
      el.style.width = (100 * (Number(b.w) || 0) / lw) + "%";
      el.style.height = (100 * (Number(b.h) || 0) / lh) + "%";
      el.title = "zone " + (k + 1) + " — " + num(b.w, 1) + " × " + num(b.h, 1)
        + " mm, densité " + num(b.densite, 2)
        + (b.tronquee ? " — tronquée par la bande exclue : cette taille est un "
          + "minimum" : "");
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
      border: null, boxes: [], zones_bande_mm: null,
      bg: null, palette: [], notes: [],
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
      zones_bande_mm: estNombre(r.zones_bande_mm) ? r.zones_bande_mm : null,
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
    const det = host.querySelector("#cf-capture-detour");
    const pub = host.querySelector("#cf-capture-publier");
    if (pub) pub.addEventListener("click", () => { publier(); });
    const ouvre = () => { if (file) { file.value = ""; file.click(); } };
    if (pick) pick.addEventListener("click", ouvre);
    if (rempl) rempl.addEventListener("click", ouvre);
    if (ana) ana.addEventListener("click", () => { analyser(); });
    if (det) det.addEventListener("click", () => { detourer(); });
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

  /* CE QU'ON MONTRE QUAND CA RATE, et il y a TROIS cas, pas deux. La premiere
     ecriture n'en traduisait qu'un : un `fetch` REJETE — backend eteint, cable
     debranche — ressortait tel quel, « Failed to fetch », en anglais et sans
     dire quoi faire. Le CORE a deja ecrit ce remede (core.js:1244, « backend
     injoignable ») ; on l'applique ici plutot que de le redecouvrir. */
  function panne(e, quoi) {
    if (e && e.missing) return "backend absent : " + quoi + " exige /api/cards";
    const m = String((e && e.message) || e);
    /* `fetch` rejette avec un TypeError et un message que le navigateur
       choisit (« Failed to fetch », « NetworkError… », « Load failed ») : on
       reconnait le TYPE, pas la phrase — elle change d'un navigateur a l'autre. */
    if (e instanceof TypeError) {
      return "backend injoignable (" + m + ") — " + quoi
        + " a besoin du service local";
    }
    return m;
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

  /* ═══════════════════════════════════════════════════════════════════════
     5. LE DETOURAGE IA (spec §7.1.3, plan D5)

     OPT-IN de bout en bout : la disponibilite est lue AVANT le clic, le prix
     est affiche AVANT le clic, et rien ne part sans le clic. La regle du
     basculement (local d'abord, fal ensuite, rien sinon) vit COTE BACKEND —
     un ecran qui la recopierait derivierait de lui au premier changement.
     ═══════════════════════════════════════════════════════════════════════ */

  /* CE QUE CE POSTE SAIT FAIRE. Un echec ici n'est pas une panne du panneau :
     l'import et l'analyse continuent de fonctionner, seule l'option
     disparait, et le motif se lit dans la note. */
  async function chargeOptions() {
    try {
      IA = await lireJson(await M.api.raw("GET", "ai-options"));
      IA_ERR = "";
    } catch (e) {
      IA = null;
      IA_ERR = panne(e, "les options de détourage");
    }
    paint();
  }

  /* LE MEME VERROU BUSY QUE L'IMPORT ET L'ANALYSE, et pour la meme raison :
     detourer pendant qu'un fichier monte detourerait l'image d'avant — sauf
     qu'ici, ca peut couter un appel payant pour un resultat perime.

     C'EST LA PIECE QUI PUBLIE (D3) : la route range le PNG et repond ; le
     `M.patch` ci-dessous ecrit `layers.sujet` par la voie d'autosave unique.
     `layers` est FUSIONNE et non remplace — T5 rangera d'autres couches a
     cote, et les ecraser a chaque detourage serait un defaut muet. */
  async function detourer() {
    if (BUSY) { M.toast("un traitement est déjà en cours"); return; }
    let off = offreIA(IA, !!info("recto"));
    if (!off.on) { M.toast(off.motif || "détourage indisponible", true); return; }
    /* LE PRIX AFFICHE PEUT NE PLUS ETRE LE PRIX RENDU. Les options sont lues
       au montage ; la table de tarifs, elle, se modifie dans les Reglages a
       tout moment (mesure : table multipliee par 83, bouton inchange jusqu'a
       reouverture du panneau). Relire est GRATUIT et LOCAL — `/ai-options` ne
       parle a personne — alors on relit juste avant de payer. Si le chiffre a
       bouge, LE GESTE NE PART PAS : le bouton se re-libelle et l'utilisateur
       re-consent d'un clic. Consentir a un montant et en payer un autre est
       le genre de chose qui ne se rattrape pas apres coup. */
    const avant = off;
    await chargeOptions();
    off = offreIA(IA, !!info("recto"));
    if (!off.on) { M.toast(off.motif || "détourage indisponible", true); return; }
    if (off.libelle !== avant.libelle) {
      M.toast("le tarif a changé depuis l'affichage : « " + avant.libelle
        + " » → « " + off.libelle + " ». Rien n'a été envoyé — relancez si "
        + "vous êtes d'accord.", true);
      return;
    }
    BUSY = true;
    try {
      M.busy(true, off.gratuit ? "détourage local…" : "détourage par fal.ai…");
      const d = await lireJson(await M.api.raw("POST", "rembg"));
      const maj = {};
      const anc = isPlain(st().layers) ? st().layers : {};
      Object.keys(anc).forEach((k) => { maj[k] = anc[k]; });
      maj.sujet = {
        /* TROISIEME COPIE AVOUEE du nom de la couche (capture.py:SUJET_NAME
           et mod-face.js portent les deux autres) : c'est un REPLI, pour le
           cas ou la route repondrait sans `layer`. La regle 8 recopie plutot
           que de partager, et exige que la copie se dise. */
        file: String(d.layer || "sujet_recto.png"),
        w: d.w, h: d.h, bytes: d.bytes, stamp: d.stamp,
        voie: String(d.voie || ""),
        couverture: estNombre(d.couverture) ? d.couverture : null,
      };
      M.patch({ layers: maj });
      paint();
      /* LA DEPENSE SE DIT APRES, AVEC LE MEME TARIF QU'AVANT LE CLIC (patron
         du decor IA de P2). Deux chiffres differents de part et d'autre d'un
         clic, c'est la confiance perdue. Et une voie gratuite ne parle pas
         d'argent du tout. */
      M.toast("sujet isolé — " + d.w + " × " + d.h + " px, " + weight(d.bytes)
        + (d.voie === "local" ? " (local, gratuit)"
          : (estNombre(d.prix_usd) ? " (fal, ~" + num(d.prix_usd, 3) + " $)"
            : " (fal)")));
    } catch (e) {
      M.toast(panne(e, "le détourage"), true);
    } finally {
      BUSY = false;
      M.busy(false);
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     6. « PUBLIER VERS LA 3D » (spec §7.1.6, dette R5 de T5)

     T5 avait ecrit la route et l'a AVOUE sans appelant : « le chemin §7.1.6
     est vrai par l'API, pas encore par un clic ». Le voici, ce clic.

     CE QUE CE GESTE N'ECRIT PAS : le document. La route range des fichiers
     dans le dossier de P9 et rend son bordereau ; il n'y a rien a patcher
     dans `doc.capture` — le manifeste EST le contrat, et P9 le relit (avec
     les empreintes qui le datent, ronde T5). Un `M.patch` ici ferait une
     seconde verite a maintenir.

     LE MEME VERROU BUSY QUE LES TROIS AUTRES GESTES : publier pendant qu'un
     fichier monte publierait l'image d'avant, et le manifeste porterait le
     sha d'une source qui n'existe deja plus.

     ET LA CARTE COURANTE SUIT (`CF.current()`) : le manifeste nomme ses
     fichiers d'apres l'index de carte (`c01`, `c02`…). Publier toujours la
     premiere ecrirait chez la voisine pendant qu'on regarde la troisieme. */
  async function publier() {
    if (BUSY) { M.toast("un traitement est déjà en cours"); return; }
    const off = offrePublier(st());
    if (!off.on) { M.toast(off.motif || "rien à publier", true); return; }
    BUSY = true;
    try {
      M.busy(true, "publication des couches vers la Forge 3D…");
      const n = Number(CF.current());
      const carte = isFinite(n) && n >= 0 ? n : 0;
      const d = await lireJson(await M.api.raw(
        "POST", "manifeste?card=" + encodeURIComponent(carte)));
      paint();
      M.toast(bordereau(d));
    } catch (e) {
      M.toast(panne(e, "la publication vers la 3D"), true);
    } finally {
      BUSY = false;
      M.busy(false);
    }
  }

})();
