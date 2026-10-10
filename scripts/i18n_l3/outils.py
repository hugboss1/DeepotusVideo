"""Format de saisie de la traduction L3 (t143), repris de L2 (t142) : chaque fichier scripts/i18n_l3/<groupe>.py
définit CIBLE (« montage ») et ENTREES, une liste faite avec ces trois constructeurs. Les positions
sont celles de la couche de BASE (main be7f9e9f) ; le générateur (scripts/i18n_l3_generer.py) en tire les nouvelles
couches et la table réversible scripts/i18n_l3_paires.json.

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

