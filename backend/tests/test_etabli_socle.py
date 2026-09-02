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


def test_extraire_traverse_la_compression_que_le_lecteur_refuse():
    """LA propriété phare du design — et elle n'était couverte par rien.

    On fabrique un GLB dont une primitive porte une vue Draco d'octets
    opaques. `print3d.lire_glb_triangles` refuse ce fichier ; `extraire`, qui
    ne décode aucune géométrie et se contente de recopier des octets, le
    traverse — et les 192 octets ressortent bit pour bit.

    Sans ce banc, on aurait pu casser la recopie sans qu'aucun test bronche :
    tous les autres passent par des GLB non compressés.
    """
    from app.services import mesh_edit, print3d
    opaque = bytes(range(64)) * 3
    doc, binc = mesh_edit.lire_glb(_cube())
    tampon = bytearray(binc)
    while len(tampon) % 4:
        tampon.append(0)
    offset = len(tampon)
    tampon += opaque
    doc["bufferViews"].append({"buffer": 0, "byteOffset": offset,
                               "byteLength": len(opaque)})
    doc["buffers"][0]["byteLength"] = len(tampon)
    prim = doc["meshes"][0]["primitives"][0]
    prim.setdefault("extensions", {})["KHR_draco_mesh_compression"] = {
        "bufferView": len(doc["bufferViews"]) - 1,
        "attributes": {"POSITION": 0},
    }
    doc["extensionsUsed"] = ["KHR_draco_mesh_compression"]
    doc["extensionsRequired"] = ["KHR_draco_mesh_compression"]
    doc["nodes"].append({"name": "voisin"})     # de quoi élaguer
    doc["scenes"][0]["nodes"] = [0, 1]
    compresse = mesh_edit.ecrire_glb(doc, bytes(tampon))

    with pytest.raises(ValueError, match="draco"):
        print3d.lire_glb_triangles(compresse)

    piece = mesh_edit.extraire(compresse, [0])
    sortie, bin_sortie = mesh_edit.lire_glb(piece)
    assert len(sortie["nodes"]) == 1
    assert sortie["extensionsRequired"] == ["KHR_draco_mesh_compression"]
    draco = sortie["meshes"][0]["primitives"][0]["extensions"][
        "KHR_draco_mesh_compression"]
    v = sortie["bufferViews"][draco["bufferView"]]
    assert bin_sortie[v["byteOffset"]:v["byteOffset"] + v["byteLength"]] == opaque


def test_extraire_remappe_les_vues_d_un_accesseur_sparse():
    """Un accesseur `sparse` porte deux vues DANS DES SOUS-OBJETS. Elles
    étaient collectées mais jamais remappées — mesuré : elles restaient aux
    index 11 et 12 dans une pièce réduite à 7 vues, donc hors bornes."""
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube_et_sol())
    tampon = bytearray(binc)
    while len(tampon) % 4:
        tampon.append(0)
    oi = len(tampon)
    tampon += b"\x00" * 4
    ov = len(tampon)
    tampon += b"\x00" * 24
    doc["bufferViews"].append({"buffer": 0, "byteOffset": oi, "byteLength": 4})
    vi = len(doc["bufferViews"]) - 1
    doc["bufferViews"].append({"buffer": 0, "byteOffset": ov, "byteLength": 24})
    vv = len(doc["bufferViews"]) - 1
    doc["buffers"][0]["byteLength"] = len(tampon)
    pos = doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
    doc["accessors"][pos]["sparse"] = {
        "count": 2,
        "indices": {"bufferView": vi, "byteOffset": 0, "componentType": 5123},
        "values": {"bufferView": vv, "byteOffset": 0},
    }
    source = mesh_edit.ecrire_glb(doc, bytes(tampon))

    sortie, _ = mesh_edit.lire_glb(mesh_edit.extraire(source, [0]))
    pos2 = sortie["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
    sparse = sortie["accessors"][pos2]["sparse"]
    n = len(sortie["bufferViews"])
    assert sparse["indices"]["bufferView"] < n
    assert sparse["values"]["bufferView"] < n
    # et le document SOURCE ne doit pas avoir été abîmé au passage
    assert doc["accessors"][pos]["sparse"]["indices"]["bufferView"] == vi


def test_extraire_ne_declare_que_les_extensions_reellement_presentes():
    """Recopier `extensionsRequired` en bloc ferait déclarer draco à une pièce
    sans un octet compressé — et `print3d` la refuserait alors qu'elle est
    saine. Mesuré : c'est exactement ce qui se passait."""
    from app.services import mesh_edit, print3d
    doc, binc = mesh_edit.lire_glb(_cube())
    tampon = bytearray(binc)
    while len(tampon) % 4:
        tampon.append(0)
    o = len(tampon)
    tampon += b"\xAA" * 32
    doc["bufferViews"].append({"buffer": 0, "byteOffset": o, "byteLength": 32})
    doc["buffers"][0]["byteLength"] = len(tampon)
    doc["meshes"][0]["primitives"][0].setdefault("extensions", {})[
        "KHR_draco_mesh_compression"] = {
            "bufferView": len(doc["bufferViews"]) - 1,
            "attributes": {"POSITION": 0}}
    doc["extensionsUsed"] = ["KHR_draco_mesh_compression"]
    doc["extensionsRequired"] = ["KHR_draco_mesh_compression"]
    # un second maillage, celui-là sans une once de compression
    libre = json.loads(json.dumps(doc["meshes"][0]))
    libre["name"] = "libre"
    libre["primitives"][0].pop("extensions", None)
    doc["meshes"].append(libre)
    doc["nodes"].append({"name": "libre", "mesh": 1})
    doc["scenes"][0]["nodes"] = [0, 1]
    mixte = mesh_edit.ecrire_glb(doc, bytes(tampon))

    piece = mesh_edit.extraire(mixte, [1])
    sortie, _ = mesh_edit.lire_glb(piece)
    assert "extensionsRequired" not in sortie
    # la preuve par l'usage : le lecteur accepte enfin cette pièce saine
    assert len(print3d.lire_glb_triangles(piece)) == 12


def test_extraire_suit_une_texture_reference_par_une_extension_materiau():
    """`KHR_materials_clearcoat` et consorts référencent des textures hors des
    cinq emplacements PBR de base. Sans les suivre, la pièce sortait avec un
    `clearcoatTexture.index` pointant dans le vide — mesuré."""
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube_et_sol())
    doc["materials"][0].setdefault("extensions", {})[
        "KHR_materials_clearcoat"] = {"clearcoatTexture": {"index": 0}}
    doc["extensionsUsed"] = ["KHR_materials_clearcoat"]
    source = mesh_edit.ecrire_glb(doc, binc)

    sortie, _ = mesh_edit.lire_glb(mesh_edit.extraire(source, [0]))
    cc = sortie["materials"][0]["extensions"]["KHR_materials_clearcoat"]
    assert cc["clearcoatTexture"]["index"] < len(sortie["textures"])
    assert len(sortie["images"]) == 1        # la texture a suivi la pièce


def test_extraire_ne_confond_pas_extras_avec_une_texture():
    """`extras` est de la donnée LIBRE : la spec glTF n'y met aucune
    structure. Un outil tiers peut y poser une clé finissant par « Texture »
    portant un `index` qui ne désigne rien — mesuré : IndexError au
    remappage, un plantage au lieu d'un refus parlant."""
    from app.services import mesh_edit, print3d
    doc, binc = mesh_edit.lire_glb(_cube())
    doc["materials"][0]["extras"] = {
        "monOutilTexture": {"index": 7, "note": "métadonnée libre"}}
    source = mesh_edit.ecrire_glb(doc, binc)
    piece = mesh_edit.extraire(source, [0])
    assert len(print3d.lire_glb_triangles(piece)) == 12
    sortie, _ = mesh_edit.lire_glb(piece)
    # l'extra est recopié tel quel, sans avoir été pris pour une structure
    assert sortie["materials"][0]["extras"]["monOutilTexture"]["index"] == 7


def test_extraire_normalise_un_quaternion_derive_d_un_ancetre():
    """`_mat_locale` normalise un quaternion non unitaire lu d'un fichier.

    Conséquence MESURÉE et assumée : sur un fichier déjà invalide au sens
    glTF, la pièce extraite ne coïncide plus avec ce que `print3d` lit de la
    scène source — le lecteur applique le quaternion brut, donc un
    cisaillement. On restitue la rotation manifestement voulue plutôt que la
    déformation, et ce banc épingle ce choix : sans lui, une régression
    réintroduirait le cisaillement sans que rien ne le voie avant Blender.
    """
    from app.services import mesh_edit, print3d

    def scene(q):
        doc, binc = mesh_edit.lire_glb(_cube())
        doc["nodes"][0]["translation"] = [0.0, 3.0, 0.0]
        doc["nodes"].append({"name": "ancetre", "children": [0], "rotation": q})
        doc["scenes"][0]["nodes"] = [1]
        return mesh_edit.ecrire_glb(doc, binc)

    r2 = (2 ** 0.5) / 2
    unitaire = scene([r2, 0.0, 0.0, r2])          # 90° autour de X
    derive = scene([r2 * 1.2, 0.0, 0.0, r2 * 1.2])   # même rotation, norme 1,2

    # la SOURCE dérivée est bel et bien cisaillée quand on la lit brute
    bb_source = print3d.bbox(print3d.lire_glb_triangles(derive))
    assert bb_source[1][0] < -3.0                 # mesuré : -3.2

    # les deux PIÈCES extraites, elles, sont identiques
    a = print3d.bbox(print3d.lire_glb_triangles(mesh_edit.extraire(unitaire, [0])))
    b = print3d.bbox(print3d.lire_glb_triangles(mesh_edit.extraire(derive, [0])))
    for (lo, hi), (alo, ahi) in zip(a, b):
        assert abs(lo - alo) < 1e-9 and abs(hi - ahi) < 1e-9


def test_extraire_refuse_meshopt_au_lieu_de_recopier_de_travers():
    """meshopt place ses octets hors des champs de premier niveau : les
    recopier en aveugle donnerait un fichier faux EN SILENCE. Le refus dit
    quoi faire à la place."""
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube())
    doc["extensionsRequired"] = ["EXT_meshopt_compression"]
    doc["extensionsUsed"] = ["EXT_meshopt_compression"]
    with pytest.raises(ValueError, match="meshopt"):
        mesh_edit.extraire(mesh_edit.ecrire_glb(doc, binc), [0])


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


# ── F. écriture versionnée ───────────────────────────────────────────────────

def test_ecrire_version_ajoute_sans_ecraser():
    from app.config import settings
    from app.services import mesh_edit
    d = settings.outputs_path / "assets3d" / "job_banc"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_cube_et_sol())

    fiche = mesh_edit.ecrire_version(
        "job_banc", mesh_edit.extraire(_cube_et_sol(), [0]),
        operation="extraire", detail={"noeuds": [0]})

    assert fiche["version"] == 2
    assert fiche["file"] == "model.v2.glb"
    assert (d / "model.glb").is_file()          # le brouillon survit
    assert (d / "model.v2.glb").is_file()
    registre = json.loads((d / "report.json").read_text("utf-8"))
    assert registre["current"] == "model.v2.glb"
    assert fiche["source"]["operation"] == "extraire"


def test_la_fiche_d_une_version_decompressee_ne_la_dit_plus_compressee():
    """Conseil de la revue de la tâche 5, et il porte.

    `extraire` filtre désormais `extensionsRequired`. Une version écrite
    derrière une extraction qui a laissé la compression au vestiaire ne doit
    donc PAS être fichée comme encore compressée — sinon `mesh_report` renonce
    à la géométrie et la fiche ment sur ce qu'on vient d'écrire.
    """
    from app.config import settings
    from app.services import mesh_edit
    d = settings.outputs_path / "assets3d" / "job_decomp"
    d.mkdir(parents=True, exist_ok=True)

    # un document mixte : un maillage draco, un maillage libre
    doc, binc = mesh_edit.lire_glb(_cube())
    tampon = bytearray(binc)
    while len(tampon) % 4:
        tampon.append(0)
    o = len(tampon)
    tampon += b"\xAA" * 32
    doc["bufferViews"].append({"buffer": 0, "byteOffset": o, "byteLength": 32})
    doc["buffers"][0]["byteLength"] = len(tampon)
    doc["meshes"][0]["primitives"][0].setdefault("extensions", {})[
        "KHR_draco_mesh_compression"] = {
            "bufferView": len(doc["bufferViews"]) - 1,
            "attributes": {"POSITION": 0}}
    doc["extensionsUsed"] = ["KHR_draco_mesh_compression"]
    doc["extensionsRequired"] = ["KHR_draco_mesh_compression"]
    libre = json.loads(json.dumps(doc["meshes"][0]))
    libre["primitives"][0].pop("extensions", None)
    doc["meshes"].append(libre)
    doc["nodes"].append({"name": "libre", "mesh": 1})
    doc["scenes"][0]["nodes"] = [0, 1]
    (d / "model.glb").write_bytes(mesh_edit.ecrire_glb(doc, bytes(tampon)))

    piece = mesh_edit.extraire((d / "model.glb").read_bytes(), [1])
    fiche = mesh_edit.ecrire_version(
        "job_decomp", piece, operation="extraire", detail={"noeuds": [1]})

    assert fiche["gltf"]["extensions_required"] == []
    # et la géométrie est bien calculée, pas abandonnée sur un faux refus
    assert fiche["geometry"]["tris_lus"] == 12


# ── F2. adoption d'une tâche Meshy ───────────────────────────────────────────

def test_une_tache_meshy_est_adoptee_par_un_job():
    from app.config import settings
    from app.services import mesh_edit
    src = settings.outputs_path / "meshy3d" / "tache_abc"
    src.mkdir(parents=True, exist_ok=True)
    (src / "model.glb").write_bytes(_cube_et_sol())

    job = mesh_edit.adopter_meshy("tache_abc", "model.glb")

    assert job == "meshy_tache_abc"
    d = settings.outputs_path / "assets3d" / job
    assert (d / "model.glb").is_file()
    man = json.loads((d / "asset.json").read_text("utf-8"))
    assert man["adopte_de"] == "meshy3d/tache_abc"
    # adopter deux fois ne duplique pas
    assert mesh_edit.adopter_meshy("tache_abc", "model.glb") == job


def test_l_adoption_refuse_une_tache_sans_glb():
    from app.services import mesh_edit
    with pytest.raises(FileNotFoundError):
        mesh_edit.adopter_meshy("tache_absente", "model.glb")


def test_une_adoption_interrompue_se_repare_au_passage_suivant():
    """Les trois écritures sont gardées séparément, et c'est le point.

    Une adoption coupée entre le binaire et sa fiche laisserait sinon un job
    sans fiche POUR TOUJOURS : le prochain appel verrait le `.glb` présent et
    repartirait aussitôt. Ici chaque appel répare ce qui manque — et ne
    réécrit rien de ce qui est déjà là.
    """
    from app.config import settings
    from app.services import mesh_edit
    src = settings.outputs_path / "meshy3d" / "tache_coupee"
    src.mkdir(parents=True, exist_ok=True)
    (src / "model.glb").write_bytes(_cube())

    job = mesh_edit.adopter_meshy("tache_coupee")
    d = settings.outputs_path / "assets3d" / job
    empreinte = (d / "model.glb").stat().st_mtime_ns

    # on simule l'interruption : la fiche et le manifeste n'ont pas été écrits
    (d / "report.json").unlink()
    (d / "asset.json").unlink()

    assert mesh_edit.adopter_meshy("tache_coupee") == job
    assert (d / "report.json").is_file()
    assert (d / "asset.json").is_file()
    # le binaire, lui, n'a PAS été réécrit
    assert (d / "model.glb").stat().st_mtime_ns == empreinte


# ── G. chronologie des étapes ────────────────────────────────────────────────

def test_la_chronologie_fond_les_versions_d_un_job():
    from app.config import settings
    from app.services import mesh_edit, mesh_sources
    d = settings.outputs_path / "assets3d" / "job_chrono"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_cube())
    mesh_edit.ecrire_version("job_chrono", _cube_et_sol(),
                             operation="banc", detail={})

    lignes = [x for x in mesh_sources.lister() if x["id"] == "job_chrono"]
    assert len(lignes) == 1
    versions = lignes[0]["etapes"]
    assert [e["version"] for e in versions] == [1, 2]
    assert versions[0]["url"].endswith("/version/1")
    assert versions[1]["triangles"] == 14
    assert versions[0]["sha256"] != versions[1]["sha256"]


def test_la_chronologie_survit_a_un_job_sans_registre():
    from app.config import settings
    from app.services import mesh_sources
    d = settings.outputs_path / "assets3d" / "job_nu"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_cube())
    lignes = [x for x in mesh_sources.lister() if x["id"] == "job_nu"]
    assert len(lignes) == 1
    assert lignes[0]["etapes"][0]["version"] == 1
    assert lignes[0]["etapes"][0]["triangles"] is None


def test_un_job_abime_n_eteint_pas_toute_la_chronologie():
    """« Il LIT ce qui existe » a une conséquence : ce dossier est ouvert aux
    mains de l'utilisateur.

    Mesuré : un seul `model.v2 (1).glb` — le nom que l'explorateur Windows
    génère tout seul sur une copie — faisait tomber la liste ENTIÈRE, jobs
    sains compris. La bibliothèque 3D disparaissait de l'écran à cause d'un
    fichier copié à la main.
    """
    from app.config import settings
    from app.services import mesh_sources
    sain = settings.outputs_path / "assets3d" / "job_voisin_sain"
    sain.mkdir(parents=True, exist_ok=True)
    (sain / "model.glb").write_bytes(_cube())

    abime = settings.outputs_path / "assets3d" / "job_voisin_abime"
    abime.mkdir(parents=True, exist_ok=True)
    (abime / "model.glb").write_bytes(_cube())
    (abime / "model.v2 (1).glb").write_bytes(_cube())
    (abime / "asset.json").write_text("[1, 2, 3]", encoding="utf-8")

    lignes = mesh_sources.lister()
    assert "job_voisin_sain" in [x["id"] for x in lignes]
    # le job abîmé reste listable avec ce qu'on sait en lire, et surtout il
    # n'emporte pas les autres avec lui
    abimee = [x for x in lignes if x["id"] == "job_voisin_abime"]
    assert len(abimee) == 1
    assert [e["version"] for e in abimee[0]["etapes"]] == [1]


def test_un_exposant_unicode_ne_fait_pas_disparaitre_le_job():
    """`isdigit()` seul n'est pas étanche : `'²'.isdigit()` vaut `True` alors
    qu'`int('²')` lève.

    Mesuré sur le Python du dépôt : 128 caractères passent `isdigit()` et font
    lever `int()` — exposants, indices, chiffres cerclés, familles éthiopienne
    ou brahmi — et TOUS sont non-ASCII. Sans `isascii()`, un `model.v².glb`
    traverse la garde interne ; le filet extérieur de `lister()` rattrape, mais
    le job ENTIER disparaît alors de la chronologie au lieu de survivre avec
    ses versions saines. C'est la promesse de la docstring, tenue jusqu'au bout.
    """
    from app.config import settings
    from app.services import mesh_sources

    # la garde interne rend `None`, elle ne lève pas
    for nom in ("model.v\u00b2.glb", "model.v\u2082.glb"):
        assert mesh_sources._numero_de_version(nom) is None, nom
    # et elle n'exclut aucun nom légitime au passage
    assert mesh_sources._numero_de_version("model.glb") == 1
    assert mesh_sources._numero_de_version("model.v2.glb") == 2
    assert mesh_sources._numero_de_version("model.v10.glb") == 10

    d = settings.outputs_path / "assets3d" / "job_exposant"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_cube())
    (d / "model.v2.glb").write_bytes(_cube_et_sol())
    (d / "model.v\u00b2.glb").write_bytes(_cube())
    (d / "model.v\u2082.glb").write_bytes(_cube())

    ligne = [x for x in mesh_sources.lister() if x["id"] == "job_exposant"]
    # le job SURVIT : c'est la conséquence qui compte, pas l'absence de levée
    assert len(ligne) == 1, "le job a disparu de la chronologie"
    assert [e["version"] for e in ligne[0]["etapes"]] == [1, 2]


def test_les_lignes_des_deux_sources_ont_la_meme_forme():
    """Le panneau de gauche ne doit pas avoir à distinguer les deux sources :
    une clé sans valeur vaut `None`, elle n'est pas absente."""
    from app.config import settings
    from app.services import mesh_edit, mesh_sources
    src = settings.outputs_path / "meshy3d" / "tache_forme"
    src.mkdir(parents=True, exist_ok=True)
    (src / "model.glb").write_bytes(_cube())
    job = mesh_edit.adopter_meshy("tache_forme")

    ligne = [x for x in mesh_sources.lister() if x["id"] == job][0]
    for cle in ("source", "id", "nom", "moteur", "phase", "kind",
                "adopte_de", "adopte_en", "created_at", "etapes"):
        assert cle in ligne, cle
    # l'adoption laisse une trace exploitable pour relier les deux vues
    assert ligne["adopte_de"] == "meshy3d/tache_forme"


# ── H. routes ────────────────────────────────────────────────────────────────

def _client():
    """`TestClient(app)` sans `with` ne déclenche PAS le `lifespan` de l'appli
    (donc pas `init_db()`) : sans cette ligne, `/etabli/sources` tombe sur
    « no such table: meshy_tasks » dans la base sqlite temporaire du banc,
    alors qu'en vrai la table existe depuis le démarrage du serveur."""
    import asyncio as _asyncio
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.storage import init_db
    _asyncio.run(init_db())
    return TestClient(app)


def test_la_route_sources_rend_la_chronologie():
    from app.config import settings
    d = settings.outputs_path / "assets3d" / "job_route"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_cube())
    r = _client().get("/api/etabli/sources")
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()["jobs"]]
    assert "job_route" in ids


def test_la_route_rig_dit_l_absence_de_squelette():
    from app.config import settings
    d = settings.outputs_path / "assets3d" / "job_rig"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_cube())
    r = _client().get("/api/etabli/rig", params={"job": "job_rig", "version": 1})
    assert r.status_code == 200
    assert r.json()["a_squelette"] is False


def test_la_route_extraire_ecrit_une_version_de_plus():
    from app.config import settings
    d = settings.outputs_path / "assets3d" / "job_extr"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_cube_et_sol())
    r = _client().post("/api/etabli/extraire",
                       json={"job": "job_extr", "version": 1, "noeuds": [0]})
    assert r.status_code == 200
    assert r.json()["version"] == 2
    assert (d / "model.v2.glb").is_file()
    assert (d / "model.glb").is_file()          # jamais d'ecrasement


def test_la_route_extraire_refuse_un_job_inconnu():
    r = _client().post("/api/etabli/extraire",
                       json={"job": "nexiste_pas", "version": 1, "noeuds": [0]})
    assert r.status_code == 404


def test_les_refus_du_socle_sortent_en_400_pas_en_500():
    """Trois tâches ont durci ces refus POUR ces routes. Si l'une d'elles
    sortait en 500, tout ce travail serait perdu à la dernière marche."""
    from app.config import settings
    d = settings.outputs_path / "assets3d" / "job_400"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_cube())
    c = _client()

    # transforms qui n'est pas un dictionnaire
    r = c.post("/api/etabli/transformer",
               json={"job": "job_400", "version": 1, "transforms": [1, 2]})
    assert r.status_code == 400, r.text

    # quaternion non normé
    r = c.post("/api/etabli/transformer",
               json={"job": "job_400", "version": 1,
                     "transforms": {"0": {"rotation": [0, 0, 0, 2]}}})
    assert r.status_code == 400, r.text

    # axe haut inconnu
    r = c.post("/api/etabli/reparer",
               json={"job": "job_400", "version": 1, "axe_haut": "Q"})
    assert r.status_code == 400, r.text

    # echelle de mauvais type
    r = c.post("/api/etabli/reparer",
               json={"job": "job_400", "version": 1, "echelle": [1.0]})
    assert r.status_code == 400, r.text

    # selection vide
    r = c.post("/api/etabli/extraire",
               json={"job": "job_400", "version": 1, "noeuds": []})
    assert r.status_code == 400, r.text


def test_la_route_adopter_fait_entrer_une_tache_meshy():
    from app.config import settings
    src = settings.outputs_path / "meshy3d" / "tache_route"
    src.mkdir(parents=True, exist_ok=True)
    (src / "model.glb").write_bytes(_cube())
    r = _client().post("/api/etabli/adopter", json={"task_id": "tache_route"})
    assert r.status_code == 200
    assert r.json()["job"] == "meshy_tache_route"
    r = _client().post("/api/etabli/adopter", json={"task_id": "absente"})
    assert r.status_code == 404


# ── I. l'assise sur une face : Rodrigues, contact, empilement ────────────────
# Lot B de la plaque façon slicer. La fixture est une BOÎTE INCLINÉE
# ASYMÉTRIQUE : le cube du banc (24 sommets, coutures UV sur chaque arête)
# sous un nœud à trois angles non nuls, une échelle NON UNIFORME (1,3 ; 0,7 ;
# 0,4) et une translation. Rien n'y est l'identité, aucun zéro où une erreur
# d'axe ou de signe pourrait se cacher — le défaut des données trop
# symétriques est revenu quatre fois sur ce chantier.

import hashlib
import math


def _quaternion_xyz(rx: float, ry: float, rz: float) -> list[float]:
    """Quaternion [x, y, z, w] d'une rotation XYZ intrinsèque — SECOND chemin,
    indépendant de three.js et de mesh_edit."""
    def q_axe(k, a):
        q = [0.0, 0.0, 0.0, math.cos(a / 2)]
        q[k] = math.sin(a / 2)
        return q

    def mul(a, b):
        ax, ay, az, aw = a
        bx, by, bz, bw = b
        return [aw * bx + ax * bw + ay * bz - az * by,
                aw * by - ax * bz + ay * bw + az * bx,
                aw * bz + ax * by - ay * bx + az * bw,
                aw * bw - ax * bx - ay * by - az * bz]
    q = mul(mul(q_axe(0, rx), q_axe(1, ry)), q_axe(2, rz))
    n = math.sqrt(sum(c * c for c in q))
    return [c / n for c in q]


_POSE_BOITE = {"translation": [0.3, -0.2, 0.5],
               "rotation": _quaternion_xyz(0.3, -0.7, 0.45),
               "scale": [1.3, 0.7, 0.4]}


def _boite_inclinee() -> bytes:
    from app.services import mesh_edit
    return mesh_edit.transformer(_cube(), {"0": _POSE_BOITE})


def _normale_de(t):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
    ln = math.sqrt(sum(c * c for c in n))
    return tuple(c / ln for c in n)


def _sommets_distincts(tris):
    return sorted({v for t in tris for v in t})


def _distances(pts):
    return [math.dist(pts[i], pts[j]) for i in range(len(pts))
            for j in range(i + 1, len(pts))]


def _volume(tris) -> float:
    """Volume signé par le théorème de la divergence — chaque triangle en
    tétraèdre avec l'origine. Un enroulement incohérent le fausse : c'est ce
    qui en fait un juge des capuchons, pas seulement des positions."""
    v = 0.0
    for (a, b, c) in tris:
        v += (a[0] * (b[1] * c[2] - b[2] * c[1])
              - a[1] * (b[0] * c[2] - b[2] * c[0])
              + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
    return v


def test_l_assise_pose_la_face_designee_vers_le_bas_au_contact_et_sans_deformer():
    """LA PREUVE EXIGÉE, EXÉCUTÉE. Sur la boîte inclinée, la face +X locale
    (les deux premiers triangles du cube) a une normale monde QUELCONQUE et le
    modèle flotte : c'est le témoin — une assise sans rotation, ou sans
    translation de contact, échouerait ici mesurablement. Après `assise` : la
    normale de cette face vaut (0, −1, 0) à 1e-9, le min Y vaut 0 à 1e-9, et
    les huit sommets se retrouvent à une isométrie près — les 28 distances
    deux à deux sont conservées."""
    from app.services import mesh_edit, print3d
    boite = _boite_inclinee()
    avant = print3d.lire_glb_triangles(boite)
    n0 = _normale_de(avant[0])
    ymin0 = print3d.bbox(avant)[1][0]
    # LE TÉMOIN : loin du bas, et loin du sol — sinon la fixture ne prouve rien
    assert math.dist(n0, (0.0, -1.0, 0.0)) > 0.5, n0
    assert abs(ymin0) > 0.1, ymin0
    assert len(_sommets_distincts(avant)) == 8

    pose = mesh_edit.assise(boite, normale=list(n0), point=list(avant[0][0]))
    apres = print3d.lire_glb_triangles(pose)
    n1 = _normale_de(apres[0])
    assert math.dist(n1, (0.0, -1.0, 0.0)) < 1e-9, n1
    assert abs(print3d.bbox(apres)[1][0]) < 1e-9, print3d.bbox(apres)
    # la face désignée est bien POSÉE : ses quatre sommets sont à y = 0
    for t in apres[:2]:
        for v in t:
            assert abs(v[1]) < 1e-9, v
    # ISOMÉTRIE : mêmes distances deux à deux, triangle par triangle (l'ordre
    # des triangles est conservé par le lecteur) — donc mêmes sommets
    d0 = _distances([v for t in avant for v in t])
    d1 = _distances([v for t in apres for v in t])
    assert max(abs(a - b) for a, b in zip(d0, d1)) < 1e-9
    assert abs(_volume(apres) - _volume(avant)) < 1e-9
    # et le pivot est le point cliqué : il n'a pas bougé dans le plan du sol
    assert math.dist(apres[0][0][::2], avant[0][0][::2]) < 1e-9


def test_deux_assises_EMPILENT_deux_noeuds_sans_toucher_le_premier():
    """L'invariant de `reparer`, tenu par `assise` : un nœud `etabli_correction`
    NEUF à chaque fois, la matrice du premier intacte au bit près, le TRS du
    nœud d'origine jamais réécrit — et la seconde face descend à son tour."""
    from app.services import mesh_edit, print3d
    boite = _boite_inclinee()
    t0 = print3d.lire_glb_triangles(boite)
    une = mesh_edit.assise(boite, normale=list(_normale_de(t0[0])),
                           point=list(t0[0][0]))
    d1, _ = mesh_edit.lire_glb(une)
    t1 = print3d.lire_glb_triangles(une)
    # la face +Y locale : triangles 4 et 5 du cube
    deux = mesh_edit.assise(une, normale=list(_normale_de(t1[4])),
                            point=list(t1[4][0]))
    d2, _ = mesh_edit.lire_glb(deux)
    noms = [n.get("name") for n in d2["nodes"]]
    assert noms == ["cube", "etabli_correction", "etabli_correction"], noms
    assert d2["nodes"][1]["matrix"] == d1["nodes"][1]["matrix"]
    assert d2["nodes"][0] == d1["nodes"][0]
    assert d2["nodes"][0]["rotation"] == _POSE_BOITE["rotation"]
    assert d2["scenes"][0]["nodes"] == [2]
    assert d2["nodes"][2]["children"] == [1]
    t2 = print3d.lire_glb_triangles(deux)
    assert math.dist(_normale_de(t2[4]), (0.0, -1.0, 0.0)) < 1e-9
    assert abs(print3d.bbox(t2)[1][0]) < 1e-9


def test_l_assise_refuse_une_normale_nulle_ou_non_finie_et_un_glb_compresse():
    """Ces valeurs viennent d'un corps JSON : les refus sont des ValueError,
    que la route traduit en 400. Le GLB compressé refuse pour la raison de
    `recentrer` — la translation de contact lit la géométrie."""
    from app.services import mesh_edit
    boite = _boite_inclinee()
    with pytest.raises(ValueError, match="nulle"):
        mesh_edit.assise(boite, normale=[0, 0, 0])
    with pytest.raises(ValueError, match="non finie"):
        mesh_edit.assise(boite, normale=[float("nan"), 1, 0])
    with pytest.raises(ValueError, match="trois nombres"):
        mesh_edit.assise(boite, normale=[1, 0])
    with pytest.raises(ValueError, match="trois nombres"):
        mesh_edit.assise(boite, normale="0,1,0")
    with pytest.raises(ValueError, match="attend des nombres"):
        mesh_edit.assise(boite, normale=[True, 0, 0])
    with pytest.raises(ValueError, match="point"):
        mesh_edit.assise(boite, normale=[0, 1, 0], point=[1, 2])
    with pytest.raises(ValueError, match="draco"):
        mesh_edit.assise(_cube_compresse(), normale=[0, 1, 0])


def test_rodrigues_tient_les_cas_alignes_et_opposes():
    """La formule diverge quand a et b sont opposés (s = 0) : le demi-tour
    autour d'un axe perpendiculaire doit quand même sortir, orthonormé, de
    déterminant +1, et envoyer a sur b."""
    from app.services import mesh_edit
    for a, b in (((0, 1, 0), (0, -1, 0)), ((1, 0, 0), (-1, 0, 0)),
                 ((0.6, 0.0, 0.8), (-0.6, 0.0, -0.8)), ((0, 1, 0), (0, 1, 0)),
                 ((0.36, 0.48, 0.8), (0, -1, 0))):
        r = mesh_edit._rodrigues(a, b)
        assert math.dist(mesh_edit._appliquer3(r, a), b) < 1e-12, (a, b, r)
        for i in range(3):
            for j in range(3):
                dot = sum(r[i][k] * r[j][k] for k in range(3))
                assert abs(dot - (1.0 if i == j else 0.0)) < 1e-12
        det = (r[0][0] * (r[1][1] * r[2][2] - r[1][2] * r[2][1])
               - r[0][1] * (r[1][0] * r[2][2] - r[1][2] * r[2][0])
               + r[0][2] * (r[1][0] * r[2][1] - r[1][1] * r[2][0]))
        assert abs(det - 1.0) < 1e-12, det
    assert mesh_edit._rodrigues((0, 1, 0), (0, 1, 0)) == mesh_edit._I3



# Deux figures qui servent à plusieurs bancs — UNE définition chacune. Le nœud
# papillon se croise : aucune oreille ne se présente. L'aiguille est une
# section d'épaisseur quasi nulle (1 sur 8e-13) : l'aire passe encore
# l'epsilon de la triangulation, plus aucun coin ne le passe.
_PAPILLON = [(0, 0), (2, 2), (2, 0), (0, 2)]
_H_AIGUILLE = 8e-13
_AIGUILLE = [(0, 0), (0.5, 0), (1, 0), (1, _H_AIGUILLE), (0.5, _H_AIGUILLE),
             (0, _H_AIGUILLE)]

# ── J. le couteau : deux moitiés FERMÉES, ni plus ni moins de volume ─────────

_PLAN_OBLIQUE = ((0.05, -0.03, 0.02), (0.3, 0.5, -0.8))


def _plan_de_la_boite(tris):
    """Un plan OBLIQUE (aucune composante nulle) près du centre de la boîte,
    décalé pour qu'il ne passe par aucun sommet ni aucun centre de face."""
    from app.services import print3d
    (x0, x1), (y0, y1), (z0, z1) = print3d.bbox(tris)
    dp, n = _PLAN_OBLIQUE
    c = ((x0 + x1) / 2 + dp[0], (y0 + y1) / 2 + dp[1], (z0 + z1) / 2 + dp[2])
    ln = math.sqrt(sum(v * v for v in n))
    return list(c), [v / ln for v in n]


def _distance(p, point, normale):
    return sum((p[k] - point[k]) * normale[k] for k in range(3))


def _lire_primitive(doc, binc, pr):
    from app.services import mesh_cut, mesh_edit
    pos = mesh_cut._lire_accesseur(doc, binc, pr["attributes"]["POSITION"])
    idx = [t[0] for t in mesh_cut._lire_accesseur(doc, binc, pr["indices"])]
    return pos, idx


def _aretes_non_appariees(doc, binc, mesh):
    """Les arêtes dirigées d'un maillage, PAR POSITION, qui n'apparaissent pas
    exactement une fois dans chaque sens — une surface fermée à enroulement
    cohérent n'en a aucune. Par position et non par index : le capuchon porte
    ses propres sommets (sa normale est celle du plan, pas celle de la paroi),
    et un slicer soude par position."""
    aretes: dict = {}
    for pr in mesh["primitives"]:
        pos, idx = _lire_primitive(doc, binc, pr)
        for k in range(0, len(idx), 3):
            p = [pos[idx[k]], pos[idx[k + 1]], pos[idx[k + 2]]]
            for e in range(3):
                cle = (p[e], p[(e + 1) % 3])
                aretes[cle] = aretes.get(cle, 0) + 1
    return [(a, b) for (a, b), c in aretes.items()
            if c != 1 or aretes.get((b, a), 0) != 1]


def _noeud_nomme(doc, nom):
    return next(i for i, n in enumerate(doc["nodes"]) if n.get("name") == nom)


def _triangles_du_noeud(data, nom):
    """Les triangles MONDE du seul nœud `nom` — par extraction, le lecteur
    éprouvé, et non par un filtre maison."""
    from app.services import mesh_cut, mesh_edit, print3d
    doc, _ = mesh_edit.lire_glb(data)
    return print3d.lire_glb_triangles(mesh_edit.extraire(data, [_noeud_nomme(doc, nom)]))


def test_les_deux_moities_sont_FERMEES_et_leurs_volumes_font_le_volume_d_origine():
    """LA PREUVE EXIGÉE, EXÉCUTÉE, sur la boîte inclinée coupée par un plan
    oblique. Les GARDE-FOUS d'abord : la fixture a 24 sommets pour 8 positions
    (coutures UV partout — la section doit se recoudre par position), une
    échelle non uniforme (la normale du plan ne se « tourne » pas dans le
    repère local, elle se transpose), aucune composante nulle à la normale,
    aucun sommet à moins de 1e-3 du plan.

    Puis les mesures : chaque moitié est FERMÉE (chaque arête dirigée exactement
    une fois dans chaque sens, comptée par position), la somme des volumes
    signés vaut le volume d'origine à 1e-9 (donc les capuchons sont là ET
    bien orientés), aucun sommet n'est du mauvais côté au-delà de 1e-9, les
    matériaux et le nom sont portés, et le compte rendu dit les capuchons."""
    from app.services import mesh_cut, mesh_edit, print3d
    boite = _boite_inclinee()
    doc0, binc0 = mesh_edit.lire_glb(boite)
    pos0, _ = _lire_primitive(doc0, binc0, doc0["meshes"][0]["primitives"][0])
    assert len(pos0) == 24 and len(set(pos0)) == 8
    assert len(set(_POSE_BOITE["scale"])) == 3
    avant = print3d.lire_glb_triangles(boite)
    point, normale = _plan_de_la_boite(avant)
    assert all(abs(c) > 0.1 for c in normale), normale
    assert min(abs(_distance(v, point, normale)) for t in avant for v in t) > 1e-3
    v_avant = _volume(avant)
    assert v_avant > 0.1

    coupe, rapport = mesh_cut.couper(boite, [0], point, normale, "deux")
    doc, binc = mesh_edit.lire_glb(coupe)
    noms = [n.get("name") for n in doc["nodes"]]
    assert noms == ["cube_a", "cube_b"], noms
    for n in doc["nodes"]:
        m = doc["meshes"][n["mesh"]]
        # FERMÉE : pas une arête sans sa jumelle
        assert _aretes_non_appariees(doc, binc, m) == [], n["name"]
        assert doc["materials"][m["primitives"][0]["material"]]["name"] == "banc"
        assert set(m["primitives"][0]["attributes"]) == {
            "POSITION", "NORMAL", "TEXCOORD_0", "TANGENT"}
        # la pose du nœud d'origine est portée telle quelle par ses moitiés
        assert n["rotation"] == _POSE_BOITE["rotation"]
        assert n["scale"] == _POSE_BOITE["scale"]
    # LES VOLUMES : a + b = tout, et chacun est franchement non nul
    va = _volume(_triangles_du_noeud(coupe, "cube_a"))
    vb = _volume(_triangles_du_noeud(coupe, "cube_b"))
    assert va > 0.1 and vb > 0.1, (va, vb)
    assert abs(va + vb - v_avant) < 1e-9, (va, vb, v_avant)
    # AUCUN SOMMET DU MAUVAIS CÔTÉ. Deux bornes, parce qu'il y a deux nombres :
    # en flottant 64, avant l'écriture, un point de section est SUR le plan à
    # 1e-12 et chaque sommet est strictement de son côté ; dans le FICHIER, les
    # positions sont des flottants 32 bits et un point de section s'écarte du
    # plan de ce que cette quantification permet — mesuré −4,6e-9 en monde,
    # borné par 1e-7 (un demi-ulp de f32 à l'ordre de grandeur 1, fois
    # l'échelle 1,3 et la norme de la normale locale).
    nl, cl = mesh_cut._plan_local(mesh_edit._mat_locale(doc0["nodes"][0]), point, normale)
    idx0 = [t[0] for t in mesh_cut._lire_accesseur(doc0, binc0, doc0["meshes"][0]["primitives"][0]["indices"])]
    d0 = [nl[0] * p[0] + nl[1] * p[1] + nl[2] * p[2] + cl for p in pos0]
    ca, cb, segs, copl = mesh_cut._decouper_primitive(["POSITION"], [pos0], idx0, d0, None, nl)
    assert copl == 0                      # aucun triangle dans le plan oblique
    for cote, signe in ((ca, 1), (cb, -1)):
        for p in cote.cols[0]:
            dl = nl[0] * p[0] + nl[1] * p[1] + nl[2] * p[2] + cl
            assert signe * dl > -1e-12, (signe, p, dl)
    for p, q in segs:
        for s in (p, q):
            assert abs(nl[0] * s[0] + nl[1] * s[1] + nl[2] * s[2] + cl) < 1e-12
    assert len(segs) >= 6
    for nom, signe in (("cube_a", 1), ("cube_b", -1)):
        for t in _triangles_du_noeud(coupe, nom):
            for v in t:
                assert signe * _distance(v, point, normale) > -1e-7, (nom, v)
    # LE COMPTE RENDU
    piece = rapport["pieces"][0]
    assert piece["traversee"] is True and piece["retire"] == []
    for cote in ("a", "b"):
        cr = piece["cotes"][cote]
        assert cr["capuchon"]["pose"] is True and cr["capuchon"]["boucles"] == 1
        assert cr["capuchon"]["triangles"] >= 4
        assert 0 <= cr["capuchon"]["degeneres"] < cr["capuchon"]["triangles"]
        assert cr["noeud_apres"] == _noeud_nomme(doc, f"cube_{cote}")
        assert cr["nom"] == f"cube_{cote}"
    assert rapport["plan"]["repere"] == "monde" and rapport["garder"] == "deux"
    assert rapport["capuchons"]["uv"] == [0, 0]
    # le maillage d'origine, orphelin, n'est PAS recopié
    assert len(doc["meshes"]) == 2
    # et le fichier se relit par le lecteur de print3d, capuchons compris
    assert len(print3d.lire_glb_triangles(coupe)) == sum(
        piece["cotes"][c]["triangles"] for c in ("a", "b"))


def test_les_UV_et_normales_interpolees_sont_la_combinaison_barycentrique_de_l_arete():
    """Chaque sommet NEUF d'une moitié (une position absente des huit
    d'origine, hors capuchon) est sur une arête d'un triangle d'origine, et ses
    UV valent exactement (1 − t)·uv_i + t·uv_j pour le t de sa position — au
    flottant 32 bits près, qui est le format du fichier. La normale est la
    même combinaison, renormée. Les sommets du capuchon, eux, portent l'UV
    (0, 0) et la normale du plan."""
    from app.services import mesh_cut, mesh_edit, print3d
    boite = _boite_inclinee()
    avant = print3d.lire_glb_triangles(boite)
    point, normale = _plan_de_la_boite(avant)
    coupe, rapport = mesh_cut.couper(boite, [0], point, normale, "deux")
    doc0, binc0 = mesh_edit.lire_glb(boite)
    pr0 = doc0["meshes"][0]["primitives"][0]
    pos0, idx0 = _lire_primitive(doc0, binc0, pr0)
    uv0 = mesh_cut._lire_accesseur(doc0, binc0, pr0["attributes"]["TEXCOORD_0"])
    nrm0 = mesh_cut._lire_accesseur(doc0, binc0, pr0["attributes"]["NORMAL"])
    aretes0 = set()
    for k in range(0, len(idx0), 3):
        for e in range(3):
            aretes0.add((idx0[k + e], idx0[k + (e + 1) % 3]))
    doc, binc = mesh_edit.lire_glb(coupe)
    verifies = 0
    capuchon = 0
    for n in doc["nodes"]:
        pr = doc["meshes"][n["mesh"]]["primitives"][0]
        pos, _ = _lire_primitive(doc, binc, pr)
        uv = mesh_cut._lire_accesseur(doc, binc, pr["attributes"]["TEXCOORD_0"])
        nrm = mesh_cut._lire_accesseur(doc, binc, pr["attributes"]["NORMAL"])
        for k, p in enumerate(pos):
            if p in set(pos0):
                continue
            if uv[k] == (0.0, 0.0):
                capuchon += 1
                continue
            trouve = False
            for (i, j) in aretes0:
                a, b = pos0[i], pos0[j]
                ab = [b[m] - a[m] for m in range(3)]
                l2 = sum(c * c for c in ab)
                t = sum((p[m] - a[m]) * ab[m] for m in range(3)) / l2
                if not (1e-6 < t < 1 - 1e-6):
                    continue
                if math.dist(p, [a[m] + t * ab[m] for m in range(3)]) > 1e-6:
                    continue
                uv_att = tuple(uv0[i][m] + t * (uv0[j][m] - uv0[i][m]) for m in range(2))
                n_att = [nrm0[i][m] + t * (nrm0[j][m] - nrm0[i][m]) for m in range(3)]
                ln = math.sqrt(sum(c * c for c in n_att))
                n_att = [c / ln for c in n_att]
                if math.dist(uv[k], uv_att) < 1e-6 and math.dist(nrm[k], n_att) < 1e-6:
                    trouve = True
                    break
            assert trouve, (n["name"], k, p, uv[k])
            verifies += 1
    # le garde-fou : la coupe a bien créé des sommets sur des arêtes, et un
    # capuchon — sinon ce banc est vert sur du vide
    assert verifies >= 8, verifies
    assert capuchon >= 6, capuchon


def test_garder_a_ou_b_ne_produit_qu_une_moitie_fermee_et_le_dit():
    from app.services import mesh_cut, mesh_edit, print3d
    boite = _boite_inclinee()
    avant = print3d.lire_glb_triangles(boite)
    point, normale = _plan_de_la_boite(avant)
    deux, _ = mesh_cut.couper(boite, [0], point, normale, "deux")
    va = _volume(_triangles_du_noeud(deux, "cube_a"))
    vb = _volume(_triangles_du_noeud(deux, "cube_b"))
    for cote, attendu in (("a", va), ("b", vb)):
        seule, rapport = mesh_cut.couper(boite, [0], point, normale, cote)
        doc, binc = mesh_edit.lire_glb(seule)
        assert [n.get("name") for n in doc["nodes"]] == [f"cube_{cote}"]
        assert _aretes_non_appariees(doc, binc, doc["meshes"][0]) == []
        assert abs(_volume(print3d.lire_glb_triangles(seule)) - attendu) < 1e-9
        piece = rapport["pieces"][0]
        assert piece["retire"] == ["b" if cote == "a" else "a"]
        assert list(piece["cotes"]) == [cote]


def test_le_couteau_refuse_ce_qu_il_ne_sait_pas_couper_en_le_disant():
    """Aucune sélection, un plan qui ne traverse rien, une normale nulle, un
    `garder` inconnu, un nœud hors document, un contenant sans maillage, un
    GLB compressé : sept refus NOMMÉS — jamais une version écrite pour rien."""
    from app.services import mesh_cut, mesh_edit, print3d
    boite = _boite_inclinee()
    avant = print3d.lire_glb_triangles(boite)
    point, normale = _plan_de_la_boite(avant)
    with pytest.raises(ValueError, match="jamais tout le modèle"):
        mesh_cut.couper(boite, [], point, normale)
    with pytest.raises(ValueError, match="ne traverse aucune"):
        mesh_cut.couper(boite, [0], [50.0, 0.0, 0.0], normale)
    with pytest.raises(ValueError, match="nulle"):
        mesh_cut.couper(boite, [0], point, [0, 0, 0])
    with pytest.raises(ValueError, match="garder attend"):
        mesh_cut.couper(boite, [0], point, normale, "c")
    with pytest.raises(ValueError, match="hors du document"):
        mesh_cut.couper(boite, [4], point, normale)
    with pytest.raises(ValueError, match="entiers"):
        mesh_cut.couper(boite, ["x"], point, normale)
    doc, binc = mesh_edit.lire_glb(boite)
    doc["nodes"].append({"name": "boite", "children": [0]})
    doc["scenes"][0]["nodes"] = [1]
    with pytest.raises(ValueError, match="sans maillage"):
        mesh_cut.couper(mesh_edit.ecrire_glb(doc, binc), [1], point, normale)
    with pytest.raises(ValueError, match="draco"):
        mesh_cut.couper(_cube_compresse(), [0], point, normale)
    # une pièce que le plan ne traverse pas est GARDÉE telle quelle si son
    # côté l'est, et une seconde pièce traversée fait quand même une version
    doc, binc = mesh_edit.lire_glb(_cube_et_sol())
    deux_pieces = mesh_edit.ecrire_glb(doc, binc)
    tris = print3d.lire_glb_triangles(deux_pieces)
    (x0, x1), (y0, y1), (z0, z1) = print3d.bbox(tris)
    # le sol est sous le cube : un plan horizontal à mi-cube coupe le cube et
    # laisse le sol entier du côté b
    coupe, rapport = mesh_cut.couper(deux_pieces, [0, 1], [0.0, 0.0, 0.0],
                                      [0.0, 1.0, 0.0], "deux")
    sol = next(p for p in rapport["pieces"] if p["nom"] == "stage")
    assert sol["traversee"] is False and sol["entier"] == "b" and sol["retire"] == []
    docc, _ = mesh_edit.lire_glb(coupe)
    assert sorted(n.get("name") for n in docc["nodes"]) == ["cube_a", "cube_b", "stage"]
    # …et `garder="a"` retire le sol, en le disant
    coupe, rapport = mesh_cut.couper(deux_pieces, [0, 1], [0.0, 0.0, 0.0],
                                      [0.0, 1.0, 0.0], "a")
    sol = next(p for p in rapport["pieces"] if p["nom"] == "stage")
    assert sol["retire"] == ["b"]
    docc, _ = mesh_edit.lire_glb(coupe)
    assert [n.get("name") for n in docc["nodes"]] == ["cube_a"]


def test_la_triangulation_par_oreilles_couvre_chaque_arete_UNE_fois_et_garde_l_aire():
    """Le capuchon n'est étanche que si chaque arête de la boucle appartient à
    exactement un triangle — y compris les arêtes entre points ALIGNÉS, que la
    section d'une face plane produit par centaines. Un L concave avec des
    points alignés sur ses bords : n − 2 triangles, chaque arête du polygone
    une fois, aire totale conservée, tous dans le même sens. Un nœud papillon
    (auto-intersection) : None."""
    from app.services import mesh_cut, mesh_edit
    L = [(0, 0), (1, 0), (2, 0), (3, 0), (3, 1), (2, 1), (1, 1), (1, 2), (1, 3),
         (0, 3), (0, 2), (0, 1)]
    tris = mesh_cut._trianguler(L)
    assert tris is not None and len(tris) == len(L) - 2
    aretes = {}
    aire = 0.0
    for (i, j, k) in tris:
        (ax, ay), (bx, by), (cx, cy) = L[i], L[j], L[k]
        a2 = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        assert a2 >= 0, (i, j, k)          # tous dans le sens de la boucle
        aire += a2 / 2
        for e in ((i, j), (j, k), (k, i)):
            aretes[e] = aretes.get(e, 0) + 1
    assert abs(aire - 5.0) < 1e-12, aire
    for i in range(len(L)):
        e = (i, (i + 1) % len(L))
        assert aretes.get(e, 0) == 1, (e, aretes.get(e))
        assert aretes.get((e[1], e[0]), 0) == 0
    # les arêtes intérieures vont deux fois, une par sens
    for (i, j), c in aretes.items():
        if (j - i) % len(L) != 1:
            assert c == 1 and aretes.get((j, i), 0) == 1, (i, j)
    # le sens inverse donne le même résultat
    assert len(mesh_cut._trianguler(list(reversed(L)))) == len(L) - 2
    assert mesh_cut._trianguler(_PAPILLON) is None
    assert mesh_cut._trianguler([(0, 0), (1, 1), (2, 2)]) is None   # plat
    # LE FILET DES OREILLES PLATES, ET IL FAUT UNE AIGUILLE POUR L'ATTEINDRE :
    # tant qu'une oreille convexe passe l'epsilon, elle est prise d'abord
    # (le L ci-dessus n'a jamais coupé d'oreille plate — mutation verte). Une
    # section d'épaisseur quasi nulle — 1 sur 8e-13, l'aire passe encore
    # l'epsilon, plus aucun coin ne le passe — n'a QUE des oreilles plates :
    # chacune doit émettre son triangle, sinon des arêtes du capuchon restent
    # sans jumelle. n − 2 triangles, chaque arête de la boucle une fois.
    aiguille = _AIGUILLE
    tris = mesh_cut._trianguler(aiguille)
    assert tris is not None and len(tris) == len(aiguille) - 2, tris
    bords = {}
    for (i, j, k) in tris:
        for e in ((i, j), (j, k), (k, i)):
            bords[e] = bords.get(e, 0) + 1
    for i in range(len(aiguille)):
        e = (i, (i + 1) % len(aiguille))
        assert bords.get(e, 0) + bords.get((e[1], e[0]), 0) == 1, (e, bords)


def test_un_capuchon_refuse_les_boucles_imbriquees_et_dit_une_surface_ouverte():
    """Deux boucles emboîtées (la section d'un tube) ne se bouchent pas :
    boucher chacune remplirait le trou. Une chaîne ouverte n'a rien à
    boucher. Dans les deux cas le compte rendu le DIT — jamais de géométrie
    fausse en silence."""
    from app.services import mesh_cut, mesh_edit
    n = (0.0, 0.0, 1.0)
    noms = ["POSITION", "NORMAL", "TEXCOORD_0"]
    ext = [(0, 0, 0), (4, 0, 0), (4, 4, 0), (0, 4, 0)]
    trou = [(1, 1, 0), (1, 3, 0), (3, 3, 0), (3, 1, 0)]
    s, t, cr = mesh_cut._capuchon([ext, trou], [], n, (0, 0, -1), noms, 1)
    assert s == [] and t == [] and cr["pose"] is False
    assert "imbriquées" in cr["raison"] and cr["boucles"] == 2
    s, t, cr = mesh_cut._capuchon([], [[(0, 0, 0), (1, 0, 0)]], n, (0, 0, -1), noms, 1)
    assert cr["pose"] is False and "surface ouverte" in cr["raison"]
    assert cr["ouvertes"] == 1
    # deux boucles DISJOINTES se bouchent toutes les deux
    loin = [(10, 0, 0), (14, 0, 0), (14, 4, 0), (10, 4, 0)]
    s, t, cr = mesh_cut._capuchon([ext, loin], [], n, (0, 0, -1), noms, 1)
    assert cr["pose"] is True and cr["boucles"] == 2 and len(t) == 4
    assert cr["degeneres"] == 0
    assert all(v[1] == (0, 0, -1) and v[2] is None for v in s)
    # LA TROISIÈME RAISON, fermée (revue : la famille des refus n'était couverte
    # qu'aux deux tiers) — une boucle qui se croise, un nœud papillon, ne se
    # triangule pas : pas de capuchon, et c'est DIT
    papillon = [(x, y, 0) for x, y in _PAPILLON]
    s, t, cr = mesh_cut._capuchon([papillon], [], n, (0, 0, -1), noms, 1)
    assert s == [] and t == [] and cr["pose"] is False
    assert "non triangulable" in cr["raison"] and cr["boucles"] == 1
    # et une section en AIGUILLE se bouche en DISANT ses triangles plats
    aiguille = [(x, y, 0) for x, y in _AIGUILLE]
    s, t, cr = mesh_cut._capuchon([aiguille], [], n, (0, 0, -1), noms, 1)
    assert cr["pose"] is True and len(t) == 4
    assert 1 <= cr["degeneres"] <= len(t), cr
    # et les boucles se recousent par POSITION, coutures comprises : le même
    # carré décrit par quatre segments dans un ordre quelconque
    segs = [((0, 0, 0), (4, 0, 0)), ((4, 4, 0), (0, 4, 0)),
            ((0, 4, 0), (0, 0, 0)), ((4, 0, 0), (4, 4, 0))]
    boucles, ouvertes = mesh_cut._boucles(segs)
    assert len(boucles) == 1 and len(boucles[0]) == 4 and ouvertes == []
    boucles, ouvertes = mesh_cut._boucles(segs[:3])
    assert boucles == [] and len(ouvertes) == 1 and len(ouvertes[0]) == 4


_MODELE_REEL = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / \
    "DeepotusVideoGenData" / "assets" / "outputs" / "assets3d" / "6e0a8a5f" / "model.v5.glb"


def test_le_couteau_sur_le_MODELE_REEL_traverse_le_cadre_en_moins_de_5_s_et_dit_une_plaque_ouverte():
    """Le modèle de l'utilisateur (assets3d/6e0a8a5f/model.v5.glb, douze
    pièces, 144 274 triangles), LU et jamais modifié. Le cadre (72 128
    sommets) se coupe en moins de 5 s, ses deux moitiés sont fermées et
    texturées comme lui ; une plaque plate (l'illustration, deux triangles)
    se coupe en deux pièces SANS capuchon — surface ouverte — et le compte
    rendu le dit. Les douze textures alpha restent référencées."""
    import time
    from app.services import mesh_cut, mesh_edit, print3d
    if not _MODELE_REEL.is_file():
        pytest.skip(f"modèle réel absent : {_MODELE_REEL}")
    data = _MODELE_REEL.read_bytes()
    sha_avant = hashlib.sha256(data).hexdigest()
    doc0, _ = mesh_edit.lire_glb(data)
    cadre, illustration = _noeud_nomme(doc0, "cadre"), _noeud_nomme(doc0, "illustration")
    tris = print3d.lire_glb_triangles(data)
    assert len(tris) == 144274
    (x0, x1), (y0, y1), (z0, z1) = print3d.bbox(tris)
    centre = [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]
    normale = [0.6, 0.7, 0.1]                     # oblique, dans le plan de la carte
    t0 = time.perf_counter()
    coupe, rapport = mesh_cut.couper(data, [cadre], centre, normale, "deux")
    duree = time.perf_counter() - t0
    assert duree < 5.0, duree
    doc, binc = mesh_edit.lire_glb(coupe)
    piece = rapport["pieces"][0]
    assert piece["nom"] == "cadre" and piece["triangles"] == 144252
    for cote in ("a", "b"):
        cr = piece["cotes"][cote]
        assert cr["capuchon"]["pose"] is True and cr["capuchon"]["boucles"] == 1
        assert isinstance(cr["capuchon"]["degeneres"], int)
        n = doc["nodes"][cr["noeud_apres"]]
        assert n["name"] == f"cadre_{cote}"
        m = doc["meshes"][n["mesh"]]
        assert _aretes_non_appariees(doc, binc, m) == [], cote
        mat = doc["materials"][m["primitives"][0]["material"]]
        assert mat["name"] == "cadre"
        assert "baseColorTexture" in mat["pbrMetallicRoughness"]
    # quinze nœuds : douze pièces moins le cadre, plus ses deux moitiés, le
    # contenant carte3d et la correction d'assise
    assert len(doc["nodes"]) == 15
    # TOUTES les textures restent référencées par un matériau
    assert len(doc["images"]) == 12
    refs = {doc["textures"][r["index"]]["source"]
            for mt in doc["materials"] for r in mesh_edit._renvois_de_texture(mt)}
    assert refs == set(range(12))
    assert sum(1 for mt in doc["materials"] if mt.get("alphaMode") == "BLEND") == 11
    # LA PLAQUE PLATE : deux pièces, aucun capuchon, et c'est DIT
    coupe2, rapport2 = mesh_cut.couper(data, [illustration], centre, normale, "deux")
    piece2 = rapport2["pieces"][0]
    assert piece2["nom"] == "illustration" and piece2["triangles"] == 2
    for cote in ("a", "b"):
        cr = piece2["cotes"][cote]
        assert cr["capuchon"]["pose"] is False
        assert "surface ouverte" in cr["capuchon"]["raison"]
        assert cr["capuchon"]["ouvertes"] == 1 and cr["capuchon"]["boucles"] == 0
        assert cr["triangles"] == 3
    doc2, binc2 = mesh_edit.lire_glb(coupe2)
    n_a = doc2["nodes"][piece2["cotes"]["a"]["noeud_apres"]]
    assert _aretes_non_appariees(doc2, binc2, doc2["meshes"][n_a["mesh"]]) != []
    # et le fichier de l'utilisateur n'a pas bougé d'un octet
    assert hashlib.sha256(_MODELE_REEL.read_bytes()).hexdigest() == sha_avant


# ── K. les routes du lot B ───────────────────────────────────────────────────

def test_la_route_assise_ecrit_une_version_posee_et_refuse_les_corps_invalides():
    from app.config import settings
    from app.services import mesh_cut, mesh_edit, print3d
    d = settings.outputs_path / "assets3d" / "job_assise"
    d.mkdir(parents=True, exist_ok=True)
    boite = _boite_inclinee()
    (d / "model.glb").write_bytes(boite)
    avant = print3d.lire_glb_triangles(boite)
    n0 = list(_normale_de(avant[0]))
    c = _client()
    r = c.post("/api/etabli/assise", json={"job": "job_assise", "version": 1,
                                           "normale": n0, "point": list(avant[0][0])})
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 2 and r.json()["source"]["operation"] == "assise"
    assert r.json()["source"]["depuis"] == {"version": 1, "fichier": "model.glb"}
    assert r.json()["source"]["normale"] == n0
    apres = print3d.lire_glb_triangles((d / "model.v2.glb").read_bytes())
    assert math.dist(_normale_de(apres[0]), (0.0, -1.0, 0.0)) < 1e-6
    assert abs(print3d.bbox(apres)[1][0]) < 1e-6
    assert (d / "model.glb").is_file()
    # les refus, tous en 400 — et le job inconnu en 404
    for corps, attendu in (
            ({"job": "job_assise", "version": 1, "normale": [0, 0, 0]}, 400),
            ({"job": "job_assise", "version": 1, "normale": "abc"}, 400),
            ({"job": "job_assise", "version": 1, "normale": [1, 0]}, 400),
            ({"job": "job_assise", "version": 1, "normale": [0, 1, 0], "point": [1]}, 400),
            ({"job": "job_assise", "version": 0, "normale": [0, 1, 0]}, 400),
            ({"job": "job_assise", "version": "1", "normale": [0, 1, 0]}, 400),
            ({"job": "..", "version": 1, "normale": [0, 1, 0]}, 400),
            ({"job": 12, "version": 1, "normale": [0, 1, 0]}, 400),
            ({"job": "nexiste_pas", "version": 1, "normale": [0, 1, 0]}, 404)):
        r = c.post("/api/etabli/assise", json=corps)
        assert r.status_code == attendu, (corps, r.status_code, r.text)
    # rien de tout cela n'a écrit de version
    assert not (d / "model.v3.glb").exists()
    # et le GLB compressé refuse en 400, avec le mot
    (d / "model.v3.glb").write_bytes(_cube_compresse())
    r = c.post("/api/etabli/assise", json={"job": "job_assise", "version": 3,
                                           "normale": [0, 1, 0]})
    assert r.status_code == 400 and "draco" in r.text


def test_la_route_couper_ecrit_une_version_avec_son_compte_rendu_et_refuse_les_corps_invalides():
    from app.config import settings
    from app.services import mesh_cut, mesh_edit, print3d
    d = settings.outputs_path / "assets3d" / "job_couteau"
    d.mkdir(parents=True, exist_ok=True)
    boite = _boite_inclinee()
    (d / "model.glb").write_bytes(boite)
    point, normale = _plan_de_la_boite(print3d.lire_glb_triangles(boite))
    c = _client()
    corps = {"job": "job_couteau", "version": 1, "noeuds": [0],
             "point": point, "normale": normale, "garder": "deux"}
    r = c.post("/api/etabli/couper", json=corps)
    assert r.status_code == 200, r.text
    fiche = r.json()
    assert fiche["version"] == 2 and fiche["source"]["operation"] == "couper"
    src = fiche["source"]
    assert src["garder"] == "deux" and src["noeuds_avant"] == [0]
    assert src["depuis"] == {"version": 1, "fichier": "model.glb"}
    assert src["plan"]["repere"] == "monde"
    cotes = src["pieces"][0]["cotes"]
    assert cotes["a"]["capuchon"]["pose"] is True
    assert cotes["b"]["capuchon"]["pose"] is True
    doc, _ = mesh_edit.lire_glb((d / "model.v2.glb").read_bytes())
    assert [n["name"] for n in doc["nodes"]] == ["cube_a", "cube_b"]
    assert doc["nodes"][cotes["a"]["noeud_apres"]]["name"] == "cube_a"
    # le registre porte le compte rendu, là où la Bibliothèque le lira
    registre = json.loads((d / "report.json").read_text("utf-8"))
    entree = next(e for e in registre["entries"] if e["version"] == 2)
    assert entree["source"]["pieces"][0]["cotes"]["a"]["capuchon"]["pose"] is True
    # les refus
    for mauvais, attendu, mot in (
            ({"noeuds": []}, 400, "jamais tout le modèle"),
            ({"noeuds": [7]}, 400, "hors du document"),
            ({"noeuds": ["x"]}, 400, "entier"),
            ({"noeuds": [-1]}, 400, "entier"),
            ({"noeuds": 0}, 400, "liste"),
            ({"garder": "c"}, 400, "garder"),
            ({"normale": [0, 0, 0]}, 400, "couteau : normale"),
            ({"normale": [0, 0]}, 400, "trois nombres"),
            ({"point": None}, 400, "trois nombres"),
            ({"point": [50, 0, 0]}, 400, "ne traverse aucune"),
            ({"version": "1"}, 400, "version"),
            ({"job": ".."}, 400, "nom de job"),
            ({"job": "nexiste_pas"}, 404, "introuvable")):
        r = c.post("/api/etabli/couper", json={**corps, **mauvais})
        assert r.status_code == attendu, (mauvais, r.status_code, r.text)
        assert mot in r.text, (mauvais, r.text)
    assert not (d / "model.v3.glb").exists()
    # `garder` absent vaut « deux »
    r = c.post("/api/etabli/couper", json={k: v for k, v in corps.items() if k != "garder"})
    assert r.status_code == 200 and r.json()["source"]["garder"] == "deux"


# ── L. la revue du lot B : ce que le couteau ne savait pas dire ──────────────

def test_une_face_CONFONDUE_avec_le_plan_ne_fait_pas_une_piece_de_volume_nul():
    """Le cube et le plan y = 1, sa face du dessus dedans. Un triangle dont les
    trois sommets sont SUR le plan partait côté a comme tout « d ≥ 0 » : quelle
    que soit la normale du plan, `cube_a` faisait quatre triangles de volume
    nul, deux arêtes non appariées, deux capuchons « posés » et un compte rendu
    « traversée » — une feuille double face écrite comme une pièce (revue).
    Un triangle coplanaire part désormais du côté OPPOSÉ à sa normale : c'est
    la peau d'un corps qui vit de l'autre côté. Le cube entier part d'un seul
    côté, et le refus qui existait déjà parle — dans les deux sens du plan,
    et sur la face du dessous aussi. (Le membre NON convexe de la famille — une
    face confondue qui n'est qu'une partie de la frontière — est la marche,
    plus bas.)"""
    from app.services import mesh_cut, mesh_edit
    cube = _cube()
    for point, normale in (([0, 1, 0], [0, 1, 0]), ([0, 1, 0], [0, -1, 0]),
                           ([0, -1, 0], [0, 1, 0]), ([0, -1, 0], [0, -1, 0])):
        with pytest.raises(ValueError, match="ne traverse aucune"):
            mesh_cut.couper(cube, [0], point, normale)
    # et le routage lui-même, sur la primitive : la face du dessus (normale
    # +y) va côté b pour un plan de normale +y, côté a pour −y
    doc, binc = mesh_edit.lire_glb(cube)
    pr = doc["meshes"][0]["primitives"][0]
    pos, idx = _lire_primitive(doc, binc, pr)
    for ny, attendu in ((1.0, "b"), (-1.0, "a")):
        d = [ny * (p[1] - 1.0) for p in pos]
        a, b, segs, copl = mesh_cut._decouper_primitive(["POSITION"], [pos], idx, d, None,
                                                        (0.0, ny, 0.0))
        assert copl == 2                  # la face du dessus, comptée
        dessus = [k for k in range(0, len(idx), 3)
                  if all(pos[idx[k + e]][1] == 1.0 for e in range(3))]
        assert len(dessus) == 2
        # TOUT part du côté de la matière : les douze triangles, dont la face
        # du dessus. Les quatre arêtes du dessus sont bien une « section »,
        # mais d'un seul côté : rien n'est traversé, et couper refuse
        plein, vide = (b, a) if attendu == "b" else (a, b)
        assert len(plein.tris) == 12 and len(vide.tris) == 0
        # …et la « section » n'existe que si les faces latérales sont mixtes :
        # sous +y les sommets du dessus (d = 0, côté a) font face au reste
        # (côté b), quatre arêtes ; sous −y tout est d ≥ 0, aucune
        assert len(segs) == (4 if attendu == "b" else 0)



def test_un_plan_a_1e_9_d_un_sommet_coupe_comme_s_il_passait_par_lui_et_les_moities_sont_FERMEES():
    """Le plan x + y − z = 1 passe par TROIS sommets du cube et détache le coin
    (1, 1, −1) : un tétraèdre de volume 8/6. Décalé de 1e-9, il laissait ces
    trois sommets à un cheveu du plan, classés par signe strict : des aiguilles
    de 1e-9 qui s'effondrent à l'écriture f32 — 5 arêtes non appariées par
    moitié, des triangles plats dans la PAROI, sous un compte rendu « fermé »
    (revue). Tout sommet à moins de 1e-7 · diagonale du plan est ramené dessus
    AVANT classification : le cas exact, prouvé fermé. Mesuré des deux côtés
    du décalage : moitiés fermées, volume du coin 4/3 à 1e-9, somme 8. Et le
    même plan à 1e-9 SOUS la face du dessus (y = 1 − 1e-9) : les quatre sommets
    reviennent sur le plan, la face devient coplanaire, rien n'est traversé."""
    from app.services import mesh_cut, mesh_edit, print3d
    cube = _cube()
    n = [1 / math.sqrt(3), 1 / math.sqrt(3), -1 / math.sqrt(3)]
    for signe in (1, -1):
        point = [1 + signe * 1e-9 * n[0], 1 + signe * 1e-9 * n[1], 1 + signe * 1e-9 * n[2]]
        coupe, rapport = mesh_cut.couper(cube, [0], point, n, "deux")
        doc, binc = mesh_edit.lire_glb(coupe)
        assert [x["name"] for x in doc["nodes"]] == ["cube_a", "cube_b"]
        for x in doc["nodes"]:
            assert _aretes_non_appariees(doc, binc, doc["meshes"][x["mesh"]]) == [], (signe, x["name"])
        va = _volume(_triangles_du_noeud(coupe, "cube_a"))
        vb = _volume(_triangles_du_noeud(coupe, "cube_b"))
        # 1e-8 et non 1e-9 : le plan EST décalé de 1e-9, le coin l'est d'autant
        # fois son aire de section (mesuré : 1,7e-9) ; la somme, elle, est exacte
        assert abs(va - 8.0 / 6.0) < 1e-8, (signe, va)
        assert abs(va + vb - 8.0) < 1e-9, (signe, va, vb)
        for cote in ("a", "b"):
            cap = rapport["pieces"][0]["cotes"][cote]["capuchon"]
            assert cap["pose"] is True and cap["boucles"] == 1
            assert 0 <= cap["degeneres"] < cap["triangles"]
    with pytest.raises(ValueError, match="ne traverse aucune"):
        mesh_cut.couper(cube, [0], [0, 1 - 1e-9, 0], [0, 1, 0])
    # le seuil est celui de l'échelle, et il est dit
    assert mesh_cut._EPS_PLAN == 1e-7


def test_le_compte_rendu_nomme_ses_deux_espaces_d_index_et_la_route_dit_depuis():
    """`noeud_avant` est un index de la version coupée, `noeud_apres` de la
    version neuve compactée — un même mot pour les deux faisait lire le mauvais
    nœud : le sol était 1 dans le compte rendu et 0 dans la version écrite
    (revue). Sur le cube et son sol, plan y = 0 : le sol passe de 1 à 0, le
    cube coupé n'a plus d'index après, ses moitiés en ont un chacune."""
    from app.services import mesh_cut, mesh_edit
    coupe, rapport = mesh_cut.couper(_cube_et_sol(), [0, 1], [0.0, 0.0, 0.0],
                                     [0.0, 1.0, 0.0], "deux")
    doc, _ = mesh_edit.lire_glb(coupe)
    noms = [x.get("name") for x in doc["nodes"]]
    assert rapport["noeuds_avant"] == [0, 1] and "noeuds" not in rapport
    sol = next(p for p in rapport["pieces"] if p["nom"] == "stage")
    cube = next(p for p in rapport["pieces"] if p["nom"] == "cube")
    assert sol["noeud_avant"] == 1 and sol["noeud_apres"] == noms.index("stage") == 0
    assert cube["noeud_avant"] == 0 and cube["noeud_apres"] is None
    assert "noeud" not in sol and "noeud" not in cube
    for cote in ("a", "b"):
        c = cube["cotes"][cote]
        assert "noeud" not in c
        assert noms[c["noeud_apres"]] == f"cube_{cote}"


def test_une_piece_ecartee_par_garder_garde_ses_enfants_comme_CONTENANT():
    """Le sol, entier du côté b, porte un enfant maillé AU-DESSUS du plan, que
    personne n'a demandé de couper. `garder = "a"` retirait le sol de son parent
    ENFANTS COMPRIS, et `retire: ["b"]` ne le disait pas (revue). Le sol reste
    désormais comme contenant sans maillage — le traitement de la pièce
    traversée dont les deux côtés sont écartés — et le compte rendu le dit."""
    from app.services import mesh_cut, mesh_edit, print3d
    doc, binc = mesh_edit.lire_glb(_cube_et_sol())
    doc["nodes"].append({"name": "haut", "mesh": 0, "translation": [0.0, 4.0, 0.0]})
    doc["nodes"][1]["children"] = [2]
    data = mesh_edit.ecrire_glb(doc, binc)
    avant = len(print3d.lire_glb_triangles(data))
    coupe, rapport = mesh_cut.couper(data, [0, 1], [0.0, 0.0, 0.0], [0.0, 1.0, 0.0], "a")
    docc, _ = mesh_edit.lire_glb(coupe)
    noms = sorted(x.get("name") for x in docc["nodes"])
    assert noms == ["cube_a", "haut", "stage"], noms
    sol_n = next(x for x in docc["nodes"] if x.get("name") == "stage")
    assert "mesh" not in sol_n and [docc["nodes"][c]["name"] for c in sol_n["children"]] == ["haut"]
    sol = next(p for p in rapport["pieces"] if p["nom"] == "stage")
    assert sol["retire"] == ["b"] and sol["contenant"] is True
    assert sol["noeud_apres"] == docc["nodes"].index(sol_n)
    # l'enfant est ENTIER : ses douze triangles sont là, en plus de la moitié
    tris = print3d.lire_glb_triangles(coupe)
    haut = _triangles_du_noeud(coupe, "haut")
    assert len(haut) == 12 and all(v[1] > 2.5 for t in haut for v in t)
    cube = next(p for p in rapport["pieces"] if p["nom"] == "cube")
    assert len(tris) == len(haut) + cube["cotes"]["a"]["triangles"]
    # et sans enfant, la pièce entière écartée disparaît toujours
    coupe2, rapport2 = mesh_cut.couper(_cube_et_sol(), [0, 1], [0.0, 0.0, 0.0],
                                       [0.0, 1.0, 0.0], "a")
    doc2, _ = mesh_edit.lire_glb(coupe2)
    assert [x.get("name") for x in doc2["nodes"]] == ["cube_a"]
    sol2 = next(p for p in rapport2["pieces"] if p["nom"] == "stage")
    assert sol2["retire"] == ["b"] and "contenant" not in sol2 and sol2["noeud_apres"] is None



def test_les_cinq_routes_d_ecriture_jugent_version_et_job_de_la_meme_facon_et_disent_depuis():
    """Deux politiques pour cinq routes sœurs (revue) : les trois de P1 prenaient
    `int(version or 1)` — « 1 », 0, 1,5 ou True ÉCRIVAIENT une version, [1]
    faisait un 500, `job = 12` un 404 là où le lot B disait 400. Toutes passent
    la même porte, et chaque fiche dit `depuis`, la version dont elle part."""
    from app.config import settings
    d = settings.outputs_path / "assets3d" / "job_portes"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_cube())
    c = _client()
    corps = {"extraire": {"noeuds": [0]},
             "transformer": {"transforms": {"0": {"translation": [0, 1, 0]}}},
             "reparer": {"axe_haut": "Y"}}
    for route, charge in corps.items():
        for version in ("1", 0, 1.5, True, [1], None):
            r = c.post(f"/api/etabli/{route}", json={"job": "job_portes", "version": version, **charge})
            assert r.status_code == 400, (route, version, r.status_code, r.text)
            assert "version" in r.text, (route, version, r.text)
        for job in (12, "..", None):
            r = c.post(f"/api/etabli/{route}", json={"job": job, "version": 1, **charge})
            assert r.status_code == 400, (route, job, r.status_code, r.text)
        r = c.post(f"/api/etabli/{route}", json={"job": "nexiste_pas", "version": 1, **charge})
        assert r.status_code == 404, (route, r.text)
    # rien de tout cela n'a écrit
    assert not (d / "model.v2.glb").exists()
    # et une écriture valide dit d'où elle part — pour les trois, puis les
    # deux du lot B sur la version qu'elles viennent d'écrire
    v = 1
    for route, charge in corps.items():
        r = c.post(f"/api/etabli/{route}", json={"job": "job_portes", "version": v, **charge})
        assert r.status_code == 200, (route, r.text)
        assert r.json()["source"]["depuis"] == {"version": v, "fichier": "model.glb" if v == 1 else f"model.v{v}.glb"}
        v = r.json()["version"]
    r = c.post("/api/etabli/assise", json={"job": "job_portes", "version": v, "normale": [0, 1, 0]})
    assert r.status_code == 200 and r.json()["source"]["depuis"] == {"version": v, "fichier": f"model.v{v}.glb"}
    v = r.json()["version"]
    # le cube, posé par l'assise, va de y = 0 à y = 2 : le plan y = 1 le coupe
    r = c.post("/api/etabli/couper", json={"job": "job_portes", "version": v, "noeuds": [0],
                                           "point": [0, 1, 0], "normale": [0, 1, 0]})
    assert r.status_code == 200, r.text
    assert r.json()["source"]["depuis"] == {"version": v, "fichier": f"model.v{v}.glb"}
    assert r.json()["source"]["noeuds_avant"] == [0]


def _marche() -> bytes:
    """Une MARCHE : un socle 4×4×2 surmonté d'un bloc 2×2×2, UN maillage fermé
    de 16 sommets et 28 triangles, enroulé vers l'extérieur — le banc le
    vérifie (0 arête non appariée, volume 40) plutôt que de le supposer. Le
    dessus du socle est un ANNEAU à y = 2 : une face confondue qui n'est qu'une
    PARTIE de la frontière entre les deux côtés d'un plan y = 2 — le membre non
    convexe de la famille, que le cube ne mesurait pas (revue ; sa fixture est
    reconstruite ici, pas recopiée)."""
    from app.services import mesh_cut, mesh_edit
    S = [(0, 0, 0), (4, 0, 0), (4, 0, 4), (0, 0, 4)]      # dessous du socle
    T = [(0, 2, 0), (4, 2, 0), (4, 2, 4), (0, 2, 4)]      # bord extérieur de l'anneau
    B = [(1, 2, 1), (3, 2, 1), (3, 2, 3), (1, 2, 3)]      # pied du bloc = bord intérieur
    U = [(1, 4, 1), (3, 4, 1), (3, 4, 3), (1, 4, 3)]      # dessus du bloc
    pos = [tuple(float(c) for c in q) for q in S + T + B + U]
    s, t, b, u = range(0, 4), range(4, 8), range(8, 12), range(12, 16)
    tris = [(s[0], s[1], s[2]), (s[0], s[2], s[3])]                     # dessous, −y
    for k in range(4):
        k1 = (k + 1) % 4
        tris += [(s[k], t[k], t[k1]), (s[k], t[k1], s[k1])]            # flancs du socle
    for k in range(4):
        k1 = (k + 1) % 4
        tris += [(t[k], b[k], b[k1]), (t[k], b[k1], t[k1])]            # l'anneau, +y
    for k in range(4):
        k1 = (k + 1) % 4
        tris += [(b[k], u[k], u[k1]), (b[k], u[k1], b[k1])]            # flancs du bloc
    tris += [(u[0], u[3], u[2]), (u[0], u[2], u[1])]                    # dessus, +y
    assert len(pos) == 16 and len(tris) == 28
    doc = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}],
           "nodes": [{"name": "marche", "mesh": 0}], "meshes": [],
           "accessors": [], "bufferViews": []}
    tampon = bytearray()
    ipos = mesh_cut._ajouter_flottants(doc, tampon, pos, 3, True)
    iidx = mesh_cut._ajouter_indices(doc, tampon, tris)
    doc["meshes"].append({"name": "marche", "primitives": [
        {"attributes": {"POSITION": ipos}, "indices": iidx, "mode": 4}]})
    doc["buffers"] = [{"byteLength": len(tampon)}]
    return mesh_edit.ecrire_glb(doc, bytes(tampon))


def test_une_face_confondue_PARTIELLE_est_refusee_en_le_disant___la_MARCHE():
    """LE MEMBRE NON CONVEXE DE LA FAMILLE, mesuré par la revue et pas par moi :
    le plan y = 2 confondu avec l'anneau du socle, de la matière des deux
    côtés. Les triangles coplanaires étaient bien AFFECTÉS (l'anneau côté b),
    mais les segments de section ne naissent que des triangles FENDUS : la
    boucle était le carré 4×4 extérieur au lieu du pied du bloc, et les deux
    capuchons se posaient dessus — `marche_a` de volume nul à 8 arêtes non
    appariées, `marche_b` à 12, sous un compte rendu « posé » ; l'autre sens du
    plan tombait juste par chance d'orientation. La section juste demande
    l'adjacence (lot ultérieur) ; d'ici là le couteau REFUSE en le disant, dans
    les deux sens et à ±1e-9 — le seuil neuf y route. Le témoin d'abord : la
    fixture est fermée et pèse 40, et un plan qui ne touche aucune face la
    coupe en deux moitiés fermées de 6 et 34."""
    from app.services import mesh_cut, mesh_edit, print3d
    data = _marche()
    doc, binc = mesh_edit.lire_glb(data)
    assert _aretes_non_appariees(doc, binc, doc["meshes"][0]) == []
    tris = print3d.lire_glb_triangles(data)
    assert len(tris) == 28 and abs(_volume(tris) - 40.0) < 1e-9
    coupe, rapport = mesh_cut.couper(data, [0], [0, 2.5, 0], [0, 1, 0], "deux")
    docc, bincc = mesh_edit.lire_glb(coupe)
    for x in docc["nodes"]:
        assert _aretes_non_appariees(docc, bincc, docc["meshes"][x["mesh"]]) == [], x["name"]
    va = _volume(_triangles_du_noeud(coupe, "marche_a"))
    vb = _volume(_triangles_du_noeud(coupe, "marche_b"))
    assert abs(va - 6.0) < 1e-9 and abs(vb - 34.0) < 1e-9, (va, vb)
    # LE PLAN CONFONDU AVEC L'ANNEAU : refus NOMMÉ, dans les deux sens, à ±1e-9
    for normale in ([0, 1, 0], [0, -1, 0]):
        for y in (2.0, 2.0 + 1e-9, 2.0 - 1e-9):
            with pytest.raises(ValueError, match="confondu avec une face") as e:
                mesh_cut.couper(data, [0], [0, y, 0], normale)
            assert "marche" in str(e.value) and "8 triangle" in str(e.value)
            assert "adjacence" in str(e.value)
    # le cube convexe, lui, garde son refus d'avant : rien n'est traversé
    with pytest.raises(ValueError, match="ne traverse aucune"):
        mesh_cut.couper(_cube(), [0], [0, 1, 0], [0, 1, 0])
    # et le dessus du bloc, confondu avec un plan y = 4, est le cas convexe :
    # tout part d'un côté, même refus d'avant
    with pytest.raises(ValueError, match="ne traverse aucune"):
        mesh_cut.couper(data, [0], [0, 4, 0], [0, 1, 0])
