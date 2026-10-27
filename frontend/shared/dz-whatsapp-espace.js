/* dz-whatsapp-espace.js — Réglages › Espaces › « Agent WhatsApp » : le panneau des réglages de l'agent WhatsApp d'un
   espace (t311 tâche 8, 27/10/2026, plan docs/superpowers/plans/2026-10-27-t311-agent-whatsapp.md).
   SOURCE : frontend/shared/dz-whatsapp-espace.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-whatsapp-espace.js,
   chargée par frontend/dist/index.html (balise classique après dz-pour-qui.js). Le bouton qui l'ouvre est posé dans
   DzEspaces par le maillon scripts/patch_bundle_whatsapppage.py (P4). Banc : backend/tests/test_whatsapp_page_ecran.py
   (joué sous node, faux DOM, faux fetch).

   window.__dzWhatsappEspace.ouvrir(espaceId) -> Promise<null> (résolue à la fermeture) : la boîte (charte de dialogue.js,
   angles vifs, en-tête IBM Plex Mono en capitales ; Tab piégé, Échap ou « Fermer » ferment) qui lit
   GET /api/espaces/{id}/whatsapp/reglages et écrit PUT …/reglages avec, au format EXACT du serveur (tâche 1) :
     {plafond_mois, marche_defaut, agent: {actif, mode, roles, horaires: {jours, debut, fin, fuseau},
      message_hors_horaires, plafond_jour_contact, mots_humain[, modele_validation]}}
   - les entiers partent en nombres quand la saisie en est un, sinon tels quels : le serveur refuse (400, message L10)
     et la boîte montre SON message ; rien n'est vérifié en double ici ;
   - mots_humain : la saisie coupée aux virgules (et fins de ligne), rognée, sans vide ;
   - mode « auto » : jamais sans une confirmation explicite (window.__dzDialogue.confirmer, phrase d'avertissement
     whatsapp.espace.auto_avertissement, aussi affichée sous le choix). Sans la boîte de dialogue, le mode reste
     « brouillon » (jamais de confirm natif : test_dialogues_partout) ;
   - modele_validation : les modèles du PREMIER numéro relié de l'espace (GET /api/comptes?espace=<id>, comptes whatsapp
     avec WHATSAPP_PHONE_ID ; c'est lui qui envoie la validation, ruling 10), GET /api/whatsapp/{cid}/modeles?espace=<id>,
     catégorie « utility », statut « approved », une variable au plus (ruling 10). Sans numéro relié ou si la lecture
     échoue, le champ dit pourquoi, reste vide et grisé, et le PUT ne porte PAS modele_validation (le modèle rangé n'est
     pas effacé). Un modèle rangé absent de la liste y reste proposé (sous son nom) pour ne pas l'effacer en silence.
   Attributs des bancs : data-dz-wa-espace-* (boite, actif, mode, avertissement, role, jour, debut, fin, fuseau,
   hors-horaires, plafond-jour, mots, modele, modele-note, plafond-mois, marche, enregistrer, fermer, msg, erreur).
   Données utilisateur par textContent. Textes : clés whatsapp.espace.* (frontend/shared/i18n/whatsapp.json). Glyphes
   Deepotus (dzIcone), jamais d'emoji. */
(function () {
  "use strict";
  if (window.__dzWhatsappEspace) return;

  var JSON_H = { "Content-Type": "application/json" };
  var ROLES = ["faq", "rendez_vous", "commande", "validation"];
  var LIB_MODE = { brouillon: "whatsapp.espace.mode_brouillon", auto: "whatsapp.espace.mode_auto" };
  var LIB_JOUR = ["whatsapp.espace.jour_0", "whatsapp.espace.jour_1", "whatsapp.espace.jour_2", "whatsapp.espace.jour_3",
                  "whatsapp.espace.jour_4", "whatsapp.espace.jour_5", "whatsapp.espace.jour_6"];
  var S = {
    voile: "position:fixed;inset:0;z-index:9998;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center",
    boite: "width:680px;max-width:94vw;max-height:88vh;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    corps: "padding:12px 14px;overflow-y:auto;display:flex;flex-direction:column;gap:14px;color:var(--txt-base,var(--ink,#cfd6e2))",
    section: "display:flex;flex-direction:column;gap:7px",
    titreSec: "font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    ligne: "display:flex;align-items:center;gap:8px;flex-wrap:wrap",
    etiquette: "font-size:12px;color:var(--txt-hi,var(--ink-strong,#e6e9ee));min-width:150px",
    note: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    alerte: "font-size:11.5px;padding:6px 8px;border:1px solid var(--amber,#e5a50a);color:var(--txt-hi,var(--ink-strong,#e6e9ee))",
    champ: "font:inherit;font-size:12px;padding:4px 6px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));color:var(--txt-hi,var(--ink-strong,#e6e9ee));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138))",
    zone: "font:inherit;font-size:12px;padding:4px 6px;border-radius:0;min-height:52px;width:100%;box-sizing:border-box;background:var(--srf-raised,var(--bg-panel-3,#1b2028));color:var(--txt-hi,var(--ink-strong,#e6e9ee));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138))",
    coche: "display:inline-flex;align-items:center;gap:5px;font-size:12px",
    statut: "font-size:12px;color:var(--txt-hi,var(--ink-strong,#e6e9ee));padding:0 14px 8px",
    erreur: "font-size:12px;color:var(--red,#e5484d);padding:0 14px 8px",
    pied: "display:flex;gap:8px;justify-content:flex-end;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
    btn: "min-width:88px;height:28px;padding:0 12px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit",
    glyphe: "display:inline-flex;width:14px;height:14px"
  };

  function T(cle, vars) { return typeof window.dzT === "function" ? window.dzT(cle, vars) : cle; }
  function icone(cle) { return typeof window.dzIcone === "function" ? window.dzIcone(cle, { taille: 14 }) : ""; }
  function el(tag, style, texte) {
    var n = document.createElement(tag);
    if (style) n.setAttribute("style", style);
    if (texte != null) n.textContent = texte;
    return n;
  }
  function bouton(texte, style, glyphe) {
    var b = el("button", style);
    b.type = "button";
    if (glyphe) {
      var g = el("span", S.glyphe);
      g.innerHTML = icone(glyphe);
      b.appendChild(g);
    }
    b.appendChild(el("span", "", texte));
    return b;
  }
  function option(valeur, texte) {
    var o = el("option", "", texte);
    o.value = valeur;
    return o;
  }

  function envoyer(url, methode, corps) {
    var o = { method: methode || "GET" };
    if (corps !== undefined) { o.headers = JSON_H; o.body = JSON.stringify(corps); }
    return fetch(url, o).then(function (R) {
      return R.json().catch(function () { return {}; }).then(function (j) {
        if (!R.ok) {
          var d = j && j.detail;
          throw new Error(d && typeof d === "object" && d.message ? String(d.message) : d ? String(d) : "HTTP " + R.status);
        }
        return j;
      });
    });
  }

  // ── la saisie vers le format du serveur (pures) ──
  function entier(v) {
    var t = String(v == null ? "" : v).trim();
    return /^-?\d+$/.test(t) ? Number(t) : t;           // pas un entier : envoyé tel quel, le serveur le refuse (400)
  }
  function mots(v) {
    return String(v || "").split(/[,\n]/).map(function (m) { return m.trim(); }).filter(function (m) { return m; });
  }
  function relie(c) {
    return !!c && c.plateforme === "whatsapp" && (c.champs || []).some(function (x) {
      return x && x.nom === "WHATSAPP_PHONE_ID" && x.valeur;
    });
  }
  function utilisable(m) {
    return !!m && typeof m.nom === "string" && m.nom && typeof m.langue === "string" && m.langue
      && String(m.categorie || "").toLowerCase() === "utility" && String(m.statut || "").toLowerCase() === "approved"
      && (Number(m.n_parametres) || 0) <= 1;
  }
  function memeModele(a, b) { return !!a && !!b && a.nom === b.nom && a.langue === b.langue; }

  // les modèles UTILITY approuvés du premier numéro relié de l'espace : {liste: [...] | null, note: ""}
  function chargerModeles(eid) {
    var q = "?espace=" + encodeURIComponent(eid);
    return envoyer("/api/comptes" + q).then(function (j) {
      var c = ((j && j.comptes) || []).filter(relie)[0];
      if (!c) return { liste: null, note: T("whatsapp.espace.modele_sans_numero") };
      return envoyer("/api/whatsapp/" + encodeURIComponent(c.id) + "/modeles" + q).then(function (l) {
        var liste = (Array.isArray(l) ? l : []).filter(utilisable).map(function (m) { return { nom: m.nom, langue: m.langue }; });
        return { liste: liste, note: liste.length ? "" : T("whatsapp.espace.modele_aucun_utilitaire") };
      });
    }).catch(function (e) {
      return { liste: null, note: T("whatsapp.espace.modele_illisible", { detail: String(e && e.message || e) }) };
    });
  }

  var courant = null;
  function ouvrir(espaceId) {
    if (typeof espaceId !== "string" || !espaceId) return Promise.resolve(null);
    if (courant) courant();
    return boite(espaceId);
  }

  function boite(eid) {
    return new Promise(function (resoudre) {
      var base = "/api/espaces/" + encodeURIComponent(eid) + "/whatsapp/reglages";
      var st = { reglages: null, modeles: null, note: "", nom: eid, modeServeur: "brouillon", modeChoisi: "brouillon",
                 autoConfirme: false, occupe: false, attente: false };
      var F = {};                                        // les champs du formulaire en cours
      var voile = el("div", S.voile);
      voile.setAttribute("role", "dialog");
      voile.setAttribute("aria-modal", "true");
      voile.setAttribute("data-dz-wa-espace-boite", eid);
      voile.className = "dz-dialogue dz-whatsapp-espace";
      var cadre = el("div", S.boite);
      var tete = el("div", S.tete);
      var corps = el("div", S.corps);
      var msg = el("div", S.statut, T("whatsapp.espace.lecture"));
      msg.setAttribute("role", "status");
      msg.setAttribute("data-dz-wa-espace-msg", "1");
      var erreur = el("div", S.erreur, "");
      erreur.setAttribute("role", "alert");
      erreur.setAttribute("data-dz-wa-espace-erreur", "1");
      var pied = el("div", S.pied);
      var enregistrerB = bouton(T("whatsapp.espace.enregistrer"), S.btn);
      enregistrerB.setAttribute("data-dz-wa-espace-enregistrer", "1");
      enregistrerB.disabled = true;
      var fermerB = bouton(T("commun.action.fermer"), S.btn);
      fermerB.setAttribute("data-dz-wa-espace-fermer", "1");
      pied.appendChild(enregistrerB);
      pied.appendChild(fermerB);
      cadre.appendChild(tete);
      cadre.appendChild(corps);
      cadre.appendChild(msg);
      cadre.appendChild(erreur);
      cadre.appendChild(pied);
      voile.appendChild(cadre);

      var fini = false;
      function fin() {
        if (fini) return;
        fini = true;
        if (courant === fin) courant = null;
        document.removeEventListener("keydown", surTouche, true);
        voile.remove();
        resoudre(null);
      }
      function pieger(ev) {
        var l = Array.prototype.slice.call(cadre.querySelectorAll("button, input, select, textarea, a[href], [tabindex]")).filter(function (n) {
          return !n.disabled && n.getAttribute("tabindex") !== "-1" && n.offsetParent !== null;
        });
        ev.preventDefault();
        if (!l.length) return;
        var i = l.indexOf(document.activeElement), n = l.length;
        var j = i < 0 ? (ev.shiftKey ? n - 1 : 0) : (i + (ev.shiftKey ? -1 : 1) + n) % n;
        l[j].focus();
      }
      function surTouche(ev) {
        if (st.attente) return;     // la confirmation de __dzDialogue a la main : ni Tab ni Échap ne sont à nous
        if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); fin(); }
        else if (ev.key === "Tab") pieger(ev);
      }
      courant = fin;
      fermerB.addEventListener("click", fin);
      enregistrerB.addEventListener("click", enregistrer);
      document.addEventListener("keydown", surTouche, true);

      function dire(t) { msg.textContent = t || ""; }
      function refus(e) { erreur.textContent = T("whatsapp.espace.refus", { detail: String(e && e.message || e) }); }
      function titre() {
        var t = T("whatsapp.espace.titre", { nom: st.nom });
        tete.textContent = t;
        voile.setAttribute("aria-label", t);
      }
      function section(cle) {
        var s = el("div", S.section);
        s.appendChild(el("div", S.titreSec, T(cle)));
        corps.appendChild(s);
        return s;
      }
      function ligne(parent, cle, champ, aide) {
        var l = el("label", S.ligne);
        l.appendChild(el("span", S.etiquette, T(cle)));
        l.appendChild(champ);
        parent.appendChild(l);
        if (aide) parent.appendChild(el("div", S.note, T(aide)));
        return l;
      }
      function coche(parent, cle, caseC) {
        var l = el("label", S.coche);
        caseC.type = "checkbox";
        l.appendChild(caseC);
        l.appendChild(el("span", "", T(cle)));
        parent.appendChild(l);
      }

      function formulaire() {
        var r = st.reglages, a = r.agent, h = a.horaires;
        corps.textContent = "";
        F = {};
        // — l'agent —
        var sA = section("whatsapp.espace.section_agent");
        var actif = el("input", "");
        actif.setAttribute("aria-label", T("whatsapp.espace.actif"));
        actif.setAttribute("data-dz-wa-espace-actif", "1");
        var lA = el("div", S.ligne);
        coche(lA, "whatsapp.espace.actif", actif);
        actif.checked = !!a.actif;
        sA.appendChild(lA);
        sA.appendChild(el("div", S.note, T("whatsapp.espace.actif_aide")));
        var mode = el("select", S.champ);
        mode.setAttribute("aria-label", T("whatsapp.espace.mode"));
        mode.setAttribute("data-dz-wa-espace-mode", "1");
        mode.appendChild(option("brouillon", T(LIB_MODE.brouillon)));
        mode.appendChild(option("auto", T(LIB_MODE.auto)));
        mode.value = st.modeChoisi;
        ligne(sA, "whatsapp.espace.mode", mode);
        var avert = el("div", S.alerte, T("whatsapp.espace.auto_avertissement"));
        avert.setAttribute("data-dz-wa-espace-avertissement", "1");
        sA.appendChild(avert);
        mode.addEventListener("change", function () { choisirMode(mode.value); });
        sA.appendChild(el("div", S.titreSec, T("whatsapp.espace.roles")));
        var roles = el("div", S.ligne);
        var rFaq = el("input", "");
        rFaq.setAttribute("aria-label", T("whatsapp.espace.role_faq"));
        var rRdv = el("input", "");
        rRdv.setAttribute("aria-label", T("whatsapp.espace.role_rendez_vous"));
        var rCommande = el("input", "");
        rCommande.setAttribute("aria-label", T("whatsapp.espace.role_commande"));
        var rValidation = el("input", "");
        rValidation.setAttribute("aria-label", T("whatsapp.espace.role_validation"));
        F.roles = { faq: rFaq, rendez_vous: rRdv, commande: rCommande, validation: rValidation };
        ROLES.forEach(function (nom) {
          var c = F.roles[nom];
          c.setAttribute("data-dz-wa-espace-role", nom);
          coche(roles, "whatsapp.espace.role_" + nom, c);
          c.checked = (a.roles || []).indexOf(nom) >= 0;
        });
        sA.appendChild(roles);
        // — les horaires —
        var sH = section("whatsapp.espace.section_horaires");
        var jours = el("div", S.ligne);
        jours.appendChild(el("span", S.etiquette, T("whatsapp.espace.jours")));
        F.jours = LIB_JOUR.map(function (cle, i) {
          var c = el("input", "");
          c.setAttribute("aria-label", T(cle));
          c.setAttribute("data-dz-wa-espace-jour", String(i));
          coche(jours, cle, c);
          c.checked = (h.jours || []).indexOf(i) >= 0;
          return c;
        });
        sH.appendChild(jours);
        var debut = el("input", S.champ);
        debut.type = "time";
        debut.setAttribute("aria-label", T("whatsapp.espace.debut"));
        debut.setAttribute("data-dz-wa-espace-debut", "1");
        debut.value = h.debut || "";
        ligne(sH, "whatsapp.espace.debut", debut);
        var finH = el("input", S.champ);
        finH.type = "time";
        finH.setAttribute("aria-label", T("whatsapp.espace.fin"));
        finH.setAttribute("data-dz-wa-espace-fin", "1");
        finH.value = h.fin || "";
        ligne(sH, "whatsapp.espace.fin", finH, "whatsapp.espace.horaires_aide");
        var fuseau = el("input", S.champ);
        fuseau.type = "text";
        fuseau.setAttribute("aria-label", T("whatsapp.espace.fuseau"));
        fuseau.setAttribute("data-dz-wa-espace-fuseau", "1");
        fuseau.value = h.fuseau || "";
        ligne(sH, "whatsapp.espace.fuseau", fuseau);
        var hors = el("textarea", S.zone);
        hors.setAttribute("aria-label", T("whatsapp.espace.hors_horaires"));
        hors.setAttribute("data-dz-wa-espace-hors-horaires", "1");
        hors.value = a.message_hors_horaires || "";
        sH.appendChild(el("span", S.etiquette, T("whatsapp.espace.hors_horaires")));
        sH.appendChild(hors);
        sH.appendChild(el("div", S.note, T("whatsapp.espace.hors_horaires_aide")));
        // — limites et passage à un humain —
        var sL = section("whatsapp.espace.section_limites");
        var plafondJour = el("input", S.champ);
        plafondJour.type = "number";
        plafondJour.setAttribute("aria-label", T("whatsapp.espace.plafond_jour"));
        plafondJour.setAttribute("data-dz-wa-espace-plafond-jour", "1");
        plafondJour.value = String(a.plafond_jour_contact == null ? "" : a.plafond_jour_contact);
        ligne(sL, "whatsapp.espace.plafond_jour", plafondJour);
        var motsH = el("input", S.champ);
        motsH.type = "text";
        motsH.setAttribute("aria-label", T("whatsapp.espace.mots_humain"));
        motsH.setAttribute("data-dz-wa-espace-mots", "1");
        motsH.value = (a.mots_humain || []).join(", ");
        ligne(sL, "whatsapp.espace.mots_humain", motsH, "whatsapp.espace.mots_humain_aide");
        // — validation des posts par le client —
        var sV = section("whatsapp.espace.section_validation");
        var modele = el("select", S.champ);
        modele.setAttribute("aria-label", T("whatsapp.espace.modele_validation"));
        modele.setAttribute("data-dz-wa-espace-modele", "1");
        modele.appendChild(option("", T("whatsapp.espace.modele_aucun")));
        F.optionsModeles = [];
        if (st.modeles) {
          F.optionsModeles = st.modeles.slice();
          if (a.modele_validation && !F.optionsModeles.some(function (m) { return memeModele(m, a.modele_validation); })) {
            F.optionsModeles.unshift({ nom: a.modele_validation.nom, langue: a.modele_validation.langue });
          }
          F.optionsModeles.forEach(function (m, i) { modele.appendChild(option(String(i), m.nom + " (" + m.langue + ")")); });
          var k = -1;
          F.optionsModeles.forEach(function (m, i) { if (memeModele(m, a.modele_validation)) k = i; });
          modele.value = k >= 0 ? String(k) : "";
        } else {
          modele.disabled = true;
          modele.value = "";
        }
        ligne(sV, "whatsapp.espace.modele_validation", modele);
        var noteM = el("div", S.note, st.note || "");
        noteM.setAttribute("data-dz-wa-espace-modele-note", "1");
        sV.appendChild(noteM);
        // — messages de l'espace —
        var sE = section("whatsapp.espace.section_espace");
        var plafondMois = el("input", S.champ);
        plafondMois.type = "number";
        plafondMois.setAttribute("aria-label", T("whatsapp.espace.plafond_mois"));
        plafondMois.setAttribute("data-dz-wa-espace-plafond-mois", "1");
        plafondMois.value = String(r.plafond_mois == null ? "" : r.plafond_mois);
        ligne(sE, "whatsapp.espace.plafond_mois", plafondMois, "whatsapp.espace.plafond_mois_aide");
        var marche = el("input", S.champ);
        marche.type = "text";
        marche.setAttribute("aria-label", T("whatsapp.espace.marche"));
        marche.setAttribute("data-dz-wa-espace-marche", "1");
        marche.value = r.marche_defaut || "";
        ligne(sE, "whatsapp.espace.marche", marche, "whatsapp.espace.marche_aide");
        F.actif = actif; F.mode = mode; F.avert = avert; F.debut = debut; F.fin = finH; F.fuseau = fuseau; F.hors = hors;
        F.plafondJour = plafondJour; F.mots = motsH; F.modele = modele; F.plafondMois = plafondMois; F.marche = marche;
        montrerAvertissement();
      }
      function montrerAvertissement() {
        if (F.avert) F.avert.setAttribute("style", S.alerte + (st.modeChoisi === "auto" ? "" : ";display:none"));
      }
      // le passage en « auto » se confirme ; refusé ou sans boîte de dialogue : retour à « brouillon »
      function confirmerAuto() {
        if (st.autoConfirme || st.modeServeur === "auto") return Promise.resolve(true);
        var d = window.__dzDialogue;
        if (!d || typeof d.confirmer !== "function") {
          erreur.textContent = T("whatsapp.espace.auto_sans_dialogue");
          return Promise.resolve(false);
        }
        st.attente = true;
        return Promise.resolve(d.confirmer(T("whatsapp.espace.auto_avertissement"),
          { titre: T("whatsapp.espace.auto_titre"), ok: T("whatsapp.espace.auto_ok"),
            annuler: T("commun.action.annuler"), danger: true })).then(function (oui) {
          st.attente = false;
          if (oui) st.autoConfirme = true;
          return !!oui;
        }, function () { st.attente = false; return false; });
      }
      function choisirMode(v) {
        if (v !== "auto") { st.modeChoisi = "brouillon"; st.autoConfirme = false; montrerAvertissement(); return; }
        erreur.textContent = "";
        confirmerAuto().then(function (oui) {
          if (fini) return;
          st.modeChoisi = oui ? "auto" : "brouillon";
          if (F.mode) F.mode.value = st.modeChoisi;
          montrerAvertissement();
        });
      }
      function lire() {
        var agent = {
          actif: !!F.actif.checked,
          mode: st.modeChoisi,
          roles: ROLES.filter(function (nom) { return F.roles[nom].checked; }),
          horaires: {
            jours: F.jours.map(function (c, i) { return c.checked ? i : -1; }).filter(function (i) { return i >= 0; }),
            debut: String(F.debut.value || ""), fin: String(F.fin.value || ""), fuseau: String(F.fuseau.value || "").trim()
          },
          message_hors_horaires: String(F.hors.value || ""),
          plafond_jour_contact: entier(F.plafondJour.value),
          mots_humain: mots(F.mots.value)
        };
        if (st.modeles) {
          var m = F.modele.value === "" ? null : F.optionsModeles[Number(F.modele.value)];
          agent.modele_validation = m ? { nom: m.nom, langue: m.langue } : null;
        }
        return { plafond_mois: entier(F.plafondMois.value), marche_defaut: String(F.marche.value || "").trim(), agent: agent };
      }
      function enregistrer() {
        if (st.occupe || fini || !st.reglages) return;
        var corpsPut = lire();
        erreur.textContent = "";
        dire("");
        var pret = corpsPut.agent.mode === "auto" ? confirmerAuto() : Promise.resolve(true);
        pret.then(function (oui) {
          if (fini) return;
          if (!oui) {
            st.modeChoisi = "brouillon";
            if (F.mode) F.mode.value = "brouillon";
            montrerAvertissement();
            return;
          }
          st.occupe = true;
          enregistrerB.disabled = true;
          return envoyer(base, "PUT", corpsPut).then(function (j) {
            if (fini) return;
            st.reglages = j;
            st.modeServeur = st.modeChoisi = (j && j.agent && j.agent.mode) || "brouillon";
            formulaire();
            dire(T("whatsapp.espace.enregistre"));
          }, refus);
        }).then(function () {
          st.occupe = false;
          if (!fini) enregistrerB.disabled = !st.reglages;
        });
      }

      titre();
      document.body.appendChild(voile);
      enregistrerB.focus();
      Promise.all([
        envoyer(base),
        envoyer("/api/espaces?archives=true").catch(function () { return null; }),
        chargerModeles(eid)
      ]).then(function (v) {
        if (fini) return;
        var e = ((v[1] && v[1].espaces) || []).filter(function (x) { return x && x.id === eid; })[0];
        if (e && e.nom) st.nom = e.nom;
        titre();
        st.reglages = v[0];
        st.modeServeur = st.modeChoisi = (v[0] && v[0].agent && v[0].agent.mode) === "auto" ? "auto" : "brouillon";
        st.modeles = v[2].liste;
        st.note = v[2].note;
        formulaire();
        dire("");
        enregistrerB.disabled = false;
      }, function (e) {
        if (fini) return;
        dire("");
        refus(e);
      });
    });
  }

  window.__dzWhatsappEspace = { ouvrir: ouvrir };
})();
