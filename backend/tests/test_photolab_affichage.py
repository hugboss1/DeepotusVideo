# -*- coding: utf-8 -*-
"""t152 (Photolab parité L2) — lire les repères du document sur le VRAI moteur.
doc.inspect ne rend pas les repères (Document.guides) : PM.reperes copie le document (image.duplicate), enregistre la
copie en .pcraft sous rendus/, la referme, rend l'original actif et lit manifest.json (document.guides).
[1] lecture : aucun repère, puis après view.newGuide / moveGuide / deleteGuide / annulation (historique)
[2] l'original est intact (révision, historique, nombre de documents, document actif) et aucun fichier n'est laissé
[3] cache par (génération, document, révision) : une deuxième lecture à la même révision ne copie rien
[4] route GET /api/photolab/reperes (avec et sans document)
Section VRAI moteur rouge si le binaire manque (PHOTOCRAFT_CLI dans un worktree).
Run : & $PY -X utf8 tests/test_photolab_affichage.py   (depuis backend/)"""
import asyncio, os, pathlib, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt152_"))
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


def pcraft_laisses():
    d = PM.dossier_travail() / "rendus"
    return sorted(p.name for p in d.iterdir() if p.suffix == ".pcraft")


def moteur():
    print("\n[1-3] VRAI moteur")
    PM.fermer()
    PM.FABRIQUE = None
    try:
        cli = PM.chemin_cli()
        check("1a le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", cli.is_file(), cli)
    except PM.MoteurAbsent as e:
        check("1a le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", False, e)
        return
    s = PM.session()
    ex = lambda c, **p: s.appeler("engine.execute", {"command": c, "params": p})
    s.appeler("doc.new", {"width": 320, "height": 200, "background": "white"})
    r, _ = PM.reperes(s)
    check("1b sans repère : listes vides", r == {"horizontal": [], "vertical": []}, r)
    ex("view.newGuide", orientation="vertical", position=50)
    ex("view.newGuide", orientation="horizontal", position=30.5)
    ex("view.newGuide", orientation="vertical", position=200)
    avant = s.appeler("doc.inspect")
    docs_avant = s.appeler("session.list")
    r, gen = PM.reperes(s)
    check("1c après trois repères : lus dans l'ordre de création", r == {"horizontal": [30.5], "vertical": [50.0, 200.0]}, r)
    apres = s.appeler("doc.inspect")
    docs_apres = s.appeler("session.list")
    check("2a original intact : même révision, même historique", apres["revision"] == avant["revision"] and apres["history"] == avant["history"],
          (avant["revision"], apres["revision"], apres["history"][-3:]))
    check("2b même nombre de documents, même document actif", len(docs_apres["documents"]) == len(docs_avant["documents"])
          and docs_apres["active"] == docs_avant["active"], (docs_avant, docs_apres))
    check("2c aucun .pcraft laissé sous rendus/", pcraft_laisses() == [], pcraft_laisses())
    compte = {"n": 0}
    vrai = s.sequence

    def compter(fn, delai_s=None):
        compte["n"] += 1
        return vrai(fn, delai_s)
    s.sequence = compter
    try:
        r2, _ = PM.reperes(s)
        check("3a même révision : même réponse, une séquence légère (aucune copie)", r2 == r and compte["n"] == 1, (r2, compte))
        check("3b le cache est celui de (génération, document, révision)", PM._CACHE_REPERES["base"] == (gen, 0, apres["revision"]), PM._CACHE_REPERES)
    finally:
        s.sequence = vrai
    ex("view.moveGuide", orientation="vertical", index=0, position=80)
    r, _ = PM.reperes(s)
    check("1d moveGuide : la nouvelle position est lue", r == {"horizontal": [30.5], "vertical": [80.0, 200.0]}, r)
    ex("view.deleteGuide", orientation="horizontal", index=0)
    r, _ = PM.reperes(s)
    check("1e deleteGuide : le repère disparaît", r == {"horizontal": [], "vertical": [80.0, 200.0]}, r)
    ex("edit.undo")
    r, _ = PM.reperes(s)
    check("1f annulation : le repère revient", r == {"horizontal": [30.5], "vertical": [80.0, 200.0]}, r)
    check("2d toujours aucun .pcraft laissé", pcraft_laisses() == [], pcraft_laisses())
    asyncio.run(routes(r))


async def routes(attendu):
    print("\n[4] route")
    import httpx
    from app.main import app
    t = httpx.ASGITransport(app=app, client=("127.0.0.1", 5000))
    async with httpx.AsyncClient(transport=t, base_url="http://t") as c:
        r = await c.get("/api/photolab/reperes")
        j = r.json() if r.status_code == 200 else {}
        check("4a GET /reperes : 200, repères du document actif + révision", r.status_code == 200 and j.get("horizontal") == attendu["horizontal"]
              and j.get("vertical") == attendu["vertical"] and isinstance(j.get("revision"), int), (r.status_code, r.text[:200]))
        check("4b en-tête X-Photolab-Generation", bool(r.headers.get("x-photolab-generation")), dict(r.headers))
    s = PM.session()
    while (s.appeler("session.list").get("documents") or []):
        s.appeler("doc.close", {"index": 0})
    async with httpx.AsyncClient(transport=t, base_url="http://t") as c:
        r = await c.get("/api/photolab/reperes")
        check("4c sans document : 200, listes vides, révision nulle", r.status_code == 200 and r.json() == {"horizontal": [], "vertical": [], "revision": None},
              (r.status_code, r.text[:200]))


try:
    moteur()
finally:
    PM.fermer()
    shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
