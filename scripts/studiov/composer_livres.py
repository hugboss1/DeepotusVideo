# -*- coding: utf-8 -*-
"""SV1 + SVH (14/11/2026) — compose backend/app/studiov/livres.json : les 11 décors LIVRÉS du studio virtuel.
Depuis le lot SVH, chaque décor porte de VRAIES textures (pack du studio `stu:`, catalogue de la Forge `cat:`), avec
son motif dessiné en repli, un mur du fond, des rubans LED, des néons à mot et des bibelots de son thème.
Les recettes sont écrites ici (aides pour les caméras et l'éclairage trois points), puis passées par
`studiov.normaliser` : le fichier livré est exactement ce que le serveur rendra.
Run (depuis la racine) : python scripts/studiov/composer_livres.py [--check]"""
import json
import math
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(RACINE / "backend"))
SORTIE = RACINE / "backend" / "app" / "studiov" / "livres.json"


def o(type_, x, y, z, ry=0, e=1, matiere=None, couleur=None, texte=None, police=None, matiere2=None):
    d = {"type": type_, "x": x, "y": y, "z": z, "ry": ry, "e": e}
    if matiere:
        d["matiere"] = matiere
    if couleur:
        d["couleur"] = couleur
    if matiere2:
        d["matiere2"] = matiere2
    if texte is not None:
        d["texte"] = texte
        d["police"] = police or "Inter"
    return d


def lum(type_, x, y, z, couleur="#ffffff", intensite=1.0, vers=(0, 1.2, 0), l=1.0, h=0.05, ry=0):
    return {"type": type_, "x": x, "y": y, "z": z, "couleur": couleur, "intensite": intensite, "vers": list(vers),
            "l": l, "h": h, "ry": ry}


def trois_points(cle="#fff1dc", appoint="#cfe0ff", contre="accent", force=1.0):
    return [lum("cle", -1.8, 2.3, 2.4, cle, 3.2 * force), lum("appoint", 2.2, 1.8, 2.2, appoint, 1.1 * force),
            lum("contre", 1.4, 2.5, -1.6, contre, 2.4 * force)]


def cameras(ecran=(0, 1.5, -2.3), assis=False, recul=3.1, le=1.9, ry=0):
    y = 1.15 if assis else 1.42
    return [
        {"nom": "Large", "x": 0, "y": y + 0.1, "z": recul, "vers": [0, y - 0.1, 0], "focale": 28,
         "mouvement": "respiration", "amplitude": 0.03, "periode_s": 11},
        {"nom": "Poitrine", "x": 0.15, "y": y, "z": 1.7, "vers": [0, y, 0], "focale": 50,
         "mouvement": "poussee", "amplitude": 0.12, "periode_s": 18},
        {"nom": "Côté", "x": -2.1, "y": y + 0.05, "z": 1.9, "vers": [0.1, y - 0.05, -0.2], "focale": 40,
         "mouvement": "travelling", "amplitude": 0.35, "periode_s": 16},
        {"nom": "Écran", "x": round(ecran[0] + math.sin(math.radians(ry)) * le * 1.3, 3), "y": ecran[1],
         "z": round(ecran[2] + math.cos(math.radians(ry)) * le * 1.3, 3), "vers": list(ecran), "focale": 45,
         "mouvement": "fixe", "amplitude": 0, "periode_s": 10},
    ]


def mat(couleur, rugosite=0.8, metal=0.0, emission=0.0, motif="uni", echelle=1.0, usage="autre"):
    return {"couleur": couleur, "rugosite": rugosite, "metal": metal, "emission": emission, "motif": motif,
            "echelle": echelle, "usage": usage}


def tex(ref, usage, couleur, rugosite=0.8, metal=0.0, motif="uni", echelle=1.0, teinte=False):
    """Une vraie texture (`stu:` ou `cat:`), avec la couleur et le motif d'avant en REPLI si le pack manque."""
    return {"couleur": couleur, "rugosite": rugosite, "metal": metal, "emission": 0.0, "motif": motif,
            "echelle": echelle, "texture": ref, "teinte": teinte, "usage": usage}


D = {}

D["livre-tech"] = {
    "nom": "Bureau créateur tech", "famille": "createur",
    "piece": {"l": 6, "p": 5, "h": 2.8, "sol": "sol", "mur": "mur", "fond": "fond", "plafond": "plafond"},
    "matieres": {"sol": tex("stu:wood_floor", "sol", "#2b2622", 0.6, motif="parquet"),
                 "mur": tex("stu:plastered_wall", "mur", "#1d2128", 0.9, teinte=True),
                 "fond": tex("stu:wood_table_001", "mur", "#2a211b", 0.75, motif="lattes", echelle=1.6),
                 "plafond": mat("#14171c", usage="plafond"),
                 "bois": tex("stu:oak_veneer_01", "bois", "#7a5a3c", 0.6, motif="bois"),
                 "noir": mat("#15171b", 0.45, 0.2, usage="metal"),
                 "lattes": tex("stu:rosewood_veneer1", "bois", "#3b2f26", 0.7, motif="lattes"),
                 "tapis": tex("stu:poly_wool_herringbone", "tissu", "#23262d", 1.0, teinte=True)},
    "lumieres": trois_points() + [lum("neon", -2.0, 1.2, -2.42, "principale", 3.5, l=1.8, ry=90),
                                  lum("neon", 2.0, 1.2, -2.42, "accent", 3.5, l=1.8, ry=90),
                                  lum("ambiance", 0, 2.6, 0, "#8fa3c8", 0.5)],
    "objets": [o("bureau", 0, 0, 0.55, matiere="bois", matiere2="noir"), o("ecran_bureau", -0.55, 0.75, 0.45, 20),
               o("micro_bras", 0.6, 0.75, 0.5, -30), o("etagere", -1.9, 0, -2.25, matiere="noir"),
               o("etagere", 1.9, 0, -2.25, matiere="noir"), o("plante", -2.6, 0, -1.6, e=1.2),
               o("lampe", 0.75, 0.75, 0.35, couleur="accent"), o("panneau_acoustique", -2.95, 1.5, -0.4, 90, matiere="lattes"),
               o("panneau_acoustique", -2.95, 1.5, 0.9, 90, matiere="lattes"), o("cadre", 2.95, 1.6, -0.6, -90),
               o("tapis", 0, 0, 0.3, e=1.4, matiere="tapis"), o("chaise_bureau", 0, 0, -0.1, matiere="noir"),
               o("camera_pied", 2.3, 0, 1.4, -140),
               o("ruban_led", -1.9, 2.03, -2.47, e=0.95, couleur="principale"), o("ruban_led", 1.9, 2.03, -2.47, e=0.95, couleur="accent"),
               o("ruban_led_sol", 0, 0, 0.93, e=1.5, couleur="accent"),
               o("livres", -2.12, 1.27, -2.22, e=0.9), o("appareil_photo", -1.72, 1.27, -2.22, -15), o("globe", -1.75, 0.87, -2.22),
               o("plante_tombante", -2.15, 1.67, -2.2), o("figurine", -2.1, 0.87, -2.22, e=1.2, couleur="principale"),
               o("cadre_photo", 1.72, 1.27, -2.2, 12), o("sculpture", 2.1, 1.27, -2.22), o("lampe_lave", 1.72, 0.87, -2.22, couleur="accent"),
               o("livres", 2.05, 0.47, -2.22, 180, e=0.9), o("trophee", 2.12, 0.87, -2.22, couleur="#f0c040"),
               o("plaque_createur", 2.97, 1.55, 0.35, -90), o("clavier", 0.02, 0.75, 0.62), o("tasse", 0.36, 0.75, 0.78),
               o("tour_pc", 1.12, 0, 0.5, couleur="principale")],
    "ecrans": [{"x": 0, "y": 1.55, "z": -2.44, "l": 1.9, "h": 1.07, "source": "ecran"}],
    "enseigne": {"style": "retro", "couleur": "principale", "x": 0, "y": 2.42, "z": -2.47, "l": 0.6},
    "presentateur": {"x": 0, "z": 0, "h": 1.3, "assis": True},
    "cameras": cameras((0, 1.55, -2.44), assis=True, le=1.9),
    "ambiance": {"fond": "#090b0f", "flou_fond": 0.35, "vignette": 0.3, "exposition": 1.05},
}

D["livre-podcast"] = {
    "nom": "Podcast à deux", "famille": "createur",
    "piece": {"l": 6.5, "p": 5, "h": 2.8, "fond": "fond"},
    "matieres": {"sol": tex("stu:herringbone_parquet", "sol", "#1f1b19", 0.7, motif="parquet"),
                 "mur": tex("stu:plastered_wall", "mur", "#2a1f1c", 0.95, teinte=True),
                 "fond": tex("cat:brick_wall_001", "mur", "#5a3a30", 0.95, motif="brique"),
                 "plafond": mat("#120f0e", usage="plafond"),
                 "bois": tex("stu:rosewood_veneer1", "bois", "#5d4330", 0.55, motif="bois"),
                 "mousse": mat("#3a2a25", 1.0, motif="grille", usage="tissu"),
                 "cuir": tex("stu:fabric_leather_02", "cuir", "#3b2418", 0.5),
                 "tapis": tex("stu:quatrefoil_jacquard_fabric", "tissu", "#4a2b22", 1.0, echelle=2.0, teinte=True)},
    "lumieres": [lum("cle", -1.6, 2.3, 2.2, "#ffd9a8", 3.0), lum("appoint", 2.0, 1.9, 2.2, "#ffe8cf", 1.3),
                 lum("contre", 0, 2.5, -1.8, "principale", 2.6), lum("neon", 0, 2.05, -2.42, "accent", 2.2, l=2.4, ry=90),
                 lum("ambiance", 0, 2.6, 0, "#ffb070", 0.35)],
    "objets": [o("table_ronde", 0, 0, 0.5, matiere="bois"), o("fauteuil", -0.95, 0, 0.2, 110, matiere="cuir"),
               o("fauteuil", 0.95, 0, 0.2, -110, matiere="cuir"), o("micro_bras", -0.45, 0.74, 0.5, 60),
               o("micro_bras", 0.45, 0.74, 0.5, -60), o("casque", 0, 0.74, 0.7),
               o("panneau_acoustique", -1.8, 1.5, -2.44, matiere="mousse"), o("panneau_acoustique", 1.8, 1.5, -2.44, matiere="mousse"),
               o("panneau_acoustique", -3.2, 1.5, -0.5, 90, matiere="mousse"), o("panneau_acoustique", 3.2, 1.5, -0.5, -90, matiere="mousse"),
               o("lampadaire", -2.6, 0, -1.9, couleur="#ffb46b"), o("plante", 2.95, 0, -1.1, e=1.3),
               o("tapis", 0, 0, 0.4, e=1.7, matiere="tapis"), o("softbox", -2.4, 0, 1.9, 40),
               o("panneau_direct", -2.7, 2.35, -2.46, couleur="#ff2b2b", texte="ON AIR", police="BebasNeue"),
               o("suspension", -1.0, 2.8, 0.4, couleur="#ffb060"), o("suspension", 1.0, 2.8, 0.4, couleur="#ffb060"),
               o("console", 2.25, 0, -2.2, matiere="bois"), o("platine", 1.9, 0.67, -2.2, matiere="bois", couleur="accent"),
               o("livres", 2.65, 0.67, -2.2, e=0.9), o("vinyle_mural", 3.23, 1.6, 0.4, -90, couleur="principale"),
               o("vinyle_mural", 3.23, 1.6, 0.86, -90, couleur="accent"), o("tasse", -0.22, 0.74, 0.78),
               o("tasse", 0.28, 0.74, 0.28, couleur="#2a2d33")],
    "ecrans": [{"x": 0, "y": 1.35, "z": -2.44, "l": 1.5, "h": 0.85, "source": "ecran"}],
    "enseigne": {"style": "neon", "couleur": "accent", "x": 0, "y": 2.3, "z": -2.44, "l": 1.6},
    "presentateur": {"x": -0.95, "z": 0.2, "h": 1.3, "assis": True},
    "cameras": cameras((0, 1.35, -2.44), assis=True, recul=3.3, le=1.5),
    "ambiance": {"fond": "#0a0706", "flou_fond": 0.4, "vignette": 0.4, "grain": 0.05},
}

D["livre-loft"] = {
    "nom": "Loft chaleureux", "famille": "createur",
    "piece": {"l": 7, "p": 5.5, "h": 3.2},
    "matieres": {"sol": tex("stu:laminate_floor_02", "sol", "#8a6a4a", 0.5, motif="parquet"),
                 "mur": tex("cat:brick_wall_001", "mur", "#a2553d", 0.95, motif="brique"),
                 "plafond": mat("#e8e2d8", usage="plafond"),
                 "bois": tex("stu:oak_veneer_01", "bois", "#a47a50", 0.6, motif="bois"),
                 "tissu": tex("stu:curly_teddy_natural", "tissu", "#c9b79c", 1.0, motif="tissu"),
                 "blanc": mat("#efe9df", 0.8),
                 "tapis": tex("stu:poly_wool_herringbone", "tissu", "#d6c3a3", 1.0, teinte=True)},
    "lumieres": [lum("fenetre", -3.45, 1.7, -0.6, "#fff4dc", 5.0, l=1.6, h=1.8, ry=90),
                 lum("cle", -2.2, 2.2, 1.8, "#fff0d6", 2.6), lum("appoint", 2.2, 1.8, 2.2, "#ffe2c0", 1.2),
                 lum("contre", 1.6, 2.6, -1.8, "#ffc890", 1.6), lum("ambiance", 0, 3.0, 0, "#ffe9cf", 0.9)],
    "objets": [o("canape", 0, 0, -1.3, matiere="tissu"), o("bibliotheque", 2.3, 0, -2.5, matiere="bois"),
               o("plante", -2.6, 0, -2.1, e=1.6), o("plante", 3.0, 0, -0.9, e=1.1), o("lampadaire", -1.7, 0, -1.9, couleur="#ffca8a"),
               o("table_basse", 0, 0, 0.6, matiere="bois"), o("tapis", 0, 0, 0, e=2.0, matiere="tapis"),
               o("cadre", -1.0, 1.9, -2.72), o("cadre", -0.2, 2.0, -2.72, e=0.7), o("fenetre", -3.48, 1.7, -0.6, 90),
               o("guirlande", 0, 2.75, -2.6), o("horloge", 1.0, 2.2, -2.72),
               o("lampe_coucher", -2.35, 2.05, -2.73, e=0.8, couleur="#ff8a4a"), o("pouf", 1.45, 0, 0.35, matiere="tissu"),
               o("livres", -0.25, 0.4, 0.62, 20), o("tasse", 0.28, 0.4, 0.72), o("bougie", 0.12, 0.4, 0.48),
               o("vase", 0.36, 0.4, 0.5, couleur="#f0b6c8", e=0.9), o("guitare", 3.48, 1.5, -1.9, -90, couleur="#b5651d")],
    "ecrans": [{"x": -3.1, "y": 1.5, "z": 1.2, "ry": 60, "l": 1.4, "h": 0.8, "source": "ecran", "bord": "#efe9df"}],
    "enseigne": {"style": "panneau", "couleur": "principale", "x": 1.0, "y": 1.55, "z": -2.72, "l": 0.8},
    "presentateur": {"x": 0, "z": -0.2, "h": 1.7},
    "cameras": cameras((-3.1, 1.5, 1.2), le=1.4, ry=60),
    "ambiance": {"fond": "#d9cdbc", "exposition": 1.15, "flou_fond": 0.3, "vignette": 0.15},
}

D["livre-actualite"] = {
    "nom": "Plateau d'actualité", "famille": "plateau",
    "piece": {"l": 9, "p": 6, "h": 3.4},
    "matieres": {"sol": mat("#0d1220", 0.12, 0.3, usage="sol"),
                 "mur": tex("stu:concrete_wall_008", "mur", "#101a30", 0.6, teinte=True),
                 "plafond": mat("#070b14", usage="plafond"),
                 "laque": mat("#eef2f8", 0.2, usage="plastique"), "verre": mat("#16284a", 0.08, 0.6),
                 "alu": mat("#9aa6b8", 0.3, 0.9, motif="metal", usage="metal")},
    "lumieres": [lum("cle", -2.0, 2.8, 2.8, "#ffffff", 3.6), lum("appoint", 2.4, 2.4, 2.6, "#dbe8ff", 1.6),
                 lum("contre", 0, 3.1, -1.6, "accent", 2.8), lum("neon", -3.2, 0.05, -2.9, "principale", 4, l=2.6),
                 lum("neon", 3.2, 0.05, -2.9, "principale", 4, l=2.6), lum("neon", 0, 3.2, -2.9, "accent", 3, l=7.5, ry=90),
                 lum("ambiance", 0, 3.2, 0, "#3050a0", 0.6)],
    "objets": [o("comptoir", 0, 0, 0.75, matiere="laque"), o("colonne", -3.4, 0, -2.6, matiere="alu"),
               o("colonne", 3.4, 0, -2.6, matiere="alu"), o("projecteur", -2.4, 3.3, 1.2), o("projecteur", 2.4, 3.3, 1.2),
               o("projecteur", 0, 3.3, 1.6), o("tube_lumineux", -4.3, 0, -1.2, couleur="principale"),
               o("tube_lumineux", 4.3, 0, -1.2, couleur="principale"), o("camera_pied", 3.4, 0, 2.2, -140),
               o("panneau_direct", -2.9, 2.85, -2.96, couleur="#ff2b2b", texte="ON AIR", police="BebasNeue"),
               o("ordinateur_portable", 0.72, 1.05, 0.72, 165), o("tasse", -0.85, 1.05, 0.8),
               o("ruban_led_sol", -2.6, 0, -2.92, e=2.0, couleur="accent"), o("ruban_led_sol", 2.6, 0, -2.92, e=2.0, couleur="accent")],
    "ecrans": [{"x": 0, "y": 1.75, "z": -2.94, "l": 4.2, "h": 2.36, "source": "ecran", "bord": "#0a1020"},
               {"x": -3.9, "y": 1.6, "z": -1.6, "ry": 50, "l": 1.6, "h": 0.9, "source": "image"}],
    "enseigne": {"style": "ecran", "couleur": "principale", "x": 3.9, "y": 1.6, "z": -1.6, "ry": -50, "l": 1.3},
    "presentateur": {"x": 0, "z": 0, "h": 1.7},
    "cameras": cameras((0, 1.75, -2.94), recul=3.8, le=4.2),
    "ambiance": {"fond": "#050810", "vignette": 0.2, "exposition": 1.1},
}

D["livre-gaming"] = {
    "nom": "Gaming néon", "famille": "createur",
    "piece": {"l": 5.5, "p": 4.6, "h": 2.7},
    "matieres": {"sol": mat("#0c0a14", 0.2, 0.2, usage="sol"),
                 "mur": tex("stu:concrete_wall_008", "mur", "#120d1f", 0.9, teinte=True),
                 "plafond": mat("#08060e", usage="plafond"),
                 "noir": mat("#0e0e12", 0.4, 0.3, usage="metal"), "hex": mat("#1a1330", 0.9, motif="grille", usage="tissu"),
                 "cuir": tex("stu:leather_white", "cuir", "#16161c", 0.6, teinte=True)},
    "lumieres": [lum("cle", -1.4, 2.1, 2.0, "#c9a8ff", 2.2), lum("appoint", 1.8, 1.6, 2.0, "#7ae7ff", 1.2),
                 lum("contre", -1.6, 2.3, -1.5, "#ff2bd6", 3.2), lum("contre", 1.6, 2.3, -1.5, "#00e5ff", 3.2),
                 lum("neon", -2.7, 1.4, -1.0, "#ff2bd6", 4, l=2.2, ry=0), lum("neon", 2.7, 1.4, -1.0, "#00e5ff", 4, l=2.2, ry=0),
                 lum("neon", 0, 0.05, -2.24, "#8a4bff", 4, l=5.0, ry=90)],
    "objets": [o("bureau", 0, 0, 0.5, matiere="noir"), o("ecran_bureau", -0.55, 0.75, 0.4, 18), o("ecran_bureau", 0.55, 0.75, 0.4, -18),
               o("chaise_gaming", 0, 0, -0.15, matiere="cuir", couleur="#ff2bd6"), o("neon_anneau", -1.6, 1.7, -2.24, couleur="#ff2bd6"),
               o("panneau_hexa", 1.45, 1.72, -2.27, e=1.25, couleur="#00e5ff"), o("etagere", -2.2, 0, -2.05, matiere="noir"),
               o("figurine", -2.2, 1.27, -2.05), o("figurine", -1.95, 0.87, -2.05, e=0.8), o("casque", 0.7, 0.75, 0.6),
               o("panneau_acoustique", 2.72, 1.5, 0.3, -90, matiere="hex"), o("panneau_acoustique", -2.72, 1.5, 0.3, 90, matiere="hex"),
               o("micro_bras", 0.65, 0.75, 0.45, -35),
               o("neon_texte", -1.6, 1.7, -2.26, e=0.42, couleur="#ffffff", texte="GG", police="PressStart2P"),
               o("tour_pc", 1.12, 0, 0.45, couleur="#ff2bd6"), o("clavier", 0, 0.75, 0.6, couleur="#00e5ff"),
               o("manette", -0.32, 0.75, 0.72, 25), o("console_jeu", -2.2, 0.47, -2.02), o("casque_vr", -2.25, 1.67, -2.02),
               o("borne_arcade", 2.25, 0, -1.55, -32, couleur="#8a4bff"), o("ruban_led_sol", 0, 0, 0.9, e=1.5, couleur="#8a4bff")],
    "ecrans": [{"x": 0, "y": 1.6, "z": -2.26, "l": 1.7, "h": 0.96, "source": "ecran", "bord": "#8a4bff"}],
    "enseigne": {"style": "neon", "couleur": "accent", "x": 0, "y": 2.3, "z": -2.26, "l": 1.0},
    "presentateur": {"x": 0, "z": 0, "h": 1.3, "assis": True, "teinte": 0.4},
    "cameras": cameras((0, 1.6, -2.26), assis=True, recul=2.9, le=1.7),
    "ambiance": {"fond": "#05030a", "brouillard": 0.04, "flou_fond": 0.3, "vignette": 0.45},
}

D["livre-atelier3d"] = {
    "nom": "Atelier d'impression 3D", "famille": "metier",
    "piece": {"l": 6.5, "p": 5, "h": 2.9},
    "matieres": {"sol": tex("cat:brushed_concrete", "sol", "#5a5d60", 0.85, motif="beton"),
                 "mur": tex("stu:plastered_wall", "mur", "#dfe3e6", 0.9, teinte=True),
                 "plafond": mat("#f2f4f5", usage="plafond"),
                 "bois": tex("stu:plywood", "bois", "#c49a62", 0.65, motif="bois"),
                 "perfo": mat("#e9ecef", 0.8),
                 "acier": mat("#8c949c", 0.35, 0.85, motif="metal", usage="metal")},
    "lumieres": [lum("cle", -1.8, 2.5, 2.4, "#f3f8ff", 3.2), lum("appoint", 2.2, 2.0, 2.2, "#ffffff", 1.6),
                 lum("contre", 1.2, 2.6, -1.7, "accent", 1.8), lum("neon", 0, 2.85, -0.6, "#ffffff", 4, l=3.0, ry=90),
                 lum("ambiance", 0, 2.7, 0, "#dfe9f5", 1.0)],
    "objets": [o("etabli", 0, 0, -2.0, matiere="bois", matiere2="acier"), o("imprimante3d", -1.1, 0.9, -2.0),
               o("imprimante3d", 0, 0.9, -2.0, couleur="principale"), o("imprimante3d", 1.1, 0.9, -2.0),
               o("panneau_perfore", -2.0, 1.85, -2.48, e=1.2, matiere="perfo", matiere2="bois"),
               o("panneau_perfore", 2.0, 1.85, -2.48, e=1.2, matiere="perfo", matiere2="bois"),
               o("etagere", 2.8, 0, -1.2, -90, matiere="acier"),
               o("bobine", 2.8, 1.27, -1.4, couleur="principale"), o("bobine", 2.8, 1.27, -1.0, couleur="accent"),
               o("bobine", 2.8, 0.87, -1.4, couleur="#e5484d"), o("bobine", 2.8, 0.87, -1.0, couleur="#f0b429"),
               o("bobine", 2.8, 0.47, -1.2, couleur="#3fb950"), o("figurine", -0.55, 0.9, -1.75), o("figurine", 0.55, 0.9, -1.75, e=0.7),
               o("table", 0, 0, 0.7, matiere="bois", matiere2="acier"), o("figurine", 0.4, 0.74, 0.7, e=1.2),
               o("cube_rangement", -2.42, 0, -1.2, 90, matiere="bois"), o("plante_tombante", -2.42, 1.52, -1.45),
               o("figurine", -2.42, 1.52, -0.95, e=1.5, couleur="accent"),
               o("lampe", -0.6, 0.74, 0.6, couleur="accent"), o("ordinateur_portable", -0.1, 0.74, 0.72, 170),
               o("tabouret", 1.15, 0, 0.55, matiere="bois"), o("ruban_led", 0, 0.96, -2.48, e=3.0, couleur="#ffffff")],
    "ecrans": [{"x": -3.2, "y": 1.6, "z": -0.4, "ry": 90, "l": 1.6, "h": 0.9, "source": "ecran"}],
    "enseigne": {"style": "caisson", "couleur": "principale", "x": 0, "y": 2.45, "z": -2.47, "l": 0.75},
    "presentateur": {"x": 0, "z": 0, "h": 1.7},
    "cameras": cameras((-3.2, 1.6, -0.4), le=1.6, ry=90),
    "ambiance": {"fond": "#cfd6dc", "exposition": 1.1, "flou_fond": 0.2, "vignette": 0.12},
}

D["livre-jeux"] = {
    "nom": "Vitrine de jeux de plateau", "famille": "metier",
    "piece": {"l": 6.5, "p": 5, "h": 2.8},
    "matieres": {"sol": tex("stu:diagonal_parquet", "sol", "#3a2a1e", 0.6, motif="parquet"),
                 "mur": tex("stu:plastered_wall", "mur", "#22382f", 0.95, teinte=True),
                 "plafond": mat("#141d19", usage="plafond"),
                 "bois": tex("stu:rosewood_veneer1", "bois", "#6e4a2c", 0.55, motif="bois"),
                 "feutre": tex("stu:velour_velvet", "tissu", "#1f5a3c", 1.0, motif="tissu", teinte=True)},
    "lumieres": [lum("cle", -1.8, 2.3, 2.3, "#ffe6bf", 3.0), lum("appoint", 2.1, 1.9, 2.2, "#fff3e0", 1.2),
                 lum("contre", 1.4, 2.5, -1.6, "#ffc46b", 2.0), lum("neon", -1.9, 2.3, -2.3, "#ffd9a0", 2.5, l=1.6, ry=90),
                 lum("neon", 1.9, 2.3, -2.3, "#ffd9a0", 2.5, l=1.6, ry=90), lum("ambiance", 0, 2.6, 0, "#ffd7a0", 0.5)],
    "objets": [o("vitrine", -1.9, 0, -2.2, matiere="bois"), o("vitrine", 1.9, 0, -2.2, matiere="bois"),
               o("boite_jeu", -2.15, 0.47, -2.2, couleur="principale"), o("boite_jeu", -1.65, 0.47, -2.2, 10, couleur="#e5484d"),
               o("boite_jeu", -2.1, 0.87, -2.2, -8, couleur="#f0b429"), o("boite_jeu", -1.7, 0.87, -2.2, couleur="accent"),
               o("boite_jeu", -1.9, 1.27, -2.2, 5, e=1.2, couleur="#3fb950"), o("boite_jeu", 1.65, 0.47, -2.2, couleur="#8a4bff"),
               o("boite_jeu", 2.15, 0.47, -2.2, 12, couleur="principale"), o("boite_jeu", 1.9, 0.87, -2.2, e=1.2, couleur="#e5484d"),
               o("boite_jeu", 1.7, 1.27, -2.2, -6, couleur="accent"), o("boite_jeu", 2.15, 1.27, -2.2, couleur="#f0b429"),
               o("table", 0, 0, 0.75, matiere="feutre", matiere2="bois"), o("plateau_jeu", 0, 0.75, 0.75), o("pion", -0.2, 0.77, 0.8, couleur="#e5484d"),
               o("pion", 0.15, 0.77, 0.65, couleur="principale"), o("pion", 0.3, 0.77, 0.9, couleur="#f0b429"), o("de", -0.4, 0.77, 0.6),
               o("de", -0.47, 0.77, 0.72, 30), o("lampadaire", -2.9, 0, -1.2, couleur="#ffc46b"), o("plante", 2.9, 0, -1.2, e=1.2),
               o("neon_texte", -1.9, 2.42, -2.47, e=0.62, couleur="accent", texte="PLAY", police="Righteous"),
               o("sablier", 0.45, 0.75, 0.98), o("suspension", -0.95, 2.8, 0.75, couleur="#ffb060"),
               o("suspension", 0.95, 2.8, 0.75, couleur="#ffb060"), o("medaille", 3.23, 1.75, -0.2, -90, couleur="principale"),
               o("trophee", 1.9, 1.67, -2.2, couleur="#f0c040")],
    "ecrans": [{"x": 0, "y": 1.6, "z": -2.44, "l": 1.7, "h": 0.96, "source": "ecran", "bord": "#6e4a2c"}],
    "enseigne": {"style": "panneau", "couleur": "accent", "x": 0, "y": 2.4, "z": -2.44, "l": 1.3},
    "presentateur": {"x": 0, "z": 0, "h": 1.7},
    "cameras": cameras((0, 1.6, -2.44), le=1.7) + [{"nom": "Table", "x": 0, "y": 1.9, "z": 1.9, "vers": [0, 0.75, 0.75], "focale": 50,
                                            "mouvement": "orbite", "amplitude": 0.25, "periode_s": 24}],
    "ambiance": {"fond": "#0f1713", "flou_fond": 0.3, "vignette": 0.35},
}

D["livre-scifi"] = {
    "nom": "Univers science-fiction", "famille": "univers",
    "piece": {"l": 7, "p": 5.5, "h": 3.0},
    "matieres": {"sol": tex("cat:metal_plate", "sol", "#141a22", 0.3, 0.7, motif="grille", teinte=True),
                 "mur": tex("cat:blue_metal_plate", "mur", "#1a222c", 0.45, 0.6, motif="metal", teinte=True),
                 "plafond": mat("#0c1016", 0.4, 0.6, usage="plafond"),
                 "coque": tex("stu:metal_plate_02", "metal", "#2b3542", 0.4, 0.8, motif="metal", teinte=True),
                 "lueur": mat("#18e0ff", 0.4, 0, 3.0)},
    "lumieres": [lum("cle", -1.8, 2.4, 2.3, "#cfe9ff", 2.6), lum("appoint", 2.1, 1.7, 2.2, "#7fd4ff", 1.0),
                 lum("contre", 0, 2.7, -1.9, "#18e0ff", 3.4), lum("neon", -3.45, 0.1, 0, "#18e0ff", 4, l=5.0),
                 lum("neon", 3.45, 0.1, 0, "#18e0ff", 4, l=5.0), lum("neon", 0, 2.95, 0, "#ff7a18", 2.0, l=4.5),
                 lum("ambiance", 0, 2.8, 0, "#2a6cff", 0.5)],
    "objets": [o("console_scifi", 0, 0, 0.7, matiere="coque"), o("hublot", -2.2, 1.6, -2.72, e=1.3), o("hublot", 2.2, 1.6, -2.72, e=1.3),
               o("tube_lumineux", -3.2, 0, -2.3, couleur="#18e0ff"), o("tube_lumineux", 3.2, 0, -2.3, couleur="#18e0ff"),
               o("hologramme", 1.9, 0, -0.9, couleur="#18e0ff"), o("colonne", -3.2, 0, 0.4, matiere="coque"),
               o("colonne", 3.2, 0, 0.4, matiere="coque"), o("caisse", -2.5, 0, -1.9, matiere="coque"),
               o("caisse", -2.5, 0.6, -1.9, 20, e=0.7, matiere="coque"), o("arche", 0, 0, -2.5, e=1.5, matiere="coque"),
               o("lettres_retro", 0, 2.62, -2.73, e=0.75, couleur="#18e0ff", texte="DECK 7", police="SpaceGrotesk"),
               o("ruban_led_sol", 0, 0, 0.98, e=1.9, couleur="#18e0ff"), o("casque_vr", -0.62, 0.86, 0.72, 20)],
    "ecrans": [{"x": 0, "y": 1.6, "z": -2.7, "l": 2.4, "h": 1.35, "source": "ecran", "bord": "#18e0ff"}],
    "enseigne": {"style": "ecran", "couleur": "#18e0ff", "x": -2.6, "y": 1.0, "z": -0.8, "ry": 60, "l": 0.9},
    "presentateur": {"x": 0, "z": 0, "h": 1.7, "teinte": 0.4},
    "cameras": cameras((0, 1.6, -2.7), recul=3.4, le=2.4),
    "ambiance": {"fond": "#03060b", "brouillard": 0.05, "vignette": 0.4, "flou_fond": 0.2},
}

D["livre-cartoon"] = {
    "nom": "Univers cartoon", "famille": "univers",
    "piece": {"l": 7, "p": 5.5, "h": 3.2, "ouvert": True},
    "matieres": {"sol": tex("stu:leafy_grass", "sol", "#6fcf5a", 1.0, motif="pelouse", teinte=True),
                 "mur": mat("#7fd0ff", 1.0, usage="mur"), "plafond": mat("#7fd0ff", usage="plafond"),
                 "rouge": mat("#ff5a5f", 0.9, usage="plastique"), "jaune": mat("#ffd23f", 0.9, usage="plastique"),
                 "violet": mat("#9b6bff", 0.9, usage="plastique")},
    "lumieres": [lum("cle", -2.2, 3.0, 2.6, "#fff6d8", 3.4), lum("appoint", 2.4, 2.0, 2.4, "#d8f0ff", 1.8),
                 lum("contre", 1.5, 2.8, -1.8, "#ffe27a", 1.6), lum("ambiance", 0, 3.0, 0, "#cfeaff", 1.4)],
    "objets": [o("arbre_cartoon", -2.5, 0, -1.9, e=1.4), o("arbre_cartoon", 2.7, 0, -2.1, e=1.1, couleur="#3fb950"),
               o("champignon", -1.5, 0, -1.3, couleur="#ff5a5f"), o("champignon", 1.9, 0, -0.9, e=0.7, couleur="#9b6bff"),
               o("nuage", -1.8, 2.5, -2.6, e=1.3), o("nuage", 1.4, 2.8, -2.65), o("nuage", 3.0, 2.3, -2.6, e=0.8),
               o("etoile", -3.0, 2.2, -2.6, couleur="#ffd23f"), o("etoile", 0.2, 2.9, -2.65, e=0.7, couleur="#ffd23f"),
               o("arche", 0, 0, -2.3, e=1.3, matiere="jaune"), o("banc", -1.2, 0, 0.6, 20, matiere="rouge"),
               o("caisse", 2.4, 0, 0.3, 15, matiere="violet"), o("pouf", 1.35, 0, 0.95, matiere="rouge"),
               o("cactus", 3.05, 0, 0.5, e=3.0, couleur="#43c463")],
    "ecrans": [{"x": 0, "y": 1.45, "z": -2.35, "l": 1.9, "h": 1.07, "source": "ecran", "bord": "#ffd23f"}],
    "enseigne": {"style": "panneau", "couleur": "principale", "x": -2.4, "y": 1.2, "z": -0.6, "ry": 40, "l": 0.9},
    "presentateur": {"x": 0, "z": 0, "h": 1.7, "teinte": 0.1},
    "cameras": cameras((0, 1.45, -2.35), le=1.9),
    "ambiance": {"fond": "#7fd0ff", "exposition": 1.2, "vignette": 0.05},
}

D["livre-foot"] = {
    "nom": "Football européen", "famille": "sport",
    "piece": {"l": 9, "p": 6, "h": 3.4, "ouvert": True},
    "matieres": {"sol": tex("stu:leafy_grass", "sol", "#2f8a3a", 1.0, motif="pelouse", teinte=True),
                 "mur": mat("#0e1a2e", 0.9, usage="mur"), "plafond": mat("#0a1220", usage="plafond"),
                 "blanc": mat("#f4f6f8", 0.6, usage="plastique"), "banc": mat("#1c2c4a", 0.6, usage="plastique")},
    "lumieres": [lum("cle", -2.6, 3.2, 3.0, "#ffffff", 3.8), lum("appoint", 2.8, 2.6, 2.8, "#eaf2ff", 2.0),
                 lum("contre", -2.0, 3.2, -2.2, "#ffffff", 2.6), lum("contre", 2.0, 3.2, -2.2, "principale", 2.6),
                 lum("ambiance", 0, 3.2, 0, "#9fc0ff", 0.8)],
    "objets": [o("gradin", 0, 0, -2.05, matiere="banc"), o("but_foot", 3.0, 0, -1.3, -35, matiere="blanc"),
               o("ballon_foot", 0.9, 0.11, 1.0), o("ballon_foot", 2.4, 0.11, -0.4), o("tableau_tactique", -2.9, 0, -0.9, 35),
               o("coupe", -1.5, 1.0, 0.2, couleur="#e9c04a"), o("pupitre", -1.5, 0, 0.2, matiere="blanc"),
               o("fanion", -4.2, 0, -2.2, couleur="principale"), o("fanion", 4.2, 0, -2.2, couleur="accent"),
               o("maillot", -3.7, 1.7, -2.4, 20, couleur="principale"), o("projecteur", -3.5, 3.3, -2.6), o("projecteur", 3.5, 3.3, -2.6),
               o("banc", 2.6, 0, 1.1, -70, matiere="banc"),
               o("echarpe", -2.6, 2.75, -2.97, couleur="principale"), o("crampons", 1.75, 0, 1.25, 35, couleur="accent"),
               o("plot", -0.95, 0, 1.35), o("plot", -0.35, 0, 1.65), o("plot", 0.3, 0, 1.4),
               o("panneau_direct", 3.6, 3.12, -2.96, couleur="#ff2b2b", texte="LIVE", police="BebasNeue")],
    "ecrans": [{"x": 0, "y": 2.45, "z": -2.9, "l": 3.0, "h": 1.69, "source": "ecran", "bord": "#0a1220"}],
    "enseigne": {"style": "panneau", "couleur": "principale", "x": 3.6, "y": 2.5, "z": -2.9, "l": 0.9},
    "presentateur": {"x": 0, "z": 0, "h": 1.7},
    "cameras": cameras((0, 2.45, -2.9), recul=3.7, le=3.0),
    "ambiance": {"fond": "#070d18", "brouillard": 0.02, "vignette": 0.25, "exposition": 1.1},
}

D["livre-usa"] = {
    "nom": "Sports américains", "famille": "sport",
    "piece": {"l": 9, "p": 6, "h": 3.4},
    "matieres": {"sol": tex("stu:plank_flooring_02", "sol", "#b9814a", 0.35, motif="parquet"),
                 "mur": tex("cat:brick_wall_001", "mur", "#16203a", 0.9, motif="brique", teinte=True),
                 "plafond": mat("#0b1020", usage="plafond"),
                 "casier": tex("stu:painted_metal_shutter", "metal", "#b5232c", 0.45, 0.5, motif="metal", teinte=True),
                 "bois": tex("stu:oak_veneer_01", "bois", "#7a5230", 0.55, motif="bois"),
                 "blanc": mat("#f2f2f2", 0.6, usage="plastique")},
    "lumieres": [lum("cle", -2.4, 3.0, 2.8, "#fff6e6", 3.6), lum("appoint", 2.6, 2.4, 2.6, "#e6efff", 1.6),
                 lum("contre", 1.8, 3.1, -2.0, "#ff4b4b", 2.4), lum("contre", -1.8, 3.1, -2.0, "#3b7bff", 2.4),
                 lum("neon", 0, 3.25, -2.9, "#ffffff", 2.5, l=7.0, ry=90), lum("ambiance", 0, 3.2, 0, "#ffd9b0", 0.6)],
    "objets": [o("casier", -3.4, 0, -2.7, matiere="casier"), o("casier", -2.7, 0, -2.7, matiere="casier"), o("casier", 2.7, 0, -2.7, matiere="casier"),
               o("casier", 3.4, 0, -2.7, matiere="casier"), o("panier_basket", 3.6, 0, -0.6, -90), o("ballon_basket", 2.6, 0.12, 0.6),
               o("ballon_ovale", -1.35, 1.0, 0.25, 30), o("pupitre", -1.4, 0, 0.2, matiere="bois"), o("batte", -3.9, 0, -1.4, 10),
               o("trophee", 1.5, 1.0, 0.2, couleur="#f0c040"), o("pupitre", 1.5, 0, 0.2, matiere="bois"),
               o("maillot", -3.05, 2.2, -2.9, couleur="#b5232c"), o("maillot", 3.05, 2.2, -2.9, couleur="#1f4fd0"),
               o("banc", -2.9, 0, -1.6, matiere="bois"), o("tableau_tactique", -4.0, 0, 0.4, 60), o("fanion", 4.2, 0, 1.4, couleur="accent"),
               o("casque_foot_us", -2.9, 0.48, -1.6, 25, couleur="#1f4fd0"),
               o("neon_texte", -2.05, 3.05, -2.97, e=0.85, couleur="#ff4b4b", texte="GAME DAY", police="Anton"),
               o("haltere", 3.3, 0, 1.0, 40), o("ruban_led_sol", -3.05, 0, -2.42, e=1.3, couleur="#ff4b4b"),
               o("ruban_led_sol", 3.05, 0, -2.42, e=1.3, couleur="#3b7bff")],
    "ecrans": [{"x": 0, "y": 1.8, "z": -2.94, "l": 3.2, "h": 1.8, "source": "ecran", "bord": "#0b1020"}],
    "enseigne": {"style": "neon", "couleur": "principale", "x": 0, "y": 3.0, "z": -2.94, "l": 1.6},
    "presentateur": {"x": 0, "z": 0, "h": 1.7},
    "cameras": cameras((0, 1.8, -2.94), recul=3.7, le=3.2),
    "ambiance": {"fond": "#070a14", "vignette": 0.3, "flou_fond": 0.2},
}


def composer() -> str:
    from app.services import studiov as S
    from app.services import studiov_habillage as H
    livrees = H.refs_livrees()
    out = {}
    for sid, d in D.items():
        n = S.normaliser(d)
        assert len(n["objets"]) == len(d["objets"]), (sid, "objet hors catalogue")
        for cle, m in n["matieres"].items():           # un décor livré n'emploie que des textures de l'installeur
            assert not m["texture"] or m["texture"] in livrees, (sid, cle, m["texture"])
        for src, x in zip(d["objets"], n["objets"]):    # une matière nommée par un objet existe dans la recette
            assert (src.get("matiere"), src.get("matiere2")) == (x["matiere"], x["matiere2"]), (sid, src)
        out[sid] = {"nom": d["nom"], "famille": d["famille"], **n}
    return json.dumps(out, ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    texte = composer()
    if "--check" in sys.argv:
        sys.exit(0 if SORTIE.is_file() and SORTIE.read_text("utf-8") == texte else 1)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(texte, "utf-8", newline="\n")
    print(f"{len(D)} décors -> {SORTIE} ({len(texte)} caractères)")
