// dz-studiov.js — SV1 (14/11/2026), le STUDIO VIRTUEL 3D côté écran : le groupe « Studio virtuel » de la boîte de
// capture, l'habillage de la scène au lancement (calque 3D sous le skin, écran du décor, caméras), et l'APERÇU des
// décors (liste, rendu en direct, caméras, choix pour l'espace, duplication). Conception
// docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md.
// SOURCE : frontend/shared/dz-studiov.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-studiov.js, chargée par
// frontend/dist/index.html (`<script type="module">`, AVANT dz-capture.js). Aucun maillon de bundle. three.js n'est
// chargé (/assets/three, embarqué) qu'au premier décor affiché. Banc : backend/tests/test_studiov_ecran.py.
//
// API : window.__dzStudiov = {
//   charger() -> {espace, choisi, decors, livres, catalogue}        GET /api/studiov
//   groupeCapture() -> {noeud, valeur()}      le groupe de la boîte de départ ; valeur() = id | "" | undefined
//   habiller(scene, {decor}) -> habit | null  pose le studio sur une scène (3,5 s au plus ; null = sans studio) ;
//                                             decor absent = celui de l'espace
//   actuel() -> habit | null ; oublier() ; ouvrirApercu({apres}) }
// Un habit : {decor(), cameras(), camera(i), courante(), retirer()}. Pendant une capture, Ctrl+Alt+1…6 change de caméra.
// Mode « plateau » : l'écran partagé quitte l'image et va sur l'écran du décor, par le canevas CAVIARDÉ de la scène
// (scene.ecranDeporte) — la source brute n'entre jamais dans WebGL. Mode « incruste » : l'écran reste plein cadre, le
// studio n'est que le fond autour d'un écran réduit par le skin.
import { Z_STUDIO, Z_VIGNETTE, nomDecor } from "./dz-studiov-logique.js";
import { creerMoteur } from "./dz-studiov-moteur.js";

if (!window.__dzStudiov) {
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
    boite: "width:1240px;max-width:97vw;height:780px;max-height:95vh;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    corps: "flex:1;min-height:0;display:flex",
    gauche: "width:250px;flex:none;border-right:1px solid var(--brd-soft,var(--stroke,#222830));overflow-y:auto;padding:8px;display:flex;flex-direction:column;gap:4px",
    centre: "flex:1;min-width:0;display:flex;flex-direction:column;gap:8px;padding:10px;overflow:auto",
    groupe: "display:flex;flex-direction:column;gap:5px",
    titreG: "font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    ligne: "display:flex;align-items:center;gap:8px;flex-wrap:wrap",
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
  const delai = (p, ms) => Promise.race([p, new Promise((r) => setTimeout(() => r(null), ms))]);
  async function api(methode, url, corps) {
    const r = await fetch(url, { method: methode, headers: corps ? { "Content-Type": "application/json" } : undefined,
      body: corps ? JSON.stringify(corps) : undefined });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error((d && d.detail) || String(r.status));
    return d;
  }
  const qualite = () => { try { return localStorage.getItem("dz_studiov_qualite") === "haute" ? "haute" : "legere"; } catch (e) { return "legere"; } };
  let THREE = null;
  const moteur3d = async () => (THREE || (THREE = await import("/assets/three/three.module.min.js")));
  function chargerImage(url) {
    return new Promise((res) => {
      if (!url) return res(null);
      const im = new Image();
      im.onload = () => res(im); im.onerror = () => res(null);
      im.src = url;
    });
  }

  let liste = null;
  const details = new Map();
  async function charger() { liste = await api("GET", "/api/studiov"); return liste; }
  async function preparer(id) {
    const d = await api("GET", "/api/studiov/" + encodeURIComponent(id));
    const logo = await delai(chargerImage(`${d.contexte.logo_espace}?v=${Date.now()}`), 1500);
    const r = { decor: d.decor, contexte: d.contexte, logo };
    details.set(id, r);
    return r;
  }

  // ── pour l'enregistreur (dz-capture.js) ──
  let habit = null;
  function poser(scene, d, env) {
    const E = env || {};
    const m = creerMoteur(THREE, { largeur: scene.largeur, hauteur: scene.hauteur, decor: d.decor, contexte: d.contexte,
      logo: d.logo, qualite: qualite(), apercu: !!E.apercu });
    const plateau = d.decor.mode === "plateau" && !E.apercu;
    const ecran = plateau && typeof scene.ecranDeporte === "function" ? scene.ecranDeporte(true) : null;
    const avaitClics = plateau && scene.calques().some((c) => c.id === "clics");
    if (avaitClics) scene.retirerCalque("clics");
    let decor = d.decor;
    scene.ajouterCalque({ id: "studiov", z: plateau || E.apercu ? Z_STUDIO : 45, dessiner(ctx, s) {
      m.rendre(s.t, { ecran, camera: s.sources.camera });
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.drawImage(m.canvas, 0, 0, s.largeur, s.hauteur);
    } });
    scene.ajouterCalque({ id: "studiov-vignette", z: plateau || E.apercu ? Z_VIGNETTE : 46, dessiner(ctx, s) {
      const v = decor.ambiance.vignette;
      if (!(v > 0)) return;
      const g = ctx.createRadialGradient(s.largeur / 2, s.hauteur / 2, s.hauteur * 0.35, s.largeur / 2, s.hauteur / 2, s.largeur * 0.72);
      if (!g || typeof g.addColorStop !== "function") return;
      g.addColorStop(0, "rgba(0,0,0,0)"); g.addColorStop(1, `rgba(0,0,0,${(v * 0.85).toFixed(3)})`);
      ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.fillStyle = g; ctx.fillRect(0, 0, s.largeur, s.hauteur);
    } });
    const touche = (e) => {
      if (!(e.ctrlKey && e.altKey) || !/^Digit[1-6]$/.test(e.code)) return;
      const i = Number(e.code.slice(5)) - 1;
      if (i < decor.cameras.length) { e.preventDefault(); m.camera(i); }
    };
    if (!E.apercu) window.addEventListener("keydown", touche, true);
    return {
      decor: () => decor, cameras: () => m.cameras(), courante: () => m.courante(), camera: (i) => m.camera(i),
      maj(nd) { decor = nd.decor; m.maj(nd.decor); },
      retirer() {
        window.removeEventListener("keydown", touche, true);
        scene.retirerCalque("studiov"); scene.retirerCalque("studiov-vignette");
        if (ecran) scene.ecranDeporte(false);
        m.detruire();
      },
    };
  }
  async function habiller(scene, o) {
    let id = o && typeof o.decor === "string" ? o.decor : undefined;
    try {
      if (id === undefined) { const l = liste || await delai(charger(), 1500); id = l ? l.choisi : ""; }
      if (!id) return null;
      const [d] = await Promise.all([details.get(id) || delai(preparer(id), 2500), delai(moteur3d(), 3000)]);
      if (!d || !THREE || (scene.etat && scene.etat.sansStudio)) return null;      // arrivé trop tard : sans studio
      habit = poser(scene, d);
      return habit;
    } catch (e) { return null; }                 // un studio en panne (WebGL absent…) ne bloque jamais la capture
  }
  window.addEventListener("dz-capture:fin", () => { if (habit) { try { habit.retirer(); } catch (e) { /* scène déjà close */ } } habit = null; });

  function options(sel, l, courant) {
    sel.textContent = "";
    sel.appendChild(el("option", { value: "", texte: T("studiov.capture.aucun") }));
    const g1 = el("optgroup", { label: T("studiov.liste.livres") }), g2 = el("optgroup", { label: T("studiov.liste.espace") });
    for (const d of l.livres) g1.appendChild(el("option", { value: d.id, texte: nomDecor(d, T) }));
    for (const d of l.decors) g2.appendChild(el("option", { value: d.id, texte: d.nom }));
    sel.appendChild(g1); if (l.decors.length) sel.appendChild(g2);
    sel.value = courant || "";
  }
  function groupeCapture() {
    let charge = false;
    const sel = el("select", { style: S.champ, "data-dz-studiov-choix": true, "aria-label": T("studiov.capture.choix") });
    const note = el("div", { style: S.note, "data-dz-studiov-note": true, texte: T("studiov.capture.note") });
    const voir = el("button", { type: "button", style: S.bouton, "data-dz-studiov-apercu": true, texte: T("studiov.capture.apercu"),
      on: { click: () => ouvrirApercu({ decor: sel.value, apres: (id) => remplir(id) }) } });
    const remplir = async (id) => {
      try { const l = await charger(); options(sel, l, id === undefined ? l.choisi : id); charge = true; }
      catch (e) { charge = false; sel.textContent = ""; sel.appendChild(el("option", { value: "", texte: T("studiov.capture.aucun") })); }
    };
    remplir();
    const noeud = el("div", { style: S.groupe, "data-dz-studiov-groupe": true }, [
      el("div", { style: S.titreG, texte: T("studiov.capture.titre") }),
      el("div", { style: S.ligne }, [sel, voir]), note,
    ]);
    return { noeud, valeur: () => (charge ? sel.value : undefined) };
  }

  // ── l'aperçu des décors ──
  let apercu = null;
  function fermerApercu() {
    if (!apercu) return;
    clearInterval(apercu.minuterie);
    if (apercu.habit) apercu.habit.retirer();
    apercu.voile.remove();
    document.removeEventListener("keydown", apercu.echap, true);
    const apres = apercu.apres, id = apercu.choisi;
    apercu = null;
    if (typeof apres === "function") apres(id);
  }
  async function ouvrirApercu(o) {
    if (apercu) return;
    const O = o || {};
    const titre = el("div", { style: S.tete, texte: T("studiov.apercu.titre") });
    const gauche = el("div", { style: S.gauche, "data-dz-studiov-liste": true });
    const cadre = el("div", { style: S.apercu, "data-dz-studiov-cadre": true });
    const cams = el("div", { style: S.ligne, "data-dz-studiov-cameras": true });
    const fiche = el("div", { style: S.note, "data-dz-studiov-fiche": true });
    const erreur = el("div", { style: S.erreur, role: "alert", "data-dz-studiov-erreur": true });
    const btnChoisir = el("button", { type: "button", style: S.principal, "data-dz-studiov-choisir": true, texte: T("studiov.apercu.choisir") });
    const btnCopier = el("button", { type: "button", style: S.bouton, "data-dz-studiov-dupliquer": true, texte: T("studiov.apercu.dupliquer") });
    const btnSans = el("button", { type: "button", style: S.bouton, "data-dz-studiov-sans": true, texte: T("studiov.capture.aucun") });
    const selQ = el("select", { style: S.champ + ";flex:none;width:auto", "data-dz-studiov-qualite": true, "aria-label": T("studiov.apercu.qualite") },
      ["legere", "haute"].map((q) => el("option", { value: q, texte: T("studiov.qualite." + q) })));
    selQ.value = qualite();
    const btnFermer = el("button", { type: "button", style: S.bouton, texte: T("studiov.apercu.fermer"), on: { click: fermerApercu } });
    const boite = el("div", { style: S.boite, role: "dialog", "aria-modal": "true", "aria-label": T("studiov.apercu.titre"), "data-dz-studiov-apercu-boite": true }, [
      titre,
      el("div", { style: S.corps }, [gauche, el("div", { style: S.centre }, [cadre, cams, fiche, erreur])]),
      el("div", { style: S.pied }, [btnChoisir, btnCopier, btnSans, el("span", { style: "flex:1" }),
        el("span", { style: S.note, texte: T("studiov.apercu.qualite") }), selQ, btnFermer]),
    ]);
    const voile = el("div", { style: S.voile, "data-dz-studiov-voile": true }, [boite]);
    const echap = (e) => { if (e.key === "Escape") { e.stopPropagation(); fermerApercu(); } };
    document.addEventListener("keydown", echap, true);
    document.body.appendChild(voile);
    apercu = { voile, echap, apres: O.apres, choisi: undefined, habit: null, minuterie: null, id: null, scene: null };

    const { creerScene } = await import("./dz-capture-scene.js");
    async function montrer(id) {
      if (!apercu) return;
      erreur.textContent = "";
      try {
        const [d] = await Promise.all([details.get(id) || preparer(id), moteur3d()]);
        if (!apercu) return;
        if (apercu.habit) { apercu.habit.retirer(); apercu.habit = null; }
        clearInterval(apercu.minuterie);
        const scene = creerScene({ largeur: 1280, hauteur: 720, fps: 30, secrets: () => [] });
        scene.canvas.style.cssText = "position:absolute;inset:0;width:100%;height:100%";
        scene.canvas.setAttribute("data-dz-studiov-canvas", "");
        cadre.textContent = ""; cadre.appendChild(scene.canvas);
        apercu.habit = poser(scene, d, { apercu: true });
        apercu.scene = scene; apercu.id = id;
        apercu.minuterie = setInterval(() => scene.dessiner(), 33);
        scene.dessiner();
        cams.textContent = "";
        apercu.habit.cameras().forEach((nom, i) => cams.appendChild(el("button", { type: "button", style: S.bouton, "data-dz-studiov-camera": String(i),
          texte: `${i + 1} · ${nom}`, on: { click: () => apercu && apercu.habit.camera(i) } })));
        const dd = d.decor;
        fiche.textContent = T("studiov.apercu.fiche", { objets: dd.objets.length, lumieres: dd.lumieres.length, cameras: dd.cameras.length,
          niveau: T(dd.fabrique ? "studiov.niveau.fabrique" : "studiov.niveau.direct") });
        for (const b of gauche.querySelectorAll("[data-dz-studiov-item]")) b.style.borderColor = b.getAttribute("data-dz-studiov-item") === id ? "var(--brand,#f0b429)" : "transparent";
      } catch (e) { erreur.textContent = T("studiov.erreur.apercu", { msg: (e && e.message) || "—" }); }
    }
    async function peindreListe(courant) {
      const l = await charger();
      gauche.textContent = "";
      const section = (titreS, items) => {
        if (!items.length) return;
        gauche.appendChild(el("div", { style: S.titreG + ";padding:6px 2px 2px", texte: titreS }));
        for (const d of items) gauche.appendChild(el("button", { type: "button", style: S.item, "data-dz-studiov-item": d.id,
          on: { click: () => montrer(d.id) } }, [el("span", { texte: d.livre ? nomDecor(d, T) : d.nom }),
          el("span", { style: S.badge, texte: (l.choisi === d.id ? T("studiov.liste.choisi") + " · " : "") + T(d.fabrique ? "studiov.niveau.fabrique" : "studiov.niveau.direct") })]));
      };
      section(T("studiov.liste.livres"), l.livres);
      section(T("studiov.liste.espace"), l.decors);
      await montrer(courant || l.choisi || (l.livres[0] && l.livres[0].id));
    }
    const choisir = async (id) => {
      try { await api("PUT", "/api/studiov/choix", { decor_id: id }); apercu.choisi = id; fermerApercu(); }
      catch (e) { erreur.textContent = T("studiov.erreur.choix", { msg: (e && e.message) || "—" }); }
    };
    btnChoisir.addEventListener("click", () => apercu && apercu.id && choisir(apercu.id));
    btnSans.addEventListener("click", () => choisir(""));
    btnCopier.addEventListener("click", async () => {
      if (!apercu || !apercu.id) return;
      try { const v = await api("POST", "/api/studiov", { base: apercu.id }); await peindreListe(v.id); }
      catch (e) { erreur.textContent = T("studiov.erreur.dupliquer", { msg: (e && e.message) || "—" }); }
    });
    selQ.addEventListener("change", () => { try { localStorage.setItem("dz_studiov_qualite", selQ.value); } catch (e) { /* stockage fermé */ } if (apercu && apercu.id) montrer(apercu.id); });
    try { await peindreListe(O.decor || undefined); }
    catch (e) { erreur.textContent = T("studiov.erreur.liste", { msg: (e && e.message) || "—" }); }
  }

  window.__dzStudiov = {
    charger, groupeCapture, habiller, ouvrirApercu, fermerApercu,
    actuel: () => habit, oublier: () => { habit = null; },
  };
}
