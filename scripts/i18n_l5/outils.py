"""Format de saisie de la traduction L5 (t145 : sous-titres, transfert, dialogues). Chaque fichier
scripts/i18n_l5/<groupe>.py définit :

  CIBLE   "subs" (le bloc SUBS du bundle), "transfert" (frontend/patches/transfert.js) ou "dialogue"
          (frontend/shared/dialogue.js, recopié octet pour octet dans frontend/patches/ et frontend/dist/shared/)
  PLAGE   (première, dernière) ligne de la cible où chercher (pour « subs » : lignes du CŒUR du bloc, la ligne du
          marqueur BEGIN comptant pour 1 ; pour une source : lignes du fichier) — deux groupes ne se partagent pas
          une ligne
  ENTREES la liste faite avec ces constructeurs :

  L(lit, cle, fr, en, n=1)       le littéral `lit` (guillemets compris, tel qu'il est écrit) devient dzT("cle") ;
                                  il doit apparaître EXACTEMENT n fois dans la plage
  S(avant, apres, dico, n=1)     le code `avant` (exact) devient `apres` ; dico = {cle: (fr, en)}
  X(lit, raison, n=1)            littéral GARDÉ tel quel (valeur comparée, envoyée ou stockée, nom propre, format)

Contrairement à L2 (positions), les entrées se repèrent par leur TEXTE : le générateur (scripts/i18n_l5_generer.py)
calcule les positions dans la cible de BASE et, pour le bundle, les ancres uniques de la table que rejoue le maillon
patch_bundle_i18n_l5.py. Règles du skill traduction-deepotus : fr = texte français existant copié tel quel ; en =
anglais d'interface (court, impératif pour un bouton) ; variables {x} identiques des deux côtés ; rien d'envoyé au
serveur ni de stocké n'est traduit. contexte=True : un même français traduit autrement ailleurs (clé réservée à dzT,
ignorée par la surcouche) ; une valeur de dico peut aussi être (fr, en, "contexte").
"""


def L(lit, cle, fr, en, n=1, contexte=False):
    return {"type": "L", "avant": lit, "apres": f'dzT("{cle}")', "n": n,
            "dico": {cle: (fr, en, "contexte") if contexte else (fr, en)}}


def S(avant, apres, dico, n=1):
    return {"type": "S", "avant": avant, "apres": apres, "n": n, "dico": dict(dico)}


def X(lit, raison, n=1):
    return {"type": "X", "avant": lit, "raison": raison, "n": n, "dico": {}}
