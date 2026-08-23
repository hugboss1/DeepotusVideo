# -*- coding: utf-8 -*-
"""Card Forge — phase 3a, tâche 3 : les MODÈLES de deck (`cards/models.py`).

Ce que ce fichier verrouille — dans l'ordre de la spec §6.1/§6.2/§6.4
(docs/superpowers/specs/2026-08-19-cardforge-universel-design.md:280-357,
474-484) :

  1. **Sept modèles d'usine**, chacun avec les clés du contrat §6.1 et un
     `format` DÉCLARÉ. Les zones de la spec sont en POKER (63 x 88) : un
     modèle qui ne déclare pas son format instancierait ses millimètres sur
     une carte qui n'est pas la sienne (entrée laissée par la T2 — `winMM`
     re-borne la fenêtre et la plaque devient NÉGATIVE sur `micro`).
  2. **L'habillage vient de `frame.archetype_frame(nom)`**, la FONCTION, pas
     la table : elle rend une copie profonde. Le modèle ne retape rien — une
     seconde source de vérité divergerait au premier réglage.
  3. **Les zones §6.2 sont transcrites**, millimètre par millimètre, depuis
     le coin de COUPE. La table `ZONES` ci-dessous est recopiée de la spec et
     sert d'ORACLE : les boîtes des slots (ou leur réunion, pour une grille)
     doivent tomber dessus. Toutes tiennent dans la rogne.
  4. **Un slot de modèle est un objet COMPLET** : les 39 clés de
     `SLOT_DEFAULTS`, et `norm_slot` ne le change PAS (idempotence = la
     donnée est propre, pas « réparable »).
  5. **Aucune police devinée.** Toute police citée par un modèle est dans la
     liste que `mod-type.js` sait CHARGER (bloc `FONTS_LOCAL`, extrait ici),
     et le repli de chaque police de la spec est NOMMÉ dans `fonts_note` —
     jamais un échec silencieux (décision 2 du plan 3a).
  6. **Un slot qui veut une plaque porte un texte** (leçon T1 : un slot vide
     ne peint pas sa plaque). Aucun élément ajoutable ne tombe SUR un slot
     déjà posé.
  7. **La palette est une LECTURE du modèle**, pas une quatrième table de
     couleurs : `ink` est l'encre que les slots emploient, `plate` la couleur
     de plaque dominante, `paper` la teinte du support.
  8. `GET /models` sert usine + perso (un JSON perso illisible est LISTÉ
     comme illisible, jamais un 500) ; `POST /decks {model}` instancie
     (inconnu -> 404 nommé) ; `POST /decks/{did}/duplicate` copie TOUT ;
     `POST /models` enregistre un modèle perso SANS les illustrations.
  9. **L'instanciation copie EN PROFONDEUR** (poison test F9) : un deck
     instancié puis modifié ne contamine ni la table des modèles ni le deck
     suivant.

Run : <embedded python> backend/tests/test_cards_models.py
"""
import asyncio
import copy
import json
import os
import pathlib
import re
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
# LE DOSSIER DE DONNÉES AUSSI : les modèles perso vivent dans
# `{DATA_ROOT}/cardforge_models/` (spec §6.4). Sans cette ligne, la suite
# écrirait ses modèles de test dans le VRAI dossier de l'utilisateur, et le
# test « le dossier ne contient que ce que j'y ai mis » serait faux chez lui.
os.environ["DEEPOTUS_DATA_DIR"] = str(pathlib.Path(_tmp, "data"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
pathlib.Path(_tmp, "data").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                  # noqa: E402
from httpx import AsyncClient, ASGITransport                    # noqa: E402

from app.services.cards import contract as CT                   # noqa: E402
from app.services.cards import frame as FR                      # noqa: E402
from app.services.cards import gltf as GL                       # noqa: E402
from app.services.cards import models as MO                     # noqa: E402
from app.services.cards import type as TY                       # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
JS_TYPE = REPO / "frontend" / "cardforge" / "js" / "mod-type.js"
JS_TEXTURE = REPO / "frontend" / "cardforge" / "js" / "mod-texture.js"

IDS = ("superstar", "duel", "creature", "arcane", "monstre", "legende",
       "gravee")
TRIM = FORMAT_TRIM = CT.FORMATS["poker_eu"]["trim_mm"]          # (63.0, 88.0)
EPS = 0.011          # un centième de millimètre : la précision des zones


# ═════════════════ L'ORACLE : les zones de la spec, recopiées ═══════════════
# spec §6.2:323-354, « x,y (largeur x hauteur) » en mm depuis le coin de COUPE.
# `union` : la réunion des boîtes citées doit tomber EXACTEMENT sur la zone.
# `dedans` : la réunion doit être INCLUSE dans la zone (une grille qui n'en
#            remplit pas la dernière ligne reste fidèle ; en sortir, non).
# `origine` : la spec ne donne qu'un point de départ — on épingle le coin.
ZONES_UNION = {
    "superstar": [
        ("note géante 8,12 (12x9)", ("note",), (8.0, 12.0, 12.0, 9.0)),
        ("bandeau nom 6,47 (51x7)", ("nom",), (6.0, 47.0, 51.0, 7.0)),
        ("grille 6 stats 2x3 8,56 (47x21)",
         ("vit", "tir", "pas", "drb", "def", "phy"),
         (8.0, 56.0, 47.0, 21.0)),
    ],
    "duel": [
        ("bandeau titre 4,4 (55x8, rectangle)", ("titre",),
         (4.0, 4.0, 55.0, 8.0)),
    ],
    "creature": [
        ("pied faiblesse/résistance/retraite",
         ("faiblesse", "resistance", "retraite"), (6.0, 74.0, 51.0, 5.0)),
    ],
    "arcane": [
        ("boîte parchemin 4,54.5 (55x24)", ("regles", "ambiance"),
         (4.0, 54.5, 55.0, 24.0)),
    ],
    "monstre": [
        ("étoiles alignées à droite 8,12.5", ("etoiles",),
         (8.0, 12.5, 47.0, 5.0)),
    ],
    "legende": [
        ("bandeau nom 0,74 (63x10)", ("nom",), (0.0, 74.0, 63.0, 10.0)),
    ],
    "gravee": [
        ("cartouche chiffres romains 4,4 (55x8)", ("romain",),
         (4.0, 4.0, 55.0, 8.0)),
        ("cartouche nom 4,75 (55x9)", ("nom",), (4.0, 75.0, 55.0, 9.0)),
    ],
}

# zone de la spec, slots posés + slots des éléments ajoutables : la réunion
# des DEUX doit tenir dans la zone (c'est ainsi que « 1-2 attaques » et
# « 5-7 lignes » se vérifient — le second exemplaire est un élément).
ZONES_DEDANS = {
    "duel": [("tableau 5-7 lignes 4,51 (55x29)",
              ("lib1", "lib2", "lib3", "lib4", "lib5",
               "val1", "val2", "val3", "val4", "val5"),
              ("lib6", "val6", "lib7", "val7"),
              (4.0, 51.0, 55.0, 29.0))],
    "creature": [("1-2 attaques 6,51 (51x22)",
                  ("att1cout", "att1nom", "att1deg"),
                  ("att2cout", "att2nom", "att2deg"),
                  (6.0, 51.0, 51.0, 22.0))],
}

ZONES_ORIGINE = {
    "creature": [("cartouche d'évolution 4,4", ("evolution",), (4.0, 4.0)),
                 ("nom 19,4", ("nom",), (19.0, 4.0)),
                 # « cartouche d'évolution 4,4 ; nom 19,4 ; PV + élément 44,4 »
                 # se lit PAR PAIRES : x = 44, y = 4. La virgule y sépare les
                 # deux coordonnées, elle n'est pas une décimale — la lecture
                 # « 44,4 mm » ferait un x et laisserait le y en l'air.
                 ("PV + élément 44,4", ("pv",), (44.0, 4.0))],
    "arcane": [("bandeau titre 4,3.5", ("nom", "cout"), (4.0, 3.5)),
               ("ligne de type 4,49", ("typeline",), (4.0, 49.0)),
               ("cartouche force/endurance 47,78", ("fe",), (47.0, 78.0))],
    "monstre": [("nom capitales 4.5,4.5", ("nom",), (4.5, 4.5)),
                ("ligne ATK/DEF à droite 6,81.5", ("atk", "dfn"),
                 (6.0, 81.5))],
    "legende": [("logo de collection 4,4", ("logo",), (4.0, 4.0))],
}

# TOUTES les zones que la spec NOMME, archétype par archétype — la table de
# PRÉSENCE. Les tables de géométrie ci-dessus ne jugent que ce qu'elles citent :
# cinq zones nommées par la spec (le pied d'icônes de « superstar », la ligne
# légale et la rareté de « créature », le pied de référence de « duel », la
# ligne de type et la boîte d'effet de « monstre ») pouvaient être SUPPRIMÉES
# du modèle sans faire rougir un seul test. Ce qui suit compte les zones ; ce
# qui précède les mesure.
# (Les zones que le CADRE porte — plaque à pans coupés, bordure 2,5 mm, double
# filet, cadre couleur pleine — et les fenêtres d'illustration ne sont pas ici :
# elles sont jugées sur `frame`, plus haut.)
ZONES_PRESENTES = {
    "superstar": (("note géante", ("note",)),
                  ("position dessous", ("poste",)),
                  ("drapeau / écusson en colonne gauche",
                   ("drapeau", "ecusson")),
                  ("bandeau nom", ("nom",)),
                  ("grille 6 stats VIT/TIR/PAS/DRB/DEF/PHY",
                   ("vit", "tir", "pas", "drb", "def", "phy")),
                  ("pied d'icônes", ("pied",))),
    "duel": (("bandeau titre", ("titre",)),
             ("tableau 5-7 lignes zébrées",
              ("lib1", "val1", "lib2", "val2", "lib3", "val3",
               "lib4", "val4", "lib5", "val5")),
             ("pied référence « 12/32 »", ("ref",))),
    "creature": (("cartouche d'évolution", ("evolution",)),
                 ("nom", ("nom",)),
                 ("PV + élément", ("pv",)),
                 ("1-2 attaques (coût / nom / dégâts)",
                  ("att1cout", "att1nom", "att1deg")),
                 ("pied faiblesse / résistance / retraite",
                  ("faiblesse", "resistance", "retraite")),
                 ("ligne légale", ("legal",)),
                 ("rareté cercle/losange/étoile", ("rarete",))),
    "arcane": (("bandeau titre (nom)", ("nom",)),
               ("coût en pastilles ⌀4", ("cout",)),
               ("ligne de type", ("typeline",)),
               ("boîte parchemin : règles romain", ("regles",)),
               ("boîte parchemin : ambiance italique", ("ambiance",)),
               ("cartouche force / endurance", ("fe",))),
    "monstre": (("nom capitales", ("nom",)),
                ("attribut ⌀7 à droite", ("attribut",)),
                ("étoiles alignées à droite", ("etoiles",)),
                ("type [CROCHETS]", ("typeline",)),
                ("boîte d'effet", ("effet",)),
                ("ligne ATK/DEF à droite", ("atk", "dfn"))),
    "legende": (("logo de collection", ("logo",)),
                ("bandeau nom", ("nom",)),
                ("№ en coin", ("numero",)),
                ("verso : lignes = saisons",
                 ("entete", "s1", "s2", "s3")),
                ("verso : TOTAL en gras", ("total",)),
                ("verso : bloc anecdote", ("anecdote",))),
    "gravee": (("cartouche chiffres romains", ("romain",)),
               ("cartouche nom capitales espacées", ("nom",))),
}

# La FENÊTRE d'illustration de chaque archétype (spec §6.2). Elle appartient
# au cadre (T2) — le modèle la reçoit par `archetype_frame`. La relire ICI
# ferme la boucle : la spec, la table de P2 et le modèle disent la même chose.
# `legende` n'en cite AUCUNE (photo pleine page) : sa fenêtre est un choix
# d'implémenteur, publié par la T2 — elle n'a donc pas de ligne ici.
FENETRES = {
    "superstar": (22.0, 8.0, 36.0, 38.0),
    "duel": (4.0, 13.0, 55.0, 31.0),
    "creature": (6.0, 11.0, 51.0, 35.0),
    "arcane": (5.0, 9.5, 53.0, 39.0),
    "monstre": (8.0, 18.5, 47.0, 47.0),
    "gravee": (4.0, 13.0, 55.0, 61.0),
}


def _api(method: str, path: str, **kw):
    """Un appel HTTP réel contre l'application montée, en process."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t") as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


def _api_parallele(n: int, method: str, path: str, **kw):
    """`n` appels EN MÊME TEMPS. Les routes travaillent dans un fil
    (`asyncio.to_thread`) : le parallélisme est réel, pas simulé."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t") as c:
            return await asyncio.gather(
                *[c.request(method, path, **kw) for _ in range(n)])
    return asyncio.run(go())


def _slots(m: dict) -> list[dict]:
    return list(m["type"]["slots"])


def _par_id(m: dict) -> dict:
    return {s["id"]: s for s in _slots(m)}


def _elem_slots(m: dict) -> list[dict]:
    out = []
    for e in m["elements"]:
        out.extend(e["slots"])
    return out


def _union(boxes) -> tuple:
    xs = [b[0] for b in boxes]
    ys = [b[1] for b in boxes]
    x2 = [b[0] + b[2] for b in boxes]
    y2 = [b[1] + b[3] for b in boxes]
    return (min(xs), min(ys), max(x2) - min(xs), max(y2) - min(ys))


def _chevauche(a, b) -> float:
    """Surface commune de deux boîtes, en mm². Un contact bord à bord vaut 0."""
    w = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    h = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return (w * h) if (w > EPS and h > EPS) else 0.0


# ═══════════════════ 1. les sept modèles d'usine ════════════════════════════

def test_sept_modeles_dusine():
    """La première fournée de la spec §6.2, ni plus ni moins."""
    assert tuple(MO.MODELS) == IDS, list(MO.MODELS)
    assert len(MO.MODELS) == 7


@pytest.mark.parametrize("mid", IDS)
def test_les_cles_du_contrat(mid):
    """Le contrat §6.1 : {id, label, hint, format, frame, type, palette,
    finish, texture, elements}. `fonts_note` et `custom` sont en plus."""
    m = MO.model(mid)
    for k in ("id", "label", "hint", "format", "frame", "type", "palette",
              "finish", "texture", "elements", "fonts_note", "custom"):
        assert k in m, f"{mid}: clé {k!r} absente"
    assert m["id"] == mid
    assert isinstance(m["label"], str) and m["label"].strip()
    assert isinstance(m["hint"], str) and m["hint"].strip()
    assert m["custom"] is False
    assert isinstance(m["type"]["slots"], list) and m["type"]["slots"]
    assert isinstance(m["elements"], list) and m["elements"]


@pytest.mark.parametrize("mid", IDS)
def test_le_format_est_declare_et_cest_le_poker(mid):
    """Les zones §6.2 sont celles du POKER (entrée de la T2). Un modèle
    DÉCLARE son format ; il ne le suppose pas."""
    assert MO.model(mid)["format"] == "poker_eu"
    assert CT.FORMATS["poker_eu"]["trim_mm"] == (63.0, 88.0)


@pytest.mark.parametrize("mid", IDS)
def test_lhabillage_vient_de_la_fonction(mid):
    """`archetype_frame` rend une COPIE PROFONDE et c'est LA porte d'entrée
    (T2, F9). Le modèle ne recopie pas la table."""
    m = MO.model(mid)
    assert m["frame"] == FR.archetype_frame(mid)
    fams = {f["id"] for f in FR.FAMILIES}
    assert m["frame"]["family"] in fams
    assert m["frame"]["rarity"] in {r["id"] for r in FR.RARITIES}
    # L'ÉGALITÉ NE SUFFIT PAS : elle reste vraie quand le modèle porte
    # l'objet MÊME de la table de P2. C'est l'IDENTITÉ qu'il faut nier —
    # jusque dans le sous-dictionnaire, seul partage qui se paie plus tard.
    assert m["frame"] is not FR.ARCHETYPE_FRAMES[mid]
    assert m["frame"]["window"] is not FR.ARCHETYPE_FRAMES[mid]["window"]
    assert MO.MODELS[mid]["frame"] is not FR.ARCHETYPE_FRAMES[mid]


@pytest.mark.parametrize("mid", sorted(FENETRES))
def test_les_fenetres_sont_celles_de_la_spec(mid):
    w = MO.model(mid)["frame"]["window"]
    attendu = FENETRES[mid]
    got = (w["x"], w["y"], w["w"], w["h"])
    assert all(abs(a - b) <= EPS for a, b in zip(got, attendu)), \
        f"{mid}: fenêtre {got} au lieu de {attendu} (spec §6.2)"


@pytest.mark.parametrize("mid", IDS)
def test_les_boites_tiennent_dans_la_rogne(mid):
    """63 x 88, coin de coupe. Une boîte qui sort part au massicot."""
    m = MO.model(mid)
    for s in _slots(m) + _elem_slots(m):
        x, y, w, h = s["box"]
        assert w > 0 and h > 0, f"{mid}/{s['id']}: boîte vide"
        assert x >= -EPS and y >= -EPS, f"{mid}/{s['id']}: {s['box']}"
        assert x + w <= TRIM[0] + EPS, f"{mid}/{s['id']}: {s['box']} > 63 mm"
        assert y + h <= TRIM[1] + EPS, f"{mid}/{s['id']}: {s['box']} > 88 mm"


@pytest.mark.parametrize("mid", IDS)
def test_un_slot_est_un_objet_complet_de_39_cles(mid):
    """Forme de stockage retenue : l'objet COMPLET, pas un partiel. Et
    `norm_slot` ne le change PAS — l'idempotence de la normalisation est la
    preuve que la donnée est propre (bornes, casse des couleurs, min_pt <=
    size_pt, identifiants légaux).

    39 depuis la phase 3b : `lock` (verrou d'édition, tâche 1) puis `kind`,
    `src` et `fit` (calque d'image, tâche 2). Les modèles n'ont RIEN eu à
    changer — ils partent de `SLOT_DEFAULTS`, donc les clés y sont nées à leur
    défaut, et le compte ci-dessous est ce qui le prouve. Tous leurs slots sont
    des blocs de TEXTE : un archétype décrit des zones à remplir."""
    m = MO.model(mid)
    assert len(TY.SLOT_DEFAULTS) == 39
    vus = set()
    for i, s in enumerate(_slots(m) + _elem_slots(m)):
        assert set(s) == set(TY.SLOT_DEFAULTS), \
            f"{mid}/{s.get('id')}: clés {sorted(set(s) ^ set(TY.SLOT_DEFAULTS))}"
        assert TY.SLOT_ID_RE.match(s["id"]), f"{mid}: id {s['id']!r} illégal"
        assert TY.norm_slot(s, i) == s, \
            f"{mid}/{s['id']}: normalisé != écrit"
    for s in _slots(m):
        assert s["id"] not in vus, f"{mid}: id {s['id']!r} en double"
        vus.add(s["id"])


# ═════════════ 2. les zones de la spec, transcrites au millimètre ═══════════

@pytest.mark.parametrize("mid", IDS)
def test_toutes_les_zones_nommees_par_la_spec_sont_la(mid):
    """LE COMPTE, pas la mesure. Les tables de géométrie ne jugent que les
    zones qu'elles citent : sans ce test, cinq zones NOMMÉES par la spec
    pouvaient disparaître du modèle sans un test rouge."""
    par_id = _par_id(MO.model(mid))
    for quoi, ids in ZONES_PRESENTES[mid]:
        for sid in ids:
            assert sid in par_id, \
                f"{mid} : zone « {quoi} » de la spec §6.2 — slot {sid!r} " \
                f"absent (présents : {sorted(par_id)})"
    # « lignes = saisons, TOTAL EN GRAS » (§6.2-6) : la seule graisse que la
    # spec impose nommément.
    if mid == "legende":
        assert par_id["total"]["bold"] is True


@pytest.mark.parametrize("mid", sorted(ZONES_UNION))
def test_les_zones_de_la_spec_sont_transcrites(mid):
    par_id = _par_id(MO.model(mid))
    for quoi, ids, zone in ZONES_UNION[mid]:
        for sid in ids:
            assert sid in par_id, f"{mid}: slot {sid!r} absent pour « {quoi} »"
        got = _union([par_id[s]["box"] for s in ids])
        assert all(abs(a - b) <= EPS for a, b in zip(got, zone)), \
            f"{mid} « {quoi} » : {got} au lieu de {zone}"


@pytest.mark.parametrize("mid", sorted(ZONES_DEDANS))
def test_les_zones_a_plusieurs_exemplaires(mid):
    """« 1-2 attaques », « 5-7 lignes » : le premier exemplaire est posé, le
    second est un ÉLÉMENT ajoutable — et les deux ensemble tiennent dans la
    zone de la spec."""
    m = MO.model(mid)
    par_id = _par_id(m)
    par_id.update({s["id"]: s for s in _elem_slots(m)})
    for quoi, poses, ajoutables, zone in ZONES_DEDANS[mid]:
        for sid in poses + ajoutables:
            assert sid in par_id, f"{mid}: slot {sid!r} absent pour « {quoi} »"
        got = _union([par_id[s]["box"] for s in poses])
        gotp = _union([par_id[s]["box"] for s in poses + ajoutables])
        for nom, u in (("posés", got), ("posés+ajoutables", gotp)):
            assert u[0] >= zone[0] - EPS and u[1] >= zone[1] - EPS \
                and u[0] + u[2] <= zone[0] + zone[2] + EPS \
                and u[1] + u[3] <= zone[1] + zone[3] + EPS, \
                f"{mid} « {quoi} » ({nom}) : {u} sort de {zone}"


@pytest.mark.parametrize("mid", sorted(ZONES_ORIGINE))
def test_les_zones_sans_dimension_epinglent_leur_coin(mid):
    par_id = _par_id(MO.model(mid))
    for quoi, ids, coin in ZONES_ORIGINE[mid]:
        for sid in ids:
            assert sid in par_id, f"{mid}: slot {sid!r} absent pour « {quoi} »"
        u = _union([par_id[s]["box"] for s in ids])
        assert abs(u[0] - coin[0]) <= EPS and abs(u[1] - coin[1]) <= EPS, \
            f"{mid} « {quoi} » : coin ({u[0]}, {u[1]}) au lieu de {coin}"


@pytest.mark.parametrize("mid", IDS)
def test_deux_slots_ne_se_chevauchent_pas(mid):
    """Sur une même face. Deux slots superposés, c'est du texte perdu sous du
    texte — et personne ne voit lequel."""
    m = MO.model(mid)
    slots = _slots(m)
    for i, a in enumerate(slots):
        for b in slots[i + 1:]:
            if a["side"] != b["side"] and "both" not in (a["side"], b["side"]):
                continue
            aire = _chevauche(a["box"], b["box"])
            assert aire == 0.0, \
                f"{mid}: {a['id']} et {b['id']} se chevauchent ({aire:.2f} mm²)"


def test_ajouter_deux_fois_le_meme_element_ne_perd_aucun_slot():
    """Les slots d'un élément portent des identifiants FIXES. Poser deux fois
    « 2e attaque » n'en perd donc aucun, mais seulement parce que le
    normaliseur du document RENOMME les doublons (`norm_slots` : `att2cout`,
    `att2cout2`…) au lieu d'en écraser un. C'est cette propriété-là qui rend
    les identifiants fixes acceptables — on l'épingle plutôt que d'y croire.
    (L'écran de la 3b posera des noms lisibles ; le filet, lui, est ici.)"""
    for mid in IDS:
        m = MO.model(mid)
        for e in m["elements"]:
            avant = m["type"]["slots"] + e["slots"] + copy.deepcopy(e["slots"])
            apres = TY.norm_slots(avant)
            assert len(apres) == len(avant), \
                f"{mid}/{e['id']}: {len(avant) - len(apres)} slot(s) perdu(s)"
            ids = [s["id"] for s in apres]
            assert len(set(ids)) == len(ids), f"{mid}/{e['id']}: {ids}"


@pytest.mark.parametrize("mid", IDS)
def test_un_element_atterrit_dans_un_espace_libre(mid):
    """Un preset ajoutable qui tombe SUR un slot posé est un cadeau empoisonné
    : l'utilisateur ne voit qu'un texte, et croit que l'ajout a échoué."""
    m = MO.model(mid)
    for e in m["elements"]:
        for k in ("id", "label", "hint", "slots"):
            assert k in e, f"{mid}: élément sans {k!r}"
        assert e["slots"], f"{mid}/{e['id']}: élément sans slot"
        for es in e["slots"]:
            for s in _slots(m):
                if es["side"] != s["side"] and \
                        "both" not in (es["side"], s["side"]):
                    continue
                aire = _chevauche(es["box"], s["box"])
                assert aire == 0.0, \
                    f"{mid}: l'élément {e['id']} ({es['id']}) tombe sur " \
                    f"{s['id']} ({aire:.2f} mm²)"


# ═══════════════════ 3. les polices : aucun repli muet ══════════════════════

def _fontes_chargeables() -> list[str]:
    """La liste que `mod-type.js` sait CHARGER, extraite du fichier — pas une
    liste recopiée ici. Une police retirée du lab fait rougir la suite."""
    src = JS_TYPE.read_text(encoding="utf-8")
    m = re.search(r"const FONTS_LOCAL = \[(.*?)\]\.map\(", src, re.S)
    assert m, "bloc FONTS_LOCAL introuvable dans mod-type.js"
    ids = re.findall(r'\[\s*"([A-Za-z0-9]+)"\s*,', m.group(1))
    assert len(ids) >= 20, ids
    return ids


def test_le_lab_charge_bien_les_polices_du_backend():
    """Le garde-fou du garde-fou : la liste extraite du JS est celle du
    backend (`FONT_META`). Sinon le pin de police ci-dessous jugerait contre
    une liste morte."""
    assert set(_fontes_chargeables()) == set(TY.FONT_META)


@pytest.mark.parametrize("mid", IDS)
def test_les_polices_sont_chargeables_et_les_replis_nommes(mid):
    """Décision 2 du plan : n'employer QUE des polices que `ensureFonts` sait
    charger, et NOMMER le repli de chaque police citée par la spec."""
    ok = set(_fontes_chargeables())
    m = MO.model(mid)
    employees = {s["font"] for s in _slots(m) + _elem_slots(m)}
    for f in employees:
        assert f in ok, f"{mid}: police {f!r} absente du lab"
    notes = m["fonts_note"]
    assert isinstance(notes, list) and notes, f"{mid}: fonts_note vide"
    declarees = set()
    for n in notes:
        for k in ("spec", "police", "pourquoi"):
            assert k in n, f"{mid}: fonts_note sans {k!r}"
        assert n["police"] in ok, \
            f"{mid}: repli {n['police']!r} introuvable au lab"
        assert str(n["spec"]).strip() and str(n["pourquoi"]).strip()
        declarees.add(n["police"])
    manquantes = employees - declarees
    assert not manquantes, \
        f"{mid}: police(s) employée(s) sans note de repli : {sorted(manquantes)}"


@pytest.mark.parametrize("mid", IDS)
def test_les_textes_par_defaut_sont_ecrivables(mid):
    """Un glyphe absent est remplacé EN SILENCE par le navigateur (le piège
    documenté par P3). Deux verrous : le répertoire employé se limite à
    l'ASCII imprimable plus le répertoire français MESURÉ, et aucune police
    citée ne manque un caractère de ses propres textes."""
    permis = set(TY.FR_PROBE)
    miss = TY.font_missing_map()
    # LE CONTRÔLE EST-IL SEULEMENT BRANCHÉ ? Sans ces deux lignes, un scan de
    # polices qui rendrait une liste vide (mauvais dossier dans une appli
    # installée) ferait passer ce test SANS RIEN MESURER. `PolandKaito.otf`
    # est le cas connu de P3 : 114 points de code, pas de « é ».
    assert len(miss) == len(TY.FONT_META), miss
    assert "é" in (miss.get("PolandKaito") or set()), \
        "le relevé de cmap ne mesure plus rien"
    m = MO.model(mid)
    for s in _slots(m) + _elem_slots(m):
        texte = TY.apply_case(s["text"], s["caps"])
        for ch in texte:
            assert ch in permis or (32 <= ord(ch) < 127), \
                f"{mid}/{s['id']}: caractère exotique {ch!r} ({hex(ord(ch))})"
        absents = miss.get(s["font"])
        if absents:
            assert not TY.missing_chars(texte, absents), \
                f"{mid}/{s['id']}: {s['font']} ne sait pas écrire " \
                f"{TY.missing_chars(texte, absents)}"


# ═══════════════════ 4. la plaque, la palette, la matière ═══════════════════

@pytest.mark.parametrize("mid", IDS)
def test_une_plaque_a_toujours_un_texte(mid):
    """Leçon T1 : la plaque vit dans `drawSlot`, sous la garde `if
    (!m.empty)`. Un slot sans texte ne peint AUCUNE plaque — un cartouche
    « toujours visible » doit donc porter un texte par défaut."""
    m = MO.model(mid)
    for s in _slots(m) + _elem_slots(m):
        if s["plate_color"] is None:
            continue
        assert s["text"].strip(), \
            f"{mid}/{s['id']}: plaque {s['plate_color']} sur un slot VIDE " \
            "— elle ne sera jamais peinte"


@pytest.mark.parametrize("mid", IDS)
def test_la_palette_est_une_lecture_du_modele(mid):
    """`palette` n'est pas une quatrième table de couleurs : c'est ce que le
    modèle EMPLOIE, relu. Une palette décorative mentirait au premier
    changement d'encre."""
    m = MO.model(mid)
    pal = m["palette"]
    assert set(pal) == {"ink", "plate", "paper"}, sorted(pal)
    encres = [s["color"] for s in _slots(m)]
    assert pal["ink"] in encres, f"{mid}: encre {pal['ink']} employée nulle part"
    plaques = [s["plate_color"] for s in _slots(m) if s["plate_color"]]
    if plaques:
        assert pal["plate"] in plaques
    else:
        assert pal["plate"] is None
    assert pal["paper"] == m["texture"]["tint"]


def test_la_palette_suit_lencre_dominante():
    """La preuve que la lecture est une LECTURE : on change les encres d'un
    modèle de laboratoire, la palette suit."""
    faux = {
        "type": {"slots": [
            TY.norm_slot({"id": "a", "color": "#112233"}),
            TY.norm_slot({"id": "b", "color": "#112233",
                          "plate_color": "#aabbcc"}),
            TY.norm_slot({"id": "c", "color": "#ffeedd"}),
        ]},
        "texture": {"tint": "#0f0f0f"},
    }
    assert MO.palette_of(faux) == {"ink": "#112233", "plate": "#aabbcc",
                                   "paper": "#0f0f0f"}


def _catalogue_matieres() -> tuple[set, set]:
    src = JS_TEXTURE.read_text(encoding="utf-8")
    m = re.search(r"CF-TEXTURE-CATALOG-BEGIN(.*?)CF-TEXTURE-CATALOG-END",
                  src, re.S)
    assert m, "bloc CF-TEXTURE-CATALOG introuvable"
    mats = set(re.findall(r'\{\s*id:\s*"([a-z0-9_]+)"', m.group(1)))
    o = re.search(r"const OVERS = \[(.*?)\];", src, re.S)
    assert o, "bloc OVERS introuvable"
    overs = set(re.findall(r'\{\s*id:\s*"([a-z0-9_]+)"', o.group(1)))
    assert len(mats) > 20 and len(overs) > 5, (len(mats), len(overs))
    return mats, overs


@pytest.mark.parametrize("mid", IDS)
def test_la_matiere_et_la_finition_existent(mid):
    """Le support vient du catalogue de l'écran (P6, le backend n'en a pas de
    miroir : il ne dessine pas) et la finition de la table de P8."""
    mats, overs = _catalogue_matieres()
    m = MO.model(mid)
    t = m["texture"]
    assert t["paper"] in mats, f"{mid}: matière {t['paper']!r} inconnue"
    assert t["over"] in overs, f"{mid}: effet {t['over']!r} inconnu"
    assert re.fullmatch(r"#[0-9a-f]{6}", t["tint"]), t["tint"]
    assert m["finish"] in GL.FINISHES, f"{mid}: finition {m['finish']!r}"


# ═════════════ 5. les signatures §6.2 que la spec écrit en toutes lettres ═══

def test_les_signatures_ecrites_de_la_spec():
    """Quatre phrases de la spec qui se MESURENT sur la donnée."""
    par = {mid: _par_id(MO.model(mid)) for mid in IDS}
    # « bandeau titre (55x8, rectangle, PAS d'ellipse) »
    assert par["duel"]["titre"]["plate_radius"] == 0.0
    assert par["duel"]["titre"]["plate_color"] is not None
    # « valeurs tabulaires à droite » — une chasse FIXE, mesurable
    assert par["duel"]["val1"]["font"] == "JetBrainsMono"
    assert par["duel"]["val1"]["align"] == "right"
    # « nom capitales », « étoiles ALIGNÉES À DROITE », « attribut ⌀7 »
    assert par["monstre"]["nom"]["caps"] == "upper"
    assert par["monstre"]["etoiles"]["align"] == "right"
    at = par["monstre"]["attribut"]
    assert at["box"][2] == at["box"][3] == 7.0
    assert at["plate_radius"] == 3.5, "⌀7 : le rayon fait la moitié du côté"
    # « règles romain + ambiance italique »
    assert par["arcane"]["regles"]["italic"] is False
    assert par["arcane"]["ambiance"]["italic"] is True
    # « cartouche nom (capitales espacées) »
    assert par["gravee"]["nom"]["caps"] == "upper"
    assert par["gravee"]["nom"]["track"] > 0
    # « verso à tableau de stats saisonnières » : le SEUL archétype à verso
    dos = [s["id"] for s in _slots(MO.model("legende")) if s["side"] == "back"]
    assert len(dos) >= 5, dos
    for mid in IDS:
        if mid == "legende":
            continue
        assert not [s for s in _slots(MO.model(mid)) if s["side"] == "back"], \
            f"{mid}: la spec ne lui donne pas de verso propre"


@pytest.mark.parametrize("mid", IDS)
def test_les_sept_passent_le_juge_de_p3(mid):
    """Le JUGE de la pièce 03 (`type.layout`), sur la géométrie réelle du
    poker à 300 DPI. Sans encombrement mesuré par le navigateur, il tranche
    sur la BOÎTE — c'est donc le verdict le plus sévère, et les sept mises en
    page le passent, à UNE exception nommée : le bandeau de nom de
    « légende », qui TOUCHE le trait de coupe parce que la spec le veut à
    fond perdu (§6.2 : « 0,74 (63 x 10) »). Dans l'application, ce même juge
    tranche sur l'ENCRE (`ink_inside_safe`), et un nom centré reste loin du
    bord ; ici, on épingle l'exception pour qu'une zone déplacée par mégarde
    ne se glisse pas à côté d'elle.

    Aucun bloc sous son plancher de lisibilité, aucun glyphe manquant.

    ATTENTION AU VERDICT VIDE : `under_read` se remplit à partir de `posed`,
    le corps RÉELLEMENT COMPOSÉ, que seul le navigateur mesure. Sans `posed`,
    la liste est vide PAR CONSTRUCTION et n'affirme rien. Le contrôle qui
    porte ici est donc STATIQUE : `size_pt >= read_pt`, c'est-à-dire qu'aucun
    bloc ne PART déjà sous son plancher de lisibilité (l'ajustement
    automatique ne fait que descendre)."""
    g = CT.geom("poker_eu", 300)
    m = MO.model(mid)
    slots = m["type"]["slots"]
    rep = TY.layout(g, slots, texts={s["id"]: s["text"] for s in slots})
    s = rep["summary"]
    attendu = ["nom"] if mid == "legende" else []
    assert s["outside_safe"] == attendu, \
        f"{mid}: hors zone sûre {s['outside_safe']} (attendu {attendu})"
    assert s["missing_glyphs"] == [], s["missing_glyphs"]
    assert s["under_read"] == [], s["under_read"]
    assert s["n"] == len(slots)
    for sl in slots + _elem_slots(m):
        assert sl["read_pt"] > 0, f"{mid}/{sl['id']}: aucun plancher déclaré"
        assert sl["size_pt"] >= sl["read_pt"], \
            f"{mid}/{sl['id']}: corps {sl['size_pt']} pt sous le plancher " \
            f"de lisibilité {sl['read_pt']} pt — il ne se lira jamais"
        assert sl["min_pt"] <= sl["size_pt"]


def test_le_gabarit_declare_ne_peut_pas_effacer_une_mise_en_page():
    """`type.preset` reçoit l'ARCHÉTYPE (« dernier gabarit appliqué » : c'est
    lui), pas l'un des quatre gabarits de P3. Ce n'est sans danger que parce
    que l'écran REPLIE un identifiant inconnu sur « champion » et ne re-sème
    JAMAIS un document qui porte déjà des slots — deux propriétés du source,
    épinglées ici plutôt que supposées."""
    for mid in IDS:
        assert MO.model(mid)["type"]["preset"] == mid
    src = JS_TYPE.read_text(encoding="utf-8")
    assert re.search(r"const p = PRESETS\[pid\] \|\| PRESETS\.champion;", src)
    assert re.search(r'if \(a\.length \|\| CF\.get\("type\.seeded", false\)\)',
                     src)


# ═══════════════════════ 6. GET /api/cards/models ═══════════════════════════

def test_get_models_sert_les_sept():
    r = _api("GET", "/api/cards/models")
    assert r.status_code == 200, r.text
    body = r.json()
    usine = [m for m in body["models"] if not m.get("custom")]
    assert [m["id"] for m in usine] == list(IDS)
    assert body["usine"] == 7
    for m in usine:
        assert m["format"] == "poker_eu"
        assert m["type"]["slots"]


def test_les_routes_de_modeles_passent_avant_le_joker():
    """`/models` est un segment : sans montage AVANT `core`, il tomberait dans
    `/{did}` et répondrait « identifiant de deck invalide »."""
    from app.main import app
    chemins = [p for p in app.openapi().get("paths", {})
               if p.startswith("/api/cards")]
    assert "/api/cards/models" in chemins
    assert chemins.index("/api/cards/models") < chemins.index("/api/cards/{did}")
    assert "/api/cards/decks/{did}/duplicate" in chemins


def test_get_models_liste_les_perso():
    """Et l'identifiant est LE NOM DU FICHIER : le fichier ci-dessous se
    déclare « superstar » dans son contenu — s'il était cru, il masquerait un
    modèle d'usine dans la galerie et l'instanciation servirait le mauvais."""
    d = MO.models_root()
    (d / "zz_test_perso.json").write_text(json.dumps({
        "id": "superstar", "label": "Mon modèle", "hint": "essai",
        "format": "poker_eu", "frame": {}, "type": {"slots": []},
        "texture": {}, "finish": "mat", "elements": [],
    }, ensure_ascii=False), encoding="utf-8")
    try:
        body = _api("GET", "/api/cards/models").json()
        perso = [m for m in body["models"] if m.get("custom")]
        assert [m["id"] for m in perso] == ["zz_test_perso"], perso
        assert perso[0]["label"] == "Mon modèle"
        assert body["perso"] == 1
        usine = [m for m in body["models"] if m["id"] == "superstar"]
        assert len(usine) == 1 and usine[0]["custom"] is False
        assert MO.model("superstar")["label"] == MO.MODELS["superstar"]["label"]
    finally:
        (d / "zz_test_perso.json").unlink()


def test_un_fichier_perso_ne_peut_pas_usurper_un_modele_dusine():
    """Le nom de FICHIER fait l'identifiant — et `superstar.json` déposé à la
    main dans le dossier rendait donc DEUX lignes au même id : la galerie
    héritait d'un doublon de clé, et la perso était morte-née (l'usine gagne
    toujours à l'instanciation). Elle est désormais listée sous un id qui ne
    peut pas collisionner, et SIGNALÉE — avec la raison et le geste à faire."""
    d = MO.models_root()
    (d / "superstar.json").write_text(json.dumps({
        "label": "Ma superstar à moi", "format": "poker_eu", "frame": {},
        "type": {"slots": []}, "texture": {}, "finish": "mat",
    }, ensure_ascii=False), encoding="utf-8")
    try:
        body = _api("GET", "/api/cards/models").json()
        ids = [m["id"] for m in body["models"]]
        assert len(ids) == len(set(ids)), f"identifiants en double : {ids}"
        usine = [m for m in body["models"] if m["id"] == "superstar"]
        assert len(usine) == 1 and usine[0]["custom"] is False
        intrus = [m for m in body["models"]
                  if m.get("fichier") == "superstar.json"]
        assert len(intrus) == 1, body["models"]
        assert intrus[0]["id"] != "superstar"
        assert intrus[0]["illisible"] is True
        assert "usine" in intrus[0]["error"] or "renomm" in intrus[0]["error"]
        # ... et l'instanciation sert toujours l'usine
        doc = _api("POST", "/api/cards/decks",
                   json={"model": "superstar"}).json()["deck"]
        assert doc["frame"] == FR.archetype_frame("superstar")
        assert doc["type"]["slots"]
    finally:
        (d / "superstar.json").unlink()


def test_un_modele_perso_illisible_est_liste_pas_un_500():
    d = MO.models_root()
    (d / "zz_casse.json").write_text("{ceci n'est pas du JSON",
                                     encoding="utf-8")
    try:
        r = _api("GET", "/api/cards/models")
        assert r.status_code == 200, r.text
        casse = [m for m in r.json()["models"] if m.get("illisible")]
        assert len(casse) == 1, casse
        assert casse[0]["fichier"] == "zz_casse.json"
        assert casse[0]["error"]
        assert casse[0]["custom"] is True
    finally:
        (d / "zz_casse.json").unlink()


# ═══════════════════════ 7. instancier un modèle ════════════════════════════

def test_instancier_superstar():
    r = _api("POST", "/api/cards/decks", json={"model": "superstar"})
    assert r.status_code == 200, r.text
    did = r.json()["deck"]["id"]
    doc = _api("GET", f"/api/cards/{did}").json()["deck"]
    m = MO.model("superstar")
    assert doc["frame"] == FR.archetype_frame("superstar")
    assert doc["type"]["slots"] == m["type"]["slots"]
    assert doc["type"]["seeded"] is True
    assert doc["format"]["fmt"] == "poker_eu"
    assert doc["texture"]["paper"] == m["texture"]["paper"]
    assert doc["gltf"]["finish"] == m["finish"]
    assert doc["name"] == m["label"]
    # ... et le document est un document ORDINAIRE : le partitionnement de
    # CORE ne laisse passer aucune clé de plus (le modèle est une GRAINE, pas
    # un lien).
    assert "model" not in doc and "modele" not in doc
    assert set(doc) == {"v", "id", "name", "format", "created", "updated"} \
        | set(CT.MODULE_IDS)
    # les slots du modèle traversent `norm_slots` sans changer : la graine est
    # de la donnée PROPRE, pas de la donnée réparable.
    assert TY.norm_slots(doc["type"]["slots"]) == doc["type"]["slots"]


@pytest.mark.parametrize("mid", IDS)
def test_les_sept_sinstancient(mid):
    r = _api("POST", "/api/cards/decks", json={"model": mid,
                                               "name": f"essai {mid}"})
    assert r.status_code == 200, r.text
    doc = r.json()["deck"]
    assert doc["name"] == f"essai {mid}"
    assert doc["frame"]["family"] == MO.model(mid)["frame"]["family"]
    assert len(doc["type"]["slots"]) == len(MO.model(mid)["type"]["slots"])


def test_modele_inconnu_404_nomme():
    r = _api("POST", "/api/cards/decks", json={"model": "inconnu"})
    assert r.status_code == 404, r.text
    detail = r.json()["detail"]
    assert "inconnu" in detail, detail
    assert re.search(r"[éèêàâîôû]", detail), f"message en français : {detail}"


def test_lecho_du_modele_inconnu_est_borne():
    """Un message d'erreur RECOPIE ce que le client a envoyé : il se borne,
    comme tous les autres échos du lab. Sans quoi 3 000 caractères, du
    balisage ou un renversement de sens de lecture (U+202E) repartent tels
    quels dans l'écran qui les affiche."""
    long = "M" * 3000
    r = _api("POST", "/api/cards/decks", json={"model": long})
    assert r.status_code == 404
    assert len(r.json()["detail"]) < 200, len(r.json()["detail"])
    # ECHAPPES, jamais bruts (R13) : un octet NUL dans un source fait
    # passer le fichier pour du binaire aux yeux de tout outil textuel.
    for hostile in ("<img src=x onerror=alert(1)>", "a\u202eb", "\x00z"):
        rr = _api("POST", "/api/cards/decks", json={"model": hostile})
        assert rr.status_code in (400, 404), rr.text
        assert len(rr.json()["detail"]) < 200


def test_linstanciation_copie_en_profondeur():
    """POISON TEST (F9). La table des modèles est un objet de MODULE : une
    instanciation qui rendrait ses sous-dictionnaires laisserait le premier
    deck modifié contaminer TOUS les suivants, dans le même processus, sans
    rien casser tout de suite."""
    avant = FR.archetype_frame("monstre")["window"]["x"]
    d1 = MO.instancier("monstre")
    d1["frame"]["window"]["x"] = 999.0
    d1["type"]["slots"][0]["text"] = "poison"
    d2 = MO.instancier("monstre")
    assert d2["frame"]["window"]["x"] == avant
    assert d2["type"]["slots"][0]["text"] != "poison"
    assert MO.MODELS["monstre"]["frame"]["window"]["x"] == avant
    assert FR.ARCHETYPE_FRAMES["monstre"]["window"]["x"] == avant
    # la porte d'entrée publique aussi
    m = MO.model("monstre")
    m["frame"]["window"]["x"] = -1.0
    m["type"]["slots"][0]["text"] = "poison"
    assert MO.model("monstre")["frame"]["window"]["x"] == avant
    assert MO.model("monstre")["type"]["slots"][0]["text"] != "poison"


# ═══════════════════════════ 8. duplication ═════════════════════════════════

def test_dupliquer_copie_tout():
    """Une duplication copie TOUT — illustrations comprises. C'est
    « enregistrer comme modèle » qui les exclut (§6.4)."""
    did = _api("POST", "/api/cards/decks",
               json={"model": "duel", "name": "Original"}).json()["deck"]["id"]
    d = CT.deck_dir(did)
    (d / "texture").mkdir(exist_ok=True)
    (d / "texture" / "paper.png").write_bytes(b"\x89PNG-faux")
    _api("PATCH", f"/api/cards/{did}",
         json={"face": {"src": "local:abc", "default_art": "face_x"}})
    r = _api("POST", f"/api/cards/decks/{did}/duplicate")
    assert r.status_code == 200, r.text
    copie = r.json()["deck"]
    assert copie["id"] != did and CT.is_valid_did(copie["id"])
    assert copie["name"] == "copie de Original"
    src = _api("GET", f"/api/cards/{did}").json()["deck"]
    for k in ("format", "frame", "type", "texture", "face", "gltf"):
        assert copie[k] == src[k], k
    assert copie["face"]["src"] == "local:abc", "la duplication garde l'image"
    d2 = CT.deck_dir(copie["id"])
    assert (d2 / "texture" / "paper.png").read_bytes() == b"\x89PNG-faux", \
        "les fichiers deck-locaux ne sont pas copiés"
    # l'original n'a pas bougé
    assert (d / "texture" / "paper.png").is_file()
    assert _api("GET", f"/api/cards/{did}").json()["deck"]["name"] == "Original"


def test_dupliquer_ce_qui_nexiste_pas():
    assert _api("POST", "/api/cards/decks/deck_00000000/duplicate"
                ).status_code == 404
    assert _api("POST", "/api/cards/decks/pas-un-did/duplicate"
                ).status_code == 400


# ═════════════════ 9. enregistrer comme modèle (perso) ══════════════════════

def test_enregistrer_comme_modele_sans_les_illustrations():
    did = _api("POST", "/api/cards/decks",
               json={"model": "gravee"}).json()["deck"]["id"]
    _api("PATCH", f"/api/cards/{did}", json={
        "face": {"src": "local:cle-secrete", "default_art": "face_a_b_c",
                 "fit": "cover", "x": 3.5, "seeded": True},
        "texture": {"paper": "__import", "custom": "paper.png",
                    "tint": "#f4ead6", "over": "grain"},
    })
    r = _api("POST", "/api/cards/models",
             json={"did": did, "name": "Mon Deck Gravé !"})
    assert r.status_code == 200, r.text
    m = r.json()["model"]
    assert m["custom"] is True
    assert m["id"] == "mon-deck-grave"
    fichier = MO.models_root() / "mon-deck-grave.json"
    assert fichier.is_file()
    brut = fichier.read_text(encoding="utf-8")
    # AUCUNE trace d'illustration : ni la clé locale, ni l'identifiant de
    # dessin, ni le papier importé (le fichier, lui, reste dans le deck).
    assert "local:" not in brut and "cle-secrete" not in brut
    assert "face_a_b_c" not in brut
    assert "__import" not in brut and "paper.png" not in brut
    disque = json.loads(brut)
    assert "face" not in disque
    assert disque["texture"]["paper"] != "__import"
    # ... mais les RÉGLAGES sont là, textes des slots compris (un slot sans
    # texte ne peindrait plus sa plaque — leçon T1).
    assert disque["frame"] == FR.archetype_frame("gravee")
    assert disque["type"]["slots"] == MO.model("gravee")["type"]["slots"]
    assert any(s["text"].strip() for s in disque["type"]["slots"])
    assert disque["finish"] == MO.model("gravee")["finish"]
    # re-listé, puis RE-INSTANCIABLE
    ids = [x["id"] for x in _api("GET", "/api/cards/models").json()["models"]]
    assert "mon-deck-grave" in ids
    r2 = _api("POST", "/api/cards/decks", json={"model": "mon-deck-grave"})
    assert r2.status_code == 200, r2.text
    neuf = r2.json()["deck"]
    assert neuf["frame"] == FR.archetype_frame("gravee")
    assert neuf["type"]["slots"] == MO.model("gravee")["type"]["slots"]
    assert not neuf["face"].get("src")
    fichier.unlink()


def test_le_cadre_aussi_est_filtre_de_ses_images():
    """`texture` était filtrée de son papier importé, `frame` ne l'était pas —
    et le cadre est justement là où §6.2ter va poser le VERSO PERSONNALISÉ
    (une image importée, « SAUVÉE dans les modèles de deck »). Le sous-arbre
    est donc passé par une LISTE BLANCHE : les clés que P2 déclare, et rien
    d'autre. Une référence d'image plantée par l'autosave ordinaire ne peut
    pas partir dans un fichier de modèle."""
    did = _api("POST", "/api/cards/decks",
               json={"model": "monstre"}).json()["deck"]["id"]
    cadre = dict(FR.archetype_frame("monstre"))
    cadre["back_image"] = "local:VERSO-SECRET"
    cadre["cle_inventee"] = {"src": "local:AUTRE-SECRET"}
    _api("PATCH", f"/api/cards/{did}", json={"frame": cadre})
    assert _api("GET", f"/api/cards/{did}").json()["deck"]["frame"] \
        .get("back_image") == "local:VERSO-SECRET", "le deck, lui, la garde"
    r = _api("POST", "/api/cards/models", json={"did": did, "name": "Filtré"})
    assert r.status_code == 200, r.text
    p = MO.models_root() / f"{r.json()['model']['id']}.json"
    try:
        brut = p.read_text(encoding="utf-8")
        assert "VERSO-SECRET" not in brut and "AUTRE-SECRET" not in brut
        assert "back_image" not in brut and "cle_inventee" not in brut
        disque = json.loads(brut)
        # ... et le cadre reste COMPLET : le filtre enlève, il n'ampute pas.
        assert set(disque["frame"]) <= set(FR.archetype_frame("monstre")) \
            | {"art_window"}
        assert disque["frame"]["family"] == "runic"
        assert disque["frame"]["window"] == \
            FR.archetype_frame("monstre")["window"]
    finally:
        p.unlink()


def test_deux_enregistrements_simultanes_ne_secrasent_pas():
    """LA COURSE DU DOUBLE-CLIC. Chercher un nom libre puis l'écrire laisse
    une fenêtre entre les deux : six appels lancés ensemble rendaient trois
    fois le MÊME identifiant — deux modèles écrasés en silence — et des
    erreurs de partage de fichier. Le nom se réserve maintenant par CRÉATION
    EXCLUSIVE : c'est le système de fichiers qui tranche, pas un `exists()`
    périmé de quelques microsecondes."""
    did = _api("POST", "/api/cards/decks",
               json={"model": "arcane"}).json()["deck"]["id"]
    n = 6
    reps = _api_parallele(n, "POST", "/api/cards/models",
                          json={"did": did, "name": "Course"})
    ids = []
    try:
        for r in reps:
            assert r.status_code == 200, r.text
            ids.append(r.json()["model"]["id"])
        assert len(set(ids)) == n, f"identifiants écrasés : {sorted(ids)}"
        for i in set(ids):
            p = MO.models_root() / f"{i}.json"
            assert p.is_file(), i
            assert json.loads(p.read_text(encoding="utf-8"))["type"]["slots"]
        listes = [m["id"] for m in
                  _api("GET", "/api/cards/models").json()["models"]]
        assert len(listes) == len(set(listes))
        assert set(ids) <= set(listes)
    finally:
        for i in set(ids):
            p = MO.models_root() / f"{i}.json"
            if p.is_file():
                p.unlink()


def test_le_slug_ne_recouvre_jamais_un_voisin():
    did = _api("POST", "/api/cards/decks",
               json={"model": "duel"}).json()["deck"]["id"]
    a = _api("POST", "/api/cards/models",
             json={"did": did, "name": "Même nom"}).json()["model"]
    b = _api("POST", "/api/cards/models",
             json={"did": did, "name": "Même nom"}).json()["model"]
    # un modèle d'usine ne peut pas être écrasé par un perso
    c = _api("POST", "/api/cards/models",
             json={"did": did, "name": "superstar"}).json()["model"]
    try:
        assert a["id"] != b["id"], "collision : le second a écrasé le premier"
        assert c["id"] != "superstar"
        assert (MO.models_root() / f"{a['id']}.json").is_file()
        assert (MO.models_root() / f"{b['id']}.json").is_file()
        usine = [m for m in _api("GET", "/api/cards/models").json()["models"]
                 if m["id"] == "superstar"]
        assert len(usine) == 1 and usine[0]["custom"] is False
    finally:
        for x in (a, b, c):
            p = MO.models_root() / f"{x['id']}.json"
            if p.is_file():
                p.unlink()


def test_enregistrer_un_deck_qui_nexiste_pas():
    r = _api("POST", "/api/cards/models",
             json={"did": "deck_00000000", "name": "x"})
    assert r.status_code == 404, r.text
    assert re.search(r"[éèêàâîôû]", r.json()["detail"])


def test_un_modele_perso_est_valide_comme_un_corps_client():
    """Un fichier perso vient du DISQUE : il a pu être écrit à la main, ou par
    une version antérieure. Ses sous-arbres passent donc par les mêmes
    normaliseurs que le reste — le cadre par la liste blanche de P2, la
    matière par le filtre d'import, les slots par `norm_slots` — et un
    « élément » sans slots n'est pas un élément."""
    d = MO.models_root()
    (d / "zz_bancal.json").write_text(json.dumps({
        "label": "Bancal", "format": "carre_de_nulle_part",
        "frame": {"family": "runic", "back_image": "local:FUITE",
                  "inconnu": 1},
        "type": {"slots": [{"id": "T!T", "box": [4, 4, 9999, 9], "size_pt": 999,
                            "color": "bleu", "plate_alpha": 5}]},
        "texture": {"paper": "__import", "custom": "paper.png"},
        "finish": "inexistante",
        "elements": [{"id": "vide", "label": "Vide"},
                     {"id": "bon", "label": "Bon", "slots": [{"id": "x"}]},
                     "pas un objet"],
    }, ensure_ascii=False), encoding="utf-8")
    try:
        m = [x for x in _api("GET", "/api/cards/models").json()["models"]
             if x["id"] == "zz_bancal"][0]
        assert not m.get("illisible"), m
        assert m["format"] == "poker_eu"          # format inconnu -> défaut
        assert m["finish"] == "mat"               # finition inconnue -> défaut
        assert "back_image" not in m["frame"] and "inconnu" not in m["frame"]
        assert m["frame"]["family"] == "runic"
        assert m["texture"]["paper"] != "__import" and "custom" not in m["texture"]
        s = m["type"]["slots"][0]
        assert s == TY.norm_slot(s), "slots non normalisés"
        assert s["box"][2] <= 500 and s["size_pt"] <= 400
        assert [e["id"] for e in m["elements"]] == ["bon"], m["elements"]
        # ... et il s'instancie sans rien casser
        doc = _api("POST", "/api/cards/decks",
                   json={"model": "zz_bancal"}).json()["deck"]
        assert doc["format"]["fmt"] == "poker_eu"
        assert doc["type"]["slots"] == m["type"]["slots"]
    finally:
        (d / "zz_bancal.json").unlink()


def test_un_modele_perso_vide_ne_bloque_pas_le_semis():
    """`seeded: true` empêche l'écran de reposer un gabarit par-dessus les
    slots du modèle. Posé en dur, il condamnait un modèle SANS slots à un
    document éternellement vide : plus de modèle, plus de gabarit, rien."""
    d = MO.models_root()
    (d / "zz_vide.json").write_text(json.dumps({
        "label": "Vide", "format": "poker_eu", "frame": {},
        "type": {"slots": []}, "texture": {}, "finish": "mat",
    }, ensure_ascii=False), encoding="utf-8")
    try:
        doc = _api("POST", "/api/cards/decks",
                   json={"model": "zz_vide"}).json()["deck"]
        assert doc["type"]["slots"] == []
        assert doc["type"]["seeded"] is False, \
            "un modèle sans slots doit laisser l'écran semer son gabarit"
        plein = _api("POST", "/api/cards/decks",
                     json={"model": "gravee"}).json()["deck"]
        assert plein["type"]["seeded"] is True
    finally:
        (d / "zz_vide.json").unlink()


def test_le_catalogue_dit_combien_de_perso_il_a_TROUVES():
    """Le plafond de listage tronquait SANS LE DIRE : un utilisateur aux 500
    modèles en voyait 400 et cherchait les autres du côté de l'écran.

    LE PLAFOND EST ABAISSÉ POUR DE VRAI le temps du test. Sans cela, le
    contrôle ne mesurait rien : avec cinq modèles sur un plafond de 400, un
    total FAUX (« autant que de lignes ») aurait été indiscernable du vrai."""
    body = _api("GET", "/api/cards/models").json()
    for k in ("usine", "perso", "perso_total", "perso_tronque", "n"):
        assert k in body, sorted(body)
    assert body["usine"] == 7
    assert body["n"] == body["usine"] + body["perso"]
    assert body["perso_tronque"] is False

    d = MO.models_root()
    faits = []
    plafond = MO.PERSO_MAX
    try:
        for i in range(5):
            p = d / f"zz_plafond{i}.json"
            p.write_text(json.dumps({"label": f"P{i}", "type": {"slots": []}}),
                         encoding="utf-8")
            faits.append(p)
        MO.PERSO_MAX = 3
        body = _api("GET", "/api/cards/models").json()
        assert body["perso"] == 3, body["perso"]
        assert body["perso_total"] == 5, body["perso_total"]
        assert body["perso_tronque"] is True
        assert body["n"] == body["usine"] + body["perso"]
    finally:
        MO.PERSO_MAX = plafond
        for p in faits:
            p.unlink()


# ══════════════════════════ 10. jamais de 500 ═══════════════════════════════

def test_jamais_500_sur_un_corps_mal_forme():
    """Spec §2.5. Un corps hostile n'a pas le droit de faire tomber le lab."""
    did = _api("POST", "/api/cards/decks", json={}).json()["deck"]["id"]
    cas = [
        ("POST", "/api/cards/decks", {"model": 42}),
        ("POST", "/api/cards/decks", {"model": ["superstar"]}),
        ("POST", "/api/cards/decks", {"model": ""}),
        ("POST", "/api/cards/decks", {"model": "../../etc/passwd"}),
        ("POST", "/api/cards/models", {}),
        ("POST", "/api/cards/models", {"did": did}),
        ("POST", "/api/cards/models", {"did": 7, "name": 7}),
        ("POST", "/api/cards/models", {"did": did, "name": "   "}),
        ("POST", "/api/cards/models", {"did": did, "name": "///"}),
        ("POST", "/api/cards/models", {"did": "../secret", "name": "x"}),
        ("POST", "/api/cards/decks/deck_zzzzzzzz/duplicate", None),
    ]
    for methode, chemin, corps in cas:
        r = _api(methode, chemin, json=corps)
        assert r.status_code < 500, f"{methode} {chemin} {corps} -> {r.text}"
        assert "json" in r.headers.get("content-type", "")
    # un modèle enregistré sous un nom qui ne donne aucun slug reste nommé
    for nom in ("   ", "///", "«»"):
        r = _api("POST", "/api/cards/models", json={"did": did, "name": nom})
        if r.status_code == 200:
            p = MO.models_root() / f"{r.json()['model']['id']}.json"
            assert p.is_file()
            assert p.parent == MO.models_root()
            p.unlink()


def test_une_reservation_qui_echoue_ne_laisse_pas_de_dechet():
    """La réservation crée le fichier AVANT de le remplir. Si le remplissage
    échoue, le nom doit être rendu — sinon un incident passager laisse un
    fichier vide, listé « illisible » à chaque ouverture de la galerie."""
    did = _api("POST", "/api/cards/decks",
               json={"model": "gravee"}).json()["deck"]["id"]
    doc = _api("GET", f"/api/cards/{did}").json()["deck"]
    avant = set(MO.models_root().glob("*.json"))
    vrai_dump = json.dump
    try:
        json.dump = lambda *a, **k: (_ for _ in ()).throw(OSError("disque"))
        with pytest.raises(OSError):
            MO.enregistrer(doc, "Echec en cours")
    finally:
        json.dump = vrai_dump
    assert set(MO.models_root().glob("*.json")) == avant, \
        "une réservation non rendue traîne dans le dossier"
    # ... et le nom est de nouveau libre
    m = MO.enregistrer(doc, "Echec en cours")
    try:
        assert m["id"] == "echec-en-cours"
    finally:
        (MO.models_root() / f"{m['id']}.json").unlink()


def test_supprimer_un_modele_perso():
    """Sans cette route, on pouvait CRÉER un modèle depuis l'écran et jamais
    le retirer — et le banc de la galerie (T4) devait effacer ses modèles de
    test en touchant le disque, avec son propre miroir du dossier de données.
    Quatre branches : usine (403), perso (200), inconnu (404), hostile."""
    did = _api("POST", "/api/cards/decks",
               json={"model": "duel"}).json()["deck"]["id"]
    m = _api("POST", "/api/cards/models",
             json={"did": did, "name": "A supprimer"}).json()["model"]
    p = MO.models_root() / f"{m['id']}.json"
    assert p.is_file()
    try:
        # 1. un modèle d'usine ne se supprime pas — et RIEN n'est touché
        r = _api("DELETE", "/api/cards/models/superstar")
        assert r.status_code == 403, r.text
        assert "usine" in r.json()["detail"]
        assert MO.model("superstar")["type"]["slots"]
        # 2. le perso, oui
        r = _api("DELETE", f"/api/cards/models/{m['id']}")
        assert r.status_code == 200, r.text
        assert r.json()["id"] == m["id"]
        assert not p.exists()
        assert m["id"] not in [x["id"] for x in
                               _api("GET", "/api/cards/models").json()["models"]]
        # 3. deux fois : inconnu
        r = _api("DELETE", f"/api/cards/models/{m['id']}")
        assert r.status_code == 404, r.text
        assert re.search(r"[éèêàâîôû]", r.json()["detail"])
    finally:
        if p.is_file():
            p.unlink()


def test_supprimer_ne_construit_aucun_chemin_depuis_lid_brut():
    """L'identifiant passe par le MÊME motif que l'écriture. Un témoin est
    posé À CÔTÉ du dossier des modèles : aucune des tentatives ne doit le
    faire disparaître.

    LES DEUX NIVEAUX, ET C'EST NÉCESSAIRE. Par HTTP, le client et le routeur
    RÉSOLVENT `..` avant que la route ne voie quoi que ce soit : le test
    passait donc même sans garde — il mesurait le transport, pas le code.
    L'appel DIRECT, lui, arrive là où la garde vit. (Mesuré : sans la garde,
    `supprimer("../zz_temoin_traversee")` efface le témoin.)"""
    temoin = MO.models_root().parent / "zz_temoin_traversee.json"
    hostiles = ("../zz_temoin_traversee", "..%2fzz_temoin_traversee",
                "sous/dossier", "..", ".", "A_MAJUSCULE", "avec espace",
                "zz_temoin_traversee.json", "..\\zz_temoin_traversee",
                "", "  ")
    temoin.write_text("{}", encoding="utf-8")
    try:
        for hostile in hostiles:
            r = _api("DELETE", f"/api/cards/models/{hostile}")
            assert r.status_code in (400, 404, 405), f"{hostile} -> {r.text}"
            assert temoin.is_file(), f"HTTP {hostile!r} a effacé le témoin"
        for hostile in hostiles:
            with pytest.raises((KeyError, ValueError)):
                MO.supprimer(hostile)
            assert temoin.is_file(), f"direct {hostile!r} a effacé le témoin"
        # le même motif garde la LECTURE : un identifiant hostile ne sert
        # jamais à construire un chemin, quel que soit le verbe.
        for hostile in hostiles:
            with pytest.raises((KeyError, ValueError)):
                MO.model(hostile)
    finally:
        temoin.unlink()


def test_aucun_message_derreur_ne_publie_un_chemin():
    """Le dossier de données porte le NOM DE COMPTE de l'utilisateur. Le
    dépôt a déjà payé cette fuite une fois (purge de 58 binaires) et la
    docstring de `catalogue()` l'interdit — mais les messages d'erreur, eux,
    recopiaient `{e}`, et un `OSError` porte le chemin complet. Le détail va
    au journal ; la réponse HTTP dit CE QUI a échoué, pas OÙ."""
    import inspect
    from app.services.cards import core as _core

    def _appels(src: str):
        """Chaque `HTTPException(...)` EN ENTIER, parenthèses appariées — un
        message tient souvent sur trois lignes, et une lecture ligne à ligne
        ne verrait que la première (elle laissait passer `{e}` posé au bout
        d'un message coupé)."""
        for m in re.finditer(r"HTTPException\(", src):
            prof, i = 0, m.end() - 1
            while i < len(src):
                if src[i] == "(":
                    prof += 1
                elif src[i] == ")":
                    prof -= 1
                    if prof == 0:
                        yield src[m.start():i + 1]
                        break
                i += 1

    vus = 0
    for mod in (MO, _core):
        src = inspect.getsource(mod)
        for appel in _appels(src):
            vus += 1
            assert "{e}" not in appel, \
                f"{mod.__name__} : « {' '.join(appel.split())[:120]} » " \
                "recopie l'exception brute (donc le chemin absolu)"
    assert vus >= 10, f"seulement {vus} appels relus — le balayage est cassé"
    # ... et la LISTE part par le même tuyau : la ligne « illisible » d'un
    # fichier qu'on n'a pas pu ouvrir est servie en HTTP, elle aussi.
    src = inspect.getsource(MO)
    lignes = [' '.join(a.split()) for a in re.findall(
        r"_illisible\((?:[^()]|\([^()]*\))*\)", src)]
    assert len(lignes) >= 3, lignes
    for ligne in lignes:
        assert "{e}" not in ligne, f"« {ligne[:120]} » recopie l'exception"
    # ... et le chemin du dossier n'est pas publié non plus par le catalogue
    body = _api("GET", "/api/cards/models").json()
    plat = json.dumps(body, ensure_ascii=False)
    assert "cardforge_models" not in plat
    assert str(MO.models_root()) not in plat


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
