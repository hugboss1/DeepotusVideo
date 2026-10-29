/* dz-mcp.js — le SERVEUR MCP à l'écran (t345, D1 du lot Scenario, 29/10/2026, spec
   docs/superpowers/specs/2026-10-27-scenario-explorations-design.md). SOURCE : frontend/shared/dz-mcp.js ; copie
   OCTET POUR OCTET : frontend/dist/shared/dz-mcp.js, servie à /shared/dz-mcp.js, chargée par une balise classique
   dans la SPA (frontend/dist/index.html). Banc : backend/tests/test_mcp_ecran.py. Serveur : backend/app/api/mcp_routes.py.

   Deux surfaces, vanilla DOM, aucun innerHTML :
   1. window.__dzMcp.monter(hote) — Réglages › Serveur MCP (l'onglet est posé par le maillon de queue
      scripts/patch_bundle_dzmcp.py, qui rend un <div data-dz-mcp-hote> et appelle monter par une ref) : activer le
      serveur (désactivé par défaut), la commande à copier pour `claude mcp add`, les demandes de lancement, ce que
      voit Claude Code (outils par nature) et le journal des appels (outil, réussite, résumé ; jamais les valeurs).
   2. Les CARTES de demande, en bas à droite de toute la SPA : quand Claude Code appelle « lancer » avec le jeton d'un
      devis, la demande passe « en_attente » ; la carte dit le genre, le résumé, la raison donnée et le MONTANT, et
      seul le clic « Lancer » de l'utilisateur dépense : POST …/commencer (la route et le corps FIGÉS au devis), puis
      l'écran appelle LUI-MÊME la route de génération (comme la carte de devis de l'agent Campagnes) — un 402 de
      plafond passe par l'enveloppe de window.fetch (dz-plafonds.js) —, puis POST …/resultat. « Refuser » : POST
      …/refuser. Sondage : 5 s quand le serveur est actif, 30 s sinon ; rien à l'écran quand rien n'attend.
   Textes : clés mcp.* (frontend/shared/i18n/mcp.json). Charte : aucun arrondi, IBM Plex Mono en capitales pour les
   titres, jetons --srf-* / --brd-* / --txt-* avec repli. */
(function () {
  "use strict";
  if (window.__dzMcp) return;

  var BASE = "/api/mcp";
  var ROUTES = { video: "/api/generate", image: "/api/images/generate", voix: "/api/audio/voiceover" };
  var JSON_H = { "Content-Type": "application/json" };
  var SONDE_ACTIF_MS = 5000, SONDE_REPOS_MS = 30000;
  var S = {
    panneau: "display:flex;flex-direction:column;gap:14px;color:var(--txt-base,var(--ink,#cfd6e2));font:13px/1.5 system-ui,sans-serif",
    titre: "font:600 18px/1.3 system-ui,sans-serif;color:var(--txt-hi,var(--ink-strong,#e6e9ee))",
    intro: "font-size:12.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae));max-width:680px",
    cadre: "border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));background:var(--srf-panel,var(--bg-panel,#13171c));padding:12px 14px;display:flex;flex-direction:column;gap:8px",
    tete: "font:10px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    note: "font-size:12px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    ligne: "display:flex;align-items:center;gap:8px;flex-wrap:wrap",
    code: "flex:1;min-width:260px;padding:7px 9px;background:var(--srf-sunken,var(--bg-base,#0d1014));border:1px solid var(--brd-soft,var(--stroke,#222830));font:11.5px/1.45 'IBM Plex Mono',monospace;color:var(--txt-hi,var(--ink-strong,#e6e9ee));word-break:break-all;user-select:all",
    btn: "height:28px;padding:0 12px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit;display:inline-flex;align-items:center;gap:6px",
    primaire: "background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6);color:var(--accent-ink,#ffffff)",
    ok: "color:var(--green,#3fb950)",
    ko: "color:var(--amber,#f0b429)",
    erreur: "color:var(--red,#e5484d);font-size:12px",
    table: "width:100%;border-collapse:collapse;font-size:12px",
    cel: "padding:4px 6px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));vertical-align:top;text-align:left",
    pile: "position:fixed;right:16px;bottom:16px;z-index:9970;display:flex;flex-direction:column;gap:10px;width:360px;max-width:calc(100vw - 32px)",
    carte: "border:1px solid var(--accent,#2b6fd6);background:var(--srf-panel,var(--bg-panel-2,#13171c));color:var(--txt-base,var(--ink,#cfd6e2));box-shadow:0 12px 34px rgba(0,0,0,.45);padding:12px 14px;display:flex;flex-direction:column;gap:8px;font:13px/1.45 system-ui,sans-serif",
    prix: "font:600 15px system-ui,sans-serif;color:var(--txt-hi,var(--ink-strong,#e6e9ee))"
  };

  function T(cle, v) { return typeof window.dzT === "function" ? window.dzT(cle, v) : cle; }
  function langue() { var l = typeof window.dzLang === "function" ? window.dzLang() : window.dzLang; return l === "en" ? "en" : "fr"; }
  function usd(v) {
    v = Number(v) || 0;
    var t = v !== 0 && Math.abs(v) < 0.1 ? v.toFixed(4).replace(/0+$/, "") : v.toFixed(2);
    if ((t.split(".")[1] || "").length < 2) t = Number(t).toFixed(2);
    return langue() === "en" ? "$" + t : t.replace(".", ",") + " $";
  }
  function el(tag, attrs, texte) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (texte != null) n.textContent = texte;
    return n;
  }
  /* Deepotus Glyph : l'icône tirée du sprite servi, décorative (le libellé porte le sens). */
  function glyphe(cle) {
    var ns = "http://www.w3.org/2000/svg", s = document.createElementNS(ns, "svg"), u = document.createElementNS(ns, "use");
    s.setAttribute("class", "dzi"); s.setAttribute("width", "14"); s.setAttribute("height", "14");
    s.setAttribute("aria-hidden", "true"); s.setAttribute("focusable", "false"); s.setAttribute("data-dz-icone", cle);
    s.setAttribute("style", "fill:currentColor;flex:none");
    u.setAttribute("href", "/shared/icons/dz-icons.svg#" + cle);
    s.appendChild(u);
    return s;
  }
  function bouton(marque, texte, icone, principal) {
    var b = el("button", { type: "button", "data-dz-mcp": marque, style: S.btn + (principal ? ";" + S.primaire : "") });
    if (icone) b.appendChild(glyphe(icone));
    b.appendChild(document.createTextNode(texte));
    return b;
  }
  function vider(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  async function lireJson(r) { try { return await r.json(); } catch (e) { return null; } }
  function detail(j, statut) {
    var d = j && j.detail;
    if (typeof d === "string" && d) return d;
    if (d && d.dz_plafond && d.dz_plafond.message) return String(d.dz_plafond.message);
    return "HTTP " + statut;
  }
  async function appel(chemin, methode, corps) {
    var r = await window.fetch(BASE + chemin, { method: methode || "GET", headers: JSON_H,
                                                 body: corps === undefined ? undefined : JSON.stringify(corps) });
    var j = await lireJson(r);
    if (!r.ok) throw new Error(detail(j, r.status));
    return j;
  }
  function heure(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso || "");
    return d.toLocaleString(langue() === "en" ? "en-GB" : "fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  }
  function genre(g) { return T("mcp.genre." + (g === "video" || g === "voix" ? g : "image")); }

  // ---- le lancement : seul geste qui dépense, au clic de l'utilisateur ---------------------------------------------
  var occupees = {};
  function nomResultat(g, j) {
    if (g === "video") return j && j.job_id ? { job_id: String(j.job_id) } : null;
    if (g === "image") {
      var i = j && j.images && j.images[0];
      if (i && typeof i === "object") i = i.filename || i.name;
      return typeof i === "string" && i ? { fichier: i } : null;
    }
    return j && typeof j.filename === "string" && j.filename ? { fichier: j.filename } : null;
  }
  async function lancer(d) {
    if (occupees[d.id]) return { ok: false, message: "" };
    occupees[d.id] = true;
    try {
      var c = await appel("/demandes/" + encodeURIComponent(d.id) + "/commencer", "POST", {});
      if (!ROUTES[c.genre] || c.route !== ROUTES[c.genre]) throw new Error(T("mcp.erreur.route"));
      var r = await window.fetch(c.route, { method: "POST", headers: JSON_H, body: JSON.stringify(c.corps || {}) });
      var j = await lireJson(r);
      if (!r.ok) {
        var m = detail(j, r.status);
        await appel("/demandes/" + encodeURIComponent(d.id) + "/resultat", "POST", { ok: false, message: m }).catch(function () {});
        return { ok: false, message: m };
      }
      var res = nomResultat(c.genre, j) || {};
      await appel("/demandes/" + encodeURIComponent(d.id) + "/resultat", "POST",
                  { ok: true, job_id: res.job_id, fichier: res.fichier }).catch(function () {});
      return { ok: true, resultat: res };
    } catch (e) {
      return { ok: false, message: String((e && e.message) || e) };
    } finally {
      delete occupees[d.id];
      sonder(true);
    }
  }
  async function refuser(d) {
    try { await appel("/demandes/" + encodeURIComponent(d.id) + "/refuser", "POST", {}); return { ok: true }; }
    catch (e) { return { ok: false, message: String((e && e.message) || e) }; }
    finally { sonder(true); }
  }

  /* Le bloc d'une demande en attente (carte flottante et panneau des Réglages partagent ce rendu). */
  function blocDemande(d, apres) {
    var b = el("div", { "data-dz-mcp": "demande", "data-dz-mcp-id": d.id, style: "display:flex;flex-direction:column;gap:6px" });
    b.appendChild(el("div", { style: S.tete }, T("mcp.carte.titre", { genre: genre(d.genre) })));
    if (d.resume) b.appendChild(el("div", { "data-dz-brut": "1", style: "color:var(--txt-hi,var(--ink-strong,#e6e9ee))" }, "« " + d.resume + " »"));
    if (d.pourquoi) b.appendChild(el("div", { "data-dz-brut": "1", style: S.note }, T("mcp.carte.pourquoi", { texte: d.pourquoi })));
    b.appendChild(el("div", { style: S.prix, "data-dz-mcp": "prix" }, T("mcp.carte.cout", { usd: usd(d.usd) })));
    b.appendChild(el("div", { style: S.note }, T("mcp.carte.aide")));
    var msg = el("div", { style: S.erreur, role: "alert", hidden: "" });
    var l = el("div", { style: S.ligne });
    var go = bouton("lancer", T("mcp.carte.lancer", { usd: usd(d.usd) }), "dz-action-lancer", true);
    var non = bouton("refuser", T("mcp.carte.refuser"), "dz-action-annuler");
    go.addEventListener("click", async function () {
      go.disabled = non.disabled = true;
      var r = await lancer(d);
      if (r.ok) { if (apres) apres(T("mcp.carte.lancee")); }
      else {
        // la demande est passée « echec » côté serveur : le bloc reste affiché (figé) avec la raison, jusqu'à « Masquer »
        b.setAttribute("data-dz-mcp-fige", "1");
        msg.textContent = T("mcp.erreur.lancement", { msg: r.message || "" }); msg.removeAttribute("hidden");
        l.style.display = "none";
        var cacher = bouton("masquer", T("mcp.carte.plus_tard"), null);
        cacher.addEventListener("click", function () {
          var n = b.closest("[data-dz-mcp='carte']") || b;
          if (n.parentNode) n.parentNode.removeChild(n);
        });
        if (!b.closest("[data-dz-mcp='carte']")) b.appendChild(cacher);   // la carte flottante a déjà « Masquer »
      }
    });
    non.addEventListener("click", async function () {
      go.disabled = non.disabled = true;
      var r = await refuser(d);
      if (r.ok) { if (apres) apres(T("mcp.carte.refusee")); }
      else { go.disabled = non.disabled = false; msg.textContent = r.message; msg.removeAttribute("hidden"); }
    });
    l.appendChild(go); l.appendChild(non);
    b.appendChild(l); b.appendChild(msg);
    return b;
  }

  // ---- les cartes flottantes ---------------------------------------------------------------------------------------
  var pile = null, vues = {}, plusTard = {}, minuterie = null, actifConnu = false;
  function pileDom() {
    if (pile && pile.parentNode) return pile;
    pile = el("div", { "data-dz-mcp": "pile", style: S.pile, "aria-live": "polite" });
    document.body.appendChild(pile);
    return pile;
  }
  function montrerCartes(liste) {
    var ids = {};
    liste.forEach(function (d) {
      ids[d.id] = true;
      if (vues[d.id] || plusTard[d.id]) return;
      var c = el("div", { "data-dz-mcp": "carte", role: "dialog", "aria-label": T("mcp.carte.titre", { genre: genre(d.genre) }), style: S.carte });
      c.appendChild(blocDemande(d, function (texte) {
        vider(c); c.appendChild(el("div", { style: S.ok }, texte));
        setTimeout(function () { if (c.parentNode) c.parentNode.removeChild(c); delete vues[d.id]; }, 2500);
      }));
      var tard = bouton("plus-tard", T("mcp.carte.plus_tard"), null);
      tard.setAttribute("style", S.btn + ";align-self:flex-end;height:24px;font-size:11.5px");
      tard.addEventListener("click", function () { plusTard[d.id] = true; if (c.parentNode) c.parentNode.removeChild(c); delete vues[d.id]; });
      c.appendChild(tard);
      pileDom().appendChild(c);
      vues[d.id] = c;
    });
    Object.keys(vues).forEach(function (id) {
      if (!ids[id] && !occupees[id] && !vues[id].querySelector("[data-dz-mcp-fige]")
          && vues[id].querySelector("[data-dz-mcp='lancer']")) {
        if (vues[id].parentNode) vues[id].parentNode.removeChild(vues[id]);
        delete vues[id];
      }
    });
  }
  async function sonder(vite) {
    if (minuterie) { clearTimeout(minuterie); minuterie = null; }
    try {
      var e = await appel("/etat");
      actifConnu = !!e.actif;
      var reglagesOuverts = !!(panneau && document.body.contains(panneau));
      // Réglages › Serveur MCP ouvert : les demandes s'y affichent déjà, pas de carte flottante par-dessus
      if (e.en_attente > 0 && !reglagesOuverts) montrerCartes((await appel("/demandes?etat=en_attente")).demandes || []);
      else montrerCartes([]);
      if (reglagesOuverts) rafraichir(panneau, e);
    } catch (err) { /* backend absent : on réessaiera */ }
    minuterie = setTimeout(sonder, vite || actifConnu ? SONDE_ACTIF_MS : SONDE_REPOS_MS);
  }

  // ---- Réglages › Serveur MCP --------------------------------------------------------------------------------------
  var panneau = null;
  function cadre(marque, titre) {
    var c = el("section", { "data-dz-mcp": marque, style: S.cadre });
    c.appendChild(el("div", { style: S.tete }, titre));
    return c;
  }
  function monter(hote) {
    if (!hote || hote.getAttribute("data-dz-mcp-monte") === "1") return;
    hote.setAttribute("data-dz-mcp-monte", "1");
    var p = el("div", { "data-dz-mcp": "panneau", style: S.panneau });
    p.appendChild(el("div", { style: S.titre }, T("mcp.reglages.titre")));
    p.appendChild(el("div", { style: S.intro }, T("mcp.reglages.intro")));

    var etat = cadre("etat", T("mcp.etat.titre"));
    var lab = el("label", { style: S.ligne + ";cursor:pointer" });
    var cb = el("input", { type: "checkbox", "data-dz-mcp": "actif" });
    lab.appendChild(cb); lab.appendChild(el("span", {}, T("mcp.etat.activer")));
    etat.appendChild(lab);
    var statut = el("div", { "data-dz-mcp": "statut", style: S.note });
    etat.appendChild(statut);
    var errEtat = el("div", { style: S.erreur, role: "alert", hidden: "" });
    etat.appendChild(errEtat);
    cb.addEventListener("change", async function () {
      cb.disabled = true; errEtat.setAttribute("hidden", "");
      try { await appel("/reglages", "PUT", { actif: cb.checked }); }
      catch (e) { cb.checked = !cb.checked; errEtat.textContent = String(e.message || e); errEtat.removeAttribute("hidden"); }
      cb.disabled = false;
      sonder(true);
    });
    p.appendChild(etat);

    var br = cadre("brancher", T("mcp.brancher.titre"));
    br.appendChild(el("div", { style: S.note }, T("mcp.brancher.etape1")));
    var lc = el("div", { style: S.ligne });
    var code = el("code", { "data-dz-mcp": "commande", style: S.code });
    var copier = bouton("copier", T("mcp.brancher.copier"), "dz-action-copier");
    copier.addEventListener("click", function () {
      var t = code.textContent || "";
      var fini = function () { copier.lastChild.textContent = T("mcp.brancher.copie"); setTimeout(function () { copier.lastChild.textContent = T("mcp.brancher.copier"); }, 1800); };
      try { navigator.clipboard.writeText(t).then(fini, fini); } catch (e) { fini(); }
    });
    lc.appendChild(code); lc.appendChild(copier);
    br.appendChild(lc);
    br.appendChild(el("div", { style: S.note }, T("mcp.brancher.etape2")));
    p.appendChild(br);

    var dem = cadre("demandes", T("mcp.demandes.titre"));
    var listeDem = el("div", { "data-dz-mcp": "liste-demandes", style: "display:flex;flex-direction:column;gap:12px" });
    dem.appendChild(listeDem);
    p.appendChild(dem);

    var out = cadre("outils", T("mcp.outils.titre"));
    out.appendChild(el("div", { style: S.note }, T("mcp.outils.aide")));
    var listeOut = el("div", { "data-dz-mcp": "liste-outils", style: "display:flex;flex-direction:column;gap:4px" });
    out.appendChild(listeOut);
    p.appendChild(out);

    var jo = cadre("journal", T("mcp.journal.titre"));
    var lj = el("div", { style: S.ligne });
    lj.appendChild(el("div", { style: S.note + ";flex:1" }, T("mcp.journal.aide")));
    var act = bouton("actualiser", T("mcp.journal.actualiser"), "dz-action-actualiser");
    act.addEventListener("click", function () { sonder(true); });
    lj.appendChild(act);
    jo.appendChild(lj);
    var tab = el("div", { "data-dz-mcp": "journal-liste" });
    jo.appendChild(tab);
    p.appendChild(jo);

    p.__dz = { cb: cb, statut: statut, code: code, listeDem: listeDem, listeOut: listeOut, tab: tab };
    hote.appendChild(p);
    panneau = p;
    sonder(true);
  }

  async function rafraichir(p, e) {
    var R = p.__dz;
    R.cb.checked = !!e.actif;
    R.statut.textContent = e.actif ? T("mcp.etat.actif") : T("mcp.etat.inactif");
    R.statut.setAttribute("style", S.note + ";" + (e.actif ? S.ok : ""));
    R.code.textContent = (e.commande && e.commande.claude) || "";
    // les outils, par nature
    vider(R.listeOut);
    var natures = { lecture: [], devis: [], demande: [] };
    (e.outils || []).forEach(function (o) { (natures[o.nature] || natures.lecture).push(o.nom); });
    ["lecture", "devis", "demande"].forEach(function (n) {
      if (!natures[n].length) return;
      var l = el("div", { style: S.ligne + ";align-items:baseline" });
      l.appendChild(el("span", { style: S.tete + ";min-width:96px" }, T("mcp.nature." + n)));
      l.appendChild(el("span", { "data-dz-brut": "1", style: "flex:1;min-width:0;overflow-wrap:anywhere;font:11.5px/1.6 'IBM Plex Mono',monospace" }, natures[n].join(" · ")));
      R.listeOut.appendChild(l);
    });
    // les demandes en attente
    try {
      var ds = e.en_attente > 0 ? ((await appel("/demandes?etat=en_attente")).demandes || []) : [];
      var cle = ds.map(function (d) { return d.id; }).join(",");
      var occupe = Object.keys(occupees).length > 0;
      // on ne reconstruit la liste que si elle a changé (un bouton ne disparaît pas sous le curseur) ; un bloc figé
      // (lancement en échec, avec sa raison) est gardé en tête
      if (cle !== R.cleDem && !occupe) {
        R.cleDem = cle;
        var figes = Array.prototype.slice.call(R.listeDem.querySelectorAll("[data-dz-mcp-fige]"));
        vider(R.listeDem);
        figes.forEach(function (f) { R.listeDem.appendChild(f); });
        if (!ds.length && !figes.length) R.listeDem.appendChild(el("div", { style: S.note, "data-dz-mcp": "vide" }, T("mcp.demandes.vide")));
        ds.forEach(function (d) {
          R.listeDem.appendChild(blocDemande(d, function (texte) { R.cleDem = null; sonder(true); R.listeDem.insertBefore(el("div", { style: S.ok, "data-dz-mcp-fige": "1" }, texte), R.listeDem.firstChild); }));
        });
      }
    } catch (err) { /* liste illisible : on garde la précédente */ }
    // le journal
    try {
      var js = (await appel("/journal?n=30")).appels || [];
      vider(R.tab);
      if (!js.length) { R.tab.appendChild(el("div", { style: S.note }, T("mcp.journal.vide"))); return; }
      var t = el("table", { style: S.table }), th = el("tr", {});
      ["mcp.journal.quand", "mcp.journal.outil", "mcp.journal.resultat", "mcp.journal.resume"].forEach(function (k) {
        th.appendChild(el("th", { style: S.cel + ";" + S.tete }, T(k)));
      });
      t.appendChild(th);
      js.forEach(function (a) {
        var tr = el("tr", { "data-dz-mcp": "appel" });
        tr.appendChild(el("td", { style: S.cel + ";white-space:nowrap" }, heure(a.quand)));
        tr.appendChild(el("td", { style: S.cel + ";font-family:'IBM Plex Mono',monospace", "data-dz-brut": "1" }, a.outil || ""));
        tr.appendChild(el("td", { style: S.cel + ";" + (a.ok ? S.ok : S.ko) }, a.ok ? T("mcp.journal.ok") : T("mcp.journal.ko")));
        tr.appendChild(el("td", { style: S.cel, "data-dz-brut": "1" }, a.resume || ""));
        t.appendChild(tr);
      });
      R.tab.appendChild(t);
    } catch (err) { /* journal illisible */ }
  }

  window.__dzMcp = { monter: monter, sonder: sonder, lancer: lancer, refuser: refuser };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", function () { setTimeout(sonder, 3000); });
  else setTimeout(sonder, 3000);
})();
