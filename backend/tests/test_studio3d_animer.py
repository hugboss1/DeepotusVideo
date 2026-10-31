# -*- coding: utf-8 -*-
"""t398 + t399 (31/10/2026) — écran ANIMER du 3D Studio : catalogue Meshy (680 animations), favoris et collections,
application d'une animation du catalogue sur un rig Meshy, texte → mouvement (Meshy Text to Motion, swift = BVH).

Tout est SIMULÉ au niveau HTTP : le module `httpx` de `meshy_service` est remplacé par un client à
`httpx.MockTransport` qui note chaque requête — aucune ne part, rien n'est dépensé. Données isolées (DEEPOTUS_DATA_DIR
temporaire) ; personnage riggé SYNTHÉTIQUE (`_squelette_synthetique.glb_cible`), BVH « Mixamo » synthétique.
Run : python tests/test_studio3d_animer.py (depuis backend/)"""
import asyncio, json, math, os, pathlib, re, shutil, subprocess, sys, tempfile, types
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzs3anim_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = ""; os.environ["ELEVENLABS_API_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
os.environ["MESHY_API_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import httpx                                                      # noqa: E402
from loguru import logger                                         # noqa: E402
logger.remove()
from app.config import settings                                   # noqa: E402
from app.services import animations_catalogue as CAT, mesh_edit, meshy_service as MS, print3d   # noqa: E402
from app.services import asset3d_service as A3, studio3d_animer as SA   # noqa: E402
import _squelette_synthetique as SQ                               # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]
J = settings.outputs_path / "assets3d"
A3.MESHY_POLL_S = 0.01


def boite():
    P = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
    F = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6), (1, 2, 6), (1, 6, 5),
         (3, 0, 4), (3, 4, 7)]
    return print3d.glb_de_pieces([("m", [(P[a], P[b], P[c]) for a, b, c in F])])


def _job(nom, fichiers, manifeste=None):
    d = J / nom
    d.mkdir(parents=True, exist_ok=True)
    for f, octets in fichiers.items():
        (d / f).write_bytes(octets)
    if manifeste is not None:
        (d / "asset.json").write_text(json.dumps(manifeste), encoding="utf-8")
    return d


RIG = SQ.glb_cible()
_job("perso", {"model.glb": RIG}, {"name": "Héros", "engine": "meshy", "created_at": "2026-10-30T10:00:00+00:00",
                                  "rig": {"meshy_task": "rig-0001", "animations": {}}})
_job("sans_meshy", {"model.glb": RIG}, {"name": "Importé", "created_at": "2026-10-29T10:00:00+00:00"})
_job("caisse", {"model.glb": boite()}, {"created_at": "2026-10-28T10:00:00+00:00"})


# ── le faux réseau : chaque requête Meshy est notée, aucune ne sort ─────────────────────────────

APPELS: list[tuple] = []
BVH = SQ.bvh_source().encode("utf-8")


def _repondre(req: httpx.Request) -> httpx.Response:
    url = str(req.url)
    APPELS.append((req.method, url, json.loads(req.content) if req.content else None))
    if req.method == "POST" and url.endswith("/openapi/v1/text-to-motion"):
        return httpx.Response(202, json={"result": "tm-0042"})
    if req.method == "GET" and url.endswith("/openapi/v1/text-to-motion/tm-0042"):
        return httpx.Response(200, json={"id": "tm-0042", "status": "SUCCEEDED", "progress": 100,
                                         "result": {"motion_url": "https://assets.meshy.ai/m/tm-0042.bvh",
                                                    "motion_format": "bvh", "duration_ms": 3000, "mode": "swift"}})
    if req.method == "GET" and url == "https://assets.meshy.ai/m/tm-0042.bvh":
        return httpx.Response(200, content=BVH)
    if req.method == "POST" and url.endswith("/openapi/v1/animations"):
        return httpx.Response(202, json={"result": "an-0007"})
    if req.method == "GET" and url.endswith("/openapi/v1/animations/an-0007"):
        return httpx.Response(200, json={"id": "an-0007", "status": "SUCCEEDED",
                                         "result": {"animation_glb_url": "https://assets.meshy.ai/a/an-0007.glb"}})
    if req.method == "GET" and url == "https://assets.meshy.ai/a/an-0007.glb":
        return httpx.Response(200, content=RIG)
    return httpx.Response(404, json={"message": f"inattendu : {req.method} {url}"})


def _faux_client(**kw):
    kw.pop("verify", None)
    return httpx.AsyncClient(transport=httpx.MockTransport(_repondre), **kw)


MS.httpx = types.SimpleNamespace(AsyncClient=_faux_client, HTTPError=httpx.HTTPError)


def _client():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def _attendre(c, job, tache):
    for _ in range(300):
        e = (await c.get("/api/studio3d/animer/tache", params={"job": job, "tache": tache})).json()
        if e.get("etat") in ("fini", "echec", "interrompu"):
            return e
        await asyncio.sleep(0.02)
    return e


# ── 1. le catalogue ──────────────────────────────────────────────────────────

def test_le_catalogue_porte_les_680_animations_du_releve():
    tout = CAT.charger()
    assert len(tout) >= 600 and len(tout) == 680, len(tout)
    ids = [e["id"] for e in tout]
    assert len(set(ids)) == len(ids) and min(ids) == -2 and max(ids) == 696
    cats = {c["id"]: c["nombre"] for c in CAT.categories()}
    assert cats == {"WalkAndRun": 178, "BodyMovements": 158, "DailyActions": 157, "Fighting": 154, "Dancing": 33}, cats
    assert [c["id"] for c in CAT.categories()][0] == "WalkAndRun"
    walk = next(c for c in CAT.categories() if c["id"] == "WalkAndRun")["sous"]
    assert walk[0] == {"id": "Walking", "nombre": 88}, walk
    assert CAT.par_id(92)["nom"] and CAT.par_id(0)["nom"] == "Idle"
    assert CAT.par_id(-2)["applicable"] is False and CAT.par_id(0)["applicable"] is True
    assert CAT.par_id(99999) is None and CAT.par_id("x") is None


def test_recherche_filtre_et_pagination():
    r = CAT.chercher("walk")
    assert r["total"] > 50 and all("walk" in (e["nom"] + e["cle"] + (e["sous_categorie"] or "")).lower().replace("_", " ")
                                   or "walk" in e["categorie"].lower() for e in r["entrees"])
    assert CAT.chercher("WALK")["total"] == r["total"]                      # casse
    deux = CAT.chercher("walk gun")
    assert 0 < deux["total"] < r["total"]                                   # tous les mots
    assert all("gun" in (e["nom"] + e["cle"]).lower() for e in deux["entrees"])
    f = CAT.chercher("", categorie="Dancing")
    assert f["total"] == 33 and {e["categorie"] for e in f["entrees"]} == {"Dancing"}
    s = CAT.chercher("", categorie="Fighting", sous_categorie="Punching")
    assert s["total"] == 38
    p = CAT.chercher("", par_page=50)
    assert p["pages"] == 14 and len(p["entrees"]) == 50
    der = CAT.chercher("", page=999, par_page=50)
    assert der["page"] == 14 and len(der["entrees"]) == 680 - 13 * 50     # hors bornes → la dernière
    assert CAT.chercher("", par_page=10_000)["par_page"] == CAT.PAR_PAGE_MAX
    assert CAT.chercher("zzzzqqq")["total"] == 0 and CAT.chercher("zzzzqqq")["pages"] == 1
    assert [e["id"] for e in CAT.chercher("", ids=[4, 0, 92, 4, 123456])["entrees"]] == [4, 0, 92]   # ordre gardé


# ── 2. favoris et collections ────────────────────────────────────────────────

def test_favoris_et_collections_persistent_dans_le_dossier_de_donnees():
    async def main():
        o = {}
        async with _client() as c:
            for i in (4, 92, 0):
                o["fav"] = (await c.post("/api/studio3d/animer/favoris", json={"id": i})).json()
            o["fav_off"] = (await c.post("/api/studio3d/animer/favoris", json={"id": 92, "favori": False})).json()
            o["fav_inconnu"] = (await c.post("/api/studio3d/animer/favoris", json={"id": 123456})).status_code
            o["fav_bool"] = (await c.post("/api/studio3d/animer/favoris", json={"id": True})).status_code
            o["vue_fav"] = (await c.get("/api/studio3d/animer/catalogue", params={"vue": "favoris"})).json()
            r = (await c.post("/api/studio3d/animer/collections", json={"nom": "  Combat   boss ", "ids": [4, 8]})).json()
            cid = r["collection"]["id"]
            o["creee"] = r["collection"]
            o["sans_nom"] = (await c.post("/api/studio3d/animer/collections", json={"nom": "  "})).status_code
            o["mod"] = (await c.post("/api/studio3d/animer/collections",
                                     json={"id": cid, "ajouter": [11, 4], "retirer": [8]})).json()["collection"]
            o["mod_inconnu"] = (await c.post("/api/studio3d/animer/collections",
                                             json={"id": cid, "ajouter": [999999]})).status_code
            o["vue_col"] = (await c.get("/api/studio3d/animer/catalogue",
                                        params={"vue": "collection", "collection": cid})).json()
            o["col_absente"] = (await c.get("/api/studio3d/animer/catalogue",
                                            params={"vue": "collection", "collection": "nope"})).status_code
            o["vue_bidon"] = (await c.get("/api/studio3d/animer/catalogue", params={"vue": "x"})).status_code
            r2 = (await c.post("/api/studio3d/animer/collections", json={"nom": "Danse"})).json()
            o["suppr"] = (await c.delete(f"/api/studio3d/animer/collections/{r2['collection']['id']}")).json()
            o["suppr2"] = (await c.delete(f"/api/studio3d/animer/collections/{r2['collection']['id']}")).status_code
            o["cid"] = cid
        return o
    o = asyncio.run(main())
    assert o["fav"]["favoris"] == [4, 92, 0] and o["fav_off"]["favoris"] == [4, 0]
    assert o["fav_inconnu"] == 400 and o["fav_bool"] == 400
    v = o["vue_fav"]
    assert [e["id"] for e in v["entrees"]] == [0, 4] and all(e["favori"] for e in v["entrees"]) and v["favoris"] == 2
    assert o["creee"]["nom"] == "Combat boss" and o["creee"]["ids"] == [4, 8]
    assert o["sans_nom"] == 400 and o["mod"]["ids"] == [4, 11] and o["mod_inconnu"] == 400
    assert [e["id"] for e in o["vue_col"]["entrees"]] == [4, 11]
    assert o["col_absente"] == 404 and o["vue_bidon"] == 400
    assert [c["id"] for c in o["suppr"]["collections"]] == [o["cid"]] and o["suppr2"] == 404
    # PERSISTÉ : dans le dossier de données isolé, relu par le service sans cache
    f = pathlib.Path(_tmp) / "studio3d" / "animer.json"
    disque = json.loads(f.read_text("utf-8"))
    assert disque["favoris"] == [4, 0] and disque["collections"][0]["ids"] == [4, 11]
    assert SA.favoris() == [4, 0] and SA.collections()[0]["nom"] == "Combat boss"
    assert not (RACINE / "backend" / "app" / "services" / "animer.json").exists()


# ── 3. texte → mouvement ─────────────────────────────────────────────────────

def test_texte_vers_mouvement_refuse_dans_l_ordre_puis_recible_le_bvh():
    from app.services import plafonds as P
    corps = {"job": "perso", "version": 1, "prompt": "marche prudente, regarde à gauche", "duree": 3, "mode": "swift",
             "nom": "prudent"}

    async def main():
        o = {}
        async with _client() as c:
            settings.MESHY_API_KEY = ""
            # sans clé : 503 AVANT toute autre vérification (même une saisie fausse)
            o["sans_cle"] = (await c.post("/api/studio3d/animer/texte", json={**corps, "prompt": "", "confirme_cout": True})).status_code
            settings.MESHY_API_KEY = "cle-de-banc"
            post = lambda **kw: c.post("/api/studio3d/animer/texte", json={**corps, "confirme_cout": True, **kw})
            o["vide"] = (await post(prompt="   ")).status_code
            o["long"] = (await post(prompt="x" * 401)).status_code
            o["trop_long"] = (await post(duree=10.5)).status_code
            o["trop_court"] = (await post(duree=1.5)).status_code
            o["pas"] = (await post(duree=2.3)).status_code
            o["texte_duree"] = (await post(duree="3")).status_code
            o["prime"] = (await post(mode="prime")).json()
            o["mode"] = (await post(mode="ultra")).status_code
            o["job_inconnu"] = (await post(job="nulpart")).status_code
            o["chemin"] = (await post(job="../perso")).status_code
            o["sans_squelette"] = (await post(job="caisse")).json()
            o["version_absente"] = (await post(version=7)).status_code
            r = await c.post("/api/studio3d/animer/texte", json=corps)
            o["sans_confirme"] = (r.status_code, r.json())
            o["appels_avant_plafond"] = len(APPELS)
            P.enregistrer({"global_usd": 0, "par_moteur": {"meshy": 0.001}, "alerte_pct": 80})
            o["plafond"] = (await post()).status_code
            o["appels_apres_plafond"] = len(APPELS)
            r = await c.post("/api/studio3d/animer/texte", json={**corps, "confirme_cout": True},
                             headers={"X-DZ-Plafond": "confirme"})
            o["ok"] = (r.status_code, r.json())
            o["etat"] = await _attendre(c, "perso", r.json()["tache"])
            o["sources"] = (await c.get("/api/etabli/mouvement", params={"job": "perso", "version": 2})).json()
            o["fiche"] = (await c.get("/api/studio3d/ouvert/perso")).json()
            o["tache_bidon"] = (await c.get("/api/studio3d/animer/tache", params={"job": "perso", "tache": "zz"})).status_code
        return o
    try:
        o = asyncio.run(main())
    finally:
        settings.MESHY_API_KEY = ""
        P.enregistrer({"global_usd": 0, "par_moteur": {}, "alerte_pct": 80})
    assert o["sans_cle"] == 503
    for k in ("vide", "long", "trop_long", "trop_court", "pas", "texte_duree", "mode", "chemin", "version_absente"):
        assert o[k] in (400, 404), (k, o[k])
    assert o["vide"] == o["long"] == o["trop_long"] == o["trop_court"] == o["pas"] == o["mode"] == 400
    assert o["job_inconnu"] in (400, 404) and o["chemin"] == 400
    assert "FBX" in o["prime"]["detail"] and "swift" in o["prime"]["detail"]
    assert "squelette" in o["sans_squelette"]["detail"]
    st, j = o["sans_confirme"]
    assert st == 409 and j["detail"]["devis"]["credits"] == {"meshy": 3.0}, j
    # RIEN n'est parti vers Meshy tant que le coût n'est pas confirmé, ni quand le plafond refuse
    assert o["appels_avant_plafond"] == 0 and o["plafond"] == 402 and o["appels_apres_plafond"] == 0
    st, j = o["ok"]
    assert st == 200 and j["nom"] == "prudent" and j["devis"]["credits"] == {"meshy": 3.0}, j
    e = o["etat"]
    assert e["etat"] == "fini", e
    assert e["meshy_task"] == "tm-0042" and e["version"] == 2 and e["clip"] == "prudent", e
    assert e["rapport"]["relies"] >= 10, e["rapport"]
    # la requête envoyée à Meshy : endpoint, prompt, mode et durée du relevé
    meth, url, charge = APPELS[0]
    assert (meth, url) == ("POST", "https://api.meshy.ai/openapi/v1/text-to-motion"), APPELS[0]
    assert charge == {"prompt": corps["prompt"], "mode": "swift", "duration": 3.0}, charge
    assert ("GET", "https://assets.meshy.ai/m/tm-0042.bvh", None) in APPELS
    # le BVH est rangé dans le job, avec sa fiche ; la version 2 porte le clip nommé
    d = J / "perso"
    assert (d / "mouvements" / "prudent.bvh").read_bytes() == BVH
    fiche = json.loads((d / "mouvements" / "prudent.bvh.json").read_text("utf-8"))
    assert fiche["origine"] == "meshy-motion" and fiche["meshy_task"] == "tm-0042" and fiche["mode"] == "swift"
    assert [c["nom"] for c in o["sources"]["clips"]] == ["prudent"], o["sources"]["clips"]
    assert any(s["nom"] == "prudent.bvh" and s["origine"] == "meshy-motion" for s in o["sources"]["sources"])
    doc, _ = mesh_edit.lire_glb((d / "model.v2.glb").read_bytes())
    assert [a["name"] for a in doc["animations"]] == ["prudent"]
    assert o["fiche"]["version"] == 2 and o["fiche"]["rig"]["animations"] == 1
    assert o["tache_bidon"] == 400


def test_texte_mode_et_bornes_annonces_a_l_ecran():
    t = SA.etat_texte()
    assert [m["id"] for m in t["modes"]] == ["swift", "prime"]
    assert t["modes"][0]["lisible"] and not t["modes"][1]["lisible"]
    assert t["modes"][0]["devis"]["credits"] == {"meshy": 3.0} and t["modes"][1]["devis"]["credits"] == {"meshy": 10.0}
    assert t["duree"] == {"min": 2.0, "max": 10.0, "pas": 0.5} and t["prompt_max"] == 400
    assert {a["id"]: a["raison"] for a in t["autres"]} == {"kimodo": "sans_api", "gvhmr": "non_commercial"}
    hy = t["hy"]
    assert [(m["id"], m["devis"]["total_usd"]) for m in hy["modeles"]] == [("hy-motion", 0.08), ("hy-motion-fast", 0.06)]
    assert all(m["devis"]["breakdown"][0]["provider"] == "fal" for m in hy["modeles"])
    assert hy["duree"] == {"min": 0.5, "max": 12.0, "pas": 0.5} and hy["guidance"]["defaut"] == 5.0
    assert hy["licence"]["nom"] == "Tencent HY-MOTION 1.0 Community License"
    assert hy["licence"]["url"].startswith("https://github.com/Tencent-Hunyuan/HY-Motion-1.0/")
    assert "UE" in hy["licence"]["territoires_exclus"] and "Royaume-Uni" in hy["licence"]["territoires_exclus"]
    assert SA.valider_texte({"prompt": "saut", "duree": 10})["duree"] == 10.0
    assert SA.valider_texte({"prompt": "Un  saut   périlleux !", "duree": 2.5})["nom"] == "Un_saut_p_rilleux"


# ── 3 bis. HY-Motion (t405) : convertisseur dict → BVH, licence, tir fal SIMULÉ ─────────────────────

from app.services import mouvement_rig as MR   # noqa: E402

N_HY = 12


def _ry(deg):
    a = math.radians(deg)
    c, s_ = math.cos(a), math.sin(a)
    return ((c, 0.0, s_), (0.0, 1.0, 0.0), (-s_, 0.0, c))


def _en_6d(m):          # convention amont : colonnes 0 et 1 de la matrice 3×3, aplaties ligne par ligne
    return [m[0][0], m[0][1], m[1][0], m[1][1], m[2][0], m[2][1]]


def _motion(rep, coude=0.0, lot=True, plat=False):
    """Un dict HY-Motion synthétique : N_HY images, toutes les rotations à l'identité sauf le coude GAUCHE (L_Elbow,
    os 18) plié de `coude` degrés autour de Y ; la racine avance de 1 cm par image en X."""
    imgs = []
    for f in range(N_HY):
        os_ = []
        for j in range(22):
            ang = coude * f / (N_HY - 1) if j == 18 else 0.0
            if rep == "rot6d":
                os_.append(_en_6d(_ry(ang)))
            elif rep == "axe":
                os_.append([0.0, math.radians(ang), 0.0])
            else:
                os_.append([math.cos(math.radians(ang) / 2), 0.0, math.sin(math.radians(ang) / 2), 0.0])
        imgs.append([v for o in os_ for v in o] if plat else os_)
    transl = [[0.01 * f, 0.9, 0.0] for f in range(N_HY)]
    cle = {"rot6d": "rot6d", "axe": "poses", "quat": "quat"}[rep]
    if lot:
        return {cle: [imgs], "transl": [transl], "text": "test"}
    return {cle: imgs, "transl": transl}


def _ecart_q(a, b):
    d = abs(sum(x * y for x, y in zip(a, b)))
    return 1 - min(1.0, d)


def test_hymotion_convertisseur_accepte_les_trois_formes_et_rend_la_pose_de_repos():
    for rep, plat in (("rot6d", False), ("axe", False), ("quat", False), ("rot6d", True), ("quat", True)):
        bvh = SA.hymotion_vers_bvh(_motion(rep, lot=not plat, plat=plat))
        m = MR.lire_bvh(bvh)
        assert m["n"] == N_HY and m["fps"] == 30.0 and len(m["os"]) == 22, (rep, m["n"], m["fps"])
        noms = [o["nom"] for o in m["os"]]
        assert noms[0] == "Hips" and "LeftForeArm" in noms and "RightToeBase" in noms, noms
        # des rôles RECONNUS par mouvement_rig : cuisse, bras, avant-bras, main des deux côtés
        roles = {MR.role(n) for n in noms}
        for r in ("bassin", "cuisse_g", "cuisse_d", "bras_g", "avantbras_g", "main_d", "pied_g", "epaule_d", "tete"):
            assert r in roles, (rep, r)
        # identité partout → toutes les rotations à l'identité : la pose de repos SMPL (en T)
        for serie in m["rot"]:
            for q in serie:
                assert _ecart_q(q, MR.Q_ID) < 1e-9, (rep, q)
        assert m["trans"][0][3] == (3.0, 90.0, 0.0), m["trans"][0][3]          # mètres → centimètres
    # la pose de repos SMPL : la main gauche à droite de l'épaule (+X), le pied sous le bassin
    R, P, _ = MR.monde(m["os"], None, None)
    i = {o["nom"]: k for k, o in enumerate(m["os"])}
    assert P[i["LeftHand"]][0] > P[i["LeftArm"]][0] + 45 and abs(P[i["LeftHand"]][1] - P[i["LeftArm"]][1]) < 5
    assert P[i["LeftFoot"]][1] < P[i["Hips"]][1] - 75


def test_la_physique_se_garde_avec_le_modele():
    """t405 : POST /physique/{job} écrit physics-config.json dans le dossier du job (lu par l'Exporter) ; refus 400/404."""
    J3 = settings.outputs_path / "assets3d"
    (J3 / "phys").mkdir(parents=True, exist_ok=True)

    async def go():
        async with _client() as c:
            ok = await c.post("/api/studio3d/animer/physique/phys", json={"reglages": {"raideur": 2}})
            r404 = await c.post("/api/studio3d/animer/physique/inconnu", json={"reglages": {}})
            r400 = await c.post("/api/studio3d/animer/physique/phys", json={"pas": "de reglages"})
            return ok, r404, r400
    ok, r404, r400 = asyncio.run(go())
    assert ok.status_code == 200 and (r404.status_code, r400.status_code) == (404, 400)
    assert json.loads((J3 / "phys" / "physics-config.json").read_text(encoding="utf-8")) == {"reglages": {"raideur": 2}}


def test_hymotion_convertisseur_refuse_les_formes_inconnues():
    def refus(motion):
        try:
            SA.hymotion_vers_bvh(motion)
        except ValueError as e:
            return str(e)
        raise AssertionError(f"accepté à tort : {str(motion)[:60]}")
    bon = _motion("rot6d", lot=False)
    assert "(L, 22, 6)" in refus({"rot6d": [[[0.0] * 5] * 22] * 3})
    assert "(L, 22, 6)" in refus({"rot6d": [[[1, 0, 0, 1, 0, 0]] * 21] * 3})
    assert "(L, 22, 3)" in refus({"poses": [[[0, 0]] * 22] * 3})
    assert "aucune rotation" in refus({"keypoints3d": [[[0, 0, 0]] * 22]})
    assert "transl" in refus({**bon, "transl": bon["transl"][:-1]})
    assert "non finie" in refus({"rot6d": [[[float("nan"), 0, 0, 1, 0, 0]] * 22]})
    assert "dégénéré" in refus({"rot6d": [[[0, 0, 0, 0, 0, 0]] * 22]})
    assert "JSON" in refus("pas du json")
    assert "objet" in refus([1, 2, 3])
    assert "cadence" in refus({**bon, "fps": 0})


def test_euler_zxy_recompose_la_matrice():
    import random
    rnd = random.Random(7)
    for _ in range(200):
        v = [rnd.uniform(-2, 2) for _ in range(3)]
        m = SA._mat_axe_angle(v)
        z, x, y = SA.euler_zxy(m)
        q = MR.q_mul(MR.q_mul(MR.q_axe("Z", z), MR.q_axe("X", x)), MR.q_axe("Y", y))
        assert _ecart_q(q, MR.q_de_matrice(m)) < 1e-9, (v, z, x, y)
    # blocage de cardan (x = ±90°) : la matrice est quand même rendue
    m = SA._mat_axe_angle((math.pi / 2, 0, 0))
    z, x, y = SA.euler_zxy(m)
    q = MR.q_mul(MR.q_mul(MR.q_axe("Z", z), MR.q_axe("X", x)), MR.q_axe("Y", y))
    assert abs(x - 90) < 1e-6 and _ecart_q(q, MR.q_de_matrice(m)) < 1e-9


def _angle_coude_cible(motion, aligner=True):
    """Le mouvement converti, reciblé sur le personnage « Unreal » synthétique : l'angle (degrés) entre le bras et
    l'avant-bras GAUCHES à la dernière image, et le résultat brut."""
    src = MR.lire_bvh(SA.hymotion_vers_bvh(motion))
    doc, _ = mesh_edit.lire_glb(RIG)
    cible = MR.squelette_glb(doc)
    res = MR.recibler(src, cible, aligner=aligner)
    k = len(res["temps"]) - 1
    rots = [res["rot"][i][k] if i in res["rot"] else None for i in range(len(cible))]
    trans = [res["trans"][i][k] if i in res["trans"] else None for i in range(len(cible))]
    _R, P, _S = MR.monde(cible, rots, trans)
    i = {o["nom"]: n for n, o in enumerate(cible)}
    bras = [P[i["lowerarm_l"]][c] - P[i["upperarm_l"]][c] for c in range(3)]
    avant = [P[i["hand_l"]][c] - P[i["lowerarm_l"]][c] for c in range(3)]
    return SQ.angle(bras, avant), res, cible


def test_hymotion_reciblage_repos_puis_coude_a_90_degres():
    # identité : sans alignement, chaque os relié garde EXACTEMENT sa rotation de repos
    _a, res, cible = _angle_coude_cible(_motion("rot6d"), aligner=False)
    assert res["rapport"]["relies"] >= 18, res["rapport"]
    for i, serie in res["rot"].items():
        for q in serie:
            assert _ecart_q(q, cible[i]["r"]) < 1e-9, (cible[i]["nom"], q)
    # l'angle du coude de la SOURCE (SMPL n'a pas le bras parfaitement droit : ≈ 7,6° au repos)
    bras_s = SA.SMPL_OS[18][2]                       # L_Shoulder → L_Elbow
    avant_s = SA.SMPL_OS[20][2]                      # L_Elbow → L_Wrist
    attendu0 = SQ.angle(bras_s, avant_s)
    plie = tuple(sum(_ry(-90.0)[r][c] * avant_s[c] for c in range(3)) for r in range(3))
    attendu90 = SQ.angle(bras_s, plie)
    assert 5 < attendu0 < 10 and 85 < attendu90 < 100, (attendu0, attendu90)
    # identité avec alignement : la pose de la source (en T) est rendue sur la cible (en A)
    a0, _r, _c = _angle_coude_cible(_motion("rot6d"))
    assert abs(a0 - attendu0) < 1.0, (a0, attendu0)
    # un coude gauche plié de 90° (autour de Y) arrive plié de même sur le rig cible, dans les trois représentations
    for rep in ("rot6d", "axe", "quat"):
        a, res, _c = _angle_coude_cible(_motion(rep, coude=-90.0))
        assert abs(a - attendu90) < 1.0, (rep, a, attendu90)
        assert res["rapport"]["correspondance"]["lowerarm_l"] == "LeftForeArm"


def _fal_stub(appels, rendre):
    async def subscribe_async(endpoint, arguments=None, with_logs=False, **kw):
        appels.append((endpoint, dict(arguments or {})))
        return rendre
    mod = types.ModuleType("fal_client")
    mod.subscribe_async = subscribe_async
    return mod


def test_hy_motion_refuse_dans_l_ordre_puis_recible_le_dict():
    from app.services import plafonds as P
    corps = {"job": "perso", "version": 1, "modele": "hy-motion", "prompt": "lève le bras et plie le coude",
             "duree": 2.5, "nom": "coude_hy"}
    FAL = []
    TELE = []
    motion = json.dumps(_motion("rot6d", coude=-90.0)).encode("utf-8")
    vieux_fal = sys.modules.get("fal_client")
    vieux_tele = SA._telecharger
    sys.modules["fal_client"] = _fal_stub(FAL, {"motion_json": {"url": "https://v3.fal.media/files/m/coude.json",
                                                                "content_type": "application/json"}, "seed": 42})

    async def tele(url):
        TELE.append(url)
        return motion
    SA._telecharger = tele

    async def main():
        o = {}
        async with _client() as c:
            settings.FAL_KEY = ""
            post = lambda **kw: c.post("/api/studio3d/animer/texte", json={**corps, "confirme_cout": True, **kw})
            o["modele"] = (await post(modele="kimodo", licence_acceptee=True)).status_code
            # la licence d'abord : même sans clé fal, même avec une saisie fausse
            o["sans_licence"] = (await post(prompt="", duree=99)).json()
            o["licence_texte"] = (await post(licence_acceptee="oui")).status_code
            o["sans_cle"] = (await post(licence_acceptee=True, prompt="")).status_code
            settings.FAL_KEY = "cle-fal-de-banc"
            o["vide"] = (await post(licence_acceptee=True, prompt=" ")).status_code
            o["duree"] = (await post(licence_acceptee=True, duree=12.5)).status_code
            o["duree_court"] = (await post(licence_acceptee=True, duree=0.4)).status_code
            o["guidance"] = (await post(licence_acceptee=True, guidance=11)).status_code
            o["graine"] = (await post(licence_acceptee=True, seed=-1)).status_code
            o["caisse"] = (await post(licence_acceptee=True, job="caisse")).json()
            o["chemin"] = (await post(licence_acceptee=True, job="../perso")).status_code
            r = await c.post("/api/studio3d/animer/texte", json={**corps, "licence_acceptee": True})
            o["sans_confirme"] = (r.status_code, r.json())
            r = await c.post("/api/studio3d/animer/texte", json={**corps, "modele": "hy-motion-fast",
                                                                 "licence_acceptee": True})
            o["fast_devis"] = r.json()["detail"]["devis"]["total_usd"]
            P.enregistrer({"global_usd": 0, "par_moteur": {"fal": 0.001}, "alerte_pct": 80})
            o["plafond"] = (await post(licence_acceptee=True)).status_code
            o["fal_avant"] = len(FAL) + len(TELE)
            r = await c.post("/api/studio3d/animer/texte", json={**corps, "licence_acceptee": True,
                                                                 "confirme_cout": True, "seed": 9},
                             headers={"X-DZ-Plafond": "confirme"})
            o["ok"] = (r.status_code, r.json())
            o["fin"] = await _attendre(c, "perso", r.json()["tache"])
            o["sources"] = (await c.get("/api/etabli/mouvement",
                                        params={"job": "perso", "version": o["fin"].get("version") or 1})).json()
        return o
    try:
        o = asyncio.run(main())
    finally:
        settings.FAL_KEY = ""
        SA._telecharger = vieux_tele
        if vieux_fal is None:
            sys.modules.pop("fal_client", None)
        else:
            sys.modules["fal_client"] = vieux_fal
        P.enregistrer({"global_usd": 0, "par_moteur": {}, "alerte_pct": 80})
    assert o["modele"] == 400
    assert "Licence HY-Motion" in o["sans_licence"]["detail"] and "Union européenne" in o["sans_licence"]["detail"]
    assert o["licence_texte"] == 400 and o["sans_cle"] == 503
    for k in ("vide", "duree", "duree_court", "guidance", "graine", "chemin"):
        assert o[k] == 400, (k, o[k])
    assert "squelette" in o["caisse"]["detail"]
    st, j = o["sans_confirme"]
    assert st == 409 and j["detail"]["devis"]["total_usd"] == 0.08, j
    assert j["detail"]["devis"]["breakdown"][0]["provider"] == "fal"
    assert o["fast_devis"] == 0.06
    # RIEN n'est parti vers fal tant que la licence, la saisie, le coût ou le plafond refusent
    assert o["plafond"] == 402 and o["fal_avant"] == 0, (o["plafond"], o["fal_avant"])
    st, j = o["ok"]
    assert st == 200 and j["modele"] == "hy-motion" and j["nom"] == "coude_hy", j
    e = o["fin"]
    assert e["etat"] == "fini", e
    assert e["clip"] == "coude_hy" and e["version"] >= 2 and e["rapport"]["relies"] >= 18, e
    # l'appel fal : l'endpoint et les paramètres du relevé, au format dict
    assert FAL == [("fal-ai/hunyuan-motion", {"prompt": corps["prompt"], "duration": 2.5, "guidance_scale": 5.0,
                                              "output_format": "dict", "seed": 9})], FAL
    assert TELE == ["https://v3.fal.media/files/m/coude.json"]
    d = J / "perso"
    fiche = json.loads((d / "mouvements" / "coude_hy.bvh.json").read_text("utf-8"))
    assert fiche["origine"] == "hy-motion" and fiche["modele"] == "hy-motion" and fiche["seed"] == 42
    assert fiche["licence"].startswith("Tencent HY-MOTION") and fiche["images"] == N_HY
    assert any(s_["nom"] == "coude_hy.bvh" and s_["origine"] == "hy-motion" for s_ in o["sources"]["sources"])
    doc, _ = mesh_edit.lire_glb((d / f"model.v{e['version']}.glb").read_bytes())
    assert "coude_hy" in [a["name"] for a in doc["animations"]]


def test_la_licence_hy_motion_se_range_dans_le_dossier_de_donnees():
    async def main():
        async with _client() as c:
            a = (await c.get("/api/studio3d/animer/licence")).json()
            b = (await c.post("/api/studio3d/animer/licence", json={"acceptee": True})).json()
            bidon = (await c.post("/api/studio3d/animer/licence", json={"acceptee": "oui"})).status_code
            etat = (await c.get("/api/studio3d/animer/etat")).json()
            disque = json.loads((pathlib.Path(_tmp) / "studio3d" / "animer.json").read_text("utf-8"))
            fav = (await c.post("/api/studio3d/animer/favoris", json={"id": 92})).json()
            garde = json.loads((pathlib.Path(_tmp) / "studio3d" / "animer.json").read_text("utf-8"))
            d = (await c.post("/api/studio3d/animer/licence", json={"acceptee": False})).json()
        return a, b, bidon, etat, disque, fav, garde, d
    a, b, bidon, etat, disque, fav, garde, d = asyncio.run(main())
    assert a["licence"]["acceptee"] is False and b["licence"]["acceptee"] is True and b["licence"]["le"]
    assert bidon == 400
    assert etat["texte"]["hy"]["licence"]["acceptee"] is True and etat["fal"] is False
    assert disque["licences"]["hy-motion"]["acceptee"] is True
    assert garde["licences"]["hy-motion"]["acceptee"] is True and 92 in fav["favoris"]   # un favori ne l'efface pas
    assert d["licence"]["acceptee"] is False and SA.licence_hy()["acceptee"] is False
    SA.marquer_favori(92, False)


# ── 4. appliquer une animation du catalogue ─────────────────────────────────

def test_appliquer_une_animation_sur_le_rig_meshy():
    async def main():
        o = {}
        async with _client() as c:
            APPELS.clear()
            settings.MESHY_API_KEY = ""
            o["sans_cle"] = (await c.post("/api/studio3d/animer/appliquer",
                                          json={"job": "perso", "action_id": 4, "confirme_cout": True})).status_code
            settings.MESHY_API_KEY = "cle-de-banc"
            o["etat"] = (await c.get("/api/studio3d/animer/etat", params={"job": "perso"})).json()
            o["etat_sans"] = (await c.get("/api/studio3d/animer/etat", params={"job": "sans_meshy"})).json()
            o["devis"] = (await c.get("/api/studio3d/animer/appliquer/devis", params={"job": "perso", "action_id": 4})).json()
            o["base"] = (await c.post("/api/studio3d/animer/appliquer",
                                      json={"job": "perso", "action_id": -2, "confirme_cout": True})).status_code
            o["inconnue"] = (await c.post("/api/studio3d/animer/appliquer",
                                          json={"job": "perso", "action_id": 99999, "confirme_cout": True})).status_code
            o["sans_rig"] = (await c.post("/api/studio3d/animer/appliquer",
                                          json={"job": "sans_meshy", "action_id": 4, "confirme_cout": True})).json()
            r = await c.post("/api/studio3d/animer/appliquer", json={"job": "perso", "action_id": 4})
            o["sans_confirme"] = (r.status_code, r.json())
            o["appels_avant"] = len(APPELS)
            r = await c.post("/api/studio3d/animer/appliquer", json={"job": "perso", "action_id": 4, "confirme_cout": True})
            o["ok"] = (r.status_code, r.json())
            o["fin"] = await _attendre(c, "perso", r.json()["tache"])
            o["anims"] = (await c.get("/api/assets/3d/perso/animations")).json()
            o["fichier"] = await c.get("/api/assets/3d/perso/animation/action_4")
        return o
    try:
        o = asyncio.run(main())
    finally:
        settings.MESHY_API_KEY = ""
    assert o["sans_cle"] == 503
    assert o["etat"]["rig_meshy"] is True and o["etat_sans"]["rig_meshy"] is False and o["etat"]["meshy"] is True
    assert o["devis"]["voie"] == "animation" and o["devis"]["devis"]["credits"] == {"meshy": 3.0}
    assert o["base"] == 400 and o["inconnue"] == 400 and "Rig" in o["sans_rig"]["detail"]
    st, j = o["sans_confirme"]
    assert st == 409 and j["detail"]["devis"]["credits"] == {"meshy": 3.0} and o["appels_avant"] == 0
    assert o["ok"][0] == 200
    assert o["fin"]["etat"] == "fini" and o["fin"]["nom"] == "action_4", o["fin"]
    assert APPELS[0] == ("POST", "https://api.meshy.ai/openapi/v1/animations", {"rig_task_id": "rig-0001", "action_id": 4})
    assert [a["nom"] for a in o["anims"]["animations"]] == ["action_4"]
    assert o["fichier"].status_code == 200 and o["fichier"].content == RIG
    assert json.loads((J / "perso" / "asset.json").read_text("utf-8"))["rig"]["meshy_task"] == "rig-0001"


# ── 5. la page ───────────────────────────────────────────────────────────────

ECR = RACINE / "frontend/studio3d/ecrans"


def test_la_coque_charge_l_ecran_animer_et_sa_feuille():
    coque = (ECR / "coque.js").read_text(encoding="utf-8")
    assert 'animer: "./animer.js"' in coque
    html = (RACINE / "frontend/studio3d/index.html").read_text(encoding="utf-8")
    assert html.count('href="ecrans/animer.css"') == 1
    css = (ECR / "animer.css").read_text(encoding="utf-8")
    assert not re.search(r"border-radius\s*:(?!\s*(?:var\(--r\)|0\b))", css)
    js = (ECR / "animer.js").read_text(encoding="utf-8")
    assert "border-radius" not in js
    # la dépense : le dialogue maison AVANT l'envoi de confirme_cout, sur les deux voies payantes
    for route in ('"/api/studio3d/animer/texte"', '"/api/studio3d/animer/appliquer"'):
        i_post = js.index(route)
        avant = js[:i_post]
        assert "__dzDialogue" in avant and "confirmer(" in avant, route
    assert js.count("confirme_cout: true") >= 2
    # la réutilisation : les routes du mouvement de l'Établi, jamais sa logique recopiée
    assert "/api/etabli/mouvement/importer" in js and "/api/etabli/mouvement/appliquer" in js
    assert 'ctx.aller("rig")' in js


def test_les_cles_de_l_ecran_animer_existent_en_fr_et_en():
    dico = json.loads((RACINE / "frontend/shared/i18n/studio3decrans_animer.json").read_text(encoding="utf-8"))
    src = "".join((ECR / f).read_text(encoding="utf-8") for f in ("animer.js", "animer_calc.js"))
    cles = {k for k in re.findall(r'"(anim\.[a-z0-9_]+)"', src) if not k.endswith("_")}   # T("…") et clés en variable
    assert len(cles) > 40, len(cles)
    for k in cles:
        assert "studio3decrans." + k in dico, k
    for k, v in dico.items():
        assert re.fullmatch(r"studio3decrans\.anim\.[a-z0-9_]+", k), k
        assert v["fr"] and v["en"] and v.get("contexte") is True, k
        assert set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"])), k
    # les familles composées à l'exécution : catégories, sous-catégories, vues de caméra, origines, modèles
    calc = (ECR / "animer_calc.js").read_text(encoding="utf-8")
    for v in json.loads("[" + calc.split("export const VUES = [", 1)[1].split("]", 1)[0] + "]"):
        assert f"studio3decrans.anim.vue_{v.lower()}" in dico and f"studio3decrans.anim.vue_{v.lower()}_aide" in dico, v
    for o in json.loads("[" + calc.split("export const ORIGINES = [", 1)[1].split("]", 1)[0] + "]"):
        assert f"studio3decrans.anim.origine_{o.replace('-', '_')}" in dico, o
    for c in CAT.categories():
        for s in c["sous"]:
            assert f"studio3decrans.anim.sous_{s['id'].lower()}" in dico, s["id"]
    for c in CAT.categories():
        assert f"studio3decrans.anim.cat_{c['id'].lower()}" in dico, c["id"]
    for m in ("swift", "prime", "hy_motion", "kimodo", "gvhmr"):
        assert f"studio3decrans.anim.modele_{m}" in dico, m
    assembled = (RACINE / "frontend/shared/dz-i18n-dico.js").read_text(encoding="utf-8")
    assert '"studio3decrans.anim.titre_biblio"' in assembled, "relancer scripts/i18n_assembler.py"


def test_le_calcul_de_l_ecran_animer_sous_node():
    node = shutil.which("node")
    if not node:
        print("    (node absent : banc JS sauté)")
        return
    r = subprocess.run([node, str(RACINE / "frontend/studio3d/qa/animer.test.mjs")], capture_output=True,
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
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (3D Studio › Animer)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
