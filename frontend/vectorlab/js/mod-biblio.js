// mod-biblio.js — la page d'accueil bibliothèque (chantier 27/08) : sans
// `?doc`, le Vectorlab liste TOUS les documents (recherche, filtre rôle,
// vignettes phase 6), en crée (POST), en ouvre (?doc=), duplique et
// supprime (DELETE = archive). La logique PURE est en tête (bancable en
// node) ; initBiblio ne touche le DOM qu'à l'appel.

/* ── pur ── */
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;")
  .replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export function parseTaille(texte) {
  const m = /^\s*(\d+)\s*[x×X]\s*(\d+)\s*$/.exec(String(texte || ""));
  if (!m) throw new Error("taille attendue « L×H » en px, ex. 640×960");
  const w = +m[1], h = +m[2];
  if (!(w > 0) || !(h > 0)) throw new Error("taille : dimensions positives requises");
  if (w > 8192 || h > 8192) throw new Error("taille : 8192 px de côté au plus");
  return { w, h };
}

export function docVierge(nom, w, h, unites) {
  const doc = {
    v: 1, nom: String(nom || "Sans titre"), taille: { w, h },
    calques: [{ id: "c1", nom: "calque 1", visible: true, verrou: false,
                objets: [] }],
  };
  if (unites) doc.unites = { affichage: unites.affichage, dpi: unites.dpi };
  return doc;
}

/* ── formats de document (éditeur complet, E5) : les physiques posent
   mm/300 dpi et calculent les px ; les px posent px/96 ; « libre » lit
   la taille saisie ── */
export const FORMATS = [
  { id: "libre", libelle: "Libre (px)" },
  { id: "carre", libelle: "Carré — 2048×2048", w: 2048, h: 2048 },
  { id: "16x9", libelle: "16:9 — 1920×1080", w: 1920, h: 1080 },
  { id: "9x16", libelle: "9:16 — 1080×1920", w: 1080, h: 1920 },
  { id: "a4p", libelle: "A4 portrait — 210×297 mm", mm: [210, 297] },
  { id: "a4l", libelle: "A4 paysage — 297×210 mm", mm: [297, 210] },
  { id: "a5p", libelle: "A5 — 148×210 mm", mm: [148, 210] },
  { id: "carte", libelle: "Carte (poker) — 63,5×88,9 mm", mm: [63.5, 88.9] },
  { id: "vitrail", libelle: "Vitrail — 640×960", w: 640, h: 960 },
];

export function formatVersDoc(id, tailleTexte) {
  const f = FORMATS.find((x) => x.id === id);
  if (!f) throw new Error(`format inconnu : ${id}`);
  if (f.mm) {
    const dpi = 300;
    const px = (mm) => Math.round(mm / 25.4 * dpi);
    return { w: px(f.mm[0]), h: px(f.mm[1]),
             unites: { affichage: "mm", dpi } };
  }
  const unites = { affichage: "px", dpi: 96 };
  if (f.w) return { w: f.w, h: f.h, unites };
  const t = parseTaille(tailleTexte);
  return { w: t.w, h: t.h, unites };
}

function badge(d) {
  if (d.chapter_id) return "⚓ chapitre";
  if (d.deck_id) return "🂠 cartes";
  return "◇ bibliothèque";
}

export function bibLigne(d) {
  const id = esc(d.id);
  const vig = d.vignette
    ? `<img src="/api/vector/docs/${encodeURIComponent(d.id)}/vignette.png?v=${
        encodeURIComponent(d.version)}" alt="" loading="lazy"/>`
    : `<span class="bib-sans" title="la vignette naît au premier Sauver">◧</span>`;
  return `<div class="bib-carte" data-bib-id="${id}">`
    + `<div class="bib-vig">${vig}</div>`
    + `<div class="bib-nom" title="${esc(d.name)}">${esc(d.name)}</div>`
    + `<div class="bib-meta">${esc(d.role)} · v${esc(d.version)} · ${badge(d)}</div>`
    + `<div class="bib-actions">`
    + `<button data-bib-open="${id}" title="Ouvrir dans l'éditeur">Ouvrir</button>`
    + `<button data-bib-dup="${id}" title="Copie indépendante (le contenu courant du disque)">Dupliquer</button>`
    + `<button data-bib-del="${id}" title="Supprime l'entrée — la dernière version reste archivée sur disque">Supprimer</button>`
    + `</div></div>`;
}

export function bibVide(q, role) {
  const filtres = [];
  if (q) filtres.push(`la recherche « ${esc(q)} »`);
  if (role) filtres.push(`le rôle ${esc(role)}`);
  return filtres.length
    ? `Aucun document pour ${filtres.join(" et ")}.`
    : "Aucun document — crée le premier avec la rangée ci-dessus.";
}

/* ── DOM (seulement à l'appel — jamais au chargement du module) ── */
export function initBiblio(VL) {
  const { $, etat } = VL;
  let debounce = null;

  async function rafraichir() {
    const q = $("#bibRecherche").value.trim();
    const role = $("#bibRole").value;
    const ps = new URLSearchParams();
    if (q) ps.set("q", q);
    if (role) ps.set("role", role);
    try {
      const d = await VL.api.get("/vector/docs" + (ps.size ? "?" + ps : ""));
      const docs = d.docs || [];
      $("#bibListe").innerHTML = docs.length
        ? docs.map(bibLigne).join("")
        : `<p class="bib-vide">${bibVide(q, role)}</p>`;
    } catch (e) {
      $("#bibListe").innerHTML =
        `<p class="bib-vide">erreur : ${esc(e.message)}</p>`;
    }
  }

  function ouvrir(id) {
    location.href = "?doc=" + encodeURIComponent(id);
  }

  async function creer() {
    let spec;
    try {
      spec = formatVersDoc($("#bibNouvFormat").value,
                           $("#bibNouvTaille").value);
    } catch (e) { VL.toast(e.message, true); return; }
    const nom = $("#bibNouvNom").value.trim() || "Sans titre";
    const r = await fetch("/api/vector/docs", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: nom, role: $("#bibNouvRole").value,
                             doc: docVierge(nom, spec.w, spec.h,
                                            spec.unites) }),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) { VL.toast(d.detail || r.statusText, true); return; }
    ouvrir(d.id);
  }

  function majFormat() {
    const id = $("#bibNouvFormat").value;
    const taille = $("#bibNouvTaille");
    if (id === "libre") { taille.disabled = false; return; }
    const spec = formatVersDoc(id);
    taille.value = `${spec.w}×${spec.h}`;
    taille.disabled = true;
  }

  async function dupliquer(id) {
    const nom = prompt("Nom de la copie ? (vide = « (copie) »)", "");
    if (nom === null) return;
    const r = await fetch("/api/vector/docs/" + encodeURIComponent(id)
      + "/duplicate", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(nom.trim() ? { name: nom.trim() } : {}),
    });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) { VL.toast(d.detail || r.statusText, true); return; }
    await rafraichir();
  }

  async function supprimer(id) {
    if (!confirm("Supprimer ce document ? Sa dernière version reste "
                 + "archivée sur disque.")) return;
    const r = await fetch("/api/vector/docs/" + encodeURIComponent(id),
                          { method: "DELETE" });
    if (!r.ok) { VL.toast("suppression : " + r.status, true); return; }
    await rafraichir();
  }

  $("#bibListe").addEventListener("click", (ev) => {
    const b = ev.target.closest("button");
    if (!b) {
      const carte = ev.target.closest(".bib-carte");
      if (carte) ouvrir(carte.dataset.bibId);
      return;
    }
    if (b.dataset.bibOpen) ouvrir(b.dataset.bibOpen);
    else if (b.dataset.bibDup) dupliquer(b.dataset.bibDup);
    else if (b.dataset.bibDel) supprimer(b.dataset.bibDel);
  });
  $("#bibRecherche").addEventListener("input", () => {
    clearTimeout(debounce);
    debounce = setTimeout(rafraichir, 300);
  });
  $("#bibRole").addEventListener("change", rafraichir);
  // le select des formats est peuplé depuis la table (jamais recopié)
  $("#bibNouvFormat").innerHTML = FORMATS.map((f) =>
    `<option value="${f.id}">${esc(f.libelle)}</option>`).join("");
  $("#bibNouvFormat").addEventListener("change", majFormat);
  $("#bibCreer").addEventListener("click", () =>
    creer().catch((e) => VL.toast(e.message, true)));
  $("#bibNouvNom").addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") $("#bibCreer").click();
  });

  // le retour ⌂ depuis l'éditeur — confirm si le document est sale
  $("#btnBiblio").addEventListener("click", () => {
    if (etat.sale && !confirm("Des modifications non sauvées seront "
                              + "perdues — retourner à la bibliothèque ?")) {
      return;
    }
    location.href = "/vectorlab/";
  });

  VL.ouvrirBiblio = async () => {
    document.body.classList.add("mode-biblio");
    $("#docTitle").textContent = "Vectorlab";
    $("#docMeta").textContent = "bibliothèque des documents";
    await rafraichir();
  };
}
