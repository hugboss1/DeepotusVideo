"""t142 — Templates, tables de module de la couche : styles de texte (DZ_TEXTE_STYLES : nom et aide affichés par
DzTexteEditor), types et courbes d'animation (DZ_ANIM_TYPES, DZ_ANIM_COURBES : libellés des listes de DzAnimEditor).
Le premier élément de chaque ligne (id du style, type, courbe) est la VALEUR enregistrée dans le gabarit : il ne bouge
pas. Tables évaluées au chargement de la couche : dzT est déjà défini (runtime chargé avant le bundle)."""
from outils import L, S, X

CIBLE = "couche"

ENTREES = [
    # DZ_TEXTE_STYLES
    L(662234, "templates.styles.aucun", "Aucun effet", "No effect"),
    L(662248, "templates.styles.aucun_aide", "Retirer tous les effets (le texte redevient celui d’origine, contour par défaut)",
      "Remove all effects (the text goes back to its original look, default stroke)"),
    L(662359, "templates.styles.soustitre", "Sous-titre réseau", "Social subtitle"),
    L(662379, "templates.styles.soustitre_aide", "Contour noir épais et ombre nette, ajusté à la case : lisible sur toute image",
      "Thick black stroke and a sharp shadow, fitted to the slot: readable on any image"),
    L(662567, "templates.styles.neon", "Néon", "Neon"),
    L(662574, "templates.styles.neon_aide", "Fin contour cyan et halo flou de la même couleur",
      "Thin cyan stroke and a soft glow of the same color"),
    L(662733, "templates.styles.bandeau", "Bandeau", "Banner"),
    L(662743, "templates.styles.bandeau_aide", "Fond sombre à coins arrondis derrière le texte",
      "Dark rounded background behind the text"),
    L(662867, "templates.styles.degrade", "Titre dégradé", "Gradient title"),
    L(662883, "templates.styles.degrade_aide", "Dégradé jaune vers rose et ombre douce",
      "Yellow-to-pink gradient and a soft shadow"),

    # DZ_ANIM_TYPES
    L(678730, "templates.animtypes.aucune", "Aucune", "None"),
    L(678748, "templates.animtypes.fondu", "Fondu", "Fade", contexte=True),
    L(678771, "templates.animtypes.gauche", "Glissement ←", "Slide ←"),
    L(678802, "templates.animtypes.droite", "Glissement →", "Slide →"),
    L(678830, "templates.animtypes.haut", "Glissement ↑", "Slide ↑"),
    L(678860, "templates.animtypes.bas", "Glissement ↓", "Slide ↓"),
    X(678883, "identique dans les deux langues"),

    # DZ_ANIM_COURBES
    L(678926, "templates.animcourbes.douce", "Douce", "Smooth"),
    L(678945, "templates.animcourbes.lineaire", "Linéaire", "Linear"),
    L(678965, "templates.animcourbes.rebond", "Rebond", "Bounce"),
]
