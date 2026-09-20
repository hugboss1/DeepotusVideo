// mod-brouillon.js — la sauvegarde AUTOMATIQUE (lot A) : toutes les 30 s,
// si le document est sale, un brouillon part dans localStorage (clé par
// document) ; à l'ouverture, un brouillon PERTINENT (même document, même
// version serveur, contenu différent) est proposé ; un Sauver réussi
// l'efface. Le raster n'est jamais dedans (les href sont des noms). Les
// timers d'un onglet caché sont throttlés : la période est un minimum.
import { parserDoc } from "./mod-doc.js";

/* ── pur ── */
export const BROUILLON_PERIODE_MS = 30000;
export function brouillon_cle(docId) { return "dz_vl_brouillon_" + docId; }
export function brouillon_faire(docId, version, doc, t = Date.now()) {
  return { docId, version, t, doc: JSON.parse(JSON.stringify(doc)) };
}
export function brouillon_pertinent(b, meta, docServeur) {
  if (!b || !b.doc || !meta) return false;
  if (b.docId !== meta.id || b.version !== meta.version) return false;
  return JSON.stringify(b.doc) !== JSON.stringify(docServeur);
}
export function brouillon_libelle(b) {
  const d = new Date(b.t);
  const p = (n) => String(n).padStart(2, "0");
  return `brouillon du ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

/* ── DOM ── */
export function initBrouillon(VL) {
  const { $, etat } = VL;
  const lire = (k) => { try { return JSON.parse(localStorage.getItem(k) || "null"); } catch { return null; } };
  const effacer = (k) => { try { localStorage.removeItem(k); } catch (e) { /* stockage indisponible */ } };

  function ecrire() {
    if (!etat.docId || !etat.doc || !etat.sale) return;
    const b = brouillon_faire(etat.docId, etat.meta.version, etat.doc);
    try { localStorage.setItem(brouillon_cle(etat.docId), JSON.stringify(b)); }
    catch (e) { return; }
    $("#temoin").title = "État d'enregistrement · " + brouillon_libelle(b) + " (non sauvé au serveur)";
  }
  setInterval(ecrire, BROUILLON_PERIODE_MS);

  const suivantCharge = VL.surCharge;
  VL.surCharge = async () => {
    suivantCharge();
    const k = brouillon_cle(etat.docId);
    const b = lire(k);
    if (!brouillon_pertinent(b, { id: etat.docId, version: etat.meta.version }, etat.doc)) {
      if (b) effacer(k);                 // périmé : on ne le reproposera pas
      return;
    }
    if (await VL.dialogue.confirmer(`Un ${brouillon_libelle(b)} de ce document n'a pas été sauvé.\n`
                + `Repartir du serveur = version ${etat.meta.version} ; le brouillon est alors oublié.`,
                { titre: "Brouillon non sauvé", ok: "Restaurer", annuler: "Repartir du serveur" })) {
      try { etat.doc = parserDoc(b.doc); }
      catch (e) { VL.toast("brouillon illisible : " + e.message, true); effacer(k); return; }
      etat.sale = true;
      etat.calqueActif = etat.doc.calques[etat.doc.calques.length - 1].id;
      VL.rendre();
      VL.toast("brouillon restauré — Sauver pour l'écrire au serveur");
    } else effacer(k);
  };
  const suivantSauve = VL.surSauve;
  VL.surSauve = () => {
    suivantSauve();
    effacer(brouillon_cle(etat.docId));
    $("#temoin").title = "État d'enregistrement";
  };
  VL.brouillonEcrire = ecrire;           // la preuve force un tic sans attendre 30 s
}
