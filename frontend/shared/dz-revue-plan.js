/* dz-revue-plan.js — la « Revue du plan » de la fiche d'un plan (t337, A7 du lot Scenario, 29/10/2026, spec
   docs/superpowers/specs/2026-10-27-scenario-explorations-design.md). SOURCE : frontend/shared/dz-revue-plan.js ;
   copie OCTET POUR OCTET : frontend/dist/shared/dz-revue-plan.js, servie à /shared/dz-revue-plan.js et chargée par
   une balise classique dans la page de l'Atelier (frontend/atelier/index.html). Bancs :
   frontend/shared/qa/revue_plan.test.mjs (comportement) et backend/tests/test_revue_plan_ecran.py (copie, balises,
   textes FR/EN).

   window.__dzRevuePlan.ouvrir({shot, numero, toast(msg, err)}) -> Promise (fermée).
   La revue du DERNIER rendu « Previs → plan » du plan, dans l'ordre de la décision :
   - COMPARER previs / rendu : le comparateur commun (window.__dzComparateur, /shared/dz-comparateur.js), rideau,
     O / C, image par image ;
   - MESURES (gratuites, locales) : POST /api/shots/{id}/revue/mesurer — dérive résiduelle en images (le rendu est
     déjà recalé par t336, le recalage d'origine est rappelé), structure image par image (bords + luminance : un
     repère de composition, la profondeur n'est PAS mesurée et la boîte le dit), identité des entités (ΔE,
     silhouette) avec son angle mort ;
   - AVIS DU DIRECTEUR ARTISTIQUE (payant, Claude vision) : devis gratuit à l'ouverture (POST …/revue/devis), puis
     « Demander l'avis » porte le montant, confirmation (window.__dzDialogue.confirmer), POST …/revue/note
     {confirme_cout: true, max_usd}. 409 : le nouveau devis est montré, rien n'est parti ; 402 de plafond : l'enveloppe
     de window.fetch (dz-plafonds.js) montre son dialogue et rejoue sur accord ; 503 : la clé à ajouter dite.
     Les notes par critère (0-10), les défauts et la synthèse s'affichent avec l'avertissement : JAMAIS une garantie.
   Une revue déjà rangée (GET …/revue) s'affiche telle quelle à l'ouverture : rien n'est recalculé ni repayé.
   CHARTE : celle de dz-previs-plan.js (aucun arrondi, IBM Plex Mono en capitales, jetons --srf-* / --brd-* / --txt-*).
   Textes : clés revueplan.* (frontend/shared/i18n/revueplan.json). Vanilla DOM, aucun innerHTML. */
(function () {
  "use strict";
  if (window.__dzRevuePlan) return;

  var CRITERES = ["mouvement", "cadrage", "style", "personnages", "lumiere", "artefacts"];
  var S = {
    voile: "position:fixed;inset:0;z-index:9980;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center",
    boite: "position:relative;width:720px;max-width:94vw;max-height:92vh;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    corps: "padding:12px 14px;overflow-y:auto;display:flex;flex-direction:column;gap:12px;color:var(--txt-base,var(--ink,#cfd6e2))",
    section: "display:flex;flex-direction:column;gap:6px",
    titre: "font:10px 'IBM Plex Mono',monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    note: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    cadre: "padding:8px 10px;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));display:flex;flex-direction:column;gap:4px",
    ligne: "display:flex;align-items:center;gap:8px;flex-wrap:wrap",
    ok: "color:var(--green,#3fb950)",
    ko: "color:var(--amber,#f0b429)",
    erreur: "color:var(--red,#e5484d);font-size:12px",
    mention: "color:var(--amber,#f0b429);font-size:12px",
    prix: "font-size:14px;color:var(--txt-hi,var(--ink-strong,#e6e9ee))",
    critere: "display:grid;grid-template-columns:120px 44px 1fr;gap:8px;align-items:baseline",
    chiffre: "font:12px 'IBM Plex Mono',monospace;color:var(--txt-hi,var(--ink-strong,#e6e9ee))",
    pied: "display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
    btn: "min-width:88px;height:28px;padding:0 12px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit",
    primaire: "background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6);color:var(--accent-ink,#ffffff)"
  };
  var courant = null;

  function T(cle, v) { return typeof window.dzT === "function" ? window.dzT(cle, v) : cle; }
  function langue() { return typeof window.dzLang === "function" ? window.dzLang() : "fr"; }
  function nombre(v, d) {
    var t = (Number(v) || 0).toFixed(d == null ? 2 : d);
    return langue() === "en" ? t : t.replace(".", ",");
  }
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
    return el("button", { type: "button", "data-dz-revue": marque, style: S.btn + (style ? ";" + style : "") }, texte);
  }
  function montrer(n, oui) { if (oui) n.removeAttribute("hidden"); else n.setAttribute("hidden", ""); }
  function griser(n, oui) { if (oui) n.setAttribute("disabled", ""); else n.removeAttribute("disabled"); }
  function vider(n) { n.textContent = ""; }
  function detail(j, status) {
    var d = j && j.detail;
    if (typeof d === "string" && d) return d;
    if (d && typeof d.message === "string") return d.message;
    if (d && d.dz_plafond && d.dz_plafond.message) return String(d.dz_plafond.message);
    return "HTTP " + status;
  }
  async function lireJson(R) { try { return await R.json(); } catch (e) { return null; } }
  function section(E, titre, aide, marque) {
    var s = el("div", { style: S.section, "data-dz-revue": marque });
    s.appendChild(el("div", { style: S.titre }, titre));
    if (aide) s.appendChild(el("div", { style: S.note }, aide));
    E.corps.appendChild(s);
    return s;
  }
  function chemin(E, fin) { return "/api/shots/" + encodeURIComponent(E.shot.id) + "/revue" + (fin || ""); }
  function fps(v) {
    var p = String(v || "").split("/"), n = Number(p[0]), d = Number(p[1] || 1);
    return n > 0 && d > 0 ? n / d : 24;
  }
  function derive(d) {
    d = Number(d) || 0;
    return T(Math.abs(d) > 1 ? "revueplan.mesures.images_n" : "revueplan.mesures.images_1", { d: (d > 0 ? "+" : "") + d });
  }

  function fermer(E) {
    if (!E || E.ferme || E.envoi) return;
    E.ferme = true;
    document.removeEventListener("keydown", E.touche, true);
    if (E.voile.parentNode) E.voile.parentNode.removeChild(E.voile);
    if (courant === E) courant = null;
    E.resoudre(null);
  }

  function ouvrir(opts) {
    opts = opts || {};
    var s = opts.shot;
    if (!s || !s.id) return Promise.resolve(null);
    if (courant && courant.envoi) return Promise.resolve(null);
    if (courant) fermer(courant);
    return new Promise(function (resoudre) {
      var E = { opts: opts, shot: s, ferme: false, envoi: false, resoudre: resoudre, revue: null, devis: null, jeton: 0 };
      courant = E;
      construire(E);
      charger(E);
    });
  }

  function construire(E) {
    var voile = E.voile = el("div", { style: S.voile, role: "dialog", "aria-modal": "true", "class": "dz-revue",
                                      "data-dz-revue": "voile", "aria-label": T("revueplan.boite.titre", { n: E.opts.numero || "" }) });
    voile.appendChild(el("style", {}, ".dz-revue [hidden]{display:none!important}"));
    var boite = el("div", { style: S.boite });
    boite.appendChild(el("div", { style: S.tete }, T("revueplan.boite.titre", { n: E.opts.numero || "" })));
    E.corps = el("div", { style: S.corps });
    E.intro = el("div", { style: S.note, "data-dz-revue": "intro" }, T("revueplan.boite.intro"));
    E.corps.appendChild(E.intro);
    E.vide = el("div", { style: S.cadre, hidden: "", "data-dz-revue": "vide" });
    E.corps.appendChild(E.vide);
    E.erreur = el("div", { style: S.erreur, hidden: "", "data-dz-revue": "erreur", role: "alert" });
    E.corps.appendChild(E.erreur);

    var sc = E.secComparer = section(E, T("revueplan.comparer.titre"), T("revueplan.comparer.aide"), "sec-comparer");
    E.btnComparer = bouton("comparer", T("revueplan.comparer.bouton"));
    E.btnComparer.addEventListener("click", function () { comparer(E); });
    sc.appendChild(E.btnComparer);
    E.sansPrevis = el("div", { style: S.note, hidden: "", "data-dz-revue": "sans-previs" }, T("revueplan.comparer.sans_previs"));
    sc.appendChild(E.sansPrevis);

    var sm = E.secMesures = section(E, T("revueplan.mesures.titre"), T("revueplan.mesures.aide"), "sec-mesures");
    E.btnMesurer = bouton("mesurer", T("revueplan.mesures.bouton"));
    E.btnMesurer.addEventListener("click", function () { mesurer(E); });
    sm.appendChild(E.btnMesurer);
    E.mesures = el("div", { style: S.cadre, hidden: "", "data-dz-revue": "mesures", role: "status" });
    sm.appendChild(E.mesures);

    var sa = E.secAvis = section(E, T("revueplan.avis.titre"), T("revueplan.avis.aide"), "sec-avis");
    E.prix = el("div", { style: S.prix, "data-dz-revue": "prix" }, T("revueplan.avis.devis_attente"));
    E.mention = el("div", { style: S.mention, hidden: "", "data-dz-revue": "mention" });
    sa.appendChild(E.prix); sa.appendChild(E.mention);
    E.btnAvis = bouton("avis", T("revueplan.avis.bouton"), S.primaire);
    griser(E.btnAvis, true);
    E.btnAvis.addEventListener("click", function () { demander(E); });
    sa.appendChild(E.btnAvis);
    E.avis = el("div", { style: S.cadre, hidden: "", "data-dz-revue": "avis-rendu" });
    sa.appendChild(E.avis);
    boite.appendChild(E.corps);

    var pied = el("div", { style: S.pied });
    var f = bouton("fermer", T("revueplan.boite.fermer"));
    f.addEventListener("click", function () { fermer(E); });
    pied.appendChild(f);
    boite.appendChild(pied);
    voile.appendChild(boite);
    voile.addEventListener("click", function (ev) { if (ev.target === voile) fermer(E); });
    E.touche = function (ev) {
      if (ev.key === "Escape" && !(window.__dzComparateur && window.__dzComparateur.ouvert && window.__dzComparateur.ouvert())) {
        ev.preventDefault(); if (ev.stopPropagation) ev.stopPropagation(); fermer(E);
      }
    };
    document.addEventListener("keydown", E.touche, true);
    document.body.appendChild(voile);
  }

  function etatVide(E, message) {
    [E.secComparer, E.secMesures, E.secAvis].forEach(function (n) { montrer(n, false); });
    vider(E.vide);
    E.vide.appendChild(el("b", {}, T("revueplan.vide.titre")));
    E.vide.appendChild(el("div", { style: S.note }, message));
    E.vide.appendChild(el("div", { style: S.note }, T("revueplan.vide.aide")));
    montrer(E.vide, true);
  }

  async function charger(E) {
    try {
      var R = await fetch(chemin(E));
      var j = await lireJson(R);
      if (E.ferme) return;
      if (R.status === 400) { etatVide(E, detail(j, R.status)); return; }
      if (!R.ok) throw new Error(detail(j, R.status));
      rendre(E, j);
    } catch (e) {
      montrer(E.erreur, true);
      E.erreur.textContent = T("revueplan.boite.ko", { msg: e.message });
      return;
    }
    lireDevis(E);
  }

  function rendre(E, j) {
    E.revue = j;
    if (j.avertissement) E.intro.textContent = T("revueplan.boite.intro") + " " + j.avertissement;
    var avecPrevis = !!(j.previs && j.previs.url);
    griser(E.btnComparer, !avecPrevis);
    montrer(E.sansPrevis, !avecPrevis);
    var rv = j.revue || {};
    E.btnMesurer.textContent = T(rv.mesures ? "revueplan.mesures.rebouton" : "revueplan.mesures.bouton");
    rendreMesures(E, rv.mesures);
    rendreAvis(E, rv.note);
  }

  function comparer(E) {
    var j = E.revue;
    if (!j || !j.previs || !window.__dzComparateur) {
      if (E.opts.toast) E.opts.toast(T("revueplan.comparer.absent"), true);
      return;
    }
    window.__dzComparateur.ouvrir({ a: { src: j.previs.url, type: "video", libelle: T("revueplan.comparer.previs") },
                                    b: { src: j.rendu.url, type: "video", libelle: T("revueplan.comparer.rendu") },
                                    titre: T("revueplan.comparer.titre_boite", { n: E.opts.numero || "" }), fps: fps(j.fps) });
  }

  async function mesurer(E) {
    griser(E.btnMesurer, true);
    E.btnMesurer.textContent = T("revueplan.mesures.en_cours");
    montrer(E.erreur, false);
    try {
      var R = await fetch(chemin(E, "/mesurer"), { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      var j = await lireJson(R);
      if (E.ferme) return;
      if (!R.ok) throw new Error(detail(j, R.status));
      rendre(E, j);
    } catch (e) {
      montrer(E.erreur, true);
      E.erreur.textContent = T("revueplan.mesures.ko", { msg: e.message });
      E.btnMesurer.textContent = T("revueplan.mesures.bouton");
    } finally {
      griser(E.btnMesurer, false);
    }
  }

  function rendreMesures(E, m) {
    vider(E.mesures);
    montrer(E.mesures, !!m);
    if (!m) return;
    var t = m.temporel, st = m.structure;
    function l(marque, texte, style) { var n = el("div", { "data-dz-revue": marque, style: style || "" }, texte); E.mesures.appendChild(n); return n; }
    if (m.sans_previs || !t) l("m-sans-previs", T("revueplan.mesures.sans_previs"), S.note);
    if (t) {
      var rc = t.recalage && t.recalage.derive_images != null
        ? " " + T("revueplan.mesures.recalage", { d: derive(t.recalage.derive_images) }) : "";
      l("m-derive", (t.fiable === false ? T("revueplan.mesures.derive_non") : T("revueplan.mesures.derive", { d: derive(t.derive_images) })) + rc,
        t.fiable !== false && Number(t.derive_images) === 0 ? S.ok : S.ko);
    }
    if (st && st.bords && st.bords.moyenne != null) {
      l("m-structure", T(st.verdict === "proche" ? "revueplan.mesures.structure_proche" : "revueplan.mesures.structure_ecart", {
        b: nombre(st.bords.moyenne), bmin: nombre(st.bords.min), i: (Number(st.bords.pire_image) || 0) + 1,
        l: nombre(st.luminance.moyenne), sb: nombre(st.seuils.bords), sl: nombre(st.seuils.luminance) }),
        st.verdict === "proche" ? S.ok : S.ko);
      l("m-structure-aide", T("revueplan.mesures.structure_aide"), S.note);
    }
    l("m-profondeur", T("revueplan.mesures.profondeur"), S.note);
    (m.identite || []).forEach(function (e) {
      l("m-identite", e.vue == null ? T("revueplan.mesures.identite_sans_vue", { nom: e.name || "" })
        : T(e.verdict === "stable" ? "revueplan.mesures.identite_stable" : "revueplan.mesures.identite_derive", {
          nom: e.name || "", c: nombre(e.ecart_couleur, 1), s: nombre(e.ecart_silhouette) }),
        e.vue == null ? S.note : e.verdict === "stable" ? S.ok : S.ko);
    });
    if ((m.identite || []).length) l("m-angle-mort", T("revueplan.mesures.angle_mort"), S.note);
    else l("m-identite-vide", T("revueplan.mesures.identite_vide"), S.note);
  }

  async function lireDevis(E) {
    var n = ++E.jeton;
    try {
      var R = await fetch(chemin(E, "/devis"), { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      var j = await lireJson(R);
      if (n !== E.jeton || E.ferme) return;
      if (!R.ok) throw new Error(detail(j, R.status));
      rendreDevis(E, j);
    } catch (e) {
      if (n !== E.jeton || E.ferme) return;
      E.devis = null;
      E.prix.textContent = T("revueplan.avis.devis_ko", { msg: e.message });
    }
  }

  function rendreDevis(E, d) {
    E.devis = d;
    E.prix.textContent = d.disponible === false ? T("revueplan.avis.devis_indispo")
      : T("revueplan.avis.devis", { usd: usd(d.usd), n: d.n_images || 0 });
    montrer(E.mention, !!d.message);
    E.mention.textContent = d.message || "";
    // jamais grisé faute de clé : le refus (503, clé à ajouter) tombe au clic, comme partout
    E.btnAvis.textContent = d.disponible === false ? T("revueplan.avis.bouton") : T("revueplan.avis.bouton_prix", { usd: usd(d.usd) });
    griser(E.btnAvis, false);
  }

  async function demander(E) {
    if (E.envoi || !E.devis) return;
    var montant = E.devis.usd;
    var oui = window.__dzDialogue && window.__dzDialogue.confirmer
      ? await window.__dzDialogue.confirmer(T("revueplan.avis.confirmer", { usd: usd(montant) }),
                                            { titre: T("revueplan.avis.confirmer_titre"), ok: T("revueplan.avis.confirmer_ok") })
      : false;                                   // sans dialogue maison : rien ne part
    if (!oui || E.ferme) return;
    E.envoi = true;
    griser(E.btnAvis, true);
    E.prix.textContent = T("revueplan.avis.envoi");
    montrer(E.erreur, false);
    try {
      var R = await fetch(chemin(E, "/note"), { method: "POST", headers: { "Content-Type": "application/json" },
                                                body: JSON.stringify({ confirme_cout: true, max_usd: montant }) });
      var j = await lireJson(R);
      E.envoi = false;
      if (R.status === 409 && j && j.detail && j.detail.devis) {   // le devis a bougé : le nouveau est montré
        rendreDevis(E, j.detail.devis);
        montrer(E.erreur, true);
        E.erreur.textContent = T("revueplan.avis.devis_change", { usd: usd(j.detail.usd) });
        return;
      }
      if (!R.ok) throw new Error(detail(j, R.status));
      rendre(E, j);
      rendreDevis(E, E.devis);
      if (E.opts.toast) E.opts.toast(T("revueplan.avis.rendu", { usd: usd((j.revue && j.revue.note && j.revue.note.usd) || montant) }));
    } catch (e) {
      E.envoi = false;
      griser(E.btnAvis, false);
      rendreDevis(E, E.devis);
      montrer(E.erreur, true);
      E.erreur.textContent = T("revueplan.avis.ko", { msg: e.message });
    }
  }

  function rendreAvis(E, n) {
    vider(E.avis);
    montrer(E.avis, !!n);
    if (!n) return;
    E.avis.appendChild(el("div", { style: S.mention, "data-dz-revue": "a-avertissement" }, T("revueplan.avis.avertissement")));
    if (n.moyenne != null) E.avis.appendChild(el("div", { style: S.prix, "data-dz-revue": "a-moyenne" }, T("revueplan.avis.moyenne", { m: nombre(n.moyenne, 1) })));
    CRITERES.forEach(function (c) {
      var v = (n.criteres || {})[c] || {};
      var ligne = el("div", { style: S.critere, "data-dz-revue": "a-critere", "data-critere": c });
      ligne.appendChild(el("span", {}, T("revueplan.critere." + c)));
      ligne.appendChild(el("span", { style: S.chiffre }, v.note == null ? "—" : T("revueplan.avis.sur_dix", { n: v.note })));
      ligne.appendChild(el("span", { style: S.note }, v.commentaire || ""));
      E.avis.appendChild(ligne);
    });
    E.avis.appendChild(el("div", { style: S.titre }, T("revueplan.avis.defauts", { n: (n.defauts || []).length })));
    if (!(n.defauts || []).length) E.avis.appendChild(el("div", { style: S.note, "data-dz-revue": "a-aucun-defaut" }, T("revueplan.avis.aucun_defaut")));
    (n.defauts || []).forEach(function (x) {
      E.avis.appendChild(el("div", { "data-dz-revue": "a-defaut", style: x.gravite === "majeur" ? S.ko : "" },
        T("revueplan.gravite." + (x.gravite || "moyen")) + (x.moment ? " · " + T("revueplan.moment." + x.moment) : "") + " — " + (x.texte || "")));
    });
    if (n.synthese) E.avis.appendChild(el("div", { "data-dz-revue": "a-synthese" }, T("revueplan.avis.synthese", { t: n.synthese })));
    E.avis.appendChild(el("div", { style: S.note, "data-dz-revue": "a-pied" }, T("revueplan.avis.pied", { usd: usd(n.usd), date: String(n.date || "").slice(0, 10) })));
  }

  window.__dzRevuePlan = { ouvrir: ouvrir };
})();
