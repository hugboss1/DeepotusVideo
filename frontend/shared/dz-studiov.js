// dz-studiov.js — SV1 + SVH (14/11/2026), le STUDIO VIRTUEL 3D côté écran : le groupe « Studio virtuel » de la boîte de
// capture, l'habillage de la scène au lancement (calque 3D sous le skin, écran du décor, caméras), l'APERÇU des
// décors (liste, rendu en direct, caméras, choix pour l'espace, duplication) et le DÉCORATEUR (lot SVH : styles,
// matières réelles, meubles et bibelots par catégorie, lumières, enseigne). Conception
// docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md.
// SOURCE : frontend/shared/dz-studiov.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-studiov.js, chargée par
// frontend/dist/index.html (`<script type="module">`, AVANT dz-capture.js). Aucun maillon de bundle. L'ATELIER (lot SVA) :
// trois vues du même décor — par ses caméras, en plan (dz-studiov-plan.js), en 3D libre — où l'on choisit d'un clic un
// meuble, un pan de mur, une lumière, une caméra ; et la bibliothèque d'objets importés (lot SVO). three.js n'est
// chargé (/assets/three, embarqué) qu'au premier décor affiché. Banc : backend/tests/test_studiov_ecran.py.
//
// API : window.__dzStudiov = {
//   charger() -> {espace, choisi, decors, livres, catalogue}        GET /api/studiov
//   groupeCapture() -> {noeud, valeur()}      le groupe de la boîte de départ ; valeur() = id | "" | undefined
//   habiller(scene, {decor}) -> habit | null  pose le studio sur une scène (3,5 s au plus ; null = sans studio) ;
//                                             decor absent = celui de l'espace
//   actuel() -> habit | null ; oublier() ; ouvrirApercu({apres, decor}) ;
//   habillage() -> le catalogue du décorateur (GET /api/studiov/habillage) }
// Un habit : {decor(), cameras(), camera(i), courante(), retirer()}. Pendant une capture, Ctrl+Alt+1…6 change de caméra.
// Mode « plateau » : l'écran partagé quitte l'image et va sur l'écran du décor, par le canevas CAVIARDÉ de la scène
// (scene.ecranDeporte) — la source brute n'entre jamais dans WebGL. Mode « incruste » : l'écran reste plein cadre, le
// studio n'est que le fond autour d'un écran réduit par le skin.
import { Z_STUDIO, Z_VIGNETTE, nomDecor, palette, couleur, usageDe, poserMatiere, appliquerAmbiance, appliquerStyle,
  objetNeuf, PANS, clePan, cleObjet, nettoyerMatieres, cameraNeuve, lumiereNeuve } from "./dz-studiov-logique.js";
import { creerPlan } from "./dz-studiov-plan.js";
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
    boite: "width:1500px;max-width:98vw;height:820px;max-height:96vh;display:flex;flex-direction:column;border-radius:0;background:var(--srf-panel,var(--bg-panel-2,#13171c));border:1px solid var(--brd-hard,var(--stroke-strong,#2a3138));color:var(--txt-hi,var(--ink-strong,#e6e9ee));box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,var(--stroke,#222830));font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,var(--ink-muted,#9aa4ae))",
    corps: "flex:1;min-height:0;display:flex",
    gauche: "width:250px;flex:none;border-right:1px solid var(--brd-soft,var(--stroke,#222830));overflow-y:auto;padding:8px;display:flex;flex-direction:column;gap:4px",
    centre: "flex:1;min-width:0;display:flex;flex-direction:column;gap:8px;padding:10px;overflow:auto",
    droite: "width:336px;flex:none;border-left:1px solid var(--brd-soft,var(--stroke,#222830));overflow-y:auto;padding:8px 10px;display:flex;flex-direction:column;gap:6px",
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

  // ── SVH : le DÉCORATEUR (panneau « Décorer » de l'aperçu) — habiller un décor de l'espace comme on meuble une pièce :
  // un style complet, une matière par surface, des meubles et des bibelots par catégorie, les lumières, l'enseigne.
  // Chaque geste modifie la recette en mémoire, la montre aussitôt, puis l'enregistre (le serveur reste seul juge). ──
  let hab = null;
  async function habillage(force) {
    if (!hab || force) {
      const h = await api("GET", "/api/studiov/habillage");
      // l'index est gardé EN PLACE : un moteur déjà ouvert voit aussitôt une matière neuve (cuisson de Blender)
      h.index = hab ? hab.index : {};
      for (const k of Object.keys(h.index)) delete h.index[k];
      for (const t of h.textures) h.index[t.ref] = t;
      h.indexObjets = hab ? hab.indexObjets : {};
      for (const k of Object.keys(h.indexObjets)) delete h.indexObjets[k];
      for (const v of h.objets || []) h.indexObjets[v.ref] = v;
      h.indexImages = hab ? hab.indexImages : {};
      for (const k of Object.keys(h.indexImages)) delete h.indexImages[k];
      for (const v of h.images || []) h.indexImages[v.ref] = v;
      hab = h;
    }
    return hab;
  }
  // le chargeur de modèles GLB (three.js embarqué, servi avec ses imports réécrits) : demandé au premier objet importé
  // (lot SVC) avec le décodeur Meshopt embarqué : les modèles du catalogue de produits réels sont compressés ainsi
  const porteGLB = { classe: null, meshopt: null };
  async function chargeurGLB() {
    if (!porteGLB.classe) { try { porteGLB.classe = (await import("/api/studiov/three/GLTFLoader.js")).GLTFLoader; } catch (e) { /* sans chargeur : l'objet reste un gabarit */ } }
    if (!porteGLB.meshopt) { try { porteGLB.meshopt = (await import("/assets/three/addons/libs/meshopt_decoder.module.js")).MeshoptDecoder; } catch (e) { /* sans décodeur : un modèle compressé reste un gabarit */ } }
    return porteGLB.classe;
  }
  const nomTexture = (t) => (typeof window.dzLang === "function" && window.dzLang() === "en" ? t.nom_en : t.nom);
  const hexDe = (ref, pal) => couleur(ref, pal, "#808890");

  function decorateur(hote, ctx) {
    // ctx : {decor(), contexte(), modifier(nd), personnaliser(), livre()}
    let onglet = "style", surface = "sol", famille = "", familleObjets = "tables", choisi = -1, lum = -1, cam = 0;
    const pal = () => palette(ctx.contexte());
    const titre = (cle) => el("div", { style: S.titreG + ";margin-top:6px", texte: T(cle) });
    const bouton = (texte, clic, plus) => el("button", { type: "button", style: S.bouton + ";padding:3px 8px;font-size:12px" + (plus || ""), texte, on: { click: clic } });
    function curseur(cle, valeur, min, max, pas, change) {
      const sortie = el("span", { style: S.note + ";width:38px;text-align:right", texte: String(Math.round(valeur * 100) / 100) });
      const c = el("input", { type: "range", min, max, step: pas, value: valeur, style: "flex:1;min-width:0", "aria-label": T(cle),
        on: { input: () => { sortie.textContent = String(Math.round(Number(c.value) * 100) / 100); change(Number(c.value)); } } });
      return el("label", { style: S.ligne + ";flex-wrap:nowrap;gap:6px" }, [el("span", { style: S.note + ";width:84px;flex:none", texte: T(cle) }), c, sortie]);
    }
    // une couleur : la pastille, puis les deux couleurs du kit de l'espace (elles suivent la marque)
    function champCouleur(valeur, change) {
      const p = pal(), c = el("input", { type: "color", value: hexDe(valeur, p), style: "width:34px;height:24px;padding:0;border:1px solid var(--brd-hard,#2a3138);background:none;border-radius:0",
        "aria-label": T("studiov.deco.couleur"), on: { input: () => change(c.value) } });
      const role = (r) => el("button", { type: "button", title: T("studiov.deco.role." + r), "aria-label": T("studiov.deco.role." + r),
        style: `width:24px;height:24px;border-radius:0;cursor:pointer;background:${p[r]};border:${valeur === r ? "2px solid #fff" : "1px solid var(--brd-hard,#2a3138)"}`,
        on: { click: () => change(r) } });
      return el("span", { style: "display:inline-flex;gap:4px;align-items:center" }, [c, role("principale"), role("accent")]);
    }
    function liste(valeur, options, change, etiquette) {
      const s = el("select", { style: S.champ, "aria-label": etiquette || "" }, options.map(([v, t]) => el("option", { value: v, texte: t })));
      s.value = valeur; s.addEventListener("change", () => change(s.value));
      return s;
    }
    const pastille = (hex) => el("span", { style: `display:inline-block;width:14px;height:14px;background:${hex};border:1px solid rgba(255,255,255,.25)` });
    const copie = (x) => JSON.parse(JSON.stringify(x));

    // ── Style : tout le décor d'un geste ──
    function panneauStyle(d) {
      const p = pal(), noeud = el("div", { style: S.groupe });
      noeud.appendChild(el("div", { style: S.note, texte: T("studiov.deco.style.note") }));
      const grille = el("div", { style: "display:grid;grid-template-columns:1fr 1fr;gap:5px" });
      for (const st of hab.styles) {
        const teinte = (u) => { const m = st.matieres[u] || {}, t = m.texture && hab.index[m.texture]; return m.teinte || !t ? hexDe(m.couleur, p) : (t.moyenne || "#808890"); };
        const A = hab.ambiances.find((a) => a.id === st.ambiance) || { neons: [] };
        grille.appendChild(el("button", { type: "button", style: S.item + ";border-color:var(--brd-soft,#222830)", "data-dz-studiov-style": st.id,
          on: { click: () => ctx.modifier(appliquerStyle(ctx.decor(), st, hab.ambiances, hab.catalogue.types_lumineux)) } }, [
          el("span", { texte: T("studiov.style." + st.id) }),
          el("span", { style: "display:flex;gap:3px" }, [pastille(teinte("mur")), pastille(teinte("sol")), pastille(teinte("bois"))].concat(A.neons.slice(0, 2).map((c) => pastille(hexDe(c, p))))),
        ]));
      }
      noeud.appendChild(grille);
      return noeud;
    }

    // ── Matières : une surface, puis une matière du catalogue ou une finition ──
    // ce qu'on peut habiller : les pans de la pièce (chacun le sien), l'objet choisi (sa matière, son piètement), puis
    // les matières que la recette nomme déjà
    const estPan = (s) => PANS.indexOf(s) >= 0;
    const objetDe = (s) => { const m = /^objet:(\d+):([12])$/.exec(s); return m ? [Number(m[1]), Number(m[2])] : null; };
    function surfaces(d) {
      const P = d.piece, out = (P.ouvert ? ["sol", "fond"] : PANS).map((p) => [p, P[p] || P.mur]), vues = new Set(out.map((x) => x[1]).concat([P.mur]));
      if (d.objets[choisi]) { out.unshift(["objet:" + choisi + ":2", d.objets[choisi].matiere2]); out.unshift(["objet:" + choisi + ":1", d.objets[choisi].matiere]); }
      for (const cle of Object.keys(d.matieres)) if (!vues.has(cle) && !(d.matieres[cle].emission > 0)) out.push([cle, cle]);
      return out;
    }
    // la clé à modifier : un pan ou un objet se DÉTACHE de ce qui partageait sa matière au premier changement
    function cleDe(d, s) {
      const ob = objetDe(s);
      return estPan(s) ? clePan(d, s) : ob ? cleObjet(d, ob[0], ob[1]) : s;
    }
    // « Depuis Blender » : cuire une matière d'un fichier .blend ; elle entre dans la Forge et se pose aussitôt
    let blend = "", matieresBlend = null, occupe = false, messageBlender = "";
    function blocBlender(poser) {
      const bloc = el("div", { style: S.groupe + ";border:1px solid var(--brd-soft,#222830);padding:6px", "data-dz-studiov-blender": true });
      bloc.appendChild(el("div", { style: S.titreG, texte: T("studiov.blender.titre") }));
      bloc.appendChild(el("div", { style: S.note, texte: T("studiov.blender.note") }));
      const chemin = el("input", { type: "text", value: blend, style: S.champ, placeholder: T("studiov.blender.chemin"), "aria-label": T("studiov.blender.chemin"), "data-dz-studiov-blend": true });
      chemin.addEventListener("input", () => { blend = chemin.value; matieresBlend = null; });
      const etat = el("div", { style: S.note, role: "status", texte: messageBlender });
      const faire = async (action) => { if (occupe) return; occupe = true; messageBlender = T("studiov.blender.patience"); etat.textContent = messageBlender;
        try { await action(); } catch (e) { messageBlender = (e && e.message) || "—"; } occupe = false; peindre(); };
      bloc.appendChild(el("div", { style: S.ligne + ";flex-wrap:nowrap" }, [chemin, bouton(T("studiov.blender.lister"), () => faire(async () => {
        const r = await api("POST", "/api/studiov/blender/matieres", { blend }); matieresBlend = r.matieres;
        messageBlender = T("studiov.blender.trouvees", { n: r.matieres.length });
      }))]));
      if (matieresBlend && matieresBlend.length) {
        const choix = liste(matieresBlend[0], matieresBlend.map((n) => [n, n]), () => {}, T("studiov.blender.matiere"));
        bloc.appendChild(el("div", { style: S.ligne + ";flex-wrap:nowrap" }, [choix, bouton(T("studiov.blender.cuire"), () => faire(async () => {
          const r = await api("POST", "/api/studiov/blender/cuire", { blend, matiere: choix.value });
          await habillage(true);
          messageBlender = T("studiov.blender.faite", { nom: r.materials[0].nom });
          poser({ texture: r.materials[0].ref, teinte: false });
        }))]));
      }
      bloc.appendChild(etat);
      return bloc;
    }
    function panneauMatieres(d) {
      const noeud = el("div", { style: S.groupe }), liens = surfaces(d);
      if (!liens.some(([s]) => s === surface)) surface = "sol";
      const cle = liens.find(([s]) => s === surface)[1], ob = objetDe(surface);
      const m = d.matieres[cle] || { couleur: (ob && d.objets[ob[0]].couleur) || "#808890", rugosite: 0.6, metal: 0, echelle: 1, texture: "", teinte: false };
      const usage = cle && d.matieres[cle] ? usageDe(d, cle) : "autre";
      const nomSurface = (s, k) => (estPan(s) ? T("studiov.surface." + s) : objetDe(s) ? `${T("studiov.objet." + d.objets[objetDe(s)[0]].type)} · ${objetDe(s)[1] === 2 ? T("studiov.deco.matiere2") : T("studiov.deco.matiere")}`
        : `${T("studiov.usage." + usageDe(d, k))} · ${k}`);
      noeud.appendChild(liste(surface, liens.map(([s, k]) => [s, nomSurface(s, k)]), (v) => { surface = v; famille = ""; if (estPan(v)) ctx.choisir({ genre: "surface", pan: v }); else peindre(); }, T("studiov.deco.surface")));
      const poser = (spec) => { const nd = copie(ctx.decor()), k = cleDe(nd, surface); ctx.modifier(nettoyerMatieres(poserMatiere(nd, k, spec))); };
      const regler = (champ, v) => { const nd = copie(ctx.decor()), k = cleDe(nd, surface); nd.matieres[k][champ] = v; ctx.modifier(nd, true); };
      // le catalogue : d'abord ce qui convient à la surface, puis par famille
      const familles = [["", T("studiov.deco.conseillees")]].concat(hab.familles_texture.map((f) => [f.id, typeof window.dzLang === "function" && window.dzLang() === "en" ? f.nom_en : f.nom]));
      noeud.appendChild(liste(famille, familles, (v) => { famille = v; peindre(); }, T("studiov.deco.famille")));
      const montrees = hab.textures.filter((t) => (famille ? t.famille === famille : usage === "autre" || t.usages.indexOf(usage) >= 0));
      const grille = el("div", { style: "display:grid;grid-template-columns:repeat(5,1fr);gap:4px;max-height:236px;overflow-y:auto", "data-dz-studiov-textures": true });
      for (const t of montrees) {
        const im = el("img", { src: t.vignette, alt: nomTexture(t), loading: "lazy", width: 52, height: 52, style: "display:block;width:100%;aspect-ratio:1;object-fit:cover" });
        grille.appendChild(el("button", { type: "button", title: nomTexture(t), "aria-label": nomTexture(t), "data-dz-studiov-texture": t.ref,
          style: `padding:0;border-radius:0;cursor:pointer;background:#000;border:2px solid ${m.texture === t.ref ? "var(--brand,#f0b429)" : "transparent"}`,
          on: { click: () => poser({ texture: t.ref, teinte: false }) } }, [im]));
      }
      if (!montrees.length) grille.appendChild(el("div", { style: S.note + ";grid-column:1/-1", texte: famille === "forge" ? T("studiov.deco.forge.vide") : T("studiov.deco.aucune") }));
      noeud.appendChild(grille);
      if (famille === "forge") noeud.appendChild(blocBlender(poser));
      const actuelle = m.texture && hab.index[m.texture];
      noeud.appendChild(el("div", { style: S.note, "data-dz-studiov-matiere": true, texte: actuelle ? nomTexture(actuelle) : T("studiov.deco.sans.texture") }));
      // les finitions sans image
      noeud.appendChild(titre("studiov.deco.finitions"));
      const fin = el("div", { style: "display:flex;flex-wrap:wrap;gap:4px" });
      for (const f of hab.finitions) if (!f.usages.length || f.usages.indexOf(usage) >= 0 || usage === "autre") {
        fin.appendChild(el("button", { type: "button", title: T("studiov.finition." + f.id), "aria-label": T("studiov.finition." + f.id), "data-dz-studiov-finition": f.id,
          style: `width:26px;height:26px;border-radius:0;cursor:pointer;border:1px solid var(--brd-hard,#2a3138);background:${f.metal >= 0.8 ? `linear-gradient(135deg,${hexDe(f.couleur, pal())},#fff 45%,${hexDe(f.couleur, pal())} 60%)` : hexDe(f.couleur, pal())}`,
          on: { click: () => poser({ texture: "", couleur: f.couleur, rugosite: f.rugosite, metal: f.metal, motif: f.motif }) } }));
      }
      noeud.appendChild(fin);
      // les réglages de la matière posée
      noeud.appendChild(titre("studiov.deco.reglages"));
      const teinter = el("input", { type: "checkbox", "data-dz-studiov-teinter": true });
      teinter.checked = !!m.teinte; teinter.disabled = !m.texture;
      teinter.addEventListener("change", () => regler("teinte", teinter.checked));
      noeud.appendChild(el("div", { style: S.ligne }, [champCouleur(m.couleur, (v) => { const nd = copie(ctx.decor()), k = cleDe(nd, surface); nd.matieres[k].couleur = v; if (nd.matieres[k].texture) nd.matieres[k].teinte = true; ctx.modifier(nd, true); teinter.checked = !!nd.matieres[k].teinte; }),
        el("label", { style: S.note + ";display:inline-flex;gap:4px;align-items:center" }, [teinter, el("span", { texte: T("studiov.deco.teinter") })])]));
      noeud.appendChild(curseur("studiov.deco.echelle", m.echelle, 0.25, 4, 0.05, (v) => regler("echelle", v)));
      noeud.appendChild(curseur("studiov.deco.rugosite", m.rugosite, 0.05, 1, 0.01, (v) => regler("rugosite", v)));
      noeud.appendChild(curseur("studiov.deco.metal", m.metal, 0, 1, 0.01, (v) => regler("metal", v)));
      return noeud;
    }

    // ── Objets : par catégorie ; l'objet choisi se place, se tourne, s'habille ──
    function panneauObjets(d) {
      const noeud = el("div", { style: S.groupe }), C = hab.catalogue, P = d.piece;
      noeud.appendChild(liste(familleObjets, Object.keys(C.familles).filter((f) => f !== "importes" && f !== "images").map((f) => [f, T("studiov.famille." + f)]), (v) => { familleObjets = v; peindre(); }, T("studiov.deco.categorie")));
      const grille = el("div", { style: "display:grid;grid-template-columns:1fr 1fr;gap:4px", "data-dz-studiov-objets": true });
      for (const type of C.familles[familleObjets] || []) {
        grille.appendChild(bouton(T("studiov.objet." + type), () => {
          const nd = copie(ctx.decor());
          if (nd.objets.length >= 120) return;
          nd.objets.push(objetNeuf(nd, type)); ctx.modifier(nd, true); ctx.choisir({ genre: "objet", index: nd.objets.length - 1 });
        }, ";text-align:left"));
      }
      noeud.appendChild(grille);
      noeud.appendChild(titre("studiov.deco.places"));
      if (choisi >= d.objets.length) choisi = d.objets.length - 1;
      const nomObjet = (o) => (o.type === "modele" && hab.indexObjets[o.ref] ? hab.indexObjets[o.ref].nom : T("studiov.objet." + o.type));
      const options = [["-1", T("studiov.deco.choisir.objet", { n: d.objets.length })]].concat(d.objets.map((o, i) => [String(i), `${i + 1} · ${nomObjet(o)}`]));
      noeud.appendChild(liste(String(choisi), options, (v) => ctx.choisir(Number(v) >= 0 ? { genre: "objet", index: Number(v) } : null), T("studiov.deco.places")));
      const o = d.objets[choisi];
      if (!o) return noeud;
      const regler = (champ, v, leger) => { const nd = copie(ctx.decor()); if (!nd.objets[choisi]) return; if (v === null) nd.objets[choisi][champ] = null; else nd.objets[choisi][champ] = v; ctx.modifier(nd, leger); };
      noeud.appendChild(curseur("studiov.deco.x", o.x, -P.l / 2, P.l / 2, 0.01, (v) => regler("x", v, true)));
      noeud.appendChild(curseur("studiov.deco.z", o.z, -P.p / 2, P.p / 2 + 2, 0.01, (v) => regler("z", v, true)));
      noeud.appendChild(curseur("studiov.deco.y", o.y, 0, P.h, 0.01, (v) => regler("y", v, true)));
      noeud.appendChild(curseur("studiov.deco.ry", o.ry, -180, 180, 1, (v) => regler("ry", v, true)));
      noeud.appendChild(curseur("studiov.deco.taille", o.e, o.type === "modele" ? 0.1 : 0.3, o.type === "modele" ? 6 : 3, 0.01, (v) => regler("e", v, true)));
      noeud.appendChild(bouton(T("studiov.deco.habiller"), () => { surface = "objet:" + choisi + ":1"; famille = ""; onglet = "matieres"; peindre(); }));
      const cles = [["", T("studiov.deco.sans.matiere")]].concat(Object.keys(d.matieres).map((k) => [k, `${T("studiov.usage." + usageDe(d, k))} · ${k}`]));
      noeud.appendChild(el("label", { style: S.ligne + ";flex-wrap:nowrap" }, [el("span", { style: S.note + ";width:84px;flex:none", texte: T("studiov.deco.matiere") }),
        liste(o.matiere || "", cles, (v) => { regler("matiere", v || null); peindre(); })]));
      noeud.appendChild(el("label", { style: S.ligne + ";flex-wrap:nowrap" }, [el("span", { style: S.note + ";width:84px;flex:none", texte: T("studiov.deco.matiere2") }),
        liste(o.matiere2 || "", cles, (v) => { regler("matiere2", v || null); peindre(); })]));
      noeud.appendChild(el("div", { style: S.ligne }, [el("span", { style: S.note + ";width:84px", texte: T("studiov.deco.couleur") }),
        champCouleur(o.couleur || "#808890", (v) => regler("couleur", v, true)), bouton(T("studiov.deco.sans.couleur"), () => { regler("couleur", null); peindre(); })]));
      if (C.types_texte.indexOf(o.type) >= 0) {
        const mot = el("input", { type: "text", maxlength: 24, value: o.texte || "", style: S.champ, "data-dz-studiov-mot": true, placeholder: T("studiov.deco.mot"), "aria-label": T("studiov.deco.mot") });
        mot.addEventListener("input", () => regler("texte", mot.value, true));
        noeud.appendChild(el("div", { style: S.ligne + ";flex-wrap:nowrap" }, [mot, liste(o.police || "Inter", C.polices.map((p) => [p, p]), (v) => regler("police", v), T("studiov.deco.police"))]));
      }
      noeud.appendChild(el("div", { style: S.ligne }, [
        bouton(T("studiov.deco.dupliquer"), () => { const nd = copie(ctx.decor()); if (nd.objets.length >= 120) return; const c = copie(nd.objets[choisi]); c.x = Math.min(P.l / 2, c.x + 0.3); nd.objets.push(c); ctx.modifier(nd, true); ctx.choisir({ genre: "objet", index: nd.objets.length - 1 }); }),
        bouton(T("studiov.deco.retirer"), () => { const nd = copie(ctx.decor()); nd.objets.splice(choisi, 1); ctx.modifier(nettoyerMatieres(nd), true); ctx.choisir(null); }),
      ]));
      return noeud;
    }

    // ── Lumières : une ambiance d'un geste, puis chaque source ──
    function panneauLumieres(d) {
      const p = pal(), noeud = el("div", { style: S.groupe });
      const grille = el("div", { style: "display:grid;grid-template-columns:1fr 1fr;gap:5px" });
      for (const A of hab.ambiances) {
        grille.appendChild(el("button", { type: "button", style: S.item + ";border-color:var(--brd-soft,#222830)", "data-dz-studiov-ambiance": A.id,
          on: { click: () => { ctx.modifier(appliquerAmbiance(ctx.decor(), A, hab.catalogue.types_lumineux)); peindre(); } } }, [
          el("span", { texte: T("studiov.ambiance." + A.id) }),
          el("span", { style: "display:flex;gap:3px" }, [A.cle, A.contre].concat(A.neons).map((c) => pastille(hexDe(c, p)))),
        ]));
      }
      noeud.appendChild(grille);
      noeud.appendChild(titre("studiov.deco.sources"));
      d.lumieres.forEach((l, i) => {
        const regler = (champ, v) => { const nd = copie(ctx.decor()); if (!nd.lumieres[i]) return; nd.lumieres[i][champ] = v; ctx.modifier(nd, true); };
        const force = el("input", { type: "range", min: 0, max: l.type === "ambiance" ? 2 : 8, step: 0.05, value: l.intensite, style: "flex:1;min-width:0", "aria-label": T("studiov.deco.intensite") });
        force.addEventListener("input", () => regler("intensite", Number(force.value)));
        const retirable = l.type === "neon" || d.lumieres.filter((x) => x.type === l.type).length > 1;
        noeud.appendChild(el("div", { style: S.ligne + ";flex-wrap:nowrap;gap:6px" }, [
          l.type === "ambiance" ? el("span", { style: S.note + ";width:62px;flex:none", texte: T("studiov.lumiere." + l.type) })
            : el("button", { type: "button", "data-dz-studiov-lumiere": String(i), texte: T("studiov.lumiere." + l.type), on: { click: () => ctx.choisir({ genre: "lumiere", index: i }) },
              style: S.bouton + `;width:62px;flex:none;padding:2px 4px;font-size:11.5px;${lum === i ? "border-color:var(--brand,#f0b429);color:var(--brand,#f0b429)" : ""}` }),
          champCouleur(l.couleur, (v) => regler("couleur", v)), force,
          retirable ? bouton("×", () => { const nd = copie(ctx.decor()); nd.lumieres.splice(i, 1); ctx.modifier(nd, true); ctx.choisir(null); }, ";padding:1px 7px") : null]));
        if (lum === i && l.type !== "ambiance") {                // la lumière choisie : sa place dans la pièce (elle se glisse aussi sur le plan)
          const P = d.piece;
          noeud.appendChild(curseur("studiov.deco.x", l.x, -P.l / 2 - 3, P.l / 2 + 3, 0.01, (v) => regler("x", v)));
          noeud.appendChild(curseur("studiov.deco.y", l.y, 0.02, P.h + 0.5, 0.01, (v) => regler("y", v)));
          noeud.appendChild(curseur("studiov.deco.z", l.z, -P.p / 2 - 1, P.p / 2 + 6, 0.01, (v) => regler("z", v)));
          if (l.type === "neon") { noeud.appendChild(curseur("studiov.deco.longueur", l.l, 0.2, 8, 0.05, (v) => regler("l", v))); noeud.appendChild(curseur("studiov.deco.ry", l.ry, -180, 180, 1, (v) => regler("ry", v))); }
        }
      });
      const plus = (type) => () => { const nd = copie(ctx.decor()); if (nd.lumieres.length >= 16) return; nd.lumieres.push(lumiereNeuve(nd, type)); ctx.modifier(nd, true); ctx.choisir({ genre: "lumiere", index: nd.lumieres.length - 1 }); };
      noeud.appendChild(el("div", { style: S.ligne }, [bouton(T("studiov.deco.projecteur.plus"), plus("appoint")), bouton(T("studiov.deco.contre.plus"), plus("contre")),
        bouton(T("studiov.deco.neon.plus"), plus("neon"))]));
      const A = d.ambiance, regA = (champ, v) => { const nd = copie(ctx.decor()); nd.ambiance[champ] = v; ctx.modifier(nd, true); };
      noeud.appendChild(curseur("studiov.deco.exposition", A.exposition, 0.4, 2, 0.01, (v) => regA("exposition", v)));
      noeud.appendChild(curseur("studiov.deco.brouillard", A.brouillard, 0, 0.15, 0.005, (v) => regA("brouillard", v)));
      noeud.appendChild(curseur("studiov.deco.vignette", A.vignette, 0, 1, 0.01, (v) => regA("vignette", v)));
      return noeud;
    }

    // ── Enseigne : le logo de l'espace ou un mot, en néon, rétroéclairé, en caisson… ──
    function panneauEnseigne(d) {
      const noeud = el("div", { style: S.groupe }), E = d.enseigne, C = hab.catalogue, P = d.piece;
      const regler = (champ, v, leger) => { const nd = copie(ctx.decor()); nd.enseigne[champ] = v; ctx.modifier(nd, leger); };
      const actif = el("input", { type: "checkbox", "data-dz-studiov-enseigne": true });
      actif.checked = !!E.actif; actif.addEventListener("change", () => regler("actif", actif.checked));
      noeud.appendChild(el("label", { style: S.ligne }, [actif, el("span", { texte: T("studiov.deco.enseigne.active") })]));
      noeud.appendChild(liste(E.source, [["espace", T("studiov.deco.enseigne.logo")], ["texte", T("studiov.deco.enseigne.texte")]].concat(E.image ? [["image", T("studiov.deco.enseigne.image")]] : []), (v) => { regler("source", v); peindre(); }, T("studiov.deco.enseigne.source")));
      if (E.source === "texte") {
        const mot = el("input", { type: "text", maxlength: 40, value: E.texte || "", style: S.champ, placeholder: T("studiov.deco.mot"), "aria-label": T("studiov.deco.mot") });
        mot.addEventListener("input", () => regler("texte", mot.value, true));
        noeud.appendChild(el("div", { style: S.ligne + ";flex-wrap:nowrap" }, [mot, liste(E.police, C.polices.map((p) => [p, p]), (v) => regler("police", v), T("studiov.deco.police"))]));
      }
      noeud.appendChild(liste(E.style, C.styles_enseigne.map((s) => [s, T("studiov.enseigne." + s)]), (v) => regler("style", v), T("studiov.deco.enseigne.style")));
      noeud.appendChild(el("div", { style: S.ligne }, [el("span", { style: S.note + ";width:84px", texte: T("studiov.deco.couleur") }), champCouleur(E.couleur, (v) => { regler("couleur", v); peindre(); })]));
      noeud.appendChild(curseur("studiov.deco.taille", E.l, 0.3, 4, 0.01, (v) => regler("l", v, true)));
      noeud.appendChild(curseur("studiov.deco.x", E.x, -P.l / 2, P.l / 2, 0.01, (v) => regler("x", v, true)));
      noeud.appendChild(curseur("studiov.deco.y", E.y, 0.2, P.h, 0.01, (v) => regler("y", v, true)));
      noeud.appendChild(curseur("studiov.deco.z", E.z, -P.p / 2, P.p / 2, 0.01, (v) => regler("z", v, true)));
      noeud.appendChild(curseur("studiov.deco.ry", E.ry, -180, 180, 1, (v) => regler("ry", v, true)));
      return noeud;
    }

    // ── Caméras : hauteur, focale, visée, mouvement ; le présentateur ──
    function panneauCameras(d) {
      const noeud = el("div", { style: S.groupe }), P = d.piece;
      if (cam >= d.cameras.length) cam = 0;
      noeud.appendChild(el("div", { style: "display:flex;flex-wrap:wrap;gap:4px" }, d.cameras.map((c, i) => el("button", { type: "button", "data-dz-studiov-cam": String(i), texte: `${i + 1} · ${c.nom}`,
        style: S.bouton + `;padding:3px 8px;font-size:12px;${cam === i ? "border-color:var(--brand,#f0b429);color:var(--brand,#f0b429)" : ""}`, on: { click: () => ctx.choisir({ genre: "camera", index: i }) } }))));
      const c = d.cameras[cam];
      const regler = (champ, v, leger) => { const nd = copie(ctx.decor()); if (!nd.cameras[cam]) return; nd.cameras[cam][champ] = v; ctx.modifier(nd, leger !== false); };
      const viser2 = (k, v) => { const nd = copie(ctx.decor()); if (!nd.cameras[cam]) return; nd.cameras[cam].vers[k] = v; ctx.modifier(nd, true); };
      const nom = el("input", { type: "text", maxlength: 24, value: c.nom, style: S.champ, "aria-label": T("studiov.cam.nom") });
      nom.addEventListener("change", () => regler("nom", nom.value, false));
      noeud.appendChild(nom);
      noeud.appendChild(curseur("studiov.cam.hauteur", c.y, 0.3, Math.min(8, P.h + 1), 0.01, (v) => regler("y", v)));
      noeud.appendChild(curseur("studiov.cam.focale", c.focale, 14, 135, 1, (v) => regler("focale", v)));
      noeud.appendChild(curseur("studiov.deco.x", c.x, -P.l / 2 - 3, P.l / 2 + 3, 0.01, (v) => regler("x", v)));
      noeud.appendChild(curseur("studiov.deco.z", c.z, -P.p / 2, P.p / 2 + 6, 0.01, (v) => regler("z", v)));
      noeud.appendChild(titre("studiov.cam.visee"));
      noeud.appendChild(curseur("studiov.deco.x", c.vers[0], -P.l / 2, P.l / 2, 0.01, (v) => viser2(0, v)));
      noeud.appendChild(curseur("studiov.deco.y", c.vers[1], 0, P.h, 0.01, (v) => viser2(1, v)));
      noeud.appendChild(curseur("studiov.deco.z", c.vers[2], -P.p / 2, P.p / 2 + 2, 0.01, (v) => viser2(2, v)));
      noeud.appendChild(el("label", { style: S.ligne + ";flex-wrap:nowrap" }, [el("span", { style: S.note + ";width:84px;flex:none", texte: T("studiov.cam.mouvement") }),
        liste(c.mouvement, hab.catalogue.mouvements.map((m) => [m, T("studiov.mouvement." + m)]), (v) => regler("mouvement", v, false))]));
      if (c.mouvement !== "fixe") noeud.appendChild(curseur("studiov.cam.amplitude", c.amplitude, 0, 1, 0.01, (v) => regler("amplitude", v)));
      const M = ctx.moteur();
      noeud.appendChild(el("div", { style: S.ligne }, [
        bouton(T("studiov.cam.ajouter"), () => { const nd = copie(ctx.decor()); if (nd.cameras.length >= 6) return; nd.cameras.push(cameraNeuve(nd)); ctx.modifier(nd, true); ctx.choisir({ genre: "camera", index: nd.cameras.length - 1 }); }),
        d.cameras.length > 1 ? bouton(T("studiov.deco.retirer"), () => { const nd = copie(ctx.decor()); nd.cameras.splice(cam, 1); cam = 0; ctx.modifier(nd, true); ctx.choisir({ genre: "camera", index: 0 }); }) : null,
        M && M.libre() ? bouton(T("studiov.cam.reprendre"), () => { const p = M.poseLibre(), nd = copie(ctx.decor()); if (!p || !nd.cameras[cam]) return; Object.assign(nd.cameras[cam], p); ctx.modifier(nd); }) : null]));
      // le présentateur : sa place et sa taille (il se glisse aussi sur le plan)
      noeud.appendChild(titre("studiov.plan.presentateur"));
      const R = d.presentateur, regR = (champ, v, leger) => { const nd = copie(ctx.decor()); nd.presentateur[champ] = v; ctx.modifier(nd, leger !== false); };
      noeud.appendChild(curseur("studiov.deco.x", R.x, -P.l / 2, P.l / 2, 0.01, (v) => regR("x", v)));
      noeud.appendChild(curseur("studiov.deco.z", R.z, -P.p / 2, P.p / 2, 0.01, (v) => regR("z", v)));
      noeud.appendChild(curseur("studiov.cam.taille", R.h, 0.6, 2.4, 0.01, (v) => regR("h", v)));
      const assis = el("input", { type: "checkbox" }); assis.checked = !!R.assis; assis.addEventListener("change", () => regR("assis", assis.checked, false));
      noeud.appendChild(el("label", { style: S.ligne }, [assis, el("span", { texte: T("studiov.cam.assis") })]));
      return noeud;
    }

    // ── Mes objets : la bibliothèque de modèles importés (fichier GLB, Blender), leurs droits, les crédits du décor ──
    let etatImport = "", blendObjets = "", objetsBlend = null, occupeObjets = false;
    const cleLic = (l) => String(l).toLowerCase().replace(/-/g, "_");          // CC-BY -> cc_by (clé du dictionnaire)
    function panneauBiblio(d) {
      const noeud = el("div", { style: S.groupe }), etat = el("div", { style: S.note, role: "status", texte: etatImport });
      noeud.appendChild(el("div", { style: S.note, texte: T("studiov.biblio.note") }));
      const faire = async (action) => { if (occupeObjets) return; occupeObjets = true; etatImport = T("studiov.biblio.patience"); etat.textContent = etatImport;
        try { await action(); } catch (e) { etatImport = (e && e.message) || "—"; } occupeObjets = false; peindre(); };
      for (const v of hab.objets || []) {
        const droits = [v.droits.video === null ? T("studiov.droit.verifier") : null, v.droits.credit ? T("studiov.droit.credit") : null, v.droits.export ? null : T("studiov.droit.sansexport"), v.lourd ? T("studiov.droit.lourd") : null].filter(Boolean);
        noeud.appendChild(el("div", { style: S.ligne + ";flex-wrap:nowrap;gap:6px;border-bottom:1px solid var(--brd-soft,#222830);padding-bottom:4px", "data-dz-studiov-objet": v.ref }, [
          el("div", { style: "flex:1;min-width:0;display:flex;flex-direction:column" }, [el("span", { texte: v.nom, style: "overflow:hidden;text-overflow:ellipsis;white-space:nowrap" }),
            el("span", { style: S.badge, texte: [T("studiov.licence." + cleLic(v.licence)), v.auteur].concat(droits).filter(Boolean).join(" · ") })]),
          bouton(T("studiov.biblio.poser"), () => faire(async () => { await chargeurGLB(); const nd = copie(ctx.decor()); if (nd.objets.length >= 120) return;
            nd.objets.push(objetNeuf(nd, "modele", v.ref, v.pose)); etatImport = ""; ctx.modifier(nd, true); ctx.choisir({ genre: "objet", index: nd.objets.length - 1 }); })),
          bouton("×", () => faire(async () => { await api("DELETE", "/api/studiov/objets/" + v.id); await habillage(true); etatImport = ""; }), ";padding:1px 7px")]));
      }
      if (!(hab.objets || []).length) noeud.appendChild(el("div", { style: S.note, texte: T("studiov.biblio.vide") }));
      // importer un fichier GLB : sa provenance et sa licence sont déclarées, et gardées avec lui
      noeud.appendChild(titre("studiov.biblio.importer"));
      const fichier = el("input", { type: "file", accept: ".glb,model/gltf-binary", style: S.champ, "data-dz-studiov-glb": true, "aria-label": T("studiov.biblio.fichier") });
      const source = liste("fichier", ["fichier", "polypizza", "sketchfab", "blenderkit", "polyhaven", "ambientcg", "kenney", "quaternius", "creation"].map((s2) => [s2, T("studiov.source." + s2)]), () => {}, T("studiov.biblio.source"));
      const licence = liste("A-VERIFIER", ["A-VERIFIER", "CC0", "CC-BY", "BLENDERKIT-RF", "CREATION", "CC-BY-NC", "CC-BY-ND", "CC-BY-SA"].map((l) => [l, T("studiov.licence." + cleLic(l))]), () => {}, T("studiov.biblio.licence"));
      const auteur = el("input", { type: "text", maxlength: 80, style: S.champ, placeholder: T("studiov.biblio.auteur"), "aria-label": T("studiov.biblio.auteur") });
      const lien = el("input", { type: "url", maxlength: 300, style: S.champ, placeholder: T("studiov.biblio.lien"), "aria-label": T("studiov.biblio.lien") });
      noeud.appendChild(fichier); noeud.appendChild(el("div", { style: S.ligne + ";flex-wrap:nowrap" }, [source, licence])); noeud.appendChild(auteur); noeud.appendChild(lien);
      noeud.appendChild(el("div", { style: S.ligne }, [bouton(T("studiov.biblio.importer.bouton"), () => faire(async () => {
        if (!fichier.files || !fichier.files[0]) { etatImport = T("studiov.biblio.choisir"); return; }
        const corps = new FormData(); corps.append("fichier", fichier.files[0]); corps.append("source", source.value); corps.append("licence", licence.value); corps.append("auteur", auteur.value); corps.append("url", lien.value);
        const r = await fetch("/api/studiov/objets", { method: "POST", body: corps }), v = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error((v && v.detail) || String(r.status));
        await habillage(true); etatImport = T("studiov.biblio.importe", { nom: v.nom, n: v.triangles });
      }))]));
      // depuis Blender : sortir un objet d'un fichier .blend (asset BlenderKit, bibliothèque d'assets, création)
      noeud.appendChild(titre("studiov.blender.titre"));
      noeud.appendChild(el("div", { style: S.note, texte: T("studiov.biblio.blender.note") }));
      const chemin = el("input", { type: "text", value: blendObjets, style: S.champ, placeholder: T("studiov.blender.chemin"), "aria-label": T("studiov.blender.chemin") });
      chemin.addEventListener("input", () => { blendObjets = chemin.value; objetsBlend = null; });
      noeud.appendChild(el("div", { style: S.ligne + ";flex-wrap:nowrap" }, [chemin, bouton(T("studiov.blender.lister"), () => faire(async () => {
        const r = await api("POST", "/api/studiov/blender/objets", { blend: blendObjets }); objetsBlend = r.objets; etatImport = T("studiov.biblio.blender.trouves", { n: r.objets.length });
      }))]));
      if (objetsBlend && objetsBlend.length) {
        const choix = liste(objetsBlend[0].nom, objetsBlend.map((x) => [x.nom, `${x.nom} (${x.faces})`]), () => {}, T("studiov.biblio.blender.objet"));
        const origine = liste("blender", [["blender", T("studiov.source.blender")], ["blenderkit", T("studiov.source.blenderkit")], ["creation", T("studiov.source.creation")]], () => {}, T("studiov.biblio.source"));
        noeud.appendChild(el("div", { style: S.ligne + ";flex-wrap:nowrap" }, [choix, origine]));
        noeud.appendChild(el("div", { style: S.ligne }, [bouton(T("studiov.biblio.blender.sortir"), () => faire(async () => {
          const v = await api("POST", "/api/studiov/blender/exporter", { blend: blendObjets, objet: choix.value, source: origine.value, licence: licence.value, auteur: auteur.value });
          await habillage(true); etatImport = T("studiov.biblio.importe", { nom: v.nom, n: v.triangles });
        }))]));
      }
      noeud.appendChild(etat);
      // les crédits du décor : ce que les licences demandent de citer, prêt à coller sous la vidéo
      noeud.appendChild(titre("studiov.credits.titre"));
      const zone = el("div", { style: S.groupe, "data-dz-studiov-credits": true }, [el("div", { style: S.note, texte: T("studiov.biblio.patience") })]);
      noeud.appendChild(zone);
      ctx.credits().then((r) => {
        zone.textContent = "";
        if (!r || !r.lignes.length) { zone.appendChild(el("div", { style: S.note, texte: T("studiov.credits.aucun") })); return; }
        const texte = (typeof window.dzLang === "function" && window.dzLang() === "en" ? r.texte_en : r.texte_fr) || "";
        if (texte) {
          const aire = el("textarea", { readonly: true, rows: Math.min(8, texte.split("\n").length + 1), style: S.champ + ";resize:vertical;font-size:11.5px;width:100%;box-sizing:border-box" }); aire.value = texte; zone.appendChild(aire);
          zone.appendChild(el("div", { style: S.ligne }, [bouton(T("studiov.credits.copier"), () => { aire.select(); try { navigator.clipboard.writeText(texte); } catch (e) { /* presse-papiers fermé : le texte reste sélectionné */ } })]));
        } else zone.appendChild(el("div", { style: S.note, texte: T("studiov.credits.libre") }));
        if (r.a_verifier.length) zone.appendChild(el("div", { style: S.erreur, texte: T("studiov.credits.verifier", { noms: r.a_verifier.join(", ") }) }));
        if (!r.export) zone.appendChild(el("div", { style: S.note, texte: T("studiov.credits.sansexport") }));
      }).catch(() => { zone.textContent = ""; });
      return noeud;
    }

    // ── Bibliothèque : ce que l'utilisateur a généré ou rangé dans l'application — illustrations, logos, modèles 3D ──
    let bib = null, bibFiltre = "", bibSource = "", imgChoisie = "", etatBib = "", occupeBib = false;
    async function chargerBib() {
      try {
        const [im, tr] = await Promise.all([api("GET", "/api/images?espace=" + encodeURIComponent(ctx.espace() || "*")), api("GET", "/api/etabli/sources").catch(() => ({ jobs: [] }))]);
        bib = { images: (im.images || []).slice().sort((a, b) => (b.mtime || 0) - (a.mtime || 0)), sources: im.sources || {},
          jobs: (tr.jobs || []).filter((j) => !String(j.id).startsWith("_")).sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || ""))) };
      } catch (e) { bib = { images: [], sources: {}, jobs: [] }; etatBib = (e && e.message) || "—"; }
      if (onglet === "bibli") peindre();
    }
    function panneauBibli(d) {
      const noeud = el("div", { style: S.groupe }), etat = el("div", { style: S.note, role: "status", texte: etatBib });
      noeud.appendChild(el("div", { style: S.note, texte: T("studiov.bibli.note") }));
      if (!bib) { noeud.appendChild(el("div", { style: S.note, texte: T("studiov.biblio.patience") })); chargerBib(); return noeud; }
      const faire = async (action) => { if (occupeBib) return; occupeBib = true; etatBib = T("studiov.biblio.patience"); etat.textContent = etatBib;
        try { await action(); } catch (e) { etatBib = (e && e.message) || "—"; } occupeBib = false; peindre(); };
      // les images : chercher, filtrer par fonction d'origine, choisir
      const champ = el("input", { type: "search", value: bibFiltre, style: S.champ, placeholder: T("studiov.bibli.chercher"), "aria-label": T("studiov.bibli.chercher"), "data-dz-studiov-bibli-filtre": true });
      champ.addEventListener("change", () => { bibFiltre = champ.value; peindre(); });
      const origines = [["", T("studiov.bibli.toutes")]].concat(Object.entries(bib.sources).filter(([k]) => bib.images.some((i) => i.source === k)));
      noeud.appendChild(el("div", { style: S.ligne + ";flex-wrap:nowrap" }, [champ, liste(bibSource, origines, (v) => { bibSource = v; peindre(); }, T("studiov.bibli.origine"))]));
      const mots = bibFiltre.toLowerCase().split(/\s+/).filter(Boolean);
      const vues = bib.images.filter((i) => (!bibSource || i.source === bibSource) && mots.every((m) => (i.filename + " " + (i.tags || []).join(" ")).toLowerCase().indexOf(m) >= 0)).slice(0, 80);
      const grille = el("div", { style: "display:grid;grid-template-columns:repeat(4,1fr);gap:4px;max-height:262px;overflow-y:auto", "data-dz-studiov-bibli": true });
      for (const i of vues) {
        grille.appendChild(el("button", { type: "button", title: i.filename, "aria-label": i.filename, "data-dz-studiov-bibli-image": i.filename,
          style: `padding:0;border-radius:0;cursor:pointer;background:#1b2028;border:2px solid ${imgChoisie === i.filename ? "var(--brand,#f0b429)" : "transparent"}`,
          on: { click: () => { imgChoisie = i.filename; etatBib = ""; peindre(); } } },
          [el("img", { src: "/api/studiov/bibliotheque/vignette?f=" + encodeURIComponent(i.filename), alt: i.filename, loading: "lazy", width: 70, height: 70, style: "display:block;width:100%;aspect-ratio:1;object-fit:contain" })]));
      }
      if (!vues.length) grille.appendChild(el("div", { style: S.note + ";grid-column:1/-1", texte: T("studiov.bibli.vide") }));
      noeud.appendChild(grille);
      if (imgChoisie) {
        noeud.appendChild(el("div", { style: S.note + ";overflow:hidden;text-overflow:ellipsis;white-space:nowrap", texte: imgChoisie }));
        // l'image choisie entre dans le studio (une copie), puis se pose : au mur, sur pied, sur l'écran du décor, en enseigne
        const entrer = async () => { const v = await api("POST", "/api/studiov/bibliotheque/image", { filename: imgChoisie }); await habillage(true); return v; };
        const objet = (type) => () => faire(async () => { const v = await entrer(), nd = copie(ctx.decor()); if (nd.objets.length >= 120) return;
          nd.objets.push(objetNeuf(nd, type, v.ref)); etatBib = T("studiov.bibli.pose", { nom: v.nom }); ctx.modifier(nd, true); ctx.choisir({ genre: "objet", index: nd.objets.length - 1 }); });
        noeud.appendChild(el("div", { style: S.ligne }, [bouton(T("studiov.objet.tableau"), objet("tableau")), bouton(T("studiov.objet.logo_mural"), objet("logo_mural")), bouton(T("studiov.objet.kakemono"), objet("kakemono")),
          bouton(T("studiov.bibli.ecran"), () => faire(async () => { const nd0 = ctx.decor(); if (!nd0.ecrans.length) { etatBib = T("studiov.bibli.sansecran"); return; }
            const v = await entrer(), nd = copie(ctx.decor()); nd.ecrans[0].source = "image"; nd.ecrans[0].image = v.ref; etatBib = T("studiov.bibli.pose", { nom: v.nom }); ctx.modifier(nd); })),
          bouton(T("studiov.bibli.enseigne"), () => faire(async () => { const v = await entrer(), nd = copie(ctx.decor()); nd.enseigne.actif = true; nd.enseigne.source = "image"; nd.enseigne.image = v.ref;
            etatBib = T("studiov.bibli.pose", { nom: v.nom }); ctx.modifier(nd); }))]));
      }
      if (d.ecrans.some((e) => e.source === "image")) noeud.appendChild(bouton(T("studiov.bibli.ecran.rendre"), () => { const nd = copie(ctx.decor());
        for (const e of nd.ecrans) if (e.source === "image") { e.source = "ecran"; e.image = ""; } ctx.modifier(nd); }));
      // les modèles 3D générés dans l'application (Game Assets 3D, Établi) : la version allégée si elle existe
      noeud.appendChild(titre("studiov.bibli.modeles"));
      for (const j of bib.jobs.slice(0, 60)) {
        const der = (j.etapes || []).slice(-1)[0] || {};
        noeud.appendChild(el("div", { style: S.ligne + ";flex-wrap:nowrap;gap:6px;border-bottom:1px solid var(--brd-soft,#222830);padding-bottom:4px", "data-dz-studiov-bibli-modele": j.id }, [
          el("div", { style: "flex:1;min-width:0;display:flex;flex-direction:column" }, [el("span", { texte: j.nom || j.id, style: "overflow:hidden;text-overflow:ellipsis;white-space:nowrap" }),
            el("span", { style: S.badge, texte: [j.moteur, der.libelle, der.triangles ? T("studiov.bibli.triangles", { n: der.triangles }) : null].filter(Boolean).join(" · ") })]),
          bouton(T("studiov.biblio.poser"), () => faire(async () => { const v = await api("POST", "/api/studiov/bibliotheque/modele", { job: j.id }); await habillage(true); await chargeurGLB();
            const nd = copie(ctx.decor()); if (nd.objets.length >= 120) return; nd.objets.push(objetNeuf(nd, "modele", v.ref, v.pose)); etatBib = T("studiov.bibli.pose", { nom: v.nom });
            ctx.modifier(nd, true); ctx.choisir({ genre: "objet", index: nd.objets.length - 1 }); }))]));
      }
      if (!bib.jobs.length) noeud.appendChild(el("div", { style: S.note, texte: T("studiov.bibli.modeles.vide") }));
      noeud.appendChild(etat);
      noeud.appendChild(el("div", { style: S.ligne }, [bouton(T("studiov.bibli.actualiser"), () => { bib = null; etatBib = ""; peindre(); })]));
      return noeud;
    }

    // ── Catalogue : de vrais produits en 3D, à leur taille (Amazon Berkeley Objects, CC BY 4.0). Rien n'est livré avec
    // l'application : la liste, les vignettes et chaque modèle sont téléchargés à la demande ; le crédit suit le modèle. ──
    let cat = null, catQ = "", catFam = "", catPage = 1, catRes = null, catChoisi = null, etatCat = "", occupeCat = false, catDemande = 0;
    const anglais = () => typeof window.dzLang === "function" && window.dzLang() === "en";
    const cm = (m) => String(Math.round(m * 100));
    async function chargerCat() {
      try { cat = await api("GET", "/api/studiov/catalogue"); } catch (e) { cat = { pret: false, total: 0, familles: [], source: {} }; etatCat = (e && e.message) || "—"; }
      if (cat.pret) await chercherCat(); else if (onglet === "catalogue") peindre();
    }
    async function chercherCat() {
      const moi = ++catDemande;
      try {
        const r = await api("GET", "/api/studiov/catalogue/recherche?q=" + encodeURIComponent(catQ) + "&famille=" + encodeURIComponent(catFam) + "&page=" + catPage);
        if (moi !== catDemande) return;
        catRes = r; catPage = r.page;
        if (catChoisi && !r.resultats.some((p) => p.id === catChoisi.id)) catChoisi = null;
      } catch (e) { if (moi !== catDemande) return; catRes = { total: 0, page: 1, pages: 1, resultats: [] }; etatCat = (e && e.message) || "—"; }
      if (onglet === "catalogue") peindre();
    }
    function panneauCatalogue() {
      const noeud = el("div", { style: S.groupe, "data-dz-studiov-catalogue": true }), etat = el("div", { style: S.note, role: "status", texte: etatCat });
      noeud.appendChild(el("div", { style: S.note, texte: T("studiov.cat.note") }));
      if (!cat) { noeud.appendChild(el("div", { style: S.note, texte: T("studiov.biblio.patience") })); chargerCat(); return noeud; }
      const faire = async (action) => { if (occupeCat) return; occupeCat = true; etatCat = T("studiov.biblio.patience"); etat.textContent = etatCat;
        try { await action(); } catch (e) { etatCat = (e && e.message) || "—"; } occupeCat = false; peindre(); };
      if (!cat.pret) {
        noeud.appendChild(el("div", { style: S.note, texte: T("studiov.cat.absent") }));
        noeud.appendChild(el("div", { style: S.ligne }, [el("button", { type: "button", style: S.principal, "data-dz-studiov-cat-charger": true, texte: T("studiov.cat.charger"),
          on: { click: () => faire(async () => { cat = await api("POST", "/api/studiov/catalogue/index"); etatCat = T("studiov.cat.charge", { n: cat.total }); catPage = 1; await chercherCat(); }) } })]));
        noeud.appendChild(etat);
        return noeud;
      }
      // chercher (en français ou en anglais), filtrer par famille
      const champ = el("input", { type: "search", value: catQ, style: S.champ, placeholder: T("studiov.cat.chercher"), "aria-label": T("studiov.cat.chercher"), "data-dz-studiov-cat-filtre": true });
      champ.addEventListener("change", () => { catQ = champ.value; catPage = 1; etatCat = ""; chercherCat(); });
      const familles = [["", T("studiov.cat.toutes", { n: cat.total })]].concat(cat.familles.map((x) => [x.id, `${anglais() ? x.nom_en : x.nom} (${x.n})`]));
      noeud.appendChild(el("div", { style: S.ligne + ";flex-wrap:nowrap" }, [champ, liste(catFam, familles, (v) => { catFam = v; catPage = 1; etatCat = ""; chercherCat(); }, T("studiov.cat.famille"))]));
      if (!catRes) { noeud.appendChild(el("div", { style: S.note, texte: T("studiov.biblio.patience") })); noeud.appendChild(etat); return noeud; }
      const nomType = (p) => (anglais() ? p.libelle_en : p.libelle);
      const grille = el("div", { style: "display:grid;grid-template-columns:repeat(3,1fr);gap:4px;max-height:330px;overflow-y:auto", "data-dz-studiov-cat-grille": true });
      for (const p of catRes.resultats) {
        const choisiIci = catChoisi && catChoisi.id === p.id;
        grille.appendChild(el("button", { type: "button", title: p.nom + (p.deja ? " — " + T("studiov.cat.deja") : ""), "aria-label": p.nom, "aria-pressed": String(!!choisiIci), "data-dz-studiov-cat-produit": p.id,
          style: `padding:0;border-radius:0;cursor:pointer;background:#f3f1ec;color:#111;display:flex;flex-direction:column;border:2px solid ${choisiIci ? "var(--brand,#f0b429)" : "transparent"}`,
          on: { click: () => { catChoisi = p; etatCat = ""; peindre(); } } },
          [el("img", { src: p.vignette, alt: "", loading: "lazy", width: 96, height: 96, style: "display:block;width:100%;aspect-ratio:1;object-fit:contain" }),
            el("span", { style: "font-size:10.5px;line-height:1.2;padding:2px 3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;background:var(--srf-raised,#1b2028);color:var(--txt-hi,#e6e9ee)",
              texte: (p.deja ? "• " : "") + nomType(p) })]));
      }
      if (!catRes.resultats.length) grille.appendChild(el("div", { style: S.note + ";grid-column:1/-1", texte: T("studiov.cat.vide") }));
      noeud.appendChild(grille);
      noeud.appendChild(el("div", { style: S.ligne + ";justify-content:space-between" }, [
        bouton("‹", () => { if (catPage > 1) { catPage -= 1; chercherCat(); } }, catPage > 1 ? "" : ";opacity:.4"),
        el("span", { style: S.note, texte: T("studiov.cat.page", { n: catRes.total, page: catRes.page, pages: catRes.pages }) }),
        bouton("›", () => { if (catPage < catRes.pages) { catPage += 1; chercherCat(); } }, catPage < catRes.pages ? "" : ";opacity:.4")]));
      if (catChoisi) {
        const p = catChoisi;
        noeud.appendChild(el("div", { style: "font-size:12px", texte: p.nom, "data-dz-studiov-cat-fiche": p.id }));
        noeud.appendChild(el("div", { style: S.badge, texte: [nomType(p), p.couleur, p.matiere, T("studiov.cat.dims", { l: cm(p.dims[0]), h: cm(p.dims[1]), p: cm(p.dims[2]) }),
          T("studiov.bibli.triangles", { n: p.triangles }), T("studiov.cat.poids", { n: (p.octets / 1048576).toFixed(1) }), T("studiov.cat.pose." + p.pose), p.lumineux ? T("studiov.cat.lumineux") : null,
          p.lourd ? T("studiov.droit.lourd") : null].filter(Boolean).join(" · ") }));
        noeud.appendChild(el("div", { style: S.ligne }, [el("button", { type: "button", style: S.principal, "data-dz-studiov-cat-poser": p.id, texte: T(p.deja ? "studiov.biblio.poser" : "studiov.cat.poser"),
          on: { click: () => faire(async () => {
            const v = await api("POST", "/api/studiov/catalogue/poser", { id: p.id }); await habillage(true); await chargeurGLB();
            const nd = copie(ctx.decor()); if (nd.objets.length >= 120) { etatCat = T("studiov.cat.plein"); return; }
            nd.objets.push(objetNeuf(nd, "modele", v.ref, v.pose)); p.deja = v.ref; etatCat = T("studiov.bibli.pose", { nom: v.nom });
            ctx.modifier(nd, true); ctx.choisir({ genre: "objet", index: nd.objets.length - 1 });
          }) } })]));
      }
      noeud.appendChild(etat);
      noeud.appendChild(el("div", { style: S.note, texte: T("studiov.cat.credit") }));
      return noeud;
    }

    const ONGLETS = [["style", panneauStyle], ["matieres", panneauMatieres], ["objets", panneauObjets], ["catalogue", panneauCatalogue], ["bibli", panneauBibli], ["biblio", panneauBiblio], ["lumieres", panneauLumieres],
      ["cameras", panneauCameras], ["enseigne", panneauEnseigne]];
    // ce qu'on vient de choisir sur le plan ou dans la vue 3D : le panneau ouvre l'onglet qui le règle
    function viser(c) {
      choisi = c && c.genre === "objet" ? c.index : -1;
      lum = c && c.genre === "lumiere" ? c.index : -1;
      if (c && !ctx.livre()) {
        if (c.genre === "objet") { if (onglet !== "matieres" || !objetDe(surface)) onglet = "objets"; else surface = "objet:" + c.index + ":1"; }
        else if (c.genre === "surface") { onglet = "matieres"; surface = c.pan; famille = ""; }
        else if (c.genre === "lumiere") onglet = "lumieres";
        else if (c.genre === "camera") { onglet = "cameras"; cam = c.index; }
        else if (c.genre === "presentateur") onglet = "cameras";
        else if (c.genre === "enseigne") onglet = "enseigne";
      }
      peindre();
    }
    function peindre() {
      hote.textContent = "";
      const d = ctx.decor();
      hote.appendChild(el("div", { style: S.titreG, texte: T("studiov.deco.titre") }));
      if (!d) return;
      if (ctx.livre()) {
        hote.appendChild(el("div", { style: S.note, texte: T("studiov.deco.livre") }));
        hote.appendChild(el("button", { type: "button", style: S.principal, "data-dz-studiov-personnaliser": true, texte: T("studiov.deco.personnaliser"), on: { click: ctx.personnaliser } }));
        return;
      }
      if (!hab) { hote.appendChild(el("div", { style: S.note, texte: T("studiov.deco.chargement") })); return; }
      hote.appendChild(el("div", { style: "display:flex;gap:0;flex-wrap:wrap", role: "tablist" }, ONGLETS.map(([id]) => el("button", { type: "button", role: "tab", "aria-selected": String(onglet === id),
        "data-dz-studiov-onglet": id, texte: T("studiov.deco.onglet." + id),
        style: S.bouton + `;padding:4px 8px;font-size:12px;border-right-width:0;${onglet === id ? "background:var(--brand,#f0b429);color:#111;border-color:var(--brand,#f0b429);font-weight:600" : ""}`,
        on: { click: () => { onglet = id; peindre(); } } }))));
      hote.appendChild(ONGLETS.find(([id]) => id === onglet)[1](d));
    }
    return { peindre, viser };
  }

  let liste = null;
  const details = new Map();
  async function charger() { liste = await api("GET", "/api/studiov"); return liste; }
  async function preparer(id) {
    // le catalogue d'habillage porte l'index des vraies textures : sans lui, le décor retombe sur ses motifs dessinés
    const [d] = await Promise.all([api("GET", "/api/studiov/" + encodeURIComponent(id)), delai(habillage().catch(() => null), 1500)]);
    const logo = await delai(chargerImage(`${d.contexte.logo_espace}?v=${Date.now()}`), 1500);
    if (d.decor.objets.some((x) => x.type === "modele")) await delai(chargeurGLB(), 2500);
    const r = { decor: d.decor, contexte: d.contexte, logo };
    details.set(id, r);
    return r;
  }

  // ── pour l'enregistreur (dz-capture.js) ──
  let habit = null;
  function poser(scene, d, env) {
    const E = env || {};
    const m = creerMoteur(THREE, { largeur: scene.largeur, hauteur: scene.hauteur, decor: d.decor, contexte: d.contexte,
      logo: d.logo, qualite: qualite(), apercu: !!E.apercu, textures: hab ? hab.index : {}, objets: hab ? hab.indexObjets : {}, images: hab ? hab.indexImages : {}, chargeur: porteGLB,
      surChange: E.surChange });
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
      moteur: () => m,
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
    if (apercu.finir) apercu.finir();                 // une retouche encore en attente part avant la fermeture
    if (apercu.plan) apercu.plan.detruire();
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
    const vues = el("div", { style: "display:flex;gap:0;align-items:center", role: "tablist", "data-dz-studiov-vues": true });
    const fiche = el("div", { style: S.note, "data-dz-studiov-fiche": true });
    const erreur = el("div", { style: S.erreur, role: "alert", "data-dz-studiov-erreur": true });
    const droite = el("div", { style: S.droite, "data-dz-studiov-decorer": true });
    const btnChoisir = el("button", { type: "button", style: S.principal, "data-dz-studiov-choisir": true, texte: T("studiov.apercu.choisir") });
    const btnCopier = el("button", { type: "button", style: S.bouton, "data-dz-studiov-dupliquer": true, texte: T("studiov.apercu.dupliquer") });
    const btnSans = el("button", { type: "button", style: S.bouton, "data-dz-studiov-sans": true, texte: T("studiov.capture.aucun") });
    const selQ = el("select", { style: S.champ + ";flex:none;width:auto", "data-dz-studiov-qualite": true, "aria-label": T("studiov.apercu.qualite") },
      ["legere", "haute"].map((q) => el("option", { value: q, texte: T("studiov.qualite." + q) })));
    selQ.value = qualite();
    const btnFermer = el("button", { type: "button", style: S.bouton, texte: T("studiov.apercu.fermer"), on: { click: fermerApercu } });
    const boite = el("div", { style: S.boite, role: "dialog", "aria-modal": "true", "aria-label": T("studiov.apercu.titre"), "data-dz-studiov-apercu-boite": true }, [
      titre,
      el("div", { style: S.corps }, [gauche, el("div", { style: S.centre }, [vues, cadre, cams, fiche, erreur]), droite]),
      el("div", { style: S.pied }, [btnChoisir, btnCopier, btnSans, el("span", { style: "flex:1" }),
        el("span", { style: S.note, texte: T("studiov.apercu.qualite") }), selQ, btnFermer]),
    ]);
    const voile = el("div", { style: S.voile, "data-dz-studiov-voile": true }, [boite]);
    const echap = (e) => { if (e.key === "Escape") { e.stopPropagation(); fermerApercu(); } };
    document.addEventListener("keydown", echap, true);
    document.body.appendChild(voile);
    apercu = { voile, echap, apres: O.apres, choisi: undefined, habit: null, minuterie: null, id: null, scene: null,
      edition: null, contexte: null, livre: true, sauve: null, aSauver: null, trame: null, finir: null, vue: "cameras", sel: null, plan: null };
    const majFiche = (dd) => { fiche.textContent = T("studiov.apercu.fiche", { objets: dd.objets.length, lumieres: dd.lumieres.length, cameras: dd.cameras.length,
      niveau: T(dd.fabrique ? "studiov.niveau.fabrique" : "studiov.niveau.direct") }); };
    async function enregistrer(id) {
      const d = details.get(id);
      if (!d) return;
      try { await api("PUT", "/api/studiov/" + encodeURIComponent(id), d.decor); }
      catch (e) { erreur.textContent = T("studiov.erreur.enregistrer", { msg: (e && e.message) || "—" }); }
    }
    let ecriture = Promise.resolve();
    const finir = () => { if (apercu && apercu.aSauver) { clearTimeout(apercu.sauve); const id = apercu.aSauver; apercu.aSauver = null; ecriture = enregistrer(id); } return ecriture; };
    // ── l'atelier : trois vues du même décor, et un seul « choisi » partagé par le plan, la vue 3D et le panneau ──
    const moteur = () => (apercu && apercu.habit ? apercu.habit.moteur() : null);
    function choisirCible(c) {
      if (!apercu) return;
      apercu.sel = c || null;
      const M = moteur();
      if (M) M.choisir(c && c.genre !== "presentateur" ? c : null);
      if (c && c.genre === "camera" && apercu.vue === "cameras" && apercu.habit) apercu.habit.camera(c.index);
      deco.viser(apercu.sel);
      if (apercu.plan) apercu.plan.peindre();
    }
    function peindreCams() {
      cams.textContent = "";
      if (!apercu || !apercu.habit) return;
      if (apercu.vue === "libre") {
        cams.appendChild(el("span", { style: S.note, texte: T("studiov.libre.aide") }));
        if (!apercu.livre) cams.appendChild(el("button", { type: "button", style: S.bouton, "data-dz-studiov-garder": true, texte: T("studiov.libre.garder"), on: { click: () => {
          const M = moteur(), p = M && M.poseLibre(), nd = JSON.parse(JSON.stringify(apercu.edition));
          if (!p || nd.cameras.length >= 6) { erreur.textContent = T("studiov.libre.plein"); return; }
          nd.cameras.push({ ...cameraNeuve(nd), ...p }); modifier(nd, true); choisirCible({ genre: "camera", index: nd.cameras.length - 1 });
        } } }));
        return;
      }
      apercu.edition.cameras.forEach((c, i) => cams.appendChild(el("button", { type: "button", style: S.bouton, "data-dz-studiov-camera": String(i),
        texte: `${i + 1} · ${c.nom}`, on: { click: () => { if (apercu) { apercu.habit.camera(i); if (!apercu.livre) choisirCible({ genre: "camera", index: i }); } } } })));
    }
    function mettreVue(v) {
      if (!apercu) return;
      apercu.vue = v;
      const M = moteur(), cv = apercu.scene && apercu.scene.canvas;
      if (M) M.vueLibre(v === "libre");
      if (cv) cv.style.cssText = v === "plan" ? "position:absolute;right:8px;bottom:30px;width:34%;aspect-ratio:16/9;border:1px solid var(--brd-hard,#2a3138);z-index:2;cursor:pointer"
        : `position:absolute;inset:0;width:100%;height:100%;cursor:${v === "libre" ? "grab" : "pointer"}`;
      if (apercu.plan) { apercu.plan.canvas.style.display = v === "plan" ? "block" : "none"; if (v === "plan") apercu.plan.peindre(); }
      vues.textContent = "";
      for (const id of ["cameras", "plan", "libre"]) vues.appendChild(el("button", { type: "button", role: "tab", "aria-selected": String(v === id), "data-dz-studiov-vue": id, texte: T("studiov.vue." + id),
        style: S.bouton + `;border-right-width:${id === "libre" ? 1 : 0}px;${v === id ? "background:var(--brand,#f0b429);color:#111;border-color:var(--brand,#f0b429);font-weight:600" : ""}`, on: { click: () => mettreVue(id) } }));
      peindreCams();
    }
    // la souris dans la vue 3D : un clic choisit (objet, pan de mur, lumière, caméra) ; en vue libre, glisser tourne
    // autour de la pièce, Maj + glisser (ou le bouton droit) la déplace, la molette approche
    function ecouterVue3d(cv) {
      let geste = null;
      cv.addEventListener("pointerdown", (e) => { geste = { x: e.clientX, y: e.clientY, bouge: false, cote: e.button !== 0 || e.shiftKey }; try { cv.setPointerCapture(e.pointerId); } catch (err) { /* pointeur déjà relâché */ } });
      cv.addEventListener("pointermove", (e) => {
        if (!geste) return;
        const dx = e.clientX - geste.x, dy = e.clientY - geste.y;
        if (!geste.bouge && Math.hypot(dx, dy) < 4) return;
        geste.bouge = true; geste.x = e.clientX; geste.y = e.clientY;
        const M = moteur();
        if (!M || !apercu || apercu.vue !== "libre") return;
        if (geste.cote) M.glisser(dx, dy); else M.orbiter(dx * 0.006, dy * 0.005);
      });
      cv.addEventListener("pointerup", (e) => {
        const g = geste; geste = null;
        const M = moteur();
        if (!g || g.bouge || !M || !apercu) return;
        if (apercu.vue === "plan") { mettreVue("cameras"); return; }           // la vignette 3D du plan : un clic y revient
        const r = cv.getBoundingClientRect();
        choisirCible(M.viser(((e.clientX - r.left) / r.width) * 2 - 1, -(((e.clientY - r.top) / r.height) * 2 - 1)));
      });
      cv.addEventListener("wheel", (e) => { const M = moteur(); if (!M || !apercu || apercu.vue !== "libre") return; e.preventDefault(); M.zoomer(e.deltaY > 0 ? 1.1 : 0.9); }, { passive: false });
      cv.addEventListener("contextmenu", (e) => e.preventDefault());
    }
    apercu.finir = finir;
    // une retouche du décorateur : montrée à la trame suivante (une reconstruction au plus par trame), enregistrée
    // 700 ms après la dernière ; `leger` = le panneau n'a pas à se repeindre (curseur en cours de glissement)
    function modifier(nd, leger) {
      if (!apercu || apercu.livre || !apercu.habit) return;
      erreur.textContent = "";
      apercu.edition = nd;
      const d = details.get(apercu.id);
      if (d) d.decor = nd;
      if (!apercu.trame) apercu.trame = setTimeout(() => { if (apercu) { apercu.trame = null; if (apercu.habit && apercu.edition) { apercu.habit.maj({ decor: apercu.edition }); if (apercu.plan) apercu.plan.peindre(); } } }, 50);
      clearTimeout(apercu.sauve);
      apercu.aSauver = apercu.id;
      apercu.sauve = setTimeout(finir, 700);
      majFiche(nd);
      if (!leger) { deco.peindre(); peindreCams(); }
    }
    const deco = decorateur(droite, { decor: () => (apercu ? apercu.edition : null), contexte: () => (apercu ? apercu.contexte : null),
      livre: () => !apercu || apercu.livre, modifier, moteur, choisir: choisirCible, espace: () => (liste ? liste.espace : "*"),
      credits: async () => { if (!apercu || !apercu.id || apercu.livre) return null; const id = apercu.id; await finir(); return api("GET", "/api/studiov/" + encodeURIComponent(id) + "/credits"); },
      personnaliser: async () => {
        if (!apercu || !apercu.id) return;
        try { const v = await api("POST", "/api/studiov", { base: apercu.id }); await peindreListe(v.id); }
        catch (e) { erreur.textContent = T("studiov.erreur.dupliquer", { msg: (e && e.message) || "—" }); }
      } });

    const { creerScene } = await import("./dz-capture-scene.js");
    async function montrer(id) {
      if (!apercu) return;
      erreur.textContent = "";
      try {
        const [d] = await Promise.all([details.get(id) || preparer(id), moteur3d()]);
        if (!apercu) return;
        finir();
        clearTimeout(apercu.trame); apercu.trame = null;
        if (apercu.habit) { apercu.habit.retirer(); apercu.habit = null; }
        if (apercu.plan) { apercu.plan.detruire(); apercu.plan = null; }
        clearInterval(apercu.minuterie);
        const scene = creerScene({ largeur: 1280, hauteur: 720, fps: 30, secrets: () => [] });
        scene.canvas.setAttribute("data-dz-studiov-canvas", "");
        cadre.textContent = ""; cadre.appendChild(scene.canvas);
        apercu.habit = poser(scene, d, { apercu: true, surChange: () => { if (apercu && apercu.plan) apercu.plan.peindre(); } });
        apercu.scene = scene; apercu.id = id; apercu.sel = null;
        apercu.minuterie = setInterval(() => scene.dessiner(), 33);
        scene.dessiner();
        apercu.edition = d.decor; apercu.contexte = d.contexte; apercu.livre = !!d.decor.livre;
        ecouterVue3d(scene.canvas);
        apercu.plan = creerPlan({ T, decor: () => (apercu ? apercu.edition : null), empreintes: () => { const M = moteur(); return M ? M.empreintes() : []; },
          palette: () => palette(apercu ? apercu.contexte : null), selection: () => (apercu ? apercu.sel : null), choisir: choisirCible, modifier,
          livre: () => !apercu || apercu.livre,
          mural: (ob) => ob.type === "modele" && !!hab && !!hab.indexObjets[ob.ref] && hab.indexObjets[ob.ref].pose === "mur" });
        cadre.appendChild(apercu.plan.canvas);
        majFiche(d.decor);
        deco.viser(null);
        mettreVue(apercu.vue);
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
    charger, groupeCapture, habiller, ouvrirApercu, fermerApercu, habillage,
    actuel: () => habit, oublier: () => { habit = null; },
  };
}
