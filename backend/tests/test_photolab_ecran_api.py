# -*- coding: utf-8 -*-
"""t137 (Photolab P2, phase A) — les routes que l'ÉCRAN ajoute au pont : /session, /historique, /vignettes,
/bibliotheque, et le montage statique /photolab/.
  [1] faux moteur (tests/faux_photocraft.py) : contrats, compteurs, séquence atomique, fermeture de la copie.
  [2] VRAI moteur photocraft-cli 0.3.0 : les vignettes sont de vrais rendus, le document actif ressort INCHANGÉ.
      Section rouge si le binaire manque — jamais de saut silencieux.
Run : & $PY tests/test_photolab_ecran_api.py   (depuis backend/)"""
import asyncio, io, os, pathlib, re, shutil, sys, tempfile, threading
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt137a_"))
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
from PIL import Image                                          # noqa: E402
GEN = "X-Photolab-Generation"
_RACINE0, _CLI0 = PM.RACINE_APP, os.environ.get("PHOTOCRAFT_CLI")


def vignettes_sur_disque():
    return sorted(f.name for f in (D / "rendus").iterdir() if f.name.startswith("vig-"))


async def compte(c):
    r = await c.post("/api/photolab/executer", json={"command": "dz.compte"})
    return r.json()


async def fake_scenario(c):
    print("\n[1] faux moteur")
    # ── A1.1 /session ─────────────────────────────────────────────────────────────────────────────────────────────
    await c.post("/api/photolab/nouveau", json={"width": 64, "height": 32, "background": "white"})
    r = await c.get("/api/photolab/session")
    j = r.json()
    check("1 GET /session : active, documents, foreground, background + en-tête de génération",
          r.status_code == 200 and {"active", "documents", "foreground", "background"} <= set(j)
          and j["active"] == 0 and len(j["documents"]) == 1 and r.headers.get(GEN) == "1", (r.status_code, j, dict(r.headers)))

    # ── A1.2 /historique ──────────────────────────────────────────────────────────────────────────────────────────
    for _ in range(3):
        await c.post("/api/photolab/executer", json={"command": "dz.modifier"})
    avant = await compte(c)
    r = await c.post("/api/photolab/historique", json={"annuler": 3})
    apres = await compte(c)
    j = r.json()
    check("2a 3 annulations = UNE requête batch de 3 étapes (le faux compte)",
          r.status_code == 200 and apres["batches"] == avant["batches"] + [3], (r.status_code, avant["batches"], apres["batches"]))
    check("2b rend doc.inspect après (history revenu à « Open », canRedo)",
          j.get("inspect", {}).get("history") == ["Open"] and j.get("inspect", {}).get("canRedo") is True
          and j.get("completed") == 3 and j.get("failed") == 0, j)
    check("2c l'en-tête de génération accompagne l'historique", r.headers.get(GEN) == "1", dict(r.headers))
    r = await c.post("/api/photolab/historique", json={"retablir": 2})
    apres2 = await compte(c)
    check("2d rétablir 2 = un batch de 2 étapes edit.redo", r.status_code == 200
          and apres2["batches"][-1] == 2 and r.json().get("inspect", {}).get("history") == ["Open", "Modifier", "Modifier"], (r.text, apres2["batches"]))
    for corps, nom in (({"annuler": 0}, "n=0"), ({"annuler": 101}, "n=101"), ({"annuler": 1, "retablir": 1}, "les deux"),
                       ({}, "ni l'un ni l'autre"), ({"annuler": "2"}, "texte"), ({"annuler": True}, "booléen"),
                       ({"annuler": 1.5}, "flottant")):
        r = await c.post("/api/photolab/historique", json=corps)
        check(f"2e /historique {nom} -> 400", r.status_code == 400, (r.status_code, r.text))
    r = await c.post("/api/photolab/historique", json={"annuler": 50})
    j = r.json()
    check("2g 50 annulations pour 2 possibles : 200, completed 2, failed >= 1 (dit à l'écran, pas une erreur)",
          r.status_code == 200 and j.get("completed") == 2 and j.get("failed", 0) >= 1
          and j.get("inspect", {}).get("history") == ["Open"], (r.status_code, j))
    r = await c.post("/api/photolab/historique", json={"annuler": 100})
    check("2f n=100 accepté (borne haute incluse)", r.status_code == 200, (r.status_code, r.text))

    # ── A1.3 /vignettes (faux) ────────────────────────────────────────────────────────────────────────────────────
    for ms in (15, 257, "x"):
        r = await c.get(f"/api/photolab/vignettes?maxSide={ms}")
        check(f"3a /vignettes maxSide={ms} refusé (16..256)", r.status_code in (400, 422), (r.status_code, r.text))
    await c.post("/api/photolab/executer", json={"command": "dz.modifier"})          # une révision connue
    insp = (await c.get("/api/photolab/inspecter")).json()
    rev = insp["revision"]
    n0 = (await compte(c))["duplicate"]
    r = await c.get("/api/photolab/vignettes?maxSide=48")
    v = r.json().get("vignettes", {})
    check("3b une vignette par calque non-groupe (ids 1, 2, 4 — pas le groupe), URL vig-<gen>-<id>-<rev>.png",
          r.status_code == 200 and sorted(v) == ["1", "2", "4"]
          and all(re.fullmatch(rf"/api/photolab/rendus/vig-1-{k}-{rev}-48\.png", u) for k, u in v.items()), (r.status_code, v))
    f = await c.get(v["1"]) if v else None
    check("3c la vignette est servie par /rendus/ (image/png, no-store)", f is not None and f.status_code == 200
          and f.headers["content-type"] == "image/png" and f.headers.get("cache-control") == "no-store", f and (f.status_code, dict(f.headers)))
    check("3d l'en-tête de génération accompagne les vignettes", r.headers.get(GEN) == "1", dict(r.headers))
    s = (await c.get("/api/photolab/session")).json()
    check("3e le document d'origine est restauré (un seul document, actif 0)", s["active"] == 0 and len(s["documents"]) == 1, s)
    r = await c.get("/api/photolab/vignettes?maxSide=48")
    cpt = await compte(c)
    check("3f deuxième demande à la même révision : AUCUN image.duplicate de plus (cache par génération+révision)",
          cpt["duplicate"] == n0 + 1 and r.json().get("vignettes") == v, (n0, cpt["duplicate"]))
    await c.post("/api/photolab/executer", json={"command": "dz.modifier"})
    r = await c.get("/api/photolab/vignettes?maxSide=48")
    v2 = r.json().get("vignettes", {})
    cpt = await compte(c)
    check("3g révision changée : on recalcule (duplicate +1), nouvelles URL", cpt["duplicate"] == n0 + 2 and v2 != v, (cpt["duplicate"], v2))
    check("3h les vignettes d'une autre révision sont supprimées (3 fichiers restent, ceux de la révision courante)",
          vignettes_sur_disque() == sorted(u.rsplit("/", 1)[1] for u in v2.values()), vignettes_sur_disque())
    # ── la copie est refermée quoi qu'il arrive (try/finally) ──
    await c.post("/api/photolab/executer", json={"command": "dz.modifier"})
    await c.post("/api/photolab/executer", json={"command": "dz.casseRendu"})
    r = await c.get("/api/photolab/vignettes?maxSide=48")
    s = (await c.get("/api/photolab/session")).json()
    check("3i rendu en échec en cours de route : erreur dite (422) ET la copie est refermée, l'original actif",
          r.status_code == 422 and len(s["documents"]) == 1 and s["active"] == 0, (r.status_code, r.text, s))
    # ── le document d'origine n'est pas toujours l'index 0 ──
    PM.session().appeler("doc.new", {"width": 8, "height": 8})
    PM.session().appeler("doc.select", {"index": 0})
    r = await c.get("/api/photolab/vignettes?maxSide=48")
    s = (await c.get("/api/photolab/session")).json()
    check("3j original = document 0 parmi deux : il redevient actif, 2 documents au total",
          r.status_code == 200 and s["active"] == 0 and len(s["documents"]) == 2, (r.status_code, s))
    PM.session().appeler("doc.select", {"index": 1})
    await c.post("/api/photolab/executer", json={"command": "dz.modifier"})
    r = await c.get("/api/photolab/vignettes?maxSide=48")
    s = (await c.get("/api/photolab/session")).json()
    check("3k original = document 1 actif : c'est lui qui est restauré", r.status_code == 200 and s["active"] == 1
          and len(s["documents"]) == 2, (r.status_code, s))
    # ── la séquence est ATOMIQUE : aucun appel étranger entre image.duplicate et doc.close ──
    PM.session().appeler("doc.select", {"index": 0})
    await c.post("/api/photolab/executer", json={"command": "dz.modifier"})
    tir = []

    def importun():
        # se présente pendant que la séquence tient le verrou (les rendus de vignette durent ~80 ms chacun)
        import time
        time.sleep(0.12)
        try:
            PM.session().appeler("engine.execute", {"command": "dz.pid"})
            tir.append("ok")
        except Exception as e:                                 # noqa: BLE001
            tir.append(repr(e))
    th = threading.Thread(target=importun)
    th.start()
    r = await c.get("/api/photolab/vignettes?maxSide=48")
    th.join()
    j = [e for e in (await compte(c))["journal"]]
    i0 = max(k for k, e in enumerate(j) if e == "engine.execute:image.duplicate")
    i1 = next(k for k, e in enumerate(j) if k > i0 and e == "doc.close")
    entre = j[i0 + 1:i1]
    check("3l aucun appel étranger (dz.pid) ENTRE image.duplicate et doc.close — la séquence tient le verrou",
          r.status_code == 200 and tir == ["ok"] and not any(e.startswith("engine.execute:dz.") for e in entre) and "engine.execute:dz.pid" in j[i1:], (tir, entre))
    # ── deux tailles de la même révision coexistent ; la troisième demande (48) vient du cache ──
    await c.post("/api/photolab/executer", json={"command": "dz.modifier"})
    d0 = (await compte(c))["duplicate"]
    ra = await c.get("/api/photolab/vignettes?maxSide=48")
    rb = await c.get("/api/photolab/vignettes?maxSide=128")
    rc = await c.get("/api/photolab/vignettes?maxSide=48")
    va, vb, vc = ra.json().get("vignettes", {}), rb.json().get("vignettes", {}), rc.json().get("vignettes", {})
    d1 = (await compte(c))["duplicate"]
    check("3p maxSide 48 puis 128 à la même révision : URL différentes (maxSide dans le nom), les deux fichiers existent",
          va and vb and set(va.values()).isdisjoint(vb.values()) and all(u.endswith("-48.png") for u in va.values())
          and all(u.endswith("-128.png") for u in vb.values())
          and all((D / "rendus" / u.rsplit("/", 1)[1]).is_file() for u in list(va.values()) + list(vb.values())), (va, vb))
    check("3q la troisième demande (48) sort du cache : 2 duplicate en tout pour 3 demandes, mêmes URL que la première",
          d1 == d0 + 2 and vc == va, (d0, d1, va, vc))
    # ── image.duplicate qui ne dit pas l'index de la copie : échec dit, MAIS la copie (un document de plus) est refermée ──
    await c.post("/api/photolab/executer", json={"command": "dz.modifier"})
    await c.post("/api/photolab/executer", json={"command": "dz.dupliquerSansIndex"})
    r = await c.get("/api/photolab/vignettes?maxSide=48")
    s = (await c.get("/api/photolab/session")).json()
    check("3r image.duplicate sans « document » : 422, la copie surnuméraire est refermée, l'original (actif 0) redevient actif",
          r.status_code == 422 and len(s["documents"]) == 2 and s["active"] == 0, (r.status_code, r.text, s))
    # ── redémarrage du moteur DANS une séquence : jamais d'étapes sur le nouveau moteur vide ──
    s0 = PM.session()
    gen0 = s0.generation

    def seq_morte(appel, gen):
        appel("engine.execute", {"command": "dz.pid"})
        try:
            appel("engine.execute", {"command": "dz.mourir"})
        except PM.MoteurErreur:
            pass
        appel("doc.inspect")                                   # le moteur est mort : doit lever, SANS relancer
    try:
        s0.sequence(seq_morte)
        lev = None
    except PM.MoteurErreur as e:
        lev = str(e)
    check("3m moteur mort pendant une séquence : l'étape suivante lève MoteurErreur (pas de relance en cours de séquence)",
          lev is not None and s0.generation == gen0 and not s0.vivant(), (lev, s0.generation, gen0))
    r = await c.post("/api/photolab/executer", json={"command": "dz.pid"})
    check("3n la demande suivante relance (génération +1)", r.status_code == 200 and r.headers.get(GEN) == str(gen0 + 1), dict(r.headers))
    # sans document : pas de copie, réponse vide
    PM.fermer()
    r = await c.get("/api/photolab/vignettes?maxSide=48")
    check("3o sans document ouvert : {vignettes: {}} (rien à copier)", r.status_code == 200 and r.json() == {"vignettes": {}}, (r.status_code, r.text))


def png_pixel(octets, x, y):
    im = Image.open(io.BytesIO(octets)).convert("RGB")
    return im.getpixel((x, y)), im.size


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
    r = await c.post("/api/photolab/nouveau", json={"width": 64, "height": 32, "background": "white"})
    assert r.status_code == 200, r.text
    await ex("layer.new.layer", name="Rouge")
    await ex("tools.setColors", foreground="#ff0000")
    await ex("edit.fill", contents="foreground")
    await ex("layer.setProps", name="Rouge", visible=False)                 # un calque masqué au départ : doit le rester
    avant = (await c.get("/api/photolab/inspecter")).json()
    sess_avant = (await c.get("/api/photolab/session")).json()
    lay_avant = [(L["id"], L["name"], L["visible"]) for L in avant["layers"]]
    r = await c.get("/api/photolab/vignettes?maxSide=48")
    v = r.json().get("vignettes", {})
    ids = {L["name"]: str(L["id"]) for L in avant["layers"]}
    check("4b une vignette pour « Rouge » et une pour « Background »", r.status_code == 200
          and set(v) == set(ids.values()), (r.status_code, r.text[:300]))
    if set(v) != set(ids.values()):
        return
    rouge = await c.get(v[ids["Rouge"]])
    fond = await c.get(v[ids["Background"]])
    taille = Image.open(io.BytesIO(rouge.content)).size
    pr, tr = png_pixel(rouge.content, taille[0] // 2, taille[1] // 2)
    pf, tf = png_pixel(fond.content, tr[0] // 2, tr[1] // 2)
    check("4c la vignette du calque rouge a un pixel central ROUGE (même masqué dans l'original)", pr[0] > 240 and pr[1] < 15 and pr[2] < 15, pr)
    check("4d la vignette du fond est BLANCHE", min(pf) > 240, pf)
    check("4e la vignette respecte maxSide (48) et le rapport 2:1", max(tr) == 48 and tr[0] == 2 * tr[1], tr)
    apres = (await c.get("/api/photolab/inspecter")).json()
    sess_apres = (await c.get("/api/photolab/session")).json()
    lay_apres = [(L["id"], L["name"], L["visible"]) for L in apres["layers"]]
    check("4f le document actif ressort INCHANGÉ : même révision, mêmes calques, mêmes visibilités",
          apres["revision"] == avant["revision"] and lay_apres == lay_avant and len(apres["layers"]) == len(avant["layers"]),
          (avant["revision"], apres["revision"], lay_avant, lay_apres))
    check("4g un seul document dans la session, le même actif", len(sess_apres["documents"]) == 1
          and sess_apres["active"] == sess_avant["active"] and sess_apres["documents"][0]["revision"] == sess_avant["documents"][0]["revision"],
          (sess_avant, sess_apres))
    # échec en cours de route sur le vrai moteur : maxSide négatif refusé par doc.render, la copie est refermée
    avant_n = len(sess_apres["documents"])
    try:
        PM.vignettes(PM.session(), -5)
        lev = None
    except PM.MoteurErreur as e:
        lev = str(e)
    n_apres = len((await c.get("/api/photolab/session")).json()["documents"])
    check("4h doc.render en échec après image.duplicate : MoteurErreur ET la copie est refermée (1 document)",
          lev is not None and n_apres == avant_n == 1, (lev, avant_n, n_apres))
    # ── historique réel ──
    h = (await c.get("/api/photolab/inspecter")).json()["history"]
    r = await c.post("/api/photolab/historique", json={"annuler": 2})
    h2 = r.json().get("inspect", {}).get("history")
    check("4i /historique {annuler: 2} sur le vrai moteur : deux états de moins, canRedo, completed 2", r.status_code == 200
          and h2 == h[:-2] and r.json()["inspect"].get("canRedo") is True and r.json().get("completed") == 2, (h, r.status_code, r.text[:200]))
    r = await c.post("/api/photolab/historique", json={"retablir": 2})
    check("4j /historique {retablir: 2} les rétablit", r.status_code == 200 and r.json().get("inspect", {}).get("history") == h, r.text[:200])
    r = await c.post("/api/photolab/historique", json={"retablir": 30})
    check("4k plus de rétablissements que possible sur le vrai moteur : 200, failed >= 1 (rien à rétablir)",
          r.status_code == 200 and r.json().get("failed", 0) >= 1 and r.json().get("completed") == 0, (r.status_code, r.text[:200]))

    # ── /bibliotheque ──
    from app.services.storage import init_db
    await init_db()
    dossier = _tmp / "images"
    r = await c.post("/api/photolab/bibliotheque", json={"format": "png"})
    nom = r.json().get("filename", "")
    check("5a /bibliotheque {png} : photolab_<AAAAMMJJ-HHMMSS>_<base>.png dans le dossier des images",
          r.status_code == 200 and re.fullmatch(r"photolab_\d{8}-\d{6}_[A-Za-z0-9_-]+\.png", nom) and (dossier / nom).is_file(), (r.status_code, r.text))
    if nom and (dossier / nom).is_file():
        im = Image.open(dossier / nom)
        check("5b le fichier est un vrai PNG 64 × 32", im.format == "PNG" and im.size == (64, 32), (im.format, im.size))
    r2 = await c.post("/api/photolab/bibliotheque", json={"format": "jpg", "quality": 80})
    nom2 = r2.json().get("filename", "")
    check("5c /bibliotheque {jpg, quality} : .jpg, jamais d'écrasement du précédent", r2.status_code == 200
          and nom2.endswith(".jpg") and nom2 != nom and (dossier / nom2).is_file(), (r2.status_code, r2.text))
    r3 = await c.post("/api/photolab/bibliotheque", json={"format": "png"})
    nom3 = r3.json().get("filename", "")
    check("5d deux enregistrements dans la même seconde : deux noms distincts", r3.status_code == 200 and nom3 not in ("", nom), (nom, nom3))
    check("5d2 l'intermédiaire de exports/ est supprimé après la copie (exports/ reste pour /enregistrer)",
          not any(f.name.startswith("Untitled") for f in (D / "exports").iterdir()), sorted(f.name for f in (D / "exports").iterdir()))
    for corps in ({"format": "psd"}, {"format": "exe"}, {}, {"format": "png", "quality": 0}):
        rr = await c.post("/api/photolab/bibliotheque", json=corps)
        check(f"5e /bibliotheque {corps} -> 400", rr.status_code == 400, (rr.status_code, rr.text))
    lst = (await c.get("/api/images")).json()
    item = next((i for i in lst["images"] if i["filename"] == nom), None)
    check("5f GET /api/images liste le fichier avec source « photolab » (déposée à l'index : origin depot)",
          item is not None and item["source"] == "photolab" and item["source_origin"] == "depot", item and (item["source"], item["source_origin"]))
    check("5g le libellé « Photolab » est dans le catalogue de sources", lst["sources"].get("photolab") == "Photolab", lst["sources"])
    from app.services import library_index as LI
    check("5h licence par défaut : propriétaire (Photolab produit)", item is not None and item.get("licence") == "propriétaire", item and item.get("licence"))
    check("5i l'heuristique reconnaît le préfixe (réconciliation au boot)", LI.heuristique("photolab_20261007-101010_x.png") == "photolab")
    up = await c.post("/api/images/upload", files={"file": ("photolab_20261007-101010_depose.png", open(dossier / nom, "rb").read(), "image/png")})
    lst = (await c.get("/api/images")).json()
    it2 = next((i for i in lst["images"] if i["filename"] == up.json().get("filename")), None)
    check("5j le dépôt par /images/upload d'un nom photolab_ est noté « photolab » (comme vector_)",
          up.status_code == 200 and it2 is not None and it2["source"] == "photolab" and it2["source_origin"] == "depot", it2 and (it2["source"], it2["source_origin"]))
    PM.fermer()


async def statique_scenario(c):
    print("\n[3] montage statique /photolab/")
    r = await c.get("/photolab/")
    check("6a GET /photolab/ -> 200 text/html contenant <title>Photolab", r.status_code == 200
          and r.headers.get("content-type", "").startswith("text/html") and "<title>Photolab" in r.text, (r.status_code, r.headers.get("content-type"), r.text[:200]))
    check("6b en-tête Cache-Control no-cache, must-revalidate", r.headers.get("cache-control") == "no-cache, must-revalidate", dict(r.headers))
    r = await c.get("/photolab", follow_redirects=False)
    check("6c GET /photolab -> 307 vers /photolab/", r.status_code == 307 and r.headers.get("location", "").endswith("/photolab/"),
          (r.status_code, dict(r.headers)))


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
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t") as c:
        await fake_scenario(c)
        await reel_scenario(c)
        await statique_scenario(c)

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
