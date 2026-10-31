# -*- coding: utf-8 -*-
"""t389 + t390 (31/10/2026) — l'onglet 3D = « Créer » et les moteurs neufs (Tripo P2 et Smart Mesh, Hunyuan 3.1,
TRELLIS 2, Rodin 2.5, Meshy 7.1).

Moteurs SIMULÉS (aucun appel réseau, aucune dépense réelle) : schémas de réglages bornés, arguments fal (image, prompt,
pose), devis ligne par ligne ; la demande de l'écran Créer (modèles × images × exemplaires) validée, chiffrée, puis
l'ordre des refus de POST /api/studio3d/creer (400 → 503 clé → 409 devis total → plafond) et les N tirs ; le mode texte
part sur l'endpoint texte ; le maillon dzcreer3d (hôte + ancien formulaire), son inverse, la page et les clés FR/EN.
Run : python tests/test_creer3d.py (depuis backend/)"""
import asyncio, io, json, os, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzc3d_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = ""; os.environ["ELEVENLABS_API_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

from loguru import logger                                         # noqa: E402
logger.remove()
from app.config import settings                                   # noqa: E402
from app.services import moteurs3d_neufs as M, pricing, studio3d_creer as SC   # noqa: E402
from app.services import asset3d_service as A3                    # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]


def png():
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (16, 16), (200, 80, 40)).save(b, "PNG")
    return b.getvalue()


for nom in ("chevalier.png", "caisse.png"):
    (pathlib.Path(_tmp, "images") / nom).write_bytes(png())


def refuse(f, *a, motif=""):
    try:
        f(*a)
    except ValueError as e:
        assert motif in str(e), (motif, str(e))
        return
    raise AssertionError(f"ValueError attendue ({motif})")


# ── t390 : les moteurs neufs ────────────────────────────────────────────────

def test_les_six_moteurs_neufs_rejoignent_le_registre_avec_leur_schema():
    neufs = {"tripo-p2", "tripo-p1", "hunyuan-3.1", "trellis-2", "rodin-2.5", "meshy-7.1"}
    assert neufs <= set(A3.ENGINES) and "meshy" not in A3.ENGINES
    for m in neufs:
        e = A3.ENGINES[m]
        assert e["neuf"] and e["reglages"] and e["label"] and e["fournisseur"]
        for r in e["reglages"]:
            assert r["type"] in ("bool", "enum", "int"), (m, r)
            if r["type"] == "enum":
                assert r["defaut"] in r["valeurs"], (m, r)
            if r["type"] == "int":
                assert r["min"] < r["max"], (m, r)
    assert {m for m in neufs if A3.ENGINES[m]["texte"]} == {"tripo-p2", "tripo-p1", "hunyuan-3.1", "rodin-2.5",
                                                             "meshy-7.1"}


def test_les_reglages_sont_bornes_au_schema():
    assert M.valider("tripo-p2", {"texture_quality": "extreme", "face_limit": 20000, "quad": True}) == \
        {"texture_quality": "extreme", "face_limit": 20000, "quad": True}
    refuse(M.valider, "tripo-p2", {"texture_quality": "8k"}, motif="hors de")
    refuse(M.valider, "tripo-p2", {"face_limit": 60000}, motif="hors de")
    refuse(M.valider, "tripo-p2", {"face_limit": True}, motif="entier")
    refuse(M.valider, "tripo-p2", {"inconnu": 1}, motif="réglage inconnu")
    refuse(M.valider, "meshy-7.1", {"should_texture": "oui"}, motif="booléen")
    assert M.valider("trellis-2", {"resolution": 1536, "seed": None}) == {"resolution": 1536}


def test_les_arguments_fal_image_prompt_et_pose():
    assert M.args("hunyuan-3.1", ["U"], {"reglages": {"enable_pbr": True}}) == {"enable_pbr": True, "input_image_url": "U"}
    assert M.args("rodin-2.5", ["U", "V"], {"pose": "a-pose"}) == {"image_urls": ["U", "V"], "TAPose": True}
    assert M.args("rodin-2.5", ["U"], {})["TAPose"] is False
    assert M.args("meshy-7.1", ["U"], {"textures": False})["should_texture"] is False      # le brouillon commun
    assert M.args("meshy-7.1", ["U"], {"pose": "t-pose"})["pose_mode"] == "t-pose"
    assert M.args("tripo-p2", [], {"prompt": "un chevalier"}) == {"prompt": "un chevalier"}
    assert M.args("tripo-p2", ["U"], {"reglages": {"texture": False}})["pbr"] is False   # pas de PBR payé sans texture
    refuse(M.args, "trellis-2", [], {"prompt": "x"}, motif="texte")
    refuse(M.args, "trellis-2", [], {}, motif="image ou un prompt")
    assert A3.build_engine_args("tripo-p1", ["U"], {"reglages": {"face_limit": 500}}) == {"face_limit": 500, "image_url": "U"}
    assert M.endpoint("tripo-p2", True) == "tripo3d/p2/text-to-3d"
    assert M.endpoint("tripo-p2", False) == "tripo3d/p2/image-to-3d"


def test_le_devis_suit_les_tarifs_fal_releves_et_les_supplements():
    e = lambda **o: pricing.estimate({"kind": "asset3d", **o})["total_usd"]          # noqa: E731
    assert e(engine="tripo-p2") == 1.10 and e(engine="tripo-p2", textures=False) == 1.00
    assert e(engine="tripo-p2", reglages={"texture_quality": "extreme"}) == 1.30
    assert e(engine="tripo-p1") == 0.50 and e(engine="tripo-p1", textures=False) == 0.40
    assert e(engine="hunyuan-3.1") == 0.375
    assert e(engine="hunyuan-3.1", reglages={"enable_pbr": True, "face_count": 80000}) == 0.675
    assert e(engine="hunyuan-3.1", reglages={"enable_pbr": True, "generate_type": "Geometry"}) == 0.375
    assert e(engine="trellis-2", reglages={"resolution": 1536}) == 0.35
    assert e(engine="rodin-2.5") == 0.40
    assert e(engine="meshy-7.1") == 1.20 and e(engine="meshy-7.1", textures=False) == 0.80
    assert e(engine="tripo") == 0.30                          # les sept d'hier : inchangés


def test_le_mode_texte_part_sur_l_endpoint_texte_sans_envoi_d_image():
    appels = []

    async def faux_run(engine, args, endpoint=None):
        if A3.ENGINES[engine].get("neuf") and not endpoint:
            endpoint = M.endpoint(engine, texte="prompt" in args and M.MOTEURS[engine]["cle_image"] not in args)
        appels.append((engine, endpoint, args))
        return {"mesh_url": "http://x/m.glb", "format_urls": {}, "texture_urls": [], "preview_url": None}

    async def faux_upload(p):
        raise AssertionError("aucun envoi d'image en mode texte")

    vrai_run, vrai_up, vrai_dl = A3._run_engine, A3._upload, A3._download
    A3._run_engine, A3._upload = faux_run, faux_upload
    A3._download = lambda url, dest, timeout=120: dest.write_bytes(b"glTF") or True
    try:
        r = asyncio.run(A3.generate_asset3d({"engine": "tripo-p2", "prompt": "un chevalier en armure",
                                             "reglages": {"texture_quality": "detailed"}}, "texte01"))
    finally:
        A3._run_engine, A3._upload, A3._download = vrai_run, vrai_up, vrai_dl
    assert r["glb"] and appels[0][1] == "tripo3d/p2/text-to-3d"
    assert appels[0][2] == {"texture_quality": "detailed", "prompt": "un chevalier en armure"}
    try:
        asyncio.run(A3.generate_asset3d({"engine": "trellis-2", "prompt": "x"}, "texte02"))
    except ValueError as e:
        assert "texte" in str(e)
    else:
        raise AssertionError("trellis-2 ne fait pas de texte")


# ── t389 : la demande de l'écran Créer ──────────────────────────────────────

IMG = settings.images_path


def test_la_demande_est_validee_puis_chiffree_tir_par_tir():
    d = SC.valider({"mode": "multi", "moteurs": ["tripo-p2", "trellis-2", "tripo-p2"], "images": ["chevalier.png",
                    "caisse.png"], "quantite": 2, "reglages": {"trellis-2": {"resolution": 512}}}, IMG)
    assert d["moteurs"] == ["tripo-p2", "trellis-2"] and d["images"] == ["chevalier.png", "caisse.png"]
    t = SC.tirs(d)
    assert len(t) == 8 and [x["engine"] for x in t[:4]] == ["tripo-p2", "tripo-p2", "trellis-2", "trellis-2"]
    assert t[2]["reglages"] == {"resolution": 512} and t[0]["image_filename"] == "chevalier.png"
    dv = SC.devis(d)
    assert dv["tirs"] == 8 and dv["total_usd"] == round(4 * 1.10 + 4 * 0.25, 4)
    assert [l["unitaire_usd"] for l in dv["lignes"]] == [1.10, 0.25]


def test_les_refus_de_la_demande():
    for corps, motif in (({"moteurs": []}, "au moins un"), ({"moteurs": ["inconnu"]}, "inconnu"),
                         ({"moteurs": ["tripo"], "images": ["absente.png"]}, "introuvable"),
                         ({"moteurs": ["tripo"], "quantite": 5, "images": ["caisse.png"]}, "de 1 à 4"),
                         ({"mode": "texte", "moteurs": ["tripo-p2"]}, "description"),
                         ({"mode": "texte", "moteurs": ["trellis-2"], "prompt": "x"}, "ne génèrent pas"),
                         ({"mode": "image", "moteurs": ["tripo"], "images": ["caisse.png", "chevalier.png"]}, "une seule"),
                         ({"moteurs": ["tripo"], "images": ["caisse.png"], "pose": "x-pose"}, "pose"),
                         ({"moteurs": ["tripo-p2"], "images": ["caisse.png"], "reglages": {"tripo-p2": {"quad": 3}}}, "booléen"),
                         ({"mode": "x", "moteurs": ["tripo"]}, "mode")):
        refuse(SC.valider, corps, IMG, motif=motif)
    big = {"mode": "multi", "moteurs": ["tripo", "trellis", "rodin", "triposr"], "images": ["caisse.png", "chevalier.png"],
           "quantite": 4}
    refuse(SC.valider, big, IMG, motif="au plus")


# ── la route ────────────────────────────────────────────────────────────────

def _client():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def _depenses():
    from sqlalchemy import select
    from app.services import plafonds
    from app.services.storage import Depense
    async with plafonds._registre() as s:
        return [(d.ref, d.estime_usd, d.categorie) for d in (await s.execute(select(Depense))).scalars().all()]


def test_la_route_refuse_dans_l_ordre_puis_lance_n_tirs():
    lances = []

    async def faux_generate(payload, job_id, on_step=None):
        lances.append((job_id, payload))
        return {"glb": "x", "files": {}, "shots": [], "engine": payload["engine"]}

    corps = {"mode": "image", "moteurs": ["tripo-p2", "hunyuan-3.1"], "images": ["chevalier.png"], "quantite": 2}

    async def go():
        from app.services.storage import init_db
        await init_db()
        async with _client() as c:
            r400 = await c.post("/api/studio3d/creer", json={"moteurs": []})
            r503 = await c.post("/api/studio3d/creer", json=corps)
            settings.FAL_KEY = "cle-de-banc"
            rdev = await c.post("/api/studio3d/creer/devis", json=corps)
            rpose = await c.post("/api/studio3d/creer/devis", json={**corps, "pose": "a-pose"})   # ni Tripo P2 ni Hunyuan 3.1 n'ont de pose
            r409 = await c.post("/api/studio3d/creer", json=corps)
            avant = await _depenses()
            import app.services.asset3d_service as _A
            vrai = _A.generate_asset3d
            _A.generate_asset3d = faux_generate
            try:
                rok = await c.post("/api/studio3d/creer", json={**corps, "confirme_cout": True},
                                   headers={"X-DZ-Plafond": "confirme"})
                await asyncio.sleep(0.3)
            finally:
                _A.generate_asset3d = vrai
                settings.FAL_KEY = ""
            return r400, r503, rdev, r409, avant, rok, await _depenses(), rpose
    r400, r503, rdev, r409, avant, rok, apres, rpose = asyncio.run(go())
    assert rpose.status_code == 400                      # pose refusée DÈS le devis, avant toute confirmation
    assert (r400.status_code, r503.status_code, rdev.status_code, r409.status_code) == (400, 503, 200, 409)
    assert "fal" in r503.json()["detail"]
    assert r409.json()["detail"]["devis"]["total_usd"] == rdev.json()["total_usd"] == round(2 * 1.10 + 2 * 0.375, 4)
    assert avant == []                                   # rien n'est écrit avant l'accord
    assert rok.status_code == 200, rok.text
    tirs = rok.json()["tirs"]
    assert len(tirs) == 4 and len({t["job"] for t in tirs}) == 4
    assert sorted(p["engine"] for _j, p in lances) == ["hunyuan-3.1", "hunyuan-3.1", "tripo-p2", "tripo-p2"]
    assert all("exemplaire" not in p and p["image_filename"] == "chevalier.png" for _j, p in lances)
    assert len([d for d in apres if d[0].startswith("asset3d:")]) == 4 and all(d[2] == "moteurs3d" for d in apres)


def test_le_registre_sert_les_schemas_sans_aucune_url_de_fournisseur():
    async def go():
        async with _client() as c:
            return (await c.get("/api/assets3d/engines")).json()
    j = asyncio.run(go())
    par = {e["id"]: e for e in j["engines"]}
    assert par["tripo-p2"]["reglages"] and par["tripo-p2"]["texte"] is True and par["trellis-2"]["texte"] is False
    assert not any(k.startswith("endpoint") for e in j["engines"] for k in e)
    assert par["meshy-7.1"]["pose"] == "moteur" and par["tripo-p2"]["pose"] is None


# ── la page et le maillon ───────────────────────────────────────────────────

def test_le_maillon_pose_l_hote_et_range_l_ancien_formulaire_et_se_defait():
    import patch_bundle_dzcreer3d as P
    import _i18n_l1_aide as AIDE
    b = P.BUNDLE.read_bytes().decode("utf-8")
    assert b.count(P.MARKER) == 1 and b.count('"data-dz-creer3d-hote":"1"') == 1
    assert b.count('"data-dz-creer3d-ancien":"1",children:r.jsx(DzGameAssets,{variant:e})') == 1
    avant = AIDE.avant_dzcreer3d(b)
    assert P.MARKER not in avant and avant.count(P._ANCRE) == 1 and P.appliquer(avant) == b
    assert P.MARKER not in AIDE.avant_dzapparence(b)            # la chaîne défait la queue d'abord
    assert b.count("x.useState(") == 731 and b.count(P.CONFIRMER) == 30


def test_le_script_est_copie_charge_et_ses_cles_existent():
    src = (RACINE / "frontend/shared/dz-creer3d.js").read_bytes()
    assert (RACINE / "frontend/dist/shared/dz-creer3d.js").read_bytes() == src
    html = (RACINE / "frontend/dist/index.html").read_text(encoding="utf-8")
    assert html.count('<script src="/shared/dz-creer3d.js"></script>') == 1
    assert html.index("/shared/dz-pose3d.js") < html.index("/shared/dz-creer3d.js")
    js = src.decode("utf-8")
    dico = json.loads((RACINE / "frontend/shared/i18n/creer3d.json").read_text(encoding="utf-8"))
    cles = {k for k in re.findall(r'T\("(creer3d\.[a-z0-9_.]+)"', js) if not k.endswith(".")}
    assert len(cles) > 20
    for k in cles:
        assert k in dico, k
    for fam, ids in {"mode": ["image", "texte", "multi"], "aide": ["image", "texte", "multi"],
                     "filtre": ["tous", "rigges", "non_rigges"], "pose": ["aucune", "a_pose", "t_pose"],
                     "ouvrir": ["preparer", "texture", "rig", "animer", "decor"],
                     "badge": sorted({e["badge"] for e in M.MOTEURS.values() if e["badge"]})}.items():
        for i in ids:
            assert f"creer3d.{fam}.{i}" in dico, (fam, i)
    for k, v in dico.items():
        assert len(k.split(".")) == 3 and v["fr"] and v["en"], k
        assert set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"])), k
    assert "window.confirm" not in js and "border-radius" not in js
    assert js.index("__dzDialogue") < js.index('jpost("/api/studio3d/creer", corps)')
    assert "confirme_cout = true" in js


def test_le_calcul_de_l_ecran_sous_node():
    node = shutil.which("node")
    if not node:
        print("    (node absent : banc JS sauté)")
        return
    r = subprocess.run([node, str(RACINE / "frontend/shared/qa/creer3d.test.mjs")], capture_output=True, text=True,
                       encoding="utf-8")
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
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (Créer 3D + moteurs neufs)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
