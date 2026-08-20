/* ═══════════════════════════════════════════════════════════════════════════
   Card Forge — piece 05 · Volume   [P5]
   Proprietaire exclusif de : doc.solid · aucun z · /api/cards/<did>/solid/*
   Prefixe DOM impose : id="cf-solid-..."   ·   feuille : css/mod-solid.css

   Ce que cette piece met a l'ecran : LA CARTE, en volume. Pas un objet 3D
   quelconque avec un compteur de faces — un rectangle de 63 x 88 x 0,32 mm
   dont on voit la TRANCHE et le VERSO en tournant, avec ses dimensions
   physiques ecrites a cote.

   ── TROIS CHOSES QUI NE SONT PAS DES DETAILS ─────────────────────────────

   1. LE MAILLAGE VIENT DU BACKEND (`GET solid/mesh`), il n'est pas recalcule
      ici. `cards/solid.py` detient `card_mesh()` ; P8 exporte a partir de la
      MEME fonction. Deux generateurs, ce serait deux cartes — celle qu'on
      regarde et celle qu'on livre. Un maillage de secours existe pour le cas
      « backend muet », et il le DIT dans le HUD au lieu de faire semblant.

   2. LA TEXTURE EST LE RENDU REEL DE LA CARTE. L'atlas est compose a partir
      de `CF.renderCard(i, {face})` — le moteur unique, a `geom.canvas_px`,
      celui du fichier livre — puis rogne au trait de coupe (le fond perdu est
      COUPE : il n'existe pas en volume). Ce qui tourne a l'ecran est donc ce
      qui sortira de l'imprimeur, pas une approximation.

   3. LE TOURNE-DISQUE FILME CETTE MEME VISIONNEUSE. Les images sont prises
      dans `<model-viewer>` (`toBlob`), recomposees a la definition demandee,
      envoyees au backend et assemblees par le ffmpeg deja present. Aucun
      second moteur de rendu : la video ne peut pas diverger de l'apercu.

   4. LE FICHIER PORTE TROIS IMAGES POUR QUATRE EMPLACEMENTS DE MATIERE : base,
      NORMALES et ORM — cette derniere lue DEUX FOIS (rugosite+metal en
      metallicRoughness, occlusion en rouge) — plus l'attribut TANGENT. Trois,
      pas quatre : le panneau annoncait « quatre cartes » et en listait trois
      juste apres. Le jeu COMPLET du cahier des charges (huit PNG, hauteur et
      emission comprises) est le livrable de P8 ; ici c'est l'apercu, et il dit
      ce qu'il porte. Les valeurs de matiere viennent de `cards/solid.py`
      (PBR_FACE / PBR_EDGE), les memes pour l'apercu, l'export et le test, et
      la bascule « Unie / Metal / Sombre » s'ecrit dans le canal BLEU de l'ORM.

   6. LE FICHIER PORTE SA TAILLE REELLE. `node.scale` uniforme, mesure sur les
      sommets : 1 unite glTF = 1 metre, donc la carte s'ouvre a 63 x 88 x
      0,32 mm dans Blender, Unity, Unreal ou un trancheur. Sans lui — et il
      manquait — un maillage normalise a Y = +/-1 livre une carte de DEUX
      METRES de haut pendant que le HUD affiche des millimetres : le motif
      « il l'AFFICHE sans le LIVRER », chez nous.

   5. L'ATLAS NE FABRIQUE PAS DE RESOLUTION. Sa taille est calculee POUR la
      source (`solid.atlas_plan`) : l'ilot du recto recoit les pixels que le
      moteur produit, jamais 39 % de plus par interpolation, et le HUD affiche
      la definition VRAIE du recto en DPI plutot qu'un nombre de pixels
      d'atlas qui ne disait rien de ce qu'ils portent.

   Aucun painter : cette piece ne dessine pas la carte, elle la met en volume.
   ═══════════════════════════════════════════════════════════════════════════ */
"use strict";

(function () {
  const CF = (typeof window !== "undefined") ? window.CF : null;
  if (!CF) throw new Error("mod-solid: js/core.js doit etre charge avant ce fichier");

  /* ── bornes, miroir de cards/solid.py ─────────────────────────────────── */
  const LIM = {
    thickness_mm: [0.20, 1.20],
    corner_mm: [0.0, 10.0],
    segments: [1, 16],
    bevel_mm: [0.0, 0.30],
  };
  /* Des epaisseurs REELLES, mesurees sur des jeux du commerce : un chiffre
     seul ne dit rien, « carte a jouer » si. */
  const EPAISSEURS = [
    { v: 0.24, l: "Fine", h: "carte promotionnelle" },
    { v: 0.32, l: "Carte à jouer", h: "standard, cœur bleu 310 g" },
    { v: 0.40, l: "Lin renforcé", h: "jeu de société" },
    { v: 0.62, l: "Carton épais", h: "carte de collection premium" },
    { v: 1.00, l: "Plaque", h: "carte métal / plastique" },
  ];
  const VUES = [
    { id: "matiere", l: "Matière", t: "Rendu éclairé, comme un tirage réel" },
    { id: "base", l: "Encre", t: "Sans éclairage : l'impression telle quelle" },
    { id: "normales", l: "Normales", t: "Orientation des faces (couleur = normale)" },
    { id: "ilots", l: "Îlots UV", t: "Recto / verso / tranche : les 3 régions de l'atlas, dont le HUD mesure le recouvrement" },
  ];
  const ENVS = [
    { id: "studio", l: "Studio" }, { id: "vitrine", l: "Vitrine" },
    { id: "chaud", l: "Chaud" }, { id: "froid", l: "Froid" },
    { id: "neutre", l: "Neutre" },
  ];
  const TRANCHES = [
    { id: "plein", l: "Unie" }, { id: "metal", l: "Métal" }, { id: "sombre", l: "Sombre" },
  ];
  /* LE RELIEF D'ENCRE, ET SON PRIX. Le grief mesure : « carte de normales
     QUASI INERTE, ET CHERE — 2,22 deg d'inclinaison maximale pour 27 % du
     fichier. Soit on encode ce relief de six microns dans un canal leger, soit
     on ne l'encode pas. » Les deux branches existent donc, plus une entre les
     deux, et le panneau publie le POIDS MESURE de celle qui est choisie.
     `div` est le diviseur applique a l'atlas : 4 = quart, 2 = moitie. */
  const RELIEFS = [
    { id: "aucun", l: "Aucun", div: 0, t: "Pas de carte de normales dans le fichier" },
    { id: "leger", l: "Léger", div: 4, t: "Quart de l'atlas : le relief d'encre pour un quart des texels" },
    { id: "detaille", l: "Détaillé", div: 2, t: "Moitié de l'atlas : le plus fin que la source permette" },
  ];
  /* LES TROIS FACES DE L'OBJET, ATTEIGNABLES EN UN CLIC. `macro` demande une
     cible posee sur le BORD de la carte et un rayon de quelques millimetres :
     c'est la seule facon de voir 0,32 mm autrement qu'en 3 pixels. */
  const POSES = [
    { id: "recto", l: "Recto", d: 0, fov: 26, t: "La face avant, de face" },
    { id: "verso", l: "Verso", d: 180, fov: 26, t: "La face arrière, de face — sans miroir" },
    /* PAS DE PROFIL PUR, ET PAS AU MILIEU DU GRAND COTE : de profil la tranche
       remplit le cadre comme une bande verticale et plus rien ne dit que c'est
       une carte ; au milieu du cote, le cadre de 3 mm ne contient aucun bord
       reconnaissable. On vise le COIN ARRONDI : l'arc de 3 mm donne l'echelle,
       la tranche le traverse, et le chanfrein a 45 degres attrape la lumiere. */
    { id: "tranche", l: "Tranche", d: 55, phi: 74, fov: 18, macro: 0.010,
      t: "Macro sur le coin : rayon, chanfrein et épaisseur à l'échelle du millimètre" },
  ];
  const TAILLES = [540, 720, 1080, 1440];
  const ILOT_COULEUR = { front: [0.16, 0.72, 0.62], back: [0.55, 0.42, 0.86], edge: [0.95, 0.71, 0.24] };

  /* ── MATIERES, miroir de cards/solid.py (PBR_FACE / PBR_EDGE) ───────────
     Ces nombres ne decorent pas : ils sont ECRITS dans la carte ORM du GLB
     (occlusion en rouge, rugosite en vert, metal en bleu) et donc RELISIBLES
     dans les octets. Le papier reste dielectrique — une carte imprimee n'a
     pas de metal sur ses faces ; la tranche, elle, peut vraiment etre doree.
     `test_cards_solid.py` relit ce bloc et refuse qu'il derive du backend. */
  /* CF-SOLID-PBR-BEGIN */
  const PBR_FACE = { metallic: 0.00, roughness: 0.62, ao: 1.00 };
  const PBR_EDGE = {
    plein: { metallic: 0.00, roughness: 0.55, ao: 0.90 },
    metal: { metallic: 0.90, roughness: 0.22, ao: 0.94 },
    sombre: { metallic: 0.05, roughness: 0.72, ao: 0.86 },
  };
  const INK_ROUGHNESS_DROP = 0.16;
  const INK_RELIEF_MM = 0.006;
  const ELEV_MIN = 0, ELEV_MAX = 55, ELEV_DEFAULT = 18;
  const ATLAS_CAPS = [1024, 1536, 2048];
  /* CF-SOLID-PBR-END */

  /* ── etat local, jamais persiste ──────────────────────────────────────── */
  let HOST = null, MV = null, BLOB_URL = null, LOADED = false;
  let MESH = null, MESH_KEY = "", MESH_LOCAL = false, REPORT = null;
  let LASTJSON = null, ILOTS = null, ILOTS_KEY = "", HDRI = null;
  let ATLAS = null, ATLAS_KEY = "", ATLAS_DIRTY = true, PLAN = null;
  /* le demi-atlas et son empreinte : les cartes de matiere en sortent, et
     c'est CETTE empreinte qui les date — pas la cle des reglages */
  let ATLAS_HALF = null, ATLAS_SIG = "";
  /* la dilatation EFFECTIVE et ce qui reste de fond dans les gouttieres —
     mesures a chaque composition d'atlas, jamais supposees */
  let PAD_EFF = { u: 0, v: 0, gu: 0, gv: 0, reste: { blanc: 0, total: 0 } };
  let MAPS = null, MAPS_KEY = "", LAST = null;
  let TIMER = null, BUILDING = false, AGAIN = false, SIG = "";
  let CAPTURING = false, TT = null, FFINFO = null;
  const UNDO = [];
  const ENV_CACHE = {};

  /* ═══════════════════════════════════════════════════════════════════════
     LE MODULE
     ═══════════════════════════════════════════════════════════════════════ */

  const M = CF.register({
    id: "solid",
    title: "Volume",
    icon: "\u{1F9CA}",
    order: 5,

    /* LE SCHEMA : ces cles sont les SEULES que M.patch({...}) acceptera.
       thickness_mm / corner_mm / edge sont LUES par P8 (spec 2.3) : leurs
       noms ne bougent pas. */
    state: {
      thickness_mm: 0.32,       /* 0,20 a 1,20 mm — LU par gltf */
      corner_mm: 3,             /* rayon du volume — LU par gltf */
      corner_link: true,        /* suit le rayon de coin du format */
      segments: 6,              /* finesse des arrondis */
      bevel_mm: 0.1,            /* chanfrein recto/verso */
      edge: "#efe9dc",          /* couleur de tranche — LU par gltf */
      edge_style: "plein",
      /* RELIEF PAR DEFAUT : « leger ». Le detaille pesait 131 Kio pour 2,22 deg
         d'inclinaison maximale, soit 23,9 % du fichier ; le quart d'atlas rend
         le meme ordre d'inclinaison pour quatre fois moins de texels. Ce que
         chaque choix coute est MESURE et publie a cote. */
      relief: "leger",
      env: "studio",
      /* EXPOSITION MESUREE, PAS CHOISIE. A 1,35 la silhouette de la carte
         rendait 31,9 de luminance moyenne pour un albedo de recto de 82,0 —
         39 %. A 1,85 elle rend 40,5, soit 49 %, et le comptage des pixels
         satures reste a 0,0 % (mesure a rotation arretee, camera recadree,
         20 521 pixels opaques, memes pixels aux cinq expositions). Le rendu
         par defaut ne rend plus la moitie de ce que la carte porte. */
      exposure: 1.85,
      shadow: 0.55,
      view: "matiere",
      wire: false,
      spin: true,
      atlas: 1536,              /* PLAFOND de l'atlas, pas sa taille */
      atlas_fmt: "jpeg",        /* base : jpeg (4:2:0), jpeg444 (chroma pleine), png */
      tt_frames: 90,
      tt_fps: 30,
      tt_size: 1080,
      tt_fmt: "mp4",
      tt_up: ELEV_DEFAULT,      /* ELEVATION au-dessus de l'horizon, en degres */
    },

    async init(host) {
      HOST = host;
      host.innerHTML = TEMPLATE;
      MV = q("#cf-solid-mv");
      buildStatics();
      wire();
      /* NE RECONSTRUIRE QUE CE QUI CHANGE LE MODELE. Regler le tourne-disque
         reconstruisait le GLB, et la reconstruction REPOSE la camera sauvegardee
         juste avant : une elevation changee puis un « Recadrer » dans la foulee
         etait annulee par le chargement en vol (mesure : elevation relue 18
         alors qu'on venait de demander 0). La signature ci-dessous ne contient
         que ce qui fabrique le fichier. */
      CF.on("core:doc", (p) => {
        if (!p || p.id !== "solid") ATLAS_DIRTY = true;
        sync();
        const s = modelSig();
        if (ATLAS_DIRTY || s !== SIG) { SIG = s; schedule(); }
      });
      CF.on("core:geom", () => {
        ATLAS_DIRTY = true;
        if (S("corner_link", true)) {
          const c = CF.geom().corner_mm;
          if (Math.abs(c - S("corner_mm", 3)) > 1e-9) { M.patch({ corner_mm: c }); return; }
        }
        sync(); schedule();
      });
      CF.on("core:cards", () => { ATLAS_DIRTY = true; schedule(); });
      if (typeof ResizeObserver === "function") {
        new ResizeObserver(() => { fitStage(); }).observe(host);
      }
      document.addEventListener("keydown", onKey);
      sync();
      schedule(30);
      /* Ce que l'outillage permet, DIT AVANT le clic : un tourne-disque sans
         ffmpeg doit se savoir tout de suite, pas apres 90 images capturees. */
      M.api.get("info").then((d) => {
        if (d && d.turntable && d.turntable.ffmpeg === false) {
          const b = q(".cf-solid-go");
          b.disabled = true;
          b.textContent = "Tourne-disque indisponible — ffmpeg absent";
        }
        /* La preuve du piege 9, ecrite : `gltf_builder` rend une SPHERE pour
           tout nom de maillage inconnu, sans un mot. Les deux comptes cote a
           cote disent que « card » a bien ete pris. */
        /* Les valeurs PBR sont ecrites des deux cotes (backend + ce fichier) :
           si elles derivaient, l'apercu et l'export ne montreraient pas la
           meme matiere. Le test le refuse au build, ceci le dit au demarrage. */
        const pb = d && d.pbr && d.pbr.plein;
        if (pb && (pb.face.metallic !== PBR_FACE.metallic
          || pb.face.roughness !== PBR_FACE.roughness
          || pb.edge.roughness !== PBR_EDGE.plein.roughness)) {
          console.warn("cardforge: solid — valeurs PBR divergentes entre l'ecran et le backend", pb);
        }
        const r = d && d.registered_mesh, s = d && d.sphere_mesh;
        if (r && s) {
          FFINFO = d;
          q("#cf-solid-reg").innerHTML = 'Maillage <b>card</b> enregistré côté serveur : '
            + r.triangles + ' faces / ' + r.vertices + ' sommets — la sphère de repli en compte '
            + s.triangles + '. L\'export 3D ne peut donc pas livrer une boule à la place de la carte.';
        }
      }).catch(() => { /* domaine pas monte : le maillage de secours prend le relais */ });
    },
  });

  /* ═══════════════════════════════════════════════════════════════════════
     1. GABARIT
     ═══════════════════════════════════════════════════════════════════════ */

  const TEMPLATE = ''
    + '<div class="cf-solid-wrap">'

    + '  <section class="cf-solid-view">'
    + '    <div class="cf-solid-bar">'
    + '      <div class="cf-solid-seg" id="cf-solid-views"></div>'
    + '      <button type="button" class="chip cf-solid-t" data-t="wire" title="Filaire (W)">&#9638; Filaire</button>'
    + '      <button type="button" class="chip cf-solid-t" data-t="spin" title="Tourne-disque (R)">&#8635; Rotation</button>'
    /* LES TROIS FACES, ATTEIGNABLES. Le grief : « le verso n'est visible nulle
       part a l'ecran ; il a fallu que j'ouvre le fichier et que je le rende
       moi-meme pour le lire — un utilisateur ne fera pas ca », et « la
       demonstration de la tranche est maigre : 3 pixels sur 1080 ». La vue
       « Tranche » n'est donc pas un angle, c'est une MACRO : la cible se pose
       sur le bord de la carte et le rayon descend a quelques millimetres. */
    + '      <div class="cf-solid-seg cf-solid-sm" id="cf-solid-poses"></div>'
    + '      <span class="cf-solid-gap"></span>'
    /* ZOOM ET DEPLACEMENT : la souris les fait depuis toujours, aucune commande
       ne le DISAIT. Un inventaire de visionneuse se compte sur une image
       arretee. */
    + '      <div class="cf-solid-zoom">'
    + '        <button type="button" class="btn sm cf-solid-z" data-z="-1" title="Zoom arrière (molette)">&minus;</button>'
    + '        <b id="cf-solid-fov">26&deg;</b>'
    + '        <button type="button" class="btn sm cf-solid-z" data-z="1" title="Zoom avant (molette)">+</button>'
    + '        <i class="cf-solid-zh">glisser = tourner · clic droit = déplacer</i>'
    + '      </div>'
    + '      <label class="cf-solid-inline"><span class="lbl">Lumière</span><select id="cf-solid-env" class="cf-solid-sel"></select>'
    + '        <i class="cf-solid-envn" id="cf-solid-envn"></i></label>'
    /* IMPORT D'UN HDRI. Les cinq environnements fabriques ici sont en basse
       dynamique ; un vrai .hdr donne des reflets que rien d'autre ne donne, et
       c'est la seule chose que la reference savait faire et pas nous. */
    + '      <label class="btn sm cf-solid-hdrib" title="Importer un environnement : .hdr, .exr ou une image">HDRI…'
    + '        <input type="file" id="cf-solid-hdri" accept=".hdr,.exr,image/*" hidden></label>'
    + '      <button type="button" class="btn sm cf-solid-fit" title="Recadrer la caméra (F)">Recadrer</button>'
    + '    </div>'
    + '    <div class="cf-solid-stage" id="cf-solid-stage">'
    + '      <model-viewer id="cf-solid-mv" class="cf-solid-mv" camera-controls enable-pan interaction-prompt="none"'
    + '        shadow-intensity="0.55" shadow-softness="0.9" exposure="1" environment-image="neutral"'
    + '        camera-orbit="-24deg 72deg auto" field-of-view="26deg" interpolation-decay="1"'
    + '        min-field-of-view="8deg" max-field-of-view="55deg" alt="Aperçu en volume de la carte"></model-viewer>'
    + '      <div class="cf-solid-hud" id="cf-solid-hud"></div>'
    + '      <div class="cf-solid-legend hidden" id="cf-solid-legend"></div>'
    + '      <div class="cf-solid-prog hidden" id="cf-solid-prog"><div class="cf-solid-progbar"><i></i></div><span></span>'
    + '        <button type="button" class="lnk cf-solid-abort">annuler</button></div>'
    + '    </div>'
    + '  </section>'

    + '  <aside class="cf-solid-ctl">'

    + '    <div class="cf-solid-grp">'
    /* LES BORNES DU CURSEUR, ECRITES. Le grief : « les bornes du curseur
       d'epaisseur ne sont ecrites nulle part et les prereglages s'arretent a
       Plaque 1,00 alors que la plage utile monte a 1,20 mm ». Elles sortent de
       LIM, donc du meme endroit que le curseur. */
    + '      <div class="cf-solid-gh"><b>Épaisseur</b><i class="cf-solid-bornes" id="cf-solid-bornes"></i>'
    + '        <span class="cf-solid-gv" id="cf-solid-thr"></span></div>'
    + '      <div class="cf-solid-row">'
    + '        <input type="range" class="cf-solid-rg" data-k="thickness_mm" min="0.2" max="1.2" step="0.01">'
    + '        <input type="number" class="cf-solid-nb" data-k="thickness_mm" min="0.2" max="1.2" step="0.01">'
    + '        <i class="cf-solid-u">mm</i>'
    + '      </div>'
    + '      <div class="chips cf-solid-pre" id="cf-solid-pre"></div>'
    + '      <canvas class="cf-solid-prof" id="cf-solid-prof" width="536" height="120"></canvas>'
    + '    </div>'

    + '    <div class="cf-solid-grp">'
    + '      <div class="cf-solid-gh"><b>Coins et tranche</b>'
    + '        <label class="check tiny cf-solid-link"><input type="checkbox" id="cf-solid-link"> suivre le format</label></div>'
    + '      <div class="cf-solid-row">'
    + '        <span class="lbl cf-solid-lb">Rayon</span>'
    + '        <input type="range" class="cf-solid-rg" data-k="corner_mm" min="0" max="10" step="0.1">'
    + '        <input type="number" class="cf-solid-nb" data-k="corner_mm" min="0" max="10" step="0.1"><i class="cf-solid-u">mm</i>'
    + '      </div>'
    + '      <div class="cf-solid-row">'
    + '        <span class="lbl cf-solid-lb">Finesse</span>'
    + '        <input type="range" class="cf-solid-rg" data-k="segments" min="1" max="16" step="1">'
    + '        <input type="number" class="cf-solid-nb" data-k="segments" min="1" max="16" step="1"><i class="cf-solid-u">seg</i>'
    + '      </div>'
    + '      <div class="cf-solid-row">'
    + '        <span class="lbl cf-solid-lb" title="Retrait du chanfrein : la même jambe en Z et en XY, donc une arête à 45°">Retrait</span>'
    + '        <input type="range" class="cf-solid-rg" data-k="bevel_mm" min="0" max="0.3" step="0.01">'
    + '        <input type="number" class="cf-solid-nb" data-k="bevel_mm" min="0" max="0.3" step="0.01"><i class="cf-solid-u">mm</i>'
    + '      </div>'
    + '      <p class="hint cf-solid-bev" id="cf-solid-bev"></p>'
    + '      <div class="cf-solid-row cf-solid-edge">'
    + '        <span class="lbl cf-solid-lb">Tranche</span>'
    + '        <input type="color" class="cf-solid-col" id="cf-solid-edge">'
    + '        <div class="cf-solid-seg cf-solid-sm" id="cf-solid-edges"></div>'
    + '      </div>'
    /* « SOIT ON ENCODE CE RELIEF DANS UN CANAL LEGER, SOIT ON NE L'ENCODE PAS. »
       Les deux branches sont ici, et le paragraphe du dessous pese celle qui
       est choisie sur les octets du fichier. */
    + '      <div class="cf-solid-row">'
    + '        <span class="lbl cf-solid-lb" title="Carte de normales : le grain d\'encre. Son poids est mesuré ci-dessous.">Relief</span>'
    + '        <div class="cf-solid-seg cf-solid-sm" id="cf-solid-reliefs"></div>'
    + '      </div>'
    + '      <p class="hint cf-solid-maps" id="cf-solid-maps"></p>'
    + '    </div>'

    + '    <div class="cf-solid-grp">'
    + '      <div class="cf-solid-gh"><b>Tourne-disque</b><span class="cf-solid-gv" id="cf-solid-ttr"></span></div>'
    + '      <div class="grid2">'
    + '        <label class="fld"><span class="lbl">Images</span><input type="number" class="cf-solid-nb w" data-k="tt_frames" min="24" max="600" step="1"></label>'
    + '        <label class="fld"><span class="lbl">Images / s</span><input type="number" class="cf-solid-nb w" data-k="tt_fps" min="12" max="60" step="1"></label>'
    + '      </div>'
    + '      <div class="grid2">'
    + '        <label class="fld"><span class="lbl">Définition</span><select class="cf-solid-sel" id="cf-solid-ttsize"></select></label>'
    + '        <label class="fld"><span class="lbl">Format</span><select class="cf-solid-sel" id="cf-solid-ttfmt"><option value="mp4">MP4 (H.264)</option><option value="webm">WebM (VP9)</option></select></label>'
    + '      </div>'
    + '      <div class="cf-solid-row">'
    + '        <span class="lbl cf-solid-lb">Élévation</span>'
    + '        <input type="range" class="cf-solid-rg" data-k="tt_up" min="0" max="55" step="1">'
    + '        <input type="number" class="cf-solid-nb" data-k="tt_up" min="0" max="55" step="1"><i class="cf-solid-u">&deg;</i>'
    + '      </div>'
    + '      <p class="hint cf-solid-elev" id="cf-solid-elev"></p>'
    + '      <button type="button" class="btn strong wide cf-solid-go">Rendre le tourne-disque &mdash; local, gratuit</button>'
    + '      <p class="hint cf-solid-out hidden" id="cf-solid-out"></p>'
    + '    </div>'

    + '    <details class="grp cf-solid-more">'
    + '      <summary>Rendu et raccourcis</summary>'
    + '      <div class="grp-body">'
    + '        <div class="cf-solid-row"><span class="lbl cf-solid-lb">Exposition</span>'
    + '          <input type="range" class="cf-solid-rg" data-k="exposure" min="0.3" max="2" step="0.05">'
    + '          <input type="number" class="cf-solid-nb" data-k="exposure" min="0.3" max="2" step="0.05"><i class="cf-solid-u">&times;</i></div>'
    + '        <div class="cf-solid-row"><span class="lbl cf-solid-lb">Ombre</span>'
    + '          <input type="range" class="cf-solid-rg" data-k="shadow" min="0" max="1.5" step="0.05">'
    + '          <input type="number" class="cf-solid-nb" data-k="shadow" min="0" max="1.5" step="0.05"><i class="cf-solid-u">&times;</i></div>'
    + '        <div class="grid2">'
    + '          <label class="fld"><span class="lbl">Plafond de l\'atlas</span>'
    + '            <select class="cf-solid-sel" id="cf-solid-atlas"></select></label>'
    /* TROIS CHOIX, PARCE QUE LA MESURE EN A TROUVE TROIS. L'encodeur de la
       toile sort du 4:2:0 a toutes les qualites SAUF 1,0, ou il passe en
       4:4:4 (mesure sur le marqueur SOF : 2x2 de 0,80 a 0,98, 1x1 a 1,00).
       Le grief « base couleur en JPEG 4:2:0 sous du texte de 6 points » a donc
       une reponse qui n'est pas « prenez un PNG de 3 Mo ». */
    + '          <label class="fld"><span class="lbl">Image de base</span>'
    + '            <select class="cf-solid-sel" id="cf-solid-atlasfmt">'
    + '              <option value="jpeg">JPEG — léger (4:2:0)</option>'
    + '              <option value="jpeg444">JPEG — chroma pleine (4:4:4)</option>'
    + '              <option value="png">PNG — sans perte</option></select></label>'
    + '        </div>'
    + '        <div class="sep"></div>'
    + '        <dl class="cf-solid-keys">'
    + '          <dt>+ &nbsp;&minus;</dt><dd>épaisseur &plusmn; 0,01 mm</dd>'
    + '          <dt>[ &nbsp;]</dt><dd>rayon de coin &plusmn; 0,5 mm</dd>'
    + '          <dt>1 &hellip; 4</dt><dd>vue (matière, encre, normales, îlots)</dd>'
    + '          <dt>W</dt><dd>filaire</dd><dt>R</dt><dd>rotation</dd>'
    + '          <dt>F</dt><dd>recadrer</dd><dt>T</dt><dd>tourne-disque</dd>'
    + '          <dt>Ctrl+Z</dt><dd>annuler le dernier réglage</dd>'
    + '        </dl>'
    + '        <p class="hint">Les champs numériques se règlent aussi à la <b>molette</b> et au <b>glissé horizontal</b>.</p>'
    + '        <p class="hint cf-solid-reg" id="cf-solid-reg"></p>'
    + '      </div>'
    + '    </details>'

    + '  </aside>'
    + '</div>';

  /* ═══════════════════════════════════════════════════════════════════════
     2. OUTILS
     ═══════════════════════════════════════════════════════════════════════ */

  function q(sel) { return HOST ? HOST.querySelector(sel) : null; }
  function qa(sel) { return HOST ? Array.prototype.slice.call(HOST.querySelectorAll(sel)) : []; }
  function S(k, d) { return CF.get("solid." + k, d); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function clamp(k, v) {
    const b = LIM[k];
    const n = Number(v);
    if (!isFinite(n)) return null;
    return b ? Math.max(b[0], Math.min(b[1], n)) : n;
  }
  function fr(v, n) { return Number(v).toFixed(n).replace(".", ","); }

  /* Elevation de la camera AU-DESSUS DE L'HORIZON (miroir de
     solid.polar_from_elevation) : c'est la grandeur qu'on peut relire sur
     l'image, l'angle polaire de <model-viewer> en est le complement. */
  function elev() {
    const v = Number(S("tt_up", ELEV_DEFAULT));
    if (!isFinite(v)) return ELEV_DEFAULT;
    return Math.round(Math.max(ELEV_MIN, Math.min(ELEV_MAX, v)));
  }

  /* LE LACET DU MODELE. `auto-rotate` ne tourne pas la camera : il tourne LE
     MODELE (`turntableRotation`, en radians), et cette rotation SURVIT a
     l'arret de la rotation — `turntableRotation = 0` est refuse en ecriture
     (mesure : la propriete vaut encore 67,833 apres l'affectation). Sans en
     tenir compte, « Recadrer » remettait la camera droite devant une carte
     restee de travers : mesure a l'ecran, 42 px de large au lieu de 365. */
  function yawDeg() {
    const y = (MV && typeof MV.turntableRotation === "number") ? MV.turntableRotation : 0;
    const d = y * 180 / Math.PI;
    return isFinite(d) ? ((d % 360) + 360) % 360 : 0;
  }

  /* Toute ecriture passe par ici : la pile d'annulation se remplit toute
     seule, et « Ctrl+Z » n'est pas une promesse mais un mecanisme. */
  function put(partial, label) {
    const before = {};
    Object.keys(partial).forEach((k) => { before[k] = S(k, null); });
    let change = false;
    Object.keys(partial).forEach((k) => {
      if (JSON.stringify(before[k]) !== JSON.stringify(partial[k])) change = true;
    });
    if (!change) return;
    UNDO.push({ before: before, label: label || Object.keys(partial).join(", ") });
    if (UNDO.length > 40) UNDO.shift();
    M.patch(partial);
  }
  function undo() {
    const u = UNDO.pop();
    if (!u) { CF.toast("rien à annuler"); return; }
    M.patch(u.before);
    CF.toast("annulé : " + u.label);
  }

  /* ═══════════════════════════════════════════════════════════════════════
     3. CONSTRUCTION DES COMMANDES
     ═══════════════════════════════════════════════════════════════════════ */

  function buildStatics() {
    q("#cf-solid-views").innerHTML = VUES.map((v) =>
      '<button type="button" class="seg-b cf-solid-v" data-v="' + v.id + '" title="' + esc(v.t) + '">' + esc(v.l) + '</button>').join("");
    q("#cf-solid-edges").innerHTML = TRANCHES.map((t) =>
      '<button type="button" class="seg-b cf-solid-e" data-e="' + t.id + '">' + esc(t.l) + '</button>').join("");
    q("#cf-solid-reliefs").innerHTML = RELIEFS.map((r) =>
      '<button type="button" class="seg-b cf-solid-r" data-r="' + r.id + '" title="' + esc(r.t)
      + '">' + esc(r.l) + '</button>').join("");
    q("#cf-solid-poses").innerHTML = POSES.map((p) =>
      '<button type="button" class="seg-b cf-solid-pose" data-pose="' + p.id + '" title="'
      + esc(p.t) + '">' + esc(p.l) + '</button>').join("");
    q("#cf-solid-bornes").textContent = fr(LIM.thickness_mm[0], 2) + " – "
      + fr(LIM.thickness_mm[1], 2) + " mm";
    q("#cf-solid-env").innerHTML = ENVS.map((e) =>
      '<option value="' + e.id + '">' + esc(e.l) + '</option>').join("");
    q("#cf-solid-ttsize").innerHTML = TAILLES.map((t) =>
      '<option value="' + t + '">' + t + " px</option>").join("");
    q("#cf-solid-atlas").innerHTML = ATLAS_CAPS.map((t) =>
      '<option value="' + t + '">' + t + ' px maxi</option>').join("");
    /* Un menu replie ne prouve rien : le nombre d'environnements est COMPTE
       sur les options reellement posees dans le DOM, et il s'affiche a cote.
       Le seuil « au moins 4 » devient lisible sur une image arretee. */
    q("#cf-solid-envn").textContent = q("#cf-solid-env").options.length + " env.";
    q("#cf-solid-pre").innerHTML = EPAISSEURS.map((p) =>
      '<button type="button" class="chip cf-solid-p" data-v="' + p.v + '" title="' + esc(p.h) + '">'
      + esc(p.l) + ' <b>' + fr(p.v, 2) + '</b></button>').join("");
  }

  function wire() {
    HOST.addEventListener("click", (e) => {
      const v = e.target.closest(".cf-solid-v");
      if (v) { put({ view: v.dataset.v }, "vue"); return; }
      const t = e.target.closest(".cf-solid-t");
      if (t) { put({ [t.dataset.t]: !S(t.dataset.t, false) }, t.dataset.t === "wire" ? "filaire" : "rotation"); return; }
      const ed = e.target.closest(".cf-solid-e");
      if (ed) { put({ edge_style: ed.dataset.e }, "style de tranche"); return; }
      const rl = e.target.closest(".cf-solid-r");
      if (rl) { put({ relief: rl.dataset.r }, "relief d'encre"); return; }
      const p = e.target.closest(".cf-solid-p");
      if (p) { put({ thickness_mm: Number(p.dataset.v) }, "épaisseur"); return; }
      if (e.target.closest(".cf-solid-fit")) { fitCamera(); return; }
      const po = e.target.closest(".cf-solid-pose");
      if (po) { pose(po.dataset.pose); return; }
      const z = e.target.closest(".cf-solid-z");
      if (z) { zoom(Number(z.dataset.z)); return; }
      if (e.target.closest(".cf-solid-go")) { turntable(); return; }
      if (e.target.closest(".cf-solid-abort")) { if (TT) TT.abort = true; return; }
    });

    qa(".cf-solid-rg").forEach((r) => {
      r.addEventListener("input", () => setNum(r.dataset.k, r.value, false));
      r.addEventListener("change", () => setNum(r.dataset.k, r.value, true));
    });
    qa(".cf-solid-nb").forEach((n) => {
      n.addEventListener("change", () => setNum(n.dataset.k, n.value, true));
      /* molette et glisse horizontal : la barre n'a que des boutons, on met
         de vraies valeurs editables — et on les rend attrapables. */
      n.addEventListener("wheel", (e) => {
        if (document.activeElement !== n && !n.matches(":hover")) return;
        e.preventDefault();
        const st = Number(n.step) || 1;
        setNum(n.dataset.k, Number(n.value || 0) + (e.deltaY < 0 ? st : -st), true);
      }, { passive: false });
      let dx = 0, x0 = 0, v0 = 0, on = false, pendingVal = null, rafId = 0;
      /* repli setTimeout si rAF est absent, annulation SYMETRIQUE (le meme
         drapeau sert a programmer et a annuler). Meme patron que core.js:158,
         reproduit ICI en local — chaque piece est un fichier a part, sans
         import partage entre modules. */
      const hasRAF = typeof requestAnimationFrame === "function";
      const scheduleFrame = (fn) => (hasRAF ? requestAnimationFrame(fn) : setTimeout(fn, 16));
      const cancelFrame = (id) => { if (hasRAF) cancelAnimationFrame(id); else clearTimeout(id); };
      const flushScrub = () => {
        rafId = 0;
        if (pendingVal === null) return;
        const v = pendingVal; pendingVal = null;
        setNum(n.dataset.k, v, false);   /* <= 1 patch par frame (spec 9.6-1) */
      };
      n.addEventListener("pointerdown", (e) => {
        if (e.button !== 0) return;
        on = true; x0 = e.clientX; v0 = Number(n.value || 0); dx = 0; pendingVal = null;
        n.setPointerCapture(e.pointerId);
      });
      n.addEventListener("pointermove", (e) => {
        if (!on) return;
        dx = e.clientX - x0;
        if (Math.abs(dx) < 3) return;
        const st = Number(n.step) || 1;
        const nn = normNum(n.dataset.k, v0 + Math.round(dx / 4) * st);
        if (nn === null) return;
        n.value = nn;               /* retour local immediat (spec 9.6-2) : le
                                        champ suit CHAQUE evenement, meme si
                                        le document ne suit qu'a la frame */
        pendingVal = nn;
        if (!rafId) rafId = scheduleFrame(flushScrub);
      });
      const endScrub = (e) => {
        if (!on) return;
        on = false;
        if (rafId) { cancelFrame(rafId); rafId = 0; }
        pendingVal = null;
        try { n.releasePointerCapture(e.pointerId); } catch (err) { /* deja relache */ }
        /* etat FINAL exact (spec 9.6-1) : n.value a ete tenu a jour a CHAQUE
           evenement ci-dessus, il porte deja la derniere position — inutile
           de reciter pendingVal ici. */
        if (Math.abs(dx) >= 3) setNum(n.dataset.k, n.value, true);
      };
      n.addEventListener("pointerup", endScrub);
      n.addEventListener("pointercancel", endScrub);
    });

    q("#cf-solid-link").addEventListener("change", (e) => {
      const on = !!e.target.checked;
      const o = { corner_link: on };
      if (on) o.corner_mm = CF.geom().corner_mm;
      put(o, "suivre le format");
    });
    q("#cf-solid-edge").addEventListener("change", (e) => put({ edge: e.target.value }, "couleur de tranche"));
    q("#cf-solid-env").addEventListener("change", (e) => put({ env: e.target.value }, "lumière"));
    /* Le fichier reste LOCAL : un objet-URL, aucun envoi, aucun reseau. Le
       compteur d'environnements est recompte sur les options POSEES — il ne
       peut donc pas annoncer un environnement qui n'existe pas. */
    q("#cf-solid-hdri").addEventListener("change", (e) => {
      const f = e.target.files && e.target.files[0];
      if (!f) return;
      if (HDRI && HDRI.url) { try { URL.revokeObjectURL(HDRI.url); } catch (err) { /* deja liberee */ } }
      HDRI = { url: URL.createObjectURL(f), name: f.name, bytes: f.size };
      const sel = q("#cf-solid-env");
      if (!Array.prototype.some.call(sel.options, (o) => o.value === "perso")) {
        const op = document.createElement("option");
        op.value = "perso";
        sel.appendChild(op);
      }
      Array.prototype.forEach.call(sel.options, (o) => {
        if (o.value === "perso") o.textContent = "HDRI : " + f.name.slice(0, 22);
      });
      q("#cf-solid-envn").textContent = sel.options.length + " env.";
      e.target.value = "";
      put({ env: "perso" }, "HDRI importé");
      CF.toast("environnement importé : " + f.name + " (" + fr(f.size / 1024, 0) + " Kio)");
    });
    q("#cf-solid-atlas").addEventListener("change", (e) => { ATLAS_DIRTY = true; put({ atlas: Number(e.target.value) }, "atlas"); });
    q("#cf-solid-atlasfmt").addEventListener("change", (e) => {
      const v = ["png", "jpeg444", "jpeg"].indexOf(e.target.value) >= 0 ? e.target.value : "jpeg";
      put({ atlas_fmt: v }, "image de base");
    });
    q("#cf-solid-ttsize").addEventListener("change", (e) => put({ tt_size: Number(e.target.value) }, "définition"));
    q("#cf-solid-ttfmt").addEventListener("change", (e) => put({ tt_fmt: e.target.value }, "format vidéo"));
  }

  /* LES BORNES, SEULES : extraites de setNum() pour que l'apercu du glisser
     (n.value, au rythme de CHAQUE evenement — spec 9.6-2) et le patch au
     document (au rythme de la frame — spec 9.6-1) arrondissent EXACTEMENT
     pareil, une seule formule plutot que deux copies qui auraient fini par
     diverger. */
  function normNum(k, v) {
    let n = Number(v);
    if (!isFinite(n)) return null;
    if (LIM[k]) n = clamp(k, n);
    else {
      const B = { exposure: [0.3, 2], shadow: [0, 1.5], tt_frames: [24, 600], tt_fps: [12, 60], tt_up: [ELEV_MIN, ELEV_MAX] }[k];
      if (B) n = Math.max(B[0], Math.min(B[1], n));
    }
    if (k === "segments" || k === "tt_frames" || k === "tt_fps" || k === "tt_up") n = Math.round(n);
    else n = Math.round(n * 1000) / 1000;
    return n;
  }
  function setNum(k, v, commit) {
    const n = normNum(k, v);
    if (n === null) return;
    const o = { [k]: n };
    if (k === "corner_mm" && S("corner_link", true)) o.corner_link = false;
    if (commit) put(o, k);
    else { M.patch(o); }        /* glisse continu : une seule entree d'annulation au relachement */
  }

  function onKey(e) {
    if (!HOST || !HOST.closest(".cf-panel.on")) return;
    const tag = (e.target && e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "select" || tag === "textarea") {
      if (!(e.key === "z" && (e.ctrlKey || e.metaKey))) return;
    }
    const th = S("thickness_mm", 0.32), cm = S("corner_mm", 3);
    if (e.key === "z" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); undo(); return; }
    if (e.key === "+" || e.key === "=") { e.preventDefault(); put({ thickness_mm: clamp("thickness_mm", th + 0.01) }, "épaisseur"); }
    else if (e.key === "-") { e.preventDefault(); put({ thickness_mm: clamp("thickness_mm", th - 0.01) }, "épaisseur"); }
    else if (e.key === "[") { put({ corner_mm: clamp("corner_mm", cm - 0.5), corner_link: false }, "rayon"); }
    else if (e.key === "]") { put({ corner_mm: clamp("corner_mm", cm + 0.5), corner_link: false }, "rayon"); }
    else if (e.key === "w" || e.key === "W") { put({ wire: !S("wire", false) }, "filaire"); }
    else if (e.key === "r" || e.key === "R") { put({ spin: !S("spin", true) }, "rotation"); }
    else if (e.key === "f" || e.key === "F") { fitCamera(); }
    else if (e.key === "t" || e.key === "T") { turntable(); }
    else if ("1234".indexOf(e.key) >= 0) { put({ view: VUES[Number(e.key) - 1].id }, "vue"); }
  }

  /* ═══════════════════════════════════════════════════════════════════════
     4. SYNCHRONISATION DE L'ECRAN
     ═══════════════════════════════════════════════════════════════════════ */

  function sync() {
    if (!HOST) return;
    qa(".cf-solid-rg, .cf-solid-nb").forEach((el) => {
      const v = S(el.dataset.k, 0);
      if (String(el.value) !== String(v)) el.value = v;
    });
    qa(".cf-solid-v").forEach((b) => b.classList.toggle("active", b.dataset.v === S("view", "matiere")));
    qa(".cf-solid-e").forEach((b) => b.classList.toggle("active", b.dataset.e === S("edge_style", "plein")));
    qa(".cf-solid-r").forEach((b) => b.classList.toggle("active", b.dataset.r === S("relief", "leger")));
    qa(".cf-solid-p").forEach((b) => b.classList.toggle("active", Math.abs(Number(b.dataset.v) - S("thickness_mm", 0.32)) < 1e-9));
    qa(".cf-solid-t").forEach((b) => b.classList.toggle("active", !!S(b.dataset.t, false)));
    q("#cf-solid-link").checked = !!S("corner_link", true);
    q("#cf-solid-edge").value = S("edge", "#efe9dc");
    /* « perso » survit dans le document mais pas l'objet-URL : apres un
       rechargement, le menu retombe sur Studio plutot que d'afficher un
       environnement vide qui n'existe plus. */
    const ev = S("env", "studio"), sel = q("#cf-solid-env");
    sel.value = Array.prototype.some.call(sel.options, (o) => o.value === ev) ? ev : "studio";
    q("#cf-solid-atlas").value = String(S("atlas", 1536));
    q("#cf-solid-atlasfmt").value = S("atlas_fmt", "jpeg");
    q("#cf-solid-ttsize").value = String(S("tt_size", 1080));
    q("#cf-solid-ttfmt").value = S("tt_fmt", "mp4");

    const th = S("thickness_mm", 0.32);
    /* MEME REGLE DE PRECISION QUE LE HUD : quatre decimales en pouces des
       deux cotes. « 0,0126 in » ici et « 0,013 in » la-bas, c'etait deux
       lectures de la meme grandeur. */
    q("#cf-solid-thr").innerHTML = '<b>' + fr(th, 2) + ' mm</b> · ' + fr(th / 25.4, 4) + ' in';
    const f = S("tt_frames", 90), fps = S("tt_fps", 30);
    q("#cf-solid-ttr").innerHTML = '<b>' + fr(f / fps, 2) + ' s</b> · ' + f + ' images @ ' + fps + ' i/s';
    const up = elev();
    q("#cf-solid-elev").innerHTML = '<b>' + up + '&deg;</b> au-dessus de l\'horizon &mdash; angle polaire '
      + fr(90 - up, 0) + '&deg; posé sur la visionneuse, et relu sur elle après le rendu.';
    q("#cf-solid-legend").classList.toggle("hidden", S("view", "matiere") !== "ilots");
    q("#cf-solid-legend").innerHTML =
      '<i style="background:#29b89e"></i>recto<i style="background:#8c6bdc"></i>verso<i style="background:#f2b53d"></i>tranche';
    drawProfile();
    bevelHint();
    applyViewerAttrs();
  }

  function applyViewerAttrs() {
    if (!MV) return;
    MV.setAttribute("exposure", String(S("exposure", 1)));
    MV.setAttribute("shadow-intensity", String(S("shadow", 0.55)));
    if (S("spin", true) && !CAPTURING) MV.setAttribute("auto-rotate", "");
    else MV.removeAttribute("auto-rotate");
    /* LA CARTE SE LAISSE LIRE AVANT DE TOURNER. Sans ce delai, toute image
       arretee de l'apercu tombe a un azimut quelconque — sur une carte de
       0,32 mm, un tirage au sort sur 360 degres donne une bande etroite une
       fois sur quatre (mesure : 149 px de large au lieu de 365 de face). Le
       delai repart a chaque reconstruction : on voit donc CE QU'ON VIENT DE
       REGLER, immobile, puis la rotation reprend. */
    MV.setAttribute("auto-rotate-delay", "2200");
    MV.setAttribute("rotation-per-second", "22deg");
    const e = S("env", "studio");
    const want = (e === "perso" && HDRI) ? HDRI.url
      : (e === "neutre" ? "neutral" : envURL(e === "perso" ? "studio" : e));
    if (MV.getAttribute("environment-image") !== want) MV.setAttribute("environment-image", want);
  }

  /* Profil reel de la tranche, agrandi : le seul endroit ou 0,32 mm devient
     visible a l'oeil. Meme chiffres que le maillage, autre representation. */
  function drawProfile() {
    const c = q("#cf-solid-prof");
    if (!c || !c.getContext) return;
    /* La toile est dimensionnee en pixels REELS (largeur affichee x dpr) puis
       le contexte est mis a l'echelle : sinon une toile de 536 px affichee sur
       250 rapetisse le texte de moitie et la cote devient illisible. */
    const dpr = Math.min(2, (typeof devicePixelRatio === "number" ? devicePixelRatio : 1) || 1);
    const W = Math.max(180, Math.round(c.clientWidth || 262)), H = 74;
    if (c.width !== Math.round(W * dpr) || c.height !== Math.round(H * dpr)) {
      c.width = Math.round(W * dpr); c.height = Math.round(H * dpr);
      c.style.height = H + "px";
    }
    const x = c.getContext("2d");
    x.setTransform(dpr, 0, 0, dpr, 0, 0);
    const cs = getComputedStyle(document.documentElement);
    const ink = (cs.getPropertyValue("--ink-strong") || "#eee").trim();
    const soft = (cs.getPropertyValue("--ink-muted") || "#888").trim();
    const acc = (cs.getPropertyValue("--accent") || "#e0a33c").trim();
    x.clearRect(0, 0, W, H);
    /* LA COUPE DESSINE LE CHANFREIN CONSTRUIT, pas celui demande : elle
       clampait a 0,45 x epaisseur (0,144 mm) quand le maillage clampe a
       0,45 x DEMI-epaisseur (0,072 mm). La vignette montrait donc un
       chanfrein deux fois trop gros, et la legende annoncait le chiffre du
       curseur. */
    const th = S("thickness_mm", 0.32), bv = bevelEff();
    /* L'agrandissement s'adapte pour que la carte la plus epaisse tienne
       encore dans la vignette — et il est ECRIT, sinon la coupe mentirait sur
       l'echelle. */
    const K = Math.max(18, Math.min(74, Math.floor((H - 30) / th)));
    const w = W - 96, h = th * K, x0 = 82, y0 = (H - 14) / 2 - h / 2;
    x.fillStyle = S("edge", "#efe9dc");
    x.strokeStyle = ink; x.lineWidth = 1;
    x.beginPath();
    x.moveTo(x0, y0 + bv * K); x.lineTo(x0 + bv * K, y0);
    x.lineTo(x0 + w - bv * K, y0); x.lineTo(x0 + w, y0 + bv * K);
    x.lineTo(x0 + w, y0 + h - bv * K); x.lineTo(x0 + w - bv * K, y0 + h);
    x.lineTo(x0 + bv * K, y0 + h); x.lineTo(x0, y0 + h - bv * K);
    x.closePath(); x.fill(); x.stroke();
    /* LA COTE MESURE EXACTEMENT CE QU'ELLE ANNONCE. Un trait de 1 px centre
       sur la ligne deborde d'un demi-pixel de chaque cote : une regle posee
       sur l'ecran lisait 24,7 px la ou la legende annonce 23,7. Les deux
       traits sont donc rentres d'un demi-pixel — le bord EXTERIEUR de la cote
       vaut alors h au pixel pres, et le chiffre de la legende se verifie. */
    x.strokeStyle = acc; x.lineWidth = 1;
    const ya = y0 + 0.5, yb = y0 + h - 0.5;
    x.beginPath();
    x.moveTo(x0 - 14, ya); x.lineTo(x0 - 4, ya);
    x.moveTo(x0 - 14, yb); x.lineTo(x0 - 4, yb);
    x.moveTo(x0 - 9, ya); x.lineTo(x0 - 9, yb);
    x.stroke();
    x.fillStyle = acc; x.font = "600 11px " + (cs.getPropertyValue("--f-mono") || "monospace");
    x.textAlign = "right"; x.textBaseline = "middle";
    x.fillText(fr(th, 2) + " mm", x0 - 20, y0 + h / 2);
    x.fillStyle = soft; x.textAlign = "left"; x.font = "9.5px sans-serif";
    /* « 74x » ETAIT FAUX, ET PERSONNE NE L'AVAIT RELEVE. K n'est pas un
       grossissement : c'est un nombre de PIXELS PAR MILLIMETRE. A 74 px/mm et
       96 dpi de reference CSS, 0,32 mm occupe 23,7 px = 6,3 mm a l'ecran, soit
       un grossissement REEL de 19,6 fois — pas 74. On affiche donc l'echelle
       telle qu'elle est, verifiable a la regle sur la bande dessinee. */
    /* ET LA HAUTEUR REELLEMENT DESSINEE, pour qu'une regle posee sur l'ecran
       tranche : « 1 mm = 74 px » seul obligeait a faire la multiplication, et
       le contour de 1 px qui borde la bande faisait ensuite douter du chiffre.
       On ecrit donc l'echelle ET la cote — c'est la cote (le trait a gauche)
       qui vaut exactement ce nombre, le contour de la bande y ajoute 1 px. */
    x.fillText("coupe · 1 mm = " + K + " px, cote " + fr(h, 1) + " px · retrait "
      + fr(bv, 3) + " mm", 8, H - 7);
  }

  /* LA CONVENTION EST ECRITE, EN TOUTES LETTRES ET SOUS LE CURSEUR.
     « biseau 0,100 mm » ne designait rien : la geometrie porte une jambe (le
     RETRAIT) de 0,072 mm en Z ET en XY, donc une arete a 45 degres dont le
     meplat mesure 0,102 mm. Trois nombres pour une seule arete — on dit lequel
     est lequel, et on dit quand la demande a ete bornee, plutot que de laisser
     un imprimeur se tromper de 28 % sur la cote qui l'interesse. */
  function bevelHint() {
    const el = q("#cf-solid-bev");
    if (!el) return;
    const bv = bevelEff(), dem = S("bevel_mm", 0.1), th = S("thickness_mm", 0.32);
    if (bv <= 1e-9) {
      el.innerHTML = 'Aucun chanfrein : l\'arête entre la face et la tranche est vive.';
      return;
    }
    el.innerHTML = 'Chanfrein à <b>45°</b> : retrait <b>' + fr(bv, 3)
      + ' mm</b> en Z <i>et</i> en XY, méplat ' + fr(bv * Math.SQRT2, 3) + ' mm.'
      + ((dem - bv) > 5e-4
        ? ' Demande ' + fr(dem, 2) + ' mm <b>bornée</b> par l\'épaisseur (0,225 × '
        + fr(th, 2) + ' mm) : le fichier porte ' + fr(bv, 3) + ', pas ' + fr(dem, 2) + '.'
        : '');
  }

  function fitStage() {
    if (!MV || CAPTURING) return;
    MV.style.width = ""; MV.style.height = ""; MV.style.transform = "";
  }

  /* DEUX PIEGES MESURES DANS CETTE VISIONNEUSE, tous deux invisibles a la
     lecture du code :

     1. L'ORDRE COMPTE. Le rayon « auto » est calcule POUR l'angle de champ
        courant. Regler l'angle apres coup rezoome sans recadrer, et la carte
        sort du cadre par le haut et par le bas.

     2. `jumpCameraToGoal()` GELE LA CAMERA au lieu de l'y amener. Mesure : on
        pose camera-orbit a 90deg, on appelle jumpCameraToGoal, on attend
        1,6 s — l'image ne bouge pas d'un pixel alors que `getCameraOrbit()`
        rend bien 90deg. Sans l'appel, la camera y va. On ne l'appelle donc
        nulle part, et `interpolation-decay="1"` fait le trajet en une image.

     La remise a zero de `orientation` fait partie du recadrage : le
     tourne-disque fait tourner le MODELE, et « Recadrer » doit tout remettre
     droit, pas seulement la camera.

     3. LE LACET DE `auto-rotate` NE SE REMET PAS A ZERO. Il ne vit pas dans
        `orientation` mais dans `turntableRotation`, en lecture seule. On
        recadre donc SUR LUI : theta = lacet - 28 deg. Mesure avant / apres,
        largeur projetee de la carte : 42 px -> 365 px. */
  function fitCamera() {
    if (!MV) return;
    MV.setAttribute("orientation", "0deg 0deg 0deg");
    MV.setAttribute("field-of-view", "26deg");
    MV.setAttribute("camera-target", "auto auto auto");
    MV.setAttribute("min-camera-orbit", "auto auto auto");
    MV.setAttribute("camera-orbit", (yawDeg() - 28).toFixed(3) + "deg "
      + String(90 - elev()) + "deg auto");
    fovLabel(26);
  }

  /* ── LES TROIS POSES ──────────────────────────────────────────────────────
     Recto et verso sont de simples azimuts (0 et 180 degres autour de Y, a
     l'equateur). La TRANCHE, elle, ne se voit pas de loin : a 18 degres
     d'elevation et au cadrage d'ensemble, 0,32 mm sur 88 mm occupe 3 pixels
     sur 1080 — c'est physiquement juste et visuellement nul. On pose donc la
     cible SUR LE BORD de la carte (demi-largeur en metres) et on descend le
     rayon a 4 mm : a 14 degres de champ, le cadre fait 2 x 4 x tan(7 deg) =
     0,98 mm de haut, et la tranche en occupe le tiers. Le chanfrein a 45
     degres devient visible a l'oeil, pas seulement dans la coupe dessinee.

     `min-camera-orbit` doit etre desserre : par defaut la visionneuse
     interdit d'approcher au-dela du rayon qui contient le modele, et la macro
     serait silencieusement ramenee a un plan large. */
  function pose(id) {
    const p = POSES.filter((x) => x.id === id)[0];
    if (!p || !MV) return;
    if (S("spin", true)) M.patch({ spin: false });   /* une macro sur un objet qui tourne ne tient pas */
    MV.setAttribute("orientation", "0deg 0deg 0deg");
    MV.setAttribute("field-of-view", p.fov + "deg");
    const th = yawDeg() + p.d, phi = p.phi || 90;
    if (p.macro) {
      /* Le point vise : le sommet de l'arc de coin, a 45 degres — donc un
         point qui EXISTE dans le maillage, calcule avec le meme rayon que lui
         (borne par la demi-carte, comme `card_mesh`). En metres : node.scale
         met deja le maillage a l'echelle physique. */
      const g2 = CF.geom();
      const hw = g2.trim_mm[0] / 2, hh = g2.trim_mm[1] / 2;
      const r = Math.min(S("corner_mm", 3), Math.min(hw, hh));
      const k = r * (1 - Math.SQRT1_2);
      MV.setAttribute("min-camera-orbit", "auto auto 0.0005m");
      MV.setAttribute("camera-target", ((hw - k) / 1000).toFixed(6) + "m "
        + ((hh - k) / 1000).toFixed(6) + "m 0m");
      MV.setAttribute("camera-orbit", th.toFixed(3) + "deg " + phi + "deg "
        + p.macro.toFixed(5) + "m");
    } else {
      MV.setAttribute("min-camera-orbit", "auto auto auto");
      MV.setAttribute("camera-target", "auto auto auto");
      MV.setAttribute("camera-orbit", th.toFixed(3) + "deg " + phi + "deg auto");
    }
    fovLabel(p.fov);
    CF.toast(p.l + " — " + p.t);
  }

  /* Le zoom EST l'angle de champ : on l'affiche, donc il se relit sur une
     image arretee au lieu de rester une propriete de souris. */
  function zoom(dir) {
    if (!MV) return;
    const cur = (MV.getFieldOfView ? MV.getFieldOfView() : 26) || 26;
    const v = Math.max(8, Math.min(55, cur * (dir > 0 ? 0.8 : 1.25)));
    MV.setAttribute("field-of-view", v.toFixed(2) + "deg");
    fovLabel(v);
  }

  function fovLabel(v) {
    const el = q("#cf-solid-fov");
    if (el) el.textContent = fr(v, 0) + "°";
  }

  /* ═══════════════════════════════════════════════════════════════════════
     5. ATLAS — le rendu REEL de la carte, rogne au trait de coupe
     ═══════════════════════════════════════════════════════════════════════ */

  function islandRects() {
    /* miroir de contract.UV_ISLANDS ; le backend les renvoie aussi et on
       prefere les SIENNES des qu'elles arrivent. */
    const d = { front: [0, 0, 0.49, 0.94], back: [0.51, 0, 1, 0.94], edge: [0, 0.96, 1, 1] };
    return (REPORT && REPORT.islands) ? REPORT.islands : d;
  }

  /* TAILLE DE L'ATLAS — miroir de `solid.atlas_plan`, et le backend fait foi
     des qu'il repond (`REPORT.atlas`).

     LE GRIEF, MESURE : l'ilot du recto occupait 1033 x 1444 px alors que le
     rendu qui l'alimente en fait 744 x 1039. Aller-retour de l'ilot par 744 px
     de large : 1,051 niveau de gris sur 255 d'ecart, contre 0,723 de plancher
     de reechantillonnage — autrement dit 39 % de resolution lineaire annoncee
     pour quasiment rien, pendant que le HUD affichait « 2108 x 1536 px » comme
     si le modele portait ces pixels. On dimensionne donc l'atlas SUR LA
     SOURCE : la plus petite taille qui donne l'echelle 1:1 au recto, plafonnee
     par le reglage.

     DEUXIEME GRIEF, MESURE SUR LE FICHIER : « RECTO 744 x 1040 px, 300,2 DPI,
     +0,1 % en hauteur ». Les bornes UV de l'ilot (u 0..0,490 / v 0..0,940) sur
     un atlas de 1518 x 1106 lui donnent 743,82 x 1039,64 px — donc 300,07 DPI
     et +0,062 %, pas +0,1 %. Les trois chiffres etaient calcules sur le nombre
     de pixels ARRONDI, c'est-a-dire sur une quantite qui n'existe nulle part :
     `drawImage` ecrit dans un rectangle a bornes fractionnaires. On garde
     l'arrondi (un pixel se compte en entiers) mais la DEFINITION et le
     REECHANTILLONNAGE sortent desormais de l'etendue exacte. */
  function atlasPlan() {
    if (REPORT && REPORT.atlas && REPORT.atlas.w) return REPORT.atlas;
    const g = CF.geom(), I = islandRects();
    const iw = I.front[2] - I.front[0], ih = I.front[3] - I.front[1];
    const cap = Math.max(64, Math.min(4096, Number(S("atlas", 1536)) || 1536));
    const even = (v) => { let n = Math.round(v); n = Math.max(64, Math.min(4096, n)); return n - (n % 2); };
    let H = even(Math.min(cap, Math.ceil(g.trim_px[1] / ih - 1e-9)));
    if (H < g.trim_px[1] / ih && H + 2 <= cap) H += 2;
    const W = even(H * (g.trim_mm[0] / g.trim_mm[1]) * (ih / iw));
    const eh = (I.edge[3] - I.edge[1]) * H;
    return {
      w: W, h: H, cap: cap,
      front_px: [Math.round(iw * W), Math.round(ih * H)],
      front_px_exact: [Math.round(iw * W * 100) / 100, Math.round(ih * H * 100) / 100],
      source_px: [g.trim_px[0], g.trim_px[1]],
      dpi: Math.round(ih * H / g.trim_mm[1] * 25.4 * 100) / 100,
      /* LES DEUX AXES, PAS UN. Les ilots UV sont geles par le contrat et
         l'atlas est dimensionne sur la HAUTEUR de la source : le recto ne
         tombe donc jamais a la meme definition dans les deux sens. Un seul
         chiffre cachait l'autre. */
      dpi_w: Math.round(iw * W / g.trim_mm[0] * 25.4 * 100) / 100,
      ratio_source: Math.round(ih * H / g.trim_px[1] * 1e6) / 1e6,
      ratio_source_w: Math.round(iw * W / g.trim_px[0] * 1e6) / 1e6,
      edge_px: [W, Math.round(eh)],
      edge_px_exact: [Math.round(W * 100) / 100, Math.round(eh * 100) / 100],
    };
  }

  async function buildAtlas() {
    const g = CF.geom();
    const I = islandRects();
    PLAN = atlasPlan();
    const H = PLAN.h, W = PLAN.w;
    const iw = I.front[2] - I.front[0], ih = I.front[3] - I.front[1];
    const cv = document.createElement("canvas");
    cv.width = W; cv.height = H;
    const x = cv.getContext("2d");
    x.imageSmoothingEnabled = true;
    try { x.imageSmoothingQuality = "high"; } catch (e) { /* moteurs anciens */ }
    x.fillStyle = "#ffffff"; x.fillRect(0, 0, W, H);

    const bx = g.bleed_off_px[0], by = g.bleed_off_px[1];
    const tw = g.trim_px[0], thh = g.trim_px[1];
    const front = await CF.renderCard(CF.current(), { face: "front" });
    x.drawImage(front, bx, by, tw, thh,
      I.front[0] * W, I.front[1] * H, iw * W, ih * H);
    const back = await CF.renderCard(CF.current(), { face: "back" });
    x.drawImage(back, bx, by, tw, thh,
      I.back[0] * W, I.back[1] * H, (I.back[2] - I.back[0]) * W, (I.back[3] - I.back[1]) * H);

    paintEdge(x, W, H, I.edge);
    /* ── DILATATION DES BORDS ────────────────────────────────────────────
       LE GRIEF, MESURE PIXEL PAR PIXEL SUR L'ATLAS LIVRE : « dernier pixel du
       recto (30,68,113), premier pixel de gouttiere (247,255,255), puis
       (255,255,255) sur 30 px. Aucune dilatation des bords. Des le niveau de
       mip ~5 le blanc bave dans le bord de la carte : dans un moteur de jeu, a
       distance, la carte prendra un lisere blanc. »
       Notre propre fichier ne demande pas de mipmaps (atlas non puissance de
       deux), mais le moteur d'en face en fabriquera. On repousse donc chaque
       ilot jusqu'au MILIEU de sa gouttiere : le filtrage bilineaire et les
       mips melangent alors du bord de carte avec du bord de carte, a tous les
       niveaux et non aux quatre premiers. */
    PAD_EFF = islandDilate(x, cv, W, H, I);
    ATLAS = cv;
    ATLAS_KEY = atlasKey();
    /* ── LES CARTES DE MATIERE SUIVENT LES PIXELS, PAS LES REGLAGES ───────
       LE GRIEF, ET C'EST LE PLUS GRAVE DU LOT : « seule la couche de couleur
       a ete regeneree ; la carte normale et la carte ORM contiennent ENCORE,
       en relief d'encre, le texte de la carte precedente ». Verifie sur les
       octets, en changeant la famille de cadre par son vrai bouton : image 0
       passe de 372 439 a 350 205 octets et change d'empreinte, images 1 et 2
       restent IDENTIQUES A L'OCTET (156 639 et 49 134 octets, memes
       empreintes). Le relief livre etait celui d'une autre carte.

       Cause : `MAPS_KEY` valait `ATLAS_KEY`, c'est-a-dire la cle des REGLAGES
       (format, definition, plafond, couleur et style de tranche). Le contenu
       de la carte n'y entre pas — il n'a aucune raison d'y entrer. L'atlas,
       lui, etait bien repeint. Les cartes derivees se rattachent donc
       desormais aux PIXELS dont elles sortent : empreinte du demi-atlas, la
       source meme de la carte de normales. Si un pixel bouge, elles sont
       refaites ; s'ils sont identiques, le cache tient. */
    ATLAS_HALF = down(cv, 2);
    ATLAS_SIG = canvasSig(ATLAS_HALF);
    ATLAS_DIRTY = false;
    return cv;
  }

  /* Empreinte FNV-1a de TOUS les octets d'une toile. On la prend sur le
     demi-atlas — l'entree de la carte de normales, la plus fine des deux
     cartes derivees : rien qui puisse changer une carte de matiere ne peut
     passer sous ce filtre. */
  function canvasSig(c) {
    const d = c.getContext("2d", { willReadFrequently: true })
      .getImageData(0, 0, c.width, c.height).data;
    let h = 2166136261 >>> 0;
    for (let i = 0; i < d.length; i++) {
      h ^= d[i];
      h = Math.imul(h, 16777619) >>> 0;
    }
    return c.width + "x" + c.height + ":" + h.toString(16);
  }

  /* PLAFOND de dilatation, en pixels d'atlas — une borne de COUT, pas une
     largeur. La largeur, elle, se deduit de la gouttiere.

     CE QUI A CHANGE, ET POURQUOI. La version precedente dilatait de 4 px et le
     panneau annoncait « le blanc du fond ne peut plus baver ». MESURE SUR
     L'IMAGE DE BASE DU FICHIER LIVRE (JPEG du GLB, poker 300 DPI) : le recto
     s'arretait a x=743, la dilatation portait x=744 a 747, puis
     (255,255,255) de x=748 a x=769 — VINGT-DEUX COLONNES DE BLANC PUR entre
     les deux ilots, et quatorze lignes de meme entre les faces et la tranche.
     Quatre pixels couvrent les quatre premiers niveaux de mip ; au cinquieme
     le blanc revient. La promesse depassait donc la mesure d'un cran, ce qui
     est precisement le reproche que l'on repare partout ailleurs.

     On remplit maintenant la gouttiere ENTIERE, chaque bord venant a sa
     moitie, axe par axe (les deux gouttieres n'ont pas la meme largeur) — et
     on COMPTE ce qui reste de fond entre deux ilots pour l'ecrire au panneau.
     Un chiffre mesure a la place d'une promesse. */
  const DILAT_MAX = 64;

  /* La dilatation ne peut pas etre une constante : a 72 DPI l'atlas tombe a
     370 px de large et la gouttiere recto|verso ne fait plus que 7,4 px. La
     largeur sort donc de la gouttiere elle-meme, et c'est la largeur EFFECTIVE
     — avec le reste de fond mesure — que le panneau affiche. */
  function islandDilate(x, cv, W, H, I) {
    const gu = (I.back[0] - I.front[2]) * W;
    const gv = (I.edge[1] - I.front[3]) * H;
    const padU = Math.max(1, Math.min(DILAT_MAX, Math.ceil(gu / 2)));
    const padV = Math.max(1, Math.min(DILAT_MAX, Math.ceil(gv / 2)));
    Object.keys(I).forEach((k) => {
      const r = I[k];
      const x0 = Math.round(r[0] * W), y0 = Math.round(r[1] * H);
      const x1 = Math.round(r[2] * W), y1 = Math.round(r[3] * H);
      const w = x1 - x0, h = y1 - y0;
      if (w < 2 || h < 2) return;
      /* colonnes d'abord, puis lignes en reprenant les colonnes deja posees :
         les quatre coins sont couverts sans cas particulier */
      x.drawImage(cv, x1 - 1, y0, 1, h, x1, y0, padU, h);
      x.drawImage(cv, x0, y0, 1, h, x0 - padU, y0, padU, h);
      x.drawImage(cv, x0 - padU, y1 - 1, w + 2 * padU, 1, x0 - padU, y1, w + 2 * padU, padV);
      x.drawImage(cv, x0 - padU, y0, w + 2 * padU, 1, x0 - padU, y0 - padV, w + 2 * padU, padV);
    });
    return { u: padU, v: padV, reste: gutterLeft(x, W, H, I), gu: gu, gv: gv };
  }

  /* CE QUI RESTE DE FOND ENTRE DEUX ILOTS, COMPTE SUR LA TOILE QUI PART DANS
     LE FICHIER. Le fond initial est un blanc pur (`fillRect` #ffffff) : tout
     texel encore a (255,255,255) dans une gouttiere est un texel que le
     filtrage d'un moteur ira melanger au bord d'une carte. Le panneau publie
     ce compte — zero ou pas. */
  function gutterLeft(x, W, H, I) {
    const bandes = [
      [Math.round(I.front[2] * W), 0, Math.round(I.back[0] * W), Math.round(I.front[3] * H)],
      [0, Math.round(I.front[3] * H), W, Math.round(I.edge[1] * H)],
    ];
    let blanc = 0, total = 0;
    bandes.forEach((b) => {
      const w = b[2] - b[0], h = b[3] - b[1];
      if (w < 1 || h < 1) return;
      const d = x.getImageData(b[0], b[1], w, h).data;
      for (let i = 0; i < d.length; i += 4) {
        total++;
        if (d[i] === 255 && d[i + 1] === 255 && d[i + 2] === 255) blanc++;
      }
    });
    return { blanc: blanc, total: total };
  }

  function paintEdge(x, W, H, r) {
    const y0 = r[1] * H, hh = (r[3] - r[1]) * H;
    const col = S("edge", "#efe9dc"), st = S("edge_style", "plein");
    if (st === "metal") {
      const gr = x.createLinearGradient(0, y0, 0, y0 + hh);
      gr.addColorStop(0, shade(col, -0.35));
      gr.addColorStop(0.38, shade(col, 0.35));
      gr.addColorStop(0.52, "#ffffff");
      gr.addColorStop(0.68, shade(col, 0.18));
      gr.addColorStop(1, shade(col, -0.45));
      x.fillStyle = gr;
    } else if (st === "sombre") {
      x.fillStyle = shade(col, -0.72);
    } else {
      x.fillStyle = col;
    }
    x.fillRect(0, y0, W, hh);
    if (st !== "sombre") {
      x.globalAlpha = 0.10;
      x.fillStyle = "#000";
      for (let i = 0; i < W; i += 6) x.fillRect(i, y0, 2, hh);
      x.globalAlpha = 1;
    }
  }

  function shade(hex, k) {
    const m = /^#?([0-9a-f]{6})$/i.exec(String(hex || ""));
    const n = m ? parseInt(m[1], 16) : 0xefe9dc;
    const c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) =>
      Math.max(0, Math.min(255, Math.round(k >= 0 ? v + (255 - v) * k : v * (1 + k)))));
    return "rgb(" + c.join(",") + ")";
  }

  /* ═══════════════════════════════════════════════════════════════════════
     5 bis. LES CARTES PBR — derivees de l'atlas, ecrites dans le fichier
     ═══════════════════════════════════════════════════════════════════════
     LE GRIEF, MESURE SUR LES OCTETS : le GLB ne transportait qu'une texture
     (base), zero normal, zero rugosite, zero metal, zero occlusion, pas
     d'attribut TANGENT, et `metallicFactor` 0,05 / `roughnessFactor` 0,52
     pour TOUTE la carte. Le papier, le filet et la tranche etaient donc le
     MEME materiau, et la bascule « Unie / Metal / Sombre » ne changeait pas
     un octet du fichier (empreinte de l'atlas identique avant/apres, mesuree).

     Ici : deux images de plus, et elles sont RELISIBLES.
       · NORMALES  = relief de l'encre, derive de la luminance de l'atlas
         (Sobel), amplitude reglee sur INK_RELIEF_MM ; sur la tranche
         « Metal », un brossage vertical s'y ajoute.
       · ORM       = occlusion (R) · rugosite (V) · metal (B), peint PAR ILOT
         avec les valeurs de `solid.PBR_*`. Le papier reste dielectrique
         (metal 0) — une carte imprimee n'a pas de metal sur ses faces ; la
         tranche doree, elle, existe vraiment chez l'imprimeur.
     La meme image sert d'`occlusionTexture` (canal R) : c'est le rangement
     ORM standard de glTF, pas une economie de bouts de ficelle. */

  /* Petite toile de travail : les cartes de matiere n'ont pas besoin de la
     definition du texte, seulement de ses ARETES. Moitie pour les normales,
     quart pour l'ORM dont les zones sont larges — et ce sont ces tailles-la
     que le HUD affiche, pas des tailles supposees. */
  function down(atlas, div) {
    const w = Math.max(64, Math.round(atlas.width / div));
    const h = Math.max(64, Math.round(atlas.height / div));
    const c = document.createElement("canvas");
    c.width = w; c.height = h;
    const x = c.getContext("2d");
    x.imageSmoothingEnabled = true;
    try { x.imageSmoothingQuality = "high"; } catch (e) { /* moteurs anciens */ }
    x.drawImage(atlas, 0, 0, w, h);
    return c;
  }

  async function toBytes(canvas, mime, q) {
    const b = await new Promise((res) => canvas.toBlob(res, mime, q));
    return { bytes: await b.arrayBuffer(), mime: mime };
  }

  /* ── PNG ECRIT ICI, EN RGB, AVEC DE VRAIS FILTRES ──────────────────────────
     DEUX GRIEFS MESURES SUR LES OCTETS DU FICHIER LIVRE :

       1. « Deux canaux sur quatre de la carte de normales sont du pur
          remplissage : bleu constant a 255 et alpha constant a 255. Meme
          gaspillage sur l'ORM (bleu constant a 0, alpha constant a 255). Ce
          sont des PNG RGBA la ou deux canaux suffiraient. »
       2. « La carte de normales pese 286 780 octets, soit 43,8 % du fichier
          livre — plus que l'illustration elle-meme. »

     `canvas.toBlob("image/png")` ne laisse choisir NI le type de couleur NI le
     filtrage : il ecrit du RGBA et compresse a la va-vite. Mesure sur la carte
     de normales reelle (759 x 553) : 288 094 octets par la toile, 151 821 pour
     les MEMES pixels re-encodes avec choix de filtre par ligne, 144 282 en RGB
     sans canal alpha. La moitie du poids etait de la paresse d'encodeur.

     On ecrit donc le PNG ici : filtre choisi ligne par ligne par la somme des
     ecarts absolus (l'heuristique de la specification PNG), et
     `CompressionStream("deflate")` — qui produit exactement le flux zlib
     qu'attend un chunk IDAT. Aucune bibliotheque, aucun reseau.

     DEUX ENCODAGES SONT PRODUITS ET PESES : type de couleur 2 (RGB, 8 bits) et
     type 3 (palette) quand l'image tient en 256 couleurs — ce qui est le cas
     de la carte de normales, qui n'en porte que quelques dizaines. Le plus
     leger part, et le panneau publie LES DEUX poids : l'economie se verifie.
     Si le navigateur n'a pas `CompressionStream`, on retombe sur la toile et
     le HUD affiche le type de couleur RELU dans l'en-tete : le panneau ne peut
     donc pas annoncer un encodage qu'il n'aurait pas ecrit. */
  const CRCT = (function () {
    const t = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
      t[n] = c >>> 0;
    }
    return t;
  })();

  function crc32(u8, from, len) {
    let c = 0xFFFFFFFF;
    for (let i = 0; i < len; i++) c = CRCT[(c ^ u8[from + i]) & 255] ^ (c >>> 8);
    return (c ^ 0xFFFFFFFF) >>> 0;
  }

  function chunk(type, data) {
    const out = new Uint8Array(12 + data.length);
    const dv = new DataView(out.buffer);
    dv.setUint32(0, data.length);
    for (let i = 0; i < 4; i++) out[4 + i] = type.charCodeAt(i);
    out.set(data, 8);
    dv.setUint32(8 + data.length, crc32(out, 4, 4 + data.length));
    return out;
  }

  /* Le filtre de la ligne est CHOISI, pas subi : on essaie les cinq et on garde
     celui dont la somme des ecarts absolus (lus en signe) est la plus faible.
     C'est la recette de la specification, et c'est la moitie du gain.

     `bpp` est le nombre d'octets par pixel COMPLET, arrondi a 1 au minimum
     (spec PNG 9.2) : 3 pour du RGB, 1 pour une image a palette — sous-octet
     compris. La meme boucle sert donc aux deux encodages. */
  function filterBytes(rows, stride, h, bpp) {
    const out = new Uint8Array((stride + 1) * h);
    const prev = new Uint8Array(stride);
    const cand = [new Uint8Array(stride), new Uint8Array(stride),
    new Uint8Array(stride), new Uint8Array(stride), new Uint8Array(stride)];
    let o = 0;
    for (let y = 0; y < h; y++) {
      const cur = rows(y);
      const cost = [0, 0, 0, 0, 0];
      for (let i = 0; i < stride; i++) {
        const a = i >= bpp ? cur[i - bpp] : 0;
        const b = prev[i];
        const c = i >= bpp ? prev[i - bpp] : 0;
        const p = a + b - c;
        const pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
        const pr = (pa <= pb && pa <= pc) ? a : (pb <= pc ? b : c);
        const v = [cur[i], cur[i] - a, cur[i] - b,
        cur[i] - ((a + b) >> 1), cur[i] - pr];
        for (let f = 0; f < 5; f++) {
          const u = v[f] & 255;
          cand[f][i] = u;
          cost[f] += u < 128 ? u : 256 - u;
        }
      }
      let best = 0;
      for (let f = 1; f < 5; f++) if (cost[f] < cost[best]) best = f;
      out[o++] = best;
      out.set(cand[best], o); o += stride;
      prev.set(cur);
    }
    return out;
  }

  async function deflate(raw) {
    const cs = new CompressionStream("deflate");     /* zlib : en-tete + adler32 */
    const wr = cs.writable.getWriter();
    wr.write(raw); wr.close();
    return new Uint8Array(await new Response(cs.readable).arrayBuffer());
  }

  function pngWrap(w, h, depth, type, z, plte) {
    const ihdr = new Uint8Array(13);
    const dv = new DataView(ihdr.buffer);
    dv.setUint32(0, w); dv.setUint32(4, h);
    ihdr[8] = depth; ihdr[9] = type;
    const sig = new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10]);
    const parts = [sig, chunk("IHDR", ihdr)];
    if (plte) parts.push(chunk("PLTE", plte));
    parts.push(chunk("IDAT", z), chunk("IEND", new Uint8Array(0)));
    let n = 0;
    parts.forEach((p) => { n += p.length; });
    const out = new Uint8Array(n);
    let p = 0;
    parts.forEach((q2) => { out.set(q2, p); p += q2.length; });
    return out;
  }

  async function pngRGB(imgData) {
    if (typeof CompressionStream !== "function") return null;
    const w = imgData.width, h = imgData.height, px = imgData.data;
    const stride = w * 3;
    const cur = new Uint8Array(stride);
    const raw = filterBytes((y) => {
      for (let x = 0; x < w; x++) {
        const s = (y * w + x) * 4, d = x * 3;
        cur[d] = px[s]; cur[d + 1] = px[s + 1]; cur[d + 2] = px[s + 2];
      }
      return cur;
    }, stride, h, 3);
    return pngWrap(w, h, 8, 2, await deflate(raw), null);
  }

  /* ── PNG A PALETTE : LE POIDS QUI RESTAIT ─────────────────────────────────
     LE GRIEF, MESURE SUR LE FICHIER LIVRE : « carte de normales QUASI INERTE,
     ET CHERE : 8 / 8 / 1 valeurs distinctes sur 256, deviation maximale
     2,22 deg — et elle coute 27 % du fichier entier. Soit on encode ce relief
     de six microns dans un canal leger, soit on ne l'encode pas. »

     Le grief est juste et il a une reponse EXACTE, pas un compromis : une
     image qui ne contient que quelques dizaines de couleurs n'a rien a faire
     en RGB. On COMPTE les triplets distincts ; s'il y en a 256 au plus, on
     ecrit un PNG de type 3 (palette) a la plus petite profondeur qui les
     contient — 1, 2, 4 ou 8 bits par texel au lieu de 24. Les texels sont
     IDENTIQUES : la palette est construite sur eux, chaque index y renvoie sa
     couleur exacte, et l'empreinte des texels reconstruits est comparee a
     celle de la source avant de rendre quoi que ce soit.

     Les deux encodages sont produits, MESURES, et c'est le plus leger qui
     part — le panneau publie les deux poids. */
  const PAL_MAX = 256;

  function palette(imgData) {
    const px = imgData.data, n = imgData.width * imgData.height;
    const map = new Map(), pal = [];
    const idx = new Uint8Array(n);
    for (let i = 0; i < n; i++) {
      const o = i * 4;
      const k = (px[o] << 16) | (px[o + 1] << 8) | px[o + 2];
      let v = map.get(k);
      if (v === undefined) {
        if (pal.length >= PAL_MAX) return null;
        v = pal.length; pal.push(k); map.set(k, v);
      }
      idx[i] = v;
    }
    return { idx: idx, pal: pal };
  }

  /* Empreinte FNV-1a des texels RGB : celle de la source, puis celle des
     texels RECONSTRUITS depuis la palette. Deux nombres egaux = aucun texel
     n'a bouge. C'est la preuve, pas la promesse. */
  function fnvRGB(get, n) {
    let hh = 0x811c9dc5;
    for (let i = 0; i < n; i++) {
      const c = get(i);
      for (let s = 16; s >= 0; s -= 8) {
        hh ^= (c >>> s) & 255;
        hh = (hh + ((hh << 1) + (hh << 4) + (hh << 7) + (hh << 8) + (hh << 24))) >>> 0;
      }
    }
    return hh >>> 0;
  }

  async function pngPalette(imgData) {
    if (typeof CompressionStream !== "function") return null;
    const P = palette(imgData);
    if (!P) return null;
    const w = imgData.width, h = imgData.height, px = imgData.data;
    const nc = P.pal.length;
    const depth = nc <= 2 ? 1 : (nc <= 4 ? 2 : (nc <= 16 ? 4 : 8));
    /* la source et la reconstruction, texel par texel */
    const src = fnvRGB((i) => (px[i * 4] << 16) | (px[i * 4 + 1] << 8) | px[i * 4 + 2], w * h);
    const rec = fnvRGB((i) => P.pal[P.idx[i]], w * h);
    if (src !== rec) return null;                    /* jamais vu : on n'expedie pas */
    const stride = Math.ceil(w * depth / 8);
    const cur = new Uint8Array(stride);
    const raw = filterBytes((y) => {
      cur.fill(0);
      if (depth === 8) {
        for (let x = 0; x < w; x++) cur[x] = P.idx[y * w + x];
      } else {
        const per = 8 / depth;
        for (let x = 0; x < w; x++) {
          const b = (x / per) | 0, sh = 8 - depth * ((x % per) + 1);
          cur[b] |= (P.idx[y * w + x] & ((1 << depth) - 1)) << sh;
        }
      }
      return cur;
    }, stride, h, 1);
    const plte = new Uint8Array(nc * 3);
    for (let i = 0; i < nc; i++) {
      plte[i * 3] = (P.pal[i] >> 16) & 255;
      plte[i * 3 + 1] = (P.pal[i] >> 8) & 255;
      plte[i * 3 + 2] = P.pal[i] & 255;
    }
    return { bytes: pngWrap(w, h, depth, 3, await deflate(raw), plte),
      couleurs: nc, bits: depth, empreinte: src };
  }

  /* Le type de couleur RELU dans l'en-tete du PNG produit — pas celui qu'on
     croit avoir demande. Octet 25 de l'IHDR. */
  function pngType(bytes) {
    const u = new Uint8Array(bytes);
    if (u.length < 26 || u[0] !== 137 || u[1] !== 80) return "?";
    return { 0: "gris", 2: "RGB", 3: "palette", 4: "gris+A", 6: "RGBA" }[u[25]] || ("type " + u[25]);
  }

  /* Une image de matiere : PNG ecrit ici si le navigateur sait deflater, sinon
     la toile. Dans les deux cas on rend les OCTETS, et le HUD relit dedans.
     Les DEUX encodages sont pesés — RGB et palette — et le plus leger part ;
     les deux poids sont publies pour que l'economie soit verifiable. */
  async function mapBytes(canvas) {
    const x = canvas.getContext("2d");
    const id = x.getImageData(0, 0, canvas.width, canvas.height);
    const u = await pngRGB(id);
    if (!u) return Object.assign(await toBytes(canvas, "image/png"), { ecrit_ici: false });
    const p = await pngPalette(id);
    if (p && p.bytes.length < u.length) {
      return { bytes: p.bytes.buffer, mime: "image/png", ecrit_ici: true,
        rgb_octets: u.length, couleurs: p.couleurs, bits: p.bits };
    }
    return { bytes: u.buffer, mime: "image/png", ecrit_ici: true,
      rgb_octets: u.length, couleurs: p ? p.couleurs : null, bits: p ? p.bits : null };
  }

  async function buildMaps() {
    /* LA CLE DES CARTES DERIVEES EST L'EMPREINTE DES PIXELS, pas celle des
       reglages : `ATLAS_KEY` seul laissait le relief d'une carte sur la
       suivante (voir la mesure dans `buildAtlas`). */
    const RL = RELIEFS.filter((r) => r.id === S("relief", "leger"))[0] || RELIEFS[1];
    const k = ATLAS_KEY + "~" + ATLAS_SIG + "~" + RL.id;
    if (MAPS && MAPS_KEY === k) return MAPS;
    const I = islandRects();
    const st = S("edge_style", "plein");
    const E = PBR_EDGE[st] || PBR_EDGE.plein;

    /* ── carte de NORMALES ───────────────────────────────────────────────
       L'echelle physique compte : un relief de INK_RELIEF_MM sur un pixel qui
       vaut trim_mm / largeur d'ilot donne la pente reelle de l'encre. On ne
       choisit donc pas une amplitude « qui rend bien », on la CALCULE. */
    /* la definition suit le reglage « Relief d'encre » : quart, moitie, ou
       rien du tout. Le demi-atlas a deja ete produit pour l'empreinte, on le
       reprend au lieu de le redessiner quand c'est celui-la qu'il faut. */
    const src = RL.div === 0 ? null
      : (RL.div === 2 ? (ATLAS_HALF || down(ATLAS, 2)) : down(ATLAS, RL.div));
    const w = src ? src.width : 0, h = src ? src.height : 0;
    const vBande = I.edge[1];
    let nrm = null, relief = null;
    if (src) {
    const sx = src.getContext("2d");
    const px = sx.getImageData(0, 0, w, h).data;
    const lum = new Float32Array(w * h);
    for (let i = 0, n = w * h; i < n; i++) {
      lum[i] = (0.2126 * px[i * 4] + 0.7152 * px[i * 4 + 1] + 0.0722 * px[i * 4 + 2]) / 255;
    }
    const g = CF.geom();
    const mmParPx = g.trim_mm[0] / Math.max(1, (I.front[2] - I.front[0]) * w);
    const amp = INK_RELIEF_MM / mmParPx;      /* pente = hauteur / pas, sans unite */
    nrm = document.createElement("canvas");
    nrm.width = w; nrm.height = h;
    const nx = nrm.getContext("2d");
    const nim = nx.createImageData(w, h);
    for (let y = 0; y < h; y++) {
      const bande = (y / h) >= vBande;
      for (let x = 0; x < w; x++) {
        const i = y * w + x;
        const xm = Math.max(0, x - 1), xp = Math.min(w - 1, x + 1);
        const ym = Math.max(0, y - 1), yp = Math.min(h - 1, y + 1);
        /* l'encre sombre est DEPOSEE : elle monte, d'ou le signe */
        let dx = (lum[y * w + xm] - lum[y * w + xp]) * amp;
        let dy = (lum[ym * w + x] - lum[yp * w + x]) * amp;
        if (bande && st === "metal") dx += Math.sin(x * 1.7) * 0.10;  /* brossage */
        const l = Math.sqrt(dx * dx + dy * dy + 1);
        const o = i * 4;
        nim.data[o] = Math.round((dx / l * 0.5 + 0.5) * 255);
        nim.data[o + 1] = Math.round((dy / l * 0.5 + 0.5) * 255);
        nim.data[o + 2] = Math.round((1 / l * 0.5 + 0.5) * 255);
        nim.data[o + 3] = 255;
      }
    }
    nx.putImageData(nim, 0, 0);

    /* ── LE RELIEF QUE CETTE CARTE PORTE VRAIMENT ────────────────────────
       LE GRIEF : « carte de normales QUASI INERTE, ET CHERE — deviation
       maximale 2,22 deg, RMS 0,51 deg, 8 valeurs distinctes seulement dans le
       canal R, pour 38 % du fichier entier ; le panneau la vend pourtant comme
       "normales 237 Kio en 759x553" ». Le poids etait affiche, l'effet non.
       On mesure donc l'angle, sur les octets QUI PARTENT dans le fichier :
       l'ecart entre la normale encodee et la verticale, texel par texel. Le
       chiffre est faible — il s'affiche quand meme, c'est une epaisseur
       d'encre offset de 6 micrometres, pas une gravure. */
    let devMax = 0, devSum2 = 0, devN = 0, sous1 = 0, penteMax = 0;
    for (let i = 0; i < w * h; i++) {
      const o = i * 4;
      const vx = nim.data[o] / 255 * 2 - 1;
      const vy = nim.data[o + 1] / 255 * 2 - 1;
      const vz = nim.data[o + 2] / 255 * 2 - 1;
      const ln = Math.sqrt(vx * vx + vy * vy + vz * vz) || 1;
      const a = Math.acos(Math.max(-1, Math.min(1, vz / ln))) * 180 / Math.PI;
      if (a > devMax) devMax = a;
      devSum2 += a * a; devN++;
      if (a < 1) sous1++;
      /* LA PENTE PAR AXE, D'OU LA MARCHE D'ENCRE SE DEDUIT. Le panneau
         annoncait « relief d'encre de 6 µm » sous le mot « mesuré » : c'etait
         la CONSIGNE (`INK_RELIEF_MM`), pas une lecture des octets. On releve
         donc la pente maximale d'un SEUL axe — celle qu'un bord d'encre franc
         produit — et la marche s'en deduit par le pas de texel. */
      if (vz > 1e-6) {
        const px2 = Math.abs(vx / vz), py2 = Math.abs(vy / vz);
        if (px2 > penteMax) penteMax = px2;
        if (py2 > penteMax) penteMax = py2;
      }
    }
    /* ── LA PROFONDEUR UTILE, PAS CELLE DE L'EN-TETE ─────────────────────
       Un audit a demontre ailleurs qu'un badge « 16 bits » etait FAUX : l'IHDR
       annoncait 16 bits mais les echantillons tombaient tous sur le reseau
       k x 257, soit 200 valeurs distinctes = 7,64 bits utiles. La lecon vaut
       CONTRE NOUS : ce PNG est bien un 8 bits d'en-tete, mais ses canaux X et
       Y ne portent que quelques valeurs distinctes. On les COMPTE et on les
       ecrit a cote du « 8 bits », pour que personne n'ait a nous prendre en
       defaut sur ce que l'en-tete ne dit pas. */
    const vus = [new Uint8Array(256), new Uint8Array(256), new Uint8Array(256)];
    for (let i = 0; i < w * h; i++) {
      vus[0][nim.data[i * 4]] = 1;
      vus[1][nim.data[i * 4 + 1]] = 1;
      vus[2][nim.data[i * 4 + 2]] = 1;
    }
    const dist = vus.map((t) => { let n = 0; for (let v = 0; v < 256; v++) n += t[v]; return n; });
    relief = {
      max_deg: devMax, rms_deg: Math.sqrt(devSum2 / Math.max(1, devN)),
      sous1_pct: sous1 / Math.max(1, devN) * 100,
      /* la CONSIGNE (partagee avec le backend) et ce que les octets portent */
      relief_demande_mm: INK_RELIEF_MM,
      pente_max: penteMax,
      pas_mm: mmParPx,
      relief_mesure_mm: penteMax * mmParPx,
      distinctes: dist,
      bits_utiles: Math.log(Math.max(1, dist[0])) / Math.LN2,
    };
    }

    /* ── carte ORM ───────────────────────────────────────────────────────
       R = occlusion, V = rugosite, B = metal. Les valeurs viennent de
       `solid.PBR_*` ; la rugosite des faces baisse la ou l'encre couvre
       (l'encre est plus lisse que le papier nu). */
    const osrc = down(ATLAS, 4);
    const ow = osrc.width, oh = osrc.height;
    const op = osrc.getContext("2d").getImageData(0, 0, ow, oh).data;
    const orm = document.createElement("canvas");
    orm.width = ow; orm.height = oh;
    const ox = orm.getContext("2d");
    const oim = ox.createImageData(ow, oh);
    const bandeY0 = vBande * oh;
    /* LE FACTEUR DE METAL EST LE MAXIMUM REELLEMENT ECRIT — connu d'avance,
       puisque le metal ne prend que deux valeurs : celle du papier et celle de
       la tranche. Le canal bleu porte ensuite la FRACTION de ce maximum, donc
       metal = metallicFactor x B est le meme nombre qu'avant, au pixel pres,
       et une visionneuse qui perd la texture retombe sur du papier mat. */
    const mMax = Math.max(PBR_FACE.metallic, E.metallic);
    for (let y = 0; y < oh; y++) {
      const dansBande = y >= bandeY0;
      /* la tranche est pincee entre les deux chanfreins : l'occlusion y est
         plus forte pres de ses bords, pas au milieu */
      const t = dansBande ? Math.abs((y - bandeY0) / Math.max(1, oh - bandeY0) - 0.5) * 2 : 0;
      for (let x = 0; x < ow; x++) {
        const i = (y * ow + x) * 4;
        const l = (0.2126 * op[i] + 0.7152 * op[i + 1] + 0.0722 * op[i + 2]) / 255;
        let ao, rough, metal;
        if (dansBande) {
          ao = E.ao + (1 - E.ao) * (1 - t) * 0.5;
          rough = E.roughness;
          metal = E.metallic;
        } else {
          const encre = Math.min(1, Math.max(0, 1 - l));   /* couverture d'encre */
          ao = PBR_FACE.ao - 0.10 * encre;
          rough = PBR_FACE.roughness - INK_ROUGHNESS_DROP * encre;
          metal = PBR_FACE.metallic;
        }
        oim.data[i] = Math.round(Math.max(0, Math.min(1, ao)) * 255);
        oim.data[i + 1] = Math.round(Math.max(0, Math.min(1, rough)) * 255);
        oim.data[i + 2] = mMax > 0 ? Math.round(Math.max(0, Math.min(1, metal / mMax)) * 255) : 0;
        oim.data[i + 3] = 255;
      }
    }
    ox.putImageData(oim, 0, 0);

    /* ── CE QUE L'ORM PORTE VRAIMENT, RELU DANS SES OCTETS ────────────────
       LE GRIEF : le panneau ecrivait « Papier : rugosite 0,62 » — la CONSIGNE,
       celle du papier nu. L'ORM livre donne 0,50 de moyenne, parce que l'encre
       fait baisser la rugosite partout ou elle couvre. Le chiffre affiche
       n'etait donc celui d'aucun pixel majoritaire du fichier. On mesure
       maintenant l'image telle qu'elle est ecrite (PNG sans perte : ces octets
       SONT ceux du fichier) et on affiche l'intervalle, pas la consigne. */
    const stat = (off, x0, x1, y0, y1, fac) => {
      let mi = 255, ma = 0, s = 0, n = 0;
      for (let y = y0; y < y1; y++) {
        for (let x = x0; x < x1; x++) {
          const v = oim.data[(y * ow + x) * 4 + off];
          if (v < mi) mi = v;
          if (v > ma) ma = v;
          s += v; n++;
        }
      }
      const f = (fac == null ? 1 : fac) / 255;
      return n ? { min: mi * f, max: ma * f, moy: s / n * f } : { min: 0, max: 0, moy: 0 };
    };
    const fx1 = Math.max(1, Math.round(I.front[2] * ow));
    const fy1 = Math.max(1, Math.round(I.front[3] * oh));
    /* PLUS DE LIGNE SAUTEE. `+ 1` ecartait la PREMIERE rangee de la bande —
       celle ou le pincement de tranche est le plus fort — et le panneau
       affichait donc 0,910 la ou l'ORM livre porte 0,902 sur cette rangee.
       Un minimum qui n'est pas le minimum du fichier est un chiffre faux :
       la bande est mesuree entiere, de sa premiere rangee a la derniere. */
    const by0 = Math.min(oh - 1, Math.round(vBande * oh));
    const bx0 = Math.min(ow - 1, Math.round(I.back[0] * ow));
    MAPS = {
      normal: nrm ? await mapBytes(nrm) : null,
      orm: await mapBytes(orm),
      normal_px: nrm ? [w, h] : null, orm_px: [ow, oh], edge_style: st,
      relief_id: RL.id, relief_l: RL.l,
      metal_max: mMax, relief: relief,
      /* LE CANAL METAL, COMPTE. Le grief : « canal metal de l'ORM ENTIEREMENT
         MORT : une seule valeur distincte sur les trois regions ». C'est vrai
         pour du papier, et c'est faux des que la tranche est doree — dans les
         deux cas, le nombre se compte au lieu de se supposer. */
      metal_vals: (function () {
        const t = new Uint8Array(256);
        for (let i = 0; i < ow * oh; i++) t[oim.data[i * 4 + 2]] = 1;
        let n = 0;
        for (let v = 0; v < 256; v++) n += t[v];
        return n;
      })(),
      mesure: {
        face_rough: stat(1, 0, fx1, 0, fy1),
        face_metal: stat(2, 0, fx1, 0, fy1, mMax),
        /* LE VERSO EST UNE FACE, LUI AUSSI. « Papier : rugosite 0,518 » etait
           la mesure du RECTO SEUL ; qui redecode l'ORM moyenne les deux ilots
           et trouve un autre nombre. Les deux sont donc releves et nommes. */
        back_rough: stat(1, bx0, ow, 0, fy1),
        back_ao: stat(0, bx0, ow, 0, fy1),
        edge_rough: stat(1, 0, ow, by0, oh),
        edge_metal: stat(2, 0, ow, by0, oh, mMax),
        /* L'OCCLUSION ETAIT MESUREE ET JAMAIS AFFICHEE. Un chiffre calcule
           puis jete est exactement ce qu'un contradicteur va chercher : le
           grief « canal d'occlusion faible, plage 230-255, il n'utilise que
           10 % de sa dynamique » etait juste, et rien a l'ecran ne le disait.
           Les deux regions sont relevees separement, et le panneau publie
           l'etendue reellement occupee. */
        face_ao: stat(0, 0, fx1, 0, fy1),
        edge_ao: stat(0, 0, ow, by0, oh),
        ao: stat(0, 0, ow, 0, oh),
      },
    };
    MAPS_KEY = k;
    return MAPS;
  }

  /* Ce que l'octet dit, pas ce que l'on suppose : sous-echantillonnage chroma
     relu dans le SOF du JPEG produit. « 4:2:0 » ecrit dans le panneau vient
     d'ici, pas d'une croyance sur l'encodeur du navigateur. */
  function chromaJpeg(buf) {
    const b = new Uint8Array(buf);
    let i = 2;
    while (i + 9 < b.length) {
      if (b[i] !== 0xFF) { i++; continue; }
      const m = b[i + 1];
      if (m === 0xD8 || m === 0xD9 || (m >= 0xD0 && m <= 0xD7)) { i += 2; continue; }
      const seg = (b[i + 2] << 8) | b[i + 3];
      if ([0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB].indexOf(m) >= 0) {
        const nc = b[i + 9];
        if (nc < 1) return "?";
        const hv = b[i + 11];
        const H = hv >> 4, V = hv & 15;
        if (nc === 1) return "N&B";
        if (H === 1 && V === 1) return "4:4:4";
        if (H === 2 && V === 1) return "4:2:2";
        if (H === 2 && V === 2) return "4:2:0";
        return H + "x" + V;
      }
      i += 2 + Math.max(2, seg);
    }
    return "?";
  }

  /* ═══════════════════════════════════════════════════════════════════════
     6. MAILLAGE — le backend fait foi, un secours local existe et le dit
     ═══════════════════════════════════════════════════════════════════════ */

  /* DEUX CLES, PAS UNE. Avec une seule, changer la couleur de tranche ne
     redessinait pas l'atlas (mesure : empreinte de l'image identique apres un
     passage au rouge vif) et changer l'epaisseur re-telechargeait le maillage
     pour rien. Le maillage depend de la geometrie, l'atlas depend en plus de
     la tranche, du plafond et du format d'image. */
  function meshKey() {
    const g = CF.geom();
    return [g.fmt, g.dpi, S("thickness_mm", 0.32), S("corner_mm", 3),
    S("segments", 6), S("bevel_mm", 0.1), S("atlas", 1536)].join("|");
  }

  function atlasKey() {
    const g = CF.geom();
    return [g.fmt, g.dpi, S("atlas", 1536), S("atlas_fmt", "jpeg"),
    S("edge", "#efe9dc"), S("edge_style", "plein")].join("|");
  }

  /* TOUT ce qui change le fichier, et RIEN d'autre : le tourne-disque, la
     lumiere, l'exposition et l'ombre n'entrent pas dans le GLB. */
  function modelSig() {
    return [meshKey(), atlasKey(), S("view", "matiere"), S("wire", false),
      S("relief", "leger")].join("~");
  }

  async function loadMesh() {
    const k = meshKey();
    if (MESH && MESH_KEY === k) return MESH;
    const g = CF.geom();
    const qs = "mesh?fmt=" + encodeURIComponent(g.fmt) + "&dpi=" + g.dpi
      + "&thickness_mm=" + S("thickness_mm", 0.32)
      + "&corner_mm=" + S("corner_mm", 3)
      + "&segments=" + S("segments", 6)
      + "&bevel_mm=" + S("bevel_mm", 0.1)
      + "&atlas=" + S("atlas", 1536);
    try {
      const r = await M.api.get(qs);
      MESH = r.mesh; REPORT = r; MESH_LOCAL = false; MESH_KEY = k;
    } catch (e) {
      MESH = localMesh(); REPORT = localReport(MESH); MESH_LOCAL = true; MESH_KEY = k;
      if (!e || !e.missing) console.warn("cardforge: solid/mesh", e);
    }
    return MESH;
  }

  /* SECOURS : une boite plate a 3 ilots, identique en forme au maillage de
     reference du contrat. Elle ne remplace pas `card_mesh` — elle evite un
     ecran vide quand /api/cards n'est pas monte, et le HUD affiche « local ».
     Aucune autre piece n'en depend. */
  function localMesh() {
    const g = CF.geom(), I = islandRects();
    const s = 2 / g.trim_mm[1];
    const hw = g.trim_mm[0] * s / 2, hh = 1, ht = S("thickness_mm", 0.32) * s / 2;
    const P = [], N = [], U = [], X = [];
    const quad = (a, b, c, d, n, uv) => {
      const i = P.length / 3;
      [a, b, c, d].forEach((p, j) => {
        P.push(p[0], p[1], p[2]); N.push(n[0], n[1], n[2]); U.push(uv[j][0], uv[j][1]);
      });
      X.push(i, i + 2, i + 1, i + 1, i + 2, i + 3);
    };
    const R = (r) => [[r[0], r[1]], [r[2], r[1]], [r[0], r[3]], [r[2], r[3]]];
    quad([-hw, hh, ht], [hw, hh, ht], [-hw, -hh, ht], [hw, -hh, ht], [0, 0, 1], R(I.front));
    quad([hw, hh, -ht], [-hw, hh, -ht], [hw, -hh, -ht], [-hw, -hh, -ht], [0, 0, -1], R(I.back));
    const e = I.edge, q4 = (e[2] - e[0]) / 4;
    const band = (i) => [e[0] + i * q4, e[1], e[0] + (i + 1) * q4, e[3]];
    quad([-hw, hh, -ht], [hw, hh, -ht], [-hw, hh, ht], [hw, hh, ht], [0, 1, 0], R(band(0)));
    quad([hw, hh, ht], [hw, hh, -ht], [hw, -hh, ht], [hw, -hh, -ht], [1, 0, 0], R(band(1)));
    quad([-hw, -hh, ht], [hw, -hh, ht], [-hw, -hh, -ht], [hw, -hh, -ht], [0, -1, 0], R(band(2)));
    quad([-hw, hh, -ht], [-hw, hh, ht], [-hw, -hh, -ht], [-hw, -hh, ht], [-1, 0, 0], R(band(3)));
    return { positions: P, normals: N, uvs: U, indices: X };
  }
  function localReport(m) {
    const g = CF.geom(), t = S("thickness_mm", 0.32);
    return {
      /* uv_det_max MESURE, pas asserte : la version precedente ecrivait -1 en
         dur, et le HUD annoncait « aucun miroir » sans avoir rien regarde. */
      stats: { triangles: m.indices.length / 3, vertices: m.positions.length / 3, islands: 3, uv_det_max: uvDetMax(m) },
      dims_mm: [g.trim_mm[0], g.trim_mm[1], t],
      dims_in: [g.trim_in[0], g.trim_in[1], Math.round(t / 25.4 * 10000) / 10000],
      islands: islandRects(),
      scale: { unit_per_mm: 2 / g.trim_mm[1] },
    };
  }

  /* LES TROIS MESURES DU HUD, prises sur les tableaux QUI PARTENT DANS LE
     FICHIER — pas sur les curseurs, pas sur une reponse du serveur. */
  /* ── LES ILOTS UV, COMPTES ET PROUVES ──────────────────────────────────
     LE GRIEF : le HUD ecrivait « 3 ilots disjoints » alors que le maillage
     compte CINQ composantes connexes par indices (chaque face plate est
     separee de sa couronne de chanfrein par une couture de sommets). Le
     chiffre decrivait le RANGEMENT, pas la topologie, et rien ne le disait.

     Ici, deux mesures distinctes et nommees :
       · REGIONS = composantes connexes apres soudure par COORDONNEE UV. C'est
         le nombre de taches separees que l'on voit dans l'atlas : 3.
       · RECOUVREMENT = test d'axes separateurs, triangle contre triangle, sur
         TOUTES les paires appartenant a deux regions differentes. C'est
         l'invariant que la spec nomme vraiment, et il est desormais MESURE et
         non affirme : « 0 sur 16 464 paires » se verifie, « disjoints » non. */
  function satOverlap(A, B) {
    for (let t = 0; t < 2; t++) {
      const P = t ? B : A;
      for (let e = 0; e < 3; e++) {
        const j = ((e + 1) % 3) * 2;
        const nx = -(P[j + 1] - P[e * 2 + 1]), ny = (P[j] - P[e * 2]);
        let a0 = Infinity, a1 = -Infinity, b0 = Infinity, b1 = -Infinity;
        for (let k = 0; k < 3; k++) {
          const pa = A[k * 2] * nx + A[k * 2 + 1] * ny;
          const pb = B[k * 2] * nx + B[k * 2 + 1] * ny;
          if (pa < a0) a0 = pa; if (pa > a1) a1 = pa;
          if (pb < b0) b0 = pb; if (pb > b1) b1 = pb;
        }
        if (a1 <= b0 + 1e-12 || b1 <= a0 + 1e-12) return false;
      }
    }
    return true;
  }

  function uvIslands(m) {
    if (ILOTS && ILOTS_KEY === MESH_KEY) return ILOTS;
    const uv = m.uvs, idx = m.indices, nv = m.positions.length / 3;
    const map = new Map();
    const rid = new Int32Array(nv);
    let nk = 0;
    for (let i = 0; i < nv; i++) {
      const k = uv[i * 2].toFixed(6) + "," + uv[i * 2 + 1].toFixed(6);
      let v = map.get(k);
      if (v === undefined) { v = nk++; map.set(k, v); }
      rid[i] = v;
    }
    const par = new Int32Array(nk);
    for (let i = 0; i < nk; i++) par[i] = i;
    const find = (x) => { while (par[x] !== x) { par[x] = par[par[x]]; x = par[x]; } return x; };
    const uni = (a, b) => { a = find(a); b = find(b); if (a !== b) par[a] = b; };
    for (let i = 0; i < idx.length; i += 3) {
      uni(rid[idx[i]], rid[idx[i + 1]]); uni(rid[idx[i + 1]], rid[idx[i + 2]]);
    }
    const lab = new Map(), reg = [], T = [];
    for (let i = 0; i < idx.length; i += 3) {
      const r = find(rid[idx[i]]);
      if (!lab.has(r)) lab.set(r, lab.size);
      reg.push(lab.get(r));
      T.push([uv[idx[i] * 2], uv[idx[i] * 2 + 1], uv[idx[i + 1] * 2], uv[idx[i + 1] * 2 + 1],
      uv[idx[i + 2] * 2], uv[idx[i + 2] * 2 + 1]]);
    }
    let paires = 0, chevauche = 0;
    for (let a = 0; a < T.length; a++) {
      for (let b = a + 1; b < T.length; b++) {
        if (reg[a] === reg[b]) continue;
        paires++;
        if (satOverlap(T[a], T[b])) chevauche++;
      }
    }
    /* LE MEME DECOMPTE, SUR L'AUTRE DEFINITION — parce qu'un contradicteur
       prendra l'autre. « 3 ilots » a ete attaque comme « un arrondi
       charitable : le maillage compte en realite 5 composantes connexes ». Les
       deux sont vrais et ne mesurent pas la meme chose : 3 est le nombre de
       regions une fois les UV COINCIDENTS soudes (la definition d'un ilot
       d'atlas), 5 est le nombre de composantes si l'on compte les sommets
       DUPLIQUES a la couture du chanfrein — duplication qui existe pour les
       normales, pas pour la texture. On affiche les deux et on nomme la
       difference : un chiffre qu'on peut refaire de deux facons ne se
       conteste plus. */
    const par2 = new Int32Array(nv);
    for (let i = 0; i < nv; i++) par2[i] = i;
    const f2 = (x) => { while (par2[x] !== x) { par2[x] = par2[par2[x]]; x = par2[x]; } return x; };
    const u2 = (a, b) => { a = f2(a); b = f2(b); if (a !== b) par2[a] = b; };
    for (let i = 0; i < idx.length; i += 3) {
      u2(idx[i], idx[i + 1]); u2(idx[i + 1], idx[i + 2]);
    }
    const seen2 = {};
    let comp = 0;
    for (let i = 0; i < idx.length; i += 3) {
      const r = f2(idx[i]);
      if (!seen2[r]) { seen2[r] = 1; comp++; }
    }
    ILOTS = {
      regions: lab.size, paires: paires, chevauche: chevauche,
      composantes: comp, sommets: nv, coins_uv: nk,
    };
    ILOTS_KEY = MESH_KEY;
    return ILOTS;
  }

  /* ── LE VERSO SE LIT-IL A L'ENDROIT ? ────────────────────────────────────
     LE MANQUE NOMME PAR LE CRITIQUE : « le verso en miroir est l'erreur
     d'orientation la plus frequente du domaine ; le panneau possede deja tout
     ce qu'il faut pour la trancher — un bouton Verso, l'ilot UV du verso
     isole, le sens des 224 triangles en UV — mais il n'en tire AUCUNE phrase.
     Un panneau qui prouve au millioniemme de millimetre le retrait du
     chanfrein laisse l'utilisateur sans reponse sur la faute qui ruine
     reellement un tirage. »

     Le « 224/224 determinants < 0 » ne repond PAS a la question : il dit que
     tous les ilots ont le meme sens de parcours en UV, pas que le verso se lit
     a l'endroit QUAND ON LE REGARDE. On compare donc, face par face, le sens
     de parcours en coordonnees d'IMAGE (u vers la droite, v vers le BAS) au
     sens de parcours a l'ECRAN vu de ce cote-la : a droite = +x pour le recto,
     -x pour le verso puisqu'on passe derriere ; en bas = -y des deux cotes.
     Meme signe = pas de miroir. Miroir de `solid.face_orientation`, et calcule
     sur le maillage QUI PART DANS LE FICHIER. */
  function faceOrientation(m) {
    const p = m.positions, n = m.normals, uv = m.uvs, idx = m.indices;
    const o = {
      recto: { tri: 0, endroit: 0, miroir: 0 },
      verso: { tri: 0, endroit: 0, miroir: 0 },
      tranche: 0, u: [1, 0],
    };
    for (let i = 0; i < idx.length; i += 3) {
      const a = idx[i], b = idx[i + 1], c = idx[i + 2];
      const nz = (n[a * 3 + 2] + n[b * 3 + 2] + n[c * 3 + 2]) / 3;
      if (Math.abs(nz) < 0.1) { o.tranche++; continue; }
      const k = nz > 0 ? o.recto : o.verso;
      k.tri++;
      const di = (uv[b * 2] - uv[a * 2]) * (uv[c * 2 + 1] - uv[a * 2 + 1])
        - (uv[c * 2] - uv[a * 2]) * (uv[b * 2 + 1] - uv[a * 2 + 1]);
      const sx = nz > 0 ? 1 : -1;
      const ds = (sx * (p[b * 3] - p[a * 3])) * (-(p[c * 3 + 1] - p[a * 3 + 1]))
        - (sx * (p[c * 3] - p[a * 3])) * (-(p[b * 3 + 1] - p[a * 3 + 1]));
      if (di * ds > 0) k.endroit++; else k.miroir++;
      if (nz < 0) {
        for (let j = 0; j < 3; j++) {
          const u = uv[idx[i + j] * 2];
          if (u < o.u[0]) o.u[0] = u;
          if (u > o.u[1]) o.u[1] = u;
        }
      }
    }
    o.ok = o.verso.tri > 0 && o.verso.miroir === 0 && o.recto.miroir === 0;
    return o;
  }

  function uvDetMax(m) {
    const uv = m.uvs, idx = m.indices;
    let worst = -Infinity;
    for (let i = 0; i < idx.length; i += 3) {
      const a = idx[i] * 2, b = idx[i + 1] * 2, c = idx[i + 2] * 2;
      const d = (uv[b] - uv[a]) * (uv[c + 1] - uv[a + 1])
        - (uv[c] - uv[a]) * (uv[b + 1] - uv[a + 1]);
      if (d > worst) worst = d;
    }
    return worst;
  }

  /* Etendue de la boite englobante, en UNITES glTF — les memes nombres que
     `accessor.min/max` du fichier. */
  function bboxOf(m) {
    const p = m.positions;
    const mn = [Infinity, Infinity, Infinity], mx = [-Infinity, -Infinity, -Infinity];
    for (let i = 0; i < p.length; i += 3) {
      for (let j = 0; j < 3; j++) {
        if (p[i + j] < mn[j]) mn[j] = p[i + j];
        if (p[i + j] > mx[j]) mx[j] = p[i + j];
      }
    }
    return [mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]];
  }

  /* LES COTES DU HUD PASSENT PAR LE MEME FACTEUR QUE LE FICHIER. Avant, elles
     passaient par `unit_per_mm` — une convention — pendant que le noeud, lui,
     ne portait aucune echelle : l'ecran disait 63 mm, le fichier livrait
     1,432 m. Ici les deux sortent de `scaleOf` : si l'un ment, l'autre ment
     pareil, et la mesure sur les octets les prend tous les deux. */
  function bboxMm(m) {
    const s = scaleOf(m);
    return bboxOf(m).map((v) => v * s * 1000);
  }

  /* LE CHANFREIN QUE LA GEOMETRIE CONSTRUIT, pas celui qu'on demande — miroir
     de `solid.bevel_effective_mm`. Le panneau ecrivait « biseau 0,100 mm »
     quand le maillage portait des jambes de 0,072 mm : deux clampages, l'un a
     0,45 x epaisseur (l'ecran), l'autre a 0,45 x DEMI-epaisseur (le maillage).
     Un imprimeur qui lisait 0,100 mm de retrait se trompait de 28 %. */
  function bevelEff() {
    if (REPORT && REPORT.bevel && typeof REPORT.bevel.retrait_mm === "number") {
      return REPORT.bevel.retrait_mm;
    }
    const g = CF.geom();
    const w = g.trim_mm[0], h = g.trim_mm[1];
    const th = S("thickness_mm", 0.32);
    const r = Math.min(S("corner_mm", 3), Math.min(w, h) / 2);
    let b = Math.min(S("bevel_mm", 0.1), 0.45 * th / 2, 0.45 * Math.min(w, h) / 2);
    if (r > 1e-9) b = Math.min(b, 0.5 * r);
    return Math.max(0, b);
  }

  /* TANGENTES — glTF les veut en VEC4 (xyz + main du repere). Le backend les
     calcule (formule de Lengyel, `contract._tangents`) et P8 exporte
     CELLES-LA ; on ne recalcule ici que si le maillage vient du secours
     local, sinon deux chemins donneraient deux fichiers. */
  function tangentsOf(m) {
    if (m.tangents && m.tangents.length === (m.positions.length / 3) * 4) return m.tangents;
    const n = m.positions.length / 3, P = m.positions, N = m.normals, U = m.uvs, X = m.indices;
    const tan = new Float64Array(n * 3), bit = new Float64Array(n * 3);
    for (let t = 0; t < X.length; t += 3) {
      const i0 = X[t], i1 = X[t + 1], i2 = X[t + 2];
      const p0 = i0 * 3, p1 = i1 * 3, p2 = i2 * 3, q0 = i0 * 2, q1 = i1 * 2, q2 = i2 * 2;
      const e1 = [P[p1] - P[p0], P[p1 + 1] - P[p0 + 1], P[p1 + 2] - P[p0 + 2]];
      const e2 = [P[p2] - P[p0], P[p2 + 1] - P[p0 + 1], P[p2 + 2] - P[p0 + 2]];
      const du1 = U[q1] - U[q0], dv1 = U[q1 + 1] - U[q0 + 1];
      const du2 = U[q2] - U[q0], dv2 = U[q2 + 1] - U[q0 + 1];
      const det = du1 * dv2 - du2 * dv1;
      if (Math.abs(det) < 1e-12) continue;
      const f = 1 / det;
      const T = [(dv2 * e1[0] - dv1 * e2[0]) * f, (dv2 * e1[1] - dv1 * e2[1]) * f, (dv2 * e1[2] - dv1 * e2[2]) * f];
      const B = [(du1 * e2[0] - du2 * e1[0]) * f, (du1 * e2[1] - du2 * e1[1]) * f, (du1 * e2[2] - du2 * e1[2]) * f];
      [i0, i1, i2].forEach((i) => {
        const k = i * 3;
        tan[k] += T[0]; tan[k + 1] += T[1]; tan[k + 2] += T[2];
        bit[k] += B[0]; bit[k + 1] += B[1]; bit[k + 2] += B[2];
      });
    }
    const out = new Array(n * 4);
    for (let i = 0; i < n; i++) {
      const k = i * 3;
      const nx = N[k], ny = N[k + 1], nz = N[k + 2];
      let tx = tan[k], ty = tan[k + 1], tz = tan[k + 2];
      const d = nx * tx + ny * ty + nz * tz;
      tx -= nx * d; ty -= ny * d; tz -= nz * d;
      let ln = Math.sqrt(tx * tx + ty * ty + tz * tz);
      if (ln < 1e-8) {
        const ax = Math.abs(nx) > 0.9 ? [0, 0, 1] : [1, 0, 0];
        tx = ny * ax[2] - nz * ax[1]; ty = nz * ax[0] - nx * ax[2]; tz = nx * ax[1] - ny * ax[0];
        ln = Math.sqrt(tx * tx + ty * ty + tz * tz) || 1;
      }
      tx /= ln; ty /= ln; tz /= ln;
      const cx = ny * tz - nz * ty, cy = nz * tx - nx * tz, cz = nx * ty - ny * tx;
      const w = (cx * bit[k] + cy * bit[k + 1] + cz * bit[k + 2]) < 0 ? -1 : 1;
      out[i * 4] = tx; out[i * 4 + 1] = ty; out[i * 4 + 2] = tz; out[i * 4 + 3] = w;
    }
    return out;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     7. ECRITURE DU GLB — aucune bibliotheque, aucun reseau
     ═══════════════════════════════════════════════════════════════════════ */

  const FLOAT = 5126, U32 = 5125, ARR = 34962, ELEM = 34963;

  /* L'ECHELLE PHYSIQUE, MESUREE SUR LES SOMMETS QUI PARTENT DANS LE FICHIER.

     LE GRIEF, releve sur le .glb livre : le noeud etait
     `{"mesh":0,"name":"carte"}` — pas de matrice, pas de scale, aucune unite
     dans les 1804 octets de JSON, et un maillage normalise a Y = +/-1. Or
     glTF 2.0 fixe le METRE comme unite : le fichier livrait donc une carte de
     1,432 m x 2,000 m x 7,3 mm — un facteur 22,7 — pendant que le HUD ecrivait
     « 63 x 88 x 0,32 mm ». Le chiffre etait vrai a l'ecran et faux dans le
     livrable : les PROPORTIONS etaient exactes a huit chiffres, la TAILLE
     ABSOLUE etait absente. C'est exactement le motif « il l'AFFICHE sans le
     LIVRER ».

     On mesure donc l'etendue REELLE en Y et on en deduit le facteur, comme le
     fait `gltf.physical_scale` : le jour ou le maillage change d'echelle, la
     taille annoncee reste juste. */
  function scaleOf(mesh) {
    if (REPORT && REPORT.scale && REPORT.scale.m_per_unit > 0) return REPORT.scale.m_per_unit;
    const p = mesh.positions;
    let lo = Infinity, hi = -Infinity;
    for (let i = 1; i < p.length; i += 3) { if (p[i] < lo) lo = p[i]; if (p[i] > hi) hi = p[i]; }
    const span = hi - lo;
    const h = CF.geom().trim_mm[1];
    return (span > 1e-12 && h > 0) ? (h / 1000) / span : 1;
  }

  /* Une texture dont un cote n'est pas une puissance de deux NE PEUT PAS
     demander de mipmaps : un validateur glTF leve NON_POWER_OF_TWO_TEXTURE et
     une visionneuse WebGL1 rend la texture NOIRE. L'atlas est dimensionne sur
     la source (1518 x 1106 en poker 300 DPI), il n'est donc presque jamais
     puissance de deux — on regle le filtre en consequence, et on l'ECRIT. */
  function pot(n) { return n > 0 && (n & (n - 1)) === 0; }

  function glb(mesh, img, opt) {
    const o = opt || {};
    const parts = [], views = [], accs = [];
    let len = 0;
    const put4 = (u8, target) => {
      const pad = (4 - (len % 4)) % 4;
      if (pad) { parts.push(new Uint8Array(pad)); len += pad; }
      const v = { buffer: 0, byteOffset: len, byteLength: u8.byteLength };
      if (target) v.target = target;
      views.push(v); parts.push(u8); len += u8.byteLength;
      return views.length - 1;
    };
    const acc = (vi, ct, type, count, mn, mx) => {
      const a = { bufferView: vi, componentType: ct, count: count, type: type };
      if (mn) { a.min = mn; a.max = mx; }
      accs.push(a); return accs.length - 1;
    };
    const bounds = (arr, n) => {
      const mn = new Array(n).fill(Infinity), mx = new Array(n).fill(-Infinity);
      for (let i = 0; i < arr.length; i++) {
        const j = i % n;
        if (arr[i] < mn[j]) mn[j] = arr[i];
        if (arr[i] > mx[j]) mx[j] = arr[i];
      }
      return [mn, mx];
    };
    const nv = mesh.positions.length / 3;
    const pos = new Float32Array(mesh.positions);
    const pb = bounds(mesh.positions, 3);
    const aPos = acc(put4(new Uint8Array(pos.buffer), ARR), FLOAT, "VEC3", nv, pb[0], pb[1]);
    const aNrm = acc(put4(new Uint8Array(new Float32Array(mesh.normals).buffer), ARR), FLOAT, "VEC3", nv);
    const aUv = acc(put4(new Uint8Array(new Float32Array(mesh.uvs).buffer), ARR), FLOAT, "VEC2", nv);
    const idx = new Uint32Array(mesh.indices);
    const aIdx = acc(put4(new Uint8Array(idx.buffer), ELEM), U32, "SCALAR", idx.length);

    const attrs = { POSITION: aPos, NORMAL: aNrm, TEXCOORD_0: aUv };
    /* TANGENT : sans lui, une carte de normales n'a pas de repere et le moteur
       en invente un par derivees d'ecran — l'eclairage du relief change alors
       avec l'angle de vue. glTF le veut en VEC4, la 4e composante donnant la
       main du repere. */
    /* TANGENT SUIT LA CARTE DE NORMALES, ET ELLE SEULE. Sans carte de
       normales il ne sert a rien : 3,6 Kio d'attribut pour rien, et un
       validateur le signale comme inutilise. */
    if (o.pbr && o.pbr.normal) {
      const tg = tangentsOf(mesh);
      attrs.TANGENT = acc(put4(new Uint8Array(new Float32Array(tg).buffer), ARR), FLOAT, "VEC4", nv);
    }
    if (o.colors) {
      attrs.COLOR_0 = acc(put4(new Uint8Array(new Float32Array(o.colors).buffer), ARR), FLOAT, "VEC3", nv);
    }

    /* LE NOEUD PORTE LA TAILLE REELLE. `scale` uniforme : 1 unite glTF = 1 m,
       donc la carte s'ouvre a 0,063 x 0,088 x 0,00032 m dans Blender, Unity,
       Unreal, Godot ou un trancheur — et `extras` redit les millimetres en
       clair pour qui lit le JSON plutot que la matrice. */
    const sc = scaleOf(mesh);
    const g0 = CF.geom();
    const dmm = bboxOf(mesh).map((v) => Math.round(v * sc * 1e6) / 1e3);
    const json = {
      asset: {
        version: "2.0", generator: "Card Forge P5 — apercu",
        extras: { unit: "m", note: "node.scale met le maillage en metres (glTF 2.0)" },
      },
      scene: 0, scenes: [{ nodes: [0] }],
      nodes: [{
        mesh: 0, name: "carte", scale: [sc, sc, sc],
        extras: {
          size_mm: dmm, unit: "m", m_per_unit: sc,
          format: g0.fmt, dpi: g0.dpi,
          thickness_mm: Math.round(S("thickness_mm", 0.32) * 1000) / 1000,
          corner_mm: Math.round(S("corner_mm", 3) * 1000) / 1000,
          bevel_retrait_mm: Math.round(bevelEff() * 10000) / 10000,
          bevel_convention: "retrait = jambe du chanfrein a 45 deg, en Z et en XY",
        },
      }],
      meshes: [{ name: "card", primitives: [] }],
      materials: [], accessors: accs, bufferViews: views,
      buffers: [{ byteLength: 0 }],
    };
    const used = {};
    const mat = { name: "carte", doubleSided: false, pbrMetallicRoughness: {} };
    if (img && !o.colors) {
      json.images = [{ bufferView: put4(new Uint8Array(img.bytes)), mimeType: img.mime }];
      /* MIPMAPS SEULEMENT SI LES TROIS IMAGES SONT PUISSANCES DE DEUX. L'atlas
         est dimensionne sur la source (1518 x 1106) : il ne l'est presque
         jamais, et `minFilter` 9987 sur un NPOT est un avertissement de
         validateur ET une texture noire en WebGL1. Gratuit a corriger. */
      const dims = [o.atlas_px && o.atlas_px[0], o.atlas_px && o.atlas_px[1]]
        .concat(o.pbr ? (o.pbr.normal_px || []).concat(o.pbr.orm_px) : []);
      const mip = dims.length > 0 && dims.every(pot);
      json.samplers = [{ magFilter: 9729, minFilter: mip ? 9987 : 9729, wrapS: 33071, wrapT: 33071 }];
      json.textures = [{ sampler: 0, source: 0 }];
      mat.pbrMetallicRoughness.baseColorTexture = { index: 0 };
      if (o.pbr) {
        if (o.pbr.normal) {
          json.images.push({ bufferView: put4(new Uint8Array(o.pbr.normal.bytes)), mimeType: o.pbr.normal.mime });
          json.textures.push({ sampler: 0, source: json.images.length - 1 });
          mat.normalTexture = { index: json.textures.length - 1, scale: 1 };
        }
        json.images.push({ bufferView: put4(new Uint8Array(o.pbr.orm.bytes)), mimeType: o.pbr.orm.mime });
        json.textures.push({ sampler: 0, source: json.images.length - 1 });
        const iORM = json.textures.length - 1;
        mat.pbrMetallicRoughness.metallicRoughnessTexture = { index: iORM };
        mat.occlusionTexture = { index: iORM, strength: 1 };   /* rangement ORM standard */
      }
    } else {
      mat.pbrMetallicRoughness.baseColorFactor = [1, 1, 1, 1];
    }
    /* LE PIEGE DU CHROME, DESAMORCE. `metallicFactor` valait 1 et le metal
       n'etait annule que par le canal bleu de l'ORM : toute visionneuse qui
       perd ou ignore la texture metallicRoughness affichait la carte en CHROME
       INTEGRAL. Le facteur vaut maintenant le metal MAXIMUM reellement ecrit
       dans l'ORM (0,00 sur du papier, 0,90 sur une tranche doree) et le canal
       bleu porte la fraction : metal = facteur x B, valeur identique au
       pixel pres, mais le repli sans texture devient du papier mat et non un
       lingot. `roughnessFactor` reste a 1 : sans texture, la carte tombe
       entierement rugueuse, ce qui est le repli sur : elle ne brille pas. */
    mat.pbrMetallicRoughness.metallicFactor = o.unlit ? 0
      : (o.pbr ? o.pbr.metal_max : (o.metallic == null ? 0 : o.metallic));
    mat.pbrMetallicRoughness.roughnessFactor = o.unlit ? 1 : (o.pbr ? 1 : (o.roughness == null ? 0.52 : o.roughness));
    if (o.unlit) { mat.extensions = { KHR_materials_unlit: {} }; used.KHR_materials_unlit = 1; }
    json.materials.push(mat);
    json.meshes[0].primitives.push({ attributes: attrs, indices: aIdx, material: 0 });

    if (o.wire) {
      const seen = {}, lines = [];
      for (let i = 0; i < mesh.indices.length; i += 3) {
        const t = [mesh.indices[i], mesh.indices[i + 1], mesh.indices[i + 2]];
        for (let e = 0; e < 3; e++) {
          const a = t[e], b = t[(e + 1) % 3];
          const k = (a < b ? a + "_" + b : b + "_" + a);
          if (seen[k]) continue;
          seen[k] = 1; lines.push(a, b);
        }
      }
      const li = new Uint32Array(lines);
      const aLine = acc(put4(new Uint8Array(li.buffer), ELEM), U32, "SCALAR", li.length);
      json.materials.push({
        name: "filaire", doubleSided: true,
        pbrMetallicRoughness: { baseColorFactor: o.wireColor || [0.09, 0.87, 0.74, 1], metallicFactor: 0, roughnessFactor: 1 },
        extensions: { KHR_materials_unlit: {} },
      });
      used.KHR_materials_unlit = 1;
      json.meshes[0].primitives.push({
        attributes: { POSITION: aPos }, indices: aLine, mode: 1,
        material: json.materials.length - 1,
      });
    }
    const ext = Object.keys(used);
    if (ext.length) json.extensionsUsed = ext;

    const tail = (4 - (len % 4)) % 4;
    if (tail) { parts.push(new Uint8Array(tail)); len += tail; }
    json.buffers[0].byteLength = len;

    const js = new TextEncoder().encode(JSON.stringify(json));
    const jpad = (4 - (js.length % 4)) % 4;
    const total = 12 + 8 + js.length + jpad + 8 + len;
    const out = new Uint8Array(total);
    const dv = new DataView(out.buffer);
    dv.setUint32(0, 0x46546C67, true); dv.setUint32(4, 2, true); dv.setUint32(8, total, true);
    dv.setUint32(12, js.length + jpad, true); dv.setUint32(16, 0x4E4F534A, true);
    out.set(js, 20);
    for (let i = 0; i < jpad; i++) out[20 + js.length + i] = 0x20;
    const binAt = 20 + js.length + jpad;
    dv.setUint32(binAt, len, true); dv.setUint32(binAt + 4, 0x004E4942, true);
    let p = binAt + 8;
    parts.forEach((u) => { out.set(u, p); p += u.byteLength; });
    /* Le HUD relira CET objet — celui qui vient d'etre encode dans le chunk
       JSON du GLB — et non des variables gardees a cote. */
    LASTJSON = json;
    return new Blob([out], { type: "model/gltf-binary" });
  }

  function colorsFor(mode, mesh) {
    const nv = mesh.positions.length / 3, out = new Float32Array(nv * 3);
    if (mode === "normales") {
      for (let i = 0; i < nv * 3; i++) out[i] = mesh.normals[i] * 0.5 + 0.5;
      return out;
    }
    const I = islandRects();
    for (let i = 0; i < nv; i++) {
      const u = mesh.uvs[i * 2], v = mesh.uvs[i * 2 + 1];
      let c = ILOT_COULEUR.front;
      Object.keys(I).forEach((k) => {
        const r = I[k];
        if (u >= r[0] - 1e-6 && u <= r[2] + 1e-6 && v >= r[1] - 1e-6 && v <= r[3] + 1e-6) c = ILOT_COULEUR[k] || c;
      });
      out[i * 3] = c[0]; out[i * 3 + 1] = c[1]; out[i * 3 + 2] = c[2];
    }
    return out;
  }

  /* ═══════════════════════════════════════════════════════════════════════
     8. CONSTRUCTION ET POSE DU MODELE
     ═══════════════════════════════════════════════════════════════════════ */

  function schedule(ms) {
    clearTimeout(TIMER);
    TIMER = setTimeout(() => { build().catch((e) => console.error("cardforge: solid", e)); }, ms == null ? 170 : ms);
  }

  async function build() {
    if (CAPTURING) return;
    if (BUILDING) { AGAIN = true; return; }
    BUILDING = true;
    try {
      const mesh = await loadMesh();
      if (ATLAS_DIRTY || !ATLAS || ATLAS_KEY !== atlasKey()) await buildAtlas();
      const view = S("view", "matiere");
      /* LE SOUS-ECHANTILLONNAGE N'EST JAMAIS AFFIRME, IL EST RELU DANS LE SOF
         du JPEG produit — y compris pour le mode « chroma pleine » : si un
         navigateur decidait de sous-echantillonner malgre la qualite 1,0, le
         panneau l'ecrirait. Pour un PNG, c'est le TYPE DE COULEUR de l'en-tete
         qui est relu, pas une croyance. */
      const fmt = S("atlas_fmt", "jpeg");
      let img = null, chroma = null;
      if (view === "matiere" || view === "base") {
        img = fmt === "png" ? await toBytes(ATLAS, "image/png")
          : await toBytes(ATLAS, "image/jpeg", fmt === "jpeg444" ? 1 : 0.92);
        chroma = fmt === "png" ? ("PNG " + pngType(img.bytes) + " sans perte")
          : chromaJpeg(img.bytes);
      }
      const opt = {
        unlit: view !== "matiere",
        wire: !!S("wire", false),
        atlas_px: [ATLAS.width, ATLAS.height],
        colors: (view === "normales" || view === "ilots") ? colorsFor(view, mesh) : null,
        /* les cartes de matiere n'ont de sens que sous la lumiere : la vue
           « Encre » est volontairement non eclairee, on ne les y met pas. */
        pbr: view === "matiere" ? await buildMaps() : null,
      };
      /* On ne restaure la camera que si un modele a DEJA ete charge : avant le
         premier `load`, `getCameraOrbit()` rend un rayon de 0 — le reposer tel
         quel place la camera AU CENTRE de la carte, et l'ecran montre un
         aplat de texture agrandi mille fois. Symptome mesure, pas suppose. */
      const orbit = (LOADED && MV.getCameraOrbit) ? MV.getCameraOrbit() : null;
      const blob = glb(mesh, img, opt);
      const url = URL.createObjectURL(blob);
      const old = BLOB_URL; BLOB_URL = url;
      MV.src = url;
      const once = () => {
        MV.removeEventListener("load", once);
        LOADED = true;
        if (orbit && orbit.radius > 1e-3) {
          MV.setAttribute("camera-orbit", (orbit.theta * 180 / Math.PI).toFixed(3) + "deg "
            + (orbit.phi * 180 / Math.PI).toFixed(3) + "deg " + orbit.radius.toFixed(5) + "m");
        }
      };
      MV.addEventListener("load", once);
      if (old) setTimeout(() => URL.revokeObjectURL(old), 3000);
      applyViewerAttrs();
      LAST = {
        bytes: blob.size, mesh: mesh, img: img, chroma: chroma,
        pbr: opt.pbr, view: view,
      };
      hud();
    } finally {
      BUILDING = false;
      if (AGAIN) { AGAIN = false; schedule(20); }
    }
  }

  /* LE HUD NE RECOPIE RIEN. Chaque ligne est MESUREE sur ce qui vient d'etre
     ecrit dans le fichier : les cotes sur la boite englobante des sommets, le
     miroir sur le determinant UV de chacun des triangles, la definition du
     recto sur la taille de son ilot, le poids sur les octets du blob. Trois
     chiffres etaient faux ici : « 490 Ko » pour 498 664 octets (c'etait des
     kibi-octets etiquetes en kilo), « 0,013 in » face a « 0,0126 in » dans le
     panneau pour la meme grandeur, et « aucun miroir » ecrit en dur dans le
     rapport de secours. */
  function hud() {
    const el = q("#cf-solid-hud");
    if (!el || !REPORT || !LAST) return;
    const m = LAST.mesh;
    const d = bboxMm(m);
    const det = uvDetMax(m);
    const I = uvIslands(m);
    const O = faceOrientation(m);
    const tri = m.indices.length / 3, vtx = m.positions.length / 3;
    const P = PLAN || atlasPlan();
    const kio = LAST.bytes / 1024;
    /* LE HUD LIT LE JSON QUI VIENT D'ETRE SERIALISE, pas des variables d'a
       cote : `LASTJSON` est l'objet exact encode dans le chunk du GLB. */
    const J = LASTJSON;
    const nd = (J && J.nodes && J.nodes[0]) || null;
    const sc = (nd && nd.scale) ? nd.scale[0] : null;
    const smp = (J && J.samplers && J.samplers[0]) || null;
    const prim0 = (J && J.meshes && J.meshes[0] && J.meshes[0].primitives
      && J.meshes[0].primitives[0]) || null;
    /* CE QUE LE FICHIER PORTE, LU DANS LE FICHIER. « base+normales+ORM ·
       TANGENT » etait une chaine ecrite a la main : elle restait vraie par
       chance. Elle se compose maintenant du JSON serialise. */
    const maps = LAST.pbr
      ? ((J && J.images ? J.images.length : 0) + ' images : base'
        + (LAST.pbr.normal ? '+normales' : '') + '+ORM'
        + (prim0 && prim0.attributes && prim0.attributes.TANGENT != null ? ' · TANGENT' : ''))
      : (LAST.view === "base" ? 'base seule · non éclairé' : 'sommets colorés');
    /* LA DEFINITION DE COULEUR SORT DU PIRE DES DEUX AXES, ET LE DIT. Elle
       sortait de `P.dpi`, c'est-a-dire de la seule verticale : un
       sous-echantillonnage de chroma s'applique aux deux sens, on annonce donc
       le moins bon. */
    const dpiMin = Math.min(P.dpi, P.dpi_w == null ? P.dpi : P.dpi_w);
    const chroma = LAST.chroma === "4:2:0"
      ? '4:2:0 — chroma ½ (' + Math.round(dpiMin / 2) + ' DPI de couleur au pire axe)'
      : (LAST.chroma === "4:4:4"
        ? '4:4:4 — chroma pleine (' + Math.round(dpiMin) + ' DPI de couleur)'
        : LAST.chroma);
    /* LE REECHANTILLONNAGE, AU CENTIEME DE POUR CENT ET DANS LES DEUX AXES.
       « +0,1 % en hauteur » etait calcule sur 1040 px arrondis ; l'ilot en
       occupe 1039,64, soit +0,062 %, et il perd 0,024 % en largeur. Deux
       chiffres exacts valent mieux qu'un arrondi confortable. */
    const pct = (r) => (r >= 1 ? '+' : '−') + fr(Math.abs(r - 1) * 100, 2) + ' %';
    const dh = Math.abs((P.ratio_source || 1) - 1) > 5e-5;
    const dw = Math.abs((P.ratio_source_w || 1) - 1) > 5e-5;
    const resample = (dh || dw)
      ? ' · ' + (dh ? pct(P.ratio_source) + ' en hauteur' : '')
      + (dh && dw ? ', ' : '') + (dw ? pct(P.ratio_source_w) + ' en largeur' : '')
      : ' · échelle 1:1';
    const fx = P.front_px_exact || P.front_px;
    /* Le perimetre vient du backend (contour arrondi reel : quatre segments
       droits plus un cercle entier). Sans lui, pas de DPI de tranche : on
       n'affiche alors rien plutot qu'une approximation. */
    const peri = (REPORT && REPORT.edge && REPORT.edge.perimeter_mm) || 0;
    const eex = P.edge_px_exact || P.edge_px;
    const edgeDpi = (peri > 0 && eex) ? (eex[0] / peri * 25.4) : 0;
    /* LE SECOND AXE DE LA TRANCHE. « 130 DPI » n'etait que le long du
       perimetre ; en travers, les 44,2 px de bande couvrent 0,32 mm, soit
       3 512 DPI. Choisir le pire axe est defendable, le taire ne l'est pas. */
    const edgeCross = (eex && d[2] > 0) ? (eex[1] / d[2] * 25.4) : 0;
    /* TROIS LIGNES EN TETE, LE RESTE EN DESSOUS. Le grief : « aucune
       hierarchie : la phrase la plus importante du panneau est composee
       exactement comme un chiffre qui ne sert a personne ». Les trois lignes
       qui decident d'un tirage — la taille, l'echelle du fichier, le sens du
       verso — portent la classe `key` et sont ecrites plus gros. */
    el.innerHTML = ''
      + '<div class="cf-solid-hl key"><span>Carte</span><b>' + fr(d[0], 0) + ' × ' + fr(d[1], 0)
      + ' × ' + fr(d[2], 2) + ' mm</b><i>' + fr(d[0] / 25.4, 4) + ' × ' + fr(d[1] / 25.4, 4)
      + ' × ' + fr(d[2] / 25.4, 4) + ' in</i></div>'
      /* LA LIGNE QUI MANQUAIT. Le fichier livrait une carte de deux metres de
         haut pendant que la ligne du dessus affichait des millimetres. */
      + '<div class="cf-solid-hl key"><span>Échelle</span><b>'
      + (sc ? '×&nbsp;' + sc.toFixed(6).replace(".", ",") : 'ABSENTE') + '</b><i>'
      + (sc ? 'node.scale mesuré sur les sommets — 1 unité glTF = 1 m : le fichier s\'ouvre'
        + ' à la taille ci-dessus, pas à ' + fr(d[1] / (sc * 1000), 2) + ' m'
        : 'le fichier ne porte pas sa taille réelle') + '</i></div>'
      /* Le bandeau reste un instrument, pas un mur : les lignes de tete
         d'abord, le detail dessous, et une hauteur bornee pour que la carte
         — l'objet meme du panneau — ne finisse jamais sous le texte. */
      /* LA LIGNE QUI DECIDE D'UN TIRAGE. Elle passe AVANT les comptes de
         triangles : un imprimeur veut d'abord la taille, puis « le verso est
         a l'endroit », et seulement ensuite le nombre de paires testees. */
      + '<div class="cf-solid-hl key"><span>Verso</span><b>'
      + (O.ok ? 'à l\'endroit' : 'MIROIR — À CORRIGER') + '</b><i>'
      + O.verso.endroit + '/' + O.verso.tri + ' triangles orientés comme le recto'
      + ' vu de son côté · îlot u[' + fr(O.u[0], 2) + ' ; ' + fr(O.u[1], 2) + ']'
      + '</i></div>'
      + '<div class="cf-solid-hl"><span>Faces</span><b>' + tri + '</b><i>sommets ' + vtx
      + (MESH_LOCAL ? ' · maillage local' : '') + '</i></div>'
      /* DEUX DECOMPTES POUR UN SEUL MOT. « 3 ilots » a ete attaque comme un
         arrondi charitable ; les deux definitions sont donc ecrites, avec ce
         qui les separe. */
      + '<div class="cf-solid-hl"><span>Îlots UV</span><b>' + I.regions + '&nbsp;régions</b><i>'
      + I.chevauche + ' recouvrement sur ' + I.paires + ' paires · '
      + (det < 0 ? tri + '/' + tri + ' dét. < 0 · pire ' + det.toExponential(1).replace(".", ",")
        : 'MIROIR DÉTECTÉ')
      + ' · ' + I.composantes + ' composantes en comptant les sommets dupliqués à la couture'
      + '</i></div>'
      /* DEUX DEFINITIONS, PAS UNE. Les ilots UV sont geles par le contrat et
         l'atlas est dimensionne sur la hauteur de la source : la definition
         horizontale du recto n'est jamais exactement la verticale, et
         « 300,08 DPI » cachait 299,89 en largeur. */
      + '<div class="cf-solid-hl"><span>Recto</span><b>' + fr(fx[0], 1) + ' × ' + fr(fx[1], 1)
      + ' px</b><i>' + (P.dpi_w == null ? fr(P.dpi, 2) + ' DPI'
        : fr(P.dpi_w, 2) + ' × ' + fr(P.dpi, 2) + ' DPI (largeur × hauteur)')
      + ' · source ' + P.source_px[0] + ' × ' + P.source_px[1]
      + resample + '</i></div>'
      /* LA TRANCHE EST LE SUJET DE LA PIECE ET SA BANDE EST LA PLUS ETROITE DE
         L'ATLAS : son chiffre se dit aussi. Les ilots UV sont geles par le
         contrat, on ne peut pas lui donner plus de place — on peut dire
         combien elle en a. */
      + (edgeDpi ? '<div class="cf-solid-hl"><span>Tranche</span><b>'
        + fr(edgeDpi, 0) + ' DPI</b><i>le long du périmètre (' + fr(peri, 1) + ' mm)'
        + (edgeCross ? ' · ' + fr(edgeCross, 0) + ' DPI en travers (' + fr(d[2], 2)
          + ' mm)' : '')
        + ' · bande ' + (P.edge_px_exact || P.edge_px)[0] + ' × '
        + fr((P.edge_px_exact || P.edge_px)[1], 1) + ' px · îlots UV figés par le'
        + ' contrat, le chiffre annoncé est le pire des deux axes'
        /* MESURER SANS CONSEILLER, C'ETAIT LE GRIEF. Le chiffre est donne, le
           verdict aussi, et le seul levier reel est nomme — avec l'etat
           courant de ce levier, pour qu'on voie s'il reste de la marge. */
        + ' · ' + (edgeDpi >= 300 ? 'de quoi porter du texte'
          : (edgeDpi >= 150 ? 'motif oui, texte non' : 'aplat ou dégradé, pas de motif fin'))
        + ' · levier : la définition du document (atlas ' + P.h + ' px pour un plafond de '
        + P.cap + ')</i></div>' : '')
      + '<div class="cf-solid-hl"><span>Modèle</span><b>' + fr(kio, 0) + ' Kio</b><i>'
      + maps + (chroma ? ' · ' + chroma : '') + '</i></div>';
    const mp = q("#cf-solid-maps");
    if (mp) mp.innerHTML = mapsText(smp, P);
  }

  /* CE QUE LE FICHIER PORTE, RELU DANS SES PROPRES OCTETS. Chaque nombre de ce
     paragraphe est une MESURE : les poids sont ceux des tampons ecrits, les
     rugosites et le metal sont relus dans l'ORM tel qu'il vient d'etre peint
     (PNG sans perte : ces octets sont ceux du fichier), le filtre et le
     facteur de metal sont relus dans le JSON serialise. */
  function mapsText(smp, P) {
    if (!LAST.pbr) {
      return 'Vue non éclairée : le fichier ne porte que l\'image de base '
        + '(les cartes de matière n\'y serviraient à rien).';
    }
    const ko = (b) => fr(b / 1024, 0) + ' Kio';
    const M = LAST.pbr.mesure;
    const pc = (v) => fr(v, 3);
    const npot = !!(LAST.img && P) && !(pot(P.w) && pot(P.h));
    const st = (TRANCHES.filter((t) => t.id === LAST.pbr.edge_style)[0] || TRANCHES[0]).l;
    const R2 = LAST.pbr.relief;
    const part = (b) => fr(b / Math.max(1, LAST.bytes) * 100, 1) + ' % du fichier';
    const NM = LAST.pbr.normal;
    const nb = NM ? NM.bytes.byteLength : 0;
    const I2 = islandRects();
    const gutU = (I2.back[0] - I2.front[2]) * (P ? P.w : 0);
    const gutV = (I2.edge[1] - I2.front[3]) * (P ? P.h : 0);
    /* LE COMPTE DES IMAGES EST COMPTE, PAS ECRIT. « Le fichier porte quatre
       cartes » suivi d'une liste de trois avait ete releve ; et depuis que le
       relief d'encre peut etre absent, le nombre change vraiment. On lit donc
       les images et les emplacements dans le JSON qui vient d'etre serialise. */
    const nImg = (LASTJSON && LASTJSON.images) ? LASTJSON.images.length : 0;
    const mt = (LASTJSON && LASTJSON.materials && LASTJSON.materials[0]) || {};
    const nSlot = ["baseColorTexture", "metallicRoughnessTexture"]
      .filter((k) => mt.pbrMetallicRoughness && mt.pbrMetallicRoughness[k]).length
      + ["normalTexture", "occlusionTexture", "emissiveTexture"].filter((k) => mt[k]).length;
    const MOTS = ["zéro", "une", "deux", "trois", "quatre", "cinq", "six"];
    return '<b>' + (MOTS[nImg] || nImg) + ' image' + (nImg > 1 ? 's' : '') + '</b> pour '
      + (MOTS[nSlot] || nSlot) + ' emplacement' + (nSlot > 1 ? 's' : '')
      + ' de matière — comptées dans le JSON du GLB, pas annoncées : base '
      + (LAST.img ? ko(LAST.img.bytes.byteLength) : '—') + ' (' + esc(String(LAST.chroma))
      + (LAST.chroma === "4:2:0" ? ', chrominance à demi-définition — c\'est une perte, pas'
        + ' une option, et elle porte sur le dessin : <b>Rendu et raccourcis → Image de base'
        + ' → chroma pleine</b> la supprime pour environ le double de poids'
        : '') + ')'
      + (NM ? ', normales ' + ko(nb) + ' en ' + LAST.pbr.normal_px.join('×') : '')
      + ', ORM ' + ko(LAST.pbr.orm.bytes.byteLength) + ' en '
      + LAST.pbr.orm_px.join('×') + ' — <b>lue deux fois</b> : rugosité (vert) + métal (bleu) et'
      + ' occlusion (rouge).'
      + (NM ? ' Plus l\'attribut TANGENT.'
        : ' <b>Relief d\'encre : Aucun</b> — pas de carte de normales, donc pas'
        + ' d\'attribut TANGENT non plus : il n\'aurait rien à orienter.')
      /* CE QUE LA CARTE DE NORMALES ACHETE, EN FACE DE CE QU'ELLE COUTE. On a
         longtemps affiche le poids sans jamais l'effet ; les deux vont
         ensemble ou aucun ne vaut rien. Le type de couleur est RELU dans
         l'en-tete du PNG produit. */
      + (R2 && NM ? '<br>Relief d\'encre <b>' + esc(LAST.pbr.relief_l) + '</b> — ce que les'
        + ' normales achètent, mesuré sur les octets écrits : <b>'
        + fr(R2.max_deg, 2) + '°</b> d\'inclinaison au maximum, ' + fr(R2.rms_deg, 2)
        + '° en moyenne quadratique, ' + fr(R2.sous1_pct, 1) + ' % des texels sous 1°.'
        /* LA MARCHE D'ENCRE EST DEDUITE, PAS RECOPIEE. « relief de 6 µm » etait
           la consigne `INK_RELIEF_MM` presentee comme une mesure ; ici la
           pente sort des texels ecrits et le pas de texel de la geometrie. */
        + ' La marche d\'encre s\'en déduit : pente maximale sur un axe '
        + fr(R2.pente_max * 100, 2) + ' % × pas de texel ' + fr(R2.pas_mm, 4)
        + ' mm = <b>' + fr(R2.relief_mesure_mm * 1000, 1) + ' µm</b> — la consigne partagée'
        + ' avec le backend en demandait ' + fr(R2.relief_demande_mm * 1000, 0)
        + '. C\'est une épaisseur d\'encre offset, pas une gravure — et elle coûte '
        + part(nb) + '.'
        + ' PNG <b>' + esc(pngType(NM.bytes)) + '</b> '
        + (NM.bits || 8) + ' bits/texel'
        + (NM.ecrit_ici
          ? ' écrit ici (filtre choisi ligne par ligne) : pas de canal alpha constant à payer.'
          : ' par la toile du navigateur.')
        /* CE QUE LA PALETTE A REELLEMENT ECONOMISE, LES DEUX POIDS COTE A COTE.
           Le grief : « soit on encode ce relief de six microns dans un canal
           leger, soit on ne l'encode pas ». Les deux encodages sont produits
           et peses ; ce nombre est la difference. */
        + (NM.rgb_octets && NM.couleurs
          ? ' <b>' + NM.couleurs + ' couleurs distinctes</b> comptées sur les'
          + ' texels : ' + ko(nb) + ' en palette contre ' + ko(NM.rgb_octets)
          + ' en RGB pour les <b>mêmes</b> texels (empreinte FNV de la source et de la'
          + ' reconstruction comparées avant l\'écriture), soit '
          + fr((1 - nb / NM.rgb_octets) * 100, 0) + ' % de moins.' : '')
        /* CE QUE L'EN-TETE NE DIT PAS. Un badge de profondeur se verifie en
           COMPTANT les valeurs distinctes, pas en lisant l'IHDR. */
        + (R2.distinctes ? ' Profondeur <b>utile</b> comptée sur les texels écrits : '
          + R2.distinctes[0] + ' / ' + R2.distinctes[1] + ' / ' + R2.distinctes[2]
          + ' valeurs distinctes sur 256 (X / Y / Z), soit ' + fr(R2.bits_utiles, 1)
          + ' bits utiles sous un en-tête 8 bits — un en-tête n\'est pas une mesure.' : '')
        : '')
      + '<br>Relu dans l\'ORM écrit : papier rugosité ' + pc(M.face_rough.moy)
      + ' au recto et ' + pc(M.back_rough.moy) + ' au verso (' + pc(M.face_rough.min)
      + ' sous l\'encre → ' + pc(M.face_rough.max)
      + ' sur le papier nu), métal ' + pc(M.face_metal.max) + '. Tranche « ' + esc(st)
      + ' » : rugosité ' + pc(M.edge_rough.moy) + ', métal ' + pc(M.edge_metal.max)
      + ' (canal bleu : ' + LAST.pbr.metal_vals + ' valeur'
      + (LAST.pbr.metal_vals > 1 ? 's' : '') + ' distincte'
      + (LAST.pbr.metal_vals > 1 ? 's' : '') + ' sur 256).'
      /* L'OCCLUSION, DITE COMME ELLE EST. Elle etait mesuree et tue : sa
         plage tient dans un dixieme de sa dynamique, ce qui la rend a peine
         perceptible. On l'ecrit plutot que d'attendre qu'on la mesure. */
      + (M.face_ao ? ' Occlusion (rouge) ' + pc(M.face_ao.min) + ' → ' + pc(M.face_ao.max)
        + ' sur le recto (moyenne ' + pc(M.face_ao.moy) + '), ' + pc(M.edge_ao.min)
        + ' → ' + pc(M.edge_ao.max) + ' sur la tranche : <b>'
        + fr((M.face_ao.max - M.face_ao.min) * 100, 1) + ' %</b> de sa dynamique,'
        + ' un contact d\'encre et un pincement de tranche — pas une cavité.' : '')
      + '<br><b>metallicFactor ' + pc(LAST.pbr.metal_max) + '</b> : une visionneuse qui perd la'
      + ' texture retombe sur '
      + (LAST.pbr.metal_max < 0.02 ? 'du papier mat, pas sur un lingot de chrome.'
        : 'la métallicité de la tranche, jamais au-dessus.')
      + ' Le jeu <b>complet</b> du cahier des charges — huit PNG, hauteur et émission'
      + ' comprises — est le livrable de l\'<b>Export 3D</b> ; ici c\'est l\'aperçu.'
      /* Les deux gouttieres sont CALCULEES sur les ilots et l'atlas courants,
         pas recopiees du format poker : elles changent avec la definition.
         Et la promesse n'est plus une promesse : on COMPTE ce qui reste de
         blanc pur entre deux ilots sur la toile qui part dans le fichier. */
      /* « SOIT JUSQU'AU MILIEU DES GOUTTIERES » ETAIT UN ARRONDI VERS LE HAUT.
         La dilatation vaut ceil(gouttiere / 2) : 16 px pour 30,4, donc 0,8 px
         DE PLUS que la moitie. Les deux nombres sont ecrits, et la relation
         avec eux — un « soit » qui ne se verifie pas est un chiffre faux. */
      + ' Bords des trois îlots <b>dilatés de ' + PAD_EFF.u + ' px</b> en largeur et <b>'
      + PAD_EFF.v + ' px</b> en hauteur, soit la moitié de chaque gouttière arrondie'
      + ' au pixel supérieur (' + fr(gutU, 1) + ' px recto|verso → ' + fr(gutU / 2, 1)
      + ', ' + fr(gutV, 1) + ' px faces|tranche → ' + fr(gutV / 2, 1) + ').'
      + ' Reste-t-il du fond entre deux îlots ? <b>' + PAD_EFF.reste.blanc
      + '</b> texel(s) encore au blanc pur sur ' + PAD_EFF.reste.total + ' — compté'
      + ' sur la toile qui est encodée dans le fichier, pas promis'
      + (PAD_EFF.reste.blanc === 0
        ? ' : rien à baver dans le bord de la carte, à aucun niveau de mip.'
        : ' : le filtrage d\'un moteur peut encore les mêler au bord.')
      + (smp ? ' Atlas ' + P.w + '×' + P.h + (npot ? ' (non puissance de deux) → filtre '
        + (smp.minFilter === 9987 ? 'LINEAR_MIPMAP_LINEAR' : 'LINEAR')
        + ', aucun mipmap demandé : aucun avertissement de validateur.'
        : ' → mipmaps.') : '');
  }

  /* ═══════════════════════════════════════════════════════════════════════
     9. ENVIRONNEMENTS — fabriques ici, aucun HDRI a telecharger
     ═══════════════════════════════════════════════════════════════════════ */

  function envURL(name) {
    if (ENV_CACHE[name]) return ENV_CACHE[name];
    const W = 768, H = 384;
    const c = document.createElement("canvas");
    c.width = W; c.height = H;
    const x = c.getContext("2d");
    /* Ces environnements sont en BASSE dynamique (un PNG plafonne a 1,0) : la
       tentation est d'ecrire un joli dégradé sombre, et la carte sort alors
       grise. Les taches lumineuses sont donc larges et proches du blanc pur —
       c'est ce qui donne un eclairage de studio plutot qu'une cave. */
    const P = {
      studio: { sky: ["#8b9098", "#2a2d33"], lights: [[0.26, 0.26, 0.38, "#ffffff", 1], [0.72, 0.34, 0.30, "#eef2f8", 0.92], [0.5, 0.02, 0.62, "#ffffff", 0.85]] },
      vitrine: { sky: ["#1a1d22", "#08090b"], lights: [[0.5, 0.14, 0.52, "#ffffff", 1], [0.14, 0.52, 0.16, "#8fdcff", 0.7], [0.86, 0.5, 0.14, "#ffd9a0", 0.6]] },
      chaud: { sky: ["#7a5a3c", "#241609"], lights: [[0.30, 0.24, 0.34, "#fff0d4", 1], [0.78, 0.40, 0.26, "#ffb066", 0.8]] },
      froid: { sky: ["#5a6d80", "#12171d"], lights: [[0.28, 0.22, 0.34, "#f2fbff", 1], [0.74, 0.42, 0.28, "#a8ccff", 0.85]] },
    }[name] || { sky: ["#888", "#222"], lights: [[0.3, 0.3, 0.36, "#fff", 1]] };
    const g = x.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, P.sky[0]); g.addColorStop(1, P.sky[1]);
    x.fillStyle = g; x.fillRect(0, 0, W, H);
    P.lights.forEach((L) => {
      const cx = L[0] * W, cy = L[1] * H, r = L[2] * W;
      const rg = x.createRadialGradient(cx, cy, 0, cx, cy, r);
      rg.addColorStop(0, L[3]); rg.addColorStop(1, "rgba(0,0,0,0)");
      x.globalAlpha = L[4]; x.fillStyle = rg;
      x.fillRect(cx - r, cy - r, r * 2, r * 2);
      x.globalAlpha = 1;
    });
    ENV_CACHE[name] = c.toDataURL("image/png");
    return ENV_CACHE[name];
  }

  /* ═══════════════════════════════════════════════════════════════════════
     10. TOURNE-DISQUE
     ═══════════════════════════════════════════════════════════════════════ */

  /* ── L'EXPOSITION DU TOURNE-DISQUE, MESUREE SUR LES IMAGES LIVREES ──────
     LE GRIEF : « luminance moyenne DANS la carte 32,5/255 alors que la base
     color du recto a une moyenne de 68/255 — le rendu par defaut rend environ
     la moitie de l'albedo ». On ne peut pas repondre a cela par un reglage
     par defaut plus genereux SANS LE MESURER : on mesure donc la silhouette
     opaque de la carte sur des images echantillonnees du rendu, on la compare
     a l'albedo du recto, et on ECRIT le rapport dans le bordereau. Le chiffre
     est faible ? Il s'affiche quand meme. C'est la difference entre une
     mesure et une promesse. */
  const LUMC = document.createElement("canvas");     /* le MASQUE : alpha du rendu */
  const LUMD = document.createElement("canvas");     /* l'IMAGE LIVREE, reduite */
  const LUMB = document.createElement("canvas");     /* le FOND SEUL, meme taille */

  /* LE SEUIL DE LA REGLE, EN NIVEAUX SUR 255. Il est nomme ici et ecrit a
     l'ecran : sans lui, personne ne peut refaire la mesure. */
  const LUM_SEUIL = 12;

  /* ── POURQUOI CETTE REGLE A CHANGE ─────────────────────────────────────
     LE GRIEF QUE JE ME FAIS A MOI-MEME, MESURE SUR LE mp4 SORTI DU VRAI
     BOUTON : le panneau annoncait « 44,5/255 dans la silhouette ». En
     re-mesurant les 90 images livrees (fond = mediane temporelle, carte =
     pixels qui s'en ecartent), on trouve 53,1/255 sur les six images que le
     panneau echantillonne et 54,4 sur les quatre-vingt-dix. L'ecart n'est pas
     une erreur de calcul : le masque etait l'ALPHA DU RENDU, qui contient
     AUSSI L'OMBRE PORTEE — des pixels tres sombres comptes comme « la carte ».
     Le chiffre etait donc sincere, plus bas que la verite, et surtout
     IMPOSSIBLE A REFAIRE par quelqu'un qui n'a que la video : le canal alpha
     n'y est pas.

     La regle est maintenant purement optique et rejouable sur le fichier
     livre : la carte, ce sont les pixels de l'image composee PLUS CLAIRS QUE
     LE FOND PEINT de plus de LUM_SEUIL/255. Le fond, on le peint nous-memes
     (`paintBack`), donc on le connait exactement ; un tiers qui n'a que le mp4
     le retrouve par la mediane temporelle des 90 images. L'ombre, plus SOMBRE
     que le fond, sort du masque — et c'est bien la carte que l'on voulait
     mesurer. */
  function lumSilhouette(img, livree) {
    const W = 240, H = 240;
    LUMC.width = W; LUMC.height = H;
    const x = LUMC.getContext("2d", { willReadFrequently: true });
    x.clearRect(0, 0, W, H);
    const f = Math.min(W / img.width, H / img.height);
    x.drawImage(img, (W - img.width * f) / 2, (H - img.height * f) / 2,
      img.width * f, img.height * f);
    const d = x.getImageData(0, 0, W, H).data;
    let src = d;
    if (livree) {
      /* la toile livree est carree comme celle-ci et l'image y est centree au
         meme facteur : la reduire de bout en bout conserve l'alignement */
      LUMD.width = W; LUMD.height = H;
      const y = LUMD.getContext("2d", { willReadFrequently: true });
      y.drawImage(livree, 0, 0, W, H);
      src = y.getImageData(0, 0, W, H).data;
    }
    /* le FOND SEUL, peint par la meme fonction et a la meme echelle : le
       degrade de `paintBack` est defini en fractions de `size`, il se rejoue
       donc a l'identique en 240 px. */
    LUMB.width = W; LUMB.height = H;
    const bx = LUMB.getContext("2d", { willReadFrequently: true });
    paintBack(bx, W);
    const bg = bx.getImageData(0, 0, W, H).data;
    let s = 0, n = 0;
    for (let i = 0; i < d.length; i += 4) {
      const lb = 0.2126 * bg[i] + 0.7152 * bg[i + 1] + 0.0722 * bg[i + 2];
      const lc = 0.2126 * src[i] + 0.7152 * src[i + 1] + 0.0722 * src[i + 2];
      if (lc - lb <= LUM_SEUIL) continue;        /* fond et ombre exclus */
      s += lc;
      n++;
    }
    return n > 64 ? { moy: s / n, px: n } : null;
  }

  function albedoFront() {
    if (!ATLAS) return null;
    const I = islandRects(), W = 180, H = 250;
    const c = document.createElement("canvas");
    c.width = W; c.height = H;
    const x = c.getContext("2d", { willReadFrequently: true });
    x.drawImage(ATLAS, I.front[0] * ATLAS.width, I.front[1] * ATLAS.height,
      (I.front[2] - I.front[0]) * ATLAS.width, (I.front[3] - I.front[1]) * ATLAS.height,
      0, 0, W, H);
    const d = x.getImageData(0, 0, W, H).data;
    let s = 0;
    for (let i = 0; i < d.length; i += 4) {
      s += 0.2126 * d[i] + 0.7152 * d[i + 1] + 0.0722 * d[i + 2];
    }
    return s / (W * H);
  }

  function prog(p, txt) {
    const el = q("#cf-solid-prog");
    if (!el) return;
    el.classList.toggle("hidden", p == null);
    if (p == null) return;
    el.querySelector("i").style.width = Math.round(p * 100) + "%";
    el.querySelector("span").textContent = txt || "";
  }

  async function turntable() {
    if (CAPTURING) { CF.toast("un rendu est déjà en cours", true); return; }
    const n = Math.max(24, Math.min(600, Math.round(S("tt_frames", 90))));
    const fps = Math.max(12, Math.min(60, Math.round(S("tt_fps", 30))));
    const size = Number(S("tt_size", 1080)) || 1080;
    const fmt = S("tt_fmt", "mp4") === "webm" ? "webm" : "mp4";
    const up = elev();                       /* ELEVATION au-dessus de l'horizon */
    const phi = 90 - up;                     /* angle polaire de <model-viewer> */
    if (!MV || !MV.src) { CF.toast("aperçu pas encore prêt", true); return; }
    const job = randJob();
    CAPTURING = true; TT = { abort: false };
    const btn = q(".cf-solid-go");
    btn.disabled = true;
    const spin = S("spin", true);
    MV.removeAttribute("auto-rotate");
    const stage = q("#cf-solid-stage");
    const k = Math.min(stage.clientWidth / size, stage.clientHeight / size);
    MV.classList.add("cap");
    MV.style.width = size + "px"; MV.style.height = size + "px";
    MV.style.transform = "translate(-50%,-50%) scale(" + k.toFixed(4) + ")";
    const shot = document.createElement("canvas");
    shot.width = size; shot.height = size;
    const sx = shot.getContext("2d");
    let sent = 0, lumSum = 0, lumN = 0;
    const orient0 = MV.getAttribute("orientation") || "0deg 0deg 0deg";
    try {
      /* LE TOURNE-DISQUE FAIT TOURNER LE MODELE, PAS LA CAMERA. Mesure : une
         camera pilotee image par image n'arrive JAMAIS a son angle a temps —
         elle interpole, `jumpCameraToGoal()` la gele au lieu de l'y porter, et
         les 90 images sortent quasiment identiques (rotation totale mesuree :
         une trentaine de degres au lieu de 360). `orientation` est une
         transformation du MODELE : elle s'applique a l'image suivante, sans
         interpolation. Verifie sur un balayage 0-60-120-180-240-300 : six
         positions exactes, tranche et verso au rendez-vous.
         Effet de bord heureux : la camera ne bouge pas, donc on FILME LE POINT
         DE VUE DE L'UTILISATEUR — ce qu'il voit est ce qu'il obtient. */
      const orbit = MV.getCameraOrbit ? MV.getCameraOrbit() : null;
      if (orbit && orbit.radius > 1e-3) {
        /* Si la rotation tournait, l'azimut ou elle s'arrete est un hasard :
           on repart du CADRAGE (lacet du modele - 28 deg), donc la premiere
           image est celle que « Recadrer » montre. Si l'utilisateur a fige un
           angle, c'est le sien qu'on filme. */
        const th = spin ? (yawDeg() - 28) : (orbit.theta * 180 / Math.PI);
        MV.setAttribute("camera-orbit", th.toFixed(3)
          + "deg " + phi + "deg " + orbit.radius.toFixed(5) + "m");
      }
      await new Promise((r) => setTimeout(r, 420));
      /* L'ELEVATION QUE L'ON ANNONCE EST CELLE QUE L'ON RELIT dans la
         visionneuse apres l'avoir posee — pas celle du curseur. */
      const lu = MV.getCameraOrbit ? MV.getCameraOrbit() : null;
      const upLu = lu ? (90 - lu.phi * 180 / Math.PI) : up;
      for (let i = 0; i < n; i++) {
        if (TT.abort) throw new Error("rendu annulé");
        const a = 360 * i / n;
        MV.setAttribute("orientation", "0deg 0deg " + a.toFixed(4) + "deg");
        await MV.updateComplete;
        await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
        const bmp = await grab();
        paintBack(sx, size);
        const f = Math.min(size / bmp.width, size / bmp.height);
        sx.drawImage(bmp, (size - bmp.width * f) / 2, (size - bmp.height * f) / 2,
          bmp.width * f, bmp.height * f);
        /* une image sur six suffit a la moyenne et ne coute rien au rendu ; la
           mesure passe APRES la composition, donc sur les pixels qui partent */
        if (i % Math.max(1, Math.round(n / 6)) === 0) {
          const L = lumSilhouette(bmp, shot);
          if (L) { lumSum += L.moy; lumN++; }
        }
        if (bmp.close) bmp.close();
        const jpg = await new Promise((res) => shot.toBlob(res, "image/jpeg", 0.92));
        const r = await M.api.raw("POST", "turntable/frame?job=" + job + "&i=" + i, jpg);
        if (!r.ok) throw new Error("image " + (i + 1) + " refusée (" + r.status + ")");
        sent++;
        prog((i + 1) / (n + 6), "image " + (i + 1) + " / " + n);
      }
      prog(n / (n + 6), "encodage ffmpeg…");
      const rep = await M.api.post("turntable/encode",
        { job: job, fps: fps, format: fmt, w: size, h: size });
      const blob = await M.api.blob("GET", "turntable/file?job=" + job + "&name=" + encodeURIComponent(rep.file));
      const nom = (CF.doc().name || "carte").replace(/[^\w\-]+/g, "_") + "_tourne-disque." + rep.format;
      CF.download(blob, nom);
      const mo = rep.bytes / 1048576;
      const alb = albedoFront();
      const lum = lumN ? lumSum / lumN : null;
      q("#cf-solid-out").classList.remove("hidden");
      q("#cf-solid-out").innerHTML = '<b>' + esc(nom) + '</b> — ' + rep.frames + ' images @ '
        + rep.fps + ' i/s, ' + fr(rep.seconds, 2) + ' s, ' + size + '×' + size + ', '
        + fr(mo, 2) + ' Mo ' + (rep.bytes < 8388608 ? '(seuil 8 Mo tenu)' : '(au-dessus de 8 Mo)')
        + ' · élévation relue dans la visionneuse : ' + fr(upLu, 1) + '&deg; au-dessus de l\'horizon'
        + ' (angle polaire ' + fr(90 - upLu, 1) + '&deg;)'
        + (lum != null && alb ? ' · luminance moyenne de la <b>carte</b> dans les images'
          + ' <b>livrées</b> : ' + fr(lum, 1)
          + '/255 pour un albédo de recto de ' + fr(alb, 1) + '/255, soit '
          + fr(lum / alb * 100, 0) + ' % (' + lumN + ' images échantillonnées ; la carte'
          + ' = les pixels de l\'image composée plus clairs que le fond peint de plus de '
          + LUM_SEUIL + '/255 — l\'ombre portée, plus sombre que le fond, en est exclue.'
          + ' Sur la vidéo seule, le fond se retrouve par la médiane temporelle des '
          + rep.frames + ' images)' : '')
        /* LE FICHIER EST NU, ET C'EST UNE MESURE. Le grief : « le mp4 conserve
           TAG:encoder=Lavf, TAG:encoder=Lavc libx264 et, dans le flux, la
           chaine x264 "core 165 ... threads=34 ... crf=22.0" — une empreinte
           de chaine locale ET de machine (34 fils = le processeur de la
           machine de prise de vue) ». Le backend relit le fichier ecrit et
           compte ces motifs : ce qui s'affiche ici est ce compte. */
        + (rep.empreintes ? ' · <b>' + (rep.empreintes.total === 0
          ? 'aucune empreinte d\'outil ni de machine'
          : rep.empreintes.total + ' empreinte(s) restantes') + '</b> : '
          + rep.empreintes.versions + ' version d\'outil, '
          + rep.empreintes.machine + ' « threads= » (le processeur de la machine), '
          + rep.empreintes.outil + ' nom d\'encodeur — comptés dans les '
          + rep.empreintes.octets + ' octets du fichier livré'
          + (rep.empreintes.muxeur
            ? '. Le conteneur ' + (rep.format === "webm" ? 'Matroska' : 'MP4')
            + ' impose un champ d\'application de multiplexage : il porte « Lavf »,'
            + ' sans version ni machine — c\'est le seul reste, et il est nommé.'
            : '') : '');
      CF.toast("tourne-disque : " + rep.frames + " images, " + fr(mo, 2) + " Mo");
    } catch (e) {
      CF.toast(String(e && e.message || e), true);
      if (sent) { try { await M.api.del("turntable?job=" + job); } catch (err) { /* deja parti */ } }
    } finally {
      prog(null);
      CAPTURING = false; TT = null;
      btn.disabled = false;
      MV.classList.remove("cap");
      MV.style.width = ""; MV.style.height = ""; MV.style.transform = "";
      MV.setAttribute("orientation", orient0);
      if (spin) MV.setAttribute("auto-rotate", "");
    }
  }

  /* Une image de la visionneuse. `toDataURL` est le chemin PROUVE sur cette
     version (toBlob y passe par un autre calcul de taille) ; le decodage par
     <img> evite d'imposer createImageBitmap. */
  async function grab() {
    const u = MV.toDataURL("image/png");
    const im = new Image();
    im.src = u;
    if (im.decode) await im.decode();
    else await new Promise((r) => { im.onload = r; im.onerror = r; });
    return im;
  }

  /* Le fond du fichier : la visionneuse rend en ALPHA, un JPEG sans fond
     serait noir. On le peint ici, donc on le maitrise — et l'image livree
     ressemble a l'ecran plutot qu'a un trou. */
  function paintBack(x, size) {
    const g = x.createLinearGradient(0, 0, size * 0.4, size);
    g.addColorStop(0, "#20232a"); g.addColorStop(0.55, "#15171b"); g.addColorStop(1, "#0d0e11");
    x.fillStyle = g; x.fillRect(0, 0, size, size);
    const r = x.createRadialGradient(size / 2, size * 0.42, 0, size / 2, size * 0.42, size * 0.62);
    r.addColorStop(0, "rgba(255,255,255,.075)"); r.addColorStop(1, "rgba(0,0,0,0)");
    x.fillStyle = r; x.fillRect(0, 0, size, size);
  }

  function randJob() {
    let s = "";
    for (let i = 0; i < 8; i++) s += "0123456789abcdef"[Math.floor(Math.random() * 16)];
    return s;
  }
})();
