"""Recette Material Forge — gltf_builder (SPEC section 5) + env_service (6).

Tests purs : aucun réseau, aucune application FastAPI, aucun fichier de la
Library. Ils vérifient ce qu'un viewer vérifie avant d'afficher quoi que ce
soit — en-tête GLB, cohérence des longueurs de chunks, JSON parsable, comptes
de sommets/indices des 6 maillages, présence et intégrité des textures
embarquées, orthonormalité des tangentes, enroulement des faces — puis les 7
environnements équirectangulaires.

    runtime\\python\\python.exe -m pytest backend/tests/test_gltf_builder.py -v
"""
import io
import json
import math
import struct

import pytest
from PIL import Image

from app.services.gltf_builder import (DEFAULT_PROPS, MESHES, build_glb,
                                       build_mesh, mesh_stats,
                                       normalize_props)

GLB_MAGIC = 0x46546C67
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942

# Comptes attendus : figés ici, ce sont eux qui décrivent la géométrie livrée.
# (sommets, indices) — les triangles dégénérés des calottes de la sphère sont
# écartés à la génération, d'où 18720 et non 19200.
# Sphère : 80x40 depuis MESH_VERSION 2 (rangées serrées aux pôles pour atténuer
# le pincement du placage). 81*41 = 3321 sommets, 80*40*2 - 2*80 = 6240
# triangles.
EXPECTED = {
    "sphere":   (3321, 18720),
    "cube":     (24, 36),
    "torus":    (1225, 6912),
    "cylinder": (198, 576),
    "plane":    (4, 6),
    "tiled":    (16, 54),
}


# ── fabriques d'images de test ──────────────────────────────────────────────
def _png(img: Image.Image) -> bytes:
    b = io.BytesIO()
    img.save(b, "PNG")
    return b.getvalue()


def _checker(size=64, a=(210, 90, 40), b=(60, 60, 66), cells=8):
    img = Image.new("RGB", (size, size))
    px = img.load()
    step = size // cells
    for y in range(size):
        for x in range(size):
            px[x, y] = a if ((x // step) + (y // step)) % 2 else b
    return img


def _flat(size=64, color=(128, 128, 255)):
    return Image.new("RGB", (size, size), color)


def _maps():
    return {
        "basecolor": _png(_checker()),
        "normal": _png(_flat(color=(128, 128, 255))),
        "orm": _png(_checker(a=(255, 200, 20), b=(200, 120, 220))),
        "emissive": _png(_flat(color=(0, 0, 0))),
    }


# ── décodage GLB (ce que fait un viewer) ────────────────────────────────────
def _parse_glb(blob: bytes):
    """Retourne (json_dict, bin_bytes). Échoue si l'en-tête est incohérent."""
    assert len(blob) >= 20, "GLB tronqué"
    magic, version, total = struct.unpack_from("<III", blob, 0)
    assert magic == GLB_MAGIC, "magic != 'glTF'"
    assert version == 2, "version glTF != 2"
    assert total == len(blob), f"longueur déclarée {total} != réelle {len(blob)}"
    assert total % 4 == 0, "longueur totale non alignée sur 4"

    off = 12
    js = None
    bins = b""
    seen = []
    while off < total:
        clen, ctype = struct.unpack_from("<II", blob, off)
        off += 8
        assert clen % 4 == 0, "longueur de chunk non alignée sur 4"
        assert off + clen <= total, "chunk déborde du fichier"
        data = blob[off:off + clen]
        off += clen
        seen.append(ctype)
        if ctype == CHUNK_JSON:
            js = data
        elif ctype == CHUNK_BIN:
            bins = data
    assert off == total, "octets résiduels après le dernier chunk"
    assert seen and seen[0] == CHUNK_JSON, "le 1er chunk doit être JSON"
    return json.loads(js.decode("utf-8")), bins


def _view(g, bins, index):
    v = g["bufferViews"][index]
    o = v.get("byteOffset", 0)
    return bins[o:o + v["byteLength"]]


# ── en-tête et structure ────────────────────────────────────────────────────
def test_entete_glb_valide():
    g, bins = _parse_glb(build_glb(_maps(), {}, "sphere"))
    assert g["asset"]["version"] == "2.0"
    assert g["scene"] == 0 and g["scenes"][0]["nodes"] == [0]
    assert len(g["meshes"]) == 1 and len(g["materials"]) == 1
    # le tampon déclaré doit correspondre exactement au chunk BIN
    assert g["buffers"][0]["byteLength"] == len(bins)
    assert "uri" not in g["buffers"][0], "GLB non auto-suffisant (uri externe)"


def test_json_parsable_sans_texture():
    """Un GLB sans aucune map reste un fichier valide (cas dégradé)."""
    g, bins = _parse_glb(build_glb({}, {}, "cube"))
    assert "images" not in g and "textures" not in g
    assert g["buffers"][0]["byteLength"] == len(bins) > 0


def test_bufferviews_dans_le_tampon_et_alignes():
    g, bins = _parse_glb(build_glb(_maps(), {}, "torus"))
    for v in g["bufferViews"]:
        o = v.get("byteOffset", 0)
        assert o % 4 == 0, "bufferView non alignée sur 4"
        assert o + v["byteLength"] <= len(bins), "bufferView hors tampon"
    for a in g["accessors"]:
        assert a.get("byteOffset", 0) % 4 == 0


# ── maillages ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("mesh", MESHES)
def test_comptes_sommets_indices(mesh):
    nv, ni = EXPECTED[mesh]
    g = build_mesh(mesh)
    assert len(g["positions"]) == nv * 3
    assert len(g["normals"]) == nv * 3
    assert len(g["uvs"]) == nv * 2
    assert len(g["tangents"]) == nv * 4
    assert len(g["indices"]) == ni
    assert ni % 3 == 0
    assert max(g["indices"]) < nv, "index hors des sommets"
    assert mesh_stats(mesh) == {"mesh": mesh, "vertices": nv,
                                "triangles": ni // 3, "indices": ni}


@pytest.mark.parametrize("mesh", MESHES)
def test_accessors_refletent_le_maillage(mesh):
    nv, ni = EXPECTED[mesh]
    g, bins = _parse_glb(build_glb(_maps(), {}, mesh))
    prim = g["meshes"][0]["primitives"][0]
    at = prim["attributes"]
    assert set(at) == {"POSITION", "NORMAL", "TEXCOORD_0", "TANGENT"}
    assert g["accessors"][at["POSITION"]]["count"] == nv
    assert g["accessors"][at["TANGENT"]]["type"] == "VEC4"
    assert g["accessors"][prim["indices"]]["count"] == ni
    # POSITION doit porter min/max (exigence du format)
    pos = g["accessors"][at["POSITION"]]
    assert len(pos["min"]) == 3 and len(pos["max"]) == 3
    # et les octets doivent réellement être là
    raw = _view(g, bins, pos["bufferView"])
    assert len(raw) == nv * 12


@pytest.mark.parametrize("mesh", MESHES)
def test_normales_unitaires_et_uv_bornes(mesh):
    g = build_mesh(mesh)
    n = g["normals"]
    for i in range(0, len(n), 3):
        ln = math.sqrt(n[i] ** 2 + n[i + 1] ** 2 + n[i + 2] ** 2)
        assert abs(ln - 1.0) < 1e-6, "normale non unitaire"
    hi = 3.0 if mesh == "tiled" else 1.0
    for v in g["uvs"]:
        assert -1e-9 <= v <= hi + 1e-9, "UV hors plage"


@pytest.mark.parametrize("mesh", MESHES)
def test_tangentes_orthonormales_et_handedness(mesh):
    g = build_mesh(mesh)
    t, n = g["tangents"], g["normals"]
    for i in range(0, len(t), 4):
        k = (i // 4) * 3
        ln = math.sqrt(t[i] ** 2 + t[i + 1] ** 2 + t[i + 2] ** 2)
        assert abs(ln - 1.0) < 1e-5, "tangente non unitaire"
        dot = t[i] * n[k] + t[i + 1] * n[k + 1] + t[i + 2] * n[k + 2]
        assert abs(dot) < 1e-5, "tangente non orthogonale à la normale"
        assert t[i + 3] in (1.0, -1.0), "w de tangente invalide"


@pytest.mark.parametrize("mesh", ("sphere", "cube", "torus", "cylinder"))
def test_enroulement_ccw_vers_l_exterieur(mesh):
    """Une face à l'envers est invisible sous élimination des faces arrière :
    la normale géométrique de chaque triangle doit pointer du même côté que
    la normale interpolée de ses sommets."""
    g = build_mesh(mesh)
    p, n, idx = g["positions"], g["normals"], g["indices"]
    bad = 0
    for t in range(0, len(idx), 3):
        i0, i1, i2 = idx[t], idx[t + 1], idx[t + 2]
        a, b, c = i0 * 3, i1 * 3, i2 * 3
        e1 = [p[b + k] - p[a + k] for k in range(3)]
        e2 = [p[c + k] - p[a + k] for k in range(3)]
        cx = e1[1] * e2[2] - e1[2] * e2[1]
        cy = e1[2] * e2[0] - e1[0] * e2[2]
        cz = e1[0] * e2[1] - e1[1] * e2[0]
        vn = [(n[a + k] + n[b + k] + n[c + k]) / 3.0 for k in range(3)]
        if cx * vn[0] + cy * vn[1] + cz * vn[2] <= 0:
            bad += 1
    assert bad == 0, f"{bad} triangles enroulés à l'envers sur {len(idx)//3}"


def test_mesh_inconnu_retombe_sur_sphere():
    assert build_mesh("../../etc/passwd")["name"] == "sphere"
    assert build_mesh(None)["name"] == "sphere"
    assert build_mesh("SPHERE")["name"] == "sphere"


# ── textures embarquées ─────────────────────────────────────────────────────
def test_textures_presentes_et_relisibles():
    maps = _maps()
    g, bins = _parse_glb(build_glb(maps, {}, "sphere"))
    assert len(g["images"]) == 4, "4 maps fournies -> 4 images"
    assert len(g["textures"]) == 4 and len(g["samplers"]) == 1
    names = [im["name"] for im in g["images"]]
    assert names == ["basecolor", "normal", "orm", "emissive"]
    for im in g["images"]:
        assert im["mimeType"] == "image/png"
        raw = _view(g, bins, im["bufferView"])
        # octet pour octet ce qui a été fourni, et relisible par PIL
        assert raw == maps[im["name"]]
        assert Image.open(io.BytesIO(raw)).size == (64, 64)


def test_slots_de_materiau_branches():
    g, _ = _parse_glb(build_glb(_maps(), {}, "sphere"))
    m = g["materials"][0]
    pbr = m["pbrMetallicRoughness"]
    assert "baseColorTexture" in pbr
    # l'ORM packée sert à la fois de metallicRoughness et d'occlusion
    orm = pbr["metallicRoughnessTexture"]["index"]
    assert m["occlusionTexture"]["index"] == orm
    assert "normalTexture" in m and "emissiveTexture" in m


def test_secours_sans_orm():
    """Sans ORM packée, l'AO garde son emplacement — mais une roughness seule
    NE PEUT PAS servir de metallicRoughness.

    Le canal B d'une roughness grise vaut la rugosité : un moteur y lirait de
    la métallicité, et une matière très rugueuse sortirait métallique. glTF ne
    sait lire rugosité et métal que dans une paire packée ; en son absence, on
    n'attache aucune texture et les facteurs reprennent leur rôle normal."""
    maps = {"basecolor": _png(_checker()),
            "roughness": _png(_flat(color=(90, 90, 90))),
            "ao": _png(_flat(color=(240, 240, 240)))}
    g, _ = _parse_glb(build_glb(maps, {"metallic": 0.0, "roughness": 0.6},
                                "plane"))
    m = g["materials"][0]
    pbr = m["pbrMetallicRoughness"]
    assert "metallicRoughnessTexture" not in pbr
    assert pbr["metallicFactor"] == 0.0 and pbr["roughnessFactor"] == 0.6
    assert m["occlusionTexture"]["index"] is not None
    # la roughness non référençable n'est pas embarquée pour rien
    assert [i["name"] for i in g["images"]] == ["basecolor", "ao"]


def test_maps_invalides_ignorees_sans_erreur():
    g, _ = _parse_glb(build_glb(
        {"basecolor": _png(_checker()), "normal": b"", "orm": None,
         "emissive": "pas des octets"}, {}, "cube"))
    assert len(g["images"]) == 1


# ── matériau, extensions, robustesse ────────────────────────────────────────
def test_extensions_pbr_emises():
    props = {"clearcoat": 0.7, "clearcoat_roughness": 0.2, "sheen": 0.5,
             "sheen_color": "#ff8800", "transmission": 0.9, "ior": 1.7,
             "tiling": 3.0, "rotation": 45.0}
    g, _ = _parse_glb(build_glb(_maps(), props, "sphere"))
    ext = g["materials"][0]["extensions"]
    assert set(ext) == {"KHR_materials_clearcoat", "KHR_materials_sheen",
                        "KHR_materials_transmission", "KHR_materials_ior"}
    assert ext["KHR_materials_ior"]["ior"] == pytest.approx(1.7)
    assert ext["KHR_materials_transmission"]["transmissionFactor"] == \
        pytest.approx(0.9)
    used = g["extensionsUsed"]
    for e in ext:
        assert e in used
    assert "KHR_texture_transform" in used
    tr = g["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"][
        "extensions"]["KHR_texture_transform"]
    assert tr["scale"] == [3.0, 3.0]
    assert tr["rotation"] == pytest.approx(math.radians(45.0), abs=1e-5)


def test_pas_d_extension_inutile_par_defaut():
    g, _ = _parse_glb(build_glb(_maps(), {}, "sphere"))
    assert "extensions" not in g["materials"][0]
    assert "extensionsUsed" not in g


def test_couleurs_converties_en_lineaire():
    g, _ = _parse_glb(build_glb(_maps(), {"color": "#808080"}, "cube"))
    r = g["materials"][0]["pbrMetallicRoughness"]["baseColorFactor"][0]
    # 0.5 sRGB -> ~0.2158 linéaire (et surtout : pas 0.5)
    assert 0.20 < r < 0.23


def test_opacite_bascule_en_blend():
    g, _ = _parse_glb(build_glb(_maps(), {"opacity": 0.4}, "sphere"))
    assert g["materials"][0]["alphaMode"] == "BLEND"
    # ...sauf sous transmission, où l'extension gère la transparence
    g2, _ = _parse_glb(build_glb(_maps(),
                                 {"opacity": 0.4, "transmission": 0.8},
                                 "sphere"))
    assert "alphaMode" not in g2["materials"][0]


def test_props_aberrantes_remplacees_par_les_defauts():
    p = normalize_props({"metallic": "abcd", "roughness": 42, "ior": None,
                         "color": "pas une couleur", "tiling": float("nan"),
                         "opacity": -5})
    assert p["metallic"] == DEFAULT_PROPS["metallic"]
    assert p["roughness"] == 1.0          # borné, pas rejeté
    assert p["ior"] == DEFAULT_PROPS["ior"]
    assert p["color"] == "#ffffff"
    assert p["tiling"] == DEFAULT_PROPS["tiling"]
    assert p["opacity"] == 0.0
    assert normalize_props(None) == DEFAULT_PROPS
    assert normalize_props("bonjour") == DEFAULT_PROPS


def test_determinisme():
    a = build_glb(_maps(), {"metallic": 0.3}, "torus")
    b = build_glb(_maps(), {"metallic": 0.3}, "torus")
    assert a == b, "deux constructions identiques doivent être bit à bit égales"


@pytest.mark.parametrize("mesh", MESHES)
def test_tous_les_maillages_produisent_un_glb_valide(mesh):
    maps = _maps()
    g, bins = _parse_glb(build_glb(maps, {"tiling": 2.0}, mesh))
    assert g["nodes"][0]["name"] == mesh
    # le tampon porte au minimum les 4 PNG + la géométrie
    assert len(bins) >= sum(len(v) for v in maps.values())
    for raw in maps.values():
        assert raw in bins


# ── environnements (SPEC section 6) ─────────────────────────────────────────
def test_sept_environnements():
    from app.services import env_service as E
    assert len(E.ENVS) == 7
    assert E.env_names() == ["unlit", "daylight", "studio", "sunset",
                             "overcast", "night", "dramatic"]
    for e in E.env_list():
        assert set(e) == {"name", "label"} and e["label"].strip()


@pytest.mark.parametrize("name", ["unlit", "daylight", "studio", "sunset",
                                  "overcast", "night", "dramatic"])
def test_environnement_equirectangulaire_non_vide(name):
    from app.services import env_service as E
    from PIL import ImageStat
    img = E.build_env(name)
    assert img.size == (E.ENV_W, E.ENV_H) == (1024, 512)
    assert img.mode == "RGB"
    st = ImageStat.Stat(img)
    # ni une image noire, ni un aplat : il faut du ciel, du sol et une source
    assert sum(st.mean) / 3 > 8, "environnement quasi noir"
    assert max(st.stddev) > 4, "environnement uniforme (pas de dégradé)"


def test_environnement_raccord_horizontal():
    """Un équirect dont les colonnes extrêmes diffèrent montre une couture
    verticale dans tous les reflets."""
    from app.services import env_service as E
    img = E.build_env("sunset")
    left = img.crop((0, 0, 1, E.ENV_H)).tobytes()
    right = img.crop((E.ENV_W - 1, 0, E.ENV_W, E.ENV_H)).tobytes()
    worst = max(abs(a - b) for a, b in zip(left, right))
    assert worst <= 6, f"couture equirect : écart max {worst}"


def test_environnement_cache_disque_et_jpeg():
    from app.services import env_service as E
    p = E.env_path("night")
    assert p.is_file() and p.suffix == ".jpg"
    first = p.stat().st_mtime_ns
    p2 = E.env_path("night")
    assert p2 == p and p2.stat().st_mtime_ns == first, "cache non réutilisé"
    raw = E.env_bytes("night")
    assert raw[:2] == b"\xff\xd8", "JPEG attendu"
    assert Image.open(io.BytesIO(raw)).size == (1024, 512)


def test_environnement_inconnu_liste_blanche():
    from app.services import env_service as E
    assert E.env_path("../../../secret").name.startswith("studio-")
    assert E.build_env("nimporte quoi").size == (1024, 512)


def test_passerelle_paresseuse_depuis_gltf_builder():
    """La SPEC autorise les envs dans gltf_builder : l'alias doit marcher."""
    from app.services import gltf_builder as G
    assert [e["name"] for e in G.env_list()][0] == "unlit"
    with pytest.raises(AttributeError):
        G.nexiste_pas
