# -*- coding: utf-8 -*-
"""LA RÈGLE DU « ≈ » — énoncée, appliquée sans exception, verrouillée ici.

Reproche exact de la critique : « Le ≈ est une légende qui contredit son
application : la seule justification visible est "Poids estimés — la profondeur
16 bits change la compression", or ≈ est apposé sur trois fichiers 8 bits
(Roughness L 8, orm RGB 8, MetallicOcclusion RGBA 8) pendant qu'Occlusion —
aussi L 8 — est donné comme exact. Aucune règle énoncée ne les sépare. »

La règle est celle-ci, et elle ne regarde NI les canaux NI la profondeur :

    =  le fichier qui part existe déjà, encodé, sur le disque : on lit sa taille
    ≈  l'export doit FABRIQUER un fichier qui n'existe pas encore

Quatre fabrications : niveau cuit dans la map (metallic, roughness, orm — les
seules que `pbr_service.bake_levels` transforme), fichier empilé à la volée
(MaskMap Unity), rééchantillonnage, profondeur 16 bits ou base64 glTF.

Ce que ce fichier vérifie :
  · `exact` équivaut EXACTEMENT à « aucune fabrication » (`weigh_tag` vide) ;
  · deux lignes de mêmes canaux et même profondeur ne peuvent pas différer sur
    `exact` sans différer sur la raison — c'était tout le reproche ;
  · un poids annoncé « mesuré » est la taille RÉELLE du fichier sur le disque ;
  · chaque bascule (bake, MaskMap, rééchantillonnage, 16 bits, base64) est bien
    celle qui produit le « ≈ », et elle est NOMMÉE ;
  · la règle elle-même est publiée avec le bordereau (`weigh_rule`).

    runtime\\python\\python.exe -m pytest backend/tests/test_export_weigh.py -v
"""
import json
import os
import pathlib
import tempfile

import pytest
from PIL import Image

import app.services.material_store as MS

_TMP = pathlib.Path(tempfile.mkdtemp())


@pytest.fixture(scope="module")
def mat(monkeypatch_module=None):
    """Une matière sur disque : huit PNG réels + un meta.json crédible.
    Le métal et l'émissive sont uniformes (matière diélectrique non émissive),
    exactement le cas que la critique lisait à l'écran."""
    root = _TMP / "materials"
    root.mkdir(parents=True, exist_ok=True)
    MS.materials_root = lambda: root                       # noqa: E731
    mid = "mat_deadbe01"
    d = root / mid
    d.mkdir(parents=True, exist_ok=True)

    def motif(mode, size=128, seed=3):
        im = Image.new(mode, (size, size))
        px = im.load()
        for y in range(size):
            for x in range(size):
                v = (x * 7 + y * 13 + seed * 29) % 256
                px[x, y] = v if mode == "L" else (v, (v * 3) % 256, (v * 5) % 256)
        return im

    for k in MS.MAP_KINDS:
        mode = MS.MAP_MODES.get(k, "L")
        if k == "metallic":
            im = Image.new("L", (128, 128), 0)             # diélectrique
        elif k == "emissive":
            im = Image.new("RGB", (128, 128), (0, 0, 0))   # n'émet pas
        else:
            im = motif(mode, seed=MS.MAP_KINDS.index(k))
        im.save(d / f"{k}.png")

    meta = {
        "id": mid, "name": "recette poids", "prompt": "recette poids",
        "res": 128, "maps": list(MS.MAP_KINDS),
        "props": {"metallic": 0.0, "roughness": 1.0},
        "map_stats": {k: {"informative": k not in ("metallic", "emissive"),
                          "mean": 0.0 if k in ("metallic", "emissive") else 128.0,
                          "note": ""} for k in MS.MAP_KINDS},
        "maps_informative": len(MS.MAP_KINDS) - 2,
        "created": "2026-08-08T00:00:00Z",
    }
    (d / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return meta


def _by_kind(d):
    return {e["kind"]: e for e in d["entries"]}


# ═══════════════ la règle est une équivalence, pas une habitude ═════════════
CAS = [
    dict(fmt="zip", naming="standard", res=0, bits=8),
    dict(fmt="zip", naming="standard", res=0, bits=16),
    dict(fmt="zip", naming="standard", res=512, bits=8),
    dict(fmt="zip", naming="unity_urp", res=0, bits=8),
    dict(fmt="zip", naming="unreal", res=64, bits=16),
    dict(fmt="glb", naming="standard", res=0, bits=8),
    dict(fmt="gltf", naming="standard", res=0, bits=8),
]


@pytest.mark.parametrize("cas", CAS)
def test_exact_equivaut_a_aucune_fabrication(mat, cas):
    """`exact` n'est jamais vrai sans raison ni faux sans raison NOMMÉE."""
    d = MS.export_manifest(mat, **cas)
    for e in d["entries"] + d["extras"]:
        tag = e.get("weigh_tag", "")
        assert bool(e["exact"]) == (not tag), (
            f"{cas} · {e['name']} : exact={e['exact']} mais raison={tag!r}")
        assert e.get("weigh"), f"{e['name']} : aucun poids justifié"


@pytest.mark.parametrize("cas", CAS)
def test_ni_les_canaux_ni_la_profondeur_ne_decident(mat, cas):
    """LE REPROCHE, EN TEST. Deux lignes de mêmes canaux et même profondeur ne
    peuvent pas différer sur « ≈ » : si elles diffèrent, c'est parce que leur
    RAISON diffère, et cette raison est écrite."""
    d = MS.export_manifest(mat, **cas)
    for a in d["entries"]:
        for b in d["entries"]:
            if a["channels"] != b["channels"] or a["bits"] != b["bits"]:
                continue
            if a["exact"] == b["exact"]:
                continue
            assert a.get("weigh_tag", "") != b.get("weigh_tag", ""), (
                f"{a['name']} et {b['name']} — mêmes canaux, même profondeur, "
                "même raison, et pourtant l'un est mesuré et l'autre estimé.")


def test_mesure_veut_dire_taille_sur_disque(mat):
    """Un « = » annonce l'octet près la taille du PNG du disque."""
    d = MS.export_manifest(mat, fmt="zip", naming="standard", res=0, bits=8)
    dossier = MS.material_dir(mat["id"])
    for e in d["entries"]:
        if not e["exact"]:
            continue
        reel = (dossier / f"{e['kind']}.png").stat().st_size
        assert e["bytes"] == reel, (
            f"{e['name']} déclaré mesuré à {e['bytes']} o pour {reel} o réels")


def test_les_trois_maps_cuites_sont_les_seules_estimees_en_natif(mat):
    """En 8 bits, à définition native, convention standard : SEULES metallic,
    roughness et orm sont estimées — ce sont les seules que `bake_levels`
    transforme. Occlusion, height, normale, couleur et émissive partent
    inchangées. C'est la ligne de partage que l'écran ne montrait pas."""
    d = MS.export_manifest(mat, fmt="zip", naming="standard", res=0, bits=8)
    e = _by_kind(d)
    estimees = {k for k, v in e.items() if not v["exact"]}
    assert estimees == set(MS.BAKED_KINDS), estimees
    for k in MS.BAKED_KINDS:
        assert "cuit" in e[k]["weigh_tag"], e[k]["weigh_tag"]
    # et l'occlusion — L 8 comme roughness — est mesurée, avec sa raison
    assert e["ao"]["exact"] and e["ao"]["channels"] == "L"
    assert e["roughness"]["channels"] == "L" and not e["roughness"]["exact"]


def test_le_maskmap_est_estime_parce_qu_il_n_existe_pas(mat):
    d = MS.export_manifest(mat, fmt="zip", naming="unity_urp", res=0, bits=8)
    e = _by_kind(d)
    assert MS.MASKMAP in e, "le MaskMap Unity manque au bordereau"
    assert not e[MS.MASKMAP]["exact"]
    assert "fabriqué" in e[MS.MASKMAP]["weigh_tag"]
    assert not (MS.material_dir(mat["id"]) / f"{MS.MASKMAP}.png").exists()


def test_le_reechantillonnage_estime_tout(mat):
    d = MS.export_manifest(mat, fmt="zip", naming="standard", res=512, bits=8)
    for e in d["entries"]:
        assert not e["exact"], e["name"]
        assert "rééchantillonné" in e["weigh_tag"] or "fabriqué" in e["weigh_tag"]


def test_le_16_bits_n_estime_que_height_et_normal(mat):
    d = MS.export_manifest(mat, fmt="zip", naming="standard", res=0, bits=16)
    e = _by_kind(d)
    assert e["height"]["bits"] == 16 and e["normal"]["bits"] == 16
    for k in ("height", "normal"):
        assert not e[k]["exact"] and "16 bits" in e[k]["weigh_tag"]
    # la couleur de base reste en 8 bits, donc mesurée : la profondeur d'UNE
    # ligne ne contamine pas les autres.
    assert e["basecolor"]["exact"] and e["basecolor"]["bits"] == 8


def test_le_gltf_estime_tout_par_le_base64(mat):
    d = MS.export_manifest(mat, fmt="gltf", naming="standard", res=0, bits=8)
    for e in d["entries"]:
        assert not e["exact"] and "base64" in e["weigh_tag"]


def test_la_regle_est_publiee_avec_le_bordereau(mat):
    d = MS.export_manifest(mat, fmt="zip", naming="standard", res=0, bits=8)
    r = d.get("weigh_rule") or ""
    assert "mesuré" in r and "estimé" in r and "fabriquer" in r, r
    assert d["exact"] is False          # trois lignes cuites : le total l'est


def test_un_export_sans_fabrication_est_entierement_mesure(mat):
    """Contre-épreuve : en ne demandant QUE les maps qu'aucune fabrication ne
    touche, tout le bordereau devient exact — la règle marche dans les deux
    sens, elle n'est pas un alibi permanent."""
    d = MS.export_manifest(mat, fmt="zip", naming="standard", res=0, bits=8,
                           kinds=["basecolor", "normal", "ao", "height"])
    listed = [e for e in d["entries"] if e["kind"] in
              ("basecolor", "normal", "ao", "height")]
    assert listed and all(e["exact"] for e in listed)
