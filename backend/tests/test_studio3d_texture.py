# -*- coding: utf-8 -*-
"""t393 (31/10/2026) — écran Texture du 3D Studio, volet 1/2 : références d'image (capture → modèle d'image) et
retexture IA (Meshy), puis la page (module, feuille, clés FR/EN) et le calcul sous node.

AUCUN appel réseau, AUCUNE dépense : l'appel au modèle d'image (`studio3d_texture._tirer`) et la retexture
(`asset3d_service.texturer_asset3d`) sont remplacés par des faux. Ce qu'on prouve : l'ordre des refus (503 clé →
400/404 entrées → 409 devis → 409 prix accepté → 402 plafond), que rien ne part ni ne s'écrit avant l'accord, et qu'un
tir accepté écrit ce qu'il doit (référence rangée avec le job, ligne de dépense « moteurs3d », version Meshy, approbation).
Run : python tests/test_studio3d_texture.py (depuis backend/)"""
import asyncio, base64, json, os, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzs3tex_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = ""; os.environ["ELEVENLABS_API_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
os.environ["MESHY_API_KEY"] = ""; os.environ["OPENAI_API_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from loguru import logger                                         # noqa: E402
logger.remove()
from app.config import settings                                   # noqa: E402
from app.services import print3d, studio3d_texture as ST          # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]
J = settings.outputs_path / "assets3d"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64          # en-tête PNG : le service ne décode pas l'image, il la range
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
du = lambda o: "data:image/png;base64," + base64.b64encode(o).decode()


def boite():
    P = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
    F = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6), (1, 2, 6), (1, 6, 5),
         (3, 0, 4), (3, 4, 7)]
    return print3d.glb_de_pieces([("m", [(P[a], P[b], P[c]) for a, b, c in F])])


def _job(nom):
    d = J / nom
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(boite())
    (d / "asset.json").write_text(json.dumps({"name": nom, "engine": "import", "version": 1,
                                              "created_at": "2026-10-31T10:00:00+00:00"}), encoding="utf-8")
    return d


_job("perso")
_job("caisse")


def _client():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def _depenses():
    from sqlalchemy import select
    from app.services import plafonds
    from app.services.storage import Depense
    async with plafonds._registre() as s:
        return [(d.ref, d.moteur, d.categorie, round(d.estime_usd, 4))
                for d in (await s.execute(select(Depense))).scalars().all()]


async def _jobs():
    from sqlalchemy import select
    from app.services.storage import JobRecord, async_session_factory, init_db
    await init_db()
    async with async_session_factory() as s:
        return (await s.execute(select(JobRecord))).scalars().all()


def _refs_sur_disque(job):
    d = J / job / "texture_refs"
    return sorted(p.name for p in d.iterdir()) if d.is_dir() else []


# ── le service ───────────────────────────────────────────────────────────────

def test_les_modeles_suivent_l_ordre_de_preference_et_restent_choisissables_sans_cle():
    m = ST.modeles()
    ids = [x["id"] for x in m["modeles"]]
    assert ids == [i for i in ST.PREFERES if i in ids], ids
    assert ids[0] == m["defaut"] and m["defaut"] in ("nano-banana-2", "nano-banana-pro"), m["defaut"]
    assert "recraft-4.1-vecteur" not in ids and "flux" not in ids          # vectoriel / sans retouche : absents
    par = {x["id"]: x for x in m["modeles"]}
    assert all(x["cle_ok"] is False for x in m["modeles"]), "aucune clé posée : tous sans clé, mais listés"
    assert par["nano-banana-pro"]["resolutions"] == ["1K", "2K", "4K"]
    assert par["nano-banana-2.1"]["resolutions"] == ["1K"]
    assert par["gpt-image-2-fal"]["multi_refs"] is False and par["nano-banana"]["multi_refs"] is True
    assert m["ratios"] == ["1:1", "16:9", "9:16", "4:3", "3:4"] and m["prompt_defaut"] == ST.PROMPT_DEFAUT
    # 4K de Nano Banana Pro : deux fois le prix de 1K (doc fal) ; 2K au même prix
    d1, d2, d4 = (ST.devis_image("nano-banana-pro", r)["usd"] for r in ("1K", "2K", "4K"))
    assert d1 > 0 and d2 == d1 and abs(d4 - 2 * d1) < 1e-9, (d1, d2, d4)
    assert ST.op_image("nano-banana-pro", "4K") == {"kind": "image", "n": 2, "model": "nano-banana-pro"}
    r = m["retexture"]["devis"]
    assert (r["2k"]["credits"], r["8k"]["credits"]) == (10, 15) and r["2k"]["usd"] > 0


def test_les_images_entrent_en_png_ou_jpeg_et_la_capture_en_png_seulement():
    assert ST.decoder_image(du(PNG), png_seul=True) == (PNG, ".png")
    assert ST.decoder_image(base64.b64encode(JPG).decode()) == (JPG, ".jpg")
    for v, png in (("", False), ("data:image/png;base64,@@@", False), (du(b"GIF89a" + b"\0" * 10), False),
                   (du(JPG), True)):
        try:
            ST.decoder_image(v, png_seul=png)
        except ValueError:
            continue
        raise AssertionError(v[:30])


def test_une_planche_de_style_se_range_avec_le_job_et_se_relit():
    e = ST.ajouter_style("caisse", du(JPG))
    assert e["sorte"] == "style" and e["fichier"].endswith(".jpg")
    assert e["url"] == f"/api/studio3d/texture/caisse/reference/{e['id']}"
    assert ST.chemin_reference("caisse", e["id"]).read_bytes() == JPG
    assert [r["id"] for r in ST.references("caisse")] == [e["id"]]
    for mauvais in ("../asset", "inconnu00", ""):
        try:
            ST.chemin_reference("caisse", mauvais)
        except FileNotFoundError:
            continue
        raise AssertionError(mauvais)
    # une image perdue disparaît de la liste ; un index abîmé ne casse rien
    (J / "caisse" / "texture_refs" / e["fichier"]).unlink()
    assert ST.references("caisse") == []
    (J / "caisse" / "texture_refs" / "refs.json").write_text("{pas du json", encoding="utf-8")
    assert ST.references("caisse") == []
    try:
        ST.ajouter_style("inexistant", du(PNG))
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("job inconnu")
    shutil.rmtree(J / "caisse" / "texture_refs")


def test_la_retexture_envoie_l_image_choisie_a_meshy_a_la_place_des_vues():
    """`vues_style` (ajouté pour t393) : le payload Meshy porte l'image choisie, pas les vues du manifeste."""
    from app.services import asset3d_service as A3, meshy_service as MS
    d = J / "caisse"
    (d / "shot_1.png").write_bytes(PNG)
    man = json.loads((d / "asset.json").read_text(encoding="utf-8"))
    (d / "asset.json").write_text(json.dumps({**man, "shots": ["shot_0.png", "shot_1.png"]}), encoding="utf-8")
    ref = ST.ajouter_style("caisse", du(PNG))
    chemin = ST.chemin_reference("caisse", ref["id"])
    A3.approve("caisse", True, "banc")
    envois, charges = [], []

    async def faux_upload(p):
        envois.append(pathlib.Path(p).name)
        return "https://fal.example/" + pathlib.Path(p).name

    async def faux_create(base, payload):
        charges.append(payload)
        raise RuntimeError("arrêt du banc avant Meshy")

    vieux = (A3._upload, MS.create_task)
    A3._upload, MS.create_task = faux_upload, faux_create
    try:
        for vues in (None, [chemin]):
            try:
                asyncio.run(A3.texturer_asset3d("caisse", vues_style=vues))
            except RuntimeError as e:
                assert "arrêt du banc" in str(e)
    finally:
        A3._upload, MS.create_task = vieux
    assert envois == ["model.glb", "shot_1.png", "model.glb", chemin.name], envois
    assert charges[0]["multiview_image_urls"] == ["https://fal.example/shot_1.png"]
    assert charges[1]["multiview_image_urls"] == ["https://fal.example/" + chemin.name]
    (d / "approval.json").unlink()
    shutil.rmtree(d / "texture_refs")


# ── les routes : générer une référence ───────────────────────────────────────

def test_generer_refuse_dans_l_ordre_sans_rien_depenser_puis_range_la_reference():
    from app.services import plafonds
    appels = []

    async def faux_tirer(modele, prompt, ratio, resolution, chemins):
        appels.append((modele, prompt, ratio, resolution, [pathlib.Path(c).name for c in chemins]))
        nom = "gen_banc0001.png"
        (settings.images_path / nom).write_bytes(PNG + b"rendu")
        return [nom]

    vieux = ST._tirer
    ST._tirer = faux_tirer
    style = ST.ajouter_style("perso", du(JPG))
    base = {"modele": "nano-banana-pro", "resolution": "4K", "ratio": "16:9", "capture": du(PNG), "vue": "face",
            "eclairage": "trois"}

    async def main():
        o = {}
        await _jobs()
        async with _client() as c:
            url = "/api/studio3d/texture/perso/generer"
            o["modele_inconnu"] = (await c.post(url, json={**base, "modele": "flux"})).status_code
            o["sans_cle"] = (await c.post(url, json={**base, "capture": "abîmée"})).status_code   # 503 AVANT l'entrée
            settings.FAL_KEY = "cle-de-banc"
            o["capture"] = (await c.post(url, json={**base, "capture": du(JPG)})).status_code
            o["ratio"] = (await c.post(url, json={**base, "ratio": "21:9"})).status_code
            o["res"] = (await c.post(url, json={**base, "modele": "nano-banana-2.1"})).status_code
            o["prompt"] = (await c.post(url, json={**base, "prompt": "x" * 1001})).status_code
            o["job"] = (await c.post("/api/studio3d/texture/inconnu/generer", json=base)).status_code
            o["style"] = (await c.post(url, json={**base, "style": "abcdef012345"})).status_code
            r = await c.post(url, json=base)
            o["devis"] = (r.status_code, r.json())
            o["devis_gratuit"] = (await c.post("/api/studio3d/texture/devis", json={"action": "generer",
                                  "modele": "nano-banana-pro", "resolution": "4K"})).json()
            r = await c.post(url, json={**base, "confirme_cout": True, "max_usd": 0.01})
            o["max"] = (r.status_code, r.json())
            plafonds.enregistrer({"par_moteur": {"fal": 0.0001}})
            r = await c.post(url, json={**base, "confirme_cout": True, "max_usd": 1})
            o["plafond"] = (r.status_code, r.json())
            o["rien"] = (len(appels), await _depenses(), _refs_sur_disque("perso"))
            r = await c.post(url, json={**base, "confirme_cout": True, "max_usd": 1, "style": style["id"],
                                        "prompt": "bois patiné"}, headers={"X-DZ-Plafond": "confirme"})
            o["ok"] = (r.status_code, r.json())
            o["liste"] = (await c.get("/api/studio3d/texture/perso/references")).json()
            rid = o["ok"][1].get("reference", {}).get("id", "x")
            r = await c.get(f"/api/studio3d/texture/perso/reference/{rid}")
            o["fichier"] = (r.status_code, r.content)
            o["fichier_404"] = (await c.get("/api/studio3d/texture/perso/reference/0123456789ab")).status_code
        o["depenses"] = await _depenses()
        return o
    try:
        o = asyncio.run(main())
    finally:
        ST._tirer = vieux
        settings.FAL_KEY = ""
        plafonds.enregistrer({"par_moteur": {}})
    assert (o["modele_inconnu"], o["sans_cle"]) == (400, 503), o
    assert (o["capture"], o["ratio"], o["res"], o["prompt"]) == (400, 400, 400, 400), o
    assert (o["job"], o["style"]) == (404, 404), o
    st, j = o["devis"]
    assert st == 409 and j["detail"]["code"] == "confirme_cout", j
    assert j["detail"]["devis"]["usd"] == o["devis_gratuit"]["usd"] == ST.devis_image("nano-banana-pro", "4K")["usd"]
    st, j = o["max"]
    assert st == 409 and j["detail"]["code"] == "max_usd", j
    st, j = o["plafond"]
    assert st == 402 and "dz_plafond" in json.dumps(j), (st, j)
    assert o["rien"] == (0, [], [style["fichier"], "refs.json"]), o["rien"]       # rien tiré, rien payé, rien rangé
    st, j = o["ok"]
    assert st == 200, (st, j)
    ref = j["reference"]
    assert (ref["sorte"], ref["modele"], ref["resolution"], ref["ratio"], ref["vue"], ref["eclairage"]) == \
        ("generee", "nano-banana-pro", "4K", "16:9", "face", "trois"), ref
    assert ref["bibliotheque"] == "gen_banc0001.png" and ref["style"] == style["id"]
    (modele, prompt, ratio, res, chemins), = appels
    assert (modele, prompt, ratio, res) == ("nano-banana-pro", "bois patiné", "16:9", "4K")
    assert chemins[0].startswith("capture_") and chemins[1] == style["fichier"], chemins
    assert (J / "perso" / "texture_refs" / chemins[0]).read_bytes() == PNG          # la capture est gardée
    assert o["fichier"] == (200, PNG + b"rendu") and o["fichier_404"] == 404
    assert [r["id"] for r in o["liste"]["references"]][0] == ref["id"]
    assert o["depenses"] == [("studio3d_texture:perso", "fal", "moteurs3d", ST.devis_image("nano-banana-pro", "4K")["usd"])], \
        o["depenses"]


def test_un_prompt_vide_envoie_le_prompt_par_defaut():
    vus = []

    async def faux_tirer(modele, prompt, ratio, resolution, chemins):
        vus.append(prompt)
        (settings.images_path / "gen_banc0002.png").write_bytes(PNG)
        return ["gen_banc0002.png"]

    vieux = ST._tirer
    ST._tirer = faux_tirer
    try:
        r = ST.valider_generation("perso", {"modele": "nano-banana", "capture": du(PNG)})
        e = asyncio.run(ST.generer_reference("perso", r))
    finally:
        ST._tirer = vieux
    assert vus == [ST.PROMPT_DEFAUT] and e["prompt"] == "" and e["resolution"] == "1K" and e["vue"] == "libre"


# ── les routes : retexture Meshy ─────────────────────────────────────────────

def test_retexturer_refuse_dans_l_ordre_puis_ecrit_une_version_et_approuve():
    from app.services import asset3d_service as A3, plafonds
    vus = []

    async def faux_texturer(job, **kw):
        vus.append((job, kw))
        d = J / job
        (d / "model.v2.glb").write_bytes(boite())
        return {"version": 2, "file": "model.v2.glb", "meshy_task": "tache-banc", "texture_mode": "meshy:2k",
                "pbr": True, "url": f"/api/assets/3d/{job}/version/2"}

    vieux = A3.texturer_asset3d
    A3.texturer_asset3d = faux_texturer
    ref = ST.ajouter_style("caisse", du(PNG))
    base = {"reference": ref["id"], "prompt": "laiton", "resolution": "2k"}

    async def main():
        o = {}
        await _jobs()
        async with _client() as c:
            url = "/api/studio3d/texture/caisse/retexturer"
            o["sans_meshy"] = (await c.post(url, json={})).status_code              # 503 AVANT l'entrée vide
            settings.MESHY_API_KEY = "cle-meshy-de-banc"
            r = await c.post(url, json=base)
            o["sans_fal"] = (r.status_code, json.dumps(r.json()))
            settings.FAL_KEY = "cle-fal-de-banc"
            o["vide"] = (await c.post(url, json={"resolution": "2k"})).status_code
            o["res"] = (await c.post(url, json={**base, "resolution": "16k"})).status_code
            o["ref"] = (await c.post(url, json={**base, "reference": "0123456789ab"})).status_code
            o["job"] = (await c.post("/api/studio3d/texture/inconnu/retexturer", json=base)).status_code
            r = await c.post(url, json=base)
            o["devis"] = (r.status_code, r.json())
            r = await c.post(url, json={**base, "confirme_cout": True})
            o["approbation"] = (r.status_code, r.json())
            r = await c.post(url, json={**base, "confirme_cout": True, "approuver": True, "max_usd": 0.001})
            o["max"] = (r.status_code, r.json())
            plafonds.enregistrer({"par_moteur": {"meshy": 0.0001}})
            r = await c.post(url, json={**base, "confirme_cout": True, "approuver": True, "max_usd": 5})
            o["plafond"] = (r.status_code, r.json())
            o["rien"] = (len(vus), await _depenses(), len(await _jobs()), A3.approval("caisse").get("approved"))
            r = await c.post(url, json={**base, "confirme_cout": True, "approuver": True, "max_usd": 5},
                             headers={"X-DZ-Plafond": "confirme"})
            o["ok"] = (r.status_code, r.json())
            if r.status_code == 200:
                o["job_fini"] = (await c.get(f"/api/jobs/{r.json()['job_id']}")).json()
        o["depenses"] = await _depenses()
        return o
    try:
        avant = asyncio.run(_depenses())
        o = asyncio.run(main())
    finally:
        A3.texturer_asset3d = vieux
        settings.MESHY_API_KEY = ""
        settings.FAL_KEY = ""
        plafonds.enregistrer({"par_moteur": {}})
    assert o["sans_meshy"] == 503, o
    st, j = o["sans_fal"]
    assert st == 503 and "FAL_KEY" in j, j
    assert (o["vide"], o["res"]) == (400, 400) and (o["ref"], o["job"]) == (404, 404), o
    st, j = o["devis"]
    assert st == 409 and j["detail"]["code"] == "confirme_cout" and j["detail"]["devis"]["credits"] == 10, j
    st, j = o["approbation"]
    assert st == 409 and j["detail"]["code"] == "approbation", j
    st, j = o["max"]
    assert st == 409 and j["detail"]["code"] == "max_usd", j
    st, j = o["plafond"]
    assert st == 402, (st, j)
    assert o["rien"] == (0, avant, 0, False), o["rien"]          # ni Meshy, ni dépense, ni job, ni approbation
    st, j = o["ok"]
    assert st == 200 and j["devis"]["credits"] == 10, (st, j)
    (job, kw), = vus
    assert job == "caisse" and kw["resolution"] == "2k" and kw["style_prompt"] == "laiton", kw
    assert [pathlib.Path(p).name for p in kw["vues_style"]] == [ref["fichier"]], kw
    assert o["job_fini"]["status"] == "done", o["job_fini"]
    assert A3.approval("caisse")["approved"] is True
    neuves = [d for d in o["depenses"] if d not in avant]
    assert len(neuves) == 1 and neuves[0][1:3] == ("meshy", "moteurs3d"), neuves
    assert neuves[0][0] == "meshy:tache-banc", neuves      # la garde rattachée à la tâche Meshy (réel à venir)


# ── t394 : la texture auto (lot de vues) ─────────────────────────────────────

def _poses(n):
    return [{"capture": du(PNG), "pose": {"azimut": 360 * i / n, "elevation": 10, "zoom": 1, "decalage": 0}}
            for i in range(n)]


def test_le_lot_refuse_dans_l_ordre_un_seul_devis_une_seule_garde_puis_n_appels():
    from app.services import plafonds
    appels = []

    async def faux_tirer(modele, prompt, ratio, resolution, chemins):
        appels.append((modele, prompt, ratio, resolution, len(chemins)))
        if len(appels) == 3:
            raise RuntimeError("vue refusée par le fournisseur (banc)")
        nom = f"gen_lot{len(appels):04d}.png"
        (settings.images_path / nom).write_bytes(PNG + bytes([len(appels)]))
        return [nom]

    vieux = ST._tirer
    ST._tirer = faux_tirer
    base = {"modele": "nano-banana-pro", "resolution": "2K", "captures": _poses(6), "disposition": 6,
            "eclairage": "plat", "prompt": "armure de bronze"}

    async def main():
        o = {}
        await _jobs()
        async with _client() as c:
            url = "/api/studio3d/texture/perso/generer-lot"
            o["modele"] = (await c.post(url, json={**base, "modele": "flux"})).status_code
            o["sans_cle"] = (await c.post(url, json={**base, "captures": "rien"})).status_code   # 503 AVANT l'entrée
            settings.FAL_KEY = "cle-de-banc"
            o["nombre"] = (await c.post(url, json={**base, "captures": _poses(5), "disposition": 5})).status_code
            o["dispo"] = (await c.post(url, json={**base, "disposition": 8})).status_code
            o["pose"] = (await c.post(url, json={**base, "captures": [{"capture": du(PNG), "pose": {"azimut": "x"}}] * 6})).status_code
            o["capture"] = (await c.post(url, json={**base, "captures": [{**_poses(1)[0], "capture": du(JPG)}] * 4,
                                                    "disposition": 4})).status_code
            o["job"] = (await c.post("/api/studio3d/texture/inconnu/generer-lot", json=base)).status_code
            r = await c.post(url, json=base)
            o["devis"] = (r.status_code, r.json())
            o["devis_gratuit"] = (await c.post("/api/studio3d/texture/devis", json={"action": "lot",
                                  "modele": "nano-banana-pro", "resolution": "2K", "vues": 6})).json()
            o["devis_mauvais"] = (await c.post("/api/studio3d/texture/devis", json={"action": "lot",
                                  "modele": "nano-banana-pro", "vues": 7})).status_code
            un = ST.devis_image("nano-banana-pro", "2K")["usd"]
            r = await c.post(url, json={**base, "confirme_cout": True, "max_usd": un * 5})     # le prix d'UNE vue × 5
            o["max"] = (r.status_code, r.json())
            plafonds.enregistrer({"par_moteur": {"fal": un * 5}})                               # passe 5 vues, pas 6
            r = await c.post(url, json={**base, "confirme_cout": True, "max_usd": 10})
            o["plafond"] = (r.status_code, r.json())
            o["rien"] = (len(appels), await _depenses(), _refs_sur_disque("perso"))
            r = await c.post(url, json={**base, "confirme_cout": True, "max_usd": 10}, headers={"X-DZ-Plafond": "confirme"})
            o["ok"] = (r.status_code, r.json())
        o["depenses"] = await _depenses()
        return o
    try:
        avant = asyncio.run(_depenses())
        refs_avant = _refs_sur_disque("perso")
        o = asyncio.run(main())
    finally:
        ST._tirer = vieux
        settings.FAL_KEY = ""
        plafonds.enregistrer({"par_moteur": {}})
    assert (o["modele"], o["sans_cle"]) == (400, 503), o
    assert (o["nombre"], o["dispo"], o["pose"], o["capture"], o["job"]) == (400, 400, 400, 400, 404), o
    st, j = o["devis"]
    assert st == 409 and j["detail"]["code"] == "confirme_cout", j
    d = j["detail"]["devis"]
    assert d["vues"] == 6 and d["usd"] == o["devis_gratuit"]["usd"] == ST.devis_lot("nano-banana-pro", "2K", 6)["usd"], d
    assert abs(d["usd"] - 6 * d["usd_vue"]) < 1e-6, d                                   # N × une image
    assert o["devis_mauvais"] == 400
    st, j = o["max"]
    assert st == 409 and j["detail"]["code"] == "max_usd", j
    st, j = o["plafond"]
    assert st == 402 and "dz_plafond" in json.dumps(j), (st, j)                         # le TOTAL jugé, pas une vue
    assert o["rien"] == (0, avant, refs_avant), o["rien"]
    st, j = o["ok"]
    assert st == 200, (st, j)
    assert len(appels) == 6 and {a[:4] for a in appels} == {("nano-banana-pro", "armure de bronze", "1:1", "2K")}, appels
    assert all(a[4] == 1 for a in appels), "pas de planche de style dans un lot"
    assert len(j["references"]) == 5 and [e["index"] for e in j["erreurs"]] == [2], j["erreurs"]
    assert "vue refusée" in j["erreurs"][0]["erreur"]
    idx = sorted(r["index"] for r in j["references"])
    assert idx == [0, 1, 3, 4, 5], idx
    r1 = next(r for r in j["references"] if r["index"] == 1)
    assert r1["pose"] == {"azimut": 60.0, "elevation": 10.0, "zoom": 1.0, "decalage": 0.0} and r1["vues"] == 6
    assert r1["lot"] == j["lot"] and r1["ratio"] == "1:1" and r1["sorte"] == "generee", r1
    neuves = [x for x in o["depenses"] if x not in avant]
    assert neuves == [("studio3d_texture:perso", "fal", "moteurs3d", d["usd"])], neuves      # UNE ligne : le total


# ── t394 : l'atlas peint écrit une NOUVELLE version ──────────────────────────

def _png(lg=64, ht=64, octet=7):
    """Un vrai PNG (zlib, une couleur) : le GLB réécrit doit l'embarquer tel quel."""
    import struct, zlib
    brut = b"".join(b"\x00" + bytes([octet, 255 - octet, 40]) * lg for _ in range(ht))
    bloc = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", lg, ht, 8, 2, 0, 0, 0))
            + bloc(b"IDAT", zlib.compress(brut)) + bloc(b"IEND", b""))


def glb_quad(texture: bytes | None = None, facteur=(0.5, 0.2, 0.2, 0.9), deux_textures=False, uv=True):
    """Un quad à UV (positions, normales, UV, indices) avec un matériau, et en option une texture de base embarquée."""
    import struct
    from app.services.mesh_edit import ecrire_glb
    pos = struct.pack("<12f", -1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0)
    nrm = struct.pack("<12f", *([0, 0, 1] * 4))
    uvs = struct.pack("<8f", 0, 1, 1, 1, 1, 0, 0, 0)
    idx = struct.pack("<6H", 0, 1, 2, 0, 2, 3) + b"\x00\x00"
    binc, vues = b"", []
    for bloc in (pos, nrm, uvs, idx):
        vues.append({"buffer": 0, "byteOffset": len(binc), "byteLength": len(bloc)})
        binc += bloc
    attrs = {"POSITION": 0, "NORMAL": 1}
    acc = [{"bufferView": 0, "componentType": 5126, "count": 4, "type": "VEC3", "min": [-1, -1, 0], "max": [1, 1, 0]},
           {"bufferView": 1, "componentType": 5126, "count": 4, "type": "VEC3"},
           {"bufferView": 2, "componentType": 5126, "count": 4, "type": "VEC2"},
           {"bufferView": 3, "componentType": 5123, "count": 6, "type": "SCALAR"}]
    if uv:
        attrs["TEXCOORD_0"] = 2
    doc = {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
           "meshes": [{"primitives": [{"attributes": attrs, "indices": 3, "material": 0}]}],
           "materials": [{"pbrMetallicRoughness": {"baseColorFactor": list(facteur)}}],
           "accessors": acc, "bufferViews": vues, "buffers": [{"byteLength": len(binc)}]}
    if texture is not None:
        for _ in range(2 if deux_textures else 1):
            vues.append({"buffer": 0, "byteOffset": len(binc), "byteLength": len(texture)})
            binc += texture + b"\x00" * (-len(texture) % 4)
            doc.setdefault("images", []).append({"bufferView": len(vues) - 1, "mimeType": "image/png"})
            doc.setdefault("textures", []).append({"source": len(doc["images"]) - 1})
        doc["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"] = {"index": 0, "texCoord": 0}
        if deux_textures:
            doc["materials"].append({"pbrMetallicRoughness": {"baseColorTexture": {"index": 1}}})
            doc["meshes"][0]["primitives"].append({"attributes": attrs, "indices": 3, "material": 1})
        doc["buffers"][0]["byteLength"] = len(binc)
    return ecrire_glb(doc, binc)


def _image_de_base(data):
    from app.services.mesh_edit import lire_glb
    doc, binc = lire_glb(data)
    info = doc["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"]
    im = doc["images"][doc["textures"][info["index"]]["source"]]
    bv = doc["bufferViews"][im["bufferView"]]
    return doc, binc[bv.get("byteOffset", 0):bv.get("byteOffset", 0) + bv["byteLength"]], im


def test_la_reecriture_du_glb_remplace_ou_ajoute_la_couleur_de_base_sans_toucher_la_geometrie():
    from app.services.mesh_edit import lire_glb
    atlas = _png(64, 64, 200)
    # 1. une texture d'origine : REMPLACÉE ; la géométrie reste octet pour octet
    orig = glb_quad(_png(32, 32, 10))
    sortie, det = ST.ecrire_texture_projetee(orig, atlas)
    doc, binc, im = _image_de_base(sortie)
    assert det == {"texture": "remplacee", "materiaux": [0]}, det
    assert bytes(binc) == atlas and im["mimeType"] == "image/png", im
    assert doc["bufferViews"][im["bufferView"]]["byteOffset"] % 4 == 0, "le PNG commence aligné sur 4 octets"
    d0, b0 = lire_glb(orig)
    _, tout = lire_glb(sortie)
    for i in range(4):
        bv0, bv1 = d0["bufferViews"][i], doc["bufferViews"][i]
        assert b0[bv0["byteOffset"]:bv0["byteOffset"] + bv0["byteLength"]] == tout[bv1["byteOffset"]:bv1["byteOffset"] + bv1["byteLength"]]
    pbr = doc["materials"][0]["pbrMetallicRoughness"]
    assert pbr["baseColorFactor"] == [1.0, 1.0, 1.0, 0.9] and "texCoord" not in pbr["baseColorTexture"], pbr
    assert doc["buffers"][0]["byteLength"] == len(tout) and len(doc["images"]) == 1
    # 2. aucune texture : une image, une texture, un échantillonneur AJOUTÉS au matériau de la primitive à UV
    sortie, det = ST.ecrire_texture_projetee(glb_quad(None), atlas)
    doc, binc, im = _image_de_base(sortie)
    assert det == {"texture": "ajoutee", "materiaux": [0]} and bytes(binc) == atlas, det
    assert len(doc["samplers"]) == 1 and doc["textures"][0]["sampler"] == 0
    # 3. deux textures de base, ou pas d'UV : refusé, rien n'est écrit
    for mauvais, motif in ((glb_quad(_png(), deux_textures=True), "textures de couleur de base"),
                           (glb_quad(None, uv=False), "TEXCOORD_0")):
        try:
            ST.ecrire_texture_projetee(mauvais, atlas)
        except ValueError as e:
            assert motif in str(e), e
        else:
            raise AssertionError(motif)
    # l'atlas : un PNG lisible, aux côtés bornés
    assert ST.decoder_atlas(du(atlas))[1:] == (64, 64)
    for v in (du(_png(32, 32)), du(JPG), du(PNG)):
        try:
            ST.decoder_atlas(v)
        except ValueError:
            continue
        raise AssertionError(v[:40])


def test_la_route_d_enregistrement_ecrit_une_version_valide_avec_l_atlas_pour_couleur_de_base():
    d = J / "peint"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(glb_quad(_png(32, 32, 10)))
    (d / "asset.json").write_text(json.dumps({"name": "peint", "engine": "import", "version": 1,
                                              "created_at": "2026-10-31T10:00:00+00:00"}), encoding="utf-8")
    atlas = _png(128, 128, 90)

    async def main():
        o = {}
        async with _client() as c:
            url = "/api/studio3d/texture/peint/projection"
            o["vide"] = (await c.post(url, json={"version": 1})).status_code
            o["jpeg"] = (await c.post(url, json={"version": 1, "atlas": du(JPG)})).status_code
            o["version"] = (await c.post(url, json={"version": 9, "atlas": du(atlas)})).status_code
            o["job"] = (await c.post("/api/studio3d/texture/inconnu/projection", json={"version": 1, "atlas": du(atlas)})).status_code
            r = await c.post(url, json={"version": 1, "atlas": du(atlas), "disposition": "8", "vues": 8})
            o["ok"] = (r.status_code, r.json())
        return o
    o = asyncio.run(main())
    assert (o["vide"], o["jpeg"], o["version"], o["job"]) == (400, 400, 404, 404), o
    st, j = o["ok"]
    assert st == 200 and j["version"] == 2 and j["atlas"] == [128, 128] and j["texture"] == "remplacee", j
    ecrit = (d / "model.v2.glb").read_bytes()
    assert (d / "model.glb").read_bytes() == glb_quad(_png(32, 32, 10)), "jamais d'écrasement"
    doc, binc, im = _image_de_base(ecrit)
    assert bytes(binc) == atlas, "la couleur de base est le PNG envoyé"
    # le GLB rendu se relit (trimesh, s'il est là) et la fiche garde l'opération et sa source
    try:
        import trimesh
        sc = trimesh.load(io_bytes(ecrit), file_type="glb")
        assert sum(len(g.faces) for g in sc.geometry.values()) == 2
    except ImportError:
        pass
    from app.services import mesh_report, studio3d_ouvert as SO
    reg = mesh_report.read_registry("peint")
    e = next(x for x in reg["entries"] if x["file"] == "model.v2.glb")
    src = e.get("source") or {}
    assert src.get("operation") == "texture_projection" and src.get("depuis") == {"version": 1, "fichier": "model.glb"}, e
    assert src.get("vues") == 8 and src.get("atlas") == [128, 128], src
    f = SO.fiche("peint")
    assert f["version"] == 2 and f["versions"][-1]["operation"] == "texture_projection", f["versions"]


def io_bytes(b):
    import io
    return io.BytesIO(b)


# ── la page ─────────────────────────────────────────────────────────────────

def _dico():
    return json.loads((RACINE / "frontend/shared/i18n/studio3decrans_texture.json").read_text(encoding="utf-8"))


def test_la_page_lie_la_feuille_sans_texte_neuf_et_la_coque_connait_l_ecran():
    html = (RACINE / "frontend/studio3d/index.html").read_text(encoding="utf-8")
    assert html.count('<link rel="stylesheet" href="ecrans/texture.css">') == 1
    assert html.index('href="ecrans/ecrans.css"') < html.index('href="ecrans/texture.css"')
    coque = (RACINE / "frontend/studio3d/ecrans/coque.js").read_text(encoding="utf-8")
    assert re.search(r'texture: "\./texture\.js"', coque)
    js = (RACINE / "frontend/studio3d/ecrans/texture.js").read_text(encoding="utf-8")
    assert "export async function monter(" in js and "export async function ouvrir(" in js
    # le dialogue maison AVANT chaque POST payant, puis confirme_cout et le prix accepté
    for action in ("generer", "retexturer"):
        corps = js.split(f"async function {action}()", 1)[1].split("\nasync function", 1)[0]
        assert corps.index("confirmer(") < corps.index(f"/{action}`"), action
        assert "confirme_cout: true" in corps and "max_usd: d.usd" in corps, action
    # t394 : la texture auto et « débruiter » passent aussi par le devis puis le dialogue maison ; l'essai gratuit
    # n'appelle AUCUNE route payante et ne s'affiche qu'avec ?essai
    pj = (RACINE / "frontend/studio3d/ecrans/projection.js").read_text(encoding="utf-8")
    assert 'import * as PJ from "./projection.js"' in js and "PJ.reinitialiser()" in js
    for fonction, route in (("texturerAuto", "/generer-lot`"), ("debruiter", "/generer`")):
        corps = pj.split(f"async function {fonction}()", 1)[1].split("\n}\n", 1)[0]
        assert corps.index("/devis`") < corps.index("confirmer(") < corps.index(route), fonction
        assert "confirme_cout: true" in corps and "max_usd: d.usd" in corps, fonction
    essai = pj.split("async function essayer()", 1)[1].split("\n}\n", 1)[0]
    assert "envoyer(" not in essai and "fetch(" not in essai and "generer" not in essai, essai
    assert 'has("essai")' in pj and '$("#pjEssai").hidden = !S.essai' in pj
    enreg = pj.split("async function enregistrer()", 1)[1].split("\n}\n", 1)[0]
    assert "/projection`" in enreg and "confirmer(" not in enreg, "l'enregistrement est gratuit : pas de dialogue de devis"


def test_les_cles_de_l_ecran_existent_en_fr_et_en():
    dico = _dico()
    js = (RACINE / "frontend/studio3d/ecrans/texture.js").read_text(encoding="utf-8")
    pj = (RACINE / "frontend/studio3d/ecrans/projection.js").read_text(encoding="utf-8")
    cles = {k for k in re.findall(r'\bT\("(tex\.[a-z0-9_]+)"', js + pj) if not k.endswith("_")}
    assert len(cles) > 100, len(cles)
    for k in cles:
        assert "studio3decrans." + k in dico, k
    calc = (RACINE / "frontend/studio3d/ecrans/texture_calc.js").read_text(encoding="utf-8")
    vues = re.findall(r'\{ id: "([a-z_]+)", azimut', calc)
    ecl = json.loads("[" + calc.split("export const ECLAIRAGES = [", 1)[1].split("]", 1)[0] + "]")
    assert len(vues) == 10 and len(ecl) == 5
    familles = {"vue_": vues, "vuec_": vues, "ecl_": ecl, "ecla_": ecl, "sorte_": sorted(ST.SORTES)}
    for prefixe, ids in familles.items():
        assert f'T("tex.{prefixe}" +' in js, prefixe
        for i in ids:
            assert f"studio3decrans.tex.{prefixe}{i}" in dico, (prefixe, i)
    # t394 : les familles du volet 2/2
    dispos = [int(x) for x in calc.split("export const DISPOSITIONS = [", 1)[1].split("]", 1)[0].split(",")]
    assert tuple(dispos) == ST.DISPOSITIONS, dispos
    pcalc = (RACINE / "frontend/studio3d/ecrans/projection_calc.js").read_text(encoding="utf-8")
    modes = json.loads("[" + pcalc.split("export const MODES = [", 1)[1].split("]", 1)[0] + "]")
    outils = json.loads("[" + pj.split("const OUTILS = [", 1)[1].split("]", 1)[0] + "]")
    pj_familles = {"pj_dispo_": dispos, "pj_mode_": modes, "pj_modea_": modes, "pj_outil_": outils + ["orbite"],
                   "pj_outila_": outils + ["orbite"], "pj_atlas_": ["peint", "original"]}
    for prefixe, ids in pj_familles.items():
        assert f'T("tex.{prefixe}" +' in pj, prefixe
        for i in ids:
            assert f"studio3decrans.tex.{prefixe}{i}" in dico, (prefixe, i)
    for v in ("ref", "proj"):
        assert f"studio3decrans.tex.volet_{v}" in dico and f"studio3decrans.tex.voleta_{v}" in dico
    for k, v in dico.items():
        assert k.startswith("studio3decrans.tex.") and len(k.split(".")) == 3, k
        assert v["fr"] and v["en"] and v.get("contexte") is True, k
        assert set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"])), k
    assembled = (RACINE / "frontend/shared/dz-i18n-dico.js").read_text(encoding="utf-8")
    assert '"studio3decrans.tex.generer_prix"' in assembled, "relancer scripts/i18n_assembler.py"
    assert '"studio3decrans.tex.pj_lancer_prix"' in assembled, "relancer scripts/i18n_assembler.py (t394)"


def test_aucun_rayon_litteral_dans_l_ecran():
    css = (RACINE / "frontend/studio3d/ecrans/texture.css").read_text(encoding="utf-8")
    assert "border-radius: var(--r)" in css
    assert not re.search(r"border-radius\s*:(?!\s*(?:var\(--r\)|0\b|50%))", css)
    for f in ("texture.js", "texture_calc.js", "projection.js", "projection_calc.js"):
        assert "border-radius" not in (RACINE / "frontend/studio3d/ecrans" / f).read_text(encoding="utf-8"), f


def test_le_calcul_de_l_ecran_sous_node():
    node = shutil.which("node")
    if not node:
        print("    (node absent : banc JS sauté)")
        return
    for banc in ("texture.test.mjs", "projection.test.mjs"):           # t394 : dispositions et projection
        r = subprocess.run([node, str(RACINE / "frontend/studio3d/qa" / banc)], capture_output=True,
                           text=True, encoding="utf-8")
        assert r.returncode == 0, banc + "\n" + r.stdout + r.stderr


def lancer_tous():
    rouges = []
    for nom, fn in list(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (écran Texture)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
