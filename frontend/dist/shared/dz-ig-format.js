/* dz-ig-format.js — le FORMAT Instagram d'un post, dans l'éditeur de post du Planificateur (t494, lot G4, 09/11/2026,
   conception docs/superpowers/specs/2026-11-09-getripping-design.md). SOURCE : frontend/shared/dz-ig-format.js ; copie
   OCTET POUR OCTET : frontend/dist/shared/dz-ig-format.js, chargée par frontend/dist/index.html. Monté par le maillon
   scripts/patch_bundle_dzigformat.py quand le post vise le canal instagram. Bancs : backend/tests/test_igformat_ecran.py
   et frontend/shared/qa/ig-format.test.mjs.

   window.__dzIgFormat.monter(noeud, postId, { statut })   idempotent : rappelé à chaque rendu de l'éditeur

   Le contrat du serveur (backend/app/api/routes.py, t494) :
   - GET /api/schedule/instagram/reglage        {depot_fal, fal_pret, formes, graduations, carrousel: [min, max]}
   - PUT /api/schedule/instagram/reglage        {depot_fal: bool}
   - GET /api/schedule/{id}/instagram           {forme, graduation, images, exige_depot, a_video, statut}
   - PUT /api/schedule/{id}/instagram           {forme, graduation, images} ; 409 post publié, 422 saisie fautive
   - GET /api/images                            la Bibliothèque (choix des images d'un carrousel)
   Rien n'est publié ici. Le dépôt temporaire chez fal n'est JAMAIS activé sans la case cochée par l'utilisateur.
   Tout texte venu du serveur est posé en textContent. Libellés par dzT. Vanilla DOM. */
(function () {
  "use strict";
  if (window.__dzIgFormat) return;

  var FORMES = ["reel", "essai", "image", "carrousel", "story"];
  var GRADUATIONS = ["MANUAL", "SS_PERFORMANCE"];
  var BIBLIO_MAX = 60;
  var JSON_H = { "Content-Type": "application/json" };

  function T(cle, vars) { return typeof window.dzT === "function" ? window.dzT(cle, vars) : cle; }
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
  async function lireJson(r) { try { return await r.json(); } catch (e) { return {}; } }

  var CSS = ""
    + ".dzIgf{display:flex;flex-direction:column;gap:6px;margin:10px 0;padding:8px 10px;border:1px solid var(--stroke,#2a2930);border-radius:var(--r-sm);"
    + "background:var(--bg-base,#0f0f12);color:var(--ink,#c4bfb6);font-family:var(--f-ui,system-ui,sans-serif);font-size:12px;line-height:1.45}"
    + ".dzIgf h4{margin:0;font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-muted,#8a857d);font-weight:600}"
    + ".dzIgfRang{display:flex;flex-wrap:wrap;gap:6px;align-items:center}"
    + ".dzIgf select,.dzIgf button{background:var(--bg-panel-2,#1c1c21);color:var(--ink-strong,#f2efe9);border:1px solid var(--stroke,#2a2930);border-radius:var(--r-sm);padding:3px 8px;font:inherit}"
    + ".dzIgf button{cursor:pointer}.dzIgf [disabled]{opacity:.55;cursor:default}"
    + ".dzIgfNote{margin:0;font-size:11px;color:var(--ink-muted,#8a857d)}"
    + ".dzIgfAlerte{margin:0;font-size:11.5px;color:var(--amber,#f0b429)}"
    + ".dzIgfErreur{margin:0;font-size:11.5px;color:var(--red,#e35d4a)}"
    + ".dzIgfAccord{display:flex;gap:6px;align-items:flex-start;font-size:11.5px}"
    + ".dzIgfGrille{display:grid;grid-template-columns:repeat(6,1fr);gap:4px;max-height:168px;overflow:auto}"
    + ".dzIgfVignette{position:relative;padding:0;aspect-ratio:1;overflow:hidden}"
    + ".dzIgfVignette img{width:100%;height:100%;object-fit:cover;display:block}"
    + ".dzIgfVignette[aria-pressed=true]{outline:2px solid var(--accent,#f0b429);outline-offset:-2px}"
    + ".dzIgfRangNum{position:absolute;top:2px;left:2px;min-width:16px;padding:0 3px;background:var(--accent,#f0b429);color:#151519;font-size:10px;font-weight:700;text-align:center}";
  function poserCss() {
    if (document.getElementById && document.getElementById("dzIgfCss")) return;
    var s = el("style", { id: "dzIgfCss" });
    s.textContent = CSS;
    (document.head || document.documentElement).appendChild(s);
  }

  function construire(noeud, postId, statut) {
    poserCss();
    var vivant = true, tour = 0;
    var E = { forme: "reel", graduation: "MANUAL", images: [], exige: false, depot: false, fal: false, bornes: [2, 20], biblio: null, fige: false };
    var racine = el("div", { class: "dzIgf", "data-dz-igformat": "racine" });
    var selForme = el("select", { "data-dz-igformat": "forme", "aria-label": T("igformat.forme.libelle") },
      FORMES.map(function (f) { return el("option", { value: f, texte: T("igformat.forme." + f) }); }));
    var selGrad = el("select", { "data-dz-igformat": "graduation", "aria-label": T("igformat.graduation.libelle") },
      GRADUATIONS.map(function (g) { return el("option", { value: g, texte: T("igformat.graduation." + g.toLowerCase()) }); }));
    var aide = el("p", { class: "dzIgfNote", "data-dz-igformat": "aide" });
    var zoneCarrousel = el("div", { "data-dz-igformat": "carrousel" });
    var zoneDepot = el("div", { "data-dz-igformat": "depot" });
    var erreur = el("p", { class: "dzIgfErreur", "data-dz-igformat": "erreur", role: "alert" });
    racine.appendChild(el("h4", { texte: T("igformat.panneau.titre") }));
    racine.appendChild(el("div", { class: "dzIgfRang" }, [selForme, selGrad]));
    [aide, zoneCarrousel, zoneDepot, erreur].forEach(function (x) { racine.appendChild(x); });
    noeud.appendChild(racine);
    selForme.addEventListener("change", function () { E.forme = selForme.value; enregistrer(); });
    selGrad.addEventListener("change", function () { E.graduation = selGrad.value; enregistrer(); });

    function dire(texte) { erreur.textContent = texte || ""; }

    function dessiner() {
      selForme.value = E.forme;
      selGrad.value = E.graduation;
      [selForme, selGrad].forEach(function (s) { if (E.fige) s.setAttribute("disabled", ""); else s.removeAttribute("disabled"); });
      if (E.forme === "essai") selGrad.removeAttribute("hidden"); else selGrad.setAttribute("hidden", "");
      aide.textContent = T("igformat.aide." + E.forme);
      vider(zoneCarrousel);
      if (E.forme === "carrousel") {
        zoneCarrousel.appendChild(el("p", { class: "dzIgfNote", "data-dz-igformat": "compte",
          texte: T("igformat.carrousel.compte", { n: E.images.length, min: E.bornes[0], max: E.bornes[1] }) }));
        if (E.biblio === null) { E.biblio = []; lireBiblio(); }
        zoneCarrousel.appendChild(el("div", { class: "dzIgfGrille" }, E.biblio.map(function (nom) {
          var rang = E.images.indexOf(nom);
          var b = el("button", { type: "button", class: "dzIgfVignette", "data-dz-igformat": "vignette", title: nom,
            "aria-pressed": rang >= 0 ? "true" : "false", "aria-label": nom, on: { click: function () { basculer(nom); } } },
            [el("img", { src: "/api/images/" + encodeURIComponent(nom), alt: "", loading: "lazy" }),
              rang >= 0 ? el("span", { class: "dzIgfRangNum", texte: String(rang + 1) }) : null]);
          if (E.fige) b.setAttribute("disabled", "");
          return b;
        })));
      }
      vider(zoneDepot);
      if (E.exige) {
        if (!E.fal) {
          zoneDepot.appendChild(el("p", { class: "dzIgfAlerte", "data-dz-igformat": "sans-fal", texte: T("igformat.depot.sans_fal") }));
        } else {
          var caseAccord = el("input", { type: "checkbox", "data-dz-igformat": "accord", id: "dzIgfAccord-" + postId });
          caseAccord.checked = !!E.depot;
          caseAccord.addEventListener("change", function () { reglerDepot(!!caseAccord.checked); });
          zoneDepot.appendChild(el("label", { class: "dzIgfAccord", for: "dzIgfAccord-" + postId },
            [caseAccord, el("span", { texte: T("igformat.depot.accord") })]));
          if (!E.depot) zoneDepot.appendChild(el("p", { class: "dzIgfAlerte", "data-dz-igformat": "bloque", texte: T("igformat.depot.bloque") }));
        }
      }
    }

    function basculer(nom) {
      if (E.fige) return;
      var i = E.images.indexOf(nom);
      if (i >= 0) E.images.splice(i, 1);
      else if (E.images.length < E.bornes[1]) E.images.push(nom);
      else return;
      enregistrer();
    }

    async function lireBiblio() {
      try {
        var j = await lireJson(await window.fetch("/api/images"));
        E.biblio = ((j && j.images) || []).map(function (x) { return typeof x === "string" ? x : x && x.filename; })
          .filter(Boolean).slice(0, BIBLIO_MAX);
      } catch (e) { E.biblio = []; }
      if (vivant) dessiner();
    }

    async function charger(gardeErreur) {
      var moi = ++tour;
      try {
        var rs = await Promise.all([window.fetch("/api/schedule/instagram/reglage"), window.fetch("/api/schedule/" + encodeURIComponent(postId) + "/instagram")]);
        if (!rs[0].ok || !rs[1].ok) throw new Error("lecture");
        var g = await lireJson(rs[0]), f = await lireJson(rs[1]);
        if (!vivant || moi !== tour) return;
        E.depot = g.depot_fal === true; E.fal = g.fal_pret === true;
        if (Array.isArray(g.carrousel) && g.carrousel.length === 2) E.bornes = g.carrousel;
        E.forme = FORMES.indexOf(f.forme) >= 0 ? f.forme : "reel";
        E.graduation = GRADUATIONS.indexOf(f.graduation) >= 0 ? f.graduation : "MANUAL";
        E.images = Array.isArray(f.images) ? f.images.slice() : [];
        E.exige = f.exige_depot === true;
        if (!gardeErreur) dire("");
      } catch (e) {
        if (!vivant || moi !== tour) return;
        dire(T("igformat.etat.erreur_lecture"));
      }
      dessiner();
    }

    async function enregistrer() {
      var moi = ++tour;
      dessiner();
      try {
        var r = await window.fetch("/api/schedule/" + encodeURIComponent(postId) + "/instagram", { method: "PUT", headers: JSON_H,
          body: JSON.stringify({ forme: E.forme, graduation: E.graduation, images: E.forme === "carrousel" ? E.images : [] }) });
        var j = await lireJson(r);
        if (!vivant || moi !== tour) return;
        if (!r.ok) { dire(r.status === 409 ? T("igformat.etat.deja_publie") : T("igformat.etat.erreur_ecriture")); return charger(true); }
        E.exige = j.exige_depot === true;
        dire("");
      } catch (e) {
        if (!vivant || moi !== tour) return;
        dire(T("igformat.etat.erreur_ecriture"));
      }
      dessiner();
    }

    async function reglerDepot(oui) {
      try {
        var r = await window.fetch("/api/schedule/instagram/reglage", { method: "PUT", headers: JSON_H, body: JSON.stringify({ depot_fal: oui }) });
        var j = await lireJson(r);
        if (!vivant) return;
        if (r.ok) { E.depot = j.depot_fal === true; dire(""); } else dire(T("igformat.etat.erreur_ecriture"));
      } catch (e) { if (vivant) dire(T("igformat.etat.erreur_ecriture")); }
      dessiner();
    }

    function figer(st) { E.fige = st === "posted" || st === "posting"; dessiner(); }
    figer(statut);
    charger();
    return { figer: figer, demonter: function () { vivant = false; if (racine.parentNode) racine.parentNode.removeChild(racine); } };
  }

  function monter(noeud, postId, opts) {
    if (!noeud || !postId) return null;
    var statut = opts && opts.statut;
    var deja = noeud.__dzIgFormat;
    if (deja && deja.post === postId) {
      if (deja.statut !== statut) { deja.statut = statut; deja.c.figer(statut); }
      return deja.c;
    }
    if (deja) deja.c.demonter();
    noeud.__dzIgFormat = { post: postId, statut: statut, c: construire(noeud, postId, statut) };
    return noeud.__dzIgFormat.c;
  }

  window.__dzIgFormat = { monter: monter };
})();
