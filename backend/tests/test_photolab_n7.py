# t417 (Photolab N7, photocraft 0.21) : cadres — lire, régler, remplir, ajuster, convertir.
# Lancement : python embarqué, `python tests/test_photolab_n7.py` depuis backend/ (PHOTOCRAFT_CLI si le moteur n'est pas vendu).
import asyncio, os, pathlib, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt417_"))
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
        fond = (await ins())["activeLayer"]
        cadre = (await ex("layer.new.frame", {"x": 20, "y": 20, "width": 120, "height": 80, "shape": "ellipse"})).json()["layer"]

        print("[1] lire")
        r = await c.get(f"{API}/cadres/{cadre}")
        check("1.1 /cadres/<id> : la fiche du cadre", r.status_code == 200 and r.json()["frame"] == [20, 20, 120, 80] and r.json()["content"] is None, r.text[:200])
        r = await c.get(f"{API}/cadres/{fond}")
        check("1.2 un calque qui n'est pas un cadre : 404", r.status_code == 404, (r.status_code, r.text[:160]))

        print("[2] contenu")
        await ex("layer.new.layer"); await ex("select.all"); await ex("edit.fill", {"color": "#ff0000"}); await ex("select.deselect")
        contenu = (await ins())["activeLayer"]
        h = (await ins())["history"]
        r = await ex("layer.frame.setContent", {"layer": cadre, "content": contenu})
        check("2.1 un état « Replace Frame Content »", r.status_code == 200 and (await ins())["history"] == h + ["Replace Frame Content"], (r.status_code, r.text[:200]))
        check("2.2 le calque entre dans le cadre", (await c.get(f"{API}/cadres/{cadre}")).json()["content"] == contenu)
        await ex("edit.undo")
        check("2.3 annulable", (await c.get(f"{API}/cadres/{cadre}")).json()["content"] is None)
        await ex("layer.frame.setContent", {"layer": cadre, "content": contenu})
        r = await ex("layer.frame.setContent", {"layer": cadre, "content": 9999})
        check("2.4 calque absent : refus du moteur", r.status_code == 422, (r.status_code, r.text[:160]))

        print("[3] ajuster")
        r = await ex("layer.frame.fit", {"layer": cadre, "mode": "contentToFrame"})
        check("3.1 contenu au cadre", r.status_code == 200 and (await ins())["history"][-1] == "Fit Content to Frame", (r.status_code, r.text[:200]))
        r = await ex("layer.frame.fit", {"layer": cadre, "mode": "frameToContent"})
        check("3.2 cadre au contenu", r.status_code == 200 and (await ins())["history"][-1] == "Frame Properties", (r.status_code, r.text[:200]))
        r = await ex("layer.frame.fit", {"layer": cadre, "mode": "zorg"})
        check("3.3 mode inconnu refusé", r.status_code == 400, (r.status_code, r.text[:160]))

        print("[4] propriétés")
        r = await ex("layer.frame.set", {"layer": cadre, "name": "Portrait", "transform": [100, 0, 0, 60, 10, 10], "stroke": {"width": 4, "color": "#00ff00"}})
        i = (await c.get(f"{API}/cadres/{cadre}")).json()
        check("4.1 position, taille, nom, contour", r.status_code == 200 and i["frame"] == [10, 10, 100, 60] and i["name"] == "Portrait" and i["stroke"] is not None, (r.text[:200], i))
        r = await ex("layer.frame.set", {"layer": cadre, "stroke": None})
        check("4.2 retirer le contour", r.status_code == 200 and (await c.get(f"{API}/cadres/{cadre}")).json()["stroke"] is None, r.text[:200])
        r = await ex("layer.frame.set", {"layer": cadre, "zorg": 1})
        check("4.3 clé inconnue refusée", r.status_code == 400, (r.status_code, r.text[:160]))

        print("[5] convertir")
        f = (await ex("shape.create", {"kind": "rect", "rect": [10, 10, 50, 50], "fill": "#0000ff"})).json()["layer"]
        r = await ex("layer.frame.convert", {"layer": f})
        check("5.1 une forme devient un cadre", r.status_code == 200 and (await ex("layer.frame.info", {"layer": r.json().get("layer", f)})).status_code == 200, (r.status_code, r.text[:200]))
        r = await ex("layer.frame.convert", {"layer": fond})
        check("5.2 un calque de pixels : refus du moteur", r.status_code == 422, (r.status_code, r.text[:160]))


asyncio.run(scenario())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
