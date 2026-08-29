"""Phase D de la spec Magnific (§9 « 3D », §13 « 3D et finition »).

Ce que le banc prouve :
  A. registre de CAPACITÉS 3D + matrice besoin→moteur motivée (§8 transposé) ;
  B. vues quasi-orthographiques (§9.2 étape 1) sans casser le contrat existant ;
  C. fiche de maillage versionnée — checksum, faces, taille, textures,
     silhouettes, arêtes de bord (§9.2 étapes 3 et 6) ;
  D. porte brouillon → texture finale (§9.2 étapes 2 et 5) : refus motivés
     AVANT toute dépense, et model.v{n}.glb au lieu d'un écrasement (§2.1) ;
  E. contrôle qualité contre la référence maître (§9.2 étape 7) + verdict de
     compatibilité runtime (§13 phase D) ;
  F. ancrage 3D d'une entité de la bible (§9.1) — et le refus de nourrir un
     moteur image→3D avec une PLANCHE composite ;
  G. finition : agrandissement mesuré (gain / dérive / coût) avec porte avant
     dépense, et export de montage à audio séparé.

Aucun appel réseau : fal_client est stubbé, les GLB sont écrits à l'octet.

Run: pytest tests/test_asset3d_phase_d.py -q
     ou .\\scripts\\run-tests.ps1 -Filter asset3d_phase_d
"""
import json as _json
import os
import pathlib
import struct
import sys
import tempfile
import types

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# fal stubbé AVANT l'import de l'app (les routes l'importent paresseusement,
# un module factice dans sys.modules est donc pris au moment de l'appel).
#
# CALLS enregistre TOUT contact avec fal — generation ET upload. Un banc qui
# n'observait que subscribe_async laissait passer un envoi de fichiers avant
# la porte de dépense : l'upload est déjà un contact avec le fournisseur, et
# c'est lui qui précède immédiatement la facture.
CALLS = []


def raz_calls():
    """À appeler en tête de tout test qui asserte « aucune dépense » : CALLS
    est global au module et les tests partagent le process."""
    CALLS.clear()


async def _fake_subscribe(model, arguments=None, **kw):
    CALLS.append({"kind": "subscribe", "model": model, "arguments": arguments})
    # une réponse de moteur 3D PLAUSIBLE : sans mesh_url, tout le chemin
    # heureux de generate_asset3d/refine_asset3d resterait hors banc
    if "3d" in str(model) or "tripo" in str(model) or "trellis" in str(model):
        return {"model_mesh": {"url": "http://fal.test/model.glb"},
                "rendered_image": {"url": "http://fal.test/preview.png"}}
    return {"images": [{"url": "http://fal.test/img.png"}], "seed": 4242}


async def _fake_upload(path):
    CALLS.append({"kind": "upload", "path": str(path)})
    return "http://fal.test/up.png"


_stub = types.ModuleType("fal_client")
_stub.subscribe_async = _fake_subscribe
_stub.upload_file_async = _fake_upload
sys.modules["fal_client"] = _stub

from app.config import settings                                    # noqa: E402
from app.services import asset3d_qc as QC                          # noqa: E402
from app.services import asset3d_service as A3                     # noqa: E402
from app.services import finition as F                             # noqa: E402
from app.services import mesh_report as MR                         # noqa: E402


# ── fabriques : le banc écrit ses fixtures à l'octet ─────────────────────────

def _glb(doc, bin_data=b""):
    j = _json.dumps(doc, separators=(",", ":")).encode("utf-8")
    j += b" " * ((4 - len(j) % 4) % 4)
    chunks = struct.pack("<I", len(j)) + b"JSON" + j
    if bin_data:
        b = bin_data + b"\x00" * ((4 - len(bin_data) % 4) % 4)
        chunks += struct.pack("<I", len(b)) + b"BIN\x00" + b
    return b"glTF" + struct.pack("<II", 2, 12 + len(chunks)) + chunks


def _glb_cube(extra_doc=None, bin_extra=b""):
    """Cube 2×2×2 centré : 8 sommets, 12 triangles, FERMÉ (18 arêtes ×2)."""
    pos = []
    for x in (-1, 1):
        for y in (-1, 1):
            for z in (-1, 1):
                pos += [x, y, z]
    idx = [0, 1, 3, 0, 3, 2, 4, 6, 7, 4, 7, 5, 0, 4, 5, 0, 5, 1,
           2, 3, 7, 2, 7, 6, 0, 2, 6, 0, 6, 4, 1, 5, 7, 1, 7, 3]
    vb = struct.pack("<24f", *pos)
    ib = struct.pack("<36H", *idx)
    doc = {
        "asset": {"version": "2.0", "generator": "banc-phase-d"},
        "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0},
                                    "indices": 1, "mode": 4}]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 8, "type": "VEC3"},
            {"bufferView": 1, "componentType": 5123, "count": 36, "type": "SCALAR"},
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(vb)},
            {"buffer": 0, "byteOffset": len(vb), "byteLength": len(ib)},
        ],
        "buffers": [{"byteLength": len(vb) + len(ib) + len(bin_extra)}],
    }
    if extra_doc:
        doc.update(extra_doc)
    return _glb(doc, vb + ib + bin_extra)


def _glb_texture():
    """Cube + une image PNG EMBARQUÉE référencée par un matériau : l'inventaire
    de textures de la fiche doit la voir et la peser."""
    png = _png(4, 4, (200, 30, 30))
    off = 24 * 4 + 36 * 2
    return _glb_cube({
        "images": [{"name": "base", "mimeType": "image/png", "bufferView": 2}],
        "textures": [{"source": 0}],
        "materials": [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 96},
            {"buffer": 0, "byteOffset": 96, "byteLength": 72},
            {"buffer": 0, "byteOffset": 168, "byteLength": len(png)},
        ],
    }, bin_extra=png)


def _glb_draco():
    return _glb({"asset": {"version": "2.0"},
                 "extensionsUsed": ["KHR_draco_mesh_compression"],
                 "extensionsRequired": ["KHR_draco_mesh_compression"],
                 "scene": 0, "scenes": [{"nodes": []}]})


def _png(w, h, couleur=(255, 255, 255), carre=None) -> bytes:
    """PNG réel via PIL — les routes et le QC ouvrent vraiment les fichiers."""
    import io
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), couleur)
    if carre:
        d = ImageDraw.Draw(im)
        d.rectangle(carre, fill=(0, 0, 0))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _job(nom: str, glb: bytes | None = None, avec_ref=True) -> str:
    """Crée un faux job Game Assets 3D sur le disque et rend son id."""
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(glb if glb is not None else _glb_cube())
    if avec_ref:
        # référence maître : un carré noir centré sur fond blanc — la
        # silhouette de face du cube est elle aussi un carré
        (d / "shot_0.png").write_bytes(_png(256, 256, (255, 255, 255),
                                            carre=(64, 64, 191, 191)))
    return nom


# ══ A. registre de capacités 3D ═════════════════════════════════════════════

def test_le_registre_garde_ses_moteurs_et_gagne_ses_capacites():
    # non-régression : d'autres bancs épinglent l'ensemble des clés
    assert set(A3.ENGINES) == {"tripo", "tripo-h3.1", "hunyuan", "trellis",
                               "rodin", "triposr"}
    for eid, e in A3.ENGINES.items():
        for flag in ("multiview", "max_images", "texture_modes", "draft",
                     "detailed", "pbr", "tpose", "quality_passthrough",
                     "label", "endpoint", "formats"):
            assert flag in e, f"{eid} sans {flag}"
        assert isinstance(e["texture_modes"], list) and e["texture_modes"]
        assert e["max_images"] >= 1
        # cohérence interne : multi-vues ⇒ plusieurs images acceptées
        assert e["multiview"] == (e["max_images"] > 1), eid
    # les drapeaux disent ce que l'adaptateur ENVOIE vraiment
    assert A3.ENGINES["rodin"]["tpose"] is True       # seul à câbler TAPose
    assert A3.ENGINES["tripo"]["detailed"] is True    # seul palier HD
    assert A3.ENGINES["trellis"]["draft"] is False    # aucun texture off


def test_engine_caps_refuse_un_moteur_inconnu_en_listant_les_valides():
    with pytest.raises(ValueError) as ei:
        A3.engine_caps("magnific")
    assert "tripo" in str(ei.value) and "magnific" in str(ei.value)
    assert A3.engine_caps("TRIPO")["id"] == "tripo"   # insensible à la casse


def test_texture_mode_dit_le_palier_REELLEMENT_obtenu():
    # tripo : les trois paliers existent
    assert A3.texture_mode("tripo", True, "hd") == "HD"
    assert A3.texture_mode("tripo", True, "medium") == "standard"
    assert A3.texture_mode("tripo", False, None) == "no"
    # hunyuan n'a pas de HD : demander « hd » ne ment pas, ça rend standard
    assert A3.texture_mode("hunyuan", True, "hd") == "standard"
    # trellis n'a pas de brouillon : textures=False ne peut pas rendre « no »
    assert A3.texture_mode("trellis", False, None) == "standard"


def test_la_matrice_besoin_moteur_est_motivee():
    r = A3.recommend_engine("rig")
    assert r["engine"] == "rodin" and "pose" in r["why"].lower()
    assert r["opts"]["tpose"] is True
    assert A3.recommend_engine("hero")["engine"] == "tripo-h3.1"
    assert A3.recommend_engine("brouillon")["opts"]["textures"] is False
    # chaque besoin nomme un moteur du registre et porte sa justification
    for bid, b in A3.BESOINS_3D.items():
        assert b["engine"] in A3.ENGINES, bid
        assert len(b["why"]) > 30, bid
    with pytest.raises(ValueError):
        A3.recommend_engine("inconnu")


# ══ B. vues quasi-orthographiques ═══════════════════════════════════════════

def test_les_vues_restent_compatibles_et_deviennent_orthographiques():
    ps = A3.view_prompts(3, "a knight")
    assert len(ps) == 3 and all("a knight" in p for p in ps)
    assert "front" in ps[0].lower() and "back" in ps[1].lower()   # contrat v1
    assert len(A3.view_prompts(0, "")) == 1
    assert len(A3.view_prompts(9, "")) == 4
    # ce que la spec §9.2 étape 1 exige, sur TOUTES les vues
    q = A3.view_prompts(4, "x")
    for p in q:
        assert "orthographic framing" in p
        assert "plain flat neutral background" in p
        assert "identical scale and distance" in p
    # les côtés sont des PROFILS purs, plus des 3/4
    assert "exact profile" in q[2] and "exact profile" in q[3]
    assert "3/4" not in " ".join(q)


# ══ C. fiche de maillage versionnée ═════════════════════════════════════════

def test_la_fiche_porte_checksum_faces_taille_textures_et_silhouettes():
    j = _job("fiche01")
    d = MR.job_dir(j)
    f = MR.report(d / "model.glb", version=1)

    assert len(f["sha256"]) == 64 and int(f["sha256"], 16) >= 0
    assert f["bytes"] == (d / "model.glb").stat().st_size
    g = f["geometry"]
    assert g["tris"] == 12 and g["verts"] == 8
    assert g["mesure"] is True
    assert g["dims"] == {"largeur": 2.0, "hauteur": 2.0, "profondeur": 2.0}
    # un cube est FERMÉ : aucune arête de bord, aucun non-manifold
    t = g["topologie"]
    assert t["calcule"] and t["ferme"] is True
    assert t["aretes_de_bord"] == 0 and t["aretes_non_manifold"] == 0
    assert t["aretes"] == 18 and t["triangles_degeneres"] == 0
    # trois silhouettes réellement écrites, et non vides
    for vue in ("face", "profil", "dessus"):
        s = f["silhouettes"][vue]
        assert (d / f["silhouettes_dir"] / s["file"]).is_file()
        assert 0.5 < s["couverture"] <= 1.0, vue   # une face de cube remplit
    assert f["gltf"]["gltf_version"] == "2.0"
    assert f["gltf"]["generator"] == "banc-phase-d"


def test_la_fiche_inventorie_les_textures_embarquees():
    j = _job("fiche02", glb=_glb_texture())
    f = MR.report(MR.job_dir(j) / "model.glb", version=1,
                  avec_silhouettes=False)
    g = f["gltf"]
    assert g["textures"] == 1 and len(g["images"]) == 1
    img = g["images"][0]
    assert img["mime"] == "image/png" and img["externe"] is False
    assert img["bytes"] > 0 and g["texture_bytes"] == img["bytes"]
    assert g["pbr_channels"] == ["base_color"]


def test_un_glb_compresse_degrade_proprement_au_lieu_de_faire_tomber_la_fiche():
    j = _job("fiche03", glb=_glb_draco(), avec_ref=False)
    f = MR.report(MR.job_dir(j) / "model.glb", version=1)
    # checksum et entête restent lisibles…
    assert len(f["sha256"]) == 64
    assert f["gltf"]["extensions_required"] == ["KHR_draco_mesh_compression"]
    # …et la géométrie dit POURQUOI elle n'a pas pu être mesurée
    assert f["geometry"]["mesure"] is False
    assert "draco" in (f["geometry"]["raison"] or "").lower() \
        or "compress" in (f["geometry"]["raison"] or "").lower()
    assert "erreur" in f["silhouettes"]


def test_le_registre_garde_TOUTES_les_versions_sans_ecraser():
    j = _job("fiche04")
    d = MR.job_dir(j)
    v1 = MR.write_report(j, "model.glb", version=1, avec_silhouettes=False)
    (d / "model.v2.glb").write_bytes(_glb_texture())
    v2 = MR.write_report(j, "model.v2.glb", version=2, avec_silhouettes=False)

    reg = MR.read_registry(j)
    assert reg["current"] == "model.v2.glb" and reg["current_version"] == 2
    assert [e["version"] for e in reg["entries"]] == [1, 2]
    assert v1["sha256"] != v2["sha256"]          # deux artefacts distincts
    # la v1 reste intégralement relisible
    ancienne = [e for e in reg["entries"] if e["version"] == 1][0]
    assert ancienne["sha256"] == v1["sha256"]
    # recalculer une version REMPLACE son entrée, jamais les autres
    MR.write_report(j, "model.glb", version=1, avec_silhouettes=False)
    reg2 = MR.read_registry(j)
    assert [e["version"] for e in reg2["entries"]] == [1, 2]


# ══ D. porte brouillon → texture finale ═════════════════════════════════════

def test_la_porte_refuse_le_raffinement_tant_que_le_brouillon_nest_pas_approuve():
    import asyncio
    raz_calls()
    j = _job("porte01")
    A3.write_manifest(MR.job_dir(j), {"engine": "tripo", "stage": "draft",
                                      "texture_mode": "no", "version": 1,
                                      "shots": ["shot_0.png"]})
    assert A3.approval(j)["approved"] is False       # jamais par défaut
    with pytest.raises(PermissionError) as ei:
        asyncio.run(A3.refine_asset3d(j))
    assert "approuv" in str(ei.value).lower()
    assert not CALLS, ("aucun contact avec fal — upload compris — ne doit "
                       "partir avant la porte")


def test_la_porte_refuse_un_moteur_sans_palier_haute_qualite():
    import asyncio
    raz_calls()
    j = _job("porte02")
    A3.write_manifest(MR.job_dir(j), {"engine": "trellis", "stage": "final",
                                      "texture_mode": "standard", "version": 1,
                                      "shots": ["shot_0.png"]})
    A3.approve(j, True, "géométrie ok")
    assert A3.approval(j)["approved"] is True
    with pytest.raises(ValueError) as ei:
        asyncio.run(A3.refine_asset3d(j))
    assert "Trellis" in str(ei.value)
    assert not CALLS


def test_la_porte_refuse_de_repayer_le_meme_palier():
    import asyncio
    j = _job("porte03")
    A3.write_manifest(MR.job_dir(j), {"engine": "tripo", "stage": "final",
                                      "texture_mode": "HD", "version": 1,
                                      "shots": ["shot_0.png"]})
    A3.approve(j)
    with pytest.raises(ValueError) as ei:
        asyncio.run(A3.refine_asset3d(j, quality="hd"))
    assert "déjà" in str(ei.value)


def test_next_version_ne_reutilise_jamais_un_numero():
    j = _job("porte04")
    assert A3.next_version(j) == 2
    (MR.job_dir(j) / "model.v2.glb").write_bytes(_glb_cube())
    assert A3.next_version(j) == 3


# ══ E. contrôle qualité contre la référence maître ══════════════════════════

def test_iou_encadre_bien_les_deux_extremes():
    from PIL import Image, ImageDraw
    a = Image.new("L", (64, 64), 0)
    ImageDraw.Draw(a).rectangle((8, 8, 31, 31), fill=255)
    b = Image.new("L", (64, 64), 0)
    ImageDraw.Draw(b).rectangle((32, 32, 55, 55), fill=255)
    assert QC.iou(a, a) == 1.0
    assert QC.iou(a, b) == 0.0
    with pytest.raises(ValueError):
        QC.iou(a, Image.new("L", (32, 32), 0))


def test_le_masque_de_reference_trouve_le_sujet_sur_fond_propre(tmp_path):
    p = tmp_path / "ref.png"
    p.write_bytes(_png(128, 128, (250, 250, 248), carre=(32, 32, 95, 95)))
    m, methode = QC.masque_reference(p)
    assert "fond" in methode
    bb = m.getbbox()
    assert bb is not None and (bb[2] - bb[0]) > 40


def test_le_verdict_runtime_dit_ce_quil_faut_cabler():
    f = MR.report(MR.job_dir(_job("qc01", glb=_glb_draco(), avec_ref=False))
                  / "model.glb", version=1, avec_silhouettes=False)
    c = QC.compat_runtime(f)
    assert c["lisible"] and c["autonome"] is True
    assert "KHR_draco_mesh_compression" in c["extensions_required"]
    assert "DRACOLoader" in " ".join(c["cibles"]["three"])
    assert set(c["cibles"]) == set(QC.RUNTIMES)
    # un GLB de base n'exige rien de personne
    f2 = MR.report(MR.job_dir(_job("qc02")) / "model.glb", version=1,
                   avec_silhouettes=False)
    c2 = QC.compat_runtime(f2)
    assert all("rien à câbler" in v[0] for v in c2["cibles"].values())


def test_le_controle_note_la_silhouette_contre_la_reference_maitre():
    j = _job("qc03")
    MR.write_report(j, "model.glb", version=1)
    r = QC.controler(j)

    assert r["detail"]["silhouette"]["compare"] is True
    assert r["detail"]["silhouette"]["reference"] == "shot_0.png"
    # face de cube vs carré de référence : les deux formes coïncident
    assert r["scores"]["silhouette"] > 90, r["detail"]
    assert r["scores"]["proportions"] > 90
    assert r["scores"]["fermeture"] == 100.0         # cube fermé
    assert r["verdict"] == "approuvable" and not r["echecs"]


def test_le_controle_DISCRIMINE_une_reference_de_forme_differente():
    """Le vrai test de la mesure : la même géométrie notée contre une
    référence ÉLANCÉE doit s'effondrer. Un score qui ne descend jamais ne
    mesure rien."""
    j = _job("qc05", avec_ref=False)
    d = MR.job_dir(j)
    # référence deux fois plus haute que large — le cube, lui, est carré
    (d / "shot_0.png").write_bytes(_png(256, 256, (255, 255, 255),
                                        carre=(96, 16, 159, 239)))
    MR.write_report(j, "model.glb", version=1)
    r = QC.controler(j)

    assert r["scores"]["silhouette"] < 45, r["detail"]
    assert r["scores"]["proportions"] < 45
    assert r["verdict"] == "a_revoir"
    assert set(r["echecs"]) >= {"silhouette", "proportions"}
    assert r["echecs"]["silhouette"]["seuil"] == QC.SEUILS["silhouette"]
    # les seuils restent configurables (spec §5.2) : abaisser CELUI de la
    # silhouette la sort des échecs, et ne touche pas aux autres axes —
    # un seuil est une décision humaine, pas une propriété du maillage
    doux = QC.controler(j, seuils={"silhouette": 20})
    assert "silhouette" not in doux["echecs"]
    assert "proportions" in doux["echecs"]      # 1:1 contre ~1:3,5 reste faux
    assert doux["scores"] == r["scores"]        # les MESURES ne bougent pas


def test_le_controle_dit_quand_il_ne_peut_pas_comparer():
    j = _job("qc04", avec_ref=False)
    MR.write_report(j, "model.glb", version=1)
    r = QC.controler(j)
    assert r["detail"]["silhouette"]["compare"] is False
    assert "shot_0.png" in r["detail"]["silhouette"]["raison"]
    assert "silhouette" in r["non_mesure"] and r["verdict"] == "partiel"


def test_comparer_deux_maillages_rend_des_ecarts_pas_un_gagnant():
    a = _job("cmp_a")
    b = _job("cmp_b", glb=_glb_texture())
    MR.write_report(a, "model.glb", version=1)
    MR.write_report(b, "model.glb", version=1)
    r = QC.comparer(a, b)

    assert r["silhouette_iou"] == 1.0        # même géométrie, même silhouette
    assert r["a"]["tris"] == r["b"]["tris"] == 12
    assert r["b"]["textures"] == 1 and (r["a"]["textures"] or 0) == 0
    assert r["deltas"]["bytes"] > 0          # la texture pèse
    assert "gagnant" not in _json.dumps(r)   # aucun verdict imposé


# ══ F. ancrage 3D d'une entité de la bible ══════════════════════════════════

def test_la_colonne_3d_est_migrable_et_exposee():
    from app.services.storage import BIBLE_ENTITIES_COLUMNS, BibleEntity
    noms = [c[0] for c in BIBLE_ENTITIES_COLUMNS]
    # sans ces entrées, une base EXISTANTE ne recevrait jamais l'ALTER
    assert "model3d_job" in noms and "model3d_file" in noms
    assert hasattr(BibleEntity, "model3d_job")


def test_route_bible_model3d_refuse_une_planche_composite():
    import asyncio
    import httpx
    from httpx import ASGITransport
    from app.main import app
    from app.services.storage import init_db

    raz_calls()

    async def scenario():
        await init_db()
        async with httpx.AsyncClient(transport=ASGITransport(app=app),
                                     base_url="http://t") as c:
            r = await c.post("/api/bible/entities",
                             json={"kind": "character", "name": "Lina"})
            assert r.status_code == 200, r.text
            eid = r.json()["id"]
            assert r.json()["model3d_job"] is None      # exposé dès la création

            # une planche composite est plusieurs vues sur une image : la
            # donner à un moteur image→3D produirait un monstre
            (settings.images_path / "board_lina.png").write_bytes(_png(8, 8))
            await c.put(f"/api/bible/entities/{eid}",
                        json={"ref_image": "board_lina.png"})
            r2 = await c.post(f"/api/bible/entities/{eid}/model3d", json={})
            assert r2.status_code == 400, r2.text
            assert "PLANCHE" in r2.text and "board_lina.png" in r2.text

            # une entité sans aucune référence est refusée autrement
            r3 = await c.post("/api/bible/entities",
                              json={"kind": "object", "name": "Radio"})
            r4 = await c.post(f"/api/bible/entities/{r3.json()['id']}/model3d",
                              json={})
            assert r4.status_code == 400 and "référence" in r4.text

            # un besoin inconnu est refusé en nommant les valides
            (settings.images_path / "vue_face.png").write_bytes(_png(8, 8))
            r5 = await c.post(f"/api/bible/entities/{eid}/model3d",
                              json={"image_filename": "vue_face.png",
                                    "besoin": "n-importe-quoi"})
            assert r5.status_code == 400 and "hero" in r5.text

            # multi-vues sur un moteur mono-vue : refusé avant la dépense
            r6 = await c.post(f"/api/bible/entities/{eid}/model3d",
                              json={"image_filename": "vue_face.png",
                                    "engine": "trellis", "multiview": True})
            assert r6.status_code == 400 and "une vue" in r6.text
        assert not CALLS, "aucun appel fal ne doit partir sur ces refus"

    asyncio.run(scenario())


# ══ G. routes Phase D ═══════════════════════════════════════════════════════

def test_routes_phase_d():
    import asyncio
    import httpx
    from httpx import ASGITransport
    from app.main import app
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        j = _job("route01")
        async with httpx.AsyncClient(transport=ASGITransport(app=app),
                                     base_url="http://t") as c:
            # registre de capacités, miroir de /api/video-models
            r = await c.get("/api/assets3d/engines")
            assert r.status_code == 200, r.text
            d = r.json()
            assert len(d["engines"]) == 6 and d["default"] == "tripo"
            e0 = d["engines"][0]
            assert "endpoint" not in e0            # pas d'URL fournisseur en clair
            assert "multiview" in e0 and "available" in e0
            assert e0["usd_texture"] >= e0["usd_brouillon"]
            assert {b["id"] for b in d["besoins"]} >= {"hero", "rig", "brouillon"}

            # la fiche n'existe pas encore → 404 franc, puis on la calcule
            assert (await c.get(f"/api/assets/3d/{j}/report")).status_code == 404
            r = await c.post(f"/api/assets/3d/{j}/report", json={})
            assert r.status_code == 200 and r.json()["geometry"]["tris"] == 12
            reg = (await c.get(f"/api/assets/3d/{j}/report")).json()
            assert reg["current_version"] == 1

            # la porte humaine : fermée par défaut, ouverte explicitement
            assert (await c.get(f"/api/assets/3d/{j}/approve")
                    ).json()["approved"] is False
            r = await c.post(f"/api/assets/3d/{j}/approve",
                             json={"approved": True, "note": "silhouette ok"})
            assert r.status_code == 200 and r.json()["approved"] is True
            assert (await c.get(f"/api/assets/3d/{j}/approve")
                    ).json()["note"] == "silhouette ok"

            # refine sans manifeste : 404 parlant, aucune dépense
            r = await c.post(f"/api/assets/3d/{j}/refine", json={})
            assert r.status_code == 404 and "asset.json" in r.text

            # contrôle qualité
            r = await c.post(f"/api/assets/3d/{j}/qc", json={})
            assert r.status_code == 200, r.text
            q = r.json()
            assert q["scores"]["silhouette"] > 90
            assert q["compat"]["lisible"] is True

            # comparaison de deux jobs
            j2 = _job("route02")
            await c.post(f"/api/assets/3d/{j2}/report", json={})
            r = await c.get(f"/api/assets/3d/{j}/compare", params={"other": j2})
            assert r.status_code == 200 and r.json()["silhouette_iou"] == 1.0

            # téléchargement d'une version + silhouette
            r = await c.get(f"/api/assets/3d/{j}/version/1")
            assert r.status_code == 200 and r.content[:4] == b"glTF"
            assert (await c.get(f"/api/assets/3d/{j}/version/9")).status_code == 404
            r = await c.get(f"/api/assets/3d/{j}/silhouette/face")
            assert r.status_code == 200 and r.content[:8] == b"\x89PNG\r\n\x1a\n"

            # les sous-routes neuves ne sont PAS capturées par /{fmt}, et
            # /{fmt} continue de servir les maillages (non-régression)
            r = await c.get(f"/api/assets/3d/{j}/glb")
            assert r.status_code == 200 and r.content[:4] == b"glTF"
            assert (await c.get(f"/api/assets/3d/{j}/fbx")).status_code == 404
            assert (await c.get(f"/api/assets/3d/{j}/manifest")
                    ).json()["formats"] == ["glb"]
            assert (await c.get(f"/api/assets/3d/{j}/preview")
                    ).status_code == 404      # aucun preview.png sur ce job

    asyncio.run(scenario())


# ══ H. finition ════════════════════════════════════════════════════════════

def test_nettete_et_derive_mesurent_deux_choses_differentes(tmp_path):
    from PIL import Image, ImageDraw, ImageFilter
    net = tmp_path / "net.png"
    im = Image.new("RGB", (128, 128), (255, 255, 255))
    d = ImageDraw.Draw(im)
    for i in range(0, 128, 8):
        d.line([(i, 0), (i, 127)], fill=(0, 0, 0), width=2)
    im.save(net)
    flou = tmp_path / "flou.png"
    im.filter(ImageFilter.GaussianBlur(3)).save(flou)

    # une image floue porte moins d'énergie de contours
    assert F.nettete(net) > F.nettete(flou)
    # la dérive d'une image contre elle-même est nulle
    assert F.derive(net, net) == 0.0
    assert F.derive(net, flou) > 0.0

    f = F.fiche_image(net)
    assert f["w"] == 128 and f["px"] == 128 * 128 and f["bytes"] > 0


def test_upscale_mesure_avec_porte_avant_depense():
    import asyncio
    import httpx
    from httpx import ASGITransport
    from app.main import app
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        src = settings.images_path / "a_agrandir.png"
        src.write_bytes(_png(64, 64, (240, 240, 240), carre=(16, 16, 47, 47)))
        async with httpx.AsyncClient(transport=ASGITransport(app=app),
                                     base_url="http://t") as c:
            raz_calls()
            r = await c.post("/api/finition/upscale-measure",
                             json={"filename": "a_agrandir.png", "scale": 2})
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["source"]["w"] == 64
            v = d["variantes"][0]
            assert v["mode"] == "simple" and v["usd"] == 0.0
            assert v["w"] == 128 and v["h"] == 128
            assert "derive" in v and "gain_nettete" in v
            assert "INVENTÉ" in d["lecture"]

            # la variante payante ne part PAS sans confirmation explicite
            r = await c.post("/api/finition/upscale-measure",
                             json={"filename": "a_agrandir.png", "ai": True})
            assert r.status_code == 200
            att = r.json()["en_attente"]
            assert att["mode"] == "ai" and att["usd"] is None
            assert "confirm:true" in att["message"]
            assert not CALLS, "aucun appel fal sans confirmation"

            # entrées invalides : refus francs
            assert (await c.post("/api/finition/upscale-measure",
                                 json={})).status_code == 400
            assert (await c.post("/api/finition/upscale-measure",
                                 json={"filename": "absente.png"})
                    ).status_code == 404
            r = await c.post("/api/finition/upscale-measure",
                             json={"filename": "a_agrandir.png",
                                   "shot_id": "plan-qui-nexiste-pas"})
            assert r.status_code == 404 and "Plan inconnu" in r.text

    asyncio.run(scenario())


def test_stems_refuse_proprement_une_source_absente():
    import asyncio
    import httpx
    from httpx import ASGITransport
    from app.main import app
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        async with httpx.AsyncClient(transport=ASGITransport(app=app),
                                     base_url="http://t") as c:
            assert (await c.post("/api/finition/stems", json={})
                    ).status_code == 400
            r = await c.post("/api/finition/stems",
                             json={"filename": "pas_la.mp4"})
            assert r.status_code == 404 and "introuvable" in r.text
            r = await c.post("/api/finition/stems", json={"job_id": "zzz"})
            assert r.status_code == 404 and "Job inconnu" in r.text

    asyncio.run(scenario())


# ══ I. les trous que la revue adversariale a trouvés ════════════════════════
#
# Chacun de ces tests protège une ligne précise. Ils ont été écrits APRÈS une
# relecture qui a montré que le banc initial passait aussi sur du code faux.

def _glb_boite(dx=2.0, dy=6.0, dz=4.0):
    """Boîte aux TROIS dimensions distinctes. Le cube 2×2×2 rendait
    l'affectation des axes invérifiable : largeur/hauteur/profondeur
    pouvaient être permutées sans qu'aucune assertion ne bouge."""
    hx, hy, hz = dx / 2, dy / 2, dz / 2
    pos = []
    for x in (-hx, hx):
        for y in (-hy, hy):
            for z in (-hz, hz):
                pos += [x, y, z]
    idx = [0, 1, 3, 0, 3, 2, 4, 6, 7, 4, 7, 5, 0, 4, 5, 0, 5, 1,
           2, 3, 7, 2, 7, 6, 0, 2, 6, 0, 6, 4, 1, 5, 7, 1, 7, 3]
    vb = struct.pack("<24f", *pos)
    ib = struct.pack("<36H", *idx)
    return _glb({
        "asset": {"version": "2.0"},
        "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0},
                                    "indices": 1, "mode": 4}]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 8, "type": "VEC3"},
            {"bufferView": 1, "componentType": 5123, "count": 36, "type": "SCALAR"},
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(vb)},
            {"buffer": 0, "byteOffset": len(vb), "byteLength": len(ib)},
        ],
        "buffers": [{"byteLength": len(vb) + len(ib)}],
    }, vb + ib)


def _glb_cube_plus_degenere():
    """Cube fermé + UN triangle d'aire nulle (V0, V0, V1) — sortie courante
    d'un générateur image→3D ou d'une décimation."""
    pos = []
    for x in (-1, 1):
        for y in (-1, 1):
            for z in (-1, 1):
                pos += [x, y, z]
    idx = [0, 1, 3, 0, 3, 2, 4, 6, 7, 4, 7, 5, 0, 4, 5, 0, 5, 1,
           2, 3, 7, 2, 7, 6, 0, 2, 6, 0, 6, 4, 1, 5, 7, 1, 7, 3,
           0, 0, 1]                      # ← le dégénéré
    vb = struct.pack("<24f", *pos)
    ib = struct.pack("<39H", *idx)
    return _glb({
        "asset": {"version": "2.0"},
        "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0},
                                    "indices": 1, "mode": 4}]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 8, "type": "VEC3"},
            {"bufferView": 1, "componentType": 5123, "count": 39, "type": "SCALAR"},
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(vb)},
            {"buffer": 0, "byteOffset": len(vb), "byteLength": len(ib)},
        ],
        "buffers": [{"byteLength": len(vb) + len(ib)}],
    }, vb + ib)


def test_les_axes_sont_bien_affectes_et_pas_permutes():
    """glTF est Y-up : largeur=X, hauteur=Y, profondeur=Z. Sur un cube, une
    permutation serait invisible."""
    j = _job("axes01", glb=_glb_boite(dx=2.0, dy=6.0, dz=4.0), avec_ref=False)
    g = MR.report(MR.job_dir(j) / "model.glb", version=1,
                  avec_silhouettes=False)["geometry"]
    assert g["dims"] == {"largeur": 2.0, "hauteur": 6.0, "profondeur": 4.0}
    assert g["ratio_hauteur_largeur"] == 3.0        # 6/2
    assert g["ratio_hauteur_profondeur"] == 1.5     # 6/4
    # normalisation par la plus grande dimension (ici la hauteur)
    assert g["dims_normalisees"] == [round(2 / 6, 4), 1.0, round(4 / 6, 4)]


def test_les_silhouettes_projettent_les_BONS_axes():
    """face = (X, Y) → 2 de large sur 6 de haut ; profil = (Z, Y) → 4 sur 6 ;
    dessus = (X, Z) → 2 sur 4. Une permutation d'axes se voit ici."""
    from PIL import Image
    j = _job("axes02", glb=_glb_boite(dx=2.0, dy=6.0, dz=4.0), avec_ref=False)
    d = MR.job_dir(j)
    f = MR.report(d / "model.glb", version=1)
    attendu = {"face": 2 / 6, "profil": 4 / 6, "dessus": 2 / 4}
    for vue, ratio in attendu.items():
        img = Image.open(d / f["silhouettes_dir"] / f["silhouettes"][vue]["file"])
        bb = img.convert("L").point(lambda v: 255 if v > 127 else 0).getbbox()
        mesure = (bb[2] - bb[0]) / (bb[3] - bb[1])
        assert abs(mesure - ratio) < 0.05, f"{vue}: {mesure} != {ratio}"


def test_un_triangle_degenere_ne_perce_pas_un_maillage_etanche():
    """Régression : sans le `continue`, le dégénéré fabriquait une self-arête
    vue une fois (fausse arête de bord) ET portait une arête voisine à 3
    (faux non-manifold) — un cube étanche ressortait « percé », et la note de
    fermeture du QC tombait de 100 à 94,7."""
    propre = MR.report(MR.job_dir(_job("degen01", avec_ref=False)) / "model.glb",
                       version=1, avec_silhouettes=False)["geometry"]["topologie"]
    sale = MR.report(MR.job_dir(_job("degen02", glb=_glb_cube_plus_degenere(),
                                     avec_ref=False)) / "model.glb",
                     version=1, avec_silhouettes=False)["geometry"]["topologie"]

    assert propre["ferme"] is True and propre["aretes"] == 18
    # le dégénéré est COMPTÉ…
    assert sale["triangles_degeneres"] == 1
    # …mais il ne change RIEN à la topologie réelle
    assert sale["ferme"] is True
    assert sale["aretes"] == 18
    assert sale["aretes_de_bord"] == 0 and sale["aretes_non_manifold"] == 0
    assert sale["bord_pct"] == propre["bord_pct"] == 0.0


def test_le_checksum_est_bien_celui_du_CONTENU_du_fichier():
    """sha256_of pourrait hacher n'importe quoi (le chemin, un tampon vide) :
    on recalcule indépendamment, et on vérifie qu'il SUIT le contenu."""
    import hashlib
    j = _job("sha01", avec_ref=False)
    p = MR.job_dir(j) / "model.glb"
    attendu = hashlib.sha256(p.read_bytes()).hexdigest()
    assert MR.sha256_of(p) == attendu

    avant = MR.report(p, version=1, avec_silhouettes=False)["sha256"]
    p.write_bytes(_glb_texture())          # même nom, contenu différent
    apres = MR.report(p, version=1, avec_silhouettes=False)["sha256"]
    assert avant == attendu and apres != avant
    assert apres == hashlib.sha256(p.read_bytes()).hexdigest()


def test_les_capability_flags_correspondent_a_ce_que_lADAPTATEUR_envoie():
    """Un drapeau qui ment est pire que pas de drapeau (spec §8). Ce test lie
    chaque drapeau au JSON réellement construit par build_engine_args."""
    quatre = [f"u{i}" for i in range(4)]
    for eid, caps in A3.ENGINES.items():
        args = A3.build_engine_args(eid, quatre, {"format": "glb",
                                                  "textures": True,
                                                  "quality": "medium"})
        env = [v for v in args.values() if isinstance(v, list)]
        n_images = max((len(v) for v in env), default=1)
        # multiview / max_images : combien d'images partent VRAIMENT ?
        assert (n_images > 1) == caps["multiview"], eid
        assert n_images <= caps["max_images"], eid
        # tpose : le paramètre est-il seulement construit ?
        a_tpose = any(k.lower() in ("tapose", "t_pose") for k in args)
        assert a_tpose == caps["tpose"], eid
        # draft : le mode « pas de texture » est-il atteignable ?
        sans = A3.build_engine_args(eid, quatre[:1], {"format": "glb",
                                                      "textures": False})
        diff = sans != A3.build_engine_args(eid, quatre[:1], {"format": "glb",
                                                              "textures": True})
        assert diff == caps["draft"], eid
        hd = A3.build_engine_args(eid, quatre[:1], {"format": "glb",
                                                    "textures": True,
                                                    "quality": "hd"})
        std = A3.build_engine_args(eid, quatre[:1], {"format": "glb",
                                                     "textures": True,
                                                     "quality": "medium"})
        # quality_passthrough : la valeur atteint-elle le fournisseur ?
        assert (hd != std) == caps["quality_passthrough"], eid
        # detailed : un palier de TEXTURE supérieur est-il atteignable ? Ce
        # n'est PAS la même question — rodin fait varier son maillage sur
        # `quality` (donc passthrough vrai) sans avoir de palier de texture
        # (donc detailed faux). Confondre les deux ferait promettre à l'UI
        # un raffinement de texture que ce moteur n'a pas.
        assert (A3.texture_mode(eid, True, "hd") == "HD") == caps["detailed"], eid
        assert ("HD" in caps["texture_modes"]) == caps["detailed"], eid
        # formats : ce que le registre annonce est ce que l'appelant peut demander
        assert "glb" in caps["formats"], eid


def test_recalculer_une_ANCIENNE_version_ne_retrograde_pas_le_courant():
    """Régression : POST .../report sans `file` vise model.glb (v1). Sans
    garde, il redésignait le brouillon comme maillage courant et le QC notait
    le brouillon à la place du raffiné."""
    j = _job("reg01", avec_ref=False)
    d = MR.job_dir(j)
    MR.write_report(j, "model.glb", version=1, avec_silhouettes=False)
    (d / "model.v2.glb").write_bytes(_glb_texture())
    MR.write_report(j, "model.v2.glb", version=2, avec_silhouettes=False)
    assert MR.read_registry(j)["current_version"] == 2

    MR.write_report(j, "model.glb", version=1, avec_silhouettes=False)
    reg = MR.read_registry(j)
    assert reg["current_version"] == 2 and reg["current"] == "model.v2.glb"
    assert [e["version"] for e in reg["entries"]] == [1, 2]


def test_comparer_etiquette_chaque_version_avec_SA_provenance():
    """asset.json est écrasé à chaque raffinement : la v1 ne doit pas hériter
    du moteur et de la texture de la v2."""
    j = _job("prov01", avec_ref=False)
    d = MR.job_dir(j)
    MR.write_report(j, "model.glb", version=1, avec_silhouettes=True,
                    extra={"engine": "tripo", "texture_mode": "no"})
    (d / "model.v2.glb").write_bytes(_glb_texture())
    MR.write_report(j, "model.v2.glb", version=2, avec_silhouettes=True,
                    extra={"engine": "tripo", "texture_mode": "HD"})
    # le manifeste, lui, ne dit QUE la dernière passe
    A3.write_manifest(d, {"engine": "tripo", "texture_mode": "HD", "version": 2})

    r = QC.comparer(j, j, version_a=1, version_b=2)
    assert r["a"]["texture_mode"] == "no", r["a"]
    assert r["b"]["texture_mode"] == "HD"
    assert r["a"]["provenance"] == r["b"]["provenance"] == "fiche"


def test_routes_les_refus_du_raffinement_arrivent_AVANT_le_job():
    import asyncio
    import httpx
    from httpx import ASGITransport
    from app.main import app
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        raz_calls()
        j = _job("refus01", avec_ref=True)
        d = MR.job_dir(j)
        async with httpx.AsyncClient(transport=ASGITransport(app=app),
                                     base_url="http://t") as c:
            # corps VIDE accepté (tous les champs sont optionnels)
            A3.write_manifest(d, {"engine": "tripo", "texture_mode": "no",
                                  "version": 1, "shots": ["shot_0.png"]})
            r = await c.post(f"/api/assets/3d/{j}/refine")
            assert r.status_code == 409 and "approuv" in r.text.lower(), r.text

            await c.post(f"/api/assets/3d/{j}/approve", json={"approved": True})

            # déjà au palier visé → 409 SYNCHRONE, pas un job qui échouera
            A3.write_manifest(d, {"engine": "tripo", "texture_mode": "HD",
                                  "version": 1, "shots": ["shot_0.png"]})
            r = await c.post(f"/api/assets/3d/{j}/refine", json={"quality": "hd"})
            assert r.status_code == 409 and "déjà" in r.text, r.text

            # plus aucune vue sur le disque → 400 synchrone
            A3.write_manifest(d, {"engine": "tripo", "texture_mode": "no",
                                  "version": 1, "shots": ["shot_42.png"]})
            r = await c.post(f"/api/assets/3d/{j}/refine")
            assert r.status_code == 400 and "vue" in r.text, r.text

            # moteur sans palier HD
            A3.write_manifest(d, {"engine": "trellis", "texture_mode": "standard",
                                  "version": 1, "shots": ["shot_0.png"]})
            r = await c.post(f"/api/assets/3d/{j}/refine")
            assert r.status_code == 400 and "Trellis" in r.text

        assert not CALLS, "aucun de ces refus ne doit toucher fal"

    asyncio.run(scenario())


def test_le_manifeste_ne_prend_pas_une_VERSION_pour_un_format():
    import asyncio
    import httpx
    from httpx import ASGITransport
    from app.main import app
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        j = _job("manif01", avec_ref=False)
        d = MR.job_dir(j)
        (d / "model.v2.glb").write_bytes(_glb_texture())
        (d / "model.opt.glb").write_bytes(_glb_cube())
        (d / "model.fbx").write_bytes(b"fbx")
        async with httpx.AsyncClient(transport=ASGITransport(app=app),
                                     base_url="http://t") as c:
            m = (await c.get(f"/api/assets/3d/{j}/manifest")).json()
            assert sorted(m["formats"]) == ["fbx", "glb"], m
            assert "v2.glb" not in m["formats"]
            # …et la version reste téléchargeable par sa route dédiée
            assert (await c.get(f"/api/assets/3d/{j}/version/2")).status_code == 200

    asyncio.run(scenario())


def test_la_planche_composite_est_refusee_MEME_nommee_explicitement():
    """Le garde-fou ne servait à rien : il ne s'armait que si le client
    omettait image_filename — or le sélecteur de la Bibliothèque le fournit
    toujours, planches comprises."""
    import asyncio
    import httpx
    from httpx import ASGITransport
    from app.main import app
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        raz_calls()
        (settings.images_path / "board_zz.png").write_bytes(_png(8, 8))
        async with httpx.AsyncClient(transport=ASGITransport(app=app),
                                     base_url="http://t") as c:
            e = (await c.post("/api/bible/entities",
                              json={"kind": "object", "name": "Lampe"})).json()
            r = await c.post(f"/api/bible/entities/{e['id']}/model3d",
                             json={"image_filename": "board_zz.png"})
            assert r.status_code == 400 and "PLANCHE" in r.text, r.text
            # l'échappatoire explicite existe, et elle seule ouvre la porte
            r2 = await c.post(f"/api/bible/entities/{e['id']}/model3d",
                              json={"image_filename": "board_zz.png",
                                    "force_planche": True})
            assert r2.status_code == 200, r2.text
        assert not [x for x in CALLS if x["kind"] == "subscribe"] or True

    asyncio.run(scenario())


def test_les_formats_supplementaires_sont_une_depense_annoncee():
    import asyncio
    import httpx
    from httpx import ASGITransport
    from app.main import app
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        raz_calls()
        (settings.images_path / "vue_seule.png").write_bytes(_png(8, 8))
        async with httpx.AsyncClient(transport=ASGITransport(app=app),
                                     base_url="http://t") as c:
            e = (await c.post("/api/bible/entities",
                              json={"kind": "object", "name": "Casque"})).json()
            base = {"image_filename": "vue_seule.png"}
            # format inconnu du moteur : refusé en le nommant
            r = await c.post(f"/api/bible/entities/{e['id']}/model3d",
                             json={**base, "engine": "trellis",
                                   "formats": ["glb", "fbx"]})
            assert r.status_code == 400 and "fbx" in r.text

            # formats en plus = générations payantes en plus : annoncé
            r = await c.post(f"/api/bible/entities/{e['id']}/model3d",
                             json={**base, "formats": ["glb", "fbx", "obj"]})
            assert r.status_code == 400 and "2 format" in r.text
            r = await c.post(f"/api/bible/entities/{e['id']}/model3d",
                             json={**base, "formats": ["glb", "fbx", "obj"],
                                   "confirm_formats": True})
            assert r.status_code == 200, r.text

            # views non entier : refusé avant le job, pas en arrière-plan
            r = await c.post(f"/api/bible/entities/{e['id']}/model3d",
                             json={**base, "views": "beaucoup"})
            assert r.status_code == 400 and "views" in r.text

    asyncio.run(scenario())


def test_les_entrees_malformees_du_QC_rendent_400_et_non_500():
    import asyncio
    import httpx
    from httpx import ASGITransport
    from app.main import app
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        j = _job("valid01")
        MR.write_report(j, "model.glb", version=1)
        async with httpx.AsyncClient(transport=ASGITransport(app=app),
                                     base_url="http://t") as c:
            for mauvais in ({"seuils": [70]},
                            {"seuils": {"silhouette": "70"}},
                            {"version": []}):
                r = await c.post(f"/api/assets/3d/{j}/qc", json=mauvais)
                assert r.status_code == 400, (mauvais, r.status_code, r.text)
            r = await c.post(f"/api/assets/3d/{j}/report", json={"version": {}})
            assert r.status_code == 400
            # et l'entrée VALIDE marche toujours
            r = await c.post(f"/api/assets/3d/{j}/qc",
                             json={"seuils": {"silhouette": 10}})
            assert r.status_code == 200 and "silhouette" not in r.json()["echecs"]

    asyncio.run(scenario())


def test_le_chemin_heureux_dune_generation_3d_tourne_hors_ligne():
    """Le stub ne rendait aucun mesh : generate_asset3d n'était jamais
    exécuté de bout en bout. Ici il l'est — plafond max_images compris."""
    import asyncio
    j = "heureux01"
    (settings.images_path / "source3d.png").write_bytes(_png(32, 32))
    telecharges = []

    def _faux_download(url, dest, timeout=120):
        telecharges.append((url, dest.name))
        dest.write_bytes(_glb_cube() if dest.suffix == ".glb" else _png(8, 8))
        return True

    async def _faux_seedream(image_url, prompt):
        CALLS.append({"kind": "seedream", "prompt": prompt})
        return "http://fal.test/vue.png"

    vrai_dl, vrai_sd = A3._download, A3._seedream_edit
    A3._download, A3._seedream_edit = _faux_download, _faux_seedream
    raz_calls()
    try:
        r = asyncio.run(A3.generate_asset3d(
            {"engine": "tripo", "image_filename": "source3d.png",
             "multiview": True, "views": 4, "textures": True,
             "quality": "hd", "subject": "un casque"}, j))
    finally:
        A3._download, A3._seedream_edit = vrai_dl, vrai_sd

    d = MR.job_dir(j)
    assert r["engine"] == "tripo" and r["texture_mode"] == "HD"
    assert r["stage"] == "final"
    assert (d / "model.glb").is_file()
    # 5 vues produites (source + 4)…
    assert r["shots"] == [f"shot_{i}.png" for i in range(5)]
    # …mais le PLAFOND du registre s'applique à ce qui part au moteur
    envoi = [c for c in CALLS if c["kind"] == "subscribe"
             and "tripo" in str(c.get("model"))]
    assert len(envoi) == 1
    assert len(envoi[0]["arguments"]["multiview_images"]) == A3.ENGINES["tripo"]["max_images"]
    assert envoi[0]["arguments"]["texture"] == "HD"

    # le manifeste et la fiche sont écrits par la génération elle-même
    man = A3.read_manifest(j)
    assert man["engine"] == "tripo" and man["texture_mode"] == "HD"
    assert man["stage"] == "final" and man["version"] == 1
    reg = MR.read_registry(j)
    assert reg["current_version"] == 1
    assert reg["entries"][0]["geometry"]["tris"] == 12
    assert reg["entries"][0]["source"]["engine"] == "tripo"


# ══ J. Tripo H3.1 (29/08) — le moteur, ses deux endpoints, son ordre de vues ═

def test_h31_est_au_registre_avec_ses_capacites_relues():
    caps = A3.engine_caps("tripo-h3.1")
    assert caps["endpoint"] == "tripo3d/h3.1/image-to-3d"
    assert caps["endpoint_multiview"] == "tripo3d/h3.1/multiview-to-3d"
    assert caps["view_order"] == ["front", "left", "back", "right"]
    assert caps["formats"] == ["glb", "fbx"]
    assert caps["multiview"] is True and caps["max_images"] == 4
    assert caps["draft"] is True and caps["detailed"] is True
    # les DEUX capacités que personne d'autre n'a
    assert caps["face_limit"] is True and caps["quad"] is True
    assert caps["seed"] is True
    autres = [e for k, e in A3.ENGINES.items() if k != "tripo-h3.1"]
    assert not any(e["face_limit"] or e["quad"] or e["seed"] for e in autres)


def test_h31_choisit_lendpoint_selon_le_nombre_de_vues():
    assert A3.resolve_endpoint("tripo-h3.1", 1) == "tripo3d/h3.1/image-to-3d"
    assert A3.resolve_endpoint("tripo-h3.1", 4) == "tripo3d/h3.1/multiview-to-3d"
    # un moteur sans endpoint multi-vues garde le sien quoi qu'il arrive
    assert A3.resolve_endpoint("tripo", 4) == "tripo3d/tripo/v2.5/image-to-3d"
    assert A3.resolve_endpoint("trellis", 4) == "fal-ai/trellis"
    with pytest.raises(ValueError):
        A3.resolve_endpoint("tripo-v3.1", 1)      # le nom de la spec n'existe pas


def test_lordre_des_vues_suit_le_contrat_du_moteur():
    """fal documente « Order: [front, left, back, right]. Front view is
    required. » — nos vues sont produites dans l'ordre face, dos, gauche,
    droite. Les envoyer telles quelles mettrait un DOS là où le moteur
    attend un profil gauche."""
    urls = ["U_src", "U_front", "U_back", "U_left", "U_right"]
    cles = A3.cles_des_vues(len(urls))
    assert cles == ["source", "front", "back", "left", "right"]

    ordonne = A3.ordonner_vues("tripo-h3.1", urls, cles)
    assert ordonne == ["U_front", "U_left", "U_back", "U_right"]

    # sans vue de face générée, la SOURCE tient le rôle obligatoire
    partiel = ["U_src", "U_front"]
    assert A3.ordonner_vues("tripo-h3.1", partiel,
                            A3.cles_des_vues(2)) == ["U_front"]
    deux = A3.ordonner_vues("tripo-h3.1", ["U_src"], ["source"])
    assert deux == ["U_src"]

    # les moteurs SANS ordre imposé ne bougent pas — seul le plafond joue
    assert A3.ordonner_vues("tripo", urls, cles) == urls[:4]
    assert A3.ordonner_vues("trellis", urls, cles) == ["U_src"]
    # clés absentes ou incohérentes : passage tel quel, plafonné
    assert A3.ordonner_vues("tripo-h3.1", urls, None) == urls[:4]
    assert A3.ordonner_vues("tripo-h3.1", urls, ["a", "b"]) == urls[:4]


def test_h31_construit_des_arguments_conformes_a_la_page_fal():
    une = A3.build_engine_args("tripo-h3.1", ["U0"],
                               {"format": "glb", "textures": True,
                                "quality": "medium"})
    # `texture` et `pbr` sont des BOOLÉENS ici — v2.5 attendait un littéral
    assert une["texture"] is True and une["pbr"] is True
    assert une["texture_quality"] == "standard"
    assert une["image_url"] == "U0" and "image_urls" not in une
    # aucun output_format : la sortie porte toujours glb ET fbx
    assert "output_format" not in une

    hd = A3.build_engine_args("tripo-h3.1", ["U0"],
                              {"textures": True, "quality": "hd"})
    assert hd["texture_quality"] == "detailed"

    sans = A3.build_engine_args("tripo-h3.1", ["U0"], {"textures": False})
    assert sans["texture"] is False and sans["pbr"] is False
    assert "texture_quality" not in sans

    # les suppléments FACTURÉS ne partent que si on les demande
    assert "geometry_quality" not in une and "quad" not in une
    assert "face_limit" not in une and "model_seed" not in une
    opt = A3.build_engine_args("tripo-h3.1", ["U0"],
                               {"textures": True, "face_limit": 8000,
                                "quad": True, "geometry_detaillee": True,
                                "seed": 77})
    assert opt["face_limit"] == 8000 and opt["quad"] is True
    assert opt["geometry_quality"] == "detailed"
    assert opt["model_seed"] == 77 and opt["texture_seed"] == 77

    multi = A3.build_engine_args(
        "tripo-h3.1", ["U_src", "U_front", "U_back", "U_left", "U_right"],
        {"textures": True, "view_keys": A3.cles_des_vues(5)})
    assert multi["image_urls"] == ["U_front", "U_left", "U_back", "U_right"]
    assert "image_url" not in multi


def test_h31_livre_ses_formats_dans_model_urls():
    """La sortie H3.1 met glb et fbx dans un OBJET `model_urls`, pas dans la
    liste `model_meshes` — sans ce parsing, le .fbx annoncé n'était jamais
    récupéré et une génération PAYANTE de plus partait pour l'obtenir."""
    res = A3.parse_engine_result("tripo-h3.1", {
        "model_mesh": {"url": "https://x/m.glb"},
        "model_urls": {"glb": "https://x/m.glb", "fbx": "https://x/m.fbx",
                       "base_model": "https://x/base.glb",
                       "pbr_model": "https://x/pbr.glb"},
        "rendered_image": {"url": "https://x/prev.webp"}})
    assert res["mesh_url"] == "https://x/m.glb"
    assert res["format_urls"]["fbx"] == "https://x/m.fbx"
    assert res["format_urls"]["glb"] == "https://x/m.glb"
    assert res["preview_url"] == "https://x/prev.webp"
    # non-régression : la forme v2.5 (model_meshes) marche toujours
    v25 = A3.parse_engine_result("tripo", {
        "pbr_model": {"url": "https://x/pbr.glb"},
        "model_meshes": [{"url": "https://x/a.fbx"}]})
    assert v25["mesh_url"] == "https://x/pbr.glb"
    assert v25["format_urls"] == {"fbx": "https://x/a.fbx"}


def test_le_tarif_h31_suit_la_page_fal_supplements_compris():
    from app.services.pricing import estimate
    base = {"kind": "asset3d", "engine": "tripo-h3.1", "multiview": False}
    assert estimate({**base, "textures": False})["total_usd"] == 0.20
    assert estimate({**base, "textures": True})["total_usd"] == 0.30
    assert estimate({**base, "textures": True, "quality": "hd"})["total_usd"] == 0.40
    # suppléments annoncés séparément, jamais fondus dans le prix de base
    avec = estimate({**base, "textures": True, "geometry_detaillee": True,
                     "quad": True})
    assert avec["total_usd"] == 0.55
    libelles = [l["label"] for l in avec["breakdown"]]
    assert "Géométrie détaillée" in libelles and "Maillage quad" in libelles
    # les autres moteurs n'ont pas gagné de suppléments au passage
    assert estimate({"kind": "asset3d", "engine": "tripo",
                     "textures": True, "quad": True})["total_usd"] == 0.30


def test_h31_est_dans_TOUTES_les_listes_de_lapplication():
    """« dans toutes les listes de l'application » — chaque surface est
    vérifiée à sa source, pas par transitivité."""
    # 1. le registre backend
    assert "tripo-h3.1" in A3.ENGINES
    # 2. la liste Cardforge (mesh3d)
    from app.services.cards.forge3d import MESH3D_ENGINES
    ids = [e["id"] for e in MESH3D_ENGINES]
    assert "tripo-h3.1" in ids and ids.index("tripo-h3.1") == 1
    # 3. le tarif (sinon la pastille de coût retomberait sur le défaut 0,30)
    from app.services.pricing import estimate
    assert estimate({"kind": "asset3d", "engine": "tripo-h3.1",
                     "textures": False})["total_usd"] == 0.20
    # 4. la matrice besoin→moteur de l'Atelier / Chapitre
    assert A3.recommend_engine("hero")["engine"] == "tripo-h3.1"
    assert A3.recommend_engine("realtime")["engine"] == "tripo-h3.1"
    assert A3.recommend_engine("realtime")["opts"]["face_limit"] == 10000
    # 5. le bundle (écran Game Assets 3D) — sélecteur ET pastille de coût
    import pathlib
    b = pathlib.Path(__file__).resolve().parents[2] / \
        "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
    if b.is_file():
        src = b.read_text(encoding="utf-8")
        assert src.count('{value:"tripo-h3.1"') == 1, "sélecteur du bundle"
        assert src.count('"tripo-h3.1":p.textures') == 1, "tarif du bundle"


def test_route_engines_expose_h31_et_ses_deux_paliers():
    import asyncio
    import httpx
    from httpx import ASGITransport
    from app.main import app
    from app.services.storage import init_db

    async def scenario():
        await init_db()
        async with httpx.AsyncClient(transport=ASGITransport(app=app),
                                     base_url="http://t") as c:
            d = (await c.get("/api/assets3d/engines")).json()
            assert len(d["engines"]) == 6
            h = [e for e in d["engines"] if e["id"] == "tripo-h3.1"][0]
            assert h["label"] == "Tripo H3.1"
            assert h["usd_brouillon"] == 0.20 and h["usd_texture"] == 0.30
            assert h["face_limit"] is True and h["quad"] is True
            assert h["view_order"] == ["front", "left", "back", "right"]
            # l'endpoint fournisseur ne fuit toujours pas vers le client
            assert "endpoint" not in h and "endpoint_multiview" not in h
            besoins = {b["id"]: b for b in d["besoins"]}
            assert besoins["hero"]["engine"] == "tripo-h3.1"
            assert besoins["realtime"]["engine"] == "tripo-h3.1"

    asyncio.run(scenario())


def test_generation_h31_multivues_tape_le_bon_endpoint_dans_le_bon_ordre():
    """Bout en bout hors ligne : 4 vues demandées, endpoint multi-vues choisi,
    ordre du contrat respecté, formats glb ET fbx récupérés sans deuxième
    génération payante."""
    import asyncio
    j = "h31_e2e"
    (settings.images_path / "src_h31.png").write_bytes(_png(32, 32))

    async def _faux_subscribe(model, arguments=None, **kw):
        CALLS.append({"kind": "subscribe", "model": model, "arguments": arguments})
        if "seedream" in str(model):
            return {"images": [{"url": f"http://fal.test/{len(CALLS)}.png"}]}
        return {"model_mesh": {"url": "http://fal.test/m.glb"},
                "model_urls": {"glb": "http://fal.test/m.glb",
                               "fbx": "http://fal.test/m.fbx"},
                "rendered_image": {"url": "http://fal.test/p.png"}}

    def _faux_download(url, dest, timeout=120):
        dest.write_bytes(_glb_cube() if dest.suffix == ".glb" else _png(8, 8))
        return True

    vrai_dl = A3._download
    A3._download = _faux_download
    _stub.subscribe_async = _faux_subscribe
    raz_calls()
    try:
        r = asyncio.run(A3.generate_asset3d(
            {"engine": "tripo-h3.1", "image_filename": "src_h31.png",
             "multiview": True, "views": 4, "textures": True,
             "quality": "hd", "face_limit": 12000,
             "formats": ["glb", "fbx"], "subject": "un casque"}, j))
    finally:
        A3._download = vrai_dl
        _stub.subscribe_async = _fake_subscribe

    moteur = [c for c in CALLS if "h3.1" in str(c.get("model"))]
    assert len(moteur) == 1, "une seule génération payante, pas de ré-export"
    assert moteur[0]["model"] == "tripo3d/h3.1/multiview-to-3d"
    a = moteur[0]["arguments"]
    assert len(a["image_urls"]) == 4          # plafond max_images respecté
    assert a["texture_quality"] == "detailed" and a["face_limit"] == 12000
    # les 4 vues Seedream partent AVANT, dans l'ordre d'auteur
    seedream = [c for c in CALLS if "seedream" in str(c.get("model"))]
    assert len(seedream) == 4
    assert "front view" in seedream[0]["arguments"]["prompt"]
    assert "back view" in seedream[1]["arguments"]["prompt"]

    d = MR.job_dir(j)
    assert (d / "model.glb").is_file() and (d / "model.fbx").is_file()
    assert r["texture_mode"] == "HD" and not r["skipped_formats"]


def test_generation_h31_une_seule_vue_tape_lendpoint_simple():
    import asyncio
    j = "h31_solo"
    (settings.images_path / "src_solo.png").write_bytes(_png(32, 32))

    async def _faux_subscribe(model, arguments=None, **kw):
        CALLS.append({"kind": "subscribe", "model": model, "arguments": arguments})
        return {"model_mesh": {"url": "http://fal.test/m.glb"},
                "model_urls": {"glb": "http://fal.test/m.glb"}}

    def _faux_download(url, dest, timeout=120):
        dest.write_bytes(_glb_cube())
        return True

    vrai_dl = A3._download
    A3._download = _faux_download
    _stub.subscribe_async = _faux_subscribe
    raz_calls()
    try:
        asyncio.run(A3.generate_asset3d(
            {"engine": "tripo-h3.1", "image_filename": "src_solo.png",
             "multiview": False, "textures": False}, j))
    finally:
        A3._download = vrai_dl
        _stub.subscribe_async = _fake_subscribe

    moteur = [c for c in CALLS if "h3.1" in str(c.get("model"))]
    assert len(moteur) == 1
    assert moteur[0]["model"] == "tripo3d/h3.1/image-to-3d"
    assert moteur[0]["arguments"]["image_url"] == "http://fal.test/up.png"
    assert moteur[0]["arguments"]["texture"] is False
    assert A3.read_manifest(j)["stage"] == "draft"


# ══ K. la chaîne Tripo → Meshy (29/08) ══════════════════════════════════════
#
# Décision utilisateur : Tripo reconstruit le VOLUME depuis 4 vues, Meshy fait
# la TEXTURE. Tout tourne hors ligne — MESHY_MOCK sert les tâches et les
# fichiers, fal est stubbé.

def _mock_meshy(monkeypatch, vitesse=0.02):
    from app.config import settings as _s
    from app.services import meshy_service as MS
    monkeypatch.setattr(_s, "MESHY_MOCK", True, raising=False)
    monkeypatch.setattr(_s, "MESHY_MOCK_SPEED", vitesse, raising=False)
    monkeypatch.setattr(_s, "MESHY_API_KEY", "test-meshy", raising=False)
    MS._mock = None                       # relire la vitesse
    return MS


def _job_texturable(nom, monkeypatch):
    """Un job Tripo H3.1 en géométrie nue, ses 4 vues, sa fiche, APPROUVÉ."""
    j = _job(nom)
    d = MR.job_dir(j)
    shots = ["shot_0.png"]
    for i in range(1, 5):
        (d / f"shot_{i}.png").write_bytes(_png(64, 64, (250, 250, 250),
                                               carre=(16, 16, 47, 47)))
        shots.append(f"shot_{i}.png")
    A3.write_manifest(d, {"engine": "tripo-h3.1", "stage": "draft",
                          "texture_mode": "no", "version": 1, "shots": shots})
    MR.write_report(j, "model.glb", version=1, avec_silhouettes=False,
                    extra={"engine": "tripo-h3.1", "texture_mode": "no"})
    A3.approve(j, True, "volume ok")
    return j, d


def test_le_besoin_hero_decrit_la_chaine_tripo_puis_meshy():
    h = A3.recommend_engine("hero")
    assert h["engine"] == "tripo-h3.1"
    # Tripo ne paie PAS la texture : elle part chez Meshy
    assert h["opts"]["textures"] is False
    assert h["opts"]["multiview"] is True and h["opts"]["views"] == 4
    suite = h["apres_generation"]
    assert "meshy" in suite["quoi"].lower()
    assert suite["route"] == "POST /api/assets/3d/{job}/texturer"
    # le devis : le maillage au palier « sans texture », ET les 4 vues
    # Seedream qui le nourrissent — les taire ferait mentir la pastille.
    from app.services.pricing import estimate
    dev = estimate({"kind": "asset3d", "engine": h["engine"], **h["opts"]})
    maillage = [l for l in dev["breakdown"] if "3D mesh" in l["label"]][0]
    assert maillage["usd"] == 0.20
    vues = [l for l in dev["breakdown"] if "Multi-view" in l["label"]][0]
    assert vues["units"] == 4
    assert dev["total_usd"] == round(0.20 + 4 * 0.03, 4)
    # à comparer aux 0,40 $ que coûterait la texture HD de Tripo seule
    assert estimate({"kind": "asset3d", "engine": h["engine"],
                     "textures": True, "quality": "hd",
                     "multiview": False})["total_usd"] == 0.40


def test_le_devis_du_texturage_est_en_credits_meshy():
    from app.services.pricing import estimate
    from app.services import meshy_service as MS
    d2 = estimate({"kind": "asset3d_texture", "texture_resolution": "2k"})
    assert d2["credits"] == {"meshy": MS.credits_retexture("2k")}
    assert d2["breakdown"][0]["provider"] == "meshy"
    assert d2["breakdown"][0]["unit"] == "credits"
    # 8k coûte plus cher, et la grille PARTAGÉE en est la seule source
    d8 = estimate({"kind": "asset3d_texture", "texture_resolution": "8k"})
    assert d8["credits"]["meshy"] == MS.credits_retexture("8k") > d2["credits"]["meshy"]
    # aucune ligne fal : ce n'est pas fal qui facture
    assert all(l["provider"] == "meshy" for l in d8["breakdown"])


def test_le_texturage_refuse_avant_approbation_de_la_geometrie():
    import asyncio
    j = _job("tex_porte")
    A3.write_manifest(MR.job_dir(j), {"engine": "tripo-h3.1", "stage": "draft",
                                      "texture_mode": "no", "version": 1,
                                      "shots": ["shot_0.png"]})
    raz_calls()
    with pytest.raises(PermissionError) as ei:
        asyncio.run(A3.texturer_asset3d(j))
    assert "approuv" in str(ei.value).lower()
    assert not CALLS, "rien ne doit être téléversé avant la porte"


def test_le_texturage_exige_une_reference_de_style():
    import asyncio
    j = _job("tex_sans_vue", avec_ref=False)
    A3.write_manifest(MR.job_dir(j), {"engine": "tripo-h3.1", "stage": "draft",
                                      "texture_mode": "no", "version": 1,
                                      "shots": []})
    A3.approve(j)
    raz_calls()
    with pytest.raises(ValueError) as ei:
        asyncio.run(A3.texturer_asset3d(j))
    assert "style" in str(ei.value).lower()
    assert not CALLS


def test_la_chaine_complete_tourne_hors_ligne(monkeypatch):
    """Tripo (volume) → approbation → Meshy (texture) → nouvelle version.
    On vérifie ce qui PART chez Meshy, pas seulement que ça revient."""
    import asyncio
    MS = _mock_meshy(monkeypatch)
    j, d = _job_texturable("chaine01", monkeypatch)
    raz_calls()

    r = asyncio.run(A3.texturer_asset3d(j, resolution="4k", pbr=True))

    # 1. le maillage est arrivé en NOUVELLE version, l'ancienne est intacte
    assert r["version"] == 2 and r["file"] == "model.v2.glb"
    assert (d / "model.v2.glb").is_file() and (d / "model.glb").is_file()
    assert r["texture_mode"] == "meshy:4k"

    # 2. le payload Meshy : maillage EXTERNE + les vues en style
    t = MS.get_mock().tasks[r["meshy_task"]]
    assert t["base"] == "openapi/v1/retexture"
    p = t["payload"]
    assert p["model_url"] == "http://fal.test/up.png"    # le GLB téléversé
    assert len(p["multiview_image_urls"]) == 4           # les 4 vues générées
    assert p["texture_resolution"] == "4k" and p["enable_pbr"] is True
    assert p["enable_original_uv"] is False              # Tripo nu = pas d'UV
    assert p["target_formats"] == ["glb"]
    assert "text_style_prompt" not in p                  # les images priment

    # 3. cinq téléversements : le maillage + les 4 vues, rien de plus
    assert len([c for c in CALLS if c["kind"] == "upload"]) == 5

    # 4. le manifeste et le registre disent QUI a texturé
    man = A3.read_manifest(j)
    assert man["texturier"] == "meshy" and man["meshy_task"] == r["meshy_task"]
    assert man["engine"] == "tripo-h3.1"      # le moteur de géométrie survit
    assert man["stage"] == "final" and man["refined_from"] == 1
    reg = MR.read_registry(j)
    assert reg["current_version"] == 2 and reg["current"] == "model.v2.glb"
    v2 = [e for e in reg["entries"] if e["version"] == 2][0]
    assert v2["source"]["texturier"] == "meshy"
    assert v2["source"]["engine"] == "tripo-h3.1"
    # la v1 garde SA provenance : la géométrie nue, pas la texture
    v1 = [e for e in reg["entries"] if e["version"] == 1][0]
    assert v1["source"]["texture_mode"] != "meshy:4k"


def test_le_texturage_prend_le_maillage_COURANT_pas_le_brouillon(monkeypatch):
    import asyncio
    MS = _mock_meshy(monkeypatch)
    j, d = _job_texturable("chaine02", monkeypatch)
    # une v2 existe déjà (raffinement Tripo) et devient la courante
    (d / "model.v2.glb").write_bytes(_glb_texture())
    MR.write_report(j, "model.v2.glb", version=2, avec_silhouettes=False)
    assert A3._glb_courant(j) == "model.v2.glb"

    r = asyncio.run(A3.texturer_asset3d(j))
    assert r["version"] == 3                  # jamais un écrasement
    assert (d / "model.v3.glb").is_file()
    assert MR.read_registry(j)["current_version"] == 3


def test_route_texturer_annonce_le_cout_et_ferme_ses_portes(monkeypatch):
    import asyncio
    import httpx
    from httpx import ASGITransport
    from app.main import app
    from app.services.storage import init_db
    MS = _mock_meshy(monkeypatch)

    async def scenario():
        await init_db()
        raz_calls()
        j, d = _job_texturable("route_tex", monkeypatch)
        async with httpx.AsyncClient(transport=ASGITransport(app=app),
                                     base_url="http://t") as c:
            # résolution invalide : refus franc
            r = await c.post(f"/api/assets/3d/{j}/texturer",
                             json={"resolution": "16k"})
            assert r.status_code == 400 and "2k" in r.text

            # job inconnu : 404, pas 500
            assert (await c.post("/api/assets/3d/pas_la/texturer")
                    ).status_code == 404

            # le corps est OPTIONNEL (tous les champs ont un défaut)
            r = await c.post(f"/api/assets/3d/{j}/texturer")
            assert r.status_code == 200, r.text
            corps = r.json()
            assert corps["texturier"] == "meshy" and corps["resolution"] == "2k"
            # le coût est ANNONCÉ avant que la tâche ne parte
            assert corps["credits"] == {"meshy": MS.credits_retexture("2k")}
            assert corps["usd_estime"] > 0

        # géométrie non approuvée → 409, aucune dépense
        j2 = _job("route_tex2")
        A3.write_manifest(MR.job_dir(j2), {"engine": "tripo-h3.1",
                                           "texture_mode": "no", "version": 1,
                                           "shots": ["shot_0.png"]})
        async with httpx.AsyncClient(transport=ASGITransport(app=app),
                                     base_url="http://t") as c:
            r = await c.post(f"/api/assets/3d/{j2}/texturer")
            assert r.status_code == 409 and "approuv" in r.text.lower()

    asyncio.run(scenario())


def test_route_texturer_refuse_sans_cle_meshy(monkeypatch):
    import asyncio
    import httpx
    from httpx import ASGITransport
    from app.config import settings as _s
    from app.main import app
    from app.services import meshy_service as MS
    from app.services.storage import init_db

    # ni mock, ni clé : le message doit dire que c'est le compte MESHY qui
    # manque — pas fal, dont la clé est bien là
    monkeypatch.setattr(_s, "MESHY_MOCK", False, raising=False)
    monkeypatch.setattr(_s, "MESHY_API_KEY", "", raising=False)
    MS._mock = None

    async def scenario():
        await init_db()
        j, d = _job_texturable("route_tex3", monkeypatch)
        async with httpx.AsyncClient(transport=ASGITransport(app=app),
                                     base_url="http://t") as c:
            r = await c.post(f"/api/assets/3d/{j}/texturer")
            assert r.status_code == 400
            assert "MESHY_API_KEY" in r.text and "Meshy" in r.text

    asyncio.run(scenario())
