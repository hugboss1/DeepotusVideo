# -*- coding: utf-8 -*-
"""t342 (lot Scenario B6 + B7, 29/10/2026) — pièces mobiles et budgets de triangles.

B6 : un maillage fait d'îlots (une caisse, quatre roues, un couvercle) se découpe en pièces NOMMÉES, chaque pièce un
nœud dont l'origine est au centre de la pièce ; le monde ne bouge pas, les matières et UV suivent. La voie IA (Tripo
sur fal) est SIMULÉE : clé, devis, `confirme_cout`, plafonds, puis la découpe par nœud. B7 : budgets par rôle et trois
densités (gltfpack réel embarqué), tableau triangles / octets / perte. Le banc relit les GLB ÉCRITS.
Run : python tests/test_pieces_budgets.py (depuis backend/)"""
import asyncio, io, json, math, os, pathlib, struct, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzpieces_")
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
from app.services import gltf_builder, mesh_edit, mesh_lod, mesh_optimize, mesh_pieces, print3d  # noqa: E402


# ── géométrie de banc ────────────────────────────────────────────────────────

def boite(c, d):
    """12 triangles d'une boîte fermée de centre c et de dimensions d."""
    x0, y0, z0 = (c[i] - d[i] / 2 for i in range(3))
    x1, y1, z1 = (c[i] + d[i] / 2 for i in range(3))
    P = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    F = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6), (1, 2, 6), (1, 6, 5),
         (3, 0, 4), (3, 4, 7)]
    return [(P[a], P[b], P[e]) for a, b, e in F]


def roue(c, r, e, n=16):
    """Un disque épais d'axe X (une roue de voiture) : 4n triangles."""
    tris = []
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        p = [(c[0] + s * e / 2, c[1] + r * math.cos(a), c[2] + r * math.sin(a)) for s in (-1, 1) for a in (a0, a1)]
        g, dr = (c[0] - e / 2, c[1], c[2]), (c[0] + e / 2, c[1], c[2])
        tris += [(g, p[1], p[0]), (dr, p[2], p[3]), (p[0], p[1], p[3]), (p[0], p[3], p[2])]
    return tris


def voiture():
    """Une caisse, quatre roues aux coins, un couvercle posé dessus — TOUT dans un seul nœud, comme un GLB généré."""
    tris = boite((0, 0.6, 0), (1.6, 0.6, 3.0))
    for x in (-0.9, 0.9):
        for z in (-1.1, 1.1):
            tris += roue((x, 0.35, z), 0.35, 0.2)
    tris += boite((0, 0.95, 0), (1.5, 0.04, 2.8))   # le couvercle, au-dessus de la caisse (y 0,93..0,97 > 0,9)
    return tris


def glb_voiture(decalage=(0.0, 0.0, 0.0)) -> bytes:
    data = print3d.glb_de_pieces([("vehicule", voiture())])
    if any(decalage):
        doc, binc = mesh_edit.lire_glb(data)
        doc["nodes"][0]["translation"] = list(decalage)
        data = mesh_edit.ecrire_glb(doc, binc)
    return data


def _job(nom: str, data: bytes) -> pathlib.Path:
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(data)
    return d


def _boite_monde(tris):
    return print3d.bbox(tris)


# ── B6 : les îlots ───────────────────────────────────────────────────────────

def test_l_analyse_trouve_corps_quatre_roues_et_couvercle_sans_rien_ecrire():
    r = mesh_pieces.analyser(glb_voiture())
    formes = sorted(p["forme"] for p in r["pieces"])
    assert formes == ["corps", "couvercle", "roue", "roue", "roue", "roue"], formes
    noms = [p["nom"] for p in r["pieces"]]
    assert "corps" in noms and "couvercle" in noms and {"roue_1", "roue_2", "roue_3", "roue_4"} <= set(noms), noms
    assert r["triangles"] == len(voiture())
    roues = [p for p in r["pieces"] if p["forme"] == "roue"]
    # le pivot d'une roue est sur son AXE (centre du disque), à 1e-6 près
    centres = sorted(tuple(round(v, 4) for v in p["pivot"]) for p in roues)
    assert centres == sorted((x, 0.35, z) for x in (-0.9, 0.9) for z in (-1.1, 1.1)), centres


def test_les_noms_proposes_suivent_la_langue():
    r = mesh_pieces.analyser(glb_voiture(), langue="en")
    noms = {p["nom"] for p in r["pieces"]}
    assert {"body", "lid", "wheel_1"} <= noms, noms


def test_separer_ecrit_un_noeud_par_piece_origine_au_centre_et_le_monde_ne_bouge_pas():
    src = glb_voiture(decalage=(2.0, 0.0, -1.0))
    sortie, rapport = mesh_pieces.separer(src, noms=["caisse"])
    doc, _ = mesh_edit.lire_glb(sortie)
    assert len(doc["nodes"]) == 6 and doc["scenes"][0]["nodes"] == list(range(6))
    noms = [n["name"] for n in doc["nodes"]]
    assert noms[0] == "caisse" and len(set(noms)) == 6, noms
    assert [m["name"] for m in doc["meshes"]] == noms
    # même géométrie MONDE, à l'arrondi flottant près
    avant, apres = print3d.lire_glb_triangles(src), print3d.lire_glb_triangles(sortie)
    assert len(avant) == len(apres)
    ba, bb = _boite_monde(avant), _boite_monde(apres)
    assert all(abs(ba[i][j] - bb[i][j]) < 1e-5 for i in range(3) for j in range(2)), (ba, bb)
    # chaque pièce est centrée sur son origine : sa boîte LOCALE a pour milieu (0, 0, 0)
    for i, nd in enumerate(doc["nodes"]):
        acc = doc["accessors"][doc["meshes"][nd["mesh"]]["primitives"][0]["attributes"]["POSITION"]]
        milieu = [(acc["min"][c] + acc["max"][c]) / 2 for c in range(3)]
        assert all(abs(v) < 1e-6 for v in milieu), (nd["name"], milieu)
        assert "translation" in nd   # pas de rotation à la source : une simple translation
    roue1 = next(nd for nd in doc["nodes"] if nd["name"] == "roue_1")
    assert abs(roue1["translation"][0] - (2.0 - 0.9)) < 1e-6 or abs(roue1["translation"][0] - (2.0 + 0.9)) < 1e-6
    assert rapport["pieces"][0]["nom"] == "caisse" and rapport["triangles"] == len(avant)


def test_les_matieres_et_les_uv_suivent_la_decoupe():
    """Un GLB texturé du dépôt (gltf_builder : UV, normales, matière, image embarquée) : la découpe garde tout."""
    src = gltf_builder.build_glb({}, None, "cube", "matiere")
    doc0, _ = mesh_edit.lire_glb(src)
    attrs0 = set(doc0["meshes"][0]["primitives"][0]["attributes"])
    sortie, _r = mesh_pieces.separer(src)
    doc, binc = mesh_edit.lire_glb(sortie)
    prim = doc["meshes"][0]["primitives"][0]
    assert set(prim["attributes"]) == attrs0, (prim["attributes"], attrs0)
    assert prim.get("material") == doc0["meshes"][0]["primitives"][0].get("material")
    assert doc.get("materials") == doc0.get("materials")
    uv = mesh_edit.lire_accesseur(doc, binc, prim["attributes"]["TEXCOORD_0"]) if "TEXCOORD_0" in attrs0 else None
    if uv is not None:
        assert all(0.0 - 1e-6 <= c <= 1.0 + 1e-6 for v in uv for c in v)


def test_les_petits_ilots_se_regroupent_en_details():
    tris = boite((0, 0, 0), (1, 1, 1))
    for k in range(5):
        tris += [((3 + k, 0, 0), (3.1 + k, 0, 0), (3 + k, 0.1, 0))]   # cinq éclats d'un triangle
    data = print3d.glb_de_pieces([("objet", tris)])
    r = mesh_pieces.analyser(data)
    assert [p["forme"] for p in r["pieces"]] == ["corps", "details"], r["pieces"]
    det = next(p for p in r["pieces"] if p["forme"] == "details")
    assert det["triangles"] == 5


def test_les_refus_parlent_avant_tout_calcul():
    doc, binc = mesh_edit.lire_glb(glb_voiture())
    for cle, val, mot in (("skins", [{"joints": [0]}], "AVANT le rig"),
                          ("extensionsRequired", ["KHR_draco_mesh_compression"], "draco")):
        d = json.loads(json.dumps(doc)); d[cle] = val
        try:
            mesh_pieces.analyser(mesh_edit.ecrire_glb(d, binc))
            raise AssertionError(f"aurait dû refuser {cle}")
        except ValueError as e:
            assert mot in str(e), e
    for mauvais in (0, "x", 99999):
        try:
            mesh_pieces.analyser(glb_voiture(), min_triangles=mauvais)
            raise AssertionError(mauvais)
        except ValueError:
            pass


def test_un_nom_est_assaini_et_les_doublons_prennent_un_suffixe():
    sortie, _ = mesh_pieces.separer(glb_voiture(), noms=["roue avant/gauche", "x", "x"])
    doc, _ = mesh_edit.lire_glb(sortie)
    noms = [n["name"] for n in doc["nodes"]]
    assert noms[0] == "roue_avant_gauche" and noms[1] == "x" and noms[2] == "x_2", noms
    try:
        mesh_pieces.separer(glb_voiture(), noms=["a"] * 7)
        raise AssertionError("7 noms pour 6 pièces")
    except ValueError as e:
        assert "6 noms au plus" in str(e)


def test_la_decoupe_par_noeud_garde_les_noms_de_tripo_et_recentre():
    """Ce que rend Tripo : un nœud par pièce, pivot au centre du monde. La découpe « par nœud » recentre."""
    seg = print3d.glb_de_pieces([("Wheel_FL", roue((-0.9, 0.35, -1.1), 0.35, 0.2)),
                                 ("Body", boite((0, 0.6, 0), (1.6, 0.6, 3.0)))])
    sortie, rap = mesh_pieces.separer(seg, par="noeuds")
    doc, _ = mesh_edit.lire_glb(sortie)
    assert [n["name"] for n in doc["nodes"]] == ["Wheel_FL", "Body"]
    assert [round(v, 4) for v in doc["nodes"][0]["translation"]] == [-0.9, 0.35, -1.1]
    sortie2, _ = mesh_pieces.separer(seg, par="noeuds", noms=["roue_avant_gauche", ""])
    doc2, _ = mesh_edit.lire_glb(sortie2)
    assert [n["name"] for n in doc2["nodes"]] == ["roue_avant_gauche", "Body"]


# ── B7 : rôles et densités ───────────────────────────────────────────────────

def test_les_roles_ont_trois_densites_decroissantes_et_motivees():
    r = {x["id"]: x for x in mesh_lod.roles()}
    assert {"heros", "prop", "decor", "web", "roblox"} <= set(r), sorted(r)
    assert r["heros"]["densites"] == [50_000, 8_000, 2_000]   # les trois densités natives relevées chez Scenario
    for x in r.values():
        assert x["label"] and len(x["pourquoi"]) > 40, x
        n = x["densites"]
        assert len(n) == 3 and n == sorted(n, reverse=True) and len(set(n)) == 3, x


def test_trois_densites_mesurees_et_la_source_sous_budget_est_gardee():
    d = _job("dens_sphere", gltf_builder.build_glb({}, None, "sphere", "s"))
    src = mesh_optimize.glb_stats(d / "model.glb")["tris"]
    info = mesh_lod.densites("dens_sphere", role="web")       # 5000 / 1500 / 400
    assert [x["densite"] for x in info["densites"]] == ["haute", "moyenne", "basse"]
    haute, moy, basse = info["densites"]
    assert info["source_tris"] == src
    if src <= 5000:
        assert haute["source_gardee"] and haute["tris"] == src
    assert not basse["source_gardee"] and basse["tris"] < src
    assert moy["tris"] >= basse["tris"]
    for x in info["densites"]:
        assert x["octets"] == (d / "densites" / x["file"]).stat().st_size > 0
        assert "perte" in x and ("iou_min" in x["perte"] or x["perte"].get("mesure") is False), x
    assert (d / "densites" / "densites.json").is_file() and not (d / "densites" / "source.glb").exists()
    doc, _ = mesh_edit.lire_glb((d / "densites" / "basse.glb").read_bytes())
    assert all(m["name"].endswith("_LOD2") for m in doc["meshes"]), [m["name"] for m in doc["meshes"]]
    nom, octets = mesh_lod.archive_densites("dens_sphere")
    z = zipfile.ZipFile(io.BytesIO(octets))
    noms = z.namelist()
    assert nom == "dens_sphere_web_densites.zip" and "LISEZMOI.txt" in noms and "densites.json" in noms
    assert "dens_sphere_web_basse_0.4k.glb" in noms, noms


def test_les_pieces_survivent_aux_densites():
    sortie, _ = mesh_pieces.separer(glb_voiture())
    d = _job("dens_voiture", sortie)
    info = mesh_lod.densites("dens_voiture", role="prop")
    doc, _ = mesh_edit.lire_glb((d / "densites" / "basse.glb").read_bytes())
    noms = {n.get("name") for n in doc["nodes"] if "mesh" in n}
    assert {"corps_LOD2", "roue_1_LOD2", "couvercle_LOD2"} <= noms, noms
    assert info["densites"][0]["source_gardee"]   # 300 triangles < 8 000 : rien n'est gonflé


def test_un_role_inconnu_est_refuse_sans_effacer_les_densites():
    _job("dens_refus", gltf_builder.build_glb({}, None, "sphere", "s"))
    mesh_lod.densites("dens_refus", role="web")
    try:
        mesh_lod.densites("dens_refus", role="geant")
        raise AssertionError("rôle inconnu accepté")
    except ValueError as e:
        assert "rôle inconnu" in str(e)
    assert mesh_lod.lire_densites("dens_refus")["role"] == "web"


# ── les routes (ASGI) ────────────────────────────────────────────────────────

def test_routes_locales_analyse_separation_densites():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    _job("rt_voiture", glb_voiture())

    async def main():
        o = {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            a = await c.get("/api/etabli/pieces", params={"job": "rt_voiture", "version": 1})
            o["analyse"] = (a.status_code, a.json())
            o["absent"] = (await c.get("/api/etabli/pieces", params={"job": "absent", "version": 1})).status_code
            w = await c.post("/api/etabli/pieces", json={"job": "rt_voiture", "version": 1, "noms": ["caisse"]})
            o["ecrit"] = (w.status_code, w.json())
            g = await c.get("/api/etabli/densites", params={"job": "rt_voiture"})
            o["roles"] = g.json()
            p = await c.post("/api/etabli/densites", json={"job": "rt_voiture", "version": 2, "role": "heros"})
            o["dens"] = (p.status_code, p.json())
            o["mauvais"] = (await c.post("/api/etabli/densites",
                                         json={"job": "rt_voiture", "version": 2, "role": "x"})).status_code
            f = await c.get("/api/etabli/densites/fichier", params={"job": "rt_voiture", "densite": "basse"})
            o["fichier"] = (f.status_code, f.content[:4])
            o["fichier_mauvais"] = (await c.get("/api/etabli/densites/fichier",
                                                params={"job": "rt_voiture", "densite": "x"})).status_code
            z = await c.get("/api/etabli/densites/zip", params={"job": "rt_voiture"})
            o["zip"] = (z.status_code, z.headers.get("content-type"))
        return o
    o = asyncio.run(main())
    st, a = o["analyse"]
    assert st == 200 and len(a["pieces"]) == 6 and a["ia"]["usd"] > 0 and a["cle_fal"] is False, a
    assert o["absent"] == 404
    st, w = o["ecrit"]
    assert st == 200, w
    v2 = settings.outputs_path / "assets3d" / "rt_voiture" / "model.v2.glb"
    doc, _ = mesh_edit.lire_glb(v2.read_bytes())
    assert doc["nodes"][0]["name"] == "caisse" and len(doc["nodes"]) == 6
    assert [r["id"] for r in o["roles"]["roles"]][0] == "heros" and o["roles"]["resultat"] is None
    st, dens = o["dens"]
    assert st == 200 and dens["source"] == "model.v2.glb" and dens["role"] == "heros", dens
    assert o["mauvais"] == 400 and o["fichier"] == (200, b"glTF") and o["fichier_mauvais"] == 400
    assert o["zip"] == (200, "application/zip")


def test_route_ia_refuse_dans_l_ordre_puis_decoupe_le_resultat_simule():
    """Sans clé : 503 AVANT la garde. Avec clé, sans `confirme_cout` : 409 avec le devis. Confirmé : la garde passe
    (X-DZ-Plafond: confirme), le faux Tripo rend un GLB à deux nœuds, la version écrite garde leurs noms."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.services import asset3d_service as A3
    import fal_client
    _job("rt_ia", glb_voiture())
    seg = print3d.glb_de_pieces([("Wheel", roue((-0.9, 0.35, -1.1), 0.35, 0.2)),
                                 ("Body", boite((0, 0.6, 0), (1.6, 0.6, 3.0)))])
    appels = []

    async def faux_upload(p):
        appels.append(("upload", pathlib.Path(p).read_bytes()[:4]))
        return "https://fal.example/source.glb"

    async def faux_subscribe(ep, arguments=None, with_logs=False):
        appels.append(("fal", ep, arguments))
        return {"model_mesh": {"url": "https://fal.example/seg.glb"}, "part_names": ["roue_av_g", "carrosserie"]}

    def faux_download(url, dest, timeout=120):
        appels.append(("dl", url))
        pathlib.Path(dest).write_bytes(seg)
        return True

    vieux = (A3._upload, fal_client.subscribe_async, A3._download)
    A3._upload, fal_client.subscribe_async, A3._download = faux_upload, faux_subscribe, faux_download

    async def main():
        o = {}
        corps = {"job": "rt_ia", "version": 1}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            o["sans_cle"] = (await c.post("/api/etabli/pieces/ia", json={**corps, "confirme_cout": True})).status_code
            settings.FAL_KEY = "cle-de-banc"
            r = await c.post("/api/etabli/pieces/ia", json=corps)
            o["sans_confirme"] = (r.status_code, r.json())
            o["appels_avant"] = len(appels)
            r = await c.post("/api/etabli/pieces/ia", json={**corps, "confirme_cout": True},
                             headers={"X-DZ-Plafond": "confirme"})
            o["ok"] = (r.status_code, r.json())
        return o
    try:
        o = asyncio.run(main())
    finally:
        A3._upload, fal_client.subscribe_async, A3._download = vieux
        settings.FAL_KEY = ""
    assert o["sans_cle"] == 503
    st, j = o["sans_confirme"]
    assert st == 409 and j["detail"]["devis"]["usd"] == 0.4 and o["appels_avant"] == 0, j
    st, j = o["ok"]
    assert st == 200, j
    assert ("fal", "tripo3d/tripo/segment", {"mesh_url": "https://fal.example/source.glb"}) in appels
    v2 = settings.outputs_path / "assets3d" / "rt_ia" / "model.v2.glb"
    doc, _ = mesh_edit.lire_glb(v2.read_bytes())
    assert [n["name"] for n in doc["nodes"]] == ["roue_av_g", "carrosserie"]
    assert [round(v, 4) for v in doc["nodes"][0]["translation"]] == [-0.9, 0.35, -1.1]


def test_le_devis_vient_de_la_grille_des_tarifs():
    from app.services import pricing
    e = pricing.estimate({"kind": "asset3d_segment"})
    assert e["total_usd"] == mesh_pieces.devis_ia()["usd"] == 0.4
    assert e["breakdown"][0]["provider"] == "fal"


def test_les_outils_de_l_agent_lisent_sans_ecrire_ni_depenser():
    from app.services import agent_boites as B, agent_outils as ao
    assert B.verifier() == [], B.verifier()
    assert B.BOITES["assets3d"]["outils"][:2] == ["pieces_analyser", "budgets_triangles"]   # t344 : + comparatif3d_lire
    assert B.BOITES["assets3d"]["agents"] == [] and B.boite_de("pieces_analyser") == "assets3d"
    assert all(ao.OUTILS[n]["nature"] == "lecture" for n in ("pieces_analyser", "budgets_triangles"))
    d = _job("ag_voiture", glb_voiture())
    avant = sorted(x.name for x in d.iterdir())
    vieux = list(B.BOITES["assets3d"]["agents"])
    B.BOITES["assets3d"]["agents"] = ["essai"]
    try:
        ctx = ao.Ctx(cid="c1", agent="essai", lang="en")
        r = asyncio.run(ao.executer("pieces_analyser", {"job": "ag_voiture"}, ctx))
        assert r["ok"] and len(r["donnees"]["pieces"]) == 6 and r["donnees"]["devis_ia_usd"] == 0.4, r
        assert "wheel_1" in {p["nom"] for p in r["donnees"]["pieces"]}
        for mauvais in ({"job": "../x"}, {"job": "ag_voiture", "version": 0}, {"job": "ag_voiture", "version": 9}):
            r2 = asyncio.run(ao.executer("pieces_analyser", mauvais, ctx))
            assert r2["ok"] is False, (mauvais, r2)
        b = asyncio.run(ao.executer("budgets_triangles", {}, ctx))
        assert b["ok"] and "heros 50000/8000/2000" in b["resume"], b
        refus = asyncio.run(ao.executer("pieces_analyser", {"job": "ag_voiture"}, ao.Ctx(cid="c1")))
        assert refus["ok"] is False and "hors de la boîte" in refus["resume"]
    finally:
        B.BOITES["assets3d"]["agents"] = vieux
    assert sorted(x.name for x in d.iterdir()) == avant   # rien d'écrit


def test_l_ecran_charge_son_module_et_chaque_cle_existe():
    """La page de l'Établi charge jeu.css et jeu.js, les deux blocs naissent VIDES, et chaque dzT de jeu.js (préfixe
    pieces3d.) a son français et son anglais — rôles et densités compris, servis par le serveur."""
    import re
    racine = pathlib.Path(__file__).resolve().parents[2]
    html = (racine / "frontend/etabli/index.html").read_text(encoding="utf-8")
    js = (racine / "frontend/etabli/jeu.js").read_text(encoding="utf-8")
    dico = json.loads((racine / "frontend/shared/i18n/pieces3d.json").read_text(encoding="utf-8"))
    assert '<link rel="stylesheet" href="jeu.css">' in html and '<script type="module" src="jeu.js"></script>' in html
    assert html.index('src="etabli.js"') < html.index('src="jeu.js"')
    assert '<div class="panneau jeu" id="panPieces"></div>' in html and '<div class="jeu" id="panDensites"></div>' in html
    assert 'import { S, ouvrirPrincipale } from "./etabli.js";' in js
    cles = {k for k in re.findall(r'\bT\("([a-z_.]+)"', js) if not k.endswith(".")}   # « forme. » + … : vus plus bas
    assert cles, "aucune clé lue"
    for k in cles:
        assert "pieces3d." + k in dico, k
    for r in mesh_lod.roles():
        assert "pieces3d.role." + r["id"] in dico and "pieces3d.pourquoi." + r["id"] in dico, r["id"]
    for f in mesh_pieces.NOMS:
        assert "pieces3d.forme." + f in dico, f
    for dn in mesh_lod.DENSITES:
        assert "pieces3d.densite." + dn in dico
    for k, v in dico.items():
        assert v["fr"] and v["en"] and set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"])), k
    # le coût est SUR le bouton payant, et la confirmation passe par le dialogue maison avant tout envoi
    assert 'T("ia.lancer", { p: usd(ia.usd || 0) })' in js
    i_conf, i_post = js.index("D_.confirmer("), js.index('fetch("/api/etabli/pieces/ia"')
    assert i_conf < i_post and "confirme_cout: true" in js


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (pièces et budgets)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
