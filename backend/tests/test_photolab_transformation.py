# -*- coding: utf-8 -*-
"""t154 (Photolab parité L4) — Transformation manuelle : edit.transform validé par la liste blanche et admis en APERÇU.
[1] liste blanche : edit.transform {layer, rect, quad, interpolation} admis ; interpolation inconnue, valeur « fichier »
    refusées ; /apercu admet désormais edit.transform (et toujours pas une commande hors aperçu).
[2] VRAI moteur — aperçu sur COPIE : l'original garde révision, historique, contenu et sélection ; l'image de l'aperçu est
    identique à l'octet près (pixels) au rendu après application réelle ; l'application réelle pose « Free Transform ».
[3] route POST /api/photolab/apercu avec une étape edit.transform.
Section VRAI moteur rouge si le binaire manque (PHOTOCRAFT_CLI dans un worktree).
Run : & $PY -X utf8 tests/test_photolab_transformation.py   (depuis backend/)"""
import asyncio, os, pathlib, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt154_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_moteur as PM                # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:500]}")


QUAD = [[70, 15], [115, 25], [110, 55], [65, 50]]


def moteur():
    print("\n[1-2] VRAI moteur")
    PM.fermer()
    PM.FABRIQUE = None
    try:
        cli = PM.chemin_cli()
        check("0 le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", cli.is_file(), cli)
    except PM.MoteurAbsent as e:
        check("0 le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", False, e)
        return None
    from PIL import Image, ImageChops
    s = PM.session()
    reg = PM.registre(s)
    ex = lambda c, **p: s.appeler("engine.execute", {"command": c, "params": p})

    print("\n[1] liste blanche")
    bon = {"layer": 3, "rect": [20, 20, 60, 50], "quad": QUAD, "interpolation": "bilinear"}
    try:
        PM.commande_autorisee("edit.transform", bon, reg)
        r = True
    except ValueError as e:
        r = e
    check("1a edit.transform {layer, rect, quad, interpolation} admis", r is True, r)
    for lib, p in (("interpolation inconnue", {**bon, "interpolation": "lanczos"}), ("valeur fichier", {**bon, "target": "c:/x.png"}),
                   ("clé inconnue", {**bon, "chemin": 1})):
        try:
            PM.commande_autorisee("edit.transform", p, reg)
            r = False
        except ValueError:
            r = True
        check(f"1b {lib} -> refusé", r)
    check("1c /apercu admet edit.transform", PM.forme_etapes([{"command": "edit.transform", "params": bon}])[0]["command"] == "edit.transform")
    try:
        PM.forme_etapes([{"command": "edit.transform.again", "params": {}}])
        r = False
    except ValueError:
        r = True
    check("1d /apercu refuse toujours une commande hors aperçu (edit.transform.again)", r)

    print("\n[2] aperçu sur copie")
    s.appeler("doc.new", {"width": 160, "height": 90, "background": "white"})
    ex("layer.new.layer")
    ex("select.rect", x=20, y=20, width=40, height=30)
    ex("edit.fill", contents="color", color="#cc3300")
    ex("select.rect", x=30, y=25, width=10, height=10)
    ex("edit.fill", contents="color", color="#0044ff")
    ex("select.deselect")
    insp = s.appeler("doc.inspect")
    calque = insp["activeLayer"]
    etape = {"command": "edit.transform", "params": {"layer": calque, "rect": [20, 20, 60, 50], "quad": QUAD, "interpolation": "bicubic"}}
    avant, sl_avant = s.appeler("doc.inspect"), s.appeler("session.list")
    sortie, _ = PM.apercu(s, [etape], 160)
    apres, sl_apres = s.appeler("doc.inspect"), s.appeler("session.list")
    check("2a l'original est intact (révision, historique, calques, documents)", avant["revision"] == apres["revision"] and avant["history"] == apres["history"]
          and avant["layers"] == apres["layers"] and len(sl_avant["documents"]) == len(sl_apres["documents"]), (avant["revision"], apres["revision"]))
    check("2b résultat de l'étape : le cadre source", sortie["resultats"][0] == {"rect": [20.0, 20.0, 60.0, 50.0]}, sortie["resultats"])
    f_apv = PM.dossier_travail() / "rendus" / sortie["fichier"]
    with Image.open(f_apv) as im:
        apv = im.convert("RGBA").copy()
    ex("edit.transform", **etape["params"])
    hist = s.appeler("doc.inspect")["history"]
    noms = [x.get("name") if isinstance(x, dict) else x for x in (hist.get("entries", []) if isinstance(hist, dict) else hist)]
    check("2c application réelle : « Free Transform » dans l'historique", noms[-1] == "Free Transform", noms[-3:])
    reel = PM.dossier_travail() / "rendus" / "t154-reel.png"
    s.appeler("doc.render", {"path": PM.relatif("rendus/t154-reel.png"), "maxSide": 160})
    with Image.open(reel) as im:
        rl = im.convert("RGBA").copy()
    diff = ImageChops.difference(apv, rl).getbbox()
    check("2d aperçu = application réelle, pixel pour pixel", apv.size == rl.size and diff is None, (apv.size, rl.size, diff))
    check("2e le contenu a bien bougé (témoin : pixel orange à (100, 40))", rl.getpixel((100, 40))[:3] != (255, 255, 255), rl.getpixel((100, 40)))
    return calque


async def route(calque):
    print("\n[3] route /apercu")
    import httpx
    from app.main import app
    t = httpx.ASGITransport(app=app, client=("127.0.0.1", 5000))
    async with httpx.AsyncClient(transport=t, base_url="http://t") as c:
        r = await c.post("/api/photolab/apercu", json={"etapes": [{"command": "edit.transform", "params": {"layer": calque, "quad": [[0, 0], [50, 0], [50, 40], [0, 40]]}}], "maxSide": 128})
        check("3a POST /apercu edit.transform : 200, url d'aperçu", r.status_code == 200 and "/rendus/apv-" in r.json().get("url", ""), (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/apercu", json={"etapes": [{"command": "edit.transform", "params": {"layer": calque, "interpolation": "zorg"}}], "maxSide": 128})
        check("3b interpolation refusée : 400 sans toucher au moteur", r.status_code == 400, (r.status_code, r.text[:200]))


try:
    cq = moteur()
    if cq is not None:
        asyncio.run(route(cq))
finally:
    PM.fermer()
    shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
