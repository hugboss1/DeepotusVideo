/* dz-prospects.js — l'écran « Prospects » de l'agent Campagnes (t353, 27/10/2026, spec
   docs/superpowers/specs/2026-10-27-agent-veille-prospection-design.md §3, §6, §9.2, P2). SOURCE :
   frontend/shared/dz-prospects.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-prospects.js, chargée par
   frontend/dist/index.html (balise classique après dz-veille.js). Monté par le 4e onglet du tiroir F1 (dz-agent.js). Le banc
   backend/tests/test_prospects_ecran.py refuse toute dérive, le banc node frontend/shared/qa/prospects.test.mjs joue le
   composant sur un DOM simulé.

   window.DzProspects.monter(el, { espace_id }) -> { demonter(), recharger() }

   Le contrat du serveur (backend/app/api/prospects_routes.py) : GET /api/prospects/{eid} {prospects, compte_par_statut,
   oppositions} ; POST /{eid} ; PATCH · DELETE /{eid}/{pid} ; POST /{eid}/{pid}/statut|consentements|consentements/revoquer|
   contacts|opposer ; GET /{eid}/{pid}/export (pièce jointe) ; POST /api/prospects/oppositions. Un refus rend
   {detail: {code, message}} (message déjà traduit par le serveur). CRM léger : AUCUN bouton n'envoie de message ni ne
   dépense (P5-P6). La source et la base légale sont exigées. Tout texte est posé en textContent ; un lien de source n'est
   cliquable qu'en http(s), avec rel="noopener noreferrer". Libellés par dzT (prospects.objet.role). Vanilla DOM. */
(function () {
  "use strict";
  if (window.DzProspects) return;

  var BASE = "/api/prospects/";
  var STATUTS = ["propose", "qualifie", "contacte", "repondu", "rdv", "client", "perdu", "oppose"];
  var TRANSITIONS = {
    propose: ["qualifie", "perdu", "oppose"],
    qualifie: ["contacte", "perdu", "oppose"],
    contacte: ["repondu", "perdu", "oppose"],
    repondu: ["rdv", "client", "perdu", "oppose"],
    rdv: ["client", "perdu", "oppose"],
    perdu: ["qualifie", "oppose"],
    client: ["oppose"],
    oppose: []
  };
  var SOURCES = ["web", "liste_attente", "whatsapp", "telegram", "formulaire", "reponse_post", "recommandation", "salon", "autre"];
  var BASES = ["consentement", "interet_legitime_b2b", "mesures_precontractuelles"];
  var OFFRES = ["licence", "prestation", "a_definir"];
  var CANAUX = ["email", "whatsapp", "telephone", "x", "instagram", "linkedin", "site", "autre"];
  var MOYENS = ["ecrit", "formulaire", "inscription", "whatsapp", "oral"];
  var NOTES = ["demo_active", "plafond_espaces", "demo_absente", "demo_erreur"];
  var HISTO = ["creation", "modification", "statut", "consentement", "revocation", "contact_entrant", "contact_sortant", "opposition",
    "qualification", "a_l_humain"];
  var CRITERES = ["source_entrante", "source_web", "consentement", "canal_possible", "adresse_pro", "signal", "contact_recent"];   // t354
  var FOURNISSEURS = ["anthropic", "tavily", "exa", "serper"];   // t354 : recherche web de la prospection
  var SEQ_STATUTS = ["proposee", "validee", "planifiee", "terminee", "annulee"];   // t355 : séquences
  var ETAPE_STATUTS = ["brouillon", "validee", "planifiee", "envoyee", "annulee"];
  var SEQ_MOTIFS = ["effacee", "remplacee", "annulee", "canal", "rebond", "echec", "fenetre", "modele", "incertain"];
  var MOTIFS_HUMAIN = ["prix", "devis", "plainte", "stop", "autre"];   // t358 : passage à l'humain
  var EMAIL_MODES = ["smtp", "brevo"];   // t356 : canal e-mail
  var EMAIL_MANQUES = ["expediteur", "identite", "smtp", "imap", "mdp", "brevo"];
  var EMAIL_PAUSES = ["rebonds", "plainte"];
  var EMAIL_CHAMPS = ["nom", "adresse", "raison", "smtp_hote", "smtp_port", "smtp_user", "imap_hote", "imap_port", "imap_user", "plafond"];   // les saisies du panneau   // le motif d'un arrêt ; « fiche:<statut> » à part
  var SEQ_MANUELS = ["x", "instagram", "linkedin"];    // envoyés à la main : jamais de message automatique
  var SAISIS = ["email", "telephone", "whatsapp", "linkedin"];     // les canaux du formulaire ; les autres sont gardés tels quels
  var JSON_H = { "Content-Type": "application/json" };

  function T(cle, vars) { return typeof window.dzT === "function" ? window.dzT(cle, vars) : cle; }
  function lib(liste, prefixe, v) { return liste.indexOf(v) >= 0 ? T(prefixe + v) : String(v || ""); }
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
  function sur(url) { return typeof url === "string" && /^https?:\/\//i.test(url); }
  function aujourdhui() { var d = new Date(); return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); }
  function options(liste, prefixe, choisi) {
    return liste.map(function (v) {
      var o = el("option", { value: v, texte: T(prefixe + v) });
      if (v === choisi) o.setAttribute("selected", "");
      return o;
    });
  }
  function choix(attrs, enfants, valeur) {     // un select dont la valeur est posée (pas seulement l'attribut selected)
    var s = el("select", attrs, enfants);
    s.value = valeur;
    return s;
  }

  var CSS = ""
    + ".dzProspects{display:flex;flex-direction:column;flex:1 1 auto;min-height:0;height:100%;background:var(--bg-panel,#151519);color:var(--ink,#c4bfb6);"
    + "font-family:var(--f-ui,system-ui,sans-serif);font-size:13px;line-height:1.5}"
    + ".dzProspectsBarre{display:flex;flex-wrap:wrap;gap:6px;align-items:center;padding:8px 12px;border-bottom:1px solid var(--stroke,#2a2930)}"
    + ".dzProspects button{background:var(--bg-panel-2,#1c1c21);color:var(--ink-strong,#f2efe9);border:1px solid var(--stroke,#2a2930);border-radius:0;padding:3px 10px;font:inherit;cursor:pointer}"
    + ".dzProspects button[aria-pressed=true]{border-color:var(--accent,#f0b429);color:var(--accent,#f0b429)}"
    + ".dzProspects input,.dzProspects select,.dzProspects textarea{background:var(--bg-panel-2,#1c1c21);color:inherit;border:1px solid var(--stroke,#2a2930);border-radius:0;padding:3px 6px;font:inherit;min-width:0}"
    + ".dzProspectsCorps{flex:1;min-height:0;overflow:auto;padding:10px 12px;display:flex;flex-direction:column;gap:10px}"
    + ".dzProspects h3{margin:0 0 4px;font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--ink-strong,#f2efe9)}"
    + ".dzProspectsLigne{display:grid;grid-template-columns:1fr auto;gap:2px 8px;width:100%;text-align:left}"
    + ".dzProspectsMeta,.dzProspectsNote{font-size:11px;color:var(--ink-soft,#8a857d)}"
    + ".dzProspectsChamps{display:grid;grid-template-columns:minmax(90px,auto) 1fr;gap:4px 8px;align-items:center}"
    + ".dzProspectsErreur{color:var(--red,#e35d4a)}"
    + ".dzProspectsActions{display:flex;flex-wrap:wrap;gap:6px}"
    + ".dzProspects ul{margin:0;padding-left:18px}"
    + ".dzProspects a{color:var(--accent,#f0b429)}"
    + ".dzProspectsSeq{border:1px solid var(--stroke,#2a2930);padding:6px 8px;margin:6px 0;display:flex;flex-direction:column;gap:4px}"
    + ".dzProspectsEtape{border-left:2px solid var(--stroke,#2a2930);padding-left:8px}"
    + ".dzProspectsTableau{display:grid;grid-template-columns:repeat(8,minmax(150px,1fr));gap:8px;overflow-x:auto}"
    + ".dzProspectsColonne{display:flex;flex-direction:column;gap:6px;min-width:150px}"
    + ".dzProspectsCarte{display:flex;flex-direction:column;align-items:flex-start;gap:2px;text-align:left;width:100%}"
    + ".dzProspectsAReprendre{border-color:var(--red,#e35d4a)!important}"
    + ".dzProspectsTexte{white-space:pre-wrap;margin:2px 0;font:inherit;color:var(--ink,#c4bfb6)}"
    + ".dzProspectsPied{padding:6px 12px;border-top:1px solid var(--stroke,#2a2930);font-size:11px;color:var(--ink-soft,#8a857d)}";
  function poserCss() {
    if (document.getElementById && document.getElementById("dzProspectsCss")) return;
    var s = el("style", { id: "dzProspectsCss" });
    s.textContent = CSS;
    (document.head || document.documentElement).appendChild(s);
  }

  async function lireJson(r) { try { return await r.json(); } catch (e) { return {}; } }
  function refus(j) {
    var d = j && j.detail;
    if (d && typeof d === "object") return { code: String(d.code || ""), message: String(d.message || "") };
    return { code: "", message: typeof d === "string" ? d : "" };
  }

  function monter(hote, opts) {
    poserCss();
    var eid = opts && typeof opts.espace_id === "string" ? opts.espace_id : "";
    var vivant = true;
    var etat = { prospects: [], compte: {}, oppositions: 0, filtre: "", fiche: null, note: "" };
    var racine = el("div", { class: "dzProspects", "data-dz-prospects": "racine" });
    var barre = el("div", { class: "dzProspectsBarre" });
    var corps = el("div", { class: "dzProspectsCorps" });
    var pied = el("div", { class: "dzProspectsPied", "data-dz-prospects": "registre" });
    racine.appendChild(barre); racine.appendChild(corps); racine.appendChild(pied);
    hote.appendChild(racine);

    async function appel(methode, chemin, corpsJson) {
      var init = { method: methode };
      if (corpsJson !== undefined) { init.headers = JSON_H; init.body = JSON.stringify(corpsJson); }
      var r;
      try { r = await window.fetch(BASE + chemin, init); }
      catch (e) {      // t353 suite (M8) : serveur injoignable : on le dit, jamais un écran muet
        return { ok: false, status: 0, j: { detail: { code: "reseau", message: T("prospects.erreur.reseau") } } };
      }
      var j = await lireJson(r);
      return { ok: r.ok, status: r.status, j: j };
    }
    function erreur(zone, j) {
      var e = refus(j);
      vider(zone);
      zone.setAttribute("data-code", e.code);
      zone.appendChild(el("p", { class: "dzProspectsErreur", texte: e.message || T("prospects.erreur.inconnue") }));
    }

    async function recharger() {
      if (!eid) {
        vider(barre); vider(corps); vider(pied);
        corps.appendChild(el("p", { class: "dzProspectsNote", "data-dz-prospects": "sans-espace", texte: T("prospects.vide.sans_espace") }));
        return;
      }
      var r = await appel("GET", encodeURIComponent(eid));
      if (!vivant) return;
      if (!r.ok) { vider(corps); erreur(corps, r.j); return; }
      etat.prospects = Array.isArray(r.j.prospects) ? r.j.prospects : [];
      etat.compte = r.j.compte_par_statut || {};
      etat.oppositions = r.j.oppositions || 0;
      etat.misDeCote = r.j.registre_mis_de_cote || 0;     // relecture I2 : un registre illisible mis de côté
      etat.demos = r.j.espaces_demo && typeof r.j.espaces_demo === "object" ? r.j.espaces_demo : {};     // M8 : leurs noms
      if (etat.fiche) etat.fiche = etat.prospects.filter(function (p) { return p.id === etat.fiche.id; })[0] || null;
      dessiner();
    }

    function dessinerBarre() {
      vider(barre);
      var tous = el("button", { type: "button", "data-dz-prospects": "filtre-tous", "aria-pressed": etat.filtre ? "false" : "true",
        texte: T("prospects.filtre.tous", { n: etat.prospects.length }), on: { click: function () { etat.filtre = ""; etat.fiche = null; dessiner(); } } });
      barre.appendChild(tous);
      STATUTS.forEach(function (s) {
        var n = etat.compte[s] || 0;
        if (!n) return;
        barre.appendChild(el("button", { type: "button", "data-dz-prospects": "filtre-" + s, "aria-pressed": etat.filtre === s ? "true" : "false",
          texte: T("prospects.statut." + s) + " " + n, on: { click: function () { etat.filtre = s; etat.fiche = null; dessiner(); } } }));
      });
      barre.appendChild(el("button", { type: "button", "data-dz-prospects": "vue-tableau", "aria-pressed": etat.tableau ? "true" : "false",   // t358
        texte: T("prospects.bouton.tableau"), on: { click: function () { etat.tableau = !etat.tableau; etat.fiche = null; dessiner(); } } }));
      barre.appendChild(el("button", { type: "button", "data-dz-prospects": "ajouter", texte: T("prospects.bouton.ajouter"),
        on: { click: function () { etat.fiche = null; vider(corps); corps.appendChild(formulaire(null)); } } }));
      barre.appendChild(el("button", { type: "button", "data-dz-prospects": "opposition-saisir", texte: T("prospects.bouton.opposition"),
        on: { click: function () { vider(corps); corps.appendChild(saisieOpposition()); } } }));
      barre.appendChild(el("button", { type: "button", "data-dz-prospects": "recherche", texte: T("prospects.bouton.recherche"),
        on: { click: function () { vider(corps); corps.appendChild(reglageRecherche()); } } }));
      barre.appendChild(el("button", { type: "button", "data-dz-prospects": "email", texte: T("prospects.bouton.email"),   // t356
        on: { click: function () { vider(corps); corps.appendChild(reglageEmail()); } } }));
    }

    function dessiner() {
      if (!vivant) return;
      dessinerBarre();
      vider(corps);
      vider(pied);
      pied.appendChild(el("span", { texte: T("prospects.registre.compte", { n: etat.oppositions }) }));
      if (etat.misDeCote) pied.appendChild(el("p", { class: "dzProspectsErreur", "data-dz-prospects": "registre-illisible",
        texte: T("prospects.registre.illisible", { n: etat.misDeCote }) }));
      if (etat.fiche) { corps.appendChild(fiche(etat.fiche)); return; }
      if (etat.tableau) { corps.appendChild(tableau()); return; }       // t358
      var liste = etat.prospects.filter(function (p) { return !etat.filtre || p.statut === etat.filtre; });
      if (!liste.length) {
        corps.appendChild(el("p", { class: "dzProspectsNote", "data-dz-prospects": "vide", texte: T("prospects.vide.aucun") }));
        return;
      }
      liste.forEach(function (p) {
        var titre = p.entreprise ? (p.nom ? p.nom + " · " + p.entreprise : p.entreprise) : (p.nom || T("prospects.fiche.anonyme"));
        var meta = [lib(OFFRES, "prospects.offre.", p.offre)];
        if (p.score !== null && p.score !== undefined) meta.push(T("prospects.liste.score", { n: p.score }));
        if (p.prochaine_action && p.prochaine_action.texte) meta.push(T("prospects.liste.prochaine", { texte: p.prochaine_action.texte, le: p.prochaine_action.le || "—" }));
        meta.push(T("prospects.liste.purge", { le: p.purge_le || "—" }));
        if (p.par_agent) meta.push(T("prospects.liste.par_agent"));      // t354
        if (p.a_l_humain) meta.unshift(T("prospects.liste.a_reprendre", { motif: lib(MOTIFS_HUMAIN, "prospects.humain.", p.a_l_humain.motif) }));   // t358
        corps.appendChild(el("button", { type: "button", class: "dzProspectsLigne", "data-dz-prospects": "ligne", "data-id": p.id,
          on: { click: function () { etat.fiche = p; etat.note = ""; dessiner(); } } }, [
          el("strong", { texte: titre }), el("span", { texte: lib(STATUTS, "prospects.statut.", p.statut) }),
          el("span", { class: "dzProspectsMeta", texte: meta.join(" · ") })]));
      });
    }

    // t358 : le tableau du pipeline — une colonne par statut ; clic sur une carte = la fiche (ses boutons font les passages)
    function tableau() {
      var t = el("div", { class: "dzProspectsTableau", "data-dz-prospects": "tableau" });
      STATUTS.forEach(function (s) {
        var fiches = etat.prospects.filter(function (p) { return p.statut === s; });
        var col = el("div", { class: "dzProspectsColonne", "data-dz-prospects": "colonne-" + s }, [
          el("h3", { texte: T("prospects.statut." + s) + " · " + fiches.length })]);
        fiches.forEach(function (p) {
          var lignes = [p.entreprise || p.nom || T("prospects.fiche.anonyme")];
          if (p.score !== null && p.score !== undefined) lignes.push(T("prospects.liste.score", { n: p.score }));
          if (p.prochaine_action && p.prochaine_action.texte) lignes.push(p.prochaine_action.texte);
          var carte = el("button", { type: "button", class: "dzProspectsCarte" + (p.a_l_humain ? " dzProspectsAReprendre" : ""),
            "data-dz-prospects": "carte", "data-id": p.id, on: { click: function () { etat.fiche = p; etat.note = ""; dessiner(); } } },
            lignes.map(function (x, i) { return el(i ? "span" : "strong", { texte: x }); }));
          if (p.a_l_humain) carte.appendChild(el("span", { class: "dzProspectsErreur", "data-dz-prospects": "a-reprendre",
            texte: T("prospects.liste.a_reprendre", { motif: lib(MOTIFS_HUMAIN, "prospects.humain.", p.a_l_humain.motif) }) }));
          col.appendChild(carte);
        });
        t.appendChild(col);
      });
      return t;
    }

    function champ(cle, saisie) { return [el("label", { texte: T(cle) }), saisie]; }

    function formulaire(p) {
      var canal = function (t) { var c = (p && p.canaux || []).filter(function (x) { return x.type === t; })[0]; return c ? c.valeur : ""; };
      var src = (p && p.source) || {};
      var f = {
        nom: el("input", { "data-dz-prospects": "champ-nom", value: (p && p.nom) || "" }),
        entreprise: el("input", { "data-dz-prospects": "champ-entreprise", value: (p && p.entreprise) || "" }),
        role: el("input", { "data-dz-prospects": "champ-role", value: (p && p.role) || "" }),
        email: el("input", { type: "email", "data-dz-prospects": "champ-email", value: canal("email") }),
        telephone: el("input", { "data-dz-prospects": "champ-telephone", value: canal("telephone") }),
        whatsapp: el("input", { "data-dz-prospects": "champ-whatsapp", value: canal("whatsapp") }),
        linkedin: el("input", { "data-dz-prospects": "champ-linkedin", value: canal("linkedin") }),
        source: choix({ "data-dz-prospects": "champ-source" }, options(SOURCES, "prospects.source.", src.type || "web"), src.type || "web"),
        url: el("input", { "data-dz-prospects": "champ-url", value: src.url || "" }),
        date: el("input", { type: "date", "data-dz-prospects": "champ-date", value: src.date || aujourdhui() }),
        base: choix({ "data-dz-prospects": "champ-base" }, [el("option", { value: "", texte: T("prospects.base.choisir") })]
          .concat(options(BASES, "prospects.base.", p ? p.base_legale : "")), (p && p.base_legale) || ""),
        offre: choix({ "data-dz-prospects": "champ-offre" }, options(OFFRES, "prospects.offre.", (p && p.offre) || "a_definir"), (p && p.offre) || "a_definir"),
        score: el("input", { type: "number", min: "0", max: "100", "data-dz-prospects": "champ-score", value: p && p.score !== null && p.score !== undefined ? String(p.score) : "" }),
        signal: el("textarea", { "data-dz-prospects": "champ-signal" }),
        action: el("input", { "data-dz-prospects": "champ-action", value: (p && p.prochaine_action && p.prochaine_action.texte) || "" }),
        actionLe: el("input", { type: "date", "data-dz-prospects": "champ-action-le", value: (p && p.prochaine_action && p.prochaine_action.le) || "" })
      };
      f.signal.value = (p && p.signal) || "";
      ["nom", "entreprise", "role", "email", "telephone", "whatsapp", "linkedin", "url", "date", "score", "action", "actionLe"].forEach(function (k) {
        f[k].value = f[k].getAttribute("value") || "";
      });
      var aide = el("p", { class: "dzProspectsNote", "data-dz-prospects": "aide-base", texte: T("prospects.aide.base") });
      var zone = el("div", { "data-dz-prospects": "erreur" });
      function lire() {
        var canaux = SAISIS.filter(function (t) { return f[t].value.trim(); }).map(function (t) { return { type: t, valeur: f[t].value.trim() }; });
        if (p) canaux = canaux.concat((p.canaux || []).filter(function (c) { return SAISIS.indexOf(c.type) < 0; }));
        var c = { nom: f.nom.value, entreprise: f.entreprise.value, role: f.role.value, canaux: canaux,
          source: { type: f.source.value, url: f.url.value.trim(), date: f.date.value }, base_legale: f.base.value || null,
          offre: f.offre.value, signal: f.signal.value,
          prochaine_action: f.action.value.trim() ? { texte: f.action.value.trim(), le: f.actionLe.value || null } : null };
        c.score = f.score.value === "" ? null : Number(f.score.value);
        return c;
      }
      async function valider() {
        var r = p ? await appel("PATCH", encodeURIComponent(eid) + "/" + encodeURIComponent(p.id), lire())
          : await appel("POST", encodeURIComponent(eid), lire());
        if (!vivant) return;
        if (!r.ok) { erreur(zone, r.j); return; }
        etat.fiche = r.j; etat.note = "";
        await recharger();
      }
      return el("form", { "data-dz-prospects": p ? "formulaire-modifier" : "formulaire", on: { submit: function (ev) { ev.preventDefault(); valider(); } } }, [
        el("h3", { texte: T(p ? "prospects.titre.modifier" : "prospects.titre.ajouter") }),
        el("div", { class: "dzProspectsChamps" }, [].concat(
          champ("prospects.champ.nom", f.nom), champ("prospects.champ.entreprise", f.entreprise), champ("prospects.champ.role", f.role),
          champ("prospects.canal.email", f.email), champ("prospects.canal.telephone", f.telephone), champ("prospects.canal.whatsapp", f.whatsapp),
          champ("prospects.canal.linkedin", f.linkedin), champ("prospects.champ.source", f.source), champ("prospects.champ.url", f.url),
          champ("prospects.champ.date", f.date), champ("prospects.champ.base", f.base), champ("prospects.champ.offre", f.offre),
          champ("prospects.champ.score", f.score), champ("prospects.champ.signal", f.signal), champ("prospects.champ.action", f.action),
          champ("prospects.champ.action_le", f.actionLe))),
        aide, zone,
        el("div", { class: "dzProspectsActions" }, [
          el("button", { type: "submit", "data-dz-prospects": "valider", texte: T(p ? "prospects.bouton.enregistrer" : "prospects.bouton.creer") }),
          el("button", { type: "button", "data-dz-prospects": "annuler", texte: T("prospects.bouton.annuler"), on: { click: function () { dessiner(); } } })])
      ]);
    }

    async function geste(chemin, corpsJson, zone) {
      var r = await appel("POST", encodeURIComponent(eid) + "/" + encodeURIComponent(etat.fiche.id) + chemin, corpsJson);
      if (!vivant) return null;
      if (!r.ok) { erreur(zone, r.j); return null; }
      return r.j;
    }

    function fiche(p) {
      var zone = el("div", { "data-dz-prospects": "erreur" });
      var bloc = el("div", { "data-dz-prospects": "fiche", "data-id": p.id });
      var titre = p.entreprise || p.nom || T("prospects.fiche.anonyme");
      bloc.appendChild(el("div", { class: "dzProspectsActions" }, [
        el("button", { type: "button", "data-dz-prospects": "retour", texte: T("prospects.bouton.retour"), on: { click: function () { etat.fiche = null; dessiner(); } } })]));
      bloc.appendChild(el("h3", { texte: titre }));
      var infos = [
        T("prospects.fiche.statut", { statut: lib(STATUTS, "prospects.statut.", p.statut) }),
        T("prospects.fiche.offre", { offre: lib(OFFRES, "prospects.offre.", p.offre) }),
        T("prospects.fiche.base", { base: p.base_legale ? lib(BASES, "prospects.base.", p.base_legale) : "—" }),
        T("prospects.fiche.purge", { le: p.purge_le || "—" })
      ];
      if (p.nom && p.entreprise) infos.unshift(p.nom + (p.role ? " · " + p.role : ""));
      if (p.signal) infos.push(T("prospects.fiche.signal", { texte: p.signal }));
      bloc.appendChild(el("ul", {}, infos.map(function (t) { return el("li", { texte: t }); })));
      var src = p.source || {};
      var ligneSrc = el("p", { class: "dzProspectsMeta", "data-dz-prospects": "source" }, [
        el("span", { texte: T("prospects.fiche.source", { type: lib(SOURCES, "prospects.source.", src.type), date: src.date || "—" }) + " " })]);
      if (sur(src.url)) ligneSrc.appendChild(el("a", { href: src.url, target: "_blank", rel: "noopener noreferrer", texte: src.url }));
      else if (src.url) ligneSrc.appendChild(el("span", { texte: src.url }));
      bloc.appendChild(ligneSrc);
      if ((p.canaux || []).length) bloc.appendChild(el("ul", { "data-dz-prospects": "canaux" }, p.canaux.map(function (c) {
        return el("li", { texte: lib(CANAUX, "prospects.canal.", c.type) + " : " + c.valeur });
      })));
      if (p.espace_demo) bloc.appendChild(el("p", { class: "dzProspectsNote", "data-dz-prospects": "espace-demo",
        texte: T(p.statut === "client" ? "prospects.fiche.espace_client" : "prospects.fiche.espace_demo",
          { id: typeof (etat.demos || {})[p.espace_demo] === "string" ? etat.demos[p.espace_demo] : p.espace_demo }) }));
      if (p.par_agent) bloc.appendChild(el("p", { class: "dzProspectsNote", "data-dz-prospects": "par-agent", texte: T("prospects.fiche.par_agent") }));
      if (p.a_l_humain) bloc.appendChild(el("p", { class: "dzProspectsErreur", "data-dz-prospects": "a-reprendre",   // t358
        texte: T("prospects.fiche.a_reprendre", { motif: lib(MOTIFS_HUMAIN, "prospects.humain.", p.a_l_humain.motif), raison: p.a_l_humain.raison || "—" }) }));
      if (p.informer_avant) bloc.appendChild(el("p", { class: p.informer_avant < aujourdhui() ? "dzProspectsErreur" : "dzProspectsNote",
        "data-dz-prospects": "informer", texte: T("prospects.fiche.informer", { le: p.informer_avant }) }));     // t354 : RGPD art. 14
      if (p.statut !== "oppose") bloc.appendChild(blocQualification(p, zone));
      if (p.statut !== "oppose") bloc.appendChild(blocSequences(p, zone));     // t355
      if (etat.note && NOTES.indexOf(etat.note) >= 0) bloc.appendChild(el("p", { class: "dzProspectsNote", "data-dz-prospects": "note",
        "data-note": etat.note, texte: T("prospects.note." + etat.note) }));
      // statut : seuls les passages permis
      var suivants = TRANSITIONS[p.statut] || [];
      if (suivants.length) {
        bloc.appendChild(el("h3", { texte: T("prospects.titre.statut") }));
        bloc.appendChild(el("div", { class: "dzProspectsActions", "data-dz-prospects": "transitions" }, suivants.filter(function (s) { return s !== "oppose"; }).map(function (s) {
          return el("button", { type: "button", "data-dz-prospects": "statut-" + s, texte: T("prospects.statut." + s), on: { click: async function () {
            var j = await geste("/statut", { statut: s }, zone);
            if (j) { etat.fiche = j.prospect; etat.note = j.note || ""; await recharger(); }
          } } });
        })));
      }
      if (p.statut !== "oppose") {
        bloc.appendChild(el("div", { class: "dzProspectsActions" }, [
          el("button", { type: "button", "data-dz-prospects": "modifier", texte: T("prospects.bouton.modifier"), on: { click: function () {
            vider(corps); corps.appendChild(formulaire(p)); } } })]));
        // consentements
        bloc.appendChild(el("h3", { texte: T("prospects.titre.consentements") }));
        var cons = p.consentements || [];
        bloc.appendChild(cons.length ? el("ul", { "data-dz-prospects": "consentements" }, cons.map(function (c) {
          var li = el("li", { texte: T(c.revoque_le ? "prospects.consentement.revoque" : "prospects.consentement.ligne", {
            canal: lib(CANAUX, "prospects.canal.", c.canal), base: lib(BASES, "prospects.base.", c.base_legale),
            moyen: lib(MOYENS, "prospects.moyen.", c.moyen), date: c.date, revoque: c.revoque_le || "" }) + " " });
          if (!c.revoque_le) li.appendChild(el("button", { type: "button", "data-dz-prospects": "revoquer-" + c.canal, texte: T("prospects.bouton.revoquer"),
            on: { click: async function () { var j = await geste("/consentements/revoquer", { canal: c.canal }, zone); if (j) { etat.fiche = j; await recharger(); } } } }));
          return li;
        })) : el("p", { class: "dzProspectsNote", texte: T("prospects.vide.consentements") }));
        var cCanal = choix({ "data-dz-prospects": "consent-canal" }, options(CANAUX, "prospects.canal.", "email"), "email");
        var cBase = choix({ "data-dz-prospects": "consent-base" }, options(BASES, "prospects.base.", "consentement"), "consentement");
        var cMoyen = choix({ "data-dz-prospects": "consent-moyen" }, options(MOYENS, "prospects.moyen.", "ecrit"), "ecrit");
        bloc.appendChild(el("div", { class: "dzProspectsActions" }, [cCanal, cBase, cMoyen,
          el("button", { type: "button", "data-dz-prospects": "consent-ajouter", texte: T("prospects.bouton.consentement"), on: { click: async function () {
            var j = await geste("/consentements", { canal: cCanal.value, base_legale: cBase.value, moyen: cMoyen.value }, zone);
            if (j) { etat.fiche = j; await recharger(); } } } })]));
        // contacts
        var sens = choix({ "data-dz-prospects": "contact-sens" }, [
          el("option", { value: "entrant", texte: T("prospects.contact.entrant") }), el("option", { value: "sortant", texte: T("prospects.contact.sortant") })], "entrant");
        var detail = el("input", { "data-dz-prospects": "contact-detail", "aria-label": T("prospects.contact.detail"), placeholder: T("prospects.contact.detail") });
        bloc.appendChild(el("div", { class: "dzProspectsActions" }, [sens, detail,
          el("button", { type: "button", "data-dz-prospects": "contact-noter", texte: T("prospects.bouton.contact"), on: { click: async function () {
            var j = await geste("/contacts", { sens: sens.value, detail: detail.value }, zone);
            if (j) { etat.fiche = j; await recharger(); } } } })]));
        bloc.appendChild(el("p", { class: "dzProspectsNote", texte: T("prospects.aide.contact") }));
      }
      // historique
      var hist = (p.historique || []).slice().reverse();
      if (hist.length) {
        bloc.appendChild(el("h3", { texte: T("prospects.titre.historique") }));
        bloc.appendChild(el("ul", { "data-dz-prospects": "historique" }, hist.map(function (h) {
          return el("li", { texte: (h.quand || "").replace("T", " ").slice(0, 16) + " · " + lib(HISTO, "prospects.histo.", h.quoi) + (h.detail ? " · " + h.detail : "") });
        })));
      }
      // RGPD : export, opposition, effacement
      bloc.appendChild(el("h3", { texte: T("prospects.titre.donnees") }));
      var confirmer = el("div", { class: "dzProspectsActions", "data-dz-prospects": "confirmation" });
      var erronee = el("input", { type: "checkbox", "data-dz-prospects": "effacer-erronee" });
      bloc.appendChild(el("div", { class: "dzProspectsActions" }, [
        el("a", { href: BASE + encodeURIComponent(eid) + "/" + encodeURIComponent(p.id) + "/export", download: "prospect-" + p.id + ".json",
          "data-dz-prospects": "exporter", texte: T("prospects.bouton.exporter") }),
        p.statut !== "oppose" ? el("button", { type: "button", "data-dz-prospects": "opposer", texte: T("prospects.bouton.opposer"), on: { click: function () {
          vider(confirmer);
          confirmer.appendChild(el("span", { texte: T("prospects.confirmer.opposer") + " " }));
          confirmer.appendChild(el("button", { type: "button", "data-dz-prospects": "opposer-confirmer", texte: T("prospects.bouton.confirmer"), on: { click: async function () {
            var j = await geste("/opposer", undefined, zone); if (j) { etat.fiche = j; etat.note = ""; await recharger(); } } } }));
        } } }) : null,
        el("button", { type: "button", "data-dz-prospects": "effacer", texte: T("prospects.bouton.effacer"), on: { click: function () {
          vider(confirmer);
          confirmer.appendChild(el("span", { texte: T("prospects.confirmer.effacer") + " " }));
          confirmer.appendChild(el("label", {}, [erronee, el("span", { texte: " " + T("prospects.confirmer.erronee") })]));
          confirmer.appendChild(el("button", { type: "button", "data-dz-prospects": "effacer-confirmer", texte: T("prospects.bouton.confirmer"), on: { click: async function () {
            var r = await appel("DELETE", encodeURIComponent(eid) + "/" + encodeURIComponent(p.id) + (erronee.checked ? "?inscrire_opposition=0" : ""));
            if (!vivant) return;
            if (!r.ok) { erreur(zone, r.j); return; }
            etat.fiche = null; await recharger(); } } }));
        } } })]));
      bloc.appendChild(confirmer);
      bloc.appendChild(zone);
      return bloc;
    }

    // t354 : la qualification (barème du serveur, ajustement borné, raison, canaux possibles) et son recalcul
    function blocQualification(p, zone) {
      var q = p.qualification;
      var b = el("div", { "data-dz-prospects": "qualification" }, [el("h3", { texte: T("prospects.titre.qualification") })]);
      if (q && typeof q.base === "number") {
        var aj = (q.ajustement > 0 ? "+" : "") + String(q.ajustement || 0);
        var lignes = [T("prospects.qualif.score", { score: p.score, base: q.base, ajustement: aj })];
        if (q.raison) lignes.push(T("prospects.qualif.raison", { texte: q.raison }));
        (q.details || []).forEach(function (d) { lignes.push(T("prospects.qualif.critere", { critere: lib(CRITERES, "prospects.critere.", d.critere), points: d.points })); });
        (q.canaux_possibles || []).forEach(function (c) {
          lignes.push(T(c.mode === "manuel" ? "prospects.qualif.canal_manuel" : "prospects.qualif.canal_auto", { canal: lib(CANAUX, "prospects.canal.", c.canal) }));
        });
        if (q.canaux_possibles && q.canaux_possibles.some(function (c) { return c.mode === "manuel"; })) lignes.push(T("prospects.qualif.manuel"));
        b.appendChild(el("ul", {}, lignes.map(function (t) { return el("li", { texte: t }); })));
      } else b.appendChild(el("p", { class: "dzProspectsNote", texte: T("prospects.qualif.aucune") }));
      b.appendChild(el("div", { class: "dzProspectsActions" }, [el("button", { type: "button", "data-dz-prospects": "qualifier",
        texte: T("prospects.bouton.qualifier"), on: { click: async function () {
          var j = await geste("/qualifier", { offre: p.offre || "a_definir", ajustement: 0 }, zone);
          if (j) { etat.fiche = j; await recharger(); } } } })]));
      return b;
    }

    // t355 : les séquences de la fiche — porte 2 (Valider), Planifier, Annuler ; canaux manuels : Copier et ouvrir, Marquer envoyé
    function blocSequences(p, zone) {
      var b = el("div", { "data-dz-prospects": "sequences" }, [el("h3", { texte: T("prospects.titre.sequences") })]);
      var liste = el("div", {}, [el("p", { class: "dzProspectsNote", texte: T("prospects.sequence.chargement") })]);
      b.appendChild(liste);
      async function sgeste(sid, quoi, corpsJson) {
        var r = await appel("POST", encodeURIComponent(eid) + "/sequences/" + encodeURIComponent(sid) + "/" + quoi, corpsJson);
        if (!vivant) return;
        if (!r.ok) { erreur(zone, r.j); return; }
        vider(zone);
        await recharger();
      }
      function peindre(seqs) {
        vider(liste);
        if (!seqs.length) { liste.appendChild(el("p", { class: "dzProspectsNote", texte: T("prospects.sequence.aucune") })); return; }
        seqs.forEach(function (s) {
          var d = el("div", { class: "dzProspectsSeq", "data-dz-prospects": "sequence", "data-id": s.id, "data-statut": s.statut });
          d.appendChild(el("p", { class: "dzProspectsMeta", texte: T("prospects.sequence.entete", {
            canal: lib(CANAUX, "prospects.canal.", s.canal), statut: lib(SEQ_STATUTS, "prospects.seqstatut.", s.statut) }) }));
          var manuel = SEQ_MANUELS.indexOf(s.canal) >= 0;
          var prochaine = (s.etapes || []).filter(function (e) { return e.statut === "planifiee"; })[0];
          (s.etapes || []).forEach(function (e) {
            var li = el("div", { class: "dzProspectsEtape", "data-dz-prospects": "etape", "data-statut": e.statut }, [
              el("p", { class: "dzProspectsMeta", texte: T("prospects.sequence.etape", { n: e.rang + 1, jours: e.delai_jours,
                statut: lib(ETAPE_STATUTS, "prospects.etapestatut.", e.statut) }) + (e.quand ? " · " + new Date(e.quand).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" }) : "")
                + (e.due ? " · " + T("prospects.sequence.due") : "") })]);
            if (e.objet) li.appendChild(el("p", { texte: T("prospects.sequence.objet", { objet: e.objet }) }));
            if (e.modele && e.modele.nom) li.appendChild(el("p", { "data-dz-prospects": "etape-modele", texte: T("prospects.sequence.modele", { nom: String(e.modele.nom), langue: String(e.modele.langue || "") }) }));   // t357
            li.appendChild(el("pre", { class: "dzProspectsTexte", texte: e.texte }));
            if (manuel && s.statut === "planifiee" && prochaine && prochaine.rang === e.rang) {
              li.appendChild(el("div", { class: "dzProspectsActions" }, [
                el("button", { type: "button", "data-dz-prospects": "seq-copier", texte: T("prospects.bouton.copier_ouvrir"), on: { click: function () {
                  try { if (navigator.clipboard) navigator.clipboard.writeText(e.texte); } catch (x) { /* le texte reste lisible */ }
                  if (sur(s.ouvrir)) window.open(s.ouvrir, "_blank", "noopener,noreferrer"); } } }),
                el("button", { type: "button", "data-dz-prospects": "seq-envoye", texte: T("prospects.bouton.envoye"), on: { click: function () {
                  sgeste(s.id, "etapes/" + e.rang + "/envoye"); } } })]));
            }
            d.appendChild(li);
          });
          var acts = [];
          if (s.statut === "proposee") acts.push(el("button", { type: "button", "data-dz-prospects": "seq-valider", texte: T("prospects.bouton.valider_seq"),
            on: { click: function () { sgeste(s.id, "valider"); } } }));
          if (s.statut === "validee") acts.push(el("button", { type: "button", "data-dz-prospects": "seq-planifier", texte: T("prospects.bouton.planifier"),
            on: { click: function () { sgeste(s.id, "planifier", {}); } } }));
          if (["proposee", "validee", "planifiee"].indexOf(s.statut) >= 0) acts.push(el("button", { type: "button", "data-dz-prospects": "seq-annuler",
            texte: T("prospects.bouton.annuler_seq"), on: { click: function () { sgeste(s.id, "annuler"); } } }));
          if (s.statut === "planifiee" && !manuel) d.appendChild(el("p", { class: "dzProspectsNote", texte: T("prospects.sequence.auto") }));
          if (s.motif) d.appendChild(el("p", { class: "dzProspectsNote", "data-dz-prospects": "seq-motif", texte: String(s.motif).indexOf("fiche:") === 0
            ? T("prospects.sequence.arret", { statut: lib(STATUTS, "prospects.statut.", String(s.motif).slice(6)) })
            : lib(SEQ_MOTIFS, "prospects.seqmotif.", s.motif) }));
          if (acts.length) d.appendChild(el("div", { class: "dzProspectsActions" }, acts));
          liste.appendChild(d);
        });
      }
      appel("GET", encodeURIComponent(eid) + "/sequences?pid=" + encodeURIComponent(p.id)).then(function (r) {
        if (!vivant) return;
        if (r.ok) peindre(Array.isArray(r.j.sequences) ? r.j.sequences : []); else erreur(zone, r.j);
      });
      return b;
    }

    // t354 : le fournisseur de la recherche web d'entreprises (payante, lancée par une carte acceptée) et ses clés
    function reglageRecherche() {
      var zone = el("div", { "data-dz-prospects": "erreur" });
      var res = el("p", { class: "dzProspectsNote", "data-dz-prospects": "recherche-resultat" });
      var sel = el("select", { "data-dz-prospects": "recherche-fournisseur", "aria-label": T("prospects.recherche.fournisseur") });
      var cle = el("input", { type: "password", autocomplete: "off", "data-dz-prospects": "recherche-cle", "aria-label": T("prospects.recherche.cle"), placeholder: T("prospects.recherche.cle") });
      var etatR = el("ul", { "data-dz-prospects": "recherche-etat" });
      function peindre(j) {
        vider(sel); vider(etatR);
        var liste = j.fournisseurs && j.fournisseurs.length ? j.fournisseurs : FOURNISSEURS.map(function (f) { return { id: f }; });
        liste.forEach(function (f) {
          if (FOURNISSEURS.indexOf(f.id) < 0) return;
          sel.appendChild(el("option", { value: f.id, texte: T("prospects.recherche." + f.id) }));
          if (f.configure !== undefined) etatR.appendChild(el("li", { texte: T(f.configure ? "prospects.recherche.pret" : "prospects.recherche.sans_cle",
            { nom: T("prospects.recherche." + f.id), usd: String(f.prix_usd) }) }));
        });
        sel.value = j.fournisseur || "anthropic";
      }
      sel.addEventListener("change", async function () {
        var r = await appel("POST", "recherche/fournisseur", { fournisseur: sel.value });
        if (!vivant) return;
        if (!r.ok) { erreur(zone, r.j); return; }
        vider(zone); res.textContent = T("prospects.recherche.choisi");
      });
      var enregistrer = el("button", { type: "button", "data-dz-prospects": "recherche-cle-enregistrer", texte: T("prospects.bouton.cle"), on: { click: async function () {
        var r = await appel("POST", "recherche/cle", { fournisseur: sel.value, valeur: cle.value });
        cle.value = "";
        if (!vivant) return;
        if (!r.ok) { erreur(zone, r.j); return; }
        vider(zone); res.textContent = T("prospects.recherche.cle_posee");
        if (r.j && r.j.fournisseurs && r.j.fournisseurs.length) peindre(r.j);
      } } });
      appel("GET", "recherche").then(function (r) { if (!vivant) return; if (r.ok) peindre(r.j); else erreur(zone, r.j); });
      return el("div", { "data-dz-prospects": "recherche-reglage" }, [
        el("h3", { texte: T("prospects.titre.recherche") }),
        el("p", { class: "dzProspectsNote", texte: T("prospects.recherche.aide") }),
        el("div", { class: "dzProspectsActions" }, [sel, cle, enregistrer]), etatR, res, zone,
        el("button", { type: "button", "data-dz-prospects": "annuler", texte: T("prospects.bouton.retour"), on: { click: function () { dessiner(); } } })]);
    }

    // t356 : le canal e-mail de l'espace — SMTP de votre boîte ou Brevo, IMAP pour les réponses, identité, plafond, pause
    function reglageEmail() {
      if (!eid) return el("p", { class: "dzProspectsNote", texte: T("prospects.vide.sans_espace") });
      var zone = el("div", { "data-dz-prospects": "erreur" });
      var res = el("p", { class: "dzProspectsNote", "data-dz-prospects": "email-resultat" });
      var etatE = el("ul", { "data-dz-prospects": "email-etat" });
      var actions = el("div", { class: "dzProspectsActions" });
      var f = {};
      function saisie(cle, type) {
        f[cle] = el("input", { type: type || "text", autocomplete: "off", "data-dz-prospects": "email-" + cle, "aria-label": T("prospects.email." + cle) });
        return champ("prospects.email." + cle, f[cle]);
      }
      f.mode = el("select", { "data-dz-prospects": "email-mode", "aria-label": T("prospects.email.mode") },
        EMAIL_MODES.map(function (m) { return el("option", { value: m, texte: T("prospects.emailmode." + m) }); }));
      f.securite = el("select", { "data-dz-prospects": "email-securite", "aria-label": T("prospects.email.securite") },
        ["ssl", "starttls"].map(function (m) { return el("option", { value: m, texte: m.toUpperCase() }); }));
      f.postale = el("textarea", { rows: "2", "data-dz-prospects": "email-postale", "aria-label": T("prospects.email.postale") });
      var grille = el("div", { class: "dzProspectsChamps" }, [].concat(
        champ("prospects.email.mode", f.mode), saisie("nom"), saisie("adresse", "email"), saisie("raison"),
        champ("prospects.email.postale", f.postale), saisie("smtp_hote"), saisie("smtp_port", "number"),
        champ("prospects.email.securite", f.securite), saisie("smtp_user"), saisie("imap_hote"), saisie("imap_port", "number"),
        saisie("imap_user"), saisie("plafond", "number")));
      var mdp = el("input", { type: "password", autocomplete: "off", "data-dz-prospects": "email-mdp", "aria-label": T("prospects.email.mdp"), placeholder: T("prospects.email.mdp") });
      var brevo = el("input", { type: "password", autocomplete: "off", "data-dz-prospects": "email-brevo", "aria-label": T("prospects.email.brevo"), placeholder: T("prospects.email.brevo") });
      function peindre(j) {
        var x = j.expediteur || {}, id = j.identite || {}, s = j.smtp || {}, im = j.imap || {};
        f.mode.value = j.mode || "smtp";
        f.nom.value = x.nom || ""; f.adresse.value = x.adresse || "";
        f.raison.value = id.raison_sociale || ""; f.postale.value = id.adresse_postale || "";
        f.smtp_hote.value = s.hote || ""; f.smtp_port.value = String(s.port || 465); f.securite.value = s.securite || "ssl";
        f.smtp_user.value = s.utilisateur || "";
        f.imap_hote.value = im.hote || ""; f.imap_port.value = String(im.port || 993); f.imap_user.value = im.utilisateur || "";
        f.plafond.value = String(j.plafond_jour || 30);
        vider(etatE); vider(actions);
        var lignes = [j.pret ? T("prospects.email.pret") : T("prospects.email.manque", {
          liste: (j.manques || []).map(function (m) { return lib(EMAIL_MANQUES, "prospects.emailmanque.", m); }).join(", ") })];
        lignes.push(T("prospects.email.jour", { n: j.envoyes_du_jour || 0, plafond: j.plafond_du_jour || 0 }));
        lignes.push(T("prospects.email.rebonds", { pct: String(Math.round((j.taux_rebond || 0) * 1000) / 10) }));
        lignes.push(T(j.mdp_pose ? "prospects.email.mdp_pose" : "prospects.email.mdp_absent"));
        lignes.forEach(function (t) { etatE.appendChild(el("li", { texte: t })); });
        if (j.pause && j.pause.active) {
          etatE.appendChild(el("li", { class: "dzProspectsErreur", "data-dz-prospects": "email-pause",
            texte: T("prospects.email.pause", { motif: lib(EMAIL_PAUSES, "prospects.emailpause.", j.pause.motif) }) }));
          actions.appendChild(el("button", { type: "button", "data-dz-prospects": "email-reprendre", texte: T("prospects.bouton.reprendre"),
            on: { click: function () { geste_("reprendre"); } } }));
        }
        if (j.erreur && j.erreur.message) etatE.appendChild(el("li", { class: "dzProspectsErreur", "data-dz-prospects": "email-erreur", texte: j.erreur.message }));
        if (j.pret) actions.appendChild(el("button", { type: "button", "data-dz-prospects": "email-essai", texte: T("prospects.bouton.essai"),
          on: { click: function () { geste_("test", undefined, "prospects.email.essai_ok"); } } }));
      }
      async function geste_(quoi, corpsJson, ok) {
        var r = await appel("POST", encodeURIComponent(eid) + "/email" + (quoi ? "/" + quoi : ""), corpsJson);
        if (!vivant) return;
        if (!r.ok) { erreur(zone, r.j); return; }
        vider(zone);
        res.textContent = T(ok || "prospects.email.enregistre", { adresse: (r.j && r.j.envoye_a) || "" });
        if (quoi === "test") { var g = await appel("GET", encodeURIComponent(eid) + "/email"); if (vivant && g.ok) peindre(g.j); }
        else peindre(r.j);
      }
      var enregistrer = el("button", { type: "button", "data-dz-prospects": "email-enregistrer", texte: T("prospects.bouton.enregistrer_email"), on: { click: function () {
        geste_("", { mode: f.mode.value, expediteur: { nom: f.nom.value, adresse: f.adresse.value.trim() },
          identite: { raison_sociale: f.raison.value, adresse_postale: f.postale.value },
          smtp: { hote: f.smtp_hote.value.trim(), port: parseInt(f.smtp_port.value, 10) || 465, securite: f.securite.value, utilisateur: f.smtp_user.value.trim() },
          imap: { hote: f.imap_hote.value.trim(), port: parseInt(f.imap_port.value, 10) || 993, utilisateur: f.imap_user.value.trim() },
          plafond_jour: parseInt(f.plafond.value, 10) || 30 });
      } } });
      function poser(quoi, input) {
        return el("button", { type: "button", "data-dz-prospects": "email-" + quoi + "-enregistrer", texte: T("prospects.bouton.cle"), on: { click: function () {
          var v = input.value; input.value = "";
          geste_("secret", { quoi: quoi, valeur: v }, "prospects.email.secret_pose");
        } } });
      }
      appel("GET", encodeURIComponent(eid) + "/email").then(function (r) { if (!vivant) return; if (r.ok) peindre(r.j); else erreur(zone, r.j); });
      return el("div", { "data-dz-prospects": "email-reglage" }, [
        el("h3", { texte: T("prospects.titre.email") }),
        el("p", { class: "dzProspectsNote", texte: T("prospects.email.aide") }),
        grille, el("div", { class: "dzProspectsActions" }, [enregistrer]),
        el("div", { class: "dzProspectsActions" }, [mdp, poser("mdp", mdp)]),
        el("div", { class: "dzProspectsActions" }, [brevo, poser("brevo", brevo)]),
        etatE, actions, res, zone,
        el("button", { type: "button", "data-dz-prospects": "annuler", texte: T("prospects.bouton.retour"), on: { click: function () { dessiner(); } } })]);
    }

    function saisieOpposition() {
      var champ_ = el("input", { "data-dz-prospects": "opposition-identifiant", "aria-label": T("prospects.opposition.identifiant"), placeholder: T("prospects.opposition.identifiant") });
      var zone = el("div", { "data-dz-prospects": "erreur" });
      var res = el("p", { class: "dzProspectsNote", "data-dz-prospects": "opposition-resultat" });
      return el("div", { "data-dz-prospects": "opposition" }, [
        el("h3", { texte: T("prospects.titre.opposition") }),
        el("p", { class: "dzProspectsNote", texte: T("prospects.opposition.aide") }),
        el("div", { class: "dzProspectsActions" }, [champ_,
          el("button", { type: "button", "data-dz-prospects": "opposition-inscrire", texte: T("prospects.bouton.inscrire"), on: { click: async function () {
            var r = await appel("POST", "oppositions", { identifiant: champ_.value });
            if (!vivant) return;
            if (!r.ok) { erreur(zone, r.j); return; }
            vider(zone); champ_.value = "";
            res.textContent = T(r.j.inscrit ? "prospects.opposition.inscrite" : "prospects.opposition.deja");
            if (r.j.inscrit) etat.oppositions += 1;
          } } }),
          // t353 suite (M6) : une saisie erronée se retire (journalisé) ; une opposition de la personne, non (409 dit)
          el("button", { type: "button", "data-dz-prospects": "opposition-retirer", texte: T("prospects.bouton.retirer"), on: { click: async function () {
            var r = await appel("POST", "oppositions/retirer", { identifiant: champ_.value });
            if (!vivant) return;
            if (!r.ok) { res.textContent = ""; erreur(zone, r.j); return; }
            vider(zone); champ_.value = "";
            res.textContent = T(r.j.retire ? "prospects.opposition.retiree" : "prospects.opposition.absente");
            if (r.j.retire) etat.oppositions = Math.max(0, etat.oppositions - 1);
          } } }),
          el("button", { type: "button", "data-dz-prospects": "annuler", texte: T("prospects.bouton.retour"), on: { click: function () { dessiner(); } } })]),
        res, zone]);
    }

    recharger();
    return {
      demonter: function () { vivant = false; if (racine.parentNode) racine.parentNode.removeChild(racine); },
      recharger: recharger
    };
  }

  window.DzProspects = { monter: monter };
})();
