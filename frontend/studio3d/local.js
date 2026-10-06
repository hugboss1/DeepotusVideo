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
  const carte = `${esc(c.nom || "carte inconnue")}${c.vram_mo ? ` · ${c.vram_mo} Mo (${esc(c.source)})` : ""}`;
  $("#falLocal").innerHTML = l.ready
    ? `<b>Service GPU local prêt</b> — ${dec.texture ? "forme et texture" : "forme seule"}. ${carte}. ${esc(dec.pourquoi)}`
    : `<b>Service GPU local absent</b> (${esc(d.url)}) — le moteur « Hunyuan3D 2.1 (local) » reste grisé. `
      + `Carte : ${carte}. ${esc(dec.pourquoi)} Pour l'activer : lancer Hunyuan3D 2.1 à côté, adresse dans LOCAL3D_URL (.env).`
      + (c.avertissement ? ` <i>${esc(c.avertissement)}</i>` : "");
}
