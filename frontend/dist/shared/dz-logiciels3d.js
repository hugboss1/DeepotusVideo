/* dz-logiciels3d.js — Réglages › « Moteurs et logiciels 3D » (t521, 13/11/2026) : Blender, Blender MCP, Godot, Unreal Engine, Unity (lot 2 du 14/11).
   SOURCE : frontend/shared/dz-logiciels3d.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-logiciels3d.js, servie à
   /shared/dz-logiciels3d.js, chargée par une balise classique dans la SPA (frontend/dist/index.html). L'onglet est posé
   par le maillon de queue scripts/patch_bundle_dzlogiciels3d.py, qui rend un <div data-dz-logiciels3d-hote> et appelle
   window.__dzLogiciels3d.monter par une ref. Banc : backend/tests/test_logiciels3d_t521.py. Serveur :
   backend/app/services/logiciels_3d.py et les routes /api/reglages/logiciels3d (settings_routes.py).

   Une carte par logiciel : ce qu'il permet, un champ par réglage (exécutable ; dossier du projet pour Godot) avec
   « Enregistrer » (POST /api/settings/keys, appliqué à chaud), « Détecter » (propose, n'enregistre rien : « Utiliser »
   remplit le champ), « Tester » (version lue sans fenêtre, message dans la langue de l'écran) et « Guide » (chapitre
   logiciels-3d). Vanilla DOM, aucun innerHTML. Textes : clés logiciels3d.* (frontend/shared/i18n/logiciels3d.json).
   Charte : aucun arrondi, jetons --srf-* / --brd-* / --txt-* avec repli. */
(function () {
  "use strict";
  if (window.__dzLogiciels3d) return;

  var BASE = "/api/reglages/logiciels3d";
  var JSON_H = { "Content-Type": "application/json" };
  var S = {
    panneau: "display:flex;flex-direction:column;gap:14px;color:var(--txt-base,var(--ink,#cfd6e2));font:13px/1.5 system-ui,sans-serif",
    titre: "font:600 18px/1.3 system-ui,sans-serif;color:var(--txt-hi,var(--ink-strong,#e6e9ee))",
    intro: "font-size:12.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae));max-width:680px",
    cadre: "border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));background:var(--srf-panel,var(--bg-panel,#13171c));padding:12px 14px;display:flex;flex-direction:column;gap:8px",
    tete: "font:10px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    note: "font-size:12px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    ligne: "display:flex;align-items:center;gap:8px;flex-wrap:wrap",
    lib: "width:150px;flex:none;font-size:12.5px;color:var(--txt-hi,var(--ink-strong,#e6e9ee))",
    champ: "flex:1;min-width:240px;height:28px;padding:0 9px;background:var(--srf-sunken,var(--bg-base,#0d1014));border:1px solid var(--brd-soft,var(--stroke,#222830));border-radius:0;color:var(--txt-hi,var(--ink-strong,#e6e9ee));font:11.5px 'IBM Plex Mono',monospace",
    btn: "height:28px;padding:0 12px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit;display:inline-flex;align-items:center;gap:6px",
    primaire: "background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6);color:var(--accent-ink,#ffffff)",
    lien: "font-size:11.5px;color:var(--cyan,#22d3ee);text-decoration:none",
    ok: "font-size:12px;color:var(--green,#3fb950)",
    ko: "font-size:12px;color:var(--red,#e5484d)",
    attente: "font-size:12px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))"
  };

  function T(cle, v) { return typeof window.dzT === "function" ? window.dzT(cle, v) : cle; }
  function langue() { var l = typeof window.dzLang === "function" ? window.dzLang() : window.dzLang; return l === "en" ? "en" : "fr"; }
  function el(tag, attrs, texte) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (texte != null) n.textContent = texte;
    return n;
  }
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
    var b = el("button", { type: "button", "data-dz-l3d": marque, style: S.btn + (principal ? ";" + S.primaire : "") });
    if (icone) b.appendChild(glyphe(icone));
    b.appendChild(document.createTextNode(texte));
    return b;
  }
  function vider(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  async function appel(chemin, corps) {
    var r = await window.fetch(chemin, corps ? { method: "POST", headers: JSON_H, body: JSON.stringify(corps) } : {});
    var j = null;
    try { j = await r.json(); } catch (e) { j = null; }
    if (!r.ok) throw new Error((j && (j.detail || j.message)) || String(r.status));
    return j || {};
  }
  function verdict(zone, ok, texte) {
    zone.setAttribute("data-dz-l3d-verdict", ok === true ? "ok" : ok === false ? "refus" : "attente");
    zone.setAttribute("style", ok === true ? S.ok : ok === false ? S.ko : S.attente);
    zone.textContent = texte;
  }

  function champ(lid, ch, retour) {
    var ligne = el("div", { style: S.ligne, "data-dz-l3d-champ": ch.cle });
    var lab = el("div", { style: S.lib });
    lab.appendChild(el("div", {}, T(ch.genre === "projet" ? "logiciels3d.champ.projet"
                                   : ch.genre === "port" ? "logiciels3d.champ.port" : "logiciels3d.champ.exe")));
    // t521 lot 2 : l'aide du dossier de projet dit ce que chaque moteur y attend (project.godot, .uproject, Assets)
    var cleAide = ch.genre === "port" ? "logiciels3d.champ.port_aide"
                : ch.genre !== "projet" ? "logiciels3d.champ.exe_aide"
                : lid === "godot" ? "logiciels3d.champ.projet_aide" : "logiciels3d.champ.projet_aide_" + lid;
    lab.appendChild(el("div", { style: "font:10px 'IBM Plex Mono',monospace;color:var(--txt-mid,#9aa4ae)" }, ch.cle));
    ligne.appendChild(lab);
    var inp = el("input", { type: "text", style: S.champ, spellcheck: "false", "data-dz-l3d": "valeur-" + ch.cle,
                            placeholder: T(cleAide) });
    inp.value = ch.valeur || "";
    ligne.appendChild(inp);
    var b = bouton("enregistrer-" + ch.cle, T("logiciels3d.bouton.enregistrer"), "dz-action-enregistrer", true);
    b.addEventListener("click", async function () {
      b.disabled = true;
      verdict(retour, null, T("logiciels3d.etat.en_cours"));
      try {
        await appel("/api/settings/keys", { name: ch.cle, value: inp.value.trim() });
        verdict(retour, true, T("logiciels3d.etat.enregistre"));
      } catch (e) { verdict(retour, false, String(e.message || e)); }
      b.disabled = false;
    });
    ligne.appendChild(b);
    return { ligne: ligne, input: inp };
  }

  function carte(l) {
    var c = el("section", { style: S.cadre, "data-dz-l3d-carte": l.id });
    c.appendChild(el("div", { style: S.tete }, T("logiciels3d." + l.id + ".titre")));
    c.appendChild(el("div", { style: S.note }, T("logiciels3d." + l.id + ".permet")));
    var retour = el("div", { style: S.attente, role: "status", "data-dz-l3d-verdict": "" });
    var champs = {};
    (l.champs || []).forEach(function (ch) {
      var f = champ(l.id, ch, retour);
      champs[ch.genre] = f.input;
      c.appendChild(f.ligne);
    });
    var actions = el("div", { style: S.ligne });
    var bd = bouton("detecter-" + l.id, T("logiciels3d.bouton.detecter"), "dz-action-chercher");
    var bt = bouton("tester-" + l.id, T("logiciels3d.bouton.tester"), "dz-action-tester");
    var guide = el("a", { href: "/guide/" + langue() + ".html#" + (l.guide || "logiciels-3d"), target: "_blank",
                          rel: "noreferrer", style: S.lien, "data-dz-l3d": "guide-" + l.id }, T("logiciels3d.bouton.guide"));
    actions.appendChild(bd); actions.appendChild(bt); actions.appendChild(guide);
    c.appendChild(actions);
    var trouves = el("div", { style: "display:flex;flex-direction:column;gap:4px", "data-dz-l3d": "trouves-" + l.id });
    c.appendChild(trouves);
    c.appendChild(retour);

    bd.addEventListener("click", async function () {
      bd.disabled = true; vider(trouves);
      try {
        var j = await appel(BASE + "/detecter", { id: l.id });
        var cands = j.candidats || [];
        if (!cands.length) { trouves.appendChild(el("div", { style: S.note }, T("logiciels3d.etat.aucun_trouve"))); }
        else {
          trouves.appendChild(el("div", { style: S.note }, T("logiciels3d.etat.trouves")));
          cands.forEach(function (x) {
            var r = el("div", { style: S.ligne });
            r.appendChild(el("code", { style: "font:11px 'IBM Plex Mono',monospace;word-break:break-all" },
                             x.chemin + (x.version ? "  (" + x.version + ")" : "")));
            var u = bouton("utiliser", T("logiciels3d.bouton.utiliser"));
            u.addEventListener("click", function () { if (champs.exe) { champs.exe.value = x.chemin; champs.exe.focus(); } });
            r.appendChild(u);
            trouves.appendChild(r);
          });
        }
      } catch (e) { verdict(retour, false, String(e.message || e)); }
      bd.disabled = false;
    });
    bt.addEventListener("click", async function () {
      bt.disabled = true;
      verdict(retour, null, T("logiciels3d.etat.en_cours"));
      try {
        var j = await appel(BASE + "/tester", { id: l.id });
        verdict(retour, j.ok === true ? true : j.ok === false ? false : null, String(j.message || ""));
      } catch (e) { verdict(retour, false, String(e.message || e)); }
      bt.disabled = false;
    });
    return c;
  }

  function monter(hote) {
    if (!hote || hote.getAttribute("data-dz-l3d-monte") === "1") return;
    hote.setAttribute("data-dz-l3d-monte", "1");
    var p = el("div", { "data-dz-l3d": "panneau", style: S.panneau });
    p.appendChild(el("div", { style: S.titre }, T("logiciels3d.reglages.titre")));
    p.appendChild(el("div", { style: S.intro }, T("logiciels3d.reglages.intro")));
    var liste = el("div", { style: "display:flex;flex-direction:column;gap:12px" });
    p.appendChild(liste);
    hote.appendChild(p);
    appel(BASE).then(function (j) {
      (j.logiciels || []).forEach(function (l) { liste.appendChild(carte(l)); });
    }).catch(function (e) { liste.appendChild(el("div", { style: S.ko, role: "alert" }, String(e.message || e))); });
  }

  window.__dzLogiciels3d = { monter: monter };
})();
