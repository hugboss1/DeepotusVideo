# -*- coding: utf-8 -*-
"""Bibliotheque, tache #77 PR A (plan-library T0-T1, 03/10/2026) — tags, favori et note 0..5 EN BASE, cote serveur.
DECISIONS DE L'UTILISATEUR (03/10) : le favori (oui/non) et la note (0..5) sont DEUX notions, jamais couplees ; les
favoris des RENDUS (dz_fav_renders, des ids de job) passent aussi en base (jobs.fav) ; l'ecran viendra en PR B.
Ce que le plan faisait faux, et que ce banc garde : renommer() recopiait une liste figee de champs (tags, favori et note
perdus au renommage) ; PATCH creait une ligne d'index pour un fichier ABSENT du magasin (-> 404 ici).
Banc-miroir : on lit la BASE (sqlite3) et le JSON SERVI, jamais le code qui pretend les produire.
Temoin positif : la base (ac9ff0e6) n'a ni les colonnes ni les routes.
Run (depuis backend/) : & $PY tests/test_library_meta.py"""
import asyncio, io, json, os, pathlib, sqlite3, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzlibmeta_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
BASE_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{BASE_DB.as_posix()}"
for d in ("images", "outputs", "audio"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ["VECTOR_FOLDER"] = str(_tmp / "vector")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY",
          "ELEVENLABS_API_KEY", "FAL_KEY", "HEYGEN_API_KEY"):
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


def png(nom, couleur=(10, 200, 30)):
    buf = io.BytesIO(); Image.new("RGB", (8, 8), couleur).save(buf, format="PNG")
    (_tmp / "images" / nom).write_bytes(buf.getvalue())


def base(sql, *a):
    con = sqlite3.connect(BASE_DB)
    try:
        return con.execute(sql, a).fetchall()
    finally:
        con.close()


BASE = "ac9ff0e6"
r_st = subprocess.run(["git", "show", f"{BASE}:backend/app/services/storage.py"], capture_output=True, cwd=str(RACINE)).stdout
r_ro = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE)).stdout
check("T0 temoin : la base n'a ni les colonnes ni les routes du DAM", b"LIBRARY_ASSETS_COLUMNS" not in r_st
      and b'"/library/asset/{filename}"' not in r_ro and b'"/jobs/{job_id}/fav"' not in r_ro and len(r_ro) > 100000)

NEUVES = ("tags", "fav", "note", "parent_filename", "relation", "licence", "auteur", "source_url", "sha256",
          "taille_o", "couleur", "teinte")


async def main():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services import storage
    from app.services import library_index as LI

    print("[M] la migration")
    # Une base d'AVANT : library_assets a ses 8 colonnes du 28/08, jobs n'a pas `fav`.
    await storage.init_db()
    con = sqlite3.connect(BASE_DB)
    con.execute("DROP TABLE library_assets")
    con.execute("CREATE TABLE library_assets (filename VARCHAR(255) PRIMARY KEY, source VARCHAR(24), kind VARCHAR(12),"
                " origin VARCHAR(12), job_id VARCHAR(36), deck_id VARCHAR(36), doc_id VARCHAR(36), created DATETIME)")
    con.execute("INSERT INTO library_assets (filename, source, kind, origin) VALUES ('vieux.png', 'generation', 'image', 'depot')")
    jcols = [r[1] for r in con.execute("PRAGMA table_info(jobs)")]
    con.execute("ALTER TABLE jobs DROP COLUMN fav") if "fav" in jcols else None
    con.commit(); con.close()
    await storage.init_db()
    cols = {r[1] for r in base("PRAGMA table_info(library_assets)")}
    check("M1 une base d'avant recoit les 12 colonnes neuves de library_assets", all(c in cols for c in NEUVES),
          str(sorted(set(NEUVES) - cols)))
    check("M2 ... sans perdre ses lignes", base("SELECT filename, source, origin FROM library_assets")
          == [("vieux.png", "generation", "depot")])
    check("M3 jobs recoit `fav`", "fav" in {r[1] for r in base("PRAGMA table_info(jobs)")})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as cl:
        print("\n[C] la carte et la liste")
        png("gen_aa11.png"); png("vieux.png")
        await LI.noter(["gen_aa11.png"], "generation")
        c = await LI.carte()
        check("C1 carte() rend un DICT par fichier (source, origin lus par nom)", isinstance(c.get("gen_aa11.png"), dict)
              and c["gen_aa11.png"].get("source") == "generation" and c["gen_aa11.png"].get("origin") == "depot", str(c.get("gen_aa11.png")))
        im = {i["filename"]: i for i in (await cl.get("/api/images")).json()["images"]}
        a = im.get("gen_aa11.png", {})
        check("C2 GET /api/images sert les champs du DAM, jamais None pour une liste : tags [], fav false, note 0",
              a.get("source") == "generation" and a.get("tags") == [] and a.get("fav") is False and a.get("note") == 0
              and "couleur" in a and a.get("couleur") is None, str(a))
        import re as _re
        appelants = {p.relative_to(_ICI.parent).as_posix(): p.read_text("utf-8") for p in (_ICI.parent / "app").rglob("*.py")
                     if "LI.carte()" in p.read_text("utf-8")}
        tuples = [n for n, s in appelants.items() if _re.search(r"connu\[[01]\]|prov\[[^\]]+\]\[[01]\]", s)]
        check("C4 TOUS les appelants de carte() la lisent en dict (le plan n'en voyait qu'un ; sync_index lisait connu[0])",
              len(appelants) >= 2 and not tuples, f"{sorted(appelants)} tuples={tuples}")
        check("C3 la provenance d'avant ne bouge pas (source + source_origin, fichier jamais indexe = heuristique)",
              im["vieux.png"]["source"] == "generation" and im["vieux.png"]["source_origin"] == "depot")

        print("\n[P] PATCH /api/library/asset/{f}")
        png("gen_bb22.png")
        r = await cl.patch("/api/library/asset/gen_bb22.png", json={"tags": ["  Vitrail ", "vitrail", "Deep   Sea", ""],
                                                                   "fav": True, "note": 4})
        check("P1 200 et l'etat RELU : tags normalises (minuscules, espaces reduits, dedoublonnes, vides retires)",
              r.status_code == 200 and r.json().get("tags") == ["vitrail", "deep sea"] and r.json().get("fav") is True
              and r.json().get("note") == 4, r.text)
        row = base("SELECT tags, fav, note, origin, source FROM library_assets WHERE filename='gen_bb22.png'")
        check("P2 en BASE : la ligne est creee a la volee (fichier present mais jamais indexe -> heuristique)",
              row and json.loads(row[0][0]) == ["vitrail", "deep sea"] and row[0][1] == 1 and row[0][2] == 4
              and row[0][3] == "heuristique" and row[0][4] == "generation", str(row))
        await cl.patch("/api/library/asset/gen_bb22.png", json={"fav": False})
        row = base("SELECT fav, note FROM library_assets WHERE filename='gen_bb22.png'")
        check("P3 favori et note sont DEUX notions : retirer le favori laisse la note (4)", row == [(0, 4)], str(row))
        await cl.patch("/api/library/asset/gen_bb22.png", json={"note": 0, "fav": True})
        check("P4 ... et remettre la note a 0 laisse le favori", base("SELECT fav, note FROM library_assets WHERE "
                                                                      "filename='gen_bb22.png'") == [(1, 0)])
        mauvais = []
        for corps in ({"note": 9}, {"note": -1}, {"note": "3"}, {"note": True}, {"note": 3.0}, {"fav": "oui"},
                      {"tags": "vitrail"}, {"tags": [1, 2]}, {}, {"source": "figma"}):
            rr = await cl.patch("/api/library/asset/gen_bb22.png", json=corps)
            if rr.status_code != 400:
                mauvais.append((corps, rr.status_code))
        check("P5 400 sur une note hors 0..5 ou non entiere, un favori non booleen, des tags non liste de chaines, un corps "
              "vide ou sans champ editable (source n'est PAS editable)", not mauvais, str(mauvais))
        check("P6 ... et rien n'a bouge en base", base("SELECT fav, note, source FROM library_assets WHERE filename="
                                                       "'gen_bb22.png'") == [(1, 0, "generation")])
        r404 = await cl.patch("/api/library/asset/fantome.png", json={"fav": True})
        check("P7 404 pour un fichier ABSENT du magasin, et AUCUNE ligne creee (le plan en creait une)",
              r404.status_code == 404 and base("SELECT count(*) FROM library_assets WHERE filename='fantome.png'") == [(0,)],
              f"{r404.status_code} {r404.text}")
        rb = await cl.patch("/api/library/asset/..", json={"fav": True})
        check("P8 un nom douteux est refuse (400/404/405, jamais 200)", rb.status_code in (400, 404, 405), str(rb.status_code))
        (_tmp / "audio" / "voix.mp3").write_bytes(b"ID3fake")
        ra = await cl.patch("/api/library/asset/voix.mp3", json={"tags": ["Voix"]})
        check("P9 un son du magasin audio s'edite aussi (kind audio)", ra.status_code == 200 and base(
            "SELECT kind, tags FROM library_assets WHERE filename='voix.mp3'") == [("audio", '["voix"]')], ra.text)
        await cl.patch("/api/library/asset/gen_aa11.png", json={"tags": ["vitrail"], "note": 4})
        await cl.patch("/api/library/asset/gen_bb22.png", json={"tags": ["vitrail", "deep sea"], "note": 2})
        im = {i["filename"]: i for i in (await cl.get("/api/images")).json()["images"]}
        check("P10 GET /api/images sert ce qui est en base", im["gen_bb22.png"]["tags"] == ["vitrail", "deep sea"]
              and im["gen_bb22.png"]["fav"] is True and im["gen_bb22.png"]["note"] == 2 and im["gen_aa11.png"]["note"] == 4)

        print("\n[F] les facettes")
        f = (await cl.get("/api/library/facettes")).json()
        check("F1 les valeurs REELLEMENT presentes, comptees, triees par nombre puis nom ; favoris et notes comptes",
              f.get("tags", [None])[0] == {"valeur": "vitrail", "n": 2} and {"valeur": "deep sea", "n": 1} in f["tags"]
              and {"valeur": "voix", "n": 1} in f["tags"] and f.get("favoris") == 1
              and f.get("notes") == {"2": 1, "4": 1}, str(f))
        con = sqlite3.connect(BASE_DB); con.execute("UPDATE library_assets SET tags='{pas du json' WHERE filename='vieux.png'")
        con.commit(); con.close()
        f2 = await cl.get("/api/library/facettes"); l2 = await cl.get("/api/images")
        check("F2 une valeur de tags abimee en base ne casse ni les facettes ni la liste (elle se lit [])",
              f2.status_code == 200 and l2.status_code == 200
              and [i for i in l2.json()["images"] if i["filename"] == "vieux.png"][0]["tags"] == [])

        print("\n[R] renommer et supprimer")
        rr = await cl.post("/api/images/gen_bb22.png/rename", json={"new_name": "mon vitrail"})
        neuf = rr.json().get("new")
        row = base("SELECT tags, fav, note, source FROM library_assets WHERE filename=?", neuf)
        check("R1 le renommage EMPORTE tags, favori et note (le plan les perdait : liste figee de champs)",
              rr.status_code == 200 and row and LI.tags_lus(row[0][0]) == ["vitrail", "deep sea"] and row[0][1:] == (1, 2, "generation")
              and base("SELECT count(*) FROM library_assets WHERE filename='gen_bb22.png'") == [(0,)], f"{rr.text} {row}")

        print("\n[J] le favori des rendus")
        from app.services.storage import JobRecord, async_session_factory
        async with async_session_factory() as s:
            for jid in ("job-a", "job-b", "job-c"):
                s.add(JobRecord(id=jid, status="done", progress=100, provider="seedance", title=jid, image_filename="x.png"))
            await s.commit()
        rj = await cl.put("/api/jobs/job-a/fav", json={"fav": True})
        check("J1 PUT /api/jobs/{id}/fav pose le favori, en BASE, et le rend", rj.status_code == 200 and rj.json().get("fav") is True
              and base("SELECT fav FROM jobs WHERE id='job-a'") == [(1,)], rj.text)
        lst = {j["job_id"]: j for j in (await cl.get("/api/jobs")).json()}
        check("J2 GET /api/jobs sert `fav` (false par defaut, NULL d'une base d'avant compris)",
              lst["job-a"]["fav"] is True and lst["job-b"]["fav"] is False)
        await cl.put("/api/jobs/job-a/rating", json={"rating": 3})
        await cl.put("/api/jobs/job-a/fav", json={"fav": False})
        check("J3 favori et note du rendu restent independants", base("SELECT fav, rating FROM jobs WHERE id='job-a'") == [(0, 3)])
        bad = [(c, (await cl.put("/api/jobs/job-a/fav", json=c)).status_code) for c in ({"fav": 1}, {"fav": "true"}, {}, {"fav": None})]
        check("J4 400 si fav n'est pas un booleen", all(s == 400 for _, s in bad), str(bad))
        check("J5 404 pour un job inconnu", (await cl.put("/api/jobs/nope/fav", json={"fav": True})).status_code == 404)
        await cl.put("/api/jobs/job-c/fav", json={"fav": True})
        fl = [j["job_id"] for j in (await cl.get("/api/jobs?fav=1")).json()]
        check("J6 GET /api/jobs?fav=1 ne garde que les favoris (filtre AVANT le limit, comme min_rating)", fl == ["job-c"], str(fl))

        print("\n[I] la reprise des favoris du navigateur")
        png("gen_cc33.png")
        r = await cl.post("/api/library/favoris/import", json={"images": ["gen_cc33.png", "absent.png", "../x.png"],
                                                               "renders": ["job-b", "inconnu"]})
        d = r.json()
        check("I1 les listes du navigateur entrent en base : images et rendus repris, absents RENDUS (jamais avales)",
              r.status_code == 200 and d.get("images") == {"repris": 1, "ignores": ["absent.png", "x.png"]}
              and d.get("renders") == {"repris": 1, "ignores": ["inconnu"]}
              and base("SELECT fav FROM library_assets WHERE filename='gen_cc33.png'") == [(1,)]
              and base("SELECT fav FROM jobs WHERE id='job-b'") == [(1,)], str(d))
        d2 = (await cl.post("/api/library/favoris/import", json={"images": ["gen_cc33.png"], "renders": ["job-b"]})).json()
        check("I2 idempotente : rejouee, elle ne reprend rien", d2.get("images", {}).get("repris") == 0
              and d2.get("renders", {}).get("repris") == 0, str(d2))
        d3 = await cl.post("/api/library/favoris/import", json={"images": "gen_cc33.png"})
        check("I3 400 si une liste n'en est pas une", d3.status_code == 400, str(d3.status_code))

        print("\n[G] la garde des ecritures locales")
        async with AsyncClient(transport=ASGITransport(app=app, client=("192.168.1.20", 50000)), base_url="http://t") as dist:
            g1 = await dist.patch("/api/library/asset/gen_cc33.png", json={"fav": False})
            g2 = await dist.put("/api/jobs/job-b/fav", json={"fav": False})
            g3 = await dist.post("/api/library/favoris/import", json={"images": []})
        check("G1 depuis le reseau local sans jeton, les trois ecritures sont refusees (401 de la garde d'appareil) et rien ne bouge",
              (g1.status_code, g2.status_code, g3.status_code) == (401, 401, 401)
              and base("SELECT fav FROM library_assets WHERE filename='gen_cc33.png'") == [(1,)], f"{g1.status_code} {g2.status_code} {g3.status_code}")
        import app.main as M
        ouvertes = {c for _m, c in M._ECRITURES_OUVERTES}
        check("G2 ... et un telephone APPAIRE serait refuse aussi (403) : aucune des trois n'est une ecriture ouverte",
              not any(c.startswith("/api/library/") or c.endswith("/fav") for c in ouvertes), str(ouvertes))

    await storage._engine.dispose() if hasattr(storage, "_engine") else None


asyncio.run(main())
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
