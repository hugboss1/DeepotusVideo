"""t147 — frame3 : mod-frame.js 7176-fin (cadres, 3e tiers) — tableaux de preuve sur les octets (en-têtes, badges,
infobulles, lectures), les deux définitions 300/600, l'épreuve de contrôle (traits de coupe), la vérification par le
backend, la ligne du Sceau, le bloc « Adopter la bordure », la synchronisation de l'écran (compte de combinaisons,
bornes du format, lecture du filet, fenêtre, bandeau, gemme), le compteur d'occupation et l'estampille, les libellés
d'historique des raccourcis clavier.
GARDÉ : noms de fichiers téléchargés (dos_/carte_), le texte tEXt « ÉPREUVE DE CONTRÔLE — NE PAS IMPRIMER » que le
backend écrit dans le fichier (cité tel quel), le format de nombres "fr-FR". Les phrases coupées en concaténations
deviennent UNE clé à variables ; pluriels choisis par le code (_un / _plusieurs)."""
from outils import L, S, X, H

F = "js/mod-frame.js"
PLAGES = {F: (7176, 8185)}


def J(*lignes):
    return "\r\n".join(lignes)


COL_ECRAN = {"cartes.frame3.col_ecran": ("ce que l'écran annonce", "what the screen claims")}
COL_HD = {"cartes.frame3.col_annonce": ("valeur annoncée", "claimed value"),
          "cartes.frame3.col_octets": ("ce que les octets disent", "what the bytes say")}
HD_AV = '"<span>valeur annoncée</span><span>ce que les octets disent</span></div>"'
HD_AP = '"<span>" + dzT("cartes.frame3.col_annonce") + "</span><span>" + dzT("cartes.frame3.col_octets") + "</span></div>"'
ECRAN_AV = """'<div class="cff-proofhd"><span>?</span><span>ce que l\\'écran annonce</span>'"""
ECRAN_AP = """'<div class="cff-proofhd"><span>?</span><span>' + dzT("cartes.frame3.col_ecran") + '</span>'"""

ECARTS_AT = {"cartes.frame3.ecarts_sur_at": ("{n} écart(s) sur {total} · {at}", "{n} mismatch(es) out of {total} · {at}")}
PERIMEE = {"cartes.frame3.perimee_depuis": ("périmée depuis {at}", "stale since {at}")}
LIGNES_OCTETS = {"cartes.frame3.lignes_verifiees_octets": ("{n} lignes vérifiées sur les octets · {at}",
                                                            "{n} rows checked against the bytes · {at}")}
AUTO = {"cartes.frame3.automatique": ("automatique", "automatic")}
TOILE_DPI = {"cartes.frame3.toile_a_dpi": ("Toile à {dpi} DPI", "Canvas at {dpi} DPI")}
PX_IHDR = {"cartes.frame3.px_lus_ihdr": ("{w} x {h} px lus dans IHDR", "{w} x {h} px read from IHDR")}
PCT_DPI = {"cartes.frame3.pct_a_dpi": ("{pct} % à {dpi} DPI ({n}/{sur})", "{pct} % at {dpi} DPI ({n}/{sur})")}
DEPART_AUTO = {"cartes.frame3.depart_auto": ("départ automatique…", "starting automatically…")}
SEP_AUTO = {"cartes.frame3.sep_depart_auto": (" · départ automatique", " · auto-start")}
IMPOSSIBLE = {"cartes.frame3.impossible": ("impossible", "failed")}
BORNE = {"cartes.frame3.borne_format": (" (borne du format)", " (format limit)")}

ENTREES = [
    # ── drawProof : en-tête, badge, infobulle, lecture ─────────────────────────────────────────────
    S(F, 7176, HD_AV, HD_AP, COL_HD),
    S(F, 7184, 'bad + " écart(s) sur " + rows.length + " · " + hms(P.at)',
      'dzT("cartes.frame3.ecarts_sur_at", { n: bad, total: rows.length, at: hms(P.at) })', ECARTS_AT),
    S(F, 7185, '"périmée depuis " + hms(P.at) + " — relecture…"',
      'dzT("cartes.frame3.perimee_relecture", { at: hms(P.at) })',
      {"cartes.frame3.perimee_relecture": ("périmée depuis {at} — relecture…", "stale since {at} — re-reading…")}),
    S(F, 7186, 'rows.length + " lignes vérifiées sur les octets · " + hms(P.at)',
      'dzT("cartes.frame3.lignes_verifiees_octets", { n: rows.length, at: hms(P.at) })', LIGNES_OCTETS),
    S(F, 7187,
      J('"Empreinte vérifiée : " + PROOF.sig + " (géométrie + document + carte courante). "',
        '      + "Relecture " + (PROOF.auto ? "automatique" : "demandée à la main") + " à " + hms(P.at)',
        '      + (perime ? " — l\'empreinte vaut maintenant " + fileSig() + ", la relecture repart." : "")'),
      J('dzT("cartes.frame3.pbadge_titre", { sig: PROOF.sig, at: hms(P.at),',
        '        mode: PROOF.auto ? dzT("cartes.frame3.automatique") : dzT("cartes.frame3.demandee_main") })',
        '      + (perime ? dzT("cartes.frame3.empreinte_maintenant", { sig: fileSig() }) : "")'),
      {"cartes.frame3.pbadge_titre": (
          "Empreinte vérifiée : {sig} (géométrie + document + carte courante). Relecture {mode} à {at}",
          "Verified fingerprint: {sig} (geometry + document + current card). Re-read ({mode}) at {at}"),
       **AUTO,
       "cartes.frame3.demandee_main": ("demandée à la main", "requested by hand"),
       "cartes.frame3.empreinte_maintenant": (" — l'empreinte vaut maintenant {sig}, la relecture repart.",
                                              " — the fingerprint is now {sig}; re-reading again.")}),
    S(F, 7194,
      J('"<b>" + (P.face === "back" ? "Verso" : "Recto") + "</b> — fichier de <b>"',
        '      + P.octets.toLocaleString("fr-FR") + " octets</b>"',
        '      + (P.estampille ? "" : " (backend absent : SANS pHYs)")',
        '      + ", " + h0.w + " x " + h0.h + " px, " + (P.alpha.canaux === 3 ? "RGB" : "RGBA") + " 8 bits, "',
        '      + h0.chunks.length + " chunks. Zlib décompressé et lignes défiltrées ici même — "',
        '      + "aucune API d\'image n\'a été employée pour relire ce fichier. "',
        '      + "<b>Relecture " + (PROOF.auto ? "automatique" : "manuelle") + " de " + hms(P.at) + "</b>, "',
        '      + "empreinte " + PROOF.sig + " — elle repart seule dès que le fichier change."'),
      J('dzT("cartes.frame3.proof_lu", { face: P.face === "back" ? dzT("cartes.frame3.face_verso") : dzT("cartes.frame3.face_recto"),',
        '        octets: P.octets.toLocaleString("fr-FR") })',
        '      + (P.estampille ? "" : dzT("cartes.frame3.sans_phys"))',
        '      + dzT("cartes.frame3.proof_lu_detail", { w: h0.w, h: h0.h, canaux: P.alpha.canaux === 3 ? "RGB" : "RGBA",',
        '        chunks: h0.chunks.length })',
        '      + dzT("cartes.frame3.proof_lu_relecture", { mode: PROOF.auto ? dzT("cartes.frame3.automatique")',
        '        : dzT("cartes.frame3.manuelle"), at: hms(P.at), sig: PROOF.sig })'),
      {"cartes.frame3.proof_lu": ("<b>{face}</b> — fichier de <b>{octets} octets</b>",
                                  "<b>{face}</b> — <b>{octets}-byte</b> file"),
       "cartes.frame3.face_verso": ("Verso", "Back"),
       "cartes.frame3.face_recto": ("Recto", "Front"),
       "cartes.frame3.sans_phys": (" (backend absent : SANS pHYs)", " (backend missing: NO pHYs)"),
       "cartes.frame3.proof_lu_detail": (
           ", {w} x {h} px, {canaux} 8 bits, {chunks} chunks. Zlib décompressé et lignes défiltrées ici même — "
           "aucune API d'image n'a été employée pour relire ce fichier. ",
           ", {w} x {h} px, {canaux} 8-bit, {chunks} chunks. Zlib inflated and rows unfiltered right here — "
           "no image API was used to re-read this file. "),
       **AUTO,
       "cartes.frame3.manuelle": ("manuelle", "manual"),
       "cartes.frame3.proof_lu_relecture": (
           "<b>Relecture {mode} de {at}</b>, empreinte {sig} — elle repart seule dès que le fichier change.",
           "<b>Re-read ({mode}) at {at}</b>, fingerprint {sig} — it restarts on its own as soon as the file changes.")}),

    # ── les deux définitions ───────────────────────────────────────────────────────────────────────
    S(F, 7252, '"la barre de format du CORE n\'offre pas " + v + " DPI"', 'dzT("cartes.frame3.err_barre_dpi", { v: v })',
      {"cartes.frame3.err_barre_dpi": ("la barre de format du CORE n'offre pas {v} DPI",
                                       "the CORE format bar has no {v} DPI option")}),
    S(F, 7258, '"la définition n\'est pas passée à " + v + " DPI"', 'dzT("cartes.frame3.err_dpi_pas_passe", { v: v })',
      {"cartes.frame3.err_dpi_pas_passe": ("la définition n'est pas passée à {v} DPI",
                                           "the resolution did not switch to {v} DPI")}),
    L(F, 7386, '"rendu et relecture des octets aux deux définitions…"', "cartes.frame3.busy_twin",
      "rendu et relecture des octets aux deux définitions…", "rendering and re-reading the bytes at both resolutions…"),
    L(F, 7415, '"départ automatique…"', "cartes.frame3.depart_auto", "départ automatique…", "starting automatically…"),
    S(F, 7421, '(TWIN.auto ? "rendu automatique" : "rendu") + " des deux fichiers…"',
      '(TWIN.auto ? dzT("cartes.frame3.rendu_auto_deux") : dzT("cartes.frame3.rendu_deux"))',
      {"cartes.frame3.rendu_auto_deux": ("rendu automatique des deux fichiers…", "automatic rendering of both files…"),
       "cartes.frame3.rendu_deux": ("rendu des deux fichiers…", "rendering both files…")}),
    L(F, 7427, '"impossible"', "cartes.frame3.impossible", "impossible", "failed"),
    S(F, 7436, '"Toile à " + A.dpi + " DPI"', 'dzT("cartes.frame3.toile_a_dpi", { dpi: A.dpi })', TOILE_DPI),
    S(F, 7437, 'A.w + " x " + A.h + " px lus dans IHDR"', 'dzT("cartes.frame3.px_lus_ihdr", { w: A.w, h: A.h })', PX_IHDR),
    L(F, 7438, '"taille recalculée à partir des millimètres, jamais multipliée"', "cartes.frame3.taille_recalculee",
      "taille recalculée à partir des millimètres, jamais multipliée", "size recomputed from millimetres, never multiplied"),
    S(F, 7439, '"Toile à " + B.dpi + " DPI"', 'dzT("cartes.frame3.toile_a_dpi", { dpi: B.dpi })', TOILE_DPI),
    S(F, 7440, 'B.w + " x " + B.h + " px lus dans IHDR"', 'dzT("cartes.frame3.px_lus_ihdr", { w: B.w, h: B.h })', PX_IHDR),
    S(F, 7441,
      J('exact2 ? "ici exactement le double" : "PAS le double de " + A.attendu[0] + " x " + A.attendu[1]',
        '        + " : la règle d\'arrondi px(mm,dpi) ne double pas sur ce format"'),
      J('exact2 ? dzT("cartes.frame3.exactement_double")',
        '        : dzT("cartes.frame3.pas_double", { w: A.attendu[0], h: A.attendu[1] })'),
      {"cartes.frame3.exactement_double": ("ici exactement le double", "exactly double here"),
       "cartes.frame3.pas_double": ("PAS le double de {w} x {h} : la règle d'arrondi px(mm,dpi) ne double pas sur ce format",
                                    "NOT double {w} x {h}: the px(mm,dpi) rounding rule does not double on this format")}),
    L(F, 7443, '"Définition portée (pHYs)"', "cartes.frame3.definition_portee", "Définition portée (pHYs)",
      "Resolution carried (pHYs)"),
    S(F, 7444, '(B.ppm + " px/m, unité " + B.ppm_unit + " = " + dpiOf(B.ppm) + " DPI")',
      'dzT("cartes.frame3.ppm_unite", { ppm: B.ppm, u: B.ppm_unit, dpi: dpiOf(B.ppm) })',
      {"cartes.frame3.ppm_unite": ("{ppm} px/m, unité {u} = {dpi} DPI", "{ppm} px/m, unit {u} = {dpi} DPI")}),
    L(F, 7444, '"aucun chunk pHYs"', "cartes.frame3.aucun_phys", "aucun chunk pHYs", "no pHYs chunk"),
    L(F, 7445, '"relu dans le fichier 600"', "cartes.frame3.relu_600", "relu dans le fichier 600", "re-read from the 600 file"),
    L(F, 7448, '"Épaisseur du filet, en MILLIMÈTRES"', "cartes.frame3.epaisseur_mm", "Épaisseur du filet, en MILLIMÈTRES",
      "Rule thickness, in MILLIMETRES"),
    S(F, 7448, 'A.annonce_mm + " mm des deux côtés"', 'dzT("cartes.frame3.mm_deux_cotes", { mm: A.annonce_mm })',
      {"cartes.frame3.mm_deux_cotes": ("{mm} mm des deux côtés", "{mm} mm on both sides")}),
    S(F, 7449,
      J('A.filet_mm + " mm à " + A.dpi + " DPI (" + A.filet.largeur + " px) · "',
        '        + B.filet_mm + " mm à " + B.dpi + " DPI (" + B.filet.largeur + " px)"'),
      J('dzT("cartes.frame3.mm_a_dpi_px", { mm: A.filet_mm, dpi: A.dpi, px: A.filet.largeur }) + " · "',
        '        + dzT("cartes.frame3.mm_a_dpi_px", { mm: B.filet_mm, dpi: B.dpi, px: B.filet.largeur })'),
      {"cartes.frame3.mm_a_dpi_px": ("{mm} mm à {dpi} DPI ({px} px)", "{mm} mm at {dpi} DPI ({px} px)")}),
    S(F, 7452,
      J('"écart " + r2(e) + " mm, pour un pas de mesure de " + A.pas_mm + " et " + B.pas_mm',
        '        + " mm (un échantillon) : la mesure est quantifiée, pas le tracé"'),
      'dzT("cartes.frame3.ecart_pas", { e: r2(e), a: A.pas_mm, b: B.pas_mm })',
      {"cartes.frame3.ecart_pas": (
          "écart {e} mm, pour un pas de mesure de {a} et {b} mm (un échantillon) : la mesure est quantifiée, pas le tracé",
          "difference {e} mm, for a measuring step of {a} and {b} mm (one sample): the measurement is quantized, "
          "not the drawing")}),
    L(F, 7455, '"Épaisseur du filet"', "cartes.frame3.epaisseur", "Épaisseur du filet", "Line thickness"),
    L(F, 7456, '"non isolable à l\'une des deux définitions"', "cartes.frame3.non_isolable",
      "non isolable à l'une des deux définitions", "cannot be isolated at one of the two resolutions"),
    L(F, 7457, '"aucun chiffre publié — voir la ligne du panneau au-dessus"', "cartes.frame3.aucun_chiffre",
      "aucun chiffre publié — voir la ligne du panneau au-dessus", "no figure published — see the line in the panel above"),
    L(F, 7459, '"Lignes identiques à leur voisine"', "cartes.frame3.lignes_identiques", "Lignes identiques à leur voisine",
      "Rows identical to their neighbour"),
    L(F, 7459, '"0 % — un x2 au plus proche voisin en donne 50,0 %"', "cartes.frame3.zero_pct_voisin",
      "0 % — un x2 au plus proche voisin en donne 50,0 %", "0 % — a nearest-neighbour x2 gives 50.0 %"),
    S(F, 7460,
      J('A.dup.pct_l + " % à " + A.dpi + " DPI (" + A.dup.lignes + "/" + A.dup.sur_l + ") · "',
        '      + B.dup.pct_l + " % à " + B.dpi + " DPI (" + B.dup.lignes + "/" + B.dup.sur_l + ")"'),
      J('dzT("cartes.frame3.pct_a_dpi", { pct: A.dup.pct_l, dpi: A.dpi, n: A.dup.lignes, sur: A.dup.sur_l }) + " · "',
        '      + dzT("cartes.frame3.pct_a_dpi", { pct: B.dup.pct_l, dpi: B.dpi, n: B.dup.lignes, sur: B.dup.sur_l })'),
      PCT_DPI),
    L(F, 7462, '"un x2 au plus proche voisin recopie exactement une ligne sur deux"', "cartes.frame3.recopie_ligne",
      "un x2 au plus proche voisin recopie exactement une ligne sur deux", "a nearest-neighbour x2 copies exactly every other row"),
    L(F, 7463, '"Colonnes identiques à leur voisine"', "cartes.frame3.colonnes_identiques", "Colonnes identiques à leur voisine",
      "Columns identical to their neighbour"),
    L(F, 7463, '"0 % — même piège dans l\'autre sens"', "cartes.frame3.meme_piege", "0 % — même piège dans l'autre sens",
      "0 % — same trap the other way"),
    L(F, 7465, '"un x2 au plus proche voisin duplique aussi une colonne sur deux"', "cartes.frame3.duplique_colonne",
      "un x2 au plus proche voisin duplique aussi une colonne sur deux",
      "a nearest-neighbour x2 also duplicates every other column"),
    L(F, 7466, '"Lignes qui sont la MOYENNE de leurs voisines"', "cartes.frame3.lignes_moyenne",
      "Lignes qui sont la MOYENNE de leurs voisines", "Rows that are the AVERAGE of their neighbours"),
    L(F, 7466, '"0 % — un x2 linéaire en donne 100 %"', "cartes.frame3.zero_pct_lineaire", "0 % — un x2 linéaire en donne 100 %",
      "0 % — a linear x2 gives 100 %"),
    S(F, 7467,
      J('A.dup.pct_m + " % à " + A.dpi + " DPI (" + A.dup.moyennes + "/" + A.dup.impaires + ") · "',
        '      + B.dup.pct_m + " % à " + B.dpi + " DPI (" + B.dup.moyennes + "/" + B.dup.impaires + ")"'),
      J('dzT("cartes.frame3.pct_a_dpi", { pct: A.dup.pct_m, dpi: A.dpi, n: A.dup.moyennes, sur: A.dup.impaires }) + " · "',
        '      + dzT("cartes.frame3.pct_a_dpi", { pct: B.dup.pct_m, dpi: B.dpi, n: B.dup.moyennes, sur: B.dup.impaires })'),
      PCT_DPI),
    S(F, 7470,
      J('"le second piège : un agrandissement filtré ne duplique rien, mais chaque ligne impaire y "',
        '      + "est la moyenne exacte des deux autres. LIMITE ASSUMÉE : un dégradé parfaitement "',
        '      + "linéaire est sa propre interpolation et ferait monter ce chiffre sans aucun "',
        '      + "agrandissement. Il ne peut donc pas laisser passer un agrandissement, seulement "',
        '      + "crier à tort"'),
      'dzT("cartes.frame3.second_piege")',
      {"cartes.frame3.second_piege": (
          "le second piège : un agrandissement filtré ne duplique rien, mais chaque ligne impaire y est la moyenne "
          "exacte des deux autres. LIMITE ASSUMÉE : un dégradé parfaitement linéaire est sa propre interpolation et "
          "ferait monter ce chiffre sans aucun agrandissement. Il ne peut donc pas laisser passer un agrandissement, "
          "seulement crier à tort",
          "the second trap: a filtered upscale duplicates nothing, but every odd row is the exact average of the other "
          "two. ACKNOWLEDGED LIMIT: a perfectly linear gradient is its own interpolation and would push this figure up "
          "with no upscale at all. So it can never let an upscale through — it can only raise a false alarm")}),
    L(F, 7477, '"Acuité imprimée de l\'arête du filet"', "cartes.frame3.acuite", "Acuité imprimée de l'arête du filet",
      "Printed sharpness of the rule edge"),
    L(F, 7477, '"plus fine sur le papier à 600 DPI"', "cartes.frame3.plus_fine_600", "plus fine sur le papier à 600 DPI",
      "finer on paper at 600 DPI"),
    S(F, 7478,
      J('A.rise.largeur_px + " échantillons = " + ma + " mm à " + A.dpi + " DPI · "',
        '        + B.rise.largeur_px + " = " + mb + " mm à " + B.dpi + " DPI"'),
      J('dzT("cartes.frame3.echantillons_mm", { n: A.rise.largeur_px, mm: ma, dpi: A.dpi }) + " · "',
        '        + dzT("cartes.frame3.egal_mm_dpi", { n: B.rise.largeur_px, mm: mb, dpi: B.dpi })'),
      {"cartes.frame3.echantillons_mm": ("{n} échantillons = {mm} mm à {dpi} DPI", "{n} samples = {mm} mm at {dpi} DPI"),
       "cartes.frame3.egal_mm_dpi": ("{n} = {mm} mm à {dpi} DPI", "{n} = {mm} mm at {dpi} DPI")}),
    S(F, 7481,
      J('"FINESSE, pas preuve de retracé : un x2 au plus proche voisin donnerait lui aussi "',
        '        + "une arête fine. Ce sont les trois lignes au-dessus qui écartent l\'agrandissement"'),
      'dzT("cartes.frame3.finesse")',
      {"cartes.frame3.finesse": (
          "FINESSE, pas preuve de retracé : un x2 au plus proche voisin donnerait lui aussi une arête fine. "
          "Ce sont les trois lignes au-dessus qui écartent l'agrandissement",
          "SHARPNESS, not proof of redrawing: a nearest-neighbour x2 would also give a sharp edge. "
          "It is the three rows above that rule out an upscale")}),
    L(F, 7484, '"Poids des deux fichiers"', "cartes.frame3.poids_deux", "Poids des deux fichiers", "Size of both files"),
    L(F, 7484, '"le 600 pèse plus : il porte 4 fois plus d\'échantillons"', "cartes.frame3.pese_plus",
      "le 600 pèse plus : il porte 4 fois plus d'échantillons", "the 600 one is larger: it carries 4 times as many samples"),
    S(F, 7485, 'A.octets.toLocaleString("fr-FR") + " octets · " + B.octets.toLocaleString("fr-FR") + " octets"',
      'dzT("cartes.frame3.octets_deux", { a: A.octets.toLocaleString("fr-FR"), b: B.octets.toLocaleString("fr-FR") })',
      {"cartes.frame3.octets_deux": ("{a} octets · {b} octets", "{a} bytes · {b} bytes")}),
    L(F, 7486, '"les deux sont téléchargeables ci-dessous, ce sont EUX qui ont été mesurés"', "cartes.frame3.telechargeables",
      "les deux sont téléchargeables ci-dessous, ce sont EUX qui ont été mesurés",
      "both can be downloaded below — THEY are the ones that were measured"),
    S(F, 7488, ECRAN_AV, ECRAN_AP, COL_ECRAN),
    S(F, 7489, HD_AV, HD_AP, COL_HD),
    S(F, 7493,
      J('bad ? (bad + " écart(s) sur " + rows.length + " · " + hms(TWIN.at))',
        '      : ((vieux ? "périmée depuis " : ICO("dz-etat-succes", 16, "cf-ic") + rows.length + " lignes vérifiées sur les DEUX fichiers · ")',
        '        + hms(TWIN.at))'),
      J('bad ? dzT("cartes.frame3.ecarts_sur_at", { n: bad, total: rows.length, at: hms(TWIN.at) })',
        '      : (vieux ? dzT("cartes.frame3.perimee_depuis", { at: hms(TWIN.at) })',
        '        : ICO("dz-etat-succes", 16, "cf-ic") + dzT("cartes.frame3.lignes_verifiees_deux", { n: rows.length, at: hms(TWIN.at) }))'),
      {**ECARTS_AT, **PERIMEE,
       "cartes.frame3.lignes_verifiees_deux": ("{n} lignes vérifiées sur les DEUX fichiers · {at}",
                                               "{n} rows checked against BOTH files · {at}")}),
    S(F, 7496,
      J('"Empreinte du document REPOSÉ, prise après le retour à " + TWIN.dpi0',
        '      + " DPI et une seconde de calme : " + TWIN.sig',
        '      + (TWIN.auto ? " · départ automatique" : " · lancée à la main")',
        '      + (TWIN.bouge ? " — l\'empreinte a bougé pendant la mesure (une couche voisine suit la "',
        '        + "définition) ; les deux fichiers, eux, ont été rendus à la suite." : "")',
        '      + (vieux ? " — le document vaut maintenant " + fileSig() + ", relance pour remesurer." : "")'),
      J('dzT("cartes.frame3.tbadge_titre", { dpi: TWIN.dpi0, sig: TWIN.sig })',
        '      + (TWIN.auto ? dzT("cartes.frame3.sep_depart_auto") : dzT("cartes.frame3.sep_lancee_main"))',
        '      + (TWIN.bouge ? dzT("cartes.frame3.empreinte_bougee") : "")',
        '      + (vieux ? dzT("cartes.frame3.doc_vaut_relance", { sig: fileSig() }) : "")'),
      {"cartes.frame3.tbadge_titre": (
          "Empreinte du document REPOSÉ, prise après le retour à {dpi} DPI et une seconde de calme : {sig}",
          "Fingerprint of the RESTORED document, taken after returning to {dpi} DPI and one quiet second: {sig}"),
       **SEP_AUTO,
       "cartes.frame3.sep_lancee_main": (" · lancée à la main", " · started by hand"),
       "cartes.frame3.empreinte_bougee": (
           " — l'empreinte a bougé pendant la mesure (une couche voisine suit la définition) ; les deux fichiers, "
           "eux, ont été rendus à la suite.",
           " — the fingerprint moved during the measurement (a neighbouring layer follows the resolution); the two "
           "files themselves were rendered back to back."),
       "cartes.frame3.doc_vaut_relance": (" — le document vaut maintenant {sig}, relance pour remesurer.",
                                          " — the document is now {sig}; run again to re-measure.")}),
    S(F, 7503,
      J('"Les deux fichiers ont été rendus par le <b>vrai chemin d\'export</b>, "',
        '      + "en conduisant le bouton <b>" + B.dpi + "</b> de la barre de format — celui qu\'un utilisateur "',
        '      + "clique — puis la définition d\'origine (<b>" + TWIN.dpi0 + " DPI</b>) a été reposée"',
        '      + (TWIN.repli ? " — <b>ÉCHEC du retour</b> : " + esc(TWIN.repli) : "") + ". "',
        '      + "Leurs octets ont été décompressés et défiltrés ici même. "',
        '      + "<b>Aucun bitmap de cadre n\'intervient</b> : le cadre est retracé à la toile demandée, "',
        '      + "c\'est pour cela que la montée d\'un front ne s\'étale pas et qu\'aucune ligne n\'est dupliquée."'),
      J('dzT("cartes.frame3.twin_lu", { dpi: B.dpi, dpi0: TWIN.dpi0 })',
        '      + (TWIN.repli ? dzT("cartes.frame3.echec_retour", { err: esc(TWIN.repli) }) : "") + ". "',
        '      + dzT("cartes.frame3.twin_lu_fin")'),
      {"cartes.frame3.twin_lu": (
          "Les deux fichiers ont été rendus par le <b>vrai chemin d'export</b>, en conduisant le bouton <b>{dpi}</b> "
          "de la barre de format — celui qu'un utilisateur clique — puis la définition d'origine (<b>{dpi0} DPI</b>) "
          "a été reposée",
          "Both files were rendered through the <b>real export path</b>, by driving the <b>{dpi}</b> button of the "
          "format bar — the one a user clicks — then the original resolution (<b>{dpi0} DPI</b>) was restored"),
       "cartes.frame3.echec_retour": (" — <b>ÉCHEC du retour</b> : {err}", " — <b>restore FAILED</b>: {err}"),
       "cartes.frame3.twin_lu_fin": (
           "Leurs octets ont été décompressés et défiltrés ici même. <b>Aucun bitmap de cadre n'intervient</b> : le "
           "cadre est retracé à la toile demandée, c'est pour cela que la montée d'un front ne s'étale pas et "
           "qu'aucune ligne n'est dupliquée.",
           "Their bytes were inflated and unfiltered right here. <b>No frame bitmap is involved</b>: the frame is "
           "redrawn at the requested canvas, which is why an edge's rise does not spread and no row is duplicated.")}),
    X(F, 7513, '"dos_"', "préfixe du nom de fichier téléchargé"),
    X(F, 7513, '"carte_"', "préfixe du nom de fichier téléchargé"),
    S(F, 7518, '"les deux fichiers mesurés sont téléchargés : " + TWIN.a.dpi + " et " + TWIN.b.dpi + " DPI"',
      'dzT("cartes.frame3.toast_deux_dl", { a: TWIN.a.dpi, b: TWIN.b.dpi })',
      {"cartes.frame3.toast_deux_dl": ("les deux fichiers mesurés sont téléchargés : {a} et {b} DPI",
                                       "both measured files downloaded: {a} and {b} DPI")}),

    # ── l'épreuve de contrôle ──────────────────────────────────────────────────────────────────────
    L(F, 7549, '"épreuve de contrôle : traits de coupe et mires…"', "cartes.frame3.busy_ctrl",
      "épreuve de contrôle : traits de coupe et mires…", "control proof: cut marks and registration targets…"),
    S(F, 7592,
      J('"backend absent : l\'épreuve de contrôle est construite "',
        '          + "par le domaine du cadre, elle ne peut pas être fabriquée dans le navigateur"'),
      'dzT("cartes.frame3.ctrl_backend_absent")',
      {"cartes.frame3.ctrl_backend_absent": (
          "backend absent : l'épreuve de contrôle est construite par le domaine du cadre, elle ne peut pas être "
          "fabriquée dans le navigateur",
          "backend missing: the control proof is built by the frame domain and cannot be made in the browser")}),
    L(F, 7600, '"départ automatique…"', "cartes.frame3.depart_auto", "départ automatique…", "starting automatically…"),
    L(F, 7602, '"construction automatique…"', "cartes.frame3.construction_auto", "construction automatique…",
      "automatic build…"),
    L(F, 7602, '"construction…"', "cartes.frame3.construction", "construction…", "building…"),
    L(F, 7604, '"impossible"', "cartes.frame3.impossible", "impossible", "failed"),
    L(F, 7611, '"Toile de l\'épreuve"', "cartes.frame3.toile_epreuve", "Toile de l'épreuve", "Proof canvas"),
    S(F, 7611,
      J('C.attendu_toile[0] + " x " + C.attendu_toile[1] + " px (toile livrée + "',
        '      + CTRL_MARGE + " mm de papier de chaque côté)", C.w + " x " + C.h + " px lus dans IHDR"'),
      J('dzT("cartes.frame3.toile_marge", { w: C.attendu_toile[0], h: C.attendu_toile[1], m: CTRL_MARGE }),',
        '      dzT("cartes.frame3.px_lus_ihdr", { w: C.w, h: C.h })'),
      {"cartes.frame3.toile_marge": ("{w} x {h} px (toile livrée + {m} mm de papier de chaque côté)",
                                     "{w} x {h} px (delivered canvas + {m} mm of paper on each side)"),
       **PX_IHDR}),
    S(F, 7613, '"marge " + C.marge + " px"', 'dzT("cartes.frame3.marge_px", { n: C.marge })',
      {"cartes.frame3.marge_px": ("marge {n} px", "margin {n} px")}),
    L(F, 7614, '"Traits de coupe verticaux"', "cartes.frame3.traits_verticaux", "Traits de coupe verticaux",
      "Vertical cut marks"),
    S(F, 7614, '"sur x = " + C.attendu_x.join(" et ") + " px"',
      'dzT("cartes.frame3.sur_x", { a: C.attendu_x[0], b: C.attendu_x[1] })',
      {"cartes.frame3.sur_x": ("sur x = {a} et {b} px", "at x = {a} and {b} px")}),
    S(F, 7615, 'C.cols.length + " colonne(s) noire(s) dans la bande du trait : " + C.cols.join(", ")',
      'dzT("cartes.frame3.cols_noires", { n: C.cols.length, liste: C.cols.join(", ") })',
      {"cartes.frame3.cols_noires": ("{n} colonne(s) noire(s) dans la bande du trait : {liste}",
                                     "{n} black column(s) in the mark band: {liste}")}),
    S(F, 7617,
      J('"cherchées dans les échantillons, pas dans l\'en-tête — la coupe tombe entre deux pixels ("',
        '      + C.attendu_x[0] + "), le trait est posé sur la colonne entière la plus proche"'),
      'dzT("cartes.frame3.cherchees_echantillons", { x: C.attendu_x[0] })',
      {"cartes.frame3.cherchees_echantillons": (
          "cherchées dans les échantillons, pas dans l'en-tête — la coupe tombe entre deux pixels ({x}), le trait est "
          "posé sur la colonne entière la plus proche",
          "searched in the samples, not the header — the cut falls between two pixels ({x}), the mark sits on the "
          "nearest whole column")}),
    L(F, 7619, '"Traits de coupe horizontaux"', "cartes.frame3.traits_horizontaux", "Traits de coupe horizontaux",
      "Horizontal cut marks"),
    S(F, 7619, '"sur y = " + C.attendu_y.join(" et ") + " px"',
      'dzT("cartes.frame3.sur_y", { a: C.attendu_y[0], b: C.attendu_y[1] })',
      {"cartes.frame3.sur_y": ("sur y = {a} et {b} px", "at y = {a} and {b} px")}),
    S(F, 7620, 'C.lignes.length + " ligne(s) noire(s) : " + C.lignes.join(", ")',
      'dzT("cartes.frame3.lignes_noires", { n: C.lignes.length, liste: C.lignes.join(", ") })',
      {"cartes.frame3.lignes_noires": ("{n} ligne(s) noire(s) : {liste}", "{n} black row(s): {liste}")}),
    S(F, 7622,
      J('"même méthode ; les colonnes et lignes en trop sont les quatre mires de repérage, "',
        '      + "posées aux COINS du papier — le milieu du bas est réservé au cartouche"'),
      'dzT("cartes.frame3.meme_methode")',
      {"cartes.frame3.meme_methode": (
          "même méthode ; les colonnes et lignes en trop sont les quatre mires de repérage, posées aux COINS du "
          "papier — le milieu du bas est réservé au cartouche",
          "same method; the extra columns and rows are the four registration targets, placed at the paper CORNERS "
          "— the bottom middle is reserved for the title block")}),
    L(F, 7625, '"La carte n\'a pas bougé"', "cartes.frame3.carte_pas_bouge", "La carte n'a pas bougé",
      "The card did not move"),
    L(F, 7625, '"zone carte identique à la source, octet par octet"', "cartes.frame3.zone_identique",
      "zone carte identique à la source, octet par octet", "card area identical to the source, byte for byte"),
    L(F, 7626, '"aucune mention PixelCheck"', "cartes.frame3.aucun_pixelcheck", "aucune mention PixelCheck",
      "no PixelCheck entry"),
    L(F, 7627, '"vérifié par le domaine du cadre APRÈS encodage, et écrit dans le fichier"', "cartes.frame3.verifie_domaine",
      "vérifié par le domaine du cadre APRÈS encodage, et écrit dans le fichier",
      "checked by the frame domain AFTER encoding, and written into the file"),
    L(F, 7629, '"Le fichier dit ce qu\'il est"', "cartes.frame3.fichier_dit", "Le fichier dit ce qu'il est",
      "The file says what it is"),
    X(F, 7629, '"« ÉPREUVE DE CONTRÔLE — NE PAS IMPRIMER »"',
      "cite tel quel le tEXt que le backend écrit dans le fichier (relu et comparé à /NE PAS IMPRIMER/)"),
    L(F, 7631, '"tEXt du fichier, relu ici"', "cartes.frame3.text_relu", "tEXt du fichier, relu ici",
      "file tEXt, re-read here"),
    S(F, 7633, ECRAN_AV, ECRAN_AP, COL_ECRAN),
    S(F, 7634, HD_AV, HD_AP, COL_HD),
    S(F, 7638,
      J('bad ? (bad + " écart(s) sur " + rows.length)',
        '      : ((vieux ? "périmée depuis " : ICO("dz-etat-succes", 16, "cf-ic") + rows.length + " lignes vérifiées sur les octets · ")',
        '        + hms(C.at))'),
      J('bad ? dzT("cartes.frame3.ecarts_sur", { n: bad, total: rows.length })',
        '      : (vieux ? dzT("cartes.frame3.perimee_depuis", { at: hms(C.at) })',
        '        : ICO("dz-etat-succes", 16, "cf-ic") + dzT("cartes.frame3.lignes_verifiees_octets", { n: rows.length, at: hms(C.at) }))'),
      {"cartes.frame3.ecarts_sur": ("{n} écart(s) sur {total}", "{n} mismatch(es) out of {total}"),
       **PERIMEE, **LIGNES_OCTETS}),
    S(F, 7641,
      J('"Empreinte mesurée : " + C.sig + (C.auto ? " · départ automatique" : "")',
        '      + (vieux ? " — le document a changé depuis." : "")'),
      J('dzT("cartes.frame3.empreinte_mesuree", { sig: C.sig }) + (C.auto ? dzT("cartes.frame3.sep_depart_auto") : "")',
        '      + (vieux ? dzT("cartes.frame3.doc_change_depuis") : "")'),
      {"cartes.frame3.empreinte_mesuree": ("Empreinte mesurée : {sig}", "Measured fingerprint: {sig}"),
       **SEP_AUTO,
       "cartes.frame3.doc_change_depuis": (" — le document a changé depuis.", " — the document has changed since.")}),
    S(F, 7644,
      J('"Épreuve de <b>" + C.octets.toLocaleString("fr-FR") + " octets</b>, "',
        '      + C.w + " x " + C.h + " px. <b>Ce n\'est pas le fichier d\'impression</b> : elle porte du papier "',
        '      + "en plus. Le fichier d\'impression, lui, ne porte aucun repère — du trait de coupe au bord de "',
        '      + "toile il n\'y a que du <b>fond perdu</b>, et un repère y serait de l\'encre sous la lame."'),
      'dzT("cartes.frame3.ctrl_lu", { octets: C.octets.toLocaleString("fr-FR"), w: C.w, h: C.h })',
      {"cartes.frame3.ctrl_lu": (
          "Épreuve de <b>{octets} octets</b>, {w} x {h} px. <b>Ce n'est pas le fichier d'impression</b> : elle porte "
          "du papier en plus. Le fichier d'impression, lui, ne porte aucun repère — du trait de coupe au bord de toile "
          "il n'y a que du <b>fond perdu</b>, et un repère y serait de l'encre sous la lame.",
          "<b>{octets}-byte</b> proof, {w} x {h} px. <b>This is not the print file</b>: it carries extra paper. The "
          "print file carries no marks at all — from the cut line to the canvas edge there is only <b>bleed</b>, and "
          "a mark there would be ink under the blade.")}),

    # ── vérification par le backend ────────────────────────────────────────────────────────────────
    L(F, 7667, '"réponse vide"', "cartes.frame3.reponse_vide", "réponse vide", "empty response"),
    S(F, 7670, 'k + " écran=" + JSON.stringify(local[k]) + " backend=" + JSON.stringify(b[k])',
      'dzT("cartes.frame3.ecart_ecran_backend", { k: k, ecran: JSON.stringify(local[k]), backend: JSON.stringify(b[k]) })',
      {"cartes.frame3.ecart_ecran_backend": ("{k} écran={ecran} backend={backend}", "{k} screen={ecran} backend={backend}")}),
    S(F, 7691, '"occupation écran≠backend (" + mine.count + " vs " + back.count + " recouvrement(s))"',
      'dzT("cartes.frame3.occupation_diverge", { a: mine.count, b: back.count })',
      {"cartes.frame3.occupation_diverge": ("occupation écran≠backend ({a} vs {b} recouvrement(s))",
                                            "screen≠backend occupancy ({a} vs {b} overlap(s))")}),
    S(F, 7695, '"divergence : " + bad[0]', 'dzT("cartes.frame3.divergence", { d: bad[0] })',
      {"cartes.frame3.divergence": ("divergence : {d}", "mismatch: {d}")}),
    L(F, 7699, '"filets + occupation vérifiés par le backend"', "cartes.frame3.verifies_backend",
      "filets + occupation vérifiés par le backend", "rules + occupancy verified by the backend"),
    L(F, 7700, '"POST /api/cards/<did>/frame/metrics et /occupancy — mêmes millimètres, mêmes pixels, mêmes boîtes réservées"',
      "cartes.frame3.verifies_titre",
      "POST /api/cards/<did>/frame/metrics et /occupancy — mêmes millimètres, mêmes pixels, mêmes boîtes réservées",
      "POST /api/cards/<did>/frame/metrics and /occupancy — same millimetres, same pixels, same reserved boxes"),
    L(F, 7704, '"hors ligne — dessin local"', "cartes.frame3.hors_ligne", "hors ligne — dessin local",
      "offline — local drawing"),
    L(F, 7704, '"vérification indisponible"', "cartes.frame3.verif_indispo", "vérification indisponible",
      "verification unavailable"),

    # ── la ligne du Sceau ──────────────────────────────────────────────────────────────────────────
    S(F, 7745,
      J('"Sceau <b>éteint</b> — le cadre est rendu exactement comme sans ce "',
        '        + "réglage, et le fichier livré n\'a pas un pixel de différence."'),
      'dzT("cartes.frame3.sceau_eteint")',
      {"cartes.frame3.sceau_eteint": (
          "Sceau <b>éteint</b> — le cadre est rendu exactement comme sans ce réglage, et le fichier livré n'a pas un "
          "pixel de différence.",
          "Seal <b>off</b> — the frame renders exactly as without this setting, and the delivered file does not "
          "differ by a single pixel.")}),
    L(F, 7750, '"écran"', "cartes.frame3.portee_ecran", "écran", "screen"),
    L(F, 7751, '"impression"', "cartes.frame3.portee_impression", "impression", "print"),
    S(F, 7757,
      J('"Portée déclarée : <b>" + (act.length ? esc(act.join(" + ")) : "aucune")',
        '      + "</b>. "'),
      'dzT("cartes.frame3.portee_declaree", { liste: act.length ? esc(act.join(" + ")) : dzT("cartes.frame3.aucune") })',
      {"cartes.frame3.portee_declaree": ("Portée déclarée : <b>{liste}</b>. ", "Declared scope: <b>{liste}</b>. "),
       "cartes.frame3.aucune": ("aucune", "none")}),
    S(F, 7759,
      J('("Cet écran montre la surface <b>écran</b>, DANS la portée : contour "',
        '          + "arc-en-ciel à la <b>phase canonique " + SEAL_PHASE + "</b> — l\'aperçu "',
        '          + "EST le fichier livré, au pixel.")'),
      'dzT("cartes.frame3.sceau_dans_portee", { phase: SEAL_PHASE })',
      {"cartes.frame3.sceau_dans_portee": (
          "Cet écran montre la surface <b>écran</b>, DANS la portée : contour arc-en-ciel à la <b>phase canonique "
          "{phase}</b> — l'aperçu EST le fichier livré, au pixel.",
          "This screen shows the <b>screen</b> surface, INSIDE the scope: rainbow outline at the <b>canonical phase "
          "{phase}</b> — the preview IS the delivered file, to the pixel.")}),
    S(F, 7762,
      J('("Cet écran montre la surface <b>écran</b>, HORS de la portée : le contour "',
        '          + "y reste dans sa <b>base calme</b> (" + esc(kind.toLowerCase())',
        '          + "), sans arc-en-ciel.")'),
      'dzT("cartes.frame3.sceau_hors_portee", { kind: esc(kind.toLowerCase()) })',
      {"cartes.frame3.sceau_hors_portee": (
          "Cet écran montre la surface <b>écran</b>, HORS de la portée : le contour y reste dans sa <b>base calme</b> "
          "({kind}), sans arc-en-ciel.",
          "This screen shows the <b>screen</b> surface, OUTSIDE the scope: the outline stays in its <b>calm base</b> "
          "({kind}), with no rainbow.")}),
    S(F, 7769,
      J('(" Entre le filet extérieur et la fenêtre d\'illustration, ce réglage "',
        '          + "ne laisse pas les <b>" + SEAL_MIN_MM + " mm</b> qu\'un imprimeur foil "',
        '          + "exige : <b>aucun contour n\'est dessiné</b>. Rapprocher le filet de "',
        '          + "la coupe (retrait) ou reculer la fenêtre.")'),
      'dzT("cartes.frame3.sceau_sans_place", { min: SEAL_MIN_MM })',
      {"cartes.frame3.sceau_sans_place": (
          " Entre le filet extérieur et la fenêtre d'illustration, ce réglage ne laisse pas les <b>{min} mm</b> "
          "qu'un imprimeur foil exige : <b>aucun contour n'est dessiné</b>. Rapprocher le filet de la coupe "
          "(retrait) ou reculer la fenêtre.",
          " Between the outer rule and the art window, this setting does not leave the <b>{min} mm</b> a foil "
          "printer requires: <b>no outline is drawn</b>. Move the rule closer to the cut (inset) or pull the window "
          "back.")}),
    S(F, 7773,
      J('" Bande de <b>" + r2(swid) + " mm</b> (" + r1(swid / 25.4 * g.dpi)',
        '          + " px), posée à <b>" + r2(Math.min(f0.edge_mm, cap))',
        '          + " mm</b> de la coupe (l\'axe du filet extérieur) et creusée vers l\'intérieur"'),
      J('dzT("cartes.frame3.sceau_bande", { mm: r2(swid), px: r1(swid / 25.4 * g.dpi),',
        '          pose: r2(Math.min(f0.edge_mm, cap)) })'),
      {"cartes.frame3.sceau_bande": (
          " Bande de <b>{mm} mm</b> ({px} px), posée à <b>{pose} mm</b> de la coupe (l'axe du filet extérieur) et "
          "creusée vers l'intérieur",
          " Band of <b>{mm} mm</b> ({px} px), placed <b>{pose} mm</b> from the cut (the outer rule's axis) and "
          "cut inwards")}),
    S(F, 7777,
      J('(" — ramenée de " + r2(s.width_mm) + " mm par la <b>borne du format</b> : "',
        '              + "au-delà, l\'anneau mordrait sur la fenêtre d\'illustration.")'),
      'dzT("cartes.frame3.sceau_ramenee", { mm: r2(s.width_mm) })',
      {"cartes.frame3.sceau_ramenee": (
          " — ramenée de {mm} mm par la <b>borne du format</b> : au-delà, l'anneau mordrait sur la fenêtre "
          "d'illustration.",
          " — reduced from {mm} mm by the <b>format limit</b>: beyond it, the ring would bite into the art window.")}),

    # ── adopter la bordure ─────────────────────────────────────────────────────────────────────────
    L(F, 7800, '"Bordure importée"', "cartes.frame3.bordure_importee", "Bordure importée", "Imported border"),
    L(F, 7801, '"mesurée par l\'import"', "cartes.frame3.mesuree_import", "mesurée par l'import", "measured by the import"),
    S(F, 7801, '"confiance " + nb2(bo.confidence)', 'dzT("cartes.frame3.confiance", { n: nb2(bo.confidence) })',
      {"cartes.frame3.confiance": ("confiance {n}", "confidence {n}")}),
    L(F, 7803, '"Adopter la bordure"', "cartes.frame3.adopter", "Adopter la bordure", "Adopt border"),
    S(F, 7805,
      J('"Pose la famille la plus proche et les réglages MESURÉS "',
        '      + "(bande, couleur, rayon) — un seul pas d\'annulation"'),
      'dzT("cartes.frame3.adopter_titre")',
      {"cartes.frame3.adopter_titre": (
          "Pose la famille la plus proche et les réglages MESURÉS (bande, couleur, rayon) — un seul pas d'annulation",
          "Applies the closest family and the MEASURED settings (band, colour, radius) — a single undo step")}),
    L(F, 7812, '"aucune bordure mesurée à adopter"', "cartes.frame3.aucune_bordure", "aucune bordure mesurée à adopter",
      "no measured border to adopt"),
    L(F, 7814, '"bordure adoptée"', "cartes.frame3.bordure_adoptee", "bordure adoptée", "border adopted"),
    S(F, 7815, '"bordure adoptée — " + a1.ecart + a1.precisions',
      'dzT("cartes.frame3.toast_adoptee", { d: a1.ecart + a1.precisions })',
      {"cartes.frame3.toast_adoptee": ("bordure adoptée — {d}", "border adopted — {d}")}),

    # ── syncNow ────────────────────────────────────────────────────────────────────────────────────
    S(F, 7839,
      J('"<b>" + (FAMILIES.length * RARITIES.length) + "</b> combinaisons"',
        '      + " <i>(</i>" + FAMILIES.length + " familles <i>x</i> " + RARITIES.length + " raretés<i>)</i>"'),
      'dzT("cartes.frame3.combinaisons", { n: FAMILIES.length * RARITIES.length, f: FAMILIES.length, r: RARITIES.length })',
      {"cartes.frame3.combinaisons": ("<b>{n}</b> combinaisons <i>(</i>{f} familles <i>x</i> {r} raretés<i>)</i>",
                                      "<b>{n}</b> combinations <i>(</i>{f} families <i>x</i> {r} rarities<i>)</i>")}),
    L(F, 7841, '"aucun cadre"', "cartes.frame3.aucun_cadre", "aucun cadre", "no frame"),
    S(F, 7843,
      J('" <i>·</i> toile <b>" + g.canvas_px[0] + " x " + g.canvas_px[1] + "</b> px calculée pour "',
        '      + g.dpi + " DPI <i>·</i> le fichier porte <b>" + ppm(g.dpi) + " px/m = "',
        '      + dpiOf(ppm(g.dpi)) + " DPI</b>"'),
      J('dzT("cartes.frame3.toile_calculee", { w: g.canvas_px[0], h: g.canvas_px[1], dpi: g.dpi,',
        '        ppm: ppm(g.dpi), reel: dpiOf(ppm(g.dpi)) })'),
      {"cartes.frame3.toile_calculee": (
          " <i>·</i> toile <b>{w} x {h}</b> px calculée pour {dpi} DPI <i>·</i> le fichier porte <b>{ppm} px/m = "
          "{reel} DPI</b>",
          " <i>·</i> canvas <b>{w} x {h}</b> px computed for {dpi} DPI <i>·</i> the file carries <b>{ppm} px/m = "
          "{reel} DPI</b>")}),
    S(F, 7846,
      J('"pHYs compte des pixels par MÈTRE entiers : 300 DPI exact n\'y est pas "',
        '      + "représentable. " + ppm(g.dpi) + " px/m est la valeur entière la plus proche, soit "',
        '      + dpiOf(ppm(g.dpi)) + " DPI — un écart de "',
        '      + r2(Math.abs(dpiOf(ppm(g.dpi)) - g.dpi) / g.dpi * 100 * 1000) + " millionièmes. On l\'écrit."'),
      J('dzT("cartes.frame3.count_titre", { ppm: ppm(g.dpi), reel: dpiOf(ppm(g.dpi)),',
        '        e: r2(Math.abs(dpiOf(ppm(g.dpi)) - g.dpi) / g.dpi * 100 * 1000) })'),
      {"cartes.frame3.count_titre": (
          "pHYs compte des pixels par MÈTRE entiers : 300 DPI exact n'y est pas représentable. {ppm} px/m est la "
          "valeur entière la plus proche, soit {reel} DPI — un écart de {e} millionièmes. On l'écrit.",
          "pHYs counts whole pixels per METRE: an exact 300 DPI cannot be represented. {ppm} px/m is the nearest "
          "whole value, i.e. {reel} DPI — a difference of {e} millionths. We say so.")}),
    L(F, 7854, '"Annuler"', "cartes.frame3.annuler", "Annuler", "Undo", contexte=True),
    L(F, 7873, '" (borne du format)"', "cartes.frame3.borne_format", " (borne du format)", " (format limit)"),
    S(F, 7875,
      J('"Le curseur va jusqu\'à " + LIMITS[row.key][1] + " mm, mais sur "',
        '            + g.fmt + " (" + r2(g.trim_mm[0]) + " x " + r2(g.trim_mm[1])',
        '            + " mm) au-delà de " + r2(cap) + " mm la bande garderait moins de "',
        '            + BAND_MIN_MM + " mm d\'ouverture — elle s\'inverserait. Le dessin, "',
        '            + "le modèle d\'occupation et le backend appliquent tous les trois "',
        '            + "cette borne : le nombre affiché est celui qui est tracé."'),
      J('dzT("cartes.frame3.borne_titre", { max: LIMITS[row.key][1], fmt: g.fmt, w: r2(g.trim_mm[0]),',
        '            h: r2(g.trim_mm[1]), cap: r2(cap), min: BAND_MIN_MM })'),
      {"cartes.frame3.borne_titre": (
          "Le curseur va jusqu'à {max} mm, mais sur {fmt} ({w} x {h} mm) au-delà de {cap} mm la bande garderait "
          "moins de {min} mm d'ouverture — elle s'inverserait. Le dessin, le modèle d'occupation et le backend "
          "appliquent tous les trois cette borne : le nombre affiché est celui qui est tracé.",
          "The slider goes up to {max} mm, but on {fmt} ({w} x {h} mm) beyond {cap} mm the band would keep less "
          "than {min} mm of opening — it would flip. The drawing, the occupancy model and the backend all apply "
          "this limit: the number shown is the one that is drawn.")}),
    S(F, 7887,
      J('"Convention du <b>trait centré</b> : la valeur porte l\'<b>axe</b>. "',
        '      + "Avec un filet de " + r2(f0.line_mm) + " mm, l\'encre occupe de <b>" + r2(eOut) + " mm</b> ("',
        '      + px1(eOut) + " px) à <b>" + r2(eIn) + " mm</b> (" + px1(eIn) + " px) depuis le trait de coupe"'),
      J('dzT("cartes.frame3.edge_convention", { line: r2(f0.line_mm), ext: r2(eOut), extpx: px1(eOut),',
        '        int: r2(eIn), intpx: px1(eIn) })'),
      {"cartes.frame3.edge_convention": (
          "Convention du <b>trait centré</b> : la valeur porte l'<b>axe</b>. Avec un filet de {line} mm, l'encre "
          "occupe de <b>{ext} mm</b> ({extpx} px) à <b>{int} mm</b> ({intpx} px) depuis le trait de coupe",
          "<b>Centred stroke</b> convention: the value sets the <b>axis</b>. With a {line} mm rule, the ink spans "
          "<b>{ext} mm</b> ({extpx} px) to <b>{int} mm</b> ({intpx} px) from the cut line")}),
    L(F, 7890, '" — <b>le filet mord sur le fond perdu</b> : la coupe passe dedans."', "cartes.frame3.edge_mord",
      " — <b>le filet mord sur le fond perdu</b> : la coupe passe dedans.",
      " — <b>the rule bites into the bleed</b>: the cut runs through it."),
    S(F, 7891,
      J('" · axe à " + r2(capE) + " mm = " + px1(capE) + " px de la coupe, soit "',
        '      + r1(g.bleed_off_px[0] + capE / 25.4 * g.dpi) + " px du bord de <b>toile</b>."'),
      'dzT("cartes.frame3.edge_axe", { mm: r2(capE), px: px1(capE), toile: r1(g.bleed_off_px[0] + capE / 25.4 * g.dpi) })',
      {"cartes.frame3.edge_axe": (" · axe à {mm} mm = {px} px de la coupe, soit {toile} px du bord de <b>toile</b>.",
                                  " · axis at {mm} mm = {px} px from the cut, i.e. {toile} px from the <b>canvas</b> edge.")}),
    S(F, 7901,
      J('" Le fond de l\'anneau garde le <b>même ton</b> de part et d\'autre du trait de coupe : "',
        '      + "si la lame passe à ± " + TOL_COUPE_MM + " mm, le bord de la carte a le même aspect "',
        '      + "et l\'arête du filet reste la seule de la zone."'),
      'dzT("cartes.frame3.edge_ton", { tol: TOL_COUPE_MM })',
      {"cartes.frame3.edge_ton": (
          " Le fond de l'anneau garde le <b>même ton</b> de part et d'autre du trait de coupe : si la lame passe à "
          "± {tol} mm, le bord de la carte a le même aspect et l'arête du filet reste la seule de la zone.",
          " The ring background keeps the <b>same tone</b> on both sides of the cut line: if the blade lands "
          "± {tol} mm off, the card edge looks the same and the rule's edge remains the only one in the area.")}),
    S(F, 7907,
      J('" <b>Attention</b> : sur cette carte, une couche posée par-dessus le cadre "',
        '          + "(texte ou illustration) déborde du trait de coupe."'),
      'dzT("cartes.frame3.edge_attention")',
      {"cartes.frame3.edge_attention": (
          " <b>Attention</b> : sur cette carte, une couche posée par-dessus le cadre (texte ou illustration) déborde "
          "du trait de coupe.",
          " <b>Warning</b>: on this card, a layer placed over the frame (text or art) spills past the cut line.")}),
    L(F, 7920, '" (borne du format)"', "cartes.frame3.borne_format", " (borne du format)", " (format limit)"),
    S(F, 7967, '"Fenêtre " + (w.auto ? "<b>automatique</b> (proportionnelle au format)" : "<b>manuelle</b>")',
      J('dzT("cartes.frame3.fenetre_mode", { mode: w.auto ? dzT("cartes.frame3.fenetre_auto")',
        '      : dzT("cartes.frame3.fenetre_manuelle") })'),
      {"cartes.frame3.fenetre_mode": ("Fenêtre {mode}", "Window: {mode}"),
       "cartes.frame3.fenetre_auto": ("<b>automatique</b> (proportionnelle au format)",
                                      "<b>automatic</b> (proportional to the format)"),
       "cartes.frame3.fenetre_manuelle": ("<b>manuelle</b>", "<b>manual</b>")}),
    S(F, 7969, '" · rayon de fenêtre " + r2(w.r) + " mm = " + r1(wpx[4]) + " px"',
      'dzT("cartes.frame3.rayon_fenetre", { mm: r2(w.r), px: r1(wpx[4]) })',
      {"cartes.frame3.rayon_fenetre": (" · rayon de fenêtre {mm} mm = {px} px", " · window radius {mm} mm = {px} px")}),
    S(F, 7970, '" · forme " + esc(WIN_SHAPE[f0.family] || "rect")',
      'dzT("cartes.frame3.forme", { f: esc(WIN_SHAPE[f0.family] || "rect") })',
      {"cartes.frame3.forme": (" · forme {f}", " · shape {f}")}),
    S(F, 7978,
      J('"<br><b>Rayon de coupe</b> " + r2(g.corner_mm) + " mm = <b>" + r1(g.corner_px) + " px</b>"',
        '      + " <i>(l\'arrondi des quatre coins de la carte)</i>"',
        '      + " · <b>Décalage du fond perdu</b> " + r2(g.bleed_mm) + " mm = <b>" + r2(g.bleed_off_px[0]) + " x " + r2(g.bleed_off_px[1]) + " px</b>"',
        '      + " <i>(l\'encre en plus autour de la rogne, sur les quatre côtés)</i>"',
        '      + " · <b>Zone sûre</b> " + r2(g.safe_mm) + " mm = <b>" + g.safe_px[0] + " x " + g.safe_px[1] + " px</b> à "',
        '      + r2(g.safe_off_px[0]) + " x " + r2(g.safe_off_px[1]) + " px de la toile"'),
      J('dzT("cartes.frame3.win_geom", { cmm: r2(g.corner_mm), cpx: r1(g.corner_px),',
        '        bmm: r2(g.bleed_mm), bx: r2(g.bleed_off_px[0]), by: r2(g.bleed_off_px[1]),',
        '        smm: r2(g.safe_mm), sw: g.safe_px[0], sh: g.safe_px[1], sx: r2(g.safe_off_px[0]), sy: r2(g.safe_off_px[1]) })'),
      {"cartes.frame3.win_geom": (
          "<br><b>Rayon de coupe</b> {cmm} mm = <b>{cpx} px</b> <i>(l'arrondi des quatre coins de la carte)</i> · "
          "<b>Décalage du fond perdu</b> {bmm} mm = <b>{bx} x {by} px</b> <i>(l'encre en plus autour de la rogne, "
          "sur les quatre côtés)</i> · <b>Zone sûre</b> {smm} mm = <b>{sw} x {sh} px</b> à {sx} x {sy} px de la toile",
          "<br><b>Corner radius</b> {cmm} mm = <b>{cpx} px</b> <i>(the rounding of the card's four corners)</i> · "
          "<b>Bleed offset</b> {bmm} mm = <b>{bx} x {by} px</b> <i>(the extra ink around the trim, on all four "
          "sides)</i> · <b>Safe zone</b> {smm} mm = <b>{sw} x {sh} px</b> at {sx} x {sy} px from the canvas")}),
    S(F, 8045,
      J('"Bandeau <b>éteint ou sans texte</b> — la case "',
        '        + "« Bandeau » et un nom de rareté le rallument."'),
      'dzT("cartes.frame3.ban_eteint")',
      {"cartes.frame3.ban_eteint": (
          "Bandeau <b>éteint ou sans texte</b> — la case « Bandeau » et un nom de rareté le rallument.",
          "Banner <b>off or without text</b> — the “Banner” box and a rarity name turn it back on.")}),
    S(F, 8048,
      J('"Bandeau <b>posé à la main</b> — coin "',
        '        + r2(bnb.box[0]) + " x " + r2(bnb.box[1]) + " mm"',
        '        + " · il ne cherche plus de voie libre : le compteur d\'occupation"',
        '        + " ci-dessus dit ce que cela coûte. <b>Auto</b> le rend au calcul."'),
      'dzT("cartes.frame3.ban_main", { x: r2(bnb.box[0]), y: r2(bnb.box[1]) })',
      {"cartes.frame3.ban_main": (
          "Bandeau <b>posé à la main</b> — coin {x} x {y} mm · il ne cherche plus de voie libre : le compteur "
          "d'occupation ci-dessus dit ce que cela coûte. <b>Auto</b> le rend au calcul.",
          "Banner <b>placed by hand</b> — corner {x} x {y} mm · it no longer looks for a free lane: the occupancy "
          "counter above shows what that costs. <b>Auto</b> hands it back to the layout.")}),
    S(F, 8053,
      J('"Bandeau <b>automatique</b> — " + esc(bnb.lane)',
        '        + ", coin " + r2(bnb.box[0]) + " x " + r2(bnb.box[1]) + " mm."'),
      'dzT("cartes.frame3.ban_auto", { lane: esc(bnb.lane), x: r2(bnb.box[0]), y: r2(bnb.box[1]) })',
      {"cartes.frame3.ban_auto": ("Bandeau <b>automatique</b> — {lane}, coin {x} x {y} mm.",
                                  "Banner <b>automatic</b> — {lane}, corner {x} x {y} mm.")}),
    L(F, 8057, '"Gemme <b>éteinte</b> — la case « Gemme de rareté » la rallume."', "cartes.frame3.gem_eteinte",
      "Gemme <b>éteinte</b> — la case « Gemme de rareté » la rallume.",
      "Gem <b>off</b> — the “Rarity gem” box turns it back on."),
    S(F, 8059,
      J('"Gemme <b>posée à la main</b> — centre "',
        '        + r2(gmb.cx) + " x " + r2(gmb.cy) + " mm, rayon " + r2(gmb.r) + " mm"',
        '        + " · elle n\'essaie plus les quatre coins et ne se range plus en écrin"',
        '        + " sous une mention : le compteur d\'occupation ci-dessus dit ce que"',
        '        + " cela coûte. <b>Auto</b> (ou un double-clic sur le plan) la rend au calcul."'),
      'dzT("cartes.frame3.gem_main", { x: r2(gmb.cx), y: r2(gmb.cy), r: r2(gmb.r) })',
      {"cartes.frame3.gem_main": (
          "Gemme <b>posée à la main</b> — centre {x} x {y} mm, rayon {r} mm · elle n'essaie plus les quatre coins et "
          "ne se range plus en écrin sous une mention : le compteur d'occupation ci-dessus dit ce que cela coûte. "
          "<b>Auto</b> (ou un double-clic sur le plan) la rend au calcul.",
          "Gem <b>placed by hand</b> — centre {x} x {y} mm, radius {r} mm · it no longer tries the four corners or "
          "tucks into a setting under a text slot: the occupancy counter above shows what that costs. <b>Auto</b> "
          "(or a double-click on the map) hands it back to the layout.")}),
    S(F, 8065,
      J('"Gemme <b>automatique</b> — " + esc(gmb.lane)',
        '        + ", centre " + r2(gmb.cx) + " x " + r2(gmb.cy) + " mm, rayon "',
        '        + r2(gmb.r) + " mm · glissez-la sur le plan pour la poser à la main."'),
      'dzT("cartes.frame3.gem_auto", { lane: esc(gmb.lane), x: r2(gmb.cx), y: r2(gmb.cy), r: r2(gmb.r) })',
      {"cartes.frame3.gem_auto": (
          "Gemme <b>automatique</b> — {lane}, centre {x} x {y} mm, rayon {r} mm · glissez-la sur le plan pour la "
          "poser à la main.",
          "Gem <b>automatic</b> — {lane}, centre {x} x {y} mm, radius {r} mm · drag it on the map to place it by "
          "hand.")}),

    # ── compteur d'occupation, table, estampille ───────────────────────────────────────────────────
    S(F, 8093, '(n + " recouvrement" + (n > 1 ? "s" : "") + " de mention")',
      '(n > 1 ? dzT("cartes.frame3.recouvrement_plusieurs", { n: n }) : dzT("cartes.frame3.recouvrement_un", { n: n }))',
      {"cartes.frame3.recouvrement_plusieurs": ("{n} recouvrements de mention", "{n} text-slot overlaps"),
       "cartes.frame3.recouvrement_un": ("{n} recouvrement de mention", "{n} text-slot overlap")}),
    L(F, 8094, '"0 recouvrement de mention"', "cartes.frame3.recouvrement_zero", "0 recouvrement de mention",
      "0 text-slot overlaps"),
    S(F, 8096, 'c.a + " recouvre " + c.b + " sur " + c.mm2 + " mm² (" + c.pct + " % de la mention)"',
      'dzT("cartes.frame3.recouvre_detail", { a: c.a, b: c.b, mm2: c.mm2, pct: c.pct })',
      {"cartes.frame3.recouvre_detail": ("{a} recouvre {b} sur {mm2} mm² ({pct} % de la mention)",
                                         "{a} overlaps {b} over {mm2} mm² ({pct} % of the text slot)")}),
    L(F, 8097, '"Aucun meuble de la couche 70 ne recouvre une mention de doc.type.slots — mesuré en mm² sur les boîtes réservées"',
      "cartes.frame3.aucun_recouvrement",
      "Aucun meuble de la couche 70 ne recouvre une mention de doc.type.slots — mesuré en mm² sur les boîtes réservées",
      "No layer-70 element overlaps a doc.type.slots text slot — measured in mm² on the reserved boxes"),
    S(F, 8107,
      "'<div class=\"cff-occhd\"><span>meuble</span><span>couche</span><span>place</span><span>boîte (mm depuis la coupe)</span><span>en px</span></div>'",
      "'<div class=\"cff-occhd\"><span>' + dzT(\"cartes.frame3.col_meuble\") + '</span><span>' + dzT(\"cartes.frame3.col_couche\")"
      " + '</span><span>' + dzT(\"cartes.frame3.col_place\") + '</span><span>' + dzT(\"cartes.frame3.col_boite\")"
      " + '</span><span>' + dzT(\"cartes.frame3.col_px\") + '</span></div>'",
      {"cartes.frame3.col_meuble": ("meuble", "element"),
       "cartes.frame3.col_couche": ("couche", "layer"),
       "cartes.frame3.col_place": ("place", "position"),
       "cartes.frame3.col_boite": ("boîte (mm depuis la coupe)", "box (mm from the cut)"),
       "cartes.frame3.col_px": ("en px", "in px")}),
    S(F, 8113, '"</span><span>recouvre</span><span>"', '"</span><span>" + dzT("cartes.frame3.recouvre") + "</span><span>"',
      {"cartes.frame3.recouvre": ("recouvre", "overlaps")}),
    S(F, 8114, 'c.pct + " % de la mention</span></div>"',
      'dzT("cartes.frame3.pct_de_mention", { pct: c.pct }) + "</span></div>"',
      {"cartes.frame3.pct_de_mention": ("{pct} % de la mention", "{pct} % of the text slot")}),
    S(F, 8115,
      J('"<b>" + plan.mentions.length + "</b> mention" + (plan.mentions.length > 1 ? "s" : "")',
        '      + " lue" + (plan.mentions.length > 1 ? "s" : "") + " dans <b>doc.type.slots</b> (pièce 03) · "',
        '      + "<b>" + plan.socles + "</b> socle" + (plan.socles > 1 ? "s" : "") + " · <b>" + plan.seats + "</b> logement"',
        '      + (plan.seats > 1 ? "s" : "")',
        '      + " · les meubles de la couche <b>40</b> passent sous le texte, ceux de la couche <b>70</b> par-dessus — "',
        '      + "seuls ces derniers peuvent masquer une mention, et c\'est eux que compte le badge."'),
      J('(plan.mentions.length > 1 ? dzT("cartes.frame3.mentions_plusieurs", { n: plan.mentions.length })',
        '        : dzT("cartes.frame3.mentions_un", { n: plan.mentions.length })) + " · "',
        '      + (plan.socles > 1 ? dzT("cartes.frame3.socles_plusieurs", { n: plan.socles })',
        '        : dzT("cartes.frame3.socles_un", { n: plan.socles })) + " · "',
        '      + (plan.seats > 1 ? dzT("cartes.frame3.logements_plusieurs", { n: plan.seats })',
        '        : dzT("cartes.frame3.logements_un", { n: plan.seats }))',
        '      + dzT("cartes.frame3.couches_40_70")'),
      {"cartes.frame3.mentions_plusieurs": ("<b>{n}</b> mentions lues dans <b>doc.type.slots</b> (pièce 03)",
                                            "<b>{n}</b> text slots read from <b>doc.type.slots</b> (part 03)"),
       "cartes.frame3.mentions_un": ("<b>{n}</b> mention lue dans <b>doc.type.slots</b> (pièce 03)",
                                     "<b>{n}</b> text slot read from <b>doc.type.slots</b> (part 03)"),
       "cartes.frame3.socles_plusieurs": ("<b>{n}</b> socles", "<b>{n}</b> bases"),
       "cartes.frame3.socles_un": ("<b>{n}</b> socle", "<b>{n}</b> base"),
       "cartes.frame3.logements_plusieurs": ("<b>{n}</b> logements", "<b>{n}</b> seats"),
       "cartes.frame3.logements_un": ("<b>{n}</b> logement", "<b>{n}</b> seat"),
       "cartes.frame3.couches_40_70": (
           " · les meubles de la couche <b>40</b> passent sous le texte, ceux de la couche <b>70</b> par-dessus — "
           "seuls ces derniers peuvent masquer une mention, et c'est eux que compte le badge.",
           " · layer <b>40</b> elements go under the text, layer <b>70</b> ones on top — only the latter can hide a "
           "text slot, and they are what the badge counts.")}),
    S(F, 8126,
      J('"Le PNG livré porte <b>pHYs " + ppm(g.dpi) + " px/m</b> (soit <b>"',
        '      + dpiOf(ppm(g.dpi)) + " DPI</b> réels — " + g.dpi + " DPI n\'est pas représentable en pixels par "',
        '      + "mètre entiers, et c\'est la valeur entière la plus proche) et les "',
        '      + "<b>tEXt</b> <i>Software · Format · Resolution · BleedBox · TrimBox · SafeBox · Face · "',
        '      + "Collisions · Comment · Alpha</i> — BleedBox " + g.canvas_px[0] + "x" + g.canvas_px[1]',
        '      + " px, TrimBox " + g.trim_px[0] + "x" + g.trim_px[1] + " px à " + r2(g.bleed_off_px[0]) + "," + r2(g.bleed_off_px[1])',
        '      + " px, SafeBox " + g.safe_px[0] + "x" + g.safe_px[1] + " px. "',
        '      + "Le backend relit IHDR avant d\'estampiller : une toile qui ne fait pas " + g.canvas_px[0] + "x" + g.canvas_px[1]',
        '      + " px est <b>refusée</b>, jamais estampillée d\'une définition fausse."'),
      J('dzT("cartes.frame3.stamp_lu", { ppm: ppm(g.dpi), reel: dpiOf(ppm(g.dpi)), dpi: g.dpi,',
        '        cw: g.canvas_px[0], ch: g.canvas_px[1], tw: g.trim_px[0], th: g.trim_px[1],',
        '        tx: r2(g.bleed_off_px[0]), ty: r2(g.bleed_off_px[1]), sw: g.safe_px[0], sh: g.safe_px[1] })'),
      {"cartes.frame3.stamp_lu": (
          "Le PNG livré porte <b>pHYs {ppm} px/m</b> (soit <b>{reel} DPI</b> réels — {dpi} DPI n'est pas "
          "représentable en pixels par mètre entiers, et c'est la valeur entière la plus proche) et les <b>tEXt</b> "
          "<i>Software · Format · Resolution · BleedBox · TrimBox · SafeBox · Face · Collisions · Comment · Alpha</i> "
          "— BleedBox {cw}x{ch} px, TrimBox {tw}x{th} px à {tx},{ty} px, SafeBox {sw}x{sh} px. Le backend relit IHDR "
          "avant d'estampiller : une toile qui ne fait pas {cw}x{ch} px est <b>refusée</b>, jamais estampillée d'une "
          "définition fausse.",
          "The delivered PNG carries <b>pHYs {ppm} px/m</b> (i.e. <b>{reel} DPI</b> actual — {dpi} DPI cannot be "
          "represented in whole pixels per metre, and this is the nearest whole value) and the <b>tEXt</b> entries "
          "<i>Software · Format · Resolution · BleedBox · TrimBox · SafeBox · Face · Collisions · Comment · Alpha</i> "
          "— BleedBox {cw}x{ch} px, TrimBox {tw}x{th} px at {tx},{ty} px, SafeBox {sw}x{sh} px. The backend re-reads "
          "IHDR before stamping: a canvas that is not {cw}x{ch} px is <b>rejected</b>, never stamped with a wrong "
          "resolution.")}),
    S(F, 8141,
      J('"<br><b>Ce que ces boîtes ne sont pas.</b> La norme PNG ne prévoit <i>aucune</i> boîte de "',
        '      + "coupe : <b>pHYs</b> est le seul chunk qu\'une machine lira (la définition), les "',
        '      + "<b>tEXt</b> sont une indication <b>humaine</b> — et le contrôle de cet écran. Les boîtes "',
        '      + "<i>MediaBox / TrimBox / BleedBox</i> vraiment lues par un RIP n\'existent que dans un "',
        '      + "<b>PDF</b> : c\'est la planche de la pièce 07 qui les porte, pas ce PNG. "',
        '      + "Ce fichier-ci est une <b>carte</b>, pas une planche d\'imposition."'),
      'dzT("cartes.frame3.stamp_boites")',
      {"cartes.frame3.stamp_boites": (
          "<br><b>Ce que ces boîtes ne sont pas.</b> La norme PNG ne prévoit <i>aucune</i> boîte de coupe : "
          "<b>pHYs</b> est le seul chunk qu'une machine lira (la définition), les <b>tEXt</b> sont une indication "
          "<b>humaine</b> — et le contrôle de cet écran. Les boîtes <i>MediaBox / TrimBox / BleedBox</i> vraiment "
          "lues par un RIP n'existent que dans un <b>PDF</b> : c'est la planche de la pièce 07 qui les porte, pas ce "
          "PNG. Ce fichier-ci est une <b>carte</b>, pas une planche d'imposition.",
          "<br><b>What these boxes are not.</b> The PNG standard defines <i>no</i> trim box: <b>pHYs</b> is the only "
          "chunk a machine will read (the resolution); the <b>tEXt</b> entries are a <b>human</b> hint — and this "
          "screen's check. The <i>MediaBox / TrimBox / BleedBox</i> boxes a RIP really reads exist only in a "
          "<b>PDF</b>: part 07's sheet carries them, not this PNG. This file is a <b>card</b>, not an imposition "
          "sheet.")}),

    # ── raccourcis clavier : libellés d'historique (montrés par « annulé : … ») ──────────────────────
    L(F, 8174, '"famille"', "cartes.frame3.hist_famille", "famille", "family"),
    L(F, 8175, '"famille"', "cartes.frame3.hist_famille", "famille", "family"),
    L(F, 8176, '"rareté"', "cartes.frame3.hist_rarete", "rareté", "rarity"),
    L(F, 8177, '"rareté"', "cartes.frame3.hist_rarete", "rareté", "rarity"),
    L(F, 8178, '"double filet"', "cartes.frame3.hist_double", "double filet", "double line"),
    L(F, 8179, '"métal"', "cartes.frame3.hist_metal", "métal", "metal"),
    L(F, 8180, '"gemme"', "cartes.frame3.hist_gemme", "gemme", "gem"),
]
