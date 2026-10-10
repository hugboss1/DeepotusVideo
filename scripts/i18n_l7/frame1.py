"""t147 — frame1 : js/mod-frame.js lignes 1-5733 (pièce 02 « Cadre » : catalogue, décor, gemme, bandeau, panneau).

GARDÉ (X) et pourquoi :
  · le bloc CF-FRAME-CATALOG (l. 38-522) est EXTRAIT et comparé à cards/frame.py par test_cards_frame.py, et même
    ÉVALUÉ sous node (miroir d'exécution, phrase d'écart comprise) : ses libellés restent tels quels. Ils sont traduits
    À L'AFFICHAGE : entrées H (fr exact → en) lues par la surcouche (cellules du catalogue) et par `libT`, petite aide
    ajoutée près de `f()` qui passe un libellé par __dzI18n.traduire (options de <select>, boutons de `seg`,
    étiquettes d'historique) — en français elle rend le libellé intact ;
  · les libellés/voies du plan d'occupation (« bandeau de rareté », « posée à la main », « logement de »…) : même
    résultat que POST /frame/occupancy, confronté au backend, et `lane` est relu (`slice("logement de ".length)`) ;
  · les textes PEINTS dans la toile (damier « décor de cadre manquant », « calque N manquant », « image du dos
    manquante ») : ils partent dans le PNG exporté ; les polices canvas, « image/ », « image/* » (MIME).
"""
from outils import L, S, X, H

PLAGES = {"js/mod-frame.js": (1, 5733)}

F = "js/mod-frame.js"


def J(*lignes):
    """Un `avant`/`apres` sur plusieurs lignes (sources en CRLF)."""
    return "\r\n".join(lignes)


CAT = "bloc CF-FRAME-CATALOG extrait, comparé à cards/frame.py et évalué sous node par test_cards_frame.py"
OCC = "plan d'occupation : même résultat que POST /frame/occupancy (confronté au backend, lane relu)"
TOILE = "texte peint dans la toile du cadre, donc dans le PNG exporté"

ENTREES = [
    # ── garde de chargement, catalogue (X : bloc figé) ───────────────────────────────────────────────────────
    X(F, 24, '"mod-frame: js/core.js doit etre charge avant ce fichier"', "garde de chargement"),
    X(F, 509, '", ni la mesure ni la famille n\'a de teinte"', CAT),
    X(F, 510, '", teinte de la mesure non mesurable (gris)"', CAT),
    X(F, 511, '", la famille n\'a pas de teinte propre"', CAT),
    X(F, 512, '", teinte à "', CAT),
    X(F, 516, '" à moins de "', CAT),
    X(F, 518, '") : le catalogue retient la première"', CAT),

    # libellés du catalogue : traduits à l'affichage (surcouche + libT)
    H("cartes.frame1.fam_runic", "Runique", "Runic"),
    H("cartes.frame1.fam_runic_hint", "gravure fine, équerres, tirets runiques", "fine engraving, brackets, runic dashes"),
    H("cartes.frame1.fam_arcane", "Arcane", "Arcane"),
    H("cartes.frame1.fam_arcane_hint", "volutes, fenêtre en arc, filigrane", "scrolls, arched window, filigree"),
    H("cartes.frame1.fam_timber", "Bois sculpté", "Carved wood"),
    H("cartes.frame1.fam_timber_hint", "veines, rivets, bande épaisse", "grain, rivets, thick band"),
    H("cartes.frame1.fam_deco", "Art déco", "Art deco"),
    H("cartes.frame1.fam_deco_hint", "chevrons étagés, éventails, coins coupés", "stepped chevrons, fans, clipped corners"),
    H("cartes.frame1.fam_neon", "Néon", "Neon"),
    H("cartes.frame1.fam_neon_hint", "double trait lumineux, coins coupés", "glowing double line, clipped corners"),
    H("cartes.frame1.fam_sable", "Épure", "Minimal"),
    H("cartes.frame1.fam_sable_hint", "un seul filet, grande marge, rien d'autre", "a single line, wide margin, nothing else"),
    H("cartes.frame1.fam_gravure", "Gravure", "Engraving"),
    H("cartes.frame1.fam_gravure_hint", "marge ivoire, aplat de pochoir décalé, repères", "ivory margin, offset stencil fill, marks"),
    H("cartes.frame1.fam_filigrane", "Filigrane à instruments", "Instrument filigree"),
    H("cartes.frame1.fam_filigrane_hint", "double filet 2,1/3,2 mm, instruments de coin, médaillons",
      "double line 2.1/3.2 mm, corner instruments, medallions"),
    H("cartes.frame1.rar_common", "Commune", "Common"),
    H("cartes.frame1.rar_uncommon", "Peu commune", "Uncommon"),
    H("cartes.frame1.rar_rare", "Rare", "Rare"),
    H("cartes.frame1.rar_epic", "Épique", "Epic"),
    H("cartes.frame1.rar_legendary", "Légendaire", "Legendary"),
    H("cartes.frame1.rar_mythic", "Mythique", "Mythic"),
    H("cartes.frame1.dos_mirror", "Miroir du recto", "Mirror of the front"),
    H("cartes.frame1.dos_lattice", "Treillis", "Lattice"),
    H("cartes.frame1.dos_guilloche", "Guilloché", "Guilloche"),
    H("cartes.frame1.dos_sunburst", "Soleil", "Sun"),
    H("cartes.frame1.dos_scales", "Écailles", "Scales"),
    H("cartes.frame1.dos_chevron", "Chevrons", "Chevrons"),
    H("cartes.frame1.dos_runes", "Runes", "Runes"),
    H("cartes.frame1.dos_custom", "Personnalisé", "Custom"),
    H("cartes.frame1.fusion_normal", "Normal", "Normal"),
    H("cartes.frame1.fusion_multiply", "Multiplier", "Multiply"),
    H("cartes.frame1.coin_none", "Aucun", "None"),
    H("cartes.frame1.coin_bracket", "Équerre", "Bracket"),
    H("cartes.frame1.coin_scroll", "Volute", "Scroll"),
    H("cartes.frame1.coin_stud", "Rivet", "Stud"),
    H("cartes.frame1.coin_fleuron", "Fleuron", "Fleuron"),
    H("cartes.frame1.coin_spike", "Pointe", "Spike"),
    H("cartes.frame1.plan_dessus", "au-dessus des blocs", "above blocks"),
    H("cartes.frame1.plan_dessous", "sous les blocs", "below blocks"),
    H("cartes.frame1.sceau_argent", "Argent holographique", "Holographic silver"),
    H("cartes.frame1.sceau_dorure", "Dorure holographique", "Holographic gilding"),
    H("cartes.frame1.metal_gold", "Or", "Gold"),
    H("cartes.frame1.metal_silver", "Argent", "Silver"),
    H("cartes.frame1.metal_copper", "Cuivre", "Copper"),
    H("cartes.frame1.metal_steel", "Acier", "Steel"),
    H("cartes.frame1.metal_rose", "Or rose", "Rose gold"),
    H("cartes.frame1.preset_sobre", "Runique sobre", "Plain runic"),
    H("cartes.frame1.preset_heroique", "Arcane légendaire", "Legendary arcane"),
    H("cartes.frame1.preset_cyber", "Néon épique", "Epic neon"),
    H("cartes.frame1.preset_taverne", "Bois commun", "Plain wood"),
    H("cartes.frame1.preset_musee", "Épure rare", "Rare minimal"),
    # boutons de `seg` (valeurs comparées : data-v reste en français, seul le texte passe par libT)
    H("cartes.frame1.spot_hg", "HG", "TL"),
    H("cartes.frame1.spot_hd", "HD", "TR"),
    H("cartes.frame1.spot_bg", "BG", "BL"),
    H("cartes.frame1.spot_bd", "BD", "BR"),
    H("cartes.frame1.spot_centre", "centre", "center"),
    H("cartes.frame1.face_recto", "Recto", "Front"),
    H("cartes.frame1.face_verso", "Verso", "Back"),

    # ── plan d'occupation (X) ─────────────────────────────────────────────────────────────────────────────────
    X(F, 1057, '"bandeau de rareté"', OCC),
    X(F, 1059, '"posée à la main"', OCC),
    X(F, 1078, '"voie libre, ruban aminci"', OCC),
    X(F, 1078, '"voie libre"', OCC),
    X(F, 1079, '"aucune voie libre"', OCC),
    X(F, 1081, '"bandeau de rareté"', OCC),
    X(F, 1170, '"gemme de rareté"', OCC),
    X(F, 1172, '"posée à la main"', OCC),
    X(F, 1193, '"logement de "', OCC),
    X(F, 1195, '"gemme en logement de "', OCC),
    X(F, 1195, '"gemme de rareté"', OCC),
    X(F, 1214, '"fenêtre d\'illustration"', OCC),
    X(F, 1214, '"posée"', OCC),
    X(F, 1232, '"logement de "', OCC),
    X(F, 1236, '"socle de "', OCC),
    X(F, 1236, '"sous la mention"', OCC),
    X(F, 1241, '"logement de "', OCC),
    X(F, 1241, '"dans l\'anneau"', OCC),

    # ── phase du Sceau ────────────────────────────────────────────────────────────────────────────────────────
    S(F, 2891, J('"phase " + r2(sealPhaseLive) + " (survol) — le fichier livré garde "',
                 '          + r2(SEAL_PHASE)'),
      'dzT("cartes.frame1.phase_survol", { v: r2(sealPhaseLive), canon: r2(SEAL_PHASE) })',
      {"cartes.frame1.phase_survol": ("phase {v} (survol) — le fichier livré garde {canon}",
                                      "phase {v} (hover) — the delivered file keeps {canon}")}),
    S(F, 2893, '"phase canonique " + r2(SEAL_PHASE) + " — celle du fichier livré"',
      'dzT("cartes.frame1.phase_canon", { canon: r2(SEAL_PHASE) })',
      {"cartes.frame1.phase_canon": ("phase canonique {canon} — celle du fichier livré",
                                     "canonical phase {canon} — the one in the delivered file")}),

    # ── textes peints dans la toile, polices, MIME (X) ───────────────────────────────────────────────────────
    X(F, 2980, '"décor de cadre manquant"', TOILE),
    X(F, 3259, '"image/"', "chemin de route /api"),
    X(F, 3358, '\'px "Segoe UI", system-ui, sans-serif\'', "police canvas"),
    X(F, 3445, '"calque "', TOILE),
    X(F, 3445, '" manquant"', TOILE),
    X(F, 3504, '"image du dos manquante"', TOILE),
    X(F, 3649, '\'px "Segoe UI", system-ui, sans-serif\'', "police canvas"),
    X(F, 3727, '\'px "Segoe UI", system-ui, sans-serif\'', "police canvas"),

    # ── module, annulation ────────────────────────────────────────────────────────────────────────────────────
    L(F, 3740, '"Cadre"', "cartes.frame1.titre", "Cadre", "Frame"),
    L(F, 3839, '"rien à annuler"', "cartes.frame1.rien_annuler", "rien à annuler", "nothing to undo"),
    S(F, 3846, 'M.toast("annulé" + (h.label ? " : " + h.label : ""));',
      'M.toast(h.label ? dzT("cartes.frame1.annule_quoi", { quoi: h.label }) : dzT("cartes.frame1.annule"));',
      {"cartes.frame1.annule": ("annulé", "undone", "contexte"),
       "cartes.frame1.annule_quoi": ("annulé : {quoi}", "undone: {quoi}")}),
    L(F, 3850, '"rien à rétablir"', "cartes.frame1.rien_retablir", "rien à rétablir", "nothing to redo"),

    # ── adopter la bordure : les précisions ───────────────────────────────────────────────────────────────────
    S(F, 3946, '"ramenée à " + mm1(bande) + " mm, la borne du curseur"',
      'dzT("cartes.frame1.adopt_ramenee", { mm: mm1(bande) })',
      {"cartes.frame1.adopt_ramenee": ("ramenée à {mm} mm, la borne du curseur", "clamped to {mm} mm, the slider limit")}),
    L(F, 3949, '"rayon non mesuré, fenêtre inchangée"', "cartes.frame1.adopt_sans_rayon",
      "rayon non mesuré, fenêtre inchangée", "radius not measured, window unchanged"),
    S(F, 3960, '"rayon " + mm1(ray) + " mm sur la fenêtre"',
      'dzT("cartes.frame1.adopt_rayon", { mm: mm1(ray) })',
      {"cartes.frame1.adopt_rayon": ("rayon {mm} mm sur la fenêtre", "radius {mm} mm on the window")}),
    L(F, 3961, '" (ramené à la borne)"', "cartes.frame1.adopt_rayon_borne", " (ramené à la borne)", " (clamped to the limit)"),
    S(F, 3967, J('"la fenêtre cesse de se re-proportionner au format "',
                 '          + "(Ctrl+Z la rend automatique)"'),
      'dzT("cartes.frame1.adopt_gel")',
      {"cartes.frame1.adopt_gel": ("la fenêtre cesse de se re-proportionner au format (Ctrl+Z la rend automatique)",
                                   "the window stops re-fitting to the format (Ctrl+Z makes it automatic again)")}),
    S(F, 3972, J('(bo.confidence < CONF_FAIBLE ? "mesure PEU SÛRE, confiance "',
                 '        : "confiance ") + nb2(bo.confidence)'),
      J('(bo.confidence < CONF_FAIBLE ? dzT("cartes.frame1.adopt_conf_faible", { v: nb2(bo.confidence) })',
        '        : dzT("cartes.frame1.adopt_conf", { v: nb2(bo.confidence) }))'),
      {"cartes.frame1.adopt_conf_faible": ("mesure PEU SÛRE, confiance {v}", "UNRELIABLE measurement, confidence {v}"),
       "cartes.frame1.adopt_conf": ("confiance {v}", "confidence {v}")}),

    # ── l'aide libT (libellés du catalogue figé, à l'affichage) ───────────────────────────────────────────────
    S(F, 3998, 'function f() { return st(CF.doc()); }',
      J('function f() { return st(CF.doc()); }',
        '  /* t147 : un libellé du CATALOGUE (figé, comparé au backend) traduit à l\'AFFICHAGE par le dictionnaire',
        '     de la surcouche — en français, ou hors navigateur, il revient intact. */',
        '  function libT(s) {',
        '    const T = (typeof window !== "undefined" && window.__dzI18n && typeof window.__dzI18n.traduire === "function")',
        '      ? window.__dzI18n.traduire(String(s == null ? "" : s)) : null;',
        '    return T == null ? s : T;',
        '  }'),
      {}),

    # ── en-tête ───────────────────────────────────────────────────────────────────────────────────────────────
    L(F, 4008, '"Annuler"', "cartes.frame1.annuler", "Annuler", "Undo", contexte=True),
    L(F, 4010, '"Rétablir"', "cartes.frame1.retablir", "Rétablir", "Redo"),
    L(F, 4011, '"Réinitialiser"', "cartes.frame1.reinitialiser", "Réinitialiser", "Reset"),
    L(F, 4016, '"occupation…"', "cartes.frame1.occupation_attente", "occupation…", "occupancy…"),
    L(F, 4026, '"vérification…"', "cartes.frame1.verification_attente", "vérification…", "checking…"),
    L(F, 4028, '"Ctrl+Maj+Z"', "cartes.frame1.raccourci_retablir", "Ctrl+Maj+Z", "Ctrl+Shift+Z"),
    L(F, 4031, '"réinitialisation"', "cartes.frame1.h_reinitialisation", "réinitialisation", "reset"),
    L(F, 4039, '"Aucun cadre sur cette carte. Un modèle pour démarrer :"', "cartes.frame1.vide",
      "Aucun cadre sur cette carte. Un modèle pour démarrer :", "No frame on this card. A template to start with:"),
    S(F, 4042, 'h("button", "btn sm", esc(p.label))', 'h("button", "btn sm", esc(libT(p.label)))', {}),
    S(F, 4044, '"modèle " + p.label', 'dzT("cartes.frame1.h_modele", { nom: libT(p.label) })',
      {"cartes.frame1.h_modele": ("modèle {nom}", "template {nom}")}),

    # ── colonne A ─────────────────────────────────────────────────────────────────────────────────────────────
    S(F, 4056, 'label("Famille graphique", FAMILIES.length + " familles")',
      'label(dzT("cartes.frame1.famille_graphique"), dzT("cartes.frame1.n_familles", { n: FAMILIES.length }))',
      {"cartes.frame1.famille_graphique": ("Famille graphique", "Frame family"),
       "cartes.frame1.n_familles": ("{n} familles", "{n} families")}),
    S(F, 4059, 'label("Rareté", RARITIES.length + " variantes")',
      'label(dzT("cartes.frame1.rarete"), dzT("cartes.frame1.n_variantes", { n: RARITIES.length }))',
      {"cartes.frame1.rarete": ("Rareté", "Rarity"),
       "cartes.frame1.n_variantes": ("{n} variantes", "{n} variants")}),
    S(F, 4069, '"Les " + (FAMILIES.length * RARITIES.length) + " combinaisons"',
      'dzT("cartes.frame1.n_combinaisons", { n: FAMILIES.length * RARITIES.length })',
      {"cartes.frame1.n_combinaisons": ("Les {n} combinaisons", "All {n} combinations")}),
    L(F, 4078, '"Loupe — le fichier livré, agrandi"', "cartes.frame1.loupe",
      "Loupe — le fichier livré, agrandi", "Magnifier — the delivered file, enlarged"),
    L(F, 4085, '"Zone"', "cartes.frame1.zone", "Zone", "Area"),
    L(F, 4086, '"Face"', "cartes.frame1.face", "Face", "Side", contexte=True),

    # ── filets, bande et matière ──────────────────────────────────────────────────────────────────────────────
    L(F, 4107, '"Filets, bande et matière"', "cartes.frame1.g_filets", "Filets, bande et matière", "Lines, band and material"),
    L(F, 4108, '"Épaisseur du filet"', "cartes.frame1.epaisseur_filet", "Épaisseur du filet", "Line thickness"),
    L(F, 4111, '"Double filet"', "cartes.frame1.double_filet", "Double filet", "Double line"),
    L(F, 4111, '"double filet"', "cartes.frame1.h_double_filet", "double filet", "double line"),
    L(F, 4113, '"Écart"', "cartes.frame1.ecart", "Écart", "Gap"),
    L(F, 4121, '"Retrait du filet depuis la coupe — AXE du trait"', "cartes.frame1.retrait_filet",
      "Retrait du filet depuis la coupe — AXE du trait", "Line inset from the trim — stroke CENTER"),
    L(F, 4126, '"Marge intérieure (bande)"', "cartes.frame1.marge_interieure", "Marge intérieure (bande)", "Inner margin (band)"),
    L(F, 4132, '"couleur de filet"', "cartes.frame1.h_couleur_filet", "couleur de filet", "line color"),
    L(F, 4133, '"couleur de la rareté"', "cartes.frame1.couleur_rarete", "couleur de la rareté", "rarity color"),
    L(F, 4135, '"couleur automatique"', "cartes.frame1.h_couleur_auto", "couleur automatique", "automatic color"),
    L(F, 4136, '"Couleur du filet"', "cartes.frame1.couleur_filet", "Couleur du filet", "Line color"),
    L(F, 4141, '"Liseré métallique"', "cartes.frame1.lisere_metal", "Liseré métallique", "Metallic edging"),
    L(F, 4141, '"liseré métallique"', "cartes.frame1.h_lisere_metal", "liseré métallique", "metallic edging"),
    L(F, 4142, '"métal"', "cartes.frame1.h_metal", "métal", "metal"),
    L(F, 4144, '"Métal"', "cartes.frame1.metal", "Métal", "Metal"),
    L(F, 4148, '"Dégradé de bande"', "cartes.frame1.degrade_bande", "Dégradé de bande", "Band gradient"),
    L(F, 4148, '"dégradé"', "cartes.frame1.h_degrade", "dégradé", "gradient"),

    # ── le Sceau ──────────────────────────────────────────────────────────────────────────────────────────────
    L(F, 4159, '"Sceau prismatique — contour holographique"', "cartes.frame1.g_sceau",
      "Sceau prismatique — contour holographique", "Prismatic seal — holographic outline"),
    L(F, 4167, '"Contour holographique"', "cartes.frame1.contour_holo", "Contour holographique", "Holographic outline"),
    L(F, 4167, '"sceau"', "cartes.frame1.h_sceau", "sceau", "seal"),
    L(F, 4168, '"métal du sceau"', "cartes.frame1.h_metal_sceau", "métal du sceau", "seal metal"),
    L(F, 4170, '"Métal"', "cartes.frame1.metal", "Métal", "Metal"),
    L(F, 4172, '"Largeur de bande du filigrane"', "cartes.frame1.largeur_sceau", "Largeur de bande du filigrane", "Filigree band width"),
    L(F, 4176, '"Portée"', "cartes.frame1.portee", "Portée", "Scope"),
    L(F, 4176, '"trois surfaces indépendantes"', "cartes.frame1.portee_aide", "trois surfaces indépendantes", "three independent surfaces"),
    L(F, 4179, '"écran"', "cartes.frame1.portee_ecran", "écran", "screen"),
    L(F, 4179, '"impression"', "cartes.frame1.portee_impression", "impression", "print"),
    S(F, 4182, '"portée " + kv[1]', 'dzT("cartes.frame1.h_portee", { quoi: kv[1] })',
      {"cartes.frame1.h_portee": ("portée {quoi}", "scope {quoi}")}),
    L(F, 4192, '"Aperçu du contour"', "cartes.frame1.apercu_contour", "Aperçu du contour", "Outline preview"),
    L(F, 4193, '"survolez : la lumière tourne, le fichier ne bouge pas"', "cartes.frame1.apercu_contour_aide",
      "survolez : la lumière tourne, le fichier ne bouge pas", "hover: the light turns, the file does not move"),
    S(F, 4195, J('"Les mêmes arrêts de dégradé que l\'anneau du Sceau. "',
                 '      + "Le survol fait vivre la phase autour de la valeur canonique — À "',
                 '      + "L\'ÉCRAN SEULEMENT : le fichier livré garde la phase " + SEAL_PHASE',
                 '      + ", et rien de ce réglage n\'est écrit dans le jeu."'),
      'dzT("cartes.frame1.apercu_contour_titre", { phase: SEAL_PHASE })',
      {"cartes.frame1.apercu_contour_titre": (
          "Les mêmes arrêts de dégradé que l'anneau du Sceau. Le survol fait vivre la phase autour de la valeur "
          "canonique — À L'ÉCRAN SEULEMENT : le fichier livré garde la phase {phase}, et rien de ce réglage n'est "
          "écrit dans le jeu.",
          "The same gradient stops as the Seal ring. Hovering moves the phase around the canonical value — ON "
          "SCREEN ONLY: the delivered file keeps phase {phase}, and nothing of this setting is written to the deck.")}),

    # ── décor par IA ──────────────────────────────────────────────────────────────────────────────────────────
    L(F, 4211, '"Décor de cadre par IA"', "cartes.frame1.g_decor", "Décor de cadre par IA", "AI frame decoration"),
    L(F, 4216, '"Modèle"', "cartes.frame1.modele", "Modèle", "Model"),
    L(F, 4218, '"Invite"', "cartes.frame1.invite", "Invite", "Prompt"),
    L(F, 4218, '"pré-remplie par l\'archétype du jeu"', "cartes.frame1.invite_aide",
      "pré-remplie par l'archétype du jeu", "pre-filled from the deck archetype"),
    L(F, 4227, '"Générer le décor"', "cartes.frame1.decor_generer", "Générer le décor", "Generate decoration"),
    L(F, 4230, '"Retirer le décor"', "cartes.frame1.decor_retirer", "Retirer le décor", "Remove decoration"),
    S(F, 4232, J('"Le fichier reste dans le magasin d\'images de l\'application ; "',
                 '      + "seul le cadre cesse de le montrer"'),
      'dzT("cartes.frame1.decor_retirer_titre")',
      {"cartes.frame1.decor_retirer_titre": (
          "Le fichier reste dans le magasin d'images de l'application ; seul le cadre cesse de le montrer",
          "The file stays in the app's image store; only the frame stops showing it")}),
    L(F, 4234, '"décor retiré"', "cartes.frame1.h_decor_retire", "décor retiré", "decoration removed"),
    L(F, 4237, '"Opacité du décor"', "cartes.frame1.decor_opacite", "Opacité du décor", "Decoration opacity"),

    # ── fenêtre d'illustration ────────────────────────────────────────────────────────────────────────────────
    L(F, 4246, '"Fenêtre d\'illustration"', "cartes.frame1.g_fenetre", "Fenêtre d'illustration", "Art window"),
    L(F, 4250, '"Glisser = déplacer · poignée = redimensionner · glisser sur le fond = redessiner · flèches = 1 mm (Maj = 0,2 mm) · double-clic = auto"',
      "cartes.frame1.carte_titre",
      "Glisser = déplacer · poignée = redimensionner · glisser sur le fond = redessiner · flèches = 1 mm (Maj = 0,2 mm) · double-clic = auto",
      "Drag = move · handle = resize · drag on background = redraw · arrows = 1 mm (Shift = 0.2 mm) · double-click = auto"),
    L(F, 4255, '"Largeur"', "cartes.frame1.largeur", "Largeur", "Width"),
    L(F, 4255, '"Hauteur"', "cartes.frame1.hauteur", "Hauteur", "Height"),
    L(F, 4255, '"Rayon"', "cartes.frame1.rayon", "Rayon", "Radius"),
    L(F, 4260, '"Verrou de proportions"', "cartes.frame1.verrou", "Verrou de proportions", "Aspect lock"),
    L(F, 4260, '"verrou"', "cartes.frame1.h_verrou", "verrou", "lock"),
    L(F, 4263, '"Plein cadre"', "cartes.frame1.win_plein", "Plein cadre", "Full frame"),
    L(F, 4263, '"Haut"', "cartes.frame1.win_haut", "Haut", "Top", contexte=True),
    L(F, 4263, '"Carré"', "cartes.frame1.win_carre", "Carré", "Square"),
    L(F, 4263, '"Nombre d\'or"', "cartes.frame1.win_or", "Nombre d'or", "Golden ratio"),
    S(F, 4281, J('"Couleur du liseré propre de la fenêtre — "',
                 '      + "indépendant de la moulure de la famille et du filet du cadre. "',
                 '      + "Tant que l\'épaisseur vaut 0, aucun liseré n\'est peint."'),
      'dzT("cartes.frame1.lisere_titre")',
      {"cartes.frame1.lisere_titre": (
          "Couleur du liseré propre de la fenêtre — indépendant de la moulure de la famille et du filet du cadre. "
          "Tant que l'épaisseur vaut 0, aucun liseré n'est peint.",
          "Color of the window's own edging — independent of the family molding and the frame line. "
          "While the thickness is 0, no edging is painted.")}),
    L(F, 4285, '"liseré de fenêtre"', "cartes.frame1.h_lisere_fenetre", "liseré de fenêtre", "window edging"),
    L(F, 4286, '"Liseré"', "cartes.frame1.lisere", "Liseré", "Border"),
    L(F, 4287, '"Épaisseur du liseré"', "cartes.frame1.lisere_epaisseur", "Épaisseur du liseré", "Edging thickness"),
    S(F, 4301, J('"Le liseré est <b>centré</b> sur le bord de la fenêtre : il pose la "',
                 '      + "<b>moitié de son épaisseur</b> de chaque côté. Sur une fenêtre calée "',
                 '      + "au trait de coupe, un liseré de " + r2(LIMITS.win_stroke_mm[1])',
                 '      + " mm met donc " + r2(LIMITS.win_stroke_mm[1] / 2)',
                 '      + " mm dans le <b>fond perdu</b> — de l\'encre que la lame emporte. "',
                 '      + "C\'est voulu quand on borde une illustration à fond perdu ; ailleurs, "',
                 '      + "rentrez la fenêtre d\'autant."'),
      'dzT("cartes.frame1.lisere_aide", { max: r2(LIMITS.win_stroke_mm[1]), demi: r2(LIMITS.win_stroke_mm[1] / 2) })',
      {"cartes.frame1.lisere_aide": (
          "Le liseré est <b>centré</b> sur le bord de la fenêtre : il pose la <b>moitié de son épaisseur</b> de "
          "chaque côté. Sur une fenêtre calée au trait de coupe, un liseré de {max} mm met donc {demi} mm dans le "
          "<b>fond perdu</b> — de l'encre que la lame emporte. C'est voulu quand on borde une illustration à fond "
          "perdu ; ailleurs, rentrez la fenêtre d'autant.",
          "The edging is <b>centered</b> on the window edge: it puts <b>half its thickness</b> on each side. On a "
          "window aligned to the cut line, a {max} mm edging therefore puts {demi} mm into the <b>bleed</b> — ink the "
          "blade cuts away. That is intended when edging full-bleed art; elsewhere, move the window in by that much.")}),

    # ── ornements, gemme, bandeau, plaque ─────────────────────────────────────────────────────────────────────
    L(F, 4311, '"Ornements"', "cartes.frame1.g_ornements", "Ornements", "Ornaments"),
    L(F, 4313, '"ornement de coin"', "cartes.frame1.h_ornement_coin", "ornement de coin", "corner ornament"),
    L(F, 4314, '"Coins"', "cartes.frame1.coins", "Coins", "Corners"),
    L(F, 4315, '"Gemme de rareté"', "cartes.frame1.gemme_rarete", "Gemme de rareté", "Rarity gem"),
    L(F, 4315, '"gemme"', "cartes.frame1.h_gemme", "gemme", "gem"),
    L(F, 4322, '"Coins : décalage X"', "cartes.frame1.coins_dx", "Coins : décalage X", "Corners: X offset"),
    L(F, 4324, '"Coins : décalage Y"', "cartes.frame1.coins_dy", "Coins : décalage Y", "Corners: Y offset"),
    L(F, 4326, '"Coins : échelle"', "cartes.frame1.coins_echelle", "Coins : échelle", "Corners: scale"),
    L(F, 4337, '"Gemme X"', "cartes.frame1.gemme_x", "Gemme X", "Gem X"),
    L(F, 4338, '"Gemme Y"', "cartes.frame1.gemme_y", "Gemme Y", "Gem Y"),
    L(F, 4339, '"Rayon"', "cartes.frame1.rayon", "Rayon", "Radius"),
    S(F, 4345, J('"Rend le placement de la gemme au calcul : elle réessaie les "',
                 '      + "quatre coins et se range en écrin quand aucun n\'est libre"'),
      'dzT("cartes.frame1.gemme_auto_titre")',
      {"cartes.frame1.gemme_auto_titre": (
          "Rend le placement de la gemme au calcul : elle réessaie les quatre coins et se range en écrin quand "
          "aucun n'est libre",
          "Returns the gem to automatic placement: it tries the four corners again and tucks into a seat when none "
          "is free")}),
    L(F, 4351, '"plan de la gemme"', "cartes.frame1.h_plan_gemme", "plan de la gemme", "gem layer"),
    S(F, 4352, J('"« au-dessus des blocs » = le décor haut de toujours ; "',
                 '      + "« sous les blocs » = la gemme passe sous tout ce que la mise en page "',
                 '      + "empile (textes, images, formes)"'),
      'dzT("cartes.frame1.plan_gemme_titre")',
      {"cartes.frame1.plan_gemme_titre": (
          "« au-dessus des blocs » = le décor haut de toujours ; « sous les blocs » = la gemme passe sous tout ce "
          "que la mise en page empile (textes, images, formes)",
          "“above blocks” = the usual top decoration; “below blocks” = the gem goes under everything the layout "
          "stacks (text, images, shapes)")}),
    L(F, 4355, '"Plan"', "cartes.frame1.plan", "Plan", "Layer", contexte=True),
    L(F, 4360, '"Bandeau"', "cartes.frame1.bandeau", "Bandeau", "Banner"),
    L(F, 4360, '"bandeau"', "cartes.frame1.h_bandeau", "bandeau", "banner"),
    L(F, 4363, '"nom de la rareté"', "cartes.frame1.bandeau_ph", "nom de la rareté", "rarity name"),
    L(F, 4365, '"texte du bandeau"', "cartes.frame1.h_texte_bandeau", "texte du bandeau", "banner text"),
    L(F, 4367, '"Texte"', "cartes.frame1.texte", "Texte", "Text"),
    L(F, 4369, '"plan du bandeau"', "cartes.frame1.h_plan_bandeau", "plan du bandeau", "banner layer"),
    S(F, 4370, J('"« au-dessus des blocs » = le décor haut de "',
                 '      + "toujours ; « sous les blocs » = le bandeau passe sous tout ce que "',
                 '      + "la mise en page empile"'),
      'dzT("cartes.frame1.plan_bandeau_titre")',
      {"cartes.frame1.plan_bandeau_titre": (
          "« au-dessus des blocs » = le décor haut de toujours ; « sous les blocs » = le bandeau passe sous tout ce "
          "que la mise en page empile",
          "“above blocks” = the usual top decoration; “below blocks” = the banner goes under everything the layout "
          "stacks")}),
    L(F, 4373, '"Plan"', "cartes.frame1.plan", "Plan", "Layer", contexte=True),
    L(F, 4378, '"Bandeau X"', "cartes.frame1.bandeau_x", "Bandeau X", "Banner X"),
    L(F, 4379, '"Bandeau Y"', "cartes.frame1.bandeau_y", "Bandeau Y", "Banner Y"),
    S(F, 4384, J('"Rend le placement du bandeau au calcul : il reprend sa "',
                 '      + "voie libre sous la fenêtre"'),
      'dzT("cartes.frame1.bandeau_auto_titre")',
      {"cartes.frame1.bandeau_auto_titre": (
          "Rend le placement du bandeau au calcul : il reprend sa voie libre sous la fenêtre",
          "Returns the banner to automatic placement: it goes back to its free lane under the window")}),
    L(F, 4392, '"Plaque de texte"', "cartes.frame1.plaque", "Plaque de texte", "Text plate"),
    L(F, 4392, '"plaque"', "cartes.frame1.h_plaque", "plaque", "plate"),
    L(F, 4393, '"Opacité"', "cartes.frame1.opacite", "Opacité", "Opacity"),

    # ── occupation ────────────────────────────────────────────────────────────────────────────────────────────
    L(F, 4400, '"Occupation du cadre — meubles, logements, recouvrements"', "cartes.frame1.g_occupation",
      "Occupation du cadre — meubles, logements, recouvrements", "Frame occupancy — fixtures, seats, overlaps"),
    L(F, 4403, '"Écarter les meubles des mentions"', "cartes.frame1.ecarter", "Écarter les meubles des mentions",
      "Keep fixtures clear of card text"),
    L(F, 4403, '"éviter les mentions"', "cartes.frame1.h_eviter", "éviter les mentions", "avoid card text"),
    L(F, 4404, '"Socle sous le texte posé sur l\'illustration"', "cartes.frame1.socles",
      "Socle sous le texte posé sur l'illustration", "Backing under text placed on the art"),
    L(F, 4404, '"socles"', "cartes.frame1.h_socles", "socles", "backings"),
    L(F, 4408, '"Logement des chiffres qui débordent de la bande"', "cartes.frame1.logements",
      "Logement des chiffres qui débordent de la bande", "Seats for numbers that overflow the band"),
    L(F, 4408, '"logements"', "cartes.frame1.h_logements", "logements", "seats"),
    L(F, 4409, '"Opacité des socles"', "cartes.frame1.socles_opacite", "Opacité des socles", "Backing opacity"),

    # ── dos de carte ──────────────────────────────────────────────────────────────────────────────────────────
    L(F, 4419, '"Dos de carte"', "cartes.frame1.g_dos", "Dos de carte", "Card back"),
    L(F, 4426, '"Dos commun à tout le jeu"', "cartes.frame1.dos_commun", "Dos commun à tout le jeu", "Same back for the whole deck"),
    L(F, 4426, '"dos commun"', "cartes.frame1.h_dos_commun", "dos commun", "shared back"),
    L(F, 4427, '"Nom du jeu au dos"', "cartes.frame1.nom_au_dos", "Nom du jeu au dos", "Deck name on the back"),
    L(F, 4427, '"nom au dos"', "cartes.frame1.h_nom_au_dos", "nom au dos", "name on back"),
    L(F, 4431, '"Voir le dos"', "cartes.frame1.voir_dos", "Voir le dos", "View back"),
    L(F, 4434, '"PNG dos 1:1 + pHYs"', "cartes.frame1.png_dos", "PNG dos 1:1 + pHYs", "PNG back 1:1 + pHYs"),
    L(F, 4436, '"Rend le VERSO à geom.canvas_px, écrit le chunk pHYs (définition) et les boîtes de coupe en tEXt, puis télécharge — local, gratuit"',
      "cartes.frame1.png_dos_titre",
      "Rend le VERSO à geom.canvas_px, écrit le chunk pHYs (définition) et les boîtes de coupe en tEXt, puis télécharge — local, gratuit",
      "Renders the BACK at geom.canvas_px, writes the pHYs chunk (resolution) and the trim boxes as tEXt, then downloads — local, free"),
    L(F, 4438, '"PNG recto 1:1 + pHYs"', "cartes.frame1.png_recto", "PNG recto 1:1 + pHYs", "PNG front 1:1 + pHYs"),
    L(F, 4440, '"Le même fichier que l\'aperçu, à geom.canvas_px, estampillé pHYs + tEXt"', "cartes.frame1.png_recto_titre",
      "Le même fichier que l'aperçu, à geom.canvas_px, estampillé pHYs + tEXt",
      "The same file as the preview, at geom.canvas_px, stamped pHYs + tEXt"),
    L(F, 4451, '"Déposez une image ici, collez-la (Ctrl+V)"', "cartes.frame1.depot",
      "Déposez une image ici, collez-la (Ctrl+V)", "Drop an image here, or paste it (Ctrl+V)"),
    L(F, 4452, '"Choisir un fichier…"', "cartes.frame1.choisir_fichier", "Choisir un fichier…", "Choose a file…"),
    X(F, 4458, '"image/*"', "type MIME du sélecteur de fichier"),
    L(F, 4477, '"Ajouter un calque"', "cartes.frame1.ajouter_calque", "Ajouter un calque", "Add a layer"),
    L(F, 4481, '"Calques du verso"', "cartes.frame1.calques_verso", "Calques du verso", "Back layers"),
    L(F, 4481, '"peints du haut vers le bas"', "cartes.frame1.calques_verso_aide", "peints du haut vers le bas",
      "painted from top to bottom"),
    L(F, 4491, '"Dos par carte : décocher « dos commun » — le motif est alors lu dans <b>card.back</b> (colonne du CSV, pièce 04), avec repli sur le motif commun."',
      "cartes.frame1.dos_par_carte",
      "Dos par carte : décocher « dos commun » — le motif est alors lu dans <b>card.back</b> (colonne du CSV, pièce 04), avec repli sur le motif commun.",
      "Per-card back: untick “shared back” — the pattern is then read from <b>card.back</b> (CSV column, piece 04), falling back to the shared pattern."),

    # ── preuves ───────────────────────────────────────────────────────────────────────────────────────────────
    L(F, 4498, '"Preuve sur les octets — le fichier livré, redécodé à la main"', "cartes.frame1.g_preuve",
      "Preuve sur les octets — le fichier livré, redécodé à la main", "Byte-level proof — the delivered file, decoded by hand"),
    L(F, 4500, '"Relire le recto livré"', "cartes.frame1.relire_recto", "Relire le recto livré", "Re-read delivered front"),
    L(F, 4501, '"Relire le verso livré"', "cartes.frame1.relire_verso", "Relire le verso livré", "Re-read delivered back"),
    L(F, 4505, '"vérification automatique…"', "cartes.frame1.verif_auto", "vérification automatique…", "automatic check…"),
    L(F, 4514, '"Les deux définitions — 300 et 600, sur les octets"', "cartes.frame1.sep_definitions",
      "Les deux définitions — 300 et 600, sur les octets", "Both resolutions — 300 and 600, on the bytes"),
    L(F, 4516, '"Rendre et relire les deux fichiers"', "cartes.frame1.rendre_relire", "Rendre et relire les deux fichiers",
      "Render and re-read both files"),
    S(F, 4518, J('"Conduit le bouton 600 de la barre de format, rend et estampille les deux fichiers, "',
                 '      + "relit leurs octets, puis repose la définition d\'origine"'),
      'dzT("cartes.frame1.rendre_relire_titre")',
      {"cartes.frame1.rendre_relire_titre": (
          "Conduit le bouton 600 de la barre de format, rend et estampille les deux fichiers, relit leurs octets, "
          "puis repose la définition d'origine",
          "Drives the 600 button of the format bar, renders and stamps both files, re-reads their bytes, then "
          "restores the original resolution")}),
    L(F, 4521, '"départ automatique…"', "cartes.frame1.depart_auto", "départ automatique…", "starting automatically…"),
    L(F, 4522, '"Télécharger les deux fichiers mesurés"', "cartes.frame1.telecharger_deux",
      "Télécharger les deux fichiers mesurés", "Download both measured files"),
    S(F, 4530, J('"Le même cadre, sorti <b>deux fois</b> par le chemin d\'export normal : une fois en 300, une "',
                 '      + "fois en 600 DPI. La toile de chaque définition est recalculée à partir des millimètres — "',
                 '      + "jamais multipliée — et le filet garde la <b>même épaisseur en millimètres</b>. Les octets "',
                 '      + "des deux fichiers sont ensuite relus pour y chercher les <b>deux traces d\'un "',
                 '      + "agrandissement</b> : un x2 au plus proche voisin recopie une ligne sur deux (<b>50 %</b>), "',
                 '      + "un x2 filtré rend chaque ligne impaire égale à la moyenne de ses voisines (<b>100 %</b>). "',
                 '      + "Un dessin refait à la bonne taille ne laisse ni l\'une ni l\'autre."'),
      'dzT("cartes.frame1.deux_definitions_aide")',
      {"cartes.frame1.deux_definitions_aide": (
          "Le même cadre, sorti <b>deux fois</b> par le chemin d'export normal : une fois en 300, une fois en 600 DPI. "
          "La toile de chaque définition est recalculée à partir des millimètres — jamais multipliée — et le filet "
          "garde la <b>même épaisseur en millimètres</b>. Les octets des deux fichiers sont ensuite relus pour y "
          "chercher les <b>deux traces d'un agrandissement</b> : un x2 au plus proche voisin recopie une ligne sur "
          "deux (<b>50 %</b>), un x2 filtré rend chaque ligne impaire égale à la moyenne de ses voisines "
          "(<b>100 %</b>). Un dessin refait à la bonne taille ne laisse ni l'une ni l'autre.",
          "The same frame, exported <b>twice</b> through the normal export path: once at 300, once at 600 DPI. "
          "Each resolution's canvas is recomputed from millimeters — never multiplied — and the line keeps the "
          "<b>same thickness in millimeters</b>. The bytes of both files are then re-read to look for the <b>two "
          "traces of upscaling</b>: a nearest-neighbor x2 copies every other row (<b>50 %</b>), a filtered x2 makes "
          "each odd row equal to the average of its neighbors (<b>100 %</b>). A drawing redone at the right size "
          "leaves neither.")}),
    L(F, 4540, '"Épreuve de contrôle — traits de coupe et mires"', "cartes.frame1.sep_epreuve",
      "Épreuve de contrôle — traits de coupe et mires", "Control proof — cut marks and targets"),
    L(F, 4542, '"Construire l\'épreuve de contrôle"', "cartes.frame1.construire_epreuve",
      "Construire l'épreuve de contrôle", "Build the control proof"),
    S(F, 4544, J('"Pose la toile livrée sur " + CTRL_MARGE + " mm de papier, y trace les huit traits "',
                 '      + "de coupe alignés sur la rogne et quatre mires — hors du fond perdu, donc hors de l\'encre"'),
      'dzT("cartes.frame1.construire_epreuve_titre", { mm: CTRL_MARGE })',
      {"cartes.frame1.construire_epreuve_titre": (
          "Pose la toile livrée sur {mm} mm de papier, y trace les huit traits de coupe alignés sur la rogne et "
          "quatre mires — hors du fond perdu, donc hors de l'encre",
          "Places the delivered canvas on {mm} mm of paper, draws the eight cut marks aligned with the trim and "
          "four targets — outside the bleed, so outside the ink")}),
    L(F, 4547, '"départ automatique…"', "cartes.frame1.depart_auto", "départ automatique…", "starting automatically…"),
    L(F, 4548, '"Télécharger l\'épreuve"', "cartes.frame1.telecharger_epreuve", "Télécharger l'épreuve", "Download the proof"),
    S(F, 4561, J('"Le PNG livré ne porte <b>aucun trait de coupe</b>, et c\'est voulu : du trait de coupe au bord "',
                 '      + "de toile il n\'y a que du <b>fond perdu</b>, un repère y serait de l\'encre sous la lame. "',
                 '      + "Un repère se pose hors du fond perdu — donc sur du papier en plus, donc dans un autre "',
                 '      + "fichier. C\'est celui-ci, et il dit lui-même qu\'il ne s\'imprime pas."'),
      'dzT("cartes.frame1.epreuve_aide")',
      {"cartes.frame1.epreuve_aide": (
          "Le PNG livré ne porte <b>aucun trait de coupe</b>, et c'est voulu : du trait de coupe au bord de toile il "
          "n'y a que du <b>fond perdu</b>, un repère y serait de l'encre sous la lame. Un repère se pose hors du fond "
          "perdu — donc sur du papier en plus, donc dans un autre fichier. C'est celui-ci, et il dit lui-même qu'il "
          "ne s'imprime pas.",
          "The delivered PNG carries <b>no cut marks</b>, and that is intended: from the cut line to the canvas edge "
          "there is only <b>bleed</b>, and a mark there would be ink under the blade. A mark goes outside the bleed "
          "— so on extra paper, so in another file. This is that file, and it says itself that it is not for "
          "printing.")}),
    L(F, 4571, '"Robustesse — les 12 formats, les 2 bornes du rayon"', "cartes.frame1.sep_robustesse",
      "Robustesse — les 12 formats, les 2 bornes du rayon", "Robustness — the 12 formats, both radius limits"),
    L(F, 4573, '"Relancer le balayage"', "cartes.frame1.relancer_balayage", "Relancer le balayage", "Re-run the sweep"),
    L(F, 4576, '"départ automatique…"', "cartes.frame1.depart_auto", "départ automatique…", "starting automatically…"),
    S(F, 4595, J('"<b>Raccourcis</b> — <kbd>Ctrl+Z</kbd>/<kbd>Ctrl+Maj+Z</kbd> annuler / rétablir · "',
                 '      + "<kbd>[</kbd> <kbd>]</kbd> famille · <kbd>,</kbd> <kbd>.</kbd> rareté · "',
                 '      + "<kbd>D</kbd> double filet · <kbd>M</kbd> métal · <kbd>G</kbd> gemme · <kbd>V</kbd> recto/verso"'),
      'dzT("cartes.frame1.raccourcis")',
      {"cartes.frame1.raccourcis": (
          "<b>Raccourcis</b> — <kbd>Ctrl+Z</kbd>/<kbd>Ctrl+Maj+Z</kbd> annuler / rétablir · <kbd>[</kbd> "
          "<kbd>]</kbd> famille · <kbd>,</kbd> <kbd>.</kbd> rareté · <kbd>D</kbd> double filet · <kbd>M</kbd> "
          "métal · <kbd>G</kbd> gemme · <kbd>V</kbd> recto/verso",
          "<b>Shortcuts</b> — <kbd>Ctrl+Z</kbd>/<kbd>Ctrl+Shift+Z</kbd> undo / redo · <kbd>[</kbd> "
          "<kbd>]</kbd> family · <kbd>,</kbd> <kbd>.</kbd> rarity · <kbd>D</kbd> double line · <kbd>M</kbd> "
          "metal · <kbd>G</kbd> gem · <kbd>V</kbd> front/back")}),

    # ── colonnes coulissantes ─────────────────────────────────────────────────────────────────────────────────
    L(F, 4636, '"épreuve & catalogue"', "cartes.frame1.col_a_min", "épreuve & catalogue", "proof & catalog"),
    L(F, 4637, '"réglages du cadre"', "cartes.frame1.col_b_min", "réglages du cadre", "frame settings"),
    S(F, 4639, '(kv[1] ? "Déployer la colonne " : "Replier la colonne ") + kv[2]',
      '(kv[1] ? dzT("cartes.frame1.deployer_col", { quoi: kv[2] }) : dzT("cartes.frame1.replier_col", { quoi: kv[2] }))',
      {"cartes.frame1.deployer_col": ("Déployer la colonne {quoi}", "Expand the {quoi} column"),
       "cartes.frame1.replier_col": ("Replier la colonne {quoi}", "Collapse the {quoi} column")}),
    L(F, 4647, '"Épreuve & catalogue"', "cartes.frame1.col_a", "Épreuve & catalogue", "Proof & catalog"),
    L(F, 4648, '"Réglages du cadre"', "cartes.frame1.col_b", "Réglages du cadre", "Frame settings"),

    # ── fabriques : les libellés du catalogue passent par libT ────────────────────────────────────────────────
    S(F, 4732, '\'">\' + esc(o.label) + "</option>"', '\'">\' + esc(libT(o.label)) + "</option>"', {}),
    S(F, 4738, '\'">\' + esc(v) + "</button>"', '\'">\' + esc(libT(v)) + "</button>"', {}),

    # ── champs de gemme / fenêtre / bandeau ───────────────────────────────────────────────────────────────────
    L(F, 4795, '"Millimètres depuis le coin de coupe · vide = placement calculé"', "cartes.frame1.champ_mm_titre",
      "Millimètres depuis le coin de coupe · vide = placement calculé",
      "Millimeters from the trim corner · empty = automatic placement"),
    L(F, 4800, '"gemme automatique"', "cartes.frame1.h_gemme_auto", "gemme automatique", "automatic gem"),
    L(F, 4812, '"gemme"', "cartes.frame1.h_gemme", "gemme", "gem"),
    L(F, 4846, '"fenêtre"', "cartes.frame1.h_fenetre", "fenêtre", "window"),
    L(F, 4849, '"fenêtre automatique"', "cartes.frame1.h_fenetre_auto", "fenêtre automatique", "automatic window"),
    S(F, 4859, '"fenêtre " + kind', 'dzT("cartes.frame1.h_fenetre_preset", { kind: kind })',
      {"cartes.frame1.h_fenetre_preset": ("fenêtre {kind}", "window {kind}")}),
    S(F, 5019, J('M.toast("la gemme est désormais posée à la main : elle ne suit plus "',
                 '      + "les mentions (Ctrl+Z, double-clic ou « Auto » la rendent automatique)");'),
      'M.toast(dzT("cartes.frame1.gel_gemme"));',
      {"cartes.frame1.gel_gemme": (
          "la gemme est désormais posée à la main : elle ne suit plus les mentions (Ctrl+Z, double-clic ou « Auto » "
          "la rendent automatique)",
          "the gem is now placed by hand: it no longer follows the card text (Ctrl+Z, double-click or “Auto” make "
          "it automatic again)")}),
    L(F, 5026, '"gemme automatique"', "cartes.frame1.h_gemme_auto", "gemme automatique", "automatic gem"),
    L(F, 5029, '"bandeau automatique"', "cartes.frame1.h_bandeau_auto", "bandeau automatique", "automatic banner"),
    S(F, 5036, J('M.toast("le bandeau est désormais posé à la main : il ne cherche plus "',
                 '      + "de voie libre (Ctrl+Z, double-clic ou « Auto » le rendent automatique)");'),
      'M.toast(dzT("cartes.frame1.gel_bandeau"));',
      {"cartes.frame1.gel_bandeau": (
          "le bandeau est désormais posé à la main : il ne cherche plus de voie libre (Ctrl+Z, double-clic ou "
          "« Auto » le rendent automatique)",
          "the banner is now placed by hand: it no longer looks for a free lane (Ctrl+Z, double-click or “Auto” "
          "make it automatic again)")}),
    L(F, 5051, '"Millimètres depuis le coin de coupe · vide = placement calculé"', "cartes.frame1.champ_mm_titre",
      "Millimètres depuis le coin de coupe · vide = placement calculé",
      "Millimeters from the trim corner · empty = automatic placement"),
    L(F, 5056, '"bandeau automatique"', "cartes.frame1.h_bandeau_auto", "bandeau automatique", "automatic banner"),
    L(F, 5062, '"bandeau"', "cartes.frame1.h_bandeau", "bandeau", "banner"),
    L(F, 5214, '"gemme"', "cartes.frame1.h_gemme", "gemme", "gem"),
    L(F, 5224, '"bandeau"', "cartes.frame1.h_bandeau", "bandeau", "banner"),
    L(F, 5233, '"fenêtre"', "cartes.frame1.h_fenetre", "fenêtre", "window"),
    L(F, 5248, '"fenêtre automatique"', "cartes.frame1.h_fenetre_auto", "fenêtre automatique", "automatic window"),

    # ── cellules du catalogue ─────────────────────────────────────────────────────────────────────────────────
    S(F, 5321, 'h("span", "cff-cn", esc(lbl))', 'h("span", "cff-cn", esc(libT(lbl)))', {}),
    S(F, 5322, 'h("i", "cff-cs", esc(sub))', 'h("i", "cff-cs", esc(libT(sub)))', {}),
    L(F, 5328, '"Aucun cadre"', "cartes.frame1.aucun_cadre", "Aucun cadre", "No frame"),
    L(F, 5328, '"carte nue"', "cartes.frame1.carte_nue", "carte nue", "bare card"),
    L(F, 5331, '"aucun cadre"', "cartes.frame1.h_aucun_cadre", "aucun cadre", "no frame"),
    S(F, 5335, '"famille " + fa.label', 'dzT("cartes.frame1.h_famille", { nom: libT(fa.label) })',
      {"cartes.frame1.h_famille": ("famille {nom}", "family {nom}")}),
    S(F, 5344, '"rareté " + ra.label', 'dzT("cartes.frame1.h_rarete", { nom: libT(ra.label) })',
      {"cartes.frame1.h_rarete": ("rareté {nom}", "rarity {nom}")}),
    S(F, 5351, '"dos " + bk.label', 'dzT("cartes.frame1.h_dos", { nom: libT(bk.label) })',
      {"cartes.frame1.h_dos": ("dos {nom}", "back {nom}")}),
    S(F, 5382, 'fa.label + " " + ra.label', 'libT(fa.label) + " " + libT(ra.label)', {}),

    # ── silhouettes ───────────────────────────────────────────────────────────────────────────────────────────
    S(F, 5460, 'FAMILIES[i].label + " x " + FAMILIES[j].label + " en « " + ra.label + " »"',
      'dzT("cartes.frame1.sil_paire", { a: libT(FAMILIES[i].label), b: libT(FAMILIES[j].label), r: libT(ra.label) })',
      {"cartes.frame1.sil_paire": ("{a} x {b} en « {r} »", "{a} x {b} in “{r}”")}),
    L(F, 5472, '"silhouettes : non mesurables"', "cartes.frame1.sil_non_mesurables", "silhouettes : non mesurables",
      "silhouettes: not measurable"),
    S(F, 5674, 'FAMILIES[i].label + " x " + FAMILIES[j].label + " en « " + ra.label + " »"',
      'dzT("cartes.frame1.sil_paire", { a: libT(FAMILIES[i].label), b: libT(FAMILIES[j].label), r: libT(ra.label) })',
      {"cartes.frame1.sil_paire": ("{a} x {b} en « {r} »", "{a} x {b} in “{r}”")}),
    S(F, 5708, J('V.distinct + "/" + V.total + " distinctes · familles "',
                 '      + (F ? (r1(F.all) + "/255 sur la toile livrée"',
                 '        + (fini ? "" : " (" + F.rangs + "/" + F.total + " raretés…)"))',
                 '        : "sur la toile livrée…")'),
      J('dzT("cartes.frame1.sil_badge", { n: V.distinct, total: V.total })',
        '      + (F ? (dzT("cartes.frame1.sil_badge_toile", { v: r1(F.all) })',
        '        + (fini ? "" : dzT("cartes.frame1.sil_badge_avance", { k: F.rangs, total: F.total })))',
        '        : dzT("cartes.frame1.sil_badge_attente"))'),
      {"cartes.frame1.sil_badge": ("{n}/{total} distinctes · familles ", "{n}/{total} distinct · families "),
       "cartes.frame1.sil_badge_toile": ("{v}/255 sur la toile livrée", "{v}/255 on the delivered canvas"),
       "cartes.frame1.sil_badge_avance": (" ({k}/{total} raretés…)", " ({k}/{total} rarities…)"),
       "cartes.frame1.sil_badge_attente": ("sur la toile livrée…", "on the delivered canvas…")}),
    # l'infobulle entière (l. 5721-5743) : elle COMMENCE dans la plage, la suite (5734-5743) en fait partie
    S(F, 5721, J('"Deux mesures, deux surfaces.\\n\\n"',
                 '      + "1) " + V.distinct + " signatures de pixels distinctes sur " + V.total',
                 '      + " vignettes affichées (" + V.dim[0] + " x " + V.dim[1] + " px) : deux entrées du "',
                 '      + "catalogue ne rendent jamais la même image.\\n\\n"',
                 '      + "2) Écart de silhouette sur gris NORMALISÉ — contraste renormalisé, donc une simple "',
                 '      + "recoloration tomberait à 0 — entre familles à rareté égale. Sur les vignettes, les "',
                 '      + V.paires + " paires — les SIX raretés, pas seulement celle qui est ouverte — donnent "',
                 '      + "au pire " + r2(V.worst) + "/255 (" + V.wp + ").\\n\\n"',
                 '      + (F',
                 '        ? ("3) LE MÊME ÉCART SUR LA TOILE LIVRÉE (" + F.w + " x " + F.h + " px, rendue par les "',
                 '          + "painters du fichier, " + F.rangs + " rareté(s) sur " + F.total + " balayées, "',
                 '          + F.paires + " paires) : au pire "',
                 '          + r2(F.all) + "/255 sur la toile entière, et " + r2(F.out) + "/255 hors fenêtre "',
                 '          + "d\'illustration — la fenêtre occupe " + r1(F.part * 100) + " % de la toile, elle porte "',
                 '          + "l\'illustration et non le cadre, elle dilue donc l\'écart. "',
                 '          + "La paire la plus serrée est " + F.pire + ". Mesure en " + F.ms + " ms.\\n\\n"',
                 '          + (F.masque_refus',
                 '            ? ("Les pixels recouverts par les autres couches n\'ont PAS pu être mis à zéro "',
                 '              + "(masque refusé) : le chiffre est donc un MAJORANT de ce que le fichier fini donnera.")',
                 '            : ("Les " + r1(F.masque * 100) + " % de pixels que les autres couches repeignent "',
                 '              + "par-dessus le cadre — le texte, notamment — sont comptés pour ZÉRO, "',
                 '              + "exactement comme dans le fichier livré.")))',
                 '        : "3) La mesure sur la toile livrée est en cours.")'),
      J('dzT("cartes.frame1.sil_titre_12", { n: V.distinct, total: V.total, w: V.dim[0], h: V.dim[1],',
        '        paires: V.paires, pire: r2(V.worst), wp: V.wp })',
        '      + (F',
        '        ? (dzT("cartes.frame1.sil_titre_3", { w: F.w, h: F.h, k: F.rangs, total: F.total, paires: F.paires,',
        '            all: r2(F.all), out: r2(F.out), part: r1(F.part * 100), pire: F.pire, ms: F.ms })',
        '          + (F.masque_refus',
        '            ? dzT("cartes.frame1.sil_masque_refus")',
        '            : dzT("cartes.frame1.sil_masque", { pct: r1(F.masque * 100) })))',
        '        : dzT("cartes.frame1.sil_titre_3_attente"))'),
      {"cartes.frame1.sil_titre_12": (
          "Deux mesures, deux surfaces.\n\n1) {n} signatures de pixels distinctes sur {total} vignettes affichées "
          "({w} x {h} px) : deux entrées du catalogue ne rendent jamais la même image.\n\n2) Écart de silhouette "
          "sur gris NORMALISÉ — contraste renormalisé, donc une simple recoloration tomberait à 0 — entre familles "
          "à rareté égale. Sur les vignettes, les {paires} paires — les SIX raretés, pas seulement celle qui est "
          "ouverte — donnent au pire {pire}/255 ({wp}).\n\n",
          "Two measurements, two surfaces.\n\n1) {n} distinct pixel signatures across {total} displayed thumbnails "
          "({w} x {h} px): no two catalog entries ever render the same image.\n\n2) Silhouette gap on NORMALIZED "
          "gray — contrast renormalized, so a mere recolor would drop to 0 — between families at equal rarity. On "
          "the thumbnails, the {paires} pairs — all SIX rarities, not just the open one — give at worst "
          "{pire}/255 ({wp}).\n\n"),
       "cartes.frame1.sil_titre_3": (
          "3) LE MÊME ÉCART SUR LA TOILE LIVRÉE ({w} x {h} px, rendue par les painters du fichier, {k} rareté(s) sur "
          "{total} balayées, {paires} paires) : au pire {all}/255 sur la toile entière, et {out}/255 hors fenêtre "
          "d'illustration — la fenêtre occupe {part} % de la toile, elle porte l'illustration et non le cadre, elle "
          "dilue donc l'écart. La paire la plus serrée est {pire}. Mesure en {ms} ms.\n\n",
          "3) THE SAME GAP ON THE DELIVERED CANVAS ({w} x {h} px, rendered by the file's painters, {k} of {total} "
          "rarities swept, {paires} pairs): at worst {all}/255 on the whole canvas, and {out}/255 outside the art "
          "window — the window covers {part} % of the canvas, it holds the art and not the frame, so it dilutes the "
          "gap. The tightest pair is {pire}. Measured in {ms} ms.\n\n"),
       "cartes.frame1.sil_masque_refus": (
          "Les pixels recouverts par les autres couches n'ont PAS pu être mis à zéro (masque refusé) : le chiffre "
          "est donc un MAJORANT de ce que le fichier fini donnera.",
          "Pixels covered by the other layers could NOT be zeroed (mask rejected): the figure is therefore an UPPER "
          "BOUND of what the finished file will give."),
       "cartes.frame1.sil_masque": (
          "Les {pct} % de pixels que les autres couches repeignent par-dessus le cadre — le texte, notamment — sont "
          "comptés pour ZÉRO, exactement comme dans le fichier livré.",
          "The {pct} % of pixels that other layers paint over the frame — text in particular — count as ZERO, "
          "exactly as in the delivered file."),
       "cartes.frame1.sil_titre_3_attente": ("3) La mesure sur la toile livrée est en cours.",
                                             "3) The measurement on the delivered canvas is in progress.")}),
]
