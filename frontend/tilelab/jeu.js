/* Tile Lab — modes Jeu et Formes (plan 2026-09-03-plan-tuiles, T9 — tâche t115).
   RÈGLE : le navigateur voit et manipule, Python écrit. Aucun .tsx, .ldtk ni .tres n'est construit ici : on demande
   l'export au backend, puis on télécharge le fichier qu'il a écrit. Le seul dessin client est le pavage de la tuile
   de forme sur son réseau — une vue, rien n'est rangé.
   S'appuie sur tilelab.js (chargé avant) : la bascule des modes (tlMode) émet « tl-mode ». */
"use strict";

(function () {
  const $ = (s) => document.querySelector(s);
  const api = {
    async get(p) {
      const r = await fetch("/api" + p);
      if (!r.ok) throw new Error(await r.text());
      return r.json();
    },
    async post(p, body) {
      const r = await fetch("/api" + p, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.detail || r.statusText);
      return d;
    },
  };
  const esc = (s) => String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const vignette = (fn) => `/api/images/${encodeURIComponent(fn)}`;
  const etat = {
    images: [], charge: false,
    a: null, b: null, slot: "a",            // les deux matières du jeu, et la case qui reçoit le prochain clic
    tid: null, jeu: null, graineApercu: null, apercu: null,
    matiere: null, forme: null, formeMeta: null,
  };

  function statut(el, msg, err) { el.classList.remove("hidden"); el.classList.toggle("err", !!err); el.textContent = msg; }
  function vider(el) { el.classList.add("hidden"); el.textContent = ""; }
  function telecharger(url, nom) {
    const a = document.createElement("a");
    a.href = url; a.download = nom; document.body.appendChild(a); a.click(); a.remove();
  }

  /* ── les matières = les images de la Library ─────────────────────────────────────────────────────────────────── */
  async function charger() {
    const d = await api.get("/images");
    etat.images = (d.images || []).map((i) => i.filename);
    etat.charge = true;
    grille("#jeuGrid", "#jeuSearch", choisirJeu);
    grille("#formeGrid", "#formeSearch", choisirForme);
  }
  function grille(sel, rech, choisir) {
    const q = ($(rech).value || "").toLowerCase();
    const liste = etat.images.filter((f) => !q || f.toLowerCase().includes(q)).slice(0, 160);
    const g = $(sel);
    g.innerHTML = liste.map((f) => `<img loading="lazy" data-fn="${esc(f)}" title="${esc(f)}" src="${vignette(f)}">`).join("")
      || `<div class="empty-note">Aucune image dans la Library.</div>`;
    g.querySelectorAll("img").forEach((el) => { el.onclick = () => choisir(el.dataset.fn); });
  }
  function poserSlot(el, fn) {
    el.querySelector("img").src = fn ? vignette(fn) : "";
    el.querySelector(".tl-slot-n").textContent = fn || "—";
    el.classList.toggle("plein", !!fn);
  }

  /* ── mode Jeu ─────────────────────────────────────────────────────────────────────────────────────────────── */
  function slotActif(s) {
    etat.slot = s;
    $("#jeuSlotA").classList.toggle("on", s === "a");
    $("#jeuSlotB").classList.toggle("on", s === "b");
  }
  function choisirJeu(fn) {
    etat[etat.slot] = fn;
    poserSlot($(etat.slot === "a" ? "#jeuSlotA" : "#jeuSlotB"), fn);
    if (etat.slot === "a" && !etat.b) slotActif("b");     // A posée : le prochain clic remplit B
    $("#jeuRun").disabled = !(etat.a && etat.b);
  }

  async function fabriquer() {
    const st = $("#jeuStatus");
    if (!(etat.a && etat.b)) return statut(st, "Choisis deux matières (A puis B).", true);
    try {
      $("#jeuRun").disabled = true;
      statut(st, "Fabrication du jeu…");
      const d = await api.post("/tiles/jeu", {
        matiere_a: { image: etat.a }, matiere_b: { image: etat.b },
        jeu: $("#jeuKind").value, cote: parseInt($("#jeuCote").value, 10),
        variantes: parseInt($("#jeuVariantes").value, 10) || 1, graine: parseInt($("#jeuGraine").value, 10) || 1,
        nom: etat.a.replace(/\.[a-z0-9]+$/i, ""),
      });
      etat.tid = d.tid; etat.jeu = d;
      $("#jeuAtlas").src = `/api/tiles/${d.tid}/fichier/atlas.png?t=${Date.now()}`;
      $("#jeuInfo").textContent = `${d.tuiles} tuiles · ${d.colonnes}×${d.rangees} · raccord ${d.raccord}`;
      $("#jeuVide").classList.add("hidden"); $("#jeuCorps").classList.remove("hidden");
      $("#jeuMesures").innerHTML = `<span class="hint">Pas encore mesuré.</span>`;
      vider(st);
      await apercu(1);
    } catch (e) { statut(st, "Échec : " + e.message, true); }
    finally { $("#jeuRun").disabled = !(etat.a && etat.b); }
  }

  async function apercu(graine) {
    if (!etat.tid) return;
    const st = $("#jeuStatus");
    const g = graine || 1 + Math.floor(Math.random() * 99999);
    try {
      statut(st, "Aperçu…");
      const d = await api.post(`/tiles/${etat.tid}/apercu`, {
        cases: parseInt($("#jeuCases").value, 10), densite: parseFloat($("#jeuDensite").value), graine: g,
      });
      // la répétition se mesure sur CETTE carte : on garde sa graine, ses cases et sa densité
      etat.graineApercu = d.graine; etat.apercu = d;
      $("#jeuApercu").src = d.url + "?t=" + Date.now();
      $("#jeuApercuInfo").textContent = `${d.cases}×${d.cases} · graine ${d.graine}`;
      vider(st);
    } catch (e) { statut(st, "Échec : " + e.message, true); }
  }

  const PUCES = [
    // [clé de la mesure, clé du verdict, clé du seuil, libellé, sens du seuil]
    ["raccord", "raccord", "raccord", "raccord", "≤"],
    ["repetition", "repetition", "repetition", "répétition", "<"],
    ["eclairage_max", "eclairage", "eclairage", "éclairage", "≤"],
    ["ecart_eclairage", "ecart_eclairage", "ecart_eclairage", "écart d'éclairage", "≤"],
  ];
  async function mesurer() {
    if (!etat.tid) return;
    const st = $("#jeuStatus");
    try {
      statut(st, "Mesures…");
      const ap = etat.apercu || {};
      const d = await api.post(`/tiles/${etat.tid}/mesures`,
                               { graine: etat.graineApercu || 1, cases: ap.cases, densite: ap.densite });
      $("#jeuMesures").innerHTML = PUCES.map(([k, v, s, nom, sens]) =>
        `<span class="tl-chip ${d.verdict[v] === "ok" ? "good" : "warn"}" title="${d.verdict[v]}">` +
        `${nom} <b>${d[k]}</b> <i>${sens} ${d.seuils[s]}</i></span>`).join("");
      vider(st);
    } catch (e) { statut(st, "Échec : " + e.message, true); }
  }

  async function exporter(tid, format, st) {
    if (!tid) return;
    try {
      statut(st, "Export " + format + "…");
      const d = await api.post(`/tiles/${tid}/export`, { format });
      telecharger(d.url, d.fichier);
      statut(st, `${d.fichier} écrit (${d.octets} o) — pose-le à côté de atlas.png`);
    } catch (e) { statut(st, "Échec : " + e.message, true); }
  }
  const atlas = (tid) => tid && telecharger(`/api/tiles/${tid}/fichier/atlas.png`, "atlas.png");

  /* ── mode Formes ──────────────────────────────────────────────────────────────────────────────────────────── */
  function choisirForme(fn) {
    etat.matiere = fn;
    poserSlot($("#formeSlot"), fn);
    $("#formeRun").disabled = !fn;
  }

  async function fabriquerForme() {
    const st = $("#formeStatus");
    if (!etat.matiere) return statut(st, "Choisis une matière.", true);
    try {
      $("#formeRun").disabled = true;
      statut(st, "Fabrication…");
      const d = await api.post("/tiles/jeu", {
        matiere_a: { image: etat.matiere }, forme: $("#formeKind").value,
        cote: parseInt($("#formeCote").value, 10), nom: $("#formeKind").value,
      });
      etat.forme = d.tid; etat.formeMeta = d;
      const img = $("#formeImg");
      await new Promise((res, rej) => {        // onload plutôt que decode() : decode() reste suspendu en onglet caché
        img.onload = res; img.onerror = () => rej(new Error("tuile illisible"));
        img.src = `/api/tiles/${d.tid}/fichier/atlas.png?t=${Date.now()}`;
      });
      $("#formeInfo").textContent = `${d.largeur}×${d.hauteur} · raccord ${d.raccord}`;
      $("#formeVide").classList.add("hidden"); $("#formeCorps").classList.remove("hidden");
      paver(img, d);
      vider(st);
    } catch (e) { statut(st, "Échec : " + e.message, true); }
    finally { $("#formeRun").disabled = !etat.matiere; }
  }

  /* Le pavage MONTRE la tuile posée sur son réseau, aux mêmes décalages entiers que tile_shapes : losange (w/2, h/2),
     hexagone à sommet plat (3w/4, h/2) en colonnes décalées d'une demi-hauteur. */
  function paver(img, d) {
    const cv = $("#formePavage"), x = cv.getContext("2d");
    const w = d.largeur, h = d.hauteur;
    const k = Math.max(1, Math.floor(Math.min(cv.width / (w * 4), cv.height / (h * 4))));
    x.imageSmoothingEnabled = false;
    x.clearRect(0, 0, cv.width, cv.height);
    const W = cv.width / k, H = cv.height / k;
    x.save(); x.scale(k, k);
    if (d.forme === "iso") {
      for (let j = -2; j * (h / 2) < H + h; j++) {
        for (let i = -2; i * w < W + w; i++) x.drawImage(img, i * w + (j & 1 ? w / 2 : 0), j * (h / 2));
      }
    } else {
      for (let i = -2; i * (3 * w / 4) < W + w; i++) {
        for (let j = -2; j * h < H + h; j++) x.drawImage(img, i * (3 * w / 4), j * h + (i & 1 ? h / 2 : 0));
      }
    }
    x.restore();
  }

  /* ── branchements ─────────────────────────────────────────────────────────────────────────────────────────── */
  $("#jeuSlotA").onclick = () => slotActif("a");
  $("#jeuSlotB").onclick = () => slotActif("b");
  $("#jeuSearch").oninput = () => grille("#jeuGrid", "#jeuSearch", choisirJeu);
  $("#formeSearch").oninput = () => grille("#formeGrid", "#formeSearch", choisirForme);
  $("#jeuRun").onclick = fabriquer;
  $("#jeuApercuBtn").onclick = () => apercu();
  $("#jeuMesuresBtn").onclick = mesurer;
  $("#expAtlas").onclick = () => atlas(etat.tid);
  $("#expTiled").onclick = () => exporter(etat.tid, "tiled", $("#jeuStatus"));
  $("#expLdtk").onclick = () => exporter(etat.tid, "ldtk", $("#jeuStatus"));
  $("#expGodot").onclick = () => exporter(etat.tid, "godot", $("#jeuStatus"));
  $("#formeRun").onclick = fabriquerForme;
  $("#expFormeAtlas").onclick = () => atlas(etat.forme);
  $("#expFormeTiled").onclick = () => exporter(etat.forme, "tiled", $("#formeStatus"));
  $("#expFormeGodot").onclick = () => exporter(etat.forme, "godot", $("#formeStatus"));
  // la Library n'est lue qu'à la première entrée dans un des deux modes
  document.addEventListener("tl-mode", (e) => {
    if ((e.detail === "jeu" || e.detail === "formes") && !etat.charge) {
      charger().catch((err) => statut($(e.detail === "jeu" ? "#jeuStatus" : "#formeStatus"), "Library : " + err.message, true));
    }
  });

  /* poignée QA (preuve navigateur) */
  window.__tljeu = { get etat() { return etat; }, charger, choisirJeu, choisirForme, fabriquer, apercu, mesurer,
                     fabriquerForme, exporter };
})();
