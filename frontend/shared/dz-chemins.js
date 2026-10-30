/* dz-chemins.js — les EMPLACEMENTS de Réglages › Chemins (t378, lot « Réglages : chemins & apparence », 30/10/2026,
   plan docs/superpowers/plans/2026-10-29-finitions-esthetiques-chemins-fils-apparence.md, décisions D2 et D3).
   SOURCE : frontend/shared/dz-chemins.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-chemins.js, servie à
   /shared/dz-chemins.js, chargée par une balise classique dans la SPA (frontend/dist/index.html).
   Serveur : backend/app/services/emplacements.py, routes /api/reglages/chemins (settings_routes.py).
   Bancs : frontend/shared/qa/chemins.test.mjs, backend/tests/test_emplacements_ecran.py.

   Deux surfaces, vanilla DOM, aucun innerHTML :
   1. window.__dzChemins.monter(hote) — sous les dossiers de Réglages › Chemins (le maillon de queue
      scripts/patch_bundle_dzchemins.py rend un <div data-dz-chemins-hote> et appelle monter par une ref) : la liste
      des emplacements (nom, adresse, rôles, dernier test et espace libre), « Ajouter un emplacement », le formulaire
      (nom, type dossier / SFTP, adresse, mot de passe au coffre jamais réaffiché, clé SSH, rôles cochables),
      « Tester » (avant ou après l'enregistrement), « Modifier », « Supprimer » derrière __dzDialogue.confirmer.
   2. window.__dzChemins.diag(hote) — dans le Diagnostic (même maillon, <div data-dz-chemins-diag>) : chaque
      emplacement joignable ou non ; rien du tout tant qu'aucun emplacement n'existe.
   Textes : clés chemins.* (frontend/shared/i18n/chemins.json) ; l'état d'un test arrive en CODE (chemins.etat.*).
   Charte : aucun arrondi, IBM Plex Mono en capitales pour les titres, jetons --srf-* / --brd-* / --txt-* avec repli. */
(function () {
  "use strict";
  if (window.__dzChemins) return;

  var BASE = "/api/reglages/chemins";
  var JSON_H = { "Content-Type": "application/json" };
  var ROLES = ["sauvegarde", "miroir", "bibliotheque"];
  var S = {
    panneau: "display:flex;flex-direction:column;gap:10px;margin-top:28px;color:var(--txt-base,var(--ink,#cfd6e2));font:13px/1.5 system-ui,sans-serif",
    titre: "font:600 16px/1.3 system-ui,sans-serif;color:var(--txt-hi,var(--ink-strong,#e6e9ee))",
    intro: "font-size:12px;color:var(--txt-mid,var(--ink-soft,#9aa4ae));max-width:680px",
    cadre: "border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));background:var(--srf-panel,var(--bg-panel,#13171c));padding:0;display:flex;flex-direction:column",
    ligne: "display:grid;grid-template-columns:minmax(150px,200px) 1fr auto;gap:14px;align-items:center;padding:12px 16px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
    nom: "font-size:12.5px;color:var(--txt-hi,var(--ink-strong,#e6e9ee))",
    petit: "font-size:10.5px;color:var(--txt-mid,var(--ink-soft,#9aa4ae))",
    mono: "font:11px/1.45 'IBM Plex Mono',monospace;color:var(--txt-base,var(--ink,#cfd6e2));word-break:break-all",
    tete: "font:10px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    boutons: "display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end",
    btn: "height:26px;padding:0 10px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit;font-size:12px",
    primaire: "background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6);color:var(--accent-ink,#ffffff)",
    form: "border:1px solid var(--amber,#f0b429);background:var(--srf-panel,var(--bg-panel,#13171c));padding:14px 16px;display:flex;flex-direction:column;gap:10px",
    grille: "display:grid;grid-template-columns:160px 1fr;gap:8px 12px;align-items:center",
    champ: "height:28px;padding:0 8px;border-radius:0;background:var(--srf-sunken,var(--bg-base,#0d1014));border:1px solid var(--brd-soft,var(--stroke,#222830));color:var(--txt-hi,var(--ink-strong,#e6e9ee));font:12px 'IBM Plex Mono',monospace;min-width:0",
    ok: "color:var(--green,#3fb950)",
    ko: "color:var(--red,#e5484d)",
    neutre: "color:var(--txt-mid,var(--ink-muted,#9aa4ae))"
  };

  function T(cle, v) { return typeof window.dzT === "function" ? window.dzT(cle, v) : cle; }
  function langue() { var l = typeof window.dzLang === "function" ? window.dzLang() : window.dzLang; return l === "en" ? "en" : "fr"; }
  function el(tag, attrs, texte) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (texte != null) n.textContent = texte;
    return n;
  }
  function vider(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function bouton(texte, action, primaire) {
    var b = el("button", { type: "button", style: S.btn + (primaire ? ";" + S.primaire : ""), "data-dz-chemins-action": action }, texte);
    return b;
  }
  function octets(n) {
    if (n == null) return "";
    var u = langue() === "en" ? ["B", "KB", "MB", "GB", "TB"] : ["o", "Ko", "Mo", "Go", "To"], i = 0, v = Number(n);
    while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
    var t = (i ? v.toFixed(1) : String(Math.round(v)));
    return (langue() === "en" ? t : t.replace(".", ",")) + " " + u[i];
  }
  function etat(r) {
    if (!r) return T("chemins.etat.jamais");
    var t = T("chemins.etat." + (r.code || "echec"));
    if (r.code === "echec" && r.detail) t += " : " + r.detail;
    if (r.libre_octets != null) t += " · " + T("chemins.etat.libre", { libre: octets(r.libre_octets) });
    return t;
  }
  function date(iso) {
    var d = new Date(String(iso || ""));
    if (isNaN(d.getTime())) return String(iso || "");
    return d.toLocaleString(langue() === "en" ? "en-GB" : "fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  }
  function teinte(r) { return !r ? S.neutre : (r.ok ? S.ok : S.ko); }
  function appel(methode, url, corps) {
    var o = { method: methode, headers: JSON_H };
    if (corps !== undefined) o.body = JSON.stringify(corps);
    return window.fetch(url, o).then(function (R) {
      return R.json().catch(function () { return {}; }).then(function (j) {
        if (!R.ok) throw new Error(String((j && j.detail) || R.status));
        return j;
      });
    });
  }

  // ── 1. Réglages › Chemins ──────────────────────────────────────────────────────────────────────────────────────

  function Panneau(hote) {
    this.hote = hote;
    this.donnees = null;
    this.form = null;                   // null | {id?: string, champs: {...}}
    this.message = null;                // {ok, texte}
    this.tests = {};                    // id -> « en cours »
    this.operations = {};               // t379 : id -> {ok, texte} de « Sauvegarder maintenant »
    this.galerie = null;                // t379 : l'emplacement dont la source est parcourue
    this.roles = {};
  }

  Panneau.prototype.charger = function () {
    var p = this;
    // t379 : l'état des rôles (dernière sauvegarde, index) arrive à part ; s'il manque, la liste s'affiche quand même
    var etatRoles = appel("GET", BASE + "/etat").catch(function () { return {}; });
    return appel("GET", BASE).then(function (j) {
      return etatRoles.then(function (er) { p.donnees = j; p.roles = (er && er.emplacements) || {}; p.garder = er && er.garder; p.dessiner(); });
    }).catch(function (e) { p.donnees = { erreur: String(e.message || e) }; p.dessiner(); });
  };

  Panneau.prototype.dessiner = function () {
    var p = this, h = this.hote;
    vider(h);
    var box = el("div", { style: S.panneau, "data-dz-chemins": "panneau" });
    box.appendChild(el("div", { style: S.titre }, T("chemins.emplacements.titre")));
    box.appendChild(el("div", { style: S.intro }, T("chemins.emplacements.aide")));
    var d = this.donnees;
    if (!d) { box.appendChild(el("div", { style: S.petit }, T("chemins.emplacements.chargement"))); h.appendChild(box); return; }
    if (d.erreur) {
      box.appendChild(el("div", { style: S.ko }, T("chemins.emplacements.indisponible", { erreur: d.erreur })));
      h.appendChild(box); return;
    }
    if (d.sftp_disponible === false) box.appendChild(el("div", { style: S.petit + ";" + S.ko }, T("chemins.sftp.absent")));
    var liste = el("div", { style: S.cadre, "data-dz-chemins": "liste" });
    if (!d.emplacements.length) {
      liste.appendChild(el("div", { style: "padding:12px 16px;" + S.petit }, T("chemins.emplacements.vide")));
    }
    d.emplacements.forEach(function (e, i) {
      var l = el("div", { style: S.ligne + (i ? "" : ";border-top:none"), "data-dz-chemin-id": e.id });
      var g = el("div");
      g.appendChild(el("div", { style: S.nom }, e.nom));
      g.appendChild(el("div", { style: S.petit }, T("chemins.type." + e.type)));
      l.appendChild(g);
      var m = el("div", { style: "display:flex;flex-direction:column;gap:2px;min-width:0" });
      m.appendChild(el("div", { style: S.mono }, e.adresse));
      m.appendChild(el("div", { style: S.petit, "data-dz-chemins": "roles" }, e.roles.length
        ? e.roles.map(function (r) { return T("chemins.role." + r); }).join(" · ") : T("chemins.role.aucun")));
      m.appendChild(el("div", { style: "font-size:11px;" + (p.tests[e.id] ? S.neutre : teinte(e.dernier_test)), "data-dz-chemins": "etat" },
        p.tests[e.id] ? T("chemins.action.test_en_cours") : etat(e.dernier_test)));
      var er = (p.roles || {})[e.id] || {};
      if (e.roles.indexOf("sauvegarde") >= 0) {
        var sv = er.sauvegarde;
        var ls = sv && sv.derniere ? T("chemins.sauvegarde.derniere", { quand: date(sv.derniere), garder: p.garder || 7 })
                                   : T("chemins.sauvegarde.jamais");
        if (sv && sv.ok === false) ls += " · " + T("chemins.sauvegarde.echec", { etat: T("chemins.etat." + (sv.code || "echec")) });
        m.appendChild(el("div", { style: "font-size:11px;" + (sv && sv.ok === false ? S.ko : S.neutre), "data-dz-chemins": "sauvegarde" }, ls));
      }
      if (e.roles.indexOf("bibliotheque") >= 0) {
        var ix = er.index;
        var li = ix && ix.quand ? T("chemins.index.etat", { n: ix.fichiers, quand: date(ix.quand) }) : T("chemins.index.jamais");
        if (ix && ix.erreur) li += " · " + T("chemins.sauvegarde.echec", { etat: T("chemins.etat." + ix.erreur) });
        m.appendChild(el("div", { style: "font-size:11px;" + (ix && ix.erreur ? S.ko : S.neutre), "data-dz-chemins": "index" }, li));
      }
      var op = p.operations[e.id];
      if (op) m.appendChild(el("div", { style: "font-size:11px;" + (op.ok === false ? S.ko : op.ok ? S.ok : S.neutre),
                                         "data-dz-chemins": "operation" }, op.texte));
      l.appendChild(m);
      var bs = el("div", { style: S.boutons });
      if (e.roles.indexOf("sauvegarde") >= 0) {
        var bsv = bouton(T("chemins.sauvegarde.maintenant"), "sauvegarder");
        bsv.title = T("chemins.sauvegarde.maintenant_aide");
        bsv.disabled = !!op && op.ok == null;
        bsv.addEventListener("click", function () { p.sauvegarder(e.id); });
        bs.appendChild(bsv);
      }
      if (e.roles.indexOf("bibliotheque") >= 0) {
        var bpa = bouton(T(p.galerie === e.id ? "chemins.biblio.fermer" : "chemins.biblio.parcourir"), "parcourir");
        bpa.addEventListener("click", function () { p.galerie = p.galerie === e.id ? null : e.id; p.dessiner(); });
        bs.appendChild(bpa);
      }
      var bt = bouton(T("chemins.action.tester"), "tester");
      bt.title = T("chemins.action.tester_aide");
      bt.disabled = !!p.tests[e.id];
      bt.addEventListener("click", function () { p.tester(e.id); });
      var bm = bouton(T("chemins.action.modifier"), "modifier");
      bm.addEventListener("click", function () { p.ouvrir(e); });
      var bx = bouton(T("chemins.action.supprimer"), "supprimer");
      bx.addEventListener("click", function () { p.supprimer(e); });
      bs.appendChild(bt); bs.appendChild(bm); bs.appendChild(bx);
      l.appendChild(bs);
      liste.appendChild(l);
    });
    box.appendChild(liste);
    if (this.galerie && d.emplacements.some(function (e) { return e.id === p.galerie; })) {
      var gh = el("div", { "data-dz-chemins": "galerie-hote" });
      box.appendChild(gh);
      galerie(gh, this.galerie, function () { p.charger(); });
    }
    if (this.form) box.appendChild(this.dessinerForm());
    else {
      var ba = bouton(T("chemins.emplacements.ajouter"), "ajouter", true);
      ba.style.alignSelf = "flex-start";
      ba.addEventListener("click", function () { p.ouvrir(null); });
      box.appendChild(ba);
    }
    if (this.message && !this.form) box.appendChild(el("div", { style: "font-size:12px;" + (this.message.ok ? S.ok : S.ko),
                                                                 "data-dz-chemins": "message" }, this.message.texte));
    h.appendChild(box);
  };

  Panneau.prototype.ouvrir = function (e) {
    this.message = null;
    this.form = e ? { id: e.id, secret_pose: !!e.secret_pose, champs: {
      nom: e.nom, type: e.type, chemin: e.chemin || "", hote: e.hote || "", port: String(e.port || 22),
      utilisateur: e.utilisateur || "", dossier_distant: e.dossier_distant || "/", cle_ssh: e.cle_ssh || "",
      secret: "", effacer_secret: false, roles: e.roles.slice() } }
      : { champs: { nom: "", type: "dossier", chemin: "", hote: "", port: "22", utilisateur: "", dossier_distant: "/",
                    cle_ssh: "", secret: "", effacer_secret: false, roles: [] } };
    this.dessiner();
  };

  Panneau.prototype.corps = function () {
    var c = this.form.champs, b = { nom: c.nom, roles: c.roles.slice() };
    if (!this.form.id) b.type = c.type;
    if (c.type === "dossier") b.chemin = c.chemin;
    else {
      b.hote = c.hote; b.port = c.port; b.utilisateur = c.utilisateur; b.dossier_distant = c.dossier_distant;
      b.cle_ssh = c.cle_ssh;
      if (c.secret) b.secret = c.secret;
      if (this.form.id && c.effacer_secret && !c.secret) b.effacer_secret = true;
    }
    return b;
  };

  Panneau.prototype.dessinerForm = function () {
    var p = this, f = this.form, c = f.champs;
    var box = el("div", { style: S.form, "data-dz-chemins": "form" });
    var g = el("div", { style: S.grille });
    function rangee(cle, noeud) { g.appendChild(el("label", { style: S.petit }, T(cle))); g.appendChild(noeud); return noeud; }
    function saisie(cle, nomChamp, type, aide) {
      var i = el("input", { style: S.champ, type: type || "text", "data-dz-chemins-champ": nomChamp, autocomplete: "off",
                            spellcheck: "false" });
      i.value = c[nomChamp];
      if (aide) i.placeholder = T(aide);
      i.addEventListener("input", function () { c[nomChamp] = i.value; });
      return rangee(cle, i);
    }
    saisie("chemins.champ.nom", "nom", "text", "chemins.champ.nom_aide");
    var sel = el("select", { style: S.champ, "data-dz-chemins-champ": "type" });
    ["dossier", "sftp"].forEach(function (t) { var o = el("option", { value: t }, T("chemins.type." + t)); sel.appendChild(o); });
    sel.value = c.type;
    sel.disabled = !!f.id;
    sel.addEventListener("change", function () { c.type = sel.value; p.dessiner(); });
    rangee("chemins.champ.type", sel);
    if (c.type === "dossier") saisie("chemins.champ.chemin", "chemin", "text", "chemins.champ.chemin_aide");
    else {
      saisie("chemins.champ.hote", "hote");
      saisie("chemins.champ.port", "port", "number");
      saisie("chemins.champ.utilisateur", "utilisateur");
      saisie("chemins.champ.distant", "dossier_distant");
      var s = saisie("chemins.champ.secret", "secret", "password", f.secret_pose ? "chemins.champ.secret_garde" : "chemins.champ.secret_aide");
      s.setAttribute("autocomplete", "new-password");
      if (f.secret_pose) {
        var lab = el("label", { style: S.petit + ";display:flex;gap:6px;align-items:center" });
        var cb = el("input", { type: "checkbox", "data-dz-chemins-champ": "effacer_secret" });
        cb.checked = !!c.effacer_secret;
        cb.addEventListener("change", function () { c.effacer_secret = cb.checked; });
        lab.appendChild(cb); lab.appendChild(document.createTextNode(T("chemins.champ.secret_effacer")));
        g.appendChild(el("span")); g.appendChild(lab);
      }
      saisie("chemins.champ.cle_ssh", "cle_ssh");
    }
    var roles = el("div", { style: "display:flex;flex-direction:column;gap:4px", "data-dz-chemins": "roles-choix" });
    ROLES.forEach(function (r) {
      var lab = el("label", { style: "display:flex;gap:8px;align-items:baseline;font-size:12px", title: T("chemins.role." + r + "_aide") });
      var cb = el("input", { type: "checkbox", value: r, "data-dz-chemins-role": r });
      cb.checked = c.roles.indexOf(r) >= 0;
      cb.addEventListener("change", function () {
        c.roles = ROLES.filter(function (x) { return x === r ? cb.checked : c.roles.indexOf(x) >= 0; });
      });
      lab.appendChild(cb);
      lab.appendChild(el("span", null, T("chemins.role." + r)));
      lab.appendChild(el("span", { style: S.petit }, T("chemins.role." + r + "_aide")));
      roles.appendChild(lab);
    });
    rangee("chemins.champ.roles", roles);
    box.appendChild(g);
    var bs = el("div", { style: S.boutons + ";justify-content:flex-start" });
    var bt = bouton(T("chemins.action.tester"), "tester-form");
    bt.title = T("chemins.action.tester_aide");
    bt.addEventListener("click", function () { p.testerForm(); });
    var be = bouton(T("chemins.action.enregistrer"), "enregistrer", true);
    be.addEventListener("click", function () { p.enregistrer(); });
    var ba = bouton(T("chemins.action.annuler"), "annuler");
    ba.addEventListener("click", function () { p.form = null; p.message = null; p.dessiner(); });
    bs.appendChild(bt); bs.appendChild(be); bs.appendChild(ba);
    box.appendChild(bs);
    if (this.message) box.appendChild(el("div", { style: "font-size:12px;" + (this.message.ok ? S.ok : this.message.ok === false ? S.ko : S.neutre),
                                                   "data-dz-chemins": "message" }, this.message.texte));
    return box;
  };

  Panneau.prototype.testerForm = function () {
    var p = this, f = this.form;
    this.message = { ok: null, texte: T("chemins.action.test_en_cours") };
    this.dessiner();
    // un emplacement déjà enregistré dont on n'a pas retapé le mot de passe : on teste CELUI du coffre
    var avecCoffre = f.id && f.secret_pose && !f.champs.secret && !f.champs.effacer_secret;
    var req = avecCoffre ? appel("POST", BASE + "/" + encodeURIComponent(f.id) + "/tester")
                         : appel("POST", BASE + "/tester", Object.assign({ type: f.champs.type }, this.corps()));
    return req.then(function (r) { p.message = { ok: !!r.ok, texte: etat(r) }; p.dessiner(); })
      .catch(function (e) { p.message = { ok: false, texte: T("chemins.erreur.generique", { erreur: e.message || e }) }; p.dessiner(); });
  };

  Panneau.prototype.enregistrer = function () {
    var p = this, f = this.form;
    var req = f.id ? appel("POST", BASE + "/" + encodeURIComponent(f.id), this.corps()) : appel("POST", BASE, this.corps());
    return req.then(function () { p.form = null; p.message = null; return p.charger(); })
      .catch(function (e) { p.message = { ok: false, texte: T("chemins.erreur.generique", { erreur: e.message || e }) }; p.dessiner(); });
  };

  Panneau.prototype.tester = function (id) {
    var p = this;
    this.tests[id] = true;
    this.dessiner();
    return appel("POST", BASE + "/" + encodeURIComponent(id) + "/tester")
      .then(function () { delete p.tests[id]; return p.charger(); })
      .catch(function (e) { delete p.tests[id]; p.message = { ok: false, texte: T("chemins.erreur.generique", { erreur: e.message || e }) }; p.dessiner(); });
  };

  Panneau.prototype.sauvegarder = function (id) {
    var p = this;
    this.operations[id] = { ok: null, texte: T("chemins.sauvegarde.en_cours") };
    this.dessiner();
    return appel("POST", BASE + "/" + encodeURIComponent(id) + "/sauvegarder").then(function (r) {
      p.operations[id] = r.ok ? { ok: true, texte: T("chemins.sauvegarde.faite", { nom: r.nom }) }
                              : { ok: false, texte: T("chemins.sauvegarde.echec", { etat: etat(r) }) };
      return p.charger();
    }).catch(function (e) { p.operations[id] = { ok: false, texte: T("chemins.erreur.generique", { erreur: e.message || e }) }; p.dessiner(); });
  };

  Panneau.prototype.supprimer = function (e) {
    var p = this;
    var dlg = window.__dzDialogue;
    var oui = dlg && dlg.confirmer ? dlg.confirmer(T("chemins.action.supprimer_confirmer", { nom: e.nom })) : Promise.resolve(false);
    return Promise.resolve(oui).then(function (v) {
      if (!v) return null;
      return appel("DELETE", BASE + "/" + encodeURIComponent(e.id)).then(function () { return p.charger(); })
        .catch(function (er) { p.message = { ok: false, texte: T("chemins.erreur.generique", { erreur: er.message || er }) }; p.dessiner(); });
    });
  };

  function monter(hote) {
    if (!hote || hote.__dzChemins) return hote && hote.__dzChemins;
    var p = new Panneau(hote);
    hote.__dzChemins = p;
    p.dessiner();
    p.charger();
    return p;
  }

  // ── t379 : la GALERIE d'une source de bibliothèque (Réglages › Chemins et Bibliothèque) ─────────────────────────
  // Lecture seule : les vignettes passent par GET …/fichier (confiné à l'index) ; « Importer » COPIE une image ou un
  // son dans la Bibliothèque ; « Indexer » relit la source sans rien y écrire.
  var PAGE = 48;
  var IMPORTABLES = /\.(png|jpe?g|webp|mp3|wav|ogg|flac|m4a)$/i;
  function galerie(hote, eid, apres) {
    var g = { idx: null, filtre: "", n: PAGE, messages: {}, occupe: false, erreur: null };
    var racine = BASE + "/" + encodeURIComponent(eid);
    function url(ch) { return racine + "/fichier?chemin=" + encodeURIComponent(ch); }
    function dessiner() {
      vider(hote);
      var box = el("div", { style: S.cadre + ";padding:12px 14px;gap:10px", "data-dz-chemins": "galerie", "data-dz-chemins-source": eid });
      var tete = el("div", { style: "display:flex;gap:8px;align-items:center;flex-wrap:wrap" });
      tete.appendChild(el("div", { style: S.tete + ";flex:1" }, T("chemins.biblio.titre")));
      var f = el("input", { style: S.champ + ";width:200px", type: "search", "data-dz-chemins-champ": "filtre" });
      f.placeholder = T("chemins.biblio.filtrer");
      f.value = g.filtre;
      f.addEventListener("input", function () { g.filtre = f.value; g.n = PAGE; grilleDessiner(); });
      tete.appendChild(f);
      var bi = bouton(T("chemins.index.indexer"), "indexer");
      bi.title = T("chemins.index.indexer_aide");
      bi.disabled = g.occupe;
      bi.addEventListener("click", function () {
        g.occupe = true; dessiner();
        appel("POST", racine + "/indexer").then(function (r) {
          g.occupe = false;
          if (!r.ok) { g.erreur = T("chemins.erreur.generique", { erreur: etat(r) }); dessiner(); return; }
          g.erreur = null; g.idx = r; dessiner(); if (apres) apres();
        }).catch(function (e) { g.occupe = false; g.erreur = T("chemins.erreur.generique", { erreur: e.message || e }); dessiner(); });
      });
      tete.appendChild(bi);
      box.appendChild(tete);
      box.appendChild(el("div", { style: S.petit }, T("chemins.biblio.aide")));
      if (g.erreur) box.appendChild(el("div", { style: "font-size:12px;" + S.ko, "data-dz-chemins": "message" }, g.erreur));
      var grille = el("div", { style: "display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:8px", "data-dz-chemins": "grille" });
      var pied = el("div");
      box.appendChild(grille);
      box.appendChild(pied);
      hote.appendChild(box);
      function grilleDessiner() {
        vider(grille); vider(pied);
        if (!g.idx) { grille.appendChild(el("div", { style: S.petit }, T("chemins.emplacements.chargement"))); return; }
        var q = g.filtre.toLowerCase();
        var tous = (g.idx.fichiers || []).filter(function (x) { return !q || x.chemin.toLowerCase().indexOf(q) >= 0; });
        if (!tous.length) grille.appendChild(el("div", { style: S.petit }, T(g.idx.quand ? "chemins.biblio.vide" : "chemins.index.jamais")));
        tous.slice(0, g.n).forEach(function (x) { grille.appendChild(carte(x)); });
        if (tous.length > g.n) {
          var plus = bouton(T("chemins.biblio.plus", { n: tous.length - g.n }), "plus");
          plus.addEventListener("click", function () { g.n += PAGE; grilleDessiner(); });
          pied.appendChild(plus);
        }
      }
      function carte(x) {
        var c = el("div", { style: "border:1px solid var(--brd-soft,var(--stroke,#222830));display:flex;flex-direction:column;min-width:0",
                            "data-dz-chemins-fichier": x.chemin });
        if (x.genre === "image") {
          c.appendChild(el("img", { src: url(x.chemin), alt: "", loading: "lazy", decoding: "async",
                                    style: "width:100%;aspect-ratio:1 / 1;object-fit:cover;display:block;background:var(--srf-sunken,var(--bg-base,#0d1014))" }));
        } else {
          c.appendChild(el("div", { style: "aspect-ratio:1 / 1;display:flex;align-items:center;justify-content:center;" + S.tete },
            T("chemins.biblio.genre_" + x.genre)));
        }
        var bas = el("div", { style: "padding:4px 6px;display:flex;flex-direction:column;gap:3px" });
        bas.appendChild(el("div", { style: S.mono + ";font-size:10.5px", title: x.chemin }, x.chemin.split("/").pop()));
        bas.appendChild(el("div", { style: S.petit }, octets(x.octets)));
        if (IMPORTABLES.test(x.chemin)) {
          var msg = g.messages[x.chemin];
          var b = bouton(T("chemins.biblio.importer"), "importer");
          b.title = T("chemins.biblio.importer_aide");
          b.disabled = !!msg && msg.ok !== false;
          b.addEventListener("click", function () {
            g.messages[x.chemin] = { ok: null, texte: T("chemins.biblio.import_en_cours") }; grilleDessiner();
            appel("POST", racine + "/importer", { chemin: x.chemin }).then(function () {
              g.messages[x.chemin] = { ok: true, texte: T("chemins.biblio.importe") }; grilleDessiner();
            }).catch(function (e) { g.messages[x.chemin] = { ok: false, texte: T("chemins.erreur.generique", { erreur: e.message || e }) }; grilleDessiner(); });
          });
          bas.appendChild(b);
          if (msg) bas.appendChild(el("div", { style: "font-size:10.5px;" + (msg.ok ? S.ok : msg.ok === false ? S.ko : S.neutre) }, msg.texte));
        }
        c.appendChild(bas);
        return c;
      }
      grilleDessiner();
    }
    dessiner();
    return appel("GET", racine + "/index").then(function (j) { g.idx = j; dessiner(); return j; })
      .catch(function (e) { g.idx = { fichiers: [] }; g.erreur = T("chemins.erreur.generique", { erreur: e.message || e }); dessiner(); return null; });
  }

  // ── t379 : la Bibliothèque. Ses outils (corbeille, nettoyage, recherche) vivent dans la couche MONTAGE, figée par
  // plusieurs bancs : comme le lecteur de t372, un OBSERVATEUR ajoute à leur rangée un bouton « Emplacements » quand
  // au moins une source de bibliothèque existe, et pose la galerie juste APRÈS le bloc des outils. Aucun maillon.
  var cache = { quand: 0, liste: null, promesse: null };
  function sources() {
    if (cache.liste && Date.now() - cache.quand < 30000) return Promise.resolve(cache.liste);
    if (!cache.promesse) {
      cache.promesse = appel("GET", BASE).then(function (j) {
        cache.liste = ((j && j.emplacements) || []).filter(function (e) { return e.roles.indexOf("bibliotheque") >= 0; });
        cache.quand = Date.now(); cache.promesse = null;
        return cache.liste;
      }).catch(function () { cache.promesse = null; cache.liste = []; cache.quand = Date.now(); return []; });
    }
    return cache.promesse;
  }
  function greffer(outils) {
    if (!outils || outils.__dzChemins) return Promise.resolve(null);
    outils.__dzChemins = true;
    return sources().then(function (liste) {
      var rangee = outils.firstChild;
      if (!liste.length || !rangee) return null;
      var b = bouton(T("chemins.biblio.bouton"), "biblio");
      b.setAttribute("data-dz-chemins-biblio", "1");
      b.setAttribute("aria-pressed", "false");
      b.title = T("chemins.biblio.bouton_aide");
      var panneau = null;
      b.addEventListener("click", function () {
        if (panneau) {
          if (panneau.parentNode) panneau.parentNode.removeChild(panneau);
          panneau = null; b.setAttribute("aria-pressed", "false"); return;
        }
        panneau = el("div", { "data-dz-chemins": "biblio", style: "display:flex;flex-direction:column;gap:8px;margin-bottom:10px" });
        var hoteG = el("div");
        if (liste.length > 1) {
          var sel = el("select", { style: S.champ + ";align-self:flex-start", "data-dz-chemins-champ": "source" });
          liste.forEach(function (e) { sel.appendChild(el("option", { value: e.id }, e.nom)); });
          sel.addEventListener("change", function () { galerie(hoteG, sel.value); });
          panneau.appendChild(sel);
        }
        panneau.appendChild(hoteG);
        outils.insertAdjacentElement("afterend", panneau);
        b.setAttribute("aria-pressed", "true");
        galerie(hoteG, liste[0].id);
      });
      rangee.appendChild(b);
      return b;
    });
  }
  function observerBiblio() {
    var d = window.document;
    if (!d || !d.body || typeof window.MutationObserver !== "function") return null;
    var tic = null;
    function balayer() { tic = null; var o = d.querySelector('[data-dz="outils-biblio"]'); if (o) greffer(o); }
    var obs = new window.MutationObserver(function () { if (!tic) tic = setTimeout(balayer, 120); });
    obs.observe(d.body, { childList: true, subtree: true });
    balayer();
    return obs;
  }

  // ── t379 : « Réessayer » du Job Dock pour une sauvegarde, un miroir ou un index en échec ──────────────────────────
  // Le serveur rend la relance « emplacement » (routes._relance_de) : le Dock (maillon dzdock) pose donc son bouton
  // « Réessayer », mais son __dzRelancer ne connaît que quick / studio / direct et vit dans un remplacement de
  // dzdock, qu'un maillon aval ne peut pas toucher sans casser son aller-retour. On ne touche donc pas au bundle : un
  // écouteur en phase de CAPTURE (avant React) reconnaît ce bouton (son infobulle de repli) dans une ligne dont l'id
  // (span.mono[title]) est un job « emplacement » en échec connu, et rejoue l'opération lui-même. La liste de ces jobs
  // n'est relue (toutes les 10 s) que si au moins un emplacement existe.
  var dock = { ids: {}, minuterie: null };
  function idDeLaLigne(b) {
    for (var n = b, k = 0; n && k < 6; n = n.parentElement, k++) {
      var s = n.querySelector && n.querySelector("span.mono[title]");
      if (s) return s.getAttribute("title");
    }
    return null;
  }
  function boutonDock(t) {
    var b = t && t.closest ? t.closest("button") : null;
    if (!b) return null;
    var titre = b.getAttribute("title");
    return titre === T("coque.file.reessayer_direct_aide") || titre === T("chemins.dock.reessayer_aide") ? b : null;
  }
  function marquerDock() {
    var d = window.document;
    if (!d || !d.querySelectorAll) return;
    Array.prototype.forEach.call(d.querySelectorAll("button[title]"), function (b) {
      if (boutonDock(b) && dock.ids[idDeLaLigne(b)]) b.setAttribute("title", T("chemins.dock.reessayer_aide"));
    });
  }
  function dockRelire() {
    return appel("GET", "/api/jobs?providers=emplacement&limit=100").then(function (js) {
      var ids = {};
      (Array.isArray(js) ? js : []).forEach(function (j) { if (j.relance === "emplacement") ids[j.job_id] = 1; });
      dock.ids = ids;
      marquerDock();
      return ids;
    }).catch(function () { return dock.ids; });
  }
  function surClicDock(ev) {
    var b = boutonDock(ev.target);
    var id = b && idDeLaLigne(b);
    if (!id || !dock.ids[id]) return false;
    ev.preventDefault();
    ev.stopPropagation();
    if (ev.stopImmediatePropagation) ev.stopImmediatePropagation();
    reessayer(id, b).then(function () { dockRelire(); });
    return true;
  }
  function veillerDock() {
    var d = window.document;
    if (!d || !d.addEventListener || dock.minuterie || typeof window.setInterval !== "function") return;
    d.addEventListener("click", surClicDock, true);
    function tour() {
      appel("GET", BASE).then(function (j) { if (j && j.emplacements && j.emplacements.length) dockRelire(); }).catch(function () {});
    }
    dock.minuterie = window.setInterval(tour, 10000);
    tour();
  }

  function reessayer(jid, b) {
    if (b) b.disabled = true;
    return appel("POST", BASE + "/operations/" + encodeURIComponent(jid) + "/reessayer").then(function (r) {
      if (b) b.disabled = false;
      return r;
    }).catch(function (e) {
      if (b) b.disabled = false;
      var dlg = window.__dzDialogue;
      if (dlg && dlg.informer) dlg.informer(T("chemins.erreur.generique", { erreur: e.message || e }));
      return null;
    });
  }

  // ── 2. Diagnostic ──────────────────────────────────────────────────────────────────────────────────────────────

  // La ref de React rappelle diag à CHAQUE rendu du Diagnostic (« Rafraîchir » compris) : une vérification au plus
  // toutes les 3 s par hôte.
  var DIAG_MS = 3000;
  function diag(hote) {
    if (!hote) return null;
    if (hote.__dzCheminsDiag && Date.now() - hote.__dzCheminsDiagT < DIAG_MS) return hote.__dzCheminsDiag;
    hote.__dzCheminsDiagT = Date.now();
    var promesse = appel("GET", BASE + "/verifier").then(function (j) {
      vider(hote);
      var es = (j && j.emplacements) || [];
      if (!es.length) return es;                      // aucun emplacement : le Diagnostic ne change pas
      var box = el("div", { style: S.cadre + ";padding:16px;margin-bottom:14px", "data-dz-chemins": "diag" });
      box.appendChild(el("div", { style: S.tete + ";margin-bottom:10px" }, T("chemins.diag.titre")));
      es.forEach(function (e) {
        var l = el("div", { style: "display:grid;grid-template-columns:200px 1fr auto;gap:10px;align-items:center;padding:6px 0;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
                            "data-dz-chemin-id": e.id });
        l.appendChild(el("div", { style: "font-size:11.5px" }, e.nom));
        l.appendChild(el("div", { style: S.mono + ";color:var(--txt-mid,var(--ink-muted,#9aa4ae))" }, e.adresse));
        l.appendChild(el("div", { style: "font-size:11px;" + teinte(e), "data-dz-chemins": "etat" }, etat(e)));
        box.appendChild(l);
      });
      hote.appendChild(box);
      return es;
    }).catch(function () { vider(hote); return []; });
    hote.__dzCheminsDiag = promesse;
    return promesse;
  }

  window.__dzChemins = { monter: monter, diag: diag, galerie: galerie, greffer: greffer, reessayer: reessayer,
                         _etat: etat, _octets: octets, _date: date, _dock: dock, _dockRelire: dockRelire,
                         _surClicDock: surClicDock };
  function demarrer() { observerBiblio(); veillerDock(); }
  var doc = window.document;
  if (doc && doc.readyState !== "loading") demarrer();
  else if (doc && doc.addEventListener) doc.addEventListener("DOMContentLoaded", demarrer);
})();
