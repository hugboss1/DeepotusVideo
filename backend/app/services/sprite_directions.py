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

LA LIMITE, DITE : la planche porte 4 vues, pas 8. La route l'écrit dans le manifeste (`directions: "4/8"`) au lieu de
la taire.

t339 (lot Scenario, B3, 28/10/2026) — 8 DIRECTIONS. Convention des feuilles 8 directions (relevé Scenario,
iso-cycles) : 5 DESSINÉES (S, SE, E, NE, N) et 3 en MIROIR (SW <- SE, W <- E, NW <- NE). La planche donne déjà S, E,
N (et W) : seules les diagonales sont GÉNÉRÉES (une image par vue, chaînée sur la face ou le dos découpés — de
l'argent : devis, `confirme_cout`, plafonds, dans la route). Les miroirs sont cochés par défaut ; décoché, un miroir
est généré (SW, NW) ou découpé (W : le profil gauche EST dessiné sur la planche). « Ne jamais miroiter » : un
personnage qui tient un objet ASYMÉTRIQUE changerait de main dans un miroir — aucun miroir n'est alors accepté, et
l'est est généré lui aussi, parce que l'est de la planche est le miroir logiciel du profil gauche.
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


# ── t339 : 8 directions ──────────────────────────────────────────────────────────────────────────────────────────
DESSINEES = ("south", "southeast", "east", "northeast", "north")
MIROIRS = {"southwest": "southeast", "west": "east", "northwest": "northeast"}
# la vue de CORPS de la planche qui vaut chaque direction (gratuite) ; « right » est le miroir logiciel de « left »
DE_LA_PLANCHE = {"south": "front", "east": "right", "north": "back", "west": "left"}
# la vue découpée qui sert de RÉFÉRENCE à une vue générée : la face pour ce qui regarde la caméra, le dos sinon
_REFERENCE = {"southeast": "front", "east": "front", "southwest": "front", "northeast": "back", "northwest": "back"}
_VUES = {
    "southeast": "full body THREE-QUARTER FRONT view, the body turned 45 degrees toward the RIGHT of the frame "
                 "(halfway between the front view and the right profile), face visible",
    "southwest": "full body THREE-QUARTER FRONT view, the body turned 45 degrees toward the LEFT of the frame "
                 "(halfway between the front view and the left profile), face visible",
    "northeast": "full body THREE-QUARTER BACK view, seen from behind at 45 degrees, the body facing away from the "
                 "camera toward the upper RIGHT of the frame",
    "northwest": "full body THREE-QUARTER BACK view, seen from behind at 45 degrees, the body facing away from the "
                 "camera toward the upper LEFT of the frame",
    "east": "full body RIGHT PROFILE view, nose pointing to the right of the frame",
}
_ASYMETRIQUE = (", holding the same object as in the reference in the same hand and on the same side of the body "
                "(never swap hands, this view is drawn, not mirrored)")


def plan_huit(miroirs=None, asymetrique: bool = False) -> list[dict]:
    """D'où vient chacune des 8 directions, dans l'ordre de HUIT : {direction, source: planche|generee|miroir, de}.
    `miroirs` : les directions à tirer en miroir (None = les trois). ValueError dite pour un nom hors des trois, et
    pour un miroir demandé quand le personnage tient un objet asymétrique."""
    voulus = set(MIROIRS) if miroirs is None else set(miroirs)
    hors = sorted(voulus - set(MIROIRS))
    if hors:
        raise ValueError(f"miroirs : {', '.join(hors)} — seules {', '.join(MIROIRS)} se tirent en miroir "
                         "(les 5 autres directions sont dessinées)")
    if asymetrique and voulus:
        raise ValueError("objet tenu asymétrique : ne jamais miroiter — décoche les miroirs "
                         f"({', '.join(sorted(voulus))}), ils seront générés")
    plan = []
    for d in HUIT:
        if d in voulus:
            plan.append({"direction": d, "source": "miroir", "de": MIROIRS[d]})
        elif d in DE_LA_PLANCHE and not (d == "east" and asymetrique):
            plan.append({"direction": d, "source": "planche", "de": DE_LA_PLANCHE[d]})
        else:
            plan.append({"direction": d, "source": "generee", "de": None})
    return plan


def generations(plan: list[dict]) -> list[str]:
    """Les directions à GÉNÉRER (payantes), dans l'ordre du plan."""
    return [p["direction"] for p in plan if p["source"] == "generee"]


def reference_vue(direction: str) -> str:
    return _REFERENCE[direction]


def prompt_vue(direction: str, asymetrique: bool = False) -> str:
    """Le prompt d'une vue générée, chaînée sur la vue de référence découpée (même consigne que les corps de la
    planche : même personnage, en pied, marges)."""
    if direction not in _VUES:
        raise ValueError(f"{direction} : cette direction ne se génère pas (découpée dans la planche)")
    return ("the exact same character, identical outfit, hairstyle and colors: " + _VUES[direction]
            + ", standing neutral pose, the entire figure head to feet inside the frame with margin above the head "
              "and below the feet, same body proportions as the reference"
            + (_ASYMETRIQUE if asymetrique else "") + BS._SHARP)


def directions_export(manifest: dict) -> list[dict] | None:
    """Pour les exports (atlas JSON, Paper2D) : [{name, frame, flip_h, mirror_of?, source?}] dans l'ordre des
    images, quand la feuille est une feuille de directions — le plan de la route s'il est là (8 directions depuis la
    planche), sinon des tags d'UNE image dont tous les noms sont des directions (4 découpées, 8 rendues du 3D). None
    pour toute autre feuille : une animation n'a pas de directions."""
    plan = (manifest.get("source") or {}).get("plan")
    if isinstance(plan, list) and plan:
        out = []
        for i, p in enumerate(plan):
            x = {"name": p["direction"], "frame": i, "flip_h": p["source"] == "miroir", "source": p["source"]}
            if p["source"] == "miroir":
                x["mirror_of"] = p["de"]
            out.append(x)
        return out
    tags = (manifest.get("anim") or {}).get("tags") or []
    if tags and all(t.get("name") in HUIT and t.get("from") == t.get("to") for t in tags):
        return [{"name": t["name"], "frame": t["from"], "flip_h": False} for t in tags]
    return None
