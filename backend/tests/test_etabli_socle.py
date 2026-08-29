"""L'Établi P1 — chirurgie GLB et chronologie des étapes
(plan 2026-08-29-etabli-p1-socle-serveur).

Le banc ne SORT jamais : les GLB sont fabriqués par gltf_builder et relus par
print3d, les deux lecteurs déjà éprouvés du dépôt.

Run: .\\scripts\\run-tests.ps1 -Filter test_etabli_socle.py
"""
import json
import os
import pathlib
import struct
import sys
import tempfile
import zlib

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _png1x1() -> bytes:
    """PNG RGBA 1x1 valide — déclenche le quad de sol de gltf_builder, donc
    un GLB à DEUX nœuds, deux matériaux et une texture."""
    def ch(tag: bytes, d: bytes) -> bytes:
        c = tag + d
        return (struct.pack(">I", len(d)) + c
                + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n"
            + ch(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + ch(b"IDAT", zlib.compress(b"\x00\xff\xff\xff\xff"))
            + ch(b"IEND", b""))


def _cube() -> bytes:
    from app.services import gltf_builder
    return gltf_builder.build_glb({}, None, "cube", "banc")


def _cube_et_sol() -> bytes:
    from app.services import gltf_builder
    return gltf_builder.build_glb({}, None, "cube", "banc",
                                  stage_png=_png1x1())


# ── A. lecture / écriture ────────────────────────────────────────────────────

def test_aller_retour_glb_ne_deforme_rien():
    from app.services import mesh_edit
    data = _cube()
    doc, binc = mesh_edit.lire_glb(data)
    refait = mesh_edit.ecrire_glb(doc, binc)
    doc2, bin2 = mesh_edit.lire_glb(refait)
    assert doc == doc2
    assert binc == bin2


def test_le_glb_reecrit_se_relit_par_print3d():
    from app.services import mesh_edit, print3d
    doc, binc = mesh_edit.lire_glb(_cube())
    tris = print3d.lire_glb_triangles(mesh_edit.ecrire_glb(doc, binc))
    assert len(tris) == 12
    assert print3d.bbox(tris) == ((-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0))


def test_un_fichier_qui_n_est_pas_un_glb_est_refuse_parlant():
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="magic GLB"):
        mesh_edit.lire_glb(b"ceci n'est pas un GLB")


def test_des_octets_parasites_apres_la_fin_declaree_sont_ignores():
    """Le conteneur GLB déclare sa longueur à l'octet 8, et cette longueur
    FAIT AUTORITÉ — `print3d._chunks` la respecte déjà.

    Sans cette borne, des octets traînant après la fin (téléchargement
    rejoué, artefact d'un générateur tiers) seraient lus comme des chunks.
    Ici la queue imite un chunk BIN vide : sans borne, le tampon déjà lu
    serait écrasé EN SILENCE, sans la moindre exception."""
    from app.services import mesh_edit
    data = _cube()
    doc, binc = mesh_edit.lire_glb(data)
    assert binc, "le cube doit avoir un tampon binaire"
    parasite = data + struct.pack("<I", 0) + b"BIN\x00"
    doc2, bin2 = mesh_edit.lire_glb(parasite)
    assert doc2 == doc
    assert bin2 == binc          # et surtout : PAS écrasé par le bruit


# ── B. inventaire de squelette ───────────────────────────────────────────────

def test_un_maillage_sans_squelette_le_dit():
    from app.services import mesh_edit
    inv = mesh_edit.rig_inventory(_cube())
    assert inv["a_squelette"] is False
    assert inv["os"] == []
    assert inv["clips"] == []


def test_l_inventaire_lit_les_os_et_leur_hierarchie():
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube())
    base = len(doc["nodes"])
    doc["nodes"].append({"name": "hanche", "children": [base + 1]})
    doc["nodes"].append({"name": "colonne"})
    doc["skins"] = [{"name": "armature", "joints": [base, base + 1],
                     "skeleton": base}]
    doc["nodes"][0]["skin"] = 0
    doc["animations"] = [{"name": "idle", "channels": [], "samplers": []}]
    inv = mesh_edit.rig_inventory(mesh_edit.ecrire_glb(doc, binc))
    assert inv["a_squelette"] is True
    assert inv["nb_os"] == 2
    assert [o["nom"] for o in inv["os"]] == ["hanche", "colonne"]
    assert inv["os"][0]["enfants"] == [base + 1]
    assert inv["os"][1]["parent"] == base
    assert inv["clips"] == [{"nom": "idle", "canaux": 0}]


# ── C. transformer : JSON seulement ──────────────────────────────────────────

def test_transformer_laisse_le_tampon_binaire_identique():
    """LA propriété qui rend l'opération sûre sur un fichier de 200 Mo."""
    from app.services import mesh_edit
    base = _cube()
    bouge = mesh_edit.transformer(base, {"0": {"translation": [0.0, 3.0, 0.0]}})
    _, bin_avant = mesh_edit.lire_glb(base)
    _, bin_apres = mesh_edit.lire_glb(bouge)
    assert bin_avant == bin_apres


def test_transformer_deplace_vraiment_le_maillage():
    from app.services import mesh_edit, print3d
    bouge = mesh_edit.transformer(_cube(), {"0": {"translation": [0.0, 3.0, 0.0]}})
    assert print3d.bbox(print3d.lire_glb_triangles(bouge)) == (
        (-1.0, 1.0), (2.0, 4.0), (-1.0, 1.0))


def test_transformer_refuse_un_noeud_hors_document():
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="hors du document"):
        mesh_edit.transformer(_cube(), {"99": {"translation": [0.0, 0.0, 0.0]}})


def test_transformer_refuse_un_vecteur_de_mauvaise_taille():
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="attend 3 valeurs"):
        mesh_edit.transformer(_cube(), {"0": {"translation": [1.0, 2.0]}})


def test_transformer_refuse_un_quaternion_non_norme():
    """glTF exige un quaternion UNITAIRE. Le refuser plutôt que le normaliser
    en douce : normaliser masquerait le bug amont qui l'a produit."""
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="quaternion normé"):
        mesh_edit.transformer(_cube(), {"0": {"rotation": [0.0, 0.0, 0.0, 2.0]}})


def test_transformer_refuse_une_entree_qui_n_est_pas_un_dictionnaire():
    """Sans ce garde, une liste lève AttributeError — que la route de la
    tâche 8 ne rattrape pas, et qui sortirait donc en 500 au lieu d'un 400."""
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="dictionnaire"):
        mesh_edit.transformer(_cube(), [{"0": {}}])
    with pytest.raises(ValueError, match="non numérique"):
        mesh_edit.transformer(_cube(), {"abc": {"translation": [0.0, 0.0, 0.0]}})


def test_transformer_exerce_aussi_rotation_et_echelle():
    """Les chemins `rotation` et `scale` de `_TAILLES` ne sont exercés par
    aucun autre banc. TRS glTF = T · R · S : le cube unité mis à l'échelle 2,
    tourné d'un quart de tour autour de X, puis décalé de +3 en Y."""
    from app.services import mesh_edit, print3d
    q = [(2 ** 0.5) / 2, 0.0, 0.0, (2 ** 0.5) / 2]      # 90° autour de X
    sortie = mesh_edit.transformer(_cube(), {"0": {
        "translation": [0.0, 3.0, 0.0], "rotation": q, "scale": [2.0, 2.0, 2.0]}})
    doc, _ = mesh_edit.lire_glb(sortie)
    assert doc["nodes"][0]["scale"] == [2.0, 2.0, 2.0]
    bb = print3d.bbox(print3d.lire_glb_triangles(sortie))
    attendu = ((-2.0, 2.0), (1.0, 5.0), (-2.0, 2.0))
    for (lo, hi), (alo, ahi) in zip(bb, attendu):
        assert abs(lo - alo) < 1e-6 and abs(hi - ahi) < 1e-6


def test_transformer_retire_une_matrice_preexistante():
    """glTF interdit de porter `matrix` ET un TRS : la docstring en fait une
    garantie, ce banc l'épingle."""
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube())
    doc["nodes"][0]["matrix"] = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                                 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    avec = mesh_edit.ecrire_glb(doc, binc)
    sortie, _ = mesh_edit.lire_glb(
        mesh_edit.transformer(avec, {"0": {"translation": [0.0, 1.0, 0.0]}}))
    assert "matrix" not in sortie["nodes"][0]
    assert sortie["nodes"][0]["translation"] == [0.0, 1.0, 0.0]


# ── D. réparer : assise globale ──────────────────────────────────────────────

def test_reparer_met_a_l_echelle():
    from app.services import mesh_edit, print3d
    gros = mesh_edit.reparer(_cube(), echelle=2.0)
    assert print3d.bbox(print3d.lire_glb_triangles(gros)) == (
        (-2.0, 2.0), (-2.0, 2.0), (-2.0, 2.0))


def test_reparer_bascule_en_z_up():
    """Un decalage de +3 en Y doit se retrouver en +3 en Z."""
    from app.services import mesh_edit, print3d
    haut = mesh_edit.transformer(_cube(), {"0": {"translation": [0.0, 3.0, 0.0]}})
    zup = mesh_edit.reparer(haut, axe_haut="Z")
    assert print3d.bbox(print3d.lire_glb_triangles(zup)) == (
        (-1.0, 1.0), (-1.0, 1.0), (2.0, 4.0))


def test_reparer_recentre_sur_l_origine():
    from app.services import mesh_edit, print3d
    haut = mesh_edit.transformer(_cube(), {"0": {"translation": [0.0, 3.0, 0.0]}})
    centre = mesh_edit.reparer(haut, recentrer=True)
    assert print3d.bbox(print3d.lire_glb_triangles(centre)) == (
        (-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0))


def test_reparer_refuse_un_axe_inconnu():
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="axe haut inconnu"):
        mesh_edit.reparer(_cube(), axe_haut="Q")


def test_reparer_refuse_une_echelle_nulle_ou_negative():
    """Politique DIFFÉRENTE de `transformer`, et c'est voulu : une échelle
    globale ≤ 0 n'a pas de sens pour une assise, alors qu'un `scale` négatif
    par axe est un miroir glTF parfaitement valide."""
    from app.services import mesh_edit
    for mauvaise in (0.0, -1.0):
        with pytest.raises(ValueError, match="strictement positive"):
            mesh_edit.reparer(_cube(), echelle=mauvaise)


def test_reparer_refuse_des_parametres_de_mauvais_type():
    """Ces deux paramètres viendront d'un corps JSON (tâche 8), et la route ne
    traduit en 400 que les `ValueError`. Sans gardes, `axe_haut=123` lève
    AttributeError et `echelle=[1.0]` TypeError — deux 500."""
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="axe_haut attend une chaîne"):
        mesh_edit.reparer(_cube(), axe_haut=123)
    with pytest.raises(ValueError, match="echelle attend un nombre"):
        mesh_edit.reparer(_cube(), echelle=[1.0])
    # `bool` est un `int` : sans garde, True passerait pour une échelle de 1
    with pytest.raises(ValueError, match="echelle attend un nombre"):
        mesh_edit.reparer(_cube(), echelle=True)


def test_reparer_refuse_une_scene_active_hors_du_document():
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube())
    doc["scene"] = 5
    with pytest.raises(ValueError, match="scène active 5 hors du document"):
        mesh_edit.reparer(mesh_edit.ecrire_glb(doc, binc))


def _cube_compresse() -> bytes:
    """Un cube qui se DÉCLARE draco. `print3d` refuse sur la déclaration
    `extensionsRequired`, pas sur le décodage : c'est donc une simulation
    honnête du contrat, sans embarquer un encodeur Draco au banc."""
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube())
    doc["extensionsRequired"] = ["KHR_draco_mesh_compression"]
    doc["extensionsUsed"] = ["KHR_draco_mesh_compression"]
    return mesh_edit.ecrire_glb(doc, binc)


def test_sur_un_glb_compresse_la_degradation_est_partielle_et_explicite():
    """LE principe du dépôt : axe et échelle passent, seul le recentrage
    refuse — et il dit pourquoi. Jamais un échec global quand une partie du
    travail est faisable."""
    from app.services import mesh_edit, print3d
    comp = _cube_compresse()
    with pytest.raises(ValueError, match="draco"):
        print3d.lire_glb_triangles(comp)
    # axe + échelle : aucune géométrie n'est lue, donc ça passe
    sortie, _ = mesh_edit.lire_glb(
        mesh_edit.reparer(comp, axe_haut="Z", echelle=2.0))
    assert sortie["nodes"][-1]["name"] == "etabli_correction"
    assert sortie["extensionsRequired"] == ["KHR_draco_mesh_compression"]
    # le recentrage, lui, a besoin des triangles : il refuse, en le disant
    with pytest.raises(ValueError, match="draco"):
        mesh_edit.reparer(comp, recentrer=True)


# ── E. extraire : la somme des parties fait le tout ──────────────────────────

def test_le_depart_porte_bien_deux_parties():
    from app.services import print3d
    assert len(print3d.lire_glb_triangles(_cube_et_sol())) == 14


def test_extraire_le_cube_garde_ses_douze_triangles():
    from app.services import mesh_edit, print3d
    cube = mesh_edit.extraire(_cube_et_sol(), [0])
    tris = print3d.lire_glb_triangles(cube)
    assert len(tris) == 12
    assert print3d.bbox(tris) == ((-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0))


def test_extraire_elague_les_dependances_de_l_autre_partie():
    """Le cube ne doit PAS trainer la texture du sol : c'est tout l'interet
    d'extraire plutot que de masquer."""
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(mesh_edit.extraire(_cube_et_sol(), [0]))
    assert len(doc["nodes"]) == 1
    assert len(doc["meshes"]) == 1
    assert len(doc.get("materials", [])) == 1
    assert len(doc.get("images", [])) == 0
    assert len(doc["accessors"]) == 5
    assert len(doc["bufferViews"]) == 5
    assert len(binc) == 1224


def test_extraire_le_sol_garde_SA_texture():
    from app.services import mesh_edit, print3d
    sol = mesh_edit.extraire(_cube_et_sol(), [1])
    doc, _ = mesh_edit.lire_glb(sol)
    assert len(print3d.lire_glb_triangles(sol)) == 2
    assert len(doc["images"]) == 1
    assert len(doc["materials"]) == 1


def test_extraire_emporte_les_enfants_du_noeud():
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube_et_sol())
    doc["nodes"][0]["children"] = [1]
    doc["scenes"][0]["nodes"] = [0]
    tout = mesh_edit.ecrire_glb(doc, binc)
    sortie, _ = mesh_edit.lire_glb(mesh_edit.extraire(tout, [0]))
    assert len(sortie["nodes"]) == 2


def test_extraire_refuse_une_selection_vide():
    from app.services import mesh_edit
    with pytest.raises(ValueError, match="aucun noeud retenu"):
        mesh_edit.extraire(_cube_et_sol(), [])


def test_extraire_un_parent_et_son_enfant_ne_double_pas_la_geometrie():
    """Cocher un parent PUIS son enfant est un geste naturel du panneau
    Parties. Les lister tous deux comme racines de scène dessinerait l'enfant
    deux fois — mesuré : 16 triangles au lieu de 14."""
    from app.services import mesh_edit, print3d
    doc, binc = mesh_edit.lire_glb(_cube_et_sol())
    doc["nodes"][0]["children"] = [1]          # le sol devient enfant du cube
    doc["scenes"][0]["nodes"] = [0]
    tout = mesh_edit.ecrire_glb(doc, binc)
    assert len(print3d.lire_glb_triangles(tout)) == 14

    chevauche = mesh_edit.extraire(tout, [0, 1])
    assert len(print3d.lire_glb_triangles(chevauche)) == 14
    sortie, _ = mesh_edit.lire_glb(chevauche)
    assert sortie["scenes"][0]["nodes"] == [0]   # l'enfant n'est PAS une racine


def test_extraire_deux_noeuds_disjoints_garde_deux_racines():
    """Le contre-cas : sans lien de parenté, les deux restent des racines."""
    from app.services import mesh_edit, print3d
    deux = mesh_edit.extraire(_cube_et_sol(), [0, 1])
    assert len(print3d.lire_glb_triangles(deux)) == 14
    sortie, _ = mesh_edit.lire_glb(deux)
    assert sortie["scenes"][0]["nodes"] == [0, 1]


def test_extraire_apres_reparer_ne_perd_pas_la_correction():
    """LE piège que la revue de la tâche 4 a repéré.

    Après `reparer`, la scène a une racine synthétique qui porte la
    correction, et le maillage est devenu son enfant. Extraire cet enfant en
    ne recopiant que sa transformation LOCALE ferait ressortir la pièce
    couchée — mesuré : ((-1,1), (2,4), (-1,1)) au lieu du monde redressé
    ((-1,1), (-1,1), (2,4)). Un modèle qu'on vient de redresser reviendrait
    de travers dans Blender, sans le moindre message.
    """
    from app.services import mesh_edit, print3d
    haut = mesh_edit.transformer(_cube(), {"0": {"translation": [0.0, 3.0, 0.0]}})
    redresse = mesh_edit.reparer(haut, axe_haut="Z")
    monde = print3d.bbox(print3d.lire_glb_triangles(redresse))
    assert monde == ((-1.0, 1.0), (-1.0, 1.0), (2.0, 4.0))

    doc, _ = mesh_edit.lire_glb(redresse)
    racine = doc["scenes"][doc.get("scene", 0)]["nodes"][0]
    enfant = doc["nodes"][racine]["children"][0]

    piece = mesh_edit.extraire(redresse, [enfant])
    bb = print3d.bbox(print3d.lire_glb_triangles(piece))
    for (lo, hi), (alo, ahi) in zip(bb, monde):
        assert abs(lo - alo) < 1e-9 and abs(hi - ahi) < 1e-9
