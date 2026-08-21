"use strict";
/* ═══════════════════════════════════════════════════════════════════════════
   Card Forge — piece 09 · Forge 3D   [P9]
   Proprietaire exclusif de : doc.forge3d · AUCUN z (ce module ne peint pas) ·
   /api/cards/<did>/forge3d/* · prefixe DOM cf-forge3d-
   feuille : css/mod-forge3d.css (tout selecteur y contient .cf-forge3d)

   Export par couches (phase 1) + l'ecran du graphe (phase 2a) : liste de
   noeuds de traitement (un rang par couche livree), construction du graphe
   100 % GRATUIT (POST build3d), apercu REEL dans <model-viewer> (le fichier
   livre, jamais un rendu invente), capture d'apercu figee cote client (POST
   preview/<art>), bordereau qui peint UNIQUEMENT la reponse mesuree — jamais
   l'intention envoyee. Ce module n'a AUCUN painter : il lit le rendu, il n'y
   dessine jamais.

   Phase 2b — LES CHAINES ET L'ARGENT. Un rang devient une CHAINE
   couche -> traitement -> [matiere] -> [placement] -> assemblage, et le
   traitement peut desormais etre un MOTEUR 3D payant (mesh3d). D'ou trois
   engagements que cet ecran tient AVANT toute depense :
     · LE PRIX EST DIT AVANT. Moteurs, tarifs, credits, surcout ultra, bornes
       et matieres viennent TOUS de GET /info — aucune grille recopiee ici
       (le bloc miroir NODE_KINDS reste la seule table partagee). Le pied de
       page somme ce que « Lancer » coutera, nœud par nœud, et il compte
       comme PAYANT tout nœud dont il ne connait pas le prix.
     · LA PANNE EST DITE, PAS AVALEE. Cle Meshy absente (has_meshy), boutique
       de matieres ou grille de prix en panne (degraded / materials_degraded),
       refus HTTP du lancement (400/409/503/413) : le message part TEL QUEL a
       l'ecran, jamais un select vide muet ni un bouton qui echoue en silence.
     · L'ETAT VIENT DU JOB, PAS DE L'INTENTION. La chip d'un nœud est peinte
       depuis job.json (POST mesh3d/<nid> puis poll GET), et le `run_id` —
       opaque mais COMPARABLE — est confronte d'un poll a l'autre : s'il
       change, un AUTRE onglet a relance ce nœud, et on le DIT.

   Phase 2c — LE CANVAS NODAL (spec §5.6). Le meme graphe gagne une SECONDE
   projection : des nœuds poses sur une surface pan/zoom, relies par une
   couche SVG. Trois lignes de partage, tenues ici :
     · LE MODELE NE BOUGE PAS. `doc.forge3d.graph` reste la seule verite
       semantique — le canvas le LIT et l'ecrit par les memes chemins que la
       liste (setGraph, editGraph). La vue LISTE survit en bascule : c'est le
       repli sans pointeur, et le support des pins de source 2a/2b.
     · LES POSITIONS SONT DE LA PRESENTATION. Elles vivent a part, dans
       `doc.forge3d.layout = {nid: [x, y]}`, et se patchent SANS entree
       d'annulation : deplacer un nœud n'est pas une edition du graphe, et
       s'intercaler dans la pile ferait annuler un GESTE la ou l'utilisateur
       demande d'annuler une DECISION. Le pan et le zoom, eux, n'entrent meme
       pas dans le document : ce sont des reglages de camera, locaux a
       l'onglet.
     · LA BARRE DE FLUIDITE §9.6 VAUT POUR CHAQUE GLISSER. <= 1 patch (ou une
       ecriture de transformation) par frame, feedback local a chaque
       evenement, geste EXACT au relache, `isPrimary` en garde et
       `touch-action: none` sur la surface.
     · UN CHAMP N'EST ECRIT QU'UNE FOIS (Task 3). Un nœud porte SES menus et
       une vignette qui reagit ; ces menus sont les BATISSEURS DE LA LISTE,
       parametres par hote (`hote: "row"|"node"` ne change que l'emballage,
       jamais les champs) — recopier ce balisage aurait marche le premier
       jour et menti le second. Le repaint est PAR NŒUD (`paintNode`, le
       pendant de `paintRow`) : passer par la reconstruction complete du
       monde volerait le curseur a chaque frappe.
     · DEUX CONTEXTES WebGL, PAS TROIS (Task 5). Un onglet n'a droit qu'a une
       poignee de contextes WebGL vivants ; cet ecran en tient DEUX, et ils ne
       montrent pas la meme chose. L'INSPECTEUR (panneau lateral du canvas)
       montre le nœud SELECTIONNE — un aperçu construit a la demande par
       `POST node-preview`, gratuit, jamais ecrit sur disque. Le viewer du
       RESULTAT, lui, montre le fichier LIVRE par « Construire » : il est
       monte DANS le nœud artefact quand le canvas est a l'ecran, et dans la
       section « Aperçu » sinon — c'est LE MEME element, DEPLACE (`poseViewer`),
       jamais un second.
     · LA PALETTE FAIT NAITRE, ET ELLE NE FAIT NAITRE QUE DU VIVANT. Une
       matiere ou un placement sans chaine est un nœud MORT : le backend
       l'avoue au bordereau, l'ecran ne le construit pas, et la palette
       n'aurait aucune raison d'en poser un d'un clic. Ils exigent donc un
       traitement SELECTIONNE et naissent CONNECTES (par l'ecrivain de chaine
       DEJA en place, `editMat`/`editTrs` -> `rewireRow`). Le glisser de fil,
       lui, garde son comportement de la Task 4 : accepte, et HONNETE a
       l'ecran (« matiere hors chaine ») — un geste vise a la main n'est pas
       un clic de menu, et le refuser aurait coute des gestes legitimes.
   ═══════════════════════════════════════════════════════════════════════════ */
(() => {
  const CF = (typeof window !== "undefined") ? window.CF : null;
  if (!CF) throw new Error("mod-forge3d: js/core.js doit etre charge avant ce fichier");

  /* ── LA TABLE DES COUCHES — BLOC MIROIR ─────────────────────────────────
     ═══ CF-FORGE3D-LAYERS-BEGIN ═══
     Le miroir Python est dans backend/app/services/cards/forge3d.py, entre
     les mêmes marqueurs ; test_cards_forge3d compare les deux champ à champ
     et dans l'ordre.
     Les z sont ceux de la Z_TABLE gelée du CORE (core.js:82). */
  const LAYER_ROLES = [
    { role: "fond-matiere", z: [10], module: "texture" },
    { role: "illustration", z: [20], module: "face" },
    { role: "voile-matiere", z: [30], module: "texture" },
    { role: "cadre", z: [40], module: "frame" },
    { role: "typographie", z: [60], module: "type" },
    { role: "ornements", z: [70], module: "frame" },
  ];
  /* ═══ CF-FORGE3D-LAYERS-END ═══ */

  /* ═══ CF-FORGE3D-NODES-BEGIN ═══
     Miroir Python dans forge3d.py ; parité testée champ à champ. */
  const NODE_KINDS = [
    { kind: "layer", params: ["role", "side"] },
    { kind: "plane", params: ["depth_mm"] },
    { kind: "relief", params: ["depth_mm", "base_mm", "grid"] },
    { kind: "mesh3d", params: ["engine", "texture_prompt", "ultra"] },
    { kind: "material", params: ["mat", "tile_mm", "finish", "aniso"] },
    { kind: "transform", params: ["x_mm", "y_mm", "z_mm", "rot_deg", "scale"] },
    { kind: "assemble", params: [] },
    { kind: "artifact", params: ["name"] },
    { kind: "export", params: ["format"] },
  ];
  /* ═══ CF-FORGE3D-NODES-END ═══ */

  /* LES TRAITEMENTS — miroir de `_PROC_KINDS` (forge3d.py:907) : ce qui peut
     s'intercaler entre une couche et l'assemblage, et donc ce qui merite un
     rang. La 2a l'ecrivait deja en dur dans `graphRows` (plane|relief) ; la 2b
     y ajoute le moteur. Ce n'est PAS une grille de prix ni un roster de
     moteurs (ceux-la viennent de /info) : c'est le vocabulaire du graphe. */
  const PROC_KINDS = ["plane", "relief", "mesh3d"];
  const PROC_LABELS = { plane: "plan", relief: "relief", mesh3d: "mesh 3D (moteur)" };
  /* borne ANTI-GEL de la descente de chaine — miroir de `_CHAIN_MAX`.
     CE QU'ELLE GARDE, EXACTEMENT (clause du report T4) : une chaine qui
     BOUCLE, ou qui s'allonge sans fin, ne peut venir que de l'API BRUTE (un
     graphe poste a la main, ou un fichier de deck bricole). Cet ecran ne peut
     pas en produire : la grammaire de la Task 4 est ACYCLIQUE par rangs
     (couche -> traitement -> maillon -> assemblage -> artefact -> export, sans
     retour possible), et un maillon n'a qu'UNE arete entrante (`surnumeraire`,
     C1). La borne n'est donc PAS une regle du domaine qu'on appliquerait ici :
     c'est un filet contre un graphe qu'on n'a pas ecrit — le meme role, et le
     meme chiffre, que `_CHAIN_MAX` cote serveur. */
  const CHAIN_MAX = 4;
  /* le pas de tuilage que `clean_graph` posera si le noeud matiere n'en porte
     pas (forge3d.py:404). /info sert les BORNES (material_limits.tile_mm), pas
     ce defaut — d'ou cette copie, nommee, plutot qu'un champ vide qui ferait
     croire que rien ne sera construit. */
  const TILE_DEFAUT = 63;
  /* la longueur d'un nom d'artefact — MIROIR de `_ART_NAME_RE` (forge3d.py) et
     de la troncature de `clean_graph`. /info ne la sert pas, d'ou cette copie
     NOMMEE plutot qu'un champ sans borne qui laisserait taper cent caracteres
     que le serveur couperait en silence. Le CHARSET, lui, reste l'affaire du
     nettoyeur : le nom REELLEMENT construit se relit dans `graph_used`
     (`artifactName`), jamais dans ce qu'on a tape. */
  const ART_NAME_MAX = 60;
  const POLL_MS = 1200;         /* periode du poll d'un job (plan 2b) */

  /* ── LE CANVAS (2c) : SES CONSTANTES, TOUTES NOMMEES ────────────────────
     La bascule est une PREFERENCE D'ECRAN, pas un morceau du deck : elle vit
     dans le stockage local (patron core.js:dz_theme), jamais dans le
     document — un jeu exporte ne transporte pas la vue que son auteur
     preferait. */
  const LS_VUE = "dz_cf_forge3d_vue";
  const VUE_DEFAUT = "canvas";  /* §5.6 : le canvas est L'ecran ; la liste
                                    « reste disponible en bascule » */
  /* L'AUTO-ARRANGEMENT : une COLONNE par etage de la grammaire des chaines
     (couche -> traitement -> matiere/placement -> assemblage -> artefact ->
     exports), un rang par nœud DANS sa colonne. Deterministe par
     construction : deux ouvertures du meme graphe posent les memes nœuds aux
     memes pixels — aucun aleatoire nulle part (c'est epingle au test). */
  const COL_X = {
    layer: 40, plane: 280, relief: 280, mesh3d: 280,
    material: 520, transform: 520, assemble: 760, artifact: 1000,
    export: 1240,               /* le kind `export` arrive en Task 4 ; sa
                                    colonne est reservee ici pour que la
                                    grammaire se lise d'un bloc */
  };
  const COL_X_DEFAUT = 760;     /* un kind hors table (graphe charge a la
                                    main) se pose avec l'assemblage plutot
                                    que d'empiler tout a l'origine */
  /* L'EMPILEMENT D'UNE COLONNE — CONTENU-DEPENDANT, ET TOUJOURS DETERMINISTE.
     La Task 2 posait un PAS FIXE (RANG_DY = 120) sous une reserve ecrite noir
     sur blanc : « la hauteur d'un nœud est INDICATIVE — le corps grandit en
     Task 3 ». Il a grandi. Un corps porte desormais sa vignette ET ses menus :
     ~215 px pour une couche, ~300 pour un relief, pres de 370 pour un moteur
     (vignette + moteur + prix + ultra + texture + bouton). Un pas de 120 ferait
     donc CHEVAUCHER les nœuds des le semis — l'auto-arrangement livrerait un
     tas que l'utilisateur devrait defaire a la main, ce qui est pire que pas
     d'arrangement du tout. On AMENDE donc a la source plutot que d'empiler une
     rustine : le rang suivant tombe SOUS le precedent, sa hauteur declaree plus
     une gouttiere. Deux ouvertures du meme graphe posent toujours les memes
     nœuds aux memes pixels (zero Math.random dans ce fichier, c'est epingle).
     CE QUE CETTE TABLE N'EST PAS : une mesure. Ce sont des hauteurs
     D'ARRANGEMENT, lues avant que le DOM n'existe — donc des ESTIMATIONS, et
     deliberement GENEREUSES : les deux erreurs ne coutent pas le meme prix.
     Sous-estimer fait CHEVAUCHER (le defaut qu'on repare ici) ; surestimer ne
     coute que du blanc, et le blanc, « recentrer » le rattrape. Le CADRAGE,
     justement, MESURE la vraie boite quand elle existe (`hauteurNoeud`) et ne
     retombe sur cette table qu'a defaut : c'est lui qui promet de tout
     montrer, il ne peut pas le promettre sur une estimation.
     CONSEQUENCE ASSUMEE, a juger au navigateur (Task 7) : six couches font
     desormais une colonne de ~1,5 k px ; « recentrer » butera sur le plancher
     de zoom et il faudra se deplacer pour tout voir. C'est le prix de menus
     LISIBLES dans le nœud — la spec §5.6 demande le second, pas le premier. */
  const RANG_Y0 = 40, RANG_GAP = 26;
  /* Task 5 : `artifact` et `export` cessent d'etre des reserves. L'artefact
     porte desormais son nom, deux boutons, LE VIEWER DU RESULTAT et le resume
     du bordereau ; l'export, sa vignette, son format et l'etat de ce format.
     Les deux chiffres montent en consequence — genereusement, comme le dit la
     note ci-dessus : le blanc se rattrape au cadrage, le chevauchement non. */
  const RANG_H = {
    layer: 230, plane: 268, relief: 322, mesh3d: 392,
    material: 358, transform: 380, assemble: 132, artifact: 420,
    export: 320,
  };
  const RANG_H_DEFAUT = 240;    /* un kind hors table (graphe charge a la main) */
  /* MIROIR DE LA FEUILLE : la largeur d'un nœud et la mi-hauteur de son
     en-tete servent a placer les PORTS (donc a tracer les aretes). Elles sont
     ecrites des deux cotes — mod-forge3d.css le dit aussi. */
  const NOEUD_W = 200;
  const PORT_Y = 18;            /* 1 px de bordure + la mi-hauteur (34 px) de
                                    l'en-tete : la boite est en `border-box`
                                    (cardforge.css: * { box-sizing }), donc
                                    NOEUD_W est bien le bord DROIT */
  const LAYOUT_MAX = 20000;     /* borne des positions, appliquee AU FLUSH */
  const CAM_X0 = 20, CAM_Y0 = 20;   /* le cadrage d'ouverture */
  /* LE PLANCHER DE ZOOM EST TENU PAR LA SPEC 9.6-3, pas par le gout : la
     poignee d'un nœud est son en-tete (34 px), et une poignee doit rester
     >= 12 px A L'ECRAN. 34 x 0,36 = 12,24 px ; a 0,35 elle tombait a 11,9 —
     sous la barre, au zoom que l'on atteint justement quand on cherche a
     tout voir pour ranger. */
  const ZOOM_MIN = 0.36, ZOOM_MAX = 2.5;

  /* ── LES VIGNETTES (2c Task 3) — LEURS CONSTANTES ───────────────────────
     120 x 168 est la SURFACE DE DESSIN (ratio carte 63 x 88 mm), pas la taille
     d'affichage : la feuille la montre a 96 x 134, donc le canvas est
     sur-echantillonne — net sur un ecran a haute densite, et surtout STABLE
     quand la feuille changera d'avis. Toutes les coordonnees de peinture sont
     donc en unites de dessin. */
  const THUMB_W = 120, THUMB_H = 168;
  /* LES PICTOGRAMMES — ce que montre un nœud qui n'a AUCUNE image a montrer.
     Ce ne sont pas des icones de decor : ce sont les seuls contenus de
     vignette pour les kinds qui n'ont pas de pixels a eux (assemblage,
     artefact, export) et le repli NOMME du kind `mesh3d` — voir la note
     « LE preview.png D'UN JOB N'EST SERVI PAR AUCUNE ROUTE » plus bas. */
  const PICTO = {
    layer: "▤", plane: "▭", relief: "◧", mesh3d: "⬢",
    material: "◍", transform: "✥", assemble: "⧉",
    artifact: "◆", export: "⭳",
  };
  const PICTO_DEFAUT = "○";
  /* LA FINITION, ESQUISSEE — un DEGRADE de vignette, jamais la recette. La
     recette holographique vit cote serveur (forge3d_scene) et ne se voit
     vraiment qu'en tournant le modele dans le viewer ; ce bandeau dit
     seulement « une finition est posee, et laquelle ». Les finitions viennent
     de /info : une recette de plus s'affichera avec le degrade par defaut
     plutot que de disparaitre. */
  const HOLO = {
    argent: ["#e6ebf2", "#8c95a1", "#f4f7fa"],
    dorure: ["#f6d98d", "#b4842a", "#ffeec0"],
  };
  const HOLO_DEFAUT = ["#d5dae2", "#8a93a0", "#eef1f6"];
  /* CE QU'UN NŒUD SANS CHAMP A QUAND MEME A DIRE. Un corps vide se lit comme
     une panne ; ces phrases disent la fonction du nœud (et, pour l'export,
     l'engagement du bordereau). */
  const KIND_HINTS = {
    assemble: "réunit les éléments de toutes les chaînes en un seul artefact.",
    artifact: "porte le nom du fichier construit — « Construire », ci-dessous.",
    export: "point de téléchargement : il n'éteint rien du bordereau.",
  };

  /* le graphe par defaut : chaque couche -> un plan texture empile (parallaxe),
     100 % gratuit, apercu immediat — on monte en gamme nœud par nœud. */
  function defaultGraph(man) {
    const nodes = [], edges = [];
    let k = 0;
    (man.layers || []).forEach((l, i) => {
      const src = "s" + (++k), tr = "t" + k;
      nodes.push({ id: src, kind: "layer", role: l.role, side: man.side });
      nodes.push({ id: tr, kind: "plane", depth_mm: Math.round(i * 0.35 * 100) / 100 });
      edges.push({ from: src, to: tr });
      edges.push({ from: tr, to: "asm" });
    });
    nodes.push({ id: "asm", kind: "assemble" });
    nodes.push({ id: "art", kind: "artifact", name: "carte3d" });
    edges.push({ from: "asm", to: "art" });
    return { nodes: nodes, edges: edges };
  }

  const M = CF.register({
    id: "forge3d",
    title: "Forge 3D",
    icon: "⬢",
    order: 9,
    state: {
      last_export: null,        /* horodatage et compte de faces du dernier
                                    export ; le bordereau n'est pas persisté */
      graph: null,               /* le graphe {nodes, edges} — null = jamais
                                    construit ; le graphe PAR DÉFAUT est
                                    proposé dès qu'un export de couches existe */
      layout: null,              /* {nid: [x, y]} — les POSITIONS des nœuds sur
                                    le canvas (2c). De la PRÉSENTATION, pas du
                                    contenu : patchée sans entrée d'annulation,
                                    semée par `seedLayout`, ignorée par tout le
                                    backend (le graphe seul se construit). Le
                                    pan/zoom, lui, n'est même pas ici : c'est
                                    une caméra locale à l'onglet. */
    },
    init(host) {
      host.innerHTML = shell();
      wire(host);
    },
  });

  const $ = (sel) => (M.slot() ? M.slot().querySelector(sel) : null);

  /* état éphémère du panneau — AUCUN n'est persisté (patron mod-gltf.js :
     INFO/BUILD/ATLAS/BUSY sont eux aussi hors de `state`). */
  let INFO = null;              /* dernière réponse de GET info (graph_limits) */
  let LAST_MANIFEST = null;     /* le manifeste RECTO de la carte courante —
                                    reçu d'un POST layers de cette session, OU
                                    relu du disque au boot (refreshManifest,
                                    I2) ; seed du graphe, bouton seed/re-seed
                                    n'existe que s'il est posé */
  let MANIFEST_CARD = null;     /* l'étiquette de carte (c01, c02…) POUR
                                    LAQUELLE `LAST_MANIFEST` a été chargé —
                                    legs 5 : c'est elle qu'on confronte à la
                                    carte courante à chaque peinture */
  let ARTIFACT = null;          /* le dernier bordereau de build3d */
  let PREVIEW_URL = null;       /* objectURL du GLB monté dans model-viewer —
                                    révoquée avant d'en poser une nouvelle */
  const HIST = [];              /* pile d'annulation des éditions du graphe —
                                    patron mod-gltf.js:HIST, 40 entrées max */
  /* ── L'ÉTAT DES JOBS mesh3d, par nœud — LU, jamais inventé ──────────────
     JOBS[nid] : le DERNIER job.json reçu (objet), ou `null` quand le backend
     a répondu 404 (« jamais lancé » — une réponse, pas une panne). La clé
     ABSENTE veut dire « pas encore sondé » : c'est ce qui déclenche le
     sondage d'une seule requête au premier rendu (un GET, gratuit).
     POLLS[nid] : la GÉNÉRATION du poll en cours (pas un booléen) — un poll
     par nœud, et un tic rassis ne retire que SA PROPRE entrée, jamais celle
     de son successeur (même doctrine que `_MESH3D_RUNNING.get(cle) is moi`
     côté serveur).
     SEEN[nid]  : l'instant du dernier état LU — c'est lui qui autorise une
     re-sonde d'un job terminal (sans quoi « relancé ailleurs » ne pourrait
     jamais se déclencher : une fois le poll arrêté, plus personne ne
     regarde).
     RUNS[nid]  : vrai dès qu'un poll a vu le `run_id` CHANGER — un autre
     onglet a relancé ce nœud, et l'écran le dit au lieu d'un flip muet.
     ERRS[nid]  : le refus HTTP LITTÉRAL du dernier lancement/poll (la
     famille nommée 400/409/503/413), effacé au premier succès. */
  const JOBS = {};
  const POLLS = {};
  const SEEN = {};
  const RUNS = {};
  const ERRS = {};
  const REPROBE_MS = 30000;     /* au-delà, l'état terminal d'un nœud est
                                    RELU une fois par peinture — c'est ce qui
                                    laisse voir la relance d'un autre onglet */
  let GEN = 1;                  /* génération : un poll d'un deck (ou d'une
                                    carte) précédent se tait au lieu d'écrire
                                    dans l'écran du suivant. Commence à 1 :
                                    zéro serait un jeton FAUX dans POLLS. */

  /* OUBLIER LES JOBS — appelé quand ce qu'ils décrivent n'est plus à l'écran
     (changement de deck, changement de carte). `GEN` d'abord : les tics déjà
     en vol se taisent, et les nouvelles sondes repartent sous un jeton neuf
     que ces tics-là ne peuvent plus retirer. */
  function oublieLesJobs() {
    GEN += 1;
    [JOBS, POLLS, SEEN, RUNS, ERRS].forEach((reg) => {
      Object.keys(reg).forEach((k) => { delete reg[k]; });
    });
  }

  function get(k) { return CF.get("forge3d." + k, null); }

  function shell() {
    return '<div class="cf-forge3d-wrap">'
      + '<section class="cf-forge3d-card">'
      + '<header class="cf-forge3d-h"><b>Couches de la carte</b></header>'
      + '<p class="hint">Une PNG alpha par élément (fond, illustration, voile, cadre, '
      + 'typo, ornements), recto et verso, plus le composite. Chaque couche est '
      + 'PROUVÉE : l\'empilement doit reproduire la carte au pixel près.</p>'
      + '<button class="btn strong" id="cf-forge3d-export" type="button">'
      + 'Exporter les couches</button>'
      + '<p class="hint" id="cf-forge3d-status"></p>'
      + '<div id="cf-forge3d-slip"></div>'
      + '</section>'

      + '<section class="cf-forge3d-card">'
      + '<header class="cf-forge3d-h"><b>Graphe 3D</b>'
      + '<div class="seg sm cf-forge3d-vue" id="cf-forge3d-vue">'
      + '<button class="seg-b" type="button" data-vue="canvas">canvas</button>'
      + '<button class="seg-b" type="button" data-vue="liste">liste</button>'
      + '</div>'
      + '<button class="lnk" id="cf-forge3d-undo" type="button" '
      + 'title="annule la dernière édition du graphe">↶ annuler</button>'
      + '</header>'
      + '<p class="hint">Un traitement par couche livrée : plan texturé (gratuit), '
      + 'relief extrudé (gratuit, solide fermé imprimable) ou moteur 3D (payant, '
      + 'prix annoncé avant). Chaque nœud porte sa chaîne — matière et placement. '
      + 'Chaque champ édité patche aussitôt le graphe — annulable. Les deux vues '
      + 'projettent LE MÊME graphe : le canvas se déplace au glisser du fond et '
      + 'se zoome à la molette (position des nœuds gardée, jamais annulable).</p>'
      /* LA PALETTE — ce qui peut NAITRE, et rien d'autre. Elle vit HORS de la
         surface (pas une surcouche) : elle porte des menus, et un menu ouvert
         par-dessus un canvas qui se déplace au glisser serait un piège. */
      + '<div class="cf-forge3d-palette hidden" id="cf-forge3d-palette"></div>'
      /* LA SCÈNE = la surface + son inspecteur. Les deux vont ensemble : le
         panneau ne dit rien sans une sélection, et la sélection ne vit que
         sur le canvas. */
      + '<div class="cf-forge3d-scene">'
      + '<div class="cf-forge3d-canvas" id="cf-forge3d-canvas">'
      + '<div class="cf-forge3d-monde"></div>'
      + '<div class="cf-forge3d-surcouche cf-forge3d-vide"></div>'
      + '<div class="cf-forge3d-surcouche cf-forge3d-outils">'
      + '<button class="btn sm" type="button" data-act="vue-recentre" '
      + 'title="ramène la vue à l\'origine">recentrer</button>'
      + '</div>'
      + '</div>'
      + '<aside class="cf-forge3d-inspecteur" id="cf-forge3d-inspecteur">'
      + '<header class="cf-forge3d-insp-tete"><b>Inspecteur</b>'
      + '<span class="mono" id="cf-forge3d-insp-nom"></span></header>'
      + '<div class="cf-forge3d-insp-view" id="cf-forge3d-insp-view"></div>'
      + '<p class="hint" id="cf-forge3d-insp-etat"></p>'
      + '<p class="hint" id="cf-forge3d-insp-avoues"></p>'
      + '</aside>'
      + '</div>'
      + '<div id="cf-forge3d-graph"></div>'
      + '<p class="hint" id="cf-forge3d-cost"></p>'
      + '</section>'

      + '<section class="cf-forge3d-card">'
      + '<header class="cf-forge3d-h"><b>Construire</b></header>'
      + '<button class="btn strong" id="cf-forge3d-build" type="button">'
      + 'Construire l\'artefact 3D</button>'
      + '<p class="hint" id="cf-forge3d-build-status"></p>'
      + '<div id="cf-forge3d-build-slip"></div>'
      + '</section>'

      + '<section class="cf-forge3d-card">'
      + '<header class="cf-forge3d-h"><b>Aperçu</b>'
      + '<button class="btn sm" id="cf-forge3d-freeze" type="button" disabled>'
      + 'figer l\'aperçu</button>'
      + '</header>'
      + '<div class="cf-forge3d-view" id="cf-forge3d-view"></div>'
      + '<p class="hint" id="cf-forge3d-freeze-status"></p>'
      + '</section>'
      + '</div>';
  }

  function wire(host) {
    $("#cf-forge3d-export").addEventListener("click", () => exportLayers());
    const slip = $("#cf-forge3d-slip");
    if (slip) slip.addEventListener("click", onSlipClick);
    const graphHost = $("#cf-forge3d-graph");
    if (graphHost) {
      graphHost.addEventListener("change", onGraphChange);
      graphHost.addEventListener("click", onGraphClick);
    }
    const canvasHost = $("#cf-forge3d-canvas");
    if (canvasHost) wireCanvas(canvasHost);
    /* LA PALETTE PASSE PAR LA MÊME DÉLÉGATION que la liste et le canvas : un
       seul vocabulaire `data-act`, un seul handler. Ses <select>, eux, ne sont
       PAS des champs de graphe (aucun `[data-proc]` au-dessus d'eux, donc
       `onGraphChange` les ignore par construction) : ils choisissent CE QUI VA
       NAÎTRE, et ce choix est de la présentation — il vit dans `PAL`. */
    const pal = $("#cf-forge3d-palette");
    if (pal) {
      pal.addEventListener("click", onGraphClick);
      pal.addEventListener("change", onPaletteChange);
    }
    const vueSeg = $("#cf-forge3d-vue");
    if (vueSeg) vueSeg.addEventListener("click", onVueClick);
    const undoBtn = $("#cf-forge3d-undo");
    if (undoBtn) undoBtn.addEventListener("click", () => undoGraph());
    $("#cf-forge3d-build").addEventListener("click", () => build3d());
    const buildSlip = $("#cf-forge3d-build-slip");
    if (buildSlip) buildSlip.addEventListener("click", onSlipClick);
    $("#cf-forge3d-freeze").addEventListener("click", () => freezePreview());
    /* ASSURANCE : un changement de deck recharge la page aujourd'hui (donc
       ce module repart de zéro par construction) — mais si ça change un
       jour, un undo ou un seed cross-deck serait un bug sérieux. mod-frame
       et mod-texture s'abonnent déjà à cet événement pour la même raison. */
    CF.on("core:deck", () => {
      HIST.length = 0;
      LAST_MANIFEST = null;
      MANIFEST_CARD = null;
      ARTIFACT = null;
      /* M1 — un chargement de manifeste en vol appartient au deck PRÉCÉDENT :
         on coupe le verrou, sinon le deck suivant se croit « déjà en train de
         charger » et n'en redemande jamais. Le chargement rassis, lui, jette
         son propre résultat (il compare sa génération). */
      refreshManifest.busy = null;
      /* les jobs sont DECK-LOCAUX (nodes/<nid>/job.json sous le deck) : ceux
         du deck précédent ne disent plus rien de celui-ci. */
      oublieLesJobs();
      /* les positions et le cadrage appartiennent au deck qu'on quitte : une
         frame retardataire écrirait son arrangement dans le deck suivant. */
      oublieLeCanvas();
      /* l'aperçu du deck qu'on quitte : révoqué ET détaché, pas seulement
         oublié — le viewer garderait sinon une scène morte à l'écran, et sa
         section un cadre qui ment. */
      videApercu();
    });
    /* LEGS 5, CÔTÉ POUSSÉE — sans cet abonnement la fraîcheur du manifeste
       n'était qu'un contrôle TIRÉ depuis `paintGraph`, que rien ne déclenchait :
       le rail (#prevBtn/#nextBtn) change `CUR` puis appelle `invalidate("core")`,
       qui redessine l'aperçu et émet `core:render {i}` — JAMAIS `core:deck`, le
       seul évènement auquel P9 s'abonnait. Résultat : changer de carte l'onglet
       Forge 3D ouvert ne rafraîchissait rien.
       `core:render` est L'ÉVÈNEMENT ÉTABLI pour ça (core.js:715 le dit :
       « quatre modules y accrochent leur péremption » — mod-gltf:checkStale,
       mod-type, mod-print, mod-data) ; P9 y devient le cinquième. Il est aussi
       le bon pour NOUS : un rendu PARTIEL (l'export par couches de ce module)
       ne l'émet volontairement pas, donc exporter ne déclenche pas N+1 fausses
       alertes de changement de carte.
       Le handler est GRATUIT quand rien ne bouge : `cardChanged` compare les
       étiquettes d'abord et rend `null` sans rien toucher. */
    CF.on("core:render", () => { cardChanged(); });
    /* la bascule est relue AVANT la première peinture : sans quoi l'écran
       s'ouvrirait sur la vue par défaut puis sauterait sur celle de
       l'utilisateur au premier repaint venu. */
    /* M6 — LES VIGNETTES SONT DU PIXEL, PAS DU CSS. Tout le reste de l'écran
       suit le thème tout seul (les feuilles lisent les jetons) ; un canvas
       2D, lui, a CUIT ses couleurs au moment où il a été peint — `encres()`
       les a lues une fois. Basculer la puce ◐ laissait donc onze vignettes en
       encres sombres au milieu d'un lab devenu clair. `applyTheme`
       (core.js:1117) écrit `data-theme` sur le documentElement de CETTE
       iframe : on l'observe, et on redemande une passe (déjà coalescée au
       rAF, donc une bascule = une frame). */
    if (typeof MutationObserver === "function"
        && typeof document !== "undefined" && document.documentElement) {
      new MutationObserver(() => { demandeRepeintVignettes(); }).observe(
        document.documentElement,
        { attributes: true, attributeFilter: ["data-theme"] });
    }
    VUE = vueLue();
    refreshInfo();
    refreshManifest();
    paintUndo();
    paintVue();
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  /* Le meme poids binaire (CEI 80000-13) que le reste du lab (mod-gltf.js,
     mod-print.js) : « Mo » decimal ne se retrouve jamais sur le disque. */
  function weight(n) {
    const v = Number(n) || 0;
    if (v < 1024) return v + " o";
    if (v < 1048576) return (v / 1024).toFixed(1) + " Kio";
    return (v / 1048576).toFixed(2) + " Mio";
  }

  /* ═══════════════════════════════════════════════════════════════════════
     EXPORT — DEUX TEMPS, pour que « rien n'a été envoyé » soit vrai PAR
     CONSTRUCTION et non par discipline de lecture du code.
     Temps 1 (preuve) : les DEUX faces sont rendues et prouvées (CF.layers) ;
     la moindre erreur de painter ou le moindre echec d'empilement NOMME la
     face fautive et REND (aucun FormData, aucun fetch n'existe encore a cet
     instant du code — pas seulement « avant d'etre appele »). Temps 2
     (envoi) : uniquement atteint si les deux faces ont passe le temps 1 —
     chaque face part alors avec SA preuve mesuree.
     Note memoire : les toiles des deux faces (12 couches + 2 composites, au
     lieu de 6+1) restent retenues entre les deux temps — un geste ponctuel
     sur clic, pas une boucle : acceptable. */
  async function exportLayers() {
    /* la carte courante, lue UNE SEULE FOIS en tete de fonction : un
       changement de carte au rail pendant l'export (temps 1 -> temps 2) ne
       peut plus desynchroniser la preuve (CF.layers) de l'etiquette envoyee
       (fd.append("card", ...)) — les deux lisaient CF.current() separement. */
    const carte = (CF.current ? CF.current() : 0);
    const status = $("#cf-forge3d-status");
    const btn = $("#cf-forge3d-export");
    btn.disabled = true;
    try {
      const sides = ["front", "back"];

      /* ── TEMPS 1 : PREUVE DES DEUX FACES, AUCUN RESEAU ────────────────── */
      const preuves = [];
      for (let s = 0; s < sides.length; s++) {
        const face = sides[s];
        status.textContent = "rendu des couches ("
          + (face === "front" ? "recto" : "verso") + ")…";
        const L = await CF.layers(carte, { face: face, groups: LAYER_ROLES });
        if (L.errors && L.errors.length) {
          /* une couche rendue avec une erreur de painter n'est pas une couche
             de confiance : on nomme (face + painters) et on n'envoie rien. */
          status.textContent = "erreur de painter pendant le rendu des couches ("
            + face + " : " + L.errors.map((e) => e.id + " z=" + e.z).join(", ")
            + ") — rien n'a été envoyé.";
          M.toast("rendu des couches en erreur : export refusé", true);
          return;
        }
        if (!L.stack_ok) {
          /* la preuve a echoue : on NOMME et on n'envoie RIEN — un ZIP faux
             est pire qu'un echec dit. */
          const fautive = L.layers.filter((l) => l.mode === "empreinte")
            .map((l) => l.role).join(", ") || "inconnue";
          status.textContent = "preuve d'empilement ÉCHOUÉE (" + face
            + ") — couches en cause : " + fautive + ". Rien n'a été envoyé.";
          M.toast("empilement non reproduit : export refusé", true);
          return;
        }
        preuves.push({ face: face, L: L });
      }

      /* ── TEMPS 2 : LES DEUX FACES SONT PROUVEES — ON ENVOIE ───────────── */
      const results = [];
      for (let p = 0; p < preuves.length; p++) {
        const face = preuves[p].face, L = preuves[p].L;
        const fd = new FormData();
        for (let k = 0; k < L.layers.length; k++) {
          const lay = L.layers[k];
          fd.append("layers", await CF.layerBlob(lay.canvas), lay.role + ".png");
        }
        fd.append("composite", await CF.layerBlob(L.composite), "composite.png");
        fd.append("side", face);
        fd.append("card", String(carte));
        fd.append("paper", L.paper || "#ffffff");
        const modes = {};
        L.layers.forEach((l) => { modes[l.role] = l.mode; });
        fd.append("modes", JSON.stringify(modes));
        fd.append("client_proof", JSON.stringify({ stack_ok: L.stack_ok, diff_px: 0 }));
        status.textContent = "téléversement (" + face + ")…";
        const rep = await M.api.post("layers", fd);
        results.push(rep.layers);
        /* I3a — CETTE FACE-CI EST LIVRÉE : SES PIXELS SONT PÉRIMÉS, MAINTENANT.
           L'invalidation vivait après la boucle, donc après les DEUX faces —
           mais un export peut s'arrêter au milieu (le verso lève : disque
           plein, backend coupé). Le recto était alors bel et bien réécrit
           SOUS LE MÊME NOM, et le cache, lui, gardait les octets d'avant :
           des vignettes fausses, sans le moindre signe, jusqu'au changement
           de deck. Une face livrée invalide sa face, dans le tour où elle
           est livrée. Et l'écran suit tout de suite : si le verso lève, le
           `catch` ne repeint pas, et des vignettes vidées mais non redemandées
           laisseraient les anciens pixels à l'affichage. La demande est
           coalescée au rAF — deux faces ne font qu'une frame. */
        oublieLesImages();
        demandeRepeintVignettes();
        /* seed du graphe par défaut (Task 5) : le RECTO fait foi, jamais le
           dernier reçu — le backend défaut side="front", l'écran affiche
           recto par défaut, et l'aperçu figé devient l'image ERC-721
           (l'identité d'une carte est sa face).

           C1 — L'APPARIEMENT SE POSE ICI AUSSI, sans quoi le legs 5 rentre
           par la porte de l'export : poser `LAST_MANIFEST` seul laissait
           `MANIFEST_CARD` sur l'ancienne carte (ou `null`), et un changement
           de carte PENDANT l'export figeait une paire fausse que le
           comparateur de `cardChanged` valide pour toujours — `seedDefault`
           semait alors depuis les couches d'une autre carte. C'est `carte`,
           l'index figé en tête de fonction, qui étiquette (pas le rail, qui
           a pu bouger). */
        if (face === "front") {
          LAST_MANIFEST = rep.layers;
          MANIFEST_CARD = cardLabel(carte);
        }
      }
      M.patch({ last_export: { at: new Date().toISOString(), sides: results.length } });
      paintSlip(results);
      paintVue();
      status.textContent = "couches livrées, preuve tenue des deux côtés.";
    } catch (e) {
      status.textContent = String(e && e.message || e);
      M.toast(String(e && e.message || e), true);
    } finally {
      btn.disabled = false;
    }
  }

  /* ── LE BORDEREAU — peint depuis la REPONSE mesuree, jamais depuis
     l'intention envoyee : role/mode/couverture/poids viennent des lignes du
     manifeste, l'ecart d'empilement vient de proof.backend.diff_px (second
     avis PIL, cote serveur). Les vignettes chargent le PNG livre par
     GET file/<nom> (patron mod-gltf.js:loadProof/mountViewer — un <img src>
     n'est pas un telechargement, juste une lecture d'apercu). */
  function paintSlip(results) {
    const slip = $("#cf-forge3d-slip");
    if (!slip) return;
    slip.innerHTML = results.map((man) => {
      const rows = man.layers.map((l) =>
        '<div class="cf-forge3d-lay"><img src="'
        + esc(M.api.url("file/" + encodeURIComponent(l.file)))
        + '" alt="" loading="lazy" decoding="async">'
        + '<span class="mono">' + esc(l.role) + " · " + esc(l.mode) + " · "
        + Number(l.coverage_pct) + " % · " + weight(l.bytes) + "</span></div>").join("");
      return '<h4>' + (man.side === "front" ? "Recto" : "Verso") + '</h4>' + rows
        + '<p class="mono">empilement : navigateur strict OK · second avis PIL '
        + Number(man.proof.backend.diff_px) + ' px d\'écart · '
        + '<button class="btn sm" type="button" data-act="grab-zip" data-name="'
        + esc(man.zip.name) + '">' + esc(man.zip.name) + " ("
        + weight(man.zip.bytes) + ')</button></p>';
    }).join("");
  }

  /* ── TELECHARGEMENT — meme provenance que le reste du lab : un fichier
     livre n'est jamais un <a href> direct (patron mod-gltf.js:grab). Le blob
     vient de M.api.blob (mint), donc M.download (alias de CF.download)
     l'accepte — un lien nu servirait un blob de provenance inconnue.
     GENERIQUE (revue) : sert aussi bien le ZIP des couches que le GLB, le
     metadata.json ou le STL du bordereau de build3d — un nom livre est un
     nom livre, peu importe la section qui l'affiche. */
  async function grabZip(name) {
    if (!name) return;
    try {
      const b = await M.api.blob("GET", "file/" + encodeURIComponent(name));
      M.download(b, name);
    } catch (e) {
      M.toast(String(e && e.message || e), true);
    }
  }

  function onSlipClick(e) {
    const b = e.target.closest ? e.target.closest("[data-act]") : null;
    if (!b) return;
    const act = b.getAttribute("data-act");
    if (act === "grab-zip" || act === "grab-file") {
      e.preventDefault();
      grabZip(b.getAttribute("data-name"));
    }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     LE GRAPHE — liste structurée de nœuds (pas un canvas nodal, Task 5 du
     plan) : un rang par nœud de TRAITEMENT (plane/relief), lu depuis l'edge
     layer -> traitement qui le sourcE. Chaque édition clone le graphe (state
     immuable : le patch précédent l'a deep-frozen), modifie le clone, puis
     M.patch — jamais une mutation en place.
     ═══════════════════════════════════════════════════════════════════════ */
  async function refreshInfo() {
    try {
      INFO = await M.api.get("info");
    } catch (e) {
      INFO = null;
    }
    paintVue();
  }

  /* I2 — LE MANIFESTE SE CHARGE AU BOOT : `LAST_MANIFEST` ne vivait qu'en
     mémoire de module, donc un F5 après un export réel faisait mentir le
     hint « exportez les couches d'abord » et effaçait le bouton de re-seed
     alors que les couches, elles, sont bel et bien sur le disque. On relit
     le manifeste RECTO de la carte courante (le même fichier que
     `post_layers` écrit, `layers_c{NN}_front.json`) — 404 = jamais exporté
     pour cette carte, toléré EN SILENCE (ce n'est pas une panne, le hint
     le dit déjà). `M.api.blob` rend un Blob de provenance connue ; on le
     relit en texte puis en JSON (pas de route JSON dédiée à ce fichier). */
  /* L'ÉTIQUETTE D'UNE CARTE — une seule règle de formatage pour tout le
     module (`c01`, `c02`… : celle de `post_layers`, qui nomme
     `layers_c{NN}_front.json`). L'index est un PARAMÈTRE : `exportLayers` a
     déjà figé le sien en tête de fonction et doit étiqueter CE numéro-là, pas
     celui que le rail affiche au moment où l'appariement se pose. */
  function cardLabel(carte) {
    const i = (carte == null) ? (CF.current ? CF.current() : 0) : carte;
    return "c" + String(i + 1).padStart(2, "0");
  }

  /* un seul chargement à la fois, et `busy` porte LA PROMESSE en cours (pas
     un booléen) : `wire()` en lance un ET peint dans la foulée, et cette
     peinture appelle `cardChanged()` — sans ce verrou, le boot partait en
     DOUBLE requête. Rendre la promesse permet en plus à un appelant qui va
     CONSOMMER le manifeste (le seed) d'attendre le chargement au lieu de lire
     l'ancien. */
  function refreshManifest() {
    if (!refreshManifest.busy) refreshManifest.busy = chargeManifeste();
    return refreshManifest.busy;
  }

  async function chargeManifeste() {
    const label = cardLabel();
    const gen = GEN;
    let recu = null;
    try {
      const blob = await M.api.blob("GET", "file/layers_" + label + "_front.json");
      recu = JSON.parse(await blob.text());
    } catch (e) {
      recu = null;
    }
    /* M1 — CE CHARGEMENT PEUT ÊTRE RASSIS : un changement de deck pendant la
       requête a incrémenté `GEN`. Écrire son résultat poserait un manifeste —
       et surtout un APPARIEMENT — appartenant à ce qui n'est plus à l'écran.
       Il se jette, il ne se peint pas ; et il ne TOUCHE PAS au verrou, que le
       handler `core:deck` a déjà libéré (le nuller ici tuerait celui du
       chargement suivant, déjà parti). Le chemin `cardChanged`, lui, ne peut
       pas rassir : il incrémente `GEN` AVANT de lancer sa requête. */
    if (gen !== GEN) return;
    LAST_MANIFEST = recu;
    /* l'étiquette est posée MÊME en échec : un 404 est une réponse (« jamais
       exporté pour cette carte »), pas une raison de re-demander en boucle
       à chaque peinture. */
    MANIFEST_CARD = label;
    refreshManifest.busy = null;
    paintVue();
  }

  /* LEGS 5 — LE MANIFESTE SUIT LA CARTE, pas seulement le boot. `LAST_MANIFEST`
     ne se chargeait qu'à l'initialisation du panneau : changer de carte au rail
     laissait donc l'écran proposer (ou refuser) un graphe par défaut d'après
     les couches d'une AUTRE carte.

     LE COMPARATEUR EST LE GARDE, et il est le PREMIER geste : tant que
     l'étiquette de la carte courante est celle du manifeste chargé, cette
     fonction ne touche à RIEN — ni réseau, ni DOM, ni focus (le piège
     syncInputs/renderPanel de mod-face : un abonné qui repeint à chaque tic de
     rendu volerait le curseur de l'utilisateur des dizaines de fois par
     minute). Elle rend la promesse du rechargement quand il a lieu (ou celle
     du rechargement DÉJÀ en vol), `null` quand il n'y a rien à faire — c'est
     ce qui permet au seed de l'ATTENDRE. */
  function cardChanged() {
    if (refreshManifest.busy) return refreshManifest.busy;
    if (cardLabel() === MANIFEST_CARD) return null;
    /* I2 — UN JOB EST LIÉ À SA CARTE. Le GLB d'un nœud a été fabriqué depuis
       LA couche d'une carte précise (le job le dit lui-même : `source.file`).
       Garder les chips en changeant de carte afficherait « servi · 30 cr » sur
       un nœud qui, pour LA carte affichée, n'a rien servi du tout — et le pied
       de coût compterait ce nœud comme déjà payé. Le chip d'une autre carte
       serait un mensonge : on oublie, et on re-sonde. */
    oublieLesJobs();
    /* UN APERÇU EST LIÉ À SA CARTE, exactement comme un job (Task 5). Le GLB
       que l'inspecteur montre a été construit depuis LES COUCHES de la carte
       affichée à ce moment-là : le garder en changeant de carte laisserait
       l'illustration d'hier tourner dans le panneau à côté du graphe
       d'aujourd'hui. On le lâche — et la peinture qui suit re-inspecte le
       nœud désigné, avec les couches de la BONNE carte (`videInspecteur`
       remet la clé de sujet à zéro, donc `majInspecteur` re-déclenche). */
    videInspecteur();
    /* ... ET LE BORDEREAU AVEC. `ARTIFACT` porte les poids, les moteurs et les
       crédits d'une construction qui a tourné sur LES COUCHES d'une carte
       précise ; le garder ferait dire au nœud artefact — et à TOUS les nœuds
       d'export, qui ne lisent RIEN d'autre — que la carte affichée a déjà
       livré ces fichiers-là, avec des boutons de téléchargement qui servent
       ceux de la carte d'avant. C'est le même mensonge que les chips de jobs,
       au même endroit. `videApercu` est la porte de sortie complète du
       viewer du RÉSULTAT : objectURL RÉVOQUÉE (pas seulement oubliée, comme
       le fait le remplacement de `mountPreview`), viewer détaché de son hôte,
       section vidée, « figer » re-verrouillé. */
    ARTIFACT = null;
    videApercu();
    /* LA PROMESSE D'ABORD, LA PEINTURE ENSUITE. `repeintLeBordereau` peint, et
       toute peinture rappelle `cardChanged` : le verrou de `refreshManifest`
       doit être posé AVANT, sans quoi un nœud absent du DOM (le premier
       passage sur le canvas) enverrait `paintNode` dans son repli
       `paintVue()` et la boucle se refermerait sur elle-même. */
    const suite = refreshManifest();
    repeintLeBordereau();
    return suite;
  }

  /* LE MODÈLE D'UN RANG — la CHAÎNE d'un traitement, résolue exactement comme
     le backend la résoudra : `_resolve_graph_elements` pour la source (la
     PREMIÈRE arête layer -> traitement gagne) et `_chaine_aval` pour l'aval
     (`material` puis `transform`, 0 ou 1 de chacun, dans n'importe quel ordre,
     première arête gagnante là aussi). Les maillons surnuméraires restent dans
     le graphe — le backend les avoue au bordereau via `ignored` après
     construction ; l'écran ne les cache pas, il ne leur donne simplement pas
     de rang. Rendre `{layer, proc, mat, trs}` : c'est la seule forme que
     l'affichage ET l'édition manipulent. */
  function rowModel(graph, procId) {
    const byId = {};
    (graph.nodes || []).forEach((n) => { byId[n.id] = n; });
    const proc = byId[procId];
    if (!proc || PROC_KINDS.indexOf(proc.kind) < 0) return null;
    const edges = graph.edges || [];
    let layer = null;
    for (let i = 0; i < edges.length && !layer; i++) {
      const f = byId[edges[i].from];
      if (edges[i].to === procId && f && f.kind === "layer") layer = f;
    }
    let mat = null, trs = null, cur = procId;
    for (let k = 0; k < CHAIN_MAX; k++) {
      let nxt = null;
      for (let i = 0; i < edges.length && !nxt; i++) {
        const t = (edges[i].from === cur) ? byId[edges[i].to] : null;
        if (t && (t.kind === "material" || t.kind === "transform")) nxt = t;
      }
      if (!nxt) break;
      /* deux matières (ou deux transforms) sur une même chaîne : on s'arrête,
         comme le backend — la seconde ne peut pas gagner sans que la première
         mente. */
      if (nxt.kind === "material") { if (mat) break; mat = nxt; } else { if (trs) break; trs = nxt; }
      cur = nxt.id;
    }
    return { layer: layer, proc: proc, mat: mat, trs: trs };
  }

  /* les rangs, DANS L'ORDRE DES NŒUDS du graphe — le même ordre que celui où
     le backend listera les éléments du bordereau. Un traitement sans aucune
     couche source n'a pas de rang (le backend l'avoue en `ignored`). */
  function graphRows(graph) {
    const rows = [];
    (graph.nodes || []).forEach((n) => {
      if (PROC_KINDS.indexOf(n.kind) < 0) return;
      const r = rowModel(graph, n.id);
      if (r && r.layer) rows.push(r);
    });
    return rows;
  }

  /* M8 — LES CHAÎNES, RÉSOLUES UNE FOIS PAR GRAPHE. `graphRows` est en O(n·m)
     (une descente de chaîne par traitement) et le canvas l'appelait DEUX fois
     par nœud : une pour bâtir son corps, une pour peindre sa vignette — soit
     2N résolutions complètes par peinture, sur un graphe qui n'a pas bougé
     entre les deux.
     LA CLÉ EST L'IDENTITÉ DU GRAPHE, et c'est un invariant du CORE, pas un
     pari : `touch()` remet `SNAP` à null à CHAQUE écriture (core.js:350) et
     `doc()` reconstruit alors tout le sous-arbre par `sanitize` — un contenu
     qui change change donc forcément d'identité. Un mémo périmé est
     impossible ; au pire il RATE, et rater ne coûte que le calcul d'avant.
     ET IL RATE SOUVENT, c'est même la règle : n'IMPORTE QUELLE écriture, de
     n'importe quel module du lab, vide `SNAP` — un patch de `layout` d'ici,
     un texte tapé dans mod-type, un cadre déplacé dans mod-frame. Le mémo
     économise donc la RÉPÉTITION DANS UNE MÊME PEINTURE (2N résolutions pour
     N nœuds, le défaut qu'il corrige), pas la peinture d'après. */
  let ROWS_MEMO = null;

  function rowsDe(graph) {
    if (!graph) return [];
    if (ROWS_MEMO && ROWS_MEMO.g === graph) return ROWS_MEMO.rows;
    const rows = graphRows(graph);
    ROWS_MEMO = { g: graph, rows: rows };
    return rows;
  }

  /* ── LES PRIX : SERVIS PAR /info, JAMAIS RECOPIÉS ───────────────────────
     `engineOf` cherche un moteur dans la table servie ; `engineFor` résout
     CELUI d'un nœud comme le fera `clean_graph` (le sien s'il est connu,
     sinon le défaut du contrat). Un seul résolveur pour l'affichage, le prix
     et le lancement — sinon l'écran annonce un prix et le backend en facture
     un autre. */
  function mesh3dInfo() { return (INFO && INFO.mesh3d) || null; }

  function engineOf(id) {
    const m = mesh3dInfo();
    const tab = (m && m.engines) || [];
    return tab.filter((e) => e && e.id === id)[0] || null;
  }

  function engineFor(proc) {
    const m = mesh3dInfo();
    const tab = (m && m.engines) || [];
    if (!tab.length) return null;
    return engineOf(proc && proc.engine) || engineOf(m.default_engine) || tab[0];
  }

  function defaultEngine() {
    const m = mesh3dInfo();
    return (m && m.default_engine) || "";
  }

  /* le surcoût ultra vient du contrat (`ultra_extra_credits`), jamais d'un id
     de moteur écrit ici : la grille partagée de meshy_service en est la seule
     vérité, et elle ne l'accorde qu'aux moteurs qui le proposent. */
  function ultraCredits(eng) {
    return (eng && Number(eng.ultra_extra_credits)) || 0;
  }

  function engPrice(eng, ultra) {
    if (!eng) return null;
    if (eng.provider !== "meshy") return { usd: Number(eng.price_usd) || 0, credits: 0 };
    const base = Number(eng.credits) || 0;
    const cr = base + (ultra ? ultraCredits(eng) : 0);
    /* le taux crédit -> $ n'est pas une constante d'ici : il se DÉDUIT du
       couple servi (`price_usd` vaut exactement `credits x taux`, cf.
       forge3d.py:_engine_table). Zéro crédit annoncé = zéro équivalent. */
    const taux = base > 0 ? (Number(eng.price_usd) || 0) / base : 0;
    return { usd: Math.round(cr * taux * 10000) / 10000, credits: cr };
  }

  function usdTxt(v) {
    return (Number(v) || 0).toFixed(2).replace(".", ",") + " $";
  }

  /* le prix d'UN nœud, dans les mots de son fournisseur */
  function priceTxt(eng, ultra) {
    const p = engPrice(eng, ultra);
    if (!p) return "prix inconnu";
    return (eng.provider === "meshy")
      ? (p.credits + " cr (~" + usdTxt(p.usd) + ")")
      : usdTxt(p.usd);
  }

  /* un champ numérique borné PAR /info — jamais des bornes écrites ici */
  function numHtml(label, field, value, bornes, step, unite, off) {
    /* les bornes viennent de /info : ABSENTES, on n'en invente pas (un
       min=0/max=0 de repli verrouillerait le champ en prétendant que c'est
       la règle du domaine). */
    const b = (bornes && bornes.length === 2
      && isFinite(bornes[0]) && isFinite(bornes[1])) ? bornes : null;
    return '<label class="cf-forge3d-num">' + esc(label)
      + '<input type="number" data-field="' + esc(field) + '" value="'
      + esc(value != null ? value : "") + '"'
      + (b ? ' min="' + Number(b[0]) + '" max="' + Number(b[1]) + '"' : "")
      + ' step="' + esc(step) + '"' + (off ? " disabled" : "")
      + '>' + (unite ? "<i>" + esc(unite) + "</i>" : "") + '</label>';
  }

  /* ── LES CHAMPS, EXTRAITS DE LEUR RANG (2c Task 3) ──────────────────────
     UN SEUL POINT D'ECRITURE PAR CHAMP, dans tout le module. La liste et le
     canvas sont deux HOTES du meme balisage : recopier ces `<select>` dans un
     corps de nœud aurait marche le premier jour et menti le second (la lecon
     des tables miroir : deux copies derivent, et une seule des deux dit vrai).
     Le test de source compte les `data-field` litteraux — a 2, la duplication
     est prouvee et la suite tombe. */
  function procSelHtml(proc) {
    return '<select class="cf-forge3d-kind" data-field="kind">'
      + PROC_KINDS.map((k) => '<option value="' + esc(k) + '"'
        + (proc.kind === k ? " selected" : "") + '>' + esc(PROC_LABELS[k])
        + '</option>').join("")
      + '</select>';
  }

  /* la géométrie d'un traitement — bornes servies par /info. Un moteur ne
     s'extrude pas : sa géométrie vient du GLB livré, pas d'une profondeur
     d'ici (les champs restent sur le nœud, `clean_graph` ne garde que ceux du
     kind retenu : revenir en arrière ne perd rien). */
  function geoHtml(proc, lim) {
    if (proc.kind === "mesh3d") return "";
    const isRelief = proc.kind === "relief";
    const pd = (lim && lim.plane_depth_mm) || [0, 0];
    const rdMax = lim ? lim.relief_depth_mm_max : 0;
    const rb = (lim && lim.relief_base_mm) || [0, 0];
    const rg = (lim && lim.relief_grid) || [0, 0];
    return numHtml("profondeur", "depth_mm", proc.depth_mm,
                   [isRelief ? 0 : pd[0], isRelief ? rdMax : pd[1]], "0.05", "mm")
      + (isRelief
        ? (numHtml("base", "base_mm", proc.base_mm, rb, "0.05", "mm")
          + numHtml("grille", "grid", proc.grid, rg, "1", ""))
        : "");
  }

  function sideSelHtml(layer) {
    const dos = !!(layer && layer.side === "back");
    return '<select class="cf-forge3d-side" data-field="side">'
      + '<option value="front"' + (dos ? "" : " selected") + '>recto</option>'
      + '<option value="back"' + (dos ? " selected" : "") + '>verso</option>'
      + '</select>';
  }

  /* UN BLOC DE CHAMPS, DEUX HOTES. La SEULE chose que l'hôte change est
     l'emballage : dans la LISTE un rang porte toute une chaîne, donc matière
     et placement s'y replient en tiroir (un rang complet tient sur une ligne
     au repos) ; sur le CANVAS ce sont des nœuds SÉPARÉS, et un nœud entier
     dont le seul contenu serait un tiroir fermé ne montrerait rien — c'est
     précisément ce que la spec §5.6 demande d'arrêter. Les CHAMPS, eux, sont
     les mêmes octets dans les deux cas. */
  function blocHtml(titre, pose, dedans, hote) {
    if (hote === "node") {
      return '<div class="cf-forge3d-blk cf-forge3d-blk-n">' + dedans + '</div>';
    }
    return '<details class="cf-forge3d-blk"><summary>' + esc(titre)
      + (pose ? ' <b class="cf-forge3d-on">·</b>' : "") + '</summary>'
      + dedans + '</details>';
  }

  function rowHtml(r, lim) {
    const proc = r.proc, layer = r.layer;
    return '<div class="cf-forge3d-row" data-proc="' + esc(proc.id) + '">'
      + '<div class="cf-forge3d-line">'
      + '<span class="mono cf-forge3d-role">' + esc(layer.role || "composite") + '</span>'
      + procSelHtml(proc)
      + geoHtml(proc, lim)
      + sideSelHtml(layer)
      + '</div>'
      + (proc.kind === "mesh3d" ? mesh3dHtml(proc) : "")
      + matHtml(r, proc.kind === "mesh3d")
      + trsHtml(r)
      + '</div>';
  }

  /* ── LE BLOC MOTEUR — la SEULE dépense de cet écran ─────────────────────
     Tout y vient de `INFO.mesh3d` : le roster, les libellés, les prix, le
     surcoût ultra, la longueur du prompt, la présence de la clé. Rien n'y est
     écrit en dur. Et quand la table est VIDE, on affiche la panne TELLE
     QUELLE — jamais un <select> vide muet, qui se relit « aucun moteur
     n'existe » alors qu'il veut dire « la grille de prix est tombée ». */
  function mesh3dHtml(proc) {
    const m = mesh3dInfo();
    const engines = (m && m.engines) || [];
    if (!engines.length) {
      /* M2 — LA ZONE D'ÉTAT SURVIT À LA PANNE. La table des moteurs est
         tombée, mais un job PAYÉ, lui, ne disparaît pas avec elle : faire
         s'évaporer sa chip effacerait la seule trace à l'écran de ce qui a été
         dépensé. `runHtml` sait déjà se désactiver sans moteur — il rend un
         bouton mort et l'état lu du disque. */
      return '<div class="cf-forge3d-blk cf-forge3d-mesh"><p class="hint">'
        + '<b>moteurs 3D indisponibles</b> — ' + esc((m && m.degraded)
          || "le contrat /info n'a pas été chargé (backend injoignable ?)")
        + '</p><span class="cf-forge3d-run" data-nid="' + esc(proc.id) + '">'
        + runHtml(proc) + '</span></div>';
    }
    const eng = engineFor(proc);
    const cle = !m.has_meshy;
    const opts = engines.map((e) => '<option value="' + esc(e.id) + '"'
      + (e.id === eng.id ? " selected" : "") + '>' + esc(e.label) + " · "
      + esc(priceTxt(e, false))
      + esc(e.provider === "meshy" && cle ? " — clé requise (Réglages)" : "")
      + '</option>').join("");
    const ultraCr = ultraCredits(eng);
    const promptMax = Number((m && m.prompt_max) || 0);
    return '<div class="cf-forge3d-blk cf-forge3d-mesh">'
      + '<label class="cf-forge3d-sel">moteur<select data-field="engine">'
      + opts + '</select></label>'
      + '<span class="cf-forge3d-price mono">' + esc(priceTxt(eng, proc.ultra))
      + '</span>'
      + (ultraCr > 0
        ? ('<label class="cf-forge3d-chk"><input type="checkbox" data-field="ultra"'
          + (proc.ultra ? " checked" : "") + '> ultra <i>+' + Number(ultraCr)
          + ' cr</i></label>')
        : "")
      + '<label class="cf-forge3d-txt">texture<input type="text" '
      + 'data-field="texture_prompt"'
      + (promptMax > 0 ? ' maxlength="' + promptMax + '"' : "")
      + ' value="' + esc(proc.texture_prompt || "") + '" '
      + 'placeholder="ce que le moteur doit peindre"></label>'
      + '<span class="cf-forge3d-run" data-nid="' + esc(proc.id) + '">'
      + runHtml(proc) + '</span>'
      + (m.meshy_mock
        ? '<p class="hint">simulateur Meshy local actif — aucun crédit réel '
          + 'n\'est débité.</p>'
        : "")
      + '</div>';
  }

  /* le bouton et la chip d'un nœud, peints DEPUIS le job (jamais l'intention
     envoyée). `runHtml` est le seul endroit qui décide de désactiver Lancer :
     un job en cours (le backend refuserait en 409) et une clé Meshy absente
     (il refuserait en 503) — l'écran le DIT avant de faire perdre un aller-
     retour à l'utilisateur. */
  function runHtml(proc) {
    const m = mesh3dInfo();
    const eng = engineFor(proc);
    const meshy = !!(eng && eng.provider === "meshy");
    const sansCle = meshy && !(m && m.has_meshy);
    const connu = Object.prototype.hasOwnProperty.call(JOBS, proc.id);
    const job = connu ? JOBS[proc.id] : undefined;
    const court = !!(job && (job.status === "queued" || job.status === "running"));
    return '<button class="btn primary sm" type="button" data-act="launch" '
      + 'data-nid="' + esc(proc.id) + '"'
      + ((court || sansCle || !eng) ? " disabled" : "") + '>'
      + (job ? "relancer" : "lancer") + '</button>'
      + (sansCle
        ? '<span class="cf-forge3d-chip echec">clé Meshy absente — Réglages</span>'
        : "")
      + chipHtml(proc.id, job);
  }

  /* I2 — CE QU'UN JOB A SERVI, dit par le job lui-même. `source` porte la
     couche ET le fichier de carte depuis lesquels ce GLB a été fabriqué : une
     chip muette là-dessus laisse croire qu'un « servi » vaut pour la carte
     affichée, alors qu'un GLB est lié à SA carte (le backend refuse d'ailleurs
     la fusion quand les deux ne coïncident plus). */
  function sourceTxt(job) {
    const s = (job && job.source) || null;
    if (!s) return "";
    return (s.role || "composite") + " · "
      + ((s.side === "back") ? "verso" : "recto")
      + (s.file ? " · " + s.file : "");
  }

  function chipHtml(nid, job) {
    const src = sourceTxt(job);
    const dit = src ? (' title="servi depuis ' + esc(src) + '"') : "";
    let html = "";
    if (RUNS[nid]) {
      html += '<span class="cf-forge3d-chip ailleurs">relancé ailleurs — un '
        + 'autre onglet a repris ce nœud</span>';
    }
    if (ERRS[nid]) {
      /* le refus du backend TEL QUEL : la famille nommée 400 (nœud/couche/clé
         fal), 409 (job déjà en cours, couches absentes), 503 (clé Meshy),
         413 (couche trop lourde). Le paraphraser le diluerait. */
      return html + '<span class="cf-forge3d-chip echec">' + esc(ERRS[nid])
        + '</span>';
    }
    if (job === undefined) return html;              /* pas encore sondé */
    if (job === null) {
      return html + '<span class="cf-forge3d-chip">jamais lancé</span>';
    }
    /* la provenance suit TOUTES les chips d'un job : ce qu'il a servi, ce
       qu'il sert, ce sur quoi il a échoué — jamais un état muet sur SA
       couche. Le texte court reste lisible, le fichier complet est en
       infobulle. */
    const quoi = src
      ? ('<i class="cf-forge3d-src"> · ' + esc((job.source.role || "composite")
        + " " + ((job.source.side === "back") ? "verso" : "recto")) + '</i>')
      : "";
    /* ÉCHAPPER À LA FRONTIÈRE, UNE FOIS. `step`, `error` et `closed_note` sont
       les SEULES valeurs de cette fonction écrites par le backend (tout le
       reste est un littéral d'ici ou passe par Number()). On les convertit en
       texte SÛR dès leur lecture, et plus bas on ne manipule que du sûr : un
       `esc()` par champ, à un endroit, plutôt qu'un `esc()` à retrouver dans
       chaque branche — c'est aussi ce qui rend la garantie vérifiable d'un
       coup d'œil (et épinglable par un test de source). */
    const pas = esc(job.step || "");
    const echec = esc(job.error || "sans motif rendu par le backend");
    const note = esc(job.closed_note || "");
    const st = job.status;
    if (st === "queued") {
      return html + '<span class="cf-forge3d-chip file"' + dit + '>en file'
        + quoi + '</span>';
    }
    if (st === "running") {
      return html + '<span class="cf-forge3d-chip cours"' + dit + '>en cours '
        + Number(job.progress || 0) + ' %' + (pas ? " · " + pas : "")
        + quoi + '</span>';
    }
    if (st === "served") {
      const cr = (job.consumed_credits != null)
        ? " · " + Number(job.consumed_credits) + " cr" : "";
      return html + '<span class="cf-forge3d-chip servi"' + dit + '>servi'
        + cr + quoi + '</span>'
        + (note ? '<span class="cf-forge3d-chip note">' + note + '</span>' : "");
    }
    if (st === "failed") {
      return html + '<span class="cf-forge3d-chip echec"' + dit + '>échec : '
        + echec + quoi + '</span>';
    }
    return html + '<span class="cf-forge3d-chip"' + dit + '>' + esc(st)
      + quoi + '</span>';
  }

  /* ── MATIÈRE ET FINITION — bornes et roster servis par /info ────────────
     Même règle que `clean_graph` : une matière sans matière NI finition n'est
     rien. `tuile` et `anisotropie` ne deviennent donc éditables qu'une fois
     l'une des deux posée — sans quoi le nœud naîtrait vide, serait jeté, et
     la case cochée mentirait sur un graphe qui ne la porte pas. */
  function finishLabel(f) {
    /* la seule finition qui ne soit pas holographique est l'absence de
       finition — le libellé se DÉRIVE de la liste servie, il ne la recopie
       pas (une recette de plus côté serveur s'affichera toute seule). */
    return (f === "aucune") ? "aucune" : (f + " holographique");
  }

  function matHtml(r, isMesh, hote) {
    const mats = (INFO && INFO.materials) || [];
    const lim = (INFO && INFO.material_limits) || null;
    const panne = INFO ? INFO.materials_degraded : null;
    const mat = r.mat;
    const finitions = (lim && lim.finishes) || [];
    const pose = !!mat;
    const matSel = mats.length
      ? ('<label class="cf-forge3d-sel">matière<select data-field="mat">'
        + '<option value=""' + (mat && mat.mat ? "" : " selected") + '>aucune</option>'
        + mats.map((x) => '<option value="' + esc(x.id) + '"'
          + (mat && mat.mat === x.id ? " selected" : "") + '>' + esc(x.name)
          + '</option>').join("")
        + '</select></label>')
      /* jamais un select vide muet : la panne (ou la boutique vide) est dite */
      : ('<span class="hint"><b>aucune matière</b> — ' + esc(panne
        || (INFO ? "la boutique de matières est vide (aucune matière installée)."
                 : "contrat /info non chargé.")) + '</span>');
    const finSel = finitions.length
      ? ('<label class="cf-forge3d-sel">finition<select data-field="finish">'
        + finitions.map((f) => '<option value="' + esc(f) + '"'
          + (((mat && mat.finish) || "aucune") === f ? " selected" : "") + '>'
          + esc(finishLabel(f)) + '</option>').join("")
        + '</select></label>')
      : '<span class="hint">finitions inconnues (contrat /info non chargé).</span>';
    const dedans = '<div class="cf-forge3d-line">' + matSel + finSel
      + numHtml("tuile", "tile_mm",
                (mat && mat.tile_mm != null) ? mat.tile_mm : TILE_DEFAUT,
                lim && lim.tile_mm, "1", "mm", !pose)
      + '<label class="cf-forge3d-chk"><input type="checkbox" data-field="aniso"'
      + (mat && mat.aniso ? " checked" : "") + (pose ? "" : " disabled")
      + '> anisotropie</label></div>'
      + '<p class="hint">matière sur plan/relief seulement — un GLB moteur '
      + 'garde la sienne.' + (isMesh && mat
        ? ' Ce rang est un moteur : la matière chaînée sera avouée comme '
          + 'ignorée au bordereau.' : "")
      + (pose ? "" : ' Tuile et anisotropie s\'activent dès qu\'une matière ou '
        + 'une finition est posée.') + '</p>';
    return blocHtml("matière", !!mat, dedans, hote);
  }

  /* LE z EFFECTIF D'UN ÉLÉMENT SANS NŒUD `transform` — c'est-à-dire ce que le
     writer posera de toute façon : pour un PLAN, sa profondeur d'empilement
     (`_node_trs` traduit `z_mm` en translation) ; pour un relief ou un GLB de
     moteur, zéro. UNE seule règle, lue par le SEMIS du nœud (`editTrs`) ET par
     son AFFICHAGE (`trsHtml`) : les laisser diverger, c'est exactement la faute
     que cette fonction existe pour tuer. */
  function zEmpilement(proc) {
    const d = Number(proc && proc.depth_mm);
    return (proc && proc.kind === "plane" && isFinite(d)) ? d : 0;
  }

  function trsHtml(r, hote) {
    const lim = (INFO && INFO.transform_limits) || null;
    const t = r.trs;
    if (!lim) {
      return blocHtml("placement", false,
                      '<p class="hint">bornes inconnues (contrat /info non '
                      + 'chargé).</p>', hote);
    }
    /* M1 — CE QUI SERA CONSTRUIT, JAMAIS UN CHAMP VIDE. Même sans nœud
       `transform`, le writer POSE un placement : identité en x/y/rotation,
       échelle 1, et en z l'empilement du traitement. Un champ blanc se relit
       « rien de défini » là où quelque chose l'est très précisément — et c'est
       ce z-là qu'un semis à zéro écrasait. Les défauts que /info ne sert pas
       sont ceux de `clean_graph` (forge3d.py:410-414). */
    const d = t || { x_mm: 0, y_mm: 0, z_mm: zEmpilement(r.proc),
                     rot_deg: 0, scale: 1 };
    const dedans = '<div class="cf-forge3d-line">'
      + numHtml("x", "x_mm", d.x_mm, lim.xy_mm, "0.5", "mm")
      + numHtml("y", "y_mm", d.y_mm, lim.xy_mm, "0.5", "mm")
      + numHtml("z", "z_mm", d.z_mm, lim.z_mm, "0.1", "mm")
      + numHtml("rotation", "rot_deg", d.rot_deg, lim.rot_deg, "1", "°")
      + numHtml("échelle", "scale", d.scale, lim.scale, "0.05", "")
      + '</div>'
      + '<p class="hint">un placement absent laisse l\'élément là où son '
      + 'traitement le pose — les valeurs ci-dessus sont celles qui seront '
      + 'construites.</p>';
    return blocHtml("placement", !!t, dedans, hote);
  }

  /* le bouton seed : identique dans les deux branches (graphe absent ou déjà
     posé), seul l'id et le libellé changent — le re-seed d'un graphe déjà
     construit passe par la MÊME pile d'annulation que toute autre édition
     (patron « re-seed = juste une édition de plus »). */
  function seedButtonHtml(id, label) {
    return '<button class="btn sm" id="' + id + '" type="button" '
      + 'data-act="seed-default">' + esc(label) + '</button>';
  }

  function paintGraph() {
    const host = $("#cf-forge3d-graph");
    if (!host) return;
    /* legs 5, second filet : l'abonnement `core:render` de `wire()` est ce qui
       DÉCLENCHE la fraîcheur ; ce contrôle-ci rattrape les peintures qui
       n'ont pas de rendu de carte derrière elles (arrivée sur l'onglet,
       réponse tardive de /info). Il est gratuit quand rien n'a bougé. */
    cardChanged();
    const graph = get("graph");
    if (!graph) {
      host.innerHTML = LAST_MANIFEST
        ? ('<p class="hint">Aucun graphe construit pour le moment.</p>'
          + seedButtonHtml("cf-forge3d-graph-seed", "construire le graphe par défaut"))
        : '<p class="hint">Exportez les couches d\'abord (section ci-dessus) '
          + 'pour proposer un graphe par défaut.</p>';
      paintCost();
      return;
    }
    const rows = rowsDe(graph);
    const lim = (INFO && INFO.graph_limits) || null;
    const body = rows.length
      ? rows.map((r) => rowHtml(r, lim)).join("")
      : '<p class="hint">Graphe sans traitement — aucune couche reliée à un '
        + 'plan, un relief ou un moteur.</p>';
    /* le re-seed reste OFFERT même une fois le graphe construit : abîmer son
       graphe n'est plus une impasse — et comme il passe par setGraph, il
       reste lui-même annulable. */
    const reseed = LAST_MANIFEST
      ? seedButtonHtml("cf-forge3d-reseed", "reconstruire le graphe par défaut")
      : "";
    /* M5 — LE PLAFOND D'ÉLÉMENTS EST DIT, PAS DÉCOUVERT AU REFUS. `build3d`
       rend un 400 nommé au-delà de `max_elements` ; ce chiffre est SERVI par
       /info (jamais recopié ici), et l'écran le rappelle dès que le graphe
       courant le dépasse — sinon l'utilisateur monte un graphe entier avant
       d'apprendre qu'il ne se construira pas. */
    const maxEl = Number(lim && lim.max_elements) || 0;
    const trop = (maxEl > 0 && rows.length > maxEl)
      ? ('<p class="hint cf-forge3d-trop"><b>' + rows.length + ' éléments</b> — '
        + 'le maximum construisible est ' + maxEl
        + ' : retire des rangs, la construction refuserait.</p>')
      : "";
    host.innerHTML = body + trop + reseed;
    sondeMoteurs(graph);
    paintCost();
  }

  /* l'état des nœuds moteur vient du DISQUE, pas de la mémoire de l'onglet :
     un nœud jamais sondé l'est UNE fois (un GET, gratuit), sans quoi un job
     servi d'une session précédente resterait invisible et serait recompté
     comme payant par le pied de coût. Extrait de `paintGraph` en 2c : LES
     DEUX vues en ont besoin, et un sondage qui ne partirait que depuis la
     liste laisserait le canvas afficher « jamais lancé » sur un nœud payé. */
  function sondeMoteurs(graph) {
    rowsDe(graph).forEach((r) => {
      if (r.proc.kind === "mesh3d") pollMesh3d(r.proc.id, true);
    });
  }

  /* ── LE PIED DE COÛT — CE QUE « LANCER » COÛTERA, AVANT ────────────────
     Somme des nœuds moteur NON SERVIS (un job déjà livré est payé : le
     relancer coûterait, mais tant qu'on ne le relance pas il ne doit pas
     gonfler le devis). fal en $, Meshy en crédits + équivalent $ déduit du
     contrat. Un nœud dont le prix est INCONNU (table des moteurs tombée) est
     compté comme payant et NOMMÉ — dire « 100 % gratuit » là serait le seul
     mensonge que ce pied de page puisse commettre. */
  function sacoche() { return { usdFal: 0, credits: 0, usdMeshy: 0, inconnus: 0, n: 0 }; }

  function montantTxt(s, appendice) {
    const bouts = [];
    if (s.usdFal > 0) bouts.push(usdTxt(s.usdFal));
    if (s.credits > 0) bouts.push(s.credits + " cr Meshy (~" + usdTxt(s.usdMeshy) + ")");
    if (s.inconnus > 0) {
      /* N7 — LA MÊME LACUNE, DEUX POSITIONS GRAMMATICALES. En tête on ÉNUMÈRE
         (« Coût à lancer : 0,30 $ + 2 nœud(s) au prix inconnu ») ; en appendice
         on complète un verbe (« relancer coûterait … »), où cette énumération
         ne se dit pas. Un aveu qu'on ne peut pas lire n'avoue rien. */
      bouts.push(appendice
        ? ("un montant inconnu pour " + s.inconnus + " nœud(s) (table des "
          + "moteurs indisponible)")
        : (s.inconnus + " nœud(s) au prix inconnu (table des moteurs "
          + "indisponible)"));
    }
    return bouts.join(" + ");
  }

  function costLine() {
    const graph = get("graph");
    if (!graph) return null;   /* pas de graphe, pas de devis à annoncer */
    const alancer = sacoche(), servis = sacoche();
    rowsDe(graph).forEach((r) => {
      if (r.proc.kind !== "mesh3d") return;
      const job = Object.prototype.hasOwnProperty.call(JOBS, r.proc.id)
        ? JOBS[r.proc.id] : undefined;
      const s = (job && job.status === "served") ? servis : alancer;
      s.n += 1;
      const eng = engineFor(r.proc);
      const p = engPrice(eng, r.proc.ultra);
      if (!p) { s.inconnus += 1; return; }
      if (eng.provider === "meshy") { s.credits += p.credits; s.usdMeshy += p.usd; } else s.usdFal += p.usd;
    });
    const tete = montantTxt(alancer, false);
    const differe = montantTxt(servis, true);   /* complète « coûterait … » */
    /* I4 — LE COÛT DIFFÉRÉ SE DIT AUSSI. Un nœud déjà servi ne gonfle pas le
       devis (il est payé), mais son bouton « relancer » est là, actif, et
       recliquer dessus REDÉPENSE. Taire ce chiffre laissait un écran affirmer
       « 100 % gratuit » à côté d'un bouton payant : le seul mensonge que ce
       pied de page puisse commettre. */
    if (tete) {
      return { txt: "Coût à lancer : " + tete + (differe
        ? (" · " + servis.n + " nœud(s) déjà servi(s) — relancer coûterait "
          + differe) : ""), payant: true };
    }
    if (differe) {
      return { txt: "Graphe construit — relancer " + servis.n + " nœud(s) "
        + "moteur coûterait " + differe + ".", payant: true };
    }
    return { txt: "Graphe 100 % gratuit.", payant: false };
  }

  function paintCost() {
    const el = $("#cf-forge3d-cost");
    if (!el) return;
    const c = costLine();
    el.textContent = c ? c.txt : "";
    /* M4 — l'ambre est le rôle « ce que l'action va COÛTER » (cardforge.css :
       un rôle par emploi de l'accent) : un graphe gratuit n'y a pas droit. */
    el.classList.toggle("cf-forge3d-payant", !!(c && c.payant));
  }

  /* ═══════════════════════════════════════════════════════════════════════
     LE CANVAS NODAL (2c, spec §5.6) — LA SECONDE PROJECTION DU MÊME GRAPHE
     Rien ici n'invente de sémantique : les nœuds affichés sont ceux de
     `graph.nodes`, les arêtes celles de `graph.edges`, et tout ce que cette
     section possède en propre, ce sont des PIXELS (le layout, dans le
     document) et une CAMÉRA (le pan/zoom, hors du document).
     ═══════════════════════════════════════════════════════════════════════ */

  /* la paire rAF du lab (mod-face.js:3782, mod-frame, mod-solid, mod-type),
     reproduite ICI en local : les pièces ne partagent aucun import. Le repli
     `setTimeout` et l'annulation SYMÉTRIQUE comptent — `cancelAnimationFrame`
     sur un identifiant de `setTimeout` ne fait rien (autre registre). */
  const hasRAF = (typeof requestAnimationFrame === "function");
  const scheduleFrame = (fn) => (hasRAF ? requestAnimationFrame(fn) : setTimeout(fn, 16));
  const cancelFrame = (id) => { if (hasRAF) cancelAnimationFrame(id); else clearTimeout(id); };

  let VUE = VUE_DEFAUT;         /* "canvas" | "liste" — présentation pure */
  let SEL = null;               /* le nœud sélectionné (clic sur son en-tête).
                                    L'inspecteur 3D de la Task 5 le consomme ;
                                    ici il ne fait que porter la classe. */
  let LAYOUT_VU = sansProto();  /* LA POSITION DE CHAQUE NŒUD À L'ÉCRAN —
                                    l'état du geste vit ici (spec 9.6-1), le
                                    document ne suit qu'au rythme des frames */
  let LAYOUT_SALE = false;      /* une position a bougé depuis le dernier flush */
  let layoutRaf = 0;
  /* LA CAMÉRA — pan et zoom. Volontairement HORS du document : ce n'est pas
     une propriété du deck mais un réglage d'onglet (deux fenêtres ouvertes
     sur le même deck ne se disputent pas leur cadrage). */
  const CAM = { px: CAM_X0, py: CAM_Y0, z: 1 };
  let camPending = null, camRaf = 0;
  let DRAG = null;              /* le geste en cours : un nœud, le fond, ou
                                    un fil tiré depuis un port (`lien`) */
  let ARETE = null;             /* l'arête désignée {from, to} — de la
                                    PRÉSENTATION, comme `SEL` : rien n'en
                                    entre dans le document */
  let lienRaf = 0, lienPoint = null;  /* le fil, coalescé au rAF (spec 9.6-1) */

  /* ── L'INSPECTEUR (Task 5) — SON ÉTAT, TOUT ÉPHÉMÈRE ────────────────────
     `INSP_SUJET` est la CLÉ de ce qui est montré ("n:<nid>", "a:<de>><vers>",
     ou "" pour rien) : c'est elle qui rend `majInspecteur` idempotent — un
     pointerdown de plus sur le nœud déjà désigné ne relance pas une
     construction d'aperçu.
     `INSP_JETON` est le jeton de la requête en vol. Deux sélections rapides
     partent dans l'ordre et peuvent revenir dans le DÉSORDRE : seule la
     dernière a le droit de peindre (la doctrine du fichier, déjà écrite pour
     `POLLS` et `IMGS_VOL` — le jeton COMPARE, il ne se contente pas
     d'exister).
     `INSP_URL` est l'objectURL montée dans le viewer, révoquée avant toute
     nouvelle (patron `mountPreview`) : une URL par sélection, retenue à vie,
     serait une fuite lente sur un panneau fait pour être balayé. */
  let INSP_SUJET = "";
  let INSP_JETON = 0;
  let INSP_URL = null;
  let inspTimer = 0;
  /* LE DÉBOUNCE — la note de concurrence de la revue T1, tenue ICI et pas
     dans la requête : un balayage de sélection (six nœuds parcourus à la
     souris) ne doit pas mettre six CONSTRUCTIONS en file côté serveur. La
     sélection se pose d'abord, la requête part quand elle a TENU. */
  const INSP_MS = 250;
  /* LES DEUX SEULS <model-viewer> DE L'ÉCRAN, tenus par RÉFÉRENCE et non
     retrouvés par id. La raison est mécanique : `paintCanvas` reconstruit le
     monde en un `innerHTML`, ce qui DÉTACHE le viewer monté dans le nœud
     artefact — un `querySelector` ne le trouverait alors plus et en ferait
     naître un second, c'est-à-dire un contexte WebGL de plus à chaque
     repeinture. La référence, elle, survit : on le RE-ACCROCHE. */
  /* LA SCÈNE DU VIEWER DU RÉSULTAT EST-ELLE LÀ ? Ce n'est PAS la même question
     que « une objectURL existe-t-elle ». `mountPreview` pose l'URL puis
     VERROUILLE « figer » jusqu'à l'évènement `load` du viewer — mais un corps
     de nœud artefact se reconstruit à chaque champ commis, et il ne pouvait
     lire que `PREVIEW_URL` : il ré-armait donc le bouton dans la fenêtre où la
     scène n'est pas encore décodée, et une capture y aurait rendu un cadre
     VIDE — qui devient l'image de la carte. */
  let FIGE_PRET = false;
  let MV = null;                /* le viewer du RÉSULTAT (fichier livré) */
  let INSP_MV = null;           /* le viewer de l'INSPECTEUR (nœud désigné) */

  function vueLue() {
    try {
      const s = localStorage.getItem(LS_VUE);
      return (s === "liste" || s === "canvas") ? s : VUE_DEFAUT;
    } catch (e) { return VUE_DEFAUT; }        /* stockage refusé (mode privé) */
  }

  function vueEcrite(v) {
    try { localStorage.setItem(LS_VUE, v); } catch (e) { /* stockage refusé */ }
  }

  function onVueClick(e) {
    const b = e.target.closest ? e.target.closest("[data-vue]") : null;
    if (!b) return;
    e.preventDefault();
    const v = b.getAttribute("data-vue");
    if ((v !== "canvas" && v !== "liste") || v === VUE) return;
    VUE = v;
    vueEcrite(v);
    paintVue();
  }

  /* LE DISPATCHER — un seul graphe, deux projections, un seul point d'entrée.
     La vue INACTIVE est VIDÉE plutôt que gardée au chaud : un poll qui
     repeindrait une chip dans un hôte caché afficherait un état… nulle part,
     et un DOM rassis ferait mentir la première bascule. */
  function paintVue() {
    const seg = $("#cf-forge3d-vue");
    if (seg) {
      Array.prototype.slice.call(seg.querySelectorAll("[data-vue]"))
        .forEach((b) => {
          b.classList.toggle("active", b.getAttribute("data-vue") === VUE);
        });
    }
    const canvas = $("#cf-forge3d-canvas");
    const liste = $("#cf-forge3d-graph");
    const auCanvas = (VUE === "canvas");
    if (canvas) canvas.classList.toggle("hidden", !auCanvas);
    if (liste) liste.classList.toggle("hidden", auCanvas);
    /* L'INSPECTEUR ET LA PALETTE SUIVENT LA SURFACE. Ils ne servent QUE le
       canvas : l'inspecteur n'a de sujet que par la sélection (que la liste
       n'a pas), et la palette pose des nœuds à une POSITION (que la liste
       n'affiche pas). Les laisser visibles en vue liste montrerait deux
       commandes sans effet — et l'inspecteur y garderait un contexte WebGL
       vivant pour rien. */
    const insp = $("#cf-forge3d-inspecteur");
    const pal = $("#cf-forge3d-palette");
    if (insp) insp.classList.toggle("hidden", !auCanvas);
    if (pal) pal.classList.toggle("hidden", !auCanvas);
    if (auCanvas) {
      if (liste) liste.innerHTML = "";
      paintCanvas();
      paintPalette();
    } else {
      videCanvas();
      paintGraph();
      /* LE VIEWER DU RÉSULTAT RENTRE À LA SECTION. `videCanvas` vient de vider
         le monde, donc de DÉTACHER le viewer qui vivait dans le nœud
         artefact : sans ce rappel, la vue liste montrerait un panneau
         « Aperçu » vide alors que le fichier est là, chargé, à une bascule de
         distance. */
      remonteApercu();
    }
  }

  function mondeEl() {
    const host = $("#cf-forge3d-canvas");
    return host ? host.querySelector(".cf-forge3d-monde") : null;
  }

  function videCanvas() {
    /* L'ORDRE DE CES TROIS GESTES EST LE CORRECTIF LUI-MÊME (épinglé au test).
       1. UN SEMIS EN ATTENTE DE FRAME APPARTIENT ENCORE À CE LAYOUT-CI :
          basculer sur la liste dans la même frame que la peinture laissait la
          frame retardataire patcher un LAYOUT_VU déjà vidé — c'est-à-dire
          effacer l'arrangement du document. On l'écrit AVANT de vider.
       2. LE GESTE APPARTENAIT À LA VUE QU'ON QUITTE. Sans `DRAG = null`, le
          pointeur CAPTURÉ continuait d'écrire dans un LAYOUT_VU vidé : le
          relâché flushait alors une carte d'UNE SEULE entrée, et `patchAs`
          remplace la valeur en bloc (fusion superficielle du 1er niveau) —
          toutes les autres positions détruites, et sans recours puisque le
          layout est justement ce qui n'entre PAS dans la pile d'annulation.
       3. et seulement là, on vide. */
    if (layoutRaf) { cancelFrame(layoutRaf); layoutRaf = 0; }
    flushLayout();
    DRAG = null;
    /* le fil et l'arête désignée appartenaient à la vue qu'on quitte : le
       premier a une frame en vol à annuler, la seconde un bouton flottant
       qui n'a plus de trait sous lui. */
    fermeFantome();
    ARETE = null;
    /* L'INSPECTEUR EST UN CONTEXTE WebGL : le laisser vivant sous une vue
       liste garderait un rendu 3D pour un nœud que plus rien ne montre. */
    videInspecteur();
    const host = $("#cf-forge3d-canvas");
    LAYOUT_VU = sansProto();
    if (!host) return;
    const monde = host.querySelector(".cf-forge3d-monde");
    const vide = host.querySelector(".cf-forge3d-vide");
    if (monde) monde.innerHTML = "";
    if (vide) vide.innerHTML = "";
  }

  /* OUBLIER LE CANVAS — appelé quand ce qu'il montre n'est plus le sujet
     (changement de deck). Contrairement à `videCanvas`, on n'écrit RIEN : les
     positions en attente appartiennent au deck qu'on quitte, et les patcher
     ici les poserait sur le deck suivant. */
  function oublieLeCanvas() {
    if (layoutRaf) { cancelFrame(layoutRaf); layoutRaf = 0; }
    if (camRaf) { cancelFrame(camRaf); camRaf = 0; }
    /* une frame de vignettes en vol appartient au deck qu'on quitte : elle
       repeindrait depuis un cache d'images qu'on vient justement de vider. */
    if (vignRaf) { cancelFrame(vignRaf); vignRaf = 0; }
    /* le mémo de chaînes retient le graphe du deck précédent : le lâcher ici
       évite de le garder en vie pour rien (l'identité, elle, ne peut pas
       collisionner — mais un objet retenu reste un objet retenu). */
    ROWS_MEMO = null;
    LAYOUT_SALE = false;
    LAYOUT_VU = sansProto();
    camPending = null;
    DRAG = null;
    SEL = null;
    /* le fil en cours et l'arête désignée parlent du deck qu'on quitte —
       `fermeFantome` n'écrit rien au document (il ne fait qu'annuler une
       frame et retirer un tracé), il a donc sa place sur ce chemin-ci. */
    fermeFantome();
    ARETE = null;
    /* l'aperçu affiché parle du deck qu'on quitte — et son objectURL doit
       être révoquée, pas seulement oubliée. */
    videInspecteur();
    /* les vignettes du deck précédent ne disent rien de celui-ci : les clés
       de couche (`role_cNN_face.png`) sont les MÊMES d'un deck à l'autre,
       donc un cache gardé peindrait la carte d'hier sur le graphe
       d'aujourd'hui. (Le changement de CARTE, lui, n'a pas ce défaut : son
       étiquette est dans la clé.) */
    oublieLesImages();
    CAM.px = CAM_X0; CAM.py = CAM_Y0; CAM.z = 1;
    /* LE PIÈGE DE LA TRANSFORMATION RASSISE : remettre les CHIFFRES sans les
       APPLIQUER laissait le monde affiché sous l'ancien cadrage jusqu'à la
       prochaine écriture de caméra — un deck neuf s'ouvrait au zoom du
       précédent, et la molette « sautait » au premier cran. */
    appliqueCam();
  }

  /* une position BORNÉE, appliquée au flush : un nœud traîné hors du monde
     (ou un layout bricolé à la main dans un fichier de deck) ne peut pas
     s'échapper à l'infini ni revenir en NaN. */
  function bornePos(v) {
    const n = Number(v);
    if (!isFinite(n)) return 0;
    return Math.max(0, Math.min(LAYOUT_MAX, Math.round(n)));
  }

  /* L'AUTO-ARRANGEMENT — DÉTERMINISTE, sans une once de hasard : chaque nœud
     tombe dans la colonne de son kind, au rang qu'il occupe DANS L'ORDRE des
     nœuds du graphe. Les positions DÉJÀ posées gagnent toujours (l'utilisateur
     a bougé ce nœud, on ne le lui reprend pas) ; seules les manquantes sont
     semées. Rend le layout COMPLET de ce graphe — c'est lui qu'on peint. */
  function seedLayout(graph) {
    const pose = get("layout") || {};
    const out = sansProto(), bas = sansProto();
    ((graph && graph.nodes) || []).forEach((n) => {
      const x = connu(COL_X, n.kind) ? COL_X[n.kind] : COL_X_DEFAUT;
      /* le rang tombe SOUS le precedent de SA colonne, hauteur + gouttiere */
      const y = connu(bas, x) ? bas[x] : RANG_Y0;
      bas[x] = y + rangH(n.kind) + RANG_GAP;
      const p = connu(pose, n.id) ? pose[n.id] : null;
      const connue = Array.isArray(p) && p.length === 2
        && isFinite(Number(p[0])) && isFinite(Number(p[1]));
      /* LES DEUX BRANCHES PASSENT PAR `bornePos` : le semis aussi. Ses
         valeurs sont sûres AUJOURD'HUI (des constantes de ce fichier), mais
         c'est le genre de sûreté qui meurt en silence — une colonne poussée à
         30000 en Task 4 aurait produit un layout hors bornes que le flush
         aurait ensuite « corrigé », donc un nœud qui saute tout seul. */
      out[n.id] = connue
        ? [bornePos(p[0]), bornePos(p[1])]
        : [bornePos(x), bornePos(y)];
    });
    return out;
  }

  /* la hauteur D'ARRANGEMENT d'un kind (jamais une mesure — voir RANG_H) */
  function rangH(kind) {
    return connu(RANG_H, kind) ? RANG_H[kind] : RANG_H_DEFAUT;
  }

  /* LA HAUTEUR REELLE D'UN NŒUD, quand elle existe. `offsetHeight` est la
     hauteur de MISE EN PAGE : la transformation de la camera ne l'affecte pas
     (elle s'applique au monde, pas au flux), donc elle est bien en pixels de
     MONDE — exactement ce que le cadrage compare aux positions. Le repli sur
     la table sert le nœud qu'on n'a pas encore peint. */
  function hauteurNoeud(nid, kind) {
    const el = findByAttr(".cf-forge3d-noeud", "data-nid", nid);
    const h = el ? Number(el.offsetHeight) : 0;
    return (isFinite(h) && h > 0) ? h : rangH(kind);
  }

  /* le layout du document est-il en retard sur ce qu'on va peindre ? (semis
     d'un nœud neuf, nœud disparu, position bornée). Comparaison de valeurs :
     patcher un layout identique ferait un enregistrement pour rien. */
  function layoutDiffere(avant, apres) {
    const a = avant || {};
    const ka = Object.keys(a), kb = Object.keys(apres);
    if (ka.length !== kb.length) return true;
    for (let i = 0; i < kb.length; i++) {
      const p = connu(a, kb[i]) ? a[kb[i]] : null;   /* jamais d'accès nu */
      const q = apres[kb[i]];
      if (!Array.isArray(p) || p[0] !== q[0] || p[1] !== q[1]) return true;
    }
    return false;
  }

  function demandeFlushLayout() {
    LAYOUT_SALE = true;
    if (!layoutRaf) layoutRaf = scheduleFrame(flushLayout);
  }

  /* LA POSITION EST DE LA PRÉSENTATION — l'annulation, elle, appartient au
     CONTENU du graphe (`setGraph` pousse sa pile ; ceci, jamais). Empiler un
     déplacement ferait annuler un GESTE là où l'utilisateur demande d'annuler
     une DÉCISION : trois nœuds recadrés effaceraient de la pile le choix de
     matière qu'il voulait reprendre. Un seul patch par frame (spec 9.6-1). */
  function flushLayout() {
    layoutRaf = 0;
    if (!LAYOUT_SALE) return;
    LAYOUT_SALE = false;
    const out = sansProto();
    Object.keys(LAYOUT_VU).forEach((k) => {
      if (k === "__proto__") return;   /* le CORE rebâtit dans un `{}` : cette clé
                                          y REPARENTE l'objet au lieu d'y entrer */
      out[k] = [bornePos(LAYOUT_VU[k][0]), bornePos(LAYOUT_VU[k][1])];
    });
    M.patch({ layout: out });
  }

  /* la translation N'EST PAS arrondie : l'invariant du point-sous-curseur se
     calcule en flottants, l'arrondir à l'affichage le ferait dériver d'un
     demi-pixel par cran de molette — et le monde est déjà mis à l'échelle,
     donc sous-pixel de toute façon. */
  function appliqueCam() {
    const host = $("#cf-forge3d-canvas");
    const monde = host ? host.querySelector(".cf-forge3d-monde") : null;
    if (!monde) return;
    monde.style.transform = "translate(" + CAM.px + "px," + CAM.py
      + "px) scale(" + CAM.z + ")";
    /* LE QUADRILLAGE SUIT LA CAMÉRA. Il est peint sur la SURFACE (elle seule
       couvre la fenêtre entière, quel que soit le zoom — le monde, lui, ne
       fait que la taille du graphe) : sans ce décalage il resterait cloué
       pendant que les nœuds glissent, et le geste de déplacement n'aurait
       AUCUN repère — on croirait le fond figé et les nœuds fous. */
    const pas = 24 * CAM.z;
    host.style.backgroundSize = pas + "px " + pas + "px";
    host.style.backgroundPosition = CAM.px + "px " + CAM.py + "px";
  }

  function flushCam() {
    camRaf = 0;
    if (!camPending) return;
    const c = camPending;
    camPending = null;
    CAM.px = c.px; CAM.py = c.py; CAM.z = c.z;
    appliqueCam();          /* <= 1 écriture de transformation par frame */
  }

  /* RECENTRER = CADRER LE GRAPHE, pas « revenir à l'origine ». Le cadrage est
     local et n'entre jamais dans le document ; sans ce bouton, une surface
     poussée au loin n'a aucun retour. Mais une remise à l'origine ne suffit
     pas : un graphe dont les nœuds ont été rangés à x=1500 reste hors champ
     après le « retour », et le bouton se lit alors comme cassé. On calcule
     donc la boîte du contenu et on l'AJUSTE à la fenêtre (échelle bornée par
     les mêmes butées que la molette, jamais au-delà de 1 — on cadre, on
     n'agrandit pas). Layout vide : la remise à l'origine, faute de contenu. */
  function recentreCam() {
    if (camRaf) { cancelFrame(camRaf); camRaf = 0; }
    camPending = null;
    const host = $("#cf-forge3d-canvas");
    const cles = Object.keys(LAYOUT_VU);
    if (!host || !cles.length) {
      CAM.px = CAM_X0; CAM.py = CAM_Y0; CAM.z = 1;
      appliqueCam();
      return;
    }
    /* LES HAUTEURS SONT MESUREES, PAS SUPPOSEES (2c Task 3) : les corps de
       nœuds ne font plus tous 100 px, et une estimation basse ferait couper le
       bas du graphe par le cadrage qui promet justement de tout montrer. */
    const kinds = sansProto();
    ((get("graph") || {}).nodes || []).forEach((n) => { kinds[n.id] = n.kind; });
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    cles.forEach((k) => {
      const p = LAYOUT_VU[k];
      const h = hauteurNoeud(k, connu(kinds, k) ? kinds[k] : null);
      if (p[0] < x0) x0 = p[0];
      if (p[1] < y0) y0 = p[1];
      if (p[0] + NOEUD_W > x1) x1 = p[0] + NOEUD_W;
      if (p[1] + h > y1) y1 = p[1] + h;
    });
    const w = host.clientWidth, h = host.clientHeight;
    const marge = 24;
    const z = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, 1,
      Math.min((w - 2 * marge) / Math.max(1, x1 - x0),
               (h - 2 * marge) / Math.max(1, y1 - y0))));
    CAM.z = z;
    CAM.px = (w - (x1 - x0) * z) / 2 - x0 * z;
    CAM.py = (h - (y1 - y0) * z) / 2 - y0 * z;
    appliqueCam();
  }

  function wireCanvas(host) {
    host.addEventListener("pointerdown", onCanvasDown);
    host.addEventListener("pointermove", onCanvasMove);
    host.addEventListener("pointerup", onCanvasUp);
    host.addEventListener("pointercancel", onCanvasUp);
    host.addEventListener("wheel", onCanvasWheel, { passive: false });
    /* les boutons du canvas (semis, recentrage) passent par LA MÊME
       délégation que ceux de la liste : un seul vocabulaire `data-act`. */
    host.addEventListener("click", onGraphClick);
    /* ... et les CHAMPS des corps de nœuds (Task 3) par LE MÊME `change` :
       `onGraphChange` remonte jusqu'au premier `[data-proc]`, que ce soit un
       rang de liste ou un corps de nœud. Sans cet abonnement, les menus
       embarqués s'afficheraient et n'écriraient rien — un écran muet, la
       panne la plus difficile à relier à sa cause. */
    host.addEventListener("change", onGraphChange);
    /* ... et `input` pour la VIGNETTE SEULE (M10) : elle suit la frappe, le
       document n'écrit qu'au `change`. Voir `onGraphInput`. */
    host.addEventListener("input", onGraphInput);
    /* ÉCHAP ANNULE — et l'abonnement est au DOCUMENT, faute de mieux : une
       surface de canvas ne porte pas le focus clavier (rien n'y est
       focalisable pendant un glisser, et le pointeur est de toute façon
       capturé). Le handler ne fait RIEN tant qu'aucun geste ni aucune arête
       n'est en cours : il ne peut donc pas voler la touche d'un autre module
       du lab. */
    if (typeof document !== "undefined") {
      document.addEventListener("keydown", onCanvasKey);
    }
  }

  function onCanvasKey(e) {
    if (e.key !== "Escape") return;
    if (DRAG && DRAG.lien) {
      /* le fil tombe sans rien écrire — et le pointeur, lui, reste capturé
         jusqu'à ce que l'utilisateur relâche : `onCanvasMove` et
         `onCanvasUp` sortent alors sur `!DRAG`, c'est-à-dire sans effet. */
      DRAG = null;
      fermeFantome();
    } else if (ARETE) {
      selectionneArete(null);
    } else {
      return;
    }
    e.preventDefault();
  }

  /* LE LÂCHER D'UN FIL — la cible se lit SOUS LE POINTEUR, jamais dans
     `e.target` : le pointeur est CAPTURÉ par la surface depuis le
     `pointerdown`, donc l'évènement désigne la surface et rien d'autre.
     Lâché dans le vide (ou sur une sortie, ou sur son propre nœud) : on
     annule EN SILENCE — le fantôme a déjà disparu sous les yeux de
     l'utilisateur, un toast n'ajouterait qu'un reproche à un geste
     abandonné exprès. Un lien REFUSÉ, lui, se dit : c'est `creeLien`. */
  function deposeLien(deNid, e) {
    if (typeof document === "undefined" || !document.elementFromPoint) return;
    const sous = document.elementFromPoint(e.clientX, e.clientY);
    const port = (sous && sous.closest)
      ? sous.closest(".cf-forge3d-port") : null;
    if (!port || port.getAttribute("data-port") !== "in") return;
    creeLien(deNid, port.getAttribute("data-nid"));
  }

  function onCanvasDown(e) {
    /* `isPrimary` se lit sur l'ÉVÉNEMENT (patron mod-frame.js:2479), jamais
       sur un état à nous : un second doigt posé au milieu d'un glisser ne
       doit pas en démarrer un autre, et un garde d'état resté armé
       verrouillerait la surface jusqu'au rechargement. */
    if (!e.isPrimary) return;
    const cible = e.target;
    if (!cible.closest) return;
    /* les surcouches (semis, outils) gardent leurs clics : démarrer un
       glisser du fond sous un bouton avalerait le bouton.
       LE BOUTON DE COUPE EST LE MÊME CAS, UN ÉTAGE PLUS BAS : il vit DANS le
       monde (pour suivre le cadrage), donc il n'est protégé par aucune
       surcouche — et le glisser du fond, lui, DÉSIGNE l'arête à null, ce qui
       RETIRE ce bouton du DOM au `pointerdown`… c'est-à-dire avant que son
       propre `click` n'arrive. Le bouton aurait disparu sous le doigt sans
       jamais couper quoi que ce soit. */
    if (cible.closest(".cf-forge3d-surcouche")
        || cible.closest(".cf-forge3d-supp")) return;
    const port = cible.closest(".cf-forge3d-port");
    const noeud = cible.closest(".cf-forge3d-noeud");
    const tete = cible.closest(".cf-forge3d-tete");
    /* UN PORT N'EST PAS UNE POIGNÉE DE DÉPLACEMENT : le glisser qui en part
       tire une CONNEXION. Le test passe AVANT celui du corps ci-dessous —
       un port vit hors de l'en-tête (il est ancré sur le BORD du nœud), donc
       la règle « le corps n'est pas une poignée » l'aurait renvoyé sans
       geste. On ne tire que depuis une SORTIE : partir d'une entrée
       demanderait de savoir lire le graphe à l'envers pour rien, le sens de
       lecture étant fixé par la grammaire. */
    if (port) {
      const pnid = port.getAttribute("data-nid");
      if (port.getAttribute("data-port") !== "out" || !pnid) return;
      selectionneArete(null);
      DRAG = { pid: e.pointerId, lien: true, nid: pnid, el: null };
      ouvreFantome();
      majFantome(mondeXY(e));
    } else if (cible.closest(".cf-forge3d-edge-hit")) {
      /* une arête est une CIBLE, pas le fond : son clic la désigne
         (`onGraphClick`) au lieu d'ouvrir un glisser de la surface. */
      return;
    } else if (noeud && !tete) {
      /* LE CORPS D'UN NŒUD N'EST PAS UNE POIGNÉE : ses champs (Task 3)
         doivent recevoir leurs propres gestes. Seul l'en-tête traîne. */
      return;
    } else if (noeud) {
      const nid = noeud.getAttribute("data-nid");
      selectionne(nid);
      /* le bouton d'une arête désignée suivrait mal un nœud qu'on traîne
         (il faudrait le replacer à chaque frame) : le geste de déplacement
         lâche la sélection d'arête, elle se reprend d'un clic. */
      selectionneArete(null);
      const p = posDe(nid) || [0, 0];
      DRAG = { pid: e.pointerId, nid: nid, el: noeud,
               x0: e.clientX, y0: e.clientY, ox: p[0], oy: p[1] };
    } else {
      /* cliquer le FOND désélectionne : sans ça, l'inspecteur de la Task 5
         continuerait de montrer un nœud que plus rien ne désigne à l'écran. */
      selectionne(null);
      DRAG = { pid: e.pointerId, pan: true, el: null,
               x0: e.clientX, y0: e.clientY, px: CAM.px, py: CAM.py };
    }
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch (err) { /* vieux moteur */ }
    e.preventDefault();
  }

  function onCanvasMove(e) {
    if (!DRAG) return;
    /* UN GESTE, UN POINTEUR. `isPrimary` empêche un second doigt d'OUVRIR un
       geste ; il n'empêche pas ses `pointermove` d'arriver ici. Sans ce
       filtre, une tentative de pincement téléportait le nœud à l'écart du
       SECOND doigt (calculé contre l'origine du premier) et le COMMETTAIT au
       relâché — même doctrine que le registre `POLLS` du 2b : le jeton
       compare, il ne se contente pas d'exister. */
    if (e.pointerId !== DRAG.pid) return;
    if (DRAG.pan) {
      camPending = { px: DRAG.px + (e.clientX - DRAG.x0),
                     py: DRAG.py + (e.clientY - DRAG.y0), z: CAM.z };
      if (!camRaf) camRaf = scheduleFrame(flushCam);
      return;
    }
    /* LE FIL SUIT LE CURSEUR, UNE ÉCRITURE PAR FRAME (spec 9.6-1). Le point
       visé est retenu à CHAQUE événement (donc rien n'est perdu : la frame
       dessine le DERNIER, exact), mais l'attribut `d` ne s'écrit qu'au rAF —
       une souris haute fréquence livre plusieurs mouvements par frame, et
       autant d'écritures de tracé n'auraient rien montré de plus. */
    if (DRAG.lien) {
      lienPoint = mondeXY(e);
      if (!lienRaf) lienRaf = scheduleFrame(flushFantome);
      return;
    }
    /* LE NŒUD A PU QUITTER LE DOM SOUS LE GESTE (repeinture venue d'ailleurs :
       réponse tardive de /info, rechargement de manifeste, re-seed). Le
       pointeur est CAPTURÉ par la surface, donc les événements continuent
       d'arriver pour un élément détaché.
       CE QUI SE PASSE ALORS, ET C'EST LE COMPORTEMENT VOULU : le geste est
       ABANDONNÉ NET. Le nœud repeint est déjà à sa position du document, le
       glisser en cours n'y avait rien écrit (le document ne suit qu'au
       relâché), et couper `DRAG` ici garantit qu'il n'y écrira rien après
       coup. L'utilisateur voit son nœud revenir où il était — l'écran et le
       document disent la même chose, ce qui est la seule fin acceptable.
       TRANSMISSION Task 3 : quand les corps de nœuds porteront des champs, un
       repaint par nœud (le pendant de `paintRow`) remplacera ces repeintures
       globales, et ce chemin-ci deviendra rare — il reste le filet. */
    if (!DRAG.el || !DRAG.el.isConnected) { DRAG = null; return; }
    /* le pointeur se déplace en pixels d'ÉCRAN, le layout en pixels de MONDE :
       diviser par l'échelle, sinon un nœud traîné à z=2 file deux fois trop
       vite sous le curseur. */
    const z = CAM.z || 1;
    const x = bornePos(DRAG.ox + (e.clientX - DRAG.x0) / z);
    const y = bornePos(DRAG.oy + (e.clientY - DRAG.y0) / z);
    LAYOUT_VU[DRAG.nid] = [x, y];
    /* FEEDBACK LOCAL IMMÉDIAT (spec 9.6-2) : le nœud et SES arêtes suivent le
       pointeur à CHAQUE événement — c'est bon marché. */
    DRAG.el.style.left = x + "px";
    DRAG.el.style.top = y + "px";
    majAretes(DRAG.nid);
    /* LE DOCUMENT SUIT AU RELÂCHÉ, PAS À LA FRAME (décision de revue). La
       barre 9.6-1 plafonne à UN patch par frame ; zéro la respecte aussi, et
       ici c'est le bon chiffre : RIEN ne lit `layout` pendant le geste (le
       feedback est local, ci-dessus), tandis que chaque patch cascade en
       `invalidate` -> `drawPreview` — un rendu COMPLET de la carte, par
       frame, pour un geste qui ne peut pas en changer un seul pixel. Le
       drapeau suffit : `onCanvasUp` et `videCanvas` flushent l'état FINAL
       exact (9.6-1, seconde moitié). */
    LAYOUT_SALE = true;
  }

  function onCanvasUp(e) {
    if (!DRAG) return;
    if (e.pointerId !== DRAG.pid) return;    /* un geste, un pointeur (I2) */
    const pan = !!DRAG.pan;
    const lien = DRAG.lien ? DRAG.nid : null;
    DRAG = null;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch (err) { /* deja relache */ }
    if (lien) {
      fermeFantome();
      /* `pointercancel` N'EST PAS UN LÂCHER : l'OS a repris le pointeur (un
         geste système, une fenêtre qui passe devant). Le confondre avec un
         relâché poserait une connexion à l'aveugle, sur ce qui se trouvait
         sous un curseur que l'utilisateur ne dirigeait plus. Ce handler sert
         les deux évènements : c'est le TYPE qui tranche. */
      if (e.type === "pointerup") deposeLien(lien, e);
      return;
    }
    if (pan) {
      if (camRaf) { cancelFrame(camRaf); camRaf = 0; }
      flushCam();
      return;
    }
    /* LE GESTE EXACT AU RELÂCHÉ (spec 9.6-1) : la frame en vol est ANNULÉE et
       le flush fait à la main — sinon la dernière position attendrait une
       frame qui peut ne jamais venir (onglet masqué juste après le lâcher),
       et le document garderait l'avant-dernière. */
    if (layoutRaf) { cancelFrame(layoutRaf); layoutRaf = 0; }
    flushLayout();
    majAretes();
  }

  /* LA MOLETTE — ACCUMULATEUR LOCAL (patron 93987ab de mod-face.js:3854).
     Molettes haute résolution et flings de trackpad livrent PLUSIEURS
     événements par frame, et le geste est INCRÉMENTAL : chaque cran compose
     l'échelle ET le point visé À PARTIR DE L'ÉTAT COURANT. `camPending` EST
     cet état tant que la frame ne l'a pas écrit, et sert donc de base au cran
     suivant — sans lui, deux crans d'une même frame partiraient tous deux de
     l'ancienne base et le second écraserait le premier.
     Différence assumée avec mod-face : là-bas la rafale devait clore un
     GROUPE D'ANNULATION (le zoom écrivait le document) ; ici elle n'écrit
     rien du tout, donc pas de minuterie de fin de rafale — la dernière frame
     applique l'état final, exact par construction. */
  function onCanvasWheel(e) {
    /* LA MOLETTE DU VIEWER EMBARQUÉ LUI APPARTIENT. Le `model-viewer`
       vendorisé `preventDefault` sa propre molette (c'est son dolly) mais il
       ne l'ARRÊTE PAS de remonter : sur le canvas il vit DANS le nœud
       artefact, donc l'événement arrivait ici et zoomait la SCÈNE ENTIÈRE
       pendant que l'utilisateur croyait s'approcher de son modèle. Le garde
       est le PREMIER geste, avant même `preventDefault` : confisquer le
       défilement sans rien faire bouger serait le pire des deux. */
    if (e.target && e.target.closest
        && e.target.closest(".cf-forge3d-art-view")) return;
    e.preventDefault();
    const surf = e.currentTarget;
    const r = surf.getBoundingClientRect();
    /* LE REPÈRE EST LA BOÎTE DE PADDING, pas la boîte de bordure : le monde
       est un enfant `position: absolute; left: 0` de la surface, donc son
       origine est DÉCALÉE de la bordure. Mesurer depuis `r.left` seul faisait
       préserver un point voisin — une dérive d'un pixel par cran, invisible
       au premier et gênante au dixième (la faute déjà réparée une fois sur la
       molette de mod-face, autre repère, même nature). */
    const cx = e.clientX - r.left - surf.clientLeft;
    const cy = e.clientY - r.top - surf.clientTop;
    const base = camPending || CAM;
    /* LIMITE ASSUMÉE, HÉRITÉE DE mod-face : `deltaY` est lu SANS regarder
       `deltaMode`. En mode LIGNE (0x01, certains Firefox) ou PAGE (0x02) un
       cran vaut « 3 » au lieu de « ~100 », et le zoom devient poussif — pas
       faux, lent. La normalisation appartient à une passe partagée (les cinq
       surfaces à molette du lab ont la même dette), pas à ce nœud-ci. */
    const k = Math.exp(-e.deltaY * 0.0016);
    const nz = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, base.z * k));
    /* LE POINT SOUS LE CURSEUR NE BOUGE PAS : le monde est translaté PUIS mis
       à l'échelle (transform-origin 0 0), donc le point d'écran cx montre le
       point de monde (cx - px)/z ; le garder fixe impose
       px' = cx - (cx - px)·(z'/z). */
    camPending = {
      px: cx - (cx - base.px) * (nz / base.z),
      py: cy - (cy - base.py) * (nz / base.z),
      z: nz,
    };
    if (!camRaf) camRaf = scheduleFrame(flushCam);
  }

  /* LA SÉLECTION — mémorisée dans `SEL`, portée par une classe, et LUE par
     trois choses depuis la Task 5 : la classe du nœud, la palette (« + matière »
     et « + placement » n'existent que sur un traitement désigné) et
     l'inspecteur, dont elle EST le sujet.
     LE GARDE EST LE PREMIER GESTE : re-cliquer le nœud déjà sélectionné ne
     doit ni repeindre la palette ni relancer une construction d'aperçu — et
     `onCanvasDown` appelle ceci à CHAQUE pointerdown, fond compris. Une seule
     fissure y est ouverte, pour la REPRISE après un échec ; voir plus bas. */
  function selectionne(nid) {
    const avant = SEL;
    SEL = nid || null;
    /* SYMÉTRIQUE de `selectionneArete` : un nœud désigné REPREND le sujet à
       l'arête. Le faire ICI plutôt qu'au site d'appel enlève une dépendance
       d'ORDRE — deux gestes qui se lâchent mutuellement ne doivent pas
       dépendre de qui appelle qui en second, sans quoi un appelant futur
       laisserait l'inspecteur montrer une arête pendant qu'un nœud porte la
       classe de sélection. Cliquer le FOND, lui, ne lâche pas l'arête : on se
       déplace sans perdre ce qu'on visait. */
    const arete = !!ARETE;
    if (SEL && arete) { ARETE = null; majSelArete(); }
    /* LA REPRISE APRÈS UN ÉCHEC — la seule fissure qu'on ouvre dans le garde
       ci-dessus, et elle est étroite exprès. `echecInsp` REND la clé de sujet
       quand un aperçu a échoué (transport coupé, refus nommé, corps vide) :
       « un nœud est désigné ET sa clé est vide » ne peut donc décrire QUE cet
       état-là, jamais un balayage. Sans cette fissure, le geste évident après
       un échec — re-cliquer le nœud — ne repartait pas, et la seule sortie de
       secours était d'aller désigner un autre nœud pour revenir.
       CE QUI RESTE FERMÉ, et ce n'est pas un détail : le FOND. `onCanvasDown`
       appelle `selectionne(null)` à CHAQUE pointerdown du fond, donc au début
       de chaque déplacement de vue ; au repos la clé y est vide elle aussi.
       Une clause qui ne regarderait QUE la clé aurait donc rouvert le passage
       à tous ces gestes-là, et chaque début de déplacement aurait repeint la
       palette entière pour rien — exactement le gaspillage que ce garde
       existe pour empêcher. D'où `!!SEL` : sans sélection, il n'y a rien à
       re-tenter.
       LA FENÊTRE DU DÉBOUNCE N'EN EST PAS UNE : `majInspecteur` pose la clé
       de façon SYNCHRONE, 250 ms avant même d'appeler `inspecte` — pendant
       l'attente comme pendant la requête, elle est donc POSÉE et le garde
       tient. Un double-clic rapide ne peut pas mettre deux constructions en
       vol. */
    const reprise = !!SEL && !INSP_SUJET;
    if (SEL === avant && !arete && !reprise) return;
    marqueSel();
    paintPalette();
    majInspecteur();
  }

  /* la classe seule — extraite pour que la désignation d'une ARÊTE puisse
     lâcher la sélection de nœud sans repasser par l'inspecteur (qui, lui,
     doit alors montrer l'arête, pas le vide). */
  function marqueSel() {
    const host = $("#cf-forge3d-canvas");
    if (!host) return;
    Array.prototype.slice.call(host.querySelectorAll(".cf-forge3d-noeud"))
      .forEach((el) => {
        el.classList.toggle("selected", el.getAttribute("data-nid") === SEL);
      });
  }

  /* les arêtes RÉELLEMENT traçables : celles dont les DEUX extrémités existent
     encore. Une arête pendante n'est pas dessinée (le backend la jetterait de
     toute façon) — mais elle n'est pas non plus effacée du graphe ici :
     `clean_graph` reste l'ultime porte, l'écran ne décide rien en douce. */
  function aretes(graph) {
    const vus = sansProto();
    ((graph && graph.nodes) || []).forEach((n) => { vus[n.id] = 1; });
    return ((graph && graph.edges) || [])
      .filter((e) => connu(vus, e.from) && connu(vus, e.to));
  }

  /* UNE LECTURE PAR ID SE FAIT AVEC hasOwnProperty, JAMAIS EN ACCÈS NU —
     même doctrine que le CORE (core.js:361, `in` traverse la chaîne de
     prototypes). L'alphabet d'id que `clean_graph` autorise ([A-Za-z0-9._-])
     contient « constructor » et « toString » : un accès nu y rendrait une
     FONCTION héritée d'Object.prototype, qui est vraie, qui n'est pas un
     tableau, et qui ferait partir un tracé d'arête en NaN. */
  function connu(reg, cle) {
    return Object.prototype.hasOwnProperty.call(reg, cle);
  }

  /* CÔTÉ ÉCRITURE, `connu()` ne suffit pas. `constructor` et `toString` posés
     en clé créent bien une propriété PROPRE (elles masquent l'héritée, sans
     surprise) ; `__proto__`, lui, ne le fait PAS — sur un objet littéral il
     traverse l'accesseur d'Object.prototype et REPARENTE l'objet au lieu d'y
     ranger une position. Un nœud nommé « __proto__ » (l'alphabet d'id de
     `clean_graph` l'autorise) faisait donc disparaître son entrée du layout et
     empoisonnait l'objet entier. Un registre sans prototype n'a pas
     d'accesseur à traverser : la clé y est une clé, quelle qu'elle soit.
     LECTURE DURCIE ICI, ÉCRITURE FILTRÉE À `flushLayout` — les deux moitiés
     se répondent, et l'une sans l'autre est une RÉGRESSION : une fois
     `__proto__` devenue une vraie clé propre, `Object.keys` la livre au
     patch, et le CORE la rebâtit dans un `{}` où elle reparente l'objet ;
     sa garde de classe lève alors à chaque `doc()` suivant — l'onglet est
     mort jusqu'au rechargement (rien de corrompu ne part au serveur, mais
     plus rien ne s'affiche non plus). D'où le filtre à l'écriture. */
  function sansProto() { return Object.create(null); }

  function posDe(nid) {
    return connu(LAYOUT_VU, nid) ? LAYOUT_VU[nid] : null;
  }

  /* la courbe d'une arête : sortie DROITE du nœud amont -> entrée GAUCHE du
     nœud aval, tangentes horizontales (le sens de lecture du graphe). */
  function courbe(a, b) {
    const x1 = a[0] + NOEUD_W, y1 = a[1] + PORT_Y;
    const x2 = b[0], y2 = b[1] + PORT_Y;
    const dx = Math.max(30, Math.abs(x2 - x1) / 2);
    return "M " + x1 + " " + y1 + " C " + (x1 + dx) + " " + y1 + ", "
      + (x2 - dx) + " " + y2 + ", " + x2 + " " + y2;
  }

  /* UNE SEULE couche SVG, SOUS les nœuds (ordre du DOM) : les nœuds restent
     cliquables, les arêtes ne volent aucun événement (pointer-events: none
     côté feuille). Chaque chemin porte ses deux extrémités en `data-*` pour
     que le glisser recalcule son tracé sans reconstruire la couche. */
  /* DEUX CHEMINS PAR ARÊTE — c'est la dette de la Task 2, payée. Le trait
     VISIBLE fait 1,5 px : comme cible de pointeur il est sous la barre des
     12 px (spec 9.6-3), et il reste donc SOURD (`pointer-events: none` côté
     feuille). La ZONE DE SAISIE est un second chemin, transparent et épais,
     seul à recevoir le pointeur — et il vient EN SECOND dans le DOM (donc
     au-dessus) : posé sous le trait, il aurait été mangé par lui le long du
     tracé, précisément là où l'on vise.
     `aria-hidden` RESTE, et c'est assumé : la zone de saisie n'est pas
     focalisable et ne s'atteint qu'au pointeur — comme le glisser d'un nœud.
     La projection ACCESSIBLE du même graphe, c'est la vue LISTE (la bascule
     est à deux boutons de là) ; exposer douze chemins SVG anonymes à un
     lecteur d'écran ajouterait du bruit, pas une prise.
     RESTE À JUGER AU NAVIGATEUR (T7) : là où plusieurs arêtes CONVERGENT
     (les six chaînes du graphe par défaut se rejoignent sur l'assemblage),
     leurs zones de 14 px se CHEVAUCHENT — le dernier chemin du DOM gagne le
     clic, donc la dernière arête du graphe. Ce n'est pas une perte de
     contrôle (le geste est en DEUX temps : le clic ne fait que DÉSIGNER, et
     `.sel` montre laquelle avant que « supprimer » n'existe), mais la
     lisibilité de ce surlignage au zoom arrière est la question ouverte ;
     le bouton, lui, reste cliquable (z-index 3, au-dessus des nœuds). */
  function edgesHtml(graph, ext) {
    const paths = aretes(graph).map((e) => {
      const bouts = 'data-from="' + esc(e.from) + '" data-to="' + esc(e.to)
        + '" d="' + esc(courbe(posDe(e.from) || [0, 0], posDe(e.to) || [0, 0]))
        + '"';
      const sel = (ARETE && ARETE.from === e.from && ARETE.to === e.to)
        ? " sel" : "";
      return '<path class="cf-forge3d-edge' + sel + '" ' + bouts + '></path>'
        + '<path class="cf-forge3d-edge-hit" ' + bouts + '></path>';
    }).join("");
    return '<svg class="cf-forge3d-edges" width="' + Number(ext.w)
      + '" height="' + Number(ext.h) + '" viewBox="0 0 ' + Number(ext.w)
      + ' ' + Number(ext.h) + '" aria-hidden="true">' + paths + '</svg>';
  }

  /* LE MILIEU D'UNE ARÊTE — et ce n'est pas une approximation : la cubique
     de `courbe` a ses deux poignées HORIZONTALES et symétriques, donc
     B(0,5) tombe pile sur la moyenne des extrémités. Le bouton « supprimer »
     se pose SUR le trait, pas à côté. */
  function milieuArete(a, b) {
    return [(a[0] + NOEUD_W + b[0]) / 2, (a[1] + b[1]) / 2 + PORT_Y];
  }

  /* les tracés SEULS, sans reconstruire la couche : c'est ce qui rend le
     glisser fluide (aucun innerHTML pendant le geste).
     `nid` RESTREINT aux arêtes INCIDENTES : un nœud traîné ne peut déplacer
     que les extrémités qui le touchent, et réécrire les autres était du
     travail par événement qui croît avec la TAILLE DU GRAPHE — la seule
     dépense du glisser qui n'était pas bornée. Sans `nid` (repeinture
     complète, fin de geste), tout est réécrit.
     La comparaison se fait par ATTRIBUT et non par sélecteur construit
     (doctrine `findByAttr`) : un id de nœud est une DONNÉE, jamais un
     fragment de sélecteur — un point y suffirait à tout casser. */
  function majAretes(nid) {
    const monde = mondeEl();
    if (!monde) return;
    /* LES DEUX CHEMINS DE CHAQUE ARÊTE, en une passe : le repère est
       l'ATTRIBUT (les deux le portent), pas la classe — une passe par classe
       aurait laissé la zone de saisie sur l'ancien tracé, c'est-à-dire une
       cible invisible décalée du trait qu'elle prétend viser. L'arête
       fantôme, elle, n'a pas de `data-from` : elle est sautée par
       construction (elle suit le curseur, pas deux nœuds). */
    Array.prototype.slice.call(monde.querySelectorAll("[data-from]"))
      .forEach((p) => {
        const de = p.getAttribute("data-from"), vers = p.getAttribute("data-to");
        if (nid != null && de !== nid && vers !== nid) return;
        const a = posDe(de), b = posDe(vers);
        if (a && b) p.setAttribute("d", courbe(a, b));
      });
  }

  /* ── L'ARÊTE SÉLECTIONNÉE ET SON BOUTON ─────────────────────────────────
     `ARETE` est de la PRÉSENTATION, exactement comme `SEL` : rien n'en entre
     dans le document. Le bouton « supprimer » vit DANS le monde (il suit
     donc le pan et le zoom sans une ligne de plus) et n'existe que tant
     qu'une arête est désignée. */
  /* REPORT T4, TRANCHÉ : UN SEUL SUJET À LA FOIS. Désigner une arête LÂCHE la
     sélection de nœud — sans quoi l'écran montrerait deux « ce que le geste
     suivant va toucher » en même temps (le nœud en `--sel-bg`, l'arête aussi),
     et l'inspecteur continuerait de rendre un nœud que plus rien ne désigne.
     L'inverse était déjà vrai depuis la Task 4 (`onCanvasDown` lâche l'arête
     quand on prend un nœud) ; la symétrie manquait. Le nœud reste le sujet
     NORMAL de l'inspecteur : une arête n'a rien à rendre en 3D, elle n'est pas
     un élément — le panneau le DIT (« arête … ») au lieu de se vider. */
  function selectionneArete(de, vers) {
    ARETE = (de && vers) ? { from: de, to: vers } : null;
    if (ARETE && SEL) {
      SEL = null;
      marqueSel();
      paintPalette();
    }
    majSelArete();
    majInspecteur();
  }

  function majSelArete() {
    const monde = mondeEl();
    if (!monde) return;
    let vue = null;
    Array.prototype.slice.call(monde.querySelectorAll(".cf-forge3d-edge"))
      .forEach((p) => {
        const ok = !!ARETE && p.getAttribute("data-from") === ARETE.from
          && p.getAttribute("data-to") === ARETE.to;
        if (ok) vue = p;
        p.classList.toggle("sel", ok);
      });
    /* L'ARÊTE A PU DISPARAÎTRE SOUS LA SÉLECTION (annulation, re-seed, coupe
       venue d'ailleurs) : on la lâche, plutôt que de laisser flotter un
       bouton prêt à couper ce qui n'existe plus. */
    if (!vue) ARETE = null;
    const a = ARETE ? posDe(ARETE.from) : null;
    const b = ARETE ? posDe(ARETE.to) : null;
    let bt = monde.querySelector(".cf-forge3d-supp");
    if (!a || !b) {
      if (bt && bt.parentNode) bt.parentNode.removeChild(bt);
      return;
    }
    if (!bt) {
      if (typeof document === "undefined") return;
      bt = document.createElement("button");
      bt.className = "btn sm cf-forge3d-supp";
      bt.type = "button";
      bt.setAttribute("data-act", "lien-supp");
      /* `textContent` et non `innerHTML` : rien d'interpolé ici, et rien à
         échapper — le bouton ne porte AUCUNE donnée du graphe (l'arête, elle,
         est dans `ARETE`, pas dans le DOM). */
      bt.textContent = "supprimer";
      monde.appendChild(bt);
    }
    const m = milieuArete(a, b);
    bt.style.left = m[0] + "px";
    bt.style.top = m[1] + "px";
  }

  /* ── L'ARÊTE FANTÔME — le fil que l'on tire depuis un port ───────────────
     Elle vit dans LA couche SVG existante (pas un second calque) : elle
     hérite donc de son `pointer-events: none` et ne peut pas voler le
     relâché qu'on attend justement sur un port d'entrée. */
  function fantomeEl() {
    const monde = mondeEl();
    return monde ? monde.querySelector(".cf-forge3d-fantome") : null;
  }

  function ouvreFantome() {
    const monde = mondeEl();
    const svg = monde ? monde.querySelector(".cf-forge3d-edges") : null;
    if (!svg || typeof document === "undefined") return;
    fermeFantome();
    const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("class", "cf-forge3d-fantome");
    svg.appendChild(p);
  }

  /* LA MÊME COURBE QUE LES VRAIES ARÊTES, et c'est le fond de l'affaire : un
     fantôme tracé par une seconde formule mentirait sur ce que le lâcher va
     poser. `courbe` prend des positions de NŒUD ; le curseur, lui, est un
     point — on lui retire donc l'ancrage que la fonction rajoutera. */
  function majFantome(pt) {
    const el = fantomeEl();
    const a = (DRAG && DRAG.lien) ? posDe(DRAG.nid) : null;
    if (!el || !a) return;
    el.setAttribute("d", courbe(a, [pt[0], pt[1] - PORT_Y]));
  }

  function flushFantome() {
    lienRaf = 0;
    if (!lienPoint) return;
    const pt = lienPoint;
    lienPoint = null;
    majFantome(pt);
  }

  function fermeFantome() {
    if (lienRaf) { cancelFrame(lienRaf); lienRaf = 0; }
    lienPoint = null;
    const el = fantomeEl();
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  /* le point du MONDE sous le pointeur — même repère que la molette : la
     boîte de PADDING de la surface (le monde est un enfant `left: 0`, donc
     décalé de la bordure), et l'échelle se divise, sinon le fantôme dérive
     du curseur dès qu'on a zoomé.
     M6 — LA CAMÉRA EN COURS D'ÉCRITURE FAIT FOI. `camPending` EST la caméra
     tant que la frame ne l'a pas appliquée (c'est déjà la doctrine de la
     molette, qui s'en sert de base pour le cran suivant) : lire `CAM` seul
     ferait calculer le point du fil dans le cadrage d'AVANT quand on zoome
     au milieu d'un glisser — le fil retarderait d'une frame sur le curseur,
     précisément pendant le geste où l'œil suit la pointe. */
  function mondeXY(e) {
    const host = $("#cf-forge3d-canvas");
    if (!host) return [0, 0];
    const r = host.getBoundingClientRect();
    const base = camPending || CAM;
    const z = base.z || 1;
    return [(e.clientX - r.left - host.clientLeft - base.px) / z,
            (e.clientY - r.top - host.clientTop - base.py) / z];
  }

  /* le kind en clair — le miroir NODE_KINDS reste la table du VOCABULAIRE ;
     ceci n'est qu'un dictionnaire d'affichage (PROC_LABELS le fait déjà pour
     les traitements de la liste). */
  const KIND_LABELS = {
    layer: "couche", plane: "plan", relief: "relief", mesh3d: "mesh 3D",
    material: "matière", transform: "placement", assemble: "assemblage",
    artifact: "artefact", export: "export",
  };

  function kindLabel(k) {
    return connu(KIND_LABELS, k) ? KIND_LABELS[k] : String(k == null ? "" : k);
  }

  /* ═══════════════════════════════════════════════════════════════════════
     LA GRAMMAIRE DES CONNEXIONS (2c Task 4) — UNE TABLE, TROIS LECTEURS
     Ce que dit cette table : ce qu'un kind peut avoir EN AVAL. Ce n'est pas
     une préférence d'écran, c'est la forme des chaînes que le backend sait
     résoudre (`_resolve_graph_elements` / `_chaine_aval`) : couche ->
     traitement -> [matière] -> [placement] -> assemblage -> artefact ->
     exports.
     ELLE EST LUE PAR TROIS ENDROITS, et c'est tout l'intérêt de la poser
     UNE fois : la VALIDATION d'un lien (`lienValide`), les PORTS d'un nœud
     (`aEntree`/`aSortie` — qui a une entrée, qui a une sortie s'en DÉDUIT)
     et le TEXTE du refus (`chaineAttendue`). Une seconde liste « qui a quel
     port » aurait dérivé au premier étage ajouté, et l'écran aurait alors
     montré une poignée qui ne branche rien — la faute des tables miroir,
     rejouée à l'intérieur d'un seul fichier.
     CE QU'ELLE NE FAIT PAS : décider de la CARDINALITÉ. « Une chaîne ne
     porte qu'une matière » n'est pas une question de grammaire mais de
     surnombre — c'est `surnumeraire()` qui la tient, plus bas, avec les mots
     du bordereau. */
  const GRAMMAIRE = {
    layer: ["plane", "relief", "mesh3d"],
    plane: ["material", "transform", "assemble"],
    relief: ["material", "transform", "assemble"],
    mesh3d: ["material", "transform", "assemble"],
    material: ["transform", "assemble"],
    transform: ["assemble"],
    assemble: ["artifact"],
    artifact: ["export"],
    export: [],
  };

  function lienValide(de, vers) {
    const suite = connu(GRAMMAIRE, de) ? GRAMMAIRE[de] : null;
    return !!suite && suite.indexOf(vers) >= 0;
  }

  /* un kind a une SORTIE s'il mène quelque part... */
  function aSortie(kind) {
    return connu(GRAMMAIRE, kind) && GRAMMAIRE[kind].length > 0;
  }

  /* ... et une ENTRÉE si quelque chose y mène. Une couche n'a donc pas
     d'entrée (rien ne la produit : elle vient du manifeste) et un export pas
     de sortie (c'est un point de téléchargement, il n'alimente rien). */
  function aEntree(kind) {
    return Object.keys(GRAMMAIRE).some(
      (de) => GRAMMAIRE[de].indexOf(kind) >= 0);
  }

  /* LA CHAÎNE ATTENDUE, EN CLAIR — dérivée de la table, jamais recopiée en
     phrase : le jour où un étage s'ajoute, le refus le dit tout seul. Un
     rang = ce qui peut venir à ce pas de la descente ; les kinds déjà vus
     ne se répètent pas (c'est ce qui borne la marche et la rend
     déterministe). */
  function chaineAttendue() {
    const vus = sansProto();
    const mots = [];
    let rang = ["layer"];
    vus.layer = 1;
    for (let k = 0; k < 12 && rang.length; k++) {
      mots.push(rang.map(kindLabel).join(" | "));
      const suiv = [];
      rang.forEach((kd) => {
        (connu(GRAMMAIRE, kd) ? GRAMMAIRE[kd] : []).forEach((t) => {
          if (connu(vus, t)) return;
          vus[t] = 1;
          suiv.push(t);
        });
      });
      rang = suiv;
    }
    return mots.join(" → ");
  }

  /* le titre d'un nœud : ce qui l'identifie POUR L'ŒIL (le rôle et la face
     d'une couche, le nom d'un artefact, le moteur choisi), jamais un id nu que
     rien ne rend lisible. L'id complet reste en infobulle de l'en-tête. */
  function noeudTitre(n) {
    if (n.kind === "layer") {
      return (n.role || "composite") + " · "
        + ((n.side === "back") ? "verso" : "recto");
    }
    if (n.kind === "artifact") return n.name || "artefact";
    if (n.kind === "mesh3d") return n.engine || "moteur";
    if (n.kind === "material") {
      return n.mat || ((n.finish && n.finish !== "aucune") ? n.finish : "matière");
    }
    return n.id;
  }

  /* UN NŒUD — en-tête (poignée + sélection) et corps. L'ÉLÉMENT extérieur
     porte la position et la sélection ; son intérieur est repeint seul par
     `paintNode`, ce qui préserve les deux choses que le DOM sait et que le
     graphe ignore : le focus et les tiroirs ouverts. */
  function canvasNodeHtml(n) {
    const p = posDe(n.id) || [0, 0];
    return '<div class="cf-forge3d-noeud' + (n.id === SEL ? " selected" : "")
      + '" data-nid="' + esc(n.id) + '" data-kind="' + esc(n.kind)
      + '" style="left: ' + Number(p[0]) + 'px; top: ' + Number(p[1]) + 'px;">'
      + noeudTeteHtml(n) + portsHtml(n) + nodeBodyHtml(n.id)
      + '</div>';
  }

  /* LES PORTS — les poignées de connexion, ancrées EXACTEMENT là où l'arête
     part et arrive (x = 0 ou NOEUD_W, y = PORT_Y ; la feuille pose les mêmes
     chiffres, et le test les compare des deux côtés). Ce sont des enfants
     DIRECTS du nœud, pas de l'en-tête : l'ancre est le bord du nœud, et
     l'en-tête vit à l'intérieur de sa bordure — un pixel d'écart suffirait à
     décoller le trait de sa poignée, le défaut nommé dans la dette de la
     Task 2.
     QUI A QUEL PORT SE DÉDUIT DE LA GRAMMAIRE (voir `aEntree`/`aSortie`) :
     aucune seconde table à tenir d'accord avec la première. */
  function portsHtml(n) {
    let h = "";
    if (aEntree(n.kind)) {
      h += '<span class="cf-forge3d-port cf-forge3d-port-in" data-port="in"'
        + ' data-nid="' + esc(n.id) + '" title="entrée"></span>';
    }
    if (aSortie(n.kind)) {
      h += '<span class="cf-forge3d-port cf-forge3d-port-out" data-port="out"'
        + ' data-nid="' + esc(n.id) + '"'
        + ' title="sortie — glisser vers une entrée"></span>';
    }
    return h;
  }

  function noeudTeteHtml(n) {
    return '<header class="cf-forge3d-tete" title="' + esc(n.id) + '">'
      + '<span class="cf-forge3d-kind-l">' + esc(kindLabel(n.kind))
      + '</span>'
      + '<span class="mono cf-forge3d-titre">' + esc(noeudTitre(n)) + '</span>'
      + '</header>';
  }

  /* ── LA CHAÎNE D'UN NŒUD, VUE DEPUIS LE NŒUD ────────────────────────────
     `rowModel` répond « quelle chaîne part de CE traitement ? ». Le canvas
     pose la question dans l'autre sens : un nœud `material` ou `transform` y
     est une CARTE À PART ENTIÈRE, et pour peindre ses champs il faut la
     chaîne à laquelle il appartient — c'est-à-dire son traitement, puisque
     c'est LUI que `editMat`/`editTrs` prennent en argument. Première chaîne
     gagnante, comme le backend (`_chaine_aval`) : un maillon partagé entre
     deux rangées (l'API brute l'autorise, cet écran ne le produit jamais —
     `surnumeraire` REFUSE une cible qui a déjà une arête entrante, C1)
     s'édite au nom de la première — et le bordereau avoue le reste. */
  function rowDuNoeud(graph, nid) {
    if (!graph || !nid) return null;
    const n = (graph.nodes || []).filter((x) => x.id === nid)[0];
    if (!n) return null;
    if (PROC_KINDS.indexOf(n.kind) >= 0) {
      const r = rowModel(graph, nid);
      return (r && r.layer) ? { r: r, role: "proc" } : null;
    }
    const rows = rowsDe(graph);
    for (let i = 0; i < rows.length; i++) {
      const r = rows[i];
      if (r.layer && r.layer.id === nid) return { r: r, role: "layer" };
      if (r.mat && r.mat.id === nid) return { r: r, role: "mat" };
      if (r.trs && r.trs.id === nid) return { r: r, role: "trs" };
    }
    return null;
  }

  /* ── LE CORPS D'UN NŒUD : SA VIGNETTE ET SES MENUS ──────────────────────
     Les champs viennent des bâtisseurs de la liste, sans une balise de plus
     (`procSelHtml`/`geoHtml`/`sideSelHtml`/`mesh3dHtml`/`matHtml`/`trsHtml`).
     Ce que ce corps ajoute, c'est l'AIGUILLAGE : quel jeu de champs pour quel
     kind, et un motif LITTÉRAL quand il n'y en a aucun à montrer (un nœud
     hors chaîne ne sera pas construit — le dire ici évite de le découvrir au
     bordereau).
     `data-proc` EST LA CLÉ DE L'ÉDITION : `onGraphChange` remonte jusqu'à lui
     et appelle `editGraph(procId, …)`. Pour un nœud matière ou placement, ce
     n'est donc PAS son id qui y figure mais celui de SON traitement — c'est
     ce que `editMat`/`editTrs` attendent, et c'est ce qui fait que les mêmes
     handlers servent les deux vues sans une ligne de plus. `data-nid`, lui,
     dit QUEL nœud repeindre. */
  function nodeBodyHtml(nid) {
    const graph = get("graph");
    const n = graph ? (graph.nodes || []).filter((x) => x.id === nid)[0] : null;
    if (!n) return '<div class="cf-forge3d-corps"></div>';
    const lim = (INFO && INFO.graph_limits) || null;
    const att = rowDuNoeud(graph, nid);
    const r = att ? att.r : null;
    let champs = "", proc = "";
    if (n.kind === "layer") {
      champs = (r && att.role === "layer")
        ? ('<div class="cf-forge3d-line">' + sideSelHtml(r.layer) + '</div>')
        : '<p class="hint">couche non reliée à un traitement — elle ne sera '
          + 'pas construite.</p>';
      if (r && att.role === "layer") proc = r.proc.id;
    } else if (PROC_KINDS.indexOf(n.kind) >= 0) {
      champs = r
        ? ('<div class="cf-forge3d-line">' + procSelHtml(n) + geoHtml(n, lim)
          + '</div>' + (n.kind === "mesh3d" ? mesh3dHtml(n) : ""))
        : '<p class="hint">traitement sans couche source — il ne sera pas '
          + 'construit.</p>';
      if (r) proc = n.id;
    } else if (n.kind === "material") {
      champs = (r && att.role === "mat")
        ? matHtml(r, r.proc.kind === "mesh3d", "node")
        : '<p class="hint">matière hors chaîne — aucun traitement ne la '
          + 'porte.</p>';
      if (r && att.role === "mat") proc = r.proc.id;
    } else if (n.kind === "transform") {
      champs = (r && att.role === "trs") ? trsHtml(r, "node")
        : '<p class="hint">placement hors chaîne — aucun traitement ne le '
          + 'porte.</p>';
      if (r && att.role === "trs") proc = r.proc.id;
    } else if (n.kind === "artifact" || n.kind === "export") {
      /* `data-proc` NE DÉSIGNE PAS UN TRAITEMENT : il désigne le nœud AU NOM
         DUQUEL l'édition s'écrit (`editGraph` le cherche par id). Pour une
         matière ou un placement, c'est son traitement ; pour un artefact ou un
         export, c'est lui-même — et les mêmes handlers servent les trois sans
         une ligne de plus. */
      champs = kindHintHtml(n)
        + ((n.kind === "artifact") ? artifactNodeHtml(n) : exportNodeHtml(n));
      proc = n.id;
    } else {
      champs = kindHintHtml(n);
    }
    return '<div class="cf-forge3d-corps" data-nid="' + esc(n.id) + '"'
      + (proc ? ' data-proc="' + esc(proc) + '"' : "") + '>'
      /* L'ARTEFACT N'A PAS DE VIGNETTE : il a mieux — le viewer du RÉSULTAT,
         c'est-à-dire le fichier lui-même. Un pictogramme à côté du modèle
         livré serait du décor, et il pousserait le viewer hors du nœud. */
      + ((n.kind === "artifact") ? "" : thumbHtml(n)) + champs + '</div>';
  }

  /* CE QU'UN NŒUD DIT DE LUI-MÊME — une phrase, la même dans les deux vues.
     Extrait pour que les corps riches (artefact, export) la portent AUSSI :
     le nœud le plus fourni de l'écran ne doit pas être celui qui oublie de
     dire à quoi il sert. */
  function kindHintHtml(n) {
    return '<p class="hint">' + esc(connu(KIND_HINTS, n.kind)
      ? KIND_HINTS[n.kind] : kindLabel(n.kind)) + '</p>';
  }

  /* ── LE NŒUD ARTEFACT (2c Task 5) — LE NOM, L'ACTION, LE RÉSULTAT ───────
     C'est le seul nœud de l'écran qui porte une ACTION de construction ; il
     porte donc aussi ce que cette action a rendu : le viewer du fichier LIVRÉ
     (jamais un rendu inventé — le patron du domaine) et le résumé du
     bordereau MESURÉ. « figer l'aperçu » reste à côté du viewer : c'est
     l'image qui deviendra celle de la carte, elle appartient au résultat. */
  function artifactNodeHtml(n) {
    return '<label class="cf-forge3d-txt">nom<input type="text" '
      + 'data-field="name" maxlength="' + Number(ART_NAME_MAX) + '" value="'
      + esc(n.name || "") + '" placeholder="artefact"></label>'
      + '<div class="cf-forge3d-line">'
      + '<button class="btn primary sm" type="button" data-act="build3d"'
      + (build3d.busy ? " disabled" : "") + '>Construire</button>'
      + '<button class="btn sm" type="button" data-act="freeze"'
      /* LES DEUX CONDITIONS, PAS UNE (voir `FIGE_PRET`) : les octets sont
         livrés ET la scène est décodée. `majFige` dit la même chose au bouton
         DÉJÀ posé ; ici c'est l'état de naissance du bouton. */
      + ((PREVIEW_URL && FIGE_PRET) ? "" : " disabled")
      + ' title="capture le rendu affiché et l\'écrit côté serveur">'
      + 'figer l\'aperçu</button>'
      + '</div>'
      + '<div class="cf-forge3d-art-view"></div>'
      + bordereauHtml(ARTIFACT);
  }

  /* LE RÉSUMÉ DU BORDEREAU — MESURÉ, jamais annoncé. Poids du GLB livré,
     moteurs RÉELLEMENT employés et crédits RÉELLEMENT consommés (ceux des
     job.json, que `elements_detail` porte : la comptabilité du fournisseur,
     pas le devis d'avant), et les aveux au complet. */
  function bordereauHtml(art) {
    if (!art) {
      return '<p class="hint">rien de construit dans cette session — '
        + '« Construire » écrit le GLB, le metadata et (si le solide est '
        + 'fermé) le STL. Les nœuds d\'export s\'allument avec lui.</p>';
    }
    const det = art.elements_detail || [];
    const moteurs = [];
    let credits = 0;
    det.forEach((d) => {
      if (d && d.engine && moteurs.indexOf(d.engine) < 0) moteurs.push(d.engine);
      if (d && d.credits != null) credits += Number(d.credits) || 0;
    });
    return '<p class="mono">' + Number(art.elements) + ' élément(s) · '
      + esc(weight(art.glb.bytes))
      + (moteurs.length ? (" · " + esc(moteurs.join(", "))) : "")
      + (credits > 0 ? (" · " + Number(credits) + " cr consommés") : "")
      + '</p>' + ignoresHtml(art);
  }

  /* LES AVEUX DU BACKEND, UNE SEULE ÉCRITURE. La section « Construire » et le
     nœud artefact montrent LES MÊMES `ignored` : deux rendus auraient dérivé,
     et c'est précisément la ligne qu'on n'a pas le droit de laisser
     diverger. */
  function ignoresHtml(art) {
    const list = (art && art.ignored) || [];
    if (!list.length) return "";
    return '<p class="hint"><b>éléments ignorés</b> — avoués, jamais tus :</p>'
      + '<ul class="cf-forge3d-ignored">'
      + list.map((i) => '<li class="mono">' + esc(i.node) + " · " + esc(i.why)
        + '</li>').join("")
      + '</ul>';
  }

  /* UNE LIGNE DE FICHIER LIVRÉ — le même balisage pour la section et pour un
     nœud d'export : un fichier livré est un fichier livré. Le téléchargement
     passe par la PROVENANCE (`grabZip` -> `M.api.blob`), jamais un <a href>.
     `octets` peut être absent (l'aperçu figé n'annonce son poids qu'au moment
     où il est écrit) : on tait alors le chiffre plutôt que d'écrire « 0 o ». */
  function fichierHtml(label, nom, octets) {
    return '<div class="cf-forge3d-file"><span class="mono">' + esc(label)
      + " · " + esc(nom) + esc(octets == null ? "" : (" · " + weight(octets)))
      + '</span>'
      + '<button class="btn sm" type="button" data-act="grab-file" data-name="'
      + esc(nom) + '">télécharger</button></div>';
  }

  /* LES FORMATS SONT SERVIS, JAMAIS RECOPIÉS — `graph_limits.export_formats`
     (/info), miroir du tuple `EXPORT_FORMATS` du backend. Une liste écrite ici
     aurait dérivé au premier format ajouté, et l'écran aurait proposé un
     téléchargement qui n'existe pas (ou tu un qui existe). */
  function exportFormats() {
    const lim = (INFO && INFO.graph_limits) || null;
    const f = lim && lim.export_formats;
    return Array.isArray(f) ? f.filter((x) => typeof x === "string") : [];
  }

  /* ── LES NŒUDS D'EXPORT (2c Task 5) — DES POINTS DE TÉLÉCHARGEMENT ──────
     Ils n'éteignent RIEN du bordereau : le résolveur les ignore SANS les
     avouer (ce ne sont pas des éléments, c'est écrit dans `clean_graph`). Ce
     qu'ils portent, c'est l'état du format qu'ils désignent, DEPUIS le dernier
     bordereau — et un format qui n'a pas été écrit dit POURQUOI, au motif
     littéral du serveur. Jamais un nœud muet. */
  function exportNodeHtml(n) {
    const fmts = exportFormats();
    const fmt = String(n.format || fmts[0] || "");
    const sel = fmts.length
      ? ('<label class="cf-forge3d-sel">format<select data-field="format">'
        + fmts.map((f) => '<option value="' + esc(f) + '"'
          + (f === fmt ? " selected" : "") + '>' + esc(f) + '</option>').join("")
        + '</select></label>')
      : ('<span class="hint"><b>formats inconnus</b> — le contrat /info n\'a '
        + 'pas été chargé (backend injoignable ?).</span>');
    return sel + exportEtatHtml(fmt);
  }

  function exportEtatHtml(fmt) {
    const art = ARTIFACT;
    if (!art) {
      /* UN ÉTAT, PAS UNE ERREUR : rien n'a échoué, rien n'a encore été
         construit. Le dire en rouge apprendrait à craindre un écran neuf. */
      return '<p class="hint">construis d\'abord l\'artefact — ce point de '
        + 'téléchargement s\'allume avec le bordereau.</p>';
    }
    if (fmt === "glb") return fichierHtml("GLB", art.glb.name, art.glb.bytes);
    if (fmt === "metadata") {
      return fichierHtml("metadata.json", art.metadata.name, art.metadata.bytes);
    }
    if (fmt === "stl") {
      /* LE MOTIF DU REFUS, TEL QUEL (`art.stl.why`) — jamais réécrit par
         l'écran : c'est la mesure du solide fermé qui parle. */
      return (art.stl && art.stl.written)
        ? fichierHtml("STL", art.stl.name, art.stl.bytes)
        : ('<p class="hint"><b>STL non fourni</b> : '
          + esc((art.stl && art.stl.why) || "motif non rendu par le backend")
          + '</p>');
    }
    if (fmt === "preview") {
      const p = art.preview || {};
      return p.written
        ? fichierHtml("aperçu", p.expected, (p.bytes == null) ? null : p.bytes)
        : ('<p class="hint">aperçu <b>attendu</b> (' + esc(p.expected)
          + ') — « figer l\'aperçu », sur le nœud artefact, l\'écrit.</p>');
    }
    return '<p class="hint">le bordereau ne livre pas « ' + esc(fmt)
      + ' » — choisis un autre format.</p>';
  }

  /* la zone de vignette : un canvas 2D à la surface de dessin FIXE (la
     feuille décide de la taille affichée). `cf-forge3d-plan` porte la légère
     perspective du kind `plane` — de la présentation pure, donc CSS. */
  function thumbHtml(n) {
    return '<canvas class="cf-forge3d-thumb'
      + (n.kind === "plane" ? " cf-forge3d-plan" : "")
      + '" width="' + THUMB_W + '" height="' + THUMB_H
      + '" aria-hidden="true"></canvas>';
  }

  /* ═══════════════════════════════════════════════════════════════════════
     LES VIGNETTES — CANVAS 2D, LOCALES, DÉTERMINISTES (2c Task 3)
     Trois engagements, tenus par construction :
       · AUCUN ALÉA. Rien ici n'appelle `Math.random` (c'est épinglé au test
         de source, sur tout le fichier) : deux ouvertures du même graphe
         peignent les mêmes pixels.
       · AUCUN RÉSEAU QUE LA PROVENANCE. Les seules images chargées sont la
         PNG de couche (`file/<nom>`) et la vignette de boutique d'une
         matière (`material-thumb/<mid>`), toutes deux par `M.api.blob` —
         donc confinées au sous-préfixe de la pièce (règle 8) et mises en
         cache par clé. Une image ABSENTE (404) est mémorisée comme absente :
         on retombe sur un aplat, on ne redemande pas en boucle.
       · AUCUNE DÉPENSE. Rien de ce qui est dessiné ici ne fait tourner un
         moteur : c'est du dessin, pas un rendu.
     LE preview.png D'UN JOB EST SERVI DEPUIS LA TASK 5 — et le chemin qu'a
     pris ce manque vaut d'être écrit. Un job meshy rapatrie sa vignette dans
     `nodes/{nid}/preview.png`, mais la seule route de fichiers de la pièce,
     `GET /file/{name}`, valide le nom sur `^[A-Za-z0-9._-]{1,90}$` : le
     séparateur y est interdit, donc rien sous `nodes/` n'était atteignable.
     La Task 3 a donc pris la branche « à défaut » du plan (pictogramme moteur
     + état lu) et REMONTÉ le manque, plutôt que d'ouvrir une route en douce
     depuis l'écran — décider seul d'une surface d'API n'appartient pas à un
     module. La Task 5 l'ouvre : `GET node-file/{nid}/{name}`, à LISTE BLANCHE
     (le dossier d'un nœud porte aussi `job.json` et des textures payées ; seul
     l'aperçu est un affichage public). Le repli, lui, reste — un moteur ne
     rapatrie pas toujours de vignette. */
  const IMGS = sansProto();     /* clé de provenance -> toile réduite | null */
  const IMGS_VOL = sansProto(); /* les chargements EN VOL -> leur GÉNÉRATION */
  const IMGS_AT = sansProto();  /* l'instant de mise en cache (I3, re-sonde) */
  /* L'ÉPOQUE DU CACHE — le jeton que `GEN` ne pouvait pas porter. `GEN` dit
     « ce n'est plus le même deck (ou la même carte) » ; il ne bouge PAS quand
     une FACE vient d'être livrée, or c'est là que le cache est vidé aussi
     (I3a : les octets sous ce nom viennent d'être réécrits). Un chargeur
     parti AVANT l'export revenait donc après le vidage, voyait sa génération
     inchangée, et re-posait dans le cache les octets PRÉ-export — les
     vignettes affichaient l'ancienne carte jusqu'au changement de deck, sans
     le moindre signe. L'époque est incrémentée par CHAQUE vidage, quelle
     qu'en soit la raison ; un chargement la capture avant ses attentes et se
     tait si elle a bougé. */
  let IMGS_EPOQUE = 1;          /* commence à 1 : zéro serait un jeton FAUX */

  /* I2 — CE QUI EST GARDÉ EST UNE RÉDUCTION, PAS LE BITMAP LIVRÉ.
     Une couche est rendue à la définition de la CARTE : 63 x 88 mm à 1200 dpi
     font 2977 x 4157 px, soit 12,4 Mpx — et un bitmap décodé coûte 4 octets
     par pixel, donc ~49 Mo. Six couches (le graphe par défaut) : ~297 Mo
     retenus pour toute la session, pour peindre des vignettes de 120 x 168.
     On blitte donc UNE fois dans une toile de 240 x 336 — le double de la
     surface de dessin, de quoi rester net si la feuille change d'avis sur la
     taille affichée — et c'est ELLE qu'on garde : 240 x 336 x 4 = 322 Kio par
     couche, ~1,9 Mio pour six. Rapport ~1/155. La silhouette d'emboss, qui
     redessine l'image dans une toile de travail, y gagne d'autant.
     Une toile est `drawImage`-able et porte `width`/`height` comme une image :
     rien en aval ne sait la différence. */
  const CACHE_W = 240, CACHE_H = 336;

  function retaille(img) {
    if (typeof document === "undefined") return img;
    const iw = Number(img.width) || 1, ih = Number(img.height) || 1;
    /* jamais d'AGRANDISSEMENT : une couche déjà petite se garde telle quelle
       (l'étirer ne lui rendrait pas les pixels qu'elle n'a pas). */
    const k = Math.min(1, CACHE_W / iw, CACHE_H / ih);
    if (k >= 1) return img;
    const c = document.createElement("canvas");
    c.width = Math.max(1, Math.round(iw * k));
    c.height = Math.max(1, Math.round(ih * k));
    const g = c.getContext ? c.getContext("2d") : null;
    if (!g) return img;      /* pas de 2d : garder l'original vaut mieux que rien */
    g.drawImage(img, 0, 0, c.width, c.height);
    return c;
  }

  function oublieLesImages() {
    /* L'ÉPOQUE D'ABORD (même ordre que `oublieLesJobs` avec `GEN`) : les
       chargements déjà en vol se taisent, et ceux qui repartiront sous
       l'époque neuve ne pourront pas être effacés par eux. */
    IMGS_EPOQUE += 1;
    [IMGS, IMGS_VOL, IMGS_AT].forEach((reg) => {
      Object.keys(reg).forEach((k) => { delete reg[k]; });
    });
  }

  /* I3b — LE no-store DU BACKEND EST UN ORDRE, et un cache de session ne peut
     pas le contredire au-delà d'une fenêtre courte. `material-thumb` le sert
     précisément parce qu'une vignette CHANGE sous le même `mid` : la boutique
     la (re)capture, et une matière sans vignette en gagne une. Or un 404
     mémorisé était DÉFINITIF — capturer la vignette après un premier coup
     d'œil laissait le nœud afficher « sans vignette » jusqu'au changement de
     deck. On périme donc les entrées `mat:` (les nulles COMPRISES, ce sont
     elles qui pourrissaient) au-delà de la fenêtre, et la peinture suivante
     redemande. Même cadence et même raison que le `REPROBE_MS` de la 2b : ce
     n'est pas un poll, c'est le droit de changer d'avis. */
  const THUMB_REPROBE_MS = 30000;

  function reSondeLesMatieres(graph) {
    const t = Date.now();
    ((graph && graph.nodes) || []).forEach((n) => {
      if (n.kind !== "material" || !n.mat) return;
      const cle = "mat:" + n.mat;
      if (!connu(IMGS, cle)) return;
      if ((t - (connu(IMGS_AT, cle) ? IMGS_AT[cle] : 0)) <= THUMB_REPROBE_MS) return;
      delete IMGS[cle];
      delete IMGS_AT[cle];
    });
  }

  /* LE NOM DU FICHIER D'UNE COUCHE — miroir de `_layer_filename`
     (forge3d.py:1214), comme `chargeManifeste` l'est déjà de
     `layers_{label}_{side}.json`. Le manifeste ne peut PAS servir de source :
     l'écran n'en charge que le RECTO, alors qu'un nœud couche peut viser le
     verso. Un nom faux ne ment pas — il 404, et la vignette retombe sur son
     aplat. */
  function layerFile(l) {
    const side = (l && l.side === "back") ? "back" : "front";
    const role = (l && !l.composite && l.role) ? l.role : "composite";
    return role + "_" + cardLabel() + "_" + side + ".png";
  }

  /* une image de provenance : rendue si connue, `null` si connue-absente,
     `undefined` tant qu'elle se charge (le peintre dessine alors son repli et
     sera rappelé au retour). */
  function imageDeProvenance(cle, sub) {
    if (connu(IMGS, cle)) return IMGS[cle];
    chargeImage(cle, sub);
    return undefined;
  }

  async function chargeImage(cle, sub) {
    if (connu(IMGS, cle) || connu(IMGS_VOL, cle)) return;
    /* GARDE DE GÉNÉRATION (2b Task 7) : un blob du deck (ou de la carte)
       précédent ne doit ni entrer dans le cache ni déclencher une peinture
       dans l'écran du suivant. Le contrôle se refait APRÈS chaque await —
       le décodage en est un aussi.
       M5 — LE REGISTRE PORTE LA GÉNÉRATION, PAS `true` : c'est la doctrine du
       jeton, déjà écrite dans ce fichier pour `POLLS` (« un tic rassis ne
       retire que SA PROPRE entrée, jamais celle de son successeur »). Un
       chargement rassis qui effacerait l'entrée de son successeur rouvrirait
       la porte à un second chargement du même octet — et, pire, ferait de
       `IMGS_VOL` un verrou qui ment. */
    const gen = GEN, ep = IMGS_EPOQUE;
    IMGS_VOL[cle] = gen;
    /* le relâché est GARDÉ PAR L'ÉPOQUE, pas seulement par la génération : un
       vidage a pu remettre la même génération en vol sous cette clé, et
       effacer l'entrée du successeur ferait de `IMGS_VOL` un verrou qui ment
       (deux chargements du même octet). */
    const relache = () => {
      if (ep === IMGS_EPOQUE && IMGS_VOL[cle] === gen) delete IMGS_VOL[cle];
    };
    let img = null;
    try {
      const b = await M.api.blob("GET", sub);
      if (gen !== GEN || ep !== IMGS_EPOQUE) { relache(); return; }
      img = await decodeBlob(b);
    } catch (e) {
      img = null;         /* absente ou refusée : un aplat, jamais une panne */
    }
    if (gen !== GEN || ep !== IMGS_EPOQUE) { relache(); return; }
    IMGS[cle] = img ? retaille(img) : null;
    IMGS_AT[cle] = Date.now();
    relache();
    demandeRepeintVignettes();
  }

  /* l'objectURL est révoquée DANS les deux issues : une vignette de nœud est
     un geste répété (chaque bascule de vue en redemande), et une URL par
     image retenue à vie serait une fuite lente — le patron `mountPreview`
     appliqué à un cas où l'image, elle, survit à son URL. */
  function decodeBlob(b) {
    return new Promise((resolve) => {
      if (typeof Image !== "function" || typeof URL === "undefined") {
        resolve(null);
        return;
      }
      const u = URL.createObjectURL(b);
      const im = new Image();
      im.onload = () => { URL.revokeObjectURL(u); resolve(im); };
      im.onerror = () => { URL.revokeObjectURL(u); resolve(null); };
      im.src = u;
    });
  }

  /* LES COULEURS VIENNENT DU THÈME, jamais d'une constante d'ici : un canvas
     2D ne connaît pas les variables CSS, on les LIT donc sur l'élément (la
     feuille reste la seule source, y compris en thème clair). */
  function encres(el) {
    const cs = (typeof getComputedStyle === "function") ? getComputedStyle(el) : null;
    const jeton = (nom, repli) => {
      const v = cs ? String(cs.getPropertyValue(nom) || "").trim() : "";
      return v || repli;
    };
    return {
      fond: jeton("--bg-panel-3", "#14141a"),
      trait: jeton("--stroke-strong", "#4a4a55"),
      encre: jeton("--ink-muted", "#9a9aa6"),
      fort: jeton("--ink-strong", "#e8e8ee"),
      accent: jeton("--accent", "#e0a33a"),
    };
  }

  function boiteContenue(iw, ih) {
    const k = Math.min(THUMB_W / Math.max(1, iw), THUMB_H / Math.max(1, ih));
    const w = (iw || 1) * k, h = (ih || 1) * k;
    return { x: (THUMB_W - w) / 2, y: (THUMB_H - h) / 2, w: w, h: h };
  }

  /* le damier d'alpha : une couche est une PNG à trous, et l'afficher sur un
     aplat laisserait croire à un fond opaque qui n'existe pas. Même repère
     que les vignettes du bordereau (mod-forge3d.css:.cf-forge3d-lay img). */
  function damier(ctx, enc) {
    const pas = 10;
    for (let y = 0; y < THUMB_H; y += pas) {
      for (let x = 0; x < THUMB_W; x += pas) {
        if (((x / pas) + (y / pas)) % 2 !== 0) continue;
        ctx.fillStyle = enc.trait;
        ctx.globalAlpha = 0.18;
        ctx.fillRect(x, y, pas, pas);
      }
    }
    ctx.globalAlpha = 1;
  }

  function texteCentre(ctx, enc, txt, y, taille, couleur) {
    ctx.fillStyle = couleur || enc.encre;
    ctx.font = taille + "px system-ui, -apple-system, Segoe UI, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(String(txt == null ? "" : txt), THUMB_W / 2, y, THUMB_W - 8);
  }

  /* le pictogramme d'un kind, en grand — le contenu de vignette d'un nœud
     qui n'a pas de pixels à lui. */
  function dessinePicto(ctx, enc, kind, sous) {
    texteCentre(ctx, enc, connu(PICTO, kind) ? PICTO[kind] : PICTO_DEFAUT,
                THUMB_H / 2 - 12, 44, enc.trait);
    if (sous) texteCentre(ctx, enc, sous, THUMB_H / 2 + 26, 11, enc.encre);
  }

  /* LA SILHOUETTE TEINTÉE d'une image — pur canvas 2D : on redessine l'image
     dans une toile de travail puis on la remplit en `source-in`, ce qui ne
     garde que ses pixels opaques. C'est ce qui permet l'ombre d'emboss du
     relief SANS toucher au fond déjà peint (un `fillRect` en `source-atop`
     sur la toile principale teinterait tout, fond compris). */
  function silhouette(img, teinte) {
    if (typeof document === "undefined") return null;
    const c = document.createElement("canvas");
    c.width = THUMB_W; c.height = THUMB_H;
    const g = c.getContext ? c.getContext("2d") : null;
    if (!g) return null;
    const b = boiteContenue(img.width, img.height);
    g.drawImage(img, b.x, b.y, b.w, b.h);
    g.globalCompositeOperation = "source-in";
    g.fillStyle = teinte;
    g.fillRect(0, 0, THUMB_W, THUMB_H);
    return c;
  }

  /* les millimètres de la carte : ceux du manifeste quand il est chargé,
     sinon le format de référence — c'est une ÉCHELLE D'ESQUISSE (le tracé de
     placement), jamais une mesure envoyée à quoi que ce soit. */
  function carteMm() {
    const m = LAST_MANIFEST && LAST_MANIFEST.size_mm;
    const w = Array.isArray(m) ? Number(m[0]) : 0;
    const h = Array.isArray(m) ? Number(m[1]) : 0;
    return (isFinite(w) && w > 0 && isFinite(h) && h > 0) ? [w, h] : [63, 88];
  }

  /* LA VIGNETTE D'UN NŒUD — repeinte à chaque édition qui la concerne.
     Elle ne LIT que le graphe et le cache d'images : aucune requête n'est
     lancée depuis ce peintre (c'est `imageDeProvenance` qui décide, une
     fois par clé). */
  function paintNodeThumb(nid) {
    const noeud = findByAttr(".cf-forge3d-noeud", "data-nid", nid);
    const cv = noeud ? noeud.querySelector(".cf-forge3d-thumb") : null;
    if (!cv || !cv.getContext) return;
    const graph = get("graph");
    const n = graph ? (graph.nodes || []).filter((x) => x.id === nid)[0] : null;
    const ctx = cv.getContext("2d");
    if (!ctx || !n) return;
    const enc = encres(cv);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = 1;
    ctx.clearRect(0, 0, THUMB_W, THUMB_H);
    ctx.fillStyle = enc.fond;
    ctx.fillRect(0, 0, THUMB_W, THUMB_H);
    const att = rowDuNoeud(graph, nid);
    const r = att ? att.r : null;
    if (n.kind === "material") thumbMatiere(ctx, enc, n);
    else if (n.kind === "mesh3d") thumbMesh3d(ctx, enc, n);
    else if (n.kind === "layer") thumbCouche(ctx, enc, n, 1);
    else if (n.kind === "plane") thumbCouche(ctx, enc, r && r.layer, 1);
    else if (n.kind === "relief") thumbRelief(ctx, enc, n, r && r.layer);
    else if (n.kind === "transform") thumbPlacement(ctx, enc, n, r && r.layer);
    else dessinePicto(ctx, enc, n.kind, kindLabel(n.kind));
    ctx.strokeStyle = enc.trait;
    ctx.lineWidth = 1;
    ctx.strokeRect(0.5, 0.5, THUMB_W - 1, THUMB_H - 1);
  }

  /* la PNG de couche, telle qu'elle a été livrée */
  /* la PNG de couche, telle qu'elle a été livrée. `dec` (M7) est l'ombre
     d'emboss du relief : elle se peint DANS la même passe, entre le damier et
     l'image — la version d'avant peignait la couche, puis effaçait tout pour
     la repeindre avec son ombre, soit deux fois le travail à chaque frappe. */
  function thumbCouche(ctx, enc, l, alpha, dec) {
    if (!l) { dessinePicto(ctx, enc, "layer", "sans couche source"); return; }
    const cle = layerFile(l);
    const img = imageDeProvenance("couche:" + cle, "file/" + encodeURIComponent(cle));
    if (!img) {
      damier(ctx, enc);
      dessinePicto(ctx, enc, "layer",
                   (img === null) ? "couche non exportée" : "chargement…");
      return;
    }
    damier(ctx, enc);
    const b = boiteContenue(img.width, img.height);
    if (dec > 0) {
      const ombre = silhouette(img, "#000000");
      if (ombre) {
        ctx.globalAlpha = 0.5;
        ctx.drawImage(ombre, dec, dec);
        ctx.globalAlpha = 1;
      }
    }
    ctx.globalAlpha = (alpha == null) ? 1 : alpha;
    ctx.drawImage(img, b.x, b.y, b.w, b.h);
    ctx.globalAlpha = 1;
    return b;
  }

  /* l'EMBOSS : la même couche, doublée d'une silhouette sombre décalée — le
     décalage est PROPORTIONNEL à `depth_mm`, donc éditer la profondeur fait
     réagir la vignette (c'est ce que la Task 3 promet, et `valeurVue` fait
     que la promesse vaut AUSSI pour une profondeur tapée au clavier, pas
     seulement pour un cran de spinner). Le décalage est borné : au-delà,
     l'esquisse ne dirait rien de plus. */
  function thumbRelief(ctx, enc, n, l) {
    const d = Math.max(0, Math.min(6,
      Number(valeurVue(n.id, "depth_mm", n.depth_mm)) || 0));
    const b = thumbCouche(ctx, enc, l, 1, Math.round(d * 2.2));
    if (!b) return;
    texteCentre(ctx, enc, d.toFixed(2) + " mm", THUMB_H - 10, 10, enc.accent);
  }

  /* le PLACEMENT, esquissé : la couche en sourdine, et le cadre de l'élément
     là où le nœud le pose (décalage, rotation, échelle). Le y descend à
     l'écran et monte dans la scène — l'esquisse le retourne, comme le
     writer. C'est un TRAIT, pas un rendu : le vrai 3D est l'affaire du
     viewer. */
  function thumbPlacement(ctx, enc, n, l) {
    const b = thumbCouche(ctx, enc, l, 0.32);
    const mm = carteMm();
    const ppmm = THUMB_W / mm[0];
    const cadre = b || boiteContenue(mm[0], mm[1]);
    /* les quatre valeurs passent par `valeurVue` : le trait bouge sous une
       coordonnée TAPÉE, pas seulement sous un cran de spinner (M10). */
    const lu = (f) => Number(valeurVue(n.id, f, n[f])) || 0;
    const s = Math.max(0.05, Math.min(8,
      Number(valeurVue(n.id, "scale", n.scale)) || 1));
    ctx.save();
    ctx.translate(THUMB_W / 2 + lu("x_mm") * ppmm,
                  THUMB_H / 2 - lu("y_mm") * ppmm);
    ctx.rotate(lu("rot_deg") * Math.PI / 180);
    ctx.strokeStyle = enc.accent;
    ctx.lineWidth = 1.5;
    ctx.strokeRect(-cadre.w * s / 2, -cadre.h * s / 2, cadre.w * s, cadre.h * s);
    ctx.restore();
  }

  /* LA MATIÈRE : la vignette de la boutique en fond (par la route de
     provenance), un bandeau de finition, et le badge d'anisotropie. Une
     matière sans vignette servie (jamais capturée, ou PÉRIMÉE : le backend
     rend 404 pour les deux) tombe sur un aplat neutre — le même repli que la
     boutique s'accorde pour sa propre galerie. */
  function thumbMatiere(ctx, enc, n) {
    const mid = n.mat ? String(n.mat) : "";
    const img = mid
      ? imageDeProvenance("mat:" + mid, "material-thumb/" + encodeURIComponent(mid))
      : null;
    if (img) {
      /* COUVRIR, pas contenir : une matière est une texture, ses bords ne
         portent rien — la montrer en entier avec des marges la rendrait
         moins lisible qu'un fragment plein cadre. */
      const k = Math.max(THUMB_W / Math.max(1, img.width),
                         THUMB_H / Math.max(1, img.height));
      const w = img.width * k, h = img.height * k;
      ctx.drawImage(img, (THUMB_W - w) / 2, (THUMB_H - h) / 2, w, h);
    } else {
      ctx.fillStyle = enc.trait;
      ctx.globalAlpha = 0.35;
      ctx.fillRect(8, 8, THUMB_W - 16, THUMB_H - 16);
      ctx.globalAlpha = 1;
      dessinePicto(ctx, enc, "material",
                   mid ? "sans vignette" : "aucune matière");
    }
    const fin = n.finish ? String(n.finish) : "";
    if (fin && fin !== "aucune") {
      const y = THUMB_H - 34;
      const stops = connu(HOLO, fin) ? HOLO[fin] : HOLO_DEFAUT;
      const g = ctx.createLinearGradient(0, y, THUMB_W, y + 20);
      g.addColorStop(0, stops[0]);
      g.addColorStop(0.5, stops[1]);
      g.addColorStop(1, stops[2]);
      ctx.fillStyle = g;
      ctx.globalAlpha = 0.85;
      ctx.fillRect(0, y, THUMB_W, 20);
      ctx.globalAlpha = 1;
      texteCentre(ctx, enc, fin, y + 10, 10, "#1a1a1f");
    }
    if (n.aniso) {
      ctx.fillStyle = enc.accent;
      ctx.globalAlpha = 0.9;
      ctx.fillRect(6, 6, 42, 15);
      ctx.globalAlpha = 1;
      ctx.fillStyle = "#1a1a1f";
      ctx.font = "9px system-ui, -apple-system, Segoe UI, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("aniso", 27, 14);
    }
  }

  /* LE MOTEUR : la VIGNETTE QUE SON JOB A RAPATRIÉE quand elle existe, son
     pictogramme sinon — et, dans les deux cas, l'état LU du job (jamais
     l'intention envoyée).
     LA BRANCHE PRINCIPALE EXISTE ENFIN (Task 5). Le `preview.png` d'un job
     meshy vit sous `nodes/{nid}/` et n'était servi par AUCUNE route : la
     Task 3 a REMONTÉ le manque au contrôleur plutôt que d'ouvrir une surface
     d'API en douce, et `GET node-file/{nid}/{name}` l'ouvre maintenant, par
     LISTE BLANCHE (le dossier d'un nœud porte aussi job.json et des textures
     payées). Le pictogramme reste le « à défaut » du plan : job jamais lancé,
     moteur qui ne rapatrie pas de vignette, 404.
     LA CLÉ DU CACHE PORTE LE `run_id`, et ce n'est pas une précaution
     gratuite : une relance EFFACE le dossier du nœud et réécrit `preview.png`
     SOUS LE MÊME NOM. Une clé sans run servirait les pixels du modèle d'avant
     à côté de l'état d'après — la faute du cache pré-export (I3a), rejouée un
     étage plus bas. */
  function thumbMesh3d(ctx, enc, n) {
    const eng = engineFor(n);
    const job = connu(JOBS, n.id) ? JOBS[n.id] : undefined;
    let etat = "jamais lancé";
    let couleur = enc.encre;
    if (job === undefined) etat = "état non lu";
    else if (job === null) etat = "jamais lancé";
    else if (job.status === "served") { etat = "servi"; couleur = enc.fort; }
    else if (job.status === "failed") etat = "échec";
    else if (job.status === "running") {
      etat = "en cours " + Number(job.progress || 0) + " %";
      couleur = enc.accent;
    } else if (job.status === "queued") { etat = "en file"; couleur = enc.accent; }
    const fichiers = (job && job.files) || null;
    const nom = (job && job.status === "served" && fichiers && fichiers.preview)
      ? String(fichiers.preview) : "";
    const img = nom
      ? imageDeProvenance(
        "noeud:" + n.id + ":" + String(job.run_id || "") + ":" + nom,
        "node-file/" + encodeURIComponent(n.id) + "/" + encodeURIComponent(nom))
      : null;
    if (img) {
      /* CONTENIR, pas couvrir : un rendu de moteur est un OBJET (pas une
         texture) — le rogner lui couperait ce qu'on veut justement voir. */
      const b = boiteContenue(img.width, img.height);
      ctx.drawImage(img, b.x, b.y, b.w, b.h);
      texteCentre(ctx, enc, (eng && eng.label) || n.engine || "moteur", 12, 10,
                  enc.encre);
    } else {
      dessinePicto(ctx, enc, "mesh3d",
                   (eng && eng.label) || n.engine || "moteur");
    }
    texteCentre(ctx, enc, etat, THUMB_H - 22, 11, couleur);
  }

  /* toutes les vignettes de la vue courante — appelé quand une image vient
     d'arriver (une seule fois par clé : le cache tient la suite).
     COALESCÉ AU rAF, et pour la même raison que le glisser (§9.6-1) : à
     l'ouverture d'un graphe, SEPT images partent d'un coup et reviennent dans
     la même poignée de frames. Un balayage complet par arrivée, c'est du
     travail par ÉVÉNEMENT qui croît avec la taille du graphe — la faute que
     `majAretes` a déjà corrigée sur les arêtes incidentes. Une frame, un
     balayage : les six autres images sont déjà en cache quand il passe. */
  let vignRaf = 0;

  function demandeRepeintVignettes() {
    if (!vignRaf) vignRaf = scheduleFrame(repeintLesVignettes);
  }

  function repeintLesVignettes() {
    vignRaf = 0;
    if (VUE !== "canvas") return;
    const graph = get("graph");
    if (!graph) return;
    (graph.nodes || []).forEach((n) => { paintNodeThumb(n.id); });
  }

  function paintCanvas() {
    const host = $("#cf-forge3d-canvas");
    if (!host) return;
    cardChanged();          /* le même filet que paintGraph (legs 5) */
    const monde = host.querySelector(".cf-forge3d-monde");
    const vide = host.querySelector(".cf-forge3d-vide");
    const graph = get("graph");
    if (!graph) {
      /* le graphe vient de disparaître SOUS le geste (annuler le tout premier
         semis, en plein glisser) : le pointeur capturé écrirait ensuite dans
         un LAYOUT_VU vidé, et le relâché patcherait une carte d'une seule
         entrée — voir `videCanvas` pour le détail du dégât. */
      DRAG = null;
      fermeFantome();
      ARETE = null;
      /* et le drapeau tombe avec lui : le laisser armé sur une carte vidée
         laissait un `videCanvas` ultérieur écrire `{}` au document sur la foi
         d'un geste qui ne décrit plus rien. */
      LAYOUT_SALE = false;
      LAYOUT_VU = sansProto();
      if (monde) monde.innerHTML = "";
      if (vide) {
        vide.innerHTML = LAST_MANIFEST
          ? ('<p class="hint">Aucun graphe construit pour le moment.</p>'
            + seedButtonHtml("cf-forge3d-canvas-seed",
                             "construire le graphe par défaut"))
          : '<p class="hint">Exportez les couches d\'abord (section ci-dessus) '
            + 'pour proposer un graphe par défaut.</p>';
      }
      paintCost();
      return;
    }
    if (vide) vide.innerHTML = "";
    /* les positions MANQUANTES sont semées ici, et le semis part au document
       par LA MÊME paire rAF que le glisser : un seul patch, hors de la pile
       d'appel de la peinture (patcher en plein rendu ferait repeindre pendant
       qu'on peint). */
    LAYOUT_VU = seedLayout(graph);
    if (layoutDiffere(get("layout"), LAYOUT_VU)) demandeFlushLayout();
    const nodes = graph.nodes || [];
    let mx = 0, my = 0;
    nodes.forEach((n) => {
      const p = posDe(n.id) || [0, 0];
      if (p[0] > mx) mx = p[0];
      /* l'etendue est calculee AVANT que le DOM n'existe : c'est la seule
         place ou la table d'arrangement fait foi (le cadrage, lui, mesure). */
      const bas = p[1] + rangH(n.kind);
      if (bas > my) my = bas;
    });
    const ext = { w: mx + NOEUD_W + 80, h: my + 80 };
    if (monde) {
      monde.style.width = ext.w + "px";
      monde.style.height = ext.h + "px";
      monde.innerHTML = edgesHtml(graph, ext)
        + nodes.map((n) => canvasNodeHtml(n)).join("");
    }
    /* la fenêtre de fraîcheur des vignettes de matière s'ouvre ICI, une fois
       par peinture (I3b) : périmer avant de peindre, jamais pendant. */
    reSondeLesMatieres(graph);
    /* les vignettes se peignent APRÈS l'insertion : un canvas hors du
       document n'a pas encore ses variables de thème (les encres se lisent
       sur l'élément) — et il n'y a rien à peindre avant qu'il existe. */
    nodes.forEach((n) => { paintNodeThumb(n.id); });
    /* l'arête désignée a survécu à la reconstruction du monde (le tracé est
       neuf, `ARETE` ne l'était pas) : on lui rend sa classe et son bouton —
       ou on la lâche, si le graphe repeint ne la porte plus. */
    majSelArete();
    appliqueCam();
    /* LE VIEWER DU RÉSULTAT VIENT D'ÊTRE DÉTACHÉ par l'`innerHTML` ci-dessus
       (il vit DANS le nœud artefact) : on le RE-ACCROCHE, sans re-télécharger
       — `PREVIEW_URL` tient toujours les octets déjà livrés. */
    remonteApercu();
    /* ... et l'inspecteur retrouve son sujet : revenir sur le canvas après un
       détour par la liste doit remontrer le nœud désigné, pas un panneau vide
       (`videInspecteur` a remis la clé à zéro, donc ceci re-déclenche). */
    majInspecteur();
    sondeMoteurs(graph);
    paintCost();
  }

  /* ═══════════════════════════════════════════════════════════════════════
     L'INSPECTEUR PARTAGÉ (2c Task 5) — LE VRAI 3D DU NŒUD DÉSIGNÉ
     UN SEUL model-viewer pour toute la sélection : c'est le premier des DEUX
     contextes WebGL de cet écran (le second est le viewer du RÉSULTAT, dans
     le nœud artefact). Trois engagements, tenus par construction :
       · IL NE DÉPENSE RIEN. `POST node-preview` construit un plan ou un
         relief SUR PLACE (grille plafonnée pour la vitesse) et, pour un
         mesh3d, se contente de servir le GLB DÉJÀ payé par son job — il ne
         lance jamais un moteur. La seule dépense de cet écran reste
         « Lancer », et elle est ailleurs.
       · IL NE PARAPHRASE PAS. Un nœud sans aperçu n'est pas une erreur de
         l'écran : c'est le backend qui NOMME pourquoi (kind non
         prévisualisable, couche source absente, job pas encore servi, GLB
         trop lourd pour l'inspecteur — ce dernier pointant vers le nœud
         artefact). Son motif part TEL QUEL, et comme un ÉTAT : rien n'a
         échoué.
       · IL AVOUE. Le GLB d'aperçu porte les mêmes `ignored` que le bordereau
         (`extras.ignored`) : ce que la résolution a écarté est LU côté client
         et rendu en clair. Un aperçu qui montrerait un élément nu sans dire
         que sa matière a été écartée mentirait par omission.
     ═══════════════════════════════════════════════════════════════════════ */

  /* CE QUE L'INSPECTEUR DIT — l'état littéral. `mauvais` n'est PAS « le nœud
     n'a pas d'aperçu » (c'est un état) mais « quelque chose est cassé » :
     seule une panne de transport ou un 5xx y a droit. */
  function inspEtat(txt, mauvais) {
    const el = $("#cf-forge3d-insp-etat");
    if (!el) return;
    el.textContent = String(txt == null ? "" : txt);
    el.classList.toggle("cf-forge3d-insp-ko", !!mauvais);
  }

  function inspNom(txt) {
    const el = $("#cf-forge3d-insp-nom");
    if (el) el.textContent = String(txt == null ? "" : txt);
  }

  /* LES AVEUX DU BACKEND, RENDUS. Compacts (le panneau est étroit) mais
     LITTÉRAUX : le motif du serveur, jamais un résumé de l'écran. */
  function inspAvoues(extras) {
    const el = $("#cf-forge3d-insp-avoues");
    if (!el) return;
    const list = (extras && Array.isArray(extras.ignored)) ? extras.ignored : [];
    if (!list.length) { el.innerHTML = ""; return; }
    el.innerHTML = '<b>avoués</b> — '
      + list.map((i) => '<span class="mono">' + esc(i && i.node) + " · "
        + esc(i && i.why) + '</span>').join(" ; ");
  }

  /* LES EXTRAS D'UN GLB, LUS CÔTÉ CLIENT — le chunk JSON, rien d'autre.
     Un GLB, c'est 12 octets d'en-tête (magic « glTF », version, longueur
     totale) puis des chunks : 4 octets de longueur, 4 de type, les données.
     Le PREMIER chunk est toujours le JSON (glTF 2.0 §4.4.3) — il n'y a donc
     rien à chercher. On ne décode que lui : le binaire (maillage, textures)
     n'apprend rien que le viewer ne montre déjà.
     TOUT EST GARDÉ, et rend `null` : un octet inattendu doit coûter une ligne
     d'aveux manquante, jamais une exception qui viderait le panneau au moment
     précis où l'aperçu vient de réussir. */
  function glbExtras(buf) {
    try {
      if (typeof DataView !== "function" || typeof TextDecoder !== "function") {
        return null;
      }
      if (!buf || buf.byteLength < 20) return null;
      const dv = new DataView(buf);
      if (dv.getUint32(0, true) !== 0x46546C67) return null;   /* « glTF » */
      const len = dv.getUint32(12, true);
      if (dv.getUint32(16, true) !== 0x4E4F534A) return null;  /* « JSON » */
      if (!(len > 0) || 20 + len > buf.byteLength) return null;
      const doc = JSON.parse(new TextDecoder("utf-8")
        .decode(new Uint8Array(buf, 20, len)));
      return (doc && doc.asset && doc.asset.extras) || null;
    } catch (e) {
      return null;
    }
  }

  /* VIDER L'INSPECTEUR — et rendre ce qu'il tenait. Le jeton AVANCE (une
     requête en vol ne peindra plus), l'objectURL est RÉVOQUÉE (pas seulement
     oubliée) et le viewer est détaché en lâchant son modèle : c'est ce qui
     libère la mémoire de scène quand on part en vue liste. L'ÉLÉMENT, lui,
     est gardé en référence — le recréer serait un contexte WebGL de plus. */
  function videInspecteur() {
    if (inspTimer) { clearTimeout(inspTimer); inspTimer = 0; }
    INSP_JETON += 1;
    INSP_SUJET = "";
    if (INSP_URL && typeof URL !== "undefined") URL.revokeObjectURL(INSP_URL);
    INSP_URL = null;
    if (INSP_MV) {
      INSP_MV.removeAttribute("src");
      if (INSP_MV.parentNode) INSP_MV.parentNode.removeChild(INSP_MV);
    }
    const view = $("#cf-forge3d-insp-view");
    if (view) view.innerHTML = "";
    inspNom("");
    inspEtat("");
    inspAvoues(null);
  }

  /* LE DÉCLENCHEUR — il décide du SUJET, jamais du contenu. Deux gardes, et
     elles ne font pas le même travail : la CLÉ (`INSP_SUJET`) évite de
     reconstruire ce qui est déjà là, le DÉBOUNCE évite d'empiler les
     constructions d'un balayage. `force` sert l'édition : le sujet n'a pas
     changé, mais ce qu'il MONTRE, si. */
  function majInspecteur(force) {
    /* la vue liste n'a pas de sélection, et son panneau est masqué : rien à
       inspecter, et surtout rien à construire côté serveur. */
    if (VUE !== "canvas") return;
    const graph = get("graph");
    /* LE SUJET A PU QUITTER LE GRAPHE, et il faut le LÂCHER ici. « ↶ annuler »
       défait une naissance, `editMat` vide un maillon devenu inutile : le
       nœud désigné disparaît alors SOUS la sélection. Sans cette relâche, la
       clé de sujet (`INSP_SUJET`, l'idempotence du déclencheur) fait sortir
       cette fonction PAR LE HAUT — et le panneau garde le nom et le 3D d'un
       mort, pour toujours. `majSelArete` lâche DÉJÀ l'arête disparue par le
       même raisonnement ; c'était l'asymétrie. Le geste est complet : la
       classe de sélection tombe et la palette reprend ses boutons de maillon
       (ils n'existent que sur un traitement DÉSIGNÉ). */
    if (SEL && !((graph && graph.nodes) || []).some((x) => x.id === SEL)) {
      SEL = null;
      marqueSel();
      paintPalette();
    }
    const sujet = ARETE ? ("a:" + ARETE.from + ">" + ARETE.to)
      : (SEL ? ("n:" + SEL) : "");
    if (!force && sujet === INSP_SUJET) return;
    if (inspTimer) { clearTimeout(inspTimer); inspTimer = 0; }
    INSP_JETON += 1;              /* ce qui vole encore ne peindra plus */
    INSP_SUJET = sujet;
    if (!sujet) { videInspecteur(); return; }
    if (ARETE) {
      /* UNE ARÊTE N'EST PAS UN ÉLÉMENT : elle n'a rien à rendre en 3D. Le
         panneau le DIT — se vider se lirait comme une panne, et c'est
         justement le geste que l'utilisateur vient de faire exprès. */
      if (INSP_URL && typeof URL !== "undefined") URL.revokeObjectURL(INSP_URL);
      INSP_URL = null;
      if (INSP_MV && INSP_MV.parentNode) {
        INSP_MV.removeAttribute("src");
        INSP_MV.parentNode.removeChild(INSP_MV);
      }
      const vue = $("#cf-forge3d-insp-view");
      if (vue) vue.innerHTML = "";
      inspNom("arête " + ARETE.from + " → " + ARETE.to);
      inspEtat("une arête n'est pas un élément : elle n'a pas d'aperçu. "
        + "« supprimer », sur le trait, la coupe ; l'en-tête d'un nœud le "
        + "désigne à la place.");
      inspAvoues(null);
      return;
    }
    const n = graph ? (graph.nodes || []).filter((x) => x.id === SEL)[0] : null;
    inspNom(n ? (kindLabel(n.kind) + " · " + noeudTitre(n)) : String(SEL));
    inspEtat("aperçu en construction…");
    inspAvoues(null);
    const nid = SEL;
    inspTimer = setTimeout(() => { inspTimer = 0; inspecte(nid); }, INSP_MS);
  }

  /* L'APERÇU D'UN NŒUD, CONSTRUIT PAR LE BACKEND.
     `M.api.raw` ET PAS `M.api.blob` : cette dernière jette le corps du refus
     (« 409 Conflict ») — c'est-à-dire exactement la phrase qu'on veut lire, et
     la seule qui dise quoi faire (« lance-le d'abord », « construis l'artefact
     pour le voir dans le nœud artefact »). */
  async function inspecte(nid) {
    const gen = GEN;
    const jeton = INSP_JETON;
    const graph = get("graph");
    const view = $("#cf-forge3d-insp-view");
    if (!view) return;
    if (!graph || !nid) { inspEtat("aucun graphe à inspecter."); return; }
    let r = null;
    try {
      r = await M.api.raw("POST", "node-preview", {
        graph: graph, card: (CF.current ? CF.current() : 0), nid: nid });
    } catch (e) {
      /* transport coupé : ça, c'est une panne — elle a droit au rouge. */
      if (gen !== GEN || jeton !== INSP_JETON) return;
      echecInsp(view, String(e && e.message || e), true);
      return;
    }
    if (gen !== GEN || jeton !== INSP_JETON) return;
    if (!r.ok) {
      let d = null;
      try { d = await r.json(); } catch (err) { d = null; }
      if (gen !== GEN || jeton !== INSP_JETON) return;
      echecInsp(view, (d && (d.detail || d.error))
        || (r.status + " " + r.statusText), r.status >= 500);
      return;
    }
    let blob = null;
    try { blob = await r.blob(); } catch (e) { blob = null; }
    if (gen !== GEN || jeton !== INSP_JETON) return;
    if (!blob) {
      echecInsp(view, "aperçu illisible (corps vide)", true);
      return;
    }
    let extras = null;
    try { extras = glbExtras(await blob.arrayBuffer()); } catch (e) { extras = null; }
    if (gen !== GEN || jeton !== INSP_JETON) return;
    if (typeof customElements === "undefined"
        || !customElements.get("model-viewer")) {
      view.innerHTML = '<p class="empty-note sm">La visionneuse 3D '
        + '(/assets/model-viewer.min.js) n\'est pas chargée.</p>';
      inspEtat("aperçu construit — la visionneuse, elle, n'est pas chargée.");
      inspAvoues(extras);
      return;
    }
    if (INSP_URL && typeof URL !== "undefined") URL.revokeObjectURL(INSP_URL);
    INSP_URL = URL.createObjectURL(blob);
    if (!INSP_MV && typeof document !== "undefined") {
      INSP_MV = document.createElement("model-viewer");
      INSP_MV.id = "cf-forge3d-insp-mv";
      INSP_MV.setAttribute("camera-controls", "");
      INSP_MV.setAttribute("auto-rotate", "");
      INSP_MV.addEventListener("error", () => {
        M.toast("la visionneuse n'a pas pu ouvrir l'aperçu du nœud", true);
      });
    }
    if (!INSP_MV) return;
    if (INSP_MV.parentNode !== view) {
      view.innerHTML = "";
      view.appendChild(INSP_MV);
    }
    INSP_MV.setAttribute("src", INSP_URL);
    inspEtat("aperçu réel de ce nœud — construit à la demande, jamais payant.");
    inspAvoues(extras);
  }

  /* TOUTES LES SORTIES D'ÉCHEC PASSENT PAR ICI, et elles font DEUX choses que
     `inspEtat` seul ne faisait pas.
     · ELLES VIDENT. Sans ça, le modèle du nœud PRÉCÉDENT restait à l'écran
       sous le NOM du nouveau (le nom, lui, est déjà posé par `majInspecteur`)
       : le panneau montrait alors un objet en affirmant que c'en est un
       autre — le seul mensonge que cet écran n'a pas le droit de dire.
     · ELLES RENDENT LA CLÉ DE SUJET. `INSP_SUJET` est l'idempotence du
       DÉCLENCHEUR : « ce sujet est déjà montré, ne le reconstruis pas ». Après
       un échec il ne l'est justement pas, et le garder posé rendait la panne
       COLLANTE — aucune peinture, aucun retour de la vue liste, aucune
       ré-inspection ne repartait. Un échec doit pouvoir être re-tenté ; c'est
       même le sens de la moitié des motifs du backend (« lance-le d'abord »).
     LE SUCCÈS, LUI, GARDE SA CLÉ : c'est ce qui empêche un balayage de
     reconstruire N fois ce qui est déjà à l'écran. */
  function echecInsp(view, motif, panne) {
    videApercuInsp(view);
    INSP_SUJET = "";
    inspEtat(motif, panne);
    inspAvoues(null);
  }

  /* le viewer lâche son modèle et quitte l'hôte — l'élément survit (voir
     `INSP_MV`), le contenu non. */
  function videApercuInsp(view) {
    if (INSP_URL && typeof URL !== "undefined") URL.revokeObjectURL(INSP_URL);
    INSP_URL = null;
    if (INSP_MV) {
      INSP_MV.removeAttribute("src");
      if (INSP_MV.parentNode) INSP_MV.parentNode.removeChild(INSP_MV);
    }
    if (view) view.innerHTML = "";
  }

  /* ═══════════════════════════════════════════════════════════════════════
     LA PALETTE (2c Task 5) — CE QUI PEUT NAÎTRE, ET RIEN D'AUTRE
     Une naissance = UNE écriture (`setGraph`), donc UNE entrée d'annulation :
     poser un nœud est une DÉCISION, exactement comme poser une arête.
     CE QU'ELLE NE FAIT PAS NAÎTRE : un maillon flottant. Une matière ou un
     placement sans chaîne est un nœud MORT — le backend l'avoue au bordereau,
     la construction ne le suit pas, et un clic de menu qui en pose un
     apprendrait à l'utilisateur à ignorer ses propres aveux. Ils exigent donc
     un traitement SÉLECTIONNÉ et naissent CONNECTÉS, par l'écrivain de chaîne
     DÉJÀ en place (`editMat`/`editTrs` -> `rewireRow`, la même porte que la
     vue liste). Le GLISSER de fil, lui, garde son comportement de la Task 4 :
     accepté, et honnête à l'écran (« matière hors chaîne »). Ce n'est pas une
     contradiction — un fil visé à la main est un geste, un bouton de menu est
     un raccourci : le premier mérite qu'on lui fasse confiance, le second
     mérite qu'on ne lui laisse pas fabriquer le défaut en un clic. */
  const PAL = { role: "", format: "" };   /* le choix des menus — présentation */

  function onPaletteChange(e) {
    const s = e.target;
    const quoi = (s && s.getAttribute) ? s.getAttribute("data-pal") : null;
    if (quoi === "role") PAL.role = s.value;
    else if (quoi === "format") PAL.format = s.value;
  }

  /* LES COUCHES QU'ON PEUT ENCORE POSER : celles du manifeste LIVRÉ qui ne
     sont pas déjà une source du graphe. Le manifeste est la seule vérité de
     ce qui existe SUR LE DISQUE — proposer un rôle jamais exporté ferait
     naître un nœud dont la vignette 404 et que la construction avouerait. */
  function couchesRestantes(graph) {
    const man = LAST_MANIFEST;
    if (!man) return [];
    const cote = (man.side === "back") ? "back" : "front";
    const pris = sansProto();
    ((graph && graph.nodes) || []).forEach((n) => {
      if (n.kind !== "layer") return;
      if (((n.side === "back") ? "back" : "front") !== cote) return;
      pris[String(n.role || "composite")] = 1;
    });
    return (man.layers || [])
      .filter((l) => l && l.role)
      .map((l) => String(l.role))
      .filter((r) => !connu(pris, r));
  }

  /* LE PLAFOND EST DIT AVANT, PAS DÉCOUVERT AU REFUS. `build3d` rend un 400
     nommé au-delà de `graph_limits.max_elements` — un chiffre SERVI, jamais
     recopié ici — et le pied de la vue liste le rappelle déjà quand le graphe
     le dépasse. Une NAISSANCE, elle, peut encore être refusée à temps.
     CE QUI COMPTE EST UN ÉLÉMENT, PAS UN NŒUD : seul un traitement SOURCÉ en
     devient un. Une couche seule n'en ajoute donc aucun — mais elle n'existe
     que pour le devenir, et laisser en poser six de plus pour découvrir le
     plafond au moment de construire ne rendrait service à personne. La phrase
     est passée ENTIÈRE par l'appelant : accorder un morceau (« construit·e »)
     remettrait la faute un mot plus loin. */
  function plafondAtteint(graph, phrase) {
    const lim = (INFO && INFO.graph_limits) || null;
    const maxEl = Number(lim && lim.max_elements) || 0;
    const n = rowsDe(graph).length;
    if (!(maxEl > 0) || n < maxEl) return false;
    M.toast(n + " élément(s) — le maximum construisible est " + maxEl + " : "
      + phrase + ". Retire un rang d'abord.", true);
    return true;
  }

  /* UNE MATIÈRE SANS MATIÈRE NI FINITION N'EST RIEN : `clean_graph` la JETTE
     (forge3d.py). Un maillon né vide serait donc un nœud que le serveur
     efface — l'écran montrerait une chaîne que la construction ne suit pas.
     Il naît avec la PREMIÈRE matière servie par /info : le même patron que le
     moteur par défaut d'un mesh3d (`editGraph`, champ `kind`), et le menu du
     nœud permet d'en changer aussitôt. */
  function premiereMatiere() {
    const mats = (INFO && INFO.materials) || [];
    return (mats[0] && mats[0].id) || "";
  }

  function naitCouche() {
    const graph = get("graph");
    if (!graph) return;
    if (plafondAtteint(graph, "une couche de plus ne serait pas construite")) return;
    const restes = couchesRestantes(graph);
    const role = (PAL.role && restes.indexOf(PAL.role) >= 0) ? PAL.role : restes[0];
    if (!role) {
      M.toast("toutes les couches livrées sont déjà des sources de ce graphe",
              true);
      return;
    }
    const next = JSON.parse(JSON.stringify(graph));
    const cote = (LAST_MANIFEST && LAST_MANIFEST.side === "back") ? "back" : "front";
    /* `|| []` — LE MÊME GARDE QUE TOUS LES LECTEURS (`grapheAvecLien`,
       `aretes`, `rowsDe`…). Un graphe chargé à la main peut n'avoir aucune
       clé `nodes` ; toute la lecture le tolère, seule l'écriture levait. */
    next.nodes = (next.nodes || []).concat([
      { id: freeId(next.nodes || [], role), kind: "layer",
        role: role, side: cote }]);
    setGraph(next, "+ couche");
    paintVue();
  }

  function naitProc() {
    const graph = get("graph");
    if (!graph) return;
    if (plafondAtteint(graph, "un traitement de plus ne serait pas construit")) return;
    const next = JSON.parse(JSON.stringify(graph));
    /* IL NAÎT EN PLAN, et sans source. Le plan est le seul traitement à la
       fois gratuit et sans réglage obligatoire (le relief a une base et une
       grille, le moteur a un prix) ; le menu du nœud en change aussitôt.
       Et l'absence de source est un travail EN COURS, pas un nœud mort : son
       corps le dit déjà (« traitement sans couche source — il ne sera pas
       construit »), et le geste suivant est justement de tirer le fil. C'est
       LA différence avec un maillon, et c'est pour ça que l'un naît libre et
       l'autre connecté. */
    next.nodes = (next.nodes || []).concat([
      { id: freeId(next.nodes || [], "t"), kind: "plane", depth_mm: 0 }]);
    setGraph(next, "+ traitement");
    paintVue();
  }

  function naitMaillon(kind) {
    const graph = get("graph");
    if (!graph) return;
    const mat = (kind === "material");
    const proc = (graph.nodes || []).filter(
      (n) => n.id === SEL && PROC_KINDS.indexOf(n.kind) >= 0)[0];
    if (!proc) {
      M.toast("désigne d'abord le traitement à "
        + (mat ? "habiller" : "placer")
        + " (clic sur l'en-tête d'un plan, d'un relief ou d'un moteur) : "
        + (mat ? "une matière appartient" : "un placement appartient")
        + " à une chaîne — seul, le maillon ne serait pas construit.", true);
      return;
    }
    /* ... ET LA CHAÎNE DOIT AVOIR SA SOURCE. Un traitement sans couche n'est
       pas encore une chaîne : le maillon naîtrait bien CÂBLÉ (`editMat` le
       relie), mais aucun rang ne le porterait — `graphRows` ne rend que les
       traitements SOURCÉS — et son corps annoncerait « matière hors chaîne —
       aucun traitement ne la porte », ce qui est FAUX : le traitement la
       porte, c'est la couche qui manque. Un écran qui désigne le mauvais
       coupable coûte plus cher qu'un écran qui refuse : on refuse, en nommant
       le geste qui débloque. Le glisser de fil, lui, garde son comportement
       (un fil visé à la main est un geste — la distinction du bloc ci-dessus). */
    const chaine = rowModel(graph, proc.id);
    if (!chaine || !chaine.layer) {
      M.toast("« " + noeudTitre(proc) + " » n'a pas encore de couche source : "
        + "relie d'abord une couche à ce traitement — sans elle, "
        + (mat ? "la matière" : "le placement")
        + " naîtrait dans une chaîne que la construction ne suit pas.", true);
      return;
    }
    /* LES MOTS DU BORDEREAU, RÉUTILISÉS TELS QUELS. `surnumeraire` les écrit
       déjà pour le glisser de fil ; une seconde phrase ici aurait dérivé de
       la première au premier changement de règle. L'id passé est celui que
       `editMat`/`editTrs` fabriqueraient — donc LIBRE, ce qui fait porter le
       refus sur la seule question qui reste : cette chaîne en a-t-elle déjà
       un ? */
    const surn = surnumeraire(graph, proc, {
      id: freeId(graph.nodes, proc.id + (mat ? "m" : "t")), kind: kind });
    if (surn) { M.toast(surn, true); return; }
    const next = JSON.parse(JSON.stringify(graph));
    if (mat) {
      const mid = premiereMatiere();
      if (!mid) {
        /* la panne (ou la boutique vide) est dite avec LES MOTS DÉJÀ ÉCRITS
           dans le bloc matière — jamais un « impossible » muet. */
        M.toast(String((INFO && INFO.materials_degraded)
          || (INFO ? "la boutique de matières est vide (aucune matière "
                   + "installée)." : "contrat /info non chargé.")), true);
        return;
      }
      editMat(next, proc.id, "mat", mid);
    } else {
      /* `editTrs` sème l'élément NEUTRE — et le z d'EMPILEMENT du plan (I1,
         2b), pas un zéro qui aplatirait la parallaxe. On lui redonne l'échelle
         qu'il vient de poser : rien ne change, et ce qui compte (la naissance
         ET le câblage de la chaîne) est fait par la MÊME porte que la liste. */
      editTrs(next, proc.id, "scale", 1);
    }
    setGraph(next, mat ? "+ matière" : "+ placement");
    paintVue();
  }

  function naitExport() {
    const graph = get("graph");
    if (!graph) return;
    const art = (graph.nodes || []).filter((n) => n.kind === "artifact")[0];
    if (!art) {
      M.toast("aucun nœud artefact dans ce graphe : un export est un point de "
        + "téléchargement SUR un artefact — reconstruis le graphe par défaut, "
        + "il en pose un.", true);
      return;
    }
    const fmts = exportFormats();
    const fmt = (PAL.format && fmts.indexOf(PAL.format) >= 0) ? PAL.format : fmts[0];
    if (!fmt) {
      M.toast("formats d'export inconnus — le contrat /info n'a pas été chargé "
        + "(backend injoignable ?).", true);
      return;
    }
    /* UN SECOND POINT DE TÉLÉCHARGEMENT DU MÊME FICHIER N'AJOUTE RIEN. Les
       nœuds d'export ne portent pas d'état propre : ils LISENT le dernier
       bordereau (`exportEtatHtml`), donc deux nœuds « glb » affichent le même
       poids et le même bouton, et encombrent la surface d'un doublon que rien
       ne distingue. Le refus est nommé — et il nomme le nœud déjà là, pour
       qu'on sache où regarder. */
    const deja = (graph.nodes || []).filter(
      (n) => n.kind === "export" && String(n.format || "") === fmt)[0];
    if (deja) {
      M.toast("un nœud d'export « " + fmt + " » existe déjà (" + deja.id
        + ") — il porte le MÊME fichier du MÊME bordereau : un second "
        + "n'ajouterait rien. Choisis un autre format.", true);
      return;
    }
    const next = JSON.parse(JSON.stringify(graph));
    const id = freeId(next.nodes || [], "ex" + fmt);
    next.nodes = (next.nodes || []).concat([
      { id: id, kind: "export", format: fmt }]);
    /* NÉ CONNECTÉ, et sans choix possible : la grammaire n'autorise que
       `artifact -> export`, et un export non relié n'aurait rien à
       télécharger. */
    next.edges = (next.edges || []).concat([{ from: art.id, to: id }]);
    setGraph(next, "+ export");
    paintVue();
  }

  function paletteHtml() {
    const graph = get("graph");
    if (!graph) {
      return '<span class="hint">la palette pose des nœuds SUR un graphe — '
        + 'construis-en un d\'abord (bouton au centre de la surface).</span>';
    }
    const restes = couchesRestantes(graph);
    const fmts = exportFormats();
    const proc = (graph.nodes || []).filter(
      (n) => n.id === SEL && PROC_KINDS.indexOf(n.kind) >= 0)[0];
    const art = (graph.nodes || []).filter((n) => n.kind === "artifact")[0];
    const lim = (INFO && INFO.graph_limits) || null;
    const maxEl = Number(lim && lim.max_elements) || 0;
    const n = rowsDe(graph).length;
    const plein = (maxEl > 0 && n >= maxEl);
    const sansProc = "désigne un traitement (plan, relief ou moteur) : "
      + "un maillon appartient à une chaîne";
    return '<span class="lbl">poser</span>'
      + (restes.length
        ? ('<select data-pal="role" title="les couches livrées qui ne sont pas '
          + 'encore des sources">'
          + restes.map((r) => '<option value="' + esc(r) + '"'
            + (PAL.role === r ? " selected" : "") + '>' + esc(r)
            + '</option>').join("")
          + '</select>')
        : "")
      + '<button class="btn sm" type="button" data-act="pal-couche"'
      + ((!restes.length || plein) ? " disabled" : "") + ' title="'
      + esc(restes.length
        ? "une couche livrée, pas encore reliée à un traitement"
        : "toutes les couches livrées sont déjà des sources de ce graphe")
      + '">+ couche</button>'
      + '<button class="btn sm" type="button" data-act="pal-proc"'
      + (plein ? " disabled" : "")
      + ' title="un plan, à relier à une couche">+ traitement</button>'
      + '<button class="btn sm" type="button" data-act="pal-mat"'
      + (proc ? "" : " disabled") + ' title="'
      + esc(proc ? ("habille « " + noeudTitre(proc) + " »") : sansProc)
      + '">+ matière</button>'
      + '<button class="btn sm" type="button" data-act="pal-trs"'
      + (proc ? "" : " disabled") + ' title="'
      + esc(proc ? ("place « " + noeudTitre(proc) + " »") : sansProc)
      + '">+ placement</button>'
      + (fmts.length
        ? ('<select data-pal="format" title="les formats que le bordereau '
          + 'livre">'
          + fmts.map((f) => '<option value="' + esc(f) + '"'
            + (PAL.format === f ? " selected" : "") + '>' + esc(f)
            + '</option>').join("")
          + '</select>')
        : "")
      + '<button class="btn sm" type="button" data-act="pal-export"'
      + ((!fmts.length || !art) ? " disabled" : "") + ' title="'
      + esc(art ? "un point de téléchargement sur l'artefact"
                : "aucun nœud artefact dans ce graphe")
      + '">+ export</button>'
      /* LE PLAFOND, TOUJOURS LISIBLE — pas seulement au moment du refus. */
      + '<span class="mono cf-forge3d-pal-compte'
      + (plein ? " cf-forge3d-trop" : "") + '">' + Number(n)
      + (maxEl > 0 ? (" / " + Number(maxEl)) : "") + ' élément(s)</span>';
  }

  function paintPalette() {
    const el = $("#cf-forge3d-palette");
    if (!el || VUE !== "canvas") return;
    el.innerHTML = paletteHtml();
  }

  /* L'HÔTE DE LA VUE ACTIVE — la liste et le canvas peignent les MÊMES
     zones (`.cf-forge3d-run` et sa chip, notamment) et une recherche clouée
     à `#cf-forge3d-graph` laissait le poll d'un job repeindre… dans un hôte
     vidé, c'est-à-dire nulle part : sur le canvas, un job passait de « en
     cours » à rien du tout jusqu'au prochain repaint global. La vue inactive
     étant VIDÉE par le dispatcher, chercher dans l'active suffit. */
  function hoteVue() {
    return (VUE === "canvas") ? $("#cf-forge3d-canvas") : $("#cf-forge3d-graph");
  }

  /* le rang (ou le nœud) dans le DOM, retrouvé par comparaison d'attribut et
     non par sélecteur construit : un id de nœud est une donnée, jamais un
     fragment de sélecteur (un point y suffirait à tout casser).
     M11 — `racine` RESTREINT la recherche à un sous-arbre. CE QUE CE
     CHANGEMENT A CORRIGÉ, EXACTEMENT (mesuré, pas supposé) : la restauration
     du focus se faisait par SÉLECTEUR CONSTRUIT (`'[data-field="' + champ +
     '"]'`), la doctrine énoncée deux lignes plus haut enfreinte à deux pas de
     l'endroit qui l'énonce — un jour où un nom de champ portera un guillemet
     ou un crochet, ce sélecteur-là lèvera. Ce qu'il n'a PAS corrigé : un
     champ volé au voisin. Les deux appels d'origine étaient DÉJÀ portés
     (`neuf.querySelector` dans `paintRow`, `el.querySelector` dans
     `paintNode`) — aucun voisin n'était atteignable, et écrire le contraire
     ferait croire à un bug là où il n'y en avait pas. La valeur du
     changement est double et tient en deux mots : la DOCTRINE (comparer un
     attribut, ne jamais bâtir un sélecteur avec une donnée) et la
     DÉ-DUPLICATION (une seule restauration de focus, `rendLeFocus`, au lieu
     de deux copies vouées à diverger). `racine` est ce qui rend la
     dé-duplication possible sans PERDRE la portée que les deux copies
     avaient. */
  function findByAttr(cls, attr, val, racine) {
    const host = racine || hoteVue();
    if (!host) return null;
    const tab = Array.prototype.slice.call(host.querySelectorAll(cls));
    for (let i = 0; i < tab.length; i++) {
      if (tab[i].getAttribute(attr) === val) return tab[i];
    }
    return null;
  }

  /* REPEINDRE UN SEUL RANG (et rien d'autre) : le moteur et l'ultra changent
     ce que le rang AFFICHE au-delà de la valeur saisie (prix, case ultra,
     bouton). Repeindre la liste entière y référerait les tiroirs ouverts des
     AUTRES rangs et volerait le focus — le piège syncInputs/renderPanel de
     mod-face. On préserve donc les deux choses que le DOM porte et que le
     graphe ne dit pas : les blocs dépliés et l'élément focalisé. */
  function paintRow(procId, focusField) {
    const graph = get("graph");
    const old = findByAttr(".cf-forge3d-row", "data-proc", procId);
    const r = graph ? rowModel(graph, procId) : null;
    if (!old || !r || !r.layer || !old.parentNode) { paintVue(); return; }
    const ouverts = Array.prototype.slice.call(old.querySelectorAll("details"))
      .map((d) => !!d.open);
    const tmp = document.createElement("div");
    tmp.innerHTML = rowHtml(r, (INFO && INFO.graph_limits) || null);
    const neuf = tmp.firstChild;
    old.parentNode.replaceChild(neuf, old);
    Array.prototype.slice.call(neuf.querySelectorAll("details"))
      .forEach((d, i) => { if (ouverts[i]) d.open = true; });
    rendLeFocus(neuf, focusField);
    paintCost();
  }

  /* rendre le focus au champ qu'on vient de reconstruire — par comparaison
     d'attribut dans CE sous-arbre (M11), jamais par sélecteur construit. */
  function rendLeFocus(racine, focusField) {
    if (!racine || !focusField) return;
    const f = findByAttr("[data-field]", "data-field", focusField, racine);
    if (f && f.focus) f.focus();
  }

  /* REPEINDRE UN SEUL NŒUD — le pendant exact de `paintRow` pour le canvas,
     et une PIÈCE OBLIGATOIRE de la Task 3, pas un raffinement. `paintCanvas`
     reconstruit tout le monde en un `innerHTML` : maintenant que les nœuds
     portent des champs, la moindre édition qui passerait par lui détruirait
     et recréerait l'input focalisé — chaque pas de spinner, chaque choix de
     matière perdrait le curseur (le piège syncInputs/renderPanel de
     mod-face, déjà payé une fois sur la liste, I1 de la 2b).
     On préserve donc les deux choses que le DOM porte et que le graphe ne dit
     pas : les tiroirs ouverts et l'élément focalisé. Et on repeint l'INTÉRIEUR
     seulement : l'élément extérieur garde sa position (style left/top écrit
     par le glisser) et sa classe de sélection. */
  function paintNode(nid, focusField) {
    const el = findByAttr(".cf-forge3d-noeud", "data-nid", nid);
    const graph = get("graph");
    const n = (el && graph)
      ? (graph.nodes || []).filter((x) => x.id === nid)[0] : null;
    /* le nœud a disparu sous l'édition (un maillon vidé par `editMat`) :
       c'est structurel, le dispatcher tranche. */
    if (!el || !n) { paintVue(); return; }
    /* M9 — AUCUNE SAUVEGARDE DE TIROIRS ICI, et ce n'est pas un oubli : un
       corps de nœud n'en a AUCUN. `blocHtml` réserve `<details>` à l'hôte
       « row » ; sur le canvas, matière et placement sont des nœuds à part et
       leurs champs sont nus (un nœud entier réduit à un tiroir fermé ne
       montrerait rien — ce que la spec §5.6 demande justement d'arrêter).
       La sauvegarde recopiée de `paintRow` tournait donc toujours sur zéro
       élément : du code qui a l'air de protéger quelque chose et ne protège
       rien, c'est-à-dire pire que rien. Si un corps de nœud gagne un jour un
       tiroir, c'est la discipline de `paintRow` qu'il faudra reprendre. */
    el.innerHTML = noeudTeteHtml(n) + portsHtml(n) + nodeBodyHtml(nid);
    rendLeFocus(el, focusField);
    paintNodeThumb(nid);
    /* le viewer du RÉSULTAT vit dans le corps qu'on vient de réécrire (nœud
       artefact) : on le RE-ACCROCHE, sans re-télécharger. */
    remonteApercu();
    paintCost();
  }

  /* LE MÊME GESTE, DANS LA VUE QUI EST À L'ÉCRAN. Un rang de liste et un
     nœud de canvas sont deux hôtes du même jeu de champs : l'édition qui
     change ce qu'ils AFFICHENT (prix, case ultra, puce de tiroir) doit
     repeindre l'un OU l'autre — jamais les deux, jamais la vue entière. */
  function paintChamps(procId, nid, field) {
    if (VUE === "canvas") paintNode(nid, field);
    else paintRow(procId, field);
  }

  /* la zone bouton+chip d'un nœud moteur, repeinte SEULE par le poll : c'est
     ce qui permet à un job de couler pendant que l'utilisateur écrit dans le
     champ texture du même rang sans jamais perdre son curseur.
     LA ZONE EST LA MÊME DANS LES DEUX VUES (2c Task 3) : `findByAttr` cherche
     dans l'hôte ACTIF, donc le poll peint la chip du rang de liste ou celle
     du corps de nœud, selon ce qui est à l'écran — clouée à la liste, elle
     laissait un job du canvas passer de « en cours » à rien du tout.
     Et la VIGNETTE suit : elle porte le même état lu du job (« servi »,
     « en cours 40 % »), donc la laisser derrière ferait dire deux choses
     différentes à deux centimètres d'écart. */
  function paintChip(nid) {
    const zone = findByAttr(".cf-forge3d-run", "data-nid", nid);
    if (!zone) return;
    const graph = get("graph");
    const proc = graph ? (graph.nodes || []).filter((n) => n.id === nid)[0] : null;
    if (!proc) return;
    zone.innerHTML = runHtml(proc);
    paintNodeThumb(nid);
  }

  function onGraphClick(e) {
    /* UNE ARÊTE EST UNE CIBLE : son chemin de saisie la DÉSIGNE, et le bouton
       flottant qui apparaît alors est le seul à pouvoir la couper. Deux
       gestes plutôt qu'un, exprès : une arête coupée d'un clic serait un
       accident permanent (le glisser du fond passe juste à côté). */
    const arc = e.target.closest
      ? e.target.closest(".cf-forge3d-edge-hit") : null;
    if (arc) {
      e.preventDefault();
      selectionneArete(arc.getAttribute("data-from"),
                       arc.getAttribute("data-to"));
      return;
    }
    const b = e.target.closest ? e.target.closest("[data-act]") : null;
    if (!b) return;
    const act = b.getAttribute("data-act");
    if (act === "seed-default") {
      e.preventDefault();
      seedDefault();
    } else if (act === "launch") {
      e.preventDefault();
      launchMesh3d(b.getAttribute("data-nid"));
    } else if (act === "vue-recentre") {
      e.preventDefault();
      recentreCam();
    } else if (act === "lien-supp") {
      e.preventDefault();
      if (ARETE) suppLien(ARETE.from, ARETE.to);
    } else if (act === "grab-file") {
      /* le MÊME acte que dans les bordereaux de section (`onSlipClick`) : un
         fichier livré se télécharge par sa PROVENANCE, d'où qu'on clique. */
      e.preventDefault();
      grabZip(b.getAttribute("data-name"));
    } else if (act === "build3d") {
      e.preventDefault();
      build3d();
    } else if (act === "freeze") {
      e.preventDefault();
      freezePreview();
    } else if (act === "pal-couche") {
      e.preventDefault();
      naitCouche();
    } else if (act === "pal-proc") {
      e.preventDefault();
      naitProc();
    } else if (act === "pal-mat") {
      e.preventDefault();
      naitMaillon("material");
    } else if (act === "pal-trs") {
      e.preventDefault();
      naitMaillon("transform");
    } else if (act === "pal-export") {
      e.preventDefault();
      naitExport();
    }
  }

  /* LE SEED CONSOMME LE MANIFESTE : il doit donc ATTENDRE la vérification de
     fraîcheur avant de le lire, pas seulement se fier au dernier repaint. Sans
     cette attente, la séquence « je change de carte, je clique aussitôt sur
     construire le graphe par défaut » sème depuis les couches de la carte
     PRÉCÉDENTE — exactement le défaut que le legs 5 existe pour tuer, et que
     l'abonnement à `core:render` seul ne couvre pas (le clic peut arriver
     avant que le rechargement déclenché ne soit revenu).
     La boucle est BORNÉE et son cas d'usage est précis : si un chargement pour
     l'ANCIENNE carte était déjà en vol, `cardChanged` rend cette promesse-là —
     l'attendre ne suffit pas, il faut un second tour pour la carte courante. */
  async function seedDefault() {
    for (let k = 0; k < 3 && cardLabel() !== MANIFEST_CARD; k++) await cardChanged();
    if (cardLabel() !== MANIFEST_CARD) {
      M.toast("manifeste de cette carte non chargé — réessayez", true);
      return;
    }
    if (!LAST_MANIFEST) {
      /* la carte courante n'a pas de couches livrées : le bouton lui-même
         n'aurait pas dû être là — on repeint pour dire la vérité. */
      M.toast("aucune couche exportée pour cette carte", true);
      paintVue();
      return;
    }
    setGraph(defaultGraph(LAST_MANIFEST), "graphe par défaut");
    paintVue();       /* structurel : la vue entière change de forme */
  }

  /* UNE SEULE DÉLÉGATION POUR LES DEUX VUES. Le repère n'est plus la classe
     du rang (`.cf-forge3d-row`, qui n'existe que dans la liste) mais
     l'ATTRIBUT que les deux hôtes portent : `data-proc`, l'id du traitement
     au nom duquel l'édition s'écrit. Un corps de nœud matière ou placement y
     met l'id de SON traitement — c'est ce que `editMat`/`editTrs` attendent,
     et c'est pour ça que les handlers n'ont pas eu à changer d'un octet.
     `data-nid` dit, en plus, QUEL nœud repeindre : dans la liste il vaut
     `data-proc` (un rang EST son traitement), sur le canvas il désigne la
     carte que l'utilisateur a sous les yeux. */
  function onGraphChange(e) {
    const hote = e.target.closest ? e.target.closest("[data-proc]") : null;
    if (!hote) return;
    const field = e.target.getAttribute("data-field");
    if (!field) return;
    const val = (e.target.type === "checkbox") ? e.target.checked : e.target.value;
    const procId = hote.getAttribute("data-proc");
    editGraph(procId, field, val, hote.getAttribute("data-nid") || procId);
  }

  /* ── M10 : LA VIGNETTE SUIT LA FRAPPE, LE DOCUMENT SUIT LE COMMIT ───────
     `change` reste le SEUL évènement qui écrit : un patch par caractère
     empilerait des entrées d'annulation illisibles et ferait cascader
     `invalidate` -> `drawPreview` à chaque touche (la raison même pour
     laquelle le glisser ne patche qu'au relâché).
     Mais la promesse de la 2c est que la vignette « réagit immédiatement », et
     au clavier elle ne réagissait pas : `input` ne partait nulle part, et un
     `input` qui aurait simplement rappelé le peintre aurait redessiné la
     valeur du GRAPHE, c'est-à-dire l'ancienne — un repaint qui ne repeint
     rien. On donne donc au peintre la valeur EN COURS DE SAISIE, et rien
     d'autre : pas de patch, pas de reconstruction de champ (le curseur ne
     bouge pas), pas d'entrée d'annulation.
     `SAISIE` vit le temps d'un repaint SYNCHRONE et est remise à null dans un
     `finally` : aucune peinture ultérieure ne peut la lire, donc la vignette
     reste une fonction du graphe partout ailleurs. */
  let SAISIE = null;            /* {nid, field, val} — jamais commis */

  function onGraphInput(e) {
    const hote = e.target.closest ? e.target.closest("[data-proc]") : null;
    if (!hote) return;
    const field = e.target.getAttribute("data-field");
    /* une case à cocher n'a pas d'état intermédiaire : son `input` est son
       `change`, et le laisser passer ici peindrait deux fois. */
    if (!field || e.target.type === "checkbox") return;
    const procId = hote.getAttribute("data-proc");
    const nid = hote.getAttribute("data-nid") || procId;
    SAISIE = { nid: nid, field: field, val: e.target.value };
    try {
      repeintChaine(procId, nid);
    } finally {
      SAISIE = null;
    }
  }

  /* la valeur qu'un champ MONTRE à cet instant : celle du graphe, sauf si
     l'utilisateur est justement en train de la taper. Lecture de DESSIN
     uniquement — rien de ce qui s'écrit (graphe, prix, lancement) ne passe
     par ici, et hors d'un `input` en cours elle rend le graphe tel quel. */
  function valeurVue(nid, field, dansLeGraphe) {
    return (SAISIE && SAISIE.nid === nid && SAISIE.field === field)
      ? SAISIE.val : dansLeGraphe;
  }

  /* ÉCRITURE + PILE D'ANNULATION (patron mod-gltf.js:set/undo, paintUndo
     ~ligne 1623) : chaque édition du graphe — champ par champ, ou un
     re-seed entier — pousse l'ANCIEN graphe sur `HIST` avant de patcher,
     jamais après : c'est cette valeur-là que `undoGraph` restaure.
     `setGraph` NE REPEINT JAMAIS la liste par elle-même (patron exact de
     mod-gltf.js:set — c'est TOUJOURS l'appelant qui décide) : c'est ce
     découplage qui rend le correctif I1 possible juste en dessous. */
  function setGraph(next, label) {
    HIST.push({ before: get("graph"), label: label || "graphe" });
    if (HIST.length > 40) HIST.shift();
    M.patch({ graph: next });
    paintUndo();
  }

  /* le bouton reflète la pile (patron mod-gltf.js:paintUndo) : désactivé si
     rien à annuler, sinon étiqueté par le label de la PROCHAINE annulation. */
  function paintUndo() {
    const b = $("#cf-forge3d-undo");
    if (!b) return;
    b.disabled = !HIST.length;
    b.textContent = HIST.length ? "↶ annuler " + HIST[HIST.length - 1].label : "↶ annuler";
  }

  function undoGraph() {
    const h = HIST.pop();
    if (!h) { M.toast("rien à annuler"); return; }
    M.patch({ graph: h.before });
    paintUndo();
    paintVue();
    M.toast("annulé : " + h.label);
  }

  /* ═══════════════════════════════════════════════════════════════════════
     LES CONNEXIONS — LA MOITIÉ PURE, PUIS LA MOITIÉ QUI ÉCRIT
     `grapheAvecLien` / `grapheSansLien` ne touchent à RIEN : elles reçoivent
     un graphe, elles en rendent un autre (ou un motif de refus). C'est ce
     qui les rend JUGEABLES — le harnais de chaînes les fait tourner telles
     quelles, extraites du fichier livré, et mesure que le graphe câblé à la
     souris se lit exactement comme celui qu'écrit la vue liste. `creeLien` /
     `suppLien` sont l'autre moitié : lire l'état, patcher, dire.

     LE REFUS EST PRONONCÉ AVANT L'ÉCRITURE, jamais après. Le backend, lui,
     ACCEPTE ces graphes et les avoue au bordereau (`ignored` : « maillon
     surnuméraire … première arête gagnante ») — c'est le bon comportement
     pour une API ouverte, ce serait le mauvais pour un écran : laisser poser
     un maillon mort puis le dénoncer à chaque construction apprend à
     l'utilisateur à ignorer son propre bordereau. */
  function grapheAvecLien(graph, deNid, versNid) {
    const nodes = (graph && graph.nodes) || [];
    const de = nodes.filter((n) => n.id === deNid)[0];
    const vers = nodes.filter((n) => n.id === versNid)[0];
    /* un nœud qui n'existe pas, ou un nœud sur lui-même : ce n'est pas un
       refus à expliquer, c'est un geste qui n'a pas eu lieu. */
    if (!de || !vers || deNid === versNid) return null;
    const edges = graph.edges || [];
    for (let i = 0; i < edges.length; i++) {
      /* DÉJÀ LÀ : rien à écrire, rien à annuler, et rien à DIRE — l'arête
         que l'utilisateur voulait est sous ses yeux. Un toast y serait un
         reproche pour un geste réussi. */
      if (edges[i].from === deNid && edges[i].to === versNid) {
        return { deja: true };
      }
    }
    if (!lienValide(de.kind, vers.kind)) {
      /* LES DEUX KINDS SONT CITÉS, PAS ARTICULÉS. Le plan écrivait « un
         {from} ne se branche pas sur un {to} » ; en français ça donne « un
         couche » et « un matière » une fois sur deux, et il aurait fallu une
         SECONDE table (le genre de chaque kind) à tenir d'accord avec
         `KIND_LABELS` — pour un article. Les guillemets disent la même chose
         sans rien à synchroniser. */
      return { refus: "« " + kindLabel(de.kind) + " » ne se branche pas sur « "
        + kindLabel(vers.kind) + " » — chaîne attendue : " + chaineAttendue() };
    }
    const surn = surnumeraire(graph, de, vers);
    if (surn) return { refus: surn };
    const next = JSON.parse(JSON.stringify(graph));
    next.edges = (next.edges || []).concat([{ from: deNid, to: versNid }]);
    return { graph: next };
  }

  /* LA CHAÎNE À LAQUELLE UN NŒUD APPARTIENT, vue depuis n'importe lequel de
     ses maillons : un traitement EST sa chaîne (`rowModel` répond même quand
     aucune couche ne le source encore) ; une matière ou un placement, eux,
     se remontent jusqu'à leur traitement.

     I2 — LA REMONTÉE SE FAIT À LA MAIN, PAS PAR `rowDuNoeud`. Celui-ci passe
     par `rowsDe`/`graphRows`, qui ne rendent QUE les rangs ayant une couche
     source : une chaîne dont on vient de couper `layer -> traitement` (un
     geste de PREMIÈRE CLASSE depuis la Task 4, il suffit d'un clic sur
     l'arête et du bouton) n'y figure plus du tout. Le contrôle de surnombre
     recevait alors `null` et laissait TOUT passer — c'est-à-dire exactement
     le créer-puis-avouer que ce fichier refuse : le backend, lui, aurait
     dénoncé le maillon surnuméraire à la construction suivante. `rowModel`,
     lui, répond sans couche ; il suffit donc de retrouver le traitement de
     tête. Marche bornée par `CHAIN_MAX`, comme la descente. */
  function chaineDe(graph, n) {
    if (PROC_KINDS.indexOf(n.kind) >= 0) return rowModel(graph, n.id);
    const byId = sansProto();
    ((graph && graph.nodes) || []).forEach((x) => { byId[x.id] = x; });
    const edges = (graph && graph.edges) || [];
    let cur = n;
    for (let k = 0; k < CHAIN_MAX && cur; k++) {
      let amont = null;
      for (let i = 0; i < edges.length && !amont; i++) {
        if (edges[i].to !== cur.id) continue;
        const src = connu(byId, edges[i].from) ? byId[edges[i].from] : null;
        /* PREMIÈRE ARÊTE GAGNANTE, comme partout ailleurs (le backend en
           tête) : on ne remonte que par un maillon ou un traitement. */
        if (src && (PROC_KINDS.indexOf(src.kind) >= 0
                    || src.kind === "material" || src.kind === "transform")) {
          amont = src;
        }
      }
      if (!amont) return null;
      if (PROC_KINDS.indexOf(amont.kind) >= 0) return rowModel(graph, amont.id);
      cur = amont;
    }
    return null;
  }

  /* LA RÈGLE DE CHAÎNE UNIQUE — les MOTS du bordereau, dits AVANT l'écriture.
     Trois surnombres possibles, et ce sont exactement ceux que
     `_resolve_graph_elements` / `_chaine_aval` avouent : une seconde source
     sur un traitement, une seconde matière ou un second placement dans une
     chaîne. Rend le motif, ou `null` quand rien ne fait nombre. */
  function surnumeraire(graph, de, vers) {
    if (PROC_KINDS.indexOf(vers.kind) >= 0) {
      const r = rowModel(graph, vers.id);
      if (r && r.layer) {
        return "ce traitement a déjà une source (" + r.layer.id + ") — une "
          + "seconde serait surnuméraire : la première arête gagne, l'autre "
          + "est une perte que le bordereau avouerait.";
      }
      return null;
    }
    if (vers.kind === "material" || vers.kind === "transform") {
      const mat = (vers.kind === "material");
      /* C1 — LA CIBLE AUSSI PEUT ÊTRE PRISE, et c'est le surnombre qu'on ne
         voyait pas : la question posée ci-dessous est « LA CHAÎNE DE LA
         SOURCE en porte-t-elle déjà un ? », jamais « ce maillon-ci
         appartient-il déjà à quelqu'un ? ». Un maillon PARTAGÉ passait donc
         (tirer la sortie de m1 sur un placement qui sert déjà une autre
         chaîne), et le dégât arrivait plus tard, ailleurs, sans un mot :
         `rewireRow` réécrit la chaîne éditée EN PREMIER et purge l'arête que
         l'autre rangée empruntait — la seconde chaîne cesse d'être
         construite (« traitement non relié à un assemble » au bordereau)
         tout en s'affichant encore comme une rangée. Un maillon n'a donc
         qu'UNE arête entrante ; pour le déplacer, on coupe d'abord.
         C'est aussi ce qui rend de nouveau VRAIE la phrase « cet écran ne
         produit jamais cette topologie » (rowDuNoeud, maillonsAval). */
      if ((graph.edges || []).some((e) => e.to === vers.id)) {
        return (mat ? "cette matière appartient" : "ce placement appartient")
          + " déjà à une autre chaîne — un maillon partagé se fait réécrire "
          + "par la première rangée éditée, et l'autre chaîne perd son lien "
          + "en silence.";
      }
      const r = chaineDe(graph, de);
      const deja = r ? (mat ? r.mat : r.trs) : null;
      if (deja) {
        /* TOUTE la phrase s'accorde sur le même genre (une matière / une
           seconde / la première — un placement / un second / le premier) :
           n'en accorder qu'un morceau remet la faute un mot plus loin. */
        return "cette chaîne porte déjà " + (mat ? "une matière" : "un placement")
          + " (" + deja.id + ") — " + (mat ? "une seconde" : "un second")
          + " serait surnuméraire : le serveur garderait "
          + (mat ? "la première" : "le premier")
          + " et avouerait l'autre au bordereau.";
      }
    }
    return null;
  }

  /* COUPER UNE ARÊTE, ET RIEN D'AUTRE. Aucune purge « pendant qu'on y est » :
     retirer un lien ne peut pas rendre une arête pendante (les nœuds
     restent), et nettoyer autre chose au passage ferait décider à l'écran ce
     que `clean_graph` est seul à trancher. Rend `null` quand il n'y avait
     rien à couper — donc AUCUNE entrée d'annulation pour un geste sans
     effet. */
  function grapheSansLien(graph, deNid, versNid) {
    const edges = (graph && graph.edges) || [];
    const reste = edges.filter(
      (e) => !(e.from === deNid && e.to === versNid));
    if (reste.length === edges.length) return null;
    const next = JSON.parse(JSON.stringify(graph));
    next.edges = reste.map((e) => ({ from: e.from, to: e.to }));
    return { graph: next };
  }

  function creeLien(deNid, versNid) {
    const r = grapheAvecLien(get("graph"), deNid, versNid);
    if (!r || !r.graph) {
      if (r && r.refus) M.toast(r.refus, true);
      return false;
    }
    setGraph(r.graph, "connexion");
    selectionneArete(null);
    /* STRUCTUREL : une arête de plus change les chaînes — donc les rangs de
       la vue liste, les vignettes qui lisent la couche source, le devis. */
    paintVue();
    return true;
  }

  function suppLien(deNid, versNid) {
    const r = grapheSansLien(get("graph"), deNid, versNid);
    if (!r) return false;
    setGraph(r.graph, "déconnexion");
    selectionneArete(null);
    paintVue();
    return true;
  }

  const MAT_FIELDS = ["mat", "finish", "tile_mm", "aniso"];
  const TRS_FIELDS = ["x_mm", "y_mm", "z_mm", "rot_deg", "scale"];
  /* les champs qui changent l'AFFICHAGE du rang (ou du nœud) au-delà de leur
     propre valeur.
     I1 — `side` EN FAIT PARTIE, et l'oubli se voyait à l'œil : l'en-tête d'un
     nœud couche affiche « cadre · recto » (`noeudTitre` lit `side`), donc
     basculer le select sur « verso » laissait le titre dire recto juste
     au-dessus d'un champ disant verso. Sur la liste, le rang ne montre que le
     rôle — le défaut y était invisible, et c'est exactement pourquoi il a
     survécu jusqu'au canvas. */
  /* Task 5 : `name` et `format` en font partie pour la même raison que `side`
     — ils changent ce que le nœud MONTRE au-delà de leur propre valeur. Le nom
     d'un artefact est son TITRE d'en-tête (`noeudTitre`), et le format d'un
     export commande TOUT son corps (poids et bouton, ou motif de refus). */
  const STRUCT_FIELDS = ["engine", "ultra", "mat", "finish", "side", "name",
                         "format"];

  /* clone + modifie + setGraph : `graph` est deep-freeze par le CORE dès
     qu'il est posé (schema simple, fusion superficielle) — une mutation en
     place lèverait TypeError en mode strict.

     I1 — NE PLUS TUER LE FOCUS : c'est le piège syncInputs/renderPanel de
     mod-face — un repaint de la LISTE à chaque édition détruit et recrée
     l'input focalisé, donc chaque pas de spinner (depth_mm/base_mm/grid) ou
     chaque changement de <select> (side) perd le focus et le curseur de
     saisie. Le DOM porte déjà la valeur commise par le navigateur : seul
     `kind` change la STRUCTURE du rang (base/grille apparaissent ou
     disparaissent) et exige donc, lui seul, un repaint. La 2b ajoute deux
     champs qui changent ce que le rang AFFICHE sans changer sa valeur
     (moteur, ultra : prix, case ultra, bouton) et deux qui font naître ou
     mourir un maillon (matière, finition) : ceux-là repeignent LE RANG SEUL,
     focus restauré, tiroirs conservés. */
  function editGraph(procId, field, rawValue, hoteNid) {
    const graph = get("graph");
    if (!graph || !procId) return;
    /* le nœud SOUS LES YEUX de l'utilisateur : c'est lui qu'on repeint et
       c'est SA vignette qui doit réagir. Dans la liste, c'est le traitement
       lui-même (un rang porte toute la chaîne). */
    const nid = hoteNid || procId;
    const next = JSON.parse(JSON.stringify(graph));
    const proc = next.nodes.filter((n) => n.id === procId)[0];
    if (!proc) return;
    /* M1b — la NAISSANCE d'un maillon est STRUCTURELLE même quand le champ
       édité, lui, ne l'est pas : le tiroir gagne sa puce, tuile/anisotropie
       s'activent, et le z semé par `editTrs` doit se voir TOUT DE SUITE (sans
       quoi l'écran afficherait 0 pendant que le graphe porte l'empilement). */
    let naissance = false;
    if (field === "kind") {
      proc.kind = (PROC_KINDS.indexOf(rawValue) >= 0) ? rawValue : "plane";
      /* les paramètres des autres traitements RESTENT sur le nœud (patron 2a :
         `clean_graph` ne garde que ceux du kind retenu, revenir en arrière ne
         perd rien). Le moteur, lui, doit exister dès le premier rendu du bloc,
         et il vient de /info — jamais d'une constante d'ici. */
      if (proc.kind === "mesh3d" && !proc.engine) proc.engine = defaultEngine();
    } else if (field === "side") {
      const edge = next.edges.filter((e) => e.to === procId)[0];
      const layer = edge ? next.nodes.filter((n) => n.id === edge.from)[0] : null;
      if (layer) layer.side = (rawValue === "back") ? "back" : "front";
    } else if (field === "grid") {
      const v = Math.round(Number(rawValue));
      if (isFinite(v)) proc.grid = v; else delete proc.grid;
    } else if (field === "depth_mm" || field === "base_mm") {
      const v = Number(rawValue);
      if (isFinite(v)) proc[field] = v; else delete proc[field];
    } else if (field === "engine") {
      proc.engine = String(rawValue || "");
      /* MÊME conservatisme que `clean_graph` sur l'axe qui coûte : l'ultra ne
         se reconduit jamais tout seul vers un moteur qui ne le propose pas —
         l'utilisateur n'a pas consenti à un surcoût qu'il n'a pas nommé. */
      if (ultraCredits(engineOf(proc.engine)) <= 0) delete proc.ultra;
    } else if (field === "ultra") {
      proc.ultra = !!rawValue;
    } else if (field === "texture_prompt") {
      const max = Number((mesh3dInfo() && mesh3dInfo().prompt_max) || 0);
      const t = String(rawValue == null ? "" : rawValue);
      proc.texture_prompt = max > 0 ? t.slice(0, max) : t;
    } else if (field === "name") {
      /* le NOM d'un artefact. La longueur est bornée ici comme au champ
         (ART_NAME_MAX, miroir du backend) ; le CHARSET, lui, reste l'affaire
         de `clean_graph` — et le nom RÉELLEMENT construit se relit dans
         `graph_used` (`artifactName`), jamais dans ce qu'on a tapé. */
      proc.name = String(rawValue == null ? "" : rawValue).slice(0, ART_NAME_MAX);
    } else if (field === "format") {
      /* seul un format SERVI s'écrit : le <select> ne peut en proposer
         d'autres, et `clean_graph` reste l'ultime porte (un format inconnu y
         retombe sur le premier). Refuser ici sans rien dire vaut mieux que
         d'écrire une valeur que le serveur remplacera en silence.
         ET LE REFUS SORT AVANT L'ÉCRITURE : `setGraph` est inconditionnel plus
         bas, donc laisser passer poussait une entrée d'annulation pour un
         graphe INCHANGÉ — « ↶ annuler format » aurait alors avalé un geste
         fantôme, et le vrai geste d'avant serait resté sous la pile. Le nœud
         est repeint pour que le menu revienne sur la valeur RÉELLEMENT
         portée. */
      const f = String(rawValue || "");
      if (exportFormats().indexOf(f) < 0) {
        paintChamps(procId, nid, field);
        return;
      }
      proc.format = f;
    } else if (MAT_FIELDS.indexOf(field) >= 0) {
      naissance = editMat(next, procId, field, rawValue);
    } else if (TRS_FIELDS.indexOf(field) >= 0) {
      naissance = editTrs(next, procId, field, rawValue);
    }
    setGraph(next, field);
    /* `kind` change la STRUCTURE du nœud : la vue ACTIVE se repeint entière,
       par le dispatcher comme les dix autres appelants. (La 2c a d'abord
       recopié la dispatche ICI pour satisfaire au mot près un pin de source
       de la 2a ; le pin a été AMENDÉ À SA SOURCE — il vérifie désormais
       l'invariant là où la logique vit, dans `paintVue`.) */
    /* UNE NAISSANCE (ou une mort) DE MAILLON EST STRUCTURELLE SUR LE CANVAS,
       pas seulement sur le rang : un nœud matière ou placement y APPARAÎT ou
       DISPARAÎT, avec ses arêtes et sa position — ce que seul `paintCanvas`
       sait poser (le semis d'un layout manquant y passe). Dans la liste, la
       même naissance ne change qu'une puce de tiroir : le rang suffit. */
    if (field === "kind" || (naissance && VUE === "canvas")) paintVue();
    else if (naissance || STRUCT_FIELDS.indexOf(field) >= 0) {
      paintChamps(procId, nid, field);
      /* LES DEUX MOITIÉS, PAS UNE. `paintChamps` refait le nœud (ou le rang)
         ÉDITÉ ; il ne touche pas aux VOISINS de la chaîne — et `side` change
         la PNG que le traitement et le placement dessinent, eux aussi. Sans
         cette seconde ligne, basculer une couche en verso corrigeait son
         en-tête et laissait les deux vignettes d'à côté sur le recto. */
      repeintChaine(procId, nid);
    } else {
      /* LA VIGNETTE RÉAGIT À LA VALEUR SAISIE, sans repeindre le champ (qui
         porte déjà ce que le navigateur vient de commettre) : c'est ce qui
         fait qu'une profondeur poussée d'un cran change l'emboss du relief
         SOUS le curseur, au lieu d'attendre un repaint global qui volerait
         justement ce curseur. */
      repeintChaine(procId, nid);
      paintCost();
    }
    /* L'INSPECTEUR SUIT L'ÉDITION (Task 5). Il promet de montrer « l'option
       DÉJÀ choisie » : le laisser sur l'aperçu d'avant le ferait mentir d'un
       cran à chaque réglage — une profondeur poussée, une matière posée, et le
       panneau montrerait encore l'état précédent. La reconstruction est
       DEBOUNCÉE (`INSP_MS`) et GRATUITE (`node-preview` ne lance aucun
       moteur) ; et comme `change` ne part qu'au COMMIT, c'est au plus une
       requête par réglage terminé, jamais une par caractère. */
    if (SEL) majInspecteur(true);
  }

  /* LA VIGNETTE DU NŒUD TOUCHÉ — ET DE SA CHAÎNE. Un champ n'appartient pas
     qu'à sa propre carte : changer la FACE d'une couche change la PNG que son
     traitement ET son placement dessinent tous les deux. Ne repeindre que le
     nœud édité laisserait deux vignettes voisines montrer le recto pendant
     que la troisième montre déjà le verso — un écran qui se contredit à
     l'œil. La chaîne est bornée par construction (couche, traitement,
     matière, placement : quatre nœuds au plus). */
  function repeintChaine(procId, nid) {
    paintNodeThumb(nid);
    const graph = get("graph");
    const r = graph ? rowModel(graph, procId) : null;
    if (!r) return;
    [r.layer, r.proc, r.mat, r.trs].forEach((x) => {
      if (x && x.id !== nid) paintNodeThumb(x.id);
    });
  }

  /* ── LA CHAÎNE D'UN RANG, RECONSTRUITE ─────────────────────────────────
     On ne touche QU'À l'aval : les arêtes ENTRANTES du traitement (les
     sources, y compris une source surnuméraire que le backend avoue) ne nous
     appartiennent pas. L'ordre canonique est celui du contrat serveur :
     traitement -> [matière] -> [placement] -> assemblage.
     `morts` porte les maillons que l'édition vient de RETIRER : leurs arêtes
     doivent tomber avec eux, sinon le graphe local garde des arêtes pendantes
     vers un nœud absent — `clean_graph` les jetterait côté serveur, mais
     l'écran, lui, montrerait une chaîne qui n'existe plus.

     M6 — LES MAILLONS SURNUMÉRAIRES PARTENT AVEC LA RÉÉCRITURE. L'API brute
     autorise deux matières en éventail sur un même traitement ; le backend
     retient la première et AVOUE la seconde dans `ignored`. Mais dès que
     l'utilisateur édite ce rang, son geste EST l'intention : garder un
     deuxième maillon que la chaîne réécrite n'emprunte plus laisserait dans
     le graphe un nœud que `build3d` dénoncerait à chaque construction, sans
     que l'écran ne l'ait jamais montré. On le retire — le rang affiché et le
     graphe disent alors la même chose. */
  function rewireRow(g, procId, matId, trsId, morts) {
    const garde = {};
    if (matId) garde[matId] = 1;
    if (trsId) garde[trsId] = 1;
    /* LES SURNUMÉRAIRES QUITTENT LE GRAPHE — eux seuls. `morts`, lui, ne
       purge que des ARÊTES : son nœud a déjà été retiré par l'appelant, et
       il porte aussi l'id d'un maillon qui vient de NAÎTRE (le retirer ici
       effacerait la matière que l'utilisateur vient de poser). */
    const surnum = maillonsAval(g, procId).filter((id) => !garde[id]);
    if (surnum.length) {
      const off = {};
      surnum.forEach((id) => { off[id] = 1; });
      g.nodes = (g.nodes || []).filter((n) => !off[n.id]);
    }
    const purge = {};
    (morts || []).forEach((id) => { if (id) purge[id] = 1; });
    surnum.forEach((id) => { purge[id] = 1; });
    if (matId) purge[matId] = 1;
    if (trsId) purge[trsId] = 1;
    g.edges = (g.edges || []).filter((e) => !(
      e.from === procId || purge[e.from] || purge[e.to]));
    const asm = (g.nodes || []).filter((n) => n.kind === "assemble")[0];
    const suite = [procId];
    if (matId) suite.push(matId);
    if (trsId) suite.push(trsId);
    if (asm) suite.push(asm.id);
    for (let i = 0; i + 1 < suite.length; i++) {
      g.edges.push({ from: suite[i], to: suite[i + 1] });
    }
  }

  /* TOUS les maillons (matière/placement) atteignables en aval d'un
     traitement — pas seulement ceux que la chaîne retient. C'est ce qui
     permet à `rewireRow` de distinguer le maillon GARDÉ des surnuméraires.
     Balayage en largeur, borné par `CHAIN_MAX` comme la descente du backend.
     N5, LIMITE AVOUÉE : un graphe CHARGÉ À LA MAIN (l'API brute est ouverte,
     cet écran ne produit jamais cette topologie — le glisser de connexion
     refuse une cible déjà pourvue d'une arête entrante, `surnumeraire` C1)
     peut partager un maillon entre deux rangées — le retrait suit alors
     l'intention de LA rangée éditée, et `clean_graph` comme le bordereau
     `ignored` avouent le reste. */
  function maillonsAval(g, procId) {
    const byId = {};
    (g.nodes || []).forEach((n) => { byId[n.id] = n; });
    const vus = {};
    let front = [procId];
    for (let k = 0; k < CHAIN_MAX && front.length; k++) {
      const suiv = [];
      (g.edges || []).forEach((e) => {
        if (front.indexOf(e.from) < 0) return;
        const t = byId[e.to];
        if (!t || (t.kind !== "material" && t.kind !== "transform")) return;
        if (vus[t.id]) return;
        vus[t.id] = 1;
        suiv.push(t.id);
      });
      front = suiv;
    }
    return Object.keys(vus);
  }

  /* un id LIBRE au charset du backend (`clean_graph` désinfecte sur
     [A-Za-z0-9._-] et tronque à 24) : le fabriquer déjà conforme évite qu'un
     nettoyage serveur ne renomme un nœud dont nos arêtes parlent encore. */
  function freeId(nodes, base) {
    const pris = {};
    (nodes || []).forEach((n) => { pris[n.id] = 1; });
    const racine = String(base).replace(/[^A-Za-z0-9._-]/g, "_").slice(0, 20) || "n";
    if (!pris[racine]) return racine;
    for (let k = 2; k < 500; k++) {
      if (!pris[racine + k]) return racine + k;
    }
    /* M5 — inatteignable, et pour la bonne raison : ce ne sont pas les
       ÉLÉMENTS (`graph_limits.max_elements`, le plafond métier appliqué APRÈS
       résolution par build3d) qui bornent ce compteur, mais les NŒUDS, que
       `clean_graph` tronque à `_GRAPH_ITER_MAX` (200). 500 candidats ne
       peuvent donc pas être tous pris. */
    return racine + "999";
  }

  function editMat(g, procId, field, rawValue) {
    const r = rowModel(g, procId);
    if (!r) return false;
    let mat = r.mat;
    const neuf = !mat;
    if (neuf) {
      mat = { id: freeId(g.nodes, procId + "m"), kind: "material" };
      g.nodes.push(mat);
    }
    if (field === "mat") mat.mat = String(rawValue || "") || null;
    else if (field === "finish") mat.finish = String(rawValue || "aucune");
    else if (field === "aniso") mat.aniso = !!rawValue;
    else if (field === "tile_mm") {
      const v = Number(rawValue);
      if (isFinite(v)) mat.tile_mm = v; else delete mat.tile_mm;
    }
    /* MÊME règle que `clean_graph` : une matière sans matière NI finition
       n'est rien. On retire le maillon plutôt que de laisser dans le graphe un
       nœud que le serveur jetterait en silence — l'écran montrerait alors une
       chaîne que la construction ne suivrait pas. */
    const vide = !mat.mat && (!mat.finish || mat.finish === "aucune");
    if (vide) g.nodes = g.nodes.filter((n) => n.id !== mat.id);
    rewireRow(g, procId, vide ? null : mat.id, r.trs ? r.trs.id : null,
              [mat.id]);
    /* la NAISSANCE (comme la mort) d'un maillon change ce que le rang montre :
       la puce du tiroir, l'activation de tuile/anisotropie. */
    return neuf || vide;
  }

  function editTrs(g, procId, field, rawValue) {
    const r = rowModel(g, procId);
    if (!r) return false;
    let trs = r.trs;
    const neuf = !trs;
    if (neuf) {
      /* I1 — L'ÉLÉMENT NEUTRE D'UN PLAN PORTE SON z D'EMPILEMENT. Côté writer,
         `translate` REMPLACE le `z_mm` de l'élément (`_node_trs`) : il ne s'y
         ajoute pas. Semer un z à zéro n'était donc pas « neutre » du tout — ça
         APLATISSAIT le plan sur la couche du dessous (le cadre du graphe par
         défaut vit à 1,05 mm), et il suffisait d'ouvrir le tiroir Placement
         pour pousser x de 2 mm afin de perdre la parallaxe et gagner du
         z-fighting : le GLB et le STL d'accord entre eux, et tous deux en
         désaccord avec ce que l'utilisateur voyait une frappe plus tôt.
         `zEmpilement` est la MÊME règle que celle qu'affiche `trsHtml`. */
      trs = { id: freeId(g.nodes, procId + "t"), kind: "transform",
              x_mm: 0, y_mm: 0, z_mm: zEmpilement(r.proc), rot_deg: 0, scale: 1 };
      g.nodes.push(trs);
    }
    const v = Number(rawValue);
    if (isFinite(v)) trs[field] = v;
    rewireRow(g, procId, r.mat ? r.mat.id : null, trs.id);
    return neuf;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     LES JOBS mesh3d — LA SEULE DÉPENSE DE CET ÉCRAN
     Lancer POSTe le graphe COURANT (le backend le renettoie et n'en retient
     que le nœud visé) ; l'état, lui, ne vient jamais de ce qu'on a envoyé :
     il est POLLÉ sur `GET mesh3d/<nid>` jusqu'au terminal.
     ═══════════════════════════════════════════════════════════════════════ */
  async function launchMesh3d(nid) {
    const graph = get("graph");
    if (!nid || !graph) return;
    if (POLLS[nid]) {
      /* un clic pendant la lecture d'un état (ou pendant un job vivant) ne
         disparaît pas en silence : le backend refuserait en 409, l'écran le
         dit d'abord. */
      M.toast("état de ce nœud en cours de lecture — réessayez");
      return;
    }
    const zone = findByAttr(".cf-forge3d-run", "data-nid", nid);
    const btn = zone ? zone.querySelector("[data-act='launch']") : null;
    if (btn) btn.disabled = true;
    ERRS[nid] = null;
    RUNS[nid] = false;
    /* N1 — LA GARDE DE GÉNÉRATION SUR LE CHEMIN QUI DÉPENSE. C'est le seul
       endroit de l'écran qui engage de l'argent, et il traverse un await : si
       la carte (ou le deck) change pendant le POST, écrire le job au retour
       poserait l'état d'un job de la carte 1 dans l'écran de la carte 2 — la
       chip mentirait sur ce qui a été servi, et le pied de coût SOUS-ESTIMERAIT
       (un nœud compté « servi » alors qu'il ne l'est pas pour cette carte-ci).
       Le job, lui, existe bel et bien côté serveur : il n'est pas perdu, il
       sera relu par la sonde quand on reviendra sur SA carte. */
    const gen = GEN;
    try {
      const carte = (CF.current ? CF.current() : 0);
      const rep = await M.api.post("mesh3d/" + encodeURIComponent(nid),
                                   { graph: graph, card: carte });
      if (gen !== GEN) return;   /* cette carte n'est plus à l'écran */
      /* on ne peint QUE ce que le backend a rendu : pas de job, pas de chip
         inventée — le poll qui suit dira l'état depuis le disque. */
      JOBS[nid] = (rep && rep.job) || null;
      SEEN[nid] = Date.now();
      paintChip(nid);
      paintCost();
      pollMesh3d(nid);
    } catch (e) {
      if (gen !== GEN) return;
      ERRS[nid] = String(e && e.message || e);
      paintChip(nid);
      M.toast(ERRS[nid], true);
    }
  }

  /* M7 — LES DEUX 404 NE DISENT PAS LA MÊME CHOSE, et `M.api.get` les
     confond : le CORE lève `ApiMissing` sur le statut AVANT même de lire le
     corps, donc « aucun job sur ce noeud » (jamais lancé — une RÉPONSE) et
     « Deck introuvable » / route absente (une PANNE) arrivent avec le même
     message générique. On passe donc par `M.api.raw`, qui rend la réponse
     telle quelle, et c'est le `detail` du backend qui tranche. */
  async function fetchJob(nid) {
    const r = await M.api.raw("GET", "mesh3d/" + encodeURIComponent(nid));
    /* N2 — ET LA GARDE QUE LE CORE AVAIT, REPRISE : en sortant de `M.api.get`
       on a perdu son contrôle de type de contenu (core.js:1161). Sans lui, un
       backend absent derrière un attrape-tout SPA rend 200 + du HTML, `json()`
       échoue, `d` vaut null, et `r.ok` déclare le nœud « jamais lancé » — une
       réponse fausse et CONFIANTE, exactement ce que la distinction des deux
       404 existait pour empêcher. Un 200 qui n'est pas du JSON est une route
       absente, pas un job absent. */
    const ct = (r.headers.get("content-type") || "").toLowerCase();
    if (r.ok && ct.indexOf("json") < 0) {
      return { erreur: "route absente sur ce backend (reponse non JSON)" };
    }
    let d = null;
    try { d = await r.json(); } catch (e) { d = null; }
    if (r.ok) return { job: d || null };
    const detail = (d && (d.detail || d.error)) || (r.status + " " + r.statusText);
    if (r.status === 404 && /aucun job/i.test(String(detail))) return { job: null };
    return { erreur: String(detail) };
  }

  /* I3b — FAUT-IL RE-SONDER CE NŒUD ? Jamais vu : oui. Job vivant : non, une
     boucle le suit déjà. Job TERMINAL : oui, mais au plus une fois par
     `REPROBE_MS` — sans cela, l'état gelait au dernier poll et « relancé
     ailleurs » ne pouvait plus jamais se déclencher, alors que c'est
     précisément après la fin d'un job qu'un autre onglet le relance. */
  function aResonder(nid) {
    if (!Object.prototype.hasOwnProperty.call(JOBS, nid)) {
      /* N4 — MÊME CADENCE POUR L'ÉCHEC. Une sonde qui a échoué (transport
         coupé, route absente) ne laisse PAS de clé dans `JOBS` : sans cette
         limite, chaque peinture relançait aussitôt une requête vouée au même
         échec. `SEEN` est posé par toutes les issues du poll, y compris
         celle-là : c'est lui qui espace les reprises. */
      return !SEEN[nid] || (Date.now() - SEEN[nid]) > REPROBE_MS;
    }
    const job = JOBS[nid];
    if (job && (job.status === "queued" || job.status === "running")) return false;
    return (Date.now() - (SEEN[nid] || 0)) > REPROBE_MS;
  }

  /* UN poll par nœud (registre `POLLS`) : recliquer Lancer pendant qu'un job
     court ne peut pas empiler deux boucles. `immediat` sert au SONDAGE — une
     seule requête, qui se prolonge en boucle uniquement si le job trouvé est
     encore vivant. Le registre porte la GÉNÉRATION, pas `true` : un tic
     rassis ne retire que sa propre entrée, jamais celle de son successeur. */
  function pollMesh3d(nid, immediat) {
    if (!nid || POLLS[nid]) return;
    if (immediat && !aResonder(nid)) return;
    const gen = GEN;
    POLLS[nid] = gen;
    const relache = () => { if (POLLS[nid] === gen) delete POLLS[nid]; };
    const tick = async () => {
      if (gen !== GEN) { relache(); return; }
      let rep = null;
      try {
        rep = await fetchJob(nid);
      } catch (e) {                    /* panne de transport, pas une réponse */
        rep = { erreur: String(e && e.message || e) };
      }
      if (gen !== GEN) { relache(); return; }
      SEEN[nid] = Date.now();
      if (rep.erreur) {
        relache();
        ERRS[nid] = rep.erreur;
        paintChip(nid);
        paintCost();
        return;
      }
      const job = rep.job;
      const avant = JOBS[nid];
      /* `run_id` est OPAQUE (jamais inventé ni renvoyé par l'écran) mais
         COMPARABLE : s'il a changé entre deux lectures, ce n'est pas notre job
         qui progresse — un AUTRE onglet a relancé ce nœud. On le DIT plutôt
         que de laisser l'état basculer en silence. */
      if (avant && avant.run_id && job && job.run_id && avant.run_id !== job.run_id) {
        RUNS[nid] = true;
      }
      JOBS[nid] = job;
      ERRS[nid] = null;
      paintChip(nid);
      paintCost();
      if (!job || job.status === "served" || job.status === "failed") {
        relache();
        return;
      }
      setTimeout(tick, POLL_MS);
    };
    if (immediat) tick(); else setTimeout(tick, POLL_MS);
  }

  /* ═══════════════════════════════════════════════════════════════════════
     CONSTRUIRE — POST build3d {graph, card}, le bordereau peint UNIQUEMENT
     la réponse mesurée (jamais l'intention envoyée : `graph_used` est le
     graphe NETTOYÉ par le backend, pas celui qu'on vient de poster).
     ═══════════════════════════════════════════════════════════════════════ */
  async function build3d() {
    if (build3d.busy) return;
    const graph = get("graph");
    const btn = $("#cf-forge3d-build");
    const status = $("#cf-forge3d-build-status");
    if (!graph) {
      if (status) status.textContent = "construisez d'abord le graphe (par "
        + "défaut ou personnalisé), ci-dessus.";
      return;
    }
    build3d.busy = true;
    if (btn) btn.disabled = true;
    /* le bouton du NŒUD artefact dit la même chose que celui de la section :
       `artifactNodeHtml` lit `build3d.busy`, il suffit de le repeindre. */
    repeintLeBordereau();
    if (status) status.textContent = "construction…";
    /* N1 (même forme, enjeu moindre) : le bordereau d'une construction décrit
       LA carte pour laquelle elle a tourné — le peindre dans l'écran d'une
       autre attribuerait ses fichiers et son aperçu à la mauvaise. */
    const gen = GEN;
    try {
      const carte = (CF.current ? CF.current() : 0);
      const rep = await M.api.post("build3d", { graph: graph, card: carte });
      if (gen !== GEN) return;
      ARTIFACT = rep.artifact;
      paintArtifact(ARTIFACT);
      /* le nœud artefact porte le MÊME bordereau et les exports en dépendent :
         on les repeint AVANT de monter l'aperçu, sans quoi le viewer se
         monterait dans un corps qu'on s'apprête à remplacer. */
      repeintLeBordereau();
      if (status) status.textContent = ARTIFACT.elements + " élément(s) — "
        + weight(ARTIFACT.glb.bytes) + " · " + ARTIFACT.ms.total + " ms.";
      await mountPreview(ARTIFACT.glb.name);
    } catch (e) {
      if (status) status.textContent = String(e && e.message || e);
      M.toast(String(e && e.message || e), true);
      /* I3a — LE BACKEND VIENT DE CONTREDIRE NOS CHIPS. La plupart des refus
         de `build3d` parlent d'un nœud moteur (n'a pas servi, GLB disparu,
         servi pour une AUTRE couche, trop lourd) : notre état en cache est
         donc périmé, et le garder afficherait « servi » sur le nœud même que
         le serveur vient de refuser. On oublie l'état des nœuds moteur du
         graphe — bornés par le graphe lui-même — et la peinture qui suit les
         re-sonde depuis le disque. */
      rowsDe(graph).forEach((r) => {
        if (r.proc.kind !== "mesh3d") return;
        delete JOBS[r.proc.id];
        delete SEEN[r.proc.id];
      });
      paintVue();
    } finally {
      build3d.busy = false;
      if (btn) btn.disabled = false;
      repeintLeBordereau();
    }
  }

  /* le nom de l'artefact : lu dans `graph_used` (ce que le backend a
     RÉELLEMENT construit), jamais dans le graphe posté — un nœud artifact
     jeté par clean_graph retomberait sur "artefact" cote serveur, jamais
     recopie en dur ici. */
  function artifactName(art) {
    const nodes = (art && art.graph_used && art.graph_used.nodes) || [];
    const n = nodes.filter((x) => x.kind === "artifact")[0];
    return (n && n.name) || "artefact";
  }

  /* ── LE BORDEREAU DE BUILD3D — peint depuis la REPONSE, jamais l'intention.
     GLB + metadata.json (+ STL si écrit) : même patron de téléchargement que
     paintSlip (provenance M.api.blob). Le motif STL refusé est affiché TEL
     QUEL (art.stl.why) — jamais réécrit par l'écran. `ignored` (le contrat
     d'honnêteté du backend) est rendu ligne par ligne s'il n'est pas vide. */
  function paintArtifact(art) {
    const slip = $("#cf-forge3d-build-slip");
    if (!slip || !art) return;
    const files = [
      { label: "GLB", name: art.glb.name, bytes: art.glb.bytes },
      { label: "metadata.json", name: art.metadata.name, bytes: art.metadata.bytes },
    ];
    let stlHtml;
    if (art.stl && art.stl.written) {
      files.push({ label: "STL", name: art.stl.name, bytes: art.stl.bytes });
      stlHtml = '<p class="mono">STL : imprimable, solide fermé prouvé.</p>';
    } else {
      stlHtml = '<p class="hint"><b>STL non fourni</b> : '
        + esc(art.stl.why) + '</p>';
    }
    /* MÊME ligne de fichier que les nœuds d'export (Task 5) : `fichierHtml`
       est la seule écriture de ce balisage dans le module. */
    const rows = files.map(
      (f) => fichierHtml(f.label, f.name, f.bytes)).join("");
    const previewHtml = '<p class="hint">aperçu : ' + (art.preview.written
      ? "figé — " + esc(art.preview.expected)
      : "en attente (" + esc(art.preview.expected) + ")") + '</p>';
    /* 2b — CE QUI A ÉTÉ ASSEMBLÉ, ÉLÉMENT PAR ÉLÉMENT : `elements` reste le
       NOMBRE (la phrase de la 2a le concatène) et le détail vit dans
       `elements_detail`. Le moteur et les crédits RÉELLEMENT consommés y sont
       ceux du job.json de chaque nœud — la comptabilité du fournisseur, pas
       le devis annoncé avant. */
    const detail = (art.elements_detail && art.elements_detail.length)
      ? ('<p class="hint">éléments assemblés :</p>'
        + '<ul class="cf-forge3d-elems">'
        + art.elements_detail.map((d) => '<li class="mono">' + esc(d.name)
          + " · " + esc(d.kind) + " · " + esc(d.node)
          + (d.engine ? " · " + esc(d.engine) : "")
          + (d.credits != null ? " · " + Number(d.credits) + " cr" : "")
          + "</li>").join("")
        + "</ul>")
      : "";
    slip.innerHTML = rows + stlHtml + previewHtml + detail + ignoresHtml(art);
  }

  /* ═══════════════════════════════════════════════════════════════════════
     APERÇU — <model-viewer> sur le VRAI fichier livré : la provenance
     d'abord (M.api.blob, pas une URL directe), objectURL révoquée avant
     d'en poser une nouvelle (patron mod-gltf.js:ATLAS/compose). Le script
     est déjà chargé par la coquille (index.html:23).
     ═══════════════════════════════════════════════════════════════════════ */
  /* OÙ VIT LE VIEWER DU RÉSULTAT — et il n'y en a QU'UN (le 2e et dernier
     contexte WebGL de cet écran). Sur le canvas, c'est DANS le nœud artefact :
     la spec §5.6 veut le résultat là où vit l'action qui le produit. En vue
     liste — ou tant qu'aucun nœud artefact n'est peint — c'est la section
     « Aperçu », qui ne disparaît pas pour autant : elle reste le repli sans
     pointeur. Le MÊME élément déménage de l'un à l'autre. */
  function hoteApercu() {
    const host = $("#cf-forge3d-canvas");
    const dans = (VUE === "canvas" && host)
      ? host.querySelector(".cf-forge3d-art-view") : null;
    return dans || $("#cf-forge3d-view");
  }

  /* CRÉE-OU-DÉMÉNAGE le viewer du résultat. Rend `null` quand la visionneuse
     n'est pas chargée : l'hôte dit alors pourquoi, et le fichier reste
     téléchargeable — il EST construit, c'est l'affichage qui manque. */
  function poseViewer(host) {
    if (!host || typeof document === "undefined") return null;
    if (typeof customElements === "undefined"
        || !customElements.get("model-viewer")) {
      host.innerHTML = '<p class="empty-note sm">La visionneuse 3D '
        + '(/assets/model-viewer.min.js) n\'est pas chargée. Le fichier, lui, '
        + 'est construit et téléchargeable.</p>';
      return null;
    }
    if (!MV) {
      MV = document.createElement("model-viewer");
      MV.id = "cf-forge3d-mv";
      MV.setAttribute("camera-controls", "");
      MV.setAttribute("auto-rotate", "");
      /* LA SCÈNE EST LÀ — et c'est le SEUL endroit qui a le droit de le dire.
         Le drapeau est levé avant le déverrouillage : une repeinture qui
         tomberait entre les deux re-poserait sinon un bouton verrouillé. */
      MV.addEventListener("load", () => { FIGE_PRET = true; majFige(false); });
      MV.addEventListener("error", () => {
        M.toast("la visionneuse n'a pas pu ouvrir le GLB", true);
      });
    }
    if (MV.parentNode !== host) {
      host.innerHTML = "";
      host.appendChild(MV);
      /* seulement QUAND IL DÉMÉNAGE, pas à chaque repeinture de nœud : cette
         fonction n'a rien à dire tant que rien n'a bougé, et `paintNode`
         passe ici à chaque champ commis. */
      majSectionApercu();
    }
    return MV;
  }

  /* LA SECTION « Aperçu » NE RESTE PAS UN CADRE VIDE quand le viewer est parti
     vivre dans le nœud artefact : elle DIT où il est. Un panneau vide se lit
     comme une panne — celui-là surtout, juste sous le bouton qui vient de
     construire. */
  function majSectionApercu() {
    const sect = $("#cf-forge3d-view");
    if (!sect) return;
    if (MV && MV.parentNode === sect) return;   /* il est ici : rien à dire */
    const dit = !PREVIEW_URL ? ""
      : ('<p class="empty-note sm">l\'aperçu est monté dans le '
        + 'nœud <b>artefact</b>, sur le canvas — bascule sur « liste » pour le '
        + 'revoir ici.</p>');
    /* ÉCRIRE SEULEMENT SI ÇA CHANGE. Le narrowing de `poseViewer` (« seulement
       quand il DÉMÉNAGE ») ne couvre PAS le cas le plus fréquent : `paintNode`
       remplace le corps du nœud artefact, ce qui DÉTACHE le viewer — au
       ré-accrochage `MV.parentNode` est donc toujours ≠ hôte, et cette
       fonction repassait à chaque champ commis. Elle réécrivait alors le même
       texte dans la section, pour rien. Comparer avant d'écrire est le fond du
       remède, et il ne peut pas régresser : au pire l'égalité échoue et on
       réécrit comme avant. */
    if (sect.innerHTML !== dit) sect.innerHTML = dit;
  }

  /* L'APERÇU DU RÉSULTAT, RENDU : objectURL révoquée, viewer détaché et
     lâché, section vidée, boutons re-verrouillés. L'ÉLÉMENT survit (une seule
     naissance par onglet — voir `MV`), ce qu'il montrait, non. */
  function videApercu() {
    if (PREVIEW_URL && typeof URL !== "undefined") URL.revokeObjectURL(PREVIEW_URL);
    PREVIEW_URL = null;
    FIGE_PRET = false;    /* la scène part avec les octets */
    if (MV) {
      MV.removeAttribute("src");
      if (MV.parentNode) MV.parentNode.removeChild(MV);
    }
    const sect = $("#cf-forge3d-view");
    if (sect) sect.innerHTML = "";
    majFige(true);
  }

  /* LES DEUX BOUTONS « figer » — celui de la section et celui du nœud
     artefact — SONT LE MÊME GESTE. Les laisser diverger ferait cliquer sur
     l'un pendant que l'autre se sait occupé (ou pas encore prêt). */
  function majFige(off) {
    const b = $("#cf-forge3d-freeze");
    if (b) b.disabled = !!off;
    const hote = hoteVue();
    const n = hote ? findByAttr("[data-act]", "data-act", "freeze", hote) : null;
    if (n) n.disabled = !!off;
  }

  /* LE VIEWER SURVIT AUX REPEINTURES. `paintCanvas` reconstruit le monde en un
     `innerHTML` et `paintNode` réécrit l'intérieur d'un nœud : dans les deux
     cas, un viewer monté DANS le nœud artefact est détaché avec lui. On le
     RE-ACCROCHE sans rien re-télécharger — une objectURL survit au DOM qui la
     montrait, et `PREVIEW_URL` tient toujours les octets déjà livrés. */
  function remonteApercu() {
    if (!PREVIEW_URL) return;
    const mv = poseViewer(hoteApercu());
    if (!mv) return;
    if (mv.getAttribute("src") !== PREVIEW_URL) mv.setAttribute("src", PREVIEW_URL);
  }

  async function mountPreview(name, hote) {
    const host = hote || hoteApercu();
    if (!host) return;
    try {
      const blob = await M.api.blob("GET", "file/" + encodeURIComponent(name));
      if (PREVIEW_URL) URL.revokeObjectURL(PREVIEW_URL);
      PREVIEW_URL = URL.createObjectURL(blob);
      const mv = poseViewer(host);
      if (!mv) return;
      /* re-verrouillé jusqu'au prochain `load` — le DRAPEAU d'abord (le bouton
         du nœud renaît à chaque repeinture et le lit), la porte du bouton
         ensuite, et la source EN DERNIER : poser `src` avant aurait laissé un
         `load` très rapide relever le drapeau qu'on s'apprêtait à baisser. */
      FIGE_PRET = false;
      majFige(true);
      mv.setAttribute("src", PREVIEW_URL);
    } catch (e) {
      M.toast(String(e && e.message || e), true);
    }
  }

  /* « figer l'aperçu » : modelViewer.toBlob() (API officielle 3.3.3) capture
     le rendu affiché, POST preview/<art> l'écrit tel quel côté serveur —
     RIEN de la carte n'est rendu au serveur (patron du domaine). Si toBlob()
     échoue (WebGL absent), toast honnête, pas de crash. */
  async function freezePreview() {
    /* UN SEUL GESTE À LA FOIS (patron `build3d.busy`) : DEUX boutons « figer »
       déclenchent désormais la même chose (la section et le nœud artefact), et
       deux POST concurrents écriraient deux fois la même image en se
       contredisant sur son poids. */
    if (freezePreview.busy) return;
    const mv = (MV && MV.isConnected) ? MV : null;
    const status = $("#cf-forge3d-freeze-status");
    if (!mv || !ARTIFACT) {
      M.toast("construisez et affichez l'aperçu d'abord", true);
      return;
    }
    freezePreview.busy = true;
    majFige(true);
    try {
      const blob = await mv.toBlob();
      const name = artifactName(ARTIFACT);
      const r = await M.api.raw("POST", "preview/" + encodeURIComponent(name), blob);
      if (!r.ok) {
        let d = null;
        try { d = await r.json(); } catch (err) { d = null; }
        throw new Error((d && d.detail) || ("aperçu refusé (" + r.status + ")"));
      }
      const d = await r.json();
      /* le POIDS vient de la RÉPONSE (ce que le serveur a écrit), jamais de la
         taille du blob envoyé : c'est lui que le nœud d'export « preview »
         affichera. */
      ARTIFACT = Object.assign({}, ARTIFACT, {
        preview: { expected: ARTIFACT.preview.expected, written: true,
                   bytes: (d && d.preview) ? d.preview.bytes : null },
      });
      paintArtifact(ARTIFACT);
      repeintLeBordereau();
      if (status) status.textContent = "aperçu figé — " + weight(d.preview.bytes) + ".";
      M.toast("aperçu figé");
    } catch (e) {
      if (status) status.textContent = String(e && e.message || e);
      M.toast(String(e && e.message || e), true);
    } finally {
      freezePreview.busy = false;
      majFige(false);
    }
  }

  /* LES NŒUDS QUI PARLENT DU BORDEREAU — l'artefact et les exports — repeints
     UN PAR UN quand `ARTIFACT` change. Reconstruire le monde entier ferait
     détacher le viewer que l'utilisateur vient de cadrer ; ces deux kinds
     sont les seuls dont le corps LIT `ARTIFACT`, il n'y a rien d'autre à
     rafraîchir. */
  function repeintLeBordereau() {
    if (VUE !== "canvas") return;
    const graph = get("graph");
    ((graph && graph.nodes) || []).forEach((n) => {
      if (n.kind === "artifact" || n.kind === "export") paintNode(n.id);
    });
  }
})();
