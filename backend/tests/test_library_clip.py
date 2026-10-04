# -*- coding: utf-8 -*-
"""Bibliotheque, tache #82 PR D (plan-library T12-T13, 04/10/2026) — CLIP en LOCAL, cote serveur.
DECISIONS DE L'UTILISATEUR (04/10) : le moteur « clip » du selecteur ; version LEGERE (≈ 186 Mo, accord donne) :
CLIP ViT-B/32 QUANTIFIE en ONNX, sur le processeur, installe A PART dans <donnees>/clip ; rien ne sort du PC.
Deux parties :
  [I] l'INSTALLATEUR, sur un faux PyPI / Hugging Face (httpx simule) : versions figees, taille ET empreinte verifiees,
      un fichier refuse ne s'installe pas, un fichier deja bon n'est pas repris ;
  [M] le MOTEUR, sur le VRAI CLIP installe (copie sans son index, accord de l'utilisateur pour le telechargement) :
      index, recherche par le sens, semblables, routes.
Temoin positif : la base (64f12040) n'a pas CLIP.
Run (depuis backend/) : & $PY tests/test_library_clip.py"""
import asyncio, hashlib, io, json, os, pathlib, shutil, subprocess, sys, tempfile, time, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzclip_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs", "audio"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ["VECTOR_FOLDER"] = str(_tmp / "vector")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY",
          "ELEVENLABS_API_KEY", "FAL_KEY", "HEYGEN_API_KEY", "FIGMA_TOKEN"):
    os.environ[k] = ""
REEL_CLIP = pathlib.Path(os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGenData\clip"))
os.environ["DEEPOTUS_CLIP_DIR"] = str(_tmp / "clip_faux")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from PIL import Image, ImageDraw                                     # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "64f12040"
r_lc = subprocess.run(["git", "show", f"{BASE}:backend/app/services/library_clip.py"], capture_output=True, cwd=str(RACINE))
check("T0 temoin : la base n'a pas CLIP", r_lc.returncode != 0)

import httpx                                                        # noqa: E402
from app.services import library_clip as C                          # noqa: E402

_SRC = (_ICI.parent / "app" / "services" / "library_clip.py").read_text(encoding="utf-8")
_TOTAL, _MOD = C.TOTAL_OCTETS, list(C.MODELES)
print("[I] l'installateur (faux PyPI / Hugging Face)")
def roue(mod):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr(f"{mod}/__init__.py", f"NOM = '{mod}'\n")
    return b.getvalue()
FICHIERS = {"https://pypi.test/a.whl": roue("modfaux_a"), "https://pypi.test/b.whl": roue("modfaux_b"),
            f"https://huggingface.co/{C.DEPOT}/resolve/{C.REVISION}/onnx/v.onnx": b"V" * 1000,
            f"https://huggingface.co/{C.DEPOT}/resolve/{C.REVISION}/tok.json": b"{}"}
sha = lambda b: hashlib.sha256(b).hexdigest()
C.ROUES = [("a.whl", "https://pypi.test/a.whl", len(FICHIERS["https://pypi.test/a.whl"]), sha(FICHIERS["https://pypi.test/a.whl"])),
           ("b.whl", "https://pypi.test/b.whl", len(FICHIERS["https://pypi.test/b.whl"]), sha(FICHIERS["https://pypi.test/b.whl"]))]
C.MODELES = [("onnx/v.onnx", 1000, sha(b"V" * 1000)), ("tok.json", 2, None)]
C.TOTAL_OCTETS = sum(r[2] for r in C.ROUES) + sum(m[1] for m in C.MODELES)
APPELS = []
def gestion(req):
    APPELS.append(str(req.url))
    b = FICHIERS.get(str(req.url))
    return httpx.Response(200, content=b) if b is not None else httpx.Response(404)
_Vrai = httpx.AsyncClient
class _Faux(_Vrai):
    def __init__(self, *a, **k):
        k.pop("verify", None); k["transport"] = httpx.MockTransport(gestion); super().__init__(*a, **k)
httpx.AsyncClient = _Faux
try:
    asyncio.run(C.installer())
    d = C.dossier()
    check("I1 installe : roues DECOMPRESSEES dans site/, modeles dans modeles/, installe.json ecrit, cache efface, avancement = total",
          C.installe() and (d / "site" / "modfaux_a" / "__init__.py").is_file() and (d / "site" / "modfaux_b" / "__init__.py").is_file()
          and (d / "modeles" / "v.onnx").read_bytes() == b"V" * 1000 and not (d / "telechargements").exists()
          and C.INSTALL["fait"] == C.TOTAL_OCTETS and C.INSTALL["erreur"] == "" and C.INSTALL["en_cours"] is False, json.dumps(C.INSTALL))
    APPELS.clear()
    asyncio.run(C.installer())
    check("I2 relancer : les modeles DEJA bons ne sont pas retelecharges (seules les roues effacees le sont)",
          not any("huggingface" in u for u in APPELS) and C.installe(), str(APPELS))
    shutil.rmtree(d)
    vrai_b = C.ROUES[1]
    C.ROUES[1] = vrai_b[:3] + ("0" * 64,)   # meme taille, empreinte attendue differente
    asyncio.run(C.installer())
    C.ROUES[1] = vrai_b
    check("I3 une roue dont l'EMPREINTE differe est REFUSEE : rien n'est installe, l'erreur est dite, pas de .part qui traine",
          not C.installe() and "empreinte" in C.INSTALL["erreur"] and not list(d.rglob("*.part")) and not (d / "site").exists(), C.INSTALL["erreur"])
    C.MODELES = [("onnx/v.onnx", 999, None), ("tok.json", 2, None)]
    shutil.rmtree(d, ignore_errors=True)
    asyncio.run(C.installer())
    check("I4 une TAILLE differente est refusee", not C.installe() and "octets reçus" in C.INSTALL["erreur"], C.INSTALL["erreur"])
    FICHIERS.pop("https://pypi.test/a.whl")
    shutil.rmtree(d, ignore_errors=True)
    asyncio.run(C.installer())
    check("I5 un 404 est dit et rien n'est installe", not C.installe() and "HTTP 404" in C.INSTALL["erreur"], C.INSTALL["erreur"])
finally:
    httpx.AsyncClient = _Vrai
check("I6 versions FIGEES dans le code : 3 roues cp313 / abi3 win_amd64 (PyPI) et 4 fichiers a une REVISION de Hugging Face ; ≈ 186 Mo",
      _SRC.count("-win_amd64.whl\",") == 6 and _SRC.count("https://files.pythonhosted.org/packages/") == 3
      and 180_000_000 < _TOTAL < 190_000_000 and len(_MOD) == 4 and C.REVISION == "d15189d7028b43f1d3e65039190477f6af591c2a")

from app.services import transfert as TR                            # noqa: E402
_tous = {k: True for k in TR.LOTS}
check("I7 le TRANSFERT entre machines n'emporte pas CLIP (≈ 240 Mo qui se reinstallent d'un clic), meme lots coches ; une image, si",
      TR.exclu("clip/site/numpy/core.pyd")[0] and TR.exclu("clip/modeles/vision_model_quantized.onnx", _tous)[0]
      and TR.exclu("clip/index.npy", _tous)[0] and not TR.exclu("assets/images/a.png")[0])


async def m_main():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services import storage
    from app.config import settings
    import importlib
    await storage.init_db()
    tr = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=tr, base_url="http://127.0.0.1") as cl:
        e = (await cl.get("/api/library/clip/etat")).json()
        r1 = await cl.get("/api/library/recherche", params={"q": "red", "moteur": "clip"})
        r2 = await cl.get("/api/library/semblables/x.png")
        r3 = await cl.post("/api/library/clip/indexer", json={})
        check("M0 sans CLIP : etat « non installe » avec la taille ; recherche clip, semblables, indexer : 503 dits",
              e["installe"] is False and e["octets"] > 0 and (r1.status_code, r2.status_code, r3.status_code) == (503, 503, 503), f"{e} {r1.status_code} {r2.status_code} {r3.status_code}")
        dist = AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False, client=("192.168.1.20", 5000)), base_url="http://192.168.1.20")
        rl = await dist.post("/api/library/clip/installer", json={})
        check("M1 installer depuis le reseau local : refuse", rl.status_code in (401, 403), str(rl.status_code))

        if not (REEL_CLIP / "installe.json").is_file():
            check("M2 le VRAI CLIP est installe sur ce PC (sinon la partie reelle est SAUTEE)", False, str(REEL_CLIP))
            return
        importlib.reload(C)
        os.environ["DEEPOTUS_CLIP_DIR"] = str(_tmp / "clip_reel")
        shutil.copytree(REEL_CLIP, _tmp / "clip_reel", ignore=shutil.ignore_patterns("index.*"))
        I = settings.images_path
        Image.new("RGB", (400, 300), (220, 30, 30)).save(I / "rouge.png")
        Image.new("RGB", (400, 300), (30, 30, 220)).save(I / "bleu.png")
        im = Image.new("RGB", (400, 300), (20, 160, 40)); ImageDraw.Draw(im).ellipse((100, 50, 300, 250), fill=(250, 220, 0)); im.save(I / "vert_soleil.png")
        e = (await cl.get("/api/library/clip/etat")).json()
        check("M2 CLIP installe, rien d'indexe : 3 images a indexer", e["installe"] is True and e["indexees"] == 0 and e["a_indexer"] == 3, json.dumps(e)[:300])
        rr = await cl.get("/api/library/recherche", params={"q": "red", "moteur": "clip"})
        check("M3 avant l'index : la recherche clip ne rend rien (pas d'erreur)", rr.status_code == 200 and rr.json()["resultats"] == [], rr.text[:200])
        ri = await cl.post("/api/library/clip/indexer", json={})
        t0 = time.time()
        while C.INDEX["en_cours"] and time.time() - t0 < 120:
            await asyncio.sleep(0.2)
        e = (await cl.get("/api/library/clip/etat")).json()
        check("M4 l'INDEX en tache de fond : 3 images indexees, plus rien a indexer", ri.status_code == 200 and e["indexees"] == 3 and e["a_indexer"] == 0, json.dumps(e)[:300])
        def top(q):
            return [x["filename"] for x in C._classer(C.vecteur_texte(q), n=3)][0]
        check("M5 par le SENS (CLIP reel) : « a red image » -> rouge.png, « a blue image » -> bleu.png, « a yellow circle on green » -> vert_soleil.png",
              (top("a red image"), top("a blue image"), top("a yellow circle on green")) == ("rouge.png", "bleu.png", "vert_soleil.png"))
        r = (await cl.get("/api/library/recherche", params={"q": "a yellow circle on green", "moteur": "clip"})).json()
        check("M6 la route rend les images classees, scores decroissants, au-dessus du plancher, avec le champ « sens »",
              r["resultats"][0]["filename"] == "vert_soleil.png" and r["resultats"][0]["champs"] == ["sens"]
              and all(a["score"] >= b["score"] for a, b in zip(r["resultats"], r["resultats"][1:])) and all(x["score"] >= C.SEUIL_TEXTE for x in r["resultats"]), json.dumps(r)[:300])
        s = (await cl.get("/api/library/semblables/rouge.png")).json()
        check("M7 SEMBLABLES : l'image n'est pas sa propre voisine ; les autres, classees", [x["filename"] for x in s["semblables"]] == ["bleu.png", "vert_soleil.png"]
              and s["semblables"][0]["score"] > s["semblables"][1]["score"], json.dumps(s))
        r404, r400 = await cl.get("/api/library/semblables/absente.png"), await cl.get("/api/library/semblables/x%5Cy.png")
        check("M8 semblables : 404 image absente, 400 nom invalide", (r404.status_code, r400.status_code) == (404, 400))
        time.sleep(0.05); Image.new("RGB", (400, 300), (250, 250, 0)).save(I / "rouge.png"); (I / "bleu.png").unlink()
        check("M9 un fichier MODIFIE est a re-indexer", C.a_indexer() == ["rouge.png"], str(C.a_indexer()))
        C.indexer_sync()
        noms = C._lire_index()[0]
        check("M10 re-indexer : l'image modifiee refaite, l'image DISPARUE retiree de l'index", sorted(noms) == ["rouge.png", "vert_soleil.png"] and C.a_indexer() == [], str(noms))
        rv = (await cl.get("/api/library/recherche", params={"q": "  ", "moteur": "clip"})).json()
        check("M11 une requete vide ne rend rien", rv["resultats"] == [] and rv["n"] == 0)
        import numpy as np
        cfg = json.loads((C._modeles() / "preprocessor_config.json").read_text(encoding="utf-8"))
        with Image.open(I / "vert_soleil.png") as im0:   # 400x300 -> 299x224 (bicubique), recadrage central 224
            im1 = im0.convert("RGB").resize((299, 224), Image.BICUBIC).crop((37, 0, 261, 224))
        ref = ((np.asarray(im1, dtype=np.float32) * cfg["rescale_factor"] - np.array(cfg["image_mean"], dtype=np.float32))
               / np.array(cfg["image_std"], dtype=np.float32)).transpose(2, 0, 1)[None, ...]
        px = C._pixels(I / "vert_soleil.png")
        check("M13 le pretraitement = celui que le modele DECLARE (preprocessor_config.json : 224, moyenne, ecart-type)",
              px.shape == (1, 3, 224, 224) and np.allclose(px, ref, atol=1e-4), str(float(np.abs(px - ref).max())))
        nv = [float(np.linalg.norm(C.vecteur_image(I / "vert_soleil.png"))), float(np.linalg.norm(C.vecteur_texte("a red car")))]
        check("M14 vecteurs image et texte NORMES (cosinus : score <= 1)", all(abs(n - 1) < 1e-4 for n in nv), str(nv))
        rb = (await cl.get("/api/library/recherche", params={"q": "an old man reading a newspaper", "moteur": "clip"})).json()
        check("M15 un texte SANS RAPPORT (mesure 04/10 : < 0,20 sur ces images) ne rend rien : le plancher ecarte le bruit",
              rb["resultats"] == [] and len(C._classer(C.vecteur_texte("an old man reading a newspaper"), seuil=0.0)) == 2, json.dumps(rb)[:200])
        C.INSTALL["en_cours"] = True; C.INDEX["en_cours"] = True
        try:
            r1, r2 = await cl.post("/api/library/clip/installer", json={}), await cl.post("/api/library/clip/indexer", json={})
        finally:
            C.INSTALL["en_cours"] = False; C.INDEX["en_cours"] = False
        check("M12 une installation ou un index DEJA en cours : 409 dit, rien de relance", (r1.status_code, r2.status_code) == (409, 409), f"{r1.status_code} {r2.status_code}")


asyncio.run(m_main())
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
