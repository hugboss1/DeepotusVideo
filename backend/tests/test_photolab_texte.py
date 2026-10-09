# -*- coding: utf-8 -*-
"""t156 (Photolab parité L6) — texte, formes, plume, tracés.
[1] liste blanche : `path` d'un tracé vectoriel admis pour path.set / shape.create / shape.edit / shape.presets.new (objet ou
    « work »), toujours refusé comme fichier ailleurs et dès qu'une chaîne « fichier » s'y cache ; type.create admet les
    clés de caractère de type.setStyle ; align (énumération complète) admis pour setStyle et create.
[2] VRAI moteur — vignettes de forme personnalisée et de style de calque (document temporaire refermé, original intact,
    refus des noms « fichier », préréglage inconnu refusé) ; [3] parcours : texte créé avec police, couleur, poids, styles par
    plage, alignement ; tracé de travail enregistré ; forme par tracé ; [4] route /presets/{genre}/vignette.png.
Section VRAI moteur rouge si le binaire manque (PHOTOCRAFT_CLI dans un worktree).
Run : & $PY -X utf8 tests/test_photolab_texte.py   (depuis backend/)"""
import asyncio, io, json, os, pathlib, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt156_"))
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


TRACE = {"subpaths": [{"closed": True, "op": "combine", "knots": [{"anchor": [10, 10], "in": [10, 10], "out": [10, 10], "smooth": False},
                                                                 {"anchor": [60, 10], "in": [60, 10], "out": [60, 10], "smooth": False},
                                                                 {"anchor": [40, 50], "in": [50, 45], "out": [30, 55], "smooth": True}]}], "fillRule": "nonzero"}


def admis(reg, cid, p):
    try:
        PM.commande_autorisee(cid, p, reg)
        return True
    except ValueError as e:
        return e


def moteur():
    print("\n[1-3] VRAI moteur")
    PM.fermer()
    PM.FABRIQUE = None
    try:
        cli = PM.chemin_cli()
        check("0 le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", cli.is_file(), cli)
    except PM.MoteurAbsent as e:
        check("0 le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", False, e)
        return False
    from PIL import Image
    s = PM.session()
    reg = PM.registre(s)
    ex = lambda c, **p: s.appeler("engine.execute", {"command": c, "params": p})

    print("\n[1] liste blanche")
    for cid, p in (("path.set", {"name": "work", "path": TRACE}), ("shape.create", {"kind": "path", "path": TRACE, "fill": "#ff0000"}),
                   ("shape.edit", {"path": TRACE}), ("shape.presets.new", {"name": "Essai", "path": "work"}),
                   ("type.create", {"x": 10, "y": 50, "text": "A", "font": "Arial", "weight": 700, "italic": True, "size": 24, "color": "#336699", "align": "justify"}),
                   ("type.setStyle", {"layer": 3, "range": [0, 2], "align": "center"}), ("type.setStyle", {"align": "justifyAll", "direction": "rtl"}),
                   ("type.insertText", {"layer": 3, "text": "€"}), ("path.rename", {"name": "work", "to": "Tracé 1"}), ("path.toSelection", {"name": "Tracé 1"}),
                   ("select.toWorkPath", {"tolerance": 2}), ("shape.presets.place", {"preset": "Heart", "group": "Symbols", "rect": [0, 0, 10, 10]}),
                   ("style.presets.apply", {"preset": "Drop Shadow", "group": "Basics", "add": True}), ("type.characterStyle.new", {"fromSelection": True}),
                   ("type.paragraphStyle.apply", {"id": 0, "clearOverrides": True})):
        r = admis(reg, cid, p)
        check(f"1a admis : {cid} {json.dumps(p, ensure_ascii=False)[:70]}", r is True, r)
    for cid, p in (("path.set", {"name": "work", "path": "c:/x.svg"}), ("shape.create", {"kind": "path", "path": "dossier/forme.svg"}),
                   ("path.set", {"name": "work", "path": "Tracé 1"}), ("shape.create", {"kind": "path", "path": "M 0 0 L 10 10"}),
                   ("path.set", {"name": "work", "path": {"subpaths": [{"knots": [["c:/a.png", 1]]}]}}),
                   ("path.set", {"name": "work", "path": {"subpaths": [], "file": "x"}}), ("type.create", {"x": 1, "y": 1, "text": "A", "chemin": "x"}),
                   ("type.setStyle", {"align": "justifyLeft"}), ("type.create", {"x": 1, "y": 1, "text": "A", "font": "c:/fonts/a.ttf"}),
                   ("path.fill", {"name": "work", "path": TRACE})):
        r = admis(reg, cid, p)
        check(f"1b refusé : {cid} {json.dumps(p, ensure_ascii=False)[:70]}", r is not True, r)

    print("\n[2] vignettes de forme et de style")
    s.appeler("doc.new", {"width": 200, "height": 120, "background": "white"})
    avant, sl_avant = s.appeler("doc.inspect"), s.appeler("session.list")
    f, _ = PM.vignette_preset(s, "forme", "Heart", "Symbols")
    st, _ = PM.vignette_preset(s, "style", "Drop Shadow", "Basics")
    apres, sl_apres = s.appeler("doc.inspect"), s.appeler("session.list")
    imf, ims = Image.open(io.BytesIO(f)), Image.open(io.BytesIO(st))
    check("2a forme : PNG 64×64 avec des pixels opaques", imf.size == (64, 64) and imf.convert("RGBA").getextrema()[3][1] > 0)
    check("2b style : PNG 64×64 (carré stylé)", ims.size == (64, 64) and ims.convert("RGBA").getextrema()[3][1] > 0)
    check("2c l'original est intact (révision, historique, documents, actif)", avant["revision"] == apres["revision"] and avant["history"] == apres["history"]
          and len(sl_avant["documents"]) == len(sl_apres["documents"]) and sl_avant["active"] == sl_apres["active"])
    for lib, args in (("genre inconnu", ("zorg", "Heart")), ("nom fichier", ("forme", "c:/a.png")), ("groupe fichier", ("style", "Gold", "../x.json")),
                      ("nom vide", ("forme", ""))):
        try:
            PM.vignette_preset(s, *args)
            r = False
        except ValueError:
            r = True
        check(f"2d {lib} -> ValueError", r)
    try:
        PM.vignette_preset(s, "forme", "Zorglub")
        r = False
    except PM.MoteurErreur:
        r = True
    sl = s.appeler("session.list")
    check("2e forme inconnue -> refus du moteur, document temporaire refermé", r and len(sl["documents"]) == 1, sl)

    print("\n[3] parcours sur le vrai moteur")
    p = {"x": 20, "y": 80, "text": "Bonjour", "font": "Arial", "weight": 700, "italic": False, "size": 30, "color": "#336699"}
    check("3a les paramètres de l'écran passent la liste blanche", admis(reg, "type.create", p) is True)
    r = ex("type.create", **p)
    info = ex("type.info", layer=r["layer"])
    run = info["runs"][0]["style"]
    check("3b texte : police, poids, taille, couleur appliqués", run["font_family"] == "Arial" and run["weight"] == 700 and run["size_pt"] == 30
          and [round(v, 2) for v in run["color"]["c"][:3]] == [0.2, 0.4, 0.6], run)
    ex("type.setStyle", layer=r["layer"], range=[0, 3], size=48)
    ex("type.setStyle", layer=r["layer"], align="center")
    info = ex("type.info", layer=r["layer"])
    check("3c style par plage et alignement", [(x["start"], x["end"], x["style"]["size_pt"]) for x in info["runs"]] == [(0, 3, 48.0), (3, 7, 30.0)]
          and info["paragraphs"][0]["style"]["align"] == "Center", info["runs"])
    ex("path.set", name="work", path=TRACE)
    ex("path.rename", name="work", to="Tracé 1")
    pl = ex("path.list")
    check("3d tracé de travail enregistré", [x["name"] for x in pl["paths"]] == ["Tracé 1"] and pl["workPath"] is None, pl)
    sh = ex("shape.create", kind="path", path=TRACE, fill="#ff0000")
    check("3e forme par tracé (plume en mode Forme)", sh["kind"] == "path" and sh["bounds"][2] > 40, sh)
    hist = s.appeler("doc.inspect")["history"]
    noms = [x.get("name") if isinstance(x, dict) else x for x in (hist.get("entries", []) if isinstance(hist, dict) else hist)]
    check("3f historique : New Type Layer, Set Type Style ×2, Work Path, Save Path, New Shape Layer",
          noms[-6:] == ["New Type Layer", "Set Type Style", "Set Type Style", "Work Path", "Save Path", "New Shape Layer"], noms)
    return True


async def routes():
    print("\n[4] route /presets/{genre}/vignette.png")
    import httpx
    from app.main import app
    t = httpx.ASGITransport(app=app, client=("127.0.0.1", 5000))
    async with httpx.AsyncClient(transport=t, base_url="http://t") as c:
        r = await c.get("/api/photolab/presets/forme/vignette.png", params={"cle": "Arrow Right", "groupe": "Arrows"})
        check("4a forme : 200, image/png", r.status_code == 200 and r.headers.get("content-type") == "image/png" and r.content[:4] == b"\x89PNG", (r.status_code, r.text[:200]))
        r = await c.get("/api/photolab/presets/style/vignette.png", params={"cle": "Gold"})
        check("4b style sans groupe : 200", r.status_code == 200, (r.status_code, r.text[:200]))
        r = await c.get("/api/photolab/presets/zorg/vignette.png", params={"cle": "x"})
        check("4c genre inconnu : 400", r.status_code == 400, (r.status_code, r.text[:200]))
        r = await c.get("/api/photolab/presets/forme/vignette.png", params={"cle": "..\\x.png"})
        check("4d nom « fichier » : 400", r.status_code == 400, (r.status_code, r.text[:200]))


try:
    if moteur():
        asyncio.run(routes())
finally:
    PM.fermer()
    shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
