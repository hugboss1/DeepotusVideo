/* dz-pour-qui.js — le bandeau « POUR QUI » et la FICHE CLIENT (t309, tâche 5, 26/10/2026, plan
   docs/superpowers/plans/2026-10-26-t309-securites-client.md décision 7, spec 2026-10-25-boite-a-outils-design.md §5.5).
   SOURCE : frontend/shared/dz-pour-qui.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-pour-qui.js, chargée par
   frontend/dist/index.html (balise classique après dz-garde-client.js). AUCUN maillon : le bundle n'est pas touché. Le
   banc backend/tests/test_pour_qui_ecran.py refuse toute dérive et le joue sous node (faux DOM, faux fetch).

   Le bandeau [data-dz-pour-qui] : posé en FRÈRE juste après `main > header` (jamais dans un enfant géré par React) sur
   les vues quick, studio, scheduler et library (localStorage.dz_view) ; retiré sur les autres. Relu à chaque mutation
   de #root (un `main` recréé le reçoit à nouveau, jamais deux), à « deepotus:navigate » ; les données (GET /api/espaces,
   GET /api/library/projets/actif) se relisent à « deepotus:espace-refresh » et « dz-projets ». Il montre la pastille de
   couleur et le nom de l'espace actif, « Projet : <nom> » si un projet est actif. Un espace gouverné par un client (type
   client, ou produit dont le parent est un client) a un liseré gauche de 3 px de SA couleur, « Client : <nom> » (la
   société de la fiche, sinon le nom de l'espace client) et le bouton « Fiche client ».

   window.__dzPourQui.rafraichir() -> Promise : relit les données et redessine le bandeau.
   window.__dzPourQui.ouvrirFiche(espaceId) -> Promise<null> : la boîte de la fiche du client qui gouverne l'espace
     (null tout de suite s'il n'y en a pas). Charte de dialogue.js (angles vifs, en-tête IBM Plex Mono en capitales),
     Tab piégé (t326), Échap ou « Fermer » ferment. On y trouve :
     - les consentements (canal, date, moyen) ; « Révoquer » confirme par window.__dzDialogue.confirmer puis dit le
       nombre de posts mis en pause que rend la route (en_pause) ;
     - « Ajouter un consentement » : canal parmi les canal_id des récapitulatifs des espaces gouvernés, moyen ;
       envoie {canal_id, permis: ["publier"], moyen} ;
     - les posts « à valider » des espaces gouvernés (libellé de window.__dzGardeClient.etiquette) : « Validé par le
       client » / « À corriger » avec le moyen de la réponse -> POST /api/schedule/{id}/validation-client, puis
       « deepotus:schedule-recharger » (le Planificateur relit ses posts) ; t311 tâche 6 : pour un post « a_valider » et
       une fiche qui a un contact WhatsApp, « Envoyer au client par WhatsApp » [data-dz-pour-qui-wa-valider] ->
       POST /api/schedule/{id}/validation-whatsapp ; l'état et la note de correction (GET /api/schedule/{id}/client,
       `validation_whatsapp`) s'affichent sous le post ;
     - le journal, plus récent d'abord, 50 lignes au plus.
   Données utilisateur par textContent (marquées data-dz-brut). Textes : clés espaces.pourqui.*
   (frontend/shared/i18n/espaces.json). Glyphes Deepotus (dzIcone), jamais d'emoji. */
(function () {
  "use strict";
  if (window.__dzPourQui) return;

  var JSON_H = { "Content-Type": "application/json" };
  var VUES = { quick: 1, studio: 1, scheduler: 1, library: 1 };
  var MOYENS = ["ecrit", "whatsapp", "doigt"];
  var MAX_JOURNAL = 50;
  var RECHARGER = "deepotus:schedule-recharger";
  var S = {
    bandeau: "flex:none;display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:5px 14px;min-height:30px;box-sizing:border-box;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));background:var(--srf-panel,var(--bg-panel-2,#13171c));color:var(--txt-base,var(--ink,#cfd6e2));font:12px/1.4 system-ui,sans-serif",
    pastille: "display:inline-block;width:10px;height:10px;flex:none;border-radius:0;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138))",
    nom: "font-weight:600;color:var(--txt-hi,var(--ink-strong,#e6e9ee))",
    meta: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    client: "font-size:11.5px;color:var(--txt-hi,var(--ink-strong,#e6e9ee))",
    voile: "position:fixed;inset:0;z-index:9998;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center",
    boite: "width:640px;max-width:94vw;max-height:86vh;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    corps: "padding:12px 14px;overflow-y:auto;display:flex;flex-direction:column;gap:12px;color:var(--txt-base,var(--ink,#cfd6e2))",
    section: "display:flex;flex-direction:column;gap:6px",
    titreSec: "font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    ligne: "display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:5px 8px;border:1px solid var(--brd-soft,var(--stroke,#222830));border-radius:0",
    ligneJ: "display:flex;gap:8px;flex-wrap:wrap;font-size:11.5px;padding:2px 0;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830))",
    cle: "font-size:11px;font-family:var(--f-mono,'IBM Plex Mono',monospace);color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    note: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    champ: "font:inherit;font-size:12px;padding:4px 6px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));color:var(--txt-hi,var(--ink-strong,#e6e9ee));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138))",
    statut: "font-size:12px;color:var(--txt-hi,var(--ink-strong,#e6e9ee));padding:0 14px 8px",
    erreur: "font-size:12px;color:var(--red,#e5484d);padding:0 14px 8px",
    pied: "display:flex;gap:8px;justify-content:flex-end;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
    btn: "min-width:88px;height:28px;padding:0 12px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit",
    petit: "display:inline-flex;align-items:center;gap:4px;height:24px;padding:0 9px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit;font-size:11.5px",
    danger: ";border-color:var(--red,#e5484d);color:var(--red,#e5484d)",
    glyphe: "display:inline-flex;width:14px;height:14px"
  };

  var etat = { espaces: [], actif: "", projet: null, fiches: {}, charge: false };
  var minuterie = null;

  function T(cle, vars) { return typeof window.dzT === "function" ? window.dzT(cle, vars) : cle; }
  function icone(cle) { return typeof window.dzIcone === "function" ? window.dzIcone(cle, { taille: 14 }) : ""; }
  // t309 revue finale D3 (26/10/2026) : une heure UTC (« Z » ou décalage : run_at du post) s'affiche en heure LOCALE, comme
  // le calendrier ; une heure sans fuseau (dates de la fiche, déjà locales) telle quelle.
  function deux(n) { return (n < 10 ? "0" : "") + n; }
  function quand(iso) {
    if (!iso) return "";
    var s = String(iso);
    if (/(Z|[+-]\d\d:?\d\d)$/.test(s)) {
      var d = new Date(s);
      if (!isNaN(d.getTime())) {
        return d.getFullYear() + "-" + deux(d.getMonth() + 1) + "-" + deux(d.getDate()) + " " + deux(d.getHours()) + ":" +
          deux(d.getMinutes());
      }
    }
    return s.replace("T", " ").slice(0, 16);
  }
  // t309 revue finale M2 : un post programmé ou prêt sans date de validation du client (la boucle le saute en valide_par_client)
  function enPause(p) { return !!p && (p.status === "scheduled" || p.status === "ready") && !p.valide_client_le; }
  function couleur(c) { return /^#[0-9a-fA-F]{3,8}$/.test(c || "") ? c : "#888888"; }

  function el(tag, style, texte) {
    var n = document.createElement(tag);
    if (style) n.setAttribute("style", style);
    if (texte != null) n.textContent = texte;
    return n;
  }
  function brut(tag, style, texte) { var n = el(tag, style, texte); n.setAttribute("data-dz-brut", "1"); return n; }
  function bouton(texte, style, glyphe) {
    var b = el("button", style);
    b.type = "button";
    if (glyphe) {
      var g = el("span", S.glyphe);
      g.innerHTML = icone(glyphe);
      b.appendChild(g);
    }
    b.appendChild(el("span", "", texte));
    return b;
  }

  function envoyer(url, methode, corps) {
    var o = { method: methode || "GET" };
    if (corps !== undefined) { o.headers = JSON_H; o.body = JSON.stringify(corps); }
    return fetch(url, o).then(function (R) {
      return R.json().catch(function () { return {}; }).then(function (j) {
        if (!R.ok) {
          var d = j && j.detail;
          throw new Error(d && typeof d === "object" && d.message ? String(d.message) : d ? String(d) : "HTTP " + R.status);
        }
        return j;
      });
    });
  }

  // ── qui gouverne : un client, ou le parent client d'un produit (comme espaces.client_responsable) ──
  function vueDe(id) { return etat.espaces.filter(function (e) { return e && e.id === id; })[0] || null; }
  function gouverneur(id) {
    var e = vueDe(id);
    if (!e) return null;
    if (e.type === "client") return e;
    var p = e.type === "produit" && e.parent ? vueDe(e.parent) : null;
    return p && p.type === "client" ? p : null;
  }
  function gouvernes(client) {
    return [client.id].concat(etat.espaces.filter(function (e) {
      return e && e.type === "produit" && e.parent === client.id;
    }).map(function (e) { return e.id; }));
  }
  function nomClient(client, fiche) {
    var s = fiche && typeof fiche.societe === "string" ? fiche.societe.trim() : "";
    return s || client.nom || client.id;
  }

  // ── les données du bandeau ──
  function rafraichir() {
    return Promise.all([
      envoyer("/api/espaces?archives=true").then(function (j) {
        etat.espaces = (j && j.espaces) || [];
        etat.actif = (j && j.actif) || "";
      }, function () { /* on garde ce qu'on avait */ }),
      envoyer("/api/library/projets/actif").then(function (j) {
        etat.projet = j && j.id ? j : null;
      }, function () { etat.projet = null; })
    ]).then(function () {
      var c = gouverneur(etat.actif);
      if (!c) return null;
      return envoyer("/api/espaces/" + encodeURIComponent(c.id) + "/client").then(function (f) {
        etat.fiches[c.id] = f;
      }, function () { delete etat.fiches[c.id]; });
    }).then(function () { etat.charge = true; dessiner(); });
  }

  function vue() {
    try { return window.localStorage.getItem("dz_view") || "quick"; } catch (e) { return "quick"; }
  }
  function existant() { return document.querySelector("[data-dz-pour-qui]"); }
  function retirer() {
    var b = existant();
    while (b) { b.remove(); b = existant(); }
  }

  var signature = "";
  function dessiner() {
    var tete = document.querySelector("main > header");
    var esp = vueDe(etat.actif);
    if (!etat.charge || !VUES[vue()] || !tete || !tete.parentNode || !esp) { retirer(); signature = ""; return; }
    var c = gouverneur(esp.id), f = c ? etat.fiches[c.id] : null;
    var sig = JSON.stringify([esp.id, esp.nom, esp.couleur, c && c.id, c && nomClient(c, f),
                              etat.projet && etat.projet.nom, T("espaces.pourqui.fiche")]);
    var b = existant();
    // un bandeau en trop (vieux `main`) : retiré ; le bon reste en place s'il est déjà juste après l'entête
    Array.prototype.forEach.call(document.querySelectorAll("[data-dz-pour-qui]"), function (n) {
      if (n !== b) n.remove();
    });
    if (b && sig === signature) {
      if (tete.nextSibling !== b) tete.parentNode.insertBefore(b, tete.nextSibling);
      return;
    }
    if (!b) {
      b = el("div", "");
      b.setAttribute("data-dz-pour-qui", "1");
      b.setAttribute("role", "region");
    }
    signature = sig;
    b.textContent = "";
    // t309 revue finale (26/10/2026) : une région nommée (role=status était annoncé à chaque redessin) ; et l'attribut
    // de l'espace est à NOUS (data-dz-pq-espace) : data-espace est observé par dz-projet-canaux.js, qui vidait le bandeau.
    b.setAttribute("aria-label", T("espaces.pourqui.bandeau"));
    b.setAttribute("data-dz-pq-espace", esp.id);
    b.setAttribute("style", S.bandeau + (c ? ";border-left:3px solid " + couleur(esp.couleur) : ""));
    var pa = el("span", S.pastille + ";background:" + couleur(esp.couleur));
    pa.setAttribute("data-dz-pq-pastille", "1");
    pa.setAttribute("aria-hidden", "true");
    b.appendChild(pa);
    b.appendChild(brut("span", S.nom, esp.nom || esp.id));
    if (etat.projet && etat.projet.id) {
      var pr = el("span", S.meta, T("espaces.pourqui.projet", { nom: etat.projet.nom || etat.projet.id }));
      pr.setAttribute("data-dz-pq-projet", "1");
      b.appendChild(pr);
    }
    if (c) {
      var cl = el("span", S.client, T("espaces.pourqui.client", { nom: nomClient(c, f) }));
      cl.setAttribute("data-dz-pq-client", c.id);
      b.appendChild(cl);
      var bt = bouton(T("espaces.pourqui.fiche"), S.petit, "dz-nav-documents");
      bt.setAttribute("data-dz-pq-fiche", c.id);
      bt.setAttribute("title", T("espaces.pourqui.fiche_aide"));
      bt.addEventListener("click", function () { ouvrirFiche(esp.id); });
      b.appendChild(bt);
    }
    if (tete.nextSibling !== b) tete.parentNode.insertBefore(b, tete.nextSibling);
  }
  function planifier() {
    if (minuterie) clearTimeout(minuterie);
    // après le passage de React (dz_view est écrit par un effet) : on relit la vue un peu plus tard
    minuterie = setTimeout(function () { minuterie = null; dessiner(); }, 40);
  }

  // ── la boîte de la fiche ──
  var courant = null;
  function ouvrirFiche(espaceId) {
    var pret = etat.espaces.length ? Promise.resolve() : rafraichir();
    return pret.then(function () {
      var client = gouverneur(espaceId || etat.actif);
      if (!client) return null;
      if (courant) courant();
      return boite(client);
    });
  }

  function boite(client) {
    return new Promise(function (resoudre) {
      var st = { fiche: etat.fiches[client.id] || null, canaux: [], libelles: {}, posts: [], moyens: {}, validations: {},
                 ajoutCanal: "", ajoutMoyen: MOYENS[0], occupe: false, attente: false };
      var voile = el("div", S.voile);
      voile.setAttribute("role", "dialog");
      voile.setAttribute("aria-modal", "true");
      voile.setAttribute("data-dz-pq-boite", client.id);
      voile.className = "dz-dialogue dz-pour-qui";
      var cadre = el("div", S.boite);
      var tete = el("div", S.tete);
      var corps = el("div", S.corps);
      var msg = el("div", S.statut, "");
      msg.setAttribute("role", "status");
      msg.setAttribute("data-dz-pq-msg", "1");
      var erreur = el("div", S.erreur, "");
      erreur.setAttribute("role", "alert");
      erreur.setAttribute("data-dz-pq-erreur", "1");
      var pied = el("div", S.pied);
      var fermerB = bouton(T("commun.action.fermer"), S.btn);
      fermerB.setAttribute("data-dz-pq-fermer", "1");
      pied.appendChild(fermerB);
      cadre.appendChild(tete);
      cadre.appendChild(corps);
      cadre.appendChild(msg);
      cadre.appendChild(erreur);
      cadre.appendChild(pied);
      voile.appendChild(cadre);

      var fini = false;
      function fin() {
        if (fini) return;
        fini = true;
        if (courant === fin) courant = null;
        document.removeEventListener("keydown", surTouche, true);
        voile.remove();
        resoudre(null);
      }
      // t326 (26/10/2026) : piège du focus — Tab et Maj+Tab bouclent sur les éléments focalisables VISIBLES de la boîte
      function pieger(ev) {
        var l = Array.prototype.slice.call(cadre.querySelectorAll("button, input, select, textarea, a[href], [tabindex]")).filter(function (n) {
          return !n.disabled && n.getAttribute("tabindex") !== "-1" && n.offsetParent !== null;
        });
        ev.preventDefault();
        if (!l.length) return;
        var i = l.indexOf(document.activeElement), n = l.length;
        var j = i < 0 ? (ev.shiftKey ? n - 1 : 0) : (i + (ev.shiftKey ? -1 : 1) + n) % n;
        l[j].focus();
      }
      function surTouche(ev) {
        if (st.attente) return;     // la confirmation de __dzDialogue a la main : ni Tab ni Échap ne sont à nous
        if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); fin(); }
        else if (ev.key === "Tab") pieger(ev);
      }
      courant = fin;
      fermerB.addEventListener("click", fin);
      document.addEventListener("keydown", surTouche, true);

      function dire(t) { msg.textContent = t || ""; }
      function echec(e) { erreur.textContent = T("espaces.pourqui.erreur", { detail: String(e && e.message || e) }); }
      function titre() {
        var t = T("espaces.pourqui.titre", { nom: nomClient(client, st.fiche) });
        tete.textContent = t;
        voile.setAttribute("aria-label", t);
      }
      function libelleCanal(cid) { return st.libelles[cid] ? st.libelles[cid] + " (" + cid + ")" : cid || "—"; }
      function section(cle) {
        var s = el("div", S.section);
        s.appendChild(el("div", S.titreSec, T(cle)));
        corps.appendChild(s);
        return s;
      }
      function selectMoyen(valeur, surChange) {
        var s = el("select", S.champ);
        MOYENS.forEach(function (m) { var o = el("option", "", T("espaces.pourqui.moyen_" + m)); o.value = m; s.appendChild(o); });
        s.value = valeur;
        s.addEventListener("change", function () { surChange(s.value); });
        return s;
      }

      // ── les consentements ──
      function consentements() {
        var s = section("espaces.pourqui.consentements");
        var l = (st.fiche && st.fiche.consentements) || [];
        if (!l.length) s.appendChild(el("div", S.note, T("espaces.pourqui.aucun_consentement")));
        l.forEach(function (x) {
          var li = el("div", S.ligne);
          li.setAttribute("data-dz-pq-consentement", x.canal_id);
          li.appendChild(brut("strong", "", libelleCanal(x.canal_id)));
          li.appendChild(el("span", S.note, T("espaces.pourqui.donne_le", { date: quand(x.date),
                                                                            moyen: T("espaces.pourqui.moyen_" + (MOYENS.indexOf(x.moyen) >= 0 ? x.moyen : "ecrit")) })));
          if (x.revoque_le) {
            li.appendChild(el("span", S.note, T("espaces.pourqui.revoque_le", { date: quand(x.revoque_le) })));
          } else {
            var r = bouton(T("espaces.pourqui.revoquer"), S.petit + S.danger, "dz-action-annuler");
            r.setAttribute("data-dz-pq-revoquer", x.canal_id);
            r.disabled = st.occupe;
            r.addEventListener("click", function () { revoquer(x.canal_id); });
            li.appendChild(r);
          }
          s.appendChild(li);
        });
        // ajouter
        var a = el("div", S.ligne);
        a.setAttribute("data-dz-pq-ajout", "1");
        a.appendChild(el("span", S.note, T("espaces.pourqui.ajouter_titre")));
        if (!st.canaux.length) {
          a.appendChild(el("span", S.note, T("espaces.pourqui.aucun_canal")));
        } else {
          if (st.canaux.indexOf(st.ajoutCanal) < 0) st.ajoutCanal = st.canaux[0];
          var sc = el("select", S.champ);
          sc.setAttribute("aria-label", T("espaces.pourqui.canal"));
          sc.setAttribute("data-dz-pq-ajout-canal", "1");
          st.canaux.forEach(function (cid) { var o = brut("option", "", libelleCanal(cid)); o.value = cid; sc.appendChild(o); });
          sc.value = st.ajoutCanal;
          sc.addEventListener("change", function () { st.ajoutCanal = sc.value; });
          var sm = selectMoyen(st.ajoutMoyen, function (v) { st.ajoutMoyen = v; });
          sm.setAttribute("aria-label", T("espaces.pourqui.moyen"));
          sm.setAttribute("data-dz-pq-ajout-moyen", "1");
          var ab = bouton(T("espaces.pourqui.ajouter"), S.petit, "dz-action-ajouter");
          ab.setAttribute("data-dz-pq-ajouter", "1");
          ab.disabled = st.occupe;
          ab.addEventListener("click", ajouter);
          a.appendChild(sc);
          a.appendChild(sm);
          a.appendChild(ab);
        }
        s.appendChild(a);
      }
      function revoquer(cid) {
        if (st.occupe || fini) return;
        var d = window.__dzDialogue;
        if (!d || typeof d.confirmer !== "function") return;     // jamais une révocation sans confirmation
        st.attente = true;
        erreur.textContent = "";
        Promise.resolve(d.confirmer(T("espaces.pourqui.revoquer_confirmer", { canal: libelleCanal(cid) }),
          { titre: T("espaces.pourqui.revoquer_titre"), ok: T("espaces.pourqui.revoquer"),
            annuler: T("commun.action.annuler"), danger: true })).then(function (oui) {
          st.attente = false;
          if (!oui || fini) return;
          st.occupe = true;
          rendre();
          return envoyer("/api/espaces/" + encodeURIComponent(client.id) + "/client/consentements/revoquer", "POST",
            { canal_id: cid }).then(function (j) {
            st.fiche = j;
            dire(T("espaces.pourqui.en_pause", { n: Number(j && j.en_pause) || 0 }));
            try { window.dispatchEvent(new CustomEvent(RECHARGER)); } catch (e) { /* vieux moteur */ }
          }, echec);
        }, function () { st.attente = false; }).then(function () { st.occupe = false; if (!fini) rendre(); });
      }
      function ajouter() {
        if (st.occupe || fini || !st.ajoutCanal) return;
        st.occupe = true;
        erreur.textContent = "";
        rendre();
        envoyer("/api/espaces/" + encodeURIComponent(client.id) + "/client/consentements", "POST",
          { canal_id: st.ajoutCanal, permis: ["publier"], moyen: st.ajoutMoyen }).then(function (j) {
          st.fiche = j;
          dire(T("espaces.pourqui.ajoute"));
        }, echec).then(function () { st.occupe = false; if (!fini) rendre(); });
      }

      // ── les posts à valider ──
      function posts() {
        var s = section("espaces.pourqui.posts");
        var aValider = ((st.fiche || {}).mode_publication || "valide_par_client") === "valide_par_client";
        var liste = st.posts.filter(function (p) { return p.status === "a_valider" || (aValider && enPause(p)); });
        if (!liste.length) s.appendChild(el("div", S.note, T("espaces.pourqui.aucun_post")));
        liste.forEach(function (p) {
          var li = el("div", S.ligne);
          li.setAttribute("data-dz-pq-post", p.id);
          li.appendChild(brut("strong", "", p.title || p.id));
          var g = window.__dzGardeClient;
          var lib = enPause(p) ? T("espaces.pourqui.en_pause_a_valider")
            : g && typeof g.etiquette === "function" ? g.etiquette(p.status) : null;
          li.appendChild(el("span", S.note, lib || p.status));
          if (p.run_at) li.appendChild(el("span", S.cle, quand(p.run_at)));
          var sm = selectMoyen(st.moyens[p.id] || MOYENS[0], function (v) { st.moyens[p.id] = v; });
          sm.setAttribute("aria-label", T("espaces.pourqui.reponse_par"));
          sm.setAttribute("data-dz-pq-post-moyen", p.id);
          li.appendChild(sm);
          var v = bouton(T("espaces.pourqui.valide"), S.petit, "dz-action-valider");
          v.setAttribute("data-dz-pq-valide", p.id);
          v.disabled = st.occupe;
          v.addEventListener("click", function () { repondre(p.id, "valide"); });
          var c = bouton(T("espaces.pourqui.corriger"), S.petit, "dz-action-modifier");
          c.setAttribute("data-dz-pq-corriger", p.id);
          c.disabled = st.occupe;
          c.addEventListener("click", function () { repondre(p.id, "corriger"); });
          li.appendChild(v);
          li.appendChild(c);
          if (p.status === "a_valider" && contactWa()) {
            var w = bouton(T("espaces.pourqui.wa_valider"), S.petit, "dz-action-envoyer-vers");
            w.setAttribute("data-dz-pour-qui-wa-valider", p.id);
            w.disabled = st.occupe;
            w.addEventListener("click", function () { envoyerWa(p.id); });
            li.appendChild(w);
          }
          var vw = st.validations[p.id];
          if (vw && vw.etat === "envoye") {
            var at = el("span", S.note, T("espaces.pourqui.wa_attente"));
            at.setAttribute("data-dz-pq-wa-etat", p.id);
            li.appendChild(at);
          }
          if (vw && vw.note) {
            var no = el("div", S.note + ";flex-basis:100%;white-space:pre-wrap");
            no.setAttribute("data-dz-pq-wa-note", p.id);
            no.appendChild(el("span", "", T("espaces.pourqui.wa_note") + " "));
            no.appendChild(brut("span", "", String(vw.note)));
            li.appendChild(no);
          }
          s.appendChild(li);
        });
      }
      function contactWa() {
        var c = (st.fiche && st.fiche.contact) || {};
        return !!String(c.whatsapp || "").trim();
      }
      function envoyerWa(id) {
        if (st.occupe || fini) return;
        st.occupe = true;
        erreur.textContent = "";
        rendre();
        envoyer("/api/schedule/" + encodeURIComponent(id) + "/validation-whatsapp", "POST").then(function () {
          dire(T("espaces.pourqui.wa_envoye"));
          return chargerPosts();
        }, echec).then(function () { st.occupe = false; if (!fini) rendre(); });
      }
      function repondre(id, reponse) {
        if (st.occupe || fini) return;
        st.occupe = true;
        erreur.textContent = "";
        rendre();
        envoyer("/api/schedule/" + encodeURIComponent(id) + "/validation-client", "POST",
          { reponse: reponse, moyen: st.moyens[id] || MOYENS[0] }).then(function () {
          dire(T("espaces.pourqui.reponse_notee"));
          try { window.dispatchEvent(new CustomEvent(RECHARGER)); } catch (e) { /* vieux moteur */ }
          return Promise.all([chargerPosts(), chargerFiche()]);
        }, echec).then(function () { st.occupe = false; if (!fini) rendre(); });
      }

      // ── le journal ──
      function journal() {
        var s = section("espaces.pourqui.journal");
        var l = ((st.fiche && st.fiche.journal) || []).slice().sort(function (a, b) {
          return String(b.quand || "") < String(a.quand || "") ? -1 : String(b.quand || "") > String(a.quand || "") ? 1 : 0;
        }).slice(0, MAX_JOURNAL);
        if (!l.length) { s.appendChild(el("div", S.note, T("espaces.pourqui.journal_vide"))); return; }
        s.appendChild(el("div", S.note, T("espaces.pourqui.journal_aide", { n: MAX_JOURNAL })));
        l.forEach(function (x) {
          var li = el("div", S.ligneJ);
          li.setAttribute("data-dz-pq-journal", String(x.quand || ""));
          li.appendChild(el("span", S.cle, quand(x.quand)));
          li.appendChild(el("span", "", T("espaces.pourqui.quoi_" + x.quoi)));
          if (x.canal_id) li.appendChild(brut("span", S.cle, libelleCanal(x.canal_id)));
          li.appendChild(el("span", S.note, T("espaces.pourqui.qui_" + x.qui)));
          s.appendChild(li);
        });
      }

      function rendre() {
        titre();
        corps.textContent = "";
        if (!st.fiche) { corps.appendChild(el("div", S.note, T("espaces.pourqui.chargement"))); return; }
        consentements();
        posts();
        journal();
      }

      // ── les chargements ──
      var ids = gouvernes(client);
      function chargerFiche() {
        return envoyer("/api/espaces/" + encodeURIComponent(client.id) + "/client").then(function (j) {
          st.fiche = j;
          etat.fiches[client.id] = j;
        }, echec);
      }
      function chargerPosts() {
        return envoyer("/api/schedule?espace=*").then(function (l) {
          st.posts = (Array.isArray(l) ? l : []).filter(function (p) {
            // t309 revue finale M2 : aussi les programmés/prêts SANS validation (d'avant t309, ou fiche passée en
            // valide_par_client) ; la boucle les laisse en pause. `posts()` ne les montre qu'en valide_par_client.
            return p && ids.indexOf(p.espace_id) >= 0 && (p.status === "a_valider" || enPause(p));
          });
          // t311 tâche 6 : la validation WhatsApp de chaque post listé (état, note) ; un échec n'affiche rien
          return Promise.all(st.posts.map(function (p) {
            return envoyer("/api/schedule/" + encodeURIComponent(p.id) + "/client").then(function (j) {
              st.validations[p.id] = (j && j.validation_whatsapp) || null;
            }, function () { st.validations[p.id] = null; });
          }));
        }, echec);
      }
      function chargerCanaux() {
        return Promise.all(ids.map(function (id) {
          return envoyer("/api/espaces/" + encodeURIComponent(id) + "/recapitulatif").then(function (r) {
            ((r && r.canaux) || []).forEach(function (c) {
              if (!c || !c.canal_id) return;           // un canal sans canal_id n'est jamais couvrable
              if (st.canaux.indexOf(c.canal_id) < 0) st.canaux.push(c.canal_id);
              if (c.libelle && !st.libelles[c.canal_id]) st.libelles[c.canal_id] = c.libelle;
            });
          }, function () { /* un espace illisible : ses canaux manquent, les autres restent */ });
        }));
      }
      rendre();
      document.body.appendChild(voile);
      try { fermerB.focus(); } catch (e) { /* rien */ }
      Promise.all([chargerFiche(), chargerPosts(), chargerCanaux()]).then(function () {
        if (!fini) { rendre(); dessiner(); }
      });
    });
  }

  // ── branchement ──
  function demarrer() {
    try {
      var cible = document.getElementById("root") || document.body;
      if (typeof MutationObserver === "function") new MutationObserver(planifier).observe(cible, { childList: true, subtree: true });
    } catch (e) { /* page sans DOM complet */ }
    window.addEventListener("deepotus:navigate", planifier);
    window.addEventListener("deepotus:espace-refresh", function () { rafraichir(); });
    window.addEventListener("dz-projets", function () { rafraichir(); });
    rafraichir();
  }
  window.__dzPourQui = { rafraichir: rafraichir, ouvrirFiche: ouvrirFiche };
  if (document.body) demarrer();
  else document.addEventListener("DOMContentLoaded", demarrer);
})();
