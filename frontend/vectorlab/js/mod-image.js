// mod-image.js — les IMAGES du Vectorlab (lot A, D1) : pose depuis la
// Bibliothèque (sélecteur __dzLibPicker du parent quand il existe, sinon
// une grille de repli sur /api/images), un fichier, le presse-papiers ou
// une génération ; rognage, verrou, opacité ; les repères de page. Le
// raster va au magasin du DOCUMENT (POST /vector/docs/<id>/images), jamais
// en base64 dans le JSON. La logique PURE est en tête (banc node) ;
// initImage ne touche le DOM qu'à l'appel.
import { op_ajouter, op_image_rogner, op_image_verrou, op_reperes,
         reperes_rects } from "./mod-doc.js";

/* ── pur ── */
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;")
  .replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export function href_est_absolu(h) {
  return /^(data:|blob:|https?:|\/)/.test(String(h || ""));
}

export function image_url(docId, href, rev) {
  if (href_est_absolu(href)) return href;
  const v = Number.isInteger(rev) && rev > 0 ? `?v=${rev}` : "";      // lot E : révision raster
  return `/api/vector/docs/${encodeURIComponent(docId)}/images/${encodeURIComponent(href)}${v}`;
}

// la pose par défaut : contenue dans la page (jamais agrandie), centrée
export function image_poser_spec(nat, taille) {
  if (!(nat && nat.w > 0 && nat.h > 0)) throw new Error("image: taille native inconnue");
  const k = Math.min(1, taille.w / nat.w, taille.h / nat.h);
  const w = Math.max(1, Math.round(nat.w * k)), h = Math.max(1, Math.round(nat.h * k));
  return { x: Math.round((taille.w - w) / 2), y: Math.round((taille.h - h) / 2), w, h };
}

// borne une fenêtre à l'image ; null si elle couvre tout (= pas de rognage)
export function rognage_normaliser(r, nat) {
  if (!r) return null;
  const x = Math.min(nat.w - 1, Math.max(0, Math.round(+r.x || 0)));
  const y = Math.min(nat.h - 1, Math.max(0, Math.round(+r.y || 0)));
  const w = Math.max(1, Math.min(nat.w - x, Math.round(+r.w || 0)));
  const h = Math.max(1, Math.min(nat.h - y, Math.round(+r.h || 0)));
  if (x === 0 && y === 0 && w === nat.w && h === nat.h) return null;
  return { x, y, w, h };
}

export function image_hrefs(doc) {
  const out = [];
  const visiter = (objs) => {
    for (const o of objs || []) {
      if (o.type === "image" && !out.includes(o.href)) out.push(o.href);
      if (o.type === "groupe") visiter(o.enfants);
    }
  };
  for (const c of doc.calques || []) visiter(c.objets);
  return out;
}

// lot E : la révision raster la plus haute portée par les objets qui
// référencent `href` (plusieurs objets peuvent partager un PNG)
export function image_rev_max(doc, href) {
  let rev = 0;
  const visiter = (objs) => {
    for (const o of objs || []) {
      if (o.type === "image" && o.href === href && (o.rev | 0) > rev) rev = o.rev | 0;
      if (o.type === "groupe") visiter(o.enfants);
    }
  };
  for (const c of doc.calques || []) visiter(c.objets);
  return rev;
}

export function libListeHTML(images, q) {
  const f = String(q || "").toLowerCase();
  const vus = (images || []).filter((i) => !f || String(i.filename).toLowerCase().includes(f));
  if (!vus.length) {
    return `<p class="lib-vide">Aucune image${f ? ` pour « ${esc(q)} »` : " dans la Bibliothèque"}.</p>`;
  }
  return vus.map((i) => `<button class="lib-carte" data-lib-nom="${esc(i.filename)}"
    title="${esc(i.filename)}${i.width ? ` — ${i.width}×${i.height}` : ""}">
    <img src="/api/images/${encodeURIComponent(i.filename)}" alt="" loading="lazy"/>
    <span>${esc(i.filename)}</span></button>`).join("");
}

/* ── DOM ── */
export function initImage(VL) {
  const { $, etat } = VL;

  VL.imageUrl = (href, rev) => image_url(etat.docId, href, rev);

  async function deposer(png) {
    const r = await fetch(`/api/vector/docs/${encodeURIComponent(etat.docId)}/images`,
      { method: "POST", headers: { "Content-Type": "image/png" }, body: png });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    return d.name;
  }
  function decoder(blob) {
    return new Promise((res, rej) => {
      const url = URL.createObjectURL(blob);
      const im = new Image();
      im.onload = () => { URL.revokeObjectURL(url); res(im); };
      im.onerror = () => { URL.revokeObjectURL(url); rej(new Error("image illisible")); };
      im.src = url;
    });
  }
  // le magasin ne stocke que du PNG : tout autre format est ré-encodé ici
  async function versPNG(blob, im) {
    if (blob.type === "image/png") return blob;
    const cv = document.createElement("canvas");
    cv.width = im.naturalWidth; cv.height = im.naturalHeight;
    cv.getContext("2d").drawImage(im, 0, 0);
    return new Promise((res, rej) => cv.toBlob((b) => b ? res(b)
      : rej(new Error("ré-encodage PNG impossible")), "image/png"));
  }
  async function poserBlob(blob) {
    if (!etat.docId) throw new Error("aucun document ouvert");
    const im = await decoder(blob);
    const nat = { w: im.naturalWidth, h: im.naturalHeight };
    const png = await versPNG(blob, im);
    const href = await deposer(png);
    const spec = image_poser_spec(nat, etat.doc.taille);
    const id = VL.executer(op_ajouter, etat.calqueActif,
      { type: "image", ...spec, href, nat, style: {} });
    if (id) { VL.setOutil("select"); VL.setSelection([id]); }
    return id;
  }
  async function poserDepuisLibrary(nom) {
    const r = await fetch("/api/images/" + encodeURIComponent(nom));
    if (!r.ok) throw new Error(`Bibliothèque : ${nom} introuvable (${r.status})`);
    await poserBlob(await r.blob());
    VL.toast(`« ${nom} » posée`);
  }

  /* ── Bibliothèque : le sélecteur du parent, sinon la grille de repli ── */
  let libImages = null;
  async function ouvrirBiblio() {
    const parent = window.parent !== window ? window.parent : null;
    let picker = null;
    try { picker = parent && typeof parent.__dzLibPicker === "function" ? parent.__dzLibPicker : null; }
    catch (e) { picker = null; }             // parent d'une autre origine : repli
    if (picker) {
      picker({ titre: "Poser une image dans le Vectorlab" },
        (nom) => poserDepuisLibrary(nom).catch((e) => VL.toast(e.message, true)));
      return;
    }
    const dlg = $("#libDlg");
    dlg.classList.remove("hidden");
    $("#libRecherche").value = "";
    $("#libGrille").innerHTML = `<p class="lib-vide">chargement…</p>`;
    const d = await VL.api.get("/images");
    libImages = (d.images || []).slice().sort((a, b) => (b.mtime || 0) - (a.mtime || 0));
    $("#libGrille").innerHTML = libListeHTML(libImages, "");
  }
  $("#libRecherche").addEventListener("input", () => {
    $("#libGrille").innerHTML = libListeHTML(libImages || [], $("#libRecherche").value);
  });
  $("#libGrille").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-lib-nom]");
    if (!b) return;
    $("#libDlg").classList.add("hidden");
    poserDepuisLibrary(b.dataset.libNom).catch((e) => VL.toast(e.message, true));
  });
  $("#libFermer").addEventListener("click", () => $("#libDlg").classList.add("hidden"));

  /* ── panneau Assets (lot C) : la Bibliothèque en permanence dans le
     panneau, un clic pose l'image — chargée à l'ouverture du volet ── */
  const det = $("#assetsDetails");
  let assets = null;
  async function chargerAssets() {
    $("#assetsGrille").innerHTML = `<p class="lib-vide">chargement…</p>`;
    const d = await VL.api.get("/images");
    assets = (d.images || []).slice().sort((a, b) => (b.mtime || 0) - (a.mtime || 0));
    $("#assetsGrille").innerHTML = libListeHTML(assets, $("#assetsRecherche").value);
  }
  det.addEventListener("toggle", () => {
    if (det.open && !assets) chargerAssets().catch((e) => VL.toast(e.message, true));
  });
  $("#assetsRecherche").addEventListener("input", () => {
    $("#assetsGrille").innerHTML = libListeHTML(assets || [], $("#assetsRecherche").value);
  });
  $("#assetsGrille").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-lib-nom]");
    if (!b) return;
    poserDepuisLibrary(b.dataset.libNom).catch((e) => VL.toast(e.message, true));
  });
  VL.poserDepuisLibrary = poserDepuisLibrary;
  VL.chargerAssets = chargerAssets;

  /* ── fichier ── */
  const inputFichier = $("#imgFichierInput");
  inputFichier.addEventListener("change", () => {
    const f = inputFichier.files && inputFichier.files[0];
    inputFichier.value = "";
    if (f) poserBlob(f).then(() => VL.toast(`« ${f.name} » posée`))
                       .catch((e) => VL.toast(e.message, true));
  });

  /* ── presse-papiers : Ctrl+V d'une image, et le bouton (clipboard.read) ── */
  document.addEventListener("paste", (ev) => {
    if (!etat.docId) return;
    if (/^(INPUT|TEXTAREA)$/.test(document.activeElement?.tagName || "")) return;
    const items = [...((ev.clipboardData && ev.clipboardData.items) || [])];
    const it = items.find((i) => i.type.startsWith("image/"));
    if (!it) return;                       // pas une image : le coller interne garde la main
    ev.preventDefault();
    poserBlob(it.getAsFile()).then(() => VL.toast("image du presse-papiers posée"))
      .catch((e) => VL.toast(e.message, true));
  });
  async function collerImage() {
    if (!navigator.clipboard || !navigator.clipboard.read) {
      throw new Error("presse-papiers : utiliser Ctrl+V sur la scène");
    }
    for (const item of await navigator.clipboard.read()) {
      const t = item.types.find((x) => x.startsWith("image/"));
      if (t) { await poserBlob(await item.getType(t)); VL.toast("image du presse-papiers posée"); return; }
    }
    throw new Error("le presse-papiers ne contient pas d'image");
  }

  /* ── génération : la route existante, la clé dépensée est dite ── */
  async function generer() {
    const p = prompt("Décrire l'image à générer (dépense la clé du fournisseur des Réglages) :", "");
    if (!p) return;
    VL.toast("génération en cours…");
    const r = await fetch("/api/images/generate", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: p, n: 1, source: "vectorlab" }) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || r.statusText);
    const nom = (d.images || [])[0];
    if (!nom) throw new Error("la génération n'a rendu aucune image");
    await poserDepuisLibrary(nom);
  }

  /* ── le menu ── */
  const menu = $("#imgMenu");
  $("#btnImage").addEventListener("click", () => menu.classList.toggle("hidden"));
  const garde = (fn) => () => {
    menu.classList.add("hidden");
    Promise.resolve().then(fn).catch((e) => VL.toast(e.message, true));
  };
  $("#imgBiblio").addEventListener("click", garde(ouvrirBiblio));
  $("#imgFichier").addEventListener("click", garde(() => inputFichier.click()));
  $("#imgColler").addEventListener("click", garde(collerImage));
  $("#imgGenerer").addEventListener("click", garde(generer));
  $("#imgVectoriser").addEventListener("click", garde(() => {
    if (VL.vectoriser) VL.vectoriser(imageCible());
  }));

  /* ── l'image cible d'une action : la sélection, sinon l'unique image ── */
  function imagesDuDoc() {
    const out = [];
    for (const c of etat.doc.calques) for (const o of c.objets) if (o.type === "image") out.push(o);
    return out;
  }
  function imageCible() {
    const t = etat.selection.length === 1 ? VL.objetDe(etat.selection[0]) : null;
    if (t && t.objet.type === "image") return t.objet.id;
    const toutes = imagesDuDoc();
    if (toutes.length === 1) return toutes[0].id;
    if (!toutes.length) throw new Error("aucune image dans le document — Image ▾ pour en poser une");
    const rep = prompt("Quelle image ?\n" + toutes.map((o, i) =>
      `${i + 1}) ${o.id} — ${o.href} (${o.nat.w}×${o.nat.h})`).join("\n"), "1");
    if (rep === null) throw new Error("annulé");
    const o = toutes[(+rep || 0) - 1];
    if (!o) throw new Error("numéro inconnu");
    return o.id;
  }

  /* ── panneau Image (sélection unique d'une image) ── */
  const hote = $("#panneauImage"), tete = $("#teteImage");
  function rendrePanneauImage() {
    const t = etat.selection.length === 1 ? VL.objetDe(etat.selection[0]) : null;
    const o = t && t.objet.type === "image" ? t.objet : null;
    tete.hidden = !o; hote.hidden = !o;
    if (!o) { hote.innerHTML = ""; return; }
    const r = o.rognage || { x: 0, y: 0, w: o.nat.w, h: o.nat.h };
    hote.innerHTML = `
      <div class="ap-ligne"><span>Source</span><i class="img-src" title="${esc(o.href)}">${esc(o.href)} · ${o.nat.w}×${o.nat.h}</i></div>
      <div class="ap-ligne"><span>Rogner</span>
        <input type="number" id="imRx" min="0" value="${r.x}" title="X de la fenêtre (px de l'image)"/>
        <input type="number" id="imRy" min="0" value="${r.y}" title="Y de la fenêtre"/></div>
      <div class="ap-ligne"><span></span>
        <input type="number" id="imRw" min="1" value="${r.w}" title="Largeur de la fenêtre"/>
        <input type="number" id="imRh" min="1" value="${r.h}" title="Hauteur de la fenêtre"/>
        <button id="imRognerRaz" title="Image entière">↺</button></div>
      <div class="ap-ligne"><span>Verrou</span>
        <button id="imVerrou" class="${o.verrou ? "actif" : ""}" title="Verrouillé : aucune commande ne bouge, ne redimensionne ni ne supprime l'image">${o.verrou ? "🔒 verrouillée" : "🔓 libre"}</button>
        <button id="imVectoriser" title="Vectoriser cette image en aplats de couleur (aperçu avant validation)">Vectoriser…</button></div>`;
    const lireRognage = () => rognage_normaliser({ x: +$("#imRx").value, y: +$("#imRy").value,
      w: +$("#imRw").value, h: +$("#imRh").value }, o.nat);
    for (const id of ["imRx", "imRy", "imRw", "imRh"]) {
      $("#" + id).addEventListener("change", () => VL.executer(op_image_rogner, o.id, lireRognage()));
    }
    $("#imRognerRaz").addEventListener("click", () => VL.executer(op_image_rogner, o.id, null));
    $("#imVerrou").addEventListener("click", () => VL.executer(op_image_verrou, o.id, !o.verrou));
    $("#imVectoriser").addEventListener("click", () => { if (VL.vectoriser) VL.vectoriser(o.id); });
  }

  /* ── panneau Repères : deux retraits uniformes dans l'unité d'affichage ── */
  const hoteRep = $("#panneauReperes");
  function rendrePanneauReperes() {
    if (!etat.doc) { hoteRep.innerHTML = ""; return; }
    const r = etat.doc.reperes || {};
    const nv = (v) => v === undefined ? "" : Math.round(VL.versUnite(v[0]) * 100) / 100;
    const suf = VL.unites().affichage;
    hoteRep.innerHTML = `
      <div class="ap-ligne"><span>Coupe</span>
        <input type="number" id="repFond" step="any" min="0" value="${nv(r.fondPerdu)}" placeholder="—"
               title="Fond perdu : retrait de la ligne de coupe depuis le bord (${suf}) — vide = aucun"/>
        <i class="rep-pastille rep-fond"></i></div>
      <div class="ap-ligne"><span>Zone sûre</span>
        <input type="number" id="repSure" step="any" min="0" value="${nv(r.zoneSure)}" placeholder="—"
               title="Zone sûre : retrait depuis le bord (${suf}) — vide = aucune"/>
        <i class="rep-pastille rep-sure"></i></div>`;
    const lire = (id) => { const v = $("#" + id).value.trim(); return v === "" ? null : VL.depuisUnite(+v); };
    $("#repFond").addEventListener("change", () => VL.executer(op_reperes, { fondPerdu: lire("repFond") }));
    $("#repSure").addEventListener("change", () => VL.executer(op_reperes, { zoneSure: lire("repSure") }));
  }

  const suivantRendu = VL.surRendu;
  VL.surRendu = () => { suivantRendu(); rendrePanneauImage(); rendrePanneauReperes(); };
  const suivantSel = VL.surSelection;
  VL.surSelection = () => { suivantSel(); rendrePanneauImage(); };
  VL.poserBlob = poserBlob;                 // la preuve et la vectorisation
  VL.reperesRects = () => reperes_rects(etat.doc);
}
