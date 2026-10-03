# -*- coding: utf-8 -*-
"""Bibliotheque, tache #81 PR A (plan-library T9-T10, 03/10/2026) — la CORBEILLE, cote serveur.
DECISIONS DE L'UTILISATEUR (03/10) : jeter une image, un son ou un rendu l'envoie dans assets/_corbeille (plus
d'effacement) ; restauration depuis l'onglet Corbeille ; « Vider » MANUEL ; plus de 30 jours = PROPOSE a la purge,
jamais purge seul ; la corbeille ne part pas au transfert (lot « rebuts »).
Ce que le plan faisait faux, et que ce banc garde : son journal perdait les PROJETS et les fichiers COMPAGNONS (recette),
il n'avait ni route pour LISTER la corbeille, ni retention, ni purge, ni regle de conflit de nom ; la suppression d'un
son ne retirait ni la ligne d'index ni les projets ; le sidecar _sfx_meta.json etait indexe comme un son.
Banc-miroir : on lit le DISQUE, la BASE (sqlite3) et le JSON servi.
Temoin positif : la base (a4e81787) efface (unlink) et n'a pas de corbeille.
Run (depuis backend/) : & $PY tests/test_library_corbeille.py"""
import asyncio, io, json, os, pathlib, shutil, sqlite3, subprocess, sys, tempfile
from datetime import datetime, timedelta, timezone
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcorb_"))
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


IMG, AUD = _tmp / "images", _tmp / "audio"
def png(nom, couleur=(200, 40, 40)):
    buf = io.BytesIO(); Image.new("RGB", (16, 16), couleur).save(buf, format="PNG"); (IMG / nom).write_bytes(buf.getvalue())


def base(sql, *a):
    con = sqlite3.connect(BASE_DB)
    try:
        r = con.execute(sql, a).fetchall(); con.commit(); return r
    finally:
        con.close()


BASE = "a4e81787"
r_ro = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE)).stdout
r_lc = subprocess.run(["git", "show", f"{BASE}:backend/app/services/library_corbeille.py"], capture_output=True, cwd=str(RACINE))
check("T0 temoin : la base EFFACE (p.unlink() dans DELETE /images) et n'a pas de corbeille", r_lc.returncode != 0
      and b"    p.unlink()\n    await LI.retirer(safe)" in r_ro.replace(b"\r\n", b"\n") and b'"/library/corbeille"' not in r_ro)


async def main():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services import storage
    from app.services import library_index as LI
    from app.services import library_corbeille as LC
    from app.services import sfx_service as SFX
    from app.services import transfert as TR
    from app.config import settings
    await storage.init_db()
    CORB = LC.dossier()
    tr = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=tr, base_url="http://127.0.0.1") as cl:
        print("[I] une image")
        png("x.png"); octets = (IMG / "x.png").read_bytes()
        await LI.noter(["x.png"], "generation", parent="mere.png", relation="crop", recette={"prompt": "un phare"})
        await LI.editer("x.png", {"tags": ["mer"], "fav": True, "note": 4, "licence": "CC BY"})
        (IMG / "x.png.recette.json").write_text('{"template_id": "t"}', encoding="utf-8")
        rd = settings.outputs_path / "_sync" / "recettes"; rd.mkdir(parents=True, exist_ok=True); (rd / "x.png.json").write_text('{"a": 1}', encoding="utf-8")
        async with storage.async_session_factory() as s:
            s.add(storage.LibraryProject(id="pj", nom="Campagne")); s.add(storage.LibraryProjectItem(project_id="pj", ref="x.png", kind="image")); await s.commit()
        r = await cl.delete("/api/images/x.png")
        eid = r.json().get("corbeille")
        entree = CORB / str(eid)
        check("I1 DELETE /images range a la CORBEILLE : le fichier quitte la Bibliotheque mais existe dans _corbeille/<id>/ (memes octets) ; index et projet retires",
              r.status_code == 200 and eid and not (IMG / "x.png").exists() and (entree / "f" / "x.png").read_bytes() == octets
              and base("SELECT COUNT(*) FROM library_assets WHERE filename='x.png'") == [(0,)]
              and base("SELECT COUNT(*) FROM library_project_items WHERE ref='x.png'") == [(0,)], r.text)
        j = json.loads((entree / "journal.json").read_text(encoding="utf-8"))
        check("I2 le JOURNAL garde la ligne d'index ENTIERE (tags, favori, note, licence, lignee, recette), le PROJET et les COMPAGNONS (recettes) deplaces",
              j["index"]["tags"] == '["mer"]' and j["index"]["fav"] == 1 and j["index"]["note"] == 4 and j["index"]["licence"] == "CC BY"
              and j["index"]["parent_filename"] == "mere.png" and "un phare" in j["index"]["recette"] and j["projets"] == [{"project_id": "pj", "kind": "image"}]
              and not (IMG / "x.png.recette.json").exists() and not (rd / "x.png.json").exists() and len(j["compagnons"]) == 2, json.dumps(j)[:400])
        g = (await cl.get("/api/library/corbeille")).json()
        check("I3 GET /library/corbeille la LISTE (type, nom, poids, date, ni ancienne ni illisible) ; poids total ; 30 jours dits",
              g["elements"][0]["id"] == eid and g["elements"][0]["type"] == "image" and g["elements"][0]["nom"] == "x.png" and g["elements"][0]["restaurable"]
              and g["elements"][0]["ancien"] is False and g["octets"] > len(octets) - 1 and g["jours"] == 30 and g["anciens"] == 0, json.dumps(g)[:300])
        r = await cl.post("/api/library/corbeille/restaurer", json={"id": eid})
        check("I4 RESTAURER remet tout : fichier, ligne d'index (tags, favori, note, licence, lignee, recette), projet, compagnons ; l'entree disparait",
              r.status_code == 200 and r.json() == {"restaure": "x.png", "type": "image", "renomme": False} and (IMG / "x.png").read_bytes() == octets
              and base("SELECT tags, fav, note, licence, parent_filename, relation FROM library_assets WHERE filename='x.png'") == [('["mer"]', 1, 4, "CC BY", "mere.png", "crop")]
              and base("SELECT project_id FROM library_project_items WHERE ref='x.png'") == [("pj",)] and (IMG / "x.png.recette.json").exists()
              and (rd / "x.png.json").exists() and not entree.exists(), r.text)

        async with storage.async_session_factory() as s:
            s.add(storage.LibraryProject(id="pj2", nom="Ephemere")); s.add(storage.LibraryProjectItem(project_id="pj2", ref="x.png", kind="image")); await s.commit()
        e3 = (await cl.delete("/api/images/x.png")).json()["corbeille"]
        base("DELETE FROM library_projects WHERE id='pj2'")
        await cl.post("/api/library/corbeille/restaurer", json={"id": e3})
        check("I5 un projet SUPPRIME pendant que l'image etait en corbeille n'est pas recree en fantome (les autres projets reviennent)",
              sorted(base("SELECT project_id FROM library_project_items WHERE ref='x.png'")) == [("pj",)], str(base("SELECT project_id FROM library_project_items WHERE ref='x.png'")))

        print("[C] un nom repris entre-temps")
        e2 = (await cl.delete("/api/images/x.png")).json()["corbeille"]
        png("x.png", (0, 0, 255)); neuf = (IMG / "x.png").read_bytes(); await LI.noter(["x.png"], "import")
        r = (await cl.post("/api/library/corbeille/restaurer", json={"id": e2})).json()
        check("C1 l'image revient sous un nom VOISIN (x_restaure.png) et le DIT ; la nouvelle x.png est intacte ; ses compagnons suivent le nouveau nom ; sa ligne garde ses tags",
              r == {"restaure": "x_restaure.png", "type": "image", "renomme": True} and (IMG / "x.png").read_bytes() == neuf
              and (IMG / "x_restaure.png").read_bytes() == octets and (IMG / "x_restaure.png.recette.json").exists() and (rd / "x_restaure.png.json").exists()
              and base("SELECT tags FROM library_assets WHERE filename='x_restaure.png'") == [('["mer"]',)]
              and base("SELECT licence FROM library_assets WHERE filename='x.png'") == [("inconnue",)], str(r))

        print("[A] un son")
        (AUD / "s.mp3").write_bytes(b"ID3son"); SFX.record_meta("s.mp3", {"kind": "sfx", "prompt": "vague"})
        await LI.noter(["s.mp3"], "inconnu", kind="audio")
        async with storage.async_session_factory() as s:
            s.add(storage.LibraryProjectItem(project_id="pj", ref="s.mp3", kind="audio")); await s.commit()
        r = await cl.delete("/api/audio/s.mp3"); ea = r.json().get("corbeille")
        check("A1 DELETE /audio range le son a la corbeille ET retire sa ligne d'index, son projet et son entree du sidecar (la suppression d'avant les laissait)",
              r.status_code == 200 and not (AUD / "s.mp3").exists() and base("SELECT COUNT(*) FROM library_assets WHERE filename='s.mp3'") == [(0,)]
              and base("SELECT COUNT(*) FROM library_project_items WHERE ref='s.mp3'") == [(0,)] and "s.mp3" not in SFX.load_meta(), r.text)
        r = await cl.post("/api/library/corbeille/restaurer", json={"id": ea})
        check("A2 restaurer un son : fichier, index (kind audio), projet et entree du sidecar reviennent",
              r.status_code == 200 and (AUD / "s.mp3").read_bytes() == b"ID3son" and base("SELECT kind FROM library_assets WHERE filename='s.mp3'") == [("audio",)]
              and base("SELECT project_id FROM library_project_items WHERE ref='s.mp3'") == [("pj",)] and SFX.load_meta().get("s.mp3", {}).get("prompt") == "vague", r.text)

        print("[R] un rendu")
        out = settings.outputs_path; (out / "rendu_j.mp4").write_bytes(b"MP4" * 10)
        sp = out / "sprites" / "jobspr12"; sp.mkdir(parents=True); (sp / "sheet.png").write_bytes(b"PNG")
        async with storage.async_session_factory() as s:
            s.add(storage.JobRecord(id="jobspr12-aaaa", status="done", progress=100, image_filename="z", title="Mon rendu",
                                    provider="sprite2d", final_video_path=str(out / "rendu_j.mp4")))
            s.add(storage.LibraryProjectItem(project_id="pj", ref="jobspr12-aaaa", kind="render")); await s.commit()
        r = await cl.delete("/api/jobs/jobspr12-aaaa"); er = r.json().get("corbeille")
        check("R1 DELETE /jobs range le RENDU a la corbeille : video et dossier de sortie deplaces, ligne du job et projet retires",
              r.status_code == 200 and er and not (out / "rendu_j.mp4").exists() and not sp.exists()
              and base("SELECT COUNT(*) FROM jobs WHERE id='jobspr12-aaaa'") == [(0,)] and base("SELECT COUNT(*) FROM library_project_items WHERE ref='jobspr12-aaaa'") == [(0,)], r.text)
        r = await cl.post("/api/library/corbeille/restaurer", json={"id": er})
        check("R2 restaurer un rendu : la ligne du job (titre, statut, chemins) revient, ses fichiers aussi, et son projet",
              r.status_code == 200 and base("SELECT title, status, provider FROM jobs WHERE id='jobspr12-aaaa'") == [("Mon rendu", "done", "sprite2d")]
              and (out / "rendu_j.mp4").read_bytes() == b"MP4" * 10 and (sp / "sheet.png").exists()
              and base("SELECT kind FROM library_project_items WHERE ref='jobspr12-aaaa'") == [("render",)], r.text)
        er2 = (await cl.delete("/api/jobs/jobspr12-aaaa")).json()["corbeille"]
        async with storage.async_session_factory() as s:
            s.add(storage.JobRecord(id="jobspr12-aaaa", status="done", progress=100, image_filename="z")); await s.commit()
        r409 = await cl.post("/api/library/corbeille/restaurer", json={"id": er2})
        check("R3 un rendu dont l'identifiant a ete repris : 409, rien n'est ecrase, l'entree reste", r409.status_code == 409 and (CORB / er2).is_dir(), r409.text)
        r404 = await cl.delete("/api/jobs/inconnu")
        check("R4 un rendu inconnu : 404, rien en corbeille", r404.status_code == 404)

        print("[V] vider, anciens, refus")
        jj = json.loads((CORB / er2 / "journal.json").read_text(encoding="utf-8"))
        jj["jete_le"] = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat(timespec="seconds")
        (CORB / er2 / "journal.json").write_text(json.dumps(jj), encoding="utf-8")
        await LI.reconcilier()
        g = (await cl.get("/api/library/corbeille")).json()
        vieux = [e for e in g["elements"] if e["id"] == er2]
        check("V1 jete il y a 40 jours : marque ANCIEN (propose a la purge) mais TOUJOURS la — rien n'est purge seul (ni a la lecture, ni au demarrage)",
              vieux and vieux[0]["ancien"] is True and vieux[0]["jours"] >= 40 and g["anciens"] == 1 and (CORB / er2).is_dir(), json.dumps(g)[:300])
        png("y.png"); ey = (await cl.delete("/api/images/y.png")).json()["corbeille"]
        r = await cl.post("/api/library/corbeille/vider", json={"ids": [er2]})
        check("V2 vider PAR id efface definitivement cette entree seule (nombre et octets rendus)", r.json()["vides"] == 1 and r.json()["octets"] > 0
              and not (CORB / er2).exists() and (CORB / ey).is_dir(), r.text)
        r = await cl.post("/api/library/corbeille/vider", json={"tout": True})
        check("V3 vider TOUT", r.json()["vides"] >= 1 and not any(CORB.iterdir()), r.text)
        b1, b2, b3 = await cl.post("/api/library/corbeille/vider", json={}), await cl.post("/api/library/corbeille/vider", json={"ids": []}), await cl.post("/api/library/corbeille/vider", json={"tout": "oui"})
        r4, r5 = await cl.post("/api/library/corbeille/restaurer", json={"id": "absent"}), await cl.post("/api/library/corbeille/restaurer", json={"id": "../x"})
        r6 = await cl.post("/api/library/corbeille/vider", json={"ids": ["../images"]})   # un dossier qui EXISTE a cote
        check("V4 refus : vider sans cible (400), restaurer une entree absente (404) ou un id qui n'est pas un nom (400) ; un id qui remonte ne vide RIEN hors de la corbeille",
              (b1.status_code, b2.status_code, b3.status_code, r4.status_code, r5.status_code) == (400, 400, 400, 404, 400)
              and r6.json()["vides"] == 0 and (IMG / "x.png").exists() and IMG.is_dir(), f"{b1.status_code} {b2.status_code} {b3.status_code} {r4.status_code} {r5.status_code} {r6.text}")

        print("[E] un echec en cours de route")
        png("z.png"); await LI.noter(["z.png"], "generation"); (IMG / "z.png.recette.json").write_text("{}", encoding="utf-8")
        vrai, n = shutil.move, {"i": 0}
        def casse(a, b):
            n["i"] += 1
            if n["i"] == 2:
                raise OSError("disque plein (simule)")
            return vrai(a, b)
        shutil.move = casse
        try:
            rz = await cl.delete("/api/images/z.png")
        finally:
            shutil.move = vrai
        check("E1 si un deplacement echoue, ce qui etait parti REVIENT, l'entree n'existe pas, l'index est intact (erreur 500 dite)",
              rz.status_code == 500 and (IMG / "z.png").exists() and (IMG / "z.png.recette.json").exists() and not any(CORB.iterdir())
              and base("SELECT COUNT(*) FROM library_assets WHERE filename='z.png'") == [(1,)], f"{rz.status_code} {list(CORB.iterdir())}")

        print("[S] le transfert et le sidecar des sons")
        check("S1 la corbeille ne part PAS au transfert par defaut ; elle part si l'on coche le lot « rebuts »",
              TR.exclu("assets/_corbeille/2026_x/journal.json") == (True, "jetable") and TR.exclu("assets/_corbeille/2026_x/journal.json", {"rebuts": True}) == (False, "")
              and TR.lot_de("assets/_corbeille/a/f/x.png") == "rebuts")
        SFX.record_meta("t.mp3", {"kind": "sfx"})
        base("INSERT INTO library_assets (filename, source, kind, origin, created) VALUES ('_sfx_meta.json','inconnu','audio','heuristique','2026-10-01')")
        (AUD / "notes.json").write_text("{}", encoding="utf-8"); (AUD / "vague.mp3.part").write_bytes(b"x")
        await LI.reconcilier()
        check("S2b ni un .json ni un .part du dossier des sons n'est indexe comme un son",
              base("SELECT COUNT(*) FROM library_assets WHERE filename IN ('notes.json','vague.mp3.part')") == [(0,)])
        check("S2 le sidecar _sfx_meta.json n'est plus un « son » : sa ligne est retiree et le reconcilier ne la recree pas",
              base("SELECT COUNT(*) FROM library_assets WHERE filename='_sfx_meta.json'") == [(0,)] and (AUD / "_sfx_meta.json").exists())


asyncio.run(main())
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
