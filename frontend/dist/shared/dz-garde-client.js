/* dz-garde-client.js — le PLANIFICATEUR face aux règles du client (t309, tâche 4, 26/10/2026, plan
   docs/superpowers/plans/2026-10-26-t309-securites-client.md, spec 2026-10-25-boite-a-outils-design.md §5.5).
   SOURCE : frontend/shared/dz-garde-client.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-garde-client.js,
   chargée par frontend/dist/index.html (balise classique après dz-espace-assistant.js : elle s'exécute AVANT le module
   différé de la SPA). Le banc backend/tests/test_garde_client_ecran.py refuse toute dérive et la joue sous node.

   Le serveur refuse de programmer un post de client par un 409 structuré :
     detail = { message (déjà traduit par L10), code : consentement | a_valider | confirmation, client, nom, canaux }.
   Avant t309, D.updateScheduledPost AVALAIT ce refus et l'écran gardait « programmé ». Le maillon de queue
   scripts/patch_bundle_dzgardeclient.py fait passer D.updateScheduledPost par ici (G1) et fait écouter au Planificateur
   « deepotus:schedule-recharger » (G2 : reloadPosts relit la liste du serveur).

   window.__dzGardeClient.patch(id, corps, envoyer) -> Promise<json | null>
     envoyer(corps) -> Promise<Response> : le PATCH d'origine du bundle (même URL, méthode, en-tête).
     - 2xx : rend le json (null s'il est illisible, comme avant) ; si le corps demandait un état (status) et que le
       serveur en a posé un autre (un contenu changé repasse « à valider »), émet « deepotus:schedule-recharger » ;
     - 409 code « confirmation » (corps sans confirme_client) : __dzDialogue.confirmer qui NOMME le client et ses canaux ;
       oui -> renvoie le même corps + confirme_client:<id du client> (une seule fois : un second refus est montré tel
       quel) ; non -> « deepotus:schedule-recharger », null ;
     - autre 409 du client (consentement, a_valider) : __dzDialogue.informer(message du serveur) + rechargement, null ;
     - toute autre réponse ou erreur réseau : null, comme le code d'origine.
     Sans couche de dialogue, rien n'est jamais confirmé par défaut (rechargement, null).
   window.__dzGardeClient.etiquette(statut) -> texte | null : le libellé traduit de « a_valider » (null pour un autre).
   Textes : clés scheduler.etat.a_valider et scheduler.client.* (frontend/shared/i18n/planif_client.json). */
(function () {
  "use strict";
  if (window.__dzGardeClient) return;

  var CODES = { consentement: 1, a_valider: 1, confirmation: 1 };
  var RECHARGER = "deepotus:schedule-recharger";

  function T(cle, vars) { return typeof window.dzT === "function" ? window.dzT(cle, vars) : cle; }

  function recharger() {
    try { window.dispatchEvent(new CustomEvent(RECHARGER)); } catch (e) { /* rien : l'écran garde son état */ }
  }

  function lireJson(r) {
    try { return Promise.resolve(r.json()).then(null, function () { return null; }); }
    catch (e) { return Promise.resolve(null); }
  }

  function refusClient(j) {
    var d = j && j.detail;
    return d && typeof d === "object" && !Array.isArray(d) && CODES[d.code] ? d : null;
  }

  function canauxTexte(c) {
    return (Array.isArray(c) ? c : []).map(function (x) { return String(x); }).join(", ");
  }

  function dialogue() { return window.__dzDialogue || null; }

  function informer(message) {
    var d = dialogue();
    try { if (d && message) d.informer(String(message)); } catch (e) { /* le rechargement suffit */ }
  }

  function patch(id, corps, envoyer) {
    var demande = corps && typeof corps === "object" && "status" in corps ? corps.status : undefined;
    var envoi;
    try { envoi = Promise.resolve(envoyer(corps)); } catch (e) { return Promise.resolve(null); }
    return envoi.then(function (r) {
      if (!r) return null;
      if (r.ok) {
        return lireJson(r).then(function (j) {
          if (j && demande !== undefined && j.status && j.status !== demande) recharger();
          return j;
        });
      }
      if (r.status !== 409) return null;
      return lireJson(r).then(function (j) {
        var refus = refusClient(j);
        if (!refus) return null;
        if (refus.code === "confirmation" && !(corps && corps.confirme_client)) {
          var d = dialogue();
          if (!d || typeof d.confirmer !== "function") { recharger(); return null; }
          return Promise.resolve(d.confirmer(T("scheduler.client.confirmer", { nom: refus.nom || refus.client || "",
                                                                           canaux: canauxTexte(refus.canaux) }),
            { titre: T("scheduler.client.confirmer_titre"), ok: T("scheduler.client.confirmer_ok") }))
            .then(function (oui) {
              if (!oui) { recharger(); return null; }
              var suite = {};
              for (var k in corps) if (Object.prototype.hasOwnProperty.call(corps, k)) suite[k] = corps[k];
              suite.confirme_client = refus.client;
              return patch(id, suite, envoyer);
            }, function () { recharger(); return null; });
        }
        informer(refus.message);
        recharger();
        return null;
      });
    }, function () { return null; });
  }

  function etiquette(statut) {
    return statut === "a_valider" ? T("scheduler.etat.a_valider") : null;
  }

  window.__dzGardeClient = { patch: patch, etiquette: etiquette };
})();
