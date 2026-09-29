/* dz-plafonds.js — les PLAFONDS DE DÉPENSE MENSUELS côté navigateur (tâche #16,
   plan Settings T7, 29/09/2026). SOURCE : frontend/shared/dz-plafonds.js ;
   copie OCTET POUR OCTET : frontend/dist/shared/dz-plafonds.js, servie à
   /shared/dz-plafonds.js et chargée par une balise classique dans la SPA
   (frontend/dist/index.html, AVANT le module du bundle) et dans les pages à
   part (Atelier, Cardforge, Établi, Material Forge, Spritelab, Studio 3D,
   Tilelab, Vectorlab). Le banc backend/tests/test_p2_plafonds_ecran.py refuse
   toute dérive entre les deux copies et toute page oubliée.

   LE 402. Le serveur refuse un tir payant qui ferait passer le mois au-dessus
   d'un plafond : 402 `{"detail":{"dz_plafond":{motif, moteur, categorie,
   deja_usd, devis_usd, plafond_usd, message}}}` (backend/app/services/
   plafonds.py). Aucun appelant de l'application ne sait lire ce détail : la
   couche ENVELOPPE `window.fetch` UNE fois, pour tout le monde. Sur ce 402 :
   dialogue maison (`window.__dzDialogue.confirmer` ; absent : refus, rien ne part) — Tirer
   quand même rejoue LA MÊME requête avec l'en-tête `X-DZ-Plafond: confirme`
   et rend sa réponse à l'appelant, qui ne voit rien d'autre ; Annuler rend un
   402 dont le `detail` est une CHAÎNE (le message), que tous les lecteurs
   d'erreur de l'application affichent déjà. Un autre 402 (garde par requête
   `max_usd`, dictée) passe intact. Les demandes simultanées se posent l'une
   après l'autre.

   L'ALERTE. Après une écriture /api réussie (hors /api/reglages), relecture
   différée de /api/reglages/plafonds/etat : chaque plafond passé au seuil
   (80 % par défaut) est dit UNE fois par mois et par onglet, dans un bandeau
   non bloquant. Aussi une fois au chargement. Vanilla DOM, aucune dépendance
   au runtime React. */
(function () {
  if (window.__dzPlafonds) return;
  var ORIGINE = window.fetch ? window.fetch.bind(window) : null;
  if (!ORIGINE) return;
  var DIFFERE_MS = 2500;
  var dits = {};
  var file = Promise.resolve();
  var minuterie = null;

  function usd(v) {
    v = Number(v) || 0;
    var t;
    if (v !== 0 && Math.abs(v) < 0.1) {
      t = v.toFixed(4).replace(/0+$/, "");
      if (t.split(".")[1].length < 2) t += "0";
    } else {
      t = v.toFixed(2);
    }
    return t.replace(".", ",") + " $";
  }

  function demander(d) {
    var suite = file.then(function () {
      var msg = String((d && d.message) || "Plafond mensuel atteint.");
      var D = window.__dzDialogue;
      if (D && typeof D.confirmer === "function") {
        return D.confirmer(msg, { titre: "Plafond de dépense mensuel", ok: "Tirer quand même", annuler: "Annuler" });
      }
      return false;   // sans dialogue maison : refus, le sens SÛR (aucun dialogue natif dans l'application)
    }).then(function (v) { return !!v; }, function () { return false; });
    file = suite;
    return suite;
  }

  function annule(d) {
    var m = String((d && d.message) || "Plafond mensuel atteint.");
    m = m.replace(/\s*Confirmez pour tirer quand même, ou /, " Annulé : rien n'a été envoyé. Pour tirer, ");
    return new Response(JSON.stringify({ detail: m }), {
      status: 402, statusText: "Payment Required", headers: { "Content-Type": "application/json" }
    });
  }

  function chemin(i) {
    try {
      var u = typeof i === "string" ? i : (i && i.url) || String(i);
      return new URL(u, location.href).pathname;
    } catch (e) { return ""; }
  }

  function methode(i, o) {
    return String((o && o.method) || (i && typeof i === "object" && i.method) || "GET").toUpperCase();
  }

  function planifierAlerte() {
    if (minuterie) clearTimeout(minuterie);
    minuterie = setTimeout(function () { minuterie = null; verifierAlerte(); }, DIFFERE_MS);
  }

  function libelle(cle, e) {
    var v = cle === "global" ? e.global : (e.par_moteur || {})[cle];
    if (!v) return "";
    return (cle === "global" ? "plafond global" : "moteur « " + cle + " »") + " : " + String(v.pct).replace(".", ",")
      + " % (" + usd(v.effectif_usd) + " sur " + usd(v.plafond_usd) + ")";
  }

  function bandeau(lignes) {
    var b = document.createElement("div");
    b.setAttribute("data-dz-plafond-alerte", "1");
    b.setAttribute("role", "status");
    b.style.cssText = "position:fixed;right:16px;bottom:16px;z-index:9998;max-width:420px;padding:10px 12px;"
      + "background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid #d99a26;border-left:4px solid #d99a26;"
      + "color:var(--txt-base,var(--ink,#cfd6e2));font:12.5px/1.45 system-ui,sans-serif;box-shadow:0 10px 30px rgba(0,0,0,.45)";
    var t = document.createElement("div");
    t.style.cssText = "font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:#d99a26;margin-bottom:4px";
    t.textContent = "Dépenses du mois";
    b.appendChild(t);
    lignes.forEach(function (l) { var p = document.createElement("div"); p.textContent = l; b.appendChild(p); });
    var n = document.createElement("div");
    n.style.cssText = "margin-top:6px;color:var(--txt-mid,var(--ink-muted,#9aa4ae));font-size:11.5px";
    n.textContent = "Réglages → Pricing & budget pour voir ou relever les plafonds.";
    b.appendChild(n);
    var x = document.createElement("button");
    x.type = "button";
    x.textContent = "OK";
    x.title = "Fermer cette alerte (elle ne revient pas ce mois-ci dans cet onglet)";
    x.style.cssText = "margin-top:8px;height:24px;padding:0 12px;background:transparent;border:1px solid #d99a26;color:inherit;cursor:pointer";
    x.onclick = function () { if (b.parentNode) b.parentNode.removeChild(b); };
    b.appendChild(x);
    (document.body || document.documentElement).appendChild(b);
    setTimeout(function () { if (b.parentNode) b.parentNode.removeChild(b); }, 20000);
    return b;
  }

  function verifierAlerte() {
    return ORIGINE("/api/reglages/plafonds/etat").then(function (R) { return R.ok ? R.json() : null; }).then(function (e) {
      if (!e || !e.alerte || !e.alerte.length) return [];
      var neufs = [];
      e.alerte.forEach(function (c) {
        var k = e.mois + ":" + c + ":" + (e.plafonds && e.plafonds.alerte_pct);
        var vu = dits[k];
        try { vu = vu || sessionStorage.getItem("dzplaf:" + k); } catch (x) { /* stockage indisponible */ }
        if (vu) return;
        dits[k] = 1;
        try { sessionStorage.setItem("dzplaf:" + k, "1"); } catch (x) { /* idem */ }
        var l = libelle(c, e);
        if (l) neufs.push(l);
      });
      if (neufs.length) bandeau(neufs);
      try { window.dispatchEvent(new Event("dz-plafonds")); } catch (x) { /* vieux moteur */ }
      return neufs;
    }).catch(function () { return []; });
  }

  async function enveloppe(i, o) {
    var copie = null;
    try { if (typeof Request !== "undefined" && i instanceof Request) copie = i.clone(); } catch (e) { copie = null; }
    var R = await ORIGINE(i, o);
    var p = chemin(i), m = methode(i, o);
    if (R.status !== 402) {
      if (R.ok && m !== "GET" && m !== "HEAD" && p.indexOf("/api/") === 0 && p.indexOf("/api/reglages/") !== 0) planifierAlerte();
      return R;
    }
    var d = null;
    try { var j = await R.clone().json(); d = j && j.detail && j.detail.dz_plafond; } catch (e) { d = null; }
    if (!d) return R;
    if (!(await demander(d))) return annule(d);
    var h = new Headers((o && o.headers) || (copie ? copie.headers : undefined));
    h.set("X-DZ-Plafond", "confirme");
    var R2 = copie ? await ORIGINE(new Request(copie, Object.assign({}, o || {}, { headers: h })))
                   : await ORIGINE(i, Object.assign({}, o || {}, { headers: h }));
    if (R2.ok) planifierAlerte();
    return R2;
  }

  window.fetch = enveloppe;
  window.__dzPlafonds = { demander: demander, verifierAlerte: verifierAlerte, usd: usd, origine: ORIGINE, differeMs: DIFFERE_MS };
  setTimeout(verifierAlerte, 4000);
})();
