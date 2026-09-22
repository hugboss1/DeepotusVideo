#!/usr/bin/env node
/* Sonde Playwright du Montage (22/09/2026) — relevé DOM mesuré, en LECTURE
   SEULE côté utilisateur (elle ne rend rien, ne publie rien, n'enregistre
   aucun projet). Sert au différentiel contre DaVinci Resolve :
   docs/superpowers/specs/2026-09-22-montage-vs-resolve-differentiel.md.

   Usage :
     node scripts/qa/probe-montage-playwright.mjs [base=http://127.0.0.1:8799] [outDir]
   Prérequis : `npm i playwright` (le script cherche le module dans PW_DIR ou
   à côté), Chrome installé (channel "chrome" — le CDN Chromium peut être
   injoignable), deux mp4 dans MEDIA_DIR (alpha.mp4, beta.mp4) envoyés par
   POST /api/videos/upload pour obtenir un projet RÉEL (la démo refuse les
   panneaux réels). Sortie : <outDir>/probe.json + captures PNG. */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const BASE = process.argv[2] || "http://127.0.0.1:8799";
const OUT = process.argv[3] || path.join(process.env.PW_DIR || process.cwd(), "out");
const MEDIA = process.env.MEDIA_DIR || path.join(process.env.PW_DIR || process.cwd(), "..", "media");
fs.mkdirSync(OUT, { recursive: true });
const require = createRequire(path.join(process.env.PW_DIR || process.cwd(), "package.json"));
const { chromium } = require("playwright");

const R = { base: BASE, date: new Date().toISOString(), etapes: [], ecrans: {} };
const note = (k, v) => { R.etapes.push({ k, v }); console.log(k, typeof v === "string" ? v : JSON.stringify(v).slice(0, 200)); };

async function upload(name) {
  const p = path.join(MEDIA, name);
  if (!fs.existsSync(p)) return { name, absent: true };
  const fd = new FormData();
  fd.append("file", new Blob([fs.readFileSync(p)], { type: "video/mp4" }), name);
  const r = await fetch(BASE + "/api/videos/upload", { method: "POST", body: fd });
  const j = await r.json().catch(() => ({}));
  return { name, status: r.status, job_id: j.job_id || j.id || null, keys: Object.keys(j).slice(0, 8) };
}

/* relevé générique d'une racine : boîte, boutons, selects, textes clés */
const RELEVE = (rootSel) => {
  const root = document.querySelector(rootSel);
  if (!root) return null;
  const box = (el) => { const b = el.getBoundingClientRect(); return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };
  const vis = (el) => { const b = el.getBoundingClientRect(); return b.width > 0 && b.height > 0; };
  const txt = (el) => (el.textContent || "").replace(/\s+/g, " ").trim().slice(0, 80);
  const btns = [...root.querySelectorAll("button,[role=button],select,input[type=range],input[type=checkbox]")].filter(vis).map((el) => ({
    tag: el.tagName.toLowerCase(), cls: (el.className && el.className.baseVal === undefined ? el.className : "").toString().split(/\s+/).filter(Boolean).slice(0, 3).join(" "),
    text: el.tagName === "SELECT" ? [...el.options].map((o) => o.textContent.trim()).join("|").slice(0, 120) : txt(el),
    title: (el.getAttribute("title") || el.getAttribute("aria-label") || "").slice(0, 120), dis: !!el.disabled, box: box(el) }));
  return { box: box(root), n_boutons: btns.length, boutons: btns };
};

(async () => {
  note("upload_alpha", await upload("alpha.mp4"));
  note("upload_beta", await upload("beta.mp4"));
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 }, locale: "fr-FR" });
  await ctx.addInitScript(() => { try { localStorage.setItem("dz_onboarded", "1"); localStorage.setItem("dz_hints_off", "1"); } catch (e) {} });
  const page = await ctx.newPage();
  const cons = []; page.on("console", (m) => { if (m.type() === "error") cons.push(m.text().slice(0, 160)); });
  await page.goto(BASE, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500);
  const skip = page.getByText("Skip for now", { exact: true });
  if (await skip.count()) { await skip.first().click(); note("onboarding", "Skip for now cliqué"); await page.waitForTimeout(800); }

  /* la barre de navigation : tous les écrans, libellés exacts */
  R.nav = await page.evaluate(() => [...document.querySelectorAll("nav button, [class*=nav] button, aside button")]
    .map((b) => (b.textContent || "").replace(/\s+/g, " ").trim()).filter((t) => t && t.length < 40).slice(0, 60));
  note("nav", R.nav);

  async function go(label) {
    const cands = page.getByText(label, { exact: true });
    const n = await cands.count();
    for (let i = 0; i < n; i++) { const el = cands.nth(i); if (await el.isVisible()) { await el.click(); await page.waitForTimeout(1500); return true; } }
    return false;
  }

  /* ── MONTAGE ── */
  note("go_montage", await go("Montage"));
  await page.waitForSelector(".dzsvm", { timeout: 15000 }).catch(() => note("dzsvm", "absent"));
  await page.waitForTimeout(2500);
  const M = (R.ecrans.montage = {});
  M.demo = await page.evaluate(() => !!document.querySelector(".dzsvm .svm-demo, .dzsvm [data-demo]") || /démonstration/i.test(document.querySelector(".dzsvm")?.textContent || ""));
  M.zones = await page.evaluate(() => {
    const box = (s) => { const el = document.querySelector(s); if (!el) return null; const b = el.getBoundingClientRect(); return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };
    const o = {}; for (const s of [".dzsvm", ".svm-titlebar", ".svm-mid", ".svm-playerzone", ".svm-frame", ".svm-insp", ".svm-tl", ".svm-trans", "#dzm-toolbar", ".dzm-tbtab", ".svm-scroll", ".svm-ruler", ".svm-narr", ".svm-pop"]) o[s] = box(s);
    o.pistes = [...document.querySelectorAll(".svm-track")].map((t) => { const b = t.getBoundingClientRect(); const h = t.querySelector(".svm-thead"); return { h: Math.round(b.height), head: (h?.textContent || "").replace(/\s+/g, " ").trim().slice(0, 40), clips: t.querySelectorAll(".svm-clip").length }; });
    o.inspecteur_css = (() => { const el = document.querySelector(".svm-insp"); if (!el) return null; const c = getComputedStyle(el); return { width: c.width, flex: c.flex, resize: c.resize, overflow: c.overflowY }; })();
    o.timeline_css = (() => { const el = document.querySelector(".svm-tl"); if (!el) return null; const c = getComputedStyle(el); return { minHeight: c.minHeight, maxHeight: c.maxHeight, height: c.height }; })();
    return o;
  });
  M.titlebar = await page.evaluate(RELEVE, ".svm-titlebar");
  M.transport = await page.evaluate(RELEVE, ".svm-trans");
  M.inspecteur = await page.evaluate(RELEVE, ".svm-insp");
  M.inspecteur_labels = await page.evaluate(() => [...document.querySelectorAll(".svm-insp .svm-propk, .svm-insp label, .svm-insp h3, .svm-insp .svm-label, .svm-insp [class*=label]")].map((e) => e.textContent.trim()).filter(Boolean).slice(0, 60));
  M.toolbar = await page.evaluate(() => [...document.querySelectorAll("#dzm-toolbar .dzm-tbgrp")].map((g) => ({ cls: g.className, boutons: [...g.querySelectorAll("button")].map((b) => ({ t: b.textContent.trim().slice(0, 30), title: (b.title || "").slice(0, 90), dis: b.disabled })) })));
  M.menus_contextuels = await page.evaluate(() => ({ clip: !!document.querySelector(".svm-clip[oncontextmenu]"), n_contextmenu_listeners: "non mesurable sans devtools" }));
  M.mots_cles = await page.evaluate(() => { const t = document.querySelector(".dzsvm")?.textContent || ""; const o = {}; for (const w of ["Nouveau montage", "Nouveau projet", "Nouveau", "Studio", "Chapitres", "Scheduler", "Rendre & publier", "Preview 480p", "bibliothèque", "projets", "Envoyer vers", "Importer", "Médias"]) o[w] = (t.match(new RegExp(w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi")) || []).length; return o; });
  await page.screenshot({ path: path.join(OUT, "montage.png") });

  /* popovers : projets, sélecteur d'assets (lier), rendu */
  async function popover(btnText, key, viaTitle) {
    try {
      const loc = viaTitle ? page.locator(`.dzsvm [title*="${btnText}"]`) : page.locator(".dzsvm button", { hasText: btnText });
      if (!(await loc.count())) { M[key] = { absent: true }; return; }
      await loc.first().click(); await page.waitForTimeout(900);
      M[key] = await page.evaluate(() => { const els = [...document.querySelectorAll(".svm-pop, .dzm-proj, .dzm-tbwin")].filter((e) => e.getBoundingClientRect().width > 0); return els.map((p) => ({ cls: p.className.toString().slice(0, 60), text: p.textContent.replace(/\s+/g, " ").trim().slice(0, 900), boutons: [...p.querySelectorAll("button")].map((b) => b.textContent.trim().slice(0, 40)).filter(Boolean).slice(0, 40), chips: p.querySelectorAll(".svm-chip, [class*=chip]").length, voile: !!document.querySelector(".svm-veil, .dzm-veil, [class*=backdrop]") })); });
      await page.screenshot({ path: path.join(OUT, `montage_${key}.png`) });
      await page.keyboard.press("Escape"); await page.waitForTimeout(400);
    } catch (e) { M[key] = { erreur: String(e).slice(0, 200) }; }
  }
  await popover("projets", "pop_projets");
  await popover("lier", "pop_picker");
  await popover("Rendre & publier", "pop_rendu");
  await popover("bibliothèque", "pop_reinit");

  /* la timeline : clic sur un clip → inspecteur par état */
  try {
    const clip = page.locator(".dzsvm .svm-clip").first();
    if (await clip.count()) { await clip.click({ position: { x: 20, y: 10 } }); await page.waitForTimeout(600); M.inspecteur_clip = await page.evaluate(RELEVE, ".svm-insp"); M.inspecteur_clip_labels = await page.evaluate(() => [...document.querySelectorAll(".svm-insp .svm-propk")].map((e) => e.textContent.trim())); await page.screenshot({ path: path.join(OUT, "montage_clip.png") }); }
  } catch (e) { M.inspecteur_clip = { erreur: String(e).slice(0, 200) }; }

  /* ── LIBRARY : onglets, chips de provenance, « Envoyer vers… » ── */
  note("go_library", await go("Library"));
  await page.waitForTimeout(2000);
  const L = (R.ecrans.library = {});
  L.onglets = await page.evaluate(() => [...document.querySelectorAll("main button, [role=tab]")].map((b) => b.textContent.trim()).filter((t) => t && t.length < 30).slice(0, 40));
  try {
    const rend = page.getByText("Renders", { exact: true }); if (await rend.count()) { await rend.first().click(); await page.waitForTimeout(1200); }
    L.chips = await page.evaluate(() => [...document.querySelectorAll("button")].map((b) => b.textContent.trim()).filter((t) => /^(Tout|Studio|Quick|Episode|Montage|News|Template|Upload|Composition|Seedance|Heygen|Import)/i.test(t)).slice(0, 30));
    const vign = page.locator("main img, main video, main [class*=card], main [class*=tile]").first();
    if (await vign.count()) { await vign.click(); await page.waitForTimeout(1000); const env = page.locator("button", { hasText: "Envoyer vers" }); if (await env.count()) { await env.first().click(); await page.waitForTimeout(700); L.envoyer_vers = await page.evaluate(() => [...document.querySelectorAll("button, [role=menuitem]")].map((b) => b.textContent.replace(/\s+/g, " ").trim()).filter((t) => /Montage|Scheduler|Studio|Quick|Template|Bible|Cardforge|Sprites|print|sheet/i.test(t) && t.length < 60).slice(0, 20)); await page.screenshot({ path: path.join(OUT, "library_envoyer.png") }); } else L.envoyer_vers = { bouton_absent: true }; await page.keyboard.press("Escape"); }
  } catch (e) { L.erreur = String(e).slice(0, 200); }

  /* ── CHAPITRES et STUDIO : y a-t-il un chemin vers le Montage ? ── */
  for (const [lab, key] of [["Chapitres", "chapitres"], ["Studio", "studio"]]) {
    note("go_" + key, await go(lab)); await page.waitForTimeout(2000);
    R.ecrans[key] = await page.evaluate(() => { const t = document.querySelector("main")?.textContent || document.body.textContent; const bt = [...document.querySelectorAll("main button")].map((b) => b.textContent.replace(/\s+/g, " ").trim()).filter((x) => x && x.length < 50); return { n_boutons: bt.length, boutons: bt.slice(0, 80), mentions_montage: (t.match(/montage/gi) || []).length, boutons_montage: bt.filter((x) => /montage/i.test(x)) }; });
    await page.screenshot({ path: path.join(OUT, key + ".png") });
  }

  /* ── API : les quatre exigences côté serveur ── */
  const api = async (m, u, body) => { const r = await fetch(BASE + u, { method: m, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined }); let j = null; try { j = await r.json(); } catch {} return { status: r.status, j }; };
  R.api = {};
  R.api.project = await api("GET", "/api/montage/project").then((x) => ({ status: x.status, clips: x.j?.clips?.length, v1: x.j?.clips?.filter((c) => c.tr === "v1").length, saved: x.j?.saved, tracks: x.j?.tracks?.map((t) => t.id) }));
  R.api.projects = await api("GET", "/api/montage/projects").then((x) => ({ status: x.status, n: Array.isArray(x.j) ? x.j.length : x.j?.projects?.length }));
  R.api.projet_vide = await api("POST", "/api/montage/projects", { name: "sonde-vide", timeline: { clips: [] } }).then((x) => ({ status: x.status, detail: x.j?.detail || null }));
  R.api.jobs = await api("GET", "/api/jobs").then((x) => { const l = Array.isArray(x.j) ? x.j : x.j?.jobs || []; return { status: x.status, n: l.length, providers: [...new Set(l.map((j) => j.provider))] }; });
  R.api.schedule = await api("GET", "/api/schedule").then((x) => ({ status: x.status, n: Array.isArray(x.j) ? x.j.length : x.j?.posts?.length }));
  R.api.routes_montage = await api("GET", "/openapi.json").then((x) => Object.keys(x.j?.paths || {}).filter((p) => /montage|episodes|schedule|videos\/upload/.test(p)));
  R.console_errors = cons.slice(0, 20);
  fs.writeFileSync(path.join(OUT, "probe.json"), JSON.stringify(R, null, 2));
  await browser.close();
  console.log("OK", path.join(OUT, "probe.json"));
})().catch((e) => { console.error("ECHEC", e); fs.writeFileSync(path.join(OUT, "probe.json"), JSON.stringify(R, null, 2)); process.exit(1); });
