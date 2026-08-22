# -*- coding: utf-8 -*-
"""Card Forge — LES MODÈLES DE DECK (phase 3a, tâche 3 ; spec §6.1/§6.2/§6.4).

Ce fichier appartient à CORE, comme `core.py` : il n'est pas l'une des neuf
pièces (pas de sous-arbre à lui, pas de couche à dessiner, pas de `{did}` dans
ses chemins). Il sert deux routes, montées AVANT le joker `/{did}` :

    GET  /api/cards/models      les 7 modèles d'usine + les modèles perso
    POST /api/cards/models      « enregistrer comme modèle » (sans les images)

et il fournit à `core.py` de quoi instancier (`POST /decks {model}`).

CE QU'EST UN MODÈLE — le principe acté de la spec §6.1 : **un modèle SEED un
deck ordinaire**. Il n'y a pas de « deck lié à un modèle » : l'instanciation
écrit les sous-arbres par le MÊME chemin d'écriture que l'autosave
(`core.patch_deck`, remplacement de sous-arbre entier), et après quoi le deck
est indiscernable d'un deck construit à la main. Aucune référence au modèle
n'est gardée — le partitionnement de `normalize_deck` la jetterait de toute
façon, et c'est très bien ainsi.

D'OÙ VIENNENT LES DONNÉES (aucune n'est inventée ici) :

  · l'HABILLAGE (`frame`) vient de `frame.archetype_frame(nom)` — LA FONCTION,
    jamais la table `ARCHETYPE_FRAMES` : elle rend une copie profonde (entrée
    F9 de la T2). Retaper ces 27 réglages ici en ferait une seconde source de
    vérité, et la première divergence silencieuse serait un deck instancié qui
    ne ressemble pas à son archétype ;
  · les ZONES (`type.slots`) sont celles de la spec §6.2:323-354, en
    millimètres depuis le coin de COUPE (même origine que `type.py`) ;
  · les POLICES sont celles que `mod-type.js` sait CHARGER (bloc
    `FONTS_LOCAL`, 23 familles, miroir de `type.FONT_META`). Les fontes citées
    par la spec qui n'y sont pas ont un repli **NOMMÉ** dans `fonts_note` —
    jamais un échec silencieux (décision 2 du plan 3a) ;
  · la FINITION est un identifiant de la table de P8 (`gltf.FINISHES`) et la
    MATIÈRE un identifiant du catalogue de P6 (bloc `CF-TEXTURE-CATALOG` de
    `mod-texture.js` — le backend n'en a pas de miroir : il ne dessine pas).

TROIS DÉCISIONS PRISES ICI, ET POURQUOI :

  1. **Le format est DÉCLARÉ (`poker_eu`), pas supposé.** Les zones §6.2 sont
     celles du poker 63 x 88. Mesuré par la T2 sur les douze formats : `winMM`
     re-borne la fenêtre dès que le format rétrécit (le carré 47 x 47 de
     « monstre » — qui EST l'archétype — devient 31,75 x 44,45 sur `micro`) et
     la plaque de bas de carte passe à une hauteur NÉGATIVE sur `micro`,
     `mini` et `square_eu`. Un modèle porte donc l'identifiant de SON format,
     et l'instanciation l'écrit. Le reste du bloc `format` (définition, fond
     perdu, rayon de coin) appartient au DECK, pas au modèle : ce sont des
     réglages d'impression, ils reprennent leurs défauts.
  2. **`palette` est une LECTURE du modèle, pas une quatrième table de
     couleurs.** `palette_of` relit l'encre dominante des slots, la couleur de
     plaque dominante et la teinte du support. Une palette écrite à la main
     serait décorative : elle mentirait dès la première retouche d'encre, et
     rien ne le dirait. Ici elle ne PEUT pas mentir.
  3. **« Enregistrer comme modèle » GARDE les textes des slots** et n'exclut
     que les illustrations (spec §6.4 : « format, frame, type, palette,
     texture — PAS les illustrations »). Raison mesurable : depuis la T1, un
     slot dont le texte est vide ne peint pas sa plaque (`drawSlot` est sous
     la garde `if (!m.empty)`). Un modèle aux textes purgés reviendrait donc
     SANS SES CARTOUCHES — une mise en page à trous, là où l'on croyait
     n'enlever que du contenu. Ce qui est purgé, lui, l'est vraiment :
     `face.src`, `face.default_art` et le papier importé (`texture.custom`),
     qui pointent tous vers des octets restés dans le deck d'origine.
"""
from __future__ import annotations

import asyncio
import copy
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from loguru import logger

from . import core
from .contract import DEFAULT_FMT, FORMATS, is_valid_did
from .frame import archetype_frame
from .gltf import DEFAULT_FINISH, FINISHES
from . import type as type_mod

router = APIRouter()

# Le dossier des modèles perso, hors du dépôt et hors des sorties : c'est de
# la préférence utilisateur, elle survit à une réinstallation (spec §6.4).
MODELS_DIR = "cardforge_models"
LABEL_MAX = 80
SLUG_MAX = 48
PERSO_MAX = 400            # garde-fou de listage : un dossier n'est pas une BDD
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
# La matière de repli quand un modèle perso portait un papier IMPORTÉ : le
# défaut de l'écran (`DEF.paper`, mod-texture.js). Le fichier importé, lui,
# reste dans le deck d'origine — un modèle ne l'emporte pas.
PAPIER_DEFAUT = "velin"


def models_root() -> Path:
    """`{DATA_ROOT}/cardforge_models/`. Résolu à l'APPEL, comme
    `contract.decks_root` : le dossier de données est une propriété du
    processus (variable `DEEPOTUS_DATA_DIR`), pas de l'import."""
    from app.config import DATA_ROOT
    p = DATA_ROOT / MODELS_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


# ════════════════════════════════════════════════════════════════════════════
# 1. LA FABRIQUE — un slot de modèle est un objet COMPLET
# ════════════════════════════════════════════════════════════════════════════
# Forme de stockage retenue : les 35 clés de `SLOT_DEFAULTS`, jamais un
# partiel. Deux raisons. (a) `type.norm_slot` ne change alors RIEN — et cette
# idempotence est la preuve, vérifiable en une ligne, que la donnée est propre
# plutôt que « réparable ». (b) Le painter reçoit les slots du document TELS
# QUELS : un partiel obligerait chaque lecteur à connaître les défauts.

def _slot(sid: str, label: str, box, **kw) -> dict:
    s = copy.deepcopy(type_mod.SLOT_DEFAULTS)
    s["id"] = sid
    s["label"] = label
    s["box"] = [float(v) for v in box]
    for k, v in kw.items():
        if k not in s:
            # UNE CLÉ INCONNUE EST UNE FAUTE DE FRAPPE, pas une extension :
            # `plate_colour` serait tombé dans le vide et la plaque n'aurait
            # jamais été peinte, sans un mot. Donnée statique : l'erreur est
            # déterministe, elle se voit au premier import.
            raise ValueError(f"slot {sid!r} : réglage inconnu {k!r}")
        s[k] = float(v) if (isinstance(s[k], float)
                            and not isinstance(v, bool)) else v
    return s


def _element(eid: str, label: str, hint: str, slots: list) -> dict:
    """Un preset de slot(s) ajoutable — la « palette d'éléments » de §6.1. La
    donnée est livrée dès la 3a ; l'écran qui y pioche est la 3b."""
    return {"id": eid, "label": label, "hint": hint, "slots": slots}


# ════════════════════════════════════════════════════════════════════════════
# 2. LES SEPT ARCHÉTYPES — zones §6.2:323-354, en mm depuis le coin de COUPE
# ════════════════════════════════════════════════════════════════════════════
# Ce que la spec donne pour chacun est recopié en commentaire au-dessus de ses
# slots, sous la forme « x,y (largeur x hauteur) ». Les zones citées SANS
# dimension (« nom 19,4 ») fixent le coin ; la taille est un choix
# d'implémenteur, borné par la zone voisine.
#
# CE QUI N'EST PAS UN SLOT : la fenêtre d'illustration (elle appartient au
# cadre, publiée par le painter en `frame.art_window`) et les ornements du
# cadre. Un modèle ne dessine rien : il POSE des objets Cardforge ordinaires.
#
# CE QUE 3a NE PEUT PAS ENCORE POSER : les icônes, drapeaux, écussons et
# pastilles d'école de la spec sont des IMAGES. La 3a n'a que des slots de
# TEXTE ; ces zones existent donc, à leur place et à leur taille, avec un
# texte de remplacement — et le `hint` du modèle le dit. Les calques d'image
# arrivent en 3b (§6.1, palette d'ajout).

_INK_OR = "#f7ecd2"        # champagne clair
_PLAQUE_NUIT = "#161310"

_SUPERSTAR = {
    "label": "Superstar du stade",
    "hint": ("Note géante, portrait, grille de six statistiques. Le drapeau "
             "et l'écusson sont des zones de TEXTE en attendant les calques "
             "d'image (3b) — la place et la taille, elles, sont celles de la "
             "spec."),
    "finish": "foil",
    "texture": {"paper": "bristol", "tint": "#ffffff", "over": "foil_or",
                "over_opacity": 0.34, "wear": 0.0, "varnish": 0.35,
                "seed": 11},
    "fonts_note": [
        {"spec": "Oswald", "police": "BebasNeue",
         "pourquoi": "absente du lab — le condensé capitales le plus proche"},
        {"spec": "Barlow Condensed", "police": "Staatliches",
         "pourquoi": "absente du lab — condensé de libellés, capitales"},
        {"spec": "Archivo (chiffres tabulaires)", "police": "ArchivoBlack",
         "pourquoi": "la seule Archivo du lab (graisse Black)"},
    ],
    "slots": [
        # note géante 8,12 (12 x 9)
        _slot("note", "Note générale", (8, 12, 12, 9), font="ArchivoBlack",
              size_pt=24, min_pt=10, read_pt=8, color=_INK_OR, align="center",
              valign="middle", wrap=False, plate_color=_PLAQUE_NUIT,
              plate_alpha=0.88, plate_radius=1.2, text="87"),
        # position dessous
        _slot("poste", "Poste", (8, 21.5, 12, 5), font="Staatliches",
              size_pt=10, min_pt=6, read_pt=6, color=_INK_OR, align="center",
              valign="middle", caps="upper", track=4, wrap=False, text="Mil"),
        # drapeau / écusson en colonne gauche
        _slot("drapeau", "Drapeau", (8, 27.5, 12, 5), font="Staatliches",
              size_pt=9, min_pt=5, read_pt=6, color=_INK_OR, align="center",
              valign="middle", caps="upper", track=3, wrap=False, text="Fra"),
        _slot("ecusson", "Écusson", (8, 33.5, 12, 5), font="Staatliches",
              size_pt=9, min_pt=5, read_pt=6, color=_INK_OR, align="center",
              valign="middle", caps="upper", track=3, wrap=False, text="Dps"),
        # bandeau nom 6,47 (51 x 7)
        _slot("nom", "Nom du joueur", (6, 47, 51, 7), font="BebasNeue",
              size_pt=17, min_pt=8, read_pt=12, color=_INK_OR, align="center",
              valign="middle", caps="upper", track=2, wrap=False,
              plate_color=_PLAQUE_NUIT, plate_alpha=0.92, plate_radius=1.0,
              text="A. Nonyme"),
        # grille 6 stats 2 x 3 : 8,56 (47 x 21) -> six cases de 23,5 x 7
        _slot("vit", "VIT", (8, 56, 23.5, 7), font="BebasNeue", size_pt=12,
              min_pt=6, read_pt=8, color=_INK_OR, align="center",
              valign="middle", track=1, wrap=False,
              plate_color=_PLAQUE_NUIT, plate_alpha=0.5, plate_radius=0.8,
              text="89 VIT"),
        _slot("tir", "TIR", (8, 63, 23.5, 7), font="BebasNeue", size_pt=12,
              min_pt=6, read_pt=8, color=_INK_OR, align="center",
              valign="middle", track=1, wrap=False,
              plate_color=_PLAQUE_NUIT, plate_alpha=0.5, plate_radius=0.8,
              text="84 TIR"),
        _slot("pas", "PAS", (8, 70, 23.5, 7), font="BebasNeue", size_pt=12,
              min_pt=6, read_pt=8, color=_INK_OR, align="center",
              valign="middle", track=1, wrap=False,
              plate_color=_PLAQUE_NUIT, plate_alpha=0.5, plate_radius=0.8,
              text="78 PAS"),
        _slot("drb", "DRB", (31.5, 56, 23.5, 7), font="BebasNeue", size_pt=12,
              min_pt=6, read_pt=8, color=_INK_OR, align="center",
              valign="middle", track=1, wrap=False,
              plate_color=_PLAQUE_NUIT, plate_alpha=0.5, plate_radius=0.8,
              text="88 DRB"),
        _slot("def", "DEF", (31.5, 63, 23.5, 7), font="BebasNeue", size_pt=12,
              min_pt=6, read_pt=8, color=_INK_OR, align="center",
              valign="middle", track=1, wrap=False,
              plate_color=_PLAQUE_NUIT, plate_alpha=0.5, plate_radius=0.8,
              text="42 DEF"),
        _slot("phy", "PHY", (31.5, 70, 23.5, 7), font="BebasNeue", size_pt=12,
              min_pt=6, read_pt=8, color=_INK_OR, align="center",
              valign="middle", track=1, wrap=False,
              plate_color=_PLAQUE_NUIT, plate_alpha=0.5, plate_radius=0.8,
              text="66 PHY"),
        # pied d'icônes
        _slot("pied", "Pied de carte", (6, 78, 51, 4.4), font="Staatliches",
              size_pt=8, min_pt=5, read_pt=4, color=_INK_OR, align="center",
              valign="middle", caps="upper", track=6, wrap=False,
              text="Saison 2025-26 / 34 matchs / 12 buts"),
    ],
    "elements": [
        _element("stat7", "7e statistique",
                 "La grille §6.2 en porte six : la septième prend la colonne "
                 "de gauche, sous l'écusson.",
                 [_slot("stat7", "7e statistique", (8, 39.5, 12, 6.5),
                        font="BebasNeue", size_pt=11, min_pt=6, read_pt=8,
                        color=_INK_OR, align="center", valign="middle",
                        wrap=False, plate_color=_PLAQUE_NUIT, plate_alpha=0.5,
                        plate_radius=0.8, text="81 REF")]),
    ],
}

_INK_DUEL = "#1d232b"
_PAPIER_DUEL = "#f7f4ee"
_ZEBRE = ("#dde3ea", "#f0f3f7")


def _duel_ligne(i: int, libelle: str, valeur: str) -> list:
    """Une ligne du tableau zébré : libellé à gauche, valeur TABULAIRE à
    droite (spec). Le zébrage est fait de PLAQUES de slot — c'est exactement
    ce que la T1 a ajouté à P3, et cela suit la ligne si on la déplace."""
    y = 51.0 + 4.8 * i
    teinte = _ZEBRE[i % 2]
    return [
        _slot(f"lib{i + 1}", f"Libellé {i + 1}", (4, y, 36, 4.8), font="Inter",
              size_pt=8, min_pt=5, read_pt=6, color=_INK_DUEL, align="left",
              valign="middle", wrap=False, plate_color=teinte,
              plate_alpha=0.95, text=libelle),
        _slot(f"val{i + 1}", f"Valeur {i + 1}", (40, y, 19, 4.8),
              font="JetBrainsMono", size_pt=8, min_pt=5, read_pt=6,
              color=_INK_DUEL, align="right", valign="middle", wrap=False,
              plate_color=teinte, plate_alpha=0.95, text=valeur),
    ]


_DUEL = {
    "label": "Duel de chiffres",
    "hint": ("Bandeau titre RECTANGLE (pas d'ellipse), tableau zébré de "
             "cinq lignes — une sixième s'ajoute depuis les éléments — et "
             "pied de référence. Les valeurs sont en chasse fixe : les "
             "colonnes s'alignent par la POLICE, pas par des espaces."),
    "finish": "mat",
    "texture": {"paper": "offset", "tint": _PAPIER_DUEL, "over": "grain",
                "over_opacity": 0.42, "wear": 0.0, "varnish": 0.0,
                "seed": 12},
    "fonts_note": [
        {"spec": "Titan One", "police": "Bungee",
         "pourquoi": "absente du lab — le titrage gras le plus proche"},
        {"spec": "Nunito", "police": "Inter",
         "pourquoi": "absente du lab — sans-serif de labeur"},
        {"spec": "Rubik (valeurs tabulaires)", "police": "JetBrainsMono",
         "pourquoi": "la seule chasse FIXE du lab : les colonnes s'alignent"},
    ],
    "slots": [
        # bandeau titre 4,4 (55 x 8, rectangle, PAS d'ellipse)
        _slot("titre", "Titre", (4, 4, 55, 8), font="Bungee", size_pt=14,
              min_pt=7, read_pt=12, color=_PAPIER_DUEL, align="center",
              valign="middle", caps="upper", wrap=False,
              plate_color=_INK_DUEL, plate_alpha=1.0, plate_radius=0.0,
              text="Voitures de course"),
        # tableau 5-7 lignes zébrées 4,51 (55 x 29)
        *_duel_ligne(0, "Vitesse de pointe", "320 km/h"),
        *_duel_ligne(1, "Puissance", "770 ch"),
        *_duel_ligne(2, "Couple", "800 Nm"),
        *_duel_ligne(3, "0 à 100 km/h", "2,9 s"),
        *_duel_ligne(4, "Masse", "1430 kg"),
        # pied référence « 12/32 »
        _slot("ref", "Référence", (4, 80.4, 55, 3.8), font="JetBrainsMono",
              size_pt=6, min_pt=4, read_pt=4, color=_INK_DUEL, align="right",
              valign="middle", wrap=False, text="12 / 32"),
    ],
    "elements": [
        _element("ligne", "Ligne de tableau",
                 "Le tableau §6.2 tient de cinq à sept lignes ; la sixième "
                 "se pose sous la cinquième, zébrage compris.",
                 _duel_ligne(5, "Longueur", "4,52 m")),
    ],
}

_INK_CREATURE = "#f3e8d2"
_PARCHEMIN = "#f2e7cf"
_ENCRE_PARCHEMIN = "#2f2418"


def _creature_attaque(n: int, y: float, cout: str, nom: str,
                      degats: str) -> list:
    return [
        _slot(f"att{n}cout", f"Coût attaque {n}", (6, y, 9, 11),
              font="IBMPlexSans", size_pt=8, min_pt=5, read_pt=6,
              color=_ENCRE_PARCHEMIN, align="center", valign="middle",
              wrap=False, plate_color=_PARCHEMIN, plate_alpha=0.94,
              plate_radius=1.5, text=cout),
        _slot(f"att{n}nom", f"Attaque {n}", (16, y, 30, 11),
              font="IBMPlexSans", size_pt=9, min_pt=5, read_pt=6,
              color=_ENCRE_PARCHEMIN, align="left", valign="middle",
              plate_color=_PARCHEMIN, plate_alpha=0.94, plate_radius=1.5,
              text=nom),
        _slot(f"att{n}deg", f"Dégâts {n}", (47, y, 10, 11),
              font="SpaceGrotesk", size_pt=13, min_pt=7, read_pt=8,
              color=_ENCRE_PARCHEMIN, align="right", valign="middle",
              bold=True, wrap=False, plate_color=_PARCHEMIN, plate_alpha=0.94,
              plate_radius=1.5, text=degats),
    ]


_CREATURE = {
    "label": "Créature à évolutions",
    "hint": ("Cartouche d'évolution, nom, points de vie, une attaque posée "
             "et une seconde à un clic. Le coût est écrit en toutes lettres "
             "en attendant les icônes (3b)."),
    "finish": "holo",
    "texture": {"paper": "bristol", "tint": "#ffffff", "over": "holo",
                "over_opacity": 0.30, "wear": 0.0, "varnish": 0.25,
                "seed": 13},
    "fonts_note": [
        {"spec": "Lato", "police": "IBMPlexSans",
         "pourquoi": "absente du lab — sans-serif de labeur"},
        {"spec": "PT Sans", "police": "IBMPlexSans",
         "pourquoi": "absente du lab — même repli que Lato"},
        {"spec": "Jost", "police": "SpaceGrotesk",
         "pourquoi": "absente du lab — géométrique, même usage de titrage"},
    ],
    "slots": [
        # cartouche d'évolution 4,4 · nom 19,4 · PV + élément 44,4
        _slot("evolution", "Évolution", (4, 4, 15, 5), font="IBMPlexSans",
              size_pt=7, min_pt=5, read_pt=6, color=_INK_CREATURE,
              align="left", valign="middle", caps="upper", track=3,
              wrap=False, text="Niv. 2"),
        _slot("nom", "Nom", (19, 4, 25, 5), font="SpaceGrotesk", size_pt=12,
              min_pt=6, read_pt=12, color=_INK_CREATURE, align="left",
              valign="middle", bold=True, wrap=False, text="Céphalopode"),
        _slot("pv", "Points de vie", (44.4, 4, 14.6, 5), font="SpaceGrotesk",
              size_pt=13, min_pt=7, read_pt=8, color=_INK_CREATURE,
              align="right", valign="middle", bold=True, wrap=False,
              text="PV 90"),
        # 1-2 attaques 6,51 (51 x 22)
        *_creature_attaque(1, 51, "Eau 2", "Marée d'encre", "60"),
        # pied faiblesse / résistance / retraite
        _slot("faiblesse", "Faiblesse", (6, 74, 17, 5), font="IBMPlexSans",
              size_pt=6.5, min_pt=4.5, read_pt=6, color=_INK_CREATURE,
              align="center", valign="middle", wrap=False, text="Faibl. x2"),
        _slot("resistance", "Résistance", (23, 74, 17, 5), font="IBMPlexSans",
              size_pt=6.5, min_pt=4.5, read_pt=6, color=_INK_CREATURE,
              align="center", valign="middle", wrap=False, text="Rés. -20"),
        _slot("retraite", "Retraite", (40, 74, 17, 5), font="IBMPlexSans",
              size_pt=6.5, min_pt=4.5, read_pt=6, color=_INK_CREATURE,
              align="center", valign="middle", wrap=False, text="Retraite 1"),
        # ligne légale + rareté (cercle / losange / étoile)
        _slot("legal", "Ligne légale", (6, 80, 40, 3.2), font="IBMPlexSans",
              size_pt=4.5, min_pt=3.5, read_pt=4, color=_INK_CREATURE,
              align="left", valign="middle", wrap=False,
              text="ill. A. Nonyme / 017 / 060"),
        _slot("rarete", "Rareté", (50, 80, 7, 3.2), font="IBMPlexSans",
              size_pt=6, min_pt=4, read_pt=4, color=_INK_CREATURE,
              align="center", valign="middle", wrap=False, text="R"),
    ],
    "elements": [
        _element("attaque2", "2e attaque",
                 "La zone §6.2 est dimensionnée pour DEUX attaques : la "
                 "seconde se pose sous la première, au millimètre.",
                 _creature_attaque(2, 62, "Air 1", "Souffle des fonds", "30")),
    ],
}

_INK_ARCANE = "#e9d7a8"
_PARCHEMIN_ARCANE = "#e8dcc0"
_ENCRE_ARCANE = "#241c10"

_ARCANE = {
    "label": "Arcane mystique",
    "hint": ("Bandeau de titre avec pastille de coût, boîte de règles sur "
             "parchemin (romain droit, ambiance en italique) et cartouche "
             "force/endurance. Une seconde pastille de coût s'ajoute depuis "
             "les éléments."),
    "finish": "satin",
    "texture": {"paper": "parchemin", "tint": "#f6efe0", "over": "grain",
                "over_opacity": 0.5, "wear": 0.08, "varnish": 0.12,
                "seed": 14},
    "fonts_note": [
        {"spec": "Cinzel", "police": "Cinzel",
         "pourquoi": "présente au lab — aucune substitution"},
        {"spec": "Alegreya SC", "police": "Cinzel",
         "pourquoi": "absente du lab — capitales romaines, même emploi"},
        {"spec": "EB Garamond", "police": "IBMPlexSans",
         "pourquoi": ("le lab n'a AUCUNE romaine de labeur : le corps de "
                      "règles passe en sans-serif, et c'est dit ici plutôt "
                      "que subi")},
    ],
    "slots": [
        # bandeau titre 4,3.5 (nom + coût en pastilles ⌀4)
        _slot("nom", "Nom", (4, 3.5, 41, 6), font="Cinzel", size_pt=12,
              min_pt=6, read_pt=12, color=_INK_ARCANE, align="left",
              valign="middle", track=2, wrap=False, text="Roue des marées"),
        _slot("cout", "Coût", (55, 4.5, 4, 4), font="Cinzel", size_pt=9,
              min_pt=5, read_pt=8, color=_ENCRE_ARCANE, align="center",
              valign="middle", wrap=False, plate_color=_INK_ARCANE,
              plate_alpha=1.0, plate_radius=2.0, text="3"),
        # ligne de type 4,49
        _slot("typeline", "Ligne de type", (4, 49, 55, 4.5), font="Cinzel",
              size_pt=8, min_pt=5, read_pt=6, color=_INK_ARCANE,
              align="center", valign="middle", caps="upper", track=6,
              wrap=False, text="Enchantement - Aura"),
        # boîte parchemin 4,54.5 (55 x 24) : règles romain + ambiance italique
        _slot("regles", "Encadré de règles", (4, 54.5, 55, 16),
              font="IBMPlexSans", size_pt=8, min_pt=4.5, read_pt=6,
              color=_ENCRE_ARCANE, align="justify", valign="top",
              leading=1.22, hyphen=True, plate_color=_PARCHEMIN_ARCANE,
              plate_alpha=0.95, plate_radius=1.5,
              text=("Quand cette carte entre en jeu, révélez les trois "
                    "cartes du dessus de votre pioche : gardez-en une, "
                    "renvoyez les autres au fond. Tant qu'elle reste en jeu, "
                    "vos sorts d'eau coûtent 1 de moins.")),
        _slot("ambiance", "Texte d'ambiance", (4, 71, 43, 7.5),
              font="IBMPlexSans", size_pt=7, min_pt=4.5, read_pt=6,
              color=_ENCRE_ARCANE, align="center", valign="middle",
              italic=True, plate_color=_PARCHEMIN_ARCANE, plate_alpha=0.95,
              plate_radius=1.5,
              text="« L'encre monte, la mémoire descend. »"),
        # cartouche force/endurance 47,78
        _slot("fe", "Force / endurance", (47, 78, 12, 6), font="Cinzel",
              size_pt=11, min_pt=6, read_pt=8, color=_ENCRE_ARCANE,
              align="center", valign="middle", wrap=False,
              plate_color=_PARCHEMIN_ARCANE, plate_alpha=0.95,
              plate_radius=1.2, text="4 / 5"),
    ],
    "elements": [
        _element("cout2", "Pastille de coût",
                 "Le coût §6.2 est une SUITE de pastilles ⌀4 : chacune est "
                 "un slot, posé à gauche de la précédente.",
                 [_slot("cout2", "Coût (2)", (50.5, 4.5, 4, 4), font="Cinzel",
                        size_pt=9, min_pt=5, read_pt=8, color=_ENCRE_ARCANE,
                        align="center", valign="middle", wrap=False,
                        plate_color=_INK_ARCANE, plate_alpha=1.0,
                        plate_radius=2.0, text="2")]),
    ],
}

_INK_MONSTRE = "#f2ead6"
_BOITE_MONSTRE = "#e6e0d2"
_ENCRE_MONSTRE = "#141414"

_MONSTRE = {
    "label": "Monstre de duel",
    "hint": ("Nom en capitales, attribut en pastille ⌀7 à droite, rang "
             "aligné à droite, illustration CARRÉE (le verrou de proportions "
             "du cadre est armé), boîte d'effet et ligne ATK/DEF."),
    "finish": "satin",
    "texture": {"paper": "bristol", "tint": "#ffffff", "over": "irise",
                "over_opacity": 0.22, "wear": 0.0, "varnish": 0.30,
                "seed": 15},
    "fonts_note": [
        {"spec": "Spectral SC", "police": "Cinzel",
         "pourquoi": "absente du lab — capitales romaines, même emploi"},
        {"spec": "Roboto Condensed", "police": "IBMPlexSans",
         "pourquoi": "absente du lab — sans-serif de labeur"},
        {"spec": "Saira Condensed", "police": "BebasNeue",
         "pourquoi": "absente du lab — condensé capitales pour les chiffres"},
    ],
    "slots": [
        # nom capitales 4.5,4.5 · attribut ⌀7 à droite
        _slot("nom", "Nom", (4.5, 4.5, 46, 6), font="Cinzel", size_pt=12,
              min_pt=6, read_pt=12, color=_INK_MONSTRE, align="left",
              valign="middle", caps="upper", track=2, wrap=False,
              text="Gardien des abysses"),
        _slot("attribut", "Attribut", (51.5, 4, 7, 7), font="Cinzel",
              size_pt=7, min_pt=4.5, read_pt=6, color=_ENCRE_MONSTRE,
              align="center", valign="middle", caps="upper", wrap=False,
              plate_color=_INK_MONSTRE, plate_alpha=1.0, plate_radius=3.5,
              text="Eau"),
        # étoiles ALIGNÉES À DROITE 8,12.5
        _slot("etoiles", "Rang", (8, 12.5, 47, 5), font="BebasNeue",
              size_pt=10, min_pt=6, read_pt=8, color=_INK_MONSTRE,
              align="right", valign="middle", track=3, wrap=False,
              text="Niveau 7"),
        # type [CROCHETS]
        _slot("typeline", "Type", (8, 66, 47, 3.8), font="IBMPlexSans",
              size_pt=7, min_pt=4.5, read_pt=6, color=_ENCRE_MONSTRE,
              align="left", valign="middle", wrap=False,
              plate_color=_BOITE_MONSTRE, plate_alpha=1.0, plate_radius=0.6,
              text="[Bête-Machine / Effet]"),
        # boîte d'effet
        _slot("effet", "Boîte d'effet", (8, 70, 47, 10.8), font="IBMPlexSans",
              size_pt=7, min_pt=4.5, read_pt=6, color=_ENCRE_MONSTRE,
              align="justify", valign="top", leading=1.18, hyphen=True,
              plate_color=_BOITE_MONSTRE, plate_alpha=1.0, plate_radius=0.6,
              text=("Une fois par tour, vous pouvez défausser une carte pour "
                    "renvoyer un monstre adverse dans la main de son "
                    "propriétaire.")),
        # ligne ATK/DEF à droite 6,81.5
        _slot("atk", "Attaque", (6, 81.5, 25, 3.4), font="BebasNeue",
              size_pt=9, min_pt=5, read_pt=8, color=_ENCRE_MONSTRE,
              align="right", valign="middle", wrap=False,
              plate_color=_BOITE_MONSTRE, plate_alpha=1.0, plate_radius=0.6,
              text="ATK 2500"),
        _slot("dfn", "Défense", (33, 81.5, 24, 3.4), font="BebasNeue",
              size_pt=9, min_pt=5, read_pt=8, color=_ENCRE_MONSTRE,
              align="right", valign="middle", wrap=False,
              plate_color=_BOITE_MONSTRE, plate_alpha=1.0, plate_radius=0.6,
              text="DEF 2100"),
    ],
    "elements": [
        _element("materiaux", "Cartouche de matériaux",
                 "Une bande posée SUR l'illustration, au-dessus de la ligne "
                 "de type : c'est là qu'il reste de la place.",
                 [_slot("materiaux", "Matériaux", (8, 58, 47, 5),
                        font="IBMPlexSans", size_pt=6.5, min_pt=4.5,
                        read_pt=6, color=_ENCRE_MONSTRE, align="left",
                        valign="middle", wrap=False,
                        plate_color=_BOITE_MONSTRE, plate_alpha=0.92,
                        plate_radius=0.6,
                        text="Matériaux : 2 monstres de niveau 4")]),
    ],
}

_INK_LEGENDE = "#f4f1ea"
_NUIT_LEGENDE = "#101418"
_TABLE_LEGENDE = "#f2efe6"
_ENCRE_LEGENDE = "#181c22"


def _legende_saison(sid: str, label: str, y: float, texte: str,
                    gras: bool = False) -> dict:
    """Une ligne du tableau saisonnier, AU VERSO. La chasse fixe fait les
    colonnes : un tableau aligné par des espaces dans une police
    proportionnelle ne l'est que sur l'écran de celui qui l'a tapé."""
    return _slot(sid, label, (6, y, 51, 4.5), font="JetBrainsMono",
                 size_pt=6.5, min_pt=4.5, read_pt=6, color=_ENCRE_LEGENDE,
                 align="left", valign="middle", bold=gras, wrap=False,
                 side="back", plate_color=_TABLE_LEGENDE, plate_alpha=0.96,
                 plate_radius=0.6, text=texte)


_LEGENDE = {
    "label": "Légende du terrain",
    "hint": ("Photo pleine page au recto, bandeau de nom à fond perdu, et le "
             "SEUL verso propre de la première fournée : un tableau de "
             "statistiques saisonnières (chasse fixe) plus un bloc "
             "anecdote."),
    "finish": "holo",
    "texture": {"paper": "bristol", "tint": "#ffffff", "over": "foil_argent",
                "over_opacity": 0.30, "wear": 0.0, "varnish": 0.40,
                "seed": 16},
    "fonts_note": [
        {"spec": "Anton", "police": "Anton",
         "pourquoi": "présente au lab — aucune substitution"},
        {"spec": "Archivo Black", "police": "ArchivoBlack",
         "pourquoi": "présente au lab — aucune substitution"},
        {"spec": "Barlow", "police": "Inter",
         "pourquoi": "absente du lab — sans-serif de labeur"},
        {"spec": "Barlow (tableau saisonnier)", "police": "JetBrainsMono",
         "pourquoi": ("les colonnes du tableau s'alignent par la CHASSE "
                      "FIXE ; une proportionnelle les décalerait")},
    ],
    "slots": [
        # logo de collection 4,4 · № en coin
        _slot("logo", "Logo de collection", (4, 4, 14, 5),
              font="ArchivoBlack", size_pt=7, min_pt=4.5, read_pt=6,
              color=_INK_LEGENDE, align="center", valign="middle",
              caps="upper", track=2, wrap=False, plate_color=_NUIT_LEGENDE,
              plate_alpha=0.55, plate_radius=0.8, text="Série 2026"),
        _slot("numero", "Numéro", (50, 4, 9, 4), font="ArchivoBlack",
              size_pt=7, min_pt=4.5, read_pt=4, color=_INK_LEGENDE,
              align="center", valign="middle", wrap=False,
              plate_color=_NUIT_LEGENDE, plate_alpha=0.55, plate_radius=0.8,
              text="No 17"),
        # bandeau nom 0,74 (63 x 10, aplat) : il TOUCHE le trait de coupe —
        # c'est un aplat à fond perdu, et le texte reste centré loin du bord.
        _slot("nom", "Bandeau de nom", (0, 74, 63, 10), font="Anton",
              size_pt=17, min_pt=8, read_pt=12, color=_INK_LEGENDE,
              align="center", valign="middle", caps="upper", track=1,
              wrap=False, plate_color=_NUIT_LEGENDE, plate_alpha=0.92,
              text="A. Nonyme"),
        # ── VERSO : tableau de stats saisonnières + bloc anecdote ──────────
        _slot("titredos", "Titre du verso", (6, 8, 51, 6), font="Anton",
              size_pt=12, min_pt=6, read_pt=12, color=_ENCRE_LEGENDE,
              align="center", valign="middle", caps="upper", track=2,
              wrap=False, side="back", plate_color=_TABLE_LEGENDE,
              plate_alpha=0.96, plate_radius=0.8,
              text="Statistiques par saison"),
        _legende_saison("entete", "En-tête du tableau", 16,
                        "Saison    MJ  Buts  Passes"),
        _legende_saison("s1", "Saison 1", 21, "2022-23   34    12       7"),
        _legende_saison("s2", "Saison 2", 26, "2023-24   31    15       9"),
        _legende_saison("s3", "Saison 3", 31, "2024-25   36    19      11"),
        _legende_saison("total", "Total", 41,
                        "TOTAL    101    46      27", gras=True),
        _slot("anecdote", "Anecdote", (6, 50, 51, 24), font="Inter",
              size_pt=7.5, min_pt=5, read_pt=6, color=_ENCRE_LEGENDE,
              align="justify", valign="top", leading=1.24, hyphen=True,
              side="back", plate_color=_TABLE_LEGENDE, plate_alpha=0.96,
              plate_radius=0.8,
              text=("Formé au club à quatorze ans, il n'a jamais porté "
                    "d'autre maillot. La saison 2024-25 reste la meilleure "
                    "de sa carrière : dix-neuf buts, dont celui de la "
                    "finale, marqué à la dernière minute.")),
    ],
    "elements": [
        _element("saison", "Ligne de saison",
                 "Une saison de plus au tableau du verso, entre la dernière "
                 "ligne et le TOTAL.",
                 [_legende_saison("s4", "Saison 4", 36,
                                  "2025-26   28    11       6")]),
    ],
}

_INK_GRAVEE = "#8f2d1e"        # vermillon (spec : l'encre, pas le cadre)
_IVOIRE = "#f4ead6"
_CARTOUCHE_GRAVEE = "#ece0c4"

_GRAVEE = {
    "label": "Arcane gravée",
    "hint": ("Double filet, cartouche de chiffres romains, gravure au trait "
             "sur ivoire et cartouche de nom en capitales espacées. La "
             "rareté du cadre y donne la couleur de l'ENCRE (vermillon, "
             "bleu, ocre, vert)."),
    "finish": "mat",
    "texture": {"paper": "velin", "tint": _IVOIRE, "over": "grain",
                "over_opacity": 0.55, "wear": 0.12, "varnish": 0.0,
                "seed": 17},
    "fonts_note": [
        {"spec": "IM Fell English", "police": "Cinzel",
         "pourquoi": "absente du lab — romaine de titrage, même époque"},
        {"spec": "Cormorant SC", "police": "Cinzel",
         "pourquoi": "absente du lab — capitales romaines, même emploi"},
    ],
    "slots": [
        # cartouche Chiffres ROMAINS 4,4 (55 x 8)
        _slot("romain", "Chiffre romain", (4, 4, 55, 8), font="Cinzel",
              size_pt=12, min_pt=6, read_pt=6, color=_INK_GRAVEE,
              align="center", valign="middle", caps="upper", track=12,
              wrap=False, plate_color=_CARTOUCHE_GRAVEE, plate_alpha=1.0,
              plate_radius=0.0, text="XVII"),
        # cartouche nom 4,75 (55 x 9, capitales espacées)
        _slot("nom", "Nom", (4, 75, 55, 9), font="Cinzel", size_pt=13,
              min_pt=6.5, read_pt=12, color=_INK_GRAVEE, align="center",
              valign="middle", caps="upper", track=10, wrap=False,
              plate_color=_CARTOUCHE_GRAVEE, plate_alpha=1.0,
              plate_radius=0.0, text="La Gardienne"),
    ],
    "elements": [
        _element("citation", "Cartouche de citation",
                 "Un bandeau posé sur le bas de la gravure, dans la zone de "
                 "l'illustration — aucun slot ne s'y trouve.",
                 [_slot("citation", "Citation", (4, 64, 55, 8), font="Cinzel",
                        size_pt=8, min_pt=5, read_pt=6, color=_INK_GRAVEE,
                        align="center", valign="middle", italic=True,
                        track=2, wrap=False, plate_color=_CARTOUCHE_GRAVEE,
                        plate_alpha=0.94, plate_radius=0.0,
                        text="« Ce qui monte finit par redescendre. »")]),
    ],
}

# L'ordre est celui de la spec §6.2 (« Première fournée »).
_DEFINITIONS = {
    "superstar": _SUPERSTAR,
    "duel": _DUEL,
    "creature": _CREATURE,
    "arcane": _ARCANE,
    "monstre": _MONSTRE,
    "legende": _LEGENDE,
    "gravee": _GRAVEE,
}


# ════════════════════════════════════════════════════════════════════════════
# 3. LA PALETTE — une LECTURE, jamais une quatrième table de couleurs
# ════════════════════════════════════════════════════════════════════════════

def _dominante(valeurs: list):
    """La valeur la plus fréquente ; à égalité, la PREMIÈRE apparue (départage
    stable — sans lui, deux exécutions pourraient rendre deux palettes)."""
    compte: dict = {}
    for v in valeurs:
        compte[v] = compte.get(v, 0) + 1
    meilleur, n = None, 0
    for v in valeurs:
        if compte[v] > n:
            meilleur, n = v, compte[v]
    return meilleur


def palette_of(m: dict) -> dict:
    """`{ink, plate, paper}` relus dans le modèle lui-même.

    Écrite à la main, une palette serait DÉCORATIVE : elle mentirait dès la
    première retouche d'encre et rien ne le dirait. Relue, elle ne peut pas.
    """
    slots = ((m or {}).get("type") or {}).get("slots") or []
    slots = [s for s in slots if isinstance(s, dict)]
    encres = [s.get("color") for s in slots if s.get("color")]
    plaques = [s.get("plate_color") for s in slots if s.get("plate_color")]
    tint = ((m or {}).get("texture") or {}).get("tint")
    return {
        "ink": _dominante(encres) or type_mod.SLOT_DEFAULTS["color"],
        "plate": _dominante(plaques),
        "paper": str(tint or "#ffffff"),
    }


def _usine(mid: str, d: dict) -> dict:
    """Un modèle d'usine COMPLET : l'habillage pris à la FONCTION de P2, la
    palette relue, les clés du contrat §6.1 au grand complet."""
    m = {
        "id": mid,
        "label": d["label"],
        "hint": d["hint"],
        # LES ZONES §6.2 SONT CELLES DU POKER — le modèle le déclare.
        "format": "poker_eu",
        "frame": archetype_frame(mid),
        "type": {"preset": mid, "slots": copy.deepcopy(d["slots"])},
        "finish": d["finish"],
        "texture": copy.deepcopy(d["texture"]),
        "elements": copy.deepcopy(d["elements"]),
        "fonts_note": copy.deepcopy(d["fonts_note"]),
        "custom": False,
    }
    m["palette"] = palette_of(m)
    return m


MODELS: dict = {mid: _usine(mid, d) for mid, d in _DEFINITIONS.items()}


# ════════════════════════════════════════════════════════════════════════════
# 4. LES MODÈLES PERSO — `{DATA_ROOT}/cardforge_models/*.json`
# ════════════════════════════════════════════════════════════════════════════

def _texte(v, defaut: str, n: int = LABEL_MAX) -> str:
    s = str(v or "").strip()
    return (s or defaut)[:n]


def _normaliser_perso(raw: dict, fichier: Path) -> dict:
    """Un modèle perso, ramené au contrat §6.1. NE LÈVE PAS.

    L'IDENTIFIANT EST LE NOM DU FICHIER, jamais le champ `id` du contenu :
    sinon un fichier perso pourrait se déclarer « superstar » et masquer un
    modèle d'usine dans la galerie."""
    raw = raw if isinstance(raw, dict) else {}
    fmt = str(raw.get("format") or "").strip().lower()
    typ = raw.get("type") if isinstance(raw.get("type"), dict) else {}
    fin = str(raw.get("finish") or "").strip().lower()
    els = raw.get("elements") if isinstance(raw.get("elements"), list) else []
    notes = raw.get("fonts_note")
    m = {
        "id": fichier.stem,
        "label": _texte(raw.get("label"), fichier.stem),
        "hint": _texte(raw.get("hint"), "Modèle enregistré depuis un deck.",
                       240),
        "format": fmt if fmt in FORMATS else DEFAULT_FMT,
        "frame": raw["frame"] if isinstance(raw.get("frame"), dict) else {},
        "type": {"preset": _texte(typ.get("preset"), fichier.stem, 40),
                 "slots": type_mod.norm_slots(typ.get("slots"))},
        "finish": fin if fin in FINISHES else DEFAULT_FINISH,
        "texture": (raw["texture"] if isinstance(raw.get("texture"), dict)
                    else {}),
        "elements": [e for e in els if isinstance(e, dict)],
        "fonts_note": notes if isinstance(notes, list) else [],
        "custom": True,
        "fichier": fichier.name,
    }
    m["palette"] = palette_of(m)
    return m


def perso_list() -> list[dict]:
    """Les modèles perso, par nom de fichier. LECTURE TOLÉRANTE : un JSON
    abîmé est LISTÉ comme illisible, avec son nom de fichier — jamais un 500,
    et jamais une disparition silencieuse (un modèle qui manque sans un mot
    est pire qu'un modèle en erreur : on cherche du côté de l'écran)."""
    try:
        fichiers = sorted(p for p in models_root().glob("*.json")
                          if p.is_file())
    except OSError as e:
        logger.warning(f"cards/models: dossier illisible: {e}")
        return []
    out: list[dict] = []
    for p in fichiers[:PERSO_MAX]:
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("le fichier ne porte pas un objet JSON")
            out.append(_normaliser_perso(raw, p))
        except (OSError, ValueError) as e:
            out.append({"id": p.stem, "label": p.stem, "custom": True,
                        "illisible": True, "fichier": p.name,
                        "error": f"{type(e).__name__}: {e}"[:200]})
    return out


def catalogue() -> dict:
    """Usine + perso. Le CHEMIN du dossier n'est pas publié : il contient le
    nom de compte de l'utilisateur."""
    usine = [copy.deepcopy(m) for m in MODELS.values()]
    perso = perso_list()
    return {"models": usine + perso, "n": len(usine) + len(perso),
            "usine": len(usine), "perso": len(perso)}


def model(mid) -> dict:
    """LA porte d'entrée — une COPIE PROFONDE, comme `archetype_frame`.

    `MODELS` est une table de MODULE : rendre ses sous-dictionnaires
    laisserait le premier appelant qui écrit dedans contaminer tous les
    suivants, dans le même processus, sans rien casser tout de suite.

    `KeyError` nommée pour un modèle inconnu (l'appelant en fait un 404 en
    français) ; `ValueError` pour un modèle perso illisible."""
    key = str(mid or "").strip()
    if key in MODELS:
        return copy.deepcopy(MODELS[key])
    # Le motif borne AUSSI le chemin : ni séparateur, ni point, ni `..`.
    if not SLUG_RE.match(key):
        raise KeyError(key)
    p = models_root() / f"{key}.json"
    if not p.is_file():
        raise KeyError(key)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"{p.name} : {e}")
    if not isinstance(raw, dict):
        raise ValueError(f"{p.name} : le fichier ne porte pas un objet JSON")
    return _normaliser_perso(raw, p)


# ════════════════════════════════════════════════════════════════════════════
# 5. INSTANCIER — le modèle SEED un deck ORDINAIRE
# ════════════════════════════════════════════════════════════════════════════

def instancier(mid, name=None) -> dict:
    """Crée un deck et y écrit les sous-arbres du modèle. Le deck n'en garde
    AUCUNE trace ensuite : c'est une graine, pas un lien.

    L'écriture passe par `core.patch_deck` — le MÊME chemin que l'autosave de
    l'écran, remplacement de sous-arbre entier. Un second chemin d'écriture
    aurait fini par diverger de celui-là."""
    m = model(mid)
    doc = core.create_deck(core.clean_name(name or m["label"]))
    # COPIE PROFONDE, même si `model()` en a déjà rendu une : `patch_deck`
    # range l'objet reçu DANS le document qu'il rend (il ne le re-sérialise
    # pas pour l'appelant). Sans cette copie, l'appelant qui retouche le deck
    # rendu écrirait dans la table des modèles.
    slots = copy.deepcopy(m["type"]["slots"])
    body = {
        "format": {"fmt": m["format"]},
        "frame": copy.deepcopy(m["frame"]),
        # `seeded` VRAI : sans lui, `seedIfEmpty` (mod-type.js) reposerait le
        # gabarit « champion » par-dessus les slots de l'archétype si
        # l'utilisateur venait à tous les supprimer.
        "type": {"preset": m["type"].get("preset") or m["id"],
                 "slots": slots, "seeded": True,
                 "sel": (slots[0]["id"] if slots else "")},
        "texture": copy.deepcopy(m["texture"]),
        "gltf": {"finish": m["finish"]},
    }
    out = core.patch_deck(doc["id"], body)
    return out if out is not None else doc


# ════════════════════════════════════════════════════════════════════════════
# 6. ENREGISTRER COMME MODÈLE — les réglages, PAS les illustrations
# ════════════════════════════════════════════════════════════════════════════

def _slug(nom) -> str:
    """Un nom de fichier sûr : sans accent, sans séparateur, sans `..`."""
    s = unicodedata.normalize("NFKD", str(nom or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:SLUG_MAX].strip("-")
    return s or "modele"


def _slug_libre(base: str) -> str:
    """Un slug qui n'écrase NI un modèle perso existant NI un modèle d'usine.
    Écraser un voisin silencieusement, c'est perdre son travail."""
    root = models_root()
    for n in range(1, 100):
        cand = base if n == 1 else f"{base}-{n}"
        if cand not in MODELS and not (root / f"{cand}.json").exists():
            return cand
    return f"{base}-{uuid4().hex[:6]}"


def _texture_sans_import(raw) -> dict:
    """La matière du deck, moins le papier IMPORTÉ : ce fichier-là vit dans le
    dossier du deck, un modèle ne l'emporte pas (§6.4)."""
    t = dict(raw) if isinstance(raw, dict) else {}
    t.pop("custom", None)
    if str(t.get("paper") or "") in ("__import", "custom"):
        t["paper"] = PAPIER_DEFAUT
    return t


def modele_depuis_deck(doc: dict, nom=None) -> dict:
    """Le modèle que porte un deck : format, cadre, typo, matière, finition.

    PAS LES ILLUSTRATIONS (§6.4) : `doc.face` n'est pas sérialisé du tout
    (`src` et `default_art` y pointent vers des octets restés dans le deck) et
    le papier importé retombe sur la matière par défaut. Les TEXTES des slots,
    eux, RESTENT — un slot vide ne peint pas sa plaque (T1), un modèle aux
    textes purgés reviendrait donc sans ses cartouches."""
    doc = doc if isinstance(doc, dict) else {}
    fmt = ((doc.get("format") or {}).get("fmt") or "").strip().lower()
    typ = doc.get("type") if isinstance(doc.get("type"), dict) else {}
    gltf = doc.get("gltf") if isinstance(doc.get("gltf"), dict) else {}
    fin = str(gltf.get("finish") or "").strip().lower()
    slots = type_mod.norm_slots(typ.get("slots"))
    m = {
        "id": "",
        "label": _texte(nom, doc.get("name") or "Mon modèle"),
        "hint": _texte(f"Modèle enregistré depuis « {doc.get('name')} » "
                       f"le {datetime.now().strftime('%d/%m/%Y')}.", "", 240),
        "format": fmt if fmt in FORMATS else DEFAULT_FMT,
        "frame": (copy.deepcopy(doc["frame"])
                  if isinstance(doc.get("frame"), dict) else {}),
        "type": {"preset": _texte(typ.get("preset"), "perso", 40),
                 "slots": slots},
        "finish": fin if fin in FINISHES else DEFAULT_FINISH,
        "texture": _texture_sans_import(doc.get("texture")),
        # Un modèle perso n'a pas de palette d'éléments : il n'en a jamais
        # déclaré. La liste est VIDE plutôt qu'absente (le contrat §6.1 tient).
        "elements": [],
        # Les polices employées, DÉCLARÉES elles aussi — l'invariant « aucune
        # police sans note » vaut pour les modèles perso comme pour les
        # autres, même si aucune n'est ici un repli.
        "fonts_note": [{"spec": f, "police": f,
                        "pourquoi": "police choisie dans le deck d'origine"}
                       for f in sorted({s["font"] for s in slots})],
        "custom": True,
    }
    m["palette"] = palette_of(m)
    return m


def enregistrer(doc: dict, nom=None) -> dict:
    """Écrit le modèle perso et rend son entrée de catalogue."""
    m = modele_depuis_deck(doc, nom)
    slug = _slug_libre(_slug(nom or doc.get("name")))
    m["id"] = slug
    p = models_root() / f"{slug}.json"
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    tmp.replace(p)              # atomique, comme `core.write_deck`
    return _normaliser_perso(m, p)


# ════════════════════════════════════════════════════════════════════════════
# 7. ROUTES — montées AVANT le joker `/{did}` (cf. cards/__init__.py)
# ════════════════════════════════════════════════════════════════════════════

@router.get("/models")
async def get_models():
    """Les 7 modèles d'usine + les modèles perso. Un fichier perso illisible
    est LISTÉ (`illisible: true`), jamais une erreur de la route."""
    return await asyncio.to_thread(catalogue)


@router.post("/models")
async def post_model(body: dict | None = None):
    """« Enregistrer comme modèle » — corps `{did, name?}` (spec §6.4)."""
    body = body if isinstance(body, dict) else {}
    did = body.get("did")
    if not is_valid_did(did):
        raise HTTPException(400, "Identifiant de deck invalide")
    doc = await asyncio.to_thread(core.read_deck, did)
    if doc is None:
        raise HTTPException(404, "Deck introuvable : impossible d'en faire "
                                 "un modèle")
    try:
        m = await asyncio.to_thread(enregistrer, doc, body.get("name"))
    except OSError as e:
        logger.exception("cards/models: écriture du modèle impossible")
        raise HTTPException(500, f"Enregistrement du modèle impossible: {e}")
    return {"model": m}
