"""t147 — face : js/mod-face.js entier (pièce 01 · Face du Card Forge : catalogue, pile d'images importées, pont
Vectorlab, jauge de DPI, contrôle de fidélité, export PNG, génération par IA, placement à la main).

GARDÉ (X), en résumé :
  - les libellés des tables CF-FACE-*-BEGIN/END (palettes, sujets, compositions, séries) : miroir de
    backend/app/services/cards/face.py, extraits mot pour mot par test_cards_face.py ; ce sont aussi les NOMS des
    faces du catalogue (contenu des cartes), écrits dans les noms de calques et titres ;
  - les amorces de génération (PROMPT_SEEDS) et le suffixe de cadrage : PROMPTS envoyés au générateur d'images,
    miroir de face.py:PROMPT_SEEDS (libellés et textes) ;
  - les noms de calques / de documents vectoriels écrits au serveur, le texte peint DANS la mire (pixels du fichier),
    les types MIME, les polices canvas, les gardes de chargement et les messages de console.
"""
from outils import L, S, X, H

F = "js/mod-face.js"
K = "cartes.face."


def c(s):
    """les sources sont en CRLF : un saut de ligne écrit ici devient \\r\\n."""
    return s.replace("\r\n", "\n").replace("\n", "\r\n")


def SS(ligne, avant, apres, dico, n=1):
    return S(F, ligne, c(avant), c(apres), {K + k: v for k, v in dico.items()}, n)


def LL(ligne, lit, cle, fr, en, n=1, contexte=False):
    return L(F, ligne, lit, K + cle, fr, en, n, contexte)


def XX(ligne, lit, raison, n=1):
    return X(F, ligne, lit, raison, n)


MIROIR = "libellé d'une table CF-FACE-*-BEGIN/END, miroir de cards/face.py extrait par test_cards_face (nom de face du catalogue)"
MIME = "type MIME"

ENTREES = [
    XX(79, '"use strict"', "directive JS"),
    XX(83, '"mod-face: js/core.js doit etre charge avant ce fichier"', "garde de chargement"),
    LL(103, '"Carré HD"', "taille_carre_hd", "Carré HD", "Square HD"),
    XX(114, '"Crépuscule"', MIROIR),
    XX(120, '"Néant"', MIROIR),
    XX(129, '"Forêt de pins"', MIROIR),
    XX(139, '"Baleine céleste"', MIROIR),
    XX(140, '"Phénix"', MIROIR),
    XX(141, '"Serpent des mers"', MIROIR),
    XX(143, '"Archère"', MIROIR),
    XX(166, '"Médaillon"', MIROIR),

    # ── 3. la pile d'images importées ──
    LL(1603, '"fichier illisible comme image"', "err_illisible", "fichier illisible comme image",
       "file is not a readable image"),
    XX(1616, '"image/png"', MIME),
    LL(1621, '"aucune image dans ce qui a été déposé"', "rien_depose", "aucune image dans ce qui a été déposé",
       "no image in what was dropped"),
    SS(1623, '"import de " + files.length + " illustration(s)…"', 'dzT("cartes.face.import_n", { n: files.length })',
       {"import_n": ("import de {n} illustration(s)…", "importing {n} illustration(s)…")}),
    XX(1647, '"image"', "nom de fichier par défaut, rangé dans la pile"),
    XX(1648, '"image/png"', MIME),
    XX(1701, '"700 30px sans-serif"', "police canvas"),
    XX(1705, '"13px sans-serif"', "police canvas"),
    XX(1710, '"mire de contrôle"', "texte peint dans les pixels de la mire (fichier rangé dans la pile)"),
    LL(1712, '"le moteur n\'a pas encodé la mire"', "err_mire", "le moteur n'a pas encodé la mire",
       "the engine did not encode the test pattern"),
    XX(1713, '"image/png"', MIME),
    XX(1721, '"image/png"', MIME),
    LL(1724, '"l\'import n\'a rien retenu"', "import_rien", "l'import n'a rien retenu", "the import kept nothing"),
    LL(1726, '"de contrôle dans la pile"', "quoi_mire", "de contrôle dans la pile",
       "added to the stack as a test pattern"),
    LL(1728, '"mire : "', "err_mire_pref", "mire : ", "test pattern: "),
    LL(1794, '"Adopter le sujet détouré de la carte importée"', "adopter_sujet",
       "Adopter le sujet détouré de la carte importée", "Adopt the cut-out subject of the imported card"),
    LL(1800, '"Adopter le recto entier de la carte importée (recadrage art)"', "adopter_recto",
       "Adopter le recto entier de la carte importée (recadrage art)",
       "Adopt the whole front of the imported card (art crop)"),
    LL(1808, '"image de capture illisible"', "err_capture", "image de capture illisible", "unreadable capture image"),
    LL(1812, '"le moteur n\'a pas encodé l\'image"', "err_encode", "le moteur n'a pas encodé l'image",
       "the engine did not encode the image"),
    XX(1813, '"image/png"', MIME),
    LL(1840, '"rien à adopter : reprenez d\'abord une carte dans la pièce Import"', "rien_adopter",
       "rien à adopter : reprenez d'abord une carte dans la pièce Import",
       "nothing to adopt: first capture a card in the Import panel"),
    LL(1845, '"la pièce Import annonce un fichier que sa liste blanche ne sert pas"', "capture_hors_liste",
       "la pièce Import annonce un fichier que sa liste blanche ne sert pas",
       "the Import panel lists a file that its whitelist does not serve"),
    XX(1868, '"image/png"', MIME),
    LL(1872, '"l\'import n\'a rien retenu"', "import_rien", "l'import n'a rien retenu", "the import kept nothing"),
    LL(1874, '"déjà dans la pile — reposée plutôt que réimportée"', "quoi_deja",
       "déjà dans la pile — reposée plutôt que réimportée", "already in the stack — placed again instead of re-imported"),
    LL(1875, '"détourée de la carte importée"', "quoi_sujet", "détourée de la carte importée",
       "cut out from the imported card"),
    LL(1876, '"reprise entière de la carte importée"', "quoi_recto", "reprise entière de la carte importée",
       "taken whole from the imported card"),
    LL(1878, '"adoption : "', "err_adoption", "adoption : ", "adoption: "),

    # ── 3-ter. le pont Vectorlab ──
    LL(1919, '"documents vectoriels : "', "err_vecs", "documents vectoriels : ", "vector documents: "),
    LL(1947, '"aucun jeu ouvert"', "aucun_jeu", "aucun jeu ouvert", "no deck open"),
    XX(1950, '"Illustration "', "nom par défaut du document vectoriel, écrit au serveur"),
    XX(1954, '"calque 1"', "nom de calque écrit dans le document vectoriel (serveur)"),
    LL(1961, '"création : "', "err_creation", "création : ", "creation: "),
    XX(1981, '"face (verrouillée)"', "nom de calque écrit dans le document vectoriel (serveur)"),
    XX(1982, '"image"', "type d'objet du document vectoriel"),
    XX(1984, '"retouches"', "nom de calque écrit dans le document vectoriel (serveur)"),
    LL(1989, '"aucun jeu ouvert"', "aucun_jeu", "aucun jeu ouvert", "no deck open"),
    XX(1991, '"Face "', "nom du document vectoriel, écrit au serveur"),
    SS(1992, '"rendu de la face à " + g.canvas_px[0] + " x " + g.canvas_px[1] + " px…"',
       'dzT("cartes.face.rendu_face", { w: g.canvas_px[0], h: g.canvas_px[1] })',
       {"rendu_face": ("rendu de la face à {w} x {h} px…", "rendering the face at {w} x {h} px…")}),
    LL(2003, '"éditer la face : "', "err_editer", "éditer la face : ", "edit the face: "),
    XX(2017, '"image/png"', MIME),
    SS(2019, '"aucun export 2× encore : dans le Vectorlab, menu Exporter "\n        + "→ PNG 2×, puis « Poser 2× » à nouveau"',
       'dzT("cartes.face.vec_pas_export")',
       {"vec_pas_export": ("aucun export 2× encore : dans le Vectorlab, menu Exporter → PNG 2×, puis « Poser 2× » à nouveau",
                           "no 2× export yet: in the Vectorlab, Export menu → PNG 2×, then “Place 2×” again")}),
    SS(2030, '"Supprimer ce document vectoriel ? Sa dernière version "\n                 + "reste archivée sur disque."',
       'dzT("cartes.face.vec_suppr_conf")',
       {"vec_suppr_conf": ("Supprimer ce document vectoriel ? Sa dernière version reste archivée sur disque.",
                           "Delete this vector document? Its latest version stays archived on disk.")}),
    LL(2035, '"suppression : "', "err_suppr", "suppression : ", "deletion: "),
    SS(2044, '\'<p class="empty-note sm">Aucun jeu ouvert.</p>\'',
       '\'<p class="empty-note sm">\' + dzT("cartes.face.aucun_jeu_p") + \'</p>\'',
       {"aucun_jeu_p": ("Aucun jeu ouvert.", "No deck open.")}),
    SS(2045, '\'<p class="empty-note sm">chargement…</p>\'',
       '\'<p class="empty-note sm">\' + dzT("cartes.face.chargement") + \'</p>\'',
       {"chargement": ("chargement…", "loading…")}),
    SS(2047, '\'<p class="empty-note sm">Aucun document vectoriel pour ce jeu \'\n        + \'— créez-en un ci-dessus.</p>\'',
       '\'<p class="empty-note sm">\' + dzT("cartes.face.vec_aucun") + \'</p>\'',
       {"vec_aucun": ("Aucun document vectoriel pour ce jeu — créez-en un ci-dessus.",
                      "No vector document for this deck — create one above.")}),
    SS(2056, '\'<span class="cf-face-vlab-sans" title="la vignette naît au premier Sauver">\'',
       '\'<span class="cf-face-vlab-sans" title="\' + dzT("cartes.face.vig_naissance") + \'">\'',
       {"vig_naissance": ("la vignette naît au premier Sauver", "the thumbnail appears on the first Save")}),
    SS(2062, '\'" title="Ouvrir dans le Vectorlab (nouvel onglet)">Ouvrir</button>\'',
       '\'" title="\' + dzT("cartes.face.vec_ouvrir_t") + \'">\' + dzT("cartes.face.ouvrir") + \'</button>\'',
       {"vec_ouvrir_t": ("Ouvrir dans le Vectorlab (nouvel onglet)", "Open in the Vectorlab (new tab)"),
        "ouvrir": ("Ouvrir", "Open")}),
    SS(2064, '\'" title="Pose l\\\'export PNG 2× comme illustration de la carte">Poser 2×</button>\'',
       '\'" title="\' + dzT("cartes.face.vec_poser_t") + \'">\' + dzT("cartes.face.vec_poser") + \'</button>\'',
       {"vec_poser_t": ("Pose l'export PNG 2× comme illustration de la carte",
                        "Places the PNG 2× export as the card's illustration"),
        "vec_poser": ("Poser 2×", "Place 2×")}),
    SS(2066, '\'" title="Supprimer (la dernière version reste archivée)" aria-label="Supprimer (la dernière version reste archivée)">\'',
       '\'" title="\' + dzT("cartes.face.vec_suppr_t") + \'" aria-label="\' + dzT("cartes.face.vec_suppr_t") + \'">\'',
       {"vec_suppr_t": ("Supprimer (la dernière version reste archivée)", "Delete (the latest version stays archived)")}),

    # ── 4-5. résolution, fenêtres ──
    LL(2147, '"image importée"', "image_importee", "image importée", "imported image"),
    LL(2184, '"Auto — celle du cadre, sinon la toile entière"', "win_auto",
       "Auto — celle du cadre, sinon la toile entière", "Auto — the frame's window, else the full canvas"),
    LL(2185, '"Toile entière (fond perdu compris)"', "win_full", "Toile entière (fond perdu compris)",
       "Full canvas (bleed included)"),
    LL(2186, '"Coupe"', "win_trim", "Coupe", "Trim"),
    LL(2187, '"Zone sûre"', "win_safe", "Zone sûre", "Safe area"),
    LL(2188, '"Fenêtre 3:4 haute"', "win_art34", "Fenêtre 3:4 haute", "Tall 3:4 window"),
    SS(2337, "ppm + ' px/m (unité mètre) = <b>' + ppmToDpi(ppm).toFixed(4)\n"
             "      + ' DPI</b> — pHYs ne stocke que des entiers de pixels par mètre, et '\n"
             "      + dpi + ' DPI en vaut ' + (dpi / PHYS_METRE).toFixed(3) + '.'",
       'dzT("cartes.face.phys_ligne", { ppm: ppm, dpif: ppmToDpi(ppm).toFixed(4), dpi: dpi, exact: (dpi / PHYS_METRE).toFixed(3) })',
       {"phys_ligne": ("{ppm} px/m (unité mètre) = <b>{dpif} DPI</b> — pHYs ne stocke que des entiers de pixels par mètre, et {dpi} DPI en vaut {exact}.",
                       "{ppm} px/m (unit: metre) = <b>{dpif} DPI</b> — pHYs only stores whole pixels per metre, and {dpi} DPI is {exact}.")}),

    # ── 6. le painter : le gabarit vide peint sur l'aperçu ──
    XX(2417, '"px sans-serif"', "police canvas"),
    LL(2418, '"Aucune illustration"', "ph_aucune", "Aucune illustration", "No illustration"),
    XX(2419, '"px sans-serif"', "police canvas"),
    LL(2420, '"déposez une image ici,"', "ph_deposez", "déposez une image ici,", "drop an image here,"),
    LL(2421, '"piochez au catalogue ou générez-la"', "ph_piochez", "piochez au catalogue ou générez-la",
       "pick from the catalog or generate one"),

    # ── 7. le panneau ──
    XX(2559, '"image"', "initiatorType comparé (API Performance)"),
    LL(2574, '"rien à annuler"', "rien_annuler", "rien à annuler", "nothing to undo"),
    LL(2577, '"annulé"', "annule", "annulé", "undone", contexte=True),
    LL(2580, '"rien à rétablir"', "rien_retablir", "rien à rétablir", "nothing to redo"),
    LL(2583, '"rétabli"', "retabli", "rétabli", "redone", contexte=True),
    LL(2589, '"illustration posée"', "posee", "illustration posée", "illustration placed"),
    SS(2597, 'CF.toast(added.length + " illustration(s) " + (quoi || "dans la pile") + " — la première est posée");',
       'CF.toast(dzT("cartes.face.apres_import", { n: added.length, quoi: quoi || dzT("cartes.face.quoi_pile") }));',
       {"apres_import": ("{n} illustration(s) {quoi} — la première est posée",
                         "{n} illustration(s) {quoi} — the first one is placed"),
        "quoi_pile": ("dans la pile", "added to the stack")}),
    XX(2759, '"mod-face: mesure du masquage"', "message de console"),
    SS(2771, '\'<span class="mono">Fenêtre d\\\'illustration : la pose y tient entière, aucun recadrage.</span>\'',
       '\'<span class="mono">\' + dzT("cartes.face.crop_entiere") + \'</span>\'',
       {"crop_entiere": ("Fenêtre d'illustration : la pose y tient entière, aucun recadrage.",
                         "Art window: the placed image fits entirely, no cropping.")}),
    SS(2772, '\'<span class="cf-face-crop"><b>\' + fmt1(p) + \' % de la pose tient dans la fenêtre \'\n'
             '        + \'d\\\'illustration</b> — les \' + fmt1(100 - p) + \' % restants en sortent et sont \'\n'
             '        + \'coupés. Passez en « Contenir » pour tout garder, ou déplacez la pose.\'',
       '\'<span class="cf-face-crop">\' + dzT("cartes.face.crop_partiel", { p: fmt1(p), r: fmt1(100 - p) })',
       {"crop_partiel": ("<b>{p} % de la pose tient dans la fenêtre d'illustration</b> — les {r} % restants en sortent et sont coupés. Passez en « Contenir » pour tout garder, ou déplacez la pose.",
                         "<b>{p} % of the placed image fits in the art window</b> — the remaining {r} % falls outside and is cropped. Switch to “Contain” to keep everything, or move the image.")}),
    SS(2778, '\'data-fix="window">Recadrer sur la fenêtre</button>\'',
       '\'data-fix="window">\' + dzT("cartes.face.recadrer_fenetre") + \'</button>\'',
       {"recadrer_fenetre": ("Recadrer sur la fenêtre", "Fit to the window")}),
    SS(2798, '\'<span class="mono">Ce qui atteint le papier : mesure en cours…</span>\'',
       '\'<span class="mono">\' + dzT("cartes.face.papier_en_cours") + \'</span>\'',
       {"papier_en_cours": ("Ce qui atteint le papier : mesure en cours…", "What reaches the paper: measuring…")}),
    SS(2802, '\'<span class="cf-face-crop">Ce qui atteint le papier : <b>non mesurable</b> — \'\n'
             '        + \'deux rendus identiques de cette carte diffèrent de \'\n'
             '        + MASK.temoin.toLocaleString("fr-FR") + \' pixels, une couche du dessus n\\\'est pas \'\n'
             '        + \'déterministe. Aucun pourcentage ne serait vérifiable ici.</span>\'',
       '\'<span class="cf-face-crop">\' + dzT("cartes.face.papier_non_mesurable", { n: MASK.temoin.toLocaleString("fr-FR") }) + \'</span>\'',
       {"papier_non_mesurable": ("Ce qui atteint le papier : <b>non mesurable</b> — deux rendus identiques de cette carte diffèrent de {n} pixels, une couche du dessus n'est pas déterministe. Aucun pourcentage ne serait vérifiable ici.",
                                 "What reaches the paper: <b>not measurable</b> — two identical renders of this card differ by {n} pixels, a layer above is not deterministic. No percentage could be verified here.")}),
    SS(2810, '\'">Sur la carte imprimée : <b>\' + fmt1(pv)\n'
             '      + \' % de la pose atteint le papier</b>\'\n'
             '      + (pv + 0.05 < pw ? \' — le cadre et les textes en masquent \' + fmt1(pw - pv)\n'
             '        + \' points de plus.\'',
       '\'">\' + dzT("cartes.face.papier_pct", { p: fmt1(pv) })\n'
       '      + (pv + 0.05 < pw ? dzT("cartes.face.papier_masque", { d: fmt1(pw - pv) })',
       {"papier_pct": ("Sur la carte imprimée : <b>{p} % de la pose atteint le papier</b>",
                       "On the printed card: <b>{p} % of the placed image reaches the paper</b>"),
        "papier_masque": (" — le cadre et les textes en masquent {d} points de plus.",
                          " — the frame and text boxes hide {d} more points.")}),
    SS(2828, '\'<span class="mono">Compté par le moteur : \' + MASK.vis.toLocaleString("fr-FR")\n'
             '      + \' px sur \' + (meme\n'
             '        ? \'une pose qui couvre la carte entière, \' + carte\n'
             '        : fmtPx(MASK.poseW) + \' × \' + fmtPx(MASK.poseH) + \' = \' + frac1(MASK.pose)\n'
             '          + \' px de pose, dans une carte de \' + carte)\n'
             '      + \' ; témoin de déterminisme \' + MASK.temoin + \' px\'\n'
             '      + (ecart === null ? \'\' : \' ; fenêtre recomptée \' + MASK.inWin.toLocaleString("fr-FR")\n'
             '        + \' px contre \' + frac1(px1(MASK.predit)) + \' prédits (\' + ecart.toFixed(2) + \' %)\')',
       '\'<span class="mono">\' + dzT("cartes.face.compte_moteur", { n: MASK.vis.toLocaleString("fr-FR") }) + (meme\n'
       '        ? dzT("cartes.face.compte_pose_entiere", { carte: carte })\n'
       '        : dzT("cartes.face.compte_pose", { w: fmtPx(MASK.poseW), h: fmtPx(MASK.poseH), a: frac1(MASK.pose), carte: carte }))\n'
       '      + dzT("cartes.face.temoin", { n: MASK.temoin })\n'
       '      + (ecart === null ? \'\' : dzT("cartes.face.recompte", { n: MASK.inWin.toLocaleString("fr-FR"), p: frac1(px1(MASK.predit)), e: ecart.toFixed(2) }))',
       {"compte_moteur": ("Compté par le moteur : {n} px sur ", "Counted by the engine: {n} px out of "),
        "compte_pose_entiere": ("une pose qui couvre la carte entière, {carte}",
                                "a placed image covering the whole card, {carte}"),
        "compte_pose": ("{w} × {h} = {a} px de pose, dans une carte de {carte}",
                        "{w} × {h} = {a} px of placed image, in a card of {carte}"),
        "temoin": (" ; témoin de déterminisme {n} px", "; determinism check {n} px"),
        "recompte": (" ; fenêtre recomptée {n} px contre {p} prédits ({e} %)",
                     "; window recounted {n} px vs {p} predicted ({e} %)")}),
    SS(2846, '\'<details class="cf-face-det"><summary>le détail, chiffre par chiffre</summary>\'',
       '\'<details class="cf-face-det"><summary>\' + dzT("cartes.face.detail") + \'</summary>\'',
       {"detail": ("le détail, chiffre par chiffre", "the details, figure by figure")}),
    SS(2880, '\'<span class="cf-face-crop">Couche de finition par-dessus l\\\'illustration : <b>\'\n'
             '        + esc(String(ov)) + \'</b>, opacité \' + Math.round(op * 100) + \' %, fusion \' + esc(bl)\n'
             '        + \' — <b>vos couleurs en sortent modifiées</b>. Réglage dans Matières.</span>\'',
       '\'<span class="cf-face-crop">\' + dzT("cartes.face.finition", { ov: esc(String(ov)), op: Math.round(op * 100), bl: esc(bl) }) + \'</span>\'',
       {"finition": ("Couche de finition par-dessus l'illustration : <b>{ov}</b>, opacité {op} %, fusion {bl} — <b>vos couleurs en sortent modifiées</b>. Réglage dans Matières.",
                     "Finish layer over the illustration: <b>{ov}</b>, opacity {op} %, blend {bl} — <b>your colors come out altered</b>. Set it in Materials.")}),
    SS(2897, '\'<span class="mono">fichier déposé \' + r.w0 + \' × \' + r.h0\n'
             '      + \' px, ramené à \' + MAX_IMPORT_PX + \' px de côté à l\\\'import : c\\\'est la trame \'\n'
             '      + \'ci-dessus qui est posée et mesurée.</span>\'',
       '\'<span class="mono">\' + dzT("cartes.face.import_reduit", { w: r.w0, h: r.h0, max: MAX_IMPORT_PX }) + \'</span>\'',
       {"import_reduit": ("fichier déposé {w} × {h} px, ramené à {max} px de côté à l'import : c'est la trame ci-dessus qui est posée et mesurée.",
                          "dropped file {w} × {h} px, scaled down to {max} px per side on import: the raster above is what is placed and measured.")}),
    SS(2910, '\'<div class="cf-face-gbody"><b>Aucune illustration posée</b>\'\n'
             '        + \'<span>Choisissez une face du catalogue, déposez une image ou générez-la. \'\n'
             '        + \'La jauge affichera alors le DPI réel de l\\\'impression.</span></div>\'',
       '\'<div class="cf-face-gbody"><b>\' + dzT("cartes.face.aucune_posee") + \'</b>\'\n'
       '        + \'<span>\' + dzT("cartes.face.jauge_vide") + \'</span></div>\'',
       {"aucune_posee": ("Aucune illustration posée", "No illustration placed"),
        "jauge_vide": ("Choisissez une face du catalogue, déposez une image ou générez-la. La jauge affichera alors le DPI réel de l'impression.",
                       "Pick a face from the catalog, drop an image or generate one. The gauge will then show the real print DPI.")}),
    SS(2934, '"Définition suffisante pour l\\\'impression" : "Définition insuffisante — sous " + DPI_TARGET + " DPI"',
       'dzT("cartes.face.def_ok") : dzT("cartes.face.def_basse", { cible: DPI_TARGET })',
       {"def_ok": ("Définition suffisante pour l'impression", "Resolution sufficient for print"),
        "def_basse": ("Définition insuffisante — sous {cible} DPI", "Resolution too low — under {cible} DPI")}),
    SS(2944, '\'<span class="mono">face vectorielle : redessinée à \' + fmtPx(LAST.dw) + \' × \'\n'
             '        + fmtPx(LAST.dh) + \' px, la trame même de la toile — sa définition suit celle-ci \'\n'
             '        + \'et ne peut pas la dépasser.</span>\'',
       '\'<span class="mono">\' + dzT("cartes.face.vec_redessinee", { w: fmtPx(LAST.dw), h: fmtPx(LAST.dh) }) + \'</span>\'',
       {"vec_redessinee": ("face vectorielle : redessinée à {w} × {h} px, la trame même de la toile — sa définition suit celle-ci et ne peut pas la dépasser.",
                           "vector face: redrawn at {w} × {h} px, the canvas's own raster — its resolution follows the canvas and cannot exceed it.")}),
    SS(2948, '\'<span class="cf-face-need">Aucune source à agrandir ici : c\\\'est la \'\n'
             '          + \'<b>toile</b> qui est à \' + g.dpi + \' DPI.</span>\'',
       '\'<span class="cf-face-need">\' + dzT("cartes.face.toile_basse", { dpi: g.dpi }) + \'</span>\'',
       {"toile_basse": ("Aucune source à agrandir ici : c'est la <b>toile</b> qui est à {dpi} DPI.",
                        "No source to enlarge here: it is the <b>canvas</b> that is at {dpi} DPI.")}),
    SS(2951, '\'<span class="mono">Toile \' + g.canvas_px[0] + \' × \' + g.canvas_px[1]\n'
             '          + \' px pour \' + fmt1(g.px2mm(g.canvas_px[0])) + \' × \' + fmt1(g.px2mm(g.canvas_px[1]))\n'
             '          + \' mm, soit \' + Math.round(rast) + \' DPI · définitions offertes : \'\n'
             '          + (CF.DPIS || []).join(" / ") + \' DPI</span>\'',
       '\'<span class="mono">\' + dzT("cartes.face.toile_detail", { w: g.canvas_px[0], h: g.canvas_px[1], wmm: fmt1(g.px2mm(g.canvas_px[0])), hmm: fmt1(g.px2mm(g.canvas_px[1])), dpi: Math.round(rast), offres: (CF.DPIS || []).join(" / ") }) + \'</span>\'',
       {"toile_detail": ("Toile {w} × {h} px pour {wmm} × {hmm} mm, soit {dpi} DPI · définitions offertes : {offres} DPI",
                         "Canvas {w} × {h} px for {wmm} × {hmm} mm, i.e. {dpi} DPI · available resolutions: {offres} DPI")}),
    SS(2955, '\'<span class="mono">Barre : échelle 0 – \' + (2 * DPI_TARGET) + \' DPI, repère à \'\n'
             '          + DPI_TARGET + \' (mi-barre) · remplissage \' + fmt1(pctv) + \' %</span>\'',
       '\'<span class="mono">\' + dzT("cartes.face.barre", { max: (2 * DPI_TARGET), cible: DPI_TARGET, p: fmt1(pctv) }) + \'</span>\'',
       {"barre": ("Barre : échelle 0 – {max} DPI, repère à {cible} (mi-barre) · remplissage {p} %",
                  "Bar: scale 0 – {max} DPI, mark at {cible} (mid-bar) · fill {p} %")}),
    SS(2965, '\'<b>Avant d\\\'imprimer</b><span>Cette face sortira à \'\n'
             '            + Math.round(rast) + \' DPI, parce que la toile est à \' + g.dpi + \' DPI. \'\n'
             '            + \'Le réglage n\\\'est pas dans ce panneau : la définition se choisit dans la \'\n'
             '            + \'barre de format, en haut (\' + (CF.DPIS || []).join(" / ")\n'
             '            + \' DPI).</span>\'',
       '\'<b>\' + dzT("cartes.face.avant_imprimer") + \'</b><span>\' + dzT("cartes.face.avertir_vec", { dpi: Math.round(rast), toile: g.dpi, offres: (CF.DPIS || []).join(" / ") }) + \'</span>\'',
       {"avant_imprimer": ("Avant d'imprimer", "Before printing"),
        "avertir_vec": ("Cette face sortira à {dpi} DPI, parce que la toile est à {toile} DPI. Le réglage n'est pas dans ce panneau : la définition se choisit dans la barre de format, en haut ({offres} DPI).",
                        "This face will print at {dpi} DPI because the canvas is at {toile} DPI. The setting is not in this panel: choose the resolution in the format bar at the top ({offres} DPI).")}),
    SS(2986, '"Définition suffisante pour l\\\'impression" : "Définition insuffisante — sous " + DPI_TARGET + " DPI"',
       'dzT("cartes.face.def_ok") : dzT("cartes.face.def_basse", { cible: DPI_TARGET })',
       {"def_ok": ("Définition suffisante pour l'impression", "Resolution sufficient for print"),
        "def_basse": ("Définition insuffisante — sous {cible} DPI", "Resolution too low — under {cible} DPI")}),
    SS(2989, '\'<span class="mono">source \' + LAST.sw + \' × \' + LAST.sh + \' px\'\n'
             '      + \' · posée \' + fmtPx(LAST.dw) + \' × \' + fmtPx(LAST.dh) + \' px</span>\'',
       '\'<span class="mono">\' + dzT("cartes.face.source_posee", { sw: LAST.sw, sh: LAST.sh, dw: fmtPx(LAST.dw), dh: fmtPx(LAST.dh) }) + \'</span>\'',
       {"source_posee": ("source {sw} × {sh} px · posée {dw} × {dh} px", "source {sw} × {sh} px · placed {dw} × {dh} px")}),
    SS(2992, '\'<span class="cf-face-need">Il faudrait une source de <b>\'\n'
             '        + LAST.need + \' × \' + LAST.needH + \' px</b> à cette taille de pose.</span>\'',
       '\'<span class="cf-face-need">\' + dzT("cartes.face.il_faudrait", { w: LAST.need, h: LAST.needH }) + \'</span>\'',
       {"il_faudrait": ("Il faudrait une source de <b>{w} × {h} px</b> à cette taille de pose.",
                        "You would need a <b>{w} × {h} px</b> source at this placement size.")}),
    SS(3002, '\'<span class="mono">Toile \' + g.canvas_px[0] + \' × \' + g.canvas_px[1] + \' px à \'\n'
             '        + g.dpi + \' DPI · DPI effectif = plus petit de ( \'',
       '\'<span class="mono">\' + dzT("cartes.face.formule_debut", { w: g.canvas_px[0], h: g.canvas_px[1], dpi: g.dpi }) + \' ( \'',
       {"formule_debut": ("Toile {w} × {h} px à {dpi} DPI · DPI effectif = plus petit de",
                          "Canvas {w} × {h} px at {dpi} DPI · effective DPI = smaller of")}),
    SS(3009, '\' DPI</b>, arrondi à \' + Math.round(LAST.eff) + \' — le nombre de la jauge</span>\'',
       '\' DPI</b>\' + dzT("cartes.face.formule_fin", { n: Math.round(LAST.eff) }) + \'</span>\'',
       {"formule_fin": (", arrondi à {n} — le nombre de la jauge", ", rounded to {n} — the gauge's number")}),
    SS(3010, '\'<span class="mono">Barre : échelle 0 – \' + (2 * DPI_TARGET) + \' DPI, repère à \'\n'
             '        + DPI_TARGET + \' (mi-barre) · remplissage \' + fmt1(pct) + \' %</span>\'',
       '\'<span class="mono">\' + dzT("cartes.face.barre", { max: (2 * DPI_TARGET), cible: DPI_TARGET, p: fmt1(pct) }) + \'</span>\'',
       {"barre": ("Barre : échelle 0 – {max} DPI, repère à {cible} (mi-barre) · remplissage {p} %",
                  "Bar: scale 0 – {max} DPI, mark at {cible} (mid-bar) · fill {p} %")}),
    SS(3020, '\'<b>Avant d\\\'imprimer</b><span>L\\\'illustration sortira à \'\n'
             '          + Math.round(LAST.eff) + \' DPI, pour \' + DPI_TARGET + \' DPI d\\\'impression. \'\n'
             '          + \'Deux réglages la ramènent à \' + DPI_TARGET + \' :</span>\'\n'
             '          + \'<div class="btn-row"><button class="btn sm" type="button" data-fix="shrink">Réduire à 300 DPI exactement</button>\'\n'
             '          + \'<button class="btn sm" type="button" data-fix="contain">Passer en « Contenir »</button></div>\'',
       '\'<b>\' + dzT("cartes.face.avant_imprimer") + \'</b><span>\' + dzT("cartes.face.avertir_bitmap", { dpi: Math.round(LAST.eff), cible: DPI_TARGET }) + \'</span>\'\n'
       '          + \'<div class="btn-row"><button class="btn sm" type="button" data-fix="shrink">\' + dzT("cartes.face.reduire_300") + \'</button>\'\n'
       '          + \'<button class="btn sm" type="button" data-fix="contain">\' + dzT("cartes.face.passer_contenir") + \'</button></div>\'',
       {"avant_imprimer": ("Avant d'imprimer", "Before printing"),
        "avertir_bitmap": ("L'illustration sortira à {dpi} DPI, pour {cible} DPI d'impression. Deux réglages la ramènent à {cible} :",
                           "The illustration will print at {dpi} DPI, for {cible} DPI printing. Two settings bring it back to {cible}:"),
        "reduire_300": ("Réduire à 300 DPI exactement", "Shrink to exactly 300 DPI"),
        "passer_contenir": ("Passer en « Contenir »", "Switch to “Contain”")}),
    SS(3037, '"posée à " + DPI_TARGET + " DPI exactement"', 'dzT("cartes.face.posee_a", { cible: DPI_TARGET })',
       {"posee_a": ("posée à {cible} DPI exactement", "placed at exactly {cible} DPI")}),
    LL(3054, '"pose recadrée sur la fenêtre d\'illustration"', "pose_recadree",
       "pose recadrée sur la fenêtre d'illustration", "image refitted to the art window"),
    SS(3116, 'c.label + " — série « " + serieLabel() + " », image peinte"',
       'dzT("cartes.face.tuile_serie", { label: tuileLib(c), serie: serieLabel() })',
       {"tuile_serie": ("{label} — série « {serie} », image peinte", "{label} — “{serie}” series, painted image")}),
    SS(3122, 'c.label + " · palette " + (PAL_BY[c.palette] || {}).label\n'
             '            + " — vectoriel, redessiné à la taille de la pose"',
       'dzT("cartes.face.tuile_vec", { label: tuileLib(c), pal: libF((PAL_BY[c.palette] || {}).label) })',
       {"tuile_vec": ("{label} · palette {pal} — vectoriel, redessiné à la taille de la pose",
                      "{label} · palette {pal} — vector, redrawn at the placement size")}),
]

ENTREES += [
    # ── grille du catalogue, preuve, pile ──
    LL(3136, '"vectoriel"', "retombee", "vectoriel", "vector"),
    LL(3152, '"Compteur réseau indisponible sur ce moteur."', "net_na", "Compteur réseau indisponible sur ce moteur.",
       "Network counter unavailable in this engine."),
    SS(3162, '\'<b>Mesuré à l\\\'instant</b> : \' + rows.length + \' vignettes peintes en \'\n'
             '        + Math.round(t1 - t0) + \' ms — <b>\' + imgs.length + \' image téléchargée</b>. \'\n'
             '        + \'<span class="mono">performance.getEntriesByType("resource")</span> : \'\n'
             '        + net0 + \' entrées avant, \' + all.length + \' après\'',
       'dzT("cartes.face.net_ligne", { n: rows.length, ms: Math.round(t1 - t0), img: imgs.length }) + \' \'\n'
       '        + \'<span class="mono">performance.getEntriesByType("resource")</span>\'\n'
       '        + dzT("cartes.face.net_entrees", { avant: net0, apres: all.length })',
       {"net_ligne": ("<b>Mesuré à l'instant</b> : {n} vignettes peintes en {ms} ms — <b>{img} image téléchargée</b>.",
                      "<b>Measured just now</b>: {n} thumbnails painted in {ms} ms — <b>{img} image downloaded</b>."),
        "net_entrees": (" : {avant} entrées avant, {apres} après", ": {avant} entries before, {apres} after")}),
    LL(3208, '"mesure en cours…"', "mesure_en_cours", "mesure en cours…", "measuring…"),
    SS(3274, '\'<b>Recompté sur les octets rendus</b>, \' + ms + \' ms. \'\n'
             '          + \'(a) les \' + DRAWINGS + \' dessins peints dans la <b>même</b> palette (\' + esc(PAL_BY[REF].label)\n'
             '          + \', \' + W + \'×\' + H + \' px) donnent <b>\' + hset.size + \' / \' + DRAWINGS\n'
             '          + \' empreintes distinctes</b>. \'\n'
             '          + \'Paire la plus <b>proche</b> : « \' + esc(names[bi]) + \' » et « \' + esc(names[bj])\n'
             '          + \' » — <b>\' + pctDiff.toFixed(1) + \' % des \' + (W * H) + \' pixels</b> diffèrent, \'\n'
             '          + \'de <b>\' + Math.round(moyDiff) + \' niveaux</b> en moyenne sur ceux-là (maximum \'\n'
             '          + mxd + \'), soit \' + (Math.round(best * 10) / 10) + \' niveau(x)/canal ramené à \'\n'
             '          + \'la vignette entière — fond commun compris. \'\n'
             '          + \'(b) les \' + n2 + \' combinaisons (\' + w2 + \'×\' + h2 + \' px) donnent <b>\'\n'
             '          + hset2.size + \' / \' + COMBINATIONS + \' empreintes distinctes</b>. \'\n'
             '          + \'<span class="mono">FNV-1a 32 bits sur getImageData, canaux R/V/B</span>.\'',
       'dzT("cartes.face.preuve_a", { ms: ms, n: DRAWINGS, pal: esc(PAL_BY[REF].label), w: W, h: H, d: hset.size }) + \' \'\n'
       '          + dzT("cartes.face.preuve_paire", { a: esc(names[bi]), b: esc(names[bj]), pct: pctDiff.toFixed(1), px: (W * H), moy: Math.round(moyDiff), max: mxd, best: (Math.round(best * 10) / 10) }) + \' \'\n'
       '          + dzT("cartes.face.preuve_b", { n: n2, w: w2, h: h2, d: hset2.size, total: COMBINATIONS }) + \' \'\n'
       '          + \'<span class="mono">\' + dzT("cartes.face.preuve_hash") + \'</span>.\'',
       {"preuve_a": ("<b>Recompté sur les octets rendus</b>, {ms} ms. (a) les {n} dessins peints dans la <b>même</b> palette ({pal}, {w}×{h} px) donnent <b>{d} / {n} empreintes distinctes</b>.",
                     "<b>Recounted on the rendered bytes</b>, {ms} ms. (a) the {n} drawings painted in the <b>same</b> palette ({pal}, {w}×{h} px) give <b>{d} / {n} distinct fingerprints</b>."),
        "preuve_paire": ("Paire la plus <b>proche</b> : « {a} » et « {b} » — <b>{pct} % des {px} pixels</b> diffèrent, de <b>{moy} niveaux</b> en moyenne sur ceux-là (maximum {max}), soit {best} niveau(x)/canal ramené à la vignette entière — fond commun compris.",
                         "<b>Closest</b> pair: “{a}” and “{b}” — <b>{pct} % of the {px} pixels</b> differ, by <b>{moy} levels</b> on average over those (maximum {max}), i.e. {best} level(s)/channel over the whole thumbnail — shared background included."),
        "preuve_b": ("(b) les {n} combinaisons ({w}×{h} px) donnent <b>{d} / {total} empreintes distinctes</b>.",
                     "(b) the {n} combinations ({w}×{h} px) give <b>{d} / {total} distinct fingerprints</b>."),
        "preuve_hash": ("FNV-1a 32 bits sur getImageData, canaux R/V/B", "32-bit FNV-1a on getImageData, R/G/B channels")}),
    LL(3292, '"la mesure a échoué : "', "mesure_echec", "la mesure a échoué : ", "the measurement failed: "),
    SS(3304, '\'<p class="empty-note sm">La pile est vide. Déposez plusieurs fichiers d\\\'un coup, \'\n'
             '        + \'collez une image (Ctrl+V) ou piochez dans le catalogue — \' + DRAWINGS\n'
             '        + \' dessins vectoriels vous attendent.</p>\'',
       '\'<p class="empty-note sm">\' + dzT("cartes.face.pile_vide", { n: DRAWINGS }) + \'</p>\'',
       {"pile_vide": ("La pile est vide. Déposez plusieurs fichiers d'un coup, collez une image (Ctrl+V) ou piochez dans le catalogue — {n} dessins vectoriels vous attendent.",
                      "The stack is empty. Drop several files at once, paste an image (Ctrl+V) or pick from the catalog — {n} vector drawings are waiting.")}),
    SS(3341, '\'" title="Retirer de la pile" aria-label="Retirer de la pile">\'',
       '\'" title="\' + dzT("cartes.face.retirer_pile") + \'" aria-label="\' + dzT("cartes.face.retirer_pile") + \'">\'',
       {"retirer_pile": ("Retirer de la pile", "Remove from the stack")}),
    SS(3351, '\'<div class="lbl">Dernière génération</div>',
       '\'<div class="lbl">\' + dzT("cartes.face.derniere_gen") + \'</div>',
       {"derniere_gen": ("Dernière génération", "Latest generation")}),

    # ── le panneau complet ──
    SS(3374, '\'" type="button" data-tab="cat">Catalogue \'',
       '\'" type="button" data-tab="cat">\' + dzT("cartes.face.onglet_cat") + \' \'',
       {"onglet_cat": ("Catalogue", "Catalog")}),
    SS(3375, '\'" type="button" data-tab="imp">Importées \'',
       '\'" type="button" data-tab="imp">\' + dzT("cartes.face.onglet_imp") + \' \'',
       {"onglet_imp": ("Importées", "Imported")}),
    SS(3376, '\'" type="button" data-tab="ai">Générer par IA</button>\'',
       '\'" type="button" data-tab="ai">\' + dzT("cartes.face.onglet_ai") + \'</button>\'',
       {"onglet_ai": ("Générer par IA", "Generate with AI")}),
    SS(3377, '\'" type="button" data-tab="vec" title="Documents vectoriels du jeu (Vectorlab)">',
       '\'" type="button" data-tab="vec" title="\' + dzT("cartes.face.onglet_vec_t") + \'">',
       {"onglet_vec_t": ("Documents vectoriels du jeu (Vectorlab)", "The deck's vector documents (Vectorlab)")}),
    SS(3402, 'placeholder="filtrer (loup, blason, braise…)"',
       'placeholder="\' + dzT("cartes.face.filtre_ph") + \'"',
       {"filtre_ph": ("filtrer (loup, blason, braise…)", "filter (wolf, heraldry, ember…)")}),
    SS(3403, 'title="filtrer par sujet">',
       'title="\' + dzT("cartes.face.filtre_sujet_t") + \'">',
       {"filtre_sujet_t": ("filtrer par sujet", "filter by subject")}),
    SS(3404, '\'<option value="">tous les sujets (\' + SUBJECTS.length + \')</option>\'',
       '\'<option value="">\' + dzT("cartes.face.tous_sujets", { n: SUBJECTS.length }) + \'</option>\'',
       {"tous_sujets": ("tous les sujets ({n})", "all subjects ({n})")}),
    SS(3408, 'id="cf-face-rand">Au hasard</button>\'',
       'id="cf-face-rand">\' + dzT("cartes.face.au_hasard") + \'</button>\'',
       {"au_hasard": ("Au hasard", "Random")}),
    SS(3411, 'data-compo="">toutes compositions</button>\'',
       'data-compo="">\' + dzT("cartes.face.toutes_compos") + \'</button>\'',
       {"toutes_compos": ("toutes compositions", "all compositions")}),
    SS(3428, '\'<p class="hint cf-face-count">\' + SUBJECTS.length + \' sujets × \' + COMPOS.length\n'
             '      + \' compositions = <b>\' + DRAWINGS + \' dessins</b>. Chacun se recolore en \'\n'
             '      + PALETTES.length + \' palettes : <b>\' + COMBINATIONS + \' combinaisons</b> en tout.</p>\'',
       '\'<p class="hint cf-face-count">\' + dzT("cartes.face.compte_cat", { s: SUBJECTS.length, c: COMPOS.length, d: DRAWINGS, p: PALETTES.length, t: COMBINATIONS }) + \'</p>\'',
       {"compte_cat": ("{s} sujets × {c} compositions = <b>{d} dessins</b>. Chacun se recolore en {p} palettes : <b>{t} combinaisons</b> en tout.",
                       "{s} subjects × {c} compositions = <b>{d} drawings</b>. Each can be recolored in {p} palettes: <b>{t} combinations</b> in all.")}),
    SS(3435, '\'<p class="hint cf-face-serie-note" id="cf-face-serie-note">Série <b>\'\n'
             '        + esc(serieLabel()) + \'</b> : <b>\' + SERIE.faites + \'</b> case(s) peinte(s) sur \'\n'
             '        + (SERIE.total || DRAWINGS) + \'. Les autres restent le <b>dessin vectoriel</b>, \'\n'
             '        + \'marqué comme tel sur la vignette\'\n'
             '        + (SERIE.ok ? \'\' : \' — l\\\'état de la série n\\\'a pas pu être lu\')',
       '\'<p class="hint cf-face-serie-note" id="cf-face-serie-note">\' + dzT("cartes.face.serie_note", { serie: esc(serieLabel()), f: SERIE.faites, t: (SERIE.total || DRAWINGS) })\n'
       '        + (SERIE.ok ? \'\' : dzT("cartes.face.serie_illisible"))',
       {"serie_note": ("Série <b>{serie}</b> : <b>{f}</b> case(s) peinte(s) sur {t}. Les autres restent le <b>dessin vectoriel</b>, marqué comme tel sur la vignette",
                       "<b>{serie}</b> series: <b>{f}</b> cell(s) painted out of {t}. The others remain the <b>vector drawing</b>, marked as such on the thumbnail"),
        "serie_illisible": (" — l'état de la série n'a pas pu être lu", " — the series status could not be read")}),
    SS(3446, '\'. Dépense de la série : <b>\' + esc(usdFmt(SERIE.depense))\n'
             '          + \'</b> sur une <b>enveloppe totale</b> de <b>\' + esc(usdFmt(SERIE.plafond))\n'
             '          + \'</b> — elle est CUMULATIVE : chaque campagne reprend le total déjà dépensé, elle ne repart jamais de zéro\'',
       'dzT("cartes.face.serie_depense", { d: esc(usdFmt(SERIE.depense)), p: esc(usdFmt(SERIE.plafond)) })',
       {"serie_depense": (". Dépense de la série : <b>{d}</b> sur une <b>enveloppe totale</b> de <b>{p}</b> — elle est CUMULATIVE : chaque campagne reprend le total déjà dépensé, elle ne repart jamais de zéro",
                          ". Series spending: <b>{d}</b> of a <b>total budget</b> of <b>{p}</b> — it is CUMULATIVE: each campaign carries over the total already spent, it never restarts from zero")}),
    SS(3452, 'id="cf-face-proof">Recompter le catalogue</button>\'',
       'id="cf-face-proof">\' + dzT("cartes.face.recompter") + \'</button>\'',
       {"recompter": ("Recompter le catalogue", "Recount the catalog")}),
    SS(3461, '\'<b>Glissez vos illustrations ici</b>\'',
       '\'<b>\' + dzT("cartes.face.glissez") + \'</b>\'',
       {"glissez": ("Glissez vos illustrations ici", "Drag your illustrations here")}),
    SS(3462, '\'<span class="hint">…ou cliquez pour choisir — <b>plusieurs fichiers d\\\'un coup</b> — ou collez avec <b>Ctrl+V</b>. \'\n'
             '      + \'Chaque image rejoint la pile avec sa taille en pixels et le DPI qu\\\'elle donnerait \'\n'
             '      + \'sur cette carte, écrits sous sa vignette. Au-delà de \' + MAX_IMPORT_PX\n'
             '      + \' px de côté, elle est ramenée à \' + MAX_IMPORT_PX + \' px et la vignette le dit.</span>\'',
       '\'<span class="hint">\' + dzT("cartes.face.drop_aide", { max: MAX_IMPORT_PX }) + \'</span>\'',
       {"drop_aide": ("…ou cliquez pour choisir — <b>plusieurs fichiers d'un coup</b> — ou collez avec <b>Ctrl+V</b>. Chaque image rejoint la pile avec sa taille en pixels et le DPI qu'elle donnerait sur cette carte, écrits sous sa vignette. Au-delà de {max} px de côté, elle est ramenée à {max} px et la vignette le dit.",
                      "…or click to choose — <b>several files at once</b> — or paste with <b>Ctrl+V</b>. Each image joins the stack with its pixel size and the DPI it would give on this card, written under its thumbnail. Beyond {max} px per side, it is scaled down to {max} px and the thumbnail says so.")}),
    XX(3466, '\'<input type="file" id="cf-face-file" accept="image/*" multiple hidden>\'', "balisage sans texte (accept = type MIME)"),
    SS(3468, '\'<p class="hint cf-face-nodb">Le stockage local du navigateur est indisponible : la pile ne survivra pas au rechargement.</p>\'',
       '\'<p class="hint cf-face-nodb">\' + dzT("cartes.face.nodb") + \'</p>\'',
       {"nodb": ("Le stockage local du navigateur est indisponible : la pile ne survivra pas au rechargement.",
                 "The browser's local storage is unavailable: the stack will not survive a reload.")}),
    SS(3474, '\'Mire de contrôle \' + MIRE_W + \' × \' + MIRE_H + \' px</button></div>\'',
       'dzT("cartes.face.mire_btn", { w: MIRE_W, h: MIRE_H }) + \'</button></div>\'',
       {"mire_btn": ("Mire de contrôle {w} × {h} px", "Test pattern {w} × {h} px")}),
    SS(3475, '\'<p class="hint">Un damier dessiné à la demande, rangé dans la pile comme une image \'\n'
             '      + \'déposée : posez-le pour caler le cadrage et la fenêtre d\\\'illustration, retirez-le \'\n'
             '      + \'d\\\'un clic. Sa vignette porte sa taille et son DPI comme les autres.</p>\'',
       '\'<p class="hint">\' + dzT("cartes.face.mire_aide") + \'</p>\'',
       {"mire_aide": ("Un damier dessiné à la demande, rangé dans la pile comme une image déposée : posez-le pour caler le cadrage et la fenêtre d'illustration, retirez-le d'un clic. Sa vignette porte sa taille et son DPI comme les autres.",
                      "A checkerboard drawn on demand, stored in the stack like a dropped image: place it to line up the framing and the art window, remove it with one click. Its thumbnail shows its size and DPI like the others.")}),
    SS(3486, '\'La pièce Import a isolé un sujet sur la carte reprise : il entre \'\n'
             '              + \'dans la pile comme une image déposée, et se pose aussitôt.\'',
       'dzT("cartes.face.adopt_sujet_aide")',
       {"adopt_sujet_aide": ("La pièce Import a isolé un sujet sur la carte reprise : il entre dans la pile comme une image déposée, et se pose aussitôt.",
                             "The Import panel isolated a subject on the captured card: it enters the stack like a dropped image and is placed right away.")}),
    SS(3488, '\'Aucun sujet détouré pour l\\\'instant — c\\\'est le RECTO ENTIER qui \'\n'
             '              + \'entrera dans la pile, à recadrer ensuite avec la fenêtre \'\n'
             '              + \'d\\\'illustration. Pour n\\\'adopter que le sujet, détourez-le \'\n'
             '              + \'d\\\'abord depuis la pièce Import.\'',
       'dzT("cartes.face.adopt_recto_aide")',
       {"adopt_recto_aide": ("Aucun sujet détouré pour l'instant — c'est le RECTO ENTIER qui entrera dans la pile, à recadrer ensuite avec la fenêtre d'illustration. Pour n'adopter que le sujet, détourez-le d'abord depuis la pièce Import.",
                             "No cut-out subject yet — the WHOLE FRONT will enter the stack, to be cropped afterwards with the art window. To adopt only the subject, cut it out first from the Import panel.")}),
    SS(3498, '<span class="lbl">Amorces d\\\'invite — cadrage de carte</span>\'',
       '<span class="lbl">\' + dzT("cartes.face.amorces") + \'</span>\'',
       {"amorces": ("Amorces d'invite — cadrage de carte", "Prompt starters — card framing")}),
    SS(3502, '<span class="lbl">Invite</span>\'',
       '<span class="lbl">\' + dzT("cartes.face.invite") + \'</span>\'',
       {"invite": ("Invite", "Prompt")}),
    SS(3503, '\'<textarea id="cf-face-prompt" placeholder="décrivez la face de la carte…">\'',
       '\'<textarea id="cf-face-prompt" placeholder="\' + dzT("cartes.face.prompt_ph") + \'">\'',
       {"prompt_ph": ("décrivez la face de la carte…", "describe the card face…")}),
    SS(3505, '<span class="lbl">Modèle</span>',
       '<span class="lbl">\' + dzT("cartes.face.modele") + \'</span>',
       {"modele": ("Modèle", "Model")}),
    SS(3506, '<span class="lbl">Cadrage</span>',
       '<span class="lbl">\' + dzT("cartes.face.cadrage") + \'</span>',
       {"cadrage": ("Cadrage", "Framing")}),
    SS(3509, '<span class="lbl">Nombre</span>',
       '<span class="lbl">\' + dzT("cartes.face.nombre") + \'</span>',
       {"nombre": ("Nombre", "Count")}),
    SS(3510, '<span class="lbl">Graine (vide = aléatoire)</span>',
       '<span class="lbl">\' + dzT("cartes.face.graine") + \'</span>',
       {"graine": ("Graine (vide = aléatoire)", "Seed (empty = random)")}),
    SS(3513, '\'Générer et poser sur la carte</button>\'',
       'dzT("cartes.face.generer") + \'</button>\'',
       {"generer": ("Générer et poser sur la carte", "Generate and place on the card")}),
    SS(3520, '\'<input class="search sm" id="cf-face-vlab-nom" type="text" placeholder="nom du nouveau document">\'',
       '\'<input class="search sm" id="cf-face-vlab-nom" type="text" placeholder="\' + dzT("cartes.face.vec_nom_ph") + \'">\'',
       {"vec_nom_ph": ("nom du nouveau document", "new document name")}),
    SS(3521, 'title="Crée un document ancré à ce jeu (taille = fenêtre d\\\'illustration) et l\\\'ouvre dans le Vectorlab">+ Nouveau</button>\'',
       'title="\' + dzT("cartes.face.vec_new_t") + \'">\' + dzT("cartes.face.vec_new") + \'</button>\'',
       {"vec_new_t": ("Crée un document ancré à ce jeu (taille = fenêtre d'illustration) et l'ouvre dans le Vectorlab",
                      "Creates a document anchored to this deck (size = art window) and opens it in the Vectorlab"),
        "vec_new": ("+ Nouveau", "+ New")}),
    SS(3522, 'title="Relit la liste (versions, vignettes, exports)">Rafraîchir</button>\'',
       'title="\' + dzT("cartes.face.vec_refresh_t") + \'">\' + dzT("cartes.face.rafraichir") + \'</button>\'',
       {"vec_refresh_t": ("Relit la liste (versions, vignettes, exports)", "Reloads the list (versions, thumbnails, exports)"),
        "rafraichir": ("Rafraîchir", "Refresh")}),
    SS(3523, 'title="Rend la face courante (le moteur, fond perdu compris), crée un document Vectorlab au format physique du jeu avec les repères de coupe et de zone sûre, la face en calque image verrouillé, et l\\\'ouvre — « Poser 2× » ramène le résultat">Éditer cette face dans le Vectorlab</button>\'',
       'title="\' + dzT("cartes.face.vec_edit_t") + \'">\' + dzT("cartes.face.vec_edit") + \'</button>\'',
       {"vec_edit_t": ("Rend la face courante (le moteur, fond perdu compris), crée un document Vectorlab au format physique du jeu avec les repères de coupe et de zone sûre, la face en calque image verrouillé, et l'ouvre — « Poser 2× » ramène le résultat",
                       "Renders the current face (the engine, bleed included), creates a Vectorlab document at the deck's physical size with trim and safe-area guides, the face as a locked image layer, and opens it — “Place 2×” brings the result back"),
        "vec_edit": ("Éditer cette face dans le Vectorlab", "Edit this face in the Vectorlab")}),
    SS(3526, '\'<p class="hint">Un document s\\\'édite dans le <b>Vectorlab</b> (nouvel onglet). « Poser 2× » pose son export PNG \'\n'
             '      + \'(menu Exporter → PNG 2× du Vectorlab) comme illustration de la carte ; rééditer puis ré-exporter met la carte à jour \'\n'
             '      + \'(même fichier, réécrit en place). Le même PNG sert aussi de source img: aux décors de la pièce Cadre.</p>\'',
       '\'<p class="hint">\' + dzT("cartes.face.vec_aide") + \'</p>\'',
       {"vec_aide": ("Un document s'édite dans le <b>Vectorlab</b> (nouvel onglet). « Poser 2× » pose son export PNG (menu Exporter → PNG 2× du Vectorlab) comme illustration de la carte ; rééditer puis ré-exporter met la carte à jour (même fichier, réécrit en place). Le même PNG sert aussi de source img: aux décors de la pièce Cadre.",
                     "A document is edited in the <b>Vectorlab</b> (new tab). “Place 2×” places its PNG export (Vectorlab Export menu → PNG 2×) as the card's illustration; re-editing then re-exporting updates the card (same file, rewritten in place). The same PNG also serves as an img: source for the Frame panel's decorations.")}),
    SS(3534, '<span class="lbl">Ajustement</span>\'',
       '<span class="lbl">\' + dzT("cartes.face.ajustement") + \'</span>\'',
       {"ajustement": ("Ajustement", "Fit")}),
    SS(3536, 'data-fit="cover">Couvrir</button>\'',
       'data-fit="cover">\' + dzT("cartes.face.fit_cover") + \'</button>\'',
       {"fit_cover": ("Couvrir", "Cover")}),
    SS(3537, 'data-fit="contain">Contenir</button>\'',
       'data-fit="contain">\' + dzT("cartes.face.fit_contain") + \'</button>\'',
       {"fit_contain": ("Contenir", "Contain")}),
    SS(3538, 'data-fit="free">Libre</button>\'',
       'data-fit="free">\' + dzT("cartes.face.fit_free") + \'</button>\'',
       {"fit_free": ("Libre", "Free", "contexte")}),
    SS(3540, '<span class="lbl">Fenêtre d\\\'illustration</span>\'',
       '<span class="lbl">\' + dzT("cartes.face.fenetre_art") + \'</span>\'',
       {"fenetre_art": ("Fenêtre d'illustration", "Art window")}),
    SS(3548, '\'<label class="fld"><span class="lbl">Échelle</span>',
       '\'<label class="fld"><span class="lbl">\' + dzT("cartes.face.echelle") + \'</span>',
       {"echelle": ("Échelle", "Scale")}),
    SS(3552, '"Hauteur" : "Hauteur = Échelle"',
       'dzT("cartes.face.hauteur") : dzT("cartes.face.hauteur_echelle")',
       {"hauteur": ("Hauteur", "Height"), "hauteur_echelle": ("Hauteur = Échelle", "Height = Scale")}),
    SS(3555, '\' disabled title="verrou de proportions actif : la hauteur recopie l\\\'échelle"\'',
       '\' disabled title="\' + dzT("cartes.face.verrou_t") + \'"\'',
       {"verrou_t": ("verrou de proportions actif : la hauteur recopie l'échelle", "aspect lock on: the height copies the scale")}),
    SS(3557, '<span class="lbl">Proportions</span>\'',
       '<span class="lbl">\' + dzT("cartes.face.proportions") + \'</span>\'',
       {"proportions": ("Proportions", "Aspect ratio", "contexte")}),
    SS(3558, '"déverrouillées" : "verrouillées"',
       'dzT("cartes.face.deverrouillees") : dzT("cartes.face.verrouillees")',
       {"deverrouillees": ("déverrouillées", "unlocked"), "verrouillees": ("verrouillées", "locked")}),
    SS(3561, 'id="cf-face-center">Recentrer</button>\'',
       'id="cf-face-center">\' + dzT("cartes.face.recentrer") + \'</button>\'',
       {"recentrer": ("Recentrer", "Recenter")}),
    SS(3563, '\'title="pose en « couvrir » au centre de la fenêtre d\\\'illustration">\'\n'
             '      + \'Recadrer sur la fenêtre</button>\'',
       '\'title="\' + dzT("cartes.face.fitwin_t") + \'">\'\n'
       '      + dzT("cartes.face.recadrer_fenetre") + \'</button>\'',
       {"fitwin_t": ("pose en « couvrir » au centre de la fenêtre d'illustration",
                     "places the image in “cover” mode at the center of the art window"),
        "recadrer_fenetre": ("Recadrer sur la fenêtre", "Fit to the window")}),
    SS(3565, 'id="cf-face-reset">Réinitialiser</button>\'',
       'id="cf-face-reset">\' + dzT("cartes.face.reinitialiser") + \'</button>\'',
       {"reinitialiser": ("Réinitialiser", "Reset")}),
    SS(3566, 'id="cf-face-undo">Annuler</button>\'',
       'id="cf-face-undo">\' + dzT("cartes.face.annuler") + \'</button>\'',
       {"annuler": ("Annuler", "Undo", "contexte")}),
    SS(3567, 'id="cf-face-redo">Rétablir</button>\'',
       'id="cf-face-redo">\' + dzT("cartes.face.retablir") + \'</button>\'',
       {"retablir": ("Rétablir", "Redo")}),
    SS(3568, 'id="cf-face-clear">Retirer</button>\'',
       'id="cf-face-clear">\' + dzT("cartes.face.retirer") + \'</button>\'',
       {"retirer": ("Retirer", "Remove")}),
    SS(3570, '\'<p class="hint cf-face-keys">Sur la carte : <b>glisser</b> = déplacer · <b>molette</b> = zoom sous le curseur · \'\n'
             '      + \'<b>Alt+glisser</b> = rotation · <b>double-clic</b> = recentrer.<br>\'\n'
             '      + \'Au clavier : <b>flèches</b> 1 mm · <b>Maj+flèches</b> 0,1 mm · <b>+ / −</b> zoom · \'\n'
             '      + \'<b>[ ]</b> rotation · <b>0</b> recentrer · <b>F</b> ajustement · <b>Ctrl+Z / Ctrl+Y</b>.</p>\'',
       '\'<p class="hint cf-face-keys">\' + dzT("cartes.face.raccourcis") + \'</p>\'',
       {"raccourcis": ("Sur la carte : <b>glisser</b> = déplacer · <b>molette</b> = zoom sous le curseur · <b>Alt+glisser</b> = rotation · <b>double-clic</b> = recentrer.<br>Au clavier : <b>flèches</b> 1 mm · <b>Maj+flèches</b> 0,1 mm · <b>+ / −</b> zoom · <b>[ ]</b> rotation · <b>0</b> recentrer · <b>F</b> ajustement · <b>Ctrl+Z / Ctrl+Y</b>.",
                       "On the card: <b>drag</b> = move · <b>wheel</b> = zoom under the cursor · <b>Alt+drag</b> = rotate · <b>double-click</b> = recenter.<br>Keyboard: <b>arrows</b> 1 mm · <b>Shift+arrows</b> 0.1 mm · <b>+ / −</b> zoom · <b>[ ]</b> rotate · <b>0</b> recenter · <b>F</b> fit · <b>Ctrl+Z / Ctrl+Y</b>.")}),
    SS(3588, 'id="cf-face-fidbtn">Contrôle de fidélité de l\\\'illustration</button>\'',
       'id="cf-face-fidbtn">\' + dzT("cartes.face.fid_btn") + \'</button>\'',
       {"fid_btn": ("Contrôle de fidélité de l'illustration", "Illustration fidelity check")}),
    SS(3590, '\'Télécharger la face — PNG 1:1 avec sa résolution physique</button>\'',
       'dzT("cartes.face.png_label") + \'</button>\'',
       {"png_label": ("Télécharger la face — PNG 1:1 avec sa résolution physique",
                      "Download the face — 1:1 PNG with its physical resolution")}),
    SS(3591, '\'<p class="hint mono" id="cf-face-pngout">Le fichier emporte sa résolution physique \'\n'
             '      + \'(<b>pHYs</b>), son espace de couleur (<b>sRGB</b>) et le nom de la carte. Sans eux, une \'\n'
             '      + \'mise en page ouvre le PNG à 72 DPI. À \' + g.dpi + \' DPI : \' + physLine(g.dpi)',
       '\'<p class="hint mono" id="cf-face-pngout">\' + dzT("cartes.face.png_aide", { dpi: g.dpi }) + physLine(g.dpi)',
       {"png_aide": ("Le fichier emporte sa résolution physique (<b>pHYs</b>), son espace de couleur (<b>sRGB</b>) et le nom de la carte. Sans eux, une mise en page ouvre le PNG à 72 DPI. À {dpi} DPI : ",
                     "The file carries its physical resolution (<b>pHYs</b>), its color space (<b>sRGB</b>) and the card name. Without them, a layout tool opens the PNG at 72 DPI. At {dpi} DPI: ")}),
    SS(3616, '\'<span class="lbl">Palette — le même dessin, \' + PALETTES.length + \' teintes</span>\'',
       '\'<span class="lbl">\' + dzT("cartes.face.palette_lbl", { n: PALETTES.length }) + \'</span>\'',
       {"palette_lbl": ("Palette — le même dessin, {n} teintes", "Palette — the same drawing, {n} hues")}),

    # ── le fichier livré ──
    LL(3645, '"Télécharger la face — PNG 1:1 avec sa résolution physique"', "png_label",
       "Télécharger la face — PNG 1:1 avec sa résolution physique", "Download the face — 1:1 PNG with its physical resolution"),
    SS(3663, '"Confirmer l\'export à " + Math.round(vu) + " DPI (sous " + DPI_TARGET + ")"',
       'dzT("cartes.face.confirmer_export", { dpi: Math.round(vu), cible: DPI_TARGET })',
       {"confirmer_export": ("Confirmer l'export à {dpi} DPI (sous {cible})", "Confirm export at {dpi} DPI (under {cible})")}),
    SS(3665, '\'<b>Rien n\\\'est parti.</b> L\\\'illustration sortirait à <b>\'\n'
             '          + Math.round(vu) + \' DPI</b>, sous les \' + DPI_TARGET + \' DPI d\\\'impression : \'\n'
             '          + (LAST.vector\n'
             '            ? \'cette face est vectorielle, il n\\\'y a pas de source à agrandir — c\\\'est la \'\n'
             '              + \'<b>toile</b> qui est à \' + g.dpi + \' DPI, et cela se règle dans la barre de format. \'\n'
             '            : \'il faudrait une source de <b>\' + LAST.need + \' x \' + LAST.needH + \' px</b> à cette taille de pose. \')\n'
             '          + \'Cliquez une seconde fois pour exporter quand même.\'',
       'dzT("cartes.face.rien_parti", { dpi: Math.round(vu), cible: DPI_TARGET })\n'
       '          + (LAST.vector\n'
       '            ? dzT("cartes.face.rien_parti_vec", { dpi: g.dpi })\n'
       '            : dzT("cartes.face.rien_parti_bmp", { w: LAST.need, h: LAST.needH }))\n'
       '          + dzT("cartes.face.cliquez_seconde")',
       {"rien_parti": ("<b>Rien n'est parti.</b> L'illustration sortirait à <b>{dpi} DPI</b>, sous les {cible} DPI d'impression : ",
                       "<b>Nothing was sent.</b> The illustration would print at <b>{dpi} DPI</b>, below the {cible} DPI for print: "),
        "rien_parti_vec": ("cette face est vectorielle, il n'y a pas de source à agrandir — c'est la <b>toile</b> qui est à {dpi} DPI, et cela se règle dans la barre de format. ",
                           "this face is vector, there is no source to enlarge — the <b>canvas</b> is at {dpi} DPI, and that is set in the format bar. "),
        "rien_parti_bmp": ("il faudrait une source de <b>{w} x {h} px</b> à cette taille de pose. ",
                           "you would need a <b>{w} x {h} px</b> source at this placement size. "),
        "cliquez_seconde": ("Cliquez une seconde fois pour exporter quand même.", "Click a second time to export anyway.")}),
    SS(3673, '"export sous " + DPI_TARGET + " DPI : confirmez"', 'dzT("cartes.face.export_sous", { cible: DPI_TARGET })',
       {"export_sous": ("export sous {cible} DPI : confirmez", "export under {cible} DPI: confirm")}),
    SS(3678, '"encodage de la carte à " + g.canvas_px[0] + " x " + g.canvas_px[1] + " px…"',
       'dzT("cartes.face.encodage", { w: g.canvas_px[0], h: g.canvas_px[1] })',
       {"encodage": ("encodage de la carte à {w} x {h} px…", "encoding the card at {w} x {h} px…")}),
    LL(3689, '"PNG livré : résolution, espace de couleur et métadonnées dans les octets"', "png_livre",
       "PNG livré : résolution, espace de couleur et métadonnées dans les octets",
       "PNG delivered: resolution, color space and metadata in the bytes"),
    SS(3692, '\'<b>Échec</b> : \' + esc(msg)', 'dzT("cartes.face.echec", { msg: esc(msg) })',
       {"echec": ("<b>Échec</b> : {msg}", "<b>Failed</b>: {msg}")}),
    LL(3693, '"export PNG : "', "err_png", "export PNG : ", "PNG export: "),
    LL(3697, '"gris"', "coul_gris", "gris", "gray"),
    LL(3697, '"RVB"', "coul_rvb", "RVB", "RGB"),
    LL(3697, '"gris+alpha"', "coul_gris_alpha", "gris+alpha", "gray+alpha"),
    LL(3697, '"RVBA"', "coul_rvba", "RVBA", "RGBA"),
    SS(3715, '\' · <b>canal alpha retiré</b> (le serveur a mesuré ses extrema à 255/255 avant de convertir, \'\n'
             '        + \'et vérifié que les trois canaux RVB survivent à l\\\'octet)\'',
       'dzT("cartes.face.alpha_retire")',
       {"alpha_retire": (" · <b>canal alpha retiré</b> (le serveur a mesuré ses extrema à 255/255 avant de convertir, et vérifié que les trois canaux RVB survivent à l'octet)",
                         " · <b>alpha channel removed</b> (the server measured its extrema at 255/255 before converting, and checked that the three RGB channels survive byte for byte)")}),
    LL(3717, '\' · canal alpha <b>conservé</b> : il porte de l\\\'information\'', "alpha_garde",
       " · canal alpha <b>conservé</b> : il porte de l'information", " · alpha channel <b>kept</b>: it carries information"),
    LL(3718, '\'<b>Fichier téléchargé.</b> En-tête relu dans les octets rendus :\'', "fichier_dl",
       "<b>Fichier téléchargé.</b> En-tête relu dans les octets rendus :",
       "<b>File downloaded.</b> Header read back from the rendered bytes:"),
    SS(3721, '\'<br><b>\' + a.w + \' x \' + a.h + \' px</b>, \' + a.depth\n'
             '      + \' bits par canal (IHDR, octet 9), type \' + a.color\n'
             '      + \' = <b>\' + (COLOR_NAME[a.color] || "?") + \'</b>\'',
       '\'<br>\' + dzT("cartes.face.ihdr", { w: a.w, h: a.h, d: a.depth, t: a.color, nom: (COLOR_NAME[a.color] || "?") })',
       {"ihdr": ("<b>{w} x {h} px</b>, {d} bits par canal (IHDR, octet 9), type {t} = <b>{nom}</b>",
                 "<b>{w} x {h} px</b>, {d} bits per channel (IHDR, byte 9), type {t} = <b>{nom}</b>")}),
    SS(3724, '\' · <b>pHYs</b> \' + a.phys.x + \' x \' + a.phys.y + \' px/m (unité \' + a.phys.unit\n'
             '        + \' = mètre) = <b>\' + (a.phys.x * 0.0254).toFixed(4) + \' DPI</b>\'\n'
             '        : \' · <b>aucun pHYs</b> — le fichier n\\\'annonce aucune résolution physique\'',
       'dzT("cartes.face.phys_relu", { x: a.phys.x, y: a.phys.y, u: a.phys.unit, dpi: (a.phys.x * 0.0254).toFixed(4) })\n'
       '        : dzT("cartes.face.phys_aucun")',
       {"phys_relu": (" · <b>pHYs</b> {x} x {y} px/m (unité {u} = mètre) = <b>{dpi} DPI</b>",
                      " · <b>pHYs</b> {x} x {y} px/m (unit {u} = metre) = <b>{dpi} DPI</b>"),
        "phys_aucun": (" · <b>aucun pHYs</b> — le fichier n'annonce aucune résolution physique",
                       " · <b>no pHYs</b> — the file declares no physical resolution")}),
    LL(3727, '\' · <b>aucun espace de couleur</b>\'', "srgb_aucun", " · <b>aucun espace de couleur</b>",
       " · <b>no color space</b>"),
    LL(3728, '\' · <b>sRGB</b> intention \'', "srgb_intention", " · <b>sRGB</b> intention ", " · <b>sRGB</b> intent "),
    SS(3731, '\'<br><span class="mono">chunks : \'', '\'<br><span class="mono">\' + dzT("cartes.face.chunks")',
       {"chunks": ("chunks : ", "chunks: ")}),
    LL(3732, '\'<br>métadonnées relues : \'', "meta_relues", "<br>métadonnées relues : ", "<br>metadata read back: "),
    LL(3734, '\'<b>aucune</b>\'', "aucune_b", "<b>aucune</b>", "<b>none</b>"),
    SS(3735, '\'<br>Avant écriture de l\\\'en-tête : \' + nRaw.toLocaleString("fr-FR")\n'
             '      + \' octets, type \' + b.color + \' (\' + (COLOR_NAME[b.color] || "?") + \'), chunks \'\n'
             '      + esc(runs(b.chunks)) + \'. Après : \' + nOut.toLocaleString("fr-FR") + \' octets (\'\n'
             '      + (nOut <= nRaw ? \'−\' : \'+\') + Math.abs(Math.round(100 - nOut * 100 / nRaw)) + \' %).\'',
       '\'<br>\' + dzT("cartes.face.avant_apres", { n: nRaw.toLocaleString("fr-FR"), t: b.color, nom: (COLOR_NAME[b.color] || "?"), ch: esc(runs(b.chunks)), m: nOut.toLocaleString("fr-FR"), s: (nOut <= nRaw ? \'−\' : \'+\'), p: Math.abs(Math.round(100 - nOut * 100 / nRaw)) })',
       {"avant_apres": ("Avant écriture de l'en-tête : {n} octets, type {t} ({nom}), chunks {ch}. Après : {m} octets ({s}{p} %).",
                        "Before writing the header: {n} bytes, type {t} ({nom}), chunks {ch}. After: {m} bytes ({s}{p} %).")}),

    # ── le contrôle de fidélité ──
    LL(3845, '"mesure en cours…"', "mesure_en_cours", "mesure en cours…", "measuring…"),
    SS(3909, '\'(\' + c.rgb.join(",") + \') \' + c.pct.toFixed(1) + \' % de la source → <b>\'\n'
             '            + a.toLocaleString("fr-FR") + \'</b> px après la pose, <b>\' + b.toLocaleString("fr-FR")\n'
             '            + \'</b> px dans la carte livrée\'',
       'dzT("cartes.face.plage", { rgb: c.rgb.join(","), p: c.pct.toFixed(1), a: a.toLocaleString("fr-FR"), b: b.toLocaleString("fr-FR") })',
       {"plage": ("({rgb}) {p} % de la source → <b>{a}</b> px après la pose, <b>{b}</b> px dans la carte livrée",
                  "({rgb}) {p} % of the source → <b>{a}</b> px after placement, <b>{b}</b> px in the delivered card")}),
    SS(3941, '\'Le voile de <b>Matières</b> est actif : motif « \' + esc(String(ov))\n'
             '              + \' », opacité <b>\' + Math.round(op * 100) + \' %</b>, fusion <b>\' + esc(bl)\n'
             '              + \'</b> — c\\\'est lui qui teinte, et il s\\\'éteint dans ce panneau-là. \'',
       'dzT("cartes.face.voile", { ov: esc(String(ov)), op: Math.round(op * 100), bl: esc(bl) })',
       {"voile": ("Le voile de <b>Matières</b> est actif : motif « {ov} », opacité <b>{op} %</b>, fusion <b>{bl}</b> — c'est lui qui teinte, et il s'éteint dans ce panneau-là. ",
                  "The <b>Materials</b> overlay is on: pattern “{ov}”, opacity <b>{op} %</b>, blend <b>{bl}</b> — it is what tints, and it is turned off in that panel. ")}),
    SS(3954, '\'<b>Aucune illustration posée</b> — rien à contrôler. \'\n'
             '          + \'Posez une face du catalogue ou déposez une image, puis relancez.\'',
       'dzT("cartes.face.fid_vide")',
       {"fid_vide": ("<b>Aucune illustration posée</b> — rien à contrôler. Posez une face du catalogue ou déposez une image, puis relancez.",
                     "<b>No illustration placed</b> — nothing to check. Place a face from the catalog or drop an image, then run again.")}),
    SS(3957, '\'Plages plates de la source : \' + plages + \'. \'',
       'dzT("cartes.face.plages", { plages: plages }) + \' \'',
       {"plages": ("Plages plates de la source : {plages}.", "Flat areas of the source: {plages}.")}),
    SS(3970, '\'La pose conserve les plages de la source au pixel (colonne « après la pose » \'\n'
             '            + \'ci-dessus) : la mise en place de l\\\'illustration ne change aucune couleur. \'\n'
             '          : \'Cette face est <b>vectorielle</b> : elle est redessinée à la taille de la pose, il n\\\'y \'\n'
             '            + \'a aucun octet source à retrouver. Déposez une image importée et relancez : \'\n'
             '            + \'le contrôle retrouvera alors ses plages plates de couleur des deux côtés. \'',
       'dzT("cartes.face.fid_conserve")\n'
       '          : dzT("cartes.face.fid_vec")',
       {"fid_conserve": ("La pose conserve les plages de la source au pixel (colonne « après la pose » ci-dessus) : la mise en place de l'illustration ne change aucune couleur. ",
                         "Placement keeps the source's flat areas to the pixel (“after placement” column above): positioning the illustration changes no color. "),
        "fid_vec": ("Cette face est <b>vectorielle</b> : elle est redessinée à la taille de la pose, il n'y a aucun octet source à retrouver. Déposez une image importée et relancez : le contrôle retrouvera alors ses plages plates de couleur des deux côtés. ",
                    "This face is <b>vector</b>: it is redrawn at the placement size, there is no source byte to find. Drop an imported image and run again: the check will then find its flat color areas on both sides. ")}),
    SS(3976, '\'<b>Fidèle à l\\\'octet</b> : sur les \' + tot.toLocaleString("fr-FR")\n'
             '            + \' pixels de la fenêtre d\\\'illustration, <b>aucun</b> n\\\'est modifié entre la face \'\n'
             '            + \'posée et la carte livrée.\'\n'
             '          : preuve\n'
             '            + \'Sur les \' + tot.toLocaleString("fr-FR") + \' pixels de la fenêtre d\\\'illustration : \'\n'
             '            + \'<b>\' + (100 * (tot - diff) / tot).toFixed(1) + \' % inchangés</b>, \'\n'
             '            + \'<b>\' + (100 * teinte / tot).toFixed(1) + \' % teintés</b> (écart de 1 à \' + FID_TINT\n'
             '            + \' niveaux — une fusion) et <b>\' + (100 * couvert / tot).toFixed(1) + \' % recouverts</b> \'\n'
             '            + \'(écart > \' + FID_TINT + \' — quelque chose d\\\'opaque est passé par-dessus). \'\n'
             '            + (med < 0 ? \'Médiane indisponible. \' : \'Écart médian \' + med + \', \')\n'
             '            + \'maximum \' + mx + \' niveaux. \'\n'
             '            + ici\n'
             '            + \'Ce qui passe AU-DESSUS de la face, d\\\'après la table des z du moteur : <b>\'\n'
             '            + esc(zs.join(", ")) + \'</b>. \' + voile\n'
             '            + \'Ce contrôle ne pèse pas ces couches une par une : il mesure leur effet total, \'\n'
             '            + \'et chacune se règle dans son propre panneau.\'',
       'dzT("cartes.face.fid_octet", { n: tot.toLocaleString("fr-FR") })\n'
       '          : preuve\n'
       '            + dzT("cartes.face.fid_ecarts", { n: tot.toLocaleString("fr-FR"), inch: (100 * (tot - diff) / tot).toFixed(1), te: (100 * teinte / tot).toFixed(1), seuil: FID_TINT, rec: (100 * couvert / tot).toFixed(1) }) + \' \'\n'
       '            + (med < 0 ? dzT("cartes.face.fid_med_na") + \' \' : dzT("cartes.face.fid_med", { m: med }) + \', \')\n'
       '            + dzT("cartes.face.fid_max", { m: mx }) + \' \'\n'
       '            + ici\n'
       '            + dzT("cartes.face.fid_dessus", { zs: esc(zs.join(", ")) }) + \' \' + voile\n'
       '            + dzT("cartes.face.fid_fin")',
       {"fid_octet": ("<b>Fidèle à l'octet</b> : sur les {n} pixels de la fenêtre d'illustration, <b>aucun</b> n'est modifié entre la face posée et la carte livrée.",
                      "<b>Byte-exact</b>: of the {n} pixels in the art window, <b>none</b> is altered between the placed face and the delivered card."),
        "fid_ecarts": ("Sur les {n} pixels de la fenêtre d'illustration : <b>{inch} % inchangés</b>, <b>{te} % teintés</b> (écart de 1 à {seuil} niveaux — une fusion) et <b>{rec} % recouverts</b> (écart > {seuil} — quelque chose d'opaque est passé par-dessus).",
                       "Of the {n} pixels in the art window: <b>{inch} % unchanged</b>, <b>{te} % tinted</b> (difference of 1 to {seuil} levels — a blend) and <b>{rec} % covered</b> (difference > {seuil} — something opaque went over it)."),
        "fid_med_na": ("Médiane indisponible.", "Median unavailable."),
        "fid_med": ("Écart médian {m}", "Median difference {m}"),
        "fid_max": ("maximum {m} niveaux.", "maximum {m} levels."),
        "fid_dessus": ("Ce qui passe AU-DESSUS de la face, d'après la table des z du moteur : <b>{zs}</b>.",
                       "What lies ABOVE the face, per the engine's z table: <b>{zs}</b>."),
        "fid_fin": ("Ce contrôle ne pèse pas ces couches une par une : il mesure leur effet total, et chacune se règle dans son propre panneau.",
                    "This check does not weigh these layers one by one: it measures their total effect, and each one is set in its own panel.")}),
    LL(3994, '"le contrôle a échoué : "', "fid_echec", "le contrôle a échoué : ", "the check failed: "),

    # ── pied de panneau, coût ──
    LL(4018, '"Auto → fenêtre publiée par le cadre"', "auto_cadre", "Auto → fenêtre publiée par le cadre",
       "Auto → window published by the frame"),
    LL(4019, '"Auto → toile entière (le cadre n\'en publie aucune)"', "auto_toile",
       "Auto → toile entière (le cadre n'en publie aucune)", "Auto → full canvas (the frame publishes none)"),
    LL(4024, '"posée"', "src_posee", "posée", "placed", contexte=True),
    LL(4024, '"aucune"', "src_aucune", "aucune", "none", contexte=True),
    SS(4026, '" · fenêtre " + Math.round(w[2]) + " x " + Math.round(w[3]) + " px"\n'
             '      + " (" + fmt1(g.px2mm(w[2])) + " x " + fmt1(g.px2mm(w[3])) + " mm, " + pct\n'
             '      + " % de la SURFACE de la toile)"\n'
             '      + " · origine " + fmt1(w[0]) + " / " + fmt1(w[1]) + " px"\n'
             '      + " · décalage " + fmt1(g.mm2px(f.x)) + " / " + fmt1(g.mm2px(f.y)) + " px"\n'
             '      + " · illustration : " + src',
       'dzT("cartes.face.lecture", { w: Math.round(w[2]), h: Math.round(w[3]), wmm: fmt1(g.px2mm(w[2])), hmm: fmt1(g.px2mm(w[3])), pct: pct, ox: fmt1(w[0]), oy: fmt1(w[1]), dx: fmt1(g.mm2px(f.x)), dy: fmt1(g.mm2px(f.y)), src: src })',
       {"lecture": (" · fenêtre {w} x {h} px ({wmm} x {hmm} mm, {pct} % de la SURFACE de la toile) · origine {ox} / {oy} px · décalage {dx} / {dy} px · illustration : {src}",
                    " · window {w} x {h} px ({wmm} x {hmm} mm, {pct} % of the canvas AREA) · origin {ox} / {oy} px · offset {dx} / {dy} px · illustration: {src}")}),
    SS(4058, '\'<b>Aucun modèle d\\\'image disponible</b> — aucune clé FAL ni OpenAI \'\n'
             '        + \'n\\\'est enregistrée dans les Réglages de l\\\'application, la génération échouerait. \'\n'
             '        + \'Le catalogue vectoriel et l\\\'import, eux, ne demandent aucune clé.\'',
       'dzT("cartes.face.cout_aucun_modele")',
       {"cout_aucun_modele": ("<b>Aucun modèle d'image disponible</b> — aucune clé FAL ni OpenAI n'est enregistrée dans les Réglages de l'application, la génération échouerait. Le catalogue vectoriel et l'import, eux, ne demandent aucune clé.",
                              "<b>No image model available</b> — no FAL or OpenAI key is saved in the app Settings, so generation would fail. The vector catalog and import need no key.")}),
    SS(4067, '\'Coût de ce clic : <b>\' + n + \' image\' + (n > 1 ? \'s\' : \'\') + \'</b> chez \' + qui\n'
             '        + \'. <b>Tarif non tabulé</b> dans l\\\'application : aucun montant n\\\'est affiché ici, \'\n'
             '        + \'plutôt qu\\\'un montant emprunté à un autre modèle.\'\n'
             '      : \'Coût de ce clic : <b>\' + n + \' × \' + usdFmt(u) + \' = \' + usdFmt(n * u) + \'</b> chez \' + qui\n'
             '        + \'. Tarif lu dans \' + esc(AI_META.tarif_source || "la table de tarifs de l\'application")\n'
             '        + \'.\')\n'
             '      + \' C\\\'est la seule action de cet écran qui dépense.\'',
       'dzT(n > 1 ? "cartes.face.cout_sans_tarif_n" : "cartes.face.cout_sans_tarif_1", { n: n, qui: qui })\n'
       '      : dzT("cartes.face.cout_tarif", { n: n, u: usdFmt(u), t: usdFmt(n * u), qui: qui, src: esc(AI_META.tarif_source || dzT("cartes.face.table_tarifs")) }))\n'
       '      + \' \' + dzT("cartes.face.seule_depense")',
       {"cout_sans_tarif_1": ("Coût de ce clic : <b>{n} image</b> chez {qui}. <b>Tarif non tabulé</b> dans l'application : aucun montant n'est affiché ici, plutôt qu'un montant emprunté à un autre modèle.",
                              "Cost of this click: <b>{n} image</b> with {qui}. <b>Price not listed</b> in the app: no amount is shown here, rather than an amount borrowed from another model."),
        "cout_sans_tarif_n": ("Coût de ce clic : <b>{n} images</b> chez {qui}. <b>Tarif non tabulé</b> dans l'application : aucun montant n'est affiché ici, plutôt qu'un montant emprunté à un autre modèle.",
                              "Cost of this click: <b>{n} images</b> with {qui}. <b>Price not listed</b> in the app: no amount is shown here, rather than an amount borrowed from another model."),
        "cout_tarif": ("Coût de ce clic : <b>{n} × {u} = {t}</b> chez {qui}. Tarif lu dans {src}.",
                       "Cost of this click: <b>{n} × {u} = {t}</b> with {qui}. Price read from {src}."),
        "table_tarifs": ("la table de tarifs de l'application", "the app's price table"),
        "seule_depense": ("C'est la seule action de cet écran qui dépense.", "It is the only action on this screen that spends money.")}),
    XX(4191, '"/image"', "unité de prix, identique en anglais"),
    LL(4192, '" — tarif non tabulé"', "tarif_non_tabule", " — tarif non tabulé", " — price not listed"),
    SS(4193, '\'<option value="">aucun modèle disponible</option>\'',
       '\'<option value="">\' + dzT("cartes.face.aucun_modele") + \'</option>\'',
       {"aucun_modele": ("aucun modèle disponible", "no model available")}),
    LL(4281, '"écrivez une invite (ou cliquez une amorce)"', "invite_vide", "écrivez une invite (ou cliquez une amorce)",
       "write a prompt (or click a starter)"),
    LL(4289, '"génération de l\'illustration…"', "gen_en_cours", "génération de l'illustration…",
       "generating the illustration…"),
    LL(4293, '"le fournisseur n\'a rendu aucune image"', "gen_vide", "le fournisseur n'a rendu aucune image",
       "the provider returned no image"),
    SS(4302, 'files.length + " image(s) générée(s) — la première est posée sur la carte"\n'
             '        + (u === null ? "" : " · " + usdFmt(files.length * u) + " facturés chez " + mm.provider)',
       'dzT("cartes.face.gen_ok", { n: files.length })\n'
       '        + (u === null ? "" : dzT("cartes.face.gen_facture", { usd: usdFmt(files.length * u), p: mm.provider }))',
       {"gen_ok": ("{n} image(s) générée(s) — la première est posée sur la carte",
                   "{n} image(s) generated — the first one is placed on the card"),
        "gen_facture": (" · {usd} facturés chez {p}", " · {usd} billed by {p}")}),
    LL(4305, '"génération : "', "err_gen", "génération : ", "generation: "),

    # ── 8. la carte elle-même ──
    LL(4469, '"déposée(s) sur la carte"', "quoi_carte", "déposée(s) sur la carte", "dropped on the card"),
    LL(4524, '"collée(s)"', "quoi_collee", "collée(s)", "pasted"),
]

# ── amorces d'invite : PROMPTS envoyés au générateur, miroir de face.py:PROMPT_SEEDS (libellés figés par test_cards_face)
PROMPT = "prompt envoyé au générateur d'images (miroir de cards/face.py:PROMPT_SEEDS)"
SEED_LBL = "libellé d'amorce, miroir de cards/face.py:PROMPT_SEEDS confronté par test_cards_face"
ENTREES.append(XX(4530, '"cadrage vertical de carte à jouer, sujet centré, marge sur les bords pour le fond perdu"', PROMPT))
for _l, _lbl, _p in [
    (4532, "Créature de garde", "créature gardienne massive de trois-quarts, armure gravée, brume au sol, "),
    (4533, "Héros au combat", "héros en pleine action, cape en mouvement, éclat d'arme, arrière-plan simplifié, "),
    (4534, "Sort élémentaire", "explosion d'énergie élémentaire, volutes lumineuses, fond sombre pour lire le titre, "),
    (4535, "Paysage de royaume", "vaste paysage de royaume au crépuscule, silhouette d'architecture, ciel très travaillé, "),
    (4536, "Artefact posé", "artefact unique posé sur un socle, éclairage rasant, arrière-plan neutre, "),
    (4537, "Bête des profondeurs", "bête abyssale cuirassée, eaux sombres, rais de lumière, "),
    (4538, "Portail arcanique", "portail arcanique ouvert, runes flottantes, particules, "),
    (4539, "Monture ailée", "monture ailée en vol au-dessus des nuages, contre-jour, "),
    (4540, "Alchimiste", "alchimiste penché sur ses fioles luminescentes, clair-obscur, "),
    (4541, "Ruine engloutie", "ruine engloutie envahie de végétation, faisceau de lumière, "),
    (4542, "Blason héraldique", "blason héraldique stylisé, symétrie parfaite, aplats lisibles, "),
    (4543, "Champ de bataille", "champ de bataille au petit matin, étendards, poussière, "),
    (4544, "Familier", "petit familier expressif, pose dynamique, couleurs saturées, "),
    (4545, "Cité suspendue", "cité suspendue dans les nuages, ponts de pierre, échelle épique, "),
    (4546, "Rituel nocturne", "rituel nocturne, cercle de bougies, ombres portées longues, "),
    (4547, "Machine de guerre", "machine de guerre à vapeur, rivets, fumée, perspective basse, "),
]:
    ENTREES.append(XX(_l, '"' + _lbl + '"', SEED_LBL))
    ENTREES.append(XX(_l, '"' + _p + '"', PROMPT))
