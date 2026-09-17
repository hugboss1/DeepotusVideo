// mod-typo.js — Texte & logo : la bibliothèque de polices (dist OFL +
// déposées + système si le navigateur les donne), les @font-face, l'éditeur
// de texte EN PLACE (plus de prompt), le panneau Texte avec son sélecteur
// visuel, les contours (un chemin par glyphe ou un seul, éditables aux
// nœuds), le contour ±, le texte sur chemin, le cadre, et « → Logo 3D » qui
// enchaîne contours puis le dialogue Impression 3D en mode logo.
// La partie haute est PURE (bancable node avec opentype et une vraie police).
import { op_ajouter, op_supprimer, op_style, op_texte_vectoriser, op_texte_en_cadre, op_texte_sur_chemin } from "./mod-doc.js";
import { op_contour } from "./mod-bool.js";
import { POLICES, commandes_vers_d } from "./mod-texte3d.js";

/* ── pur ── */
export function polices_toutes(lib, user, systeme) {
  const out = [];
  for (const p of lib || []) out.push({ id: "lib:" + p.id, famille: p.nom, nom: p.nom, source: "lib", fichier: p.fichier, url: "/fonts/" + p.fichier });
  for (const u of user || []) {
    const nom = u.nom || u, famille = String(nom).replace(/\.[^.]+$/, "");
    out.push({ id: "user:" + nom, famille, nom: famille, source: "user", fichier: nom, url: "/api/fonts/user/" + encodeURIComponent(nom) });
  }
  for (const f of systeme || []) out.push({ id: "sys:" + f, famille: f, nom: f, source: "systeme" });
  return out;
}
export function font_face_css(polices) {
  return (polices || []).filter((p) => p.url).map((p) =>
    `@font-face { font-family: "${p.famille.replace(/"/g, "")}"; src: url("${p.url}"); font-display: swap; }`).join("\n");
}
const _MAGIC = ["\x00\x01\x00\x00", "true", "OTTO", "wOFF", "wOF2"];
export function police_fichier_valide(nom, octets) {
  if (!/^[A-Za-z0-9_-]+\.(ttf|otf|woff|woff2)$/i.test(String(nom || ""))) return false;
  const u = octets instanceof Uint8Array ? octets : new Uint8Array(octets && octets.buffer ? octets.buffer : (octets || new ArrayBuffer(0)));
  if (u.length < 8) return false;
  const m = String.fromCharCode(u[0], u[1], u[2], u[3]);
  return _MAGIC.includes(m);
}
export function lignes_de(contenu) {
  const l = String(contenu ?? "").split("\n");
  while (l.length > 1 && l[l.length - 1] === "") l.pop();
  return l;
}
export function glyphes_separes(font, texte, taille, x, y, interlettrage = 0) {
  const s = String(texte || "");
  if (!s.trim()) return [];
  const paths = font.getPaths(s, x, y, taille, { kerning: true, letterSpacing: interlettrage / taille });
  const out = [];
  [...s].forEach((car, i) => {
    const p = paths[i];
    if (!p || !p.commands || !p.commands.length || !car.trim()) return;
    const d = commandes_vers_d(p.commands);
    if (!d) return;
    const b = p.getBoundingBox();
    out.push({ car, d, x: b.x1, y: b.y1 });
  });
  return out;
}
export function texte_multi_d(font, lignes, taille, x, y, interlettrage = 0, interligne = 1.2, ancre = "start") {
  const parts = [];
  (lignes || []).forEach((l, i) => {
    if (!l) return;
    const opts = { kerning: true, letterSpacing: interlettrage / taille };
    const w = font.getAdvanceWidth(l, taille, opts);
    const x0 = ancre === "middle" ? x - w / 2 : ancre === "end" ? x - w : x;
    const d = commandes_vers_d(font.getPath(l, x0, y + i * taille * interligne, taille, opts).commands);
    if (d) parts.push(d);
  });
  return parts.join(" ");
}

/* ── UI ── */
export function initTypo(VL) {
  const { $, etat } = VL;
  const hote = $("#panneauTexte"), stage = $("#stage");
  etat.typo = { polices: polices_toutes(POLICES, [], []), courante: "lib:anton", parGlyphe: true, systeme: [] };
  const fonts = new Map();               // id → opentype.Font
  const feuille = document.createElement("style");
  feuille.id = "typoFontFaces";
  document.head.appendChild(feuille);
  const majFontFaces = () => { feuille.textContent = font_face_css(etat.typo.polices); };
  majFontFaces();
  async function chargerBibliotheque() {
    try {
      const d = await VL.api.get("/fonts");
      etat.typo.polices = polices_toutes(POLICES, d.user || [], etat.typo.systeme);
      majFontFaces(); rendre();
    } catch (e) { /* hors ligne : la bibliothèque du dist suffit */ }
  }
  chargerBibliotheque();
  const policeDe = (id) => etat.typo.polices.find((p) => p.id === id) || null;
  const policeParFamille = (famille) => etat.typo.polices.find((p) => p.famille === famille) || null;
  async function fontDe(p) {
    if (!p) throw new Error("police inconnue");
    if (fonts.has(p.id)) return fonts.get(p.id);
    let buf;
    if (p.url) {
      const r = await fetch(p.url);
      if (!r.ok) throw new Error(`police ${p.famille} introuvable (${r.status})`);
      buf = await r.arrayBuffer();
    } else {
      const trouvees = await window.queryLocalFonts({ postscriptNames: undefined });
      const f = trouvees.find((x) => x.family === p.famille);
      if (!f) throw new Error(`police système ${p.famille} indisponible`);
      buf = await (await f.blob()).arrayBuffer();
    }
    const font = window.opentype.parse(buf);
    fonts.set(p.id, font);
    return font;
  }

  /* ── éditeur en place ── */
  let editeur = null;
  function fermerEditeur(valider) {
    if (!editeur) return;
    const { ta, id, neuf } = editeur;
    editeur = null;
    const contenu = ta.value.replace(/\r/g, "");
    ta.remove();
    if (!valider) { if (neuf) VL.executer(op_supprimer, [id]); return; }
    if (!contenu.trim()) { VL.executer(op_supprimer, [id]); return; }
    VL.executer((doc) => {
      const t = _profond(doc, id);
      if (!t || (t.type !== "texte" && t.type !== "cadre")) throw new Error("texte introuvable");
      t.contenu = contenu;
    });
    if (neuf) VL.setOutil("select");           // le texte posé, on revient à la sélection (double-clic pour rééditer)
    VL.setSelection([id]);
  }
  function _profond(doc, id) {
    const visiter = (objs) => { for (const o of objs || []) { if (o.id === id) return o; if (o.type === "groupe") { const t = visiter(o.enfants); if (t) return t; } } return null; };
    for (const c of doc.calques) { const t = visiter(c.objets); if (t) return t; }
    return null;
  }
  VL.editerTexte = (id, { neuf = false } = {}) => {
    fermerEditeur(true);
    const t = VL.objetDe(id);
    if (!t || (t.objet.type !== "texte" && t.objet.type !== "cadre")) return;
    const o = t.objet, s = o.style || {}, corps = Number(s.corps || 16);
    const ta = document.createElement("textarea");
    ta.className = "tx-editeur";
    ta.value = o.contenu || "";
    const [ex, ey] = VL.ecranPt(o.x, o.type === "cadre" ? o.y : o.y - corps);
    const w = o.type === "cadre" ? o.w * etat.zoom : Math.max(120, (o.contenu || "Texte").length * corps * 0.6 * etat.zoom + 40);
    ta.style.cssText = `left:${ex}px;top:${ey}px;width:${w}px;font-family:"${s.police || "Segoe UI"}";font-size:${corps * etat.zoom}px;font-weight:${s.graisse || "normal"};letter-spacing:${(s.interlettrage || 0) * etat.zoom}px;line-height:${s.interligne || 1.2};color:${typeof s.fond === "string" && /^#/.test(s.fond) ? s.fond : "#1F1512"};text-align:${{ middle: "center", end: "right" }[s.ancre] || "left"}`;
    stage.appendChild(ta);
    editeur = { ta, id, neuf };
    ta.addEventListener("keydown", (ev) => {
      ev.stopPropagation();
      if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); fermerEditeur(true); }
      else if (ev.key === "Escape") { ev.preventDefault(); fermerEditeur(false); }
    });
    ta.addEventListener("blur", () => fermerEditeur(true));
    ta.focus(); ta.select();
    return ta;
  };
  // l'outil Texte pose un texte vide et ouvre l'éditeur ; mod-tools délègue ici
  VL.poserTexte = (x, y) => {
    const sc = etat.styleCourant;
    const fond = (sc.fond && sc.fond !== "none" && !String(sc.fond).startsWith("grad:")) ? sc.fond : (sc.contour && sc.contour !== "none" ? sc.contour : "#1F1512");
    const p = policeDe(etat.typo.courante);
    const id = VL.executer(op_ajouter, etat.calqueActif, { type: "texte", x, y, contenu: "", style: { fond, police: p ? p.famille : "Segoe UI", corps: 48 } });
    if (id) { VL.setSelection([id]); VL.editerTexte(id, { neuf: true }); }
    return id;
  };

  /* ── contours, contour ±, logo 3D ── */
  async function vectoriser(id, parGlyphe) {
    const t = VL.objetDe(id);
    if (!t || t.objet.type !== "texte") throw new Error("sélectionner un texte");
    const o = t.objet, s = o.style || {};
    const p = policeParFamille(s.police) || policeDe(etat.typo.courante);
    const font = await fontDe(p);
    const corps = +s.corps || 16, inter = +s.interlettrage || 0, lignes = lignes_de(o.contenu);
    let r;
    if (parGlyphe) {
      const gl = [];
      lignes.forEach((l, i) => {
        if (!l) return;
        const w = font.getAdvanceWidth(l, corps, { kerning: true, letterSpacing: inter / corps });
        const x0 = s.ancre === "middle" ? o.x - w / 2 : s.ancre === "end" ? o.x - w : o.x;
        gl.push(...glyphes_separes(font, l, corps, x0, o.y + i * corps * (+s.interligne || 1.2), inter));
      });
      r = VL.executer(op_texte_vectoriser, id, gl);
    } else {
      r = VL.executer(op_texte_vectoriser, id, texte_multi_d(font, lignes, corps, o.x, o.y, inter, +s.interligne || 1.2, s.ancre || "start"));
    }
    if (r !== undefined) { VL.setSelection([id]); VL.toast(parGlyphe ? `${r.length} glyphe(s) en chemins — éditables aux nœuds (annulable)` : "texte vectorisé en un chemin (annulable)"); }
    return r;
  }
  VL.vectoriserTexte = (id, _policeId, parGlyphe = false) => vectoriser(id, parGlyphe);
  async function logo3D() {
    const id = etat.selection[0];
    const t = id && VL.objetDe(id);
    if (t && t.objet.type === "texte") await vectoriser(id, false);
    if (!VL.impression) throw new Error("impression 3D indisponible");
    VL.impression("logo");
  }
  // à l'export : les textes en polices de bibliothèque deviennent des chemins
  VL.textesEnChemins = async (doc) => {
    const remplacer = async (objs) => {
      for (let i = 0; i < (objs || []).length; i++) {
        const o = objs[i];
        if (o.type === "groupe") { await remplacer(o.enfants); continue; }
        if (o.type !== "texte") continue;
        const s = o.style || {}, p = policeParFamille(s.police);
        if (!p || !p.url) continue;
        try {
          const font = await fontDe(p);
          const d = texte_multi_d(font, lignes_de(o.contenu), +s.corps || 16, o.x, o.y, +s.interlettrage || 0, +s.interligne || 1.2, s.ancre || "start");
          if (d) { const st = { ...s, regle: "evenodd" }; for (const k of ["police", "corps", "graisse", "interlettrage", "interligne", "ancre"]) delete st[k]; objs[i] = { id: o.id, type: "path", d, style: st, transform: o.transform }; }
        } catch (e) { /* police muette : le texte reste un texte */ }
      }
    };
    for (const c of doc.calques) await remplacer(c.objets);
    return doc;
  };

  /* ── panneau Texte ── */
  const esc = (v) => String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  let timerContenu = 0;
  function rendre() {
    if (!hote) return;
    if (!etat.doc) { hote.innerHTML = ""; return; }
    const t = etat.selection.length === 1 ? VL.objetDe(etat.selection[0]) : null;
    const o = t && (t.objet.type === "texte" || t.objet.type === "cadre") ? t.objet : null;
    const s = o ? (o.style || {}) : {};
    const familleCourante = o ? s.police : (policeDe(etat.typo.courante) || {}).famille;
    const peutSystem = typeof window.queryLocalFonts === "function";
    hote.innerHTML = `
      ${o ? `<textarea id="txContenu" rows="3" placeholder="Votre texte — Maj+Entrée : nouvelle ligne" title="Le contenu du texte (Entrée dans l'éditeur en place valide)">${esc(o.contenu || "")}</textarea>`
          : `<p class="px-note">Outil Texte (T) : cliquer sur la scène pose un texte et l'édite en place. Double-clic sur un texte pour le rééditer.</p>`}
      <div class="ap-ligne"><span>Police</span><i class="px-note" style="font-family:&quot;${esc(familleCourante || "Segoe UI")}&quot;;font-size:14px">${esc(familleCourante || "—")}</i></div>
      <div class="ap-ligne"><span></span><i class="px-note">se choisit dans le menu du bouton Texte</i></div>
      <div class="ap-ligne"><button id="txDeposer" title="Déposer un fichier TTF / OTF / WOFF : il rejoint la bibliothèque du poste">⬆ Déposer une police…</button>
        <button id="txSysteme" ${peutSystem ? "" : "disabled"} title="${peutSystem ? "Lister les polices installées sur ce poste (permission du navigateur)" : "Ce navigateur ne donne pas ses polices"}">💻 Système…</button></div>
      <input type="file" id="txFichier" accept=".ttf,.otf,.woff,.woff2" hidden/>
      ${o ? `
      <div class="ap-ligne"><span>Corps</span><input type="number" id="txCorps" min="4" max="600" value="${s.corps || 16}"/>
        <select id="txGraisse" title="Graisse">${["normal", "bold", "300", "600", "800"].map((g) => `<option${(s.graisse || "normal") === g ? " selected" : ""}>${g}</option>`).join("")}</select></div>
      <div class="ap-ligne"><span>Espace</span><input type="number" id="txInterlettrage" step="0.5" min="-20" max="60" value="${s.interlettrage || 0}" title="Interlettrage (px)"/>
        <input type="number" id="txInterligne" step="0.05" min="0.5" max="4" value="${s.interligne || 1.2}" title="Interligne (× corps)"/></div>
      <div class="ap-ligne"><span>Ancre</span>${[["start", "⇤"], ["middle", "↔"], ["end", "⇥"]].map(([a, g]) => `<button data-ancre="${a}" class="${(s.ancre || "start") === a ? "actif" : ""}" title="Ancrage ${a === "start" ? "à gauche" : a === "middle" ? "au centre" : "à droite"} du point posé">${g}</button>`).join("")}</div>
      <div class="ap-ligne"><label title="Chaque lettre devient un chemin séparé (déplaçable, éditable aux nœuds, booléen)"><input type="checkbox" id="txParGlyphe"${etat.typo.parGlyphe ? " checked" : ""}/> un chemin par glyphe</label></div>
      <div class="ap-ligne"><button id="txContours" ${o.type === "texte" ? "" : "disabled"} title="Le texte devient ses contours : chemins éditables (outil Nœuds), épaississables, booléens — annulable">◇ Contours</button>
        <button id="txLogo" title="Contours puis Impression 3D en mode logo (biseau, évidement, STL / 3MF)">⬢ Logo 3D</button></div>
      <div class="ap-ligne"><span>Épaissir</span><input type="number" id="txDecal" step="0.5" value="2" title="Décalage du contour (px) : + engraisse, − amaigrit — sur des contours vectorisés"/>
        <button id="txEpaissir" title="Applique un contour ± à la sélection (des chemins)">±</button>
        <button id="txCadre" ${o.type === "texte" ? "" : "disabled"} title="Cadre de texte à paragraphes">→ cadre</button></div>` : ""}
      ${etat.selection.length === 2 ? `<div class="ap-ligne"><button id="txSurChemin" title="Sélectionner le texte PUIS un chemin : le texte suit le chemin">↝ Sur le chemin</button></div>` : ""}`;
    lier(o);
  }
  function lier(o) {
    const on = (id, ev, fn) => { const e = $("#" + id); if (e) e.addEventListener(ev, fn); };
    hote.querySelectorAll("[data-police]").forEach((b) => b.addEventListener("click", () => {
      etat.typo.courante = b.dataset.police;
      const p = policeDe(b.dataset.police);
      if (o && p) VL.executer(op_style, [o.id], { police: p.famille }); else rendre();
    }));
    on("txDeposer", "click", () => $("#txFichier").click());
    on("txFichier", "change", async (ev) => {
      const f = ev.target.files && ev.target.files[0];
      if (!f) return;
      if (!police_fichier_valide(f.name.replace(/\s+/g, "-").replace(/[^A-Za-z0-9_.-]/g, ""), new Uint8Array(await f.slice(0, 12).arrayBuffer()))) { VL.toast("police : TTF / OTF / WOFF attendu", true); return; }
      const fd = new FormData(); fd.append("file", f, f.name);
      const r = await fetch("/api/fonts/upload", { method: "POST", body: fd });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) { VL.toast(d.detail || r.statusText, true); return; }
      VL.toast(`police « ${d.famille} » déposée`);
      etat.typo.courante = "user:" + d.nom;
      await chargerBibliotheque();
      if (o) VL.executer(op_style, [o.id], { police: d.famille });
    });
    on("txSysteme", "click", async () => {
      try {
        const liste = await window.queryLocalFonts();
        etat.typo.systeme = [...new Set(liste.map((f) => f.family))].sort();
        etat.typo.polices = polices_toutes(POLICES, etat.typo.polices.filter((p) => p.source === "user").map((p) => ({ nom: p.fichier })), etat.typo.systeme);
        VL.toast(`${etat.typo.systeme.length} police(s) du système`);
        rendre();
      } catch (e) { VL.toast("polices du système refusées : " + e.message, true); }
    });
    if (!o) return;
    on("txContenu", "input", (ev) => {
      clearTimeout(timerContenu);
      const v = ev.target.value;
      timerContenu = setTimeout(() => VL.executer((doc) => { const t = _profond(doc, o.id); if (t) t.contenu = v; }), 350);
    });
    const st = (patch) => VL.executer(op_style, [o.id], patch);
    on("txCorps", "change", (ev) => st({ corps: Math.max(4, +ev.target.value || 16) }));
    on("txGraisse", "change", (ev) => st({ graisse: ev.target.value === "normal" ? null : ev.target.value }));
    on("txInterlettrage", "change", (ev) => st({ interlettrage: +ev.target.value || 0 }));
    on("txInterligne", "change", (ev) => st({ interligne: Math.max(0.5, +ev.target.value || 1.2) }));
    hote.querySelectorAll("[data-ancre]").forEach((b) => b.addEventListener("click", () => st({ ancre: b.dataset.ancre === "start" ? null : b.dataset.ancre })));
    on("txParGlyphe", "change", (ev) => { etat.typo.parGlyphe = ev.target.checked; });
    on("txContours", "click", () => vectoriser(o.id, etat.typo.parGlyphe).catch((e) => VL.toast(e.message, true)));
    on("txLogo", "click", () => logo3D().catch((e) => VL.toast(e.message, true)));
    on("txEpaissir", "click", () => { const ids = etat.selection.slice(); const r = VL.executer(op_contour, ids, +$("#txDecal").value || 2); if (r) VL.setSelection(r); });
    on("txCadre", "click", () => VL.executer(op_texte_en_cadre, o.id, Math.max(100, (o.contenu || "").length * (+o.style.corps || 16) * 0.6), (+o.style.corps || 16) * 3));
    on("txSurChemin", "click", () => { const [t, c] = etat.selection; VL.executer(op_texte_sur_chemin, t, c); VL.setSelection([t]); });
  }
  const suivantRendu = VL.surRendu;
  VL.surRendu = () => { suivantRendu(); rendre(); };
  const suivantSel = VL.surSelection;
  VL.surSelection = () => { suivantSel(); if (editeur && !etat.selection.includes(editeur.id)) fermerEditeur(true); rendre(); };
  const suivantOutil = VL.surOutil;
  VL.surOutil = () => { suivantOutil(); if (etat.outil === "texte") { const d = $("#texteDetails"); if (d) d.open = true; } rendre(); };
  rendre();
}
