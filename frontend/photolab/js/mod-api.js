// mod-api.js — les appels à /api/photolab/*, le suivi de génération du moteur et la traduction des erreurs.
// Fonctions PURES exportées : messageErreur (statut + corps -> texte), memeGeneration.

const BASE = "/api/photolab";
const ENTETE_GENERATION = "X-Photolab-Generation";
const ATTENTE_409_MS = 300;

const T = (cle, vars) => (typeof window !== "undefined" && window.dzT ? window.dzT(cle, vars) : cle);

// Extrait le texte utile d'un corps d'erreur FastAPI ({detail: "…"} ou {detail: [{msg}]}).
export function detailDe(corps) {
  if (corps == null) return "";
  if (typeof corps === "string") return corps.slice(0, 300);
  const d = corps.detail ?? corps.message ?? corps.error;
  if (typeof d === "string") return d.slice(0, 300);
  if (Array.isArray(d)) return d.map((e) => e && (e.msg || e.message) || "").filter(Boolean).join(" ; ").slice(0, 300);
  return "";
}

// Statut HTTP + corps -> message affichable. `t` = traducteur (dzT) injecté pour rester bancable sous node.
export function messageErreur(statut, corps, t = (c) => c) {
  const d = detailDe(corps);
  if (statut === 409) return t("photolab.moteur.occupe");
  if (statut === 503) return d ? t("photolab.moteur.absent") + " " + d : t("photolab.moteur.absent");
  if (statut === 504) return d ? t("photolab.moteur.delai") + " " + d : t("photolab.moteur.delai");
  if (statut === 422) return d ? t("photolab.moteur.refuse") + " " + d : t("photolab.moteur.refuse");
  return d || t("photolab.moteur.erreur") + " (" + statut + ")";
}

// Le moteur a-t-il été relancé ? (la génération change => les documents ouverts sont perdus)
export function memeGeneration(avant, apres) {
  return avant == null || apres == null || String(avant) === String(apres);
}

export class ErreurApi extends Error {
  constructor(statut, message, corps) { super(message); this.statut = statut; this.corps = corps; }
}

export function initApi(PL) {
  PL.etat.generation = null;

  function noterGeneration(rep) {
    const g = rep.headers.get(ENTETE_GENERATION);
    if (g == null) return;
    const avant = PL.etat.generation;
    PL.etat.generation = g;
    if (!memeGeneration(avant, g) && PL.etat.doc) {
      // Le moteur a été relancé : les documents de la session sont perdus, on revient à l'accueil.
      PL.etat.doc = null;
      PL.signaler(T("photolab.moteur.relance"), true);
      if (PL.surMoteurRelance) PL.surMoteurRelance();
    }
  }

  // api("POST", "/executer", {command, params}) -> JSON. Une seule nouvelle tentative sur 409 (moteur occupé).
  // `silencieux` : aucun toast d'erreur (rafraîchissements d'arrière-plan, comme le registre des menus) ; l'erreur est quand
  // même levée à l'appelant.
  PL.api = async function api(methode, chemin, corps, essai = 0, silencieux = false) {
    const opts = { method: methode, headers: {} };
    if (corps !== undefined && corps !== null) {
      if (corps instanceof FormData) opts.body = corps;
      else { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(corps); }
    }
    let rep;
    try {
      rep = await fetch(BASE + chemin, opts);
    } catch (e) {
      const m = T("photolab.moteur.injoignable");
      if (!silencieux) PL.signaler(m, true);
      throw new ErreurApi(0, m, null);
    }
    noterGeneration(rep);
    if (rep.ok) {
      const type = rep.headers.get("content-type") || "";
      return type.includes("json") ? rep.json() : rep;
    }
    if (rep.status === 409 && essai === 0) {
      await new Promise((r) => setTimeout(r, ATTENTE_409_MS));
      return PL.api(methode, chemin, corps, 1, silencieux);
    }
    let contenu = null;
    try { contenu = await rep.json(); } catch (e) { /* corps non JSON : message générique */ }
    const m = messageErreur(rep.status, contenu, T);
    if (!silencieux) PL.signaler(m, true);
    throw new ErreurApi(rep.status, m, contenu);
  };

  PL.get = (chemin, silencieux = false) => PL.api("GET", chemin, undefined, 0, silencieux);
  PL.post = (chemin, corps) => PL.api("POST", chemin, corps === undefined ? {} : corps);
}
