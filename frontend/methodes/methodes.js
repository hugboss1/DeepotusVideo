/* methodes.js — l'écran « MÉTHODES », servi à /methodes/ (t433, lot M0, 08/11/2026 ; conception
   docs/superpowers/specs/2026-11-08-scenario-explorations-agents-design.md §5). Vanilla JS, aucune construction.

   Une galerie de 94 méthodes (GET /api/methodes?…&langue=), filtrable par famille, agent, écran et mots ; un clic ouvre
   la fiche (GET /api/methodes/<slug>?langue=) : étapes, contrôles, pièges, exemples de demandes (copiables), agent
   métier qui la portera, écrans de l'app, lien vers l'exploration d'origine. Lecture seule, gratuit.

   Adresse : ?famille=&agent=&ecran=&q=&slug= — les tiroirs « Méthodes » des écrans (lots M2-M9) ouvrent cette page
   pré-filtrée par ?ecran=<id>. L'état est réécrit dans l'adresse (history.replaceState) à chaque filtre.
   Réponses périmées : S.gen change à chaque lecture ; une réponse plus ancienne ne touche ni S ni le DOM.
   Textes : dzT("methodes.…") (frontend/shared/i18n/methodes.json) ; données des fiches par textContent seulement. */
(function () {
  "use strict";
  if (window.__dzMethodes) return;

  function T(cle, vars) { return typeof window.dzT === "function" ? window.dzT(cle, vars) : cle; }
  function langue() { return typeof window.dzLang === "function" && window.dzLang() === "en" ? "en" : "fr"; }

  // l'icône de chaque famille, en attendant les illustrations du lot M10
  var GLYPHE = {
    "previs-blender": "dz-nav-plateau", "film-agent-blender": "dz-media-film", "video-edit-chaine": "dz-nav-montage",
    "video-personnage-voix": "dz-media-voix", "motion-code": "dz-media-titre", "pub-marketing": "dz-nav-campagne",
    "produit-ecommerce": "dz-media-image", "mode-beaute": "dz-media-persona", "image-edit-reference": "dz-nav-photolab",
    "game-assets-2d": "dz-nav-espace-pixel", "game-assets-3d": "dz-nav-cf-forge-3d", "jeu-jouable": "dz-nav-game-assets",
    "monde-3d-interactif": "dz-nav-cf-volume", "benchmark-modeles": "dz-nav-analytics",
    "livre-illustre-educatif": "dz-nav-bible"
  };
  var FILTRES = ["famille", "agent", "ecran"];

  // t435 : S.agents = {id: true} pour les agents métier DISPONIBLES (GET /api/agents-metier) ; leur fiche propose alors
  // « Parler au … » (conversation.js), sinon « bientôt »
  var S = { reperes: null, liste: [], gen: 0, f: { famille: "", agent: "", ecran: "", q: "" }, slug: "", agents: {} };
  var Z = {};
  window.__dzMethodes = { S: S, T: T, el: el, icone: icone, lire: lire, langue: langue };

  function el(tag, p, enfants) {
    var n = document.createElement(tag);
    p = p || {};
    if (p.cls) n.className = p.cls;
    if (p.texte != null) n.textContent = p.texte;
    if (p.a) Object.keys(p.a).forEach(function (k) { if (p.a[k] != null && p.a[k] !== false) n.setAttribute(k, p.a[k] === true ? "" : p.a[k]); });
    ["type", "value", "placeholder", "href", "target", "rel"].forEach(function (k) { if (p[k] != null) n[k] = p[k]; });
    if (p.on) Object.keys(p.on).forEach(function (k) { n.addEventListener(k, p.on[k]); });
    (enfants || []).forEach(function (e) { if (e) n.appendChild(e); });
    return n;
  }
  function icone(cle, taille) {
    var s = el("span", { cls: "mt-ico", a: { "aria-hidden": "true" } });
    if (typeof window.dzIcone === "function") s.innerHTML = window.dzIcone(cle, { taille: taille || 16 });
    return s;
  }
  function lire(url) {
    return fetch(url, { headers: { Accept: "application/json" } }).then(function (r) {
      if (!r.ok) { var e = new Error("http " + r.status); e.status = r.status; throw e; }
      return r.json();
    });
  }
  function qs(o) {
    return Object.keys(o).filter(function (k) { return o[k]; })
      .map(function (k) { return encodeURIComponent(k) + "=" + encodeURIComponent(o[k]); }).join("&");
  }

  // ── adresse ⇄ état ──────────────────────────────────────────────────────────────────────────────────────────────
  function lireAdresse() {
    var p = new URLSearchParams(window.location.search);
    FILTRES.concat(["q"]).forEach(function (k) { S.f[k] = (p.get(k) || "").slice(0, 200); });
    S.slug = (p.get("slug") || "").slice(0, 120);
  }
  function ecrireAdresse() {
    var o = { famille: S.f.famille, agent: S.f.agent, ecran: S.f.ecran, q: S.f.q, slug: S.slug };
    try { history.replaceState(null, "", window.location.pathname + (qs(o) ? "?" + qs(o) : "")); } catch (e) { /* bac à sable */ }
  }

  // ── squelette ───────────────────────────────────────────────────────────────────────────────────────────────────
  function squelette(racine) {
    Z.sous = el("span", { cls: "mt-sous" });
    Z.q = el("input", { cls: "mt-champ mt-champ--q", type: "search", placeholder: T("methodes.filtre.chercher"),
      a: { "aria-label": T("methodes.filtre.chercher"), "data-dz-methodes-q": true },
      on: { input: function () { S.f.q = Z.q.value.slice(0, 200); S.slug = ""; planifier(); } } });
    Z.selects = {};
    var filtres = FILTRES.map(function (k) {
      var s = el("select", { cls: "mt-champ", a: { "aria-label": T("methodes.filtre." + k), "data-dz-methodes-filtre": k },
        on: { change: function () { S.f[k] = s.value; S.slug = ""; charger(); } } });
      Z.selects[k] = s;
      return el("label", { cls: "mt-etiquette" }, [el("span", { texte: T("methodes.filtre." + k) }), s]);
    });
    Z.effacer = el("button", { cls: "mt-btn mt-btn--discret", type: "button", texte: T("methodes.filtre.effacer"),
      on: { click: function () { S.f = { famille: "", agent: "", ecran: "", q: "" }; S.slug = ""; Z.q.value = ""; remplirFiltres(); charger(); } } });
    var tete = el("header", { cls: "mt-tete" }, [
      el("div", { cls: "mt-marque" }, [icone("dz-action-lancer-recette", 20), el("b", { texte: T("methodes.page.titre") }), Z.sous]),
      Z.q
    ].concat(filtres).concat([Z.effacer]));
    Z.compte = el("div", { cls: "mt-compte", a: { "aria-live": "polite" } });
    Z.grille = el("div", { cls: "mt-grille", a: { "data-dz-methodes-grille": true } });
    Z.fiche = el("article", { cls: "mt-fiche", a: { "data-dz-methodes-fiche": true, hidden: true } });
    Z.pied = el("footer", { cls: "mt-pied", texte: T("methodes.pied.source") });
    var corps = el("div", { cls: "mt-corps" }, [Z.compte, Z.grille, Z.fiche, Z.pied]);
    racine.appendChild(tete);
    racine.appendChild(corps);
    Z.corps = corps;
  }

  function remplirFiltres() {
    var R = S.reperes;
    if (!R) return;
    Z.sous.textContent = T("methodes.page.sous_titre", { n: R.total });
    var sources = {
      famille: R.familles.map(function (x) { return [x.id, x.libelle + " (" + x.nb + ")"]; }),
      agent: R.agents.map(function (x) { return [x.id, x.libelle + " (" + x.nb + ")"]; }),
      ecran: R.ecrans.filter(function (x) { return x.nb > 0; }).map(function (x) { return [x.id, x.libelle + " (" + x.nb + ")"]; })
    };
    FILTRES.forEach(function (k) {
      var s = Z.selects[k];
      s.textContent = "";
      s.appendChild(el("option", { value: "", texte: T(k === "famille" ? "methodes.filtre.toutes" : "methodes.filtre.tous") }));
      sources[k].forEach(function (o) { s.appendChild(el("option", { value: o[0], texte: o[1] })); });
      s.value = sources[k].some(function (o) { return o[0] === S.f[k]; }) ? S.f[k] : "";
      S.f[k] = s.value;
    });
    Z.q.value = S.f.q;
  }

  // ── galerie ─────────────────────────────────────────────────────────────────────────────────────────────────────
  var minuteur = null;
  function planifier() { clearTimeout(minuteur); minuteur = setTimeout(charger, 220); }

  function charger() {
    var gen = ++S.gen;
    ecrireAdresse();
    var url = "/api/methodes?" + qs({ famille: S.f.famille, agent: S.f.agent, ecran: S.f.ecran, q: S.f.q, langue: langue() });
    return lire(url).then(function (d) {
      if (gen !== S.gen) return;
      S.liste = d.methodes || [];
      dessinerGrille();
      if (S.slug) ouvrir(S.slug); else fermerFiche();
    }).catch(function () {
      if (gen !== S.gen) return;
      Z.grille.textContent = "";
      Z.compte.textContent = T("methodes.liste.erreur");
    });
  }

  // t443b : l'illustration de la fiche (générée à nous) si elle existe, sinon l'icône de la famille
  function visuel(m, grand) {
    var cls = "mt-carte-visuel" + (grand ? " mt-carte-visuel--grand" : "") + " mt-fam--" + m.famille;
    if (m.visuel) {
      return el("div", { cls: cls + " mt-carte-visuel--image" }, [
        el("img", { a: { src: m.visuel, alt: "", loading: "lazy", decoding: "async", "data-dz-methode-visuel": m.slug } })
      ]);
    }
    return el("div", { cls: cls }, [icone(GLYPHE[m.famille] || "dz-action-lancer-recette", grand ? 40 : 28)]);
  }

  function badge(texte, cls) { return el("span", { cls: "mt-badge" + (cls ? " " + cls : ""), texte: texte }); }

  function carte(m) {
    return el("button", { cls: "mt-carte", type: "button",
      a: { "data-dz-methode": m.slug, "aria-label": T("methodes.carte.ouvrir", { titre: m.titre }) },
      on: { click: function () { S.slug = m.slug; ecrireAdresse(); ouvrir(m.slug); } } }, [
      visuel(m, false),
      el("div", { cls: "mt-carte-corps" }, [
        el("div", { cls: "mt-carte-famille", texte: m.famille_libelle }),
        el("h3", { cls: "mt-carte-titre", texte: m.titre }),
        el("p", { cls: "mt-carte-resume", texte: m.resume }),
        el("div", { cls: "mt-carte-pied" }, [
          badge(m.agent_libelle, "mt-badge--agent"),
          badge(T("methodes.effort." + String(m.effort).toLowerCase())),
          badge(T("methodes.carte.valeur", { n: m.valeur }))
        ])
      ])
    ]);
  }

  function dessinerGrille() {
    Z.grille.textContent = "";
    Z.compte.textContent = S.liste.length ? T("methodes.liste.compte", { n: S.liste.length }) : T("methodes.liste.vide");
    S.liste.forEach(function (m) { Z.grille.appendChild(carte(m)); });
  }

  // ── fiche ───────────────────────────────────────────────────────────────────────────────────────────────────────
  function fermerFiche() {
    Z.fiche.hidden = true;
    Z.grille.hidden = false;
    Z.compte.hidden = false;
  }

  function liste(titre, items, ordonnee, copiable) {
    if (!items || !items.length) return null;
    var l = el(ordonnee ? "ol" : "ul", { cls: "mt-liste" });
    items.forEach(function (t) {
      var li = el("li", {}, [el("span", { texte: t })]);
      if (copiable) {
        var b = el("button", { cls: "mt-btn mt-btn--petit", type: "button", texte: T("methodes.fiche.copier"),
          on: { click: function () {
            var fini = function () { b.textContent = T("methodes.fiche.copie"); setTimeout(function () { b.textContent = T("methodes.fiche.copier"); }, 1500); };
            if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t).then(fini, fini); else fini();
          } } });
        li.appendChild(b);
      }
      l.appendChild(li);
    });
    return el("section", { cls: "mt-bloc" }, [el("h4", { texte: titre }), l]);
  }

  function ouvrir(slug) {
    var gen = ++S.gen;
    return lire("/api/methodes/" + encodeURIComponent(slug) + "?langue=" + langue()).then(function (f) {
      if (gen !== S.gen) return;
      dessinerFiche(f);
    }).catch(function () {
      if (gen !== S.gen) return;
      Z.fiche.textContent = "";
      Z.fiche.appendChild(el("p", { cls: "mt-vide", texte: T("methodes.fiche.introuvable") }));
      Z.fiche.appendChild(boutonRetour());
      Z.fiche.hidden = false; Z.grille.hidden = true; Z.compte.hidden = true;
    });
  }

  function boutonRetour() {
    return el("button", { cls: "mt-btn", type: "button", a: { "data-dz-methodes-retour": true },
      on: { click: function () { S.slug = ""; ecrireAdresse(); fermerFiche(); } } },
      [icone("dz-media-precedent", 14), el("span", { texte: T("methodes.fiche.retour") })]);
  }

  function dessinerFiche(f) {
    var F = Z.fiche;
    F.textContent = "";
    F.setAttribute("data-dz-methode-ouverte", f.slug);
    var agent = el("aside", { cls: "mt-agent" }, [
      el("div", { cls: "mt-agent-tete", texte: T(f.agent_outil ? "methodes.fiche.outil" : "methodes.fiche.agent") }),
      el("b", { texte: f.agent_libelle }),
      el("p", { texte: f.agent_role }),
      S.agents[f.agent] && window.__dzMethodesConversation
        ? el("button", { cls: "mt-btn mt-btn--accent", type: "button", a: { "data-dz-methodes-parler": f.agent },
            on: { click: function () { window.__dzMethodesConversation.ouvrir(f); } } },
            [icone("dz-action-lancer-recette", 14), el("span", { texte: T("methodes.agent.parler", { agent: f.agent_libelle }) })])
        : el("p", { cls: "mt-agent-bientot", texte: T("methodes.fiche.bientot") })
    ]);
    var ecrans = el("div", { cls: "mt-ligne" }, [el("span", { cls: "mt-ligne-titre", texte: T("methodes.fiche.ecrans") })]
      .concat((f.ecrans_libelles || []).map(function (e) { return badge(e); })));
    var modeles = f.modeles && f.modeles.length ? el("div", { cls: "mt-ligne" },
      [el("span", { cls: "mt-ligne-titre", texte: T("methodes.fiche.modeles") })].concat(f.modeles.map(function (m) { return badge(m, "mt-badge--mono"); }))) : null;
    var source = el("p", { cls: "mt-source" }, [
      el("a", { href: f.source, target: "_blank", rel: "noopener noreferrer", texte: T("methodes.fiche.source") + " ↗" })
    ]);
    if (f.licence_skill) source.appendChild(el("span", { texte: " · " + T("methodes.fiche.licence") }));
    [
      boutonRetour(),
      el("div", { cls: "mt-fiche-tete" }, [
        visuel(f, true),
        el("div", {}, [
          el("div", { cls: "mt-carte-famille", texte: f.famille_libelle }),
          el("h2", { cls: "mt-fiche-titre", texte: f.titre }),
          el("p", { cls: "mt-fiche-resume", texte: f.resume }),
          ecrans, modeles
        ])
      ]),
      el("div", { cls: "mt-fiche-corps" }, [
        el("div", { cls: "mt-fiche-col" }, [
          liste(T("methodes.fiche.etapes"), f.etapes, true),
          liste(T("methodes.fiche.controles"), f.controles),
          liste(T("methodes.fiche.pieges"), f.pieges)
        ]),
        el("div", { cls: "mt-fiche-col mt-fiche-col--cote" }, [agent, liste(T("methodes.fiche.exemples"), f.exemples, false, true)])
      ]),
      source
    ].forEach(function (n) { if (n) F.appendChild(n); });
    F.hidden = false;
    Z.grille.hidden = true;
    Z.compte.hidden = true;
    Z.corps.scrollTop = 0;
  }

  function demarrer() {
    var racine = document.querySelector("[data-dz-methodes]");
    if (!racine) return;
    lireAdresse();
    squelette(racine);
    var agentsPrets = lire("/api/agents-metier?langue=" + langue()).then(function (d) {
      (d.agents || []).forEach(function (a) { if (a.disponible) S.agents[a.id] = true; });
    }).catch(function () { /* sans la liste : toutes les fiches disent « bientôt » */ });
    Promise.all([lire("/api/methodes/reperes?langue=" + langue()), agentsPrets]).then(function (res) {
      var R = res[0];
      S.reperes = R;
      remplirFiltres();
      return charger();
    }).catch(function () { Z.compte.textContent = T("methodes.liste.erreur"); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", demarrer); else demarrer();
})();
