/* dz-veille.js — l'écran « Veille » de l'agent Campagnes (t352, 27/10/2026, spec
   docs/superpowers/specs/2026-10-27-agent-veille-prospection-design.md §5, P1). SOURCE : frontend/shared/dz-veille.js ;
   copie OCTET POUR OCTET : frontend/dist/shared/dz-veille.js, chargée par frontend/dist/index.html (balise classique
   après dz-campagnes.js). Monté par le 3e onglet du tiroir F1 (dz-agent.js). Le banc backend/tests/test_veille_ecran.py
   refuse toute dérive, le banc node frontend/shared/qa/veille.test.mjs joue le composant sur un DOM simulé.

   window.DzVeille.monter(el, { espace_id }) -> { demonter(), recharger() }

   Le contrat du serveur (backend/app/api/veille_routes.py) :
   - GET  /api/veille/{eid}            {etat, rapport|null, veilles}
   - POST /api/veille/{eid}/collectes  202 (collecte de fond : relue toutes les SONDE_MS tant qu'elle tourne) ; 409 ;
   - POST /api/veille/{eid}/importer   {dossier} : le verbatims.jsonl d'une veille faite hors de l'app ; 413, 422.
   Lecture seule, gratuite : aucun bouton ne publie, n'écrit à un concurrent ni ne dépense. Les citations collectées sont
   posées en textContent (jamais en HTML) et un lien n'est cliquable que s'il est en http(s). Les libellés viennent de
   dzT (zone.objet.role) ; les phrases « preuve » et « angle » viennent du serveur en {fr, en}. Vanilla DOM. */
(function () {
  "use strict";
  if (window.DzVeille) return;

  var BASE = "/api/veille/";
  var SONDE_MS = 3000;
  var THEMES = ["prix_credits", "qualite_sortie", "coherence", "controle", "vitesse_files", "censure_moderation",
    "droits_licence", "confidentialite_local", "flux_travail", "game_assets", "social_publication",
    "support_fiabilite", "apprentissage", "fournisseur_unique"];
  var ETATS = ["en_cours", "fini", "fini_partiel", "erreur", "interrompu"];
  var CHEZ_NOUS = ["regle", "partiel", "absent", "inconnu"];
  var JSON_H = { "Content-Type": "application/json" };

  function T(cle, vars) { return typeof window.dzT === "function" ? window.dzT(cle, vars) : cle; }
  function langue() {
    var l = typeof window.dzLang === "function" ? window.dzLang() : window.dzLang;
    return l === "en" ? "en" : "fr";
  }
  function bilingue(v) { return v && typeof v === "object" ? (v[langue()] || v.fr || "") : (v || ""); }
  function theme(c) { return THEMES.indexOf(c) >= 0 ? T("veille.theme." + c) : String(c || ""); }
  function el(tag, attrs, enfants) {
    var n = document.createElement(tag);
    var a = attrs || {};
    for (var k in a) {
      if (k === "texte") n.textContent = a[k];
      else if (k === "on") for (var e in a.on) n.addEventListener(e, a.on[e]);
      else n.setAttribute(k, a[k]);
    }
    (enfants || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }
  function vider(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function sur(url) { return typeof url === "string" && /^https?:\/\//i.test(url); }

  var CSS = ""
    + ".dzVeille{display:flex;flex-direction:column;flex:1 1 auto;min-height:0;height:100%;background:var(--bg-panel,#151519);color:var(--ink,#c4bfb6);"
    + "font-family:var(--f-ui,system-ui,sans-serif);font-size:13px;line-height:1.5}"
    + ".dzVeilleBarre{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center;padding:8px 12px;border-bottom:1px solid var(--stroke,#2a2930)}"
    + ".dzVeille button{background:var(--bg-panel-2,#1c1c21);color:var(--ink-strong,#f2efe9);border:1px solid var(--stroke,#2a2930);border-radius:var(--r);padding:3px 10px;font:inherit;cursor:pointer}"
    + ".dzVeille button:disabled{opacity:.55;cursor:default}"
    + ".dzVeille input{flex:1;min-width:120px;background:var(--bg-panel-2,#1c1c21);color:inherit;border:1px solid var(--stroke,#2a2930);border-radius:var(--r);padding:3px 6px;font:inherit}"
    + ".dzVeilleNote{width:100%;font-size:11px;color:var(--ink-soft,#8a857d)}"
    + ".dzVeilleEtat{width:100%;font-family:var(--f-mono,monospace);font-size:11px;color:var(--ink-soft,#8a857d);white-space:pre-wrap}"
    + ".dzVeilleEtat[data-erreur]{color:var(--red,#e35d4a)}"
    + ".dzVeilleCorps{flex:1;min-height:0;overflow:auto;padding:10px 12px;display:flex;flex-direction:column;gap:14px}"
    + ".dzVeille h3{margin:0 0 4px;font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--ink-strong,#f2efe9)}"
    + ".dzVeille ol,.dzVeille ul{margin:0;padding-left:18px;display:flex;flex-direction:column;gap:6px}"
    + ".dzVeilleMatrice{overflow:auto}"
    + ".dzVeilleMatrice table{border-collapse:collapse;font-family:var(--f-mono,monospace);font-size:11px}"
    + ".dzVeilleMatrice th,.dzVeilleMatrice td{border:1px solid var(--stroke,#2a2930);padding:2px 6px;text-align:center;white-space:nowrap}"
    + ".dzVeilleMatrice th{color:var(--ink-soft,#8a857d);font-weight:500}"
    + ".dzVeilleMatrice td[data-max]{color:var(--ink-strong,#f2efe9);font-weight:700}"
    + ".dzVeilleCit{margin:2px 0 0;padding-left:8px;border-left:2px solid var(--stroke,#2a2930);color:var(--ink-soft,#8a857d)}"
    + ".dzVeilleCit a{color:var(--accent,#f0b429)}"
    + ".dzVeilleChez{font-size:11px;color:var(--ink-soft,#8a857d)}"
    + ".dzVeilleDiff{white-space:pre-wrap;font-size:11px;margin:4px 0 8px;color:var(--ink-soft,#8a857d)}"
    + ".dzVeilleVide{color:var(--ink-soft,#8a857d)}";
  function poserCss() {
    if (document.getElementById && document.getElementById("dzVeilleCss")) return;
    var s = el("style", { id: "dzVeilleCss" });
    s.textContent = CSS;
    (document.head || document.documentElement).appendChild(s);
  }

  async function lireJson(r) { try { return await r.json(); } catch (e) { return {}; } }

  function monter(hote, opts) {
    poserCss();
    var eid = (opts && typeof opts.espace_id === "string") ? opts.espace_id : "";
    var vivant = true, sonde = null;
    var racine = el("div", { class: "dzVeille", "data-dz-veille": "racine" });
    var etatLigne = el("div", { class: "dzVeilleEtat", "data-dz-veille": "etat", role: "status" });
    var btnLancer = el("button", { type: "button", "data-dz-veille": "lancer", texte: T("veille.bouton.lancer"), on: { click: lancer } });
    var btnImporter = el("button", { type: "button", "data-dz-veille": "importer", texte: T("veille.bouton.importer"), on: { click: montrerImport } });
    var champ = el("input", { type: "text", "data-dz-veille": "dossier", "aria-label": T("veille.import.dossier"),
      placeholder: T("veille.import.exemple"), hidden: "" });
    var btnValider = el("button", { type: "button", "data-dz-veille": "valider-import", texte: T("veille.bouton.valider"), hidden: "", on: { click: importer } });
    var note = el("div", { class: "dzVeilleNote", "data-dz-veille": "note", texte: T("veille.collecte.note") });
    var corps = el("div", { class: "dzVeilleCorps", "data-dz-veille": "corps" });
    racine.appendChild(el("div", { class: "dzVeilleBarre" }, [btnLancer, btnImporter, champ, btnValider, note, etatLigne]));
    racine.appendChild(corps);
    hote.appendChild(racine);

    function dire(texte, erreur) {
      etatLigne.textContent = texte || "";
      if (erreur) etatLigne.setAttribute("data-erreur", ""); else etatLigne.removeAttribute("data-erreur");
    }
    function montrerImport() { champ.removeAttribute("hidden"); btnValider.removeAttribute("hidden"); champ.focus(); }
    function arreterSonde() { if (sonde) { clearTimeout(sonde); sonde = null; } }

    function direEtat(e) {
      if (!e || ETATS.indexOf(e.etat) < 0) { dire(""); return; }
      var lignes = [T("veille.etat." + e.etat, { date: e.date || "" })];
      if (e.etat === "en_cours" && Array.isArray(e.journal) && e.journal.length) lignes.push(String(e.journal[e.journal.length - 1]));
      dire(lignes.join("\n"), e.etat === "erreur");
    }

    var generation = 0;                 // seule la DERNIÈRE relecture dessine (sonde en vol + ↺ ou import : pas de doublon)
    async function recharger() {
      arreterSonde();
      var g = ++generation;
      if (!eid) { vider(corps); corps.appendChild(el("p", { class: "dzVeilleVide", "data-dz-veille": "sans-espace", texte: T("veille.vide.sans_espace") })); btnLancer.setAttribute("disabled", ""); btnImporter.setAttribute("disabled", ""); return; }
      btnLancer.removeAttribute("disabled"); btnImporter.removeAttribute("disabled");
      var j;
      try {
        var r = await window.fetch(BASE + encodeURIComponent(eid));
        if (!vivant || g !== generation) return;
        if (!r.ok) { dire(T("veille.erreur.lecture", { code: r.status }), true); return; }
        j = await lireJson(r);
      } catch (e) { if (vivant && g === generation) dire(T("veille.erreur.reseau"), true); return; }
      if (!vivant || g !== generation) return;
      arreterSonde();
      vider(corps);
      direEtat(j.etat);
      var enCours = j.etat && j.etat.etat === "en_cours";
      if (enCours) { btnLancer.setAttribute("disabled", ""); sonde = setTimeout(recharger, SONDE_MS); }
      if (j.rapport) dessiner(j.rapport);
      else corps.appendChild(el("p", { class: "dzVeilleVide", "data-dz-veille": "vide", texte: T("veille.vide.aucune") }));
      concurrents(g);
    }

    // t368 : le volet « Concurrents » (lecture seule) — pubs actives, pages prix changées, positions sur nos mots-clés
    async function concurrents(g) {
      var k;
      try {
        var r = await window.fetch(BASE + encodeURIComponent(eid) + "/concurrents");
        if (!vivant || g !== generation || !r.ok) return;
        k = await lireJson(r);
      } catch (e) { return; }
      if (!vivant || g !== generation || !k) return;
      var blocs = [];
      var pubs = k.pubs || {};
      Object.keys(pubs).sort().forEach(function (c) {
        var liste = Array.isArray(pubs[c]) ? pubs[c] : [];
        blocs.push(el("p", { "data-dz-veille": "pubs-" + c, texte: T("veille.concurrents.pubs", { nom: c, n: liste.length }) }));
        blocs.push(el("ul", {}, liste.slice(0, 3).map(function (p) {
          var li = el("li", {}, [el("span", { texte: String((p && p.texte) || "") + (p && p.debut ? " · " + T("veille.concurrents.depuis", { date: p.debut }) : "") })]);
          if (p && sur(p.lien)) li.appendChild(el("a", { href: p.lien, target: "_blank", rel: "noopener noreferrer", texte: " " + T("veille.concurrents.voir") }));
          return li;
        })));
      });
      (Array.isArray(k.pages) ? k.pages : []).filter(function (p) { return p && p.change; }).forEach(function (p) {
        blocs.push(el("p", { "data-dz-veille": "page-changee", texte: T("veille.concurrents.page_changee", { nom: String(p.concurrent || ""), url: String(p.url || "") }) }));
        blocs.push(el("pre", { class: "dzVeilleDiff", texte: String(p.diff || "") }));
      });
      var mots = (k.serp && k.serp.mots_cles) || {};
      Object.keys(mots).forEach(function (m) {
        var leurs = (Array.isArray(mots[m]) ? mots[m] : []).filter(function (x) { return x && x.concurrent; });
        blocs.push(el("p", { "data-dz-veille": "serp", texte: leurs.length
          ? T("veille.concurrents.serp", { mot: m, rangs: leurs.map(function (x) { return x.concurrent + " #" + x.rang; }).join(", ") })
          : T("veille.concurrents.serp_aucun", { mot: m }) }));
      });
      if (blocs.length) corps.appendChild(section("veille.section.concurrents", "concurrents", blocs));
    }

    async function lancer() {
      if (!eid) return;
      btnLancer.setAttribute("disabled", "");
      try {
        var r = await window.fetch(BASE + encodeURIComponent(eid) + "/collectes", { method: "POST", headers: JSON_H, body: "{}" });
        if (!vivant) return;
        if (r.status === 409) { await recharger(); if (vivant) dire(T("veille.etat.conflit"), true); return; }
        if (!r.ok) { var j = await lireJson(r); dire(T("veille.erreur.collecte", { detail: String((j && j.detail) || r.status) }), true); btnLancer.removeAttribute("disabled"); return; }
      } catch (e) { if (vivant) { dire(T("veille.erreur.reseau"), true); btnLancer.removeAttribute("disabled"); } return; }
      recharger();
    }

    async function importer() {
      var dossier = String(champ.value || "").trim();
      if (!eid || !dossier) { champ.focus(); return; }
      btnValider.setAttribute("disabled", "");
      try {
        var r = await window.fetch(BASE + encodeURIComponent(eid) + "/importer", { method: "POST", headers: JSON_H, body: JSON.stringify({ dossier: dossier }) });
        if (!vivant) return;
        var j = await lireJson(r);
        if (r.status === 413) dire(T("veille.erreur.trop_gros"), true);
        else if (!r.ok) dire(T("veille.erreur.import", { detail: String((j && j.detail) || r.status) }), true);
        else {
          champ.value = ""; champ.setAttribute("hidden", ""); btnValider.setAttribute("hidden", "");
          await recharger();
          dire(T("veille.import.fait", { n: j.lignes, ignorees: j.ignorees, date: j.date }));
        }
      } catch (e) { if (vivant) dire(T("veille.erreur.reseau"), true); }
      btnValider.removeAttribute("disabled");
    }

    function section(cle, marque, enfants) {
      return el("section", { "data-dz-veille": marque }, [el("h3", { texte: T(cle) })].concat(enfants));
    }
    function citations(liste) {
      return (liste || []).map(function (c) {
        var q = el("blockquote", { class: "dzVeilleCit" });
        q.appendChild(el("span", { texte: "« " + String(c.texte || "") + " » " }));
        var src = [c.concurrent, c.source, c.date].filter(Boolean).join(" · ");
        if (sur(c.url)) q.appendChild(el("a", { href: c.url, target: "_blank", rel: "noopener noreferrer", texte: src || T("veille.citation.lien") }));
        else q.appendChild(el("span", { texte: src }));
        return q;
      });
    }
    function chezNous(statut, preuve) {
      var s = CHEZ_NOUS.indexOf(statut) >= 0 ? statut : "inconnu";
      var t = T("veille.chez_nous." + s);
      var p = bilingue(preuve);
      return el("div", { class: "dzVeilleChez", texte: p ? T("veille.chez_nous.avec_preuve", { statut: t, preuve: p }) : t });
    }

    function matrice(m) {
      var concurrents = Object.keys(m || {});
      var cols = THEMES.filter(function (t) { return concurrents.some(function (c) { var v = m[c][t]; return v && (v.f || v.F); }); });
      if (!concurrents.length || !cols.length) return el("p", { class: "dzVeilleVide", texte: T("veille.vide.matrice") });
      var total = function (c) { return cols.reduce(function (s, t) { var v = m[c][t]; return s + (v ? v.f + v.F : 0); }, 0); };
      concurrents.sort(function (a, b) { return total(b) - total(a) || (a < b ? -1 : 1); });
      var tete = el("tr", {}, [el("th", { texte: T("veille.matrice.concurrent") })].concat(cols.map(function (t) { return el("th", { texte: theme(t), title: theme(t) }); })));
      var lignes = concurrents.map(function (c) {
        var maxF = Math.max.apply(null, cols.map(function (t) { var v = m[c][t]; return v ? v.f : 0; }));
        return el("tr", {}, [el("th", { texte: c })].concat(cols.map(function (t) {
          var v = m[c][t];
          var attrs = { texte: v ? (v.f + "/" + v.F) : "—" };
          if (v && maxF > 0 && v.f === maxF) attrs["data-max"] = "";
          return el("td", attrs);
        })));
      });
      return el("div", { class: "dzVeilleMatrice" }, [el("table", { "aria-label": T("veille.section.matrice") }, [el("thead", {}, [tete]), el("tbody", {}, lignes)])]);
    }

    function dessiner(R) {
      var v = R.volumes || {};
      var periode = Array.isArray(v.periode) ? v.periode.join(" → ") : "—";
      var sources = Object.keys(v.par_source || {}).map(function (s) { return s + " " + v.par_source[s]; }).join(", ");
      corps.appendChild(section("veille.section.bref", "bref", [
        el("p", { texte: T("veille.bref.volumes", { date: R.date || "", gardes: v.gardes || 0, brut: v.brut || 0, periode: periode }) }),
        el("p", { texte: T("veille.bref.sources", { sources: sources || "—" }) }),
        el("p", { "data-dz-veille": "classement", texte: T(R.classement === "importe" ? "veille.classement.importe" : "veille.classement.auto") }),
      ]));
      corps.appendChild(section("veille.section.matrice", "matrice", [el("p", { class: "dzVeilleNote", texte: T("veille.matrice.legende") }), matrice(R.matrice)]));
      var douleurs = R.douleurs || [];
      corps.appendChild(section("veille.section.douleurs", "douleurs", douleurs.length ? [el("ol", {}, douleurs.map(function (d) {
        return el("li", {}, [el("strong", { texte: theme(d.theme) }),
          el("span", { texte: " " + T("veille.douleur.compte", { n: d.n, n3: d.n3, auteurs: d.auteurs, concurrents: (d.concurrents || []).slice(0, 5).join(", ") }) })]
          .concat(citations(d.citations)).concat([chezNous(d.chez_nous, d.preuve)]));
      }))] : [el("p", { class: "dzVeilleVide", texte: T("veille.vide.douleurs") })]));
      var angles = R.angles || [];
      corps.appendChild(section("veille.section.angles", "angles", angles.length ? [el("ul", {}, angles.map(function (a) {
        return el("li", {}, [el("strong", { texte: bilingue(a.angle) }), el("div", { class: "dzVeilleChez", texte: T("veille.angle.preuve", { preuve: bilingue(a.preuve), n: a.n }) })]);
      }))] : [el("p", { class: "dzVeilleVide", texte: T("veille.vide.angles") })]));
      var forces = R.forces || [];
      if (forces.length) corps.appendChild(section("veille.section.forces", "forces", [el("ul", {}, forces.map(function (f) {
        return el("li", {}, [el("span", { texte: T("veille.force.ligne", { theme: theme(f.theme), n: f.n, concurrents: (f.concurrents || []).join(", ") }) })].concat(citations(f.citations)));
      }))]));
      var demandes = R.demandes || [];
      corps.appendChild(section("veille.section.demandes", "demandes", [el("p", { class: "dzVeilleNote", texte: T("veille.demande.regle") })].concat(demandes.length ? [el("ul", {}, demandes.map(function (d) {
        return el("li", {}, [el("span", { texte: T("veille.demande.ligne", { theme: theme(d.theme), n: d.n }) })].concat(citations(d.citations)));
      }))] : [el("p", { class: "dzVeilleVide", texte: T("veille.vide.demandes") })])));
      var limites = R.limites || [];
      if (limites.length) corps.appendChild(section("veille.section.limites", "limites", [el("ul", {}, limites.map(function (l) { return el("li", { texte: String(l) }); }))]));
    }

    recharger();
    return {
      demonter: function () { vivant = false; arreterSonde(); if (racine.parentNode) racine.parentNode.removeChild(racine); },
      recharger: recharger,
    };
  }

  window.DzVeille = { monter: monter };
})();
