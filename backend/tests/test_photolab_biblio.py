# -*- coding: utf-8 -*-
"""t139 (Photolab P4) — la Bibliothèque côté pont : fichier de travail .pcraft lié à l'image enregistrée, lignée
(« retouche » de l'image d'origine), réouverture avec les calques, et jamais de réécriture d'un original.
  [1] faux moteur (tests/faux_photocraft.py) : contrats, index, gardes.
  [2] VRAI moteur photocraft-cli 0.3.0 : le .pcraft rouvert rend les mêmes calques et les mêmes pixels.
      Section rouge si le binaire manque — jamais de saut silencieux.
Run : & $PY tests/test_photolab_biblio.py   (depuis backend/)"""
import asyncio, hashlib, os, pathlib, re, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt139b_"))
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
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:400]}")


D = PM.dossier_travail()
IMAGES = _tmp / "images"
FAUX = [sys.executable, str(BACKEND / "tests" / "faux_photocraft.py"), "serve",
        "--automation-read-root", str(D), "--automation-write-root", str(D)]
PM.FABRIQUE = lambda: PM.SessionMoteur(FAUX, delai_s=5.0)
from PIL import Image                                          # noqa: E402
Image.new("RGB", (8, 8), (200, 30, 30)).save(IMAGES / "rouge.png")
_RACINE0, _CLI0 = PM.RACINE_APP, os.environ.get("PHOTOCRAFT_CLI")
TRAVAIL = re.compile(r"photolab_\d{8}-\d{6}_[A-Za-z0-9_-]+-(png|jpg)\.pcraft")


def empreinte(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


async def fiche(nom):
    from app.services import library_index as LI
    return (await LI.carte()).get(nom) or {}


async def fake_scenario(c):
    print("\n[1] faux moteur")
    from app.services.storage import init_db
    from app.services import library_index as LI
    await init_db()
    r = await c.post("/api/photolab/nouveau", json={"width": 64, "height": 32, "background": "white", "name": "Herbe"})
    assert r.status_code == 200, r.text

    # ── A1 : le fichier de travail ──
    r = await c.post("/api/photolab/bibliotheque", json={"format": "png", "nom": "herbe"})
    j = r.json()
    nom, trav = j.get("filename", ""), j.get("travail") or ""
    check("1a /bibliotheque rend {filename, travail} : le .pcraft porte le nom de l'image (extension comprise)",
          r.status_code == 200 and TRAVAIL.fullmatch(trav) and trav == nom.replace(".png", "-png.pcraft"), j)
    check("1b le .pcraft est écrit sous biblio/ du dossier du moteur, PAS dans la Bibliothèque",
          (D / "biblio" / trav).is_file() and not (IMAGES / trav).exists(), sorted(p.name for p in IMAGES.iterdir()))
    check("1c l'index lie l'image à son fichier de travail (doc_id)", (await fiche(nom)).get("doc_id") == trav, await fiche(nom))
    r2 = await c.post("/api/photolab/bibliotheque", json={"format": "jpg", "quality": 80, "nom": "herbe"})
    nom2, trav2 = r2.json().get("filename", ""), r2.json().get("travail") or ""
    check("1d un JPG du même nom dans la même seconde : un AUTRE fichier de travail (jamais partagé)",
          r2.status_code == 200 and trav2 and trav2 != trav and (D / "biblio" / trav2).is_file(), (trav, trav2))
    e1 = empreinte(D / "biblio" / trav)
    r3 = await c.post("/api/photolab/bibliotheque", json={"format": "png", "nom": "herbe"})
    check("1e un nouvel enregistrement ne réécrit pas le fichier de travail précédent",
          r3.status_code == 200 and empreinte(D / "biblio" / trav) == e1 and r3.json().get("travail") not in (trav, trav2), r3.text)

    # ── A2 : la lignée ──
    r = await c.post("/api/photolab/bibliotheque", json={"format": "png", "nom": "rouge", "parent": "rouge.png"})
    f = await fiche(r.json().get("filename", ""))
    check("2a parent = image de la Bibliothèque -> lignée « retouche »", r.status_code == 200
          and f.get("parent_filename") == "rouge.png" and f.get("relation") == "retouche", f)
    for mauvais in ("../t.db", "absent.png", 12, "a/b.png", ""):
        r = await c.post("/api/photolab/bibliotheque", json={"format": "png", "nom": "x", "parent": mauvais})
        f = await fiche(r.json().get("filename", ""))
        check(f"2b parent {mauvais!r} : enregistré quand même, sans lignée inventée", r.status_code == 200
              and not f.get("parent_filename") and not f.get("relation"), (r.status_code, r.text, f))

    # ── A2 bis : la lignée retrouvée par le PONT (le chemin moteur du document actif), sans que l'écran la donne ──
    Image.new("RGB", (8, 8), (0, 120, 0)).save(IMAGES / "vert.png")
    r = await c.post("/api/photolab/ouvrir", json={"filename": "vert.png"})
    assert r.status_code == 200, r.text
    r = await c.post("/api/photolab/bibliotheque", json={"format": "png", "nom": "vert"})
    f = await fiche(r.json().get("filename", ""))
    check("2c sans `parent` : le pont retrouve l'image ouverte -> lignée « retouche »",
          f.get("parent_filename") == "vert.png" and f.get("relation") == "retouche", f)
    r = await c.post("/api/photolab/bibliotheque", json={"format": "png", "nom": "vert"})
    f = await fiche(r.json().get("filename", ""))
    check("2d un second enregistrement (le moteur a rattaché le document à son fichier de travail) : même mère",
          f.get("parent_filename") == "vert.png", f)
    r = await c.post("/api/photolab/enregistrer", json={"format": "png", "nom": "telecharge"})
    r = await c.post("/api/photolab/bibliotheque", json={"format": "png", "nom": "vert"})
    f = await fiche(r.json().get("filename", ""))
    check("2e après un Exporter… (téléchargement) : toujours la même mère", f.get("parent_filename") == "vert.png", f)
    await c.post("/api/photolab/nouveau", json={"width": 16, "height": 16, "background": "white"})
    r = await c.post("/api/photolab/bibliotheque", json={"format": "png", "nom": "neuf"})
    f = await fiche(r.json().get("filename", ""))
    check("2f un document NEUF n'a pas de mère", not f.get("parent_filename") and not f.get("relation"), f)
    r = await c.post("/api/photolab/bibliotheque", json={"format": "png", "nom": "x", "parent": "rouge.png"})
    f = await fiche(r.json().get("filename", ""))
    check("2g un `parent` explicite (valide) l'emporte sur celui du pont", f.get("parent_filename") == "rouge.png", f)

    # ── A3 : rouvrir avec les calques ──
    avant_img, avant_trav = empreinte(IMAGES / nom), empreinte(D / "biblio" / trav)
    r = await c.post("/api/photolab/ouvrir", json={"filename": nom})
    j = r.json()
    check("3a /ouvrir d'une image Photolab qui a son .pcraft : une COPIE du .pcraft sous entrees/, travail: true",
          r.status_code == 200 and j.get("travail") is True and re.fullmatch(r"entrees/[0-9a-f]{8}-" + re.escape(trav), j.get("path", ""))
          and (D / j["path"]).is_file(), j)
    check("3b ni l'image ni le fichier de travail d'origine ne sont touchés",
          empreinte(IMAGES / nom) == avant_img and empreinte(D / "biblio" / trav) == avant_trav)
    r = await c.post("/api/photolab/ouvrir", json={"filename": nom, "calques": False})
    check("3c calques: false -> l'image aplatie, travail: false", r.status_code == 200 and r.json().get("travail") is False
          and r.json().get("path", "").endswith(nom.replace(".png", ".png")) and not r.json().get("path", "").endswith(".pcraft"), r.text)
    r = await c.post("/api/photolab/ouvrir", json={"filename": "rouge.png"})
    check("3d une image sans fichier de travail : l'image, travail: false", r.status_code == 200
          and r.json().get("travail") is False and r.json().get("path", "").endswith("-rouge.png"), r.text)
    for mauvais in ("oui", 1, None):
        r = await c.post("/api/photolab/ouvrir", json={"filename": nom, "calques": mauvais})
        check(f"3e calques {mauvais!r} (pas un booléen) -> 400", r.status_code == 400, (r.status_code, r.text))
    # un doc_id qui sort du dossier biblio/ (index abîmé ou écrit par un autre) n'est jamais suivi
    (D / "evade.pcraft").write_bytes(b"x")
    await LI.noter([nom2], "photolab", doc_id="../evade.pcraft")
    r = await c.post("/api/photolab/ouvrir", json={"filename": nom2})
    check("3f doc_id « ../evade.pcraft » ignoré : l'image s'ouvre aplatie", r.status_code == 200
          and r.json().get("travail") is False and r.json().get("path", "").endswith(".jpg"), r.text)
    # une image d'une AUTRE source (le doc_id du Vectorlab est l'id d'un document vectoriel) n'ouvre jamais un .pcraft
    Image.new("RGB", (8, 8), (0, 0, 200)).save(IMAGES / "vector_1_bleu.png")
    (D / "biblio").mkdir(parents=True, exist_ok=True)
    # un doc_id de la FORME exacte d'un fichier de travail, présent dans biblio/ : seule la source doit l'arrêter
    (D / "biblio" / "photolab_20261008-000000_bleu-png.pcraft").write_bytes(b"x")
    await LI.noter(["vector_1_bleu.png"], "vectorlab", doc_id="photolab_20261008-000000_bleu-png.pcraft")
    r = await c.post("/api/photolab/ouvrir", json={"filename": "vector_1_bleu.png"})
    check("3g source vectorlab : jamais de fichier de travail Photolab", r.status_code == 200 and r.json().get("travail") is False, r.text)
    (D / "biblio" / trav).unlink()
    r = await c.post("/api/photolab/ouvrir", json={"filename": nom})
    check("3h fichier de travail effacé : l'image s'ouvre quand même (aplatie)", r.status_code == 200
          and r.json().get("travail") is False, r.text)
    PM.fermer()


async def reel_scenario(c):
    print("\n[2] VRAI moteur photocraft-cli")
    PM.fermer()
    PM.FABRIQUE = None
    try:
        cli = PM.chemin_cli()
        check("4a le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", cli.is_file(), cli)
    except PM.MoteurAbsent as e:
        check("4a le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", False, e)
        return

    async def ex(cmd, **p):
        r = await c.post("/api/photolab/executer", json={"command": cmd, "params": p})
        assert r.status_code == 200, (cmd, r.status_code, r.text)
        return r.json()

    async def rendu():
        r = await c.post("/api/photolab/rendu", json={"maxSide": 64})
        assert r.status_code == 200, r.text
        nomr = r.json()["url"].rsplit("/", 1)[1]
        return Image.open(D / "rendus" / nomr).convert("RGBA").tobytes()

    r = await c.post("/api/photolab/nouveau", json={"width": 64, "height": 32, "background": "white"})
    assert r.status_code == 200, r.text
    await ex("layer.new.layer", name="Rouge")
    await ex("tools.setColors", foreground="#ff0000")
    await ex("edit.fill", contents="foreground")
    await ex("layer.setProps", name="Rouge", opacity=0.5)
    await ex("layer.new.layer", name="Vide")
    await ex("layer.setProps", name="Vide", visible=False)
    avant = (await c.get("/api/photolab/inspecter")).json()
    calques = lambda d: [(L["name"], L["visible"], L.get("opacity")) for L in d["layers"]]
    pix_avant = await rendu()
    r = await c.post("/api/photolab/bibliotheque", json={"format": "png", "nom": "reel"})
    nom, trav = r.json().get("filename", ""), r.json().get("travail")
    check("4b /bibliotheque sur le vrai moteur : image + fichier de travail", r.status_code == 200 and trav
          and (D / "biblio" / trav).is_file() and (IMAGES / nom).is_file(), r.text)
    r = await c.post("/api/photolab/ouvrir", json={"filename": nom})
    check("4c le .pcraft s'ouvre (travail: true)", r.status_code == 200 and r.json().get("travail") is True, r.text)
    apres = (await c.get("/api/photolab/inspecter")).json()
    check("4d mêmes calques : noms, visibilité, opacité (le calque masqué le reste)", calques(apres) == calques(avant),
          (calques(avant), calques(apres)))
    check("4e mêmes pixels au rendu", await rendu() == pix_avant)
    r = await c.post("/api/photolab/ouvrir", json={"filename": nom, "calques": False})
    plat = (await c.get("/api/photolab/inspecter")).json()
    check("4f calques: false -> l'image aplatie (un seul calque)", r.status_code == 200 and len(plat["layers"]) == 1, calques(plat))
    # la lignée sur le vrai moteur : il rattache le document au fichier enregistré, le pont doit suivre
    r = await c.post("/api/photolab/ouvrir", json={"filename": "rouge.png"})
    r1 = await c.post("/api/photolab/bibliotheque", json={"format": "png", "nom": "rouge"})
    r2 = await c.post("/api/photolab/bibliotheque", json={"format": "png", "nom": "rouge"})
    f1, f2 = await fiche(r1.json().get("filename", "")), await fiche(r2.json().get("filename", ""))
    check("4g vrai moteur : deux enregistrements successifs d'une image ouverte -> même mère « retouche »",
          f1.get("parent_filename") == f2.get("parent_filename") == "rouge.png" and f2.get("relation") == "retouche", (f1, f2))
    PM.fermer()


async def scenario():
    import httpx
    from app.main import app
    _json0 = httpx.Response.json

    def _json_tolerant(self, *a, **k):
        try:
            return _json0(self, *a, **k)
        except ValueError:
            return {}
    httpx.Response.json = _json_tolerant
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t") as c:
        await fake_scenario(c)
        await reel_scenario(c)

try:
    asyncio.run(scenario())
finally:
    PM.fermer()
    PM.RACINE_APP = _RACINE0
    if _CLI0 is None:
        os.environ.pop("PHOTOCRAFT_CLI", None)
    else:
        os.environ["PHOTOCRAFT_CLI"] = _CLI0
shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
