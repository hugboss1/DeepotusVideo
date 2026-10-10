/* Tile Lab — mode Peintre (plan 2026-09-03-plan-tuiles, T12 — tâche t116).
   RÈGLE : le navigateur voit et manipule, Python compose. Le peintre ne connaît AUCUNE règle de tuilage : il pose des
   cases de terrain sur une grille booléenne et l'envoie à POST /api/tiles/{tid}/carte ; Python lit les voisinages,
   choisit les tuiles du jeu fabriqué dans le mode Jeu et écrit carte.png + carte.json, que la page affiche.
   Chaque coup de pinceau recompose (un instant après) : on voit l'auto-tuilage presque en direct.
   S'appuie sur jeu.js (chargé avant) : le jeu courant se lit dans window.__tljeu.etat. */
"use strict";

(function () {
  const $ = (s) => document.querySelector(s);
  const P = { grille: [], larg: 12, haut: 8, pose: 1, glisse: false, dernier: null, minuteur: 0, tid: null, envoi: 0 };

  function statut(msg, err, html) {
    const el = $("#peStatus");
    el.classList.remove("hidden"); el.classList.toggle("err", !!err);
    if (html) el.innerHTML = msg; else el.textContent = msg;   // html : un message fixe qui porte une icône
  }
  function jeuCourant() {
    const e = window.__tljeu && window.__tljeu.etat;
    return e && e.tid ? { tid: e.tid, jeu: e.jeu || {} } : null;
  }

  function nouvelleGrille() {
    P.larg = Math.max(2, Math.min(32, parseInt($("#peLargeur").value, 10) || 12));
    P.haut = Math.max(2, Math.min(32, parseInt($("#peHauteur").value, 10) || 8));
    $("#peLargeur").value = P.larg; $("#peHauteur").value = P.haut;
    P.grille = Array.from({ length: P.haut }, () => Array(P.larg).fill(0));
    dessiner();
  }

  /* la grille que l'on peint : une case = un carré ; le résultat composé par Python est l'image d'en dessous */
  function dessiner() {
    const cv = $("#peCanvas"), x = cv.getContext("2d");
    const k = Math.max(8, Math.floor(Math.min(480 / P.larg, 320 / P.haut)));
    cv.width = P.larg * k; cv.height = P.haut * k;
    x.fillStyle = "#1b1f27"; x.fillRect(0, 0, cv.width, cv.height);
    for (let j = 0; j < P.haut; j++) {
      for (let i = 0; i < P.larg; i++) {
        if (P.grille[j][i]) { x.fillStyle = "#3fb98a"; x.fillRect(i * k + 1, j * k + 1, k - 2, k - 2); }
      }
    }
    x.strokeStyle = "rgba(255,255,255,0.12)";
    for (let i = 0; i <= P.larg; i++) { x.beginPath(); x.moveTo(i * k + 0.5, 0); x.lineTo(i * k + 0.5, cv.height); x.stroke(); }
    for (let j = 0; j <= P.haut; j++) { x.beginPath(); x.moveTo(0, j * k + 0.5); x.lineTo(cv.width, j * k + 0.5); x.stroke(); }
  }

  function caseSous(ev) {
    const cv = $("#peCanvas"), b = cv.getBoundingClientRect();
    const i = Math.floor((ev.clientX - b.left) / b.width * P.larg), j = Math.floor((ev.clientY - b.top) / b.height * P.haut);
    return i >= 0 && j >= 0 && i < P.larg && j < P.haut ? [i, j] : null;
  }
  /* les cases traversées entre deux positions du pointeur (ligne de Bresenham, extrémités comprises) : un glisser
     rapide n'envoie que quelques pointermove — vu à l'écran le 06/10, une rangée glissée n'avait que 3 cases sur 7 */
  function ligneCases(a, b) {
    const out = [];
    let [x, y] = a;
    const dx = Math.abs(b[0] - x), dy = -Math.abs(b[1] - y), sx = x < b[0] ? 1 : -1, sy = y < b[1] ? 1 : -1;
    let err = dx + dy;
    for (;;) {
      out.push([x, y]);
      if (x === b[0] && y === b[1]) return out;
      const e2 = 2 * err;
      if (e2 >= dy) { err += dy; x += sx; }
      if (e2 <= dx) { err += dx; y += sy; }
    }
  }
  function peindre(ev) {
    const c = caseSous(ev);
    if (!c) return;
    let change = false;
    for (const [i, j] of ligneCases(P.dernier || c, c)) {
      if (P.grille[j][i] !== P.pose) { P.grille[j][i] = P.pose; change = true; }
    }
    P.dernier = c;
    if (!change) return;
    dessiner();
    clearTimeout(P.minuteur);
    P.minuteur = setTimeout(composer, 350);
  }

  async function composer() {
    const j = jeuCourant();
    if (!j) return statut(__dzT9("tuiles.tl1_pe.sans_jeu", "Fabrique d'abord un jeu dans le mode {icone} Jeu : le peintre pose SES tuiles.", { icone: dzIcone("dz-edit-autotuile", { taille: 16 }) }), true, true);
    const n = ++P.envoi;                       // seule la dernière réponse s'affiche (coups de pinceau rapides)
    try {
      statut(__dzT9("tuiles.tl1_pe.composition", "Composition…"));
      const r = await fetch(`/api/tiles/${encodeURIComponent(j.tid)}/carte`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ grille: P.grille, graine: parseInt($("#peGraine").value, 10) || 1 }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.detail || r.statusText);
      if (n !== P.envoi) return;
      $("#peCarte").src = d.url + "?t=" + Date.now();
      $("#pePng").href = d.url; $("#peJson").href = d.json;
      $("#peResultat").classList.remove("hidden");
      const terrain = P.grille.reduce((a, l) => a + l.reduce((b, v) => b + v, 0), 0);
      statut(__dzT9("tuiles.tl1_pe.info", "{l}×{h} · {n} case(s) de terrain · composée par Python", { l: P.larg, h: P.haut, n: terrain }));
    } catch (e) { if (n === P.envoi) statut(__dzT9("tuiles.tl1_x.echec", "Échec : {msg}", { msg: e.message }), true); }
  }

  function entrer() {
    const j = jeuCourant();
    if (j) $("#peJeu").textContent = __dzT9("tuiles.tl1_pe.jeu", "jeu {jeu} · {cote} px · {tid}", { jeu: j.jeu.jeu || "", cote: j.jeu.cote || "?", tid: j.tid });
    else $("#peJeu").innerHTML = __dzT9("tuiles.tl1_pe.aucun_jeu", "aucun jeu — fabrique-le dans le mode {icone} Jeu", { icone: dzIcone("dz-edit-autotuile", { taille: 16 }) });
    if (j && j.tid !== P.tid) { P.tid = j.tid; $("#peResultat").classList.add("hidden"); }
    if (!P.grille.length) nouvelleGrille(); else dessiner();
  }

  const cv = $("#peCanvas");
  cv.addEventListener("pointerdown", (ev) => {
    const c = caseSous(ev);
    if (!c) return;
    P.pose = P.grille[c[1]][c[0]] ? 0 : 1;     // le premier geste décide : poser ou gommer
    P.glisse = true; P.dernier = null; cv.setPointerCapture(ev.pointerId); peindre(ev);
  });
  cv.addEventListener("pointermove", (ev) => { if (P.glisse) peindre(ev); });
  cv.addEventListener("pointerup", () => { P.glisse = false; P.dernier = null; });
  $("#peEffacer").onclick = () => { nouvelleGrille(); clearTimeout(P.minuteur); P.minuteur = setTimeout(composer, 50); };
  $("#peLargeur").onchange = nouvelleGrille;
  $("#peHauteur").onchange = nouvelleGrille;
  $("#peGraine").onchange = composer;
  document.addEventListener("tl-mode", (e) => { if (e.detail === "peintre") entrer(); });

  window.__tlpeintre = { get etat() { return P; }, composer, nouvelleGrille, ligneCases };
})();
// t149 (traduction L9) : dzT dans la page, le français sous node (bancs)
function __dzT9(k, fr, v) { return typeof globalThis.dzT === "function" ? globalThis.dzT(k, v) : String(fr).replace(/\{(\w+)\}/g, (m, n) => (v && v[n] != null ? String(v[n]) : m)); }
