# t419 (Photolab N9, photocraft 0.21) : longues opérations en tâche de fond — lancer, suivre, annuler.
# Lancement : python embarqué, `python tests/test_photolab_n9.py` depuis backend/ (PHOTOCRAFT_CLI si le moteur n'est pas vendu).
import asyncio, os, pathlib, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt419_"))
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
        fond = lambda cmd, p=None: post("/executer", {"command": cmd, "params": p or {}, "fond": True})
        ins = lambda: asyncio.to_thread(PM.session().appeler, "doc.inspect")

        async def attendre(job):
            for _ in range(600):
                j = (await c.get(f"{API}/taches/{job}")).json()
                if j["state"] != "running":
                    return j
                await asyncio.sleep(0.05)
            return j
        assert (await post("/nouveau", {"width": 6000, "height": 4000, "background": "white"})).status_code == 200
        await post("/executer", {"command": "filter.render.clouds", "params": {}})

        print("[1] lancer et suivre")
        h = (await ins())["history"]
        r = await fond("filter.blur.gaussianBlur", {"radius": 200})
        job = r.json().get("job")
        check("1.1 réponse immédiate : un numéro de tâche", r.status_code == 200 and isinstance(job, int), r.text)
        j = (await c.get(f"{API}/taches/{job}")).json()
        check("1.2 l'état se lit, avec sa progression", j["state"] in ("running", "done") and 0 <= j["progress"] <= 1 and "command" not in j, j)
        j = await attendre(job)
        check("1.3 fini : un état d'historique", j["state"] == "done" and (await ins())["history"] == h + ["Gaussian Blur"], (j, (await ins())["history"][-2:]))
        check("1.4 le résultat suit", "result" in j, j)

        print("[2] annuler")
        h = (await ins())["history"]
        job = (await fond("filter.blur.gaussianBlur", {"radius": 240})).json()["job"]
        r = await post("/executer", {"command": "image.adjustments.invert", "params": {}})
        check("2.1 pendant la tâche, le moteur refuse d'éditer le document", r.status_code == 422 and "still running" in r.text, (r.status_code, r.text))
        r = await post(f"/taches/{job}/annuler")
        j = await attendre(job)
        check("2.2 annulée : document inchangé", r.status_code == 200 and j["state"] == "cancelled" and (await ins())["history"] == h, (r.text, j))

        print("[3] refus")
        r = await post("/executer", {"command": "layer.new.layer", "params": {}, "fond": True})
        check("3.1 hors des longues opérations : 400", r.status_code == 400, (r.status_code, r.text))
        r = await post("/executer", {"command": "filter.blur.gaussianBlur", "params": {"radius": 2}, "fond": "oui"})
        check("3.2 fond : booléen", r.status_code == 400, (r.status_code, r.text))
        r = await fond("filter.blur.gaussianBlur", {"radius": -5})
        check("3.3 la liste blanche passe avant", r.status_code == 400, (r.status_code, r.text))
        r = await fond("filter.blur.gaussianBlur", {"zorg": 1})
        check("3.4 clé inconnue refusée", r.status_code == 400, (r.status_code, r.text))
        r = await c.get(f"{API}/taches/99999")
        check("3.5 tâche inconnue : 404", r.status_code == 404, (r.status_code, r.text))
        r = await post("/taches/99999/annuler")
        check("3.6 annuler une tâche inconnue : 404", r.status_code == 404, (r.status_code, r.text))
        r = await c.get(f"{API}/taches/abc")
        check("3.7 numéro illisible : 422", r.status_code == 422, (r.status_code, r.text))

        print("[4] enregistrer une action")
        await post("/executer", {"command": "actions.record", "params": {"name": "Flou"}})
        job = (await fond("filter.blur.gaussianBlur", {"radius": 2})).json()["job"]
        await attendre(job)
        await post("/executer", {"command": "actions.stop", "params": {}})
        g = (await post("/executer", {"command": "actions.get", "params": {"action": "Flou"}})).json()
        check("4.1 un filtre en tâche de fond reste enregistré", [e[0] for e in g["steps"]] == ["filter.blur.gaussianBlur"], g)
        h = (await ins())["history"]
        await post("/executer", {"command": "actions.play", "params": {"action": "Flou"}})
        check("4.2 et se rejoue", len((await ins())["history"]) == len(h) + 1, (await ins())["history"][-2:])


asyncio.run(scenario())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
