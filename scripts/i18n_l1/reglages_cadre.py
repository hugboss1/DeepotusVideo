"""t141 — Réglages : le cadre (xm, liste des onglets), Personas (jm), Apparence (Cm), Chemins (_m)."""
from outils import L, S, X

ENTREES = [
    # xm : titre et onglets (la recherche DzSettingsSearch est dans reglages_outils)
    L(653067, "reglages.cadre.titre", "Réglages", "Settings"),
    L(653127, "reglages.onglet.diag", "Diagnostic", "Diagnostics"),
    L(653155, "reglages.onglet.coffre", "Coffre", "Vault"),
    L(653182, "reglages.onglet.appareils", "Appareils", "Devices"),
    L(653207, "reglages.onglet.cles", "Clés d'API", "API keys"),
    L(653235, "reglages.onglet.comptes", "Comptes connectés", "Connected accounts"),
    L(653273, "reglages.onglet.personas", "Personas", "Personas"),
    L(653301, "reglages.onglet.marque", "Identité visuelle", "Branding"),
    L(653325, "reglages.onglet.pack", "Pack de sous-titres", "Caption pack"),
    L(653357, "reglages.onglet.defauts", "Fournisseurs par défaut", "Provider defaults"),
    L(653391, "reglages.onglet.chemins", "Chemins", "Paths"),
    L(653412, "reglages.onglet.news", "News", "News"),
    L(653438, "reglages.onglet.apparence", "Apparence", "Appearance"),
    L(653467, "reglages.onglet.tarifs", "Tarifs et budget", "Pricing & budget"),
    L(653504, "reglages.onglet.transfert", "Transfert entre machines", "Machine transfer"),

    # jm : Personas
    L(658685, "reglages.personas.titre", "Personas", "Personas"),
    L(658774, "reglages.personas.nouveau", "Nouveau persona", "New persona"),
    L(658890, "reglages.personas.aide_debut", "Chaque persona est un fichier JSON : ", "Each persona is a JSON file at "),
    X(658964, "chemin de fichier"),
    L(658994, "reglages.personas.aide_fin",
      ". Le persona actif règle le scénariste des News, le ton du générateur de prompts et la voix off par défaut. "
      "Les personas fournis sont en lecture seule : dupliquez-en un pour le modifier.",
      ". The active one drives the News scripter, the prompt generator's tone, and the default Voiceover. "
      "Built-in personas are read-only; duplicate any of them to edit."),

    # Cm : Apparence
    L(674697, "reglages.apparence.titre", "Apparence", "Appearance"),
    L(674794, "reglages.apparence.aide",
      "Animations et effets. Enregistré dans votre navigateur, appliqué tout de suite à tous les écrans.",
      "Motion + flair toggles. Saved in your browser; apply across all screens immediately."),
    L(675131, "reglages.apparence.mouvement_reduit", "Mouvement réduit", "Reduced motion"),
    L(675218, "reglages.apparence.mouvement_aide",
      "Coupe la pulsation du halo, la cascade des bords, le zoom de l'écran d'accueil et les reflets. Suit ",
      "Disable halo pulse, edge cascade, splash zoom, caustics. Honors "),
    L(675352, "reglages.apparence.mouvement_auto", " automatiquement.", " automatically."),
    L(675604, "reglages.apparence.halo", "Halo de tentacules sur le nœud actif", "Tentacle halo on active node"),
    L(675703, "reglages.apparence.halo_aide", "L'effet des profondeurs sur le nœud du Studio en cours.",
      "The deep flair on the running Studio node."),

    # _m : Chemins
    L(675852, "reglages.chemins.images", "Dossier des images", "Images folder"),
    L(675873, "reglages.chemins.images_aide", "Où sont rangées les images importées. La Bibliothèque lit ici.",
      "Where uploaded source images are stored. Library reads from here."),
    L(675968, "reglages.chemins.sorties", "Dossier des sorties", "Outputs folder"),
    L(675990, "reglages.chemins.sorties_aide", "Les rendus finaux, l'audio et les sous-titres y sont écrits, job par job.",
      "Final renders, audio, captions are written here per job."),
    L(676249, "reglages.chemins.titre", "Chemins", "Paths"),
    L(676343, "reglages.chemins.aide_1", "Lus depuis ", "Resolved from "),
    L(676416, "reglages.chemins.aide_2", ". Configurés automatiquement par ", ". Auto-configured by "),
    L(676508, "reglages.chemins.aide_3", ". Pour les changer, modifiez ", ". To change them, edit "),
    L(676591, "reglages.chemins.aide_4", " avec ", " with "),
    L(677395, "reglages.chemins.copier", "Copier", "Copy"),
    L(677522, "reglages.chemins.version_backend", "Version du backend", "Backend version"),
    L(677772, "reglages.chemins.version_api", "Version de l'API", "API version"),
    L(677856, "reglages.chemins.depuis", "Depuis ", "From "),
]
