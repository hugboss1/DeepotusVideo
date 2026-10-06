# -*- coding: utf-8 -*-
"""T104 (plan-moteurs-3d T1) — socle des moteurs 3D : tarifs des nouvelles opérations (rig, vues, conversion,
opérations locales), mock Meshy rigging aligné sur docs.meshy.ai (relu le 06/10/2026 : rigged_character_glb_url,
basic_animations), GLB riggé minimal relu par mesh_edit.rig_inventory.
Écart au plan, voulu : le devis du rig a UNE LIGNE PAR TÂCHE Meshy (remesh, rig, chaque action) — la garde des
plafonds écrit une dépense par ligne, et chaque ligne doit pouvoir être rapprochée du coût réel de SA tâche.
Run : python tests/test_moteurs3d_socle.py (depuis backend/)"""
import os, pathlib, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzm3s_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
os.environ["MESHY_MOCK"] = "1"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_le_devis_du_rig_dit_remesh_et_animations_une_ligne_par_tache():
    from app.services.pricing import estimate
    r = estimate({"kind": "asset3d_rig"})
    assert r["credits"] == {"meshy": 5.0} and len(r["breakdown"]) == 1, r
    assert abs(r["total_usd"] - 5 * 0.02) < 1e-9, r
    r2 = estimate({"kind": "asset3d_rig", "remesh_requis": True, "actions": [0, 4]})
    assert r2["credits"] == {"meshy": 16.0}, r2          # 5 + 5 + 2 × 3
    labels = [l["label"] for l in r2["breakdown"]]
    assert len(labels) == 4, labels                      # remesh, rig, action 0, action 4 : une ligne par tâche
    assert "300" in labels[0] and "rig" in labels[1].lower(), labels   # le remesh DIT pourquoi, et vient d'abord
    assert "Idle" in labels[2] and "Attack" in labels[3], labels       # chaque action est nommée
    r3 = estimate({"kind": "asset3d_rig", "actions": [999]})
    assert "999" in r3["breakdown"][1]["label"], r3                     # un id hors bibliothèque reste lisible


def test_les_operations_locales_coutent_zero_et_le_disent():
    from app.services.pricing import estimate
    for kind in ("asset3d_lod", "asset3d_textures", "asset3d_local"):
        r = estimate({"kind": kind})
        assert r["total_usd"] == 0.0 and r["breakdown"][0]["provider"] == "local", kind
    assert estimate({"kind": "asset3d_convert", "via": "local"})["total_usd"] == 0.0
    assert estimate({"kind": "asset3d_convert", "via": "meshy"})["credits"] == {"meshy": 1.0}
    v = estimate({"kind": "asset3d_views", "views": 4})
    assert abs(v["total_usd"] - 0.12) < 1e-9, v
    v2 = estimate({"kind": "asset3d_views", "views": 2, "rembg": 2})
    assert abs(v2["total_usd"] - (0.06 + 0.006)) < 1e-9, v2


def test_les_vues_du_flux_asset3d_lisent_le_tarif_edite():
    from app.services.pricing import estimate, DEFAULTS
    assert DEFAULTS["seedream_edit_usd"] == 0.03
    a = estimate({"kind": "asset3d", "engine": "tripo", "multiview": True, "views": 3})
    assert abs(a["total_usd"] - (0.30 + 3 * 0.03)) < 1e-9, a          # même total qu'avant le socle
    b = estimate({"kind": "asset3d", "engine": "tripo", "multiview": True, "views": 3},
                 dict(DEFAULTS, seedream_edit_usd=0.05))
    assert abs(b["total_usd"] - (0.30 + 3 * 0.05)) < 1e-9, b          # le tarif n'est plus figé en dur


def test_le_mock_rigging_porte_les_cles_documentees():
    from app.services import meshy_service as MS
    from app.config import settings
    MS._mock = None
    settings.MESHY_MOCK, settings.MESHY_MOCK_SPEED = True, 0.001
    mk = MS.get_mock()
    code, d = mk.create("openapi/v1/rigging", {"model_url": "http://x/m.glb", "height_meters": 1.7})
    assert code == 202, (code, d)
    time.sleep(0.05)
    code, t = mk.get(d["result"])
    res = t["result"]
    assert res["rigged_character_glb_url"].endswith("rig.glb"), res
    assert res["rigged_model_url"]                          # clé historique conservée (meshy.client.js)
    assert set(res["basic_animations"]) >= {"walking_glb_url", "running_glb_url",
                                            "walking_fbx_url", "running_armature_glb_url"}, res
    code, d2 = mk.create("openapi/v1/animations", {"rig_task_id": d["result"], "action_id": 4})
    time.sleep(0.05)
    code, t2 = mk.get(d2["result"])
    assert t2["result"]["animation_glb_url"].endswith(".glb"), t2


def test_le_glb_rigge_du_mock_a_un_squelette_et_un_clip():
    from app.services import meshy_service as MS, mesh_edit, print3d
    data = MS.tiny_rigged_glb()
    inv = mesh_edit.rig_inventory(data)
    assert inv["a_squelette"] and inv["nb_os"] == 1 and len(inv["clips"]) == 1, inv
    assert len(print3d.lire_glb_triangles(data)) == 1
    for nom in ("rig.glb", "anim_walking.glb", "anim_action_4.glb"):
        octets, media = MS.mock_file_bytes(nom)
        assert octets[:4] == b"glTF" and media == "model/gltf-binary", nom
        assert mesh_edit.rig_inventory(octets)["a_squelette"], nom
    assert not mesh_edit.rig_inventory(MS.mock_file_bytes("model.glb")[0])["a_squelette"]   # le reste ne change pas


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001 — on VEUT le nom du rouge
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (moteurs3d_socle)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
