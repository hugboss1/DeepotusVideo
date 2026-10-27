/* whatsapp.js — la PAGE WHATSAPP d'un espace, servie à /whatsapp/ (t311 tâche 7, 27/10/2026, plan
   docs/superpowers/plans/2026-10-27-t311-agent-whatsapp.md). Vanilla JS, aucun framework, aucune construction.
   Ce fichier : le socle (état, appels, en-tête, onglets, minuterie). Les onglets vivent dans onglets-conversations.js
   (Conversations) et onglets-gestion.js (Modèles, Contacts, Santé, Prix Meta) : ils s'inscrivent dans
   window.__dzWhatsapp.onglets[nom] = { afficher(panneau), rafraichir?() }.

   En-tête : espace (GET /api/espaces, l'actif d'abord), puis numéro (GET /api/comptes?espace=<id> : les comptes
   whatsapp RELIÉS, c.-à-d. avec un WHATSAPP_PHONE_ID). États vides : clé Kapso absente (plateformes.whatsapp.cle_plate
   .posee faux : seul l'état est lu, jamais le nom ni la valeur de la clé) -> Réglages ; aucun numéro relié -> l'assistant
   d'espace (Réglages › Espaces). Les deux ouvrent Réglages par « deepotus:navigate » sur la fenêtre parente (la page
   vit dans une iframe de la SPA).
   Appels : toute route /api/whatsapp/{cid}/… porte ?espace=<eid> (la route refuse un compte d'un autre espace).
   Erreurs : 409 {message, code} -> whatsapp.refus.<code> ; 402 : dz-plafonds.js enveloppe fetch et ouvre sa boîte ;
   annulé, il rend un 402 dont le détail est une chaîne (montrée telle quelle) ; sans dz-plafonds, le message du
   dz_plafond ; 502 -> le message du fournisseur (déjà nettoyé par le serveur).
   Minuterie : 30 s (setTimeout reprogrammé après la fin du tic, jamais deux tics à la fois), onglet Conversations
   seulement, arrêtée dès que document.visibilityState n'est plus « visible », reposée (avec une relecture immédiate) au
   retour. Réponses périmées : S.gen change à chaque choix d'espace ou de numéro ; toute fonction asynchrone le capture
   avant son await et ne touche ni S ni le DOM s'il a changé. Délai d'abandon des appels : 30 s (120 s pour rediger),
   rendu comme une panne réseau. Jamais de texte de message ni de clé dans la console.
   Textes : dzT("whatsapp.…") (frontend/shared/i18n/whatsapp.json). Données utilisateur par textContent. */
(function () {
  "use strict";
  if (window.__dzWhatsapp) return;

  function T(cle, vars) { return typeof window.dzT === "function" ? window.dzT(cle, vars) : cle; }
  function langue() { return typeof window.dzLang === "function" && window.dzLang() === "en" ? "en" : "fr"; }

  var REFUS = ["accord", "stop", "fenetre", "marketing", "plafond", "consentement", "prix", "bsuid_authentification", "occupee"];
  var IDENTITE = /^(?:tel:\d{5,20}|bsuid:\S{1,128})$/;
  var MAX_BOUTONS = 3, MAX_TITRE = 20;
  var ONGLETS = [["conversations", "dz-nav-boite-reception"], ["modeles", "dz-nav-templates"], ["contacts", "dz-media-persona"],
                 ["sante", "dz-etat-information"], ["prix", "dz-action-cout"]];
  var PERIODE_MS = 30000;

  var S = {};
  var Z = {};
  var W = window.__dzWhatsapp = { onglets: {}, S: S, T: T, langue: langue };

  // ── petits outils DOM ───────────────────────────────────────────────────────────────────────────────────────────────
  function el(tag, p, enfants) {
    var n = document.createElement(tag);
    p = p || {};
    if (p.cls) n.className = p.cls;
    if (p.texte != null) n.textContent = p.texte;
    if (p.a) Object.keys(p.a).forEach(function (k) { if (p.a[k] != null && p.a[k] !== false) n.setAttribute(k, p.a[k] === true ? "" : p.a[k]); });
    ["type", "value", "placeholder"].forEach(function (k) { if (p[k] != null) n[k] = p[k]; });
    if (p.disabled) n.disabled = true;
    if (p.on) Object.keys(p.on).forEach(function (k) { n.addEventListener(k, p.on[k]); });
    (enfants || []).forEach(function (e) { if (e) n.appendChild(e); });
    return n;
  }
  function icone(cle, taille) {
    var s = el("span", { cls: "wa-ico", a: { "aria-hidden": "true" } });
    if (typeof window.dzIcone === "function") s.innerHTML = window.dzIcone(cle, { taille: taille || 16 });
    return s;
  }
  function bouton(texte, p, cle) {
    p = p || {};
    var b = el("button", { cls: "wa-btn" + (p.cls ? " " + p.cls : ""), type: "button", a: p.a, on: p.on, disabled: p.disabled });
    if (cle) b.appendChild(icone(cle));
    if (texte) b.appendChild(el("span", { texte: texte }));
    if (!texte && p.titre) { b.setAttribute("aria-label", p.titre); }
    if (p.titre) b.setAttribute("title", p.titre);
    return b;
  }
  function champ(p) {
    var n = el(p.tag || "input", { cls: "wa-champ" + (p.cls ? " " + p.cls : ""), a: p.a, placeholder: p.placeholder, on: p.on });
    if (!p.tag || p.tag === "input") n.type = p.type || "text";
    if (p.value != null) n.value = p.value;
    if (p.label) n.setAttribute("aria-label", p.label);
    return n;
  }
  function etiquette(texte, ctrl) {
    return el("label", { cls: "wa-etiquette" }, [el("span", { texte: texte }), ctrl]);
  }

  // ── messages de la page ─────────────────────────────────────────────────────────────────────────────────────────────
  function effacer() { if (Z.erreur) { Z.erreur.textContent = ""; Z.erreur.hidden = true; } if (Z.info) { Z.info.textContent = ""; Z.info.hidden = true; } }
  function erreur(t) { if (Z.info) { Z.info.textContent = ""; Z.info.hidden = true; } if (Z.erreur) { Z.erreur.textContent = t; Z.erreur.hidden = !t; } }
  function info(t) { if (Z.info) { Z.info.textContent = t; Z.info.hidden = !t; } }

  function messageErreur(res) {
    var d = res && res.data ? res.data.detail : null;
    if (!res || res.status === 0) return T("whatsapp.erreur.reseau");
    if (d && typeof d === "object" && !Array.isArray(d) && d.dz_plafond) {
      return T("whatsapp.erreur.plafond", { detail: String(d.dz_plafond.message || "") });
    }
    if (d && typeof d === "object" && !Array.isArray(d) && REFUS.indexOf(d.code) >= 0) return T("whatsapp.refus." + d.code);
    var msg = d && typeof d === "object" && !Array.isArray(d) ? String(d.message || "") : (typeof d === "string" ? d : "");
    if (res.status === 502) return T("whatsapp.erreur.fournisseur", { detail: msg });
    if (msg) return T("whatsapp.erreur.serveur", { detail: msg });
    return T("whatsapp.erreur.generique", { code: res.status });
  }

  // ── appels ──────────────────────────────────────────────────────────────────────────────────────────────────────────
  function waUrl(suffixe) { return "/api/whatsapp/" + encodeURIComponent(S.cid || "") + suffixe; }
  function avecEspace(url) {
    if (url.indexOf("/api/whatsapp/") !== 0) return url;
    return url + (url.indexOf("?") < 0 ? "?" : "&") + "espace=" + encodeURIComponent(S.eid || "");
  }
  function mediaUrl(mid) { return avecEspace(waUrl("/medias/" + encodeURIComponent(mid))); }
  // délai d'abandon : un appel qui ne répond pas rend status 0 (message « réseau ») au lieu de bloquer la page
  async function api(methode, url, corps, delai) {
    var o = { method: methode, headers: { "Accept": "application/json", "Accept-Language": langue() } };
    if (corps !== undefined) { o.headers["Content-Type"] = "application/json"; o.body = JSON.stringify(corps); }
    var ctl = typeof AbortController === "function" ? new AbortController() : null;
    var minu = null;
    if (ctl) { o.signal = ctl.signal; minu = setTimeout(function () { ctl.abort(); }, delai || W.DELAI_MS); }
    try {
      var R = await window.fetch(avecEspace(url), o);
      var d = null;
      try { d = await R.json(); } catch (e) { d = null; }
      if (ctl && ctl.signal.aborted) return { ok: false, status: 0, data: null };
      return { ok: !!R.ok, status: R.status, data: d };
    } catch (e) {
      return { ok: false, status: 0, data: null };
    } finally {
      if (minu) clearTimeout(minu);
    }
  }
  // un appel à la fois par garde ; les éléments sont grisés pendant l'appel, puis rendus à leur état d'avant
  async function occuper(garde, elts, fn) {
    if (garde.occupe) return undefined;
    garde.occupe = true;
    var avant = (elts || []).filter(Boolean).map(function (e) { return [e, !!e.disabled]; });
    avant.forEach(function (p) { p[0].disabled = true; });
    try { return await fn(); } finally {
      garde.occupe = false;
      avant.forEach(function (p) { p[0].disabled = p[1]; });
    }
  }
  async function confirmer(msg) {
    var D = window.__dzDialogue;
    if (D && typeof D.confirmer === "function") { try { return !!(await D.confirmer(msg)); } catch (e) { return false; } }
    return typeof window.confirm === "function" ? !!window.confirm(msg) : true;
  }

  // ── identités, brouillons, boutons (purs) ───────────────────────────────────────────────────────────────────────────
  function normaliserIdentite(v) {
    var s = String(v || "").trim();
    if (/^bsuid:/i.test(s)) return "bsuid:" + s.slice(6).trim();
    var chiffres = s.replace(/^tel:/i, "").replace(/\D/g, "");
    return chiffres ? "tel:" + chiffres : "";
  }
  function identiteValide(v) { return IDENTITE.test(v); }
  function groupe(identite) {
    var a = S.etat && S.etat.alias ? S.etat.alias : {};
    var g = [identite];
    if (a[identite] && g.indexOf(a[identite]) < 0) g.push(a[identite]);
    Object.keys(a).forEach(function (k) { if (a[k] === identite && g.indexOf(k) < 0) g.push(k); });
    return g;
  }
  // une entrée sans etat (ou décidée) n'est PAS un brouillon : seuls « attente » et « humain » attendent une décision
  function brouillonDe(identite) {
    var B = S.brouillons || {};
    var g = groupe(identite);
    for (var i = 0; i < g.length; i++) {
      var b = B[g[i]];
      if (b && typeof b === "object" && (b.etat === "attente" || b.etat === "humain")) return b;
    }
    return null;
  }
  function validerBoutons(titres) {
    if (titres.length > MAX_BOUTONS) return "whatsapp.saisie.trop_de_boutons";
    for (var i = 0; i < titres.length; i++) if (String(titres[i]).length > MAX_TITRE) return "whatsapp.saisie.titre_long";
    var vus = {};
    for (var j = 0; j < titres.length; j++) { if (vus[titres[j]]) return "whatsapp.saisie.titres_doubles"; vus[titres[j]] = 1; }
    return null;
  }
  function locale() { return langue() === "en" ? "en-GB" : "fr-FR"; }
  function heure(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "";
    var h = d.toLocaleTimeString(locale(), { hour: "2-digit", minute: "2-digit" });
    return d.toDateString() === new Date().toDateString() ? h : d.toLocaleDateString(locale(), { day: "2-digit", month: "2-digit" }) + " " + h;
  }
  function date(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    return isNaN(d.getTime()) ? "" : d.toLocaleDateString(locale(), { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  // ── navigation vers la SPA ──────────────────────────────────────────────────────────────────────────────────────────
  function aller(vue) {
    var cible = window;
    try { if (window.parent && window.parent !== window && typeof window.parent.dispatchEvent === "function") cible = window.parent; } catch (e) { cible = window; }
    var C = cible.CustomEvent || CustomEvent;
    cible.dispatchEvent(new C("deepotus:navigate", { detail: { view: vue } }));
    if (cible === window && window.top === window && window.location) window.location.href = "/";
  }

  // ── minuterie ───────────────────────────────────────────────────────────────────────────────────────────────────────
  // un setTimeout reprogrammé APRÈS la fin du tic (jamais deux tics en parallèle, même si une lecture est lente)
  function arreterMinuterie() { if (S.minuterie) { clearTimeout(S.minuterie); S.minuterie = null; } }
  function demarrerMinuterie() {
    arreterMinuterie();
    if (document.visibilityState !== "visible" || S.onglet !== "conversations" || !S.cid) return;
    S.minuterie = setTimeout(tour, PERIODE_MS);
  }
  async function tour() {
    S.minuterie = null;
    if (S.ticEnCours) return;
    await tic();
    demarrerMinuterie();
  }
  async function tic() {
    if (document.visibilityState !== "visible" || S.onglet !== "conversations" || !S.cid || S.ticEnCours) return;
    var o = W.onglets.conversations;
    if (!o || typeof o.rafraichir !== "function") return;
    S.ticEnCours = true;
    try { await o.rafraichir(); } finally { S.ticEnCours = false; }
  }
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible") {
      if (S.cid && S.onglet === "conversations") { tic(); demarrerMinuterie(); }
    } else arreterMinuterie();
  });

  // ── en-tête : espace, numéro, états vides ───────────────────────────────────────────────────────────────────────────
  function libelleCompte(c) {
    var num = (c.champs || []).filter(function (x) { return x.nom === "WHATSAPP_NUMERO"; })[0];
    return (num && num.valeur) ? String(num.valeur) : String(c.libelle || c.id);
  }
  function relie(c) {
    return c.plateforme === "whatsapp" && (c.champs || []).some(function (x) { return x.nom === "WHATSAPP_PHONE_ID" && x.valeur; });
  }
  function montrerVide(genre) {
    arreterMinuterie();
    Z.vide.textContent = "";
    Z.vide.hidden = !genre;
    Z.corps.hidden = !!genre;
    if (!genre) return;
    var boite = el("div", { cls: "wa-vide", a: { "data-dz-wa-vide": genre } });
    boite.appendChild(icone(genre === "cle" ? "dz-nav-cles-api" : "dz-nav-boite-reception", 32));
    boite.appendChild(el("h2", { texte: T("whatsapp.vide." + genre + "_titre") }));
    boite.appendChild(el("p", { texte: T("whatsapp.vide." + genre + "_texte") }));
    if (genre === "cle") boite.appendChild(bouton(T("whatsapp.vide.ouvrir_reglages"), { cls: "wa-btn--primaire", a: { "data-dz-wa-aller": "reglages" }, on: { click: function () { aller("settings"); } } }, "dz-nav-reglages"));
    if (genre === "numero") boite.appendChild(bouton(T("whatsapp.vide.ouvrir_assistant"), { cls: "wa-btn--primaire", a: { "data-dz-wa-aller": "assistant" }, on: { click: function () { aller("settings"); } } }, "dz-nav-espace-travail"));
    Z.vide.appendChild(boite);
  }
  function remplir(sel, items, valeur) {
    sel.textContent = "";
    items.forEach(function (it) { sel.appendChild(el("option", { texte: it[1], a: { value: it[0] } })); });
    sel.value = valeur || "";
    sel.disabled = items.length < 2;
  }

  // S.gen : changé à chaque choix d'espace ou de numéro ; une réponse arrivée après un autre choix est jetée
  function perime(g) { return g !== S.gen; }
  async function chargerEspaces() {
    var g = S.gen;
    var r = await api("GET", "/api/espaces");
    if (perime(g)) return;
    if (!r.ok || !r.data) { erreur(messageErreur(r)); montrerVide("espace"); return; }
    S.espaces = (r.data.espaces || []).filter(function (e) { return !e.archive; });
    var ids = S.espaces.map(function (e) { return e.id; });
    var eid = ids.indexOf(r.data.actif) >= 0 ? r.data.actif : ids[0];
    remplir(Z.selEspace, S.espaces.map(function (e) { return [e.id, e.nom]; }), eid);
    if (!eid) { montrerVide("espace"); return; }
    await choisirEspace(eid);
  }
  async function choisirEspace(eid) {
    arreterMinuterie();
    var g = ++S.gen;
    S.eid = eid; S.cid = null; S.etat = null; S.sel = null;
    effacer();
    var r = await api("GET", "/api/comptes?espace=" + encodeURIComponent(eid));
    if (perime(g)) return;
    if (!r.ok || !r.data) { erreur(messageErreur(r)); remplir(Z.selNumero, [], ""); montrerVide("numero"); return; }
    var cp = r.data.plateformes && r.data.plateformes.whatsapp && r.data.plateformes.whatsapp.cle_plate;
    S.clePosee = !!(cp && cp.posee);
    S.comptes = (r.data.comptes || []).filter(relie);
    remplir(Z.selNumero, S.comptes.map(function (c) { return [c.id, libelleCompte(c)]; }), S.comptes[0] ? S.comptes[0].id : "");
    if (!S.clePosee) { montrerVide("cle"); return; }
    if (!S.comptes.length) { montrerVide("numero"); return; }
    await choisirNumero(S.comptes[0].id);
  }
  async function choisirNumero(cid) {
    arreterMinuterie();
    var g = ++S.gen;
    S.cid = cid; S.sel = null; S.convs = []; S.brouillons = {}; S.etat = null; S.modeles = null; S.modelesTous = null;
    effacer();
    montrerVide(null);
    await chargerEtat();
    if (perime(g)) return;
    Object.keys(Z.panneaux).forEach(function (k) { Z.panneaux[k].textContent = ""; Z.panneaux[k].removeAttribute("data-dz-wa-pret"); });
    await activerOnglet(S.onglet || "conversations");
  }
  async function chargerEtat() {
    var g = S.gen;
    var r = await api("GET", waUrl("/etat"));
    if (perime(g)) return { ok: false, status: -1, data: null, perime: true };
    if (r.ok && r.data) S.etat = r.data;
    return r;
  }
  async function activerOnglet(nom) {
    S.onglet = nom;
    effacer();
    Object.keys(Z.onglets).forEach(function (k) {
      Z.onglets[k].setAttribute("aria-selected", k === nom ? "true" : "false");
      Z.onglets[k].classList.toggle("actif", k === nom);
      Z.panneaux[k].hidden = k !== nom;
    });
    arreterMinuterie();
    var o = W.onglets[nom];
    var g = S.gen;
    if (o && S.cid) await o.afficher(Z.panneaux[nom]);
    if (!perime(g) && S.onglet === nom && nom === "conversations") demarrerMinuterie();
  }

  // ── démarrage ───────────────────────────────────────────────────────────────────────────────────────────────────────
  async function demarrer(racine) {
    arreterMinuterie();
    var g = (S.gen || 0) + 1;
    Object.keys(S).forEach(function (k) { delete S[k]; });
    S.gen = g;
    S.onglet = "conversations";
    racine.textContent = "";
    Z.racine = racine;
    Z.selEspace = champ({ tag: "select", label: T("whatsapp.entete.espace"), a: { "data-dz-wa-espace": true },
                          on: { change: function () { choisirEspace(Z.selEspace.value); } } });
    Z.selNumero = champ({ tag: "select", label: T("whatsapp.entete.numero"), a: { "data-dz-wa-numero": true },
                          on: { change: function () { choisirNumero(Z.selNumero.value); } } });
    var tete = el("header", { cls: "wa-tete" }, [
      el("div", { cls: "wa-marque" }, [icone("dz-nav-boite-reception", 20), el("b", { texte: T("whatsapp.page.titre") }),
                                       el("span", { cls: "wa-sous", texte: T("whatsapp.page.sous_titre") })]),
      etiquette(T("whatsapp.entete.espace"), Z.selEspace),
      etiquette(T("whatsapp.entete.numero"), Z.selNumero),
      bouton("", { titre: T("whatsapp.entete.actualiser"), a: { "data-dz-wa-actualiser": true },
                   on: { click: function () { if (S.cid) activerOnglet(S.onglet); } } }, "dz-action-actualiser")
    ]);
    Z.erreur = el("div", { cls: "wa-erreur", a: { role: "alert", "data-dz-wa-erreur": true } });
    Z.info = el("div", { cls: "wa-info", a: { role: "status", "aria-live": "polite", "data-dz-wa-info": true } });
    Z.erreur.hidden = true; Z.info.hidden = true;
    Z.vide = el("section", { cls: "wa-vides" });
    Z.vide.hidden = true;
    Z.onglets = {}; Z.panneaux = {};
    var nav = el("nav", { cls: "wa-onglets", a: { role: "tablist", "aria-label": T("whatsapp.onglets.aria") } });
    var panneaux = el("div", { cls: "wa-panneaux" });
    ONGLETS.forEach(function (o) {
      var b = el("button", { cls: "wa-onglet", type: "button", a: { role: "tab", "aria-selected": "false", "data-dz-wa-onglet": o[0] },
                             on: { click: function () { if (S.cid) activerOnglet(o[0]); } } }, [icone(o[1]), el("span", { texte: T("whatsapp.onglet." + o[0]) })]);
      var p = el("section", { cls: "wa-panneau wa-panneau--" + o[0], a: { role: "tabpanel", "data-dz-wa-panneau": o[0] } });
      p.hidden = true;
      Z.onglets[o[0]] = b; Z.panneaux[o[0]] = p;
      nav.appendChild(b); panneaux.appendChild(p);
    });
    Z.corps = el("div", { cls: "wa-corps" }, [nav, panneaux]);
    Z.corps.hidden = true;
    racine.appendChild(tete);
    racine.appendChild(el("div", { cls: "wa-messages" }, [Z.erreur, Z.info]));
    racine.appendChild(Z.vide);
    racine.appendChild(Z.corps);
    await chargerEspaces();
  }

  Object.assign(W, {
    el: el, icone: icone, bouton: bouton, champ: champ, etiquette: etiquette, api: api, waUrl: waUrl, mediaUrl: mediaUrl,
    messageErreur: messageErreur, erreur: erreur, info: info, effacer: effacer, confirmer: confirmer,
    normaliserIdentite: normaliserIdentite, identiteValide: identiteValide, groupe: groupe, brouillonDe: brouillonDe,
    validerBoutons: validerBoutons, heure: heure, date: date, chargerEtat: chargerEtat, demarrer: demarrer,
    occuper: occuper, perime: perime, DELAI_MS: 30000, DELAI_REDIGER_MS: 120000, NOM_PARAMETRE_MAX: 60,
    MAX_BOUTONS: MAX_BOUTONS, MAX_TITRE: MAX_TITRE
  });

  function auto() {
    var r = document.querySelector("[data-dz-wa-page]");
    if (r) demarrer(r);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", auto);
  else setTimeout(auto, 0);
})();
