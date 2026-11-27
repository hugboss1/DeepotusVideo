/* dz-ig-relier.js — Réglages › Comptes connectés › Instagram : « Relier par Instagram » (t493, 26/11/2026).
   SOURCE : frontend/shared/dz-ig-relier.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-ig-relier.js, servie à
   /shared/dz-ig-relier.js, chargée par une balise classique dans la SPA (frontend/dist/index.html). Le bouton est posé
   par le maillon de queue scripts/patch_bundle_dziglogin.py, qui rend un <span data-dz-ig-relier-hote> dans le bloc
   Instagram (à côté de « Vérifier » et du lien « Guide ») et appelle window.__dzIgRelier.monter par une ref ; le même
   maillon ajoute au bloc les champs IG_APP_ID, IG_APP_SECRET, IG_OAUTH_REDIRECT (enregistrés comme les autres).
   Serveur : backend/app/services/instagram_oauth.py, routes /api/oauth/instagram (instagram_oauth_routes.py).
   Banc : backend/tests/test_instagram_oauth_t493.py.

   Le panneau : l'état (application prête ? coffre ouvert ?), le compte à relier (Deepotus ou un compte d'espace),
   l'adresse de retour à déclarer chez Meta, « Ouvrir l'autorisation Instagram » (POST /demarrer -> nouvel onglet), le
   champ où coller l'adresse de retour (POST /retour) et le rappel du collage manuel, qui reste possible. Aucun secret
   n.arrive ici. Vanilla DOM (createElement et textContent seulement) ; textes : clés igrelier.* (frontend/shared/i18n/igrelier.json). */
(function () {
  "use strict";
  if (window.__dzIgRelier) return;

  var BASE = "/api/oauth/instagram";
  var JSON_H = { "Content-Type": "application/json" };
  var S = {
    voile: "position:fixed;inset:0;z-index:9000;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;padding:16px",
    panneau: "width:min(620px,100%);max-height:90vh;overflow:auto;display:flex;flex-direction:column;gap:10px;padding:16px 18px;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));background:var(--srf-panel,var(--bg-panel,#13171c));color:var(--txt-base,var(--ink,#cfd6e2));font:13px/1.5 system-ui,sans-serif",
    titre: "font:600 16px/1.3 system-ui,sans-serif;color:var(--txt-hi,var(--ink-strong,#e6e9ee))",
    note: "font-size:12px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    lib: "font-size:12px;color:var(--txt-hi,var(--ink-strong,#e6e9ee))",
    champ: "width:100%;box-sizing:border-box;height:28px;padding:0 9px;background:var(--srf-sunken,var(--bg-base,#0d1014));border:1px solid var(--brd-soft,var(--stroke,#222830));border-radius:0;color:var(--txt-hi,var(--ink-strong,#e6e9ee));font:11.5px 'IBM Plex Mono',monospace",
    ligne: "display:flex;align-items:center;gap:8px;flex-wrap:wrap",
    btn: "height:28px;padding:0 12px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit;display:inline-flex;align-items:center;gap:6px",
    petit: "height:26px;padding:0 10px;border-radius:0;background:transparent;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:12px system-ui,sans-serif;white-space:nowrap",
    primaire: "background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6);color:var(--accent-ink,#ffffff)",
    ok: "font-size:12px;color:var(--green,#3fb950)",
    ko: "font-size:12px;color:var(--red,#e5484d)",
    attente: "font-size:12px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))"
  };

  function T(cle, v) { return typeof window.dzT === "function" ? window.dzT(cle, v) : cle; }
  function el(tag, attrs, texte) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (texte != null) n.textContent = texte;
    return n;
  }
  async function appel(chemin, corps) {
    var r = await window.fetch(BASE + chemin, corps ? { method: "POST", headers: JSON_H, body: JSON.stringify(corps) } : {});
    var j = null;
    try { j = await r.json(); } catch (e) { j = null; }
    if (!r.ok) throw new Error((j && (j.detail || j.message)) || String(r.status));
    return j || {};
  }
  function dire(zone, ok, texte) {
    zone.setAttribute("data-dz-ig-verdict", ok === true ? "ok" : ok === false ? "refus" : "attente");
    zone.setAttribute("style", ok === true ? S.ok : ok === false ? S.ko : S.attente);
    zone.textContent = texte;
  }

  var ouvert = null;

  function fermer() {
    if (ouvert && ouvert.parentNode) ouvert.parentNode.removeChild(ouvert);
    ouvert = null;
    document.removeEventListener("keydown", echap, true);
  }
  function echap(ev) { if (ev.key === "Escape") { ev.stopPropagation(); fermer(); } }

  function etatDuCompte(e, id) {
    var c = (e.comptes || {})[id];
    if (!c) return null;
    if (c.expire_passe) return [false, T("igrelier.etat.expire_passe")];
    if (c.erreur) return [false, T("igrelier.etat.erreur", { detail: c.erreur })];
    return [true, T("igrelier.etat.relie", { nom: c.username || "?", date: c.expire || "?" })];
  }

  async function panneau() {
    fermer();
    var voile = el("div", { style: S.voile, "data-dz-ig-relier": "voile" });
    var p = el("div", { style: S.panneau, role: "dialog", "aria-modal": "true", "data-dz-ig-relier": "panneau" });
    voile.appendChild(p);
    voile.addEventListener("click", function (ev) { if (ev.target === voile) fermer(); });
    p.appendChild(el("div", { style: S.titre, id: "dz-ig-relier-titre" }, T("igrelier.panneau.titre")));
    p.setAttribute("aria-labelledby", "dz-ig-relier-titre");
    p.appendChild(el("div", { style: S.note }, T("igrelier.panneau.intro")));
    var statut = el("div", { role: "status", "data-dz-ig-relier": "statut" });
    p.appendChild(statut);

    p.appendChild(el("label", { style: S.lib, "for": "dz-ig-relier-compte" }, T("igrelier.panneau.compte_lib")));
    var choix = el("select", { id: "dz-ig-relier-compte", style: S.champ, "data-dz-ig-relier": "compte" });
    p.appendChild(choix);
    var compteEtat = el("div", { "data-dz-ig-relier": "compte-etat" });
    p.appendChild(compteEtat);

    p.appendChild(el("label", { style: S.lib, "for": "dz-ig-relier-retour" }, T("igrelier.panneau.retour_lib")));
    var retour = el("input", { id: "dz-ig-relier-retour", type: "text", readonly: "readonly", style: S.champ,
                               "data-dz-ig-relier": "adresse-retour" });
    p.appendChild(retour);

    var l1 = el("div", { style: S.ligne });
    var bOuvrir = el("button", { type: "button", style: S.btn + ";" + S.primaire, "data-dz-ig-relier": "ouvrir" },
                     T("igrelier.bouton.ouvrir"));
    l1.appendChild(bOuvrir);
    p.appendChild(l1);

    p.appendChild(el("label", { style: S.lib, "for": "dz-ig-relier-colle" }, T("igrelier.panneau.coller_lib")));
    p.appendChild(el("div", { style: S.note }, T("igrelier.panneau.coller_aide")));
    var colle = el("input", { id: "dz-ig-relier-colle", type: "text", spellcheck: "false", style: S.champ,
                              placeholder: "https://localhost/?code=…&state=…", "data-dz-ig-relier": "colle" });
    p.appendChild(colle);
    var l2 = el("div", { style: S.ligne });
    var bTerminer = el("button", { type: "button", style: S.btn, "data-dz-ig-relier": "terminer" }, T("igrelier.bouton.terminer"));
    var bFermer = el("button", { type: "button", style: S.btn, "data-dz-ig-relier": "fermer" }, T("igrelier.bouton.fermer"));
    l2.appendChild(bTerminer); l2.appendChild(bFermer);
    p.appendChild(l2);
    var verdict = el("div", { role: "status", "data-dz-ig-relier": "verdict" });
    p.appendChild(verdict);
    p.appendChild(el("div", { style: S.note }, T("igrelier.panneau.secours")));

    document.body.appendChild(voile);
    ouvert = voile;
    document.addEventListener("keydown", echap, true);
    bFermer.addEventListener("click", fermer);

    var e = {};
    function montrerCompte() {
      var x = etatDuCompte(e, choix.value);
      if (x) dire(compteEtat, x[0], x[1]); else { compteEtat.textContent = ""; compteEtat.removeAttribute("data-dz-ig-verdict"); }
    }
    async function relire() {
      try { e = await appel("/etat"); } catch (err) { dire(statut, false, T("igrelier.etat.echec", { detail: err.message })); return; }
      var garde = choix.value;
      while (choix.firstChild) choix.removeChild(choix.firstChild);
      (e.choix || []).forEach(function (c) {
        choix.appendChild(el("option", { value: c.id }, c.historique ? T("igrelier.panneau.historique") : c.libelle));
      });
      if (garde) choix.value = garde;
      retour.value = e.redirect_uri || "";
      var pret = e.configure && e.coffre_ouvert;
      bOuvrir.disabled = !pret;
      bOuvrir.style.opacity = pret ? "1" : ".45";
      bOuvrir.style.cursor = pret ? "pointer" : "not-allowed";
      dire(statut, pret ? null : false, !e.configure ? T("igrelier.etat.non_configure")
        : !e.coffre_ouvert ? T("igrelier.etat.coffre_ferme") : T("igrelier.etat.pret"));
      montrerCompte();
    }
    choix.addEventListener("change", montrerCompte);
    bOuvrir.addEventListener("click", async function () {
      var w = null;
      try { w = window.open("", "_blank"); } catch (err) { w = null; }   // ouvert sur le clic : pas bloqué
      dire(verdict, null, T("igrelier.etat.en_cours"));
      try {
        var j = await appel("/demarrer", { compte: choix.value || null });
        if (w) { w.opener = null; w.location.href = j.url; } else { window.open(j.url, "_blank", "noopener"); }
        dire(verdict, null, T("igrelier.etat.ouvert"));
      } catch (err) {
        if (w) w.close();
        dire(verdict, false, T("igrelier.etat.echec", { detail: err.message }));
      }
    });
    bTerminer.addEventListener("click", async function () {
      var a = colle.value.trim();
      if (!a) return;
      dire(verdict, null, T("igrelier.etat.en_cours"));
      try {
        var j = await appel("/retour", { adresse: a });
        colle.value = "";
        dire(verdict, true, j.message || "OK");
        await relire();
      } catch (err) {
        dire(verdict, false, T("igrelier.etat.echec", { detail: err.message }));
      }
    });
    await relire();
    bOuvrir.focus();
  }

  function monter(hote) {
    if (!hote || hote.getAttribute("data-dz-ig-relier-monte") === "1") return;
    hote.setAttribute("data-dz-ig-relier-monte", "1");
    var b = el("button", { type: "button", style: S.petit, title: T("igrelier.bouton.relier_titre"),
                           "data-dz-ig-relier": "bouton" }, T("igrelier.bouton.relier"));
    b.addEventListener("click", function () { panneau(); });
    hote.appendChild(b);
  }

  window.__dzIgRelier = { monter: monter, fermer: fermer };
})();
