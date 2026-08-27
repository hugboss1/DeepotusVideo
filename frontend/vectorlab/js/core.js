// core.js — coquille phase 0 du Vectorlab : charge ?doc=<id> via l'API,
// compile le document (mod-doc) et l'affiche ; zoom molette + pan glisser.
// L'édition (outils, calques, undo) arrive en phase 1 — ce cœur reste le
// point unique d'état et d'io, au patron du core cardforge.
import { compilerSVG } from "./mod-doc.js";

const $ = (s) => document.querySelector(s);
const api = {
  async get(p) {
    const r = await fetch("/api" + p);
    if (!r.ok) throw new Error((await r.text()).slice(0, 300));
    return r.json();
  },
};

const etat = { docId: null, meta: null, doc: null, zoom: 1, tx: 0, ty: 0 };

function appliquerVue() {
  const svg = $("#canvasHost svg");
  if (svg) {
    svg.style.transform =
      `translate(${etat.tx}px, ${etat.ty}px) scale(${etat.zoom})`;
  }
  $("#zoomLabel").textContent = Math.round(etat.zoom * 100) + " %";
}

function rendre() {
  $("#canvasHost").innerHTML = etat.doc ? compilerSVG(etat.doc) : "";
  appliquerVue();
}

async function charger() {
  const id = new URLSearchParams(location.search).get("doc");
  if (!id) {
    $("#docTitle").textContent = "Vectorlab";
    $("#docMeta").textContent = "aucun document — ouvre ?doc=<id>";
    return;
  }
  $("#docMeta").classList.remove("erreur");
  try {
    const d = await api.get("/vector/docs/" + encodeURIComponent(id));
    etat.docId = id;
    etat.meta = d.meta;
    etat.doc = d.doc;
    $("#docTitle").textContent = d.meta.name;
    $("#docMeta").textContent = `${d.meta.role} · v${d.meta.version}`
      + (d.meta.chapter_id ? ` · chapitre ${d.meta.chapter_id}` : "");
    rendre();
  } catch (e) {
    $("#docMeta").classList.add("erreur");
    $("#docMeta").textContent = "erreur : " + e.message;
  }
}

/* ── zoom molette + pan au glisser ── */
const stage = $("#stage");
stage.addEventListener("wheel", (ev) => {
  ev.preventDefault();
  const facteur = Math.pow(1.0015, -ev.deltaY);
  etat.zoom = Math.max(0.1, Math.min(8, etat.zoom * facteur));
  appliquerVue();
}, { passive: false });

let saisie = null;
stage.addEventListener("pointerdown", (ev) => {
  saisie = { x: ev.clientX, y: ev.clientY, tx: etat.tx, ty: etat.ty };
  stage.classList.add("saisi");
  stage.setPointerCapture(ev.pointerId);
});
stage.addEventListener("pointermove", (ev) => {
  if (!saisie) return;
  etat.tx = saisie.tx + (ev.clientX - saisie.x);
  etat.ty = saisie.ty + (ev.clientY - saisie.y);
  appliquerVue();
});
stage.addEventListener("pointerup", () => {
  saisie = null;
  stage.classList.remove("saisi");
});

$("#btnRecharger").addEventListener("click", charger);
charger();
