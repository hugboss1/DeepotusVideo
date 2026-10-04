# -*- coding: utf-8 -*-
"""Bibliotheque, tache #81 PR B (plan-library T9, T11, 03/10/2026) — NETTOYAGE (doublons exacts, poids) et COULEUR
DOMINANTE, cote serveur.
DECISIONS DE L'UTILISATEUR (03/10) : doublons EXACTS (sha256 recalcule si le fichier change) avec leurs usages,
l'utilisateur coche, la copie UTILISEE est protegee et un groupe garde au moins une copie, ce qui part va a la CORBEILLE ;
couleur dominante EN TACHE DE FOND apres le demarrage et pour chaque nouvelle image, 12 teintes + neutre.
Ce que le plan faisait faux : sha256 et couleur DANS le reconcilier du demarrage (31 s mesurees, lifespan attendu =
serveur muet) ; sha256 pose une fois (un fichier reecrit en place gardait l'ancienne) ; aucune protection des copies.
Temoin positif : la base (a6e226ed) n'a ni nettoyage ni couleur.
Run (depuis backend/) : & $PY tests/test_library_nettoyage.py"""
import asyncio, io, json, os, pathlib, sqlite3, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dznett_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
BASE_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{BASE_DB.as_posix()}"
for d in ("images", "outputs", "audio"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ["VECTOR_FOLDER"] = str(_tmp / "vector")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY",
          "ELEVENLABS_API_KEY", "FAL_KEY", "HEYGEN_API_KEY", "FIGMA_TOKEN"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from PIL import Image                                               # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


IMG = _tmp / "images"
def png(nom, couleur=(10, 60, 220), taille=(32, 32), mode="RGB", carre=None):
    im = Image.new(mode, taille, couleur)
    if carre:
        for x in range(carre[0][0], carre[0][2]):
            for y in range(carre[0][1], carre[0][3]):
                im.putpixel((x, y), carre[1])
    buf = io.BytesIO(); im.save(buf, format="PNG"); (IMG / nom).write_bytes(buf.getvalue())


def base(sql, *a):
    con = sqlite3.connect(BASE_DB)
    try:
        r = con.execute(sql, a).fetchall(); con.commit(); return r
    finally:
        con.close()


BASE = "a6e226ed"
def git(p):
    return subprocess.run(["git", "show", f"{BASE}:{p}"], capture_output=True, cwd=str(RACINE))
check("T0 temoin : la base n'a ni le nettoyage ni la couleur", git("backend/app/services/library_nettoyage.py").returncode != 0
      and git("backend/app/services/library_couleur.py").returncode != 0 and b'"/library/nettoyage"' not in git("backend/app/api/routes.py").stdout)


async def attendre(cond, s=15):
    t = time.time()
    while time.time() - t < s:
        if cond():
            return True
        await asyncio.sleep(0.1)
    return False


async def main():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services import storage
    from app.services import library_index as LI
    from app.services import library_couleur as LCOL
    from app.services import library_corbeille as LC
    await storage.init_db()

    print("[K] la couleur dominante")
    N = LCOL.nommer
    check("K1 12 teintes + neutre : rouge, orange, jaune, vert-jaune, vert, emeraude, cyan, azur, bleu, violet, magenta, rose ; gris, quasi-noir et quasi-blanc = neutre",
          [N(c) for c in ((255, 0, 0), (255, 128, 0), (255, 255, 0), (128, 255, 0), (0, 255, 0), (0, 255, 128), (0, 255, 255), (0, 128, 255),
                          (0, 0, 255), (128, 0, 255), (255, 0, 255), (255, 0, 128))]
          == ["rouge", "orange", "jaune", "vert-jaune", "vert", "émeraude", "cyan", "azur", "bleu", "violet", "magenta", "rose"]
          and [N(c) for c in ((128, 128, 128), (5, 5, 5), (250, 250, 250), (140, 120, 125), (242, 239, 233), (14, 20, 30))] == ["neutre"] * 6
          and N((14, 58, 92)) == "azur")
    png("bleu.png", (10, 60, 220), carre=((0, 0, 6, 6), (230, 20, 20)))
    png("sticker.png", (0, 0, 0, 0), mode="RGBA", carre=((8, 8, 24, 24), (220, 30, 30, 255)))
    png("vide.png", (0, 0, 0, 0), mode="RGBA")
    (IMG / "casse.png").write_bytes(b"pas une image")
    D = LCOL.dominante
    d1, d2 = D(IMG / "bleu.png"), D(IMG / "sticker.png")
    check("K2 la couleur la PLUS FREQUENTE (un petit carre rouge ne change rien) ; la TRANSPARENCE ne compte pas (un sticker rouge detoure est rouge, pas noir) ; vide ou illisible : rien",
          d1 and d1[1] == "bleu" and d1[0].startswith("#") and len(d1[0]) == 7 and d2 and d2[1] == "rouge"
          and D(IMG / "vide.png") is None and D(IMG / "casse.png") is None, f"{d1} {d2}")
    png("hors.png", (0, 200, 0)); await LI.noter(["hors.png"], "import"); await asyncio.sleep(1.0)
    check("K3a hors d'un serveur demarre, noter ne lance RIEN en tache de fond (drapeau du demarrage)",
          LCOL.ACTIF is False and base("SELECT teinte FROM library_assets WHERE filename='hors.png'") == [(None,)])
    (IMG / "hors.png").unlink(); base("DELETE FROM library_assets WHERE filename='hors.png'")
    LCOL.ACTIF = True   # comme apres le demarrage
    for n in ("bleu.png", "sticker.png"):
        await LI.noter([n], "import")
    ok_k3 = await attendre(lambda: base("SELECT COUNT(*) FROM library_assets WHERE filename IN ('bleu.png','sticker.png') AND teinte IS NOT NULL") == [(2,)])
    check("K3 chaque NOUVELLE image (noter) recoit sa couleur EN TACHE DE FOND, sans que noter attende",
          ok_k3 and base("SELECT teinte FROM library_assets WHERE filename='bleu.png'") == [("bleu",)], str(base("SELECT filename, couleur, teinte FROM library_assets")))
    base("UPDATE library_assets SET couleur=NULL, teinte=NULL")
    t0 = time.time(); n = await LCOL.remplir(); dt = time.time() - t0
    check("K4 remplir() colorie les images SANS couleur (une illisible reste sans) et rend le nombre",
          n == 2 and base("SELECT COUNT(*) FROM library_assets WHERE teinte IS NOT NULL") == [(2,)], f"{n} {dt}")
    png("bleu.png", (240, 200, 10))
    await LCOL.remplir(["bleu.png"])
    check("K5 remplir(noms) RECALCULE les images nommees (un fichier reecrit change de couleur)", base("SELECT teinte FROM library_assets WHERE filename='bleu.png'") == [("jaune",)])

    print("[B] au demarrage")
    base("UPDATE library_assets SET couleur=NULL, teinte=NULL")
    LCOL.ACTIF = False   # c'est le DEMARRAGE qui doit l'armer
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        rep = c.get("/api/health")
        pret = time.time()
        while time.time() - pret < 15 and base("SELECT COUNT(*) FROM library_assets WHERE teinte IS NOT NULL") != [(2,)]:
            time.sleep(0.1)
    check("K6 le DEMARRAGE lance la couleur en tache de fond (le serveur repond pendant ce temps) ; /api/images sert couleur et teinte",
          rep.status_code == 200 and LCOL.ACTIF is True and base("SELECT COUNT(*) FROM library_assets WHERE teinte IS NOT NULL") == [(2,)], str(base("SELECT filename, teinte FROM library_assets")))

    tr = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=tr, base_url="http://127.0.0.1") as cl:
        im = {i["filename"]: i for i in (await cl.get("/api/images")).json()["images"]}
        fi = (await cl.get("/api/library/fiche/sticker.png")).json()
        check("K7 la grille et la fiche servent la couleur (hex + teinte)", im["sticker.png"]["teinte"] == "rouge" and im["sticker.png"]["couleur"].startswith("#")
              and fi["couleur"]["teinte"] == "rouge" and fi["couleur"]["hex"] == im["sticker.png"]["couleur"], json.dumps(fi.get("couleur")))

        print("[D] les doublons")
        for n in ("a.png", "b.png", "c.png", "d.png"):
            png(n, (90, 90, 30), (40, 40))
        png("e.png", (1, 2, 3), (40, 40)); png("f.png", (200, 10, 200), (20, 20)); png("g.png", (200, 10, 200), (20, 20))
        os.utime(IMG / "g.png", (time.time() - 3600 * 24 * 3, time.time() - 3600 * 24 * 3))
        for n in ("a.png", "b.png", "c.png", "d.png", "e.png", "f.png", "g.png"):
            await LI.noter([n], "generation")
        await LI.editer("c.png", {"fav": True})
        async with storage.async_session_factory() as s:
            s.add(storage.JobRecord(id="job-d", status="done", progress=100, image_filename="d.png", title="Rendu D")); await s.commit()
        r = (await cl.get("/api/library/nettoyage")).json()
        g1 = next(g for g in r["doublons"] if "a.png" in [f["filename"] for f in g["fichiers"]])
        g2 = next(g for g in r["doublons"] if "f.png" in [f["filename"] for f in g["fichiers"]])
        P = {f["filename"]: f for f in g1["fichiers"]}
        check("D1 deux groupes EXACTS (e.png, unique, n'y est pas) ; copies en trop et octets recuperables comptes",
              len(r["doublons"]) == 2 and sorted(P) == ["a.png", "b.png", "c.png", "d.png"] and g1["en_trop"] == 3
              and r["copies_en_trop"] == 4 and r["octets_recuperables"] == g1["octets"] * 3 + g2["octets"], json.dumps(r)[:400])
        check("D2 la copie UTILISEE est protegee (favori, usage par un rendu) et ses usages sont dits ; les autres ne le sont pas",
              P["c.png"]["protege"] and P["c.png"]["fav"] and P["d.png"]["protege"] and P["d.png"]["usages"][0]["libelle"] == "Rendu D"
              and not P["a.png"]["protege"] and not P["b.png"]["protege"], json.dumps(P)[:400])
        Q = {f["filename"]: f for f in g2["fichiers"]}
        check("D3 un groupe SANS copie protegee propose de GARDER la plus ancienne (g.png)", Q["g.png"].get("garder") is True and "garder" not in Q["f.png"])
        check("D4 les empreintes et poids vont a l'INDEX ; le poids par sorte est rendu",
              base("SELECT COUNT(*) FROM library_assets WHERE sha256 IS NOT NULL AND taille_o > 0") == [(len(list(IMG.glob('*.png'))),)]
              and r["poids"]["images"]["fichiers"] == len(list(IMG.glob("*.png"))) and "corbeille" in r["poids"] and "sons" in r["poids"], json.dumps(r["poids"]))
        png("b.png", (5, 200, 5), (40, 40))
        time.sleep(0.02); os.utime(IMG / "b.png")
        r2 = (await cl.get("/api/library/nettoyage")).json()
        g1b = next(g for g in r2["doublons"] if "a.png" in [f["filename"] for f in g["fichiers"]])
        check("D5 un fichier REECRIT en place est re-hache : b.png quitte le groupe", "b.png" not in [f["filename"] for f in g1b["fichiers"]]
              and base("SELECT sha256 FROM library_assets WHERE filename='b.png'") != base("SELECT sha256 FROM library_assets WHERE filename='a.png'"))

        print("[J] jeter des copies")
        rj = await cl.post("/api/library/nettoyage/jeter", json={"fichiers": ["a.png"]})
        check("J1 une copie non protegee part a la CORBEILLE (restaurable)", rj.status_code == 200 and rj.json()["jetes"][0]["filename"] == "a.png"
              and not (IMG / "a.png").exists() and (LC.dossier() / rj.json()["jetes"][0]["corbeille"]).is_dir(), rj.text)
        refus = [await cl.post("/api/library/nettoyage/jeter", json={"fichiers": f}) for f in (["c.png"], ["f.png", "g.png"], ["e.png"], ["d.png"])]
        check("J2 refus 409 : une copie protegee (favori), un groupe qui perdrait TOUTES ses copies, un fichier qui n'est pas un doublon, une copie utilisee — et rien n'est parti",
              [x.status_code for x in refus] == [409, 409, 409, 409] and all((IMG / n).exists() for n in ("c.png", "f.png", "g.png", "e.png", "d.png"))
              and "protégé" in refus[0].json()["detail"] and "zéro copie" in refus[1].json()["detail"], str([x.text for x in refus]))
        rg = await cl.post("/api/library/nettoyage/jeter", json={"fichiers": ["f.png"]})
        check("J3 dans un groupe sans protection, jeter une copie en laisse une (permis)", rg.status_code == 200 and (IMG / "g.png").exists(), rg.text)
        b1, b2 = await cl.post("/api/library/nettoyage/jeter", json={"fichiers": []}), await cl.post("/api/library/nettoyage/jeter", json={"fichiers": "a.png"})
        check("J4 un corps sans liste de noms : 400", (b1.status_code, b2.status_code) == (400, 400))


asyncio.run(main())
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
