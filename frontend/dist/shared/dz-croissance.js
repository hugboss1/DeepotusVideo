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
   t495 (G5, 26/11/2026) — la section « Gagnants de ma niche » (services/croissance_gagnants.py) :
   - GET  /api/croissance/gagnants?espace_id=             le fil des gagnants des fils suivis de la niche (aucun relevé)
   - GET  /api/croissance/niche?espace_id=  / PUT /api/croissance/niche {espace_id, fils}   choisir les fils de la niche
   - POST /api/croissance/enregistres {espace_id, item_id}                                  enregistrer (métadonnées)
   - POST /api/croissance/gagnants/<id>/devis {espace_id, transcription}                    le devis GRATUIT
   - POST /api/croissance/gagnants/<id>/analyse {espace_id, max_usd, transcription}         « pourquoi ça marche »
     (PAYANT : seulement après le clic sur le bouton qui affiche le montant du devis, max_usd = ce montant)
   Aucun bouton ne diffuse quoi que ce soit. Tout texte venu du serveur (titres, noms, légendes, raisons) est posé en textContent. Les
   libellés viennent de dzT (zone.objet.role).
   t500 (G10, 26/11/2026) — « Mes posts X » (services/croissance_x.py ; l'API X est PAYANTE à l'usage) :
   - GET  /api/croissance/x/devis                          les posts X dus à leur jalon et le coût (gratuit)
   - POST /api/croissance/x/releve {max_usd}               le relevé, au montant affiché sur le bouton (PAYANT)
   - PUT  /api/croissance/x/accord {auto, plafond_usd}     l'accord du relevé automatique et le plafond X du mois
   Les cartes « fil X » et « post vidéo X » du recyclage disent ce que coûtera la mise en ligne sur X.
   t498 (lot G8, 26/11/2026) — « Recycler ce gagnant » sur chaque ligne gagnante :
   - GET  /api/recyclage/{id}/proposition                  quatre cartes de devis (carrousel, accroches, fil X, branche)
   - POST /api/recyclage/{id}/redaction  {element, max_usd} l'appel Claude d'UNE carte, au montant affiché et accepté
   - POST /api/recyclage/{id}/brouillons {elements}         les brouillons au Planificateur (jamais en mode automatique)
   Aucun bouton ne publie ; seule l'acceptation d'une carte dépense, à son montant. Tout texte venu du serveur (titres, noms) est posé en
   textContent. Les libellés viennent de dzT (zone.objet.role). Vanilla DOM, aucune dépendance. */
(function () {
  "use strict";
  if (window.DzCroissance) return;

  var PERIODES = [7, 30, 90];
  var RAISONS = ["trop_tot", "peu_de_recul", "sans_releve"];
  var TUILES_COMPTE = ["views", "reach", "followers", "follows", "interactions", "non_abonnes_pct"];
  var TUILES_POSTS = ["posts", "views", "engagement"];
  var JALONS = ["j1", "j3", "j7", "j30"];
  var GRILLE = ["accroche", "ennemi", "chiffre", "promesse", "appel"];
  var MESURES = ["vues", "interactions"];
  var CLES_MESURE = {
    vues: { habituel: "croissance.niche.habituel_vues", valeur: "croissance.niche.valeur_vues" },
    interactions: { habituel: "croissance.niche.habituel_interactions", valeur: "croissance.niche.valeur_interactions" },
  };
  var ELEMENTS_RECYCLAGE = ["carrousel", "accroches", "fil_x", "branche", "x_video"];   // t498 : recyclage.ELEMENTS
  var RAISONS_RECYCLAGE = ["cle", "sans_plans", "sans_gabarit"];

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
    + ".dzCroiVide{color:var(--ink-soft,#8a857d);margin:0}"
    + ".dzCroiActions{grid-column:1 / -1;display:flex;flex-wrap:wrap;gap:6px;align-items:center}"
    + ".dzCroi a{color:var(--accent,#f0b429)}"
    + ".dzCroi textarea{width:100%;box-sizing:border-box;min-height:52px;background:var(--bg-panel-2,#1c1c21);color:var(--ink-strong,#f2efe9);border:1px solid var(--stroke,#2a2930);border-radius:var(--r);font:inherit;padding:4px 6px}"
    + ".dzCroiAnalyse{grid-column:1 / -1;display:flex;flex-direction:column;gap:4px;border-top:1px solid var(--stroke,#2a2930);padding-top:6px}"
    + ".dzCroiRaisons{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:3px}"
    + ".dzCroiRaison{font-size:12px}.dzCroiRaison b{color:var(--ink-strong,#f2efe9)}"
    + ".dzCroiRaison[data-principale]{border-left:2px solid var(--accent,#f0b429);padding-left:6px}"
    + ".dzCroiRaison[data-absent]{color:var(--ink-soft,#8a857d)}"
    + ".dzCroiFils{display:flex;flex-direction:column;gap:2px;margin:4px 0}"
    + ".dzCroiFils label{display:flex;gap:6px;align-items:center}"
    + ".dzCroiRecyBtn,.dzCroiRecy{grid-column:1 / -1;justify-self:start}.dzCroiRecy{justify-self:stretch}"
    + ".dzCroiRecy .dzCroiNote[data-erreur]{color:var(--red,#e35d4a)}"
    + ".dzCroiCartes{list-style:none;margin:4px 0;padding:0;display:flex;flex-direction:column;gap:4px}"
    + ".dzCroiCarte{border:1px solid var(--stroke,#2a2930);border-radius:var(--r);padding:4px 8px;display:grid;grid-template-columns:1fr auto;gap:2px 8px}"
    + ".dzCroiCarte button{grid-column:1 / -1;justify-self:start}";
  function poserCss() {
    if (document.getElementById && document.getElementById("dzCroiCss")) return;
    var s = el("style", { id: "dzCroiCss" });
    s.textContent = CSS;
    (document.head || document.documentElement).appendChild(s);
  }

  async function lireJson(r) { try { return await r.json(); } catch (e) { return {}; } }

  function monter(hote) {
    poserCss();
    var vivant = true, jours = 30, espace = "", tour = 0, igc = null;
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
      rechargerNiche();
      rechargerX();
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
      rechargerAlertes();   // t504 : après le tableau (G12)
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
      var enfants = [el("strong", { texte: String(p.title || "") }), mult, el("div", { class: "dzCroiDetail", texte: detail.join(" — ") })];
      if (c.gagnant && p.id) {                       // t498 : recycler ce gagnant (proposition gratuite, devis par carte)
        var zone = el("div", { class: "dzCroiRecy", "data-dz-croissance": "recyclage" });
        var br = el("button", { type: "button", class: "dzCroiRecyBtn", "data-dz-croissance": "recycler",
          texte: T("croissance.recyclage.bouton"), title: T("croissance.recyclage.bouton_aide") });
        br.addEventListener("click", function () { recycler(p, zone, br); });
        enfants.push(br, zone);
      }
      return el("li", { class: "dzCroiPost", "data-dz-croissance": "post" }, enfants);
    }

    // ---- t498 : recycler un gagnant ----------------------------------------------------------------------------------
    function dollarsRecy(v) {
      var n = typeof v === "number" && isFinite(v) ? v : 0;
      return n.toLocaleString(langue() === "en" ? "en-US" : "fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: n > 0 && n < 0.01 ? 4 : 2 }) + " $";
    }
    async function messageDe(r) {
      var j = await lireJson(r), d = j && j.detail;
      if (typeof d === "string") return d;
      return d && typeof d.message === "string" ? d.message : T("croissance.recyclage.erreur");
    }
    function recycler(p, zone, bouton) {
      var base = "/api/recyclage/" + encodeURIComponent(String(p.id));
      var redige = {};
      vider(zone);
      var etatR = el("p", { class: "dzCroiNote", "data-dz-croissance": "recyclage-etat", role: "status" });
      zone.appendChild(etatR);
      function direR(t, err) {
        etatR.textContent = t || "";
        if (err) etatR.setAttribute("data-erreur", "1"); else etatR.removeAttribute("data-erreur");
      }
      var envoi = { "Content-Type": "application/json" };
      var btnB = el("button", { type: "button", "data-dz-croissance": "recyclage-brouillons", texte: T("croissance.recyclage.brouillons") });

      async function accepter(elt, usd, b) {
        b.setAttribute("disabled", "");
        direR(T("croissance.recyclage.redaction"));
        var bon = false, msg = "";
        try {
          var r = await window.fetch(base + "/redaction", { method: "POST", headers: envoi,
            body: JSON.stringify({ element: elt, max_usd: usd, langue: langue() }) });
          if (r.ok) {
            var j = await lireJson(r);
            bon = true;
            if (Array.isArray(j.interdits) && j.interdits.length) msg = T("croissance.recyclage.interdits", { mots: j.interdits.join(", ") });
          } else msg = await messageDe(r);
        } catch (e) { msg = T("croissance.recyclage.erreur"); }
        if (!vivant) return;
        if (!bon) { b.removeAttribute("disabled"); direR(msg, true); return; }
        redige[elt] = true;
        b.textContent = T("croissance.recyclage.redige");
        direR(msg || T("croissance.recyclage.pret"), !!msg);
      }

      function carte(c) {
        var a = c.arguments || {}, t = a.texte || {}, elt = String(a.element || "");
        var li = el("li", { class: "dzCroiCarte", "data-dz-croissance": "recyclage-carte", "data-element": elt }, [
          el("strong", { texte: ELEMENTS_RECYCLAGE.indexOf(elt) >= 0 ? T("croissance.recyclage." + elt) : elt }),
          el("span", { class: "dzCroiMult", texte: dollarsRecy(c.devis) })]);
        var note = "";
        if (!t.disponible) note = RAISONS_RECYCLAGE.indexOf(t.raison) >= 0 ? T("croissance.raison_recyclage." + t.raison) : "—";
        else if (elt === "branche") note = T("croissance.recyclage.branche_note");
        if (note) li.appendChild(el("div", { class: "dzCroiDetail", texte: note }));
        var pub = a.publication;                       // t500 : la mise en ligne sur X a son prix (lien plus cher)
        if (pub && typeof pub.usd_max === "number") {
          li.appendChild(el("div", { class: "dzCroiDetail", "data-dz-croissance": "recyclage-publication-x",
            texte: T("croissance.recyclage.publication_x", { usd: dollarsX(pub.usd_max), post: dollarsX(pub.usd_post),
              lien: dollarsX(pub.usd_post_lien) }) }));
        }
        if (t.disponible) {
          var b = el("button", { type: "button", "data-dz-croissance": "recyclage-accepter",
            texte: a.redige ? T("croissance.recyclage.redige") : T("croissance.recyclage.accepter", { usd: dollarsRecy(t.usd) }) });
          if (a.redige) { redige[elt] = true; b.setAttribute("disabled", ""); }
          b.addEventListener("click", function () { accepter(elt, t.usd, b); });
          li.appendChild(b);
        }
        return li;
      }

      async function brouillons() {
        var els = ELEMENTS_RECYCLAGE.filter(function (e) { return redige[e]; });
        if (!els.length) { direR(T("croissance.recyclage.rien"), true); return; }
        btnB.setAttribute("disabled", "");
        direR(T("croissance.recyclage.creation"));
        var j = null, msg = "";
        try {
          var r = await window.fetch(base + "/brouillons", { method: "POST", headers: envoi, body: JSON.stringify({ elements: els }) });
          if (r.ok) j = await lireJson(r); else msg = await messageDe(r);
        } catch (e) { msg = T("croissance.recyclage.erreur"); }
        if (!vivant) return;
        btnB.removeAttribute("disabled");
        if (!j) { direR(msg || T("croissance.recyclage.erreur"), true); return; }
        var dit = T("croissance.recyclage.crees", { n: (j.brouillons || []).length });
        if ((j.non_crees || []).length) dit += " " + T("croissance.recyclage.branche_montage");
        direR(dit);
      }
      btnB.addEventListener("click", brouillons);

      (async function () {
        bouton.setAttribute("disabled", "");
        direR(T("croissance.recyclage.lecture"));
        var prop = null, msg = "";
        try {
          var r = await window.fetch(base + "/proposition");
          if (r.ok) prop = await lireJson(r); else msg = await messageDe(r);
        } catch (e) { msg = T("croissance.recyclage.erreur"); }
        if (!vivant) return;
        bouton.removeAttribute("disabled");
        if (!prop || !Array.isArray(prop.cartes)) { direR(msg || T("croissance.recyclage.erreur"), true); return; }
        direR(T("croissance.recyclage.aide"));
        zone.appendChild(el("ul", { class: "dzCroiCartes", "data-dz-croissance": "recyclage-cartes" }, prop.cartes.map(carte)));
        zone.appendChild(btnB);
      })();
    }

    // ---- t495 : « Gagnants de ma niche » -------------------------------------------------------------------------------
    var blocNiche = el("section", { "data-dz-croissance": "niche" });
    var tourNiche = 0, editeurOuvert = false;
    function avecEspace(url) { return url + (espace ? (url.indexOf("?") >= 0 ? "&" : "?") + "espace_id=" + encodeURIComponent(espace) : ""); }
    function corpsJson(c) {
      var o = {};
      for (var k in c) o[k] = c[k];
      if (espace) o.espace_id = espace;
      return JSON.stringify(o);
    }
    function envoyer(url, methode, c) {
      return window.fetch(url, { method: methode, headers: { "Content-Type": "application/json" }, body: corpsJson(c || {}) });
    }
    function dollars(v) {
      var loc = langue() === "en" ? "en-US" : "fr-FR";
      return (typeof v === "number" && isFinite(v) ? v : 0).toLocaleString(loc, { minimumFractionDigits: 2, maximumFractionDigits: 4 });
    }
    function lien(url) {
      if (typeof url !== "string" || url.indexOf("https://") !== 0) return null;
      return el("a", { href: url, target: "_blank", rel: "noopener noreferrer", "data-dz-croissance": "niche-lien", texte: T("croissance.niche.ouvrir") });
    }

    async function rechargerNiche() {
      var moi = ++tourNiche;
      var d = null;
      try {
        var r = await window.fetch(avecEspace("/api/croissance/gagnants"));
        if (r.ok) d = await lireJson(r);
      } catch (e) { d = null; }
      if (!vivant || moi !== tourNiche) return;
      dessinerNiche(d);
    }

    function dessinerNiche(d) {
      vider(blocNiche);
      blocNiche.appendChild(el("h3", { texte: T("croissance.section.niche") }));
      var btnChoisir = el("button", { type: "button", "data-dz-croissance": "niche-choisir", texte: T("croissance.niche.choisir"),
        on: { click: function () { editeurOuvert = !editeurOuvert; if (editeurOuvert) ouvrirEditeur(editeur); else vider(editeur); } } });
      var editeur = el("div", { "data-dz-croissance": "niche-editeur" });
      if (!d || !Array.isArray(d.gagnants)) {
        blocNiche.appendChild(el("p", { class: "dzCroiVide", "data-dz-croissance": "niche-etat", texte: T("croissance.niche.erreur") }));
        return;
      }
      blocNiche.appendChild(el("p", { class: "dzCroiNote", texte: T("croissance.niche.note", { n: nombre(d.seuil), j: d.jours }) }));
      blocNiche.appendChild(el("div", { class: "dzCroiActions" }, [btnChoisir]));
      blocNiche.appendChild(editeur);
      if (editeurOuvert) ouvrirEditeur(editeur);
      if (!(d.niche || []).length) {
        blocNiche.appendChild(el("p", { class: "dzCroiVide", "data-dz-croissance": "niche-etat", texte: T("croissance.niche.sans_fils") }));
        return;
      }
      if (!d.gagnants.length) {
        blocNiche.appendChild(el("p", { class: "dzCroiVide", "data-dz-croissance": "niche-etat",
          texte: T("croissance.niche.aucun", { n: nombre(d.seuil), j: d.jours, f: d.niche.length }) }));
        return;
      }
      blocNiche.appendChild(el("ul", { class: "dzCroiPosts" }, d.gagnants.map(ligneGagnant)));
    }

    async function ouvrirEditeur(hoteEd) {
      vider(hoteEd);
      var j = null;
      try {
        var r = await window.fetch(avecEspace("/api/croissance/niche"));
        if (r.ok) j = await lireJson(r);
      } catch (e) { j = null; }
      if (!vivant || !editeurOuvert) return;
      vider(hoteEd);
      if (!j || !Array.isArray(j.fils)) { hoteEd.appendChild(el("p", { class: "dzCroiVide", texte: T("croissance.niche.erreur") })); return; }
      if (!j.fils.length) { hoteEd.appendChild(el("p", { class: "dzCroiVide", "data-dz-croissance": "niche-aucun-fil", texte: T("croissance.niche.aucun_fil") })); return; }
      var cases = j.fils.map(function (f) {
        var c = el("input", { type: "checkbox", "data-dz-croissance": "niche-fil", "data-id": String(f.id) });
        c.checked = !!f.dans_niche;
        return { id: f.id, c: c, l: el("label", {}, [c, el("span", { texte: String(f.nom || f.identifiant || f.id) + " · " + String(f.plateforme || "") })]) };
      });
      var etatEd = el("span", { class: "dzCroiNote", role: "status" });
      var btn = el("button", { type: "button", "data-dz-croissance": "niche-poser", texte: T("croissance.niche.poser"), on: { click: async function () {
        btn.setAttribute("disabled", "");
        var bon = false;
        try {
          bon = (await envoyer("/api/croissance/niche", "PUT", { fils: cases.filter(function (x) { return x.c.checked; }).map(function (x) { return x.id; }) })).ok;
        } catch (e) { bon = false; }
        if (!vivant) return;
        btn.removeAttribute("disabled");
        if (!bon) { etatEd.textContent = T("croissance.niche.poser_erreur"); return; }
        editeurOuvert = false;
        rechargerNiche();
      } } });
      hoteEd.appendChild(el("div", { class: "dzCroiFils" }, cases.map(function (x) { return x.l; })));
      hoteEd.appendChild(el("div", { class: "dzCroiActions" }, [btn, etatEd]));
    }

    function ligneGagnant(g) {
      var mult = el("span", { class: "dzCroiMult", "data-dz-croissance": "multiplicateur", "data-gagnant": "1", texte: fois(g.multiplicateur) });
      var mes = MESURES.indexOf(g.mesure) >= 0 ? g.mesure : "vues";
      mult.setAttribute("title", T(CLES_MESURE[mes].habituel, { n: nombre(g.habituel) }));
      var detail = [String(g.source_name || g.plateforme || ""), T(CLES_MESURE[mes].valeur, { n: nombre(g.valeur) })];
      var etatL = el("span", { class: "dzCroiNote", role: "status" });
      var btnEnr = el("button", { type: "button", "data-dz-croissance": "niche-enregistrer",
        texte: T(g.enregistre ? "croissance.niche.enregistre" : "croissance.niche.enregistrer") });
      if (g.enregistre) btnEnr.setAttribute("disabled", "");
      btnEnr.addEventListener("click", async function () {
        btnEnr.setAttribute("disabled", "");
        var bon = false;
        try { bon = (await envoyer("/api/croissance/enregistres", "POST", { item_id: g.id })).ok; } catch (e) { bon = false; }
        if (!vivant) return;
        if (bon) { btnEnr.textContent = T("croissance.niche.enregistre"); return; }
        btnEnr.removeAttribute("disabled");
        etatL.textContent = T("croissance.niche.enregistrer_erreur");
      });
      var zone = el("div", { class: "dzCroiAnalyse", "data-dz-croissance": "analyse" });
      var btnPourquoi = el("button", { type: "button", "data-dz-croissance": "niche-pourquoi", texte: T("croissance.analyse.pourquoi"),
        on: { click: function () { if (g.analyse) dessinerAnalyse(zone, g.analyse); else preparerAnalyse(zone, g); } } });
      return el("li", { class: "dzCroiPost", "data-dz-croissance": "niche-gagnant" }, [
        el("strong", { texte: String(g.title || "") }), mult,
        el("div", { class: "dzCroiDetail", texte: detail.join(" — ") }),
        el("div", { class: "dzCroiActions" }, [btnEnr, btnPourquoi, lien(g.link), etatL]), zone]);
    }

    function preparerAnalyse(zone, g) {
      vider(zone);
      var trans = el("textarea", { "data-dz-croissance": "analyse-transcription", "aria-label": T("croissance.analyse.transcription"),
        placeholder: T("croissance.analyse.transcription") });
      var etatA = el("span", { class: "dzCroiNote", role: "status", "data-dz-croissance": "analyse-etat" });
      var btnLancer = el("button", { type: "button", "data-dz-croissance": "analyse-lancer" });
      btnLancer.setAttribute("hidden", "");
      var devisUsd = null;
      var btnDevis = el("button", { type: "button", "data-dz-croissance": "analyse-devis", texte: T("croissance.analyse.devis"), on: { click: async function () {
        btnDevis.setAttribute("disabled", "");
        etatA.textContent = T("croissance.analyse.devis_lecture");
        var d = null;
        try {
          var r = await envoyer("/api/croissance/gagnants/" + encodeURIComponent(g.id) + "/devis", "POST", { transcription: trans.value || "" });
          if (r.ok) d = await lireJson(r);
        } catch (e) { d = null; }
        if (!vivant) return;
        btnDevis.removeAttribute("disabled");
        if (!d || typeof d.usd !== "number") { etatA.textContent = T("croissance.analyse.erreur"); return; }
        if (!d.disponible) { etatA.textContent = String(d.raison || "") || T("croissance.analyse.indisponible"); return; }
        devisUsd = d.usd;
        etatA.textContent = T("croissance.analyse.devis_note", { usd: dollars(d.usd), s: d.delai_s });
        btnLancer.textContent = T("croissance.analyse.lancer", { usd: dollars(d.usd) });
        btnLancer.removeAttribute("hidden");
      } } });
      btnLancer.addEventListener("click", async function () {
        if (typeof devisUsd !== "number") return;
        btnLancer.setAttribute("disabled", "");
        etatA.textContent = T("croissance.analyse.en_cours");
        var r = null, j = {};
        try {
          r = await envoyer("/api/croissance/gagnants/" + encodeURIComponent(g.id) + "/analyse", "POST", { max_usd: devisUsd, transcription: trans.value || "" });
          j = await lireJson(r);
        } catch (e) { r = null; }
        if (!vivant) return;
        btnLancer.removeAttribute("disabled");
        if (r && r.ok && Array.isArray(j.raisons)) { g.analyse = j; dessinerAnalyse(zone, j); return; }
        var det = (j && j.detail) || {};
        if (r && r.status === 409 && det.code === "cout" && typeof det.usd === "number") {
          devisUsd = det.usd;
          btnLancer.textContent = T("croissance.analyse.lancer", { usd: dollars(det.usd) });
          etatA.textContent = T("croissance.analyse.cout", { usd: dollars(det.usd) });
          return;
        }
        etatA.textContent = T(r && r.status === 402 ? "croissance.analyse.plafond" : "croissance.analyse.erreur");
      });
      zone.appendChild(trans);
      zone.appendChild(el("div", { class: "dzCroiActions" }, [btnDevis, btnLancer, etatA]));
    }

    function dessinerAnalyse(zone, a) {
      vider(zone);
      var princ = Array.isArray(a.principales) ? a.principales : [];
      zone.appendChild(el("ul", { class: "dzCroiRaisons", "data-dz-croissance": "raisons" }, (a.raisons || []).filter(function (x) {
        return x && GRILLE.indexOf(x.critere) >= 0;
      }).map(function (x) {
        var attrs = { class: "dzCroiRaison", "data-dz-croissance": "raison", "data-critere": x.critere };
        if (princ.indexOf(x.critere) >= 0) attrs["data-principale"] = "1";
        if (!x.present) attrs["data-absent"] = "1";
        var tete = T("croissance.grille." + x.critere) + (x.present ? " ✓" : " ✗");
        if (x.critere === "accroche" && typeof x.secondes === "number") tete += " · " + T("croissance.analyse.secondes", { n: nombre(x.secondes) });
        var corpsR = (x.alertes || []).indexOf("copie") >= 0 ? T("croissance.analyse.masquee") : String(x.explication || "");
        return el("li", attrs, [el("b", { texte: tete }), el("span", { texte: corpsR ? " — " + corpsR : "" })]);
      })));
      if (a.resume) zone.appendChild(el("p", { class: "dzCroiNote", "data-dz-croissance": "analyse-resume", texte: String(a.resume) }));
      zone.appendChild(el("p", { class: "dzCroiNote", texte: T("croissance.analyse.note", { usd: dollars(a.usd) }) }));
    }

    // ---- t500 : « Mes posts X » — relevé payant par jalon, sur accord, et le plafond X ---------------------------------
    var blocX = el("section", { "data-dz-croissance": "x" });
    var tourX = 0;
    function dollarsX(v) { return dollars(v) + " $"; }   // t500 : 0,015 $ reste 0,015 $
    async function rechargerX() {
      var moi = ++tourX, d = null;
      try { var r = await window.fetch("/api/croissance/x/devis"); if (r.ok) d = await lireJson(r); } catch (e) { d = null; }
      if (!vivant || moi !== tourX) return;
      dessinerX(d);
    }
    function dessinerX(d) {
      vider(blocX);
      blocX.appendChild(el("h3", { texte: T("croissance.section.x") }));
      var etatX = el("p", { class: "dzCroiNote", "data-dz-croissance": "x-etat", role: "status" });
      function direX(t, err) { etatX.textContent = t || ""; if (err) etatX.setAttribute("data-erreur", "1"); else etatX.removeAttribute("data-erreur"); }
      if (!d || typeof d.n !== "number") { direX(T("croissance.x.erreur"), true); blocX.appendChild(etatX); return; }
      var t = d.tarifs || {}, relu = d.relu || {};
      blocX.appendChild(el("p", { class: "dzCroiNote", "data-dz-croissance": "x-tarifs", texte: T("croissance.x.tarifs", {
        lecture: dollarsX(t.lecture), post: dollarsX(t.post), lien: dollarsX(t.post_lien), le: String(relu.le || "") }) }));
      var devisX = typeof d.usd === "number" ? d.usd : 0;
      blocX.appendChild(el("p", { "data-dz-croissance": "x-devis", texte: d.n ? T("croissance.x.devis", { n: d.n, usd: dollarsX(devisX) })
        : T("croissance.x.rien") }));
      if (d.n) {
        var btnX = el("button", { type: "button", "data-dz-croissance": "x-relever", texte: T("croissance.x.relever", { usd: dollarsX(devisX) }) });
        btnX.addEventListener("click", async function () {
          btnX.setAttribute("disabled", "");
          var r = null, j = null;
          try { r = await envoyer("/api/croissance/x/releve", "POST", { max_usd: devisX }); j = await lireJson(r); } catch (e) { r = null; }
          if (!vivant) return;
          btnX.removeAttribute("disabled");
          var det = j && j.detail;
          if (r && r.status === 409 && det && det.code === "cout" && typeof det.usd === "number") {
            devisX = det.usd;
            btnX.textContent = T("croissance.x.relever", { usd: dollarsX(devisX) });
            direX(T("croissance.x.cout", { usd: dollarsX(devisX) }), true);
            return;
          }
          if (!r || !r.ok) { direX(typeof det === "string" ? det : T("croissance.x.erreur"), true); return; }
          direX(T("croissance.x.releve_ok", { n: (j && j.releves) || 0 }));
          recharger();
        });
        blocX.appendChild(btnX);
      }
      var acc = d.accord || {};
      var caseAuto = el("input", { type: "checkbox", "data-dz-croissance": "x-auto" });
      caseAuto.checked = acc.auto === true;
      var plaf = el("input", { type: "number", min: "0", step: "0.5", "data-dz-croissance": "x-plafond",
        "aria-label": T("croissance.x.plafond"), value: String(acc.plafond_usd || 0) });
      var btnAcc = el("button", { type: "button", "data-dz-croissance": "x-accord", texte: T("croissance.x.accord") });
      btnAcc.addEventListener("click", async function () {
        var r = null;
        try { r = await envoyer("/api/croissance/x/accord", "PUT", { auto: caseAuto.checked === true, plafond_usd: parseFloat(plaf.value) || 0 }); } catch (e) { r = null; }
        if (!vivant) return;
        direX(r && r.ok ? T("croissance.x.accord_ok") : T("croissance.x.accord_erreur"), !(r && r.ok));
      });
      blocX.appendChild(el("div", { class: "dzCroiActions" }, [
        el("label", {}, [caseAuto, el("span", { texte: T("croissance.x.auto") })]),
        el("label", {}, [el("span", { texte: T("croissance.x.plafond") }), plaf]), btnAcc]));
      blocX.appendChild(etatX);
    }

    // ---- t504 (clôture G12) : l'ACCORD du bilan hebdo et de l'alerte « gagnant » WhatsApp ---------------------------
    // GET /api/schedule/croissance/alertes (état, et devis par message avec `numero`, gratuit), PUT (accord : modèle
    // utilitaire approuvé, montant accepté = le devis affiché), DELETE (retrait). Rien ne part sans la case d'accord.
    var blocAlertes = el("section", { "data-dz-croissance": "alertes" });
    var tourAl = 0;
    async function rechargerAlertes() {
      var moi = ++tourAl, d = null;
      try { var r = await window.fetch(avecEspace("/api/schedule/croissance/alertes")); if (r.ok) d = await lireJson(r); } catch (e) { d = null; }
      if (!vivant || moi !== tourAl) return;
      dessinerAlertes(d);
    }
    function dessinerAlertes(d) {
      vider(blocAlertes);
      blocAlertes.appendChild(el("h3", { texte: T("croissance.section.alertes") }));
      var etatA = el("p", { class: "dzCroiNote", "data-dz-croissance": "alertes-etat", role: "status" });
      function direA(t, err) { etatA.textContent = t || ""; if (err) etatA.setAttribute("data-erreur", "1"); else etatA.removeAttribute("data-erreur"); }
      if (!d || typeof d.alertes !== "object" || d.alertes === null) { direA(T("croissance.alertes.erreur"), true); blocAlertes.appendChild(etatA); return; }
      var a = d.alertes, actif = !!(a.accord && a.etat === "actif");
      blocAlertes.appendChild(el("p", { class: "dzCroiNote", texte: T("croissance.alertes.explication") }));
      blocAlertes.appendChild(el("p", { "data-dz-croissance": "alertes-statut", texte: actif
        ? T("croissance.alertes.actif", { le: String(a.accord.le || "").slice(0, 10), usd: dollars(a.accord.usd_par_message) + " $",
          quoi: [a.bilan ? T("croissance.alertes.bilan") : "", a.alerte ? T("croissance.alertes.alerte") : ""].filter(Boolean).join(" + ") })
        : T("croissance.alertes.inactif") }));
      if (!d.compte) { blocAlertes.appendChild(el("p", { class: "dzCroiVide", "data-dz-croissance": "alertes-sans-compte", texte: T("croissance.alertes.sans_compte") })); }
      var numero = el("input", { type: "tel", "data-dz-croissance": "alertes-numero", "aria-label": T("croissance.alertes.numero"),
        placeholder: T("croissance.alertes.numero_exemple"), value: String(a.destinataire || "").replace(/^tel:/, "") });
      var caseBilan = el("input", { type: "checkbox", "data-dz-croissance": "alertes-bilan" });
      var caseAlerte = el("input", { type: "checkbox", "data-dz-croissance": "alertes-alerte" });
      caseBilan.checked = actif ? a.bilan !== false : true;
      caseAlerte.checked = actif ? a.alerte !== false : true;
      var selModele = el("select", { "data-dz-croissance": "alertes-modele", "aria-label": T("croissance.alertes.modele") },
        [el("option", { value: "", texte: T("croissance.alertes.modele_aucun") })]);
      if (actif && a.modele && a.modele.nom) {
        selModele.appendChild(el("option", { value: a.modele.nom + "|" + a.modele.langue, texte: a.modele.nom + " (" + a.modele.langue + ")" }));
        selModele.value = a.modele.nom + "|" + a.modele.langue;
      }
      var btnModeles = el("button", { type: "button", "data-dz-croissance": "alertes-modeles", texte: T("croissance.alertes.lire_modeles") });
      var devisTxt = el("p", { "data-dz-croissance": "alertes-devis" });
      var btnDevis = el("button", { type: "button", "data-dz-croissance": "alertes-devis-bouton", texte: T("croissance.alertes.devis_bouton") });
      var caseAccord = el("input", { type: "checkbox", "data-dz-croissance": "alertes-accord-case" });
      var btnAccord = el("button", { type: "button", "data-dz-croissance": "alertes-accord", texte: T("croissance.alertes.accord") });
      btnAccord.setAttribute("disabled", "");
      var devisA = null;
      function majAccord() {
        if (devisA && devisA.disponible && caseAccord.checked && selModele.value && (caseBilan.checked || caseAlerte.checked)) btnAccord.removeAttribute("disabled");
        else btnAccord.setAttribute("disabled", "");
      }
      [caseAccord, caseBilan, caseAlerte, selModele].forEach(function (x) { x.addEventListener("change", majAccord); });
      numero.addEventListener("change", function () { devisA = null; devisTxt.textContent = ""; caseAccord.checked = false; majAccord(); });
      btnModeles.addEventListener("click", async function () {
        if (!d.compte) { direA(T("croissance.alertes.sans_compte"), true); return; }
        var r = null, j = null;
        try { r = await window.fetch("/api/whatsapp/" + encodeURIComponent(d.compte) + "/modeles"); j = await lireJson(r); } catch (e) { r = null; }
        if (!vivant) return;
        if (!r || !r.ok || !Array.isArray(j)) { direA(T("croissance.alertes.modeles_erreur"), true); return; }
        var bons = j.filter(function (m) { return m && String(m.categorie || "").toLowerCase() === "utility" && (m.n_parametres || 0) <= 1; });
        vider(selModele);
        selModele.appendChild(el("option", { value: "", texte: T("croissance.alertes.modele_aucun") }));
        bons.forEach(function (m) { selModele.appendChild(el("option", { value: m.nom + "|" + m.langue, texte: m.nom + " (" + m.langue + ")" })); });
        direA(bons.length ? T("croissance.alertes.modeles_lus", { n: bons.length }) : T("croissance.alertes.modeles_vide"), !bons.length);
        majAccord();
      });
      btnDevis.addEventListener("click", async function () {
        var r = null, j = null;
        try { r = await window.fetch(avecEspace("/api/schedule/croissance/alertes?numero=" + encodeURIComponent(numero.value || ""))); j = await lireJson(r); } catch (e) { r = null; }
        if (!vivant) return;
        if (!r || !r.ok) { direA(j && typeof j.detail === "string" ? j.detail : T("croissance.alertes.erreur"), true); return; }
        devisA = j.devis || null;
        caseAccord.checked = false;
        if (!devisA || !devisA.disponible) { devisTxt.textContent = T("croissance.alertes.devis_indispo"); majAccord(); return; }
        devisTxt.textContent = T("croissance.alertes.devis", { usd: dollars(devisA.usd_par_message) + " $", mois: dollars(devisA.par_mois_max) + " $" });
        direA("");
        majAccord();
      });
      btnAccord.addEventListener("click", async function () {
        if (!devisA || !caseAccord.checked) return;
        var p = String(selModele.value || "").split("|");
        btnAccord.setAttribute("disabled", "");
        var r = null, j = null;
        try {
          r = await envoyer("/api/schedule/croissance/alertes", "PUT", { numero: numero.value || "", modele: { nom: p[0] || "", langue: p[1] || "" },
            usd_accepte: devisA.usd_par_message, bilan: caseBilan.checked === true, alerte: caseAlerte.checked === true });
          j = await lireJson(r);
        } catch (e) { r = null; }
        if (!vivant) return;
        if (!r || !r.ok) { majAccord(); direA(j && typeof j.detail === "string" ? j.detail : T("croissance.alertes.erreur"), true); return; }
        rechargerAlertes();
      });
      blocAlertes.appendChild(el("div", { class: "dzCroiActions" }, [
        el("label", {}, [el("span", { texte: T("croissance.alertes.numero") }), numero]),
        el("label", {}, [caseBilan, el("span", { texte: T("croissance.alertes.bilan") })]),
        el("label", {}, [caseAlerte, el("span", { texte: T("croissance.alertes.alerte") })])]));
      blocAlertes.appendChild(el("div", { class: "dzCroiActions" }, [selModele, btnModeles, btnDevis]));
      blocAlertes.appendChild(devisTxt);
      blocAlertes.appendChild(el("div", { class: "dzCroiActions" }, [
        el("label", {}, [caseAccord, el("span", { texte: T("croissance.alertes.accord_case") })]), btnAccord]));
      if (actif) {
        var btnRetirer = el("button", { type: "button", "data-dz-croissance": "alertes-retirer", texte: T("croissance.alertes.retirer") });
        btnRetirer.addEventListener("click", async function () {
          var r = null;
          try { r = await window.fetch(avecEspace("/api/schedule/croissance/alertes"), { method: "DELETE" }); } catch (e) { r = null; }
          if (!vivant) return;
          if (!r || !r.ok) { direA(T("croissance.alertes.erreur"), true); return; }
          rechargerAlertes();
        });
        blocAlertes.appendChild(el("div", { class: "dzCroiActions" }, [btnRetirer]));
      }
      blocAlertes.appendChild(etatA);
    }

    function dessiner(d) {
      vider(corps);
      corps.appendChild(compte(d.compte));
      // t501 (G11) : les commentaires au mot-clé et la file des brouillons de réponse publique, montés par
      // dz-ig-commentaires.js (les gestes y vivent ; cet écran reste en lecture)
      if (igc) { igc.demonter(); igc = null; }
      if (window.DzIgCommentaires) {
        var hoteIgc = section("croissance.section.commentaires", "commentaires", []);
        corps.appendChild(hoteIgc);
        igc = window.DzIgCommentaires.monter(hoteIgc, { espace: espace });
      }
      var t = d.totaux || {};
      corps.appendChild(section("croissance.section.posts", "posts", [el("div", { class: "dzCroiTuiles" },
        TUILES_POSTS.map(function (k) { return tuile("croissance.posts." + k, nombre(t[k]), "posts-" + k); }))]));
      corps.appendChild(regularite(d.regularite));
      var gagn = d.gagnants || [];
      corps.appendChild(section("croissance.section.gagnants", "gagnants", gagn.length
        ? [el("ul", { class: "dzCroiPosts" }, gagn.map(ligne))]
        : [el("p", { class: "dzCroiVide", texte: T("croissance.vide.gagnants", { n: nombre(d.seuil_gagnant) }) })]));
      corps.appendChild(blocNiche);
      corps.appendChild(blocX);
      corps.appendChild(blocAlertes);   // t504 : accord du bilan et de l'alerte WhatsApp (G12)
      var top = d.top || [];
      corps.appendChild(section("croissance.section.top", "top", top.length
        ? [el("ul", { class: "dzCroiPosts" }, top.map(ligne)), el("p", { class: "dzCroiNote", texte: T("croissance.top.note") })]
        : [el("p", { class: "dzCroiVide", texte: T("croissance.vide.top") })]));
    }

    lireEspaces();
    recharger();
    return {
      demonter: function () { vivant = false; if (igc) igc.demonter(); if (racine.parentNode) racine.parentNode.removeChild(racine); },
      recharger: recharger,
    };
  }

  window.DzCroissance = { monter: monter };
})();
