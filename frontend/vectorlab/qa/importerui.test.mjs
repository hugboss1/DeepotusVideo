// importerui.test.mjs — lot D4 « Interop » (t470) : importer un SVG DANS le document. L'opération op_importer_svg
// (js/mod-importsvg.js, pure) et l'interface (js/mod-importerui.js) : menu Fichier › Importer, fichier choisi,
// SVG collé, SVG déposé, bilan en une ligne. Le VL est factice : executer applique l'op sur le document.
import { svg_vers_objets, op_importer_svg } from "../js/mod-importsvg.js";
import { importer_actions, bilan_import, est_svg, type_fichier, svg_du_presse_papiers } from "../js/mod-importerui.js";
import { T } from "../js/mod-i18n.js";
import { compilerSVG } from "../js/mod-doc.js";
import { polylignes_objet } from "../js/mod-bool.js";

const echecs = [];
const ok = (nom, cond, detail = "") => {
  if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 240) : ""));
};
const refus = (fn) => { try { fn(); return null; } catch (e) { return e.message; } };
const doc = (...objets) => ({ v: 1, taille: { w: 400, h: 400 },
  calques: [{ id: "c1", nom: "c", visible: true, verrou: false, objets }, { id: "c2", nom: "v", visible: true, verrou: true, objets: [] }] });
const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="50"><rect id="a" width="10" height="10" fill="#f00"/><g><circle r="5"/></g></svg>';
const ids = (o, out = []) => { out.push(o.id); (o.enfants || []).forEach((e) => ids(e, out)); return out; };

/* ── l'opération ── */
{
  const d = doc({ id: "o1", type: "rect", x: 0, y: 0, w: 1, h: 1, style: {} }, { id: "o3", type: "rect", x: 0, y: 0, w: 1, h: 1, style: {} });
  const a = svg_vers_objets(SVG);
  const id = op_importer_svg(d, a, { calque: "c1" });
  const g = d.calques[0].objets[2];
  ok("un groupe ajouté au calque, id rendu", d.calques[0].objets.length === 3 && g.type === "groupe" && g.id === id);
  ok("posé au centre de la page (boîte du SVG centrée)", g.transform === "translate(150 175)", g.transform);
  ok("contenu repris : rect + groupe(cercle)", g.enfants.length === 2 && g.enfants[0].type === "rect" && g.enfants[1].enfants[0].type === "ellipse");
  const tous = ids(g);
  ok("ids neufs o<n>, uniques, sans collision", tous.every((x) => /^o\d+$/.test(x)) && new Set(tous).size === tous.length
     && !tous.includes("o1") && !tous.includes("o3"), tous.join(","));
  ok("l'analyse n'est pas modifiée (réimportable)", a.objets[0].id.startsWith("i"));
  const id2 = op_importer_svg(d, a, { calque: "c1", x: 50, y: 50 });
  const g2 = d.calques[0].objets[3];
  ok("point voulu : translate(0 25)", g2.id === id2 && g2.transform === "translate(0 25)", g2.transform);
  ok("deux imports : aucun id partagé", ids(g2).every((x) => !tous.includes(x)));
  ok("calque par défaut : le premier", (() => { const d3 = doc(); op_importer_svg(d3, a); return d3.calques[0].objets.length === 1; })());
  ok("rien à importer → refus traduit", refus(() => op_importer_svg(doc(), { objets: [], taille: { w: 1, h: 1 } }, { calque: "c1" })) === T("vectorlab.importer.vide"));
  ok("calque verrouillé → refus (op_ajouter)", refus(() => op_importer_svg(doc(), a, { calque: "c2" })) !== null);
  const im = svg_vers_objets('<svg width="10" height="10"><image href="data:image/png;base64,AAAA" width="4" height="3"/></svg>');
  const d4 = doc();
  op_importer_svg(d4, im, { calque: "c1" });
  ok("la marque nat_provisoire ne reste pas dans le document", !JSON.stringify(d4).includes("nat_provisoire"));
}

/* ── aller-retour : export SVG du document → réimport, même géométrie et mêmes styles ── */
{
  const d = doc();
  op_importer_svg(d, svg_vers_objets('<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 150 100">'
    + '<style>.a{fill:#2b6cb0;stroke:#1a365d;stroke-width:2}</style><rect class="a" x="5" y="5" width="60" height="40" rx="8"/>'
    + '<path fill-rule="evenodd" opacity=".4" d="M80 45 a25 25 0 1 1 50 0 a25 25 0 1 1 -50 0z M95 45 h20 v5 h-20z"/>'
    + '<polyline fill="none" stroke="red" stroke-dasharray="6 3" points="10,90 40,60 70,90"/><g transform="rotate(15 50 50)"><ellipse cx="40" cy="70" rx="9" ry="4"/></g></svg>'), { calque: "c1" });
  const copie = doc();
  op_importer_svg(copie, svg_vers_objets(compilerSVG(d, { sansId: true })), { calque: "c1", x: 200, y: 200 });
  const pts = (x) => x.calques[0].objets.flatMap((o) => polylignes_objet(o)).flatMap((l) => l.points);
  const p0 = pts(d), p1 = pts(copie);
  ok("aller-retour : autant de points, écart nul", p0.length > 50 && p0.length === p1.length && p0.every((p, k) => Math.hypot(p[0] - p1[k][0], p[1] - p1[k][1]) < 1e-3), p0.length + "/" + p1.length);
  const feuilles = (o) => (o.enfants ? o.enfants.flatMap(feuilles) : [o]);
  const st = (x) => JSON.stringify(x.calques[0].objets.flatMap(feuilles).map((f) => f.style));
  ok("aller-retour : mêmes styles (fond, contour, pointillés, règle, opacité, jointure)", st(d) === st(copie), st(d) + " ≠ " + st(copie));
}

/* ── petites fonctions ── */
{
  ok("est_svg : <svg, <?xml, commentaire, DOCTYPE, BOM", est_svg('<svg width="1"/>') && est_svg('  <?xml version="1.0"?>\n<svg/>')
     && est_svg("<!-- Illustrator --><svg/>") && est_svg('<!DOCTYPE svg PUBLIC "x" "y"><svg/>') && est_svg("\uFEFF<svg/>"));
  ok("est_svg : pas du SVG", !est_svg("bonjour") && !est_svg("<html><svg/></html>") && !est_svg("") && !est_svg(null) && !est_svg('<?xml version="1.0"?><x/>'));
  ok("type_fichier : extension ou type", type_fichier("Logo.SVG", "") === "svg" && type_fichier("a", "image/svg+xml") === "svg"
     && type_fichier("plan.pdf", "") === "pdf" && type_fichier("x", "application/pdf") === "pdf" && type_fichier("a.png", "image/png") === null);
  ok("bilan : rien d'ignoré", bilan_import({ importes: 3, ignores: { cache: 0, image: 0 } }) === T("vectorlab.importer.bilan", { n: 3 }));
  const b = bilan_import({ importes: 1, ignores: { cache: 0, image: 2, filtre: 1 } });
  ok("bilan : raisons non nulles, avec leur nombre", b === T("vectorlab.importer.non_repris", { bilan: T("vectorlab.importer.bilan", { n: 1 }),
    liste: T("vectorlab.importer.r_image") + " (2), " + T("vectorlab.importer.r_filtre") + " (1)" }), b);
  ok("bilan : le texte français exact", b === "1 objet(s) importé(s) ; non repris : images liées (2), filtres (1)", b);
  const cp = (types, donnees) => ({ types, getData: (t) => donnees[t] || "" });
  ok("presse-papiers : image/svg+xml d'abord", svg_du_presse_papiers(cp(["text/plain", "image/svg+xml"], { "image/svg+xml": "<svg/>", "text/plain": "x" })) === "<svg/>");
  ok("presse-papiers : texte qui est un SVG", svg_du_presse_papiers(cp(["text/plain"], { "text/plain": " <svg/>" })) === " <svg/>");
  ok("presse-papiers : texte ordinaire → rien", svg_du_presse_papiers(cp(["text/plain"], { "text/plain": "bonjour" })) === null && svg_du_presse_papiers(null) === null);
}

/* ── l'interface (VL factice) ── */
const vlFactice = (d = doc()) => {
  const VL = { etat: { doc: d, docId: "d1", calqueActif: "c1", selection: [] }, toasts: [], depots: [],
    executer(fn, ...args) { try { return fn(VL.etat.doc, ...args); } catch (e) { VL.toast(e.message, true); return undefined; } },
    toast(m, err) { VL.toasts.push([m, !!err]); },
    setSelection(s) { VL.etat.selection = s; }, setOutil(o) { VL.outil = o; },
    async deposerBlob(blob) { VL.depots.push(blob.size); return { href: "img_" + VL.depots.length + ".png", nat: { w: 40, h: 30 } }; } };
  return VL;
};
{
  const VL = vlFactice();
  const A = importer_actions(VL);
  const id = await A.texte(SVG, "logo.svg");
  const g = VL.etat.doc.calques[0].objets[0];
  ok("texte : importé dans le calque actif, sélectionné, outil Sélection", g && g.id === id && VL.etat.selection[0] === id && VL.outil === "select");
  ok("texte : bilan dans le toast", VL.toasts.at(-1)[0] === T("vectorlab.importer.bilan", { n: 2 }) && !VL.toasts.at(-1)[1], JSON.stringify(VL.toasts));
  const id2 = await A.texte(SVG, "x.svg", { x: 10, y: 20 });
  ok("texte : au point de dépôt", VL.etat.doc.calques[0].objets[1].id === id2 && VL.etat.doc.calques[0].objets[1].transform === "translate(-40 -5)");
  VL.etat.calqueActif = "c2";
  ok("calque verrouillé : rien, l'erreur est dite", (await A.texte(SVG, "x.svg")) === undefined && VL.toasts.at(-1)[1]);
  VL.etat.calqueActif = "c1";
  ok("SVG malformé : erreur dite, rien posé", (await A.texte("<svg><g></svg>", "x.svg")) === undefined
     && VL.toasts.at(-1)[0] === T("vectorlab.importer.xml_invalide") && VL.etat.doc.calques[0].objets.length === 2);
  // les images data: entrent au magasin du document
  const png = "data:image/png;base64," + Buffer.from("PNG!").toString("base64");
  const idi = await A.texte(`<svg width="10" height="10"><image href="${png}" x="1" y="2" width="4" height="3"/></svg>`, "i.svg");
  const im = VL.etat.doc.calques[0].objets.find((o) => o.id === idi).enfants[0];
  ok("image data: déposée au magasin (href, nat réelle)", VL.depots.length === 1 && im.href === "img_1.png" && im.nat.w === 40 && im.nat.h === 30
     && im.w === 4 && im.h === 3 && !("nat_provisoire" in im), JSON.stringify(im));
  // fichier choisi
  const fic = (name, type, texte) => ({ name, type, text: async () => texte });
  const n0 = VL.etat.doc.calques[0].objets.length;
  ok("fichier SVG : importé", (await A.fichier(fic("Logo.svg", "", SVG))) !== undefined && VL.etat.doc.calques[0].objets.length === n0 + 1);
  ok("fichier d'un autre type : refus dit", (await A.fichier(fic("a.png", "image/png", ""))) === undefined
     && VL.toasts.at(-1)[0] === T("vectorlab.importer.type_inconnu") && VL.toasts.at(-1)[1]);
  ok("fichier PDF sans lecteur PDF : refus dit", (await A.fichier(fic("a.pdf", "application/pdf", ""))) === undefined && VL.toasts.at(-1)[1]);
  ok("fichier PDF : confié au lecteur PDF s'il existe", await (async () => {
    let vu = null; VL.importerPdf = async (f, pos) => { vu = [f.name, pos]; return "oX"; };
    const r = await A.fichier(fic("a.pdf", "application/pdf", ""), { x: 1, y: 2 });
    delete VL.importerPdf; return r === "oX" && vu[0] === "a.pdf" && vu[1].x === 1;
  })());
  // l'action de menu
  ok("action importer : possible avec un document", A.action("importer").peut() === true);
  const VL0 = vlFactice(); VL0.etat.doc = null;
  ok("action importer : impossible sans document", importer_actions(VL0).action("importer").peut() === false);
  ok("sans document : l'import est refusé et dit", (await importer_actions(VL0).texte(SVG, "x.svg")) === undefined && VL0.toasts.at(-1)[0] === T("vectorlab.importer.aucun_doc"));
  ok("action inconnue : jamais possible", A.action("zzz").peut() === false);
}

if (echecs.length) {
  console.error(`importerui : ${echecs.length} échec(s)\n - ` + echecs.join("\n - "));
  process.exit(1);
}
console.log("importerui : ok");
