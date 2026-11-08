# -*- coding: utf-8 -*-
"""t421 (cartes hexagonales, 08/11/2026, vague finale) : LA garde du nom d'une image de la Bibliothèque.

`/images/upload` garde le nom du fichier tel quel : un import courant s'appelle « carte (1).png », « d'été.png »,
« a+b.png » ou « carte #3.png ». Une garde par liste blanche (lettres, chiffres, « . _ - » et espace) les refusait
ensuite partout (création d'un jeu depuis des images, Photolab) : l'image entrait dans la Bibliothèque mais aucun écran
ne l'ouvrait. Cette garde ne refuse donc QUE le dangereux :
  - vide, « . », « .. », plus de NOM_MAX caractères (points de code, comme `len`) ;
  - un séparateur de dossier (« / », « \\ ») ;
  - un caractère de contrôle (U+0000-U+001F, U+007F-U+009F) ;
  - un interdit de Windows : < > : " | ? * ;
  - une fin en point ou en espace (Windows les retire en silence : le fichier copié n'aurait plus le nom ouvert).
Les noms réservés de Windows (con, nul, com1…) gardent leur traitement : chaque copie qui en fait un chemin les suffixe.
Le miroir côté écran est `nomValide` de frontend/shared/dz-envoi.js (même règle, même plafond).

Module sans dépendance : importé par app/api (photolab_routes) comme par app/services (cards/depuis_images), sans
cycle.
"""
from __future__ import annotations

import re

__all__ = ["NOM_MAX", "nom_image_valide"]

NOM_MAX = 180
_INTERDIT = re.compile(r'[\x00-\x1f\x7f-\x9f<>:"|?*/\\]')


def nom_image_valide(nom) -> bool:
    """Vrai si `nom` peut désigner un fichier de la Bibliothèque sans danger."""
    return (isinstance(nom, str) and 0 < len(nom) <= NOM_MAX and nom not in (".", "..")
            and not nom.endswith((".", " ")) and _INTERDIT.search(nom) is None)
