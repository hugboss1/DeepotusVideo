# t416 (Photolab N6, photocraft 0.21) : bibliothèques — styles .asl (import, export), formes .csh (import), gardés d'un
# démarrage du moteur à l'autre.
# Lancement : python embarqué, `python tests/test_photolab_n6.py` depuis backend/ (PHOTOCRAFT_CLI si le moteur n'est pas vendu).
import asyncio, base64, os, pathlib, struct, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt416_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_moteur as PM, photolab_bibliotheques as PB   # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:500]}")


def csh(label="Triangle", points=((0.25, 0.25), (0.75, 0.25), (0.5, 0.75))):
    """Un .csh d'une forme : reprend crates/psd/tests/common/csh_fixture.rs (amont)."""
    be32, be16 = (lambda n: struct.pack(">I", n)), (lambda n: struct.pack(">H", n))
    nom = [ord(c) for c in label] + [0]
    o = b"cush" + be32(2) + be32(1) + be32(len(nom)) + b"".join(be16(u) for u in nom)
    if len(nom) % 2:
        o += b"\0\0"
    o += be32(1)
    corps = b"\x24" + b"00000000-0000-4000-8000-000000000001" + b"".join(struct.pack(">i", b) for b in (0, 0, 100, 200))
    for sel in (6, 8):
        corps += be16(sel) + bytes(24)
    corps += be16(0) + be16(len(points)) + bytes(22)
    for x, y in points:
        corps += be16(2) + (struct.pack(">i", int(y * 16777216)) + struct.pack(">i", int(x * 16777216))) * 3
    corps += bytes(-len(corps) % 4)
    return o + be32(len(corps)) + corps


async def scenario():
    import httpx
    from app.main import app
    API = "/api/photolab"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t", timeout=120) as c:
        post = lambda u, j=None: c.post(API + u, json=j if j is not None else {})
        ex = lambda cmd, p=None: post("/executer", {"command": cmd, "params": p or {}})
        imp = lambda g, n, o: post("/bibliotheques/importer", {"genre": g, "groupe": n, "data": base64.b64encode(o).decode()})
        groupes = lambda cmd: ex(cmd)
        noms = lambda r: [g["name"] for g in r.json()["groups"]]
        assert (await post("/nouveau", {"width": 200, "height": 100, "background": "white"})).status_code == 200
        await ex("layer.new.layer"); await ex("select.all"); await ex("edit.fill", {"color": "#ff0000"}); await ex("select.deselect")
        await ex("layer.layerStyle.dropShadow", {"distance": 5, "size": 5, "opacity": 50})

        print("[1] styles .asl")
        await ex("style.presets.edit", {"action": "newGroup", "name": "Mes styles"})
        r = await ex("style.presets.new", {"name": "Rouge", "group": "Mes styles"})
        check("1.0 un style à exporter", r.status_code == 200, r.text[:200])
        r = await post("/bibliotheques/exporter", {"groupe": "Mes styles"})
        j = r.json() if r.status_code == 200 else {}
        check("1.1 export : un fichier .asl en base64", r.status_code == 200 and j.get("count") == 1 and j.get("data"), r.text[:200])
        asl = base64.b64decode(j.get("data", ""))
        r = await imp("styles", "Importé", asl)
        check("1.2 import : le groupe et ses styles", r.status_code == 200 and r.json().get("count") == 1 and "Importé" in noms(await groupes("style.presets.list")), r.text[:200])
        r = await post("/bibliotheques/exporter", {"groupe": "Absent"})
        check("1.3 export d'un groupe absent : refus", r.status_code in (400, 422), (r.status_code, r.text[:160]))

        print("[2] formes .csh")
        r = await imp("formes", "Mes formes", csh())
        check("2.1 import : une forme", r.status_code == 200 and r.json().get("count") == 1 and "Mes formes" in noms(await groupes("shape.presets.list")), (r.status_code, r.text[:200]))
        r = await ex("shape.presets.place", {"preset": "Triangle", "group": "Mes formes", "rect": [10, 10, 80, 80]})
        check("2.2 la forme se pose", r.status_code == 200, (r.status_code, r.text[:200]))

        print("[3] refus")
        for corps, lib in (({"genre": "brosses", "groupe": "g", "data": "AAAA"}, "genre inconnu"), ({"genre": "styles", "groupe": "", "data": "AAAA"}, "groupe vide"),
                           ({"genre": "styles", "groupe": "g", "data": "%%%"}, "base64 abîmé"), ({"genre": "styles", "groupe": "g"}, "sans contenu"),
                           ({"genre": "styles", "groupe": "g", "data": "AAAA", "path": "x"}, "clé inconnue")):
            r = await post("/bibliotheques/importer", corps)
            check(f"3.1 {lib}", r.status_code == 400, (r.status_code, r.text[:160]))
        r = await imp("styles", "Abîmé", b"zorg")
        check("3.2 fichier illisible : refus du moteur, rien de gardé", r.status_code == 422 and not any(e["groupe"] == "Abîmé" for e in PB.lire()), (r.status_code, r.text[:160]))
        for cmd, p in (("style.presets.importAsl", {"data": "AAAA"}), ("shape.presets.importCsh", {"data": "AAAA"}), ("style.presets.exportAsl", {}), ("layer.layerStyle.contours.list", {})):
            r = await ex(cmd, p)
            check(f"3.3 {cmd} fermée à /executer", r.status_code == 400, (r.status_code, r.text[:160]))

        print("[4] gardés au redémarrage")
        check("4.1 la réserve tient deux fichiers", sorted(e["groupe"] for e in PB.lire()) == ["Importé", "Mes formes"], [e["groupe"] for e in PB.lire()])
        await asyncio.to_thread(PM.session().fermer)
        r = await groupes("style.presets.list")
        check("4.2 moteur neuf : le groupe de styles revient", "Importé" in noms(r), noms(r))
        r = await groupes("shape.presets.list")
        check("4.3 moteur neuf : le groupe de formes revient", "Mes formes" in noms(r), noms(r))
        r = await ex("shape.presets.edit", {"action": "rename", "preset": "Triangle", "group": "Mes formes", "name": "Tri"})
        check("4.3b renommer une forme ne retire pas le fichier", r.status_code == 200 and sorted(e["groupe"] for e in PB.lire()) == ["Importé", "Mes formes"], (r.text[:160], [e["groupe"] for e in PB.lire()]))
        r = await ex("shape.presets.edit", {"action": "renameGroup", "group": "Mes formes", "name": "Formes à moi"})
        check("4.3c renommer un groupe suit dans la réserve", r.status_code == 200 and sorted(e["groupe"] for e in PB.lire()) == ["Formes à moi", "Importé"], (r.text[:160], [e["groupe"] for e in PB.lire()]))
        r = await ex("style.presets.edit", {"action": "deleteGroup", "group": "Importé"})
        check("4.4 supprimer le groupe le retire de la réserve", r.status_code == 200 and [e["groupe"] for e in PB.lire()] == ["Formes à moi"], (r.text[:160], [e["groupe"] for e in PB.lire()]))
        await asyncio.to_thread(PM.session().fermer)
        r = await groupes("style.presets.list")
        check("4.5 et il ne revient plus", "Importé" not in noms(r), noms(r))
    PB.chemin().write_text("{abîmé", encoding="utf-8")
    check("5.1 réserve abîmée : vide", PB.lire() == [] and PB.etapes() == [])


asyncio.run(scenario())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
