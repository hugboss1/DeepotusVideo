/* dz-ig-commentaires.js — « Commentaires au mot-clé » de l'écran Croissance (t501, lot G11, 26/11/2026). SOURCE :
   frontend/shared/dz-ig-commentaires.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-ig-commentaires.js, chargée
   par frontend/dist/index.html AVANT dz-croissance.js, qui le monte dans sa section « commentaires ». Banc
   backend/tests/test_instagram_commentaires_t501.py.

   window.DzIgCommentaires.monter(el, {espace}) -> { demonter(), recharger() }

   Le contrat du serveur (/api/instagram/commentaires) :
   - GET  /file?espace_id=                                  {disponible, scope, reponses_jour, plafond_jour, posts}
   - PUT  /posts/{id}/mot-cle                               {mot_cle}
   - POST /posts/{id}/relever                               lit les commentaires et compte ceux au mot-clé
   - POST /posts/{id}/brouillons/gabarit                    brouillons gratuits
   - GET  /posts/{id}/brouillons/devis   puis   POST /posts/{id}/brouillons/claude {max_usd}   (Claude, sur devis)
   - POST /posts/{id}/brouillons/{b}/valider {texte}  |  /rejeter  |  /envoyer {texte, confirme: true}
   Réponse PUBLIQUE seulement : aucun message privé, aucun envoi groupé ; chaque envoi vise UN brouillon validé et
   passe par une confirmation (__dzDialogue ; sans dialogue, rien ne part). Tout texte venu du serveur (titres,
   commentaires, brouillons) est posé en textContent ou en value. Libellés : dzT (igcomm.objet.role). */
(function () {
  "use strict";
  if (window.DzIgCommentaires) return;

  var BASE = "/api/instagram/commentaires";
  var JSON_H = { "Content-Type": "application/json" };
  var STATUTS = { a_valider: "igcomm.statut.a_valider", valide: "igcomm.statut.valide" };
  var SOURCES = { gabarit: "igcomm.source.gabarit", claude: "igcomm.source.claude" };

  function T(cle, vars) { return typeof window.dzT === "function" ? window.dzT(cle, vars) : cle; }
  function el(tag, attrs, enfants) {
    var n = document.createElement(tag);
    var a = attrs || {};
    for (var k in a) {
      if (k === "texte") n.textContent = a[k];
      else if (k === "valeur") n.value = a[k];
      else if (k === "on") for (var e in a.on) n.addEventListener(e, a.on[e]);
      else n.setAttribute(k, a[k]);
    }
    (enfants || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }
  function vider(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function usd(v) { return (typeof v === "number" && isFinite(v) ? v : 0).toFixed(4); }

  var CSS = ""
    + ".dzIgc{display:flex;flex-direction:column;gap:8px}"
    + ".dzIgc ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px}"
    + ".dzIgcPost{border:1px solid var(--stroke,#2a2930);border-radius:var(--r);padding:6px 8px;display:flex;flex-direction:column;gap:6px}"
    + ".dzIgcPost strong{color:var(--ink-strong,#f2efe9);font-weight:600}"
    + ".dzIgcLigne{display:flex;flex-wrap:wrap;gap:6px;align-items:center}"
    + ".dzIgc input,.dzIgc textarea{background:var(--bg-panel-2,#1c1c21);color:var(--ink-strong,#f2efe9);border:1px solid var(--stroke,#2a2930);border-radius:var(--r);padding:3px 6px;font:inherit}"
    + ".dzIgc textarea{width:100%;min-height:44px;box-sizing:border-box;resize:vertical}"
    + ".dzIgcNote{font-size:11px;color:var(--ink-soft,#8a857d);margin:0}"
    + ".dzIgcNote[data-erreur]{color:var(--red,#e35d4a)}"
    + ".dzIgcExtrait{margin:0;padding:2px 8px;border-left:2px solid var(--stroke,#2a2930);color:var(--ink-soft,#8a857d);font-size:12px}"
    + ".dzIgcBrouillon{border-top:1px dashed var(--stroke,#2a2930);padding-top:6px;display:flex;flex-direction:column;gap:4px}"
    + ".dzIgcBrouillon[data-statut=valide]{border-top-color:var(--accent,#f0b429)}";
  function poserCss() {
    if (document.getElementById && document.getElementById("dzIgcCss")) return;
    var s = el("style", { id: "dzIgcCss" });
    s.textContent = CSS;
    (document.head || document.documentElement).appendChild(s);
  }

  async function lireJson(R) { try { return await R.json(); } catch (e) { return null; } }
  function detail(j, status) {
    var d = j && j.detail;
    if (typeof d === "string" && d) return d;
    if (d && typeof d.message === "string") return d.message;
    if (d && d.dz_plafond && d.dz_plafond.message) return String(d.dz_plafond.message);
    return "HTTP " + status;
  }
  async function appel(methode, chemin, corps) {
    var init = { method: methode, headers: JSON_H };
    if (corps !== undefined) init.body = JSON.stringify(corps);
    var R = await window.fetch(BASE + chemin, init);
    return { R: R, j: await lireJson(R) };
  }
  function confirmer(msg) {
    var d = window.__dzDialogue;
    if (!d || typeof d.confirmer !== "function") return Promise.resolve(false);
    return d.confirmer(msg, { danger: false });
  }

  function monter(hote, opts) {
    poserCss();
    var vivant = true, occupe = false, espace = (opts && opts.espace) || "";
    var racine = el("div", { class: "dzIgc", "data-dz-igcomm": "racine" });
    var etat = el("p", { class: "dzIgcNote", "data-dz-igcomm": "etat", role: "status" });
    var liste = el("ul", { "data-dz-igcomm": "posts" });
    racine.appendChild(etat);
    racine.appendChild(liste);
    hote.appendChild(racine);

    function dire(texte, erreur) {
      etat.textContent = texte || "";
      if (erreur) etat.setAttribute("data-erreur", "1"); else etat.removeAttribute("data-erreur");
    }
    async function geste(fn) {
      if (occupe) return;
      occupe = true;
      try {
        var r = await fn();
        if (!vivant) return;
        if (r && r.R && !r.R.ok) { dire(T("igcomm.etat.erreur", { msg: detail(r.j, r.R.status) }), true); return; }
        await recharger();
      } catch (e) {
        if (vivant) dire(T("igcomm.etat.erreur", { msg: String((e && e.message) || e) }), true);
      } finally { occupe = false; }
    }

    function brouillon(pid, b) {
      var zone = el("textarea", { "data-dz-igcomm": "texte", "aria-label": T("igcomm.brouillon.texte"), valeur: String(b.texte || "") });
      var boutons = [];
      if (b.statut === "a_valider" || b.statut === "valide") {
        boutons.push(el("button", { type: "button", "data-dz-igcomm": "valider", texte: T("igcomm.bouton.valider"),
          on: { click: function () { geste(function () { return appel("POST", "/posts/" + encodeURIComponent(pid) + "/brouillons/" + b.id + "/valider", { texte: zone.value }); }); } } }));
        boutons.push(el("button", { type: "button", "data-dz-igcomm": "rejeter", texte: T("igcomm.bouton.rejeter"),
          on: { click: function () { geste(function () { return appel("POST", "/posts/" + encodeURIComponent(pid) + "/brouillons/" + b.id + "/rejeter"); }); } } }));
      }
      if (b.statut === "valide") {
        boutons.push(el("button", { type: "button", "data-dz-igcomm": "envoyer", texte: T("igcomm.bouton.envoyer"),
          title: T("igcomm.bouton.envoyer_aide"), on: { click: function () {
            geste(async function () {
              var texte = String(b.texte_valide || "");
              if (!(await confirmer(T("igcomm.envoi.confirmer", { texte: texte })))) return null;
              return appel("POST", "/posts/" + encodeURIComponent(pid) + "/brouillons/" + b.id + "/envoyer", { texte: texte, confirme: true });
            });
          } } }));
      }
      var enfants = [
        el("blockquote", { class: "dzIgcExtrait", "data-dz-igcomm": "extrait", texte: String(b.extrait || "") }),
        zone,
        el("p", { class: "dzIgcNote", texte: T(STATUTS[b.statut] || STATUTS.a_valider) + (SOURCES[b.source] ? " · " + T(SOURCES[b.source]) : "") }),
      ];
      if (b.fautifs && b.fautifs.length) {
        enfants.push(el("p", { class: "dzIgcNote", "data-erreur": "1", "data-dz-igcomm": "fautifs", texte: T("igcomm.brouillon.fautifs", { mots: b.fautifs.join(", ") }) }));
      }
      enfants.push(el("div", { class: "dzIgcLigne" }, boutons));
      return el("div", { class: "dzIgcBrouillon", "data-dz-igcomm": "brouillon", "data-statut": String(b.statut || "") }, enfants);
    }

    async function claude(pid) {
      var d = await appel("GET", "/posts/" + encodeURIComponent(pid) + "/brouillons/devis");
      if (!d.R.ok) return d;
      if (!d.j || !d.j.disponible) { dire(T("igcomm.etat.claude_indispo"), true); return null; }
      if (!(await confirmer(T("igcomm.claude.confirmer", { usd: usd(d.j.usd), n: d.j.n })))) return null;
      return appel("POST", "/posts/" + encodeURIComponent(pid) + "/brouillons/claude", { max_usd: d.j.usd });
    }

    function post(p) {
      var pid = String(p.post_id);
      var mot = el("input", { type: "text", maxlength: "40", "data-dz-igcomm": "mot", "aria-label": T("igcomm.mot.libelle"),
        placeholder: T("igcomm.mot.exemple"), valeur: String(p.mot_cle || "") });
      var brs = (p.brouillons || []).filter(function (b) { return b.statut === "a_valider" || b.statut === "valide"; });
      var attente = (p.brouillons || []).filter(function (b) { return b.statut === "a_rediger"; }).length;
      var envoyes = (p.brouillons || []).filter(function (b) { return b.statut === "envoye"; }).length;
      var compte = typeof p.au_mot_cle === "number"
        ? T("igcomm.compteur.texte", { n: p.au_mot_cle, lus: p.lus || 0, date: String(p.releve_le || "").slice(0, 16).replace("T", " ") })
        : T("igcomm.compteur.jamais");
      return el("li", { class: "dzIgcPost", "data-dz-igcomm": "post" }, [
        el("strong", { texte: String(p.title || "") }),
        el("div", { class: "dzIgcLigne" }, [mot,
          el("button", { type: "button", "data-dz-igcomm": "poser-mot", texte: T("igcomm.bouton.mot"),
            on: { click: function () { geste(function () { return appel("PUT", "/posts/" + encodeURIComponent(pid) + "/mot-cle", { mot_cle: mot.value }); }); } } }),
          el("button", { type: "button", "data-dz-igcomm": "relever", texte: T("igcomm.bouton.relever"),
            on: { click: function () { geste(function () { return appel("POST", "/posts/" + encodeURIComponent(pid) + "/relever"); }); } } })]),
        el("p", { class: "dzIgcNote", "data-dz-igcomm": "compteur", texte: compte + " · " + T("igcomm.compteur.suivi", { attente: attente, envoyes: envoyes }) }),
        attente ? el("div", { class: "dzIgcLigne" }, [
          el("button", { type: "button", "data-dz-igcomm": "gabarit", texte: T("igcomm.bouton.gabarit"), title: T("igcomm.bouton.gabarit_aide"),
            on: { click: function () { geste(function () { return appel("POST", "/posts/" + encodeURIComponent(pid) + "/brouillons/gabarit", {}); }); } } }),
          el("button", { type: "button", "data-dz-igcomm": "claude", texte: T("igcomm.bouton.claude"), title: T("igcomm.bouton.claude_aide"),
            on: { click: function () { geste(function () { return claude(pid); }); } } })]) : null,
      ].concat(brs.map(function (b) { return brouillon(pid, b); })));
    }

    async function recharger() {
      var r = null;
      try { r = await appel("GET", "/file" + (espace ? "?espace_id=" + encodeURIComponent(espace) : "")); } catch (e) { r = null; }
      if (!vivant) return;
      vider(liste);
      if (!r || !r.R.ok || !r.j) { dire(T("igcomm.etat.lecture_erreur"), true); return; }
      var d = r.j;
      dire(d.disponible ? T("igcomm.etat.pret", { n: d.reponses_jour || 0, max: d.plafond_jour || 0 })
                        : T("igcomm.etat.sans_jeton", { scope: String(d.scope || "") }), !d.disponible);
      var posts = d.posts || [];
      if (!posts.length) { liste.appendChild(el("li", { class: "dzIgcNote", texte: T("igcomm.vide.posts") })); return; }
      posts.forEach(function (p) { liste.appendChild(post(p)); });
    }

    recharger();
    return {
      demonter: function () { vivant = false; if (racine.parentNode) racine.parentNode.removeChild(racine); },
      recharger: recharger,
    };
  }

  window.DzIgCommentaires = { monter: monter };
})();
