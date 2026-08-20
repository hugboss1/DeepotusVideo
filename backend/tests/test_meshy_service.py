"""3D Studio Meshy (v2.1) — grille tarifaire (port exact de meshy.client.js),
estimate_pipeline (coût AVANT action), allowlist du proxy /api/meshy/*,
simulateur MESHY_MOCK (statuts/progress/consumed_credits fidèles), pipeline
complet preview→refine→remesh→rig→animations enchaîné à travers le proxy
HTTP (ASGITransport, zéro réseau), enregistrement meshy_tasks, rapatriement
des binaires (spec INTEGRATION-MESHY.md §6), SSE mock, 403 hors allowlist,
503 sans clé. Run: python backend/tests/test_meshy_service.py"""
import asyncio
import json as _json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
# DATA_ROOT isolé : ni le .env réel ni la DB réelle ne sont touchés (règle 6).
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["MESHY_MOCK"] = "1"
os.environ["MESHY_MOCK_SPEED"] = "0.02"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings                      # noqa: E402
import app.services.meshy_service as MS              # noqa: E402

PASS = 0


def ok(label: str):
    global PASS
    PASS += 1
    print(f"  ✓ {label}")


# ══ 1 · grille tarifaire — mêmes valeurs que meshy.client.js → CREDITS ══════
print("— pricing —")
assert MS.credits_text_to_3d_preview("meshy-6") == 20
assert MS.credits_text_to_3d_preview("latest") == 20
assert MS.credits_text_to_3d_preview("meshy-5") == 5
assert MS.credits_text_to_3d_preview("meshy-5", "lowpoly") == 20
ok("text-to-3d preview : 20 (meshy-6/latest/lowpoly) · 5 (meshy-5)")
assert MS.credits_text_to_3d_refine("2k") == 10
assert MS.credits_text_to_3d_refine("4k") == 10
assert MS.credits_text_to_3d_refine("8k") == 15
ok("refine : 10 (2k/4k) · 15 (8k)")
assert MS.credits_image_to_3d("meshy-6", "standard", True, "2k") == 30
assert MS.credits_image_to_3d("meshy-6", "smart-topology", True, "2k") == 15
assert MS.credits_image_to_3d("meshy-6", "standard", True, "8k") == 35
assert MS.credits_image_to_3d("meshy-6", "smart-topology", True, "8k") == 20
assert MS.credits_image_to_3d("meshy-6", "standard", False) == 20
assert MS.credits_image_to_3d("meshy-5", "standard", False) == 5
assert MS.credits_image_to_3d("meshy-6", "smart-topology", False) == 5
ok("image-to-3d : 30/15 texturé · 35/20 en 8k · 20/5/5 sans texture")
assert MS.credits_retexture("4k") == 10 and MS.credits_retexture("8k") == 15
assert MS.CREDITS_FLAT == {"remesh": 5, "convert": 1, "resize": 1,
                           "uv-unwrap": 1, "rigging": 5, "animations": 3}
ok("retexture 10/15 · flat remesh 5, rig 5, anim 3, convert 1")

print("— meshy-7 + ultra —")
assert MS.credits_image_to_3d("meshy-7", "standard", True, "2k") == 30
assert MS.credits_image_to_3d("meshy-7", "standard", True, "8k") == 35
assert MS.credits_image_to_3d("meshy-7", "standard", False) == 20
assert MS.credits_image_to_3d("meshy-7", "standard", True, "2k", ultra=True) == 35
assert MS.credits_image_to_3d("meshy-7", "standard", True, "8k", ultra=True) == 40
assert MS.credits_image_to_3d("meshy-6", "standard", True, "2k", ultra=True) == 30  # ultra ignoré hors v7/latest
assert MS.credits_image_to_3d("latest", "standard", True, "2k", ultra=True) == 35
assert MS.credits_text_to_3d_preview("meshy-7") == 20
assert MS.credits_text_to_3d_preview("meshy-7", ultra=True) == 25
ok("meshy-7 : grille HD (20/30/35) + ultra +5 (v7/latest seulement)")

# le miroir JS porte les mêmes valeurs — confronté PAR VALEUR via node, pas
# par simple présence de sous-chaîne (le docstring du module promet mieux).
_js_path = (pathlib.Path(__file__).resolve().parent.parent.parent
           / "frontend" / "meshy" / "meshy.client.js")
if shutil.which("node") is None:
    _js = _js_path.read_text(encoding="utf-8")
    _bloc = _js.split("export const CREDITS")[1].split("};")[0]
    assert "meshy-7" in _bloc and "ultra" in _bloc
    ok("miroir JS non confronté : node absent (substring seulement)")
else:
    _js_url = "file:///" + str(_js_path.resolve()).replace("\\", "/")
    _node_script = f"""
const M = await import(new URL({_json.dumps(_js_url)}));
const models = ["meshy-5", "meshy-6", "meshy-7", "latest"];
const modelTypes = ["standard", "lowpoly", "smart-topology"];
const out = [];
for (const aiModel of models)
  for (const modelType of modelTypes)
    for (const shouldTexture of [true, false])
      for (const textureResolution of ["2k", "8k"])
        for (const ultra of [true, false]) {{
          out.push({{
            aiModel, modelType, shouldTexture, textureResolution, ultra,
            img: M.CREDITS.imageTo3d({{ aiModel, modelType, shouldTexture, textureResolution, ultra }}),
            prev: M.CREDITS.textTo3dPreview({{ aiModel, modelType, ultra }})
          }});
        }}
console.log(JSON.stringify(out));
"""
    _r = subprocess.run(["node", "--input-type=module"], input=_node_script,
                        capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert _r.returncode == 0, _r.stderr
    _combos = _json.loads(_r.stdout)
    _bad = [c for c in _combos if
           MS.credits_image_to_3d(c["aiModel"], c["modelType"], c["shouldTexture"],
                                  c["textureResolution"], ultra=c["ultra"]) != c["img"]
           or MS.credits_text_to_3d_preview(c["aiModel"], c["modelType"],
                                            ultra=c["ultra"]) != c["prev"]]
    assert not _bad, _bad[:5]
    ok(f"miroir CREDITS confronté par node : {len(_combos)} combinaisons, 0 divergence")

# helpers serveur mock-aware (P9 s'en servira ; ici on prouve le contrat)
settings.MESHY_MOCK = True
settings.MESHY_MOCK_SPEED = 0.01
MS._mock = None                      # repartir d'un simulateur neuf, vitesse test


async def _create_and_wait_ultra():
    tid = await MS.create_task("openapi/v1/image-to-3d", {
        "image_url": "data:image/png;base64,AAAA", "ai_model": "meshy-7",
        "should_texture": True, "ultra_mode": True})
    assert tid.startswith("mock-")
    for _ in range(500):
        t = await MS.get_task("openapi/v1/image-to-3d", tid)
        if t["status"] in MS.TERMINAL:
            return t
        await asyncio.sleep(0.02)
    else:
        raise AssertionError("tâche mock jamais terminale")


_final_task = asyncio.run(_create_and_wait_ultra())
assert _final_task["status"] == "SUCCEEDED" and _final_task["consumed_credits"] == 35
assert _final_task["model_urls"]["glb"].startswith(MS.MOCK_FILE_PREFIX)
ok("create_task/get_task serveur : mock-aware, crédits ultra comptés")
settings.MESHY_MOCK = True    # restaure : main() plus bas suppose le mock actif
settings.MESHY_MOCK_SPEED = 0.02   # restaure : valeur d'origine (env, ligne ~24)
MS._mock = None

# ══ 2 · estimate_pipeline — coût AVANT lancement (règle produit) ════════════
print("— estimate_pipeline —")
REF = {  # enchaînement de référence INTEGRATION-MESHY.md §5
    "source": "text", "aiModel": "meshy-6", "textureResolution": "4k",
    "withTexture": True, "withRemesh": True, "withRig": True,
    "animationActions": [{"actionId": 41, "name": "idle_breathe"},
                         {"actionId": 92, "name": "walk_cycle"},
                         {"actionId": 118, "name": "attack_slam"}],
    "exportFormats": ["glb", "fbx", "usdz"],
}
est = MS.estimate_pipeline(REF)
assert est["total"] == 49, est   # 20 + 10 + 5 + 5 + 3×3 (formats natifs = 0)
assert [x["id"] for x in est["lines"]] == \
    ["preview", "texture", "remesh", "rig", "animate", "animate", "animate"]
ok("référence §5 : 49 cr, 7 lignes (export natif gratuit)")
est2 = MS.estimate_pipeline({**REF, "exportFormats": ["glb", "3mf"]})
assert est2["total"] == 50 and est2["lines"][-1]["id"] == "export"
ok("3MF opt-in : +1 cr en ligne export")
est3 = MS.estimate_pipeline({"source": "image", "aiModel": "meshy-6",
                             "withRemesh": False, "withRig": False})
assert est3["total"] == 30 and len(est3["lines"]) == 1
ok("image-to-3d : passe unique 30 cr, pas de ligne refine")
est4 = MS.estimate_pipeline({"source": "text", "ai_model": "meshy-5",
                             "with_texture": False, "with_remesh": False,
                             "with_rig": False, "animation_actions": []})
assert est4["total"] == 5
ok("snake_case accepté (backend) — meshy-5 nu : 5 cr")

# ══ 3 · allowlist du proxy ══════════════════════════════════════════════════
print("— parse_proxy_path —")
p = MS.parse_proxy_path("POST", "openapi/v2/text-to-3d")
assert p == {"base": "openapi/v2/text-to-3d", "task_id": None, "stream": False}
p = MS.parse_proxy_path("GET", "openapi/v2/text-to-3d/018a210d-abcd/stream")
assert p and p["stream"] and p["task_id"] == "018a210d-abcd"
assert MS.parse_proxy_path("GET", "openapi/v1/balance") is not None
assert MS.parse_proxy_path("DELETE", "openapi/v1/remesh/mock-0001") is not None
ok("chemins documentés acceptés (création, suivi, stream, balance, delete)")
for m, path in [("POST", "openapi/v1/balance"), ("DELETE", "openapi/v2/text-to-3d"),
                ("GET", "openapi/v1/evil"), ("GET", "openapi/v1/rigging/../../etc"),
                ("POST", "openapi/v2/text-to-3d/tid"), ("GET", "admin"),
                ("GET", "openapi/v1/remesh/id/xx"), ("PUT", "openapi/v1/remesh")]:
    assert MS.parse_proxy_path(m, path) is None, (m, path)
ok("hors surface → refusé (traversée, verbes, endpoints inconnus)")

# ══ 4 · binaires mock minimaux ══════════════════════════════════════════════
print("— tiny binaries —")
glb = MS.tiny_glb()
assert glb[:4] == b"glTF" and len(glb) == int.from_bytes(glb[8:12], "little")
png = MS.tiny_png()
assert png[:8] == b"\x89PNG\r\n\x1a\n" and png.endswith(b"IEND\xaeB`\x82")
data, media = MS.mock_file_bytes("model.glb")
assert data[:4] == b"glTF" and media == "model/gltf-binary"
ok("GLB (header/longueur) et PNG (magic/IEND) valides")


# ══ 5-9 · async : mock, pipeline HTTP complet, DB, rapatriement, SSE ════════
async def wait_done(c, base, tid):
    for _ in range(400):
        r = await c.get(f"/api/meshy/{base}/{tid}")
        assert r.status_code == 200, r.text
        t = r.json()
        if t["status"] in MS.TERMINAL:
            return t
        await asyncio.sleep(0.02)
    raise AssertionError(f"task {tid} never terminal")


async def main():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.services.storage import init_db, MeshyTaskRecord, async_session_factory
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:

        print("— endpoints compagnons —")
        r = await c.get("/api/meshy3d/status")
        assert r.json() == {"enabled": True, "mock": True, "configured": False,
                            "host": "simulateur local"}
        r = await c.post("/api/meshy3d/estimate", json=REF)
        assert r.status_code == 200 and r.json()["total"] == 49
        r = await c.get("/api/health")
        h = r.json()
        assert h["meshy_mock"] is True and h["meshy_enabled"] is True
        ok("status/estimate/health cohérents en mode mock")

        print("— allowlist HTTP —")
        r = await c.get("/api/meshy/openapi/v1/evil")
        assert r.status_code == 403, r.text
        r = await c.post("/api/meshy/openapi/v1/balance")
        assert r.status_code == 403
        ok("403 hors surface documentée")

        print("— pipeline complet en mock (enchaînement §5) —")
        # 1 · preview (maillage brut)
        r = await c.post("/api/meshy/openapi/v2/text-to-3d", json={
            "mode": "preview", "prompt": "prophète pieuvre, armure de corail",
            "ai_model": "meshy-6", "topology": "triangle",
            "target_polycount": 30000, "pose_mode": "a-pose"})
        assert r.status_code == 202, r.text
        prev_id = r.json()["result"]
        # refine AVANT que le preview soit SUCCEEDED → 400 (contrat API réel)
        r = await c.post("/api/meshy/openapi/v2/text-to-3d", json={
            "mode": "refine", "preview_task_id": prev_id})
        assert r.status_code == 400
        ok("refine prématuré refusé (preview pas SUCCEEDED)")
        prev = await wait_done(c, "openapi/v2/text-to-3d", prev_id)
        assert prev["status"] == "SUCCEEDED" and prev["consumed_credits"] == 20
        assert prev["model_urls"]["glb"].startswith("/api/meshy3d/mockfile/")
        # 2 · refine (texture PBR 4k)
        r = await c.post("/api/meshy/openapi/v2/text-to-3d", json={
            "mode": "refine", "preview_task_id": prev_id,
            "texture_resolution": "4k", "enable_pbr": True})
        tex = await wait_done(c, "openapi/v2/text-to-3d", r.json()["result"])
        assert tex["consumed_credits"] == 10
        # 3 · remesh quad 30 k
        r = await c.post("/api/meshy/openapi/v1/remesh", json={
            "input_task_id": tex["id"], "topology": "quad",
            "target_polycount": 30000, "target_formats": ["glb", "fbx"]})
        rem = await wait_done(c, "openapi/v1/remesh", r.json()["result"])
        assert rem["consumed_credits"] == 5
        # 4 · auto-rig 1,75 m
        r = await c.post("/api/meshy/openapi/v1/rigging", json={
            "input_task_id": rem["id"], "height_meters": 1.75})
        rig = await wait_done(c, "openapi/v1/rigging", r.json()["result"])
        assert rig["consumed_credits"] == 5 and rig["result"]["rigged_model_url"]
        # animations sans rig_task_id → 400
        r = await c.post("/api/meshy/openapi/v1/animations", json={"action_id": 41})
        assert r.status_code == 400
        # 5 · trois actions, 3 cr pièce
        spent = 0
        for aid in (41, 92, 118):
            r = await c.post("/api/meshy/openapi/v1/animations", json={
                "rig_task_id": rig["id"], "action_id": aid})
            anim = await wait_done(c, "openapi/v1/animations", r.json()["result"])
            spent += anim["consumed_credits"]
            assert anim["result"]["animation_glb_url"]
        assert spent == 9
        total = 20 + 10 + 5 + 5 + spent
        assert total == MS.estimate_pipeline(REF)["total"] == 49
        ok("preview 20 + refine 10 + remesh 5 + rig 5 + 3 anims 9 = estimé 49")

        r = await c.get("/api/meshy/openapi/v1/balance")
        assert r.json()["balance"] == 8240 - 49
        ok("solde API décrémenté des consumed_credits réels")

        print("— journal + rapatriement (spec §6) —")
        await asyncio.sleep(0.4)   # laisse les rapatriements de fond aboutir
        r = await c.get("/api/meshy3d/tasks")
        tasks = r.json()["tasks"]
        # preview + refine + remesh + rig + 3 animations = 7 tâches
        assert len(tasks) == 7 and all(t["status"] == "SUCCEEDED" for t in tasks)
        phases = {t["phase"] for t in tasks}
        assert phases == {"preview", "texture", "remesh", "rig", "animate"}
        prev_row = next(t for t in tasks if t["id"] == prev_id)
        assert prev_row["consumed_credits"] == 20
        assert prev_row["payload"]["pose_mode"] == "a-pose"
        ok("7 tâches journalisées, phases du graphe, paramètres envoyés conservés")
        assert all(t["local_files"] for t in tasks), tasks
        glb_url = prev_row["local_files"]["glb"]
        assert glb_url.startswith("/api/meshy3d/files/")
        r = await c.get(glb_url)
        assert r.status_code == 200 and r.content[:4] == b"glTF"
        disk = pathlib.Path(_tmp, "outputs", "meshy3d")
        assert any(disk.iterdir())
        ok("binaires rapatriés sur disque et servis en URLs locales stables")
        r = await c.get("/api/meshy3d/tasks")
        assert r.json()["expiring"] == []
        ok("rien n'expire sans copie locale (expiring vide)")

        print("— SSE mock —")
        r = await c.post("/api/meshy/openapi/v1/remesh", json={
            "input_task_id": rem["id"], "topology": "quad"})
        sse_id = r.json()["result"]
        events = []
        async with c.stream("GET",
                            f"/api/meshy/openapi/v1/remesh/{sse_id}/stream") as s:
            assert s.headers["content-type"].startswith("text/event-stream")
            async for line in s.aiter_lines():
                if line.startswith("data:"):
                    events.append(line)
        assert events and '"SUCCEEDED"' in events[-1]
        ok("flux SSE : événements jusqu'au statut terminal")

        print("— clé absente, mock coupé —")
        settings.MESHY_MOCK = False
        settings.MESHY_API_KEY = ""
        r = await c.get("/api/meshy/openapi/v1/balance")
        assert r.status_code == 503 and "Settings" in r.json()["detail"]
        r = await c.get("/api/meshy3d/status")
        assert r.json()["enabled"] is False
        r = await c.get("/api/meshy3d/mockfile/x/model.glb")
        assert r.status_code == 404
        settings.MESHY_MOCK = True
        ok("503 explicite sans clé ; mockfile inerte hors mode mock")

        print("— headers proxy réel —")
        settings.MESHY_API_KEY = "msy-test-key"
        settings.MESHY_MOCK = False
        seen = {}

        class _FakeResp:
            status_code = 200
            content = b'{"balance": 5}'
            headers = {"content-type": "application/json"}

        class _FakeClient:
            def __init__(self, **kw):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def request(self, method, url, headers=None, content=None,
                              params=None):
                seen.update(method=method, url=url, headers=headers)
                return _FakeResp()

        real_client = MS.httpx.AsyncClient
        MS.httpx.AsyncClient = _FakeClient
        try:
            r = await c.get("/api/meshy/openapi/v1/balance")
        finally:
            MS.httpx.AsyncClient = real_client
            settings.MESHY_MOCK = True
            settings.MESHY_API_KEY = ""
        assert r.status_code == 200 and r.json()["balance"] == 5
        assert seen["url"] == "https://api.meshy.ai/openapi/v1/balance"
        assert seen["headers"]["Authorization"] == "Bearer msy-test-key"
        ok("Bearer injecté côté serveur, cible api.meshy.ai (la clé ne sort pas)")

        print("— create_task/get_task hors mock : erreurs et allowlist —")
        settings.MESHY_API_KEY = "msy-test-key"
        settings.MESHY_MOCK = False

        class _RaisingClient:
            def __init__(self, **kw):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def post(self, *a, **kw):
                raise httpx.ConnectError("boom")

            async def get(self, *a, **kw):
                raise httpx.ConnectError("boom")

        class _UnauthResp:
            status_code = 401
            text = '{"error": "Unauthorized"}'

            def json(self):
                return {"error": "Unauthorized"}

        class _UnauthClient:
            def __init__(self, **kw):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def post(self, *a, **kw):
                return _UnauthResp()

            async def get(self, *a, **kw):
                return _UnauthResp()

        try:
            MS.httpx.AsyncClient = _RaisingClient
            try:
                await MS.create_task("openapi/v1/image-to-3d", {})
                raise AssertionError("aurait dû lever ConnectError")
            except RuntimeError as e:
                assert str(e).startswith("meshy: ConnectError"), str(e)
            # allowlist rejette AVANT tout réseau — même client (qui casserait
            # sinon avec ConnectError) le prouve : jamais appelé ici.
            try:
                await MS.get_task("openapi/v1/../../evil", "x")
                raise AssertionError("aurait dû lever chemin non autorisé")
            except RuntimeError as e:
                assert "chemin non autorisé" in str(e), str(e)
            # verrou : clé absente → RuntimeError nommée, jamais un appel voué
            # au 401 (même client, qui casserait sinon avec ConnectError).
            settings.MESHY_API_KEY = ""
            try:
                await MS.create_task("openapi/v1/image-to-3d", {})
                raise AssertionError("aurait dû lever MESHY_API_KEY absente")
            except RuntimeError as e:
                assert "MESHY_API_KEY absente" in str(e), str(e)
            settings.MESHY_API_KEY = "msy-test-key"

            MS.httpx.AsyncClient = _UnauthClient
            try:
                await MS.create_task("openapi/v1/image-to-3d", {})
                raise AssertionError("aurait dû lever Unauthorized")
            except RuntimeError as e:
                assert "Unauthorized" in str(e) and "None" not in str(e), str(e)
        finally:
            MS.httpx.AsyncClient = real_client
            settings.MESHY_MOCK = True
            settings.MESHY_API_KEY = ""
            MS._mock = None
        ok("hors mock : ConnectError/401 préfixés meshy:, clé absente nommée, allowlist get_task sans réseau")

    # garde anti-régression : Game Assets 3D (fal) intact
    from app.services.asset3d_service import ENGINES
    assert set(ENGINES) == {"tripo", "hunyuan", "trellis", "rodin", "triposr"}
    assert "meshy" not in ENGINES
    ok("ENGINES fal inchangés — meshy ne s'y invite pas")


asyncio.run(main())
print(f"\nOK — {PASS} assertions groupées vertes (meshy_service)")
