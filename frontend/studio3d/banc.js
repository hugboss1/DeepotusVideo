/* Le banc de référence — T107 (plan-moteurs-3d T8, R10e D2). La matrice des moteurs cesse de citer des fiches
   produit : ce que chaque moteur a VRAIMENT rendu chez nous (tris, poids, coût, étanchéité), médianes du backend
   (GET /api/assets3d/engines → banc). Un moteur sans ligne affiche « jamais mesuré chez nous », et c'est une
   information : ne pas remplir la case par la note du fournisseur.
   Ranger le job choisi dans l'atelier est gratuit (lecture de sa fiche de maillage) : un POST, sans dialogue. */
"use strict";
import { F, jget, jpost } from "./fal.js";

const $ = (s) => document.querySelector(s);

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export async function charger() {
  const d = await jget("/api/assets3d/engines");
  const sel = $("#bancSujet");
  const garde = sel.value;
  sel.innerHTML = (d.sujets_banc || []).map((s) =>
    `<option value="${esc(s.id)}"${s.id === garde ? " selected" : ""}>${esc(s.label)}</option>`).join("");
  /* une ligne par moteur, qui passe à la ligne : un tableau à six colonnes ne tient pas dans le rail (vu à l'écran
     le 06/10 — colonnes coupées, « jamais mesur… ») */
  $("#falBanc").innerHTML = (d.engines || []).map((e) => {
    const b = e.banc;
    return `<div class="banc-ligne"><b>${esc(e.label || e.id)}</b> ${b
      ? `<span>${__dzT9("studio3d.s3b_banc.sujets", "{n} sujet(s)", { n: b.sujets })} · ${Number(b.tris_median).toLocaleString("fr-FR")} tris · `
        + `${(b.bytes_median / 1048576).toFixed(1)} ${__dzT9("studio3d.s3b.mo", "Mo")} · ${Number(b.usd_median).toFixed(2)} $ · ${__dzT9("studio3d.s3b_banc.etanche", "étanche {a}/{b}", { a: b.ferme_sur, b: b.mesures })}</span>`
      : `<span class="jamais">${__dzT9("studio3d.s3b_banc.jamais", "jamais mesuré chez nous")}</span>`}</div>`;
  }).join("");
}

export async function ranger(toast) {
  if (!F.job) { toast(__dzT9("studio3d.s3b_banc.choisis_job", "choisis d'abord un job dans l'atelier ci-dessus")); return; }
  const sujet = $("#bancSujet").value;
  let r;
  try {
    r = await jpost("/api/assets3d/banc", { job: F.job, sujet });
  } catch (e) { toast(String(e.message || e)); return; }
  toast(__dzT9("studio3d.s3b_banc.range", "rangé au banc : {sujet} / {moteur} · {tris} tris (gratuit)", { sujet: r.sujet, moteur: r.moteur, tris: Number(r.tris).toLocaleString("fr-FR") }));
  await charger();
}

export function brancher({ toast }) {
  $("#btnBanc").addEventListener("click", () => ranger(toast).catch((e) => toast(String(e.message || e))));
}
// t149 (traduction L9) : dzT dans la page, le français sous node (bancs)
function __dzT9(k, fr, v) { return typeof globalThis.dzT === "function" ? globalThis.dzT(k, v) : String(fr).replace(/\{(\w+)\}/g, (m, n) => (v && v[n] != null ? String(v[n]) : m)); }
