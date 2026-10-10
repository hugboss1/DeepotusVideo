"""t145 — subs_b : tables de style du calque sous-titres (polices de repli, animations, modes karaoké, ancrages,
préréglages et leurs libellés « par effet », fiche technique d'un préréglage), réglages neutralisés et gestes
opposés (traits), santé du service, métriques de polices, langues de transcription (SUBS_LANGS), détection de la
langue par mots-outils, estimation du coût (pastilles et infobulles), bandeau de panne, libellés de placement
(SUBS_VLAB / SUBS_HLAB) et témoin « Sous-titre » de l'aperçu.

Gardés : les identifiants internes (codes de langue envoyés au serveur, "auto" comparé, clés none/fade/pop,
fill/box, left/center/right, top/middle/bottom, ids des préréglages stockés dans le style) ; les noms de polices
(noms propres, passés au moteur) ; les libellés qui se lisent pareil en anglais (« pop », « Pop Art », « Prime »,
« Machine », « opaque », « Courier New · mono ») ; les listes de mots-outils de la détection de langue (données
comparées au texte, pas affichées) ; unités ($, s, min)."""
from outils import L, S, X

CIBLE = "subs"
PLAGE = (1179, 1841)

ENTREES = [
    # ── polices de repli : [famille, libellé] ──
    L('"Inter · interface"', "subs.police.inter", "Inter · interface", "Inter · UI"),
    L('"Impact · massif"', "subs.police.impact", "Impact · massif", "Impact · heavy"),
    L('"Bahnschrift · condensé"', "subs.police.bahnschrift", "Bahnschrift · condensé", "Bahnschrift · condensed"),
    L('"Georgia · sérif"', "subs.police.georgia", "Georgia · sérif", "Georgia · serif"),
    X('"Courier New · mono"', "libellé de police qui se lit pareil en anglais"),

    # ── animations, modes karaoké ──
    L('"aucune"', "subs.anim.aucune", "aucune", "none"),
    L('"fondu"', "subs.anim.fondu", "fondu", "fade"),
    X('"pop"', "clé d'animation stockée dans le style (et libellé identique en anglais)", n=5),
    L('"remplissage"', "subs.karaoke_mode.remplissage", "remplissage", "fill"),
    L('"boîte"', "subs.karaoke_mode.boite", "boîte", "box"),

    # ── ancrages (SUBS_ALIGN / SUBS_VALIGN puis SUBS_VLAB / SUBS_HLAB) ──
    L('"gauche"', "subs.align.gauche", "gauche", "left", n=2),
    L('"centré"', "subs.align.centre", "centré", "centered", n=2),
    L('"droite"', "subs.align.droite", "droite", "right", n=2),
    L('"haut"', "subs.align.haut", "haut", "top", n=2),
    L('"milieu"', "subs.align.milieu", "milieu", "middle", n=2),
    L('"bas"', "subs.align.bas", "bas", "bottom", n=2),

    # ── préréglages : libellés d'origine (l'id est gardé) ──
    L('"Défaut"', "subs.preset.defaut", "Défaut", "Default"),
    X('"Pop Art"', "nom de préréglage identique en anglais"),
    L('"Surligneur"', "subs.preset.surligneur", "Surligneur", "Highlighter"),
    L('"Beurre"', "subs.preset.beurre", "Beurre", "Butter"),
    L('"Contour sombre"', "subs.preset.contour", "Contour sombre", "Dark outline"),
    X('"Prime"', "nom de préréglage identique en anglais"),
    L('"Abysse"', "subs.preset.abysse", "Abysse", "Abyss"),
    X('"Machine"', "nom de préréglage identique en anglais"),
    L('"Nu"', "subs.preset.nu", "Nu", "Bare"),

    # ── préréglages : libellé par effet (SUBS_PLABEL) ──
    L('"Blanc, contour fin"', "subs.preset_effet.blanc_fin", "Blanc, contour fin", "White, thin outline", n=2),
    L('"Capitales jaunes"', "subs.preset_effet.capitales_jaunes", "Capitales jaunes", "Yellow caps"),
    L('"Capitales, gros contour"', "subs.preset_effet.capitales_gros", "Capitales, gros contour", "Caps, heavy outline"),
    L('"Fond plein surligneur"', "subs.preset_effet.surligneur", "Fond plein surligneur", "Solid highlighter background"),
    L('"Capitales crème, contour brun"', "subs.preset_effet.beurre", "Capitales crème, contour brun",
      "Cream caps, brown outline"),
    L('"Blanc, contour épais"', "subs.preset_effet.blanc_epais", "Blanc, contour épais", "White, thick outline", n=2),
    L('"Bandeau noir léger"', "subs.preset_effet.prime", "Bandeau noir léger", "Light black band"),
    L('"Cyan lumineux"', "subs.preset_effet.neon", "Cyan lumineux", "Bright cyan"),
    L('"Feutre manuscrit"', "subs.preset_effet.marqueur", "Feutre manuscrit", "Handwritten marker"),
    L('"Bandeau noir dense"', "subs.preset_effet.sobre", "Bandeau noir dense", "Dense black band"),
    L('"Bandeau bleu nuit"', "subs.preset_effet.abysse", "Bandeau bleu nuit", "Midnight blue band"),
    L('"Mono vert sur noir"', "subs.preset_effet.machine", "Mono vert sur noir", "Green mono on black"),
    L('"Blanc sans décor"', "subs.preset_effet.nu", "Blanc sans décor", "Plain white"),
    L('"préréglage"', "subs.preset.repli", "préréglage", "preset"),

    # ── fiche technique d'un préréglage ──
    L('"capitales"', "subs.spec.capitales", "capitales", "caps"),
    S('a.push("fond "+Math.round(subsClamp(subsN(ps.bgOpacity,100),0,100))+" %");',
      'a.push(dzT("subs.spec.fond",{pct:Math.round(subsClamp(subsN(ps.bgOpacity,100),0,100))}));',
      {"subs.spec.fond": ("fond {pct} %", "background {pct}%")}),
    S('a.push("contour "+(rel<.06?"fin":rel<.1?"moyen":"épais"))}',
      'a.push(dzT("subs.spec.contour",{epaisseur:rel<.06?dzT("subs.spec.fin"):rel<.1?dzT("subs.spec.moyen"):dzT("subs.spec.epais")}))}',
      {"subs.spec.contour": ("contour {epaisseur}", "{epaisseur} outline"),
       "subs.spec.fin": ("fin", "thin", "contexte"), "subs.spec.moyen": ("moyen", "medium"),
       "subs.spec.epais": ("épais", "thick")}),
    L('"sans fond ni contour"', "subs.spec.sans_fond_contour", "sans fond ni contour", "no background or outline"),

    # ── réglages neutralisés ──
    L('"sans effet"', "subs.neutre.sans_effet", "sans effet", "no effect"),
    L('"le fond consomme le contour"', "subs.neutre.contour_court", "le fond consomme le contour",
      "the background swallows the outline"),
    S('why:"Mesuré à la gravure : sous un fond, le contour ne sort pas. À 0, 3 "+\n'
      '        "ou 8 px la vidéo est le même fichier au pixel près — libass se sert "+\n'
      '        "de l\'épaisseur de contour comme rembourrage de la boîte, et c\'est la "+\n'
      '        "marge intérieure du fond qui la règle.",',
      'why:dzT("subs.neutre.contour_pourquoi"),',
      {"subs.neutre.contour_pourquoi": (
          "Mesuré à la gravure : sous un fond, le contour ne sort pas. À 0, 3 ou 8 px la vidéo est le même fichier "
          "au pixel près — libass se sert de l'épaisseur de contour comme rembourrage de la boîte, et c'est la marge "
          "intérieure du fond qui la règle.",
          "Measured on the burned video: under a background, the outline doesn't show. At 0, 3 or 8 px the video is "
          "the same file down to the pixel — libass uses the outline thickness as box padding, and it's the "
          "background's inner margin that sets it.")}),
    S('label:"Couper le fond"', 'label:dzT("subs.neutre.couper_fond")',
      {"subs.neutre.couper_fond": ("Couper le fond", "Remove background")}),
    L('"rendre le contour visible"', "subs.neutre.couper_fond_but", "rendre le contour visible",
      "make the outline visible"),
    S('effect:"Le fond disparaît et le contour de "+\n          subsFr(subsN(s.outW,3),1)+" px se met à agir."}});',
      'effect:dzT("subs.neutre.couper_fond_effet",{px:subsFr(subsN(s.outW,3),1)})}});',
      {"subs.neutre.couper_fond_effet": ("Le fond disparaît et le contour de {px} px se met à agir.",
                                         "The background disappears and the {px} px outline takes effect.")}),

    # ── gestes opposés, traits ──
    S('ou:"réglage éteint : "+\n        (SUBS_CHAMP[n.champ]||n.champ)})});',
      'ou:dzT("subs.geste.reglage_eteint",{champ:SUBS_CHAMP[n.champ]||n.champ})})});',
      {"subs.geste.reglage_eteint": ("réglage éteint : {champ}", "setting off: {champ}")}),
    L('"le fond"', "subs.trait.fond", "le fond", "the background"),
    L('"le contour"', "subs.trait.contour", "le contour", "the outline"),
    L('"le karaoké"', "subs.trait.karaoke", "le karaoké", "the karaoke"),
    X('"opaque"', "valeur de trait affichée, identique en anglais"),
    L('"translucide"', "subs.trait.translucide", "translucide", "translucent"),
    L('"aucun"', "subs.trait.aucun", "aucun", "none", n=2),
    L('"actif"', "subs.trait.actif", "actif", "active"),
    L('"éteint"', "subs.trait.eteint", "éteint", "off"),

    # ── langues de transcription : codes gardés, libellés traduits ──
    X('"auto"', "code de langue envoyé au serveur et comparé (lang===\"auto\")", n=2),
    L('"détection par le moteur"', "subs.langue.auto", "détection par le moteur", "engine detection"),
    L('"français"', "subs.langue.fr", "français", "French"),
    L('"anglais"', "subs.langue.en", "anglais", "English"),
    L('"espagnol"', "subs.langue.es", "espagnol", "Spanish"),
    L('"allemand"', "subs.langue.de", "allemand", "German"),
    L('"italien"', "subs.langue.it", "italien", "Italian"),
    L('"portugais"', "subs.langue.pt", "portugais", "Portuguese"),
    L('"néerlandais"', "subs.langue.nl", "néerlandais", "Dutch"),
    L('"polonais"', "subs.langue.pl", "polonais", "Polish"),
    L('"russe"', "subs.langue.ru", "russe", "Russian"),
    L('"ukrainien"', "subs.langue.uk", "ukrainien", "Ukrainian"),
    L('"turc"', "subs.langue.tr", "turc", "Turkish"),
    L('"arabe"', "subs.langue.ar", "arabe", "Arabic"),
    L('"japonais"', "subs.langue.ja", "japonais", "Japanese"),
    L('"chinois"', "subs.langue.zh", "chinois", "Chinese"),
    L('"coréen"', "subs.langue.ko", "coréen", "Korean"),
    L('"hindi"', "subs.langue.hi", "hindi", "Hindi"),

    # ── détection de la langue ──
    X('"le la les de des du un une et est en que qui dans pour pas sur au aux "', "mots-outils comparés au texte"),
    X('"ce cette ces avec plus je tu il elle nous vous ils elles mais ou donc "', "mots-outils comparés au texte"),
    X('"son sa ses mon ma mes tout tous fait être avoir cest ny na quil"', "mots-outils comparés au texte"),
    X('"the of and to a in is it you that he was for on are with as his they i "', "mots-outils comparés au texte"),
    X('"be this have from or one had by but not what all were we when your can "', "mots-outils comparés au texte"),
    X('"there my been if would about who its did get like just dont im thats"', "mots-outils comparés au texte"),
    X('"el la los las de del un una y es en que no se por con para su al lo "', "mots-outils comparés au texte"),
    X('"como más pero sus le ya o este sí porque esta entre cuando muy sin "', "mots-outils comparés au texte"),
    X('"sobre también me hasta hay donde han quien"', "mots-outils comparés au texte"),
    X('"der die das den dem des ein eine und ist in zu von mit auf für nicht "', "mots-outils comparés au texte"),
    X('"auch es sich als an werden aus er hat dass sie nach bei um noch wie "', "mots-outils comparés au texte"),
    X('"über nur oder aber vor zum zur ich wir"', "mots-outils comparés au texte"),
    X('"il lo la i gli le di del della un una e è in che non per con su come "', "mots-outils comparés au texte"),
    X('"da si sono ma anche più ci se al alla nel questo questa loro suo mi ti "', "mots-outils comparés au texte"),
    X('"ho hanno essere fare quando perché"', "mots-outils comparés au texte"),
    X('"o a os as de do da dos das um uma e é em que não para com por se mais "', "mots-outils comparés au texte"),
    X('"como mas ao à no na você eu ele ela nós eles isso este esta seu sua "', "mots-outils comparés au texte"),
    X('"quando porque muito já também até"', "mots-outils comparés au texte"),
    L('"aucun texte"', "subs.detect.aucun_texte", "aucun texte", "no text"),
    S('?"trop peu de mots reconnus ("+score[p]+", il en faut "+SUBS_LG_MIN+")"',
      '?dzT("subs.detect.trop_peu",{n:score[p],min:SUBS_LG_MIN})',
      {"subs.detect.trop_peu": ("trop peu de mots reconnus ({n}, il en faut {min})",
                                "too few recognized words ({n}, {min} needed)")}),
    S(':"« "+subsLangLab(p)+" » et « "+subsLangLab(s)+" » à égalité ("+\n     score[p]+" contre "+score[s]+")";',
      ':dzT("subs.detect.egalite",{a:subsLangLab(p),b:subsLangLab(s),na:score[p],nb:score[s]});',
      {"subs.detect.egalite": ("« {a} » et « {b} » à égalité ({na} contre {nb})",
                               "“{a}” and “{b}” tied ({na} vs {nb})")}),
    L('"les répliques de la piste"', "subs.detect.source_repliques", "les répliques de la piste", "the track's lines"),
    L('"la narration écrite sur les clips de voix"', "subs.detect.source_narration",
      "la narration écrite sur les clips de voix", "the narration written on the voice clips"),

    # ── estimation du coût ──
    L('"moteur de transcription"', "subs.cout.moteur_transcription", "moteur de transcription", "transcription engine"),
    S('"Aucune clé de transcription configurée (Réglages : ElevenLabs ou "+\n          "OpenAI). Le calage d\'un texte de narration reste gratuit.")}',
      'dzT("subs.cout.aucune_cle"))}',
      {"subs.cout.aucune_cle": (
          "Aucune clé de transcription configurée (Réglages : ElevenLabs ou OpenAI). Le calage d'un texte de "
          "narration reste gratuit.",
          "No transcription key configured (Settings: ElevenLabs or OpenAI). Aligning a narration text stays free.")}),
    S('SUBS_EST.reason="Le moteur ne répond pas : le coût ne peut pas être "+\n      "annoncé, donc rien n\'est lancé.";',
      'SUBS_EST.reason=dzT("subs.cout.moteur_muet");',
      {"subs.cout.moteur_muet": ("Le moteur ne répond pas : le coût ne peut pas être annoncé, donc rien n'est lancé.",
                                 "The engine isn't responding: the cost can't be announced, so nothing is started.")}),
    L('"moteur"', "subs.cout.moteur", "moteur", "engine"),
    S('if(free)return {txt:subsLangLab(lang)+" · calage local · gratuit",free:!0,\n'
      '    apres:"Le texte de narration est déjà écrit : le moteur le CALE sur les "+\n'
      '      "silences réels du son (langue "+subsLangLab(lang)+"). Aucun appel "+\n'
      '      "payant, aucun nom propre écorché, et ça marche hors ligne."};',
      'if(free)return {txt:dzT("subs.cout.gratuit_pastille",{langue:subsLangLab(lang)}),free:!0,\n'
      '    apres:dzT("subs.cout.gratuit_apres",{langue:subsLangLab(lang)})};',
      {"subs.cout.gratuit_pastille": ("{langue} · calage local · gratuit", "{langue} · local alignment · free"),
       "subs.cout.gratuit_apres": (
           "Le texte de narration est déjà écrit : le moteur le CALE sur les silences réels du son (langue "
           "{langue}). Aucun appel payant, aucun nom propre écorché, et ça marche hors ligne.",
           "The narration text is already written: the engine ALIGNS it to the real silences of the audio "
           "(language {langue}). No paid call, no mangled proper names, and it works offline.")}),
    S('if(!SUBS_EST.ok)return {txt:subsLangLab(lang)+" · coût indisponible",',
      'if(!SUBS_EST.ok)return {txt:dzT("subs.cout.indisponible_pastille",{langue:subsLangLab(lang)}),',
      {"subs.cout.indisponible_pastille": ("{langue} · coût indisponible", "{langue} · cost unavailable")}),
    S('"Aucun moteur de transcription configuré : le coût ne peut pas être "+\n      "annoncé, donc le geste n\'est pas offert."};',
      'dzT("subs.cout.aucun_moteur")};',
      {"subs.cout.aucun_moteur": (
          "Aucun moteur de transcription configuré : le coût ne peut pas être annoncé, donc le geste n'est pas offert.",
          "No transcription engine configured: the cost can't be announced, so the action isn't offered.")}),
    L('"langue auto"', "subs.cout.langue_auto", "langue auto", "auto language"),
    S('apres:"Appel PAYANT à "+SUBS_EST.label+\n'
      '      (SUBS_EST.model?" ("+SUBS_EST.model+")":"")+", langue "+\n'
      '      /* P13 — sous « auto » : « détectée par le moteur ». */\n'
      '      (lang==="auto"?"détectée par le moteur":subsLangLab(lang))+" : "+subsUsd(usd)+" pour "+subsFr(d,1)+" s de son ("+\n'
      '      subsUsd(SUBS_EST.usdMin)+" la minute annoncés par le moteur × "+\n'
      '      subsFr(d,1)+" ÷ 60), "+subsEta(eta)+" d\'attente ("+\n'
      '      subsFr(SUBS_EST.over,1)+" s de mise en route + "+\n'
      '      subsFr(SUBS_EST.rt,2)+" s par seconde de son)."}}',
      'apres:dzT("subs.cout.payant_apres",{moteur:SUBS_EST.label,modele:SUBS_EST.model?" ("+SUBS_EST.model+")":"",\n'
      '      /* P13 — sous « auto » : « détectée par le moteur ». */\n'
      '      langue:lang==="auto"?dzT("subs.cout.detectee_moteur"):subsLangLab(lang),prix:subsUsd(usd),duree:subsFr(d,1),\n'
      '      tarif:subsUsd(SUBS_EST.usdMin),attente:subsEta(eta),mise:subsFr(SUBS_EST.over,1),rt:subsFr(SUBS_EST.rt,2)})}}',
      {"subs.cout.payant_apres": (
          "Appel PAYANT à {moteur}{modele}, langue {langue} : {prix} pour {duree} s de son ({tarif} la minute "
          "annoncés par le moteur × {duree} ÷ 60), {attente} d'attente ({mise} s de mise en route + {rt} s par "
          "seconde de son).",
          "PAID call to {moteur}{modele}, language {langue}: {prix} for {duree} s of audio ({tarif} per minute "
          "announced by the engine × {duree} ÷ 60), {attente} wait ({mise} s startup + {rt} s per second of audio)."),
       "subs.cout.detectee_moteur": ("détectée par le moteur", "detected by the engine")}),

    # ── bandeau de panne ──
    L('"Service de sous-titres injoignable — le backend ne répond pas."', "subs.alerte.titre",
      "Service de sous-titres injoignable — le backend ne répond pas.",
      "Subtitle service unreachable — the backend isn't responding."),
    S('title:"/api/subtitles/presets et /api/subtitles/transcribe sont muets "+\n'
      '          "sur 127.0.0.1:8765. Relancez DeepotusVideoGen : le panneau se "+\n'
      '          "remplira seul, sans être rouvert.",',
      'title:dzT("subs.alerte.detail"),',
      {"subs.alerte.detail": (
          "/api/subtitles/presets et /api/subtitles/transcribe sont muets sur 127.0.0.1:8765. Relancez "
          "DeepotusVideoGen : le panneau se remplira seul, sans être rouvert.",
          "/api/subtitles/presets and /api/subtitles/transcribe are silent on 127.0.0.1:8765. Restart "
          "DeepotusVideoGen: the panel will fill itself, without being reopened.")}),
    S('children:"Seule la transcription automatique en dépend. Écrire, "+\n'
      '          "découper, caler, styler, le karaoké et l\'export .SRT / .VTT / .TXT "+\n'
      '          "marchent hors ligne ; préréglages et polices = liste locale."}),',
      'children:dzT("subs.alerte.ampute")}),',
      {"subs.alerte.ampute": (
          "Seule la transcription automatique en dépend. Écrire, découper, caler, styler, le karaoké et l'export "
          ".SRT / .VTT / .TXT marchent hors ligne ; préréglages et polices = liste locale.",
          "Only automatic transcription depends on it. Writing, splitting, aligning, styling, karaoke and "
          ".SRT / .VTT / .TXT export work offline; presets and fonts = local list.")}),
    L('"Nouvelle tentative en cours…"', "vfx.alerte.tentative", "Nouvelle tentative en cours…", "Retrying now…"),
    S('"Reprise automatique — nouvelle tentative dans "+left+" s."',
      'dzT("subs.alerte.reprise",{s:left})',
      {"subs.alerte.reprise": ("Reprise automatique — nouvelle tentative dans {s} s.",
                               "Automatic recovery — retrying in {s} s.")}),
    L('"Redemander /api/subtitles/presets immédiatement"', "subs.alerte.reessayer_aide",
      "Redemander /api/subtitles/presets immédiatement", "Request /api/subtitles/presets again now"),
    L('"Réessayer"', "commun.action.reessayer", "Réessayer", "Retry"),

    # ── aperçu ──
    L('"Sous-titre"', "subs.overlay.temoin", "Sous-titre", "Subtitle", contexte=True),
    # ── gardés : noms de polices (noms propres passés au moteur), CSS, classes ──
    X('"Inter"', "nom de police", n=8),
    X('"Segoe UI"', "nom de police", n=2),
    X('"Arial"', "nom de police", n=2),
    X('"Impact"', "nom de police", n=2),
    X('"Bahnschrift"', "nom de police", n=2),
    X('"Franklin Gothic Medium"', "nom de police"),
    X('"Franklin Gothic"', "nom de police (libellé = nom propre)"),
    X('"Georgia"', "nom de police", n=2),
    X('"Trebuchet MS"', "nom de police", n=2),
    X('"Verdana"', "nom de police", n=2),
    X('"Tahoma"', "nom de police", n=2),
    X('"Courier New"', "nom de police", n=2),
    X('"Comic Sans MS"', "nom de police", n=2),
    X('"bebas neue"', "clé de table des hauteurs de ligne (famille en minuscules)"),
    X('"press start 2p"', "clé de table des hauteurs de ligne (famille en minuscules)"),
    X('"ibm plex sans"', "clé de table des hauteurs de ligne (famille en minuscules)"),
    X('"\') format(\'truetype\');font-display:swap}\\n"', "CSS @font-face"),
    X('"sub-btn sub-alertbtn"', "classes CSS"),
]
