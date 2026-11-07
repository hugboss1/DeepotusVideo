# t411 (Photolab N1, photocraft 0.21) : objets dynamiques — Remplacer le contenu et Exporter le contenu.
# [1] les commandes à chemin restent refusées à /executer ; seules les routes y mènent ;
# [2] /objets/remplacer : image de la Bibliothèque, un état « Replace Contents », annulable, refus propres ;
# [3] /objets/exporter : le contenu dans la Bibliothèque, l'original intact ;
# [4] commandes neuves du lot restées fermées (bloqué moteur, ou sans destination dans la Bibliothèque).
# Lancement : python embarqué, `python tests/test_photolab_n1.py` depuis backend/ (PHOTOCRAFT_CLI si le moteur n'est pas vendu).
import asyncio, os, pathlib, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt411_"))
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


Image.new("RGB", (80, 40), (255, 0, 0)).save(_tmp / "images" / "rouge.png")
Image.new("RGB", (60, 60), (0, 255, 0)).save(_tmp / "images" / "vert.png")
(_tmp / "images" / "abime.png").write_bytes(b"pas une image")


async def scenario():
    import httpx
    from app.main import app
    API = "/api/photolab"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t", timeout=120) as c:
        post = lambda u, j=None: c.post(API + u, json=j if j is not None else {})
        ex = lambda cmd, p=None: post("/executer", {"command": cmd, "params": p or {}})
        ins = lambda: asyncio.to_thread(PM.session().appeler, "doc.inspect")
        assert (await post("/nouveau", {"width": 200, "height": 100, "background": "white"})).status_code == 200

        print("[1] les commandes à chemin restent fermées")
        for cmd, p in (("layer.smartObjects.replaceContents", {"path": "x.png"}), ("layer.smartObjects.exportContents", {"path": "x.png"})):
            r = await ex(cmd, p)
            check(f"1.1 {cmd} refusée à /executer", r.status_code in (400, 403), (r.status_code, r.text))

        print("[2] Remplacer le contenu")
        r = await post("/objets/remplacer", {"filename": "vert.png"})
        check("2.1 calque de pixels : refus clair, rien ne change", r.status_code == 400 and "objet dynamique" in r.text, (r.status_code, r.text))
        r = await post("/placer", {"filename": "rouge.png", "reduire": False})
        lid = r.json()["layer"]
        h0 = (await ins())["history"]
        r = await post("/objets/remplacer", {"filename": "vert.png"})
        i = await ins()
        calque = next(x for x in i["layers"] if x["id"] == lid)
        check("2.2 remplacé : même calque, un état « Replace Contents »", r.status_code == 200 and r.json().get("layer") == lid
              and i["history"] == h0 + ["Replace Contents"], (r.status_code, r.text, i["history"][-3:]))
        check("2.3 le contenu suit la nouvelle image", calque["smartSource"]["fileName"].endswith("vert.png") and calque["bounds"][2:] == [60, 60], calque)
        await ex("edit.undo")
        i = await ins()
        check("2.4 annulable", next(x for x in i["layers"] if x["id"] == lid)["bounds"][2:] == [80, 40] and i["history"] == h0, i["history"][-3:])
        r = await post("/objets/remplacer", {"filename": "absente.png"})
        check("2.5 image absente : 404", r.status_code == 404, (r.status_code, r.text))
        r = await post("/objets/remplacer", {"filename": "../rouge.png"})
        check("2.6 nom refusé : 400", r.status_code == 400, (r.status_code, r.text))
        r = await post("/objets/remplacer", {"filename": "abime.png"})
        check("2.7 fichier illisible : 422, le document ne change pas", r.status_code == 422 and (await ins())["history"] == h0, (r.status_code, r.text))
        r = await post("/objets/remplacer", {"filename": "vert.png", "path": "x"})
        check("2.8 clé inconnue : 400", r.status_code == 400, (r.status_code, r.text))

        print("[3] Exporter le contenu")
        avant, sl_avant = await ins(), await asyncio.to_thread(PM.session().appeler, "session.list")
        r = await post("/objets/exporter")
        apres, sl_apres = await ins(), await asyncio.to_thread(PM.session().appeler, "session.list")
        noms = r.json().get("filenames") if r.status_code == 200 else []
        check("3.1 un PNG déposé dans la Bibliothèque", r.status_code == 200 and len(noms) == 1 and noms[0].startswith("photolab_") and noms[0].endswith(".png"), r.text)
        if noms:
            f = _tmp / "images" / noms[0]
            with Image.open(f) as im:
                check("3.2 c'est le contenu, pas le calque transformé", im.size == (80, 40) and im.convert("RGB").getpixel((5, 5)) == (255, 0, 0), im.size)
        check("3.4 l'original est intact (historique, révision, document actif, un seul document)",
              avant["history"] == apres["history"] and avant["revision"] == apres["revision"] and sl_avant["active"] == sl_apres["active"]
              and len(sl_apres["documents"]) == len(sl_avant["documents"]), (sl_avant, sl_apres))
        reste = list((PM.dossier_travail() / "sorties").glob("*"))
        check("3.5 aucun dossier de lot laissé", not reste, reste)
        await ex("layer.select", {"layer": next(x["id"] for x in apres["layers"] if x["kind"] == "Pixel"), "mode": "replace"})
        r = await post("/objets/exporter")
        check("3.6 calque de pixels : refus clair", r.status_code == 400 and "objet dynamique" in r.text, (r.status_code, r.text))

        print("[4] le reste du lot reste fermé")
        for cmd in ("layer.smartObjects.embedAllLinked", "layer.smartObjects.exportSvg", "layer.smartObjects.updateSvg", "layer.smartObjects.updateVectorSource"):
            r = await ex(cmd)
            check(f"4.1 {cmd} fermée", r.status_code == 400 and "pas encore ouverte" in r.text, (r.status_code, r.text))


asyncio.run(scenario())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
