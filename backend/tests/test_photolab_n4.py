# t414 (Photolab N4, photocraft 0.21) : peinture — Mélangeur (charger, nettoyer, prélever), Forme d'art d'historique, source
# de l'historique, pinceau précédent / suivant.
# Lancement : python embarqué, `python tests/test_photolab_n4.py` depuis backend/ (PHOTOCRAFT_CLI si le moteur n'est pas vendu).
import asyncio, base64, io, os, pathlib, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt414_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from PIL import Image                                          # noqa: E402
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

        async def px(*pts):
            r = await asyncio.to_thread(PM.session().appeler, "doc.render", {"maxSide": 0})
            im = Image.open(io.BytesIO(base64.b64decode(r["base64"])))
            return [im.getpixel(p)[:3] for p in pts]
        assert (await post("/nouveau", {"width": 200, "height": 100, "background": "white"})).status_code == 200
        await ex("layer.new.layer"); await ex("select.rect", {"x": 0, "y": 0, "width": 100, "height": 100})
        await ex("edit.fill", {"contents": "color", "color": "#ff0000"}); await ex("select.deselect")

        print("[1] Mélangeur")
        h = (await ins())["history"]
        r = await ex("paint.mixerLoad", {"x": 50, "y": 50, "size": 5})
        check("1.1 charger depuis la toile : la couleur, aucun état", r.status_code == 200 and r.json()["loaded"] is True and r.json()["color"][:3] == [1.0, 0.0, 0.0]
              and (await ins())["history"] == h, r.text)
        r = await ex("paint.mixerBrush", {"points": [[120, 20], [190, 20]], "size": 20, "wet": 0, "load": 100, "mix": 0, "flow": 100, "color": "#000000"})
        check("1.2 le trait suivant garde la charge", r.status_code == 200 and (await px((150, 20))) == [(255, 0, 0)], (r.text, await px((150, 20))))
        r = await ex("brush.mixer.clean")
        await ex("paint.mixerBrush", {"points": [[120, 50], [190, 50]], "size": 20, "wet": 50, "load": 0, "mix": 50, "flow": 100, "sampleAllLayers": False})
        check("1.3 nettoyé : le trait ne dépose plus de rouge", r.status_code == 200 and (await px((150, 50))) == [(255, 255, 255)], (r.text, await px((150, 50))))
        r = await ex("brush.mixer.load", {"color": "#00ff00"})
        check("1.4 charger la couleur", r.status_code == 200 and r.json()["reservoir"][:3] == [0.0, 1.0, 0.0], r.text)
        r = await ex("paint.mixerBrush", {"points": [[120, 80], [190, 80]], "size": 10, "wet": 0, "load": 100, "mix": 0, "cleanAfterStroke": True, "loadAfterStroke": False})
        check("1.5 options après le trait", r.status_code == 200, r.text)
        r = await ex("paint.mixerLoad", {"x": 50, "y": 50, "size": 7})
        check("1.6 taille hors liste refusée", r.status_code in (400, 422), (r.status_code, r.text))

        print("[2] source de l'historique")
        i = await ins()
        check("2.1 doc.inspect dit la source", i["historySource"] == {"label": "Open", "state": 0}, i.get("historySource"))
        r = await ex("history.setSource", {"state": 3})
        check("2.2 un état", r.status_code == 200 and (await ins())["historySource"]["state"] == 3, r.text)
        r = await ex("history.setSource", {"state": 999})
        check("2.3 état absent : refus du moteur", r.status_code == 422, (r.status_code, r.text))
        s = (await ex("history.newSnapshot", {"name": "A"})).json()["snapshot"]
        r = await ex("history.setSource", {"snapshot": s})
        check("2.4 un instantané", r.status_code == 200 and (await ins())["historySource"] == {"name": "A", "snapshot": s}, r.text)
        r = await ex("history.setSource", {"zorg": 1})
        check("2.5 clé inconnue refusée", r.status_code == 400, (r.status_code, r.text))
        await ex("history.setSource", {"state": 3})
        await ex("select.rect", {"x": 0, "y": 0, "width": 100, "height": 100}); await ex("edit.fill", {"contents": "color", "color": "#0000ff"}); await ex("select.deselect")
        r = await ex("paint.historyBrush", {"points": [[20, 20], [80, 20]], "size": 20, "hardness": 100, "opacity": 100, "flow": 100})
        check("2.6 le pinceau d'historique suit la source", r.status_code == 200 and (await px((50, 20))) == [(255, 0, 0)], (r.text, await px((50, 20))))

        print("[3] Forme d'art d'historique")
        h = (await ins())["history"]
        r = await ex("paint.artHistoryBrush", {"points": [[20, 70], [80, 70]], "size": 20, "hardness": 0, "style": "dab", "area": 50, "tolerance": 0, "opacity": 100})
        check("3.1 un état « Art History Brush »", r.status_code == 200 and (await ins())["history"] == h + ["Art History Brush"], (r.status_code, r.text, (await ins())["history"][-2:]))
        r = await ex("paint.artHistoryBrush", {"points": [[20, 70], [80, 70]], "style": "zorg"})
        check("3.2 style inconnu refusé", r.status_code in (400, 422), (r.status_code, r.text))

        print("[4] pinceau précédent / suivant")
        n = (await ex("tools.nextBrush")).json().get("preset")
        p = (await ex("tools.previousBrush")).json().get("preset")
        check("4.1 suivant puis précédent : deux pinceaux distincts", n and p and n != p, (n, p))
        d = (await ex("tools.lastBrush")).json().get("preset"); f = (await ex("tools.firstBrush")).json().get("preset")
        check("4.2 dernier et premier", d and f and d != f, (d, f))
        check("4.3 aucun état d'historique", (await ins())["history"][-1] == "Art History Brush")

        print("[5] le reste reste fermé")
        for cmd, q in (("brush.mixer.sample", {"points": [[1, 1]]}), ("paint.mixerBrush", {"points": [[1, 1]], "mixerState": {}}), ("paint.historyBrush", {"points": [[1, 1]], "snapshot": 1})):
            r = await ex(cmd, q)
            check(f"5.1 {cmd} {sorted(q)[-1]} : fermé", r.status_code == 400, (r.status_code, r.text))


asyncio.run(scenario())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
