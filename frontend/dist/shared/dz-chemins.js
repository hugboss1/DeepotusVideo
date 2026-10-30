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
  }

  Panneau.prototype.charger = function () {
    var p = this;
    return appel("GET", BASE).then(function (j) { p.donnees = j; p.dessiner(); })
      .catch(function (e) { p.donnees = { erreur: String(e.message || e) }; p.dessiner(); });
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
      l.appendChild(m);
      var bs = el("div", { style: S.boutons });
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

  window.__dzChemins = { monter: monter, diag: diag, _etat: etat, _octets: octets };
})();
