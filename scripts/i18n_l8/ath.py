"""t148 — ath : les deux pages HTML de l'Atelier (atelier/index.html, atelier/preview.html), jamais modifiées : chaque
texte affiché (nœud texte, title, placeholder, aria-label, <option>) reçoit son H, traduit à l'affichage par la surcouche.
GARDÉ (X) : les données factices de preview.html (texte de manuscrit, scénario, noms d'entités, prompts de plan : contenu
d'utilisateur simulé) et deux textes bruts à entités HTML (« &#10; », « &amp; ») dont la version DÉCODÉE a son H.
Le script inline de preview.html ne pose aucun texte (bascule d'onglets et de thème seulement)."""
from outils import H, X

IDX = "atelier/index.html"
PRV = "atelier/preview.html"

ENTREES = [
    # ── index.html : en-tête ──
    H("atelier.ath_page.titre", "Deepotus — Atelier Chapitre", "Deepotus — Chapter Workshop"),
    H("atelier.ath_page.marque", "Atelier Chapitre", "Chapter Workshop"),
    H("atelier.ath_chap.liste", "Chapitres", "Chapters"),
    H("atelier.ath_chap.nouveau", "Chapitre", "Chapter"),
    H("atelier.ath_chap.manuscrit_aide",
      "Importer un manuscrit complet : l'agent IA segmente les chapitres, remplit la bible (personnages, lieux, objets, "
      "dates, ambiances, décors) et surligne le texte",
      "Import a full manuscript: the AI agent splits it into chapters, fills the bible (characters, places, objects, "
      "dates, ambiences, sets) and highlights the text"),
    H("atelier.ath_chap.manuscrit", "Manuscrit", "Manuscript"),
    H("atelier.ath_chap.titre_ph", "Titre du chapitre", "Chapter title"),
    H("atelier.ath_chap.titre", "Titre", "Title"),
    H("atelier.ath_chap.serie_ph", "Série (ex: Lost Abyss)", "Series (e.g. Lost Abyss)"),
    H("atelier.ath_chap.serie", "Série", "Series"),
    H("atelier.ath_chap.supprimer", "Supprimer ce chapitre", "Delete this chapter"),
    H("atelier.ath_chap.versions_aide",
      "Versions : chaque écrasement (édition, adaptation, ré-import, retour du téléphone…) a laissé un instantané — "
      "comparer et revenir en arrière",
      "Versions: every overwrite (edit, adaptation, re-import, return from the phone…) left a snapshot — "
      "compare and roll back"),
    H("atelier.ath_page.retour", "Retour à l'app", "Back to the app"),
    # ── volet script ──
    H("atelier.ath_mode.scenario", "Scénario", "Screenplay"),
    H("atelier.ath_mode.duree_board", "Durée totale du storyboard", "Total storyboard duration"),
    H("atelier.ath_script.importer", "Importer (txt/docx/pdf)", "Import (txt/docx/pdf)"),
    H("atelier.ath_script.exp_docx",
      "Exporter le manuscrit du chapitre en .docx (Word, A4) — tout caractère gardé",
      "Export the chapter manuscript as .docx (Word, A4) — every character kept"),
    H("atelier.ath_script.exp_pdf",
      "Exporter le manuscrit du chapitre en PDF (A4, pages numérotées)",
      "Export the chapter manuscript as PDF (A4, numbered pages)"),
    H("atelier.ath_sel.selection", "Sélection :", "Selection:"),
    H("atelier.ath_kind.personnage", "Personnage", "Character"),
    H("atelier.ath_kind.lieu", "Lieu", "Place"),
    H("atelier.ath_kind.objet", "Objet", "Object"),
    H("atelier.ath_kind.ambiance", "Ambiance", "Ambience"),
    H("atelier.ath_kind.decor", "Décor", "Set", contexte=True),
    H("atelier.ath_sel.lier_aide", "Lier la sélection à une entité existante", "Link the selection to an existing entity"),
    H("atelier.ath_sel.lier", "Lier à…", "Link to…"),                                   # <option>
    H("atelier.ath_sel.reecrire_aide",
      "Une passe du modèle sur la sélection, dans le ton de la bible (personnages, voix castées, style) — le coût est "
      "dit et confirmé avant, et rien n'est écrit sans votre accord",
      "One model pass over the selection, in the tone of the bible (characters, cast voices, style) — the cost is "
      "shown and confirmed first, and nothing is written without your approval"),
    H("atelier.ath_sel.reecrire", "Réécrire…", "Rewrite…"),                             # <option>
    H("atelier.ath_sel.reformuler", "Reformuler", "Rephrase"),                          # <option>
    H("atelier.ath_sel.resserrer", "Resserrer", "Tighten"),                             # <option>
    H("atelier.ath_sel.traduire", "Traduire…", "Translate…"),                           # <option>
    H("atelier.ath_sel.scene", "Proposer une scène", "Suggest a scene"),                # <option>
    H("atelier.ath_sel.dialogue", "Proposer un dialogue", "Suggest a dialogue"),        # <option>
    H("atelier.ath_script.placeholder",
      "Colle ton chapitre ici, ou importe un fichier. Puis sélectionne un mot ou une phrase (un personnage, un lieu, un "
      "objet) et crée l'entité — elle rejoindra la bible à droite et restera disponible pour tous les chapitres suivants.",
      "Paste your chapter here, or import a file. Then select a word or a sentence (a character, a place, an object) "
      "and create the entity — it will join the bible on the right and stay available for all the following chapters."),
    X(IDX, 68, "Colle ton chapitre ici, ou importe un fichier.&#10;&#10;Puis",
      "texte brut à entités &#10; : sa version décodée (espaces normalisés) a son H atelier.ath_script.placeholder"),
    H("atelier.ath_legende.orpheline", "zone orpheline — re-lier", "orphan zone — re-link"),
    # ── mode Scénario ──
    H("atelier.ath_sp.adapter_aide",
      "L'agent adapte le chapitre en scénario (règles de l'art : show don't tell, sluglines, éclairages et caméra "
      "motivés par le narratif) — le manuscrit original n'est PAS modifié",
      "The agent adapts the chapter into a screenplay (by the book: show don't tell, sluglines, lighting and camera "
      "driven by the story) — the original manuscript is NOT changed"),
    H("atelier.ath_sp.adapter", "Adapter (IA)", "Adapt (AI)"),
    H("atelier.ath_sp.lire_aide", "Lire le scénario assemblé du chapitre, ici même",
      "Read the chapter's assembled screenplay, right here"),
    H("atelier.ath_sp.lire", "Lire", "Read"),
    H("atelier.ath_sp.vo_aide",
      "Génère le voice-over de toutes les scènes (narration = Narrateur, répliques = voix castées) — chaque scène "
      "reçoit sa durée réelle",
      "Generates the voice-over for every scene (narration = Narrator, lines = cast voices) — each scene gets its "
      "real duration"),
    H("atelier.ath_sp.vo_total", "Durée totale du voice-over du chapitre", "Total voice-over duration of the chapter"),
    H("atelier.ath_sp.fountain_aide",
      "Export .fountain = simple fichier TEXTE (standard industrie). S'ouvre avec le Bloc-notes ou un logiciel de "
      "scénario (Fade In, Highland, Arc Studio). L'Atelier n'en a PAS besoin : le storyboard lit les scènes directement.",
      "Export .fountain = plain TEXT file (industry standard). Opens in Notepad or in screenwriting software "
      "(Fade In, Highland, Arc Studio). The Workshop does NOT need it: the storyboard reads the scenes directly."),
    H("atelier.ath_sp.importer_aide",
      "Importer un scénario Fountain (.fountain, .txt) ou Final Draft (.fdx) dans ce chapitre : remplacer les scènes "
      "(sauvegardées avant) ou les ajouter à la suite — sans IA, gratuit",
      "Import a Fountain (.fountain, .txt) or Final Draft (.fdx) screenplay into this chapter: replace the scenes "
      "(saved first) or append them — no AI, free"),
    H("atelier.ath_sp.importer", "Importer .fountain / .fdx", "Import .fountain / .fdx"),
    H("atelier.ath_sp.exp_docx", "Exporter le scénario en .docx (Courier 12, US Letter, retraits du métier)",
      "Export the screenplay as .docx (Courier 12, US Letter, industry-standard indents)"),
    H("atelier.ath_sp.exp_pdf",
      "Exporter le scénario en PDF (Courier 12, US Letter, page de titre, pages numérotées)",
      "Export the screenplay as PDF (Courier 12, US Letter, title page, numbered pages)"),
    H("atelier.ath_sp.reset_aide", "Supprimer toutes les scènes de ce chapitre (le manuscrit reste intact)",
      "Delete every scene of this chapter (the manuscript stays intact)"),
    H("atelier.ath_sp.reset", "Réinitialiser", "Reset"),
    H("atelier.ath_sp.indice", "le manuscrit reste intact — le scénario est un artefact dérivé",
      "the manuscript stays intact — the screenplay is a derived artifact"),
    # ── mode Storyboard ──
    H("atelier.ath_sb.decouper_aide",
      "L'IA lit le chapitre et la bible, puis découpe en plans (action, entités, cadrage, caméra, durée, prompt)",
      "The AI reads the chapter and the bible, then breaks it down into shots (action, entities, framing, camera, "
      "duration, prompt)"),
    H("atelier.ath_sb.decouper", "Découper (IA)", "Break down (AI)"),
    H("atelier.ath_sb.para_aide", "Un plan par paragraphe, sans IA", "One shot per paragraph, no AI"),
    H("atelier.ath_sb.para", "Paragraphes", "Paragraphs"),
    H("atelier.ath_sb.plan_aide", "Ajouter un plan vide à la fin", "Add an empty shot at the end"),
    H("atelier.ath_sb.plan", "Plan", "Shot"),
    H("atelier.ath_sb.episode_aide",
      "Créer un épisode narré (un plan = une scène : son texte, son image) dans la vue Épisodes — SANS rendu : la "
      "narration et le rendu payants s'y lancent avec leur devis",
      "Create a narrated episode (one shot = one scene: its text, its image) in the Episodes view — NO render: the "
      "paid narration and render are started there with their quote"),
    H("atelier.ath_sb.episode", "Épisode", "Episode"),
    H("atelier.ath_sb.pdf_aide",
      "Exporter le storyboard en PDF : quatre plans par page A4, vignette 9:16 entière (production, sinon croquis)",
      "Export the storyboard as PDF: four shots per A4 page, full 9:16 thumbnail (production, otherwise sketch)"),
    H("atelier.ath_sb.anim_aide",
      "Animatique : les plans montés en vidéo de répétition (image fixe à sa durée), muette et gratuite par défaut — "
      "à regarder avant de payer un rendu",
      "Animatic: the shots cut into a rehearsal video (each still held for its duration), silent and free by default "
      "— watch it before paying for a render"),
    H("atelier.ath_sb.anim", "Animatique", "Animatic"),
    H("atelier.ath_sb.reset_aide", "Supprimer tous les plans de ce storyboard pour repartir de zéro",
      "Delete every shot of this storyboard to start from scratch"),
    H("atelier.ath_sb.indice", "croquis = validation du cadrage et du rythme avant la production",
      "sketch = checking framing and pacing before production"),
    H("atelier.ath_sb.pont", "Pont video-shotcraft", "video-shotcraft bridge"),
    # ── éléments vectoriels ──
    H("atelier.ath_vec.titre", "Éléments vectoriels", "Vector elements"),
    H("atelier.ath_vec.decor_aide", "Nouveau décor vectoriel lié à ce chapitre (ouvre l'éditeur)",
      "New vector set linked to this chapter (opens the editor)"),
    H("atelier.ath_vec.lumiere_aide", "Nouveau calque de lumière (halos, dégradés) lié à ce chapitre",
      "New light layer (halos, gradients) linked to this chapter"),
    H("atelier.ath_vec.lumiere", "Lumière", "Light"),
    H("atelier.ath_vec.perso_aide", "Nouveau personnage vectoriel lié à ce chapitre",
      "New vector character linked to this chapter"),
    H("atelier.ath_vec.biblio_aide",
      "Instancier par référence un élément de la bibliothèque ou d'un autre chapitre (sans copie)",
      "Instance an element of the library or of another chapter by reference (no copy)"),
    H("atelier.ath_vec.biblio", "Bibliothèque", "Library"),
    H("atelier.ath_vec.recherche", "Rechercher par nom…", "Search by name…"),
    H("atelier.ath_vec.tous_roles", "Tous rôles", "All roles"),                           # <option>
    H("atelier.ath_vec.libre", "Libre", "Free", contexte=True),                          # <option> (« Liberal » ailleurs)
    # ── bible ──
    H("atelier.ath_bible.personnages", "Personnages", "Characters"),
    H("atelier.ath_bible.lieux", "Lieux", "Places"),
    H("atelier.ath_bible.objets", "Objets", "Objects"),
    H("atelier.ath_bible.ambiances", "Ambiances", "Ambiences"),
    H("atelier.ath_bible.decors", "Décors", "Sets", contexte=True),
    H("atelier.ath_bible.nouveau", "Nouveau", "New"),
    H("atelier.ath_bible.da_aide",
      "Direction artistique : propositions de l'agent (motivées par le manuscrit), styles présets (BD, manga, "
      "réaliste…), choix du générateur d'images et référence de style",
      "Art direction: the agent's proposals (grounded in the manuscript), preset styles (comics, manga, "
      "realistic…), choice of image generator and style reference"),
    H("atelier.ath_bible.da", "DA", "AD"),
    H("atelier.ath_bible.style_ph",
      "Style global du projet — toutes les planches l'utilisent (🎨 DA pour les propositions)",
      "Project-wide style — every sheet uses it (🎨 AD for proposals)"),
    H("atelier.ath_bible.style_aide",
      "Style de réalisation appliqué à TOUTES les générations du projet. Une entité peut le surcharger ponctuellement "
      "via ses propres notes de style.",
      "Visual style applied to ALL generations of the project. An entity can override it case by case "
      "through its own style notes."),
    # ── modale inspiration ──
    H("atelier.ath_lib.titre", "Ajouter une inspiration", "Add an inspiration"),
    H("atelier.ath_lib.fichier_aide", "Importer un fichier de ton PC (il rejoint la Library)",
      "Import a file from your PC (it joins the Library)"),
    H("atelier.ath_lib.fichier", "Fichier", "File"),
    H("atelier.ath_lib.url_aide", "Importer depuis une URL web (elle rejoint la Library)",
      "Import from a web URL (it joins the Library)"),
    H("atelier.ath_modale.fermer", "Fermer", "Close"),
    # ── modale direction artistique ──
    H("atelier.ath_da.titre", "Direction artistique du projet", "Project art direction"),
    H("atelier.ath_da.propositions", "Propositions de l'agent", "Agent proposals"),
    H("atelier.ath_da.proposer_aide",
      "L'agent relit le manuscrit (ton, époque, genre, indices visuels rédigés) et propose 4 directions motivées",
      "The agent rereads the manuscript (tone, period, genre, written visual cues) and proposes 4 grounded directions"),
    H("atelier.ath_da.proposer", "(Re)proposer", "(Re)propose"),
    H("atelier.ath_da.vide",
      "Importe un manuscrit (📚) ou clique ✨ — l'agent proposera 4 directions motivées par le texte.",
      "Import a manuscript (📚) or click ✨ — the agent will propose 4 directions grounded in the text."),
    H("atelier.ath_da.presets", "Styles présets", "Preset styles"),
    H("atelier.ath_da.applique", "Style appliqué (modifiable)", "Applied style (editable)"),
    H("atelier.ath_da.style_ph", "Le style injecté dans toutes les générations du projet…",
      "The style injected into every generation of the project…"),
    H("atelier.ath_da.canon", "Canon de proportions", "Proportion canon"),
    H("atelier.ath_da.canon_note",
      "— morphologie des personnages selon les grandes écoles (De Vinci, manga, ligne claire, gros nez, Moebius, DC…)",
      "— character build according to the great schools (Da Vinci, manga, ligne claire, big-nose, Moebius, DC…)"),
    H("atelier.ath_da.canon_aide",
      "Injecté dans chaque planche : nombre de têtes, traits du visage, perspective des décors — accordé au style "
      "général",
      "Injected into every sheet: head count, facial features, set perspective — matched to the overall style"),
    H("atelier.ath_da.generateur", "Générateur d'images", "Image generator"),
    H("atelier.ath_da.ref", "Référence de style (optionnel)", "Style reference (optional)"),
    H("atelier.ath_da.aucune", "aucune", "none"),
    H("atelier.ath_da.choisir", "Choisir", "Choose"),
    H("atelier.ath_da.retirer", "Retirer", "Remove"),
    H("atelier.ath_da.ref_note",
      "Une image (planche BD, still de film…) dont le RENDU sert de modèle aux planches — utilisée quand l'entité n'a "
      "pas sa propre référence d'identité.",
      "An image (comic page, film still…) whose RENDERING serves as the model for the sheets — used when the entity "
      "has no identity reference of its own."),
    H("atelier.ath_da.appliquer", "Appliquer au projet", "Apply to project"),
    H("atelier.ath_da.persiste",
      "persiste et s'applique à toutes les générations — chaque entité peut garder son style spécifique",
      "saved and applied to every generation — each entity can keep its own style"),
    # ── modale agent manuscrit (le paragraphe se traduit nœud texte par nœud texte) ──
    H("atelier.ath_ms.titre", "Agent Manuscrit — ingestion complète", "Manuscript agent — full ingestion"),
    H("atelier.ath_ms.p1", "L'agent lit le manuscrit entier : il", "The agent reads the whole manuscript: it"),
    H("atelier.ath_ms.p2", "segmente les chapitres", "splits the chapters"),
    H("atelier.ath_ms.p3", "(titres importés), liste dans la bible", "(imported titles), lists in the bible"),
    H("atelier.ath_ms.p4", "personnages, lieux, objets, dates, ambiances et décors",
      "characters, places, objects, dates, ambiences and sets"),
    H("atelier.ath_ms.p5", "chapitre par chapitre, fait une", "chapter by chapter, does a"),
    H("atelier.ath_ms.p6", "relecture globale", "global review"),
    H("atelier.ath_ms.p7",
      "pour consolider les descriptions (ton fichier de notes sert de référence), puis",
      "to consolidate the descriptions (your notes file is the reference), then"),
    H("atelier.ath_ms.p8", "surligne", "highlights"),
    H("atelier.ath_ms.p9", "toutes les zones correspondantes dans le texte.", "every matching zone in the text."),
    H("atelier.ath_ms.fichier", "Manuscrit (txt / docx / pdf) — requis", "Manuscript (txt / docx / pdf) — required"),
    H("atelier.ath_ms.compagnon",
      "Fichier compagnon (notes de l'auteur) — optionnel, source d'autorité",
      "Companion file (author's notes) — optional, authoritative source"),
    H("atelier.ath_ms.serie", "Nom de la série", "Series name"),
    H("atelier.ath_ms.serie_ph", "(par défaut : nom du fichier)", "(default: file name)"),
    H("atelier.ath_ms.lancer", "Lancer l'agent", "Run the agent"),
    H("atelier.ath_ms.duree",
      "plusieurs minutes selon la taille (1 lecture IA par chapitre + consolidation)",
      "several minutes depending on size (1 AI read per chapter + consolidation)"),
    # ── modale versions ──
    H("atelier.ath_ver.titre", "Versions du texte", "Text versions"),
    H("atelier.ath_ver.vide",
      "Choisis une version à gauche : le côte à côte la compare au texte courant.",
      "Pick a version on the left: the side-by-side view compares it with the current text."),
    # ── modale animatique ──
    H("atelier.ath_anim.voix_aide",
      "Une voix témoin par plan, lue par le Narrateur de la bible : elle fixe la durée du plan. Les voix déjà faites "
      "sont en cache (gratuites).",
      "One guide voice per shot, read by the bible's Narrator: it sets the shot's duration. Voices already made are "
      "cached (free)."),
    H("atelier.ath_anim.voix", "Voix témoin", "Guide voice"),
    H("atelier.ath_anim.monter_aide",
      "Monter l'animatique (muette : gratuit ; avec voix : coût affiché et confirmé avant)",
      "Build the animatic (silent: free; with voice: cost shown and confirmed first)"),
    # « Monter » est déjà « Move up » ailleurs (sens différent) : contexte, la surcouche l'ignore (voir réponse)
    H("atelier.ath_anim.monter", "Monter", "Build", contexte=True),
    H("atelier.ath_anim.sorties", "Vers le Montage (nouveau projet, gratuit) :", "To Montage (new project, free):"),
    H("atelier.ath_anim.film_aide",
      "Créer un NOUVEAU projet de Montage avec tous les plans de l'animatique et leurs voix témoins — la timeline en "
      "cours n'est pas touchée",
      "Create a NEW Montage project with all the animatic's shots and their guide voices — the current timeline is "
      "left untouched"),
    H("atelier.ath_anim.reel_aide",
      "Créer un NOUVEAU projet de Montage avec les plans les plus forts (énergie du storyboard), 30 s au plus — la "
      "timeline en cours n'est pas touchée",
      "Create a NEW Montage project with the strongest shots (storyboard energy), 30 s at most — the current "
      "timeline is left untouched"),
    H("atelier.ath_anim.vide", "Pas encore d'animatique pour ce chapitre : « 🎞 Monter ».",
      "No animatic for this chapter yet: “🎞 Build”."),
    # ── modale réécriture ──
    H("atelier.ath_ree.titre", "Proposition", "Proposal"),
    H("atelier.ath_ree.fermer", "Fermer sans rien écrire", "Close without writing anything"),
    H("atelier.ath_ree.texte_aide", "La proposition — modifiable avant de l'appliquer",
      "The proposal — editable before you apply it"),
    H("atelier.ath_ree.laisser_aide", "Garder le texte tel quel (la proposition est jetée)",
      "Keep the text as is (the proposal is discarded)"),
    H("atelier.ath_ree.laisser", "Laisser tel quel", "Leave as is"),
    H("atelier.ath_ree.appliquer_aide",
      "Écrire la proposition dans le chapitre — l'état d'avant est gardé dans 🕘 Versions",
      "Write the proposal into the chapter — the previous state is kept in 🕘 Versions"),
    H("atelier.ath_ree.appliquer", "Appliquer", "Apply"),

    # ── preview.html (aperçu statique de dev ; textes non déjà couverts ci-dessus) ──
    H("atelier.ath_prv.titre", "Atelier Chapitre — aperçu du thème v2 (dev only)",
      "Chapter Workshop — theme v2 preview (dev only)"),
    X(PRV, 20, "Ch. 04 — La marée", "<option> factice : titre de chapitre (contenu d'utilisateur simulé)"),
    X(PRV, 20, "Ch. 05 — Le rivage", "<option> factice : titre de chapitre (contenu d'utilisateur simulé)"),
    H("atelier.ath_prv.chapitre", "+ Chapitre", "+ Chapter"),
    H("atelier.ath_prv.manuscrit", "📚 Manuscrit", "📚 Manuscript"),
    H("atelier.ath_prv.enregistre", "enregistré", "saved"),
    H("atelier.ath_prv.theme", "Thème clair / sombre", "Light / dark theme"),
    H("atelier.ath_prv.importer", "📄 Importer (txt/docx/pdf)", "📄 Import (txt/docx/pdf)"),
    X(PRV, 45, "le Prophète", "sélection factice : nom d'entité (contenu d'utilisateur simulé)"),
    H("atelier.ath_prv.k_personnage", "➕ Personnage", "➕ Character"),
    H("atelier.ath_prv.k_lieu", "➕ Lieu", "➕ Place"),
    H("atelier.ath_prv.k_objet", "➕ Objet", "➕ Object"),
    H("atelier.ath_prv.k_ambiance", "➕ Ambiance", "➕ Ambience"),
    H("atelier.ath_prv.k_decor", "➕ Décor", "➕ Set"),
    H("atelier.ath_prv.lier", "🔗 Lier à…", "🔗 Link to…"),                               # <option>
    X(PRV, 56, '      <div id="hl" class="hl" aria-hidden="true">Nuit d\'encre sur <mark class="k-place">la baie de Kessel</mark>. La mer respire lentement, et sous la surface une lueur monte — <mark class="k-ambiance">froide, biolumineuse</mark>.', "texte de manuscrit factice surligné (contenu d'utilisateur simulé)"),
    X(PRV, 58, '<mark class="k-character">Le Prophète</mark> ne remonte pas : il s\'installe. Les <mark class="k-object">tables de marée</mark> deviennent inutiles ; le rivage apprend une autre grammaire.',
      "texte de manuscrit factice surligné (contenu d'utilisateur simulé)"),
    X(PRV, 60, '<mark class="k-date">Le 14 du huitième mois</mark>, les écrans de <mark class="k-decor">la promenade basse</mark> se sont tous mis à clignoter en même temps. Personne n\'a pensé à débrancher quoi que ce soit.',
      "texte de manuscrit factice surligné (contenu d'utilisateur simulé)"),
    X(PRV, 62, '<mark class="orphan">La vieille jetée</mark> — zone orpheline, à re-lier.',
      "texte de manuscrit factice surligné (contenu d'utilisateur simulé)"),
    X(PRV, 63, "Nuit d'encre sur la baie de Kessel.", "texte de manuscrit factice (contenu d'utilisateur simulé)"),
    H("atelier.ath_prv.adapter", "🎭 Adapter (IA)", "🎭 Adapt (AI)"),
    H("atelier.ath_prv.lire", "👁 Lire", "👁 Read"),
    H("atelier.ath_prv.reset", "🗑 Réinitialiser", "🗑 Reset"),
    X(PRV, 91, "EXT. BAIE DE KESSEL — NUIT", "slugline factice (contenu d'utilisateur simulé)"),
    H("atelier.ath_prv.camera", "Caméra & lumière", "Camera & lighting"),
    X(PRV, 98, "Caméra &amp; lumière", "texte brut à entité &amp; : sa version décodée a son H atelier.ath_prv.camera"),
    X(PRV, 101, "EXT. BAIE DE KESSEL - NUIT", "scénario Fountain factice (contenu d'utilisateur simulé)"),
    X(PRV, 108, "Le Prophète", "nom d'entité factice (contenu d'utilisateur simulé)"),
    X(PRV, 110, "froide, biolumineuse", "nom d'entité factice (contenu d'utilisateur simulé)"),
    H("atelier.ath_prv.derive", "dérivé des paragraphes 1–2 du chapitre", "derived from paragraphs 1–2 of the chapter"),
    X(PRV, 115, "EXT. PROMENADE BASSE — NUIT", "slugline factice (contenu d'utilisateur simulé)"),
    X(PRV, 122, "Caméra &amp; lumière", "texte brut à entité &amp; : sa version décodée a son H atelier.ath_prv.camera"),
    X(PRV, 125, "EXT. PROMENADE BASSE - NUIT", "scénario Fountain factice (contenu d'utilisateur simulé)"),
    X(PRV, 130, "14 du huitième mois", "nom d'entité factice (contenu d'utilisateur simulé)"),
    H("atelier.ath_prv.decouper", "🎬 Découper (IA)", "🎬 Break down (AI)"),
    H("atelier.ath_prv.para", "¶ Paragraphes", "¶ Paragraphs"),
    H("atelier.ath_prv.plan", "＋ Plan", "＋ Shot"),
    H("atelier.ath_prv.croquis", "croquis", "sketch"),
    H("atelier.ath_prv.non_genere", "non généré", "not generated"),
    H("atelier.ath_prv.plan_01", "Plan 01", "Shot 01"),
    H("atelier.ath_prv.plan_02", "Plan 02", "Shot 02"),
    H("atelier.ath_prv.btn_croquis", "✎ Croquis", "✎ Sketch"),
    X(PRV, 159, "Plongée nocturne sur la baie", "prompt de plan factice (contenu d'utilisateur simulé)"),
    H("atelier.ath_prv.plongee", "Plongée", "High angle"),                                # <option>
    H("atelier.ath_prv.fixe", "Fixe", "Static"),                                          # <option>
    H("atelier.ath_prv.entites", "entités :", "entities:"),
    X(PRV, 165, "froide, biolumineuse", "nom d'entité factice (contenu d'utilisateur simulé)"),
    X(PRV, 166, "Nuit d'encre sur la baie de Kessel. La mer respire lentement…",
      "extrait de manuscrit factice (contenu d'utilisateur simulé)"),
    X(PRV, 177, "Le Prophète", "nom d'entité factice (contenu d'utilisateur simulé)"),
    X(PRV, 183, "Gros plan sur l'œil du Prophète", "prompt de plan factice (contenu d'utilisateur simulé)"),
    H("atelier.ath_prv.gros_plan", "Gros plan", "Close-up"),                              # <option>
    H("atelier.ath_prv.travelling_avant", "Travelling avant", "Dolly in"),                # <option>
    X(PRV, 189, "tables de marée", "nom d'entité factice (contenu d'utilisateur simulé)"),
    H("atelier.ath_prv.nouveau", "＋ Nouveau", "＋ New"),
    H("atelier.ath_prv.reference", "référence", "reference"),
    H("atelier.ath_prv.non_generee", "non générée", "not generated"),
    H("atelier.ath_prv.generer", "✨ Générer", "✨ Generate"),
    X(PRV, 228, "alias : le Prophète, la créature, l'Écouteur", "alias d'entité factices (contenu d'utilisateur simulé)"),
    X(PRV, 229, "Céphalopode colossal", "description d'entité factice (contenu d'utilisateur simulé)"),
    X(PRV, 235, "Le Prophète ne remonte pas : il s'installe.", "extrait de manuscrit factice (contenu d'utilisateur simulé)"),
    X(PRV, 249, "alias : la baie, Kessel", "alias d'entité factices (contenu d'utilisateur simulé)"),
    X(PRV, 250, "Baie industrielle en fer à cheval", "description d'entité factice (contenu d'utilisateur simulé)"),
    H("atelier.ath_prv.vide", "Sélectionne un mot dans le script pour créer une entité.",
      "Select a word in the script to create an entity."),
    H("atelier.ath_prv.toast", "Storyboard découpé — 12 plans, Σ 1:04", "Storyboard broken down — 12 shots, Σ 1:04"),
]
