/* L'Établi — inspecteur 3D en bout de chaîne du 3D Studio.
   Vanilla, HORS du bundle minifié (même patron que /studio3d).

   RÈGLE STRUCTURANTE (spec §2.1) : cette page ne fabrique JAMAIS un GLB. Elle
   envoie des paramètres — une liste de nœuds, une matrice — aux routes
   /api/etabli/*, et c'est Python qui écrit, versionne et fiche. */
"use strict";
import { creerCanevas, charger, cadrer, vider, projeter, orienter, cadreOrtho,
         aspectDe } from "/lib3d/viewer.js";
import { indexerNoeuds, inventaire, isoler, surligner, designerAuClic }
  from "/lib3d/selection.js";
import { etaler, ranger, estEtalee, montrerPiece } from "/lib3d/plaque.js";
import { TransformControls } from "three/addons/controls/TransformControls.js";

const $ = (s) => document.querySelector(s);

/* Seuil de confort machine — MONTRÉ, jamais caché (doctrine des seuils du QC).
   Le franchir n'interdit rien : cela propose la version allégée. */
const SEUIL = { triangles: 300000, octets: 80 * 1024 * 1024 };

const S = {
  sources: { jobs: [], meshy: [] },
  a: null, b: null,          // { job, meshy, version, url, libelle }
  vueA: null, vueB: null,    // canevas
  /* La géométrie que charger() a MESURÉE dans le navigateur, par vue :
     { tris, maillages, taille, centre, rayon }. Elle est retenue parce que la
     ligne d'écart en a besoin quand la fiche manque — et elle manque le plus
     souvent, `/api/assets/3d/{job}/report` rendant 404 tant qu'aucune fiche
     n'a été écrite. (Règle du fichier : toute clé de S se déclare ICI.) */
  geoA: null, geoB: null,
  enAttente: [],             // corrections non écrites
};

/* L'état du panneau Parties. Il vit à côté de S plutôt que dedans parce
   qu'il ne décrit PAS le modèle affiché mais ce que l'utilisateur en a
   retenu — et parce que la tâche suivante l'enverra au serveur tel quel.
   `retenus` porte des uuid three.js (d'un maillage ou d'un matériau) ou
   des index de nœud glTF, selon la granularité, et il reste HOMOGÈNE :
   changer de granularité le vide, sans quoi une sélection mêlerait trois
   vocabulaires que rien ne saurait plus démêler. (Même règle que pour S :
   toute clé se déclare ICI.) */
const SEL = { granularite: "maillage", retenus: new Set() };

/* L'état de la PLAQUE. Il vit à côté de SEL, et pour la même raison : il ne
   décrit pas le modèle mais la façon dont on le REGARDE. Et il est
   délibérément SÉPARÉ de SEL.retenus — voir le commentaire de rendreParties
   sur l'œil : masquer une pièce est un geste de vue, la retenir est une
   charge qui part au serveur. Les confondre ferait perdre une sélection
   d'extraction en rangeant son écran.

   `masquees` porte des CLÉS DE PIÈCE, c'est-à-dire des index de nœud glTF
   (des nombres) — pas des uuid : la plaque ne connaît qu'une granularité, le
   nœud, quelle que soit celle du panneau. `teintes` est la table
   uuid → couleur CSS que plaque.js rend, et qui couvre tout le sous-arbre de
   chaque pièce : c'est elle qui permet de peindre la pastille d'un maillage
   comme celle de son nœud.

   `axe` est l'axe d'EMPILEMENT que plaque.js a choisi d'après les pièces —
   donc la normale du plan d'étalement, "x", "y" ou "z", et null hors plaque.
   Il ne décide de RIEN ici : il sert à dire, sur le bouton de vue
   correspondant, laquelle des trois regarde la plaque en face. (Même règle
   que pour S : toute clé se déclare ICI.) */
const PLQ = { active: false, pieces: [], masquees: new Set(),
              teintes: new Map(), partages: 0, vides: 0, axe: null };

/* La clé interne d'une granularité et son LIBELLÉ ne sont pas la même chose.
   Les clés (« noeud », « materiau ») sont des identifiants sans accents, qui
   voyagent dans `data-g` et qui partiront un jour au serveur ; le panneau, lui,
   écrit du français — il dit déjà « Isoler la sélection », et selection.js
   retombe sur « matériau » ACCENTUÉ pour un matériau sans nom. Sans cette
   table, l'onglet « materiau » listait des rangées « matériau ». */
const LIBELLE_GRANULARITE =
  { noeud: "nœud", maillage: "maillage", materiau: "matériau" };

/* Le gizmo de manipulation, UN pour toute la page : il se branche sur la
   caméra et sur le canevas de la vue A, l'un et l'autre créés une seule fois
   (viewer.js met les vues en cache et ne démonte jamais le canevas). */
let GIZMO = null;

/* Une série d'écritures à la fois — voir ecrireVersion(), qui explique
   pourquoi le bouton grisé ne suffit pas. */
let _ecritEnCours = false;

/* L'ORDRE D'ÉCRITURE, et il n'est pas décoratif. `extraire` REMAPPE le
   document — mesh_edit._carte renumérote les nœuds retenus — tandis que
   `reparer` AJOUTE un nœud racine en fin de tableau et que `transformer` ne
   réécrit qu'un champ : ni l'un ni l'autre ne déplace un index existant.
   Écrire l'extraction avant une transformation ferait donc porter les index
   du modèle AFFICHÉ sur un document déjà remappé — le mauvais maillage, sur
   disque, sans que rien ne grince. L'extraction passe en DERNIER, quel que
   soit l'ordre des clics. */
const ORDRE_ECRITURE = ["reparer", "transformer", "extraire"];

/* Les trois plumes de P1, ÉCRITES plutôt que composées. Un
   `/api/etabli/${t.operation}` marcherait aussi bien et rendrait le fichier
   muet à la recherche plein texte : personne — ni un banc, ni quelqu'un qui
   cherche « qui appelle extraire ? » — n'y trouverait ces adresses. */
const ROUTES = {
  reparer: "/api/etabli/reparer",
  transformer: "/api/etabli/transformer",
  extraire: "/api/etabli/extraire",
};

async function jget(p) {
  const r = await fetch(p);
  if (!r.ok) throw new Error(`${p} → ${r.status}`);
  return r.json();
}

async function jpost(p, corps) {
  const r = await fetch(p, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corps),
  });
  const t = await r.text();
  if (!r.ok) throw new Error(t || `${p} → ${r.status}`);
  return t ? JSON.parse(t) : {};
}

const fmtOctets = (n) => !n ? "—"
  : n > 1048576 ? `${(n / 1048576).toFixed(1)} Mo` : `${Math.round(n / 1024)} Ko`;

/* Les noms et les libellés viennent du DISQUE : mesh_sources « LIT ce qui
   existe », donc un nom de dossier ou un `asset.json` écrit à la main. Une
   apostrophe double dans un nom casserait l'attribut qui le porte, et la ligne
   entière avec. Échapper coûte trois lignes ; ne pas échapper coûte l'écran. */
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* Un nombre, ou `null` — jamais NaN, jamais une chaîne. Les chiffres de la
   ligne d'écart viennent de `report.json`, un fichier de disque que la
   doctrine du module décrit comme ouvert aux mains de l'utilisateur : « 12 000 »
   peut donc arriver là où un entier est attendu. Le refuser fait tomber la
   valeur sur le repli (la mesure du navigateur) au lieu de la recopier telle
   quelle dans le balisage — la même leçon que le Number() de rendreChrono. */
const nombre = (v) => {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
};

/* Ce que la barre du bas peut montrer d'un refus sans chasser le reste de la
   ligne. Le texte entier reste au survol : on ABRÈGE, on ne PERD pas. */
const LARGEUR_REFUS = 160;

/* Le dépôt n'a qu'UN endroit pour ses refus, et c'est la barre du bas : c'est
   là que _ouvrirPrincipale() écrit ses échecs de chargement, sous la classe
   `erreur` que la feuille peint en rouge. Une boîte d'alerte du navigateur
   bloquerait la page et ne ressemblerait à rien de ce que l'Établi affiche
   par ailleurs. Le message est posé en textContent : il vient d'un serveur ou
   d'un nom de fichier, il n'a rien à faire dans du balisage.

   ET IL EST BORNÉ ICI, pas dans jpost(). Mesuré : un serveur qui répond 501
   avec une page HTML fait déverser la page ENTIÈRE dans la barre — un 502 de
   proxy, une déconnexion, n'importe quel corps non-JSON. jpost() doit rester
   véridique pour la console et pour tout appelant futur ; c'est le point
   d'AFFICHAGE qui sait que la barre ne fait qu'une ligne. */
function direRefus(message) {
  const zone = $("#barreGeo");
  const texte = String(message ?? "");
  const ligne = texte.split("\n")[0].trim();
  zone.textContent = ligne.length > LARGEUR_REFUS
    ? `${ligne.slice(0, LARGEUR_REFUS)}…` : ligne;
  zone.title = texte;                 /* le refus entier, au survol */
  zone.classList.add("erreur");
}

/* Le texte NORMAL de la barre du bas : la mesure du modèle affiché. Il s'écrit
   à DEUX moments — au chargement, et après un refus TRANSITOIRE dont le geste
   suivant a réussi (poserGizmo, séparerSelection). Sans ce retour, la classe
   `erreur` ne périmerait qu'au prochain chargement : la barre resterait rouge
   sous un geste qui vient de marcher, ce qui est un mensonge de moins d'une
   seconde mais un mensonge quand même. */
function direGeometrie() {
  const zone = $("#barreGeo");
  zone.classList.remove("erreur");
  zone.title = "";
  const geo = S.geoA;
  if (!geo) { zone.textContent = "—"; return; }
  zone.textContent =
    `${geo.tris.toLocaleString("fr-FR")} triangles · ${geo.maillages} maillages`;
  if (geo.tris > SEUIL.triangles) {
    zone.textContent +=
      ` · au-delà du seuil de ${SEUIL.triangles.toLocaleString("fr-FR")}, une version décimée existe peut-être`;
  }
}

/* ── la chronologie : une ligne par job, une puce par étape ────────────────── */
function rendreChrono() {
  const box = $("#chrono");
  const blocs = [];
  for (const j of S.sources.jobs) {
    const etapes = j.etapes.map((e) => {
      /* `triangles` vient du `geo.get("tris_lus")` de mesh_sources, lu SANS
         validation de type dans le registry.json du job — le fichier même que
         la doctrine du module décrit comme ouvert aux mains de l'utilisateur.
         Une CHAÎNE y survit : elle rendrait `lourd` faux en silence (NaN), et
         `toLocaleString` la recopierait telle quelle dans le balisage, un
         guillemet compris — mot pour mot le scénario que décrit le commentaire
         d'esc(). C'était la seule valeur de mesh_sources qui entrait dans
         innerHTML sans passer par esc() ; un Number() en tête la ramène dans
         le rang, et l'invariant que ce fichier s'est donné redevient vrai. */
      const tri = Number(e.triangles) || 0;
      const lourd = tri > SEUIL.triangles || (e.bytes && e.bytes > SEUIL.octets);
      return `<button class="etape${lourd ? " lourde" : ""}"
        data-job="${esc(j.id)}" data-version="${esc(e.version ?? "")}"
        data-url="${esc(e.url)}" data-libelle="${esc(e.libelle)}"
        title="${tri ? tri + " triangles · " : ""}${fmtOctets(e.bytes)}">
        <b>${esc(e.libelle)}</b>
        <span>${tri ? tri.toLocaleString("fr-FR") + " tri" : fmtOctets(e.bytes)}</span>
      </button>`;
    }).join("");
    /* `data-job`/`data-nom` : les deux noms sous lesquels un job peut arriver
       dans `?job=`. L'id est le nom du DOSSIER (mesh_sources : `d.name`) ; le
       nom vient de `asset.json`, et c'est celui-là que le 3D Studio a en main
       (S.cfg.name). Ils coïncident souvent, jamais toujours. — Dans la boucle
       Meshy juste en dessous, `data-job` porte l'id de la TÂCHE et non un
       dossier : une tâche Meshy n'est pas encore un job (elle le devient par
       /api/etabli/adopter), mais elle se laisse viser sous ce nom. */
    blocs.push(`<section class="job" data-job="${esc(j.id)}" data-nom="${esc(j.nom)}">
      <div class="job-tete">${esc(j.nom)}<span>${esc(j.moteur || j.source)}</span></div>
      <div class="job-etapes">${etapes}</div></section>`);
  }
  for (const t of S.sources.meshy) {
    const etapes = t.etapes.map((e) => `<button class="etape"
      data-meshy="${esc(t.id)}" data-url="${esc(e.url)}" data-libelle="${esc(e.libelle)}">
      <b>${esc(e.libelle)}</b><span>${esc(t.phase || t.kind || "meshy")}</span></button>`).join("");
    blocs.push(`<section class="job" data-job="${esc(t.id)}" data-nom="${esc(t.nom)}">
      <div class="job-tete">${esc(t.nom)}<span>meshy · ${esc(t.phase || "")}</span></div>
      <div class="job-etapes">${etapes}</div></section>`);
  }
  box.innerHTML = blocs.join("") || '<div class="chrono-vide">aucun maillage</div>';

  box.querySelectorAll(".etape").forEach((b) => {
    b.addEventListener("click", (ev) => {
      const cible = {
        job: b.dataset.job || null,
        /* une étape Meshy n'a pas de job : on garde l'id de la tâche pour
           pouvoir la faire adopter au moment d'écrire (spec §6.2) */
        meshy: b.dataset.meshy || null,
        version: b.dataset.version ? Number(b.dataset.version) : null,
        url: b.dataset.url,
        libelle: b.dataset.libelle,
      };
      /* alt-clic : la seconde vue, pour comparer deux étapes (spec §5.1). */
      if (ev.altKey) ouvrirComparaison(cible);
      else ouvrirPrincipale(cible);
    });
  });
}

/* ── le verrou de la vue A ──────────────────────────────────────────────────
   charger() est NON RÉ-ENTRANT et le dit en tête de viewer.js : sur deux clics
   rapprochés, le vider() du second s'exécute pendant que le loadAsync du
   premier est encore en vol, puis les DEUX font scene.add() — le perdant reste
   dans le graphe pour toujours, vider() ne retirant que `api.racine`.

   Un simple jeton de génération comparé APRÈS l'attente ne corrigerait rien :
   à cet instant les deux modèles sont DÉJÀ dans la scène, le mal est fait. Il
   faut empêcher le RECOUVREMENT lui-même, pas seulement la dernière écriture —
   d'où une FILE : chaque demande attend que la précédente ait fini.

   Le jeton sert alors à autre chose, et reste utile : quand dix clics se sont
   empilés pendant le chargement d'un gros GLB, seul le dernier mérite d'être
   téléchargé ; les neuf autres se retirent en tête de tour sans rien charger. */
let _file = Promise.resolve();
let _demande = 0;

function ouvrirPrincipale(cible) {
  const numero = ++_demande;
  /* Le `.catch` n'est pas décoratif : une promesse rejetée laisserait `_file`
     rejetée POUR TOUJOURS, et le `.then` de tous les clics suivants serait
     purement sauté — la chronologie deviendrait muette au premier échec. Le
     refus, lui, est déjà montré dans la barre par _ouvrirPrincipale(). */
  _file = _file.then(() => _ouvrirPrincipale(cible, numero)).catch(() => {});
  /* Ce que l'appelant reçoit, puisque trois issues n'ont qu'un seul résultat
     observable : la promesse rendue dit seulement que la FILE est vide — pas
     que le modèle est chargé. Un échec est avalé par le `.catch`, une demande
     dépassée se retire sans rien charger. D'où le booléen : `S.a === cible`
     est la seule réponse vraie à « est-ce que MA cible est à l'écran ? ». */
  return _file.then(() => S.a === cible);
}

async function _ouvrirPrincipale(cible, numero) {
  if (numero !== _demande) return;   // dépassée pendant l'attente : on se retire
  /* À partir d'ici le modèle affiché va changer, quoi qu'il arrive. Les
     corrections en attente sont indexées par numéro de nœud DU modèle affiché
     (`userData.indexGltf`) : les garder ferait écrire les index d'un maillage
     dans la version d'un AUTRE, sur disque et sans que rien ne grince. */
  S.enAttente.length = 0;
  /* Vider le tableau ne redessine pas la barre : elle continuerait d'annoncer
     « 2 modifications en attente » et d'offrir un bouton « écrire la version »
     pour une file vide. Elle AFFIRME quelque chose — elle se refait ici. */
  rendreAttente();
  /* Et le gizmo lâche son nœud, ICI et pas ailleurs : `attach()` en garde une
     référence FORTE, et le `vider()` de charger() est sur le point d'en
     disposer géométrie et matériaux. Le gizmo tiendrait alors un objet mort
     et continuerait de le peindre. L'évènement `etabli:charge` n'arriverait
     qu'APRÈS le chargement, et seulement en cas de succès : il ne peut pas
     porter ce détachement. */
  if (GIZMO) GIZMO.detach();
  /* Et la PLAQUE se range, ICI aussi et pour une raison de plus : ses berceaux
     et ses teintes d'origine sont accrochés aux objets et aux matériaux du
     modèle SORTANT, que le vider() de charger() est sur le point de libérer,
     et son PLATEAU vit dans la scène — que vider() ne touche pas, puisqu'il ne
     retire que `api.racine`. Non rangé, il resterait sur la carte pour
     toujours et un second étalement en poserait un deuxième par-dessus.

     LA DÉCISION, ET ELLE EST ASSUMÉE : changer de modèle pendant que la plaque
     est affichée RAMÈNE à « Assemblé ». Ré-étaler le modèle entrant serait
     plus doux, et c'est justement ce qu'on refuse : la vue reviendrait éclatée
     après chaque écriture de version (ecrireVersion rouvre la version neuve),
     sur un modèle que l'utilisateur vient d'écrire et qu'il veut voir tel
     qu'il est sur le disque. Une plaque est la vue D'UN modèle ; l'autre
     modèle demande un clic. */
  oublierPlaque();
  /* Et la sélection du panneau Parties avec elles, pour la même raison :
     ses uuid désignent les objets du modèle SORTANT, que vider() est sur le
     point de libérer. Gardés, ils ne désigneraient plus rien — ou pire,
     désigneraient un jour autre chose, et la tâche 8 les enverrait tels
     quels au serveur. */
  SEL.retenus.clear();
  const geoBox = $("#barreGeo");
  $("#barreFichier").textContent = cible.url.split("/").pop();
  geoBox.classList.remove("erreur");
  geoBox.title = "";                 /* le refus entier d'avant, au survol */
  geoBox.textContent = "chargement…";
  let geo;
  try {
    /* creerCanevas() DANS le try : sans contexte WebGL (GPU sur liste noire,
       trop de contextes ouverts) il lève, et posé au-dessus il serait le seul
       chemin d'échec de cette fonction à ne PAS se voir — « chargement… »
       resterait figé, le `.catch` de la file ayant avalé la promesse. */
    if (!S.vueA) S.vueA = creerCanevas($("#vueA canvas"));
    geo = await charger(S.vueA, cible.url);
  } catch (e) {
    /* Un GLB absent (404), tronqué, ou compressé sans son décodeur laisse le
       canevas VIDE — charger() ayant vidé la vue précédente AVANT d'échouer.
       Sans ce bloc l'échec ne se verrait nulle part : la barre du bas est
       l'endroit où le dépôt met ses refus parlants. */
    S.a = null;                      // rien n'est chargé : ne pas mentir à la suite
    S.geoA = null;                   // ni à la ligne d'écart, qui la lirait
    rendreParties();                 // ni au panneau, qui listerait un modèle absent
    perimerEcart();                  // ni à l'écran, si une comparaison est ouverte
    $("#chipSource").textContent = "—";
    geoBox.textContent = `échec du chargement — ${e.message}`;
    geoBox.classList.add("erreur");
    return;
  }
  S.a = cible;                       // posé APRÈS le succès, pour la même raison
  /* Retenue pour la ligne d'écart : c'est le SEUL compte de triangles dont on
     dispose tant qu'aucune fiche n'existe, et le recalculer exigerait de
     recharger le GLB. */
  S.geoA = geo;
  perimerEcart();                    // le terme de gauche a changé sous la boîte
  $("#chipSource").textContent = `${cible.job || "meshy"} · ${cible.libelle}`;
  /* La mesure passe par direGeometrie(), qui la lit dans S.geoA — posé juste
     au-dessus. Un seul endroit écrit cette ligne, donc un seul endroit à
     changer le jour où le seuil se dira autrement. */
  direGeometrie();
  document.dispatchEvent(new CustomEvent("etabli:charge", { detail: { geo } }));
}

/* ── la comparaison A/B ─────────────────────────────────────────────────────
   Deux vues, une seule caméra logique. Comparer deux étapes sous deux angles
   différents ne compare rien : la synchronisation n'est pas un confort.
   Elle copie la caméra en ABSOLU (position, cible, cadre, near/far) — donc si
   B est plus gros que A, il déborde du cadre de A, et c'est le but : la
   différence de taille se VOIT, au lieu d'être annulée par deux cadrages
   indépendants. */
function synchroniser(src, dst) {
  /* Les deux sens sont branchés tête-bêche : sans ce drapeau, l'update() de
     dst lèverait son propre « change », qui recopierait dst vers src, etc. */
  let enCours = false;
  src.controls.addEventListener("change", () => {
    if (enCours) return;
    enCours = true;
    /* LA PROJECTION D'ABORD. Deux vues qui ne projettent pas pareil ne
       comparent rien — c'est le même défaut que deux angles différents, et
       c'est exactement ce que cette fonction existe pour empêcher.

       SECONDE GARDE, ET ELLE NE DEVRAIT JAMAIS SERVIR : basculerProjection()
       projette les DEUX vues d'un même geste, et _ouvrirComparaison() aligne B
       sur A dès sa naissance, avant tout chargement. Elle est là pour le jour
       où une troisième route ferait diverger les deux modes — même doctrine
       que les deux gardes indépendantes de la plaque sur le mode d'échec qui
       écrit un GLB faux.
       CE QU'ELLE COÛTE LE JOUR OÙ ELLE SERT : projeter() finit par un
       controls.update() sur dst, dont le « change » réveille le handler
       tête-bêche, lequel recopie dst — encore d'un cran en arrière — vers src.
       Une image de retard, corrigée à la suivante puisque `enableDamping` fait
       tourner update() à chaque image. Hors de ce cas, projeter() rend la main
       aussitôt quand le mode est déjà le bon, et la ligne ne coûte qu'une
       comparaison. */
    if (dst.projection !== src.projection) {
      projeter(dst, src.projection);
      /* ET LE GIZMO AVEC, PARCE QUE `dst` PEUT ÊTRE LA VUE A. Le câblage est
         tête-bêche — synchroniser(A, B) ET synchroniser(B, A) — donc dans le
         second sens c'est `S.vueA.camera` qui change ici. Sans cette ligne, le
         gizmo garderait une caméra que plus personne ne rend : poignées mal
         taillées et impossibles à attraper, sans erreur nulle part. C'est
         exactement le piège que projeter() nomme, traité à DEUX sites sur
         trois dans la première écriture — l'oubli était ici.
         reposerCameraDuGizmo() lit S.vueA et rien d'autre : l'appeler quand
         c'est B qui a bougé ne coûte qu'une affectation identique. */
      reposerCameraDuGizmo();
    }
    dst.camera.position.copy(src.camera.position);
    /* Redondante avec l'update() ci-dessous, qui refait un lookAt(target) :
       gardée pour que dst soit juste même avant lui, pas parce qu'il la faut. */
    dst.camera.quaternion.copy(src.camera.quaternion);
    dst.camera.zoom = src.camera.zoom;
    if (src.camera.isOrthographicCamera) {
      /* UNE ORTHO N'A PAS DE `fov`, et lui en écrire un ne lève rien : la
         copie serait silencieusement sans effet et les deux vues divergeraient
         à la première image. Sa grandeur à elle est la DEMI-HAUTEUR, et le
         cadre se REFAIT sur l'aspect de dst plutôt que d'être recopié —
         recopier left/right imposerait à B l'aspect de A, ce qui écraserait le
         modèle B le jour où les deux moitiés cesseront d'être égales. */
      const c = cadreOrtho((src.camera.top - src.camera.bottom) / 2, aspectDe(dst));
      dst.camera.left = c.left;
      dst.camera.right = c.right;
      dst.camera.top = c.top;
      dst.camera.bottom = c.bottom;
    } else {
      dst.camera.fov = src.camera.fov;
    }
    dst.camera.near = src.camera.near;
    dst.camera.far = src.camera.far;
    dst.camera.updateProjectionMatrix();
    /* La cible AVANT l'update : OrbitControls.update() redéduit ses
       coordonnées sphériques de (position − target) à chaque appel, donc une
       cible non copiée ferait pivoter dst autour de son ancien centre. */
    dst.controls.target.copy(src.controls.target);
    dst.controls.update();
    enCours = false;
  });
}

/* La fiche BRUTE du registre — attention, ce n'est PAS le vocabulaire de la
   chronologie : mesh_sources normalisait vers `triangles`/`bytes`, le registre
   dit `tris_lus`, `dims`, `gltf.textures`, `sha256`. Deux noms pour les mêmes
   chiffres ; les mélanger afficherait des tirets sans rien casser. */
async function ficheDe(cible) {
  /* Pas de job (une étape Meshy) : aucun registre à interroger. Pas de version
     (l'étape « décimée », qui est un fichier à part) : le registre est indexé
     PAR VERSION, et retomber sur la version 1 afficherait le sha256 et les
     cotes du BROUILLON sous un fichier qui n'est pas lui. Une fiche fausse est
     pire qu'une fiche absente — le repli garde de toute façon les triangles.
     Et `cible` peut être null : les files de A et de B sont indépendantes,
     donc un échec de chargement en A pendant que B charge remet S.a à null
     sous nos pieds. Sans cette garde, le déréférencement lèverait DANS une
     promesse que le .catch de la file avale — « comparaison… » resterait figé
     à l'écran, le refus ne vivant que dans la console. */
  if (!cible || !cible.job || !cible.version) return null;
  try {
    const reg = await jget(
      `/api/assets/3d/${encodeURIComponent(cible.job)}/report`);
    return (reg.entries || []).find(
      (e) => Number(e.version) === Number(cible.version)) || null;
  } catch { return null; }         /* 404 : aucune fiche encore écrite */
}

function ligneEcart(fa, fb, geoA, geoB) {
  const ga = (fa && fa.geometry) || {}, gb = (fb && fb.geometry) || {};
  /* La fiche nomme le compte `tris_lus` et les cotes `dims` (un OBJET
     largeur/hauteur/profondeur, pas un tableau) — vérifié dans
     mesh_report.geometry. Se tromper de clé afficherait « — » partout sans
     rien casser, ce qui est le pire des échecs : silencieux.

     D'où le REPLI, et d'où le fait qu'il compte vraiment : la route rend 404
     tant qu'aucune fiche n'existe, et ficheDe() avale ce 404. Deux étapes non
     fichées — le cas ORDINAIRE — n'auraient donc que des tirets. Or les
     triangles, eux, viennent d'être mesurés : le navigateur a chargé les deux
     GLB pour les afficher, et charger() en rend le compte. Seuls les cotes,
     les textures et le sha256 n'ont aucun équivalent mesuré ici ; eux seuls
     ont droit au tiret. */
  const ta = nombre(ga.tris_lus) ?? nombre(geoA.tris);
  const tb = nombre(gb.tris_lus) ?? nombre(geoB.tris);
  const chiffre = (n) => (n === null ? "—" : n.toLocaleString("fr-FR"));
  let delta = "";
  if (ta !== null && tb !== null) {
    const d = tb - ta, signe = d >= 0 ? "+" : "";
    /* Le pourcentage n'a de sens que rapporté à quelque chose : sur un A à
       zéro triangle il vaudrait l'infini. */
    /* toLocaleString et non toFixed : le reste de la ligne est en français
       (« 6 240 »), et un « 51900.0 » au milieu jurerait. */
    const pct = ta ? ` (${signe}${((d / ta) * 100).toLocaleString("fr-FR",
      { minimumFractionDigits: 1, maximumFractionDigits: 1 })} %)` : "";
    delta = ` <i>${signe}${d.toLocaleString("fr-FR")}${pct}</i>`;
  }
  const dim = (g) => {
    const c = [g.dims && g.dims.largeur, g.dims && g.dims.hauteur,
               g.dims && g.dims.profondeur].map(nombre);
    return c.every((x) => x !== null)
      ? c.map((x) => x.toFixed(3)).join(" × ") : "—";
  };
  /* esc() sur le sha256 : il vient de `report.json`, donc du disque, et il
     entre dans innerHTML — l'invariant que ce fichier s'est donné. Les autres
     valeurs passent par nombre(), qui ne rend que des nombres. */
  const sha = (f) => (f && f.sha256
    ? esc(String(f.sha256).slice(0, 10)) + "…" : "—");
  const tex = (f) => chiffre(nombre(f && f.gltf && f.gltf.textures));
  /* L'unité n'est pas décorative : le commentaire de cadrer() explique qu'un
     modèle en mètres et un modèle en centimètres donnent l'un un point, l'autre
     un mur — et cette ligne est justement l'endroit où cet écart se lit. glTF
     compte en mètres ; un maillage qui n'en tient pas compte se voit ici. */
  const da = dim(ga), db = dim(gb);
  const unite = (da !== "—" || db !== "—") ? ' <i>u. glTF (1 = 1 m)</i>' : "";
  return `
    <div><b>triangles</b> ${chiffre(ta)} → ${chiffre(tb)}${delta}</div>
    <div><b>dimensions</b> ${da} → ${db}${unite}</div>
    <div><b>textures</b> ${tex(fa)} → ${tex(fb)}</div>
    <div><b>sha256</b> ${sha(fa)} → ${sha(fb)}</div>`;
}

/* ── le verrou de la vue B ──────────────────────────────────────────────────
   Le mécanisme de la tâche 4, à la lettre, et pour la même raison : charger()
   n'est pas ré-entrant, donc deux alt-clics rapprochés recouvriraient deux
   chargements sur S.vueB et le perdant resterait dans le graphe pour toujours.
   Mais une file PROPRE à B, et non celle de A : le jeton signifie « seule la
   dernière demande compte », ce qui n'est vrai qu'À L'INTÉRIEUR d'une vue. Un
   jeton partagé ferait qu'un clic sur A annule l'alt-clic sur B qui attendait
   derrière lui, et la comparaison ne s'ouvrirait jamais. */
let _fileB = Promise.resolve();
let _demandeB = 0;

function ouvrirComparaison(cible) {
  const numero = ++_demandeB;
  _fileB = _fileB.then(() => _ouvrirComparaison(cible, numero)).catch(() => {});
  /* Même contrat que pour la vue A : la promesse dit que la file est vide, et
     le booléen répond seul à « est-ce que MA cible est en B ? ». */
  return _fileB.then(() => S.b === cible);
}

async function _ouvrirComparaison(cible, numero) {
  if (numero !== _demandeB) return;   // dépassée ou fermée : on se retire
  /* Comparer avec rien n'a pas de sens : sans vue A, l'alt-clic vaut le clic.
     Ce que rend ouvrirPrincipale ne dit PAS que le modèle est chargé — sa
     promesse dit seulement que la file est vide — donc on ne bâtit RIEN
     derrière ce await : on rend la main, et le refus éventuel est déjà montré
     dans la barre du bas par _ouvrirPrincipale(). */
  if (!S.a) { await ouvrirPrincipale(cible); return; }

  const boite = $("#ecart");
  /* La vue B est montrée AVANT le chargement : c'est ce qui donne au canevas
     sa taille, donc à cadrer() l'aspect réel de la demi-largeur. Montrée
     après, B serait cadrée sur une largeur qu'elle n'a plus. */
  $("#vueB").classList.remove("hidden");
  boite.classList.remove("hidden", "erreur");
  /* Et la boîte d'écart reçoit sa hauteur FINALE tout de suite, sous forme de
     squelette à tirets : exactement la même doctrine qu'au-dessus, appliquée
     cette fois à la hauteur. Sans lui, la boîte tient UNE ligne au moment du
     cadrage et CINQ quand le contenu vrai arrive, deux requêtes réseau plus
     loin ; elle reprend alors 56 px aux vues, et les deux modèles se retrouvent
     posés 7,6 % trop loin — mesuré en navigateur (1440×900) : 6,1536 au lieu
     de 5,7213, trois fois sur trois, l'aspect valant 0,538 au lieu de 0,579.
     Un requestAnimationFrame n'y changerait rien : aucune image ne sépare le
     cadrage du réseau. L'écriture finale remplace ensuite un contenu de MÊME
     hauteur, donc sans saut de caméra — ce qu'aurait coûté l'autre correctif
     possible, déplacer le cadrage après la réponse du réseau. */
  boite.innerHTML = '<div class="ecart-tete">comparaison…</div>'
    + ligneEcart(null, null, {}, {});
  let geoB;
  try {
    if (!S.vueB) {
      /* creerCanevas() DANS le try, comme pour A : c'est le SECOND contexte
         WebGL de la page, donc le premier à se voir refuser quand la carte
         est à court — et un refus muet laisserait « comparaison… » figé. */
      S.vueB = creerCanevas($("#vueB canvas"));
      /* B NAÎT SUR LE POINT DE VUE DE A, avant tout chargement : charger()
         cadre, et cadrer() lit `api.vue`. Une vue B née en perspective libre
         pendant que A regarde en isométrie serait cadrée de travers, puis
         redressée à la première synchronisation — un saut visible, sur la vue
         dont le métier est justement de comparer. La synchronisation ci-dessous
         ne suffit pas : elle ne parle qu'au premier « change » d'OrbitControls,
         qui arrive APRÈS le cadrage. */
      projeter(S.vueB, S.vueA.projection);
      orienter(S.vueB, S.vueA.vue);
      /* LES DEUX SENS. Une seule direction ferait suivre B quand on tourne A
         et laisserait A immobile quand on tourne B : un geste sur deux
         comparerait alors deux angles différents, ce que cette vue existe
         précisément pour empêcher. */
      synchroniser(S.vueA, S.vueB);
      synchroniser(S.vueB, S.vueA);
    }
    geoB = await charger(S.vueB, cible.url);
  } catch (e) {
    /* Le jeton d'abord, comme sur le chemin du succès : fermer la comparaison
       pendant un chargement qui échoue ouvrirait sinon une bande d'erreur pour
       une comparaison que plus personne n'attend. */
    if (numero !== _demandeB) return;
    /* Le refus se VOIT, et la page revient à l'état d'avant plutôt que de
       garder une demi-page noire. Il s'affiche dans la ligne d'écart et non
       dans la barre du bas : celle-ci appartient au modèle A, qui n'a pas
       bougé — y écrire l'échec de B mentirait sur A. textContent, le message
       venant du serveur. */
    fermerComparaison();
    boite.classList.remove("hidden");
    boite.classList.add("erreur");
    boite.textContent = `échec du chargement de B — ${e.message}`;
    return;
  }
  if (numero !== _demandeB) {
    /* Fermée (ou dépassée) pendant le chargement : fermerComparaison() a vidé
       la vue AVANT que ce modèle-ci n'y entre, il n'a donc personne pour le
       regarder et personne d'autre pour le libérer. */
    vider(S.vueB);
    return;
  }
  S.b = cible;
  S.geoB = geoB;
  /* B vient de prendre la moitié de la largeur à A : le cadrage de A, calculé
     en pleine largeur, rogne maintenant d'un bon tiers. cadrer() est conscient
     de l'aspect depuis cette tâche (la dérivation est dans viewer.js) et, à
     aspect égal, rend à A et à B le MÊME recul — leur distance ne diffère plus
     que par leur taille propre, ce qui est justement ce qu'on veut comparer.
     Ce re-cadrage propage de surcroît la caméra de A vers B par la
     synchronisation (controls.update() lève un « change ») : les deux vues
     partagent donc un seul point de vue dès la première image, celui de A, la
     référence. */
  cadrer(S.vueA);
  /* Le terme de GAUCHE est capturé AVANT l'attente. Les deux files sont
     indépendantes et s'entrelacent : S.a peut passer de A1 à A2 pendant les
     deux requêtes, et sans cette capture la boîte afficherait le libellé de A2
     au-dessus des triangles, des cotes et du sha256 de A1 — une comparaison
     fausse, exactement ce que ficheDe() refuse quatorze lignes plus haut. */
  const a = S.a;
  const [fa, fb] = await Promise.all([ficheDe(a), ficheDe(S.b)]);
  if (numero !== _demandeB) return;   // fermée pendant les deux requêtes
  if (S.a !== a) {
    /* La vue A a changé — ou échoué, le `!==` couvre le cas null du même
       geste — pendant que B chargeait. Il n'y a plus de terme de gauche à la
       comparaison : la fermer est la seule réponse vraie. Cette garde est
       posée ICI, après le dernier await, parce que c'est le seul endroit où
       rien ne peut plus changer avant l'écriture. */
    fermerComparaison();
    boite.classList.remove("hidden");
    boite.classList.add("erreur");
    boite.textContent = "comparaison abandonnée — la vue A a changé";
    return;
  }
  /* S.a === a ici, la garde vient de le dire : les deux écritures parlent du
     MÊME modèle. */
  boite.innerHTML =
    `<div class="ecart-tete">A ${esc(S.a.libelle)} → B ${esc(cible.libelle)}</div>`
    + ligneEcart(fa, fb, S.geoA || {}, geoB || {});
}

/* La ligne d'écart PÉRIME dès que la vue A change de modèle : elle AFFIRME
   « A <libellé> → B <libellé> » alors que #chipSource et #barreFichier viennent
   d'être réécrits sous elle. Un commentaire ne remonte pas jusqu'à l'écran, et
   c'est l'écran qui affirme. On ne promet pas une comparaison vivante — la
   recalculer exigerait de relire deux fiches — on promet de ne jamais en
   afficher une fausse.

   Le SQUELETTE, et non un textContent d'une ligne : la boîte garde ses cinq
   rangées. Écrite en une ligne, elle rendait 56 px aux vues APRÈS que
   charger() ait cadré la vue A — mêmes 56 px et mêmes 7,6 % que le défaut que
   ce commit corrige, mais dans l'autre sens : TROP PRÈS, donc rognant ~3,8 %
   de la largeur à chaque bord (recul posé 1,4045 contre 1,5107 requis), sur la
   vue principale d'un modèle que l'utilisateur vient de charger, et jusqu'au
   prochain alt-clic. Trop loin ne rogne jamais ; trop près, si.
   Les tirets y sont littéralement vrais : il n'y a plus de comparaison. */
function perimerEcart() {
  if (!S.b) return;
  const boite = $("#ecart");
  boite.classList.add("erreur");
  boite.innerHTML =
    '<div class="ecart-tete">la vue A a changé — alt-cliquez pour recomparer</div>'
    + ligneEcart(null, null, {}, {});
}

/* Le bouton est visible dès le chargement de la page, avant qu'il y ait quoi
   que ce soit à fermer : chaque geste est donc gardé, et fermer sur rien ne
   fait rien. */
function fermerComparaison() {
  $("#vueB").classList.add("hidden");
  $("#ecart").classList.add("hidden");
  $("#ecart").textContent = "";
  /* vider() libère le MODÈLE, pas le canevas : la boucle de rendu et le
     contexte WebGL de B restent vivants, c'est délibéré et documenté dans
     viewer.js (les deux vues sont mises en cache pour la durée de la page). */
  if (S.vueB) vider(S.vueB);
  S.b = null;
  S.geoB = null;
  /* A récupère toute la largeur : son aspect change dans CE sens aussi, et le
     cadrage reculé pour une demi-largeur y laisserait le modèle trop petit. */
  if (S.vueA) cadrer(S.vueA);
}

$("#btnCompare").addEventListener("click", () => {
  /* Le jeton avance ICI et non dans fermerComparaison() : une demande encore
     en file doit se retirer quand c'est l'UTILISATEUR qui ferme (sinon elle
     rouvrirait la vue qu'il vient de fermer), mais surtout pas quand c'est un
     chargement raté qui appelle la même fonction — il annulerait alors
     l'alt-clic suivant, qui n'a rien à voir avec son échec. */
  _demandeB++;
  fermerComparaison();
});

/* ── retour au 3D Studio ────────────────────────────────────────────────────
   L'Établi n'est plus un onglet à part : il PREND LA PLACE du graphe dans
   l'iframe du hub (voir ouvrirEtabli dans studio3d.js, et la demande de
   l'utilisateur qui l'a voulu ainsi). Sans ce bouton, le sous-onglet
   « 3D Studio » resterait sur l'Établi jusqu'au prochain rechargement du hub.

   UNE adresse absolue, et rien d'autre : pas de `window.parent`, pas de
   `window.top`. /etabli/ s'ouvre AUSSI en direct, et une navigation qui
   suppose un parent ne marcherait qu'embarquée. `?job=` ne repart pas : le
   studio a son propre état, et lui rendre une chaîne de requête qu'il ne lit
   pas ferait une URL qui promet sans tenir.

   Branché ICI, au premier niveau du module — il ne s'exécute qu'à l'import.
   Posé dans l'écouteur `etabli:charge`, il s'empilerait à chaque modèle chargé
   (c'est le piège que `_clicBranche` corrige plus bas).

   ET IL REFUSE DE PARTIR SUR UNE FILE PLEINE. `S.enAttente` porte des
   corrections qui ne sont PAS sur le disque — c'est toute la doctrine de cette
   page : les boutons mettent en attente, la porte d'écriture écrit. Partir les
   perdrait EN SILENCE.

   REFUS et non confirm(), et la raison n'est pas le style de la page. LA RÈGLE
   EST LA RÉVERSIBILITÉ : ON DEMANDE QUAND LE COÛT EST INÉVITABLE, ON REFUSE
   QUAND LE REMÈDE EST À UN CLIC. Le 3D Studio, lui, DEMANDE avant de venir
   ici, et c'est la même règle qui le veut : une série Meshy en vol meurt quoi
   qu'on fasse, aucun geste ne la sauve, informer est tout ce qu'on peut faire.
   Ici c'est l'inverse — « écrire la version » et « annuler » sont deux
   boutons de la barre du bas, frères du <footer class="barre"> où le refus
   s'écrit, et « annuler » vide la file en un clic. Offrir « pars quand même et
   perds tout » serait offrir STRICTEMENT PIRE que ce qui est déjà sous les
   yeux : un abandon irréversible fondu dans un clic de navigation, quand le
   bouton d'à côté fait l'abandon proprement et laisse partir juste après.

   (Le retour ⌂ de vectorlab, qui confirme sur `etat.sale`, ne dit pas le
   contraire : là-bas PARTIR EST le seul moyen d'abandonner un essai — son
   `#btnAnnuler` est un Ctrl+Z, pas un vidage. Le coût y est donc inévitable au
   même titre qu'une série Meshy, et la règle rend le même verdict.)

   Que la doctrine anti-`alert` de cette page (test_aucun_refus_ne_passe_par
   _alert) aille dans le même sens est une confirmation, pas l'argument : elle
   justifierait aussi bien un modal maison, et elle n'expliquerait pas
   pourquoi le studio, lui, a le droit de demander. */
$("#btnRetour").addEventListener("click", () => {
  if (S.enAttente.length) {
    /* Le message ne DÉSIGNE JAMAIS un bouton grisé : pendant une série
       d'écritures, `#btnEcrire` est `disabled` alors que la file n'est pas
       encore vidée (rendreAttente porte l'état du verrou). Fenêtre étroite,
       mais un refus qui montre du doigt un bouton mort est un refus qui ment.
       On dit alors la seule chose vraie : c'est en cours, ça va se vider. */
    direRefus(_ecritEnCours
      ? `${S.enAttente.length} modification(s) en cours d'écriture — `
        + "attends la fin de la série avant de revenir au 3D Studio"
      : `${S.enAttente.length} modification(s) non écrite(s) — `
        + "« écrire la version » ou « annuler » avant de revenir au 3D Studio");
    return;
  }
  location.href = "/studio3d/";
});

/* ── ?job= : la promesse du lien du 3D Studio, tenue ────────────────────────
   Le nœud « 07 · établi » du graphe amène ici avec `?job=<nom>` en poche.
   Ignorer cette chaîne — ce que faisait la page — déposait l'utilisateur sur
   la chronologie ENTIÈRE, sans rapport visible avec le job d'où il venait :
   une URL qui promet et ne tient pas.

   Ce que l'on tient, et rien de plus : le bloc est MARQUÉ et amené sous les
   yeux. On n'OUVRE aucun modèle. charger() n'est pas ré-entrant et passe par
   un verrou de sérialisation ; une ouverture surprise au chargement de la page
   coûterait le téléchargement d'un GLB que personne n'a demandé, et volerait
   la première vue à qui venait comparer autre chose.

   Job absent de la chronologie : rien, en silence. Une alerte pour une chaîne
   de requête que l'utilisateur ne maîtrise pas ne lui apprendrait rien. */
function marquerJobVise() {
  const vise = new URLSearchParams(location.search).get("job");
  if (!vise) return;
  /* on cherche par dataset et non par sélecteur : un nom de dossier venu du
     disque peut contenir un guillemet, et `[data-job="…"]` lèverait dessus. */
  const bloc = [...$("#chrono").querySelectorAll(".job")]
    .find((s) => s.dataset.job === vise || s.dataset.nom === vise);
  if (!bloc) return;
  bloc.classList.add("vise");
  /* `nearest` : si le bloc est déjà visible, on ne bouge pas la chronologie
     sous les yeux de quelqu'un qui la lisait. */
  bloc.scrollIntoView({ block: "nearest" });
}

/* ── la plaque : une VUE, JAMAIS une mutation ───────────────────────────────
   « pour pouvoir sélectionner décemment il faut intégrer une étape
   intermédiaire de visualisation sur plaque » — la demande, mot pour mot.
   Cocher `fond-matiere`, `illustration`, `cadre` sans voir les pièces, c'est
   choisir à l'aveugle ; étalées, elles se désignent.

   LA RÈGLE QUI DOMINE CE BLOC : **rien de ce qui suit n'entre dans
   `S.enAttente`**. Sans cette garde, l'utilisateur étale, clique « écrire la
   version », et son modèle part ÉCLATÉ ET DÉFINITIF sur le disque. Chez
   Meshy, « Sur la plaque » est un aperçu ; le modèle assemblé reste la
   vérité. Ici c'est tenu par TROIS mécanismes indépendants, et non par la
   présente phrase :

   1. STRUCTUREL — le décalage d'étalement vit dans un BERCEAU (un Group
      glissé entre la pièce et son parent, voir /lib3d/plaque.js), jamais dans
      `piece.position`. Or le seul producteur d'une ligne `transformer` est
      l'écouteur `objectChange` du gizmo, qui lit `o.position` : il ne PEUT
      pas lire un décalage qui n'y est pas.
   2. COMPORTEMENTAL — le gizmo est lâché en entrant sur la plaque, et
      poserGizmo() le refuse tant qu'elle est affichée.
   3. TEXTUEL — aucune de ces fonctions n'appelle noterAttente(), et
      plaque.js ne connaît ni `fetch` ni la moindre route.

   Un banc de la section N épingle les trois. */

function majBoutonPlaque() {
  const b = $("#btnPlaque");
  /* Le libellé porte la DESTINATION, comme « ← 3D Studio » : ce qu'un clic
     fait, et non l'état où l'on est — l'état, la vue 3D le crie déjà. */
  b.textContent = PLQ.active ? "Assemblé" : "Sur la plaque";
  b.title = PLQ.active
    ? "Revenir au modèle assemblé — l'étalement n'avait rien modifié"
    : "Étaler les pièces pour les voir séparément — une VUE : "
      + "rien n'est modifié, rien n'est écrit";
}

function basculerPlaque() {
  if (PLQ.active) { quitterPlaque(); return; }
  if (!S.vueA || !S.vueA.racine) {
    direRefus("aucun modèle chargé — rien à étaler sur la plaque");
    return;
  }
  /* LE GIZMO LÂCHE AVANT L'ÉTALEMENT, et c'est le piège le plus cher de cette
     tâche. Une pièce tenue par le gizmo puis déplacée par l'étalement resterait
     saisissable : le glissement suivant enverrait au serveur une translation
     née d'un décalage d'AFFICHAGE. Le berceau de plaque.js rend déjà ce chiffre
     impossible à lire ; on lâche quand même, parce qu'un gizmo qui suit une
     pièce en train de s'envoler à l'autre bout de la plaque est un mensonge
     visuel avant d'être un risque, et parce que deux gardes valent mieux
     qu'une sur le mode d'échec qui écrit un GLB faux. */
  if (GIZMO) GIZMO.detach();
  const vue = etaler(S.vueA);
  if (!vue) {
    direRefus("aucune pièce mesurable — ce modèle n'expose aucun nœud glTF "
      + "porteur de géométrie, il n'y a rien à étaler");
    return;
  }
  PLQ.active = true;
  PLQ.pieces = vue.pieces;
  PLQ.teintes = vue.teintes;
  PLQ.partages = vue.partages;
  /* `masquees` n'est PAS vidée ici : oublierPlaque() en répond, et tout
     chemin de sortie de la plaque passe par lui. Une seconde remise à zéro
     ferait chercher au lecteur une divergence qui n'existe pas. */
  PLQ.vides = vue.vides;
  PLQ.axe = vue.axe;
  /* L'empreinte étalée est bien plus large que le modèle assemblé : sans
     re-cadrage, la plaque naîtrait pour moitié hors champ. */
  cadrer(S.vueA);
  majBoutonPlaque();
  /* La plaque vient de choisir son plan : l'un des trois boutons de vue
     regarde désormais l'étalement en face, et c'est lui qui le dit. */
  majBoutonsVue();
  rendreParties();
  /* Le geste a réussi : un refus rouge laissé par le clic d'avant ne doit pas
     lui rester accroché. */
  direGeometrie();
}

/* Revenir à « Assemblé » SANS RECHARGER, et c'est un corollaire de la règle,
   pas une optimisation. Un `ouvrirPrincipale(S.a)` repasserait par le verrou
   de sérialisation et par un téléchargement du GLB — 9 Mo sur le modèle de
   l'utilisateur — pour rendre un modèle que personne n'a modifié. ranger()
   défait ce qu'étaler a fait, dans l'ordre inverse : le berceau retiré et la
   pièce remise à SA place dans la fratrie, la couleur d'origine rendue au
   matériau, la visibilité restaurée, le plateau libéré. */
function quitterPlaque() {
  oublierPlaque();
  /* L'empreinte se rétracte : le cadrage étalé laisserait le modèle assemblé
     minuscule au centre. Symétrique du re-cadrage de basculerPlaque(). */
  if (S.vueA) cadrer(S.vueA);
  rendreParties();
}

/* Le rangement SEC, sans re-cadrage ni redessin : ce que _ouvrirPrincipale()
   appelle avant charger(), qui cadre et redessine lui-même. Séparé de
   quitterPlaque() pour que le chemin du changement de modèle ne cadre pas une
   vue qui va être vidée à la ligne suivante. */
function oublierPlaque() {
  if (!PLQ.active) return;
  ranger(S.vueA);
  PLQ.active = false;
  PLQ.pieces = [];
  PLQ.teintes = new Map();
  PLQ.partages = 0;
  PLQ.vides = 0;
  PLQ.axe = null;
  PLQ.masquees.clear();
  majBoutonPlaque();
  /* Le liseré « fait face à la plaque » s'éteint avec elle : laissé allumé, il
     désignerait le plan d'un étalement qui n'existe plus. */
  majBoutonsVue();
}

$("#btnPlaque").addEventListener("click", basculerPlaque);

/* ── le point de vue : deux projections, trois vues d'axe ───────────────────
   DEUX OPTIONS, ce que la demande dit : celle qui existait — perspective sur
   la direction historique — et une ISOMÉTRIQUE. Le bouton porte la
   DESTINATION comme ses voisins, et chacune de ses deux positions est un point
   de vue COMPLET : « Isométrique » pose la caméra orthographique sur (1, 1, 1),
   « Perspective » rend la caméra à fuite sur la direction d'origine. Une
   bascule qui ne changerait QUE la projection aurait laissé une ortho posée
   sur un trois-quarts — orthographique, oui, isométrique, non : le mot du
   bouton aurait été faux.

   LES TROIS VUES D'AXE passent elles aussi en orthographique, et c'est une
   mesure — 8,6 % de largeur rognée sous perspective — dont la démonstration
   est sous PROJECTION_DE_VUE, plus bas. La bascule n'est donc qu'un raccourci
   vers deux des cinq vues, ce qui rend impossible la seule incohérence que
   deux commandes séparées auraient permise : une projection que la vue ne
   porte pas.

   ET LES DEUX VUES ENSEMBLE, jamais A seule. La comparaison A/B promet un
   point de vue unique ; laisser B en perspective pendant que A passe en
   isométrie comparerait deux projections, ce qui ne compare rien. La
   synchronisation d'OrbitControls rattraperait la projection au premier
   « change », mais pas avant, et pas si la souris ne bouge plus. */

/* L'AXE D'EMPILEMENT DE LA PLAQUE → LA VUE QUI LA REGARDE EN FACE.
   `axeEmpile` choisit son plan d'après les PIÈCES : y pour des volumes posés,
   z pour les douze cartes du modèle réel de l'utilisateur. « Dessus » n'est
   donc pas toujours la vue de la plaque, et faire suivre les libellés aurait
   fait dire à ce bouton qu'il regarde selon X un jour sur deux. Les trois vues
   restent les axes DU MODÈLE — ceux que le serveur nomme dans `axe_haut` — et
   c'est cette table qui DIT laquelle tombe en face, sur le bouton lui-même.
   Les pièces sont posées du côté POSITIF de l'axe (leur minimum y vaut zéro,
   le plateau recule en dessous), donc la caméra du côté positif les regarde de
   face et non par le dos. */
const VUE_DE_PLAQUE = { x: "profil", y: "dessus", z: "face" };

/* Les axes sont ceux DU MODÈLE — ceux-là mêmes que le panneau Fiche nomme dans
   `axe_haut` — et l'infobulle le dit, parce que rien à l'écran ne distingue un
   axe du modèle d'un axe de la plaque. Elle dit aussi la projection : une vue
   d'axe est orthographique (voir PROJECTION_DE_VUE), et l'utilisateur doit
   savoir pourquoi le bouton d'à côté vient de passer à « Perspective ». */
const TITRE_VUE = {
  face: "Depuis +Z, en orthographique — un axe du modèle, pas de la plaque",
  dessus: "Depuis +Y, en orthographique — un axe du modèle, pas de la plaque",
  profil: "Depuis +X, en orthographique — un axe du modèle, pas de la plaque",
};

/* CONSÉQUENCE ASSUMÉE, ET ÉCRITE ICI PLUTÔT QUE DÉCOUVERTE À L'USAGE : le
   libellé se déduit de la PROJECTION, pas de la vue. Depuis « Dessus », qui est
   orthographique, le bouton dit donc « Perspective » et ramène à « libre » — il
   faut deux clics pour revenir à l'isométrie. C'est le prix de la règle « chaque
   vue porte sa projection » (voir PROJECTION_DE_VUE), et c'est le bon prix : un
   bouton qui dirait « Isométrique » alors que la caméra est DÉJÀ
   orthographique mentirait sur ce qu'un clic change. */
function majBoutonProjection() {
  const b = $("#btnProjection");
  const iso = !!(S.vueA && S.vueA.projection === "orthographique");
  /* Le libellé porte la DESTINATION, comme « ← 3D Studio » et « Sur la
     plaque » : ce qu'un clic fait, et non l'état où l'on est — l'état, la vue
     3D le crie déjà. */
  b.textContent = iso ? "Perspective" : "Isométrique";
  b.title = iso
    ? "Revenir à la caméra à fuite, sur la direction d'origine"
    : "Caméra orthographique sur (1, 1, 1) : les fuyantes disparaissent, "
      + "deux longueurs égales se lisent égales où qu'elles soient";
}

function majBoutonsVue() {
  const courante = S.vueA ? S.vueA.vue : null;
  const face = PLQ.active ? VUE_DE_PLAQUE[PLQ.axe] : null;
  for (const b of document.querySelectorAll("#vueCam [data-vue]")) {
    const nom = b.dataset.vue;
    /* Quatre boutons identiques ne disent jamais lequel a été pressé : sans
       cette marque, « Face » cliqué deux fois passe pour un bouton mort. */
    b.classList.toggle("actif", nom === courante);
    b.classList.toggle("plaque", nom === face);
    b.title = TITRE_VUE[nom] + (nom === face
      ? " · c'est cette vue qui regarde la plaque en face" : "");
  }
}

/* LE GIZMO CAPTURE SA CAMÉRA à la construction et la garde pour dimensionner
   ses poignées ET pour les piquer au rayon. Sous une caméra qu'il ne connaît
   pas, elles sont mal taillées et impossibles à attraper — un gizmo visible
   qui ne répond plus, sans erreur nulle part. `camera` est chez lui une
   propriété définie qui repropage la valeur au gizmo et à son plan de saisie
   (TransformControls.js, ligne 103) : lui réaffecter suffit. */
function reposerCameraDuGizmo() {
  if (GIZMO && S.vueA) GIZMO.camera = S.vueA.camera;
}

/* CHAQUE VUE PORTE SA PROJECTION, ET C'EST UNE MESURE, pas un goût.

   Un modèle aussi large que son cube englobant DÉBORDE sous perspective dans
   une vue d'axe. Mesuré hors navigateur sur une boîte 3 × 1,1 × 0,4 dans un
   canevas 430 × 824 (la demi-largeur de la comparaison A/B), vue « dessus » :
   la caméra est posée à 6,940, la face proche à 6,390, et la magnification
   6,940/6,390 = 1,086 met 8,6 % de la largeur hors du cadre — 4,3 % rognés à
   chaque bord. La même vue en orthographique tient à 1,000 000, exactement.

   POURQUOI LE ROGNAGE APPARAÎT LÀ ET PAS AILLEURS : le pire cas d'une vue
   d'axe vaut 1,000·rayon quand celui de la vue libre vaut 1,372, si bien que
   le cadre d'une vue d'axe est SERRÉ sur le modèle et n'a plus de mou pour
   absorber la fuite. Le cadrage de la tâche 3 compare des étendues au plan du
   centre et laisse cette tolérance-là depuis toujours ; l'annuler demanderait
   de reculer avant le seuil de rognage, donc de déplacer aussi le cadrage
   vertical, donc de casser ce que la demande exige de conserver.

   Reste à choisir : rogner, ou projeter parallèlement. Face, dessus et profil
   sont les vues du DESSIN TECHNIQUE — elles existent pour lire une forme sans
   fuyantes, et Blender fait le même choix depuis toujours (le pavé numérique
   bascule en orthographique). Elles passent donc en orthographique, et la
   bascule n'est plus qu'un cas particulier : « libre » est la seule vue à
   fuite, ce que le bouton dit. */
const PROJECTION_DE_VUE = { libre: "perspective", iso: "orthographique",
  face: "orthographique", dessus: "orthographique",
  profil: "orthographique" };

function appliquerVue(nom) {
  if (!S.vueA) {
    direRefus("aucun modèle chargé — il n'y a pas encore de caméra à orienter");
    return;
  }
  /* LES DEUX VUES, jamais A seule : la comparaison A/B promet un point de vue
     unique, et deux projections différentes ne comparent rien. */
  for (const v of [S.vueA, S.vueB]) {
    if (!v) continue;
    /* PROJETER AVANT D'ORIENTER : orienter() recadre, et le cadre d'une ortho
       ne s'écrit pas comme celui d'une perspective. Dans l'autre ordre, le
       cadrage serait fait pour la caméra qu'on s'apprête à quitter. */
    projeter(v, PROJECTION_DE_VUE[nom]);
    orienter(v, nom);
  }
  reposerCameraDuGizmo();
  majBoutonProjection();
  majBoutonsVue();
  /* Le geste a réussi : un refus rouge laissé par le clic d'avant ne doit pas
     lui rester accroché. */
  direGeometrie();
}

/* La bascule N'EST QU'UN RACCOURCI vers deux des cinq vues — c'est ce qui
   garantit qu'elle ne peut pas poser une projection que la vue ne porte pas.
   « Isométrique » emmène sur (1, 1, 1) en orthographique ; « Perspective »
   ramène EXACTEMENT au point de vue d'avant cette tâche, direction historique
   comprise. Deux options complètes, comme la demande les dit. */
function basculerProjection() {
  if (!S.vueA) {
    direRefus("aucun modèle chargé — il n'y a pas encore de caméra à basculer");
    return;
  }
  appliquerVue(S.vueA.projection === "orthographique" ? "libre" : "iso");
}

$("#btnProjection").addEventListener("click", basculerProjection);
for (const b of document.querySelectorAll("#vueCam [data-vue]")) {
  b.addEventListener("click", () => appliquerVue(b.dataset.vue));
}

/* ── le panneau Parties : nœud, maillage, matériau ──────────────────────────
   Trois granularités parce que les moteurs ne découpent pas pareil : un modèle
   Meshy est souvent un nœud UNIQUE à plusieurs matériaux — le lister par nœud
   n'en montrerait qu'une seule ligne — quand un Tripo arrive en plusieurs
   nœuds. Aucune des trois ne suffit seule.

   Ce panneau N'ÉCRIT RIEN. Isoler est un AFFICHAGE : les pièces écartées
   passent en fantôme, aucun GLB n'est fabriqué, aucune route n'est appelée.
   C'est la règle de tête de ce fichier, et /lib3d/selection.js la tient
   structurellement — un banc y interdit la moindre requête réseau. */

/* Le clic dans le canevas n'est branché QU'UNE FOIS : voir l'écouteur plus
   bas, `etabli:charge` est émis à chaque chargement réussi. */
let _clicBranche = false;

function rendreParties() {
  const box = $("#panParties");
  const inv = inventaire(S.vueA);
  const liste = SEL.granularite === "noeud" ? inv.noeuds
    : SEL.granularite === "materiau" ? inv.materiaux : inv.maillages;
  /* esc() partout, attributs data- compris : `nom` vient des noms de nœuds, de
     maillages et de matériaux DU FICHIER GLB, donc du dehors, exactement comme
     les libellés du disque de la tâche 4 — et c'est dans un attribut qu'un
     guillemet casse la ligne entière. `tris`, lui, est compté par selection.js
     sur les tampons de géométrie : c'est un nombre, et le seul chiffre de ce
     balisage à n'avoir traversé aucun fichier.

     ATTRIBUT ABSENT plutôt que VIDE, et c'est un PIÈGE DÉSARMÉ pour la porte
     d'écriture : un matériau n'a pas d'index de nœud, un maillage non indexé
     non plus. Émis à vide, `dataset.index` rendrait "" — et `Number("")` vaut
     ZÉRO, c'est-à-dire LE NŒUD 0 du document, que l'extraction viserait sans
     que rien ne grince, exactement le mode de défaillance qu'indexerNoeuds()
     existe pour empêcher. Absent, `dataset.index` vaut undefined,
     `Number(undefined)` vaut NaN, et la lecture naïve échoue BRUYAMMENT. */
  const rangees = liste.map((x) => `
      <label class="partie">
        <input type="checkbox" data-uuid="${esc(x.uuid)}"
               ${x.indexGltf === undefined ? ""
                 : `data-index="${esc(x.indexGltf)}"`}
               ${SEL.retenus.has(x.uuid) ? "checked" : ""}>${PLQ.teintes.has(x.uuid)
          ? `<i class="pastille" style="background:${esc(PLQ.teintes.get(x.uuid))}"></i>`
          : ""}
        <b>${esc(x.nom)}</b>${x.tris
          ? `<span>${x.tris.toLocaleString("fr-FR")} tri</span>` : ""}
      </label>`).join("");
  /* ── l'œil, ET POURQUOI IL N'EST PAS BRANCHÉ SUR `SEL.retenus` ────────────
     La question était posée : brancher la liste latérale sur la sélection
     existante plutôt qu'en doublon. Réponse : NON pour la VISIBILITÉ, OUI
     pour l'identité — et voici le partage.

     Masquer et retenir ne veulent pas dire la même chose, et ne durent pas
     aussi longtemps. `SEL.retenus` est la CHARGE : separerSelection() la
     convertit en index de nœud et la met en file pour le serveur, QUI ÉCRIT
     UN GLB. La visibilité est un geste d'écran, qui meurt quand on revient à
     « Assemblé ». Les confondre donnerait ceci : l'utilisateur masque trois
     pièces pour mieux voir les autres, et perd trois pièces de son
     extraction — en silence, exactement le mode d'échec que cette page
     traque partout ailleurs.

     Deux raisons de plus, mécaniques. `SEL.retenus` est VIDÉ à chaque
     changement de granularité (l'uuid d'un matériau ne désigne pas un
     maillage) : l'œil perdrait son état en passant sur l'onglet
     « matériau ». Et la plaque ne connaît qu'une granularité, le NŒUD, alors
     que le panneau en offre trois : les lier forcerait le panneau au nœud,
     ou mêlerait les vocabulaires que SEL.retenus garde homogènes.

     CE QUI EST PARTAGÉ, donc, et qui suffit : la COULEUR. Chaque rangée du
     panneau — nœud ou maillage — porte la pastille de la pièce à laquelle
     elle appartient (`PLQ.teintes`, que plaque.js remplit sur tout le
     sous-arbre). Le nom qu'on coche est visiblement la pièce qu'on voit sur
     le plateau, sans qu'aucun état ne soit dupliqué ni qu'aucun geste de vue
     ne puisse abîmer une charge d'écriture. La sélection reste où elle
     était, dans un seul vocabulaire. */
  const oeil = (cle) => (PLQ.masquees.has(cle) ? "montrer" : "masquer");
  const plaqueBloc = !PLQ.active ? "" : `
    <div class="plaque-tete">Sur la plaque · ${PLQ.pieces.length} pièce(s)</div>
    <div class="plaque-liste">${PLQ.pieces.map((x) => `
      <div class="plaque-rang${PLQ.masquees.has(x.cle) ? " masquee" : ""}">
        <i class="pastille" style="background:${esc(x.couleur)}"></i>
        <b>${esc(x.nom)}</b>
        <button class="plaque-oeil" data-cle="${esc(x.cle)}"
                title="${oeil(x.cle)} cette pièce"
                aria-label="${oeil(x.cle)} cette pièce"
        >${PLQ.masquees.has(x.cle) ? "◌" : "◉"}</button>
      </div>`).join("")}</div>
    <p class="plaque-note">Vue seulement : le modèle assemblé reste la
      vérité, rien n'est modifié ni écrit.${PLQ.vides
        ? ` ${PLQ.vides} nœud(s) sans géométrie ne sont pas étalés : un
      contenant n'a rien à montrer, et son œil ne commanderait rien.` : ""}${PLQ.partages
        ? ` ${PLQ.partages} matériau(x) partagé(s) entre pièces — leur teinte
      sur le modèle n'est pas fidèle (le dernier parcouru gagne) ; la
      pastille, elle, l'est.` : ""}</p>`;
  /* Les deux boutons sont rendus MÊME quand la liste est vide : ils sont relus
     juste après par leur id, et un panneau sans eux ferait lever le
     addEventListener sur null. isoler() garde de son côté le cas « aucun
     modèle chargé ». */
  box.innerHTML = `${plaqueBloc}
    <div class="granularite">
      ${["noeud", "maillage", "materiau"].map((g) =>
        `<button data-g="${g}" class="${g === SEL.granularite ? "actif" : ""}">${LIBELLE_GRANULARITE[g]}</button>`
      ).join("")}
    </div>
    <div class="parties">${rangees || `<div class="vide">${S.vueA && S.vueA.racine
      ? "aucune partie à cette granularité" : "aucun modèle chargé"}</div>`}</div>
    <div class="parties-actions">
      <button id="btnIsoler">Isoler la sélection</button>
      <button id="btnToutVoir">Tout revoir</button>
      <button id="btnSeparer">Séparer la sélection en une version</button>
    </div>`;

  box.querySelectorAll("[data-g]").forEach((b) =>
    b.addEventListener("click", () => {
      /* On VIDE en changeant de granularité : l'uuid d'un matériau ne désigne
         pas un maillage, et une sélection mêlée partirait telle quelle au
         serveur en tâche 8. */
      SEL.granularite = b.dataset.g; SEL.retenus.clear();
      /* Le bleu appartenait à la sélection qu'on vient de vider : le laisser
         ferait croire qu'un maillage est encore retenu. surligner() accepte
         null et restaure tout — aucune ligne neuve. */
      surligner(S.vueA, null);
      rendreParties();
    }));
  box.querySelectorAll("input[type=checkbox]").forEach((c) =>
    c.addEventListener("change", () => {
      if (c.checked) SEL.retenus.add(c.dataset.uuid);
      else SEL.retenus.delete(c.dataset.uuid);
    }));
  /* L'œil ne change QUE `piece.visible` (dans plaque.js), et il ne note son
     basculement que si la pièce a répondu : sur une plaque déjà rangée sous
     nos pieds, la liste et le modèle resteraient sinon en désaccord. */
  box.querySelectorAll(".plaque-oeil").forEach((b) =>
    b.addEventListener("click", () => {
      const cle = Number(b.dataset.cle);
      const masquee = PLQ.masquees.has(cle);
      if (!montrerPiece(S.vueA, cle, masquee)) return;
      if (masquee) PLQ.masquees.delete(cle); else PLQ.masquees.add(cle);
      rendreParties();
    }));
  $("#btnIsoler").addEventListener("click", () => isoler(S.vueA, [...SEL.retenus]));
  /* « Tout revoir » n'est pas un second chemin : isoler SUR RIEN restaure, par
     la ligne de code même qui isole. Les deux ne peuvent donc pas diverger. */
  $("#btnToutVoir").addEventListener("click", () => isoler(S.vueA, []));
  /* Le bouton de séparation est RENDU par le gabarit ci-dessus, exactement
     comme ses deux voisins, et branché ici : il ne PEUT donc pas s'empiler.
     Il fut un temps greffé au panneau par une fonction à part, et sa sûreté
     dépendait alors de l'endroit d'où on appelait celle-ci — un danger qu'il
     fallait garder au banc. On retire le danger plutôt que de le garder. La
     conversion uuid → index, elle, reste dans separerSelection(), avec la
     porte d'écriture à qui elle appartient. */
  $("#btnSeparer").addEventListener("click", separerSelection);
}

/* ── la porte d'écriture : séparer, transformer, réparer ────────────────────
   TANT QUE « écrire la version » N'A PAS ÉTÉ CLIQUÉ, RIEN N'A BOUGÉ SUR LE
   DISQUE. Le gizmo, « Séparer » et le bloc Réparer ne font qu'une chose :
   poser une ligne dans `S.enAttente`. La barre du bas l'énumère, et
   ecrireVersion() est le seul chemin de cette page vers les trois plumes de
   P1 — la règle de tête du fichier, tenue par un seul entonnoir. */

/* ── le gizmo ───────────────────────────────────────────────────────────────
   PIÈGE MESURÉ, ET MUET. Dans le three.js vendorisé (0.185.1),
   `TransformControls` n'est PLUS un Object3D : le fichier
   /assets/three/addons/controls/TransformControls.js déclare, ligne 77,
   `class TransformControls extends Controls`. Or `Object3D.add()` d'un
   non-Object3D se contente d'un avertissement en console et rend la main sans
   rien faire — le gizmo ne serait jamais visible, et aucun banc qui lit du
   texte ne le verrait. Ce qui entre dans la scène est son HELPER :
   `getHelper()` (ligne 453) rend `this._root` (ligne 455), un
   `TransformControlsRoot extends Object3D` (ligne 1111) que le constructeur
   fabrique une fois (lignes 89-90) et qui porte le gizmo et son plan de
   saisie. Le constructeur branche lui-même ses écouteurs sur le canevas
   (ligne 418, `this.connect(domElement)`) : rien d'autre à câbler.

   POUR LE RETIRER PROPREMENT, le jour où cette page démonterait sa vue :
   `S.vueA.scene.remove(GIZMO.getHelper())` puis `GIZMO.dispose()` (ligne 789),
   qui déconnecte les écouteurs du canevas et appelle `_root.dispose()`
   (ligne 793, défini ligne 1176) — lequel libère géométries et matériaux du
   gizmo. On ne le fait nulle part : le canevas vit autant que la page, comme
   le dit viewer.js (« Libère le MODÈLE, pas le CANEVAS »). */
function poserGizmo(objet) {
  /* LA PLAQUE EST UNE VUE : on n'y manipule pas. Un gizmo posé sur une pièce
     étalée enverrait au serveur une pose née d'un décalage d'AFFICHAGE — le
     modèle écrit serait éclaté. Le berceau de plaque.js rend déjà ce chiffre
     illisible (le décalage n'est pas dans `piece.position`), et cette garde
     ferme la porte une seconde fois : deux mécanismes indépendants sur le
     seul mode d'échec de cette tâche qui écrive un GLB faux. On le DIT, comme
     partout sur cette page, plutôt que de laisser un clic sans effet. */
  if (estEtalee(S.vueA)) {
    if (GIZMO) GIZMO.detach();
    direRefus("la plaque est une VUE : revenez à « Assemblé » pour "
      + "déplacer une pièce");
    return;
  }
  /* On REMONTE jusqu'au premier ancêtre qui EST un nœud du document. Un
     maillage à plusieurs primitives donne, chez GLTFLoader, un Group pour le
     nœud et un Mesh par primitive ; la primitive n'a pas de `nodes` dans la
     Map du parser, et indexerNoeuds() refuse délibérément de lui en inventer
     un. C'est le Group qu'il faut manipuler — c'est lui que le serveur sait
     nommer. Sans cette remontée, un Meshy à deux matériaux refuserait le
     gizmo. La remontée s'arrête à la racine du modèle : au-delà commence la
     scène du canevas. */
  let noeud = objet;
  while (noeud && (!noeud.userData || noeud.userData.indexGltf === undefined)) {
    noeud = noeud === S.vueA.racine ? null : noeud.parent;
  }
  if (!noeud) {
    /* Manipuler ce que le serveur ne sait pas nommer donnerait un glissement
       joli et sans effet : la file resterait vide, l'utilisateur croirait
       avoir déplacé quelque chose. On le DIT, et on lâche le gizmo. */
    if (GIZMO) GIZMO.detach();
    direRefus("ce maillage n'est rattaché à aucun nœud glTF — "
      + "rien à envoyer au serveur, donc rien à déplacer");
    return;
  }
  if (!GIZMO) {
    GIZMO = new TransformControls(S.vueA.camera, S.vueA.renderer.domElement);
    /* le gizmo et l'orbite se disputent la souris : l'un désarme l'autre */
    GIZMO.addEventListener("dragging-changed", (e) => {
      S.vueA.controls.enabled = !e.value;
    });
    GIZMO.addEventListener("objectChange", () => {
      const o = GIZMO.object;
      if (!o || !o.userData || o.userData.indexGltf === undefined) return;
      /* Le quaternion part TEL QUEL. `mesh_edit.transformer` refuse un
         quaternion non normé, en 400, et sa docstring dit pourquoi :
         « Normaliser un quaternion en douce masquerait un bug amont ; le
         refuser le montre. » Le normaliser ICI masquerait le même bug d'un
         cran plus haut. Le refus, lui, remonte jusqu'à la barre du bas par le
         `catch` d'ecrireVersion() — sans lui, la promesse partirait dans le
         vide et la barre resterait figée sur « en attente » sans rien dire. */
      noterAttente("transformer", {
        [o.userData.indexGltf]: {
          translation: [o.position.x, o.position.y, o.position.z],
          rotation: [o.quaternion.x, o.quaternion.y, o.quaternion.z,
                     o.quaternion.w],
          scale: [o.scale.x, o.scale.y, o.scale.z],
        },
      }, o.userData.indexGltfSource);
    });
    S.vueA.scene.add(GIZMO.getHelper());
  }
  GIZMO.attach(noeud);
  /* Le refus qu'un clic PRÉCÉDENT a pu laisser portait sur un autre maillage :
     le laisser rouge ferait passer ce geste-ci, qui a réussi, pour un échec. */
  direGeometrie();
}

/* Rien n'est écrit tant que le bouton n'est pas cliqué : la file est la
   mémoire de ce qui attend, et la barre du bas la montre.

   FUSION plutôt que remplacement pour `transformer`, et c'est un piège
   désarmé : la route accepte un dictionnaire de PLUSIEURS nœuds, et remplacer
   l'entrée entière perdrait le premier nœud déplacé au profit du second —
   sans que rien ne le dise, la barre continuant d'annoncer « 1 modification
   en attente ».

   `reparer` se remplace au contraire, et c'est juste : c'est un réglage
   d'assise, pas une accumulation. `extraire` se remplace AUSSI, et c'est une
   décision : sa charge est la sélection VISIBLE du panneau Parties. Cumuler
   ferait diverger la file de ce que les cases à cocher montrent — on ne
   pourrait plus retirer un nœud d'une extraction déjà en attente, alors que
   le décocher est le geste évident. La file dit ce que le panneau dit.

   `source` est la PROVENANCE de l'index (voir indexerNoeuds) : « associations »
   est la carte du GLTFParser, « nom » une heuristique que son propre
   commentaire décrit comme faillible en trois cas. Ces index partent au
   serveur, QUI ÉCRIT UN GLB : un index faux écrirait sur le mauvais maillage
   sans que rien ne grince. On ne refuse pas — le repli vaut mieux que rien —
   on le DIT dans la barre avant que le bouton ne soit cliqué. C'est la seule
   occasion où ce marqueur peut servir ; s'il ne sert pas ici, il ne servira
   jamais et il ne fallait pas l'écrire. */
function noterAttente(operation, charge, source) {
  const doute = source !== undefined && source !== "associations";
  const i = S.enAttente.findIndex((x) => x.operation === operation);
  if (i >= 0 && operation === "transformer") {
    Object.assign(S.enAttente[i].charge, charge);
    S.enAttente[i].heuristique = S.enAttente[i].heuristique || doute;
  } else if (i >= 0) {
    S.enAttente[i] = { operation, charge, heuristique: doute };
  } else {
    S.enAttente.push({ operation, charge, heuristique: doute });
  }
  rendreAttente();
}

/* La file dans l'ordre où elle sera ÉCRITE, jamais dans celui des clics.
   Rendue triée à la barre aussi, pour que ce qu'on lit soit ce qui partira. */
function fileOrdonnee() {
  return [...S.enAttente].sort((a, b) =>
    ORDRE_ECRITURE.indexOf(a.operation) - ORDRE_ECRITURE.indexOf(b.operation));
}

/* La barre ÉNUMÈRE, elle ne se contente pas de compter : c'est ce détail qui
   rend la fusion visible — « 2 nœud(s) déplacé(s) » et non deux fois
   « 1 modification », qui aurait laissé passer l'écrasement en silence. */
const libelleAttente = (t) =>
  t.operation === "transformer"
    ? `${Object.keys(t.charge).length} nœud(s) déplacé(s)`
    : t.operation === "extraire"
      ? `${t.charge.length} nœud(s) à séparer`
      : `assise : axe ${t.charge.axe_haut}, échelle ${t.charge.echelle}`
        + (t.charge.recentrer ? ", recentré" : "");

function rendreAttente() {
  const box = $("#barreAttente");
  if (!S.enAttente.length) { box.innerHTML = ""; return; }
  const liste = fileOrdonnee().map(libelleAttente).join(" · ");
  /* esc() comme partout dans ce fichier : `axe_haut` vient d'un <select> et
     les comptes sont des nombres, mais l'invariant ne se négocie pas au cas
     par cas — c'est ainsi qu'il survit à la prochaine tâche. */
  const doute = S.enAttente.some((t) => t.heuristique)
    ? `<span class="attente-doute">index de nœud déduits d'un NOM — repli heuristique, à vérifier</span>`
    : "";
  /* Le `title` n'est pas décoratif : l'énumération se RÉORDONNE sous les yeux
     de l'utilisateur (fileOrdonnee), et rien à l'écran ne dirait pourquoi.
     Le bouton d'écriture, lui, porte l'état du VERROU : rendre la barre est
     le seul geste qui le montre, et ecrireVersion() la refait des deux côtés
     de la série. Sans cela, le bouton renaîtrait actif au milieu des requêtes
     et le clic se solderait par un `return` muet — ce que ce fichier refuse
     partout ailleurs. */
  box.innerHTML = `<b>${S.enAttente.length} modification(s) en attente</b>
    <span class="attente-liste" title="ordre d'écriture imposé : réparer, puis transformer, puis séparer — l'extraction renumérote les nœuds, elle passe donc en dernier">${esc(liste)}</span>${doute}
    <button id="btnEcrire"${_ecritEnCours ? " disabled" : ""}>écrire la version</button>
    <button id="btnAnnuler">annuler</button>`;
  $("#btnEcrire").addEventListener("click", ecrireVersion);
  $("#btnAnnuler").addEventListener("click", () => {
    S.enAttente.length = 0;
    rendreAttente();
    /* Le modèle est REchargé : le gizmo a déplacé des objets three.js, et
       rien d'autre ne saurait leur rendre leur pose. Le geste reste gardé —
       S.a est null quand le dernier chargement a échoué. */
    if (S.a) ouvrirPrincipale(S.a);
  });
}

async function ecrireVersion() {
  if (!S.a) { direRefus("aucun modèle chargé — rien à écrire"); return; }
  /* UN VERROU, et il court jusqu'à la QUEUE de la fonction. La fenêtre
     dangereuse n'est pas la boucle d'écriture : c'est tout l'intervalle où
     `S.a` ne correspond pas encore au disque. Pendant le rechargement final —
     le téléchargement d'un GLB, plusieurs secondes sur un modèle lourd — S.a
     porte encore la cible d'AVANT l'écriture, le gizmo tient encore un nœud
     du modèle sortant, et rendreAttente() vient de refaire la barre. Un
     glissement de gizmo dans cette fenêtre repeuple la file et fait renaître
     un bouton ACTIF ; un clic relancerait la série sur la version d'avant,
     alors que N+1 existe déjà sur le disque. C'est la fourche même que ce
     verrou existe pour empêcher.

     Le `return` sec ci-dessous n'est donc jamais le seul refus : le bouton
     est rendu grisé tant que le verrou tient (voir rendreAttente), et la
     barre est refaite des DEUX côtés de la série. */
  if (_ecritEnCours) return;
  _ecritEnCours = true;
  rendreAttente();                  /* la barre relit le verrou : le bouton grise */
  const ecrites = [];
  let derniere = null, echec = null, adopte = false;
  try {
    try {
      /* Une étape venue d'une tâche Meshy n'a pas de job où se versionner : on
         la fait adopter d'abord (spec §6.2). Une seule provenance, pas deux.
         L'adoption COPIE `model.glb` tel quel (shutil.copy2) : les index de
         nœud déjà en file restent donc valides sur le job neuf. */
      if (!S.a.job && S.a.meshy) {
        const ad = await jpost("/api/etabli/adopter", { task_id: S.a.meshy });
        /* Et elle a ÉCRIT SUR LE DISQUE : un dossier, une copie du GLB, un
           registre. Le compte rendu doit le dire, sans quoi « écrit : rien »
           serait faux au moment même où rendreChrono() fait apparaître le job
           neuf dans la chronologie, sous les yeux de l'utilisateur. On ne le
           pousse pas dans `ecrites` pour autant : ce n'est pas une opération
           de la file, la copie est octet pour octet, les index restent
           valides — la vider serait la punir pour une réussite. */
        adopte = true;
        S.a = { ...S.a, job: ad.job, version: ad.version, url: ad.url };
      }
      /* L'étape « décimée » est un FICHIER À PART (`model.opt.glb`) et n'a pas
         de numéro : mesh_sources lui donne `version: null`. Or la route
         retombe sur la version 1 quand le corps n'en porte pas — écrire d'ici
         partirait du BROUILLON, qui n'a ni la même géométrie ni les mêmes
         index que ce qui est à l'écran. Un GLB faux, sur disque, en silence.
         ficheDe() refuse déjà cette étape pour exactement la même raison. */
      if (!S.a.version) {
        throw new Error("l'étape « décimée » n'est pas une version numérotée : "
          + "chargez une version pour la corriger");
      }
      const base = { job: S.a.job, version: S.a.version };
      for (const t of fileOrdonnee()) {
        const corps = t.operation === "transformer"
          ? { ...base, transforms: t.charge }
          : t.operation === "extraire"
            ? { ...base, noeuds: t.charge }
            : { ...base, ...t.charge };
        derniere = await jpost(ROUTES[t.operation], corps);
        ecrites.push(t.operation);
        /* LE CHAÎNAGE, et c'est lui qui fait de la série une LIGNÉE : sans
           cette ligne, les trois opérations repartent toutes de la version de
           départ et écrivent trois versions SŒURS nées du même parent — la
           deuxième perd la première, la troisième perd les deux, et le
           registre garde les trois comme si de rien n'était. */
        base.version = derniere.version;
      }
    } catch (e) {
      /* Sans ce bloc, un refus du serveur — un quaternion non normé, un GLB
         meshopt que l'extraction ne sait pas recopier — partirait dans le
         vide : la promesse serait rejetée sans témoin, la barre resterait
         figée sur « en attente », et l'utilisateur ne saurait pas que rien
         n'a bougé. */
      echec = e;
    }
    const restantes = fileOrdonnee().map((t) => t.operation)
      .filter((op) => !ecrites.includes(op));
    /* La file est vidée DÈS QUE quelque chose a touché le disque, et pas
       seulement en cas de succès complet : ce qui reste est indexé sur le
       modèle d'AVANT, et la version qu'on s'apprête à ouvrir n'est plus
       celui-là. Rejouer le reste depuis l'ancienne version FOURCHERAIT
       l'historique en silence — deux branches nées de la même base, sans que
       rien ne le dise. Si RIEN n'a été écrit, rien n'a bougé non plus à
       l'écran : la file reste intacte, et le refus se lit dans la barre. */
    if (ecrites.length) S.enAttente.length = 0;
    rendreAttente();
    try {
      /* La chronologie apprend les versions neuves MÊME en cas d'échec
         partiel : ce qui est passé existe sur disque et doit se voir. */
      S.sources = await jget("/api/etabli/sources");
      rendreChrono();
    } catch { /* la chronologie précédente reste : elle n'a menti sur rien */ }
    if (derniere) {
      const cible = { ...S.a, version: derniere.version,
        url: `/api/assets/3d/${S.a.job}/version/${derniere.version}`,
        libelle: `version ${derniere.version}` };
      const ouvert = await ouvrirPrincipale(cible);
      /* LE MOMENT DE LA VIGNETTE, et il n'est pas négociable : APRÈS la
         réouverture. Capturer plus haut photographierait la version
         PRÉCÉDENTE — la vignette mentirait, ce qui est pire que pas de
         vignette du tout. Et SEULEMENT si la réouverture a rendu vrai : ce
         booléen dit `S.a === cible`, seule réponse honnête à « est-ce que MA
         cible est à l'écran ? ». Un échec de chargement laisse le canevas
         VIDE (charger() vide la vue AVANT d'échouer), et on écrirait alors la
         vignette blanche qu'on prétend supprimer.

         HORS DE LA FILE DE SÉRIALISATION, aussi : l'`await` ci-dessus attend
         que `_file` se soit vidée, la capture vient APRÈS elle et ne s'y
         greffe pas. Greffée, elle ferait attendre tout clic suivant sur un
         encodage PNG et un aller-retour réseau — et un rejet y laisserait la
         file rejetée pour toujours, comme le dit ouvrirPrincipale().

         LE `.catch` EST UNE CEINTURE, et il en faut une : la capture dit déjà
         ses échecs dans la barre et ne rejette pas, mais le `try` de cette
         fonction-ci n'a PAS de `catch`. Un rejet inattendu partirait dans le
         vide APRÈS une écriture RÉUSSIE. La version est sur le disque, c'est
         ce qui compte ; la vignette est un agrément. */
      if (ouvert) {
        await capturerVignette(cible.job, cible.version).catch(() => {});
      }
    }
    if (echec) {
      /* APRÈS le rechargement, et c'est tout le soin : _ouvrirPrincipale()
         réécrit #barreGeo, donc un refus posé avant lui disparaîtrait sans
         avoir été lu. On dit ce qui est passé ET ce qui ne l'est pas — un
         « échec » sec laisserait croire que le disque n'a pas bougé. */
      direRefus(`écrit : ${ecrites.join(", ") || "rien"}`
        + (adopte ? ` · adoption faite (job ${S.a.job})` : "")
        + ` · abandonné : ${restantes.join(", ") || "rien"}`
        + ` — ${echec.message}`);
    }
  } finally {
    /* Le verrou tombe ici, et pas une ligne plus haut : un `finally` est le
       seul endroit dont on sorte à coup sûr, et un verrou resté posé
       condamnerait le bouton pour le reste de la session — pire que ce qu'il
       empêche. La barre est refaite juste après pour que le bouton, qui
       porte l'état du verrou, cesse d'être grisé. */
    _ecritEnCours = false;
    rendreAttente();
  }
}

/* ── la vignette de la version écrite ───────────────────────────────────────
   POURQUOI ELLE EXISTE, ET C'EST MESURÉ. L'onglet « Établi » de la
   Bibliothèque montrait des vignettes blanches parce que l'image N'EXISTE PAS
   SUR LE DISQUE pour la plupart des jobs : sur les trois jobs de
   l'utilisateur, un seul porte un vrai rendu de moteur (190 couleurs
   distinctes) ; un autre a un `preview.png` ET un `shot_0.png` qui sont le
   MÊME aplat ambré (14 couleurs) ; le troisième n'a ni rendu ni shot, rien
   que des masques de silhouette. L'ordre de préférence du serveur a été
   corrigé — `preview` → `shot_0` → silhouette — et il était juste, mais aucun
   ordre n'invente une image absente. Le seul remède est de la FABRIQUER : la
   page affiche déjà le maillage cadré, elle capture son canevas.

   ET LA RÈGLE STRUCTURANTE TIENT — il faut le dire, sinon le prochain lecteur
   croira à une entorse. « Le navigateur voit et manipule, PYTHON ÉCRIT »
   porte sur l'AUTORITÉ DU MAILLAGE : aucun GLB ne naît ici, ce fichier ne
   contient l'ombre d'aucun exportateur three.js, et le banc
   `test_la_page_ne_fabrique_jamais_un_glb` reste vert. Une vignette PNG n'est
   pas un maillage : c'est une PHOTO de ce que le canevas montre déjà, et le
   fichier sur le disque est écrit par `/api/etabli/vignette`, en Python, dans
   le dossier du job — le navigateur voit, Python écrit.

   (Ce paragraphe NE NOMME PAS la classe d'export interdite, alors que ce
   serait plus clair : ce banc-là cherche ce nom dans le fichier ENTIER, et
   l'écrire ici le ferait rougir sur sa propre prose. Le défaut que ce dépôt a
   corrigé huit fois, pris à l'envers.)

   À L'ÉCRITURE SEULEMENT. Décision de l'utilisateur, assumée : pas de
   rattrapage à l'ouverture, pas de bouton « régénérer », pas de traitement
   par lots. Ses productions actuelles resteront sans vignette jusqu'à ce
   qu'il en écrive de neuves — le prix achète qu'aucune écriture disque ne le
   surprenne. Un seul site d'appel, donc, dans ecrireVersion(), et un banc
   compte les appels pour que cela le reste. */

/* Le plus grand côté de la vignette envoyée. 512 est la taille des vignettes
   3D du dépôt — `mesh_report.SILHOUETTE_PX`, les planches de matériaux — et
   l'ordre de grandeur d'un `preview.png` de moteur. Un canevas d'écran fait
   couramment 2000×1500 sur un écran HiDPI (viewer.js va jusqu'à
   `setPixelRatio(2)`) : envoyer ce tampon-là ferait plusieurs mégaoctets pour
   une carte de bibliothèque large de deux cents pixels. */
const VIGNETTE_PX = 512;

/* Le canevas du rendu, RAMENÉ à la taille d'une vignette.

   SYNCHRONE À DESSEIN. `drawImage` LIT le tampon de dessin du canevas WebGL,
   exactement comme `toDataURL` : elle tombe sous la même règle que
   capturerVignette() explique ci-dessous, et un `await` glissé ici rendrait
   une image transparente.

   L'ASPECT EST GARDÉ, et l'échelle bornée à 1. Écraser le rendu dans un carré
   déformerait les proportions, ce que cette page-ci existe justement pour
   montrer ; et on RÉDUIT, on n'agrandit jamais un rendu de 400 px en 512
   flous. */
function reduireCanevas(source) {
  const w = source.width || 1, h = source.height || 1;
  const k = Math.min(1, VIGNETTE_PX / Math.max(w, h));
  const hors = document.createElement("canvas");
  hors.width = Math.max(1, Math.round(w * k));
  hors.height = Math.max(1, Math.round(h * k));
  hors.getContext("2d").drawImage(source, 0, 0, hors.width, hors.height);
  return hors;
}

/* Fabrique la vignette de la version qui vient d'être écrite, et l'envoie.

   PIÈGE 1, MESURÉ ET MUET : UN CANEVAS WEBGL EST VIDE À LA LECTURE.
   `creerCanevas()` construit son `WebGLRenderer` sans `preserveDrawingBuffer`,
   donc à `false` — le tampon de dessin est effacé dès que le compositeur l'a
   pris. Lu à n'importe quel autre moment, le canevas rend une image
   TRANSPARENTE, sans la moindre erreur nulle part : ce serait la vignette
   blanche qu'on prétend supprimer, fabriquée par nos soins. Le remède ne
   demande PAS de toucher `creerCanevas`, canevas partagé du dépôt dont
   viewer.js annonce qu'un autre écran le réutilisera un jour : il suffit de
   RENDRE ET DE LIRE DANS LE MÊME TOUR, sans un seul `await` entre les deux.
   L'ordre de ces deux lignes est donc porteur, et un banc l'épingle.

   PIÈGE 2 : LE GIZMO EST DANS LA SCÈNE. poserGizmo() y ajoute
   `GIZMO.getHelper()`, et `attach()` le rend visible : photographié, il
   poserait trois flèches rouge/vert/bleu en travers du maillage. On le masque
   avant le rendu et on le rétablit dans un `finally` — Y COMPRIS SI LA
   CAPTURE LÈVE, sans quoi un contexte WebGL perdu laisserait le gizmo
   invisible pour le reste de la session : l'utilisateur cliquerait un nœud et
   ne verrait rien apparaître, sans qu'aucun message ne l'explique. L'état est
   RELU plutôt que supposé — `detach()` a pu l'effacer entre-temps, et c'est
   même ce que fait _ouvrirPrincipale() juste avant nous ; ne pas en dépendre
   coûte une variable et survit au jour où cet ordre changera.

   PIÈGE 3 : UN ÉCHEC DE VIGNETTE N'EST PAS UN ÉCHEC D'ÉCRITURE. La version
   est sur le disque quoi qu'il arrive ici. Les deux moitiés — fabriquer,
   envoyer — ont donc chacune leur filet, et le message le rappelle au lieu de
   laisser croire que la correction a été perdue. */
async function capturerVignette(job, version) {
  const vue = S.vueA;
  /* PIÈGE 4 : LA FILE. Ni `_file` ni `_demande` n'apparaissent ici, et c'est
     une contrainte, pas un hasard : la file de sérialisation d'ouvrir-
     Principale() est déjà vidée quand l'appelant nous attend. S'y greffer
     ferait patienter tout clic suivant sur un encodage PNG et un aller-retour
     réseau, et un rejet y laisserait la file rejetée pour toujours. */
  if (!vue || !vue.racine) return;
  let reduite;
  const helper = GIZMO ? GIZMO.getHelper() : null;
  const visible = helper ? helper.visible : false;
  try {
    if (helper) helper.visible = false;
    /* RENDRE, PUIS LIRE — dans cet ordre, dans le même tour, sans attente. */
    vue.renderer.render(vue.scene, vue.camera);
    reduite = reduireCanevas(vue.renderer.domElement);
  } catch (e) {
    direRefus(`vignette non fabriquée (${e.message}) — la version `
      + `${version} est écrite`);
    return;
  } finally {
    if (helper) helper.visible = visible;
  }
  try {
    const png = await new Promise((tenir, casser) => reduite.toBlob(
      (b) => (b ? tenir(b) : casser(new Error("toBlob n'a rien rendu"))),
      "image/png"));
    /* Le serveur vérifie la signature PNG, borne la taille, aplatit `job` et
       exige que la version existe : cet en-tête est une politesse, pas une
       preuve, et il le sait. */
    const r = await fetch(`/api/etabli/vignette?job=${encodeURIComponent(job)}`
      + `&version=${encodeURIComponent(version)}`,
      { method: "POST", headers: { "Content-Type": "image/png" }, body: png });
    if (!r.ok) throw new Error((await r.text()).split("\n")[0] || `${r.status}`);
  } catch (e) {
    direRefus(`vignette non envoyée (${e.message}) — la version `
      + `${version} est écrite`);
  }
}

/* Séparer : la sélection courante part comme nouvelle version. */
function separerSelection() {
  /* ICI se rencontrent les deux vocabulaires : `SEL.retenus` porte des uuid
     three.js, le serveur veut des index de nœud glTF. isoler() refuse
     délibérément de faire la conversion et son commentaire renvoie à cette
     porte — « la conversion appartient à qui mêlera les deux vocabulaires ».
     Un uuid de MATÉRIAU ne se retrouve pas dans le graphe : il tombe donc
     naturellement, comme un maillage sans index. */
  let source;
  const idx = [...SEL.retenus]
    .map((u) => {
      let trouve;
      if (S.vueA && S.vueA.racine) {
        S.vueA.racine.traverse((o) => { if (o.uuid === u) trouve = o; });
      }
      if (!trouve || !trouve.userData) return undefined;
      if (trouve.userData.indexGltf !== undefined
          && trouve.userData.indexGltfSource !== "associations") {
        source = trouve.userData.indexGltfSource;
      }
      return trouve.userData.indexGltf;
    })
    .filter((x) => x !== undefined);
  if (!idx.length) {
    /* La page a déjà une façon de refuser en le disant, et ce n'est pas une
       boîte modale du navigateur : la barre du bas. */
    direRefus("aucun nœud glTF dans la sélection — un matériau, ou une "
      + "primitive de maillage, n'a pas d'index à envoyer");
    return;
  }
  noterAttente("extraire", idx, source);
  /* Le geste a réussi : un refus rouge laissé par le clic d'avant ne doit pas
     lui rester accroché. */
  direGeometrie();
}

/* ── le panneau Fiche : réparer l'assise ────────────────────────────────────
   Trois réglages GLOBAUX, portés par mesh_edit.reparer : l'axe haut, une
   échelle, un recentrage. Comme partout ailleurs sur cette page, le bouton
   n'écrit rien — il pose une ligne dans la file. */
function rendreFiche() {
  $("#panFiche").innerHTML = `
    <div class="dt-label">Réparer l'assise</div>
    <label>axe haut
      <select id="fAxe"><option value="Y">Y (glTF, Unity, Godot)</option>
      <option value="Z">Z (Blender, Unreal)</option></select></label>
    <label>échelle <input id="fEchelle" type="number" step="0.01" value="1"></label>
    <label><input id="fRecentrer" type="checkbox"> recentrer sur l'origine</label>
    <button id="fAppliquer">Mettre en attente</button>
    <p class="note">Le recentrage a besoin de la géométrie : sur un GLB
      compressé il refuse, en le disant. L'axe et l'échelle passent quand
      même.</p>`;
  $("#fAppliquer").addEventListener("click", () => {
    if (!S.a) { direRefus("aucun modèle chargé — rien à réparer"); return; }
    /* Les trois clés sont celles que la route attend, au caractère près :
       `axe_haut`, `echelle`, `recentrer`. Une faute de frappe ici passerait
       en 200 et ne corrigerait RIEN — la route lit `body.get(...)` et prend
       un absent pour un « laisse tel quel ». */
    noterAttente("reparer", {
      axe_haut: $("#fAxe").value,
      echelle: Number($("#fEchelle").value) || 1,
      recentrer: $("#fRecentrer").checked,
    });
  });
}

document.addEventListener("etabli:charge", () => {
  /* Le pont vers le vocabulaire du serveur, refait à CHAQUE modèle : les
     objets sont neufs, et la Map du chargeur aussi. */
  indexerNoeuds(S.vueA);
  rendreParties();
  /* Et le formulaire d'assise repart à neuf : un axe ou une échelle laissés
     d'un modèle à l'autre décriraient une correction que personne n'a
     demandée pour CE maillage-ci. */
  rendreFiche();
  /* PIÈGE : cet évènement est émis à chaque chargement RÉUSSI. Brancher
     l'écouteur de clic ici sans garde en empilerait un par modèle — au
     troisième GLB, un seul clic tirerait trois rayons et redessinerait trois
     fois le panneau. Le canevas, lui, est créé UNE fois pour la vie de la
     page : viewer.js met les deux vues en cache et ne démonte jamais le
     canevas (« Libère le MODÈLE, pas le CANEVAS »). Un seul branchement suffit
     donc, et il vaut pour tous les modèles suivants. */
  if (_clicBranche) return;
  _clicBranche = true;
  designerAuClic(S.vueA, $("#vueA canvas"), (obj) => {
    if (!obj) return;
    surligner(S.vueA, obj.uuid);
    /* Le gizmo suit le clic quelle que soit la granularité : déplacer un nœud
       n'est pas le même geste que le retenir, et le panneau n'a pas à être en
       mode « maillage » pour qu'on puisse redresser une pièce.

       SAUF SUR LA PLAQUE, et le silence est ici la bonne réponse. poserGizmo()
       refuse déjà l'étalement EN LE DISANT — ce que ce fichier fait partout —
       mais ce refus-là s'écrit dans la barre du bas, en rouge, et ce chemin-ci
       est justement celui du geste que la plaque existe pour servir : DÉSIGNER
       une pièce qu'on voit enfin. Peindre la barre en rouge à chaque clic
       réussi ferait passer la sélection pour un échec. La garde bruyante reste
       pour qui appellerait poserGizmo() autrement ; ici on se tait, et le
       titre du bouton de bascule dit déjà que la plaque ne manipule pas. */
    if (!estEtalee(S.vueA)) poserGizmo(obj);
    /* Le clic désigne un MAILLAGE, et rien d'autre : son uuid n'est ni celui
       d'un matériau, ni un index de nœud, et `retenus` doit rester homogène.
       Mais hors de la granularité « maillage » on SORT — on ne détruit pas.
       Appuyer sur un bouton de granularité est un changement de mode explicite,
       où perdre sa sélection est attendu ; cliquer dans le canevas est le geste
       d'INSPECTION, et TOLERANCE_CLIC fait qu'une orbite presque immobile
       compte comme un clic. Une sélection de dix matériaux ne doit pas
       disparaître sur un frôlement. Le surlignage, lui, a déjà eu lieu : on
       montre ce qui est sous le curseur sans rien retenir. */
    if (SEL.granularite !== "maillage") return;
    SEL.retenus.add(obj.uuid);
    rendreParties();
  });
});

/* Un premier rendu à VIDE, dès l'import : sans lui le panneau Parties reste
   littéralement blanc jusqu'au premier GLB, entre deux voisins qui, eux,
   disent ce qu'ils attendent (« le panneau Rig arrive en P4 »). Un panneau
   muet se lit comme un panneau cassé. Tout ce qu'il touche garde le cas du
   modèle absent — inventaire() rend trois listes vides, isoler() ne fait
   rien. */
rendreParties();
/* Le libellé et l'infobulle du bouton de bascule viennent d'UN seul endroit,
   majBoutonPlaque(), plutôt que d'être écrits dans index.html PUIS réécrits
   ici : deux sources pour un même texte divergent à la première retouche. */
majBoutonPlaque();
/* Même règle pour le point de vue : #btnProjection naît sans texte et les
   trois vues d'axe naissent sans marque ni infobulle. Les écrire dans
   index.html PUIS ici ferait deux sources pour un même texte. */
majBoutonProjection();
majBoutonsVue();
/* Et le panneau Fiche pour la même raison : #panFiche naît VIDE dans
   index.html, et un onglet qu'on ouvre sur du blanc se lit comme un onglet
   cassé. Le bloc garde le cas du modèle absent — son bouton refuse en le
   disant. */
rendreFiche();

/* ── les onglets du rail droit ──────────────────────────────────────────────
   Les quatre boutons portent `data-onglet` depuis la tâche 2 et PERSONNE ne
   les écoutait : #panFiche naît `hidden` et le restait. Le bloc « Réparer
   l'assise » aurait donc été écrit et rendu INATTEIGNABLE — le pire des
   échecs, silencieux, et sur la moitié de cette tâche. Les panneaux Rig et
   Export restent des coquilles qui annoncent P4 et P5 ; encore faut-il
   pouvoir les lire. */
const PANNEAUX = { parties: "#panParties", rig: "#panRig",
                   fiche: "#panFiche", export: "#panExport" };
const ONGLETS = [...document.querySelectorAll(".onglets .on")];
ONGLETS.forEach((b) => b.addEventListener("click", () => {
  for (const [cle, sel] of Object.entries(PANNEAUX)) {
    $(sel).classList.toggle("hidden", cle !== b.dataset.onglet);
  }
  /* L'onglet actif se marque ICI et non par un `classList.add` seul : sans le
     retrait sur les trois autres, deux onglets se diraient actifs. */
  ONGLETS.forEach((o) => o.classList.toggle("actif", o === b));
}));

async function amorcer() {
  const box = $("#chrono");
  try {
    S.sources = await jget("/api/etabli/sources");
    /* rendreChrono() DANS le try : une réponse à laquelle il manquerait
       `meshy`, ou un job sans `etapes`, lève dans le rendu — et posé hors du
       try, cet échec laisserait « chargement… » figé pour toujours, ce que ce
       filet est précisément là pour empêcher. */
    rendreChrono();
    /* APRÈS le rendu : avant, il n'existe aucun bloc à marquer. Et DANS le
       `try` en connaissance de cause — la fonction ne lit que le DOM que
       rendreChrono() vient d'écrire, si bien que le seul échec qu'elle puisse
       produire est celui que « chronologie illisible » décrit justement. */
    marquerJobVise();
  } catch (e) {
    /* amorcer() tourne à l'IMPORT du module : sans ce filet, la promesse
       rejetée laisse « chargement… » figé pour toujours et le refus ne vit que
       dans la console. textContent et non innerHTML — le message vient du
       serveur, il n'a rien à faire dans le balisage. */
    box.innerHTML = '<div class="chrono-vide"></div>';
    box.firstElementChild.textContent = `chronologie illisible — ${e.message}`;
  }
}
amorcer();

export { S, SEL, SEUIL, jget, jpost, ouvrirPrincipale };
