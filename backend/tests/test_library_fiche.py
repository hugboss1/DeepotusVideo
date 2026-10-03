# -*- coding: utf-8 -*-
"""Bibliotheque, tache #80 PR A (plan-library T6-T8, 03/10/2026) — la FICHE complete, cote serveur : licence par
defaut, recette du generateur, GET /library/fiche.
DECISIONS DE L'UTILISATEUR (03/10) : licence par defaut PAR SOURCE (produit dans l'app = proprietaire ; imports, URL,
news, Figma, telephone, inconnu = inconnue -> alerte ; particules du catalogue = CC0) + RETRO-REMPLISSAGE des lignes
existantes SANS ecraser une saisie ; /images/generate ENREGISTRE la recette, la fiche lit aussi les recettes deja
posees (images fixes de gabarit, depots du telephone) ; « Rejouer » = /images/generate (payant), recette du generateur
seulement ; usages : rendus, posts, bible, plans, scenes, projets.
Ce que le plan faisait faux : recette tiree de JobRecord (les images du generateur n'ont ni job ni prompt) ; 4 tables
d'usages (pas 5) et shots.image, scenes.vo_audio, projets oublies ; rejouer vers /api/generate (rendu VIDEO).
Le generateur est SIMULE (coeur remplace) : aucun appel payant.
Temoin positif : la base (e216fccb) n'a ni la route, ni la colonne `recette`, ni la licence par defaut.
Run (depuis backend/) : & $PY tests/test_library_fiche.py"""
import asyncio, io, json, os, pathlib, sqlite3, subprocess, sys, tempfile
from datetime import datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzfiche_"))
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


def png(nom, w=40, h=30):
    buf = io.BytesIO(); Image.new("RGB", (w, h), (200, 40, 40)).save(buf, format="PNG")
    (_tmp / "images" / nom).write_bytes(buf.getvalue())


def base(sql, *a):
    con = sqlite3.connect(BASE_DB)
    try:
        r = con.execute(sql, a).fetchall(); con.commit(); return r
    finally:
        con.close()


def lic(nom):
    r = base("SELECT licence FROM library_assets WHERE filename=?", nom)
    return r[0][0] if r else "ABSENTE"


BASE = "e216fccb"
def git(p):
    return subprocess.run(["git", "show", f"{BASE}:{p}"], capture_output=True, cwd=str(RACINE)).stdout
check("T0 temoin : la base n'a ni la route de fiche, ni la colonne recette, ni la licence par defaut",
      b'"/library/fiche/{filename}"' not in git("backend/app/api/routes.py") and b'("recette", "TEXT")' not in git("backend/app/services/storage.py")
      and b"licence_defaut" not in git("backend/app/services/library_index.py"))


async def main():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services import storage
    from app.services import library_index as LI
    from app.api import routes as RT
    from app.config import settings
    await storage.init_db()

    print("[L] la licence par defaut")
    D = LI.licence_defaut
    check("L1 par SOURCE : produit dans l'app = proprietaire ; import, URL, news, Figma, telephone, inconnu = inconnue ; particule du catalogue = CC0",
          [D("a.png", s) for s in ("generation", "retouche", "vectorlab", "templates", "sprites")] == ["propriétaire"] * 5
          and [D("a.png", s) for s in ("import", "import_url", "news", "figma", "mobile", "inconnu", None)] == ["inconnue"] * 7
          and D("particule_spark.png", "inconnu") == "CC0")
    png("g1.png"); png("imp.png")
    await LI.noter(["g1.png"], "generation"); await LI.noter(["imp.png"], "import")
    check("L2 noter pose le defaut d'une ligne neuve", (lic("g1.png"), lic("imp.png")) == ("propriétaire", "inconnue"))
    await LI.editer("imp.png", {"licence": "CC BY"})
    await LI.noter(["imp.png"], "import")
    check("L3 une licence SAISIE n'est jamais ecrasee (noter ensuite garde « CC BY »)", lic("imp.png") == "CC BY")
    # des lignes d'AVANT (licence NULL) + un fichier jamais indexe
    for n, src in (("vieux_gen.png", "generation"), ("vieux_news.png", "news"), ("particule_x.png", "inconnu")):
        png(n); await LI.noter([n], src)
    base("UPDATE library_assets SET licence=NULL WHERE filename IN ('vieux_gen.png','vieux_news.png','particule_x.png')")
    png("gen_jamais.png")
    await LI.reconcilier()
    check("L4 RETRO-REMPLISSAGE au boot : les lignes a NULL recoivent le defaut de leur source ; un fichier jamais indexe entre avec le sien ; la saisie reste",
          (lic("vieux_gen.png"), lic("vieux_news.png"), lic("particule_x.png"), lic("gen_jamais.png"), lic("imp.png"))
          == ("propriétaire", "inconnue", "CC0", "propriétaire", "CC BY"))
    avant = base("SELECT filename, licence FROM library_assets ORDER BY filename")
    await LI.reconcilier()
    check("L5 idempotent : un second passage ne change rien", base("SELECT filename, licence FROM library_assets ORDER BY filename") == avant)
    png("edit_neuf.png")
    await LI.editer("edit_neuf.png", {"note": 3})
    check("L6 une ligne creee par l'edition (fichier au magasin, pas indexe) recoit aussi son defaut", lic("edit_neuf.png") == "inconnue")

    tr = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=tr, base_url="http://127.0.0.1") as cl:
        print("[R] la recette du generateur")
        vrai = RT._generate_image_core
        async def faux(body, bt):
            png("gen_tir.png", 64, 96)
            return {"images": ["gen_tir.png"], "prompt": "un phare, VITRAIL plomb", "model": "flux", "seed": 4242}
        RT._generate_image_core = faux
        try:
            r = await cl.post("/api/images/generate", json={"prompt": "  un phare ", "style": "Vitrail", "size": "square_hd", "model": ""})
        finally:
            RT._generate_image_core = vrai
        rec = json.loads((base("SELECT recette FROM library_assets WHERE filename='gen_tir.png'") or [[None]])[0][0] or "{}")
        check("R1 /images/generate GARDE la recette avec l'image : prompt tel que saisi, style, modele servi, format, graine, prompt envoye ; licence proprietaire",
              r.status_code == 200 and rec.get("prompt") == "un phare" and rec.get("style") == "vitrail" and rec.get("model") == "flux"
              and rec.get("size") == "square_hd" and rec.get("seed") == 4242 and rec.get("prompt_envoye") == "un phare, VITRAIL plomb"
              and "le" in rec and lic("gen_tir.png") == "propriétaire", f"{r.status_code} {rec}")

        print("[F] la fiche")
        f = (await cl.get("/api/library/fiche/gen_tir.png")).json()
        check("F1 image generee : droits (proprietaire, pas d'alerte, liste des licences), fichier (64 x 96, poids, format, date), source dite",
              f["droits"]["licence"] == "propriétaire" and f["droits"]["alerte"] is False and "CC BY-SA" in f["droits"]["licences"]
              and f["fichier"]["largeur"] == 64 and f["fichier"]["hauteur"] == 96 and f["fichier"]["octets"] > 0 and f["fichier"]["format"] == "png"
              and f["fichier"]["modifie"].endswith("+00:00") and f["source"] == "generation" and f["source_libelle"] == "Générateur", json.dumps(f)[:400])
        check("F2 la recette (origine generateur) et « rejouer » : corps pour /api/images/generate, UNE image, graine gardee, rien d'autre ; le PRIX annonce (grille locale)",
              f["recette"]["origine"] == "generation" and f["rejouer"] == {"route": "/api/images/generate", "corps": {
                  "prompt": "un phare", "style": "vitrail", "model": "flux", "size": "square_hd", "seed": 4242, "n": 1, "source": "generation"},
                  "usd": float(__import__("app.services.pricing", fromlist=["x"]).estimate({"kind": "image", "n": 1, "model": "flux"})["total_usd"])}
              and f["rejouer"]["usd"] > 0,
              json.dumps(f["rejouer"]))
        fi = (await cl.get("/api/library/fiche/imp.png")).json()
        png("news_x.png"); await LI.noter(["news_x.png"], "news")
        fn = (await cl.get("/api/library/fiche/news_x.png")).json()
        check("F3 un import : la licence SAISIE ; une image de news : « inconnue » ET alerte ; ni recette ni rejouer",
              fi["droits"]["licence"] == "CC BY" and fi["droits"]["alerte"] is False and fn["droits"]["licence"] == "inconnue"
              and fn["droits"]["alerte"] is True and fn["recette"] is None and fn["rejouer"] is None)
        png("tpl_still_ab.png"); (_tmp / "images" / "tpl_still_ab.png.recette.json").write_text(json.dumps({"template_id": "tpl_x", "at_s": 1.0}), encoding="utf-8")
        png("mob_1.png"); rd = settings.outputs_path / "_sync" / "recettes"; rd.mkdir(parents=True, exist_ok=True)
        (rd / "mob_1.png.json").write_text(json.dumps({"prompt": "pris au telephone", "appareil": {"nom": "P"}}), encoding="utf-8")
        ft, fm = (await cl.get("/api/library/fiche/tpl_still_ab.png")).json(), (await cl.get("/api/library/fiche/mob_1.png")).json()
        check("F4 les recettes DEJA posees : image fixe de gabarit (« template ») et depot du telephone (« mobile ») ; elles ne se rejouent pas",
              ft["recette"] == {"origine": "template", "template_id": "tpl_x", "at_s": 1.0} and ft["rejouer"] is None
              and fm["recette"]["origine"] == "mobile" and fm["recette"]["prompt"] == "pris au telephone" and fm["rejouer"] is None,
              json.dumps([ft["recette"], fm["recette"]]))

        print("[U] les usages")
        png("u.png"); png("xu.png")
        async with storage.async_session_factory() as s:
            s.add(storage.JobRecord(id="job-a", status="done", progress=100, image_filename="u.png", title="Rendu A"))
            s.add(storage.JobRecord(id="job-b", status="done", progress=100, image_filename="autre.png", image_filename_end="u.png"))
            s.add(storage.ScheduledPost(id="post-1", title="Post 1", run_at=datetime(2026, 10, 9, 8, 0), source_image="u.png"))
            s.add(storage.BibleEntity(id="bib-1", kind="character", name="Ysolde", ref_image="u.png"))
            s.add(storage.BibleEntity(id="bib-2", kind="place", name="Phare", inspiration_images=json.dumps(["xu.png", "u.png"])))
            s.add(storage.BibleEntity(id="bib-3", kind="place", name="Faux", inspiration_images=json.dumps(["xu.png"])))
            # « _ » est un JOKER de LIKE : « u_a.png » ressemble a « uxa.png » — la relecture de la liste l'ecarte
            s.add(storage.BibleEntity(id="bib-4", kind="place", name="Joker", inspiration_images=json.dumps(["uxa.png"])))
            s.add(storage.Shot(id="shot-1", chapter_id="ch-1", idx=2, image="u.png"))
            s.add(storage.LibraryProject(id="pj-1", nom="Campagne"))
            s.add(storage.LibraryProjectItem(project_id="pj-1", ref="u.png", kind="image"))
            await s.commit()
        png("u_a.png")
        uj = (await cl.get("/api/library/fiche/u_a.png")).json()["usages"]
        us = (await cl.get("/api/library/fiche/u.png")).json()["usages"]
        vu = sorted((u["type"], u["id"], u["role"]) for u in us)
        check("U1 rendus (depart / fin), post programme, bible (reference, inspiration), plan (production), projet — et PAS une inspiration qui cite un autre nom",
              vu == sorted([("rendu", "job-a", "image de départ"), ("rendu", "job-b", "image de fin"), ("post", "post-1", "draft"),
                            ("bible", "bib-1", "référence"), ("bible", "bib-2", "inspiration"), ("plan", "shot-1", "production"),
                            ("projet", "pj-1", "membre")]) and uj == [], str(vu) + str(uj))
        # un « son » dont les octets sont ceux d'une image : la fiche ne lit JAMAIS les dimensions d'un son
        _b = io.BytesIO(); Image.new("RGB", (9, 9)).save(_b, format="PNG"); (_tmp / "audio" / "vo.mp3").write_bytes(_b.getvalue())
        async with storage.async_session_factory() as s:
            s.add(storage.Scene(id="sc-1", chapter_id="ch-1", slugline="INT. PHARE - NUIT", vo_audio="vo.mp3")); await s.commit()
        fa = (await cl.get("/api/library/fiche/vo.mp3")).json()
        check("U2 un SON : la scene dont il est la voix off ; ni dimensions ni recette", fa["kind"] == "audio" and fa["usages"] == [{
            "type": "scene", "id": "sc-1", "libelle": "INT. PHARE - NUIT", "role": "voix off", "chapitre": "ch-1"}]
              and fa["fichier"]["largeur"] is None and fa["fichier"]["octets"] == len(_b.getvalue()), json.dumps(fa)[:300])

        print("[E] edition et refus")
        r = await cl.patch("/api/library/asset/news_x.png", json={"licence": "CC BY-SA", "auteur": "AFP", "source_url": "https://exemple.org/p"})
        fe = (await cl.get("/api/library/fiche/news_x.png")).json()
        check("E1 PATCH (deja la, #77) puis fiche : licence, auteur, lien relus ; l'alerte tombe", r.status_code == 200 and fe["droits"]["licence"] == "CC BY-SA"
              and fe["droits"]["auteur"] == "AFP" and fe["droits"]["source_url"] == "https://exemple.org/p" and fe["droits"]["alerte"] is False)
        r404, r400 = await cl.get("/api/library/fiche/absent.png"), await cl.get("/api/library/fiche/x%5Cy.png")
        check("E2 404 pour un fichier absent ; 400 pour un nom qui n'est pas un nom", (r404.status_code, r400.status_code) == (404, 400))
        png("jamais_vu.png")
        fj = (await cl.get("/api/library/fiche/jamais_vu.png")).json()
        check("E3 une image au magasin mais pas encore indexee a sa fiche (licence par defaut calculee, origine heuristique)",
              fj["droits"]["licence"] == "inconnue" and fj["origin"] == "heuristique" and fj["fichier"]["largeur"] == 40)

    print("[M] la migration d'une base d'AVANT")
    base("ALTER TABLE library_assets DROP COLUMN recette")
    sans = "recette" not in [c[1] for c in base("PRAGMA table_info(library_assets)")]
    await storage._auto_migrate()
    check("M1 une base sans la colonne `recette` la recoit au demarrage (ALTER par LIBRARY_ASSETS_COLUMNS)",
          sans and "recette" in [c[1] for c in base("PRAGMA table_info(library_assets)")])


asyncio.run(main())
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
