"""Recette de la ronde 5 du gauntlet Material Forge — trois defauts nommes par
la critique, verrouilles ici.

    runtime\\python\\python.exe -m pytest backend/tests/test_material_gauntlet_r5.py -v

1. LA RUGOSITE S'APPLIQUAIT (POTENTIELLEMENT) DEUX FOIS.
   glTF pose `rugosite = roughnessFactor x metallicRoughnessTexture.G`. Le
   niveau est cuit dans la map, le facteur doit donc valoir 1.0 — et ca doit
   etre DIT, pas devine : `material.json` publiait `props.roughness = 0.25` a
   cote d'un `roughness.png` de moyenne 0.251, sans un mot sur la composition.
   Un script d'import qui lit l'un et branche l'autre appliquait
   0.25 x 0.251 = 0.063. Verrouille ici : le facteur, la valeur effective a
   cinq crans de curseur, le bloc `render` dans meta.json / material.json /
   bordereau, et le bloc `extras` du materiau glTF.

2. LA MAP DE RUGOSITE NE PORTAIT RIEN, ET CE QU'ELLE PORTAIT ETAIT L'ECLAIRAGE.
   Mesure sur les seize matieres du disque, AVANT :
     - « acier rouge » : centiles 5 % et 95 % tous les deux a 64/255, soit
       0.0 % de variation utile — une constante comptee comme map pleine,
       parce que le critere de platitude regardait min/max (0 et 64) au lieu
       de l'amplitude utile ;
     - correlation avec la luminance de la base color : -0.76 a -0.99,
       mediane -0.90. C'est-a-dire l'albedo inverse, comme la reference
       (-0.987) : chaque reflet cuit dans la photo devenait une zone miroir.
   Verrouille ici : un degrade d'eclairage pur ne doit PAS ressortir dans la
   rugosite, une map constante sur 90 % de sa surface doit etre declaree
   constante, et chaque map doit publier sa correlation.

3. LE PREREGLAGE UNITY ETAIT FAUX.
   « Slots URP / HDRP : BaseMap, MaskMap, Occlusion » — or, documentation
   Unity en main : URP Lit n'a AUCUNE propriete Mask Map (Base Map, Metallic
   Map, Normal Map, Height Map, Occlusion Map, Emission Map ; smoothness dans
   l'alpha de la Metallic Map), et HDRP Lit range l'occlusion DANS le canal V
   de son Mask Map, donc n'a pas d'emplacement Occlusion separe. L'archive
   decochait ensuite Occlusion, Roughness et Metallic : choisir « Unity » ne
   remplissait plus aucun emplacement d'URP. Verrouille ici : deux cibles
   separees, et chacune livre de quoi remplir les emplacements de SON moteur.
"""
import io
import json
import os
import pathlib
import struct
import sys
import tempfile
import zipfile

_tmp = tempfile.mkdtemp()
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image, ImageDraw                            # noqa: E402

from app.services import gltf_builder as GB
from app.services import material_store as MS
from app.services import pbr_service as PBR

CRANS = (0.0, 0.25, 0.50, 0.75, 1.00)


# ── sources de test deterministes ────────────────────────────────────────────

def _grain(w=192, h=192, seed=11):
    """Texture a grain reel : bruit fin sur un fond neutre, plus quelques
    creux. Aucun gradient d'eclairage."""
    img = Image.new("RGB", (w, h), (140, 132, 124))
    px = img.load()
    s = seed
    for y in range(h):
        for x in range(w):
            s = (s * 1103515245 + 12345) & 0x7FFFFFFF
            n = (s >> 16) % 48 - 24
            r, g, b = px[x, y]
            px[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)),
                        max(0, min(255, b + n)))
    d = ImageDraw.Draw(img)
    for k in range(9):
        cx, cy = 20 + k * 18, 40 + (k * 37) % 110
        d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=(96, 90, 84))
    return img


def _lit_grain(w=192, h=192):
    """LE MEME grain, multiplie par un fort gradient d'eclairage gauche-droite
    (facteur 0.35 -> 1.0). Un moteur re-eclairera la matiere lui-meme : ce
    gradient ne doit teindre NI la rugosite NI la metallicite, sinon l'ombre
    de la photo est cuite dans la matiere."""
    src = _grain(w, h)
    px = src.load()
    for y in range(h):
        for x in range(w):
            k = 0.35 + 0.65 * x / (w - 1)
            r, g, b = px[x, y]
            px[x, y] = (int(r * k), int(g * k), int(b * k))
    return src


def _column_means(img, cols=8):
    """Moyenne de luminance par bande verticale — la signature d'un gradient
    horizontal. Les deux bandes de bord sont ecartees : la source de ce test
    n'est PAS raccordable (elle est sombre a gauche, claire a droite), donc le
    bordage cyclique y cree une marche legitime qui n'a rien a voir avec la
    fuite d'eclairage qu'on mesure."""
    g = img.convert("L")
    w, h = g.size
    step = w // cols
    out = [PBR.stats(g.crop((i * step, 0, (i + 1) * step, h)))["mean"]
           for i in range(cols)]
    return out[1:-1]


def _mat(name="acier rouge", **props):
    p = dict(MS.default_props())
    p.update(props)
    return MS.normalize_material({"id": "mat_0000beef", "name": name,
                                  "props": p})


def _glb_json(glb: bytes) -> dict:
    ln = struct.unpack("<I", glb[12:16])[0]
    return json.loads(glb[20:20 + ln].decode("utf-8"))


# ═══════════ 1. la rugosite ne s'applique pas deux fois ═════════════════════

def test_the_slider_is_the_effective_roughness_at_every_crank():
    """Curseur -> rugosite EFFECTIVE = roughnessFactor x texture.G, lue dans le
    GLB reellement produit. Aucune tolerance sur le facteur : il vaut 1.0 ou le
    niveau est compte deux fois."""
    maps = PBR.derive_maps(_grain(), None, list(MS.MAP_KINDS))
    seen = {}
    for lv in CRANS:
        props = dict(MS.default_props(), roughness=lv, metallic=0.35)
        baked = PBR.bake_levels(maps, props)
        payload = {k: MS.png_bytes(v, k, 8) for k, v in baked.items()}
        glb = GB.build_glb(payload, props, "sphere")
        pbr = _glb_json(glb)["materials"][0]["pbrMetallicRoughness"]
        assert "metallicRoughnessTexture" in pbr
        assert pbr["roughnessFactor"] == 1.0, (lv, pbr["roughnessFactor"])
        assert pbr["metallicFactor"] == 1.0, (lv, pbr["metallicFactor"])
        g = PBR.stats(baked["orm"].convert("RGB").split()[1])["mean"] / 255.0
        effective = pbr["roughnessFactor"] * g
        assert abs(effective - lv) <= 2.0 / 255.0, (lv, effective)
        seen[lv] = effective
    assert sorted(seen) == list(CRANS)
    # et la metallicite reste a son propre cran, sans que la rugosite l'entraine
    b = PBR.bake_levels(maps, dict(MS.default_props(), roughness=0.25,
                                   metallic=0.35))
    m = PBR.stats(b["orm"].convert("RGB").split()[2])["mean"] / 255.0
    assert abs(m - 0.35) <= 2.0 / 255.0, m


def test_effective_levels_are_measured_on_the_bytes_that_ship():
    maps = PBR.derive_maps(_grain(), None, list(MS.MAP_KINDS))
    for lv in CRANS:
        props = dict(MS.default_props(), roughness=lv, metallic=1.0 - lv)
        eff = PBR.effective_levels(PBR.bake_levels(maps, props))
        assert abs(eff["roughness"] - lv) <= 0.01, (lv, eff)
        assert abs(eff["metallic"] - (1.0 - lv)) <= 0.01, (lv, eff)


def test_the_glb_material_declares_how_the_factor_composes():
    """Le fichier lui-meme le dit : un lecteur n'a pas a deviner ni a nous
    croire sur parole."""
    maps = PBR.derive_maps(_grain(), None, list(MS.MAP_KINDS))
    props = dict(MS.default_props(), roughness=0.25, metallic=1.0)
    payload = {k: MS.png_bytes(v, k, 8)
               for k, v in PBR.bake_levels(maps, props).items()}
    extras = _glb_json(GB.build_glb(payload, props, "sphere"))["materials"][0]["extras"]
    assert set(extras["levelsBaked"]) == {"metallic", "roughness"}
    assert "1.0" in extras["note"]
    assert extras["settings"]["roughness"] == 0.25

    # sans texture packee, les facteurs reprennent leur role — et le disent
    bare = {"basecolor": payload["basecolor"]}
    ex2 = _glb_json(GB.build_glb(bare, props, "cube"))["materials"][0]
    assert ex2["extras"]["levelsBaked"] == []
    assert ex2["pbrMetallicRoughness"]["roughnessFactor"] == 0.25
    assert "metallicRoughnessTexture" not in ex2["pbrMetallicRoughness"]


def test_material_json_carries_the_composition_contract():
    """Le trou exact : `props.roughness` seul se relit comme un facteur."""
    mat = _mat(roughness=0.25, metallic=1.0)
    assert mat["render"]["roughnessFactor"] == 1.0
    assert mat["render"]["metallicFactor"] == 1.0
    assert "roughnessFactor x metallicRoughnessTexture.G" in mat["render"]["formula"]

    maps = PBR.bake_levels(PBR.derive_maps(_grain(), None,
                                           list(MS.MAP_KINDS)), mat["props"])
    blob = MS.export_zip(mat, maps, "standard", 8, None)
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        meta = json.loads(z.read("material.json").decode("utf-8"))
        readme = z.read("LISEZMOI.txt").decode("utf-8")
    assert meta["render"]["roughnessFactor"] == 1.0
    assert meta["render"]["measured"] is True
    assert abs(meta["render"]["effective"]["roughness"] - 0.25) <= 0.01
    assert "roughnessFactor = 1.0" in readme
    assert "cuites dans les maps" in readme.lower()


def test_the_manifest_publishes_the_same_contract():
    mat = _mat(roughness=0.5)
    mani = MS.export_manifest(mat, "zip", "standard")
    assert mani["render"]["roughnessFactor"] == 1.0
    assert mani["render"]["metallicFactor"] == 1.0


# ═══════════ 2. la map porte quelque chose, et c'est independant ════════════

def test_a_lighting_gradient_does_not_leak_into_roughness():
    """LE test de la ronde. Meme grain, une fois a plat et une fois multiplie
    par un gradient d'eclairage x0.35 -> x1.0. La base color, elle, PORTE le
    gradient (c'est son role). La rugosite ne doit pas : sinon la matiere
    s'effondre des qu'on la re-eclaire."""
    flat = PBR.derive_maps(_grain(), None, ["roughness", "basecolor"])
    lit = PBR.derive_maps(_lit_grain(), None, ["roughness", "basecolor"])

    base_cols = _column_means(lit["basecolor"])
    # la base color PORTE le gradient (60 -> 113 sur les bandes retenues)
    assert base_cols[-1] - base_cols[0] > 40, base_cols

    # MESURE : la rugosite derivee du grain eclaire penche de 1.9 niveau sur
    # les six bandes retenues, contre 94.2 avec l'ancienne formule (albedo
    # inverse) pour le meme gradient de 52 niveaux dans la base color.
    cols = _column_means(lit["roughness"])
    tilt = abs(cols[-1] - cols[0])
    assert tilt < 8, cols
    ref = abs(_column_means(flat["roughness"])[-1]
              - _column_means(flat["roughness"])[0])
    assert tilt < ref + 8, (tilt, ref)

    # et la preuve chiffree : la correlation avec la luminance
    r_lit = PBR.map_report(lit)["maps"]["roughness"]
    assert abs(r_lit["corr_lum"]) < PBR.DEPENDENT_R, r_lit["corr_lum"]
    # l'ancienne formule, elle, est bien l'albedo inverse — on le montre
    old = PBR.derive_maps(_lit_grain(), {"roughness_source": "albedo"},
                          ["roughness", "basecolor"])
    r_old = PBR.map_report(old)["maps"]["roughness"]
    assert r_old["corr_lum"] < -0.95, r_old["corr_lum"]
    assert r_old["dependent"] is True
    assert abs(r_lit["corr_lum"]) < abs(r_old["corr_lum"])


def test_every_map_publishes_its_correlation_with_the_base_color():
    maps = PBR.derive_maps(_grain(), None, list(MS.MAP_KINDS))
    rep = PBR.map_report(maps)
    for kind in MS.MAP_KINDS:
        assert "corr_lum" in rep["maps"][kind], kind
        assert "dependent" in rep["maps"][kind], kind
        assert -1.0 <= rep["maps"][kind]["corr_lum"] <= 1.0
    assert "dependent" in rep


def test_a_map_flat_over_90_percent_of_its_surface_is_called_flat():
    """Le critere de platitude regardait min/max : « acier rouge » avait
    min=0 max=64 pour p5 = p95 = 64. Une poignee de pixels aberrants suffisait
    a faire compter une constante comme une map pleine."""
    img = Image.new("L", (100, 100), 64)
    px = img.load()
    for i in range(20):                        # 0.2 % de pixels aberrants
        px[i, 0] = 0
        px[i, 1] = 128
    st = PBR.stats(img)
    assert (st["min"], st["max"]) == (0, 128)  # les extremes s'ouvrent
    assert st["span"] == 0                     # l'amplitude utile, non
    rep = PBR.map_report({"roughness": img})["maps"]["roughness"]
    assert rep["informative"] is False
    assert "uniforme" in rep["note"]


def test_the_extreme_cranks_are_declared_constant_not_full():
    """A 0.00 et 1.00 aucune variation ne tient sous la moyenne demandee : la
    map EST constante. On le dit, au lieu de la compter dans les 8 maps."""
    maps = PBR.derive_maps(_grain(), None, list(MS.MAP_KINDS))
    for lv, expect in ((0.0, False), (0.5, True), (1.0, False)):
        baked = PBR.bake_levels(maps, dict(MS.default_props(), roughness=lv))
        rep = PBR.map_report(baked)["maps"]["roughness"]
        assert rep["informative"] is expect, (lv, rep)
        if not expect:
            assert rep["note"], lv


def test_level_stats_agrees_with_the_baked_map():
    """L'ecran met a jour ses chiffres au curseur sans relire 16 M pixels :
    la prevision doit coller a la mesure, y compris sur « la map est-elle
    encore informative ? »."""
    maps = PBR.derive_maps(_grain(), None, ["roughness", "basecolor"])
    pattern = PBR.stats(maps["roughness"])
    for lv in CRANS:
        baked = PBR.bake_levels(maps, dict(MS.default_props(), roughness=lv))
        real = PBR.stats(baked["roughness"])
        told = PBR.level_stats(pattern, lv)
        assert abs(told["mean"] - real["mean"]) <= 2.0, (lv, told, real)
        assert abs(told["span"] - real["span"]) <= 4, (lv, told, real)
        assert told["informative"] == (real["span"] > PBR.FLAT_SPAN), lv


def test_the_new_roughness_still_tiles():
    """Toutes les convolutions restent cycliques : la map derivee d'une tuile
    3x3 est, au centre, EXACTEMENT celle derivee de la tuile seule."""
    tile = _grain(96, 96)
    one = PBR.derive_maps(tile, None, ["roughness"])["roughness"]
    big = Image.new("RGB", (288, 288))
    for dy in range(3):
        for dx in range(3):
            big.paste(tile, (dx * 96, dy * 96))
    mid = PBR.derive_maps(big, None, ["roughness"])["roughness"] \
        .crop((96, 96, 192, 192))
    # meme motif au centre : la derivation ne lit rien hors tuile
    diff = [abs(a - b) for a, b in zip(one.tobytes(), mid.tobytes())]
    assert max(diff) <= 2, max(diff)


# ═══════════ 3. URP et HDRP sont deux moteurs ═══════════════════════════════

def test_urp_and_hdrp_are_separate_targets():
    assert "unity" not in MS.NAMINGS
    assert MS.clean_naming("unity") == "unity_urp"     # l'ancien lien vit
    assert set(MS.UNITY_NAMINGS) <= set(MS.NAMINGS)
    assert MS.NAMING_LABELS["unity_urp"] != MS.NAMING_LABELS["unity_hdrp"]


def test_urp_is_never_told_it_has_a_mask_map():
    """URP Lit n'a pas de propriete Mask Map — le mot ne doit apparaitre ni
    dans la note, ni dans un nom de fichier, ni dans un emplacement."""
    urp = [n for n in MS.naming_catalog() if n["id"] == "unity_urp"][0]
    haystack = (urp["note"] + " "
                + " ".join(s["file"] + " " + s["slot"] for s in urp["slots"]))
    assert "MaskMap" not in haystack and "Mask Map" not in haystack.replace(
        "n'a pas de Mask Map", "")
    slots = {s["kind"]: s["slot"] for s in urp["slots"]}
    assert "Metallic Map" in slots[MS.MASKMAP]
    assert "Occlusion Map" in slots[MS.MASKMAP]
    assert "Base Map" in slots["basecolor"]
    assert "Normal Map" in slots["normal"]
    assert "Emission Map" in slots["emissive"]


def test_hdrp_puts_occlusion_inside_the_mask_map():
    hdrp = [n for n in MS.naming_catalog() if n["id"] == "unity_hdrp"][0]
    slots = {s["kind"]: s["slot"] for s in hdrp["slots"]}
    assert "Mask Map" in slots[MS.MASKMAP]
    # pas d'emplacement Occlusion separe sous HDRP
    assert "ao" not in slots
    told = MS.engine_slot("ao", "unity_hdrp")
    assert "aucun emplacement" in told.lower() and "Mask Map" in told


def test_each_unity_archive_actually_fills_its_engine_slots():
    """Le reproche exact : « choisir Unity produit une archive qui ne peut pas
    remplir les slots d'URP ». On verifie que chaque emplacement annonce a un
    fichier reel dans l'archive, et que ce fichier a les bons canaux."""
    mat = _mat(name="fer rouille", roughness=0.4, metallic=0.8)
    maps = PBR.bake_levels(PBR.derive_maps(_grain(), None,
                                           list(MS.MAP_KINDS)), mat["props"])
    for naming in MS.UNITY_NAMINGS:
        want = MS.default_export_maps(naming)
        sel = {k: v for k, v in maps.items() if k in want}
        if MS.MASKMAP in want:
            sel[MS.MASKMAP] = MS.build_maskmap(maps)
        blob = MS.export_zip(mat, sel, naming, 8, None)
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            names = set(z.namelist())
            readme = z.read("LISEZMOI.txt").decode("utf-8")
            packed = MS.naming_map(naming, mat["name"])[MS.MASKMAP]
            assert packed in names, (naming, sorted(names))
            img = Image.open(io.BytesIO(z.read(packed)))
            assert img.mode == "RGBA", naming     # sans alpha, pas de smoothness
            r, g, b, a = img.split()
            # R = metal (0.8), V = occlusion, B = detail (0), A = smoothness
            assert abs(PBR.stats(r)["mean"] / 255.0 - 0.8) < 0.02, naming
            assert PBR.stats(b)["mean"] == 0.0, naming
            assert abs(PBR.stats(a)["mean"] / 255.0 - (1.0 - 0.4)) < 0.02, naming
            for kind in ("basecolor", "normal", "height", "emissive"):
                assert MS.naming_map(naming, mat["name"])[kind] in names, \
                    (naming, kind)
        # le LISEZMOI dit ou deposer chaque fichier
        assert "Où déposer chaque fichier" in readme, naming
        assert MS.engine_slot(MS.MASKMAP, naming)[:20] in readme, naming


def _on_disk(name="fer rouille", **props):
    """Une matiere reelle sur disque (le bordereau lit des tailles reelles)."""
    mat = MS.create_material(name=name, prompt=name, res=192,
                             props=dict(MS.default_props(), **props))
    maps = PBR.derive_maps(_grain(), None, list(MS.MAP_KINDS))
    MS.save_maps(mat["id"], maps)
    return MS.write_material(MS.refresh_report(mat, maps))


def test_the_manifest_names_the_destination_slot():
    mat = _on_disk("fer manifeste")
    for naming in ("unity_urp", "unity_hdrp", "unreal", "godot"):
        mani = MS.export_manifest(mat, "zip", naming)
        assert mani["naming"] == naming
        assert mani["naming_note"]
        sel = [e for e in mani["entries"] if e["selected"]]
        assert sel, naming
        assert all(e["slot"] for e in sel), \
            (naming, [e["kind"] for e in sel if not e["slot"]])
    # la convention neutre n'invente pas d'emplacement moteur
    assert MS.engine_slot("basecolor", "standard") == ""


def test_the_alias_keeps_old_links_alive():
    mat = _mat(name="fer rouille")
    a = MS.export_manifest(mat, "zip", "unity")
    b = MS.export_manifest(mat, "zip", "unity_urp")
    assert a["naming"] == b["naming"] == "unity_urp"
    assert MS.export_filename(mat, "zip", "unity") == \
        MS.export_filename(mat, "zip", "unity_urp")
    assert MS.clean_naming("n'importe quoi") == "standard"
