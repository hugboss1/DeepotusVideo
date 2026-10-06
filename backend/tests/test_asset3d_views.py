# -*- coding: utf-8 -*-
"""T106 (plan-moteurs-3d T6, P5) — les vues AVANT le tir. fal stubbé (upload, Seedream, moteur, rembg,
téléchargements) : le banc ne sort jamais. Service : préparer écrit shot_i.png + views.json sans AUCUN moteur, rejouer ne
touche qu'une vue, détourer en local est gratuit et écrit un alpha, tirer envoie les vues validées (dans l'ordre imposé
du moteur, même quand une vue a raté) et ré-envoie celles retouchées sur le disque. Routes : tout refus AVANT la garde
(clé fal, job, état, index, double clic), la garde AVANT le job (402 sans JobRecord), le tir chiffré SANS les vues (déjà
payées), aucune ligne Depense sur un refus.
Run : python tests/test_asset3d_views.py (depuis backend/)"""
import asyncio, io, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzvues_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["ELEVENLABS_API_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loguru import logger                                        # noqa: E402
logger.remove()
from PIL import Image                                            # noqa: E402
from app.config import settings                                  # noqa: E402
from app.services import asset3d_service as A3, gltf_builder     # noqa: E402
from app.services import asset3d_views as V                      # noqa: E402
from app.services import sprite_service                          # noqa: E402
from app.services.storage import init_db                         # noqa: E402

EDITS, MOTEURS, UPLOADS, REMBG = [], [], [], []
ECHEC_VUE = set()          # prompts (sous-chaînes) qui font échouer Seedream
_BASE = []


def _pret():
    if not _BASE:
        asyncio.run(init_db()); _BASE.append(1)


async def _faux_upload(p):
    UPLOADS.append(pathlib.Path(p).name)
    return f"https://fal.test/up/{len(UPLOADS)}/{pathlib.Path(p).name}"


async def _faux_seedream(url, prompt):
    if any(s in prompt for s in ECHEC_VUE):
        raise RuntimeError("seedream KO")
    EDITS.append(prompt)
    return f"https://fal.test/vue{len(EDITS)}.png"


async def _faux_moteur(engine, args, endpoint=None):
    MOTEURS.append((engine, args))
    return {"mesh_url": "https://fal.test/m.glb", "format_urls": {}, "texture_urls": {}, "preview_url": None}


async def _faux_rembg(url):
    REMBG.append(url)
    return "https://fal.test/rembg.png"


def _faux_download(url, dest, timeout=120):
    if str(dest).endswith(".glb"):
        dest.write_bytes(gltf_builder.build_glb({}, None, "cube", "m"))
    else:
        # un sujet carré sur fond uni : le masque des quatre coins le trouve ; la couleur dépend de l'URL pour qu'une
        # vue rejouée change VRAIMENT d'octets
        teinte = (sum(map(ord, url)) * 37) % 200
        im = Image.new("RGB", (64, 64), (242, 239, 233))
        im.paste(Image.new("RGB", (32, 32), (teinte, 90, 40)), (16, 16))
        b = io.BytesIO(); im.save(b, "PNG"); dest.write_bytes(b.getvalue())
    return True


A3._upload = _faux_upload
A3._seedream_edit = _faux_seedream
A3._run_engine = _faux_moteur
A3._download = _faux_download
sprite_service._rembg_api = _faux_rembg


def _source(nom="src.png"):
    b = io.BytesIO(); Image.new("RGB", (64, 64), (200, 90, 40)).save(b, "PNG")
    (settings.images_path / nom).write_bytes(b.getvalue())
    return nom


def _vider():
    EDITS.clear(); MOTEURS.clear(); UPLOADS.clear(); REMBG.clear(); ECHEC_VUE.clear()


def _dir(job):
    return settings.outputs_path / "assets3d" / job


def _vj(job):
    return json.loads((_dir(job) / "views.json").read_text("utf-8"))


# ── service ──────────────────────────────────────────────────────────────────

def test_preparer_genere_les_vues_et_ne_tire_PAS():
    _vider()
    r = asyncio.run(V.preparer_vues({"image_filename": _source(), "engine": "tripo", "views": 4,
                                     "subject": "un poulpe prophète"}, "vu_prep"))
    assert r["vues"] == 5 and len(EDITS) == 4, (r, EDITS)
    assert MOTEURS == [], "AUCUN moteur ne doit tourner avant le tir"
    for i in range(5):
        assert (_dir("vu_prep") / f"shot_{i}.png").is_file(), i
    vj = _vj("vu_prep")
    assert vj["etat"] == "en_attente" and len(vj["vues"]) == 5, vj
    assert vj["vues"][0]["role"] == "source" and vj["vues"][0]["prompt"] is None
    assert [v["cle"] for v in vj["vues"]] == ["source", "front", "back", "left", "right"], vj
    assert "poulpe" in vj["vues"][1]["prompt"]
    assert all(v["url"] for v in vj["vues"]), vj
    assert not (_dir("vu_prep") / "asset.json").exists(), "pas de manifeste avant le tir"


def test_une_vue_ratee_reste_dans_le_jeu_avec_son_erreur():
    _vider()
    ECHEC_VUE.add("seen directly from behind")
    asyncio.run(V.preparer_vues({"image_filename": _source(), "engine": "tripo", "views": 4}, "vu_ko"))
    vj = _vj("vu_ko")
    dos = vj["vues"][2]
    assert dos["cle"] == "back" and dos["file"] is None and dos["url"] is None and dos["erreur"], dos
    assert not (_dir("vu_ko") / "shot_2.png").exists()


def test_rejouer_une_vue_ne_touche_que_celle_la():
    _vider()
    asyncio.run(V.preparer_vues({"image_filename": _source(), "engine": "tripo", "views": 3}, "vu_rej"))
    d = _dir("vu_rej")
    avant, autre = (d / "shot_1.png").read_bytes(), (d / "shot_2.png").read_bytes()
    _vider()
    r = asyncio.run(V.rejouer_vue("vu_rej", 2, prompt="seen from behind, exact"))
    assert len(EDITS) == 1 and EDITS[0] == "seen from behind, exact", EDITS
    assert (d / "shot_2.png").read_bytes() != autre, "la vue 2 devait changer"
    assert (d / "shot_1.png").read_bytes() == avant, "la vue 1 ne devait PAS bouger"
    vj = _vj("vu_rej")
    assert vj["vues"][2]["rejeux"] == 1 and vj["vues"][1]["rejeux"] == 0, vj
    assert r["index"] == 2 and r["rejeux"] == 1, r


def test_rejouer_repare_une_vue_ratee():
    _vider()
    ECHEC_VUE.add("seen directly from behind")
    asyncio.run(V.preparer_vues({"image_filename": _source(), "engine": "tripo", "views": 2}, "vu_rep"))
    ECHEC_VUE.clear()
    asyncio.run(V.rejouer_vue("vu_rep", 2))            # le prompt d'origine, conservé malgré l'échec
    v = _vj("vu_rep")["vues"][2]
    assert v["file"] == "shot_2.png" and v["url"] and "erreur" not in v, v


def test_les_refus_du_service():
    _vider()
    asyncio.run(V.preparer_vues({"image_filename": _source(), "engine": "tripo", "views": 1}, "vu_ref"))
    for idx, mot in ((0, "source"), (5, "inconnue")):
        try:
            asyncio.run(V.rejouer_vue("vu_ref", idx)); raise AssertionError(f"vue {idx} acceptée")
        except ValueError as e:
            assert mot in str(e).lower(), e
    try:
        asyncio.run(V.preparer_vues({"image_filename": "absente.png", "engine": "tripo"}, "vu_abs"))
        raise AssertionError("image absente acceptée")
    except ValueError as e:
        assert "library" in str(e).lower(), e
    try:
        V.lire_vues("pas_de_vues"); raise AssertionError("job inconnu accepté")
    except FileNotFoundError:
        pass
    assert not EDITS[1:], "aucun refus ne dépense"


def test_le_detourage_local_est_gratuit_et_ecrit_un_alpha():
    _vider()
    asyncio.run(V.preparer_vues({"image_filename": _source(), "engine": "tripo", "views": 2}, "vu_det"))
    n_up = len(UPLOADS)
    r = asyncio.run(V.detourer_vue("vu_det", 1, via="local"))
    assert r["via"] == "local" and r["usd"] == 0.0, r
    im = Image.open(_dir("vu_det") / "shot_1.png")
    assert im.mode == "RGBA", im.mode
    a = im.getchannel("A")
    assert a.getpixel((0, 0)) == 0 and a.getpixel((32, 32)) == 255, "fond transparent, sujet opaque"
    v = _vj("vu_det")["vues"][1]
    assert v["detoure"] == "local" and v["a_renvoyer"] is True, v
    assert len(UPLOADS) == n_up and not REMBG, "le local ne contacte pas fal"


def test_le_detourage_fal_part_du_fichier_courant():
    _vider()
    asyncio.run(V.preparer_vues({"image_filename": _source(), "engine": "tripo", "views": 1}, "vu_dfal"))
    r = asyncio.run(V.detourer_vue("vu_dfal", 1, via="fal"))
    assert r["via"] == "fal" and r["usd"] > 0, r
    assert len(REMBG) == 1 and REMBG[0].endswith("shot_1.png"), REMBG   # l'URL d'un envoi du fichier, pas l'ancienne
    v = _vj("vu_dfal")["vues"][1]
    assert v["url"] == "https://fal.test/rembg.png" and not v.get("a_renvoyer"), v


def test_tirer_envoie_les_vues_validees_et_ecrit_le_maillage():
    _vider()
    asyncio.run(V.preparer_vues({"image_filename": _source(), "engine": "tripo", "views": 4}, "vu_tir"))
    _vider()
    r = asyncio.run(V.tirer_vues("vu_tir"))
    assert len(MOTEURS) == 1 and MOTEURS[0][0] == "tripo", MOTEURS
    assert (_dir("vu_tir") / "model.glb").is_file() and r["glb"], r
    assert (_dir("vu_tir") / "asset.json").is_file() and (_dir("vu_tir") / "report.json").is_file()
    man = A3.read_manifest("vu_tir")
    assert man["multiview"] is True and man["views"] == 4 and man["shots"][0] == "shot_0.png", man
    assert _vj("vu_tir")["etat"] == "tire"
    assert not EDITS and not UPLOADS, "tirer ne régénère ni ne ré-envoie une vue intacte"


def test_tirer_respecte_l_ordre_du_moteur_meme_avec_une_vue_ratee():
    """H3.1 exige [front, left, back, right]. Si le dos rate, la liste positionnelle [source, front, left, right]
    étiquetée par position appelait `left` « back » : on garde la CLÉ de chaque vue."""
    _vider()
    ECHEC_VUE.add("seen directly from behind")
    asyncio.run(V.preparer_vues({"image_filename": _source(), "engine": "tripo-h3.1", "views": 4}, "vu_ord"))
    par_cle = {v["cle"]: v["url"] for v in _vj("vu_ord")["vues"] if v["url"]}
    asyncio.run(V.tirer_vues("vu_ord"))
    envoyees = next(x for x in MOTEURS[0][1].values() if isinstance(x, list))
    assert envoyees == [par_cle["front"], par_cle["left"], par_cle["right"]], (envoyees, par_cle)


def test_tirer_renvoie_une_vue_detouree_en_local():
    _vider()
    asyncio.run(V.preparer_vues({"image_filename": _source(), "engine": "tripo", "views": 2}, "vu_ren"))
    asyncio.run(V.detourer_vue("vu_ren", 2, via="local"))
    ancienne = _vj("vu_ren")["vues"][2]["url"]
    _vider()
    asyncio.run(V.tirer_vues("vu_ren"))
    assert UPLOADS == ["shot_2.png"], UPLOADS
    envoye = json.dumps(MOTEURS[0][1])
    assert ancienne not in envoye and "shot_2.png" in envoye, envoye


def test_on_ne_tire_pas_deux_fois_le_meme_jeu_de_vues():
    _vider()
    asyncio.run(V.preparer_vues({"image_filename": _source(), "engine": "tripo", "views": 1}, "vu_2x"))
    asyncio.run(V.tirer_vues("vu_2x"))
    for f in (lambda: V.tirer_vues("vu_2x"), lambda: V.rejouer_vue("vu_2x", 1),
              lambda: V.detourer_vue("vu_2x", 1, via="local")):
        try:
            asyncio.run(f()); raise AssertionError("aurait dû refuser")
        except ValueError as e:
            assert "déjà" in str(e), e


def test_generate_garde_la_cle_de_chaque_vue_quand_une_rate():
    """La moitié aval extraite (tirer_moteur) sert aussi le chemin d'un clic : il étiquetait par position."""
    _vider()
    ECHEC_VUE.add("seen directly from behind")
    asyncio.run(A3.generate_asset3d({"image_filename": _source(), "engine": "tripo-h3.1", "multiview": True,
                                     "views": 4}, "gen_ord"))
    envoyees = next(x for x in MOTEURS[0][1].values() if isinstance(x, list))
    assert len(envoyees) == 3 and envoyees[0].startswith("https://fal.test/vue"), envoyees
    # front=vue1, left=vue2, right=vue3 : le dos a raté, rien ne prend sa place
    assert envoyees == ["https://fal.test/vue1.png", "https://fal.test/vue2.png", "https://fal.test/vue3.png"], envoyees
    assert A3.read_manifest("gen_ord")["shots"] == ["shot_0.png", "shot_1.png", "shot_3.png", "shot_4.png"]


# ── routes ───────────────────────────────────────────────────────────────────

def test_routes_refusent_avant_la_garde_puis_gardent():
    _pret()
    from httpx import AsyncClient, ASGITransport
    from sqlalchemy import func, select
    from app.main import app
    from app.services import plafonds as PL
    from app.services.storage import Depense, JobRecord, async_session_factory
    src = _source("route.png")

    async def compter():
        async with async_session_factory() as s:
            return ((await s.execute(select(func.count()).select_from(Depense))).scalar(),
                    (await s.execute(select(func.count()).select_from(JobRecord))).scalar())

    async def attendre(c, jid):
        for _ in range(200):
            j = (await c.get(f"/api/jobs/{jid}")).json()
            if j.get("status") in ("done", "failed"):
                return j
            await asyncio.sleep(0.02)
        return j

    async def main():
        o = {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            avant = await compter()
            o["img"] = (await c.post("/api/assets/3d/views", json={"image_filename": "absente.png"})).status_code
            o["moteur"] = (await c.post("/api/assets/3d/views", json={"image_filename": src, "engine": "x"})).status_code
            o["nvues"] = (await c.post("/api/assets/3d/views", json={"image_filename": src, "views": "deux"})).status_code
            fk, settings.FAL_KEY = settings.FAL_KEY, "  "
            o["fal_prep"] = (await c.post("/api/assets/3d/views", json={"image_filename": src})).status_code
            settings.FAL_KEY = fk
            o["404_get"] = (await c.get("/api/assets/3d/inconnu/views")).status_code
            o["404_tir"] = (await c.post("/api/assets/3d/inconnu/tirer")).status_code
            o["404_rej"] = (await c.post("/api/assets/3d/inconnu/views/1/rejouer", json={})).status_code
            o["refus_sans_depense"] = (await compter()) == avant

            PL.enregistrer({"par_moteur": {"fal": 0.01}})
            o["402"] = (await c.post("/api/assets/3d/views", json={"image_filename": src, "views": 4})).status_code
            o["apres_402"] = (await compter())[1] == avant[1]
            PL.enregistrer({"par_moteur": {"fal": 0}})

            _vider()
            r = await c.post("/api/assets/3d/views", json={"image_filename": src, "engine": "tripo", "views": 3,
                                                          "subject": "un poulpe"})
            o["prep"] = (r.status_code, r.json())
            job = r.json()["job"]
            o["prep_job"] = await attendre(c, r.json()["job_id"])
            o["moteurs_apres_prep"] = len(MOTEURS)
            o["get"] = (await c.get(f"/api/assets/3d/{job}/views")).json()
            o["liste"] = (await c.get("/api/assets/3d/views")).json()

            o["rej_src"] = (await c.post(f"/api/assets/3d/{job}/views/0/rejouer", json={})).status_code
            o["rej_9"] = (await c.post(f"/api/assets/3d/{job}/views/9/rejouer", json={})).status_code
            settings.FAL_KEY = ""
            o["fal_rej"] = (await c.post(f"/api/assets/3d/{job}/views/1/rejouer", json={})).status_code
            o["fal_dfal"] = (await c.post(f"/api/assets/3d/{job}/views/1/detourer", json={"via": "fal"})).status_code
            o["fal_tir"] = (await c.post(f"/api/assets/3d/{job}/tirer")).status_code
            # le détourage LOCAL n'a besoin d'aucune clé
            o["det_local"] = (await c.post(f"/api/assets/3d/{job}/views/1/detourer", json={})).json()
            settings.FAL_KEY = fk
            o["det_src"] = (await c.post(f"/api/assets/3d/{job}/views/0/detourer", json={})).status_code

            r = await c.post(f"/api/assets/3d/{job}/views/2/rejouer", json={"prompt": "seen from behind, exact"})
            o["rej"] = (r.status_code, await attendre(c, r.json()["job_id"]))

            async with async_session_factory() as s0:   # un job vivant sur ce jeu de vues → double clic refusé
                s0.add(JobRecord(id="vues-vivant", status="generating_video", progress=50, title="x",
                                 image_filename=f"asset3d_{job}", provider="asset3d", current_step="x"))
                await s0.commit()
            o["double_rej"] = (await c.post(f"/api/assets/3d/{job}/views/1/rejouer", json={})).status_code
            o["double_tir"] = (await c.post(f"/api/assets/3d/{job}/tirer")).status_code
            async with async_session_factory() as s0:
                (await s0.get(JobRecord, "vues-vivant")).status = "failed"
                await s0.commit()

            dep_avant_tir = (await compter())[0]
            r = await c.post(f"/api/assets/3d/{job}/tirer")
            o["tir"] = (r.status_code, r.json(), await attendre(c, r.json()["job_id"]))
            o["retir"] = (await c.post(f"/api/assets/3d/{job}/tirer")).status_code
            o["glb"] = (await c.get(f"/api/assets/3d/{job}/glb")).status_code
            async with async_session_factory() as s:
                deps = (await s.execute(select(Depense).order_by(Depense.id))).scalars().all()
                o["dep_tir"] = [(d.op, d.libelle if hasattr(d, "libelle") else "", d.estime_usd)
                                for d in deps][dep_avant_tir:]
                o["dep_ops"] = [d.op for d in deps]
        return o

    o = asyncio.run(main())
    assert o["img"] == 400 and o["moteur"] == 400 and o["nvues"] == 400, o
    assert o["fal_prep"] == 400, o["fal_prep"]
    assert o["404_get"] == 404 and o["404_tir"] == 404 and o["404_rej"] == 404, o
    assert o["refus_sans_depense"], "un refus n'inscrit ni dépense ni job"
    assert o["402"] == 402 and o["apres_402"], (o["402"], o["apres_402"])
    st, p = o["prep"]
    assert st == 200 and p["status"] == "queued" and p["job"] and p["usd_estime"] > 0, o["prep"]
    assert o["prep_job"]["status"] == "done", o["prep_job"]
    assert o["moteurs_apres_prep"] == 0, "préparer ne lance aucun moteur"
    assert o["get"]["etat"] == "en_attente" and len(o["get"]["vues"]) == 4, o["get"]
    assert any(x["job"] == p["job"] and x["etat"] == "en_attente" for x in o["liste"]["jeux"]), o["liste"]
    assert o["rej_src"] == 400 and o["rej_9"] == 400, (o["rej_src"], o["rej_9"])
    assert o["fal_rej"] == 400 and o["fal_dfal"] == 400 and o["fal_tir"] == 400, o
    assert o["det_local"]["via"] == "local" and o["det_local"]["usd"] == 0.0, o["det_local"]
    assert o["det_src"] == 400, o["det_src"]
    assert o["rej"][0] == 200 and o["rej"][1]["status"] == "done", o["rej"]
    assert o["double_rej"] == 409 and o["double_tir"] == 409, (o["double_rej"], o["double_tir"])
    st, t, tj = o["tir"]
    assert st == 200 and t["status"] == "queued" and tj["status"] == "done", o["tir"]
    assert o["retir"] == 409, o["retir"]
    assert o["glb"] == 200, o["glb"]
    # le tir est chiffré SANS les vues : elles ont été payées à la préparation et au rejeu
    assert o["dep_tir"] and all(op == "asset3d" for op, _, _ in o["dep_tir"]), o["dep_tir"]
    assert abs(sum(u for _, _, u in o["dep_tir"]) - 0.30) < 1e-6, o["dep_tir"]
    assert o["dep_ops"].count("asset3d_views") == 2, o["dep_ops"]     # préparation + un rejeu


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (asset3d_views)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
