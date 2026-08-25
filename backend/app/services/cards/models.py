# -*- coding: utf-8 -*-
"""Card Forge — LES MODÈLES DE DECK (phase 3a, tâche 3 ; spec §6.1/§6.2/§6.4).

Ce fichier appartient à CORE, comme `core.py` : il n'est pas l'une des neuf
pièces (pas de sous-arbre à lui, pas de couche à dessiner, pas de `{did}` dans
ses chemins). Il sert deux routes, montées AVANT le joker `/{did}` :

    GET    /api/cards/models        les 7 modèles d'usine + les perso
    POST   /api/cards/models        « enregistrer comme modèle » (sans images)
    DELETE /api/cards/models/{id}   retire un modèle PERSO (l'usine : 403)

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
  4. **Le cadre part par une LISTE BLANCHE** (`_FRAME_CLES`), pas par une
     liste noire : §6.2ter a fait du verso personnalisé une image importée
     « sauvée dans les modèles », et une liste noire écrite avant elle
     n'aurait pas connu la clé du lendemain. Voir le pavé de `_FRAME_CLES`.
     La 3c-T4 a tranché ce que le modèle en emporte : les RÉGLAGES (`back`,
     `back_image`, `back_layers` sont ADMIS), jamais les OCTETS (leurs `src`
     sont purgés, et le modèle le DIT) — voir `_frame_sans_import`.
  5. **Un fichier perso qui porte le nom d'un modèle d'usine est LISTÉ ET
     SIGNALÉ**, sous un identifiant préfixé — pas silencieusement écrasé, pas
     silencieusement ignoré. Voir `_normaliser_perso`.
  6. **Un nom de modèle se RÉSERVE, il ne se cherche pas** (création
     exclusive) : entre `exists()` et l'écriture il y a une fenêtre, et un
     double-clic la traverse. Voir `_reserver`.
"""
from __future__ import annotations

import asyncio
import copy
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4          # ultime recours de nommage (cf. `enregistrer`)

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
# LE MOTIF DES IDENTIFIANTS PERSO — celui du nom de fichier, donc celui qui
# borne le chemin. Il accepte le tiret BAS bien que `_slug` n'en produise
# jamais : un fichier déposé à la main s'appelle `mon_modele.json` une fois sur
# deux. Ce que le motif refuse (séparateurs, points, majuscules, espaces) est
# refusé DES DEUX CÔTÉS — voir `_id_utilisable` : un fichier qui ne peut pas
# s'ouvrir ne doit pas se lister comme s'il s'ouvrait.
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")
ECHO_MAX = 40              # ce qu'un message d'erreur RECOPIE du client
# ── LA PROVENANCE D'UN DECK, DITE À SA NAISSANCE (3b-T3, ronde) ─────────────
# `doc.type.preset` portait DEUX vocabulaires dans un seul espace de noms : les
# clés des quatre gabarits locaux de P3 (champion / sort / arcane / minimal,
# écrites par `applyPreset`) et les identifiants de MODÈLES (écrits ici). Ils se
# rencontraient déjà : « arcane » est un gabarit ET un archétype d'usine, si
# bien qu'un deck posé sur le gabarit se voyait offrir les éléments d'un modèle
# dont il n'était pas né. Et rien n'empêchait un modèle perso nommé
# « Champion » de reproduire le cas sur les trois autres (`_slug` réserve les
# ids d'usine, pas les clés de gabarits).
# Le préfixe ferme les DEUX SENS PAR CONSTRUCTION : aucune clé de gabarit ni
# aucun slug (`[^a-z0-9]+` -> `-`) ne peut contenir « : », donc un gabarit ne
# peut plus désigner un modèle, et un modèle ne peut plus se faire passer pour
# un gabarit. Ce n'est pas une clé de plus dans le document : c'est la même
# clé, qui dit désormais D'OÙ elle vient.
# CE QUE ÇA NE RATTRAPE PAS, et c'est dit plutôt que caché : un deck instancié
# AVANT ce changement porte encore l'id nu, indiscernable d'une clé de gabarit.
# L'écran ne devine pas — il ne propose rien. La palette d'éléments étant née
# avec cette ronde, aucun comportement existant ne se perd ; recréer le jeu
# depuis la galerie rétablit la provenance.
PRESET_MODELE = "modele:"
# La matière de repli quand un modèle perso portait un papier IMPORTÉ : le
# défaut de l'écran (`DEF.paper`, mod-texture.js). Le fichier importé, lui,
# reste dans le deck d'origine — un modèle ne l'emporte pas.
PAPIER_DEFAUT = "velin"

# ── LA LISTE BLANCHE DU CADRE ───────────────────────────────────────────────
# Le vocabulaire de `doc.frame`, DÉRIVÉ de l'habillage d'un archétype plutôt
# que retapé : `test_cards_frame.py` exige que les sept habillages portent
# EXACTEMENT les clés du bloc DEFAULTS de mod-frame.js, moins `art_window`
# (que le painter publie). Ce jeu suit donc P2 tout seul — une clé de cadre
# ajoutée un jour au bloc JS devra passer par les habillages, et arrivera ici
# sans que personne n'y pense.
#
# POURQUOI UNE LISTE BLANCHE ET NON UNE LISTE NOIRE : la §6.2ter a posé un
# VERSO PERSONNALISÉ dans le cadre — « une image importée » qui doit être
# « SAUVÉE dans les modèles de deck ». Une liste noire écrite avant elle ne
# l'aurait pas connue et aurait laissé partir une référence vers des octets
# restés dans le deck d'origine. La liste blanche refuse par défaut : la 3c a
# donc DÛ décider ce qu'un modèle emporte (décision 5 : les réglages oui, les
# `src` non — `_frame_sans_import`), au lieu de l'emporter par accident. La
# décision s'est prise TOUTE SEULE côté vocabulaire : les clés dérivent des
# habillages d'archétype, où `back_image`/`back_layers` sont nées vides.
# (Elle est plus stricte que nécessaire : elle jette
# aussi les clés inconnues d'un fichier perso écrit à la main. C'est le sens
# de la normalisation — un sous-arbre venu du disque n'est pas une autorité.)
_FRAME_CLES = frozenset(archetype_frame("superstar")) | {"art_window"}


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
# Forme de stockage retenue : les 49 clés de `SLOT_DEFAULTS`, jamais un
# partiel. Deux raisons. (a) `type.norm_slot` ne change alors RIEN — et cette
# idempotence est la preuve, vérifiable en une ligne, que la donnée est propre
# plutôt que « réparable ». (b) Le painter reçoit les slots du document TELS
# QUELS : un partiel obligerait chaque lecteur à connaître les défauts.
#
# Les modèles n'ont RIEN eu à changer aux phases 3b-T1 (`lock`), 3b-T2
# (`kind`/`src`/`fit`) ni 5-T2 (les dix clés des formes) : ils partent de
# `SLOT_DEFAULTS`, donc les clés y sont nées à leur défaut. Tous leurs slots
# sont des blocs de TEXTE — un archétype décrit des zones à remplir, pas des
# images ni des décors de deck.

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


# La zone du tableau fait 29 mm et la spec veut « 5 à 7 lignes ». C'est le PAS
# qui décide du maximum, et lui seul : à 4,8 mm on plafonnait à SIX lignes
# (7 x 4,8 = 33,6 > 29) — la borne haute de la spec était inatteignable sans
# que rien ne le dise. À 4,1 : 7 x 4,1 = 28,7 mm, la septième tient.
_DUEL_PAS_MM = 4.1
_DUEL_Y0_MM = 51.0


def _duel_ligne(i: int, libelle: str, valeur: str) -> list:
    """Une ligne du tableau zébré : libellé à gauche, valeur TABULAIRE à
    droite (spec). Le zébrage est fait de PLAQUES de slot — c'est exactement
    ce que la T1 a ajouté à P3, et cela suit la ligne si on la déplace."""
    y = _DUEL_Y0_MM + _DUEL_PAS_MM * i
    teinte = _ZEBRE[i % 2]
    return [
        _slot(f"lib{i + 1}", f"Libellé {i + 1}", (4, y, 36, _DUEL_PAS_MM),
              font="Inter", size_pt=7.5, min_pt=5, read_pt=6, color=_INK_DUEL,
              align="left", valign="middle", wrap=False, plate_color=teinte,
              plate_alpha=0.95, text=libelle),
        _slot(f"val{i + 1}", f"Valeur {i + 1}", (40, y, 19, _DUEL_PAS_MM),
              font="JetBrainsMono", size_pt=7.5, min_pt=5, read_pt=6,
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
        _element("ligne6", "6e ligne de tableau",
                 "Le tableau §6.2 tient de cinq à SEPT lignes ; la sixième "
                 "se pose sous la cinquième, zébrage compris.",
                 _duel_ligne(5, "Longueur", "4,52 m")),
        _element("ligne7", "7e ligne de tableau",
                 "La septième — la borne haute de la spec. Au-delà, il faut "
                 "resserrer le pas : sept lignes de 4,1 mm remplissent déjà "
                 "28,7 des 29 mm de la zone.",
                 _duel_ligne(6, "Année", "2026")),
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
        # (« 44,4 » = x 44, y 4 — la virgule sépare les DEUX coordonnées de la
        #  spec, elle n'est pas une décimale : la lecture par paires est la
        #  seule qui laisse un y à chacune des trois zones.)
        _slot("evolution", "Évolution", (4, 4, 15, 5), font="IBMPlexSans",
              size_pt=7, min_pt=5, read_pt=6, color=_INK_CREATURE,
              align="left", valign="middle", caps="upper", track=3,
              wrap=False, text="Niv. 2"),
        _slot("nom", "Nom", (19, 4, 25, 5), font="SpaceGrotesk", size_pt=12,
              min_pt=6, read_pt=12, color=_INK_CREATURE, align="left",
              valign="middle", bold=True, wrap=False, text="Céphalopode"),
        _slot("pv", "Points de vie", (44, 4, 15, 5), font="SpaceGrotesk",
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
# 3bis. LES FILTRES — les MÊMES à la lecture et à l'écriture
# ════════════════════════════════════════════════════════════════════════════
# Un modèle perso traverse ces filtres DEUX fois : quand on l'écrit depuis un
# deck, et quand on le relit depuis le disque. Deux jeux de règles auraient
# fini par diverger, et c'est la lecture qui aurait perdu — un fichier écrit
# par une version antérieure, ou à la main, n'a aucune raison d'être propre.

def _frame_sans_import(raw) -> dict:
    """Le cadre, réduit au vocabulaire que P2 déclare (liste blanche
    `_FRAME_CLES`), puis PURGÉ de ce qui pointe des octets du jeu.

    LE VERSO PERSONNALISÉ (§6.2ter, décision 5 du plan 3c) : ses `src`
    désignent `decks/{did}/frame/img_N.png`, un dossier qu'un modèle ne suit
    pas. Les RÉGLAGES voyagent — `back: "custom"` reste, pour que le jeu
    instancié dise « ce dos est une image à toi » au lieu de retomber en
    silence sur un motif du catalogue — les OCTETS non.

    LES CALQUES SONT LÂCHÉS ENTIERS, pas vidés de leur source, et c'est un
    choix mesuré. Un calque n'a rien d'autre que son fichier : opacité,
    échelle et fusion décrivent COMMENT montrer une image. Le garder sans elle
    rendrait le modèle avec jusqu'à six rangées mortes dans le panneau, à
    supprimer une par une. C'est l'inverse exact du choix fait pour les TEXTES
    des slots (doctrine 3 en tête de ce fichier) — et pour la même raison :
    là, purger casse la mise en page ; ici, garder la peuple de fantômes.

    LE MÊME FILTRE AUX DEUX PASSAGES (écriture depuis un jeu, lecture depuis
    le disque) : un fichier déposé à la main qui porterait `img:img_2.png`
    ferait sinon chercher — et parfois TROUVER — l'image d'un autre jeu."""
    f = raw if isinstance(raw, dict) else {}
    out = copy.deepcopy({k: v for k, v in f.items() if k in _FRAME_CLES})
    if "back_image" in out:
        out["back_image"] = ""
    if "back_layers" in out:
        out["back_layers"] = []
    # LE DÉCOR DE CADRE PAR IA (§6.3, décision 6) : son `src` désigne un
    # fichier du magasin d'images de l'APPLICATION — pas du jeu, mais pas du
    # modèle non plus (un modèle n'embarque pas d'illustrations, 3a). Le
    # FICHIER part, l'OPACITÉ RESTE.
    #
    # ET C'EST L'INVERSE DU CHOIX FAIT POUR LES CALQUES DU VERSO, qui sont
    # lâchés entiers. La raison est la forme, pas le principe : un calque est
    # une RANGÉE du panneau, et six rangées mortes se suppriment une par une ;
    # `decor` est une clé UNIQUE, toujours présente, avec un seul curseur. Rien
    # à nettoyer, donc — et l'opacité que l'auteur du modèle a choisie est un
    # réglage de son design : le décor que l'on générera ensuite sur le jeu
    # instancié apparaîtra à l'intensité qu'il avait prévue.
    if isinstance(out.get("decor"), dict):
        out["decor"]["src"] = ""
    return out


def _verso_note(raw) -> str:
    """Ce que la purge des IMAGES du cadre a laissé derrière, en une phrase —
    ou rien.

    Purger en silence, c'est un utilisateur qui instancie le modèle, regarde
    un dos vide et cherche la panne. La note part dans le `hint`, l'endroit
    MÊME où l'on choisit un modèle dans la galerie.

    Elle ne part QUE si quelque chose a vraiment été perdu : l'invariant 2c —
    on ne nomme que ce qui manque. Un modèle sans image se tait.

    DEUX PURGES, UNE SEULE NOTE (3c-T5) : le verso personnalisé (§6.2ter) et le
    décor de cadre par IA (§6.3) perdent tous deux leurs fichiers, et la phrase
    NOMME ce qui est parti — pas « des images » en général."""
    f = raw if isinstance(raw, dict) else {}
    perdus = []
    if f.get("back_image") or f.get("back_layers"):
        perdus.append("Le verso personnalisé garde ses réglages : ses images "
                      "et ses calques restent dans le jeu d'origine")
    dec = f.get("decor")
    if isinstance(dec, dict) and dec.get("src"):
        perdus.append("Le décor de cadre garde son opacité : l'image générée "
                      "reste dans le jeu d'origine")
    if not perdus:
        return ""
    return " ".join(p + " (à régénérer ou ré-importer)." for p in perdus)


def _texture_sans_import(raw) -> dict:
    """La matière du deck, moins le papier IMPORTÉ : ce fichier-là vit dans le
    dossier du deck, un modèle ne l'emporte pas (§6.4)."""
    t = copy.deepcopy(raw) if isinstance(raw, dict) else {}
    t.pop("custom", None)
    if str(t.get("paper") or "") in ("__import", "custom"):
        t["paper"] = PAPIER_DEFAUT
    return t


def _elements_normalises(raw) -> list[dict]:
    """Les éléments ajoutables d'un modèle perso. UN ÉLÉMENT SANS SLOTS N'EST
    PAS UN ÉLÉMENT : l'écran de la 3b en ferait un bouton qui ne pose rien."""
    out = []
    for e in (raw if isinstance(raw, list) else []):
        if not isinstance(e, dict):
            continue
        slots = type_mod.norm_slots(e.get("slots"))
        if not slots:
            continue
        out.append({"id": _texte(e.get("id"), "element", 40),
                    "label": _texte(e.get("label"), "Élément", 40),
                    "hint": _texte(e.get("hint"), "", 240),
                    "slots": slots})
    return out


# ════════════════════════════════════════════════════════════════════════════
# 4. LES MODÈLES PERSO — `{DATA_ROOT}/cardforge_models/*.json`
# ════════════════════════════════════════════════════════════════════════════

def _texte(v, defaut: str, n: int = LABEL_MAX) -> str:
    s = str(v or "").strip()
    return (s or defaut)[:n]


def _id_utilisable(ident) -> bool:
    """Un identifiant que l'on peut à la fois LISTER et OUVRIR. Une seule
    fonction pour les deux : deux motifs auraient fini par diverger, et le
    perdant aurait été l'utilisateur qui voit un modèle et ne peut pas s'en
    servir."""
    return bool(SLUG_RE.match(str(ident or "")))


def _detail_json(e: ValueError) -> str:
    """CE QU'ON PUBLIE d'une erreur de lecture JSON : le motif et la position,
    jamais l'objet d'exception entier.

    `json.JSONDecodeError` n'a rien de dangereux à dire — mais la règle
    « aucun message servi ne recopie une exception » ne souffre pas
    d'exception justement parce qu'elle est aveugle : le jour où l'on
    remplace un `json.loads` par autre chose, personne n'aura à se demander
    si CETTE exception-là portait un chemin. Ici, on nomme ce qu'on publie."""
    motif = getattr(e, "msg", None)
    if motif is None:
        return "le fichier ne porte pas un objet JSON"
    return (f"{motif} (ligne {getattr(e, 'lineno', '?')}, "
            f"colonne {getattr(e, 'colno', '?')})")


def _illisible(fichier: Path, pourquoi: str, ident: str | None = None) -> dict:
    """Une ligne « je l'ai vu, je ne peux pas m'en servir, voilà pourquoi ».
    Un modèle qui DISPARAÎT sans un mot est pire qu'un modèle en erreur : on
    le cherche du côté de l'écran pendant une heure."""
    return {"id": ident or fichier.stem, "label": fichier.stem,
            "custom": True, "illisible": True, "fichier": fichier.name,
            "error": pourquoi[:200]}


def _normaliser_perso(raw: dict, fichier: Path) -> dict:
    """Un modèle perso, ramené au contrat §6.1. NE LÈVE PAS.

    L'IDENTIFIANT EST LE NOM DU FICHIER, jamais le champ `id` du contenu :
    sinon un fichier perso pourrait se déclarer « superstar » et masquer un
    modèle d'usine dans la galerie.

    UN FICHIER QUI PORTE LE NOM D'UN MODÈLE D'USINE est LISTÉ ET SIGNALÉ,
    sous un identifiant préfixé qui ne peut pas collisionner. Les deux moitiés
    comptent : sans le préfixe, la galerie recevait deux lignes de MÊME clé
    (et une liste à clés doubles finit toujours par en perdre une) ; sans le
    signalement, l'utilisateur aurait vu son modèle, cliqué dessus, et obtenu
    le modèle d'usine — parce que `model()` sert l'usine d'abord, et doit
    continuer : c'est ce qui empêche un fichier déposé de DÉTOURNER un
    archétype. Le geste à faire (« renommez le fichier ») est dans le message
    plutôt que dans une note de version.

    CE SOUS-ARBRE VIENT DU DISQUE : il a pu être écrit à la main ou par une
    version antérieure, il n'est donc pas plus digne de confiance qu'un corps
    client. Cadre par la liste blanche, matière par le filtre d'import, slots
    par `norm_slots`, éléments sans slots jetés."""
    raw = raw if isinstance(raw, dict) else {}
    if fichier.stem in MODELS:
        return _illisible(
            fichier,
            f"« {fichier.stem} » est le nom d'un modèle d'usine : renommez "
            "le fichier pour pouvoir utiliser ce modèle",
            ident=f"perso-{fichier.stem}")
    if not _id_utilisable(fichier.stem):
        # LISTER CE QU'ON NE SAIT PAS OUVRIR SANS LE DIRE, c'est promettre une
        # vignette qui répondra 404 au clic. Le motif qui borne le chemin
        # décide donc aussi de l'affichage, et il DIT ce qu'il accepte.
        return _illisible(
            fichier,
            "nom de fichier inutilisable comme identifiant : minuscules, "
            "chiffres, tiret et tiret bas seulement (48 signes au plus)")
    fmt = str(raw.get("format") or "").strip().lower()
    typ = raw.get("type") if isinstance(raw.get("type"), dict) else {}
    fin = str(raw.get("finish") or "").strip().lower()
    els = raw.get("elements") if isinstance(raw.get("elements"), list) else []
    notes = raw.get("fonts_note")
    # LA NOTE DU VERSO VAUT AUSSI ICI, et pas seulement à l'écriture. Le
    # filtre joue aux DEUX passages : un fichier déposé à la main qui porte des
    # `src` de verso est purgé À LA LECTURE — et sans cette ligne, personne ne
    # le disait sur ce chemin-là. La note se motive par « purger en silence,
    # c'est un utilisateur qui cherche la panne » : la raison ne dépend pas du
    # sens dans lequel on traverse.
    note = _verso_note(raw.get("frame"))
    m = {
        "id": fichier.stem,
        "label": _texte(raw.get("label"), fichier.stem),
        "hint": _texte(str(raw.get("hint") or "Modèle enregistré depuis un deck.")
                       + (" " + note if note else ""),
                       "Modèle enregistré depuis un deck.", 240),
        "format": fmt if fmt in FORMATS else DEFAULT_FMT,
        "frame": _frame_sans_import(raw.get("frame")),
        "type": {"preset": _texte(typ.get("preset"), fichier.stem, 40),
                 "slots": type_mod.norm_slots(typ.get("slots"))},
        "finish": fin if fin in FINISHES else DEFAULT_FINISH,
        "texture": _texture_sans_import(raw.get("texture")),
        "elements": _elements_normalises(els),
        # La grille de référence et son éventuelle divination SURVIVENT au
        # disque (phase 6, T4) : une clé qui ne survit pas n'existe pas.
        "grille": _texte(raw.get("grille"), "", 60),
        "grille_devinee": bool(raw.get("grille_devinee")),
        "fonts_note": notes if isinstance(notes, list) else [],
        "custom": True,
        "fichier": fichier.name,
    }
    m["palette"] = palette_of(m)
    return m


def perso_list() -> tuple[list[dict], int]:
    """`(lignes, total trouvé)`. LECTURE TOLÉRANTE : un JSON abîmé est LISTÉ
    comme illisible, avec son nom de fichier — jamais un 500.

    Le TOTAL est rendu à part parce que le plafond de listage tronque : sans
    lui, un dossier de 500 modèles en montrait 400 et l'écran affirmait,
    faux, que c'était tout."""
    try:
        fichiers = sorted(p for p in models_root().glob("*.json")
                          if p.is_file())
    except OSError as e:
        logger.warning(f"cards/models: dossier illisible: {e}")
        return [], 0
    out: list[dict] = []
    for p in fichiers[:PERSO_MAX]:
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("le fichier ne porte pas un objet JSON")
            out.append(_normaliser_perso(raw, p))
        except OSError as e:
            # `str(OSError)` porte le CHEMIN COMPLET, donc le nom de compte —
            # et cette ligne-ci part dans la réponse HTTP, pas seulement dans
            # le journal. Même règle que les messages d'erreur des routes.
            logger.warning(f"cards/models: {p.name} illisible: {e}")
            out.append(_illisible(p, f"fichier illisible ({e.strerror or 'E/S'})"))
        except ValueError as e:
            out.append(_illisible(p, f"JSON invalide : {_detail_json(e)}"))
    return out, len(fichiers)


def catalogue() -> dict:
    """Usine + perso. Le CHEMIN du dossier n'est pas publié : il contient le
    nom de compte de l'utilisateur."""
    usine = [copy.deepcopy(m) for m in MODELS.values()]
    perso, total = perso_list()
    return {"models": usine + perso, "n": len(usine) + len(perso),
            "usine": len(usine), "perso": len(perso),
            "perso_total": total, "perso_tronque": total > len(perso)}


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
    if not _id_utilisable(key):
        raise KeyError(key)
    p = models_root() / f"{key}.json"
    if not p.is_file():
        raise KeyError(key)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except OSError as e:
        raise ValueError(f"{p.name} : lecture refusée ({e.strerror or 'E/S'})")
    except ValueError as e:
        raise ValueError(f"{p.name} : {_detail_json(e)}")
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
    aurait fini par diverger de celui-là.

    PAS DE COPIE PROFONDE ICI, et c'est mesuré, pas supposé : `model()` rend
    déjà une copie PRIVÉE à cet appel (elle ne partage rien avec `MODELS`), et
    `patch_deck` range l'objet reçu tel quel dans le document qu'il rend. Le
    deck hérite donc de la copie de `model()`, ce qui est exactement ce qu'on
    veut. Une seconde copie ici n'aurait rien protégé de plus — mais la
    protection tient ENTIÈREMENT à celle de `model()` : le test poison la
    vérifie des deux côtés (`test_linstanciation_copie_en_profondeur`)."""
    m = model(mid)
    doc = core.create_deck(core.clean_name(name or m["label"]))
    slots = m["type"]["slots"]
    body = {
        "format": {"fmt": m["format"]},
        "frame": m["frame"],
        # `seeded` SUIT LES SLOTS. Vrai, il empêche `seedIfEmpty`
        # (mod-type.js) de reposer le gabarit « champion » par-dessus les
        # slots de l'archétype si l'utilisateur venait à tous les supprimer.
        # Mais posé en dur, il condamnait un modèle SANS slots — un perso
        # enregistré depuis un deck vide — à un document éternellement vide :
        # plus de modèle à poser, et plus de gabarit non plus.
        # LA PROVENANCE VIENT DE L'IDENTITÉ DU MODÈLE, PAS DE CE QU'IL DÉCLARE
        # (voir `PRESET_MODELE`). `m["type"]["preset"]` n'est plus lu : sur un
        # modèle perso, il porte ce que SON deck d'origine déclarait — donc,
        # depuis ce changement, la provenance d'un AUTRE modèle. Un deck né de
        # « mon-modele » aurait annoncé venir de « superstar ». Le seul fait
        # sûr ici est l'identifiant du modèle qu'on instancie.
        "type": {"preset": PRESET_MODELE + m["id"],
                 "slots": slots, "seeded": bool(slots),
                 "sel": (slots[0]["id"] if slots else "")},
        "texture": m["texture"],
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


def _reserver(base: str):
    """Réserve un nom de fichier libre et rend `(chemin, descripteur ouvert)`.

    PAR CRÉATION EXCLUSIVE (`open("x")`), pas par `exists()` puis écriture :
    entre le regard et l'écriture, il y a une fenêtre, et un double-clic sur
    « enregistrer » la traverse. Mesuré avant correction, six appels lancés
    ensemble : trois réponses portaient le MÊME identifiant — deux modèles
    écrasés en silence — plus deux erreurs de partage de fichier. Ici, c'est
    le système de fichiers qui tranche, et il ne tranche qu'une fois.

    Un modèle d'usine n'est jamais un candidat : son nom est réservé même si
    aucun fichier ne le porte."""
    root = models_root()
    for n in range(1, 100):
        cand = base if n == 1 else f"{base}-{n}"
        if cand in MODELS:
            continue
        try:
            p = root / f"{cand}.json"
            return p, p.open("x", encoding="utf-8")
        except FileExistsError:
            continue
    p = root / f"{base}-{uuid4().hex[:6]}.json"
    return p, p.open("x", encoding="utf-8")


def _souche(ident) -> str:
    """L'id sans son suffixe NUMÉRIQUE — le parent que le produit écrit
    lui-même : `dupSlot` suffixe en chiffres (`s.id + n`) et `norm_slots`
    renomme les collisions pareil. Un id tout en chiffres reste lui-même :
    personne ne le regroupe avec rien (arbitrage (d), 26/08)."""
    s = str(ident or "")
    return re.sub(r"[0-9]+\Z", "", s) or s


def _grille_de_reference(typ: dict, slots: list) -> tuple:
    """(ids de la grille, nom, devinée ?) — l'arbitrage (a), tranché le
    26/08 : « deviner une grille ».

    `modele:<id>` → les slots de CE modèle (usine, puis perso sur disque) ;
    un gabarit du catalogue → ses slots ; sinon la grille se DEVINE : le
    gabarit dont les identifiants recouvrent le mieux ceux du jeu (départage
    par l'ordre du catalogue), et la divination SE DIT — une carte devinée
    qui ne le dit pas est une carte fausse."""
    preset = str((typ or {}).get("preset") or "").strip()
    if preset.startswith("modele:"):
        mid = preset.split(":", 1)[1]
        if mid in MODELS:
            usine = (MODELS[mid].get("type") or {}).get("slots") or []
            return {s.get("id") for s in usine}, preset, False
        if _id_utilisable(mid):
            try:
                raw = json.loads((models_root() / (mid + ".json"))
                                 .read_text(encoding="utf-8"))
                t = raw.get("type") if isinstance(raw.get("type"), dict) else {}
                ids = {s.get("id") for s in (t.get("slots") or [])
                       if isinstance(s, dict)}
                if ids:
                    return ids, preset, False
            except (OSError, ValueError):
                pass                    # le modèle d'origine a disparu : on devine
    if preset in type_mod.PRESETS:
        return ({s["id"] for s in type_mod.PRESETS[preset]["slots"]},
                preset, False)
    miens = {s.get("id") for s in slots or [] if isinstance(s, dict)}
    meilleur, score = None, -1
    for pid, p in type_mod.PRESETS.items():
        ids = {s["id"] for s in p["slots"]}
        n = len(ids & miens)
        if n > score:                   # strict : le PREMIER du catalogue gagne
            meilleur, score = pid, n
    ids = {s["id"] for s in type_mod.PRESETS[meilleur]["slots"]}
    return ids, meilleur, True


def _elements_du_deck(slots: list, grille: set, nom_grille: str,
                      devinee: bool) -> list:
    """La palette DÉRIVÉE du deck (arbitrages (b)(c)(d)) : seuls les slots
    HORS grille deviennent des éléments, ils RESTENT dans `type.slots`
    (l'élément pointe, il ne déplace pas — la re-pose passe par le renommage
    de `norm_slots`), et ceux qui partagent une souche font UN élément."""
    groupes: dict = {}
    for s in slots or []:
        sid = s.get("id")
        if sid in grille:
            continue
        groupes.setdefault(_souche(sid) or str(sid), []).append(s)
    out = []
    for souche, membres in groupes.items():
        label = re.sub(r"[\s0-9]+\Z", "", str(membres[0].get("label") or ""))
        n = len(membres)
        out.append({
            "id": _texte(souche, membres[0].get("id") or "element", 40),
            "label": _texte(label, souche or "Élément", 40),
            "hint": _texte(
                "Hors de la grille « " + str(nom_grille) + " »"
                + (" (devinée)" if devinee else "") + " : "
                + str(n) + (" blocs repris" if n > 1 else " bloc repris")
                + " du jeu d'origine.", "", 240),
            "slots": copy.deepcopy(membres),
        })
    return out


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
    grille_ids, grille_nom, grille_devinee = _grille_de_reference(typ, slots)
    m = {
        "id": "",
        "label": _texte(nom, doc.get("name") or "Mon modèle"),
        # DATE EN UTC, comme `created`/`updated` du document (`_now_iso`) :
        # deux horloges dans un même fichier finissent par se contredire d'un
        # jour, et c'est toujours au changement de date qu'on s'en aperçoit.
        # LA NOTE DU VERSO S'AJOUTE ICI, et seulement si quelque chose a été
        # purgé (`_verso_note`). Le `hint` est ce qu'on lit dans la galerie
        # avant de cliquer : c'est là que « ce modèle n'emporte pas les
        # fichiers » sert, pas dans une note de version.
        "hint": _texte(f"Modèle enregistré depuis « {doc.get('name')} » le "
                       f"{datetime.now(timezone.utc).strftime('%d/%m/%Y')}."
                       + (" " + _verso_note(doc.get("frame"))
                          if _verso_note(doc.get("frame")) else ""),
                       "", 240),
        "format": fmt if fmt in FORMATS else DEFAULT_FMT,
        # LE CADRE AUSSI EST FILTRÉ (liste blanche `_FRAME_CLES`) : c'est là
        # que §6.2ter a posé le verso personnalisé, « une image importée » —
        # dont les réglages partent et les fichiers restent.
        "frame": _frame_sans_import(doc.get("frame")),
        "type": {"preset": _texte(typ.get("preset"), "perso", 40),
                 "slots": slots},
        "finish": fin if fin in FINISHES else DEFAULT_FINISH,
        "texture": _texture_sans_import(doc.get("texture")),
        # LA PALETTE DÉRIVÉE (phase 6, T4 — la dette de la phase 5 soldée) :
        # les slots HORS de la grille de référence deviennent des éléments
        # ajoutables, groupés par souche d'identifiant. La grille et son
        # éventuelle divination s'écrivent juste en dessous.
        "elements": _elements_du_deck(slots, grille_ids, grille_nom,
                                      grille_devinee),
        "grille": grille_nom,
        "grille_devinee": grille_devinee,
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
    """Écrit le modèle perso et rend son entrée de catalogue.

    Le nom est RÉSERVÉ avant d'être rempli (cf. `_reserver`) ; l'écriture se
    fait dans le descripteur que la réservation a ouvert. Un lecteur qui
    passerait pendant ces quelques microsecondes lit un fichier vide et le
    liste « illisible » — la lecture est tolérante par construction, et c'est
    une ligne qui disparaît au rafraîchissement suivant, pas un modèle
    écrasé."""
    m = modele_depuis_deck(doc, nom)
    p, fh = _reserver(_slug(nom or doc.get("name")))
    m["id"] = p.stem
    try:
        json.dump(m, fh, ensure_ascii=False, indent=2)
        fh.close()
    except BaseException:
        # UNE RÉSERVATION QUI ÉCHOUE SE REND. Sans cela, un disque plein
        # laissait derrière lui un fichier VIDE, listé « illisible » à chaque
        # ouverture de la galerie — un déchet permanent né d'une erreur
        # passagère, et un nom de modèle pris pour rien.
        fh.close()
        try:
            p.unlink()
        except OSError:
            logger.warning(f"cards/models: réservation {p.name} non rendue")
        raise
    return _normaliser_perso(m, p)


def supprimer(mid) -> bool:
    """Efface un modèle perso. `KeyError` si l'identifiant est inconnu,
    `PermissionError` si c'est un modèle d'USINE — les sept ne vivent pas sur
    le disque, il n'y a rien à effacer et une route qui répondrait « fait »
    mentirait au prochain rafraîchissement.

    L'identifiant passe par le MÊME motif que l'écriture (`SLUG_RE`) : aucun
    chemin n'est construit depuis une chaîne brute."""
    key = str(mid or "").strip()
    if key in MODELS:
        raise PermissionError(key)
    if not _id_utilisable(key):
        raise KeyError(key)
    p = models_root() / f"{key}.json"
    if not p.is_file():
        raise KeyError(key)
    p.unlink()
    return not p.exists()


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
        # LE DÉTAIL VA AU JOURNAL, PAS DANS LA RÉPONSE : `str(OSError)` porte
        # le chemin complet, donc le nom de compte de l'utilisateur. Ce dépôt
        # a déjà payé cette fuite une fois.
        logger.exception("cards/models: écriture du modèle impossible")
        raise HTTPException(
            500, "Enregistrement du modèle impossible : le dossier des "
                 f"modèles n'a pas accepté l'écriture ({e.strerror or 'E/S'})")
    return {"model": m}


@router.delete("/models/{mid}")
async def delete_model(mid: str):
    """Supprime un modèle PERSO. Les sept d'usine ne se suppriment pas : ils
    ne sont pas sur le disque, et un « supprimé » qui réapparaît au
    rafraîchissement est pire qu'un refus."""
    try:
        await asyncio.to_thread(supprimer, mid)
    except PermissionError:
        raise HTTPException(
            403, f"« {str(mid)[:ECHO_MAX]} » est un modèle d'usine — non "
                 "supprimable")
    except KeyError:
        raise HTTPException(
            404, f"Modèle inconnu : « {str(mid)[:ECHO_MAX]} »")
    except OSError as e:
        logger.exception("cards/models: suppression impossible")
        raise HTTPException(
            500, "Suppression du modèle impossible : le dossier des modèles "
                 f"n'a pas accepté l'effacement ({e.strerror or 'E/S'})")
    return {"ok": True, "id": str(mid)[:ECHO_MAX]}
