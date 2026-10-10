"""t147 — data1 : js/mod-data.js lignes 1-2006 (piece 04 Donnees : import CSV/classeur, compteurs, controle du
mappage, provenance, filtre). Traduit : toasts, compteurs, pastilles, infobulles, phrases d'audit, menus de l'ecran.
GARDE : les libelles des slots de repli et des champs reserves (envoyes au moteur avec la table : /build et /suggest
confrontent l'id ET le libelle), les valeurs comparees (#qty, auto, separateurs), le contenu des cartes et des
CSV d'exemple, les gardes de chargement, les formats numeriques."""
from outils import L, S, X, H

PLAGES = {"js/mod-data.js": (1, 2006)}

F = "js/mod-data.js"


def C(s):
    """les sources sont en CRLF : un saut de ligne ecrit ici devient \\r\\n."""
    return s.replace("\n", "\r\n")


def K(cle):
    return "cartes.data1." + cle


ENTREES = [
    X(F, 28, '"mod-data: js/core.js doit etre charge avant ce fichier"', "garde de chargement"),
    X(F, 43, '"Coût"', "libellé de slot de repli envoyé au moteur (/build, /suggest confrontent id ET libellé)"),
    X(F, 47, '"Encadré de règles"', "libellé de slot de repli envoyé au moteur"),
    X(F, 48, '"Texte d\'ambiance"', "libellé de slot de repli envoyé au moteur"),
    X(F, 49, '"Numéro"', "libellé de slot de repli envoyé au moteur"),
    X(F, 42, '"Titre"', "libellé de slot de repli envoyé au moteur"),
    X(F, 44, '"Attaque"', "libellé de slot de repli envoyé au moteur"),
    X(F, 45, '"Vie"', "libellé de slot de repli envoyé au moteur"),
    X(F, 50, '"Artiste"', "libellé de slot de repli envoyé au moteur"),
    X(F, 56, '"▸ Illustration (card.art)"', "libellé de cible réservée envoyé au moteur avec les slots (slotPayload)"),
    X(F, 57, '"▸ Dos (card.back)"', "libellé de cible réservée envoyé au moteur avec les slots (slotPayload)"),
    X(F, 58, '"▸ Identifiant (card.id)"', "libellé de cible réservée envoyé au moteur avec les slots (slotPayload)"),
    X(F, 1897, '"nom"', "nom de colonne écrit dans la table du projet (contenu)"),
    X(F, 1897, '"pv"', "nom de colonne écrit dans la table du projet (contenu)"),
    L(F, 65, '"n° de copie"', K("v_copie"), "n° de copie", "copy no."),
    L(F, 65, '"1, 2, 3… dans la ligne"', K("v_copie_h"), "1, 2, 3… dans la ligne", "1, 2, 3… within the row"),
    L(F, 66, '"copies de la ligne"', K("v_copies"), "copies de la ligne", "copies of the row"),
    L(F, 66, '"la quantité de cette ligne"', K("v_copies_h"), "la quantité de cette ligne", "this row's quantity"),
    L(F, 67, '"n° de carte"', K("v_carte"), "n° de carte", "card no."),
    L(F, 67, '"1 … total du deck"', K("v_carte_h"), "1 … total du deck", "1 … deck total"),
    L(F, 68, '"total du deck"', K("v_total"), "total du deck", "deck total"),
    L(F, 68, '"le même sur toutes les cartes"', K("v_total_h"), "le même sur toutes les cartes", "the same on every card"),
    L(F, 86, '"virgule"', K("sep_virgule"), "virgule", "comma"),
    L(F, 87, '"point-virgule"', K("sep_pv"), "point-virgule", "semicolon"),
    L(F, 88, '"tabulation"', K("sep_tab"), "tabulation", "tab"),
    L(F, 89, '"barre"', K("sep_barre"), "barre", "pipe"),
    L(F, 281, '"rien à annuler"', K("rien_annuler"), "rien à annuler", "nothing to undo"),
    S(F, 285, '"annulé — " + UNDO.length + " étape(s) restante(s)"', 'dzT("cartes.data1.annule", { n: UNDO.length })',
      {K("annule"): ("annulé — {n} étape(s) restante(s)", "undone — {n} step(s) left")}),
    L(F, 288, '"rien à rétablir"', K("rien_retablir"), "rien à rétablir", "nothing to redo"),
    L(F, 406, '"backend /api/cards/…/data absent"', K("backend_absent"), "backend /api/cards/…/data absent",
      "backend /api/cards/…/data missing"),
    S(F, 439, '"lecture de " + (name || "la table") + "…"',
      'dzT("cartes.data1.lecture", { nom: name || dzT("cartes.data1.la_table") })',
      {K("lecture"): ("lecture de {nom}…", "reading {nom}…"), K("la_table"): ("la table", "the table")}),
    S(F, 496, C('''T.rows.length + " ligne(s) importée(s) en " + Math.round(ms) + " ms — "
        + (r.table.workbook ? (r.table.encoding_label || "classeur")
          : ("séparateur " + sepLabel(T.sep) + ", "
            + (r.table.encoding_label || r.table.encoding)))'''),
      C('''dzT("cartes.data1.importe", { n: T.rows.length, ms: Math.round(ms) })
        + (r.table.workbook ? (r.table.encoding_label || dzT("cartes.data1.classeur"))
          : (dzT("cartes.data1.separateur", { sep: sepLabel(T.sep) }) + ", "
            + (r.table.encoding_label || r.table.encoding)))'''),
      {K("importe"): ("{n} ligne(s) importée(s) en {ms} ms — ", "{n} row(s) imported in {ms} ms — "),
       K("classeur"): ("classeur", "workbook"),
       K("separateur"): ("séparateur {sep}", "{sep} separator")}),
    L(F, 510, '"réponse d\'analyse illisible"', K("reponse_illisible"), "réponse d'analyse illisible",
      "unreadable parse response"),
    S(F, 596, '<i class="cf-data-ml">lignes</i>\'', '<i class="cf-data-ml">\' + dzT("cartes.data1.m_lignes") + \'</i>\'',
      {K("m_lignes"): ("lignes", "rows", "contexte")}),
    S(F, 597, '<i class="cf-data-ml">retenues</i>\'', '<i class="cf-data-ml">\' + dzT("cartes.data1.m_retenues") + \'</i>\'',
      {K("m_retenues"): ("retenues", "kept")}),
    S(F, 598, '<i class="cf-data-ml">cartes</i>\'', '<i class="cf-data-ml">\' + dzT("cartes.data1.m_cartes") + \'</i>\'',
      {K("m_cartes"): ("cartes", "cards")}),
    S(F, 603, '<i class="cf-data-ml">slots au gabarit</i>\'', '<i class="cf-data-ml">\' + dzT("cartes.data1.m_gab") + \'</i>\'',
      {K("m_gab"): ("slots au gabarit", "template slots")}),
    S(F, 616, '\'<b class="cf-data-mv">—</b><i class="cf-data-ml">champs inventés</i>\'',
      '\'<b class="cf-data-mv">—</b><i class="cf-data-ml">\' + dzT("cartes.data1.m_fab") + \'</i>\'',
      {K("m_fab"): ("champs inventés", "invented fields")}),
    S(F, 651, C('''(nEvit ? "slots au gabarit (" + nEvit + " neutralisé(s))" : "slots au gabarit")
      : "slots au gabarit";'''),
      C('''(nEvit ? dzT("cartes.data1.m_gab_neutr", { n: nEvit }) : dzT("cartes.data1.m_gab"))
      : dzT("cartes.data1.m_gab");'''),
      {K("m_gab_neutr"): ("slots au gabarit ({n} neutralisé(s))", "template slots ({n} neutralized)"),
       K("m_gab"): ("slots au gabarit", "template slots")}),
    S(F, 662, C('''(nGab || nEvit)
        + " = " + au.n_slots_unfed_template + " slot(s) qu'aucune colonne "
        + "n'alimente" + (seul ? (" + " + seul + " slot(s) pourtant mappé(s) "
          + "dont la colonne a des cellules vides (" + (au.slots_template_hole_only
            || []).map(slotLabel).join(", ") + ")") : "")
        + ". Le grand livre ci-dessous en compte "
        + au.n_slots_unfed_template + " : il classe les colonnes, pas les "
        + "prises de parole."
        + (au.blank_mode
          ? (" Mode « laisser vide » actif : le gabarit ne reprend la main "
            + "nulle part, soit " + (au.n_fabricated_avoided || 0)
            + " emplacement(s) évité(s) sur l'ensemble du tirage.")
          : " Mode « texte du gabarit » : ces slots impriment la valeur de "
            + "démonstration de la pièce 03.");'''),
      C('''dzT("cartes.data1.gab_t_base", { tot: nGab || nEvit, n: au.n_slots_unfed_template })
        + (seul ? dzT("cartes.data1.gab_t_seul", { n: seul, slots: (au.slots_template_hole_only
            || []).map(slotLabel).join(", ") }) : "")
        + dzT("cartes.data1.gab_t_livre", { n: au.n_slots_unfed_template })
        + (au.blank_mode
          ? dzT("cartes.data1.gab_t_vide", { n: au.n_fabricated_avoided || 0 })
          : dzT("cartes.data1.gab_t_texte"));'''),
      {K("gab_t_base"): ("{tot} = {n} slot(s) qu'aucune colonne n'alimente", "{tot} = {n} slot(s) fed by no column"),
       K("gab_t_seul"): (" + {n} slot(s) pourtant mappé(s) dont la colonne a des cellules vides ({slots})",
                         " + {n} slot(s) that are mapped but whose column has empty cells ({slots})"),
       K("gab_t_livre"): (". Le grand livre ci-dessous en compte {n} : il classe les colonnes, pas les prises de parole.",
                          ". The ledger below counts {n}: it sorts columns, not the places where the template speaks."),
       K("gab_t_vide"): (" Mode « laisser vide » actif : le gabarit ne reprend la main nulle part, soit {n} emplacement(s) évité(s) sur l'ensemble du tirage.",
                         " “Leave blank” mode is on: the template never takes over, so {n} placement(s) avoided across the whole print run."),
       K("gab_t_texte"): (" Mode « texte du gabarit » : ces slots impriment la valeur de démonstration de la pièce 03.",
                          " “Template text” mode: these slots print the sample value from piece 03.")}),
    S(F, 700, C('''"recalcul en cours — les 4 compteurs sont ceux de la "
      + "construction précédente"'''), 'dzT("cartes.data1.recalcul")',
      {K("recalcul"): ("recalcul en cours — les 4 compteurs sont ceux de la construction précédente",
                       "recalculating — the 4 counters are from the previous build")}),
    S(F, 703, 'T.columns.length + " colonnes"', 'dzT("cartes.data1.n_colonnes", { n: T.columns.length })',
      {K("n_colonnes"): ("{n} colonnes", "{n} columns")}),
    S(F, 714, '"séparateur " + sepLabel(T.sep)', 'dzT("cartes.data1.separateur", { sep: sepLabel(T.sep) })',
      {K("separateur"): ("séparateur {sep}", "{sep} separator")}),
    L(F, 715, '" (deviné)"', K("devine"), " (deviné)", " (detected)"),
    L(F, 715, '" (imposé)"', K("impose"), " (imposé)", " (forced)"),
    L(F, 723, '" (deviné)"', K("devine"), " (deviné)", " (detected)"),
    L(F, 723, '" (imposé)"', K("impose"), " (imposé)", " (forced)"),
    S(F, 725, 'st.disabled + " désactivée(s)"', 'dzT("cartes.data1.n_desactivees", { n: st.disabled })',
      {K("n_desactivees"): ("{n} désactivée(s)", "{n} disabled")}),
    S(F, 731, C('''LASTTABLE.n_ragged_long + " ligne(s) trop longue(s) — "
          + LASTTABLE.n_values_lost + " valeur(s) perdue(s)"'''),
      'dzT("cartes.data1.trop_longues", { n: LASTTABLE.n_ragged_long, perdues: LASTTABLE.n_values_lost })',
      {K("trop_longues"): ("{n} ligne(s) trop longue(s) — {perdues} valeur(s) perdue(s)",
                           "{n} row(s) too long — {perdues} value(s) lost")}),
    S(F, 735, 'LASTTABLE.n_ragged_short + " ligne(s) trop courte(s), complétée(s)"',
      'dzT("cartes.data1.trop_courtes", { n: LASTTABLE.n_ragged_short })',
      {K("trop_courtes"): ("{n} ligne(s) trop courte(s), complétée(s)", "{n} row(s) too short, padded")}),
    S(F, 753, C('''"import " + IMPORTED_N + " ligne(s) en "
        + Math.round(IMPORT_MS) + " ms"'''),
      'dzT("cartes.data1.import_n", { n: IMPORTED_N, ms: Math.round(IMPORT_MS) })',
      {K("import_n"): ("import {n} ligne(s) en {ms} ms", "import {n} row(s) in {ms} ms")}),
    S(F, 756, C('''"Le seuil du cahier des charges porte sur 200 lignes en moins de 2 s. "
      + "Mesure ici : " + IMPORTED_N + " ligne(s) en " + Math.round(IMPORT_MS)
      + " ms, octets lus compris et première frame peinte comprise."
      + (IMPORTED_N < 200
        ? " Cette mesure ne porte PAS sur 200 lignes : le jeu « Charge » de "
          + "l'écran vide les fournit."
        : " Le seuil est tenu sur le nombre de lignes qu'il nomme.")'''),
      C('''dzT("cartes.data1.seuil", { n: IMPORTED_N, ms: Math.round(IMPORT_MS) })
      + (IMPORTED_N < 200
        ? dzT("cartes.data1.seuil_non")
        : dzT("cartes.data1.seuil_oui"))'''),
      {K("seuil"): ("Le seuil du cahier des charges porte sur 200 lignes en moins de 2 s. Mesure ici : {n} ligne(s) en {ms} ms, octets lus compris et première frame peinte comprise.",
                    "The spec threshold is 200 rows in under 2 s. Measured here: {n} row(s) in {ms} ms, including reading the bytes and the first painted frame."),
       K("seuil_non"): (" Cette mesure ne porte PAS sur 200 lignes : le jeu « Charge » de l'écran vide les fournit.",
                        " This measurement is NOT on 200 rows: the “Charge” sample on the empty screen provides them."),
       K("seuil_oui"): (" Le seuil est tenu sur le nombre de lignes qu'il nomme.",
                        " The threshold is met on the number of rows it names.")}),
    L(F, 766, '"accents douteux"', K("accents_douteux"), "accents douteux", "suspicious accents"),
    S(F, 772, C('''"cadre : « " + au.frame.word + " » contredit " + au.frame.col
          + " sur " + au.frame.n_clash + " / " + au.frame.n_cards + " cartes"'''),
      'dzT("cartes.data1.cadre_contredit", { mot: au.frame.word, col: au.frame.col, n: au.frame.n_clash, total: au.frame.n_cards })',
      {K("cadre_contredit"): ("cadre : « {mot} » contredit {col} sur {n} / {total} cartes",
                              "frame: “{mot}” contradicts {col} on {n} / {total} cards")}),
    L(F, 777, '"aucune donnée — déposez un CSV, un classeur, ou chargez un exemple"', K("aucune_donnee"),
      "aucune donnée — déposez un CSV, un classeur, ou chargez un exemple",
      "no data — drop a CSV or a workbook, or load a sample"),
    S(F, 789, '("Exporter le deck — " + nc + " carte(s)")', 'dzT("cartes.data1.exporter_deck_n", { n: nc })',
      {K("exporter_deck_n"): ("Exporter le deck — {n} carte(s)", "Export deck — {n} card(s)")}),
    L(F, 789, '"Exporter le deck"', K("exporter_deck"), "Exporter le deck", "Export deck"),
    S(F, 807, C('''" [somme incohérente : "
      + a + " + " + b + " ≠ " + tot + " — ne rien conclure de ce chiffre]"'''),
      'dzT("cartes.data1.somme_incoherente", { a: a, b: b, tot: tot })',
      {K("somme_incoherente"): (" [somme incohérente : {a} + {b} ≠ {tot} — ne rien conclure de ce chiffre]",
                                " [inconsistent sum: {a} + {b} ≠ {tot} — draw no conclusion from this number]")}),
    S(F, 809, C('''(au.blank_mode ? "Auraient été fabriqués : " : "Fabriqués : ")
      + au.n_slots_unfed_template + " slot(s) qu'aucune colonne n'alimente × "
      + nc + " carte(s) = " + a
      + " · + " + b + " emplacement(s) laissés vides par une colonne pourtant "
      + "posée = " + tot + " au total, compté carte par carte par le moteur "
      + "(jamais un produit)." + somme
      + (au.blank_mode ? " Le mode « laisser vide » les a tous neutralisés : "
        + "le fichier livré n'en porte aucun." : "");'''),
      C('''(au.blank_mode ? dzT("cartes.data1.fab_auraient") : dzT("cartes.data1.fab_fabriques"))
      + dzT("cartes.data1.fab_detail", { n: au.n_slots_unfed_template, nc: nc, a: a, b: b, tot: tot }) + somme
      + (au.blank_mode ? dzT("cartes.data1.fab_neutralises") : "");'''),
      {K("fab_auraient"): ("Auraient été fabriqués : ", "Would have been invented: "),
       K("fab_fabriques"): ("Fabriqués : ", "Invented: "),
       K("fab_detail"): ("{n} slot(s) qu'aucune colonne n'alimente × {nc} carte(s) = {a} · + {b} emplacement(s) laissés vides par une colonne pourtant posée = {tot} au total, compté carte par carte par le moteur (jamais un produit).",
                         "{n} slot(s) fed by no column × {nc} card(s) = {a} · + {b} placement(s) left empty by a column that is mapped = {tot} in total, counted card by card by the engine (never a product)."),
       K("fab_neutralises"): (" Le mode « laisser vide » les a tous neutralisés : le fichier livré n'en porte aucun.",
                              " “Leave blank” mode neutralized all of them: the delivered file contains none.")}),
    L(F, 827, '"classeur .xlsx"', K("classeur_xlsx"), "classeur .xlsx", ".xlsx workbook"),
    L(F, 828, '"classeur .ods"', K("classeur_ods"), "classeur .ods", ".ods workbook"),
    L(F, 829, '"encodage non déterminé (table saisie ici)"', K("enc_indetermine"),
      "encodage non déterminé (table saisie ici)", "encoding unknown (table typed here)"),
    X(F, 855, '"< 0,1 ms"', "format numérique (virgule décimale, cohérent avec la ligne 856)"),
    S(F, 870, C('''" · <i>somme des cinq postes affichés : " + r(s)
        + " (arrondis)</i>"'''),
      '" · <i>" + dzT("cartes.data1.t_somme", { s: r(s) }) + "</i>"',
      {K("t_somme"): ("somme des cinq postes affichés : {s} (arrondis)", "sum of the five items shown: {s} (rounded)")}),
    S(F, 873, C('''"où passent ces " + r(TIMING.total) + " : base64 <b>" + r(TIMING.b64)
      + "</b> · moteur <b>" + r(eng)
      + "</b> · trajet HTTP <b>" + r(net)
      + "</b> · table dans le DOM <b>" + r(TIMING.apply)
      + "</b> · première frame peinte <b>" + r(TIMING.paint) + "</b>" + somme'''),
      'dzT("cartes.data1.t_detail", { total: r(TIMING.total), b64: r(TIMING.b64), moteur: r(eng), net: r(net), dom: r(TIMING.apply), peint: r(TIMING.paint) }) + somme',
      {K("t_detail"): ("où passent ces {total} : base64 <b>{b64}</b> · moteur <b>{moteur}</b> · trajet HTTP <b>{net}</b> · table dans le DOM <b>{dom}</b> · première frame peinte <b>{peint}</b>",
                       "where these {total} go: base64 <b>{b64}</b> · engine <b>{moteur}</b> · HTTP round trip <b>{net}</b> · table in the DOM <b>{dom}</b> · first painted frame <b>{peint}</b>")}),
    S(F, 911, C('''"Aucune table : la carte affichée est <b>entièrement</b> celle du gabarit "
        + "de la pièce 03. Le contrôle du mappage s'allume dès qu'un fichier entre."'''),
      'dzT("cartes.data1.audit_vide")',
      {K("audit_vide"): ("Aucune table : la carte affichée est <b>entièrement</b> celle du gabarit de la pièce 03. Le contrôle du mappage s'allume dès qu'un fichier entre.",
                         "No table: the card shown comes <b>entirely</b> from the piece 03 template. The mapping check turns on as soon as a file comes in.")}),
    L(F, 917, '"Contrôle du mappage : en attente de la construction…"', K("audit_attente"),
      "Contrôle du mappage : en attente de la construction…", "Mapping check: waiting for the build…"),
    L(F, 959, '"vers un slot disparu"', K("vers_slot_disparu"), "vers un slot disparu", "to a missing slot"),
    S(F, 960, C('''(au.cols_to_ghost || []).join(", ")
          + " — ces colonnes visent un slot qui n'existe plus dans « 03 "
          + "Typographie » : elles n'alimentent rien, reposez-les"'''),
      'dzT("cartes.data1.ghost_t", { cols: (au.cols_to_ghost || []).join(", ") })',
      {K("ghost_t"): ("{cols} — ces colonnes visent un slot qui n'existe plus dans « 03 Typographie » : elles n'alimentent rien, reposez-les",
                      "{cols} — these columns target a slot that no longer exists in “03 Typography”: they feed nothing, map them again")}),
    L(F, 964, '"colonnes du fichier"', K("cols_fichier"), "colonnes du fichier", "file columns"),
    L(F, 965, '"vers un slot"', K("vers_slot"), "vers un slot", "to a slot"),
    L(F, 968, '"vers un champ réservé"', K("vers_reserve"), "vers un champ réservé", "to a reserved field"),
    S(F, 969, C('''(au.cols_to_reserved || []).join(", ")
          + " — art / dos / identifiant ne sont pas des slots de texte : "
          + "c'est TOUT l'écart entre « posées » et « alimentés »"'''),
      'dzT("cartes.data1.reserve_t", { cols: (au.cols_to_reserved || []).join(", ") })',
      {K("reserve_t"): ("{cols} — art / dos / identifiant ne sont pas des slots de texte : c'est TOUT l'écart entre « posées » et « alimentés »",
                        "{cols} — art / back / id are not text slots: that is the WHOLE gap between “mapped” and “fed”")}),
    L(F, 979, '"quantité (comptée à gauche)"', K("qty_gauche"), "quantité (comptée à gauche)", "quantity (counted on the left)"),
    L(F, 979, '"quantité"', K("qty"), "quantité", "quantity"),
    S(F, 981, C('''("« " + String(T.qty_col || "") + " » sert de quantité ET alimente un "
          + "slot : elle est comptée une seule fois, dans « vers un slot ».")'''),
      'dzT("cartes.data1.qty_aussi_t", { col: String(T.qty_col || "") })',
      {K("qty_aussi_t"): ("« {col} » sert de quantité ET alimente un slot : elle est comptée une seule fois, dans « vers un slot ».",
                          "“{col}” is the quantity AND feeds a slot: it is counted only once, under “to a slot”.")}),
    L(F, 984, '"sans emploi"', K("sans_emploi"), "sans emploi", "unused"),
    L(F, 988, '"slots de la carte"', K("slots_carte"), "slots de la carte", "card slots"),
    L(F, 989, '"du fichier"', K("du_fichier"), "du fichier", "from the file"),
    L(F, 998, '"sans colonne, laissés vides"', K("sans_col_vides"), "sans colonne, laissés vides", "no column, left blank"),
    L(F, 999, '"sans colonne, au gabarit"', K("sans_col_gab"), "sans colonne, au gabarit", "no column, template text"),
    S(F, 1004, C('''(" — le compteur du haut en annonce "
                + (au.n_slots_unfed_template + au.n_slots_template_hole_only)
                + " : il ajoute " + au.n_slots_template_hole_only
                + " slot(s) pourtant mappé(s) dont la colonne a des cellules "
                + "vides (" + (au.slots_template_hole_only || [])
                  .map(slotLabel).join(", ") + ")")'''),
      C('''dzT("cartes.data1.haut_annonce", { tot: au.n_slots_unfed_template + au.n_slots_template_hole_only,
                n: au.n_slots_template_hole_only,
                slots: (au.slots_template_hole_only || []).map(slotLabel).join(", ") })'''),
      {K("haut_annonce"): (" — le compteur du haut en annonce {tot} : il ajoute {n} slot(s) pourtant mappé(s) dont la colonne a des cellules vides ({slots})",
                           " — the counter above shows {tot}: it adds {n} slot(s) that are mapped but whose column has empty cells ({slots})")}),
    L(F, 1011, '"vides de toute façon"', K("vides_toute_facon"), "vides de toute façon", "empty anyway"),
    S(F, 1012, C('''mute.map(slotLabel).join(", ")
            + " — sans donnée ET sans texte de démonstration : ils n'impriment "
            + "rien, ils ne sont donc PAS comptés comme fabriqués"'''),
      'dzT("cartes.data1.muets_t", { slots: mute.map(slotLabel).join(", ") })',
      {K("muets_t"): ("{slots} — sans donnée ET sans texte de démonstration : ils n'impriment rien, ils ne sont donc PAS comptés comme fabriqués",
                      "{slots} — no data AND no sample text: they print nothing, so they are NOT counted as invented")}),
    S(F, 1018, C('''"<b>" + au.n_slots_hidden + "</b> slot(s) masqué(s) dans « 03 "
          + "Typographie » — hors compte : la carte ne les dessine pas."'''),
      'dzT("cartes.data1.masques", { n: au.n_slots_hidden })',
      {K("masques"): ("<b>{n}</b> slot(s) masqué(s) dans « 03 Typographie » — hors compte : la carte ne les dessine pas.",
                      "<b>{n}</b> slot(s) hidden in “03 Typography” — not counted: the card does not draw them.")}),
    L(F, 1022, '"slots de la pièce 03 non publiés"', K("slots_non_publies"), "slots de la pièce 03 non publiés",
      "piece 03 slots not published"),
    L(F, 1037, '"les slots sans donnée resteront vides sur les cartes"', K("toast_vide"),
      "les slots sans donnée resteront vides sur les cartes", "slots without data will stay blank on the cards"),
    S(F, 1038, C('''"ATTENTION : les slots sans donnée impriment le texte de démonstration "
        + "du gabarit, indiscernable d'une vraie valeur"'''), 'dzT("cartes.data1.toast_gabarit")',
      {K("toast_gabarit"): ("ATTENTION : les slots sans donnée impriment le texte de démonstration du gabarit, indiscernable d'une vraie valeur",
                            "WARNING: slots without data print the template's sample text, indistinguishable from a real value")}),
    L(F, 1044, '"Laisser <b>vides</b> les slots sans donnée"', K("laisser_vides"),
      "Laisser <b>vides</b> les slots sans donnée", "Leave slots without data <b>blank</b>"),
    S(F, 1045, C('''"Décoché, la pièce 03 imprime son texte de démonstration à la "
      + "place de la donnée manquante — même typographie, même aplomb qu'une "
      + "vraie valeur, sur toutes les cartes du tirage."'''), 'dzT("cartes.data1.laisser_vides_t")',
      {K("laisser_vides_t"): ("Décoché, la pièce 03 imprime son texte de démonstration à la place de la donnée manquante — même typographie, même aplomb qu'une vraie valeur, sur toutes les cartes du tirage.",
                              "Unchecked, piece 03 prints its sample text in place of the missing data — same typography, same confidence as a real value, on every card of the print run.")}),
    L(F, 1058, '"Mesurer sur la carte livrée"', K("mesurer"), "Mesurer sur la carte livrée", "Measure on the delivered card"),
    S(F, 1060, C('''"Rend la carte affichée dans les deux modes et compare les deux "
      + "fichiers PNG pixel par pixel. Le compteur ci-dessus parle de "
      + "card.fields ; cette mesure parle du fichier."'''), 'dzT("cartes.data1.mesurer_t")',
      {K("mesurer_t"): ("Rend la carte affichée dans les deux modes et compare les deux fichiers PNG pixel par pixel. Le compteur ci-dessus parle de card.fields ; cette mesure parle du fichier.",
                        "Renders the card shown in both modes and compares the two PNG files pixel by pixel. The counter above is about card.fields; this measurement is about the file.")}),
    S(F, 1071, C('''("<b>" + fabriques + "</b> valeur(s) que personne n'a écrite partiraient "
        + "à l'impression — <b>" + au.n_fab_unfed + "</b> venant de "
        + au.n_slots_unfed_template + " slot(s) sans colonne sur les "
        + (st.n_cards || 0) + " carte(s), <b>" + au.n_fab_holes
        + "</b> de cellules vides sur une colonne posée")'''),
      'dzT("cartes.data1.hint_fab", { n: fabriques, unfed: au.n_fab_unfed, slots: au.n_slots_unfed_template, nc: st.n_cards || 0, holes: au.n_fab_holes })',
      {K("hint_fab"): ("<b>{n}</b> valeur(s) que personne n'a écrite partiraient à l'impression — <b>{unfed}</b> venant de {slots} slot(s) sans colonne sur les {nc} carte(s), <b>{holes}</b> de cellules vides sur une colonne posée",
                       "<b>{n}</b> value(s) nobody wrote would go to print — <b>{unfed}</b> from {slots} slot(s) without a column across the {nc} card(s), <b>{holes}</b> from empty cells in a mapped column")}),
    S(F, 1077, C('''("<b>0</b> valeur inventée <b>dans les slots</b> sur les "
          + (st.n_cards || 0) + " carte(s) — " + au.n_template_avoided
          + " slot(s) du gabarit neutralisé(s), soit <b>"
          + (au.n_fabricated_avoided || 0) + "</b> emplacement(s) qui auraient "
          + "été fabriqués")'''),
      'dzT("cartes.data1.hint_zero", { nc: st.n_cards || 0, n: au.n_template_avoided, evites: au.n_fabricated_avoided || 0 })',
      {K("hint_zero"): ("<b>0</b> valeur inventée <b>dans les slots</b> sur les {nc} carte(s) — {n} slot(s) du gabarit neutralisé(s), soit <b>{evites}</b> emplacement(s) qui auraient été fabriqués",
                        "<b>0</b> invented values <b>in the slots</b> across the {nc} card(s) — {n} template slot(s) neutralized, i.e. <b>{evites}</b> placement(s) that would have been invented")}),
    L(F, 1082, '"aucun slot ne fabrique de valeur"', K("aucun_fab"), "aucun slot ne fabrique de valeur",
      "no slot invents a value"),
    S(F, 1095, C('''("Slots sans donnée dont le gabarit a un texte — " + (BLANKMODE
          ? "laissés vides sur les " + (st.n_cards || 0) + " carte(s) :"
          : "voici ce qui s'imprime sur les " + (st.n_cards || 0) + " carte(s) :"))'''),
      C('''(BLANKMODE
          ? dzT("cartes.data1.slots_txt_vides", { nc: st.n_cards || 0 })
          : dzT("cartes.data1.slots_txt_imprime", { nc: st.n_cards || 0 }))'''),
      {K("slots_txt_vides"): ("Slots sans donnée dont le gabarit a un texte — laissés vides sur les {nc} carte(s) :",
                              "Slots without data whose template has text — left blank on the {nc} card(s):"),
       K("slots_txt_imprime"): ("Slots sans donnée dont le gabarit a un texte — voici ce qui s'imprime sur les {nc} carte(s) :",
                                "Slots without data whose template has text — here is what prints on the {nc} card(s):")}),
    L(F, 1098, '"Slots sans donnée (le gabarit n\'a rien à imprimer non plus) :"', K("slots_muets"),
      "Slots sans donnée (le gabarit n'a rien à imprimer non plus) :",
      "Slots without data (the template has nothing to print either):"),
    S(F, 1106, C('''"Colonne <code>" + esc(x.col) + "</code> → <b>" + esc(slotLabel(x.slot))
          + "</b> : <b>" + x.n_cards + "</b> carte(s) ont la cellule vide — "'''),
      'dzT("cartes.data1.trou_col", { col: esc(x.col), slot: esc(slotLabel(x.slot)), n: x.n_cards })',
      {K("trou_col"): ("Colonne <code>{col}</code> → <b>{slot}</b> : <b>{n}</b> carte(s) ont la cellule vide — ",
                       "Column <code>{col}</code> → <b>{slot}</b>: <b>{n}</b> card(s) have an empty cell — ")}),
    L(F, 1110, '"laissées vides (sans le mode ci-dessus, le gabarit y reprendrait la main)."', K("trou_vides"),
      "laissées vides (sans le mode ci-dessus, le gabarit y reprendrait la main).",
      "left blank (without the mode above, the template would take over there)."),
    L(F, 1111, '"<b>sur celles-là le gabarit reprend la main</b>."', K("trou_gabarit"),
      "<b>sur celles-là le gabarit reprend la main</b>.", "<b>on those, the template takes over</b>."),
    L(F, 1112, '"le gabarit n\'a rien à y mettre non plus : elles restent vides."', K("trou_rien"),
      "le gabarit n'a rien à y mettre non plus : elles restent vides.",
      "the template has nothing to put there either: they stay blank."),
    L(F, 1120, '"Colonnes du fichier qui n\'entrent dans aucune carte :"', K("orphelines"),
      "Colonnes du fichier qui n'entrent dans aucune carte :", "File columns that go into no card:"),
    L(F, 1142, '"poser ici sur…"', K("poser_ici"), "poser ici sur…", "map here to…"),
    L(F, 1150, '"▸ colonne de quantité"', K("col_qty"), "▸ colonne de quantité", "▸ quantity column"),
    S(F, 1182, C('''"Le <b>cadre</b> (pièce 02) imprime « <b>" + esc(fr.word)
        + "</b> » sur les <b>" + n + "</b> carte(s) : ce mot ne passe par aucun "
        + "slot et ne vient d'aucune colonne — aucune colonne de rareté dans "
        + "ce fichier, c'est donc un choix de mise en page, pas une donnée."'''),
      'dzT("cartes.data1.cadre_sans_col", { mot: esc(fr.word), n: n })',
      {K("cadre_sans_col"): ("Le <b>cadre</b> (pièce 02) imprime « <b>{mot}</b> » sur les <b>{n}</b> carte(s) : ce mot ne passe par aucun slot et ne vient d'aucune colonne — aucune colonne de rareté dans ce fichier, c'est donc un choix de mise en page, pas une donnée.",
                             "The <b>frame</b> (piece 02) prints “<b>{mot}</b>” on the <b>{n}</b> card(s): this word goes through no slot and comes from no column — there is no rarity column in this file, so it is a layout choice, not data.")}),
    S(F, 1188, C('''"Le <b>cadre</b> (pièce 02) imprime « <b>" + esc(fr.word)
        + "</b> » sur les <b>" + n + "</b> carte(s), et la colonne <code>"
        + esc(fr.col) + "</code> dit autre chose sur <b>" + fr.n_clash
        + "</b> d'entre elles"'''),
      'dzT("cartes.data1.cadre_clash", { mot: esc(fr.word), n: n, col: esc(fr.col), k: fr.n_clash })',
      {K("cadre_clash"): ("Le <b>cadre</b> (pièce 02) imprime « <b>{mot}</b> » sur les <b>{n}</b> carte(s), et la colonne <code>{col}</code> dit autre chose sur <b>{k}</b> d'entre elles",
                          "The <b>frame</b> (piece 02) prints “<b>{mot}</b>” on the <b>{n}</b> card(s), and the <code>{col}</code> column says something else on <b>{k}</b> of them")}),
    S(F, 1195, C('''". Ce mot ne passe par aucun slot : cette pièce ne peut pas "
        + "l'éteindre, il se règle dans « 02 Cadre » (bandeau, ou rareté du "
        + "cadre). Tant qu'il est là, <b>" + fr.n_clash + "</b> carte(s) "
        + "partiraient avec un mot que le fichier contredit."'''),
      'dzT("cartes.data1.cadre_clash_fin", { k: fr.n_clash })',
      {K("cadre_clash_fin"): (". Ce mot ne passe par aucun slot : cette pièce ne peut pas l'éteindre, il se règle dans « 02 Cadre » (bandeau, ou rareté du cadre). Tant qu'il est là, <b>{k}</b> carte(s) partiraient avec un mot que le fichier contredit.",
                              ". This word goes through no slot: this piece cannot turn it off, it is set in “02 Frame” (banner, or frame rarity). As long as it is there, <b>{k}</b> card(s) would ship with a word the file contradicts.")}),
    S(F, 1201, C('''"Le <b>cadre</b> (pièce 02) imprime « <b>" + esc(fr.word)
        + "</b> » sur les <b>" + n + "</b> carte(s) et la colonne <code>"
        + esc(fr.col) + "</code> dit la même chose sur toutes : rien à signaler."'''),
      'dzT("cartes.data1.cadre_ok", { mot: esc(fr.word), n: n, col: esc(fr.col) })',
      {K("cadre_ok"): ("Le <b>cadre</b> (pièce 02) imprime « <b>{mot}</b> » sur les <b>{n}</b> carte(s) et la colonne <code>{col}</code> dit la même chose sur toutes : rien à signaler.",
                       "The <b>frame</b> (piece 02) prints “<b>{mot}</b>” on the <b>{n}</b> card(s) and the <code>{col}</code> column says the same on all of them: nothing to report.")}),
    S(F, 1227, '"</s> laissé vide"', '"</s> " + dzT("cartes.data1.laisse_vide")',
      {K("laisse_vide"): ("laissé vide", "left blank")}),
    L(F, 1228, '"rien à imprimer"', K("rien_imprimer"), "rien à imprimer", "nothing to print"),
    L(F, 1231, '"alimenter avec…"', K("alimenter"), "alimenter avec…", "feed with…"),
    L(F, 1341, '"construisez d\'abord le deck"', K("construire_dabord"), "construisez d'abord le deck",
      "build the deck first"),
    L(F, 1344, '"ce moteur ne sait pas relire un PNG : mesure impossible"', K("png_illisible"),
      "ce moteur ne sait pas relire un PNG : mesure impossible",
      "this browser engine cannot read a PNG back: measurement impossible"),
    L(F, 1350, '"rendu de la carte dans les deux modes…"', K("rendu_deux_modes"),
      "rendu de la carte dans les deux modes…", "rendering the card in both modes…"),
    L(F, 1367, '"les deux rendus n\'ont pas la même toile"', K("toiles_differentes"),
      "les deux rendus n'ont pas la même toile", "the two renders do not have the same canvas"),
    S(F, 1396, 'diff + " pixel(s) d\'écart entre les deux fichiers de carte"',
      'dzT("cartes.data1.ecart_px", { n: diff })',
      {K("ecart_px"): ("{n} pixel(s) d'écart entre les deux fichiers de carte",
                       "{n} pixel(s) of difference between the two card files")}),
    S(F, 1405, '"mesure impossible : " + DELIV.err', 'dzT("cartes.data1.mesure_impossible", { err: DELIV.err })',
      {K("mesure_impossible"): ("mesure impossible : {err}", "measurement impossible: {err}")}),
    S(F, 1416, C('''"À <b>" + G.dpi + " DPI</b>, re-dérivé des millimètres : coupe "
      + G.g.trim_mm[0] + " × " + G.g.trim_mm[1] + " mm → <b>" + G.trim[0]
      + " × " + G.trim[1] + " px</b> · + 2 × " + G.bleed_mm
      + " mm de fond perdu → toile <b>" + G.canvas[0] + " × " + G.canvas[1]
      + " px</b> · − 2 × " + G.safe_mm + " mm → zone sûre <b>" + G.safe[0]
      + " × " + G.safe[1] + " px</b>"
      + (G.same ? "" : " — <b>la table du CORE annonce autre chose ("
        + G.g.canvas_px[0] + " × " + G.g.canvas_px[1] + ")</b>")'''),
      C('''dzT("cartes.data1.geom", { dpi: G.dpi, tw: G.g.trim_mm[0], th: G.g.trim_mm[1], pw: G.trim[0],
        ph: G.trim[1], bleed: G.bleed_mm, cw: G.canvas[0], ch: G.canvas[1], safe: G.safe_mm,
        sw: G.safe[0], sh: G.safe[1] })
      + (G.same ? "" : dzT("cartes.data1.geom_core", { w: G.g.canvas_px[0], h: G.g.canvas_px[1] }))'''),
      {K("geom"): ("À <b>{dpi} DPI</b>, re-dérivé des millimètres : coupe {tw} × {th} mm → <b>{pw} × {ph} px</b> · + 2 × {bleed} mm de fond perdu → toile <b>{cw} × {ch} px</b> · − 2 × {safe} mm → zone sûre <b>{sw} × {sh} px</b>",
                   "At <b>{dpi} DPI</b>, re-derived from millimetres: trim {tw} × {th} mm → <b>{pw} × {ph} px</b> · + 2 × {bleed} mm bleed → canvas <b>{cw} × {ch} px</b> · − 2 × {safe} mm → safe zone <b>{sw} × {sh} px</b>"),
       K("geom_core"): (" — <b>la table du CORE annonce autre chose ({w} × {h})</b>",
                        " — <b>the CORE table says otherwise ({w} × {h})</b>")}),
    S(F, 1428, C('''". Aucun fichier mesuré pour l'instant : le bouton "
      + "ci-dessus en rend deux et les lit octet par octet."'''), 'dzT("cartes.data1.geom_aucun")',
      {K("geom_aucun"): (". Aucun fichier mesuré pour l'instant : le bouton ci-dessus en rend deux et les lit octet par octet.",
                         ". No file measured yet: the button above renders two and reads them byte by byte.")}),
    S(F, 1442, '"mesure sur la carte livrée impossible — " + esc(DELIV.err)',
      'dzT("cartes.data1.deliv_err", { err: esc(DELIV.err) })',
      {K("deliv_err"): ("mesure sur la carte livrée impossible — {err}",
                        "measurement on the delivered card impossible — {err}")}),
    S(F, 1461, C('''"CONTRADICTION — le moteur annonce " + fc + " emplacement(s) du "
        + "gabarit neutralisé(s) sur CETTE carte, et pourtant le fichier ne "
        + "change pas plus que le plancher de bruit quand on rend le gabarit. "
        + "L'un des deux ment : ne pas partir à l'impression sur ce compte."'''),
      'dzT("cartes.data1.contra_neutr", { n: fc })',
      {K("contra_neutr"): ("CONTRADICTION — le moteur annonce {n} emplacement(s) du gabarit neutralisé(s) sur CETTE carte, et pourtant le fichier ne change pas plus que le plancher de bruit quand on rend le gabarit. L'un des deux ment : ne pas partir à l'impression sur ce compte.",
                           "CONTRADICTION — the engine reports {n} template placement(s) neutralized on THIS card, yet the file changes no more than the noise floor when the template is rendered. One of the two is lying: do not go to print on this count.")}),
    S(F, 1466, C('''"CONTRADICTION — le moteur n'annonce aucun emplacement au gabarit "
        + "sur cette carte, et pourtant " + d.diff + " pixel(s) changent quand "
        + "on le laisse parler. Le compteur ne voit pas tout ce qui s'imprime."'''),
      'dzT("cartes.data1.contra_aucun", { n: d.diff })',
      {K("contra_aucun"): ("CONTRADICTION — le moteur n'annonce aucun emplacement au gabarit sur cette carte, et pourtant {n} pixel(s) changent quand on le laisse parler. Le compteur ne voit pas tout ce qui s'imprime.",
                           "CONTRADICTION — the engine reports no template placement on this card, yet {n} pixel(s) change when the template is allowed to speak. The counter does not see everything that prints.")}),
    S(F, 1476, C('''"CONTRADICTION — l'écran lit " + ih.w + " × " + ih.h + " / "
        + ih.bits + " bits dans l'en-tête et le moteur lit " + R.ihdr.w + " × "
        + R.ihdr.h + " / " + R.ihdr.bits + " bits dans le MÊME fichier. "
        + "Aucun des deux ne vaut tant que ce n'est pas expliqué."'''),
      'dzT("cartes.data1.contra_ihdr", { w: ih.w, h: ih.h, bits: ih.bits, rw: R.ihdr.w, rh: R.ihdr.h, rbits: R.ihdr.bits })',
      {K("contra_ihdr"): ("CONTRADICTION — l'écran lit {w} × {h} / {bits} bits dans l'en-tête et le moteur lit {rw} × {rh} / {rbits} bits dans le MÊME fichier. Aucun des deux ne vaut tant que ce n'est pas expliqué.",
                          "CONTRADICTION — the screen reads {w} × {h} / {bits} bits in the header and the engine reads {rw} × {rh} / {rbits} bits in the SAME file. Neither counts until this is explained.")}),
    S(F, 1495, C('''"<b>Carte " + (d.i + 1) + " telle qu'elle est livrée</b>, lue octet "
      + "par octet : PNG <b>" + gr(d.n) + "</b> octets"'''),
      'dzT("cartes.data1.d_carte", { i: d.i + 1, n: gr(d.n) })',
      {K("d_carte"): ("<b>Carte {i} telle qu'elle est livrée</b>, lue octet par octet : PNG <b>{n}</b> octets",
                      "<b>Card {i} as delivered</b>, read byte by byte: PNG <b>{n}</b> bytes")}),
    S(F, 1498, C('''"En-tête IHDR : <b>" + (ih ? (ih.w + " × " + ih.h) : "illisible")
      + " px</b>"'''),
      'dzT("cartes.data1.d_ihdr", { dim: ih ? (ih.w + " × " + ih.h) : dzT("cartes.data1.illisible") })',
      {K("d_ihdr"): ("En-tête IHDR : <b>{dim} px</b>", "IHDR header: <b>{dim} px</b>"),
       K("illisible"): ("illisible", "unreadable")}),
    L(F, 1501, '", entrelacé"', K("entrelace"), ", entrelacé", ", interlaced"),
    L(F, 1502, '", non entrelacé"', K("non_entrelace"), ", non entrelacé", ", not interlaced"),
    S(F, 1503, C('''", <b>" + (ih ? ih.bits : "?") + " bits/canal ANNONCÉS</b> — un "
      + "en-tête est une déclaration."'''),
      'dzT("cartes.data1.d_bits", { bits: ih ? ih.bits : "?" })',
      {K("d_bits"): (", <b>{bits} bits/canal ANNONCÉS</b> — un en-tête est une déclaration.",
                     ", <b>{bits} bits/channel DECLARED</b> — a header is a declaration.")}),
    S(F, 1507, C('''"Profondeur <b>effective</b>, mesurée sur les <b>"
        + gr(R.samples) + "</b> échantillons dégonflés et défiltrés : <b>"
        + gr(R.distinct) + "</b> valeur(s) distincte(s), pas du réseau <b>"
        + R.lattice_step + "</b> → <b>"
        + Number(R.bits_effective).toFixed(2).replace(".", ",")
        + " bits utiles</b>"'''),
      C('''dzT("cartes.data1.d_prof", { n: gr(R.samples), k: gr(R.distinct), pas: R.lattice_step,
        bits: Number(R.bits_effective).toFixed(2).replace(".", ",") })'''),
      {K("d_prof"): ("Profondeur <b>effective</b>, mesurée sur les <b>{n}</b> échantillons dégonflés et défiltrés : <b>{k}</b> valeur(s) distincte(s), pas du réseau <b>{pas}</b> → <b>{bits} bits utiles</b>",
                     "<b>Effective</b> depth, measured on the <b>{n}</b> inflated and unfiltered samples: <b>{k}</b> distinct value(s), lattice step <b>{pas}</b> → <b>{bits} useful bits</b>")}),
    S(F, 1514, C('''" — <b>l'en-tête MENT</b> : tout tombe sur le réseau k·257, "
            + "c'est une carte 8 bits élargie."'''), 'dzT("cartes.data1.d_ment")',
      {K("d_ment"): (" — <b>l'en-tête MENT</b> : tout tombe sur le réseau k·257, c'est une carte 8 bits élargie.",
                     " — <b>the header LIES</b>: everything falls on the k·257 lattice, it is a widened 8-bit card.")}),
    L(F, 1517, '" — l\'en-tête dit vrai."', K("d_vrai"), " — l'en-tête dit vrai.", " — the header tells the truth."),
    L(F, 1517, '" — incohérent avec l\'en-tête."', K("d_incoherent"), " — incohérent avec l'en-tête.",
      " — inconsistent with the header."),
    S(F, 1522, C('''(" Canal alpha : <b>" + R.alpha.distinct
          + "</b> valeur(s) distincte(s)"
          + (R.alpha.opaque ? (" — entièrement opaque : ses <b>"
            + gr(R.alpha.bytes) + "</b> échantillons valent tous 255, il ne "
            + "porte aucune information") : (" de " + R.alpha.min + " à "
            + R.alpha.max)) + ".")'''),
      C('''(dzT("cartes.data1.d_alpha", { k: R.alpha.distinct })
          + (R.alpha.opaque ? dzT("cartes.data1.d_alpha_opaque", { n: gr(R.alpha.bytes) })
            : dzT("cartes.data1.d_alpha_plage", { min: R.alpha.min, max: R.alpha.max })) + ".")'''),
      {K("d_alpha"): (" Canal alpha : <b>{k}</b> valeur(s) distincte(s)", " Alpha channel: <b>{k}</b> distinct value(s)"),
       K("d_alpha_opaque"): (" — entièrement opaque : ses <b>{n}</b> échantillons valent tous 255, il ne porte aucune information",
                             " — fully opaque: its <b>{n}</b> samples are all 255, it carries no information"),
       K("d_alpha_plage"): (" de {min} à {max}", " from {min} to {max}")}),
    S(F, 1529, C('''"Profondeur effective <b>non mesurée</b> : "
        + esc(R.deep_why || R.error || "raison non rendue")
        + " — le chiffre de l'en-tête reste une déclaration."'''),
      'dzT("cartes.data1.d_prof_non", { why: esc(R.deep_why || R.error || dzT("cartes.data1.raison_non_rendue")) })',
      {K("d_prof_non"): ("Profondeur effective <b>non mesurée</b> : {why} — le chiffre de l'en-tête reste une déclaration.",
                         "Effective depth <b>not measured</b>: {why} — the header's number remains a declaration."),
       K("raison_non_rendue"): ("raison non rendue", "no reason given")}),
    S(F, 1537, C('''"Résolution : chunk <b>pHYs</b> présent — " + gr(R.phys.x)
        + " × " + gr(R.phys.y) + " " + esc(R.phys.unit_label) + ", soit <b>"
        + String(R.dpi).replace(".", ",") + " DPI</b> écrits DANS le fichier"'''),
      'dzT("cartes.data1.d_phys", { x: gr(R.phys.x), y: gr(R.phys.y), unite: esc(R.phys.unit_label), dpi: String(R.dpi).replace(".", ",") })',
      {K("d_phys"): ("Résolution : chunk <b>pHYs</b> présent — {x} × {y} {unite}, soit <b>{dpi} DPI</b> écrits DANS le fichier",
                     "Resolution: <b>pHYs</b> chunk present — {x} × {y} {unite}, i.e. <b>{dpi} DPI</b> written IN the file")}),
    S(F, 1540, '(", pour " + G.dpi + " DPI demandés"', '(dzT("cartes.data1.d_pour_dpi", { dpi: G.dpi })',
      {K("d_pour_dpi"): (", pour {dpi} DPI demandés", ", for {dpi} DPI requested")}),
    L(F, 1541, '" : ils tombent juste."', K("d_juste"), " : ils tombent juste.", ": they match."),
    L(F, 1542, '" : <b>ils ne tombent pas juste</b>."', K("d_pas_juste"), " : <b>ils ne tombent pas juste</b>.",
      ": <b>they do not match</b>."),
    S(F, 1544, C('''"Résolution : <b>aucun chunk pHYs</b> — ce fichier ne déclare "
        + "AUCUN DPI. Ce qui se prouve ici, ce sont ses pixels."'''), 'dzT("cartes.data1.d_sans_phys")',
      {K("d_sans_phys"): ("Résolution : <b>aucun chunk pHYs</b> — ce fichier ne déclare AUCUN DPI. Ce qui se prouve ici, ce sont ses pixels.",
                          "Resolution: <b>no pHYs chunk</b> — this file declares NO DPI. What can be proven here is its pixels.")}),
    S(F, 1549, C('''". L'en-tête du fichier livré dit "
        + (ih ? (ih.w + " × " + ih.h) : "?") + " : "'''),
      'dzT("cartes.data1.d_entete_dit", { dim: ih ? (ih.w + " × " + ih.h) : "?" })',
      {K("d_entete_dit"): (". L'en-tête du fichier livré dit {dim} : ", ". The delivered file's header says {dim}: ")}),
    L(F, 1551, '"<b>l\'arithmétique et le fichier tombent juste</b>."', K("d_arith_ok"),
      "<b>l'arithmétique et le fichier tombent juste</b>.", "<b>the arithmetic and the file match</b>."),
    L(F, 1552, '"<b>ILS NE TOMBENT PAS JUSTE</b>."', K("d_arith_ko"), "<b>ILS NE TOMBENT PAS JUSTE</b>.",
      "<b>THEY DO NOT MATCH</b>."),
    S(F, 1559, C('''(d.slots + " slot(s) sans donnée (compte par carte non rendu pour "
        + "celle-ci)")'''), 'dzT("cartes.data1.port_slots", { n: d.slots })',
      {K("port_slots"): ("{n} slot(s) sans donnée (compte par carte non rendu pour celle-ci)",
                         "{n} slot(s) without data (per-card count not returned for this one)")}),
    S(F, 1561, '(d.fabCard + " emplacement(s) fabriqué(s) sur cette carte")', 'dzT("cartes.data1.port_fab", { n: d.fabCard })',
      {K("port_fab"): ("{n} emplacement(s) fabriqué(s) sur cette carte", "{n} invented placement(s) on this card")}),
    S(F, 1562, C('''"La <b>même carte</b> rendue avec le texte du gabarit fait <b>"
      + gr(d.nb) + "</b> octets et diffère sur <b>" + gr(d.diff)
      + "</b> pixel(s) sur " + gr(d.tot) + " ("
      + String(pct).replace(".", ",") + " %)"
      + (d.blank
        ? (" : c'est l'encre de " + port + ", et elle n'est PAS dans le "
          + "fichier livré.")
        : (" : c'est l'encre fabriquée que le fichier livré CONTIENT — "
          + port + "."))
      + " Sur l'ensemble du tirage, le moteur compte <b>" + d.fabDeck
      + "</b> emplacement(s) fabriqué(s) pour " + d.cards + " carte(s)"
      + (d.blank ? ", tous neutralisés." : ".")
      + " Plancher de bruit mesuré (deux rendus du MÊME état) : <b>" + d.noise
      + "</b> pixel(s). 3 rendus + 2 reconstructions en " + Math.round(d.ms)
      + " ms" + (R && R.ms != null ? (", dont " + Math.round(R.ms)
        + " ms de relecture du PNG par le moteur") : "") + "."'''),
      C('''dzT("cartes.data1.d_meme", { nb: gr(d.nb), diff: gr(d.diff), tot: gr(d.tot), pct: String(pct).replace(".", ",") })
      + (d.blank
        ? dzT("cartes.data1.d_encre_absente", { port: port })
        : dzT("cartes.data1.d_encre_contenue", { port: port }))
      + dzT("cartes.data1.d_tirage", { n: d.fabDeck, nc: d.cards })
      + (d.blank ? dzT("cartes.data1.d_tous_neutr") : ".")
      + dzT("cartes.data1.d_bruit", { n: d.noise, ms: Math.round(d.ms) })
      + (R && R.ms != null ? dzT("cartes.data1.d_dont", { ms: Math.round(R.ms) }) : "") + "."'''),
      {K("d_meme"): ("La <b>même carte</b> rendue avec le texte du gabarit fait <b>{nb}</b> octets et diffère sur <b>{diff}</b> pixel(s) sur {tot} ({pct} %)",
                     "The <b>same card</b> rendered with the template text is <b>{nb}</b> bytes and differs on <b>{diff}</b> pixel(s) out of {tot} ({pct} %)"),
       K("d_encre_absente"): (" : c'est l'encre de {port}, et elle n'est PAS dans le fichier livré.",
                              ": that is the ink of {port}, and it is NOT in the delivered file."),
       K("d_encre_contenue"): (" : c'est l'encre fabriquée que le fichier livré CONTIENT — {port}.",
                               ": that is the invented ink the delivered file CONTAINS — {port}."),
       K("d_tirage"): (" Sur l'ensemble du tirage, le moteur compte <b>{n}</b> emplacement(s) fabriqué(s) pour {nc} carte(s)",
                       " Across the whole print run, the engine counts <b>{n}</b> invented placement(s) for {nc} card(s)"),
       K("d_tous_neutr"): (", tous neutralisés.", ", all neutralized."),
       K("d_bruit"): (" Plancher de bruit mesuré (deux rendus du MÊME état) : <b>{n}</b> pixel(s). 3 rendus + 2 reconstructions en {ms} ms",
                      " Measured noise floor (two renders of the SAME state): <b>{n}</b> pixel(s). 3 renders + 2 rebuilds in {ms} ms"),
       K("d_dont"): (", dont {ms} ms de relecture du PNG par le moteur", ", including {ms} ms for the engine to read the PNG back")}),
    S(F, 1592, C('''"D'où vient chaque valeur imprimée — carte "
      + (Math.min((i | 0) + 1, cards.length || 1)) + " / " + (cards.length || 1)'''),
      'dzT("cartes.data1.prov_titre", { i: Math.min((i | 0) + 1, cards.length || 1), n: cards.length || 1 })',
      {K("prov_titre"): ("D'où vient chaque valeur imprimée — carte {i} / {n}", "Where each printed value comes from — card {i} / {n}")}),
    S(F, 1611, '\' <i class="cf-data-pside">dos</i>\'', '\' <i class="cf-data-pside">\' + dzT("cartes.data1.p_dos") + \'</i>\'',
      {K("p_dos"): ("dos", "back")}),
    S(F, 1612, '\' <i class="cf-data-pside off">masqué</i>\'',
      '\' <i class="cf-data-pside off">\' + dzT("cartes.data1.p_masque") + \'</i>\'',
      {K("p_masque"): ("masqué", "hidden")}),
    L(F, 1615, '"laissé vide"', K("laisse_vide"), "laissé vide", "left blank"),
    L(F, 1615, '"rien"', K("rien"), "rien", "nothing"),
    S(F, 1617, '(\'fichier · <code>\' + esc(src[s.id] || "?") + "</code>")',
      'dzT("cartes.data1.p_fichier", { col: esc(src[s.id] || "?") })',
      {K("p_fichier"): ("fichier · <code>{col}</code>", "file · <code>{col}</code>")}),
    L(F, 1618, '"vide <b>voulu</b>"', K("p_vide_voulu"), "vide <b>voulu</b>", "<b>intentionally</b> blank"),
    L(F, 1619, '"non dessiné"', K("p_non_dessine"), "non dessiné", "not drawn"),
    L(F, 1620, '"<b>GABARIT</b>"', K("p_gabarit"), "<b>GABARIT</b>", "<b>TEMPLATE</b>"),
    L(F, 1620, '"vide"', K("p_vide"), "vide", "empty"),
    L(F, 1631, '"Bandeau du cadre"', K("p_bandeau"), "Bandeau du cadre", "Frame banner"),
    S(F, 1635, C('''("<b>CADRE</b> · contredit <code>" + esc(fr.col) + "</code> sur "
          + fr.n_clash + " carte(s)")
        : (fr.col ? "CADRE · d'accord avec <code>" + esc(fr.col) + "</code>"
          : "<b>CADRE</b> · aucune colonne")'''),
      C('''dzT("cartes.data1.p_cadre_contredit", { col: esc(fr.col), n: fr.n_clash })
        : (fr.col ? dzT("cartes.data1.p_cadre_accord", { col: esc(fr.col) })
          : dzT("cartes.data1.p_cadre_aucune"))'''),
      {K("p_cadre_contredit"): ("<b>CADRE</b> · contredit <code>{col}</code> sur {n} carte(s)",
                                "<b>FRAME</b> · contradicts <code>{col}</code> on {n} card(s)"),
       K("p_cadre_accord"): ("CADRE · d'accord avec <code>{col}</code>", "FRAME · agrees with <code>{col}</code>"),
       K("p_cadre_aucune"): ("<b>CADRE</b> · aucune colonne", "<b>FRAME</b> · no column")}),
    S(F, 1648, C('''"Le domaine <b>/api/cards/&lt;deck&gt;/data</b> n'est pas monté sur ce backend : "
      + "l'analyse CSV, le filtre et le tri vivent là-bas, en un seul exemplaire "
      + "(deux moteurs divergeraient en silence). Relancer le python du :8765."'''),
      'dzT("cartes.data1.missing")',
      {K("missing"): ("Le domaine <b>/api/cards/&lt;deck&gt;/data</b> n'est pas monté sur ce backend : l'analyse CSV, le filtre et le tri vivent là-bas, en un seul exemplaire (deux moteurs divergeraient en silence). Relancer le python du :8765.",
                      "The <b>/api/cards/&lt;deck&gt;/data</b> domain is not mounted on this backend: CSV parsing, filtering and sorting live there, in a single copy (two engines would silently diverge). Restart the Python on :8765.")}),
    S(F, 1678, C(''''<b>Déposez un fichier .csv / .tsv / .xlsx / .ods, ou un export Notion (.zip)</b>'
        + '<span class="hint">ou cliquez pour choisir · <b>Ctrl+V</b> colle une table · '
        + 'séparateur et encodage devinés sur les octets · un classeur n\\'a ni l\\'un ni l\\'autre</span>\''''),
      C(''''<b>' + dzT("cartes.data1.depot_titre") + '</b>'
        + '<span class="hint">' + dzT("cartes.data1.depot_hint") + '</span>\''''),
      {K("depot_titre"): ("Déposez un fichier .csv / .tsv / .xlsx / .ods, ou un export Notion (.zip)",
                          "Drop a .csv / .tsv / .xlsx / .ods file, or a Notion export (.zip)"),
       K("depot_hint"): ("ou cliquez pour choisir · <b>Ctrl+V</b> colle une table · séparateur et encodage devinés sur les octets · un classeur n'a ni l'un ni l'autre",
                         "or click to choose · <b>Ctrl+V</b> pastes a table · separator and encoding detected from the bytes · a workbook has neither")}),
    L(F, 1684, '"table saisie à la main"', K("table_main"), "table saisie à la main", "table typed by hand"),
    L(F, 1685, '"Remplacer…"', K("remplacer"), "Remplacer…", "Replace…"),
    L(F, 1687, '"Charger un autre fichier (ou glissez-le n\'importe où sur ce panneau)"', K("remplacer_t"),
      "Charger un autre fichier (ou glissez-le n'importe où sur ce panneau)",
      "Load another file (or drag it anywhere onto this panel)"),
    S(F, 1694, '" · ni séparateur ni encodage à choisir"', '" · " + dzT("cartes.data1.wb_rien")',
      {K("wb_rien"): ("ni séparateur ni encodage à choisir", "no separator or encoding to choose")}),
    L(F, 1696, '"Séparateur"', K("separateur_lbl"), "Séparateur", "Separator"),
    L(F, 1700, '"Encodage"', K("encodage_lbl"), "Encodage", "Encoding"),
    L(F, 1706, '"Réparer les accents"', K("reparer"), "Réparer les accents", "Fix accents"),
    L(F, 1708, '"Ce fichier contient des suites « Ã© » : du cp1252 relu en UTF-8."', K("reparer_t"),
      "Ce fichier contient des suites « Ã© » : du cp1252 relu en UTF-8.",
      "This file contains “Ã©” sequences: cp1252 read back as UTF-8."),
    L(F, 1713, '"Vider"', K("vider"), "Vider", "Clear"),
    L(F, 1715, '"Repartir de zéro (annulable par Ctrl+Z)"', K("vider_t"), "Repartir de zéro (annulable par Ctrl+Z)",
      "Start from scratch (undo with Ctrl+Z)"),
    L(F, 1733, '"Séparateur"', K("separateur_lbl"), "Séparateur", "Separator"),
    L(F, 1737, '"Encodage"', K("encodage_lbl"), "Encodage", "Encoding"),
    S(F, 1767, C('''"les octets d'origine ne sont plus en mémoire : rechargez le fichier "
      + "(« Remplacer… ») pour appliquer ce réglage"'''), 'dzT("cartes.data1.no_raw")',
      {K("no_raw"): ("les octets d'origine ne sont plus en mémoire : rechargez le fichier (« Remplacer… ») pour appliquer ce réglage",
                     "the original bytes are no longer in memory: reload the file (“Replace…”) to apply this setting")}),
    L(F, 1782, '"Lien Google Sheets…"', K("gs_bouton"), "Lien Google Sheets…", "Google Sheets link…"),
    L(F, 1784, '"Importer une feuille Google Sheets partagée « tous les utilisateurs disposant du lien » (CSV public, gratuit, sans clé)"',
      K("gs_bouton_t"),
      "Importer une feuille Google Sheets partagée « tous les utilisateurs disposant du lien » (CSV public, gratuit, sans clé)",
      "Import a Google Sheets sheet shared with “anyone with the link” (public CSV, free, no key)"),
    S(F, 1801, C('''"Lien de la feuille Google Sheets (partagée « tous les utilisateurs disposant du lien »). "
        + "L'onglet du lien (#gid=…) est celui qui sera lu."'''), 'dzT("cartes.data1.gs_saisir")',
      {K("gs_saisir"): ("Lien de la feuille Google Sheets (partagée « tous les utilisateurs disposant du lien »). L'onglet du lien (#gid=…) est celui qui sera lu.",
                        "Google Sheets link (shared with “anyone with the link”). The tab in the link (#gid=…) is the one that will be read.")}),
    L(F, 1802, '"Importer"', K("importer"), "Importer", "Import"),
    X(F, 1808, '"Google Sheets.csv"', "nom de fichier par défaut, écrit dans doc.data.src"),
    S(F, 1810, '"Google Sheets : " + String((e && e.message) || e)',
      'dzT("cartes.data1.gs_err", { err: String((e && e.message) || e) })',
      {K("gs_err"): ("Google Sheets : {err}", "Google Sheets: {err}")}),
    L(F, 1817, '"lecture du fichier impossible"', K("lecture_impossible"), "lecture du fichier impossible",
      "cannot read the file"),
    L(F, 1824, '"Aucune donnée. Commencez par&nbsp;:"', K("vide_titre"), "Aucune donnée. Commencez par&nbsp;:",
      "No data. Start with:"),
    L(F, 1834, '"détecté sur les octets : "', K("detecte_octets"), "détecté sur les octets : ", "detected from the bytes: "),
    S(F, 1840, C('''esc(s.n + " lignes × " + s.n_cols + " colonnes · "
          + s.bytes + " octets"
          + (s.n_cards != null ? (" → " + s.n_kept + " retenues, "
            + s.n_cards + " cartes") : ""))'''),
      C('''esc(dzT("cartes.data1.ech_taille", { n: s.n, cols: s.n_cols, octets: s.bytes })
          + (s.n_cards != null ? dzT("cartes.data1.ech_cartes", { k: s.n_kept, nc: s.n_cards }) : ""))'''),
      {K("ech_taille"): ("{n} lignes × {cols} colonnes · {octets} octets", "{n} rows × {cols} columns · {octets} bytes"),
       K("ech_cartes"): (" → {k} retenues, {nc} cartes", " → {k} kept, {nc} cards")}),
    S(F, 1844, '\'<em class="warn">\' + s.n_warn + " avertissement(s) : "',
      '\'<em class="warn">\' + dzT("cartes.data1.ech_avert", { n: s.n_warn })',
      {K("ech_avert"): ("{n} avertissement(s) : ", "{n} warning(s): ")}),
    L(F, 1858, '"Exemples indisponibles (backend muet)."', K("ech_indispo"), "Exemples indisponibles (backend muet).",
      "Samples unavailable (backend not responding)."),
    S(F, 1881, C('''"Ces <b>" + SAMPLES.length + "</b> jeux sont lus par le moteur "
        + "<b>sans aucun réglage</b>, et les valeurs ci-dessus sont celles "
        + "qu'il a rendues : <b>" + seps.length + "</b> séparateur(s) distinct(s) "
        + "(" + esc(seps.join(", ")) + ") · <b>" + encs.length + "</b> encodage(s) "
        + "distinct(s) (" + esc(encs.join(", ")) + ")"
        + (wbs.length ? (" · <b>" + wbs.length + "</b> classeur(s) sans "
          + "séparateur ni encodage à deviner (" + esc(wbs.join(", ")) + ")") : "")
        + ". Une valeur par défaut heureuse ne tombe pas juste "
        + SAMPLES.length + " fois."'''),
      C('''dzT("cartes.data1.detsum", { n: SAMPLES.length, ns: seps.length, seps: esc(seps.join(", ")),
          ne: encs.length, encs: esc(encs.join(", ")) })
        + (wbs.length ? dzT("cartes.data1.detsum_wb", { n: wbs.length, wbs: esc(wbs.join(", ")) }) : "")
        + dzT("cartes.data1.detsum_fin", { n: SAMPLES.length })'''),
      {K("detsum"): ("Ces <b>{n}</b> jeux sont lus par le moteur <b>sans aucun réglage</b>, et les valeurs ci-dessus sont celles qu'il a rendues : <b>{ns}</b> séparateur(s) distinct(s) ({seps}) · <b>{ne}</b> encodage(s) distinct(s) ({encs})",
                     "These <b>{n}</b> samples are read by the engine <b>with no settings at all</b>, and the values above are the ones it returned: <b>{ns}</b> distinct separator(s) ({seps}) · <b>{ne}</b> distinct encoding(s) ({encs})"),
       K("detsum_wb"): (" · <b>{n}</b> classeur(s) sans séparateur ni encodage à deviner ({wbs})",
                        " · <b>{n}</b> workbook(s) with no separator or encoding to detect ({wbs})"),
       K("detsum_fin"): (". Une valeur par défaut heureuse ne tombe pas juste {n} fois.",
                         ". A lucky default value does not land right {n} times.")}),
    S(F, 1893, '"Table vierge 4 × 3"', 'dzT("cartes.data1.table_vierge_btn")',
      {K("table_vierge_btn"): ("Table vierge 4 × 3", "Blank 4 × 3 table")}),
    X(F, 1902, '"table vierge"', "valeur écrite dans doc.data.src (stockée dans le document)"),
    S(F, 1909, '"Coller depuis le presse-papiers"', 'dzT("cartes.data1.coller")',
      {K("coller"): ("Coller depuis le presse-papiers", "Paste from clipboard")}),
    L(F, 1914, '"presse-papiers vide"', K("pp_vide"), "presse-papiers vide", "clipboard empty"),
    X(F, 1916, '"presse-papiers"', "nom de source écrit dans doc.data.src (stocké dans le document)"),
    L(F, 1918, '"autorisation refusée — utilisez Ctrl+V dans ce panneau"', K("pp_refuse"),
      "autorisation refusée — utilisez Ctrl+V dans ce panneau", "permission denied — use Ctrl+V in this panel"),
    L(F, 1961, '"ex. une condition sur une colonne de la table"', K("ex_filtre_vide"),
      "ex. une condition sur une colonne de la table", "e.g. a condition on a column of the table"),
    S(F, 1962, C('''"ex. " + (refCol(n) || n) + " > 1   ·   " + (refCol(t) || t)
      + " contient …"'''),
      'dzT("cartes.data1.ex", { c: (refCol(n) || n) + " > 1   ·   " + (refCol(t) || t) + " contient …" })',
      {K("ex"): ("ex. {c}", "e.g. {c}")}),
    S(F, 1965, '"ex. " + (refCol(c) || c) + (n ? " > 1" : " contient …")',
      'dzT("cartes.data1.ex", { c: (refCol(c) || c) + (n ? " > 1" : " contient …") })',
      {K("ex"): ("ex. {c}", "e.g. {c}")}),
    L(F, 1969, '"ex. colonne desc"', K("ex_tri_vide"), "ex. colonne desc", "e.g. column desc"),
    S(F, 1970, '"ex. " + n + " desc, " + t', 'dzT("cartes.data1.ex", { c: n + " desc, " + t })',
      {K("ex"): ("ex. {c}", "e.g. {c}")}),
    S(F, 1971, '"ex. " + (n || t) + " desc"', 'dzT("cartes.data1.ex", { c: (n || t) + " desc" })',
      {K("ex"): ("ex. {c}", "e.g. {c}")}),
    L(F, 1980, '"— aucune (1 carte par ligne)"', K("qty_aucune"), "— aucune (1 carte par ligne)", "— none (1 card per row)"),
    S(F, 1992, '\'<span class="lbl">Colonne de quantité</span>\'',
      '\'<span class="lbl">\' + dzT("cartes.data1.qty_lbl") + \'</span>\'',
      {K("qty_lbl"): ("Colonne de quantité", "Quantity column")}),
    S(F, 2001, '\'<span class="lbl">Tri du deck <em class="cf-data-same">= les flèches ▲▼ des entêtes</em></span>\'',
      '\'<span class="lbl">\' + dzT("cartes.data1.tri_lbl") + \' <em class="cf-data-same">\' + dzT("cartes.data1.tri_fleches") + \'</em></span>\'',
      {K("tri_lbl"): ("Tri du deck", "Deck sort"),
       K("tri_fleches"): ("= les flèches ▲▼ des entêtes", "= the ▲▼ arrows in the headers")}),
    S(F, 2005, C('''"Ce champ et les flèches des entêtes de colonne sont le MÊME réglage : "
      + "cliquer une flèche réécrit cette ligne."'''), 'dzT("cartes.data1.tri_t")',
      {K("tri_t"): ("Ce champ et les flèches des entêtes de colonne sont le MÊME réglage : cliquer une flèche réécrit cette ligne.",
                    "This field and the column header arrows are the SAME setting: clicking an arrow rewrites this line.")}),
    # >>> SUITE
]
