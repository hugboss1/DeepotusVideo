/* dz-previs-plan.js — le mode « Previs → plan » de la fiche d'un plan (t335, A5 du lot Scenario, 28/10/2026, spec
   docs/superpowers/specs/2026-10-27-scenario-explorations-design.md). SOURCE : frontend/shared/dz-previs-plan.js ;
   copie OCTET POUR OCTET : frontend/dist/shared/dz-previs-plan.js, servie à /shared/dz-previs-plan.js et chargée par
   une balise classique dans la page de l'Atelier (frontend/atelier/index.html). Le banc
   backend/tests/test_previs_plan_ecran.py refuse toute dérive.

   window.__dzPrevisPlan.ouvrir({shot, numero, toast(msg, err), apres(reponse)}) -> Promise<reponse | null>.
   Une boîte de dialogue, dans l'ordre de la décision :
   - MODÈLE : Seedance 2.5 previs → plan (clip + style frames, le video-to-video de scenario.com) ou Veo 3.1 références
     (style frames seules). Un modèle sans clé reste choisissable : la clé à ajouter est DITE, le 503 tombe au lancement.
   - CLIP DE PREVIS (@Video1, Seedance seulement) : la vidéo du plan d'abord, puis les rendus vidéo de la Bibliothèque
     (GET /api/shots/{id}/previs/sources) ; et la TÂCHE : garder le mouvement et la caméra (editing, défaut) ou s'en
     inspirer à la durée du plan (reference).
   - DURÉE MINIMALE (t336, A6) : un clip plus court que ce que le modèle rend (Seedance 4 s) est conformé avant
     l'envoi — « Étirer puis ré-accélérer » ou « Compléter au noir puis couper » (choix automatique montré, l'autre
     à un clic) ; une phrase dit ce qui sera fait et la durée FACTURÉE qui en découle. Après le rendu, la dérive en
     images est mesurée contre la previs et le rendu recalé à son nombre d'images exact : le dernier rendu du plan
     l'affiche (« dérive : +2 images, recalée »).
   - STYLE FRAMES (@Image1…, 4 au plus) : les images du plan (production, croquis, bornes du Plateau), puis « Plus
     d'images de la Bibliothèque » (GET /api/images) ; l'ordre du clic donne @Image1, @Image2…
   - RÉSOLUTION et PROMPT (proposé par le serveur, modifiable, « Rétablir »).
   - DEVIS : POST /api/shots/{id}/previs/devis à chaque changement (réponse périmée ignorée) — coût, secondes facturées
     (entrée + sortie), notes (troncatures, références non nommées), refus. « Lancer » porte le montant et reste
     inactif tant qu'un refus tient.
   - LANCER : confirmation (window.__dzDialogue.confirmer, montant dit), puis POST /api/shots/{id}/previs
     {…, confirme_cout: true}. 409 : le nouveau devis s'affiche, rien n'est parti. 402 de plafond : l'enveloppe de
     window.fetch posée par dz-plafonds.js montre son dialogue et rejoue sur accord. Réussi : `apres(reponse)` (la
     carte du plan suit le job ; la vidéo rejoint la Bibliothèque avec sa provenance et sa recette), et la boîte se ferme.
   CHARTE : celle de dialogue.js / dz-scan.js (aucun arrondi, en-tête IBM Plex Mono en capitales, jetons --srf-* /
   --brd-* / --txt-* avec replis). Textes : clés previs.* (frontend/shared/i18n/previs.json). Vanilla DOM. */
(function () {
  "use strict";
  if (window.__dzPrevisPlan) return;

  var FRAMES_MAX = 4, BIBLIO_MAX = 60, DELAI_DEVIS_MS = 250;
  var S = {
    voile: "position:fixed;inset:0;z-index:9980;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center",
    boite: "position:relative;width:760px;max-width:94vw;max-height:92vh;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    corps: "padding:12px 14px;overflow-y:auto;display:flex;flex-direction:column;gap:10px;color:var(--txt-base,var(--ink,#cfd6e2))",
    section: "display:flex;flex-direction:column;gap:6px",
    titre: "font:10px 'IBM Plex Mono',monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    note: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    ligne: "display:flex;align-items:center;gap:8px;flex-wrap:wrap",
    grille: "display:flex;flex-wrap:wrap;gap:6px;max-height:190px;overflow-y:auto",
    clip: "display:flex;flex-direction:column;gap:2px;min-width:150px;max-width:220px;padding:6px 8px;border:1px solid var(--brd-soft,var(--stroke,#222830));background:var(--srf-raised,var(--bg-panel-3,#1b2028));cursor:pointer;text-align:left;color:inherit;font:inherit;border-radius:0",
    vignette: "position:relative;width:72px;height:96px;padding:0;border:1px solid var(--brd-soft,var(--stroke,#222830));background:#000;cursor:pointer;border-radius:0;overflow:hidden",
    choisi: "outline:2px solid var(--accent,#2b6fd6);outline-offset:-2px",
    rang: "position:absolute;left:0;top:0;padding:1px 4px;background:var(--accent,#2b6fd6);color:var(--accent-ink,#fff);font:10px 'IBM Plex Mono',monospace",
    legende: "position:absolute;left:0;right:0;bottom:0;padding:1px 3px;background:rgba(0,0,0,.65);color:#e6e9ee;font-size:10px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis",
    champ: "width:100%;box-sizing:border-box;min-height:84px;padding:8px;resize:vertical;border-radius:0;background:transparent;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));font:12px/1.45 'IBM Plex Mono',ui-monospace,monospace",
    devis: "padding:8px 10px;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));display:flex;flex-direction:column;gap:4px",
    prix: "font-size:14px;color:var(--txt-hi,var(--ink-strong,#e6e9ee))",
    erreur: "color:var(--red,#e5484d);font-size:12px",
    mention: "color:var(--amber,#f0b429);font-size:12px",
    pied: "display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
    btn: "min-width:88px;height:28px;padding:0 12px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit",
    ok: "background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6);color:var(--accent-ink,#ffffff)",
    mini: "min-width:0;height:22px;padding:0 6px"
  };
  var ORIGINES = { production: "previs.image.production", croquis: "previs.image.croquis",
                   plateau_debut: "previs.image.plateau_debut", plateau_fin: "previs.image.plateau_fin",
                   bibliotheque: "previs.image.bibliotheque" };
  // t336 : les phrases du conform et ses deux choix (clés écrites en entier : le banc d'écran les relit)
  var CONFORM = { etirer: "previs.conform.etirer", noir: "previs.conform.noir", transcoder: "previs.conform.transcoder" };
  var CHOIX_CONFORM = { etirer: "previs.conform.choix_etirer", noir: "previs.conform.choix_noir" };
  var courant = null;

  function T(cle, v) { return typeof window.dzT === "function" ? window.dzT(cle, v) : cle; }
  function langue() { return typeof window.dzLang === "function" ? window.dzLang() : "fr"; }
  function usd(v) {
    v = Number(v) || 0;
    var t = v !== 0 && Math.abs(v) < 0.1 ? v.toFixed(4).replace(/0+$/, "") : v.toFixed(2);
    if ((t.split(".")[1] || "").length < 2) t = Number(t).toFixed(2);
    return langue() === "en" ? "$" + t : t.replace(".", ",") + " $";
  }
  function sec(v) {
    var t = (Math.round((Number(v) || 0) * 10) / 10).toString();
    return langue() === "en" ? t : t.replace(".", ",");
  }
  function el(tag, attrs, texte) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    if (texte != null) n.textContent = texte;
    return n;
  }
  function bouton(marque, texte, style) {
    return el("button", { type: "button", "data-dz-previs": marque, style: S.btn + (style ? ";" + style : "") }, texte);
  }
  function montrer(n, oui) { if (oui) n.removeAttribute("hidden"); else n.setAttribute("hidden", ""); }
  function griser(n, oui) { if (oui) n.setAttribute("disabled", ""); else n.removeAttribute("disabled"); }
  function detail(j, status) {
    var d = j && j.detail;
    if (typeof d === "string" && d) return d;
    if (d && typeof d.message === "string") return d.message;
    if (d && d.dz_plafond && d.dz_plafond.message) return String(d.dz_plafond.message);
    return "HTTP " + status;
  }
  async function lireJson(R) { try { return await R.json(); } catch (e) { return null; } }
  function section(E, titre, aide) {
    var s = el("div", { style: S.section });
    s.appendChild(el("div", { style: S.titre }, titre));
    if (aide) s.appendChild(el("div", { style: S.note }, aide));
    E.corps.appendChild(s);
    return s;
  }

  function modele(E) {
    return (E.sources && E.sources.modeles || []).find(function (m) { return m.id === E.choix.modele; }) || null;
  }

  /* le corps envoyé au devis ET au tir : le même, par construction */
  function corpsDe(E) {
    var m = modele(E), c = { modele: E.choix.modele, style_frames: E.choix.frames.slice(),
                             resolution: E.choix.resolution, prompt: E.champ.value };
    if (m && m.clip) {
      c.tache = E.choix.tache;
      if (E.choix.clip) c.clip_id = E.choix.clip;
      if (E.choix.conform) c.conform = E.choix.conform;   // t336 : absent = choix automatique du serveur
    }
    return c;
  }

  function fermer(E, valeur) {
    if (!E || E.ferme || E.envoi) return;
    E.ferme = true;
    E.jeton++;
    clearTimeout(E.minuterie);
    document.removeEventListener("keydown", E.touche, true);
    if (E.voile.parentNode) E.voile.parentNode.removeChild(E.voile);
    if (courant === E) courant = null;
    E.resoudre(valeur);
  }

  function ouvrir(opts) {
    opts = opts || {};
    var s = opts.shot;
    if (!s || !s.id) return Promise.resolve(null);
    if (courant && courant.envoi) return Promise.resolve(null);
    if (courant) fermer(courant, null);
    return new Promise(function (resoudre) {
      var E = { opts: opts, shot: s, jeton: 0, ferme: false, envoi: false, resoudre: resoudre, devis: null,
                sources: null, biblio: [], promptTouche: false, minuterie: null,
                choix: { modele: null, clip: null, tache: "editing", frames: [], resolution: "720p", conform: null } };
      courant = E;
      construire(E);
      charger(E);
    });
  }

  function construire(E) {
    var voile = E.voile = el("div", { style: S.voile, role: "dialog", "aria-modal": "true", "class": "dz-previs",
                                      "data-dz-previs": "voile" });
    voile.appendChild(el("style", {}, ".dz-previs [hidden]{display:none!important}"));
    var boite = el("div", { style: S.boite });
    boite.appendChild(el("div", { style: S.tete }, T("previs.boite.titre", { n: E.opts.numero || "" })));
    E.corps = el("div", { style: S.corps });
    E.corps.appendChild(el("div", { style: S.note }, T("previs.boite.intro")));

    var sm = section(E, T("previs.modele.titre"));
    E.selModele = el("select", { "data-dz-previs": "modele" });
    E.selModele.addEventListener("change", function () {
      E.choix.modele = E.selModele.value;
      if (!E.promptTouche) E.champ.value = "";
      majModele(E); relancer(E);
    });
    sm.appendChild(E.selModele);
    E.aideModele = el("div", { style: S.note, "data-dz-previs": "aide-modele" });
    sm.appendChild(E.aideModele);

    var sc = E.secClip = section(E, T("previs.clip.titre"), T("previs.clip.aide"));
    E.grilleClips = el("div", { style: S.grille, "data-dz-previs": "clips" });
    sc.appendChild(E.grilleClips);
    var lt = el("div", { style: S.ligne });
    [["editing", "previs.tache.editing"], ["reference", "previs.tache.reference"]].forEach(function (o) {
      var l = el("label", { style: S.note });
      var r = el("input", { type: "radio", name: "dz-previs-tache", value: o[0], "data-dz-previs": "tache-" + o[0] });
      if (o[0] === E.choix.tache) r.checked = true;
      r.addEventListener("change", function () { if (r.checked) { E.choix.tache = o[0]; relancer(E); } });
      l.appendChild(r); l.appendChild(document.createTextNode(" " + T(o[1])));
      lt.appendChild(l);
    });
    sc.appendChild(lt);
    // t336 : la durée minimale du modèle — ce que le conform fera, au choix, et la durée facturée qui en découle
    var cf = E.boxConform = el("div", { style: S.devis, hidden: "", "data-dz-previs": "conform" });
    cf.appendChild(el("div", { style: S.titre }, T("previs.conform.titre")));
    E.phraseConform = el("div", { "data-dz-previs": "conform-phrase" });
    cf.appendChild(E.phraseConform);
    E.choixConform = el("div", { style: S.ligne, "data-dz-previs": "conform-choix" });
    E.radiosConform = {};
    ["etirer", "noir"].forEach(function (mode) {
      var l = el("label", { style: S.note });
      var r = el("input", { type: "radio", name: "dz-previs-conform", value: mode, "data-dz-previs": "conform-" + mode });
      r.addEventListener("change", function () { if (r.checked) { E.choix.conform = mode; relancer(E); } });
      E.radiosConform[mode] = { radio: r, texte: l };
      l.appendChild(r); l.appendChild(el("span", {}, " " + T(CHOIX_CONFORM[mode])));
      E.choixConform.appendChild(l);
    });
    cf.appendChild(E.choixConform);
    E.factureConform = el("div", { style: S.note, "data-dz-previs": "conform-facture" });
    cf.appendChild(E.factureConform);
    sc.appendChild(cf);
    E.aideRecalage = el("div", { style: S.note, "data-dz-previs": "recalage-aide" }, T("previs.recalage.aide"));
    sc.appendChild(E.aideRecalage);
    E.dernier = el("div", { style: S.note, hidden: "", "data-dz-previs": "recalage-dernier" });
    sc.appendChild(E.dernier);
    // t337 (C4) : le dernier rendu contre sa previs, dans le comparateur commun (/shared/dz-comparateur.js)
    E.comparer = bouton("comparer", T("previs.recalage.comparer"), S.mini);
    E.comparer.setAttribute("hidden", "");
    E.comparer.setAttribute("title", T("previs.recalage.comparer_t"));
    E.comparer.addEventListener("click", function () { comparerDernier(E); });
    sc.appendChild(E.comparer);

    var sf = section(E, T("previs.frames.titre", { max: FRAMES_MAX }), T("previs.frames.aide"));
    E.grilleFrames = el("div", { style: S.grille, "data-dz-previs": "frames" });
    sf.appendChild(E.grilleFrames);
    E.plus = bouton("biblio", T("previs.frames.biblio"), S.mini);
    E.plus.addEventListener("click", function () { chargerBiblio(E); });
    sf.appendChild(E.plus);

    var sr = section(E, T("previs.reglages.titre"));
    var lr = el("label", { style: S.note }, T("previs.resolution.libelle") + " ");
    E.selRes = el("select", { "data-dz-previs": "resolution" });
    E.selRes.addEventListener("change", function () { E.choix.resolution = E.selRes.value; relancer(E); });
    lr.appendChild(E.selRes);
    sr.appendChild(lr);
    sr.appendChild(el("div", { style: S.note }, T("previs.prompt.aide")));
    E.champ = el("textarea", { style: S.champ, "data-dz-previs": "prompt", spellcheck: "false",
                               "aria-label": T("previs.prompt.libelle") });
    E.champ.addEventListener("input", function () { E.promptTouche = true; relancer(E); });
    sr.appendChild(E.champ);
    var rp = bouton("retablir", T("previs.prompt.retablir"), S.mini);
    rp.addEventListener("click", function () { E.promptTouche = false; E.champ.value = ""; relancer(E); });
    sr.appendChild(rp);

    var dv = E.boxDevis = el("div", { style: S.devis, role: "status", "data-dz-previs": "devis" });
    E.prix = el("div", { style: S.prix, "data-dz-previs": "prix" }, T("previs.devis.attente"));
    E.detailDevis = el("div", { style: S.note, "data-dz-previs": "detail" });
    E.notes = el("div", { style: S.note, "data-dz-previs": "notes" });
    E.mention = el("div", { style: S.mention, hidden: "", "data-dz-previs": "mention" });
    E.erreur = el("div", { style: S.erreur, hidden: "", "data-dz-previs": "erreur" });
    [E.prix, E.detailDevis, E.notes, E.mention, E.erreur].forEach(function (n) { dv.appendChild(n); });
    E.corps.appendChild(dv);
    boite.appendChild(E.corps);

    var pied = el("div", { style: S.pied });
    var annuler = bouton("annuler", T("previs.boite.annuler"));
    annuler.addEventListener("click", function () { fermer(E, null); });
    E.lancer = bouton("lancer", T("previs.lancer.libelle"), S.ok);
    griser(E.lancer, true);
    E.lancer.addEventListener("click", function () { lancer(E); });
    pied.appendChild(annuler); pied.appendChild(E.lancer);
    boite.appendChild(pied);
    voile.appendChild(boite);
    voile.addEventListener("click", function (ev) { if (ev.target === voile) fermer(E, null); });
    E.touche = function (ev) { if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); fermer(E, null); } };
    document.addEventListener("keydown", E.touche, true);
    document.body.appendChild(voile);
  }

  async function charger(E) {
    try {
      var R = await fetch("/api/shots/" + encodeURIComponent(E.shot.id) + "/previs/sources");
      var j = await lireJson(R);
      if (!R.ok) throw new Error(detail(j, R.status));
      if (E.ferme) return;
      E.sources = j;
    } catch (e) {
      montrer(E.erreur, true);
      E.erreur.textContent = T("previs.sources.ko", { msg: e.message });
      return;
    }
    E.selModele.textContent = "";
    (E.sources.modeles || []).forEach(function (m) {
      var o = el("option", { value: m.id }, m.label + (m.dispo === false && m.cle
        ? " — " + T("previs.modele.cle_a_ajouter", { cle: m.cle }) : ""));
      E.selModele.appendChild(o);           // jamais désactivée : le refus tombe au lancement (503)
    });
    E.choix.modele = E.sources.defaut || (E.sources.modeles[0] || {}).id;
    E.selModele.value = E.choix.modele;
    var clips = E.sources.clips || [];
    var plan = clips.find(function (c) { return c.origine === "plan"; });
    if (plan) E.choix.clip = plan.job_id;
    var prod = (E.sources.images || []).find(function (i) { return i.origine === "production"; });
    if (prod) E.choix.frames = [prod.nom];
    rendreDernier(E, E.sources.dernier_rendu);
    majModele(E);
    relancer(E);
  }

  function majModele(E) {
    var m = modele(E);
    montrer(E.secClip, !!(m && m.clip));
    E.aideModele.textContent = m ? T(m.clip ? "previs.modele.aide_v2v" : "previs.modele.aide_refs") : "";
    E.selRes.textContent = "";
    ((m && m.resolutions) || []).forEach(function (r) { E.selRes.appendChild(el("option", { value: r }, r)); });
    if (m && m.resolutions && m.resolutions.indexOf(E.choix.resolution) < 0) E.choix.resolution = m.resolutions.indexOf("720p") >= 0 ? "720p" : m.resolutions[0];
    E.selRes.value = E.choix.resolution;
    poserClips(E);
    poserFrames(E);
  }

  function poserClips(E) {
    var g = E.grilleClips;
    g.textContent = "";
    var clips = (E.sources && E.sources.clips) || [];
    if (!clips.length) {
      g.appendChild(el("div", { style: S.note, "data-dz-previs": "clips-vide" }, T("previs.clip.vide")));
      return;
    }
    clips.forEach(function (c) {
      var b = el("button", { type: "button", style: S.clip + (c.job_id === E.choix.clip ? ";" + S.choisi : ""),
                             "data-dz-previs": "clip", "data-job": c.job_id, "aria-pressed": String(c.job_id === E.choix.clip) });
      b.appendChild(el("b", {}, c.titre || c.nom));
      b.appendChild(el("span", { style: S.note }, (c.origine === "plan" ? T("previs.clip.du_plan") + " · " : "")
        + (c.secondes != null ? T("previs.clip.secondes", { s: sec(c.secondes) }) : c.nom)));
      b.addEventListener("click", function () { E.choix.clip = c.job_id; E.choix.conform = null; poserClips(E); relancer(E); });
      g.appendChild(b);
    });
  }

  function images(E) {
    var vus = {}, out = [];
    ((E.sources && E.sources.images) || []).concat(E.biblio).forEach(function (i) {
      if (!vus[i.nom]) { vus[i.nom] = 1; out.push(i); }
    });
    return out;
  }

  function poserFrames(E) {
    var g = E.grilleFrames;
    g.textContent = "";
    var liste = images(E);
    if (!liste.length) g.appendChild(el("div", { style: S.note, "data-dz-previs": "frames-vide" }, T("previs.frames.vide")));
    liste.forEach(function (i) {
      var rang = E.choix.frames.indexOf(i.nom);
      var b = el("button", { type: "button", style: S.vignette + (rang >= 0 ? ";" + S.choisi : ""), title: i.nom,
                             "data-dz-previs": "frame", "data-nom": i.nom, "aria-pressed": String(rang >= 0) });
      var img = el("img", { src: "/api/images/" + encodeURIComponent(i.nom), alt: "", loading: "lazy",
                            style: "width:100%;height:100%;object-fit:cover;display:block" });
      b.appendChild(img);
      if (rang >= 0) b.appendChild(el("span", { style: S.rang }, "@Image" + (rang + 1)));
      b.appendChild(el("span", { style: S.legende }, T(ORIGINES[i.origine] || "previs.image.bibliotheque")));
      b.addEventListener("click", function () {
        var k = E.choix.frames.indexOf(i.nom);
        if (k >= 0) E.choix.frames.splice(k, 1);
        else if (E.choix.frames.length >= FRAMES_MAX) {
          if (E.opts.toast) E.opts.toast(T("previs.frames.plein", { max: FRAMES_MAX }), true);
          return;
        } else E.choix.frames.push(i.nom);
        poserFrames(E); relancer(E);
      });
      g.appendChild(b);
    });
  }

  async function chargerBiblio(E) {
    griser(E.plus, true);
    try {
      var R = await fetch("/api/images");
      var j = await lireJson(R);
      if (!R.ok) throw new Error(detail(j, R.status));
      E.biblio = ((j && j.images) || []).map(function (x) { return typeof x === "string" ? x : x && x.filename; })
        .filter(Boolean).slice(0, BIBLIO_MAX).map(function (n) { return { nom: n, origine: "bibliotheque" }; });
      montrer(E.plus, false);
      poserFrames(E);
    } catch (e) {
      griser(E.plus, false);
      if (E.opts.toast) E.opts.toast(T("previs.frames.biblio_ko", { msg: e.message }), true);
    }
  }

  function relancer(E) {
    clearTimeout(E.minuterie);
    griser(E.lancer, true);
    E.prix.textContent = T("previs.devis.attente");
    E.minuterie = setTimeout(function () { lireDevis(E); }, DELAI_DEVIS_MS);
  }

  async function lireDevis(E) {
    var n = ++E.jeton;
    try {
      var R = await fetch("/api/shots/" + encodeURIComponent(E.shot.id) + "/previs/devis",
                          { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpsDe(E)) });
      var j = await lireJson(R);
      if (n !== E.jeton || E.ferme) return;          // réponse périmée : le choix a changé entre-temps
      if (!R.ok) throw new Error(detail(j, R.status));
      rendreDevis(E, j);
    } catch (e) {
      if (n !== E.jeton || E.ferme) return;
      E.devis = null;
      E.prix.textContent = T("previs.devis.ko");
      montrer(E.erreur, true);
      E.erreur.textContent = e.message;
    }
  }

  function rendreDevis(E, d) {
    E.devis = d;
    if (!E.promptTouche && d.prompt) E.champ.value = d.prompt;
    // preuve t335 : un devis REFUSÉ (clip ou style frame manquants) ne montre pas « 0,00 $ » : il dit ce qui manque
    E.prix.textContent = d.refus ? T("previs.devis.incomplet")
      : d.usd == null ? T("previs.devis.inconnu") : T("previs.devis.prix", { usd: usd(d.usd) });
    E.detailDevis.textContent = d.refus ? ""
      : d.secondes_entree
        ? T("previs.devis.detail_v2v", { entree: sec(d.secondes_entree), sortie: sec(d.secondes_sortie), res: d.resolution || "" })
        : T("previs.devis.detail_refs", { sortie: sec(d.secondes_sortie), res: d.resolution || "" });
    rendreConform(E, d);
    E.notes.textContent = (d.notes || []).length ? T("previs.devis.notes", { notes: d.notes.join(" · ") }) : "";
    montrer(E.mention, !!d.cle_absente);
    E.mention.textContent = d.cle_absente ? T("previs.devis.cle_absente", { cle: d.cle_absente }) : "";
    montrer(E.erreur, !!d.refus);
    E.erreur.textContent = d.refus || "";
    E.lancer.textContent = d.usd == null || d.refus ? T("previs.lancer.libelle") : T("previs.lancer.prix", { usd: usd(d.usd) });
    griser(E.lancer, !!d.refus);
  }

  /* t336 : ce que le conform fera du clip, en clair, et ce qui sera facturé */
  function rendreConform(E, d) {
    var c = d && !d.refus ? d.conform : null;
    montrer(E.boxConform, !!c);
    if (!c) return;
    var v = { clip: sec(c.secondes_clip), plancher: sec(c.plancher_s), k: String(c.facteur).replace(".", langue() === "en" ? "." : ","),
              envoi: sec(c.secondes_envoyees), n: c.images_previs, fps: sec(c.fps_envoye) };
    E.phraseConform.textContent = T(CONFORM[c.mode] || CONFORM.transcoder, v) + (c.auto && c.choix_possibles && c.choix_possibles.length
      ? " " + T("previs.conform.auto") : "");
    var choix = c.choix_possibles || [];
    montrer(E.choixConform, choix.length > 0);
    Object.keys(E.radiosConform).forEach(function (mode) {
      E.radiosConform[mode].radio.checked = mode === c.mode;
    });
    E.factureConform.textContent = T("previs.conform.facture", { envoi: sec(d.secondes_entree), sortie: sec(d.secondes_sortie) });
  }

  /* t337 (C4) : le dernier rendu à droite, sa previs à gauche, sous le rideau du comparateur commun */
  async function comparerDernier(E) {
    try {
      var R = await fetch("/api/shots/" + encodeURIComponent(E.shot.id) + "/revue");
      var j = await lireJson(R);
      if (!R.ok) throw new Error(detail(j, R.status));
      if (!j.previs || !window.__dzComparateur) throw new Error(T("previs.recalage.comparer_absent"));
      var f = String(j.fps || "24").split("/");
      window.__dzComparateur.ouvrir({ a: { src: j.previs.url, type: "video", libelle: T("previs.recalage.cote_previs") },
                                      b: { src: j.rendu.url, type: "video", libelle: T("previs.recalage.cote_rendu") },
                                      titre: T("previs.recalage.comparer"), fps: Number(f[0]) / Number(f[1] || 1) || 24 });
    } catch (e) {
      if (E.opts.toast) E.opts.toast(T("previs.recalage.comparer_ko", { msg: e.message }), true);
    }
  }

  /* t336 : le recalage du dernier rendu « previs » du plan (dérive mesurée contre la previs) */
  function rendreDernier(E, dr) {
    montrer(E.comparer, !!(dr && dr.job_id && dr.status === "done"));
    var r = dr && dr.recalage;
    montrer(E.dernier, !!r);
    if (!r) return;
    var d = Number(r.derive_images) || 0;
    E.dernier.textContent = r.erreur ? T("previs.recalage.echec", { msg: r.erreur })
      : T("previs.recalage.dernier", { derive: r.fiable === false ? T("previs.recalage.non_mesurable")
          : T(Math.abs(d) > 1 ? "previs.recalage.derive_n" : "previs.recalage.derive_1", { d: (d > 0 ? "+" : "") + d }),
          n: r.images });
  }

  async function lancer(E) {
    if (E.envoi || !E.devis || E.devis.refus) return;
    clearTimeout(E.minuterie);
    var montant = E.devis.usd;
    var oui = window.__dzDialogue && window.__dzDialogue.confirmer
      ? await window.__dzDialogue.confirmer(T("previs.lancer.confirmer", { usd: usd(montant), modele: (modele(E) || {}).label || "" }),
                                            { titre: T("previs.lancer.titre"), ok: T("previs.lancer.ok") })
      : false;                                   // sans dialogue maison : rien ne part
    if (!oui || E.ferme) return;
    E.envoi = true;
    griser(E.lancer, true);
    E.prix.textContent = T("previs.lancer.envoi");
    try {
      var c = corpsDe(E);
      c.confirme_cout = true;
      var R = await fetch("/api/shots/" + encodeURIComponent(E.shot.id) + "/previs",
                          { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(c) });
      var j = await lireJson(R);
      if (R.status === 409 && j && j.detail && j.detail.devis) {   // le devis a bougé : le nouveau est montré
        E.envoi = false;
        rendreDevis(E, j.detail.devis);
        montrer(E.erreur, true);
        E.erreur.textContent = T("previs.lancer.devis_change", { usd: usd(j.detail.usd) });
        return;
      }
      if (!R.ok) throw new Error(detail(j, R.status));
      E.envoi = false;
      if (E.opts.toast) E.opts.toast(T("previs.lancer.lance", { usd: usd(j.usd) }));
      if (typeof E.opts.apres === "function") {
        try { await E.opts.apres(j); } catch (e) { /* la page se recharge à sa façon */ }
      }
      fermer(E, j);
    } catch (e) {
      E.envoi = false;
      griser(E.lancer, false);
      E.prix.textContent = E.devis && E.devis.usd != null ? T("previs.devis.prix", { usd: usd(E.devis.usd) }) : "";
      montrer(E.erreur, true);
      E.erreur.textContent = T("previs.lancer.ko", { msg: e.message });
    }
  }

  window.__dzPrevisPlan = { ouvrir: ouvrir, _corpsDe: corpsDe };
})();
