"""t478 (09/11/2026) — lot D5 « Couleur et motif », T4 : les motifs faits d'objets (module NEUF js/mod-motifs.js, hors
table). Les éditions des modules de BASE, chacune sur un fragment de sa ligne qui ne recouvre aucun libellé traduit :
  * mod-doc.js :
    - l'import (motif_valider paramétrique renommé, puis la validation qui aiguille vers mod-motifs) ;
    - parserDoc refuse un cycle entre motifs ;
    - _defs émet aussi les motifs et les dégradés employés DANS un motif, puis le <pattern> d'un motif d'objets ;
  * mod-pdf.js :
    - l'import ;
    - _motif aiguille un motif d'objets vers mod-motifs ;
    - le motif de pavage a un pas X et un pas Y, et peut prendre les ressources de la page.
Les refus sont saisis en entrées H."""
from outils import L, S, X, H  # noqa: F401

DOC = "js/mod-doc.js"
PDF = "js/mod-pdf.js"

ENTREES = [
    S(DOC, 10, "motif_valider, motif_svg,", "motif_valider as _motifValiderParam, motif_svg,", {}),
    S(DOC, 11, 'from "./mod-effets.js";',
      'from "./mod-effets.js";\r\n'
      'import { motif_objets_valider, motif_objets_svg, motifs_fermeture, motifs_cycle } from "./mod-motifs.js";   // t478\r\n'
      '// t478 : un motif fait d\'objets (type « objets ») est validé par mod-motifs ; les autres restent paramétriques\r\n'
      'const motif_valider = (m) => (m && m.type === "objets" ? motif_objets_valider(m) : _motifValiderParam(m));', {}),
    S(DOC, 243, "    for (const [id, m] of Object.entries(doc.motifs)) {",
      "    motifs_cycle(doc.motifs);   // t478 : un motif ne se contient pas, même indirectement\r\n"
      "    for (const [id, m] of Object.entries(doc.motifs)) {", {}),
    S(DOC, 2215, "  const degs = doc.degrades || {}, mots = doc.motifs || {};",
      "  const degs = doc.degrades || {}, mots = doc.motifs || {};\r\n"
      "  motifs_fermeture(doc, motifs, refs);   // t478 : les motifs et dégradés employés DANS un motif d'objets", {}),
    S(DOC, 2242, "morceaux.push(motif_svg(id, {",
      'morceaux.push(mots[id].type === "objets" ? motif_objets_svg(id, mots[id], (o) => compilerObjet(o, { ...ctx, sansId: true }), (c) => _couleur(c, ctx)) : motif_svg(id, {', {}),
    S(PDF, 22, 'import { hex_centre, hex_d } from "./mod-grille.js";',
      'import { hex_centre, hex_d } from "./mod-grille.js";\r\nimport { motif_objets_pdf } from "./mod-motifs.js";   // t478', {}),
    S(PDF, 235, "function _motif(ctx, spec) {",
      "function _motif(ctx, spec) {\r\n"
      '  if (spec && spec.type === "objets") return motif_objets_pdf(ctx, spec, { dessiner: _objet, raison: _raison, matrice_mul, matrice_inverse, nb });   // t478', {}),
    S(PDF, 489, "/XStep ${nb(P.pas)} ", "/XStep ${nb(P.pasX ?? P.pas)} ", {}),
    S(PDF, 490, "/YStep ${nb(P.pas)} /Resources << /ProcSet [/PDF] >> ",
      '/YStep ${nb(P.pasY ?? P.pas)} /Resources ${P.ressources ? ressources + " 0 R" : "<< /ProcSet [/PDF] >>"} ', {}),

    H("vectorlab.motifs.pavage", "Pavage inconnu : « {pavage} ».", "Unknown tiling: “{pavage}”."),
    H("vectorlab.motifs.taille", "La tuile d'un motif doit mesurer de 0,5 à 10 000 px.", "A pattern tile must measure from 0.5 to 10,000 px."),
    H("vectorlab.motifs.espacement", "Espacement invalide : il ne peut pas annuler la tuile (ni dépasser 10 000 px).",
      "Invalid spacing: it cannot cancel the tile (nor exceed 10,000 px)."),
    H("vectorlab.motifs.vide", "Un motif doit contenir au moins un objet.", "A pattern must contain at least one object."),
    H("vectorlab.motifs.type_objet", "Un motif ne peut pas contenir cet objet ({type}).", "A pattern cannot contain this object ({type})."),
    H("vectorlab.motifs.effets", "Un objet de motif ne peut porter ni effet, ni masque, ni écrêtage.",
      "A pattern object cannot carry effects, masks or clipping."),
    H("vectorlab.motifs.cycle", "Le motif « {id} » se contiendrait lui-même.", "Pattern “{id}” would contain itself."),
    H("vectorlab.motifs.trop", "Un motif contient {n} objets au plus.", "A pattern holds {n} objects at most."),
    H("vectorlab.motifs.aucune_selection", "Sélectionnez les objets qui feront le motif.", "Select the objects that will make the pattern."),
    H("vectorlab.motifs.pas_objets", "Ce motif n'est pas fait d'objets : il se règle dans l'onglet Apparence.",
      "This pattern is not made of objects: adjust it in the Appearance tab."),
]
