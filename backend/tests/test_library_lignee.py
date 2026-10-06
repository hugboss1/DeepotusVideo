# -*- coding: utf-8 -*-
"""Bibliotheque, tache #79 PR A (plan-library T5, 03/10/2026) — la LIGNEE (mere / relation), cote serveur.
DECISIONS DE L'UTILISATEUR (03/10) : ecrivent leur mere la retouche (8 operations, relation = l'operation), la
finition (upscale / upscale_ai), les vues 3D (mere = l'image source lue AU MANIFESTE du job ; shot_0 = copie) et la
planche de sprite (mere = la VIDEO d'un rendu, seule source qui soit dans la Bibliotheque ; upload / fichier : rien) ;
les 17 autres producteurs plus tard.
Ce que le plan faisait faux, et que ce banc garde : « 14 sites » (21) ; /assets/3d et /assets/sprite « ont
body["image_filename"] » (la sauvegarde n'a PAS de corps ; un sprite nait d'une video) ; la colonne, la migration,
editer et carte() etaient DEJA la (#77).
Banc-miroir : on lit la BASE (sqlite3) et le JSON SERVI.
Temoin positif : la base (341572f8) n'a ni noter(parent, relation) ni la route de lignee.
Run (depuis backend/) : & $PY tests/test_library_lignee.py"""
import asyncio, io, json, os, pathlib, sqlite3, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzlignee_"))
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


def png(chemin, w=64, h=64, couleur=(10, 200, 30)):
    chemin = pathlib.Path(chemin); chemin.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO(); Image.new("RGB", (w, h), couleur).save(buf, format="PNG")
    chemin.write_bytes(buf.getvalue())


def base(sql, *a):
    con = sqlite3.connect(BASE_DB)
    try:
        return con.execute(sql, a).fetchall()
    finally:
        con.close()


def mere(nom):
    r = base("SELECT parent_filename, relation FROM library_assets WHERE filename=?", nom)
    return r[0] if r else None


BASE = "341572f8"
r_li = subprocess.run(["git", "show", f"{BASE}:backend/app/services/library_index.py"], capture_output=True, cwd=str(RACINE)).stdout
r_ro = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE)).stdout
check("T0 temoin : la base n'a ni noter(parent, relation) ni la route de lignee (mais DEJA les colonnes : #77)",
      b"relation: str | None = None" not in r_li and b'"/library/lignee/{filename}"' not in r_ro and b"parent_filename" in r_li and len(r_ro) > 100000)

IMG = _tmp / "images"


async def main():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services import storage
    from app.services import library_index as LI
    from app.api import routes as RT
    from app.config import settings
    await storage.init_db()

    print("[N] noter apprend la mere")
    png(IMG / "n_mere.png"); png(IMG / "n_fille.png")
    await LI.noter(["sous/dossier/n_fille.png"], "retouche", parent="ailleurs/n_mere.png", relation="x" * 40)
    check("N1 la mere est ecrite par son NOM (sans chemin), la relation bornee a 24", mere("n_fille.png") == ("n_mere.png", "x" * 24), str(mere("n_fille.png")))
    await LI.noter(["n_fille.png"], "retouche")
    check("N2 un appelant qui ne donne PAS la mere ne l'efface pas (les 17 autres sites restent tels quels)", mere("n_fille.png") == ("n_mere.png", "x" * 24))
    await LI.noter(["n_mere.png"], "retouche", parent="n_mere.png", relation="crop")
    check("N3 une image n'est pas sa propre mere (reecriture en place) ; une relation vide devient NULL",
          mere("n_mere.png") == (None, "crop") and (await LI.noter(["n_mere.png"], "retouche", relation="")) is None and mere("n_mere.png") == (None, None))

    tr = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=tr, base_url="http://127.0.0.1") as cl:
        print("[P] les producteurs")
        png(IMG / "gen_mere.png", 90, 160)
        r = await cl.post("/api/images/process", json={"op": "crop", "filename": "gen_mere.png", "ratio": "1:1"})
        fille = (r.json().get("images") or [None])[0] if r.status_code == 200 else None
        check("P1 RETOUCHE : la fille d'un recadrage a pour mere le fichier retouche et pour relation l'operation",
              fille is not None and mere(fille) == ("gen_mere.png", "crop"), f"{r.status_code} {r.text[:200]} {fille and mere(fille)}")
        r = await cl.post("/api/finition/upscale-measure", json={"filename": "gen_mere.png", "scale": 2})
        noms = [v.get("filename") or v.get("image") or v.get("nom") for v in (r.json().get("variantes") or [])] if r.status_code == 200 else []
        loc = [n for n in base("SELECT filename FROM library_assets WHERE relation='upscale' AND parent_filename='gen_mere.png'")]
        check("P2 FINITION locale : la variante agrandie a pour mere la source, relation « upscale »", r.status_code == 200 and len(loc) >= 1, f"{r.status_code} {r.text[:200]}")
        # la variante PAYANTE, sans appel : le coeur est remplace le temps d'un appel, cle factice
        vrai, cle = RT._process_image_core, settings.FAL_KEY
        async def faux(body):
            if body.get("mode") == "ai":
                png(IMG / "up_ai_faux.png", 180, 320); return {"images": ["up_ai_faux.png"]}
            return await vrai(body)
        RT._process_image_core, settings.FAL_KEY = faux, "cle-factice-du-banc"
        try:
            r = await cl.post("/api/finition/upscale-measure", json={"filename": "gen_mere.png", "scale": 2, "ai": True, "confirm": True})
        finally:
            RT._process_image_core, settings.FAL_KEY = vrai, cle
        check("P3 FINITION payante (coeur simule, aucun appel) : relation « upscale_ai »", mere("up_ai_faux.png") == ("gen_mere.png", "upscale_ai"), f"{r.status_code} {r.text[:200]} {mere('up_ai_faux.png')}")

        J = settings.outputs_path / "assets3d" / "job3d"
        png(J / "shot_0.png"); png(J / "shot_1.png")
        (J / "asset.json").write_text(json.dumps({"image_filename": "gen_mere.png", "version": 1}), encoding="utf-8")
        r0 = await cl.post("/api/assets/3d/job3d/shot/0/save"); r1 = await cl.post("/api/assets/3d/job3d/shot/1/save")
        K = settings.outputs_path / "assets3d" / "jobvieux"; png(K / "shot_1.png")
        r2 = await cl.post("/api/assets/3d/jobvieux/shot/1/save")
        check("P4 VUES 3D : la mere est l'image source LUE AU MANIFESTE ; shot_0 est une « copie », les autres des « vue_3d » ; un job sans manifeste : pas de mere",
              mere(r0.json()["filename"]) == ("gen_mere.png", "copie") and mere(r1.json()["filename"]) == ("gen_mere.png", "vue_3d")
              and mere(r2.json()["filename"]) == (None, None), f"{r0.text} {r1.text} {r2.text}")

        S = settings.outputs_path / "sprites"
        png(S / "spjob" / "sheet.png"); (S / "spjob" / "manifest.json").write_text(json.dumps({"source": {"kind": "job", "file": "rendu_final.mp4"}}), encoding="utf-8")
        png(S / "spup" / "sheet.png"); (S / "spup" / "manifest.json").write_text(json.dumps({"source": {"kind": "upload", "file": "x.mp4"}}), encoding="utf-8")
        png(S / "spnu" / "sheet.png")
        a, b_, c = (await cl.post("/api/assets/sprite/spjob/save")).json()["filename"], (await cl.post("/api/assets/sprite/spup/save")).json()["filename"], (await cl.post("/api/assets/sprite/spnu/save")).json()["filename"]
        check("P5 SPRITE : la mere est la VIDEO d'un rendu (source « job ») ; un upload ou un sprite sans manifeste n'en a pas",
              mere(a) == ("rendu_final.mp4", "sprite") and mere(b_) == (None, None) and mere(c) == (None, None), f"{mere(a)} {mere(b_)} {mere(c)}")

        print("[L] la route de lignee")
        for n in ("la.png", "lb.png", "lc.png", "ld.png", "le.png"):
            png(IMG / n)
        await LI.noter(["la.png"], "generation")
        await LI.noter(["lb.png"], "retouche", parent="la.png", relation="crop")
        await LI.noter(["lc.png"], "retouche", parent="lb.png", relation="upscale")
        await LI.noter(["ld.png"], "retouche", parent="lb.png", relation="remove-bg")
        await LI.noter(["le.png"], "retouche", parent="ld.png", relation="edit")
        gc, gb = (await cl.get("/api/library/lignee/lc.png")).json(), (await cl.get("/api/library/lignee/lb.png")).json()
        check("L1 on REMONTE a la racine ; la mere directe est rendue avec sa relation ; une feuille n'a pas de filles",
              gc["racine"] == "la.png" and gc["mere"]["filename"] == "lb.png" and gc["noeud"]["relation"] == "upscale" and gc["filles"] == [] and gc["cycle"] is False, json.dumps(gc)[:300])
        check("L2 les filles DIRECTES (pas les petites-filles) ; l'arbre entier sous la racine, en largeur",
              [f["filename"] for f in gb["filles"]] == ["lc.png", "ld.png"] and [e["filename"] for e in gb["enfants"]] == ["lb.png", "lc.png", "ld.png", "le.png"]
              and [e["relation"] for e in gb["enfants"]] == ["crop", "upscale", "remove-bg", "edit"], json.dumps(gb)[:400])
        ga = (await cl.get("/api/library/lignee/la.png")).json()
        check("L3 la racine n'a pas de mere ; une image jamais indexee mais au magasin repond aussi (sans mere)",
              ga["mere"] is None and ga["racine"] == "la.png" and (await cl.get("/api/library/lignee/n_fille.png")).status_code == 200
              and (png(IMG / "jamais.png") or (await cl.get("/api/library/lignee/jamais.png")).json()["mere"] is None))

        for n in ("ca.png", "cb.png"):
            png(IMG / n)
        await LI.editer("ca.png", {"parent_filename": "cb.png", "relation": "edit"})
        await LI.editer("cb.png", {"parent_filename": "ca.png", "relation": "edit"})
        rc = await asyncio.wait_for(cl.get("/api/library/lignee/ca.png"), 20)
        check("L4 une BOUCLE (deux editions croisees par PATCH) ne pend pas : 200 et `cycle: true`", rc.status_code == 200 and rc.json()["cycle"] is True, rc.text[:200])
        noms = [f"ch{i:02d}.png" for i in range(40)]
        for i, n in enumerate(noms):
            png(IMG / n); await LI.noter([n], "retouche", parent=noms[i - 1] if i else None, relation="crop" if i else None)
        gl = (await cl.get("/api/library/lignee/ch39.png")).json()
        check("L5 la remontee est BORNEE a 32 pas (une chaine de 40 s'arrete a ch07), sans pretendre a un cycle",
              gl["racine"] == "ch07.png" and gl["cycle"] is False, gl["racine"])
        LI.LIGNEE_MAX, garde = 3, LI.LIGNEE_MAX
        try:
            gt = (await cl.get("/api/library/lignee/ch00.png")).json()
        finally:
            LI.LIGNEE_MAX = garde
        check("L6 la descente est BORNEE et le DIT (`tronque`)", len(gt["enfants"]) == 3 and gt["tronque"] is True and (await cl.get("/api/library/lignee/ch00.png")).json()["tronque"] is False)

        async with storage.async_session_factory() as s:
            s.add(storage.JobRecord(id="job-rendu-1", status="done", progress=100, image_filename="x", final_video_path=str(settings.outputs_path / "rendu_final.mp4")))
            await s.commit()
        gs = (await cl.get(f"/api/library/lignee/{a}")).json()
        check("L7 la mere HORS index (la video d'un rendu) est rendue « externe » avec le job qui l'a produite",
              gs["mere"] == {"filename": "rendu_final.mp4", "externe": True, "job_id": "job-rendu-1"} and gs["racine"] == a, json.dumps(gs["mere"]))
        r404, r400 = await cl.get("/api/library/lignee/absent.png"), await cl.get("/api/library/lignee/x%5Cy.png")
        check("L8 404 pour un fichier ni au magasin ni indexe ; 400 pour un nom qui n'est pas un nom", r404.status_code == 404 and r400.status_code == 400, f"{r404.status_code} {r400.status_code}")

    # Les producteurs AJOUTÉS depuis la base, chacun nommé : le compte figé à 19 rougissait sur main depuis T098
    # (from-photo) sans dire lequel ; un site de plus non listé ici rougit encore, un site retiré aussi.
    AJOUTS = {
        "T098 /materials/from-photo": '"matieres")',
        "T100 /audio/enhance + /audio/isolate": '"sonvfx", kind="audio", parent=r["parent"], relation=r["relation"])',
    }
    texte = (RACINE / "backend/app/api/routes.py").read_text(encoding="utf-8")
    sites = texte.count("LI.noter(")
    attendus = r_ro.decode("utf-8").count("LI.noter(") + 1 + 2
    check(f"I1 producteurs dans routes.py : les 19 de la base + ceux de {', '.join(AJOUTS)} = {attendus}",
          r_ro.decode("utf-8").count("LI.noter(") == 19 and sites == attendus
          and all(m in texte for m in AJOUTS.values()), str(sites))


asyncio.run(main())
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
