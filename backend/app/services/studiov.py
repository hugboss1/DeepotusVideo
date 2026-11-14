# -*- coding: utf-8 -*-
"""SV1 (14/11/2026) — le STUDIO VIRTUEL 3D : les décors en volume qui entourent le présentateur dans la capture
(t315) et le live (t318), EN PLUS des skins (t316) qui restent par-dessus. Conception :
docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md.

Un décor est une RECETTE (`deepotus-studio`, version 1) : pièce, matières (motif dessiné OU vraie texture référencée,
lot SVH : services/studiov_habillage.py), lumières, objets du catalogue, écrans, enseigne, place du présentateur,
caméras, ambiance. La même recette est lue par le moteur three.js de l'écran
(/shared/dz-studiov-moteur.js) et par la fabrique Blender (scripts/studiov/fabriquer_decor.py).

- `DATA_ROOT/studiov/<id>.json` (id = 16 hex) : un décor de l'utilisateur, rattaché à un espace ;
- `DATA_ROOT/studiov/choix.json` = {espace_id: decor_id | ""} ; un espace qui n'a rien choisi n'a PAS de studio
  ("" : le studio s'ajoute aux skins, il ne s'impose pas) ;
- `app/studiov/livres.json` : les décors LIVRÉS, en lecture seule (`livre-<nom>`) ;
- `app/studiov/fabriques/<id>.glb` : le décor FABRIQUÉ par Blender, s'il existe (`fabrique: true` dans la vue).

Le serveur est le SEUL juge du format (`normaliser`) : champ inconnu ignoré, nombre borné, choix fermé, liste bornée,
type d'objet hors catalogue retiré, couleur = rôle du kit (principale, accent, texte, fond) ou #rrggbb. Mètres, repère
three.js (y vers le haut, le présentateur regarde vers +z, mur du fond à z = -p/2).
Aucun réseau, aucune dépense. Les refus portent un message littéral (traduit par L10)."""
from __future__ import annotations

import json
import re
import secrets
import threading
from pathlib import Path

from app.config import DATA_ROOT
from app.services import skins as K

FORMAT = "deepotus-studio"
VERSION = 1
ID = re.compile(r"^[a-f0-9]{16}$")
ID_LIVRE = re.compile(r"^livre-[a-z0-9]{2,24}$")
CLE = re.compile(r"^[a-z][a-z0-9_]{0,23}$")
LIVRES_FICHIER = Path(__file__).resolve().parent.parent / "studiov" / "livres.json"
FABRIQUES = LIVRES_FICHIER.parent / "fabriques"
MAX_DECORS = 80
MAX_NOM, MAX_TEXTE, MAX_MOT = 60, 40, 24
MAX_MATIERES, MAX_LUMIERES, MAX_OBJETS, MAX_ECRANS, MAX_CAMERAS = 48, 16, 120, 4, 6

MOTIFS = ("uni", "bois", "parquet", "brique", "beton", "tissu", "pelouse", "grille", "carreaux", "metal", "lattes")
TYPES_LUMIERE = ("cle", "appoint", "contre", "ambiance", "neon", "fenetre")
SOURCES_ECRAN = ("ecran", "image", "eteint")
SOURCES_ENSEIGNE = ("espace", "texte")
STYLES_ENSEIGNE = ("neon", "panneau", "ecran", "retro", "caisson")
# SVH (habillage) : une matière peut porter une VRAIE texture — pack du studio (stu:), catalogue de la Forge (cat:)
# ou matière de l'utilisateur dans la Forge (mat:). Ce n'est qu'une RÉFÉRENCE : jamais un chemin, jamais une URL ;
# le décorateur la résout dans le catalogue servi par services/studiov_habillage.py.
REF_TEXTURE = re.compile(r"^(?:(?:stu|cat):[a-z0-9_]{2,40}|mat:[0-9a-f]{8})$")
# SVO : un objet de type `modele` désigne un modèle importé par sa RÉFÉRENCE (services/studiov_objets.py)
REF_OBJET = re.compile(r"^obj:[a-f0-9]{16}$")
USAGES = ("autre", "sol", "mur", "plafond", "bois", "tissu", "cuir", "metal", "pierre", "plastique")
# les polices embarquées (frontend/dist/fonts) proposées aux enseignes et aux objets à texte
POLICES = ("Inter", "BebasNeue", "Anton", "ArchivoBlack", "Monoton", "Pacifico", "Righteous", "Bungee", "Cinzel",
           "PermanentMarker", "PressStart2P", "Staatliches", "AbrilFatface", "SpaceGrotesk")
MODES_PRESENTATEUR = ("detoure", "fondvert", "avatar", "encart")
MOUVEMENTS = ("fixe", "respiration", "travelling", "poussee", "orbite")
MODES = ("plateau", "incruste")
# le CATALOGUE du niveau « direct » : chaque type a son constructeur dans dz-studiov-moteur.js (banc : les deux
# listes sont égales) ; famille -> types
CATALOGUE = {
    "tables": ("bureau", "table", "table_ronde", "pupitre", "etabli", "bureau_angle", "table_basse", "console",
               "comptoir"),
    "assises": ("chaise", "fauteuil", "canape", "banc", "chaise_bureau", "chaise_gaming", "tabouret", "pouf"),
    "rangement": ("etagere", "bibliotheque", "vitrine", "casier", "etagere_murale", "cube_rangement", "meuble_tv"),
    "image_son": ("ecran_bureau", "micro_bras", "micro_table", "casque", "softbox", "projecteur", "camera_pied",
                  "panneau_acoustique", "enceinte", "table_mixage", "anneau_lumineux", "ordinateur_portable",
                  "clavier", "tour_pc", "appareil_photo"),
    "lumiere": ("lampe", "lampadaire", "neon_barre", "neon_anneau", "guirlande", "tube_lumineux", "ruban_led",
                "ruban_led_sol", "panneau_hexa", "barre_led", "suspension", "applique", "lampe_coucher",
                "lampe_lave", "bougie"),
    "enseignes": ("neon_texte", "lettres_retro", "caisson_lumineux", "panneau_direct"),
    "murs": ("cadre", "horloge", "fenetre", "affiche", "miroir", "vinyle_mural", "mur_lattes", "panneau_perfore",
             "rideau"),
    "plantes": ("plante", "cactus", "plante_tombante", "vase"),
    "bibelots": ("livres", "globe", "sablier", "cadre_photo", "tasse", "sculpture", "tapis"),
    "structure": ("colonne", "arche", "caisse", "paravent", "estrade"),
    "atelier": ("imprimante3d", "bobine", "figurine"),
    "jeux": ("boite_jeu", "plateau_jeu", "pion", "de", "manette", "borne_arcade", "console_jeu", "casque_vr"),
    "musique": ("guitare", "platine", "clap"),
    "scifi": ("console_scifi", "hublot", "hologramme"),
    "cartoon": ("nuage", "arbre_cartoon", "champignon", "etoile"),
    "football": ("but_foot", "ballon_foot", "gradin", "tableau_tactique", "fanion", "maillot", "echarpe",
                 "crampons", "plot"),
    "basket": ("panier_basket", "ballon_basket"),
    "sports_us": ("ballon_ovale", "batte", "casque_foot_us"),
    "autres_sports": ("raquette", "balle_tennis", "haltere", "gant_boxe", "skateboard"),
    "recompenses": ("trophee", "coupe", "medaille", "plaque_createur"),
    "importes": ("modele",),          # SVO : un modèle 3D de la bibliothèque de l'utilisateur (champ `ref`)
}
TYPES_OBJET = tuple(t for f in CATALOGUE.values() for t in f)
# les objets qui PORTENT UN MOT (champs `texte` et `police`) et ceux dont la couleur est une LUMIÈRE (les ambiances
# lumineuses du décorateur les recolorent)
TYPES_TEXTE = ("neon_texte", "lettres_retro", "caisson_lumineux", "panneau_direct")
TYPES_LUMINEUX = ("lampe", "lampadaire", "neon_barre", "neon_anneau", "tube_lumineux", "ruban_led", "ruban_led_sol",
                  "panneau_hexa", "barre_led", "suspension", "applique", "lampe_coucher", "lampe_lave", "neon_texte",
                  "lettres_retro", "caisson_lumineux")

DEFAUT = {
    "piece": {"l": 6.0, "p": 5.0, "h": 2.8, "sol": "sol", "mur": "mur", "plafond": "plafond", "plinthe": True},
    "enseigne": {"actif": True, "source": "espace", "texte": "", "style": "neon", "couleur": "principale",
                 "police": "Inter", "x": 0.0, "y": 1.9, "z": -2.4, "ry": 0.0, "l": 1.2},
    "presentateur": {"x": 0.0, "z": 0.0, "h": 1.7, "mode": "detoure", "ombre": True, "teinte": 0.25},
    "ambiance": {"fond": "#0b0f14", "brouillard": 0.0, "exposition": 1.0, "flou_fond": 0.0, "grain": 0.0,
                 "vignette": 0.25},
    "mode": "plateau",
}
MATIERE_DEFAUT = {"couleur": "#808890", "rugosite": 0.8, "metal": 0.0, "emission": 0.0, "motif": "uni", "echelle": 1.0,
                  "texture": "", "teinte": False, "usage": "autre"}
CAMERA_DEFAUT = {"nom": "Large", "x": 0.0, "y": 1.4, "z": 3.2, "vers": [0.0, 1.2, 0.0], "focale": 35.0,
                 "mouvement": "respiration", "amplitude": 0.03, "periode_s": 9.0}

_VERROU = threading.RLock()


class RefusStudio(ValueError):
    """Une demande refusée : `statut` = le code HTTP (400, 404, 409). Message littéral (L10)."""
    def __init__(self, message: str, statut: int):
        super().__init__(message)
        self.statut = statut


def racine() -> Path:
    return DATA_ROOT / "studiov"


# ── format ──

def _n(v, defaut, lo, hi):
    return K._nombre(v, defaut, lo, hi)


def _point(v, defaut):
    if not isinstance(v, (list, tuple)) or len(v) != 3:
        return list(defaut)
    return [_n(v[0], defaut[0], -12, 12), _n(v[1], defaut[1], -1, 8), _n(v[2], defaut[2], -12, 12)]


def _liste(v, maximum):
    return [x for x in v if isinstance(x, dict)][:maximum] if isinstance(v, list) else []


def _place(d, defaut=(0.0, 0.0, 0.0)):
    return {"x": _n(d.get("x"), defaut[0], -12, 12), "y": _n(d.get("y"), defaut[1], -1, 8),
            "z": _n(d.get("z"), defaut[2], -12, 12)}


def _ref_texture(v) -> str:
    return v if isinstance(v, str) and REF_TEXTURE.match(v) else ""


def _matieres(v) -> dict:
    out = {}
    if isinstance(v, dict):
        for cle, m in list(v.items())[:MAX_MATIERES]:
            if not (isinstance(cle, str) and CLE.match(cle) and isinstance(m, dict)):
                continue
            out[cle] = {
                "couleur": K._couleur(m.get("couleur"), MATIERE_DEFAUT["couleur"]),
                "rugosite": _n(m.get("rugosite"), 0.8, 0.02, 1.0), "metal": _n(m.get("metal"), 0.0, 0.0, 1.0),
                "emission": _n(m.get("emission"), 0.0, 0.0, 8.0),
                "motif": K._choix(m.get("motif"), MOTIFS, "uni"), "echelle": _n(m.get("echelle"), 1.0, 0.1, 10.0),
                "texture": _ref_texture(m.get("texture")), "teinte": m.get("teinte") is True,
                "usage": K._choix(m.get("usage"), USAGES, "autre"),
            }
    for cle, coul in (("sol", "#3a3f47"), ("mur", "#2a2f36"), ("plafond", "#1c2026")):
        out.setdefault(cle, dict(MATIERE_DEFAUT, couleur=coul))
    return out


def normaliser(doc) -> dict:
    """La recette telle que le moteur la lit : tout champ présent, borné, de type sûr."""
    d = doc if isinstance(doc, dict) else {}
    mat = _matieres(d.get("matieres"))
    cle_mat = lambda v, defaut: v if isinstance(v, str) and v in mat else defaut      # noqa: E731
    p, P = (d.get("piece") if isinstance(d.get("piece"), dict) else {}), DEFAUT["piece"]
    piece = {"l": _n(p.get("l"), P["l"], 3.0, 16.0), "p": _n(p.get("p"), P["p"], 3.0, 16.0),
             "h": _n(p.get("h"), P["h"], 2.2, 7.0), "sol": cle_mat(p.get("sol"), "sol"),
             "mur": cle_mat(p.get("mur"), "mur"), "plafond": cle_mat(p.get("plafond"), "plafond"),
             "plinthe": p.get("plinthe") is not False,
             "fond": cle_mat(p.get("fond"), cle_mat(p.get("mur"), "mur")),       # le mur du fond (mur d'accent)
             "gauche": cle_mat(p.get("gauche"), cle_mat(p.get("mur"), "mur")),   # SVA : chaque pan de mur a sa matière
             "droite": cle_mat(p.get("droite"), cle_mat(p.get("mur"), "mur")),
             "ouvert": p.get("ouvert") is True}            # ouvert : ni plafond ni murs latéraux (stade, extérieur)
    lumieres = []
    for x in _liste(d.get("lumieres"), MAX_LUMIERES):
        lum = {"type": K._choix(x.get("type"), TYPES_LUMIERE, "appoint"),
               "couleur": K._couleur(x.get("couleur"), "#ffffff"), "intensite": _n(x.get("intensite"), 1.0, 0.0, 20.0),
               "vers": _point(x.get("vers"), (0.0, 1.2, 0.0)), "l": _n(x.get("l"), 1.0, 0.05, 8.0),
               "h": _n(x.get("h"), 0.05, 0.02, 4.0), "ry": _n(x.get("ry"), 0.0, -360, 360)}
        lum.update(_place(x, (0.0, 2.4, 2.0)))
        lumieres.append(lum)
    objets = []
    for x in _liste(d.get("objets"), MAX_OBJETS):
        if x.get("type") not in TYPES_OBJET:
            continue                                   # hors catalogue : retiré (jamais un chemin, jamais une URL)
        if x["type"] == "modele" and not (isinstance(x.get("ref"), str) and REF_OBJET.match(x["ref"])):
            continue                                   # un modèle importé sans référence valide n'est rien
        o = {"type": x["type"], "ry": _n(x.get("ry"), 0.0, -360, 360), "e": _n(x.get("e"), 1.0, 0.1, 6.0),
             "matiere": cle_mat(x.get("matiere"), None), "couleur": K._couleur(x.get("couleur"), None, nul=True),
             "matiere2": cle_mat(x.get("matiere2"), None)}
        if o["type"] == "modele":
            o["ref"] = x["ref"]
        if o["type"] in TYPES_TEXTE:
            o["texte"] = K._texte(x.get("texte"), "", MAX_MOT)
            o["police"] = K._choix(x.get("police"), POLICES, "Inter")
        o.update(_place(x))
        objets.append(o)
    ecrans = []
    for x in _liste(d.get("ecrans"), MAX_ECRANS):
        e = {"ry": _n(x.get("ry"), 0.0, -360, 360), "l": _n(x.get("l"), 1.6, 0.3, 8.0), "h": _n(x.get("h"), 0.9, 0.2, 5.0),
             "source": K._choix(x.get("source"), SOURCES_ECRAN, "ecran"), "bord": K._couleur(x.get("bord"), "#0c0d10")}
        e.update(_place(x, (0.0, 1.5, -2.3)))
        ecrans.append(e)
    s, S = (d.get("enseigne") if isinstance(d.get("enseigne"), dict) else {}), DEFAUT["enseigne"]
    enseigne = {"actif": s.get("actif", True) is not False, "source": K._choix(s.get("source"), SOURCES_ENSEIGNE, "espace"),
                "texte": K._texte(s.get("texte"), "", MAX_TEXTE), "style": K._choix(s.get("style"), STYLES_ENSEIGNE, "neon"),
                "couleur": K._couleur(s.get("couleur"), "principale"),
                "police": K._choix(s.get("police"), POLICES, "Inter"), "ry": _n(s.get("ry"), 0.0, -360, 360),
                "l": _n(s.get("l"), S["l"], 0.2, 6.0)}
    enseigne.update(_place(s, (S["x"], S["y"], S["z"])))
    r, R = (d.get("presentateur") if isinstance(d.get("presentateur"), dict) else {}), DEFAUT["presentateur"]
    presentateur = {"x": _n(r.get("x"), 0.0, -8, 8), "z": _n(r.get("z"), 0.0, -8, 8), "h": _n(r.get("h"), R["h"], 0.6, 2.4),
                    "mode": K._choix(r.get("mode"), MODES_PRESENTATEUR, "detoure"), "ombre": r.get("ombre", True) is not False,
                    "teinte": _n(r.get("teinte"), R["teinte"], 0.0, 1.0),
                    "assis": r.get("assis") is True}
    cameras = []
    for x in _liste(d.get("cameras"), MAX_CAMERAS):
        C = CAMERA_DEFAUT
        cam = {"nom": K._texte(x.get("nom"), C["nom"], 24) or C["nom"], "vers": _point(x.get("vers"), C["vers"]),
               "focale": _n(x.get("focale"), C["focale"], 14.0, 135.0),
               "mouvement": K._choix(x.get("mouvement"), MOUVEMENTS, "fixe"),
               "amplitude": _n(x.get("amplitude"), C["amplitude"], 0.0, 1.5),
               "periode_s": _n(x.get("periode_s"), C["periode_s"], 2.0, 120.0)}
        cam.update(_place(x, (C["x"], C["y"], C["z"])))
        cameras.append(cam)
    if not cameras:
        cameras = [json.loads(json.dumps(CAMERA_DEFAUT))]
    a, A = (d.get("ambiance") if isinstance(d.get("ambiance"), dict) else {}), DEFAUT["ambiance"]
    ambiance = {"fond": K._couleur(a.get("fond"), A["fond"]), "brouillard": _n(a.get("brouillard"), 0.0, 0.0, 0.3),
                "exposition": _n(a.get("exposition"), 1.0, 0.2, 3.0), "flou_fond": _n(a.get("flou_fond"), 0.0, 0.0, 1.0),
                "grain": _n(a.get("grain"), 0.0, 0.0, 0.5), "vignette": _n(a.get("vignette"), A["vignette"], 0.0, 1.0)}
    return {"piece": piece, "matieres": mat, "lumieres": lumieres, "objets": objets, "ecrans": ecrans,
            "enseigne": enseigne, "presentateur": presentateur, "cameras": cameras, "ambiance": ambiance,
            "mode": K._choix(d.get("mode"), MODES, "plateau")}


def _livres_bruts() -> dict:
    try:
        d = json.loads(LIVRES_FICHIER.read_text("utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def est_livre(sid) -> bool:
    return isinstance(sid, str) and bool(ID_LIVRE.match(sid)) and sid in _livres_bruts()


def chemin_fabrique(sid: str) -> Path | None:
    """Le GLB fabriqué par Blender pour ce décor (livré : dans l'app ; utilisateur : dans ses données), ou None."""
    if isinstance(sid, str) and ID_LIVRE.match(sid):
        f = FABRIQUES / f"{sid}.glb"
    elif isinstance(sid, str) and ID.match(sid):
        f = racine() / "fabriques" / f"{sid}.glb"
    else:
        return None
    return f if f.is_file() else None


def _vue(sid: str, doc: dict, livre: bool, espace_id=None, nom="", modifie="", base=None) -> dict:
    v = normaliser(doc)
    v.update({"format": FORMAT, "version": VERSION, "id": sid, "nom": nom or sid, "livre": livre,
              "espace_id": None if livre else espace_id, "base": base, "modifie": modifie,
              "famille": K._texte(doc.get("famille"), "", 24) if isinstance(doc, dict) else "",
              "fabrique": chemin_fabrique(sid) is not None})
    return v


def livres() -> list:
    return [_vue(k, v, True, nom=K._texte(v.get("nom"), k, MAX_NOM)) for k, v in _livres_bruts().items()
            if ID_LIVRE.match(k) and isinstance(v, dict)]


def catalogue() -> dict:
    return {"familles": {f: list(t) for f, t in CATALOGUE.items()}, "motifs": list(MOTIFS),
            "lumieres": list(TYPES_LUMIERE), "mouvements": list(MOUVEMENTS), "usages": list(USAGES),
            "polices": list(POLICES), "styles_enseigne": list(STYLES_ENSEIGNE), "types_texte": list(TYPES_TEXTE),
            "types_lumineux": list(TYPES_LUMINEUX)}


# ── stockage ──

def _fichier(sid: str) -> Path:
    if not isinstance(sid, str) or not ID.match(sid):
        raise RefusStudio("Identifiant de décor invalide.", 400)
    return racine() / f"{sid}.json"


def _lire_brut(sid: str) -> dict:
    f = _fichier(sid)
    try:
        d = json.loads(f.read_text("utf-8"))
    except OSError:
        raise RefusStudio("Décor introuvable.", 404) from None
    except ValueError:
        raise RefusStudio("Décor illisible.", 404) from None
    if not isinstance(d, dict):
        raise RefusStudio("Décor illisible.", 404)
    return d


def lire(sid: str) -> dict:
    if est_livre(sid):
        return next(v for v in livres() if v["id"] == sid)
    if isinstance(sid, str) and ID_LIVRE.match(sid):
        raise RefusStudio("Décor introuvable.", 404)
    d = _lire_brut(sid)
    return _vue(sid, d, False, d.get("espace_id"), K._texte(d.get("nom"), sid, MAX_NOM), d.get("modifie", ""), d.get("base"))


def _tous() -> list:
    out = []
    if racine().is_dir():
        for f in sorted(racine().glob("*.json")):
            if ID.match(f.stem):
                try:
                    out.append(lire(f.stem))
                except RefusStudio:
                    continue
    return out


def lister(eid: str) -> list:
    return [v for v in _tous() if v["espace_id"] == eid]


def _nom_libre(nom: str, eid: str) -> str:
    noms = {v["nom"] for v in lister(eid)}
    if nom not in noms:
        return nom
    for i in range(2, 100):
        n = f"{nom[:MAX_NOM - 5]} ({i})"
        if n not in noms:
            return n
    return nom


def _enregistrer_brut(sid: str, doc: dict, eid: str, nom: str, base) -> dict:
    brut = normaliser(doc)
    brut.update({"format": FORMAT, "version": VERSION, "nom": nom, "espace_id": eid, "base": base,
                 "famille": K._texte(doc.get("famille"), "", 24), "modifie": K._maintenant()})
    K._ecrire_json(_fichier(sid), brut)
    return lire(sid)


def creer(base: str | None, nom: str | None, eid: str) -> dict:
    """Un décor neuf de l'espace `eid` : copie de `base` (livré ou décor de l'espace) ou de la pièce de référence."""
    with _VERROU:
        if len(_tous()) >= MAX_DECORS:
            raise RefusStudio("Trop de décors : supprimez-en un d'abord.", 409)
        src = lire(base) if base else None
        if src and not src["livre"] and src["espace_id"] != eid:
            raise RefusStudio("Ce décor appartient à un autre espace.", 409)
        n = K._texte(nom, "", MAX_NOM) or (src["nom"] if src else "Studio")
        return _enregistrer_brut(secrets.token_hex(8), src or {}, eid, _nom_libre(n, eid), base if src else None)


def enregistrer(sid: str, doc) -> dict:
    if isinstance(sid, str) and ID_LIVRE.match(sid):
        raise RefusStudio("Un décor livré ne se modifie pas : dupliquez-le d'abord.", 409)
    if not isinstance(doc, dict):
        raise RefusStudio("Décor illisible : un objet JSON est attendu.", 400)
    with _VERROU:
        d = _lire_brut(sid)
        nom = K._texte(doc.get("nom"), "", MAX_NOM) or K._texte(d.get("nom"), sid, MAX_NOM)
        doc = dict(doc, famille=d.get("famille", ""))
        return _enregistrer_brut(sid, doc, d.get("espace_id"), nom, d.get("base"))


def supprimer(sid: str) -> None:
    if isinstance(sid, str) and ID_LIVRE.match(sid):
        raise RefusStudio("Un décor livré ne se supprime pas.", 409)
    with _VERROU:
        f = _fichier(sid)
        if not f.is_file():
            raise RefusStudio("Décor introuvable.", 404)
        f.unlink()
        (racine() / "fabriques" / f"{sid}.glb").unlink(missing_ok=True)
        ch = _choix_lus()
        if sid in ch.values():
            K._ecrire_json(racine() / "choix.json", {k: v for k, v in ch.items() if v != sid})


# ── le décor de chaque espace ──

def _choix_lus() -> dict:
    try:
        d = json.loads((racine() / "choix.json").read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in d.items() if isinstance(k, str) and isinstance(v, str)} if isinstance(d, dict) else {}


def choisi(eid: str) -> str:
    """L'id du décor de l'espace ; "" = sans studio (le défaut) ; un choix disparu retombe sur ""."""
    sid = _choix_lus().get(eid) or ""
    if not sid or est_livre(sid):
        return sid
    try:
        return sid if lire(sid)["espace_id"] == eid else ""
    except RefusStudio:
        return ""


def choisir(eid: str, sid) -> str:
    if sid in (None, ""):
        sid = ""
    elif not est_livre(sid):
        if lire(sid)["espace_id"] != eid:
            raise RefusStudio("Ce décor appartient à un autre espace.", 409)
    with _VERROU:
        ch = _choix_lus()
        ch[eid] = sid
        K._ecrire_json(racine() / "choix.json", ch)
    return sid


def du_meme_espace(sid: str, eid: str) -> dict:
    v = lire(sid)
    if not v["livre"] and v["espace_id"] != eid:
        raise RefusStudio("Ce décor appartient à un autre espace.", 409)
    return v


def contexte(eid: str) -> dict:
    """L'espace, son kit et son logo : les rôles de couleur et l'enseigne du décor s'y résolvent (comme un skin)."""
    return K.contexte(eid)
