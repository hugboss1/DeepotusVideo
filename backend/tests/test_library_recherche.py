# -*- coding: utf-8 -*-
"""Bibliotheque, tache #82 PR C (plan-library T12-T13, 04/10/2026) — la RECHERCHE (moteur texte, local) et les LEGENDES
(modele vision payant), cote serveur.
DECISIONS DE L'UTILISATEUR (04/10) : deux moteurs avec un SELECTEUR — texte (legendes, tags, prompts, commentaires,
noms ; rien ne sort du PC) et CLIP local (PR D) ; les legendes par un modele vision PAYANT : prix ANNONCE avant
(devis), plafond « bibliotheque » verifie AVANT, les images partent chez Google (dit a l'ecran).
Ce que le plan faisait faux : un service « Clipbox » inexistant retenu par defaut, un chemin distant qui enverrait
toutes les images sans prix ni plafond ; la grille locale (0,075 $/M) etait perimee pour la vision (releve 04/10 :
Flash-Lite 0,10 / 0,40 $).
Gemini est SIMULE (couture _appel remplacee) : AUCUN appel reel. Cles videes.
Temoin positif : la base (258d5724) n'a ni la recherche ni les legendes.
Run (depuis backend/) : & $PY tests/test_library_recherche.py"""
import asyncio, io, json, os, pathlib, sqlite3, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzrech_"))
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


def png(nom, c=(9, 9, 9)):
    # du BRUIT : une image unie se compresse en rien, et la taille de la vignette envoyee ne se verrait pas
    buf = io.BytesIO(); Image.frombytes("RGB", (900, 600), os.urandom(900 * 600 * 3)).save(buf, format="PNG"); (_tmp / "images" / nom).write_bytes(buf.getvalue())


def base(sql, *a):
    con = sqlite3.connect(BASE_DB)
    try:
        r = con.execute(sql, a).fetchall(); con.commit(); return r
    finally:
        con.close()


BASE = "258d5724"
r_ro = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE)).stdout
check("T0 temoin : la base n'a ni la recherche ni les legendes", b'"/library/recherche"' not in r_ro and b'"/library/legendes"' not in r_ro)


async def main():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.config import settings
    from app.services import storage, pricing, plafonds
    from app.services import library_index as LI
    from app.services import library_legendes as LL
    await storage.init_db()

    print("[P] le prix")
    d = pricing.estimate({"kind": "legende", "n": 1009, "model": "gemini-2.5-flash-lite"})
    attendu = 1009 * (348 / 1e6 * 0.10 + 70 / 1e6 * 0.40)
    check("P1 le devis : n images x (258 jetons image + 90 de consigne) en entree, 70 en sortie, au tarif RELEVE (Flash-Lite 0,10 / 0,40 $/M) — ≈ 0,06 $ pour 1009",
          abs(d["total_usd"] - round(attendu, 4)) < 1e-4 and 0.05 < d["total_usd"] < 0.07 and d["breakdown"][0]["provider"] == "gemini", json.dumps(d))
    d2 = pricing.estimate({"kind": "legende", "n": 10, "model": "gemini-2.5-flash"})
    check("P2 le modele Flash (plus cher) a son propre tarif ; un modele inconnu retombe sur Flash-Lite",
          abs(d2["total_usd"] - round(10 * (348 / 1e6 * 0.30 + 70 / 1e6 * 2.50), 4)) < 1e-4
          and pricing.estimate({"kind": "legende", "n": 10, "model": "x"})["total_usd"] == pricing.estimate({"kind": "legende", "n": 10})["total_usd"])

    for n in ("gen_4307033a.png", "phare_nuit.png", "b.png", "c.png"):
        png(n); await LI.noter([n], "generation")
    tr = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=tr, base_url="http://127.0.0.1") as cl:
        print("[L] les legendes")
        dv = (await cl.get("/api/library/legendes/devis")).json()
        check("L1 devis : 4 images sans legende, le prix, le modele, la cle absente dite", dv["n"] == 4 and dv["modele"] == "gemini-2.5-flash-lite"
              and dv["cle"] is False and dv["usd"] == pricing.estimate({"kind": "legende", "n": 4})["total_usd"], json.dumps(dv))
        r = await cl.post("/api/library/legendes", json={})
        check("L2 sans cle : 503 et RIEN n'est lance", r.status_code == 503 and LL.etat()["en_cours"] is False and LL.etat()["total"] == 0, r.text)
        dist = AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False, client=("192.168.1.20", 5000)), base_url="http://192.168.1.20")
        rl = await dist.post("/api/library/legendes", json={})
        # (mutant equivalent documente : sans la garde de depense locale, la garde d'APPAREIL du reseau local refuse deja en 401)
        check("L3 depuis le reseau local : refuse (403) avant toute lecture", rl.status_code in (401, 403), str(rl.status_code))

        settings.GEMINI_API_KEY = "cle-factice-du-banc"
        appels = []
        async def faux(client, b64):
            appels.append(len(b64))
            await asyncio.sleep(0.01)
            return "Un phare sous la tempête, la nuit. phare, tempête, lighthouse, storm, bleu"
        vrai = LL._appel
        LL._appel = faux
        plafonds.enregistrer({"par_moteur": {"gemini": 0.000001}})
        r402 = await cl.post("/api/library/legendes", json={})
        check("L4 un PLAFOND depasse refuse (402) AVANT tout appel", r402.status_code == 402 and appels == [] and LL.etat()["total"] == 0, r402.text[:200])
        plafonds.enregistrer({"par_moteur": {}})
        r = await cl.post("/api/library/legendes", json={"noms": ["phare_nuit.png", "b.png"]})
        t0 = time.time()
        while LL.etat()["en_cours"] and time.time() - t0 < 10:
            await asyncio.sleep(0.05)
        check("L5 les images NOMMEES seulement, en tache de fond ; la legende et son modele sont ecrits ; l'image envoyee est une vignette (<= 384 px)",
              r.status_code == 200 and r.json()["lance"] == 2 and len(appels) == 2 and LL.etat()["faits"] == 2
              and base("SELECT legende_modele FROM library_assets WHERE filename='phare_nuit.png'") == [("gemini-2.5-flash-lite",)]
              and base("SELECT COUNT(*) FROM library_assets WHERE legende IS NOT NULL") == [(2,)] and 0 < max(appels) < 200000, r.text + str(appels))   # 900x600 de bruit en entier : plus d'1 Mo en base64
        check("L6 la garde a ECRIT la depense prevue au registre (categorie bibliotheque)",
              base("SELECT COUNT(*) FROM depenses WHERE categorie='bibliotheque' AND moteur='gemini'") == [(1,)], str(base("SELECT moteur, categorie FROM depenses")))
        async def lent(client, b64):
            await asyncio.sleep(0.3); return "x"
        LL._appel = lent
        r1 = await cl.post("/api/library/legendes", json={})
        r2 = await cl.post("/api/library/legendes", json={})
        double = LL.lancer(["b.png"])   # la garde du service elle-meme (la route la double par le 409)
        check("L7 un legendage EN COURS : le second est refuse (409)", r1.status_code == 200 and r2.status_code == 409 and double is False, f"{r1.status_code} {r2.status_code} {double}")
        while LL.etat()["en_cours"]:
            await asyncio.sleep(0.05)
        base("UPDATE library_assets SET legende=NULL")
        async def capricieux(client, b64):
            appels.append("c")
            if len([a for a in appels if a == "c"]) == 1:
                raise RuntimeError("Gemini HTTP 500 : boom")
            return "ok"
        LL._appel, LL.PARALLELE = capricieux, 1
        await cl.post("/api/library/legendes", json={})
        while LL.etat()["en_cours"]:
            await asyncio.sleep(0.05)
        e = LL.etat()
        check("L8 une image ratee (HTTP 500) n'arrete pas les autres : elle est DITE dans les erreurs", e["n_erreurs"] == 1 and e["faits"] == 3 and e["arret"] == "", json.dumps(e)[:300])
        base("UPDATE library_assets SET legende=NULL")
        async def refuse(client, b64):
            raise RuntimeError("Gemini HTTP 401 : cle invalide")
        LL._appel = refuse
        await cl.post("/api/library/legendes", json={})
        while LL.etat()["en_cours"]:
            await asyncio.sleep(0.05)
        e = LL.etat()
        check("L9 une cle REFUSEE (401) ARRETE le travail (pas quatre refus pour rien) et le dit", "HTTP 401" in e["arret"] and e["faits"] == 0 and e["n_erreurs"] == 1, json.dumps(e)[:300])
        LL._appel, LL.PARALLELE = vrai, 4

        print("[R] la recherche (texte, local)")
        base("UPDATE library_assets SET legende='Un phare sous la tempête, la nuit. phare, tempête, lighthouse, bleu' WHERE filename='b.png'")
        await LI.editer("c.png", {"tags": ["mer", "phare"]})
        async with storage.async_session_factory() as s:
            s.add(storage.JobRecord(id="j1", status="done", progress=100, image_filename="gen_4307033a.png", final_prompt="a red lighthouse at dawn"))
            await s.commit()
        await cl.post("/api/library/commentaires/c.png", json={"texte": "à refaire avec une baleine"})
        R = lambda q, m="texte": cl.get("/api/library/recherche", params={"q": q, "moteur": m})
        r = (await R("tempete")).json()
        check("R1 « tempete » (sans accent) trouve la LEGENDE « tempête », avec l'extrait et le champ", [x["filename"] for x in r["resultats"]] == ["b.png"]
              and r["resultats"][0]["champs"] == ["legende"] and "tempête" in r["resultats"][0]["extrait"], json.dumps(r))
        r = (await R("phar")).json()
        check("R2 un debut de mot suffit ; la legende et les tags (3) passent avant le nom (1)",
              [x["filename"] for x in r["resultats"]] == ["b.png", "c.png", "phare_nuit.png"], json.dumps([(x["filename"], x["score"]) for x in r["resultats"]]))
        png("a_phare_nom.png"); await LI.noter(["a_phare_nom.png"], "generation")
        base("UPDATE library_assets SET legende='un phare' WHERE filename='zz.png'")
        png("zz.png"); await LI.noter(["zz.png"], "generation"); base("UPDATE library_assets SET legende='un phare' WHERE filename='zz.png'")
        rz = [x["filename"] for x in (await R("phare")).json()["resultats"]]
        check("R2b le POIDS decide avant l'ordre alphabetique : zz.png (legende) passe avant a_phare_nom.png (nom)", rz.index("zz.png") < rz.index("a_phare_nom.png"), str(rz))
        r = (await R("phare mer")).json()
        check("R3 TOUS les mots doivent etre trouves (ET)", [x["filename"] for x in r["resultats"]] == ["c.png"], json.dumps(r["resultats"]))
        r1, r2 = (await R("lighthouse dawn")).json(), (await R("baleine")).json()
        check("R4 le PROMPT d'un rendu nourrit son image de depart ; un COMMENTAIRE aussi", [x["filename"] for x in r1["resultats"]] == ["gen_4307033a.png"]
              and r1["resultats"][0]["champs"] == ["prompt"] and [x["filename"] for x in r2["resultats"]] == ["c.png"] and r2["resultats"][0]["champs"] == ["commentaires"])
        r = (await R("4307033a")).json()
        check("R5 le hachage d'un nom gen_<hex> n'est pas un mot cherchable", r["n"] == 0, json.dumps(r))
        rv, rc, rb = (await R("  ")).json(), await R("phare", "clip"), await R("phare", "autre")
        check("R6 une requete vide ne rend rien ; moteur clip : 503 dit (PR D) ; moteur inconnu : 400", rv["resultats"] == [] and rc.status_code == 503 and rb.status_code == 400)
        f = (await cl.get("/api/library/fiche/b.png")).json()
        base("ALTER TABLE library_assets DROP COLUMN legende_modele"); base("ALTER TABLE library_assets DROP COLUMN legende")
        await storage._auto_migrate()
        cols = [c[1] for c in base("PRAGMA table_info(library_assets)")]
        check("M1 une base d'AVANT recoit les colonnes legende et legende_modele au demarrage", "legende" in cols and "legende_modele" in cols)
        check("R7 la fiche sert la legende et son modele", f["legende"] == {"texte": "Un phare sous la tempête, la nuit. phare, tempête, lighthouse, bleu", "modele": None}
              or (f["legende"] or {}).get("texte", "").startswith("Un phare"), json.dumps(f.get("legende")))


asyncio.run(main())
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
