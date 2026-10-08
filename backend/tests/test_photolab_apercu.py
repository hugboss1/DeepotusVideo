# -*- coding: utf-8 -*-
"""t138 (Photolab P3, Task A3) — aperçu calculé par le moteur sur une COPIE du document, et histogramme.
  [1] faux moteur (tests/faux_photocraft.py) : refus AVANT tout appel, ids traduits par position, calque actif reposé
      sur la copie, trois apv-* gardés, copie refermée même quand une étape échoue au moteur.
  [2] VRAI moteur photocraft-cli 0.3.0 : aperçu identique À L'OCTET à l'application réelle (sélection elliptique
      progressive, calque actif non supérieur), original intact (revision, activeLayer, selectionBounds, canRedo,
      history) ; filtre, niveaux destructifs, ombre portée visée par un id traduit ; 422 réel et copie refermée.
  [3] VRAI moteur : histogramme (blanc, calque Inverser masqué par `sans`, puis visible).
  Sections VRAI moteur rouges si le binaire manque — jamais de saut silencieux.
Run : & $PY -X utf8 tests/test_photolab_apercu.py   (depuis backend/)"""
import asyncio, os, pathlib, shutil, sys, tempfile, time
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt138a3_"))
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
FAUX = [sys.executable, str(BACKEND / "tests" / "faux_photocraft.py"), "serve",
        "--automation-read-root", str(D), "--automation-write-root", str(D)]
PM.FABRIQUE = lambda: PM.SessionMoteur(FAUX, delai_s=5.0)
GEN = "X-Photolab-Generation"


def apv_sur_disque():
    return sorted(f.name for f in (D / "rendus").iterdir() if f.name.startswith("apv-"))


async def compte(c):
    return (await c.post("/api/photolab/executer", json={"command": "dz.compte"})).json()


async def apercu(c, etapes, **extra):
    return await c.post("/api/photolab/apercu", json={"etapes": etapes, **extra})


async def fake_scenario(c):
    print("\n[1] faux moteur")
    r = await c.post("/api/photolab/nouveau", json={"width": 64, "height": 32, "background": "white"})
    assert r.status_code == 200, r.text
    await compte(c)                                            # registre en cache : les compteurs suivants sont nets
    base = await compte(c)

    # ── refus AVANT tout appel au moteur ──
    refus = (
        ("1a layer.delete (famille hors aperçu)", [{"command": "layer.delete"}], "aperçu impossible"),
        ("1b select.all (famille hors aperçu)", [{"command": "select.all"}], "aperçu impossible"),
        ("1c gaussianBlur radius \"2\" (type refusé par la liste blanche)",
         [{"command": "filter.blur.gaussianBlur", "params": {"radius": "2"}}], ""),
        ("1d une étape admise puis une refusée : rien n'est lancé",
         [{"command": "filter.blur.gaussianBlur", "params": {"radius": 2}}, {"command": "image.mode.rgb"}], "aperçu impossible"),
        ("1e image.adjustments.colorLookup {lut: ../x.cube}",
         [{"command": "image.adjustments.colorLookup", "params": {"lut": "../x.cube"}}], ""),
        ("1f commande illisible", [{"command": "../x"}], ""),
        ("1g aucune étape", [], ""),
        ("1h 13 étapes (12 au plus)", [{"command": "filter.blur.gaussianBlur", "params": {"radius": 1}}] * 13, ""),
        ("1i params non dict", [{"command": "filter.blur.gaussianBlur", "params": [1]}], ""),
        # liste STRICTE : décrites par le registre, mais hors aperçu (presse-papiers de styles, création, plein-écran D9)
        ("1m layer.layerStyle.copyLayerStyle", [{"command": "layer.layerStyle.copyLayerStyle"}], "aperçu impossible"),
        ("1n layer.layerStyle.pasteLayerStyle", [{"command": "layer.layerStyle.pasteLayerStyle"}], "aperçu impossible"),
        ("1o layer.layerStyle.createLayer", [{"command": "layer.layerStyle.createLayer"}], "aperçu impossible"),
        ("1p filter.convertForSmartFilters", [{"command": "filter.convertForSmartFilters"}], "aperçu impossible"),
        ("1q filter.vanishingPoint", [{"command": "filter.vanishingPoint"}], "aperçu impossible"),
        ("1r image.adjustments.colorLookup.list", [{"command": "image.adjustments.colorLookup.list"}], "aperçu impossible"),
        ("1s étape sans command", [{"params": {"radius": 1}}], ""),
    )
    for nom, etapes, motif in refus:
        r = await apercu(c, etapes)
        check(f"{nom} -> 400", r.status_code == 400 and motif in r.text, (r.status_code, r.text))
    for ms in (32, 4096, "x", True):
        r = await apercu(c, [{"command": "filter.blur.gaussianBlur", "params": {"radius": 1}}], maxSide=ms)
        check(f"1j maxSide {ms!r} -> 400", r.status_code == 400, (r.status_code, r.text))
    apres = await compte(c)
    check("1k aucun refus n'a touché le moteur (journal inchangé, aucune copie)",
          apres["journal"] == base["journal"] and apres["duplicate"] == base["duplicate"],
          (base["journal"][-5:], apres["journal"][len(base["journal"]):]))

    # ── un id de calque inconnu de l'original : 400, aucune copie ──
    base = await compte(c)
    r = await apercu(c, [{"command": "layer.layerStyle.dropShadow", "params": {"layer": 777, "distance": 4}}])
    apres = await compte(c)
    check("1l id de calque inconnu de l'original -> 400, aucune copie ouverte",
          r.status_code == 400 and "777" in r.text and apres["duplicate"] == base["duplicate"], (r.status_code, r.text))

    # ── un aperçu admis : copie, calque actif reposé PAR POSITION, ids traduits, copie refermée ──
    # appel direct (hors pont) : la liste blanche refuserait la clé `layer` que dz.actif ne décrit pas
    PM.session().appeler("engine.execute", {"command": "dz.actif", "params": {"layer": 4}})        # « Dans le groupe »
    r = (await c.get("/api/photolab/inspecter")).json()
    check("2_ mise en place : calque actif de l'original = 4 (« Dans le groupe », 4e en préordre)", r.get("activeLayer") == 4, r.get("activeLayer"))
    base = await compte(c)
    r = await apercu(c, [{"command": "filter.blur.gaussianBlur", "params": {"radius": 3}},
                         {"command": "layer.layerStyle.dropShadow", "params": {"layer": 2, "distance": 4}},
                         {"command": "layer.setAdjustment", "params": {"layer": 6, "gamma": 1.4}},
                         {"command": "layer.setProps", "params": {"layer": 1, "blend": "Linear Dodge (Add)"}}],
                     maxSide=256)
    j = r.json()
    apres = await compte(c)
    neuf = apres["journal"][len(base["journal"]):]
    check("2a 200 : url /api/photolab/rendus/apv-<gen>-<n>.png, ms, un résultat par étape",
          r.status_code == 200 and j.get("url", "").startswith("/api/photolab/rendus/apv-") and isinstance(j.get("ms"), int)
          and len(j.get("resultats") or []) == 4 and r.headers.get(GEN) == "1", (r.status_code, j))
    res = j.get("resultats") or [{}] * 4
    check("2b le calque actif de la copie est celui à la MÊME position (« Dans le groupe »)",
          apres.get("selections", [])[-1:] == ["Dans le groupe"], apres.get("selections"))
    check("2c id `layer` traduit : l'ombre vise « Calque 1 » de la copie (pas l'id 2 de l'original)",
          res[1].get("nomCalque") == "Calque 1" and res[1].get("params", {}).get("layer") != 2, res[1])
    check("2d layer.setAdjustment : kind lu sur l'original (Levels dans le groupe), id traduit",
          res[2].get("nomCalque") == "Levels 1" and res[2].get("params", {}).get("layer") != 6, res[2])
    check("2e layer.setProps {layer: 1} traduit vers « Fond » de la copie", res[3].get("nomCalque") == "Fond", res[3])
    check("2f séquence : duplicate, select, étapes, rendu, doc.close, doc.select (rien d'autre entre)",
          [x for x in neuf if x.startswith("engine.execute:") or x in ("doc.render", "doc.close", "doc.select")]
          == ["engine.execute:image.duplicate", "engine.execute:layer.select", "engine.execute:filter.blur.gaussianBlur",
              "engine.execute:layer.layerStyle.dropShadow", "engine.execute:layer.setAdjustment",
              "engine.execute:layer.setProps", "doc.render", "doc.close", "doc.select"], neuf)
    s = (await c.get("/api/photolab/session")).json()
    check("2g après l'aperçu : un seul document, l'original actif", len(s["documents"]) == 1 and s["active"] == 0, s)
    f = await c.get(j.get("url", "/x"))
    check("2h le rendu est servi par /rendus/ (no-store)", f.status_code == 200 and f.headers.get("cache-control") == "no-store",
          (f.status_code, dict(f.headers)))

    # ── setAdjustment sur un calque qui n'est pas un réglage : 400 sans copie ──
    base = await compte(c)
    r = await apercu(c, [{"command": "layer.setAdjustment", "params": {"layer": 2, "gamma": 1.2}}])
    apres = await compte(c)
    check("2i layer.setAdjustment sur un calque pixel -> 400, aucune copie",
          r.status_code == 400 and apres["duplicate"] == base["duplicate"], (r.status_code, r.text))
    r = await apercu(c, [{"command": "layer.setAdjustment", "params": {"layer": 6, "points": [[0, 0], [255, 255]]}}])
    check("2j layer.setAdjustment Levels avec une clé de Courbes -> 400", r.status_code == 400, (r.status_code, r.text))
    # hueSaturation : bornes de colorisation lues dans l'état du calque de l'ORIGINAL (comme /executer)
    for lid, colo in ((30, True), (31, False)):
        PM.session().appeler("engine.execute", {"command": "dz.reglage", "params": {"layer": lid, "adjustment": {
            "HueSaturation": {"colorize": colo, "hue": 0.0, "saturation": 0.0, "lightness": 0.0, "ranges": []}}}})
    r = await apercu(c, [{"command": "layer.setAdjustment", "params": {"layer": 30, "hue": 200}}])
    check("2j2 aperçu setAdjustment hue 200 sur un calque colorisé : admis", r.status_code == 200, (r.status_code, r.text[:200]))
    r = await apercu(c, [{"command": "layer.setAdjustment", "params": {"layer": 31, "hue": 200}}])
    check("2j3 …refusé (400) sur un calque non colorisé", r.status_code == 400, (r.status_code, r.text[:200]))

    # ── trois apv-* gardés au plus ──
    codes = []
    for _ in range(4):
        r = await apercu(c, [{"command": "filter.blur.gaussianBlur", "params": {"radius": 1}}])
        codes.append(r.status_code)
    noms = apv_sur_disque()
    check("3a quatre aperçus de suite : trois fichiers apv-* restent, le dernier compris",
          codes == [200] * 4 and len(noms) == 3 and r.json().get("url", "/").rsplit("/", 1)[1] in noms, (codes, noms))

    # ── une étape refusée PAR LE MOTEUR : 422 et la copie est refermée quand même ──
    await c.post("/api/photolab/executer", json={"command": "dz.echecEtape"})
    base = await compte(c)
    r = await apercu(c, [{"command": "filter.blur.gaussianBlur", "params": {"radius": 2}}])
    apres = await compte(c)
    s = (await c.get("/api/photolab/session")).json()
    neuf = apres["journal"][len(base["journal"]):]
    check("4a étape en échec au moteur -> 422 avec son message", r.status_code == 422 and "filtre refusé" in r.text,
          (r.status_code, r.text))
    check("4b la copie est refermée et l'original resélectionné (un seul document, actif 0)",
          len(s["documents"]) == 1 and s["active"] == 0 and neuf[-2:] == ["doc.close", "doc.select"], (s, neuf))
    n_apv = len(apv_sur_disque())
    check("4c aucun rendu après l'échec (toujours trois apv-*)", n_apv == 3, apv_sur_disque())

    # ── histogramme : contrats sur le faux (les pixels sont dans [3]) ──
    for q in ("maxSide=32", "maxSide=2048", "maxSide=256&sans=777"):
        r = await c.get(f"/api/photolab/histogramme?{q}")
        check(f"5a /histogramme?{q} -> 400", r.status_code == 400, (r.status_code, r.text))
    s = (await c.get("/api/photolab/session")).json()
    check("5b après un sans inconnu : toujours un seul document", len(s["documents"]) == 1, s)
    # la FORME est validée avant de lire le registre : une demande mal formée ne démarre pas le moteur
    PM.fermer()
    for etapes in ([], "x", [{"command": 3}], [{"command": "layer.delete"}]):
        r = await apercu(c, etapes)
        check(f"5c moteur arrêté, étapes {etapes!r} -> 400 sans démarrer le moteur",
              r.status_code == 400 and (await c.get("/api/photolab/etat")).json().get("vivant") is False, (r.status_code, r.text))
    PM.fermer()


def octets(url_rel):
    return (D / "rendus" / url_rel.rsplit("/", 1)[1]).read_bytes()


async def reel_scenario(c):
    print("\n[2] VRAI moteur photocraft-cli : aperçu == application")
    PM.fermer()
    PM.FABRIQUE = None
    try:
        cli = PM.chemin_cli()
        check("6a le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", cli.is_file(), cli)
    except PM.MoteurAbsent as e:
        check("6a le binaire photocraft-cli 0.3.0 est présent (sinon cette section est rouge)", False, e)
        return False

    async def ex(cmd, **p):
        r = await c.post("/api/photolab/executer", json={"command": cmd, "params": p})
        assert r.status_code == 200, (cmd, r.status_code, r.text)
        return r.json()

    async def etat():
        i = (await c.get("/api/photolab/inspecter")).json()
        return {k: i.get(k) for k in ("revision", "activeLayer", "selectionBounds", "hasSelection", "canRedo", "history")}

    async def rendu():
        r = await c.post("/api/photolab/rendu", json={"maxSide": 512})
        assert r.status_code == 200, r.text
        return octets(r.json()["url"])

    r = await c.post("/api/photolab/nouveau", json={"width": 400, "height": 300, "background": "white"})
    assert r.status_code == 200, r.text
    await ex("filter.render.clouds", seed=7)
    await ex("layer.new.layer", name="haut")
    await ex("select.rect", x=60, y=40, width=200, height=150, mode="replace")
    await ex("edit.fill", color="#3366cc")
    await ex("select.deselect")
    await ex("layer.new.layer", name="vide")
    insp = (await c.get("/api/photolab/inspecter")).json()
    ids = {L["name"]: L["id"] for L in insp["layers"]}
    await ex("layer.select", layer=ids["haut"], mode="replace")
    await ex("select.rect", x=30, y=20, width=300, height=220, mode="replace", ellipse=True, feather=8)
    e0 = await etat()
    check("6b mise en place : calque actif « haut » (non supérieur), sélection elliptique progressive",
          e0["activeLayer"] == ids["haut"] and insp["layers"][0]["name"] == "vide" and e0["hasSelection"], (e0, ids))
    nu = await rendu()

    cas = (("filtre gaussianBlur r=12", [{"command": "filter.blur.gaussianBlur", "params": {"radius": 12}}]),
           ("niveaux destructifs inBlack 40", [{"command": "image.adjustments.levels", "params": {"inBlack": 40}}]),
           ("ombre portée {layer: id de « haut »}",
            [{"command": "layer.layerStyle.dropShadow", "params": {"layer": ids["haut"], "distance": 12, "color": "#0000ff"}}]))
    for k, (nom, etapes) in enumerate(cas):
        avant = await etat()
        r = await apercu(c, etapes, maxSide=512)
        j = r.json()
        check(f"7{k}a aperçu {nom} : 200", r.status_code == 200 and j.get("url", "").startswith("/api/photolab/rendus/apv-"),
              (r.status_code, r.text[:300]))
        if r.status_code != 200:
            continue
        pv = octets(j["url"])
        apres = await etat()
        check(f"7{k}b {nom} : original INTACT (revision, activeLayer, selectionBounds, canRedo, history)", apres == avant,
              (avant, apres))
        if k:                                              # après l'annulation du cas précédent, la pile de rétablissement est pleine
            check(f"7{k}b2 {nom} : canRedo VRAI conservé (l'aperçu ne vide pas la pile de rétablissement)",
                  avant["canRedo"] is True and apres["canRedo"] is True, (avant["canRedo"], apres["canRedo"]))
        s = (await c.get("/api/photolab/session")).json()
        check(f"7{k}c {nom} : un seul document dans la session", len(s["documents"]) == 1, s)
        for st in etapes:
            await ex(st["command"], **st["params"])
        reel = await rendu()
        check(f"7{k}d {nom} : aperçu IDENTIQUE À L'OCTET à l'application réelle", pv == reel, (len(pv), len(reel)))
        check(f"7{k}e {nom} : et différent du document sans l'étape (l'effet est visible)", pv != nu)
        if k == 0:
            f = j["resultats"][0].get("filter") if j.get("resultats") else None
            check("7f result.filter rend les valeurs appliquées (radius 12)", isinstance(f, dict) and f.get("radius") == 12, j.get("resultats"))
        h = await c.post("/api/photolab/historique", json={"annuler": 1})
        assert h.status_code == 200, h.text
        check(f"7{k}g {nom} : annulé, l'original revient à son rendu d'avant", await rendu() == nu)

    # calque actif sur la copie : un filtre SANS `layer` doit viser « haut » sur la copie aussi (sinon il flouterait
    # « vide », transparent, et l'aperçu serait identique au document nu) — couvert par 70d/70e. Puis la latence.
    print("\n  mesure : aperçu flou r=8 sur 1920×1080 à deux calques")
    r = await c.post("/api/photolab/nouveau", json={"width": 1920, "height": 1080, "background": "white"})
    await ex("filter.render.clouds", seed=3)
    await ex("layer.new.layer", name="dessus")
    await ex("select.rect", x=200, y=200, width=800, height=500, mode="replace")
    await ex("edit.fill", color="#cc3366")
    await ex("select.deselect")
    mesures = []
    for _ in range(3):
        t0 = time.perf_counter()
        r = await apercu(c, [{"command": "filter.blur.gaussianBlur", "params": {"radius": 8}}], maxSide=1024)
        mesures.append((round((time.perf_counter() - t0) * 1000), r.json().get("ms")))
    print(f"  latence (mur ms, ms rendu par la route) : {mesures}")
    check("8a aperçu 1920×1080 : 200 et sous 10 s", r.status_code == 200 and max(m[0] for m in mesures) < 10000, (r.status_code, mesures))
    return True


async def histo_scenario(c):
    print("\n[3] VRAI moteur : histogramme")
    s0 = (await c.get("/api/photolab/session")).json()
    r = await c.post("/api/photolab/nouveau", json={"width": 64, "height": 64, "background": "white"})
    assert r.status_code == 200, r.text
    r = await c.get("/api/photolab/histogramme?maxSide=256")
    j = r.json()
    check("9a document blanc 64×64 : l[255] == 4096, somme 4096, r/g/b idem",
          r.status_code == 200 and len(j.get("l", [])) == 256 and j["l"][255] == 4096 and sum(j["l"]) == 4096
          and all(j[k][255] == 4096 and sum(j[k]) == 4096 for k in "rgb"), (r.status_code, r.text[:200]))
    restes = [f.name for f in (D / "rendus").iterdir() if f.name.startswith("hst-")]
    check("9b le rendu temporaire de l'histogramme est supprimé après lecture", restes == [], restes)
    inv = await c.post("/api/photolab/executer", json={"command": "layer.newAdjustmentLayer.invert", "params": {}})
    lid = (inv.json() or {}).get("layer")
    check("9c calque de réglage Inverser créé", inv.status_code == 200 and isinstance(lid, int), inv.text)
    r = await c.get(f"/api/photolab/histogramme?maxSide=256&sans={lid}")
    j = r.json()
    check("9d avec sans=<id du réglage> : toujours blanc (l[255] == 4096)",
          r.status_code == 200 and j.get("l", [0] * 256)[255] == 4096, (r.status_code, r.text[:200]))
    r = await c.get("/api/photolab/histogramme?maxSide=256")
    j = r.json()
    check("9e sans `sans` : tout noir (l[0] == 4096)", r.status_code == 200 and j.get("l", [0])[0] == 4096,
          (r.status_code, r.text[:200]))
    vis = [L.get("visible") for L in (await c.get("/api/photolab/inspecter")).json()["layers"]]
    check("9f l'original garde son réglage VISIBLE (masqué sur la copie seulement)", all(vis), vis)
    # 422 réel : un filtre sur le calque de réglage actif est refusé par le moteur ; la copie est refermée
    s1 = (await c.get("/api/photolab/session")).json()
    r = await apercu(c, [{"command": "filter.blur.gaussianBlur", "params": {"radius": 2}}])
    s2 = (await c.get("/api/photolab/session")).json()
    check("9g filtre sur un calque de réglage : 422 du moteur", r.status_code == 422 and "photocraft" in r.text, (r.status_code, r.text))
    check("9h et la copie est refermée : mêmes documents, même actif",
          len(s2["documents"]) == len(s1["documents"]) == len(s0.get("documents", [])) + 1 and s2["active"] == s1["active"], (s1, s2))

    # trois documents, l'original à l'index 0 (la copie prend l'index 3) : il doit redevenir actif, pas le dernier
    print("\n[4] VRAI moteur : trois documents, original à l'index 0")
    PM.session().appeler("doc.select", {"index": 0})       # pas de route de sélection de document : appel direct
    s3 = (await c.get("/api/photolab/session")).json()
    check("10a mise en place : trois documents, l'index 0 actif", len(s3["documents"]) == 3 and s3["active"] == 0, s3)
    avant = (await c.get("/api/photolab/inspecter")).json()
    r = await apercu(c, [{"command": "filter.blur.gaussianBlur", "params": {"radius": 3}}], maxSide=256)
    s4 = (await c.get("/api/photolab/session")).json()
    check("10b aperçu : 200, l'original (index 0) reste actif, 3 documents restent",
          r.status_code == 200 and s4["active"] == 0 and len(s4["documents"]) == 3, (r.status_code, r.text[:200], s4))
    r = await c.get("/api/photolab/histogramme?maxSide=128")
    s5 = (await c.get("/api/photolab/session")).json()
    check("10c histogramme : 200, l'original (index 0) reste actif, 3 documents restent",
          r.status_code == 200 and s5["active"] == 0 and len(s5["documents"]) == 3, (r.status_code, r.text[:200], s5))
    apres = (await c.get("/api/photolab/inspecter")).json()
    check("10d l'original 400×300 inchangé (largeur, revision, history)",
          (apres.get("width"), apres["revision"], apres["history"]) == (avant.get("width"), avant["revision"], avant["history"])
          and apres.get("width") == 400, (avant.get("revision"), apres.get("revision")))
    PM.fermer()


async def scenario():
    import httpx
    from app.main import app
    _json0 = httpx.Response.json

    def _json_tolerant(self, *a, **k):
        # route absente = le catch-all de l'application sert son index.html : un FAIL lisible, pas une trace
        try:
            return _json0(self, *a, **k)
        except ValueError:
            return {}
    httpx.Response.json = _json_tolerant
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t",
                                 timeout=120) as c:
        await fake_scenario(c)
        if await reel_scenario(c):
            await histo_scenario(c)

try:
    asyncio.run(scenario())
finally:
    PM.fermer()
shutil.rmtree(_tmp, ignore_errors=True)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
