"""t142 — templates : fm (écran Modèles, liste des layouts), hm (éditeur visuel des régions, dzAddKind imbriqué),
dzRegionFace (visage d'une région dans l'aperçu), dzDupTemplate, dzDelTemplate.

« layout » se dit « mise en page » (comme coque.rail.modeles_desc). Le nom, la description et le slot_label d'un layout
créé ou dupliqué partent au serveur (JSON.stringify) : gardés. Les textes posés dans une région (« My text »,
« ● BREAKING ● $DEEP ● », badges) sont du CONTENU enregistré : gardés, comme leurs reprises d'aperçu dans dzRegionFace.
Le statut d'enregistrement est testé par y.startsWith("Save failed") pour le rouge : le test passe par la même clé
que le message (dzT(...).trim())."""
from outils import L, S, X

FRAGMENTS = {
    "px solid ": "valeur CSS de bordure",
}

ENTREES = [
    # dzDelTemplate
    S(539996, '\'Delete le layout "\'+(nm||id)+\'" ? Action irreversible.\'',
      'dzT("templates.supprimer.confirmer",{nom:nm||id})',
      {"templates.supprimer.confirmer": ('Supprimer la mise en page "{nom}" ? Action irréversible.',
                                         'Delete layout "{nom}"? This cannot be undone.')}),
    L(540168, "templates.supprimer.echec", "Suppression impossible : ", "Delete failed: "),
    L(540315, "templates.supprimer.echec", "Suppression impossible : ", "Delete failed: "),

    # dzDupTemplate
    L(540523, "templates.dupliquer.impossible", "Duplication impossible", "Duplicate failed"),
    X(540635, "nom du layout dupliqué envoyé au serveur (contenu enregistré)"),
    X(540645, "suffixe du nom du layout dupliqué envoyé au serveur (contenu enregistré)"),
    L(540939, "templates.dupliquer.echec", "Duplication impossible : ", "Duplicate failed: "),
    L(541039, "templates.dupliquer.echec", "Duplication impossible : ", "Duplicate failed: "),

    # fm : création d'un layout (contenu envoyé au serveur)
    X(542252, "nom du layout créé envoyé au serveur (contenu enregistré)"),
    X(542268, "nom du layout créé envoyé au serveur (contenu enregistré)"),
    X(542290, "description du layout créé envoyée au serveur (contenu enregistré)"),
    X(542568, "slot_label enregistré dans le layout"),
    L(543204, "templates.creer.echec", "Échec de la création : ", "Create failed: "),
    L(543295, "templates.creer.echec", "Échec de la création : ", "Create failed: "),

    # fm : écran
    L(543819, "templates.ecran.titre", "Modèles", "Templates"),
    L(543983, "templates.ecran.rechercher", "Rechercher…", "Search…"),
    L(544182, "templates.ecran.nouveau", "Nouveau :", "New:"),
    L(546861, "templates.menu.dupliquer", "⧉  Dupliquer", "⧉  Duplicate"),
    L(547010, "templates.menu.verrouille", "🔒  Intégré (verrouillé)", "🔒  Built-in (locked)"),
    L(547246, "templates.menu.supprimer", "🗑  Supprimer", "🗑  Delete"),

    # hm : régions ajoutées (contenu enregistré dans le layout)
    X(548908, "texte de démonstration posé dans la région (contenu enregistré)"),
    X(548964, "nom de police"),
    X(549159, "texte de démonstration posé dans la région (contenu enregistré)"),
    X(549254, "nom de police"),
    X(549933, "texte de démonstration du badge (contenu enregistré)"),
    X(550053, "nom de police"),
    X(550243, "texte de démonstration du badge (contenu enregistré)"),
    X(550540, "texte de démonstration du badge (contenu enregistré)"),

    # hm : enregistrement
    L(553220, "templates.enregistrement.ok", "Enregistré ✓", "Saved ✓"),
    L(553273, "templates.enregistrement.echec", "Échec de l'enregistrement : ", "Save failed: "),
    L(553331, "templates.enregistrement.echec", "Échec de l'enregistrement : ", "Save failed: "),
    S(560200, '"Save failed"', 'dzT("templates.enregistrement.echec").trim()',
      {"templates.enregistrement.echec": ("Échec de l'enregistrement : ", "Save failed: ")}),

    # hm : en-tête et barre d'ajout
    L(553871, "templates.editeur.nom", "Nom de la mise en page", "Layout name"),
    L(554169, "templates.editeur.spatial", "Éditeur spatial · ", "Spatial editor · "),
    L(554199, "templates.editeur.aide_glisser", " · glissez les régions ou leurs poignées", " · drag regions or their handles"),
    L(554470, "templates.editeur.ajouter", "Ajouter :", "Add:"),
    L(554488, "templates.region.texte", "Texte", "Text"),
    L(554506, "templates.region.ticker", "Bandeau défilant", "Ticker"),
    L(554529, "templates.region.separateur", "Séparateur", "Separator"),
    L(554551, "templates.region.marque", "Marque", "Brand"),
    X(554568, "libellé du badge LIVE, identique au texte inséré dans la région"),
    L(554587, "templates.region.prix", "$ Prix", "$ Price"),
    X(554621, "identique dans les deux langues"),

    # hm : inspecteur de région
    S(557063, '`Region · ${c.slot_name||c.type}`', 'dzT("templates.inspecteur.region",{nom:c.slot_name||c.type})',
      {"templates.inspecteur.region": ("Région · {nom}", "Region · {nom}")}),
    L(557097, "templates.inspecteur.aucune", "Aucune région sélectionnée", "No region selected"),
    L(557927, "templates.inspecteur.type", "Type : ", "Type: "),
    L(558080, "templates.region.texte", "Texte", "Text"),
    L(558209, "templates.inspecteur.texte_marque", "Texte de marque", "Brand text"),
    L(558625, "templates.inspecteur.couleur", "Couleur", "Color"),
    L(558635, "templates.inspecteur.couleur_texte", "Couleur texte", "Text color"),
    L(558832, "templates.inspecteur.couleur_fond", "Couleur fond", "Background color"),
    L(559126, "templates.inspecteur.pulsation", "Pulsation (animée)", "Pulse (animated)"),
    L(559188, "templates.inspecteur.image_sticker", "Image du sticker", "Sticker image"),
    L(559860, "templates.inspecteur.supprimer", "🗑  Supprimer la région", "🗑  Delete region"),
    L(559954, "templates.inspecteur.aide",
      "Cliquez une région dans l'aperçu pour la modifier. Glissez son corps pour la déplacer, les points pour la redimensionner.",
      "Click a region in the preview to edit. Drag the body to move, the dots to resize."),
    L(560346, "templates.editeur.enregistrer", "Enregistrer la mise en page", "Save layout"),
    L(560442, "templates.editeur.ouvrir_studio", "Ouvrir dans le Studio", "Open in Studio"),

    # dzRegionFace : aperçu d'une région
    X(564595, "texte de démonstration de l'aperçu du ticker (reprise du contenu)"),
    X(564750, "nom de police"),
    L(564882, "templates.region.texte", "Texte", "Text"),
    L(565291, "templates.apercu.avatar", "Avatar HeyGen", "HeyGen avatar"),
    X(565963, "identique dans les deux langues"),
    X(566075, "valeur CSS"),
    X(566484, "identique dans les deux langues"),
    X(566576, "texte de démonstration du badge (reprise du contenu inséré)"),
    X(566598, "texte de démonstration du badge (reprise du contenu inséré)"),
    X(566623, "texte de démonstration du badge (reprise du contenu inséré)"),
    L(567465, "templates.apercu.reel_news", "Reel News", "News reel"),
    X(567544, "identique dans les deux langues"),
]
