// dz-skins.js — t316 (28/10/2026, lot D2 « skins de capture »), les SKINS de la capture côté écran : le groupe
// « Habillage » de la boîte de départ, l'habillage de la scène au lancement, et l'ÉDITEUR de skins (aperçu en direct,
// glisser-déposer, réglages par section, skins livrés, export et import .zip). Plan
// docs/superpowers/plans/2026-10-28-t316-skins.md, spec 2026-10-25-boite-a-outils-design.md §8.5.
// SOURCE : frontend/shared/dz-skins.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-skins.js, chargée par
// frontend/dist/index.html (`<script type="module">`, AVANT dz-capture.js). Aucune dépendance au runtime React, aucun
// maillon de bundle. Banc : backend/tests/test_skins_ecran.py.
//
// API (contrat t317-t319) : window.__dzSkins = {
//   charger() -> {espace, choisi, skins, livres}      la liste de l'espace courant (GET /api/skins)
//   groupeCapture({forme}) -> {noeud, valeur()}         le groupe de la boîte de départ ; valeur() = id | "" | undefined
//   habiller(scene, {skin, camera, halo}) -> habit|null  habille une scène (2 s au plus) ; skin absent = celui de l'espace
//   actuel() -> habit|null ; alerte({type, nom, texte}) ; ecran("pause" | "fin" | null)   (pour le live, t318)
//   ouvrirEditeur({apres}) }
// Un habit (dz-skins-calques.js) : {skin(), maj(skin), alerte(), ecran(), outro() -> Promise, rejouer(), retirer()}.
// Le logo d'un skin est celui DE L'ESPACE (GET /api/espaces/{id}/logo) ou une image du skin ; le logo de
// l'application n'est jamais lu ni changé ici (règle du logo figé).
import { POLICES, disposer, toucher, deplacer } from "./dz-skins-logique.js";
import { habiller as habillerScene } from "./dz-skins-calques.js";
import { creerScene, calqueEcran, calqueClics, calqueEncart } from "./dz-capture-scene.js";

if (!window.__dzSkins) {
  const T = (cle, vars) => (typeof window.dzT === "function" ? window.dzT(cle, vars) : cle);
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
    voile: "position:fixed;inset:0;z-index:2147483005;background:rgba(0,0,0,.62);display:flex;align-items:center;justify-content:center",
    boite: "width:1320px;max-width:97vw;height:860px;max-height:95vh;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    corps: "flex:1;min-height:0;display:flex",
    gauche: "width:220px;flex:none;border-right:1px solid var(--brd-soft,var(--stroke,#222830));overflow-y:auto;padding:8px;display:flex;flex-direction:column;gap:4px",
    centre: "flex:1;min-width:0;display:flex;flex-direction:column;gap:8px;padding:10px;overflow:auto",
    droite: "width:340px;flex:none;border-left:1px solid var(--brd-soft,var(--stroke,#222830));overflow-y:auto;padding:8px 10px;display:flex;flex-direction:column;gap:6px",
    groupe: "display:flex;flex-direction:column;gap:5px",
    titreG: "font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    section: "border:1px solid var(--brd-soft,var(--stroke,#222830));border-radius:0;padding:0",
    resume: "cursor:pointer;padding:6px 8px;font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    champs: "display:flex;flex-direction:column;gap:6px;padding:4px 8px 8px",
    ligne: "display:flex;align-items:center;gap:8px",
    libelle: "flex:none;width:118px;font-size:12px;color:var(--txt-base,var(--ink,#cfd6e2))",
    note: "font-size:11.5px;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    erreur: "font-size:12px;color:var(--red,#e5484d)",
    champ: "font:inherit;font-size:12px;padding:3px 6px;border-radius:0;background:var(--srf-raised,var(--bg-panel-3,#1b2028));color:var(--txt-hi,var(--ink-strong,#e6e9ee));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));min-width:0;flex:1",
    pied: "display:flex;gap:8px;align-items:center;padding:10px 14px;border-top:1px solid var(--brd-soft,var(--stroke,#222830))",
    bouton: "font:inherit;font-size:12.5px;padding:5px 12px;border-radius:0;cursor:pointer;background:var(--srf-raised,var(--bg-panel-3,#1b2028));color:var(--txt-hi,var(--ink-strong,#e6e9ee));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138))",
    principal: "font:inherit;font-size:12.5px;padding:5px 12px;border-radius:0;cursor:pointer;background:var(--brand,#f0b429);color:#111;border:1px solid var(--brand,#f0b429);font-weight:600",
    item: "text-align:left;font:inherit;font-size:12.5px;padding:6px 8px;border-radius:0;cursor:pointer;background:transparent;color:inherit;border:1px solid transparent;display:flex;flex-direction:column;gap:2px",
    badge: "font:9px 'IBM Plex Mono',monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    apercu: "position:relative;width:100%;aspect-ratio:16/9;background:#000;border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138))",
  };

  // un bouton grisé se voit grisé (les styles en ligne gardent sinon l'aspect actif)
  const feuille = el("style", { "data-dz-skins-ui": true,
    texte: "[data-dz-skins-editeur] button:disabled,[data-dz-skins-groupe] button:disabled{opacity:.42;cursor:not-allowed}" });
  document.head.appendChild(feuille);

  async function api(methode, url, corps, type) {
    const o = { method: methode, headers: {} };
    if (corps !== undefined) {
      o.body = type ? corps : JSON.stringify(corps);
      o.headers["Content-Type"] = type || "application/json";
    }
    const r = await fetch(url, o);
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      throw new Error(typeof j.detail === "string" ? j.detail : String(r.status));
    }
    return (r.headers.get("content-type") || "").includes("json") ? r.json() : r.blob();
  }
  const delai = (p, ms) => Promise.race([p, new Promise((ok) => setTimeout(() => ok(null), ms))]);
  const nomLivre = (id) => T("skins.livre." + String(id).replace(/^livre-/, ""));
  const nomSkin = (s) => (s.livre ? nomLivre(s.id) : s.nom);

  // ── données ──
  let liste = null;
  async function charger() { liste = await api("GET", "/api/skins"); return liste; }
  const details = new Map();
  function chargerImage(url) {
    return new Promise((ok) => {
      if (!url) { ok(null); return; }
      const im = new Image();
      const fin = (v) => { clearTimeout(minuterie); ok(v); };
      const minuterie = setTimeout(() => fin(null), 4000);
      im.onload = () => fin(im);
      im.onerror = () => fin(null);
      im.src = url;
    });
  }
  async function preparer(id) {
    const d = await api("GET", "/api/skins/" + encodeURIComponent(id));
    const sk = d.skin, cx = d.contexte, v = encodeURIComponent(sk.modifie || "0");
    const logo = sk.logo.source === "image" && sk.images.includes("logo") ? `/api/skins/${sk.id}/images/logo?v=${v}`
      : `${cx.logo_espace}?v=${Date.now()}`;
    const fond = sk.images.includes("fond") ? `/api/skins/${sk.id}/images/fond?v=${v}` : null;
    const [li, fi] = await Promise.all([chargerImage(logo), chargerImage(fond)]);
    const r = { skin: sk, contexte: cx, images: { logo: li, fond: fi } };
    details.set(id, r);
    return r;
  }

  // ── pour l'enregistreur (dz-capture.js) ──
  let habit = null;
  async function habiller(scene, o) {
    let id = o && typeof o.skin === "string" ? o.skin : undefined;
    try {
      if (id === undefined) { const l = liste || await delai(charger(), 1500); id = l ? l.choisi : ""; }
      if (!id) return null;
      const d = details.get(id) || await delai(preparer(id), 2000);
      if (!d || (scene.etat && scene.etat.sansSkin)) return null;      // arrivé trop tard : la capture a commencé sans
      habit = habillerScene(scene, d.skin, { contexte: d.contexte, T, images: d.images });
      return habit;
    } catch (e) { return null; }                 // un skin en panne ne bloque jamais la capture
  }
  window.addEventListener("dz-capture:fin", () => { habit = null; });

  function groupeCapture(rappels) {
    let charge = false;
    const sel = el("select", { style: S.champ, "data-dz-skins-choix": true, "aria-label": T("skins.capture.choix") });
    const note = el("div", { style: S.note, "data-dz-skins-note": true });
    const choisi = (id) => {
      if (!id) return;
      preparer(id).then((d) => {
        if (sel.value === id && rappels && typeof rappels.forme === "function" && d) rappels.forme(d.skin.encart.forme);
      }).catch(() => {});
    };
    async function remplir() {
      let l;
      try { l = await charger(); } catch (e) { note.textContent = T("skins.erreur.liste", { msg: e.message || "—" }); return; }
      const opt = (s) => el("option", { value: s.id, texte: nomSkin(s), "data-dz-brut": s.livre ? false : true });
      sel.replaceChildren(el("option", { value: "", texte: T("skins.capture.aucun") }), ...l.skins.map(opt), ...l.livres.map(opt));
      sel.value = l.choisi;
      charge = true;
      choisi(sel.value);
    }
    sel.addEventListener("change", () => choisi(sel.value));
    const btn = el("button", { type: "button", style: S.bouton + ";padding:3px 10px", "data-dz-skins-ouvrir": true,
      texte: T("skins.capture.modifier"), on: { click: () => ouvrirEditeur({ apres: remplir }) } });
    const noeud = el("div", { style: S.groupe, "data-dz-skins-groupe": true }, [
      el("div", { style: S.titreG, texte: T("skins.capture.titre") }),
      el("div", { style: S.ligne }, [sel, btn]), note]);
    remplir();
    return { noeud, valeur: () => (charge ? sel.value : undefined) };
  }

  // ── l'éditeur ──
  // [section, clé, type, …] ; un chemin « fond.type » descend dans un objet
  const CHAMPS = [
    ["couleurs", [["principale", "kit"], ["accent", "kit"], ["texte", "hex"], ["fond", "hex"]]],
    ["polices", [["titre", "police"], ["texte", "police"]]],
    ["cadre", [["marge", "plage", 0, 0.12, 0.005], ["bord", "plage", 0, 0.02, 0.001], ["couleur", "ref"],
      ["fond.type", "choix", ["degrade", "uni", "image"]], ["fond.c1", "ref"], ["fond.c2", "ref"], ["@fond", "image"]]],
    ["logo", [["actif", "case"], ["source", "choix", ["espace", "image"]], ["l", "plage", 0.03, 0.3, 0.005],
      ["opacite", "plage", 0.2, 1, 0.05], ["@logo", "image"]]],
    ["bandeau", [["actif", "case"], ["titre", "texte"], ["sous_titre", "texte"], ["style", "choix", ["bande", "bloc", "souligne"]],
      ["l", "plage", 0.2, 0.9, 0.01], ["debut_s", "plage", 0, 60, 1], ["duree_s", "plage", 0, 120, 1]]],
    ["intro", [["actif", "case"], ["titre", "texte"], ["sous_titre", "texte"], ["duree_s", "plage", 1, 8, 0.5]]],
    ["outro", [["actif", "case"], ["titre", "texte"], ["sous_titre", "texte"], ["duree_s", "plage", 1, 8, 0.5]]],
    ["encart", [["forme", "choix", ["cercle", "carre", "vif"]], ["bord", "plage", 0, 0.02, 0.001], ["couleur", "ref"],
      ["ombre", "case"], ["l", "plage", 0.08, 0.6, 0.01], ["h", "plage", 0.08, 0.6, 0.01]]],
    ["alertes", [["actif", "case"], ["abonne", "texte"], ["message", "texte"], ["duree_s", "plage", 2, 10, 0.5],
      ["l", "plage", 0.15, 0.7, 0.01]]],
    ["pause", [["titre", "texte"], ["sous_titre", "texte"]]],
    ["fin", [["titre", "texte"], ["sous_titre", "texte"]]],
    ["zoom", [["niveau", "plage", 1.1, 2.5, 0.05], ["duree_ms", "plage", 800, 4000, 100]]],
    ["curseur", [["style", "choix", ["anneau", "point", "aucun"]], ["couleur", "ref"], ["taille", "plage", 0.5, 2, 0.1]]],
    ["signature", [["actif", "case"], ["coin", "choix", ["bas-droite", "bas-gauche", "haut-droite", "haut-gauche"]],
      ["opacite", "plage", 0.3, 1, 0.05]]],
  ];
  const ROLES = ["principale", "accent", "texte", "fond"];
  const cleChamp = (sec, cle) => (sec === "couleurs" ? "skins.couleur." + cle : sec === "polices" ? "skins.police." + cle
    : "skins.champ." + cle.replace(".", "_").replace("@", "image_"));
  const cleOption = (v) => "skins.option." + String(v).replace("-", "_");
  const lireChemin = (o, ch) => ch.split(".").reduce((x, k) => (x == null ? undefined : x[k]), o);
  function ecrireChemin(o, ch, v) {
    const ks = ch.split("."), dernier = ks.pop();
    let x = o;
    for (const k of ks) { if (typeof x[k] !== "object" || x[k] == null) x[k] = {}; x = x[k]; }
    x[dernier] = v;
  }

  // la capture d'EXEMPLE de l'aperçu : une esquisse de l'app dessinée (aucun écran réel n'est filmé ici)
  function exemple(W, H) {
    const c = document.createElement("canvas");
    c.width = W; c.height = H;
    const g = c.getContext("2d");
    g.fillStyle = "#0e1217"; g.fillRect(0, 0, W, H);
    g.fillStyle = "#151a21"; g.fillRect(0, 0, W * 0.16, H);
    g.fillStyle = "#11161c"; g.fillRect(W * 0.16, 0, W, H * 0.07);
    g.fillStyle = "#f0b429"; g.fillRect(W * 0.02, H * 0.03, W * 0.05, H * 0.025);
    for (let i = 0; i < 9; i++) { g.fillStyle = i === 2 ? "#26303b" : "#1b2129"; g.fillRect(W * 0.015, H * (0.12 + i * 0.075), W * 0.13, H * 0.05); }
    for (let i = 0; i < 6; i++) {
      const x = W * (0.19 + (i % 3) * 0.265), y = H * (0.12 + Math.floor(i / 3) * 0.42);
      g.fillStyle = "#171d25"; g.fillRect(x, y, W * 0.245, H * 0.38);
      const d = g.createLinearGradient(x, y, x + W * 0.245, y + H * 0.26);
      d.addColorStop(0, ["#1d3a5f", "#3a1d5f", "#1d5f4a", "#5f3a1d", "#5f1d3a", "#2e5f1d"][i]); d.addColorStop(1, "#0b0f14");
      g.fillStyle = d; g.fillRect(x + 8, y + 8, W * 0.245 - 16, H * 0.26);
      g.fillStyle = "#2a3138"; g.fillRect(x + 8, y + H * 0.3, W * 0.15, H * 0.02);
      g.fillStyle = "#f0b429"; g.fillRect(x + W * 0.245 - 8 - W * 0.06, y + H * 0.3, W * 0.06, H * 0.035);
    }
    c.readyState = 4;
    return c;
  }
  function fausseCamera() {
    const c = document.createElement("canvas");
    c.width = 640; c.height = 480;
    const g = c.getContext("2d");
    const peindre = () => {
      const t = performance.now() / 1000, d = g.createLinearGradient(0, 0, 640, 480);
      d.addColorStop(0, "#1d3a5f"); d.addColorStop(1, "#5f1d3a");
      g.fillStyle = d; g.fillRect(0, 0, 640, 480);
      g.fillStyle = "#e6c7a8"; g.beginPath(); g.arc(320 + Math.sin(t) * 12, 210, 110, 0, Math.PI * 2); g.fill();
      g.fillStyle = "#2a3138"; g.fillRect(170, 330, 300, 150);
    };
    peindre();
    const id = setInterval(peindre, 80);
    Object.assign(c, { readyState: 4, videoWidth: 640, videoHeight: 480, _dzArret: () => clearInterval(id) });
    return c;
  }

  let editeur = null;
  async function ouvrirEditeur(opts) {
    if (editeur) return;
    const W = 1280, H = 720;
    const ed = { courant: null, skin: null, contexte: null, images: {}, sale: false, habit: null, livre: false };
    editeur = ed;
    const statut = el("div", { style: S.note + ";flex:1", role: "status", "aria-live": "polite", "data-dz-skins-statut": true });
    const dire = (m, err) => { statut.textContent = m || ""; statut.style.color = err ? "var(--red,#e5484d)" : ""; };
    const gauche = el("div", { style: S.gauche, "data-dz-skins-liste": true });
    const droite = el("div", { style: S.droite, "data-dz-skins-reglages": true });
    const titreEspace = el("span", { "data-dz-brut": true });

    // la scène d'aperçu : la MÊME scène que l'enregistrement, sur une capture d'exemple, sans aucun secret
    const scene = creerScene({ largeur: W, hauteur: H, fps: 30, secrets: () => [] });
    const cam = fausseCamera();
    scene.source("ecran", exemple(W, H)).source("camera", cam);
    scene.ajouterCalque(calqueEcran()).ajouterCalque(calqueClics()).ajouterCalque(calqueEncart());
    scene.etat.encart = { x: 0.76, y: 0.62, l: 0.2, h: 0.32 };
    const canvas = scene.canvas;
    canvas.setAttribute("data-dz-skins-apercu", "");
    canvas.setAttribute("aria-label", T("skins.editeur.apercu"));
    canvas.style.cssText = "position:absolute;inset:0;width:100%;height:100%;display:block;cursor:crosshair;touch-action:none";
    scene.demarrer();

    function poser(skin) {
      if (ed.habit) { ed.habit.retirer(); ed.habit = null; }
      ed.skin = skin;
      if (skin) ed.habit = habillerScene(scene, skin, { contexte: ed.contexte, T, images: ed.images, apercu: true });
    }
    function modifie() {
      ed.sale = true;
      if (ed.habit) ed.habit.maj(ed.skin);
      peindreBoutons();
    }

    // ── glisser-déposer dans l'aperçu ; ailleurs, un clic montre le curseur et le zoom du skin ──
    let prise = null;
    const versScene = (ev) => { const r = canvas.getBoundingClientRect(); return { x: (ev.clientX - r.left) * W / (r.width || 1), y: (ev.clientY - r.top) * H / (r.height || 1) }; };
    canvas.addEventListener("pointerdown", (ev) => {
      if (!ed.skin) return;
      const p = versScene(ev), n = toucher(ed.skin, disposer(ed.skin, W, H), p.x, p.y, true);
      if (n) {
        ev.preventDefault();
        try { canvas.setPointerCapture(ev.pointerId); } catch (x) { /* déjà relâché */ }
        prise = { nom: n, p };
        canvas.style.cursor = "grabbing";
        return;
      }
      const t = performance.now();
      scene.etat.clics.push({ x: p.x, y: p.y, debut: t });
      scene.etat.zoom = Object.assign({}, scene.etat.styleZoom, { cx: p.x, cy: p.y, debut: t });
    });
    canvas.addEventListener("pointermove", (ev) => {
      if (!prise) return;
      const p = versScene(ev);
      ed.skin = deplacer(ed.skin, prise.nom, (p.x - prise.p.x) / W, (p.y - prise.p.y) / H, W, H, p.x / W, p.y / H);
      prise.p = p;
      modifie();
    });
    const lacher = () => { prise = null; canvas.style.cursor = "crosshair"; };
    canvas.addEventListener("pointerup", lacher);
    canvas.addEventListener("pointercancel", lacher);

    // ── la liste ──
    function peindreListe() {
      const l = liste || { skins: [], livres: [], choisi: "" };
      const item = (id, nom, badges, brut) => {
        const b = el("button", { type: "button", style: S.item + (id === ed.courant ? ";border-color:var(--brand,#f0b429);background:var(--srf-raised,#1b2028)" : ""),
          "data-dz-skins-item": id, "aria-pressed": id === ed.courant ? "true" : "false", on: { click: () => choisir(id) } },
        [el("span", { texte: nom, "data-dz-brut": brut ? true : false }), badges.length ? el("span", { style: S.badge, texte: badges.join(" · ") }) : null]);
        return b;
      };
      const badges = (id, livre) => [livre ? T("skins.liste.livre") : null, l.choisi === id ? T("skins.liste.espace") : null].filter(Boolean);
      gauche.replaceChildren(
        el("div", { style: S.titreG, texte: T("skins.liste.titre") }),
        item("", T("skins.capture.aucun"), badges("", false), false),
        ...l.skins.map((s) => item(s.id, s.nom, badges(s.id, false), true)),
        el("div", { style: S.titreG + ";margin-top:8px", texte: T("skins.liste.livres") }),
        ...l.livres.map((s) => item(s.id, nomLivre(s.id), badges(s.id, true), false)),
        el("div", { style: "flex:1" }),
        btnImporter);
    }
    async function rafraichir() {
      try { await charger(); } catch (e) { dire(T("skins.erreur.liste", { msg: e.message || "—" }), true); }
      titreEspace.textContent = liste ? (liste.espace_nom || liste.espace) : "";
      peindreListe();
    }
    async function choisir(id, force) {
      if (ed.sale && !force) {
        if (ed.confirmeChoix !== id) { ed.confirmeChoix = id; dire(T("skins.editeur.perdre"), true); return; }
      }
      ed.confirmeChoix = null;
      ed.courant = id; ed.sale = false;
      if (!id) {
        ed.contexte = null; ed.images = {}; ed.livre = false;
        poser(null); peindreReglages(); peindreListe(); peindreBoutons(); dire("");
        return;
      }
      dire(T("skins.editeur.chargement"));
      try {
        const d = await preparer(id);
        if (ed.courant !== id) return;
        ed.contexte = d.contexte; ed.images = d.images; ed.livre = !!d.skin.livre;
        poser(JSON.parse(JSON.stringify(d.skin)));
        dire(ed.livre ? T("skins.editeur.note_livre") : "");
      } catch (e) { dire(T("skins.erreur.lecture", { msg: e.message || "—" }), true); poser(null); }
      peindreReglages(); peindreListe(); peindreBoutons();
    }

    // ── les réglages ──
    function champ(sec, def) {
      const [cle, type, a, b, pas] = def;
      const chemin = sec + "." + cle;
      const val = lireChemin(ed.skin, chemin);
      const libelle = el("span", { style: S.libelle, texte: T(cleChamp(sec, cle)) });
      const regle = (v) => { ecrireChemin(ed.skin, chemin, v); modifie(); };
      const attr = { "data-dz-skins-champ": chemin, "aria-label": T(cleChamp(sec, cle)) };
      let ctrl;
      if (type === "case") {
        ctrl = el("input", Object.assign({ type: "checkbox" }, attr));
        ctrl.checked = !!val;
        ctrl.addEventListener("change", () => regle(ctrl.checked));
        return el("label", { style: S.ligne }, [ctrl, el("span", { texte: T(cleChamp(sec, cle)) })]);
      }
      if (type === "plage") {
        const lu = el("span", { style: S.note + ";width:44px;text-align:right;font-variant-numeric:tabular-nums" });
        ctrl = el("input", Object.assign({ type: "range", min: a, max: b, step: pas, style: "flex:1;min-width:0" }, attr));
        ctrl.value = String(val);
        const montrer = () => { lu.textContent = Number(ctrl.value) >= 100 ? String(Math.round(ctrl.value)) : String(Math.round(Number(ctrl.value) * 1000) / 1000); };
        montrer();
        ctrl.addEventListener("input", () => { montrer(); regle(Number(ctrl.value)); });
        return el("div", { style: S.ligne }, [libelle, ctrl, lu]);
      }
      if (type === "texte") {
        ctrl = el("input", Object.assign({ type: "text", maxlength: "80", style: S.champ, placeholder: T("skins.editeur.defaut") }, attr));
        ctrl.value = val || "";
        ctrl.addEventListener("input", () => regle(ctrl.value));
        return el("div", { style: S.ligne }, [libelle, ctrl]);
      }
      if (type === "choix") {
        ctrl = el("select", Object.assign({ style: S.champ }, attr), a.map((v) => el("option", { value: v, texte: T(cleOption(v)) })));
        ctrl.value = val;
        ctrl.addEventListener("change", () => regle(ctrl.value));
        return el("div", { style: S.ligne }, [libelle, ctrl]);
      }
      if (type === "police") {
        ctrl = el("select", Object.assign({ style: S.champ }, attr),
          [el("option", { value: "", texte: T("skins.editeur.identite") }), ...POLICES.map((p) => el("option", { value: p, texte: p, "data-dz-brut": true }))]);
        ctrl.value = val || "";
        ctrl.addEventListener("change", () => regle(ctrl.value || null));
        return el("div", { style: S.ligne }, [libelle, ctrl]);
      }
      if (type === "hex" || type === "kit") {
        const coul = el("input", Object.assign({ type: "color", style: "width:42px;height:24px;padding:0;border-radius:0;border:1px solid var(--brd-hard,#2a3138);background:none" }, attr));
        coul.value = val || (sec === "couleurs" && cle === "accent" ? ((ed.contexte && ed.contexte.kit.accent_color) || "#00e5ff")
          : ((ed.contexte && ed.contexte.kit.brand_color) || "#f0b429"));
        const enfants = [libelle, coul];
        if (type === "kit") {
          const kit = el("input", { type: "checkbox", "data-dz-skins-kit": chemin, "aria-label": T("skins.editeur.kit") });
          kit.checked = val == null;
          coul.disabled = kit.checked;
          kit.addEventListener("change", () => { coul.disabled = kit.checked; regle(kit.checked ? null : coul.value); });
          enfants.push(el("label", { style: S.ligne + ";font-size:12px" }, [kit, el("span", { texte: T("skins.editeur.kit") })]));
        }
        coul.addEventListener("input", () => regle(coul.value));
        return el("div", { style: S.ligne }, enfants);
      }
      if (type === "ref") {
        const role = ROLES.includes(val) ? val : "perso";
        ctrl = el("select", Object.assign({ style: S.champ }, attr),
          [...ROLES.map((r) => el("option", { value: r, texte: T("skins.couleur." + r) })), el("option", { value: "perso", texte: T("skins.option.perso") })]);
        ctrl.value = role;
        const coul = el("input", { type: "color", "aria-label": T(cleChamp(sec, cle)), style: "width:42px;height:24px;padding:0;border-radius:0;border:1px solid var(--brd-hard,#2a3138);background:none" });
        coul.value = role === "perso" ? val : "#f0b429";
        coul.style.display = role === "perso" ? "" : "none";
        ctrl.addEventListener("change", () => { coul.style.display = ctrl.value === "perso" ? "" : "none"; regle(ctrl.value === "perso" ? coul.value : ctrl.value); });
        coul.addEventListener("input", () => regle(coul.value));
        return el("div", { style: S.ligne }, [libelle, ctrl, coul]);
      }
      if (type === "image") {
        const nom = cle.slice(1);
        const fichier = el("input", { type: "file", accept: "image/png,image/jpeg,image/webp", style: "display:none" });
        const poserImg = el("button", { type: "button", style: S.bouton + ";padding:3px 8px", "data-dz-skins-image": nom,
          texte: T("skins.editeur.image_choisir"), disabled: ed.livre, on: { click: () => fichier.click() } });
        const oter = el("button", { type: "button", style: S.bouton + ";padding:3px 8px", "data-dz-skins-image-oter": nom,
          texte: T("skins.editeur.image_retirer"), disabled: ed.livre || !(ed.skin.images || []).includes(nom),
          on: { click: () => image(nom, null) } });
        fichier.addEventListener("change", () => { const f = fichier.files && fichier.files[0]; if (f) image(nom, f); fichier.value = ""; });
        return el("div", { style: S.ligne }, [libelle, poserImg, oter, fichier]);
      }
      return null;
    }
    function peindreReglages() {
      if (!ed.skin) {
        droite.replaceChildren(el("div", { style: S.note, texte: T("skins.editeur.sans") }));
        return;
      }
      const nom = el("input", { type: "text", maxlength: "60", style: S.champ, "data-dz-skins-champ": "nom", "aria-label": T("skins.editeur.nom"),
        disabled: ed.livre, "data-dz-brut": true });
      nom.value = ed.livre ? nomLivre(ed.courant) : ed.skin.nom;
      nom.addEventListener("input", () => { ed.skin.nom = nom.value; modifie(); });
      const blocs = [el("div", { style: S.ligne }, [el("span", { style: S.libelle, texte: T("skins.editeur.nom") }), nom])];
      if (ed.livre) blocs.push(el("div", { style: S.note, texte: T("skins.editeur.note_livre") }));
      CHAMPS.forEach(([sec, defs], i) => {
        const d = el("details", { style: S.section, "data-dz-skins-section": sec, open: i < 2 || sec === "signature" ? true : false }, [
          el("summary", { style: S.resume, texte: T("skins.section." + sec) }),
          el("div", { style: S.champs }, defs.map((x) => champ(sec, x)))]);
        blocs.push(d);
      });
      droite.replaceChildren(...blocs);
    }

    // ── actions ──
    async function enregistrer() {
      if (!ed.skin || !ed.sale) return true;
      try {
        let id = ed.courant;
        if (ed.livre) {
          const copie = await api("POST", "/api/skins", { base: id, nom: nomLivre(id) });   // nom traduit du livré
          id = copie.id;
          ed.skin.nom = copie.nom;
        }
        const v = await api("PUT", "/api/skins/" + id, ed.skin);
        details.delete(id);
        ed.sale = false;
        await rafraichir();
        await choisir(id, true);
        dire(T("skins.editeur.enregistre", { nom: v.nom }));
        return true;
      } catch (e) { dire(T("skins.erreur.enregistrer", { msg: e.message || "—" }), true); return false; }
    }
    async function image(nom, fichier) {
      if (ed.livre || !ed.courant) return;
      if (ed.sale && !(await enregistrer())) return;
      try {
        if (fichier) await api("PUT", `/api/skins/${ed.courant}/images/${nom}`, fichier, fichier.type || "application/octet-stream");
        else await api("DELETE", `/api/skins/${ed.courant}/images/${nom}`);
        details.delete(ed.courant);
        await choisir(ed.courant, true);
        dire(T(fichier ? "skins.editeur.image_posee" : "skins.editeur.image_otee"));
      } catch (e) { dire(T("skins.erreur.image", { msg: e.message || "—" }), true); }
    }
    async function dupliquer() {
      if (!ed.courant) return;
      try {
        const v = await api("POST", "/api/skins", { base: ed.courant, nom: ed.livre ? nomLivre(ed.courant) : undefined });
        if (ed.sale) { await api("PUT", "/api/skins/" + v.id, Object.assign({}, ed.skin, { nom: v.nom })); }
        ed.sale = false;
        await rafraichir();
        await choisir(v.id, true);
        dire(T("skins.editeur.duplique", { nom: v.nom }));
      } catch (e) { dire(T("skins.erreur.enregistrer", { msg: e.message || "—" }), true); }
    }
    async function supprimer() {
      if (!ed.courant || ed.livre) return;
      if (ed.confirmeSuppr !== ed.courant) { ed.confirmeSuppr = ed.courant; btnSupprimer.textContent = T("skins.editeur.confirmer_supprimer"); return; }
      ed.confirmeSuppr = null;
      try {
        await api("DELETE", "/api/skins/" + ed.courant);
        details.delete(ed.courant);
        ed.sale = false;
        await rafraichir();
        await choisir(liste ? liste.choisi : "", true);
        dire(T("skins.editeur.supprime"));
      } catch (e) { dire(T("skins.erreur.enregistrer", { msg: e.message || "—" }), true); }
    }
    async function utiliser() {
      if (ed.sale && !(await enregistrer())) return;
      try {
        await api("PUT", "/api/skins/choix", { skin_id: ed.courant || "" });
        await rafraichir();
        dire(T("skins.editeur.utilise"));
      } catch (e) { dire(T("skins.erreur.enregistrer", { msg: e.message || "—" }), true); }
      peindreBoutons();
    }
    async function exporter() {
      if (!ed.courant) return;
      if (ed.sale && !(await enregistrer())) return;
      try {
        const r = await fetch(`/api/skins/${ed.courant}/export`);
        if (!r.ok) { const j = await r.json().catch(() => ({})); throw new Error(typeof j.detail === "string" ? j.detail : String(r.status)); }
        const nom = ((r.headers.get("content-disposition") || "").match(/filename="([^"]+)"/) || [])[1] || "skin.zip";
        const url = URL.createObjectURL(await r.blob());
        const a = el("a", { href: url, download: nom, style: "display:none" });
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 2000);
        dire(T("skins.editeur.exporte", { fichier: nom }));
      } catch (e) { dire(T("skins.erreur.export", { msg: e.message || "—" }), true); }
    }
    const fichierZip = el("input", { type: "file", accept: ".zip,application/zip", style: "display:none", "data-dz-skins-fichier": true });
    fichierZip.addEventListener("change", async () => {
      const f = fichierZip.files && fichierZip.files[0];
      fichierZip.value = "";
      if (!f) return;
      try {
        const v = await api("POST", "/api/skins/import", f, "application/zip");
        await rafraichir();
        await choisir(v.id, true);
        dire(T("skins.editeur.importe", { nom: v.nom }) + (v.ignores && v.ignores.length ? " " + T("skins.editeur.ignores", { liste: v.ignores.join(", ") }) : ""));
      } catch (e) { dire(T("skins.erreur.import", { msg: e.message || "—" }), true); }
    });
    const btnImporter = el("button", { type: "button", style: S.bouton, "data-dz-skins-importer": true, texte: T("skins.editeur.importer"),
      on: { click: () => fichierZip.click() } });

    // ── la lecture (aperçu des moments du skin) ──
    const lecture = (cle, f) => el("button", { type: "button", style: S.bouton + ";padding:3px 10px", "data-dz-skins-jouer": cle,
      texte: T("skins.jouer." + cle), on: { click: () => { if (ed.habit) f(ed.habit); } } });
    const barreLecture = el("div", { style: "display:flex;flex-wrap:wrap;gap:6px" }, [
      lecture("intro", (h) => h.rejouer()),
      lecture("outro", (h) => { h.ecran(null); h.outro().then(() => { if (ed.habit === h) { h.etat.outro = null; } }); }),
      lecture("abonne", (h) => h.alerte({ type: "abonne", nom: "Zoé" })),
      lecture("message", (h) => h.alerte({ type: "message", nom: "Zoé", texte: T("skins.jouer.exemple") })),
      lecture("pause", (h) => h.ecran(h.etat.ecran === "pause" ? null : "pause")),
      lecture("fin", (h) => h.ecran(h.etat.ecran === "fin" ? null : "fin")),
    ]);

    // ── pied ──
    const btnEnregistrer = el("button", { type: "button", style: S.principal, "data-dz-skins-enregistrer": true, texte: T("skins.editeur.enregistrer"), on: { click: enregistrer } });
    const btnDupliquer = el("button", { type: "button", style: S.bouton, "data-dz-skins-dupliquer": true, texte: T("skins.editeur.dupliquer"), on: { click: dupliquer } });
    const btnSupprimer = el("button", { type: "button", style: S.bouton, "data-dz-skins-supprimer": true, texte: T("skins.editeur.supprimer"), on: { click: supprimer } });
    const btnExporter = el("button", { type: "button", style: S.bouton, "data-dz-skins-exporter": true, texte: T("skins.editeur.exporter"), on: { click: exporter } });
    const btnUtiliser = el("button", { type: "button", style: S.bouton, "data-dz-skins-utiliser": true, texte: T("skins.editeur.utiliser"), on: { click: utiliser } });
    const btnFermer = el("button", { type: "button", style: S.bouton, "data-dz-skins-fermer": true, texte: T("skins.editeur.fermer"), on: { click: () => fermer() } });
    function peindreBoutons() {
      btnEnregistrer.disabled = !ed.skin || !ed.sale;
      btnEnregistrer.textContent = T(ed.livre ? "skins.editeur.enregistrer_copie" : "skins.editeur.enregistrer");
      btnDupliquer.disabled = !ed.courant;
      btnSupprimer.disabled = !ed.courant || ed.livre;
      if (ed.confirmeSuppr !== ed.courant) btnSupprimer.textContent = T("skins.editeur.supprimer");
      btnExporter.disabled = !ed.courant;
      btnUtiliser.disabled = !!(liste && liste.choisi === ed.courant);
      if (ed.confirmeFermer) btnFermer.textContent = T("skins.editeur.fermer");
      ed.confirmeFermer = false;
    }

    function fermer() {
      if (ed.sale && !ed.confirmeFermer) {
        ed.confirmeFermer = true;
        btnFermer.textContent = T("skins.editeur.fermer_perdre");
        dire(T("skins.editeur.perdre"), true);
        return;
      }
      if (ed.habit) ed.habit.retirer();
      scene.arreter();
      if (cam._dzArret) cam._dzArret();
      voile.remove();
      editeur = null;
      if (opts && typeof opts.apres === "function") opts.apres();
    }

    const voile = el("div", { style: S.voile, "data-dz-skins-editeur": true, "data-dz-capture-ui": true }, [
      el("div", { style: S.boite, role: "dialog", "aria-modal": "true", "aria-label": T("skins.editeur.titre") }, [
        el("div", { style: S.tete }, [el("span", { texte: T("skins.editeur.titre") + " — " }), titreEspace]),
        el("div", { style: S.corps }, [
          gauche,
          el("div", { style: S.centre }, [
            el("div", { style: S.apercu }, [canvas]),
            barreLecture,
            el("div", { style: S.note, texte: T("skins.editeur.aide") }),
          ]),
          droite,
        ]),
        el("div", { style: S.pied }, [statut, btnSupprimer, btnExporter, btnDupliquer, btnUtiliser, btnEnregistrer, btnFermer, fichierZip]),
      ]),
    ]);
    voile.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") { ev.preventDefault(); fermer(); return; }
      if (ev.key !== "Tab") return;
      const f = Array.from(voile.querySelectorAll("button, input, select, summary")).filter((x) => !x.disabled && x.offsetParent !== null);
      if (!f.length) return;
      const i = f.indexOf(document.activeElement);
      if (ev.shiftKey && i <= 0) { ev.preventDefault(); f[f.length - 1].focus(); }
      else if (!ev.shiftKey && i === f.length - 1) { ev.preventDefault(); f[0].focus(); }
    });
    document.body.appendChild(voile);
    peindreReglages();
    peindreBoutons();
    await rafraichir();
    await choisir(liste ? liste.choisi : "", true);
    btnFermer.focus();
  }

  window.__dzSkins = {
    charger, habiller, groupeCapture, ouvrirEditeur,
    actuel: () => habit,
    alerte: (a) => (habit ? habit.alerte(a) : false),
    ecran: (n) => (habit ? habit.ecran(n) : null),
  };
}
