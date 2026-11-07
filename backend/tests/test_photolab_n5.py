# t415 (Photolab N5, photocraft 0.21) : historique et lecture des actions.
# [1] Effacer l'historique : image intacte, annulable ; [2] options : routes, refus, effet réel sur le moteur ;
# [3] rejouées à chaque démarrage du moteur ; [4] les commandes de réglage restent fermées à /executer.
# Lancement : python embarqué, `python tests/test_photolab_n5.py` depuis backend/ (PHOTOCRAFT_CLI si le moteur n'est pas vendu).
import asyncio, os, pathlib, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt415_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_moteur as PM, photolab_options as PO   # noqa: E402

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
        assert (await post("/nouveau", {"width": 100, "height": 80, "background": "white"})).status_code == 200

        print("[1] Effacer l'historique")
        await ex("layer.new.layer"); await ex("select.all"); await ex("edit.fill", {"color": "#ff0000"}); await ex("select.deselect")
        h = (await ins())["history"]
        r = await ex("history.clear")
        i = await ins()
        check("1.1 il reste l'état courant seul", r.status_code == 200 and i["history"] == h[-1:], (r.text, i["history"]))
        check("1.2 les instantanés restent", [x["name"] for x in i["snapshots"]] == ["Untitled"], i["snapshots"])
        await ex("edit.undo")
        check("1.3 Annuler rend les états", (await ins())["history"] == h, (await ins())["history"])

        print("[2] options")
        r = await c.get(API + "/options/moteur")
        check("2.1 défauts", r.status_code == 200 and r.json()["options"] == PO.DEFAUTS, r.text)
        for corps, lib in (({"zorg": True}, "clé inconnue"), ({"actionUnEtat": 1}, "pas un booléen"), ({"allowNonLinearHistory": True}, "historique non linéaire fermé")):
            r = await post("/options/moteur", corps)
            check(f"2.2 {lib} : refus", r.status_code == 400, (r.status_code, r.text))
        r = await post("/options/moteur", {"actionUnEtat": False, "visibiliteAnnulable": False})
        check("2.3 enregistré, relu", r.status_code == 200 and r.json()["options"]["actionUnEtat"] is False and PO.lire()["visibiliteAnnulable"] is False, r.text)
        await ex("actions.record", {"name": "Deux"}); await ex("image.adjustments.invert"); await ex("select.all"); await ex("actions.stop")
        await ex("select.deselect")
        h = (await ins())["history"]
        await ex("actions.play", {"action": "Deux"})
        check("2.4 un état par étape quand l'option est coupée", (await ins())["history"][len(h):] == ["Invert", "Select All"], (await ins())["history"][-3:])
        lid = (await ins())["activeLayer"]
        h = (await ins())["history"]
        await ex("layer.setProps", {"layer": lid, "visible": False})
        check("2.5 visibilité non annulable : aucun état", (await ins())["history"] == h, (await ins())["history"][-2:])
        await ex("layer.setProps", {"layer": lid, "visible": True})
        await post("/options/moteur", {"instantaneEnregistrement": True})
        s = (await ins())["snapshots"]
        await asyncio.to_thread(PM.session().appeler, "doc.save", {"path": "exports/n5.pcraft"})
        check("2.6 un instantané à l'enregistrement", len((await ins())["snapshots"]) == len(s) + 1, (await ins())["snapshots"])

        print("[3] rejouées au démarrage")
        await asyncio.to_thread(PM.session().fermer)
        assert (await post("/nouveau", {"width": 50, "height": 50, "background": "white"})).status_code == 200
        o = (await ex("actions.list")).status_code
        r = await asyncio.to_thread(PM.session().appeler, "engine.execute", {"command": "history.options", "params": {}})
        check("3.1 le moteur neuf a les options", r["makeLayerVisibilityChangesUndoable"] is False and r["automaticallyCreateNewSnapshotWhenSaving"] is True, r)
        r = await asyncio.to_thread(PM.session().appeler, "engine.execute", {"command": "actions.setPlayback", "params": {}})
        check("3.2 lecture : un état par étape, rejoué", r["singleState"] is False and o == 200, r)
        await post("/options/moteur", {"premierInstantane": False})
        assert (await post("/nouveau", {"width": 50, "height": 50, "background": "white"})).status_code == 200
        check("3.3 sans instantané initial : un document nu", (await ins()).get("snapshots") == [], (await ins()).get("snapshots"))

        print("[4] fermées à /executer")
        for cmd, p in (("history.options", {"allowNonLinearHistory": True}), ("actions.setHistory", {"singleState": True}), ("actions.setPlayback", {}),
                       ("actions.newSet", {"name": "x"}), ("history.stepForward", {}), ("history.stepBackward", {})):
            r = await ex(cmd, p)
            check(f"4.1 {cmd} refusée", r.status_code == 400 and "pas encore ouverte" in r.text, (r.status_code, r.text))
    chemin = PO.chemin()
    chemin.write_text("{abîmé", encoding="utf-8")
    check("5.1 fichier abîmé : les défauts", PO.lire() == PO.DEFAUTS)
    check("5.2 étapes : deux commandes, jamais de clé non linéaire", [e["command"] for e in PO.etapes(PO.DEFAUTS)] == ["history.options", "actions.setHistory"]
          and "allowNonLinearHistory" not in PO.etapes(PO.DEFAUTS)[0]["params"])


asyncio.run(scenario())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
