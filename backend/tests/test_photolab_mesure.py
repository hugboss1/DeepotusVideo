# t160 (Photolab parité L10) : mesure, comptage, notes, tranches — le pont.
# [1] liste blanche (formes alternatives, textes libres bornés, refus) ; [2] vrai moteur : noms d'étapes, analyse,
# CSV du journal, import de notes d'un autre document ; [3] routes.
# Lancement : python embarqué, `python tests/test_photolab_mesure.py` (PHOTOCRAFT_CLI si le moteur n'est pas vendu).
import asyncio, csv, io, os, pathlib, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt160_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
RACINE = BACKEND.parent
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
        return str(e)


def liste_blanche(reg):
    print("\n[1] liste blanche")
    bons = [("count.add", {"x": 1, "y": 2}), ("count.add", {"x": 1.5, "y": 2, "group": 1}),
            ("count.remove", {"x": 1, "y": 2, "radius": 6}), ("count.remove", {"index": 0, "group": 0}),
            ("count.move", {"index": 0, "group": 0, "to": [3, 4]}), ("count.move", {"x": 1, "y": 2, "to": [3, 4]}),
            ("count.clear", {"group": "all"}), ("count.clear", {}), ("count.newGroup", {"name": "a/b.png", "color": "#00ff00"}),
            ("count.setGroup", {"group": 0, "name": "Bleus", "markerSize": 10, "labelSize": 72, "visible": False, "active": True}),
            ("count.deleteGroup", {"group": 1}),
            ("notes.add", {"x": 1, "y": 2, "text": "voir C:\\x\\a.png ou a/b", "author": "Moi", "color": "#ffff80", "open": True}),
            ("notes.add", {"x": 1, "y": 2, "text": "ligne 1\nligne 2\tfin"}),
            ("notes.set", {"index": 0, "text": "x", "x": 3, "y": 4}), ("notes.delete", {"index": 0}), ("notes.delete", {"all": True}),
            ("slice.new", {"rect": [1, 2, 3, 4]}), ("slice.new", {"x": 1, "y": 2, "width": 3, "height": 4, "name": "haut"}),
            ("slice.set", {"slice": 1, "rect": [1, 2, 3, 4]}),
            ("slice.set", {"slice": 1, "name": "haut", "url": "https://exemple.org/a?b=c", "target": "_blank", "alt": "x", "message": "m",
                           "kind": "image", "background": "#ffffff"}),
            ("slice.set", {"number": 2, "kind": "noImage", "cellText": "<b>x</b>", "cellTextIsHtml": True, "background": "none"}),
            ("slice.divide", {"slice": 1, "horizontal": 2, "vertical": 3}), ("slice.promote", {"number": 2}), ("slice.delete", {"slice": 1}),
            ("slice.delete", {"slices": [1, 2]}), ("measurementLog.delete", {"rows": [1, 2]}), ("measurementLog.delete", {"all": True}),
            ("image.analysis.rulerTool", {"start": [1, 2], "end": [3, 4], "protractor": [5, 6]}), ("image.analysis.rulerTool", {"clear": True}),
            ("image.analysis.recordMeasurements", {"source": "count"}), ("measurementLog.list", {}), ("slice.fromGuides", {}),
            ("view.lockSlices", {"on": True})]
    for cid, p in bons:
        r = admis(reg, cid, p)
        check(f"1a admis : {cid} {sorted(p)}", r is True, r)
    mauvais = [("count.add", {"x": 1}, "y manquant"), ("count.add", {"x": "1", "y": 2}, "x texte"), ("count.add", {"x": True, "y": 2}, "x booléen"),
               ("count.add", {"x": 2e6, "y": 2}, "hors toile"), ("count.add", {"x": 1, "y": 2, "path": "a"}, "clé inconnue"),
               ("count.remove", {"index": 0, "x": 1, "y": 2}, "index ET point"), ("count.remove", {"x": 1, "y": 2, "group": 0}, "group avec un point"),
               ("count.remove", {"index": 0, "radius": 3}, "radius avec index"), ("count.move", {"index": 0}, "to manquant"),
               ("count.move", {"index": 0, "to": [1]}, "to tronqué"), ("count.clear", {"group": "tous"}, "group texte"),
               ("count.setGroup", {"markerSize": 11}, "marque 11"), ("count.setGroup", {"labelSize": 7}, "numéro 7"),
               ("count.setGroup", {"color": "red"}, "couleur nommée"), ("count.newGroup", {"name": "x" * 129}, "nom trop long"),
               ("count.newGroup", {"name": "a\x00b"}, "caractère de contrôle"),
               ("notes.add", {"x": 1, "y": 2, "text": "x" * 4001}, "texte trop long"), ("notes.add", {"x": 1, "y": 2, "open": "oui"}, "open texte"),
               ("notes.set", {"text": "x"}, "index manquant"), ("notes.delete", {"all": False}, "all faux"),
               ("notes.delete", {"index": 0, "all": True}, "index ET all"), ("notes.delete", {}, "rien"),
               ("slice.new", {}, "sans rectangle"), ("slice.new", {"rect": [1, 2, 0, 4]}, "largeur 0"), ("slice.new", {"rect": [1, 2, 3]}, "rect tronqué"),
               ("slice.new", {"x": 1, "y": 2, "width": 3}, "xywh incomplet"), ("slice.new", {"rect": [1, 2, 3, 4], "x": 1}, "rect ET x"),
               ("slice.set", {"rect": [1, 2, 3, 4]}, "sans cible"), ("slice.set", {"slice": 1, "number": 2}, "deux cibles"),
               ("slice.set", {"slice": 1, "kind": "video"}, "type inconnu"), ("slice.set", {"slice": 1, "background": "bleu"}, "fond nommé"),
               ("slice.set", {"slice": 1, "url": "x" * 2049}, "URL trop longue"), ("slice.set", {"slice": 1, "horizontalAlign": 5}, "alignement 5"),
               ("slice.set", {"slice": 1, "file": "a"}, "clé file"), ("slice.divide", {"slice": 1, "horizontal": 101}, "101 tranches"),
               ("slice.divide", {"slice": 1, "vertical": 0}, "0 tranche"), ("slice.delete", {"slices": []}, "liste vide"),
               ("slice.delete", {"slices": ["1"]}, "id texte"), ("slice.promote", {"number": 0}, "numéro 0"),
               ("measurementLog.delete", {}, "rien"), ("measurementLog.delete", {"rows": [1], "all": True}, "rows ET all"),
               ("measurementLog.delete", {"rows": [-1]}, "id négatif"), ("measurementLog.export", {}, "export (désactivé par le moteur)"),
               ("measurementLog.export", {"path": "exports/x.csv"}, "export vers un fichier"), ("file.import.notes", {"path": "exports/n.pcraft"}, "import de notes")]
    for cid, p, pourquoi in mauvais:
        check(f"1b refusé ({pourquoi}) : {cid}", admis(reg, cid, p) is not True)


def moteur():
    print("\n[2] VRAI moteur")
    PM.fermer()
    PM.FABRIQUE = None
    try:
        cli = PM.chemin_cli()
        check("2 le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", cli.is_file(), cli)
    except PM.MoteurAbsent as e:
        check("2 le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", False, e)
        return None
    s = PM.session()
    reg = PM.registre(s)
    liste_blanche(reg)
    ap = s.appeler
    ex = lambda c, p=None: ap("engine.execute", {"command": c, "params": p or {}})
    h = lambda: ap("doc.inspect")["history"][-1]
    src = (RACINE / "frontend/photolab/js/mod-historique.js").read_text(encoding="utf-8")
    ap("doc.new", {"width": 400, "height": 300, "name": "A"})
    etapes = []
    for cid, p in (("count.add", {"x": 10, "y": 10}), ("count.newGroup", {"name": "G"}), ("count.setGroup", {"group": 1, "markerSize": 3}),
                   ("count.clear", {"group": 1}), ("count.deleteGroup", {"group": 1}), ("notes.add", {"x": 5, "y": 5, "text": "a"}),
                   ("notes.set", {"index": 0, "text": "b"}), ("notes.set", {"index": 0, "x": 50, "y": 60}),
                   ("slice.new", {"rect": [10, 10, 50, 50]}), ("slice.set", {"slice": 1, "name": "haut"}), ("slice.divide", {"slice": 1, "horizontal": 2}),
                   ("slice.promote", {"number": 1}), ("slice.delete", {"slice": 1}), ("view.clearSlices", {}),
                   ("image.analysis.setMeasurementScale", {"pixelLength": 100, "logicalLength": 2, "units": "cm"})):
        ex(cid, p)
        etapes.append(h())
    manquants = sorted({e for e in etapes if f'"{e}":' not in src})
    check("2a chaque étape d'historique a son nom dans ETATS_MOTEUR (mod-historique)", not manquants, (manquants, etapes))
    ex("image.analysis.rulerTool", {"start": [0, 0], "end": [100, 0]})
    check("2b la règle ne fait aucune étape", h() == etapes[-1], h())
    ex("count.add", {"x": 20, "y": 30}); ex("count.add", {"x": 40, "y": 30})
    ex("notes.add", {"x": 7, "y": 8, "text": "voir a/b.png", "author": "Moi", "color": "#ff0000"})
    ex("slice.new", {"rect": [0, 0, 100, 100], "name": "zone"})
    an, _ = PM.analyse(s)
    check("2c analyse : règle (2 cm à l'échelle), comptage, notes, tranches, échelle", an["ruler"]["end"] == [100.0, 0.0]
          and abs(an["rulerInfo"]["length"] - 2.0) < 1e-6 and an["rulerInfo"]["units"] == "cm"
          and an["count"]["total"] == 3 and any(n["text"] == "voir a/b.png" for n in an["notes"])
          and any(x["origin"] == "user" and x["name"] == "zone" for x in an["slices"]) and an["scale"]["units"] == "cm", an)
    check("2d analyse : aucune étape", h() == ap("doc.inspect")["history"][-1])
    if ex("measurementLog.list")["rows"]:                         # vide : le moteur refuse « the Measurement Log is empty »
        ex("measurementLog.delete", {"all": True})
    ex("image.analysis.recordMeasurements", {"source": "ruler"})
    ex("image.analysis.recordMeasurements", {"source": "count"})
    texte = PM.journal_csv(s)
    lignes = list(csv.reader(io.StringIO(texte), delimiter=";"))
    check("2e CSV : en-tête des colonnes choisies, une ligne par mesure", lignes[0][:4] == ["Label", "Date and Time", "Document", "Source"]
          and len(lignes) == 3 and "Length" in lignes[0], lignes[:2])
    i_long = lignes[0].index("Length")
    check("2f CSV : la longueur de la règle à l'échelle (2)", lignes[1][i_long] == "2", lignes[1])
    check("2f2 CSV : l'angle d'une règle horizontale vaut « 0 », jamais « -0 »", lignes[1][lignes[0].index("Angle")] == "0", lignes[1])
    ids = [r["id"] for r in ex("measurementLog.list")["rows"]]
    check("2g CSV : lignes choisies seulement", len(list(csv.reader(io.StringIO(PM.journal_csv(s, [ids[1]])), delimiter=";"))) == 2)
    ex("image.analysis.selectDataPoints", {"ruler": {"angle": False}})
    check("2h CSV : une colonne décochée disparaît si aucune source ne la garde", "Angle" not in PM.journal_csv(s).splitlines()[0],
          PM.journal_csv(s).splitlines()[0])
    ex("image.analysis.selectDataPoints", {"reset": True})
    # import de notes : B (actif) reçoit les notes de A
    a_index = ap("session.list")["active"]
    ap("doc.new", {"width": 50, "height": 40, "name": "B"})
    r, _ = PM.importer_notes(s, a_index)
    notes = ex("notes.list")["notes"]
    n1 = next((n for n in notes if n["text"] == "voir a/b.png"), {})
    n2 = next((n for n in notes if n["text"] == "b"), {})
    check("2i import de notes : les 2 de A copiées dans l'actif, fermées, texte et auteur gardés", r["imported"] == 2 and len(notes) == 2
          and n1.get("author") == "Moi" and n1.get("open") is False and n1.get("position") == [7.0, 8.0], (r, notes))
    check("2j import : couleur conservée ; une note hors de la toile (50, 60) bornée à (49, 39)",
          abs(n1["color"][0] - 1) < 0.01 and n1["color"][1] < 0.01 and n2.get("position") == [49.0, 39.0], notes)
    check("2k import : le document actif reste B", ap("doc.inspect")["name"] == "B", ap("doc.inspect")["name"])
    try:
        PM.importer_notes(s, ap("session.list")["active"])
        check("2l import depuis le document actif refusé", False)
    except ValueError:
        check("2l import depuis le document actif refusé", True)
    try:
        PM.importer_notes(s, 99)
        check("2m import depuis un document inconnu refusé", False)
    except ValueError:
        check("2m import depuis un document inconnu refusé", True)
    return s


async def routes():
    print("\n[3] routes")
    import httpx
    from app.main import app
    t = httpx.ASGITransport(app=app, client=("127.0.0.1", 5000))
    async with httpx.AsyncClient(transport=t, base_url="http://t") as c:
        r = await c.get("/api/photolab/analyse")
        check("3a GET /analyse -> 200 (règle, comptage, notes, tranches)", r.status_code == 200 and {"ruler", "count", "notes", "slices", "locked", "scale"} <= set(r.json()),
              (r.status_code, r.text[:200]))
        r = await c.get("/api/photolab/mesures.csv")
        check("3b GET /mesures.csv -> CSV UTF-8 avec BOM, en téléchargement", r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
              and r.content.startswith("\ufeff".encode("utf-8")) and "attachment" in r.headers.get("content-disposition", ""), (r.status_code, r.headers))
        for q, pourquoi in (("lignes=a", "id texte"), ("lignes=1,%2E%2E", "id chemin")):
            r = await c.get(f"/api/photolab/mesures.csv?{q}")
            check(f"3c /mesures.csv refusé ({pourquoi}) -> 400", r.status_code == 400, (r.status_code, r.text[:200]))
        for corps, pourquoi in (({"document": "0"}, "index texte"), ({"document": -1}, "négatif"), ({"document": 0, "path": "x"}, "clé inconnue"),
                                ({"document": True}, "booléen"), ({"document": 99}, "inconnu")):
            r = await c.post("/api/photolab/notes/importer", json=corps)
            check(f"3d /notes/importer refusé ({pourquoi}) -> 400", r.status_code == 400, (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/executer", json={"command": "measurementLog.export", "params": {}})
        check("3e /executer measurementLog.export -> 400 (réservée)", r.status_code == 400, (r.status_code, r.text[:200]))
        r = await c.post("/api/photolab/executer", json={"command": "notes.add", "params": {"x": 1, "y": 1, "text": "par la route a/b"}})
        check("3f /executer notes.add avec un texte « fichier » -> 200", r.status_code == 200, (r.status_code, r.text[:200]))


try:
    if moteur():
        asyncio.run(routes())
finally:
    PM.fermer()
    shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
