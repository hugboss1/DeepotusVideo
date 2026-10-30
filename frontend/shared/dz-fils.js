/* dz-fils.js — les FILS SOCIAUX SUIVIS de News › Sources (t381, lot « News : fils suivis », 30/10/2026, plan
   docs/superpowers/plans/2026-10-29-finitions-esthetiques-chemins-fils-apparence.md, décision D4).
   SOURCE : frontend/shared/dz-fils.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-fils.js, servie à
   /shared/dz-fils.js, chargée par une balise classique dans la SPA (frontend/dist/index.html).
   Serveur : backend/app/services/news_fils.py, routes /api/news/fils (t380).
   Bancs : frontend/shared/qa/fils.test.mjs, backend/tests/test_fils_ecran.py.

   window.__dzFils.monter(hote) — sous la liste des flux de News › Sources (le maillon de queue
   scripts/patch_bundle_dzfils.py rend un <div data-dz-fils-hote> et appelle monter par une ref), vanilla DOM, aucun
   innerHTML :
   1. « Fils suivis » : chaque fil avec sa pastille de plateforme, son nom, sa lecture (gratuite ou payante), sa
      fréquence (choix en ligne), son état, sa dernière lecture, son coût (payant), son origine ; « Lire maintenant »,
      « Mettre en pause » / « Reprendre la lecture », « Retirer » (derrière __dzDialogue.confirmer) ; un fil payant
      sans accord montre « Voir le devis » : le devis, le plafond par relevé (au plus celui du serveur), « Accepter le
      devis » (confirme_cout) ; avec accord : son plafond et « Retirer l'accord ».
      « Ajouter un fil » : plateforme, identifiant (aide selon la plateforme), nom, fréquence.
   2. « Suggérés par les agents » : les suggestions en attente (raison, origine : agent, travail, date) ; « Accepter »
      fait naître le fil, « Écarter » ne la reproposera plus.
   Textes : clés fils.* (frontend/shared/i18n/fils.json) ; états et travaux arrivent en CODE (fils.etat.*, fils.cadre.*).
   Charte : aucun arrondi, jetons --srf-* / --brd-* / --txt-* avec repli. */
(function () {
  "use strict";
  if (window.__dzFils) return;

  var BASE = "/api/news/fils";
  var JSON_H = { "Content-Type": "application/json" };
  var ORDRE = ["youtube", "reddit", "x", "instagram", "tiktok"];
  var PASTILLES = {
    x: ["X", "var(--txt-hi,var(--ink-strong,#e6e9ee))"], instagram: ["IG", "var(--magenta,#d6409f)"],
    tiktok: ["TT", "var(--cyan,#22d3ee)"], youtube: ["YT", "var(--red,#e5484d)"], reddit: ["RD", "var(--amber,#f0b429)"]
  };
  var S = {
    panneau: "display:flex;flex-direction:column;gap:6px;padding:10px 16px 12px;border-top:1px solid var(--brd-soft,var(--stroke,#222830));color:var(--txt-base,var(--ink,#cfd6e2));font:12px/1.45 system-ui,sans-serif",
    tete: "display:flex;align-items:center;justify-content:space-between;gap:8px",
    titre: "font:600 13px/1.3 system-ui,sans-serif;color:var(--txt-hi,var(--ink-strong,#e6e9ee))",
    petit: "font-size:10.5px;color:var(--txt-mid,var(--ink-soft,#9aa4ae))",
    ligne: "display:flex;flex-direction:column;gap:3px;padding:7px 0 7px 8px;border-left:2px solid transparent",
    nomRang: "display:flex;align-items:center;gap:6px;min-width:0",
    nom: "flex:1;font-size:12px;color:var(--txt-hi,var(--ink-strong,#e6e9ee));overflow:hidden;text-overflow:ellipsis;white-space:nowrap",
    pastille: "flex:none;min-width:20px;height:16px;padding:0 3px;display:inline-flex;align-items:center;justify-content:center;font:600 9px/1 'IBM Plex Mono',monospace;border:1px solid currentColor;border-radius:0",
    boutons: "display:flex;gap:4px;flex-wrap:wrap",
    btn: "height:22px;padding:0 7px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit;font-size:11px",
    primaire: "background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6);color:var(--accent-ink,#ffffff)",
    cadre: "border:1px solid var(--amber,#f0b429);padding:8px;display:flex;flex-direction:column;gap:6px",
    champ: "height:24px;padding:0 6px;border-radius:0;background:var(--srf-sunken,var(--bg-base,#0d1014));border:1px solid var(--brd-soft,var(--stroke,#222830));color:var(--txt-hi,var(--ink-strong,#e6e9ee));font:11px 'IBM Plex Mono',monospace;min-width:0;width:100%;box-sizing:border-box",
    etiquette: "display:flex;flex-direction:column;gap:2px;font-size:10.5px;color:var(--txt-mid,var(--ink-soft,#9aa4ae))",
    ok: "color:var(--green,#3fb950)",
    ko: "color:var(--red,#e5484d)",
    alerte: "color:var(--amber,#f0b429)",
    raison: "font-size:11px;color:var(--txt-base,var(--ink,#cfd6e2))"
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
    return el("button", { type: "button", style: S.btn + (primaire ? ";" + S.primaire : ""), "data-dz-fils-action": action }, texte);
  }
  function usd(v) {
    var t = Number(v || 0).toFixed(2);
    return langue() === "en" ? t : t.replace(".", ",");
  }
  function date(iso) {
    var d = new Date(String(iso || ""));
    if (isNaN(d.getTime())) return String(iso || "");
    return d.toLocaleString(langue() === "en" ? "en-GB" : "fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  }
  function pastille(p, libelle) {
    var x = PASTILLES[p] || ["?", "inherit"];
    return el("span", { style: S.pastille + ";color:" + x[1], title: libelle || p, "data-dz-fils-plateforme": p }, x[0]);
  }
  function appel(methode, url, corps) {
    var o = { method: methode, headers: JSON_H };
    if (corps !== undefined) o.body = JSON.stringify(corps);
    return window.fetch(url, o).then(function (R) {
      return R.json().catch(function () { return {}; }).then(function (j) {
        if (!R.ok) {
          var d = j && j.detail, e = new Error(String((d && typeof d === "object" ? d.message : d) || R.status));
          e.detail = d; e.status = R.status;
          throw e;
        }
        return j;
      });
    });
  }

  function Panneau(hote) {
    this.hote = hote;
    this.donnees = null;
    this.form = null;                   // null | {plateforme, identifiant, nom, frequence_h}
    this.message = null;                // {ok, texte} sous le titre
    this.msgs = {};                     // id du fil -> {ok, texte}
    this.devis = {};                    // id du fil -> devis ouvert {devis_usd, max, plafond_max_usd, configure, plafond}
    this.encours = {};                  // id du fil -> lecture en cours
  }

  Panneau.prototype.charger = function () {
    var p = this;
    return appel("GET", BASE).then(function (j) { p.donnees = j; p.dessiner(); })
      .catch(function (e) { p.donnees = { erreur: String(e.message || e) }; p.dessiner(); });
  };

  Panneau.prototype.libelle = function (plateforme) {
    var d = this.donnees && this.donnees.plateformes;
    return (d && d[plateforme] && d[plateforme].libelle) || plateforme;
  };

  Panneau.prototype.dessiner = function () {
    var p = this, h = this.hote, d = this.donnees;
    vider(h);
    var box = el("div", { style: S.panneau, "data-dz-fils": "panneau" });
    var tete = el("div", { style: S.tete });
    tete.appendChild(el("div", { style: S.titre }, T("fils.section.titre")));
    var aj = bouton(T("fils.section.ajouter"), "ajouter");
    aj.addEventListener("click", function () {
      p.form = { plateforme: "youtube", identifiant: "", nom: "", frequence_h: (d && d.frequence_defaut_h) || 24 };
      p.dessiner();
    });
    if (d && !d.erreur) tete.appendChild(aj);
    box.appendChild(tete);
    box.appendChild(el("div", { style: S.petit }, T("fils.section.aide")));
    if (!d) { box.appendChild(el("div", { style: S.petit }, T("fils.section.chargement"))); h.appendChild(box); return; }
    if (d.erreur) {
      box.appendChild(el("div", { style: S.petit + ";" + S.ko }, T("fils.section.indisponible", { erreur: d.erreur })));
      h.appendChild(box); return;
    }
    if (this.message) {
      box.appendChild(el("div", { style: "font-size:11px;" + (this.message.ok ? S.ok : S.ko), "data-dz-fils": "message" }, this.message.texte));
    }
    if (this.form) box.appendChild(this.formulaire());
    var liste = el("div", { "data-dz-fils": "liste" });
    if (!d.fils.length) liste.appendChild(el("div", { style: S.petit }, T("fils.section.vide")));
    d.fils.forEach(function (f) { liste.appendChild(p.ligne(f)); });
    box.appendChild(liste);
    box.appendChild(this.suggestions());
    h.appendChild(box);
  };

  Panneau.prototype.choixFrequence = function (valeur, action) {
    var d = this.donnees, s = el("select", { style: S.champ + ";width:auto;height:22px", "data-dz-fils-action": action });
    (d.frequences_h || [24]).forEach(function (n) {
      var o = el("option", { value: String(n) }, T("fils.freq.heures", { n: n }));
      if (n === valeur) o.setAttribute("selected", "selected");
      s.appendChild(o);
    });
    s.value = String(valeur);
    return s;
  };

  Panneau.prototype.formulaire = function () {
    var p = this, f = this.form;
    var c = el("div", { style: S.cadre, "data-dz-fils": "formulaire" });
    var lp = el("label", { style: S.etiquette }, null);
    lp.appendChild(el("span", null, T("fils.form.plateforme")));
    var sp = el("select", { style: S.champ, "data-dz-fils-champ": "plateforme" });
    ORDRE.forEach(function (k) {
      var o = el("option", { value: k }, p.libelle(k) + " — " + T("fils.lecture." + ((p.donnees.plateformes[k] || {}).lecture || "rss")));
      if (k === f.plateforme) o.setAttribute("selected", "selected");
      sp.appendChild(o);
    });
    sp.value = f.plateforme;
    sp.addEventListener("change", function () { f.plateforme = sp.value; p.dessiner(); });
    lp.appendChild(sp);
    c.appendChild(lp);
    var aide = f.plateforme === "youtube" ? "fils.form.aide_youtube" : f.plateforme === "reddit" ? "fils.form.aide_reddit" : "fils.form.aide_pseudo";
    [["identifiant", "fils.form.identifiant", T(aide)], ["nom", "fils.form.nom", ""]].forEach(function (z) {
      var l = el("label", { style: S.etiquette }, null);
      l.appendChild(el("span", null, T(z[1])));
      var i = el("input", { type: "text", style: S.champ, placeholder: z[2], "data-dz-fils-champ": z[0] });
      i.value = f[z[0]] || "";
      i.addEventListener("input", function () { f[z[0]] = i.value; });
      l.appendChild(i);
      c.appendChild(l);
    });
    var lf = el("label", { style: S.etiquette }, null);
    lf.appendChild(el("span", null, T("fils.form.frequence")));
    var sf = this.choixFrequence(f.frequence_h, "frequence-form");
    sf.addEventListener("change", function () { f.frequence_h = Number(sf.value); });
    lf.appendChild(sf);
    c.appendChild(lf);
    var b = el("div", { style: S.boutons });
    var ok = bouton(T("fils.form.valider"), "valider", true);
    ok.addEventListener("click", function () {
      appel("POST", BASE, { plateforme: f.plateforme, identifiant: f.identifiant, nom: f.nom || null, frequence_h: f.frequence_h })
        .then(function () { p.form = null; p.message = null; return p.charger(); })
        .catch(function (e) { p.message = { ok: false, texte: String(e.message || e) }; p.dessiner(); });
    });
    var an = bouton(T("fils.form.annuler"), "annuler");
    an.addEventListener("click", function () { p.form = null; p.message = null; p.dessiner(); });
    b.appendChild(ok); b.appendChild(an);
    c.appendChild(b);
    return c;
  };

  Panneau.prototype.agir = function (fid, promesse, succes) {
    var p = this;
    return promesse.then(function (j) {
      p.msgs[fid] = succes ? { ok: true, texte: succes(j) } : null;
      return p.charger();
    }).catch(function (e) { p.msgs[fid] = { ok: false, texte: String(e.message || e) }; return p.charger(); });
  };

  Panneau.prototype.ligne = function (f) {
    var p = this, apify = f.lecture === "apify";
    var l = el("div", { style: S.ligne + (f.pause ? "" : ";border-left-color:var(--cyan,#22d3ee)"), "data-dz-fil-id": f.id });
    var r1 = el("div", { style: S.nomRang });
    r1.appendChild(pastille(f.plateforme, this.libelle(f.plateforme)));
    r1.appendChild(el("span", { style: S.nom, title: f.lien || f.nom }, f.nom));
    var freq = this.choixFrequence(f.frequence_h, "frequence");
    freq.addEventListener("change", function () { p.agir(f.id, appel("PATCH", BASE + "/" + f.id, { frequence_h: Number(freq.value) })); });
    r1.appendChild(freq);
    l.appendChild(r1);
    var info = [T("fils.lecture." + f.lecture)];
    if (f.pause) info.push(T("fils.ligne.en_pause"));
    info.push(T("fils.etat." + (f.etat || "jamais_lu")));
    l.appendChild(el("div", { style: S.petit + ";" + (f.etat === "ok" ? "" : f.etat === "erreur" || f.etat === "plafond_mensuel" ? S.ko : f.etat === "jamais_lu" ? "" : S.alerte),
                               "data-dz-fils": "etat" }, info.join(" · ")));
    var lec = [];
    if (f.derniere_lecture) lec.push(T("fils.ligne.lu_le", { date: date(f.derniere_lecture) }), T("fils.ligne.nombre", { n: f.dernier_nombre || 0 }));
    if (apify && (f.derniere_lecture || f.cout_cumule_usd)) lec.push(T("fils.ligne.cout", { dernier: usd(f.dernier_cout_usd), total: usd(f.cout_cumule_usd) }));
    if (f.prochaine) lec.push(T("fils.ligne.prochaine", { date: date(f.prochaine) }));
    if (lec.length) l.appendChild(el("div", { style: S.petit, "data-dz-fils": "lecture" }, lec.join(" · ")));
    var o = f.origine || {};
    l.appendChild(el("div", { style: S.petit, "data-dz-fils": "origine" }, o.type === "agent"
      ? T("fils.ligne.origine_agent", { cadre: T("fils.cadre." + (o.cadre || "campagne")) }) : T("fils.ligne.origine_main")));
    if (apify && f.accord) {
      l.appendChild(el("div", { style: S.petit, "data-dz-fils": "accord" }, T("fils.accord.texte", { usd: usd(f.accord.plafond_usd) })));
    }
    if (this.msgs[f.id]) l.appendChild(el("div", { style: "font-size:11px;" + (this.msgs[f.id].ok ? S.ok : S.ko), "data-dz-fils": "message" }, this.msgs[f.id].texte));
    var b = el("div", { style: S.boutons });
    if (!apify || f.accord) {
      var lire = bouton(this.encours[f.id] ? T("fils.action.lecture_en_cours") : T("fils.action.lire"), "lire", true);
      if (this.encours[f.id]) lire.disabled = true;
      lire.addEventListener("click", function () {
        p.encours[f.id] = true; p.dessiner();
        p.agir(f.id, appel("POST", BASE + "/" + f.id + "/lire"), function (j) { return T("fils.action.lus", { n: j.lus }); })
          .then(function () { delete p.encours[f.id]; p.dessiner(); });
      });
      b.appendChild(lire);
    }
    if (apify && !f.accord) {
      var dv = bouton(T("fils.action.devis"), "devis", true);
      dv.addEventListener("click", function () {
        appel("GET", BASE + "/" + f.id + "/devis").then(function (j) {
          var defaut = Math.min(j.plafond_max_usd, Math.max(0.1, Math.ceil(j.devis_usd * 150) / 100));
          p.devis[f.id] = { devis_usd: j.devis_usd, max: j.max, plafond_max_usd: j.plafond_max_usd, configure: j.configure, plafond: defaut };
          p.msgs[f.id] = null; p.dessiner();
        }).catch(function (e) { p.msgs[f.id] = { ok: false, texte: String(e.message || e) }; p.dessiner(); });
      });
      b.appendChild(dv);
    }
    if (apify && f.accord) {
      var ra = bouton(T("fils.accord.retirer"), "retirer-accord");
      ra.addEventListener("click", function () { p.agir(f.id, appel("DELETE", BASE + "/" + f.id + "/accord")); });
      b.appendChild(ra);
    }
    var pz = bouton(f.pause ? T("fils.action.reprendre") : T("fils.action.pause"), f.pause ? "reprendre" : "pause");
    pz.addEventListener("click", function () { p.agir(f.id, appel("PATCH", BASE + "/" + f.id, { pause: !f.pause })); });
    b.appendChild(pz);
    var rt = bouton(T("fils.action.retirer"), "retirer");
    rt.addEventListener("click", function () {
      var dlg = window.__dzDialogue;
      var oui = dlg && dlg.confirmer ? dlg.confirmer(T("fils.action.retirer_confirmer", { nom: f.nom })) : Promise.resolve(false);
      Promise.resolve(oui).then(function (v) {
        if (!v) return;
        p.agir(f.id, appel("DELETE", BASE + "/" + f.id));
      });
    });
    b.appendChild(rt);
    l.appendChild(b);
    if (this.devis[f.id] && apify && !f.accord) l.appendChild(this.carteDevis(f));
    return l;
  };

  Panneau.prototype.carteDevis = function (f) {
    var p = this, dv = this.devis[f.id];
    var c = el("div", { style: S.cadre, "data-dz-fils": "devis" });
    c.appendChild(el("div", { style: S.raison }, T("fils.devis.texte", { usd: usd(dv.devis_usd), n: dv.max })));
    if (!dv.configure) {
      c.appendChild(el("div", { style: "font-size:11px;" + S.ko, "data-dz-fils": "sans-cle" }, T("fils.devis.sans_cle")));
    }
    var l = el("label", { style: S.etiquette }, null);
    l.appendChild(el("span", null, T("fils.devis.plafond") + " — " + T("fils.devis.borne", { usd: usd(dv.plafond_max_usd) })));
    var i = el("input", { type: "number", step: "0.05", min: "0.01", max: String(dv.plafond_max_usd), style: S.champ, "data-dz-fils-champ": "plafond" });
    i.value = String(dv.plafond);
    i.addEventListener("input", function () { dv.plafond = Number(i.value); });
    l.appendChild(i);
    c.appendChild(l);
    var b = el("div", { style: S.boutons });
    var ok = bouton(T("fils.devis.accepter"), "accepter-devis", true);
    if (!dv.configure) ok.disabled = true;
    ok.addEventListener("click", function () {
      appel("POST", BASE + "/" + f.id + "/accord", { plafond_usd: Number(dv.plafond), confirme_cout: true })
        .then(function () { delete p.devis[f.id]; p.msgs[f.id] = null; return p.charger(); })
        .catch(function (e) { p.msgs[f.id] = { ok: false, texte: String(e.message || e) }; p.dessiner(); });
    });
    var an = bouton(T("fils.form.annuler"), "annuler-devis");
    an.addEventListener("click", function () { delete p.devis[f.id]; p.dessiner(); });
    b.appendChild(ok); b.appendChild(an);
    c.appendChild(b);
    return c;
  };

  Panneau.prototype.suggestions = function () {
    var p = this, d = this.donnees;
    var en = (d.suggestions || []).filter(function (s) { return s.etat === "proposee"; });
    var box = el("div", { style: "display:flex;flex-direction:column;gap:4px;margin-top:6px", "data-dz-fils": "suggestions" });
    box.appendChild(el("div", { style: S.titre }, T("fils.sug.titre") + (en.length ? " (" + en.length + ")" : "")));
    box.appendChild(el("div", { style: S.petit }, T("fils.sug.aide")));
    if (!en.length) box.appendChild(el("div", { style: S.petit }, T("fils.sug.vide")));
    en.forEach(function (s) {
      var l = el("div", { style: S.ligne + ";border-left-color:var(--amber,#f0b429)", "data-dz-suggestion-id": s.id });
      var r1 = el("div", { style: S.nomRang });
      r1.appendChild(pastille(s.plateforme, p.libelle(s.plateforme)));
      r1.appendChild(el("span", { style: S.nom, title: s.identifiant }, s.nom));
      l.appendChild(r1);
      if (s.raison) l.appendChild(el("div", { style: S.raison, "data-dz-fils": "raison" }, s.raison));
      var o = s.origine || {};
      l.appendChild(el("div", { style: S.petit, "data-dz-fils": "origine" }, T("fils.sug.origine", {
        agent: T("fils.agent." + (o.agent || "campagnes")), cadre: T("fils.cadre." + (o.cadre || "campagne")), date: date(s.cree) })));
      var b = el("div", { style: S.boutons });
      var ac = bouton(T("fils.sug.accepter"), "accepter", true);
      ac.addEventListener("click", function () {
        appel("POST", BASE + "/suggestions/" + s.id + "/accepter", {}).then(function () { p.message = null; return p.charger(); })
          .catch(function (e) { p.message = { ok: false, texte: String(e.message || e) }; p.dessiner(); });
      });
      var ec = bouton(T("fils.sug.ecarter"), "ecarter");
      ec.addEventListener("click", function () {
        appel("POST", BASE + "/suggestions/" + s.id + "/ecarter").then(function () { p.message = null; return p.charger(); })
          .catch(function (e) { p.message = { ok: false, texte: String(e.message || e) }; p.dessiner(); });
      });
      b.appendChild(ac); b.appendChild(ec);
      l.appendChild(b);
      box.appendChild(l);
    });
    return box;
  };

  var MONTES = [];
  function monter(hote) {
    if (!hote || hote.__dzFils) return hote && hote.__dzFils;
    var p = new Panneau(hote);
    hote.__dzFils = p;
    MONTES.push(p);
    p.dessiner();
    p.charger();
    return p;
  }

  window.__dzFils = { monter: monter, _Panneau: Panneau };
})();
