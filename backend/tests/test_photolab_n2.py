# t412 (Photolab N2, photocraft 0.21) : texte — styles de chiffres, jeux stylistiques, texte dans une forme.
# [1] les 30 commandes ouvertes passent par /executer, sur un calque de texte, avec un état d'historique annulable ;
# [2] Texte dans une forme : sur un calque de forme ou le tracé de travail, refus propres ;
# [3] les favoris restent à l'écran : type.font.* reste fermée (elle écrirait les préférences du moteur).
# Lancement : python embarqué, `python tests/test_photolab_n2.py` depuis backend/ (PHOTOCRAFT_CLI si le moteur n'est pas vendu).
import asyncio, os, pathlib, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt412_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_moteur as PM                 # noqa: E402
from app.services.photolab_neuves import COMMANDES_NEUVES_FERMEES as F, OUVERTES_021   # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:500]}")


CHIFFRES = ("default", "lining", "oldstyle", "proportional", "tabular", "proportionalLining", "tabularLining",
            "proportionalOldstyle", "tabularOldstyle")
ATTENDUS = {f"type.openType.numerals.{c}" for c in CHIFFRES} | {f"type.openType.stylisticSets.set{n}" for n in range(1, 21)} | {"type.fillPath"}


async def scenario():
    import httpx
    from app.main import app
    API = "/api/photolab"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t", timeout=120) as c:
        post = lambda u, j=None: c.post(API + u, json=j if j is not None else {})
        ex = lambda cmd, p=None: post("/executer", {"command": cmd, "params": p or {}})
        ins = lambda: asyncio.to_thread(PM.session().appeler, "doc.inspect")
        traits = lambda l: ex("type.info", {"layer": l})
        print("[1] chiffres et jeux stylistiques")
        check("1.0 les 30 commandes du lot sont ouvertes, et elles seules parmi celles de 0.21", {x for x in ATTENDUS if x not in F} == ATTENDUS and ATTENDUS <= OUVERTES_021, sorted(ATTENDUS & F)[:5])
        assert (await post("/nouveau", {"width": 400, "height": 200, "background": "white"})).status_code == 200
        r = await ex("type.create", {"text": "Office 0123", "x": 20, "y": 60, "size": 40})
        calque = r.json()["layer"]
        features = lambda j: sorted(f["tag"] for f in j["runs"][0]["style"]["features"])
        for cmd, tags in (("oldstyle", ["onum"]), ("lining", ["lnum"]), ("proportional", ["pnum"]), ("tabular", ["tnum"]), ("proportionalOldstyle", ["onum", "pnum"]),
                          ("tabularLining", ["lnum", "tnum"]), ("proportionalLining", ["lnum", "pnum"]), ("tabularOldstyle", ["onum", "tnum"]), ("default", [])):
            r = await ex(f"type.openType.numerals.{cmd}")
            t = features((await traits(calque)).json())
            check(f"1.1 {cmd} : {tags}", r.status_code == 200 and t == tags, (r.status_code, r.text, t))
        h = (await ins())["history"]
        await ex("type.openType.numerals.oldstyle")
        h2 = (await ins())["history"]
        check("1.2 un état « Change OpenType Numerals »", h2 == h + ["Change OpenType Numerals"], h2[-3:])
        await ex("edit.undo")
        check("1.3 annulable", features((await traits(calque)).json()) == [] and (await ins())["history"] == h)
        for n in (1, 3, 20):
            await ex(f"type.openType.stylisticSets.set{n}")
            check(f"1.4 jeu {n} allumé (ss{n:02d})", features((await traits(calque)).json()) == [f"ss{n:02d}"], features((await traits(calque)).json()))
            await ex(f"type.openType.stylisticSets.set{n}")
            check(f"1.5 jeu {n} : second appel, éteint", features((await traits(calque)).json()) == [])
        r = await ex("type.openType.stylisticSets.set2", {"on": True})
        check("1.6 clé `on` admise", r.status_code == 200 and features((await traits(calque)).json()) == ["ss02"], r.text)
        await ex("type.openType.stylisticSets.set2", {"on": False})
        r = await ex("type.openType.stylisticSets.set2", {"zorg": 1})
        check("1.7 clé inconnue refusée", r.status_code == 400, (r.status_code, r.text))
        fond = next(x["id"] for x in (await ins())["layers"] if x["kind"] == "Pixel")
        await ex("layer.select", {"layer": fond, "mode": "replace"})
        r = await ex("type.openType.numerals.oldstyle")
        check("1.8 sans calque de texte : refus du moteur", r.status_code == 422, (r.status_code, r.text))
        await ex("layer.select", {"layer": calque, "mode": "replace"})

        print("[2] Texte dans une forme")
        r = await ex("type.fillPath")
        check("2.1 sans tracé ni forme : refus du moteur, rien ne change", r.status_code == 422 and "work path" in r.text, (r.status_code, r.text))
        forme = (await ex("shape.create", {"kind": "ellipse", "rect": [100, 20, 300, 180], "fill": "#cccccc"})).json()["layer"]
        await ex("layer.select", {"layer": calque, "mode": "replace"})
        h = (await ins())["history"]
        r = await ex("type.fillPath", {"shape": forme})
        i = (await traits(calque)).json()
        check("2.2 le texte passe dans la forme : état « Area Type »", r.status_code == 200 and (await ins())["history"] == h + ["Area Type"] and "Area" in i["shape"], (r.text, str(i.get("shape"))[:80]))
        await ex("edit.undo")
        r = await ex("type.fillPath", {"shape": "C:/x"})
        check("2.3 `shape` : un id de calque, jamais autre chose", r.status_code == 400, (r.status_code, r.text))

        print("[3] favoris")
        for cmd, p in (("type.font.favorite", {"family": "Inter"}), ("type.font.library", {})):
            r = await ex(cmd, p)
            check(f"3.1 {cmd} reste fermée", r.status_code == 400 and "pas encore ouverte" in r.text, (r.status_code, r.text))


asyncio.run(scenario())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
