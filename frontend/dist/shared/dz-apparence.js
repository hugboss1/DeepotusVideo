/* dz-apparence.js — la PALETTE de l'application (t382, lot « Réglages : chemins & apparence », 30/10/2026, plan
   docs/superpowers/plans/2026-10-29-finitions-esthetiques-chemins-fils-apparence.md, décision D5 : globale à l'app,
   préréglages + palette libre, un « clair » complet).
   SOURCE : frontend/shared/dz-apparence.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-apparence.js, servie à
   /shared/dz-apparence.js, chargée TÔT par une balise classique dans la SPA (frontend/dist/index.html, après
   dz-i18n.js, avant le bundle) : la palette est peinte avant le premier rendu.
   Serveur : backend/app/services/apparence.py, routes /api/reglages/apparence (le serveur fait foi : 127.0.0.1 et
   deepotus.localhost n'ont pas le même localStorage ; le localStorage n'est que le cache du premier rendu).
   Bancs : frontend/shared/qa/apparence.test.mjs, backend/tests/test_apparence_ecran.py, test_apparence.py.

   COMMENT : six jetons choisis (fond, panneau, texte, accent, succès, erreur) ; tout le reste se DÉRIVE (surfaces,
   bordures, quatre encres, encre du bouton, teintes douces, color-scheme) et s'écrit en STYLE EN LIGNE sur <html> :
   il gagne sur toute feuille (bundle, theme-v2.css, deepotus.tokens.css et ses blocs data-theme), donc les jetons de
   la charte t370 (--fg-*, résolus sur :root) suivent d'eux-mêmes. data-theme="light" | "dark" est posé avec, pour les
   règles « clair » déjà écrites par les labs. La coque peint ses cadres de MÊME ORIGINE (les labs, un cadre dans un
   cadre) au chargement de chacun ; aucun lab n'a de balise à ajouter. Deepotus sombre = RIEN d'écrit : l'app d'avant.
   La couleur de marque (--brand, le rouge du logo) n'est jamais réécrite.

   window.__dzApparence :
     PRESETS, ORDRE, JETONS ; contraste(a, b) (WCAG 2.x) ; sombre(couleurs) ; deriver(couleurs, "coque"|"lab", fort) ;
     controles(couleurs, fort) -> [{id, avant, fond, ratio, seuil, ok}] ; normaliser(etat) -> etat | null ;
     couleursDe(etat) ; lire() ; appliquer(etat, doc?) ; suivreCadre(iframe) ; choisir(etat) ; reinitialiser() ;
     synchroniser() ; monter(hote) — le panneau de Réglages › Apparence (maillon de queue patch_bundle_dzapparence :
     un <div data-dz-apparence-hote> dont la ref appelle monter), vanilla DOM, aucun innerHTML.
   Textes : clés apparence.* (frontend/shared/i18n/apparence.json). Charte : aucun arrondi, jetons sans hexadécimal. */
(function () {
  "use strict";
  if (window.__dzApparence) return;

  var CLE = "deepotus.apparence";
  var URL_API = "/api/reglages/apparence";
  var JETONS = ["fond", "panneau", "texte", "accent", "succes", "erreur"];
  // Deepotus sombre = les valeurs Cinema de theme-v2.css ; clair = le bloc data-theme="light" de deepotus.tokens.css ;
  // Deep Lab = l'ancienne direction bleue (data-direction="deep"), rouge éclairci pour l'AA sur son panneau.
  var PRESETS = {
    sombre: { couleurs: { fond: "#0a0a0c", panneau: "#151519", texte: "#f2efe9", accent: "#f0b429", succes: "#5ec8a0", erreur: "#e35d4a" } },
    clair: { couleurs: { fond: "#f2f0ec", panneau: "#ffffff", texte: "#171512", accent: "#a06a00", succes: "#1f7a5c", erreur: "#b03a28" } },
    contraste: { couleurs: { fond: "#000000", panneau: "#0b0b0b", texte: "#ffffff", accent: "#ffd23f", succes: "#5df2b0", erreur: "#ff7a66" }, fort: true },
    deeplab: { couleurs: { fond: "#02060d", panneau: "#0a1422", texte: "#e6f1ff", accent: "#00e5ff", succes: "#22c55e", erreur: "#f87171" } }
  };
  var ORDRE = ["sombre", "clair", "contraste", "deeplab"];
  // part du panneau dans --ink, --ink-soft, --ink-muted (le reste est le texte)
  var POIDS = { sombre: [0.2, 0.45, 0.65], clair: [0.15, 0.36, 0.6], fort: [0.08, 0.25, 0.45] };
  var NOIR = "#000000", BLANC = "#ffffff";

  // ── couleurs ──────────────────────────────────────────────────────────────
  function rgb(h) { return [1, 3, 5].map(function (i) { return parseInt(h.slice(i, i + 2), 16); }); }
  function hex(c) {
    return "#" + c.map(function (v) {
      var x = Math.max(0, Math.min(255, Math.round(v))).toString(16);
      return x.length < 2 ? "0" + x : x;
    }).join("");
  }
  function melange(a, b, t) {
    var x = rgb(a), y = rgb(b);
    return hex(x.map(function (v, i) { return v + (y[i] - v) * t; }));
  }
  function lum(h) {
    var c = rgb(h).map(function (v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  }
  function contraste(a, b) {
    var x = lum(a), y = lum(b);
    return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
  }
  function sombre(c) { return lum(c.fond) < 0.18; }
  function encreSur(fond) {
    var noire = melange(fond, NOIR, 0.88);
    return contraste(noire, fond) >= contraste(BLANC, fond) ? noire : BLANC;
  }

  function deriver(c, contexte, fort) {
    var s = sombre(c), w = fort ? POIDS.fort : s ? POIDS.sombre : POIDS.clair, v = {};
    v["--bg-base"] = c.fond;
    v["--bg-panel"] = c.panneau;
    v["--bg-panel-2"] = melange(c.panneau, c.texte, 0.05);
    // dans la coque, panneau 3 est la surface d'ÉLÉVATION (survol) ; dans les labs, un puits plus bas que le panneau
    v["--bg-panel-3"] = contexte === "lab" ? (s ? melange(c.fond, c.panneau, 0.5) : melange(c.fond, c.texte, 0.05))
                                           : melange(c.panneau, c.texte, 0.1);
    v["--bg-overlay"] = c.fond + "cc";
    v["--well"] = c.fond + "cc";
    v["--stroke"] = melange(c.panneau, c.texte, 0.12);
    v["--stroke-strong"] = melange(c.panneau, c.texte, 0.22);
    v["--ink-strong"] = c.texte;
    v["--ink"] = melange(c.texte, c.panneau, w[0]);
    v["--ink-soft"] = melange(c.texte, c.panneau, w[1]);
    v["--ink-muted"] = melange(c.texte, c.panneau, w[2]);
    v["--slate"] = v["--ink-soft"];
    v["--accent"] = c.accent;
    v["--accent-soft"] = c.accent + "24";
    v["--accent-ink"] = encreSur(c.accent);
    v["--amber"] = c.accent;            // coût / avertissement = accent (theme-v2.css, deepotus.tokens.css)
    v["--amber-soft"] = c.accent + "22";
    v["--cyan"] = c.accent;             // la couche Cinema remappe --cyan sur l'accent
    v["--cyan-soft"] = c.accent + "24";
    v["--cyan-glow"] = c.accent + "55";
    v["--green"] = c.succes;
    v["--green-soft"] = c.succes + "22";
    v["--red"] = c.erreur;
    v["--red-soft"] = c.erreur + "22";
    v["color-scheme"] = s ? "dark" : "light";
    return v;
  }
  var NOMS = Object.keys(deriver(PRESETS.sombre.couleurs, "coque"));

  function controles(c, fort) {
    var d = deriver(c, "coque", fort);
    return [
      ["texte_fond", c.texte, c.fond, 4.5], ["texte_panneau", c.texte, c.panneau, 4.5],
      ["secondaire_panneau", d["--ink-soft"], c.panneau, 4.5], ["accent_panneau", c.accent, c.panneau, 3],
      ["bouton", d["--accent-ink"], c.accent, 4.5], ["succes_panneau", c.succes, c.panneau, 4.5],
      ["erreur_panneau", c.erreur, c.panneau, 4.5]
    ].map(function (x) {
      var r = contraste(x[1], x[2]);
      return { id: x[0], avant: x[1], fond: x[2], ratio: r, seuil: x[3], ok: r >= x[3] };
    });
  }

  // ── état ──────────────────────────────────────────────────────────────────
  function normaliser(e) {
    if (!e || typeof e !== "object") return null;
    if (ORDRE.indexOf(e.preset) >= 0) return { preset: e.preset };
    if (e.preset !== "libre" || !e.couleurs || typeof e.couleurs !== "object") return null;
    var c = {};
    for (var i = 0; i < JETONS.length; i++) {
      var v = e.couleurs[JETONS[i]];
      if (typeof v !== "string" || !/^#[0-9a-f]{6}$/i.test(v)) return null;
      c[JETONS[i]] = v.toLowerCase();
    }
    var n = { preset: "libre", couleurs: c };
    if (e.fort === true) n.fort = true;
    return n;
  }
  function couleursDe(e) {
    var src = e && e.preset === "libre" && e.couleurs ? e.couleurs : (PRESETS[e && e.preset] || PRESETS.sombre).couleurs;
    var c = {};
    JETONS.forEach(function (j) { c[j] = src[j]; });
    return c;
  }
  function fortDe(e) {
    if (!e) return false;
    return e.preset === "libre" ? e.fort === true : !!(PRESETS[e.preset] && PRESETS[e.preset].fort);
  }
  function estDefaut(e) { return !e || e.preset === "sombre"; }

  var ETAT = { preset: "sombre" };
  var choisiDepuisDemarrage = false;
  var PANNEAUX = [];

  // ── application : <html> de la coque, puis chaque cadre de même origine ────
  function ecrireDoc(doc, contexte) {
    var r = doc && doc.documentElement;
    if (!r || !r.style || typeof r.style.setProperty !== "function") return;
    var marque = r.getAttribute("data-dz-apparence");
    if (estDefaut(ETAT)) {
      if (marque === null) return;
      NOMS.forEach(function (k) { r.style.removeProperty(k); });
      var avant = r.getAttribute("data-dz-apparence-avant");
      if (avant !== null) { r.setAttribute("data-theme", avant); r.removeAttribute("data-dz-apparence-avant"); }
      else r.removeAttribute("data-theme");
      r.removeAttribute("data-dz-apparence");
      return;
    }
    var v = deriver(couleursDe(ETAT), contexte, fortDe(ETAT));
    NOMS.forEach(function (k) { r.style.setProperty(k, v[k]); });
    var t = v["color-scheme"] === "light" ? "light" : "dark";
    if (marque === null && r.getAttribute("data-theme") !== null) r.setAttribute("data-dz-apparence-avant", r.getAttribute("data-theme"));
    r.setAttribute("data-theme", t);
    r.setAttribute("data-dz-apparence", t);
  }
  function cadres(doc) {
    try { return Array.prototype.slice.call(doc.querySelectorAll("iframe")); } catch (e) { return []; }
  }
  function docDe(f) {
    try { var d = f.contentDocument; return d && d.documentElement ? d : null; } catch (e) { return null; }
  }
  function appliquerArbre(doc, contexte, prof) {
    ecrireDoc(doc, contexte);
    if (prof > 4) return;
    cadres(doc).forEach(function (f) {
      suivreCadre(f, prof + 1);
      var d = docDe(f);
      if (d) appliquerArbre(d, "lab", prof + 1);
    });
  }
  // un cadre est repeint à chaque document qu'il charge : à son « load », et dès que son nouveau document existe
  // (guet par images, quelques secondes après l'apparition du cadre ou un changement de src) pour éviter l'éclair
  function peindreCadre(f, prof) {
    var d = docDe(f);
    if (!d) return null;
    appliquerArbre(d, "lab", prof);
    observer(d, prof);
    return d;
  }
  function guetter(f, prof) {
    var raf = window.requestAnimationFrame;
    if (typeof raf !== "function") return;
    var vu = null, restant = 600;
    (function tour() {
      if (f.isConnected === false || restant-- <= 0) return;
      var d = docDe(f);
      if (d && d !== vu) { vu = d; peindreCadre(f, prof); }
      raf(tour);
    })();
  }
  function suivreCadre(f, prof) {
    if (!f || f.__dzApparence) return;
    f.__dzApparence = true;
    var p = prof || 1;
    if (typeof f.addEventListener === "function") f.addEventListener("load", function () { peindreCadre(f, p); });
    guetter(f, p);
  }
  function observer(doc, prof) {
    var MO = window.MutationObserver;
    if (typeof MO !== "function" || !doc || doc.__dzApparenceObs || prof > 4) return;
    try {
      doc.__dzApparenceObs = true;
      new MO(function (muts) {
        muts.forEach(function (m) {
          if (m.type === "attributes") {
            if (m.target && m.target.tagName === "IFRAME") { suivreCadre(m.target, prof + 1); guetter(m.target, prof + 1); }
            return;
          }
          Array.prototype.forEach.call(m.addedNodes || [], function (nd) {
            var fs = nd.tagName === "IFRAME" ? [nd] : (typeof nd.querySelectorAll === "function" ? cadres(nd) : []);
            fs.forEach(function (f) { suivreCadre(f, prof + 1); peindreCadre(f, prof + 1); });
          });
        });
      }).observe(doc.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["src"] });
    } catch (e) { /* document fermé entre-temps */ }
  }
  function avertir() {
    PANNEAUX = PANNEAUX.filter(function (p) { return p.racine.isConnected !== false; });
    PANNEAUX.forEach(function (p) { p.rafraichir(); });
  }
  function appliquer(e, doc) {
    ETAT = normaliser(e) || { preset: "sombre" };
    appliquerArbre(doc || document, "coque", 0);
    avertir();
  }

  // ── persistance : cache local + serveur ───────────────────────────────────
  function lireLocal() {
    try { return normaliser(JSON.parse(window.localStorage.getItem(CLE))); } catch (e) { return null; }
  }
  function garderLocal(e) {
    try { window.localStorage.setItem(CLE, JSON.stringify(e)); } catch (x) { /* stockage refusé : le serveur garde */ }
  }
  function statut(texte) { PANNEAUX.forEach(function (p) { p.statut(texte); }); }
  function detail(j) {
    var d = j && j.detail;
    if (typeof d === "string") return d;
    return d && (d.message || d.texte) ? String(d.message || d.texte) : "";
  }
  var minuterie = null;
  function envoyer(e) {
    if (typeof window.fetch !== "function") return;
    if (minuterie) clearTimeout(minuterie);
    minuterie = setTimeout(function () {
      minuterie = null;
      window.fetch(URL_API, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(e) })
        .then(function (r) {
          return r.json().catch(function () { return {}; }).then(function (j) {
            if (!r.ok) throw new Error(detail(j) || "HTTP " + r.status);
            statut("");
          });
        })
        .catch(function (err) { statut(T("apparence.statut.echec", { erreur: String((err && err.message) || err) })); });
    }, 300);
  }
  function choisir(e) {
    var n = normaliser(e);
    if (!n) return false;
    choisiDepuisDemarrage = true;
    appliquer(n);
    garderLocal(n);
    envoyer(n);
    return true;
  }
  function reinitialiser() { return choisir({ preset: "sombre" }); }
  function synchroniser() {
    if (typeof window.fetch !== "function") return Promise.resolve(null);
    return window.fetch(URL_API)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        var n = j && normaliser(j.etat);
        if (n && !choisiDepuisDemarrage && JSON.stringify(n) !== JSON.stringify(ETAT)) { garderLocal(n); appliquer(n); }
        return n;
      })
      .catch(function () { return null; });
  }

  // ── le panneau de Réglages › Apparence ────────────────────────────────────
  var S = {
    panneau: "display:flex;flex-direction:column;gap:12px;padding:14px;margin-bottom:12px;border:1px solid var(--stroke);border-radius:0;background:var(--bg-panel);color:var(--ink);font:12px/1.45 var(--font-ui,system-ui,sans-serif)",
    titre: "font:600 13px/1.3 var(--font-ui,system-ui,sans-serif);color:var(--ink-strong)",
    petit: "font-size:11px;color:var(--ink-soft)",
    section: "font:10px/1.3 var(--font-mono,monospace);letter-spacing:.12em;text-transform:uppercase;color:var(--ink-soft)",
    presets: "display:flex;flex-wrap:wrap;gap:6px",
    preset: "display:inline-flex;align-items:center;gap:8px;height:30px;padding:0 10px;border-radius:0;background:var(--bg-panel-2);border:1px solid var(--stroke-strong);color:var(--ink-strong);cursor:pointer;font:inherit;font-size:12px",
    presetActif: "border-color:var(--accent);box-shadow:inset 0 0 0 1px var(--accent)",
    pastilles: "display:inline-flex;border:1px solid var(--stroke-strong)",
    pastille: "display:inline-block;width:10px;height:14px",
    grille: "display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:6px 16px",
    ligne: "display:flex;align-items:center;gap:8px",
    libelle: "flex:1;font-size:12px;color:var(--ink)",
    couleur: "width:30px;height:24px;padding:0;border:1px solid var(--stroke-strong);border-radius:0;background:transparent;cursor:pointer",
    hex: "width:84px;height:24px;padding:0 6px;border-radius:0;background:var(--bg-base);border:1px solid var(--stroke);color:var(--ink-strong);font:11px var(--font-mono,monospace);box-sizing:border-box",
    deux: "display:grid;grid-template-columns:minmax(220px,1fr) minmax(260px,1.3fr);gap:12px",
    apercu: "display:flex;flex-direction:column;gap:8px;padding:12px;border-radius:0",
    rang: "display:flex;flex-wrap:wrap;align-items:center;gap:8px",
    bouton: "display:inline-flex;align-items:center;height:26px;padding:0 12px;font-weight:600;font-size:12px",
    etiquette: "font:11px var(--font-mono,monospace)",
    controle: "display:grid;grid-template-columns:1fr auto auto;align-items:center;gap:8px;padding:3px 0;border-bottom:1px solid var(--stroke);font-size:11.5px",
    ratio: "font:11px var(--font-mono,monospace);color:var(--ink-strong)",
    verdict: "min-width:44px;padding:1px 6px;text-align:center;font:600 10px/1.6 var(--font-mono,monospace);border:1px solid currentColor;border-radius:0",
    alerte: "padding:6px 8px;border:1px solid var(--amber);color:var(--ink-strong);font-size:11.5px",
    pied: "display:flex;align-items:center;gap:10px",
    action: "height:26px;padding:0 10px;border-radius:0;background:var(--bg-panel-2);border:1px solid var(--stroke-strong);color:var(--ink-strong);cursor:pointer;font:inherit;font-size:12px"
  };

  function T(cle, v) { return typeof window.dzT === "function" ? window.dzT(cle, v) : cle; }
  function langue() { var l = typeof window.dzLang === "function" ? window.dzLang() : window.dzLang; return l === "en" ? "en" : "fr"; }
  function el(tag, attrs, texte) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (texte != null) n.textContent = texte;
    return n;
  }
  function vider(n) { while (n.firstChild) n.removeChild(n.firstChild); }
  function ratioTexte(r) {
    var t = r.toFixed(2);
    return (langue() === "en" ? t : t.replace(".", ",")) + ":1";
  }

  function monter(hote) {
    if (!hote) return;
    if (hote.__dzApparence) { hote.__dzApparence.rafraichir(); return; }     // la ref est rappelée à chaque rendu
    vider(hote);
    var racine = el("div", { "data-dz-apparence-panneau": "1", style: S.panneau });
    var tete = el("div", {});
    tete.appendChild(el("div", { style: S.titre }, T("apparence.palette.titre")));
    tete.appendChild(el("div", { style: S.petit }, T("apparence.palette.aide")));
    racine.appendChild(tete);

    var rang = el("div", { style: S.presets });
    var boutons = {};
    ORDRE.forEach(function (p) {
      var b = el("button", { type: "button", "data-dz-apparence-preset": p, "aria-pressed": "false", style: S.preset });
      var pas = el("span", { style: S.pastilles, "aria-hidden": "true" });
      ["fond", "panneau", "accent"].forEach(function (j) {
        pas.appendChild(el("span", { "data-dz-apparence-pastille": j, style: S.pastille + ";background:" + PRESETS[p].couleurs[j] }));
      });
      b.appendChild(pas);
      b.appendChild(el("span", {}, T("apparence.preset." + p)));
      b.addEventListener("click", function () { choisir({ preset: p }); });
      boutons[p] = b;
      rang.appendChild(b);
    });
    racine.appendChild(rang);
    var libre = el("div", { "data-dz-apparence-libre": "1", style: S.petit });
    racine.appendChild(libre);

    racine.appendChild(el("div", { style: S.section }, T("apparence.section.couleurs")));
    var grille = el("div", { style: S.grille });
    var champs = {};
    function changer(j, v) {
      var c = couleursDe(ETAT);
      c[j] = String(v).toLowerCase();
      choisir({ preset: "libre", couleurs: c, fort: fortDe(ETAT) });
    }
    JETONS.forEach(function (j) {
      var ligne = el("label", { style: S.ligne });
      ligne.appendChild(el("span", { style: S.libelle }, T("apparence.jeton." + j)));
      var c = el("input", { type: "color", "data-dz-apparence-jeton": j, style: S.couleur, title: T("apparence.jeton." + j) });
      var h = el("input", { type: "text", "data-dz-apparence-hex": j, style: S.hex, maxlength: "7", spellcheck: "false",
                            "aria-label": T("apparence.jeton." + j) });
      c.addEventListener("input", function () { changer(j, c.value); });
      h.addEventListener("change", function () {
        var v = String(h.value || "").trim().toLowerCase();
        if (v.charAt(0) !== "#") v = "#" + v;
        if (!/^#[0-9a-f]{6}$/.test(v)) {
          h.value = couleursDe(ETAT)[j];
          statut(T("apparence.statut.hex_invalide"));
          return;
        }
        changer(j, v);
      });
      ligne.appendChild(c);
      ligne.appendChild(h);
      grille.appendChild(ligne);
      champs[j] = { c: c, h: h };
    });
    racine.appendChild(grille);

    var deux = el("div", { style: S.deux });
    var gauche = el("div", {});
    gauche.appendChild(el("div", { style: S.section }, T("apparence.section.apercu")));
    var ap = el("div", { "data-dz-apparence-apercu": "1", style: S.apercu });
    var apTitre = el("div", {}, T("apparence.apercu.titre"));
    var apTexte = el("div", {}, T("apparence.apercu.texte"));
    var apRang = el("div", { style: S.rang });
    var apBouton = el("span", {}, T("apparence.apercu.bouton"));
    var apOk = el("span", {}, T("apparence.apercu.succes"));
    var apKo = el("span", {}, T("apparence.apercu.erreur"));
    apRang.appendChild(apBouton);
    apRang.appendChild(apOk);
    apRang.appendChild(apKo);
    ap.appendChild(apTitre);
    ap.appendChild(apTexte);
    ap.appendChild(apRang);
    gauche.appendChild(ap);
    var droite = el("div", {});
    droite.appendChild(el("div", { style: S.section }, T("apparence.section.contraste")));
    var lignesCtl = {};
    controles(couleursDe(ETAT), fortDe(ETAT)).forEach(function (x) {
      var row = el("div", { "data-dz-apparence-controle": x.id, "data-ok": "1", style: S.controle });
      var lib = el("span", {}, T("apparence.contraste." + x.id));
      var ra = el("span", { style: S.ratio });
      var ve = el("span", { style: S.verdict });
      row.appendChild(lib);
      row.appendChild(ra);
      row.appendChild(ve);
      droite.appendChild(row);
      lignesCtl[x.id] = { row: row, ra: ra, ve: ve };
    });
    var zoneAlerte = el("div", {});
    droite.appendChild(zoneAlerte);
    deux.appendChild(gauche);
    deux.appendChild(droite);
    racine.appendChild(deux);

    var pied = el("div", { style: S.pied });
    var reinit = el("button", { type: "button", "data-dz-apparence-action": "reinitialiser", style: S.action },
                    T("apparence.action.reinitialiser"));
    reinit.addEventListener("click", function () { reinitialiser(); });
    var st = el("span", { "data-dz-apparence-statut": "1", role: "status", style: S.petit });
    pied.appendChild(reinit);
    pied.appendChild(st);
    racine.appendChild(pied);
    hote.appendChild(racine);

    function rafraichir() {
      var c = couleursDe(ETAT), fort = fortDe(ETAT), d = deriver(c, "coque", fort);
      ORDRE.forEach(function (p) {
        var actif = ETAT.preset === p;
        boutons[p].setAttribute("aria-pressed", actif ? "true" : "false");
        boutons[p].setAttribute("style", S.preset + (actif ? ";" + S.presetActif : ""));
      });
      libre.textContent = ETAT.preset === "libre" ? T("apparence.preset.libre") : "";
      var actifDoc = document.activeElement;
      JETONS.forEach(function (j) {
        champs[j].c.value = c[j];
        if (actifDoc !== champs[j].h) champs[j].h.value = c[j];
      });
      ap.setAttribute("style", S.apercu + ";background:" + c.panneau + ";border:1px solid " + d["--stroke-strong"]);
      apTitre.setAttribute("style", S.titre + ";color:" + c.texte);
      apTexte.setAttribute("style", "font-size:12px;color:" + d["--ink-soft"]);
      apBouton.setAttribute("style", S.bouton + ";background:" + c.accent + ";color:" + d["--accent-ink"]);
      apOk.setAttribute("style", S.etiquette + ";color:" + c.succes);
      apKo.setAttribute("style", S.etiquette + ";color:" + c.erreur);
      var rates = 0;
      controles(c, fort).forEach(function (x) {
        var l = lignesCtl[x.id];
        l.row.setAttribute("data-ok", x.ok ? "1" : "0");
        l.ra.textContent = ratioTexte(x.ratio);
        l.ve.textContent = T(x.ok ? "apparence.verdict.ok" : "apparence.verdict.ko");
        l.ve.setAttribute("style", S.verdict + ";color:" + (x.ok ? "var(--green)" : "var(--red)"));
        if (!x.ok) rates++;
      });
      vider(zoneAlerte);
      if (rates) zoneAlerte.appendChild(el("div", { "data-dz-apparence-alerte": "1", role: "alert", style: S.alerte },
                                           T("apparence.alerte.contraste", { n: rates })));
    }
    var panneau = { racine: racine, rafraichir: rafraichir, statut: function (t) { st.textContent = t || ""; } };
    hote.__dzApparence = panneau;
    PANNEAUX.push(panneau);
    rafraichir();
  }

  window.__dzApparence = {
    PRESETS: PRESETS, ORDRE: ORDRE, JETONS: JETONS, contraste: contraste, sombre: sombre, deriver: deriver,
    controles: controles, normaliser: normaliser, couleursDe: couleursDe, lire: function () { return ETAT; },
    appliquer: appliquer, suivreCadre: suivreCadre, choisir: choisir, reinitialiser: reinitialiser,
    synchroniser: synchroniser, monter: monter
  };

  // démarrage : le cache local peint tout de suite, le serveur fait foi ensuite ; un autre onglet est suivi
  appliquer(lireLocal() || { preset: "sombre" });
  observer(document, 0);
  if (typeof window.addEventListener === "function") {
    window.addEventListener("storage", function (ev) {
      if (!ev || ev.key !== CLE) return;
      var n = null;
      try { n = normaliser(JSON.parse(ev.newValue)); } catch (x) { n = null; }
      appliquer(n || { preset: "sombre" });
    });
  }
  synchroniser();
})();
