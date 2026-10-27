/* onglets-conversations.js — l'onglet CONVERSATIONS de la page WhatsApp (t311 tâche 7). S'inscrit dans
   window.__dzWhatsapp.onglets.conversations = { afficher(panneau), rafraichir() } (socle : whatsapp.js).
   · Liste : GET …/conversations + GET …/brouillons. Pastilles : fenêtre de 24 h ouverte ou fermée, STOP, « à reprendre »
     (brouillon `humain`), brouillon en attente (`attente`). Une entrée de brouillon SANS etat (traces du relevé de fond,
     `traite_jusqu_a` seul) n'est pas un brouillon. Le brouillon est cherché sous l'identité ET son alias (etat.alias).
   · Fil : POST …/relire (jamais le GET messages), filtré sur le contact (et son alias), du plus ancien au plus récent ;
     « Plus anciens » suit le curseur `suivant` (apres). Bulles : texte (textContent), heure, statut traduit (sortants),
     image depuis la route média, autre média en lien de téléchargement.
   · Saisie : fenêtre ouverte -> texte + 1 à 3 boutons (20 caractères, compteur) ; fenêtre fermée -> bandeau « modèles
     seulement » et « Envoyer un modèle » ; contact en STOP -> bandeau, rien d'autre. Modèle en deux temps : choisir
     (GET …/modeles, approuvés), puis remplir les paramètres nommés (noms_parametres) ou positionnels, l'en-tête (texte
     variable ou identifiant de média) et les payloads des boutons de réponse rapide.
   · Brouillon de l'agent : texte modifiable, « Envoyer » (decider envoyer + texte), « Rejeter », « Faire rédiger »
     (…/brouillons/rediger, motif traduit). « Prendre le fil » / « Rendre le fil » (…/fil).
   La saisie et la carte du brouillon ne sont reconstruites que si le contact, la fenêtre, le STOP ou le brouillon
   changent : un rafraîchissement de 30 s n'efface jamais ce que l'utilisateur tape. */
(function () {
  "use strict";
  var W = window.__dzWhatsapp;
  if (!W || W.onglets.conversations) return;
  var T = W.T, el = W.el, S = W.S;
  var STATUTS = ["accepted", "pending", "sent", "delivered", "read", "failed"];
  var TYPES = ["image", "video", "audio", "document", "sticker"];
  var MOTIFS = ["carte", "declencheur", "sans_cle", "plafond", "moteur", "max_tours", "sans_carte", "stop", "sans_entrant", "occupee"];
  var RAISONS = ["mot_cle", "argent", "negatif"];
  var MAX_TEXTE = 4096, MAX_CORPS_BOUTONS = 1024, MAX_PARAMETRE = 1024;
  var C = {};

  function courant() { return (S.convs || []).filter(function (c) { return c.identite === S.sel; })[0] || null; }
  function typeLisible(t) { return TYPES.indexOf(t) >= 0 ? T("whatsapp.type." + t) : String(t || ""); }

  // ── squelette ───────────────────────────────────────────────────────────────────────────────────────────────────────
  async function afficher(p) {
    if (!p.hasAttribute("data-dz-wa-pret")) {
      p.textContent = "";
      C = { sigSaisie: null, sigBrouillon: null, titres: [], occupe: false };
      C.liste = el("div", { cls: "wa-liste", a: { "data-dz-wa-convs": true, role: "list" } });
      C.nom = el("h2", { cls: "wa-contact" });
      C.btnsFil = [
        W.bouton(T("whatsapp.fil.prendre"), { a: { "data-dz-wa-fil-action": "prendre" }, titre: T("whatsapp.fil.prendre_aide"), on: { click: function () { fil("prendre"); } } }, "dz-action-reprendre-reglages"),
        W.bouton(T("whatsapp.fil.rendre"), { a: { "data-dz-wa-fil-action": "rendre" }, titre: T("whatsapp.fil.rendre_aide"), on: { click: function () { fil("rendre"); } } }, "dz-etat-ia")
      ];
      C.actions = el("div", { cls: "wa-actions-fil" }, C.btnsFil);
      C.plus = W.bouton(T("whatsapp.fil.plus_anciens"), { cls: "wa-btn--discret", a: { "data-dz-wa-plus": true }, on: { click: function () { relireFil(true); } } });
      C.plus.hidden = true;
      C.fil = el("div", { cls: "wa-fil", a: { "data-dz-wa-fil": true, "aria-live": "polite" } });
      C.brouillon = el("div", { cls: "wa-zone-brouillon" });
      C.saisie = el("div", { cls: "wa-saisie", a: { "data-dz-wa-saisie": true } });
      C.modele = el("div", { cls: "wa-modele" });
      C.vue = el("section", { cls: "wa-conv" }, [el("div", { cls: "wa-conv-tete" }, [C.nom, C.actions]), C.plus, C.fil, C.brouillon, C.modele, C.saisie]);
      C.choisir = el("p", { cls: "wa-aide wa-choisir", texte: T("whatsapp.conv.choisir") });
      p.appendChild(el("div", { cls: "wa-conversations" }, [C.liste, el("div", { cls: "wa-droite" }, [C.choisir, C.vue])]));
      p.setAttribute("data-dz-wa-pret", "");
    }
    await rafraichir();
  }

  async function rafraichir() {
    var g = S.gen;
    var rs = await Promise.all([W.api("GET", W.waUrl("/conversations")), W.api("GET", W.waUrl("/brouillons"))]);
    if (W.perime(g)) return;
    if (rs[0].ok && Array.isArray(rs[0].data)) S.convs = rs[0].data;
    else if (!rs[0].ok) W.erreur(W.messageErreur(rs[0]));
    if (rs[1].ok && rs[1].data && typeof rs[1].data === "object") {
      var b = rs[1].data;
      S.brouillons = b.brouillons && typeof b.brouillons === "object" && !Array.isArray(b.brouillons) ? b.brouillons : b;
    }
    afficherListe();
    if (S.sel) { await relireFil(false); if (W.perime(g)) return; afficherConversation(false); }
    else afficherConversation(false);
  }

  // ── la liste ────────────────────────────────────────────────────────────────────────────────────────────────────────
  function pastille(genre, cle) {
    return el("span", { cls: "wa-pastille wa-pastille--" + genre, a: { "data-dz-wa-pastille": genre } }, [W.icone(cle, 12), el("span", { texte: T("whatsapp.pastille." + genre) })]);
  }
  function afficherListe() {
    C.liste.textContent = "";
    var convs = S.convs || [];
    if (!convs.length) { C.liste.appendChild(el("p", { cls: "wa-aide", texte: T("whatsapp.conv.aucune") })); return; }
    convs.forEach(function (c) {
      var b = W.brouillonDe(c.identite);
      var pastilles = el("span", { cls: "wa-pastilles" }, [
        c.fenetre_ouverte ? pastille("ouverte", "dz-etat-actif") : pastille("fermee", "dz-etat-verrouille"),
        c.stop ? pastille("stop", "dz-etat-exclu") : null,
        b && b.etat === "humain" ? pastille("humain", "dz-etat-avertissement") : null,
        b && b.etat === "attente" ? pastille("brouillon", "dz-etat-note") : null
      ]);
      var item = el("button", { cls: "wa-conv-item", type: "button", a: { role: "listitem", "data-dz-wa-conv": c.identite, "aria-current": c.identite === S.sel ? "true" : null },
                                on: { click: function () { selectionner(c.identite); } } }, [
        el("span", { cls: "wa-conv-nom", texte: c.nom || c.identite }),
        el("span", { cls: "wa-conv-sous", texte: (c.nom ? c.identite + " · " : "") + (c.dernier_entrant ? W.heure(c.dernier_entrant) : T("whatsapp.conv.jamais")) }),
        pastilles
      ]);
      C.liste.appendChild(item);
    });
  }

  async function selectionner(identite) {
    S.sel = identite; S.msgs = []; S.suivant = null;
    C.sigSaisie = null; C.sigBrouillon = null; C.titres = [];
    C.modele.textContent = "";
    W.effacer();
    afficherListe();
    afficherConversation(true);
    var g = S.gen;
    await relireFil(false);
    if (W.perime(g) || S.sel !== identite) return;
    afficherConversation(false);
  }

  // ── le fil ──────────────────────────────────────────────────────────────────────────────────────────────────────────
  async function relireFil(plus) {
    if (!S.sel) return;
    var corps = plus && S.suivant ? { apres: S.suivant } : {};
    var sel = S.sel, gen = S.gen;
    var r = await W.api("POST", W.waUrl("/relire"), corps);
    if (W.perime(gen) || sel !== S.sel) return;
    if (!r.ok || !r.data) { W.erreur(W.messageErreur(r)); return; }
    var grp = W.groupe(sel);
    var neufs = (r.data.messages || []).filter(function (m) { return m && grp.indexOf(m.identite) >= 0; });
    // fusion par id : une relecture met à jour les statuts sans perdre les pages plus anciennes déjà lues
    var parId = {};
    neufs.forEach(function (m) { parId[m.id] = 1; });
    S.msgs = neufs.concat((S.msgs || []).filter(function (m) { return !parId[m.id]; }));
    if (plus || !S.suivant) S.suivant = r.data.suivant || null;
    afficherFil();
  }
  function bulle(m) {
    var sens = m.sens === "sortant" ? "sortant" : "entrant";
    var b = el("div", { cls: "wa-bulle wa-bulle--" + sens, a: { "data-dz-wa-bulle": sens } });
    if (m.media_id) {
      if (m.type === "image" || m.type === "sticker") {
        b.appendChild(el("img", { cls: "wa-media", a: { src: W.mediaUrl(m.media_id), alt: typeLisible(m.type), loading: "lazy", "data-dz-wa-media": "image" } }));
      } else {
        b.appendChild(el("a", { cls: "wa-lien", a: { href: W.mediaUrl(m.media_id), download: true, "data-dz-wa-media": "lien" } },
                         [W.icone("dz-action-telecharger"), el("span", { texte: T("whatsapp.fil.telecharger", { type: typeLisible(m.type) }) })]));
      }
    }
    if (m.texte) b.appendChild(el("p", { cls: "wa-bulle-texte", texte: m.texte }));
    else if (!m.media_id) b.appendChild(el("p", { cls: "wa-bulle-texte wa-sous", texte: T("whatsapp.fil.sans_texte", { type: typeLisible(m.type) }) }));
    if (m.bouton && m.bouton.titre) b.appendChild(el("p", { cls: "wa-bulle-bouton", texte: T("whatsapp.fil.bouton", { titre: m.bouton.titre }) }));
    var meta = el("span", { cls: "wa-bulle-meta" }, [el("span", { texte: W.heure(m.quand) })]);
    if (sens === "sortant" && m.statut) {
      var st = String(m.statut);
      meta.appendChild(el("span", { cls: "wa-statut wa-statut--" + (STATUTS.indexOf(st) >= 0 ? st : "autre"), a: { "data-dz-wa-statut": st },
                                    texte: STATUTS.indexOf(st) >= 0 ? T("whatsapp.statut." + st) : T("whatsapp.statut.autre", { statut: st }) }));
    }
    b.appendChild(meta);
    return b;
  }
  function afficherFil() {
    C.fil.textContent = "";
    var msgs = (S.msgs || []).slice().sort(function (a, b) { return String(a.quand || "").localeCompare(String(b.quand || "")); });
    if (!msgs.length) C.fil.appendChild(el("p", { cls: "wa-aide", texte: T("whatsapp.fil.vide") }));
    msgs.forEach(function (m) { C.fil.appendChild(bulle(m)); });
    C.plus.hidden = !S.suivant;
    try { C.fil.scrollTop = C.fil.scrollHeight || 0; } catch (e) { /* rien */ }
  }

  // ── la conversation choisie ─────────────────────────────────────────────────────────────────────────────────────────
  function afficherConversation(force) {
    var c = courant();
    C.choisir.hidden = !!S.sel;
    C.vue.hidden = !S.sel;
    if (!S.sel) return;
    C.nom.textContent = c ? (c.nom || c.identite) : S.sel;
    var b = W.brouillonDe(S.sel);
    var sigB = b ? b.etat + "|" + (b.cree_le || "") : "";
    if (force || sigB !== C.sigBrouillon) { C.sigBrouillon = sigB; afficherBrouillon(b, c); }
    var sigS = c ? S.sel + "|" + (c.fenetre_ouverte ? "o" : "f") + (c.stop ? "s" : "") : S.sel + "|?";
    if (force || sigS !== C.sigSaisie) {
      // reconstruite sous les yeux de l'utilisateur (même contact) : on dit pourquoi la saisie a changé
      var meme = !force && !!C.sigSaisie && C.sigSaisie.indexOf(S.sel + "|") === 0;
      var avantOuverte = meme && C.sigSaisie.charAt(S.sel.length + 1) === "o", avantStop = meme && /s$/.test(C.sigSaisie);
      C.sigSaisie = sigS;
      afficherSaisie(c);
      if (meme && c && c.stop && !avantStop) W.info(T("whatsapp.saisie.devenu_stop"));
      else if (meme && c && !c.fenetre_ouverte && avantOuverte) W.info(T("whatsapp.saisie.fenetre_vient_de_fermer"));
    }
  }

  // ── le brouillon ────────────────────────────────────────────────────────────────────────────────────────────────────
  function afficherBrouillon(b, c) {
    C.brouillon.textContent = "";
    C.zBrouillon = null;
    C.btnRediger = W.bouton(T("whatsapp.brouillon.rediger"), { a: { "data-dz-wa-rediger": true }, titre: T("whatsapp.brouillon.rediger_aide"), on: { click: rediger } }, "dz-action-reecrire-ia");
    C.btnsBrouillon = [];
    var outils = el("div", { cls: "wa-ligne" }, [C.btnRediger]);
    if (!b) { C.brouillon.appendChild(outils); return; }
    var carte = b.carte && typeof b.carte === "object" ? b.carte : null;
    var args = carte && carte.arguments && typeof carte.arguments === "object" ? carte.arguments : {};
    var boite = el("div", { cls: "wa-brouillon wa-brouillon--" + b.etat, a: { "data-dz-wa-brouillon": b.etat } });
    boite.appendChild(el("div", { cls: "wa-brouillon-tete" }, [W.icone(b.etat === "humain" ? "dz-etat-avertissement" : "dz-etat-ia"),
      el("b", { texte: T(b.etat === "humain" ? "whatsapp.brouillon.titre_humain" : "whatsapp.brouillon.titre_attente") })]));
    var raison = b.raison || (carte && carte.genre === "humain" ? args.raison : null);
    if (raison) boite.appendChild(el("p", { cls: "wa-aide", texte: T("whatsapp.brouillon.raison", { raison: RAISONS.indexOf(raison) >= 0 ? T("whatsapp.raison." + raison) : String(raison) }) }));
    var decide = el("div", { cls: "wa-ligne" });
    C.btnsBrouillon = [];
    if (b.etat === "attente" && carte && carte.genre === "reponse_whatsapp") {
      C.zBrouillon = W.champ({ tag: "textarea", cls: "wa-champ--texte", label: T("whatsapp.brouillon.texte"), value: String(args.texte || ""), a: { "data-dz-wa-brouillon-texte": true, rows: "3" } });
      boite.appendChild(C.zBrouillon);
    } else if (b.etat === "attente" && carte && carte.genre === "modele_whatsapp") {
      boite.appendChild(el("p", { texte: T("whatsapp.brouillon.modele", { nom: String(args.nom || ""), langue: String(args.langue || "") }) }));
      var pr = args.parametres;
      var lignes = Array.isArray(pr) ? pr.map(function (v, i) { return [String(i + 1), v]; }) : Object.keys(pr || {}).map(function (k) { return [k, pr[k]]; });
      lignes.forEach(function (l) { boite.appendChild(el("p", { cls: "wa-sous", texte: T("whatsapp.brouillon.parametre", { nom: l[0], valeur: String(l[1]) }) })); });
    } else if (b.etat === "humain") {
      boite.appendChild(el("p", { cls: "wa-aide", texte: T("whatsapp.brouillon.humain_aide") }));
    }
    if (b.etat === "attente") C.btnsBrouillon.push(decide.appendChild(W.bouton(T("whatsapp.brouillon.envoyer"), { cls: "wa-btn--primaire", a: { "data-dz-wa-decider": "envoyer" }, on: { click: function () { decider("envoyer"); } } }, "dz-action-publier")));
    C.btnsBrouillon.push(decide.appendChild(W.bouton(T("whatsapp.brouillon.rejeter"), { a: { "data-dz-wa-decider": "rejeter" }, on: { click: function () { decider("rejeter"); } } }, "dz-action-abandonner")));
    if (C.zBrouillon) C.btnsBrouillon.push(C.zBrouillon);
    boite.appendChild(decide);
    C.brouillon.appendChild(boite);
    C.brouillon.appendChild(outils);
  }
  async function relireBrouillons() {
    var g = S.gen;
    var r = await W.api("GET", W.waUrl("/brouillons"));
    if (W.perime(g)) return;
    if (r.ok && r.data && typeof r.data === "object") {
      S.brouillons = r.data.brouillons && typeof r.data.brouillons === "object" && !Array.isArray(r.data.brouillons) ? r.data.brouillons : r.data;
    }
    afficherListe();
    var b = W.brouillonDe(S.sel);
    C.sigBrouillon = b ? b.etat + "|" + (b.cree_le || "") : "";
    afficherBrouillon(b, courant());
  }
  // tout ce que l'utilisateur peut toucher pendant un appel de la conversation (envoi, modèle, décision, rédaction)
  function gardes() {
    return [C.btnRediger, C.btnEnvoyer, C.btnModele, C.zTexte, C.ajouter, C.btnModeleEnvoyer]
      .concat(C.btnsBrouillon || [], C.champsModele || [], (C.titres || []).map(function (l) { return l.champ; }));
  }
  function apresAppel() { if (C.ajouter) C.ajouter.disabled = (C.titres || []).length >= W.MAX_BOUTONS; }
  async function decider(decision) {
    if (!S.sel) return;
    var sel = S.sel, g = S.gen;
    var corps = { identite: sel, decision: decision };
    if (decision === "envoyer" && C.zBrouillon) corps.texte = C.zBrouillon.value;
    await W.occuper(C, gardes(), async function () {
      W.effacer();
      var r = await W.api("POST", W.waUrl("/brouillons/decider"), corps);
      if (W.perime(g) || sel !== S.sel) return;
      if (!r.ok) { W.erreur(W.messageErreur(r)); return; }
      W.info(T(decision === "envoyer" ? "whatsapp.brouillon.envoye" : "whatsapp.brouillon.rejete"));
      await relireBrouillons();
      if (decision === "envoyer" && !W.perime(g)) await relireFil(false);
    });
    apresAppel();
  }
  async function rediger() {
    if (!S.sel) return;
    var sel = S.sel, g = S.gen;
    await W.occuper(C, gardes(), async function () {
      W.effacer();
      W.info(T("whatsapp.brouillon.redaction"));
      var r = await W.api("POST", W.waUrl("/brouillons/rediger"), { identite: sel, langue: W.langue() });
      if (W.perime(g) || sel !== S.sel) return;
      if (!r.ok) { W.erreur(W.messageErreur(r)); return; }
      var motif = r.data && r.data.motif;
      W.info(MOTIFS.indexOf(motif) >= 0 ? T("whatsapp.motif." + motif) : T("whatsapp.motif.autre", { motif: String(motif || "") }));
      await relireBrouillons();
    });
    apresAppel();
  }
  var GF = {};
  async function fil(action) {
    if (!S.sel) return;
    var sel = S.sel, g = S.gen;
    await W.occuper(GF, C.btnsFil, async function () {
      W.effacer();
      var r = await W.api("POST", W.waUrl("/fil"), { identite: sel, action: action });
      if (W.perime(g) || sel !== S.sel) return;
      if (!r.ok) { W.erreur(W.messageErreur(r)); return; }
      W.info(T(action === "prendre" ? "whatsapp.fil.pris" : "whatsapp.fil.rendu"));
    });
  }

  // ── la saisie ───────────────────────────────────────────────────────────────────────────────────────────────────────
  function afficherSaisie(c) {
    C.saisie.textContent = "";
    C.zTexte = null; C.titres = []; C.btnEnvoyer = null; C.btnModele = null; C.ajouter = null;
    if (!c) return;
    var boutonModele = function () {
      return W.bouton(T("whatsapp.saisie.envoyer_modele"), { a: { "data-dz-wa-modele-ouvrir": true }, on: { click: ouvrirModele } }, "dz-nav-templates");
    };
    if (c.stop) {
      C.saisie.appendChild(el("div", { cls: "wa-bandeau wa-bandeau--stop", a: { "data-dz-wa-bandeau": "stop" } }, [W.icone("dz-etat-exclu"), el("span", { texte: T("whatsapp.saisie.stop") })]));
      return;
    }
    if (!c.fenetre_ouverte) {
      C.saisie.appendChild(el("div", { cls: "wa-bandeau", a: { "data-dz-wa-bandeau": "modeles" } }, [W.icone("dz-etat-verrouille"), el("span", { texte: T("whatsapp.saisie.fenetre_fermee") })]));
      C.btnModele = boutonModele();
      C.saisie.appendChild(el("div", { cls: "wa-ligne" }, [C.btnModele]));
      return;
    }
    C.zTexte = W.champ({ tag: "textarea", cls: "wa-champ--texte", label: T("whatsapp.saisie.texte"), placeholder: T("whatsapp.saisie.texte_ph"), a: { "data-dz-wa-texte": true, rows: "3" } });
    C.zBoutons = el("div", { cls: "wa-boutons-msg" });
    C.ajouter = W.bouton(T("whatsapp.saisie.ajouter_bouton"), { a: { "data-dz-wa-bouton-ajouter": true }, titre: T("whatsapp.saisie.ajouter_bouton_aide"), on: { click: ajouterBouton } }, "dz-action-ajouter");
    C.saisie.appendChild(C.zTexte);
    C.saisie.appendChild(C.zBoutons);
    C.btnModele = boutonModele();
    C.btnEnvoyer = W.bouton(T("whatsapp.saisie.envoyer"), { cls: "wa-btn--primaire", a: { "data-dz-wa-envoyer": true }, on: { click: envoyer } }, "dz-action-publier");
    C.saisie.appendChild(el("div", { cls: "wa-ligne" }, [C.ajouter, C.btnModele, el("span", { cls: "wa-espace" }), C.btnEnvoyer]));
  }
  function majCompteur(ligne) {
    var n = ligne.champ.value.length;
    ligne.compteur.textContent = T("whatsapp.saisie.compteur", { n: n, max: W.MAX_TITRE });
    ligne.compteur.classList.toggle("trop", n > W.MAX_TITRE);
  }
  function ajouterBouton() {
    if (C.titres.length >= W.MAX_BOUTONS) { C.ajouter.disabled = true; return; }
    var ligne = {};
    ligne.champ = W.champ({ label: T("whatsapp.saisie.titre_bouton"), placeholder: T("whatsapp.saisie.titre_bouton"), a: { "data-dz-wa-bouton-titre": true },
                            on: { input: function () { majCompteur(ligne); } } });
    ligne.compteur = el("span", { cls: "wa-compteur", a: { "data-dz-wa-compteur": true } });
    ligne.noeud = el("div", { cls: "wa-ligne wa-bouton-msg" }, [ligne.champ, ligne.compteur,
      W.bouton("", { titre: T("whatsapp.saisie.retirer_bouton"), a: { "data-dz-wa-bouton-retirer": true }, on: { click: function () {
        ligne.noeud.remove(); C.titres = C.titres.filter(function (x) { return x !== ligne; }); C.ajouter.disabled = false; } } }, "dz-action-retirer")]);
    C.titres.push(ligne);
    C.zBoutons.appendChild(ligne.noeud);
    majCompteur(ligne);
    C.ajouter.disabled = C.titres.length >= W.MAX_BOUTONS;
  }
  async function envoyer() {
    if (C.occupe || !S.sel || !C.zTexte) return;
    W.effacer();
    var texte = C.zTexte.value;
    var titres = C.titres.map(function (l) { return l.champ.value.trim(); }).filter(function (t) { return t; });
    if (!texte.trim()) { W.erreur(T("whatsapp.saisie.texte_vide")); return; }
    var err = W.validerBoutons(titres);
    if (err) { W.erreur(T(err)); return; }
    var max = titres.length ? MAX_CORPS_BOUTONS : MAX_TEXTE;
    if (texte.length > max) { W.erreur(T("whatsapp.saisie.texte_long", { max: max })); return; }
    var envoi = titres.length ? { type: "boutons", texte: texte, boutons: titres } : { type: "texte", texte: texte };
    var sel = S.sel, g = S.gen, zone = C.zTexte;
    await W.occuper(C, gardes(), async function () {
      var r = await W.api("POST", W.waUrl("/envoyer"), { identite: sel, envoi: envoi });
      if (W.perime(g) || sel !== S.sel || zone !== C.zTexte) return;
      if (!r.ok) { W.erreur(W.messageErreur(r)); return; }
      C.zTexte.value = "";
      C.titres.forEach(function (l) { l.noeud.remove(); });
      C.titres = [];
      W.info(T("whatsapp.saisie.envoye"));
      await relireFil(false);
    });
    apresAppel();
  }

  // ── l'envoi d'un modèle, en deux temps ──────────────────────────────────────────────────────────────────────────────
  async function ouvrirModele() {
    W.effacer();
    C.modele.textContent = "";
    if (!S.modeles) {
      var g = S.gen;
      var r = await W.api("GET", W.waUrl("/modeles"));
      if (W.perime(g)) return;
      if (!r.ok || !Array.isArray(r.data)) { W.erreur(W.messageErreur(r)); return; }
      // même règle que le serveur : un modèle dont un nom de paramètre dépasse NOM_PARAMETRE_MAX est écarté
      S.modeles = r.data.filter(function (m) {
        return (!m.statut || m.statut === "approved")
          && !(m.noms_parametres || []).some(function (n) { return String(n).length > W.NOM_PARAMETRE_MAX; });
      });
    }
    var boite = el("div", { cls: "wa-modele-boite", a: { "data-dz-wa-modele": "choix" } });
    boite.appendChild(el("b", { texte: T("whatsapp.modele.etape1") }));
    if (!S.modeles.length) {
      boite.appendChild(el("p", { cls: "wa-aide", texte: T("whatsapp.modele.aucun") }));
      boite.appendChild(W.bouton(T("whatsapp.modele.fermer"), { a: { "data-dz-wa-modele-fermer": true }, on: { click: fermerModele } }));
      C.modele.appendChild(boite);
      return;
    }
    var sel = W.champ({ tag: "select", label: T("whatsapp.modele.choisir"), a: { "data-dz-wa-modele-choix": true } });
    S.modeles.forEach(function (m) {
      sel.appendChild(el("option", { a: { value: m.nom + "|" + m.langue }, texte: T("whatsapp.modele.option", { nom: m.nom, langue: m.langue, categorie: categorie(m.categorie) }) }));
    });
    sel.value = S.modeles[0].nom + "|" + S.modeles[0].langue;
    boite.appendChild(W.etiquette(T("whatsapp.modele.choisir"), sel));
    boite.appendChild(el("div", { cls: "wa-ligne" }, [
      W.bouton(T("whatsapp.modele.fermer"), { a: { "data-dz-wa-modele-fermer": true }, on: { click: fermerModele } }),
      W.bouton(T("whatsapp.modele.suivant"), { cls: "wa-btn--primaire", a: { "data-dz-wa-modele-suivant": true }, on: { click: function () {
        var m = S.modeles.filter(function (x) { return x.nom + "|" + x.langue === sel.value; })[0];
        if (m) remplirModele(m);
      } } }, "dz-action-continuer")
    ]));
    C.modele.appendChild(boite);
  }
  function categorie(c) { return ["marketing", "utility", "authentication"].indexOf(c) >= 0 ? T("whatsapp.categorie." + c) : String(c || ""); }
  function fermerModele() { C.modele.textContent = ""; C.champsModele = []; C.btnModeleEnvoyer = null; }
  function remplirModele(m) {
    C.modele.textContent = "";
    var comp = m.composants || {};
    var boite = el("div", { cls: "wa-modele-boite", a: { "data-dz-wa-modele": "remplir" } });
    boite.appendChild(el("b", { texte: T("whatsapp.modele.etape2", { nom: m.nom, langue: m.langue }) }));
    var nommes = m.parametres === "nommes";
    var noms = Array.isArray(m.noms_parametres) && m.noms_parametres.length === m.n_parametres ? m.noms_parametres.map(String) : [];
    if (!noms.length) for (var i = 1; i <= (m.n_parametres || 0); i++) noms.push(String(i));
    var params = noms.map(function (n) {
      var c = W.champ({ label: T("whatsapp.modele.parametre", { nom: n }), a: { "data-dz-wa-param": n } });
      boite.appendChild(W.etiquette(T(nommes ? "whatsapp.modele.parametre_nomme" : "whatsapp.modele.parametre", { nom: n }), c));
      return [n, c];
    });
    if (!params.length) boite.appendChild(el("p", { cls: "wa-sous", texte: T("whatsapp.modele.sans_parametre") }));
    var entete = null;
    if (comp.entete === "text" && comp.entete_variable) {
      entete = ["text", W.champ({ label: T("whatsapp.modele.entete_texte"), a: { "data-dz-wa-entete": "text" } })];
      boite.appendChild(W.etiquette(T("whatsapp.modele.entete_texte"), entete[1]));
    } else if (["image", "video", "document"].indexOf(comp.entete) >= 0) {
      entete = [comp.entete, W.champ({ label: T("whatsapp.modele.entete_media", { type: typeLisible(comp.entete) }), a: { "data-dz-wa-entete": comp.entete } })];
      boite.appendChild(W.etiquette(T("whatsapp.modele.entete_media", { type: typeLisible(comp.entete) }), entete[1]));
      boite.appendChild(el("p", { cls: "wa-sous", texte: T("whatsapp.modele.entete_media_aide") }));
    }
    var payloads = (comp.boutons || []).filter(function (b) { return b.type === "quick_reply"; }).map(function (b) {
      var c = W.champ({ label: T("whatsapp.modele.payload", { n: b.index + 1 }), a: { "data-dz-wa-payload": String(b.index) } });
      boite.appendChild(W.etiquette(T("whatsapp.modele.payload", { n: b.index + 1 }), c));
      return [b.index, c];
    });
    if (payloads.length) boite.appendChild(el("p", { cls: "wa-sous", texte: T("whatsapp.modele.payload_aide") }));
    C.champsModele = params.map(function (x) { return x[1]; }).concat(entete ? [entete[1]] : [], payloads.map(function (x) { return x[1]; }));
    boite.appendChild(el("div", { cls: "wa-ligne" }, [
      W.bouton(T("whatsapp.modele.retour"), { a: { "data-dz-wa-modele-retour": true }, on: { click: ouvrirModele } }, "dz-action-retour"),
      C.btnModeleEnvoyer = W.bouton(T("whatsapp.modele.envoyer"), { cls: "wa-btn--primaire", a: { "data-dz-wa-modele-envoyer": true }, on: { click: function () { envoyerModele(m, nommes, params, entete, payloads); } } }, "dz-action-publier")
    ]));
    C.modele.appendChild(boite);
  }
  async function envoyerModele(m, nommes, params, entete, payloads) {
    if (C.occupe || !S.sel) return;
    W.effacer();
    var valeurs = nommes ? {} : [];
    for (var i = 0; i < params.length; i++) {
      var v = params[i][1].value;
      if (!String(v).trim()) { W.erreur(T("whatsapp.modele.parametre_vide")); return; }
      if (String(v).length > MAX_PARAMETRE) { W.erreur(T("whatsapp.modele.parametre_long", { max: MAX_PARAMETRE })); return; }
      if (nommes) valeurs[params[i][0]] = v; else valeurs.push(v);
    }
    var envoi = { type: "modele", nom: m.nom, langue: m.langue, parametres: valeurs };
    if (entete) {
      var ev = String(entete[1].value || "").trim();
      if (!ev) { W.erreur(T("whatsapp.modele.entete_vide")); return; }
      envoi.entete = entete[0] === "text" ? { type: "text", texte: ev } : { type: entete[0], media_id: ev };
    }
    var bt = payloads.map(function (p) { return { index: p[0], payload: String(p[1].value || "").trim() }; }).filter(function (b) { return b.payload; });
    if (bt.length) envoi.boutons = bt;
    var sel = S.sel, g = S.gen;
    await W.occuper(C, gardes(), async function () {
      var r = await W.api("POST", W.waUrl("/envoyer"), { identite: sel, envoi: envoi });
      if (W.perime(g) || sel !== S.sel) return;
      if (!r.ok) { W.erreur(W.messageErreur(r)); return; }
      fermerModele();
      W.info(T("whatsapp.modele.envoye"));
      await relireFil(false);
    });
    apresAppel();
  }

  W.onglets.conversations = { afficher: afficher, rafraichir: rafraichir };
})();
