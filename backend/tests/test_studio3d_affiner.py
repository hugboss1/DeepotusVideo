# -*- coding: utf-8 -*-
"""t396 + t397 (31/10/2026) — écran Affiner du 3D Studio : poids peints et corrections automatiques
(poids_corrections.py) et leurs routes.

Modèles SYNTHÉTIQUES (aucun appel réseau, aucune dépense) : le mannequin en T du banc du Rig, riggé par rig_local ;
une variante SYMÉTRIQUE de topologie (chaque pièce est une moitié et son miroir) dont les poids sont rendus exactement
symétriques, pour éprouver le miroir ; le personnage de `_squelette_synthetique.glb_cible` (armature tournée, échelle
0,01) pour la lecture d'une peau qui n'est pas la nôtre.
Run : python tests/test_studio3d_affiner.py (depuis backend/)"""
import asyncio, json, math, os, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzs3aff_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = ""; os.environ["ELEVENLABS_API_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
os.environ["MESHY_API_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from loguru import logger                                         # noqa: E402
logger.remove()
from app.config import settings                                   # noqa: E402
from app.services import mesh_edit as ME, print3d, rig_local as RL, poids_corrections as PC   # noqa: E402
import _squelette_synthetique as SQ                               # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]
J = settings.outputs_path / "assets3d"

# ── les modèles ──────────────────────────────────────────────────────────────

PIECES = [
    ("torse", (-0.18, 0.9, -0.1), (0.18, 1.45, 0.1)), ("cou", (-0.05, 1.45, -0.05), (0.05, 1.52, 0.05)),
    ("tete", (-0.1, 1.52, -0.1), (0.1, 1.8, 0.1)),
    ("bras_g", (0.18, 1.4, -0.05), (0.9, 1.5, 0.05)), ("jambe_g", (0.03, 0.05, -0.07), (0.17, 0.9, 0.07)),
    ("pied_g", (0.03, 0.0, -0.07), (0.17, 0.05, 0.2)),
]


def _boite(lo, hi, n=3):
    tris = []
    for ax in range(3):
        u, v = [a for a in range(3) if a != ax]
        for cote_, val in ((0, lo[ax]), (1, hi[ax])):
            def P(i, j):
                p = [0.0, 0.0, 0.0]
                p[ax] = val
                p[u] = lo[u] + (hi[u] - lo[u]) * i / n
                p[v] = lo[v] + (hi[v] - lo[v]) * j / n
                return tuple(round(c, 6) for c in p)
            for i in range(n):
                for j in range(n):
                    a, b, c, d = P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)
                    tris += [(a, b, c), (a, c, d)] if cote_ else [(a, c, b), (a, d, c)]
    return tris


def mannequin(symetrique=False, n=4) -> bytes:
    """Le mannequin en T ; `symetrique` : chaque pièce centrée est une moitié (x ≥ 0) et son miroir, si bien que la
    TOPOLOGIE elle-même est symétrique (les diagonales des quads aussi)."""
    tris = []
    for nom, lo, hi in PIECES:
        if symetrique and not nom.endswith("_g"):
            lo = (0.0, lo[1], lo[2])
        t = _boite(lo, hi, n)
        tris += t
        if nom.endswith("_g") or symetrique:
            tris += [tuple((-p[0], p[1], p[2]) for p in reversed(x)) for x in t]
    return print3d.glb_de_pieces([("corps", tris)])


def rigge(data: bytes) -> bytes:
    return RL.rigger(data, RL.proposition(data)["joints"])[0]


MIROIR_NOM = lambda n: n[:-1] + ("r" if n.endswith("_l") else "l") if n.endswith(("_l", "_r")) else n   # noqa: E731


def _miroirs(pe):
    """{point: point miroir (x → −x)} et {nœud d'os: nœud miroir}."""
    idx = {tuple(round(c, 5) for c in p): i for i, p in enumerate(pe.positions)}
    pts = {}
    for i, p in enumerate(pe.positions):
        q = idx.get((round(-p[0], 5), round(p[1], 5), round(p[2], 5)))
        if q is not None:
            pts[i] = q
    par_nom = {o["nom"]: j for j, o in pe.os.items()}
    return pts, {j: par_nom[MIROIR_NOM(o["nom"])] for j, o in pe.os.items()}


def symetriser(data: bytes) -> bytes:
    """Les poids moyennés avec ceux du point miroir (os miroir) : une peau EXACTEMENT symétrique."""
    pe = PC.Peau(data)
    pts, osm = _miroirs(pe)
    neuf = []
    for i, w in enumerate(pe.poids):
        q = pts.get(i, i)
        m = {osm[b]: v for b, v in pe.poids[q].items()}
        neuf.append(PC._normaliser(PC._melange(w, m, 0.5)))
    return PC.ecrire_peau(pe, neuf)


def asymetrie(data: bytes) -> float:
    pe = PC.Peau(data)
    pts, osm = _miroirs(pe)
    e = 0.0
    for i, q in pts.items():
        a = {osm[b]: v for b, v in pe.poids[i].items()}
        b = pe.poids[q]
        for k in set(a) | set(b):
            e = max(e, abs(a.get(k, 0.0) - b.get(k, 0.0)))
    return e


MAN = mannequin()
RIG = rigge(MAN)
SYM = symetriser(rigge(mannequin(symetrique=True, n=3)))


def _job(nom, fichiers):
    d = J / nom
    d.mkdir(parents=True, exist_ok=True)
    for f, octets in fichiers.items():
        (d / f).write_bytes(octets)
    (d / "asset.json").write_text(json.dumps({"name": nom, "engine": "test", "created_at": "2026-10-31T10:00:00+00:00"}),
                                  encoding="utf-8")
    return d


def _normalises(data: bytes):
    """Chaque sommet de chaque primitive skinnée : quatre influences, poids ≥ 0, somme 1."""
    doc, binc = ME.lire_glb(data)
    n = 0
    for m in doc["meshes"]:
        for p in m["primitives"]:
            a = p["attributes"]
            for jv, wv in zip(ME.lire_accesseur(doc, binc, a["JOINTS_0"]), RL._flottants(doc, binc, a["WEIGHTS_0"])):
                assert abs(sum(wv) - 1) < 1e-5 and all(w >= 0 for w in wv), (jv, wv)
                n += 1
    return n


def _sans_les_poids(data: bytes):
    """Le document sans ses accesseurs de poids : ce qui doit rester IDENTIQUE (os, IBM, positions, scène)."""
    doc, binc = ME.lire_glb(data)
    att = [p["attributes"] for m in doc["meshes"] for p in m["primitives"]]
    pos = [ME.lire_accesseur(doc, binc, a["POSITION"]) for a in att]
    ibm = [ME.lire_accesseur(doc, binc, s["inverseBindMatrices"]) for s in doc.get("skins") or []]
    return doc["nodes"], doc.get("skins"), doc.get("animations"), pos, ibm


# ── lecture ──────────────────────────────────────────────────────────────────

def test_la_peau_se_lit_soudee_avec_ses_22_os():
    pe = PC.Peau(RIG)
    r = pe.resume()
    assert len(r["os"]) == 22 and [o["nom"] for o in r["os"]] == RL.IDS
    assert r["sans_poids"] == 0 and r["points"] <= r["sommets"] and r["aretes"] > r["points"]
    roles = {o["nom"]: o["role"] for o in r["os"]}
    assert roles["clavicle_l"] == "epaule_g" and roles["upperarm_r"] == "bras_d" and roles["thigh_l"] == "cuisse_g"
    for w in pe.poids:
        assert abs(sum(w.values()) - 1) < 1e-6 and len(w) <= 4
    # une couture d'UV (deux sommets, une position) ne fait qu'UN point
    doc, binc = ME.lire_glb(RIG)
    pos = ME.lire_accesseur(doc, binc, doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"])
    assert r["points"] == len({tuple(round(c, 6) for c in p) for p in pos})
    # un modèle sans peau est refusé, en français
    try:
        PC.Peau(MAN)
        raise AssertionError("modèle sans peau accepté")
    except ValueError as e:
        assert "rigge-le d'abord" in str(e)


def test_une_peau_tierce_armature_tournee_se_lit_et_se_pose():
    data = SQ.glb_cible()
    pe = PC.Peau(data)
    assert pe.par_nom("upperarm_l") is not None and pe.os[pe.par_nom("upperarm_l")]["role"] == "bras_g"
    # au repos (pose vide), les positions posées sont les positions de repos
    for a, b in zip(pe.positions, PC.poser(pe, pe.poids, {})):
        assert math.dist(a, b) < 1e-6
    # lever le bras gauche ne bouge que les points qu'il tient
    j = pe.par_nom("upperarm_l")
    posees = PC.poser(pe, pe.poids, {j: [0, 0, 60]})
    for p, q, w in zip(pe.positions, posees, pe.poids):
        if not any(pe.os[b]["nom"].endswith(("arm_l", "hand_l")) for b in w):
            assert math.dist(p, q) < 1e-6
    assert any(math.dist(p, q) > 1e-3 for p, q in zip(pe.positions, posees))


# ── écriture ─────────────────────────────────────────────────────────────────

def test_ecrire_la_peau_sans_changement_rend_les_memes_poids_en_place():
    pe = PC.Peau(RIG)
    out = PC.ecrire_peau(pe, pe.poids)
    assert len(ME.lire_glb(out)[1]) == len(ME.lire_glb(RIG)[1])      # EN PLACE : le tampon ne grossit pas
    assert _sans_les_poids(out) == _sans_les_poids(RIG)
    pe2 = PC.Peau(out)
    for a, b in zip(pe.poids, pe2.poids):
        for k in set(a) | set(b):
            assert abs(a.get(k, 0) - b.get(k, 0)) < 1e-6


def test_les_poids_peints_sont_renormalises_et_valides():
    doc, binc = ME.lire_glb(RIG)
    att = doc["meshes"][0]["primitives"][0]["attributes"]
    k_tete = RL.IDS.index("head")
    k_cou = RL.IDS.index("neck_01")
    out, rap = PC.ecrire_sommets(RIG, [{"mesh": 0, "primitive": 0, "sommets": [0, 5],
                                        "joints": [k_tete, 0, 0, 0, k_cou, k_tete, 0, 0],
                                        "poids": [2, 0, 0, 0, 1, 3, 0, 0]}])
    assert rap == {"sommets": 2, "primitives": 1, "operation": "poids_peints"}
    assert len(ME.lire_glb(out)[1]) == len(ME.lire_glb(RIG)[1])
    d2, b2 = ME.lire_glb(out)
    js = ME.lire_accesseur(d2, b2, att["JOINTS_0"])
    ws = RL._flottants(d2, b2, att["WEIGHTS_0"])
    assert js[0][0] == k_tete and abs(ws[0][0] - 1) < 1e-6 and sum(ws[0][1:]) < 1e-9
    assert (js[5][0], js[5][1]) == (k_tete, k_cou) and abs(ws[5][0] - 0.75) < 1e-6 and abs(ws[5][1] - 0.25) < 1e-6
    assert ws[1] == RL._flottants(doc, binc, att["WEIGHTS_0"])[1]          # les autres sommets n'ont pas bougé
    assert _sans_les_poids(out) == _sans_les_poids(RIG)
    _normalises(out)
    bons = {"mesh": 0, "primitive": 0, "sommets": [0], "joints": [0, 0, 0, 0], "poids": [1, 0, 0, 0]}
    for mauvais, mot in [
        ([], "liste non vide"), ([{**bons, "mesh": 3}], "introuvable"), ([{**bons, "sommets": [10 ** 7]}], "hors de"),
        ([{**bons, "joints": [99, 0, 0, 0]}], "indice d'os"), ([{**bons, "poids": [-1, 0, 0, 0]}], "négatif"),
        ([{**bons, "poids": [0, 0, 0, 0]}], "aucun poids"), ([{**bons, "joints": [0, 0]}], "4·k"),
    ]:
        try:
            PC.ecrire_sommets(RIG, mauvais)
            raise AssertionError(f"accepté : {mot}")
        except ValueError as e:
            assert mot in str(e), (mot, str(e))


# ── les corrections ──────────────────────────────────────────────────────────

def test_chaque_correction_garde_les_poids_normalises_et_ne_touche_pas_aux_os():
    base = _sans_les_poids(RIG)
    n0 = _normalises(RIG)
    for op in PC.OPERATIONS:
        out, rap = PC.corriger(RIG, op)
        assert rap["correction"] == op, rap
        assert _normalises(out) == n0, op
        assert _sans_les_poids(out) == base, op
        assert len(ME.lire_glb(out)[1]) == len(ME.lire_glb(RIG)[1]), op   # en place
        assert json.dumps(rap)                        # le compte rendu passe en JSON


def test_les_orphelins_trouvent_l_ilot_injecte_et_le_rendent_a_sa_bordure():
    pe = PC.Peau(RIG)
    main = pe.par_nom("hand_l")
    # un îlot connexe sur le devant du torse (z = 0,1), loin de la main
    ilot = [i for i, p in enumerate(pe.positions) if abs(p[2] - 0.1) < 1e-6 and -0.1 <= p[0] <= 0.1 and 1.0 <= p[1] <= 1.2]
    assert len(ilot) >= 4
    poids = [dict(w) for w in pe.poids]
    for i in ilot:
        poids[i] = PC._normaliser({**poids[i], main: 0.8 * sum(poids[i].values()) / 0.2})
    sale = PC.ecrire_peau(pe, poids)
    _, rap = PC.corriger(sale, "orphelins", os="hand_l", parametres={"apercu": True})
    lignes = rap["orphelins"]
    assert len(lignes) == 1 and lignes[0]["os"] == "hand_l"
    trouve = [x for x in lignes[0]["ilots"] if abs(x["centre"][2] - 0.1) < 1e-6 and 1.0 <= x["centre"][1] <= 1.2]
    assert len(trouve) == 1 and trouve[0]["points"] == len(ilot), lignes
    assert trouve[0]["vers"] and "hand_l" not in trouve[0]["vers"], trouve
    propre, rap2 = PC.corriger(sale, "orphelins", os="hand_l")
    pe2 = PC.Peau(propre)
    m2 = pe2.par_nom("hand_l")
    for i in ilot:
        assert pe2.poids[i].get(m2, 0) == 0 and abs(sum(pe2.poids[i].values()) - 1) < 1e-6
    # le membre, lui, garde sa main
    assert sum(1 for w in pe2.poids if w.get(m2, 0) > 0.5) > 10
    # un second passage ne trouve plus rien sur cet os
    assert PC.corriger(propre, "orphelins", os="hand_l", parametres={"apercu": True})[1]["ilots"] == 0


def test_le_confinement_rogne_un_bras_loin_de_son_segment_selon_sa_force():
    pe = PC.Peau(RIG)
    bras = pe.par_nom("upperarm_l")
    loin = min(range(len(pe.positions)), key=lambda i: math.dist(pe.positions[i], (0.0, 0.9, 0.1)))   # bas du torse
    poids = [dict(w) for w in pe.poids]
    poids[loin] = PC._normaliser({**poids[loin], bras: 1.0})
    sale = PC.ecrire_peau(pe, poids)
    w0 = PC.Peau(sale).poids[loin][bras]
    out70, rap = PC.corriger(sale, "confinement", os="upperarm_l")
    w70 = PC.Peau(out70).poids[loin].get(bras, 0)
    out0, _ = PC.corriger(sale, "confinement", os="upperarm_l", parametres={"force": 0})
    assert abs(PC.Peau(out0).poids[loin][bras] - w0) < 1e-6           # force nulle : rien ne bouge
    assert w70 < w0 * 0.5, (w0, w70)                                    # 70 % de l'excès au-delà de la portée
    assert rap["confinement"][0]["os"] == "upperarm_l" and rap["points"] >= 1
    # un point du bras, PRÈS de son segment, ne perd rien
    pres = min(range(len(pe.positions)), key=lambda i: math.dist(pe.positions[i], (0.45, 1.45, 0.05)))
    assert abs(PC.Peau(out70).poids[pres].get(bras, 0) - PC.Peau(sale).poids[pres].get(bras, 0)) < 1e-6


def test_l_epaule_reconstruite_ne_touche_que_sa_region_et_garde_la_masse_du_trio():
    pe = PC.Peau(RIG)
    out, rap = PC.corriger(RIG, "epaules")
    pe2 = PC.Peau(out)
    assert {r["cote"] for r in rap["epaules"]} == {"g", "d"} and rap["points"] > 0
    trio = {pe.par_nom(n) for n in ("spine_03", "clavicle_l", "upperarm_l", "clavicle_r", "upperarm_r")}
    centre_g = pe.os[pe.par_nom("upperarm_l")]["tete"]
    r = rap["epaules"][0]["rayon"]
    for i, p in enumerate(pe.positions):
        a, b = pe.poids[i], pe2.poids[i]
        if math.dist(p, centre_g) >= r and math.dist(p, (-centre_g[0], centre_g[1], centre_g[2])) >= r:
            assert all(abs(a.get(k, 0) - b.get(k, 0)) < 1e-6 for k in set(a) | set(b)), p
        else:                                   # sans troncature à quatre, la masse du trio est conservée
            c = "l" if p[0] > 0 else "r"
            cote_trio = {pe.par_nom(n) for n in ("spine_03", "clavicle_" + c, "upperarm_" + c)}
            if len(set(a) | cote_trio) <= 4:
                assert abs(sum(a.get(k, 0) for k in trio) - sum(b.get(k, 0) for k in trio)) < 1e-5, p


def test_les_coutures_lissent_un_collier_qui_grandit_avec_ses_anneaux():
    _, r1 = PC.corriger(RIG, "coutures", parametres={"anneaux": 1, "apercu": True})
    _, r3 = PC.corriger(RIG, "coutures", parametres={"anneaux": 3, "apercu": True})
    _, rb = PC.corriger(RIG, "coutures", os="calf_l", parametres={"anneaux": 2, "apercu": True})
    assert 0 < r1["coutures"]["collier"] < r3["coutures"]["collier"]
    assert 0 < rb["coutures"]["collier"] < r3["coutures"]["collier"] and rb["coutures"]["os"] == "calf_l"
    # « seulement les déformées » : sans pose, refusé ; avec une pose du genou, le collier se réduit
    try:
        PC.corriger(RIG, "coutures", parametres={"deformees": True})
        raise AssertionError("deformees sans pose acceptée")
    except ValueError as e:
        assert "pose" in str(e)
    _, rd = PC.corriger(RIG, "coutures", parametres={"deformees": True, "pose": {"calf_l": [90, 0, 0]},
                                                    "apercu": True})
    assert 0 < rd["coutures"]["collier"] < r3["coutures"]["collier"] and rd["coutures"]["deformees_seulement"]


def test_la_guerison_ne_rend_jamais_une_pose_plus_etiree():
    out, rap = PC.corriger(RIG, "guerison", parametres={"poses": [{"lowerarm_l": [0, -100, 0]}, {"thigh_r": [-80, 0, 0]}]})
    assert len(rap["guerison"]) == 2
    for r in rap["guerison"]:
        assert r["apres"] <= r["avant"], r
    assert any(r["apres"] < r["avant"] for r in rap["guerison"]), rap
    # sans poses : la batterie d'amplitude, jouée des deux côtés
    pe = PC.Peau(RIG)
    bat = PC.batterie(pe)
    assert len(bat) >= 8
    lever = bat[0]
    g, d = pe.par_nom("upperarm_l"), pe.par_nom("upperarm_r")
    assert lever[g] == [0, 0, -60] and lever[d] == [0, 0, 60]
    for mauvais, mot in [({"poses": [{"inconnu": [0, 0, 0]}]}, "os inconnu"), ({"poses": [{"head": [0, 0]}]}, "trois angles"),
                         ({"poses": []}, "1 à 32"), ({"pose": {"head": [0, 0, 0, 0]}}, "quaternion nul"),
                         ({"tolerance": 9}, "tolerance")]:
        try:
            PC.corriger(RIG, "guerison", parametres=mauvais)
            raise AssertionError(f"accepté : {mot}")
        except ValueError as e:
            assert mot in str(e), (mot, str(e))


def test_le_miroir_les_corrections_gardent_une_peau_symetrique_symetrique():
    assert asymetrie(SYM) < 1e-6
    pe = PC.Peau(SYM)
    pts, _ = _miroirs(pe)
    assert len(pts) == len(pe.positions)                    # chaque point a son miroir
    for op in PC.OPERATIONS:
        out, _ = PC.corriger(SYM, op)
        assert asymetrie(out) < 1e-5, (op, asymetrie(out))


def test_les_refus_du_service_sont_en_francais():
    for args, kw, mot in [(("rien",), {}, "opération inconnue"), (("confinement",), {"os": "aile"}, "os inconnu"),
                          (("confinement",), {"parametres": {"force": 2}}, "force"),
                          (("coutures",), {"parametres": {"anneaux": 0}}, "anneaux"),
                          (("orphelins",), {"parametres": {"apercu": "oui"}}, "apercu")]:
        try:
            PC.corriger(RIG, *args, **kw)
            raise AssertionError(f"accepté : {mot}")
        except ValueError as e:
            assert mot in str(e), (mot, str(e))


# ── les routes ───────────────────────────────────────────────────────────────

def _client():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


def test_les_routes_lisent_peignent_corrigent_et_ecrivent_des_versions():
    _job("aff", {"model.glb": MAN})

    async def go():
        async with _client() as c:
            r0 = await c.get("/api/studio3d/affiner/poids/aff")                        # pas encore riggé
            j = (await c.get("/api/studio3d/rig/proposition/aff")).json()["joints"]
            r1 = await c.post("/api/studio3d/rig/appliquer/aff", json={"version": 1, "joints": j})
            r2 = await c.get("/api/studio3d/affiner/poids/aff")
            r3 = await c.post("/api/studio3d/affiner/enregistrer/aff", json={"version": 2, "modifs": [
                {"mesh": 0, "primitive": 0, "sommets": [0], "joints": [5, 0, 0, 0], "poids": [1, 0, 0, 0]}]})
            r4 = await c.post("/api/studio3d/affiner/corriger/aff", json={"version": 3, "operation": "orphelins",
                                                                         "parametres": {"apercu": True}})
            r5 = await c.post("/api/studio3d/affiner/corriger/aff", json={"version": 3, "operation": "tout"})
            r6 = await c.get("/api/studio3d/ouvert/aff")
            return r0, r1, r2, r3, r4, r5, r6
    r0, r1, r2, r3, r4, r5, r6 = asyncio.run(go())
    assert r0.status_code == 400 and "rigge-le d'abord" in r0.json()["detail"], r0.text
    assert r1.status_code == 200 and r1.json()["version"] == 2
    b = r2.json()
    assert r2.status_code == 200 and b["version"] == 2 and len(b["os"]) == 22 and b["sans_poids"] == 0
    assert r3.status_code == 200, r3.text
    assert (r3.json()["depuis"], r3.json()["version"], r3.json()["fichier"]) == (2, 3, "model.v3.glb")
    assert r4.status_code == 200 and r4.json()["apercu"] and r4.json()["version"] is None
    assert r5.status_code == 200, r5.text
    assert (r5.json()["depuis"], r5.json()["version"]) == (3, 4) and r5.json()["url"] == "/api/assets/3d/aff/version/4"
    f = r6.json()
    assert f["version"] == 4 and f["rig"]["rigge"] and f["rig"]["os"] == 22
    ops = {v["version"]: (v["operation"], v["depuis"]) for v in f["versions"]}
    assert ops[3] == ("poids_peints", 2) and ops[4] == ("poids_tout", 3), ops
    assert sorted(x.name for x in (J / "aff").glob("model*.glb")) == ["model.glb", "model.v2.glb", "model.v3.glb",
                                                                     "model.v4.glb"]
    # le sommet peint tient à la tête (indice 5 de la peau)
    doc, binc = ME.lire_glb((J / "aff" / "model.v3.glb").read_bytes())
    a = doc["meshes"][0]["primitives"][0]["attributes"]
    assert ME.lire_accesseur(doc, binc, a["JOINTS_0"])[0][0] == 5


def test_les_routes_refusent_proprement_sans_rien_ecrire():
    _job("aff2", {"model.glb": RIG})
    _job("abime_aff", {"model.glb": b"pas un glb"})

    async def go():
        async with _client() as c:
            return [
                await c.get("/api/studio3d/affiner/poids/inconnu"),
                await c.get("/api/studio3d/affiner/poids/aff2", params={"version": 7}),
                await c.post("/api/studio3d/affiner/enregistrer/aff2", json={"modifs": []}),
                await c.post("/api/studio3d/affiner/enregistrer/aff2", json={"modifs": [{"mesh": 9, "primitive": 0,
                                                                            "sommets": [], "joints": [], "poids": []}]}),
                await c.post("/api/studio3d/affiner/corriger/aff2", json={"operation": "magie"}),
                await c.post("/api/studio3d/affiner/corriger/aff2", json={"operation": "confinement", "os": 3}),
                await c.post("/api/studio3d/affiner/corriger/aff2", json={"operation": "confinement", "os": "aile"}),
                await c.post("/api/studio3d/affiner/corriger/aff2", json={"operation": "tout", "parametres": "x"}),
                await c.post("/api/studio3d/affiner/corriger/aff2", json={"operation": "tout", "version": 0}),
                await c.post("/api/studio3d/affiner/corriger/inconnu", json={"operation": "tout"}),
                await c.get("/api/studio3d/affiner/poids/abime_aff"),
                await c.post("/api/studio3d/affiner/corriger/job$", json={"operation": "tout"}),
            ]
    rs = asyncio.run(go())
    assert [r.status_code for r in rs] == [404, 404, 400, 400, 400, 400, 400, 400, 400, 404, 400, 400], \
        [(r.status_code, r.text) for r in rs]
    assert "aile" in rs[6].json()["detail"]
    assert sorted(f.name for f in (J / "aff2").glob("model*.glb")) == ["model.glb"]


def test_les_routes_de_l_affinage_ne_touchent_a_aucun_fournisseur_payant():
    src = (RACINE / "backend/app/api/studio3d_affiner_routes.py").read_text(encoding="utf-8") \
        + (RACINE / "backend/app/services/poids_corrections.py").read_text(encoding="utf-8")
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    code = re.sub(r'"""[\s\S]*?"""', "", code)
    for mot in ("meshy", "fal_client", "httpx", "requests", "_plafond", "pricing", "uthana", "openai"):
        assert mot not in code.lower(), mot


def test_les_refus_des_routes_sont_traduits():
    erreurs = json.loads((RACINE / "backend/app/i18n/erreurs.json").read_text(encoding="utf-8"))
    par_fr = {v["fr"]: v["en"] for v in erreurs.values()}
    for fr, en in (("ce modèle n'a pas de peau (JOINTS_0 / WEIGHTS_0) : rigge-le d'abord (écran Rig)",
                    "this model has no skin (JOINTS_0 / WEIGHTS_0): rig it first (Rig screen)"),
                   ("os inconnu « {v} »", 'unknown bone "{v}"'),
                   ("deformees : une pose est requise (lance le test de pose)",
                    "deformees: a pose is required (start the pose test)")):
        assert par_fr.get(fr) == en, (fr, par_fr.get(fr))


# ── la page ─────────────────────────────────────────────────────────────────

def test_l_ecran_est_branche_et_sa_feuille_n_a_aucun_rayon():
    coque = (RACINE / "frontend/studio3d/ecrans/coque.js").read_text(encoding="utf-8")
    assert 'affiner: "./affiner.js"' in coque
    html = (RACINE / "frontend/studio3d/index.html").read_text(encoding="utf-8")
    assert 'href="ecrans/affiner.css"' in html and html.index('href="ecrans/ecrans.css"') < html.index('href="ecrans/affiner.css"')
    css = (RACINE / "frontend/studio3d/ecrans/affiner.css").read_text(encoding="utf-8")
    assert not re.search(r"border-radius\s*:(?!\s*var\(--r\)\s*[;}])", css)       # angles vifs : var(--r) seulement
    js = (RACINE / "frontend/studio3d/ecrans/affiner.js").read_text(encoding="utf-8")
    for route in ("/api/studio3d/affiner/poids/", "/api/studio3d/affiner/enregistrer/", "/api/studio3d/affiner/corriger/"):
        assert route in js, route
    assert "ctx.rafraichir()" in js and "marquerSale(" in js and 'aller("rig")' in js
    assert "AnimationMixer" in js and "applyBoneTransform" in js


def test_les_cles_de_l_ecran_affiner_existent_en_fr_et_en():
    dico = json.loads((RACINE / "frontend/shared/i18n/studio3decrans_affiner.json").read_text(encoding="utf-8"))
    for k, v in dico.items():
        assert re.fullmatch(r"studio3decrans\.aff\.[a-z0-9_]+", k), k
        assert v["fr"].strip() and v["en"].strip() and v.get("contexte") is True, k
        assert set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"])), k
    src = "".join((RACINE / "frontend/studio3d/ecrans" / f).read_text(encoding="utf-8") for f in ("affiner.js", "poids_calc.js"))
    cles = {k for k in re.findall(r'"(aff\.[a-z0-9_]+)"', src) if not k.endswith("_")}
    calc = (RACINE / "frontend/studio3d/ecrans/poids_calc.js").read_text(encoding="utf-8")
    for fam in ("OUTILS", "MODES", "ATTENUATIONS", "VUES"):
        ids = json.loads(calc.split(f"export const {fam} = ", 1)[1].split(";", 1)[0])
        cles |= {f"aff.{fam.lower()[:-1] if fam != 'ATTENUATIONS' else 'attenuation'}_{i}" for i in ids}
    cles |= {f"aff.op_{o}" for o in PC.OPERATIONS}
    assert len(cles) > 60, len(cles)
    for k in cles:
        assert "studio3decrans." + k in dico, k
    assembled = (RACINE / "frontend/shared/dz-i18n-dico.js").read_text(encoding="utf-8")
    assert '"studio3decrans.aff.enregistrer"' in assembled, "relancer scripts/i18n_assembler.py"


def test_le_calcul_des_poids_sous_node():
    node = shutil.which("node")
    if not node:
        print("    (node absent : banc JS sauté)")
        return
    r = subprocess.run([node, str(RACINE / "frontend/studio3d/qa/affiner.test.mjs")], capture_output=True,
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
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (écran Affiner)")
    shutil.rmtree(_tmp, ignore_errors=True)
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
