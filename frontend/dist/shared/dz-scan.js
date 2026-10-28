/* dz-scan.js — la boîte « Scanner une page » (t312, tâche 6, 28/10/2026, plan
   docs/superpowers/plans/2026-10-28-t312-scan-texte.md, Décisions 6 à 8). SOURCE : frontend/shared/dz-scan.js ; copie
   OCTET POUR OCTET : frontend/dist/shared/dz-scan.js, servie à /shared/dz-scan.js et chargée par une balise classique
   dans la page de l'Atelier (frontend/atelier/index.html, après dz-plafonds.js et dialogue.js). Le banc
   backend/tests/test_scan_ecran.py refuse toute dérive ; frontend/shared/qa/scan.test.mjs joue la boîte sous node
   (faux DOM, faux fetch, la vraie enveloppe dz-plafonds.js).

   window.__dzScan.ouvrir({hote, serie, inserer(texte), creerChapitres(liste), importerManuscrit(texte)})
     -> Promise<{action} | null>. Une boîte de dialogue :
   - DÉPÔT : glisser-déposer, coller (Ctrl+V d'une image, écouté sur le document tant que la boîte est ouverte) ou
     « Choisir des fichiers… » ; images (image/*) et PDF seulement, DIX au plus (au-delà : message, rien n'est ajouté).
   - LECTURE : langue Français / English / Auto, « Lire » -> POST /api/scan/lire (multipart `pages`, `langue`), délai
     90 s (AbortController) ; une réponse PÉRIMÉE (nouvelle lecture, pages changées, boîte fermée) est ignorée.
     503 {code: "ocr_indisponible", secours_vision, scan_id} : message, et le bouton Claude MIS EN AVANT.
   - APERÇU : le texte lu dans un <textarea> modifiable (aucun HTML injecté) ; les mots incertains (positions du serveur
     en points de code Python, converties ici en indices UTF-16) surlignés par un calque miroir derrière le champ
     (<mark>, textContent seulement) et parcourus par « Précédent » / « Suivant » (sélection dans le champ) ; une
     modification du texte décale les marques qui suivent et retire celles qu'elle touche. Statistiques du nettoyage.
   - SECOURS CLAUDE (payant, jamais automatique) : GET /api/scan/{id}/devis-vision -> « Essayer avec Claude (≈ X) » ;
     au clic, `await window.__dzDialogue.confirmer(` avec le montant (sans dialogue maison : rien ne part), puis
     POST /api/scan/{id}/vision {max_usd: devis, langue}. 409 {message, usd} : le nouveau montant est proposé à son
     tour. 402 de plafond : l'enveloppe de window.fetch posée par dz-plafonds.js montre son dialogue et rejoue sur
     accord ; refusé, son message s'affiche ici. Rendu partiel (partiel, pages_lues, erreur) et réponse tronquée
     (stats.tronque, lots_tronques) : un bandeau le dit. Scan non gardé (en_cache false, scan_id null) : pas de
     bouton, la raison est dite.
   - ENVOI (Décision 7, les fonctions de l'hôte) : « Insérer dans le chapitre » (inserer), « Créer les chapitres »
     (POST /api/scan/decoupage d'abord : titres et tailles montrés, puis creerChapitres([{titre, texte}])),
     « Importer comme manuscrit » (refusé ICI sous 200 caractères, avec la raison, sinon importerManuscrit). Une
     fonction absente de l'hôte : son bouton n'est pas posé. Une fonction qui rend false garde la boîte ouverte.
   REVUE FINALE t312 : le délai de la lecture Claude vient du devis (`delai_s` du serveur + 30 s) ; « Relire » (après
     un délai, un 502/504 ou un 409 vision_en_cours) demande d'abord GET /api/scan/{id}/vision (gratuit) et ne
     propose une nouvelle lecture payante que s'il n'y a rien de gardé ; une réponse `deja_payee` le dit et offre
     « Payer une nouvelle lecture » (confirmation, puis nouvelle: true) ; « Lire » après une lecture Claude demande
     confirmation avant d'écraser ; lecture locale : délai 135 s (le serveur s'arrête à 120 s et rend `partiel`) ;
     découpage : le `texte` exact de chaque chapitre rendu par le serveur ; une note TOUJOURS visible invite à relire
     (les mots faux plausibles ne sont pas surlignés).
   CHARTE : celle de dialogue.js (aucun arrondi, en-tête IBM Plex Mono en capitales, jetons --srf-* / --brd-* /
   --txt-* avec replis). Textes : clés scan.* (frontend/shared/i18n/scan.json). Vanilla DOM. */
(function () {
  "use strict";
  if (window.__dzScan) return;

  var MAX_FICHIERS = 10, DELAI_MS = 135000, DELAI_CLAUDE_MS = 180000, MARGE_CLAUDE_MS = 30000, MIN_MANUSCRIT = 200;
  var POLICE = "13px/1.5 'IBM Plex Mono',ui-monospace,monospace";
  var S = {
    voile: "position:fixed;inset:0;z-index:9990;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center",
    occupe: "position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.45);color:var(--txt-hi,var(--ink-strong,#e6e9ee));font-size:13px;z-index:2",
    boite: "position:relative;width:720px;max-width:94vw;max-height:90vh;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    corps: "padding:12px 14px;overflow-y:auto;display:flex;flex-direction:column;gap:8px;color:var(--txt-base,var(--ink,#cfd6e2))",
    depot: "border:1px dashed var(--brd-hard,var(--stroke-strong,#2a3138));padding:14px;display:flex;flex-direction:column;gap:8px;align-items:flex-start",
    note: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    liste: "display:flex;flex-wrap:wrap;gap:6px",
    puce: "display:inline-flex;align-items:center;gap:4px;padding:2px 6px;border:1px solid var(--brd-soft,var(--stroke,#222830));font-size:11.5px",
    ligne: "display:flex;align-items:center;gap:8px;flex-wrap:wrap",
    etat: "font-size:12px;min-height:16px",
    erreur: "color:var(--red,#e5484d)",
    bandeau: "font-size:12px;padding:6px 8px;border:1px solid var(--amber,#f0b429);color:var(--amber,#f0b429)",
    cadre: "position:relative;height:260px",
    miroir: "position:absolute;inset:0;box-sizing:border-box;margin:0;padding:8px;border:1px solid transparent;overflow:hidden;white-space:pre-wrap;word-wrap:break-word;overflow-wrap:break-word;color:transparent;pointer-events:none;font:" + POLICE,
    champ: "position:relative;display:block;width:100%;height:100%;box-sizing:border-box;margin:0;padding:8px;resize:none;background:transparent;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));font:" + POLICE,
    marque: "background:rgba(240,180,41,.35);color:transparent",
    marqueCourante: "background:rgba(229,72,77,.6);color:transparent",
    pied: "display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
    btn: "min-width:88px;height:28px;padding:0 12px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));cursor:pointer;font:inherit",
    ok: "background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6);color:var(--accent-ink,#ffffff)",
    mini: "min-width:0;height:22px;padding:0 6px"
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
    return el("button", { type: "button", "data-dz-scan": marque, style: S.btn + (style ? ";" + style : "") }, texte);
  }
  function montrer(n, oui) { if (oui) n.removeAttribute("hidden"); else n.setAttribute("hidden", ""); }
  function griser(n, oui) { if (oui) n.setAttribute("disabled", ""); else n.removeAttribute("disabled"); }

  /* les positions du serveur sont des indices de POINTS DE CODE (Python) ; JS compte en unités UTF-16 */
  function tableU16(texte) {
    var t = [0], u = 0;
    Array.from(texte).forEach(function (ch) { u += ch.length; t.push(u); });
    return t;
  }
  function versU16(texte, positions) {
    var t = tableU16(texte), n = t.length - 1;
    return (positions || []).map(function (p) {
      var a = Math.max(0, Math.min(n, Number(p && p.debut) || 0)), b = Math.max(0, Math.min(n, Number(p && p.fin) || 0));
      return { debut: t[a], fin: t[b] };
    }).filter(function (p) { return p.fin > p.debut; }).sort(function (x, y) { return x.debut - y.debut; });
  }

  function accepte(f) {
    var type = String((f && f.type) || "").toLowerCase(), nom = String((f && f.name) || "").toLowerCase();
    return type.indexOf("image/") === 0 || type === "application/pdf"
      || (!type && /\.(png|jpe?g|webp|bmp|tiff?|pdf)$/.test(nom));
  }
  function detail(j, status) {
    var d = j && j.detail;
    if (typeof d === "string" && d) return d;
    if (d && typeof d.message === "string") return d.message;
    if (d && d.dz_plafond && d.dz_plafond.message) return String(d.dz_plafond.message);
    return "HTTP " + status;
  }
  async function lireJson(R) { try { return await R.json(); } catch (e) { return null; } }

  function fermer(E, valeur) {
    if (!E || E.ferme) return;
    if (E.occupe) return;                         // une lecture PAYANTE en cours : sa réponse ne sera jamais perdue
    E.ferme = true;
    E.jeton++;
    if (E.ctrl) { try { E.ctrl.abort(); } catch (e) { /* déjà fini */ } }
    if (E.minuterie) clearTimeout(E.minuterie);
    try { document.removeEventListener("paste", E.coller); } catch (e) { /* vieux moteur */ }
    if (E.voile.parentNode) E.voile.parentNode.removeChild(E.voile);
    if (courant === E) courant = null;
    E.resoudre(valeur);
  }

  function ouvrir(opts) {
    opts = opts || {};
    if (courant && courant.occupe) return Promise.resolve(null);
    if (courant) fermer(courant, null);
    return new Promise(function (resoudre) {
      var E = { opts: opts, fichiers: [], jeton: 0, jetonClaude: 0, scanId: null, devis: null, marques: [], idx: -1, base: "",
                ferme: false, resoudre: resoudre, decoupage: null, occupe: false, envoi: false };
      courant = E;
      construire(E);
    });
  }

  function construire(E) {
    var voile = E.voile = el("div", { style: S.voile, role: "dialog", "aria-modal": "true", "class": "dz-scan", "data-dz-scan": "voile" });
    // preuve t312 (28/10) : un style `display:flex` en ligne l'emporte sur l'attribut `hidden` → tout élément masqué
    // de la boîte reste invisible, quel que soit son style
    voile.appendChild(el("style", {}, ".dz-scan [hidden]{display:none!important}"));
    var boite = el("div", { style: S.boite });
    boite.appendChild(el("div", { style: S.tete }, T("scan.boite.titre")));
    var corps = el("div", { style: S.corps });

    // ── dépôt
    var depot = E.depot = el("div", { style: S.depot, "data-dz-scan": "depot" });
    depot.appendChild(el("div", { style: S.note }, T("scan.depot.invite")));
    var entree = E.entree = el("input", { type: "file", multiple: "", accept: "image/*,application/pdf", hidden: "", "data-dz-scan": "fichiers" });
    var choisir = bouton("choisir", T("scan.depot.choisir"));
    choisir.addEventListener("click", function () { entree.click(); });
    entree.addEventListener("change", function () { ajouter(E, entree.files); try { entree.value = ""; } catch (e) { /* lecture seule */ } });
    depot.addEventListener("dragover", function (e) { e.preventDefault(); depot.setAttribute("data-survol", ""); });
    depot.addEventListener("dragleave", function () { depot.removeAttribute("data-survol"); });
    depot.addEventListener("drop", function (e) {
      e.preventDefault(); depot.removeAttribute("data-survol");
      ajouter(E, e.dataTransfer && e.dataTransfer.files);
    });
    depot.appendChild(choisir); depot.appendChild(entree);
    E.liste = el("div", { style: S.liste, "data-dz-scan": "liste" });
    depot.appendChild(E.liste);
    corps.appendChild(depot);

    // ── langue + lire
    var ligne = el("div", { style: S.ligne });
    var lab = el("label", { style: S.note }, T("scan.langue.libelle") + " ");
    var choix = E.langue = el("select", { "data-dz-scan": "langue" });
    [["fr", "scan.langue.fr"], ["en", "scan.langue.en"], ["auto", "scan.langue.auto"]].forEach(function (o) {
      choix.appendChild(el("option", { value: o[0] }, T(o[1])));
    });
    // preuve t312 (28/10) : la langue du TEXTE n'est pas celle de l'interface (une page française lue en « English »
    // sort très abîmée) → « Auto » par défaut, qui reconnaît la langue de chaque page
    choix.value = "auto";
    lab.appendChild(choix); ligne.appendChild(lab);
    E.lire = bouton("lire", T("scan.lecture.lire"), S.ok);
    E.lire.addEventListener("click", function () { lire(E); });
    ligne.appendChild(E.lire);
    corps.appendChild(ligne);

    E.etat = el("div", { style: S.etat, role: "status", "data-dz-scan": "etat" });
    corps.appendChild(E.etat);
    E.bandeau = el("div", { style: S.bandeau, hidden: "", "data-dz-scan": "bandeau" });
    corps.appendChild(E.bandeau);

    // ── secours Claude
    var secours = el("div", { style: S.ligne });
    E.claude = bouton("claude", "", "");
    montrer(E.claude, false);
    E.claude.addEventListener("click", function () { claude(E); });
    E.noteClaude = el("span", { style: S.note, hidden: "", "data-dz-scan": "note-claude" });
    E.relire = bouton("relire", T("scan.claude.relire"), "");
    montrer(E.relire, false);
    E.relire.addEventListener("click", function () { relire(E); });
    E.nouvelle = bouton("nouvelle", "", "");
    montrer(E.nouvelle, false);
    E.nouvelle.addEventListener("click", function () { claude(E, true); });
    secours.appendChild(E.claude); secours.appendChild(E.relire); secours.appendChild(E.nouvelle); secours.appendChild(E.noteClaude);
    corps.appendChild(secours);

    // ── aperçu
    var res = E.resultat = el("div", { hidden: "", style: "display:flex;flex-direction:column;gap:6px", "data-dz-scan": "resultat" });
    E.stats = el("div", { style: S.note, "data-dz-scan": "stats" });
    res.appendChild(E.stats);
    var nav = el("div", { style: S.ligne });
    E.prec = bouton("prec", T("scan.incertains.precedent"), S.mini);
    E.suiv = bouton("suiv", T("scan.incertains.suivant"), S.mini);
    E.compteur = el("span", { style: S.note, "data-dz-scan": "compteur" });
    E.prec.addEventListener("click", function () { aller(E, E.idx < 0 ? -1 : E.idx - 1); });
    E.suiv.addEventListener("click", function () { aller(E, E.idx + 1); });
    nav.appendChild(E.prec); nav.appendChild(E.compteur); nav.appendChild(E.suiv);
    res.appendChild(nav);
    res.appendChild(el("div", { style: S.note }, T("scan.apercu.libelle")));
    var cadre = el("div", { style: S.cadre });
    E.miroir = el("div", { style: S.miroir, "aria-hidden": "true", "data-dz-scan": "miroir" });
    E.champ = el("textarea", { style: S.champ, spellcheck: "false", "aria-label": T("scan.apercu.libelle"), "data-dz-scan": "texte" });
    E.champ.addEventListener("input", function () { editer(E); });
    E.champ.addEventListener("scroll", function () { E.miroir.scrollTop = E.champ.scrollTop; });
    cadre.appendChild(E.miroir); cadre.appendChild(E.champ);
    res.appendChild(cadre);
    res.appendChild(el("div", { style: S.note, "data-dz-scan": "note-relire" }, T("scan.apercu.relire_note")));
    corps.appendChild(res);

    // ── découpage proposé
    E.coupe = el("div", { hidden: "", style: "display:flex;flex-direction:column;gap:4px", "data-dz-scan": "decoupage" });
    corps.appendChild(E.coupe);

    boite.appendChild(corps);
    E.voileOccupe = el("div", { hidden: "", role: "status", "data-dz-scan": "occupe", style: S.occupe }, T("scan.claude.en_cours"));
    boite.appendChild(E.voileOccupe);

    // ── pied : envoi + fermer
    var pied = el("div", { style: S.pied });
    E.envois = [];
    [["inserer", "inserer", "scan.envoi.inserer"], ["chapitres", "creerChapitres", "scan.envoi.chapitres"],
     ["manuscrit", "importerManuscrit", "scan.envoi.manuscrit"]].forEach(function (a) {
      if (typeof E.opts[a[1]] !== "function") return;
      var b = bouton(a[0], T(a[2]));
      montrer(b, false);
      b.addEventListener("click", function () { envoyer(E, a[0]); });
      E.envois.push(b); pied.appendChild(b);
    });
    var f = E.fermer = bouton("fermer", T("scan.boite.fermer"));
    f.addEventListener("click", function () { fermer(E, null); });
    pied.appendChild(f);
    boite.appendChild(pied);
    voile.appendChild(boite);
    voile.addEventListener("keydown", function (e) { clavier(E, e); });

    E.coller = function (e) { coller(E, e); };
    document.addEventListener("paste", E.coller);
    (document.body || document.documentElement).appendChild(voile);
    majListe(E);
    try { choisir.focus(); } catch (e) { /* pas de focus possible */ }
  }

  /* le clavier : Échap ferme (sauf lecture payante en cours), Tab reste DANS la boîte */
  function focalisables(n, out) {
    out = out || [];
    if (!n || (n.hasAttribute && n.hasAttribute("hidden"))) return out;
    var tag = String(n.tagName || "").toUpperCase();
    if ((tag === "BUTTON" || tag === "SELECT" || tag === "TEXTAREA") && !n.hasAttribute("disabled")) out.push(n);
    Array.prototype.forEach.call(n.children || [], function (c) { focalisables(c, out); });
    return out;
  }
  function clavier(E, e) {
    if (!e) return;
    if (e.key === "Escape") { fermer(E, null); return; }
    if (e.key !== "Tab") return;
    var liste = focalisables(E.voile);
    if (!liste.length) { if (e.preventDefault) e.preventDefault(); return; }
    var actif = document.activeElement, i = liste.indexOf(actif);
    var cible = null;
    if (i < 0) cible = e.shiftKey ? liste[liste.length - 1] : liste[0];
    else if (e.shiftKey && i === 0) cible = liste[liste.length - 1];
    else if (!e.shiftKey && i === liste.length - 1) cible = liste[0];
    if (cible) { if (e.preventDefault) e.preventDefault(); try { cible.focus(); } catch (x) { /* caché */ } }
  }

  /* le verrou d'une lecture PAYANTE : tout ce qui pourrait la périmer ou la doubler est grisé, la boîte reste ouverte */
  function verrouiller(E, oui) {
    E.occupe = !!oui;
    montrer(E.voileOccupe, !!oui);
    var boutons = focalisables(E.voile).concat([E.lire, E.claude, E.relire, E.nouvelle, E.fermer, E.entree], E.envois);
    tous(E.voile).forEach(function (n) { if (String(n.tagName || "").toUpperCase() === "BUTTON") boutons.push(n); });
    boutons.forEach(function (b) { if (b && b.getAttribute("data-dz-scan") !== "prec" && b.getAttribute("data-dz-scan") !== "suiv") griser(b, !!oui); });
    E.champ.readOnly = !!oui;
    if (!oui) majEnvoi(E);
  }
  function tous(n, out) {
    out = out || [];
    if (!n) return out;
    out.push(n);
    Array.prototype.forEach.call(n.children || [], function (c) { tous(c, out); });
    return out;
  }
  /* un envoi en cours : ses boutons grisés jusqu'à la réponse de l'hôte (aucun double envoi) */
  function majEnvoi(E) {
    var b = E.envoi || E.occupe;
    E.envois.forEach(function (x) { griser(x, b); });
    tous(E.coupe).forEach(function (n) { if (String(n.tagName || "").toUpperCase() === "BUTTON") griser(n, b); });
  }

  function dire(E, texte, erreur) {
    E.etat.textContent = texte || "";
    if (erreur) E.etat.setAttribute("data-erreur", ""); else E.etat.removeAttribute("data-erreur");
    E.etat.setAttribute("style", S.etat + (erreur ? ";" + S.erreur : ""));
  }
  function banniere(E, lignes) {
    E.bandeau.textContent = "";
    lignes.forEach(function (l) { E.bandeau.appendChild(el("div", null, l)); });
    montrer(E.bandeau, lignes.length > 0);
  }

  // ───────────────────────────────────────────── dépôt
  function ajouter(E, liste) {
    var neufs = Array.prototype.slice.call(liste || []);
    if (!neufs.length) return;
    if (E.occupe) { dire(E, T("scan.depot.occupe"), true); return; }
    var refus = neufs.filter(function (f) { return !accepte(f); });
    if (refus.length) { dire(E, T("scan.fichiers.refuse", { nom: refus[0].name || "?" }), true); return; }
    if (E.fichiers.length + neufs.length > MAX_FICHIERS) {
      dire(E, T("scan.fichiers.trop", { n: E.fichiers.length + neufs.length }), true);
      return;
    }
    E.fichiers = E.fichiers.concat(neufs);
    E.jeton++;                                    // une lecture en cours porte sur d'autres pages : périmée
    dire(E, "");
    majListe(E);
  }
  function coller(E, e) {
    var items = (e && e.clipboardData && e.clipboardData.items) || [];
    var images = [];
    Array.prototype.forEach.call(items, function (it) {
      if (it && it.kind === "file" && String(it.type || "").indexOf("image/") === 0) {
        var f = it.getAsFile && it.getAsFile();
        if (f) images.push(f);
      }
    });
    if (!images.length) return;                   // un collage de texte dans l'aperçu suit son cours
    if (e.preventDefault) e.preventDefault();
    ajouter(E, images);
  }
  function majListe(E) {
    E.liste.textContent = "";
    E.fichiers.forEach(function (f, i) {
      var p = el("span", { style: S.puce, "data-dz-scan": "page" }, String(f.name || "page-" + (i + 1)));
      var x = el("button", { type: "button", style: S.btn + ";" + S.mini, "data-dz-scan": "retirer",
                             "aria-label": T("scan.depot.retirer", { nom: f.name || "" }), title: T("scan.depot.retirer", { nom: f.name || "" }) }, "×");
      x.addEventListener("click", function () { if (E.occupe) return; E.fichiers.splice(i, 1); E.jeton++; majListe(E); });
      if (E.occupe) griser(x, true);
      p.appendChild(x);
      E.liste.appendChild(p);
    });
    if (E.fichiers.length) E.liste.appendChild(el("span", { style: S.note }, T("scan.fichiers.prets", { n: E.fichiers.length })));
  }

  // ───────────────────────────────────────────── lecture locale
  async function lire(E) {
    if (E.occupe) return;
    if (!E.fichiers.length) { dire(E, T("scan.fichiers.aucun"), true); return; }
    if (E.moteur === "claude" && E.champ.value.trim()) {     // m3 : une transcription PAYÉE ne s'écrase pas sans accord
      var D = window.__dzDialogue, oui = false;
      if (D && typeof D.confirmer === "function") {
        try { oui = !!(await D.confirmer(T("scan.lire.ecraser"), { titre: T("scan.claude.titre"), ok: T("scan.lire.ecraser_ok") })); } catch (e) { oui = false; }
      }
      if (!oui) { dire(E, T("scan.lire.garde")); return; }
      if (E.occupe || E.ferme) return;
    }
    var jeton = ++E.jeton;
    if (E.ctrl) { try { E.ctrl.abort(); } catch (e) { /* fini */ } }
    if (E.minuterie) clearTimeout(E.minuterie);
    var ctrl = E.ctrl = typeof AbortController === "function" ? new AbortController() : null;
    var expire = false;
    E.minuterie = setTimeout(function () { expire = true; if (ctrl) ctrl.abort(); }, DELAI_MS);
    var fd = new FormData();
    E.fichiers.forEach(function (f) { fd.append("pages", f, f.name || "page"); });
    fd.append("langue", E.langue.value || "fr");
    dire(E, T("scan.lecture.en_cours", { n: E.fichiers.length }));
    banniere(E, []);
    proposerClaude(E, null, false, false);        // le devis de la lecture précédente ne vaut plus
    montrer(E.relire, false); montrer(E.nouvelle, false);
    var R, j;
    try {
      R = await fetch("/api/scan/lire", { method: "POST", body: fd, signal: ctrl ? ctrl.signal : undefined });
      j = await lireJson(R);
    } catch (e) {
      if (jeton !== E.jeton) return;
      clearTimeout(E.minuterie);
      dire(E, expire ? T("scan.lecture.delai") : T("scan.lecture.echec", { msg: (e && e.message) || "?" }), true);
      return;
    }
    if (jeton !== E.jeton) return;                // réponse périmée : ignorée
    clearTimeout(E.minuterie);
    if (R.status === 503 && j && j.detail && j.detail.code === "ocr_indisponible") {
      E.scanId = j.detail.scan_id || null;
      dire(E, T("scan.ocr.indisponible", { msg: j.detail.message || "" }), true);
      proposerClaude(E, j.detail.secours_vision, true, j.detail.en_cache === false || !E.scanId);
      return;
    }
    if (!R.ok) { dire(E, T("scan.lecture.echec", { msg: detail(j, R.status) }), true); return; }
    afficher(E, j);
    if (j.partiel) banniere(E, [T("scan.bandeau.lecture_partielle", { de: (Number(j.pages_lues) || 0) + 1 })]);
    E.scanId = j.scan_id || null;
    if (j.moteur === "texte") { proposerClaude(E, null, false, false); return; }
    if (!E.scanId || j.en_cache === false) { proposerClaude(E, null, false, true); return; }
    try {
      var D = await fetch("/api/scan/" + encodeURIComponent(E.scanId) + "/devis-vision");
      var d = await lireJson(D);
      if (jeton !== E.jeton) return;
      proposerClaude(E, D.ok ? d : null, false, false);
    } catch (e) { /* sans devis : pas de bouton */ }
  }

  function proposerClaude(E, devis, enAvant, sansCache) {
    E.devis = devis || null;
    montrer(E.noteClaude, false);
    montrer(E.claude, false);
    if (sansCache) { E.noteClaude.textContent = T("scan.claude.sans_cache"); montrer(E.noteClaude, true); return; }
    if (!devis) return;
    if (!devis.disponible) {
      E.noteClaude.textContent = T("scan.claude.indisponible", { raison: devis.raison || "" });
      montrer(E.noteClaude, true);
      return;
    }
    E.claude.textContent = T("scan.claude.bouton", { usd: usd(devis.usd) });
    E.claude.setAttribute("style", S.btn + (enAvant ? ";" + S.ok : ""));
    if (enAvant) { E.claude.setAttribute("data-mis-en-avant", ""); E.noteClaude.textContent = T("scan.ocr.secours"); montrer(E.noteClaude, true); }
    else E.claude.removeAttribute("data-mis-en-avant");
    griser(E.claude, false);
    montrer(E.claude, true);
  }

  // ───────────────────────────────────────────── aperçu
  function afficher(E, r) {
    var texte = String((r && r.texte) || "");
    E.moteur = (r && r.moteur) || "";
    E.champ.value = texte;
    E.base = texte;
    E.marques = versU16(texte, r && r.incertains);
    E.idx = -1;
    var st = (r && r.stats) || {};
    var morceaux = [T("scan.stats.pages", { n: r.pages != null ? r.pages : (st.pages || 0) }), T("scan.stats.mots", { n: st.mots || 0 })];
    [["colonnes", "scan.stats.colonnes"], ["folios_retires", "scan.stats.folios"], ["titres_retires", "scan.stats.titres"],
     ["cesures", "scan.stats.cesures"], ["pages_texte", "scan.stats.pages_texte"]].forEach(function (k) {
      if (Number(st[k[0]]) > (k[0] === "colonnes" ? 1 : 0)) morceaux.push(T(k[1], { n: st[k[0]] }));
    });
    morceaux.push(T("scan.stats.incertains", { n: E.marques.length }));
    if (r.moteur) morceaux.push(T("scan.moteur." + (["windows", "texte", "claude"].indexOf(r.moteur) >= 0 ? r.moteur : "windows")));
    E.stats.textContent = morceaux.join(" · ");
    dire(E, texte.trim() ? "" : T("scan.lecture.vide"), !texte.trim());
    montrer(E.resultat, true);
    montrer(E.coupe, false);
    E.envois.forEach(function (b) { montrer(b, true); });
    peindre(E);
  }

  function peindre(E) {
    var texte = E.champ.value, m = E.miroir, k = 0;
    m.textContent = "";
    E.marques.forEach(function (p, i) {
      if (p.debut > k) m.appendChild(el("span", null, texte.slice(k, p.debut)));
      m.appendChild(el("mark", { "data-dz-scan": "incertain", "data-i": String(i), style: i === E.idx ? S.marqueCourante : S.marque },
                       texte.slice(p.debut, p.fin)));
      k = p.fin;
    });
    m.appendChild(el("span", null, texte.slice(k) + "\n"));
    // preuve t312 (28/10) : la barre de défilement du champ réduit sa largeur utile ; le miroir garde la même marge à
    // droite, sinon ses lignes se coupent ailleurs et les surlignages glissent
    var barre = (E.champ.offsetWidth || 0) - (E.champ.clientWidth || 0) - 2;
    if (m.style) m.style.paddingRight = (8 + Math.max(0, barre)) + "px";
    var n = E.marques.length;
    E.compteur.textContent = !n ? T("scan.incertains.aucun") : T("scan.incertains.compteur", { i: E.idx >= 0 ? E.idx + 1 : 0, n: n });
    griser(E.prec, !n); griser(E.suiv, !n);
  }

  function aller(E, i) {
    var n = E.marques.length;
    if (!n) return;
    E.idx = ((i % n) + n) % n;
    var p = E.marques[E.idx];
    try { E.champ.focus(); E.champ.setSelectionRange(p.debut, p.fin); } catch (e) { /* champ caché */ }
    peindre(E);
  }

  /* une modification : préfixe et suffixe communs ; les marques après la zone touchée se décalent, celles qu'elle
     touche disparaissent (le mot a été corrigé) */
  function editer(E) {
    var a = E.base, b = E.champ.value;
    var p = 0, max = Math.min(a.length, b.length);
    while (p < max && a.charCodeAt(p) === b.charCodeAt(p)) p++;
    var s = 0;
    while (s < max - p && a.charCodeAt(a.length - 1 - s) === b.charCodeAt(b.length - 1 - s)) s++;
    var finA = a.length - s, delta = b.length - a.length;
    E.marques = E.marques.filter(function (m) { return m.fin <= p || m.debut >= finA; })
      .map(function (m) { return m.debut >= finA ? { debut: m.debut + delta, fin: m.fin + delta } : m; });
    if (E.idx >= E.marques.length) E.idx = E.marques.length - 1;
    E.base = b;
    peindre(E);
  }

  // ───────────────────────────────────────────── secours Claude
  async function claude(E, nouvelle) {
    if (!E.scanId || !E.devis || E.occupe) return;
    var D = window.__dzDialogue;
    if (!D || typeof D.confirmer !== "function") { dire(E, T("scan.claude.annule"), true); return; }
    var montant = Number(E.devis.usd) || 0;
    var question = T(nouvelle ? "scan.claude.nouvelle_confirmer" : "scan.claude.confirmer",
                     { n: E.devis.pages || E.fichiers.length || 1, nom: E.devis.nom || "Claude", usd: usd(montant) });
    var delaiMs = Number(E.devis.delai_s) > 0 ? Number(E.devis.delai_s) * 1000 + MARGE_CLAUDE_MS : DELAI_CLAUDE_MS;
    var jeton = ++E.jetonClaude;                  // son PROPRE jeton : aucune autre action ne périme une lecture payée
    verrouiller(E, true);
    montrer(E.voileOccupe, false);                // le voile « lecture en cours » ne vient qu'avec l'appel
    montrer(E.relire, false); montrer(E.nouvelle, false);
    try {
      for (;;) {
        var oui = false;
        try { oui = !!(await D.confirmer(question, { titre: T("scan.claude.titre"), ok: T("scan.claude.ok") })); } catch (e) { oui = false; }
        if (!oui) { dire(E, T("scan.claude.annule")); return; }
        dire(E, T("scan.claude.en_cours"));
        montrer(E.voileOccupe, true);
        var ctrl = typeof AbortController === "function" ? new AbortController() : null, expire = false;
        var minut = setTimeout(function () { expire = true; if (ctrl) ctrl.abort(); }, delaiMs);
        var R, j;
        try {
          R = await fetch("/api/scan/" + encodeURIComponent(E.scanId) + "/vision", {
            method: "POST", headers: { "Content-Type": "application/json" }, signal: ctrl ? ctrl.signal : undefined,
            body: JSON.stringify(nouvelle ? { max_usd: montant, langue: E.langue.value || "auto", nouvelle: true }
                                          : { max_usd: montant, langue: E.langue.value || "auto" }) });
          j = await lireJson(R);
        } catch (e) {
          clearTimeout(minut);
          if (expire) {                            // la lecture a pu être facturée : on le dit, « Relire » reste possible
            dire(E, T("scan.claude.delai"), true);
            montrer(E.claude, false); montrer(E.relire, true);
          } else dire(E, T("scan.claude.echec", { msg: (e && e.message) || "?" }), true);
          return;
        }
        clearTimeout(minut);
        montrer(E.voileOccupe, false);
        if (jeton !== E.jetonClaude) return;      // garde de principe : le verrou empêche une seconde lecture
        if (R.status === 409 && j && j.detail && j.detail.code === "vision_en_cours") {
          dire(E, T("scan.claude.encore"), true);
          montrer(E.claude, false); montrer(E.relire, true);
          return;
        }
        if (R.status === 409 && j && j.detail && j.detail.usd != null) {
          montant = Number(j.detail.usd) || 0;
          E.devis = Object.assign({}, E.devis, { usd: montant });
          E.claude.textContent = T("scan.claude.bouton", { usd: usd(montant) });
          question = T("scan.claude.cout_change", { usd: usd(montant) });
          continue;
        }
        if (!R.ok) {
          dire(E, T("scan.claude.echec", { msg: detail(j, R.status) }), true);
          if (R.status === 502 || R.status === 504) { montrer(E.claude, false); montrer(E.relire, true); }   // m2 : peut-être facturée
          return;
        }
        montrerVision(E, j);
        return;
      }
    } catch (e) {
      dire(E, T("scan.claude.echec", { msg: (e && e.message) || "?" }), true);
    } finally {
      montrer(E.voileOccupe, false);
      verrouiller(E, false);
    }
  }

  /* une transcription Claude reçue (payée maintenant ou déjà payée et gardée par le serveur) */
  function montrerVision(E, j) {
    E.jeton++;                                    // une lecture locale ou un découpage d'avant ne remplaceront pas ce texte
    afficher(E, j);
    montrer(E.claude, false); montrer(E.noteClaude, false); montrer(E.relire, false); montrer(E.nouvelle, false);
    if (j.deja_payee) {
      dire(E, T("scan.claude.deja_payee"));
      if (E.devis && E.devis.disponible !== false) {
        E.nouvelle.textContent = T("scan.claude.nouvelle", { usd: usd(E.devis.usd) });
        griser(E.nouvelle, false);
        montrer(E.nouvelle, true);
      }
    }
    var lignes = [];
    if (j.partiel) {
      var de = Number(j.premiere_page_non_lue) || ((Number(j.pages_lues) || 0) + 1);   // m5 : numéro dans le dépôt
      lignes.push(T("scan.bandeau.partiel", { de: de,
        raison: T(j.erreur === "plafond" ? "scan.partiel.plafond" : "scan.partiel.appel"), usd: usd(j.usd) }));
    }
    var st = j.stats || {};
    if (st.tronque) {
      var lots = (st.lots_tronques || []).map(function (l) { return l[0] === l[1] ? String(l[0]) : l[0] + "–" + l[1]; }).join(", ");
      lignes.push(T("scan.bandeau.tronque", { lots: lots || "?" }));
    }
    banniere(E, lignes);
  }

  /* « Relire » : d'abord la transcription PAYÉE gardée par le serveur (gratuit) ; rien de gardé -> lecture payante
     (avec sa confirmation) ; encore en cours -> on le dit, « Relire » reste */
  async function relire(E) {
    if (!E.scanId || E.occupe) return;
    var jeton = E.jetonClaude;
    verrouiller(E, true);
    montrer(E.voileOccupe, false);
    var R, j;
    try {
      R = await fetch("/api/scan/" + encodeURIComponent(E.scanId) + "/vision");
      j = await lireJson(R);
    } catch (e) {
      verrouiller(E, false);
      dire(E, T("scan.claude.echec", { msg: (e && e.message) || "?" }), true);
      return;
    }
    verrouiller(E, false);
    if (jeton !== E.jetonClaude || E.ferme) return;
    if (R.ok && j) { montrerVision(E, j); return; }
    if (R.status === 409) { dire(E, T("scan.claude.encore"), true); montrer(E.relire, true); return; }
    if (R.status === 404 && E.devis) { montrer(E.relire, false); dire(E, T("scan.claude.rien_garde")); return claude(E); }
    dire(E, T("scan.claude.echec", { msg: detail(j, R.status) }), true);
  }

  // ───────────────────────────────────────────── envoi
  /* une fonction de l'hôte : boutons d'envoi grisés jusqu'à sa réponse (aucun double envoi) ; false = boîte gardée ;
     une erreur = son message DANS la boîte ; creerChapitres peut dire combien ont été créés avant l'échec (e.crees) */
  async function rappeler(E, fn, arg, action) {
    if (E.envoi || E.occupe) return;
    E.envoi = true; majEnvoi(E);
    try {
      var r = await E.opts[fn](arg);
      if (r === false) return;
      E.envoi = false;
      fermer(E, { action: action });
    } catch (e) {
      var k = Number(e && e.crees) || 0;
      if (action === "chapitres" && k > 0) {
        E.creesTotal = (E.creesTotal || 0) + k;
        E.aCreer = arg.slice(k);
        dire(E, T("scan.decoupage.partiel", { k: E.creesTotal, n: E.totalChap, msg: (e && e.message) || "?" }), true);
        if (E.btnCreer) E.btnCreer.textContent = T("scan.decoupage.restants");
      } else {
        dire(E, T("scan.envoi.echec", { msg: (e && e.message) || "?" }), true);
      }
    } finally {
      E.envoi = false;
      if (!E.ferme) majEnvoi(E);
    }
  }

  async function envoyer(E, quoi) {
    if (E.envoi || E.occupe) return;
    var texte = E.champ.value;
    if (!texte.trim()) { dire(E, T("scan.envoi.vide"), true); return; }
    if (quoi === "inserer") return rappeler(E, "inserer", texte, "inserer");
    if (quoi === "manuscrit") {
      var n = Array.from(texte.trim()).length;
      if (n < MIN_MANUSCRIT) { dire(E, T("scan.manuscrit.trop_court", { n: n }), true); return; }
      return rappeler(E, "importerManuscrit", texte, "manuscrit");
    }
    // créer les chapitres : le découpage proposé d'abord
    var jeton = ++E.jeton;
    E.envoi = true; majEnvoi(E);
    dire(E, T("scan.decoupage.en_cours"));
    var R, j;
    try {
      R = await fetch("/api/scan/decoupage", { method: "POST", headers: { "Content-Type": "application/json" },
                                                body: JSON.stringify({ texte: texte }) });
      j = await lireJson(R);
    } catch (e) {
      if (jeton === E.jeton) dire(E, T("scan.decoupage.echec", { msg: (e && e.message) || "?" }), true);
      return;
    } finally {
      E.envoi = false;
      if (!E.ferme) majEnvoi(E);
    }
    if (jeton !== E.jeton) return;
    if (!R.ok) { dire(E, T("scan.decoupage.echec", { msg: detail(j, R.status) }), true); return; }
    var chap = (j && j.chapitres) || [];
    if (!chap.length) { dire(E, T("scan.decoupage.aucun"), true); return; }
    var liste = chap.map(function (c, i) {        // I2 : le texte EXACT du découpage serveur, tel quel
      return { titre: String(c.titre || "").trim() || T("scan.decoupage.sans_titre", { n: i + 1 }),
               texte: String(c.texte || ""), caracteres: Number(c.caracteres) || 0 };
    });
    dire(E, "");
    montrerDecoupage(E, liste);
  }

  function montrerDecoupage(E, liste) {
    var c = E.coupe;
    c.textContent = "";
    E.aCreer = liste.map(function (x) { return { titre: x.titre, texte: x.texte }; });
    E.totalChap = liste.length;
    E.creesTotal = 0;
    c.appendChild(el("div", { style: "font-weight:600" }, T("scan.decoupage.titre", { n: liste.length })));
    var serie = String(E.opts.serie || "").trim();
    c.appendChild(el("div", { style: S.note, "data-dz-scan": "serie" },
                     serie ? T("scan.decoupage.serie", { serie: serie }) : T("scan.decoupage.sans_serie")));
    var ol = el("ol", { style: "margin:0;padding-left:20px", "data-dz-scan": "chapitres-proposes" });
    liste.forEach(function (x) {
      ol.appendChild(el("li", { "data-dz-scan": "chapitre-propose" }, T("scan.decoupage.ligne", { titre: x.titre, n: x.caracteres || Array.from(x.texte).length })));
    });
    c.appendChild(ol);
    var l = el("div", { style: S.ligne });
    var ok = E.btnCreer = bouton("creer-chapitres", T("scan.decoupage.creer"), S.ok);
    var retour = bouton("retour", T("scan.decoupage.retour"));
    ok.addEventListener("click", function () { rappeler(E, "creerChapitres", E.aCreer, "chapitres"); });
    retour.addEventListener("click", function () { if (E.envoi) return; montrer(c, false); montrer(E.resultat, true); });
    l.appendChild(ok); l.appendChild(retour);
    c.appendChild(l);
    montrer(E.resultat, false);
    montrer(c, true);
  }

  window.__dzScan = {
    ouvrir: ouvrir,
    fermer: function () { if (courant) fermer(courant, null); },
    versU16: versU16,
    MAX_FICHIERS: MAX_FICHIERS,
    DELAI_MS: DELAI_MS,
    DELAI_CLAUDE_MS: DELAI_CLAUDE_MS,
    MARGE_CLAUDE_MS: MARGE_CLAUDE_MS
  };
})();
