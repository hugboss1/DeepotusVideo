# -*- coding: utf-8 -*-
"""t421 (cartes hexagonales, tâche 1) — les noms d'image accentués passent le Photolab et le renommage.

Constat du 05/11 : 53 des 93 cartes réelles portent un accent (« adrian_veilleur_des_âmes_fracturées.png »), et
/api/photolab/ouvrir les refusait (« nom d'image refusé »). Ce banc, sur un dossier jetable et le FAUX moteur :
  [1] /ouvrir et /actions/lot acceptent le nom accentué (NFC et NFD), refusent séparateurs, « .. », retour à la ligne ;
  [2] un nom de périphérique Windows n'ouvre rien (introuvable ici) ;
  [3] le renommage garde « été » ;
  [4] /bibliotheque sans `nom` retire l'empreinte et le « -png » : base « carte » ;
  [5] _base_defaut (helper pur).
Run : & $PY tests/test_noms_accentues.py   (depuis backend/)
"""
import asyncio, os, pathlib, re, shutil, sys, tempfile, unicodedata
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt421n_"))
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
        fail += 1; print(f"  FAIL  {label} {str(detail)[:300]}")


D = PM.dossier_travail()
FAUX = [sys.executable, str(BACKEND / "tests" / "faux_photocraft.py"), "serve",
        "--automation-read-root", str(D), "--automation-write-root", str(D)]
PM.FABRIQUE = lambda: PM.SessionMoteur(FAUX, delai_s=3.0)
from PIL import Image                                          # noqa: E402
NFC = "adrian_veilleur_des_âmes_fracturées.png"
NFD = unicodedata.normalize("NFD", NFC)
for n in (NFC, NFD, "carte.png", "été.png"):
    Image.new("RGB", (8, 8), (200, 30, 30)).save(_tmp / "images" / n)
check("0 les deux formes sont deux fichiers distincts", NFC != NFD and len(list((_tmp / "images").glob("adrian*"))) in (1, 2))
_RACINE0, _CLI0 = PM.RACINE_APP, os.environ.get("PHOTOCRAFT_CLI")


async def scenario():
    import httpx
    from app.main import app
    from app.api import photolab_routes as PR, routes
    from app.services.storage import init_db
    await init_db()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t") as c:
        print("\n[1] /ouvrir")
        for etiquette, nom in (("NFC", NFC), ("NFD", NFD)):
            r = await c.post("/api/photolab/ouvrir", json={"filename": nom})
            check(f"1a /ouvrir accepte le nom accentué ({etiquette})", r.status_code == 200
                  and re.fullmatch(r"entrees/[0-9a-f]{8}-[A-Za-z0-9._-]+\.png", r.json().get("path", "")), (r.status_code, r.text))
        avant = sorted(x.name for x in (D / "entrees").iterdir())
        for mauvais in ("a/b.png", "a\b.png", "..", "x\n.png", "../t.db", "a:b.png", ""):
            r = await c.post("/api/photolab/ouvrir", json={"filename": mauvais})
            check(f"1b /ouvrir refuse {mauvais!r} (400)", r.status_code == 400, (r.status_code, r.text))
        for absent in ("con.png", "nul.txt"):
            r = await c.post("/api/photolab/ouvrir", json={"filename": absent})
            check(f"1c /ouvrir {absent!r} : rien d'ouvert (introuvable)", r.status_code == 404, (r.status_code, r.text))
        check("1d aucun fichier copié par ces refus", sorted(x.name for x in (D / "entrees").iterdir()) == avant)

        print("\n[2] /actions/lot")
        for etiquette, nom in (("NFC", NFC), ("NFD", NFD)):
            r = await c.post("/api/photolab/actions/lot", json={"action": "absente", "filename": nom})
            check(f"2a /actions/lot ({etiquette}) passe la garde du nom (le refus vient de l'action, pas du nom)",
                  "nom d'image refusé" not in r.text, (r.status_code, r.text))
        for mauvais in ("a/b.png", "a\b.png", "..", "x\n.png"):
            r = await c.post("/api/photolab/actions/lot", json={"action": "x", "filename": mauvais})
            check(f"2b /actions/lot refuse {mauvais!r}", r.status_code == 400 and "nom d'image refusé" in r.text, (r.status_code, r.text))

        print("\n[3] /bibliotheque sans nom")
        r = await c.post("/api/photolab/ouvrir", json={"filename": "carte.png"})
        check("3a une image est ouverte", r.status_code == 200, r.text)
        vrai = PR._appeler

        async def appeler(methode, params=None, delai_s=None):
            if methode == "doc.inspect":                       # le faux moteur nomme tout « Ouvert » : on lui prête le vrai nom
                return {"name": "544a527f-carte.png"}, 1
            return await vrai(methode, params, delai_s)
        PR._appeler = appeler
        try:
            r = await c.post("/api/photolab/bibliotheque", json={"format": "png"})
        finally:
            PR._appeler = vrai
        check("3b document « 544a527f-carte.png » : base « carte », ni empreinte ni -png", r.status_code == 200
              and re.fullmatch(r"photolab_\d{8}-\d{6}_carte\.png", r.json().get("filename", "")), (r.status_code, r.text))

        print("\n[4] renommage")
        out = routes._safe_rename_image("été.png", "Âme d'été ?")
        check("4a le renommage garde les accents, remplace ce qui est interdit", out == "Âme d_été.png", out)
        out2 = routes._safe_rename_image("carte.png", "été")
        check("4b « été » reste « été »", out2 == "été.png", out2)
        check("4c le nom rendu passe la garde de /ouvrir", PR._NOM_IMAGE.fullmatch(out2) is not None)
    PM.fermer()


print("\n[5] _base_defaut (helper pur)")


def pur():
    from app.api import photolab_routes as PR
    for brut, attendu in (("544a527f-carte.png", "carte"), ("photolab_20261008-154030_herbe-png.pcraft", "herbe"),
                          ("photolab_20261008-154030_herbe.png", "herbe"), ("carte", "carte"),
                          ("544a527f-âme_brisée.png", "ame_brisee")):
        check(f"5 _base_defaut({brut!r}) -> {attendu!r}", PR._base_defaut(brut) == attendu, PR._base_defaut(brut))


pur()
asyncio.run(scenario())
PM.fermer()
PM.RACINE_APP = _RACINE0
if _CLI0 is None:
    os.environ.pop("PHOTOCRAFT_CLI", None)
else:
    os.environ["PHOTOCRAFT_CLI"] = _CLI0
shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
