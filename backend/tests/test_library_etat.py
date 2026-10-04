# -*- coding: utf-8 -*-
"""Bibliotheque, tache #82 PR B (plan-library T15, 04/10/2026) — l'ETAT d'un projet : monte / publie / imprime /
inutilise, cote serveur. Aucune donnee neuve, aucune ecriture : trois jointures et un complement EXACT.
Le plan voulait un onglet Projets « pose par libproj » (inexistant) : l'etat s'affiche dans la barre Projet (PR B ecran).
Temoin positif : la base (db3cf49b) n'a pas la route.
Run (depuis backend/) : & $PY tests/test_library_etat.py"""
import asyncio, io, json, os, pathlib, subprocess, sys, tempfile
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzetat_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs", "audio"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ["VECTOR_FOLDER"] = str(_tmp / "vector")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY",
          "ELEVENLABS_API_KEY", "FAL_KEY", "HEYGEN_API_KEY", "FIGMA_TOKEN"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from PIL import Image                                               # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "db3cf49b"
r_ro = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE)).stdout
check("T0 temoin : la base n'a pas la route d'etat", b'"/library/projets/{pid}/etat"' not in r_ro and b'"/library/projets/{pid}"' in r_ro)


async def main():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services import storage, gltf_builder, mesh_report
    from app.config import settings
    await storage.init_db()
    # un job 3D de l'Etabli dont la source est src3d.png
    t = io.BytesIO(); Image.new("RGBA", (1, 1)).save(t, "PNG")
    glb = gltf_builder.build_glb({}, None, "cube", "banc", stage_png=t.getvalue())
    J = settings.outputs_path / "assets3d" / "job3dabc"
    J.mkdir(parents=True); (J / "model.glb").write_bytes(glb)
    (J / "asset.json").write_text(json.dumps({"image_filename": "src3d.png", "version": 1}), encoding="utf-8")
    mesh_report.write_report("job3dabc", "model.glb", version=1, extra={"outil": "etabli", "operation": "adoption"})
    async with storage.async_session_factory() as s:
        s.add(storage.JobRecord(id="job-done-1", status="done", progress=100, image_filename="depart.png", image_filename_end="fin.png"))
        s.add(storage.JobRecord(id="job-encours", status="generating_video", progress=10, image_filename="encours.png"))
        s.add(storage.JobRecord(id="rendu-fini", status="done", progress=100, image_filename="x.png"))
        s.add(storage.JobRecord(id="job3dabc-0000", status="done", progress=100, image_filename="asset3d_job3dabc"))
        s.add(storage.ScheduledPost(id="p1", title="P", run_at=datetime(2026, 10, 1), status="posted", source_image="depart.png"))
        s.add(storage.ScheduledPost(id="p2", title="Q", run_at=datetime(2026, 10, 1), status="ready", source_image="pret.png"))
        s.add(storage.ScheduledPost(id="p3", title="R", run_at=datetime(2026, 10, 1), status="posted", job_id="rendu-fini"))
        s.add(storage.LibraryProject(id="pj", nom="Campagne"))
        for ref, kind in (("depart.png", "image"), ("fin.png", "image"), ("encours.png", "image"), ("pret.png", "image"), ("src3d.png", "image"),
                          ("rendu-fini", "render"), ("job3dabc-0000", "asset3d"), ("seule.png", "image")):
            s.add(storage.LibraryProjectItem(project_id="pj", ref=ref, kind=kind))
        s.add(storage.LibraryProject(id="vide", nom="Vide"))
        await s.commit()
    tr = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=tr, base_url="http://127.0.0.1") as cl:
        r = await cl.get("/api/library/projets/pj/etat")
        e = r.json()
        refs = lambda k: sorted(x["ref"] for x in e[k])
        check("E1 MONTE : image de depart ou de fin d'un job TERMINE, ou un rendu termine du projet (pas un job en cours)",
              r.status_code == 200 and refs("monte") == ["depart.png", "fin.png", "job3dabc-0000", "rendu-fini"], str(e.get("monte")))
        check("E2 PUBLIE : un post PUBLIE l'utilise (image source ou rendu) — pas un post seulement pret", refs("publie") == ["depart.png", "rendu-fini"], str(e.get("publie")))
        check("E3 IMPRIME : l'image source d'une production de l'Etabli, et le job 3D lui-meme", refs("imprime") == ["job3dabc-0000", "src3d.png"], str(e.get("imprime")))
        tous = {x["ref"] for x in e["monte"] + e["publie"] + e["imprime"]}
        check("E4 INUTILISE est le COMPLEMENT EXACT (partition) ; un asset peut etre dans plusieurs etats (depart.png : monte ET publie) ; le genre est rendu",
              refs("inutilise") == ["encours.png", "pret.png", "seule.png"] and set(refs("inutilise")).isdisjoint(tous)
              and tous | set(refs("inutilise")) == {"depart.png", "fin.png", "encours.png", "pret.png", "src3d.png", "rendu-fini", "job3dabc-0000", "seule.png"}
              and e["n"] == 8 and e["nom"] == "Campagne" and {"ref": "rendu-fini", "kind": "render"} in e["monte"], json.dumps(e)[:300])
        v = (await cl.get("/api/library/projets/vide/etat")).json()
        r404 = await cl.get("/api/library/projets/inconnu/etat")
        check("E5 un projet vide : quatre listes vides ; un projet inconnu : 404", v["n"] == 0 and all(v[k] == [] for k in ("monte", "publie", "imprime", "inutilise"))
              and r404.status_code == 404)
        avant = (_tmp / "t.db").read_bytes()
        await cl.get("/api/library/projets/pj/etat")
        check("E6 aucune ecriture (la base est identique a l'octet)", (_tmp / "t.db").read_bytes() == avant)


asyncio.run(main())
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
