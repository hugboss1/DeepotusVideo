/* dz-espace-assistant.js — l'ASSISTANT de création d'un espace, en quatre temps (t308, tâche 4, 26/10/2026, plan
   docs/superpowers/plans/2026-10-26-t308-assistant-espace.md, spec 2026-10-25-boite-a-outils-design.md §5.3).
   SOURCE : frontend/shared/dz-espace-assistant.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-espace-assistant.js,
   chargée par frontend/dist/index.html (balise classique après dz-projet-canaux.js : elle s'exécute AVANT le module
   différé de la SPA). Le banc backend/tests/test_espace_assistant_ecran.py refuse toute dérive et joue l'assistant sous
   node (faux DOM, faux fetch).

   window.__dzEspaceAssistant.ouvrir(opts?) -> Promise<id | null>
     opts : { nom, couleur } préremplis (le formulaire de Réglages › Espaces les passe). Une boîte (charte de dialogue.js :
     angles vifs, en-tête IBM Plex Mono en capitales) avec un fil d'étapes, Précédent / Suivant :
     1. Type et identité : nom, couleur, kit (vide = suit le kit de Réglages › Identité visuelle), type (marque, produit,
        client), parent (produit seulement : les marques et les clients). « Suivant » CRÉE l'espace (POST /api/espaces)
        UNE seule fois — un second clic pendant l'envoi est ignoré ; au retour, il le MODIFIE (POST /api/espaces/{id}).
     2. Fiche (client seulement, sinon sautée) : société, contact, pays, langue, mode de publication -> PUT …/client.
     3. Canaux : une case par plateforme (GET /api/comptes?espace=<id> -> plateformes). Pour une plateforme cochée, ses
        champs : un champ SECRET est en type mot de passe et n'est JAMAIS prérempli (ni depuis une réponse, ni après
        écriture) ; « Connecter » pour OAuth (/api/oauth/<p>/start?compte=<id>, comme DzComptesEspace) ; « Vérifier »
        écrit la saisie (POST /api/comptes ou /api/comptes/{id}) puis POST /api/comptes/{id}/verifier, sans rien
        publier, et montre la pastille et la date. À l'écran : la traduction du CODE de la vérification ; la raison
        brute (française) n'est qu'au survol. « Suivant » enregistre les plateformes cochées, vérifiées ou non.
     4. Récapitulatif (GET /api/espaces/{id}/recapitulatif) : canaux et état, mode de publication, consentements
        manquants. « Terminer » active l'espace (POST …/activate), émet « deepotus:espace-refresh »,
        « deepotus:brand-refresh » puis « dz-espace-cree » (detail = id), ferme et rend l'id.
     Annuler ou Échap : la boîte se ferme ; la promesse rend l'id si l'espace a déjà été créé (la liste se relit), sinon
     null. Un clic sur le voile ne ferme PAS (il perdrait la saisie).
   pastille(vue) : la pastille d'état d'un compte (vue.verification) ou d'un canal du récapitulatif (vue.etat,
     vue.verifie_le) ; fonction interne ici, à exposer telle quelle (tâche 5). Glyphes Deepotus (dz-etat-*), jamais
     d'emoji ; données utilisateur par textContent. Textes : clés espaces.assistant.* (frontend/shared/i18n/espaces.json).
   Le maillon de queue scripts/patch_bundle_dzassistant.py branche « Créer l'espace » de Réglages › Espaces ici. */
(function () {
  "use strict";
  if (window.__dzEspaceAssistant) return;

  var JSON_H = { "Content-Type": "application/json" };
  var GLYPHES = { x: "dz-reseau-x", telegram: "dz-reseau-telegram", youtube: "dz-reseau-youtube",
                  instagram: "dz-reseau-instagram", tiktok: "dz-reseau-tiktok" };
  var ETATS = {
    vert: ["dz-etat-succes", "var(--green,#2fbf71)"],
    orange: ["dz-etat-avertissement", "var(--amber,#f0b429)"],
    rouge: ["dz-etat-erreur", "var(--red,#e5484d)"],
    non_verifie: ["dz-etat-inconnu", "var(--txt-mid,var(--ink-muted,#9aa4ae))"]
  };
  var TYPES = ["marque", "produit", "client"];
  var MODES = ["valide_par_client", "publie_en_son_nom"];
  var S = {
    voile: "position:fixed;inset:0;z-index:9998;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center",
    boite: "width:600px;max-width:94vw;max-height:86vh;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    fil: "display:flex;gap:0;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830))",
    filPas: "flex:1;padding:7px 10px;font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae));border-right:1px solid var(--brd-soft,var(--stroke,#222830))",
    filCourant: ";color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:inset 0 -2px 0 var(--accent,#2b6fd6)",
    filSans: ";opacity:.45",
    corps: "padding:12px 14px;overflow-y:auto;display:flex;flex-direction:column;gap:10px;color:var(--txt-base,var(--ink,#cfd6e2));min-height:220px",
    note: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    grille: "display:grid;grid-template-columns:minmax(150px,auto) 1fr;gap:6px 10px;align-items:center",
    etiquette: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    cle: "font-size:11px;font-family:var(--f-mono,'IBM Plex Mono',monospace);color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    champ: "font:inherit;font-size:12px;padding:5px 8px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));color:var(--txt-hi,var(--ink-strong,#e6e9ee));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138))",
    couleur: "width:40px;height:28px;padding:0;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));border-radius:0;background:none",
    plat: "display:flex;flex-direction:column;gap:8px;padding:8px 10px;border:1px solid var(--brd-soft,var(--stroke,#222830));border-radius:0",
    ligne: "display:flex;align-items:center;gap:8px;flex-wrap:wrap",
    glyphe: "display:inline-flex;width:16px;height:16px;color:var(--txt-hi,var(--ink-strong,#e6e9ee))",
    pastille: "display:inline-flex;align-items:center;gap:4px;font-size:11px;padding:1px 6px;border:1px solid currentColor;border-radius:0",
    pastilleGlyphe: "display:inline-flex;width:12px;height:12px",
    detail: "font-size:11px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    alerte: "font-size:11.5px;color:var(--amber,#f0b429)",
    erreur: "font-size:12px;color:var(--red,#e5484d);padding:0 14px 8px",
    pied: "display:flex;gap:8px;justify-content:flex-end;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
    btn: "min-width:88px;height:28px;padding:0 12px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit",
    petit: "height:24px;padding:0 10px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit;font-size:11.5px",
    ok: ";background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6);color:var(--accent-ink,#ffffff)",
    cache: ";display:none"
  };
  var courant = null;

  function T(cle, vars) { return typeof window.dzT === "function" ? window.dzT(cle, vars) : cle; }
  function icone(cle, taille) { return typeof window.dzIcone === "function" ? window.dzIcone(cle, { taille: taille || 16 }) : ""; }
  function glyphe(plateforme) { return GLYPHES[plateforme] || "dz-action-publier"; }
  function quand(iso) { return iso ? String(iso).replace("T", " ").slice(0, 16) : ""; }

  function el(tag, style, texte) {
    var n = document.createElement(tag);
    if (style) n.setAttribute("style", style);
    if (texte != null) n.textContent = texte;
    return n;
  }

  function envoyer(url, methode, corps) {
    var o = { method: methode || "GET" };
    if (corps !== undefined) { o.headers = JSON_H; o.body = JSON.stringify(corps); }
    return fetch(url, o).then(function (R) {
      return R.json().catch(function () { return {}; }).then(function (j) {
        if (!R.ok) throw new Error(j && j.detail ? String(j.detail) : "HTTP " + R.status);
        return j;
      });
    });
  }

  // ── la pastille d'état : un compte (vue.verification) ou un canal du récapitulatif (vue.etat, vue.verifie_le) ──
  function etatDe(vue) {
    var v = vue && vue.verification;
    if (v && ETATS[v.etat]) return { etat: v.etat, code: v.code || "", raison: v.raison || "", date: v.date || "" };
    if (vue && ETATS[vue.etat] && vue.etat !== "non_verifie") return { etat: vue.etat, code: "", raison: "", date: vue.verifie_le || "" };
    return { etat: "non_verifie", code: "", raison: "", date: "" };
  }
  function pastille(vue) {
    var v = etatDe(vue), e = ETATS[v.etat];
    var n = el("span", S.pastille + ";color:" + e[1]);
    n.setAttribute("data-etat", v.etat);
    var g = el("span", S.pastilleGlyphe);
    g.innerHTML = icone(e[0], 12);
    n.appendChild(g);
    n.appendChild(el("span", "", T("espaces.assistant.etat_" + v.etat)));
    // la raison BRUTE (française, du serveur) n'est qu'au survol ; l'écran montre la traduction du code
    n.setAttribute("title", v.etat === "non_verifie" ? T("espaces.assistant.etat_non_verifie")
      : T("espaces.assistant.survol", { date: quand(v.date), raison: v.raison || T("espaces.assistant.etat_" + v.etat) }));
    return n;
  }
  function detail(vue) {
    var v = etatDe(vue);
    if (v.etat === "non_verifie" || !v.code) return "";
    return T("espaces.assistant.detail", { code: T("espaces.assistant.code_" + v.code), date: quand(v.date) });
  }

  function ouvrir(opts) {
    opts = opts || {};
    if (courant) courant(null);
    return new Promise(function (resoudre) {
      var st = {
        etape: 1, id: null, nom: String(opts.nom || ""), couleur: /^#[0-9a-fA-F]{6}$/.test(opts.couleur || "") ? opts.couleur : "#3b82f6",
        kit: "", type: "marque", parent: "", espaces: [], kits: [],
        fiche: { societe: "", contact_nom: "", contact_email: "", contact_whatsapp: "", pays: "", langue: "fr", mode: MODES[0] },
        plats: null, comptes: {}, coches: {}, saisies: {}, msgs: {}, recap: null
      };
      var voile = el("div", S.voile);
      voile.setAttribute("role", "dialog");
      voile.setAttribute("aria-modal", "true");
      voile.setAttribute("data-dz-assistant", "1");
      voile.className = "dz-dialogue dz-espace-assistant";
      var titre = T("espaces.assistant.titre");
      voile.setAttribute("aria-label", titre);
      var boite = el("div", S.boite);
      var tete = el("div", S.tete, titre);
      var fil = el("div", S.fil);
      var pas = ["espaces.assistant.etape_identite", "espaces.assistant.etape_fiche", "espaces.assistant.etape_canaux",
                 "espaces.assistant.etape_recap"].map(function (k, i) {
        var p = el("span", S.filPas, T(k));
        p.setAttribute("data-dz-assistant-fil", String(i + 1));
        fil.appendChild(p);
        return p;
      });
      var corps = el("div", S.corps);
      var erreur = el("div", S.erreur, "");
      erreur.setAttribute("role", "alert");
      erreur.setAttribute("data-dz-assistant-erreur", "1");
      var pied = el("div", S.pied);
      var annuler = el("button", S.btn);
      annuler.textContent = T("commun.action.annuler");
      annuler.type = "button";
      annuler.setAttribute("data-dz-assistant-annuler", "1");
      var precedent = el("button", S.btn);
      precedent.textContent = T("commun.action.precedent");
      precedent.type = "button";
      precedent.setAttribute("data-dz-assistant-precedent", "1");
      var suivant = el("button", S.btn + S.ok);
      suivant.textContent = T("commun.action.suivant");
      suivant.type = "button";
      suivant.setAttribute("data-dz-assistant-suivant", "1");
      var terminer = el("button", S.btn + S.ok);
      terminer.textContent = T("espaces.assistant.terminer");
      terminer.setAttribute("title", T("espaces.assistant.terminer_aide"));
      terminer.type = "button";
      terminer.setAttribute("data-dz-assistant-terminer", "1");
      pied.appendChild(annuler);
      pied.appendChild(precedent);
      pied.appendChild(suivant);
      pied.appendChild(terminer);
      boite.appendChild(tete);
      boite.appendChild(fil);
      boite.appendChild(corps);
      boite.appendChild(erreur);
      boite.appendChild(pied);
      voile.appendChild(boite);

      var fini = false, occupe = false;
      function fin(valeur) {
        if (fini) return;
        fini = true;
        if (courant === fermer) courant = null;
        document.removeEventListener("keydown", surTouche, true);
        voile.remove();
        resoudre(valeur || null);
      }
      function surTouche(ev) {
        if (ev.key === "Escape") { ev.preventDefault(); fin(st.id); }
      }
      function fermer() { fin(st.id); }
      courant = fermer;
      annuler.addEventListener("click", function () { fin(st.id); });
      document.addEventListener("keydown", surTouche, true);

      function dire(texte) { erreur.textContent = texte || ""; }
      function echec(e) { return T("espaces.assistant.erreur", { detail: String(e && e.message || e) }); }
      function boutons() {
        precedent.setAttribute("style", S.btn + (st.etape > 1 ? "" : S.cache));
        suivant.setAttribute("style", S.btn + S.ok + (st.etape < 4 ? "" : S.cache));
        terminer.setAttribute("style", S.btn + S.ok + (st.etape === 4 ? "" : S.cache));
        precedent.disabled = suivant.disabled = terminer.disabled = occupe;
      }
      function etiquette(texte, controle) {
        var l = el("label", S.etiquette, texte);
        return [l, controle];
      }
      function grille(lignes) {
        var g = el("div", S.grille);
        lignes.forEach(function (paire) { g.appendChild(paire[0]); g.appendChild(paire[1]); });
        return g;
      }
      function option(sel, valeur, texte, brut) {
        var o = el("option", "", texte);
        o.value = valeur;
        if (brut) o.setAttribute("data-dz-brut", "1");
        sel.appendChild(o);
        return o;
      }

      // ── 1. type et identité ──
      function etape1() {
        corps.appendChild(el("div", S.note, T("espaces.assistant.aide_identite")));
        var nom = el("input", S.champ);
        nom.setAttribute("aria-label", T("espaces.nouveau.nom"));
        nom.setAttribute("data-dz-assistant-champ", "nom");
        nom.maxLength = 60;
        nom.value = st.nom;
        nom.addEventListener("input", function () { st.nom = nom.value; dire(""); });
        var couleur = el("input", S.couleur);
        couleur.type = "color";
        couleur.setAttribute("aria-label", T("espaces.nouveau.couleur"));
        couleur.setAttribute("data-dz-assistant-champ", "couleur");
        couleur.value = st.couleur;
        couleur.addEventListener("input", function () { st.couleur = couleur.value; });
        var kit = el("select", S.champ);
        kit.setAttribute("aria-label", T("espaces.champ.kit"));
        kit.setAttribute("data-dz-assistant-champ", "kit");
        option(kit, "", T("espaces.champ.kit_branding"));
        st.kits.forEach(function (k) { option(kit, k.id, k.name || k.id, true); });
        kit.value = st.kit;
        kit.addEventListener("change", function () { st.kit = kit.value; });
        var type = el("select", S.champ);
        type.setAttribute("aria-label", T("espaces.assistant.type"));
        type.setAttribute("data-dz-assistant-champ", "type");
        TYPES.forEach(function (t) { option(type, t, T("espaces.assistant.type_" + t)); });
        type.value = st.type;
        type.addEventListener("change", function () {
          st.type = type.value;
          if (st.type !== "produit") st.parent = "";
          rendre();
        });
        var lignes = [etiquette(T("espaces.nouveau.nom"), nom), etiquette(T("espaces.nouveau.couleur"), couleur),
                      etiquette(T("espaces.champ.kit"), kit), etiquette(T("espaces.assistant.type"), type)];
        if (st.type === "produit") {
          var parent = el("select", S.champ);
          parent.setAttribute("aria-label", T("espaces.assistant.parent"));
          parent.setAttribute("data-dz-assistant-champ", "parent");
          option(parent, "", T("espaces.assistant.parent_aucun")).setAttribute("data-dz-assistant-parent-option", "");
          st.espaces.filter(function (e) {
            return e.id !== st.id && !e.archive && (e.type === "marque" || e.type === "client");
          }).forEach(function (e) {
            option(parent, e.id, e.nom || e.id, true).setAttribute("data-dz-assistant-parent-option", e.id);
          });
          parent.value = st.parent;
          parent.addEventListener("change", function () { st.parent = parent.value; });
          lignes.push(etiquette(T("espaces.assistant.parent"), parent));
        }
        corps.appendChild(grille(lignes));
      }
      function valider1() {
        if (!st.nom.trim()) { dire(T("espaces.assistant.nom_requis")); return Promise.resolve(false); }
        var c = { nom: st.nom.trim(), couleur: st.couleur, kit_id: st.kit, type: st.type,
                  parent: st.type === "produit" && st.parent ? st.parent : null };
        var url = st.id ? "/api/espaces/" + encodeURIComponent(st.id) : "/api/espaces";
        return envoyer(url, "POST", c).then(function (j) {
          st.id = (j && j.espace && j.espace.id) || st.id;
          return !!st.id;
        });
      }

      // ── 2. la fiche du client ──
      function etape2() {
        corps.appendChild(el("div", S.note, T("espaces.assistant.aide_fiche")));
        var f = st.fiche, lignes = [];
        [["societe", 200, "espaces.assistant.societe"], ["contact_nom", 200, "espaces.assistant.contact_nom"],
         ["contact_email", 200, "espaces.assistant.contact_email"], ["contact_whatsapp", 40, "espaces.assistant.contact_whatsapp"],
         ["pays", 2, "espaces.assistant.pays"]].forEach(function (d) {
          var n = el("input", S.champ);
          n.setAttribute("aria-label", T(d[2]));
          n.setAttribute("data-dz-assistant-champ", d[0]);
          n.maxLength = d[1];
          n.value = f[d[0]];
          n.addEventListener("input", function () { f[d[0]] = n.value; });
          lignes.push(etiquette(T(d[2]), n));
        });
        var langue = el("select", S.champ);
        langue.setAttribute("aria-label", T("espaces.assistant.langue"));
        langue.setAttribute("data-dz-assistant-champ", "langue");
        option(langue, "fr", T("espaces.assistant.langue_fr"));
        option(langue, "en", T("espaces.assistant.langue_en"));
        langue.value = f.langue;
        langue.addEventListener("change", function () { f.langue = langue.value; });
        lignes.push(etiquette(T("espaces.assistant.langue"), langue));
        var mode = el("select", S.champ);
        mode.setAttribute("aria-label", T("espaces.assistant.mode"));
        mode.setAttribute("data-dz-assistant-champ", "mode");
        MODES.forEach(function (m) { option(mode, m, T("espaces.assistant.mode_" + m)); });
        mode.value = f.mode;
        mode.addEventListener("change", function () { f.mode = mode.value; });
        lignes.push(etiquette(T("espaces.assistant.mode"), mode));
        corps.appendChild(grille(lignes));
      }
      function valider2() {
        var f = st.fiche;
        return envoyer("/api/espaces/" + encodeURIComponent(st.id) + "/client", "PUT", {
          societe: f.societe.trim(), contact: { nom: f.contact_nom.trim(), email: f.contact_email.trim(),
                                                whatsapp: f.contact_whatsapp.trim() },
          pays: f.pays.trim().toUpperCase(), langue: f.langue, mode_publication: f.mode
        }).then(function () { return true; });
      }

      // ── 3. les canaux ──
      function chargerCanaux() {
        envoyer("/api/comptes?espace=" + encodeURIComponent(st.id)).then(function (j) {
          st.plats = (j && j.plateformes) || {};
          ((j && j.comptes) || []).forEach(function (c) {
            if (!c || c.espace_id !== st.id || c.historique || st.comptes[c.plateforme]) return;
            st.comptes[c.plateforme] = c;
            st.coches[c.plateforme] = true;
          });
          if (!fini && st.etape === 3) rendre();
        }, function (e) { dire(echec(e)); });
      }
      function ecrireCompte(p) {
        var v = {}, s = st.saisies[p] || {};
        Object.keys(s).forEach(function (k) { if (s[k] !== "" && s[k] != null) v[k] = s[k]; });
        var a = Object.keys(v).length > 0, c = st.comptes[p];
        var envoi = !c ? envoyer("/api/comptes", "POST", a ? { espace_id: st.id, plateforme: p, valeurs: v } : { espace_id: st.id, plateforme: p })
          : a ? envoyer("/api/comptes/" + encodeURIComponent(c.id), "POST", { valeurs: v }) : null;
        if (!envoi) return Promise.resolve(c);
        return envoi.then(function (j) {
          st.comptes[p] = j.compte;
          st.saisies[p] = {};          // un secret écrit n'est jamais relu : le champ revient vide
          return j.compte;
        });
      }
      function verifier(p) {
        st.msgs[p] = T("espaces.assistant.verif_en_cours");
        rendre();
        ecrireCompte(p).then(function (c) {
          return envoyer("/api/comptes/" + encodeURIComponent(c.id) + "/verifier", "POST");
        }).then(function (j) {
          st.comptes[p] = j.compte;
          st.msgs[p] = "";
        }, function (e) {
          st.msgs[p] = echec(e);
        }).then(function () { if (!fini) rendre(); });
      }
      function connecter(p) {
        var w = null;
        try { w = window.open("", "_blank"); } catch (e) { /* bloqueur */ }
        ecrireCompte(p).then(function (c) {
          var u = "/api/oauth/" + p + "/start?compte=" + encodeURIComponent(c.id);
          return fetch(u, { redirect: "manual" }).then(function (R) {
            if (R.type === "opaqueredirect" || R.status === 302) {
              if (w) w.location = u; else window.open(u, "_blank");
              st.msgs[p] = T("espaces.comptes.connexion_ouverte");
              return;
            }
            if (w) w.close();
            return R.json().catch(function () { return {}; }).then(function (j) {
              st.msgs[p] = echec(j && j.detail || "HTTP " + R.status);
            });
          });
        }).catch(function (e) { if (w) w.close(); st.msgs[p] = echec(e); }).then(function () { if (!fini) rendre(); });
      }
      function champsDe(p) {
        var plat = st.plats[p], c = st.comptes[p], s = st.saisies[p] = st.saisies[p] || {};
        var vus = {};
        ((c && c.champs) || []).forEach(function (f) { vus[f.nom] = f; });
        var lignes = [];
        (plat.champs || []).forEach(function (f) {
          var vu = vus[f.nom] || {}, n;
          if (f.nom === "TIKTOK_AUDITED") {
            n = el("input");
            n.type = "checkbox";
            n.checked = s[f.nom] != null ? !!s[f.nom] : !!vu.valeur;
            n.addEventListener("change", function () { s[f.nom] = n.checked; });
          } else {
            n = el("input", S.champ);
            n.type = f.secret ? "password" : "text";
            n.autocomplete = "off";
            // un champ SECRET ne reprend jamais une valeur venue du serveur : seulement ce qui vient d'être tapé
            n.value = s[f.nom] != null ? s[f.nom] : f.secret ? "" : String(vu.valeur || "");
            if (f.secret && vu.pose) n.placeholder = T("espaces.comptes.pose");
            n.addEventListener("input", function () { s[f.nom] = n.value; });
          }
          n.setAttribute("aria-label", f.nom);
          n.setAttribute("data-dz-assistant-cle", f.nom);
          lignes.push([el("label", S.cle, f.nom), n]);
        });
        return grille(lignes);
      }
      function etape3() {
        corps.appendChild(el("div", S.note, T("espaces.assistant.aide_canaux")));
        if (!st.plats) { corps.appendChild(el("div", S.note, T("espaces.assistant.chargement"))); return; }
        Object.keys(st.plats).forEach(function (p) {
          var plat = st.plats[p], c = st.comptes[p];
          var bloc = el("div", S.plat);
          bloc.setAttribute("data-dz-assistant-plateforme", p);
          var tete3 = el("label", S.ligne);
          var caseP = el("input");
          caseP.type = "checkbox";
          caseP.checked = !!st.coches[p];
          caseP.disabled = !!c;           // un compte déjà créé se supprime dans Réglages › Espaces (deux clics)
          caseP.setAttribute("data-dz-assistant-case", p);
          caseP.setAttribute("aria-label", plat.libelle || p);
          caseP.addEventListener("change", function () {
            st.coches[p] = caseP.checked;
            if (!caseP.checked) st.saisies[p] = {};
            rendre();
          });
          var g = el("span", S.glyphe);
          g.setAttribute("data-dz-glyphe", glyphe(p));
          g.innerHTML = icone(glyphe(p));
          tete3.appendChild(caseP);
          tete3.appendChild(g);
          tete3.appendChild(el("strong", "", plat.libelle || p));
          bloc.appendChild(tete3);
          if (st.coches[p]) {
            bloc.appendChild(champsDe(p));
            var actions = el("div", S.ligne);
            if (plat.oauth) {
              var co = el("button", S.petit);
              co.textContent = T("espaces.comptes.connecter");
              co.type = "button";
              co.setAttribute("data-dz-assistant-connecter", p);
              co.addEventListener("click", function () { connecter(p); });
              actions.appendChild(co);
            }
            var ve = el("button", S.petit);
            ve.textContent = T("espaces.assistant.verifier");
            ve.setAttribute("title", T("espaces.assistant.verifier_aide"));
            ve.type = "button";
            ve.setAttribute("data-dz-assistant-verifier", p);
            ve.addEventListener("click", function () { verifier(p); });
            actions.appendChild(ve);
            var pa = pastille(c);
            pa.setAttribute("data-dz-assistant-pastille", p);
            actions.appendChild(pa);
            var de = el("span", S.detail, detail(c));
            de.setAttribute("data-dz-assistant-detail", p);
            actions.appendChild(de);
            bloc.appendChild(actions);
            if (st.msgs[p]) {
              var m = el("div", S.detail, st.msgs[p]);
              m.setAttribute("role", "status");
              bloc.appendChild(m);
            }
          }
          corps.appendChild(bloc);
        });
      }
      function valider3() {
        var faits = Promise.resolve();
        Object.keys(st.plats || {}).forEach(function (p) {
          if (st.coches[p]) faits = faits.then(function () { return ecrireCompte(p); });
        });
        return faits.then(function () { st.recap = null; return true; });
      }

      // ── 4. le récapitulatif ──
      function chargerRecap() {
        envoyer("/api/espaces/" + encodeURIComponent(st.id) + "/recapitulatif").then(function (j) {
          st.recap = j;
          if (!fini && st.etape === 4) rendre();
        }, function (e) { dire(echec(e)); });
      }
      function etape4() {
        var r = st.recap;
        if (!r) { corps.appendChild(el("div", S.note, T("espaces.assistant.chargement"))); return; }
        if (r.mode_publication && MODES.indexOf(r.mode_publication) >= 0) {
          var mo = el("div", "", T("espaces.assistant.recap_mode", { mode: T("espaces.assistant.mode_" + r.mode_publication) }));
          mo.setAttribute("data-dz-assistant-mode", "1");
          corps.appendChild(mo);
        }
        if (!(r.canaux || []).length) corps.appendChild(el("div", S.note, T("espaces.assistant.recap_aucun_canal")));
        (r.canaux || []).forEach(function (c) {
          var bloc = el("div", S.plat);
          bloc.setAttribute("data-dz-assistant-recap-canal", c.compte);
          var l = el("div", S.ligne);
          var g = el("span", S.glyphe);
          g.setAttribute("data-dz-glyphe", glyphe(c.plateforme));
          g.innerHTML = icone(glyphe(c.plateforme));
          l.appendChild(g);
          var nom = el("strong", "", c.libelle || c.compte);
          nom.setAttribute("data-dz-brut", "1");
          l.appendChild(nom);
          var pa = pastille(c);
          pa.setAttribute("data-dz-assistant-pastille", c.compte);
          l.appendChild(pa);
          bloc.appendChild(l);
          if (c.consentement === "manquant" || c.consentement === "en_cours") {
            var co = el("div", c.consentement === "manquant" ? S.alerte : S.detail,
              T(c.consentement === "manquant" ? "espaces.assistant.consentement_manquant" : "espaces.assistant.consentement_en_cours"));
            co.setAttribute("data-dz-assistant-consentement", c.compte);
            bloc.appendChild(co);
          }
          corps.appendChild(bloc);
        });
        var ma = r.manques || {};
        var mq = el("div", S.note, T("espaces.assistant.manques", { non_verifies: ma.non_verifies || 0, consentements: ma.consentements || 0 }));
        mq.setAttribute("data-dz-assistant-manques", "1");
        corps.appendChild(mq);
      }
      function terminerTout() {
        if (occupe || fini || !st.id) return;
        occupe = true;
        boutons();
        dire("");
        envoyer("/api/espaces/" + encodeURIComponent(st.id) + "/activate", "POST").then(function () {
          occupe = false;
          try {
            window.dispatchEvent(new Event("deepotus:espace-refresh"));
            window.dispatchEvent(new Event("deepotus:brand-refresh"));
            window.dispatchEvent(new CustomEvent("dz-espace-cree", { detail: st.id }));
          } catch (e) { /* vieux moteur */ }
          fin(st.id);
        }, function (e) { occupe = false; dire(echec(e)); boutons(); });
      }

      function rendre() {
        corps.textContent = "";
        pas.forEach(function (p, i) {
          var n = i + 1, sans = n === 2 && st.type !== "client";
          p.setAttribute("style", S.filPas + (n === st.etape ? S.filCourant : "") + (sans ? S.filSans : ""));
          if (n === st.etape) p.setAttribute("aria-current", "step"); else p.removeAttribute("aria-current");
          if (sans) p.setAttribute("title", T("espaces.assistant.etape_sans_objet")); else p.removeAttribute("title");
        });
        voile.setAttribute("data-etape", String(st.etape));
        [etape1, etape2, etape3, etape4][st.etape - 1]();
        boutons();
      }
      function aller(n) {
        st.etape = n;
        dire("");
        if (n === 3 && !st.plats) chargerCanaux();
        if (n === 4 && !st.recap) chargerRecap();
        rendre();
      }
      suivant.addEventListener("click", function () {
        if (occupe || fini) return;
        occupe = true;
        boutons();
        dire("");
        var p = [valider1, valider2, valider3][st.etape - 1];
        (p ? p() : Promise.resolve(false)).then(function (bon) {
          occupe = false;
          if (fini) return;
          if (!bon) { boutons(); return; }
          var n = st.etape + 1;
          if (n === 2 && st.type !== "client") n = 3;
          aller(n);
        }, function (e) { occupe = false; dire(echec(e)); boutons(); });
      });
      precedent.addEventListener("click", function () {
        if (occupe || fini || st.etape <= 1) return;
        var n = st.etape - 1;
        if (n === 2 && st.type !== "client") n = 1;
        aller(n);
      });
      terminer.addEventListener("click", terminerTout);

      Promise.all([
        envoyer("/api/espaces").then(function (j) { st.espaces = (j && j.espaces) || []; }, function () { /* liste vide */ }),
        envoyer("/api/brand-kits").then(function (j) { st.kits = (j && j.kits) || []; }, function () { /* kit de Branding */ })
      ]).then(function () { if (!fini && st.etape === 1) rendre(); });

      rendre();
      document.body.appendChild(voile);
    });
  }

  window.__dzEspaceAssistant = { ouvrir: ouvrir };
})();
