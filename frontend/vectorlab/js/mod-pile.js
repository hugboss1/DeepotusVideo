// mod-pile.js — la pile de droite d'Affinity (R3) : trois groupes de
// panneaux à onglets par persona. Les sections <details id="…Details">
// EXISTANTES sont déplacées dans le groupe de leur onglet (leur summary
// est masqué, l'onglet actif = section ouverte — mod-panneaux continue
// de mémoriser l'état) ; les rangées du panneau Apparence sont
// redistribuées par libellé vers Transformer et Trait APRÈS chaque rendu
// (les écouteurs suivent les nœuds déplacés) ; Échantillons et Navigateur
// sont rendus ici. `VL.ouvrirOnglet(id)` : les menus (R1) l'appellent.
import { ONGLETS, onglets_de, onglet_de_section, actif_lire, actif_poser, actif_de, sections_ouvertes, actif_serialiser } from "./mod-onglets.js";
import { echelle_vignette, cadre_vue, zoom_de_curseur, curseur_de_zoom } from "./mod-navigateur.js";
import { compilerSVG, op_style } from "./mod-doc.js";

const VERS_TRANSFORMER = ["X · Y", "L · H", "Incliner", "Puissance"];
const VERS_TRAIT = ["Contour", "Trait", "Pointillés", "Joint", "Décaler"];
const CLE = "dz_vl_onglets";

export function initPile(VL) {
  const { $, etat } = VL;
  const pile = $("#panneauCalques");
  if (!pile) return;
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
  let actifs = actif_lire(null);
  try { actifs = actif_lire(localStorage.getItem(CLE)); } catch (e) { /* stockage indisponible */ }
  const persona = () => etat.persona || "vecteur";

  /* ── les trois groupes ── */
  const groupes = [0, 1, 2].map((i) => {
    const g = document.createElement("div");
    g.className = "groupe"; g.dataset.g = i;
    g.innerHTML = `<div class="onglets"></div><button class="groupe-repli" title="Replier / déplier ce groupe">⌄</button><div class="groupe-corps"></div>`;
    g.querySelector(".groupe-repli").addEventListener("click", () => g.classList.toggle("replie"));
    pile.appendChild(g);
    return g;
  });
  const section = (id) => document.getElementById(id);

  function rendreOnglets() {
    const p = persona();
    const liste = onglets_de(p), act = actif_de(actifs, p), ouvertes = new Set(sections_ouvertes(actifs, p));
    liste.forEach((ids, i) => {
      const g = groupes[i], corps = g.querySelector(".groupe-corps"), rangee = g.querySelector(".onglets");
      rangee.innerHTML = ids.map((id) => `<button class="onglet${id === act[i] ? " actif" : ""}" data-onglet="${id}" title="${esc(ONGLETS[id].libelle)}">${esc(ONGLETS[id].libelle)}</button>`).join("");
      rangee.querySelectorAll(".onglet").forEach((b) => b.addEventListener("click", () => activer(b.dataset.onglet)));
      for (const id of ids) for (const sid of ONGLETS[id].sections) { const d = section(sid); if (d) corps.appendChild(d); }
    });
    // toutes les sections connues des onglets : ouvertes si leur onglet est actif, fermées sinon
    for (const x of Object.values(ONGLETS)) for (const sid of x.sections) { const d = section(sid); if (d) d.open = ouvertes.has(sid); }
    // les sections d'onglets absents de ce persona restent dans leur groupe précédent, fermées : les cacher
    const visibles = new Set(liste.flat().flatMap((id) => ONGLETS[id].sections));
    for (const x of Object.values(ONGLETS)) for (const sid of x.sections) { const d = section(sid); if (d) d.classList.toggle("hors-persona", !visibles.has(sid)); }
    rendreNavigateur();
  }
  function activer(id) {
    const p = persona();
    const i = onglets_de(p).findIndex((g) => g.includes(id));
    if (i < 0) return false;
    actifs = actif_poser(actifs, p, i, id);
    try { localStorage.setItem(CLE, actif_serialiser(actifs)); } catch (e) { /* stockage indisponible */ }
    groupes[i].classList.remove("replie");
    rendreOnglets();
    return true;
  }
  // un onglet absent du persona courant mais présent dans l'autre : on y bascule (Pixel, Trait…)
  VL.ouvrirOnglet = (id) => {
    if (!ONGLETS[id]) return false;
    if (!onglets_de(persona()).some((g) => g.includes(id))) {
      const autre = Object.keys(actifs).find((p) => p !== persona() && onglets_de(p).some((g) => g.includes(id)));
      if (autre && VL.setPersona) VL.setPersona(autre); else return false;
    }
    return activer(id);
  };
  VL.onglets = { actifs: () => actifs, activer, groupes: () => groupes, ouvertes: () => sections_ouvertes(actifs, persona()) };   // la preuve

  /* ── Apparence → Transformer / Trait : par libellé de rangée ── */
  function redistribuer() {
    const src = $("#panneauStyle"), t = $("#panneauTransformer"), tr = $("#panneauTrait");
    if (!src || !t || !tr) return;
    t.innerHTML = ""; tr.innerHTML = "";
    for (const ligne of [...src.querySelectorAll(":scope > .ap-ligne")]) {
      const lib = (ligne.querySelector(":scope > span:first-child") || {}).textContent || "";
      const l = lib.trim();
      if (VERS_TRANSFORMER.includes(l)) t.appendChild(ligne);
      else if (VERS_TRAIT.includes(l)) tr.appendChild(ligne);
    }
    if (!t.children.length) t.innerHTML = `<p class="px-note">Sélectionner un objet : position, taille, inclinaison et duplication en puissance.</p>`;
    if (!tr.children.length) tr.innerHTML = `<p class="px-note">Le contour de la sélection ou des prochains objets.</p>`;
  }

  /* ── Échantillons : la palette du document ── */
  function rendreEchantillons() {
    const h = $("#panneauEchantillons");
    if (!h) return;
    const pal = (etat.doc && etat.doc.palette) || [];
    h.innerHTML = pal.length
      ? `<div class="ech-grille">${pal.map((c) => `<button class="ech-case" data-hex="${esc(c)}" style="background:${esc(c)}" title="${esc(c)} — clic : fond de la sélection · Maj+clic : contour"></button>`).join("")}</div><p class="px-note">La palette du document (＋ dans le nuancier pour y ajouter).</p>`
      : `<p class="px-note">Aucun échantillon — le nuancier (pastille Fond) ajoute une couleur à la palette du document.</p>`;
    h.querySelectorAll(".ech-case").forEach((b) => b.addEventListener("click", (ev) => {
      const patch = ev.shiftKey ? { contour: b.dataset.hex } : { fond: b.dataset.hex };
      if (etat.selection.length) VL.executer(op_style, etat.selection.slice(), patch);
      else { Object.assign(etat.styleCourant, patch); VL.surSelection(); }
    }));
  }

  /* ── Navigateur : vignette, cadre de vue, curseur de zoom ── */
  const NAV_W = 236, NAV_H = 148;
  function rendreNavigateur() {
    const h = $("#panneauNavigateur");
    if (!h) return;
    if (!etat.doc) { h.innerHTML = `<p class="px-note">Aucun document.</p>`; return; }
    if (!h.querySelector(".nav-vignette")) {
      h.innerHTML = `<div class="nav-vignette" style="width:${NAV_W}px;height:${NAV_H}px"><div class="nav-page"></div><div class="nav-cadre"></div></div>
        <div class="ap-ligne nav-zoom"><button id="navMoins" title="Zoom arrière">−</button><input id="navZoom" type="range" min="0" max="1000" value="500" title="Zoom"/><button id="navPlus" title="Zoom avant">+</button><b id="navPct">100 %</b></div>`;
      const poser = (z) => { const r = $("#stage").getBoundingClientRect(); const cx = r.width / 2, cy = r.height / 2; etat.tx = cx - (cx - etat.tx) * (z / etat.zoom); etat.ty = cy - (cy - etat.ty) * (z / etat.zoom); etat.zoom = z; VL.appliquerVue(); };
      h.querySelector("#navZoom").addEventListener("input", (ev) => poser(zoom_de_curseur(ev.target.value)));
      h.querySelector("#navMoins").addEventListener("click", () => poser(Math.max(0.05, etat.zoom / 1.25)));
      h.querySelector("#navPlus").addEventListener("click", () => poser(Math.min(16, etat.zoom * 1.25)));
      h.querySelector(".nav-vignette").addEventListener("pointerdown", (ev) => {
        const e = echelle_vignette(etat.doc.taille, NAV_W, NAV_H); if (!e.k) return;
        const rv = ev.currentTarget.getBoundingClientRect(), r = $("#stage").getBoundingClientRect();
        const dx = (ev.clientX - rv.left - e.ox) / e.k, dy = (ev.clientY - rv.top - e.oy) / e.k;   // point document cliqué → centre de la scène
        etat.tx = r.width / 2 - dx * etat.zoom; etat.ty = r.height / 2 - dy * etat.zoom; VL.appliquerVue();
      });
    }
    const e = echelle_vignette(etat.doc.taille, NAV_W, NAV_H);
    const page = h.querySelector(".nav-page");
    if (page.dataset.rev !== String(etat.histo._avant.length) + ":" + etat.doc.calques.length) {
      page.dataset.rev = String(etat.histo._avant.length) + ":" + etat.doc.calques.length;
      let svg = "";
      try { svg = compilerSVG(etat.doc, { image: VL.imageUrl, mesure: VL.mesureTexte }).replace(/ data-objet="[^"]*"/g, "").replace(/ id="([^"]+)"/g, ' id="nav_$1"').replace(/url\(#([^)]+)\)/g, "url(#nav_$1)").replace(/href="#([^"]+)"/g, 'href="#nav_$1"'); } catch (err) { svg = ""; }
      page.innerHTML = svg;
    }
    page.style.left = e.ox + "px"; page.style.top = e.oy + "px"; page.style.width = (etat.doc.taille.w * e.k) + "px"; page.style.height = (etat.doc.taille.h * e.k) + "px";
    const svgEl = page.querySelector("svg"); if (svgEl) { svgEl.setAttribute("width", etat.doc.taille.w * e.k); svgEl.setAttribute("height", etat.doc.taille.h * e.k); }
    const r = $("#stage").getBoundingClientRect();
    const c = cadre_vue(etat.doc.taille, { zoom: etat.zoom, tx: etat.tx, ty: etat.ty }, { w: r.width, h: r.height }, e);
    const cadre = h.querySelector(".nav-cadre");
    if (c) { cadre.style.left = c.x + "px"; cadre.style.top = c.y + "px"; cadre.style.width = c.w + "px"; cadre.style.height = c.h + "px"; cadre.hidden = false; } else cadre.hidden = true;
    const z = h.querySelector("#navZoom"); if (z && document.activeElement !== z) z.value = curseur_de_zoom(etat.zoom);
    h.querySelector("#navPct").textContent = Math.round(etat.zoom * 100) + " %";
  }

  /* ── crochets : après TOUS les rendus des modules (initPile est le dernier) ── */
  const sRendu = VL.surRendu, sSel = VL.surSelection, sVue = VL.surVue, sPersona = VL.surPersona;
  VL.surRendu = () => { sRendu(); redistribuer(); rendreEchantillons(); rendreNavigateur(); };
  VL.surSelection = () => { sSel(); redistribuer(); };
  VL.surVue = () => { sVue(); rendreNavigateur(); };
  VL.surPersona = () => { sPersona(); rendreOnglets(); };
  rendreOnglets(); redistribuer(); rendreEchantillons();
}
