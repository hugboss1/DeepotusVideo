/* dz-blender-scene.js — « Blender ouvert » : le pont Scène Blender dans la fiche d'un plan (t331, A1 du lot Scenario,
   29/10/2026, spec docs/superpowers/specs/2026-10-27-scenario-explorations-design.md). SOURCE :
   frontend/shared/dz-blender-scene.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-blender-scene.js, servie à
   /shared/dz-blender-scene.js, chargée par une balise classique dans la page de l'Atelier (frontend/atelier/index.html)
   AVANT dz-passes-plan.js. Bancs : backend/tests/test_blender_scene_ecran.py (copie, balises, textes FR/EN) et
   frontend/shared/qa/blender_scene.test.mjs (comportement sur un faux DOM).

   window.__dzBlenderScene.monter(hote, {shot, numero, toast}) -> la section posée dans la boîte « Passes Blender »
     (dz-passes-plan.js l'appelle à la construction). Le Blender OUVERT de l'utilisateur, par mcp-for-blender en mode
     sûr, sur la boucle locale :
       « Envoyer vers Blender »  POST /api/blender/plan/{id}/envoyer {elements} — les GABARITS du serveur (caméra et
                                 focale, éclairage 3 points, blocking coloré, clés de caméra) nourris par la scène du
                                 Plateau du plan ; la page n'envoie que des cases cochées, jamais du code ;
       « Regarder la scène »     POST /api/blender/regarder {mode} → la capture (GET /api/blender/regard/{id}), sa
                                 légende et les licences des assets importés visibles ; « Garder dans la Bibliothèque »
                                 → POST …/garder {plan} ;
       « Retirer de Blender »    POST /api/blender/nettoyer — seulement la collection DZ_Deepotus posée par l'app.
     t332 (A2) — l'ALLER-RETOUR avec le Plateau (même section, sous-bloc « Plateau ↔ Blender ») :
       « Envoyer le plan vers Blender »  POST /api/blender/plan/{id}/aller {} — caméra, focale, clés et maquette GLB ;
       « Reprendre depuis Blender »      POST …/reprendre {} — caméras et objets DZ_ relus, copie .blend, vignette en
                                         Bibliothèque ; le dernier retour est relu au montage (GET …/retours) ;
       « Appliquer au Plateau »          POST …/retour/{rid}/appliquer {camera} (avant/après) puis, après confirmation,
                                         {camera, confirmer: true} — seule écriture au Plateau.
     Gratuit : rien n'est généré ni acheté (dit avant le clic). Exe absent / Blender fermé : le 503 du serveur dit quoi
     faire, les boutons restent cliquables.
   CHARTE : celle de dz-passes-plan.js (aucun arrondi, IBM Plex Mono en capitales, jetons --srf-* / --brd-* / --txt-*).
   Textes : clés blenderscene.* (frontend/shared/i18n/blenderscene.json). Vanilla DOM, aucun innerHTML. */
(function () {
  "use strict";
  if (window.__dzBlenderScene) return;

  var ELEMENTS = ["camera", "eclairage", "blocking", "cles"];
  var MODES = ["camera", "viewport", "angles"];
  var S = {
    section: "display:flex;flex-direction:column;gap:6px;padding-top:10px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
    titre: "font:10px 'IBM Plex Mono',monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    note: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    ligne: "display:flex;align-items:center;gap:10px;flex-wrap:wrap",
    coche: "display:inline-flex;align-items:center;gap:4px;font-size:12px",
    prix: "font-size:13px;color:var(--green,#3fb950)",
    ok: "color:var(--green,#3fb950)",
    ko: "color:var(--amber,#f0b429)",
    erreur: "color:var(--red,#e5484d);font-size:12px",
    btn: "min-width:88px;height:28px;padding:0 12px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit",
    primaire: "background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6);color:var(--accent-ink,#ffffff)",
    choix: "height:28px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:inherit;font:inherit",
    image: "display:block;width:100%;max-height:340px;object-fit:contain;background:#000;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138))"
  };

  function T(cle, v) { return typeof window.dzT === "function" ? window.dzT(cle, v) : cle; }
  function el(tag, attrs, texte) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (texte != null) n.textContent = texte;
    return n;
  }
  function bouton(marque, texte, style) {
    return el("button", { type: "button", "data-dz-blender": marque, style: S.btn + (style ? ";" + style : "") }, texte);
  }
  function montrer(n, oui) { if (oui) n.removeAttribute("hidden"); else n.setAttribute("hidden", ""); }
  function griser(n, oui) { if (oui) n.setAttribute("disabled", ""); else n.removeAttribute("disabled"); }
  function detail(j, status) {
    var d = j && j.detail;
    if (typeof d === "string" && d) return d;
    if (d && typeof d.message === "string") return d.message;
    return "HTTP " + status;
  }
  async function lireJson(R) { try { return await R.json(); } catch (e) { return null; } }
  async function appel(url, corps) {
    var R = await fetch(url, corps === undefined ? undefined
      : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps) });
    var j = await lireJson(R);
    if (!R.ok) throw new Error(detail(j, R.status));
    return j;
  }

  function monter(hote, opts) {
    opts = opts || {};
    if (!hote || !opts.shot || !opts.shot.id) return null;
    var E = { opts: opts, shot: opts.shot, regard: null, occupe: false };
    var s = E.racine = el("div", { style: S.section, "data-dz-blender": "section" });
    s.appendChild(el("div", { style: S.titre }, T("blenderscene.section.titre")));
    s.appendChild(el("div", { style: S.note, "data-dz-blender": "aide" }, T("blenderscene.section.aide")));
    E.etat = el("div", { style: S.note, "data-dz-blender": "etat" }, T("blenderscene.etat.lecture"));
    s.appendChild(E.etat);

    var cases = el("div", { style: S.ligne, "data-dz-blender": "elements" });
    E.coches = {};
    ELEMENTS.forEach(function (k) {
      var lab = el("label", { style: S.coche, title: T("blenderscene.element_aide." + k) });
      var c = el("input", { type: "checkbox", "data-dz-blender": "element-" + k });
      c.checked = k !== "cles";
      lab.appendChild(c); lab.appendChild(document.createTextNode(T("blenderscene.element." + k)));
      E.coches[k] = c;
      cases.appendChild(lab);
    });
    s.appendChild(cases);
    s.appendChild(el("div", { style: S.prix, "data-dz-blender": "prix" }, T("blenderscene.section.gratuit")));

    var l1 = el("div", { style: S.ligne });
    E.btnEnvoyer = bouton("envoyer", T("blenderscene.section.envoyer"), S.primaire);
    E.btnEnvoyer.addEventListener("click", function () { envoyer(E); });
    l1.appendChild(E.btnEnvoyer);
    E.mode = el("select", { style: S.choix, "data-dz-blender": "mode", title: T("blenderscene.section.mode_titre") });
    MODES.forEach(function (m) { E.mode.appendChild(el("option", { value: m }, T("blenderscene.mode." + m))); });
    l1.appendChild(E.mode);
    E.btnRegarder = bouton("regarder", T("blenderscene.section.regarder"));
    E.btnRegarder.addEventListener("click", function () { regarder(E); });
    l1.appendChild(E.btnRegarder);
    E.btnRetirer = bouton("retirer", T("blenderscene.section.retirer"));
    E.btnRetirer.setAttribute("title", T("blenderscene.section.retirer_aide"));
    E.btnRetirer.addEventListener("click", function () { retirer(E); });
    l1.appendChild(E.btnRetirer);
    s.appendChild(l1);

    E.statut = el("div", { style: S.note, "data-dz-blender": "statut", role: "status" });
    s.appendChild(E.statut);
    E.erreur = el("div", { style: S.erreur, hidden: "", "data-dz-blender": "erreur", role: "alert" });
    s.appendChild(E.erreur);

    E.vue = el("div", { style: "display:flex;flex-direction:column;gap:6px", hidden: "", "data-dz-blender": "vue" });
    E.image = el("img", { style: S.image, alt: T("blenderscene.section.capture_alt"), "data-dz-blender": "image" });
    E.legende = el("div", { style: S.note, "data-dz-blender": "legende" });
    E.licences = el("div", { style: S.note, "data-dz-blender": "licences" });
    E.btnGarder = bouton("garder", T("blenderscene.section.garder"));
    E.btnGarder.addEventListener("click", function () { garder(E); });
    E.vue.appendChild(E.image); E.vue.appendChild(E.legende); E.vue.appendChild(E.licences); E.vue.appendChild(E.btnGarder);
    s.appendChild(E.vue);
    monterAllerRetour(E, s);
    hote.appendChild(s);
    lireEtat(E);
    lireRetours(E);
    return E;
  }

  // ── t332 (A2) : l'ALLER-RETOUR Plateau ↔ Blender. Le Plateau reste l'éditeur léger, Blender l'étage pro. ──
  function monterAllerRetour(E, s) {
    var b = el("div", { style: "display:flex;flex-direction:column;gap:6px;padding-top:8px;border-top:1px dashed var(--brd-soft,var(--stroke,#222830))", "data-dz-blender": "allerretour" });
    b.appendChild(el("div", { style: S.titre }, T("blenderscene.ar.titre")));
    b.appendChild(el("div", { style: S.note }, T("blenderscene.ar.aide")));
    b.appendChild(el("div", { style: S.prix, "data-dz-blender": "ar-prix" }, T("blenderscene.ar.gratuit")));
    var l = el("div", { style: S.ligne });
    E.btnAller = bouton("aller", T("blenderscene.ar.aller"), S.primaire);
    E.btnAller.setAttribute("title", T("blenderscene.ar.aller_aide"));
    E.btnAller.addEventListener("click", function () { aller(E); });
    E.btnReprendre = bouton("reprendre", T("blenderscene.ar.reprendre"));
    E.btnReprendre.setAttribute("title", T("blenderscene.ar.reprendre_aide"));
    E.btnReprendre.addEventListener("click", function () { reprendre(E); });
    l.appendChild(E.btnAller); l.appendChild(E.btnReprendre);
    b.appendChild(l);
    E.retour = el("div", { style: "display:flex;flex-direction:column;gap:6px", hidden: "", "data-dz-blender": "retour" });
    E.retourImage = el("img", { style: S.image, alt: T("blenderscene.ar.vignette_alt"), "data-dz-blender": "retour-image" });
    E.retourResume = el("div", { style: S.note, "data-dz-blender": "retour-resume" });
    E.retourAvantApres = el("div", { style: "font-size:12px", "data-dz-blender": "retour-avant-apres" });
    var l2 = el("div", { style: S.ligne });
    E.retourCamera = el("select", { style: S.choix, "data-dz-blender": "retour-camera", title: T("blenderscene.ar.camera_titre") });
    E.retourCamera.addEventListener("change", function () { proposer(E); });
    E.btnAppliquer = bouton("appliquer", T("blenderscene.ar.appliquer"), S.primaire);
    E.btnAppliquer.setAttribute("title", T("blenderscene.ar.appliquer_aide"));
    E.btnAppliquer.addEventListener("click", function () { appliquer(E); });
    E.lienBlend = el("a", { "data-dz-blender": "retour-blend", style: "font-size:12px;color:var(--accent,#2b6fd6)" }, T("blenderscene.ar.blend"));
    l2.appendChild(E.retourCamera); l2.appendChild(E.btnAppliquer); l2.appendChild(E.lienBlend);
    [E.retourImage, E.retourResume, E.retourAvantApres, l2].forEach(function (n) { E.retour.appendChild(n); });
    b.appendChild(E.retour);
    s.appendChild(b);
  }

  function mm(v) { return v == null ? "?" : String(Math.round(v)); }
  function montrerRetour(E, r) {
    E.dernier = r;
    montrer(E.retour, true);
    if (r.vignette_url) { E.retourImage.setAttribute("src", r.vignette_url + "?v=" + encodeURIComponent(r.id)); montrer(E.retourImage, true); }
    else montrer(E.retourImage, false);
    E.retourResume.textContent = T("blenderscene.ar.resume", { date: (r.date || "").replace("T", " "),
      c: (r.cameras || []).length, o: (r.objets || []).length, version: r.version || "?" })
      + (r.bibliotheque ? " " + T("blenderscene.ar.bibliotheque", { nom: r.bibliotheque }) : "");
    E.lienBlend.setAttribute("href", r.blend_url);
    E.lienBlend.setAttribute("download", r.blend_nom || "");
    E.retourCamera.textContent = "";
    (r.cameras || []).filter(function (c) { return c.perspective; }).forEach(function (c) {
      var o = el("option", { value: c.nom }, c.nom + (c.cles ? " · " + T("blenderscene.ar.cles", { n: c.cles }) : ""));
      if (c.nom === r.camera_nom) o.setAttribute("selected", "");
      E.retourCamera.appendChild(o);
    });
    E.retourCamera.value = r.camera_nom || "";
    peindreProposition(E, r.proposition, r.proposition_erreur);
  }
  function peindreProposition(E, p, erreur) {
    E.proposition = p || null;
    griser(E.btnAppliquer, !p);
    if (!p) { E.retourAvantApres.textContent = T("blenderscene.ar.sans_proposition", { msg: erreur || "?" }); return; }
    E.retourAvantApres.textContent = T("blenderscene.ar.avant_apres", {
      fa: mm(p.avant.focale_mm), fb: mm(p.apres.focale_mm), ka: p.avant.keyframes, kb: p.apres.keyframes, d: p.ecart_m });
  }

  function occuperAR(E, oui, texte) {
    occuper(E, oui, texte);
    [E.btnAller, E.btnReprendre].forEach(function (b) { griser(b, oui); });
    griser(E.btnAppliquer, oui || !E.proposition);
  }
  function echecAR(E, e) { occuperAR(E, false, ""); montrer(E.erreur, true); E.erreur.textContent = T("blenderscene.section.ko", { msg: e.message }); }

  async function lireRetours(E) {
    try {
      var j = await appel("/api/blender/plan/" + encodeURIComponent(E.shot.id) + "/retours");
      if (j && j.retours && j.retours.length) montrerRetour(E, j.retours[0]);
    } catch (e) { /* aucun retour encore : rien à montrer */ }
  }

  async function aller(E) {
    if (E.occupe) return;
    occuperAR(E, true, T("blenderscene.section.envoi"));
    try {
      var j = await appel("/api/blender/plan/" + encodeURIComponent(E.shot.id) + "/aller", {});
      occuperAR(E, false, T("blenderscene.ar.envoye", { f: Math.round((j.camera || {}).focale_mm || 0), k: j.cles || 0, m: j.maquette || 0 }));
      if (E.opts.toast) E.opts.toast(T("blenderscene.section.envoye_toast"));
    } catch (e) { echecAR(E, e); }
  }

  async function reprendre(E) {
    if (E.occupe) return;
    occuperAR(E, true, T("blenderscene.section.envoi"));
    try {
      var j = await appel("/api/blender/plan/" + encodeURIComponent(E.shot.id) + "/reprendre", {});
      montrerRetour(E, j);
      occuperAR(E, false, T("blenderscene.ar.repris"));
      if (E.opts.toast) E.opts.toast(T("blenderscene.ar.repris"));
    } catch (e) { echecAR(E, e); }
  }

  function urlAppliquer(E) {
    return "/api/blender/plan/" + encodeURIComponent(E.shot.id) + "/retour/" + encodeURIComponent(E.dernier.id) + "/appliquer";
  }
  async function proposer(E) {
    if (E.occupe || !E.dernier) return;
    occuperAR(E, true, "");
    try {
      var j = await appel(urlAppliquer(E), { camera: E.retourCamera.value });
      occuperAR(E, false, "");
      peindreProposition(E, j.proposition);
      griser(E.btnAppliquer, false);
    } catch (e) { peindreProposition(E, null, e.message); occuperAR(E, false, ""); }
  }
  async function appliquer(E) {
    if (E.occupe || !E.dernier || !E.proposition) return;
    var texte = T("blenderscene.ar.confirmer", { cam: E.retourCamera.value || E.dernier.camera_nom || "?" }) + "\n" + E.retourAvantApres.textContent;
    var D = window.__dzDialogue;
    var oui = D && typeof D.confirmer === "function" ? await D.confirmer(texte) : (typeof window.confirm === "function" ? window.confirm(texte) : false);
    if (!oui) return;
    occuperAR(E, true, "");
    try {
      var j = await appel(urlAppliquer(E), { camera: E.retourCamera.value, confirmer: true });
      occuperAR(E, false, T("blenderscene.ar.applique", { n: (j.proposition || {}).keyframes ? j.proposition.keyframes.length : 0 }));
      if (E.opts.toast) E.opts.toast(T("blenderscene.ar.applique_toast"));
    } catch (e) { echecAR(E, e); }
  }

  async function lireEtat(E) {
    try {
      var j = await appel("/api/blender/etat");
      var x = j.exe || {};
      E.etat.textContent = x.trouve ? T("blenderscene.etat.pret", { port: x.port || 9876 }) : (j.installer || T("blenderscene.etat.absent"));
      E.etat.setAttribute("style", S.note + ";" + (x.trouve ? S.ok : S.ko));
    } catch (e) {
      E.etat.textContent = T("blenderscene.section.ko", { msg: e.message });
    }
  }

  function occuper(E, oui, texte) {
    E.occupe = oui;
    [E.btnEnvoyer, E.btnRegarder, E.btnRetirer, E.btnGarder].forEach(function (b) { griser(b, oui); });
    E.statut.textContent = texte || "";
    if (oui) montrer(E.erreur, false);
  }
  function echec(E, e) {
    occuper(E, false, "");
    montrer(E.erreur, true);
    E.erreur.textContent = T("blenderscene.section.ko", { msg: e.message });
  }

  async function envoyer(E) {
    if (E.occupe) return;
    var elements = ELEMENTS.filter(function (k) { return E.coches[k].checked; });
    if (!elements.length) { montrer(E.erreur, true); E.erreur.textContent = T("blenderscene.section.aucun"); return; }
    occuper(E, true, T("blenderscene.section.envoi"));
    try {
      var j = await appel("/api/blender/plan/" + encodeURIComponent(E.shot.id) + "/envoyer", { elements: elements });
      occuper(E, false, T("blenderscene.section.envoye", { n: j.blocking || 0, f: Math.round((j.camera || {}).focale_mm || 0) }));
      if (E.opts.toast) E.opts.toast(T("blenderscene.section.envoye_toast"));
    } catch (e) { echec(E, e); }
  }

  async function regarder(E) {
    if (E.occupe) return;
    occuper(E, true, T("blenderscene.section.capture_en_cours"));
    try {
      var j = await appel("/api/blender/regarder", { mode: E.mode.value || "camera" });
      E.regard = j;
      E.image.setAttribute("src", j.url + "?v=" + encodeURIComponent(j.id));
      E.legende.textContent = j.legende || "";
      var ls = j.licences || [];
      E.licences.textContent = ls.length ? T("blenderscene.section.licences", { liste: ls.map(function (l) {
        return (l.titre || l.id) + " — " + (l.licence || "?") + (l.auteur ? " (" + l.auteur + ")" : "");
      }).join(" ; ") }) : T("blenderscene.section.sans_licence");
      montrer(E.vue, true);
      griser(E.btnGarder, false);
      E.btnGarder.textContent = T("blenderscene.section.garder");
      occuper(E, false, "");
    } catch (e) { echec(E, e); }
  }

  async function garder(E) {
    if (E.occupe || !E.regard) return;
    occuper(E, true, "");
    try {
      var j = await appel("/api/blender/regard/" + encodeURIComponent(E.regard.id) + "/garder", { plan: E.shot.id });
      occuper(E, false, T("blenderscene.section.garde", { nom: j.nom, licence: j.licence || "" }));
      griser(E.btnGarder, true);
      E.btnGarder.textContent = T("blenderscene.section.garde_bouton");
      if (E.opts.toast) E.opts.toast(T("blenderscene.section.garde_toast"));
    } catch (e) { echec(E, e); }
  }

  async function retirer(E) {
    if (E.occupe) return;
    occuper(E, true, T("blenderscene.section.envoi"));
    try {
      var j = await appel("/api/blender/nettoyer", {});
      occuper(E, false, T("blenderscene.section.retire", { n: ((j.resume || {}).retires) || 0 }));
    } catch (e) { echec(E, e); }
  }

  window.__dzBlenderScene = { monter: monter, ELEMENTS: ELEMENTS.slice() };
})();
