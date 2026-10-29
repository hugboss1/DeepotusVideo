/* dz-passes-plan.js — les « Passes Blender » de la fiche d'un plan (t334, A4 du lot Scenario, 29/10/2026, spec
   docs/superpowers/specs/2026-10-27-scenario-explorations-design.md). SOURCE : frontend/shared/dz-passes-plan.js ;
   copie OCTET POUR OCTET : frontend/dist/shared/dz-passes-plan.js, servie à /shared/dz-passes-plan.js et chargée par
   une balise classique dans la page de l'Atelier (frontend/atelier/index.html). Bancs :
   frontend/shared/qa/passes_plan.test.mjs (comportement) et backend/tests/test_passes_plan_ecran.py (copie, balises,
   textes FR/EN).

   window.__dzPassesPlan.ouvrir({shot, numero, toast(msg, err)}) -> Promise (fermée).
     La scène du Plateau 3D du plan rendue par Blender en arrière-plan, caméra du plan reproduite : clay (Workbench),
     look (EEVEE), profondeur (PNG 16 bits, blanc = proche), normales (espace caméra), masques (une couleur par
     entité, la palette de la previs colorée). GRATUIT et LOCAL : aucun devis, le coût affiché est « gratuit ».
     GET /api/passes/plan/{id} → état de Blender (version, ou quoi installer), scène, derniers runs, job en cours ;
     « Rendre les passes » → POST /api/passes/plan/{id} {sequence, passes} ; avancement par GET /api/passes/job/{jid}
     (une fois par seconde), « Annuler » → POST /api/passes/job/{jid}/annuler. Blender absent : le message du serveur
     (503) dit quoi installer ; le bouton reste cliquable (la règle des modèles sans clé).
     Les vignettes (« les versions du plan ») ouvrent l'image en grand ; « Comparer clay / look » passe par le
     comparateur commun (window.__dzComparateur) quand il est chargé.
   window.__dzPassesPlan.vignettes(liste, chapterId) -> Promise : pose sous la vignette de chaque carte de plan
     (.shot-card[data-id] .thumb) la bande des passes de son DERNIER run (GET /api/passes/chapitre/{id}) ; un clic
     sur la bande ouvre la boîte du plan.
   CHARTE : celle de dz-revue-plan.js (aucun arrondi, IBM Plex Mono en capitales, jetons --srf-* / --brd-* / --txt-*).
   Textes : clés passesplan.* (frontend/shared/i18n/passesplan.json). Vanilla DOM, aucun innerHTML. */
(function () {
  "use strict";
  if (window.__dzPassesPlan) return;

  var PASSES = ["clay", "look", "profondeur", "normales", "masques"];
  var PAS_MS = 1000;
  var S = {
    voile: "position:fixed;inset:0;z-index:9980;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center",
    boite: "position:relative;width:820px;max-width:94vw;max-height:92vh;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    corps: "padding:12px 14px;overflow-y:auto;display:flex;flex-direction:column;gap:12px;color:var(--txt-base,var(--ink,#cfd6e2))",
    section: "display:flex;flex-direction:column;gap:6px",
    titre: "font:10px 'IBM Plex Mono',monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    note: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    cadre: "padding:8px 10px;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));display:flex;flex-direction:column;gap:4px",
    ligne: "display:flex;align-items:center;gap:10px;flex-wrap:wrap",
    ok: "color:var(--green,#3fb950)",
    ko: "color:var(--amber,#f0b429)",
    erreur: "color:var(--red,#e5484d);font-size:12px",
    prix: "font-size:13px;color:var(--green,#3fb950)",
    grille: "display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px",
    tuile: "display:flex;flex-direction:column;gap:3px;padding:0;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));border-radius:0;background:#000;cursor:zoom-in;color:inherit;font:inherit;text-align:left",
    media: "display:block;width:100%;aspect-ratio:16/9;object-fit:contain;background:#000",
    legende: "padding:3px 6px;font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae));background:var(--srf-panel,var(--bg-panel-2,#13171c))",
    barre: "height:6px;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138))",
    plein: "height:100%;width:0;background:var(--accent,#2b6fd6);transition:width .3s",
    pied: "display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
    btn: "min-width:88px;height:28px;padding:0 12px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit",
    primaire: "background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6);color:var(--accent-ink,#ffffff)",
    coche: "display:inline-flex;align-items:center;gap:4px;font-size:12px",
    bande: "display:flex;gap:2px;margin-top:3px;cursor:pointer",
    mini: "width:30px;height:17px;object-fit:cover;background:#000;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138))"
  };
  var courant = null;

  function T(cle, v) { return typeof window.dzT === "function" ? window.dzT(cle, v) : cle; }
  function el(tag, attrs, texte) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (texte != null) n.textContent = texte;
    return n;
  }
  function bouton(marque, texte, style) {
    return el("button", { type: "button", "data-dz-passes": marque, style: S.btn + (style ? ";" + style : "") }, texte);
  }
  function montrer(n, oui) { if (oui) n.removeAttribute("hidden"); else n.setAttribute("hidden", ""); }
  function griser(n, oui) { if (oui) n.setAttribute("disabled", ""); else n.removeAttribute("disabled"); }
  function vider(n) { n.textContent = ""; }
  function detail(j, status) {
    var d = j && j.detail;
    if (typeof d === "string" && d) return d;
    if (d && typeof d.message === "string") return d.message;
    return "HTTP " + status;
  }
  async function lireJson(R) { try { return await R.json(); } catch (e) { return null; } }
  function nomPasse(p) { return T("passesplan.passe." + p); }
  function metres(v) {
    var s = (Number(v) || 0).toFixed(2);
    return typeof window.dzLang === "function" && window.dzLang() === "en" ? s : s.replace(".", ",");
  }
  function urlFichier(shotId, run, nom) {
    return "/api/passes/fichier/" + encodeURIComponent(shotId) + "/" + encodeURIComponent(run) + "/" + encodeURIComponent(nom);
  }
  function section(E, titre, aide, marque) {
    var s = el("div", { style: S.section, "data-dz-passes": marque });
    s.appendChild(el("div", { style: S.titre }, titre));
    if (aide) s.appendChild(el("div", { style: S.note }, aide));
    E.corps.appendChild(s);
    return s;
  }
  function attendre(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  function fermer(E) {
    if (!E || E.ferme) return;
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
    if (courant) fermer(courant);
    return new Promise(function (resoudre) {
      var E = { opts: opts, shot: s, ferme: false, resoudre: resoudre, etat: null, job: null, run: 0, jetonSuivi: 0 };
      courant = E;
      construire(E);
      charger(E);
    });
  }

  function construire(E) {
    var titre = T("passesplan.boite.titre", { n: E.opts.numero || "" });
    var voile = E.voile = el("div", { style: S.voile, role: "dialog", "aria-modal": "true", "class": "dz-passes",
                                      "data-dz-passes": "voile", "aria-label": titre });
    voile.appendChild(el("style", {}, ".dz-passes [hidden]{display:none!important}.dz-passes button[disabled],.dz-passes input[disabled]{opacity:.5;cursor:default}"));
    var boite = el("div", { style: S.boite });
    boite.appendChild(el("div", { style: S.tete }, titre));
    E.corps = el("div", { style: S.corps });
    E.corps.appendChild(el("div", { style: S.note, "data-dz-passes": "intro" }, T("passesplan.boite.intro")));
    E.vide = el("div", { style: S.cadre, hidden: "", "data-dz-passes": "vide" });
    E.corps.appendChild(E.vide);
    E.erreur = el("div", { style: S.erreur, hidden: "", "data-dz-passes": "erreur", role: "alert" });
    E.corps.appendChild(E.erreur);

    // 1. Rendre : Blender, la scène, les options, le prix (gratuit), le bouton
    var sr = E.secRendre = section(E, T("passesplan.rendre.titre"), null, "sec-rendre");
    E.blender = el("div", { style: S.note, "data-dz-passes": "blender" });
    E.scene = el("div", { style: S.note, "data-dz-passes": "scene" });
    sr.appendChild(E.blender); sr.appendChild(E.scene);
    var options = el("div", { style: S.ligne, "data-dz-passes": "options" });
    E.coches = {};
    PASSES.forEach(function (p) {
      var lab = el("label", { style: S.coche, title: T("passesplan.aide." + p) });
      var c = el("input", { type: "checkbox", "data-dz-passes": "passe-" + p });
      c.checked = true;
      lab.appendChild(c); lab.appendChild(document.createTextNode(nomPasse(p)));
      E.coches[p] = c;
      options.appendChild(lab);
    });
    sr.appendChild(options);
    var labSeq = el("label", { style: S.coche, "data-dz-passes": "sequence-lab" });
    E.sequence = el("input", { type: "checkbox", "data-dz-passes": "sequence" });
    labSeq.appendChild(E.sequence);
    E.sequenceTexte = document.createTextNode(T("passesplan.rendre.sequence"));
    labSeq.appendChild(E.sequenceTexte);
    sr.appendChild(labSeq);
    E.prix = el("div", { style: S.prix, "data-dz-passes": "prix" }, T("passesplan.rendre.gratuit"));
    sr.appendChild(E.prix);
    var ligne = el("div", { style: S.ligne });
    E.btnRendre = bouton("rendre", T("passesplan.rendre.bouton"), S.primaire);
    E.btnRendre.addEventListener("click", function () { lancer(E); });
    ligne.appendChild(E.btnRendre);
    E.btnAnnuler = bouton("annuler", T("passesplan.rendre.annuler"));
    montrer(E.btnAnnuler, false);
    E.btnAnnuler.addEventListener("click", function () { annuler(E); });
    ligne.appendChild(E.btnAnnuler);
    sr.appendChild(ligne);
    E.progres = el("div", { style: S.section, hidden: "", "data-dz-passes": "progres", role: "status" });
    var barre = el("div", { style: S.barre });
    E.plein = el("div", { style: S.plein, "data-dz-passes": "plein" });
    barre.appendChild(E.plein);
    E.progresTexte = el("div", { style: S.note, "data-dz-passes": "progres-texte" });
    E.progres.appendChild(barre); E.progres.appendChild(E.progresTexte);
    sr.appendChild(E.progres);

    // 2. Les versions du plan (le dernier run, puis les précédents)
    var sv = E.secVersions = section(E, T("passesplan.versions.titre"), T("passesplan.versions.aide"), "sec-versions");
    E.choixRun = el("select", { "data-dz-passes": "runs", hidden: "", title: T("passesplan.versions.runs") });
    E.choixRun.addEventListener("change", function () { rendreRun(E, Number(E.choixRun.value) || 0); });
    sv.appendChild(E.choixRun);
    E.resume = el("div", { style: S.note, "data-dz-passes": "resume" });
    sv.appendChild(E.resume);
    E.grille = el("div", { style: S.grille, "data-dz-passes": "grille" });
    sv.appendChild(E.grille);
    E.btnComparer = bouton("comparer", T("passesplan.versions.comparer"));
    E.btnComparer.addEventListener("click", function () { comparer(E); });
    montrer(E.btnComparer, false);
    sv.appendChild(E.btnComparer);
    E.aucun = el("div", { style: S.note, "data-dz-passes": "aucun" }, T("passesplan.versions.aucune"));
    sv.appendChild(E.aucun);
    // 3. t331 : « Blender ouvert » (pont MCP : envoyer le plan, regarder la scène) quand /shared/dz-blender-scene.js est chargé
    if (window.__dzBlenderScene) window.__dzBlenderScene.monter(E.corps, { shot: E.shot, numero: E.opts.numero, toast: E.opts.toast });
    boite.appendChild(E.corps);

    var pied = el("div", { style: S.pied });
    var f = bouton("fermer", T("passesplan.boite.fermer"));
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

  function chemin(E) { return "/api/passes/plan/" + encodeURIComponent(E.shot.id); }

  async function charger(E) {
    try {
      var R = await fetch(chemin(E));
      var j = await lireJson(R);
      if (E.ferme) return;
      if (!R.ok) throw new Error(detail(j, R.status));
      rendre(E, j);
      if (j.job && (j.job.statut === "attente" || j.job.statut === "rendu")) suivre(E, j.job);
    } catch (e) {
      montrer(E.erreur, true);
      E.erreur.textContent = T("passesplan.boite.ko", { msg: e.message });
    }
  }

  function rendre(E, j) {
    E.etat = j;
    var b = j.blender || {};
    E.blender.textContent = b.dispo ? T("passesplan.rendre.blender", { v: b.version || "?" })
      : (b.installer || T("passesplan.rendre.blender_absent"));
    E.blender.setAttribute("style", S.note + ";" + (b.dispo ? S.ok : S.ko));
    var sc = j.scene;
    montrer(E.vide, !sc);
    if (!sc) {
      vider(E.vide);
      E.vide.appendChild(el("b", {}, T("passesplan.vide.titre")));
      E.vide.appendChild(el("div", { style: S.note }, T("passesplan.vide.aide")));
      var go = bouton("plateau", T("passesplan.vide.plateau"));
      go.addEventListener("click", function () { location.href = "/plateau/?shot=" + encodeURIComponent(E.shot.id); });
      E.vide.appendChild(go);
    }
    montrer(E.secRendre, !!sc);
    if (sc) {
      E.scene.textContent = T(sc.anime ? "passesplan.rendre.scene_animee" : "passesplan.rendre.scene_fixe",
        { nom: sc.nom || "", n: sc.instances || 0, aspect: sc.aspect || "", d: sc.duree_s || 0 });
      var bornes = j.bornes || {};
      E.sequenceTexte.textContent = T("passesplan.rendre.sequence", { fps: bornes.fps || 12, max: bornes.images_max || 48 });
      griser(E.sequence, !sc.anime);
      if (!sc.anime) E.sequence.checked = false;
    }
    E.runs = j.runs || [];
    vider(E.choixRun);
    E.runs.forEach(function (r, i) {
      var o = el("option", { value: String(i) }, T(i === 0 ? "passesplan.versions.run_dernier" : "passesplan.versions.run",
        { date: String(r.date || "").replace("T", " ").slice(0, 16) }));
      E.choixRun.appendChild(o);
    });
    montrer(E.choixRun, E.runs.length > 1);
    rendreRun(E, 0);
  }

  function tuile(E, r, p) {
    var e = (r.passes || {})[p];
    if (!e || !e.fichiers || !e.fichiers.length) return null;
    var src = urlFichier(r.shot_id, r.run, e.fichiers[0]);
    var t = el("button", { type: "button", style: S.tuile, "data-dz-passes": "tuile-" + p, title: T("passesplan.aide." + p) });
    var m;
    if (r.sequence && e.video) {
      m = el("video", { src: urlFichier(r.shot_id, r.run, e.video), muted: "", loop: "", autoplay: "", playsinline: "",
                        style: S.media, "aria-label": nomPasse(p) });
      m.muted = true;
    } else {
      m = el("img", { src: src, alt: nomPasse(p), style: S.media, loading: "lazy" });
    }
    t.appendChild(m);
    t.appendChild(el("span", { style: S.legende }, nomPasse(p)));
    t.addEventListener("click", function () { window.open(src, "_blank", "noopener"); });
    return t;
  }

  function rendreRun(E, i) {
    E.run = i;
    vider(E.grille);
    var r = (E.runs || [])[i];
    montrer(E.aucun, !r);
    montrer(E.btnComparer, !!(r && r.passes && r.passes.clay && r.passes.look && window.__dzComparateur));
    if (!r) { E.resume.textContent = ""; return; }
    var prof = r.profondeur || {};
    E.resume.textContent = T(r.sequence ? "passesplan.versions.resume_seq" : "passesplan.versions.resume", {
      n: r.images || 1, l: r.largeur, h: r.hauteur, v: r.blender || "?",
      proche: metres(prof.proche_m), loin: metres(prof.loin_m),
      palette: T(r.palette === "palette" ? "passesplan.versions.palette" : "passesplan.versions.palette_stable") });
    PASSES.forEach(function (p) { var t = tuile(E, r, p); if (t) E.grille.appendChild(t); });
  }

  function comparer(E) {
    var r = (E.runs || [])[E.run];
    if (!r || !window.__dzComparateur) return;
    var a = r.passes.clay.fichiers[0], b = r.passes.look.fichiers[0];
    window.__dzComparateur.ouvrir({ a: { src: urlFichier(r.shot_id, r.run, a), type: "image", libelle: nomPasse("clay") },
                                    b: { src: urlFichier(r.shot_id, r.run, b), type: "image", libelle: nomPasse("look") },
                                    titre: T("passesplan.versions.comparer_titre", { n: E.opts.numero || "" }) });
  }

  function choisies(E) { return PASSES.filter(function (p) { return E.coches[p].checked; }); }

  async function lancer(E) {
    var passes = choisies(E);
    montrer(E.erreur, false);
    if (!passes.length) { montrer(E.erreur, true); E.erreur.textContent = T("passesplan.rendre.aucune"); return; }
    griser(E.btnRendre, true);
    try {
      var R = await fetch(chemin(E), { method: "POST", headers: { "Content-Type": "application/json" },
                                       body: JSON.stringify({ sequence: !!E.sequence.checked, passes: passes }) });
      var j = await lireJson(R);
      if (E.ferme) return;
      if (!R.ok) throw new Error(detail(j, R.status));
      suivre(E, j.job);
    } catch (e) {
      montrer(E.erreur, true);
      E.erreur.textContent = T("passesplan.rendre.ko", { msg: e.message });
      griser(E.btnRendre, false);
    }
  }

  function montrerJob(E, job) {
    montrer(E.progres, true);
    E.plein.style.width = Math.max(0, Math.min(100, Number(job.progression) || 0)) + "%";
    E.progresTexte.textContent = job.statut === "attente" ? T("passesplan.rendre.attente")
      : job.etape === "rangement" ? T("passesplan.rendre.rangement")
      : T("passesplan.rendre.progres", { k: job.images || 0, n: job.total || 0, passe: job.etape ? nomPasse(job.etape) : "…" });
  }

  async function suivre(E, job) {
    E.job = job;
    griser(E.btnRendre, true);
    montrer(E.btnAnnuler, true);
    montrerJob(E, job);
    var jeton = ++E.jetonSuivi;
    while (!E.ferme && jeton === E.jetonSuivi) {
      await attendre(PAS_MS);
      if (E.ferme) return;
      var j;
      try {
        var R = await fetch("/api/passes/job/" + encodeURIComponent(job.id));
        j = await lireJson(R);
        if (!R.ok) throw new Error(detail(j, R.status));
      } catch (e) {
        montrer(E.erreur, true);
        E.erreur.textContent = T("passesplan.rendre.ko", { msg: e.message });
        break;
      }
      montrerJob(E, j);
      if (j.statut === "attente" || j.statut === "rendu") continue;
      if (j.statut === "erreur") {
        montrer(E.erreur, true);
        E.erreur.textContent = T("passesplan.rendre.ko", { msg: j.erreur || "" });
      } else if (j.statut === "annule") {
        if (E.opts.toast) E.opts.toast(T("passesplan.rendre.annule"));
      } else if (j.statut === "fini" && E.opts.toast) {
        E.opts.toast(T("passesplan.rendre.fini"));
      }
      break;
    }
    if (E.ferme) return;
    montrer(E.btnAnnuler, false);
    montrer(E.progres, false);
    griser(E.btnRendre, false);
    E.job = null;
    await charger(E);
    if (E.opts.apres) E.opts.apres();
  }

  async function annuler(E) {
    if (!E.job) return;
    griser(E.btnAnnuler, true);
    try {
      var R = await fetch("/api/passes/job/" + encodeURIComponent(E.job.id) + "/annuler", { method: "POST" });
      var j = await lireJson(R);
      if (!R.ok) throw new Error(detail(j, R.status));
    } catch (e) {
      montrer(E.erreur, true);
      E.erreur.textContent = T("passesplan.rendre.ko", { msg: e.message });
    } finally {
      griser(E.btnAnnuler, false);
    }
  }

  // ── la bande des passes sous la vignette de chaque carte de plan (Atelier) ──
  function glyphe(id) {
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("class", "dzi dzi--16");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    var u = document.createElementNS(ns, "use");
    u.setAttribute("href", "/shared/icons/dz-icons.svg#" + id);
    svg.appendChild(u);
    return svg;
  }
  function toastAtelier() { return typeof window.toast === "function" ? window.toast : null; }

  // le bouton « Passes Blender » de chaque carte, en fin des actions de sa vignette (après « Revue du plan »)
  function boutons(liste) {
    var cartes = Array.prototype.slice.call(liste.querySelectorAll(".shot-card[data-id]"));
    cartes.forEach(function (carte, i) {
      var hote = carte.querySelector(".entity-actions");
      if (!hote || hote.querySelector(".act-passes")) return;
      var b = el("button", { type: "button", "class": "btn ghost act-passes", "data-dz-passes": "bouton-carte",
                             title: T("passesplan.carte.bouton_t"), "aria-label": T("passesplan.carte.bouton") });
      b.appendChild(glyphe("dz-nav-panneau-calques"));
      b.addEventListener("click", function () {
        ouvrir({ shot: { id: carte.getAttribute("data-id") }, numero: i + 1, toast: toastAtelier(),
                 apres: function () { vignettes(liste, liste.getAttribute("data-dz-chapitre")); } });
      });
      hote.appendChild(b);
    });
  }

  async function vignettes(liste, chapterId) {
    if (!liste || !chapterId) return;
    liste.setAttribute("data-dz-chapitre", chapterId);
    boutons(liste);
    var j;
    try {
      var R = await fetch("/api/passes/chapitre/" + encodeURIComponent(chapterId));
      if (!R.ok) return;
      j = await lireJson(R);
    } catch (e) { return; }
    var plans = (j && j.plans) || {};
    liste.querySelectorAll(".shot-card[data-id]").forEach(function (carte) {
      var id = carte.getAttribute("data-id");
      var ancienne = carte.querySelector("[data-dz-passes='bande']");
      if (ancienne) ancienne.parentNode.removeChild(ancienne);
      var r = plans[id];
      var hote = carte.querySelector(".thumb");
      if (!r || !hote) return;
      var bande = el("div", { style: S.bande, "data-dz-passes": "bande", role: "button", tabindex: "0",
                              title: T("passesplan.bande.titre", { date: String(r.date || "").replace("T", " ").slice(0, 16) }),
                              "aria-label": T("passesplan.bande.aria") });
      PASSES.forEach(function (p) {
        var e = (r.passes || {})[p];
        if (!e || !e.fichiers || !e.fichiers.length) return;
        bande.appendChild(el("img", { src: urlFichier(r.shot_id, r.run, e.fichiers[0]), alt: nomPasse(p),
                                      title: nomPasse(p), style: S.mini, loading: "lazy" }));
      });
      var cartes = Array.prototype.slice.call(liste.querySelectorAll(".shot-card[data-id]"));
      var ouvrirIci = function () {
        ouvrir({ shot: { id: id }, numero: cartes.indexOf(carte) + 1, toast: toastAtelier(),
                 apres: function () { vignettes(liste, chapterId); } });
      };
      bande.addEventListener("click", ouvrirIci);
      bande.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); ouvrirIci(); } });
      hote.appendChild(bande);
    });
  }

  window.__dzPassesPlan = { ouvrir: ouvrir, vignettes: vignettes, PASSES: PASSES.slice() };
})();
