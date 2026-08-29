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
