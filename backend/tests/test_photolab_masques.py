# t157 (Photolab parité L7) : masques, filtres dynamiques, Sélectionner et masquer, Galerie de filtres — le pont.
# [1] liste blanche (galerie, réédition d'un filtre dynamique, étapes d'aperçu) ; [2] vignettes de masque ;
# [3] aperçu « Sélectionner et masquer » ; [4] galerie (catalogue, vignettes, aperçu) ; [5] routes.
# Lancement : python embarqué, `python tests/test_photolab_masques.py` (PHOTOCRAFT_CLI si le moteur n'est pas vendu).
import asyncio, base64, io, os, pathlib, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt157_"))
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


def admis(reg, cid, p):
    try:
        PM.commande_autorisee(cid, p, reg)
        return True
    except ValueError as e:
        return e


def refuse(f, *a):
    try:
        f(*a)
        return False
    except ValueError:
        return True


def png(data_url_ou_octets):
    from PIL import Image
    b = data_url_ou_octets
    if isinstance(b, str):
        b = base64.b64decode(b.split(",", 1)[1])
    return Image.open(io.BytesIO(b))


def image_rendu(fichier):
    from PIL import Image
    with Image.open(PM.dossier_travail() / "rendus" / fichier) as im:
        return im.convert("RGBA").copy()


def moteur():
    print("\n[0] VRAI moteur")
    PM.fermer()
    PM.FABRIQUE = None
    try:
        cli = PM.chemin_cli()
        check("0 le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", cli.is_file(), cli)
    except PM.MoteurAbsent as e:
        check("0 le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", False, e)
        return False
    s = PM.session()
    reg = PM.registre(s)
    ex = lambda c, **p: s.appeler("engine.execute", {"command": c, "params": p})

    print("\n[1] liste blanche")
    for p in ({"effects": [{"filter": "cutout"}]},
              {"effects": [{"filter": "cutout", "params": {"numberOfLevels": 6}, "visible": True},
                           {"filter": "filmGrain", "params": {"grain": 8}, "visible": False}], "foreground": "#000000", "background": "#ffffff"},
              {"effects": [{"filter": "neonGlow", "params": {"glowColor": [0.2, 0.4, 1, 1]}}]},
              {"effects": [{"filter": "paintDaubs", "params": {"brushType": "sparkle"}}]},
              {"list": True}):
        r = admis(reg, "filter.filterGallery", p)
        check(f"1a galerie admise : {str(p)[:80]}", r is True, r)
    for lib, p in (("filtre inconnu", {"effects": [{"filter": "zorg"}]}),
                   ("hors bornes (le moteur reviendrait au défaut en silence)", {"effects": [{"filter": "cutout", "params": {"numberOfLevels": 99}}]}),
                   ("paramètre inconnu", {"effects": [{"filter": "cutout", "params": {"radius": 3}}]}),
                   ("clé d'effet inconnue", {"effects": [{"filter": "cutout", "path": "x"}]}),
                   ("valeurs à plat (l'écran envoie params)", {"effects": [{"filter": "cutout", "numberOfLevels": 4}]}),
                   ("visible non booléen", {"effects": [{"filter": "cutout", "visible": "oui"}]}),
                   ("pile vide", {"effects": []}),
                   ("trop d'effets", {"effects": [{"filter": "cutout"}] * 21}),
                   ("effet non objet", {"effects": ["cutout"]}),
                   ("couleur non hex", {"effects": [{"filter": "cutout"}], "foreground": "red"}),
                   ("couleur de lueur hors 0..1", {"effects": [{"filter": "neonGlow", "params": {"glowColor": [255, 0, 0, 1]}}]}),
                   ("liste de choix hors liste", {"effects": [{"filter": "paintDaubs", "params": {"brushType": "c:/x.abr"}}]})):
        r = admis(reg, "filter.filterGallery", p)
        check(f"1b galerie refusée : {lib}", r is not True, r)

    insp = {"activeLayer": 6, "layers": [{"id": 6, "kind": "Smart Object", "smartFilters": [
        {"command": "filter.blur.gaussianBlur", "params": {"radius": 4}}, {"command": "filter.filterGallery", "params": {"effects": [{"filter": "cutout"}]}}]},
        {"id": 2, "kind": "Pixel"}]}
    v = PM.verifier_filtre_dynamique
    check("1c réédition admise : flou gaussien, rayon 8", v(reg, {"layer": 6, "index": 0, "params": {"radius": 8}}, insp) is None)
    check("1d réédition admise : galerie (pile)", v(reg, {"index": 1, "params": {"effects": [{"filter": "cutout", "params": {"numberOfLevels": 5}}]}}, insp) is None)
    check("1e index absent = filtre du haut (galerie) : une clé de flou est refusée", refuse(v, reg, {"params": {"radius": 8}}, insp))
    for lib, p in (("rayon hors bornes", {"layer": 6, "index": 0, "params": {"radius": 99999}}),
                   ("clé inconnue du filtre", {"layer": 6, "index": 0, "params": {"zorg": 1}}),
                   ("chaîne fichier", {"layer": 6, "index": 0, "params": {"radius": "c:/x.png"}}),
                   ("index hors pile", {"layer": 6, "index": 5, "params": {"radius": 2}}),
                   ("calque sans filtres dynamiques", {"layer": 2, "index": 0, "params": {"radius": 2}}),
                   ("calque inconnu", {"layer": 99, "index": 0, "params": {"radius": 2}}),
                   ("params non objet", {"layer": 6, "index": 0, "params": [1]})):
        check(f"1f réédition refusée : {lib}", refuse(v, reg, p, insp))
    for e in ({"command": "layer.smartFilter.setParams", "params": {"index": 0, "params": {"radius": 3}}},
              {"command": "layer.smartFilter.setVisible", "params": {"index": 0}},
              {"command": "layer.smartFilter.blendingOptions", "params": {"index": 0, "blend": "multiply", "opacity": 0.5}},
              {"command": "layer.smartFilter.disableSmartFilters", "params": {}},
              {"command": "filter.filterGallery", "params": {"effects": [{"filter": "cutout"}]}}):
        try:
            PM.etapes_apercu(PM.forme_etapes([e]), reg)
            r = True
        except ValueError as x:
            r = x
        check(f"1g étape d'aperçu admise : {e['command']}", r is True, r)
    check("1h aperçu de select.refineEdge par /apercu : refusé (il a sa route)", refuse(PM.forme_etapes, [{"command": "select.refineEdge", "params": {}}]))

    print("\n[2] vignettes de masque")
    s.appeler("doc.new", {"width": 200, "height": 120, "background": "white"})
    ex("layer.new.layer"); ex("select.all"); ex("edit.fill", contents="color", color="#ff0000")
    ex("select.rect", x=20, y=20, width=60, height=40)
    ex("layer.layerMask.revealSelection")
    masque_id = s.appeler("doc.inspect")["activeLayer"]
    ex("layer.new.layer")
    avant, sl_avant = s.appeler("doc.inspect"), s.appeler("session.list")
    out, _ = PM.masques(s, 100)
    apres, sl_apres = s.appeler("doc.inspect"), s.appeler("session.list")
    check("2a une vignette, pour le seul calque masqué", [m["layer"] for m in out] == [masque_id], out and [m["layer"] for m in out])
    if out:
        im = png(out[0]["png"]).convert("L")
        w, h = im.size
        check("2b 100 px de grand côté, niveaux de gris", max(w, h) == 100 and im.mode == "L", im.size)
        check("2c blanc dans le rectangle révélé, noir ailleurs",
              im.getpixel((int(50 * w / 200), int(40 * h / 120))) > 240 and im.getpixel((int(150 * w / 200), int(100 * h / 120))) < 15,
              (im.getpixel((int(50 * w / 200), int(40 * h / 120))), im.getpixel((int(150 * w / 200), int(100 * h / 120)))))
    check("2d l'original est intact (révision, historique, actif, sélection, documents)",
          avant["revision"] == apres["revision"] and avant["history"] == apres["history"] and avant["activeLayer"] == apres["activeLayer"]
          and avant["hasSelection"] == apres["hasSelection"] and len(sl_avant["documents"]) == len(sl_apres["documents"])
          and sl_avant["active"] == sl_apres["active"], (avant["history"], apres["history"]))
    seul, _ = PM.masques(s, 400, masque_id)
    check("2e un seul calque, grande taille (Alt-clic : le masque sur la toile)", len(seul) == 1 and max(png(seul[0]["png"]).size) == 200, seul and png(seul[0]["png"]).size)
    check("2f calque sans masque demandé -> ValueError", refuse(PM.masques, s, 100, 999))
    restes = [f for f in (PM.dossier_travail() / "rendus").iterdir() if f.name.startswith("msk-")]
    check("2g aucun rendu temporaire laissé", not restes, restes)

    print("\n[3] aperçu « Sélectionner et masquer »")
    s.appeler("doc.new", {"width": 200, "height": 120, "background": "white"})
    ex("layer.new.layer"); ex("select.rect", x=60, y=30, width=60, height=50); ex("edit.fill", contents="color", color="#2040c0")
    avant, sl_avant = s.appeler("doc.inspect"), s.appeler("session.list")
    reglages = {"radius": 2, "smooth": 10, "feather": 1, "contrast": 0, "shiftEdge": 0}
    vues = {}
    for vue in PM.VUES_MASQUER:
        sortie, _ = PM.apercu_masque(s, reglages, vue, 50, False, 200)
        vues[vue] = (sortie, image_rendu(sortie["fichier"]))
    apres, sl_apres = s.appeler("doc.inspect"), s.appeler("session.list")
    check("3a les 7 vues de la référence", sorted(PM.VUES_MASQUER) == sorted(["oignon", "fourmis", "incrustation", "noir", "blanc", "nb", "calques"]), PM.VUES_MASQUER)
    dedans, dehors = (90, 55), (10, 10)
    px = lambda vue, p: vues[vue][1].getpixel(p)
    check("3b noir et blanc : blanc dedans, noir dehors", px("nb", dedans)[:3] == (255, 255, 255) and px("nb", dehors)[:3] == (0, 0, 0), (px("nb", dedans), px("nb", dehors)))
    check("3c sur noir : le calque dedans, noir dehors", px("noir", dedans)[:3] == (32, 64, 192) and px("noir", dehors)[:3] == (0, 0, 0), (px("noir", dedans), px("noir", dehors)))
    check("3d sur blanc : blanc dehors", px("blanc", dehors)[:3] == (255, 255, 255) and px("blanc", dedans)[:3] == (32, 64, 192), (px("blanc", dedans), px("blanc", dehors)))
    r, g, b, _a = px("incrustation", dehors)
    check("3e incrustation : rouge à 50 % dehors, intact dedans", r > 240 and 110 < g < 145 and 110 < b < 145 and px("incrustation", dedans)[:3] == (32, 64, 192), (px("incrustation", dehors), px("incrustation", dedans)))
    check("3f sur calques : le fond blanc des autres calques reste visible dehors", px("calques", dehors)[:3] == (255, 255, 255), px("calques", dehors))
    check("3g pelure d'oignon : dehors transparent à moitié", 100 < px("oignon", dehors)[3] < 155 or px("oignon", dehors)[3] == 0, px("oignon", dehors))
    bf = vues["fourmis"][0].get("bounds")
    check("3h cadre de sélection : composite + cadre de la sélection affinée", px("fourmis", dehors)[:3] == (255, 255, 255)
          and isinstance(bf, list) and len(bf) == 4 and 50 <= bf[0] <= 62, bf)
    check("3i l'original est intact", avant["revision"] == apres["revision"] and avant["history"] == apres["history"]
          and avant.get("selectionBounds") == apres.get("selectionBounds") and len(sl_avant["documents"]) == len(sl_apres["documents"]),
          (avant["history"], apres["history"]))
    sortie, _ = PM.apercu_masque(s, reglages, "nb", 50, True, 200)
    im = image_rendu(sortie["fichier"])
    check("3j Inverser : noir dedans, blanc dehors", im.getpixel(dedans)[:3] == (0, 0, 0) and im.getpixel(dehors)[:3] == (255, 255, 255))
    for lib, args in (("vue inconnue", (reglages, "zorg", 50, False, 200)), ("transparence hors 0..100", (reglages, "nb", 150, False, 200)),
                      ("rayon hors bornes", ({"radius": 9999}, "nb", 50, False, 200)), ("sortie choisie par l'écran", ({"output": "newLayer"}, "nb", 50, False, 200)),
                      ("clé inconnue", ({"zorg": 1}, "nb", 50, False, 200)), ("chaîne fichier", ({"radius": "c:/a.png"}, "nb", 50, False, 200))):
        check(f"3k refusé : {lib}", refuse(PM.apercu_masque, s, *args))
    ex("select.deselect")
    check("3l sans sélection : ValueError (le moteur l'exige)", refuse(PM.apercu_masque, s, reglages, "nb", 50, False, 200))

    print("\n[4] galerie")
    cat, _ = PM.catalogue_galerie(s)
    check("4a catalogue : 47 filtres en 6 catégories", len(cat["filters"]) == 47 and len(cat["categories"]) == 6, (len(cat["filters"]), cat["categories"]))
    ex("select.rect", x=60, y=30, width=60, height=50)
    avant, sl_avant = s.appeler("doc.inspect"), s.appeler("session.list")
    vig, _ = PM.vignettes_galerie(s, ["cutout", "filmGrain", "glowingEdges"])
    apres, sl_apres = s.appeler("doc.inspect"), s.appeler("session.list")
    check("4b trois vignettes 80×56", sorted(vig) == ["cutout", "filmGrain", "glowingEdges"] and all(png(x).size == (80, 56) for x in vig.values()),
          {k: png(x).size for k, x in vig.items()})
    check("4c vignettes différentes d'un filtre à l'autre", len({x for x in vig.values()}) == 3)
    check("4d l'original est intact", avant["revision"] == apres["revision"] and avant["history"] == apres["history"]
          and avant.get("selectionBounds") == apres.get("selectionBounds") and len(sl_avant["documents"]) == len(sl_apres["documents"]), apres["history"])
    check("4e clé inconnue -> ValueError", refuse(PM.vignettes_galerie, s, ["zorg"]))
    check("4f plus de 16 clés -> ValueError", refuse(PM.vignettes_galerie, s, ["cutout"] * 17))
    pile = [{"filter": "cutout", "params": {"numberOfLevels": 3}}, {"filter": "filmGrain", "params": {"grain": 6}}]
    sortie, _ = PM.apercu(s, [{"command": "filter.filterGallery", "params": {"effects": pile}}], 200)
    ex("filter.filterGallery", effects=pile)
    ref = s.appeler("doc.render", {"path": PM.relatif("rendus/ref-galerie.png"), "maxSide": 200})
    check("4g aperçu de la galerie identique à l'application réelle", image_rendu(sortie["fichier"]).tobytes() == image_rendu("ref-galerie.png").tobytes())
    check("4h historique : « Filter Gallery »", s.appeler("doc.inspect")["history"][-1] == "Filter Gallery", s.appeler("doc.inspect")["history"][-2:])

    print("\n[5] filtres dynamiques : réédition avec aperçu")
    s.appeler("doc.new", {"width": 120, "height": 80, "background": "white"})
    ex("layer.new.layer"); ex("select.rect", x=30, y=20, width=60, height=40); ex("edit.fill", contents="color", color="#000000"); ex("select.deselect")
    ex("filter.convertForSmartFilters"); ex("filter.blur.gaussianBlur", radius=2); ex("filter.filterGallery", effects=[{"filter": "cutout"}])
    insp = s.appeler("doc.inspect")
    sf = next(c for c in insp["layers"] if c.get("smartFilters"))["smartFilters"]
    check("5a deux filtres dynamiques (flou, galerie)", [x["command"] for x in sf] == ["filter.blur.gaussianBlur", "filter.filterGallery"], sf)
    sortie, _ = PM.apercu(s, [{"command": "layer.smartFilter.setParams", "params": {"index": 0, "params": {"radius": 9}}}], 120)
    rev = s.appeler("doc.inspect")["revision"]
    ex("layer.smartFilter.setParams", index=0, params={"radius": 9})
    s.appeler("doc.render", {"path": PM.relatif("rendus/ref-sf.png"), "maxSide": 120})
    check("5b aperçu de la réédition identique à l'application réelle", image_rendu(sortie["fichier"]).tobytes() == image_rendu("ref-sf.png").tobytes())
    check("5c l'aperçu n'avait rien touché (révision avant l'application)", rev == insp["revision"], (rev, insp["revision"]))
    return True


async def routes():
    print("\n[6] routes")
    import httpx
    from app.main import app
    t = httpx.ASGITransport(app=app, client=("127.0.0.1", 5000))
    s = PM.session()
    ex = lambda c, **p: s.appeler("engine.execute", {"command": c, "params": p})
    s.appeler("doc.new", {"width": 160, "height": 100, "background": "white"})
    ex("layer.new.layer"); ex("select.rect", x=40, y=20, width=50, height=40); ex("edit.fill", contents="color", color="#336699")
    ex("layer.layerMask.revealSelection"); ex("select.rect", x=40, y=20, width=50, height=40)
    async with httpx.AsyncClient(transport=t, base_url="http://t") as c:
        r = await c.get("/api/photolab/masques", params={"maxSide": 64})
        j = r.json() if r.status_code == 200 else {}
        check("6a /masques : 200, une vignette data-URL", r.status_code == 200 and len(j.get("masques", [])) == 1
              and j["masques"][0]["png"].startswith("data:image/png;base64,"), (r.status_code, r.text[:200]))
        r = await c.get("/api/photolab/masques", params={"maxSide": 5})
        check("6b /masques : maxSide hors bornes -> 400", r.status_code == 400, r.status_code)
        r = await c.post("/api/photolab/masquer/apercu", json={"reglages": {"radius": 2}, "vue": "nb", "transparence": 50, "maxSide": 128})
        check("6c /masquer/apercu : 200, url de rendu", r.status_code == 200 and r.json().get("url", "").startswith("/api/photolab/rendus/apv-"), (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/masquer/apercu", json={"reglages": {"output": "newLayer"}, "vue": "nb"})
        check("6d /masquer/apercu : sortie imposée -> 400", r.status_code == 400, (r.status_code, r.text[:200]))
        r = await c.get("/api/photolab/galerie")
        check("6e /galerie : catalogue", r.status_code == 200 and len(r.json().get("filters", [])) == 47, (r.status_code, r.text[:200]))
        r = await c.get("/api/photolab/galerie/vignettes", params={"cles": "cutout,sponge"})
        check("6f /galerie/vignettes : deux data-URL", r.status_code == 200 and sorted(r.json().get("vignettes", {})) == ["cutout", "sponge"], (r.status_code, r.text[:200]))
        r = await c.get("/api/photolab/galerie/vignettes", params={"cles": "..\\x"})
        check("6g /galerie/vignettes : clé illisible -> 400", r.status_code == 400, (r.status_code, r.text[:200]))
        ex("select.deselect"); ex("filter.convertForSmartFilters"); ex("filter.blur.gaussianBlur", radius=2)
        r = await c.post("/api/photolab/executer", json={"command": "layer.smartFilter.setParams", "params": {"index": 0, "params": {"radius": 99999}}})
        check("6h /executer setParams hors bornes du filtre -> 400", r.status_code == 400, (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/executer", json={"command": "layer.smartFilter.setParams", "params": {"index": 0, "params": {"radius": 5}}})
        check("6i /executer setParams correct -> 200", r.status_code == 200, (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/apercu", json={"etapes": [{"command": "layer.smartFilter.setParams", "params": {"index": 0, "params": {"zorg": 5}}}]})
        check("6j /apercu setParams clé inconnue -> 400", r.status_code == 400, (r.status_code, r.text[:200]))


try:
    if moteur():
        asyncio.run(routes())
finally:
    PM.fermer()
    shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
