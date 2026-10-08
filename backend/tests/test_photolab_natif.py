# -*- coding: utf-8 -*-
"""t140 (Photolab P5, décision D10) — le repli « app native » : POST /api/photolab/natif/ouvrir enregistre le document
actif en natif/<base>-<horodatage>.pcraft et l'ouvre dans photocraft.exe --control (lancé sur un port libre, jeton dans
un fichier, racines d'automatisation = dossier du moteur) ; POST /natif/reprendre fait enregistrer l'app native puis
rouvre le résultat dans le Photolab ; GET /natif/etat.
  [1] FAUX app native (tests/faux_natif.py, même protocole que le vrai) : jeton, port, chemins relatifs, réutilisation,
      relance après fermeture, reprise, lignée, erreurs dites.
  [2] VRAIE app native : seulement avec DZ_NATIF_REEL=1 (elle ouvre une fenêtre) — sinon la section le DIT.
Run : & $PY tests/test_photolab_natif.py   (depuis backend/)"""
import asyncio, json, os, pathlib, re, shutil, sys, tempfile, time
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt140n_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ.setdefault("FAL_KEY", "test-key")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_moteur as PM                # noqa: E402
from app.services import photolab_natif as PN                 # noqa: E402
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:400]}")


D = PM.dossier_travail()
FAUX = [sys.executable, str(BACKEND / "tests" / "faux_photocraft.py"), "serve",
        "--automation-read-root", str(D), "--automation-write-root", str(D)]
PM.FABRIQUE = lambda: PM.SessionMoteur(FAUX, delai_s=5.0)
from PIL import Image                                          # noqa: E402
Image.new("RGB", (8, 8), (200, 30, 30)).save(_tmp / "images" / "rouge.png")
JOURNAL = D / "natif" / ".journal-faux"


def journal():
    if not JOURNAL.is_file():
        return []
    return [json.loads(l) for l in JOURNAL.read_text("utf-8").splitlines() if l.strip()]


async def fake_scenario(c):
    print("\n[1] faux app native")
    from app.services.storage import init_db
    from app.services import library_index as LI
    await init_db()
    PN.FABRIQUE = None
    PN.RACINE_APP = _tmp                                          # aucun photocraft.exe ici
    e = (await c.get("/api/photolab/natif/etat")).json()
    check("1a /natif/etat sans app native : present false, actif false", e.get("present") is False and e.get("actif") is False, e)
    r = await c.post("/api/photolab/natif/ouvrir", json={})
    check("1b ouvrir sans app native -> 503 qui le dit", r.status_code == 503 and "photocraft.exe" in r.text, (r.status_code, r.text))
    PN.FABRIQUE = lambda: [sys.executable, str(BACKEND / "tests" / "faux_natif.py")]
    PN.DELAI_DEMARRAGE = 15.0
    r = await c.post("/api/photolab/natif/ouvrir", json={})
    check("1c ouvrir sans document -> 409 (rien à envoyer), l'app n'est pas lancée", r.status_code == 409 and not journal(), (r.status_code, r.text))

    r = await c.post("/api/photolab/ouvrir", json={"filename": "rouge.png"})
    assert r.status_code == 200, r.text
    r = await c.post("/api/photolab/natif/ouvrir", json={})
    j = r.json()
    f1 = j.get("fichier", "")
    check("1d ouvrir : le document est enregistré en natif/<base>-<horodatage>.pcraft sous le dossier du moteur",
          r.status_code == 200 and re.fullmatch(r"natif/rouge-\d{8}-\d{6}\.pcraft", f1) and (D / f1).is_file(), (r.status_code, r.text))
    J = journal()
    dem = next((x for x in J if x.get("demarrage")), {})
    a = dem.get("args", [])
    port = int(a[a.index("--control") + 1]) if "--control" in a else 0
    check("1e lancée avec --control <port libre>, --control-token-file, et les racines = dossier du moteur",
          port > 1024 and "--control-token-file" in a and a[a.index("--automation-read-root") + 1] == str(D)
          and a[a.index("--automation-write-root") + 1] == str(D), a)
    jf = pathlib.Path(a[a.index("--control-token-file") + 1]) if "--control-token-file" in a else None
    check("1f le jeton : 64 hex, dans un fichier du dossier de données (jamais en clair sur la ligne de commande)",
          jf is not None and jf.is_file() and re.fullmatch(r"[0-9a-f]{64}", jf.read_text().strip())
          and str(_tmp) in str(jf) and jf.read_text().strip() not in " ".join(a), (jf, a))
    req = [x for x in J if x.get("method")]
    k_open = next((k for k, x in enumerate(req) if x["method"] == "app.open"), -1)
    check("1g chaque connexion s'authentifie d'abord ; app.open du fichier (chemin RELATIF), authentifié, puis ui.focus",
          req and all(x["method"] == "auth" for x in req if not x["auth"])
          and all(x["auth"] for x in req if x["method"] != "auth")
          and k_open > 0 and req[k_open]["params"] == {"path": f1} and req[k_open - 1]["method"] == "auth"
          and any(x["method"] == "ui.focus" for x in req[k_open + 1:]), req)
    e = (await c.get("/api/photolab/natif/etat")).json()
    check("1h /natif/etat : present, actif, le fichier envoyé", e.get("present") and e.get("actif") and e.get("fichier") == f1, e)
    pid1 = dem.get("pid")
    await asyncio.sleep(1.1)                                     # un autre horodatage
    r = await c.post("/api/photolab/natif/ouvrir", json={})
    J = journal()
    check("1i un second envoi RÉUTILISE l'app ouverte (aucun nouveau démarrage)", r.status_code == 200
          and sum(1 for x in J if x.get("demarrage")) == 1 and r.json().get("fichier") != f1, (r.text, [x for x in J if x.get("demarrage")]))

    # reprendre : l'app native enregistre, le Photolab rouvre
    r = await c.post("/api/photolab/natif/reprendre", json={})
    j = r.json()
    f2 = j.get("fichier", "")
    J = journal()
    sauve = [x for x in J if x.get("method") == "app.save"]
    check("1j reprendre : app.save vers natif/<base>-retour-<horodatage>.pcraft (relatif), puis ouvert dans le Photolab",
          r.status_code == 200 and re.fullmatch(r"natif/rouge-retour-\d{8}-\d{6}\.pcraft", f2) and sauve and sauve[-1]["params"] == {"path": f2}
          and (D / f2).read_bytes() == b"FAUXNATIF", (r.status_code, r.text, sauve))
    s = (await c.get("/api/photolab/session")).json()
    actif = next((d for d in s["documents"] if d["index"] == s["active"]), {})
    check("1k le document rapporté est le document actif du Photolab", actif.get("path") == f2, s)
    r = await c.post("/api/photolab/bibliotheque", json={"format": "png", "nom": "rouge"})
    fi = (await LI.carte()).get(r.json().get("filename", "")) or {}
    check("1l la lignée suit l'aller-retour : la mère reste rouge.png", fi.get("parent_filename") == "rouge.png", fi)

    # erreurs
    await c.post("/api/photolab/natif/ouvrir", json={})
    import socket
    with socket.create_connection(("127.0.0.1", port), timeout=3) as so:
        f = so.makefile("rwb")
        f.write((json.dumps({"id": 1, "method": "auth", "params": {"token": "0" * 64}}) + "\n").encode()); f.flush()
        rep = json.loads(f.readline())
    check("1m sans le bon jeton, l'app native refuse (le pont ne publie pas le sien)", rep.get("ok") is False, rep)
    PN.appeler("dz.casse")
    r = await c.post("/api/photolab/natif/reprendre", json={})
    check("1n une erreur de l'app native -> 422 qui la dit", r.status_code == 422 and "panne simulée" in r.text, (r.status_code, r.text))
    PN.fermer()
    time.sleep(0.5)
    e = (await c.get("/api/photolab/natif/etat")).json()
    check("1o fermer : l'app native n'est plus active", e.get("actif") is False, e)
    r = await c.post("/api/photolab/natif/reprendre", json={})
    check("1p reprendre sans app native ouverte -> 409", r.status_code == 409, (r.status_code, r.text))
    r = await c.post("/api/photolab/natif/ouvrir", json={})
    J = journal()
    check("1q ouvrir après fermeture RELANCE l'app (nouveau démarrage, nouveau jeton)", r.status_code == 200
          and sum(1 for x in J if x.get("demarrage")) == 2, [x for x in J if x.get("demarrage")])
    PN.fermer()
    PM.fermer()


async def reel_scenario(c):
    print("\n[2] VRAIE app native photocraft.exe")
    if os.environ.get("DZ_NATIF_REEL") != "1":
        check("2- section NON jouée (elle ouvre une fenêtre) : relancer avec DZ_NATIF_REEL=1 pour l'éprouver", True)
        return
    PM.fermer(); PM.FABRIQUE = None
    PN.FABRIQUE = None; PN.RACINE_APP = PM.RACINE_APP; PN.DELAI_DEMARRAGE = 30.0
    e = (await c.get("/api/photolab/natif/etat")).json()
    check("2a photocraft.exe présent", e.get("present") is True, e)
    r = await c.post("/api/photolab/nouveau", json={"width": 64, "height": 32, "background": "white"})
    assert r.status_code == 200, r.text
    await c.post("/api/photolab/executer", json={"command": "layer.new.layer", "params": {"name": "Rouge"}})
    r = await c.post("/api/photolab/natif/ouvrir", json={})
    check("2b la vraie app s'ouvre sur le document (authentifiée, app.open)", r.status_code == 200, (r.status_code, r.text))
    r = await c.post("/api/photolab/natif/reprendre", json={})
    check("2c la vraie app enregistre, le Photolab rouvre", r.status_code == 200, (r.status_code, r.text))
    ins = (await c.get("/api/photolab/inspecter")).json()
    check("2d le document rapporté a ses calques (« Rouge »)", any(L.get("name") == "Rouge" for L in ins.get("layers", [])), ins.get("layers"))
    PN.fermer()
    PM.fermer()


async def scenario():
    import httpx
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t") as c:
        await fake_scenario(c)
        await reel_scenario(c)

try:
    asyncio.run(scenario())
finally:
    try:
        PN.fermer()
    except Exception:
        pass
    PM.fermer()
shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
