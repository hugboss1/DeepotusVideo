# t158 (Photolab parité L8) : Fichier sûr et Image › Mode sous liste blanche — le pont.
# [1] liste blanche (commandes rouvertes une à une, profils intégrés, bichromie, table, infos, flamme) ;
# [2] Image › Mode sur le vrai moteur (profils, grisés) ; [3] compositions (copie, export de calque, Revenir, Placer) ;
# [4] routes.
# Lancement : python embarqué, `python tests/test_photolab_fichier_mode.py` (PHOTOCRAFT_CLI si le moteur n'est pas vendu).
import asyncio, os, pathlib, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt158_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_moteur as PM                # noqa: E402
from app.services import photolab_registre as PR              # noqa: E402

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


def image(chemin):
    from PIL import Image
    with Image.open(chemin) as im:
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

    print("\n[1] liste blanche")
    for cid, p in (("file.closeAll", {}), ("file.closeOthers", {}), ("file.closeOthers", {"document": 0}),
                   ("file.close", {"document": 1}), ("file.fileInfo", {}),
                   ("file.fileInfo", {"title": "Été / hiver", "description": "a/b\\c C:\\x.png", "keywords": ["a", "b"],
                                      "copyrightStatus": "copyrighted", "copyrightUrl": "https://exemple.org/licence"}),
                   ("file.fileInfo", {"keywords": "a; b", "copyrightUrl": ""}),
                   ("image.mode.rgb", {}), ("image.mode.rgb", {"profile": "srgb", "intent": "perceptual", "bpc": False}),
                   ("image.mode.grayscale", {"profile": "gray-gamma-2.2"}), ("image.mode.cmyk", {"profile": "coated-cmyk"}),
                   ("image.mode.lab", {"profile": "working"}), ("image.mode.bits16", {}), ("image.mode.multichannel", {}),
                   ("image.mode.bitmap", {"method": "halftone", "frequency": 60, "angle": 30, "shape": "line"}),
                   ("image.mode.indexedColor", {"palette": "web", "colors": 16, "dither": "none"}),
                   ("image.mode.duotone", {"type": "tritone", "inks": [{"name": "Noir", "color": "#000000"},
                                                                      {"name": "R", "color": "#ff0000", "curve": [[0, 0], [50, 70], [100, 100]]},
                                                                      {"name": "B", "color": "#0000ff"}]}),
                   ("image.mode.colorTable", {}), ("image.mode.colorTable", {"table": "spectrum"}),
                   ("image.mode.colorTable", {"entries": {"0": "#123456", "255": "#ffffff"}, "transparent": 3}),
                   ("image.mode.colorTable", {"colors": ["#000000", "#ffffff"], "transparent": None}),
                   ("filter.render.flame", {"path": "Ligne"}), ("filter.render.flame", {"path": "work", "length": 80}),
                   ("filter.distort.displace", {"mapDocument": 0, "horizontal": 5}),
                   ("image.adjustments.matchColor", {"source": 1, "fade": 20, "neutralize": True})):
        r = admis(reg, cid, p)
        check(f"1a admis : {cid} {str(p)[:70]}", r is True, r)
    for cid, p, pourquoi in (
            ("file.saveACopy", {"path": "exports/a.png"}, "famille toujours refusée"),
            ("file.revert", {}, "famille toujours refusée"), ("file.placeEmbedded", {"path": "x.png"}, "refusée"),
            ("file.openAs", {"path": "x.png"}, "refusée"), ("file.exit", {}, "refusée"),
            ("image.mode.rgb", {"profile": "C:/Windows/x.icc"}, "profil = chemin absolu"),
            ("image.mode.rgb", {"profile": "../../x.icc"}, "profil = remontée"),
            ("image.mode.rgb", {"profile": "profils\\x.icm"}, "profil = antislash"),
            ("image.mode.rgb", {"profile": "/path/to/profile.icc"}, "profil = valeur d'exemple du registre"),
            ("image.mode.rgb", {"profile": "<builtin id>"}, "profil = gabarit du registre"),
            ("image.mode.rgb", {"profile": "sgray"}, "profil d'un autre espace"),
            ("image.mode.rgb", {"profile": "sRGB"}, "casse : l'écran envoie l'id exact"),
            ("image.mode.cmyk", {"profile": "srgb"}, "profil RVB pour CMJN"),
            ("image.mode.rgb", {"zorg": 1}, "clé inconnue"),
            ("image.mode.bitmap", {"frequency": 5000}, "hors bornes"),
            ("image.mode.duotone", {"type": "tritone", "inks": [{"name": "N", "color": "#000000"}]}, "1 encre pour tritone"),
            ("image.mode.duotone", {"inks": [{"name": "N", "color": "#000000"}]}, "1 encre pour duotone (défaut)"),
            ("image.mode.duotone", {"type": "monotone", "inks": [{"name": "N", "color": "noir"}]}, "couleur illisible"),
            ("image.mode.duotone", {"type": "monotone", "inks": [{"name": "", "color": "#000000"}]}, "nom vide"),
            ("image.mode.duotone", {"type": "monotone", "inks": [{"name": "N", "color": "#000000", "curve": [[0, 0], [0, 50]]}]}, "entrées non croissantes"),
            ("image.mode.duotone", {"type": "monotone", "inks": [{"name": "N", "color": "#000000", "curve": [[0, 0], [100, 150]]}]}, "sortie > 100"),
            ("image.mode.duotone", {"type": "monotone", "inks": [{"name": "N", "color": "#000000", "path": "x.icc"}]}, "clé d'encre inconnue"),
            ("image.mode.duotone", {"type": "zorg", "inks": []}, "type inconnu"),
            ("image.mode.colorTable", {"entries": {"256": "#000000"}}, "index 256"),
            ("image.mode.colorTable", {"entries": {"01": "#000000"}}, "index écrit « 01 »"),
            ("image.mode.colorTable", {"colors": ["#000000"] * 257}, "257 couleurs"),
            ("image.mode.colorTable", {"transparent": -1}, "transparence -1"),
            ("image.mode.colorTable", {"table": "C:/x.act"}, "table = fichier"),
            ("file.fileInfo", {"copyrightUrl": "file:///C:/Windows/win.ini"}, "URL file://"),
            ("file.fileInfo", {"copyrightUrl": "javascript:alert(1)"}, "URL javascript:"),
            ("file.fileInfo", {"title": "x" * 2001}, "titre trop long"),
            ("file.fileInfo", {"keywords": ["a"] * 65}, "65 mots-clés"),
            ("file.fileInfo", {"path": "x"}, "clé inconnue"),
            ("file.fileInfo", {"copyrightStatus": "libre"}, "statut inconnu"),
            ("filter.render.flame", {"path": "exports/x.pcraft"}, "tracé = fichier"),
            ("filter.render.flame", {"path": "C:\\x"}, "tracé = chemin"),
            ("filter.render.flame", {"path": ""}, "tracé vide"),
            ("filter.distort.displace", {"mapPath": "exports/a.pcraft"}, "carte de déplacement = fichier"),
            ("filter.distort.displace", {"mapDocument": -1}, "document négatif")):
        r = admis(reg, cid, p)
        check(f"1b refusé ({pourquoi}) : {cid}", r is not True, r)
    check("1c PERMIS_REFUSES ne rouvre que des ids sous un préfixe refusé, connus du registre",
          all(c.lower().startswith(PM.PREFIXES_REFUSES) and c in reg for c in PM.PERMIS_REFUSES), sorted(PM.PERMIS_REFUSES))
    # t159 : edit.presets.exportImportPresets a une clé `data` (CLES_CHEMIN) qui porte des DONNÉES, jamais un chemin :
    # vérifiée clé par clé par photolab_registre._v_echange (banc test_photolab_preferences 4c-4d)
    check("1d aucun permis n'a de clé chemin au registre (hors `data` de l'échange de préréglages, vérifiée à part)",
          not any(c["cle"].lower() in PR.CLES_CHEMIN for i in PM.PERMIS_REFUSES for c in reg[i]["champs"]
                  if not (i == "edit.presets.exportImportPresets" and c["cle"] == "data")))
    liste = {"paths": [{"name": "Ligne"}], "workPath": {"knots": 2}}
    check("1e verifier_trace : nom connu / work admis", not refuse(PM.verifier_trace, {"path": "Ligne"}, liste)
          and not refuse(PM.verifier_trace, {"path": "work"}, liste) and not refuse(PM.verifier_trace, {}, liste))
    check("1f verifier_trace : nom inconnu refusé, work sans tracé de travail refusé",
          refuse(PM.verifier_trace, {"path": "Nope"}, liste) and refuse(PM.verifier_trace, {"path": "work"}, {"paths": []}))

    print("\n[2] Image › Mode sur le vrai moteur")
    ap = lambda m, p=None: s.appeler(m, p or {})
    ex = lambda c, **p: ap("engine.execute", {"command": c, "params": p})
    infos = ex("edit.profileInfo") or {}
    integres = {b["id"] for b in infos.get("builtins") or []}
    attendus = set().union(*PR.PROFILS_MODE.values()) - {"working"}
    check("2a PROFILS_MODE = profils intégrés du moteur (edit.profileInfo)", integres == attendus, (sorted(integres), sorted(attendus)))
    ap("doc.new", {"width": 40, "height": 30, "background": "white", "name": "M"})
    rates = []
    for cid, profils in PR.PROFILS_MODE.items():
        for pr in profils:
            try:
                PM.commande_autorisee(cid, {"profile": pr}, reg)
                ex(cid, profile=pr)
            except Exception as e:  # noqa: BLE001
                rates.append((cid, pr, str(e)[:80]))
        ex("image.mode.rgb")
    check("2b chaque profil admis convertit vraiment", not rates, rates)
    en = lambda: {c["id"]: c.get("enabled") for c in (ap("engine.commands") or [])}
    e = en()
    check("2c RVB : Bitmap, Bichromie, Table grisés par le moteur",
          e["image.mode.bitmap"] is False and e["image.mode.duotone"] is False and e["image.mode.colorTable"] is False
          and e["image.mode.grayscale"] is True, {k: e[k] for k in ("image.mode.bitmap", "image.mode.duotone", "image.mode.colorTable")})
    ex("image.mode.grayscale")
    p = {"type": "duotone", "inks": [{"name": "Noir", "color": "#000000"}, {"name": "Rouge", "color": "#cc2200", "curve": [[0, 0], [100, 60]]}]}
    PM.commande_autorisee("image.mode.duotone", p, reg)
    r = ex("image.mode.duotone", **p)
    insp = ap("doc.inspect")
    check("2d bichromie : 2 encres nommées, mode Duotone, étape « Duotone »",
          (r or {}).get("inks") == ["Noir", "Rouge"] and insp["mode"] == "Duotone" and insp["history"][-1] == "Duotone", (r, insp["mode"]))
    ex("image.mode.grayscale"); ex("image.mode.rgb"); ex("image.mode.indexedColor", colors=8)
    n = len(ap("doc.inspect")["history"])
    lu = ex("image.mode.colorTable")
    check("2e table des couleurs : lecture sans étape", isinstance((lu or {}).get("colors"), list) and len(ap("doc.inspect")["history"]) == n, lu)
    ex("image.mode.colorTable", entries={"0": "#123456"})
    check("2f table : une entrée réécrite, étape « Color Table »",
          ex("image.mode.colorTable")["colors"][0] == "#123456" and ap("doc.inspect")["history"][-1] == "Color Table")
    n = len(ap("doc.inspect")["history"])
    ex("file.fileInfo")
    ex("file.fileInfo", title="Titre", copyrightUrl="https://exemple.org/l")
    lu = ex("file.fileInfo")
    check("2g infos : lecture sans étape, écriture = une étape « File Info », relue",
          lu.get("title") == "Titre" and lu.get("copyrightUrl") == "https://exemple.org/l"
          and ap("doc.inspect")["history"][n:] == ["File Info"], (lu, ap("doc.inspect")["history"][n:]))
    ap("doc.close", {"index": ap("session.list")["active"]})
    return True


def compositions():
    print("\n[3] compositions (vrai moteur)")
    s = PM.session()
    ap = lambda m, p=None: s.appeler(m, p or {})
    ex = lambda c, **p: ap("engine.execute", {"command": c, "params": p})
    W = PM.dossier_travail()
    ap("doc.new", {"width": 64, "height": 48, "background": "white", "name": "C"})
    ex("layer.new.layer"); ex("select.rect", x=10, y=10, width=20, height=10); ex("edit.fill", color="#ff0000"); ex("select.deselect")
    rouge = ap("doc.inspect")["activeLayer"]
    ex("layer.new.layer"); ex("select.rect", x=40, y=30, width=8, height=8); ex("edit.fill", color="#00ff00"); ex("select.deselect")
    ex("select.rect", x=1, y=1, width=5, height=5)
    avant = ap("doc.inspect"); sl_avant = ap("session.list")
    fichier, _ = PM.copie_document(s, "png", "copie", None)
    apres = ap("doc.inspect"); sl = ap("session.list")
    check("3a copie : fichier sous exports/", (W / "exports" / fichier).is_file(), fichier)
    check("3b copie : l'original garde révision, historique, sélection, calque actif, documents",
          (apres["revision"], apres["history"], apres["hasSelection"], apres["activeLayer"]) ==
          (avant["revision"], avant["history"], avant["hasSelection"], avant["activeLayer"])
          and sl["documents"] == sl_avant["documents"] and sl["active"] == sl_avant["active"], (apres["history"][-3:], sl))
    ap("doc.render", {"path": "rendus/c-ref.png"})
    check("3c copie : pixels égaux au rendu de l'original", image(W / "exports" / fichier).tobytes() == image(W / "rendus" / "c-ref.png").tobytes())
    check("3d copie : nom libre (-2) au deuxième essai", PM.copie_document(s, "png", "copie", None)[0] == "copie-2.png")
    ex("select.deselect")

    f, _ = PM.exporter_calque(s, rouge, "png", "rouge", 100, None)
    im = image(W / "exports" / f)
    check("3e export de calque : le calque seul, rogné (20 × 10, rouge plein)",
          im.size == (20, 10) and im.getpixel((0, 0)) == (255, 0, 0, 255) and im.getpixel((19, 9)) == (255, 0, 0, 255), (im.size, im.getpixel((0, 0))))
    f, _ = PM.exporter_calque(s, None, "png", "vert", 50, None)
    im = image(W / "exports" / f)
    check("3f export : calque actif (vert 8 × 8) à 50 % -> 4 × 4", im.size == (4, 4) and im.getpixel((1, 1))[1] == 255, (im.size,))
    ex("layer.new.layer")
    vide = ap("doc.inspect")["activeLayer"]
    check("3g export d'un calque vide -> ValueError, documents inchangés",
          refuse(PM.exporter_calque, s, vide, "png", "vide", 100, None) and ap("session.list")["documents"] == sl_avant["documents"][:0] + ap("session.list")["documents"]
          and len(ap("session.list")["documents"]) == len(sl_avant["documents"]))
    check("3h export : calque inconnu -> ValueError", refuse(PM.exporter_calque, s, 99999, "png", "x", 100, None))
    ex("layer.delete", layer=vide)
    ex("layer.hideLayers", layer=rouge)
    f, _ = PM.exporter_calque(s, rouge, "jpg", "cache", 100, 80)
    check("3i export d'un calque MASQUÉ : il est montré sur la copie, reste masqué dans l'original",
          image(W / "exports" / f).size == (20, 10) and next(c for c in ap("doc.inspect")["layers"] if c["id"] == rouge)["visible"] is False)
    ex("layer.showLayers", layer=rouge)

    check("3j Revenir sans fichier -> ValueError", refuse(PM.revenir, s))
    ap("doc.save", {"path": "exports/C.pcraft", "format": "pcraft"})
    ap("doc.render", {"path": "rendus/c-sauve.png"})
    ex("edit.fill", color="#0000ff")
    n_docs = len(ap("session.list")["documents"])
    sl, _ = PM.revenir(s)
    ap("doc.render", {"path": "rendus/c-revenu.png"})
    insp = ap("doc.inspect")
    check("3k Revenir : pixels = version enregistrée, même nombre de documents, document rouvert actif",
          image(W / "rendus" / "c-revenu.png").tobytes() == image(W / "rendus" / "c-sauve.png").tobytes()
          and len(sl["documents"]) == n_docs and next(d for d in sl["documents"] if d["index"] == sl["active"])["path"] == "exports/C.pcraft",
          sl)
    check("3l Revenir : historique repart de l'ouverture", insp["history"] == ["Open"], insp["history"])

    from PIL import Image
    Image.new("RGB", (30, 20), (0, 0, 255)).save(W / "entrees" / "petit.png")
    Image.new("RGB", (200, 50), (255, 200, 0)).save(W / "entrees" / "grand.png")
    r, _ = PM.placer(s, "entrees/petit.png", "petit")
    insp = ap("doc.inspect")
    c = next(x for x in insp["layers"] if x["id"] == r["layer"])
    check("3m Placer : objet dynamique nommé, centré (bounds [x, y, l, h] = [17, 14, 30, 20]), l'image ouverte refermée",
          c["kind"] == "Smart Object" and c["name"] == "petit" and c["bounds"] == [17, 14, 30, 20]
          and len(ap("session.list")["documents"]) == n_docs, c)
    r, _ = PM.placer(s, "entrees/grand.png", "grand")
    c = next(x for x in ap("doc.inspect")["layers"] if x["id"] == r["layer"])
    b = c["bounds"]
    check("3n Placer : plus grand que la toile -> réduit à la largeur (64 × 16), centré verticalement",
          b == [0, 16, 64, 16], b)
    check("3o Placer : chemin refusé", refuse(PM.placer, s, "../x.png", "x") and refuse(PM.placer, s, "C:/x.png", "x"))
    ap("doc.close", {"index": ap("session.list")["active"]})


async def routes():
    print("\n[4] routes")
    import httpx
    from app.main import app
    from PIL import Image
    from app.services import storage
    await storage.init_db()                                    # l'index de la Bibliothèque (lignée de /copie)
    t = httpx.ASGITransport(app=app, client=("127.0.0.1", 5000))
    s = PM.session()
    ex = lambda c, **p: s.appeler("engine.execute", {"command": c, "params": p})
    Image.new("RGB", (30, 20), (0, 120, 255)).save(_tmp / "images" / "bleu.png")
    async with httpx.AsyncClient(transport=t, base_url="http://t") as c:
        r = await c.post("/api/photolab/ouvrir", json={"filename": "bleu.png"})
        check("4a /ouvrir bleu.png", r.status_code == 200, (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/copie", json={"format": "png", "nom": "ma copie"})
        j = r.json() if r.status_code == 200 else {}
        check("4b /copie télécharger : url d'export", r.status_code == 200 and j.get("url", "").startswith("/api/photolab/exports/ma-copie"), (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/copie", json={"format": "jpg", "quality": 80, "destination": "bibliotheque"})
        j = r.json() if r.status_code == 200 else {}
        check("4c /copie Bibliothèque : déposée sous photolab_…", r.status_code == 200 and (_tmp / "images" / j.get("filename", "?")).is_file()
              and j["filename"].startswith("photolab_"), (r.status_code, r.text[:200]))
        from app.services.storage import LibraryAsset, async_session_factory
        async with async_session_factory() as se:
            row = await se.get(LibraryAsset, j.get("filename", "?"))
        check("4d /copie Bibliothèque : lignée « retouche » vers bleu.png", row is not None and row.parent_filename == "bleu.png"
              and row.relation == "retouche", row and (row.parent_filename, row.relation))
        for corps, pourquoi in (({"format": "psd", "destination": "bibliotheque"}, "psd vers la Bibliothèque"),
                                ({"format": "exe"}, "format inconnu"), ({"format": "png", "destination": "C:/"}, "destination"),
                                ({"format": "png", "quality": 0}, "qualité 0")):
            r = await c.post("/api/photolab/copie", json=corps)
            check(f"4e /copie refusée ({pourquoi}) -> 400", r.status_code == 400, (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/calque/exporter", json={"format": "png", "echelle": 200})
        j = r.json() if r.status_code == 200 else {}
        check("4f /calque/exporter : 200 %", r.status_code == 200 and j.get("url"), (r.status_code, r.text[:200]))
        r2 = await c.get(j.get("url", "/x"))
        check("4g l'export se télécharge, 60 × 40", r2.status_code == 200 and Image.open(__import__("io").BytesIO(r2.content)).size == (60, 40))
        for corps, pourquoi in (({"format": "tif"}, "format"), ({"format": "png", "echelle": 0}, "échelle 0"),
                                ({"format": "png", "layer": "2"}, "layer texte"), ({"format": "png", "layer": 99999}, "calque inconnu")):
            r = await c.post("/api/photolab/calque/exporter", json=corps)
            check(f"4h /calque/exporter refusé ({pourquoi}) -> 400", r.status_code == 400, (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/revenir")
        check("4i /revenir d'un document ouvert de la Bibliothèque -> 200 (fichier entrees/)", r.status_code == 200, (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/nouveau", json={"width": 50, "height": 40})
        r = await c.post("/api/photolab/revenir")
        check("4j /revenir d'un document neuf -> 400", r.status_code == 400, (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/placer", json={"filename": "bleu.png"})
        check("4k /placer bleu.png -> objet dynamique", r.status_code == 200 and r.json().get("layer"), (r.status_code, r.text[:200]))
        for nom, code in (("../x.png", 400), ("absent.png", 404), ("C:\\x.png", 400)):
            r = await c.post("/api/photolab/placer", json={"filename": nom})
            check(f"4l /placer {nom!r} -> {code}", r.status_code == code, (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/executer", json={"command": "filter.render.flame", "params": {"path": "Nope"}})
        check("4m /executer flamme sur tracé inconnu -> 400", r.status_code == 400, (r.status_code, r.text[:200]))
        ex("path.set", name="work", path={"subpaths": [{"closed": False, "knots": [[5, 30], [45, 5]]}]})
        r = await c.post("/api/photolab/apercu", json={"etapes": [{"command": "filter.render.flame", "params": {"path": "Nope"}}]})
        check("4n /apercu flamme sur tracé inconnu -> 400", r.status_code == 400, (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/executer", json={"command": "filter.render.flame", "params": {"path": "work"}})
        check("4o /executer flamme sur le tracé de travail -> 200, usedPath", r.status_code == 200 and r.json().get("usedPath") is True, (r.status_code, r.text[:200]))
        for cid, p in (("file.saveACopy", {"path": "exports/x.png"}), ("file.revert", {}), ("image.mode.rgb", {"profile": "C:/x.icc"})):
            r = await c.post("/api/photolab/executer", json={"command": cid, "params": p})
            check(f"4p /executer {cid} -> 400", r.status_code == 400, (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/executer", json={"command": "image.mode.cmyk", "params": {}})
        check("4q /executer image.mode.cmyk -> 200", r.status_code == 200, (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/executer", json={"command": "file.closeOthers", "params": {}})
        r2 = await c.get("/api/photolab/session")
        check("4r /executer file.closeOthers -> un seul document", r.status_code == 200 and len(r2.json()["documents"]) == 1, r2.text[:200])
        r = await c.post("/api/photolab/executer", json={"command": "file.closeAll", "params": {}})
        r2 = await c.get("/api/photolab/session")
        check("4s /executer file.closeAll -> aucun document", r.status_code == 200 and r2.json()["documents"] == [], r2.text[:200])


try:
    if moteur():
        compositions()
        asyncio.run(routes())
finally:
    PM.fermer()
    shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
