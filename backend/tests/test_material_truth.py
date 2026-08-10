# -*- coding: utf-8 -*-
"""Recette « ce qu'on montre est ce qu'on livre » — Material Forge.

Ce fichier verrouille les QUATRE defauts de fond releves par la critique sur
les maps et l'export. Chaque test correspond a un reproche precis et mesure ce
que le code produit vraiment, jamais ce qu'il promet.

1. LE METAL EXPORTE ETAIT DU PLASTIQUE. L'inspecteur affichait « Metallique
   1.00 » alors que la carte metallic mesurait 1.17/255 et le canal B de l'ORM
   autant : glTF pose `metalness = metallicFactor x texture.B`, donc
   1.0 x 0.0046 = 0.005. Verifie ici : la map PORTE le niveau regle (moyenne =
   valeur, a 2/255 pres), le GLB met son facteur a 1.0, et le produit des deux
   — dans l'apercu comme dans l'export — vaut exactement le reglage.

2. DEUX MAPS SUR HUIT ETAIENT VIDES. L'AO derivee mesurait 251/255 de moyenne
   (occlusion nulle) pendant que le bandeau revendiquait « 8 MAPS PBR ».
   Verifie ici : l'AO porte une vraie occlusion de cavite, le rayon et la force
   ont l'effet annonce, et `map_report` compte les maps porteuses au lieu de
   toutes les compter.

3. LE MASKMAP UNITY ETAIT FAUX. Le fichier `_MaskMap.png` contenait l'ORM
   (R=AO V=rugosite B=metal) au lieu de la convention Unity (R=metal
   V=occlusion B=detail A=smoothness) : canaux intervertis, matiere fausse.
   Verifie ici canal par canal, plus le fait qu'Unity ne recoit plus les maps
   que le MaskMap rend redondantes.

4. LE SCORE DE RACCORD NE POUVAIT PAS ECHOUER. `seam_score` compare la colonne
   0 a la colonne w-1 et `make_seamless` les rend identiques : l'« apres »
   valait 0.00 pour les quinze matieres du disque. Verifie ici que le rapport
   de couture, lui, distingue une tuile corrigee d'une tuile brute, et que les
   paliers sont ceux mesures en aveugle (invisible <= 1.0, discret <= 2.0).

    runtime\\python\\python.exe -m pytest backend/tests/test_material_truth.py -v
"""
import io
import json
import math
import random
import zipfile

from PIL import Image, ImageDraw, ImageFilter

import app.services.gltf_builder as GB
import app.services.material_store as MS
import app.services.pbr_service as PBR
from app.services.pixel_ops import (make_seamless, normalize_seamless_opts,
                                    seam_score)


# ── images de recette ────────────────────────────────────────────────────────

def _blobs(w=256, seed=11):
    """Texture aleatoire mais deterministe, avec des creux francs : de quoi
    donner une occlusion mesurable et un motif non trivial."""
    rng = random.Random(seed)
    img = Image.new("RGB", (w, w), (40, 44, 52))
    d = ImageDraw.Draw(img)
    for _ in range(160):
        x, y = rng.randrange(w), rng.randrange(w)
        r = rng.randrange(4, 22)
        d.ellipse([x - r, y - r, x + r, y + r],
                  fill=(rng.randrange(60, 210), rng.randrange(50, 180),
                        rng.randrange(40, 150)))
    return img.filter(ImageFilter.GaussianBlur(2))


def _tile(w=256, seed=11):
    return make_seamless(_blobs(w, seed),
                         normalize_seamless_opts({"blend": 25})).convert("RGB")


def _mean(img):
    return PBR.stats(img)["mean"]


def _glb_doc(data):
    import struct
    ln, _ = struct.unpack("<II", data[12:20])
    return json.loads(data[20:20 + ln].decode("utf-8").rstrip(" \x00"))


# ═══════════ 1. le metal exporte est du metal ═══════════════════════════════

def test_metallic_map_carries_the_level_that_is_displayed():
    """moyenne(metallic) == reglage, a 2/255 pres, sur toute la plage."""
    maps = PBR.derive_maps(_tile(), None, ["metallic", "roughness", "orm"])
    # prealable, et c'est LE defaut : le motif brut est quasi noir (mesure sur
    # les matieres du disque, moyenne 1.17/255 pour « or martele »). Sous 6 %
    # de 255, aucun moteur n'y verra du metal.
    assert _mean(maps["metallic"]) < 0.06 * 255, _mean(maps["metallic"])
    for level in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0):
        baked = PBR.bake_levels(maps, {"metallic": level, "roughness": 1 - level})
        got_m = _mean(baked["metallic"]) / 255.0
        got_r = _mean(baked["roughness"]) / 255.0
        assert abs(got_m - level) <= 2 / 255.0, (level, got_m)
        assert abs(got_r - (1 - level)) <= 2 / 255.0, (level, got_r)
        # ORM : B = metal, V = rugosite, memes valeurs que les maps separees
        r, g, b = baked["orm"].convert("RGB").split()
        assert abs(_mean(b) / 255.0 - level) <= 2 / 255.0, (level, _mean(b))
        assert abs(_mean(g) / 255.0 - (1 - level)) <= 2 / 255.0


def test_glb_factor_times_texture_equals_the_setting():
    """Le produit facteur x texture — la formule glTF — vaut le reglage.

    C'est LE test du defaut n.1 : avant, 1.0 x 0.0046 = 0.005 pour un
    « Metallique 1.00 » affiche."""
    maps = PBR.derive_maps(_tile())
    for metallic, roughness in ((1.0, 0.28), (0.0, 0.95), (0.5, 0.5)):
        props = {"metallic": metallic, "roughness": roughness}
        baked = PBR.bake_levels(maps, props)
        payload = {k: MS.png_bytes(v, k, 8) for k, v in baked.items()}
        doc = _glb_doc(GB.build_glb(payload, props, "sphere"))
        pbr = doc["materials"][0]["pbrMetallicRoughness"]
        assert "metallicRoughnessTexture" in pbr
        r, g, b = baked["orm"].convert("RGB").split()
        eff_m = pbr["metallicFactor"] * _mean(b) / 255.0
        eff_r = pbr["roughnessFactor"] * _mean(g) / 255.0
        assert abs(eff_m - metallic) <= 0.01, (metallic, eff_m)
        assert abs(eff_r - roughness) <= 0.01, (roughness, eff_r)


def test_preview_and_export_share_one_formula():
    """Apercu et export sont le MEME GLB a la resolution pres : aucune des deux
    voies ne peut mentir sans l'autre."""
    maps = PBR.derive_maps(_tile(), None, list(MS.MAP_KINDS))
    props = {"metallic": 1.0, "roughness": 0.3}
    payload = {k: MS.png_bytes(v, k, 8)
               for k, v in PBR.bake_levels(maps, props).items()}
    preview = _glb_doc(GB.build_glb(payload, props, "sphere",
                                    uv_repeat=GB.MESH_UV["sphere"]))
    export = _glb_doc(GB.build_glb(payload, props, "sphere"))
    a = preview["materials"][0]["pbrMetallicRoughness"]
    b = export["materials"][0]["pbrMetallicRoughness"]
    assert a["metallicFactor"] == b["metallicFactor"] == 1.0
    assert a["roughnessFactor"] == b["roughnessFactor"] == 1.0
    assert a["baseColorFactor"] == b["baseColorFactor"]


def test_glb_carries_no_texture_the_material_never_reads():
    """L'ORM sert deja de metallicRoughness ET d'occlusion : embarquer en plus
    roughness/metallic/ao separees, c'etait du poids mort (1.9 Mo mesures sur
    un export 1024)."""
    maps = PBR.derive_maps(_tile())
    payload = {k: MS.png_bytes(v, k, 8) for k, v in maps.items()}
    doc = _glb_doc(GB.build_glb(payload, {}, "sphere"))
    names = [i["name"] for i in doc.get("images", [])]
    assert names == ["basecolor", "normal", "orm", "emissive"], names
    used = set()
    mat = doc["materials"][0]
    for ref in (mat["pbrMetallicRoughness"].get("baseColorTexture"),
                mat["pbrMetallicRoughness"].get("metallicRoughnessTexture"),
                mat.get("normalTexture"), mat.get("occlusionTexture"),
                mat.get("emissiveTexture")):
        if ref:
            used.add(ref["index"])
    assert used == set(range(len(doc["textures"]))), "texture non referencee"


def test_a_roughness_alone_never_becomes_metal():
    """Sans ORM, une roughness grise ne peut pas servir de metallicRoughness :
    son canal B vaut la rugosite, un moteur y lirait du metal."""
    maps = PBR.derive_maps(_tile(), None, ["basecolor", "roughness"])
    payload = {k: MS.png_bytes(v, k, 8) for k, v in maps.items()}
    doc = _glb_doc(GB.build_glb(payload, {"metallic": 0.0, "roughness": 0.7},
                                "sphere"))
    pbr = doc["materials"][0]["pbrMetallicRoughness"]
    assert "metallicRoughnessTexture" not in pbr
    assert pbr["roughnessFactor"] == 0.7      # le facteur reprend son role
    assert pbr["metallicFactor"] == 0.0


def test_level_stats_predicts_the_baked_map_exactly():
    """Bouger un curseur doit mettre a jour ce que l'ecran annonce sans relire
    16 M pixels : la prevision analytique doit coller a la mesure."""
    maps = PBR.derive_maps(_tile(), None, ["roughness"])
    pattern = PBR.stats(maps["roughness"])
    for level in (0.0, 0.2, 0.5, 0.8, 1.0):
        got = PBR.stats(PBR.bake_levels(maps, {"roughness": level})["roughness"])
        pred = PBR.level_stats(pattern, level)
        assert abs(pred["mean"] - got["mean"]) <= 2, (level, pred, got)
        assert abs(pred["min"] - got["min"]) <= 2, (level, pred, got)
        assert abs(pred["max"] - got["max"]) <= 2, (level, pred, got)


# ═══════════ 2. aucune map vide comptee comme pleine ════════════════════════

def test_ao_carries_real_cavity_occlusion():
    """Avant : moyenne 251/255, centile 1 % a 225 — du blanc. Apres : une
    occlusion qu'on voit."""
    maps = PBR.derive_maps(_blobs(), None, ["ao"])
    st = PBR.stats(maps["ao"])
    assert st["mean"] < 248, st            # ce n'est plus du blanc
    assert st["p1"] < 190, st              # les creux descendent vraiment
    assert st["max"] >= 250, st            # les plats restent non occlus


def test_ao_radius_and_strength_do_what_they_say():
    """Deux reglages annonces a l'ecran : ils doivent avoir un effet monotone,
    et la force a 0 doit rendre un blanc parfait (aucune occlusion)."""
    src = _blobs()
    means = {}
    for r in (2.0, 4.0, 8.0, 16.0):
        d = dict(PBR.DERIVE_DEFAULTS, ao_radius=r)
        means[r] = _mean(PBR.derive_maps(src, d, ["ao"])["ao"])
    ordered = [means[r] for r in (2.0, 4.0, 8.0, 16.0)]
    assert ordered == sorted(ordered, reverse=True), means
    assert ordered[0] - ordered[-1] > 8, means      # l'effet est VISIBLE

    by_k = {}
    for k in (0.0, 0.5, 1.0, 2.0):
        d = dict(PBR.DERIVE_DEFAULTS, ao_strength=k)
        by_k[k] = _mean(PBR.derive_maps(src, d, ["ao"])["ao"])
    assert by_k[0.0] == 255.0, by_k          # force nulle = blanc pur
    assert by_k[2.0] < by_k[1.0] < by_k[0.5] < by_k[0.0], by_k


def test_map_report_counts_only_the_maps_that_carry_something():
    """Une emissive eteinte et une metallic uniforme ne sont pas comptees comme
    des maps pleines — et le rapport DIT pourquoi."""
    maps = PBR.bake_levels(PBR.derive_maps(_tile()),
                           {"metallic": 0.0, "roughness": 0.6})
    rep = PBR.map_report(maps)
    assert rep["total"] == 8
    assert rep["informative"] < 8
    assert rep["maps"]["metallic"]["informative"] is False
    assert "diélectrique" in rep["maps"]["metallic"]["note"]
    assert rep["maps"]["emissive"]["informative"] is False
    assert "émet" in rep["maps"]["emissive"]["note"]
    for kind in ("basecolor", "normal", "roughness", "ao", "height"):
        assert rep["maps"][kind]["informative"] is True, kind


def test_a_metallic_material_declares_its_metallic_map_uniform():
    """Metallique 1.00 : la map est blanche partout. C'est juste, et ca doit
    etre dit — pas compte comme une huitieme map texturee."""
    maps = PBR.bake_levels(PBR.derive_maps(_tile()),
                           {"metallic": 1.0, "roughness": 0.3})
    rep = PBR.map_report(maps)
    assert rep["maps"]["metallic"]["mean"] == 255.0
    assert rep["maps"]["metallic"]["informative"] is False
    assert "1.00" in rep["maps"]["metallic"]["note"]
    assert "uniforme" in rep["maps"]["metallic"]["note"]


# ═══════════ 3. le MaskMap Unity est un vrai MaskMap ════════════════════════

def test_unity_maskmap_uses_the_unity_convention():
    """R=metal, V=occlusion, B=detail(0), A=smoothness=1-rugosite. L'ORM
    (R=AO V=rugosite B=metal) n'a rien a faire sous ce nom."""
    maps = PBR.bake_levels(PBR.derive_maps(_tile()),
                           {"metallic": 1.0, "roughness": 0.25})
    mask = MS.build_maskmap(maps)
    assert mask.mode == "RGBA"
    r, g, b, a = mask.split()
    assert abs(_mean(r) - _mean(maps["metallic"])) < 0.5      # R = metal
    assert abs(_mean(g) - _mean(maps["ao"])) < 0.5            # V = occlusion
    assert _mean(b) == 0.0                                    # B = detail, nul
    # A = smoothness = 1 - rugosite
    assert abs(_mean(a) - (255.0 - _mean(maps["roughness"]))) < 0.5
    # et surtout : ce n'est PAS l'ORM
    o_r, o_g, o_b = maps["orm"].convert("RGB").split()
    assert abs(_mean(r) - _mean(o_r)) > 1.0, "R du MaskMap = R de l'ORM (AO)"


def test_unity_export_drops_what_the_maskmap_replaces():
    """Unity ne branche que BaseMap / Normal / la texture packee (+ Height,
    Emission) : livrer en plus Roughness, Metallic et Occlusion, c'etait le
    meme contenu deux fois. Vaut pour les DEUX pipelines."""
    for naming in MS.UNITY_NAMINGS + ("unity",):
        sel = MS.default_export_maps(naming)
        assert MS.MASKMAP in sel, naming
        for kind in ("roughness", "metallic", "ao", "orm"):
            assert kind not in sel, (naming, kind)
    assert MS.default_export_maps("unreal").count("orm") == 1
    for kind in ("roughness", "metallic", "ao"):
        assert kind not in MS.default_export_maps("unreal")
    assert set(MS.default_export_maps("standard")) == set(MS.MAP_KINDS)
    # le role affiche doit dire la verite, pas « B = metal » sous Unity
    role = MS.map_role(MS.MASKMAP, "unity_hdrp").lower()
    assert "r=métal" in role and "smoothness" in role
    assert "smoothness" in MS.map_role("roughness", "unity_urp").lower()


def test_unity_zip_contains_a_real_maskmap_file():
    maps = PBR.bake_levels(PBR.derive_maps(_tile()),
                           {"metallic": 1.0, "roughness": 0.25})
    mat = {"id": "mat_00000000", "name": "or martelé", "props":
           {"metallic": 1.0, "roughness": 0.25},
           "seam": {"before": 3.4, "after": 0.0, "ratio": 0.95,
                    "grade": "invisible"}}
    sel = {k: v for k, v in maps.items()
           if k in MS.default_export_maps("unity_hdrp")}
    sel[MS.MASKMAP] = MS.build_maskmap(maps)
    blob = MS.export_zip(mat, sel, "unity_hdrp", 8, None)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names = z.namelist()
        assert "or_martele_MaskMap.png" in names
        for gone in ("or_martele_Roughness.png", "or_martele_Metallic.png",
                     "or_martele_Occlusion.png", "or_martele_orm.png"):
            assert gone not in names, gone
        img = Image.open(io.BytesIO(z.read("or_martele_MaskMap.png")))
        assert img.mode == "RGBA"
        readme = z.read("LISEZMOI.txt").decode("utf-8")
    assert "R=métal" in readme and "smoothness" in readme
    assert "0.95" in readme and "invisible" in readme
    # sous URP le MEME contenu part sous le nom de ses emplacements reels
    blob = MS.export_zip(mat, sel, "unity_urp", 8, None)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert "or_martele_MetallicOcclusion.png" in z.namelist()


# ═══════════ 4. le score de raccord ne se donne plus 0 tout seul ════════════

def test_the_old_edge_score_is_zero_by_construction():
    """Constat du defaut : la correction rend la colonne 0 identique a la
    colonne w-1, donc la mesure historique vaut 0.00 quoi qu'il arrive. Ce
    n'est pas une reussite, c'est une tautologie."""
    for seed in (3, 11, 29):
        assert seam_score(_tile(seed=seed)) == 0.0


def test_seam_ratio_separates_a_corrected_tile_from_a_raw_one():
    """Le rapport, lui, distingue : la tuile brute depasse le seuil de
    visibilite mesure (2.0), la corrigee reste sous 1.4."""
    for seed in (3, 11, 29):
        raw = PBR.seam_report(_blobs(seed=seed))["ratio"]
        fixed = PBR.seam_report(_tile(seed=seed))["ratio"]
        assert raw > 2.0, (seed, raw)
        assert fixed < 1.4, (seed, fixed)
        assert fixed < raw / 2.0, (seed, raw, fixed)


def test_seam_grades_match_the_blind_measurement():
    """Paliers issus du test a deux alternatives en aveugle sur neuf tuiles
    reelles : 0 detection sur 3 a 0.96/0.98/1.36, 6 sur 6 de 1.27 a 6.23,
    donc detection certaine des 2.0."""
    assert PBR.seam_grade(0.0) == "invisible"
    assert PBR.seam_grade(1.0) == "invisible"
    assert PBR.seam_grade(1.01) == "discret"
    assert PBR.seam_grade(2.0) == "discret"
    assert PBR.seam_grade(2.01) == "visible"
    assert PBR.seam_grade(4.0) == "visible"
    assert PBR.seam_grade(4.01) == "cassé"


def test_seam_report_is_multi_scale_and_bounded():
    rep = PBR.seam_report(_tile())
    assert [s["px"] for s in rep["scales"]] == list(PBR.SEAM_SCALES)
    assert rep["ratio"] == max(s["ratio"] for s in rep["scales"])
    assert rep["grade"] == PBR.seam_grade(rep["ratio"])


def test_a_pure_gradient_tile_is_caught_as_broken():
    """Cas d'ecole : une rampe horizontale ne se referme pas. La mesure de bord
    la voit aussi, mais le rapport dit surtout DE COMBIEN elle depasse."""
    w = 256
    ramp = Image.merge("RGB", tuple(
        Image.frombytes("L", (w, 1), bytes(x for x in range(w)))
             .resize((w, w), Image.NEAREST) for _ in range(3)))
    rep = PBR.seam_report(ramp)
    assert rep["ratio"] > 4.0, rep
    assert rep["grade"] == "cassé"


# ═══════════ le contrat de stockage suit ════════════════════════════════════

def test_material_object_keeps_the_new_evidence():
    """`seam.ratio` / `seam.grade` et `map_stats` doivent survivre a la
    normalisation, sinon l'ecran retombe sur le score d'avant correction."""
    raw = {
        "id": "mat_12345678", "name": "test",
        "seam": {"before": 9.6, "after": 0.0, "ratio": 1.19,
                 "grade": "discret"},
        "maps": list(MS.MAP_KINDS),
        "map_stats": {"metallic": {"mean": 0.0, "informative": False,
                                   "note": "uniforme"},
                      "ao": {"mean": 236.0, "informative": True, "note": ""}},
    }
    mat = MS.normalize_material(raw, "mat_12345678")
    assert mat["seam"]["ratio"] == 1.19
    assert mat["seam"]["grade"] == "discret"
    assert mat["map_stats"]["metallic"]["informative"] is False
    assert mat["maps_informative"] == 1
    # une matiere sans preuve ne raconte rien plutot que d'inventer
    empty = MS.normalize_material({"id": "mat_87654321"}, "mat_87654321")
    assert empty["seam"]["ratio"] is None and empty["seam"]["grade"] is None
    assert empty["map_stats"] == {} and empty["maps_informative"] == 0


def test_natural_levels_are_what_the_maps_measure():
    """A la creation, le curseur affiche ce que la texture vaut : cuire ce
    niveau-la ne doit modifier aucun pixel."""
    maps = PBR.derive_maps(_tile(), None, ["metallic", "roughness", "orm"])
    nat = MS.natural_levels(maps)
    assert abs(nat["roughness"] * 255 - _mean(maps["roughness"])) < 1.0
    baked = PBR.bake_levels(maps, nat)
    for kind in ("metallic", "roughness"):
        before, after = PBR.stats(maps[kind]), PBR.stats(baked[kind])
        assert abs(before["mean"] - after["mean"]) < 1.0, kind
        # le niveau naturel est arrondi a 3 decimales pour etre affichable :
        # la reconstruction est donc exacte a un niveau 8 bits pres.
        assert abs(before["max"] - after["max"]) <= 3, kind
        assert abs(before["min"] - after["min"]) <= 3, kind


def test_bake_never_raises_on_junk_props():
    maps = PBR.derive_maps(_tile(), None, ["metallic", "roughness", "orm"])
    for junk in (None, {}, {"metallic": "beaucoup"}, {"roughness": None},
                 {"metallic": float("nan")}, {"metallic": 42},
                 {"roughness": -3}, [1, 2, 3]):
        out = PBR.bake_levels(maps, junk)
        assert set(out) == set(maps)
        for img in out.values():
            assert img.size == maps["metallic"].size


if __name__ == "__main__":       # execution directe (harnais run-tests.ps1)
    import sys
    fails = 0
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS {name}")
            except AssertionError as e:
                fails += 1
                print(f"  FAIL {name}: {e}")
    print("échecs :", fails)
    sys.exit(1 if fails else 0)
