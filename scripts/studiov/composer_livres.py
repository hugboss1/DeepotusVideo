# -*- coding: utf-8 -*-
"""SV1 (14/11/2026) — compose backend/app/studiov/livres.json : les 11 décors LIVRÉS du studio virtuel.
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


def o(type_, x, y, z, ry=0, e=1, matiere=None, couleur=None):
    d = {"type": type_, "x": x, "y": y, "z": z, "ry": ry, "e": e}
    if matiere:
        d["matiere"] = matiere
    if couleur:
        d["couleur"] = couleur
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


def mat(couleur, rugosite=0.8, metal=0.0, emission=0.0, motif="uni", echelle=1.0):
    return {"couleur": couleur, "rugosite": rugosite, "metal": metal, "emission": emission, "motif": motif,
            "echelle": echelle}


D = {}

D["livre-tech"] = {
    "nom": "Bureau créateur tech", "famille": "createur",
    "piece": {"l": 6, "p": 5, "h": 2.8, "sol": "sol", "mur": "mur", "plafond": "plafond"},
    "matieres": {"sol": mat("#2b2622", 0.55, motif="parquet"), "mur": mat("#1d2128", 0.9), "plafond": mat("#14171c"),
                 "bois": mat("#7a5a3c", 0.6, motif="bois"), "noir": mat("#15171b", 0.45, 0.2),
                 "lattes": mat("#3b2f26", 0.7, motif="lattes")},
    "lumieres": trois_points() + [lum("neon", -2.0, 1.2, -2.42, "principale", 3.5, l=1.8, ry=90),
                                  lum("neon", 2.0, 1.2, -2.42, "accent", 3.5, l=1.8, ry=90),
                                  lum("ambiance", 0, 2.6, 0, "#8fa3c8", 0.5)],
    "objets": [o("bureau", 0, 0, 0.55, matiere="bois"), o("ecran_bureau", -0.55, 0.75, 0.45, 20),
               o("micro_bras", 0.6, 0.75, 0.5, -30), o("etagere", -1.9, 0, -2.25, matiere="noir"),
               o("etagere", 1.9, 0, -2.25, matiere="noir"), o("plante", -2.6, 0, -1.6, e=1.2),
               o("lampe", 0.75, 0.75, 0.35, couleur="accent"), o("panneau_acoustique", -2.95, 1.5, -0.4, 90, matiere="lattes"),
               o("panneau_acoustique", -2.95, 1.5, 0.9, 90, matiere="lattes"), o("cadre", 2.95, 1.6, -0.6, -90),
               o("tapis", 0, 0, 0.3, e=1.4, couleur="#23262d"), o("fauteuil", 0, 0, -0.1, 180, matiere="noir"),
               o("camera_pied", 2.3, 0, 1.4, -140)],
    "ecrans": [{"x": 0, "y": 1.55, "z": -2.44, "l": 1.9, "h": 1.07, "source": "ecran"}],
    "enseigne": {"style": "neon", "couleur": "principale", "x": 0, "y": 2.35, "z": -2.44, "l": 1.1},
    "presentateur": {"x": 0, "z": 0, "h": 1.3, "assis": True},
    "cameras": cameras((0, 1.55, -2.44), assis=True, le=1.9),
    "ambiance": {"fond": "#090b0f", "flou_fond": 0.35, "vignette": 0.3, "exposition": 1.05},
}

D["livre-podcast"] = {
    "nom": "Podcast à deux", "famille": "createur",
    "piece": {"l": 6.5, "p": 5, "h": 2.8},
    "matieres": {"sol": mat("#1f1b19", 0.7, motif="parquet"), "mur": mat("#2a1f1c", 0.95),
                 "plafond": mat("#120f0e"), "bois": mat("#5d4330", 0.55, motif="bois"),
                 "mousse": mat("#3a2a25", 1.0, motif="grille"), "cuir": mat("#3b2418", 0.5)},
    "lumieres": [lum("cle", -1.6, 2.3, 2.2, "#ffd9a8", 3.0), lum("appoint", 2.0, 1.9, 2.2, "#ffe8cf", 1.3),
                 lum("contre", 0, 2.5, -1.8, "principale", 2.6), lum("neon", 0, 2.05, -2.42, "accent", 2.2, l=2.4, ry=90),
                 lum("ambiance", 0, 2.6, 0, "#ffb070", 0.35)],
    "objets": [o("table_ronde", 0, 0, 0.5, matiere="bois"), o("fauteuil", -0.95, 0, 0.2, 110, matiere="cuir"),
               o("fauteuil", 0.95, 0, 0.2, -110, matiere="cuir"), o("micro_bras", -0.45, 0.74, 0.5, 60),
               o("micro_bras", 0.45, 0.74, 0.5, -60), o("casque", 0, 0.74, 0.7),
               o("panneau_acoustique", -1.8, 1.5, -2.44, matiere="mousse"), o("panneau_acoustique", 1.8, 1.5, -2.44, matiere="mousse"),
               o("panneau_acoustique", -3.2, 1.5, -0.5, 90, matiere="mousse"), o("panneau_acoustique", 3.2, 1.5, -0.5, -90, matiere="mousse"),
               o("lampadaire", -2.6, 0, -1.9, couleur="#ffb46b"), o("plante", 2.7, 0, -1.9, e=1.3),
               o("tapis", 0, 0, 0.4, e=1.7, couleur="#4a2b22"), o("softbox", -2.4, 0, 1.9, 40)],
    "ecrans": [{"x": 0, "y": 1.35, "z": -2.44, "l": 1.5, "h": 0.85, "source": "ecran"}],
    "enseigne": {"style": "neon", "couleur": "accent", "x": 0, "y": 2.3, "z": -2.44, "l": 1.6},
    "presentateur": {"x": -0.95, "z": 0.2, "h": 1.3, "assis": True},
    "cameras": cameras((0, 1.35, -2.44), assis=True, recul=3.3, le=1.5),
    "ambiance": {"fond": "#0a0706", "flou_fond": 0.4, "vignette": 0.4, "grain": 0.05},
}

D["livre-loft"] = {
    "nom": "Loft chaleureux", "famille": "createur",
    "piece": {"l": 7, "p": 5.5, "h": 3.2},
    "matieres": {"sol": mat("#8a6a4a", 0.5, motif="parquet"), "mur": mat("#a2553d", 0.95, motif="brique"),
                 "plafond": mat("#e8e2d8"), "bois": mat("#a47a50", 0.6, motif="bois"),
                 "tissu": mat("#c9b79c", 1.0, motif="tissu"), "blanc": mat("#efe9df", 0.8)},
    "lumieres": [lum("fenetre", -3.45, 1.7, -0.6, "#fff4dc", 5.0, l=1.6, h=1.8, ry=90),
                 lum("cle", -2.2, 2.2, 1.8, "#fff0d6", 2.6), lum("appoint", 2.2, 1.8, 2.2, "#ffe2c0", 1.2),
                 lum("contre", 1.6, 2.6, -1.8, "#ffc890", 1.6), lum("ambiance", 0, 3.0, 0, "#ffe9cf", 0.9)],
    "objets": [o("canape", 0, 0, -1.3, matiere="tissu"), o("bibliotheque", 2.3, 0, -2.5, matiere="bois"),
               o("plante", -2.6, 0, -2.1, e=1.6), o("plante", 3.0, 0, -0.9, e=1.1), o("lampadaire", -1.7, 0, -1.9, couleur="#ffca8a"),
               o("table", 0, 0, 0.6, e=0.7, matiere="bois"), o("tapis", 0, 0, 0, e=2.0, couleur="#d6c3a3"),
               o("cadre", -1.0, 1.9, -2.72), o("cadre", -0.2, 2.0, -2.72, e=0.7), o("fenetre", -3.48, 1.7, -0.6, 90),
               o("guirlande", 0, 2.75, -2.6), o("horloge", 1.0, 2.2, -2.72)],
    "ecrans": [{"x": -3.1, "y": 1.5, "z": 1.2, "ry": 60, "l": 1.4, "h": 0.8, "source": "ecran", "bord": "#efe9df"}],
    "enseigne": {"style": "panneau", "couleur": "principale", "x": 1.0, "y": 1.55, "z": -2.72, "l": 0.8},
    "presentateur": {"x": 0, "z": -0.2, "h": 1.7},
    "cameras": cameras((-3.1, 1.5, 1.2), le=1.4, ry=60),
    "ambiance": {"fond": "#d9cdbc", "exposition": 1.15, "flou_fond": 0.3, "vignette": 0.15},
}

D["livre-actualite"] = {
    "nom": "Plateau d'actualité", "famille": "plateau",
    "piece": {"l": 9, "p": 6, "h": 3.4},
    "matieres": {"sol": mat("#0d1220", 0.12, 0.3), "mur": mat("#101a30", 0.6), "plafond": mat("#070b14"),
                 "laque": mat("#eef2f8", 0.2), "verre": mat("#16284a", 0.08, 0.6), "alu": mat("#9aa6b8", 0.3, 0.9, motif="metal")},
    "lumieres": [lum("cle", -2.0, 2.8, 2.8, "#ffffff", 3.6), lum("appoint", 2.4, 2.4, 2.6, "#dbe8ff", 1.6),
                 lum("contre", 0, 3.1, -1.6, "accent", 2.8), lum("neon", -3.2, 0.05, -2.9, "principale", 4, l=2.6),
                 lum("neon", 3.2, 0.05, -2.9, "principale", 4, l=2.6), lum("neon", 0, 3.2, -2.9, "accent", 3, l=7.5, ry=90),
                 lum("ambiance", 0, 3.2, 0, "#3050a0", 0.6)],
    "objets": [o("bureau", 0, 0, 0.75, e=1.25, matiere="laque"), o("colonne", -3.4, 0, -2.6, matiere="alu"),
               o("colonne", 3.4, 0, -2.6, matiere="alu"), o("projecteur", -2.4, 3.3, 1.2), o("projecteur", 2.4, 3.3, 1.2),
               o("projecteur", 0, 3.3, 1.6), o("tube_lumineux", -4.3, 0, -1.2, couleur="principale"),
               o("tube_lumineux", 4.3, 0, -1.2, couleur="principale"), o("camera_pied", 3.4, 0, 2.2, -140)],
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
    "matieres": {"sol": mat("#0c0a14", 0.25, 0.2), "mur": mat("#120d1f", 0.9), "plafond": mat("#08060e"),
                 "noir": mat("#0e0e12", 0.4, 0.3), "hex": mat("#1a1330", 0.9, motif="grille")},
    "lumieres": [lum("cle", -1.4, 2.1, 2.0, "#c9a8ff", 2.2), lum("appoint", 1.8, 1.6, 2.0, "#7ae7ff", 1.2),
                 lum("contre", -1.6, 2.3, -1.5, "#ff2bd6", 3.2), lum("contre", 1.6, 2.3, -1.5, "#00e5ff", 3.2),
                 lum("neon", -2.7, 1.4, -1.0, "#ff2bd6", 4, l=2.2, ry=0), lum("neon", 2.7, 1.4, -1.0, "#00e5ff", 4, l=2.2, ry=0),
                 lum("neon", 0, 0.05, -2.24, "#8a4bff", 4, l=5.0, ry=90)],
    "objets": [o("bureau", 0, 0, 0.5, matiere="noir"), o("ecran_bureau", -0.55, 0.75, 0.4, 18), o("ecran_bureau", 0.55, 0.75, 0.4, -18),
               o("fauteuil", 0, 0, -0.15, 180, couleur="#ff2bd6"), o("neon_anneau", -1.6, 1.7, -2.24, couleur="#ff2bd6"),
               o("neon_anneau", 1.6, 1.7, -2.24, couleur="#00e5ff", e=0.7), o("etagere", -2.2, 0, -2.05, matiere="noir"),
               o("figurine", -2.2, 1.27, -2.05), o("figurine", -1.95, 0.87, -2.05, e=0.8), o("casque", 0.7, 0.75, 0.6),
               o("panneau_acoustique", 2.72, 1.5, 0.3, -90, matiere="hex"), o("panneau_acoustique", -2.72, 1.5, 0.3, 90, matiere="hex"),
               o("micro_bras", 0.65, 0.75, 0.45, -35)],
    "ecrans": [{"x": 0, "y": 1.6, "z": -2.26, "l": 1.7, "h": 0.96, "source": "ecran", "bord": "#8a4bff"}],
    "enseigne": {"style": "neon", "couleur": "accent", "x": 0, "y": 2.3, "z": -2.26, "l": 1.0},
    "presentateur": {"x": 0, "z": 0, "h": 1.3, "assis": True, "teinte": 0.4},
    "cameras": cameras((0, 1.6, -2.26), assis=True, recul=2.9, le=1.7),
    "ambiance": {"fond": "#05030a", "brouillard": 0.04, "flou_fond": 0.3, "vignette": 0.45},
}

D["livre-atelier3d"] = {
    "nom": "Atelier d'impression 3D", "famille": "metier",
    "piece": {"l": 6.5, "p": 5, "h": 2.9},
    "matieres": {"sol": mat("#5a5d60", 0.85, motif="beton"), "mur": mat("#dfe3e6", 0.9), "plafond": mat("#f2f4f5"),
                 "bois": mat("#c49a62", 0.65, motif="bois"), "perfo": mat("#2f3a44", 0.8, motif="grille"),
                 "acier": mat("#8c949c", 0.35, 0.85, motif="metal")},
    "lumieres": [lum("cle", -1.8, 2.5, 2.4, "#f3f8ff", 3.2), lum("appoint", 2.2, 2.0, 2.2, "#ffffff", 1.6),
                 lum("contre", 1.2, 2.6, -1.7, "accent", 1.8), lum("neon", 0, 2.85, -0.6, "#ffffff", 4, l=3.0, ry=90),
                 lum("ambiance", 0, 2.7, 0, "#dfe9f5", 1.0)],
    "objets": [o("etabli", 0, 0, -2.0, matiere="bois"), o("imprimante3d", -1.1, 0.9, -2.0), o("imprimante3d", 0, 0.9, -2.0, couleur="principale"),
               o("imprimante3d", 1.1, 0.9, -2.0), o("panneau_acoustique", -2.0, 1.75, -2.44, e=1.3, matiere="perfo"),
               o("panneau_acoustique", 2.0, 1.75, -2.44, e=1.3, matiere="perfo"), o("etagere", 2.8, 0, -1.2, -90, matiere="acier"),
               o("bobine", 2.8, 1.27, -1.4, couleur="principale"), o("bobine", 2.8, 1.27, -1.0, couleur="accent"),
               o("bobine", 2.8, 0.87, -1.4, couleur="#e5484d"), o("bobine", 2.8, 0.87, -1.0, couleur="#f0b429"),
               o("bobine", 2.8, 0.47, -1.2, couleur="#3fb950"), o("figurine", -0.55, 0.9, -1.75), o("figurine", 0.55, 0.9, -1.75, e=0.7),
               o("table", 0, 0, 0.7, matiere="bois"), o("figurine", 0.4, 0.74, 0.7, e=1.2), o("caisse", -2.7, 0, -1.6),
               o("lampe", -0.6, 0.74, 0.6, couleur="accent")],
    "ecrans": [{"x": -3.2, "y": 1.6, "z": -0.4, "ry": 90, "l": 1.6, "h": 0.9, "source": "ecran"}],
    "enseigne": {"style": "panneau", "couleur": "principale", "x": 0, "y": 2.4, "z": -2.44, "l": 1.2},
    "presentateur": {"x": 0, "z": 0, "h": 1.7},
    "cameras": cameras((-3.2, 1.6, -0.4), le=1.6, ry=90),
    "ambiance": {"fond": "#cfd6dc", "exposition": 1.1, "flou_fond": 0.2, "vignette": 0.12},
}

D["livre-jeux"] = {
    "nom": "Vitrine de jeux de plateau", "famille": "metier",
    "piece": {"l": 6.5, "p": 5, "h": 2.8},
    "matieres": {"sol": mat("#3a2a1e", 0.6, motif="parquet"), "mur": mat("#22382f", 0.95), "plafond": mat("#141d19"),
                 "bois": mat("#6e4a2c", 0.55, motif="bois"), "feutre": mat("#1f5a3c", 1.0, motif="tissu")},
    "lumieres": [lum("cle", -1.8, 2.3, 2.3, "#ffe6bf", 3.0), lum("appoint", 2.1, 1.9, 2.2, "#fff3e0", 1.2),
                 lum("contre", 1.4, 2.5, -1.6, "#ffc46b", 2.0), lum("neon", -1.9, 2.3, -2.3, "#ffd9a0", 2.5, l=1.6, ry=90),
                 lum("neon", 1.9, 2.3, -2.3, "#ffd9a0", 2.5, l=1.6, ry=90), lum("ambiance", 0, 2.6, 0, "#ffd7a0", 0.5)],
    "objets": [o("vitrine", -1.9, 0, -2.2, matiere="bois"), o("vitrine", 1.9, 0, -2.2, matiere="bois"),
               o("boite_jeu", -2.15, 0.47, -2.2, couleur="principale"), o("boite_jeu", -1.65, 0.47, -2.2, 10, couleur="#e5484d"),
               o("boite_jeu", -2.1, 0.87, -2.2, -8, couleur="#f0b429"), o("boite_jeu", -1.7, 0.87, -2.2, couleur="accent"),
               o("boite_jeu", -1.9, 1.27, -2.2, 5, e=1.2, couleur="#3fb950"), o("boite_jeu", 1.65, 0.47, -2.2, couleur="#8a4bff"),
               o("boite_jeu", 2.15, 0.47, -2.2, 12, couleur="principale"), o("boite_jeu", 1.9, 0.87, -2.2, e=1.2, couleur="#e5484d"),
               o("boite_jeu", 1.7, 1.27, -2.2, -6, couleur="accent"), o("boite_jeu", 2.15, 1.27, -2.2, couleur="#f0b429"),
               o("table", 0, 0, 0.75, matiere="feutre"), o("plateau_jeu", 0, 0.75, 0.75), o("pion", -0.2, 0.77, 0.8, couleur="#e5484d"),
               o("pion", 0.15, 0.77, 0.65, couleur="principale"), o("pion", 0.3, 0.77, 0.9, couleur="#f0b429"), o("de", -0.4, 0.77, 0.6),
               o("de", -0.47, 0.77, 0.72, 30), o("lampadaire", -2.9, 0, -1.2, couleur="#ffc46b"), o("plante", 2.9, 0, -1.2, e=1.2)],
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
    "matieres": {"sol": mat("#141a22", 0.2, 0.7, motif="grille"), "mur": mat("#1a222c", 0.4, 0.6, motif="metal"),
                 "plafond": mat("#0c1016", 0.4, 0.6), "coque": mat("#2b3542", 0.35, 0.8, motif="metal"),
                 "lueur": mat("#18e0ff", 0.4, 0, 3.0)},
    "lumieres": [lum("cle", -1.8, 2.4, 2.3, "#cfe9ff", 2.6), lum("appoint", 2.1, 1.7, 2.2, "#7fd4ff", 1.0),
                 lum("contre", 0, 2.7, -1.9, "#18e0ff", 3.4), lum("neon", -3.45, 0.1, 0, "#18e0ff", 4, l=5.0),
                 lum("neon", 3.45, 0.1, 0, "#18e0ff", 4, l=5.0), lum("neon", 0, 2.95, 0, "#ff7a18", 2.0, l=4.5),
                 lum("ambiance", 0, 2.8, 0, "#2a6cff", 0.5)],
    "objets": [o("console_scifi", 0, 0, 0.7, matiere="coque"), o("hublot", -2.2, 1.6, -2.72, e=1.3), o("hublot", 2.2, 1.6, -2.72, e=1.3),
               o("tube_lumineux", -3.2, 0, -2.3, couleur="#18e0ff"), o("tube_lumineux", 3.2, 0, -2.3, couleur="#18e0ff"),
               o("hologramme", 1.9, 0, -0.9, couleur="#18e0ff"), o("colonne", -3.2, 0, 0.4, matiere="coque"),
               o("colonne", 3.2, 0, 0.4, matiere="coque"), o("caisse", -2.5, 0, -1.9, matiere="coque"),
               o("caisse", -2.5, 0.6, -1.9, 20, e=0.7, matiere="coque"), o("arche", 0, 0, -2.5, e=1.5, matiere="coque")],
    "ecrans": [{"x": 0, "y": 1.6, "z": -2.7, "l": 2.4, "h": 1.35, "source": "ecran", "bord": "#18e0ff"}],
    "enseigne": {"style": "ecran", "couleur": "#18e0ff", "x": -2.6, "y": 1.0, "z": -0.8, "ry": 60, "l": 0.9},
    "presentateur": {"x": 0, "z": 0, "h": 1.7, "teinte": 0.4},
    "cameras": cameras((0, 1.6, -2.7), recul=3.4, le=2.4),
    "ambiance": {"fond": "#03060b", "brouillard": 0.05, "vignette": 0.4, "flou_fond": 0.2},
}

D["livre-cartoon"] = {
    "nom": "Univers cartoon", "famille": "univers",
    "piece": {"l": 7, "p": 5.5, "h": 3.2, "ouvert": True},
    "matieres": {"sol": mat("#6fcf5a", 1.0, motif="pelouse"), "mur": mat("#7fd0ff", 1.0), "plafond": mat("#7fd0ff"),
                 "rouge": mat("#ff5a5f", 0.9), "jaune": mat("#ffd23f", 0.9), "violet": mat("#9b6bff", 0.9)},
    "lumieres": [lum("cle", -2.2, 3.0, 2.6, "#fff6d8", 3.4), lum("appoint", 2.4, 2.0, 2.4, "#d8f0ff", 1.8),
                 lum("contre", 1.5, 2.8, -1.8, "#ffe27a", 1.6), lum("ambiance", 0, 3.0, 0, "#cfeaff", 1.4)],
    "objets": [o("arbre_cartoon", -2.5, 0, -1.9, e=1.4), o("arbre_cartoon", 2.7, 0, -2.1, e=1.1, couleur="#3fb950"),
               o("champignon", -1.5, 0, -1.3, couleur="#ff5a5f"), o("champignon", 1.9, 0, -0.9, e=0.7, couleur="#9b6bff"),
               o("nuage", -1.8, 2.5, -2.6, e=1.3), o("nuage", 1.4, 2.8, -2.65), o("nuage", 3.0, 2.3, -2.6, e=0.8),
               o("etoile", -3.0, 2.2, -2.6, couleur="#ffd23f"), o("etoile", 0.2, 2.9, -2.65, e=0.7, couleur="#ffd23f"),
               o("arche", 0, 0, -2.3, e=1.3, matiere="jaune"), o("banc", -1.2, 0, 0.6, 20, matiere="rouge"),
               o("caisse", 2.4, 0, 0.3, 15, matiere="violet")],
    "ecrans": [{"x": 0, "y": 1.45, "z": -2.35, "l": 1.9, "h": 1.07, "source": "ecran", "bord": "#ffd23f"}],
    "enseigne": {"style": "panneau", "couleur": "principale", "x": -2.4, "y": 1.2, "z": -0.6, "ry": 40, "l": 0.9},
    "presentateur": {"x": 0, "z": 0, "h": 1.7, "teinte": 0.1},
    "cameras": cameras((0, 1.45, -2.35), le=1.9),
    "ambiance": {"fond": "#7fd0ff", "exposition": 1.2, "vignette": 0.05},
}

D["livre-foot"] = {
    "nom": "Football européen", "famille": "sport",
    "piece": {"l": 9, "p": 6, "h": 3.4, "ouvert": True},
    "matieres": {"sol": mat("#2f8a3a", 1.0, motif="pelouse"), "mur": mat("#0e1a2e", 0.9), "plafond": mat("#0a1220"),
                 "blanc": mat("#f4f6f8", 0.6), "banc": mat("#1c2c4a", 0.6)},
    "lumieres": [lum("cle", -2.6, 3.2, 3.0, "#ffffff", 3.8), lum("appoint", 2.8, 2.6, 2.8, "#eaf2ff", 2.0),
                 lum("contre", -2.0, 3.2, -2.2, "#ffffff", 2.6), lum("contre", 2.0, 3.2, -2.2, "principale", 2.6),
                 lum("ambiance", 0, 3.2, 0, "#9fc0ff", 0.8)],
    "objets": [o("gradin", 0, 0, -2.05, matiere="banc"), o("but_foot", 3.0, 0, -1.3, -35, matiere="blanc"),
               o("ballon_foot", 0.9, 0.11, 1.0), o("ballon_foot", 2.4, 0.11, -0.4), o("tableau_tactique", -2.9, 0, -0.9, 35),
               o("trophee", -1.5, 1.0, 0.2, couleur="#f0c040"), o("pupitre", -1.5, 0, 0.2, matiere="blanc"),
               o("fanion", -4.2, 0, -2.2, couleur="principale"), o("fanion", 4.2, 0, -2.2, couleur="accent"),
               o("maillot", -3.7, 1.7, -2.4, 20, couleur="principale"), o("projecteur", -3.5, 3.3, -2.6), o("projecteur", 3.5, 3.3, -2.6),
               o("banc", 2.6, 0, 1.1, -70, matiere="banc")],
    "ecrans": [{"x": 0, "y": 2.45, "z": -2.9, "l": 3.0, "h": 1.69, "source": "ecran", "bord": "#0a1220"}],
    "enseigne": {"style": "panneau", "couleur": "principale", "x": 3.6, "y": 2.5, "z": -2.9, "l": 0.9},
    "presentateur": {"x": 0, "z": 0, "h": 1.7},
    "cameras": cameras((0, 2.45, -2.9), recul=3.7, le=3.0),
    "ambiance": {"fond": "#070d18", "brouillard": 0.02, "vignette": 0.25, "exposition": 1.1},
}

D["livre-usa"] = {
    "nom": "Sports américains", "famille": "sport",
    "piece": {"l": 9, "p": 6, "h": 3.4},
    "matieres": {"sol": mat("#b9814a", 0.3, motif="parquet"), "mur": mat("#16203a", 0.9, motif="brique"),
                 "plafond": mat("#0b1020"), "casier": mat("#b5232c", 0.45, 0.5, motif="metal"), "bois": mat("#7a5230", 0.55, motif="bois"),
                 "blanc": mat("#f2f2f2", 0.6)},
    "lumieres": [lum("cle", -2.4, 3.0, 2.8, "#fff6e6", 3.6), lum("appoint", 2.6, 2.4, 2.6, "#e6efff", 1.6),
                 lum("contre", 1.8, 3.1, -2.0, "#ff4b4b", 2.4), lum("contre", -1.8, 3.1, -2.0, "#3b7bff", 2.4),
                 lum("neon", 0, 3.25, -2.9, "#ffffff", 2.5, l=7.0, ry=90), lum("ambiance", 0, 3.2, 0, "#ffd9b0", 0.6)],
    "objets": [o("casier", -3.4, 0, -2.7, matiere="casier"), o("casier", -2.7, 0, -2.7, matiere="casier"), o("casier", 2.7, 0, -2.7, matiere="casier"),
               o("casier", 3.4, 0, -2.7, matiere="casier"), o("panier_basket", 3.6, 0, -0.6, -90), o("ballon_basket", 2.6, 0.12, 0.6),
               o("ballon_ovale", -1.35, 1.0, 0.25, 30), o("pupitre", -1.4, 0, 0.2, matiere="bois"), o("batte", -3.9, 0, -1.4, 10),
               o("trophee", 1.5, 1.0, 0.2, couleur="#f0c040"), o("pupitre", 1.5, 0, 0.2, matiere="bois"),
               o("maillot", -3.05, 2.2, -2.9, couleur="#b5232c"), o("maillot", 3.05, 2.2, -2.9, couleur="#1f4fd0"),
               o("banc", -2.9, 0, -1.6, matiere="bois"), o("tableau_tactique", -4.0, 0, 0.4, 60), o("fanion", 4.2, 0, 1.4, couleur="accent")],
    "ecrans": [{"x": 0, "y": 1.8, "z": -2.94, "l": 3.2, "h": 1.8, "source": "ecran", "bord": "#0b1020"}],
    "enseigne": {"style": "neon", "couleur": "principale", "x": 0, "y": 3.0, "z": -2.94, "l": 1.6},
    "presentateur": {"x": 0, "z": 0, "h": 1.7},
    "cameras": cameras((0, 1.8, -2.94), recul=3.7, le=3.2),
    "ambiance": {"fond": "#070a14", "vignette": 0.3, "flou_fond": 0.2},
}


def composer() -> str:
    from app.services import studiov as S
    out = {}
    for sid, d in D.items():
        n = S.normaliser(d)
        assert len(n["objets"]) == len(d["objets"]), (sid, "objet hors catalogue")
        out[sid] = {"nom": d["nom"], "famille": d["famille"], **n}
    return json.dumps(out, ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    texte = composer()
    if "--check" in sys.argv:
        sys.exit(0 if SORTIE.is_file() and SORTIE.read_text("utf-8") == texte else 1)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(texte, "utf-8", newline="\n")
    print(f"{len(D)} décors -> {SORTIE} ({len(texte)} caractères)")
