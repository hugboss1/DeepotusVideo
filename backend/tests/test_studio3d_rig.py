# -*- coding: utf-8 -*-
"""t395 (31/10/2026) — écran Rig du 3D Studio : le rig semi-automatique LOCAL (rig_local.py) et ses routes.

Modèles SYNTHÉTIQUES (aucun appel réseau, aucune dépense) : un mannequin en T fait de boîtes subdivisées, symétrique
autour de x = 0 ; le même sous un nœud parent déplacé et mis à l'échelle ; le personnage riggé de
`_squelette_synthetique.glb_cible` (armature tournée de -90° en X, échelle 0,01). L'auto-rig IA (Meshy) n'est JAMAIS
appelé : sa fonction est remplacée par une sentinelle qui échoue si on la touche.
Run : python tests/test_studio3d_rig.py (depuis backend/)"""
import asyncio, json, math, os, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzs3rig_")
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
from app.services import mesh_edit as ME, print3d, rig_local as RL, studio3d_ouvert as SO   # noqa: E402
import _squelette_synthetique as SQ                               # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]
J = settings.outputs_path / "assets3d"
H = 1.8


# ── le mannequin : boîtes subdivisées (une grille n × n par face), en pose en T ─────────────────────────────────────

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


def _sym(lo, hi):
    return (-hi[0], lo[1], lo[2]), (-lo[0], hi[1], hi[2])


PIECES = [
    ("torse", (-0.18, 0.9, -0.1), (0.18, 1.45, 0.1)), ("cou", (-0.05, 1.45, -0.05), (0.05, 1.52, 0.05)),
    ("tete", (-0.1, 1.52, -0.1), (0.1, 1.8, 0.1)),
    ("bras_g", (0.18, 1.4, -0.05), (0.9, 1.5, 0.05)), ("jambe_g", (0.03, 0.05, -0.07), (0.17, 0.9, 0.07)),
    ("pied_g", (0.03, 0.0, -0.07), (0.17, 0.05, 0.2)),
]


def mannequin() -> bytes:
    tris = []
    for nom, lo, hi in PIECES:
        tris += _boite(lo, hi, 4)
        if nom.endswith("_g"):
            tris += [tuple((-p[0], p[1], p[2]) for p in reversed(t)) for t in _boite(lo, hi, 4)]
    return print3d.glb_de_pieces([("corps", tris)])


def sous_parent(data: bytes, t=(2.0, 0.0, -1.0), s=0.5) -> bytes:
    """Le même GLB sous un nœud parent déplacé et mis à l'échelle (la cuisson en repère monde est mise à l'épreuve)."""
    doc, binc = ME.lire_glb(data)
    racines = list(doc["scenes"][doc.get("scene", 0)]["nodes"])
    doc["nodes"].append({"name": "Parent", "translation": list(t), "scale": [s, s, s], "children": racines})
    doc["scenes"][doc.get("scene", 0)]["nodes"] = [len(doc["nodes"]) - 1]
    return ME.ecrire_glb(doc, binc)


def _job(nom, fichiers, manifeste=None):
    d = J / nom
    d.mkdir(parents=True, exist_ok=True)
    for f, octets in fichiers.items():
        (d / f).write_bytes(octets)
    (d / "asset.json").write_text(json.dumps(manifeste or {"name": nom, "engine": "test",
                                                         "created_at": "2026-10-31T10:00:00+00:00"}), encoding="utf-8")
    return d


MAN = mannequin()


def _lire_peau(data: bytes):
    """(doc, [(positions, joints, poids)] par primitive) d'un GLB skinné."""
    doc, binc = ME.lire_glb(data)
    out = []
    for m in doc["meshes"]:
        for p in m["primitives"]:
            a = p["attributes"]
            out.append((RL._flottants(doc, binc, a["POSITION"]), ME.lire_accesseur(doc, binc, a["JOINTS_0"]),
                        RL._flottants(doc, binc, a["WEIGHTS_0"])))
    return doc, out


def _poids_de(joints, poids, k):
    return sum(w for j, w in zip(joints, poids) if j == k)


# ── le gabarit ───────────────────────────────────────────────────────────────

def test_le_gabarit_est_un_humanoide_sense_dans_sa_boite():
    g = RL.gabarit({"min": [-0.7, 0, -0.2], "max": [0.7, 2.0, 0.2]})
    j = g["joints"]
    assert list(j) == RL.IDS and len(j) == 22
    assert g["hauteur"] == 2.0 and g["axe_x"] == 0
    y = {k: v[1] for k, v in j.items()}
    assert y["head"] > y["neck_01"] > y["spine_03"] > y["spine_02"] > y["spine_01"] > y["pelvis"] > y["calf_l"] > y["foot_l"] > y["ball_l"]
    assert j["upperarm_l"][0] > j["clavicle_l"][0] > 0 and j["thigh_l"][0] > 0
    for k, v in j.items():
        assert -0.7 <= v[0] <= 0.7 and 0 <= v[1] <= 2.0, (k, v)
    # boîte de 1,4 m sur 2 : bras inclinés (pose en A), la main sous l'épaule ; plus étroite : bras le long du corps
    assert g["pose"] == "A" and j["hand_l"][1] < j["upperarm_l"][1]
    assert RL.gabarit({"min": [-0.3, 0, -0.2], "max": [0.3, 2.0, 0.2]})["pose"] == "bas"
    # une boîte en T (envergure = hauteur) : bras horizontaux
    t = RL.gabarit({"min": [-1.1, 0, -0.2], "max": [1.1, 2, 0.2]})
    assert t["pose"] == "T" and abs(t["joints"]["hand_l"][1] - t["joints"]["upperarm_l"][1]) < 1e-9
    # la profondeur du tronc remplace le milieu de la boîte (les pieds avancent)
    assert RL.gabarit({"min": [-1, 0, -0.2], "max": [1, 2, 0.6]}, centre_z=0.0)["joints"]["spine_02"][2] == 0.0


def test_le_gabarit_est_symetrique_autour_du_centre_de_la_boite():
    g = RL.gabarit({"min": [1.0, 0, 0], "max": [2.0, 2.0, 0.4]})
    assert g["axe_x"] == 1.5
    for i in RL.IDS + RL.IDS_POITRINE:
        p = (g["joints"].get(i) or g["poitrine"][i])
        q = (g["joints"].get(RL.paire(i)) or g["poitrine"].get(RL.paire(i))) if RL.paire(i) else None
        if q is None:
            assert abs(p[0] - 1.5) < 1e-9, i
        else:
            assert abs((p[0] + q[0]) / 2 - 1.5) < 1e-9 and p[1:] == q[1:], i


def test_la_proposition_lit_la_boite_du_mannequin_en_pose_en_t():
    p = RL.proposition(MAN)
    assert p["source"] == "gabarit" and p["pose"] == "T" and p["ordre"] == RL.IDS
    assert p["boite"] == {"min": [-0.9, 0.0, -0.1], "max": [0.9, 1.8, 0.2]}
    assert abs(p["hauteur"] - H) < 1e-9 and p["sommets"] > 300
    j = p["joints"]
    assert j["hand_l"][0] > 0.6 and j["hand_r"][0] < -0.6           # les mains vers le bout des bras
    assert 0.85 < j["pelvis"][1] < 1.0 and j["head"][1] > 1.5
    assert abs(j["spine_02"][2]) < 1e-9 and abs(j["ball_l"][2] - 0.065 * H) < 1e-9    # tronc en z = 0, pas la boîte
    assert set(p["poitrine"]) == {"breast_l", "breast_r"} and not p["avec_poitrine"]


# ── le rig ───────────────────────────────────────────────────────────────────

def test_le_rig_ecrit_une_peau_valide_de_22_os_aux_poids_normalises():
    j = RL.proposition(MAN)["joints"]
    out, rap = RL.rigger(MAN, j)
    assert rap["os"] == 22 and rap["methode"] == RL.METHODE and rap["sommets"] > 300
    doc, prims = _lire_peau(out)
    sk = doc["skins"][0]
    assert len(sk["joints"]) == 22 and [doc["nodes"][i]["name"] for i in sk["joints"]] == RL.IDS
    ibm = RL._flottants(doc, ME.lire_glb(out)[1], sk["inverseBindMatrices"])
    assert len(ibm) == 22
    for i, m in zip(sk["joints"], ibm):     # IBM = inverse de la position monde de l'os
        w = RL._mondes(doc)[0][i]
        assert all(abs(a + b) < 1e-5 for a, b in zip(m[12:15], w[12:15])), doc["nodes"][i]["name"]
    # parenté SMPL dans le graphe de nœuds
    par = ME._parents(doc["nodes"])
    noms = [n.get("name") for n in doc["nodes"]]
    for i, p in RL.PARENTS.items():
        if i in noms and p:
            assert noms[par[noms.index(i)]] == p, i
    n = 0
    for pos, js, ws in prims:
        for jv, wv in zip(js, ws):
            assert abs(sum(wv) - 1) < 1e-5 and all(w >= 0 for w in wv)
            assert all(0 <= x < 22 for x in jv)
            n += 1
    assert n == rap["sommets"]
    # le fichier, relu comme le bandeau le lit
    d = J / "lecture"
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(out)
    lu = SO.lire_glb(d / "model.glb")
    assert lu["rig"] == {"rigge": True, "os": 22, "animations": 0}
    assert lu["maillages"] == 1 and lu["sommets"] == rap["sommets"]


def test_les_poids_suivent_les_membres_et_ne_franchissent_pas_l_axe():
    j = RL.proposition(MAN)["joints"]
    out, _ = RL.rigger(MAN, j)
    _doc, prims = _lire_peau(out)
    k = {i: n for n, i in enumerate(RL.IDS)}
    for pos, js, ws in prims:
        for p, jv, wv in zip(pos, js, ws):
            if p[0] > 0.85:                                         # bout du bras gauche : la main
                assert _poids_de(jv, wv, k["hand_l"]) > 0.5, p
            if p[0] > 0.05 and p[1] < 0.6:                          # jambe gauche : aucun os de droite
                assert all(w == 0 or not RL.IDS[x].endswith("_r") for x, w in zip(jv, wv)), (p, jv, wv)
                assert _poids_de(jv, wv, k["calf_l"]) + _poids_de(jv, wv, k["thigh_l"]) \
                    + _poids_de(jv, wv, k["foot_l"]) + _poids_de(jv, wv, k["ball_l"]) > 0.99, p
            if p[1] > 1.7:                                          # haut de la tête
                assert _poids_de(jv, wv, k["head"]) > 0.85, p


def test_les_poids_sont_symetriques_en_miroir():
    j = RL.proposition(MAN)["joints"]
    out, _ = RL.rigger(MAN, j)
    _doc, prims = _lire_peau(out)
    pos, js, ws = prims[0]
    par_pos = {tuple(round(c, 5) for c in p): (jv, wv) for p, jv, wv in zip(pos, js, ws)}
    vus = 0
    for p, (jv, wv) in par_pos.items():
        q = (round(-p[0], 5) + 0.0, p[1], p[2])
        if p[0] <= 0.01 or q not in par_pos:
            continue
        jq, wq = par_pos[q]
        for x in set(jv):
            paire = RL.paire(RL.IDS[x]) or RL.IDS[x]
            assert abs(_poids_de(jv, wv, x) - _poids_de(jq, wq, RL.IDS.index(paire))) < 1e-5, (p, RL.IDS[x])
        vus += 1
    assert vus > 100, vus


def test_les_os_de_poitrine_portent_le_squelette_a_24():
    p = RL.proposition(MAN)
    out, rap = RL.rigger(MAN, {**p["joints"], **p["poitrine"]}, avec_poitrine=True)
    doc, _ = ME.lire_glb(out)
    assert rap["os"] == 24 and rap["poitrine"] and len(doc["skins"][0]["joints"]) == 24
    p2 = RL.proposition(out)
    assert p2["source"] == "rig" and p2["avec_poitrine"]


def test_un_modele_sous_un_parent_transforme_est_cuit_en_repere_monde():
    data = sous_parent(MAN)
    p = RL.proposition(data)
    b = p["boite"]
    assert all(abs(a - e) < 1e-6 for a, e in zip(b["min"], [2 - 0.45, 0.0, -1.05]))
    assert all(abs(a - e) < 1e-6 for a, e in zip(b["max"], [2 + 0.45, 0.9, -0.9]))
    out, _ = RL.rigger(data, p["joints"])
    doc, prims = _lire_peau(out)
    node = next(n for n in doc["nodes"] if "skin" in n)
    assert not any(k in node for k in ("translation", "rotation", "scale", "matrix"))
    xs = [q[0] for q in prims[0][0]]
    assert abs(min(xs) - 1.55) < 1e-5 and abs(max(xs) - 2.45) < 1e-5


def test_un_modele_deja_rigge_revient_a_sa_pose_de_repos_et_perd_ses_clips():
    # glb_cible porte nos noms d'os (convention Unreal) : ses articulations reviennent, en repère monde (armature
    # tournée de -90° en X et mise à l'échelle 0,01 : le bassin à (0, 0,95, 0))
    p0 = RL.proposition(SQ.glb_cible())
    assert p0["source"] == "rig" and all(abs(x - e) < 1e-6 for x, e in zip(p0["joints"]["pelvis"], [0, 0.95, 0]))
    # une peau dont les os passent sous une armature tournée (-90° X) et réduite (0,01), IBM inchangées : la pose de
    # repos (Σ w · J · IBM · p) est le mannequin tourné et réduit — c'est elle qui doit être cuite
    out0, _ = RL.rigger(MAN, RL.proposition(MAN)["joints"])
    doc0, binc0 = ME.lire_glb(out0)
    doc0["nodes"].append({"name": "Armature", "rotation": list(SQ.ARMATURE_R), "scale": [0.01] * 3, "children": [0]})
    sc = doc0["scenes"][0]["nodes"]
    sc[sc.index(0)] = len(doc0["nodes"]) - 1
    doc0["animations"] = [{"name": "vieux", "channels": [], "samplers": []}]   # un clip de l'ancien squelette
    src = ME.ecrire_glb(doc0, binc0)
    p = RL.proposition(src)
    attendu_min, attendu_max = [-0.009, -0.001, -0.018], [0.009, 0.002, 0.0]
    assert all(abs(x - e) < 1e-6 for x, e in zip(p["boite"]["min"], attendu_min)), p["boite"]
    assert all(abs(x - e) < 1e-6 for x, e in zip(p["boite"]["max"], attendu_max)), p["boite"]
    out, rap = RL.rigger(src, p["joints"])
    assert rap["retire"]["animations"] == 1 and rap["retire"]["os"] == 22
    doc, prims = _lire_peau(out)
    assert "animations" not in doc and len(doc["skins"]) == 1 and len(doc["nodes"]) == 23
    for c in range(3):
        vals = [q[c] for q in prims[0][0]]
        assert abs(min(vals) - attendu_min[c]) < 1e-6 and abs(max(vals) - attendu_max[c]) < 1e-6, c


def test_un_aller_retour_garde_les_articulations_placees():
    p = RL.proposition(MAN)
    j = dict(p["joints"])
    j["hand_l"] = [0.8, 1.44, 0.01]
    out, _ = RL.rigger(MAN, j)
    p2 = RL.proposition(out)
    assert p2["source"] == "rig" and p2["joints"]["hand_l"] == [0.8, 1.44, 0.01]
    out2, rap2 = RL.rigger(out, p2["joints"])            # re-rigger une version riggée
    assert rap2["os"] == 22 and RL.proposition(out2)["boite"] == p["boite"]


def test_les_refus_du_service():
    j = RL.proposition(MAN)["joints"]
    for mauvais, mot in (({k: v for k, v in j.items() if k != "head"}, "head"),
                         ({**j, "head": [0, float("nan"), 0]}, "head"), ({**j, "head": [0, 1]}, "head"),
                         ({**j, "head": [0, 99, 0]}, "hors du modèle"), ({**j, "queue": [0, 1, 0]}, "inconnu"),
                         ("pas un objet", "objet")):
        try:
            RL.rigger(MAN, mauvais)
            raise AssertionError(f"accepté : {mot}")
        except ValueError as e:
            assert mot in str(e), (mot, str(e))
    doc, binc = ME.lire_glb(MAN)
    doc["extensionsUsed"] = ["KHR_draco_mesh_compression"]
    try:
        RL.proposition(ME.ecrire_glb(doc, binc))
        raise AssertionError("draco accepté")
    except ValueError as e:
        assert "compressé" in str(e)
    # sans la poitrine demandée, ses os sont refusés s'ils manquent ; demandée, ils sont exigés
    try:
        RL.rigger(MAN, j, avec_poitrine=True)
        raise AssertionError("poitrine manquante acceptée")
    except ValueError as e:
        assert "breast_l" in str(e)


# ── les routes ───────────────────────────────────────────────────────────────

def _client():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


def test_les_routes_proposent_puis_ecrivent_une_version_riggee_sans_jamais_appeler_l_ia():
    from app.services import asset3d_rig, meshy_service
    appels = []

    async def sentinelle(*a, **k):
        appels.append((a, k))
        raise AssertionError("auto-rig IA appelé")
    vrai = asset3d_rig.rigger_asset3d
    asset3d_rig.rigger_asset3d = sentinelle
    _job("mannequin", {"model.glb": MAN})
    try:
        async def go():
            async with _client() as c:
                r1 = await c.get("/api/studio3d/rig/proposition/mannequin")
                j = r1.json()["joints"]
                j["hand_l"] = [0.82, 1.45, 0.0]
                r2 = await c.post("/api/studio3d/rig/appliquer/mannequin", json={"version": 1, "joints": j})
                r3 = await c.get("/api/studio3d/ouvert/mannequin")
                r4 = await c.get("/api/studio3d/rig/proposition/mannequin")
                r5 = await c.get("/api/studio3d/rig/proposition/mannequin", params={"version": 1})
                return r1, r2, r3, r4, r5
        r1, r2, r3, r4, r5 = asyncio.run(go())
    finally:
        asset3d_rig.rigger_asset3d = vrai
    assert appels == []
    assert r1.status_code == 200 and r1.json()["version"] == 1 and r1.json()["source"] == "gabarit"
    assert r2.status_code == 200, r2.text
    b = r2.json()
    assert (b["depuis"], b["version"], b["fichier"], b["os"]) == (1, 2, "model.v2.glb", 22)
    assert b["url"] == "/api/assets/3d/mannequin/version/2"
    f = r3.json()
    assert f["version"] == 2 and f["rig"] == {"rigge": True, "os": 22, "animations": 0}
    etape = next(v for v in f["versions"] if v["version"] == 2)
    assert (etape["operation"], etape["depuis"]) == ("rig_local", 1)       # la lignée de Préparer la lit
    assert r4.json()["source"] == "rig" and r4.json()["joints"]["hand_l"] == [0.82, 1.45, 0.0]
    assert r5.json()["source"] == "gabarit"
    assert (J / "mannequin" / "model.v2.glb").is_file() and (J / "mannequin" / "model.glb").read_bytes() == MAN
    assert meshy_service is not None


def test_les_routes_refusent_proprement():
    _job("mannequin2", {"model.glb": MAN})
    _job("abime_rig", {"model.glb": b"pas un glb"})
    j = RL.proposition(MAN)["joints"]

    async def go():
        async with _client() as c:
            return [
                await c.get("/api/studio3d/rig/proposition/inconnu"),
                await c.get("/api/studio3d/rig/proposition/mannequin2", params={"version": 7}),
                await c.post("/api/studio3d/rig/appliquer/mannequin2", json={"joints": {**j, "head": None}}),
                await c.post("/api/studio3d/rig/appliquer/mannequin2", json={"joints": "x"}),
                await c.post("/api/studio3d/rig/appliquer/mannequin2", json={"joints": j, "poitrine": "oui"}),
                await c.post("/api/studio3d/rig/appliquer/mannequin2", json={"joints": j, "version": 0}),
                await c.post("/api/studio3d/rig/appliquer/mannequin2", json={"joints": j, "version": 9}),
                await c.post("/api/studio3d/rig/appliquer/inconnu", json={"joints": j}),
                await c.get("/api/studio3d/rig/proposition/abime_rig"),
                await c.post("/api/studio3d/rig/appliquer/job$", json={"joints": j}),
            ]
    rs = asyncio.run(go())
    assert [r.status_code for r in rs] == [404, 404, 400, 400, 400, 400, 404, 404, 400, 400], [(r.status_code, r.text) for r in rs]
    assert "head" in rs[2].json()["detail"]
    # aucun refus n'a écrit de version
    assert sorted(f.name for f in (J / "mannequin2").glob("model*.glb")) == ["model.glb"]


def test_les_routes_du_rig_local_ne_touchent_a_aucun_fournisseur_payant():
    src = (RACINE / "backend/app/api/studio3d_rig_routes.py").read_text(encoding="utf-8") \
        + (RACINE / "backend/app/services/rig_local.py").read_text(encoding="utf-8")
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    code = re.sub(r'"""[\s\S]*?"""', "", code)
    for mot in ("meshy", "fal_client", "httpx", "requests", "_plafond", "pricing", "uthana", "openai"):
        assert mot not in code.lower(), mot


# ── la page ─────────────────────────────────────────────────────────────────

def test_l_ecran_est_branche_et_sa_feuille_n_a_aucun_rayon():
    coque = (RACINE / "frontend/studio3d/ecrans/coque.js").read_text(encoding="utf-8")
    assert 'rig: "./rig.js"' in coque
    html = (RACINE / "frontend/studio3d/index.html").read_text(encoding="utf-8")
    assert 'href="ecrans/rig.css"' in html and html.index('href="ecrans/ecrans.css"') < html.index('href="ecrans/rig.css"')
    css = (RACINE / "frontend/studio3d/ecrans/rig.css").read_text(encoding="utf-8")
    assert "border-radius" not in css
    js = (RACINE / "frontend/studio3d/ecrans/rig.js").read_text(encoding="utf-8")
    # l'IA payante : devis lu, confirmation, PUIS la route existante avec confirme_cout
    assert js.index("/rig/devis") < js.index("dlg.confirmer(") < js.index("confirme_cout: true")
    assert "/api/studio3d/rig/appliquer/" in js and "ctx.rafraichir()" in js


def test_le_squelette_du_front_est_celui_du_service():
    calc = (RACINE / "frontend/studio3d/ecrans/rig_calc.js").read_text(encoding="utf-8")
    os_js = re.findall(r'\["([a-z_0-9]+)", (?:"([a-z_0-9]+)"|null)\]', calc)
    assert [(i, p or None) for i, p in os_js] == RL.OS + RL.POITRINE


def test_les_cles_de_l_ecran_rig_existent_en_fr_et_en():
    dico = json.loads((RACINE / "frontend/shared/i18n/studio3decrans_rig.json").read_text(encoding="utf-8"))
    for k, v in dico.items():
        assert re.fullmatch(r"studio3decrans\.rigx\.[a-z0-9_]+", k), k
        assert v["fr"].strip() and v["en"].strip() and v.get("contexte") is True, k
        assert set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"])), k
    src = "".join((RACINE / "frontend/studio3d/ecrans" / f).read_text(encoding="utf-8") for f in ("rig.js", "rig_calc.js"))
    cles = {k for k in re.findall(r'"(rigx\.[a-z0-9_]+)"', src) if not k.endswith("_")}
    calc = (RACINE / "frontend/studio3d/ecrans/rig_calc.js").read_text(encoding="utf-8")
    familles = {"os": RL.IDS + RL.IDS_POITRINE, "pose": ["t", "a", "bas"],
                "ombrage": json.loads(calc.split("export const OMBRAGES = ", 1)[1].split(";", 1)[0]),
                "vue": json.loads(calc.split("export const VUES = ", 1)[1].split(";", 1)[0])}
    for fam, ids in familles.items():
        cles |= {f"rigx.{fam}_{i}" for i in ids}
    assert len(cles) > 80, len(cles)
    for k in cles:
        assert "studio3decrans." + k in dico, k
    assembled = (RACINE / "frontend/shared/dz-i18n-dico.js").read_text(encoding="utf-8")
    assert '"studio3decrans.rigx.recalculer"' in assembled, "relancer scripts/i18n_assembler.py"


def test_le_calcul_de_l_ecran_rig_sous_node():
    node = shutil.which("node")
    if not node:
        print("    (node absent : banc JS sauté)")
        return
    r = subprocess.run([node, str(RACINE / "frontend/studio3d/qa/rig.test.mjs")], capture_output=True,
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
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (écran Rig)")
    shutil.rmtree(_tmp, ignore_errors=True)
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
