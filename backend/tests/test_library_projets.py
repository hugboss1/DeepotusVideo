# -*- coding: utf-8 -*-
"""Bibliotheque, tache #78 PR A (plan-library T3, 03/10/2026) — les PROJETS de toutes categories, cote serveur.
DECISIONS DE L'UTILISATEUR (03/10) : UN seul projet — celui de la Bibliotheque porte une case « epingle sur le
telephone » ; le manifeste mobile lit la table ; les epingles de projets.json (#58, qui se disait pense-bete de CE
chantier) sont reprises une fois et le fichier garde. Le projet ACTIF range TOUT : fichiers (images, sons) ET rendus,
3D, sprites termines pendant qu'il est actif.
Ce que le plan faisait faux, et que ce banc garde : renommer ou supprimer un fichier laissait une appartenance
orpheline ; le hook de LI.noter ne voyait aucun job (rendus, 3D, sprites) ; un pid inconnu posable comme projet actif.
Banc-miroir : la BASE (sqlite3) et le JSON SERVI. Temoin positif : la base (0f965627) n'a ni le service ni les routes.
Run (depuis backend/) : & $PY tests/test_library_projets.py"""
import asyncio, io, json, os, pathlib, sqlite3, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzlibproj_"))
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


def png(nom):
    buf = io.BytesIO(); Image.new("RGB", (8, 8), (20, 90, 200)).save(buf, format="PNG")
    (_tmp / "images" / nom).write_bytes(buf.getvalue())


def base(sql, *a):
    con = sqlite3.connect(BASE_DB)
    try:
        return con.execute(sql, a).fetchall()
    finally:
        con.close()


def items(pid):
    return sorted(base("SELECT ref, kind FROM library_project_items WHERE project_id=?", pid))


BASE = "0f965627"
r_ro = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE)).stdout
r_lp = subprocess.run(["git", "show", f"{BASE}:backend/app/services/library_projects.py"], capture_output=True, cwd=str(RACINE))
check("T0 temoin : la base n'a ni le service ni les routes des projets", r_lp.returncode != 0 and len(r_ro) > 100000
      and b'"/library/projets"' not in r_ro)

# Les epingles du telephone d'AVANT (#58) : un projets.json a reprendre une fois.
(_tmp / "outputs" / "_sync").mkdir(parents=True, exist_ok=True)
(_tmp / "outputs" / "_sync" / "projets.json").write_text(json.dumps({"campagne-septembre": ["gen_s1.png", "gen_s2.png"]}),
                                                          "utf-8")


async def main():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services import storage
    from app.services import library_index as LI
    await storage.init_db()
    try:
        from app.services import library_projects as LP
    except ImportError as e:
        check("T1 le service existe", False, str(e)); return
    from app.services.storage import JobRecord, async_session_factory

    async def job(jid, provider="seedance", status="queued"):
        async with async_session_factory() as s:
            s.add(JobRecord(id=jid, status=status, progress=0, provider=provider, title=jid, image_filename="x.png"))
            await s.commit()

    async def statut(jid, st):
        async with async_session_factory() as s:
            j = await s.get(JobRecord, jid); j.status = st; await s.commit()

    async def calme():
        for _ in range(20):
            await asyncio.sleep(0.02)

    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t") as cl:
        print("[P] les projets")
        tables = {r[0] for r in base("SELECT name FROM sqlite_master WHERE type='table'")}
        check("P0 deux tables neuves : library_projects et library_project_items", {"library_projects", "library_project_items"} <= tables)
        r = await cl.post("/api/library/projets", json={"nom": "  Campagne   Abysses "})
        p = r.json()
        check("P1 creer : 200, id proj_…, nom nettoye, ni epingle ni couleur par defaut", r.status_code == 200
              and str(p.get("id", "")).startswith("proj_") and p.get("nom") == "Campagne Abysses" and p.get("epingle") is False, r.text)
        check("P2 nom vide : 400 avec le message", (await cl.post("/api/library/projets", json={"nom": "   "})).status_code == 400)
        png("gen_a.png"); png("gen_b.png")
        r = await cl.post(f"/api/library/projets/{p['id']}/items", json={"items": [
            {"ref": "gen_a.png", "kind": "image"}, {"ref": "job-1234", "kind": "render"}, {"ref": "", "kind": "image"}]})
        check("P3 un projet traverse les categories : image + rendu, le vide ignore ; en base", r.status_code == 200
              and r.json().get("ajoutes") == 2 and items(p["id"]) == [("gen_a.png", "image"), ("job-1234", "render")], r.text)
        r = await cl.post(f"/api/library/projets/{p['id']}/items", json={"items": [{"ref": "gen_a.png", "kind": "image"}]})
        check("P4 idempotent : re-poser un item vaut 0 (unicite tenue par la base)", r.status_code == 200 and r.json().get("ajoutes") == 0,
              f"{r.status_code} {r.text[:120]}")
        bad = (await cl.post(f"/api/library/projets/{p['id']}/items", json={"items": [{"ref": "x", "kind": "pdf"}]})).status_code
        check("P5 un kind inconnu est refuse (400) : seuls image, audio, render, asset3d, sprite2d", bad == 400, str(bad))
        p2 = (await cl.post("/api/library/projets", json={"nom": "Deck Oracle"})).json()
        await cl.post(f"/api/library/projets/{p2['id']}/items", json={"items": [{"ref": "gen_a.png", "kind": "image"}]})
        ou = (await cl.get("/api/library/projets?ref=gen_a.png")).json().get("projets", [])
        tous = (await cl.get("/api/library/projets")).json().get("projets", [])
        check("P6 un asset dans N projets (?ref=) ; la liste porte le nombre d'items de chacun",
              sorted(x["nom"] for x in ou) == ["Campagne Abysses", "Deck Oracle"]
              and {x["nom"]: x["n"] for x in tous}.get("Campagne Abysses") == 2, f"{ou} {tous}")
        d = (await cl.get(f"/api/library/projets/{p['id']}")).json()
        check("P7 le contenu d'un projet rend ses items (ref, kind)", sorted((i["ref"], i["kind"]) for i in d.get("items", []))
              == [("gen_a.png", "image"), ("job-1234", "render")], str(d))
        r = await cl.request("DELETE", f"/api/library/projets/{p2['id']}/items", json={"refs": ["gen_a.png"]})
        check("P8 retirer un item", r.status_code == 200 and r.json().get("retires") == 1 and items(p2["id"]) == [])
        check("P9 projet inconnu : 404 (lecture, ajout)", (await cl.get("/api/library/projets/proj_nope")).status_code == 404
              and (await cl.post("/api/library/projets/proj_nope/items", json={"items": []})).status_code == 404)
        r = await cl.patch(f"/api/library/projets/{p2['id']}", json={"nom": "Deck Oracle II", "couleur": "#a0c4ff", "epingle": True})
        check("P10 renommer, colorer, epingler un projet (PATCH, etat relu)", r.status_code == 200
              and r.json().get("nom") == "Deck Oracle II" and r.json().get("epingle") is True and r.json().get("couleur") == "#a0c4ff", r.text)
        bads = [(c, (await cl.patch(f"/api/library/projets/{p2['id']}", json=c)).status_code)
                for c in ({"couleur": "rouge"}, {"epingle": "oui"}, {"nom": " "}, {})]
        check("P11 400 : couleur non #rrggbb, epingle non booleen, nom vide, corps sans champ", all(s == 400 for _, s in bads), str(bads))

        print("\n[A] le projet actif range TOUT")
        r = await cl.put("/api/library/projets/actif", json={"id": "proj_nope"})
        check("A1 poser un projet INCONNU comme actif : 404, rien ne change", r.status_code == 404
              and (await cl.get("/api/library/projets/actif")).json().get("id") == "")
        await cl.put("/api/library/projets/actif", json={"id": p["id"]})
        a = (await cl.get("/api/library/projets/actif")).json()
        check("A2 l'actif se lit (id et nom)", a.get("id") == p["id"] and a.get("nom") == "Campagne Abysses", str(a))
        png("gen_z.png"); await LI.noter(["gen_z.png"], "generation")
        (_tmp / "audio" / "voix.mp3").write_bytes(b"ID3"); await LI.noter(["voix.mp3"], "import", kind="audio")
        check("A3 un fichier produit pendant que le projet est actif y entre (image, son), par le seul site LI.noter",
              ("gen_z.png", "image") in items(p["id"]) and ("voix.mp3", "audio") in items(p["id"]), str(items(p["id"])))
        await job("job-render"); await job("job-3d", "asset3d"); await job("job-sprite", "sprite2d")
        await job("job-proxy", "montage_proxy"); await job("job-rate")
        for j in ("job-render", "job-3d", "job-sprite", "job-proxy"):
            await statut(j, "done")
        await statut("job-rate", "failed")
        await job("job-upload", "ugc", status="done")
        await calme()
        it = items(p["id"])
        check("A4 un rendu, une 3D, un sprite TERMINES y entrent avec le kind de l'ecran ; un job cree deja termine aussi",
              {("job-render", "render"), ("job-3d", "asset3d"), ("job-sprite", "sprite2d"), ("job-upload", "render")} <= set(it), str(it))
        check("A5 ... mais ni un precalcul du Montage (montage_proxy) ni un job rate",
              not any(r_ in ("job-proxy", "job-rate") for r_, _k in it), str(it))
        await cl.request("DELETE", f"/api/library/projets/{p['id']}/items", json={"refs": ["job-render"]})
        n0 = len(items(p["id"]))
        async with async_session_factory() as s_:
            j_ = await s_.get(JobRecord, "job-render"); j_.status = "done"; j_.progress = 100; await s_.commit()
        await calme()
        check("A6 un job DEJA termine qu'on re-ecrit (« done » encore) ne revient pas dans un projet d'ou on l'a retire",
              len(items(p["id"])) == n0 and not any(r_ == "job-render" for r_, _k in items(p["id"])), str(items(p["id"])))
        await cl.put("/api/library/projets/actif", json={"id": ""})
        png("gen_y.png"); await LI.noter(["gen_y.png"], "generation"); await job("job-tard"); await statut("job-tard", "done"); await calme()
        check("A7 sans projet actif : rien n'est range", not any(r_ in ("gen_y.png", "job-tard") for r_, _k in items(p["id"])))

        print("\n[R] renommer et supprimer ne laissent pas d'orphelin")
        rr = await cl.post("/api/images/gen_a.png/rename", json={"new_name": "abysses une"})
        neuf = rr.json().get("new")
        check("R1 renommer un fichier : son appartenance le SUIT (dans chaque projet)", rr.status_code == 200
              and (neuf, "image") in items(p["id"]) and not any(r_ == "gen_a.png" for r_, _ in items(p["id"])), str(items(p["id"])))
        await cl.delete(f"/api/images/{neuf}")
        check("R2 supprimer le fichier : il quitte ses projets", not any(r_ == neuf for r_, _ in items(p["id"])))
        await cl.delete("/api/jobs/job-3d")
        check("R3 supprimer un job : il quitte ses projets", not any(r_ == "job-3d" for r_, _ in items(p["id"])))
        await cl.put("/api/library/projets/actif", json={"id": p["id"]})
        r = await cl.delete(f"/api/library/projets/{p['id']}")
        check("R4 supprimer un projet : ses appartenances partent, les FICHIERS restent, l'actif est vide",
              r.status_code == 200 and items(p["id"]) == [] and (_tmp / "images" / "gen_z.png").is_file()
              and (await cl.get("/api/library/projets/actif")).json().get("id") == ""
              and base("SELECT value FROM atelier_settings WHERE key='library_projet_actif'") == [("",)], r.text)

        print("\n[S] le telephone : un seul projet")
        n = await LP.reprendre_epingles_json()
        try:
            n2 = await LP.reprendre_epingles_json()
        except Exception as e:  # un rejeu qui casse est un FAIL nomme, pas un plantage du banc
            n2 = f"exception {type(e).__name__}"
        sept = [x for x in (await cl.get("/api/library/projets")).json()["projets"] if x["nom"] == "campagne-septembre"]
        check("S1 projets.json repris UNE fois en projet EPINGLE (fichier garde)", n == 1 and n2 == 0 and len(sept) == 1
              and sept[0].get("epingle") is True and (_tmp / "outputs" / "_sync" / "projets.json").is_file(), f"{n} {n2} {sept}")
        r = await cl.post("/api/sync/projet", json={"nom": "campagne-octobre", "fichiers": ["../../gen_b.png", "gen_z.png", ""]})
        check("S2 /api/sync/projet garde son contrat ({nom, fichiers} noms nus, tries) et ecrit un projet EPINGLE de la Bibliotheque",
              r.status_code == 200 and r.json() == {"nom": "campagne-octobre", "fichiers": ["gen_b.png", "gen_z.png"]}
              and base("SELECT epingle FROM library_projects WHERE nom='campagne-octobre'") == [(1,)], r.text)
        await cl.post(f"/api/library/projets/{p2['id']}/items", json={"items": [{"ref": "gen_b.png", "kind": "image"},
                                                                               {"ref": "job-render", "kind": "render"}]})
        from app.services import sync_index as SI
        pj = (await SI.manifeste())["projets"]
        check("S3 le manifeste lit la TABLE : les projets epingles seulement, leurs FICHIERS images seulement (pas un id de job)",
              pj == [{"nom": "Deck Oracle II", "fichiers": ["gen_b.png"], "entier": True},
                     {"nom": "campagne-octobre", "fichiers": ["gen_b.png", "gen_z.png"], "entier": True},
                     {"nom": "campagne-septembre", "fichiers": ["gen_s1.png", "gen_s2.png"], "entier": True}], str(pj))

        print("\n[G] la garde des ecritures locales")
        async with AsyncClient(transport=ASGITransport(app=app, client=("192.168.1.20", 50000)), base_url="http://t") as dist:
            g = [(await dist.post("/api/library/projets", json={"nom": "x"})).status_code,
                 (await dist.put("/api/library/projets/actif", json={"id": ""})).status_code,
                 (await dist.request("DELETE", f"/api/library/projets/{p2['id']}")).status_code]
        import app.main as M
        check("G1 depuis le reseau local : refuse (401 sans jeton), et aucune de ces ecritures n'est ouverte au telephone",
              g == [401, 401, 401] and not any("/library/projets" in c for _m, c in M._ECRITURES_OUVERTES), str(g))
    await storage._engine.dispose()


asyncio.run(main())
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
