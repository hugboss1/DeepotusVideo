/* dz-projet-canaux.js — les CANAUX d'un projet de la Bibliothèque (t307, tâche 4, 25/10/2026, plan
   docs/superpowers/plans/2026-10-25-t307-projets-canaux.md). SOURCE : frontend/shared/dz-projet-canaux.js ; copie
   OCTET POUR OCTET : frontend/dist/shared/dz-projet-canaux.js, chargée par frontend/dist/index.html (balise classique
   après dz-campagnes.js : elle s'exécute AVANT le module différé de la SPA, window.__dzProjetCanaux existe quand la
   Bibliothèque monte). Le banc backend/tests/test_projets_canaux_ecran.py refuse toute dérive et joue la boîte sous
   node (faux DOM, faux fetch).

   window.__dzProjetCanaux :
   - ouvrir(projet) -> Promise<vue|null> : `projet` = la vue du projet (id, nom, espace_id, canaux). Une boîte de
     dialogue liste les comptes de L'ESPACE DU PROJET (GET /api/comptes?espace=<espace_id>, puis filtre côté client
     sur `espace_id` : jamais le compte d'un autre espace), une case par compte (glyphe de la plateforme, libellé,
     handle). « Enregistrer » envoie PUT /api/library/projets/{id}/canaux {canaux: [ids]} ; la vue relue part dans
     l'évènement « dz-projet-canaux » (CustomEvent, detail = la vue) et la promesse la rend. 409 (compte d'un autre
     espace) et 404 (projet ou compte disparu) s'affichent DANS la boîte, traduits par dzT ; la boîte reste ouverte.
     Annuler, Échap ou un clic sur le voile : null.
   - comptes(espace) -> Promise<liste> (mise en cache par espace ; `rafraichir` vide le cache) ;
   - connus(espace) -> la liste en cache ou null (lecture synchrone pour les glyphes de la barre des projets) ;
   - glyphe(plateforme) -> la clé Deepotus Glyph de la plateforme (dz-reseau-*, jamais d'emoji).
   - remplir(hote) : les glyphes des canaux dans l'HÔTE que pose la barre « Projet » (span data-dz-projet-canaux,
     data-canaux = ids séparés par des virgules, data-espace), titre au survol = les comptes ; aucun canal : vide.
     Un observateur de mutations remplit chaque hôte à sa naissance et à chaque changement de data-canaux.
   La barre vit dans la couche frontend/patches/montage.js (bloc #78, aides dzPcB / dzPcEc, saisie
   scripts/i18n_l3/montage_i.py) : elle pose l'hôte et le bouton « Canaux » (classe dzpc-btn, stylée ici) qui appelle
   ouvrir(f), et relit le projet à « dz-projet-canaux ». CHARTE : celle de dialogue.js (aucun arrondi de châssis, en-tête
   IBM Plex Mono en capitales, jetons --srf-* / --brd-* / --txt-* avec replis). Textes : clés projets.canaux.*
   (frontend/shared/i18n/projets.json). Vanilla DOM, aucune dépendance au runtime React. */
(function () {
  "use strict";
  if (window.__dzProjetCanaux) return;

  var JSON_H = { "Content-Type": "application/json" };
  var GLYPHES = { x: "dz-reseau-x", telegram: "dz-reseau-telegram", youtube: "dz-reseau-youtube",
                  instagram: "dz-reseau-instagram", tiktok: "dz-reseau-tiktok" };
  var S = {
    voile: "position:fixed;inset:0;z-index:9998;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center",
    boite: "width:440px;max-width:92vw;max-height:80vh;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    corps: "padding:12px 14px;overflow-y:auto;display:flex;flex-direction:column;gap:6px;color:var(--txt-base,var(--ink,#cfd6e2))",
    note: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    ligne: "display:flex;align-items:center;gap:8px;padding:5px 6px;border:1px solid var(--brd-soft,var(--stroke,#222830));border-radius:0;cursor:pointer;font-size:12.5px",
    glyphe: "display:inline-flex;width:16px;height:16px;color:var(--txt-hi,var(--ink-strong,#e6e9ee))",
    handle: "font-family:var(--f-mono,'IBM Plex Mono',monospace);font-size:11px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    hote: "display:inline-flex;align-items:center;gap:5px;height:24px;padding:0 6px;border:1px solid var(--stroke);color:var(--ink-strong)",
    alerte: "font-size:11px;color:var(--amber,#f0b429)",
    erreur: "font-size:12px;color:var(--red,#e5484d);padding:0 14px 8px",
    pied: "display:flex;gap:8px;justify-content:flex-end;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
    btn: "min-width:88px;height:28px;padding:0 12px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit",
    ok: "background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6);color:var(--accent-ink,#ffffff)"
  };
  var cache = {};
  var courant = null;

  function T(cle, vars) { return typeof window.dzT === "function" ? window.dzT(cle, vars) : cle; }
  function espaceDe(projet) { return (projet && projet.espace_id) || "deepotus"; }
  function glyphe(plateforme) { return GLYPHES[plateforme] || "dz-action-publier"; }
  function icone(cle) { return typeof window.dzIcone === "function" ? window.dzIcone(cle, { taille: 16 }) : ""; }

  function comptes(espace, rafraichir) {
    var esp = espace || "deepotus";
    if (rafraichir) delete cache[esp];
    if (cache[esp]) return cache[esp].promesse;
    var entree = { liste: null };
    entree.promesse = fetch("/api/comptes?espace=" + encodeURIComponent(esp)).then(function (R) {
      if (!R.ok) throw new Error("HTTP " + R.status);
      return R.json();
    }).then(function (j) {
      // le serveur filtre déjà par espace ; on refiltre : la boîte ne propose JAMAIS le compte d'un autre espace.
      // t310 (27/10/2026) : ni un compte whatsapp — t328 : une diffusion se choisit post par post dans le Planificateur,
      // jamais comme canal par défaut d'un projet (comptes.CIBLES_EXPLICITES)
      entree.liste = ((j && j.comptes) || []).filter(function (c) {
        return c && c.espace_id === esp && c.plateforme !== "whatsapp";
      });
      return entree.liste;
    }, function (e) { delete cache[esp]; throw e; });
    cache[esp] = entree;
    return entree.promesse;
  }
  function connus(espace) { var e = cache[espace || "deepotus"]; return e && e.liste ? e.liste : null; }

  function messageErreur(status, detail) {
    if (status === 409) return T("projets.canaux.erreur_espace");
    if (status === 404) return T("projets.canaux.erreur_inconnu");
    return T("projets.canaux.erreur", { detail: detail || ("HTTP " + status) });
  }

  function enregistrer(projet, ids) {
    return fetch("/api/library/projets/" + encodeURIComponent(projet.id) + "/canaux",
      { method: "PUT", headers: JSON_H, body: JSON.stringify({ canaux: ids }) }).then(function (R) {
      return R.json().catch(function () { return {}; }).then(function (j) {
        if (!R.ok) return { ok: false, message: messageErreur(R.status, j && j.detail ? String(j.detail) : "") };
        return { ok: true, vue: j };
      });
    }, function (e) { return { ok: false, message: messageErreur(0, String(e && e.message || e)) }; });
  }

  function el(tag, style, texte) {
    var n = document.createElement(tag);
    if (style) n.setAttribute("style", style);
    if (texte != null) n.textContent = texte;
    return n;
  }

  function ouvrir(projet) {
    if (!projet || !projet.id) return Promise.resolve(null);
    if (courant) courant(null);
    return new Promise(function (resoudre) {
      var esp = espaceDe(projet);
      var choisis = (projet.canaux || []).slice();
      var voile = el("div", S.voile);
      voile.setAttribute("role", "dialog");
      voile.setAttribute("aria-modal", "true");
      voile.setAttribute("data-dz-projet-canaux-boite", projet.id);
      voile.className = "dz-dialogue dz-projet-canaux";
      var boite = el("div", S.boite);
      var titre = T("projets.canaux.titre", { nom: projet.nom || projet.id });
      voile.setAttribute("aria-label", titre);
      var tete = el("div", S.tete, titre);
      var corps = el("div", S.corps);
      corps.appendChild(el("div", S.note, T("projets.canaux.explication")));
      var zone = el("div", "display:flex;flex-direction:column;gap:4px");
      zone.appendChild(el("div", S.note, T("projets.canaux.chargement")));
      corps.appendChild(zone);
      var erreur = el("div", S.erreur, "");
      erreur.setAttribute("role", "alert");
      erreur.setAttribute("data-dz-projet-canaux-erreur", "1");
      var pied = el("div", S.pied);
      var annuler = el("button", S.btn, T("commun.action.annuler"));
      annuler.type = "button";
      var ok = el("button", S.btn + ";" + S.ok);
      ok.textContent = T("projets.canaux.enregistrer");    /* forme lue par scripts/agent/catalogue_partages.py */
      ok.type = "button";
      ok.disabled = true;
      ok.setAttribute("data-dz-projet-canaux-enregistrer", "1");
      pied.appendChild(annuler);
      pied.appendChild(ok);
      boite.appendChild(tete);
      boite.appendChild(corps);
      boite.appendChild(erreur);
      boite.appendChild(pied);
      voile.appendChild(boite);

      var fini = false, occupe = false;
      function fin(vue) {
        if (fini) return;
        fini = true;
        if (courant === fin) courant = null;
        document.removeEventListener("keydown", surTouche, true);
        voile.remove();
        resoudre(vue || null);
      }
      // t326 (26/10/2026) : piège du focus — Tab et Maj+Tab bouclent sur les éléments focalisables VISIBLES de la boîte
      function pieger(ev, boite) {
        var l = Array.prototype.slice.call(boite.querySelectorAll("button, input, select, textarea, a[href], [tabindex]")).filter(function (n) {
          return !n.disabled && n.getAttribute("tabindex") !== "-1" && n.offsetParent !== null;   // offsetParent absent = gardé
        });
        ev.preventDefault();
        if (!l.length) return;
        var i = l.indexOf(document.activeElement), n = l.length;
        var j = i < 0 ? (ev.shiftKey ? n - 1 : 0) : (i + (ev.shiftKey ? -1 : 1) + n) % n;
        l[j].focus();
      }
      function surTouche(ev) {
        if (ev.key === "Escape") { ev.preventDefault(); fin(null); }
        else if (ev.key === "Tab") pieger(ev, boite);
      }
      courant = fin;
      annuler.addEventListener("click", function () { fin(null); });
      voile.addEventListener("click", function (ev) { if (ev.target === voile) fin(null); });
      document.addEventListener("keydown", surTouche, true);

      function montrer(liste) {
        zone.textContent = "";
        if (!liste.length) {
          zone.appendChild(el("div", S.note, T("projets.canaux.aucun_compte")));
        }
        liste.forEach(function (c) {
          var ligne = el("label", S.ligne);
          ligne.setAttribute("data-dz-projet-canal", c.id);
          var caseC = el("input");
          caseC.type = "checkbox";
          caseC.checked = choisis.indexOf(c.id) >= 0;
          caseC.addEventListener("change", function () {
            choisis = caseC.checked ? choisis.concat([c.id]) : choisis.filter(function (i) { return i !== c.id; });
            erreur.textContent = "";
          });
          var g = el("span", S.glyphe);
          g.setAttribute("data-dz-glyphe", glyphe(c.plateforme));
          g.innerHTML = icone(glyphe(c.plateforme));
          var nom = el("span", "", c.libelle || c.id);
          nom.setAttribute("data-dz-brut", "1");
          ligne.appendChild(caseC);
          ligne.appendChild(g);
          ligne.appendChild(nom);
          if (c.handle) ligne.appendChild(el("span", S.handle, c.handle));
          if (c.disponible === false) ligne.appendChild(el("span", S.alerte, T("espaces.comptes.incomplet")));
          zone.appendChild(ligne);
        });
        // un canal posé dont le compte n'est plus dans l'espace reste dans `choisis` : le serveur le refusera (409/404)
        ok.disabled = false;
      }
      comptes(esp, true).then(montrer, function (e) {
        zone.textContent = "";
        erreur.textContent = messageErreur(0, String(e && e.message || e));
      });

      ok.addEventListener("click", function () {
        if (occupe || fini) return;
        occupe = true;
        ok.disabled = true;
        erreur.textContent = "";
        enregistrer(projet, choisis).then(function (r) {
          occupe = false;
          if (!r.ok) { erreur.textContent = r.message; ok.disabled = false; return; }
          try { window.dispatchEvent(new CustomEvent("dz-projet-canaux", { detail: r.vue })); } catch (e) { /* vieux moteur */ }
          fin(r.vue);
        });
      });

      document.body.appendChild(voile);
      try { ok.focus(); } catch (e) { /* rien */ }
    });
  }

  // ── l'hôte des glyphes dans la barre « Projet » (couche montage, dzPcB) ──
  function remplir(hote) {
    if (!hote || !hote.getAttribute) return;
    var ids = String(hote.getAttribute("data-canaux") || "").split(",").filter(Boolean);
    var esp = hote.getAttribute("data-espace") || "deepotus";
    function dessiner() {
      var liste = connus(esp) || [];
      var vus = ids.map(function (i) {
        return liste.filter(function (c) { return c.id === i; })[0] || { id: i, plateforme: "", libelle: i, handle: "" };
      });
      hote.innerHTML = vus.map(function (c) {
        return '<span data-dz-canal="' + String(c.id).replace(/"/g, "") + '" style="display:inline-flex">' +
          icone(glyphe(c.plateforme)) + "</span>";
      }).join("");
      hote.setAttribute("style", ids.length ? S.hote : "display:none");
      if (ids.length) hote.setAttribute("title", T("projets.canaux.survol", { noms: vus.map(function (c) {
        return c.libelle + (c.handle ? " " + c.handle : ""); }).join(", ") }));
      else hote.removeAttribute("title");
    }
    dessiner();
    if (ids.length && !connus(esp)) comptes(esp).then(dessiner, function () { /* les identifiants restent */ });
  }
  function balayer(racine) {
    if (!racine || !racine.querySelectorAll) return;
    if (racine.getAttribute && racine.getAttribute("data-dz-projet-canaux") !== null) remplir(racine);
    Array.prototype.forEach.call(racine.querySelectorAll("[data-dz-projet-canaux]"), remplir);
  }
  function observer() {
    try {
      var st = document.createElement("style");
      st.textContent = ".dzpc-btn{height:24px;padding:0 9px;font-size:11px;border-radius:12px;cursor:pointer;" +
        "border:1px solid var(--stroke);background:transparent;color:var(--ink-soft);display:inline-flex;" +
        "align-items:center;gap:4px}.dzpc-btn:hover{color:var(--ink-strong)}";
      document.head.appendChild(st);
      new MutationObserver(function (ms) {
        ms.forEach(function (m) {
          // t309 revue finale I1 (26/10/2026) : une mutation d'attribut ne remplit que NOS hôtes ; un autre élément qui
          // porte data-espace (le bandeau « pour qui » d'avant) n'est plus vidé ni masqué. Le garde n'est pas dans
          // remplir, que l'API appelle aussi sur un nœud nu.
          if (m.type === "attributes") {
            if (m.target && m.target.getAttribute && m.target.getAttribute("data-dz-projet-canaux") !== null) remplir(m.target);
          }
          else Array.prototype.forEach.call(m.addedNodes || [], function (n) { if (n.nodeType === 1) balayer(n); });
        });
      }).observe(document.body, { childList: true, subtree: true, attributes: true,
                                   attributeFilter: ["data-canaux", "data-espace"] });
      balayer(document.body);
    } catch (e) { /* page sans DOM complet */ }
  }
  if (typeof MutationObserver === "function" && document.body) observer();
  else if (typeof MutationObserver === "function") document.addEventListener("DOMContentLoaded", observer);

  window.__dzProjetCanaux = { ouvrir: ouvrir, comptes: comptes, connus: connus, glyphe: glyphe, remplir: remplir };
})();
