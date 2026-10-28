// dz-capture.js — t315 (28/10/2026, lot D1 « capture façon streaming »), l'ENREGISTREUR de l'app (plan
// docs/superpowers/plans/2026-10-28-t315-capture.md, spec 2026-10-25-boite-a-outils-design.md §8.1-8.3).
// SOURCE : frontend/shared/dz-capture.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-capture.js, chargée par
// frontend/dist/index.html (`<script type="module">`, après dz-whatsapp-espace.js). Aucune dépendance au runtime React.
// Banc : backend/tests/test_capture_ecran.py.
//
// - Bouton « Enregistrer » [data-dz-capture-ouvrir] dans la barre du haut de la coque (remis en place si React la
//   remonte) ; il ouvre la boîte de départ (charte de dialogue.js : angles vifs, en-tête mono en capitales, Tab piégé,
//   Échap) : cadre (l'app seule par Element Capture | tout l'onglet), voix, son de l'app, caméra (la case EST l'accord),
//   forme de l'encart, piste des clics, halo, zoom en direct.
// - « Démarrer » : getDisplayMedia({preferCurrentTab}) EN PREMIER (geste de l'utilisateur), refus si la surface n'est
//   pas un onglet ou n'est pas CET onglet (Capture Handle) ; Element Capture sur #root (repli : tout l'onglet, dit) ;
//   micro et caméra ensuite ; session POST /api/capture/sessions ; scène (dz-capture-scene.js) ; une MediaRecorder par
//   piste (scene, ecran, camera, voix), morceaux d'une seconde envoyés DANS L'ORDRE.
// - Pendant : <html data-dz-capture> + CSS_MASQUE (aussi dans les cadres de même origine) ; caviardage peint par la
//   scène à chaque image ; pastille [data-dz-capture-pastille] (REC, minuteur, micro, témoin caméra, « Arrêter ») ;
//   encart caméra [data-dz-capture-encart] déplaçable et redimensionnable ; piste des clics sur pointerdown (jamais
//   le clavier).
// - Fin (« Arrêter », arrêt du partage par le navigateur) : pistes vidées, caméra et micro coupés, POST …/terminer, la
//   scène entre dans la Bibliothèque.
// Drapeau de PREUVE (localStorage dz_capture_preuve = "1", jamais posé par le code) : écran, caméra et voix factices.
// API (contrat t316-t319) : window.__dzCapture = {ouvrir(), demarrer(options), arreter(), session(), disponible()}.
import { SELECTEURS_SECRETS, ATTR_CAPTURE, CSS_MASQUE, estSecret, cibleClic, normaliser, versScene, bornerEncart,
  formeLue, choisirMime, verifierSurface, creerPiste, duree } from "./dz-capture-logique.js";
import { creerScene, calqueEcran, calqueClics, calqueEncart } from "./dz-capture-scene.js";

if (!window.__dzCapture) {
  const T = (cle, vars) => (typeof window.dzT === "function" ? window.dzT(cle, vars) : cle);
  const glyphe = (cle, taille) => {
    const s = document.createElement("span");
    s.className = "dzCapGl";
    s.innerHTML = typeof window.dzIcone === "function" ? window.dzIcone(cle, { taille: taille || 14 }) : "";
    return s;
  };
  const lire = (k) => { try { return window.localStorage.getItem(k); } catch (e) { return null; } };
  const ecrire = (k, v) => { try { window.localStorage.setItem(k, v); } catch (e) { /* stockage indisponible */ } };
  const vue = () => lire("dz_view") || "quick";
  const preuve = () => lire("dz_capture_preuve") === "1";
  const el = (tag, attrs, enfants) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "on") for (const [e, f] of Object.entries(v)) n.addEventListener(e, f);
      else if (k === "texte") n.textContent = v;
      else if (k === "style") n.style.cssText = v;
      else if (v !== false && v != null) n.setAttribute(k, v === true ? "" : v);
    }
    for (const c of enfants || []) if (c) n.appendChild(c);
    return n;
  };
  const S = {
    voile: "position:fixed;inset:0;z-index:2147483004;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center",
    boite: "width:480px;max-width:94vw;max-height:88vh;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    corps: "padding:12px 14px;overflow-y:auto;display:flex;flex-direction:column;gap:10px;color:var(--txt-base,var(--ink,#cfd6e2))",
    groupe: "display:flex;flex-direction:column;gap:5px",
    titreG: "font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    ligne: "display:flex;align-items:center;gap:8px;cursor:pointer",
    note: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    erreur: "font-size:12px;color:var(--red,#e5484d)",
    champ: "font:inherit;font-size:12px;padding:3px 6px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));color:var(--txt-hi,var(--ink-strong,#e6e9ee));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138))",
    pied: "display:flex;gap:8px;justify-content:flex-end;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
    bouton: "font:inherit;font-size:12.5px;padding:5px 12px;border-radius:0;cursor:pointer;background:var(--srf-raised,var(--bg-panel-3,#1b2028));color:var(--txt-hi,var(--ink-strong,#e6e9ee));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138))",
    principal: "font:inherit;font-size:12.5px;padding:5px 12px;border-radius:0;cursor:pointer;background:var(--brand,#f0b429);color:#111;border:1px solid var(--brand,#f0b429);font-weight:600",
    pastille: "position:fixed;top:8px;left:50%;transform:translateX(-50%);z-index:2147483003;display:flex;align-items:center;gap:10px;padding:5px 8px 5px 12px;background:rgba(17,20,25,.94);color:#e6e9ee;border:1px solid #e5484d;font:12px/1.3 system-ui,sans-serif;box-shadow:0 6px 24px rgba(0,0,0,.45)",
    point: "width:10px;height:10px;border-radius:50%;background:#e5484d;flex:none",
    jauge: "display:inline-block;width:36px;height:6px;background:#2a3138;position:relative;overflow:hidden",
    temoin: "display:inline-flex;align-items:center;gap:4px;color:#e5484d;font-weight:600",
    encart: "position:fixed;z-index:2147483002;overflow:hidden;background:#000;border:2px solid var(--brand,#f0b429);cursor:move;touch-action:none;box-shadow:0 8px 28px rgba(0,0,0,.5)",
    poignee: "position:absolute;right:0;bottom:0;width:16px;height:16px;cursor:nwse-resize;background:linear-gradient(135deg,transparent 50%,var(--brand,#f0b429) 50%)",
  };
  const CSS = ".dzCapGl{display:inline-flex;align-items:center;vertical-align:middle;margin-right:5px}.dzCapGl svg{display:block}"
    + "[data-dz-capture-ouvrir]{display:inline-flex;align-items:center;gap:6px;flex-shrink:0;align-self:center;margin:0 4px;padding:4px 10px;font-size:12px;border-radius:0;cursor:pointer;background:transparent;color:inherit;border:1px solid var(--stroke,#2a3138)}"
    + "[data-dz-capture-ouvrir][data-actif]{border-color:#e5484d;color:#e5484d}"
    + "[data-dz-capture-ouvrir]:disabled{opacity:.45;cursor:not-allowed}";
  const style = el("style", { "data-dz-capture-ui": true, texte: CSS });
  document.head.appendChild(style);

  let session = null;               // la capture en cours (une seule à la fois)

  // ── disponibilité ──
  const md = navigator.mediaDevices;
  const disponible = () => preuve() || !!(md && typeof md.getDisplayMedia === "function"
    && typeof window.MediaRecorder === "function" && typeof HTMLCanvasElement.prototype.captureStream === "function");
  const avecElementCapture = () => typeof window.RestrictionTarget === "function"
    && typeof window.RestrictionTarget.fromElement === "function";

  // ── le bouton de la barre du haut ──
  const bouton = el("button", { type: "button", "data-dz-capture-ouvrir": true, "data-dz-capture-ui": true,
    title: T("capture.barre.titre"), on: { click: () => (session ? arreter() : ouvrir()) } });
  function peindreBouton() {
    const actif = !!session;
    bouton.replaceChildren(glyphe(actif ? "dz-media-arret" : "dz-media-rec"),
      document.createTextNode(T(actif ? "capture.barre.arreter" : "capture.barre.bouton")));
    bouton.toggleAttribute("data-actif", actif);
    bouton.disabled = !actif && !disponible();
    bouton.title = bouton.disabled ? T("capture.barre.indisponible") : T(actif ? "capture.barre.arreter" : "capture.barre.titre");
  }
  const barre = () => document.querySelector("#root header");
  function placerBouton() {
    const h = barre();
    if (!h) { if (bouton.isConnected) bouton.remove(); return; }
    if (bouton.parentNode === h) return;
    const agent = h.querySelector(".dzAgentBtn");
    const dernier = h.lastElementChild;
    h.insertBefore(bouton, agent || (dernier && dernier.tagName === "BUTTON" ? dernier : null));
  }
  let guet = 0;
  new MutationObserver(() => {
    if (guet) return;
    guet = setTimeout(() => { guet = 0; if (!bouton.isConnected || bouton.parentNode !== barre()) placerBouton(); }, 30);
  }).observe(document.getElementById("root") || document.body, { childList: true, subtree: true });
  peindreBouton();
  placerBouton();

  // ── la boîte de départ ──
  let boite = null;
  function fermerBoite() { if (boite) { boite.remove(); boite = null; } }
  function pieger(b, fermer) {
    b.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") { ev.preventDefault(); fermer(); return; }
      if (ev.key !== "Tab") return;
      const f = Array.from(b.querySelectorAll("button, input, select")).filter((x) => !x.disabled);
      if (!f.length) return;
      const i = f.indexOf(document.activeElement);
      if (ev.shiftKey && i <= 0) { ev.preventDefault(); f[f.length - 1].focus(); }
      else if (!ev.shiftKey && i === f.length - 1) { ev.preventDefault(); f[0].focus(); }
    });
  }
  // une case et son libellé (la case porte aussi le libellé en aria-label : lu par le catalogue de « Demander »)
  function caseA(c, coche) {
    c.checked = !!coche;
    return { c, ligne: el("label", { style: S.ligne }, [c, el("span", { texte: c.getAttribute("aria-label") })]) };
  }

  function ouvrir() {
    if (session || boite || !disponible()) return;
    const memo = (() => { try { return JSON.parse(lire("dz_capture_options") || "{}") || {}; } catch (e) { return {}; } })();
    const radio = (v) => {
      const r = el("input", { type: "radio", name: "dzCapCadre", value: v, "data-dz-capture-option": "mode-" + v,
        "aria-label": T(v === "app" ? "capture.cadre.app" : "capture.cadre.onglet") });
      r.checked = (memo.mode === "onglet" ? "onglet" : "app") === v;
      return el("label", { style: S.ligne }, [r, el("span", { texte: r.getAttribute("aria-label") })]);
    };
    const voix = caseA(el("input", { type: "checkbox", "data-dz-capture-option": "voix", "aria-label": T("capture.son.voix") }),
      memo.voix !== false);
    const son = caseA(el("input", { type: "checkbox", "data-dz-capture-option": "son_onglet", "aria-label": T("capture.son.onglet") }),
      memo.son_onglet === true);
    // l'accord se redonne à chaque capture : jamais coché d'office
    const cam = caseA(el("input", { type: "checkbox", "data-dz-capture-option": "camera", "aria-label": T("capture.camera.accord") }),
      false);
    const forme = el("select", { style: S.champ, "data-dz-capture-option": "forme", "aria-label": T("capture.camera.forme") },
      ["cercle", "carre", "vif"].map((f) => { const o = el("option", { value: f, texte: T("capture.forme." + f) }); return o; }));
    forme.value = formeLue(memo.forme);
    const clics = caseA(el("input", { type: "checkbox", "data-dz-capture-option": "clics", "aria-label": T("capture.clics.piste") }),
      memo.clics !== false);
    const halo = caseA(el("input", { type: "checkbox", "data-dz-capture-option": "halo", "aria-label": T("capture.clics.halo") }),
      memo.halo !== false);
    const zoom = caseA(el("input", { type: "checkbox", "data-dz-capture-option": "zoom", "aria-label": T("capture.clics.zoom") }),
      memo.zoom === true);
    const erreur = el("div", { style: S.erreur, role: "alert", "data-dz-capture-erreur": true });
    const btnDemarrer = el("button", { type: "button", style: S.principal, "data-dz-capture-demarrer": true,
      texte: T("capture.boite.demarrer") });
    btnDemarrer.insertBefore(glyphe("dz-media-rec"), btnDemarrer.firstChild);
    const btnAnnuler = el("button", { type: "button", style: S.bouton, texte: T("capture.boite.annuler"), on: { click: fermerBoite } });
    const lireOptions = () => ({
      mode: (boite.querySelector('input[name="dzCapCadre"]:checked') || {}).value === "onglet" ? "onglet" : "app",
      voix: voix.c.checked, son_onglet: son.c.checked, camera: cam.c.checked, forme: forme.value,
      clics: clics.c.checked, halo: halo.c.checked, zoom: zoom.c.checked,
    });
    btnDemarrer.addEventListener("click", async () => {
      const o = lireOptions();
      ecrire("dz_capture_options", JSON.stringify(Object.assign({}, o, { camera: false })));
      btnDemarrer.disabled = true; btnAnnuler.disabled = true; erreur.textContent = "";
      const r = await demarrer(o);
      if (r.ok) fermerBoite();
      else { erreur.textContent = r.message; btnDemarrer.disabled = false; btnAnnuler.disabled = false; }
    });
    boite = el("div", { style: S.voile, "data-dz-capture-ui": true, "data-dz-capture-boite": true }, [
      el("div", { style: S.boite, role: "dialog", "aria-modal": "true", "aria-label": T("capture.boite.titre") }, [
        el("div", { style: S.tete, texte: T("capture.boite.titre") }),
        el("div", { style: S.corps }, [
          el("div", { style: S.groupe }, [el("div", { style: S.titreG, texte: T("capture.cadre.titre") }),
            radio("app"), radio("onglet"),
            el("div", { style: S.note, texte: T(avecElementCapture() ? "capture.cadre.note_app" : "capture.cadre.sans_ec") })]),
          el("div", { style: S.groupe }, [el("div", { style: S.titreG, texte: T("capture.son.titre") }), voix.ligne, son.ligne]),
          el("div", { style: S.groupe }, [el("div", { style: S.titreG, texte: T("capture.camera.titre") }), cam.ligne,
            el("label", { style: S.ligne }, [el("span", { texte: T("capture.camera.forme") }), forme])]),
          el("div", { style: S.groupe }, [el("div", { style: S.titreG, texte: T("capture.clics.titre") }), clics.ligne,
            halo.ligne, zoom.ligne]),
          el("div", { style: S.note, texte: T("capture.boite.securite") }),
          preuve() ? el("div", { style: S.note, texte: T("capture.preuve.note") }) : null,
          erreur,
        ]),
        el("div", { style: S.pied }, [btnAnnuler, btnDemarrer]),
      ]),
    ]);
    boite.addEventListener("pointerdown", (ev) => { if (ev.target === boite) fermerBoite(); });
    pieger(boite, () => { if (!btnAnnuler.disabled) fermerBoite(); });
    document.body.appendChild(boite);
    btnDemarrer.focus();
  }

  // ── flux factices (drapeau de preuve) ──
  function fauxEcran() {
    const c = document.createElement("canvas");
    c.width = Math.max(320, window.innerWidth); c.height = Math.max(240, window.innerHeight);
    const g = c.getContext("2d");
    const peindre = () => {
      g.fillStyle = "#0b0f14"; g.fillRect(0, 0, c.width, c.height);
      const tout = Array.from(document.querySelectorAll("#root *")).slice(0, 2500);
      for (const x of tout) {
        const r = x.getBoundingClientRect();
        if (!(r.width > 0 && r.height > 0) || r.bottom < 0 || r.top > c.height) continue;
        const cs = getComputedStyle(x);
        if (cs.visibility === "hidden" || cs.display === "none") continue;
        const secret = estSecret(x);
        if (cs.backgroundColor && !/rgba\(0, 0, 0, 0\)|transparent/.test(cs.backgroundColor)) {
          g.fillStyle = cs.backgroundColor; g.fillRect(r.x, r.y, r.width, r.height);
        }
        if (parseFloat(cs.borderTopWidth) > 0) { g.strokeStyle = cs.borderTopColor; g.strokeRect(r.x + .5, r.y + .5, r.width - 1, r.height - 1); }
        if (secret) { g.fillStyle = "rgba(120,130,140,.35)"; g.fillRect(r.x, r.y, r.width, r.height); continue; }   // le flou de la page
        for (const n of x.childNodes) {
          if (n.nodeType !== 3 || !n.textContent.trim()) continue;
          g.fillStyle = cs.color; g.font = cs.fontWeight + " " + cs.fontSize + " " + cs.fontFamily; g.textBaseline = "top";
          g.fillText(n.textContent.trim().slice(0, 80), r.x + parseFloat(cs.paddingLeft || 0), r.y + parseFloat(cs.paddingTop || 0));
        }
      }
    };
    peindre();
    const id = setInterval(peindre, 200);
    const flux = c.captureStream(10);
    flux.getVideoTracks()[0].addEventListener("ended", () => clearInterval(id));
    flux._dzArret = () => clearInterval(id);
    return flux;
  }
  function fausseCamera() {
    const c = document.createElement("canvas"); c.width = 640; c.height = 480;
    const g = c.getContext("2d");
    const id = setInterval(() => {
      const t = performance.now() / 1000;
      const d = g.createLinearGradient(0, 0, 640, 480);
      d.addColorStop(0, "#1d3a5f"); d.addColorStop(1, "#5f1d3a");
      g.fillStyle = d; g.fillRect(0, 0, 640, 480);
      g.fillStyle = "#f0b429"; g.beginPath(); g.arc(320 + Math.sin(t) * 40, 210, 90, 0, Math.PI * 2); g.fill();
      g.fillStyle = "#fff"; g.font = "bold 30px system-ui"; g.textAlign = "center"; g.fillText("CAMERA", 320, 400);
    }, 66);
    const flux = c.captureStream(15);
    flux._dzArret = () => clearInterval(id);
    return flux;
  }
  function fausseVoix(ac) {
    const o = ac.createOscillator(), lfo = ac.createOscillator(), g = ac.createGain(), gl = ac.createGain();
    o.frequency.value = 220; lfo.frequency.value = 2; gl.gain.value = 0.15; g.gain.value = 0.15;
    lfo.connect(gl); gl.connect(g.gain); o.connect(g);
    const dest = ac.createMediaStreamDestination(); g.connect(dest);
    o.start(); lfo.start();
    dest.stream._dzArret = () => { try { o.stop(); lfo.stop(); } catch (e) { /* déjà arrêté */ } };
    return dest.stream;
  }

  // ── la session en cours ──
  const piste = creerPiste(() => performance.now());

  function cadreFilme() {
    if (session && session.elementCapture) {
      const r = document.getElementById("root").getBoundingClientRect();
      return { x: r.x, y: r.y, l: r.width, h: r.height };
    }
    return { x: 0, y: 0, l: window.innerWidth, h: window.innerHeight };
  }
  // les documents de même origine : la page et ses cadres (labs), avec le décalage de chaque cadre
  function documents() {
    const out = [{ doc: document, dx: 0, dy: 0 }];
    for (const f of document.querySelectorAll("iframe")) {
      try {
        const d = f.contentDocument;
        if (!d) continue;
        const r = f.getBoundingClientRect();
        out.push({ doc: d, dx: r.x + (f.clientLeft || 0), dy: r.y + (f.clientTop || 0), cadre: f });
      } catch (e) { /* autre origine : ni masque ni clics, et rien n'y est lu */ }
    }
    return out;
  }
  function mesurerSecrets() {
    if (!session) return [];
    const cadre = cadreFilme(), W = session.scene.largeur, H = session.scene.hauteur, out = [];
    for (const { doc, dx, dy } of documents()) {
      let noeuds = [];
      try { noeuds = doc.querySelectorAll(SELECTEURS_SECRETS); } catch (e) { noeuds = []; }
      for (const x of noeuds) {
        const r = x.getBoundingClientRect();
        if (!(r.width > 0 && r.height > 0)) continue;
        const v = versScene({ x: r.x + dx, y: r.y + dy, l: r.width, h: r.height }, cadre, W, H);
        if (v) { v.ecran = x.getAttribute("data-dz-secret") === "ecran"; out.push(v); }
      }
    }
    return out;
  }
  function poserMasque(doc) {
    try {
      doc.documentElement.setAttribute(ATTR_CAPTURE, "1");
      if (!doc.querySelector("style[data-dz-capture-masque]")) {
        const st = doc.createElement("style");
        st.setAttribute("data-dz-capture-masque", "");
        st.textContent = CSS_MASQUE;
        (doc.head || doc.documentElement).appendChild(st);
      }
    } catch (e) { /* cadre parti */ }
  }
  function oterMasque(doc) {
    try {
      doc.documentElement.removeAttribute(ATTR_CAPTURE);
      doc.querySelectorAll("style[data-dz-capture-masque]").forEach((s) => s.remove());
    } catch (e) { /* cadre parti */ }
  }
  // un appui (souris, doigt, stylet) : jamais une touche ; nos propres contrôles ne comptent pas
  function surAppui(ev, dx, dy) {
    if (!session) return;
    const cible = ev.target;
    if (cible && cible.closest && cible.closest("[data-dz-capture-ui]")) return;
    const n = normaliser(ev.clientX + dx, ev.clientY + dy, cadreFilme());
    const secret = estSecret(cible);
    const W = session.scene.largeur, H = session.scene.hauteur, maintenant = performance.now();
    if (session.options.halo) session.scene.etat.clics.push({ x: n.x * W, y: n.y * H, debut: maintenant });
    if (session.options.zoom) session.scene.etat.zoom = { cx: n.x * W, cy: n.y * H, debut: maintenant };
    if (!session.options.clics) return;
    const e = piste.clic({ x: n.x, y: n.y, bouton: ev.button, ecran: vue(), secret, cible: cibleClic(cible) });
    window.dispatchEvent(new CustomEvent("dz-capture:clic", { detail: { evt: e } }));
  }
  const ecouteurs = new Map();               // document -> fonction d'écoute
  function ecouter() {
    for (const { doc, dx, dy, cadre } of documents()) {
      if (ecouteurs.has(doc)) continue;
      const f = (ev) => {
        let ox = dx, oy = dy;
        if (cadre) { const r = cadre.getBoundingClientRect(); ox = r.x + (cadre.clientLeft || 0); oy = r.y + (cadre.clientTop || 0); }
        surAppui(ev, ox, oy);
      };
      try { doc.addEventListener("pointerdown", f, true); ecouteurs.set(doc, f); poserMasque(doc); } catch (e) { /* cadre parti */ }
    }
  }
  function nePlusEcouter() {
    for (const [doc, f] of ecouteurs) { try { doc.removeEventListener("pointerdown", f, true); } catch (e) { /* parti */ } oterMasque(doc); }
    ecouteurs.clear();
  }

  // un envoi DANS L'ORDRE par piste ; un PUT raté est retenté deux fois (0,5 s puis 1,5 s), puis la file s'arrête :
  // revue finale t315 (I2) : seule la piste « scene » est vitale, une piste brute perdue ne perd pas l'enregistrement
  const attendreMs = (ms) => new Promise((ok) => setTimeout(ok, ms));
  function fileEnvoi(id, nom, mime, surEchec) {
    let n = 0, chaine = Promise.resolve(), echec = null;
    async function envoyer(k, blob) {
      let derniere = null;
      for (const pause of [0, 500, 1500]) {
        if (pause) await attendreMs(pause);
        try {
          const r = await fetch(`/api/capture/sessions/${id}/pistes/${nom}/${k}`, { method: "PUT",
            headers: { "Content-Type": mime }, body: blob });
          if (r.ok) return;
          const j = await r.json().catch(() => ({}));
          derniere = new Error(typeof j.detail === "string" ? j.detail : String(r.status));
          if (r.status !== 408 && r.status !== 429 && r.status < 500) break;       // refus net : inutile de retenter
        } catch (e) { derniere = e; }
      }
      throw derniere || new Error("—");
    }
    return {
      pousser(blob) {
        if (!blob || !blob.size) return;
        const k = n++;
        chaine = chaine.then(() => (echec ? null : envoyer(k, blob)))
          .catch((e) => { if (!echec) { echec = e; if (surEchec) surEchec(nom, e); } });
      },
      fin: () => chaine,
      echec: () => echec,
    };
  }
  function enregistreur(id, nom, flux, genre) {
    const mime = choisirMime((m) => window.MediaRecorder.isTypeSupported(m), genre);
    const rec = new window.MediaRecorder(flux, mime ? { mimeType: mime } : undefined);
    const file = fileEnvoi(id, nom, (rec.mimeType || mime || (genre === "audio" ? "audio/webm" : "video/webm")),
      nom === "scene" ? null : pistePerdue);
    rec.addEventListener("dataavailable", (ev) => file.pousser(ev.data));
    const arrete = new Promise((ok) => rec.addEventListener("stop", ok, { once: true }));
    rec.start(1000);
    return { nom, rec, file, arrete };
  }

  // ── la pastille (témoin) et l'encart caméra ──
  function pastille() {
    const temps = el("span", { texte: "00:00", "data-dz-capture-temps": true, style: "font-variant-numeric:tabular-nums" });
    const niveau = el("span", { style: "position:absolute;left:0;top:0;bottom:0;width:0;background:#3fb950" });
    const enfants = [el("span", { style: S.point }), el("strong", { texte: T("capture.pastille.rec") }), temps];
    if (session.flux.voix) enfants.push(el("span", { style: S.temoin + ";color:#e6e9ee", title: T("capture.pastille.micro"),
      "aria-label": T("capture.pastille.micro"), "data-dz-capture-micro": true }, [glyphe("dz-media-dicter"),
      el("span", { style: S.jauge }, [niveau])]));
    if (session.flux.camera) enfants.push(el("span", { style: S.temoin, "data-dz-capture-temoin-camera": true },
      [glyphe("dz-media-avatar"), el("span", { texte: T("capture.pastille.camera") })]));
    if (session.preuve) enfants.push(el("em", { texte: T("capture.pastille.preuve"), style: "color:#f0b429" }));
    for (const n of session.notes) enfants.push(el("span", { texte: n, style: "font-size:11px;color:#9aa4ae" }));
    const arret = el("button", { type: "button", style: S.bouton + ";padding:3px 10px;border-color:#e5484d", "data-dz-capture-arreter": true,
      texte: T("capture.pastille.arreter"), on: { click: () => arreter() } });
    arret.insertBefore(glyphe("dz-media-arret"), arret.firstChild);
    enfants.push(arret);
    const p = el("div", { style: S.pastille, role: "status", "aria-live": "polite", "data-dz-capture-ui": true,
      "data-dz-capture-pastille": true }, enfants);
    document.body.appendChild(p);
    return { p, temps, niveau, arret };
  }
  // l'encart caméra à l'écran (hors #root : en mode « app » il n'est pas filmé, la scène dessine la caméra au même
  // endroit) ; sa place, normalisée au cadre filmé, pilote etat.encart. Un cercle garde un encart carré en pixels.
  function encartDom(flux) {
    const memo = (() => { try { return JSON.parse(lire("dz_capture_encart") || "null"); } catch (e) { return null; } })();
    const forme = session.scene.etat.forme;
    const ajuster = (x) => {
      const c = cadreFilme(), b = bornerEncart(x);
      return forme === "cercle" ? bornerEncart({ x: b.x, y: b.y, l: b.l, h: b.l * c.l / (c.h || 1) }) : b;
    };
    let e = ajuster(memo || { x: 0.76, y: 0.62, l: 0.2, h: 0.32 });
    const v = el("video", { style: "width:100%;height:100%;object-fit:cover;display:block;pointer-events:none" });
    v.muted = true; v.playsInline = true; v.srcObject = flux; v.play().catch(() => {});
    const poignee = el("div", { style: S.poignee });
    const boiteE = el("div", { style: S.encart, "data-dz-capture-ui": true, "data-dz-capture-encart": true,
      title: T("capture.encart.titre"), "aria-label": T("capture.encart.titre") }, [v, poignee]);
    const placer = () => {
      const c = cadreFilme();
      e = ajuster(e);
      Object.assign(boiteE.style, { left: c.x + e.x * c.l + "px", top: c.y + e.y * c.h + "px", width: e.l * c.l + "px",
        height: e.h * c.h + "px", borderRadius: forme === "cercle" ? "50%" : forme === "carre" ? "12%" : "0" });
      if (session) session.scene.etat.encart = Object.assign({}, session.scene.etat.encart, e);   // champs d'un skin gardés
    };
    let appui = null;
    boiteE.addEventListener("pointerdown", (ev) => {
      ev.preventDefault();
      try { boiteE.setPointerCapture(ev.pointerId); } catch (x) { /* pointeur déjà relâché */ }
      appui = { x: ev.clientX, y: ev.clientY, e: Object.assign({}, e), taille: ev.target === poignee };
    });
    boiteE.addEventListener("pointermove", (ev) => {
      if (!appui) return;
      const c = cadreFilme(), dx = (ev.clientX - appui.x) / c.l, dy = (ev.clientY - appui.y) / c.h;
      e = appui.taille ? { x: appui.e.x, y: appui.e.y, l: appui.e.l + dx, h: appui.e.h + dy }
        : { x: appui.e.x + dx, y: appui.e.y + dy, l: appui.e.l, h: appui.e.h };
      placer();
    });
    const lacher = () => { if (appui) { appui = null; ecrire("dz_capture_encart", JSON.stringify(e)); } };
    boiteE.addEventListener("pointerup", lacher);
    boiteE.addEventListener("pointercancel", lacher);
    window.addEventListener("resize", placer);
    document.body.appendChild(boiteE);
    placer();
    return { boite: boiteE, placer, retirer: () => { window.removeEventListener("resize", placer); boiteE.remove(); } };
  }

  function video(flux) {
    const v = document.createElement("video");
    v.muted = true; v.playsInline = true; v.srcObject = flux;
    v.play().catch(() => {});
    return v;
  }
  const couper = (f) => { if (!f) return; f.getTracks().forEach((t) => t.stop()); if (f._dzArret) f._dzArret(); };

  // ── démarrer : rend {ok, message?} ; rien ne reste allumé après un échec, à quelque étape que ce soit ──
  // revue finale t315 : un seul démarrage à la fois (I4) ; un onglet sans poignée alors que la page en a posé une est un
  // AUTRE onglet, et un onglet qu'on n'a pu vérifier ni restreindre est refusé (C1) ; toute panne après l'ouverture des
  // pistes coupe tout, abandonne la session serveur et libère l'enregistreur (C2).
  let demarrage = false;
  async function demarrer(options) {
    if (session || demarrage) return { ok: false, message: "" };
    demarrage = true;
    try { return await demarrer0(options); }
    finally { demarrage = false; }
  }
  async function demarrer0(options) {
    const o = Object.assign({ mode: "app", voix: true, son_onglet: false, camera: false, forme: "cercle", clics: true,
      halo: true, zoom: false }, options || {});
    o.forme = formeLue(o.forme);
    const p = preuve(), notes = [], flux = { ecran: null, voix: null, camera: null, onglet: null };
    const jeton = "dzcap-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    const root = document.getElementById("root");
    let ac = null, poignee = false;
    const libererRoot = () => { if (root) { root.style.isolation = ""; root.style.transformStyle = ""; } };
    const toutCouper = () => { Object.values(flux).forEach(couper); if (ac) ac.close().catch(() => {}); libererRoot(); };
    // 1. l'écran, EN PREMIER (le geste de l'utilisateur est encore frais)
    try {
      if (p) flux.ecran = fauxEcran();
      else {
        try { md.setCaptureHandleConfig({ handle: jeton, exposeOrigin: false, permittedOrigins: [location.origin] }); poignee = true; }
        catch (e) { /* Capture Handle absent : seul Element Capture pourra prouver l'auto-capture */ }
        flux.ecran = await md.getDisplayMedia({ video: { frameRate: 30 }, audio: !!o.son_onglet, preferCurrentTab: true,
          selfBrowserSurface: "include", surfaceSwitching: "exclude", monitorTypeSurfaces: "exclude", systemAudio: "exclude" });
      }
    } catch (e) {
      return { ok: false, message: T("capture.erreur.refus") };
    }
    const piste0 = flux.ecran.getVideoTracks()[0];
    let elementCapture = false;
    if (!p) {
      const lisible = poignee && typeof piste0.getCaptureHandle === "function";
      const verdict = verifierSurface(piste0.getSettings ? piste0.getSettings() : null,
        lisible ? piste0.getCaptureHandle() : null, jeton, lisible);
      if (verdict === "pas_onglet" || verdict === "autre_onglet") {
        toutCouper();
        return { ok: false, message: T(verdict === "pas_onglet" ? "capture.erreur.surface" : "capture.erreur.autre_onglet") };
      }
      // 2. Element Capture : l'app seule (#root) ; repli = tout l'onglet, dit dans la pastille. Element Capture ne marche
      // que sur l'onglet lui-même : quand l'onglet n'a pas pu être vérifié autrement, on l'essaie toujours et son échec
      // est un REFUS (jamais un autre onglet filmé en silence).
      if ((o.mode === "app" || verdict === "inconnu") && avecElementCapture() && typeof piste0.restrictTo === "function" && root) {
        try {
          root.style.isolation = "isolate";
          root.style.transformStyle = "flat";
          await piste0.restrictTo(await window.RestrictionTarget.fromElement(root));
          elementCapture = true;
        } catch (e) { libererRoot(); }
      }
      if (verdict === "inconnu" && !elementCapture) {
        toutCouper();
        return { ok: false, message: T("capture.erreur.verif") };
      }
      if (o.mode === "app" && !elementCapture) notes.push(T("capture.note.sans_ec"));
    }
    let id = null;
    try {
      if (flux.ecran.getAudioTracks().length) flux.onglet = new MediaStream(flux.ecran.getAudioTracks());
      // 3. la voix, puis la caméra (accord donné par la case de la boîte)
      try { ac = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { ac = null; }
      if (o.voix) {
        try {
          flux.voix = p && ac ? fausseVoix(ac) : await md.getUserMedia({ audio: { noiseSuppression: true, echoCancellation: true,
            autoGainControl: true } });
        } catch (e) { notes.push(T("capture.note.sans_voix")); }
      }
      if (o.camera) {
        try { flux.camera = p ? fausseCamera() : await md.getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 } } }); }
        catch (e) { notes.push(T("capture.note.sans_camera")); }
      }
      if (piste0.readyState === "ended") throw new Error(T("capture.erreur.refus"));   // partage arrêté pendant l'attente
      // 4. la session côté serveur
      const r = await fetch("/api/capture/sessions", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ options: Object.assign({}, o, { camera: !!flux.camera, voix: !!flux.voix,
          element_capture: elementCapture, preuve: p, mode: elementCapture || p ? o.mode : "onglet" }) }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok || !j.id) throw new Error(typeof j.detail === "string" ? j.detail : String(r.status));
      id = j.id;
      return await lancer(id, o, p, flux, notes, ac, piste0, elementCapture);
    } catch (e) {
      // C2 : rien ne reste allumé, la session serveur est abandonnée, l'enregistreur est libre
      const s = session;
      session = null;
      if (s) {
        s.enregistreurs.forEach((x) => { try { if (x.rec.state !== "inactive") x.rec.stop(); } catch (z) { /* arrêté */ } });
        s.scene.arreter();
        s.minuteries.forEach(clearInterval);
        if (s.audio) couper(s.audio);
        if (s.encart) s.encart.retirer();
        if (s.ui) s.ui.p.remove();
      }
      nePlusEcouter();
      toutCouper();
      if (id) await fetch(`/api/capture/sessions/${id}`, { method: "DELETE" }).catch(() => {});
      peindreBouton();
      return { ok: false, message: T("capture.erreur.session", { msg: (e && e.message) || "—" }) };
    }
  }

  async function lancer(id, o, p, flux, notes, ac, piste0, elementCapture) {
    // 5. la scène : proportions de la piste écran, 1920 px au plus sur le grand côté ; la mesure des secrets est donnée
    // À LA CRÉATION (revue finale I3 : aucun skin ne peut la remplacer)
    const reglages = piste0.getSettings ? piste0.getSettings() : {};
    let W = reglages.width || window.innerWidth, H = reglages.height || window.innerHeight;
    if (elementCapture) { const r = document.getElementById("root").getBoundingClientRect(); W = r.width * (window.devicePixelRatio || 1); H = r.height * (window.devicePixelRatio || 1); }
    const k = Math.min(1, 1920 / Math.max(W, H));
    const scene = creerScene({ largeur: W * k, hauteur: H * k, fps: 30, secrets: () => mesurerSecrets() });
    scene.source("ecran", video(flux.ecran));
    if (flux.camera) scene.source("camera", video(flux.camera));
    scene.ajouterCalque(calqueEcran());
    if (o.halo) scene.ajouterCalque(calqueClics());
    if (flux.camera) scene.ajouterCalque(calqueEncart());
    scene.etat.forme = o.forme;
    scene.etat.textes.masque = T("capture.masque.ecran");
    // 6. le son : voix (+ son de l'app) mêlés dans la scène ; jauge
    let analyseur = null;
    const pistesAudio = [];
    if (ac && (flux.voix || flux.onglet)) {
      const dest = ac.createMediaStreamDestination();
      if (flux.voix) {
        const src = ac.createMediaStreamSource(flux.voix);
        src.connect(dest);
        analyseur = ac.createAnalyser(); analyseur.fftSize = 256; src.connect(analyseur);
      }
      if (flux.onglet) ac.createMediaStreamSource(flux.onglet).connect(dest);
      pistesAudio.push(...dest.stream.getAudioTracks());
    }
    const audio = pistesAudio.length ? new MediaStream(pistesAudio) : null;
    session = { id, scene, options: o, flux, notes, preuve: p, elementCapture, audio, debut: 0, enregistreurs: [],
      ac, analyseur, minuteries: [], ui: null, encart: null, clics: piste, perdues: [] };
    // 7. le masque AVANT la première image, puis la scène et les enregistreurs
    ecouter();
    session.minuteries.push(setInterval(ecouter, 1000));            // un lab ouvert pendant la capture
    scene.dessiner();
    scene.demarrer();
    const fluxScene = new MediaStream([...scene.flux(30).getVideoTracks(), ...(audio ? audio.getAudioTracks() : [])]);
    session.debut = piste.debut();
    piste.ecran(vue());
    session.enregistreurs.push(enregistreur(id, "scene", fluxScene, "scene"));
    session.enregistreurs.push(enregistreur(id, "ecran", new MediaStream([piste0]), "video"));
    if (flux.camera) session.enregistreurs.push(enregistreur(id, "camera", flux.camera, "video"));
    if (flux.voix) session.enregistreurs.push(enregistreur(id, "voix", flux.voix, "audio"));
    session.minuteries.push(setInterval(() => {
      const e = piste.ecran(vue());
      if (e) window.dispatchEvent(new CustomEvent("dz-capture:ecran", { detail: { ecran: e.ecran } }));
    }, 500));
    // 8. le témoin et l'encart
    session.ui = pastille();
    if (flux.camera) session.encart = encartDom(flux.camera);
    const tampon = new Uint8Array(128);
    session.minuteries.push(setInterval(() => {
      if (!session || !session.ui) return;
      session.ui.temps.textContent = duree(performance.now() - session.debut);
      if (analyseur) {
        analyseur.getByteTimeDomainData(tampon);
        let m = 0; for (const v of tampon) m = Math.max(m, Math.abs(v - 128));
        session.ui.niveau.style.width = Math.min(100, Math.round(m / 128 * 180)) + "%";
      }
    }, 100));
    piste0.addEventListener("ended", () => arreter());              // « Arrêter le partage » du navigateur
    if (piste0.readyState === "ended") throw new Error(T("capture.erreur.refus"));
    peindreBouton();
    window.dispatchEvent(new CustomEvent("dz-capture:debut", { detail: { id } }));
    return { ok: true, id };
  }

  // une piste brute perdue en route : dit dans la pastille, l'enregistrement continue (la scène seule est vitale)
  function pistePerdue(nom) {
    if (!session) return;
    session.perdues.push(nom);
    if (session.ui) session.ui.p.appendChild(el("span", { texte: T("capture.note.piste_perdue", { piste: nom }),
      style: "font-size:11px;color:#e5484d", "data-dz-capture-perdue": nom }));
  }

  // ── arrêter : vider les pistes, tout couper, ranger dans la Bibliothèque ; la session est TOUJOURS libérée ──
  let arret = null;
  function arreter() {
    if (!session) return Promise.resolve(null);
    if (arret) return arret;
    arret = (async () => {
      const s = session;
      let resultat = null, message = "";
      try {
        if (s.ui) { s.ui.arret.disabled = true; s.ui.temps.textContent = T("capture.pastille.envoi"); }
        const dureeMs = Math.round(performance.now() - s.debut);
        s.enregistreurs.forEach((x) => { try { if (x.rec.state !== "inactive") x.rec.stop(); } catch (e) { /* déjà arrêté */ } });
        await Promise.all(s.enregistreurs.map((x) => Promise.race([x.arrete, attendreMs(5000)])));
        s.scene.arreter();
        s.minuteries.forEach(clearInterval);
        Object.values(s.flux).forEach(couper);                    // caméra et micro éteints : le témoin peut partir
        if (s.audio) couper(s.audio);
        if (s.ac) s.ac.close().catch(() => {});
        if (s.encart) s.encart.retirer();
        nePlusEcouter();
        if (s.elementCapture) { const root = document.getElementById("root"); root.style.isolation = ""; root.style.transformStyle = ""; }
        await Promise.all(s.enregistreurs.map((x) => x.file.fin()));
        const scene = s.enregistreurs.find((x) => x.nom === "scene");
        const echec = scene && scene.file.echec();
        if (echec) {
          await fetch(`/api/capture/sessions/${s.id}`, { method: "DELETE" }).catch(() => {});
          message = T("capture.erreur.envoi", { msg: echec.message || "—" });
        } else {
          const r = await fetch(`/api/capture/sessions/${s.id}/terminer`, { method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ clics: s.options.clics ? piste.json() : { version: 1, evenements: [] }, duree_ms: dureeMs,
              cadre: { largeur: s.scene.largeur, hauteur: s.scene.hauteur } }) });
          const j = await r.json().catch(() => ({}));
          if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : String(r.status));
          resultat = j;
        }
      } catch (e) {
        message = T("capture.fin.erreur", { msg: (e && e.message) || "—" });
        Object.values(s.flux).forEach(couper);                    // jamais une caméra laissée allumée
        if (s.encart) s.encart.retirer();
        nePlusEcouter();
      } finally {
        if (s.ui) s.ui.p.remove();
        session = null;
        arret = null;
        peindreBouton();
      }
      window.dispatchEvent(new CustomEvent("dz-capture:fin", { detail: { id: s.id, capture: resultat, job_id: resultat && resultat.job_id } }));
      finir(resultat, message, s.perdues);
      return resultat;
    })();
    return arret;
  }

  function finir(r, message, perdues) {
    const fermer = () => voile.remove();
    const texte = r ? T("capture.fin.texte", { fichier: r.fichier, clics: r.clics.clics, reconnus: r.clics.reconnus }) : message;
    const corps = el("div", { style: S.corps }, [el("div", { texte: texte, "data-dz-brut": true, "data-dz-capture-resultat": r ? "ok" : "erreur",
      style: r ? "" : S.erreur })]);
    if (r && perdues && perdues.length) corps.appendChild(el("div", { style: S.erreur, "data-dz-capture-perdues": true,
      texte: T("capture.fin.pistes_perdues", { pistes: perdues.join(", ") }) }));
    const pied = el("div", { style: S.pied });
    if (r) pied.appendChild(el("button", { type: "button", style: S.bouton, texte: T("capture.fin.biblio"), on: { click: () => {
      fermer(); window.dispatchEvent(new CustomEvent("deepotus:navigate", { detail: { view: "library" } })); } } }));
    const ok = el("button", { type: "button", style: S.principal, texte: T("capture.fin.fermer"), on: { click: fermer } });
    pied.appendChild(ok);
    const voile = el("div", { style: S.voile, "data-dz-capture-ui": true, "data-dz-capture-fin": true }, [
      el("div", { style: S.boite, role: "dialog", "aria-modal": "true", "aria-label": T("capture.fin.titre") }, [
        el("div", { style: S.tete, texte: T(r ? "capture.fin.titre" : "capture.fin.titre_erreur") }), corps, pied])]);
    pieger(voile, fermer);
    document.body.appendChild(voile);
    ok.focus();
  }

  window.__dzCapture = {
    ouvrir, demarrer, arreter, disponible,
    session: () => (session ? { id: session.id, scene: session.scene, debut: session.debut, options: session.options,
      audio: session.audio, clics: session.clics, pistes: session.enregistreurs.map((x) => x.nom) } : null),
  };
}
