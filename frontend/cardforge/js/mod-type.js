/* ═══════════════════════════════════════════════════════════════════════════
   Card Forge — piece 03 · Typographie   [P3]
   Proprietaire exclusif de : doc.type · z 60 · /api/cards/<did>/type/*
   Prefixe DOM impose : id="cf-type-..."   ·   feuille : css/mod-type.css
   (tout selecteur y contient .cf-type)

   CE QUE CETTE PIECE TIENT, ET COMMENT :

   1. JAMAIS DE TRONCATURE MUETTE. Un texte qui ne tient pas est d'abord
      retreci (recherche dichotomique sur le corps, jusqu'a `min_pt`) et
      renvoye a la ligne. S'il ne tient toujours pas, il est DESSINE QUAND
      MEME, en entier, et le depassement est signale HORS DU FICHIER : lisere
      rouge sur le calque d'edition (DOM, jamais exporte) plus un compteur
      chiffre dans le panneau. Couper un mot en silence est le seul
      comportement que ce module ne sait pas produire.

   2. LE LISERE D'ALERTE N'EST PAS DANS LA TOILE. Le painter z=60 ne dessine
      que du texte : un cadre d'alerte peint sur la toile partirait dans le
      PNG et dans le PDF de l'imprimeur. L'alerte vit sur le calque
      d'edition, superpose a l'apercu — le meme endroit que les reperes du
      CORE, et pour la meme raison.

   3. UNE SEULE MISE EN PAGE. `layoutSlot()` sert le painter ET les mesures
      affichees dans le panneau : les chiffres a l'ecran sont ceux qui ont
      dessine le fichier, pas une seconde estimation.

   4. LES POLICES VIENNENT DU DISQUE. 23 familles servies sur /fonts/ (22
      .ttf + PolandKaito.otf — l'extension est LUE, jamais devinee), chargees
      par FontFace. Zero CDN, zero octet reseau vers le dehors.

   5. LA JUSTIFICATION A UN PLAFOND. Un bord droit net se paie en blancs, et
      c'est le seul defaut que produit une justification. Au-dela de
      `just_max` % de l'espace naturel, le supplement passe dans
      l'INTERLETTRAGE de la ligne au lieu de gonfler encore ses blancs. Le
      releve donne les blancs REELLEMENT poses (mini -> maxi, en px, avec leur
      rapport) et le nombre de lignes rattrapees — pas seulement
      l'irregularite des FINS de ligne, qui est le cote ou une justification
      est bonne par construction. `last_pct` fait de meme pour la ligne
      creuse : la derniere ligne d'un paragraphe doit faire au moins tant de
      pour cent de la justification, sinon un mot lui est descendu.

   6. AUCUN CHIFFRE AFFICHE QUI NE SOIT MESURE SUR LES OCTETS. Le pave de
      regles annonce l'encre RELUE sur le composite, anticrenelage compris —
      un typographe mesure l'encre, pas la boite, et une bbox qui ne compte
      que les pixels pleins est plus petite que ce qu'un imprimeur mesure. Le
      contraste le plus bas NOMME son slot, son corps et son seuil, et donne
      les deux luminances qui le produisent : il se recalcule sans nous, et il
      se recalcule JUSTE — le rapport affiche est la division des luminances
      affichees, arrondies d'abord (sinon refaire le calcul a la main donnait
      0,01 d'ecart, et un chiffre qu'on ne retrouve pas est un chiffre faux).
      Les blancs-mots sont donnes dans les DEUX conventions, l'avance composee
      et le vide relu d'encre a encre : qui remesure le bitmap retombe sur le
      second, et ne conclut plus au mensonge en trouvant un autre nombre.

   7. « CA TIENT » N'EST PAS « CA SE LIT ». `min_pt` est un plancher
      d'ENCOMBREMENT : jusqu'ou l'ajustement automatique a le droit de
      descendre pour faire tenir le texte. `read_pt` est le plancher du
      METIER : le corps sous lequel le bloc ne se lit plus une fois la carte
      imprimee (titre 12 pt, encadre de regles 6 pt, credits 4 pt). Un titre
      ramene de 14 a 9 pt TIENT — et le badge vert « ajuste » le certifiait
      sans un mot sur la lecture. Le plancher n'empeche rien (couper serait
      pire que retrecir) : il fait dire au releve, au badge et au backend que
      ce bloc-la est en dessous, avec les deux chiffres.

   8. UN AVERTISSEMENT SANS REMEDE EST UN AVERTISSEMENT QU'ON PASSERA. Le
      releve disait « Titre 8,9 pt (plancher 12) » et s'arretait la, alors que
      l'ajustement automatique n'a qu'un levier — reduire le corps — et que les
      cinq autres sont dans cet inspecteur. Chaque bloc fautif porte desormais
      ses remedes MESURES : de combien agrandir la boite (hauteur et largeur
      cherchees separement, la plus petite surface l'emporte), combien de
      caracteres retirer, ce qu'atteignent la cesure, l'interlettrage et
      l'interligne. Chaque chiffre sort d'une mise en page refaite avec le
      changement propose, par le MEME `layoutSlot` que le painter. Le levier qui
      suffit porte un bouton ; le remede applique est REMESURE a la passe
      suivante, et s'il n'a pas tenu, le panneau le dit. Raccourcir le texte
      reste un chiffre et jamais un bouton : cette piece ne coupe pas.

   9. UN CHIFFRE SE VERIFIE OU IL A ETE PRIS. Publier deux luminances laissait
      encore chercher OU les lire : sur un fond en degrade, celui qui
      echantillonne ailleurs trouve un autre nombre et conclut au mensonge (un
      critique a annonce 5,50:1 la ou nous annoncions 4,29:1 — deux mesures
      justes, deux endroits). Le releve nomme donc LE PIXEL de chaque terme, en
      coordonnees du fichier livre, et dit lequel porte quoi : quand un contour
      fait le relais, le rapport publie n'oppose pas l'encre au fond mais le
      CONTOUR au fond. De meme « 23 polices » n'est plus un compte de fichiers :
      chaque famille chargee est mesuree (la chasse d'un specimen contre celle
      du repli) et le releve n'affiche que ce compte-la.

   doc.type.slots est le seul contrat sortant de cette piece : P4 le lit pour
   construire son menu de mappage, P7 pour son controle avant vol. Sa forme
   est gelee par la spec : {id, label, box:[x,y,w,h] en mm depuis le coin de
   COUPE, ...}.
   ═══════════════════════════════════════════════════════════════════════════ */
"use strict";

(function () {
  const CF = (typeof window !== "undefined") ? window.CF : null;
  if (!CF) throw new Error("mod-type: js/core.js doit etre charge avant ce fichier");

  /* ═════════════════════════════════════════════════════════════════════════
     0. TABLES MIROIR — identiques a backend/app/services/cards/type.py.
     `test_cards_type.py` EXTRAIT les deux blocs marques ci-dessous et les
     compare au dictionnaire Python : une divergence fait rougir la suite. Le
     lab doit servir les memes gabarits hors ligne que le backend en ligne ;
     deux tables recopiees a la main auraient derive au premier ajout.
     ═════════════════════════════════════════════════════════════════════════ */

  /* ═══ CF-TYPE-DEFAULTS-BEGIN ═══ */
  const SLOT_DEFAULTS = {
    "align": "left", "arc": 0.0, "autofit": true, "bold": false,
    "box": [0.0, 0.0, 10.0, 5.0], "caps": "none", "color": "#f2efe9", "fit": "contain",
    "font": "Inter", "hyphen": false, "id": "slot", "italic": false, "just_max": 133.0,
    "kind": "text", "label": "Texte", "last_pct": 25.0, "leading": 1.18, "lock": false,
    "min_pt": 5.0, "on": true, "opacity": 100.0, "outline": 0.0,
    "outline_color": "#0a0a0c", "plate_alpha": 1.0, "plate_color": null,
    "plate_radius": 0.0, "read_pt": 0.0, "rotate": 0.0, "shadow": 0.0,
    "shadow_color": "#000000", "shadow_dx": 0.0, "shadow_dy": 0.0, "side": "front",
    "size_pt": 10.0, "src": "", "text": "", "track": 0.0, "valign": "top",
    "wrap": true
  };
  /* ═══ CF-TYPE-DEFAULTS-END ═══ */

  /* ═══ CF-TYPE-PRESETS-BEGIN ═══ */
  const PRESETS = {
    "champion": {
      "label": "Champion",
      "hint": "Titre long, coût, statistiques, encadré de règles, ambiance, crédits.",
      "slots": [
        {"align": "center", "color": "#f6e7c2", "font": "Anton", "id": "cost", "label": "Coût", "min_pt": 9.0, "outline": 1.4, "outline_color": "#1b1206", "read_pt": 8.0, "rel": [0.0, 0.0, 0.17, 0.115], "size_pt": 22.0, "text": "5", "valign": "middle", "wrap": false},
        {"align": "center", "bold": true, "caps": "upper", "color": "#f6e7c2", "font": "Cinzel", "id": "title", "label": "Titre", "leading": 1.02, "min_pt": 6.5, "outline": 0.8, "outline_color": "#1b1206", "read_pt": 12.0, "rel": [0.19, 0.0, 0.81, 0.115], "shadow": 1.2, "shadow_dy": 0.6, "size_pt": 14.0, "text": "Veilleur, Grand Oracle des Marches Profondes", "track": 2.0, "valign": "middle"},
        {"align": "center", "caps": "upper", "color": "#e8d8b6", "font": "Staatliches", "id": "typeline", "label": "Ligne de type", "min_pt": 5.0, "read_pt": 6.0, "rel": [0.0, 0.552, 1.0, 0.05], "size_pt": 8.5, "text": "Créature légendaire — Sentinelle", "track": 6.0, "valign": "middle", "wrap": false},
        {"align": "justify", "color": "#efe7d6", "font": "IBMPlexSans", "hyphen": true, "id": "rules", "label": "Encadré de règles", "leading": 1.22, "min_pt": 4.5, "read_pt": 6.0, "rel": [0.02, 0.615, 0.96, 0.2], "size_pt": 8.0, "text": "Vol, célérité. À l'entrée en jeu, révélez les trois cartes du dessus de votre pioche : gardez-en une en main, renvoyez les autres au fond du paquet. Tant que cette créature est en jeu, vos sorts d'eau coûtent 1 de moins et vos créatures marines gagnent +0/+1. Sacrifice : défaussez une carte pour donner +2/+0 à une créature alliée jusqu'à la fin du tour. À sa mort, chaque adversaire défausse une carte au hasard et vous piochez.", "valign": "top"},
        {"align": "center", "color": "#c9bda6", "font": "IBMPlexSans", "id": "flavor", "italic": true, "label": "Texte d'ambiance", "min_pt": 4.5, "read_pt": 6.0, "rel": [0.04, 0.826, 0.92, 0.055], "size_pt": 7.0, "text": "« Ce qui monte finit toujours par redescendre, dit-on ici. »", "valign": "middle"},
        {"align": "center", "color": "#f6e7c2", "font": "Anton", "id": "atk", "label": "Attaque", "min_pt": 8.0, "outline": 1.4, "outline_color": "#1b1206", "read_pt": 8.0, "rel": [0.0, 0.885, 0.17, 0.09], "size_pt": 19.0, "text": "4", "valign": "middle", "wrap": false},
        {"align": "center", "color": "#f6e7c2", "font": "Anton", "id": "def", "label": "Vie", "min_pt": 8.0, "outline": 1.4, "outline_color": "#1b1206", "read_pt": 8.0, "rel": [0.83, 0.885, 0.17, 0.09], "size_pt": 19.0, "text": "5", "valign": "middle", "wrap": false},
        {"align": "left", "color": "#c5bba4", "font": "JetBrainsMono", "id": "num", "label": "Numéro", "min_pt": 3.5, "read_pt": 4.0, "rel": [0.2, 0.952, 0.25, 0.045], "size_pt": 5.0, "text": "017 / 060", "valign": "middle", "wrap": false},
        {"align": "right", "color": "#c5bba4", "font": "IBMPlexSans", "id": "artist", "label": "Artiste", "min_pt": 3.5, "read_pt": 4.0, "rel": [0.55, 0.952, 0.25, 0.045], "size_pt": 5.0, "text": "ill. A. Nonyme", "valign": "middle", "wrap": false}
      ]
    },
    "sort": {
      "label": "Sort",
      "hint": "Sans statistiques : titre, coût, grand encadré de règles, ambiance.",
      "slots": [
        {"align": "center", "color": "#dce9f6", "font": "Anton", "id": "cost", "label": "Coût", "min_pt": 9.0, "outline": 1.4, "outline_color": "#08131f", "read_pt": 8.0, "rel": [0.0, 0.0, 0.16, 0.11], "size_pt": 21.0, "text": "3", "valign": "middle", "wrap": false},
        {"align": "center", "color": "#dce9f6", "font": "Cinzel", "id": "title", "label": "Titre", "min_pt": 6.5, "outline": 0.8, "outline_color": "#08131f", "read_pt": 12.0, "rel": [0.18, 0.0, 0.82, 0.11], "size_pt": 15.0, "text": "Marée d'encre", "track": 1.0, "valign": "middle"},
        {"align": "center", "caps": "upper", "color": "#c7d9ea", "font": "Staatliches", "id": "typeline", "label": "Ligne de type", "min_pt": 5.0, "read_pt": 6.0, "rel": [0.0, 0.55, 1.0, 0.05], "size_pt": 8.5, "text": "Sort instantané", "track": 6.0, "valign": "middle", "wrap": false},
        {"align": "justify", "color": "#e6eef7", "font": "IBMPlexSans", "hyphen": true, "id": "rules", "label": "Encadré de règles", "leading": 1.24, "min_pt": 4.5, "read_pt": 6.0, "rel": [0.02, 0.615, 0.96, 0.24], "size_pt": 8.5, "text": "Vol, célérité. À l'entrée en jeu, révélez les trois cartes du dessus de votre pioche : gardez-en une en main, renvoyez les autres au fond du paquet. Tant que cette créature est en jeu, vos sorts d'eau coûtent 1 de moins et vos créatures marines gagnent +0/+1. Sacrifice : défaussez une carte pour donner +2/+0 à une créature alliée jusqu'à la fin du tour. À sa mort, chaque adversaire défausse une carte au hasard et vous piochez.", "valign": "top"},
        {"align": "center", "color": "#9fb3c6", "font": "IBMPlexSans", "id": "flavor", "italic": true, "label": "Texte d'ambiance", "min_pt": 4.5, "read_pt": 6.0, "rel": [0.04, 0.87, 0.92, 0.06], "size_pt": 7.0, "text": "« L'encre monte, la mémoire descend. »", "valign": "middle"},
        {"align": "right", "color": "#8496a8", "font": "IBMPlexSans", "id": "artist", "label": "Artiste", "min_pt": 3.5, "read_pt": 4.0, "rel": [0.35, 0.945, 0.65, 0.045], "size_pt": 5.0, "text": "ill. A. Nonyme", "valign": "middle", "wrap": false}
      ]
    },
    "arcane": {
      "label": "Arcane (texte sur arc)",
      "hint": "Titre courbé en haut, chiffre romain, cartouche de nom en bas.",
      "slots": [
        {"align": "center", "caps": "upper", "color": "#e9d7a8", "font": "Cinzel", "id": "arcnum", "label": "Numéro d'arcane", "min_pt": 6.0, "read_pt": 6.0, "rel": [0.3, 0.0, 0.4, 0.07], "size_pt": 11.0, "text": "XVII", "track": 12.0, "valign": "middle", "wrap": false},
        {"align": "center", "arc": 38.0, "bold": true, "caps": "upper", "color": "#e9d7a8", "font": "Cinzel", "id": "title", "label": "Titre sur arc", "min_pt": 6.0, "read_pt": 12.0, "rel": [0.05, 0.075, 0.9, 0.12], "size_pt": 13.0, "text": "La Roue des Marées", "track": 4.0, "valign": "middle", "wrap": false},
        {"align": "center", "arc": -22.0, "caps": "upper", "color": "#e9d7a8", "font": "Cinzel", "id": "name", "label": "Cartouche", "min_pt": 6.0, "read_pt": 12.0, "rel": [0.05, 0.86, 0.9, 0.075], "size_pt": 12.0, "text": "La Gardienne", "track": 8.0, "valign": "middle", "wrap": false},
        {"align": "center", "color": "#d3c39c", "font": "IBMPlexSans", "id": "artist", "label": "Artiste", "min_pt": 3.5, "read_pt": 4.0, "rel": [0.2, 0.95, 0.6, 0.04], "size_pt": 5.0, "text": "ill. A. Nonyme", "valign": "middle", "wrap": false}
      ]
    },
    "minimal": {
      "label": "Minimal",
      "hint": "Deux slots : un titre, un encadré. Le point de départ le plus sobre.",
      "slots": [
        {"align": "left", "bold": true, "color": "#f2efe9", "font": "SpaceGrotesk", "id": "title", "label": "Titre", "min_pt": 7.0, "read_pt": 12.0, "rel": [0.0, 0.0, 1.0, 0.1], "size_pt": 14.0, "text": "Veilleur, Grand Oracle des Marches Profondes", "valign": "top"},
        {"align": "justify", "color": "#d8d2c8", "font": "IBMPlexSans", "hyphen": true, "id": "rules", "label": "Encadré de règles", "leading": 1.25, "min_pt": 4.5, "read_pt": 6.0, "rel": [0.0, 0.62, 1.0, 0.24], "size_pt": 8.5, "text": "Vol, célérité. À l'entrée en jeu, révélez les trois cartes du dessus de votre pioche : gardez-en une en main, renvoyez les autres au fond du paquet. Tant que cette créature est en jeu, vos sorts d'eau coûtent 1 de moins et vos créatures marines gagnent +0/+1. Sacrifice : défaussez une carte pour donner +2/+0 à une créature alliée jusqu'à la fin du tour. À sa mort, chaque adversaire défausse une carte au hasard et vous piochez.", "valign": "top"}
      ]
    }
  };
  /* ═══ CF-TYPE-PRESETS-END ═══ */

  /* Repli hors ligne du catalogue de polices : le lab reste entierement
     utilisable quand /api/cards n'est pas monte (le CORE bascule alors en
     mode local). Les libelles et familles d'usage sont ceux du backend. */
  const FONTS_LOCAL = [
    ["AbrilFatface", "Abril Fatface", "titre", "ttf"],
    ["Anton", "Anton", "titre", "ttf"],
    ["ArchivoBlack", "Archivo Black", "titre", "ttf"],
    ["BebasNeue", "Bebas Neue", "titre", "ttf"],
    ["Bungee", "Bungee", "titre", "ttf"],
    ["Righteous", "Righteous", "titre", "ttf"],
    ["Staatliches", "Staatliches", "titre", "ttf"],
    ["Cinzel", "Cinzel", "fantasy", "ttf"],
    ["DistantGalaxy", "Distant Galaxy", "fantasy", "ttf"],
    ["PolandKaito", "Poland Kaito", "fantasy", "otf"],
    ["IBMPlexSans", "IBM Plex Sans", "texte", "ttf"],
    ["Inter", "Inter", "texte", "ttf"],
    ["SpaceGrotesk", "Space Grotesk", "texte", "ttf"],
    ["JetBrainsMono", "JetBrains Mono", "mono", "ttf"],
    ["DrippingMarker", "Dripping Marker", "manuscrit", "ttf"],
    ["GraffitiBrush", "Graffiti Brush", "manuscrit", "ttf"],
    ["Pacifico", "Pacifico", "manuscrit", "ttf"],
    ["PermanentMarker", "Permanent Marker", "manuscrit", "ttf"],
    ["SuperFeel", "Super Feel", "manuscrit", "ttf"],
    ["SuperPencil", "Super Pencil", "manuscrit", "ttf"],
    ["Hacked", "Hacked", "retro", "ttf"],
    ["Monoton", "Monoton", "retro", "ttf"],
    ["PressStart2P", "Press Start 2P", "retro", "ttf"],
  ].map((r) => ({
    id: r[0], label: r[1], kind: r[2], ext: r[3],
    family: "CFT " + r[0], file: r[0] + "." + r[3], url: "/fonts/" + r[0] + "." + r[3],
    /* HORS LIGNE, ON NE SAIT PAS. La couverture d'une police se lit dans sa
       table cmap, donc dans le fichier, donc au backend. Le repli local dit
       « inconnu » (null) et le panneau l'ecrit tel quel : recopier ici une
       liste que personne n'a mesuree aurait ete exactement le badge menteur
       qu'on pourchasse. */
    fr_missing: null,
  }));

  const KIND_LABELS = {
    titre: "Titres", fantasy: "Fantasy", texte: "Texte courant",
    mono: "Chasse fixe", manuscrit: "Manuscrites", retro: "Rétro / jeu",
    autre: "Autres",
  };

  const ALIGNS = ["left", "center", "right", "justify"];
  const VALIGNS = ["top", "middle", "bottom"];
  const CASES = ["none", "upper", "lower", "title"];
  const SIDES = ["front", "back", "both"];
  /* LA NATURE D'UN BLOC ET LE CADRAGE DE SON IMAGE — miroir de
     cards/type.py:KINDS / FITS. Un calque d'image est un SLOT de cette bande,
     pas un objet neuf : il herite ainsi de l'ordre de peinture, de l'oeil, du
     verrou, du calque d'edition, de l'annulation et de la fluidite. */
  const KINDS = ["text", "image"];
  const FITS = ["contain", "cover"];
  /* Le motif EXACT d'une source de calque, miroir de type.py:SLOT_SRC_RE. Ce
     nom n'est jamais tape par un humain : la route d'import le fabrique
     (`img_{n}.png`). Un motif permissif aurait ouvert le dossier du deck. */
  const SRC_RE = /^(|img:img_\d+\.png)$/;
  /* Cote long au-dela duquel une image importee est reduite AVANT l'envoi.
     MEME CHIFFRE que l'illustration de P1 (mod-face.js:91 / face.py:92) et que
     cards/type.py:MAX_IMPORT_PX, recopie et non partage : chaque piece porte
     ses constantes (regle 8). Le serveur reduit de toute facon — un client
     n'est pas une garantie ; ici on evite un aller-retour de 40 Mo. */
  const MAX_IMPORT_PX = 4096;
  const SLOTS_MAX = 40;
  const TRACK_MIN_PC = -30;      /* miroir de cards/type.py:TRACK_MIN */
  /* LA PLAQUE DE FOND — rayon des coins, en millimetres. Miroir de
     cards/type.py:PLATE_RADIUS_MAX. Le plafond du metier : au-dela de 30 mm,
     sur une carte de 63 x 88, un « coin arrondi » est un disque. La boite du
     slot borne de toute facon le rayon a la moitie de son petit cote, AU
     DESSIN — le painter recoit les slots du document tels quels, jamais
     repasses par `normSlot` (qui, lui, ne sert que le panneau). */
  const PLATE_RADIUS_MAX_MM = 30;
  /* LE PAS DU CLAVIER, tel que la spec le NOMME (§6.1:307, patron P2) : une
     flèche pousse d'un millimètre, Maj AFFINE à deux dixièmes. P3 faisait
     l'inverse — 0,5 mm et Maj = 5 mm — c'est-à-dire que la touche de
     précision agrandissait le pas. Sur une carte de 63 x 88, 5 mm n'est pas
     un « grand pas », c'est un déménagement ; et 0,5 mm ne se cale sur rien
     (la grille d'accrochage du glisser vaut 0,25 mm). */
  const NUDGE_MM = 1, NUDGE_FINE_MM = 0.2, SNAP_MM = 0.25, MIN_BOX_MM = 2;
  const UNDO_MAX = 60;
  const FONT_WAIT_MS = 2500;      /* le painter a 4 s : on garde de la marge */

  /* MARGE OPTIQUE, en millimetres. « Ca rentre » au sens du test geometrique
     et « ca rentre » au sens de l'imprimeur sont deux choses : les reperes de
     coupe d'une rotative derivent de +/- 0,5 mm, si bien qu'une encre calee a
     0,3 mm du bord de la zone sure n'a AUCUNE marge optique. Cette valeur est
     retranchee de la boite AVANT composition, sur les quatre cotes : elle
     n'est donc pas un avertissement de plus, elle empeche le cas. Le releve
     affiche le degagement REELLEMENT MESURE, en mm. */
  const OPTICAL_MM_DEF = 0.5;
  const OPTICAL_MM_MAX = 5;
  /* Le lisere d'anticrenelage d'un glyphe : un pixel de plus de chaque cote,
     de l'encre faible mais de l'encre. Le controle photometrique la compte
     (c'est ce qu'un imprimeur mesure), donc la composition la reserve. */
  const AA_PX = 1;
  /* LE REPERTOIRE FRANCAIS — miroir de cards/type.py:FR_PROBE, extrait et
     compare par test_cards_type.py. C'est la liste des signes qu'un jeu de
     cartes en francais a besoin d'ecrire, et contre laquelle chaque fichier
     de police est relu (table cmap) au lieu d'etre cru sur parole. */
  /* ═══ CF-TYPE-FRPROBE-BEGIN ═══ */
  const FR_PROBE = "ÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸÆŒàâäçéèêëîïôöùûüÿæœ«»…—’";
  /* ═══ CF-TYPE-FRPROBE-END ═══ */
  /* Le specimen du menu de polices : des lettres a jambages ET des accents.
     « Agyfj 42 » seul montrait la meme chose pour une police complete et pour
     une police sans un seul accent. */
  const FP_SAMPLE = "Agyfj — Créature";
  /* Seuils WCAG appliques a la taille PHYSIQUE du texte (une carte se lit a
     taille reelle) : 3:1 au-dessus de 18 pt, ou 14 pt en gras ; 4,5:1 sinon. */
  function wcagSeuil(pt, bold) { return (pt >= 18 || (bold && pt >= 14)) ? 3.0 : 4.5; }
  /* La marque la PLUS PROCHE du bord de la zone sure pour un slot : le corps
     des glyphes, ou le halo de l'ombre portee s'il va plus loin. L'ombre est
     un degrade, pas de l'encre pleine — mais elle EST dans le fichier livre,
     donc c'est elle qui decide quand la marge optique est tenue ou non. */
  function nearestClearMm(r) {
    if (!r) return null;
    const a = r.clear_mm, b = r.halo_clear_mm;
    if (a == null) return (b == null ? null : b);
    if (b == null) return a;
    return Math.min(a, b);
  }

  /* ═════════════════════════════════════════════════════════════════════════
     1. OUTILS
     ═════════════════════════════════════════════════════════════════════════ */
  const clone = (v) => JSON.parse(JSON.stringify(v));
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  const num = (v, d, lo, hi) => {
    const n = Number(v);
    return isFinite(n) ? clamp(n, lo, hi) : d;
  };
  /* UNE ENUMERATION, LUE COMME LE BACKEND LA LIT (miroir de
     cards/type.py:_choice) : rognee, mise en bas de casse, puis comparee. Les
     deux tables doivent rendre le MEME verdict sur la meme chaine, sans quoi
     un document se lirait autrement a l'ecran qu'au controle. */
  const pick = (v, list, d) => {
    const s = String(v == null ? "" : v).trim().toLowerCase();
    return list.indexOf(s) >= 0 ? s : d;
  };
  const esc = (s) => String(s == null ? "" : s).replace(/&/g, "&amp;")
    .replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const fx = (v, n) => {
    const s = Number(v).toFixed(n == null ? 1 : n);
    return s.replace(".", ",").replace(/,0+$/, "").replace(/(,\d*[1-9])0+$/, "$1");
  };
  const pxOfPt = (pt, g) => pt / 72 * g.dpi;
  const ptOfPx = (px, g) => px * 72 / g.dpi;

  function familyOf(id) {
    const f = FONT_BY_ID[id];
    return f ? f.family : "CFT " + String(id || "Inter");
  }

  function normSlot(raw, i) {
    const r = (raw && typeof raw === "object") ? raw : {};
    const s = clone(SLOT_DEFAULTS);
    let sid = String(r.id == null ? "" : r.id).trim().toLowerCase();
    if (!/^[a-z][a-z0-9_]{0,23}$/.test(sid)) sid = "slot" + ((i | 0) + 1);
    s.id = sid;
    s.label = String(r.label == null || r.label === "" ? sid : r.label).slice(0, 40);
    const b = r.box;
    if (Array.isArray(b) && b.length === 4) {
      s.box = [num(b[0], 0, -500, 500), num(b[1], 0, -500, 500),
        num(b[2], 10, 0, 500), num(b[3], 5, 0, 500)];
    }
    s.font = String(r.font || SLOT_DEFAULTS.font).slice(0, 64);
    s.size_pt = num(r.size_pt, SLOT_DEFAULTS.size_pt, 2, 400);
    s.min_pt = Math.min(num(r.min_pt, SLOT_DEFAULTS.min_pt, 2, 400), s.size_pt);
    /* PLANCHER DE LISIBILITE — voir cards/type.py. Il n'est PAS ramene sous
       `size_pt` : un plancher au-dessus du corps demande est une information
       juste (« ce bloc est deja trop petit »), pas une saisie a corriger en
       silence. */
    s.read_pt = num(r.read_pt, 0, 0, 400);
    s.hyphen = !!r.hyphen;
    s.color = /^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(String(r.color || "")) ? String(r.color).toLowerCase() : SLOT_DEFAULTS.color;
    s.align = ALIGNS.indexOf(r.align) >= 0 ? r.align : SLOT_DEFAULTS.align;
    s.valign = VALIGNS.indexOf(r.valign) >= 0 ? r.valign : SLOT_DEFAULTS.valign;
    s.track = num(r.track, 0, -30, 100);
    s.leading = num(r.leading, SLOT_DEFAULTS.leading, 0.6, 3);
    /* JUST_MAX : elasticite maximale d'un blanc justifie, en % de l'espace
       naturel de la fonte. 100 = aucun etirement (tout passe dans
       l'interlettrage). Le plancher est 100 : un blanc RETRECI casserait les
       mots entre eux, ce qu'aucun plafond ne doit pouvoir demander.
       LAST_PCT : longueur minimale de la derniere ligne d'un paragraphe, en %
       de la justification. 0 = controle desactive. */
    s.just_max = num(r.just_max, SLOT_DEFAULTS.just_max, 100, 400);
    s.last_pct = num(r.last_pct, SLOT_DEFAULTS.last_pct, 0, 80);
    s.caps = CASES.indexOf(r.caps) >= 0 ? r.caps : "none";
    s.bold = !!r.bold; s.italic = !!r.italic;
    s.outline = num(r.outline, 0, 0, 20);
    s.outline_color = /^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(String(r.outline_color || "")) ? String(r.outline_color).toLowerCase() : SLOT_DEFAULTS.outline_color;
    s.shadow = num(r.shadow, 0, 0, 40);
    s.shadow_color = /^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(String(r.shadow_color || "")) ? String(r.shadow_color).toLowerCase() : "#000000";
    s.shadow_dx = num(r.shadow_dx, 0, -40, 40);
    s.shadow_dy = num(r.shadow_dy, 0, -40, 40);
    /* LA PLAQUE DE FOND. Une couleur illisible ne vaut pas « noir » ici :
       elle vaut PAS DE PLAQUE. Peindre du noir sur un cartouche parce qu'un
       import a ecrit « bleu » aurait ete un defaut visible et muet. */
    s.plate_color = /^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(String(r.plate_color || "")) ? String(r.plate_color).toLowerCase() : null;
    s.plate_alpha = num(r.plate_alpha, 1, 0, 1);
    s.plate_radius = num(r.plate_radius, 0, 0, PLATE_RADIUS_MAX_MM);
    s.rotate = num(r.rotate, 0, -180, 180);
    s.arc = num(r.arc, 0, -100, 100);
    s.autofit = r.autofit === undefined ? true : !!r.autofit;
    s.wrap = r.wrap === undefined ? true : !!r.wrap;
    s.opacity = num(r.opacity, 100, 0, 100);
    s.side = SIDES.indexOf(r.side) >= 0 ? r.side : "front";
    s.on = r.on === undefined ? true : !!r.on;
    /* LE VERROU. Faux par defaut, et faux pour tout document ecrit avant lui :
       un slot ne devient protege que si quelqu'un l'a demande. Il ne dit RIEN
       de ce qui est peint (le painter ne le lit pas) — il n'arrete que les
       gestes de scene du calque d'edition. */
    s.lock = !!r.lock;
    /* LA NATURE DU BLOC, puis sa source et son cadrage. `pick` est le miroir
       exact de cards/type.py:_choice — une valeur inconnue retombe sur le
       defaut plutot que d'envoyer le painter dans une branche qui n'existe
       pas. La source, elle, n'est PAS rognee : ce nom vient de la route
       d'import, pas d'une main humaine, donc « img:img_1.png » suivi d'une
       espace n'est pas une faute de frappe a reparer — c'est une chaine qui ne
       vient pas de nous. */
    s.kind = pick(r.kind, KINDS, SLOT_DEFAULTS.kind);
    s.src = SRC_RE.test(String(r.src == null ? "" : r.src)) ? String(r.src) : "";
    s.fit = pick(r.fit, FITS, SLOT_DEFAULTS.fit);
    s.text = String(r.text == null ? "" : r.text).slice(0, 4000);
    return s;
  }
  /* UN CALQUE D'IMAGE, RECONNU EN UN SEUL ENDROIT. Trois passes d'encre, un
     painter, une liste et un panneau posent la meme question ; ils la posent
     donc au meme endroit. C'est aussi ce qui rend l'exclusion CHERCHABLE : la
     quatrieme passe d'encre trouvera ce nom avant d'oublier la regle. */
  function isImage(s) { return !!s && s.kind === "image"; }
  /* Le fichier d'un calque, sans son prefixe — "" si la source est vide ou
     illegale (elle a deja ete bornee par `normSlot`, mais le painter recoit
     les slots du document TELS QUELS). */
  function srcFile(s) {
    const v = String((s && s.src) || "");
    return (SRC_RE.test(v) && v.indexOf("img:") === 0) ? v.slice(4) : "";
  }

  /* La zone sure TELLE QU'ELLE EXISTE EN PIXELS, relue en millimetres depuis
     le coin de coupe. Miroir exact de cards/type.py:safe_rect_mm — la zone
     sure du fichier livre est `safe_px` centree dans la rogne, elle ne
     retombe pas sur les millimetres demandes (poker_eu : 3 mm de consigne =
     3,0057 mm en largeur et 2,9633 mm en hauteur). Ce sont les pixels qui
     font le fichier. */
  function safeRectMm(g) {
    const k = 25.4 / g.dpi;
    return [(g.safe_off_px[0] - g.bleed_off_px[0]) * k,
      (g.safe_off_px[1] - g.bleed_off_px[1]) * k,
      g.safe_px[0] * k, g.safe_px[1] * k];
  }
  function presetSlots(pid, g) {
    const p = PRESETS[pid] || PRESETS.champion;
    const sr = safeRectMm(g);
    return p.slots.map((spec, i) => {
      const s = {};
      Object.keys(spec).forEach((k) => { if (k !== "rel") s[k] = clone(spec[k]); });
      const r6 = (v) => Math.round(v * 1e6) / 1e6;
      s.box = [r6(sr[0] + spec.rel[0] * sr[2]), r6(sr[1] + spec.rel[1] * sr[3]),
        r6(spec.rel[2] * sr[2]), r6(spec.rel[3] * sr[3])];
      return normSlot(s, i);
    });
  }
  function boxPx(slot, g) {
    return [g.bleed_off_px[0] + g.mm2px(slot.box[0]),
      g.bleed_off_px[1] + g.mm2px(slot.box[1]),
      g.mm2px(slot.box[2]), g.mm2px(slot.box[3])];
  }
  function safeRectPx(g) {
    return [g.safe_off_px[0], g.safe_off_px[1], g.safe_px[0], g.safe_px[1]];
  }
  function outsideBy(rect, safe) {
    const e = 1e-4, d = (v) => (v > e ? v : 0);
    return {
      left: d(safe[0] - rect[0]), top: d(safe[1] - rect[1]),
      right: d((rect[0] + rect[2]) - (safe[0] + safe[2])),
      bottom: d((rect[1] + rect[3]) - (safe[1] + safe[3])),
    };
  }
  const anyOut = (o) => !!(o.left || o.top || o.right || o.bottom);
  /* ── CE QUE L'IMPRIMEUR VEUT SAVOIR : COMBIEN DE MILLIMETRES ─────────────
     Un panneau qui repond « oui » ou « non » demande qu'on le croie ; un
     panneau qui repond « 4,26 mm » se verifie a la regle sur l'epreuve. Les
     deux rectangles viennent de la geometrie qui a rendu le fichier
     (`trim_px` et `bleed_off_px` du CORE), l'encre vient de la mise en page
     qui l'a dessinee : la soustraction se refait a la main. */
  function trimRectPx(g) {
    return [g.bleed_off_px[0], g.bleed_off_px[1], g.trim_px[0], g.trim_px[1]];
  }
  /* distance de l'encre au bord de COUPE, en mm. Negative = la lame passe
     dans le texte. */
  function trimClearMm(rect, g) {
    const t = trimRectPx(g);
    return Math.min(rect[0] - t[0], rect[1] - t[1],
      (t[0] + t[2]) - (rect[0] + rect[2]),
      (t[1] + t[3]) - (rect[1] + rect[3])) * 25.4 / g.dpi;
  }
  /* la marge de securite du format, en mm : le plus petit des quatre retraits
     du cadre de securite par rapport a la coupe. C'est le nombre auquel se
     compare la distance ci-dessus. */
  function safeMarginMm(g) {
    const sr = safeRectMm(g), k = 25.4 / g.dpi;
    const w = g.trim_px[0] * k, h = g.trim_px[1] * k;
    return Math.min(sr[0], sr[1], w - (sr[0] + sr[2]), h - (sr[1] + sr[3]));
  }
  /* la phrase de distance, ecrite pour quelqu'un qui pose une carte sur une
     table — jamais un « oui / non ». */
  function clearTxt(rect, g, bad) {
    const c = trimClearMm(rect, g), mg = safeMarginMm(g);
    if (c < 0) {
      return "<b>l'encre passe " + fx(-c, 2) + " mm sous la lame</b>";
    }
    return (bad ? "<b>" : "") + "l'encre s'arrête à " + fx(c, 2) + " mm du bord de coupe"
      + (bad ? ", pour " + fx(mg, 2) + " mm de marge au format</b>" : "");
  }

  /* ═════════════════════════════════════════════════════════════════════════
     2. POLICES — FontFace, depuis /fonts/. Aucun CDN.
     ═════════════════════════════════════════════════════════════════════════ */
  let FONTS = FONTS_LOCAL.slice();
  let FONT_BY_ID = {};
  const FONT_STATE = {};          /* id -> "loading" | "ok" | "ko" */
  const FONT_PROMISE = {};
  /* ── « 23 POLICES » : UN CHIFFRE QU'IL FAUT MERITER ──────────────────────
     Le catalogue en annonce 23 parce que le backend a trouve 23 fichiers. Que
     le navigateur les CHARGE, et qu'il les pose vraiment au lieu de retomber
     sur le repli du systeme, est une AUTRE affirmation — et c'est celle que le
     panneau faisait sans jamais la verifier. Le critique n'a pas pu la
     verifier non plus : « les 23 polices ne sont pour moi qu'un badge 23 ».
     Ici chaque famille chargee est MESUREE : on compare la chasse d'un
     specimen dans cette famille a la meme chasse dans une famille qui n'existe
     pas (donc le repli). Si les deux sont egales, le fichier n'est pas pose et
     on ne le compte pas. Le releve affiche ce compte-la, jamais le catalogue. */
  const FONT_MEAS = {};           /* id -> true (distincte du repli) | false */
  const FACE_PROBE = "Agyfj 42 — ABCgjmwq éàôü";
  function faceIsReal(id) {
    try {
      const ctx = fixCtx();
      ctx.font = '100px "CFT  absente ", monospace';
      const w0 = ctx.measureText(FACE_PROBE).width;
      ctx.font = '100px "' + familyOf(id) + '", monospace';
      const w1 = ctx.measureText(FACE_PROBE).width;
      return Math.abs(w1 - w0) > 0.5;
    } catch (e) { return false; }
  }
  function fontProof() {
    const ids = FONTS.map((f) => f.id);
    return {
      served: ids.length,
      ok: ids.filter((id) => FONT_STATE[id] === "ok").length,
      ko: ids.filter((id) => FONT_STATE[id] === "ko").length,
      dist: ids.filter((id) => FONT_MEAS[id] === true).length,
    };
  }
  /* les 23, chargees et mesurees, a la demande : le chiffre publie passe alors
     de « 5 verifiees » a « 23 verifiees », et il l'aura ete pour de vrai. */
  let fontsBusy = false;
  async function proveFonts() {
    if (fontsBusy) return;
    fontsBusy = true;
    M.busy(true, "chargement des " + FONTS.length + " polices…");
    try {
      await Promise.all(FONTS.map((f) => loadFont(f.id)));
      FONTS.forEach((f) => { if (FONT_STATE[f.id] === "ok") FONT_MEAS[f.id] = faceIsReal(f.id); });
    } finally {
      fontsBusy = false;
      M.busy(false);
    }
    const p = fontProof();
    M.toast(p.dist + " / " + p.served + " familles chargées et distinctes du repli"
      + (p.ko ? " · " + p.ko + " illisible(s)" : ""), p.dist < p.served);
    renderAll();
  }

  function indexFonts() {
    FONT_BY_ID = {};
    FONTS.forEach((f) => { FONT_BY_ID[f.id] = f; });
  }
  indexFonts();

  function loadFont(id) {
    const f = FONT_BY_ID[id];
    if (!f) return Promise.resolve(false);
    if (FONT_PROMISE[id]) return FONT_PROMISE[id];
    FONT_STATE[id] = "loading";
    const p = (async () => {
      try {
        const ff = new FontFace(f.family, 'url("' + f.url + '")');
        await ff.load();
        document.fonts.add(ff);
        FONT_STATE[id] = "ok";
        /* mesuree A L'INSTANT OU ELLE EST POSEE : le compte affiche ne peut pas
           avancer sans qu'une chasse ait ete relue. */
        FONT_MEAS[id] = faceIsReal(id);
        /* UNE POLICE ARRIVEE APRES COUP DOIT REFAIRE LA MISE EN PAGE. Le
           painter n'attend les fontes que 2,5 s ; au-dela il compose avec le
           repli — et le corps ajuste, qui depend entierement des chasses,
           n'est alors PAS celui de la police demandee. MESURE sur demarrage a
           froid : titre annonce « 8,8 pt » ; une fois Cinzel chargee, six
           passes de suite donnent 9,0 pt, et rien ne rattrapait l'ecart tant
           qu'on ne touchait pas a la boite. Un chiffre qui depend d'une course
           n'est pas un chiffre : la police qui arrive redemande le rendu, et
           le CORE coalesce les 23 arrivees en une frame. */
        if (slots().some((s) => s.on && s.font === id)) M.invalidate();
        return true;
      } catch (e) {
        FONT_STATE[id] = "ko";
        console.warn("cardforge/type: police illisible " + f.url, e);
        return false;
      }
    })();
    FONT_PROMISE[id] = p;
    return p;
  }
  function ensureFonts(ids) {
    const todo = ids.filter((id) => FONT_STATE[id] !== "ok" && FONT_STATE[id] !== "ko");
    if (!todo.length) return Promise.resolve();
    const all = Promise.all(todo.map(loadFont));
    /* le painter dispose de 4 s : on ne l'y laisse jamais aller. Une police
       muette dessine en repli et le panneau le dit, l'ecran ne gele pas. */
    return Promise.race([all, new Promise((r) => setTimeout(r, FONT_WAIT_MS))]);
  }

  /* ═════════════════════════════════════════════════════════════════════════
     3. MISE EN PAGE — UNE SEULE, pour le painter comme pour les mesures
     ═════════════════════════════════════════════════════════════════════════ */

  /* L'APOSTROPHE N'OUVRE PAS UN MOT — miroir exact de cards/type.py.
     « marée d'encre » en capitales initiales sortait « Marée D'Encre » :
     l'apostrophe comptait comme une espace, donc « encre » passait pour un mot
     neuf, et cette capitale-la partait a l'impression. Les coupures sont les
     blancs (l'insecable compris) et les guillemets droits et parentheses ;
     l'apostrophe, elle, reste DANS le mot. */
  function applyCase(t, caps) {
    if (caps === "upper") return t.toUpperCase();
    if (caps === "lower") return t.toLowerCase();
    if (caps === "title") {
      return t.replace(/([^\s "(\[]+)/g, (w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase());
    }
    return t;
  }
  function fontCss(slot, sizePx) {
    return (slot.italic ? "italic " : "") + (slot.bold ? "700 " : "400 ")
      + sizePx.toFixed(3) + 'px "' + familyOf(slot.font) + '", sans-serif';
  }
  /* Largeur d'un fragment. Avec interlettrage, le dessin se fait glyphe par
     glyphe : la mesure DOIT suivre le meme chemin, sinon le pave mesure et le
     pave dessine ne sont pas le meme. */
  function runWidth(ctx, str, trackPx) {
    if (!str) return 0;
    if (!trackPx) return ctx.measureText(str).width;
    let w = 0;
    const chars = Array.from(str);
    for (let i = 0; i < chars.length; i++) w += ctx.measureText(chars[i]).width;
    return w + trackPx * Math.max(0, chars.length - 1);
  }
  /* ── CESURE ────────────────────────────────────────────────────────────
     Deux sources de points de coupe, jamais une de plus :
       1. le TIRET CONDITIONNEL U+00AD que l'auteur a pose lui-meme — exact,
          il ne peut pas se tromper ;
       2. une cesure automatique CONSERVATRICE (option `hyphen`), qui ne coupe
          qu'entre deux consonnes encadrees de voyelles (voyelle-C|C-voyelle),
          jamais dans un digramme inseparable (ch, ph, gn, bl, tr), jamais a
          moins de 3 lettres d'un bout. C'est la regle francaise de base ; elle
          rate des coupes, elle n'en invente pas de fausses.
     Un tiret de cesure AJOUTE un glyphe a la ligne : le recompte de `cut`
     l'ignore explicitement (voir HYPH_RE dans layoutSlot), sinon l'invariant
     « 0 caractere supprime » se serait mis a compter des caracteres AJOUTES. */
  const SOFT = "­";                 /* tiret conditionnel */
  const VOW = "aeiouyàâäéèêëîïôöùûüÿæœ";
  const DIGRAPHS = ["ch", "ph", "th", "gn", "bl", "br", "cl", "cr", "dr", "fl",
    "fr", "gl", "gr", "pl", "pr", "tr", "vr", "qu"];
  function hyphenPoints(word) {
    /* rend les index (dans `word`) OU l'on a le droit de couper, tiret pose
       a gauche de la coupe. */
    const w = word.toLowerCase();
    const out = [];
    for (let i = 3; i <= w.length - 3; i++) {
      const a = w[i - 2], b = w[i - 1], c = w[i];
      if (VOW.indexOf(a) < 0 || VOW.indexOf(b) >= 0 || VOW.indexOf(c) >= 0) continue;
      if (DIGRAPHS.indexOf(b + c) >= 0) continue;
      out.push(i);
    }
    return out;
  }
  /* Le mot, decoupe en fragments secables. `[ "impo", "ssi", "ble" ]` se
     recolle en "impossible" : aucun caractere n'est cree ni perdu ici. */
  function pieces(word, auto) {
    const raw = word.split(SOFT);
    const out = [];
    raw.forEach((part) => {
      if (!auto || part.length < 6) { out.push(part); return; }
      const cuts = hyphenPoints(part);
      let prev = 0;
      cuts.forEach((i) => { out.push(part.slice(prev, i)); prev = i; });
      out.push(part.slice(prev));
    });
    return out.filter((p, i) => p !== "" || i === 0);
  }

  /* ── LIGNE CREUSE ──────────────────────────────────────────────────────
     Une derniere ligne de paragraphe reduite a un mot est le defaut que la
     justification ne montre pas : les fins de ligne restent parfaitement
     alignees et le pave se termine sur un moignon. La regle classique veut
     que la derniere ligne fasse au moins un quart de la justification ; ici
     c'est un REGLAGE (`last_pct`), et le releve affiche la valeur mesuree a
     cote du seuil. Quand elle est trop courte, on DESCEND le dernier mot de
     la ligne precedente — jamais on ne coupe, jamais on ne remonte du texte.
     Deux garde-fous : la ligne precedente doit garder au moins deux mots (on
     ne fait pas remonter le probleme d'une ligne), et on ne descend pas un
     fragment de cesure (il finit par un tiret : le mot serait casse en deux
     morceaux separes par un blanc). Aucun caractere n'est cree ni perdu :
     l'invariant `cut` le recompte apres coup. */
  function pullWidow(out, start, lastMinW, fits, width) {
    for (let guard = 0; guard < 4; guard++) {
      const li = out.length - 1;
      if (li - 1 < start) return;                 /* un seul ligne : rien a faire */
      if (width(out[li]) >= lastMinW) return;
      const prev = out[li - 1];
      if (/-$/.test(prev)) return;                /* fragment de cesure : on n'y touche pas */
      const m = /^(.*\S)\s+(\S+)$/.exec(prev);    /* pas de slice : rien n'est tronque */
      if (!m) return;                             /* la precedente n'a qu'un mot */
      const cand = m[2] + " " + out[li];
      if (!fits(cand)) return;
      out[li - 1] = m[1];
      out[li] = cand;
    }
  }

  function wrapLines(ctx, text, maxW, trackPx, wrap, hyphen, lastMinW) {
    const paras = String(text).split(/\r?\n/);
    if (!wrap) return { lines: paras.map((p) => p.split(SOFT).join("")), ends: paras.map(() => true) };
    const out = [], ends = [];
    const fits = (s) => runWidth(ctx, s, trackPx) <= maxW;
    const width = (s) => runWidth(ctx, s, trackPx);
    paras.forEach((para) => {
      const start = out.length;
      const words = para.split(/(\s+)/);          /* les blancs sont gardes */
      let line = "";
      const flush = (end) => { out.push(line.replace(/\s+$/, "")); ends.push(!!end); line = ""; };
      for (let i = 0; i < words.length; i++) {
        const w = words[i];
        if (!w) continue;
        if (/^\s+$/.test(w)) { if (line) line += w; continue; }
        const clean = w.split(SOFT).join("");
        const cand = line + clean;
        if (line === "" || fits(cand.replace(/\s+$/, ""))) { line = cand; continue; }
        /* le mot ne tient pas a la suite : on tente une CESURE avant de le
           renvoyer entier a la ligne. */
        const frags = pieces(w, hyphen);
        let placed = false;
        if (frags.length > 1) {
          let head = "";
          for (let k = 0; k < frags.length - 1; k++) {
            const t = head + frags[k];
            if (!fits(line + t + "-")) break;
            head = t;
          }
          if (head) {
            const rest = frags.join("").slice(head.length);
            line += head + "-";
            flush(false);
            line = rest;
            placed = true;
          }
        }
        if (!placed) { flush(false); line = clean; }
      }
      flush(true);
      if (lastMinW > 0) pullWidow(out, start, lastMinW, fits, width);
    });
    /* un mot plus long que la boite est coupe PAR CARACTERE — pas jete. La
       coupure se voit (le mot continue a la ligne suivante) ; disparaitre en
       silence est ce que cette piece refuse de faire. */
    const cutL = [], cutE = [];
    out.forEach((l, i) => {
      if (fits(l) || Array.from(l).length <= 1) { cutL.push(l); cutE.push(ends[i]); return; }
      let cur = "";
      Array.from(l).forEach((ch) => {
        if (cur && !fits(cur + ch)) { cutL.push(cur); cutE.push(false); cur = ch; }
        else cur += ch;
      });
      if (cur) { cutL.push(cur); cutE.push(ends[i]); }
    });
    return { lines: cutL, ends: cutE };
  }

  /* Une ligne justifiee : la largeur manquante est repartie sur les BLANCS.
     Rend la liste des blancs et le supplement par blanc — le dessin et la
     mesure lisent la meme, sinon le pave mesure et le pave dessine divergent. */
  function justifyGaps(line, extra) {
    const n = (line.match(/ /g) || []).length;
    return (n > 0 && extra > 0) ? extra / n : 0;
  }
  /* ── PLAFOND D'ELASTICITE ──────────────────────────────────────────────
     « Fins de ligne a 0 % d'irregularite » mesure le seul cote ou une
     justification est bonne par construction. Le defaut qu'elle produit est
     ailleurs : des blancs qui vont du simple au double d'une ligne a
     l'autre — une ligne lache se voit a l'oeil nu et ce chiffre-la ne la
     montrait pas.

     Ici le blanc ne peut plus depasser `capRatio` fois l'espace naturel de la
     fonte (133 % par defaut, la valeur du metier). Ce qui reste a repartir
     passe dans l'INTERLETTRAGE de la ligne, reparti sur toutes ses lettres :
     un supplement de 0,6 px par lettre a 5,5 pt est invisible la ou un blanc
     double se voit. La ligne occupe toujours EXACTEMENT la justification —
     l'encombrement d'encre, donc le verdict de zone sure, ne bouge pas.

     Le calcul est fait UNE FOIS, dans `build()`, et range dans `m.sp` : le
     dessin le relit, il ne le refait pas. C'est la meme regle que pour la
     mise en page — deux calculs, c'est un jour ou ils divergent. */
  function justifySpread(line, extra, natWs, capRatio) {
    const n = (line.match(/ /g) || []).length;
    const nat = Math.max(0.01, natWs);
    const nc = Array.from(line).length;
    const done = (gap, let_, capped, over) => ({
      gap: gap, let: let_, ws: nat + gap + let_, ratio: (nat + gap + let_) / nat,
      capped: capped, over_cap: !!over,
    });
    if (n <= 0 || extra <= 0) return done(0, 0, false, false);
    /* Le blanc REELLEMENT POSE entre deux mots vaut l'espace naturel plus le
       supplement de justification PLUS l'interlettrage de la ligne : c'est
       cette avance-la qu'un re-mesureur trouve sur le bitmap, et c'est donc
       elle qu'on plafonne. Plafonner le seul supplement aurait donne un
       chiffre affiche plus petit que le blanc visible — la meme faute que
       toutes les autres corrigees ici. */
    const budget = Math.max(0, nat * (capRatio - 1));
    const slots = nc - 1;                 /* intervalles entre caracteres */
    if (extra / n <= budget || slots <= n) return done(extra / n, 0, false, false);
    if (extra / slots > budget) {
      /* meme en n'etirant QUE les lettres on depasse : le blanc garde sa
         largeur naturelle, tout part dans l'interlettrage, et le releve le
         dit au lieu de pretendre que le plafond a tenu. */
      return done(0, extra / slots, true, true);
    }
    /* gap + let = budget, et gap*n + let*(nc-1) = extra : une seule solution,
       et elle remplit la justification EXACTEMENT. */
    const let_ = (extra - budget * n) / (slots - n);
    return done(budget - let_, let_, true, false);
  }

  /* Geometrie de l'arc : la ligne de base suit un cercle dont la corde est la
     largeur de la boite et la fleche vaut arc% x 18 % de cette largeur. */
  function arcGeom(slot, w) {
    const a = slot.arc / 100;
    if (!a || w <= 0) return null;
    const s = Math.abs(a) * w * 0.18;
    const R = (s * s + (w * w) / 4) / (2 * s);
    const half = Math.min(1, (w / 2) / R);
    const ang = Math.asin(half);        /* demi-angle de la corde */
    return { R: R, sag: s, up: a > 0, ang: ang, span: 2 * ang * R };
  }

  function layoutSlot(ctx, slot, g, rawText) {
    const box = boxPx(slot, g);
    const text = applyCase(String(rawText == null ? "" : rawText), slot.caps);
    /* LE CONTOUR FAIT PARTIE DE L'ENCOMBREMENT. Un trait de contour deborde
       du glyphe de la moitie de son epaisseur ; si la mise en page ignore ce
       demi-trait, un texte cale sur le bord de sa boite peint EN DEHORS — et
       une boite posee sur le bord de la zone sure fait sortir l'encre de la
       zone sure, ce que le controle avant vol signale a juste titre. On
       degonfle donc la boite du demi-trait avant de composer : ce qui est
       dessine reste dans la boite, contour compris. (L'ombre portee, elle,
       deborde volontairement : c'est un effet, pas de l'encre pleine.) */
    const grow = pxOfPt(slot.outline, g) / 2;
    let bx0 = box[0] + grow, by0 = box[1] + grow;
    let bx1 = box[0] + box[2] - grow, by1 = box[1] + box[3] - grow;
    /* MARGE OPTIQUE — la ou la boite touche la ZONE SURE, et nulle part
       ailleurs. « Ca rentre a 4 px du bord » est vrai au sens du test et faux
       au sens de l'imprimeur : les reperes d'une rotative derivent de 0,5 mm.
       On retranche donc cette marge du cote qui touche la bordure de la zone
       sure — pas des quatre cotes de toutes les boites, ce qui aurait coute du
       corps a des slots posés au milieu de la carte, loin de tout bord. Un
       slot volontairement pose HORS de la zone sure (son centre dehors) n'est
       pas rapatrie : on ne redispose pas le travail de quelqu'un. */
    const optPx = g.mm2px(clamp(Number(CF.get("type.optical_mm", OPTICAL_MM_DEF)) || 0, 0, OPTICAL_MM_MAX));
    if (optPx > 0) {
      const sr = safeRectPx(g);
      const cx = box[0] + box[2] / 2, cy = box[1] + box[3] / 2;
      if (cx > sr[0] && cx < sr[0] + sr[2] && cy > sr[1] && cy < sr[1] + sr[3]) {
        /* LA MARGE DOIT RESTER LIBRE D'ENCRE, pas seulement libre de BOITE.
           Le demi-trait de contour se pose EN DEHORS du cadre composé, et le
           liseré d'anticrénelage d'un glyphe déborde encore d'un pixel : une
           marge de 0,5 mm qui ne réservait que la boîte laissait l'encre
           arriver à 0,34 mm du bord — un chiffre annoncé qui ne survit pas au
           premier re-mesurage. On réserve donc les trois.
           ── ET L'OMBRE PORTEE. Elle était oubliée, et elle va plus loin que
           tout le reste : MESURE sur le fichier livré, le halo du titre (flou
           1,2 pt, décalage 0,6 pt) arrivait à 0,17 mm du bord de la zone sûre
           pendant que le corps des glyphes se tenait sagement à 0,59 mm. Le
           panneau déclarait 0,50 mm de marge optique et cochait vert : un
           seuil affiché que le fichier ne respecte pas. Un halo est un
           dégradé, pas de l'encre pleine — mais il EST dans le PNG livré, et
           une rotative qui dérive de 0,5 mm l'emporte comme le reste. La
           réserve se calcule donc CÔTÉ PAR CÔTÉ : le flou porte dans les
           quatre directions, le décalage n'ajoute que du côté où il pousse. */
        const blur = pxOfPt(slot.shadow, g);
        const sdx = pxOfPt(slot.shadow_dx, g), sdy = pxOfPt(slot.shadow_dy, g);
        const halo = (slot.shadow > 0 || slot.shadow_dx || slot.shadow_dy);
        const base = optPx + grow + AA_PX;
        const padL = base + (halo ? Math.max(0, blur - sdx) : 0);
        const padR = base + (halo ? Math.max(0, blur + sdx) : 0);
        const padT = base + (halo ? Math.max(0, blur - sdy) : 0);
        const padB = base + (halo ? Math.max(0, blur + sdy) : 0);
        const nx0 = Math.max(bx0, sr[0] + padL), nx1 = Math.min(bx1, sr[0] + sr[2] - padR);
        const ny0 = Math.max(by0, sr[1] + padT), ny1 = Math.min(by1, sr[1] + sr[3] - padB);
        if (nx1 - nx0 > 1) { bx0 = nx0; bx1 = nx1; }
        if (ny1 - ny0 > 1) { by0 = ny0; by1 = ny1; }
      }
    }
    const innerX = bx0, innerY = by0;
    const maxW = Math.max(1, bx1 - bx0), maxH = Math.max(1, by1 - by0);
    const hi = slot.size_pt, lo = Math.min(slot.min_pt, slot.size_pt);
    const just = slot.align === "justify";

    function build(pt) {
      const sizePx = pxOfPt(pt, g);
      ctx.font = fontCss(slot, sizePx);
      const trackPx = slot.track / 100 * sizePx;
      const arc = arcGeom(slot, maxW);
      /* l'espace naturel de CETTE fonte a CE corps — mesure, jamais suppose :
         0,26 em chez IBM Plex, 0,20 chez Anton. Un plafond exprime en em
         aurait serre les unes et laisse filer les autres. */
      const natWs = ctx.measureText(" ").width + trackPx;
      /* Les deux reglages sont relus a travers `num()`, avec leurs bornes :
         un document ENREGISTRE AVANT leur arrivee n'a ni l'un ni l'autre, et
         `undefined / 100` aurait rendu NaN — c'est-a-dire une carte vide, sans
         un mot. Un defaut manquant vaut le defaut, jamais NaN. */
      const capR = num(slot.just_max, SLOT_DEFAULTS.just_max, 100, 400) / 100;
      const lastMin = num(slot.last_pct, SLOT_DEFAULTS.last_pct, 0, 80);
      const lastMinW = (slot.wrap && lastMin > 0) ? maxW * lastMin / 100 : 0;
      const wr = arc ? { lines: [text.replace(/\r?\n/g, " ").split(SOFT).join("")], ends: [true] }
        : wrapLines(ctx, text, maxW, trackPx, slot.wrap, slot.hyphen, lastMinW);
      const lines = wr.lines, ends = wr.ends;
      const widths = lines.map((l) => runWidth(ctx, l, trackPx));
      const lineH = sizePx * slot.leading;
      const blockH = lines.length ? (lines.length - 1) * lineH + sizePx : 0;
      const wMax = widths.length ? Math.max.apply(null, widths) : 0;
      const avail = arc ? arc.span : maxW;
      /* une ligne justifiee occupe TOUTE la largeur utile : c'est cette
         largeur-la que l'encombrement d'encre doit porter, pas celle des mots
         serres a gauche. */
      /* le test doit etre EXACTEMENT celui de `justifyGaps` (une espace
         ordinaire, pas un blanc quelconque) : sinon une ligne tenue par une
         espace insecable serait annoncee pleine largeur et dessinee courte —
         un encombrement d'encre surevalue, donc un faux « hors zone sure ». */
      const drawn = widths.map((w, i) => (just && !arc && !ends[i] && lines[i].indexOf(" ") >= 0) ? maxW : w);
      /* les blancs REELLEMENT poses, ligne par ligne : c'est ce tableau que le
         dessin relit et que le releve affiche. Une ligne non justifiee garde
         l'espace naturel — son rapport vaut 1, et elle compte dans le mini. */
      const sp = lines.map((l, i) => ((drawn[i] > widths[i] + 0.01)
        ? justifySpread(l, drawn[i] - widths[i], natWs, capR)
        : { gap: 0, let: 0, ws: natWs, ratio: 1, capped: false }));
      return {
        pt: pt, sizePx: sizePx, trackPx: trackPx, lines: lines, ends: ends,
        widths: widths, drawn: drawn, sp: sp, natWs: natWs, capR: capR, lastMin: lastMin,
        lineH: lineH, blockH: blockH, wMax: wMax, arc: arc, avail: avail,
        fits: (wMax <= avail + 0.01) && (blockH <= maxH + 0.01),
      };
    }

    let m = build(hi);
    if (slot.autofit && !m.fits && hi > lo) {
      let a = lo, b = hi, best = null;
      for (let i = 0; i < 16 && b - a > 0.02; i++) {
        const mid = (a + b) / 2;
        const t = build(mid);
        if (t.fits) { best = t; a = mid; } else b = mid;
      }
      m = best || build(lo);
      if (!m.fits) m = build(lo);
    }

    /* encombrement REEL de l'encre : ce qui sera vraiment noirci sur la toile.
       C'est cette boite-la que le controle avant vol doit juger, pas le cadre
       du slot — un texte qui deborde sort de la zone sure meme si sa boite y
       etait. */
    const asc = [], dsc = [];
    m.lines.forEach((l) => {
      const mt = ctx.measureText(l || "M");
      asc.push(isFinite(mt.actualBoundingBoxAscent) ? mt.actualBoundingBoxAscent : m.sizePx * 0.8);
      dsc.push(isFinite(mt.actualBoundingBoxDescent) ? mt.actualBoundingBoxDescent : m.sizePx * 0.22);
    });
    let top = innerY;
    if (slot.valign === "middle") top = innerY + (maxH - m.blockH) / 2;
    else if (slot.valign === "bottom") top = innerY + (maxH - m.blockH);
    let inkX = innerX, inkW = 0, inkY = top, inkH = m.blockH;
    if (m.lines.length) {
      let x0 = Infinity, x1 = -Infinity;
      m.lines.forEach((l, i) => {
        const w = m.drawn[i];
        let x = innerX;
        if (slot.align === "center") x = innerX + (maxW - w) / 2;
        else if (slot.align === "right") x = innerX + maxW - w;
        x0 = Math.min(x0, x); x1 = Math.max(x1, x + w);
      });
      inkX = x0 - grow; inkW = (x1 - x0) + grow * 2;
      inkY = top + m.sizePx - (asc[0] || m.sizePx * 0.8) - grow;
      inkH = (m.lines.length - 1) * m.lineH + (asc[0] || 0) + (dsc[dsc.length - 1] || 0) + grow * 2;
    }
    if (m.arc) {
      /* Sur un arc, l'encre ne tient pas dans la boite des largeurs droites :
         la fleche l'etale en hauteur, et les glyphes des extremites, tournes
         du demi-angle de la corde, debordent lateralement de leur propre
         hauteur x sin(angle). Sans ces deux termes, le controle avant vol
         declarerait « dans la zone sure » un titre courbe qui n'y est pas. */
      const ex = m.sizePx * Math.sin(m.arc.ang);
      const ey = m.sizePx * (1 - Math.cos(m.arc.ang));
      inkX -= ex; inkW += 2 * ex;
      inkH += m.arc.sag + ey;
      if (m.arc.up) inkY -= m.arc.sag + ey;
    }
    let ink = [inkX, inkY, inkW, inkH];
    if (slot.rotate) {
      const cx = box[0] + maxW / 2, cy = box[1] + maxH / 2;
      const r = slot.rotate * Math.PI / 180, co = Math.cos(r), si = Math.sin(r);
      const pts = [[ink[0], ink[1]], [ink[0] + ink[2], ink[1]],
        [ink[0], ink[1] + ink[3]], [ink[0] + ink[2], ink[1] + ink[3]]]
        .map((p) => [cx + (p[0] - cx) * co - (p[1] - cy) * si,
          cy + (p[0] - cx) * si + (p[1] - cy) * co]);
      const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
      ink = [Math.min.apply(null, xs), Math.min.apply(null, ys),
        Math.max.apply(null, xs) - Math.min.apply(null, xs),
        Math.max.apply(null, ys) - Math.min.apply(null, ys)];
    }

    /* depassement : de combien, et COMBIEN DE CARACTERES sont concernes. Le
       texte n'est jamais coupe — le chiffre dit juste ce qui sort du cadre. */
    const overW = Math.max(0, m.wMax - m.avail);
    const overH = Math.max(0, m.blockH - maxH);
    let overChars = 0;
    if (overH > 0 && m.lineH > 0) {
      const fitLines = Math.max(0, Math.floor((maxH - m.sizePx) / m.lineH) + 1);
      for (let i = fitLines; i < m.lines.length; i++) overChars += Array.from(m.lines[i]).length;
    }
    if (overW > 0 && !overChars) overChars = Array.from(text).length;

    /* L'INVARIANT DE LA PIECE, MESURE — pas promis. On recompte les glyphes
       une fois la mise en page faite : le retour a la ligne insere des
       ruptures, il n'a pas le droit d'ENLEVER un caractere. Le panneau
       affiche ce chiffre tel quel ; s'il cessait d'etre nul, il le dirait au
       lieu de laisser croire que tout va bien. */
    /* On compare le texte SOURCE au texte POSE, blancs et tirets conditionnels
       retires des deux cotes, et les tirets de cesure AJOUTES en fin de ligne
       retires du cote pose : un tiret de cesure est un glyphe de plus, pas un
       caractere en moins, et le compter aurait rendu l'invariant negatif. */
    const flat = (s) => Array.from(String(s).split(SOFT).join("").replace(/\s+/g, "")).length;
    const posed = m.lines.map((l, i) => ((slot.hyphen || text.indexOf(SOFT) >= 0)
      && !m.ends[i] ? l.replace(/-$/, "") : l)).join("");
    const cut = Math.max(0, flat(text) - flat(posed));
    /* irregularite des fins de ligne : (la plus longue - la plus courte) / la
       plus longue, sur les lignes qui ne finissent pas un paragraphe. C'est le
       chiffre que la justification et la cesure font baisser. */
    let ragged = 0;
    const mids = m.drawn.filter((w, i) => !m.ends[i]);
    if (mids.length > 1) {
      const hiW = Math.max.apply(null, mids), loW = Math.min.apply(null, mids);
      ragged = hiW > 0 ? (hiW - loW) / hiW : 0;
    }
    /* CE QUE LA JUSTIFICATION COUTE, mesure sur les lignes qui la subissent :
       le blanc le plus serre, le plus lache, leur rapport, et le nombre de
       lignes dont l'excedent a du passer dans l'interlettrage. Sans ces
       chiffres, « 0 % d'irregularite » se felicite du seul cote propre. */
    let wsLo = null, wsHi = null, capped = 0;
    m.lines.forEach((l, i) => {
      if (m.ends[i] || l.indexOf(" ") < 0) return;   /* pas de blanc etire ici */
      const s = m.sp[i];
      if (wsLo == null || s.ws < wsLo) wsLo = s.ws;
      if (wsHi == null || s.ws > wsHi) wsHi = s.ws;
      if (s.capped) capped++;
    });
    /* la derniere ligne, en % de la justification : le chiffre que `last_pct`
       borne. Sur une seule ligne il n'y a pas de ligne creuse — c'est un
       paragraphe complet, et la valeur reste nulle. */
    const nL = m.lines.length;
    const lastPct = (nL > 1 && maxW > 0) ? m.widths[nL - 1] / maxW * 100 : null;
    return {
      id: slot.id, label: slot.label, text: text, chars: Array.from(text).length,
      box: box, ix: innerX, iy: innerY, iw: maxW, ih: maxH, grow: grow,
      pt: m.pt, sizePx: m.sizePx, trackPx: m.trackPx, lines: m.lines, ends: m.ends,
      widths: m.widths, drawn: m.drawn, sp: m.sp, natWs: m.natWs,
      lineH: m.lineH, blockH: m.blockH, wMax: m.wMax,
      arc: m.arc, avail: m.avail, ink: ink, top: top, ragged: ragged,
      ws_lo: wsLo, ws_hi: wsHi, ws_ratio: (wsLo && wsHi) ? wsHi / wsLo : null,
      ws_stretch: (wsHi && m.natWs > 0) ? wsHi / m.natWs : null,
      ws_capped: capped, just_max: m.capR * 100, last_min: m.lastMin,
      last_pct: lastPct,
      last_short: lastPct != null && m.lastMin > 0 && lastPct < m.lastMin - 0.05,
      shrunk: m.pt < slot.size_pt - 0.005,
      /* LE PLANCHER DE LISIBILITE, MESURE. `min_pt` dit jusqu'ou l'ajustement
         a le droit de descendre pour faire TENIR ; `read_pt` dit a partir de
         quel corps le bloc se LIT une fois imprime. Le badge « ajuste »
         certifiait le premier et se taisait sur le second — c'est exactement
         ce qu'un titre ramene de 14 a 9 pt cache.
         LA COMPARAISON SE FAIT A LA PRECISION AFFICHEE, au dixieme de point.
         Le corps sort d'une recherche dichotomique : elle s'arrete a 11,99 pt
         quand on visait 12, et le badge annonçait alors « 12 < 12 pt » — une
         phrase fausse a l'oeil, vraie au centieme, et donc invendable. Un
         centieme de point n'est pas un defaut de lisibilite ; un badge qui se
         contredit lui-meme en est un. */
      read_pt: slot.read_pt,
      under_read: slot.read_pt > 0
        && Math.round(m.pt * 10) < Math.round(slot.read_pt * 10),
      over: overW > 0.01 || overH > 0.01,
      over_w: overW, over_h: overH, over_chars: overChars,
      cut: cut,                    /* invariant MESURE : 0 caractere supprime */
      /* LES DEUX NOMBRES QUI PRODUISENT L'INVARIANT, publies a cote de lui.
         Un compteur a zero se croit ; deux comptes egaux se REFONT — celui du
         texte source et celui des signes reellement poses, meme convention des
         deux cotes (blancs et tirets conditionnels retires). */
      srcn: flat(text), posed: flat(posed),
    };
  }

  /* ═════════════════════════════════════════════════════════════════════════
     4. DESSIN — le painter z=60
     ═════════════════════════════════════════════════════════════════════════ */
  function drawRun(ctx, str, x, y, trackPx, mode, gapPx, letPx) {
    if (!str) return;
    if (!trackPx && !gapPx && !letPx) {
      if (mode === "stroke") ctx.strokeText(str, x, y); else ctx.fillText(str, x, y);
      return;
    }
    let cx = x;
    Array.from(str).forEach((ch) => {
      if (mode === "stroke") ctx.strokeText(ch, cx, y); else ctx.fillText(ch, cx, y);
      cx += ctx.measureText(ch).width + trackPx + (letPx || 0) + (gapPx && ch === " " ? gapPx : 0);
    });
  }
  function drawArc(ctx, m, slot, mode) {
    const a = m.arc, w = m.iw;
    const cxBox = m.ix + w / 2;
    let baseY = m.top + m.sizePx;
    const chars = Array.from(m.lines[0] || "");
    const total = m.widths[0] || 0;
    const cy = a.up ? baseY + a.R : baseY - a.R;
    let phi = -(total / a.R) / 2;
    chars.forEach((ch) => {
      const cw = ctx.measureText(ch).width + m.trackPx;
      const mid = phi + (cw / 2) / a.R;
      ctx.save();
      if (a.up) {
        ctx.translate(cxBox + a.R * Math.sin(mid), cy - a.R * Math.cos(mid));
        ctx.rotate(mid);
      } else {
        ctx.translate(cxBox + a.R * Math.sin(mid), cy + a.R * Math.cos(mid));
        ctx.rotate(-mid);
      }
      if (mode === "stroke") ctx.strokeText(ch, -ctx.measureText(ch).width / 2, 0);
      else ctx.fillText(ch, -ctx.measureText(ch).width / 2, 0);
      ctx.restore();
      phi += cw / a.R;
    });
  }
  function drawLines(ctx, m, slot, mode) {
    if (m.arc) { drawArc(ctx, m, slot, mode); return; }
    m.lines.forEach((l, i) => {
      const w = m.drawn[i];
      let x = m.ix, gap = 0, let_ = 0;
      if (slot.align === "center") x = m.ix + (m.iw - w) / 2;
      else if (slot.align === "right") x = m.ix + m.iw - w;
      else if (slot.align === "justify" && w !== m.widths[i]) {
        /* le supplement a ete calcule UNE FOIS par `build()` : on le relit. */
        const s = (m.sp && m.sp[i]) || { gap: justifyGaps(l, w - m.widths[i]), let: 0 };
        gap = s.gap; let_ = s.let;
      }
      drawRun(ctx, l, x, m.top + m.sizePx + i * m.lineH, m.trackPx, mode, gap, let_);
    });
  }
  /* ── LA PLAQUE DE FOND D'UN SLOT ─────────────────────────────────────────
     Un rectangle, eventuellement arrondi, peint SOUS le texte du slot : le
     cartouche derriere un encadre de regles, la pastille derriere un cout, la
     barre derriere un nom. Elle est a P3 et pas a P2 parce qu'elle SUIT LE
     SLOT : on deplace la boite, la plaque va avec — un ornement de cadre, lui,
     reste ou le cadre l'a mis.
     Trois choix qui ne sont pas des details :
       1. MEME BOITE que le texte (`m.box`, en pixels de toile), pas la boite
          degonflee de la composition : la plaque est le FOND du slot, elle
          doit border le texte, pas s'arreter a l'interieur de sa marge
          optique.
       2. MEME PASSE et MEME ROTATION : elle est posee apres la rotation du
          slot, avant les passes d'ombre et de contour. Un slot tourne emporte
          sa plaque.
       3. RIEN PAR DEFAUT : `plate_color` nul = aucun appel de dessin, donc
          aucun octet change. C'est ce qui garde les quatre gabarits livres
          identiques a l'octet apres l'arrivee des trois reglages. */
  function plateRadiusPx(slot, g, b) {
    const mm = num(slot.plate_radius, 0, 0, PLATE_RADIUS_MAX_MM);
    /* BORNE AU DESSIN, pas seulement a la saisie : le painter recoit les
       slots du document TELS QUELS (un import, un modele, une main humaine
       dans le JSON), jamais repasses par `normSlot`. Un rayon plus grand que
       la moitie du petit cote n'a pas de sens geometrique — la toile le
       rabote elle aussi, mais en silence et pas partout pareil. */
    return Math.max(0, Math.min(g.mm2px(mm), b[2] / 2, b[3] / 2));
  }
  function platePath(ctx, b, r) {
    ctx.beginPath();
    if (r > 0 && typeof ctx.roundRect === "function") {
      ctx.roundRect(b[0], b[1], b[2], b[3], r);
      return;
    }
    if (r <= 0) { ctx.rect(b[0], b[1], b[2], b[3]); return; }
    /* repli sans `roundRect` : quatre raccords d'arc, meme trace. */
    const x = b[0], y = b[1], w = b[2], h = b[3];
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }
  function drawPlate(ctx, slot, g, m) {
    const hex = String(slot.plate_color == null ? "" : slot.plate_color);
    if (!/^#([0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(hex)) return;
    const pa = num(slot.plate_alpha, 1, 0, 1);
    if (pa <= 0) return;
    const b = m.box;
    if (!(b[2] > 0) || !(b[3] > 0)) return;
    ctx.save();
    /* L'OPACITE DU SLOT PORTE AUSSI SUR SA PLAQUE, et les deux se
       MULTIPLIENT : le `globalAlpha` d'une toile ne se compose pas tout seul,
       il REMPLACE. Un slot a 50 % avec une plaque a 80 % pose donc 40 %, et
       non 80 % — ce qui aurait fait ressortir le fond quand on efface le
       texte. */
    ctx.globalAlpha = num(slot.opacity, 100, 0, 100) / 100 * pa;
    ctx.fillStyle = hex;
    platePath(ctx, b, plateRadiusPx(slot, g, b));
    ctx.fill();
    ctx.restore();
  }
  /* ── LES IMAGES DE CALQUE, CHARGEES UNE FOIS ────────────────────────────
     Patron `IMGS` de mod-face : une entree par fichier, gardee pour toute la
     vie de l'onglet. Le painter tourne a chaque frame ; sans ce cache, chaque
     frame redecoderait le PNG.

     L'ETAT EST RESOLU, JAMAIS REJETE. Une entree vaut `{img, ok}` : `ok:false`
     dit « ce fichier n'est pas arrive », ce qui est un ETAT de la carte (le
     damier), pas une panne du painter. Une promesse rejetee, elle, aurait
     traverse le painter et noirci l'ecran des sept autres pieces.

     LE PAINTER ATTEND, comme il attend deja ses polices (`ensureFonts`) : la
     course est bornee (le CORE laisse 4 s a un painter, on n'y va jamais) et
     le rendu suivant trouve le cache chaud. Un chargement qui arrive APRES la
     course redemande un rendu de lui-meme — c'est la seule facon de voir
     apparaitre une image lente sans toucher a la souris. */
  const IMGS = new Map();          /* fichier -> {img, ok} ou Promise */
  const IMG_WAIT_MS = 2500;        /* le painter a 4 s : on garde de la marge */
  function imgRec(file) {
    const v = IMGS.get(file);
    return (v && !v.then) ? v : null;
  }
  function loadImg(file) {
    const known = IMGS.get(file);
    if (known) return known.then ? known : Promise.resolve(known);
    let res = null;
    /* LA PROMESSE ENTRE DANS LE CACHE AVANT QUE LE CHARGEMENT COMMENCE, et
       l'ETAT ne la remplace qu'a la resolution. L'ordre inverse a un piege
       reel : un echec SYNCHRONE (l'API du jeton refuse le chemin) ecrivait
       l'etat, puis le `IMGS.set` d'apres l'ecrasait par la promesse — le cache
       ne rendait plus jamais d'etat lisible et la boite restait au damier pour
       toujours. */
    const p = new Promise((r) => { res = r; }).then((rec) => {
      IMGS.set(file, rec);
      /* ARRIVEE TARDIVE : la course du painter est peut-etre deja finie et la
         carte peinte sans l'image. On redemande un rendu — exactement comme
         une police qui arrive (`loadFont`), et sous la meme garde : seulement
         si un calque VIVANT porte ce fichier. Le CORE coalesce. */
      if (rec.ok && !IN_AUDIT
        && slots().some((s) => s.on && isImage(s) && srcFile(s) === file)) M.invalidate();
      return rec;
    });
    IMGS.set(file, p);
    let done = false;
    const fin = (ok, im) => {
      if (done) return;
      done = true;
      res({ img: ok ? im : null, ok: ok, file: file });
    };
    let url = "";
    try { url = M.api.url("image/" + encodeURIComponent(file)); }
    catch (e) { fin(false, null); return p; }
    const im = new Image();
    im.decoding = "sync";
    im.onload = () => fin(true, im);
    im.onerror = () => fin(false, null);
    im.src = url;
    return p;
  }
  function ensureImgs(files) {
    const todo = files.filter((f) => f && !imgRec(f));
    if (!todo.length) return Promise.resolve();
    const all = Promise.all(todo.map(loadImg));
    return Promise.race([all, new Promise((r) => setTimeout(r, IMG_WAIT_MS))]);
  }

  /* LE DAMIER — l'etat « ce fichier n'est pas arrive », peint DANS la boite.
     Un rectangle vide se lit comme « le calque est casse » ; un damier et un
     nom se lisent comme « ce fichier-la manque », ce qui est l'information
     utile quand un deck a ete copie a moitie. C'est un etat, pas une erreur :
     le painter ne leve pas et le releve ne compte rien.

     CE DAMIER EST DANS LE FICHIER LIVRE, et c'est voulu. La toile de cette
     passe EST celle qui part au PNG et au PDF : un trou transparent aurait
     laisse partir une carte incomplete sans que rien ne le dise, alors qu'un
     damier nomme est impossible a ne pas voir sur une epreuve. Le meme fait
     est double dans la liste des blocs (badge « image absente »), pour le cas
     ou le calque serait masque, sur l'autre face ou couvert par un voisin. */
  const DAMIER_PX = 14;
  function drawDamier(ctx, b, file) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(b[0], b[1], b[2], b[3]);
    ctx.clip();
    ctx.fillStyle = "#241f2b";
    ctx.fillRect(b[0], b[1], b[2], b[3]);
    ctx.fillStyle = "#39323f";
    const n = DAMIER_PX;
    for (let y = 0; y < b[3]; y += n) {
      for (let x = 0; x < b[2]; x += n) {
        if ((((x / n) | 0) + ((y / n) | 0)) % 2) continue;
        ctx.fillRect(b[0] + x, b[1] + y, Math.min(n, b[2] - x), Math.min(n, b[3] - y));
      }
    }
    if (file) {
      const px = clamp(Math.round(Math.min(b[2] / 12, b[3] / 3)), 8, 34);
      ctx.font = px.toFixed(3) + 'px "CFT Inter", sans-serif';
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = "#e6dfd4";
      ctx.fillText(file, b[0] + b[2] / 2, b[1] + b[3] / 2);
    }
    ctx.restore();
  }
  /* LE CADRAGE — miroir de la regle de P1 (`fit_rect`), reduite aux deux modes
     qu'un calque demande. `contain` fait entrer l'image ENTIERE (des bandes
     restent sur le petit cote), `cover` REMPLIT la boite et le debordement est
     DECOUPE : sans la decoupe, un calque « cover » aurait deborde sur ses
     voisins et sur le fond perdu. */
  function fitRect(sw, sh, b, mode) {
    if (!(sw > 0) || !(sh > 0) || !(b[2] > 0) || !(b[3] > 0)) return null;
    const k = (mode === "cover")
      ? Math.max(b[2] / sw, b[3] / sh) : Math.min(b[2] / sw, b[3] / sh);
    const w = sw * k, h = sh * k;
    return [b[0] + (b[2] - w) / 2, b[1] + (b[3] - h) / 2, w, h];
  }
  /* UN CALQUE D'IMAGE. Meme squelette que `drawSlot` — opacite, rotation
     autour du centre de la boite, plaque DESSOUS — et pas une seule passe de
     glyphe : ce bloc porte peut-etre un `text` (le vocabulaire est commun),
     il n'a rien a ecrire. */
  function drawImgSlot(ctx, slot, g) {
    const b = boxPx(slot, g);
    if (!(b[2] > 0) || !(b[3] > 0)) return;
    const file = srcFile(slot);
    const rec = file ? imgRec(file) : null;
    /* SOURCE VIDE = calque qui vient de naitre, l'image n'est pas encore
       deposee. Ce n'est pas un manque : on ne salit pas la carte d'un damier
       pour un etat d'attente que le panneau montre deja. RIEN n'est peint, pas
       meme la plaque — exactement ce que fait le painter d'un bloc de texte
       vide (`if (!m.empty) drawSlot(...)`), et pour la meme raison : un
       cartouche sans son contenu est un defaut visible qu'on n'a pas demande. */
    if (!file) return;
    ctx.save();
    ctx.globalAlpha = clamp(num(slot.opacity, 100, 0, 100) / 100, 0, 1);
    if (slot.rotate) {
      const cx = b[0] + b[2] / 2, cy = b[1] + b[3] / 2;
      ctx.translate(cx, cy);
      ctx.rotate(slot.rotate * Math.PI / 180);
      ctx.translate(-cx, -cy);
    }
    /* LA PLAQUE D'ABORD, comme sous le texte : peinte apres, elle effacerait
       l'image. Elle sert au meme usage — le cartouche derriere un calque a
       fond transparent, la bande derriere une image « contain ». */
    drawPlate(ctx, slot, g, { box: b });
    if (!rec || !rec.ok) {
      /* en cours de chargement OU absente : le damier dit lequel. Les deux
         etats se ressemblent a l'ecran parce qu'ils se ressemblent en fait —
         « pas encore la ». Un chargement qui aboutit redemande un rendu. */
      drawDamier(ctx, b, file);
      ctx.restore();
      return;
    }
    const sw = rec.img.naturalWidth || rec.img.width;
    const sh = rec.img.naturalHeight || rec.img.height;
    const r = fitRect(sw, sh, b, slot.fit);
    if (r) {
      ctx.save();
      ctx.beginPath();
      ctx.rect(b[0], b[1], b[2], b[3]);
      ctx.clip();
      ctx.drawImage(rec.img, r[0], r[1], r[2], r[3]);
      ctx.restore();
    }
    ctx.restore();
  }

  function drawSlot(ctx, slot, g, m) {
    ctx.save();
    ctx.globalAlpha = clamp(slot.opacity / 100, 0, 1);
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    ctx.font = fontCss(slot, m.sizePx);
    ctx.lineJoin = "round";
    ctx.miterLimit = 2;
    if (slot.rotate) {
      const cx = m.box[0] + m.box[2] / 2, cy = m.box[1] + m.box[3] / 2;
      ctx.translate(cx, cy);
      ctx.rotate(slot.rotate * Math.PI / 180);
      ctx.translate(-cx, -cy);
    }
    /* LA PLAQUE D'ABORD — sous l'ombre, sous le contour, sous les glyphes.
       Dessinee apres eux, elle les EFFACERAIT : c'est le defaut que le banc
       de pixels de la suite existe pour attraper. */
    drawPlate(ctx, slot, g, m);
    const strokeW = pxOfPt(slot.outline, g);
    const passes = [];
    if (slot.shadow > 0 || slot.shadow_dx || slot.shadow_dy) passes.push(true);
    passes.push(false);
    passes.forEach((withShadow) => {
      ctx.save();
      if (withShadow) {
        ctx.shadowColor = slot.shadow_color;
        ctx.shadowBlur = pxOfPt(slot.shadow, g);
        ctx.shadowOffsetX = pxOfPt(slot.shadow_dx, g);
        ctx.shadowOffsetY = pxOfPt(slot.shadow_dy, g);
      }
      if (strokeW > 0) {
        ctx.strokeStyle = slot.outline_color;
        ctx.lineWidth = strokeW;
        drawLines(ctx, m, slot, "stroke");
      }
      ctx.fillStyle = slot.color;
      drawLines(ctx, m, slot, "fill");
      ctx.restore();
    });
    ctx.restore();
  }

  /* ═════════════════════════════════════════════════════════════════════════
     5. LE MODULE
     ═════════════════════════════════════════════════════════════════════════ */
  let MEAS = {};            /* id -> mesure de la derniere passe du painter */
  let MEAS_SIDE = "front";
  /* ── LE RELEVE NE SE VIDE PLUS QUAND UNE AUTRE PIECE REND LE VERSO ───────
     Le painter z=60 tourne pour CHAQUE rendu, d'ou qu'il vienne : l'apercu,
     mais aussi l'atlas de P8 ou une vignette de P2, qui demandent le VERSO.
     Sur une carte dont tous les slots sont au recto, cette passe-la mesure
     zero slot — et le releve, qui gardait la derniere passe quelle qu'elle
     soit, se vidait. MESURE : apres un simple clic sur « Pleine largeur », le
     panneau restait bloque sur « rendu en cours » et affichait « 0 ajuste(s),
     0 en depassement » pendant plus de trente secondes, alors que rien n'etait
     en cours et que la mise en page etait faite. Des compteurs a zero qui ne
     comptent rien sont exactement ce que cette piece refuse.
     On garde donc UNE mesure par face, et le releve parle de la face qui
     porte du texte — en DISANT laquelle quand ce n'est pas celle du dernier
     rendu. */
  const MEAS_BY_SIDE = { front: null, back: null };
  let LAST_SIDE = "front";
  let HOST = null, OV = null, PANEL = null;
  let UNDO = [], REDO = [];
  let dragState = null, reportTimer = null, apiTimer = null;
  let apiVerdict = null;
  /* le controle photometrique (section 7bis) */
  let AUDIT = null, AUDIT_STAMP = 0, AUDIT_DONE = -1;
  let auditTimer = null, auditing = false, IN_AUDIT = false, auditErr = "";
  let SERIES = null, seriesBusy = false;

  const M = CF.register({
    id: "type",
    title: "Typographie",
    icon: "\u{1F524}",
    order: 3,

    /* z=60 : TOUT le texte de la carte, et rien d'autre. Le painter ne recoit
       aucune echelle — la toile fait toujours geom.canvas_px, donc ce qu'on
       voit a l'ecran est le bitmap qui sera livre, reduit. */
    painters: [
      {
        z: 60,
        async fn(ctx, geom, doc, card, side) {
          const st = (doc && doc.type) || {};
          const slots = Array.isArray(st.slots) ? st.slots : [];
          const live = slots.filter((s) => s.on && (s.side === "both" || s.side === side));
          const fams = [];
          live.forEach((s) => { if (!isImage(s) && fams.indexOf(s.font) < 0) fams.push(s.font); });
          if (fams.length) await ensureFonts(fams);
          /* les fichiers des calques d'image, charges UNE FOIS et attendus ici
             — exactement comme les polices deux lignes plus haut, et pour la
             meme raison : sans l'attente, la premiere frame peindrait un
             damier a la place d'une image qui existe. */
          const files = [];
          live.forEach((s) => {
            const f = isImage(s) ? srcFile(s) : "";
            if (f && files.indexOf(f) < 0) files.push(f);
          });
          if (files.length) await ensureImgs(files);
          const meas = {};
          live.forEach((slot) => {
            /* ── UN CALQUE D'IMAGE NE LAISSE AUCUNE MESURE ─────────────────
               `meas` est l'entree des trois passes d'encre (controle
               photometrique, releve du halo, second tirage) et du releve du
               panneau. Un calque d'image n'a pas de glyphe : il n'a ni corps
               compose, ni taux de survie, ni contraste. Y entrer l'aurait fait
               compter comme un « slot vide » — un defaut annonce qui n'existe
               pas. On sort AVANT `layoutSlot`. */
            if (isImage(slot)) { drawImgSlot(ctx, slot, geom); return; }
            const text = textOf(slot, card);
            /* UN SLOT VIDE EST UN FAIT, PAS UN NON-EVENEMENT. Avant, il
               sortait de la boucle sans laisser de trace : la carte partait
               avec un orbe creux et le releve n'avait rien a dire. Il est
               desormais MESURE (mise en page a vide) et compte comme « vide »
               — un deck importe avec une colonne manquante se voit. */
            const m = layoutSlot(ctx, slot, geom, text);
            m.empty = !String(text).length;
            if (!m.empty) drawSlot(ctx, slot, geom, m);
            meas[slot.id] = m;
          });
          /* Les mesures sont TOUJOURS reprises, y compris pendant le controle
             photometrique : c'est ce qui garantit que l'encre redessinee seule
             et le composite relu viennent de la MEME passe. Ce qui est
             suspendu, c'est la boucle de releve — sans quoi l'audit
             relancerait l'audit qui relancerait l'audit. */
          MEAS_BY_SIDE[side] = meas;
          LAST_SIDE = side;
          const autre = side === "front" ? "back" : "front";
          const dispo = MEAS_BY_SIDE[autre] && Object.keys(MEAS_BY_SIDE[autre]).length;
          if (live.length || !dispo) { MEAS = meas; MEAS_SIDE = side; }
          else { MEAS = MEAS_BY_SIDE[autre]; MEAS_SIDE = autre; }
          if (IN_AUDIT) return;
          AUDIT_STAMP++;
          scheduleReport();
        },
      },
    ],

    state: {
      slots: [],            /* [{id, label, box:[x,y,w,h] mm depuis la coupe, ...}] — LU par data et par print */
      sel: "",              /* slot selectionne */
      preset: "champion",   /* dernier gabarit applique */
      seeded: false,        /* le gabarit de depart a deja ete pose une fois */
      font_default: "Inter",
      autofit: true,        /* defaut des nouveaux slots */
      show_boxes: true,     /* calque d'edition sur l'apercu */
      fit_rect: [],         /* zone sure (mm) pour laquelle la mise en page a ete faite */
      optical_mm: OPTICAL_MM_DEF,  /* marge optique retranchee de chaque boite */
      audit: true,          /* controle photometrique automatique */
    },

    async init(host) {
      HOST = host;
      PANEL = host.closest ? host.closest(".cf-panel") : null;
      buildPanel();
      buildOverlay();
      await loadCatalog();
      seedIfEmpty();
      /* les polices REELLEMENT utilisees, chargees avant le premier rendu :
         sans cela le painter attend au demarrage (jusqu'a 2,5 s a froid) et
         le releve chiffre apparait un battement apres la carte. */
      const used = [];
      slots().forEach((s) => {
        if (!isImage(s) && used.indexOf(s.font) < 0) used.push(s.font);
      });
      if (used.length) await ensureFonts(used);
      renderAll();
      CF.on("core:geom", () => { renderAll(); syncOverlay(); });
      CF.on("core:cards", () => { renderAll(); });
      CF.on("core:render", () => { syncOverlay(); });
      CF.on("core:doc", (p) => { if (!SELF && p && p.id === "type") renderAll(); });
      if (typeof ResizeObserver === "function") {
        const st = document.querySelector(".stage-wrap");
        if (st) new ResizeObserver(() => syncOverlay()).observe(st);
      }
      window.addEventListener("resize", syncOverlay);
      document.addEventListener("keydown", onKey, true);
      document.addEventListener("paste", onPaste);
      if (PANEL && typeof MutationObserver === "function") {
        new MutationObserver(() => syncOverlay()).observe(PANEL, { attributes: true, attributeFilter: ["class"] });
      }
      M.invalidate();
    },
  });

  /* ── etat courant ──────────────────────────────────────────────────────── */
  /* TOUTE ecriture passe par ici. `SELF` est leve pendant l'emission
     synchrone de "core:doc" : sans lui, l'abonne redessinerait le panneau au
     milieu d'une frappe et la zone de texte perdrait le focus au premier
     caractere (le champ est recree). Les rendus voulus sont explicites. */
  let SELF = false;
  function mpatch(partial) {
    SELF = true;
    try { return M.patch(partial); } finally { SELF = false; }
  }
  const slots = () => (CF.get("type.slots", []) || []).slice();
  const selId = () => CF.get("type.sel", "");
  function selSlot() {
    const a = slots(), id = selId();
    return a.filter((s) => s.id === id)[0] || a[0] || null;
  }
  function textOf(slot, card) {
    const f = (card && card.fields) ? card.fields[slot.id] : null;
    const v = (f == null ? "" : String(f));
    return v.trim() !== "" ? v : String(slot.text || "");
  }
  function pushUndo() {
    UNDO.push({ slots: clone(slots()), sel: selId() });
    if (UNDO.length > UNDO_MAX) UNDO.shift();
    REDO.length = 0;
  }
  function commit(next, sel) {
    const p = { slots: next.map((s, i) => normSlot(s, i)) };
    if (sel !== undefined) p.sel = sel;
    mpatch(p);
  }
  function undo() {
    if (!UNDO.length) { M.toast("rien à annuler"); return; }
    const cur = { slots: clone(slots()), sel: selId() };
    const prev = UNDO.pop();
    REDO.push(cur);
    mpatch({ slots: prev.slots, sel: prev.sel });
    renderAll();
  }
  function redo() {
    if (!REDO.length) { M.toast("rien à rétablir"); return; }
    const cur = { slots: clone(slots()), sel: selId() };
    const nx = REDO.pop();
    UNDO.push(cur);
    mpatch({ slots: nx.slots, sel: nx.sel });
    renderAll();
  }

  async function loadCatalog() {
    try {
      const r = await M.api.get("fonts");
      if (r && Array.isArray(r.fonts) && r.fonts.length) {
        FONTS = r.fonts;
        indexFonts();
      }
    } catch (e) {
      /* hors ligne : le repli local porte les 23 memes familles */
      console.warn("cardforge/type: catalogue de polices hors ligne", e && e.message);
    }
    indexFonts();
  }

  function seedIfEmpty() {
    const a = slots();
    if (a.length || CF.get("type.seeded", false)) {
      if (a.length && !CF.get("type.fit_rect", []).length) {
        mpatch({ fit_rect: safeRectMm(CF.geom()).map((v) => Math.round(v * 1e4) / 1e4) });
      }
      return;
    }
    applyPreset(CF.get("type.preset", "champion"), true);
  }
  function applyPreset(pid, silent) {
    const g = CF.geom();
    const next = presetSlots(pid, g);
    if (!silent) pushUndo();
    /* on ouvre sur le TITRE : c'est le slot qui porte le cas difficile (44
       caracteres) et celui qu'on regle en premier neuf fois sur dix. */
    const first = (next.filter((s) => s.id === "title")[0] || next[0] || {}).id || "";
    mpatch({
      slots: next, preset: pid, seeded: true, sel: first,
      fit_rect: safeRectMm(g).map((v) => Math.round(v * 1e4) / 1e4),
    });
    if (!silent) M.toast("gabarit « " + (PRESETS[pid] || {}).label + " » posé — " + next.length + " slots");
    renderAll();
  }
  /* Reechelonnage : la mise en page suit la zone sure d'un format a l'autre.
     Ce n'est PAS automatique — on ne redispose pas le travail de quelqu'un
     sans le lui demander — mais c'est un clic, pas une reprise a la main. */
  function refit() {
    const g = CF.geom(), now = safeRectMm(g), was = CF.get("type.fit_rect", []);
    if (!was || was.length !== 4 || !was[2] || !was[3]) {
      mpatch({ fit_rect: now.map((v) => Math.round(v * 1e4) / 1e4) });
      renderAll();
      return;
    }
    pushUndo();
    const kx = now[2] / was[2], ky = now[3] / was[3];
    const next = slots().map((s) => {
      const b = s.box;
      return Object.assign(clone(s), {
        box: [now[0] + (b[0] - was[0]) * kx, now[1] + (b[1] - was[1]) * ky,
          b[2] * kx, b[3] * ky].map((v) => Math.round(v * 1e4) / 1e4),
        size_pt: Math.round(s.size_pt * Math.min(kx, ky) * 100) / 100,
        min_pt: Math.round(s.min_pt * Math.min(kx, ky) * 100) / 100,
      });
    });
    mpatch({ slots: next.map((s, i) => normSlot(s, i)), fit_rect: now.map((v) => Math.round(v * 1e4) / 1e4) });
    M.toast("mise en page réadaptée à " + CF.geom().label);
    renderAll();
  }

  /* ═════════════════════════════════════════════════════════════════════════
     6. PANNEAU
     ═════════════════════════════════════════════════════════════════════════ */
  function buildPanel() {
    HOST.innerHTML = ''
      + '<div class="cf-type-bar">'
      + '  <button class="btn sm cf-type-add" type="button" title="Nouveau bloc de texte, posé au centre du cadre de composition">+ Slot</button>'
      /* LA NATURE SE CHOISIT A LA NAISSANCE, et c'est pour cela qu'il y a deux
         boutons plutot qu'une bascule dans le panneau. Voir `addImgSlot`. */
      + '  <button class="btn sm cf-type-addimg" type="button" title="Nouveau calque d\'image, posé au centre du cadre de composition — il se peint au-dessus du cadre de base et sous le décor haut">+ Image</button>'
      + '  <button class="btn sm cf-type-preset" type="button" title="Poser un gabarit complet">Gabarits</button>'
      + '  <span class="stage-sep" aria-hidden="true"></span>'
      + '  <button class="btn sm cf-type-undo" type="button" title="Annuler (Ctrl+Z)">&#8630;</button>'
      + '  <button class="btn sm cf-type-redo" type="button" title="Rétablir (Ctrl+Y)">&#8631;</button>'
      + '  <button class="chip cf-type-boxes" type="button" title="Cadres d\'édition sur l\'aperçu (jamais exportés)">&#9635; Cadres</button>'
      + '  <button class="chip cf-type-audit" type="button" title="Contrôle photométrique : relit le fichier de la carte et compte l\'encre réellement visible, slot par slot">&#9673; Lisibilité</button>'
      + '  <label class="cf-type-opt" title="Marge optique retranchée de chaque boîte avant composition : les repères de coupe d\'une rotative dérivent de ±0,5 mm.">'
      + '<span>Marge optique</span><input type="number" class="cf-type-optv" step="0.25" min="0" max="' + OPTICAL_MM_MAX + '"><i>mm</i></label>'
      + '  <button class="btn sm cf-type-refit hidden" type="button" title="Réadapter la mise en page au format courant">Réadapter</button>'
      + '  <span class="tb-spacer"></span>'
      + '  <span class="cf-type-count mono"></span>'
      + '</div>'
      + '<div class="cf-type-cols">'
      + '  <div class="cf-type-left">'
      + '    <div class="cf-type-list"></div>'
      /* LE MEMO CLAVIER NE S'IMPRIME PLUS SUR L'ECRAN. Deplie, il occupait
         trois lignes du panneau pour redire ce que la souris apprend en une
         seconde. Replie, il reste a un clic et dans le DOM — rien n'est perdu,
         la place revient a la liste des blocs. */
      + '    <details class="cf-type-keys"><summary>Raccourcis</summary>'
      + '<p class="hint">Sur l\'aperçu : <b>glisser</b> déplace, les coins redimensionnent. '
      + 'Clavier : <b>flèches</b> 1 mm (<b>Maj</b> 0,2 mm), <b>Alt+flèches</b> redimensionne, '
      + '<b>Ctrl+D</b> duplique, <b>Suppr</b> supprime, <b>Ctrl+Z</b> annule. '
      + 'Un bloc <b>verrouillé</b> (cadenas) refuse ces gestes et reste réglable ici.</p></details>'
      + '  </div>'
      + '  <div class="cf-type-insp"></div>'
      + '</div>'
      + '<div class="cf-type-proof"></div>';
    HOST.querySelector(".cf-type-add").addEventListener("click", addSlot);
    HOST.querySelector(".cf-type-addimg").addEventListener("click", addImgSlot);
    HOST.querySelector(".cf-type-preset").addEventListener("click", openPresets);
    HOST.querySelector(".cf-type-undo").addEventListener("click", undo);
    HOST.querySelector(".cf-type-redo").addEventListener("click", redo);
    HOST.querySelector(".cf-type-refit").addEventListener("click", refit);
    HOST.querySelector(".cf-type-boxes").addEventListener("click", () => {
      mpatch({ show_boxes: !CF.get("type.show_boxes", true) });
      renderAll(); syncOverlay();
    });
    HOST.querySelector(".cf-type-audit").addEventListener("click", () => {
      const on = !CF.get("type.audit", true);
      mpatch({ audit: on });
      AUDIT = null;
      renderAll();
      if (on) scheduleAudit();
    });
    const ov = HOST.querySelector(".cf-type-optv");
    ov.value = nv(CF.get("type.optical_mm", OPTICAL_MM_DEF));
    const applyOpt = () => {
      const v = clamp(Number(ov.value) || 0, 0, OPTICAL_MM_MAX);
      ov.value = nv(v);
      mpatch({ optical_mm: v });
      AUDIT = null;
      M.invalidate();
      renderAll();
    };
    ov.addEventListener("change", applyOpt);
    ov.addEventListener("keydown", (e) => { if (e.key === "Enter") { applyOpt(); e.preventDefault(); } });
  }

  function addSlot() {
    const a = slots();
    if (a.length >= SLOTS_MAX) { M.toast("40 slots au maximum", true); return; }
    const g = CF.geom(), sr = safeRectMm(g);
    let n = 1;
    while (a.filter((s) => s.id === "texte" + n).length) n++;
    const s = normSlot({
      id: "texte" + n, label: "Texte " + n,
      box: [sr[0] + sr[2] * 0.15, sr[1] + sr[3] * 0.42, sr[2] * 0.7, sr[3] * 0.1],
      font: CF.get("type.font_default", "Inter"),
      size_pt: 10, min_pt: 5, align: "center", valign: "middle",
      autofit: CF.get("type.autofit", true),
      text: "Nouveau texte",
    }, a.length);
    pushUndo();
    commit(a.concat([s]), s.id);
    renderAll();
  }
  /* ── UN CALQUE D'IMAGE NAIT ICI, ET SEULEMENT ICI ───────────────────────
     DECISION : la nature d'un bloc se pose A LA NAISSANCE ; le panneau la
     MONTRE et ne la bascule pas.

     Une bascule aurait change le SENS des reglages d'un bloc existant sous la
     main de l'utilisateur : un `src` sur un bloc de texte ne veut rien dire,
     une police et une casse sur un calque d'image non plus. Et elle aurait
     pose une question sans bonne reponse — que faire du texte deja saisi, de
     l'image deja importee, du reglage d'ajustement ? La manoeuvre honnete
     (creer l'autre, deplacer la boite, supprimer le premier) tient en deux
     clics et laisse une trace dans HIST, ce qu'une bascule silencieuse ne
     ferait pas.

     La palette d'elements de la tache 3 appellera CETTE fonction : elle n'aura
     pas a savoir ce qu'est un calque d'image. */
  function addImgSlot() {
    const a = slots();
    if (a.length >= SLOTS_MAX) { M.toast(SLOTS_MAX + " slots au maximum", true); return; }
    const g = CF.geom(), sr = safeRectMm(g);
    let n = 1;
    while (a.filter((s) => s.id === "image" + n).length) n++;
    const s = normSlot({
      id: "image" + n, label: "Image " + n,
      kind: "image", fit: "contain",
      /* une boite CARREE au centre : un calque naissant n'a pas encore
         d'image, donc pas de rapport de forme a respecter — le fit s'en
         chargera au depot, et la poignee au millimetre pres. */
      box: [sr[0] + sr[2] * 0.2, sr[1] + sr[3] * 0.3, sr[2] * 0.6, sr[3] * 0.3],
    }, a.length);
    pushUndo();
    commit(a.concat([s]), s.id);
    renderAll();
  }
  function dupSlot() {
    const s = selSlot();
    if (!s) return;
    const a = slots();
    let n = 2, nid = s.id + n;
    while (a.filter((x) => x.id === nid).length) { n++; nid = s.id + n; }
    /* CTRL+D SUR UN BLOC VERROUILLE EST PERMIS, ET LA COPIE NAIT OUVERTE.
       Dupliquer ne touche pas au bloc protege : cela en pose un AUTRE, a 2 mm,
       avec un identifiant neuf — un acte d'intention, comme un reglage du
       panneau, pas un geste de scene. Et le verrou marque un bloc DEJA place :
       une copie qu'on vient de creer, elle, se place. Nee fermee, elle aurait
       refuse le glisser qui la suit d'une seconde sans que rien a l'ecran ne
       dise pourquoi. */
    const c = Object.assign(clone(s), {
      id: nid, label: s.label + " (copie)",
      box: [s.box[0] + 2, s.box[1] + 2, s.box[2], s.box[3]],
      lock: false,
    });
    pushUndo();
    commit(a.concat([c]), nid);
    renderAll();
  }
  function delSlot(id) {
    const a = slots(), i = a.map((s) => s.id).indexOf(id || selId());
    if (i < 0) return;
    pushUndo();
    const next = a.slice(0, i).concat(a.slice(i + 1));
    commit(next, next.length ? next[Math.min(i, next.length - 1)].id : "");
    renderAll();
  }
  function moveSlot(id, dir) {
    const a = slots(), i = a.map((s) => s.id).indexOf(id);
    const j = i + dir;
    if (i < 0 || j < 0 || j >= a.length) return;
    pushUndo();
    const t = a[i]; a[i] = a[j]; a[j] = t;
    commit(a, id);
    renderAll();
  }
  function patchSlot(id, partial, noUndo) {
    const a = slots(), i = a.map((s) => s.id).indexOf(id);
    if (i < 0) return;
    if (!noUndo) pushUndo();
    a[i] = normSlot(Object.assign(clone(a[i]), partial), i);
    commit(a);
  }

  /* ── liste des slots ───────────────────────────────────────────────────── */
  function renderList() {
    const wrap = HOST && HOST.querySelector(".cf-type-list");
    if (!wrap) return;                 /* pas de panneau : rien a ecrire dedans */
    const a = slots(), sel = selId();
    if (!a.length) {
      wrap.innerHTML = '<div class="cf-type-empty">'
        + '<b>Aucun slot de texte.</b>'
        + '<p class="hint">Un gabarit pose d\'un coup le titre, le coût, les statistiques, '
        + 'l\'encadré de règles, l\'ambiance et les crédits — déjà calés sur le format courant.</p>'
        + '<div class="cf-type-egal">'
        + Object.keys(PRESETS).map((p) => '<button class="btn sm cf-type-ep" type="button" data-p="' + p + '">'
          + esc(PRESETS[p].label) + '</button>').join("")
        + '</div></div>';
      wrap.querySelectorAll(".cf-type-ep").forEach((b) => {
        b.addEventListener("click", () => applyPreset(b.dataset.p));
      });
      return;
    }
    const card = CF.card(CF.current());
    wrap.innerHTML = a.map((s) => {
      /* UN CALQUE D'IMAGE N'A AUCUN BADGE DE TEXTE. Il n'entre pas dans le
         relevé (le painter l'écarte), donc `m` et `au` sont vides pour lui de
         toute façon — mais on le DIT ici plutôt que de compter là-dessus : un
         badge « vide » sur un calque d'image annoncerait un défaut inexistant,
         et c'est exactement le genre de compteur menteur que cette pièce
         pourchasse. */
      const img = isImage(s);
      const m = img ? null : MEAS[s.id];
      const au = img ? null : auditOf(s.id);
      const tofu = img ? [] : tofuOf(s, textOf(s, card));
      const vide = m && m.empty;
      const bad = m && m.over && !vide;
      const shr = m && m.shrunk && !bad && !vide;
      const masq = au && !au.empty && au.exact && au.rate < SURV_MIN;
      const lowc = au && !au.empty && au.contrast_min != null && au.contrast_min < au.seuil;
      const fichier = img ? srcFile(s) : "";
      /* le relevé du slot, en clair, au survol : ce sont les chiffres relus
         sur les octets du composite, pas une estimation. */
      const tip = img
        ? ("calque d'image — " + (fichier ? fichier + ", cadrage "
          + (s.fit === "cover" ? "remplir" : "entière")
          : "aucune image déposée") + " · aucune mesure d'encre : ce bloc n'a pas de glyphe")
        : !au ? "mesure en cours" : (au.empty ? "slot sans glyphe"
        : (au.total + " px de corps de glyphe · " + (au.exact ? fx(au.rate * 100, 1) + " % visibles"
          : "survie non mesurable (opacité < 100 %)")
          + (au.contrast_min != null ? " · contraste " + fx(au.contrast_min, 2) + ":1 (seuil "
            + fx(au.seuil, 1) + ":1 à " + fx(au.pt, 1) + " pt)" : "")
          + (au.lum_a != null ? " = " + contrastCalc(au) + " sur " + au.bg_n
            + " points de fond · " + contrastWhere(au) : "")
          + (au.via === "contour" && au.contrast_direct != null
            ? " · sans le contour " + fx(au.contrast_direct, 2) + ":1" : "")
          + (au.clear_mm != null ? " · dégagement " + fx(au.clear_mm, 2) + " mm" : "")
          + (au.ink_px ? " · encre " + (au.clipped ? "≥ " : "") + au.ink_px[2] + " x "
            + au.ink_px[3] + " px (anticrénelage compris)"
            + (au.ink_core_px ? ", corps plein " + au.ink_core_px[2] + " x "
              + au.ink_core_px[3] + " px" : "") : "")
          + (au.halo_px ? " · halo d'ombre " + au.halo_px[2] + " x " + au.halo_px[3]
            + " px, à " + fx(au.halo_clear_mm, 2) + " mm du cadre de composition" : "")));
      return '<div class="cf-type-row' + (s.id === sel ? " on" : "") + (s.on ? "" : " off")
        + '" data-id="' + esc(s.id) + '" data-audit="' + esc(tip) + '" title="' + esc(tip) + '" draggable="true">'
        + '<button class="cf-type-eye" type="button" title="Afficher / masquer">' + (s.on ? "&#9679;" : "&#9675;") + '</button>'
        /* LE CADENAS. Meme rang que l'oeil : deux etats d'un bloc, pas deux
           familles de commandes. Il protege des GESTES DE SCENE (glisser,
           poignees, fleches, Suppr au clavier) et de rien d'autre — la ligne
           reste cliquable, donc le panneau reste atteignable, donc le verrou
           se reprend. Un verrou dont on ne sait plus sortir serait pire que
           pas de verrou du tout.
           CE QUI RESTE LIBRE, ET POURQUOI : l'oeil, l'ordre, la corbeille de
           CETTE ligne, le panneau, Ctrl+D. Ce sont des actes VISES — on a
           clique sur la commande de ce bloc-la. Le verrou arrete la main qui
           derape sur l'apercu et la touche pressee au hasard, pas la decision
           prise en connaissance de cause. */
        + '<button class="cf-type-lock' + (s.lock ? " on" : "") + '" type="button" title="'
        + (s.lock ? "Déverrouiller ce bloc" : "Verrouiller ce bloc — il refusera le glisser, "
          + "les poignées, les flèches et Suppr ; le panneau continuera de le régler")
        + '">' + (s.lock ? "&#128274;" : "&#128275;") + '</button>'
        /* LE BADGE DE NATURE. La liste est la seule vue où les deux natures se
           croisent : elle doit les distinguer d'un coup d'œil, sans quoi
           « Image 1 » et « Texte 1 » se ressemblent jusqu'au clic. */
        + '<em class="cf-type-kind' + (img ? " img" : "") + '" title="'
        + esc(img ? "Calque d'image — il se peint dans sa boîte, au-dessus du "
          + "cadre de base et sous le décor haut" : "Bloc de texte")
        + '">' + (img ? "&#128444;" : "T") + '</em>'
        + '<span class="cf-type-nm"><b>' + esc(s.label) + '</b><i class="mono">' + esc(s.id) + '</i></span>'
        + '<span class="cf-type-meta mono">'
        + (img
          ? (fichier ? esc(fichier) : "sans image")
            + ' · ' + (s.fit === "cover" ? "remplir" : "entière")
          : esc(fontLabel(s.font)) + ' · ' + fx(m ? m.pt : s.size_pt, 1) + ' pt')
        + (!img && synthNote(s) ? ' · <i class="cf-type-syn" title="' + esc(synthNote(s)) + '">'
          + (s.bold ? "G" : "") + (s.italic ? "I" : "") + '*</i>' : "")
        + (s.side !== "front" ? ' · ' + (s.side === "back" ? "verso" : "R/V") : "") + '</span>'
        + (vide ? '<em class="cf-type-badge bad" title="slot configuré, aucun glyphe posé">vide</em>' : '')
        /* LE FICHIER QUI N'EST PAS ARRIVE. L'aperçu le dit déjà (damier + nom
           dans la boîte) ; la liste le dit aussi, parce qu'un calque peut être
           masqué, hors face ou caché sous un autre — et il partirait alors à
           l'impression sans que rien ne l'ait annoncé. */
        + (img && fichier && imgRec(fichier) && !imgRec(fichier).ok
          ? '<em class="cf-type-badge bad" title="' + esc(fichier
            + " n'est pas dans ce jeu — l'aperçu pose un damier à sa place")
            + '">image absente</em>' : '')
        /* LE BADGE QUI MANQUAIT : ce texte contient des signes que cette
           police n'a pas. Le navigateur les emprunte ailleurs, sans un mot. */
        + (tofu.length && !vide ? '<em class="cf-type-badge bad" title="'
          + esc(tofu.join(" ") + ' — « ' + fontLabel(s.font) + ' » ne porte pas ' + (tofu.length > 1 ? 'ces signes' : 'ce signe')
            + ' (lu dans la table cmap du fichier). Le navigateur les dessine avec une autre police.')
          + '">' + esc(tofu.join("")) + ' hors police</em>' : '')
        + (masq ? '<em class="cf-type-badge bad" title="' + Number(au.masked) + ' px d\'encre recouverts par une couche dessinée au-dessus">'
          + fx((1 - au.rate) * 100, 0) + ' % masqué</em>' : '')
        + (lowc && !masq ? '<em class="cf-type-badge bad" title="contraste mesuré contre le fond réellement derrière l\'encre">'
          + fx(au.contrast_min, 1) + ':1</em>' : '')
        /* L'ORDRE DIT LA GRAVITE. « Hors cadre » d'abord (de l'encre part
           hors du cadre), puis « sous le plancher » (le fichier est juste, la
           carte ne se lira pas), puis « ajuste » — qui ne s'affiche PLUS quand
           le corps est passe sous le plancher de lisibilite : un badge vert
           sur un titre a 9 pt certifiait l'encombrement et taisait la lecture. */
        + (bad ? '<em class="cf-type-badge bad" title="' + Number(m.over_chars)
          + ' caractères débordent du cadre — ils sont dessinés quand même">'
          + m.over_chars + ' hors cadre</em>'
          : (m && m.under_read)
            ? '<em class="cf-type-badge warn" title="composé à ' + fx(m.pt, 1)
              + ' pt pour ' + fx(m.read_pt, 1)
              + ' pt réglés — le texte tient dans sa boîte, il ne se lira pas à taille réelle">'
              + fx(m.pt, 1) + ' &lt; ' + fx(m.read_pt, 1) + ' pt</em>'
            /* le badge porte la MESURE de l'ajustement, plus son nom : « ajusté »
               ne disait pas ce qu'il avait coûté. */
            : shr ? '<em class="cf-type-badge ok" title="corps ramené de ' + fx(s.size_pt, 1)
              + ' à ' + fx(m.pt, 1) + ' pt, ' + m.posed + ' des ' + m.srcn
              + ' signes posés">' + fx(s.size_pt, 1) + ' → ' + fx(m.pt, 1) + ' pt</em>' : '')
        + '<span class="cf-type-ops">'
        + '<button class="cf-type-mv" type="button" data-d="-1" title="Monter">&#9650;</button>'
        + '<button class="cf-type-mv" type="button" data-d="1" title="Descendre">&#9660;</button>'
        + '<button class="cf-type-del" type="button" title="Supprimer">&#10005;</button>'
        + '</span></div>';
    }).join("");
    wrap.querySelectorAll(".cf-type-row").forEach((row) => {
      const id = row.dataset.id;
      row.addEventListener("click", (e) => {
        if (e.target.closest("button")) return;
        mpatch({ sel: id }); renderAll(); syncOverlay();
      });
      row.querySelector(".cf-type-eye").addEventListener("click", () => {
        const s = slots().filter((x) => x.id === id)[0];
        patchSlot(id, { on: !s.on });
        renderAll();
      });
      row.querySelector(".cf-type-lock").addEventListener("click", () => {
        const s = slots().filter((x) => x.id === id)[0];
        /* UNE entree d'annulation PAR GESTE : patchSlot en pousse une seule,
           comme l'oeil juste au-dessus. */
        patchSlot(id, { lock: !s.lock });
        renderAll();
      });
      row.querySelectorAll(".cf-type-mv").forEach((b) => {
        b.addEventListener("click", () => moveSlot(id, Number(b.dataset.d)));
      });
      row.querySelector(".cf-type-del").addEventListener("click", () => delSlot(id));
      row.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData("text/plain", id);
        e.dataTransfer.effectAllowed = "move";
        row.classList.add("drag");
      });
      row.addEventListener("dragend", () => row.classList.remove("drag"));
      row.addEventListener("dragover", (e) => { e.preventDefault(); row.classList.add("over"); });
      row.addEventListener("dragleave", () => row.classList.remove("over"));
      row.addEventListener("drop", (e) => {
        e.preventDefault(); row.classList.remove("over");
        const from = e.dataTransfer.getData("text/plain");
        if (!from || from === id) return;
        const a2 = slots(), i = a2.map((s) => s.id).indexOf(from), j = a2.map((s) => s.id).indexOf(id);
        if (i < 0 || j < 0) return;
        pushUndo();
        const moved = a2.splice(i, 1)[0];
        a2.splice(j, 0, moved);
        commit(a2, from);
        renderAll();
      });
    });
  }
  function fontLabel(id) {
    const f = FONT_BY_ID[id];
    return f ? f.label : id;
  }
  /* ── GRAS ET ITALIQUE : DITS POUR CE QU'ILS SONT ───────────────────────
     Le catalogue sert UN fichier par famille (compte par le backend, pas
     promis : `faces` vaut 1 partout tant qu'aucune famille n'a de second
     fichier). Une famille d'une seule graisse ne PEUT PAS charger un vrai
     gras ni un vrai italique : le navigateur epaissit le trait et penche le
     glyphe lui-meme. C'est un rendu acceptable, ce n'est pas la meme chose
     qu'un caractere dessine, et le bouton G ne doit pas laisser croire le
     contraire. Le jour ou une famille recoit un second fichier, `faces`
     passe a 2 et la mention disparait toute seule. */
  function facesOf(id) {
    const f = FONT_BY_ID[id];
    return (f && isFinite(Number(f.faces))) ? Number(f.faces) : 1;
  }
  /* ── CE QUE LA POLICE NE SAIT PAS ECRIRE ────────────────────────────────
     Un glyphe absent ne fait pas de bruit : le navigateur va le chercher dans
     une AUTRE police, caractere par caractere, et le mot part a l'impression
     avec un « é » d'une fonte etrangere — ou un rectangle vide. C'est la
     meme faute que la troncature muette, jouee sur un seul signe.
     La liste vient du backend, qui l'a lue dans la table cmap du FICHIER (pas
     d'une mesure de chasse, qui confond « absent » et « meme largeur »).
     `null` = table illisible ou catalogue hors ligne : on dit « inconnu ». */
  function frMissingOf(id) {
    const f = FONT_BY_ID[id];
    return (f && Array.isArray(f.fr_missing)) ? f.fr_missing : null;
  }
  /* les caracteres DISTINCTS du texte reellement pose (casse appliquee) que
     cette police n'a pas. Ordre d'apparition, blancs exclus. */
  function tofuOf(slot, text) {
    const miss = frMissingOf(slot.font);
    if (!miss || !miss.length) return [];
    const t = applyCase(String(text == null ? "" : text), slot.caps);
    const out = [];
    for (const ch of t) {
      if (miss.indexOf(ch) >= 0 && out.indexOf(ch) < 0 && ch.trim()) out.push(ch);
    }
    return out;
  }
  function frCount() {
    let ok = 0, bad = 0, unk = 0;
    FONTS.forEach((f) => {
      if (!Array.isArray(f.fr_missing)) unk++;
      else if (f.fr_missing.length) bad++;
      else ok++;
    });
    return { n: FONTS.length, ok: ok, bad: bad, unk: unk };
  }
  function synthNote(slot) {
    if (!slot || (!slot.bold && !slot.italic)) return "";
    if (facesOf(slot.font) > 1) return "";
    const q = [];
    if (slot.bold) q.push("gras");
    if (slot.italic) q.push("italique");
    return q.join(" et ") + " synthétique — « " + fontLabel(slot.font)
      + " » n'a qu'un fichier, donc une seule graisse et un seul style : "
      + "le navigateur épaissit et penche le glyphe, il ne charge pas un caractère dessiné.";
  }

  /* ── inspecteur ────────────────────────────────────────────────────────── */
  /* Un champ NUMERIQUE EDITABLE partout ou la barre n'a que des boutons.
     La cle est portee par l'attribut, pas par le rang dans le DOM : ajouter
     un champ au milieu ne peut pas decaler silencieusement les onze autres. */
  const nv = (v) => String(Math.round(Number(v) * 1e3) / 1e3);
  function nfield(key, label, value, step, title, min, max) {
    return '<label class="fld cf-type-f"><span class="lbl">' + esc(label) + '</span>'
      + '<input type="number" data-k="' + key + '" value="' + nv(value) + '" step="' + step + '"'
      + (min === undefined ? "" : ' min="' + min + '"') + (max === undefined ? "" : ' max="' + max + '"')
      + ' title="' + esc(title || label) + '"></label>';
  }
  function segf(label, key, opts, cur, titles) {
    return '<div class="fld cf-type-f"><span class="lbl">' + esc(label) + '</span>'
      + '<div class="seg sm cf-type-seg" data-k="' + key + '">'
      + opts.map((o, i) => '<button class="seg-b' + (o[0] === cur ? " active" : "") + '" type="button" data-v="'
        + esc(o[0]) + '" title="' + esc((titles && titles[i]) || o[1]) + '">' + o[1] + '</button>').join("")
      + '</div></div>';
  }
  /* ── LES MESURES DE L'INSPECTEUR, DANS UNE SEULE FONCTION ────────────────
     Elles vivaient dans le corps de `renderInsp`, qui n'est PAS rappele par
     le releve (le reconstruire pendant une frappe volerait le focus du champ
     en cours). Resultat mesure dans l'app : le pied de l'inspecteur annonçait
     « corps 14 pt (58,3 px) » — le corps DEMANDE — pendant que le releve, dix
     lignes plus bas, annonçait 9 pt : le corps POSE. Deux chiffres pour la
     meme grandeur, dont un faux. Le bloc est donc isole ici et reecrit seul
     apres chaque mise en page, sans toucher aux champs. */
  function inspMeas(s) {
    /* un SEUL conteneur : le bloc passe d'un paragraphe a deux des que le slot
       gagne une ligne, et remplacer paragraphe par paragraphe aurait laisse
       tomber la mise a jour precisement dans ce cas-la (mesure : le pied
       restait a « 14 pt » sur le titre, qui est justement celui qui passe a
       deux lignes). */
    return '<div class="cf-type-meas">' + inspMeasInner(s) + '</div>';
  }
  function inspMeasInner(s) {
    const g = CF.geom(), m = MEAS[s.id], bpx = boxPx(s, g);
    return '<p class="hint mono cf-type-bpx">' + fx(bpx[2], 1) + ' x ' + fx(bpx[3], 1) + ' px de toile'
      + ' · corps ' + (m ? corps(m, g) : fx(s.size_pt, 1) + " pt (" + fx(pxOfPt(s.size_pt, g), 1)
        + " px) — <i>demandé, pas encore composé</i>")
      + (m && m.under_read ? ' · <b>plus petit que les ' + fx(m.read_pt, 1)
        + ' pt réglés</b>' : "")
      + ' · cadre de composition ' + g.safe_px[0] + ' x ' + g.safe_px[1] + ' px'
      + ' · marge optique ' + fx(CF.get("type.optical_mm", OPTICAL_MM_DEF), 2) + ' mm'
      /* LA REGLE DE CONVERSION, A COTE DES MILLIMETRES. Les boites sont en mm
         et le fichier est en pixels : sans le facteur, aucun des chiffres en
         mm de ce panneau ne se verifie sur les octets. Avec lui, chacun se
         recalcule a la main. */
      + ' · 1 mm = ' + fx(g.mm2px(1), 3) + ' px à ' + g.dpi + ' DPI</p>'
      /* les chiffres du paragraphe SOUS les reglages qui les produisent : le
         releve du bas ne detaille que le titre et l'encadre, or tout slot de
         plusieurs lignes paie la justification. */
      + ((m && m.lines && m.lines.length > 1)
        ? '<p class="hint cf-type-bpx">' + justInfo(m) + '</p>' : '');
  }
  function syncInspMeas() {
    const box = HOST && HOST.querySelector(".cf-type-insp");
    const s = selSlot();
    if (!box || !s) return;
    const host = box.querySelector(".cf-type-meas");
    if (!host) return;
    /* LE MEME CONTENEUR PORTE DEUX RELEVES, ET IL FAUT LE BON. Le panneau d'un
       calque d'image reutilise `.cf-type-meas` (c'est le pied de la section
       « Boite », partagee) : y reecrire le releve TYPOGRAPHIQUE aurait ecrase
       « image 200 x 100 px » par « corps 10 pt » a la premiere mise en page.
       Le releve suit la nature du bloc, comme le panneau au-dessus de lui. */
    /* aucun champ n'est touche : ce conteneur ne porte que des mesures, jamais
       un input — la frappe en cours garde son focus. */
    host.innerHTML = isImage(s) ? imgMeasInner(s) : inspMeasInner(s);
  }
  /* ── LES TROIS BLOCS QUE LES DEUX NATURES PARTAGENT ─────────────────────
     Un bloc de texte et un calque d'image se règlent différemment SAUF sur
     trois points : leur nom, leur plaque de fond et leur boîte. Ces trois-là
     sont donc écrits UNE fois et appelés deux fois — la leçon du helper
     d'encre de la tâche 1, appliquée au panneau : trois littéraux recopiés,
     c'est trois occasions d'oublier le champ suivant d'un seul côté. */
  function inspHead(s) {
    const img = isImage(s);
    return '<div class="cf-type-ihead">'
      /* LA NATURE EST MONTREE, PAS BASCULEE — voir `addImgSlot`. Le panneau
         dit ce qu'on édite ; il ne transforme pas un bloc en un autre. */
      + '<em class="cf-type-kind' + (img ? " img" : "") + '" title="'
      + esc(img ? "Calque d'image. La nature d'un bloc se choisit à sa création : "
        + "pour passer au texte, créez un bloc de texte et supprimez celui-ci."
        : "Bloc de texte. La nature d'un bloc se choisit à sa création : pour "
        + "passer à l'image, créez un calque d'image et supprimez celui-ci.")
      + '">' + (img ? "&#128444;" : "T") + '</em>'
      + '<input type="text" class="cf-type-label" value="' + esc(s.label) + '" maxlength="40" title="Nom du slot">'
      + '<span class="counter mono cf-type-id">' + esc(s.id) + '</span>'
      + '</div>';
  }
  function inspPlaque(s) {
    return '<details class="grp cf-type-grp" open><summary>Plaque de fond</summary>'
      + '<div class="grp-body"><div class="cf-type-grid">'
      + '<label class="fld cf-type-f"><span class="lbl">Couleur plaque</span>'
      + '<input type="color" class="cf-type-pcol" value="'
      + esc(String(s.plate_color || "#1b1206").slice(0, 7))
      + '" title="Rectangle peint SOUS le contenu de ce slot, dans sa boîte."></label>'
      + nfield("plate_alpha", "Opacité plaque", s.plate_alpha, 0.05,
        "Opacité de la plaque, de 0 à 1. Elle se multiplie avec l'opacité du slot : "
        + "un slot à 50 % et une plaque à 0,8 posent 40 %.", 0, 1)
      + nfield("plate_radius", "Rayon (mm)", s.plate_radius, 0.25,
        "Rayon des coins de la plaque, en millimètres. Il est ramené à la moitié du "
        + "petit côté de la boîte au dessin : au-delà, un coin arrondi est un disque.",
        0, PLATE_RADIUS_MAX_MM)
      + '</div>'
      + '<div class="btn-row"><button class="btn sm cf-type-pnone" type="button"'
      + ' title="Retire la plaque : le contenu revient sur le fond des autres couches">Sans plaque</button></div>'
      + '<p class="hint">' + (s.plate_color
        ? 'plaque ' + esc(s.plate_color) + ' à ' + fx(s.plate_alpha * 100, 0) + ' %'
          + (s.plate_radius ? ', coins ' + fx(s.plate_radius, 2) + ' mm' : ', coins vifs')
        : 'aucune plaque — posez une couleur pour en créer une')
      + '</p></div></details>';
  }
  function inspBoite(s, mesures) {
    return '<details class="grp cf-type-grp" open><summary>Boîte — millimètres depuis le coin de coupe</summary>'
      + '<div class="grp-body"><div class="cf-type-grid">'
      + nfield("bx", "X (mm)", s.box[0], 0.25, "Depuis le coin de coupe")
      + nfield("by", "Y (mm)", s.box[1], 0.25, "Depuis le coin de coupe")
      + nfield("bw", "Largeur (mm)", s.box[2], 0.25, "Largeur de la boîte")
      + nfield("bh", "Hauteur (mm)", s.box[3], 0.25, "Hauteur de la boîte")
      + '</div>'
      + mesures
      + '<div class="btn-row"><button class="btn sm cf-type-dup" type="button" title="Ctrl+D">Dupliquer</button>'
      + '<button class="btn sm cf-type-center" type="button">Centrer</button>'
      + '<button class="btn sm cf-type-fill" type="button" title="Étendre à toute la largeur du cadre de composition">Pleine largeur</button>'
      + '</div></div></details>';
  }

  function renderInsp() {
    const box = HOST && HOST.querySelector(".cf-type-insp");
    if (!box) return;
    const s = selSlot();
    if (!s) { box.innerHTML = '<p class="empty-note sm">Sélectionnez un slot pour en régler la typographie.</p>'; return; }
    /* LE PANNEAU BASCULE SES SECTIONS SELON LA NATURE DU BLOC. Un calque
       d'image n'a ni police, ni corps, ni casse, ni césure : les afficher
       inertes aurait été onze réglages qui ne font rien — la faute qu'on
       reproche aux barres concurrentes. */
    if (isImage(s)) { renderInspImage(box, s); return; }
    box.innerHTML = ''
      + inspHead(s)
      + '<label class="fld cf-type-f"><span class="lbl">Texte par défaut<i class="cf-type-cc mono">'
      + Array.from(s.text).length + ' car.</i></span>'
      + '<textarea class="cf-type-text" rows="3" title="Utilisé tant que la colonne CSV du même nom est vide">'
      + esc(s.text) + '</textarea></label>'
      + '<div class="cf-type-grid">'
      /* LE NOM DE LA FAMILLE EST ECRIT DANS SA PROPRE FONTE, menu ferme. La
         spec demande un apercu du glyphe ; il n'existait que dans le menu
         deroulant, donc invisible sur une capture — « le champ POLICE n'affiche
         qu'un nom et un compteur ». Ecrit ainsi, le champ EST l'apercu, et il
         trahit tout de suite une famille qui n'a pas charge (elle s'affiche
         alors dans le repli). */
      + '<div class="fld cf-type-f cf-type-fontf"><span class="lbl">Police</span>'
      + '<button class="btn cf-type-font" type="button" title="' + FONTS.length
      + ' familles installées avec le logiciel · le nom est écrit dans sa propre fonte">'
      + '<span class="cf-type-fs" style="font-family:\'' + esc(familyOf(s.font)) + '\',sans-serif">'
      + esc(fontLabel(s.font)) + '</span><i>' + esc("." + ((FONT_BY_ID[s.font] || {}).ext || "ttf"))
      + ' · ' + FONTS.length + '</i></button></div>'
      + nfield("size_pt", "Corps (pt)", s.size_pt, 0.5, "Corps demandé, en points typographiques", 2, 400)
      + nfield("min_pt", "Mini (pt)", s.min_pt, 0.5,
        "Jusqu'où « Ajuster » a le droit de descendre pour faire tenir le texte dans "
        + "la boîte.", 2, 400)
      + nfield("read_pt", "Lisible dès (pt)", s.read_pt, 0.5,
        "Le corps sous lequel ce bloc ne se lit plus une fois la carte imprimée et tenue "
        + "à bout de bras. Repères d'usage : un titre tient à 12 à 20 pt, un encadré de "
        + "règles à 6 à 9, les crédits à 4 à 5. Le texte reste entier dans tous les cas : "
        + "le relevé écrit le corps composé et ce qu'il faudrait changer pour remonter. "
        + "0 = pas de contrôle.", 0, 400)
      + '<label class="fld cf-type-f"><span class="lbl">Couleur</span>'
      + '<input type="color" class="cf-type-col" value="' + esc(s.color.slice(0, 7)) + '"></label>'
      + nfield("track", "Interlettrage (%)", s.track, 0.5, "Approche, en % du cadratin", -30, 100)
      + nfield("leading", "Interligne", s.leading, 0.02, "Multiple du corps", 0.6, 3)
      + '</div>'
      /* ── LES REGLAGES DU DOMAINE, AU-DESSUS DE LA LIGNE DE FLOTTAISON ──────
         Alignement, vertical, casse, contour, ombre et arc existaient tous ;
         ils vivaient sous six lignes de champs numeriques et dans un groupe
         replie, c'est-a-dire nulle part pour qui ouvre le panneau. Ce qu'un
         typographe touche en premier passe donc devant, et les reglages de
         justification — qu'on regle une fois — passent derriere. Aucun champ
         n'a ete retire : ils ont change de rang. */
      + segf("Alignement", "align", [["left", "&#8676;"], ["center", "&#8596;"], ["right", "&#8677;"], ["justify", "&#9776;"]], s.align,
        ["à gauche", "centré", "à droite", "justifié — les blancs absorbent la largeur manquante"])
      + segf("Vertical", "valign", [["top", "&#8593;"], ["middle", "&#8597;"], ["bottom", "&#8595;"]], s.valign,
        ["en haut", "au milieu", "en bas"])
      + segf("Casse", "caps", [["none", "Aa"], ["upper", "AA"], ["lower", "aa"], ["title", "Ab Cd"]], s.caps,
        ["telle quelle", "capitales", "bas de casse", "capitales initiales"])
      + segf("Face", "side", [["front", "Recto"], ["back", "Verso"], ["both", "R+V"]], s.side,
        ["recto seul", "verso seul", "recto et verso"])
      + '<div class="cf-type-tog">'
      /* le libelle porte l'asterisque des que la famille n'a qu'un fichier :
         le bouton dit alors ce qu'il fait vraiment, avant qu'on clique. */
      + '<button class="chip cf-type-t' + (s.bold ? " active" : "") + '" data-k="bold" type="button" title="'
      + esc(facesOf(s.font) > 1 ? "Gras" : "Gras synthétique : « " + fontLabel(s.font)
        + " » n'a qu'un fichier (une graisse). Le navigateur épaissit le trait, il ne charge pas un gras dessiné.")
      + '"><b>G</b>' + (facesOf(s.font) > 1 ? "" : "<sup>*</sup>") + '</button>'
      + '<button class="chip cf-type-t' + (s.italic ? " active" : "") + '" data-k="italic" type="button" title="'
      + esc(facesOf(s.font) > 1 ? "Italique" : "Italique synthétique : « " + fontLabel(s.font)
        + " » n'a qu'un fichier (un style). Le navigateur penche le glyphe, il ne charge pas une italique dessinée.")
      + '"><i>I</i>' + (facesOf(s.font) > 1 ? "" : "<sup>*</sup>") + '</button>'
      + '<button class="chip cf-type-t' + (s.autofit ? " active" : "") + '" data-k="autofit" type="button" title="Réduit le corps, jusqu\'au mini, pour faire entrer le texte dans sa boîte">Ajuster</button>'
      + '<button class="chip cf-type-t' + (s.wrap ? " active" : "") + '" data-k="wrap" type="button" title="Retour à la ligne automatique">Retour ligne</button>'
      + '<button class="chip cf-type-t' + (s.hyphen ? " active" : "") + '" data-k="hyphen" type="button" title="Césure : coupe entre deux consonnes encadrées de voyelles, jamais dans un digramme, jamais à moins de 3 lettres d\'un bout. Le tiret conditionnel U+00AD que vous posez vous-même est toujours respecté.">Césure</button>'
      + '</div>'
      /* ── LA PLAQUE DE FOND, JUSTE AVANT LE CONTOUR ────────────────────────
         Elle se regle avec le meme geste que le contour et l'ombre — c'est le
         fond de ce bloc-la, pas un ornement de cadre — et elle se pose donc
         au meme endroit du panneau, avec les memes gabarits de champ. Un
         `input[type=color]` ne sait pas dire « rien » : le bouton « Sans
         plaque » est le SEUL chemin de retour, et sans lui une couleur posee
         par erreur ne se reprenait plus. Le bloc est partage avec le calque
         d'image (`inspPlaque`) : c'est le meme fond, sous un autre contenu. */
      + inspPlaque(s)
      + '<details class="grp cf-type-grp" open><summary>Contour, ombre, arc</summary>'
      + '<div class="grp-body cf-type-grid">'
      + nfield("outline", "Contour (pt)", s.outline, 0.1, "Épaisseur du contour", 0, 20)
      + '<label class="fld cf-type-f"><span class="lbl">Couleur contour</span>'
      + '<input type="color" class="cf-type-ocol" value="' + esc(s.outline_color.slice(0, 7)) + '"></label>'
      + nfield("shadow", "Ombre (pt)", s.shadow, 0.2, "Flou de l’ombre portée", 0, 40)
      + '<label class="fld cf-type-f"><span class="lbl">Couleur ombre</span>'
      + '<input type="color" class="cf-type-scol" value="' + esc(s.shadow_color.slice(0, 7)) + '"></label>'
      + nfield("shadow_dx", "Ombre X (pt)", s.shadow_dx, 0.2, "Décalage horizontal", -40, 40)
      + nfield("shadow_dy", "Ombre Y (pt)", s.shadow_dy, 0.2, "Décalage vertical", -40, 40)
      + nfield("rotate", "Rotation (°)", s.rotate, 1, "Rotation autour du centre de la boîte", -180, 180)
      + nfield("arc", "Arc (%)", s.arc, 2, "Texte sur arc : positif = bombé, négatif = creux", -100, 100)
      + '</div></details>'
      + '<details class="grp cf-type-grp"><summary>Opacité, justification</summary>'
      + '<div class="grp-body cf-type-grid">'
      + nfield("opacity", "Opacité (%)", s.opacity, 5, "Opacité du texte", 0, 100)
      + nfield("just_max", "Blancs max (%)", s.just_max, 1,
        "Élasticité maximale d'un blanc justifié, en % de l'espace naturel de la fonte. "
        + "Au-delà, le supplément passe dans l'interlettrage de la ligne au lieu de gonfler "
        + "encore ses blancs : une ligne lâche se voit, un dixième de pixel entre les lettres non. "
        + "133 % est la valeur du métier.", 100, 400)
      + nfield("last_pct", "Dern. ligne (%)", s.last_pct, 5,
        "Longueur minimale de la dernière ligne d'un paragraphe, en % de la justification. "
        + "En dessous, le dernier mot de la ligne précédente lui est descendu — jamais un mot "
        + "n'est coupé ni remonté. 0 désactive le contrôle.", 0, 80)
      + '</div></details>'
      + inspBoite(s, inspMeas(s));

    const id = s.id;
    wireInspCommun(box, id);
    const ta = box.querySelector(".cf-type-text");
    ta.addEventListener("input", () => {
      patchSlot(id, { text: ta.value }, true);
      const cc = box.querySelector(".cf-type-cc");
      if (cc) cc.textContent = Array.from(ta.value).length + " car.";
    });
    ta.addEventListener("focus", pushUndo);
    box.querySelector(".cf-type-font").addEventListener("click", (e) => openFontPicker(e.currentTarget, id));
    box.querySelector(".cf-type-col").addEventListener("input", (e) => patchSlot(id, { color: e.target.value }, true));
    box.querySelector(".cf-type-ocol").addEventListener("input", (e) => patchSlot(id, { outline_color: e.target.value }, true));
    box.querySelector(".cf-type-scol").addEventListener("input", (e) => patchSlot(id, { shadow_color: e.target.value }, true));
  }

  /* ── LE BRANCHEMENT QUE LES DEUX PANNEAUX PARTAGENT ─────────────────────
     Il est piloté par les ATTRIBUTS (`data-k`), pas par une liste de champs :
     ajouter un réglage au panneau d'image n'oblige donc à rien ici, et un
     champ retiré ne laisse pas un écouteur orphelin. Les trois blocs communs
     (nom, plaque, boîte) ont leur branchement ici, une fois. */
  function wireInspCommun(box, id) {
    box.querySelector(".cf-type-label").addEventListener("change", (e) => {
      patchSlot(id, { label: e.target.value }); renderAll();
    });
    box.querySelector(".cf-type-pcol").addEventListener("input", (e) => patchSlot(id, { plate_color: e.target.value }, true));
    box.querySelector(".cf-type-pnone").addEventListener("click", () => {
      patchSlot(id, { plate_color: null });
      renderAll();
    });
    const inputs = box.querySelectorAll('input[type="number"][data-k]');
    Array.prototype.forEach.call(inputs, (inp) => {
      const k = inp.dataset.k;
      const apply = () => {
        const v = Number(inp.value);
        if (!isFinite(v)) return;
        if (k === "bx" || k === "by" || k === "bw" || k === "bh") {
          const cur = slots().filter((x) => x.id === id)[0];
          if (!cur) return;
          const b = cur.box.slice();
          b[{ bx: 0, by: 1, bw: 2, bh: 3 }[k]] = v;
          patchSlot(id, { box: b });
        } else patchSlot(id, { [k]: v });
        renderAll();
      };
      inp.addEventListener("change", apply);
      inp.addEventListener("keydown", (e) => { if (e.key === "Enter") { apply(); e.preventDefault(); } });
    });
    box.querySelectorAll(".cf-type-seg").forEach((seg) => {
      seg.addEventListener("click", (e) => {
        const b = e.target.closest("button[data-v]");
        if (!b) return;
        patchSlot(id, { [seg.dataset.k]: b.dataset.v });
        renderAll();
      });
    });
    box.querySelectorAll(".cf-type-t").forEach((b) => {
      b.addEventListener("click", () => {
        const cur = slots().filter((x) => x.id === id)[0];
        patchSlot(id, { [b.dataset.k]: !cur[b.dataset.k] });
        renderAll();
      });
    });
    box.querySelector(".cf-type-dup").addEventListener("click", dupSlot);
    box.querySelector(".cf-type-center").addEventListener("click", () => {
      const sr = safeRectMm(CF.geom()), cur = slots().filter((x) => x.id === id)[0];
      patchSlot(id, { box: [sr[0] + (sr[2] - cur.box[2]) / 2, cur.box[1], cur.box[2], cur.box[3]] });
      renderAll();
    });
    box.querySelector(".cf-type-fill").addEventListener("click", () => {
      const sr = safeRectMm(CF.geom()), cur = slots().filter((x) => x.id === id)[0];
      patchSlot(id, { box: [sr[0], cur.box[1], sr[2], cur.box[3]] });
      renderAll();
    });
  }

  /* ═════════════════════════════════════════════════════════════════════════
     6bis. LE PANNEAU D'UN CALQUE D'IMAGE
     ═════════════════════════════════════════════════════════════════════════
     Les memes trois blocs communs (nom, plaque, boite) et, a la place des onze
     reglages typographiques, les deux qui font un calque : SON IMAGE et SON
     CADRAGE. Rien d'inerte n'est affiche — un champ « Interlettrage » sur un
     calque d'image serait un mensonge poli. */
  function imgMeasHtml(s) {
    /* le MEME conteneur que le panneau de texte (`.cf-type-meas`) : c'est le
       pied de la section « Boite », partagee, et `syncInspMeas` le reecrit
       apres chaque mise en page — avec le releve de la bonne nature. */
    return '<div class="cf-type-meas">' + imgMeasInner(s) + '</div>';
  }
  function imgMeasInner(s) {
    const g = CF.geom(), b = boxPx(s, g);
    const file = srcFile(s);
    const rec = file ? imgRec(file) : null;
    const sw = (rec && rec.ok) ? (rec.img.naturalWidth || rec.img.width) : 0;
    const sh = (rec && rec.ok) ? (rec.img.naturalHeight || rec.img.height) : 0;
    const r = (sw && sh) ? fitRect(sw, sh, b, s.fit) : null;
    return '<p class="hint mono cf-type-bpx">'
      + fx(b[2], 1) + ' x ' + fx(b[3], 1) + ' px de toile'
      + (sw ? ' · image ' + sw + ' x ' + sh + ' px' : '')
      /* LE CHIFFRE QUI DECIDE DE LA QUALITE D'IMPRESSION : combien de pixels
         de la source tombent dans un pixel de la toile. En dessous de 1, la
         toile agrandit — c'est le meme fait que la jauge de DPI de P1, dit
         ici avec les grandeurs de ce panneau. */
      + (r ? ' · posée ' + fx(r[2], 1) + ' x ' + fx(r[3], 1) + ' px, soit '
        + fx(sw / Math.max(1, r[2]), 2) + ' pixel(s) d\'image par pixel de toile'
        + (sw / Math.max(1, r[2]) < 0.999 ? ' — <b>la toile agrandit</b>' : '') : '')
      + (file && rec && !rec.ok ? ' · <b>' + esc(file) + ' introuvable</b>' : '')
      + ' · 1 mm = ' + fx(g.mm2px(1), 3) + ' px à ' + g.dpi + ' DPI</p>';
  }
  function renderInspImage(box, s) {
    const file = srcFile(s);
    const rec = file ? imgRec(file) : null;
    box.innerHTML = ''
      + inspHead(s)
      /* LA ZONE DE DEPOT — patron de P1 (mod-face) : cliquer, deposer ou
         coller, les trois chemins d'un import d'image dans ce lab. */
      + '<div class="cf-type-drop" title="Déposez une image, collez-la (Ctrl+V) ou cliquez pour en choisir une">'
      + '<input type="file" class="cf-type-file" accept="image/*" hidden>'
      + '<b>' + (file ? esc(file) : 'Aucune image') + '</b>'
      + '<span class="hint">' + (file
        ? 'Déposez-en une autre pour la remplacer.'
        : 'Déposez une image, collez-la ou cliquez ici.')
      + '</span></div>'
      + (file && rec && !rec.ok
        ? '<p class="hint cf-type-warn">' + esc(file) + ' n\'est pas dans ce jeu : '
          + 'l\'aperçu pose un damier à sa place. Déposez le fichier à nouveau.'
        + '</p>' : '')
      + segf("Cadrage", "fit", [["contain", "Entière"], ["cover", "Remplir"]], s.fit,
        ["l'image entière tient dans la boîte — des bandes vides restent sur le petit côté",
          "l'image remplit la boîte et ce qui dépasse est coupé"])
      + segf("Face", "side", [["front", "Recto"], ["back", "Verso"], ["both", "R+V"]], s.side,
        ["recto seul", "verso seul", "recto et verso"])
      + inspPlaque(s)
      + '<details class="grp cf-type-grp" open><summary>Rotation, opacité</summary>'
      + '<div class="grp-body cf-type-grid">'
      + nfield("rotate", "Rotation (°)", s.rotate, 1, "Rotation autour du centre de la boîte", -180, 180)
      + nfield("opacity", "Opacité (%)", s.opacity, 5, "Opacité du calque, plaque comprise", 0, 100)
      + '</div>'
      /* OU CE CALQUE SE PEINT, dit a l'ecran : la bande z=60 passe AU-DESSUS
         du cadre de base (40) et SOUS le decor haut (70). Sans cette phrase,
         « mon image passe derriere le cadre » devient un rapport de bogue. */
      + '<p class="hint">Ce calque se peint au-dessus du cadre de base et sous le décor haut, '
      + 'dans l\'ordre de la liste des blocs.</p>'
      + '</details>'
      + inspBoite(s, imgMeasHtml(s));

    const id = s.id;
    wireInspCommun(box, id);
    const drop = box.querySelector(".cf-type-drop");
    const file_in = box.querySelector(".cf-type-file");
    drop.addEventListener("click", (e) => { if (e.target !== file_in) file_in.click(); });
    file_in.addEventListener("change", async () => {
      const f = file_in.files && file_in.files[0];
      file_in.value = "";
      if (f) await importImage(f, id);
    });
    ["dragenter", "dragover"].forEach((n) => drop.addEventListener(n, (e) => {
      e.preventDefault(); drop.classList.add("over");
    }));
    ["dragleave", "drop"].forEach((n) => drop.addEventListener(n, () => drop.classList.remove("over")));
    drop.addEventListener("drop", async (e) => {
      e.preventDefault();
      const fs = (e.dataTransfer && e.dataTransfer.files) || [];
      if (fs.length) await importImage(fs[0], id);
    });
  }

  /* LE COLLAGE — au niveau du document, comme dans P1, et garde par le meme
     controle : le panneau doit etre ouvert ET un calque d'image selectionne.
     Sans ces deux gardes, un Ctrl+V destine a un champ de texte partait au
     backend en image. */
  function onPaste(e) {
    if (!panelOn()) return;
    const s = selSlot();
    if (!s || !isImage(s)) return;
    const items = (e.clipboardData && e.clipboardData.items) || [];
    let f = null;
    for (let i = 0; i < items.length && !f; i++) {
      if (items[i].kind === "file") {
        const g = items[i].getAsFile();
        if (g && /^image\//.test(g.type || "")) f = g;
      }
    }
    if (!f) return;
    e.preventDefault();
    importImage(f, s.id);
  }

  /* LA REDUCTION AVANT L'ENVOI — patron `downscale` de mod-face. Le serveur
     reduit de toute facon (il ne croit pas le client) ; ce qu'on evite ici est
     un fichier de 40 Mo qui part sur le fil pour revenir a 4096 px. */
  function downscaleImg(bmp, w, h) {
    const k = MAX_IMPORT_PX / Math.max(w, h);
    const nw = Math.max(1, Math.round(w * k)), nh = Math.max(1, Math.round(h * k));
    const cv = document.createElement("canvas");
    cv.width = nw; cv.height = nh;
    const c = cv.getContext("2d");
    c.imageSmoothingEnabled = true;
    try { c.imageSmoothingQuality = "high"; } catch (e) { /* moteur ancien */ }
    c.drawImage(bmp, 0, 0, nw, nh);
    return new Promise((res) => cv.toBlob((b) => res(b), "image/png"));
  }
  async function importImage(f, id) {
    if (!f || !/^image\//.test(f.type || "")) {
      M.toast("ce fichier n'est pas une image", true);
      return;
    }
    let body = f;
    M.busy(true, "import de l'image…");
    try {
      /* `createImageBitmap` et non une URL d'objet : la pièce n'a pas le droit
         de fabriquer d'URL de blob (elle n'a aucun chemin de livraison), et le
         décodage direct s'en passe. */
      let bmp = null;
      try { bmp = await createImageBitmap(f); }
      catch (e) { M.toast("image illisible : " + f.name, true); return; }
      if (Math.max(bmp.width, bmp.height) > MAX_IMPORT_PX) {
        body = await downscaleImg(bmp, bmp.width, bmp.height);
      }
      if (bmp.close) bmp.close();
      const resp = await M.api.raw("POST", "image", body);
      if (resp.status === 404) { M.toast("import impossible : le service de cartes n'est pas joignable", true); return; }
      const d = await resp.json().catch(() => null);
      if (!resp.ok) throw new Error((d && d.detail) || (resp.status + " " + resp.statusText));
      /* ON RELIT L'IMAGE SERVIE, pas le fichier local : c'est elle que le
         painter dessinera (bornée, ré-encodée). Une divergence entre les deux
         serait invisible et partirait à l'impression. */
      IMGS.delete(d.file);
      await loadImg(d.file);
      patchSlot(id, { src: d.src });
      renderAll();
      M.invalidate();
      M.toast("image importée — " + d.px[0] + " x " + d.px[1] + " px ("
        + d.n + " / " + d.max + ")");
    } catch (e) {
      M.toast(String((e && e.message) || e), true);
    } finally { M.busy(false); }
  }

  /* ── selecteur de police : les 23 familles, chacune dans SA fonte ──────── */
  let fp = null;
  function openFontPicker(anchor, slotId) {
    closeFontPicker();
    fp = document.createElement("div");
    fp.className = "cf-type cf-type-fp";
    const groups = {};
    FONTS.forEach((f) => { (groups[f.kind] = groups[f.kind] || []).push(f); });
    fp.innerHTML = '<div class="cf-type-fph">'
      + '<input type="text" class="search sm cf-type-fq" placeholder="Filtrer ' + FONTS.length + ' polices…">'
      + '<span class="counter mono cf-type-fn">' + FONTS.length + '</span></div>'
      + '<div class="cf-type-fpl">'
      + Object.keys(groups).map((k) => '<div class="cf-type-fg">' + esc(KIND_LABELS[k] || k) + '</div>'
        + groups[k].map((f) => {
          /* LE SPECIMEN PORTE DES ACCENTS. « Agyfj 42 » ne montrait que des
             lettres que toutes les polices ont : une famille sans « é » avait
             exactement la meme vignette qu'une famille complete. Le specimen
             pose donc les signes qui separent, et le compte de manquants —
             lu dans le fichier — est ecrit a cote. */
          const miss = Array.isArray(f.fr_missing) ? f.fr_missing : null;
          return '<button class="cf-type-fi' + (miss && miss.length ? " part" : "")
            + '" type="button" data-f="' + esc(f.id) + '" data-l="'
            + esc(f.label.toLowerCase()) + '" title="'
            + esc(miss == null ? "couverture non mesurée (catalogue hors ligne)"
              : (miss.length ? miss.length + " des " + FR_PROBE.length
                + " signes du français manquent dans " + f.file + " : " + miss.join(" ")
                : "les " + FR_PROBE.length + " signes du français sont dans " + f.file))
            + '">'
            + '<span class="cf-type-fsample" style="font-family:\'' + esc(f.family) + '\',sans-serif">' + esc(FP_SAMPLE) + '</span>'
            + '<span class="cf-type-flab">' + esc(f.label) + '<i class="mono">.' + esc(f.ext)
            + (miss && miss.length ? ' · &#9888; ' + miss.length : "") + '</i></span>'
            + '</button>';
        }).join("")).join("")
      + '</div>';
    document.body.appendChild(fp);
    const r = anchor.getBoundingClientRect();
    fp.style.left = Math.max(8, Math.min(window.innerWidth - 336, r.left)) + "px";
    fp.style.top = Math.min(window.innerHeight - 380, r.bottom + 6) + "px";
    ensureFonts(FONTS.map((f) => f.id));
    const q = fp.querySelector(".cf-type-fq");
    const items = () => Array.prototype.slice.call(fp.querySelectorAll(".cf-type-fi:not(.hidden)"));
    q.addEventListener("input", () => {
      const v = q.value.trim().toLowerCase();
      let n = 0;
      fp.querySelectorAll(".cf-type-fi").forEach((b) => {
        const ok = !v || b.dataset.l.indexOf(v) >= 0 || b.dataset.f.toLowerCase().indexOf(v) >= 0;
        b.classList.toggle("hidden", !ok);
        if (ok) n++;
      });
      fp.querySelector(".cf-type-fn").textContent = n;
    });
    let cur = -1;
    q.addEventListener("keydown", (e) => {
      const its = items();
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        cur = clamp(cur + (e.key === "ArrowDown" ? 1 : -1), 0, its.length - 1);
        its.forEach((b, i) => b.classList.toggle("on", i === cur));
        if (its[cur]) its[cur].scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter" && its[cur]) {
        pick(its[cur].dataset.f);
      } else if (e.key === "Escape") closeFontPicker();
    });
    function pick(fid) {
      patchSlot(slotId, { font: fid });
      loadFont(fid).then(() => M.invalidate());
      mpatch({ font_default: fid });
      closeFontPicker();
      renderAll();
    }
    fp.querySelectorAll(".cf-type-fi").forEach((b) => b.addEventListener("click", () => pick(b.dataset.f)));
    setTimeout(() => q.focus(), 0);
    setTimeout(() => document.addEventListener("pointerdown", outside, true), 0);
    function outside(e) { if (fp && !fp.contains(e.target)) closeFontPicker(); }
    fp._outside = outside;
  }
  function closeFontPicker() {
    if (!fp) return;
    document.removeEventListener("pointerdown", fp._outside, true);
    fp.remove();
    fp = null;
  }

  /* ── gabarits ──────────────────────────────────────────────────────────── */
  function openPresets(e) {
    closeFontPicker();
    const menu = document.createElement("div");
    menu.className = "cf-type cf-type-menu";
    menu.innerHTML = Object.keys(PRESETS).map((p) => '<button class="cf-type-mi" type="button" data-p="' + p + '">'
      + '<b>' + esc(PRESETS[p].label) + '</b><span>' + esc(PRESETS[p].hint) + '</span>'
      + '<i class="mono">' + PRESETS[p].slots.length + ' slots</i></button>').join("");
    document.body.appendChild(menu);
    const r = e.currentTarget.getBoundingClientRect();
    menu.style.left = Math.max(8, Math.min(window.innerWidth - 400, r.left)) + "px";
    menu.style.top = (r.bottom + 6) + "px";
    menu.querySelectorAll(".cf-type-mi").forEach((b) => b.addEventListener("click", () => {
      applyPreset(b.dataset.p);
      menu.remove();
    }));
    const off = (ev) => {
      if (!menu.contains(ev.target)) { menu.remove(); document.removeEventListener("pointerdown", off, true); }
    };
    setTimeout(() => document.addEventListener("pointerdown", off, true), 0);
  }

  /* ═════════════════════════════════════════════════════════════════════════
     7. LE RELEVE — les chiffres qui ont dessine le fichier
     ═════════════════════════════════════════════════════════════════════════ */
  /* LE PAINTER PEUT RENDRE AVANT init(host). Le CORE compose la carte des
     qu'un module s'enregistre ; `init` n'arrive qu'au premier affichage du
     panneau. Le painter demandait pourtant un releve 30 ms plus tard, et
     `renderList` allait chercher HOST.querySelector sur un HOST encore nul :
     une exception rouge en console a CHAQUE ouverture de l'onglet (3
     rechargements sur 3). Le releve n'a de sens que s'il a un panneau ou
     s'ecrire — sans panneau, on ne fait rien, et `init` rattrape en appelant
     renderAll(). Les deux rendus sont gardes a leur tour : la cause est ici,
     le garde-fou est chez eux. */
  function scheduleReport() {
    clearTimeout(reportTimer);
    reportTimer = setTimeout(() => {
      if (!HOST) return;
      checkPending();
      renderList(); syncInspMeas(); renderProof(); paintOverlay();
      scheduleApiCheck(); scheduleAudit(); scheduleFixes(); scheduleDefCheck();
    }, 30);
  }
  /* Une seule ecriture pour une seule grandeur : le corps s'affiche PARTOUT
     « 9,1 pt (37,9 px) », jamais 38 ici et 37,9 la-bas. */
  /* LES DEUX NOMBRES DOIVENT SE RETROUVER L'UN L'AUTRE. Le corps etait arrondi
     au dixieme de point et les pixels pris sur le corps EXACT : cela donnait
     « 9,2 pt (38,1 px) », et qui refait 9,2 / 72 x 300 trouve 38,3 — un ecart
     d'un dixieme suffit pour conclure que le panneau ment (c'est exactement ce
     qui etait arrive au rapport de contraste, corrige de la meme facon). Les
     pixels sont donc calcules SUR LE CHIFFRE AFFICHE. L'ecart avec le corps
     reellement compose reste sous le demi-pixel : l'arrondi ne depasse pas
     0,05 pt, soit 0,21 px a 300 DPI. */
  function corps(m, g) {
    const pt = Math.round(m.pt * 10) / 10;
    return fx(pt, 1) + " pt (" + fx(pxOfPt(pt, g || CF.geom()), 1) + " px)";
  }
  /* CE QUE COUTE LA JUSTIFICATION, en clair. « Fins de ligne a 0 %
     d'irregularite » est vrai et ne dit rien : c'est le bord ou une
     justification est bonne PAR CONSTRUCTION. Le prix, lui, se lit sur les
     blancs — et sur la derniere ligne. Les trois chiffres viennent de la mise
     en page qui a dessine le fichier, pas d'une seconde estimation. */
  function justInfo(m) {
    /* LE ZERO DU MODELE ET L'ECART DE L'ENCRE, COTE A COTE. Le premier est
       vrai par construction (une ligne justifiee occupe exactement la
       justification) ; le second est ce qu'un critique trouve en remesurant le
       bitmap, parce que l'approche droite du dernier glyphe change d'une ligne
       a l'autre. Publier le seul zero, c'etait promettre un chiffre que le
       fichier ne rend pas. */
    const out = ["fins de ligne " + fx(m.ragged * 100, 0) + " % d'irrégularité au tracé (bord droit)"
      + (m.edge_ink
        ? " · <b>" + m.edge_ink.spread + " px</b> d'écart d'encre relus sur le fichier ("
          + fx(m.edge_ink.pct, 1) + " %, " + m.edge_ink.n + " lignes, bords "
          + m.edge_ink.right[0] + " à " + m.edge_ink.right[1] + " px"
          /* LES DEUX SEUILS, PARCE QU'IL Y A DEUX FACONS DE REMESURER. Celui
             qui masque la couleur d'encre ne voit pas le liseré et trouve des
             bords decales d'un pixel : ce nombre-la est publie aussi, sinon
             son re-mesurage contredit le panneau et le panneau a tort. */
          + (m.edge_ink.right_core
            ? " ; corps plein seul " + m.edge_ink.right_core[0] + " à "
              + m.edge_ink.right_core[1] + " px, écart " + m.edge_ink.spread_core + " px"
            : "") + ")"
        : "")];
    if (m.ws_lo != null && m.ws_hi != null) {
      out.push("blancs-mots " + fx(m.ws_lo, 1) + " → " + fx(m.ws_hi, 1) + " px d'avance, étirement max "
        + fx(m.ws_stretch, 2) + " × le naturel (" + fx(m.natWs, 1) + " px, plafond "
        + fx(m.just_max / 100, 2) + " ×)"
        + (m.ws_capped ? " · " + m.ws_capped + " ligne(s) rattrapée(s) par l'interlettrage" : "")
        /* LES DEUX CONVENTIONS COTE A COTE. Sans la seconde, quiconque
           remesure le bitmap trouve un autre nombre et conclut au mensonge. */
        + (m.ws_ink ? " · " + m.ws_ink.lo + " → " + m.ws_ink.hi
          + " px mesurés d'encre à encre sur le fichier (" + m.ws_ink.n + " blancs"
          + (m.ws_ink.lo_core != null ? " ; corps plein seul " + m.ws_ink.lo_core
            + " → " + m.ws_ink.hi_core + " px" : "") + ")" : ""));
    }
    if (m.last_pct != null) {
      out.push((m.last_short ? "<b>dernière ligne " : "dernière ligne ") + fx(m.last_pct, 0)
        + " % de la justification" + (m.last_short ? "</b>" : "")
        + (m.last_min > 0 ? " (mini " + fx(m.last_min, 0) + " %)" : " — contrôle désactivé"));
    }
    return out.join(" · ");
  }
  /* LA DIVISION QUI DONNE LE CHIFFRE, ecrite telle qu'on la refait a la main.
     Sans elle, « contraste 4,18:1 » se recalcule a 3,61 sur les deux couleurs
     evidentes, et le panneau passe pour menteur alors qu'il a simplement
     mesure le chemin par le contour. */
  function contrastCalc(r) {
    if (!r || r.lum_a == null || r.lum_b == null) return "";
    const hi = Math.max(r.lum_a, r.lum_b), lo = Math.min(r.lum_a, r.lum_b);
    return "(" + fx(hi, 4) + " + 0,05) / (" + fx(lo, 4) + " + 0,05)"
      + (r.via === "contour" ? " — c'est le contour qui fait le relais" : "");
  }
  /* ── OU CE CHIFFRE A ETE PRIS ─────────────────────────────────────────────
     Deux luminances publiees laissent encore chercher OU les lire : sur un fond
     en degrade, celui qui echantillonne ailleurs trouve un autre nombre et
     conclut que le panneau ment (le second critique a annonce 5,50:1 la ou nous
     annoncions 4,29:1 — deux mesures justes, deux endroits differents). On
     nomme donc LE PIXEL, en coordonnees du fichier livre, origine en haut a
     gauche, fond perdu compris. Une pipette posee la retombe sur la valeur. */
  const ptTxt = (p) => (p ? "(" + p[0] + ", " + p[1] + ")" : "");
  function contrastWhere(r) {
    if (!r || r.lum_a == null) return "";
    /* CHAQUE TERME EST NOMME. Le rapport publie n'oppose pas toujours l'encre au
       fond : quand le contour fait le relais, c'est CONTOUR contre fond. Donner
       les pixels sans dire lequel porte quoi aurait remplace une ambiguite par
       une autre. */
    const enc = "encre" + (r.ink_pt ? " au pixel " + ptTxt(r.ink_pt) : "");
    const fnd = "fond" + (r.bg_pt ? " au pixel " + ptTxt(r.bg_pt) : "");
    const con = "contour " + (r.out_hex || "") + " (couleur déclarée)";
    const m = { ink_bg: [enc, fnd], outline_bg: [con, fnd], ink_outline: [enc, con] }[r.pair]
      || [enc, fnd];
    const hi = Math.max(r.lum_a, r.lum_b), lo = Math.min(r.lum_a, r.lum_b);
    const first = r.lum_a >= r.lum_b ? 0 : 1;
    return "relevé sur le fichier : " + fx(hi, 4) + " = " + m[first] + " · "
      + fx(lo, 4) + " = " + m[1 - first];
  }
  function auditOf(id) {
    if (!AUDIT || AUDIT.stamp !== AUDIT_STAMP) return null;
    return AUDIT.rows.filter((r) => r.id === id)[0] || null;
  }
  function renderProof() {
    const el = HOST && HOST.querySelector(".cf-type-proof");
    if (!el) return;                   /* le garde vient AVANT le dereferencement */
    const g = CF.geom(), sr = safeRectPx(g), a = slots();
    const rows = [];
    let over = 0, outSafe = 0, shrunk = 0, empty = 0;
    a.forEach((s) => {
      const m = MEAS[s.id];
      if (!m) return;
      const o = outsideBy(m.ink, sr);
      const bad = anyOut(o) && !m.empty;
      if (m.empty) { empty++; rows.push({ s: s, m: m, o: o, bad: false }); return; }
      if (m.over) over++;
      if (bad) outSafe++;
      if (m.shrunk) shrunk++;
      rows.push({ s: s, m: m, o: o, bad: bad });
    });
    const hero = rows.filter((r) => r.s.id === "title")[0] || rows[0];
    const rules = rows.filter((r) => r.s.id === "rules")[0];
    let html = '<div class="cf-type-pr">';
    if (!rows.length && a.length) {
      /* les chiffres viennent du painter : tant qu'il n'a pas rendu la main,
         on le DIT au lieu d'afficher des zeros qui ressembleraient a un
         verdict. */
      html += '<div class="cf-type-prow"><i>&#8987;</i><b>Mesure</b>'
        + '<span>rendu en cours — les chiffres ci-dessous sont ceux du dernier rendu de la toile.</span></div>';
    } else if (MEAS_SIDE !== LAST_SIDE) {
      /* le releve decrit une face, le dernier rendu en concernait une autre :
         on NOMME la face plutot que de laisser croire que les chiffres
         viennent de la passe qu'on vient de voir passer. */
      html += '<div class="cf-type-prow"><i>&#9432;</i><b>Face</b><span>relevé du <b>'
        + (MEAS_SIDE === "front" ? "recto" : "verso") + '</b> — le dernier rendu portait sur le '
        + (LAST_SIDE === "front" ? "recto" : "verso") + ', qui ne porte aucun slot de texte.</span></div>';
    }
    if (hero) {
      html += line(
        esc(hero.s.label),
        hero.m.empty ? "<b>aucun texte</b> — le bloc est réglé mais ne pose aucun glyphe"
          /* CE QUE LE BLOC EST DEVENU, EN CHIFFRES ET SANS VERDICT. « rétréci
             pour tenir » disait la manoeuvre sans dire son prix ; « 14 → 8,2 pt »
             dit les deux, et se relit sur le fichier. « 44 des 44 signes »
             remplace un compteur a zero par les deux nombres qui le produisent :
             qui recompte le texte et l'image retombe dessus. */
          : (hero.m.chars + " car. en " + hero.m.lines.length + " ligne" + (hero.m.lines.length > 1 ? "s" : "")
            + " · corps " + corps(hero.m, g)
            + (hero.m.shrunk ? ", demandé " + fx(hero.s.size_pt, 1) + " pt" : "")
            + (hero.m.over ? " · corps mini " + fx(hero.s.min_pt, 1) + " pt atteint" : "")
            + (hero.m.under_read ? " · <b>plus petit que les " + fx(hero.m.read_pt, 1)
              + " pt réglés pour ce bloc</b>" : "")
            + " · " + hero.m.posed + " des " + hero.m.srcn + " signes composés (blancs exclus)"
            + " · " + clearTxt(hero.m.ink, g, hero.bad)),
        /* le fichier d'abord : rien de perdu, rien qui sorte. Le plancher de
           lisibilite ne descend la ligne qu'en ambre — c'est un defaut de
           lecture, pas de fabrication. */
        (hero.m.empty || hero.m.over || hero.m.cut !== 0 || hero.bad) ? false
          : (hero.m.under_read ? "warn" : true));
    }
    if (rules) {
      const ar = auditOf(rules.s.id);
      /* le pavé affiché est celui MESURÉ SUR LES OCTETS quand le contrôle
         photométrique a tourné ; l'estimation ne s'affiche que tant qu'il n'a
         pas encore rendu la main, et elle se dit estimation. */
      /* DEUX BORNES, PAS UNE. Le tour precedent a vu ce pave annonce a
         645 x 188 px et remesure a 647 x 193 : l'ecart n'etait pas un
         mensonge, c'etait un seuil non dit. Le panneau publie desormais les
         deux — l'encre totale (liseré d'anticrenelage compris) et le corps
         plein seul — pour qu'un re-mesurage retombe sur un chiffre AFFICHE
         quel que soit le masque qu'il applique au PNG. */
      const pave = ar && ar.ink_px
        ? (ar.clipped ? "au moins " : "") + ar.ink_px[2] + " x " + ar.ink_px[3]
          + " px d'encre totale (α &gt; 0)"
          + (ar.ink_core_px ? ", " + ar.ink_core_px[2] + " x " + ar.ink_core_px[3]
            + " px de corps plein (α ≥ 250)" : "")
          + " — relus sur le PNG"
        : fx(rules.m.ink[2], 0) + " x " + fx(rules.m.ink[3], 0)
          + " px (estimé — le contrôle photométrique n'a pas encore relu le fichier)";
      html += line("Encadré de règles",
        rules.m.chars + " car. · pavé " + pave
        + " · cadre de composition " + sr[2] + " x " + sr[3] + " px · "
        /* PAS DE PROMESSE UNIVERSELLE. « toute re-mesure tombe entre ces deux
           bornes » etait une affirmation sur TOUS les masques possibles, alors
           que l'essai porte sur une plage de tolerances donnee (elle est ecrite
           dans les conventions de mesure, avec ses chiffres). Restent les deux
           bornes et le seuil d'opacite de chacune : verifiables, elles. */
        + clearTxt(rules.m.ink, g, rules.bad)
        + " · " + justInfo(rules.m),
        !rules.bad && !rules.m.last_short);
    }
    /* le plus petit corps REELLEMENT pose : c'est lui qui decide si la carte
       se lit une fois imprimee, et l'ajustement automatique peut l'avoir
       descendu tres bas sans que la liste le resume. */
    const pts = rows.filter((r) => !r.m.empty).map((r) => r.m.pt);
    const ptMin = pts.length ? Math.min.apply(null, pts) : null;
    const creuses = rows.filter((r) => !r.m.empty && r.m.last_short).length;
    const sous = rows.filter((r) => !r.m.empty && r.s.on && r.m.under_read);
    /* LE COMPTE DE POLICES EST CELUI QU'ON A MESURE, pas celui du catalogue :
       « 23 polices locales » etait une affirmation, « 23 servies · 5 chargées
       et distinctes du repli (mesuré) » est un releve. */
    const fp = fontProof();
    /* LE BLOC LE PLUS PRES DE LA LAME, NOMME ET CHIFFRE. Un compteur « 0 hors
       zone sure » ne dit pas s'il restait un dixieme de millimetre ou six ;
       celui-ci donne la distance et le bloc qui la porte, et c'est le meme
       nombre qu'une regle posee sur l'epreuve. */
    let pres = null;
    rows.forEach((r) => {
      if (r.m.empty) return;
      const c = trimClearMm(r.m.ink, g);
      if (!pres || c < pres.c) pres = { c: c, label: r.s.label };
    });
    html += line("Mise en page",
      a.length + " blocs de texte · " + fp.dist + " police(s) posée(s) sur les "
      + fp.served + " du catalogue, chasse mesurée"
      + (fp.ko ? " · <b>" + fp.ko + " fichier(s) de police illisible(s)</b>" : "")
      + (shrunk ? " · " + shrunk + " au corps réduit" : "")
      + (ptMin != null ? " · corps le plus petit " + fx(ptMin, 1) + " pt" : "")
      + (pres ? " · encre la plus proche de la coupe " + fx(pres.c, 2) + " mm (« "
        + esc(pres.label) + " »)" : "")
      + (over ? " · <b>" + over + " bloc(s) débordent de leur cadre</b>" : "")
      + (outSafe ? " · <b>" + outSafe + " bloc(s) entament la marge du format</b>" : "")
      + (creuses ? " · <b>" + creuses + " ligne(s) creuse(s)</b>" : "")
      + (empty ? " · <b>" + empty + " sans glyphe</b>" : "")
      + (apiVerdict ? " · " + esc(apiVerdict) : ""),
      over === 0 && outSafe === 0 && empty === 0 && creuses === 0 && fp.ko === 0);
    /* ── LES SIGNES QUE LA POLICE N'A PAS ─────────────────────────────────
       Sa propre ligne, parce que c'est un troisieme genre de defaut : le
       fichier est juste, le bloc est lisible, et un caractere sur deux cents
       n'est pas de la police annoncee. Personne ne le voit sans qu'on le
       dise — c'est la troncature muette, jouee sur un seul signe. */
    const frc = frCount();
    if (frc.unk < frc.n) {
      const cardT = CF.card(CF.current());
      const tofus = rows.filter((r) => !r.m.empty && r.s.on)
        .map((r) => ({ r: r, t: tofuOf(r.s, textOf(r.s, cardT)) }))
        .filter((x) => x.t.length);
      html += line("Signes hors police",
        (tofus.length
          ? "<b>" + tofus.length + " bloc(s) demandent des signes que leur police n'a pas</b> : "
            + tofus.map((x) => esc(x.r.s.label) + " → " + esc(x.t.join(" ")) + " (« "
              + esc(fontLabel(x.r.s.font)) + " »)").join(" · ")
            + " — le navigateur va les chercher dans une autre police, sans un mot, "
            + "et c'est cette autre police qui part à l'impression."
          : "aucun : les " + rows.filter((r) => r.s.on).length
            + " bloc(s) visibles n'emploient que des signes présents dans leur propre fichier de police")
        + " · " + frc.ok + " des " + frc.n + " familles du catalogue portent les "
        + FR_PROBE.length + " signes du français"
        + (frc.bad ? ", " + frc.bad + " ne les portent pas" : "")
        + (frc.unk ? ", " + frc.unk + " non mesurée(s)" : "")
        + " — lu dans la table cmap de chaque fichier",
        tofus.length ? false : true);
    }
    /* ── LE PLANCHER DE LISIBILITE, SUR SA PROPRE LIGNE ────────────────────
       Sortir de la zone sure est un defaut de FABRICATION : la coupe emporte
       l'encre. Composer sous le plancher est un defaut de LECTURE : le
       fichier est juste, la carte ne se lira pas. Les fondre dans un seul
       voyant aurait rendu l'un des deux invisible — et c'est precisement le
       reproche fait au badge « ajuste », qui certifiait l'encombrement en se
       taisant sur la lecture. */
    const avecPlancher = rows.filter((r) => !r.m.empty && r.m.read_pt > 0);
    if (avecPlancher.length) {
      html += line("Corps à l'impression",
        sous.length
          ? "<b>" + sous.length + " bloc(s) composé(s) plus petit que réglé</b> : "
            + sous.map((r) => esc(r.s.label) + " " + fx(r.m.pt, 1) + " pt pour "
              + fx(r.m.read_pt, 1) + " pt demandés").join(" · ")
            + " — le texte est entier et dans sa boîte, mais la carte se lira mal à "
            + "taille réelle. Ce qu'il faut changer, et de combien, est mesuré ci-dessous."
          : avecPlancher.length + " bloc(s) portent un corps de lecture réglé, tous "
            + "composés au-dessus (le plus juste : " + esc(serre(avecPlancher).s.label)
            + " à " + fx(serre(avecPlancher).m.pt, 1) + " pt pour "
            + fx(serre(avecPlancher).m.read_pt, 1) + " pt demandés)",
        sous.length ? "warn" : true);
    }
    /* LE REMEDE SE LIT AVEC LE DEFAUT QU'IL REPARE. Pose en fin de releve, il
       tombait sous la ligne de flottaison du panneau : le seul bloc actionnable
       de l'ecran etait celui qu'il fallait aller chercher. Il se glisse donc
       entre le constat (plancher de lisibilite) et le controle photometrique,
       qui est long et n'appelle, lui, aucune action. */
    html += '</div>' + fixBlock() + '<div class="cf-type-pr">';
    html += auditLine();
    html += defLine();
    if (SERIES) {
      const e = SERIES.per[(hero && hero.s.id) || ""] || null;
      html += line("Série",
        SERIES.n + (SERIES.n > 1 ? " cartes · " : " carte · ")
        + (e && e.n ? esc(e.label) + " de " + fx(e.lo, 1) + " à " + fx(e.hi, 1) + " pt · "
          + e.min + " au corps mini · " : "")
        /* LES DEUX COMPTES PLUTOT QUE LEUR DIFFERENCE : « 0 caractere supprime »
           demandait qu'on croie un zero, « 9 600 signes demandés, 9 600 posés »
           se recompte sur la colonne du tableur et sur les cartes. */
        + SERIES.srcn.toLocaleString("fr-FR") + " signes demandés, "
        + SERIES.posed.toLocaleString("fr-FR") + " posés"
        + (SERIES.over ? " · <b>" + SERIES.over + " bloc(s) débordent</b>" : "")
        + (SERIES.under ? " · <b>" + SERIES.under + " bloc(s) plus petits que réglé</b>" : "")
        + (SERIES.empty ? " · " + SERIES.empty + " champ vide" : ""),
        SERIES.cut === 0 && SERIES.over === 0 && SERIES.empty === 0 && !SERIES.under);
    }
    html += '</div>';
    if (over) {
      html += '<p class="cf-type-warn">' + over + ' bloc(s) débordent de leur cadre. Le texte '
        + 'reste entier dans le fichier : agrandissez la boîte, baissez le corps mini '
        + 'ou activez « Ajuster ».</p>';
    }
    html += auditDetail();
    html += defDetail();
    html += methodNote();
    html += '<p class="hint cf-type-tools">'
      + '<button class="cf-type-lnk cf-type-recheck" type="button">Recontrôler la lisibilité</button> · '
      + '<button class="cf-type-lnk cf-type-series" type="button">Contrôler toute la série</button>'
      + (fp.dist < fp.served
        ? ' · <button class="cf-type-lnk cf-type-provef" type="button" title="Charge les '
          + fp.served + ' fichiers et vérifie, pour chacun, que la chasse posée diffère de '
          + 'celle du repli du système — une police qui n\'arrive pas se voit alors tout de suite.">'
          + 'Vérifier les ' + fp.served + ' polices</button>'
        : "")
      + '</p>';
    el.innerHTML = html;
    const bs = el.querySelector(".cf-type-series");
    if (bs) {
      bs.addEventListener("click", () => {
        /* la remise en page de 200 cartes prend quelques secondes et elle est
           synchrone : sans ce report d'une frame, le voyant d'attente n'aurait
           pas le temps de s'afficher et l'ecran passerait pour fige. */
        M.busy(true, "mise en page de la série…");
        setTimeout(() => {
          try { runSeries(); } finally { M.busy(false); }
          renderProof();
        }, 40);
      });
    }
    const br = el.querySelector(".cf-type-recheck");
    if (br) br.addEventListener("click", () => { runAudit().catch(() => { }); });
    el.querySelectorAll(".cf-type-defc").forEach((b) => {
      /* le clic efface la marque d'echec : sinon un tirage rate une fois
         n'aurait plus jamais ete retente, meme a la demande. */
      b.addEventListener("click", () => { defcTried = ""; runDefCheck().catch(() => { }); });
    });
    const bf = el.querySelector(".cf-type-provef");
    if (bf) bf.addEventListener("click", () => { proveFonts().catch(() => { }); });
    /* les boutons de remede : ils appliquent le reglage MESURE, puis le
       panneau verifie ce que la mise en page suivante a reellement compose. */
    el.querySelectorAll(".cf-type-fixb").forEach((b) => {
      b.addEventListener("click", () => {
        const row = (FIXES && FIXES.rows.filter((r) => r.id === b.dataset.id)[0]) || null;
        const lv = row && row.levers.filter((l) => l.k === b.dataset.k)[0];
        if (!row || !lv || !lv.patch) return;
        PENDING = { id: row.id, label: row.label, target: row.target, stamp: AUDIT_STAMP };
        patchSlot(row.id, lv.patch);
        FIXES_KEY = "";
        renderAll();
      });
    });
    /* le bouton unique : meme chemin, meme remesure — il choisit seulement la
       sortie a la place de l'utilisateur. */
    el.querySelectorAll(".cf-type-fixgo").forEach((b) => {
      b.addEventListener("click", () => {
        const row = (FIXES && FIXES.rows.filter((r) => r.id === b.dataset.id)[0]) || null;
        const a = row && autoLever(row);
        if (!a) return;
        PENDING = { id: row.id, label: row.label, target: row.target, stamp: AUDIT_STAMP };
        patchSlot(row.id, a.patch);
        FIXES_KEY = "";
        renderAll();
      });
    });
    /* TROIS ETATS, LE MEME LANGAGE QUE LES BADGES. `true` = rien a signaler ;
       `false` = de l'encre part hors du cadre ou hors de la zone sure, ou un
       caractere manque : le fichier est fautif. `"warn"` = le fichier est
       juste et le bloc ne se lira pas. Un seul rouge pour les deux aurait
       remis dans le meme sac ce que cette passe vient justement de separer. */
    function line(k, v, ok) {
      const cls = ok === true ? "" : (ok === "warn" ? " warn" : " bad");
      const ic = ok === true ? "&#10003;" : "&#9888;";
      return '<div class="cf-type-prow' + cls + '"><i>' + ic
        + '</i><b>' + k + '</b><span>' + v + '</span></div>';
    }
    /* le bloc le plus PROCHE de son plancher : c'est celui qui basculera au
       prochain caractere ajoute, et le seul dont le chiffre soit utile quand
       tout va bien. */
    function serre(list) {
      let best = list[0];
      list.forEach((r) => { if (r.m.pt - r.m.read_pt < best.m.pt - best.m.read_pt) best = r; });
      return best;
    }

    /* ── la ligne du controle photometrique ──────────────────────────────
       Elle ne dit JAMAIS « 0 masqué » tant qu'elle n'a pas relu les octets du
       composite en cours : un compteur qui ment est pire qu'un compteur
       absent, il eteint la vigilance. */
    function auditLine() {
      if (!CF.get("type.audit", true)) {
        return '<div class="cf-type-prow"><i>&#9678;</i><b>Lisibilité</b><span>'
          + 'contrôle photométrique désactivé — les compteurs ci-dessus ne parlent que de géométrie. '
          + '<button class="cf-type-lnk cf-type-recheck" type="button">Contrôler maintenant</button></span></div>';
      }
      if (auditErr) {
        return '<div class="cf-type-prow bad"><i>&#9888;</i><b>Lisibilité</b><span>contrôle impossible : '
          + esc(auditErr) + ' <button class="cf-type-lnk cf-type-recheck" type="button">Réessayer</button></span></div>';
      }
      if (!AUDIT || AUDIT.stamp !== AUDIT_STAMP) {
        return '<div class="cf-type-prow"><i>&#8987;</i><b>Lisibilité</b>'
          + '<span>contrôle photométrique en cours sur le composite…</span></div>';
      }
      const A = AUDIT;
      /* UN CHIFFRE SANS SON SLOT SE FAIT LIRE A L'ENVERS. « Contraste le plus
         bas 4,29:1 » a ete lu comme « le credit d'illustration est sous le
         seuil AA de 4,5 » alors qu'il s'agissait de l'ATTAQUE, a 19 pt, dont
         le seuil WCAG est 3:1. Le releve nomme donc le slot, son corps, son
         seuil — et les deux luminances qui produisent le rapport, pour qu'un
         imprimeur le recalcule sans nous croire sur parole. */
      let wr = null;
      A.rows.forEach((r) => {
        if (r.contrast_min == null) return;
        if (!wr || r.contrast_min < wr.contrast_min) wr = r;
      });
      let nr = null, nh = null;
      A.rows.forEach((r) => {
        if (r.clear_mm != null && (!nr || r.clear_mm < nr.clear_mm)) nr = r;
        if (r.halo_clear_mm != null && (!nh || r.halo_clear_mm < nh.halo_clear_mm)) nh = r;
      });
      const maskedPx = A.masked.reduce((n, r) => n + r.masked, 0);
      const ok = !A.masked.length && !A.lowc.length && !A.empties.length
        && !A.tight.length && !A.relayed.length && !A.file_dev;
      /* la marque la plus proche du bord, encre OU halo confondus : c'est elle
         que la marge optique doit tenir, et c'est elle qu'on annonce. */
      const opt = A.optical_mm;
      const tightTxt = nr
        ? "dégagement optique " + fx(nr.clear_mm, 2) + " mm — « " + esc(nr.label) + " »"
          + (nh ? " (halo d'ombre à " + (nh.halo_clear_mm < opt ? "<b>" : "")
            + fx(nh.halo_clear_mm, 2) + " mm" + (nh.halo_clear_mm < opt ? "</b>" : "")
            + " — « " + esc(nh.label) + " »)" : "")
          + " · marge déclarée " + fx(opt, 2) + " mm"
        : "";
      const parts = [
        /* D'OU VIENNENT CES CHIFFRES : d'un fichier PNG, pas d'une toile. Et
           l'ecart entre les deux est MESURE, pas affirme — c'est le critere
           « apercu contre fichier livre » du dossier, chiffre sur les octets. */
        A.rows.length + " slots relus sur le PNG encodé (" + fx(A.file_bytes / 1024, 0)
        + " Ko, " + A.canvas[0] + " x " + A.canvas[1] + " px)"
        + (A.file_dev != null
          ? " · l’aperçu et le fichier livré diffèrent de "
            + (A.file_dev ? "<b>" + A.file_dev + " canal</b>" : "<b>zéro canal</b>")
            + " sur " + A.file_n.toLocaleString("fr-FR") + " px comparés" : ""),
        (A.masked.length ? "<b>" + maskedPx + " px d'encre masqués sur " + A.masked.length + " slot(s)</b>"
          : "0 px d'encre masqué"),
        (wr ? "contraste le plus bas " + fx(wr.contrast_min, 2) + ":1 — « " + esc(wr.label)
          + " » à " + fx(wr.pt, 1) + " pt" + (wr.bold ? " gras" : "") + ", seuil AA "
          + fx(wr.seuil, 1) + ":1"
          + (wr.lum_a != null ? " = " + contrastCalc(wr) : "")
          + (contrastWhere(wr) ? " · " + contrastWhere(wr) : "")
          /* LE RAPPORT DIRECT, DES QUE LE CONTOUR FAIT LE RELAIS. C'est celui
             qu'une pipette WCAG rend sur le fichier ; le taire, c'etait
             laisser le re-mesureur trouver un autre nombre. */
          + (wr.via === "contour" && wr.contrast_direct != null
            ? " · encre contre fond sans le contour : "
              + (wr.contrast_direct < wr.seuil ? "<b>" : "")
              + fx(wr.contrast_direct, 2) + ":1"
              + (wr.contrast_direct < wr.seuil ? " (sous le seuil)</b>" : "")
            : "")
          : "contraste non mesurable"),
        tightTxt,
        (A.empties.length ? "<b>" + A.empties.length + " slot(s) sans glyphe</b>" : ""),
      ].filter(Boolean);
      return line("Lisibilité (photométrique)", parts.join(" · "),
        ok ? true : ((A.masked.length || A.lowc.length || A.empties.length) ? false : "warn"));
    }
    /* ── LA LIGNE DE DEFINITION ──────────────────────────────────────────
       Elle ne s'affiche JAMAIS sans avoir tourne : tant que les deux tirages
       n'existent pas, elle propose le controle au lieu d'annoncer un resultat.
       Et elle se perime avec la mise en page — un verdict de definition calcule
       sur d'autres boites parlerait d'une carte qui n'existe plus. */
    function defLine() {
      const alt = altDpi(g.dpi);
      const bouton = '<button class="cf-type-lnk cf-type-defc" type="button">'
        + (alt == null ? "définition unique" : "Refaire l’épreuve à " + alt + " DPI") + '</button>';
      if (defcBusy) {
        return '<div class="cf-type-prow"><i>&#8987;</i><b>Épreuve</b>'
          + '<span>second tirage à ' + alt + ' DPI, en cours…</span></div>';
      }
      if (defcErr) {
        return '<div class="cf-type-prow bad"><i>&#9888;</i><b>Épreuve</b><span>'
          + 'tirage impossible : ' + esc(defcErr) + ' ' + bouton + '</span></div>';
      }
      /* ELLE NE RESTE PAS VIDE. Le tour precedent laissait cette ligne sur
         « non contrôlé » avec un bouton gris : la mesure la plus chere du
         panneau etait a un clic, et le clic n'etait jamais fait. Elle part
         donc toute seule des que la mise en page se pose (voir
         scheduleDefCheck) ; ce qui suit n'est plus qu'un etat d'attente. */
      if (!DEFC || DEFC.key !== defKey(g)) {
        return '<div class="cf-type-prow"><i>&#8987;</i><b>Épreuve</b><span>'
          + (alt == null
            ? 'une seule définition disponible pour ce format.'
            : 'second tirage à ' + alt + ' DPI en attente — la même carte est '
              + 'recomposée à l’autre définition et les deux tirages sont comparés '
              + 'pavé par pavé. ' + bouton) + '</span></div>';
      }
      const D = DEFC;
      /* le temoin fait partie du verdict : tant que le retracage ne fait pas
         MIEUX que l'agrandissement, il n'y a rien a certifier. */
      const flou = (D.ratio != null && D.ratio_w != null && D.ratio >= D.ratio_w);
      const dur = D.moved.length || D.lost.length || D.gone.length || D.out_b.length
        || D.repts.length || flou;
      const parts = [
        D.n + " bloc(s) recomposé(s) à " + D.dpi_b + " DPI (toile " + D.canvas_b[0]
        + " x " + D.canvas_b[1] + " px contre " + D.canvas_a[0] + " x " + D.canvas_a[1]
        + ") et relus sur " + fx(D.bytes / 1024, 0) + " Ko de PNG",
        /* L'ECART EST DONNE DANS L'UNITE QUI LE REND LISIBLE. En millimetres
           seuls, « 0,127 » ressemble a un deplacement ; rapporte au pas de la
           grille, on voit que c'est un pixel et demi de la definition la plus
           grossiere, c'est-a-dire le grain meme du cadre d'encre. */
        (D.worst
          ? "écart de pavé maximal <b>" + fx(D.worst.dmm, 3) + " mm</b> = "
            + fx(D.worst.dpx, 1) + " px de la grille de " + D.dpi_min + " DPI (1 px = "
            + fx(D.qmm, 3) + " mm) — « " + esc(D.worst.label) + " »"
            + (D.moved.length ? ", <b>" + D.moved.length + " au-delà du grain de grille</b>"
              : ", tout est dans le grain de grille : <b>aucun bloc n'a bougé</b>")
          : "aucun pavé mesurable"),
        (D.repts.length
          ? "<b>" + D.repts.length + " bloc(s) changent de corps</b> : "
            + D.repts.map((r) => esc(r.label) + " " + fx(r.a.pt, 2) + " → "
              + fx(r.b.pt, 2) + " pt").join(" · ")
          : "0 changement de corps composé"),
        (D.lost.length
          ? "<b>" + D.lost.length + " bloc(s) changent de contenu</b> : "
            + D.lost.map((r) => esc(r.label) + " " + (r.dchars ? r.dchars + " car." : "")
              + (r.dlines ? " " + r.dlines + " ligne(s)" : "")).join(" · ")
          : "0 caractère et 0 ligne de différence"),
        (D.gone.length ? "<b>" + D.gone.length + " bloc(s) disparaissent</b>" : ""),
        (D.out_b.length
          ? "<b>" + D.out_b.length + " bloc(s) entament la marge du format à "
            + D.dpi_b + " DPI</b>"
          : "la marge du format est tenue aux deux définitions"),
        /* LE CHIFFRE QUI NE SE FALSIFIE PAS — ET SON TEMOIN, MESURE. Doubler
           la definition multiplie l'aire d'un glyphe par 4 et son perimetre
           par 2 : la part de liseré recule SI le texte est redessine. Ce que
           ferait un simple agrandissement n'est pas affirme ici : le tirage de
           depart est reellement agrandi, encode et recompte, et son chiffre
           est publie a cote. */
        (D.ratio != null
          ? "netteté : liseré d'anticrénelage " + fx(D.frac_a * 100, 1) + " % du tracé à "
            + D.dpi_a + " DPI → " + fx(D.frac_b * 100, 1) + " % à " + D.dpi_b
            + " DPI (<b>" + fx(D.ratio, 2) + " ×</b>)"
            + (D.ratio_w != null
              ? " · témoin mesuré, le même tirage simplement agrandi ×" + fx(1 / (D.dpi_a / D.dpi_b), 0)
                + " : " + fx(D.frac_w * 100, 1) + " % (" + fx(D.ratio_w, 2) + " ×)"
              : "")
          : ""),
      ].filter(Boolean);
      return line("Épreuve (" + D.dpi_a + " → " + D.dpi_b + " DPI)",
        parts.join(" · ") + " " + bouton, !dur);
    }
    /* ── CE QU'IL FAUT CHANGER, ET DE COMBIEN ────────────────────────────
       Un avertissement sans remede est un avertissement qu'on passera. Chaque
       ligne d'ici a ete OBTENUE en refaisant la mise en page avec la
       modification proposee, pas estimee ; le bouton applique exactement le
       reglage qui a ete mesure. */
    function fixBlock() {
      if (!FIXES || !FIXES.rows.length) return "";
      /* un remede calcule pour une autre mise en page ne s'affiche pas : il
         dirait « +9,2 mm » sur une boite qui a change entre-temps. */
      if (FIXES.key !== fixKey(g)) return "";
      const vivants = FIXES.rows.filter((r) => {
        const mm = MEAS[r.id];
        return mm && !mm.empty && (mm.under_read || mm.over);
      });
      if (!vivants.length) return "";
      return '<div class="cf-type-fix">' + vivants.map((r) => {
        /* LES DEUX DEFAUTS SONT DITS QUAND ILS SONT DEUX. Un bloc peut a la
           fois deborder de son cadre et se composer sous son plancher ; ne
           nommer que le second aurait laisse croire que l'encre, elle, tient. */
        /* ── UN SIGNALEMENT N'EST PAS UNE CORRECTION ────────────────────────
           Le panneau mesurait cinq sorties et laissait l'utilisateur choisir :
           au tirage, la carte restait fausse et l'imprimeur, prevenu. Le bouton
           ci-dessous applique la premiere sortie MESUREE qui suffit — et, si
           elle demande d'abord de remonter le corps demande, les deux d'un
           coup. Il evite la boite quand elle mordrait un bloc voisin (ce serait
           echanger un defaut contre un autre), sauf si c'est la seule qui
           suffise. Le resultat est remesure a la passe suivante et annonce. */
        const auto = autoLever(r);
        const head = '<p class="cf-type-fixh"><b>' + esc(r.label) + '</b> — composé à '
          + fx(r.pt, 1) + ' pt'
          + (r.over_chars ? ', <b>' + r.over_chars + ' caractères hors du cadre</b>' : "")
          + (r.kind === "read"
            ? ', réglé pour être lisible dès ' + fx(r.target, 1) + ' pt. Pour le composer à '
              + fx(r.target, 1) + ' pt' + (r.over_chars ? ' et le faire rentrer' : "")
              + ', une seule de ces lignes suffit :'
            : '. Pour qu\'il rentre dans son cadre, une seule de ces lignes suffit :')
          + (auto ? ' <button class="cf-type-fixgo" type="button" data-id="' + esc(r.id)
            + '" title="Applique la sortie mesurée ci-dessous, puis remesure ce qui a été composé">'
            + 'Corriger : ' + esc(auto.court) + '</button>' : "") + '</p>';
        return head + '<ul class="cf-type-fixl">' + r.levers.map((l) => '<li class="'
          + (l.ok && !l.info ? "on" : (l.info ? "info" : "no")) + '">' + l.txt
          + (l.patch ? ' <button class="cf-type-fixb" type="button" data-id="' + esc(r.id)
            + '" data-k="' + esc(l.k) + '" title="Applique ce réglage, puis remesure ce qui a été composé">'
            + 'Appliquer</button>' : "") + '</li>').join("") + '</ul>';
      }).join("") + '</div>';
    }
    /* LA REGLE DU CALCUL, ECRITE A COTE DU CHIFFRE. Un contraste annonce sans
       sa convention est invérifiable : celui qui recompte autrement — sur la
       couleur declaree, sur la moyenne des fonds, sur les bords adoucis —
       trouve un autre nombre et en conclut que le panneau ment. Les trois
       conventions tiennent en trois lignes ; elles sont ici. */
    /* REPLIEE PAR DEFAUT, mais toujours la : depliee, elle prenait cinq lignes
       au releve et volait au panneau la place de la liste des slots (la
       derniere ligne du memo clavier se retrouvait coupee en deux par le bord
       de la zone defilante). Le titre dit ce qu'elle contient ; le detail est
       a un clic, et il est dans le DOM meme replie. */
    /* LE DETAIL, BLOC PAR BLOC : sans lui, « déplacement maximal 0,003 mm » est
       un chiffre qu'il faut croire. Ici chaque ligne porte ses deux pavés en
       millimètres depuis le coin de coupe — on refait la soustraction. */
    function defDetail() {
      if (!DEFC || DEFC.key !== defKey(g)) return "";
      const D = DEFC;
      const cel = (r) => '<tr class="' + (r.dpx > DEFC_PX || r.dchars || r.dlines
        || Math.abs(r.dpt) > DEFC_PT || !r.safe_b ? "no" : "")
        + '"><td>' + esc(r.label) + '</td>'
        + '<td class="mono">' + fx(r.a.mm[0], 3) + " ; " + fx(r.a.mm[1], 3) + " · "
        + fx(r.a.mm[2], 3) + " x " + fx(r.a.mm[3], 3) + '</td>'
        + '<td class="mono">' + fx(r.b.mm[0], 3) + " ; " + fx(r.b.mm[1], 3) + " · "
        + fx(r.b.mm[2], 3) + " x " + fx(r.b.mm[3], 3) + '</td>'
        + '<td class="mono">' + fx(r.dmm, 3) + " (" + fx(r.dpx, 1) + " px)" + '</td>'
        + '<td class="mono">' + r.a.chars + " / " + r.a.lines + " / " + fx(r.a.pt, 1)
        + " pt</td>"
        + '<td class="mono">' + r.b.chars + " / " + r.b.lines + " / " + fx(r.b.pt, 1)
        + " pt</td>"
        + '<td class="mono">' + fx(r.frac_a * 100, 1) + " % → " + fx(r.frac_b * 100, 1)
        + " %</td></tr>";
      const vivants = D.rows.filter((r) => !r.empty);
      if (!vivants.length) return "";
      return '<details class="cf-type-meth"><summary>Épreuve, bloc par bloc — '
        + D.dpi_a + ' DPI contre ' + D.dpi_b + ' DPI, relue sur le fichier</summary>'
        + '<div class="cf-type-defw"><table class="cf-type-deft"><thead><tr>'
        + '<th>Bloc</th><th>Pavé à ' + D.dpi_a + ' DPI (mm)</th><th>Pavé à ' + D.dpi_b
        + ' DPI (mm)</th><th>Écart (mm, px de ' + D.dpi_min + ' DPI)</th><th>car. / lignes / corps</th>'
        + '<th>idem à ' + D.dpi_b + '</th><th>liseré</th></tr></thead><tbody>'
        + vivants.map(cel).join("") + '</tbody></table></div>'
        + '<p class="hint cf-type-methb">Les pavés sont donnés en millimètres depuis le '
        + 'coin de coupe (fond perdu déduit), mesurés sur le PNG de chaque tirage — pas sur '
        + 'la toile, pas sur la boîte. L\'écart est aussi donné en <b>pixels de la grille de '
        + D.dpi_min + ' DPI</b> (1 px = ' + fx(D.qmm, 3) + ' mm) : un cadre d\'encre est calé '
        + 'sur une grille, deux grilles différentes ne cernent pas le même contour au même '
        + 'endroit, et un écart d\'un pixel n\'est pas un déplacement. Au-delà de '
        + DEFC_PX + ' px, ou dès qu\'un caractère, une ligne ou le corps composé change, la '
        + 'ligne passe en ambre. « Liseré » = part des pixels d\'anticrénelage dans le tracé.'
        + '</p></details>';
    }
    function methodNote() {
      if (!AUDIT || AUDIT.stamp !== AUDIT_STAMP) return "";
      return '<details class="cf-type-meth"><summary>Conventions de mesure'
        + ' — encre, contraste, blancs-mots</summary>'
        + '<p class="hint cf-type-methb">'
        + '<i>Où sont pris les chiffres</i> : la carte est rendue, <b>encodée en PNG</b>, puis '
        + 'les octets sont relus — tout ce qui suit est mesuré sur ce fichier, jamais sur la '
        + 'toile. L\'écart entre les deux est publié à côté (0 canal attendu). '
        + '<i>Encre</i> : deux bornes, données ensemble parce qu\'il y a deux façons de '
        + 'remesurer un PNG. L\'<b>encre totale</b> compte tout pixel d\'opacité non nulle '
        + '(α &gt; 0) posé par le slot, liseré d\'anticrénelage compris ; le <b>corps plein</b> '
        + 'ne compte que les pixels franchement opaques (α ≥ 250). Un masque de couleur posé '
        + 'sur le fichier livré retombe forcément <b>entre les deux</b> — plus le masque est '
        + 'lâche, plus il approche la borne haute. VÉRIFIÉ hors du produit sur l\'encadré de '
        + 'règles de la carte de démonstration : de ±10 à ±80 niveaux de tolérance, le pavé '
        + 'remesuré va de 646 x 188 à 647 x 193 px, toujours dans la fourchette publiée. Ni '
        + 'la boîte, ni une estimation. L\'ombre portée '
        + 'est mesurée <b>à part</b> (« halo ») : c\'est un dégradé, pas de l\'encre pleine, '
        + 'mais elle est bien dans le fichier. '
        + '<i>Contraste</i> : luminance relative WCAG entre la médiane du corps des glyphes '
        + '(alpha plein) et le 5<sup>e</sup> centile des fonds à 6 px ou moins du glyphe, '
        + 'contour pris comme relais quand il y en a un ; seuil AA 4,5:1, ou 3:1 au-delà de '
        + '18 pt (14 pt en gras) ; le rapport affiché est la division des deux luminances '
        + 'affichées, arrondies d\'abord — il se refait à la main et retombe au centième près. '
        + 'Les <b>coordonnées publiées</b> à côté du rapport sont celles du fichier livré '
        + '(origine en haut à gauche de la toile de ' + g.canvas_px[0] + ' x ' + g.canvas_px[1]
        + ' px, fond perdu compris) : une pipette posée sur ces deux pixels-là retombe sur '
        + 'ces deux luminances-là. '
        + 'Dès que le relais sert, le rapport <b>direct</b> (encre contre fond, sans le contour) '
        + 'est publié à côté : c\'est celui que rend une pipette WCAG, et il est plus bas. '
        + '<i>Fins de ligne</i> : deux chiffres. Le <b>tracé</b> vaut 0 % par construction — une '
        + 'ligne justifiée occupe exactement la justification. L\'<b>encre</b> s\'arrête où '
        + 'finit le dernier glyphe : l\'écart des bords droits est relu sur le composite, en '
        + 'pixels, et c\'est lui qu\'un re-mesurage trouve. '
        + '<i>Marge optique</i> : comparée à la marque la plus proche du bord du cadre, '
        + '<b>halo d\'ombre compris</b> — un dégradé est de l\'encre du fichier. '
        + '<i>Blancs-mots</i> : deux conventions, données ensemble. L\'<b>avance</b> = espace '
        + 'naturel de la fonte au corps posé plus l\'étirement réellement dessiné. L\'<b>encre à '
        + 'encre</b> = le vide relu entre deux amas sur le composite, soit l\'avance moins les '
        + 'approches des deux glyphes voisins ; sur une ligne qui porte <i>k</i> espaces, les '
        + '<i>k</i> plus grands vides sont comptés comme blancs-mots. '
        + '<i>Corps de lecture</i> : le corps réglé bloc par bloc (champ « Lisible dès »), sous '
        + 'lequel le texte ne se lit plus une fois la carte imprimée — distinct du corps mini, '
        + 'qui ne borne que l\'encombrement. '
        + '<i>Définition</i> : chaque bloc est recomposé à l\'autre définition, les deux tirages '
        + 'sont encodés en PNG puis relus, et les pavés d\'encre sont comparés en millimètres '
        + 'depuis le coin de coupe — un bloc qui bouge, rétrécit, perd un caractère ou sort de '
        + 'la marge du format en changeant de définition est nommé. La part de liseré recule quand '
        + 'la définition double, parce que l\'aire d\'un glyphe est multipliée par 4 et son '
        + 'périmètre seulement par 2 ; à ces corps-là, où les fûts font un pixel de large, '
        + 'elle ne tombe pas jusqu\'à 0,50 × pour autant. Ce que ferait un agrandissement '
        + 'n\'est donc pas affirmé mais <b>mesuré</b> : le tirage de départ est réellement '
        + 'agrandi, encodé en PNG, relu et recompté de la même main, et son chiffre est publié '
        + 'à côté. Tant que le retraçage ne fait pas mieux que ce témoin, la ligne reste en '
        + 'ambre.</p></details>';
    }
    function auditDetail() {
      if (!AUDIT || AUDIT.stamp !== AUDIT_STAMP) return "";
      const A = AUDIT, out = [];
      A.masked.forEach((r) => {
        out.push("<b>" + esc(r.label) + "</b> : " + r.masked + " px d'encre sur " + r.total
          + " sont recouverts par une couche dessinée au-dessus — "
          + fx((1 - r.rate) * 100, 1) + " % des glyphes ne sont pas dans le fichier livré.");
      });
      A.lowc.forEach((r) => {
        out.push("<b>" + esc(r.label) + "</b> : contraste mesuré " + fx(r.contrast_min, 2)
          + ":1 contre le fond réellement derrière (médiane " + fx(r.contrast, 2) + ":1), "
          + "sous le seuil WCAG AA de " + fx(r.seuil, 1) + ":1 à " + fx(r.pt, 1)
          + " pt" + (r.lum_a != null ? " — " + contrastCalc(r) : "")
          + (contrastWhere(r) ? ", " + contrastWhere(r) : "")
          + ". Un contour, une ombre ou une plaque de fond règlent le cas.");
      });
      A.empties.forEach((r) => {
        out.push("<b>" + esc(r.label) + "</b> : slot configuré, aucun glyphe posé. "
          + "La zone reste vide dans le fichier livré.");
      });
      A.relayed.forEach((r) => {
        out.push("<b>" + esc(r.label) + "</b> : lisible grâce à son contour ("
          + fx(r.contrast_min, 2) + ":1 par le relais), mais l'encre seule contre le fond ne fait que "
          + fx(r.contrast_direct, 2) + ":1"
          + (r.direct_a != null ? " — (" + fx(r.direct_a, 4) + " + 0,05) / ("
            + fx(r.direct_b, 4) + " + 0,05)" : "")
          + (r.ink_pt && r.direct_pt ? ", relevé au pixel " + ptTxt(r.ink_pt)
            + " pour l'encre et " + ptTxt(r.direct_pt) + " pour le fond" : "")
          + ", sous le seuil AA de " + fx(r.seuil, 1) + ":1 à " + fx(r.pt, 1) + " pt. "
          /* CE QUI LE REMONTE, VERIFIE PLUTOT QUE SUPPOSE. Le panneau disait
             « épaissir le contour ou assombrir le fond le remonte » : la
             seconde moitié est vraie, la première est FAUSSE. Le rapport direct
             ne connaît que deux couleurs, l'encre et le fond ; un contour plus
             épais n'agit que sur le relais. Sur ce slot, encre 0,8064 contre
             fond 0,3163 : même une encre BLANCHE ne donnerait que
             (1,05)/(0,3663) = 2,87:1, toujours sous 3. Seul le fond peut
             bouger — c'est mesurable, donc c'est ce qui est écrit. */
          + "C'est le chiffre que rendra une pipette WCAG posée sur le fichier, et il ne "
          + "dépend que de deux couleurs : assombrir le fond sous l'encre — ou lui poser "
          + "une plaque — le remonte. Épaissir le contour, non : le contour n'agit que "
          + "sur le relais.");
      });
      A.tight.forEach((r) => {
        /* on NOMME la marque en cause : le corps des glyphes, ou le halo de
           l'ombre. Les deux sont dans le fichier, l'un est de l'encre pleine
           et l'autre un dégradé — les confondre était le premier défaut. */
        const halo = r.halo_clear_mm != null && (r.clear_mm == null || r.halo_clear_mm < r.clear_mm);
        out.push("<b>" + esc(r.label) + "</b> : " + (halo
          ? "le halo de l'ombre portée passe à " + fx(r.halo_clear_mm, 2)
          : "l'encre passe à " + fx(r.clear_mm, 2))
          + " mm du bord du cadre de composition — sous la marge optique de "
          + fx(A.optical_mm, 2) + " mm que ce panneau déclare"
          + (halo ? " (le corps des glyphes, lui, est à " + fx(r.clear_mm, 2) + " mm)" : "")
          + ". Les repères de coupe d'une rotative dérivent d'autant.");
      });
      return out.length ? '<p class="cf-type-warn">' + out.join("<br>") + "</p>" : "";
    }
  }
  /* ═════════════════════════════════════════════════════════════════════════
     7ter. LES REMEDES — ce qu'il faut changer, ET DE COMBIEN

     Le reproche exact du critique : « B a construit le meilleur detecteur de
     faute du duel et s'est arrete juste avant de le rendre actionnable. Un
     avertissement pose sur le seul reglage que l'utilisateur ne peut pas
     corriger depuis cet ecran est un avertissement qu'on passera. »

     C'etait vrai : le releve disait « Titre 8,9 pt (plancher 12) » et
     s'arretait la. Le seul levier de l'ajustement automatique est de REDUIRE
     LE CORPS ; les autres — agrandir la boite, relacher l'interlettrage,
     serrer l'interligne, activer la cesure, raccourcir le texte — existent
     tous dans cet inspecteur, et personne ne disait lequel suffirait.

     Ici chaque levier est ESSAYE, pas estime : on refait la mise en page avec
     la modification, avec le MEME `layoutSlot` que le painter, et on publie le
     corps qu'elle atteint. Un candidat = UNE mise en page, parce qu'on fige le
     corps (mini = demande = cible, ajustement coupe) au lieu de relancer la
     dichotomie interne. Le levier qui suffit porte un bouton qui l'applique ;
     le remede est ensuite VERIFIE sur la mise en page suivante, et s'il ne
     tient pas, le panneau le dit au lieu de se taire.

     RACCOURCIR LE TEXTE EST UN CHIFFRE, JAMAIS UN BOUTON : cette piece ne
     supprime pas un caractere. On dit combien il faudrait en retirer ; c'est
     l'auteur qui decide, dans son champ.
     ═════════════════════════════════════════════════════════════════════════ */
  let FIXES = null, FIXES_KEY = "", fixTimer = null, FIX_CV = null;
  let PENDING = null;              /* remede applique, en attente de verdict */
  const FIX_TRACKS = [-1, -2, -3, -5];      /* % de cadratin retires */
  const FIX_LEADS = [1.1, 1.05, 1.0, 0.95];

  function fixCtx() {
    if (!FIX_CV) { FIX_CV = document.createElement("canvas"); FIX_CV.width = 8; FIX_CV.height = 8; }
    return FIX_CV.getContext("2d");
  }
  /* « ce texte tient-il a CE corps, avec CE changement ? » — une seule mise en
     page par candidat. */
  function fitsWith(ctx, slot, g, text, pt, over) {
    const s = normSlot(Object.assign(clone(slot), over || {},
      { size_pt: pt, min_pt: pt, autofit: false }), 0);
    return !layoutSlot(ctx, s, g, text).over;
  }
  /* le plus grand corps qui tient avec ce changement — c'est le chiffre que le
     panneau publie a cote de chaque levier. */
  function maxPtWith(ctx, slot, g, text, over, lo, hi) {
    if (fitsWith(ctx, slot, g, text, hi, over)) return hi;
    if (!fitsWith(ctx, slot, g, text, lo, over)) return null;
    let a = lo, b = hi;
    for (let i = 0; i < 14 && b - a > 0.02; i++) {
      const mid = (a + b) / 2;
      if (fitsWith(ctx, slot, g, text, mid, over)) a = mid; else b = mid;
    }
    return a;
  }
  const insideSafe = (b, sr) => b[0] >= sr[0] - 1e-6 && b[1] >= sr[1] - 1e-6
    && b[0] + b[2] <= sr[0] + sr[2] + 1e-6 && b[1] + b[3] <= sr[1] + sr[3] + 1e-6;
  /* La boite portee a w x h, AUTOUR DE SON CENTRE. Une boite qui etait dans la
     zone sure y reste (on la translate plutot que de la rogner) ; une boite que
     l'auteur avait posee dehors n'y est pas rapatriee — on ne redispose pas le
     travail de quelqu'un.
     LARGEUR ET HAUTEUR SONT INDEPENDANTES. Un facteur unique les liait : sur un
     titre de 46 x 9 mm dans une zone sure de 57 x 82, la largeur plafonnait le
     facteur a 1,23 et le panneau concluait « meme etendue a toute la zone sure,
     ce bloc ne compose pas » — une phrase FAUSSE, jamais essayee, alors qu'une
     boite plus HAUTE suffisait. Un chiffre qu'on n'a pas mesure ne s'affiche
     pas. */
  function boxAt(box, w, h, sr, keepIn) {
    if (keepIn && (w > sr[2] + 1e-9 || h > sr[3] + 1e-9)) return null;
    /* ARRONDI AU MICRON, ET TOUJOURS VERS L'INTERIEUR. Une ordonnee calee sur
       le bord de la zone sure et arrondie au plus proche en sortait de 0,3
       micron (2,9633 mm -> 2,963) : invisible a l'oeil, faux au controle avant
       vol, qui ne fait pas de courtoisie. La largeur et la hauteur descendent,
       l'origine monte : ce qu'on propose tient dans ce qu'on annonce. */
    const dn = (v) => Math.floor(v * 1e3) / 1e3;
    const up = (v) => Math.ceil(v * 1e3) / 1e3;
    const nw = dn(w), nh = dn(h);
    let x = Math.round((box[0] + (box[2] - nw) / 2) * 1e3) / 1e3;
    let y = Math.round((box[1] + (box[3] - nh) / 2) * 1e3) / 1e3;
    if (keepIn) {
      const xl = up(sr[0]), xh = dn(sr[0] + sr[2] - nw);
      const yl = up(sr[1]), yh = dn(sr[1] + sr[3] - nh);
      x = (xh < xl) ? xl : clamp(x, xl, xh);
      y = (yh < yl) ? yl : clamp(y, yl, yh);
    }
    return [x, y, nw, nh];
  }
  /* Le remede d'UN slot. Rend null quand il n'y a rien a corriger. */
  function remedyFor(slot, m, g, text) {
    if (!m || m.empty || (!m.under_read && !m.over)) return null;
    const ctx = fixCtx();
    const kind = m.under_read ? "read" : "over";
    const target = kind === "read" ? slot.read_pt : m.pt;
    const sr = safeRectMm(g);
    const keepIn = insideSafe(slot.box, sr);
    const out = { id: slot.id, label: slot.label, kind: kind, target: target,
      pt: m.pt, chars: m.chars, over_chars: (m.over ? m.over_chars : 0), levers: [] };
    /* PREREQUIS : un corps DEMANDE sous la cible ne peut etre atteint par
       aucun agrandissement — l'ajustement ne monte jamais au-dessus du corps
       demande. On le dit avant de proposer le reste. */
    const base = slot.size_pt < target - 0.005
      ? Object.assign(clone(slot), { size_pt: target }) : slot;
    if (base !== slot) {
      /* PREALABLE et non remede : neutre a l'affichage (il ne suffit pas seul),
         mais il porte son bouton — c'est le premier geste a faire. */
      out.levers.push({ k: "size", ok: false, info: true,
        txt: "d'abord porter le corps demandé de " + fx(slot.size_pt, 1) + " à "
          + fx(target, 1) + " pt : <i>l'ajustement ne monte jamais au-dessus du corps"
          + " demandé, aucun agrandissement ne peut donc y arriver seul</i>",
        patch: { size_pt: target } });
    }
    const lo = Math.min(base.min_pt, base.size_pt), hi = base.size_pt;
    /* 1. LA BOITE — le plus petit agrandissement qui compose a la cible.
       Trois candidats mesures : plus HAUTE seule (une ligne de plus), plus
       LARGE seule (un slot sans retour a la ligne), et les deux. On retient
       celui qui ajoute le moins de surface. */
    const wMax = keepIn ? sr[2] : Math.max(sr[2], slot.box[2] * 4);
    const hMax = keepIn ? sr[3] : Math.max(sr[3], slot.box[3] * 8);
    const fitsB = (w, h) => {
      const b = boxAt(slot.box, w, h, sr, keepIn);
      return b ? fitsWith(ctx, base, g, text, target, { box: b }) : false;
    };
    /* le plus petit v de [v0, vMax] qui tient — null si meme vMax ne tient pas */
    const least = (v0, vMax, mk) => {
      if (!(vMax > v0 + 1e-6) || !mk(vMax)) return null;
      let a = v0, b = vMax;
      for (let i = 0; i < 18 && b - a > 0.01; i++) {
        const mid = (a + b) / 2;
        if (mk(mid)) b = mid; else a = mid;
      }
      return b;
    };
    const cands = [];
    const hOnly = least(slot.box[3], hMax, (h) => fitsB(slot.box[2], h));
    if (hOnly != null) cands.push([slot.box[2], hOnly]);
    const wOnly = least(slot.box[2], wMax, (w) => fitsB(w, slot.box[3]));
    if (wOnly != null) cands.push([wOnly, slot.box[3]]);
    if (!cands.length && fitsB(wMax, hMax)) {
      const h2 = least(slot.box[3], hMax, (h) => fitsB(wMax, h));
      if (h2 != null) cands.push([wMax, h2]);
    }
    if (cands.length) {
      /* UN REMEDE NE DOIT PAS ECHANGER UN DEFAUT CONTRE UN AUTRE. Une boite
         agrandie peut venir mordre le slot voisin : on prefere donc le candidat
         qui ne chevauche RIEN, et si aucun n'y arrive, on garde le plus petit
         mais on NOMME le slot qu'il touchera. Se taire la-dessus aurait rendu
         le bouton piegeux. */
      const chevauche = (b) => slots().filter((o) => o.id !== slot.id && o.on
        && (o.side === slot.side || o.side === "both" || slot.side === "both")
        && b[0] < o.box[0] + o.box[2] - 1e-6 && o.box[0] < b[0] + b[2] - 1e-6
        && b[1] < o.box[1] + o.box[3] - 1e-6 && o.box[1] < b[1] + b[3] - 1e-6)
        .map((o) => o.label);
      cands.forEach((c) => {
        c[2] = chevauche(boxAt(slot.box, c[0], c[1], sr, keepIn) || slot.box);
      });
      cands.sort((p, q) => (p[2].length - q[2].length) || (p[0] * p[1] - q[0] * q[1]));
      const heurt = cands[0][2];
      const nb = boxAt(slot.box, cands[0][0], cands[0][1], sr, keepIn);
      const dw = nb[2] - slot.box[2], dh = nb[3] - slot.box[3];
      /* on ne nomme que la dimension qui CHANGE : « +-0 x +8,8 » etait juste et
         illisible. */
      const dim = (dw > 0.05 && dh > 0.05)
        ? "la boîte : " + fx(slot.box[2], 1) + " x " + fx(slot.box[3], 1) + " → <b>"
          + fx(nb[2], 1) + " x " + fx(nb[3], 1) + " mm</b>"
        : (dh > 0.05
          ? "la boîte en hauteur : " + fx(slot.box[3], 1) + " → <b>" + fx(nb[3], 1)
            + " mm</b> (+" + fx(dh, 1) + ")"
          : "la boîte en largeur : " + fx(slot.box[2], 1) + " → <b>" + fx(nb[2], 1)
            + " mm</b> (+" + fx(dw, 1) + ")");
      out.levers.push({ k: "box", ok: true, patch: { box: nb }, heurt: heurt.length,
        txt: "agrandir " + dim + (heurt.length
          ? " — <i>elle chevauchera alors « " + heurt.map(esc).join(" » et « ") + " »</i>"
          : "") });
    } else {
      /* la phrase n'est publiee qu'apres avoir ESSAYE la boite maximale. */
      out.levers.push({ k: "box", ok: false,
        txt: "agrandir la boîte ne suffit pas : <b>même portée à " + fx(wMax, 0) + " x "
          + fx(hMax, 0) + " mm</b>" + (keepIn ? " (tout le cadre de composition)" : "")
          + ", ce bloc ne compose pas à " + fx(target, 1) + " pt" });
    }
    /* 2. LE TEXTE — combien de caracteres en trop, dans la boite ACTUELLE.
       Chiffre, jamais bouton : ce module ne supprime pas un caractere. */
    const gl = Array.from(text);
    if (gl.length > 1) {
      const fitsN = (n) => fitsWith(ctx, base, g, gl.slice(0, n).join(""), target, null);
      if (!fitsN(gl.length)) {
        let a = 0, b = gl.length;
        for (let i = 0; i < 16 && b - a > 1; i++) {
          const mid = Math.floor((a + b) / 2);
          if (fitsN(mid)) a = mid; else b = mid;
        }
        out.levers.push({ k: "chars", ok: true, info: true,
          txt: "ou raccourcir le texte de <b>" + (gl.length - a) + " caractères</b> ("
            + gl.length + " → " + a + ") — <i>chiffre, pas bouton : ce module ne coupe rien</i>" });
      }
    }
    /* 3. LES REGLAGES DEJA PRESENTS DANS CET INSPECTEUR, essayes un par un.
       Une famille (interlettrage, interligne) est essayee du plus doux au plus
       fort et s'arrete au premier cran qui suffit ; si aucun ne suffit, on
       publie le cran le plus fort AVEC le corps qu'il atteint — « atteint 9,2
       pt » se lit tout seul, « insuffisant » sans chiffre ne se lit pas. */
    const famille = (nom, cands) => {
      if (!cands.length) return;
      let best = null;
      for (let i = 0; i < cands.length; i++) {
        const c = cands[i];
        const p = maxPtWith(ctx, base, g, text, c.over, lo, hi);
        const ok = p != null && Math.round(p * 10) >= Math.round(target * 10);
        if (!best || (p != null && (best.reach == null || p > best.reach))) {
          best = { k: nom, ok: ok, reach: p, label: c.label, over: c.over };
        }
        if (ok) { best = { k: nom, ok: true, reach: p, label: c.label, over: c.over }; break; }
      }
      out.levers.push({ k: best.k, ok: best.ok, reach: best.reach,
        txt: best.label + " : " + (best.reach == null ? "le texte ne rentre toujours pas"
          : "atteint <b>" + fx(best.reach, 1) + " pt</b>" + (best.ok ? "" : " (insuffisant)")),
        patch: best.ok ? best.over : null });
    };
    if (!slot.hyphen && slot.wrap) {
      famille("hyphen", [{ over: { hyphen: true }, label: "activer la césure" }]);
    }
    famille("track", FIX_TRACKS
      .map((d) => Math.round((slot.track + d) * 10) / 10)
      .filter((t) => t >= TRACK_MIN_PC)
      .map((t) => ({ over: { track: t },
        label: "interlettrage " + fx(slot.track, 1) + " → " + fx(t, 1) + " %" })));
    famille("lead", (m.lines.length > 1 ? FIX_LEADS : [])
      .filter((l) => l < slot.leading - 0.005)
      .map((l) => ({ over: { leading: l },
        label: "interligne " + fx(slot.leading, 2) + " → " + fx(l, 2) })));
    /* ── 4. UNE AUTRE FAMILLE — LE LEVIER QUE L'INSPECTEUR NE POUVAIT PAS
       TROUVER SEUL. Un titre qui ne compose pas a 12 pt dans une romaine large
       y arrive dans une etroite ; le catalogue en sert 23 et leur chasse se
       MESURE ici, avec le moteur qui dessine. Deux garde-fous, sans quoi le
       chiffre publie ne vaudrait rien :
       — on n'essaie qu'une famille reellement POSEE (fichier charge ET chasse
         mesuree differente du repli du systeme) : mesurer une famille absente,
         c'est mesurer le repli et l'annoncer sous un autre nom ;
       — jamais une famille a qui il manque un signe du texte (table cmap du
         fichier) : un remede qui change le titre en « Cr ature » n'en est pas un. */
    const posables = FONTS.filter((f) => f.id !== slot.font
      && FONT_STATE[f.id] === "ok" && FONT_MEAS[f.id] === true
      && !tofuOf(Object.assign(clone(slot), { font: f.id }), text).length);
    if (posables.length) {
      let bf = null;
      posables.forEach((f) => {
        const p = maxPtWith(ctx, base, g, text, { font: f.id }, lo, hi);
        if (p == null) return;
        if (!bf || p > bf.p) bf = { f: f, p: p };
      });
      if (bf) {
        const okf = Math.round(bf.p * 10) >= Math.round(target * 10);
        out.levers.push({ k: "font", ok: okf, reach: bf.p,
          txt: "changer de police pour « " + esc(bf.f.label) + " » : atteint <b>"
            + fx(bf.p, 1) + " pt</b>" + (okf ? "" : " (insuffisant)")
            + " — <i>la meilleure des " + posables.length
            + " familles essayées qui savent écrire ce texte</i>",
          patch: okf ? { font: bf.f.id } : null });
      }
    }
    return out;
  }
  /* ── LA SORTIE QU'UN SEUL BOUTON APPLIQUE ────────────────────────────────
     La premiere des sorties mesurees qui SUFFIT ; la boite est ecartee quand
     elle mordrait un bloc voisin (echanger un defaut contre un autre n'est pas
     corriger), sauf si elle est la seule a suffire. Le prealable de corps
     demande part avec elle : deux reglages, un clic, une seule mise en page.
     Rend null quand aucune sortie ne suffit — le panneau n'offre alors PAS de
     bouton, plutot qu'un bouton qui ne tiendrait pas sa promesse. */
  const LEVER_COURT = { box: "agrandir la boîte", hyphen: "activer la césure",
    track: "resserrer l'interlettrage", lead: "resserrer l'interligne",
    font: "changer de police" };
  function autoLever(r) {
    if (!r || !r.levers) return null;
    const suff = r.levers.filter((l) => l.ok && !l.info && l.patch);
    if (!suff.length) return null;
    const doux = suff.filter((l) => !l.heurt);
    const best = (doux.length ? doux : suff)[0];
    const pre = r.levers.filter((l) => l.info && l.patch && l.k === "size")[0];
    return {
      lever: best,
      patch: Object.assign({}, pre ? pre.patch : null, best.patch),
      court: LEVER_COURT[best.k] || "appliquer",
    };
  }
  function fixKey(g) {
    return JSON.stringify([slots(), g.fmt, g.dpi, CF.current(),
      CF.get("type.optical_mm", OPTICAL_MM_DEF)]);
  }
  let fontsForFix = false;
  function scheduleFixes() {
    clearTimeout(fixTimer);
    fixTimer = setTimeout(() => {
      const g = CF.geom(), key = fixKey(g);
      if (key === FIXES_KEY) return;
      /* LE LEVIER « AUTRE POLICE » A BESOIN DES POLICES. Tant qu'un fichier
         n'est pas pose, sa chasse est celle du repli : on chargerait le
         catalogue pour mesurer 23 fois la meme fonte. Les 23 sont donc
         chargees une fois — et seulement le jour ou un bloc est fautif, pour
         ne pas payer 23 requetes a l'ouverture d'un document sain. */
      const fautif = slots().some((s) => {
        const mm = s.on ? MEAS[s.id] : null;
        return !!(mm && !mm.empty && (mm.under_read || mm.over));
      });
      if (fautif && !fontsForFix) {
        fontsForFix = true;
        ensureFonts(FONTS.map((f) => f.id)).then(() => {
          FONTS.forEach((f) => {
            if (FONT_STATE[f.id] === "ok" && FONT_MEAS[f.id] === undefined) {
              FONT_MEAS[f.id] = faceIsReal(f.id);
            }
          });
          FIXES_KEY = "";
          scheduleFixes();
        });
      }
      const card = CF.card(CF.current());
      const out = [];
      slots().forEach((s) => {
        if (!s.on) return;
        const m = MEAS[s.id];
        if (!m) return;
        const r = remedyFor(s, m, g, textOf(s, card));
        if (r) out.push(r);
      });
      FIXES_KEY = key;
      FIXES = out.length ? { key: key, rows: out } : null;
      renderProof();
    }, 420);
  }
  /* LE REMEDE APPLIQUE EST VERIFIE. Un panneau qui propose un reglage et ne
     regarde pas ce qu'il a produit est un panneau qui promet ; celui-ci
     remesure a la passe suivante et annonce le corps REELLEMENT compose. */
  function checkPending() {
    if (!PENDING) return;
    const m = MEAS[PENDING.id];
    if (!m || PENDING.stamp === AUDIT_STAMP) return;
    const p = PENDING; PENDING = null;
    const ok = Math.round(m.pt * 10) >= Math.round(p.target * 10) && !m.over;
    M.toast("« " + p.label + " » composé à " + fx(m.pt, 1) + " pt"
      + (ok ? " — les " + fx(p.target, 1) + " pt réglés sont atteints"
        : " : le remède n'a pas tenu"), !ok);
  }

  /* Le meme controle, mais rendu par le BACKEND, avec la meme regle de
     geometrie que l'imprimeur — et sur les encombrements REELLEMENT MESURES
     ici. Si les deux verdicts divergent, c'est un bug, et il se voit. */
  function scheduleApiCheck() {
    clearTimeout(apiTimer);
    apiTimer = setTimeout(async () => {
      const g = CF.geom(), a = slots();
      if (!a.length) return;
      const ink = {}, posed = {};
      Object.keys(MEAS).forEach((k) => {
        ink[k] = MEAS[k].ink.map((v) => Math.round(v * 100) / 100);
        /* le corps REELLEMENT COMPOSE part avec l'encombrement : le backend
           n'a pas les polices, il ne peut pas le recalculer — mais il peut
           appliquer la meme regle de plancher, et un desaccord entre les deux
           verdicts devient visible au lieu de rester dans l'ecran. */
        posed[k] = Math.round(MEAS[k].pt * 100) / 100;
      });
      try {
        /* les textes REELLEMENT POSES partent aussi : le second comptage relit
           alors la table cmap des fichiers de police et redonne, tout seul, la
           liste des signes hors police. Deux comptes de la meme grandeur. */
        const cardA = CF.card(CF.current());
        const texts = {};
        a.forEach((s) => { texts[s.id] = textOf(s, cardA); });
        const r = await M.api.post("layout", {
          fmt: g.fmt, dpi: g.dpi, bleed_mm: g.bleed_mm, safe_mm: g.safe_mm,
          slots: a, ink: ink, posed: posed, texts: texts,
        });
        const s = r && r.summary;
        /* ── CE QUE VAUT LE VERDICT DE ZONE SURE ────────────────────────────
           La zone sure sort d'un arrondi au pixel : sa longueur en millimetres
           n'est pas EXACTEMENT la meme a 150, 300 et 600 DPI. Le backend
           mesure cette derive au lieu de la supposer nulle, et le panneau la
           publie a cote du verdict qu'elle qualifie — un bloc pose a moins de
           ce chiffre du bord peut changer d'avis en changeant de definition,
           et celui qui l'ignore croit a une certitude qui n'existe pas. */
        const dd = r && r.definition;
        /* CE COMPTE-CI N'EST PAS CELUI DE L'ECRAN. Il est refait ailleurs, sur
           les memes encombrements mesures, avec la meme regle de geometrie —
           c'est ce que « recompté hors de l'écran » veut dire, et un desaccord
           entre les deux chiffres serait visible au lieu d'etre tu. */
        apiVerdict = s ? ("recompté hors de l'écran : " + (s.ok ? "aucun bloc à reprendre"
          : s.outside_safe.length + " bloc(s) entament la marge du format")
          + ((s.under_read && s.under_read.length)
            ? ", " + s.under_read.length + " sous le corps réglé" : "")
          + ((s.missing_glyphs && s.missing_glyphs.length)
            ? ", " + s.missing_glyphs.length + " avec un signe hors police" : "")
          + (dd ? " · le cadre de composition lui-même varie de " + fx(dd.drift_mm, 3)
            + " mm entre les définitions du format (" + dd.dpis.join(" / ")
            + " DPI, soit " + fx(dd.drift_px_min_dpi, 2)
            + " px de " + dd.dpis[0] + " DPI) : c'est la tolérance de ce relevé" : "")) : null;
      } catch (e) {
        apiVerdict = (e && e.missing) ? "second comptage indisponible" : null;
      }
      renderProof();
    }, 700);
  }

  /* ═════════════════════════════════════════════════════════════════════════
     7bis. LE CONTROLE PHOTOMETRIQUE — sur le bitmap, pas sur les rectangles

     Le controle geometrique (boite contre zone sure) ne sait repondre qu'a une
     question : « le cadre du slot tient-il dans la zone sure ? ». Il repond
     « oui » sur une carte ou le texte a DISPARU sous une couche dessinee
     par-dessus (z=70), parce qu'il n'a jamais regarde l'image. Trois compteurs
     verts sur un nom d'illustrateur illisible : c'est exactement la troncature
     muette que cette piece reproche a la barre, obtenue autrement.

     Ce controle-ci regarde les OCTETS. Pour chaque slot :
       * on redessine son encre SEULE sur une toile transparente de la meme
         geometrie, avec les memes reglages, ombre coupee (l'ombre est un halo,
         pas de l'encre). Les pixels a alpha 255 sont le CORPS des glyphes ;
       * on lit le composite final au meme endroit. Un pixel de corps est
         opaque : sans occlusion, le composite y vaut EXACTEMENT la couleur de
         l'encre. S'il vaut autre chose, une couche est passee dessus ;
       * on rapporte « N px d'encre masques (M % des glyphes) », le cadre
         d'encre REELLEMENT MESURE (plus aucune estimation affichee), le
         degagement optique en mm, et le CONTRASTE WCAG de l'encre survivante
         contre le fond reellement derriere elle — echantillonne sur le
         composite, autour des glyphes, pas suppose.
     ═════════════════════════════════════════════════════════════════════════ */
  const AUDIT_TOL = 12;          /* ecart de canal tolere sur un pixel de corps */
  const AUDIT_ALPHA = 250;       /* alpha d'un pixel de CORPS de glyphe */
  const SURV_MIN = 0.98;         /* en deca, l'encre est declaree masquee */
  const BG_MAX = 40000;          /* echantillons de fond par slot */
  const BG_NEAR = 6;             /* px : au-dela, ce n'est plus le fond DU glyphe */

  function srgb(v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
  function lumOf(r, gg, b) { return 0.2126 * srgb(r) + 0.7152 * srgb(gg) + 0.0722 * srgb(b); }
  function wcag(l1, l2) {
    const a = Math.max(l1, l2), b = Math.min(l1, l2);
    return (a + 0.05) / (b + 0.05);
  }
  function pct(arr, p) {
    if (!arr.length) return null;
    const s = arr.slice().sort((x, y) => x - y);
    return s[clamp(Math.round((s.length - 1) * p), 0, s.length - 1)];
  }
  /* le rang de la valeur la plus proche de `v` : sert a retrouver LE PIXEL qui
     porte la luminance publiee (une mediane est une valeur, pas un endroit). */
  function nearestIdx(arr, v) {
    let best = 0, d = Infinity;
    for (let i = 0; i < arr.length; i++) {
      const e = Math.abs(arr[i] - v);
      if (e < d) { d = e; best = i; }
    }
    return best;
  }
  /* index dans la fenetre de lecture -> coordonnees en pixels DU FICHIER. */
  function xy(p, x0, y0, w) {
    return (p == null) ? null : [x0 + (p % w), y0 + ((p / w) | 0)];
  }

  /* ── UNE TOILE DEVIENT UN FICHIER, ET C'EST LE FICHIER QU'ON MESURE ───────
     Tant que le controle lisait la TOILE, chacun de ses chiffres restait un
     chiffre d'ecran : « l'encadre fait 649 x 194 px » decrivait un tampon
     memoire, pas les octets qui partent chez l'imprimeur. C'est le reproche
     de fond du tour precedent — « tout son avantage est un avantage d'ecran,
     le critere apercu-contre-fichier reste a zero ».
     On encode donc la toile en PNG, on RELIT les octets produits, et toutes
     les mesures qui suivent sortent de cette relecture. L'ecart entre la
     toile et le fichier est lui aussi mesure et publie : s'il n'est pas nul,
     c'est l'encodage qui a menti, et on veut le savoir. */
  async function asFile(cv) {
    const blob = await new Promise((res, rej) => {
      cv.toBlob((b) => (b ? res(b) : rej(new Error("encodage PNG impossible"))), "image/png");
    });
    const bmp = await createImageBitmap(blob);
    const c2 = document.createElement("canvas");
    c2.width = cv.width; c2.height = cv.height;
    const x2 = c2.getContext("2d", { willReadFrequently: true });
    x2.clearRect(0, 0, c2.width, c2.height);
    x2.drawImage(bmp, 0, 0);
    if (bmp.close) bmp.close();
    return { ctx: x2, bytes: blob.size, w: cv.width, h: cv.height };
  }

  /* ── L'ENCRE SEULE : UN SEUL OBJET DE NEUTRALISATION ────────────────────
     Trois passes redessinent un slot TOUT SEUL pour mesurer son encre : le
     controle photometrique (ce qui survit au composite), le releve du halo
     d'ombre, et le tirage sur fichier. Les trois doivent voir LES GLYPHES et
     rien d'autre :
       · la PLAQUE de fond est du decor. Peinte ici, elle rendrait chaque
         pixel de la boite opaque — donc « corps de glyphe » pour le masque —
         et ni le taux de masquage ni le contraste ne mesureraient plus rien.
         Dans le COMPOSITE elle reste : c'est meme le bon fond a mesurer
         derriere le texte.
       · l'OPACITE du slot est ramenee a 100 : on mesure de l'encre, pas un
         reglage de fondu.
       · l'OMBRE tombe aussi — c'est un degrade, pas de l'encre — SAUF pour la
         passe qui la mesure justement (`{ shadow: true }`), parce qu'elle
         existe bel et bien dans le fichier livre.
     Les trois le faisaient A LA MAIN, chacune avec son propre litteral : trois
     occasions d'oublier la cle suivante. Une QUATRIEME passe doit appeler ce
     helper, pas recopier l'objet une quatrieme fois — le test qui compte les
     appels le dit en toutes lettres. */
  function soloClone(slot, garde) {
    return Object.assign(clone(slot), (garde && garde.shadow)
      ? { opacity: 100, plate_color: null }
      : { shadow: 0, shadow_dx: 0, shadow_dy: 0, opacity: 100, plate_color: null });
  }

  async function runAudit() {
    if (auditing || !HOST || IN_AUDIT) return;
    if (!Object.keys(MEAS).length) { AUDIT = null; AUDIT_DONE = AUDIT_STAMP; return; }
    const stamp = AUDIT_STAMP;
    auditing = true; IN_AUDIT = true; auditErr = "";
    try {
      const g = CF.geom();
      const comp = await CF.renderCard(CF.current(), { face: MEAS_SIDE });
      /* les mesures d'APRES le rendu : ce sont celles de la passe qui vient de
         produire `comp`, pas celles d'avant l'attente. */
      const file = await asFile(comp);
      let devMax = 0, devN = 0;
      const ids = Object.keys(MEAS);
      const cw = comp.width, ch = comp.height;
      const cctx = comp.getContext("2d");
      const fctx = file.ctx;
      const scr = document.createElement("canvas");
      scr.width = cw; scr.height = ch;
      const sctx = scr.getContext("2d");
      const byId = {};
      slots().forEach((s) => { byId[s.id] = s; });
      const sr = safeRectPx(g);
      const rows = [];
      ids.forEach((id) => {
        const m = MEAS[id], slot = byId[id];
        /* Le releve ne PORTE deja pas les calques d'image (le painter les
           ecarte avant `layoutSlot`) ; la garde est DITE ici quand meme :
           cette passe part de `MEAS` aujourd'hui, elle pourrait repartir de
           `slots()` demain, et l'exclusion doit survivre a ce changement-la.
           Mesurer le contraste d'une image serait mesurer une photographie
           contre un fond — un nombre sans metier. */
        if (!slot || isImage(slot)) return;
        if (m.empty) {
          rows.push({ id: id, label: slot.label, empty: true, total: 0, vis: 0,
            masked: 0, rate: 1, contrast: null, seuil: wcagSeuil(m.pt, slot.bold) });
          return;
        }
        /* fenetre de lecture : l'encombrement estime, dilate de trois quarts
           de cadratin pour attraper le fond autour des glyphes ET l'encre qui
           deborderait de l'estimation. Si l'encre touche quand meme le bord de
           la fenetre, le releve le DIT (`clipped`) au lieu d'annoncer une
           bbox rognee comme si elle etait complete. */
        const grow = Math.ceil(m.sizePx * 0.75) + 6;
        const x0 = clamp(Math.floor(m.ink[0] - grow), 0, cw - 1);
        const y0 = clamp(Math.floor(m.ink[1] - grow), 0, ch - 1);
        const x1 = clamp(Math.ceil(m.ink[0] + m.ink[2] + grow), 1, cw);
        const y1 = clamp(Math.ceil(m.ink[1] + m.ink[3] + grow), 1, ch);
        const w = Math.max(1, x1 - x0), h = Math.max(1, y1 - y0);
        sctx.setTransform(1, 0, 0, 1, 0, 0);
        sctx.clearRect(x0, y0, w, h);
        /* ombre coupee, opacite a 100, plaque coupee : on veut le CORPS des
           glyphes, et rien que lui (voir soloClone). */
        const solo = soloClone(slot);
        drawSlot(sctx, solo, g, m);
        const S = sctx.getImageData(x0, y0, w, h).data;
        /* `F` = LE FICHIER. `Fc` = la toile. Toutes les mesures publiees se
           font sur `F` ; `Fc` ne sert qu'a chiffrer l'ecart entre les deux. */
        const F = fctx.getImageData(x0, y0, w, h).data;
        const Fc = cctx.getImageData(x0, y0, w, h).data;
        const n = w * h;
        for (let p = 0; p < n; p++) {
          const i = p << 2;
          const e = Math.max(Math.abs(F[i] - Fc[i]), Math.abs(F[i + 1] - Fc[i + 1]),
            Math.abs(F[i + 2] - Fc[i + 2]), Math.abs(F[i + 3] - Fc[i + 3]));
          if (e > devMax) devMax = e;
        }
        devN += n;
        let total = 0, vis = 0;
        let ix0 = 1e9, iy0 = 1e9, ix1 = -1, iy1 = -1;
        /* la SECONDE borne du pave : le corps plein seul, sans le liseré. */
        let kx0 = 1e9, ky0 = 1e9, kx1 = -1, ky1 = -1;
        /* LES DEUX POINTS QUI PRODUISENT LE RAPPORT SONT GARDES AVEC LEURS
           COORDONNEES. Publier deux luminances laisse encore le re-mesureur
           chercher OU les prendre : sur un fond en degrade il tombe sur un
           autre nombre et conclut au mensonge — c'est mot pour mot le reproche
           du second critique (« ne correspond a aucune lecture WCAG directe des
           deux couleurs : je mesure 5,50:1 »). Un pixel nomme se verifie a la
           pipette, sur le fichier livre, sans nous croire sur parole. */
        const inkL = [], inkP = [];
        const exact = slot.opacity >= 99.5;
        const A = new Uint8Array(n);        /* 0 rien · 1 anticrenelage · 2 corps */
        for (let p = 0; p < n; p++) {
          const a = S[(p << 2) + 3];
          A[p] = a >= AUDIT_ALPHA ? 2 : (a > 0 ? 1 : 0);
        }
        /* LA BBOX D'ENCRE SE MESURE SUR TOUTE L'ENCRE, anticrenelage compris.
           Un critique qui remesure le PNG avec un masque de couleur attrape
           les bords adoucis des glyphes ; une bbox limitee aux pixels PLEINS
           rendait 645 x 188 la ou l'encre fait 647 x 193 — un chiffre plus
           flatteur que le fichier, donc faux. Le CORPS des glyphes (alpha
           plein) reste le seul juge du masquage et du contraste : lui seul
           permet d'affirmer une couleur. */
        for (let p = 0; p < n; p++) {
          if (!A[p]) continue;
          const px = p % w, py = (p / w) | 0;
          if (px < ix0) ix0 = px; if (px > ix1) ix1 = px;
          if (py < iy0) iy0 = py; if (py > iy1) iy1 = py;
          if (A[p] !== 2) continue;
          if (px < kx0) kx0 = px; if (px > kx1) kx1 = px;
          if (py < ky0) ky0 = py; if (py > ky1) ky1 = py;
        }
        for (let p = 0; p < n; p++) {
          if (A[p] !== 2) continue;
          const i = p << 2;
          total++;
          const ok = Math.abs(F[i] - S[i]) <= AUDIT_TOL
            && Math.abs(F[i + 1] - S[i + 1]) <= AUDIT_TOL
            && Math.abs(F[i + 2] - S[i + 2]) <= AUDIT_TOL;
          if (ok || !exact) { vis++; inkL.push(lumOf(F[i], F[i + 1], F[i + 2])); inkP.push(p); }
        }
        /* LE FOND, C'EST CE QUI TOUCHE LA LETTRE. Un echantillon pris a 40 px
           d'un glyphe n'est pas le fond de ce glyphe : on ne garde que les
           pixels a moins de BG_NEAR px d'un corps de glyphe, sur la meme
           ligne. Sans cette borne, le « pire fond » etait souvent un coin de
           la fenetre de lecture ou aucune lettre ne se pose. */
        const near = new Uint8Array(n);
        for (let y = 0; y < h; y++) {
          const o = y * w;
          let d = 1e9;
          for (let x = 0; x < w; x++) { const p = o + x; if (A[p] === 2) d = 0; else d++; if (d <= BG_NEAR) near[p] = 1; }
          d = 1e9;
          for (let x = w - 1; x >= 0; x--) { const p = o + x; if (A[p] === 2) d = 0; else d++; if (d <= BG_NEAR) near[p] = 1; }
        }
        const bgL = [], bgP = [];
        for (let p = 0; p < n && bgL.length < BG_MAX; p++) {
          if (A[p] !== 0 || !near[p]) continue;
          const px = p % w;
          if (px === 0 || px === w - 1 || p < w || p >= n - w) continue;
          if (A[p - 1] || A[p + 1] || A[p - w] || A[p + w]) continue;
          const i = p << 2;
          bgL.push(lumOf(F[i], F[i + 1], F[i + 2]));
          bgP.push(p);
        }
        /* la MEDIANE de l'encre, et le pixel qui la porte : la valeur affichee
           doit exister quelque part dans le fichier, pas seulement dans un
           tableau. */
        const iL = pct(inkL, 0.5);
        const inkPt = (iL == null) ? null
          : xy(inkP[nearestIdx(inkL, iL)], x0, y0, w);
        /* UN CONTOUR EST UNE REPONSE AU CONTRASTE, PAS UN DETAIL. Un chiffre
           creme cercle de noir se lit sur un fond creme : la lettre se detache
           de son contour, et le contour se detache du fond. Mesurer seulement
           creme-contre-creme aurait condamne un texte parfaitement lisible.
           On retient donc, pour chaque pixel de fond, le meilleur des deux
           chemins : l'encre contre le fond, ou l'encre contre le contour ET le
           contour contre le fond. */
        const strokePx = pxOfPt(slot.outline, g);
        const oL = strokePx >= 0.6 ? lumOf(
          parseInt(slot.outline_color.slice(1, 3), 16),
          parseInt(slot.outline_color.slice(3, 5), 16),
          parseInt(slot.outline_color.slice(5, 7), 16)) : null;
        /* On garde la LUMINANCE DU FOND qui produit le chiffre annonce, pas
           seulement le chiffre : un contraste sans ses deux termes ne se
           recalcule pas, et un imprimeur qui recompte autrement conclut qu'on
           a menti. Le releve donne donc (L encre, L fond) a cote du rapport —
           n'importe qui refait (L1+0,05)/(L2+0,05) a la main. */
        let cMed = null, cMin = null, bgAt = null, lumA = null, lumB = null, via = "direct";
        let pair = "ink_bg";
        /* ── LE RAPPORT DIRECT, TOUJOURS CALCULE ───────────────────────────
           Quand un contour fait le relais, le chiffre publie n'est plus celui
           qu'un outil WCAG rendra : lui ne connait pas le relais, il divise
           l'encre par le fond et rien d'autre. MESURE sur le fichier livre de
           la carte de demonstration : « Attaque » sort a 4,18:1 par le
           contour et a 2,90:1 encre contre fond — sous le seuil de 3:1 de son
           corps. Publier le seul 4,18 laissait le re-mesureur trouver 2,90 et
           conclure au mensonge. On calcule donc les DEUX, sur la meme
           population de fonds et au meme centile, et le releve donne les deux
           des que le relais sert. */
        let cDir = null, dirBg = null, dirA = null, dirB = null, dirPt = null;
        let bgPt = null;
        if (iL != null && bgL.length) {
          const rs = bgL.map((b, bi) => {
            /* le CHEMIN retenu est garde avec le chiffre : quand c'est le
               contour qui fait le relais, la division a ecrire n'est pas
               encre/fond mais contour/fond — et un panneau qui affiche
               l'autre est un panneau qu'on ne peut pas recalculer. */
            const o = { r: wcag(iL, b), b: b, p: bgP[bi], va: iL, vb: b,
              via: "direct", pair: "ink_bg" };
            if (oL != null) {
              const legInk = wcag(iL, oL), legBg = wcag(oL, b);
              const relay = Math.min(legInk, legBg);
              if (relay > o.r) {
                o.r = relay; o.via = "contour";
                /* la PAIRE retenue est nommee : sans elle, « (0,1872 + 0,05) /
                   (0,0068 + 0,05) » laisse croire que 0,1872 est l'encre alors
                   que c'est le fond, et le pixel publie a cote devient
                   trompeur. */
                if (legBg <= legInk) { o.va = oL; o.vb = b; o.pair = "outline_bg"; }
                else { o.va = iL; o.vb = oL; o.pair = "ink_outline"; }
              }
            }
            return o;
          });
          rs.sort((x, y) => x.r - y.r);
          const at = (p) => rs[clamp(Math.round((rs.length - 1) * p), 0, rs.length - 1)];
          cMed = at(0.5).r;
          const w5 = at(0.05);
          bgAt = w5.b; via = w5.via; bgPt = xy(w5.p, x0, y0, w); pair = w5.pair;
          /* LE RAPPORT AFFICHE EST CELUI DES LUMINANCES AFFICHEES. Le panneau
             ecrit les deux luminances a quatre decimales et le rapport a deux ;
             tant que le rapport se calculait sur les valeurs PLEINES, refaire
             la division a la main donnait parfois 0,01 d'ecart (releve dans
             l'app : « Artiste » 5,27 affiche pour 0,4950/0,0533 qui donne
             5,28 ; « Ambiance » 7,99 pour un calcul a 7,98). Un lecteur qui
             recompte et ne retombe pas sur le chiffre conclut que le panneau
             ment — et il a raison de le conclure. On arrondit donc D'ABORD,
             puis on divise : ce qui est ecrit se refait exactement. */
          const r4 = (v) => Math.round(v * 1e4) / 1e4;
          lumA = r4(w5.va); lumB = r4(w5.vb);
          cMin = wcag(lumA, lumB);
          /* MEME POPULATION, MEME CENTILE, SANS LE RELAIS : c'est le nombre
             que rend une pipette WCAG posee sur le fichier. */
          const ds = bgL.map((b, bi) => ({ r: wcag(iL, b), b: b, p: bgP[bi] }));
          ds.sort((x, y) => x.r - y.r);
          const d5 = ds[clamp(Math.round((ds.length - 1) * 0.05), 0, ds.length - 1)];
          dirA = r4(iL); dirB = r4(d5.b); dirBg = d5.b;
          dirPt = xy(d5.p, x0, y0, w);
          cDir = wcag(dirA, dirB);
        }
        /* ── LES BLANCS-MOTS, RELUS SUR L'ENCRE ────────────────────────────
           Le releve donne jusqu'ici l'AVANCE : l'espace naturel de la fonte
           plus l'etirement de justification. Un critique qui remesure le
           bitmap ne mesure pas cela — il mesure le VIDE entre deux amas
           d'encre, qui vaut l'avance moins les approches des deux glyphes
           voisins, et il trouve un autre nombre. Les deux sont justes ; un
           seul etait affiche, et l'ecart passait pour un mensonge. On mesure
           donc aussi le blanc d'encre a encre, sur le masque du slot, et on
           affiche les deux.
           REGLE DE TRI, ECRITE POUR ETRE REFAITE : sur une ligne qui porte k
           espaces, les k plus grands vides sont les blancs-mots ; les autres
           sont des ecarts entre lettres. Perimetre identique a celui de
           l'avance affichee (lignes justifiees portant au moins un blanc),
           sinon les deux chiffres ne parleraient pas du meme endroit. */
        /* ── L'IRREGULARITE DES FINS DE LIGNE, RELUE SUR L'ENCRE ───────────
           « Fins de ligne 0 % d'irregularite » est vrai du TRACE et faux du
           BITMAP : une ligne justifiee occupe exactement la justification par
           construction, donc le chiffre du modele vaut zero quoi qu'il
           arrive. L'encre, elle, s'arrete ou s'arrete le dernier glyphe, et
           son approche droite depend du caractere : MESURE sur le fichier
           livre, les six lignes justifiees de l'encadre finissent a x = 729,
           730, 731 et 732 — 3 px d'ecart, soit 0,4 %, pas 0. Un chiffre qui
           ne survit pas au re-mesurage vaut moins que pas de chiffre : on
           mesure donc le bord d'encre de chaque ligne justifiee et on publie
           l'ecart a cote du zero du modele. */
        let wsInk = null, edgeInk = null;
        const spaces = m.lines.map((l) => (l.match(/ /g) || []).length);
        if (m.lines.length && spaces.some((k) => k > 0)) {
          const bands = [];
          let s0 = -1;
          for (let y = 0; y < h; y++) {
            let on = 0;
            for (let x = 0; x < w; x++) { if (A[y * w + x]) { on = 1; break; } }
            if (on && s0 < 0) s0 = y;
            else if (!on && s0 >= 0) { bands.push([s0, y - 1]); s0 = -1; }
          }
          if (s0 >= 0) bands.push([s0, h - 1]);
          /* une bande par ligne, sinon on ne sait pas laquelle est laquelle et
             on se tait : un chiffre mal apparie serait pire que pas de chiffre. */
          if (bands.length === m.lines.length) {
            let lo = null, hi = null, nb = 0;
            let loK = null, hiK = null;
            const rEdge = [], lEdge = [], rEdgeK = [];
            bands.forEach((bd, i) => {
              const k = spaces[i];
              if (!k || m.ends[i]) return;
              const gs = [], gsK = [];
              let run = 0, seen = false, first = -1, last = -1;
              let runK = 0, seenK = false, lastK = -1;
              for (let x = 0; x < w; x++) {
                let on = 0, onK = 0;
                for (let y = bd[0]; y <= bd[1]; y++) {
                  const v = A[y * w + x];
                  if (v) { on = 1; if (v === 2) { onK = 1; break; } }
                }
                if (on) {
                  if (first < 0) first = x;
                  last = x;
                  if (seen && run) gs.push(run);
                  run = 0; seen = true;
                } else if (seen) run++;
                /* LA MEME MESURE, AU SEUIL DE L'AUTRE. Celui qui remesure le
                   PNG avec un masque de couleur ne voit que le corps plein :
                   il trouve des blancs PLUS LARGES et des bords decales d'un
                   pixel. Publier une seule des deux bornes, c'etait promettre
                   un nombre que la moitie des re-mesurages ne retrouve pas. */
                if (onK) {
                  lastK = x;
                  if (seenK && runK) gsK.push(runK);
                  runK = 0; seenK = true;
                } else if (seenK) runK++;
              }
              if (first >= 0) { lEdge.push(x0 + first); rEdge.push(x0 + last); }
              if (lastK >= 0) rEdgeK.push(x0 + lastK);
              gs.sort((p, q) => q - p);
              gsK.sort((p, q) => q - p);
              const topK = gsK.slice(0, k);
              if (topK.length) {
                const mnK = Math.min.apply(null, topK), mxK = Math.max.apply(null, topK);
                if (loK == null || mnK < loK) loK = mnK;
                if (hiK == null || mxK > hiK) hiK = mxK;
              }
              const top = gs.slice(0, k);
              if (!top.length) return;
              nb += top.length;
              const mn = Math.min.apply(null, top), mx = Math.max.apply(null, top);
              if (lo == null || mn < lo) lo = mn;
              if (hi == null || mx > hi) hi = mx;
            });
            if (lo != null) wsInk = { lo: lo, hi: hi, n: nb, lo_core: loK, hi_core: hiK };
            if (rEdge.length > 1) {
              const rHi = Math.max.apply(null, rEdge), rLo = Math.min.apply(null, rEdge);
              const lHi = Math.max.apply(null, lEdge), lLo = Math.min.apply(null, lEdge);
              edgeInk = {
                n: rEdge.length, right: [rLo, rHi], left: [lLo, lHi],
                spread: rHi - rLo, left_spread: lHi - lLo,
                right_core: rEdgeK.length > 1
                  ? [Math.min.apply(null, rEdgeK), Math.max.apply(null, rEdgeK)] : null,
                spread_core: rEdgeK.length > 1
                  ? Math.max.apply(null, rEdgeK) - Math.min.apply(null, rEdgeK) : null,
                /* rapporte a la justification REELLEMENT occupee, la meme
                   grandeur que le 0 % du modele. */
                pct: (rHi > x0) ? (rHi - rLo) / Math.max(1, rHi - lLo) * 100 : 0,
              };
            }
          }
        }
        /* pose sur la mesure de mise en page elle-meme : le releve n'affiche ce
           chiffre que tant qu'il porte sur le rendu en cours — une remise en
           page efface `m`, donc efface le chiffre, au lieu d'en garder un vieux. */
        m.ws_ink = wsInk;
        m.edge_ink = edgeInk;
        const inkRect = (ix1 >= 0)
          ? [x0 + ix0, y0 + iy0, ix1 - ix0 + 1, iy1 - iy0 + 1] : null;
        const coreRect = (kx1 >= 0)
          ? [x0 + kx0, y0 + ky0, kx1 - kx0 + 1, ky1 - ky0 + 1] : null;
        const clipped = inkRect != null
          && (ix0 === 0 || iy0 === 0 || ix1 === w - 1 || iy1 === h - 1);
        /* L'OMBRE PORTEE, MESUREE A PART. Ce n'est pas de l'encre pleine —
           c'est un degrade — mais elle EXISTE dans le fichier livre : qui
           refait la mesure en soustrayant deux rendus la trouve, et sans ce
           chiffre il conclut que le pave annonce est trop petit. On la mesure
           donc, on la nomme, et on ne la confond pas avec les glyphes. */
        let halo = null, haloClear = null;
        if (slot.shadow > 0 || slot.shadow_dx || slot.shadow_dy) {
          sctx.setTransform(1, 0, 0, 1, 0, 0);
          sctx.clearRect(x0, y0, w, h);
          /* l'ombre GARDEE : c'est elle que cette passe mesure. */
          drawSlot(sctx, soloClone(slot, { shadow: true }), g, m);
          const S2 = sctx.getImageData(x0, y0, w, h).data;
          let hx0 = 1e9, hy0 = 1e9, hx1 = -1, hy1 = -1;
          for (let q = 0; q < n; q++) {
            if (!S2[(q << 2) + 3]) continue;
            const px = q % w, py = (q / w) | 0;
            if (px < hx0) hx0 = px; if (px > hx1) hx1 = px;
            if (py < hy0) hy0 = py; if (py > hy1) hy1 = py;
          }
          if (hx1 >= 0) {
            halo = [x0 + hx0, y0 + hy0, hx1 - hx0 + 1, hy1 - hy0 + 1];
            haloClear = Math.min(halo[0] - sr[0], halo[1] - sr[1],
              (sr[0] + sr[2]) - (halo[0] + halo[2]),
              (sr[1] + sr[3]) - (halo[1] + halo[3])) * 25.4 / g.dpi;
          }
        }
        let clear = null;
        if (inkRect) {
          clear = Math.min(inkRect[0] - sr[0], inkRect[1] - sr[1],
            (sr[0] + sr[2]) - (inkRect[0] + inkRect[2]),
            (sr[1] + sr[3]) - (inkRect[1] + inkRect[3])) * 25.4 / g.dpi;
        }
        rows.push({
          id: id, label: slot.label, empty: false, exact: exact,
          total: total, vis: vis, masked: total - vis,
          rate: total ? vis / total : 1,
          ink_px: inkRect, ink_core_px: coreRect, clear_mm: clear, clipped: clipped,
          halo_px: halo, halo_clear_mm: haloClear,
          contrast: cMed, contrast_min: cMin,
          contrast_direct: cDir, direct_a: dirA, direct_b: dirB, direct_bg: dirBg,
          ink_lum: iL, bg_lum: bgAt, bg_n: bgL.length,
          /* les deux pixels du fichier qui portent les deux luminances */
          ink_pt: inkPt, bg_pt: bgPt, direct_pt: dirPt, pair: pair,
          lum_a: lumA, lum_b: lumB, via: via, out_lum: oL,
          out_hex: (oL != null ? slot.outline_color : null),
          seuil: wcagSeuil(m.pt, slot.bold), pt: m.pt, bold: !!slot.bold,
        });
      });
      /* ── LA MARGE OPTIQUE PORTE SUR TOUTE L'ENCRE DU FICHIER ─────────────
         Le controle ne regardait que le corps des glyphes : un halo d'ombre
         passait a 0,17 mm du bord de la zone sure — mesure sur les octets du
         fichier livre — pendant que la ligne « Lisibilite » affichait une
         coche verte, alors que la marge optique DECLAREE par ce meme panneau
         vaut 0,50 mm. Un seuil qu'on affiche et qu'on ne fait pas respecter
         apprend a l'utilisateur a ignorer le controle. Le halo est de l'encre
         du fichier ; il compte. Et le seuil compare est celui qui est
         REGLE a l'ecran, pas une constante — sinon le chiffre du champ et le
         chiffre du verdict parlaient de deux choses. */
      const optMm = clamp(Number(CF.get("type.optical_mm", OPTICAL_MM_DEF)) || 0, 0, OPTICAL_MM_MAX);
      AUDIT = {
        stamp: stamp, side: MEAS_SIDE, card: CF.current(),
        canvas: [cw, ch], rows: rows, optical_mm: optMm,
        /* la PROVENANCE des chiffres : un PNG de tant d'octets, relu, et
           l'ecart mesure entre cette relecture et l'apercu. */
        file_bytes: file.bytes, file_dev: devMax, file_n: devN,
        masked: rows.filter((r) => !r.empty && r.exact && r.rate < SURV_MIN),
        empties: rows.filter((r) => r.empty),
        lowc: rows.filter((r) => !r.empty && r.contrast_min != null && r.contrast_min < r.seuil),
        /* le contour sauve la lecture, il ne sauve pas le chiffre : ces
           slots-la sont listes a part, en ambre, avec les deux rapports. */
        relayed: rows.filter((r) => !r.empty && r.via === "contour"
          && r.contrast_direct != null && r.contrast_direct < r.seuil),
        tight: rows.filter((r) => optMm > 0 && nearestClearMm(r) != null
          && nearestClearMm(r) < optMm),
      };
      AUDIT_DONE = stamp;
    } catch (e) {
      auditErr = String((e && e.message) || e);
      console.warn("cardforge/type: contrôle photométrique", e);
    } finally {
      IN_AUDIT = false;
      auditing = false;
    }
    renderList();
    renderProof();
    if (AUDIT_STAMP !== AUDIT_DONE) scheduleAudit();
  }
  function scheduleAudit() {
    clearTimeout(auditTimer);
    if (!CF.get("type.audit", true)) { AUDIT = null; return; }
    auditTimer = setTimeout(() => { runAudit().catch(() => { }); }, 650);
  }

  /* ═════════════════════════════════════════════════════════════════════════
     7ter. LE CONTROLE DE DEFINITION — 300 PUIS 600 DPI, SUR DES OCTETS PNG

     C'est le trou que le tour precedent a nomme en premier : « rien de ce que
     ce cote gagne n'est prouve ailleurs qu'a l'ecran ; la nettete du texte a
     300 puis a 600 DPI et la coherence entre l'apercu et le fichier livre
     restent a zero ». Un panneau qui compose bien mais ne peut pas montrer que
     sa composition survit au retracage a la definition d'impression n'a fait
     que la moitie du travail.

     Ce controle-ci recompose CHAQUE bloc a l'autre definition, encode les deux
     tirages en PNG, RELIT les octets, et publie quatre grandeurs :
       * le deplacement du pave d'encre, en MILLIMETRES (0 attendu) ;
       * le nombre de caracteres et de lignes posees (identique attendu) ;
       * le verdict de zone sure a chaque definition ;
       * la part d'anticrenelage dans le trace, a chaque definition.
     La derniere grandeur est celle qui separe un VRAI retracage d'un simple
     agrandissement, et elle ne se falsifie pas : quand on double la
     definition, l'aire d'un glyphe est multipliee par 4 tandis que son
     perimetre ne l'est que par 2, donc la part de liseré est DIVISEE PAR
     DEUX. Un bitmap agrandi garde la sienne (rapport 1,00). Le rapport publie
     dit donc, sur les octets, si le texte a ete redessine ou etire.
     ═════════════════════════════════════════════════════════════════════════ */
  let DEFC = null, defcBusy = false, defcErr = "";
  let defcTimer = null, defcTried = "";
  /* ── LE SEUIL N'EST PAS EN MILLIMETRES, IL EST EN PIXELS ────────────────
     Premiere version : « au-dela de 0,05 mm, le bloc a bouge ». MESURE sur la
     carte de demonstration : les neuf blocs sortaient a 0,042 / 0,085 / 0,127
     mm — c'est-a-dire EXACTEMENT 1, 2 et 3 pixels de la toile de 600 DPI,
     alors que le corps compose, le nombre de caracteres et le nombre de lignes
     etaient identiques au chiffre pres des deux cotes. Rien n'avait bouge : un
     cadre d'encre est un rectangle CALE SUR UNE GRILLE, et deux grilles
     differentes ne peuvent pas cerner le meme contour au meme endroit. Le
     seuil de 0,05 mm etait sous le pas de la grille la plus fine : il ne
     pouvait qu'allumer une alerte, toujours, sur n'importe quelle carte.
     Un voyant qui s'allume par construction n'apprend rien et use la
     vigilance. Le seuil se compte donc en pixels de la grille la PLUS
     GROSSIERE — deux, soit un pixel de battement par bord — et le panneau
     publie le pas de quantification a cote de l'ecart, pour qu'on voie que le
     chiffre est du bruit de grille et non un deplacement. */
  const DEFC_PX = 2;        /* pixels de la definition la plus grossiere */
  const DEFC_PT = 0.05;     /* points : au-dela, le corps compose a CHANGE */

  /* CE QUI PERIME UN RELEVE DE DEFINITION, c'est la MISE EN PAGE, pas le
     compteur de rendus. Indexer ce releve sur `AUDIT_STAMP` le rendait
     inaffichable : le controle dure plusieurs secondes, une police qui finit
     d'arriver redemande un rendu, le compteur avance, et un resultat juste
     sortait perime a la seconde ou il naissait. La cle porte donc les slots,
     les textes reellement poses, la geometrie et la face — tout ce qui
     changerait le resultat, et rien d'autre. */
  function defKey(g) {
    const card = CF.card(CF.current());
    return JSON.stringify([slots(), slots().map((s) => textOf(s, card)),
      g.fmt, g.dpi, g.bleed_mm, g.safe_mm, MEAS_SIDE]);
  }

  function altDpi(dpi) {
    const list = (CF.DPIS || []).filter((d) => d !== dpi);
    if (!list.length) return null;
    if (dpi !== 600 && list.indexOf(600) >= 0) return 600;
    if (list.indexOf(300) >= 0) return 300;
    return list[list.length - 1];
  }

  /* Encode une toile en PNG, RELIT les octets, et compte : corps plein,
     liseré, cadre d'encre. Aucun chiffre ne sort d'ici sans etre passe par un
     encodeur et un decodeur. */
  async function countPng(cv) {
    const f = await asFile(cv);
    const w = cv.width, h = cv.height;
    const D = f.ctx.getImageData(0, 0, w, h).data;
    let body = 0, edge = 0, bx0 = 1e9, by0 = 1e9, bx1 = -1, by1 = -1;
    for (let p = 0, n = w * h; p < n; p++) {
      const a = D[(p << 2) + 3];
      if (!a) continue;
      if (a >= AUDIT_ALPHA) body++; else edge++;
      const px = p % w, py = (p / w) | 0;
      if (px < bx0) bx0 = px; if (px > bx1) bx1 = px;
      if (py < by0) by0 = py; if (py > by1) by1 = py;
    }
    return {
      bytes: f.bytes, body: body, edge: edge,
      frac: (body + edge) ? edge / (body + edge) : null,
      bbox: bx1 < 0 ? null : [bx0, by0, bx1 - bx0 + 1, by1 - by0 + 1],
    };
  }

  /* ── LE TEMOIN ────────────────────────────────────────────────────────────
     « Un agrandissement rendrait 1,00 × » etait une AFFIRMATION, donc
     exactement ce que cette passe refuse. Le voici mesure : le tirage de
     depart est agrandi au facteur des deux definitions, encode en PNG, relu,
     et sa part de liseré est comptee de la meme main. Le lecteur n'a plus a
     nous croire sur ce que ferait un agrandissement — il lit ce qu'il a fait. */
  async function witnessUpscale(cv, k) {
    const w = Math.max(1, Math.round(cv.width * k));
    const h = Math.max(1, Math.round(cv.height * k));
    const up = document.createElement("canvas");
    up.width = w; up.height = h;
    const ux = up.getContext("2d", { willReadFrequently: true });
    ux.imageSmoothingEnabled = true;
    ux.drawImage(cv, 0, 0, w, h);
    return countPng(up);
  }

  /* Le tirage d'UN bloc a UNE definition, encode puis relu. Rien n'est compte
     sur la toile : `countPng` a fait le tour par les octets. */
  async function inkFile(gg, slot, text, witness) {
    const m = layoutSlot(fixCtx(), slot, gg, text);
    if (!String(text).length) return { m: m, empty: true };
    const grow = Math.ceil(m.sizePx * 0.75) + 6;
    const cw = gg.canvas_px[0], chh = gg.canvas_px[1];
    const x0 = clamp(Math.floor(m.ink[0] - grow), 0, cw - 1);
    const y0 = clamp(Math.floor(m.ink[1] - grow), 0, chh - 1);
    const x1 = clamp(Math.ceil(m.ink[0] + m.ink[2] + grow), 1, cw);
    const y1 = clamp(Math.ceil(m.ink[1] + m.ink[3] + grow), 1, chh);
    const w = Math.max(1, x1 - x0), h = Math.max(1, y1 - y0);
    const cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    const cx = cv.getContext("2d", { willReadFrequently: true });
    cx.translate(-x0, -y0);
    drawSlot(cx, soloClone(slot), gg, m);
    const f = await countPng(cv);
    const wit = (witness && witness > 1) ? await witnessUpscale(cv, witness) : null;
    if (!f.bbox) return { m: m, empty: true, bytes: f.bytes };
    const body = f.body, edge = f.edge;
    const bx0 = f.bbox[0], by0 = f.bbox[1];
    const k = 25.4 / gg.dpi;
    const px = [x0 + bx0, y0 + by0, f.bbox[2], f.bbox[3]];
    const sr = safeRectPx(gg);
    return {
      m: m, empty: false, bytes: f.bytes + (wit ? wit.bytes : 0),
      body: body, edge: edge, wit: wit,
      frac: (body + edge) ? edge / (body + edge) : 0,
      px: px,
      /* en millimetres DEPUIS LE COIN DE COUPE : la seule unite ou deux
         definitions se comparent sans conversion cachee. */
      mm: [(px[0] - gg.bleed_off_px[0]) * k, (px[1] - gg.bleed_off_px[1]) * k,
        px[2] * k, px[3] * k],
      inside: !anyOut(outsideBy(px, sr)),
      chars: m.chars, lines: m.lines.length, pt: m.pt,
      canvas: [cw, chh], dpi: gg.dpi,
    };
  }

  async function runDefCheck(auto) {
    if (defcBusy) return;
    const g = CF.geom();
    const alt = altDpi(g.dpi);
    if (alt == null) { defcErr = "une seule définition disponible"; renderProof(); return; }
    defcBusy = true; defcErr = "";
    /* AUTOMATIQUE = SILENCIEUX. Le voyant « occupé » du CORE appartient aux
       gestes de l'utilisateur ; le faire clignoter tout seul toutes les
       secondes aurait rendu le panneau inutilisable. Le clic, lui, garde son
       accusé de réception. */
    if (!auto) M.busy(true, "second tirage à " + alt + " DPI…");
    try {
      const gg = CF.geomOf(g.fmt, alt, g.bleed_mm, g.safe_mm, g.corner_mm);
      const card = CF.card(CF.current());
      /* LES CALQUES D'IMAGE SONT HORS SUJET ICI. Ce controle compare le meme
         BLOC compose a deux definitions pour prouver qu'aucun caractere ne se
         deplace ; une image, elle, est ré-échantillonnée par la toile — la
         comparer reviendrait a mesurer l'interpolation du navigateur, pas la
         stabilite de la mise en page. */
      const live = slots().filter((s) => s.on && !isImage(s)
        && (s.side === "both" || s.side === MEAS_SIDE));
      await ensureFonts(live.map((s) => s.font));
      const rows = [];
      const kUp = alt / g.dpi;
      /* le pas de la grille la plus grossiere : l'unite dans laquelle un
         cadre d'encre peut differer SANS que rien n'ait bouge. */
      const qmm = 25.4 / Math.min(g.dpi, alt);
      let bytesA = 0, bytesB = 0, bodyA = 0, edgeA = 0, bodyB = 0, edgeB = 0;
      let bodyW = 0, edgeW = 0;
      for (let i = 0; i < live.length; i++) {
        const slot = live[i];
        const text = textOf(slot, card);
        /* eslint-disable no-await-in-loop */
        const a = await inkFile(g, slot, text, kUp);
        const b = await inkFile(gg, slot, text);
        /* eslint-enable no-await-in-loop */
        bytesA += a.bytes || 0; bytesB += b.bytes || 0;
        if (a.empty || b.empty) {
          rows.push({ id: slot.id, label: slot.label, empty: true,
            only: a.empty !== b.empty });
          continue;
        }
        bodyA += a.body; edgeA += a.edge; bodyB += b.body; edgeB += b.edge;
        if (a.wit) { bodyW += a.wit.body; edgeW += a.wit.edge; }
        const d = [b.mm[0] - a.mm[0], b.mm[1] - a.mm[1], b.mm[2] - a.mm[2], b.mm[3] - a.mm[3]];
        const dmm = Math.max.apply(null, d.map(Math.abs));
        rows.push({
          id: slot.id, label: slot.label, empty: false,
          a: a, b: b,
          dmm: dmm, dpx: dmm / qmm,
          dpos: Math.max(Math.abs(d[0]), Math.abs(d[1])),
          ddim: Math.max(Math.abs(d[2]), Math.abs(d[3])),
          dchars: b.chars - a.chars, dlines: b.lines - a.lines,
          dpt: b.pt - a.pt,
          safe_a: a.inside, safe_b: b.inside,
          frac_a: a.frac, frac_b: b.frac,
        });
      }
      const vivants = rows.filter((r) => !r.empty);
      const worst = vivants.slice().sort((p, q) => q.dmm - p.dmm)[0] || null;
      DEFC = {
        key: defKey(g), dpi_a: g.dpi, dpi_b: alt, fmt: g.fmt,
        canvas_a: g.canvas_px.slice(), canvas_b: gg.canvas_px.slice(),
        rows: rows, worst: worst, qmm: qmm, dpi_min: Math.min(g.dpi, alt),
        bytes: bytesA + bytesB, n: vivants.length,
        moved: vivants.filter((r) => r.dpx > DEFC_PX),
        repts: vivants.filter((r) => Math.abs(r.dpt) > DEFC_PT),
        lost: vivants.filter((r) => r.dchars !== 0 || r.dlines !== 0),
        gone: rows.filter((r) => r.empty && r.only),
        out_b: vivants.filter((r) => !r.safe_b),
        out_a: vivants.filter((r) => !r.safe_a),
        frac_a: (bodyA + edgeA) ? edgeA / (bodyA + edgeA) : null,
        frac_b: (bodyB + edgeB) ? edgeB / (bodyB + edgeB) : null,
        frac_w: (bodyW + edgeW) ? edgeW / (bodyW + edgeW) : null,
        ink_a: bodyA + edgeA, ink_b: bodyB + edgeB, ink_w: bodyW + edgeW,
      };
      DEFC.ratio = (DEFC.frac_a && DEFC.frac_b != null) ? DEFC.frac_b / DEFC.frac_a : null;
      DEFC.ratio_w = (DEFC.frac_a && DEFC.frac_w != null) ? DEFC.frac_w / DEFC.frac_a : null;
    } catch (e) {
      defcErr = String((e && e.message) || e);
      DEFC = null;
      console.warn("cardforge/type: second tirage", e);
    } finally {
      defcBusy = false;
      if (!auto) M.busy(false);
    }
    renderProof();
  }

  /* ── L'EPREUVE PART TOUTE SEULE ────────────────────────────────────────────
     Le reproche du tour precedent, mot pour mot : « la mesure la plus chere du
     domaine est a un clic et n'a pas ete lancee avant de presenter la carte ».
     Un panneau qui affiche « non controle » a cote d'un bouton gris publie un
     trou, pas un releve. Le second tirage se declenche donc quand la mise en
     page se pose — apres le controle photometrique, qui est plus court et
     porte sur le fichier courant.

     TROIS GARDE-FOUS, parce qu'un travail automatique qui se relance tout seul
     est un lab qui chauffe :
       * la CLE de mise en page (`defKey`) : une epreuve deja faite pour cet
         etat ne se refait pas ;
       * `defcTried` : une epreuve qui a ECHOUE sur cet etat ne se retente pas
         en boucle — le bouton reste, pour la retenter a la main ;
       * un delai plus long que celui du releve, et jamais pendant un glisser
         ni pendant le controle photometrique. */
  function scheduleDefCheck() {
    clearTimeout(defcTimer);
    if (!HOST || dragState) return;
    if (altDpi(CF.geom().dpi) == null) return;
    defcTimer = setTimeout(() => {
      if (!HOST) return;
      /* les deux sorties DEFINITIVES d'abord : sans cela, la reprise
         ci-dessous serait une boucle sans fin quand rien ne change. */
      const k = defKey(CF.geom());
      if (DEFC && DEFC.key === k) return;      /* deja fait pour cet etat */
      if (defcTried === k) return;             /* deja tente, et il a echoue */
      if (defcBusy || auditing || IN_AUDIT || dragState) { scheduleDefCheck(); return; }
      defcTried = k;
      runDefCheck(true).catch(() => { });
    }, 1400);
  }

  /* ── LE MEME CONTROLE, MAIS SUR TOUTE LA SERIE ─────────────────────────
     L'ajustement automatique est bon et il est OPAQUE : sur 200 cartes
     importees, les titres n'ont pas tous le meme corps et rien ne le montre au
     niveau du deck. Ici on remet en page CHAQUE carte (sans dessiner) et on
     rend l'etendue reelle : de tel corps a tel corps, tant de cartes au corps
     mini, tant de caracteres supprimes — zero, et mesure carte par carte. */
  function runSeries() {
    const cards = CF.cards() || [];
    const g = CF.geom();
    /* LES CALQUES D'IMAGE SORTENT ICI AUSSI. Ce contrôle remet en page CHAQUE
       carte pour rendre l'étendue des corps composés ; un calque d'image n'a
       pas de corps, et il serait compté « vide » sur les 200 cartes — un
       compteur de défauts inventés, exactement ce que cette section refuse. */
    const a = slots().filter((s) => s.on && !isImage(s));
    if (!a.length) { SERIES = null; return; }
    const cv = document.createElement("canvas");
    cv.width = 8; cv.height = 8;
    const ctx = cv.getContext("2d");
    const per = {};
    let cut = 0, over = 0, empty = 0, under = 0, srcn = 0, posed = 0;
    const list = cards.length ? cards : [CF.card(CF.current())];
    list.forEach((cd) => {
      a.forEach((s) => {
        const t = textOf(s, cd);
        const m = layoutSlot(ctx, s, g, t);
        const e = per[s.id] || (per[s.id] = { label: s.label, lo: 1e9, hi: -1e9, min: 0, n: 0, under: 0 });
        if (!String(t).length) { empty++; return; }
        e.n++;
        e.lo = Math.min(e.lo, m.pt); e.hi = Math.max(e.hi, m.pt);
        if (m.pt <= s.min_pt + 0.01 && m.pt < s.size_pt - 0.005) e.min++;
        /* LE PLANCHER, CARTE PAR CARTE. Un titre court passe a 14 pt et un
           titre long tombe a 9 : c'est justement sur un deck entier que
           l'ajustement automatique devient invisible. */
        if (m.under_read) { e.under++; under++; }
        cut += m.cut;
        /* les deux totaux qui font l'invariant, additionnes carte par carte :
           c'est leur EGALITE qui se lit au releve, pas un zero. */
        srcn += m.srcn; posed += m.posed;
        if (m.over) over++;
      });
    });
    SERIES = { n: list.length, per: per, cut: cut, over: over, empty: empty, under: under,
      srcn: srcn, posed: posed };
  }

  function renderAll() {
    if (!HOST) return;
    /* pendant un glisser, on ne reconstruit que ce qui bouge : refaire
       l'inspecteur a chaque frame volerait le focus et couterait cher. */
    if (dragState) { renderList(); paintOverlay(); return; }
    renderList();
    renderInsp();
    renderProof();
    const c = HOST.querySelector(".cf-type-count");
    /* meme regle que le releve : la barre ne dit « vérifiées » que lorsque les
       chasses ont ete relues une par une ; sinon elle dit « servies », qui est
       ce que le catalogue prouve. */
    const fpb = fontProof();
    if (c) {
      /* LE COMPTE QUI VAUT QUELQUE CHOSE. « 23 polices » comptait des
         fichiers ; ce qui interesse un jeu francais, c'est combien d'entre
         elles savent ecrire « Créature ». Le chiffre est lu dans la table
         cmap de chaque fichier, au backend. Hors ligne, il n'est pas affiche
         du tout — on ne remplace pas une mesure absente par un optimisme. */
      const fr = frCount();
      c.textContent = slots().length + " blocs · " + fpb.served + " polices"
        + (fpb.dist >= fpb.served ? ", chasses relues" : "")
        + (fr.unk >= fr.n ? "" : " · " + fr.ok + " en français");
    }
    const bx = HOST.querySelector(".cf-type-boxes");
    if (bx) bx.classList.toggle("active", CF.get("type.show_boxes", true));
    const au = HOST.querySelector(".cf-type-audit");
    if (au) au.classList.toggle("active", CF.get("type.audit", true));
    const ov = HOST.querySelector(".cf-type-optv");
    if (ov && document.activeElement !== ov) ov.value = nv(CF.get("type.optical_mm", OPTICAL_MM_DEF));
    const rf = HOST.querySelector(".cf-type-refit");
    if (rf) {
      const was = CF.get("type.fit_rect", []), now = safeRectMm(CF.geom());
      const dif = was && was.length === 4 && (Math.abs(was[2] - now[2]) > 0.02 || Math.abs(was[3] - now[3]) > 0.02);
      rf.classList.toggle("hidden", !dif);
      if (dif) rf.textContent = "Réadapter à " + fx(now[2], 0) + " x " + fx(now[3], 0) + " mm";
    }
    paintOverlay();
  }

  /* ═════════════════════════════════════════════════════════════════════════
     8. CALQUE D'EDITION — sur l'apercu, JAMAIS dans le fichier
     ═════════════════════════════════════════════════════════════════════════ */
  const HANDLES = [["nw", 0, 0], ["n", 0.5, 0], ["ne", 1, 0], ["e", 1, 0.5],
    ["se", 1, 1], ["s", 0.5, 1], ["sw", 0, 1], ["w", 0, 0.5]];

  function buildOverlay() {
    OV = document.createElement("div");
    OV.className = "cf-type cf-type-ov";
    document.body.appendChild(OV);
    OV.addEventListener("pointerdown", onOvDown);
    syncOverlay();
  }
  function stageCanvas() { return document.querySelector(".stage-canvas"); }
  /* LE PANNEAU EST-IL DEVANT ? Deux surfaces s'en servent, pour deux raisons :
     le calque d'edition (qui exige EN PLUS que les cadres soient demandes) et
     le collage d'image (qui n'a rien a voir avec les cadres — coller dans un
     panneau qu'on ne voit pas serait le vrai defaut). */
  function panelOn() {
    return !!(PANEL && PANEL.classList.contains("on"));
  }
  function visible() {
    return !!(panelOn() && CF.get("type.show_boxes", true));
  }
  function syncOverlay() {
    if (!OV) return;
    const cv = stageCanvas();
    if (!cv || !visible()) { OV.classList.add("hidden"); return; }
    const r = cv.getBoundingClientRect();
    if (!r.width || !r.height) { OV.classList.add("hidden"); return; }
    OV.classList.remove("hidden");
    OV.style.left = r.left + "px";
    OV.style.top = r.top + "px";
    OV.style.width = r.width + "px";
    OV.style.height = r.height + "px";
    paintOverlay();
  }
  function ovScale() {
    const cv = stageCanvas(), g = CF.geom();
    if (!cv) return 1;
    const r = cv.getBoundingClientRect();
    return r.width / g.canvas_px[0];
  }
  /* `liveId`/`liveBox` : pendant un geste, la boite EN COURS DE GLISSE est
     substituee localement — feedback immediat (spec 9.6-2), sans attendre le
     patch coalesce au rAF ni le repaint complet de la carte qui le suit.
     Appel par defaut (sans argument) : inchange, lit le document. */
  function paintOverlay(liveId, liveBox) {
    if (!OV || OV.classList.contains("hidden")) return;
    const g = CF.geom(), k = ovScale(), sel = selId(), side = MEAS_SIDE;
    const sr = safeRectPx(g);
    OV.innerHTML = slots().filter((s) => s.on && (s.side === "both" || s.side === side)).map((s) => {
      const live = (liveId && s.id === liveId) ? Object.assign({}, s, { box: liveBox }) : s;
      const b = boxPx(live, g), m = MEAS[s.id];
      const outSafe = m && anyOut(outsideBy(m.ink, sr));
      const bad = m && (m.over || outSafe);
      /* LE LISERE D'ALERTE EST ICI, PAS DANS LA TOILE : ce calque est du DOM
         pose sur l'apercu, rien de ce qu'il montre ne peut partir dans un PNG
         ni dans un PDF. Un cadre d'alerte peint par le painter, si. */
      const why = !bad ? "" : (m.over
        ? " · " + m.over_chars + " car. hors cadre"
        : " · entame la marge du format");
      const st = "left:" + (b[0] * k) + "px;top:" + (b[1] * k) + "px;width:" + (b[2] * k) + "px;height:" + (b[3] * k) + "px";
      /* LE CADENAS SE VOIT SUR LA SCENE, pas seulement dans la liste : un
         glisser refusé sans marque à l'endroit où la main appuie se lit comme
         une panne. La classe change le trait de la boîte et le curseur des
         poignées ; le glyphe le dit en toutes lettres dans l'étiquette. */
      /* LE CALQUE D'EDITION NE PEINT AUCUN CONTENU — il ne pose que des
         boîtes, des poignées et une étiquette : un calque d'image s'y montre
         donc exactement comme un bloc de texte, et c'est voulu (on y déplace
         une boîte, pas une image). Seule l'étiquette gagne le pictogramme de
         nature, pour que deux boîtes superposées se distinguent au survol. */
      let h = '<div class="cf-type-hbox' + (s.id === sel ? " on" : "") + (bad ? " bad" : "")
        + (s.lock ? " lock" : "")
        + '" data-id="' + esc(s.id) + '" style="' + st + '">'
        + '<span class="cf-type-htag">' + (s.lock ? "&#128274; " : "")
        + (isImage(s) ? "&#128444; " : "") + esc(s.label) + why + '</span>';
      if (s.id === sel) {
        h += HANDLES.map((hd) => '<i class="cf-type-hh cf-type-h-' + hd[0] + '" data-h="' + hd[0] + '"></i>').join("");
      }
      return h + "</div>";
    }).join("");
  }
  function onOvDown(e) {
    /* un second pointeur (tactile multi-doigts, desormais possible —
       touch-action: none l'autorise sur cette surface) pendant un geste deja
       en cours : ignore, plutot qu'ecraser dragState et changer la selection
       (mpatch ci-dessous) au milieu du glisser en cours. `isPrimary`, pas un
       garde d'etat (`if (dragState) return;`, la version d'origine) : ICI,
       dragState est pose AVANT le setPointerCapture protege par try/catch —
       si la capture leve ET que le relachement arrive HORS d'une boite (OV
       est pointer-events:none en dehors), onOvUp (le seul point qui remet
       dragState a null) ne serait JAMAIS appele : le calque se coincerait
       DEFINITIVEMENT, tout glisser futur silencieusement refuse jusqu'au
       rechargement. `isPrimary` se lit sur l'EVENEMENT, jamais sur un etat
       qui pourrait rester coince (revue 7bis, re-revue, item 1). */
    if (!e.isPrimary) return;
    const hb = e.target.closest(".cf-type-hbox");
    if (!hb) return;
    const id = hb.dataset.id;
    if (id !== selId()) { mpatch({ sel: id }); renderAll(); }
    const s = slots().filter((x) => x.id === id)[0];
    if (!s) return;
    /* La SELECTION vient d'avoir lieu (juste au-dessus) et reste libre sur un
       bloc verrouille — c'est par elle qu'on atteint le panneau. Le
       GESTE, lui, ne demarre pas : on sort AVANT pushUndo et AVANT de brancher
       pointermove, si bien qu'il n'y a ni entree d'annulation a reprendre ni
       ecouteur a defaire. Un geste joue puis annule aurait laisse les deux. */
    if (s.lock) return;   /* VERROU : aucun geste ne demarre */
    const hd = e.target.closest(".cf-type-hh");
    pushUndo();
    dragState = {
      id: id, box: s.box.slice(), x0: e.clientX, y0: e.clientY,
      k: ovScale(), dpi: CF.geom().dpi, h: hd ? hd.dataset.h : null, moved: false,
    };
    /* la capture est un CONFORT (le pointeur peut sortir de la carte pendant
       le glisser), pas une condition : un pointerId inconnu la fait lever, et
       une exception ici tuerait le branchement des ecouteurs juste dessous —
       le glisser ne demarrerait jamais. */
    try { OV.setPointerCapture(e.pointerId); } catch (err) { /* pointeur synthetique */ }
    OV.addEventListener("pointermove", onOvMove);
    OV.addEventListener("pointerup", onOvUp);
    OV.addEventListener("pointercancel", onOvUp);
    e.preventDefault();
  }
  let dragRaf = 0;
  /* repli setTimeout si rAF est absent, annulation SYMETRIQUE (le meme
     drapeau sert a programmer et a annuler — cancelAnimationFrame sur un
     identifiant de setTimeout ne fait rien, autre registre). Meme patron
     que core.js:158 et les trois autres surfaces de glisse du labo,
     reproduit ICI en local pour l'uniformite (revue 7bis, item 4b). */
  const hasRAF = typeof requestAnimationFrame === "function";
  const scheduleFrame = (fn) => (hasRAF ? requestAnimationFrame(fn) : setTimeout(fn, 16));
  const cancelFrame = (id) => { if (hasRAF) cancelAnimationFrame(id); else clearTimeout(id); };
  function onOvMove(e) {
    if (!dragState) return;
    const g = CF.geom();
    const mmPerPx = 25.4 / g.dpi / dragState.k;   /* px ecran -> mm */
    let dx = (e.clientX - dragState.x0) * mmPerPx;
    let dy = (e.clientY - dragState.y0) * mmPerPx;
    if (!e.altKey) { dx = Math.round(dx / SNAP_MM) * SNAP_MM; dy = Math.round(dy / SNAP_MM) * SNAP_MM; }
    const b = dragState.box.slice();
    const h = dragState.h;
    let nb;
    if (!h) nb = [b[0] + dx, b[1] + dy, b[2], b[3]];
    else {
      let x = b[0], y = b[1], w = b[2], ht = b[3];
      if (h.indexOf("w") >= 0) { x = b[0] + dx; w = b[2] - dx; }
      if (h.indexOf("e") >= 0) { w = b[2] + dx; }
      if (h.indexOf("n") >= 0) { y = b[1] + dy; ht = b[3] - dy; }
      if (h.indexOf("s") >= 0) { ht = b[3] + dy; }
      if (w < MIN_BOX_MM) { w = MIN_BOX_MM; if (h.indexOf("w") >= 0) x = b[0] + b[2] - MIN_BOX_MM; }
      if (ht < MIN_BOX_MM) { ht = MIN_BOX_MM; if (h.indexOf("n") >= 0) y = b[1] + b[3] - MIN_BOX_MM; }
      nb = [x, y, w, ht];
    }
    dragState.moved = true;
    dragState.next = nb.map((v) => Math.round(v * 1e3) / 1e3);
    /* retour local immediat (spec 9.6-2) : le calque suit CHAQUE evenement —
       bon marche, c'est juste le DOM du calque, pas un repaint de carte. */
    paintOverlay(dragState.id, dragState.next);
    if (dragRaf) return;
    dragRaf = scheduleFrame(() => {
      dragRaf = 0;
      if (dragState && dragState.next) {
        patchSlot(dragState.id, { box: dragState.next }, true);
        /* vide APRES application : sans ca, onOvUp (ci-dessous) trouvait
           encore un dragState.next non nul quand ce rAF avait deja fini son
           travail avant le relachement, et repatchait EN DOUBLE la meme
           boite, identique, a chaque fin de glisse de plus d'une frame
           (revue 7bis, item 4a — inoffensif mais gaspille un patch complet).
           dragState.moved, lui, ne bouge pas : la decision UNDO.pop() plus
           bas en depend toujours. */
        dragState.next = null;
      }
    });
  }
  function onOvUp() {
    OV.removeEventListener("pointermove", onOvMove);
    OV.removeEventListener("pointerup", onOvUp);
    OV.removeEventListener("pointercancel", onOvUp);
    /* etat FINAL exact au relachement (spec 9.6-1) : un dragRaf encore en
       attente ICI (le dernier pointermove est arrive a moins d'une frame du
       relachement) perdait sinon la toute derniere position — dragState
       redevenait null AVANT que le rAF ne s'execute, et son garde
       `if (dragState && dragState.next)` avalait le patch en silence. */
    if (dragRaf) { cancelFrame(dragRaf); dragRaf = 0; }
    if (dragState && dragState.next) { patchSlot(dragState.id, { box: dragState.next }, true); }
    if (dragState && !dragState.moved) UNDO.pop();
    dragState = null;
    renderAll();
  }

  /* ── clavier ───────────────────────────────────────────────────────────── */
  function onKey(e) {
    if (!PANEL || !PANEL.classList.contains("on")) return;
    const t = e.target;
    const inField = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA"
      || t.tagName === "SELECT" || t.isContentEditable);
    const ctrl = e.ctrlKey || e.metaKey;
    if (ctrl && (e.key === "z" || e.key === "Z")) { e.preventDefault(); e.shiftKey ? redo() : undo(); return; }
    if (ctrl && (e.key === "y" || e.key === "Y")) { e.preventDefault(); redo(); return; }
    if (inField) return;
    if (ctrl && (e.key === "d" || e.key === "D")) { e.preventDefault(); dupSlot(); return; }
    const s = selSlot();
    if (!s) return;
    if (e.key === "Delete" || e.key === "Backspace") {
      e.preventDefault();
      /* DIT, pas avale : effacer est un acte dont le refus silencieux se lit
         comme une touche morte. (Les fleches, elles, se repetent : une
         infobulle par pression noierait l'ecran — leur refus se lit sur le
         cadenas de la boite, qui est sous les yeux.) */
      if (s.lock) { M.toast("bloc verrouillé — ouvrez le cadenas pour le supprimer", true); return; }
      delSlot(s.id);
      return;
    }
    if (e.key === "Escape") { closeFontPicker(); return; }
    const d = e.shiftKey ? NUDGE_FINE_MM : NUDGE_MM;
    const map = { ArrowLeft: [-d, 0], ArrowRight: [d, 0], ArrowUp: [0, -d], ArrowDown: [0, d] };
    const mv = map[e.key];
    if (!mv) return;
    /* preventDefault AVANT le garde : la fleche etait destinee au bloc, pas a
       la page. Refuser le deplacement ET laisser defiler l'ecran aurait fait
       deux surprises au lieu d'une. */
    e.preventDefault();
    if (s.lock) return;   /* VERROU : ni fleche ni Alt+fleche */
    const b = s.box.slice();
    if (e.altKey) { b[2] = Math.max(MIN_BOX_MM, b[2] + mv[0]); b[3] = Math.max(MIN_BOX_MM, b[3] + mv[1]); }
    else { b[0] += mv[0]; b[1] += mv[1]; }
    patchSlot(s.id, { box: b.map((v) => Math.round(v * 1e3) / 1e3) });
    renderAll();
  }
})();
