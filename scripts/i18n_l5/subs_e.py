"""t145 — subs_e : le contrôle qualité du backend et les écarts aperçu / gravure (aucun texte affiché), puis le TIROIR
« Sous-titres » (SubsDrawer) : note de langue détectée, estimation et geste « Traduire » (dzTraduire, nouvelle piste),
transcription (transcribe(plan) : étapes, notes de résultat et d'erreur), ligne des comptes et ses infobulles, onglets
Répliques / Style et placement, rangée qui dépense (transcrire, langue, cible, nouvelle piste), ligne qui confronte la
langue au texte ; enfin le contrat d'export window.DzSubs (aucun texte affiché).

Gardés : les classes CSS à espace ("sub-iconbtn sub-close", "sub-trlang sub-trnew", "sub-btn sub-lgfix") ; l'erreur
interne "pas de job_id" (jamais affichée : le rejet affiche sa propre note). Les valeurs comparées ("moteur" de
vd.source, "done", "failed", "auto", codes de langue) et les clés localStorage restent hors de toute traduction : les
S qui touchent `vd.source==="moteur"` réécrivent le seul libellé affiché. Les mots comptés réutilisent les clés
montage.sous_titres.* (réplique/line, signalée/flagged, bloquante/blocking, plan/clip) ; « défaut » (= defect, ailleurs
« default ») est en contexte ; « écart » reprend « diff » des Réglages."""
from outils import L, S, X

CIBLE = "subs"
PLAGE = (3417, 4058)

REP = 'dzT("montage.sous_titres.replique"),dzT("montage.sous_titres.repliques")'
PLN = 'dzT("montage.sous_titres.plan"),dzT("montage.sous_titres.plans")'
M_REP = {"montage.sous_titres.replique": ("réplique", "line"),
         "montage.sous_titres.repliques": ("répliques", "lines")}
M_PLN = {"montage.sous_titres.plan": ("plan", "clip"),
         "montage.sous_titres.plans": ("plans", "clips")}
M_SIG = {"montage.sous_titres.signalee": ("signalée", "flagged"),
         "montage.sous_titres.signalees": ("signalées", "flagged")}
M_BLO = {"montage.sous_titres.bloquante": ("bloquante", "blocking"),
         "montage.sous_titres.bloquantes": ("bloquantes", "blocking")}
ECART = {"subs.comptes.ecart": ("écart", "diff"), "subs.comptes.ecarts": ("écarts", "diffs")}
RAISON = {"subs.commun.raison_absente": ("raison non fournie", "no reason given")}

ENTREES = [
    # ── langue détectée (fireNote) ──
    S('''"Langue détectée d'après "+det.ou+" : "+subsLangLab(det.code)+
      " ("+det.hits+" mots reconnus sur "+det.total+
      "). Le sélecteur reste maître."''',
      'dzT("subs.langue.detectee",{ou:det.ou,langue:subsLangLab(det.code),hits:det.hits,total:det.total})',
      {"subs.langue.detectee": ("Langue détectée d'après {ou} : {langue} ({hits} mots reconnus sur {total}). "
                                "Le sélecteur reste maître.",
                                "Language detected from {ou}: {langue} ({hits} words recognized out of {total}). "
                                "The selector stays in charge.")}),

    # ── estimation de la traduction ──
    L('"Aucune clé LLM configurée (Réglages)."', "subs.traduction.aucune_cle",
      "Aucune clé LLM configurée (Réglages).", "No LLM key configured (Settings)."),
    S('''"Le backend ne répond pas : "+
        "le coût ne peut pas être annoncé, donc rien n'est lancé."''',
      'dzT("subs.traduction.backend_absent")',
      {"subs.traduction.backend_absent": ("Le backend ne répond pas : le coût ne peut pas être annoncé, donc rien "
                                          "n'est lancé.",
                                          "The backend is not responding: the cost cannot be announced, so nothing "
                                          "is started.")}),

    # ── dzTraduire ──
    S('''"traduction de "+subsPl(dzTrN,"réplique")+
      " vers "+subsLangLab(dzTo)+"…"''',
      'dzT("subs.traduction.etape",{repliques:subsPl(dzTrN,' + REP + '),langue:subsLangLab(dzTo)})',
      dict(M_REP, **{"subs.traduction.etape": ("traduction de {repliques} vers {langue}…",
                                               "translating {repliques} to {langue}…")})),
    S('''"Traduction refusée ("+o.res.status+") : "+
            String((o.d&&o.d.detail)||"raison non fournie")''',
      'dzT("subs.traduction.refusee",{code:o.res.status,raison:String((o.d&&o.d.detail)||dzT("subs.commun.raison_absente"))})',
      dict(RAISON, **{"subs.traduction.refusee": ("Traduction refusée ({code}) : {raison}",
                                                  "Translation refused ({code}): {raison}")})),
    S('''"Réponse illisible : le compte des répliques "+
          "ne correspond pas — rien n'a été écrit."''',
      'dzT("subs.traduction.illisible")',
      {"subs.traduction.illisible": ("Réponse illisible : le compte des répliques ne correspond pas — rien n'a été "
                                     "écrit.",
                                     "Unreadable response: the line count does not match — nothing was written.")}),
    S('''"Traduction indisponible : POST /api/subtitles/translate "+
          "ne répond pas — le backend est-il lancé ?"''',
      'dzT("subs.traduction.indisponible")',
      {"subs.traduction.indisponible": ("Traduction indisponible : POST /api/subtitles/translate ne répond pas — le "
                                        "backend est-il lancé ?",
                                        "Translation unavailable: POST /api/subtitles/translate is not responding — "
                                        "is the backend running?")}),

    # ── transcribe(plan) ──
    S('"plan "+plan.n+"…"', 'dzT("subs.transcription.etape_plan",{n:plan.n})',
      {"subs.transcription.etape_plan": ("plan {n}…", "clip {n}…")}),
    S('''"Aucun clip "+dzTd.toUpperCase()+" ou V1 porteur d'une source ne chevauche le plan n° "+plan.n+" — rien n'est envoyé."''',
      'dzT("subs.transcription.aucun_clip",{piste:dzTd.toUpperCase(),n:plan.n})',
      {"subs.transcription.aucun_clip": ("Aucun clip {piste} ou V1 porteur d'une source ne chevauche le plan n° {n} — "
                                         "rien n'est envoyé.",
                                         "No {piste} or V1 clip with a source overlaps clip #{n} — nothing is sent.")}),
    X('"pas de job_id"', "erreur interne jetée dans la promesse : le rejet affiche sa propre note, jamais ce texte"),
    S('''"Aucune parole détectée dans le plan n° "+plan.n+
                    " ("+subsTc(plan.start)+" → "+subsTc(plan.end)+"). "+
                    "Marquez-le « sans parole » s'il est muet."''',
      'dzT("subs.transcription.plan_muet",{n:plan.n,debut:subsTc(plan.start),fin:subsTc(plan.end)})',
      {"subs.transcription.plan_muet": ("Aucune parole détectée dans le plan n° {n} ({debut} → {fin}). Marquez-le "
                                        "« sans parole » s'il est muet.",
                                        "No speech detected in clip #{n} ({debut} → {fin}). Mark it “no speech” if "
                                        "it is silent.")}),
    S('''subsPl(dans.length,"réplique")+" ajoutée"+
                  (dans.length>1?"s":"")+" sur le plan n° "+plan.n+
                  " — relisez, la machine se trompe."''',
      '(dans.length>1?dzT("subs.transcription.ajoutees",{n:dans.length,plan:plan.n})'
      ':dzT("subs.transcription.ajoutee",{n:dans.length,plan:plan.n}))',
      {"subs.transcription.ajoutee": ("{n} réplique ajoutée sur le plan n° {plan} — relisez, la machine se trompe.",
                                      "{n} line added to clip #{plan} — review it, the machine makes mistakes."),
       "subs.transcription.ajoutees": ("{n} répliques ajoutées sur le plan n° {plan} — relisez, la machine se trompe.",
                                       "{n} lines added to clip #{plan} — review them, the machine makes mistakes.")}),
    L('"Transcription terminée : aucune parole détectée."', "subs.transcription.aucune_parole",
      "Transcription terminée : aucune parole détectée.", "Transcription finished: no speech detected."),
    S('got.length+" sous-titres transcrits — relisez, la machine se trompe."',
      'dzT("subs.transcription.transcrits",{n:got.length})',
      {"subs.transcription.transcrits": ("{n} sous-titres transcrits — relisez, la machine se trompe.",
                                         "{n} subtitles transcribed — review them, the machine makes mistakes.")}),
    S('"Transcription échouée : "+String(j&&j.error||"raison non fournie")',
      'dzT("subs.transcription.echouee",{raison:String(j&&j.error||dzT("subs.commun.raison_absente"))})',
      dict(RAISON, **{"subs.transcription.echouee": ("Transcription échouée : {raison}",
                                                     "Transcription failed: {raison}")})),
    L('"transcription…"', "subs.transcription.etape_defaut", "transcription…", "transcribing…"),
    L('"Suivi de la transcription perdu — le backend ne répond plus."', "subs.transcription.suivi_perdu",
      "Suivi de la transcription perdu — le backend ne répond plus.",
      "Lost track of the transcription — the backend no longer responds."),
    S('''"Transcription automatique indisponible : POST /api/subtitles/transcribe "+
          "ne répond pas. Tout le reste marche hors ligne — écrivez, importez "+
          "un .srt, ou relancez DeepotusVideoGen."''',
      'dzT("subs.transcription.indisponible")',
      {"subs.transcription.indisponible": ("Transcription automatique indisponible : POST /api/subtitles/transcribe ne "
                                           "répond pas. Tout le reste marche hors ligne — écrivez, importez un .srt, "
                                           "ou relancez DeepotusVideoGen.",
                                           "Automatic transcription unavailable: POST /api/subtitles/transcribe is not "
                                           "responding. Everything else works offline — type, import an .srt, or "
                                           "restart DeepotusVideoGen.")}),

    # ── en-tête du tiroir ──
    L('"Sous-titres"', "subs.tiroir.titre", "Sous-titres", "Subtitles", n=2),
    X('"sub-iconbtn sub-close"', "classes CSS"),
    L('"Fermer (Échap)"', "subs.tiroir.fermer", "Fermer (Échap)", "Close (Esc)"),
    L('"Fermer le panneau de sous-titres"', "subs.tiroir.fermer_aide", "Fermer le panneau de sous-titres",
      "Close the subtitles panel"),

    # ── ligne des comptes ──
    S('''"Signalées = répliques portant au moins un défaut. Bloquantes = "+
        "sous-ensemble des signalées, celles qui portent un défaut bloquant. "+
        "Défauts = total des défauts (une réplique peut en porter plusieurs). "+
        "Écarts = différences entre l'aperçu et la gravure ; ils portent sur "+
        "le style. Couvert = part du montage qui porte des sous-titres. "+
        "Tous ces chiffres sortent du même contrôle ("+
        (vd.source==="moteur"?"moteur":"calcul local")+")."''',
      'dzT("subs.comptes.aide",{source:vd.source==="moteur"?dzT("subs.comptes.moteur"):dzT("subs.comptes.calcul_local")})',
      {"subs.comptes.aide": ("Signalées = répliques portant au moins un défaut. Bloquantes = sous-ensemble des "
                             "signalées, celles qui portent un défaut bloquant. Défauts = total des défauts (une "
                             "réplique peut en porter plusieurs). Écarts = différences entre l'aperçu et la gravure ; "
                             "ils portent sur le style. Couvert = part du montage qui porte des sous-titres. Tous ces "
                             "chiffres sortent du même contrôle ({source}).",
                             "Flagged = lines with at least one defect. Blocking = subset of the flagged ones, those "
                             "with a blocking defect. Defects = total number of defects (a line can have several). "
                             "Diffs = differences between the preview and the burn-in; they concern the style. "
                             "Covered = share of the edit that has subtitles. All these figures come from the same "
                             "check ({source})."),
       "subs.comptes.moteur": ("moteur", "engine"),
       "subs.comptes.calcul_local": ("calcul local", "local computation")}),
    L('"réplique"', "montage.sous_titres.replique", "réplique", "line"),
    L('"répliques"', "montage.sous_titres.repliques", "répliques", "lines"),
    L('"signalée"', "montage.sous_titres.signalee", "signalée", "flagged"),
    L('"signalées"', "montage.sous_titres.signalees", "signalées", "flagged"),
    # "bloquantes" est aussi la valeur de data-k (sélecteur CSS / bancs) : on ne prend que le libellé
    S('C.bloquantes<2?"bloquante":"bloquantes"',
      'C.bloquantes<2?dzT("montage.sous_titres.bloquante"):dzT("montage.sous_titres.bloquantes")', M_BLO),
    X('"bloquantes"', "valeur de data-k (attribut lu par le CSS et les bancs)"),
    L('"défaut"', "subs.comptes.defaut", "défaut", "defect", contexte=True),
    L('"défauts"', "subs.comptes.defauts", "défauts", "defects"),
    L('"écart"', "subs.comptes.ecart", "écart", "diff"),
    L('"écarts"', "subs.comptes.ecarts", "écarts", "diffs"),
    S('''title:subsFr(vd.cov.couvert,1)+" s ÷ "+subsFr(vd.cov.attendu,1)+
          " s de plans à sous-titrer = "+vd.cov.pct+" %"+
          (C.plans_ignores?" ("+subsPl(C.plans_ignores,"plan")+
            " acquitté« sans parole » RETIRÉ du total, pas ajouté au "+
            "couvert)":"")+
          (C.plans_sans?" — "+subsPl(C.plans_sans,"plan")+
            " sans la moindre réplique, détail dans l'onglet Répliques":""),''',
      'title:dzT("subs.comptes.couverture_aide",{couvert:subsFr(vd.cov.couvert,1),attendu:subsFr(vd.cov.attendu,1),'
      'pct:vd.cov.pct})+\n'
      '          (C.plans_ignores?" ("+dzT("subs.comptes.acquittes_detail",{plans:subsPl(C.plans_ignores,' + PLN + ')})'
      '+")":"")+\n'
      '          (C.plans_sans?" — "+dzT("subs.comptes.plans_sans",{plans:subsPl(C.plans_sans,' + PLN + ')}):""),',
      dict(M_PLN, **{
          "subs.comptes.couverture_aide": ("{couvert} s ÷ {attendu} s de plans à sous-titrer = {pct} %",
                                           "{couvert} s ÷ {attendu} s of clips to subtitle = {pct} %"),
          "subs.comptes.acquittes_detail": ("{plans} acquitté« sans parole » RETIRÉ du total, pas ajouté au couvert",
                                            "{plans} dismissed as “no speech” REMOVED from the total, not added to "
                                            "the covered part"),
          "subs.comptes.plans_sans": ("{plans} sans la moindre réplique, détail dans l'onglet Répliques",
                                      "{plans} without a single line, details in the Lines tab")})),
    L('"couvert"', "subs.comptes.couvert", "couvert", "covered"),
    S('''"Plans que vous avez déclarés muets : ils sortent du calcul de "+
          "couverture mais sortiront muets à la livraison, exactement comme "+
          "avant l'acquittement. Détail et révocation dans l'onglet Répliques, "+
          "en tête de « Couverture du montage »."''',
      'dzT("subs.comptes.acquittes_aide")',
      {"subs.comptes.acquittes_aide": ("Plans que vous avez déclarés muets : ils sortent du calcul de couverture mais "
                                       "sortiront muets à la livraison, exactement comme avant l'acquittement. Détail "
                                       "et révocation dans l'onglet Répliques, en tête de « Couverture du montage ».",
                                       "Clips you declared silent: they leave the coverage computation but will be "
                                       "delivered silent, exactly as before the dismissal. Details and undo in the "
                                       "Lines tab, at the top of “Edit coverage”.")}),
    L('"plan acquitté"', "subs.comptes.plan_acquitte", "plan acquitté", "dismissed clip"),
    L('"plans acquittés"', "subs.comptes.plans_acquittes", "plans acquittés", "dismissed clips"),
    L('"masquée"', "subs.comptes.masquee", "masquée", "hidden"),
    L('"masquées"', "subs.comptes.masquees", "masquées", "hidden"),
    S('children:vd.source==="moteur"?"moteur":"local"',
      'children:vd.source==="moteur"?dzT("subs.comptes.moteur"):dzT("subs.comptes.local")',
      {"subs.comptes.moteur": ("moteur", "engine"), "subs.comptes.local": ("local", "local")}),

    # ── onglets ──
    S('''subsPl(C.signalees,"réplique")+" signalée"+
          (C.signalees>1?"s":"")+", dont "+subsPl(C.bloquantes,"bloquante")+
          " — le compte est écrit au-dessus, le détail sur chaque ligne"''',
      'dzT("subs.onglet.repliques_signalees",{repliques:subsPl(C.signalees,' + REP + '),'
      'signalee:C.signalees>1?dzT("montage.sous_titres.signalees"):dzT("montage.sous_titres.signalee"),'
      'bloquantes:subsPl(C.bloquantes,dzT("montage.sous_titres.bloquante"),dzT("montage.sous_titres.bloquantes"))})',
      dict(M_REP, **M_SIG, **M_BLO, **{
          "subs.onglet.repliques_signalees": ("{repliques} {signalee}, dont {bloquantes} — le compte est écrit "
                                              "au-dessus, le détail sur chaque ligne",
                                              "{repliques} {signalee}, including {bloquantes} — the count is written "
                                              "above, the details on each line")})),
    L('"La liste des répliques : bornes, texte, découpe, export"', "subs.onglet.repliques_aide",
      "La liste des répliques : bornes, texte, découpe, export", "The list of lines: bounds, text, splitting, export"),
    L('"Répliques"', "subs.onglet.repliques", "Répliques", "Lines"),
    S('''subsPl(C.ecarts,"écart")+" entre l'aperçu et la gravure "+
          "— le compte est écrit au-dessus, le détail en tête de cet onglet"''',
      'dzT("subs.onglet.ecarts_aide",{ecarts:subsPl(C.ecarts,dzT("subs.comptes.ecart"),dzT("subs.comptes.ecarts"))})',
      dict(ECART, **{"subs.onglet.ecarts_aide": ("{ecarts} entre l'aperçu et la gravure — le compte est écrit "
                                                 "au-dessus, le détail en tête de cet onglet",
                                                 "{ecarts} between the preview and the burn-in — the count is "
                                                 "written above, the details at the top of this tab")})),
    L('"Police, corps, couleur, fond, contour, karaoké et placement"', "subs.onglet.style_aide",
      "Police, corps, couleur, fond, contour, karaoké et placement",
      "Font, size, color, background, outline, karaoke and placement"),
    L('"Style et placement"', "subs.onglet.style", "Style et placement", "Style and placement"),

    # ── rangée qui dépense : transcrire ──
    L('"Caler la narration écrite"', "subs.transcription.caler", "Caler la narration écrite", "Align the written narration"),
    L('"Transcrire l\'audio"', "subs.transcription.transcrire", "Transcrire l'audio", "Transcribe the audio"),
    L('"sous-titrer tout le montage"', "subs.transcription.but", "sous-titrer tout le montage", "subtitle the whole edit"),
    L('"en cours…"', "subs.commun.en_cours", "en cours…", "in progress…", n=2),
    S('''" REMPLACE toute la piste S1 par le résultat ("+
          (C.repliques?subsPl(C.repliques,"réplique")+" posée"+
            (C.repliques>1?"s":"")+" aujourd'hui":"la piste est vide")+
          "). Pour ne toucher qu'un seul plan, prenez le geste en face de ce "+
          "plan, dans « Couverture du montage »."''',
      '" "+dzT("subs.transcription.remplace",{etat:C.repliques?(C.repliques>1'
      '?dzT("subs.transcription.posees",{n:C.repliques}):dzT("subs.transcription.posee",{n:C.repliques}))'
      ':dzT("subs.transcription.piste_vide")})',
      {"subs.transcription.remplace": ("REMPLACE toute la piste S1 par le résultat ({etat}). Pour ne toucher qu'un "
                                       "seul plan, prenez le geste en face de ce plan, dans « Couverture du montage ».",
                                       "REPLACES the whole S1 track with the result ({etat}). To change a single "
                                       "clip only, use the action next to that clip, in “Edit coverage”."),
       "subs.transcription.posee": ("{n} réplique posée aujourd'hui", "{n} line on it today"),
       "subs.transcription.posees": ("{n} répliques posées aujourd'hui", "{n} lines on it today"),
       "subs.transcription.piste_vide": ("la piste est vide", "the track is empty")}),
    L('"langue"', "subs.rangee.langue", "langue", "language"),
    L('"Langue de la transcription"', "subs.rangee.langue_aria", "Langue de la transcription",
      "Transcription language"),
    S('''"Langue annoncée au moteur : elle change le découpage en mots "+
            "et le calage sur les silences. Elle est écrite sur chaque bouton "+
            "qui lance une transcription."''',
      'dzT("subs.rangee.langue_aide")',
      {"subs.rangee.langue_aide": ("Langue annoncée au moteur : elle change le découpage en mots et le calage sur les "
                                   "silences. Elle est écrite sur chaque bouton qui lance une transcription.",
                                   "Language announced to the engine: it changes the word splitting and the "
                                   "alignment on silences. It is written on every button that starts a "
                                   "transcription.")}),

    # ── rangée qui dépense : traduire ──
    L('"vers"', "subs.rangee.vers", "vers", "to"),
    L('"Langue cible de la traduction"', "subs.rangee.cible_aria", "Langue cible de la traduction",
      "Translation target language"),
    S('''"Langue vers laquelle « Traduire » réécrit le texte des "+
            "répliques. Leurs temps ne bougent pas."''',
      'dzT("subs.rangee.cible_aide")',
      {"subs.rangee.cible_aide": ("Langue vers laquelle « Traduire » réécrit le texte des répliques. Leurs temps ne "
                                  "bougent pas.",
                                  "Language into which “Translate” rewrites the text of the lines. Their timings do "
                                  "not move.")}),
    X('"sub-trlang sub-trnew"', "classes CSS"),
    L('"Coché : la traduction naît dans une nouvelle piste de sous-titres S2, S3… (S1 reste intacte ; la piste gravée '
      'au rendu se choisit par clic droit sur sa tête). Décoché : S1 est réécrite."', "subs.rangee.nouvelle_piste_aide",
      "Coché : la traduction naît dans une nouvelle piste de sous-titres S2, S3… (S1 reste intacte ; la piste gravée "
      "au rendu se choisit par clic droit sur sa tête). Décoché : S1 est réécrite.",
      "Checked: the translation goes into a new subtitle track S2, S3… (S1 stays intact; the track burned in at "
      "render is chosen by right-clicking its header). Unchecked: S1 is rewritten."),
    L('"Traduire dans une nouvelle piste"', "subs.rangee.nouvelle_piste_aria", "Traduire dans une nouvelle piste",
      "Translate into a new track"),
    L('"nouvelle piste"', "subs.rangee.nouvelle_piste", "nouvelle piste", "new track"),
    L('"traduire les répliques"', "subs.traduction.but", "traduire les répliques", "translate the lines"),
    L('"aucune réplique"', "subs.traduction.aucune_replique", "aucune réplique", "no lines"),
    L('"coût indisponible"', "subs.commun.cout_indisponible", "coût indisponible", "cost unavailable", n=2),
    S('''"Les "+dzTrN+" répliques traduites naissent dans une nouvelle piste S2, S3… — S1 reste intacte ; « Annuler » retire la piste et ses répliques."''',
      'dzT("subs.traduction.nouvelle_piste_apres",{n:dzTrN})',
      {"subs.traduction.nouvelle_piste_apres": ("Les {n} répliques traduites naissent dans une nouvelle piste S2, S3… "
                                                "— S1 reste intacte ; « Annuler » retire la piste et ses répliques.",
                                                "The {n} translated lines go into a new track S2, S3… — S1 stays "
                                                "intact; “Undo” removes the track and its lines.")}),
    S('''"Le texte de la narration est déjà écrit : le moteur le cale sur "+
             "les silences réels du son. Rien n'est envoyé, rien n'est deviné, "+
             "aucun nom propre n'est écorché."''',
      'dzT("subs.rangee.gratuit_aide")',
      {"subs.rangee.gratuit_aide": ("Le texte de la narration est déjà écrit : le moteur le cale sur les silences "
                                    "réels du son. Rien n'est envoyé, rien n'est deviné, aucun nom propre n'est "
                                    "écorché.",
                                    "The narration text is already written: the engine aligns it on the actual "
                                    "silences of the audio. Nothing is sent, nothing is guessed, no proper name is "
                                    "mangled.")}),
    S('''"Écrire, découper, caler, styler, le karaoké et l'export "+
             ".SRT/.VTT/.TXT ne coûtent rien et marchent hors ligne : seule la "+
             "transcription d'un son sans texte est payante."''',
      'dzT("subs.rangee.payant_aide")',
      {"subs.rangee.payant_aide": ("Écrire, découper, caler, styler, le karaoké et l'export .SRT/.VTT/.TXT ne coûtent "
                                   "rien et marchent hors ligne : seule la transcription d'un son sans texte est "
                                   "payante.",
                                   "Writing, splitting, aligning, styling, karaoke and .SRT/.VTT/.TXT export cost "
                                   "nothing and work offline: only transcribing audio without text is paid.")}),
    L('"gratuit : texte déjà écrit, calé sur les silences"', "subs.rangee.gratuit",
      "gratuit : texte déjà écrit, calé sur les silences", "free: text already written, aligned on silences"),
    L('"écrire à la main reste gratuit"', "subs.rangee.main_gratuit", "écrire à la main reste gratuit",
      "typing by hand stays free"),

    # ── la langue confrontée au texte ──
    S('''"Aucun texte à analyser : « "+subsLangLab(lang)+" » est le réglage, "+
         "pas une lecture."''',
      'dzT("subs.langue.vide",{langue:subsLangLab(lang)})',
      {"subs.langue.vide": ("Aucun texte à analyser : « {langue} » est le réglage, pas une lecture.",
                            "No text to analyze: “{langue}” is the setting, not a reading.")}),
    S('''"Langue indécise sur "+det.ou+" — "+det.raison+". Rien n'a été choisi "+
         "à votre place : le panneau reste sur « "+subsLangLab(lang)+" »."''',
      'dzT("subs.langue.flou",{ou:det.ou,raison:det.raison,langue:subsLangLab(lang)})',
      {"subs.langue.flou": ("Langue indécise sur {ou} — {raison}. Rien n'a été choisi à votre place : le panneau reste "
                            "sur « {langue} ».",
                            "Language undecided on {ou} — {raison}. Nothing was chosen for you: the panel stays on "
                            "“{langue}”.")}),
    S('''"Langue lue sur "+det.ou+" : "+subsLangLab(det.code)+", "+
         det.hits+" mots reconnus sur "+det.total+"."''',
      'dzT("subs.langue.ok",{ou:det.ou,langue:subsLangLab(det.code),hits:det.hits,total:det.total})',
      {"subs.langue.ok": ("Langue lue sur {ou} : {langue}, {hits} mots reconnus sur {total}.",
                          "Language read from {ou}: {langue}, {hits} words recognized out of {total}.")}),
    S('''"Le texte de la piste est en "+subsLangLab(det.code).toUpperCase()+
         " ("+det.hits+" mots reconnus sur "+det.total+", contre "+
         det.secondHits+" en "+subsLangLab(det.second)+"), et ce panneau "+
         "annonce « "+subsLangLab(lang)+" » à chaque bouton qui dépense."''',
      'dzT("subs.langue.contre",{langue:subsLangLab(det.code).toUpperCase(),hits:det.hits,total:det.total,'
      'second_hits:det.secondHits,second:subsLangLab(det.second),choisie:subsLangLab(lang)})',
      {"subs.langue.contre": ("Le texte de la piste est en {langue} ({hits} mots reconnus sur {total}, contre "
                              "{second_hits} en {second}), et ce panneau annonce « {choisie} » à chaque bouton qui "
                              "dépense.",
                              "The track text is in {langue} ({hits} words recognized out of {total}, versus "
                              "{second_hits} in {second}), and this panel announces “{choisie}” on every button "
                              "that spends.")}),
    S('''(lang==="auto"?"Sous « auto » le moteur détecte lui-même la langue ; lue sur le contenu : "
            :"La langue lue sur le contenu est d'accord avec le sélecteur : ")+
           subsLangLab(det.code)+" ("+det.hits+" mots-outils reconnus sur "+
           det.total+" mots examinés). Rien à arbitrer."''',
      '(lang==="auto"'
      '?dzT("subs.langue.ok_auto_aide",{langue:subsLangLab(det.code),hits:det.hits,total:det.total})'
      ':dzT("subs.langue.ok_aide",{langue:subsLangLab(det.code),hits:det.hits,total:det.total}))',
      {"subs.langue.ok_auto_aide": ("Sous « auto » le moteur détecte lui-même la langue ; lue sur le contenu : "
                                    "{langue} ({hits} mots-outils reconnus sur {total} mots examinés). Rien à "
                                    "arbitrer.",
                                    "Under “auto” the engine detects the language itself; read from the content: "
                                    "{langue} ({hits} function words recognized out of {total} words examined). "
                                    "Nothing to settle."),
       "subs.langue.ok_aide": ("La langue lue sur le contenu est d'accord avec le sélecteur : {langue} ({hits} "
                               "mots-outils reconnus sur {total} mots examinés). Rien à arbitrer.",
                               "The language read from the content agrees with the selector: {langue} ({hits} "
                               "function words recognized out of {total} words examined). Nothing to settle.")}),
    X('"sub-btn sub-lgfix"', "classes CSS"),
    S('''"Règle le sélecteur sur « "+subsLangLab(det.code)+" » — donc "+
              "aussi la langue annoncée au moteur, le découpage en mots et le "+
              "calage sur les silences. N'écrit RIEN dans la piste : aucune "+
              "réplique n'est traduite ni retouchée."''',
      'dzT("subs.langue.passer_aide",{langue:subsLangLab(det.code)})',
      {"subs.langue.passer_aide": ("Règle le sélecteur sur « {langue} » — donc aussi la langue annoncée au moteur, le "
                                   "découpage en mots et le calage sur les silences. N'écrit RIEN dans la piste : "
                                   "aucune réplique n'est traduite ni retouchée.",
                                   "Sets the selector to “{langue}” — and so also the language announced to the "
                                   "engine, the word splitting and the alignment on silences. Writes NOTHING to the "
                                   "track: no line is translated or edited.")}),
    S('''"Langue réglée sur "+subsLangLab(det.code)+
                " — aucune réplique n'a été touchée."''',
      'dzT("subs.langue.reglee",{langue:subsLangLab(det.code)})',
      {"subs.langue.reglee": ("Langue réglée sur {langue} — aucune réplique n'a été touchée.",
                              "Language set to {langue} — no line was touched.")}),
    S('children:"passer en "+subsLangLab(det.code)',
      'children:dzT("subs.langue.passer",{langue:subsLangLab(det.code)})',
      {"subs.langue.passer": ("passer en {langue}", "switch to {langue}")}),
]
