# t413 (Photolab N3, photocraft 0.21) : tracés et formes — opérations de tracés, fusion de composants, ajouter ou soustraire
# à la sélection, angles arrondis des polygones, flèches du Trait.
# Lancement : python embarqué, `python tests/test_photolab_n3.py` depuis backend/ (PHOTOCRAFT_CLI si le moteur n'est pas vendu).
import asyncio, os, pathlib, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt413_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_moteur as PM                 # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:500]}")


async def scenario():
    import httpx
    from app.main import app
    API = "/api/photolab"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t", timeout=120) as c:
        post = lambda u, j=None: c.post(API + u, json=j if j is not None else {})
        ex = lambda cmd, p=None: post("/executer", {"command": cmd, "params": p or {}})
        ins = lambda: asyncio.to_thread(PM.session().appeler, "doc.inspect")
        assert (await post("/nouveau", {"width": 300, "height": 200, "background": "white"})).status_code == 200

        print("[1] opérations de tracés")
        l = (await ex("shape.create", {"kind": "rect", "rect": [20, 20, 120, 120], "fill": "#ff0000"})).json()["layer"]
        await ex("shape.create", {"kind": "ellipse", "rect": [80, 60, 120, 120], "addTo": l, "op": "combine"})
        ops = lambda j: [sp.get("op") for sp in j["path"]["subpaths"]]
        r = await ex("shape.create", {"kind": "ellipse", "rect": [10, 10, 30, 30], "addTo": l, "op": "subtract"})
        check("1.0 une forme ajoutée en soustraction", r.status_code == 200 and (await ex("path.info", {"name": "layer"})).json()["path"]["subpaths"][-1]["op"] == "subtract", r.text[:160])
        await ex("edit.undo")
        r = await ex("shape.create", {"kind": "ellipse", "rect": [10, 10, 30, 30], "addTo": l, "op": "zorg"})
        check("1.0b opération inconnue refusée", r.status_code == 400, (r.status_code, r.text))
        for op in ("subtract", "intersect", "exclude", "combine"):
            r = await ex("path.setOperation", {"name": "layer", "subpaths": [1], "op": op})
            check(f"1.1 {op}", r.status_code == 200 and ops(r.json()) == ["combine", op], (r.status_code, r.text[:160]))
        check("1.2 état « Path Operation »", (await ins())["history"][-1] == "Path Operation")
        r = await ex("path.setOperation", {"name": "layer", "subpaths": [1], "op": "zorg"})
        check("1.3 opération inconnue refusée par le pont", r.status_code == 400, (r.status_code, r.text))
        r = await ex("path.setOperation", {"name": "layer", "subpaths": [9], "op": "subtract"})
        check("1.4 sous-tracé absent : refus du moteur", r.status_code == 422, (r.status_code, r.text))
        r = await ex("path.setOperation", {"name": "layer", "subpaths": [0], "op": "subtract"})
        check("1.5 le premier composant combine toujours", r.status_code == 422, (r.status_code, r.text))
        await ex("path.setOperation", {"name": "layer", "subpaths": [1], "op": "subtract"})
        r = await ex("path.mergeShapeComponents", {"name": "layer"})
        check("1.6 fusion : un seul tracé", r.status_code == 200 and len(r.json()["path"]["subpaths"]) == 1 and (await ins())["history"][-1] == "Merge Shape Components", r.text[:160])
        await ex("edit.undo")
        r = await ex("path.info", {"name": "layer"})
        check("1.7 annulable", len(r.json()["path"]["subpaths"]) == 2)

        print("[2] sélection")
        await ex("path.set", {"name": "work", "path": {"subpaths": [{"closed": True, "knots": [[10, 10], [100, 10], [100, 100]]}]}})
        r = await ex("path.toSelection", {"name": "work", "mode": "add"})
        check("2.1 ajouter à la sélection", r.status_code == 200 and (await ins())["hasSelection"] is True, r.text)
        r = await ex("path.toSelection", {"name": "work", "mode": "subtract"})
        check("2.2 soustraire de la sélection : plus rien", r.status_code == 200 and (await ins())["hasSelection"] is False, r.text)

        print("[3] formes")
        r = await ex("shape.create", {"kind": "polygon", "sides": 5, "rect": [10, 10, 100, 100], "cornerRadius": 12, "fill": "#00ff00"})
        check("3.1 angles arrondis d'un polygone", r.status_code == 200 and r.json()["live"]["corner_radius"] == 12.0, r.text[:200])
        r = await ex("shape.create", {"kind": "line", "from": [10, 150], "to": [200, 150], "weight": 4, "arrowEnd": True, "arrowStart": False,
                                      "arrowWidth": 60, "arrowLength": 80, "arrowConcavity": 30, "fill": "#0000ff"})
        j = r.json() if r.status_code == 200 else {}
        check("3.2 flèche au bout du trait", r.status_code == 200 and j["live"]["end"] is True and j["live"]["start"] is False and j["live"]["concavity"] == 30.0, r.text[:200])
        r = await ex("shape.create", {"kind": "line", "from": [0, 0], "to": [5, 5], "arrowConcavity": 500})
        check("3.3 creux hors bornes refusé", r.status_code == 400, (r.status_code, r.text))
        r = await ex("shape.edit", {"layer": j.get("layer"), "arrowEnd": False})
        check("3.4 shape.edit aussi", r.status_code == 200 and r.json()["live"]["end"] is False, r.text[:200])

        print("[4] le reste reste fermé")
        for cmd in ("path.addToSelection", "path.subtractFromSelection"):
            r = await ex(cmd, {"name": "work"})
            check(f"4.1 {cmd} : doublon de path.toSelection, fermée", r.status_code == 400, (r.status_code, r.text))


asyncio.run(scenario())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
