/* dz-croissance.js — l'écran « Croissance » de l'agent Campagnes (t492, lot G2, 09/11/2026, conception
   docs/superpowers/specs/2026-11-09-getripping-design.md). SOURCE : frontend/shared/dz-croissance.js ; copie OCTET POUR
   OCTET : frontend/dist/shared/dz-croissance.js, chargée par frontend/dist/index.html (balise classique après
   dz-prospects.js). Monté par le 5e onglet du tiroir F1 (dz-agent.js). Le banc backend/tests/test_croissance_ecran.py
   refuse toute dérive, le banc node frontend/shared/qa/croissance.test.mjs joue le composant sur un DOM simulé.

   window.DzCroissance.monter(el) -> { demonter(), recharger() }

   Le contrat du serveur :
   - GET  /api/schedule/croissance?days=&espace_id=&tz=   {totaux, canaux, top, gagnants, seuil_gagnant, regularite, compte}
   - POST /api/schedule/analytics/refresh                 la passe de mesures (rationnée par le serveur)
   - GET  /api/espaces                                    la liste du filtre
   Lecture seule : aucun bouton ne publie ni ne dépense. Tout texte venu du serveur (titres, noms) est posé en
   textContent. Les libellés viennent de dzT (zone.objet.role). Vanilla DOM, aucune dépendance. */
(function () {
  "use strict";
  if (window.DzCroissance) return;

  var PERIODES = [7, 30, 90];
  var RAISONS = ["trop_tot", "peu_de_recul", "sans_releve"];
  var TUILES_COMPTE = ["views", "reach", "followers", "follows", "interactions", "non_abonnes_pct"];
  var TUILES_POSTS = ["posts", "views", "engagement"];
  var JALONS = ["j1", "j3", "j7", "j30"];

  function T(cle, vars) { return typeof window.dzT === "function" ? window.dzT(cle, vars) : cle; }
  function langue() {
    var l = typeof window.dzLang === "function" ? window.dzLang() : window.dzLang;
    return l === "en" ? "en" : "fr";
  }
  function nombre(v) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    var loc = langue() === "en" ? "en-US" : "fr-FR";
    if (Math.abs(v) >= 1e6) return (v / 1e6).toLocaleString(loc, { maximumFractionDigits: 1 }) + " M";
    if (Math.abs(v) >= 1e4) return (v / 1e3).toLocaleString(loc, { maximumFractionDigits: 1 }) + " k";
    return v.toLocaleString(loc, { maximumFractionDigits: 1 });
  }
  function fois(m) { return nombre(m) + "×"; }
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

  var CSS = ""
    + ".dzCroi{display:flex;flex-direction:column;flex:1 1 auto;min-height:0;height:100%;background:var(--bg-panel,#151519);color:var(--ink,#c4bfb6);"
    + "font-family:var(--f-ui,system-ui,sans-serif);font-size:13px;line-height:1.5}"
    + ".dzCroiBarre{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center;padding:8px 12px;border-bottom:1px solid var(--stroke,#2a2930)}"
    + ".dzCroi button,.dzCroi select{background:var(--bg-panel-2,#1c1c21);color:var(--ink-strong,#f2efe9);border:1px solid var(--stroke,#2a2930);border-radius:var(--r);padding:3px 10px;font:inherit}"
    + ".dzCroi button{cursor:pointer}.dzCroi button:disabled{opacity:.55;cursor:default}"
    + ".dzCroiEtat{width:100%;font-family:var(--f-mono,monospace);font-size:11px;color:var(--ink-soft,#8a857d)}"
    + ".dzCroiEtat[data-erreur]{color:var(--red,#e35d4a)}"
    + ".dzCroiCorps{flex:1;min-height:0;overflow:auto;padding:10px 12px;display:flex;flex-direction:column;gap:16px}"
    + ".dzCroi h3{margin:0 0 6px;font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--ink-strong,#f2efe9)}"
    + ".dzCroiTuiles{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}"
    + ".dzCroiTuile{border:1px solid var(--stroke,#2a2930);border-radius:var(--r);padding:6px 8px;display:flex;flex-direction:column;gap:2px;min-width:0}"
    + ".dzCroiTuile b{font-size:17px;font-weight:600;color:var(--ink-strong,#f2efe9);font-variant-numeric:tabular-nums}"
    + ".dzCroiTuile span{font-size:11px;color:var(--ink-soft,#8a857d);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}"
    + ".dzCroiNote{font-size:11px;color:var(--ink-soft,#8a857d);margin:4px 0 0}"
    + ".dzCroiSemaine{display:grid;grid-template-columns:repeat(7,1fr);gap:4px}"
    + ".dzCroiJour{border:1px solid var(--stroke,#2a2930);border-radius:var(--r);padding:4px 0;text-align:center;font-size:11px;color:var(--ink-soft,#8a857d)}"
    + ".dzCroiJour[data-posts]{background:var(--accent,#f0b429);border-color:var(--accent,#f0b429);color:#151519;font-weight:600}"
    + ".dzCroiPosts{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px}"
    + ".dzCroiPost{border:1px solid var(--stroke,#2a2930);border-radius:var(--r);padding:6px 8px;display:grid;grid-template-columns:1fr auto;gap:2px 8px}"
    + ".dzCroiPost strong{color:var(--ink-strong,#f2efe9);font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}"
    + ".dzCroiMult{font-family:var(--f-mono,monospace);font-variant-numeric:tabular-nums;color:var(--ink-strong,#f2efe9);text-align:right}"
    + ".dzCroiMult[data-gagnant]{color:var(--accent,#f0b429);font-weight:700}"
    + ".dzCroiDetail{grid-column:1 / -1;font-size:11px;color:var(--ink-soft,#8a857d)}"
    + ".dzCroiVide{color:var(--ink-soft,#8a857d);margin:0}";
  function poserCss() {
    if (document.getElementById && document.getElementById("dzCroiCss")) return;
    var s = el("style", { id: "dzCroiCss" });
    s.textContent = CSS;
    (document.head || document.documentElement).appendChild(s);
  }

  async function lireJson(r) { try { return await r.json(); } catch (e) { return {}; } }

  function monter(hote) {
    poserCss();
    var vivant = true, jours = 30, espace = "", tour = 0;
    var racine = el("div", { class: "dzCroi", "data-dz-croissance": "racine" });
    var selPeriode = el("select", { "data-dz-croissance": "periode", "aria-label": T("croissance.periode.libelle") },
      PERIODES.map(function (p) { return el("option", { value: String(p), texte: T("croissance.periode.jours", { n: p }) }); }));
    selPeriode.value = String(jours);
    var selEspace = el("select", { "data-dz-croissance": "espace", "aria-label": T("croissance.espace.libelle") },
      [el("option", { value: "", texte: T("croissance.espace.tous") })]);
    var btnRelever = el("button", { type: "button", "data-dz-croissance": "relever", texte: T("croissance.bouton.relever"),
      title: T("croissance.bouton.relever_aide"), on: { click: relever } });
    var etat = el("div", { class: "dzCroiEtat", "data-dz-croissance": "etat", role: "status" });
    var corps = el("div", { class: "dzCroiCorps", "data-dz-croissance": "corps" });
    racine.appendChild(el("div", { class: "dzCroiBarre" }, [selPeriode, selEspace, btnRelever, etat]));
    racine.appendChild(corps);
    hote.appendChild(racine);
    selPeriode.addEventListener("change", function () { jours = parseInt(selPeriode.value, 10) || 30; recharger(); });
    selEspace.addEventListener("change", function () { espace = selEspace.value || ""; recharger(); });

    function dire(texte, erreur) {
      etat.textContent = texte || "";
      if (erreur) etat.setAttribute("data-erreur", "1"); else etat.removeAttribute("data-erreur");
    }
    function section(cle, marque, enfants) {
      return el("section", { "data-dz-croissance": marque }, [el("h3", { texte: T(cle) })].concat(enfants));
    }
    function tuile(cle, valeur, marque) {
      return el("div", { class: "dzCroiTuile", "data-dz-croissance": marque }, [el("b", { texte: valeur }), el("span", { texte: T(cle) })]);
    }

    async function lireEspaces() {
      try {
        var j = await lireJson(await window.fetch("/api/espaces"));
        (Array.isArray(j.espaces) ? j.espaces : []).forEach(function (e) {
          if (e && typeof e.id === "string" && !e.archive) {
            selEspace.appendChild(el("option", { value: e.id, texte: typeof e.nom === "string" ? e.nom : e.id }));
          }
        });
      } catch (e) { /* hors ligne : « tous les espaces » reste */ }
    }

    async function recharger() {
      var moi = ++tour;
      dire(T("croissance.etat.lecture"));
      var d = null;
      try {
        var q = "?days=" + jours + "&tz=" + (-new Date().getTimezoneOffset()) + (espace ? "&espace_id=" + encodeURIComponent(espace) : "");
        var r = await window.fetch("/api/schedule/croissance" + q);
        if (r.ok) d = await lireJson(r);
      } catch (e) { d = null; }
      if (!vivant || moi !== tour) return;
      if (!d || !d.totaux) { dire(T("croissance.etat.erreur"), true); return; }
      dire("");
      dessiner(d);
    }

    async function relever() {
      btnRelever.setAttribute("disabled", "");
      dire(T("croissance.etat.releve"));
      var bon = false;
      try { bon = (await window.fetch("/api/schedule/analytics/refresh", { method: "POST" })).ok; } catch (e) { bon = false; }
      if (!vivant) return;
      btnRelever.removeAttribute("disabled");
      if (!bon) { dire(T("croissance.etat.releve_erreur"), true); return; }
      recharger();
    }

    function compte(c) {
      var ig = c && c.instagram;
      if (!ig) {
        return section("croissance.section.compte", "compte", [el("p", { class: "dzCroiVide", "data-dz-croissance": "compte-absent",
          texte: T(c && c.erreur ? "croissance.compte.erreur" : "croissance.compte.absent") })]);
      }
      var enfants = [el("div", { class: "dzCroiTuiles" }, TUILES_COMPTE.map(function (k) {
        var v = ig[k];
        return tuile("croissance.compte." + k, k === "non_abonnes_pct" && typeof v === "number" ? nombre(v) + " %" : nombre(v), "compte-" + k);
      }))];
      enfants.push(el("p", { class: "dzCroiNote", texte: T("croissance.compte.note", { nom: ig.username || "—", n: ig.jours }) }));
      if ((ig.illisibles || []).length) {
        enfants.push(el("p", { class: "dzCroiNote", "data-dz-croissance": "illisibles", texte: T("croissance.compte.illisibles", { n: ig.illisibles.length }) }));
      }
      return section("croissance.section.compte", "compte", enfants);
    }

    function regularite(g) {
      var sem = (g && g.semaine) || [];
      return section("croissance.section.regularite", "regularite", [
        el("div", { class: "dzCroiSemaine" }, sem.map(function (j) {
          var a = { class: "dzCroiJour", title: String(j.jour), texte: String(j.jour).slice(8, 10) };
          if (j.posts > 0) a["data-posts"] = String(j.posts);
          return el("div", a);
        })),
        el("p", { class: "dzCroiNote", "data-dz-croissance": "regularite-texte",
          texte: T("croissance.regularite.jours", { n: g ? g.jours_avec_post : 0, total: g ? g.jours : 0 }) + " · " + T("croissance.regularite.serie", { n: g ? g.serie : 0 }) }),
      ]);
    }

    function ligne(p) {
      var c = p.croissance || {};
      var mult = el("span", { class: "dzCroiMult", "data-dz-croissance": "multiplicateur" });
      if (typeof c.multiplicateur === "number") {
        mult.textContent = fois(c.multiplicateur);
        mult.setAttribute("title", T("croissance.post.habituel", { n: nombre(c.habituel), jalon: c.jalon }));
        if (c.gagnant) mult.setAttribute("data-gagnant", "1");
      } else {
        mult.textContent = RAISONS.indexOf(c.raison) >= 0 ? T("croissance.raison." + c.raison, { n: c.recul || 0 }) : "—";
      }
      var jal = c.jalons || {};
      var detail = [T("croissance.post.vues", { n: nombre(p.views), canal: String(p.channel || "") })];
      var lus = JALONS.filter(function (k) { return typeof jal[k] === "number"; })
        .map(function (k) { return T("croissance.jalon." + k, { n: nombre(jal[k]) }); });
      if (lus.length) detail.push(lus.join(" · "));
      if (typeof c.visionnage_s === "number") detail.push(T("croissance.post.visionnage", { n: nombre(c.visionnage_s) }));
      return el("li", { class: "dzCroiPost", "data-dz-croissance": "post" }, [
        el("strong", { texte: String(p.title || "") }), mult, el("div", { class: "dzCroiDetail", texte: detail.join(" — ") })]);
    }

    function dessiner(d) {
      vider(corps);
      corps.appendChild(compte(d.compte));
      var t = d.totaux || {};
      corps.appendChild(section("croissance.section.posts", "posts", [el("div", { class: "dzCroiTuiles" },
        TUILES_POSTS.map(function (k) { return tuile("croissance.posts." + k, nombre(t[k]), "posts-" + k); }))]));
      corps.appendChild(regularite(d.regularite));
      var gagn = d.gagnants || [];
      corps.appendChild(section("croissance.section.gagnants", "gagnants", gagn.length
        ? [el("ul", { class: "dzCroiPosts" }, gagn.map(ligne))]
        : [el("p", { class: "dzCroiVide", texte: T("croissance.vide.gagnants", { n: nombre(d.seuil_gagnant) }) })]));
      var top = d.top || [];
      corps.appendChild(section("croissance.section.top", "top", top.length
        ? [el("ul", { class: "dzCroiPosts" }, top.map(ligne)), el("p", { class: "dzCroiNote", texte: T("croissance.top.note") })]
        : [el("p", { class: "dzCroiVide", texte: T("croissance.vide.top") })]));
    }

    lireEspaces();
    recharger();
    return {
      demonter: function () { vivant = false; if (racine.parentNode) racine.parentNode.removeChild(racine); },
      recharger: recharger,
    };
  }

  window.DzCroissance = { monter: monter };
})();
