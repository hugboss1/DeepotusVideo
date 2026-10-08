# -*- coding: utf-8 -*-
"""t153 (Photolab parité L3) — panneaux Nuancier, Dégradés, Motifs, Histogramme, Infos, Couches, Compositions.
[1] service photolab_nuancier : défaut (les 40 nuances de l'amont en 4 groupes), validation STRICTE, lecture tolérante,
    écriture atomique ; [2] routes GET / PUT /api/photolab/nuancier ; [3] la copie JavaScript du défaut est identique.
[4] VRAI moteur — vignette d'un motif (document temporaire refermé, original intact, cache, refus) ;
[5] VRAI moteur — contenu des couches alpha (copie refermée, blanc = sélectionné, original intact, aucun fichier laissé) ;
[6] la liste blanche du pont admet les commandes des panneaux et refuse les familles qui lisent un fichier ;
[7] routes /motifs/{id}.png et /couches.
Section VRAI moteur rouge si le binaire manque (PHOTOCRAFT_CLI dans un worktree).
Run : & $PY -X utf8 tests/test_photolab_panneaux3.py   (depuis backend/)"""
import asyncio, copy, io, json, os, pathlib, shutil, subprocess, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt153_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
RACINE = BACKEND.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_moteur as PM              # noqa: E402
from app.services import photolab_nuancier as N             # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:500]}")


def refuse(obj):
    try:
        N.valider(obj)
        return False
    except ValueError:
        return True


def service():
    print("\n[1] service du nuancier")
    d = N.etat_defaut()
    check("1a défaut : 4 groupes fournis (gris, pastels, vives, foncees), 10 nuances chacun, aucune récente",
          [g["id"] for g in d["groupes"]] == ["gris", "pastels", "vives", "foncees"]
          and all(len(g["couleurs"]) == 10 for g in d["groupes"]) and d["recentes"] == [], d)
    check("1b les 40 nuances de l'amont, du noir au violet foncé", d["groupes"][0]["couleurs"][0]["hex"] == "#000000"
          and d["groupes"][3]["couleurs"][9]["hex"] == "#6e145a" and d["groupes"][2]["couleurs"][0]["hex"] == "#e62828")
    check("1c le défaut est admis tel quel", N.valider(copy.deepcopy(d)) == d)
    ajout = copy.deepcopy(d)
    ajout["groupes"].append({"id": "g-1", "nom": "  Ma marque ", "couleurs": [{"hex": "#123456", "nom": "Bleu nuit"}]})
    ajout["recentes"] = ["#ff0000", "#00ff00"]
    v = N.valider(copy.deepcopy(ajout))
    check("1d un groupe créé et des récentes sont admis ; noms rendus sans espaces autour", v["groupes"][4]["nom"] == "Ma marque", v["groupes"][4])
    mauvais = {
        "1e couleur en majuscules": lambda o: o["groupes"][0]["couleurs"][0].update(hex="#FFFFFF"),
        "1f couleur sur 3 chiffres": lambda o: o["groupes"][0]["couleurs"][0].update(hex="#fff"),
        "1g clé inconnue dans une nuance": lambda o: o["groupes"][0]["couleurs"][0].update(chemin="c:/x"),
        "1h id de groupe mal formé": lambda o: o["groupes"][0].update(id="../x"),
        "1i id de groupe en double": lambda o: o["groupes"].append(copy.deepcopy(o["groupes"][0])),
        "1j groupe créé sans nom": lambda o: o["groupes"].append({"id": "g-2", "nom": " ", "couleurs": []}),
        "1k nom sur deux lignes": lambda o: o["groupes"][0]["couleurs"][0].update(nom="a\nb"),
        "1l plus de 12 récentes": lambda o: o.update(recentes=["#000000"] * 13),
        "1m version inconnue": lambda o: o.update(version=2),
        "1n clé manquante": lambda o: o.pop("recentes"),
    }
    for lib, f in mauvais.items():
        o = copy.deepcopy(d)
        f(o)
        check(lib + " -> refusé", refuse(o))
    N.chemin().parent.mkdir(parents=True, exist_ok=True)
    N.chemin().write_text("{pas du json", encoding="utf-8")
    check("1o fichier corrompu -> défaut", N.lire() == N.etat_defaut())
    N.ecrire(copy.deepcopy(ajout))
    lu = N.lire()
    check("1p écrire puis lire : aller-retour", lu["groupes"][4]["couleurs"][0] == {"hex": "#123456", "nom": "Bleu nuit"} and lu["recentes"] == ["#ff0000", "#00ff00"], lu)
    check("1q écriture atomique : aucun fichier temporaire laissé", [p.name for p in N.chemin().parent.iterdir()] == ["nuancier.json"],
          list(N.chemin().parent.iterdir()))
    N.chemin().unlink()


async def routes_nuancier():
    print("\n[2] routes /api/photolab/nuancier")
    import httpx
    from app.main import app
    t = httpx.ASGITransport(app=app, client=("127.0.0.1", 5000))
    async with httpx.AsyncClient(transport=t, base_url="http://t") as c:
        r = await c.get("/api/photolab/nuancier")
        check("2a GET sans fichier : 200, défaut", r.status_code == 200 and r.json() == N.etat_defaut(), r.text[:200])
        e = N.etat_defaut()
        e["recentes"] = ["#abcdef"]
        r = await c.put("/api/photolab/nuancier", json=e)
        check("2b PUT : 200, état rendu", r.status_code == 200 and r.json()["recentes"] == ["#abcdef"], r.text[:200])
        r = await c.get("/api/photolab/nuancier")
        check("2c GET relit l'état écrit", r.json()["recentes"] == ["#abcdef"], r.text[:200])
        avant = N.chemin().read_bytes()
        e["recentes"] = ["rouge"]
        r = await c.put("/api/photolab/nuancier", json=e)
        check("2d PUT refusé : 400 qui dit pourquoi, fichier intact", r.status_code == 400 and "recentes" in r.text
              and N.chemin().read_bytes() == avant, (r.status_code, r.text[:200]))
    t2 = httpx.ASGITransport(app=app, client=("192.168.1.20", 5000))
    async with httpx.AsyncClient(transport=t2, base_url="http://t") as c:
        r = await c.put("/api/photolab/nuancier", json=N.etat_defaut())
        check("2e PUT depuis le réseau local : refusé (401/403), fichier intact", r.status_code in (401, 403) and N.chemin().read_bytes() == avant,
              (r.status_code, r.text[:200]))


def copie_js():
    print("\n[3] copie JavaScript du défaut")
    mod = (RACINE / "frontend" / "photolab" / "js" / "mod-nuancier.js").as_uri()
    r = subprocess.run(["node", "--input-type=module", "-e",
                        f"import {{ etatDefaut }} from '{mod}'; console.log(JSON.stringify(etatDefaut()))"],
                       capture_output=True, text=True, encoding="utf-8")
    try:
        js = json.loads(r.stdout)
    except ValueError:
        js = None
    check("3a mod-nuancier.etatDefaut() == photolab_nuancier.etat_defaut()", js == N.etat_defaut(), (r.stdout[:300], r.stderr[:300]))


def moteur():
    print("\n[4-6] VRAI moteur")
    PM.fermer()
    PM.FABRIQUE = None
    try:
        cli = PM.chemin_cli()
        check("4a le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", cli.is_file(), cli)
    except PM.MoteurAbsent as e:
        check("4a le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", False, e)
        return None
    from PIL import Image
    s = PM.session()
    ex = lambda c, **p: s.appeler("engine.execute", {"command": c, "params": p})
    pl = ex("pattern.presets.list")
    motifs = {m["name"]: m["id"] for g in pl["groups"] for m in g["patterns"]}
    # Vignette SANS document ouvert : le document temporaire est refermé, il ne reste rien d'ouvert.
    octets, _ = PM.vignette_motif(s, motifs["Checkerboard"])
    im = Image.open(io.BytesIO(octets))
    couleurs = im.convert("RGB").getcolors(4096) or []
    check("4b sans document : PNG 64×64 du damier, au moins deux couleurs", im.size == (64, 64) and len(couleurs) >= 2, (im.size, len(couleurs)))
    check("4c sans document : aucun document laissé ouvert", (s.appeler("session.list").get("documents") or []) == [], s.appeler("session.list"))
    s.appeler("doc.new", {"width": 120, "height": 80, "background": "white"})
    ex("paint.bucket", x=1, y=1, color="#336699")
    avant, sl_avant = s.appeler("doc.inspect"), s.appeler("session.list")
    octets2, _ = PM.vignette_motif(s, motifs["Dots"])
    apres, sl_apres = s.appeler("doc.inspect"), s.appeler("session.list")
    check("4d avec un document : vignette 64×64", Image.open(io.BytesIO(octets2)).size == (64, 64))
    check("4e l'original est intact (révision, historique, documents, actif)", avant["revision"] == apres["revision"]
          and avant["history"] == apres["history"] and len(sl_avant["documents"]) == len(sl_apres["documents"])
          and sl_avant["active"] == sl_apres["active"], (avant["revision"], apres["revision"], sl_apres))
    rev = apres["revision"]
    n_docs = []
    # Les étapes d'une séquence passent par la fonction `appel` qu'elle reçoit (pas SessionMoteur.appeler) : on espionne
    # celle-là, en enveloppant la séquence de CETTE session.
    vraie_seq = s.sequence
    try:
        s.sequence = lambda fn, *a, **k: vraie_seq(lambda appel, gen: fn(lambda m, *p, **q: (n_docs.append(m), appel(m, *p, **q))[1], gen), *a, **k)
        PM.vignette_motif(s, motifs["Dots"])
        temoin = list(n_docs)
        PM.vignette_motif(s, motifs["Grid"])         # témoin : un motif pas encore rendu passe bien par doc.new
    finally:
        s.sequence = vraie_seq
    check("4f cache : une deuxième vignette du même motif n'appelle pas doc.new (témoin : un motif neuf, si)",
          "doc.new" not in temoin and "doc.new" in n_docs[len(temoin):], n_docs)
    for lib, ident in (("id mal formé", "../x"), ("chemin", "c:/a.pat")):
        try:
            PM.vignette_motif(s, ident)
            r = False
        except ValueError:
            r = True
        check(f"4g {lib} -> ValueError sans appel au moteur", r)
    try:
        PM.vignette_motif(s, "00000000-0000-0000-0000-000000000000")
        r = False
    except PM.MoteurErreur:
        r = True
    sl = s.appeler("session.list")
    check("4h motif inconnu -> refus du moteur, document temporaire refermé, original actif", r and len(sl["documents"]) == 1 and sl["active"] == 0, sl)
    check("4i aucun mtf-*.png laissé", not any(p.name.startswith("mtf-") for p in (PM.dossier_travail() / "rendus").iterdir()))

    # [5] couches alpha
    vide, _ = PM.couches_alpha(s, 64)
    check("5a sans couche alpha : liste vide", vide == [], vide)
    ex("select.rect", x=0, y=0, width=60, height=80)
    ex("select.saveSelection")
    ex("select.deselect")
    ex("select.all")
    ex("select.saveSelection")
    ex("select.deselect")
    avant, sl_avant = s.appeler("doc.inspect"), s.appeler("session.list")
    cs, _ = PM.couches_alpha(s, 120)
    apres, sl_apres = s.appeler("doc.inspect"), s.appeler("session.list")
    check("5b deux couches alpha -> deux images, index 0 et 1", [c["index"] for c in cs] == [0, 1], [c.get("index") for c in cs])

    def gris(c):
        import base64
        return Image.open(io.BytesIO(base64.b64decode(c["png"].split(",", 1)[1])))
    g0, g1 = gris(cs[0]), gris(cs[1])
    check("5c niveaux de gris à la taille du document", g0.mode == "L" and g0.size == (120, 80), (g0.mode, g0.size))
    check("5d couche 0 (moitié gauche) : blanc à gauche, noir à droite", g0.getpixel((10, 40)) > 240 and g0.getpixel((110, 40)) < 15,
          (g0.getpixel((10, 40)), g0.getpixel((110, 40))))
    check("5e couche 1 (tout) : blanc partout", g1.getpixel((10, 40)) > 240 and g1.getpixel((110, 40)) > 240)
    check("5f l'original est intact (révision, historique, sélection, documents, actif)", avant["revision"] == apres["revision"]
          and avant["history"] == apres["history"] and avant["hasSelection"] == apres["hasSelection"]
          and len(sl_avant["documents"]) == len(sl_apres["documents"]) and sl_avant["active"] == sl_apres["active"], (avant["revision"], apres["revision"]))
    un, _ = PM.couches_alpha(s, 64, 1)
    check("5g index=1 : une seule couche", [c["index"] for c in un] == [1], un)
    try:
        PM.couches_alpha(s, 64, 7)
        r = False
    except ValueError:
        r = True
    check("5h index inconnu -> ValueError", r)
    check("5i aucun cha-*.png laissé", not any(p.name.startswith("cha-") for p in (PM.dossier_travail() / "rendus").iterdir()))

    # [6] liste blanche du pont
    print("\n[6] liste blanche")
    reg = PM.registre(s)
    admis = [("tools.setColors", {"foreground": "#ff0000"}), ("gradient.presets.select", {"preset": "Blue 01"}),
             ("gradient.presets.apply", {"preset": "Blue 01"}), ("gradient.presets.new", {"name": "Essai"}),
             ("gradient.presets.edit", {"action": "newGroup", "name": "Groupe"}), ("pattern.presets.select", {"pattern": motifs["Dots"]}),
             ("pattern.presets.apply", {"pattern": motifs["Dots"]}), ("pattern.presets.new", {}),
             ("pattern.presets.edit", {"action": "rename", "preset": "Dots", "name": "Points"}),
             ("document.pixel", {"x": 3, "y": 4}), ("channel.target", {"channel": "red"}), ("channel.target", {"channel": 0}),
             ("channel.setVisible", {"channel": "green", "visible": False}), ("channel.new", {}), ("channel.delete", {"channel": 0}),
             ("channel.rename", {"channel": 0, "name": "Masque"}), ("select.loadSelection", {"channel": 0, "operation": "add"}),
             ("select.saveSelection", {}), ("layerComp.new", {"name": "A", "visibility": True, "position": False, "appearance": True, "comment": "c"}),
             ("layerComp.apply", {"comp": 1}), ("layerComp.setOptions", {"comp": 1, "position": False}), ("layerComp.previous", {}),
             ("layerComp.next", {}), ("layerComp.update", {"comp": 1}), ("layerComp.delete", {"comp": 1}),
             ("layerComp.rename", {"comp": 1, "name": "B"}), ("layerComp.restoreLastDocumentState", {}),
             ("layerComp.list", {}), ("layerComp.updateWarnings", {"clear": True}), ("gradient.presets.list", {}),
             ("pattern.presets.list", {}), ("gradient.presets.edit", {"action": "rename", "preset": "Blue 01", "group": "Blues", "name": "B"}),
             ("gradient.presets.edit", {"action": "deleteGroup", "group": "Blues"}), ("tools.setColors", {"background": "#00ff00"})]
    for cid, p in admis:
        try:
            PM.commande_autorisee(cid, p, reg)
            r = True
        except ValueError as e:
            r = e
        check(f"6a admis : {cid} {json.dumps(p)[:60]}", r is True, r)
    refuses = [("pattern.import", {"path": "c:/x.pat"}), ("pattern.export", {"path": "x.pat"}),
               ("gradient.presets.importGrd", {"path": "x.grd"}), ("pattern.presets.new", {"name": "../../x.pat"})]
    for cid, p in refuses:
        try:
            PM.commande_autorisee(cid, p, reg)
            r = False
        except ValueError:
            r = True
        check(f"6b refusé : {cid} {json.dumps(p)[:60]}", r)
    return motifs


async def routes_moteur(motifs):
    print("\n[7] routes /motifs et /couches")
    import httpx
    from app.main import app
    t = httpx.ASGITransport(app=app, client=("127.0.0.1", 5000))
    async with httpx.AsyncClient(transport=t, base_url="http://t") as c:
        r = await c.get(f"/api/photolab/motifs/{motifs['Grid']}.png")
        check("7a GET /motifs/{id}.png : 200, image/png, en-tête de génération", r.status_code == 200 and r.headers.get("content-type") == "image/png"
              and r.content[:8] == b"\x89PNG\r\n\x1a\n" and bool(r.headers.get("x-photolab-generation")), (r.status_code, r.text[:200]))
        r = await c.get("/api/photolab/motifs/pas-un-id.png")
        check("7b id mal formé : 400", r.status_code == 400, (r.status_code, r.text[:200]))
        r = await c.get("/api/photolab/couches?maxSide=48")
        j = r.json() if r.status_code == 200 else {}
        check("7c GET /couches : 200, deux couches en data-URL", r.status_code == 200 and [x["index"] for x in j.get("couches", [])] == [0, 1]
              and j["couches"][0]["png"].startswith("data:image/png;base64,"), (r.status_code, r.text[:200]))
        r = await c.get("/api/photolab/couches?maxSide=5000")
        check("7d maxSide hors bornes : 400", r.status_code == 400, (r.status_code, r.text[:200]))
    s = PM.session()
    while (s.appeler("session.list").get("documents") or []):
        s.appeler("doc.close", {"index": 0})
    async with httpx.AsyncClient(transport=t, base_url="http://t") as c:
        r = await c.get("/api/photolab/couches")
        check("7e /couches sans document : refus du moteur (422)", r.status_code == 422, (r.status_code, r.text[:200]))


try:
    service()
    asyncio.run(routes_nuancier())
    copie_js()
    m = moteur()
    if m:
        asyncio.run(routes_moteur(m))
finally:
    PM.fermer()
    shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
