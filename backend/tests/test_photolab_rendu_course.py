# -*- coding: utf-8 -*-
"""Course du rangement des aperçus (constat du 10/11/2026) : cinq `PL.executer` enchaînés sans pause depuis l'iframe
/photolab/ laissaient « aperçu introuvable après le rendu : [WinError 2…] ». Deux rendus rangeaient en même temps :
l'un listait un ancien aperçu que l'autre effaçait, puis son stat() levait FileNotFoundError.
Run : & $PY tests/test_photolab_rendu_course.py   (depuis backend/)"""
import asyncio, os, pathlib, re, shutil, sys, tempfile, threading, time
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzrcourse_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_moteur as PM                # noqa: E402
from app.api import photolab_routes as R                      # noqa: E402
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:300]}")


PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 32


def apercus(d):
    return sorted(x.name for x in d.iterdir() if R._APERCU.fullmatch(x.name))


# ── 1. Déterministe : un aperçu listé disparaît avant sa lecture (ce que faisait l'autre rendu) ──────────────────
d1 = _tmp / "r1"; d1.mkdir()
for i in range(1, 6):
    (d1 / f"apercu-1-{i}.png").write_bytes(PNG)
    os.utime(d1 / f"apercu-1-{i}.png", ns=(i * 10**9, i * 10**9))
(d1 / "tmp-6.png").write_bytes(PNG)
_iterdir = pathlib.Path.iterdir


def iterdir_concurrent(self):
    noms = list(_iterdir(self))
    victime = self / "apercu-1-2.png"                         # effacé par « l'autre rendu » juste après la liste
    if victime.exists():
        victime.unlink()
    return iter(noms)


pathlib.Path.iterdir = iterdir_concurrent
try:
    try:
        R._ranger_apercu(d1 / "tmp-6.png", d1 / "apercu-1-6.png")
        err = None
    except OSError as e:
        err = e
finally:
    pathlib.Path.iterdir = _iterdir
check("1 un aperçu effacé entre la liste et sa lecture n'interrompt pas le rangement (plus de WinError 2)",
      err is None, repr(err))
check("1b le rangement garde les 3 derniers aperçus, le nouveau compris",
      apercus(d1) == ["apercu-1-4.png", "apercu-1-5.png", "apercu-1-6.png"], apercus(d1))

# ── 2. Rendus concurrents réels : 12 fils rangent 25 fois chacun, lâchés ensemble ─────────────────────────────────
d2 = _tmp / "r2"; d2.mkdir()
compteur = iter(range(1, 10**6))
verrou_c = threading.Lock()
erreurs = []
depart = threading.Barrier(12)


def rendeur():
    depart.wait()
    for _ in range(25):
        with verrou_c:
            n = next(compteur)
        (d2 / f"tmp-{n}.png").write_bytes(PNG)
        try:
            R._ranger_apercu(d2 / f"tmp-{n}.png", d2 / f"apercu-1-{n}.png")
        except OSError as e:
            erreurs.append(repr(e))


fils = [threading.Thread(target=rendeur) for _ in range(12)]
for f in fils:
    f.start()
for f in fils:
    f.join()
check("2 300 rangements concurrents : aucune erreur « aperçu introuvable »", not erreurs, erreurs[:3])
check("2b après la rafale, exactement 3 aperçus et aucun temporaire",
      len(apercus(d2)) == 3 and len(list(d2.iterdir())) == 3, sorted(x.name for x in d2.iterdir()))
check("2c le verrou de rangement est libre après la rafale", R._VERROU_RANGEMENT.acquire(blocking=False))
R._VERROU_RANGEMENT.release()

# ── 3. Un rangement isolé reste immédiat ─────────────────────────────────────────────────────────────────────────
d3 = _tmp / "r3"; d3.mkdir()
durees = []
for n in range(1, 41):
    (d3 / f"tmp-{n}.png").write_bytes(PNG)
    t = time.perf_counter()
    R._ranger_apercu(d3 / f"tmp-{n}.png", d3 / f"apercu-1-{n}.png")
    durees.append(time.perf_counter() - t)
durees.sort()
check("3 un rangement isolé prend quelques ms (médiane < 20 ms)", durees[len(durees) // 2] < 0.02,
      f"médiane {durees[len(durees) // 2] * 1000:.1f} ms")

# ── 4. Bout à bout : 5 POST /rendu lancés ensemble sur le faux moteur ────────────────────────────────────────────
D = PM.dossier_travail()
FAUX = [sys.executable, str(BACKEND / "tests" / "faux_photocraft.py"), "serve",
        "--automation-read-root", str(D), "--automation-write-root", str(D)]
PM.FABRIQUE = lambda: PM.SessionMoteur(FAUX, delai_s=10.0)
_RACINE0 = PM.RACINE_APP


async def scenario():
    import httpx
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t") as c:
        r = await c.post("/api/photolab/nouveau", json={"width": 64, "height": 32, "background": "white"})
        check("4a document ouvert sur le faux moteur", r.status_code == 200, r.text)
        for tour in range(4):
            rs = await asyncio.gather(*(c.post("/api/photolab/rendu", json={"maxSide": 64}) for _ in range(5)))
            mauvais = [(x.status_code, x.text) for x in rs if x.status_code != 200]
            if mauvais:
                break
        check("4b 4 rafales de 5 /rendu simultanés : toutes en 200, jamais « aperçu introuvable »", not mauvais, mauvais[:2])
        urls = [x.json()["url"] for x in rs]
        check("4c chaque rendu d'une rafale a son propre fichier", len(set(urls)) == 5
              and all(re.fullmatch(r"/api/photolab/rendus/apercu-\d+-\d+\.png", u) for u in urls), urls)
        dernier = max(urls, key=lambda u: int(u.rsplit("-", 1)[1][:-4]))
        f = await c.get(dernier)
        check("4d le dernier aperçu de la rafale est servi", f.status_code == 200 and f.content.startswith(b"\x89PNG"),
              f.status_code)
        restants = [x.name for x in (D / "rendus").iterdir()]
        check("4e après les rafales, 3 aperçus et aucun temporaire",
              len(restants) == 3 and all(R._APERCU.fullmatch(x) for x in restants), sorted(restants))
    PM.fermer()
    PM.FABRIQUE = None
    PM.RACINE_APP = _RACINE0

asyncio.run(scenario())
shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
