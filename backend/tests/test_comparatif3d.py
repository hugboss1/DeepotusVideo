# -*- coding: utf-8 -*-
"""t344 (lot Scenario B9, 29/10/2026) — banc comparatif des moteurs image → 3D.

Une image, N moteurs SIMULÉS (aucun appel réseau) : l'ordre des refus du tir (400, 503 clé nommée, 409 devis total,
402 plafond sur le TOTAL — même quand chaque tir seul passerait), puis N jobs en parallèle et le tableau MESURÉ
(triangles, arêtes ouvertes, non-manifold, étanche, taille, temps, coût estimé, réel). Le mode « existants » rejoue des
GLB déjà générés sans rien dépenser. « Garder celui-ci » range la vue capturée dans la Bibliothèque avec sa provenance.
L'outil d'agent lit sans écrire. L'écran : page à part, dialogue maison avant le POST payant, clés FR/EN.
Run : python tests/test_comparatif3d.py (depuis backend/)"""
import asyncio, base64, io, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzcmp3d_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = ""; os.environ["ELEVENLABS_API_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loguru import logger                                         # noqa: E402
logger.remove()
from app.config import settings                                   # noqa: E402
from app.services import comparatif3d as C3, print3d              # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]


# ── géométrie de banc ────────────────────────────────────────────────────────

def boite(c=(0, 0, 0), d=(1, 1, 1)):
    x0, y0, z0 = (c[i] - d[i] / 2 for i in range(3))
    x1, y1, z1 = (c[i] + d[i] / 2 for i in range(3))
    P = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    F = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6), (1, 2, 6), (1, 6, 5),
         (3, 0, 4), (3, 4, 7)]
    return [(P[a], P[b], P[e]) for a, b, e in F]


def ferme():          # 12 triangles, étanche
    return boite()


def ouvert():         # une face retirée : 4 arêtes de bord
    return boite()[2:]


def non_manifold():   # une ailette sur une arête : 3 triangles la partagent
    t = boite()
    a, b = t[0][0], t[0][1]
    return t + [(a, b, (5.0, 5.0, 5.0))]


GEOS = {"tripo": ferme, "trellis": ouvert, "triposr": non_manifold, "hunyuan": ferme}


def glb(tris) -> bytes:
    return print3d.glb_de_pieces([("m", tris)])


def png(couleur=(200, 80, 40)) -> bytes:
    from PIL import Image
    b = io.BytesIO()
    Image.new("RGB", (32, 32), couleur).save(b, "PNG")
    return b.getvalue()


IMAGE = "robot_source.png"
(pathlib.Path(_tmp, "images") / IMAGE).write_bytes(png())


def _job(nom, tris, engine="tripo", image=IMAGE):
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(glb(tris))
    (d / "asset.json").write_text(json.dumps({"engine": engine, "texture_mode": "standard", "image_filename": image,
                                              "created_at": "2026-10-20T10:00:00+00:00"}), encoding="utf-8")
    return d


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


async def _jobs():
    from sqlalchemy import select
    from app.services.storage import JobRecord, async_session_factory, init_db
    await init_db()
    async with async_session_factory() as s:
        return (await s.execute(select(JobRecord))).scalars().all()


# ── le service pur ───────────────────────────────────────────────────────────

def test_valider_moteurs_refuse_un_seul_un_inconnu_et_dedoublonne():
    assert C3.valider_moteurs(["tripo", "TRELLIS", "tripo"]) == ["tripo", "trellis"]
    for mauvais in (["tripo"], ["tripo", "tripo"], ["tripo", "nope"], "tripo", None):
        try:
            C3.valider_moteurs(mauvais)
        except ValueError:
            continue
        raise AssertionError(mauvais)


def test_le_devis_additionne_les_tirs_et_dit_la_cle_sans_griser():
    d = C3.devis(["tripo", "trellis", "hunyuan-local"], True, cle_fal=False, local_ok=False)
    assert d["n"] == 3 and abs(d["total_usd"] - (0.3 + 0.35 + 0.0)) < 1e-9, d
    par = {l["moteur"]: l for l in d["lignes"]}
    assert par["tripo"]["cle"] == "fal" and par["tripo"]["cle_ok"] is False
    assert par["hunyuan-local"]["cle"] == "local" and par["hunyuan-local"]["usd"] == 0.0
    sans_tex = C3.devis(["tripo", "trellis"], False, cle_fal=True)
    assert abs(sans_tex["total_usd"] - 0.55) < 1e-9 and sans_tex["lignes"][0]["cle_ok"] is True


def test_trier_met_l_inconnu_en_dernier_dans_les_deux_sens():
    L = [{"moteur": "a", "tris": 30}, {"moteur": "b", "tris": None}, {"moteur": "c", "tris": 10}]
    assert [l["moteur"] for l in C3.trier(L, "tris")] == ["c", "a", "b"]
    assert [l["moteur"] for l in C3.trier(L, "tris", desc=True)] == ["a", "c", "b"]
    try:
        C3.trier(L, "rm -rf")
    except ValueError:
        pass
    else:
        raise AssertionError("tri inconnu accepté")


def test_le_poster_est_un_png_borne():
    assert C3.lire_poster("data:image/png;base64," + base64.b64encode(png()).decode()) == png()
    for mauvais in ("", None, "data:image/png;base64,@@@", base64.b64encode(b"GIF89a....").decode()):
        try:
            C3.lire_poster(mauvais)
        except ValueError:
            continue
        raise AssertionError(mauvais)


# ── le tir : N moteurs en un clic ───────────────────────────────────────────

def test_le_tir_refuse_dans_l_ordre_puis_lance_n_jobs_et_mesure():
    from app.services import asset3d_service as A3, plafonds
    appels = []

    async def faux_upload(p):
        appels.append(("upload", pathlib.Path(p).name))
        return "https://fal.example/source.png"

    async def faux_run(engine, args, endpoint=None):
        appels.append(("fal", engine))
        if engine == "hunyuan":
            raise RuntimeError("fal.ai: moteur en panne (simulé)")
        return {"mesh_url": f"https://fal.example/{engine}.glb", "format_urls": {}, "texture_urls": {},
                "preview_url": None}

    def faux_download(url, dest, timeout=120):
        nom = url.rsplit("/", 1)[-1].split(".")[0]
        pathlib.Path(dest).write_bytes(glb(GEOS[nom]()))
        return True

    vieux = (A3._upload, A3._run_engine, A3._download)
    A3._upload, A3._run_engine, A3._download = faux_upload, faux_run, faux_download
    corps = {"image_filename": IMAGE, "moteurs": ["tripo", "trellis", "triposr", "hunyuan"], "textures": True}

    async def main():
        o = {}
        await _jobs()                                                   # init_db : la table des jobs existe
        async with _client() as c:
            o["un_seul"] = (await c.post("/api/comparatif3d", json={**corps, "moteurs": ["tripo"]})).status_code
            o["sans_image"] = (await c.post("/api/comparatif3d", json={**corps, "image_filename": "x.png"})).status_code
            r = await c.post("/api/comparatif3d", json={**corps, "confirme_cout": True})
            o["sans_cle"] = (r.status_code, r.json())
            settings.FAL_KEY = "cle-de-banc"
            r = await c.post("/api/comparatif3d", json=corps)
            o["sans_confirme"] = (r.status_code, r.json())
            o["dev"] = (await c.post("/api/comparatif3d/devis", json=corps)).json()
            # chaque tir seul (≤ 0,48 $) passe sous 0,60 $ ; le TOTAL (1,20 $) non : le refus vient du total
            plafonds.enregistrer({"par_moteur": {"fal": 0.6}})
            r = await c.post("/api/comparatif3d", json={**corps, "confirme_cout": True})
            o["plafond"] = (r.status_code, r.json())
            o["rien_avant"] = (len(appels), await _depenses(), len(await _jobs()))
            r = await c.post("/api/comparatif3d", json={**corps, "confirme_cout": True},
                             headers={"X-DZ-Plafond": "confirme"})
            o["ok"] = (r.status_code, r.json())
            if r.status_code == 200:
                o["tab"] = (await c.get(f"/api/comparatif3d/{r.json()['id']}")).json()
            o["liste"] = (await c.get("/api/comparatif3d")).json()
            o["mauvais_id"] = (await c.get("/api/comparatif3d/pas-un-id")).status_code
            o["id_inconnu"] = (await c.get("/api/comparatif3d/c3d_0000000000")).status_code
        o["depenses"] = await _depenses()
        return o
    try:
        o = asyncio.run(main())
    finally:
        A3._upload, A3._run_engine, A3._download = vieux
        settings.FAL_KEY = ""
        plafonds.enregistrer({"par_moteur": {}})
    assert o["un_seul"] == 400 and o["sans_image"] == 400
    st, j = o["sans_cle"]
    assert st == 503 and "fal" in json.dumps(j), j
    st, j = o["sans_confirme"]
    assert st == 409 and abs(j["detail"]["devis"]["total_usd"] - 1.2) < 1e-9, j
    assert o["dev"]["total_usd"] == j["detail"]["devis"]["total_usd"]
    st, j = o["plafond"]
    assert st == 402, (st, j)
    assert o["rien_avant"] == (0, [], 0), o["rien_avant"]
    st, j = o["ok"]
    assert st == 200 and len(j["lignes"]) == 4, j
    tab = o["tab"]
    par = {l["moteur"]: l for l in tab["lignes"]}
    assert par["tripo"]["statut"] == "termine" and par["tripo"]["tris"] == 12 and par["tripo"]["ferme"] is True
    assert par["tripo"]["aretes_bord"] == 0 and par["tripo"]["aretes_non_manifold"] == 0
    assert par["trellis"]["tris"] == 10 and par["trellis"]["aretes_bord"] == 4 and par["trellis"]["ferme"] is False
    assert par["triposr"]["aretes_non_manifold"] == 1 and par["triposr"]["ferme"] is False
    assert par["hunyuan"]["statut"] == "echec" and "panne" in (par["hunyuan"]["erreur"] or "")
    for m in ("tripo", "trellis", "triposr"):
        l = par[m]
        assert l["octets"] > 0 and l["duree_s"] is not None and l["glb"] == f"/api/assets/3d/{l['job']}/version/1"
        assert l["usd_reel"] is None                                  # fal ne dit pas le réel : « non rapproché »
    assert par["tripo"]["usd_estime"] == 0.3 and tab["en_cours"] is False and tab["mode"] == "tir"
    # une garde PAR tir, rattachée à son job ; catégorie moteurs3d ; le total des lignes = le devis
    refs = sorted(r for r, _u, _c in o["depenses"])
    assert refs == sorted(f"asset3d:{l['job']}" for l in tab["lignes"]), (refs, o["depenses"])
    assert all(c == "moteurs3d" for _r, _u, c in o["depenses"])
    assert abs(sum(u for _r, u, _c in o["depenses"]) - 1.2) < 1e-9
    assert sum(1 for a in appels if a[0] == "fal") == 4 and tab["id"] in {x["id"] for x in o["liste"]["comparatifs"]}
    assert o["mauvais_id"] == 400 and o["id_inconnu"] == 404


def test_un_moteur_local_injoignable_refuse_en_503_avant_tout():
    from app.services import local3d_service
    vieux = local3d_service.joignable
    local3d_service.joignable = lambda: False

    async def main():
        async with _client() as c:
            r = await c.post("/api/comparatif3d", json={"image_filename": IMAGE, "moteurs": ["hunyuan-local",
                                                                                              "triposr"]})
            m = (await c.get("/api/comparatif3d/moteurs")).json()
        return r.status_code, m
    settings.FAL_KEY = "cle-de-banc"
    try:
        st, m = asyncio.run(main())
    finally:
        local3d_service.joignable = vieux
        settings.FAL_KEY = ""
    assert st == 503
    par = {l["moteur"]: l for l in m["lignes"]}
    assert par["hunyuan-local"]["cle_ok"] is False and "tripo" in par and par["tripo"]["usd"] > 0


# ── les modèles existants : gratuit ─────────────────────────────────────────

def test_comparer_des_modeles_existants_ne_depense_rien_et_mesure():
    _job("ex_ferme", ferme(), "tripo")
    _job("ex_ouvert", ouvert(), "trellis")
    imp = _job("import_vase_1234", non_manifold(), "import")

    async def main():
        await _jobs()
        o = {"avant": await _depenses()}
        async with _client() as c:
            o["modeles"] = (await c.get("/api/comparatif3d/modeles")).json()
            r = await c.post("/api/comparatif3d/existants",
                             json={"modeles": [{"job": "ex_ferme"}, "ex_ouvert", {"job": "import_vase_1234"}]})
            o["tab"] = (r.status_code, r.json())
            o["un"] = (await c.post("/api/comparatif3d/existants", json={"modeles": ["ex_ferme"]})).status_code
            o["trav"] = (await c.post("/api/comparatif3d/existants", json={"modeles": ["..", "ex_ferme"]})).status_code
            o["absent"] = (await c.post("/api/comparatif3d/existants",
                                        json={"modeles": ["ex_ferme", {"job": "ex_ouvert", "version": 4}]})).status_code
        o["apres"] = await _depenses()
        return o
    o = asyncio.run(main())
    noms = {m["job"] for m in o["modeles"]["modeles"]}
    assert {"ex_ferme", "ex_ouvert", "import_vase_1234"} <= noms and not any(n.startswith("_") for n in noms)
    st, tab = o["tab"]
    assert st == 200 and tab["mode"] == "existants", tab
    par = {l["job"]: l for l in tab["lignes"]}
    assert par["ex_ferme"]["ferme"] is True and par["ex_ouvert"]["aretes_bord"] == 4
    assert par["import_vase_1234"]["aretes_non_manifold"] == 1 and par["import_vase_1234"]["usd_estime"] is None
    assert par["ex_ouvert"]["usd_estime"] == 0.35 and all(l["statut"] == "termine" for l in tab["lignes"])
    assert (imp / "report.json").is_file()                            # la fiche absente est calculée (gratuit)
    assert o["un"] == 400 and o["trav"] == 400 and o["absent"] == 404
    assert o["avant"] == o["apres"]


def test_garder_celui_ci_range_le_gagnant_dans_la_bibliotheque_avec_provenance():
    _job("gd_a", ferme(), "tripo")
    _job("gd_b", ouvert(), "trellis")
    poster = "data:image/png;base64," + base64.b64encode(png((10, 200, 30))).decode()

    async def main():
        from app.services.storage import LibraryAsset, async_session_factory
        o = {}
        async with _client() as c:
            cid = (await c.post("/api/comparatif3d/existants", json={"modeles": ["gd_a", "gd_b"]})).json()["id"]
            o["etranger"] = (await c.post(f"/api/comparatif3d/{cid}/garder",
                                          json={"job": "ex_ferme", "poster": poster})).status_code
            o["mauvais"] = (await c.post(f"/api/comparatif3d/{cid}/garder",
                                         json={"job": "gd_a", "poster": "data:image/png;base64,AAAA"})).status_code
            r = await c.post(f"/api/comparatif3d/{cid}/garder", json={"job": "gd_a", "poster": poster})
            o["ok"] = (r.status_code, r.json())
            o["tab"] = (await c.get(f"/api/comparatif3d/{cid}")).json()
        async with async_session_factory() as s:
            row = await s.get(LibraryAsset, o["ok"][1].get("filename", "?"))
            o["row"] = None if row is None else (row.source, row.job_id, row.parent_filename, row.relation,
                                                 json.loads(row.recette or "{}"))
        return o
    o = asyncio.run(main())
    assert o["etranger"] == 404 and o["mauvais"] == 400
    st, j = o["ok"]
    assert st == 200 and j["filename"].startswith("shot_gd_a_comparatif"), j
    assert (settings.images_path / j["filename"]).read_bytes() == png((10, 200, 30))
    src, job, mere, rel, rec = o["row"]
    assert (src, job, mere, rel) == ("assets3d", "gd_a", IMAGE, "comparatif"), o["row"]
    assert rec["outil"] == "comparatif3d" and rec["mesures"]["tris"] == 12 and rec["rivaux"][0]["job"] == "gd_b"
    assert (settings.outputs_path / "assets3d" / "gd_a" / "vignette_v1.png").is_file()
    assert [l["gagnant"] for l in o["tab"]["lignes"]] == [True, False] and o["tab"]["gagnant"]["moteur"] == "tripo"


# ── l'agent : lecture seule ─────────────────────────────────────────────────

def test_l_outil_de_l_agent_lit_le_tableau_sans_ecrire():
    from app.services import agent_boites as B, agent_outils as ao
    assert B.verifier() == [], B.verifier()
    assert "comparatif3d_lire" in B.BOITES["assets3d"]["outils"] and ao.OUTILS["comparatif3d_lire"]["nature"] == "lecture"
    _job("ag_a", ferme(), "tripo")
    _job("ag_b", ouvert(), "trellis")
    c = C3.creer("existants", C3.preparer_existants(["ag_a", "ag_b"]))
    avant = sorted(p.name for p in C3.dossier().iterdir())
    vieux = list(B.BOITES["assets3d"]["agents"])
    B.BOITES["assets3d"]["agents"] = ["essai"]
    try:
        ctx = ao.Ctx(cid="c1", agent="essai", lang="fr")
        r = asyncio.run(ao.executer("comparatif3d_lire", {"id": c["id"], "tri": "aretes_bord"}, ctx))
        assert r["ok"] and [l["job"] for l in r["donnees"]["lignes"]] == ["ag_a", "ag_b"], r
        assert "étanche" in r["resume"] and "4 arêtes ouvertes" in r["resume"], r["resume"]
        dernier = asyncio.run(ao.executer("comparatif3d_lire", {}, ctx))
        assert dernier["ok"] and dernier["donnees"]["id"], dernier
        for mauvais in ({"id": "../x"}, {"id": "c3d_ffffffffff"}, {"id": c["id"], "tri": "x"}):
            assert asyncio.run(ao.executer("comparatif3d_lire", mauvais, ctx))["ok"] is False, mauvais
    finally:
        B.BOITES["assets3d"]["agents"] = vieux
    assert sorted(p.name for p in C3.dossier().iterdir()) == avant


# ── l'écran ──────────────────────────────────────────────────────────────────

def test_l_ecran_page_a_part_dialogue_avant_le_tir_et_cles_fr_en():
    import re
    html = (RACINE / "frontend/studio3d/comparer.html").read_text(encoding="utf-8")
    js = (RACINE / "frontend/studio3d/comparer.js").read_text(encoding="utf-8")
    calc = (RACINE / "frontend/studio3d/comparer_calc.js").read_text(encoding="utf-8")
    dico = json.loads((RACINE / "frontend/shared/i18n/comparatif3d.json").read_text(encoding="utf-8"))
    carte = json.loads((RACINE / "frontend/dist/assets/three/importmap.json").read_text(encoding="utf-8"))
    bloc = html.split('type="importmap"', 1)[1].split(">", 1)[1].split("</script>", 1)[0]
    assert json.loads(bloc) == carte
    for balise in ('<script src="/shared/dialogue.js"></script>', '<script src="/shared/dz-plafonds.js"></script>',
                   '<script src="/shared/dz-i18n.js"></script>', '<script src="/shared/icons/dz-icons.js"></script>'):
        assert balise in html, balise
    assert html.index("/shared/dialogue.js") < html.index('src="comparer.js"')
    cles = {k for k in re.findall(r'\bT\("([a-z0-9_.]+)"', js + calc) if not k.endswith(".")}
    assert len(cles) > 30, len(cles)
    for k in cles:
        assert "comparatif3d." + k in dico, k
    # les familles composées à l'exécution : « statut. » + statut, « mode. » + mode, rendus et vues des boutons
    for f in ("statut.en_cours", "statut.echec", "statut.absent", "statut.termine", "mode.tir", "mode.existants",
              "rendu.texture", "rendu.argile", "rendu.fil", "vue.libre", "vue.iso", "vue.face", "vue.profil",
              "vue.dessus"):
        assert "comparatif3d." + f in dico, f
    for k, v in dico.items():
        assert k.startswith("comparatif3d.") and len(k.split(".")) == 3, k
        assert v["fr"] and v["en"] and set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"])), k
    i_conf, i_post = js.index("D_.confirmer("), js.index('jpost("/api/comparatif3d", ')
    assert i_conf < i_post and "confirme_cout: true" in js
    # la page n'invente aucun prix : le total vient du devis du serveur
    assert "/api/comparatif3d/moteurs" in js and "totalCoches(d, " in js
    s3d = (RACINE / "frontend/studio3d/index.html").read_text(encoding="utf-8")
    assert 'href="/studio3d/comparer.html"' in s3d and "Comparer les moteurs" in s3d


def test_le_calcul_de_l_ecran_sous_node():
    node = shutil.which("node")
    if not node:
        print("    (node absent : banc JS sauté)")
        return
    r = subprocess.run([node, str(RACINE / "frontend/studio3d/qa/comparer.test.mjs")], capture_output=True,
                       text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (comparatif 3D)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
