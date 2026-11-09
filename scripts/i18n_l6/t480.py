"""t480 (09/11/2026) — lot D5 « Couleur et motif », T6 : les pinceaux artistique, dispersion et motif, vivants (module
NEUF js/mod-pinceaux.js, hors table). Décomposer un tracé peint passe par la condition de mod-vivants.js déjà greffée par
t450.py (étendue à o.pinceau) ; le recalcul est appelé par deformations_rafraichir (mod-deformer.js, module neuf).
Aucune édition de BASE ici : les refus traduits, en entrées H."""
from outils import L, S, X, H  # noqa: F401

ENTREES = [
    H("vectorlab.pinceaux.genre", "Genre de pinceau inconnu : « {genre} ».", "Unknown brush type: “{genre}”."),
    H("vectorlab.pinceaux.aucune_selection", "Sélectionnez d'abord les objets.", "Select the objects first."),
    H("vectorlab.pinceaux.nom_defaut", "Pinceau {n}", "Brush {n}"),
    H("vectorlab.pinceaux.borne", "Valeur hors bornes : de {min} à {max}.", "Value out of range: from {min} to {max}."),
    H("vectorlab.pinceaux.choix", "Choix inconnu : « {v} ».", "Unknown choice: “{v}”."),
    H("vectorlab.pinceaux.trop", "Trop de copies : {n} au plus (augmentez l'espacement ou la taille).",
      "Too many copies: {n} at most (increase the spacing or the size)."),
    H("vectorlab.pinceaux.inconnu", "Pinceau inconnu : {id}.", "Unknown brush: {id}."),
    H("vectorlab.pinceaux.pas_trace", "Un pinceau se pose sur un tracé, pas sur cet objet ({type}).",
      "A brush applies to a path, not to this object ({type})."),
    H("vectorlab.pinceaux.pas_pinceau", "{id} n'est pas un tracé peint.", "{id} is not a brushed path."),
    H("vectorlab.pinceaux.sans_geometrie", "Ce pinceau n'a aucun dessin à poser le long d'un tracé.",
      "This brush has no drawing to lay along a path."),
]
