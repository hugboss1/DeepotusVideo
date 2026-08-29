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
  a: null, b: null,          // { job, version, url, libelle, fiche }
  vueA: null, vueB: null,    // canevas
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

/* ── la chronologie : une ligne par job, une puce par étape ────────────────── */
function rendreChrono() {
  const box = $("#chrono");
  const blocs = [];
  for (const j of S.sources.jobs) {
    const etapes = j.etapes.map((e) => {
      const lourd = (e.triangles && e.triangles > SEUIL.triangles)
        || (e.bytes && e.bytes > SEUIL.octets);
      return `<button class="etape${lourd ? " lourde" : ""}"
        data-job="${esc(j.id)}" data-version="${esc(e.version ?? "")}"
        data-url="${esc(e.url)}" data-libelle="${esc(e.libelle)}"
        title="${e.triangles ? e.triangles + " triangles · " : ""}${fmtOctets(e.bytes)}">
        <b>${esc(e.libelle)}</b>
        <span>${e.triangles ? e.triangles.toLocaleString("fr-FR") + " tri" : fmtOctets(e.bytes)}</span>
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
      /* alt-clic : la seconde vue, pour comparer deux étapes (spec §5.1).
         ouvrirComparaison() arrive en TÂCHE 5 avec la vue B et la ligne
         d'écart ; d'ici là un alt-clic lève une ReferenceError, et c'est
         délibéré — un bouchon muet ferait croire la comparaison livrée. */
      if (ev.altKey) ouvrirComparaison(cible);   // eslint-disable-line no-undef
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
  return _file;
}

async function _ouvrirPrincipale(cible, numero) {
  if (numero !== _demande) return;   // dépassée pendant l'attente : on se retire
  if (!S.vueA) S.vueA = creerCanevas($("#vueA canvas"));
  const geoBox = $("#barreGeo");
  $("#barreFichier").textContent = cible.url.split("/").pop();
  geoBox.classList.remove("erreur");
  geoBox.textContent = "chargement…";
  let geo;
  try {
    geo = await charger(S.vueA, cible.url);
  } catch (e) {
    /* Un GLB absent (404), tronqué, ou compressé sans son décodeur laisse le
       canevas VIDE — charger() ayant vidé la vue précédente AVANT d'échouer.
       Sans ce bloc l'échec ne se verrait nulle part : la barre du bas est
       l'endroit où le dépôt met ses refus parlants. */
    S.a = null;                      // rien n'est chargé : ne pas mentir à la suite
    $("#chipSource").textContent = "—";
    geoBox.textContent = `échec du chargement — ${e.message}`;
    geoBox.classList.add("erreur");
    return;
  }
  S.a = cible;                       // posé APRÈS le succès, pour la même raison
  $("#chipSource").textContent = `${cible.job || "meshy"} · ${cible.libelle}`;
  geoBox.textContent =
    `${geo.tris.toLocaleString("fr-FR")} triangles · ${geo.maillages} maillages`;
  if (geo.tris > SEUIL.triangles) {
    geoBox.textContent +=
      ` · au-delà du seuil de ${SEUIL.triangles.toLocaleString("fr-FR")}, une version décimée existe peut-être`;
  }
  document.dispatchEvent(new CustomEvent("etabli:charge", { detail: { geo } }));
}

async function amorcer() {
  const box = $("#chrono");
  try {
    S.sources = await jget("/api/etabli/sources");
  } catch (e) {
    /* amorcer() tourne à l'IMPORT du module : sans ce filet, la promesse
       rejetée laisse « chargement… » figé pour toujours et le refus ne vit que
       dans la console. textContent et non innerHTML — le message vient du
       serveur, il n'a rien à faire dans le balisage. */
    box.innerHTML = '<div class="chrono-vide"></div>';
    box.firstElementChild.textContent = `sources illisibles — ${e.message}`;
    return;
  }
  rendreChrono();
}
amorcer();

export { S, SEUIL, jget, jpost, ouvrirPrincipale };
