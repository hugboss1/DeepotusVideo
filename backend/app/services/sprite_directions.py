# -*- coding: utf-8 -*-
"""Les directions d'un sprite depuis la bible (t111, plan-sprites T9 partie serveur, CORRIGÉ le 06/10/2026).

La planche d'un personnage est composée PAR CODE (`board_service.compose_character_board`) : 4 colonnes
front / left / right / back, les visages au-dessus des corps, fond `_BG`, gouttières `_GUTTER`. Son layout est
déterministe, donc elle se DÉCOUPE au lieu d'être régénérée — c'est ce qui tient l'identité, et c'est gratuit.

CE QUE LE PLAN NE SAVAIT PAS (il date du 03/09) : le dépôt découpe déjà ces planches — `board_service.
decouper_planche`, tâche #62 (02/10), qui VÉRIFIE la géométrie (hauteur exacte des bandes, nombre de panneaux par
bande), rend None plutôt que des vues fausses, et écrit chaque vue une fois (`<planche>_<clé>.png`) pour la partager
avec les générateurs multi-références. Le plan réécrivait un second détecteur ; deux découpeurs auraient eu deux
idées de ce qu'est une planche. Ce module n'en a aucune : il prend les CORPS de celui de #62, dans l'ordre des
colonnes, et leur donne un nom de direction.

LA LIMITE, DITE : la planche porte 4 vues, pas 8. Les diagonales demanderaient une génération par vue (de l'argent,
et une référence multiple) ; la route l'écrit dans le manifeste (`directions: "4/8"`) au lieu de la taire.
"""
from __future__ import annotations

from pathlib import Path

from app.services import board_service as BS

# L'ordre EST celui des colonnes de `compose_character_board` (`order = ["front", "left", "right", "back"]`).
COLONNES = ("front", "left", "right", "back")

# Nom de direction façon feuille 8 directions (le « sud » regarde la caméra). `left` est le profil dont le nez
# pointe vers la GAUCHE du cadre (le prompt du panneau le dit : « nose pointing to the left of the frame »), donc
# l'ouest ; `right` en est le MIROIR (`mirrors: {"right": "left"}` du plan de planche), donc l'est.
VERS_HUIT = {"front": "south", "left": "west", "right": "east", "back": "north"}
HUIT = ("south", "southwest", "west", "northwest", "north", "northeast", "east", "southeast")


def directions() -> list[str]:
    return [VERS_HUIT[c] for c in COLONNES]


def vues_de_planche(images_path: Path, planche: str, kind: str) -> list[str]:
    """Les noms des 4 vues de CORPS de la planche, dans l'ordre des directions. ValueError dite sinon.

    `kind` est celui de l'entité : seule une planche de PERSONNAGE a un profil et un dos — un lieu ou un objet se
    découpe aussi (#62), mais ses panneaux ne sont pas des directions."""
    plan = BS.PANEL_PLANS.get(kind) or {}
    if plan.get("compose") != "character":
        raise ValueError(f"« {kind} » n'est pas un personnage : seule une planche de personnage porte des "
                         "directions (face, profils, dos)")
    vues = BS.decouper_planche(images_path, planche, kind)
    if not vues or any(c not in vues for c in COLONNES):
        raise ValueError(f"{Path(str(planche)).name} n'est pas une planche de personnage composée par l'Atelier "
                         "(bandes ou colonnes inattendues) — rien n'est découpé plutôt que des vues fausses")
    return [vues[c] for c in COLONNES]


def tags_directions(noms_directions: list[str]) -> list[dict]:
    """Un tag d'UNE image par direction : c'est exactement ce qu'est une feuille de directions, et cela donne à
    Godot et Aseprite quatre (ou huit) animations nommées au lieu d'une seule anonyme."""
    return [{"name": d, "from": i, "to": i, "direction": "forward"} for i, d in enumerate(noms_directions)]
