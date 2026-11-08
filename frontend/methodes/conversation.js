/* conversation.js — la CONVERSATION avec un agent métier depuis la fiche d'une méthode (t435, lot M2, 08/11/2026).
   Chargé après methodes.js, dont il reprend les outils (window.__dzMethodes : T, el, icone, langue).

   Ouvrir : POST /api/agents-metier/<agent>/conversations {methode} -> un panneau latéral.
   Envoyer, en DEUX temps et jamais sans accord : 1) POST …/devis {texte} -> « Envoyer (≈ x $) » ; 2) le clic envoie
   POST …/message {texte, confirme_cout: true, max_usd: devis} -> la réponse, les outils appelés (nom + résumé), le coût.
   Erreurs : 503 (clé Anthropic absente), 402 (plafond), 409 (occupée / coût), autre -> le message du serveur.
   Les exemples de la fiche deviennent des suggestions qui remplissent le champ (rien n'est envoyé sans clic).
   Textes : dzT("methodes.agent.…") ; réponses et données par textContent seulement. */
(function () {
  "use strict";
  if (window.__dzMethodesConversation) return;
  var M = window.__dzMethodes;
  if (!M) return;
  var T = M.T, el = M.el, icone = M.icone;

  var C = { agent: "", cid: "", devis: null, occupe: false, panneau: null };

  function envoyerJson(url, corps) {
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(corps || {}) }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) { return { statut: r.status, json: j }; });
    });
  }
  function base() { return "/api/agents-metier/" + encodeURIComponent(C.agent) + "/conversations"; }
  function prix(usd) { return (Math.round((Number(usd) || 0) * 1e4) / 1e4).toFixed(usd < 0.1 ? 3 : 2); }

  function bulle(role, texte, extra) {
    var b = el("div", { cls: "mt-bulle mt-bulle--" + role }, [el("p", { texte: texte })]);
    (extra || []).forEach(function (n) { if (n) b.appendChild(n); });
    C.fil.appendChild(b);
    C.fil.scrollTop = C.fil.scrollHeight;
    return b;
  }

  function erreur(statut, json) {
    var d = json && json.detail;
    var cle = statut === 503 ? "methodes.agent.sans_cle" : statut === 402 ? "methodes.agent.plafond"
      : statut === 409 ? "methodes.agent.occupe" : "";
    var txt = cle ? T(cle) : (typeof d === "string" ? d : (d && d.message) || T("methodes.agent.erreur"));
    bulle("erreur", txt);
  }

  function majBouton() {
    var t = C.champ.value.trim();
    C.envoyer.disabled = C.occupe || !t;
    C.envoyer.textContent = C.devis && C.devis.texte === t
      ? T("methodes.agent.envoyer_prix", { usd: prix(C.devis.usd) }) : T("methodes.agent.estimer");
  }

  function estimer(texte) {
    C.occupe = true; majBouton();
    return envoyerJson(base() + "/" + C.cid + "/devis", { texte: texte, langue: M.langue() }).then(function (r) {
      C.occupe = false;
      if (r.statut !== 200) { erreur(r.statut, r.json); majBouton(); return; }
      if (!r.json.cle) { bulle("erreur", T("methodes.agent.sans_cle")); majBouton(); return; }
      C.devis = { texte: texte, usd: r.json.usd };
      majBouton();
    }, function () { C.occupe = false; bulle("erreur", T("methodes.agent.erreur")); majBouton(); });
  }

  function envoyer() {
    var texte = C.champ.value.trim();
    if (!texte || C.occupe) return;
    if (!C.devis || C.devis.texte !== texte) { estimer(texte); return; }
    var usd = C.devis.usd;
    C.occupe = true; majBouton();
    bulle("user", texte);
    var attente = bulle("agent", T("methodes.agent.reflechit"));
    envoyerJson(base() + "/" + C.cid + "/message", { texte: texte, langue: M.langue(), confirme_cout: true, max_usd: usd })
      .then(function (r) {
        attente.remove();
        C.occupe = false; C.devis = null;
        if (r.statut !== 200) { erreur(r.statut, r.json); majBouton(); return; }
        C.champ.value = "";
        var j = r.json;
        var outils = (j.outils || []).length ? el("ul", { cls: "mt-outils" }, (j.outils || []).map(function (o) {
          return el("li", { cls: o.ok ? "" : "mt-outil--ko" }, [el("b", { texte: o.nom }), el("span", { texte: " — " + o.resume })]);
        })) : null;
        var pied = el("div", { cls: "mt-bulle-pied", texte: T("methodes.agent.cout", { usd: prix(j.usd) })
          + (j.arret && j.arret !== "fin" ? " · " + T("methodes.agent.arret." + j.arret) : "") });
        bulle("agent", j.texte || T("methodes.agent.sans_texte"), [outils, pied]);
        majBouton();
      }, function () { attente.remove(); C.occupe = false; bulle("erreur", T("methodes.agent.erreur")); majBouton(); });
  }

  function fermer() { if (C.panneau) { C.panneau.remove(); C.panneau = null; } }

  function ouvrir(f) {
    fermer();
    C.agent = f.agent; C.cid = ""; C.devis = null; C.occupe = false;
    C.fil = el("div", { cls: "mt-fil", a: { "aria-live": "polite" } });
    C.champ = el("textarea", { cls: "mt-champ mt-champ--message", placeholder: T("methodes.agent.ecrire"),
      a: { rows: "3", "aria-label": T("methodes.agent.ecrire"), "data-dz-methodes-message": true },
      on: { input: majBouton, keydown: function (e) { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) envoyer(); } } });
    C.envoyer = el("button", { cls: "mt-btn mt-btn--accent", type: "button", a: { "data-dz-methodes-envoyer": true },
      on: { click: envoyer } });
    var suggestions = el("div", { cls: "mt-suggestions" }, (f.exemples || []).map(function (x) {
      return el("button", { cls: "mt-btn mt-btn--petit", type: "button", texte: x,
        on: { click: function () { C.champ.value = x; C.devis = null; majBouton(); C.champ.focus(); } } });
    }));
    C.panneau = el("aside", { cls: "mt-conv", a: { "data-dz-methodes-conversation": f.agent, role: "dialog",
      "aria-label": T("methodes.agent.parler", { agent: f.agent_libelle }) } }, [
      el("header", { cls: "mt-conv-tete" }, [
        icone("dz-action-lancer-recette", 16),
        el("b", { texte: f.agent_libelle }),
        el("span", { cls: "mt-sous", texte: f.titre }),
        el("button", { cls: "mt-btn mt-btn--discret", type: "button", texte: T("methodes.agent.fermer"),
          a: { "data-dz-methodes-fermer": true }, on: { click: fermer } })
      ]),
      C.fil, suggestions,
      el("div", { cls: "mt-conv-saisie" }, [C.champ, C.envoyer]),
      el("p", { cls: "mt-conv-note", texte: T("methodes.agent.note") })
    ]);
    document.body.appendChild(C.panneau);
    majBouton();
    C.occupe = true; majBouton();
    envoyerJson("/api/agents-metier/" + encodeURIComponent(f.agent) + "/conversations", { methode: f.slug }).then(function (r) {
      C.occupe = false;
      if (r.statut !== 200) { erreur(r.statut, r.json); majBouton(); return; }
      C.cid = r.json.id;
      bulle("agent", T("methodes.agent.accueil", { agent: f.agent_libelle, methode: f.titre }));
      majBouton();
      C.champ.focus();
    }, function () { C.occupe = false; bulle("erreur", T("methodes.agent.erreur")); majBouton(); });
  }

  window.__dzMethodesConversation = { ouvrir: ouvrir, fermer: fermer, C: C };
})();
