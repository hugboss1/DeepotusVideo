// mod-importerui.js — lot D4 « Interop », T2 (t470 ; plan 2026-11-09-vectorlab-d4-import.md) : faire entrer un SVG
// dans le document. Trois chemins mènent au même import (importer_actions().texte) :
//   * Fichier › Importer (SVG, PDF)… : un sélecteur de fichier (action « importer » de mod-charpente) ;
//   * un SVG COLLÉ (copie d'Illustrator, de Figma, d'un éditeur de texte) : image/svg+xml ou texte qui commence par <svg ;
//   * un fichier SVG DÉPOSÉ sur la toile, posé au point de dépôt.
// Les images data: du SVG entrent au magasin du document (VL.deposerBlob) avant l'opération, qui reste pure ; un PDF
// est confié à VL.importerPdf (T4). Le bilan tient en une ligne : objets importés, puis ce qui n'est pas repris.
import { T } from "./mod-i18n.js";
import { svg_vers_objets, op_importer_svg } from "./mod-importsvg.js";

// les raisons, dans l'ordre du bilan (clés écrites en entier : le banc i18n suit chaque clé T())
const RAISONS = {
  cache: "vectorlab.importer.r_cache", image: "vectorlab.importer.r_image", inconnu: "vectorlab.importer.r_inconnu",
  filtre: "vectorlab.importer.r_filtre", decoupe: "vectorlab.importer.r_decoupe", masque: "vectorlab.importer.r_masque",
  degrade: "vectorlab.importer.r_degrade", use: "vectorlab.importer.r_use", chemin: "vectorlab.importer.r_chemin",
};

export function bilan_import(stats) {
  const ign = (stats && stats.ignores) || {};
  const liste = Object.keys(RAISONS).filter((r) => ign[r] > 0).map((r) => `${T(RAISONS[r])} (${ign[r]})`);
  const tete = T("vectorlab.importer.bilan", { n: (stats && stats.importes) || 0 });
  return liste.length ? T("vectorlab.importer.non_repris", { bilan: tete, liste: liste.join(", ") }) : tete;
}

// un texte est un SVG s'il COMMENCE par <svg, une fois retirés BOM, blancs, déclaration XML, commentaires et DOCTYPE
export function est_svg(texte) {
  let s = String(texte || "");   // \s couvre aussi le BOM
  for (;;) {
    const avant = s;
    s = s.replace(/^\s+/, "").replace(/^<\?[\s\S]*?\?>/, "").replace(/^<!--[\s\S]*?-->/, "").replace(/^<!DOCTYPE[^>]*>/i, "");
    if (s === avant) break;
  }
  return /^<svg[\s>/]/i.test(s);
}

export function type_fichier(nom, type) {
  const n = String(nom || "").toLowerCase(), t = String(type || "").toLowerCase();
  if (t === "image/svg+xml" || n.endsWith(".svg")) return "svg";
  if (t === "application/pdf" || n.endsWith(".pdf")) return "pdf";
  return null;
}

export function svg_du_presse_papiers(cp) {
  if (!cp) return null;
  const types = [...(cp.types || [])];
  if (types.includes("image/svg+xml")) { const s = cp.getData("image/svg+xml"); if (s) return s; }
  if (types.includes("text/plain")) { const s = cp.getData("text/plain"); if (est_svg(s)) return s; }
  return null;
}

export function importer_actions(VL) {
  const etat = VL.etat;
  const dire = (e) => { VL.toast(e.message, true); return undefined; };

  // les images data: entrent au magasin du document ; leur taille naturelle est la vraie
  async function deposerImages(objets) {
    for (const o of objets) {
      if (o.type === "groupe") await deposerImages(o.enfants || []);
      else if (o.type === "image" && o.nat_provisoire) {
        const blob = await (await fetch(o.href)).blob();
        const d = await VL.deposerBlob(blob);
        o.href = d.href; o.nat = d.nat; delete o.nat_provisoire;
      }
    }
  }

  async function texte(svg, nom, pos = {}) {
    try {
      if (!etat.doc) throw new Error(T("vectorlab.importer.aucun_doc"));
      const a = svg_vers_objets(svg);
      await deposerImages(a.objets);
      const id = VL.executer(op_importer_svg, a, { calque: etat.calqueActif, x: pos.x, y: pos.y });
      if (!id) return undefined;                     // executer a déjà dit l'erreur (calque verrouillé…)
      VL.setOutil("select");
      VL.setSelection([id]);
      VL.toast(bilan_import(a.stats));
      return id;
    } catch (e) { return dire(e); }
  }

  async function fichier(f, pos) {
    const genre = type_fichier(f && f.name, f && f.type);
    if (genre === "svg") return texte(await f.text(), f.name, pos);
    if (genre === "pdf" && VL.importerPdf) return VL.importerPdf(f, pos || {});
    return dire(new Error(T("vectorlab.importer.type_inconnu")));
  }

  const ACTIONS = {
    importer: { peut: () => !!etat.doc, faire: () => A.ouvrir() },
  };
  const A = {
    texte, fichier,
    ouvrir() { if (A.entree) A.entree.click(); },
    action: (nom) => ACTIONS[nom] || { peut: () => false, faire: () => {} },
  };
  return A;
}

export function initImporterUI(VL) {
  const A = importer_actions(VL);
  VL.importer = A;
  if (typeof document === "undefined") return A;
  const etat = VL.etat;

  // le sélecteur de fichier, créé ici (aucune édition de la page)
  const entree = document.createElement("input");
  entree.type = "file";
  entree.id = "vlImporterInput";
  entree.accept = ".svg,.pdf,image/svg+xml,application/pdf";
  entree.hidden = true;
  document.body.appendChild(entree);
  entree.addEventListener("change", () => {
    const f = entree.files && entree.files[0];
    entree.value = "";
    if (f) A.fichier(f);
  });
  A.entree = entree;

  // collage : le Ctrl+V clavier colle AUSSI le presse-papiers interne (core.js) ; s'il l'a fait pour ce même
  // geste, on l'annule — le SVG du presse-papiers système est ce que l'utilisateur vient de copier
  let ppAvant = null;
  document.addEventListener("keydown", (ev) => {
    if (VL.dansPanneau(ev)) return;  // un panneau flottant garde ses gestes (mod-flottant)
    if (ev.ctrlKey && (ev.key || "").toLowerCase() === "v") ppAvant = etat.pressePapiers ? etat.pressePapiers.n : null;
  }, true);
  document.addEventListener("paste", (ev) => {
    if (!etat.doc || /^(INPUT|TEXTAREA)$/.test((document.activeElement && document.activeElement.tagName) || "")) return;
    const svg = svg_du_presse_papiers(ev.clipboardData);
    if (!svg) return;
    ev.preventDefault();
    if (ppAvant !== null && etat.pressePapiers && etat.pressePapiers.n !== ppAvant) { VL.annuler(); etat.pressePapiers.n = ppAvant; }
    ppAvant = null;
    A.texte(svg, "presse-papiers");
  });

  // dépôt sur la toile : posé au point de dépôt
  const scene = document.querySelector("#stage");
  if (scene) {
    const fichierDe = (ev) => [...((ev.dataTransfer && ev.dataTransfer.files) || [])].find((f) => type_fichier(f.name, f.type));
    scene.addEventListener("dragover", (ev) => {
      if (!etat.doc || ![...((ev.dataTransfer && ev.dataTransfer.types) || [])].includes("Files")) return;
      ev.preventDefault();
      ev.dataTransfer.dropEffect = "copy";
    });
    scene.addEventListener("drop", (ev) => {
      const f = etat.doc && fichierDe(ev);
      if (!f) return;
      ev.preventDefault();
      const [x, y] = VL.docPt(ev.clientX, ev.clientY);
      A.fichier(f, { x, y });
    });
  }
  return A;
}
