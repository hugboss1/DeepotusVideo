# -*- coding: utf-8 -*-
"""Bibliotheque, tache #82 PR A (plan-library T14, 04/10/2026) — les COMMENTAIRES de revue, cote serveur.
DECISION DE L'UTILISATEUR (04/10) : commentaires DATES avec STATUT (a_revoir / valide / rejete), instant pour un son ;
« note » designe deja la note 0..5 (#77). Un commentaire suit son asset : renomme, et jete puis restaure (meme sous un
nom voisin). Le plan les mettait dans `library_fiche.sections` (inexistant) et ne pensait ni au renommage ni a la corbeille.
Temoin positif : la base (329aa702) n'a ni la table ni les routes.
Run (depuis backend/) : & $PY tests/test_library_commentaires.py"""
import asyncio, io, json, os, pathlib, sqlite3, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcomm_"))
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


def png(nom):
    buf = io.BytesIO(); Image.new("RGB", (8, 8), (9, 9, 9)).save(buf, format="PNG"); (_tmp / "images" / nom).write_bytes(buf.getvalue())


def base(sql, *a):
    con = sqlite3.connect(BASE_DB)
    try:
        r = con.execute(sql, a).fetchall(); con.commit(); return r
    finally:
        con.close()


BASE = "329aa702"
r_ro = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE)).stdout
r_st = subprocess.run(["git", "show", f"{BASE}:backend/app/services/storage.py"], capture_output=True, cwd=str(RACINE)).stdout
check("T0 temoin : la base n'a ni la table ni les routes des commentaires", b"library_comments" not in r_st and b'"/library/commentaires/{ref}"' not in r_ro)


async def main():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services import storage
    from app.services import library_index as LI
    await storage.init_db()
    tr = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=tr, base_url="http://127.0.0.1") as cl:
        png("a b.png"); await LI.noter(["a b.png"], "generation")
        U = "/api/library/commentaires/a%20b.png"
        r1 = await cl.post(U, json={"texte": "  ciel trop sature  "})
        r2 = await cl.post(U, json={"texte": "ok pour la version 2", "statut": "valide"})
        L = (await cl.get(U)).json()
        c1 = L["commentaires"][0]
        check("C1 ajouter : texte NETTOYE, statut « a_revoir » par defaut (ou celui donne), dates ISO UTC ; la liste dans l'ordre, avec les statuts possibles",
              r1.status_code == 200 and c1["texte"] == "ciel trop sature" and c1["statut"] == "a_revoir" and c1["t_s"] is None and c1["cree_le"].endswith("+00:00")
              and [c["statut"] for c in L["commentaires"]] == ["a_revoir", "valide"] and L["statuts"] == ["a_revoir", "valide", "rejete"]
              and base("SELECT COUNT(*) FROM library_comments WHERE ref='a b.png'") == [(2,)], json.dumps(L)[:300])
        await asyncio.sleep(1.1)   # les dates sont a la seconde
        r = await cl.patch(f"/api/library/commentaires/c/{c1['id']}", json={"statut": "rejete"})
        r_t = await cl.patch(f"/api/library/commentaires/c/{c1['id']}", json={"texte": "ciel corrige"})
        check("C2 modifier le statut puis le texte (relus) ; la date de modification avance", r.status_code == 200 and r.json()["statut"] == "rejete"
              and r_t.json()["texte"] == "ciel corrige" and r_t.json()["statut"] == "rejete" and r_t.json()["modifie_le"] > c1["modifie_le"] and r_t.json()["cree_le"] == c1["cree_le"], r_t.text)
        refus = [await cl.post(U, json=j) for j in ({"texte": "   "}, {"texte": "x" * 2001}, {"texte": "x", "statut": "bof"},
                                                     {"texte": "x", "t_s": -1}, {"texte": "x", "t_s": "3"}, {"texte": "x", "t_s": True})]
        p0 = await cl.patch(f"/api/library/commentaires/c/{c1['id']}", json={})
        p404 = await cl.patch("/api/library/commentaires/c/absent", json={"statut": "valide"})
        r400 = await cl.get("/api/library/commentaires/x%5Cy.png")
        check("C3 refus 400 : texte vide ou trop long, statut inconnu, instant negatif / texte / booleen, PATCH sans champ, reference qui n'est pas un nom ; 404 : commentaire inconnu",
              [x.status_code for x in refus] == [400] * 6 and p0.status_code == 400 and p404.status_code == 404 and r400.status_code == 400,
              str([x.status_code for x in refus]) + f" {p0.status_code} {p404.status_code} {r400.status_code}")
        (_tmp / "audio" / "v.mp3").write_bytes(b"ID3")
        rs = await cl.post("/api/library/commentaires/v.mp3", json={"texte": "souffle ici", "t_s": 83.5})
        check("C4 un SON : l'instant vise est garde", rs.status_code == 200 and rs.json()["t_s"] == 83.5, rs.text)
        d = await cl.delete(f"/api/library/commentaires/c/{r2.json()['id']}")
        d2 = await cl.delete(f"/api/library/commentaires/c/{r2.json()['id']}")
        check("C5 supprimer, puis 404 la seconde fois", d.status_code == 200 and d2.status_code == 404 and len((await cl.get(U)).json()["commentaires"]) == 1)

        print("[S] le commentaire suit son asset")
        await LI.renommer("a b.png", "renomme.png")
        check("S1 RENOMME : le commentaire change de reference", (await cl.get("/api/library/commentaires/renomme.png")).json()["commentaires"][0]["texte"] == "ciel corrige"
              and (await cl.get(U)).json()["commentaires"] == [])
        (_tmp / "images" / "a b.png").rename(_tmp / "images" / "renomme.png")
        eid = (await cl.delete("/api/images/renomme.png")).json()["corbeille"]
        check("S2 JETE : le commentaire part avec l'asset (plus de ligne)", base("SELECT COUNT(*) FROM library_comments WHERE ref='renomme.png'") == [(0,)])
        png("renomme.png")   # le nom est repris entre-temps
        rr = (await cl.post("/api/library/corbeille/restaurer", json={"id": eid})).json()
        cs = (await cl.get(f"/api/library/commentaires/{rr['restaure']}")).json()["commentaires"]
        check("S3 RESTAURE sous un nom voisin : le commentaire revient avec SON statut et sa date, sous le nom rendu ; rien sur le nouveau fichier",
              rr["renomme"] is True and [(c["texte"], c["statut"], c["cree_le"]) for c in cs] == [("ciel corrige", "rejete", c1["cree_le"])]
              and (await cl.get("/api/library/commentaires/renomme.png")).json()["commentaires"] == [], json.dumps(cs))


asyncio.run(main())
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
