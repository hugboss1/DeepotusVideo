/* Avatar live (t162, 10/10/2026) — l'écran des Personnages et du Recast différé.
   Serveur : /api/avatar-live (backend/app/api/avatar_live_routes.py). Le catalogue des modèles, leurs prix et les
   préréglages sont SERVIS (/recast/modeles) : rien n'est recopié ici. Le 402 d'un plafond est pris par
   /shared/dz-plafonds.js (dialogue « Tirer quand même »), chargé avant ce fichier. Vanilla DOM. */
(function () {
  "use strict";
  var API = "/api/avatar-live";
  // G7 (t168) : les textes passent par dzT (dictionnaire frontend/shared/i18n/avatar.json, FR de référence, EN) ;
  // les <option> aussi, que la surcouche ignore.
  function T(cle, vars) { return window.dzT ? window.dzT(cle, vars) : cle; }
  // G7 : les catalogues du serveur (modèles, préréglages) arrivent en français ; traduits par leur id, sinon tels quels
  function Tid(cle, defaut) { var v = T(cle); return v === cle ? defaut : v; }
  // virgule décimale en français, point en anglais (dz-plafonds formate à la française)
  var EN = !!(window.__dzI18n && window.__dzI18n.langue === "en");
  function dec(t) { return EN ? String(t).replace(",", ".") : String(t).replace(".", ","); }
  document.querySelectorAll("option[data-t]").forEach(function (o) { o.textContent = T(o.dataset.t); });
  var $ = function (id) { return document.getElementById(id); };
  var etat = { cat: null, persos: [], fichiers: [], source: null, modele: "remplacer", pre: "", suivis: {} };

  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "text") n.textContent = attrs[k];
      else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] !== false && attrs[k] != null) n.setAttribute(k, attrs[k] === true ? "" : attrs[k]);
    });
    (kids || []).forEach(function (c) { if (c != null) n.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return n;
  }
  function usd(v) { return dec(window.__dzPlafonds ? window.__dzPlafonds.usd(v) : (Number(v) || 0).toFixed(2) + " $"); }
  // un tarif PAR SECONDE garde ses trois décimales (0,126 $/s, pas 0,13)
  function jid(j) { return j.job_id || j.id; }   // /api/jobs rend « job_id »
  function sec(v) { return dec((Number(v) || 0).toFixed(1)) + " s"; }
  function usdS(v) { return dec((Number(v) || 0).toFixed(3).replace(/0$/, "")) + " $/s"; }
  function msg(id, t, err) { var m = $(id); m.textContent = t || ""; m.classList.toggle("err", !!err); }
  async function lire(r) {
    var j = null;
    try { j = await r.json(); } catch (e) { /* corps vide */ }
    if (!r.ok) {
      var d = j && j.detail;
      throw new Error(typeof d === "string" ? d : (d && d.dz_plafond && d.dz_plafond.message) || ("HTTP " + r.status));
    }
    return j;
  }
  function b64(f) {
    return new Promise(function (ok, ko) {
      var fr = new FileReader();
      fr.onload = function () { ok(String(fr.result).split(",")[1] || ""); };
      fr.onerror = function () { ko(new Error("Lecture du fichier impossible.")); };
      fr.readAsDataURL(f);
    });
  }

  // ── onglets ──
  document.querySelectorAll(".onglet").forEach(function (b) {
    b.addEventListener("click", function () {
      document.querySelectorAll(".onglet").forEach(function (x) {
        var a = x === b; x.classList.toggle("actif", a); x.setAttribute("aria-selected", String(a));
      });
      $("vuePersonnages").hidden = b.dataset.onglet !== "personnages";
      $("vueRecast").hidden = b.dataset.onglet !== "recast";
      $("vueDirect").hidden = b.dataset.onglet !== "direct";
      try { localStorage.setItem("dz_avatar_onglet", b.dataset.onglet); } catch (e) { /* stockage indisponible */ }
    });
  });

  // ── Personnages ──
  function zoneDepot(zone, input, quand) {
    zone.addEventListener("click", function () { input.click(); });
    zone.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
    zone.addEventListener("dragover", function (e) { e.preventDefault(); zone.classList.add("survol"); });
    zone.addEventListener("dragleave", function () { zone.classList.remove("survol"); });
    zone.addEventListener("drop", function (e) { e.preventDefault(); zone.classList.remove("survol"); quand(Array.from(e.dataTransfer.files || [])); });
    input.addEventListener("change", function () { quand(Array.from(input.files || [])); input.value = ""; });
  }
  zoneDepot($("pDepot"), $("pFichiers"), function (fs) {
    var max = (etat.cat && etat.cat.images_max) || 8;
    etat.fichiers = etat.fichiers.concat(fs.filter(function (f) { return /^image\//.test(f.type); })).slice(0, max);
    var v = $("pVignettes"); v.textContent = "";
    etat.fichiers.forEach(function (f) { v.appendChild(el("img", { src: URL.createObjectURL(f), alt: f.name })); });
    majCreer();
  });
  function majCreer() { $("pCreer").disabled = !(etat.fichiers.length && $("pConsent").checked); }
  $("pConsent").addEventListener("change", majCreer);

  $("pCreer").addEventListener("click", async function () {
    $("pCreer").disabled = true; msg("pMsg", T("avatar.perso.creation"));
    try {
      var images = await Promise.all(etat.fichiers.map(b64));
      var voix = $("pVoix").value.trim();
      var r = await fetch(API + "/personnages", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nom: $("pNom").value, images: images, consentement: $("pConsent").checked,
          voix: voix ? { fournisseur: "elevenlabs", voice_id: voix } : {} }) });
      var p = await lire(r);
      msg("pMsg", T("avatar.perso.pret", { nom: p.nom }));
      etat.fichiers = []; $("pVignettes").textContent = ""; $("pNom").value = ""; $("pVoix").value = "";
      $("pConsent").checked = false;
      await chargerPersos();
    } catch (e) { msg("pMsg", e.message, true); }
    majCreer();
  });

  async function chargerPersos() {
    etat.persos = (await lire(await fetch(API + "/personnages"))).personnages || [];
    var g = $("pListe"); g.textContent = "";
    if (!etat.persos.length) g.appendChild(el("p", { class: "vide", text: T("avatar.perso.aucun") }));
    etat.persos.forEach(function (p) {
      g.appendChild(el("article", { class: "perso" }, [
        el("img", { src: API + "/personnages/" + p.id + "/image/0", alt: "", loading: "lazy" }),
        el("div", { class: "corps" }, [
          el("b", { text: p.nom }),
          el("small", { text: T("avatar.perso.photos", { n: p.images }) + (p.voix && p.voix.voice_id ? " · " + T("avatar.perso.voix_de", { id: p.voix.voice_id }) : "") }),
          el("small", { text: T("avatar.perso.consenti_le", { date: String(p.consentement.le || "").slice(0, 10).split("-").reverse().join("/") }) }),
          el("div", { class: "ligne" }, [
            el("button", { type: "button", class: "btn fin", title: T("avatar.perso.cloner_aide"),
              onclick: function () { clonerVoix(p); } }, [el("span", { text: T(p.voix && p.voix.clonee ? "avatar.perso.recloner" : "avatar.perso.cloner") })]),
            el("button", { type: "button", class: "btn fin", onclick: function () { supprimer(p); } }, [
              el("span", { text: T("avatar.perso.supprimer") })])])
        ])
      ]));
    });
    var s = $("rPerso"), avant = s.value; s.textContent = "";
    s.appendChild(el("option", { value: "", text: T("avatar.recast.aucun_perso") }));
    etat.persos.forEach(function (p) { s.appendChild(el("option", { value: p.id, text: p.nom })); });
    if (avant) s.value = avant; else if (etat.persos.length) s.value = etat.persos[etat.persos.length - 1].id;
    majRecast();
  }
  var cible = null;
  $("pVoixFichiers").addEventListener("change", async function () {
    var fs = Array.from($("pVoixFichiers").files || []); $("pVoixFichiers").value = "";
    if (!cible || !fs.length) return;
    msg("pMsg", T("avatar.perso.clonage", { nom: cible.nom }));
    try {
      var fd = new FormData(); fs.slice(0, 5).forEach(function (f) { fd.append("echantillons", f, f.name); });
      fd.append("debruiter", "true");
      await lire(await fetch(API + "/personnages/" + cible.id + "/voix", { method: "POST", body: fd }));
      msg("pMsg", T("avatar.perso.clonee", { nom: cible.nom }));
    } catch (e) { msg("pMsg", e.message, true); }
    chargerPersos();
  });
  function clonerVoix(p) { cible = p; $("pVoixFichiers").click(); }

  async function supprimer(p) {
    var D = window.__dzDialogue;
    var ok = D && D.confirmer ? await D.confirmer(T("avatar.perso.supprimer_question", { nom: p.nom }), { titre: T("avatar.perso.supprimer_titre"), ok: T("avatar.perso.supprimer"), annuler: T("avatar.commun.annuler") }) : false;
    if (!ok) return;
    try { await lire(await fetch(API + "/personnages/" + p.id, { method: "DELETE" })); } catch (e) { msg("pMsg", e.message, true); }
    chargerPersos();
  }

  // ── Recast ──
  zoneDepot($("rDepot"), $("rFichier"), async function (fs) {
    var f = fs[0]; if (!f) return;
    $("rRendu").value = "";
    $("rSourceInfo").textContent = T("avatar.recast.envoi", { nom: f.name });
    try {
      var fd = new FormData(); fd.append("fichier", f, f.name);
      var d = await lire(await fetch(API + "/recast/source", { method: "POST", body: fd }));
      etat.source = { depot: d.depot, duree_s: d.duree_s, nom: f.name };
      $("rSourceInfo").textContent = f.name + " · " + sec(d.duree_s) + " · " + d.largeur + "×" + d.hauteur;
    } catch (e) { etat.source = null; $("rSourceInfo").textContent = e.message; }
    majRecast();
  });
  $("rRendu").addEventListener("change", function () {
    var o = $("rRendu").selectedOptions[0];
    etat.source = o && o.value ? { job_id: o.value, duree_s: Number(o.dataset.duree) || 0, nom: o.textContent } : null;
    $("rSourceInfo").textContent = etat.source ? (etat.source.duree_s ? sec(etat.source.duree_s) : T("avatar.recast.duree_lue")) : "";
    majRecast();
  });

  function majRecast() {
    var cat = etat.cat && etat.cat.recast; if (!cat) return;
    var m = cat.modeles[etat.modele];
    var res = $("rRes"); var avant = res.value; res.textContent = "";
    Object.keys(m.prix_usd_s).forEach(function (k) {
      res.appendChild(el("option", { value: k, text: k === "source" ? T("avatar.recast.res_source") : k }));
    });
    res.value = m.prix_usd_s[avant] != null ? avant : m.defaut;
    $("rOrientChamp").hidden = etat.modele.indexOf("mouvement") !== 0;
    $("rPerso").disabled = !m.personnage;
    var perso = etat.persos.filter(function (x) { return x.id === $("rPerso").value; })[0];
    var aVoix = !!(perso && perso.voix && perso.voix.voice_id);
    $("rVoix").disabled = !aVoix; if (!aVoix) $("rVoix").checked = false;
    var prix = (m.prix_usd_s[res.value] || 0) + ($("rVoix").checked ? (cat.voix_usd_s || 0) : 0);
    var d = etat.source && etat.source.duree_s;
    $("rDevis").textContent = d ? T("avatar.recast.devis", { total: usd(prix * d), duree: sec(d), prix: usdS(prix) }) : T("avatar.recast.prix_s", { prix: usdS(prix) });
    var dureeOk = !d || (d >= cat.duree.min && d <= cat.duree.max);
    if (d && !dureeOk) $("rSourceInfo").textContent = T("avatar.recast.trop_long", { duree: sec(d), min: cat.duree.min, max: cat.duree.max });
    var consigneOk = !(etat.modele === "objet" && !$("rConsigne").value.trim() && !etat.pre);
    $("rLancer").disabled = !(etat.source && dureeOk && consigneOk && (!m.personnage || $("rPerso").value));
    // t168c : brouillon 480p (Wan, Lucy : fal y prend une graine) ; Kling n'en a pas, le bouton le dit
    var br = m.brouillon && m.prix_usd_s[m.brouillon] != null;
    $("rBrouillon").disabled = $("rLancer").disabled || !br;
    $("rBrouillon").title = !br ? T("avatar.brouillon.indispo")
      : T("avatar.brouillon.aide", { total: d ? usd((m.prix_usd_s[m.brouillon] + ($("rVoix").checked ? (cat.voix_usd_s || 0) : 0)) * d) : usdS(m.prix_usd_s[m.brouillon]), res: m.defaut });
    $("rVoixSeule").disabled = !(etat.source && aVoix);
    majDecor();
  }
  ["rPerso", "rRes", "rConsigne", "rOrient", "rVoix"].forEach(function (id) { $(id).addEventListener("input", majRecast); });

  function construireRecast() {
    var cat = etat.cat.recast, box = $("rModeles"); box.textContent = "";
    Object.keys(cat.modeles).forEach(function (k) {
      var m = cat.modeles[k];
      var prix = Object.keys(m.prix_usd_s).map(function (r) { return usdS(m.prix_usd_s[r]) + (r === "source" ? "" : " " + T("avatar.recast.en_res", { res: r })); });
      box.appendChild(el("label", { class: "modele", title: m.note_prix || "" }, [
        el("input", { type: "radio", name: "modele", value: k, checked: k === etat.modele,
          onchange: function () { etat.modele = k; majRecast(); } }),
        el("span", { class: "nom" }, [el("span", { text: Tid("avatar.modele." + k, m.label) }),
          el("span", { class: "prix", text: prix[0] + (prix.length > 1 ? " · " + prix[prix.length - 1] : "") })])
      ]));
    });
    var pre = $("rPre"); pre.textContent = "";
    cat.prereglages.forEach(function (p) {
      var b = el("button", { type: "button", class: "puce", "aria-pressed": "false", text: Tid("avatar.prereglage." + p.id, p.label), onclick: function () {
        etat.pre = etat.pre === p.id ? "" : p.id;
        pre.querySelectorAll(".puce").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b && etat.pre === p.id)); });
        majRecast();
      } });
      pre.appendChild(b);
    });
  }

  async function lancerRecast(brouillon) {
    $("rLancer").disabled = true; $("rBrouillon").disabled = true; msg("rMsg", T("avatar.recast.lancement"));
    try {
      var src = etat.source.job_id ? { job_id: etat.source.job_id } : { depot: etat.source.depot };
      var d = await lire(await fetch(API + "/recast", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: src, personnage_id: $("rPerso").value || null, modele: etat.modele,
          resolution: $("rRes").value, consigne: $("rConsigne").value, prereglage: etat.pre, orientation: $("rOrient").value,
          voix: $("rVoix").checked, brouillon: !!brouillon }) }));
      msg("rMsg", T(brouillon ? "avatar.brouillon.lance" : "avatar.recast.lance", { usd: usd(d.devis_usd) }));
      suivre(d.job_id);
    } catch (e) { msg("rMsg", e.message, true); }
    majRecast();
  }
  $("rLancer").addEventListener("click", function () { lancerRecast(false); });
  $("rBrouillon").addEventListener("click", function () { lancerRecast(true); });

  // t168c : les brouillons finalisables (recette gardée par le serveur), relus à chaque brouillon terminé
  async function chargerBrouillons() {
    try { etat.brouillons = (await lire(await fetch(API + "/recast/brouillons"))).brouillons || {}; } catch (e) { etat.brouillons = {}; }
  }
  async function finaliser(id, bouton) {
    bouton.disabled = true; msg("rMsg", T("avatar.recast.lancement"));
    try {
      var d = await lire(await fetch(API + "/recast/finaliser", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: id }) }));
      msg("rMsg", T("avatar.brouillon.finale_lancee", { usd: usd(d.devis_usd) }));
      await chargerBrouillons();
      var j0 = null; try { j0 = await lire(await fetch("/api/jobs/" + id)); } catch (e) { /* la carte reste telle */ }
      if (j0) carteJob(j0);
      suivre(d.job_id);
    } catch (e) { msg("rMsg", e.message, true); bouton.disabled = false; }
  }

  $("rVoixSeule").addEventListener("click", async function () {
    $("rVoixSeule").disabled = true; msg("rMsg", T("avatar.recast.conversion"));
    try {
      var src = etat.source.job_id ? { job_id: etat.source.job_id } : { depot: etat.source.depot };
      var d = await lire(await fetch(API + "/voix", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: src, personnage_id: $("rPerso").value }) }));
      msg("rMsg", T("avatar.recast.lance", { usd: usd(d.devis_usd) }));
      suivre(d.job_id);
    } catch (e) { msg("rMsg", e.message, true); }
    majRecast();
  });

  // ── G3 : le décor seul (détourage BiRefNet + composition locale) ──
  var fondVideo = null;
  function majDecor() {
    var t = $("dType").value;
    $("dCouleurChamp").hidden = t !== "couleur"; $("dImageChamp").hidden = t !== "image"; $("dVideoChamp").hidden = t !== "video";
    var pret = t === "couleur" || (t === "image" && $("dImage").value) || (t === "video" && fondVideo);
    $("dLancer").disabled = !(etat.source && pret);
  }
  ["dType", "dImage", "dCouleur"].forEach(function (id) { $(id).addEventListener("input", majDecor); });
  zoneDepot($("dDepot"), $("dFichier"), async function (fs) {
    var f = fs[0]; if (!f) return;
    msg("dMsg", T("avatar.decor.envoi_fond"));
    try {
      var fd = new FormData(); fd.append("fichier", f, f.name);
      fondVideo = (await lire(await fetch(API + "/recast/source", { method: "POST", body: fd }))).depot;
      msg("dMsg", T("avatar.decor.fond_nom", { nom: f.name }));
    } catch (e) { fondVideo = null; msg("dMsg", e.message, true); }
    majDecor();
  });
  $("dLancer").addEventListener("click", async function () {
    $("dLancer").disabled = true; msg("dMsg", T("avatar.recast.lancement"));
    var t = $("dType").value;
    var fond = t === "couleur" ? { couleur: $("dCouleur").value } : t === "image" ? { image: $("dImage").value } : { video: fondVideo };
    try {
      var src = etat.source.job_id ? { job_id: etat.source.job_id } : { depot: etat.source.depot };
      var d = await lire(await fetch(API + "/decor", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: src, fond: fond }) }));
      msg("dMsg", d.devis_usd ? T("avatar.decor.lance", { usd: usd(d.devis_usd) }) : T("avatar.decor.a_mesurer"));
      suivre(d.job_id);
    } catch (e) { msg("dMsg", e.message, true); }
    majDecor();
  });
  async function chargerImages() {
    try {
      var d = await lire(await fetch("/api/images"));
      var s = $("dImage"); s.textContent = "";
      (d.images || []).slice().sort(function (a, b) { return (b.mtime || 0) - (a.mtime || 0); }).slice(0, 200)
        .forEach(function (i) { s.appendChild(el("option", { value: i.filename, text: i.filename })); });
    } catch (e) { /* liste facultative */ }
  }

  var LIB = ["queued", "uploading_image", "generating_video", "downloading_video", "generating_voiceover", "merging", "done", "failed"];
  function carteJob(j) {
    var id = jid(j), box = etat.suivis[id];
    if (!box) {
      box = el("article", { class: "job" });
      etat.suivis[id] = box;
      $("rJobs").prepend(box);
    }
    box.textContent = "";
    box.appendChild(el("div", { class: "tete" }, [el("b", { text: j.title || id }),
      el("span", { class: "statut " + j.status, text: LIB.indexOf(j.status) >= 0 ? T("avatar.job." + j.status) : j.status })]));
    if (j.status !== "done" && j.status !== "failed") {
      var g = el("div", { class: "jauge" }, [el("span")]); g.firstChild.style.width = (j.progress || 0) + "%";
      box.appendChild(g);
      box.appendChild(el("small", { class: "msg", text: j.current_step || "" }));
    } else if (j.status === "done") {
      box.appendChild(el("video", { src: "/api/jobs/" + id + "/video", controls: true, preload: "metadata" }));
      var b = etat.brouillons && etat.brouillons[id];
      if (b) {
        var cout = (b.prix_usd_s + (b.voix ? ((etat.cat.recast && etat.cat.recast.voix_usd_s) || 0) : 0)) * (b.duree_s || 0);
        var deja = (b.finales || []).length > 0;
        var bt = el("button", { type: "button", class: deja ? "btn" : "btn plein",
          text: T(deja ? "avatar.brouillon.refinaliser" : "avatar.brouillon.finaliser", { res: b.resolution_finale, total: usd(cout) }) });
        bt.addEventListener("click", function () { finaliser(id, bt); });
        box.appendChild(el("div", { class: "actions" }, [bt]));
        box.appendChild(el("small", { class: "msg", text: T("avatar.brouillon.note") }));
      }
    } else {
      box.appendChild(el("small", { class: "msg err", text: j.error || T("avatar.commun.echec") }));
    }
  }
  async function suivre(id) {
    for (;;) {
      var j;
      try { j = await lire(await fetch("/api/jobs/" + id)); } catch (e) { return; }
      if (j.status === "done" && j.provider === "recast" && etat.brouillons && !(id in etat.brouillons)) await chargerBrouillons();
      carteJob(j);
      if (j.status === "done" || j.status === "failed") return;
      await new Promise(function (ok) { setTimeout(ok, 2000); });
    }
  }

  async function chargerRendus() {
    try {
      var d = await lire(await fetch("/api/jobs?limit=40&video=1"));
      var jobs = Array.isArray(d) ? d : (d.jobs || d.items || []);
      var s = $("rRendu");
      jobs.filter(function (j) { return j.status === "done"; }).forEach(function (j) {
        s.appendChild(el("option", { value: jid(j), "data-duree": j.duration_s || "", text: (j.title || jid(j)).slice(0, 60) }));
      });
      await chargerBrouillons();
      jobs.filter(function (j) { return j.provider === "recast"; }).reverse().forEach(carteJob);
      jobs.filter(function (j) { return j.provider === "recast" && j.status !== "done" && j.status !== "failed"; }).forEach(function (j) { suivre(jid(j)); });
    } catch (e) { /* liste facultative */ }
  }

  // G4 : un enregistrement du Direct rangé en rendu paraît aussitôt dans « Rendus Recast »
  window.addEventListener("dz-avatar-rendu", function (e) { suivre(e.detail); });

  async function demarrer() {
    try {
      var e = await lire(await fetch(API + "/etat"));
      var r = await lire(await fetch(API + "/recast/modeles"));
      etat.cat = e; etat.cat.recast = r;
      $("pConsentTexte").textContent = T("avatar.perso.consentement");
      $("etatCle").textContent = e.cle ? T("avatar.direct.etat_cle") : "";
      construireRecast();
      await chargerPersos();
      await chargerRendus();
      await chargerImages();
      var o = null; try { o = localStorage.getItem("dz_avatar_onglet"); } catch (x) { /* rien */ }
      var b = o && document.querySelector('.onglet[data-onglet="' + o + '"]'); if (b) b.click();
    } catch (x) { msg("pMsg", T("avatar.commun.serveur_muet", { raison: x.message }), true); }
  }
  demarrer();
})();
