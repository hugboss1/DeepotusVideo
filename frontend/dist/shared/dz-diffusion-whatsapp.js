/* dz-diffusion-whatsapp.js — Planificateur › inspecteur du post : le panneau de DIFFUSION WhatsApp d'un post dont la cible
   est un compte WhatsApp (t328 tâche 5, 27/10/2026, plan docs/superpowers/plans/2026-10-27-t328-diffusions-whatsapp.md,
   Décisions 6-7). SOURCE : frontend/shared/dz-diffusion-whatsapp.js ; copie OCTET POUR OCTET :
   frontend/dist/shared/dz-diffusion-whatsapp.js, chargée par frontend/dist/index.html (balise classique après
   dz-whatsapp-espace.js). Le point de montage `<div data-dz-diffusion={post.id}>` est posé dans DzPostComptes par le
   maillon scripts/patch_bundle_dzdiffusion.py quand UN compte whatsapp est coché. Bancs : frontend/shared/qa/
   diffusion.test.mjs (faux DOM, faux fetch, FR et EN) et backend/tests/test_diffusion_ecran.py (le maillon, la livraison).

   window.__dzDiffusionWhatsapp.monter(el, postId, {compte, espace, delai}) -> Promise (résolue après la 1re lecture) ;
   idempotent pour un même nœud et un même post (le ref du bundle le rappelle à chaque rendu).
     · GET /api/schedule/{post}/diffusion -> {config (n_identites, jamais la liste), audience, devis, refus, etat} ;
     · pas lancée (aucun état, ou configuree / preparation / echec) : ÉDITION — le modèle (GET /api/whatsapp/{cid}/modeles,
       approuvés, sans en-tête média ni en-tête texte variable, avec identifiant Meta ; catégorie affichée), ses
       paramètres (nommés ou positionnels, un seul jeu pour tous), l'audience (« N contacts », écartés et leurs raisons),
       le devis en dollars, « Enregistrer la diffusion » (PUT {modele: {nom, langue}, parametres}). Audience vide :
       message, bouton grisé tant que rien n'a changé. Une liste explicite rangée (n_identites) : l'enregistrer d'ici
       l'élargit, ce que dit une confirmation ;
     · lancée : SUIVI — statut, compteurs (envoyés, livrés, lus, échecs, retirés du marketing), coût réel, « Relire »
       (GET ?relire=1) ; incertaine ou en attente de confirmation : l'explication et « Confirmer l'envoi » (POST
       …/diffusion/confirmer {confirme_incertain: true}) derrière `await window.__dzDialogue.confirmer(` dont le texte
       AVERTIT que confirmer publie aussi les autres canaux du post pas encore envoyés. Sans boîte de dialogue : rien ne
       part (jamais de confirm natif : test_dialogues_partout).
   Le 402 du plafond est lu par dz-plafonds.js (il enveloppe fetch : son dialogue, puis la même requête ou un 402 au détail
   texte affiché ici). Réponses périmées ignorées (jeton par instance), délai de 30 s (GET et PUT abandonnés ; la
   confirmation n'est jamais abandonnée en vol : un message dit d'attendre). Jamais un numéro affiché : le serveur n'en
   rend aucun, et les identités ne sont jamais lues. Données par textContent. Textes : clés diffusion.*
   (frontend/shared/i18n/diffusion.json). Attributs des bancs : data-dz-diffusion-* (panneau, modele, categorie, params,
   param, audience, ecartes, vide, devis, enregistrer, statut, compteurs, compteur, reel, incertain, confirmer, relire,
   msg, erreur, note). */
(function () {
  "use strict";
  if (window.__dzDiffusionWhatsapp) return;

  var DELAI_MS = 30000;
  var JSON_H = { "Content-Type": "application/json" };
  var RELANCABLES = ["configuree", "preparation", "echec"];
  var ECARTES = ["accord", "stop", "marketing", "bsuid"];
  var STATUTS = ["configuree", "preparation", "envoi", "draft", "sending", "completed", "stopped", "failed", "echec"];
  var CATEGORIES = ["marketing", "utility", "authentication"];
  var COMPTEURS = [["envoyes", ["sent"]], ["livres", ["livres", "delivered"]], ["lus", ["lus", "read"]],
                   ["echecs", ["failed"]], ["retires", ["suppressed"]]];
  var MEDIA = ["image", "video", "document"];
  var S = {
    panneau: "display:flex;flex-direction:column;gap:7px;margin-top:6px;padding:8px;border:1px solid var(--stroke,#222830);background:var(--bg-base,#0d1014);font-size:11.5px;color:var(--ink,#cfd6e2)",
    titre: "font-size:11px;color:var(--ink-soft,#9aa4ae);text-transform:uppercase;letter-spacing:.04em",
    note: "font-size:11px;color:var(--ink-muted,#9aa4ae)",
    alerte: "font-size:11.5px;padding:6px 8px;border:1px solid var(--amber,#e5a50a);color:var(--ink-strong,#e6e9ee)",
    etiquette: "display:flex;flex-direction:column;gap:3px;font-size:11px;color:var(--ink-soft,#9aa4ae)",
    champ: "font:inherit;font-size:12px;padding:4px 6px;border-radius:0;background:var(--bg-panel-3,#1b2028);color:var(--ink-strong,#e6e9ee);border:1px solid var(--stroke-strong,#2a3138)",
    ligne: "display:flex;gap:6px;flex-wrap:wrap;align-items:center",
    btn: "height:26px;padding:0 10px;border-radius:0;background:var(--bg-panel-3,#1b2028);border:1px solid var(--stroke-strong,#2a3138);color:var(--ink-strong,#e6e9ee);cursor:pointer;font:inherit;font-size:11.5px",
    msg: "font-size:11.5px;color:var(--green,#3fb950)",
    erreur: "font-size:11.5px;color:var(--red,#e5484d)"
  };

  function T(cle, vars) { return typeof window.dzT === "function" ? window.dzT(cle, vars) : cle; }
  function langue() { return typeof window.dzLang === "function" ? window.dzLang() : "fr"; }
  function el(tag, style, texte, attrs) {
    var n = document.createElement(tag);
    if (style) n.setAttribute("style", style);
    if (texte != null) n.textContent = texte;
    for (var k in attrs || {}) n.setAttribute(k, attrs[k]);
    return n;
  }
  function bouton(texte, attr, surClic) {
    var b = el("button", S.btn, texte);
    b.type = "button";
    b.setAttribute(attr, "1");
    b.addEventListener("click", surClic);
    return b;
  }
  function griser(b, oui) {
    b.disabled = !!oui;
    if (oui) b.setAttribute("disabled", ""); else b.removeAttribute("disabled");
  }
  function vider(n) { n.textContent = ""; }
  function montant(v) {
    v = Number(v) || 0;
    var t = v.toFixed(v !== 0 && Math.abs(v) < 0.1 ? 4 : 2);
    if (t.indexOf(".") >= 0) { t = t.replace(/0+$/, ""); if (t.split(".")[1].length < 2) t += "0".repeat(2 - t.split(".")[1].length); }
    return langue() === "en" ? t : t.replace(".", ",");
  }
  function categorie(c) { return CATEGORIES.indexOf(c) >= 0 ? T("diffusion.categorie." + c) : String(c || ""); }
  function statut(s) { return STATUTS.indexOf(s) >= 0 ? T("diffusion.statut." + s) : String(s || ""); }
  function signaler(nom) {
    try { window.dispatchEvent(new CustomEvent(nom)); } catch (e) { /* rien : l'écran garde son état */ }
  }

  // ── le réseau : délai de 30 s, réponse {ok, status, data} ; rejet {message, delai} ──
  function requete(methode, url, corps, attente) {
    var ctrl = !attente && typeof AbortController === "function" ? new AbortController() : null;
    var o = { method: methode };
    if (corps !== undefined) { o.headers = JSON_H; o.body = JSON.stringify(corps); }
    if (ctrl) o.signal = ctrl.signal;
    return new Promise(function (ok, ko) {
      var fini = false;
      var minuterie = setTimeout(function () {
        if (fini) return;
        if (attente) { attente(); return; }            // jamais abandonnée : on le dit, on attend la réponse
        fini = true;
        try { if (ctrl) ctrl.abort(); } catch (e) { /* déjà close */ }
        ko({ delai: true, message: T("diffusion.erreur.delai") });
      }, DELAI_MS);
      fetch(url, o).then(function (R) {
        return R.json().catch(function () { return {}; }).then(function (j) {
          if (fini) return;
          fini = true; clearTimeout(minuterie);
          ok({ ok: !!R.ok, status: R.status, data: j || {} });
        });
      }).catch(function (e) {
        if (fini) return;
        fini = true; clearTimeout(minuterie);
        ko({ message: String((e && e.message) || e) });
      });
    });
  }
  function detail(r) { return r && r.data ? r.data.detail : null; }
  function code(r) { var d = detail(r); return d && typeof d === "object" ? d.code || "" : ""; }
  function message(r) {
    var d = detail(r);
    if (d && typeof d === "object" && d.message) return String(d.message);
    if (typeof d === "string" && d) return d;
    return T("diffusion.erreur.http", { status: r ? r.status : 0 });
  }

  // ── règles pures ──
  function lancee(d) {
    var e = d && d.etat;
    return !!e && (e.incertain === true || e.attente_confirmation === true || (!!e.statut && RELANCABLES.indexOf(e.statut) < 0));
  }
  function utilisable(m) {
    var c = (m && m.composants) || {};
    return !!m && typeof m.nom === "string" && !!m.nom && typeof m.langue === "string" && !!m.langue && !!m.meta_id
      && (!m.statut || String(m.statut).toLowerCase() === "approved")
      && MEDIA.indexOf(c.entete) < 0 && !(c.entete === "text" && c.entete_variable);
  }
  function nomsParametres(m) {
    var n = Number(m.n_parametres) || 0;
    var noms = Array.isArray(m.noms_parametres) && m.noms_parametres.length === n ? m.noms_parametres.map(String) : [];
    if (!noms.length) for (var i = 1; i <= n; i++) noms.push(String(i));
    return noms;
  }
  function cle(m) { return m.nom + "|" + m.langue; }
  function ecartesTexte(ec) {
    var parts = [], total = 0;
    ECARTES.forEach(function (k) {
      var v = Number(ec && ec[k]) || 0;
      if (v > 0) { total += v; parts.push(T("diffusion.ecarte." + k, { n: v })); }
    });
    return total ? T("diffusion.audience.ecartes", { n: total, detail: parts.join(", ") }) : "";
  }
  function refusTexte(c) {
    return c === "consentement" || c === "prix" ? T("diffusion.refus." + c) : T("diffusion.refus.autre", { code: c });
  }

  // ── une instance par nœud ──
  function monter(elt, postId, o) {
    if (!elt || postId == null || postId === "") return Promise.resolve(null);
    o = o || {};
    var pid = String(postId);
    var deja = elt.__dzDiffusion;
    if (deja && deja.postId === pid) return deja.pret;
    var inst = { el: elt, postId: pid, compte: o.compte || "", espace: o.espace || "", jeton: 0, d: null,
                 modeles: null, modelesDe: null, noteModeles: "", occupe: false, modifie: false, choix: null, saisie: {}, msg: "", err: "" };
    elt.__dzDiffusion = inst;
    var delai = Number(o.delai) || 0;
    inst.pret = new Promise(function (ok) { delai > 0 ? setTimeout(ok, delai) : ok(); }).then(function () {
      return elt.__dzDiffusion === inst ? charger(inst, false) : null;
    });
    return inst.pret;
  }
  function base(inst) { return "/api/schedule/" + encodeURIComponent(inst.postId) + "/diffusion"; }

  function charger(inst, relire) {
    var j = ++inst.jeton;
    inst.occupe = true;
    etatSeul(inst, T("diffusion.etat.chargement"));
    return requete("GET", base(inst) + (relire ? "?relire=1" : "")).then(function (r) {
      if (j !== inst.jeton) return null;
      if (!r.ok) { inst.occupe = false; inst.err = message(r); rendreErreur(inst); return null; }
      inst.d = r.data || {};
      if (lancee(inst.d)) { inst.occupe = false; rendreSuivi(inst); return null; }
      var cid = (inst.d.config && inst.d.config.compte) || inst.compte;
      return chargerModeles(inst, cid).then(function () {
        if (j !== inst.jeton) return null;
        inst.occupe = false;
        rendreEdition(inst);
        return null;
      });
    }, function (e) {
      if (j !== inst.jeton) return null;
      inst.occupe = false; inst.err = e.message; rendreErreur(inst);
      return null;
    });
  }

  function chargerModeles(inst, cid) {
    if (!cid) { inst.modeles = null; inst.noteModeles = T("diffusion.modele.sans_compte"); return Promise.resolve(); }
    if (inst.modeles && inst.modelesDe === cid) return Promise.resolve();
    var q = inst.espace ? "?espace=" + encodeURIComponent(inst.espace) : "";
    return requete("GET", "/api/whatsapp/" + encodeURIComponent(cid) + "/modeles" + q).then(function (r) {
      if (!r.ok || !Array.isArray(r.data)) {
        inst.modeles = null; inst.noteModeles = T("diffusion.modele.illisible", { detail: r.ok ? "?" : message(r) });
        return;
      }
      inst.modeles = r.data.filter(utilisable);
      inst.modelesDe = cid;
      inst.noteModeles = inst.modeles.length ? "" : T("diffusion.modele.aucun");
    }, function (e) {
      inst.modeles = null; inst.noteModeles = T("diffusion.modele.illisible", { detail: e.message });
    });
  }

  // ── rendus ──
  function cadre(inst) {
    vider(inst.el);
    var p = el("div", S.panneau, null, { "data-dz-diffusion-panneau": inst.postId });
    p.appendChild(el("div", S.titre, T("diffusion.panneau.titre")));
    inst.el.appendChild(p);
    return p;
  }
  function pied(inst, p) {
    if (inst.msg) p.appendChild(el("div", S.msg, inst.msg, { "data-dz-diffusion-msg": "1", role: "status" }));
    if (inst.err) p.appendChild(el("div", S.erreur, inst.err, { "data-dz-diffusion-erreur": "1", role: "alert" }));
  }
  function etatSeul(inst, texte) {
    var p = cadre(inst);
    p.appendChild(el("div", S.note, texte, { "data-dz-diffusion-note": "chargement" }));
  }
  function rendreErreur(inst) {
    var p = cadre(inst);
    pied(inst, p);
    var l = el("div", S.ligne);
    l.appendChild(bouton(T("diffusion.action.relire"), "data-dz-diffusion-relire", function () { effacer(inst); charger(inst, false); }));
    p.appendChild(l);
  }
  function effacer(inst) { inst.msg = ""; inst.err = ""; }

  function rendreEdition(inst) {
    var d = inst.d || {}, cfg = d.config || null, e = d.etat || null;
    var p = cadre(inst);
    p.appendChild(el("div", S.note, T("diffusion.panneau.intro")));
    if (e && e.statut === "echec") p.appendChild(el("div", S.alerte, T("diffusion.statut.echec_note"), { "data-dz-diffusion-statut": "echec" }));
    var btn = null;
    if (!inst.modeles || !inst.modeles.length) {
      p.appendChild(el("div", S.note, inst.noteModeles || T("diffusion.modele.aucun"), { "data-dz-diffusion-note": "modeles" }));
    } else {
      var rangee = cfg && cfg.modele ? inst.modeles.filter(function (m) { return m.nom === cfg.modele.nom && m.langue === cfg.modele.langue; })[0] : null;
      if (cfg && cfg.modele && !rangee) {
        p.appendChild(el("div", S.alerte, T("diffusion.modele.plus_approuve", { nom: cfg.modele.nom, langue: cfg.modele.langue }), { "data-dz-diffusion-note": "plus_approuve" }));
      }
      if (!inst.choix || !inst.modeles.some(function (m) { return cle(m) === inst.choix; })) inst.choix = cle(rangee || inst.modeles[0]);
      var sel = el("select", S.champ, null, { "data-dz-diffusion-modele": "1" });
      inst.modeles.forEach(function (m) {
        var op = el("option", "", T("diffusion.modele.option", { nom: m.nom, langue: m.langue, categorie: categorie(m.categorie) }));
        op.value = cle(m);
        op.setAttribute("value", cle(m));
        sel.appendChild(op);
      });
      sel.value = inst.choix;
      var lab = el("label", S.etiquette);
      lab.appendChild(el("span", "", T("diffusion.modele.choisir")));
      lab.appendChild(sel);
      p.appendChild(lab);
      var cat = el("div", S.note, null, { "data-dz-diffusion-categorie": "1" });
      p.appendChild(cat);
      var zone = el("div", "display:flex;flex-direction:column;gap:5px", null, { "data-dz-diffusion-params": "1" });
      p.appendChild(zone);
      var champs = [];
      var remplir = function () {
        var m = inst.modeles.filter(function (x) { return cle(x) === inst.choix; })[0];
        cat.textContent = T("diffusion.modele.categorie", { categorie: categorie(m.categorie) });
        vider(zone);
        champs = [];
        var nommes = m.parametres === "nommes";
        var avant = cfg && cfg.modele && cle(cfg.modele) === cle(m) ? cfg.parametres : null;
        nomsParametres(m).forEach(function (n, i) {
          var c = el("input", S.champ, null, { "data-dz-diffusion-param": n });
          c.type = "text";
          var saisi = (inst.saisie[cle(m)] || {})[n];
          var v = saisi != null ? saisi : avant == null ? "" : nommes ? (avant[n] == null ? "" : avant[n]) : (avant[i] == null ? "" : avant[i]);
          c.value = String(v);
          c.addEventListener("input", function () {
            (inst.saisie[cle(m)] = inst.saisie[cle(m)] || {})[n] = String(c.value == null ? "" : c.value);   // gardée d'un rendu à l'autre
            inst.modifie = true; etatBouton();
          });
          var l = el("label", S.etiquette);
          l.appendChild(el("span", "", T(nommes ? "diffusion.parametre.nomme" : "diffusion.parametre.position", { nom: n })));
          l.appendChild(c);
          zone.appendChild(l);
          champs.push([n, c]);
        });
        if (!champs.length) zone.appendChild(el("div", S.note, T("diffusion.parametre.aucun"), { "data-dz-diffusion-note": "sans_parametre" }));
        inst.lireChamps = function () { return { m: m, nommes: nommes, champs: champs }; };
      };
      sel.addEventListener("change", function () { inst.choix = sel.value; inst.modifie = true; remplir(); etatBouton(); });
      remplir();
    }
    // l'audience et le devis de la config RANGÉE (recalculés par le serveur)
    var aud = el("div", "display:flex;flex-direction:column;gap:3px", null, { "data-dz-diffusion-audience": "1" });
    var vide = false;
    if (d.refus) {
      aud.appendChild(el("div", S.alerte, T("diffusion.audience.refus", { detail: refusTexte(d.refus) })));
    } else if (d.audience) {
      var n = Number(d.audience.n) || 0;
      aud.appendChild(el("div", "", T("diffusion.audience.n", { n: n })));
      var ec = ecartesTexte(d.audience.ecartes);
      if (ec) aud.appendChild(el("div", S.note, ec, { "data-dz-diffusion-ecartes": "1" }));
      if (cfg && cfg.n_identites != null) aud.appendChild(el("div", S.note, T("diffusion.audience.liste", { n: cfg.n_identites })));
      if (!n) { vide = true; aud.appendChild(el("div", S.alerte, T("diffusion.audience.vide"), { "data-dz-diffusion-vide": "1", role: "alert" })); }
    } else {
      aud.appendChild(el("div", S.note, T("diffusion.audience.apres")));
    }
    p.appendChild(aud);
    if (d.devis && !d.refus) p.appendChild(el("div", "", T("diffusion.devis.montant", { montant: montant(d.devis.usd) }), { "data-dz-diffusion-devis": "1" }));
    if (inst.modeles && inst.modeles.length) {
      var l = el("div", S.ligne);
      btn = bouton(T("diffusion.action.enregistrer"), "data-dz-diffusion-enregistrer", function () { enregistrer(inst); });
      l.appendChild(btn);
      p.appendChild(l);
    }
    function etatBouton() { if (btn) griser(btn, inst.occupe || (vide && !inst.modifie)); }
    inst.etatBouton = etatBouton;
    etatBouton();
    pied(inst, p);
  }

  async function enregistrer(inst) {
    if (inst.occupe || !inst.lireChamps) return;
    effacer(inst);
    var lu = inst.lireChamps();
    var valeurs = lu.nommes ? {} : [];
    for (var i = 0; i < lu.champs.length; i++) {
      var v = String(lu.champs[i][1].value == null ? "" : lu.champs[i][1].value);
      if (!v.trim()) { inst.err = T("diffusion.parametre.vide"); rendreEdition(inst); return; }
      if (lu.nommes) valeurs[lu.champs[i][0]] = v; else valeurs.push(v);
    }
    var cfg = inst.d && inst.d.config;
    if (cfg && cfg.n_identites != null) {
      if (!window.__dzDialogue || typeof window.__dzDialogue.confirmer !== "function") { inst.err = T("diffusion.confirmer.sans_dialogue"); rendreEdition(inst); return; }
      var elargir = await window.__dzDialogue.confirmer(T("diffusion.liste.texte", { n: cfg.n_identites }),
        { titre: T("diffusion.liste.titre"), ok: T("diffusion.liste.ok"), annuler: T("diffusion.confirmer.annuler") });
      if (!elargir) return;
    }
    var j = ++inst.jeton;
    inst.occupe = true;
    if (inst.etatBouton) inst.etatBouton();
    var corps = { modele: { nom: lu.m.nom, langue: lu.m.langue }, parametres: valeurs };
    return requete("PUT", base(inst), corps).then(function (r) {
      if (j !== inst.jeton) return;
      inst.occupe = false;
      if (!r.ok) {
        inst.err = message(r);
        if (r.status === 409 && (code(r) === "deja_lancee" || code(r) === "incertain")) { var err = inst.err; return charger(inst, false).then(function () { inst.err = err; rerendre(inst); }); }
        rendreEdition(inst);
        return;
      }
      var res = r.data || {};
      inst.d = { config: res.config || null, audience: res.audience || null, devis: res.devis || null, refus: null, etat: (inst.d && inst.d.etat) || null };
      inst.modifie = false;
      inst.msg = T("diffusion.etat.enregistree");
      signaler("deepotus:schedule-recharger");                // le PUT efface la validation : la liste relit le post
      rendreEdition(inst);
    }, function (e) {
      if (j !== inst.jeton) return;
      inst.occupe = false; inst.err = e.message; rendreEdition(inst);
    });
  }
  function rerendre(inst) { if (lancee(inst.d)) rendreSuivi(inst); else rendreEdition(inst); }

  function rendreSuivi(inst) {
    var e = (inst.d && inst.d.etat) || {};
    var p = cadre(inst);
    p.appendChild(el("div", "", T("diffusion.statut.ligne", { statut: statut(e.statut) }) + " · " + T("diffusion.suivi.n", { n: Number(e.n) || 0 }),
      { "data-dz-diffusion-statut": String(e.statut || "") }));
    var c = e.compteurs || {};
    var cpt = el("div", S.ligne, null, { "data-dz-diffusion-compteurs": "1" });
    COMPTEURS.forEach(function (k) {
      var v = 0;
      for (var i = 0; i < k[1].length; i++) if (c[k[1][i]] != null) { v = Number(c[k[1][i]]) || 0; break; }
      cpt.appendChild(el("span", S.note, T("diffusion.compteur." + k[0], { n: v }), { "data-dz-diffusion-compteur": k[0] }));
    });
    p.appendChild(cpt);
    if (e.reel_usd != null) p.appendChild(el("div", S.note, T("diffusion.suivi.reel", { montant: montant(e.reel_usd) }), { "data-dz-diffusion-reel": "1" }));
    var l = el("div", S.ligne);
    if (e.incertain === true || e.attente_confirmation === true) {
      var boite = el("div", S.alerte, null, { "data-dz-diffusion-incertain": e.attente_confirmation === true ? "attente" : "incertain", role: "alert" });
      boite.appendChild(el("div", "", T(e.attente_confirmation === true ? "diffusion.incertain.attente" : "diffusion.incertain.texte")));
      p.appendChild(boite);
      var bc = bouton(T("diffusion.action.confirmer"), "data-dz-diffusion-confirmer", function () { confirmer(inst); });
      griser(bc, inst.occupe);
      l.appendChild(bc);
    }
    var br = bouton(T("diffusion.action.relire"), "data-dz-diffusion-relire", function () { effacer(inst); charger(inst, true); });
    griser(br, inst.occupe);
    l.appendChild(br);
    p.appendChild(l);
    pied(inst, p);
  }

  async function confirmer(inst) {
    if (inst.occupe) return;
    effacer(inst);
    if (!window.__dzDialogue || typeof window.__dzDialogue.confirmer !== "function") {
      inst.err = T("diffusion.confirmer.sans_dialogue"); rendreSuivi(inst); return;
    }
    var oui = await window.__dzDialogue.confirmer(T("diffusion.confirmer.texte"),
      { titre: T("diffusion.confirmer.titre"), ok: T("diffusion.confirmer.ok"), annuler: T("diffusion.confirmer.annuler"), danger: true });
    if (!oui || inst.occupe) return;
    var j = ++inst.jeton;
    inst.occupe = true;
    inst.msg = T("diffusion.etat.envoi");
    rendreSuivi(inst);
    return requete("POST", base(inst) + "/confirmer", { confirme_incertain: true }, function () {
      if (j !== inst.jeton) return;
      inst.msg = ""; inst.err = T("diffusion.erreur.attente"); rendreSuivi(inst);
    }).then(function (r) {
      if (j !== inst.jeton) return;
      inst.occupe = false;
      if (!r.ok) {
        inst.msg = ""; inst.err = message(r);
        if (r.status === 409 && code(r) === "pas_incertaine") { var err = inst.err; return charger(inst, false).then(function () { inst.err = err; rerendre(inst); }); }
        rendreSuivi(inst);
        return;
      }
      signaler("deepotus:schedule-recharger");                // le post a pu partir (posted, remote_ids)
      return charger(inst, false).then(function () { inst.msg = T("diffusion.etat.confirmee"); rerendre(inst); });
    }, function (e) {
      if (j !== inst.jeton) return;
      inst.occupe = false; inst.msg = ""; inst.err = e.message; rendreSuivi(inst);
    });
  }

  window.__dzDiffusionWhatsapp = { monter: monter, _regles: { lancee: lancee, utilisable: utilisable, montant: montant, ecartesTexte: ecartesTexte } };
})();
