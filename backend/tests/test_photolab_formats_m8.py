# t257 (Photolab M8, photocraft 0.10) : formats neufs et exports — le pont.
# [1] gardes du moteur (#7023 qualité entière, #7025 document actif, index/dir posés par le pont) ;
# [2] enregistrer ORA, PDF d'une page, TIFF à calques, WebP ; ouvrir depuis l'ordinateur (/importer) ;
# [3] Calques en fichiers vers la Bibliothèque ; [4] jeux de données (importer un CSV, exporter en fichiers) ;
# [5] préréglages d'export (gardés par Deepotus : file.export.presets.* est désactivé en automation).
# Lancement : python embarqué, `python tests/test_photolab_formats_m8.py` (PHOTOCRAFT_CLI si le moteur n'est pas vendu).
import asyncio, io, os, pathlib, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt257_"))
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


def refuse(f, *a, **k):
    try:
        f(*a, **k)
        return False
    except ValueError:
        return True


class FausseSession:
    """Une séquence jouée sur un faux moteur qui CHANGE le document actif pendant l'export (#7025)."""
    def __init__(self, change=True):
        self.actif, self.appels, self.change = 0, [], change

    def sequence(self, fn, delai_s=None, pause_actions=True):
        def appel(m, p=None, delai_etape=None):
            self.appels.append((m, p))
            if m == "session.list":
                return {"active": self.actif, "documents": [{"index": 0}, {"index": 1}]}
            if m == "doc.select":
                self.actif = p["index"]
                return {}
            if m in ("doc.exportLayers", "doc.importDataSets"):
                if self.change:
                    self.actif = 1
                return {"files": ["sorties/x/hors.png", "../evade.png"], "imported": 1}
            if m == "engine.execute":
                return {"dataSets": [{"name": "A"}]}
            return {}
        return fn(appel, 1), 1


def gardes():
    print("\n[1] gardes")
    check("1a qualite_douze : 1 -> 0, 100 -> 12, 50 -> 6", (PM.qualite_douze(1), PM.qualite_douze(100), PM.qualite_douze(50)) == (0, 12, 6))
    check("1b qualite_douze : 0, 101, 50.0, True, '50' refusés (#7023 : jamais un flottant)",
          all(refuse(PM.qualite_douze, v) for v in (0, 101, 50.0, True, "50")))
    s = FausseSession()
    check("1c exporter_en_fichiers : méthode hors liste refusée", refuse(PM.exporter_en_fichiers, s, "doc.save", {}))
    check("1d exporter_en_fichiers : index ou dir venus de l'appelant refusés",
          refuse(PM.exporter_en_fichiers, s, "doc.exportLayers", {"index": 1})
          and refuse(PM.exporter_en_fichiers, s, "doc.exportLayers", {"dir": "exports"}))
    check("1e exporter_en_fichiers : quality flottante refusée (#7023)",
          refuse(PM.exporter_en_fichiers, s, "doc.exportLayers", {"quality": 6.0}))
    r, _ = PM.exporter_en_fichiers(s, "doc.exportLayers", {"format": "png"})
    sel = [p for m, p in s.appels if m == "doc.select"]
    exp = next(p for m, p in s.appels if m == "doc.exportLayers")
    check("1f #7025 : le moteur a changé le document actif -> doc.select de l'ancien, actif rétabli",
          sel == [{"index": 0}] and s.actif == 0, (sel, s.actif))
    check("1g aucun index envoyé, dir sous sorties/", "index" not in exp and exp["dir"].startswith("sorties/"), exp)
    check("1h fichiers rendus hors du dossier du lot écartés", r["fichiers"] == [], r)
    s2 = FausseSession(change=False)
    PM.exporter_en_fichiers(s2, "doc.exportLayers", {})
    check("1i actif inchangé -> aucun doc.select", not [m for m, _ in s2.appels if m == "doc.select"])
    s3 = FausseSession()
    PM.importer_jeux(s3, "entrees/j.csv", ";")
    check("1j importer_jeux : #7025 gardé, delimiter transmis, chemin relatif vérifié",
          s3.actif == 0 and next(p for m, p in s3.appels if m == "doc.importDataSets") == {"path": "entrees/j.csv", "delimiter": ";"}
          and refuse(PM.importer_jeux, s3, "../j.csv"))
    check("1k HEIC hors des formats ouverts (Q3), ORA/Krita/Affinity/PDN/EXR/DPX/DDS/raws dedans",
          "heic" not in PM.FORMATS_OUVERTURE and all(f in PM.FORMATS_OUVERTURE for f in
          ("ora", "kra", "pdn", "afphoto", "exr", "dpx", "dds", "dng", "cr2", "nef", "arw", "raf")))
    check("1l une valeur « x.ora » ou « x.kra » est un fichier pour /executer",
          PM._valeur_fichier("calque.ora") and PM._valeur_fichier("a.kra") and not PM._valeur_fichier("Leaf"))


def image(octets):
    from PIL import Image
    with Image.open(io.BytesIO(octets)) as im:
        return im.convert("RGBA").copy()


async def routes():
    import httpx
    from app.main import app
    from PIL import Image
    from app.services import storage
    from app.services.storage import LibraryAsset, async_session_factory
    await storage.init_db()
    t = httpx.ASGITransport(app=app, client=("127.0.0.1", 5000))
    s = PM.session()
    ex = lambda c, **p: s.appeler("engine.execute", {"command": c, "params": p})
    W = PM.dossier_travail()
    Image.new("RGB", (40, 30), (0, 120, 255)).save(_tmp / "images" / "bleu.png")
    async with httpx.AsyncClient(transport=t, base_url="http://t", timeout=120) as c:
        print("\n[2] enregistrer et ouvrir")
        r = await c.post("/api/photolab/ouvrir", json={"filename": "bleu.png"})
        check("2a /ouvrir bleu.png", r.status_code == 200, r.text[:200])
        ex("layer.new.layer", name="Rouge"); ex("select.rect", x=2, y=2, width=10, height=8)
        ex("edit.fill", color="#ff0000"); ex("select.deselect")
        ex("layer.new.layer", name="Cache"); ex("edit.fill", color="#00ff00"); ex("layer.hideLayers")
        n_calques = 3
        r = await c.post("/api/photolab/enregistrer", json={"format": "ora", "nom": "essai"})
        j = r.json() if r.status_code == 200 else {}
        check("2b /enregistrer ORA -> exports/essai.ora", r.status_code == 200 and j.get("fichier") == "essai.ora"
              and isinstance(j.get("avertissements"), list), (r.status_code, r.text[:300]))
        ora = (await c.get(j.get("url", "/x"))).content
        check("2c l'ORA est un zip OpenRaster (mimetype en tête)", ora[:2] == b"PK" and b"image/openraster" in ora[:200])
        r = await c.post("/api/photolab/enregistrer", json={"format": "pdf", "nom": "essai"})
        j = r.json() if r.status_code == 200 else {}
        pdf = (await c.get(j.get("url", "/x"))).content if j else b""
        check("2d /enregistrer PDF : %PDF, avertissement « aplati » remonté",
              pdf.startswith(b"%PDF") and any("flattened" in a for a in j.get("avertissements", [])), (r.status_code, r.text[:300]))
        r = await c.post("/api/photolab/enregistrer", json={"format": "tif", "calques": True, "nom": "essai"})
        j = r.json() if r.status_code == 200 else {}
        tif = (await c.get(j.get("url", "/x"))).content if j else b""
        check("2e /enregistrer TIFF à calques", r.status_code == 200 and tif[:2] in (b"II", b"MM"), (r.status_code, r.text[:300]))
        r = await c.post("/api/photolab/enregistrer", json={"format": "tif", "nom": "plat"})
        plat = (await c.get(r.json().get("url", "/x"))).content
        check("2f le TIFF à calques est plus lourd que le TIFF aplati (calques gardés)", len(tif) > len(plat), (len(tif), len(plat)))
        r = await c.post("/api/photolab/enregistrer", json={"format": "webp", "quality": 40, "nom": "w"})
        j = r.json() if r.status_code == 200 else {}
        check("2g /enregistrer WebP quality entière -> avec pertes (avertissement « lossy »)",
              r.status_code == 200 and any("lossy" in a for a in j.get("avertissements", [])), (r.status_code, r.text[:300]))
        for corps, pourquoi in (({"format": "png", "calques": True}, "calques hors TIFF"),
                                ({"format": "tif", "calques": "oui"}, "calques non booléen"),
                                ({"format": "webp", "quality": 40.0}, "quality flottante (#7023)"),
                                ({"format": "heic"}, "HEIC"), ({"format": "kra"}, "Krita en écriture")):
            r = await c.post("/api/photolab/enregistrer", json=corps)
            check(f"2h /enregistrer refusé ({pourquoi}) -> 400", r.status_code == 400, (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/copie", json={"format": "tif", "calques": True, "nom": "copie"})
        check("2i /copie TIFF à calques -> 200", r.status_code == 200, (r.status_code, r.text[:200]))
        sl = (await c.get("/api/photolab/session")).json()
        n_docs, actif = len(sl["documents"]), sl["active"]

        r = await c.post("/api/photolab/importer", params={"nom": "Mon dessin.ora"}, content=ora)
        j = r.json() if r.status_code == 200 else {}
        check("2j /importer ORA -> ouvert avec ses calques, « importe »", r.status_code == 200 and j.get("importe") is True
              and j.get("layers") == n_calques, (r.status_code, r.text[:300]))
        r = await c.post("/api/photolab/importer", params={"nom": "calques.tif"}, content=tif)
        check("2k /importer TIFF à calques -> calques relus", r.status_code == 200 and r.json().get("layers") == n_calques, r.text[:300])
        b = io.BytesIO(); Image.new("RGBA", (16, 8), (9, 9, 9, 255)).save(b, "DDS")
        r = await c.post("/api/photolab/importer", params={"nom": "texture.dds"}, content=b.getvalue())
        check("2l /importer DDS (texture) -> 16 × 8", r.status_code == 200 and (r.json().get("width"), r.json().get("height")) == (16, 8), r.text[:300])
        avant = sorted(p.name for p in (W / "entrees").iterdir())
        r = await c.post("/api/photolab/importer", params={"nom": "faux.kra"}, content=b"pas un kra")
        check("2m /importer d'un faux Krita -> 422, la copie est effacée",
              r.status_code == 422 and sorted(p.name for p in (W / "entrees").iterdir()) == avant, (r.status_code, r.text[:200]))
        for nom, corps, code in (("photo.heic", b"x", 415), ("x.exe", b"MZ", 415), ("sans", b"x", 415), ("vide.ora", b"", 400),
                                 ("../x.ora", b"x", 400), ("C:\\x.ora", b"x", 400), ("a.ora.", b"x", 400), ("a/b.ora", b"x", 400)):
            r = await c.post("/api/photolab/importer", params={"nom": nom}, content=corps)
            check(f"2n /importer {nom!r} -> {code}", r.status_code == code, (r.status_code, r.text[:200]))
        check("2o rien n'a fui hors d'entrees/ (aucun « x.ora » ailleurs dans la racine)",
              not [p for p in W.rglob("*x.ora")] and not (_tmp / "x.ora").exists())
        await c.post("/api/photolab/executer", json={"command": "file.closeAll", "params": {}})

        print("\n[3] Calques en fichiers")
        r = await c.post("/api/photolab/ouvrir", json={"filename": "bleu.png"})
        ex("layer.new.layer", name="Rouge"); ex("select.rect", x=2, y=2, width=10, height=8)
        ex("edit.fill", color="#ff0000"); ex("select.deselect")
        ex("layer.new.layer", name="Cache vert"); ex("edit.fill", color="#00ff00"); ex("layer.hideLayers")
        sl = (await c.get("/api/photolab/session")).json()
        r = await c.post("/api/photolab/calques/fichiers", json={"format": "png", "nom": "Mes calques"})
        j = r.json() if r.status_code == 200 else {}
        noms = j.get("filenames", [])
        check("3a /calques/fichiers : 2 calques visibles -> 2 images dans la Bibliothèque",
              r.status_code == 200 and len(noms) == 2 and all((_tmp / "images" / n).is_file() for n in noms), (r.status_code, r.text[:300]))
        check("3b noms : photolab_<horodatage>_Mes-calques_<calque>.png", all(n.startswith("photolab_") and "_Mes-calques_" in n for n in noms)
              and any(n.endswith("_Rouge.png") for n in noms) and any(n.endswith("_Background.png") for n in noms), noms)
        if noms:
            rouge = Image.open(_tmp / "images" / next(n for n in noms if n.endswith("_Rouge.png"))).convert("RGBA")
            check("3c le calque Rouge seul : rouge plein dans son rectangle, transparent ailleurs",
                  rouge.getpixel((5, 5)) == (255, 0, 0, 255) and rouge.getpixel((30, 25))[3] == 0, (rouge.size, rouge.getpixel((5, 5))))
        async with async_session_factory() as se:
            rows = [await se.get(LibraryAsset, n) for n in noms]
        check("3d index : source photolab, lignée « retouche » vers bleu.png",
              rows and all(x is not None and x.source == "photolab" and x.parent_filename == "bleu.png" and x.relation == "retouche" for x in rows),
              [(x.source, x.parent_filename) for x in rows if x])
        check("3e sorties/ vidé après le dépôt", not any((W / "sorties").iterdir()), list((W / "sorties").iterdir()))
        sl2 = (await c.get("/api/photolab/session")).json()
        check("3f document actif et documents inchangés", (sl2["active"], len(sl2["documents"])) == (sl["active"], len(sl["documents"])))
        r = await c.post("/api/photolab/calques/fichiers", json={"format": "png", "visibles": False})
        check("3g visibles: false -> 3 images (le calque caché aussi)", r.status_code == 200 and len(r.json()["filenames"]) == 3, r.text[:300])
        r1 = await c.post("/api/photolab/calques/fichiers", json={"format": "jpg", "quality": 1, "nom": "q1"})
        r2 = await c.post("/api/photolab/calques/fichiers", json={"format": "jpg", "quality": 100, "nom": "q100"})
        t1 = sum((_tmp / "images" / n).stat().st_size for n in r1.json().get("filenames", []))
        t2 = sum((_tmp / "images" / n).stat().st_size for n in r2.json().get("filenames", []))
        check("3h jpg : quality 1 plus léger que quality 100 (échelle 0..12 du moteur)", r1.status_code == r2.status_code == 200 and t1 < t2, (t1, t2))
        for corps, pourquoi in (({"format": "tif"}, "format"), ({"format": "png", "quality": 50}, "quality sur png"),
                                ({"format": "jpg", "quality": 50.5}, "quality flottante"), ({"format": "png", "visibles": "oui"}, "visibles"),
                                ({"format": "png", "dir": "C:/"}, "clé inconnue dir"), ({"format": "png", "index": 0}, "clé inconnue index")):
            r = await c.post("/api/photolab/calques/fichiers", json=corps)
            check(f"3i /calques/fichiers refusé ({pourquoi}) -> 400", r.status_code == 400, (r.status_code, r.text[:200]))

        print("\n[4] jeux de données")
        r = await c.post("/api/photolab/jeux/fichiers", json={"format": "png"})
        check("4a /jeux/fichiers sans jeu de données -> 400", r.status_code == 400, (r.status_code, r.text[:200]))
        ins = (await c.get("/api/photolab/inspecter")).json()
        rouge_id = next(x["id"] for x in ins["layers"] if x["name"] == "Rouge")
        r = await c.post("/api/photolab/executer", json={"command": "image.variables.define",
                                                          "params": {"defs": [{"name": "rouge", "layer": rouge_id, "type": "visibility"}]}})
        check("4b Image › Variables › Définir (vérifiée clé par clé) -> 200", r.status_code == 200, r.text[:200])
        for cid, p, pourquoi in (
                ("image.variables.define", {"defs": [{"name": "p", "layer": rouge_id, "type": "pixelReplacement"}]}, "remplacement de pixels (chemin)"),
                ("image.variables.define", {"defs": [{"name": "p", "layer": rouge_id, "type": "visibility", "method": "fit"}]}, "clé de pixels"),
                ("image.variables.define", {"defs": [{"name": " ", "layer": rouge_id, "type": "visibility"}]}, "nom vide"),
                ("image.variables.define", {"defs": [{"name": "a", "layer": rouge_id, "type": "visibility"}] * 2}, "doublon"),
                ("image.variables.define", {"defs": [{"name": "a", "layer": "Rouge", "type": "visibility"}]}, "calque par nom"),
                ("image.variables.define", {"defs": "x"}, "pas une liste"),
                ("image.variables.dataSets", {"dataSets": [{"name": "A", "values": [{"variable": "rouge", "kind": "pixels", "value": "C:/x.png"}]}]}, "pixels"),
                ("image.variables.dataSets", {"dataSets": [{"name": "A", "values": [{"variable": "rouge", "kind": "visibility", "value": "oui"}]}]}, "visibilité non booléenne"),
                ("image.variables.dataSets", {"dataSets": [{"name": "A", "values": []}, {"name": "A", "values": []}]}, "jeux en double"),
                ("image.variables.dataSets", {"dataSets": [], "append": "oui"}, "append"),
                ("image.applyDataSet", {}, "ni nom ni index"), ("image.applyDataSet", {"name": "A", "index": 0}, "les deux"),
                ("image.applyDataSet", {"index": -1}, "index négatif")):
            r = await c.post("/api/photolab/executer", json={"command": cid, "params": p})
            check(f"4b2 /executer {cid} refusé ({pourquoi}) -> 400", r.status_code == 400, (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/jeux/importer", json={"csv": "Jeu;rouge\nAvec;true\nSans;false\n", "separateur": ";"})
        j = r.json() if r.status_code == 200 else {}
        check("4c /jeux/importer CSV (;) -> 2 jeux", r.status_code == 200 and j.get("imported") == 2 and len(j.get("dataSets", [])) == 2,
              (r.status_code, r.text[:300]))
        check("4d le CSV n'est pas resté sous entrees/", not list((W / "entrees").glob("jeux-*.csv")))
        jeux = j.get("dataSets", [])
        r = await c.post("/api/photolab/jeux/fichiers", json={"format": "png", "nom": "affiche"})
        j = r.json() if r.status_code == 200 else {}
        noms = j.get("filenames", [])
        check("4e /jeux/fichiers -> une image par jeu, nommée d'après le jeu",
              r.status_code == 200 and len(noms) == 2 and all(any(n.endswith(f"_{PM_base(x)}.png") for n in noms) for x in jeux), (r.text[:300], jeux))
        if len(noms) == 2:
            a = Image.open(_tmp / "images" / noms[0]).convert("RGBA"); b = Image.open(_tmp / "images" / noms[1]).convert("RGBA")
            check("4f les deux jeux diffèrent (calque Rouge montré / caché)", a.getpixel((5, 5)) != b.getpixel((5, 5)), (a.getpixel((5, 5)), b.getpixel((5, 5))))
        r = await c.post("/api/photolab/jeux/fichiers", json={"format": "png", "jeux": [jeux[-1]] if jeux else ["?"]})
        n1 = r.json().get("filenames", []) if r.status_code == 200 else []
        check("4g un seul jeu choisi -> une image à son nom", len(n1) == 1 and jeux and n1[0].endswith(f"_{PM_base(jeux[-1])}.png"), (r.status_code, r.text[:300]))
        r = await c.post("/api/photolab/executer", json={"command": "image.applyDataSet", "params": {"name": jeux[-1] if jeux else "?"}})
        hist = (await c.get("/api/photolab/inspecter")).json().get("history", [])
        check("4g2 Appliquer un jeu -> un état d'historique « Apply Data Set »", r.status_code == 200 and hist and hist[-1].startswith("Apply Data Set"),
              (r.status_code, r.text[:200], hist[-2:]))
        r = await c.post("/api/photolab/executer", json={"command": "image.variables.dataSets",
                                                          "params": {"dataSets": [{"name": "Trois", "values": [{"variable": "rouge", "kind": "visibility", "value": True}]}], "append": True}})
        r2 = await c.post("/api/photolab/executer", json={"command": "variables.list", "params": {}})
        check("4g3 Jeux de données (ajout) puis variables.list -> 3 jeux", r.status_code == 200 and len(r2.json().get("dataSets", [])) == 3, (r.text[:200], r2.text[:300]))
        for corps, pourquoi in (({"format": "png", "jeux": []}, "liste vide"), ({"format": "png", "jeux": "A"}, "pas une liste"),
                                ({"format": "png", "naming": "{name}"}, "naming venu de l'écran"), ({"format": "pdf"}, "format")):
            r = await c.post("/api/photolab/jeux/fichiers", json=corps)
            check(f"4h /jeux/fichiers refusé ({pourquoi}) -> 400", r.status_code == 400, (r.status_code, r.text[:200]))
        for corps, code in (({"csv": ""}, 400), ({"csv": "a,b", "separateur": "|"}, 400), ({"csv": "a" * (1024 * 1024 + 1)}, 413),
                            ({"csv": "a,b", "path": "C:/x.csv"}, 400)):
            r = await c.post("/api/photolab/jeux/importer", json=corps)
            check(f"4i /jeux/importer {str(corps)[:40]} -> {code}", r.status_code == code, (r.status_code, r.text[:200]))

        print("\n[5] préréglages d'export")
        r = await c.get("/api/photolab/export/prereglages")
        check("5a aucun préréglage au départ", r.status_code == 200 and r.json() == {"prereglages": []}, r.text[:200])
        liste = [{"nom": "Web léger", "format": "webp", "quality": 70}, {"nom": "Calques", "format": "tif", "calques": True}]
        r = await c.put("/api/photolab/export/prereglages", json={"prereglages": liste})
        r2 = await c.get("/api/photolab/export/prereglages")
        check("5b écrits puis relus à l'identique", r.status_code == 200 and r2.json()["prereglages"] == liste, r2.text[:300])
        for l, pourquoi in (([{"nom": "a", "format": "png"}, {"nom": "A", "format": "jpg"}], "doublon sans casse"),
                            ([{"nom": "a", "format": "exe"}], "format"), ([{"nom": "a", "format": "png", "calques": True}], "calques hors TIFF"),
                            ([{"nom": "", "format": "png"}], "nom vide"), ([{"nom": "a", "format": "jpg", "quality": 70.0}], "quality flottante"),
                            ([{"nom": "a", "format": "png", "path": "x"}], "clé inconnue"), ([{"nom": f"n{i}", "format": "png"} for i in range(51)], "51")):
            r = await c.put("/api/photolab/export/prereglages", json={"prereglages": l})
            check(f"5c refusé ({pourquoi}) -> 400, liste gardée", r.status_code == 400
                  and (await c.get("/api/photolab/export/prereglages")).json()["prereglages"] == liste, (r.status_code, r.text[:200]))
        (W / "prereglages-export.json").write_text("{abîmé", "utf-8")
        r = await c.get("/api/photolab/export/prereglages")
        check("5d fichier abîmé -> liste vide, jamais un 500", r.status_code == 200 and r.json()["prereglages"] == [], (r.status_code, r.text[:200]))


def PM_base(nom):
    from app.api.photolab_routes import _base_sure
    return _base_sure(nom, "element")


try:
    gardes()
    PM.fermer()
    PM.FABRIQUE = None
    try:
        cli = PM.chemin_cli()
        check("0 le binaire photocraft-cli est présent (sinon les sections 2 à 5 sont rouges)", cli.is_file(), cli)
        asyncio.run(routes())
    except PM.MoteurAbsent as e:
        check("0 le binaire photocraft-cli est présent (sinon les sections 2 à 5 sont rouges)", False, e)
finally:
    PM.fermer()
    shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
