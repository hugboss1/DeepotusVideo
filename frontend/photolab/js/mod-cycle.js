import { tranches } from "./mod-historique.js";

// mod-cycle.js — le cycle inspect -> rendu (décision D1) : après CHAQUE commande, l'écran relit le document
// (GET /inspecter), met à jour les panneaux, redemande un rendu complet (POST /rendu) et le pose sur le canevas ; les
// vignettes des calques suivent, débouncées, quand la révision a changé. L'écran n'invente aucun pixel.
// Un seul cycle en vol à la fois : les demandes arrivées pendant qu'il vole sont fusionnées en UN cycle de plus (dix
// clics rapides = deux cycles, jamais dix requêtes empilées dans le moteur). Fonctions PURES exportées (qa/cycle.test.mjs).

// File à un seul vol. `tache()` rend une promesse. demander() : si rien ne vole, lance ; sinon toutes les demandes
// suivantes partagent UNE promesse, celle du cycle lancé à la fin du cycle en cours (il relira l'état le plus récent).
export function fileUnique(tache) {
  let enVol = null;          // promesse du cycle en cours
  let suivant = null;        // promesse du cycle fusionné (lancé à la fin de enVol)
  function lancer() {
    const p = (async () => tache())();
    enVol = p;
    const fin = () => { if (enVol === p) enVol = null; };
    p.then(fin, fin);
    return p;
  }
  return function demander() {
    // `suivant` d'abord : entre la fin du cycle en vol et le lancement du fusionné, enVol est déjà nul ; sans ce test une
    // demande arrivée dans cet intervalle lancerait un second cycle en parallèle.
    if (suivant) return suivant;
    if (!enVol) return lancer();
    suivant = enVol.then(() => {}, () => {}).then(() => { suivant = null; return lancer(); });
    return suivant;
  };
}

// Numérotation des rendus : un rendu demandé plus tôt mais arrivé plus tard (zoom puis commande, par exemple) ne doit
// jamais recouvrir un rendu plus récent déjà posé.
export function rendusOrdonnes() {
  let compteur = 0, pose = 0;
  return {
    numero: () => ++compteur,
    poser(n) { if (n <= pose) return false; pose = n; return true; },
  };
}

// Les vignettes ne se rechargent que si le document a réellement changé (révision, ou autre document).
export function revisionNeuve(avant, doc) {
  if (!doc) return false;
  if (!avant) return true;
  return avant.revision !== doc.revision || avant.name !== doc.name || avant.width !== doc.width || avant.height !== doc.height;
}

// La vue se recadre sur un document neuf, ou dont la taille a changé (recadrage, taille de l'image).
export function documentNeuf(avant, doc) {
  return !avant || avant.width !== doc.width || avant.height !== doc.height;
}

// maxSide envoyé à /rendu. tailleRendu (mod-vue) rend 0 pour « taille réelle » ; or la route refuse moins de 64 et le
// moteur refuse tout côté au-delà de 2048, y compris 0 sur un document plus grand (relevé le 08/10 : « automation
// preview side exceeds 2048 pixels »). 0 devient donc le grand côté du document, et tout est borné à [64, 2048].
export const RENDU_MAX = 2048;
export function maxSideRequete(maxSide, doc) {
  const grand = doc ? Math.max(doc.width || 0, doc.height || 0) : RENDU_MAX;
  const m = maxSide > 0 ? maxSide : grand;
  return Math.max(64, Math.min(RENDU_MAX, m || RENDU_MAX));
}

// Nombre de calques (feuilles et groupes) d'un arbre doc.inspect.
export function compterCalques(layers) {
  let n = 0;
  for (const c of layers || []) { n++; if (Array.isArray(c.children)) n += compterCalques(c.children); }
  return n;
}

// File FIFO : les commandes moteur partent dans l'ordre des gestes, une à la fois (deux gestes rapides ne se croisent
// jamais dans le pont). ajouter(tache) -> promesse du résultat de CETTE tâche ; un échec ne bloque pas les suivantes.
export function fileFifo() {
  let queue = Promise.resolve();
  return function ajouter(tache) {
    const p = queue.then(() => tache());
    queue = p.then(() => {}, () => {});
    return p;
  };
}

// Accumulateur : le premier ajout part tout de suite ; tant qu'il vole, les ajouts suivants se cumulent (cumuler(a, b))
// et partent en UN envoi à son retour. Flèches de déplacement (vecteurs) et Ctrl+Z / Ctrl+Maj+Z (compte signé).
export function creerAccumulateur(envoyer, cumuler) {
  let enVol = false, attente = null;
  function partir(x) {
    enVol = true;
    let p;
    try { p = envoyer(x); } catch (e) { p = Promise.reject(e); }
    Promise.resolve(p).then(fin, fin);
  }
  function fin() {
    enVol = false;
    if (attente != null) { const x = attente; attente = null; partir(x); }
  }
  return function ajouter(x) {
    if (enVol) { attente = attente == null ? x : cumuler(attente, x); return; }
    partir(x);
  };
}

// Ce qui appartient au document affiché et doit disparaître avec lui (fermer, moteur relancé, autre document) : le
// document, ses vignettes et les verrous que l'écran tient (le moteur ne les relit pas — un id de calque d'un autre
// document hériterait sinon d'un cadenas).
export function viderEtatDocument(etat) {
  etat.doc = null;
  etat.vignettes = {};
  etat.verrous = {};
  return etat;
}

// Recadrer la vue sur un document ouvert : seulement dans un cycle LANCÉ après l'ouverture (jeton de départ plus
// récent que le dernier appliqué). Un cycle plus ancien encore en vol ne « consomme » pas la demande.
export function doitRecadrer(jetonDepart, jetonApplique) { return jetonDepart > jetonApplique; }

// Données de l'utilisateur (nom de calque, de fichier, de document) : la surcouche de traduction FR -> EN (dz-i18n)
// ne doit jamais les réécrire — un calque nommé « Calque » deviendrait « Layer ». Marque data-dz-brut.
export function brut(el) { el.setAttribute("data-dz-brut", "1"); return el; }

/* ───────────── côté DOM ───────────── */

const TAILLE_VIGNETTES = 64;       // 32 px affichés, ×2 pour les écrans denses ; fixe pour profiter du cache du service
const DEBOUNCE_VIGNETTES = 400;
const DEBOUNCE_MENUS = 600;

export function initCycle(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  PL.surDoc = [];            // crochets (doc | null) appelés après chaque inspection (panneaux, onglet, statut)
  PL.surVignettes = [];      // crochets (carte id -> url) appelés quand les vignettes arrivent
  PL.etat.vignettes = {};
  PL.etat.verrous = PL.etat.verrous || {};
  let docVignettes = null;   // {revision, name, width, height} des dernières vignettes demandées
  let jetonDemande = 0;      // +1 à chaque ouverture de document (recadrer la vue)…
  let jetonApplique = 0;     // … et le dernier jeton honoré par un cycle lancé après lui
  let minutVig = null, minutMenus = null;
  let imageEnEchec = false;  // un échec de chargement de l'aperçu n'est signalé qu'une fois (jusqu'au prochain succès)
  const ordre = rendusOrdonnes();

  const sur = (liste, ...args) => liste.forEach((f) => { try { f(...args); } catch (e) { console.error(e); } });

  // Le chargement passe par onload, pas Image.decode() : decode() reste suspendu dans un onglet masqué (l'iframe du
  // lab l'est souvent), relevé sur le Spritelab.
  function chargerImage(url) {
    return new Promise((ok, ko) => {
      const im = new Image();
      im.onload = () => ok(im);
      im.onerror = () => ko(new Error(url));
      im.src = url;
    });
  }

  async function rendre(maxSide) {
    const doc = PL.etat.doc;
    if (!doc) return;
    const n = ordre.numero();
    const r = await PL.post("/rendu", { maxSide: maxSideRequete(maxSide, doc) });     // une erreur HTTP est signalée par mod-api
    let image;
    try { image = await chargerImage(r.url); } catch (e) {
      if (!imageEnEchec) { imageEnEchec = true; PL.signaler(T("photolab.rendu.echec"), true); }
      throw e;
    }
    imageEnEchec = false;
    if (!PL.etat.doc || !ordre.poser(n)) return;          // document fermé entre-temps, ou rendu dépassé
    PL.vue.poserRendu({ image, maxSide });                 // maxSide tel que voulu par la vue (0 compris) : ses comparaisons restent justes
    sur(PL.surRendu, PL.vue.rendu);
  }

  function statut(doc) {
    const ecrire = (id, t) => { const el = PL.$(id); if (el) el.textContent = t; };
    if (!doc) { ecrire("#stTaille", ""); ecrire("#stCalques", ""); return; }
    ecrire("#stTaille", doc.width + " × " + doc.height + " px");
    ecrire("#stMode", T("photolab.statut.mode", { mode: String(doc.mode || "rgb").toUpperCase(), bits: doc.depth || 8 }));
    ecrire("#stCalques", T("photolab.statut.calques", { n: compterCalques(doc.layers) }));
  }

  async function unCycle() {
    const depart = jetonDemande;                           // lu AU LANCEMENT : un cycle plus ancien ne recadre pas
    let doc;
    try {
      doc = await PL.get("/inspecter", true);
    } catch (e) {
      // 422 = le moteur n'a plus de document actif : retour à l'accueil. Les autres erreurs (occupé, délai) laissent
      // l'écran tel quel et le disent.
      if (e && e.statut === 422) fermerVue(); else if (e && e.message) PL.signaler(e.message, true);
      return null;
    }
    const avant = PL.etat.doc;
    PL.etat.doc = doc;
    const recadrer = doitRecadrer(depart, jetonApplique);
    if (recadrer) jetonApplique = depart;
    if (recadrer || documentNeuf(avant, doc)) {
      PL.afficherAccueil(false);                          // AVANT d'ajuster : un canevas masqué mesure 0 × 0
      PL.vue.surNouveauDoc();
    }
    sur(PL.surDoc, doc);
    statut(doc);
    // Un rendu raté (réseau, image illisible) ne doit priver ni les vignettes ni les menus de leur mise à jour.
    try { await rendre(PL.vue.maxSideVoulu()); } catch (e) { /* déjà signalé (mod-api, ou l'image ci-dessus) */ }
    if (revisionNeuve(docVignettes, doc)) {
      docVignettes = { revision: doc.revision, name: doc.name, width: doc.width, height: doc.height };
      clearTimeout(minutVig);
      minutVig = setTimeout(chargerVignettes, DEBOUNCE_VIGNETTES);
    }
    // L'état « actif » des entrées de menu dépend du document (sélection, historique…) : registre relu, débouncé.
    clearTimeout(minutMenus);
    minutMenus = setTimeout(() => PL.menus && PL.menus.rafraichir(), DEBOUNCE_MENUS);
    return doc;
  }

  async function chargerVignettes() {
    if (!PL.etat.doc) return;
    try {
      const r = await PL.get("/vignettes?maxSide=" + TAILLE_VIGNETTES, true);
      if (!PL.etat.doc) return;
      PL.etat.vignettes = (r && r.vignettes) || {};
      sur(PL.surVignettes, PL.etat.vignettes);
    } catch (e) { /* vignettes facultatives : la liste des calques reste utilisable sans elles */ }
  }

  const fileCycle = fileUnique(unCycle);
  // Toujours résolu (jamais rejeté) : les appelants n'ont rien à rattraper, les erreurs ont déjà été signalées.
  PL.cycle = () => fileCycle().catch(() => null);

  // Rendu seul (zoom de la vue) : sa propre file, la dernière taille voulue gagne.
  let voulu = 0;
  const fileRendu = fileUnique(() => rendre(voulu));
  PL.rendre = (maxSide) => { voulu = maxSide; return fileRendu().catch(() => null); };

  // Toutes les commandes moteur passent par UNE file FIFO : l'ordre des gestes est l'ordre d'exécution.
  PL.file = fileFifo();

  // Une commande moteur puis un cycle. -> {ok, r} (r = résultat de la commande ; un échec a déjà été signalé).
  PL.executer = function executer(command, params = {}, { cycle = true } = {}) {
    if (!PL.etat.doc) return Promise.resolve({ ok: false });
    return PL.file(async () => {
      let r;
      try { r = await PL.post("/executer", { command, params }); } catch (e) { return { ok: false, erreur: e }; }
      if (cycle) PL.cycle();
      return { ok: true, r };
    });
  };

  // Annuler (n < 0) / rétablir (n > 0), cumulés pendant qu'une requête vole (Ctrl+Z tenu : la répétition de touche
  // n'empile pas cent requêtes). /historique n'échoue pas quand il n'y a plus rien à annuler (il compte « failed ») :
  // pas de toast pour un Ctrl+Z de trop, et pas besoin d'un canUndo peut-être périmé. Au-delà de 100 (borne de la
  // route), par tranches de 100.
  PL.historique = creerAccumulateur(async (n) => {
    if (!n || !PL.etat.doc) return;
    const cle = n < 0 ? "annuler" : "retablir";
    for (const k of tranches(Math.abs(n))) {
      try { await PL.file(() => PL.post("/historique", { [cle]: k })); } catch (e) { break; }      // signalé par mod-api
    }
    await PL.cycle();
  }, (a, b) => a + b);

  // Un document vient d'être créé ou ouvert (routes /nouveau, /ouvrir) : le cycle suivant recadre la vue.
  PL.documentOuvert = async function documentOuvert() {
    jetonDemande++;
    docVignettes = null;
    PL.etat.vignettes = {};
    PL.etat.verrous = {};
    const doc = await PL.cycle();
    if (PL.menus) PL.menus.rafraichir();
    if (PL.relireCouleurs) PL.relireCouleurs();          // pastilles et panneau Couleur : la session du moteur fait foi
    return doc;
  };

  // Retour à l'accueil (fermer, moteur relancé, plus de document) : la session du moteur garde ses documents.
  function fermerVue() {
    viderEtatDocument(PL.etat);
    docVignettes = null;
    clearTimeout(minutVig);
    if (PL.vue) PL.vue.rendu = null;
    PL.afficherAccueil(true);
    sur(PL.surDoc, null);
    statut(null);
    if (PL.menus) PL.menus.rafraichir();
  }
  PL.fermerVue = fermerVue;
  PL.surMoteurRelance = fermerVue;                      // mod-api l'appelle quand la génération du moteur change
}

