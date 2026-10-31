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


def test_les_cles_de_l_ecran_existent_en_fr_et_en():
    dico = _dico()
    js = (RACINE / "frontend/studio3d/ecrans/texture.js").read_text(encoding="utf-8")
    cles = {k for k in re.findall(r'\bT\("(tex\.[a-z0-9_]+)"', js) if not k.endswith("_")}
    assert len(cles) > 50, len(cles)
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
    for k, v in dico.items():
        assert k.startswith("studio3decrans.tex.") and len(k.split(".")) == 3, k
        assert v["fr"] and v["en"] and v.get("contexte") is True, k
        assert set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"])), k
    assembled = (RACINE / "frontend/shared/dz-i18n-dico.js").read_text(encoding="utf-8")
    assert '"studio3decrans.tex.generer_prix"' in assembled, "relancer scripts/i18n_assembler.py"


def test_aucun_rayon_litteral_dans_l_ecran():
    css = (RACINE / "frontend/studio3d/ecrans/texture.css").read_text(encoding="utf-8")
    assert "border-radius: var(--r)" in css
    assert not re.search(r"border-radius\s*:(?!\s*(?:var\(--r\)|0\b|50%))", css)
    for f in ("texture.js", "texture_calc.js"):
        assert "border-radius" not in (RACINE / "frontend/studio3d/ecrans" / f).read_text(encoding="utf-8"), f


def test_le_calcul_de_l_ecran_sous_node():
    node = shutil.which("node")
    if not node:
        print("    (node absent : banc JS sauté)")
        return
    r = subprocess.run([node, str(RACINE / "frontend/studio3d/qa/texture.test.mjs")], capture_output=True,
                       text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr


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
