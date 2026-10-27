/* onglets-gestion.js — les onglets MODÈLES, CONTACTS, SANTÉ et PRIX META de la page WhatsApp (t311 tâche 7).
   S'inscrivent dans window.__dzWhatsapp.onglets (socle : whatsapp.js). Chaque onglet se relit à l'ouverture.
   · Modèles : GET …/modeles?tous=1 — nom, langue, catégorie, paramètres, statut (approuvé, en attente, refusé, désactivé).
   · Contacts (GET …/etat) : accords (ajouter un accord SAISI : identité + source, POST …/accords), STOP (poser : POST
     …/stop ; lever : source OBLIGATOIRE, POST …/stop/lever), désinscrits du marketing (lecture : seul le contact lève sa
     désinscription, chez Meta).
   · Santé : compteurs du mois UTC de ce numéro (sortants, entrants, service) contre `plafond_mois` (le plafond de
     l'espace), échecs de livraison du journal, désinscrits, modèles refusés, état de l'agent.
   · Prix Meta : la grille `whatsapp_meta_usd` de GET /api/cost/pricing, une ligne par marché (indicatif + marketing,
     utility, authentication, service). `pricing.save` fusionne CLÉ PAR CLÉ au premier niveau : la grille entière est
     donc envoyée à chaque enregistrement (POST /api/cost/pricing {"whatsapp_meta_usd": {…}}), et une ligne supprimée
     disparaît vraiment. Une grille vide refuse tout envoi (rappel affiché, confirmation avant d'enregistrer). */
(function () {
  "use strict";
  var W = window.__dzWhatsapp;
  if (!W || W.onglets.modeles) return;
  var T = W.T, el = W.el, S = W.S;
  var STATUTS_MODELE = ["approved", "pending", "rejected", "disabled", "paused"];
  var CATEGORIES = ["marketing", "utility", "authentication"];
  var COLONNES = ["marketing", "utility", "authentication", "service"];

  function categorie(c) { return CATEGORIES.indexOf(c) >= 0 ? T("whatsapp.categorie." + c) : String(c || ""); }
  function statutModele(s) { return STATUTS_MODELE.indexOf(s) >= 0 ? T("whatsapp.modele_statut." + s) : T("whatsapp.modele_statut.autre", { statut: String(s || "") }); }
  function titre(texte, cle) { return el("h3", { cls: "wa-titre" }, [W.icone(cle), el("span", { texte: texte })]); }
  function section(cls, enfants) { return el("section", { cls: "wa-bloc " + (cls || "") }, enfants); }
  async function modelesTous() {
    var r = await W.api("GET", W.waUrl("/modeles?tous=1"));
    if (r.ok && Array.isArray(r.data)) S.modelesTous = r.data;
    return r;
  }

  // ── Modèles ─────────────────────────────────────────────────────────────────────────────────────────────────────────
  async function afficherModeles(p) {
    p.textContent = "";
    p.appendChild(el("p", { cls: "wa-aide", texte: T("whatsapp.modeles.aide") }));
    var r = await modelesTous();
    if (!r.ok) { W.erreur(W.messageErreur(r)); return; }
    var liste = el("div", { cls: "wa-table wa-table--modeles", a: { role: "table" } });
    liste.appendChild(el("div", { cls: "wa-rangee wa-rangee--tete", a: { role: "row" } },
      ["nom", "langue", "categorie", "parametres", "statut"].map(function (k) { return el("span", { a: { role: "columnheader" }, texte: T("whatsapp.modeles.col_" + k) }); })));
    (S.modelesTous || []).forEach(function (m) {
      var st = String(m.statut || "");
      liste.appendChild(el("div", { cls: "wa-rangee", a: { role: "row", "data-dz-wa-modele-ligne": m.nom } }, [
        el("span", { cls: "wa-mono", texte: m.nom }), el("span", { texte: m.langue || "" }), el("span", { texte: categorie(m.categorie) }),
        el("span", { texte: T("whatsapp.modeles.n_parametres", { n: m.n_parametres || 0 }) }),
        el("span", { cls: "wa-statut-modele wa-statut-modele--" + (STATUTS_MODELE.indexOf(st) >= 0 ? st : "autre"), a: { "data-dz-wa-modele-statut": st }, texte: statutModele(st) })
      ]));
    });
    if (!(S.modelesTous || []).length) liste.appendChild(el("p", { cls: "wa-aide", texte: T("whatsapp.modeles.aucun") }));
    p.appendChild(liste);
  }

  // ── Contacts ────────────────────────────────────────────────────────────────────────────────────────────────────────
  function identiteSaisie(champ) {
    var id = W.normaliserIdentite(champ.value);
    if (!W.identiteValide(id)) { W.erreur(T("whatsapp.contacts.identite_invalide")); return null; }
    return id;
  }
  async function poster(suffixe, corps, cleOk, p) {
    var r = await W.api("POST", W.waUrl(suffixe), corps);
    if (!r.ok) { W.erreur(W.messageErreur(r)); return false; }
    W.info(T(cleOk));
    await afficherContacts(p, true);
    return true;
  }
  async function afficherContacts(p, garderMessages) {
    if (!garderMessages) W.effacer();
    var r = await W.chargerEtat();
    p.textContent = "";
    if (!r.ok || !S.etat) { W.erreur(W.messageErreur(r)); return; }
    var e = S.etat;

    // accords
    var accords = el("div", { cls: "wa-table", a: { "data-dz-wa-accords": true } });
    var ka = Object.keys(e.accords || {}).sort();
    if (!ka.length) accords.appendChild(el("p", { cls: "wa-aide", texte: T("whatsapp.contacts.aucun_accord") }));
    ka.forEach(function (id) {
      var a = e.accords[id] || {};
      accords.appendChild(el("div", { cls: "wa-rangee" }, [el("span", { cls: "wa-mono", texte: id }), el("span", { texte: String(a.source || "") }), el("span", { cls: "wa-sous", texte: W.date(a.date) })]));
    });
    var aId = W.champ({ label: T("whatsapp.contacts.identite"), placeholder: T("whatsapp.contacts.identite_ph"), a: { "data-dz-wa-accord-identite": true } });
    var aSrc = W.champ({ label: T("whatsapp.contacts.source"), placeholder: T("whatsapp.contacts.source_ph"), a: { "data-dz-wa-accord-source": true } });
    var aBtn = W.bouton(T("whatsapp.contacts.ajouter_accord"), { cls: "wa-btn--primaire", a: { "data-dz-wa-accord-ajouter": true }, on: { click: async function () {
      W.effacer();
      var id = identiteSaisie(aId); if (!id) return;
      var src = aSrc.value.trim();
      if (!src) { W.erreur(T("whatsapp.contacts.source_exigee")); return; }
      await poster("/accords", { identite: id, source: src }, "whatsapp.contacts.accord_note", p);
    } } }, "dz-action-ajouter");
    p.appendChild(section("wa-bloc--accords", [titre(T("whatsapp.contacts.accords"), "dz-etat-succes"), el("p", { cls: "wa-aide", texte: T("whatsapp.contacts.accord_aide") }),
      accords, el("div", { cls: "wa-ligne" }, [aId, aSrc, aBtn])]));

    // STOP
    var stops = el("div", { cls: "wa-table", a: { "data-dz-wa-stops": true } });
    var ks = Object.keys(e.stops || {}).sort();
    if (!ks.length) stops.appendChild(el("p", { cls: "wa-aide", texte: T("whatsapp.contacts.aucun_stop") }));
    ks.forEach(function (id) {
      var src = W.champ({ label: T("whatsapp.contacts.lever_source"), placeholder: T("whatsapp.contacts.lever_source_ph"), a: { "data-dz-wa-lever-source": true } });
      var lever = W.bouton(T("whatsapp.contacts.lever"), { a: { "data-dz-wa-lever": true }, disabled: true, titre: T("whatsapp.contacts.lever_aide"), on: { click: async function () {
        W.effacer();
        var s = src.value.trim();
        if (!s) { W.erreur(T("whatsapp.contacts.source_exigee")); return; }
        await poster("/stop/lever", { identite: id, source: s }, "whatsapp.contacts.stop_leve", p);
      } } }, "dz-action-restaurer");
      src.addEventListener("input", function () { lever.disabled = !src.value.trim(); });
      stops.appendChild(el("div", { cls: "wa-rangee", a: { "data-dz-wa-stop-ligne": id } }, [el("span", { cls: "wa-mono", texte: id }), el("span", { cls: "wa-sous", texte: W.date(e.stops[id]) }), src, lever]));
    });
    var sId = W.champ({ label: T("whatsapp.contacts.identite"), placeholder: T("whatsapp.contacts.identite_ph"), a: { "data-dz-wa-stop-identite": true } });
    var sBtn = W.bouton(T("whatsapp.contacts.poser_stop"), { a: { "data-dz-wa-stop-poser": true }, on: { click: async function () {
      W.effacer();
      var id = identiteSaisie(sId); if (!id) return;
      if (!(await W.confirmer(T("whatsapp.contacts.stop_confirmer", { identite: id })))) return;
      await poster("/stop", { identite: id }, "whatsapp.contacts.stop_pose", p);
    } } }, "dz-etat-exclu");
    p.appendChild(section("wa-bloc--stops", [titre(T("whatsapp.contacts.stops"), "dz-etat-exclu"), el("p", { cls: "wa-aide", texte: T("whatsapp.contacts.stop_aide") }),
      stops, el("div", { cls: "wa-ligne" }, [sId, sBtn])]));

    // désinscrits du marketing
    var des = el("div", { cls: "wa-table", a: { "data-dz-wa-desinscrits": true } });
    var kd = Object.keys(e.desinscrits_marketing || {}).sort();
    if (!kd.length) des.appendChild(el("p", { cls: "wa-aide", texte: T("whatsapp.contacts.aucun_desinscrit") }));
    kd.forEach(function (id) { des.appendChild(el("div", { cls: "wa-rangee" }, [el("span", { cls: "wa-mono", texte: id }), el("span", { cls: "wa-sous", texte: W.date(e.desinscrits_marketing[id]) })])); });
    p.appendChild(section("wa-bloc--desinscrits", [titre(T("whatsapp.contacts.desinscrits"), "dz-etat-avertissement"), el("p", { cls: "wa-aide", texte: T("whatsapp.contacts.desinscrits_aide") }), des]));
  }

  // ── Santé ───────────────────────────────────────────────────────────────────────────────────────────────────────────
  function nombre(v) { return typeof v === "number" && isFinite(v) && v > 0 ? v : 0; }
  async function afficherSante(p) {
    p.textContent = "";
    var rs = await Promise.all([W.chargerEtat(), modelesTous()]);
    if (!rs[0].ok || !S.etat) { W.erreur(W.messageErreur(rs[0])); return; }
    var e = S.etat;
    var mois = new Date().toISOString().slice(0, 7);
    var cpt = (e.compteur || {})[mois] || {};
    var so = nombre(cpt.sortants), en = nombre(cpt.entrants), se = nombre(cpt.service);
    var plafond = typeof e.plafond_mois === "number" ? e.plafond_mois : 0;
    var total = so + en;
    var tuile = function (k, v) { return el("div", { cls: "wa-tuile", a: { "data-dz-wa-sante": k } }, [el("span", { cls: "wa-sous", texte: T("whatsapp.sante." + k) }), el("b", { cls: "wa-mono", texte: String(v) })]); };
    var pct = plafond > 0 ? Math.min(100, Math.round(total * 100 / plafond)) : 100;
    var jauge = el("div", { cls: "wa-jauge" + (pct >= 80 ? " wa-jauge--alerte" : ""), a: { role: "progressbar", "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": String(pct) } }, [el("span", { cls: "wa-jauge-plein" })]);
    jauge.firstChild.style.width = pct + "%";
    p.appendChild(section("wa-bloc--compteurs", [titre(T("whatsapp.sante.mois", { mois: mois }), "dz-media-duree"),
      el("div", { cls: "wa-tuiles" }, [tuile("sortants", so), tuile("entrants", en), tuile("service", se), tuile("desinscrits", Object.keys(e.desinscrits_marketing || {}).length)]),
      el("div", { cls: "wa-total", a: { "data-dz-wa-sante": "total" } }, [el("span", { texte: T("whatsapp.sante.total", { n: total, plafond: plafond }) }), jauge]),
      el("p", { cls: "wa-aide", texte: T("whatsapp.sante.total_aide") })]));
    var echecs = el("div", { cls: "wa-table", a: { "data-dz-wa-echecs": true } });
    var liste = (e.journal || []).filter(function (j) { return j && j.sens === "sortant" && /fail|echec|undeliver/i.test(String(j.statut || "")); }).reverse();
    if (!liste.length) echecs.appendChild(el("p", { cls: "wa-aide", texte: T("whatsapp.sante.aucun_echec") }));
    liste.slice(0, 50).forEach(function (j) {
      echecs.appendChild(el("div", { cls: "wa-rangee", a: { "data-dz-wa-echec": true } }, [el("span", { cls: "wa-sous", texte: W.heure(j.quand) }), el("span", { cls: "wa-mono", texte: String(j.identite || "") }),
        el("span", { texte: String(j.type || "") + (j.categorie ? " · " + categorie(j.categorie) : "") })]));
    });
    p.appendChild(section("wa-bloc--echecs", [titre(T("whatsapp.sante.echecs"), "dz-etat-erreur"), echecs]));
    var refuses = el("div", { cls: "wa-table", a: { "data-dz-wa-refuses": true } });
    if (!rs[1].ok) refuses.appendChild(el("p", { cls: "wa-aide", texte: T("whatsapp.sante.modeles_illisibles") }));
    else {
      var ref = (S.modelesTous || []).filter(function (m) { return m.statut === "rejected"; });
      if (!ref.length) refuses.appendChild(el("p", { cls: "wa-aide", texte: T("whatsapp.sante.aucun_refuse") }));
      ref.forEach(function (m) { refuses.appendChild(el("div", { cls: "wa-rangee" }, [el("span", { cls: "wa-mono", texte: m.nom }), el("span", { texte: m.langue || "" }), el("span", { texte: categorie(m.categorie) })])); });
    }
    p.appendChild(section("wa-bloc--refuses", [titre(T("whatsapp.sante.refuses"), "dz-nav-templates"), refuses]));
    var ag = e.agent || {};
    p.appendChild(section("wa-bloc--agent", [titre(T("whatsapp.sante.agent"), "dz-etat-ia"),
      el("p", { texte: ag.actif ? T("whatsapp.sante.agent_actif", { mode: T(ag.mode === "auto" ? "whatsapp.mode.auto" : "whatsapp.mode.brouillon") }) : T("whatsapp.sante.agent_inactif") })]));
  }

  // ── Prix Meta ───────────────────────────────────────────────────────────────────────────────────────────────────────
  var P = { lignes: [] };
  function ligneDePrix(marche, cols) {
    var l = { marche: W.champ({ cls: "wa-champ--court", label: T("whatsapp.prix.marche"), placeholder: T("whatsapp.prix.marche_ph"), value: marche || "", a: { "data-dz-wa-prix-marche": true } }), cols: {} };
    var enfants = [l.marche];
    COLONNES.forEach(function (k) {
      var v = cols && typeof cols[k] === "number" ? String(cols[k]) : "";
      l.cols[k] = W.champ({ cls: "wa-champ--court wa-mono", label: T("whatsapp.prix.col_" + k), value: v, a: { "data-dz-wa-prix-col": k, inputmode: "decimal" } });
      enfants.push(l.cols[k]);
    });
    enfants.push(W.bouton("", { titre: T("whatsapp.prix.supprimer"), a: { "data-dz-wa-prix-supprimer": true }, on: { click: function () {
      l.noeud.remove(); P.lignes = P.lignes.filter(function (x) { return x !== l; });
    } } }, "dz-action-supprimer"));
    l.noeud = el("div", { cls: "wa-rangee wa-rangee--prix", a: { role: "row", "data-dz-wa-prix-ligne": true } }, enfants);
    P.lignes.push(l);
    P.corps.appendChild(l.noeud);
    return l;
  }
  function lireGrille() {
    var out = {};
    for (var i = 0; i < P.lignes.length; i++) {
      var l = P.lignes[i];
      var brut = l.marche.value.trim();
      var vides = COLONNES.every(function (k) { return !l.cols[k].value.trim(); });
      if (!brut && vides) continue;
      var m = brut.replace(/^\+/, "").replace(/\s+/g, "");
      if (!/^\d{1,6}$/.test(m)) return { erreur: T("whatsapp.prix.marche_invalide", { marche: brut }) };
      if (Object.prototype.hasOwnProperty.call(out, m)) return { erreur: T("whatsapp.prix.marche_double", { marche: m }) };
      var ligne = {};
      for (var j = 0; j < COLONNES.length; j++) {
        var k = COLONNES[j], v = l.cols[k].value.trim().replace(",", ".");
        if (!v) continue;
        var n = Number(v);
        if (!isFinite(n) || n < 0) return { erreur: T("whatsapp.prix.tarif_invalide", { marche: m, categorie: T("whatsapp.prix.col_" + k) }) };
        ligne[k] = n;
      }
      out[m] = ligne;
    }
    return { grille: out };
  }
  function dessinerGrille(g) {
    P.corps.textContent = ""; P.lignes = [];
    Object.keys(g || {}).forEach(function (m) { ligneDePrix(m, g[m]); });
  }
  async function afficherPrix(p) {
    p.textContent = "";
    P.corps = el("div", { cls: "wa-table wa-table--prix", a: { role: "rowgroup" } });
    p.appendChild(el("p", { cls: "wa-bandeau", a: { "data-dz-wa-prix-rappel": true }, texte: T("whatsapp.prix.rappel") }));
    p.appendChild(el("p", { cls: "wa-aide", texte: T("whatsapp.prix.aide") }));
    p.appendChild(el("div", { cls: "wa-rangee wa-rangee--prix wa-rangee--tete", a: { role: "row" } },
      ["marche"].concat(COLONNES).map(function (k) { return el("span", { a: { role: "columnheader" }, texte: T("whatsapp.prix.col_" + k) }); }).concat([el("span")])));
    p.appendChild(P.corps);
    p.appendChild(el("div", { cls: "wa-ligne" }, [
      W.bouton(T("whatsapp.prix.ajouter"), { a: { "data-dz-wa-prix-ajouter": true }, on: { click: function () { ligneDePrix("", null); } } }, "dz-action-ajouter"),
      el("span", { cls: "wa-espace" }),
      W.bouton(T("whatsapp.prix.enregistrer"), { cls: "wa-btn--primaire", a: { "data-dz-wa-prix-enregistrer": true }, on: { click: enregistrerPrix } }, "dz-action-enregistrer")
    ]));
    var r = await W.api("GET", "/api/cost/pricing");
    if (!r.ok || !r.data) { W.erreur(W.messageErreur(r)); return; }
    var g = r.data.whatsapp_meta_usd;
    dessinerGrille(g && typeof g === "object" ? g : {});
  }
  async function enregistrerPrix() {
    W.effacer();
    var lu = lireGrille();
    if (lu.erreur) { W.erreur(lu.erreur); return; }
    if (!Object.keys(lu.grille).length && !(await W.confirmer(T("whatsapp.prix.vide_confirmer")))) return;
    var r = await W.api("POST", "/api/cost/pricing", { whatsapp_meta_usd: lu.grille });
    if (!r.ok) { W.erreur(W.messageErreur(r)); return; }
    W.info(T("whatsapp.prix.enregistre"));
    var g = r.data && r.data.whatsapp_meta_usd;
    dessinerGrille(g && typeof g === "object" ? g : lu.grille);
  }

  W.onglets.modeles = { afficher: afficherModeles };
  W.onglets.contacts = { afficher: function (p) { return afficherContacts(p, false); } };
  W.onglets.sante = { afficher: afficherSante };
  W.onglets.prix = { afficher: afficherPrix };
})();
