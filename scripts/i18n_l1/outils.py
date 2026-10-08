"""Format de saisie de la traduction L1 (t141) : chaque fichier scripts/i18n_l1/<groupe>.py définit ENTREES, une liste
faite avec ces trois constructeurs. Les positions sont celles du bundle de BASE (main 92bec8ed) ; le générateur
(scripts/i18n_l1_generer.py) en tire des ancres uniques et la table que rejoue le maillon patch_bundle_i18n_l1.py.

  L(pos, cle, fr, en)            le littéral (avec ses guillemets) qui commence à `pos` devient dzT("cle")
  S(pos, avant, apres, dico)     le code `avant` (exact, commence à `pos`) devient `apres` ; dico = {cle: (fr, en)}
  X(pos, raison)                 littéral GARDÉ tel quel (nom propre, format, valeur technique) : la raison est dite

Règles (skill traduction-deepotus) : fr = référence (texte français existant copié tel quel, ou écrit pour un texte du
socle anglais) ; en = anglais d'interface (court, impératif pour un bouton) ; variables `{x}` identiques des deux
côtés ; rien d'envoyé au serveur ni de stocké n'est traduit.
"""


def L(pos, cle, fr, en, contexte=False):
    """contexte=True : le même français a AILLEURS une autre traduction (« Effacer » = Clear dans le Photolab, Delete
    dans la Corbeille) ; l'entrée ne sert qu'à dzT(clé), la surcouche l'ignore. Une valeur de dico peut aussi être
    (fr, en, "contexte") dans S et K."""
    return {"type": "L", "pos": pos, "cle": cle, "dico": {cle: (fr, en, "contexte") if contexte else (fr, en)}}


def S(pos, avant, apres, dico):
    return {"type": "S", "pos": pos, "avant": avant, "apres": apres, "dico": dict(dico)}


def X(pos, raison):
    return {"type": "X", "pos": pos, "raison": raison}


def K(cle, fr, en):
    """Clé posée HORS de la table : un texte de la couche frontend/patches/montage.js passé par dzT dans la couche
    elle-même (refresh_layer), dont le dictionnaire est assemblé ici avec les autres."""
    return {"type": "K", "dico": {cle: (fr, en)}}
