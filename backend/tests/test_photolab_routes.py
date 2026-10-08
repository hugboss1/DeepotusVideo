# -*- coding: utf-8 -*-
"""t136 (Photolab P1) — les routes /api/photolab avec le FAUX moteur (tests/faux_photocraft.py).
Run : & $PY tests/test_photolab_routes.py   (depuis backend/)"""
import asyncio, os, pathlib, re, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt136r_"))
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
Image.new("RGB", (8, 8), (200, 30, 30)).save(_tmp / "images" / "rouge.png")
Image.new("RGB", (8, 8), (30, 200, 30)).save(_tmp / "images" / "nul.png")   # nom de périphérique Windows
_RACINE0, _CLI0 = PM.RACINE_APP, os.environ.get("PHOTOCRAFT_CLI")          # restaurés en fin de banc
GEN = "X-Photolab-Generation"


async def scenario():
    import httpx
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t") as c:
        e = (await c.get("/api/photolab/etat")).json()
        check("1 /etat : version 0.3.0, generation 0 avant la première demande", e.get("version") == "0.3.0"
              and e.get("generation") == 0, e)
        r = await c.post("/api/photolab/nouveau", json={"width": 64, "height": 32, "background": "white"})
        check("2 /nouveau crée un document", r.status_code == 200 and r.json().get("document") == 0, r.text)
        check("2b /nouveau porte l'en-tête X-Photolab-Generation = 1 (corps JSON inchangé)",
              r.headers.get(GEN) == "1" and "generation" not in r.json(), dict(r.headers))
        r = await c.post("/api/photolab/nouveau", json={"width": 0, "height": 32})
        check("3 /nouveau borné (1..30000)", r.status_code == 400, r.status_code)
        r = await c.post("/api/photolab/ouvrir", json={"filename": "rouge.png"})
        p4 = r.json().get("path", "")
        check("4 /ouvrir copie l'image de la Bibliothèque dans entrees/ sous un nom UNIQUE (hash-nom) et l'ouvre par chemin RELATIF",
              r.status_code == 200 and re.fullmatch(r"entrees/[0-9a-f]{8}-rouge\.png", p4) and (D / p4).is_file(), r.text)
        r = await c.post("/api/photolab/ouvrir", json={"filename": "rouge.png"})
        check("4b rouvrir la même image réutilise la même copie (nom stable)", r.json().get("path") == p4, r.text)
        avant = sorted(x.name for x in (D / "entrees").iterdir())
        for mauvais in ("rouge.png.", "rouge.png ", "rouge. "):
            r = await c.post("/api/photolab/ouvrir", json={"filename": mauvais})
            check(f"4c /ouvrir {mauvais!r} : 400, jamais un 500", r.status_code == 400, (r.status_code, r.text))
        check("4d aucun fichier copié par ces refus", sorted(x.name for x in (D / "entrees").iterdir()) == avant)
        r = await c.post("/api/photolab/ouvrir", json={"filename": "nul.png"})
        check("4e « nul.png » (nom de périphérique) s'ouvre sous entrees/<hash>-nul_.png",
              r.status_code == 200 and re.fullmatch(r"entrees/[0-9a-f]{8}-nul_\.png", r.json().get("path", "")), r.text)
        # mutation t136 : un lien symbolique DANS la Bibliothèque qui pointe dehors ne doit rien faire entrer
        (_tmp / "dehors.png").write_bytes((_tmp / "images" / "rouge.png").read_bytes())
        lien = _tmp / "images" / "lien.png"
        try:
            os.symlink(_tmp / "dehors.png", lien)
            avant_lien = sorted(x.name for x in (D / "entrees").iterdir())
            r = await c.post("/api/photolab/ouvrir", json={"filename": "lien.png"})
            check("4f un lien symbolique de la Bibliothèque qui sort du dossier -> 400, rien de copié",
                  r.status_code == 400 and sorted(x.name for x in (D / "entrees").iterdir()) == avant_lien, (r.status_code, r.text))
        except OSError as e:
            check("4f lien symbolique créable sur cette machine (sinon la garde n'est pas éprouvée)", False, e)
        for mauvais in ("../t.db", "absent.png", "a/b.png"):
            r = await c.post("/api/photolab/ouvrir", json={"filename": mauvais})
            check(f"5 /ouvrir refuse {mauvais}", r.status_code in (400, 404), (r.status_code, r.text))
        r = await c.post("/api/photolab/executer", json={"command": "filter.blur.gaussianBlur", "params": {"radius": 3}})
        check("6 /executer passe la commande et ses paramètres", r.status_code == 200
              and r.json() == {"command": "filter.blur.gaussianBlur", "params": {"radius": 3}}, r.text)
        r = await c.post("/api/photolab/executer", json={"command": "file.saveAs", "params": {"path": "C:/x.psd"}})
        check("7 /executer refuse une commande de fichier (400)", r.status_code == 400, r.status_code)
        r = await c.post("/api/photolab/executer", json={"command": "dz.erreur"})
        check("8 erreur du moteur -> 422 avec son message", r.status_code == 422 and "no active layer" in r.text, r.text)
        r = await c.post("/api/photolab/rendu", json={"maxSide": 512})
        j = r.json()
        check("9 /rendu écrit un fichier PROPRE À CE RENDU (generation-n) et rend son URL, sans ?v",
              r.status_code == 200 and re.fullmatch(r"/api/photolab/rendus/apercu-1-\d+\.png", j.get("url", "")) and "ms" in j, j)
        check("9b /rendu porte l'en-tête de génération", r.headers.get(GEN) == "1", dict(r.headers))
        f = await c.get(j["url"])
        check("10 l'aperçu est servi en image/png, jamais mis en cache", f.status_code == 200
              and f.headers["content-type"] == "image/png" and f.headers.get("cache-control") == "no-store"
              and f.content.startswith(b"\x89PNG"), (f.status_code, dict(f.headers)))
        for _ in range(5):
            await c.post("/api/photolab/rendu", json={"maxSide": 256})
        restants = [x.name for x in (D / "rendus").iterdir() if re.fullmatch(r"apercu-\d+-\d+\.png", x.name)]
        check("10b après 6 rendus, seuls les 3 derniers aperçus restent (et aucun temporaire)",
              len(restants) == 3 and len(list((D / "rendus").iterdir())) == 3, sorted(x.name for x in (D / "rendus").iterdir()))
        r = await c.post("/api/photolab/rendu", json={"maxSide": 99999})
        check("11 /rendu borné (64..8192)", r.status_code == 400, r.status_code)
        r = await c.post("/api/photolab/enregistrer", json={"format": "psd", "nom": "Mon essai"})
        j = r.json()
        check("12 /enregistrer écrit dans exports/ sous un nom sûr et le sert",
              r.status_code == 200 and j.get("fichier") == "Mon-essai.psd" and (D / "exports" / "Mon-essai.psd").is_file(), j)
        check("12b /enregistrer porte l'en-tête de génération", r.headers.get(GEN) == "1", dict(r.headers))
        f = await c.get(j["url"])
        check("12c l'export est servi avec son nom de téléchargement", "Mon-essai.psd" in f.headers.get("content-disposition", ""),
              dict(f.headers))
        r = await c.post("/api/photolab/enregistrer", json={"format": "psd", "nom": "Con"})
        check("12d /enregistrer « Con » (nom de périphérique) -> Con_.psd", r.status_code == 200
              and r.json().get("fichier") == "Con_.psd", r.text)
        noms = []
        for nom in ("Photo d'été", "Photo d'été", "写真", "写真"):
            r = await c.post("/api/photolab/enregistrer", json={"format": "psd", "nom": nom})
            noms.append(r.json().get("fichier") if r.status_code == 200 else r.status_code)
        check("12e noms translittérés en ASCII, jamais d'écrasement (-2)",
              noms == ["Photo-d-ete.psd", "Photo-d-ete-2.psd", "photolab.psd", "photolab-2.psd"], noms)
        r = await c.post("/api/photolab/enregistrer", json={"format": "exe"})
        check("13 /enregistrer : format hors liste refusé", r.status_code == 400, r.status_code)
        # Cibles RÉELLES au bon endroit : un sentinelle un cran au-dessus de rendus/ et exports/ (dossier photolab/) et
        # deux crans au-dessus (dossier de données), plus la base si elle existe déjà.
        SENT = b"SECRET-T136"
        (D / "secret.txt").write_bytes(SENT)
        (_tmp / "secret.txt").write_bytes(SENT)
        check("14a les cibles de traversée existent bel et bien", (D / "secret.txt").is_file()
              and (_tmp / "secret.txt").is_file())
        index = (BACKEND.parent / "frontend" / "dist" / "index.html").read_bytes()
        for chemin in ("/api/photolab/rendus/..%2Fsecret.txt", "/api/photolab/exports/..%2F..%2Fsecret.txt",
                       "/api/photolab/rendus/..%2Ft.db", "/api/photolab/exports/..%5Ct.db",
                       "/api/photolab/rendus/..%2F..%2Fsecret.txt", "/api/photolab/rendus/absent.png",
                       # mutation t136 : « ..\ » atteint la route (le %5C n'est pas un séparateur d'URL) et vise la
                       # sentinelle UN cran au-dessus de rendus/ — seule la regex du nom servi la refuse
                       "/api/photolab/rendus/..%5Csecret.txt", "/api/photolab/exports/..%5Csecret.txt"):
            r = await c.get(chemin)
            # %2F décodé en « / » : la route ne correspond plus et le catch-all de l'application sert son index.html
            # (200 text/html). N'est accepté que ce index.html exact, sans un octet de la cible.
            propre = SENT not in r.content and b"SQLite format" not in r.content
            spa = (r.status_code == 200 and r.headers.get("content-type", "").startswith("text/html")
                   and (r.content == index or b'<div id="root">' in r.content))
            check(f"14 {chemin} : 400/404, ou l'index.html de l'application sans octet de la cible",
                  propre and (r.status_code in (400, 404) or spa), (r.status_code, r.content[:60]))
        # t138 A2 : le faux moteur sert la copie du registre réel (776 entrées + les commandes dz.* du banc) ; chaque
        # entrée de /commandes gagne ses « champs » structurés, calculés UNE fois par génération du moteur.
        from app.services import photolab_registre as PR
        appels = []
        _structurer0 = PR.structurer
        PR.structurer = lambda cmds: (appels.append(1), _structurer0(cmds))[1]
        try:
            PM._CACHE_REGISTRE.update({"session": None, "gen": None, "registre": None})
            r = await c.get("/api/photolab/commandes")
            j = r.json() if r.status_code == 200 else []
            g = next((x for x in j if x.get("id") == "filter.blur.gaussianBlur"), {})
            check("15 /commandes rend le registre du moteur (776 entrées réelles + dz.*)", r.status_code == 200
                  and len([x for x in j if not x["id"].startswith("dz.")]) == 776 and g.get("params") == '{"radius":0.1..1000=1}',
                  r.text[:200])
            check("15b chaque entrée porte ses champs (gaussianBlur : radius number 0.1..1000)",
                  all("champs" in x for x in j) and [(f["cle"], f["type"], f.get("min"), f.get("max")) for f in g.get("champs", [])]
                  == [("radius", "number", 0.1, 1000)], g)
            await c.get("/api/photolab/commandes")
            await c.post("/api/photolab/executer", json={"command": "filter.blur.gaussianBlur", "params": {"radius": 2}})
            await c.post("/api/photolab/executer", json={"command": "select.all"})
            await c.get("/api/photolab/commandes")
            check("15c registre structuré UNE seule fois pour 3 /commandes + 2 /executer (même génération)", len(appels) == 1, len(appels))
        finally:
            PR.structurer = _structurer0
        for corps, motif in (({"command": "filter.blur.gaussianBlur", "params": {"radius": 4, "zorglub": 1}}, "paramètre inconnu : zorglub"),
                             ({"command": "filter.blur.gaussianBlur", "params": {"radius": 5000}}, "0.1..1000"),
                             ({"command": "filter.zorg", "params": {}}, "inconnue du moteur"),
                             ({"command": "image.mode.rgb", "params": {"profile": "C:/x.icc"}}, "réservée"),
                             ({"command": "layer.setProps", "params": {"blend": "zorg"}}, "mode de fusion")):
            r = await c.post("/api/photolab/executer", json=corps)
            check(f"15d /executer refuse {corps['command']} {corps['params']} (400, « {motif} »)",
                  r.status_code == 400 and motif in r.json().get("detail", ""), (r.status_code, r.text))
        # une commande illisible ne démarre pas le moteur : refusée AVANT la lecture du registre (session qui lève)
        class Interdite:
            def appeler_g(self, *a, **k):
                raise AssertionError("le moteur ne doit pas être sollicité")
        vraie, PM._SESSION = PM._SESSION, Interdite()
        try:
            r = await c.post("/api/photolab/executer", json={"command": "../x"})
        finally:
            PM._SESSION = vraie
        check("15o commande illisible : 400 sans aucun appel au moteur", r.status_code == 400 and "illisible" in r.text,
              (r.status_code, r.text))
        # layer.setAdjustment : le kind vient du calque visé (doc.inspect), jamais de l'écran
        r = await c.post("/api/photolab/executer", json={"command": "layer.setAdjustment", "params": {"layer": 5, "lut": "warm"}})
        check("15e setAdjustment sur le calque Color Lookup (5) : clé de colorLookup admise", r.status_code == 200
              and r.json().get("command") == "layer.setAdjustment", (r.status_code, r.text))
        r = await c.post("/api/photolab/executer", json={"command": "layer.setAdjustment", "params": {"layer": 5, "gamma": 1.2}})
        check("15f setAdjustment : une clé d'un AUTRE kind (gamma des niveaux) -> 400", r.status_code == 400
              and "gamma" in r.text, (r.status_code, r.text))
        for p in ({"layer": 1, "lut": "warm"}, {"lut": "warm"}):
            r = await c.post("/api/photolab/executer", json={"command": "layer.setAdjustment", "params": p})
            check(f"15g setAdjustment {p} sur un calque de pixels (1 ; ou l'actif) -> 400 « pas un calque de réglage »",
                  r.status_code == 400 and "pas un calque de réglage" in r.text, (r.status_code, r.text))
        r = await c.post("/api/photolab/executer", json={"command": "layer.setAdjustment", "params": {"layer": 999, "lut": "warm"}})
        check("15h setAdjustment sur un calque absent -> 400", r.status_code == 400 and "999" in r.text, (r.status_code, r.text))
        # réglage Niveaux (6) DANS le groupe 3 : le kind est trouvé en descendant dans children
        r = await c.post("/api/photolab/executer", json={"command": "layer.setAdjustment", "params": {"layer": 6, "gamma": 1.4}})
        check("15k setAdjustment sur le Levels imbriqué (6) : gamma admis (kind levels trouvé dans le groupe)",
              r.status_code == 200 and r.json().get("params") == {"layer": 6, "gamma": 1.4}, (r.status_code, r.text))
        r = await c.post("/api/photolab/executer", json={"command": "layer.setAdjustment", "params": {"layer": 6, "lut": "warm"}})
        check("15l setAdjustment sur le Levels imbriqué : clé de colorLookup -> 400", r.status_code == 400 and "lut" in r.text,
              (r.status_code, r.text))
        # sans `layer` : la cible lue dans doc.inspect (calque actif) est FIGÉE dans les paramètres envoyés
        PM.session().appeler("engine.execute", {"command": "dz.actif", "params": {"layer": 5}})
        r = await c.post("/api/photolab/executer", json={"command": "layer.setAdjustment", "params": {"lut": "warm"}})
        check("15m setAdjustment sans layer, actif = Color Lookup (5) : envoyé avec layer 5 figé",
              r.status_code == 200 and r.json().get("params") == {"lut": "warm", "layer": 5}, (r.status_code, r.text))
        # hueSaturation : bornes de colorisation lues dans l'ÉTAT du calque visé (doc.inspect), pas déclarées par l'écran
        HS = {"HueSaturation": {"colorize": True, "hue": 200.0, "saturation": 40.0, "lightness": 0.0, "ranges": []}}
        PM.session().appeler("engine.execute", {"command": "dz.reglage", "params": {"layer": 20, "adjustment": HS}})
        PM.session().appeler("engine.execute", {"command": "dz.reglage", "params": {"layer": 21, "adjustment": {
            "HueSaturation": {**HS["HueSaturation"], "colorize": False, "hue": 0.0, "saturation": 0.0}}}})
        r = await c.post("/api/photolab/executer", json={"command": "layer.setAdjustment", "params": {"layer": 20, "hue": 200}})
        check("15p setAdjustment hue 200 sur un calque DÉJÀ colorisé (20) : admis", r.status_code == 200, (r.status_code, r.text))
        r = await c.post("/api/photolab/executer", json={"command": "layer.setAdjustment", "params": {"layer": 21, "hue": 200}})
        check("15q setAdjustment hue 200 sur un calque NON colorisé (21) : 400 hors bornes", r.status_code == 400
              and "hue" in r.text, (r.status_code, r.text))
        r = await c.post("/api/photolab/executer", json={"command": "layer.setAdjustment",
                                                         "params": {"layer": 21, "colorize": True, "hue": 200}})
        check("15r setAdjustment colorize:true dans les paramètres PRIME sur l'état non colorisé", r.status_code == 200,
              (r.status_code, r.text))
        r = await c.post("/api/photolab/executer", json={"command": "layer.newAdjustmentLayer.hueSaturation",
                                                         "params": {"colorize": True, "hue": 200, "saturation": 40}})
        check("15s création colorize hue 200 : admise", r.status_code == 200, (r.status_code, r.text))
        PM.session().appeler("engine.execute", {"command": "dz.actif", "params": {"layer": 1}})
        for corps in ({"command": "FILTER.blur"}, {"command": None}, {"command": "a..b"}):
            r = await c.post("/api/photolab/executer", json=corps)
            check(f"15n commande illisible {corps['command']!r} -> 400 « illisible »", r.status_code == 400
                  and "illisible" in r.text, (r.status_code, r.text))
        r = await c.get("/api/photolab/inspecter")
        cl = next((L for L in r.json().get("layers", []) if L.get("id") == 5), {}).get("adjustment", {}).get("ColorLookup", {})
        check("15i /inspecter élague la LUT du Color Lookup (lut None, lutElague)", cl.get("lut") is None and cl.get("lutElague") is True
              and cl.get("name") == "Warm Filter", cl)
        await c.post("/api/photolab/executer", json={"command": "dz.modifier"})
        r = await c.post("/api/photolab/historique", json={"annuler": 1})
        cl = next((L for L in r.json().get("inspect", {}).get("layers", []) if L.get("id") == 5), {}).get("adjustment", {}).get("ColorLookup", {})
        check("15j /historique élague aussi l'inspect qu'il rend", r.status_code == 200 and cl.get("lut") is None
              and cl.get("lutElague") is True, (r.status_code, cl))
        appels = []
        PR.structurer = lambda cmds: (appels.append(1), _structurer0(cmds))[1]
        try:
            r = await c.post("/api/photolab/executer", json={"command": "dz.mourir"})
            e = (await c.get("/api/photolab/etat")).json()
            r2 = await c.post("/api/photolab/executer", json={"command": "dz.pid"})
            e2 = (await c.get("/api/photolab/etat")).json()
            await c.post("/api/photolab/executer", json={"command": "select.all"})
            await c.get("/api/photolab/commandes")
        finally:
            PR.structurer = _structurer0
        check("16 moteur mort : 422 dit, puis relancé ; /etat montre la nouvelle generation",
              r.status_code == 422 and r2.status_code == 200 and e2["generation"] == e["generation"] + 1, (r.text, e, e2))
        check("16b l'en-tête de génération passe de 1 à 2 après le redémarrage",
              r2.headers.get(GEN) == str(e2["generation"]) == "2", (dict(r2.headers), e2))
        check("16c moteur mort puis relancé : le registre est relu et structuré UNE fois de plus (puis vient du cache)",
              len(appels) == 1, len(appels))
        # 19 : délai dépassé -> 504 (session de remplacement, comme pour le 409)
        class Lente:
            def appeler_g(self, *a, **k):
                raise PM.MoteurDelai("doc.render : pas de réponse en 60 s")
        vraie, PM._SESSION = PM._SESSION, Lente()
        try:
            r = await c.post("/api/photolab/rendu", json={})
        finally:
            PM._SESSION = vraie
        check("19 délai dépassé : 504 avec le message", r.status_code == 504 and "pas de réponse" in r.text, (r.status_code, r.text))
        # 18 : MoteurOccupe -> 409. Un vrai verrou tenu serait une course contre le délai ; on remplace la session.
        class Occupee:
            def appeler_g(self, *a, **k):
                raise PM.MoteurOccupe("moteur occupé : une opération est en cours")
        vraie, PM._SESSION = PM._SESSION, Occupee()
        try:
            r = await c.post("/api/photolab/executer", json={"command": "dz.pid"})
            r3 = await c.post("/api/photolab/nouveau", json={"width": 8, "height": 8})
        finally:
            PM._SESSION = vraie
        check("18 moteur occupé : 409 avec le message", r.status_code == 409 and "occupé" in r.text
              and r3.status_code == 409, (r.status_code, r.text, r3.status_code))
    PM.fermer()
    PM.FABRIQUE = None
    os.environ["PHOTOCRAFT_CLI"] = str(_tmp / "absent.exe")
    PM.RACINE_APP = _tmp
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t") as c:
        r = await c.post("/api/photolab/nouveau", json={"width": 8, "height": 8})
        e = (await c.get("/api/photolab/etat")).json()
        check("17 moteur absent : 503 qui dit comment le fournir ; /etat present:false",
              r.status_code == 503 and "vendor_photocraft.py" in r.text and e.get("present") is False, (r.text, e))
    # Hygiène : le banc ne laisse derrière lui ni variable d'environnement, ni racine modifiée, ni dossier temporaire.
    PM.fermer()
    PM.RACINE_APP = _RACINE0
    if _CLI0 is None:
        os.environ.pop("PHOTOCRAFT_CLI", None)
    else:
        os.environ["PHOTOCRAFT_CLI"] = _CLI0

asyncio.run(scenario())
shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
