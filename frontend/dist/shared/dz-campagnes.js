/* dz-campagnes.js — le composant PARTAGÉ de conversation de l'agent Campagnes (t285, T8, 24/10/2026, spec
   docs/superpowers/specs/2026-10-23-agent-interne-design.md §6). SOURCE : frontend/shared/dz-campagnes.js ; copie OCTET
   POUR OCTET : frontend/dist/shared/dz-campagnes.js, chargée par frontend/dist/index.html : balise classique placée
   après dz-agent.js dans la page ; script classique, il s'exécute donc AVANT le module (différé) de la SPA, et
   window.DzCampagnes existe quand les écrans montent. Le banc backend/tests/test_campagnes_shared.py refuse toute dérive, le banc node
   frontend/shared/qa/campagnes.test.mjs joue le composant sur un DOM simulé.

   window.DzCampagnes.monter(el, { cid?, role, espace_id?, brief?, contexte: "planificateur" | "f1", surCid? })
     -> { demonter(), cid(), recharger() }

   Le contrat du serveur (backend/app/api/agent_campagnes_routes.py) :
   - sans `cid`, la conversation naît au premier besoin (POST /api/agent/campagnes/ {role, espace_id?}) ;
   - le DEVIS d'abord : POST /{cid}/devis {texte} -> « ≤ X $ » sous le champ ; l'envoi (POST /{cid}/message {texte,
     plafond_usd}) VAUT ACCORD, donc un clic sans devis affiché ne fait que l'afficher ;
   - la réponse est un flux SSE (fetch + ReadableStream) ; à la fin, la conversation est relue (GET /{cid}) ;
   - 503 sans clé Anthropic : un message clair, le champ et le bouton ne sont JAMAIS grisés pour ça ; 402 `dz_plafond` :
     c'est dz-plafonds.js (il enveloppe window.fetch, lu ICI à chaque appel) qui montre son dialogue et rejoue ;
     409 : conversation occupée ;
   - les CARTES (POST /{cid}/carte/{n}, n = rang parmi les cartes des messages `agent`) : porte (Valider / Modifier),
     devis (le bouton appelle LA route de génération de la carte, puis /carte avec job_id ou fichier), continuer
     (nouveau message au devis de la carte), espace (liste), brouillons (lien vers le calendrier du Planificateur) ;
   - AUCUN bouton publier : la porte 2 reste le Planificateur ; l'espace de la campagne est écrit en clair et ne se
     modifie pas ici ; le coût cumulé de la conversation est affiché.
   Les libellés viennent de dzT (zone.objet.role) ; le `libelle` français du serveur ne sert que de secours pour
   un genre de carte inconnu. Vanilla DOM, aucune dépendance au runtime React. */
(function () {
  "use strict";
  if (window.DzCampagnes) return;

  var BASE = "/api/agent/campagnes";
  var DELAI_DEVIS_MS = 450;     // pause de saisie avant de demander le plafond
  var SONDE_MS = 8000;          // relecture tant qu'un rendu vidéo n'est pas fini
  // la route de génération de chaque genre de devis : la carte ne peut en désigner aucune autre
  var ROUTES = { video: "/api/generate", image: "/api/images/generate", voix: "/api/audio/voiceover" };
  var JSON_H = { "Content-Type": "application/json" };

  function T(cle, vars) { return typeof window.dzT === "function" ? window.dzT(cle, vars) : cle; }
  function langue() {
    var l = typeof window.dzLang === "function" ? window.dzLang() : window.dzLang;
    return l === "en" ? "en" : "fr";
  }

  // le montant, sans l'unité (elle est dans la phrase traduite). Un plafond s'arrondit vers le HAUT au centime.
  function usd(v, plafond) {
    v = Number(v) || 0;
    var t;
    if (plafond) t = (Math.ceil(v * 100 - 1e-9) / 100).toFixed(2);
    else if (v !== 0 && Math.abs(v) < 0.1) {
      t = v.toFixed(4).replace(/0+$/, "");
      if (t.split(".")[1].length < 2) t += "0";
    } else t = v.toFixed(2);
    return langue() === "en" ? t : t.replace(".", ",");
  }

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

  var CSS = ""
    + ".dzCamp{display:flex;flex-direction:column;flex:1 1 auto;min-height:0;height:100%;background:var(--bg-panel,#151519);color:var(--ink,#c4bfb6);"
    + "font-family:var(--f-ui,system-ui,sans-serif);font-size:13px;line-height:1.5}"
    + ".dzCampTete{display:flex;flex-wrap:wrap;gap:4px 16px;justify-content:space-between;padding:8px 12px;border-bottom:1px solid var(--stroke,#2a2930);"
    + "font-family:var(--f-mono,monospace);font-size:11px;color:var(--ink-soft,#8a857d)}"
    + ".dzCampTete strong{color:var(--ink-strong,#f2efe9);font-weight:600}"
    + ".dzCampFil{flex:1;min-height:0;overflow:auto;padding:12px;display:flex;flex-direction:column;gap:10px}"
    + ".dzCampVide{color:var(--ink-soft,#8a857d)}"
    + ".dzCampMsg{display:flex;flex-direction:column;gap:6px;max-width:100%}"
    + ".dzCampMsg[data-role=utilisateur]{align-self:flex-end;background:var(--accent-soft,rgba(240,180,41,.14));border-radius:var(--r,10px);padding:8px 10px}"
    + ".dzCampTexte{white-space:pre-wrap}"
    + ".dzCampOutil{font-family:var(--f-mono,monospace);font-size:11px;color:var(--ink-soft,#8a857d)}"
    + ".dzCampOutil[data-ok=non]{color:var(--red,#e35d4a)}"
    + ".dzCampCarte{border:1px solid var(--stroke-strong,#3d3b45);border-radius:var(--r,10px);background:var(--bg-panel-2,#1c1c21);padding:10px;display:flex;flex-direction:column;gap:8px}"
    + ".dzCampCarte[data-etat=proposee]{border-color:var(--accent,#f0b429)}"
    + ".dzCampCarteT{color:var(--ink-strong,#f2efe9);font-weight:600}"
    + ".dzCampResume{white-space:pre-wrap}"
    + ".dzCampLignes{margin:0;padding-left:18px;font-family:var(--f-mono,monospace);font-size:11px;color:var(--ink-soft,#8a857d)}"
    + ".dzCampEtat{font-family:var(--f-mono,monospace);font-size:11px;color:var(--ink-soft,#8a857d)}"
    + ".dzCampEtat[data-ton=ok]{color:var(--green,#5ec8a0)}.dzCampEtat[data-ton=ko]{color:var(--red,#e35d4a)}"
    + ".dzCampActions{display:flex;flex-wrap:wrap;gap:6px}"
    + ".dzCamp button,.dzCamp a.dzCampLien{background:transparent;color:inherit;border:1px solid var(--stroke-strong,#3d3b45);border-radius:var(--r-sm,6px);"
    + "padding:5px 10px;font:inherit;cursor:pointer;text-decoration:none}"
    + ".dzCamp button:hover,.dzCamp a.dzCampLien:hover{border-color:var(--accent,#f0b429)}"
    + ".dzCamp button[data-primaire=\"1\"]{background:var(--accent,#f0b429);color:var(--accent-ink,#1a1206);border-color:var(--accent,#f0b429);font-weight:600}"
    + ".dzCamp button[aria-busy=true]{opacity:.6;cursor:progress}"
    + ".dzCamp :focus-visible{outline:2px solid var(--accent,#f0b429);outline-offset:1px}"
    + ".dzCampStatut{padding:0 12px;color:var(--red,#e35d4a)}"
    + ".dzCampStatut:empty{display:none}"
    + ".dzCampPied{display:flex;flex-direction:column;gap:6px;padding:10px 12px;border-top:1px solid var(--stroke,#2a2930)}"
    + ".dzCampDevis{font-family:var(--f-mono,monospace);font-size:11px;color:var(--amber,#f0b429);min-height:16px}"
    + ".dzCampSaisie{display:flex;gap:6px}"
    + ".dzCampSaisie textarea{flex:1;resize:none;min-height:38px;background:var(--bg-panel-2,#1c1c21);color:inherit;border:1px solid var(--stroke,#2a2930);"
    + "border-radius:var(--r-sm,6px);padding:6px;font:inherit}"
    + "@media (prefers-reduced-motion:reduce){.dzCamp *{transition:none!important;animation:none!important}}";
  var styleInjecte = false;
  function injecterStyle() {
    if (styleInjecte) return;
    styleInjecte = true;
    var s = el("style", { "data-dz-campagnes-style": "1" });
    s.textContent = CSS;
    (document.head || document.documentElement).appendChild(s);
  }

  // ---- le flux SSE : des lignes `data: {json}` séparées par une ligne vide --------------------------------------------
  function extraire(tampon, surEvt) {
    var morceaux = tampon.replace(/\r\n/g, "\n").split("\n\n");
    var reste = morceaux.pop();
    morceaux.forEach(function (m) {
      m.split("\n").forEach(function (ligne) {
        if (ligne.indexOf("data:") !== 0) return;
        var j = ligne.slice(5).trim();
        if (!j) return;
        var e = null;
        try { e = JSON.parse(j); } catch (x) { e = null; }   // une ligne illisible est ignorée
        if (e && typeof e === "object") surEvt(e);
      });
    });
    return reste;
  }

  async function lireFlux(res, surEvt) {
    var corps = res.body;
    if (corps && typeof corps.getReader === "function") {
      var lecteur = corps.getReader();
      var dec = new TextDecoder("utf-8");
      var tampon = "";
      for (;;) {
        var r = await lecteur.read();
        if (r.done) break;
        tampon = extraire(tampon + dec.decode(r.value, { stream: true }), surEvt);
      }
      extraire(tampon + dec.decode() + "\n\n", surEvt);
    } else {
      extraire((await res.text()) + "\n\n", surEvt);
    }
  }

  // le texte d'un refus HTTP : `detail` (chaîne, ou objet portant un message) sinon le code
  async function detailDe(res) {
    var j = null;
    try { j = await res.json(); } catch (e) { j = null; }
    var d = j && j.detail;
    if (typeof d === "string" && d) return d;
    if (d && typeof d === "object") {
      var m = d.message || (d.dz_plafond && d.dz_plafond.message);
      if (typeof m === "string" && m) return m;
    }
    return T("campagnes.erreur.http", { code: res.status });
  }

  function nomImage(j) {
    var i = j && j.images && j.images[0];
    if (i && typeof i === "object") i = i.filename || i.name;
    return typeof i === "string" && i ? i : "";
  }

  // ---- l'analyse d'une conversation : les cartes et leur dernier état ----------------------------------------------
  function analyser(conv) {
    var cartes = [], etats = {};
    ((conv && conv.messages) || []).forEach(function (m) {
      (m.blocs || []).forEach(function (b) {
        if (!b || typeof b !== "object" || b.type !== "carte") return;
        if (m.role === "agent") cartes.push(b);
        else if (m.role === "fait") {
          var n = b.arguments && b.arguments.carte;
          if (typeof n === "number") etats[n] = b;
        }
      });
    });
    var porte = -1;
    cartes.forEach(function (b, i) { if (b.genre === "porte") porte = i; });
    return { cartes: cartes, etats: etats, dernierePorte: porte };
  }

  // t285 T9 (relecture) : la ligne d'un outil = son libellé traduit (campagnes.outil.<nom>) + son état ; le résumé du
  // serveur (en français) n'est plus affiché. Un nom inconnu : un libellé générique.
  var OUTILS = ["chercher_app", "lire_espace", "lire_bibliotheque", "lire_planificateur", "lire_document", "ecrire_dossier",
    "proposer_porte", "deviser_generation", "creer_brouillons", "pointer"];
  function ligneOutil(nom, ok) {
    var lib = OUTILS.indexOf(String(nom)) >= 0 ? T("campagnes.outil." + nom) : T("campagnes.outil.inconnu");
    if (ok === true) return T("campagnes.fil.outil_ok", { outil: lib });
    if (ok === false) return T("campagnes.fil.outil_echec", { outil: lib });
    return lib;
  }
  function noeudOutil(nom, ok) {
    var a = { class: "dzCampOutil", texte: ligneOutil(nom, ok) };
    if (ok === true || ok === false) a["data-ok"] = ok ? "oui" : "non";
    return el("div", a);
  }

  function montantContinuer(b) {
    var d = b.arguments && b.arguments.devis;
    if (d && typeof d.plafond_usd === "number") return d.plafond_usd;
    return Number(b.devis) || 0;
  }

  function libelle(b) {
    var a = b.arguments || {};
    switch (b.genre) {
      case "porte": return T("campagnes.carte.porte", { n: a.numero || 1 });
      case "devis": return T("campagnes.carte.devis", {
        genre: ROUTES[a.genre] ? T("campagnes.genre." + a.genre) : String(a.genre || ""),
        usd: usd(a.usd != null ? a.usd : b.devis) });
      case "espace": return T("campagnes.carte.espace");
      case "continuer": return T("campagnes.carte.continuer", { usd: usd(montantContinuer(b), true) });
      case "brouillons": return T("campagnes.carte.brouillons", { n: (a.ids || []).length });
      default: return String(b.libelle || "");   // secours : un genre que cet écran ne connaît pas
    }
  }

  // ---- le composant -----------------------------------------------------------------------------------------------------
  function monter(hote, opts) {
    opts = opts || {};
    var S = {
      cid: opts.cid || null, conv: null, noms: {}, devis: null, calcul: false, occupe: false, live: [], erreur: "",
      transitoire: null, occ: {}, rendus: {}, stop: (typeof AbortController === "function" ? new AbortController() : null), correction: null, sonde: null, minuteur: null, seq: 0, creation: null, ferme: false,
      indice: ""
    };
    injecterStyle();

    var tete = el("div", { class: "dzCampTete", "data-dz-camp": "tete" });
    var fil = el("div", { class: "dzCampFil", "data-dz-camp": "fil", role: "log" });
    var statut = el("div", { class: "dzCampStatut", "data-dz-camp": "statut", role: "status" });
    var devisLigne = el("div", { class: "dzCampDevis", "data-dz-camp": "devis", role: "status" });
    var champ = el("textarea", { rows: "2", "data-dz-camp": "champ" });
    var envoyer = el("button", { type: "button", "data-dz-camp": "envoyer", "data-primaire": "1" });
    var racine = el("div", { class: "dzCamp", "data-dz-campagnes": "1", "data-contexte": opts.contexte || "planificateur" }, [
      tete, fil, statut,
      el("div", { class: "dzCampPied" }, [devisLigne, el("div", { class: "dzCampSaisie" }, [champ, envoyer])])
    ]);

    var saisie = function () { return String(champ.value || "").trim(); };
    var appel = function (methode, chemin, corps) {
      var init = { method: methode, headers: JSON_H };
      if (S.stop) init.signal = S.stop.signal;
      if (corps !== undefined) init.body = JSON.stringify(corps);
      return window.fetch(BASE + chemin, init);    // window.fetch lu ICI : dz-plafonds.js l'enveloppe (le 402)
    };

    // -- dessin ------------------------------------------------------------------------------------------------------
    function nomEspace(id) { return id ? (S.noms[id] || String(id)) : ""; }

    function dessinerTete() {
      vider(tete);
      var id = (S.conv && S.conv.espace_id) || (!S.conv && opts.espace_id) || null;
      var espace = id ? nomEspace(id) : T("campagnes.entete.aucun_espace");
      tete.appendChild(el("span", { "data-dz-camp": "espace" }, [
        el("span", { texte: T("campagnes.entete.espace", { nom: espace }) })]));
      tete.appendChild(el("span", { "data-dz-camp": "cout", texte: T("campagnes.entete.cout", { usd: usd(S.conv ? S.conv.cout_usd : 0) }) }));
    }

    function etat(texte, ton, marqueur) {
      var a = { class: "dzCampEtat", "data-ton": ton || "", texte: texte };
      if (marqueur) a["data-dz-camp"] = marqueur;
      return el("div", a);
    }

    function bouton(texte, surClic, primaire, occupe) {
      var b = el("button", { type: "button", texte: texte });
      if (primaire) b.setAttribute("data-primaire", "1");
      if (occupe) b.setAttribute("aria-busy", "true");
      b.addEventListener("click", surClic);
      return b;
    }

    function carteNode(b, n, info) {
      var dernier = n !== null ? (info.etats[n] || b) : b;
      var e = dernier.etat || "proposee";
      var a = b.arguments || {};
      var occupe = n !== null && !!S.occ[n];
      var c = el("div", { class: "dzCampCarte", "data-genre": String(b.genre), "data-etat": e });
      c.appendChild(el("div", { class: "dzCampCarteT", texte: libelle(b) }));
      var actions = el("div", { class: "dzCampActions" });
      var propose = e === "proposee";

      if (b.genre === "porte") {
        if (a.resume) c.appendChild(el("div", { class: "dzCampResume", texte: String(a.resume) }));
        var cal = Array.isArray(a.calendrier) ? a.calendrier : [];
        if (cal.length) {
          var ul = el("ul", { class: "dzCampLignes" });
          cal.forEach(function (l) {
            var t = l && typeof l === "object" ? [l.quand, l.canal, l.sujet].filter(Boolean).join(" · ") : String(l);
            ul.appendChild(el("li", { texte: t }));
          });
          c.appendChild(ul);
        }
        if (propose && n === info.dernierePorte) {
          actions.appendChild(bouton(T("campagnes.action.valider"), function () { decider(n, "acceptee"); }, true, occupe));
          actions.appendChild(bouton(T("campagnes.action.modifier"), function () {
            decider(n, "refusee").then(function () { S.correction = n; dessinerPied(); try { champ.focus(); } catch (x) { /* rien */ } });
          }, false, occupe));
        } else if (e === "acceptee" || e === "terminee") c.appendChild(etat(T("campagnes.etat.validee"), "ok"));
        else if (e === "refusee") c.appendChild(etat(T("campagnes.etat.corriger")));
      } else if (b.genre === "devis") {
        if (propose) {
          actions.appendChild(bouton(S.rendus[n] ? T("campagnes.action.enregistrer") : T("campagnes.action.generer", { usd: usd(a.usd != null ? a.usd : b.devis) }),
            function () { genererDevis(n, b); }, true, occupe));
          actions.appendChild(bouton(T("campagnes.action.refuser"), function () { decider(n, "refusee"); }, false, occupe));
        } else if (e === "refusee") c.appendChild(etat(T("campagnes.etat.refusee")));
        else {
          var da = dernier.arguments || {};
          var echec = String(da.statut || "").toLowerCase() === "failed";
          if (e === "terminee") c.appendChild(etat(T(echec ? "campagnes.etat.echec" : "campagnes.etat.terminee"), echec ? "ko" : "ok"));
          else c.appendChild(etat(T("campagnes.etat.lancee")));
          if (da.fichier) c.appendChild(etat(T("campagnes.etat.fichier", { fichier: da.fichier })));
          if (e === "terminee") actions.appendChild(bouton(T("campagnes.action.reprendre"), reprendre, false, false));
        }
      } else if (b.genre === "espace") {
        if (propose && !(S.conv && S.conv.espace_id)) {
          (a.espaces || []).forEach(function (x) {
            if (x && x.id) actions.appendChild(bouton(String(x.nom || x.id), function () { decider(n, "acceptee", { espace_id: x.id }); }, false, occupe));
          });
        } else if (e === "acceptee") {
          c.appendChild(etat(T("campagnes.etat.espace_choisi", { nom: nomEspace((dernier.arguments || {}).espace_id || (S.conv && S.conv.espace_id)) }), "ok"));
        } else if (e === "refusee") c.appendChild(etat(T("campagnes.etat.refusee")));
      } else if (b.genre === "continuer") {
        if (propose) actions.appendChild(bouton(T("campagnes.action.continuer", { usd: usd(montantContinuer(b), true) }),
          function () { continuer(n, b); }, true, occupe));
        else c.appendChild(etat(T(e === "refusee" ? "campagnes.etat.refusee" : "campagnes.etat.acceptee")));
      } else if (b.genre === "brouillons") {
        var ide = a.espace_id || (S.conv && S.conv.espace_id) || null;
        if (ide) c.appendChild(etat(T("campagnes.carte.brouillons_espace", { nom: nomEspace(ide) }), "", "brouillons-espace"));
        if (ide && typeof S.actif === "string" && S.actif !== ide) {
          var act = bouton(T("campagnes.action.activer_ouvrir", { nom: nomEspace(ide) }), function () { activerEtOuvrir(ide, a, act); }, true, false);
          act.setAttribute("data-dz-camp", "activer-espace");
          actions.appendChild(act);
        } else {
          var lien = el("a", { class: "dzCampLien", href: "#", "data-dz-camp": "ouvrir-planificateur", texte: T("campagnes.action.ouvrir") });
          lien.addEventListener("click", function (ev) { if (ev && ev.preventDefault) ev.preventDefault(); ouvrirPlanificateur(a); });
          actions.appendChild(lien);
        }
      }
      if (actions.firstChild) c.appendChild(actions);
      return c;
    }

    function dessinerFil() {
      vider(fil);
      var info = analyser(S.conv);
      var msgs = (S.conv && S.conv.messages) || [];
      var n = 0, vu = false;
      msgs.forEach(function (m) {
        if (m.role === "utilisateur") {
          var t = (m.blocs || []).filter(function (b) { return b && b.type === "texte"; }).map(function (b) { return b.texte; }).join("\n");
          if (t) { vu = true; fil.appendChild(el("div", { class: "dzCampMsg", "data-role": "utilisateur" }, [el("div", { class: "dzCampTexte", texte: t })])); }
        } else if (m.role === "agent") {
          var msg = el("div", { class: "dzCampMsg", "data-role": "agent" });
          (m.blocs || []).forEach(function (b) {
            if (!b || typeof b !== "object") return;
            if (b.type === "texte" && b.texte) msg.appendChild(el("div", { class: "dzCampTexte", texte: b.texte }));
            else if (b.type === "resultat_outil") msg.appendChild(noeudOutil(b.outil, typeof b.ok === "boolean" ? b.ok : null));
            else if (b.type === "carte") msg.appendChild(carteNode(b, n++, info));
          });
          if (msg.firstChild) { vu = true; fil.appendChild(msg); }
        }
      });
      S.live.forEach(function (x) {
        vu = true;
        if (x.type === "utilisateur") fil.appendChild(el("div", { class: "dzCampMsg", "data-role": "utilisateur" }, [el("div", { class: "dzCampTexte", texte: x.texte })]));
        else if (x.type === "texte") fil.appendChild(el("div", { class: "dzCampMsg", "data-role": "agent" }, [el("div", { class: "dzCampTexte", texte: x.texte })]));
        else if (x.type === "outil") fil.appendChild(noeudOutil(x.nom, !!x.ok));
        else if (x.type === "carte") fil.appendChild(el("div", { class: "dzCampCarte", "data-etat": "live" }, [el("div", { class: "dzCampCarteT", texte: libelle(x.carte) })]));
      });
      if (S.occupe) fil.appendChild(el("div", { class: "dzCampEtat", "data-dz-camp": "travail", texte: T("campagnes.fil.reflechit") }));
      if (S.transitoire && !S.occupe) {
        vu = true;
        fil.appendChild(el("div", { class: "dzCampMsg", "data-role": "agent" }, [carteNode(S.transitoire, null, info)]));
      }
      if (!vu) fil.appendChild(el("div", { class: "dzCampVide", texte: T("campagnes.fil.vide") }));
      try { fil.scrollTop = fil.scrollHeight; } catch (x) { /* rien */ }
    }

    function dessinerPied() {
      champ.setAttribute("placeholder", T(S.correction !== null ? "campagnes.champ.correction" : "campagnes.champ.placeholder"));
      vider(envoyer);
      envoyer.textContent = T("campagnes.champ.envoyer");
      if (S.occupe) envoyer.setAttribute("aria-busy", "true"); else envoyer.removeAttribute("aria-busy");
      var d = S.devis && S.devis.texte === saisie() ? S.devis.data : null;
      var t = "";
      if (d) t = T(S.indice ? "campagnes.devis.relire" : "campagnes.devis.explication", { plafond: T("campagnes.devis.plafond", { usd: usd(d.plafond_usd, true) }) });
      else if (S.calcul) t = T("campagnes.devis.calcul");
      devisLigne.textContent = t;
      devisLigne.setAttribute("data-etat", d ? "pret" : (S.calcul ? "calcul" : "vide"));
    }

    // les noms d'espaces connus : ceux des cartes « espace » du fil, sinon une lecture de /api/espaces
    function retenirNoms() {
      analyser(S.conv).cartes.forEach(function (c) {
        if (c.genre === "espace") ((c.arguments || {}).espaces || []).forEach(function (x) { if (x && x.id && x.nom) S.noms[x.id] = x.nom; });
      });
      var id = S.conv && S.conv.espace_id;
      var brouillons = analyser(S.conv).cartes.some(function (c) { return c.genre === "brouillons"; });
      if (((id && !S.noms[id]) || (brouillons && S.actif === undefined)) && !S.nomsEnCours) {
        S.nomsEnCours = true;
        nomsEspaces().then(function () { S.nomsEnCours = false; dessinerTete(); });
      }
    }

    function dessiner() {
      if (S.ferme) return;
      retenirNoms();
      dessinerTete();
      dessinerFil();
      dessinerPied();
      statut.textContent = S.erreur || "";
      planifierSonde();
    }

    // -- la conversation -----------------------------------------------------------------------------------------------
    async function nomsEspaces() {
      try {
        var r = await window.fetch("/api/espaces?archives=true");
        if (!r.ok) { lectureEspacesRatee(); return; }
        var j = await r.json();
        (j.espaces || []).forEach(function (x) { if (x && x.id) S.noms[x.id] = x.nom || x.id; });
        S.actif = typeof j.actif === "string" ? j.actif : null;
      } catch (e) { lectureEspacesRatee(); }   // le nom retombe sur l'identifiant
    }
    // relecture de branche (M6) : une lecture ratée ne se relance pas à chaque dessin
    function lectureEspacesRatee() {
      if (S.actif === undefined) S.actif = null;
      var id = S.conv && S.conv.espace_id;
      if (id && !S.noms[id]) S.noms[id] = String(id);
    }

    async function charger() {
      if (!S.cid || S.ferme) return;
      try {
        var r = await appel("GET", "/" + S.cid);
        if (!r.ok) { S.erreur = T("campagnes.erreur.reseau", { msg: await detailDe(r) }); return; }
        S.conv = await r.json();
        if (S.conv && S.conv.espace_id && !S.noms[S.conv.espace_id]) await nomsEspaces();
      } catch (e) { S.erreur = T("campagnes.erreur.reseau", { msg: String((e && e.message) || e) }); }
      finally { dessiner(); }
    }

    function assurerCid() {
      if (S.cid) return Promise.resolve(S.cid);
      if (!S.creation) {
        S.creation = (async function () {
          var corps = { role: opts.role || "campagnes" };
          if (opts.espace_id) corps.espace_id = opts.espace_id;
          var r = await appel("POST", "/", corps);
          if (!r.ok) throw new Error(await detailDe(r));
          var c = await r.json();
          S.cid = c.id;
          S.conv = c;
          if (typeof opts.surCid === "function") { try { opts.surCid(S.cid); } catch (e) { /* l'appelant se débrouille */ } }
          return S.cid;
        })().finally(function () { S.creation = null; });
      }
      return S.creation;
    }

    // -- le devis, puis l'envoi (qui vaut accord) -----------------------------------------------------------------------
    async function demanderDevis() {
      var texte = saisie();
      if (!texte || S.ferme) return null;
      var seq = ++S.seq;
      S.calcul = true; dessinerPied();
      try {
        await assurerCid();
        var r = await appel("POST", "/" + S.cid + "/devis", { texte: texte });
        if (!r.ok) throw new Error(await detailDe(r));
        var d = await r.json();
        if (seq === S.seq && saisie() === texte) S.devis = { texte: texte, data: d };
      } catch (e) {
        if (seq === S.seq) { S.devis = null; S.erreur = T("campagnes.erreur.reseau", { msg: String((e && e.message) || e) }); statut.textContent = S.erreur; }
      } finally {
        if (seq === S.seq) S.calcul = false;
        dessinerPied();
      }
      return S.devis;
    }

    function surSaisie() {
      S.indice = "";
      if (S.devis && S.devis.texte !== saisie()) S.devis = null;
      dessinerPied();
      if (S.minuteur) clearTimeout(S.minuteur);
      S.minuteur = null;
      if (saisie()) S.minuteur = setTimeout(function () { S.minuteur = null; demanderDevis(); }, DELAI_DEVIS_MS);
    }

    async function surEnvoi() {
      if (S.occupe || S.ferme) return;
      var texte = saisie();
      if (!texte) return;
      if (S.minuteur) { clearTimeout(S.minuteur); S.minuteur = null; }
      if (!S.devis || S.devis.texte !== texte) {
        // l'envoi vaut accord : le plafond doit être VU avant. Ce clic ne fait que l'afficher.
        var d = await demanderDevis();
        if (d) { S.indice = "relire"; dessinerPied(); }
        return;
      }
      var plafond = S.devis.data.plafond_usd;
      champ.value = "";
      S.devis = null; S.correction = null; S.indice = "";
      await partir(texte, plafond, null);
    }

    function messageHttp(res) {
      return (async function () {
        if (res.status === 503) return T("campagnes.erreur.sans_cle");
        var d = await detailDe(res);
        if (res.status === 409) return /illisible|unreadable/i.test(d) ? T("campagnes.erreur.reseau", { msg: d }) : T("campagnes.erreur.occupee");
        if (res.status === 402) return T("campagnes.erreur.plafond_detail", { msg: d });
        return T("campagnes.erreur.reseau", { msg: d });
      })();
    }

    function evenement(e) {
      // un morceau de texte n'est pas un changement d'état : l'évènement `texte` du bloc redessine, une fois (L4.1 T3)
      if (e.type === "delta") return;
      if (e.type === "texte") S.live.push({ type: "texte", texte: String(e.texte || "") });
      else if (e.type === "outil") S.live.push({ type: "outil", nom: String(e.nom || ""), ok: !!e.ok, resume: String(e.resume || "") });
      else if (e.type === "carte" && e.carte) {
        S.live.push({ type: "carte", carte: e.carte });
        if (e.carte.genre === "continuer") S.transitoire = e.carte;
      } else if (e.type === "erreur") {
        if (e.code === "sans_cle") S.erreur = T("campagnes.erreur.sans_cle");
        else if (e.code === "dz_plafond") S.erreur = T("campagnes.erreur.plafond");
        else if (e.code === "occupee") S.erreur = T("campagnes.erreur.occupee");
        else S.erreur = T("campagnes.erreur.moteur", { msg: String(e.message || e.code || "") });
      }
      dessiner();
    }

    function compter(conv, genre) {
      return analyser(conv).cartes.filter(function (b) { return b.genre === genre; }).length;
    }

    // `apres.carte` : la carte « continuer » (rang n) à marquer acceptée une fois la réponse partie
    async function partir(texte, plafond, apres) {
      if (S.occupe || S.ferme) return;
      S.occupe = true; S.erreur = ""; S.transitoire = null;
      var avant = compter(S.conv, "continuer");
      S.live = [{ type: "utilisateur", texte: texte }];
      dessiner();
      var parti = false;
      try {
        await assurerCid();
        var r = await appel("POST", "/" + S.cid + "/message", { texte: texte, plafond_usd: plafond });
        if (!r.ok) {
          S.erreur = await messageHttp(r);
          if (!saisie()) champ.value = texte;   // rien n'est parti : le texte revient dans le champ
        } else {
          parti = true;
          await lireFlux(r, evenement);
        }
      } catch (e) {
        if (S.ferme) return;
        S.erreur = T("campagnes.erreur.reseau", { msg: String((e && e.message) || e) });
        if (!parti && !saisie()) champ.value = texte;   // rien n'est parti : le texte revient dans le champ
      } finally {
        S.occupe = false;
      }
      if (parti && apres && typeof apres.carte === "number") {
        try { await appel("POST", "/" + S.cid + "/carte/" + apres.carte, { decision: "acceptee" }); } catch (e) { /* la carte reste cliquable */ }
      }
      var erreur = S.erreur;
      S.live = [];
      await charger();
      if (compter(S.conv, "continuer") > avant) S.transitoire = null;   // la carte est maintenant écrite dans le fil
      S.erreur = erreur;
      dessiner();
    }

    // -- les cartes ------------------------------------------------------------------------------------------------------
    async function decider(n, decision, extra) {
      if (n === null || S.occ[n] || S.ferme) return;
      S.occ[n] = true; dessiner();
      try {
        var corps = { decision: decision };
        for (var k in (extra || {})) corps[k] = extra[k];
        var r = await appel("POST", "/" + S.cid + "/carte/" + n, corps);
        if (!r.ok) throw new Error(await detailDe(r));
        S.conv = await r.json();
        S.erreur = "";
      } catch (e) {
        if (S.ferme) return;
        var msgE = T("campagnes.erreur.carte", { msg: String((e && e.message) || e) });
        delete S.occ[n];
        S.erreur = "";
        await charger();   // l'état réel (409 : déjà décidée)
        if (S.ferme) return;
        // la carte n'est plus « proposee » (déjà décidée ailleurs) : l'erreur n'a plus lieu d'être affichée
        var infoE = analyser(S.conv), xE = infoE.etats[n];
        var etatE = xE ? (xE.etat || "proposee") : ((infoE.cartes[n] && infoE.cartes[n].etat) || "proposee");
        if (etatE === "proposee" && !S.erreur) S.erreur = msgE;
      } finally {
        delete S.occ[n];
        dessiner();
      }
    }

    // le devis accepté : l'écran appelle LUI-MÊME la route de génération de la carte, puis annonce le résultat
    async function genererDevis(n, b) {
      var a = b.arguments || {};
      if (n === null || S.occ[n] || S.ferme) return;
      if (S.rendus[n]) { await enregistrerRendu(S.cid, n, S.rendus[n]); return; }   // déjà payé : on ne refait que /carte
      if (!ROUTES[a.genre] || a.route !== ROUTES[a.genre]) { S.erreur = T("campagnes.erreur.generation", { msg: String(a.route || "") }); dessiner(); return; }
      S.occ[n] = true; S.erreur = ""; dessiner();
      var extra = null;
      try {
        var r = await window.fetch(a.route, { method: "POST", headers: JSON_H, body: JSON.stringify(a.corps || {}) });
        if (!r.ok) throw new Error(await detailDe(r));
        var j = await r.json();
        if (a.genre === "video") { if (j && j.job_id) extra = { job_id: String(j.job_id) }; }
        else if (a.genre === "image") { var f = nomImage(j); if (f) extra = { fichier: f }; }
        else if (j && typeof j.filename === "string" && j.filename) extra = { fichier: j.filename };
        if (!extra) throw new Error(T("campagnes.erreur.sans_resultat"));
      } catch (e) {
        delete S.occ[n];
        S.erreur = T("campagnes.erreur.generation", { msg: String((e && e.message) || e) });
        dessiner();
        return;
      }
      S.rendus[n] = extra;
      garderRendu(S.cid, n, extra);         // payé : gardé jusqu'à ce que /carte l'ait noté (démontage, rechargement)
      delete S.occ[n];
      await enregistrerRendu(S.cid, n, extra);
    }

    // relecture de branche (IMPORTANT 2) : un rendu PAYÉ s'annonce à /carte même si le composant est démonté
    // pendant ou juste après la génération : window.fetch direct (sans le signal d'annulation), malgré S.ferme, deux
    // tentatives ; {cid, n, extra} reste en sessionStorage jusqu'au succès et se rejoue au montage d'un cid connu.
    var CLE_RENDU = "dzCampagnes.rendu:";
    function cleRendu(cid, n) { return CLE_RENDU + cid + "/" + n; }
    function garderRendu(cid, n, extra) {
      try { window.sessionStorage.setItem(cleRendu(cid, n), JSON.stringify(extra)); } catch (e) { /* stockage absent */ }
    }
    function oublierRendu(cid, n) {
      try { window.sessionStorage.removeItem(cleRendu(cid, n)); } catch (e) { /* stockage absent */ }
    }
    function rendusEnAttente(cid) {
      var out = {}, pre = CLE_RENDU + cid + "/";
      try {
        var ss = window.sessionStorage;
        for (var i = 0; i < ss.length; i++) {
          var k = ss.key(i);
          if (!k || k.indexOf(pre) !== 0) continue;
          var n = Number(k.slice(pre.length)), v = JSON.parse(ss.getItem(k));
          if (isFinite(n) && v && typeof v === "object") out[n] = v;
        }
      } catch (e) { /* stockage absent ou illisible */ }
      return out;
    }
    async function posterRendu(cid, n, extra) {
      var corps = { decision: "acceptee" };
      for (var k in (extra || {})) corps[k] = extra[k];
      var msgR = "";
      for (var essai = 0; essai < 2; essai++) {
        try {
          var r = await window.fetch(BASE + "/" + cid + "/carte/" + n, { method: "POST", headers: JSON_H, body: JSON.stringify(corps) });
          if (r.ok) { oublierRendu(cid, n); var cv = null; try { cv = await r.json(); } catch (e) { cv = null; } return { ok: true, conv: cv }; }
          if (r.status === 409) { oublierRendu(cid, n); return { ok: true, conv: null }; }   // déjà notée
          msgR = await detailDe(r);
        } catch (e) { msgR = String((e && e.message) || e); }
      }
      return { ok: false, msg: msgR };
    }
    async function enregistrerRendu(cid, n, extra) {
      if (!cid || n === null) return;
      S.occ[n] = true;
      if (!S.ferme) dessiner();
      var res = await posterRendu(cid, n, extra);
      delete S.occ[n];
      if (S.ferme) return;
      if (res.ok) {
        S.erreur = "";
        if (res.conv && res.conv.messages) S.conv = res.conv; else await charger();
      } else {
        await charger();                           // l'état réel ; l'erreur reste dite, le rendu reste gardé
        if (S.ferme) return;
        S.erreur = T("campagnes.erreur.carte", { msg: res.msg });
      }
      dessiner();
    }
    async function rejouerRendus() {
      var att = rendusEnAttente(S.cid);
      for (var k in att) S.rendus[k] = att[k];     // avant tout dessin de la carte : jamais de bouton « Générer »
      for (var k2 in att) await posterRendu(S.cid, Number(k2), att[k2]);
    }

    function continuer(n, b) {
      var a = b.arguments || {};
      var texte = String(a.texte || "") || T("campagnes.message.continuer");
      partir(texte, montantContinuer(b), { carte: n });
    }

    // « Continuer » après un rendu terminé : le texte est posé dans le champ, le plafond s'affiche, l'utilisateur envoie
    function reprendre() {
      champ.value = T("campagnes.message.continuer");
      surSaisie();
      try { champ.focus(); } catch (e) { /* rien */ }
    }

    // l'espace des brouillons n'est pas l'actif (GET /api/schedule ne rend que l'actif) : sur le CLIC de l'utilisateur,
    // l'activer — par l'activation de la coque quand elle est exposée (window.__dzEspActiver : POST, cache relu,
    // « deepotus:espace-refresh »), sinon POST /api/espaces/{id}/activate puis « deepotus:espace-refresh » —, puis
    // recharger le calendrier et l'ouvrir. Jamais automatique.
    async function activerEtOuvrir(id, a, btn) {
      if (S.ferme || (btn && btn.getAttribute("aria-busy") === "true")) return;
      if (btn) btn.setAttribute("aria-busy", "true");
      try {
        if (typeof window.__dzEspActiver === "function") await window.__dzEspActiver(id);
        else {
          var r = await window.fetch("/api/espaces/" + encodeURIComponent(id) + "/activate", { method: "POST", headers: JSON_H, body: "{}" });
          if (!r.ok) throw new Error(await detailDe(r));
          window.dispatchEvent(new Event("deepotus:espace-refresh"));
        }
        S.actif = id;
        window.dispatchEvent(new CustomEvent("deepotus:schedule-reload"));
        S.erreur = "";
        ouvrirPlanificateur(a);
      } catch (e) {
        S.erreur = T("campagnes.erreur.activation", { msg: String((e && e.message) || e) });
      } finally {
        if (btn) btn.removeAttribute("aria-busy");
        dessiner();
      }
    }

    function ouvrirPlanificateur(a) {
      try {
        window.dispatchEvent(new CustomEvent("deepotus:navigate", { detail: { view: "scheduler" } }));
        window.dispatchEvent(new CustomEvent("dz-campagnes-brouillons", { detail: { ids: a.ids || [], espace_id: a.espace_id || (S.conv && S.conv.espace_id) || null, cid: S.cid } }));
      } catch (e) { /* pas de navigation possible hors de la SPA */ }
    }

    // un rendu vidéo en cours : on relit la conversation (le GET note les jobs finis) jusqu'à ce qu'il soit fini
    function planifierSonde() {
      if (S.sonde) { clearTimeout(S.sonde); S.sonde = null; }
      if (S.ferme || S.occupe || !S.conv) return;
      var info = analyser(S.conv);
      var attente = Object.keys(info.etats).some(function (k) {
        var x = info.etats[k], c = info.cartes[Number(k)];
        return c && c.genre === "devis" && x.etat === "acceptee" && x.arguments && x.arguments.job_id;
      });
      if (!attente) return;
      S.sonde = setTimeout(function () { S.sonde = null; charger(); }, SONDE_MS);
      if (S.sonde && typeof S.sonde.unref === "function") S.sonde.unref();
    }

    // -- montage -----------------------------------------------------------------------------------------------------
    champ.addEventListener("input", surSaisie);
    champ.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) { if (ev.preventDefault) ev.preventDefault(); surEnvoi(); }
    });
    envoyer.addEventListener("click", surEnvoi);
    hote.appendChild(racine);
    dessiner();
    if (opts.brief) { champ.value = String(opts.brief); surSaisie(); }
    if (S.cid) rejouerRendus().then(charger);
    else if (opts.espace_id) nomsEspaces().then(function () { dessiner(); });

    return {
      cid: function () { return S.cid; },
      recharger: charger,
      demonter: function () {
        S.ferme = true;
        if (S.minuteur) clearTimeout(S.minuteur);
        if (S.sonde) clearTimeout(S.sonde);
        S.minuteur = S.sonde = null;
        if (S.stop) { try { S.stop.abort(); } catch (e) { /* rien */ } }
        if (racine.parentNode) racine.parentNode.removeChild(racine);
      }
    };
  }

  window.DzCampagnes = { monter: monter };
})();
