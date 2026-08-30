/* L'Établi — inspecteur 3D en bout de chaîne du 3D Studio.
   Vanilla, HORS du bundle minifié (même patron que /studio3d).

   RÈGLE STRUCTURANTE (spec §2.1) : cette page ne fabrique JAMAIS un GLB. Elle
   envoie des paramètres — une liste de nœuds, une matrice — aux routes
   /api/etabli/*, et c'est Python qui écrit, versionne et fiche. */
"use strict";
import { creerCanevas, charger, cadrer, vider } from "/lib3d/viewer.js";

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
    blocs.push(`<section class="job">
      <div class="job-tete">${esc(j.nom)}<span>${esc(j.moteur || j.source)}</span></div>
      <div class="job-etapes">${etapes}</div></section>`);
  }
  for (const t of S.sources.meshy) {
    const etapes = t.etapes.map((e) => `<button class="etape"
      data-meshy="${esc(t.id)}" data-url="${esc(e.url)}" data-libelle="${esc(e.libelle)}">
      <b>${esc(e.libelle)}</b><span>${esc(t.phase || t.kind || "meshy")}</span></button>`).join("");
    blocs.push(`<section class="job">
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
  const geoBox = $("#barreGeo");
  $("#barreFichier").textContent = cible.url.split("/").pop();
  geoBox.classList.remove("erreur");
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
  geoBox.textContent =
    `${geo.tris.toLocaleString("fr-FR")} triangles · ${geo.maillages} maillages`;
  if (geo.tris > SEUIL.triangles) {
    geoBox.textContent +=
      ` · au-delà du seuil de ${SEUIL.triangles.toLocaleString("fr-FR")}, une version décimée existe peut-être`;
  }
  document.dispatchEvent(new CustomEvent("etabli:charge", { detail: { geo } }));
}

/* ── la comparaison A/B ─────────────────────────────────────────────────────
   Deux vues, une seule caméra logique. Comparer deux étapes sous deux angles
   différents ne compare rien : la synchronisation n'est pas un confort.
   Elle copie la caméra en ABSOLU (position, cible, fov, near/far) — donc si B
   est plus gros que A, il déborde du cadre de A, et c'est le but : la
   différence de taille se VOIT, au lieu d'être annulée par deux cadrages
   indépendants. */
function synchroniser(src, dst) {
  /* Les deux sens sont branchés tête-bêche : sans ce drapeau, l'update() de
     dst lèverait son propre « change », qui recopierait dst vers src, etc. */
  let enCours = false;
  src.controls.addEventListener("change", () => {
    if (enCours) return;
    enCours = true;
    dst.camera.position.copy(src.camera.position);
    /* Redondante avec l'update() ci-dessous, qui refait un lookAt(target) :
       gardée pour que dst soit juste même avant lui, pas parce qu'il la faut. */
    dst.camera.quaternion.copy(src.camera.quaternion);
    dst.camera.fov = src.camera.fov;
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

async function amorcer() {
  const box = $("#chrono");
  try {
    S.sources = await jget("/api/etabli/sources");
    /* rendreChrono() DANS le try : une réponse à laquelle il manquerait
       `meshy`, ou un job sans `etapes`, lève dans le rendu — et posé hors du
       try, cet échec laisserait « chargement… » figé pour toujours, ce que ce
       filet est précisément là pour empêcher. */
    rendreChrono();
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

export { S, SEUIL, jget, jpost, ouvrirPrincipale };
