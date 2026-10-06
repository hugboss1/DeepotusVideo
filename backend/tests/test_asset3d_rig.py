# -*- coding: utf-8 -*-
"""T104 (plan-moteurs-3d T2, P1) — rig et animations Meshy d'un job fal. Le banc ne sort jamais : upload fal stubbé,
Meshy en MESHY_MOCK, GLB fabriqués par gltf_builder, relus par mesh_edit.rig_inventory.
Service : devis lu sur le GLB courant, refus gratuits (non approuvé, sans texture), remesh au-delà de 300 000 faces,
version squelettée dans le registre, clips à côté. Routes : refus AVANT le job (404, 400 clé, 409 approbation,
400 texture, 409 double clic), garde des plafonds AVANT toute dépense (402), coût réel de CHAQUE tâche Meshy
rattaché à SA ligne de dépense, clips servis.
Run : python tests/test_asset3d_rig.py (depuis backend/)"""
import asyncio, json, os, pathlib, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzrig_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
os.environ["MESHY_MOCK"] = "1"; os.environ["MESHY_MOCK_SPEED"] = "0.005"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["ELEVENLABS_API_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loguru import logger                                         # noqa: E402
logger.remove()
from app.config import settings                                   # noqa: E402
from app.services import asset3d_service as A3, gltf_builder, mesh_edit, mesh_report  # noqa: E402
from app.services import asset3d_rig as RIG                       # noqa: E402
from app.services.storage import init_db                         # noqa: E402
_BASE = []


def _pret():
    """La base du banc (meshy_tasks : record_created/record_state écrivent le journal des tâches), une fois."""
    if not _BASE:
        asyncio.run(init_db()); _BASE.append(1)

UPLOADS = []


async def _faux_upload(p):
    UPLOADS.append(pathlib.Path(p).name)
    return f"https://fal.test/{pathlib.Path(p).name}"


A3._upload = _faux_upload


def _png() -> bytes:
    import io
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (4, 4), (200, 90, 40)).save(b, "PNG"); return b.getvalue()


def _job(nom: str, texture: bool = True, approuve: bool = True) -> pathlib.Path:
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    maps = {"basecolor": _png()} if texture else {}
    (d / "model.glb").write_bytes(gltf_builder.build_glb(maps, None, "cube", nom))
    A3.write_manifest(d, {"engine": "tripo-h3.1", "stage": "final", "version": 1,
                          "texture_mode": "meshy:2k" if texture else "no", "shots": []})
    mesh_report.write_report(nom, "model.glb", version=1, avec_silhouettes=False)
    if approuve:
        A3.approve(nom, True)
    return d


def test_le_devis_lit_les_faces_et_dit_si_le_remesh_est_requis():
    _job("rig_devis")
    d = RIG.devis("rig_devis", actions=[0])
    assert d["tris"] == 12 and d["remesh_requis"] is False and d["credits"] == {"meshy": 8.0}, d
    assert d["fichier"] == "model.glb"
    RIG.RIG_MAX_FACES = 10                        # un cube de 12 faces dépasse
    try:
        d2 = RIG.devis("rig_devis")
        assert d2["remesh_requis"] is True and d2["credits"] == {"meshy": 10.0}, d2
    finally:
        RIG.RIG_MAX_FACES = 300_000


def test_un_maillage_nu_ou_non_approuve_est_refuse_avant_toute_depense():
    _job("rig_nu", texture=False); UPLOADS.clear()
    try:
        asyncio.run(RIG.rigger_asset3d("rig_nu")); raise AssertionError("aurait dû refuser")
    except ValueError as e:
        assert "texture" in str(e).lower(), e
    _job("rig_brouillon", approuve=False)
    try:
        asyncio.run(RIG.rigger_asset3d("rig_brouillon")); raise AssertionError("aurait dû refuser")
    except PermissionError as e:
        assert "approuv" in str(e).lower(), e
    assert UPLOADS == [], "rien ne doit partir chez fal avant la porte"


def test_le_rig_ecrit_une_version_squelettee_et_ses_animations():
    _pret()
    d = _job("rig_ok"); UPLOADS.clear()
    r = asyncio.run(RIG.rigger_asset3d("rig_ok", height_m=1.8, actions=[0]))
    assert r["version"] == 2 and r["file"] == "model.v2.glb", r
    assert mesh_edit.rig_inventory((d / "model.v2.glb").read_bytes())["a_squelette"]
    assert not mesh_edit.rig_inventory((d / "model.glb").read_bytes())["a_squelette"]   # la v1 n'est pas écrasée
    anims = RIG.animations_du_job("rig_ok")
    assert {a["nom"] for a in anims} == {"walking", "running", "action_0"}, anims
    for a in anims:
        assert (d / a["file"]).is_file() and mesh_edit.rig_inventory((d / a["file"]).read_bytes())["clips"], a
        assert a["file"].endswith(".v2.glb"), a                                        # les clips portent la version
    man = json.loads((d / "asset.json").read_text("utf-8"))
    assert man["rig"]["height_m"] == 1.8 and man["rig"]["remesh_task"] is None and man["engine"] == "tripo-h3.1"
    assert r["taches"] == [r["meshy_task"], r["anim_tasks"][0]] and len(r["anim_tasks"]) == 1, r
    reg = mesh_report.read_registry("rig_ok")
    assert reg["current"] == "model.v2.glb" and reg["entries"][-1]["source"]["operation"] == "rig", reg["entries"][-1]
    assert UPLOADS == ["model.glb"], UPLOADS       # le GLB courant, une fois
    (d / "anim_running.v2.glb").unlink()            # un clip effacé à la main n'est plus annoncé
    assert {a["nom"] for a in RIG.animations_du_job("rig_ok")} == {"walking", "action_0"}


def test_au_dela_de_300000_faces_le_remesh_precede_le_rig():
    _pret()
    d = _job("rig_gros"); RIG.RIG_MAX_FACES = 10
    try:
        r = asyncio.run(RIG.rigger_asset3d("rig_gros"))
    finally:
        RIG.RIG_MAX_FACES = 300_000
    man = json.loads((d / "asset.json").read_text("utf-8"))
    assert man["rig"]["remesh_task"] and man["rig"]["remesh_task"] != man["rig"]["meshy_task"], man["rig"]
    assert r["remesh"] is True and r["taches"][0] == man["rig"]["remesh_task"], r   # l'ordre = celui du devis


def test_les_routes_refusent_avant_le_job_puis_gardent_et_rattachent():
    _pret()
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.services import plafonds as PL
    from app.services.storage import Depense, JobRecord, async_session_factory
    from sqlalchemy import select
    _job("rig_route"); _job("rig_route_bis"); _job("rig_route_nu", texture=False); _job("rig_route_br", approuve=False)

    async def main():
        o = {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            dv = await c.get("/api/assets/3d/rig_route/rig/devis", params={"actions": "0,4"})
            o["devis"] = (dv.status_code, dv.json())
            o["404"] = (await c.post("/api/assets/3d/inconnu/rig", json={})).status_code
            o["409"] = (await c.post("/api/assets/3d/rig_route_br/rig", json={})).status_code
            nu = await c.post("/api/assets/3d/rig_route_nu/rig", json={})
            o["nu"] = (nu.status_code, nu.text)
            o["actions"] = (await c.post("/api/assets/3d/rig_route/rig", json={"actions": ["x"]})).status_code
            settings.MESHY_MOCK = False
            k, settings.MESHY_API_KEY = settings.MESHY_API_KEY, ""
            o["cle"] = (await c.post("/api/assets/3d/rig_route/rig", json={})).status_code
            settings.MESHY_MOCK, settings.MESHY_API_KEY = True, k
            fk, settings.FAL_KEY = settings.FAL_KEY, ""
            o["fal"] = (await c.post("/api/assets/3d/rig_route/rig", json={})).status_code
            o["devis_fal"] = (await c.get("/api/assets/3d/rig_route/rig/devis")).json()["fal"]
            settings.FAL_KEY = fk
            PL.enregistrer({"par_moteur": {"meshy": 0.01}})
            o["402"] = (await c.post("/api/assets/3d/rig_route/rig", json={"actions": [0]})).status_code
            async with async_session_factory() as s:
                o["jobs_apres_402"] = len((await s.execute(select(JobRecord).where(JobRecord.provider == "asset3d"))).scalars().all())
            PL.enregistrer({"par_moteur": {"meshy": 0}})
            r = await c.post("/api/assets/3d/rig_route/rig", json={"height_m": 1.6, "actions": [0, 4]})
            o["lance"] = (r.status_code, r.json())
            jid = r.json().get("job_id")
            for _ in range(400):
                j = (await c.get(f"/api/jobs/{jid}")).json()
                if j.get("status") in ("done", "failed"):
                    break
                await asyncio.sleep(0.05)
            o["job"] = j
            await asyncio.sleep(0.2)
            async with async_session_factory() as s0:      # le client de test attend la tâche de fond : on pose
                s0.add(JobRecord(id="rig-en-cours", status="generating_video", progress=50, title="x",   # un job vivant
                                 image_filename="asset3d_rig_route_bis", provider="asset3d", current_step="x"))
                await s0.commit()
            o["double"] = (await c.post("/api/assets/3d/rig_route_bis/rig", json={})).status_code
            a = await c.get("/api/assets/3d/rig_route/animations")
            o["anims"] = a.json()
            w = await c.get("/api/assets/3d/rig_route/animation/walking")
            o["walking"] = (w.status_code, w.headers.get("content-type"), w.content[:4])
            o["anim404"] = (await c.get("/api/assets/3d/rig_route/animation/asset.json")).status_code
            tr = await c.get("/api/assets/3d/rig_route/animation/..%2Fasset.json")
            o["traversee"] = (tr.headers.get("content-type", ""), b'"rig"' in tr.content, tr.content[:4] == b"glTF")
            async with async_session_factory() as s:
                o["dep"] = [(d.op, d.estime_usd, d.ref, d.reel_unites)
                            for d in (await s.execute(select(Depense).order_by(Depense.id))).scalars().all()]
        return o
    o = asyncio.run(main())
    st, dv = o["devis"]
    assert st == 200 and dv["credits"] == {"meshy": 11.0} and dv["tris"] == 12, o["devis"]
    assert o["404"] == 404 and o["409"] == 409 and o["nu"][0] == 400 and "texture" in o["nu"][1].lower(), o
    assert o["actions"] == 400, o["actions"]
    assert o["cle"] == 400, o["cle"]
    assert o["fal"] == 400 and o["devis_fal"] is False, (o["fal"], o["devis_fal"])   # mesuré sur 8799 : sans clé fal, refus AVANT la garde
    assert dv["fal"] is True and dv["approuve"] is True and dv["texture"] is True and dv["meshy"] is True, dv
    assert o["402"] == 402 and o["jobs_apres_402"] == 0, (o["402"], o["jobs_apres_402"])
    st, l = o["lance"]
    assert st == 200 and l["status"] == "queued" and l["devis"]["credits"] == {"meshy": 11.0}, o["lance"]
    assert o["double"] == 409, o["double"]                              # un job vivant sur ce maillage : refus AVANT tout
    assert o["job"]["status"] == "done", o["job"]
    noms = {x["nom"] for x in o["anims"]["animations"]}
    assert noms == {"walking", "running", "action_0", "action_4"}, o["anims"]
    assert o["walking"] == (200, "model/gltf-binary", b"glTF"), o["walking"]
    assert o["anim404"] == 404, o["anim404"]
    assert o["traversee"][1] is False and o["traversee"][2] is False, o["traversee"]   # ni le manifeste, ni un GLB
    dep = [x for x in o["dep"] if x[0] == "asset3d_rig"]
    assert len(dep) == 3, o["dep"]                                       # rig + 2 actions : une dépense par tâche
    refs = [x[2] for x in dep]
    assert all(r and r.startswith("meshy:") for r in refs) and len(set(refs)) == 3, refs   # chacune SA tâche
    assert all(x[3] is not None for x in dep), dep                       # le réel (crédits) est noté


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (asset3d_rig)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
