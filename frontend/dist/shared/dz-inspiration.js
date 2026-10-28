/* dz-inspiration.js — la boîte « Inspiration → contenu neuf » du Planificateur (t313, 28/10/2026, plan
   docs/superpowers/plans/2026-10-28-t313-inspiration.md, Décision 9 ; spec boîte à outils §7.4). SOURCE :
   frontend/shared/dz-inspiration.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-inspiration.js, chargée par
   frontend/dist/index.html (balise classique après dz-whatsapp-espace.js). Le bouton « Depuis une inspiration » du
   Planificateur (maillon de queue scripts/patch_bundle_dzinspiration.py) appelle window.__dzInspiration.ouvrir().
   Bancs : backend/tests/test_inspiration_ecran.py (copie, balise, clés, maillon) et frontend/shared/qa/inspiration.test.mjs
   (la boîte jouée sous node, faux DOM, faux fetch, la vraie enveloppe dz-plafonds.js).

   window.__dzInspiration.ouvrir() -> Promise<{post} | null>. Décision de l'utilisateur : on REFABRIQUE, on ne republie
   jamais l'original. Une boîte en quatre temps :
   - EN TÊTE : « Pour : espace · projet · canaux » (GET /api/inspiration, l'espace de la requête), la règle anti-copie,
     et, chez un client « validé par le client », que le brouillon naîtra « À valider » ; les inspirations récentes
     (source, date, brouillons) qu'on peut reprendre (GET /api/inspiration/{id}).
   - 1. CAPTURE : une image (glisser, coller Ctrl+V, choisir ; une nouvelle remplace l'ancienne) et/ou un texte collé,
     la source (libellé et lien, notés dans la fiche, jamais publiés), la langue ; « Lire la capture (gratuit) » ->
     POST /api/inspiration/capter (multipart). Le texte lu est montré tel quel (textContent), comme une matière à
     analyser, jamais une consigne ; la palette relevée.
   - 2. MATIÈRE ET ANGLES (payant) : GET …/devis-analyse?image=0|1 (« Lire aussi l'image » coûte plus) ; au clic,
     `await window.__dzDialogue.confirmer(` avec le montant (sans dialogue : rien ne part), puis POST …/analyse
     {max_usd: devis, avec_image, langue}. 409 `cout` : le nouveau montant est montré, un second clic l'accepte ;
     402 : l'enveloppe de dz-plafonds.js. Trois angles ; un angle en alerte (reprend la capture, mot interdit) est grisé.
   - 3. DEVIS : POST …/devis {angle, image} -> la carte (texte + visuel fal neuf) ; « Générer (≈ total) » ->
     confirmation -> POST …/redaction {angle, max_usd: texte} puis, si le visuel est demandé, la route de la carte
     (/api/images/generate, la seule permise) avec son corps ; le nom du fichier rendu devient le visuel.
   - 4. BROUILLON : titre, accroche, légende modifiables (la garde du serveur est montrée : proximité, plus longue
     reprise, mots interdits) ; « Créer le brouillon » -> POST …/brouillon ; 409 copie / interdits / visuel_capte : le
     message et l'extrait ; succès : statut (À valider ou brouillon, canaux), puis l'événement
     « deepotus:schedule-recharger » (t309) recharge le Planificateur.
   Pendant un appel payant, la boîte ne se ferme pas et tout est grisé (une réponse payée n'est jamais perdue).
   Échap ferme (hors appel), Tab reste dans la boîte. Jamais d'innerHTML. CHARTE : celle de dz-scan.js (aucun arrondi).
   Textes : clés inspiration.* (frontend/shared/i18n/inspiration.json). */
(function () {
  "use strict";
  if (window.__dzInspiration) return;

  var BASE = "/api/inspiration";
  var ROUTE_IMAGE = "/api/images/generate";
  var JSON_H = { "Content-Type": "application/json" };
  var S = {
    voile: "position:fixed;inset:0;z-index:9990;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center",
    occupe: "position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.45);color:var(--txt-hi,var(--ink-strong,#e6e9ee));font-size:13px;z-index:2",
    boite: "position:relative;width:760px;max-width:94vw;max-height:90vh;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    corps: "padding:12px 14px;overflow-y:auto;display:flex;flex-direction:column;gap:10px;color:var(--txt-base,var(--ink,#cfd6e2))",
    section: "display:flex;flex-direction:column;gap:6px;border-top:1px solid var(--brd-soft,var(--stroke,#222830));padding-top:8px",
    titre: "font:10px 'IBM Plex Mono',monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    depot: "border:1px dashed var(--brd-hard,var(--stroke-strong,#2a3138));padding:10px;display:flex;flex-direction:column;gap:6px;align-items:flex-start",
    note: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    ligne: "display:flex;align-items:center;gap:8px;flex-wrap:wrap",
    etat: "font-size:12px;min-height:16px",
    erreur: "color:var(--red,#e5484d)",
    alerte: "font-size:12px;padding:6px 8px;border:1px solid var(--amber,#f0b429);color:var(--amber,#f0b429)",
    lu: "margin:0;max-height:140px;overflow:auto;white-space:pre-wrap;word-wrap:break-word;padding:8px;border:1px solid var(--brd-soft,var(--stroke,#222830));font:12px/1.45 'IBM Plex Mono',ui-monospace,monospace",
    champ: "box-sizing:border-box;width:100%;padding:6px 8px;background:transparent;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));font:inherit;border-radius:0",
    angle: "display:flex;flex-direction:column;gap:3px;padding:8px;border:1px solid var(--brd-soft,var(--stroke,#222830))",
    angleChoisi: "border-color:var(--accent,#2b6fd6)",
    pastille: "display:inline-block;width:16px;height:16px;border:1px solid var(--brd-soft,#222830)",
    apercu: "max-width:160px;max-height:120px;border:1px solid var(--brd-soft,#222830)",
    pied: "display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
    btn: "min-width:88px;height:28px;padding:0 12px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit",
    ok: "background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6);color:var(--accent-ink,#ffffff)"
  };
  var courant = null;

  function T(cle, v) { return typeof window.dzT === "function" ? window.dzT(cle, v) : cle; }
  function langue() { return typeof window.dzLang === "function" ? window.dzLang() : "fr"; }
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
  function bouton(marque, texte, style) {
    return el("button", { type: "button", "data-dz-insp": marque, style: S.btn + (style ? ";" + style : "") }, texte);
  }
  function montrer(n, oui) { if (!n) return; if (oui) n.removeAttribute("hidden"); else n.setAttribute("hidden", ""); }
  function griser(n, oui) { if (!n) return; if (oui) n.setAttribute("disabled", ""); else n.removeAttribute("disabled"); }
  function vider(n) { while (n && n.firstChild) n.removeChild(n.firstChild); }
  function dire(E, texte, erreur) {
    E.etat.textContent = texte || "";
    E.etat.setAttribute("style", S.etat + (erreur ? ";" + S.erreur : ""));
  }
  function detail(j, status) {
    var d = j && j.detail;
    if (typeof d === "string" && d) return d;
    if (d && typeof d.message === "string") return d.message;
    if (d && d.dz_plafond && d.dz_plafond.message) return String(d.dz_plafond.message);
    return "HTTP " + status;
  }
  async function lireJson(R) { try { return await R.json(); } catch (e) { return null; } }
  async function appel(methode, chemin, corps) {
    var init = { method: methode, headers: corps instanceof FormData ? {} : JSON_H };
    if (corps !== undefined) init.body = corps instanceof FormData ? corps : JSON.stringify(corps);
    var R = await window.fetch(chemin, init);
    return { R: R, j: await lireJson(R) };
  }
  function accepte(f) {
    var type = String((f && f.type) || "").toLowerCase(), nom = String((f && f.name) || "").toLowerCase();
    return (type.indexOf("image/") === 0 && type !== "image/svg+xml") || (!type && /\.(png|jpe?g|webp|bmp|tiff?)$/.test(nom));
  }
  function nomImage(j) {
    var i = j && j.images && j.images[0];
    if (i && typeof i === "object") i = i.filename || i.name;
    return typeof i === "string" && i ? i : "";
  }

  /* ---- montage ------------------------------------------------------------------------------------------------- */
  function section(E, cle) {
    var s = el("div", { "data-dz-insp": "section-" + cle, style: S.section });
    s.appendChild(el("div", { style: S.titre }, T("inspiration." + cle + ".titre")));
    E.corps.appendChild(s);
    return s;
  }
  function champ(tag, marque, etiquette, attrs) {
    var l = el("label", { style: "display:flex;flex-direction:column;gap:3px;font-size:12px" }, null);
    l.appendChild(el("span", null, etiquette));
    var c = el(tag, Object.assign({ "data-dz-insp": marque, style: S.champ }, attrs || {}));
    l.appendChild(c);
    return { l: l, c: c };
  }

  function construire(E) {
    var voile = el("div", { "data-dz-insp": "voile", style: S.voile, role: "dialog", "aria-modal": "true" });
    var boite = el("div", { style: S.boite });
    voile.appendChild(boite);
    boite.appendChild(el("div", { style: S.tete }, T("inspiration.boite.titre")));
    E.voileOccupe = el("div", { "data-dz-insp": "occupe", style: S.occupe, hidden: "" }, T("inspiration.boite.occupe"));
    boite.appendChild(E.voileOccupe);
    E.corps = el("div", { style: S.corps });
    boite.appendChild(E.corps);
    E.pourQui = el("div", { "data-dz-insp": "pour-qui", style: "font-size:12.5px" });
    E.corps.appendChild(E.pourQui);
    E.client = el("div", { "data-dz-insp": "client", style: S.alerte, hidden: "" }, T("inspiration.pour_qui.client"));
    E.corps.appendChild(E.client);
    E.corps.appendChild(el("div", { "data-dz-insp": "regle", style: S.note }, T("inspiration.boite.regle")));
    E.recents = el("div", { "data-dz-insp": "recents", style: "display:flex;flex-direction:column;gap:3px", hidden: "" });
    E.corps.appendChild(E.recents);

    /* 1. capture */
    var s1 = section(E, "capture");
    var depot = el("div", { "data-dz-insp": "depot", style: S.depot });
    depot.appendChild(el("div", { style: S.note }, T("inspiration.capture.depot")));
    var ligne = el("div", { style: S.ligne });
    E.choisir = bouton("choisir", T("inspiration.capture.choisir"));
    E.entree = el("input", { type: "file", accept: "image/*", "data-dz-insp": "fichier", hidden: "" });
    E.nomFichier = el("span", { "data-dz-insp": "nom-fichier", style: S.note });
    E.retirer = bouton("retirer", T("inspiration.capture.retirer"), "min-width:0");
    montrer(E.retirer, false);
    ligne.appendChild(E.choisir); ligne.appendChild(E.entree); ligne.appendChild(E.nomFichier); ligne.appendChild(E.retirer);
    depot.appendChild(ligne);
    s1.appendChild(depot);
    var t = champ("textarea", "texte", T("inspiration.capture.texte"), { rows: "3" });
    E.texte = t.c; s1.appendChild(t.l);
    var src = el("div", { style: "display:grid;grid-template-columns:1fr 1fr;gap:8px" });
    var a = champ("input", "source", T("inspiration.capture.source"), { type: "text", maxlength: "300" });
    var b = champ("input", "lien", T("inspiration.capture.lien"), { type: "text", maxlength: "300" });
    E.source = a.c; E.lien = b.c; src.appendChild(a.l); src.appendChild(b.l);
    s1.appendChild(src);
    var l2 = el("div", { style: S.ligne });
    l2.appendChild(el("span", { style: S.note }, T("inspiration.capture.langue")));
    E.langue = el("select", { "data-dz-insp": "langue", style: S.champ + ";width:auto" });
    ["auto", "fr", "en"].forEach(function (k) { var o = el("option", { value: k }, T("inspiration.langue." + k)); E.langue.appendChild(o); });
    E.langue.value = "auto";
    E.lire = bouton("lire", T("inspiration.capture.lire"), S.ok);
    l2.appendChild(E.langue); l2.appendChild(E.lire);
    s1.appendChild(l2);
    E.lu = el("div", { "data-dz-insp": "lu", style: "display:flex;flex-direction:column;gap:4px", hidden: "" });
    s1.appendChild(E.lu);

    /* 2. matière et angles */
    E.s2 = section(E, "analyse");
    montrer(E.s2, false);
    var l3 = el("label", { style: S.ligne + ";font-size:12px" });
    E.avecImage = el("input", { type: "checkbox", "data-dz-insp": "avec-image" });
    l3.appendChild(E.avecImage); l3.appendChild(el("span", null, T("inspiration.analyse.image")));
    E.ligneImage = l3;
    E.s2.appendChild(l3);
    E.analyser = bouton("analyser", T("inspiration.analyse.bouton", { usd: "…" }), S.ok);
    E.s2.appendChild(E.analyser);
    E.matiere = el("div", { "data-dz-insp": "matiere", style: "display:flex;flex-direction:column;gap:2px;font-size:12px" });
    E.angles = el("div", { "data-dz-insp": "angles", style: "display:flex;flex-direction:column;gap:6px" });
    E.s2.appendChild(E.matiere); E.s2.appendChild(E.angles);

    /* 3. devis */
    E.s3 = section(E, "devis");
    montrer(E.s3, false);
    var l4 = el("label", { style: S.ligne + ";font-size:12px" });
    E.avecVisuel = el("input", { type: "checkbox", "data-dz-insp": "avec-visuel" });
    E.avecVisuel.checked = true;
    l4.appendChild(E.avecVisuel); l4.appendChild(el("span", null, T("inspiration.devis.visuel")));
    E.s3.appendChild(l4);
    E.lignesDevis = el("div", { "data-dz-insp": "devis", style: "display:flex;flex-direction:column;gap:2px;font-size:12px" });
    E.s3.appendChild(E.lignesDevis);
    E.s3.appendChild(el("div", { style: S.note }, T("inspiration.devis.jamais_capte")));
    E.s3.appendChild(el("div", { style: S.note }, T("inspiration.devis.animation")));
    E.generer = bouton("generer", T("inspiration.generer.bouton", { usd: "…" }), S.ok);
    E.s3.appendChild(E.generer);

    /* 4. brouillon */
    E.s4 = section(E, "brouillon");
    montrer(E.s4, false);
    var c1 = champ("input", "titre", T("inspiration.brouillon.champ_titre"), { type: "text", maxlength: "200" });
    var c2 = champ("input", "accroche", T("inspiration.brouillon.accroche"), { type: "text", maxlength: "1000" });
    var c3 = champ("textarea", "legende", T("inspiration.brouillon.legende"), { rows: "5" });
    E.titre = c1.c; E.accroche = c2.c; E.legende = c3.c;
    E.s4.appendChild(c1.l); E.s4.appendChild(c2.l); E.s4.appendChild(c3.l);
    E.visuel = el("div", { "data-dz-insp": "visuel", style: S.ligne + ";font-size:12px" });
    E.s4.appendChild(E.visuel);
    E.garde = el("div", { "data-dz-insp": "garde", style: "font-size:12px" });
    E.s4.appendChild(E.garde);
    E.creer = bouton("creer", T("inspiration.brouillon.creer"), S.ok);
    E.s4.appendChild(E.creer);
    E.fait = el("div", { "data-dz-insp": "fait", style: "display:flex;flex-direction:column;gap:3px;font-size:12.5px", hidden: "" });
    E.s4.appendChild(E.fait);

    E.etat = el("div", { "data-dz-insp": "etat", style: S.etat, role: "status" });
    E.corps.appendChild(E.etat);
    var pied = el("div", { style: S.pied });
    E.fermer = bouton("fermer", T("inspiration.boite.fermer"));
    pied.appendChild(E.fermer);
    boite.appendChild(pied);
    E.voile = voile;

    /* événements */
    E.choisir.addEventListener("click", function () { E.entree.click(); });
    E.entree.addEventListener("change", function () { prendre(E, (E.entree.files || [])[0]); });
    E.retirer.addEventListener("click", function () { E.image = null; majImage(E); });
    depot.addEventListener("dragover", function (e) { if (e.preventDefault) e.preventDefault(); });
    depot.addEventListener("drop", function (e) {
      if (e.preventDefault) e.preventDefault();
      var fs = (e.dataTransfer && e.dataTransfer.files) || [];
      prendre(E, fs[0]);
    });
    E.lire.addEventListener("click", function () { capter(E); });
    E.avecImage.addEventListener("change", function () { devisAnalyse(E); });
    E.analyser.addEventListener("click", function () { analyser(E); });
    E.avecVisuel.addEventListener("change", function () { if (E.angle != null) devisContenu(E); });
    E.generer.addEventListener("click", function () { generer(E); });
    E.creer.addEventListener("click", function () { creer(E); });
    E.fermer.addEventListener("click", function () { fermer(E, E.resultat || null); });
    voile.addEventListener("keydown", function (e) { clavier(E, e); });
    E.coller = function (e) {
      var items = (e && e.clipboardData && e.clipboardData.files) || [];
      if (items[0] && accepte(items[0]) && !E.occupe) { if (e.preventDefault) e.preventDefault(); prendre(E, items[0]); }
    };
    document.addEventListener("paste", E.coller);
    (document.body || document.documentElement).appendChild(voile);
    try { E.choisir.focus(); } catch (e) { /* pas de focus possible */ }
  }

  function prendre(E, f) {
    if (!f || E.occupe) return;
    if (!accepte(f)) { dire(E, T("inspiration.capture.refus_type"), true); return; }
    E.image = f;
    dire(E, "");
    majImage(E);
  }
  function majImage(E) {
    E.nomFichier.textContent = E.image ? String(E.image.name || "image") : "";
    montrer(E.retirer, !!E.image);
  }

  /* ---- clavier, verrou ------------------------------------------------------------------------------------------- */
  function focalisables(n, out) {
    out = out || [];
    if (!n || (n.hasAttribute && n.hasAttribute("hidden"))) return out;
    var tag = String(n.tagName || "").toUpperCase();
    if ((tag === "BUTTON" || tag === "SELECT" || tag === "TEXTAREA" || (tag === "INPUT" && n.getAttribute("type") !== "file"))
        && !n.hasAttribute("disabled")) out.push(n);
    Array.prototype.forEach.call(n.children || [], function (c) { focalisables(c, out); });
    return out;
  }
  function clavier(E, e) {
    if (!e) return;
    if (e.key === "Escape") { fermer(E, E.resultat || null); return; }
    if (e.key !== "Tab") return;
    var liste = focalisables(E.voile);
    if (!liste.length) { if (e.preventDefault) e.preventDefault(); return; }
    var i = liste.indexOf(document.activeElement), cible = null;
    if (i < 0) cible = e.shiftKey ? liste[liste.length - 1] : liste[0];
    else if (e.shiftKey && i === 0) cible = liste[liste.length - 1];
    else if (!e.shiftKey && i === liste.length - 1) cible = liste[0];
    if (cible) { if (e.preventDefault) e.preventDefault(); try { cible.focus(); } catch (x) { /* caché */ } }
  }
  function tous(n, out) {
    out = out || [];
    if (!n) return out;
    out.push(n);
    Array.prototype.forEach.call(n.children || [], function (c) { tous(c, out); });
    return out;
  }
  /* un appel PAYANT (ou la lecture) : tout est grisé, la boîte ne se ferme pas ; à la fin, chaque bouton reprend son état */
  function verrouiller(E, oui, voile) {
    E.occupe = !!oui;
    montrer(E.voileOccupe, !!oui && voile !== false);
    tous(E.voile).forEach(function (n) {
      var tag = String(n.tagName || "").toUpperCase();
      if (tag === "BUTTON" || tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
        if (oui) { if (!n.hasAttribute("disabled")) { n.setAttribute("data-dz-insp-verrou", ""); griser(n, true); } }
        else if (n.hasAttribute("data-dz-insp-verrou")) { n.removeAttribute("data-dz-insp-verrou"); griser(n, false); }
      }
    });
  }

  function fermer(E, valeur) {
    if (!E || E.ferme || E.occupe) return;
    E.ferme = true;
    try { document.removeEventListener("paste", E.coller); } catch (e) { /* vieux moteur */ }
    if (E.voile.parentNode) E.voile.parentNode.removeChild(E.voile);
    if (courant === E) courant = null;
    E.resoudre(valeur);
  }

  /* ---- en-tête : pour qui, récents ------------------------------------------------------------------------------- */
  function pourQui(E, j) {
    if (!j || !j.espace) return;
    var p = j.projet || {};
    var canaux = (p.canaux || []).map(function (c) { return String(c.libelle || c.plateforme || ""); }).filter(Boolean);
    E.pourQui.textContent = T("inspiration.pour_qui.texte", {
      espace: String(j.espace.nom || j.espace.id || ""),
      projet: p.nom ? String(p.nom) : T("inspiration.pour_qui.sans_projet"),
      canaux: canaux.length ? canaux.join(", ") : T("inspiration.pour_qui.sans_canal")
    });
    E.canauxTexte = canaux.length ? canaux.join(", ") : T("inspiration.pour_qui.sans_canal");
    montrer(E.client, j.espace.mode === "valide_par_client");
  }
  function recents(E, liste) {
    vider(E.recents);
    liste = (liste || []).slice(0, 5);
    montrer(E.recents, liste.length > 0);
    if (!liste.length) return;
    E.recents.appendChild(el("div", { style: S.titre }, T("inspiration.recents.titre")));
    liste.forEach(function (x) {
      var l = el("div", { "data-dz-insp": "recent", style: S.ligne + ";font-size:12px" });
      var src = (x.source && (x.source.libelle || x.source.lien)) || T("inspiration.recents.sans_source");
      l.appendChild(el("span", null, T("inspiration.recents.ligne", { date: String(x.cree || "").slice(0, 10), source: String(src),
        n: (x.brouillons || []).length })));
      var b = bouton("reprendre", T("inspiration.recents.reprendre"), "min-width:0;height:22px;padding:0 6px");
      b.addEventListener("click", function () { reprendre(E, x.id); });
      l.appendChild(b);
      E.recents.appendChild(l);
    });
  }
  async function entete(E) {
    try {
      var r = await appel("GET", BASE);
      if (E.ferme || !r.R.ok) return;
      pourQui(E, r.j);
      recents(E, r.j && r.j.inspirations);
    } catch (e) { /* l'en-tête n'empêche rien */ }
  }
  async function reprendre(E, id) {
    if (E.occupe) return;
    try {
      var r = await appel("GET", BASE + "/" + encodeURIComponent(id));
      if (E.ferme) return;
      if (!r.R.ok) { dire(E, T("inspiration.boite.erreur", { msg: detail(r.j, r.R.status) }), true); return; }
      montrerCapture(E, r.j);
      if (r.j.analyse) montrerAnalyse(E, r.j.analyse);
    } catch (e) { dire(E, T("inspiration.boite.erreur", { msg: String((e && e.message) || e) }), true); }
  }

  /* ---- 1. capter --------------------------------------------------------------------------------------------------- */
  async function capter(E) {
    if (E.occupe) return;
    var texte = String(E.texte.value || "");
    if (!E.image && !texte.trim()) { dire(E, T("inspiration.capture.vide"), true); return; }
    var fd = new FormData();
    if (E.image) fd.append("image", E.image, E.image.name || "capture");
    fd.append("texte", texte);
    fd.append("source_libelle", String(E.source.value || ""));
    fd.append("source_lien", String(E.lien.value || ""));
    fd.append("langue", E.langue.value || "auto");
    verrouiller(E, true, false);
    dire(E, T("inspiration.capture.lecture"));
    try {
      var r = await appel("POST", BASE + "/capter", fd);
      if (E.ferme) return;
      if (!r.R.ok) { dire(E, T("inspiration.boite.erreur", { msg: detail(r.j, r.R.status) }), true); return; }
      dire(E, "");
      montrerCapture(E, r.j);
    } catch (e) {
      dire(E, T("inspiration.boite.erreur", { msg: String((e && e.message) || e) }), true);
    } finally { verrouiller(E, false); }
  }
  function montrerCapture(E, j) {
    E.rec = j;
    E.iid = j.id;
    E.analyse = null; E.angle = null; E.carte = null; E.visuelNom = ""; E.resultat = null;
    if (j.espace) pourQui(E, j);
    vider(E.lu);
    montrer(E.lu, true);
    var mots = String(j.texte_capte || "").split(/\s+/).filter(Boolean).length;
    if (j.texte_capte) {
      E.lu.appendChild(el("div", { style: S.note }, T("inspiration.capture.lue", { n: mots })));
      E.lu.appendChild(el("pre", { "data-dz-insp": "texte-lu", style: S.lu }, String(j.texte_capte)));
    }
    if (j.ocr && j.ocr.raison) E.lu.appendChild(el("div", { "data-dz-insp": "ocr-absent", style: S.alerte }, T("inspiration.capture.ocr_absent", { raison: String(j.ocr.raison) })));
    if ((j.palette || []).length) {
      var l = el("div", { "data-dz-insp": "palette", style: S.ligne });
      l.appendChild(el("span", { style: S.note }, T("inspiration.capture.palette")));
      j.palette.forEach(function (c) {
        if (/^#[0-9a-fA-F]{6}$/.test(String(c))) l.appendChild(el("span", { title: String(c), style: S.pastille + ";background:" + c }));
      });
      E.lu.appendChild(l);
    }
    montrer(E.s2, true);
    montrer(E.ligneImage, !!j.image);
    E.avecImage.checked = false;
    vider(E.matiere); vider(E.angles);
    montrer(E.s3, false); montrer(E.s4, false); montrer(E.fait, false);
    devisAnalyse(E);
  }

  /* ---- 2. analyse (payante) ---------------------------------------------------------------------------------------- */
  async function devisAnalyse(E) {
    if (!E.iid) return;
    var id = E.iid, avec = !!E.avecImage.checked;
    E.devisA = null;
    E.analyser.textContent = T("inspiration.analyse.bouton", { usd: "…" });
    griser(E.analyser, true);
    try {
      var r = await appel("GET", BASE + "/" + encodeURIComponent(id) + "/devis-analyse?image=" + (avec ? 1 : 0) + "&langue=" + langue());
      if (E.ferme || E.iid !== id || !!E.avecImage.checked !== avec) return;
      if (!r.R.ok) { dire(E, T("inspiration.boite.erreur", { msg: detail(r.j, r.R.status) }), true); return; }
      if (!r.j.disponible) { dire(E, T("inspiration.analyse.indispo", { raison: String(r.j.raison || "") }), true); return; }
      E.devisA = r.j;
      E.analyser.textContent = T("inspiration.analyse.bouton", { usd: usd(r.j.usd) });
      if (!E.occupe) griser(E.analyser, false);
    } catch (e) { dire(E, T("inspiration.boite.erreur", { msg: String((e && e.message) || e) }), true); }
  }
  function confirmer(msg) {
    var d = window.__dzDialogue;
    if (!d || typeof d.confirmer !== "function") return Promise.resolve(false);
    return d.confirmer(msg, { danger: false });
  }
  async function analyser(E) {
    if (E.occupe || !E.iid || !E.devisA) return;
    var montant = E.devisA.usd, avec = !!E.avecImage.checked;
    if (!(await confirmer(T("inspiration.analyse.confirmer", { usd: usd(montant) })))) return;
    if (E.ferme) return;
    verrouiller(E, true);
    try {
      var r = await appel("POST", BASE + "/" + encodeURIComponent(E.iid) + "/analyse",
        { max_usd: montant, avec_image: avec, langue: langue(), nouvelle: !!(E.rec && E.rec.analyse) });
      if (r.R.status === 409 && r.j && r.j.detail && r.j.detail.code === "cout") {
        E.devisA = Object.assign({}, E.devisA, { usd: Number(r.j.detail.usd) || 0 });
        E.analyser.textContent = T("inspiration.analyse.bouton", { usd: usd(E.devisA.usd) });
        dire(E, T("inspiration.cout.change", { usd: usd(E.devisA.usd) }), true);
        return;
      }
      if (!r.R.ok) { dire(E, T("inspiration.boite.erreur", { msg: detail(r.j, r.R.status) }), true); return; }
      dire(E, r.j.deja_payee ? T("inspiration.analyse.deja") : "");
      if (E.rec) E.rec.analyse = r.j;
      montrerAnalyse(E, r.j);
    } catch (e) {
      dire(E, T("inspiration.boite.erreur", { msg: String((e && e.message) || e) }), true);
    } finally { verrouiller(E, false); }
  }
  function montrerAnalyse(E, a) {
    E.analyse = a;
    vider(E.matiere); vider(E.angles);
    var m = a.matiere || {};
    if (m.ton) E.matiere.appendChild(el("div", null, T("inspiration.matiere.ton", { v: String(m.ton) })));
    if (m.structure) E.matiere.appendChild(el("div", null, T("inspiration.matiere.structure", { v: String(m.structure) })));
    if ((m.idees || []).length) E.matiere.appendChild(el("div", null, T("inspiration.matiere.idees", { v: m.idees.map(String).join(" · ") })));
    if (m.composition) E.matiere.appendChild(el("div", null, T("inspiration.matiere.composition", { v: String(m.composition) })));
    (a.angles || []).forEach(function (x, i) {
      var c = el("div", { "data-dz-insp": "angle", "data-index": String(i), style: S.angle });
      c.appendChild(el("strong", null, String(x.titre || "")));
      if (x.accroche) c.appendChild(el("div", null, String(x.accroche)));
      if (x.idee) c.appendChild(el("div", { style: S.note }, String(x.idee)));
      var al = x.alertes || [];
      if (al.indexOf("copie") >= 0) c.appendChild(el("div", { "data-dz-insp": "alerte", style: S.alerte }, T("inspiration.angle.alerte_copie")));
      if (al.indexOf("interdits") >= 0) c.appendChild(el("div", { "data-dz-insp": "alerte", style: S.alerte }, T("inspiration.angle.alerte_interdits", { mots: (x.interdits || []).join(", ") })));
      var b = bouton("choisir-angle", T("inspiration.angle.choisir"), "align-self:flex-start");
      if (al.length) griser(b, true);
      b.addEventListener("click", function () { choisirAngle(E, i); });
      c.appendChild(b);
      E.angles.appendChild(c);
    });
  }

  /* ---- 3. devis du contenu, génération (payante) ------------------------------------------------------------------ */
  function choisirAngle(E, i) {
    if (E.occupe) return;
    E.angle = i;
    tous(E.angles).forEach(function (n) {
      if (n.getAttribute && n.getAttribute("data-dz-insp") === "angle") {
        n.setAttribute("style", S.angle + (n.getAttribute("data-index") === String(i) ? ";" + S.angleChoisi : ""));
      }
    });
    montrer(E.s3, true);
    montrer(E.s4, false); montrer(E.fait, false);
    devisContenu(E);
  }
  async function devisContenu(E) {
    var id = E.iid, angle = E.angle, avec = !!E.avecVisuel.checked;
    E.carte = null;
    vider(E.lignesDevis);
    E.generer.textContent = T("inspiration.generer.bouton", { usd: "…" });
    griser(E.generer, true);
    try {
      var r = await appel("POST", BASE + "/" + encodeURIComponent(id) + "/devis", { angle: angle, image: avec, langue: langue() });
      if (E.ferme || E.iid !== id || E.angle !== angle || !!E.avecVisuel.checked !== avec) return;
      if (!r.R.ok) { dire(E, T("inspiration.boite.erreur", { msg: detail(r.j, r.R.status) }), true); return; }
      E.carte = r.j;
      var a = r.j.arguments || {};
      E.lignesDevis.appendChild(el("div", null, T("inspiration.devis.ligne_texte", { usd: usd(a.texte && a.texte.usd) })));
      if (a.image) E.lignesDevis.appendChild(el("div", null, T("inspiration.devis.ligne_visuel", { modele: String((a.image.corps || {}).model || ""), usd: usd(a.image.usd) })));
      E.lignesDevis.appendChild(el("div", { style: "font-weight:600" }, T("inspiration.devis.total", { usd: usd(a.usd) })));
      if (a.texte && a.texte.disponible === false) { dire(E, T("inspiration.analyse.indispo", { raison: String(a.texte.raison || "") }), true); return; }
      E.generer.textContent = T("inspiration.generer.bouton", { usd: usd(a.usd) });
      if (!E.occupe) griser(E.generer, false);
    } catch (e) { dire(E, T("inspiration.boite.erreur", { msg: String((e && e.message) || e) }), true); }
  }
  async function generer(E) {
    if (E.occupe || !E.carte) return;
    var a = E.carte.arguments || {}, img = a.image;
    if (img && img.route !== ROUTE_IMAGE) { dire(E, T("inspiration.boite.erreur", { msg: String(img.route) }), true); return; }
    var cle = img ? "inspiration.generer.confirmer_tout" : "inspiration.generer.confirmer_texte";
    if (!(await confirmer(T(cle, { usd: usd(a.usd) })))) return;
    if (E.ferme) return;
    verrouiller(E, true);
    var red = null;
    try {
      var r = await appel("POST", BASE + "/" + encodeURIComponent(E.iid) + "/redaction",
        { angle: E.angle, max_usd: (a.texte && a.texte.usd) || 0, langue: langue() });
      if (r.R.status === 409 && r.j && r.j.detail && r.j.detail.code === "cout") {
        dire(E, T("inspiration.cout.change", { usd: usd(r.j.detail.usd) }), true);
        verrouiller(E, false);
        await devisContenu(E);
        return;
      }
      if (!r.R.ok) { dire(E, T("inspiration.boite.erreur", { msg: detail(r.j, r.R.status) }), true); return; }
      red = r.j;
      dire(E, "");
      E.visuelNom = "";
      if (img) {
        try {
          var v = await appel("POST", ROUTE_IMAGE, img.corps || {});
          if (!v.R.ok) dire(E, T("inspiration.visuel.echec", { msg: detail(v.j, v.R.status) }), true);
          else E.visuelNom = nomImage(v.j);
        } catch (e) { dire(E, T("inspiration.visuel.echec", { msg: String((e && e.message) || e) }), true); }
      }
    } catch (e) {
      dire(E, T("inspiration.boite.erreur", { msg: String((e && e.message) || e) }), true);
    } finally { if (E.occupe) verrouiller(E, false); }
    if (red) montrerBrouillon(E, red);
  }

  /* ---- 4. brouillon ------------------------------------------------------------------------------------------------- */
  function montrerGarde(E, g, interdits) {
    vider(E.garde);
    if (g) {
      E.garde.appendChild(el("div", { "data-dz-insp": "proximite" }, T("inspiration.garde.ok", { p: g.proximite || 0, n: g.suite || 0 })));
      if (g.ok === false) E.garde.appendChild(el("div", { "data-dz-insp": "copie", style: S.alerte }, T("inspiration.garde.copie", { extrait: String(g.extrait || ""), n: g.suite || 0 })));
    }
    if ((interdits || []).length) E.garde.appendChild(el("div", { "data-dz-insp": "interdits", style: S.alerte }, T("inspiration.garde.interdits", { mots: interdits.join(", ") })));
  }
  function montrerBrouillon(E, red) {
    montrer(E.s4, true);
    montrer(E.fait, false);
    E.titre.value = String(red.titre || "");
    E.accroche.value = String(red.accroche || "");
    var tags = (red.hashtags || []).join(" ");
    E.legende.value = String(red.legende || "") + (tags ? "\n\n" + tags : "");
    vider(E.visuel);
    if (E.visuelNom) {
      E.visuel.appendChild(el("img", { "data-dz-insp": "visuel-img", src: "/api/images/" + encodeURIComponent(E.visuelNom), alt: "", style: S.apercu }));
      E.visuel.appendChild(el("span", null, T("inspiration.brouillon.visuel", { nom: E.visuelNom })));
    } else {
      E.visuel.appendChild(el("span", { style: S.note }, T("inspiration.brouillon.sans_visuel")));
    }
    montrerGarde(E, red.garde, red.interdits);
    griser(E.creer, false);
  }
  async function creer(E) {
    if (E.occupe || !E.iid) return;
    verrouiller(E, true, false);
    try {
      var r = await appel("POST", BASE + "/" + encodeURIComponent(E.iid) + "/brouillon", {
        titre: String(E.titre.value || ""), accroche: String(E.accroche.value || ""), legende: String(E.legende.value || ""),
        visuel: E.visuelNom || null });
      if (E.ferme) return;
      if (!r.R.ok) {
        var d = r.j && r.j.detail;
        if (d && typeof d === "object" && (d.garde || d.interdits)) montrerGarde(E, d.garde, d.interdits);
        dire(E, detail(r.j, r.R.status), true);
        return;
      }
      var p = r.j.post || {};
      E.resultat = { post: p };
      dire(E, "");
      vider(E.fait);
      montrer(E.fait, true);
      E.fait.appendChild(el("div", { "data-dz-insp": "statut" }, p.status === "a_valider" ? T("inspiration.brouillon.a_valider")
        : T("inspiration.brouillon.cree", { canaux: (p.channels || []).join(", ") || E.canauxTexte || "" })));
      E.fait.appendChild(el("div", { style: S.note }, T("inspiration.brouillon.source")));
      try { window.dispatchEvent(new CustomEvent("deepotus:schedule-recharger")); } catch (e) { /* l'écran se rechargera seul */ }
    } catch (e) {
      dire(E, T("inspiration.boite.erreur", { msg: String((e && e.message) || e) }), true);
    } finally {
      verrouiller(E, false);
      if (E.resultat) griser(E.creer, true);
    }
  }

  function ouvrir() {
    if (courant && courant.occupe) return Promise.resolve(null);
    if (courant) fermer(courant, null);
    return new Promise(function (resoudre) {
      var E = { resoudre: resoudre, ferme: false, occupe: false, image: null, iid: null, rec: null, devisA: null,
                analyse: null, angle: null, carte: null, visuelNom: "", resultat: null, canauxTexte: "" };
      courant = E;
      construire(E);
      entete(E);
    });
  }

  window.__dzInspiration = { ouvrir: ouvrir };
})();
