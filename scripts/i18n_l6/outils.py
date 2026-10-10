"""Format de saisie de la traduction L6 (t146, Vectorlab). Chaque fichier scripts/i18n_l6/<groupe>.py définit ENTREES,
une liste faite avec les constructeurs ci-dessous. Les ancres sont prises dans les sources de la BASE (commit BASE de
scripts/i18n_l6_generer.py) : `fichier` est relatif à frontend/vectorlab/ (« js/mod-doc.js », « index.html »),
`ligne` est le numéro de ligne (1 = première) où COMMENCE le texte ancré.

  L(fichier, ligne, lit, cle, fr, en, n=1, contexte=False)
        le littéral JS `lit` (guillemets compris : "…", '…' ou `…` sans ${}) devient T("cle"). Il doit apparaître
        exactement n fois en commençant sur cette ligne (toutes remplacées). fr = le contenu du littéral, tel quel.
  S(fichier, ligne, avant, apres, dico, n=1)
        le code `avant` (exact, qui commence sur cette ligne, peut couvrir plusieurs lignes) devient `apres`.
        dico = {cle: (fr, en)} ou {cle: (fr, en, "contexte")}. Sert aux gabarits `…${x}…` (→ T("cle", {x: …})),
        au HTML dans une chaîne (`<b>Calque</b>` → `<b>${T("cle")}</b>`), aux concaténations ("Plan " + i).
  X(fichier, ligne, lit, raison, n=1)
        littéral GARDÉ tel quel (valeur technique, id, nom propre, unité, format, texte identique dans les deux
        langues, valeur stockée ou envoyée au serveur) : la raison est dite.
  H(cle, fr, en, contexte=False)
        entrée du dictionnaire SANS changement de source : texte de index.html (traduit à l'affichage par la
        surcouche de /shared/dz-i18n.js, comme le Photolab), ou texte composé ailleurs qui doit être connu.

Règles (skill traduction-deepotus) : clés `vectorlab.<zone>.<role>` en français ASCII minuscule ; fr = le texte
français existant copié tel quel ; en = anglais d'interface (court, impératif pour un bouton, pas de calque) ;
variables `{x}` identiques des deux côtés ; JAMAIS traduire une valeur envoyée au serveur, stockée (localStorage,
document .vlab, noms d'outils internes, ids, data-*), comparée (e.key, types MIME) ; un même français a UNE traduction
dans tous les dictionnaires (sinon contexte=True : la clé ne sert qu'à T, la surcouche l'ignore).
"""


def L(fichier, ligne, lit, cle, fr, en, n=1, contexte=False):
    return {"type": "L", "fichier": fichier, "ligne": ligne, "avant": lit, "apres": f'T("{cle}")', "n": n,
            "cle": cle, "dico": {cle: (fr, en, "contexte") if contexte else (fr, en)}}


def S(fichier, ligne, avant, apres, dico, n=1):
    return {"type": "S", "fichier": fichier, "ligne": ligne, "avant": avant, "apres": apres, "n": n,
            "dico": dict(dico)}


def X(fichier, ligne, lit, raison, n=1):
    return {"type": "X", "fichier": fichier, "ligne": ligne, "avant": lit, "raison": raison, "n": n}


def H(cle, fr, en, contexte=False):
    return {"type": "H", "cle": cle, "dico": {cle: (fr, en, "contexte") if contexte else (fr, en)}}
