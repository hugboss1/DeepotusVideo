"""t147 — gltf : js/mod-gltf.js entier (pièce 08 · Export 3D du Card Forge) : coquille, réglages, livrables,
visionneuse, bordereau, relevés de densité / 16 bits / pivot / dossier, état vide, toasts et messages d'erreur
montrés (throw attrapés puis affichés). Les phrases coupées en concaténations deviennent UNE clé à variables.
GARDÉ : la garde de chargement, les types MIME, et tout ce qui part dans le fichier glTF/ZIP exporté ou au serveur
(rien de tel n'est écrit en dur ici : noms de fichiers et notices viennent du backend). Les noms techniques
(metallicFactor, doubleSided, KHR_*, GLB, OBJ + MTL, DXF 3DFACE, Atlas, UV, Texels, Source, Rectangles, rotation,
pivot, textures, 16 bits) sont identiques dans les deux langues et restent tels quels. Les libellés venant du
backend (finitions, pivots, livrables, notes) ne sont traduits que dans leurs listes de SECOURS."""
from outils import L, S, X, H

F = "js/mod-gltf.js"
P = "cartes.gltf."


def _crlf(s):
    return s.replace("\r\n", "\n").replace("\n", "\r\n")


def SS(ligne, avant, apres, dico):
    return S(F, ligne, _crlf(avant), _crlf(apres), {P + k: v for k, v in dico.items()})


def LL(ligne, lit, cle, fr, en, n=1, contexte=False):
    return L(F, ligne, lit, P + cle, fr, en, n=n, contexte=contexte)


def IN(ligne, txt, cle, fr, en):
    """texte au milieu d'un littéral '…' de HTML : `txt` → ' + dzT(clé) + '"""
    return S(F, ligne, txt, "' + dzT(\"" + P + cle + "\") + '", {P + cle: (fr, en)})


ENTREES = [
    X(F, 36, '"mod-gltf: js/core.js doit etre charge avant ce fichier"', "garde de chargement"),

    # ── libellés de module ──
    LL(54, '"RECTO"', "ilot_recto", "RECTO", "FRONT"),
    LL(54, '"VERSO"', "ilot_verso", "VERSO", "BACK"),
    LL(54, '"TRANCHE"', "ilot_tranche", "TRANCHE", "EDGE"),
    LL(56, '"ZIP des maps"', "zip_des_maps", "ZIP des maps", "Maps ZIP"),
    LL(56, '"Jeu complet"', "jeu_complet", "Jeu complet", "Full deck"),
    LL(57, '"3MF couleur"', "kind_3mf", "3MF couleur", "Color 3MF"),
    LL(58, '"PLY couleur/sommet"', "kind_ply", "PLY couleur/sommet", "PLY vertex color"),
    LL(58, '"Planche de contrôle"', "planche", "Planche de contrôle", "Proof sheet"),
    LL(75, '"Export 3D"', "titre", "Export 3D", "3D Export"),
    SS(121, r'''"GLB et glTF, archive des maps PNG et du maillage, "
          + "manifeste, et les dimensions physiques relues dans le fichier."''',
       r'''dzT("cartes.gltf.tete")''',
       {"tete": ("GLB et glTF, archive des maps PNG et du maillage, manifeste, et les dimensions physiques relues dans le fichier.",
                 "GLB and glTF, archive of the PNG maps and the mesh, manifest, and the physical dimensions read back from the file.")}),
    LL(128, '"format"', "pourquoi_format", "format", "format"),
    LL(129, '"cartes"', "pourquoi_cartes", "cartes", "cards"),
    LL(130, '"carte"', "pourquoi_carte", "carte", "card"),

    # ── poids ──
    SS(176, r'''v + " o"''', r'''dzT("cartes.gltf.poids_o", { v: v })''', {"poids_o": ("{v} o", "{v} B")}),
    SS(177, r'''(v / 1024).toFixed(v < 10240 ? 1 : 0) + " Kio"''',
       r'''dzT("cartes.gltf.poids_kio", { v: (v / 1024).toFixed(v < 10240 ? 1 : 0) })''', {"poids_kio": ("{v} Kio", "{v} KiB")}),
    SS(178, r'''(v / 1048576).toFixed(2) + " Mio"''',
       r'''dzT("cartes.gltf.poids_mio", { v: (v / 1048576).toFixed(2) })''', {"poids_mio": ("{v} Mio", "{v} MiB")}),
    SS(184, r'''v.toLocaleString("fr-FR") + " octets — " + weight(v)
      + " (binaire) = " + (v / 1e6).toFixed(2) + " Mo (SI, 10⁶)"''',
       r'''dzT("cartes.gltf.poids_titre", { n: v.toLocaleString("fr-FR"), b: weight(v), si: (v / 1e6).toFixed(2) })''',
       {"poids_titre": ("{n} octets — {b} (binaire) = {si} Mo (SI, 10⁶)", "{n} bytes — {b} (binary) = {si} MB (SI, 10⁶)")}),

    # ── annulation ──
    LL(219, '"rien à annuler"', "rien_a_annuler", "rien à annuler", "nothing to undo"),
    SS(222, r'''"annulé : " + h.label''', r'''dzT("cartes.gltf.annule", { label: h.label })''',
       {"annule": ("annulé : {label}", "undone: {label}")}),

    # ── coquille ──
    IN(276, "un seul matériau", "un_seul_materiau", "un seul matériau", "single material"),
    SS(279, r"""'title="Recompose l\'atlas depuis le moteur de rendu (A)">Composer</button>'""",
       r"""'title="' + dzT("cartes.gltf.composer_titre") + '">' + dzT("cartes.gltf.composer") + '</button>'""",
       {"composer_titre": ("Recompose l'atlas depuis le moteur de rendu (A)", "Recompose the atlas from the render engine (A)"),
        "composer": ("Composer", "Compose")}),
    IN(285, "Glissez-déposez un PNG ici pour utiliser votre propre atlas.", "glisser_png",
       "Glissez-déposez un PNG ici pour utiliser votre propre atlas.", "Drag and drop a PNG here to use your own atlas."),
    IN(293, "Réglages", "reglages", "Réglages", "Settings"),
    SS(294, r"""'annuler</button>'""", r"""dzT("cartes.gltf.annuler") + '</button>'""", {"annuler": ("annuler", "undo")}),
    IN(297, r"Définition de l\'atlas", "def_atlas", "Définition de l'atlas", "Atlas resolution"),
    IN(311, "Finition", "finition_lbl", "Finition", "Finish"),
    IN(318, "Émission", "emission_lbl", "Émission", "Emission"),
    IN(322, "celle de la finition", "celle_finition", "celle de la finition", "use the finish's"),
    IN(326, "Épaisseur", "epaisseur_lbl", "Épaisseur", "Thickness"),
    IN(330, "reprendre la pièce 05", "reprendre_p5", "reprendre la pièce 05", "use piece 05"),
    IN(334, "Textures du GLB", "textures_glb", "Textures du GLB", "GLB textures"),
    IN(348, "Livrables", "livrables_lbl", "Livrables", "Deliverables"),
    SS(356, r"""'<span><b>16 bits</b> sur height et normal dans le ZIP '
      + '<i>(plus fin sur les dégradés, ZIP plus lourd)</i></span></label>'""",
       r"""'<span>' + dzT("cartes.gltf.bits16_case") + '</span></label>'""",
       {"bits16_case": ("<b>16 bits</b> sur height et normal dans le ZIP <i>(plus fin sur les dégradés, ZIP plus lourd)</i>",
                        "<b>16-bit</b> height and normal in the ZIP <i>(smoother gradients, heavier ZIP)</i>")}),
    IN(359, "Origine du pivot", "origine_pivot", "Origine du pivot", "Pivot origin"),
    IN(362, "Portée", "portee_lbl", "Portée", "Scope"),
    SS(365, r"""'Construire l\'export</button>'""", r"""dzT("cartes.gltf.construire") + '</button>'""",
       {"construire": ("Construire l'export", "Build export")}),
    IN(375, "Le fichier livré", "fichier_livre", "Le fichier livré", "The delivered file"),
    IN(376, "le .glb construit, ouvert ici", "glb_ouvert", "le .glb construit, ouvert ici", "the built .glb, opened here"),
    IN(386, "Bordereau", "bordereau", "Bordereau", "Build report"),
    SS(387, r"""'Tout télécharger</button>'""", r"""dzT("cartes.gltf.tout_telecharger") + '</button>'""",
       {"tout_telecharger": ("Tout télécharger", "Download all")}),

    # ── câblage : libellés d'annulation / de péremption (affichés) ──
    LL(412, '"épaisseur"', "lbl_epaisseur", "épaisseur", "thickness"),
    LL(413, '"épaisseur"', "lbl_epaisseur", "épaisseur", "thickness"),
    LL(425, '"définition"', "lbl_definition", "définition", "resolution", n=2),
    LL(431, '"définition juste"', "lbl_def_juste", "définition juste", "exact resolution"),
    LL(432, '"définition"', "lbl_definition", "définition", "resolution"),
    SS(433, r'''"définition ajustée à la source : " + fit + " px"''',
       r'''dzT("cartes.gltf.def_ajustee", { fit: fit })''',
       {"def_ajustee": ("définition ajustée à la source : {fit} px", "resolution matched to the source: {fit} px")}),
    LL(436, '"épaisseur"', "lbl_epaisseur", "épaisseur", "thickness", n=2),
    LL(438, '"qualité"', "lbl_qualite", "qualité", "quality"),
    LL(440, '"émission"', "lbl_emission", "émission", "emission"),
    LL(443, '"émission"', "lbl_emission", "émission", "emission"),
    LL(499, '"définition"', "lbl_definition", "définition", "resolution", n=2),

    # ── atlas ──
    LL(652, '"composition de l\'atlas…"', "composition", "composition de l'atlas…", "composing atlas…"),
    LL(656, '"encodage de l\'atlas impossible"', "encodage_ko", "encodage de l'atlas impossible", "atlas encoding failed"),
    X(F, 657, '"image/png"', "type MIME"),
    SS(664, r'''"dépôt de l'atlas refusé (" + r.status + ")"''',
       r'''dzT("cartes.gltf.depot_refuse", { status: r.status })''',
       {"depot_refuse": ("dépôt de l'atlas refusé ({status})", "atlas upload rejected ({status})")}),
    SS(670, r'''"atlas " + res + " x " + res + " composé — " + weight(blob.size)''',
       r'''dzT("cartes.gltf.atlas_compose", { res: res, poids: weight(blob.size) })''',
       {"atlas_compose": ("atlas {res} x {res} composé — {poids}", "atlas {res} x {res} composed — {poids}")}),
    LL(690, '"encodage de l\'atlas impossible"', "encodage_ko", "encodage de l'atlas impossible", "atlas encoding failed"),
    X(F, 691, '"image/png"', "type MIME"),
    SS(693, r'''"dépôt de l'atlas " + (i + 1) + " refusé ("
        + r.status + ")"''',
       r'''dzT("cartes.gltf.depot_n_refuse", { n: i + 1, status: r.status })''',
       {"depot_n_refuse": ("dépôt de l'atlas {n} refusé ({status})", "atlas {n} upload rejected ({status})")}),
    LL(709, '"un PNG ou un JPEG est attendu"', "png_attendu", "un PNG ou un JPEG est attendu", "a PNG or JPEG is expected"),
    LL(711, '"import de l\'atlas…"', "import_atlas", "import de l'atlas…", "importing atlas…"),
    SS(717, r'''("import refusé (" + r.status + ")")''', r'''dzT("cartes.gltf.import_refuse", { status: r.status })''',
       {"import_refuse": ("import refusé ({status})", "import rejected ({status})")}),
    SS(729, r'''"atlas importé : " + file.name + " — " + d.atlas.res.join(" x ")''',
       r'''dzT("cartes.gltf.atlas_importe", { nom: file.name, res: d.atlas.res.join(" x ") })''',
       {"atlas_importe": ("atlas importé : {nom} — {res}", "atlas imported: {nom} — {res}")}),

    # ── vues ──
    LL(741, '"ce qui part dans le fichier"', "vue_atlas", "ce qui part dans le fichier", "what goes into the file"),
    LL(742, '"le fil de fer UV du maillage livré"', "vue_uv", "le fil de fer UV du maillage livré", "UV wireframe of the delivered mesh"),
    LL(743, '"Îlots"', "ilots", "Îlots", "Islands"),
    LL(743, '"les rectangles de l\'atlas"', "vue_ilots", "les rectangles de l'atlas", "the atlas rectangles"),
    LL(744, '"Canaux"', "canaux", "Canaux", "Channels"),
    LL(745, '"les maps côte à côte — cochez « Planche de contrôle » et construisez"', "vue_canaux",
       "les maps côte à côte — cochez « Planche de contrôle » et construisez",
       "the maps side by side — tick “Proof sheet” and build"),
    LL(791, '"cochez « Planche de contrôle »"', "cochez_planche", "cochez « Planche de contrôle »", "tick “Proof sheet”"),
    LL(792, '"puis construisez (E) :"', "puis_construisez", "puis construisez (E) :", "then build (E):"),
    SS(793, r'''(n ? n + " canaux" : "les canaux") + " seront ici."''',
       r'''n ? dzT("cartes.gltf.n_canaux_ici", { n: n }) : dzT("cartes.gltf.canaux_ici")''',
       {"n_canaux_ici": ("{n} canaux seront ici.", "{n} channels will appear here."),
        "canaux_ici": ("les canaux seront ici.", "the channels will appear here.")}),
    SS(823, r'''tris.length + " triangles UV · " + (me.uv_islands || "?")
        + " îlots mesurés (" + (me.uv_islands_tri || []).join("+") + ")"''',
       r'''dzT("cartes.gltf.uv_bandeau", { tris: tris.length, ilots: (me.uv_islands || "?"), detail: (me.uv_islands_tri || []).join("+") })''',
       {"uv_bandeau": ("{tris} triangles UV · {ilots} îlots mesurés ({detail})",
                       "{tris} UV triangles · {ilots} measured islands ({detail})")}),
    SS(856, r'''"un seul matériau — <b>"
        + (me.uv_islands != null ? me.uv_islands : "?")
        + "</b> îlots UV mesurés sur le maillage livré"''',
       r'''dzT("cartes.gltf.sous_titre_ilots", { n: (me.uv_islands != null ? me.uv_islands : "?") })''',
       {"sous_titre_ilots": ("un seul matériau — <b>{n}</b> îlots UV mesurés sur le maillage livré",
                             "single material — <b>{n}</b> UV islands measured on the delivered mesh")}),
    SS(909, r'''"L'atlas déposé date d'avant « " + esc(why)
      + " ». <button class=\"lnk\" data-act=\"compose\">recomposer</button>"''',
       r'''dzT("cartes.gltf.perime", { why: esc(why) })''',
       {"perime": ('L\'atlas déposé date d\'avant « {why} ». <button class="lnk" data-act="compose">recomposer</button>',
                   'The uploaded atlas predates “{why}”. <button class="lnk" data-act="compose">recompose</button>')}),

    # ── construction ──
    LL(924, '"API cartes indisponible"', "api_ko", "API cartes indisponible", "Cards API unavailable"),
    LL(926, '"cochez au moins un livrable"', "cochez_livrable", "cochez au moins un livrable", "tick at least one deliverable"),
    LL(935, '"construction — maps PBR, GLB, glTF, ZIP…"', "construction", "construction — maps PBR, GLB, glTF, ZIP…",
       "building — PBR maps, GLB, glTF, ZIP…"),
    SS(956, r'''BUILD.files.length + " fichier(s) · " + weight(BUILD.total_bytes)
        + " · " + ((Date.now() - t0) / 1000).toFixed(1) + " s"''',
       r'''dzT("cartes.gltf.toast_build", { n: BUILD.files.length, poids: weight(BUILD.total_bytes), s: ((Date.now() - t0) / 1000).toFixed(1) })''',
       {"toast_build": ("{n} fichier(s) · {poids} · {s} s", "{n} file(s) · {poids} · {s} s")}),
    LL(973, '"construisez l\'export d\'abord (E)"', "construisez_dabord", "construisez l'export d'abord (E)", "build the export first (E)"),
    LL(974, '"téléchargement…"', "telechargement", "téléchargement…", "downloading…"),
    LL(1000, '"définition juste"', "lbl_def_juste", "définition juste", "exact resolution"),
    LL(1001, '"définition"', "lbl_definition", "définition", "resolution"),
    SS(1002, r'''"définition ajustée à la source : " + fit + " px"''',
       r'''dzT("cartes.gltf.def_ajustee", { fit: fit })''',
       {"def_ajustee": ("définition ajustée à la source : {fit} px", "resolution matched to the source: {fit} px")}),
    LL(1007, '"livrables"', "lbl_livrables", "livrables", "deliverables"),
    LL(1008, '"livrables"', "lbl_livrables", "livrables", "deliverables"),
    LL(1009, '"STL et 3MF cochés — reconstruisez pour les obtenir"', "stl_coches",
       "STL et 3MF cochés — reconstruisez pour les obtenir", "STL and 3MF ticked — rebuild to get them"),

    # ── visionneuse ──
    SS(1030, r"""'<p class="empty-note sm">La visionneuse 3D '
        + '(/assets/model-viewer.min.js) n\'est pas chargée. Le fichier, lui, '
        + 'est construit et téléchargeable.</p>'""",
       r"""'<p class="empty-note sm">' + dzT("cartes.gltf.visionneuse_absente") + '</p>'""",
       {"visionneuse_absente": ("La visionneuse 3D (/assets/model-viewer.min.js) n'est pas chargée. Le fichier, lui, est construit et téléchargeable.",
                                "The 3D viewer (/assets/model-viewer.min.js) is not loaded. The file itself is built and downloadable.")}),
    LL(1054, '"la visionneuse n\'a pas pu ouvrir le GLB"', "visionneuse_ko", "la visionneuse n'a pas pu ouvrir le GLB",
       "the viewer could not open the GLB"),
    SS(1099, r"""'<span><b>' + mm4(buf) + ' mm</b> — les float32 de POSITION relus '
        + 'dans le chunk binaire du .glb, à l\'échelle du nœud</span>'""",
       r"""'<span>' + dzT("cartes.gltf.mes_buf", { mm: mm4(buf) }) + '</span>'""",
       {"mes_buf": ("<b>{mm} mm</b> — les float32 de POSITION relus dans le chunk binaire du .glb, à l'échelle du nœud",
                    "<b>{mm} mm</b> — the POSITION float32 values read back from the .glb binary chunk, at node scale")}),
    SS(1104, r"""'<span>la visionneuse n\'a pas rendu de boîte englobante pour ce '
        + 'fichier.</span>'""",
       r"""'<span>' + dzT("cartes.gltf.mes_sans_boite") + '</span>'""",
       {"mes_sans_boite": ("la visionneuse n'a pas rendu de boîte englobante pour ce fichier.",
                           "the viewer returned no bounding box for this file.")}),
    SS(1118, r"""'<span>un moteur 3D dans cette page d\'un côté, les octets du '
          + 'fichier de l\'autre : deux chemins sans rien en commun, '
          + '<b class="cf-gltf-ok">le même nombre</b>.</span>'""",
       r"""'<span>' + dzT("cartes.gltf.mes_accord") + '</span>'""",
       {"mes_accord": ('un moteur 3D dans cette page d\'un côté, les octets du fichier de l\'autre : deux chemins sans rien en commun, <b class="cf-gltf-ok">le même nombre</b>.',
                       'a 3D engine in this page on one side, the file bytes on the other: two paths with nothing in common, <b class="cf-gltf-ok">the same number</b>.')}),
    SS(1121, r"""'<span class="cf-gltf-ko">les deux lectures ne donnent pas le même '
          + 'nombre : ' + um.toFixed(1) + ' µm d\'un relevé à l\'autre sur '
          + 'l\'axe le plus large.</span>'""",
       r"""'<span class="cf-gltf-ko">' + dzT("cartes.gltf.mes_desaccord", { um: um.toFixed(1) }) + '</span>'""",
       {"mes_desaccord": ("les deux lectures ne donnent pas le même nombre : {um} µm d'un relevé à l'autre sur l'axe le plus large.",
                          "the two readings disagree: {um} µm between them on the widest axis.")}),
    SS(1128, r"""'<span><b>' + mm4(mm) + ' mm</b> — la boîte englobante '
      + 'que la visionneuse a mesurée en ouvrant le .glb</span>'""",
       r"""'<span>' + dzT("cartes.gltf.mes_viewer", { mm: mm4(mm) }) + '</span>'""",
       {"mes_viewer": ("<b>{mm} mm</b> — la boîte englobante que la visionneuse a mesurée en ouvrant le .glb",
                       "<b>{mm} mm</b> — the bounding box the viewer measured when opening the .glb")}),

    # ── définition ──
    SS(1159, r'''"raccourci " + (i + 1)''', r'''dzT("cartes.gltf.raccourci_n", { n: i + 1 })''',
       {"raccourci_n": ("raccourci {n}", "shortcut {n}")}),
    LL(1160, '"définition"', "lbl_definition", "définition", "resolution", n=2),
    LL(1170, '"définition libre de 256 à 4096 px."', "def_libre", "définition libre de 256 à 4096 px.",
       "any resolution from 256 to 4096 px."),
    SS(1186, r"""'Face dans l\'atlas : <b>' + dens.front_px.join(" x ")
        + ' px</b> — <b>' + dpi[0] + ' x ' + dpi[1] + ' DPI</b> de texels'""",
       r"""dzT("cartes.gltf.face_atlas", { px: dens.front_px.join(" x "), dx: dpi[0], dy: dpi[1] })""",
       {"face_atlas": ("Face dans l'atlas : <b>{px} px</b> — <b>{dx} x {dy} DPI</b> de texels",
                       "Face in the atlas: <b>{px} px</b> — <b>{dx} x {dy} DPI</b> of texels")}),
    SS(1196, r"""'l\'îlot l\'agrandit de'""", r"""dzT("cartes.gltf.verbe_agrandit")""",
       {"verbe_agrandit": ("l'îlot l'agrandit de", "the island enlarges it by")}),
    SS(1197, r"""'<b class="cf-gltf-ko">l\'îlot la réduit</b> à'""", r"""dzT("cartes.gltf.verbe_reduit")""",
       {"verbe_reduit": ('<b class="cf-gltf-ko">l\'îlot la réduit</b> à', '<b class="cf-gltf-ko">the island shrinks it</b> to')}),
    SS(1198, r"""'l\'îlot la met à l\'échelle'""", r"""dzT("cartes.gltf.verbe_echelle")""",
       {"verbe_echelle": ("l'îlot la met à l'échelle", "the island scales it by")}),
    SS(1204, r"""'Face : <b>' + dens.front_px.join(" x ") + ' px</b>, texels '
      + '<b>' + dpi[0] + ' x ' + dpi[1] + ' DPI</b> <i>(c\'est cette densité '
      + 'qui partira dans le chunk pHYs de chaque PNG)</i><br>'""",
       r"""dzT("cartes.gltf.face_texels", { px: dens.front_px.join(" x "), dx: dpi[0], dy: dpi[1] }) + '<br>'""",
       {"face_texels": ("Face : <b>{px} px</b>, texels <b>{dx} x {dy} DPI</b> <i>(c'est cette densité qui partira dans le chunk pHYs de chaque PNG)</i>",
                        "Face: <b>{px} px</b>, texels <b>{dx} x {dy} DPI</b> <i>(this is the density written to the pHYs chunk of each PNG)</i>")}),
    SS(1207, r"""'Information réelle <b class="' + (ok ? "cf-gltf-ok" : "cf-gltf-ko") + '">'
      + eff + ' DPI</b> — la source rognée fait ' + (dens.source_px || []).join(" x ")
      + ' px, ' + verbe + ' <b>x' + up[0] + '</b> et <b>x' + up[1] + '</b>. '""",
       r"""dzT("cartes.gltf.info_reelle", { cls: (ok ? "cf-gltf-ok" : "cf-gltf-ko"), eff: eff, src: (dens.source_px || []).join(" x "), verbe: verbe, ux: up[0], uy: up[1] }) + ' '""",
       {"info_reelle": ('Information réelle <b class="{cls}">{eff} DPI</b> — la source rognée fait {src} px, {verbe} <b>x{ux}</b> et <b>x{uy}</b>.',
                        'Real detail <b class="{cls}">{eff} DPI</b> — the cropped source is {src} px, {verbe} <b>x{ux}</b> and <b>x{uy}</b>.')}),
    SS(1217, r'''(ok ? "l\'export garde les " : "l\'export descend sous les ")
        + cible + " DPI posés dans la barre du document"''',
       r'''(ok ? dzT("cartes.gltf.export_garde", { cible: cible }) : dzT("cartes.gltf.export_sous", { cible: cible }))''',
       {"export_garde": ("l'export garde les {cible} DPI posés dans la barre du document",
                         "the export keeps the {cible} DPI set in the document bar"),
        "export_sous": ("l'export descend sous les {cible} DPI posés dans la barre du document",
                        "the export falls below the {cible} DPI set in the document bar")}),
    SS(1220, r"""'texels non carrés : ' + dens.anisotropy + 'x'""",
       r"""dzT("cartes.gltf.texels_non_carres", { a: dens.anisotropy })""",
       {"texels_non_carres": ("texels non carrés : {a}x", "non-square texels: {a}x")}),
    SS(1222, r"""' · <b>' + dens.useful_pct + ' %</b> des texels de l\'îlot portent '
          + 'de l\'information'""",
       r"""' · ' + dzT("cartes.gltf.texels_utiles", { pct: dens.useful_pct })""",
       {"texels_utiles": ("<b>{pct} %</b> des texels de l'îlot portent de l'information",
                          "<b>{pct}%</b> of the island's texels carry detail")}),
    SS(1240, r'''"ajuster à la source (" + fit + " px)"''', r'''dzT("cartes.gltf.ajuster_source", { fit: fit })''',
       {"ajuster_source": ("ajuster à la source ({fit} px)", "match the source ({fit} px)")}),

    # ── finition ──
    LL(1256, '"Mat (papier)"', "fin_mat", "Mat (papier)", "Matte (paper)"),
    LL(1256, '"Satiné"', "fin_satin", "Satiné", "Satin"),
    LL(1257, '"Vernis sélectif"', "fin_vernis", "Vernis sélectif", "Spot varnish"),
    LL(1257, '"Dorure à chaud"', "fin_foil", "Dorure à chaud", "Hot foil"),
    LL(1258, '"Holographique"', "fin_holo", "Holographique", "Holographic"),
    LL(1264, '"finition"', "lbl_finition", "finition", "finish"),
    SS(1279, r"""'rugosité <b>' + f.roughness + '</b> · métal <b>' + f.metallic
        + '</b> · vernis <b>' + f.clearcoat + '</b> · émission <b'
        + (eff ? '' : ' class="cf-gltf-ok"') + '>' + eff + '</b>'""",
       r"""dzT("cartes.gltf.pbr_lecture", { r: f.roughness, m: f.metallic, v: f.clearcoat, cls: (eff ? '' : ' class="cf-gltf-ok"'), e: eff })""",
       {"pbr_lecture": ("rugosité <b>{r}</b> · métal <b>{m}</b> · vernis <b>{v}</b> · émission <b{cls}>{e}</b>",
                        "roughness <b>{r}</b> · metal <b>{m}</b> · clearcoat <b>{v}</b> · emission <b{cls}>{e}</b>")}),
    SS(1282, r"""' <i>(réglage local — prime sur la finition)</i>'""",
       r"""' <i>(' + dzT("cartes.gltf.local_prime") + ')</i>'""",
       {"local_prime": ("réglage local — prime sur la finition", "local setting — overrides the finish")}),
    SS(1283, r"""' <i>(le papier n\'émet pas de lumière)</i>'""",
       r"""' <i>(' + dzT("cartes.gltf.papier_sans_lumiere") + ')</i>'""",
       {"papier_sans_lumiere": ("le papier n'émet pas de lumière", "paper emits no light")}),
    SS(1284, r"""'<br>cuits dans les maps, facteurs glTF à 1.0 · extensions écrites : <b>'
        + (ext.length ? esc(ext.join(", ")) : "aucune") + '</b>'""",
       r"""'<br>' + dzT("cartes.gltf.cuits_ext", { ext: (ext.length ? esc(ext.join(", ")) : dzT("cartes.gltf.aucune")) })""",
       {"cuits_ext": ("cuits dans les maps, facteurs glTF à 1.0 · extensions écrites : <b>{ext}</b>",
                      "baked into the maps, glTF factors at 1.0 · extensions written: <b>{ext}</b>"),
        "aucune": ("aucune", "none")}),
    LL(1287, '"les niveaux sont cuits dans les maps ; les facteurs glTF restent à 1.0"', "niveaux_cuits",
       "les niveaux sont cuits dans les maps ; les facteurs glTF restent à 1.0",
       "levels are baked into the maps; glTF factors stay at 1.0"),

    # ── émission ──
    SS(1308, r"""'celle de la finition : <b>' + emissiveEff() + '</b>'""",
       r"""dzT("cartes.gltf.emi_finition", { e: emissiveEff() })""",
       {"emi_finition": ("celle de la finition : <b>{e}</b>", "the finish's: <b>{e}</b>")}),
    SS(1310, r"""' — la map émission part câblée (emissiveTexture + map_Ke)'""",
       r"""' — ' + dzT("cartes.gltf.emi_cablee")""",
       {"emi_cablee": ("la map émission part câblée (emissiveTexture + map_Ke)",
                       "the emission map ships wired (emissiveTexture + map_Ke)")}),
    SS(1311, r"""' — à 0, aucune map émission n\'est écrite. Posez une valeur pour '
            + 'la câbler sans changer la matière (encre luminescente).'""",
       r"""' — ' + dzT("cartes.gltf.emi_zero")""",
       {"emi_zero": ("à 0, aucune map émission n'est écrite. Posez une valeur pour la câbler sans changer la matière (encre luminescente).",
                     "at 0, no emission map is written. Set a value to wire it without changing the material (glow ink).")}),
    SS(1314, r"""'réglage local <b>' + ov + '</b> — la map émission part '
        + 'câblée des deux côtés (emissiveTexture dans le GLB, map_Ke dans le '
        + 'MTL), le facteur du fichier vaudra [' + ov + ', ' + ov + ', ' + ov + ']'""",
       r"""dzT("cartes.gltf.emi_locale", { ov: ov })""",
       {"emi_locale": ("réglage local <b>{ov}</b> — la map émission part câblée des deux côtés (emissiveTexture dans le GLB, map_Ke dans le MTL), le facteur du fichier vaudra [{ov}, {ov}, {ov}]",
                       "local setting <b>{ov}</b> — the emission map ships wired on both sides (emissiveTexture in the GLB, map_Ke in the MTL), the file factor will be [{ov}, {ov}, {ov}]")}),
    SS(1318, r"""'réglage local <b>0</b> — émission éteinte, la map '
        + 'n\'est pas écrite (même sur dorure ou holographique)'""",
       r"""dzT("cartes.gltf.emi_eteinte")""",
       {"emi_eteinte": ("réglage local <b>0</b> — émission éteinte, la map n'est pas écrite (même sur dorure ou holographique)",
                        "local setting <b>0</b> — emission off, the map is not written (even on foil or holographic)")}),

    # ── épaisseur ──
    SS(1333, r"""'Carte finie : <b>' + g.trim_mm[0] + ' x ' + g.trim_mm[1]
      + ' x ' + th + ' mm</b> · source : '""",
       r"""dzT("cartes.gltf.carte_finie", { w: g.trim_mm[0], h: g.trim_mm[1], th: th })""",
       {"carte_finie": ("Carte finie : <b>{w} x {h} x {th} mm</b> · source : ",
                        "Finished card: <b>{w} x {h} x {th} mm</b> · source: ")}),
    LL(1335, '"<b>pièce 05</b>"', "src_p5", "<b>pièce 05</b>", "<b>piece 05</b>"),
    LL(1336, '"réglage local"', "reglage_local", "réglage local", "local setting"),
    LL(1336, '"défaut carte à jouer"', "defaut_carte", "défaut carte à jouer", "playing-card default"),

    # ── textures ──
    LL(1343, '"encode les deux et garde le plus léger"', "img_auto", "encode les deux et garde le plus léger",
       "encodes both and keeps the lighter one"),
    LL(1344, '"sans perte"', "img_png", "sans perte", "lossless"),
    LL(1354, '"les deux codecs sont encodés et le plus léger est retenu, texture par texture ; le bordereau montre les deux poids. <b>normal</b> et <b>orm</b> restent toujours en PNG."',
       "img_auto_lecture",
       "les deux codecs sont encodés et le plus léger est retenu, texture par texture ; le bordereau montre les deux poids. <b>normal</b> et <b>orm</b> restent toujours en PNG.",
       "both codecs are encoded and the lighter one is kept, texture by texture; the build report shows both sizes. <b>normal</b> and <b>orm</b> always stay PNG."),
    LL(1355, '"sans perte partout — le plus sûr, pas toujours le plus lourd."', "img_png_lecture",
       "sans perte partout — le plus sûr, pas toujours le plus lourd.",
       "lossless everywhere — the safest, not always the heaviest."),
    LL(1356, '"JPEG sur basecolor et emissive ; <b>normal</b> et <b>orm</b> restent en PNG (le JPEG déplacerait les canaux)."',
       "img_jpeg_lecture",
       "JPEG sur basecolor et emissive ; <b>normal</b> et <b>orm</b> restent en PNG (le JPEG déplacerait les canaux).",
       "JPEG on basecolor and emissive; <b>normal</b> and <b>orm</b> stay PNG (JPEG would shift the channels)."),

    # ── livrables (liste de secours) ──
    LL(1375, '"géométrie + matériau + textures, un seul fichier"', "fmt_glb",
       "géométrie + matériau + textures, un seul fichier", "geometry + material + textures, one single file"),
    LL(1376, '"le même en JSON, buffer en data URI"', "fmt_gltf", "le même en JSON, buffer en data URI",
       "the same in JSON, buffer as a data URI"),
    LL(1377, '"ZIP des maps"', "zip_des_maps", "ZIP des maps", "Maps ZIP"),
    LL(1377, '"les PNG nommés + manifest.json + le maillage OBJ"', "fmt_zip",
       "les PNG nommés + manifest.json + le maillage OBJ", "the named PNGs + manifest.json + the OBJ mesh"),
    LL(1378, '"le repli universel, en mm, avec ses maps"', "fmt_obj", "le repli universel, en mm, avec ses maps",
       "the universal fallback, in mm, with its maps"),
    LL(1379, '"facettes nues en mm pour l\'impression 3D"', "fmt_stl", "facettes nues en mm pour l'impression 3D",
       "bare facets in mm for 3D printing"),
    LL(1380, '"3MF (couleur)"', "fmt_3mf_lbl", "3MF (couleur)", "3MF (color)"),
    LL(1380, '"norme ouverte ISO/ASTM 52915 : mm inscrits dans le fichier et couleur par facette"', "fmt_3mf",
       "norme ouverte ISO/ASTM 52915 : mm inscrits dans le fichier et couleur par facette",
       "open standard ISO/ASTM 52915: mm recorded in the file and per-facet color"),
    LL(1381, '"PLY (couleur/sommet)"', "fmt_ply_lbl", "PLY (couleur/sommet)", "PLY (vertex color)"),
    LL(1381, '"binaire, en mm, couleur par sommet + normales + UV"', "fmt_ply",
       "binaire, en mm, couleur par sommet + normales + UV", "binary, in mm, per-vertex color + normals + UV"),
    LL(1382, '"R12, faces nues en mm ($INSUNITS = 4), pour la CAO et la découpe"', "fmt_dxf",
       "R12, faces nues en mm ($INSUNITS = 4), pour la CAO et la découpe",
       "R12, bare faces in mm ($INSUNITS = 4), for CAD and cutting"),
    LL(1383, '"Planche de contrôle"', "planche", "Planche de contrôle", "Proof sheet"),
    LL(1383, '"les canaux côte à côte dans un PNG"', "fmt_proof", "les canaux côte à côte dans un PNG",
       "the channels side by side in one PNG"),
    LL(1391, '"au moins un livrable"', "un_livrable", "au moins un livrable", "at least one deliverable"),
    LL(1392, '"livrables"', "lbl_livrables", "livrables", "deliverables"),
    SS(1413, r"""'<span>Ces deux cases ne produisent qu\'<b>une</b> archive : le '
          + '<b>ZIP des maps</b> embarque déjà l\'OBJ, le MTL et les mêmes '
          + 'PNG, l\'archive OBJ n\'en serait qu\'une seconde copie. Elle '
          + 'n\'est pas écrite.</span><br>'""",
       r"""'<span>' + dzT("cartes.gltf.zip_obj_une") + '</span><br>'""",
       {"zip_obj_une": ("Ces deux cases ne produisent qu'<b>une</b> archive : le <b>ZIP des maps</b> embarque déjà l'OBJ, le MTL et les mêmes PNG, l'archive OBJ n'en serait qu'une seconde copie. Elle n'est pas écrite.",
                        "These two boxes produce only <b>one</b> archive: the <b>Maps ZIP</b> already carries the OBJ, the MTL and the same PNGs, so the OBJ archive would just be a second copy. It is not written.")}),
    LL(1417, '"Pas encore écrits : "', "pas_encore", "Pas encore écrits : ", "Not written yet: "),

    # ── 16 bits ──
    SS(1445, r'''"Demandé. La profondeur obtenue s\'affiche ici après la construction."''',
       r'''dzT("cartes.gltf.b16_demande")''',
       {"b16_demande": ("Demandé. La profondeur obtenue s'affiche ici après la construction.",
                        "Requested. The resulting bit depth will show here after the build.")}),
    SS(1446, r'''"Décoché : height et normal sortiront en <b>8 bits</b>, le ZIP sera "
          + "d\'autant plus léger."''',
       r'''dzT("cartes.gltf.b16_decoche")''',
       {"b16_decoche": ("Décoché : height et normal sortiront en <b>8 bits</b>, le ZIP sera d'autant plus léger.",
                        "Unticked: height and normal will come out in <b>8-bit</b>, and the ZIP will be lighter.")}),
    SS(1456, r"""'<span class="cf-gltf-ok">16 bits</span> · '
          + d.levels.toLocaleString("fr-FR") + ' niveaux ('
          + d.bits_effective + ' bits utiles) contre '
          + (d.levels_8 != null ? d.levels_8 : "?") + ' en 8 bits'""",
       r"""dzT("cartes.gltf.b16_reel", { niv: d.levels.toLocaleString("fr-FR"), utiles: d.bits_effective, n8: (d.levels_8 != null ? d.levels_8 : "?") })""",
       {"b16_reel": ('<span class="cf-gltf-ok">16 bits</span> · {niv} niveaux ({utiles} bits utiles) contre {n8} en 8 bits',
                     '<span class="cf-gltf-ok">16-bit</span> · {niv} levels ({utiles} effective bits) vs {n8} in 8-bit')}),
    SS(1461, r"""' · <b>' + off.toFixed(1) + ' %</b> des échantillons <b>hors</b> '
            + 'du réseau k·257'""",
       r"""' · ' + dzT("cartes.gltf.hors_reseau", { pct: off.toFixed(1) })""",
       {"hors_reseau": ("<b>{pct} %</b> des échantillons <b>hors</b> du réseau k·257",
                        "<b>{pct}%</b> of samples <b>off</b> the k·257 lattice")}),
    SS(1472, r"""' · même image à ' + (pc.length > 1
            ? pc.map((c) => c.moyen).join(" / ") + ' niveau (max '
              + pc.map((c) => c.max).join(" / ") + ')'
            : d.accord_8.ecart_moyen + ' niveau en moyenne (max '
              + d.accord_8.ecart_max + ')')""",
       r"""' · ' + (pc.length > 1
            ? dzT("cartes.gltf.meme_image_canaux", { moy: pc.map((c) => c.moyen).join(" / "), max: pc.map((c) => c.max).join(" / ") })
            : dzT("cartes.gltf.meme_image_moy", { moy: d.accord_8.ecart_moyen, max: d.accord_8.ecart_max }))""",
       {"meme_image_canaux": ("même image à {moy} niveau (max {max})", "same image within {moy} level (max {max})"),
        "meme_image_moy": ("même image à {moy} niveau en moyenne (max {max})",
                           "same image within {moy} level on average (max {max})")}),
    SS(1478, r"""' · coût <b>+' + weight(d.cost_16) + '</b>'""",
       r"""' · ' + dzT("cartes.gltf.cout16", { poids: weight(d.cost_16) })""",
       {"cout16": ("coût <b>+{poids}</b>", "cost <b>+{poids}</b>")}),
    SS(1480, r"""'<span class="cf-gltf-ko">16 bits refusés</span> · livré en '
          + '<b>8 bits</b>, ' + d.levels + ' niveaux'""",
       r"""dzT("cartes.gltf.b16_refuse", { niv: d.levels })""",
       {"b16_refuse": ('<span class="cf-gltf-ko">16 bits refusés</span> · livré en <b>8 bits</b>, {niv} niveaux',
                       '<span class="cf-gltf-ko">16-bit rejected</span> · delivered in <b>8-bit</b>, {niv} levels')}),
    SS(1482, r"""' <i>(le conteneur aurait coûté +'
            + weight(d.refused_bytes) + ' pour '
            + (d.refused_levels != null ? d.refused_levels : "?")
            + ' valeurs distinctes)</i>'""",
       r"""' <i>' + dzT("cartes.gltf.conteneur_cout", { poids: weight(d.refused_bytes), n: (d.refused_levels != null ? d.refused_levels : "?") }) + '</i>'""",
       {"conteneur_cout": ("(le conteneur aurait coûté +{poids} pour {n} valeurs distinctes)",
                           "(the container would have cost +{poids} for {n} distinct values)")}),
    SS(1487, r"""'<span class="cf-gltf-ok">8 bits réels</span> · ' + d.levels
          + ' niveaux (' + d.bits_effective + ' bits utiles)'""",
       r"""dzT("cartes.gltf.b8_reel", { niv: d.levels, utiles: d.bits_effective })""",
       {"b8_reel": ('<span class="cf-gltf-ok">8 bits réels</span> · {niv} niveaux ({utiles} bits utiles)',
                    '<span class="cf-gltf-ok">true 8-bit</span> · {niv} levels ({utiles} effective bits)')}),
    SS(1499, r"""'Relevé sur ' + esc(how || "les octets livrés") + ' : '""",
       r"""dzT("cartes.gltf.releve_sur", { how: esc(how || dzT("cartes.gltf.octets_livres")) })""",
       {"releve_sur": ("Relevé sur {how} : ", "Measured on {how}: "),
        "octets_livres": ("les octets livrés", "the delivered bytes")}),
    SS(1501, r"""'<br><i>Seize bits : <b>' + (ms / 1000).toFixed(1) + ' s</b> dont '
        + (msd / 1000).toFixed(1) + ' s de dérivation. Décocher les rend, '
        + 'et rend aussi le poids.</i>'""",
       r"""'<br><i>' + dzT("cartes.gltf.seize_bits_temps", { s: (ms / 1000).toFixed(1), d: (msd / 1000).toFixed(1) }) + '</i>'""",
       {"seize_bits_temps": ("Seize bits : <b>{s} s</b> dont {d} s de dérivation. Décocher les rend, et rend aussi le poids.",
                             "Sixteen bits: <b>{s} s</b>, {d} s of it deriving. Unticking saves that time, and the weight too.")}),

    # ── pivot ──
    LL(1514, '"Centre"', "piv_centre", "Centre", "Center"),
    LL(1514, '"origine au centre de la boîte"', "piv_centre_note", "origine au centre de la boîte", "origin at the center of the box"),
    LL(1515, '"Posée debout"', "piv_bas", "Posée debout", "Standing"),
    LL(1515, '"le bas de la carte à y = 0"', "piv_bas_note", "le bas de la carte à y = 0", "card bottom at y = 0"),
    LL(1516, '"Couchée"', "piv_dos", "Couchée", "Lying flat"),
    LL(1516, '"le dos à z = 0"', "piv_dos_note", "le dos à z = 0", "back at z = 0"),
    SS(1539, r'''" — sur la <b>translation du nœud</b> en " + esc(up(pc.node))
        + " (la géométrie ne bouge pas d\'un octet) et <b>cuit dans les "
        + "positions</b> en " + esc(up(pc.baked)) + ", qui n\'ont pas de "
        /* « DANS LES 7 FICHIERS » comptait des FORMATS et les appelait des
           fichiers, sur un écran qui, à côté, en livre trois. Le nombre est
           juste, le nom ne l'était pas — et sur ce panneau un nom qui glisse
           vaut un chiffre faux. */
        + "nœud. <b>Une seule origine</b> dans les "
        + (pc.node.length + pc.baked.length) + " formats, quel que soit le "
        + "fichier qu\'on ouvre."''',
       r'''" — " + dzT("cartes.gltf.pivot_lecture", { node: esc(up(pc.node)), baked: esc(up(pc.baked)), n: (pc.node.length + pc.baked.length) })
        /* « DANS LES 7 FICHIERS » comptait des FORMATS et les appelait des
           fichiers, sur un écran qui, à côté, en livre trois. Le nombre est
           juste, le nom ne l'était pas — et sur ce panneau un nom qui glisse
           vaut un chiffre faux. */''',
       {"pivot_lecture": ("sur la <b>translation du nœud</b> en {node} (la géométrie ne bouge pas d'un octet) et <b>cuit dans les positions</b> en {baked}, qui n'ont pas de nœud. <b>Une seule origine</b> dans les {n} formats, quel que soit le fichier qu'on ouvre.",
                          "on the <b>node translation</b> in {node} (the geometry doesn't move a single byte) and <b>baked into the positions</b> in {baked}, which have no node. <b>One single origin</b> across the {n} formats, whichever file you open.")}),

    # ── portée ──
    LL(1555, '"Carte affichée"', "carte_affichee", "Carte affichée", "Current card"),
    SS(1556, r'''"Jeu entier (" + n + ")"''', r'''dzT("cartes.gltf.jeu_entier", { n: n })''',
       {"jeu_entier": ("Jeu entier ({n})", "Whole deck ({n})")}),
    LL(1557, '"portée"', "lbl_portee", "portée", "scope"),

    # ── fiche de l'atlas ──
    IN(1564, "Aucun atlas encore composé.", "aucun_atlas", "Aucun atlas encore composé.", "No atlas composed yet."),
    LL(1578, '"Définition"', "kv_definition", "Définition", "Resolution", contexte=True),
    LL(1579, '"Poids"', "kv_poids", "Poids", "Size"),
    LL(1580, '"Îlots UV"', "kv_ilots_uv", "Îlots UV", "UV islands"),
    SS(1580, r'''(nIsl == null ? "—" : nIsl + (tri.length
        ? " (" + tri.join("+") + " tri)" : "")) + " mesurés"''',
       r'''dzT("cartes.gltf.n_mesures", { n: (nIsl == null ? "—" : nIsl + (tri.length
        ? " (" + tri.join("+") + " tri)" : "")) })''',
       {"n_mesures": ("{n} mesurés", "{n} measured")}),
    SS(1585, r'''me.atlas_rects + " réservés"''', r'''dzT("cartes.gltf.n_reserves", { n: me.atlas_rects })''',
       {"n_reserves": ("{n} réservés", "{n} reserved")}),
    SS(1587, r'''"moteur de rendu (carte "
        + ((ATLAS.i || 0) + 1) + ")"''',
       r'''dzT("cartes.gltf.source_moteur", { n: ((ATLAS.i || 0) + 1) })''',
       {"source_moteur": ("moteur de rendu (carte {n})", "render engine (card {n})")}),
    LL(1592, '"Coupe"', "kv_coupe", "Coupe", "Trim"),
    LL(1597, '"Information"', "kv_information", "Information", "Information"),
    LL(1609, '"Tranche"', "kv_tranche", "Tranche", "Edge", contexte=True),
    SS(1611, r'''" · " + s.density.edge_perim_mm + " mm de contour"''',
       r'''" · " + dzT("cartes.gltf.mm_contour", { mm: s.density.edge_perim_mm })''',
       {"mm_contour": ("{mm} mm de contour", "{mm} mm outline")}),
    LL(1619, '"Atlas importé : il part tel quel dans les maps et dans le GLB."', "atlas_importe_note",
       "Atlas importé : il part tel quel dans les maps et dans le GLB.",
       "Imported atlas: it goes as-is into the maps and the GLB."),
    SS(1620, r'''"Les îlots reçoivent la carte <b>massicotée</b> (" + g.trim_px.join(" x ")
          + " px pris dans " + g.canvas_px.join(" x ") + ") : le fond perdu de <b>"
          + g.bleed_mm + " mm</b> n'apparaît pas sur la carte 3D, comme sur une "
          + "carte imprimée. Les gouttières reçoivent une dilatation des bords "
          + "d'îlot, pas un aplat — sans quoi les niveaux de mip ramènent un halo "
          + "clair sur le bord de la carte."''',
       r'''dzT("cartes.gltf.note_massicot", { trim: g.trim_px.join(" x "), canvas: g.canvas_px.join(" x "), bleed: g.bleed_mm })''',
       {"note_massicot": ("Les îlots reçoivent la carte <b>massicotée</b> ({trim} px pris dans {canvas}) : le fond perdu de <b>{bleed} mm</b> n'apparaît pas sur la carte 3D, comme sur une carte imprimée. Les gouttières reçoivent une dilatation des bords d'îlot, pas un aplat — sans quoi les niveaux de mip ramènent un halo clair sur le bord de la carte.",
                          "The islands receive the <b>trimmed</b> card ({trim} px taken from {canvas}): the <b>{bleed} mm</b> bleed does not show on the 3D card, just like on a printed card. The gutters get a dilation of the island edges, not a flat fill — otherwise the mip levels bring a light halo onto the card edge.")}),
    SS(1633, r'''HIST.length ? "annuler " + HIST[HIST.length - 1].label : "annuler"''',
       r'''HIST.length ? dzT("cartes.gltf.annuler_label", { label: HIST[HIST.length - 1].label }) : dzT("cartes.gltf.annuler")''',
       {"annuler_label": ("annuler {label}", "undo {label}"), "annuler": ("annuler", "undo")}),

    # ── dérivation PBR ──
    SS(1649, r"""'Dérivation PBR : <b class="' + (n ? "cf-gltf-ok" : "")
      + '">' + n + '</b> réglage(s) repris de la <b>pièce 06</b>'""",
       r"""dzT("cartes.gltf.derive_n", { cls: (n ? "cf-gltf-ok" : ""), n: n })""",
       {"derive_n": ('Dérivation PBR : <b class="{cls}">{n}</b> réglage(s) repris de la <b>pièce 06</b>',
                     'PBR derivation: <b class="{cls}">{n}</b> setting(s) taken from <b>piece 06</b>')}),
    SS(1651, r"""' (' + esc((d.keys || []).join(", ")) + ') — lus dans <code>'
        + esc(d.source) + '</code>' : ' — aucun réglage enregistré, les défauts '
        + 'du service s\'appliquent'""",
       r"""' ' + dzT("cartes.gltf.derive_lus", { cles: esc((d.keys || []).join(", ")), src: esc(d.source) }) : ' — ' + dzT("cartes.gltf.derive_aucun")""",
       {"derive_lus": ("({cles}) — lus dans <code>{src}</code>", "({cles}) — read from <code>{src}</code>"),
        "derive_aucun": ("aucun réglage enregistré, les défauts du service s'appliquent",
                         "no saved setting, the service defaults apply")}),
    SS(1654, r"""'<br><span class="cf-gltf-ko">La pièce 06 a coché ses '
        + 'propres 16 bits : c\'est un réglage HOMONYME et indépendant. Celui '
        + 'qui commande ce ZIP est la case ci-dessous.</span>'""",
       r"""'<br><span class="cf-gltf-ko">' + dzT("cartes.gltf.p6_bits16") + '</span>'""",
       {"p6_bits16": ("La pièce 06 a coché ses propres 16 bits : c'est un réglage HOMONYME et indépendant. Celui qui commande ce ZIP est la case ci-dessous.",
                      "Piece 06 has ticked its own 16-bit option: it is a SAME-NAMED, independent setting. The one that controls this ZIP is the box below.")}),

    # ── raccourcis, dossier ──
    SS(1682, r"""'<span>raccourcis : '
        + '<kbd>E</kbd> construire · <kbd>A</kbd> atlas · <kbd>G</kbd> GLB · '
        + '<kbd>T</kbd> glTF · <kbd>Z</kbd> ZIP · <kbd>1..3</kbd> définition · '
        + '<kbd>Ctrl+Z</kbd> annuler</span>'""",
       r"""'<span>' + dzT("cartes.gltf.raccourcis") + '</span>'""",
       {"raccourcis": ("raccourcis : <kbd>E</kbd> construire · <kbd>A</kbd> atlas · <kbd>G</kbd> GLB · <kbd>T</kbd> glTF · <kbd>Z</kbd> ZIP · <kbd>1..3</kbd> définition · <kbd>Ctrl+Z</kbd> annuler",
                       "shortcuts: <kbd>E</kbd> build · <kbd>A</kbd> atlas · <kbd>G</kbd> GLB · <kbd>T</kbd> glTF · <kbd>Z</kbd> ZIP · <kbd>1..3</kbd> resolution · <kbd>Ctrl+Z</kbd> undo")}),
    SS(1695, r"""'dossier du jeu › <code>' + esc(m.dir) + '</code>' : 'dossier du jeu'""",
       r"""dzT("cartes.gltf.dossier_jeu_dir", { dir: esc(m.dir) }) : dzT("cartes.gltf.dossier_jeu")""",
       {"dossier_jeu_dir": ("dossier du jeu › <code>{dir}</code>", "deck folder › <code>{dir}</code>"),
        "dossier_jeu": ("dossier du jeu", "deck folder")}),
    SS(1699, r"""'« Télécharger » en pose une copie dans le '
        + 'dossier de téléchargements du navigateur ; celui d\'ici ne '
        + 'bouge pas.'""",
       r"""dzT("cartes.gltf.geste")""",
       {"geste": ("« Télécharger » en pose une copie dans le dossier de téléchargements du navigateur ; celui d'ici ne bouge pas.",
                  "“Download” puts a copy in the browser's downloads folder; the one here stays put.")}),
    SS(1703, r"""'<span><b>Où vont les fichiers</b> — ' + dir
          + '. Rien n\'y est encore écrit pour ce jeu. ' + geste + '</span>'""",
       r"""'<span>' + dzT("cartes.gltf.ou_vide", { dir: dir, geste: geste }) + '</span>'""",
       {"ou_vide": ("<b>Où vont les fichiers</b> — {dir}. Rien n'y est encore écrit pour ce jeu. {geste}",
                    "<b>Where files go</b> — {dir}. Nothing has been written there for this deck yet. {geste}")}),
    SS(1713, r"""' — <b class="' + (m.missing ? "cf-gltf-ko" : "cf-gltf-ok") + '">'
            + m.missing + '</b> disparu(s) sur les <b>' + m.listed
            + '</b> du dernier bordereau'""",
       r"""' — ' + dzT("cartes.gltf.disparus", { cls: (m.missing ? "cf-gltf-ko" : "cf-gltf-ok"), n: m.missing, total: m.listed })""",
       {"disparus": ('<b class="{cls}">{n}</b> disparu(s) sur les <b>{total}</b> du dernier bordereau',
                     '<b class="{cls}">{n}</b> missing out of the <b>{total}</b> in the last build report')}),
    SS(1717, r"""'<span><b>Où vont les fichiers</b> — ' + dir + '. '
          + geste + '</span>'
          + '<span><b>' + m.files + ' fichier(s)</b> s\'y sont accumulés ('
          + '<b title="' + esc(weightTitle(m.bytes)) + '">' + weight(m.bytes)
          + '</b>)' + suivi + ', le plus ancien depuis <b>'
          + Number(m.oldest_age_hours || 0).toFixed(2) + ' h</b> : ce qui est '
          + 'écrit là y reste jusqu\'à ce que vous l\'effaciez.</span>'""",
       r"""'<span>' + dzT("cartes.gltf.ou_plein", { dir: dir, geste: geste }) + '</span>'
          + '<span>' + dzT("cartes.gltf.accumules", { n: m.files, titre: esc(weightTitle(m.bytes)), poids: weight(m.bytes), suivi: suivi, h: Number(m.oldest_age_hours || 0).toFixed(2) }) + '</span>'""",
       {"ou_plein": ("<b>Où vont les fichiers</b> — {dir}. {geste}", "<b>Where files go</b> — {dir}. {geste}"),
        "accumules": ('<b>{n} fichier(s)</b> s\'y sont accumulés (<b title="{titre}">{poids}</b>){suivi}, le plus ancien depuis <b>{h} h</b> : ce qui est écrit là y reste jusqu\'à ce que vous l\'effaciez.',
                      '<b>{n} file(s)</b> have piled up there (<b title="{titre}">{poids}</b>){suivi}, the oldest for <b>{h} h</b>: what is written there stays until you delete it.')}),

    # ── bordereau ──
    SS(1752, r"""'<table class="cf-gltf-tab"><thead><tr><th>Fichier</th><th>Contenu</th>'
      + '<th class="num">Poids</th><th></th></tr></thead><tbody>'""",
       r"""'<table class="cf-gltf-tab"><thead><tr><th>' + dzT("cartes.gltf.th_fichier") + '</th><th>' + dzT("cartes.gltf.th_contenu") + '</th>'
      + '<th class="num">' + dzT("cartes.gltf.kv_poids") + '</th><th></th></tr></thead><tbody>'""",
       {"th_fichier": ("Fichier", "File"), "th_contenu": ("Contenu", "Contents"), "kv_poids": ("Poids", "Size")}),
    SS(1760, r"""'">Télécharger</button></td></tr>'""",
       r"""'">' + dzT("cartes.gltf.telecharger") + '</button></td></tr>'""",
       {"telecharger": ("Télécharger", "Download")}),
    SS(1763, r"""BUILD.files.length + ' fichier(s) · construit en '
      + (BUILD.ms / 1000).toFixed(1) + ' s</td>'""",
       r"""dzT("cartes.gltf.pied_bordereau", { n: BUILD.files.length, s: (BUILD.ms / 1000).toFixed(1) }) + '</td>'""",
       {"pied_bordereau": ("{n} fichier(s) · construit en {s} s", "{n} file(s) · built in {s} s")}),
    SS(1783, r"""'<p class="hint">Une seule archive écrite : <code>'
        + esc(arc.kept) + '</code> porte <b>' + arc.count + '</b> entrées '
        + 'relues dans ses octets — <b>' + (arc.png || []).length
        + '</b> PNG, ' + esc((arc.mesh || []).join(" et ")) + ', le manifeste '
        + 'et la notice. <code>' + esc(arc.dropped) + '</code> aurait '
        + 'transporté exactement les mêmes : elle n\'a pas été écrite.</p>'""",
       r"""'<p class="hint">' + dzT("cartes.gltf.archive_unique", { kept: esc(arc.kept), n: arc.count, png: (arc.png || []).length, mesh: esc((arc.mesh || []).join(dzT("cartes.gltf.et_sep"))), dropped: esc(arc.dropped) }) + '</p>'""",
       {"archive_unique": ("Une seule archive écrite : <code>{kept}</code> porte <b>{n}</b> entrées relues dans ses octets — <b>{png}</b> PNG, {mesh}, le manifeste et la notice. <code>{dropped}</code> aurait transporté exactement les mêmes : elle n'a pas été écrite.",
                           "Only one archive written: <code>{kept}</code> holds <b>{n}</b> entries read back from its bytes — <b>{png}</b> PNG, {mesh}, the manifest and the readme. <code>{dropped}</code> would have carried exactly the same: it was not written."),
        "et_sep": (" et ", " and ")}),
    SS(1792, r"""'Redondance mesurée : <b>'
        + p.identiques + '</b> entrée(s) sur ' + p.entrees_a + ' et ' + p.entrees_b
        + ' sont <b>identiques</b> (nom + CRC-32) entre <code>' + esc(p.a)
        + '</code> et <code>' + esc(p.b) + '</code> — ' + weight(p.bytes_decompresses)
        + ' décompressés livrés deux fois.'""",
       r"""dzT("cartes.gltf.redondance", { n: p.identiques, na: p.entrees_a, nb: p.entrees_b, a: esc(p.a), b: esc(p.b), poids: weight(p.bytes_decompresses) })""",
       {"redondance": ("Redondance mesurée : <b>{n}</b> entrée(s) sur {na} et {nb} sont <b>identiques</b> (nom + CRC-32) entre <code>{a}</code> et <code>{b}</code> — {poids} décompressés livrés deux fois.",
                       "Measured redundancy: <b>{n}</b> entry(ies) out of {na} and {nb} are <b>identical</b> (name + CRC-32) between <code>{a}</code> and <code>{b}</code> — {poids} uncompressed delivered twice.")}),
    IN(1805, "Dans le GLB", "dans_glb", "Dans le GLB", "In the GLB"),
    SS(1828, r'''"laissez-le tel quel : la métallicité est déjà cuite dans la "
             + "map, la remultiplier la compterait deux fois"''',
       r'''dzT("cartes.gltf.why_metal")''',
       {"why_metal": ("laissez-le tel quel : la métallicité est déjà cuite dans la map, la remultiplier la compterait deux fois",
                      "leave it as is: metalness is already baked into the map, multiplying again would count it twice")}),
    LL(1831, '"même chose pour la rugosité"', "why_rough", "même chose pour la rugosité", "same for roughness"),
    LL(1834, '"cette finition émet : la texture d\'émission part avec le fichier"', "why_emet",
       "cette finition émet : la texture d'émission part avec le fichier",
       "this finish emits: the emission texture ships with the file"),
    SS(1835, r'''"cette finition n'émet pas — aucune texture d'émission "
                 + "n'est embarquée, elle serait multipliée par zéro"''',
       r'''dzT("cartes.gltf.why_emet_pas")''',
       {"why_emet_pas": ("cette finition n'émet pas — aucune texture d'émission n'est embarquée, elle serait multipliée par zéro",
                         "this finish does not emit — no emission texture is embedded, it would be multiplied by zero")}),
    LL(1837, '"matériaux"', "kv_materiaux", "matériaux", "materials"),
    LL(1838, '"un seul matériau pour toute la carte : un seul appel de rendu"', "why_materiaux",
       "un seul matériau pour toute la carte : un seul appel de rendu",
       "a single material for the whole card: a single draw call"),
    LL(1839, '"branchée"', "ao_branchee", "branchée", "wired"),
    LL(1839, '"absente"', "ao_absente", "absente", "missing"),
    SS(1840, r'''"l'ombre de contact est dans le fichier, "
               + "pas à refaire à l'import"''',
       r'''dzT("cartes.gltf.why_ao_oui")''',
       {"why_ao_oui": ("l'ombre de contact est dans le fichier, pas à refaire à l'import",
                       "contact shadowing is in the file, nothing to redo on import")}),
    SS(1841, r'''"à brancher à la main si "
               + "votre moteur l'attend"''',
       r'''dzT("cartes.gltf.why_ao_non")''',
       {"why_ao_non": ("à brancher à la main si votre moteur l'attend", "wire it by hand if your engine expects it")}),
    LL(1843, '"attributs"', "kv_attributs", "attributs", "attributes"),
    SS(1845, r'''"TANGENT est écrit : votre moteur n'a pas à recalculer "
                 + "les tangentes, la normale rendra pareil partout"''',
       r'''dzT("cartes.gltf.why_tangent")''',
       {"why_tangent": ("TANGENT est écrit : votre moteur n'a pas à recalculer les tangentes, la normale rendra pareil partout",
                        "TANGENT is written: your engine does not have to recompute tangents, the normal map renders the same everywhere")}),
    SS(1847, r'''"sans TANGENT, chaque moteur recalcule les siennes et la "
                 + "normale peut rendre différemment d'un moteur à l'autre"''',
       r'''dzT("cartes.gltf.why_sans_tangent")''',
       {"why_sans_tangent": ("sans TANGENT, chaque moteur recalcule les siennes et la normale peut rendre différemment d'un moteur à l'autre",
                             "without TANGENT, each engine recomputes its own and the normal map may render differently from one engine to another")}),
    LL(1849, '"échantillonnage"', "kv_echant", "échantillonnage", "sampling"),
    SS(1851, r'''"sur un atlas c'est le seul réglage sûr : en REPEAT, le "
                 + "filtrage du bord droit va chercher l'autre face"''',
       r'''dzT("cartes.gltf.why_clamp")''',
       {"why_clamp": ("sur un atlas c'est le seul réglage sûr : en REPEAT, le filtrage du bord droit va chercher l'autre face",
                      "on an atlas this is the only safe setting: with REPEAT, filtering at the right edge samples the other face")}),
    SS(1853, r'''"sur un atlas, le filtrage du bord droit ira chercher "
                 + "l'autre face de la carte"''',
       r'''dzT("cartes.gltf.why_repeat")''',
       {"why_repeat": ("sur un atlas, le filtrage du bord droit ira chercher l'autre face de la carte",
                       "on an atlas, filtering at the right edge will sample the other face of the card")}),
    SS(1855, r'''me.triangles + " / " + me.vertices + " sommets"''',
       r'''dzT("cartes.gltf.tri_sommets", { t: me.triangles, v: me.vertices })''',
       {"tri_sommets": ("{t} / {v} sommets", "{t} / {v} vertices")}),
    LL(1856, '"coins arrondis compris"', "coins_compris", "coins arrondis compris", "rounded corners included"),
    LL(1857, '"solide"', "kv_solide", "solide", "solid"),
    SS(1857, r'''"fermé — " + me.edges + " arêtes, 0 libre"''', r'''dzT("cartes.gltf.ferme", { n: me.edges })''',
       {"ferme": ("fermé — {n} arêtes, 0 libre", "closed — {n} edges, 0 free")}),
    SS(1858, r'''me.free_edges + " arêtes libres"''', r'''dzT("cartes.gltf.aretes_libres", { n: me.free_edges })''',
       {"aretes_libres": ("{n} arêtes libres", "{n} free edges")}),
    LL(1859, '"aucun trou : le maillage se remplit"', "why_ferme", "aucun trou : le maillage se remplit",
       "no holes: the mesh can be filled"),
    LL(1860, '"un maillage ouvert ne se remplit pas"', "why_ouvert", "un maillage ouvert ne se remplit pas",
       "an open mesh cannot be filled"),
    LL(1872, '"solide à trancher"', "kv_trancher", "solide à trancher", "solid for slicing"),
    SS(1873, r'''"oui — volume " + (me.volume_mm3 != null ? me.volume_mm3 : "?")
               + " mm³ (pavé plein " + (me.volume_box_mm3 != null ? me.volume_box_mm3 : "?")
               + " mm³)"''',
       r'''dzT("cartes.gltf.oui_volume", { v: (me.volume_mm3 != null ? me.volume_mm3 : "?"), box: (me.volume_box_mm3 != null ? me.volume_box_mm3 : "?") })''',
       {"oui_volume": ("oui — volume {v} mm³ (pavé plein {box} mm³)", "yes — volume {v} mm³ (solid block {box} mm³)")}),
    LL(1876, '"non — normales retournées (volume signé négatif)"', "non_normales",
       "non — normales retournées (volume signé négatif)", "no — flipped normals (negative signed volume)"),
    SS(1877, r'''"non — " + me.free_edges + " arêtes libres"''', r'''dzT("cartes.gltf.non_aretes", { n: me.free_edges })''',
       {"non_aretes": ("non — {n} arêtes libres", "no — {n} free edges")}),
    SS(1880, r'''"dans ce lot : " + trancheurs.map((f) => f.name).join(", ")''',
       r'''dzT("cartes.gltf.dans_lot", { noms: trancheurs.map((f) => f.name).join(", ") })''',
       {"dans_lot": ("dans ce lot : {noms}", "in this batch: {noms}")}),
    LL(1881, '"aucun fichier de ce lot ne se donne à un trancheur"', "aucun_trancheur",
       "aucun fichier de ce lot ne se donne à un trancheur", "no file in this batch can go straight to a slicer"),
    LL(1885, '"bornes d\'accesseur"', "kv_bornes", "bornes d'accesseur", "accessor bounds"),
    LL(1886, '"exactes — "', "bornes_exactes", "exactes — ", "exact — "),
    LL(1886, '"arrondies — "', "bornes_arrondies", "arrondies — ", "rounded — "),
    LL(1888, '" accesseur(s) relus dans le buffer"', "accesseurs_relus", " accesseur(s) relus dans le buffer",
       " accessor(s) read back from the buffer"),
    SS(1890, r'''"arrondies, le validateur glTF de référence refuse le fichier "
             + "(ACCESSOR_MIN_MISMATCH)"''',
       r'''dzT("cartes.gltf.why_bornes")''',
       {"why_bornes": ("arrondies, le validateur glTF de référence refuse le fichier (ACCESSOR_MIN_MISMATCH)",
                       "if rounded, the reference glTF validator rejects the file (ACCESSOR_MIN_MISMATCH)")}),
    SS(1894, r'''"un solide fermé se rend en simple face : la face "
               + "arrière n'est jamais vue, la dessiner double le coût"''',
       r'''dzT("cartes.gltf.why_simple_face")''',
       {"why_simple_face": ("un solide fermé se rend en simple face : la face arrière n'est jamais vue, la dessiner double le coût",
                            "a closed solid renders single-sided: the back face is never seen, drawing it doubles the cost")}),
    LL(1896, '"surface ouverte : la double face évite les trous noirs"', "why_double_face",
       "surface ouverte : la double face évite les trous noirs", "open surface: double-sided avoids black holes"),
    LL(1897, '"aucune"', "aucune", "aucune", "none"),
    SS(1898, r'''"un moteur qui ne les connaît pas rend la carte sans elles, "
             + "jamais en erreur : c'est la règle des extensions glTF"''',
       r'''dzT("cartes.gltf.why_extensions")''',
       {"why_extensions": ("un moteur qui ne les connaît pas rend la carte sans elles, jamais en erreur : c'est la règle des extensions glTF",
                           "an engine that doesn't know them renders the card without them, never with an error: that is the glTF extension rule")}),
    LL(1908, '"boîte englobante"', "kv_boite", "boîte englobante", "bounding box"),
    LL(1911, '"non relue dans le buffer"', "boite_non_relue", "non relue dans le buffer", "not read back from the buffer"),
    SS(1913, r'''"relue dans les float32 de POSITION du chunk binaire, à "
             + "l'échelle du nœud"''',
       r'''dzT("cartes.gltf.why_boite")''',
       {"why_boite": ("relue dans les float32 de POSITION du chunk binaire, à l'échelle du nœud",
                      "read back from the POSITION float32 values of the binary chunk, at node scale")}),
    SS(1921, r"""'<p class="hint">Les deux formats qu\'un trancheur ouvre '
          + 'directement ne sont pas dans ce lot. '
          + '<button class="btn sm" data-act="slice">ajouter STL et 3MF</button></p>'""",
       r"""'<p class="hint">' + dzT("cartes.gltf.pas_trancheur") + ' '
          + '<button class="btn sm" data-act="slice">' + dzT("cartes.gltf.ajouter_stl") + '</button></p>'""",
       {"pas_trancheur": ("Les deux formats qu'un trancheur ouvre directement ne sont pas dans ce lot.",
                          "The two formats a slicer opens directly are not in this batch."),
        "ajouter_stl": ("ajouter STL et 3MF", "add STL and 3MF")}),

    # ── maps livrées ──
    SS(1972, r"""' — ' + esc(cst.join(", ")) + ' : 1 seul niveau, '
        + 'constante' + pl(cst.length, "s")""",
       r"""' — ' + dzT(cst.length > 1 ? "cartes.gltf.constantes" : "cartes.gltf.constante", { noms: esc(cst.join(", ")) })""",
       {"constante": ("{noms} : 1 seul niveau, constante", "{noms}: a single level, constant"),
        "constantes": ("{noms} : 1 seul niveau, constantes", "{noms}: a single level each, constant")}),
    SS(1978, r"""' — ' + esc(faibles.join(", ")) + ' varie'
        + pl(faibles.length, "nt") + ' trop peu pour se voir, sans être '
        + 'constante' + pl(faibles.length, "s")""",
       r"""' — ' + dzT(faibles.length > 1 ? "cartes.gltf.faibles_plusieurs" : "cartes.gltf.faibles_un", { noms: esc(faibles.join(", ")) })""",
       {"faibles_un": ("{noms} varie trop peu pour se voir, sans être constante",
                       "{noms} varies too little to show, without being constant"),
        "faibles_plusieurs": ("{noms} varient trop peu pour se voir, sans être constantes",
                              "{noms} vary too little to show, without being constant")}),
    SS(1985, r"""'<div class="cf-gltf-detail"><h4>Les ' + names.length
        + ' maps PNG livrées <i>dans '
        + esc(porteurs.map((f) => f.name).join(" et ")) + ' — '
        + (names.length - cst.length - faibles.length)
        + ' portent une variation mesurable' + lg
        + '</i></h4><div class="cf-gltf-maps">'""",
       r"""'<div class="cf-gltf-detail"><h4>' + dzT("cartes.gltf.maps_livrees", { n: names.length, dans: esc(porteurs.map((f) => f.name).join(dzT("cartes.gltf.et_sep"))), nv: (names.length - cst.length - faibles.length), lg: lg })
        + '</h4><div class="cf-gltf-maps">'""",
       {"maps_livrees": ("Les {n} maps PNG livrées <i>dans {dans} — {nv} portent une variation mesurable{lg}</i>",
                         "The {n} delivered PNG maps <i>in {dans} — {nv} carry measurable variation{lg}</i>"),
        "et_sep": (" et ", " and ")}),
    SS(2011, r'''"moyenne relue sur les "
                 + (d.mean_measured_on || "") + " : " + det + " — tous canaux "
                 + moy.toFixed(4) + ". "''',
       r'''dzT("cartes.gltf.moy_titre", { sur: (d.mean_measured_on || ""), det: det, moy: moy.toFixed(4) }) + " "''',
       {"moy_titre": ("moyenne relue sur les {sur} : {det} — tous canaux {moy}.",
                      "mean read back over the {sur}: {det} — all channels {moy}.")}),
    SS(2018, r'''"Le service de dérivation, lui, mesure : "
                 + m.channel + ". "''',
       r'''dzT("cartes.gltf.service_mesure", { canal: m.channel }) + " "''',
       {"service_mesure": ("Le service de dérivation, lui, mesure : {canal}.",
                           "The derivation service measures: {canal}.")}),
    SS(2021, r"""'</b><i>moy '""", r"""'</b><i>' + dzT("cartes.gltf.moy_abbr") + ' '""",
       {"moy_abbr": ("moy", "avg")}),
    SS(2023, r"""' niv.'""", r"""' ' + dzT("cartes.gltf.niv_abbr")""", {"niv_abbr": ("niv.", "lv.")}),
    SS(2037, r"""'<p class="hint">Branchement relu dans <code>'
          + esc(w.material || "") + '</code> : '""",
       r"""'<p class="hint">' + dzT("cartes.gltf.branchement", { mat: esc(w.material || "") })""",
       {"branchement": ("Branchement relu dans <code>{mat}</code> : ", "Wiring read back from <code>{mat}</code>: ")}),
    LL(2041, '"aucune map pointée"', "aucune_map", "aucune map pointée", "no map referenced"),
    SS(2045, r"""'<p class="hint cf-gltf-warn"><b>' + esc(orph.join(", "))
            + '</b> : aucun matériau de cette archive ne les pointe — elles '
            + 'partent comme images sources'""",
       r"""'<p class="hint cf-gltf-warn">' + dzT("cartes.gltf.orphelines", { noms: esc(orph.join(", ")) })""",
       {"orphelines": ("<b>{noms}</b> : aucun matériau de cette archive ne les pointe — elles partent comme images sources",
                       "<b>{noms}</b>: no material in this archive references them — they ship as source images")}),
    SS(2048, r"""' (<b>' + esc(glb.join(", ")) + '</b> '
              + (glb.length > 1 ? 'sont branchées' : 'est branchée')
              + ' dans le GLB)'""",
       r"""' (' + dzT(glb.length > 1 ? "cartes.gltf.branchees_glb" : "cartes.gltf.branchee_glb", { noms: esc(glb.join(", ")) }) + ')'""",
       {"branchee_glb": ("<b>{noms}</b> est branchée dans le GLB", "<b>{noms}</b> is wired in the GLB"),
        "branchees_glb": ("<b>{noms}</b> sont branchées dans le GLB", "<b>{noms}</b> are wired in the GLB")}),
    SS(2053, r"""'<p class="hint"><b>moy</b> — moyenne des échantillons du PNG '
        + 'écrit, <b>tous canaux</b>, ramenée en 0..1 par la pleine échelle du '
        + 'conteneur : c\'est le nombre que n\'importe quel décodeur refait sur '
        + 'ces octets. Le détail par canal est dans l\'infobulle, avec le canal '
        + 'que le service de dérivation regarde pour décider si la map porte '
        + 'quelque chose — ce n\'est pas le même calcul, et les deux sont '
        + 'nommés. Profondeur et niveaux sortent des mêmes octets. Une map à '
        + '<b>un seul niveau</b> est dite constante.</p>'""",
       r"""'<p class="hint">' + dzT("cartes.gltf.legende_moy") + '</p>'""",
       {"legende_moy": ("<b>moy</b> — moyenne des échantillons du PNG écrit, <b>tous canaux</b>, ramenée en 0..1 par la pleine échelle du conteneur : c'est le nombre que n'importe quel décodeur refait sur ces octets. Le détail par canal est dans l'infobulle, avec le canal que le service de dérivation regarde pour décider si la map porte quelque chose — ce n'est pas le même calcul, et les deux sont nommés. Profondeur et niveaux sortent des mêmes octets. Une map à <b>un seul niveau</b> est dite constante.",
                        "<b>avg</b> — mean of the written PNG samples, <b>all channels</b>, scaled to 0..1 by the container's full range: it is the number any decoder recomputes from these bytes. The per-channel detail is in the tooltip, along with the channel the derivation service checks to decide whether the map carries anything — it is not the same calculation, and both are named. Bit depth and levels come from the same bytes. A map with <b>a single level</b> is called constant.")}),
    SS(2071, r"""'<p class="hint">Chunk <b>pHYs</b> relu dans les <b>' + phys.png
            + '</b> PNG écrits : <b>' + phys.dpi.join(" x ") + ' DPI</b>'""",
       r"""'<p class="hint">' + dzT("cartes.gltf.phys_relu", { n: phys.png, dpi: phys.dpi.join(" x ") })""",
       {"phys_relu": ("Chunk <b>pHYs</b> relu dans les <b>{n}</b> PNG écrits : <b>{dpi} DPI</b>",
                      "<b>pHYs</b> chunk read back from the <b>{n}</b> written PNGs: <b>{dpi} DPI</b>")}),
    SS(2073, r"""' <b class="cf-gltf-ko">(les PNG ne portent '
              + 'pas tous la même densité)</b>'""",
       r"""' <b class="cf-gltf-ko">(' + dzT("cartes.gltf.phys_divers") + ')</b>'""",
       {"phys_divers": ("les PNG ne portent pas tous la même densité", "the PNGs do not all carry the same density")}),
    SS(2076, r"""' · chunk <b>sRGB</b> sur ' + esc(phys.srgb.join(", "))""",
       r"""' · ' + dzT("cartes.gltf.srgb_sur", { noms: esc(phys.srgb.join(", ")) })""",
       {"srgb_sur": ("chunk <b>sRGB</b> sur {noms}", "<b>sRGB</b> chunk on {noms}")}),
    SS(2078, r"""' · <b>linéaire</b> (gAMA 1.0) sur '
                + esc(phys.lineaire.join(", "))""",
       r"""' · ' + dzT("cartes.gltf.lineaire_sur", { noms: esc(phys.lineaire.join(", ")) })""",
       {"lineaire_sur": ("<b>linéaire</b> (gAMA 1.0) sur {noms}", "<b>linear</b> (gAMA 1.0) on {noms}")}),
    SS(2088, r"""'<p class="hint cf-gltf-warn">Un <b>pHYs</b> pour <b>trois îlots</b> : '
            + 'ce chiffre est celui du <b>recto</b>. L\'îlot de tranche sort à <b>'
            + row.atlas.density.edge_dpi.join(" x ") + ' DPI</b> (rapport '
            + row.atlas.density.edge_ratio + ':1) sur un contour de <b>'
            + row.atlas.density.edge_perim_mm + ' mm</b> <i>mesuré sur le '
            + esc(String(row.atlas.density.edge_perim_source || "")) + '</i>, '
            + 'coins arrondis compris — un outil d\'impression qui '
            + 'prend le pHYs au pied de la lettre se trompe sur cette zone. '
            + 'La réserve voyage dans un chunk <code>tEXt</code> de chaque PNG.</p>'""",
       r"""'<p class="hint cf-gltf-warn">' + dzT("cartes.gltf.phys_reserve", { dpi: row.atlas.density.edge_dpi.join(" x "), ratio: row.atlas.density.edge_ratio, mm: row.atlas.density.edge_perim_mm, src: esc(String(row.atlas.density.edge_perim_source || "")) }) + '</p>'""",
       {"phys_reserve": ("Un <b>pHYs</b> pour <b>trois îlots</b> : ce chiffre est celui du <b>recto</b>. L'îlot de tranche sort à <b>{dpi} DPI</b> (rapport {ratio}:1) sur un contour de <b>{mm} mm</b> <i>mesuré sur le {src}</i>, coins arrondis compris — un outil d'impression qui prend le pHYs au pied de la lettre se trompe sur cette zone. La réserve voyage dans un chunk <code>tEXt</code> de chaque PNG.",
                         "One <b>pHYs</b> for <b>three islands</b>: this figure is the <b>front</b>'s. The edge island comes out at <b>{dpi} DPI</b> (ratio {ratio}:1) over a <b>{mm} mm</b> outline <i>measured on the {src}</i>, rounded corners included — a print tool that takes pHYs at face value gets this area wrong. The caveat travels in a <code>tEXt</code> chunk of each PNG.")}),
    SS(2108, r"""'<p class="hint cf-gltf-warn"><b>' + dens.useful_pct + ' %</b> des '
            + 'texels de l\'îlot recto portent de l\'information : <b>'
            + dens.wasted_px + '</b> texels n\'en portent aucune. '
            + '<button class="btn sm" data-act="fit">ramener l\'atlas à '
            + dens.res_fit + ' px</button> '""",
       r"""'<p class="hint cf-gltf-warn">' + dzT("cartes.gltf.gaspillage", { pct: dens.useful_pct, n: dens.wasted_px }) + ' '
            + '<button class="btn sm" data-act="fit">' + dzT("cartes.gltf.ramener", { fit: dens.res_fit }) + '</button> '""",
       {"gaspillage": ("<b>{pct} %</b> des texels de l'îlot recto portent de l'information : <b>{n}</b> texels n'en portent aucune.",
                       "<b>{pct}%</b> of the front island's texels carry detail: <b>{n}</b> texels carry none."),
        "ramener": ("ramener l'atlas à {fit} px", "bring the atlas down to {fit} px")}),

    # ── visionneuse vide ──
    SS(2132, r"""'<p class="empty-note sm">La visionneuse ouvrira le '
      + '<b>.glb</b> une fois construit et mesurera sa boîte englobante. Le '
      + 'nombre s\'affichera ici, relu dans le fichier livré.</p>'""",
       r"""'<p class="empty-note sm">' + dzT("cartes.gltf.visionneuse_attente") + '</p>'""",
       {"visionneuse_attente": ("La visionneuse ouvrira le <b>.glb</b> une fois construit et mesurera sa boîte englobante. Le nombre s'affichera ici, relu dans le fichier livré.",
                                "The viewer will open the <b>.glb</b> once built and measure its bounding box. The number will show here, read back from the delivered file.")}),
    SS(2145, r"""'<span>1 unité glTF = 1 mètre : le nœud porte l\'échelle '
        + 'physique, sinon un viewer annoncerait une carte de '
        + sansEchelle.slice(0, 2).map((v) => v.toFixed(2).replace(".", ","))
          .join(" x ") + ' m.</span>'""",
       r"""'<span>' + dzT("cartes.gltf.echelle_noeud", { dim: sansEchelle.slice(0, 2).map((v) => v.toFixed(2).replace(".", ","))
          .join(" x ") }) + '</span>'""",
       {"echelle_noeud": ("1 unité glTF = 1 mètre : le nœud porte l'échelle physique, sinon un viewer annoncerait une carte de {dim} m.",
                          "1 glTF unit = 1 meter: the node carries the physical scale, otherwise a viewer would report a {dim} m card.")}),

    # ── état vide ──
    SS(2185, r'''"un <b>.glb</b> — géométrie, "
      + "matériau, textures"''',
       r'''dzT("cartes.gltf.vide_glb")''',
       {"vide_glb": ("un <b>.glb</b> — géométrie, matériau, textures", "a <b>.glb</b> — geometry, material, textures")}),
    SS(2187, r'''" (émission à zéro : aucune texture émissive, elle serait "
          + "multipliée par zéro — voir le réglage Émission)"''',
       r'''" (" + dzT("cartes.gltf.vide_glb_emi") + ")"''',
       {"vide_glb_emi": ("émission à zéro : aucune texture émissive, elle serait multipliée par zéro — voir le réglage Émission",
                         "emission at zero: no emissive texture, it would be multiplied by zero — see the Emission setting")}),
    LL(2189, '"un <b>.gltf</b> autonome — buffer en data URI, aucun <i>.bin</i> à côté"', "vide_gltf",
       "un <b>.gltf</b> autonome — buffer en data URI, aucun <i>.bin</i> à côté",
       "a standalone <b>.gltf</b> — buffer as a data URI, no <i>.bin</i> alongside"),
    SS(2196, r'''"un <b>.zip</b> — les maps PNG (une "
      + "par canal dérivé, l\'émission seulement si elle est non nulle — "
      + "finition ou réglage), le manifeste, le maillage OBJ et son MTL"''',
       r'''dzT("cartes.gltf.vide_zip")''',
       {"vide_zip": ("un <b>.zip</b> — les maps PNG (une par canal dérivé, l'émission seulement si elle est non nulle — finition ou réglage), le manifeste, le maillage OBJ et son MTL",
                     "a <b>.zip</b> — the PNG maps (one per derived channel, emission only if non-zero — finish or setting), the manifest, the OBJ mesh and its MTL")}),
    LL(2200, '"un <b>OBJ + MTL</b> en millimètres, avec ses maps"', "vide_obj",
       "un <b>OBJ + MTL</b> en millimètres, avec ses maps", "an <b>OBJ + MTL</b> in millimeters, with its maps"),
    LL(2201, '"un <b>.stl</b> binaire en millimètres"', "vide_stl", "un <b>.stl</b> binaire en millimètres",
       "a binary <b>.stl</b> in millimeters"),
    SS(2202, r'''"un <b>.3mf</b> — norme ouverte d\'impression 3D, en millimètres, <b>avec la couleur</b>"''',
       r'''dzT("cartes.gltf.vide_3mf")''',
       {"vide_3mf": ("un <b>.3mf</b> — norme ouverte d'impression 3D, en millimètres, <b>avec la couleur</b>",
                     "a <b>.3mf</b> — open 3D printing standard, in millimeters, <b>with color</b>")}),
    SS(2203, r'''"plus un ZIP du <b>jeu entier</b> (" + n + " cartes)"''', r'''dzT("cartes.gltf.vide_deck", { n: n })''',
       {"vide_deck": ("plus un ZIP du <b>jeu entier</b> ({n} cartes)", "plus a ZIP of the <b>whole deck</b> ({n} cards)")}),
    SS(2205, r"""'<p>Rien n\'est encore construit. En <b>' + get("res") + ' px</b>, '
      + 'la construction produira :</p><ul><li>'""",
       r"""'<p>' + dzT("cartes.gltf.vide_intro", { res: get("res") }) + '</p><ul><li>'""",
       {"vide_intro": ("Rien n'est encore construit. En <b>{res} px</b>, la construction produira :",
                       "Nothing built yet. At <b>{res} px</b>, the build will produce:")}),
    IN(2207, "Construire maintenant", "construire_maintenant", "Construire maintenant", "Build now"),
    IN(2208, r"Les poids s\'afficheront ici, fichier par fichier.", "poids_ici",
       "Les poids s'afficheront ici, fichier par fichier.", "Sizes will show here, file by file."),
]
