/* Le service GPU local — T107 (plan-moteurs-3d T10, R10e D4). Il n'est pas une promesse : s'il ne tourne pas, on le
   DIT avec l'adresse, la carte mesurée et ce que sa VRAM permet, au lieu de griser le moteur sans raison
   (GET /api/assets3d/local). Rien n'est installé par l'application : le serveur Hunyuan3D se lance à côté. */
"use strict";
import { jget } from "./fal.js";

const $ = (s) => document.querySelector(s);

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export async function charger() {
  const d = await jget("/api/assets3d/local");
  const l = (d.providers || []).find((p) => p.id === "local3d") || {};
  const c = l.carte || {};
  const dec = l.decision || {};
  const carte = `${esc(c.nom || __dzT9("studio3d.s3b_local.carte_inconnue", "carte inconnue"))}${c.vram_mo ? ` · ${c.vram_mo} ${__dzT9("studio3d.s3b.mo", "Mo")} (${esc(c.source)})` : ""}`;
  $("#falLocal").innerHTML = l.ready
    ? `<b>${__dzT9("studio3d.s3b_local.pret", "Service GPU local prêt")}</b> — ${dec.texture ? __dzT9("studio3d.s3b_local.forme_texture", "forme et texture") : __dzT9("studio3d.s3b_local.forme_seule", "forme seule")}. ${carte}. ${esc(dec.pourquoi)}`
    : `${__dzT9("studio3d.s3b_local.absent", "<b>Service GPU local absent</b> ({url}) — le moteur « Hunyuan3D 2.1 (local) » reste grisé.", { url: esc(d.url) })} `
      + `${__dzT9("studio3d.s3b_local.carte", "Carte : {carte}.", { carte: carte })} ${esc(dec.pourquoi)} ${__dzT9("studio3d.s3b_local.activer", "Pour l'activer : lancer Hunyuan3D 2.1 à côté, adresse dans LOCAL3D_URL (.env).")}`
      + (c.avertissement ? ` <i>${esc(c.avertissement)}</i>` : "");
}
// t149 (traduction L9) : dzT dans la page, le français sous node (bancs)
function __dzT9(k, fr, v) { return typeof globalThis.dzT === "function" ? globalThis.dzT(k, v) : String(fr).replace(/\{(\w+)\}/g, (m, n) => (v && v[n] != null ? String(v[n]) : m)); }
