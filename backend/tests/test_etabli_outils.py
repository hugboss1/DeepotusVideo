"""L'Établi — outils de préparation (plan 2026-09-03-plan-etabli). Tâche #88 PR A (T1-T2, 04/10/2026) : RÉPARER EN
UN CLIC, le module `mesh_repair` et la route `/api/etabli/reparer-maillage`.

DÉCISIONS DE L'UTILISATEUR (04/10) : le bouchage des trous est une option DÉCOCHÉE par défaut ; 2 PR (réparer, puis
profils). Écarts au plan corrigés : retournements comptés NETS (le plan comptait 19 sur 5 triangles retournés), le
cube aux dégénérés reste « fermé » pour mesh_report (qui saute les dégénérés : on compte nous-mêmes), l'échelle
négative inverse le verdict du volume, un maillage partagé n'est réparé qu'une fois, une boucle trop longue n'est
pas bouchée et c'est dit.

Le banc ne SORT jamais : les GLB sont fabriqués par gltf_builder et relus par print3d.
Témoin positif : la base (a832d79a) n'a ni mesh_repair ni la route.
Run : cd backend ; & $PY -m pytest tests/test_etabli_outils.py -q
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "ELEVENLABS_API_KEY", "HEYGEN_API_KEY"):
    os.environ[_k] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RACINE = pathlib.Path(__file__).resolve().parents[2]
BASE = "a832d79a"


def _cube() -> bytes:
    from app.services import gltf_builder
    return gltf_builder.build_glb({}, None, "cube", "banc")


def _volume(tris):
    return sum((a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0])
                + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0 for a, b, c in tris)


def _tris(data):
    from app.services import print3d
    return print3d.lire_glb_triangles(data)


def _ferme(data):
    """Fermé = chaque arête (par positions) vue exactement deux fois — dégénérés COMPRIS (mesh_report les saute)."""
    c = {}
    for t in _tris(data):
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            a, b = tuple(round(x, 9) for x in a), tuple(round(x, 9) for x in b)
            k = (a, b) if a <= b else (b, a)
            c[k] = c.get(k, 0) + 1
    return all(v == 2 for v in c.values())


def _refaire(data, f, noeud=None):
    """Le cube (ou un GLB) dont les triangles de la primitive 0 passent par `f(liste de triplets)`."""
    from app.services import mesh_cut, mesh_edit
    doc, binc = mesh_edit.lire_glb(data)
    pr = doc["meshes"][0]["primitives"][0]
    idx = [t[0] for t in mesh_cut._lire_accesseur(doc, binc, pr["indices"])]
    tris = [tuple(idx[k:k + 3]) for k in range(0, len(idx), 3)]
    tampon = bytearray(binc)
    pr["indices"] = mesh_cut._ajouter_indices(doc, tampon, f(tris))
    doc["buffers"] = [{"byteLength": len(tampon)}]
    if noeud:
        noeud(doc)
    return mesh_edit.ecrire_glb(doc, bytes(tampon))


def _cube_casse(quoi) -> bytes:
    """Le cube du dépôt (24 sommets, 12 triangles, fermé, volume 8) abîmé d'UNE façon."""
    f = {"trou": lambda t: t[2:],
         "doublons": lambda t: t + t[:3],
         "degeneres": lambda t: t + [(0, 0, 1), (5, 6, 6)],
         "normales": lambda t: [(x[0], x[2], x[1]) for x in t[:5]] + t[5:],
         "envers": lambda t: [(x[0], x[2], x[1]) for x in t]}[quoi]
    return _refaire(_cube(), f)


def test_temoin_la_base_n_a_ni_module_ni_route():
    r = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE)).stdout
    assert r and b"reparer-maillage" not in r
    assert subprocess.run(["git", "cat-file", "-e", f"{BASE}:backend/app/services/mesh_repair.py"],
                          capture_output=True, cwd=str(RACINE)).returncode != 0


def test_le_cube_est_sain_et_la_reparation_ne_change_rien():
    from app.services import mesh_repair
    assert _ferme(_cube()) and abs(_volume(_tris(_cube())) - 8.0) < 1e-9
    sortie, r = mesh_repair.reparer(_cube(), None, list(mesh_repair.ACTIONS))
    p = r["pieces"][0]
    assert (p["soudes"], p["doublons"], p["degeneres"], p["retournes"], p["trous"]["bouches"]) == (0, 0, 0, 0, 0), p
    assert len(_tris(sortie)) == 12 and r["ferme_avant"] is True and r["ferme_apres"] is True


def test_souder_respecte_les_coutures_UV_et_soude_un_vrai_double():
    from app.services import mesh_cut, mesh_edit, mesh_repair
    sortie, r = mesh_repair.reparer(_cube(), None, ["souder"])
    assert r["pieces"][0]["soudes"] == 0                 # 24 sommets, 8 positions, normales/UV différents : rien
    doc, binc = mesh_edit.lire_glb(_cube())
    pos = mesh_cut._lire_accesseur(doc, binc, doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"])
    assert len(pos) == 24 and len(set(pos)) == 8
    # sur la fonction : deux sommets identiques EN TOUT se soudent, une couture (attribut différent) non
    idx, n = mesh_repair.souder([(0, 0, 0), (0, 0, 0), (0, 0, 0), (1, 0, 0)], [[(0, 1), (0, 1), (5, 5), (0, 0)]],
                                [0, 1, 2, 1, 3, 2], 1e-6)
    assert n == 1 and idx == [0, 0, 2, 0, 3, 2]
    idx, n = mesh_repair.souder([(0, 0, 0), (1e-9, 0, 0)], [], [0, 1], 1e-6)         # à la tolérance près
    assert n == 1 and idx == [0, 0]


def test_reparer_retire_doublons_et_degeneres_et_le_DIT():
    from app.services import mesh_repair
    for quoi, n in (("doublons", 3), ("degeneres", 2)):
        casse = _cube_casse(quoi)
        assert not _ferme(casse)
        sortie, r = mesh_repair.reparer(casse, None, [quoi])
        assert r["pieces"][0][quoi] == n and r["ferme_avant"] is False and r["ferme_apres"] is True
        assert len(_tris(sortie)) == 12 and _ferme(sortie)


def test_les_normales_sont_unifiees_et_le_compte_est_NET():
    from app.services import mesh_repair
    casse = _cube_casse("normales")
    assert _volume(_tris(casse)) < 8.0 - 1e-9
    sortie, r = mesh_repair.reparer(casse, None, ["normales"])
    assert r["pieces"][0]["retournes"] == 5, r                 # NET : les cinq retournés, pas 19
    assert abs(_volume(_tris(sortie)) - 8.0) < 1e-9
    # tout à l'envers : la propagation ne voit rien, le VOLUME signé retourne tout
    sortie, r = mesh_repair.reparer(_cube_casse("envers"), None, ["normales"])
    assert r["pieces"][0]["retournes"] == 12 and abs(_volume(_tris(sortie)) - 8.0) < 1e-9


def test_une_echelle_negative_inverse_le_verdict_du_volume():
    """Un nœud en miroir (échelle −1 sur X) : le cube sain, vu dans le MONDE, est à l'envers. Le juger dans son
    repère local le laisserait tel quel — et le slicer recevrait un solide retourné."""
    from app.services import mesh_repair

    def miroir(doc):
        doc["nodes"][0]["scale"] = [-1.0, 1.0, 1.0]
    sain_en_miroir = _refaire(_cube(), lambda t: t, miroir)
    _sortie, r = mesh_repair.reparer(sain_en_miroir, None, ["normales"])
    assert r["pieces"][0]["retournes"] == 12, r


def test_reparer_bouche_un_trou_sur_demande_et_le_capuchon_est_bien_oriente():
    from app.services import mesh_repair
    troue = _cube_casse("trou")
    assert not _ferme(troue)
    sortie, r = mesh_repair.reparer(troue)                    # PAR DÉFAUT : les trous ne sont PAS bouchés
    assert "trous" not in r["actions"] and r["pieces"][0]["trous"] is None and r["ferme_apres"] is False
    sortie, r = mesh_repair.reparer(troue, None, ["trous"])
    t = r["pieces"][0]["trous"]
    assert t["bouches"] == 1 and t["non_bouches"] == 0 and t["triangles"] == 2
    assert _ferme(sortie) and abs(_volume(_tris(sortie)) - 8.0) < 1e-9
    assert r["ferme_avant"] is False and r["ferme_apres"] is True


def test_une_boucle_trop_longue_n_est_pas_bouchee_et_c_est_dit():
    from app.services import mesh_repair
    troue = _cube_casse("trou")
    from app.services import mesh_cut, mesh_edit
    doc, binc = mesh_edit.lire_glb(troue)
    pr = doc["meshes"][0]["primitives"][0]
    pos = mesh_cut._lire_accesseur(doc, binc, pr["attributes"]["POSITION"])
    idx = [t[0] for t in mesh_cut._lire_accesseur(doc, binc, pr["indices"])]
    tris = [tuple(idx[k:k + 3]) for k in range(0, len(idx), 3)]
    ajout, r = mesh_repair.trous(pos, tris, maxi=3)
    assert ajout == [] and r["non_bouches"] == 1 and "trop longue" in r["raisons"][0]


def test_une_jonction_n_est_pas_bouchee_et_c_est_dit():
    """Deux triangles qui ne partagent qu'UN sommet (un « nœud papillon ») : ce sommet a deux bords sortants. Suivre
    l'un au hasard fabriquerait un capuchon à travers les deux — on ne bouche pas, on le dit."""
    from app.services import mesh_repair
    pos = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, -1.0, 0.0)]
    ajout, r = mesh_repair.trous(pos, [(0, 1, 2), (0, 3, 4)])
    assert ajout == [] and r["jonctions"] == 1 and r["bouches"] == 0 and r["non_bouches"] >= 1, r
    assert "jonction" in r["raisons"][0]


def test_les_refus_sont_dits():
    from app.services import mesh_edit, mesh_repair
    doc, binc = mesh_edit.lire_glb(_cube())
    doc["extensionsRequired"] = ["KHR_draco_mesh_compression"]
    with pytest.raises(ValueError, match="draco"):
        mesh_repair.reparer(mesh_edit.ecrire_glb(doc, binc), None, ["trous"])
    with pytest.raises(ValueError, match="action inconnue"):
        mesh_repair.reparer(_cube(), None, ["lisser"])
    with pytest.raises(ValueError, match="aucune action"):
        mesh_repair.reparer(_cube(), None, [])
    with pytest.raises(ValueError, match="sans maillage"):
        mesh_repair.reparer(_cube(), [7], ["souder"])


def test_un_maillage_partage_n_est_repare_qu_une_fois_et_c_est_dit():
    from app.services import mesh_repair

    def jumeau(doc):
        doc["nodes"].append({"name": "jumeau", "mesh": doc["nodes"][0]["mesh"], "translation": [3, 0, 0]})
        doc["scenes"][0]["nodes"].append(len(doc["nodes"]) - 1)
    deux = _refaire(_cube(), lambda t: [(x[0], x[2], x[1]) for x in t[:5]] + t[5:], jumeau)
    sortie, r = mesh_repair.reparer(deux, None, ["normales"])
    a, b = r["pieces"]
    assert a["retournes"] == 5 and a["partage_avec"] == [1] and b["deja_repare"] is True and b["retournes"] == 0
    assert abs(_volume(_tris(sortie)) - 16.0) < 1e-9             # les deux cubes, chacun de volume 8


# ── la route ──────────────────────────────────────────────────────────────────────────────────────────────────────
def _client():
    import asyncio as _a
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.storage import init_db
    _a.run(init_db())
    return TestClient(app)


def _job(nom, data):
    from app.config import settings
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(data)
    return d


def test_la_route_ecrit_une_version_avec_son_rapport_et_refuse_les_corps_invalides():
    d = _job("job_rep", _cube_casse("trou"))
    with _client() as c:
        r = c.post("/api/etabli/reparer-maillage", json={"job": "job_rep", "version": 1, "actions": ["normales", "trous"]})
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["version"] == 2 and (d / "model.v2.glb").is_file()
        src = j["source"]
        assert src["operation"] == "reparer_maillage" and src["depuis"] == {"version": 1, "fichier": "model.glb"}
        assert src["ferme_apres"] is True and src["pieces"][0]["trous"]["bouches"] == 1
        assert _ferme((d / "model.v2.glb").read_bytes())
        # sans `actions` : la liste PAR DÉFAUT, sans les trous
        r = c.post("/api/etabli/reparer-maillage", json={"job": "job_rep", "version": 1})
        assert r.status_code == 200 and r.json()["source"]["actions"] == ["souder", "doublons", "degeneres", "normales"]
        for corps in ({"job": "job_rep", "version": 1, "actions": ["lisser"]}, {"job": "job_rep", "version": 1, "actions": []},
                      {"job": "job_rep", "version": 1, "actions": "trous"}, {"job": "job_rep", "version": "1"},
                      {"job": "..", "version": 1}, {"job": "job_rep", "version": 1, "noeuds": [-1]},
                      {"job": "job_rep", "version": 1, "noeuds": "0"}, {"job": "job_rep", "version": 1, "noeuds": [9]}):
            assert c.post("/api/etabli/reparer-maillage", json=corps).status_code == 400, corps
        assert c.post("/api/etabli/reparer-maillage", json={"job": "absent", "version": 1}).status_code == 404


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
