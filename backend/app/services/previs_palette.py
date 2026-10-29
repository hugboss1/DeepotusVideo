# -*- coding: utf-8 -*-
"""t333 (A3 du lot Scenario, 29/10/2026) — la PREVIS COLORÉE ET NOMMÉE du Plateau 3D. PUR : aucune E/S.

Spec : docs/superpowers/specs/2026-10-27-scenario-explorations-design.md, ligne A3 (« previs colorée et nommée ; le
prompt nomme chaque forme »). Chez scenario.com la previs Blender n'est jamais grise : un code couleur publié (« cônes
verts = cyprès ») et des prompts qui nomment chaque forme. Ici :

  * chaque instance reçoit une couleur de la PALETTE (dix teintes contrastées, écart RVB ≥ 80 entre deux teintes,
    aucun gris : le gris reste celui du sol et des repères) selon sa CLÉ : l'entité de la bible (`entity_id`), sinon
    la MATIÈRE saisie (« ce que c'est », champ `matiere`), sinon son nom sans « (bible) » ni « (copie) » — les copies
    d'un cyprès partagent donc sa couleur ;
  * la couleur est STABLE : la teinte préférée d'une clé est son empreinte crc32 modulo la palette (jamais `hash()`,
    salé par processus) ; les entités de la bible sont servies D'ABORD (un personnage garde sa teinte d'une scène à
    l'autre du chapitre), puis les matières dans l'ordre d'apparition ; une teinte déjà prise passe à la suivante
    libre. Ajouter une matière APRÈS ne change aucune couleur déjà donnée. Au-delà de dix clés, les teintes se
    partagent et `partagees` le dit ;
  * les FAISCEAUX (volumes de lumière : rôle « faisceau », ou un nom qui le dit — « faisceau du phare », « god
    rays ») sont retirés d'office : ni couleur, ni légende, ni capture, ni GLB composé. Un faisceau envoyé à un modèle
    devient un SOLIDE (relevé scenario.com : « faisceau du phare retiré avant envoi ») ; le prompt dit qu'il n'y en a
    pas dans la previs. Les repères (rôle « repere ») restent gris et hors légende ;
  * la LÉGENDE est rendue en français accordé (« cylindres verts = cyprès », « capsule verte = Marie ») pour l'écran
    et en anglais pour les prompts (« green cylinders = cyprès ») ; le libellé est le texte de l'utilisateur, tel quel ;
  * la table `blender` (matériaux `previs_<clé>`, couleur LINÉAIRE, objets) attend le pont Blender (A1/A2, t331-t332) :
    les mêmes couleurs y seront posées, rien à recalculer.
"""
import re
import unicodedata
import zlib

# Dix teintes : (hex, accords français m / f / m. pl. / f. pl., anglais). Écart RVB minimal mesuré : 84 (rouge/orange).
PALETTE = [
    {"hex": "#2fb344", "fr": {"m": "vert", "f": "verte", "mp": "verts", "fp": "vertes"}, "en": "green"},
    {"hex": "#c92a2a", "fr": {"m": "rouge", "f": "rouge", "mp": "rouges", "fp": "rouges"}, "en": "red"},
    {"hex": "#1c7ed6", "fr": {"m": "bleu", "f": "bleue", "mp": "bleus", "fp": "bleues"}, "en": "blue"},
    {"hex": "#fcc419", "fr": {"m": "jaune", "f": "jaune", "mp": "jaunes", "fp": "jaunes"}, "en": "yellow"},
    {"hex": "#f76707", "fr": {"m": "orange", "f": "orange", "mp": "orange", "fp": "orange"}, "en": "orange"},
    {"hex": "#9c36b5", "fr": {"m": "violet", "f": "violette", "mp": "violets", "fp": "violettes"}, "en": "purple"},
    {"hex": "#22d3ee", "fr": {"m": "cyan", "f": "cyan", "mp": "cyan", "fp": "cyan"}, "en": "cyan"},
    {"hex": "#f783ac", "fr": {"m": "rose", "f": "rose", "mp": "roses", "fp": "roses"}, "en": "pink"},
    {"hex": "#6f4518", "fr": {"m": "marron", "f": "marron", "mp": "marron", "fp": "marron"}, "en": "brown"},
    {"hex": "#f1f3f5", "fr": {"m": "blanc", "f": "blanche", "mp": "blancs", "fp": "blanches"}, "en": "white"},
]
GRIS_REPERE = "#8a8f98"

# forme → (singulier, pluriel, genre) en français ; (singulier, pluriel) en anglais. « maillage » = un modèle 3D posé.
_FORMES_FR = {"boite": ("bloc", "blocs", "m"), "capsule": ("capsule", "capsules", "f"),
              "cylindre": ("cylindre", "cylindres", "m"), "sphere": ("sphère", "sphères", "f"),
              "maillage": ("modèle", "modèles", "m"), "*": ("forme", "formes", "f")}
_FORMES_EN = {"boite": ("block", "blocks"), "capsule": ("capsule", "capsules"), "cylindre": ("cylinder", "cylinders"),
              "sphere": ("sphere", "spheres"), "maillage": ("model", "models"), "*": ("shape", "shapes")}

_FAISCEAU = re.compile(r"\b(faisceaux?|god ?rays?|light ?(beams?|cones?|shafts?|volumes?)|beams?"
                       r"|c[oô]nes? de lumi[eè]re|volumes? de lumi[eè]re|rayons? lumineux|rayons? de lumi[eè]re)\b",
                       re.I)
_SUFFIXES = re.compile(r"\s*\((bible|copie|copy)\)\s*$", re.I)


def _texte(v, n=80) -> str:
    return " ".join(str(v or "").split())[:n]


def est_faisceau(inst: dict) -> bool:
    """Un volume de lumière : rôle « faisceau », ou un nom / une matière qui le dit."""
    if (inst or {}).get("role") == "faisceau":
        return True
    return bool(_FAISCEAU.search(f"{_texte(inst.get('nom'))} {_texte(inst.get('matiere'))}"))


def libelle(inst: dict) -> str:
    """Ce que la forme REPRÉSENTE, pour la légende : la matière saisie, sinon le nom sans « (bible) » / « (copie) »."""
    m = _texte(inst.get("matiere"), 60)
    if m:
        return m
    n = _texte(inst.get("nom"))
    while _SUFFIXES.search(n):
        n = _SUFFIXES.sub("", n)
    return n or _texte(inst.get("id"), 40)


def _slug(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")[:48] or "x"


def cle(inst: dict) -> str:
    if inst.get("entity_id"):
        return f"entite:{_texte(inst['entity_id'], 40)}"
    return f"matiere:{_slug(libelle(inst))}"


def _forme(inst: dict) -> str:
    src = inst.get("source") or {}
    return src.get("forme", "boite") if src.get("kind", "proxy") == "proxy" else "maillage"


def ligne_fr(e: dict) -> str:
    formes = sorted(set(e["formes"]))
    sg, pl, genre = _FORMES_FR[formes[0] if len(formes) == 1 else "*"]
    plur = len(e["ids"]) > 1
    adj = e["teinte"]["fr"][genre + ("p" if plur else "")]
    return f"{pl if plur else sg} {adj} = {e['libelle']}"


def ligne_en(e: dict) -> str:
    formes = sorted(set(e["formes"]))
    sg, pl = _FORMES_EN[formes[0] if len(formes) == 1 else "*"]
    return f"{e['teinte']['en']} {pl if len(e['ids']) > 1 else sg} = {e['libelle']}"


def _lineaire(hexa: str) -> list:
    out = []
    for i in (1, 3, 5):
        c = int(hexa[i:i + 2], 16) / 255
        out.append(round(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4, 5))
    return out + [1.0]


def palette(instances) -> dict:
    """La palette d'une scène : {table, couleurs {id: hex}, legende {fr, en}, prompt, faisceaux, partagees, blender}.
    `table` = une entrée par clé, dans l'ordre de la légende (entités d'abord, puis matières, ordre d'apparition)."""
    groupes, ordre, faisceaux = {}, [], []
    for i in instances or []:
        if not isinstance(i, dict):
            continue
        if est_faisceau(i):
            faisceaux.append({"id": i.get("id"), "nom": _texte(i.get("nom")),
                              "raison": "role" if i.get("role") == "faisceau" else "nom"})
            continue
        if i.get("role") == "repere":
            continue
        k = cle(i)
        if k not in groupes:
            groupes[k] = {"cle": k, "libelle": libelle(i), "entity_id": i.get("entity_id") or None, "formes": [],
                          "ids": []}
            ordre.append(k)
        groupes[k]["formes"].append(_forme(i))
        groupes[k]["ids"].append(i.get("id"))
    ordre.sort(key=lambda k: 0 if k.startswith("entite:") else 1)        # tri stable : l'apparition est gardée
    prises, partagees, n = set(), [], len(PALETTE)
    for k in ordre:
        pref = zlib.crc32(k.encode("utf-8")) % n
        idx = next(((pref + d) % n for d in range(n) if (pref + d) % n not in prises), None)
        if idx is None:
            idx = pref
            partagees.append(k)
        prises.add(idx)
        groupes[k]["teinte"] = PALETTE[idx]
        groupes[k]["couleur"] = PALETTE[idx]["hex"]
    table = [groupes[k] for k in ordre]
    fr, en = [ligne_fr(e) for e in table], [ligne_en(e) for e in table]
    prompt = ""
    if en:
        prompt = "Colour-coded previs: " + "; ".join(en) + "."
    if faisceaux and en:
        prompt += " Light beams are not drawn in the previs: they are light, not solid objects."
    blender = {"version": 1, "exclus": [f["id"] for f in faisceaux],
               "materiaux": [{"nom": f"previs_{_slug(e['cle'].split(':', 1)[1])}", "cle": e["cle"],
                              "libelle": e["libelle"], "hex": e["couleur"], "rgba_lineaire": _lineaire(e["couleur"]),
                              "objets": list(e["ids"])} for e in table]}
    return {"table": table, "couleurs": {x: e["couleur"] for e in table for x in e["ids"]},
            "legende": {"fr": fr, "en": en}, "prompt": prompt, "faisceaux": faisceaux, "partagees": partagees,
            "blender": blender}


def phrase_image(prompt_legende: str) -> str:
    """La phrase ajoutée au prompt de l'IMAGE du plan quand la capture colorée du Plateau part en dernière référence."""
    if not prompt_legende:
        return ""
    return (" Layout: the last reference image is a colour-coded 3D previs of this shot — follow its composition, "
            f"camera and placement, not its colours. {prompt_legende}")
