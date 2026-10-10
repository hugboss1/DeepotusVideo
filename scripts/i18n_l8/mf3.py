"""t148 — mf3 : Material Forge, materialforge.js 2701-4063 — fin de l'inspecteur (réinitialiser, re-dériver, vignette,
préréglages), bloc Export (rôles des maps, ordre des canaux, bordereau, notes de format / profondeur / définition,
règle du « ≈ »), puces maillage / environnement, « Mon modèle » de l'Établi, panneau Photo, comparaison, onglet
Générateurs, câblage (toasts d'import d'ambiance, aide de l'inspecteur).

GARDÉ : types MIME, nom de fichier par défaut envoyé au serveur (reference.png), classes CSS (« est »,
« est-size »), nom des matières fabriquées par le harnais de charge __stress (QA, jamais montré à l'utilisateur
final). Les messages d'erreur du serveur (e.message) passent en variable {msg} ; les labels de préréglages,
d'ambiances et de générateurs viennent du serveur et ne sont pas traduits ici. Les unités d'octets (o / ko / Mo)
se traduisent (B / KB / MB) : en anglais « Mo » ne veut rien dire.
"""
from outils import L, S, X, H

F = "materialforge/materialforge.js"
PLAGES = {F: (2701, 4063)}

ENTREES = [
    # ── inspecteur : réinitialiser, re-dériver, vignette ──────────────────────────────────────────────────────
    L(F, 2704, '"Propriétés réinitialisées."', "matiere.mf3_insp.reinit_ok", "Propriétés réinitialisées.",
      "Properties reset."),
    S(F, 2705, 'toast("Réinitialisation impossible : " + e.message, true)',
      'toast(dzT("matiere.mf3_insp.reinit_err", { msg: e.message }), true)',
      {"matiere.mf3_insp.reinit_err": ("Réinitialisation impossible : {msg}", "Couldn't reset: {msg}")}),
    S(F, 2713, 'ico("dz-lab3d-deriver-maps") + " Dérivation…"',
      'ico("dz-lab3d-deriver-maps") + " " + dzT("matiere.mf3_insp.derivation")',
      {"matiere.mf3_insp.derivation": ("Dérivation…", "Deriving…")}),
    S(F, 2729, 'toast(((nm.maps || []).length || "les") + " maps re-dérivées localement — 0 crédit.")',
      'toast((nm.maps || []).length ? dzT("matiere.mf3_insp.derive_ok_n", { n: (nm.maps || []).length })'
      ' : dzT("matiere.mf3_insp.derive_ok"))',
      {"matiere.mf3_insp.derive_ok_n": ("{n} maps re-dérivées localement — 0 crédit.",
                                        "{n} maps re-derived locally — 0 credits."),
       "matiere.mf3_insp.derive_ok": ("les maps re-dérivées localement — 0 crédit.",
                                      "Maps re-derived locally — 0 credits.")}),
    S(F, 2730, 'toast("Dérivation impossible : " + e.message, true)',
      'toast(dzT("matiere.mf3_insp.derive_err", { msg: e.message }), true)',
      {"matiere.mf3_insp.derive_err": ("Dérivation impossible : {msg}", "Couldn't derive maps: {msg}")}),
    S(F, 2731, 'ico("dz-lab3d-deriver-maps") + " Re-dériver les maps"',
      'ico("dz-lab3d-deriver-maps") + " " + dzT("matiere.mf3_insp.rederiver")',
      {"matiere.mf3_insp.rederiver": ("Re-dériver les maps", "Re-derive maps")}),
    L(F, 2738, '"Visionneuse indisponible."', "matiere.mf3_insp.visionneuse_absente", "Visionneuse indisponible.",
      "Viewer unavailable."),
    X(F, 2740, '"image/png"', "type MIME"),
    X(F, 2742, '"image/png"', "type MIME (en-tête Content-Type)"),
    L(F, 2746, '"Vignette de la carte mise à jour depuis le rendu 3D."', "matiere.mf3_insp.vignette_ok",
      "Vignette de la carte mise à jour depuis le rendu 3D.", "Card thumbnail updated from the 3D render."),
    S(F, 2747, 'toast("Vignette de la carte impossible : " + e.message, true)',
      'toast(dzT("matiere.mf3_insp.vignette_err", { msg: e.message }), true)',
      {"matiere.mf3_insp.vignette_err": ("Vignette de la carte impossible : {msg}",
                                         "Couldn't update the card thumbnail: {msg}")}),

    # ── préréglages ──────────────────────────────────────────────────────────────────────────────────────────
    S(F, 2806, 'toast("Préréglage posé : " + (p.label || p.id))',
      'toast(dzT("matiere.mf3_preset.pose", { nom: p.label || p.id }))',
      {"matiere.mf3_preset.pose": ("Préréglage posé : {nom}", "Preset applied: {nom}")}),
    S(F, 2807, 'toast("Préréglage impossible : " + e.message, true)',
      'toast(dzT("matiere.mf3_preset.err", { msg: e.message }), true)',
      {"matiere.mf3_preset.err": ("Préréglage impossible : {msg}", "Couldn't apply the preset: {msg}")}),

    # ── rôle de chaque map (bordereau) ───────────────────────────────────────────────────────────────────────
    L(F, 2841, '"Couleur diffuse, sRGB"', "matiere.mf3_role.basecolor", "Couleur diffuse, sRGB",
      "Diffuse color, sRGB"),
    L(F, 2842, '"Relief tangent-space, OpenGL +Y"', "matiere.mf3_role.normal", "Relief tangent-space, OpenGL +Y",
      "Tangent-space normal, OpenGL +Y"),
    L(F, 2843, '"Rugosité · 0 miroir, 1 mat"', "matiere.mf3_role.roughness", "Rugosité · 0 miroir, 1 mat",
      "Roughness · 0 mirror, 1 matte"),
    L(F, 2844, '"Métallicité · 0 diélectrique, 1 métal"', "matiere.mf3_role.metallic",
      "Métallicité · 0 diélectrique, 1 métal", "Metalness · 0 dielectric, 1 metal"),
    L(F, 2845, '"Occlusion ambiante, assombrit les creux"', "matiere.mf3_role.ao",
      "Occlusion ambiante, assombrit les creux", "Ambient occlusion, darkens crevices"),
    L(F, 2846, '"Déplacement / parallaxe"', "matiere.mf3_role.height", "Déplacement / parallaxe",
      "Displacement / parallax"),
    L(F, 2847, '"Zones qui émettent de la lumière"', "matiere.mf3_role.emissive", "Zones qui émettent de la lumière",
      "Areas that emit light"),
    L(F, 2848, '"Packée pour glTF / Unreal"', "matiere.mf3_role.orm", "Packée pour glTF / Unreal",
      "Packed for glTF / Unreal"),
    L(F, 2849, '"Packée pour le Lit URP / HDRP d\'Unity"', "matiere.mf3_role.maskmap",
      "Packée pour le Lit URP / HDRP d'Unity", "Packed for Unity's URP / HDRP Lit"),
    L(F, 2850, '"Lissage · inverse de la rugosité"', "matiere.mf3_role.smoothness", "Lissage · inverse de la rugosité",
      "Smoothness · inverse of roughness"),
    L(F, 2851, '"Opacité · 0 transparent, 1 opaque"', "matiere.mf3_role.opacity", "Opacité · 0 transparent, 1 opaque",
      "Opacity · 0 transparent, 1 opaque"),
    L(F, 2852, '"Déplacement géométrique"', "matiere.mf3_role.displacement", "Déplacement géométrique",
      "Geometric displacement"),

    # ── ordre des canaux (V = vert en français, G = green en anglais) ────────────────────────────────────────
    L(F, 2855, '"R V B = couleur"', "matiere.mf3_canaux.basecolor", "R V B = couleur", "R G B = color"),
    L(F, 2856, '"R = pente X · V = pente Y · B = Z"', "matiere.mf3_canaux.normal", "R = pente X · V = pente Y · B = Z",
      "R = X slope · G = Y slope · B = Z"),
    L(F, 2857, '"L = rugosité"', "matiere.mf3_canaux.roughness", "L = rugosité", "L = roughness"),
    L(F, 2858, '"L = métallicité"', "matiere.mf3_canaux.metallic", "L = métallicité", "L = metalness"),
    X(F, 2859, '"L = occlusion"', "identique en anglais (L = occlusion)"),
    L(F, 2860, '"L = hauteur"', "matiere.mf3_canaux.height", "L = hauteur", "L = height"),
    L(F, 2861, '"R V B = lumière émise"', "matiere.mf3_canaux.emissive", "R V B = lumière émise",
      "R G B = emitted light"),
    L(F, 2862, '"R = occlusion · V = rugosité · B = métal"', "matiere.mf3_canaux.orm",
      "R = occlusion · V = rugosité · B = métal", "R = occlusion · G = roughness · B = metal"),
    L(F, 2863, '"R = métal · V = occlusion · B = détail · A = lissage"', "matiere.mf3_canaux.maskmap",
      "R = métal · V = occlusion · B = détail · A = lissage", "R = metal · G = occlusion · B = detail · A = smoothness"),
    L(F, 2864, '"L = lissage"', "matiere.mf3_canaux.smoothness", "L = lissage", "L = smoothness"),
    L(F, 2865, '"L = opacité"', "matiere.mf3_canaux.opacity", "L = opacité", "L = opacity"),
    L(F, 2866, '"L = déplacement"', "matiere.mf3_canaux.displacement", "L = déplacement", "L = displacement"),

    # ── fichiers annexes de l'archive ────────────────────────────────────────────────────────────────────────
    L(F, 2869, '"Toutes les valeurs PBR, relisibles par un script"', "matiere.mf3_extra.material_json",
      "Toutes les valeurs PBR, relisibles par un script", "All PBR values, readable by a script"),
    L(F, 2870, '"Score de raccord, contenu de l\'ORM, convention utilisée"', "matiere.mf3_extra.lisezmoi",
      "Score de raccord, contenu de l'ORM, convention utilisée", "Seam score, ORM contents, naming convention used"),
    L(F, 2871, '"Vignette de la carte, capturée dans le rendu 3D"', "matiere.mf3_extra.thumb",
      "Vignette de la carte, capturée dans le rendu 3D", "Card thumbnail, captured from the 3D render"),
    S(F, 2901, '"Fichier de données packé sur " + ch.length + " canaux, livré dans l\'archive"',
      'dzT("matiere.mf3_mani.donnees_n", { n: ch.length })',
      {"matiere.mf3_mani.donnees_n": ("Fichier de données packé sur {n} canaux, livré dans l'archive",
                                      "Data file packed on {n} channels, shipped in the archive")}),
    L(F, 2902, '"Fichier de données à un canal, livré dans l\'archive"', "matiere.mf3_mani.donnees_1",
      "Fichier de données à un canal, livré dans l'archive", "Single-channel data file, shipped in the archive"),
    L(F, 2918, '"canaux non déclarés par le backend"', "matiere.mf3_canaux.non_declares",
      "canaux non déclarés par le backend", "channels not declared by the backend"),
    L(F, 2919, '"L = niveau de gris"', "matiere.mf3_canaux.gris", "L = niveau de gris", "L = grayscale"),
    S(F, 2920, 'ch.split("").join(" ") + " — rôle des canaux non déclaré"',
      'dzT("matiere.mf3_canaux.role_non_declare", { canaux: ch.split("").join(" ") })',
      {"matiere.mf3_canaux.role_non_declare": ("{canaux} — rôle des canaux non déclaré",
                                               "{canaux} — channel roles not declared")}),
    L(F, 2926, '"Géométrie du maillage exporté, textures comprises"', "matiere.mf3_extra.glb",
      "Géométrie du maillage exporté, textures comprises", "Exported mesh geometry, textures included"),
    L(F, 2927, '"Note jointe à l\'archive"', "matiere.mf3_extra.note", "Note jointe à l'archive",
      "Note included in the archive"),
    L(F, 2928, '"Données de la matière, relisibles par un script"', "matiere.mf3_extra.json",
      "Données de la matière, relisibles par un script", "Material data, readable by a script"),
    L(F, 2929, '"Image jointe à l\'archive"', "matiere.mf3_extra.image", "Image jointe à l'archive",
      "Image included in the archive"),
    L(F, 2930, '"Fichier joint à l\'archive"', "matiere.mf3_extra.fichier", "Fichier joint à l'archive",
      "File included in the archive"),

    # ── notes de format et de profondeur ─────────────────────────────────────────────────────────────────────
    L(F, 2950, '"Un dossier de PNG, relisible par tout moteur — et le seul livrable qui emporte la height (donc le '
      'displacement) et la profondeur 16 bits."', "matiere.mf3_export.note_zip",
      "Un dossier de PNG, relisible par tout moteur — et le seul livrable qui emporte la height (donc le "
      "displacement) et la profondeur 16 bits.",
      "A folder of PNGs, readable by any engine — and the only deliverable that carries the height map (hence "
      "displacement) and 16-bit depth."),
    L(F, 2951, '"Fichier unique, textures embarquées : Blender, Unity, Godot, la visionneuse Windows. La height '
      'n\'existe pas en glTF cœur — prends le ZIP pour le displacement."', "matiere.mf3_export.note_glb",
      "Fichier unique, textures embarquées : Blender, Unity, Godot, la visionneuse Windows. La height n'existe pas "
      "en glTF cœur — prends le ZIP pour le displacement.",
      "Single file, embedded textures: Blender, Unity, Godot, the Windows viewer. Core glTF has no height map — "
      "use the ZIP for displacement."),
    L(F, 2952, '"Même scène en JSON lisible (buffer base64) : plus lourd que le GLB, mais versionnable et '
      'inspectable à la main."', "matiere.mf3_export.note_gltf",
      "Même scène en JSON lisible (buffer base64) : plus lourd que le GLB, mais versionnable et inspectable à la "
      "main.",
      "Same scene as readable JSON (base64 buffer): heavier than the GLB, but versionable and inspectable by hand."),
    L(F, 2955, '"8 bits partout : poids minimal, et c\'est tout ce que voient la couleur, la rugosité et l\'AO."',
      "matiere.mf3_export.note_8bits",
      "8 bits partout : poids minimal, et c'est tout ce que voient la couleur, la rugosité et l'AO.",
      "8 bits everywhere: smallest size, and all that color, roughness and AO can show anyway."),
    L(F, 2956, '"16 bits appliqué à height et normal uniquement — les deux maps où les paliers se voient (bandes '
      'sur le displacement). Les autres restent en 8 bits, l\'archive ne double pas."',
      "matiere.mf3_export.note_16bits",
      "16 bits appliqué à height et normal uniquement — les deux maps où les paliers se voient (bandes sur le "
      "displacement). Les autres restent en 8 bits, l'archive ne double pas.",
      "16 bits applied to height and normal only — the two maps where stepping shows (banding on displacement). "
      "The others stay 8-bit, so the archive doesn't double in size."),

    # ── unités de poids ──────────────────────────────────────────────────────────────────────────────────────
    S(F, 2976, 'return n + " o";', 'return dzT("matiere.mf3_poids.octets", { n });',
      {"matiere.mf3_poids.octets": ("{n} o", "{n} B", "contexte")}),
    S(F, 2977, '.replace(".", ",") + " ko";', '.replace(".", ",") + " " + dzT("matiere.mf3_poids.ko");',
      {"matiere.mf3_poids.ko": ("ko", "KB", "contexte")}),
    S(F, 2978, '.replace(".", ",") + " Mo";', '.replace(".", ",") + " " + dzT("matiere.mf3_poids.mo");',
      {"matiere.mf3_poids.mo": ("Mo", "MB", "contexte")}),

    # ── bordereau ────────────────────────────────────────────────────────────────────────────────────────────
    S(F, 3033, '\'<div class="mani-empty">Bordereau indisponible : \' + esc(e.message) + "</div>"',
      '\'<div class="mani-empty">\' + esc(dzT("matiere.mf3_mani.indispo", { msg: e.message })) + "</div>"',
      {"matiere.mf3_mani.indispo": ("Bordereau indisponible : {msg}", "File list unavailable: {msg}")}),
    S(F, 3036, 'ico("dz-action-telecharger") + " Télécharger"',
      'ico("dz-action-telecharger") + " " + dzT("matiere.mf3_export.telecharger")',
      {"matiere.mf3_export.telecharger": ("Télécharger", "Download")}),
    S(F, 3076, '(e.weigh ? " · Poids " + (e.exact ? "mesuré" : "estimé") + " : " +\r\n'
               '                   esc(e.weigh) : "")',
      '(e.weigh ? " · " + esc(e.exact ? dzT("matiere.mf3_mani.poids_mesure", { poids: e.weigh })\r\n'
      '                   : dzT("matiere.mf3_mani.poids_estime", { poids: e.weigh })) : "")',
      {"matiere.mf3_mani.poids_mesure": ("Poids mesuré : {poids}", "Measured size: {poids}"),
       "matiere.mf3_mani.poids_estime": ("Poids estimé : {poids}", "Estimated size: {poids}")}),
    S(F, 3078, '" — obligatoire : sans couleur de base, la matière livrée est inutilisable"',
      '" — " + esc(dzT("matiere.mf3_mani.obligatoire"))',
      {"matiere.mf3_mani.obligatoire": ("obligatoire : sans couleur de base, la matière livrée est inutilisable",
                                        "required: without a base color, the delivered material is unusable")}),
    S(F, 3082, '\' <i class="req">requise</i>\'',
      '\' <i class="req">\' + dzT("matiere.mf3_mani.requise") + "</i>"',
      {"matiere.mf3_mani.requise": ("requise", "required", "contexte")}),
    S(F, 3094, '(e.weigh ? " — poids " + (e.exact ? "mesuré" : "estimé") + " : " +\r\n'
               '                   esc(e.weigh) : "")',
      '(e.weigh ? " — " + esc(e.exact ? dzT("matiere.mf3_mani.poids_mesure_min", { poids: e.weigh })\r\n'
      '                   : dzT("matiere.mf3_mani.poids_estime_min", { poids: e.weigh })) : "")',
      {"matiere.mf3_mani.poids_mesure_min": ("poids mesuré : {poids}", "measured size: {poids}"),
       "matiere.mf3_mani.poids_estime_min": ("poids estimé : {poids}", "estimated size: {poids}")}),
    S(F, 3116, '"· " + (nsel + (d.extras || []).length) + " fichiers"',
      '"· " + dzT("matiere.mf3_mani.n_fichiers", { n: nsel + (d.extras || []).length })',
      {"matiere.mf3_mani.n_fichiers": ("{n} fichiers", "{n} files")}),
    X(F, 3120, '\' <b class="est-size">\'',"balise et classe CSS"),

    # ── note de définition (rééchantillonnage) ───────────────────────────────────────────────────────────────
    S(F, 3154, 'k ? "les " + k + " PNG" : "les PNG"',
      'k ? dzT("matiere.mf3_res.les_n_png", { n: k }) : dzT("matiere.mf3_res.les_png")',
      {"matiere.mf3_res.les_n_png": ("les {n} PNG", "the {n} PNGs"),
       "matiere.mf3_res.les_png": ("les PNG", "the PNGs")}),
    S(F, 3157, 's = "Livraison à la définition native (" + (n || t) + "²) : aucun " +\r\n'
               '        "rééchantillonnage, " + png + " partent tels qu\'ils ont été calculés.";',
      's = dzT("matiere.mf3_res.native", { res: n || t, png });',
      {"matiere.mf3_res.native": ("Livraison à la définition native ({res}²) : aucun rééchantillonnage, {png} "
                                  "partent tels qu'ils ont été calculés.",
                                  "Delivered at native resolution ({res}²): no resampling, {png} ship exactly as "
                                  "computed.")}),
    S(F, 3160, 's = "Agrandissement à la livraison : " + n + "² → " + t + "², " + png + " sont " +\r\n'
               '        "interpolés. Le fichier grossit, le détail non — pour de vrais pixels en " +\r\n'
               '        t + "², reforge la matière à cette définition.";',
      's = dzT("matiere.mf3_res.agrandi", { n, t, png });',
      {"matiere.mf3_res.agrandi": ("Agrandissement à la livraison : {n}² → {t}², {png} sont interpolés. Le fichier "
                                   "grossit, le détail non — pour de vrais pixels en {t}², reforge la matière à "
                                   "cette définition.",
                                   "Upscaled on delivery: {n}² → {t}², {png} are interpolated. The file gets "
                                   "bigger, the detail doesn't — for real pixels at {t}², reforge the material at "
                                   "that resolution.")}),
    S(F, 3164, 's = "Réduction à la livraison : " + n + "² → " + t + "², " + png + " sont " +\r\n'
               '        "rééchantillonnés (Lanczos pour la couleur, bicubique pour les données, " +\r\n'
               '        "normale renormalisée). Micro-détail perdu ; la matière rangée sur " +\r\n'
               '        "disque, elle, ne bouge pas.";',
      's = dzT("matiere.mf3_res.reduit", { n, t, png });',
      {"matiere.mf3_res.reduit": ("Réduction à la livraison : {n}² → {t}², {png} sont rééchantillonnés (Lanczos "
                                  "pour la couleur, bicubique pour les données, normale renormalisée). Micro-détail "
                                  "perdu ; la matière rangée sur disque, elle, ne bouge pas.",
                                  "Downscaled on delivery: {n}² → {t}², {png} are resampled (Lanczos for color, "
                                  "bicubic for data, normal renormalized). Fine detail is lost; the material stored "
                                  "on disk stays unchanged.")}),

    # ── règle du « ≈ » ───────────────────────────────────────────────────────────────────────────────────────
    S(F, 3196, '"Un poids est mesuré quand le fichier qui part existe déjà, encodé, sur le " +\r\n'
               '  "disque. Il est estimé — « ≈ » — dès que l\'export doit en fabriquer un.";',
      'dzT("matiere.mf3_poids.regle");',
      {"matiere.mf3_poids.regle": ("Un poids est mesuré quand le fichier qui part existe déjà, encodé, sur le "
                                   "disque. Il est estimé — « ≈ » — dès que l'export doit en fabriquer un.",
                                   "A size is measured when the outgoing file already exists, encoded, on disk. It "
                                   "is estimated — “≈” — as soon as the export has to build one.")}),
    S(F, 3210, 'el.innerHTML = "<b>Poids mesurés.</b> Les " + (mes.length + ann.length) +\r\n'
               '      " fichiers de cette archive sont comptés octet par octet — les " +\r\n'
               '      mes.length + " PNG partent tels qu\'ils sont sur le disque, rien n\'est " +\r\n'
               '      "fabriqué à l\'export.";',
      'el.innerHTML = "<b>" + dzT("matiere.mf3_poids.mesures_titre") + "</b> " +\r\n'
      '      dzT("matiere.mf3_poids.mesures", { n: mes.length + ann.length, png: mes.length });',
      {"matiere.mf3_poids.mesures_titre": ("Poids mesurés.", "Measured sizes."),
       "matiere.mf3_poids.mesures": ("Les {n} fichiers de cette archive sont comptés octet par octet — les {png} PNG "
                                     "partent tels qu'ils sont sur le disque, rien n'est fabriqué à l'export.",
                                     "All {n} files in this archive are counted byte for byte — the {png} PNGs ship "
                                     "as they are on disk, nothing is built at export.")}),
    X(F, 3214, '"est"', "classe CSS"),
    L(F, 3220, '"fabriqué à l\'export"', "matiere.mf3_poids.fabrique", "fabriqué à l'export", "built at export"),
    S(F, 3233, '"<b>La règle du ≈ :</b> "', '"<b>" + dzT("matiere.mf3_poids.regle_titre") + "</b> "',
      {"matiere.mf3_poids.regle_titre": ("La règle du ≈ :", "The ≈ rule:")}),
    S(F, 3234, '"<br><b>Ici :</b> "', '"<br><b>" + dzT("matiere.mf3_poids.ici") + "</b> "',
      {"matiere.mf3_poids.ici": ("Ici :", "Here:", "contexte")}),
    S(F, 3235, '"</b> partent inchangées, poids " +\r\n      "lus sur le disque."',
      '"</b> " + dzT("matiere.mf3_poids.inchangees")',
      {"matiere.mf3_poids.inchangees": ("partent inchangées, poids lus sur le disque.",
                                        "ship unchanged, sizes read from disk.")}),
    S(F, 3237, '" Le modèle est calibré sur de vraies archives ; écart mesuré sur 28 " +\r\n'
               '    "exports de contrôle : " +\r\n'
               '    (down ? "jusqu\'à +23 % en rééchantillonnant" : "±7 %") +\r\n'
               '    ". Le poids exact reste celui du fichier téléchargé."',
      '" " + dzT("matiere.mf3_poids.calibre", { ecart: down ? dzT("matiere.mf3_poids.ecart_reech") : "±7 %" })',
      {"matiere.mf3_poids.calibre": ("Le modèle est calibré sur de vraies archives ; écart mesuré sur 28 exports de "
                                     "contrôle : {ecart}. Le poids exact reste celui du fichier téléchargé.",
                                     "The model is calibrated on real archives; deviation measured over 28 control "
                                     "exports: {ecart}. The exact size is that of the downloaded file."),
       "matiere.mf3_poids.ecart_reech": ("jusqu'à +23 % en rééchantillonnant", "up to +23% when resampling")}),
    X(F, 3241, '"est"', "classe CSS"),
    L(F, 3250, '"Définition source de cette matière — aucun rééchantillonnage"', "matiere.mf3_res.titre_source",
      "Définition source de cette matière — aucun rééchantillonnage",
      "Source resolution of this material — no resampling"),
    S(F, 3252, '"Agrandissement par interpolation depuis " + native + "²"',
      'dzT("matiere.mf3_res.titre_agrandi", { res: native })',
      {"matiere.mf3_res.titre_agrandi": ("Agrandissement par interpolation depuis {res}²",
                                         "Upscaled by interpolation from {res}²")}),
    S(F, 3253, '"Réduction depuis " + native + "²"', 'dzT("matiere.mf3_res.titre_reduit", { res: native })',
      {"matiere.mf3_res.titre_reduit": ("Réduction depuis {res}²", "Downscaled from {res}²")}),
    S(F, 3324, 'toast("Téléchargement : " + (a.download || (mani && mani.archive) ||\r\n'
               '    ((m && (m.name || m.id)) || mid)) + w);',
      'toast(dzT("matiere.mf3_export.telechargement", { nom: (a.download || (mani && mani.archive) ||\r\n'
      '    ((m && (m.name || m.id)) || mid)) + w }));',
      {"matiere.mf3_export.telechargement": ("Téléchargement : {nom}", "Downloading: {nom}")}),

    # ── puces maillage ───────────────────────────────────────────────────────────────────────────────────────
    L(F, 3351, '"Mon modèle"', "matiere.mf3_maillage.mon_modele", "Mon modèle", "My model", contexte=True),
    L(F, 3358, '"Un modèle de l\'Établi, habillé de la matière (aperçu seulement : rien n\'est écrit)"',
      "matiere.mf3_maillage.mon_modele_aide",
      "Un modèle de l'Établi, habillé de la matière (aperçu seulement : rien n'est écrit)",
      "A model from the Workbench, dressed in the material (preview only: nothing is written)"),
    L(F, 3362, '"Variés"', "matiere.mf3_maillage.varies", "Variés", "Varied", contexte=True),
    L(F, 3365, '"Les six maillages à tour de rôle, une carte après l\'autre."', "matiere.mf3_maillage.varies_aide",
      "Les six maillages à tour de rôle, une carte après l'autre.", "The six meshes in turn, one card after another."),
    L(F, 3375, '"Les six maillages à tour de rôle, une carte après l\'autre : une matière ne se juge pas que sur une '
      'sphère."', "matiere.mf3_maillage.note_varies",
      "Les six maillages à tour de rôle, une carte après l'autre : une matière ne se juge pas que sur une sphère.",
      "The six meshes in turn, one card after another: a material can't be judged on a sphere alone."),
    L(F, 3376, '"Toutes les cartes sont rendues sur ce maillage."', "matiere.mf3_maillage.note_un",
      "Toutes les cartes sont rendues sur ce maillage.", "All cards are rendered on this mesh."),
    L(F, 3412, '"liste des modèles de l\'Établi"', "matiere.mf3_maillage.liste_etabli", "liste des modèles de l'Établi",
      "Workbench model list"),
    L(F, 3413, '"Aucun modèle dans l\'Établi : génère ou importe d\'abord un modèle 3D."',
      "matiere.mf3_maillage.aucun_modele", "Aucun modèle dans l'Établi : génère ou importe d'abord un modèle 3D.",
      "No model in the Workbench: generate or import a 3D model first."),

    # ── environnements ───────────────────────────────────────────────────────────────────────────────────────
    L(F, 3464, '"Ambiance importée"', "matiere.mf3_env.importee", "Ambiance importée", "Imported environment"),

    # ── référence téléversée ─────────────────────────────────────────────────────────────────────────────────
    X(F, 3535, '"reference.png"', "nom de fichier par défaut envoyé au serveur"),
    S(F, 3540, 'toast("Référence téléversée : " + d.filename)',
      'toast(dzT("matiere.mf3_ref.ok", { nom: d.filename }))',
      {"matiere.mf3_ref.ok": ("Référence téléversée : {nom}", "Reference uploaded: {nom}")}),
    S(F, 3541, 'toast("Téléversement impossible : " + e.message, true)',
      'toast(dzT("matiere.mf3_ref.err", { msg: e.message }), true)',
      {"matiere.mf3_ref.err": ("Téléversement impossible : {msg}", "Upload failed: {msg}")}),

    # ── panneau Photo ────────────────────────────────────────────────────────────────────────────────────────
    L(F, 3620, '"Choisis d\'abord une image de référence."', "matiere.mf3_photo.sans_ref",
      "Choisis d'abord une image de référence.", "Pick a reference image first."),
    S(F, 3622, '"Rien à préparer : coche « Retirer l\'éclairage » ou "\r\n'
               '                     + "clique les quatre coins."',
      'dzT("matiere.mf3_photo.rien")',
      {"matiere.mf3_photo.rien": ("Rien à préparer : coche « Retirer l'éclairage » ou clique les quatre coins.",
                                  "Nothing to prepare: tick “Remove lighting” or click the four corners.")}),
    L(F, 3632, '"redressée"', "matiere.mf3_photo.redressee", "redressée", "rectified", contexte=True),
    L(F, 3642, '"préparation de la photo"', "matiere.mf3_photo.preparation", "préparation de la photo",
      "photo preparation"),
    S(F, 3643, 'toast("Préparation refusée : " + e.message, true)',
      'toast(dzT("matiere.mf3_photo.refusee", { msg: e.message }), true)',
      {"matiere.mf3_photo.refusee": ("Préparation refusée : {msg}", "Preparation refused: {msg}")}),

    # ── comparaison ──────────────────────────────────────────────────────────────────────────────────────────
    L(F, 3692, '"Il faut au moins deux matières pour comparer."', "matiere.mf3_cmp.deux",
      "Il faut au moins deux matières pour comparer.", "You need at least two materials to compare."),

    # ── générateurs ──────────────────────────────────────────────────────────────────────────────────────────
    L(F, 3708, '"générateurs"', "matiere.mf3_gen.generateurs", "générateurs", "generators", contexte=True),
    S(F, 3708, 'toast("Générateurs : " + e.message, true)',
      'toast(dzT("matiere.mf3_gen.err", { msg: e.message }), true)',
      {"matiere.mf3_gen.err": ("Générateurs : {msg}", "Generators: {msg}")}),
    S(F, 3800, 'toast(`Matière « ${d.material.name} » créée en local, sans crédit.`)',
      'toast(dzT("matiere.mf3_gen.cree", { nom: d.material.name }))',
      {"matiere.mf3_gen.cree": ("Matière « {nom} » créée en local, sans crédit.",
                                "Material “{nom}” created locally, no credits used.")}),
    L(F, 3802, '"génération de motif"', "matiere.mf3_gen.generation", "génération de motif", "pattern generation"),
    S(F, 3802, 'toast("Génération refusée : " + e.message, true)',
      'toast(dzT("matiere.mf3_gen.refusee", { msg: e.message }), true)',
      {"matiere.mf3_gen.refusee": ("Génération refusée : {msg}", "Generation refused: {msg}")}),

    # ── import / suppression d'ambiance ──────────────────────────────────────────────────────────────────────
    S(F, 3818, 'toast(`Ambiance « ${d.env.label} » importée.`)',
      'toast(dzT("matiere.mf3_env.import_ok", { nom: d.env.label }))',
      {"matiere.mf3_env.import_ok": ("Ambiance « {nom} » importée.", "Environment “{nom}” imported.")}),
    L(F, 3821, '"import d\'ambiance"', "matiere.mf3_env.import", "import d'ambiance", "environment import"),
    S(F, 3822, 'toast("Import refusé : " + err.message, true)',
      'toast(dzT("matiere.mf3_env.import_err", { msg: err.message }), true)',
      {"matiere.mf3_env.import_err": ("Import refusé : {msg}", "Import refused: {msg}")}),
    L(F, 3829, '"Les sept ambiances du studio ne se suppriment pas."', "matiere.mf3_env.studio",
      "Les sept ambiances du studio ne se suppriment pas.", "The seven studio environments can't be deleted."),
    S(F, 3834, 'toast("Suppression impossible : " + err.message, true)',
      'toast(dzT("matiere.mf3_env.suppr_err", { msg: err.message }), true)',
      {"matiere.mf3_env.suppr_err": ("Suppression impossible : {msg}", "Could not delete: {msg}")}),

    # ── aide de l'inspecteur ─────────────────────────────────────────────────────────────────────────────────
    L(F, 3951, '"Masquer l\'aide de toutes les propriétés"', "matiere.mf3_aide.masquer",
      "Masquer l'aide de toutes les propriétés", "Hide help for all properties"),
    L(F, 3952, '"Afficher l\'aide de toutes les propriétés d\'un coup"', "matiere.mf3_aide.afficher",
      "Afficher l'aide de toutes les propriétés d'un coup", "Show help for all properties at once"),

    # ── harnais de charge (QA) ───────────────────────────────────────────────────────────────────────────────
    X(F, 4025, '"matière"', "nom des matières factices du harnais de charge __stress (QA)"),
]
