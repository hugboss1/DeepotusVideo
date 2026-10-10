"""t148 — mf2 : materialforge.js lignes 1401-2700 — catalogue CC0, état vide de la galerie, cartes de galerie (jeton de
maps, infobulles, suppression armée), preuve des maps (audit d'indépendance, bordereau du ZIP), toasts de duplication /
suppression / enregistrement, en-tête de l'éditeur, inspecteur (résumés de groupes, lignes de propriétés, maps de
texture, dérivation, filtre). GARDÉ : messages renvoyés par le serveur (e.message, st.note, mani.weigh_rule), noms
d'usage des maps (Base Color, ORM, MaskMap : noms des moteurs), « occlusion » (identique en anglais), valeurs
techniques. Pluriels : deux clés (.un / .n) choisies par le code ; phrases coupées réunies en UNE clé à variables."""
from outils import L, S, X, H

F = "materialforge/materialforge.js"
PLAGES = {F: (1401, 2700)}

ENTREES = [
    # ── catalogue CC0 ──
    S(F, 1404, '"Catalogue : " + e.message', 'dzT("matiere.mf2_cat.echec", { msg: e.message })',
      {"matiere.mf2_cat.echec": ("Catalogue : {msg}", "Catalog: {msg}")}),
    S(F, 1404, 'apiFail(e, "catalogue")', 'apiFail(e, dzT("matiere.mf2_cat.quoi"))',
      {"matiere.mf2_cat.quoi": ("catalogue", "catalog", "contexte")}),
    L(F, 1406, '"Le catalogue n\'est pas dans cette installation (scripts/build_materials_catalog.py --fetch)."',
      "matiere.mf2_cat.absent",
      "Le catalogue n'est pas dans cette installation (scripts/build_materials_catalog.py --fetch).",
      "The catalog is not part of this installation (scripts/build_materials_catalog.py --fetch)."),
    S(F, 1413, '`Catalogue CC0 — ${d.materials.length} matière${d.materials.length > 1 ? "s" : ""}`',
      '(d.materials.length > 1 ? dzT("matiere.mf2_cat.titre_n", { n: d.materials.length }) : '
      'dzT("matiere.mf2_cat.titre_1", { n: d.materials.length }))',
      {"matiere.mf2_cat.titre_n": ("Catalogue CC0 — {n} matières", "CC0 catalog — {n} materials"),
       "matiere.mf2_cat.titre_1": ("Catalogue CC0 — {n} matière", "CC0 catalog — {n} material")}),
    S(F, 1415, 'Source : <b>${esc(src.name || "")}</b> — licence ${esc(src.license || "")}.\r\n'
      '      Trois cartes sont embarquées (couleur, normale mesurée, rugosité) ; les cinq autres sont\r\n'
      "      dérivées à l'import, localement et gratuitement.</p>",
      '${dzT("matiere.mf2_cat.source", { nom: esc(src.name || ""), licence: esc(src.license || "") })}</p>',
      {"matiere.mf2_cat.source": (
          "Source : <b>{nom}</b> — licence {licence}. Trois cartes sont embarquées (couleur, normale mesurée, "
          "rugosité) ; les cinq autres sont dérivées à l'import, localement et gratuitement.",
          "Source: <b>{nom}</b> — {licence} license. Three maps are bundled (color, measured normal, roughness); "
          "the other five are derived on import, locally and for free.")}),
    L(F, 1420, '"Toutes"', "matiere.mf2_cat.toutes", "Toutes", "All", contexte=True),
    S(F, 1428, "disabled>Importer</button>", 'disabled>${dzT("matiere.mf2_cat.importer")}</button>',
      {"matiere.mf2_cat.importer": ("Importer", "Import")}),
    S(F, 1434, 'choisis.size ? `Importer ${choisis.size} matière${choisis.size > 1 ? "s" : ""}` : "Importer"',
      'choisis.size ? (choisis.size > 1 ? dzT("matiere.mf2_cat.importer_n", { n: choisis.size }) : '
      'dzT("matiere.mf2_cat.importer_1", { n: choisis.size })) : dzT("matiere.mf2_cat.importer")',
      {"matiere.mf2_cat.importer_n": ("Importer {n} matières", "Import {n} materials"),
       "matiere.mf2_cat.importer_1": ("Importer {n} matière", "Import {n} material")}),
    S(F, 1444, '`Import de ${choisis.size} matière${choisis.size > 1 ? "s" : ""} — dérivation locale…`',
      '(choisis.size > 1 ? dzT("matiere.mf2_cat.import_n", { n: choisis.size }) : '
      'dzT("matiere.mf2_cat.import_1", { n: choisis.size }))',
      {"matiere.mf2_cat.import_n": ("Import de {n} matières — dérivation locale…",
                                    "Importing {n} materials — local derivation…"),
       "matiere.mf2_cat.import_1": ("Import de {n} matière — dérivation locale…",
                                    "Importing {n} material — local derivation…")}),
    S(F, 1449, '`${r.materials.length} matière${r.materials.length > 1 ? "s" : ""} importée${r.materials.length > 1 ? "s" : ""}.`',
      '(r.materials.length > 1 ? dzT("matiere.mf2_cat.importees_n", { n: r.materials.length }) : '
      'dzT("matiere.mf2_cat.importees_1", { n: r.materials.length }))',
      {"matiere.mf2_cat.importees_n": ("{n} matières importées.", "{n} materials imported."),
       "matiere.mf2_cat.importees_1": ("{n} matière importée.", "{n} material imported.")}),
    S(F, 1451, 'apiFail(e, "import du catalogue")', 'apiFail(e, dzT("matiere.mf2_cat.quoi_import"))',
      {"matiere.mf2_cat.quoi_import": ("import du catalogue", "catalog import")}),
    S(F, 1451, '"Import refusé : " + e.message', 'dzT("matiere.mf2_cat.import_refuse", { msg: e.message })',
      {"matiere.mf2_cat.import_refuse": ("Import refusé : {msg}", "Import refused: {msg}")}),

    # ── galerie vide ──
    S(F, 1460, "</div>\r\n      <h3>L’API Matières ne répond pas</h3>", '</div>\r\n      <h3>${dzT("matiere.mf2_vide.api_titre")}</h3>',
      {"matiere.mf2_vide.api_titre": ("L’API Matières ne répond pas", "The Materials API is not responding")}),
    S(F, 1462, "<p>Le lab reste ouvert. Dès que <code>GET /api/materials</code> répond, la galerie se remplit ici.</p>",
      '<p>${dzT("matiere.mf2_vide.api_texte")}</p>',
      {"matiere.mf2_vide.api_texte": (
          "Le lab reste ouvert. Dès que <code>GET /api/materials</code> répond, la galerie se remplit ici.",
          "The lab stays open. As soon as <code>GET /api/materials</code> responds, the gallery fills up here.")}),
    S(F, 1463, ">Réessayer</button>", '>${dzT("matiere.mf2_vide.reessayer")}</button>',
      {"matiere.mf2_vide.reessayer": ("Réessayer", "Retry")}),
    S(F, 1468, "</div>\r\n      <h3>Aucune matière pour « ${esc(state.filter)} »</h3>",
      '</div>\r\n      <h3>${dzT("matiere.mf2_vide.aucune", { q: esc(state.filter) })}</h3>',
      {"matiere.mf2_vide.aucune": ("Aucune matière pour « {q} »", "No material for “{q}”")}),
    S(F, 1470, '<p>${state.materials.length} matière${state.materials.length > 1 ? "s" : ""} en stock — le filtre porte sur le nom, l’invite et l’image d’origine.</p>',
      '<p>${state.materials.length > 1 ? dzT("matiere.mf2_vide.stock_n", { n: state.materials.length }) : '
      'dzT("matiere.mf2_vide.stock_1", { n: state.materials.length })}</p>',
      {"matiere.mf2_vide.stock_n": (
          "{n} matières en stock — le filtre porte sur le nom, l’invite et l’image d’origine.",
          "{n} materials in stock — the filter looks at the name, the prompt and the source image."),
       "matiere.mf2_vide.stock_1": (
          "{n} matière en stock — le filtre porte sur le nom, l’invite et l’image d’origine.",
          "{n} material in stock — the filter looks at the name, the prompt and the source image.")}),
    S(F, 1471, ">Effacer le filtre</button>", '>${dzT("matiere.mf2_vide.effacer")}</button>',
      {"matiere.mf2_vide.effacer": ("Effacer le filtre", "Clear filter")}),
    S(F, 1475, "</div>\r\n    <h3>La galerie est vide</h3>", '</div>\r\n    <h3>${dzT("matiere.mf2_vide.titre")}</h3>',
      {"matiere.mf2_vide.titre": ("La galerie est vide", "The gallery is empty")}),
    S(F, 1477, "<p>Décris une matière à gauche, ou pars d’une image de la Library.\r\n"
      "       Chaque forge dépose ici une carte en aperçu 3D réel, avec ses\r\n"
      "       <b>maps PBR</b> et son <b>score de raccord mesuré</b>.</p>",
      '<p>${dzT("matiere.mf2_vide.intro")}</p>',
      {"matiere.mf2_vide.intro": (
          "Décris une matière à gauche, ou pars d’une image de la Library. Chaque forge dépose ici une carte en "
          "aperçu 3D réel, avec ses <b>maps PBR</b> et son <b>score de raccord mesuré</b>.",
          "Describe a material on the left, or start from a Library image. Each forge drops a card here with a "
          "real 3D preview, its <b>PBR maps</b> and its <b>measured seam score</b>.")}),
    S(F, 1483, "<p>Ou pars d'une matière du catalogue :", '<p>${dzT("matiere.mf2_vide.ou_catalogue")}',
      {"matiere.mf2_vide.ou_catalogue": ("Ou pars d'une matière du catalogue :", "Or start from a catalog material:")}),
    S(F, 1484, " Catalogue CC0 (30 matières)</button>", ' ${dzT("matiere.mf2_vide.catalogue_30")}</button>',
      {"matiere.mf2_vide.catalogue_30": ("Catalogue CC0 (30 matières)", "CC0 catalog (30 materials)")}),
    S(F, 1485, '<p class="empty-foot">Rouvrir une matière plus tard : un clic sur sa carte la rouvre\r\n'
      "      dans l’éditeur, propriétés et maps intactes.</p>",
      '<p class="empty-foot">${dzT("matiere.mf2_vide.rouvrir")}</p>',
      {"matiere.mf2_vide.rouvrir": (
          "Rouvrir une matière plus tard : un clic sur sa carte la rouvre dans l’éditeur, propriétés et maps intactes.",
          "Reopen a material later: one click on its card opens it in the editor again, properties and maps "
          "intact.")}),

    # ── jeton de maps et infobulle de preuve des cartes ──
    L(F, 1553, '"couleur"', "matiere.mf2_mapc.basecolor", "couleur", "color", contexte=True),
    L(F, 1553, '"normale"', "matiere.mf2_mapc.normal", "normale", "normal", contexte=True),
    L(F, 1553, '"rugosité"', "matiere.mf2_mapc.roughness", "rugosité", "roughness"),
    L(F, 1554, '"métal"', "matiere.mf2_mapc.metallic", "métal", "metal", contexte=True),
    X(F, 1554, '"occlusion"', "identique en anglais"),
    L(F, 1554, '"hauteur"', "matiere.mf2_mapc.height", "hauteur", "height", contexte=True),
    L(F, 1554, '"émission"', "matiere.mf2_mapc.emissive", "émission", "emission", contexte=True),
    X(F, 1555, '"ORM"', "nom de map des moteurs"),
    X(F, 1555, '"MaskMap"', "nom de map des moteurs (Unity HDRP)"),
    S(F, 1563, 'c.cst + (c.cst > 1 ? " unies : " : " unie : ") + esc(noms)',
      '(c.cst > 1 ? dzT("matiere.mf2_carte.unies", { n: c.cst, noms: esc(noms) }) : '
      'dzT("matiere.mf2_carte.unie", { n: c.cst, noms: esc(noms) }))',
      {"matiere.mf2_carte.unies": ("{n} unies : {noms}", "{n} flat: {noms}"),
       "matiere.mf2_carte.unie": ("{n} unie : {noms}", "{n} flat: {noms}")}),
    L(F, 1564, '"toutes porteuses"', "matiere.mf2_carte.porteuses", "toutes porteuses", "all carry data"),
    S(F, 1577, '"Ouvrir la preuve des maps : les images, leurs statistiques et le " +\r\n'
      '      "contenu exact du ZIP."',
      'dzT("matiere.mf2_carte.preuve_ouvrir")',
      {"matiere.mf2_carte.preuve_ouvrir": (
          "Ouvrir la preuve des maps : les images, leurs statistiques et le contenu exact du ZIP.",
          "Open the map proof: the images, their statistics and the exact contents of the ZIP.")}),
    S(F, 1581, '"Les " + c.n + " maps du jeu sont livrées, toujours." +\r\n'
      "    (c.cst\r\n"
      '      ? " " + c.cst + " d\'entre elles sont des champs constants : " +\r\n'
      '        why.join(" ; ") + ". C\'est un fait sur CETTE matière, pas une map " +\r\n'
      '        "manquante — un moteur attend les " + c.n + " fichiers et les reçoit."\r\n'
      '      : " Les " + c.n + " portent de l\'information : aucun champ constant.") +\r\n'
      '    " Ouvrir la preuve : les images, leurs statistiques, la corrélation entre " +\r\n'
      '    "maps et le contenu exact du ZIP."',
      'dzT("matiere.mf2_carte.livrees", { n: c.n }) +\r\n'
      "    (c.cst\r\n"
      '      ? " " + dzT("matiere.mf2_carte.constantes", { c: c.cst, raisons: why.join(" ; "), n: c.n })\r\n'
      '      : " " + dzT("matiere.mf2_carte.aucune_constante", { n: c.n })) +\r\n'
      '    " " + dzT("matiere.mf2_carte.ouvrir_preuve")',
      {"matiere.mf2_carte.livrees": ("Les {n} maps du jeu sont livrées, toujours.",
                                     "All {n} maps of the set are delivered, always."),
       "matiere.mf2_carte.constantes": (
           "{c} d'entre elles sont des champs constants : {raisons}. C'est un fait sur CETTE matière, pas une map "
           "manquante — un moteur attend les {n} fichiers et les reçoit.",
           "{c} of them are constant fields: {raisons}. That is a fact about THIS material, not a missing map — an "
           "engine expects the {n} files and gets them."),
       "matiere.mf2_carte.aucune_constante": ("Les {n} portent de l'information : aucun champ constant.",
                                              "All {n} carry information: no constant field."),
       "matiere.mf2_carte.ouvrir_preuve": (
           "Ouvrir la preuve : les images, leurs statistiques, la corrélation entre maps et le contenu exact du ZIP.",
           "Open the proof: the images, their statistics, the correlation between maps and the exact contents of "
           "the ZIP.")}),

    # ── carte de galerie ──
    S(F, 1601, '" tabindex="0" role="button" aria-label="Ouvrir ${esc(nm)}"', '" tabindex="0" role="button" aria-label="${dzT("matiere.mf2_carte.ouvrir_nom", { nom: esc(nm) })}"',
      {"matiere.mf2_carte.ouvrir_nom": ("Ouvrir {nom}", "Open {nom}")}),
    S(F, 1602, 'title="Ouvrir « ${esc(nm)} » dans l’éditeur"',
      'title="${dzT("matiere.mf2_carte.ouvrir_editeur", { nom: esc(nm) })}"',
      {"matiere.mf2_carte.ouvrir_editeur": ("Ouvrir « {nom} » dans l’éditeur", "Open “{nom}” in the editor")}),
    S(F, 1607, "<span class=\"card-res\" title=\"Cette matière s'écarte de la définition courante de la galerie (${resView.base}²) : elle a été forgée en ${m.res}².\"",
      '<span class="card-res" title="${dzT("matiere.mf2_carte.res_ecart", { base: resView.base, res: m.res })}"',
      {"matiere.mf2_carte.res_ecart": (
          "Cette matière s'écarte de la définition courante de la galerie ({base}²) : elle a été forgée en {res}².",
          "This material differs from the gallery's current resolution ({base}²): it was forged at {res}².")}),
    S(F, 1609, '\r\n    <button class="card-del" data-act="del" data-arm="0" type="button"\r\n            aria-label="Supprimer ${esc(nm)}"',
      '\r\n    <button class="card-del" data-act="del" data-arm="0" type="button"\r\n            aria-label="${dzT("matiere.mf2_carte.supprimer_nom", { nom: esc(nm) })}"',
      {"matiere.mf2_carte.supprimer_nom": ("Supprimer {nom}", "Delete {nom}")}),
    S(F, 1612, 'title="Supprimer la matière et ses maps — un second clic confirme"',
      'title="${dzT("matiere.mf2_carte.supprimer_titre")}"',
      {"matiere.mf2_carte.supprimer_titre": ("Supprimer la matière et ses maps — un second clic confirme",
                                             "Delete the material and its maps — a second click confirms")}),
    S(F, 1612, '</button>\r\n    <span class="card-open">Ouvrir</span>', '</button>\r\n    <span class="card-open">${dzT("matiere.mf2_carte.ouvrir")}</span>',
      {"matiere.mf2_carte.ouvrir": ("Ouvrir", "Open")}),
    S(F, 1618, '<span class="card-model" title="Modèle payant appelé pour l’image de base"', '<span class="card-model" title="${dzT("matiere.mf2_carte.modele")}"',
      {"matiere.mf2_carte.modele": ("Modèle payant appelé pour l’image de base",
                                    "Paid model called for the base image")}),
    S(F, 1622, '</button>\r\n      <button class="iact" data-act="dup" title="Copie locale et gratuite de cette matière">${ico("dz-action-dupliquer")} Dupliquer</button>',
      '</button>\r\n      <button class="iact" data-act="dup" title="${dzT("matiere.mf2_carte.dup_titre")}">${ico("dz-action-dupliquer")} ${dzT("matiere.mf2_carte.dupliquer")}</button>',
      {"matiere.mf2_carte.dup_titre": ("Copie locale et gratuite de cette matière",
                                       "Free local copy of this material"),
       "matiere.mf2_carte.dupliquer": ("Dupliquer", "Duplicate")}),
    S(F, 1624, 'title="Télécharger l’archive ZIP des maps de cette matière — son contenu exact est listé dans la preuve"',
      'title="${dzT("matiere.mf2_carte.zip_titre")}"',
      {"matiere.mf2_carte.zip_titre": (
          "Télécharger l’archive ZIP des maps de cette matière — son contenu exact est listé dans la preuve",
          "Download the ZIP archive of this material's maps — its exact contents are listed in the proof")}),
    S(F, 1624, ' ZIP</button>\r\n      <button class="iact" data-act="reuse" title="Recharger son invite et ses réglages dans le rail de gauche">${ico("dz-action-reprendre-reglages")} Invite</button>',
      ' ZIP</button>\r\n      <button class="iact" data-act="reuse" title="${dzT("matiere.mf2_carte.invite_titre")}">${ico("dz-action-reprendre-reglages")} ${dzT("matiere.mf2_carte.invite")}</button>',
      {"matiere.mf2_carte.invite_titre": ("Recharger son invite et ses réglages dans le rail de gauche",
                                          "Reload its prompt and settings into the left rail"),
       "matiere.mf2_carte.invite": ("Invite", "Prompt", "contexte")}),
    L(F, 1648, '"Supprimer ?"', "matiere.mf2_carte.supprimer_arme", "Supprimer ?", "Delete?"),

    # ── preuve des maps : liens déclarés ──
    L(F, 1725, '"image de base — c\'est la source payante, tout en dérive"', "matiere.mf2_kin.basecolor",
      "image de base — c'est la source payante, tout en dérive", "base image — the paid source, everything derives from it"),
    L(F, 1726, '"luminance de la couleur de base, lissée"', "matiere.mf2_kin.height",
      "luminance de la couleur de base, lissée", "base color luminance, smoothed"),
    L(F, 1727, '"gradient (Sobel cyclique) de la hauteur"', "matiere.mf2_kin.normal",
      "gradient (Sobel cyclique) de la hauteur", "gradient (cyclic Sobel) of the height"),
    L(F, 1728, '"écart entre la hauteur et sa version floue"', "matiere.mf2_kin.ao",
      "écart entre la hauteur et sa version floue", "difference between the height and its blurred version"),
    L(F, 1729, '"luminance inversée, biaisée et contrastée"', "matiere.mf2_kin.roughness",
      "luminance inversée, biaisée et contrastée", "inverted, biased and contrasted luminance"),
    L(F, 1730, '"seuil sur la saturation et la luminance"', "matiere.mf2_kin.metallic",
      "seuil sur la saturation et la luminance", "threshold on saturation and luminance"),
    L(F, 1731, '"couleur de base masquée par un seuil de luminance"', "matiere.mf2_kin.emissive",
      "couleur de base masquée par un seuil de luminance", "base color masked by a luminance threshold"),
    L(F, 1732, '"empilement : R occlusion, V rugosité, B métal"', "matiere.mf2_kin.orm",
      "empilement : R occlusion, V rugosité, B métal", "packing: R occlusion, G roughness, B metal"),

    # ── preuve des maps : ligne de mesure ──
    L(F, 1861, '"mesure non publiée par l\'API"', "matiere.mf2_stat.non_publiee",
      "mesure non publiée par l'API", "measurement not published by the API"),
    S(F, 1862, '"médiane " + num(st.median, 0) + " · min–max " + num(st.min, 0) + "–" +\r\n'
      '    num(st.max, 0) + " · 1 % à " + num(st.p1, 0)',
      'dzT("matiere.mf2_stat.ligne", { med: num(st.median, 0), min: num(st.min, 0), max: num(st.max, 0), '
      'p1: num(st.p1, 0) })',
      {"matiere.mf2_stat.ligne": ("médiane {med} · min–max {min}–{max} · 1 % à {p1}",
                                  "median {med} · min–max {min}–{max} · 1st percentile {p1}")}),
    L(F, 1864, '" · référence de la corrélation"', "matiere.mf2_stat.reference",
      " · référence de la corrélation", " · correlation reference"),
    L(F, 1867, '" · champ constant"', "matiere.mf2_stat.constant", " · champ constant", " · constant field"),
    L(F, 1870, '" · r(couleur de base) "', "matiere.mf2_stat.r_couleur", " · r(couleur de base) ", " · r(base color) "),
    L(F, 1871, '" — dépendante, pas d\'information indépendante"', "matiere.mf2_stat.dependante",
      " — dépendante, pas d'information indépendante", " — dependent, no independent information"),
    L(F, 1872, '" — indépendante"', "matiere.mf2_stat.independante", " — indépendante", " — independent"),

    # ── noms français des maps dans la prose ──
    L(F, 1878, '"couleur de base"', "matiere.mf2_mapfr.basecolor", "couleur de base", "base color"),
    L(F, 1878, '"normale"', "matiere.mf2_mapfr.normal", "normale", "normal", contexte=True),
    L(F, 1878, '"rugosité"', "matiere.mf2_mapfr.roughness", "rugosité", "roughness"),
    L(F, 1879, '"métallicité"', "matiere.mf2_mapfr.metallic", "métallicité", "metalness"),
    X(F, 1879, '"occlusion"', "identique en anglais"),
    L(F, 1879, '"hauteur"', "matiere.mf2_mapfr.height", "hauteur", "height", contexte=True),
    L(F, 1879, '"émission"', "matiere.mf2_mapfr.emissive", "émission", "emission", contexte=True),
    X(F, 1880, '"ORM"', "nom de map des moteurs"),
    X(F, 1880, '"MaskMap"', "nom de map des moteurs (Unity HDRP)"),
    L(F, 1880, '"lissage"', "matiere.mf2_mapfr.smoothness", "lissage", "smoothness"),
    L(F, 1880, '"opacité"', "matiere.mf2_mapfr.opacity", "opacité", "opacity"),
    L(F, 1881, '"déplacement"', "matiere.mf2_mapfr.displacement", "déplacement", "displacement"),

    # ── preuve des maps : panneau ──
    S(F, 1891, '"Preuve des maps — " + (m.name || m.id)', 'dzT("matiere.mf2_preuve.titre", { nom: m.name || m.id })',
      {"matiere.mf2_preuve.titre": ("Preuve des maps — {nom}", "Map proof — {nom}")}),
    S(F, 1892, "'<p class=\"proof-wait\">Lecture des PNG servis par le backend, ' +\r\n"
      '    "ajustement affine sur la hauteur…</p>"',
      '\'<p class="proof-wait">\' + dzT("matiere.mf2_preuve.attente") + "</p>"',
      {"matiere.mf2_preuve.attente": ("Lecture des PNG servis par le backend, ajustement affine sur la hauteur…",
                                      "Reading the PNGs served by the backend, affine fit on the height…")}),
    S(F, 1923, "'<table class=\"ptab audit\"><thead><tr><th>Map</th><th>Lien déclaré</th>' +\r\n"
      '      "<th>r avec la " + esc(refFr) + "</th>" +\r\n'
      '      "<th>Part inexpliquée</th></tr></thead><tbody>" +',
      "'<table class=\"ptab audit\"><thead><tr><th>Map</th><th>' + dzT(\"matiere.mf2_audit.lien\") + '</th>' +\r\n"
      '      "<th>" + dzT("matiere.mf2_audit.r_avec", { ref: esc(refFr) }) + "</th>" +\r\n'
      '      "<th>" + dzT("matiere.mf2_audit.part") + "</th></tr></thead><tbody>" +',
      {"matiere.mf2_audit.lien": ("Lien déclaré", "Declared link"),
       "matiere.mf2_audit.r_avec": ("r avec la {ref}", "r with the {ref}"),
       "matiere.mf2_audit.part": ("Part inexpliquée", "Unexplained share")}),
    L(F, 1928, '"référence"', "matiere.mf2_audit.reference", "référence", "reference", contexte=True),
    L(F, 1929, '"champ constant"', "matiere.mf2_audit.constant", "champ constant", "constant field"),
    L(F, 1931, '" niv."', "matiere.mf2_audit.niv", " niv.", " lvl"),
    L(F, 1933, '"dérivée localement"', "matiere.mf2_audit.derivee", "dérivée localement", "derived locally"),
    S(F, 1941, 'au.tested + " des " + au.n + " maps sont passées au test ; la " + esc(refFr) +\r\n'
      '      " est la référence" +\r\n'
      '      (au.flatN ? ", et " + au.flatN + " sont des champs constants (la raison est écrite " +\r\n'
      '        "sous leur image)" : "") + "."',
      '(au.flatN\r\n'
      '      ? dzT("matiere.mf2_audit.testees_cst", { t: au.tested, n: au.n, ref: esc(refFr), c: au.flatN })\r\n'
      '      : dzT("matiere.mf2_audit.testees", { t: au.tested, n: au.n, ref: esc(refFr) }))',
      {"matiere.mf2_audit.testees_cst": (
          "{t} des {n} maps sont passées au test ; la {ref} est la référence, et {c} sont des champs constants "
          "(la raison est écrite sous leur image).",
          "{t} of the {n} maps went through the test; the {ref} is the reference, and {c} are constant fields "
          "(the reason is written under their image)."),
       "matiere.mf2_audit.testees": (
           "{t} des {n} maps sont passées au test ; la {ref} est la référence.",
           "{t} of the {n} maps went through the test; the {ref} is the reference.")}),
    L(F, 1947, '"Audit impossible : la hauteur n\'a pas pu être lue dans cette page."', "matiere.mf2_audit.impossible",
      "Audit impossible : la hauteur n'a pas pu être lue dans cette page.",
      "Audit impossible: the height map could not be read in this page."),
    S(F, 1949, 'gains.map((x) => mapLabel(x.k)).join(", ") + " : le meilleur ajustement " +\r\n'
      '        "affine sur la " + esc(refFr) + " ne laisse rien — ces maps SONT la même image " +\r\n'
      '        "re-réglée. "',
      'dzT("matiere.mf2_audit.gain", { maps: gains.map((x) => mapLabel(x.k)).join(", "), ref: esc(refFr) }) + " "',
      {"matiere.mf2_audit.gain": (
          "{maps} : le meilleur ajustement affine sur la {ref} ne laisse rien — ces maps SONT la même image re-réglée.",
          "{maps}: the best affine fit on the {ref} leaves nothing — these maps ARE the same image, re-tuned.")}),
    S(F, 1952, '"Aucune map n\'est la " + esc(refFr) + " re-réglée. La plus proche des maps " +\r\n'
      '        "dérivées, " + esc(mapLabel(au.worst.k)) + ", garde " +\r\n'
      '        fmt(au.worst.share * 100, 1) + " % de sa propre variation qu\'aucun couple (a, b) " +\r\n'
      '        "n\'explique — " + fmt(au.worst.resid, 1) + " niveaux sur 255. Un simple gain, lui, " +\r\n'
      '        "tomberait à 0,0 %, quel que soit le facteur."',
      'dzT("matiere.mf2_audit.aucune", { ref: esc(refFr), map: esc(mapLabel(au.worst.k)),\r\n'
      '          part: fmt(au.worst.share * 100, 1), resid: fmt(au.worst.resid, 1) })',
      {"matiere.mf2_audit.aucune": (
          "Aucune map n'est la {ref} re-réglée. La plus proche des maps dérivées, {map}, garde {part} % de sa "
          "propre variation qu'aucun couple (a, b) n'explique — {resid} niveaux sur 255. Un simple gain, lui, "
          "tomberait à 0,0 %, quel que soit le facteur.",
          "No map is the {ref} re-tuned. The closest derived map, {map}, keeps {part} % of its own variation that "
          "no (a, b) pair explains — {resid} levels out of 255. A plain gain would drop to 0.0 %, whatever the "
          "factor.")}),
    S(F, 1957, '" La couleur de base est le seul cas serré (" +\r\n'
      '          fmt(au.src.share * 100, 1) + " %), et c\'est attendu : c\'est l\'image source dont " +\r\n'
      '          "la " + esc(refFr) + " est tirée — le lien est déclaré sur sa ligne."',
      '" " + dzT("matiere.mf2_audit.source", { part: fmt(au.src.share * 100, 1), ref: esc(refFr) })',
      {"matiere.mf2_audit.source": (
          "La couleur de base est le seul cas serré ({part} %), et c'est attendu : c'est l'image source dont la "
          "{ref} est tirée — le lien est déclaré sur sa ligne.",
          "The base color is the only tight case ({part} %), and that is expected: it is the source image the "
          "{ref} is drawn from — the link is declared on its row.")}),
    S(F, 1983, '\'<p class="proof-note">Archive <b>\' + esc(mani.archive) + "</b> — " +\r\n'
      '      ((mani.entries || []).filter((e) => e.selected !== false).length + (mani.extras || []).length) +\r\n'
      '      " fichiers cochés par défaut, " + (mani.exact ? "" : "≈ ") + fmtBytes(mani.total_bytes) +\r\n'
      '      ". Les lignes grisées ne partent pas par défaut ; le bloc Export de " +\r\n'
      '      "l\'inspecteur permet de les cocher, et de changer de convention, de " +\r\n'
      '      "définition et de profondeur.</p>"',
      '\'<p class="proof-note">\' + dzT("matiere.mf2_zip.archive", { nom: esc(mani.archive),\r\n'
      '        n: (mani.entries || []).filter((e) => e.selected !== false).length + (mani.extras || []).length,\r\n'
      '        taille: (mani.exact ? "" : "≈ ") + fmtBytes(mani.total_bytes) }) + "</p>"',
      {"matiere.mf2_zip.archive": (
          "Archive <b>{nom}</b> — {n} fichiers cochés par défaut, {taille}. Les lignes grisées ne partent pas par "
          "défaut ; le bloc Export de l'inspecteur permet de les cocher, et de changer de convention, de définition "
          "et de profondeur.",
          "Archive <b>{nom}</b> — {n} files checked by default, {taille}. Greyed-out rows are left out by default; "
          "the inspector's Export block lets you check them, and change the naming convention, resolution and bit "
          "depth.")}),
    S(F, 1989, '\'<p class="proof-note">Bordereau indisponible : \' + esc(maniErr || "—")',
      '\'<p class="proof-note">\' + dzT("matiere.mf2_zip.indispo", { err: esc(maniErr || "—") })',
      {"matiere.mf2_zip.indispo": ("Bordereau indisponible : {err}", "Manifest unavailable: {err}")}),
    S(F, 1993, '\'<p class="proof-lead"><b>Les \' + kinds.length + " maps du jeu sont " +\r\n'
      '      "livrées</b> — c\'est le compte du bandeau, et il ne bouge pas d\'une " +\r\n'
      '      "matière à l\'autre. " +\r\n'
      '      (kinds.length - ninf\r\n'
      '        ? "Sur celle-ci, " + (kinds.length - ninf) + " sont des champs " +\r\n'
      '          "constants : " + esc(flatReasons(m).join(" ; ")) + ". Fait sur la " +\r\n'
      '          "matière, pas map manquante — la mesure est sous chaque image."\r\n'
      '        : "Les " + kinds.length + " portent de l\'information : aucun champ " +\r\n'
      '          "constant sur celle-ci.") +\r\n'
      '      " Les images ci-dessous sont les PNG servis par le backend, pas des " +\r\n'
      '      "aperçus reconstitués.</p>" +\r\n'
      '    \'<div class="pgrid">\' + cells + "</div>" +\r\n'
      '    \'<h4 class="proof-h">Ces maps sont-elles la même, re-réglée ? — le test</h4>\' +\r\n'
      '    \'<p class="proof-sub">« Un réglage de gain de plus sur le même champ » s’écrit \' +\r\n'
      '      "<b>map = a × " + esc(refFr) + " + b</b>. On cherche donc le meilleur couple " +\r\n'
      '      "(a, b) au sens des moindres carrés, sur la luminance de chaque PNG en " +\r\n'
      '      PROOF_N + "×" + PROOF_N + ", et on mesure ce qu\'il RESTE — en part de la variation " +\r\n'
      '      "propre de la map, pour qu\'une map de faible amplitude ne passe pas le test par " +\r\n'
      '      "sa seule platitude. Un gain, quel qu\'il soit, ne laisse rien.</p>" +\r\n'
      '    tab +\r\n'
      '    \'<p class="proof-verdict\' + (gains.length ? " bad" : "") + \'">\' + verdict + "</p>" +\r\n'
      '    \'<h4 class="proof-h">Ce que contient le ZIP de cette carte</h4>\' +\r\n'
      '    \'<p class="proof-sub">Convention standard · \' + num(m.res, 2048) + "² · 8 bits — " +\r\n'
      '      "les réglages qu\'applique le bouton ZIP de la carte.</p>" + zip;',
      '\'<p class="proof-lead">\' + dzT("matiere.mf2_preuve.lead", { n: kinds.length }) + " " +\r\n'
      '      (kinds.length - ninf\r\n'
      '        ? dzT("matiere.mf2_preuve.lead_cst", { c: kinds.length - ninf, raisons: esc(flatReasons(m).join(" ; ")) })\r\n'
      '        : dzT("matiere.mf2_preuve.lead_aucune", { n: kinds.length })) +\r\n'
      '      " " + dzT("matiere.mf2_preuve.lead_png") + "</p>" +\r\n'
      '    \'<div class="pgrid">\' + cells + "</div>" +\r\n'
      '    \'<h4 class="proof-h">\' + dzT("matiere.mf2_preuve.test_h") + "</h4>" +\r\n'
      '    \'<p class="proof-sub">\' + dzT("matiere.mf2_preuve.test_sub", { ref: esc(refFr), n: PROOF_N }) + "</p>" +\r\n'
      '    tab +\r\n'
      '    \'<p class="proof-verdict\' + (gains.length ? " bad" : "") + \'">\' + verdict + "</p>" +\r\n'
      '    \'<h4 class="proof-h">\' + dzT("matiere.mf2_preuve.zip_h") + "</h4>" +\r\n'
      '    \'<p class="proof-sub">\' + dzT("matiere.mf2_preuve.zip_sub", { res: num(m.res, 2048) }) + "</p>" + zip;',
      {"matiere.mf2_preuve.lead": (
          "<b>Les {n} maps du jeu sont livrées</b> — c'est le compte du bandeau, et il ne bouge pas d'une matière "
          "à l'autre.",
          "<b>All {n} maps of the set are delivered</b> — that is the count in the banner, and it does not change "
          "from one material to another."),
       "matiere.mf2_preuve.lead_cst": (
           "Sur celle-ci, {c} sont des champs constants : {raisons}. Fait sur la matière, pas map manquante — la "
           "mesure est sous chaque image.",
           "On this one, {c} are constant fields: {raisons}. A fact about the material, not a missing map — the "
           "measurement is under each image."),
       "matiere.mf2_preuve.lead_aucune": ("Les {n} portent de l'information : aucun champ constant sur celle-ci.",
                                          "All {n} carry information: no constant field on this one."),
       "matiere.mf2_preuve.lead_png": (
           "Les images ci-dessous sont les PNG servis par le backend, pas des aperçus reconstitués.",
           "The images below are the PNGs served by the backend, not rebuilt previews."),
       "matiere.mf2_preuve.test_h": ("Ces maps sont-elles la même, re-réglée ? — le test",
                                     "Are these maps the same one, re-tuned? — the test"),
       "matiere.mf2_preuve.test_sub": (
           "« Un réglage de gain de plus sur le même champ » s’écrit <b>map = a × {ref} + b</b>. On cherche donc le "
           "meilleur couple (a, b) au sens des moindres carrés, sur la luminance de chaque PNG en {n}×{n}, et on "
           "mesure ce qu'il RESTE — en part de la variation propre de la map, pour qu'une map de faible amplitude ne "
           "passe pas le test par sa seule platitude. Un gain, quel qu'il soit, ne laisse rien.",
           "“One more gain tweak on the same field” reads <b>map = a × {ref} + b</b>. So we look for the best "
           "(a, b) pair in the least-squares sense, on the luminance of each PNG at {n}×{n}, and measure what is "
           "LEFT — as a share of the map's own variation, so that a low-amplitude map cannot pass the test through "
           "flatness alone. A gain, whatever it is, leaves nothing."),
       "matiere.mf2_preuve.zip_h": ("Ce que contient le ZIP de cette carte", "What this card's ZIP contains"),
       "matiere.mf2_preuve.zip_sub": (
           "Convention standard · {res}² · 8 bits — les réglages qu'applique le bouton ZIP de la carte.",
           "Standard convention · {res}² · 8 bits — the settings the card's ZIP button applies.")}),
    L(F, 2020, '" Télécharger ce ZIP"', "matiere.mf2_preuve.telecharger", " Télécharger ce ZIP", " Download this ZIP"),

    # ── toasts ──
    S(F, 2040, '"Invite réutilisée : « " + (m.prompt || "") + " »"',
      'dzT("matiere.mf2_toast.invite", { p: m.prompt || "" })',
      {"matiere.mf2_toast.invite": ("Invite réutilisée : « {p} »", "Prompt reused: “{p}”")}),
    S(F, 2050, '"Matière dupliquée (gratuit, local) : « " + (d.material.name || d.material.id) + " »."',
      'dzT("matiere.mf2_toast.dupliquee", { nom: d.material.name || d.material.id })',
      {"matiere.mf2_toast.dupliquee": ("Matière dupliquée (gratuit, local) : « {nom} ».",
                                       "Material duplicated (free, local): “{nom}”.")}),
    S(F, 2052, '"Duplication impossible : " + e.message', 'dzT("matiere.mf2_toast.dup_impossible", { msg: e.message })',
      {"matiere.mf2_toast.dup_impossible": ("Duplication impossible : {msg}", "Could not duplicate: {msg}")}),
    L(F, 2071, '"Matière supprimée."', "matiere.mf2_toast.supprimee", "Matière supprimée.", "Material deleted."),
    S(F, 2072, '"Suppression impossible : " + e.message', 'dzT("matiere.mf2_toast.sup_impossible", { msg: e.message })',
      {"matiere.mf2_toast.sup_impossible": ("Suppression impossible : {msg}", "Could not delete: {msg}")}),

    # ── en-tête de l'éditeur ──
    S(F, 2136, '"Définition de cette matière, fixée à sa forge. Le segment " +\r\n'
      '    "« Définition source » du rail gauche règle la prochaine ; « Taille à " +\r\n'
      '    "l\'export », dans l\'inspecteur, ne touche qu\'au livrable."',
      'dzT("matiere.mf2_ed.meta")',
      {"matiere.mf2_ed.meta": (
          "Définition de cette matière, fixée à sa forge. Le segment « Définition source » du rail gauche règle la "
          "prochaine ; « Taille à l'export », dans l'inspecteur, ne touche qu'au livrable.",
          "Resolution of this material, set when it was forged. The “Source resolution” segment in the left rail "
          "sets the next one; “Export size”, in the inspector, only affects the deliverable.")}),
    L(F, 2155, '"Aperçu"', "matiere.mf2_insp.apercu", "Aperçu", "Preview", contexte=True),

    # ── inspecteur : résumés des groupes ──
    S(F, 2192, 'fmt(p.metallic) + " mét · " + fmt(p.roughness) + " rug"',
      'dzT("matiere.mf2_dig.base", { m: fmt(p.metallic), r: fmt(p.roughness) })',
      {"matiere.mf2_dig.base": ("{m} mét · {r} rug", "{m} met · {r} rough")}),
    S(F, 2193, '"relief ×" + fmt(p.normal_scale, 1) + " · répétition ×" + trim0(fmt(p.tiling, 2))',
      'dzT("matiere.mf2_dig.surface", { r: fmt(p.normal_scale, 1), t: trim0(fmt(p.tiling, 2)) })',
      {"matiere.mf2_dig.surface": ("relief ×{r} · répétition ×{t}", "bump ×{r} · tiling ×{t}")}),
    S(F, 2195, 'fmt(p.clearcoat) + " · rug " + fmt(p.clearcoat_roughness)',
      'dzT("matiere.mf2_dig.clearcoat", { c: fmt(p.clearcoat), r: fmt(p.clearcoat_roughness) })',
      {"matiere.mf2_dig.clearcoat": ("{c} · rug {r}", "{c} · rough {r}")}),
    S(F, 2196, '"duvet " + fmt(p.sheen)', 'dzT("matiere.mf2_dig.sheen", { s: fmt(p.sheen) })',
      {"matiere.mf2_dig.sheen": ("duvet {s}", "sheen {s}")}),
    L(F, 2217, '"Groupe resté à ses valeurs par défaut."', "matiere.mf2_grp.neutre",
      "Groupe resté à ses valeurs par défaut.", "Group left at its default values."),

    # ── inspecteur : ligne de propriété ──
    S(F, 2241, 'aria-label="Aide">', 'aria-label="\' + dzT("matiere.mf2_prop.aide") + \'">',
      {"matiere.mf2_prop.aide": ("Aide", "Help")}),
    S(F, 2256, '"Ce que fait « " + row.l + " »"', 'dzT("matiere.mf2_prop.ce_que_fait", { l: row.l })',
      {"matiere.mf2_prop.ce_que_fait": ("Ce que fait « {l} »", "What “{l}” does")}),
    S(F, 2272, '"défaut " + fmt(def, dec) + " — double-clic sur le libellé pour y revenir"',
      'dzT("matiere.mf2_prop.defaut", { v: fmt(def, dec) })',
      {"matiere.mf2_prop.defaut": ("défaut {v} — double-clic sur le libellé pour y revenir",
                                   "default {v} — double-click the label to go back to it")}),
    L(F, 2280, '"Valeur exacte : tape-la, ou règle-la avec ↑ ↓"', "matiere.mf2_prop.valeur",
      "Valeur exacte : tape-la, ou règle-la avec ↑ ↓", "Exact value: type it, or adjust it with ↑ ↓"),
    S(F, 2307, 'row.l + " — double-clic : retour au défaut (" + fmt(def, dec) + (row.u || "") + ")"',
      'dzT("matiere.mf2_prop.retour_defaut", { l: row.l, v: fmt(def, dec) + (row.u || "") })',
      {"matiere.mf2_prop.retour_defaut": ("{l} — double-clic : retour au défaut ({v})",
                                          "{l} — double-click: back to default ({v})")}),
    L(F, 2321, '"Hexadécimal — collable depuis n’importe quelle charte"', "matiere.mf2_prop.hex",
      "Hexadécimal — collable depuis n’importe quelle charte", "Hexadecimal — paste it from any style guide"),
    S(F, 2332, 'row.l + " — double-clic : retour au défaut (" + def + ")"',
      'dzT("matiere.mf2_prop.retour_defaut", { l: row.l, v: def })',
      {"matiere.mf2_prop.retour_defaut": ("{l} — double-clic : retour au défaut ({v})",
                                          "{l} — double-click: back to default ({v})")}),
    S(F, 2367, '\'<em class="grp-mod" title="\' + mods + \' réglage(s) hors défaut">\'',
      '\'<em class="grp-mod" title="\' + dzT("matiere.mf2_grp.hors_defaut", { n: mods }) + \'">\'',
      {"matiere.mf2_grp.hors_defaut": ("{n} réglage(s) hors défaut", "{n} setting(s) off default")}),
    L(F, 2374, '"Inspecteur"', "matiere.mf2_insp.inspecteur", "Inspecteur", "Inspector"),

    # ── inspecteur : maps de texture ──
    S(F, 2423, 'grpSummary("Maps de texture",\r\n'
      '    (Object.keys(mstats).length\r\n'
      '      ? nmaps + " livrées" + (ncst ? " · " + ncst + " constante" +\r\n'
      '        (ncst > 1 ? "s" : "") : "")\r\n'
      '      : nmaps + " générées"), 0);',
      'grpSummary(dzT("matiere.mf2_maps.titre"),\r\n'
      '    (Object.keys(mstats).length\r\n'
      '      ? dzT("matiere.mf2_maps.livrees", { n: nmaps }) + (ncst ? " · " + (ncst > 1\r\n'
      '        ? dzT("matiere.mf2_maps.constantes", { n: ncst }) : dzT("matiere.mf2_maps.constante", { n: ncst })) : "")\r\n'
      '      : dzT("matiere.mf2_maps.generees", { n: nmaps })), 0);',
      {"matiere.mf2_maps.titre": ("Maps de texture", "Texture maps"),
       "matiere.mf2_maps.livrees": ("{n} livrées", "{n} delivered"),
       "matiere.mf2_maps.constantes": ("{n} constantes", "{n} constant maps"),
       "matiere.mf2_maps.constante": ("{n} constante", "{n} constant map"),
       "matiere.mf2_maps.generees": ("{n} générées", "{n} generated")}),
    S(F, 2438, '" — moyenne " + fmt(st.mean, 1) + "/255"',
      '" — " + dzT("matiere.mf2_maps.moyenne", { v: fmt(st.mean, 1) })',
      {"matiere.mf2_maps.moyenne": ("moyenne {v}/255", "mean {v}/255")}),
    L(F, 2442, '"Cliquer pour télécharger cette map en pleine résolution"', "matiere.mf2_maps.cliquer",
      "Cliquer pour télécharger cette map en pleine résolution", "Click to download this map at full resolution"),
    L(F, 2443, '" — non générée"', "matiere.mf2_maps.non_generee", " — non générée", " — not generated"),
    S(F, 2456, 'note.innerHTML = "height et ORM en plus des six usuelles ; les <b>" + nmaps +\r\n'
      '    "</b> partent dans l\'archive, toujours. " +\r\n'
      '    (cstWhy.length\r\n'
      '      ? "Sur cette matière, " + (cstWhy.length > 1 ? "les " + cstWhy.length +\r\n'
      '          " maps suivantes sont des champs constants" : "une map est un champ " +\r\n'
      '          "constant") + " : " + esc(cstWhy.join(" ; ")) + ". Un moteur attend " +\r\n'
      '        "ces fichiers et les reçoit — c\'est la matière qui est unie là, pas la " +\r\n'
      '        "map qui manque. "\r\n'
      '      : "Les " + nmaps + " portent de l\'information sur cette matière. ") +\r\n'
      '    "L\'ORM empile trois maps dans un seul fichier — <b>R</b> occlusion, " +\r\n'
      '    "<b>V</b> rugosité, <b>B</b> métal — d\'où sa couleur. Clique une map : son " +\r\n'
      '    "PNG pleine résolution se télécharge.";',
      'note.innerHTML = dzT("matiere.mf2_maps.note_tete", { n: nmaps }) + " " +\r\n'
      '    (cstWhy.length\r\n'
      '      ? (cstWhy.length > 1\r\n'
      '          ? dzT("matiere.mf2_maps.note_cst_n", { n: cstWhy.length, raisons: esc(cstWhy.join(" ; ")) })\r\n'
      '          : dzT("matiere.mf2_maps.note_cst_1", { raisons: esc(cstWhy.join(" ; ")) }))\r\n'
      '      : dzT("matiere.mf2_maps.note_aucune", { n: nmaps })) + " " +\r\n'
      '    dzT("matiere.mf2_maps.note_orm");',
      {"matiere.mf2_maps.note_tete": (
          "height et ORM en plus des six usuelles ; les <b>{n}</b> partent dans l'archive, toujours.",
          "height and ORM on top of the usual six; all <b>{n}</b> always go into the archive."),
       "matiere.mf2_maps.note_cst_n": (
           "Sur cette matière, les {n} maps suivantes sont des champs constants : {raisons}. Un moteur attend ces "
           "fichiers et les reçoit — c'est la matière qui est unie là, pas la map qui manque.",
           "On this material, the following {n} maps are constant fields: {raisons}. An engine expects these files "
           "and gets them — it is the material that is flat there, not the map that is missing."),
       "matiere.mf2_maps.note_cst_1": (
           "Sur cette matière, une map est un champ constant : {raisons}. Un moteur attend ces fichiers et les "
           "reçoit — c'est la matière qui est unie là, pas la map qui manque.",
           "On this material, one map is a constant field: {raisons}. An engine expects these files and gets them "
           "— it is the material that is flat there, not the map that is missing."),
       "matiere.mf2_maps.note_aucune": ("Les {n} portent de l'information sur cette matière.",
                                        "All {n} carry information on this material."),
       "matiere.mf2_maps.note_orm": (
           "L'ORM empile trois maps dans un seul fichier — <b>R</b> occlusion, <b>V</b> rugosité, <b>B</b> métal — "
           "d'où sa couleur. Clique une map : son PNG pleine résolution se télécharge.",
           "ORM packs three maps into a single file — <b>R</b> occlusion, <b>G</b> roughness, <b>B</b> metal — "
           "hence its color. Click a map to download its full-resolution PNG.")}),

    # ── inspecteur : dérivation ──
    L(F, 2480, '"Réglages de dérivation"', "matiere.mf2_deriv.titre", "Réglages de dérivation", "Derivation settings"),
    S(F, 2486, '"Calcul des maps secondaires depuis la couleur de base, en convolutions " +\r\n'
      '    "<b>cycliques</b> : le raccord mesuré reste intact. Recalcul local et <b>gratuit</b>."',
      'dzT("matiere.mf2_deriv.note")',
      {"matiere.mf2_deriv.note": (
          "Calcul des maps secondaires depuis la couleur de base, en convolutions <b>cycliques</b> : le raccord "
          "mesuré reste intact. Recalcul local et <b>gratuit</b>.",
          "Secondary maps are computed from the base color with <b>cyclic</b> convolutions: the measured seam stays "
          "intact. Local and <b>free</b> recompute.")}),
    L(F, 2495, '" Re-dériver les maps"', "matiere.mf2_deriv.bouton", " Re-dériver les maps", " Re-derive maps"),

    # ── filtre, pastilles, enregistrement ──
    S(F, 2541, '"Aucun réglage pour « " + state.propQ + " »."', 'dzT("matiere.mf2_filtre.aucun", { q: state.propQ })',
      {"matiere.mf2_filtre.aucun": ("Aucun réglage pour « {q} ».", "No setting for “{q}”.")}),
    S(F, 2582, 'n + " réglage(s) hors défaut"', 'dzT("matiere.mf2_grp.hors_defaut", { n: n })',
      {"matiere.mf2_grp.hors_defaut": ("{n} réglage(s) hors défaut", "{n} setting(s) off default")}),
    S(F, 2650, '"Enregistrement impossible : " + e.message', 'dzT("matiere.mf2_toast.enreg_impossible", { msg: e.message })',
      {"matiere.mf2_toast.enreg_impossible": ("Enregistrement impossible : {msg}", "Could not save: {msg}")}),
]
