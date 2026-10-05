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



# ══ PR B : PROFILS D'IMPRIMANTE ET GARDE DU PLATEAU (tâche #88, plan-etabli T3-T4) ═══════════════════════════════
# DÉCISIONS (04/10) : la Centauri Carbon 2 intégrée par défaut ; les presets INSTANCIABLES d'Orca, groupés par marque,
# Elegoo en tête ; le choix est retenu, le preset actif du slicer seulement proposé ; la garde du profil dans
# creer_export ET creer_lot (XY triées, hauteur à part). Écarts du plan : presets communs listés (instantiation),
# `profil` passé en 7e position (= couleur), garde fausse sur un plateau non carré, préfixes d'id incohérents.

def _faux_orca(tmp):
    """La forme RÉELLE relevée le 04/10 : machine_model, preset instancié qui hérite d'un preset COMMUN (non
    instanciable mais qui porte un plateau), preset 0.2 sans printable_area, profil utilisateur, .conf + ligne MD5."""
    m = tmp / "OrcaSlicer" / "system" / "Elegoo" / "machine" / "ECC2"
    m.mkdir(parents=True)
    commun = tmp / "OrcaSlicer" / "system" / "Elegoo" / "machine"
    (commun / "fdm_elegoo_3dp_001_common.json").write_text(json.dumps({
        "type": "machine", "name": "fdm_elegoo_3dp_001_common", "instantiation": "false",
        "printable_area": ["0x0", "220x0", "220x220", "0x220"], "printable_height": "250"}), "utf-8")
    (m / "Elegoo Centauri Carbon 2.json").write_text(json.dumps({"type": "machine_model", "name": "Elegoo Centauri Carbon 2"}), "utf-8")
    (m / "Elegoo Centauri Carbon 2 0.4 nozzle.json").write_text(json.dumps({
        "type": "machine", "name": "Elegoo Centauri Carbon 2 0.4 nozzle", "instantiation": "true",
        "printable_area": ["0x0", "256x0", "256x256", "0x256"], "printable_height": "256",
        "bed_exclude_area": ["246x0", "256x0", "256x20", "246x20"], "inherits": "fdm_elegoo_3dp_001_common"}), "utf-8")
    (m / "Elegoo Centauri Carbon 2 0.2 nozzle.json").write_text(json.dumps({
        "type": "machine", "name": "Elegoo Centauri Carbon 2 0.2 nozzle", "instantiation": "true",
        "inherits": "Elegoo Centauri Carbon 2 0.4 nozzle", "nozzle_diameter": ["0.2"]}), "utf-8")
    a = tmp / "OrcaSlicer" / "system" / "Anycubic" / "machine"
    a.mkdir(parents=True)
    (a / "Anycubic Kobra 0.4 nozzle.json").write_text(json.dumps({
        "type": "machine", "name": "Anycubic Kobra 0.4 nozzle", "printable_area": ["0x0", "220x0", "220x220", "0x220"],
        "printable_height": "250"}), "utf-8")
    (a / "casse.json").write_text("{ pas du json", "utf-8")
    (a / "Orphelin.json").write_text(json.dumps({"type": "machine", "name": "Orphelin sans plateau"}), "utf-8")
    u = tmp / "OrcaSlicer" / "user" / "default" / "machine"
    u.mkdir(parents=True)
    (u / "Ma CC2 modifiee.json").write_text(json.dumps({"type": "machine", "name": "Ma CC2 modifiee",
                                                         "inherits": "Elegoo Centauri Carbon 2 0.4 nozzle",
                                                         "printable_height": "250"}), "utf-8")
    (tmp / "OrcaSlicer" / "OrcaSlicer.conf").write_text(
        '{\n"presets": {"machine": "Elegoo Centauri Carbon 2 0.2 nozzle", "filament": ["x"]},\n'
        '"autres": [{"machine": "ne pas lire"}]\n}\n# MD5 checksum 338F06710BD1E8116D5507BA509F20E1\n', "utf-8")
    return tmp


def test_temoin_la_base_n_a_pas_de_profils():
    assert subprocess.run(["git", "cat-file", "-e", "2a42aebd:backend/app/services/print_profiles.py"],
                          capture_output=True, cwd=str(RACINE)).returncode != 0


def test_les_profils_orca_sont_LUS_avec_leur_heritage_filtres_et_jamais_ecrits(tmp_path):
    from app.services import print_profiles as PP
    racine = _faux_orca(tmp_path)
    avant = sorted((str(p), p.stat().st_mtime_ns) for p in racine.rglob("*"))
    profils = PP.importer(racine / "OrcaSlicer", "orcaslicer")
    par = {p["nom"]: p for p in profils}
    assert sorted(par) == ["Anycubic Kobra 0.4 nozzle", "Elegoo Centauri Carbon 2 0.2 nozzle",
                           "Elegoo Centauri Carbon 2 0.4 nozzle", "Ma CC2 modifiee"], sorted(par)   # ni commun, ni modèle
    p2 = par["Elegoo Centauri Carbon 2 0.2 nozzle"]
    assert p2["plateau_mm"] == [256.0, 256.0] and p2["hauteur_mm"] == 256.0          # hérité du 0.4, pas du commun
    assert p2["exclusions_mm"] == [[246.0, 0.0, 256.0, 20.0]] and p2["id"] == "orcaslicer:Elegoo Centauri Carbon 2 0.2 nozzle"
    assert par["Ma CC2 modifiee"]["hauteur_mm"] == 250.0 and par["Ma CC2 modifiee"]["marque"] == "Mes profils du slicer"
    assert [p["marque"] for p in profils][:2] == ["Elegoo", "Elegoo"]                 # Elegoo en tête
    assert PP.profil_actif_du_slicer(racine / "OrcaSlicer") == "Elegoo Centauri Carbon 2 0.2 nozzle"   # malgré la ligne MD5
    assert sorted((str(p), p.stat().st_mtime_ns) for p in racine.rglob("*")) == avant  # LECTURE SEULE


def test_le_cache_suit_les_fichiers(tmp_path):
    from app.services import print_profiles as PP
    racine = _faux_orca(tmp_path) / "OrcaSlicer"
    n = len(PP.importer(racine, "orcaslicer"))
    (racine / "system" / "Elegoo" / "machine" / "ECC2" / "Neuve 0.4 nozzle.json").write_text(json.dumps({
        "type": "machine", "name": "Neuve 0.4 nozzle", "printable_area": ["0x0", "300x0", "300x300", "0x300"]}), "utf-8")
    assert len(PP.importer(racine, "orcaslicer")) == n + 1


def test_l_integre_par_defaut_le_choix_persiste_et_l_actif_du_slicer_est_seulement_propose(tmp_path, monkeypatch):
    from app.services import print_profiles as PP
    racine = _faux_orca(tmp_path)
    monkeypatch.setattr(PP, "_dossiers_slicers", lambda: [(racine / "OrcaSlicer", "orcaslicer")])
    monkeypatch.setattr(PP, "_fichier", lambda: tmp_path / "profils.json")
    l = PP.lister()
    assert l["profils"][0]["nom"] == "Elegoo Centauri Carbon 2" and l["actif"] == "integre:elegoo-centauri-carbon-2"
    assert l["actif_slicer"] == {"nom": "Elegoo Centauri Carbon 2 0.2 nozzle",
                                 "id": "orcaslicer:Elegoo Centauri Carbon 2 0.2 nozzle"}     # PROPOSÉ, pas actif
    assert PP.profil_courant()["plateau_mm"] == [256.0, 256.0] and PP.profil_courant()["hauteur_mm"] == 256.0
    PP.choisir("orcaslicer:Anycubic Kobra 0.4 nozzle")
    assert PP.lister()["actif"] == "orcaslicer:Anycubic Kobra 0.4 nozzle" and PP.profil_courant()["plateau_mm"] == [220.0, 220.0]
    PP.choisir("", {"nom": "Ma résine", "plateau_mm": [143.0, 89.6], "hauteur_mm": 175.0})
    assert PP.lister()["actif"] == "manuel:ma-resine" and PP.profil_courant()["plateau_mm"] == [143.0, 89.6]
    with pytest.raises(ValueError, match="inconnu"):
        PP.choisir("orcaslicer:nexiste-pas")
    for mauvais in ({"plateau_mm": [0, 10]}, {"plateau_mm": [10]}, {"plateau_mm": ["a", 2]}, {"plateau_mm": [10, 10], "hauteur_mm": -1}):
        with pytest.raises(ValueError):
            PP.choisir("", mauvais)
    # un preset qui disparaît du slicer : on retombe sur l'intégré, sans planter
    PP.choisir("orcaslicer:Anycubic Kobra 0.4 nozzle")
    (racine / "OrcaSlicer" / "system" / "Anycubic" / "machine" / "Anycubic Kobra 0.4 nozzle.json").unlink()
    assert PP.lister()["actif"] == "integre:elegoo-centauri-carbon-2"
    # le preset actif du slicer qui n'existe plus dans ses dossiers : rien à proposer
    conf = racine / "OrcaSlicer" / "OrcaSlicer.conf"
    conf.write_text('{"presets": {"machine": "Imprimante disparue"}}\n# MD5 checksum 0\n', "utf-8")
    assert PP.lister()["actif_slicer"] is None
    # un profils.json illisible retombe sur l'intégré
    (tmp_path / "profils.json").write_text("{cassé", "utf-8")
    assert PP.lister()["actif"] == "integre:elegoo-centauri-carbon-2"


def test_la_garde_est_celle_du_PROFIL_en_dimensions_triees_et_le_message_par_defaut_ne_change_pas(tmp_path):
    from app.services import print3d as P3
    from app.services import print_profiles as PP
    tris = P3.lire_glb_triangles(_cube())
    grand = P3.creer_export(tmp_path, "g", tris, 300.0)
    assert grand["avertissement"] == "300 mm dépasse le plateau de la Centauri Carbon 2 (256 mm) — le slicer devra couper ou réduire"
    resine = {"id": "manuel:r", "nom": "Ma résine", "plateau_mm": [143.0, 89.6], "hauteur_mm": 175.0}
    petit = P3.creer_export(tmp_path, "p", tris, 140.0, profil=resine)                 # 140 x 140 : la profondeur déborde
    assert "140 x 140 mm dépasse le plateau de Ma résine (143 x 90 mm)" in petit["avertissement"]
    meta = json.loads((tmp_path / petit["dossier"] / "impression.json").read_text("utf-8"))
    assert meta["profil"] == "Ma résine" and json.loads((tmp_path / grand["dossier"] / "impression.json").read_text("utf-8"))["profil"] == "Elegoo Centauri Carbon 2"
    # 140 x 80 mm TIENT sur 89,6 x 143 en tournant la pièce : dimensions TRIÉES
    assert PP.garde(((0, 80), (0, 140), (0, 10)), resine) is None
    assert PP.garde(((0, 80), (0, 140), (0, 180)), resine) == ("180 mm de haut dépasse la hauteur de Ma résine (175 mm) — "
                                                               "le slicer devra couper ou réduire")
    assert PP.garde(((0, 100), (0, 100), (0, 300)), None).startswith("300 mm de haut dépasse la hauteur de la Centauri Carbon 2 (256 mm)")
    assert PP.garde(((0, 256), (0, 256), (0, 256)), None) is None
    # la couleur garde sa place (7e argument) : le profil passe par MOT-CLÉ
    c = P3.creer_export(tmp_path, "c", tris, 50.0, "banc", "inconnue", "#ff0000", profil=resine)
    assert json.loads((tmp_path / c["dossier"] / "impression.json").read_text("utf-8"))["couleur"] == "#ff0000"


def test_le_lot_prend_aussi_la_garde_du_profil(tmp_path):
    from app.services import print3d as P3
    tris = P3.lire_glb_triangles(_cube())                              # un cube de 2 unités = 2 mm
    gros = [tuple(tuple(v * 60 for v in p) for p in t) for t in tris]   # 120 mm
    lot = P3.creer_lot(tmp_path, "l", [("a", gros)], "", "banc", profil={"id": "m", "nom": "Mini", "plateau_mm": [100.0, 100.0]})
    assert lot["avertissement"] == "120 mm dépasse le plateau de Mini (100 mm) — imprimer les pièces séparément (un STL par tuile)"
    assert P3.creer_lot(tmp_path, "l2", [("a", gros)], "", "banc").get("avertissement") is None


def test_les_routes_profils_listent_choisissent_et_l_impression_prend_le_profil_actif(tmp_path, monkeypatch):
    from app.services import print_profiles as PP
    racine = _faux_orca(tmp_path)
    monkeypatch.setattr(PP, "_dossiers_slicers", lambda: [(racine / "OrcaSlicer", "orcaslicer")])
    _job("job_prof", _cube())
    with _client() as c:
        l = c.get("/api/print3d/profils").json()
        assert l["actif"] == "integre:elegoo-centauri-carbon-2" and len(l["profils"]) == 5 and l["actif_slicer"]["nom"].endswith("0.2 nozzle")
        # ce que la page AFFICHE et DESSINE, rédigé ici (elle n'écrit aucune unité)
        cc2 = l["profils"][0]
        assert cc2["resume"] == "plateau 256 × 256 mm · hauteur 256 mm · 1 zone(s) exclue(s), en rouge sur la plaque"
        assert cc2["contour"] == {"l": 256.0, "p": 256.0, "zones": [[246.0, 0.0, 256.0, 20.0]]}
        r = c.post("/api/print3d/profils/actif", json={"manuel": {"nom": "Mini", "plateau_mm": [100, 100], "hauteur_mm": 100}})
        assert r.status_code == 200 and r.json()["actif"] == "manuel:mini" and r.json()["profil"]["plateau_mm"] == [100.0, 100.0]
        e = c.post("/api/print3d/from-assets3d/job_prof", json={"cible_mm": 120}).json()
        assert "Mini (100 mm)" in e["avertissement"], e
        r = c.post("/api/print3d/profils/actif", json={"id": "orcaslicer:Elegoo Centauri Carbon 2 0.4 nozzle"})
        assert r.status_code == 200 and r.json()["profil"]["exclusions_mm"] == [[246.0, 0.0, 256.0, 20.0]]
        for corps in ({"id": "orcaslicer:rien"}, {}, {"id": 3}, {"manuel": {"plateau_mm": [0, 1]}}, {"manuel": "x"}):
            assert c.post("/api/print3d/profils/actif", json=corps).status_code == 400, corps



# ══ PR C : RANGER SUR LE PLATEAU (tâche #89, plan-etabli T5) ═══════════════════════════════════════════════════════
# DÉCISIONS (05/10) : N plateaux dessinés ; refus sans taille cible. Écarts du plan corrigés : entrées malformées en 400
# (et non 500), calcul en unités du modèle (la page n'écrit aucune unité), rotation relative, pose dans le sens des règles.

def test_temoin_la_base_n_a_pas_de_rangement():
    assert subprocess.run(["git", "cat-file", "-e", "931dccaf:backend/app/services/nesting.py"],
                          capture_output=True, cwd=str(RACINE)).returncode != 0


def test_le_nesting_range_sans_chevauchement_et_TOURNE_quand_cela_fait_gagner():
    """96x40 et 40x96 sur 100x100, marge 2. À plat la seconde ne rentre pas ; tournée, elle se pose à v = 42. Sans
    rotation, la même paire prend DEUX plateaux."""
    from app.services import nesting
    pieces = [{"cle": "A", "l": 96.0, "p": 40.0}, {"cle": "B", "l": 40.0, "p": 96.0}]
    r = nesting.ranger(pieces, (100.0, 100.0), 2.0)
    assert len(r["plateaux"]) == 1 and not r["debordent"]
    poses = {q["cle"]: q for q in r["plateaux"][0]}
    assert poses["A"] == {"cle": "A", "u": 0.0, "v": 0.0, "rot": 0, "l": 96.0, "p": 40.0}
    assert poses["B"] == {"cle": "B", "u": 0.0, "v": 42.0, "rot": 90, "l": 40.0, "p": 96.0}
    assert r["taux"] == [0.768]
    boites = []
    for q in r["plateaux"][0]:
        l, prof = (q["p"], q["l"]) if q["rot"] == 90 else (q["l"], q["p"])
        assert q["u"] + l <= 100.0 + 1e-9 and q["v"] + prof <= 100.0 + 1e-9
        boites.append((q["u"], q["v"], q["u"] + l, q["v"] + prof))
    a, b = boites
    assert a[3] <= b[1] + 1e-9 or b[3] <= a[1] + 1e-9 or a[2] <= b[0] + 1e-9 or b[2] <= a[0] + 1e-9
    assert abs(poses["B"]["v"] - poses["A"]["p"] - 2.0) < 1e-9          # la marge, ENTRE les pièces
    assert len(nesting.ranger(pieces, (100.0, 100.0), 2.0, rotation=False)["plateaux"]) == 2


def test_aucun_chevauchement_sur_un_lot_aleatoire_et_les_plateaux_sont_bornes():
    import random
    from app.services import nesting
    random.seed(3)
    pieces = [{"cle": i, "l": random.uniform(5, 60), "p": random.uniform(5, 60)} for i in range(300)]
    r = nesting.ranger(pieces, (256.0, 256.0), 2.0, True, 3)
    assert len(r["plateaux"]) == 3 and r["debordent"]                     # borné à 3 : le reste DÉBORDE, dit
    assert sum(len(p) for p in r["plateaux"]) + len(r["debordent"]) == 300
    for pl in r["plateaux"]:
        bx = []
        for q in pl:
            l, prof = (q["p"], q["l"]) if q["rot"] == 90 else (q["l"], q["p"])
            assert q["u"] >= -1e-9 and q["v"] >= -1e-9 and q["u"] + l <= 256 + 1e-9 and q["v"] + prof <= 256 + 1e-9
            bx.append((q["u"], q["v"], q["u"] + l + 2.0, q["v"] + prof + 2.0))      # avec la marge
        for i in range(len(bx)):
            for j in range(i + 1, len(bx)):
                a, b = bx[i], bx[j]
                assert a[2] <= b[0] + 1e-6 or b[2] <= a[0] + 1e-6 or a[3] <= b[1] + 1e-6 or b[3] <= a[1] + 1e-6, (a, b)


def test_le_nesting_choisit_la_pose_la_plus_BASSE_range_le_plus_grand_d_abord_et_remplit_le_plateau_jusqu_au_bord():
    from app.services import nesting
    # A (60x50) en (0,0) ; B (40x10) à droite en (60,0) ; C (30x30) : à gauche il monterait à 50, à droite à 10 → (60, 10)
    r = nesting.ranger([{"cle": "A", "l": 60, "p": 50}, {"cle": "B", "l": 40, "p": 10}, {"cle": "C", "l": 30, "p": 30}],
                       (100.0, 100.0), 0.0, rotation=False)
    poses = {q["cle"]: (q["u"], q["v"]) for q in r["plateaux"][0]}
    assert poses == {"A": (0.0, 0.0), "B": (60.0, 0.0), "C": (60.0, 10.0)}, poses
    # le plus grand d'abord, quel que soit l'ordre reçu
    r = nesting.ranger([{"cle": "petit", "l": 5, "p": 5}, {"cle": "grand", "l": 50, "p": 40}], (100.0, 100.0), 2.0)
    assert r["plateaux"][0][0]["cle"] == "grand"
    # une pièce EXACTEMENT de la largeur du plateau tient (la marge gonfle la pièce ET le plateau)
    r = nesting.ranger([{"cle": "pleine", "l": 100, "p": 10}], (100.0, 100.0), 2.0, rotation=False)
    assert r["plateaux"][0][0]["u"] == 0.0 and r["plateaux"][0][0]["rot"] == 0 and not r["debordent"]


def test_la_zone_exclue_au_bord_avant_est_EVITEE_et_les_autres_sont_DITES():
    """Mesuré sur 8799 le 05/10 : sans zone, une pièce se posait dans la purge de la Centauri Carbon 2."""
    from app.services import nesting
    zone = [246.0, 0.0, 256.0, 20.0]
    pieces = [{"cle": i, "l": 40.0, "p": 30.0} for i in range(30)]
    r = nesting.ranger(pieces, (256.0, 256.0), 2.0, True, 1, [zone])
    assert r["exclusions_ignorees"] == 0
    for q in r["plateaux"][0]:
        l, prof = (q["p"], q["l"]) if q["rot"] == 90 else (q["l"], q["p"])
        hors = q["u"] + l <= zone[0] - 2.0 + 1e-9 or q["v"] >= zone[3] + 2.0 - 1e-9
        assert hors, (q, "dans la zone exclue, ou sans sa marge")
    # sans la zone, ce même rangement entrait dedans (le témoin)
    r0 = nesting.ranger(pieces, (256.0, 256.0), 2.0, True, 1)
    assert any(q["u"] + (q["p"] if q["rot"] else q["l"]) > 246 and q["v"] < 20 for q in r0["plateaux"][0])
    # une zone au MILIEU du plateau ne se représente pas dans un squelette : COMPTÉE, pas évitée en silence
    r = nesting.ranger([{"cle": 0, "l": 5, "p": 5}], (100.0, 100.0), 0.0, False, 8, [[0, 0, 50, 10], [10, 50, 20, 60]])
    assert r["exclusions_ignorees"] == 1 and (r["plateaux"][0][0]["u"], r["plateaux"][0][0]["v"]) == (50.0, 0.0)
    with pytest.raises(ValueError):
        nesting.ranger([{"cle": 0, "l": 5, "p": 5}], (100.0, 100.0), 0.0, False, 8, [["a", 0, 1, 1]])
    # une zone au MILIEU du bord avant : la marge vaut des DEUX côtés — la pièce posée à droite commence à 60 + 2
    r = nesting.ranger([{"cle": i, "l": 30, "p": 30} for i in range(2)], (100.0, 100.0), 2.0, False, 1, [[40, 0, 60, 20]])
    assert sorted((q["u"], q["v"]) for q in r["plateaux"][0]) == [(0.0, 0.0), (62.0, 0.0)], r


def test_le_nesting_dit_ce_qui_ne_rentre_sur_AUCUN_plateau_au_lieu_de_le_poser_dehors():
    from app.services import nesting
    r = nesting.ranger([{"cle": "trop", "l": 300.0, "p": 10.0}, {"cle": "ok", "l": 10.0, "p": 10.0}], (256.0, 256.0), 2.0)
    assert r["debordent"] == ["trop"] and [p["cle"] for p in r["plateaux"][0]] == ["ok"] and len(r["plateaux"]) == 1
    assert 0.0 < r["taux"][0] < 1.0


def test_le_nesting_refuse_les_entrees_qui_ne_sont_pas_des_cotes():
    from app.services import nesting
    for mauvais in ([], [{"cle": 1, "l": 0.0, "p": 5.0}], [{"cle": 1, "l": 5.0}], ["x"], [{"l": 1, "p": 1}],
                    [{"cle": 1, "l": float("inf"), "p": 1}]):
        with pytest.raises(ValueError):
            nesting.ranger(mauvais, (100.0, 100.0), 2.0)
    with pytest.raises(ValueError):
        nesting.ranger([{"cle": 1, "l": 5.0, "p": 5.0}], (0.0, 100.0), 2.0)
    with pytest.raises(ValueError):
        nesting.ranger([{"cle": 1, "l": 5.0, "p": 5.0}], (10.0, 100.0), -1)
    with pytest.raises(ValueError, match="budget"):
        nesting.ranger([{"cle": i, "l": 1.0, "p": 1.0} for i in range(1001)], (100.0, 100.0), 2.0)


def test_la_route_ranger_calcule_sans_rien_ecrire_et_juge_son_corps():
    with _client() as c:
        r = c.post("/api/etabli/ranger", json={"pieces": [{"cle": 0, "l": 60, "p": 10}, {"cle": 1, "l": 60, "p": 10}],
                                               "plateau": [100, 100], "marge": 2})
        d = r.json()
        assert r.status_code == 200 and len(d["plateaux"]) == 1 and len(d["plateaux"][0]) == 2
        un = c.post("/api/etabli/ranger", json={"pieces": [{"cle": i, "l": 90, "p": 90} for i in range(3)],
                                                "plateau": [100, 100], "plateaux_max": 2}).json()
        assert len(un["plateaux"]) == 2 and un["debordent"] == [2]
        paire = [{"cle": "A", "l": 96, "p": 40}, {"cle": "B", "l": 40, "p": 96}]
        assert len(c.post("/api/etabli/ranger", json={"pieces": paire, "plateau": [100, 100], "marge": 2}).json()["plateaux"]) == 1
        assert len(c.post("/api/etabli/ranger", json={"pieces": paire, "plateau": [100, 100], "marge": 2,
                                                      "rotation": False}).json()["plateaux"]) == 2
        z = c.post("/api/etabli/ranger", json={"pieces": [{"cle": 0, "l": 5, "p": 5}], "plateau": [100, 100], "marge": 0,
                                               "rotation": False, "exclusions": [[0, 0, 50, 10]]}).json()
        assert z["plateaux"][0][0]["u"] == 50.0 and z["exclusions_ignorees"] == 0, "la route TRANSMET les zones"
        for corps in ({"pieces": [], "plateau": [100, 100]}, {"pieces": [{"cle": 0, "l": 1, "p": 1}], "plateau": [100]},
                      {"pieces": [{"cle": 0, "l": 1, "p": 1}], "plateau": [100, 100], "marge": -1},
                      {"pieces": [{"cle": 0, "l": 1, "p": 1}], "plateau": [100, True]},
                      {"pieces": ["x"], "plateau": [100, 100]}, {"pieces": [{"l": 1, "p": 1}], "plateau": [100, 100]},
                      {"pieces": [{"cle": 0, "l": 1, "p": 1}], "plateau": [100, 100], "plateaux_max": 9},
                      {"pieces": [{"cle": 0, "l": 1, "p": 1}], "plateau": [100, 100], "exclusions": [[1, 2, 3]]},
                      {"pieces": [{"cle": 0, "l": 1, "p": 1}], "plateau": [100, 100], "exclusions": "zone"}):
            assert c.post("/api/etabli/ranger", json=corps).status_code == 400, corps


# ── tâche #89 PR D : extraire une par une, décimer dans la lignée ─────────────────────────────────────────────────
BASE_D = "2de62acc"


def test_temoin_la_base_d_n_a_ni_separement_ni_decimer():
    r = subprocess.run(["git", "show", f"{BASE_D}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE)).stdout
    assert r and b"separement" not in r and b"/etabli/decimer" not in r
    m = subprocess.run(["git", "show", f"{BASE_D}:backend/app/services/mesh_optimize.py"], capture_output=True,
                       cwd=str(RACINE)).stdout
    assert m and b"decimer_octets" not in m


def _png1x1() -> bytes:
    import struct
    import zlib

    def ch(tag: bytes, d: bytes) -> bytes:
        c = tag + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + ch(b"IDAT", zlib.compress(b"\x00\xff\xff\xff\xff")) + ch(b"IEND", b""))


def _cube_et_sol() -> bytes:
    """Recopié de test_etabli_socle.py : le quad de sol de gltf_builder donne un GLB à DEUX nœuds."""
    from app.services import gltf_builder
    return gltf_builder.build_glb({}, None, "cube", "banc", stage_png=_png1x1())


def _fiche(d, v):
    reg = json.loads((d / "report.json").read_text("utf-8"))
    return next(e for e in reg["entries"] if e["file"] == f"model.v{v}.glb")["source"]


def test_extraire_une_par_une_ecrit_UN_FICHIER_PAR_ELEMENT_toutes_nees_du_MEME_parent():
    from app.services import mesh_edit
    d = _job("job_sep", _cube_et_sol())
    assert len(mesh_edit.lire_glb(_cube_et_sol())[0]["nodes"]) == 2
    with _client() as c:
        r = c.post("/api/etabli/extraire", json={"job": "job_sep", "version": 1, "noeuds": [0, 1], "separement": True})
        assert r.status_code == 200, r.text
        corps = r.json()
    assert [v["version"] for v in corps["versions"]] == [2, 3]
    assert corps["version"] == 3, "la fiche rendue est la DERNIÈRE"
    noms = {}
    for v, noeud in ((2, 0), (3, 1)):
        fiche = _fiche(d, v)
        assert fiche["depuis"] == {"version": 1, "fichier": "model.glb"}, "des SŒURS, pas une chaîne"
        assert fiche["element"] == {"noeud": noeud, "rang": v - 2, "sur": 2} and fiche["noeuds"] == [noeud]
        assert fiche["operation"] == "extraire"
        doc, _ = mesh_edit.lire_glb((d / f"model.v{v}.glb").read_bytes())
        assert len(doc["nodes"]) == 1, "chaque fichier ne contient QUE son élément"
        noms[v] = doc["nodes"][0].get("name")
    src = mesh_edit.lire_glb(_cube_et_sol())[0]["nodes"]
    assert noms == {2: src[0].get("name"), 3: src[1].get("name")} and noms[2] != noms[3]


def test_extraire_ensemble_reste_ce_qu_elle_etait_et_separement_juge_son_corps():
    d = _job("job_sep2", _cube_et_sol())
    with _client() as c:
        r = c.post("/api/etabli/extraire", json={"job": "job_sep2", "version": 1, "noeuds": [0, 1]})
        assert r.status_code == 200 and r.json()["version"] == 2 and "versions" not in r.json()
        assert "element" not in _fiche(d, 2) and _fiche(d, 2)["noeuds"] == [0, 1]
        assert (d / "model.v2.glb").is_file() and not (d / "model.v3.glb").exists()
        for corps in ({"noeuds": [], "separement": True}, {"noeuds": [0], "separement": "oui"},
                      {"noeuds": [0], "separement": 1}, {"separement": True},
                      {"noeuds": [0, 0], "separement": True}, {"noeuds": [True], "separement": True},
                      {"noeuds": [-1], "separement": True}, {"noeuds": "0", "separement": True}):
            assert c.post("/api/etabli/extraire", json={"job": "job_sep2", "version": 1, **corps}).status_code == 400, corps
        # un élément refusé AU MILIEU : rien n'est écrit — pas une moitié de sœurs sur le disque
        r = c.post("/api/etabli/extraire", json={"job": "job_sep2", "version": 1, "noeuds": [0, 9], "separement": True})
        assert r.status_code == 400 and "élément par élément" in r.json()["detail"]
    assert not (d / "model.v3.glb").exists()


def _gltfpack_ou_skip():
    from app.services import mesh_optimize
    try:
        mesh_optimize._gltfpack()
    except RuntimeError:
        pytest.skip("gltfpack absent : la décimation ne peut pas être MESURÉE ici")


def _deux_tores(seg=60) -> bytes:
    """Deux tores NOMMÉS dans deux nœuds — de quoi voir si gltfpack les fond en un seul maillage anonyme."""
    import math
    import struct
    bin_ = b""
    vues, acc, meshes, nodes = [], [], [], []
    for k, nom in enumerate(("socle", "tour")):
        n = seg + 1
        pos = []
        for i in range(n):
            u = 2 * math.pi * i / seg
            for j in range(n):
                v = 2 * math.pi * j / seg
                R, r = 2.0 - 0.5 * k, 0.7 - 0.2 * k              # deux formes : gltfpack fond deux maillages IDENTIQUES en un
                pos += [(R + r * math.cos(v)) * math.cos(u), r * math.sin(v), (R + r * math.cos(v)) * math.sin(u)]
        idx = []
        for i in range(seg):
            for j in range(seg):
                a, b = i * n + j, (i + 1) * n + j
                idx += [a, b, a + 1, b, b + 1, a + 1]
        pb, ib = struct.pack(f"<{len(pos)}f", *pos), struct.pack(f"<{len(idx)}I", *idx)
        vues += [{"buffer": 0, "byteOffset": len(bin_), "byteLength": len(pb)},
                 {"buffer": 0, "byteOffset": len(bin_) + len(pb), "byteLength": len(ib)}]
        bin_ += pb + ib
        acc += [{"bufferView": 2 * k, "componentType": 5126, "count": len(pos) // 3, "type": "VEC3",
                 "min": [min(pos[0::3]), min(pos[1::3]), min(pos[2::3])],
                 "max": [max(pos[0::3]), max(pos[1::3]), max(pos[2::3])]},
                {"bufferView": 2 * k + 1, "componentType": 5125, "count": len(idx), "type": "SCALAR"}]
        meshes.append({"name": nom, "primitives": [{"attributes": {"POSITION": 2 * k}, "indices": 2 * k + 1}]})
        nodes.append({"name": nom, "mesh": k, "translation": [0.0, 3.0 * k, 0.0]})
    doc = {"asset": {"version": "2.0"}, "buffers": [{"byteLength": len(bin_)}], "bufferViews": vues,
           "accessors": acc, "meshes": meshes, "nodes": nodes, "scenes": [{"nodes": [0, 1]}], "scene": 0}
    from app.services import mesh_edit
    return mesh_edit.ecrire_glb(doc, bin_)


def test_decimer_rend_des_octets_GARDE_les_pieces_nommees_et_ne_touche_pas_au_job():
    _gltfpack_ou_skip()
    from app.services import mesh_edit, mesh_optimize as MO, print3d
    data = _deux_tores()                                   # 2 × 7 200 triangles
    octets, info = MO.decimer_octets(data, target_tris=1000)
    assert octets[:4] == b"glTF" and info["before"]["tris"] == 14400
    assert info["after"]["tris"] <= 1150 and info["target_tris"] == 1000 and info["preset"] is None
    assert info["reduction_pct"] == round(100.0 * (1 - info["after"]["tris"] / 14400), 1) and info["ratio"] == round(1000 / 14400, 6)
    doc, _ = mesh_edit.lire_glb(octets)
    # `-kn` : les DEUX pièces restent des nœuds NOMMÉS — sans lui gltfpack les fond en un maillage anonyme
    assert sorted(n.get("name") for n in doc["nodes"] if "mesh" in n) == ["socle", "tour"]
    assert "KHR_mesh_quantization" not in doc.get("extensionsUsed", []), "-noq : lisible par print3d et mesh_edit"
    assert len(print3d.lire_glb_triangles(octets)) == info["after"]["tris"]
    assert info["aggressive"] is False and info["cible_atteinte"] is True
    # la PASSE AGRESSIVE : à 500, la première passe reste au-dessus de 575 (mesuré 05/10)
    _o, ia = MO.decimer_octets(data, target_tris=500)
    assert ia["aggressive"] is True and ia["after"]["tris"] <= 575 and ia["cible_atteinte"] is True
    # et ce que gltfpack ne sait pas faire se DIT : à 100, il s'arrête bien au-dessus
    _o, ib = MO.decimer_octets(data, target_tris=100)
    assert ib["aggressive"] is True and ib["after"]["tris"] > 115 and ib["cible_atteinte"] is False
    # preset : la cible est celle de PRESETS
    _o, i2 = MO.decimer_octets(data, preset="game")
    assert i2["target_tris"] == 10000 and i2["preset"] == "game" and i2["after"]["tris"] < 14400


def test_decimer_juge_la_cible_AVANT_de_chercher_gltfpack_et_refuse_un_modele_deja_sous_la_cible(monkeypatch):
    from app.services import mesh_optimize as MO

    def absent():
        raise RuntimeError("gltfpack absent")
    monkeypatch.setattr(MO, "_gltfpack", absent)
    with pytest.raises(ValueError, match="preset inconnu"):
        MO.decimer_octets(_cube(), preset="inconnu")
    with pytest.raises(RuntimeError, match="absent"):
        MO.decimer_octets(_cube(), preset="game")
    monkeypatch.setattr(MO, "_gltfpack", lambda: "gltfpack-qui-ne-doit-pas-tourner")
    with pytest.raises(ValueError, match="rien à décimer"):
        MO.decimer_octets(_cube(), target_tris=100)        # 12 triangles, cible plancher 100


def test_la_route_decimer_ecrit_une_VERSION_dans_la_lignee_et_juge_son_corps(monkeypatch):
    d = _job("job_dec", _deux_tores())
    with _client() as c:
        for corps, code in (({"version": 1, "preset": "inconnu"}, 400), ({"version": "1"}, 400),
                            ({"version": 1, "target_tris": "beaucoup"}, 400)):
            assert c.post("/api/etabli/decimer", json={"job": "job_dec", **corps}).status_code == code, corps
        assert c.post("/api/etabli/decimer", json={"job": "..", "version": 1}).status_code == 400
        assert c.post("/api/etabli/decimer", json={"job": "job_dec", "version": 5}).status_code == 404
        _job("job_dec_cube", _cube())
        r = c.post("/api/etabli/decimer", json={"job": "job_dec_cube", "version": 1})
        assert r.status_code == 400 and "rien à décimer" in r.json()["detail"]
        assert not list((d.parent / "job_dec_cube").glob("model.v*.glb"))
        from app.services import mesh_optimize as MO

        def absent():
            raise RuntimeError("gltfpack absent")
        monkeypatch.setattr(MO, "_gltfpack", absent)
        r = c.post("/api/etabli/decimer", json={"job": "job_dec", "version": 1})
        assert r.status_code == 502 and "absent" in r.json()["detail"], "l'outil manquant se DIT, sans rien écrire"
        assert not (d / "model.v2.glb").exists()
        monkeypatch.undo()
        _gltfpack_ou_skip()
        r = c.post("/api/etabli/decimer", json={"job": "job_dec", "version": 1, "target_tris": 2000})
        assert r.status_code == 200, r.text
        j = r.json()
    assert j["version"] == 2 and (d / "model.v2.glb").is_file()
    src = _fiche(d, 2)
    assert src["operation"] == "decimer" and src["depuis"] == {"version": 1, "fichier": "model.glb"}
    assert src["before"]["tris"] == 14400 and src["after"]["tris"] <= 2300 and src["target_tris"] == 2000
    assert not (d / "model.opt.glb").exists() and not (d / "optimize.json").exists(), "AUCUN fichier à part"

# ── tâche #89 PR E : creuser (plan-etabli T6 corrigé) ──────────────────────────────────────────────────────────────
BASE_E = "df8cce69"


def test_temoin_la_base_e_n_a_ni_module_ni_route_de_creusage():
    r = subprocess.run(["git", "show", f"{BASE_E}:backend/app/api/routes.py"], capture_output=True, cwd=str(RACINE)).stdout
    assert r and b"/etabli/creuser" not in r
    assert subprocess.run(["git", "cat-file", "-e", f"{BASE_E}:backend/app/services/hollow.py"],
                          capture_output=True, cwd=str(RACINE)).returncode != 0


def _boite(l, p, h) -> bytes:
    """Une boîte FERMÉE et soudée (8 sommets partagés, 12 triangles sortants), centrée sur l'origine."""
    import struct
    from app.services import mesh_edit
    x, y, z = l / 2, p / 2, h / 2
    pos = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z), (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    tris = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
            (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    pb = struct.pack("<24f", *[c for q in pos for c in q])
    ib = struct.pack("<36H", *[i for q in tris for i in q])
    doc = {"asset": {"version": "2.0"}, "buffers": [{"byteLength": len(pb) + len(ib)}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(pb)},
                           {"buffer": 0, "byteOffset": len(pb), "byteLength": len(ib)}],
           "accessors": [{"bufferView": 0, "componentType": 5126, "count": 8, "type": "VEC3",
                          "min": [-x, -y, -z], "max": [x, y, z]},
                         {"bufferView": 1, "componentType": 5123, "count": 36, "type": "SCALAR"}],
           "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
           "nodes": [{"name": "boite", "mesh": 0}], "scenes": [{"nodes": [0]}], "scene": 0}
    return mesh_edit.ecrire_glb(doc, pb + ib)


def test_creuser_le_cube_du_depot_SOUDE_puis_tient_la_paroi_de_CHAQUE_face_et_garde_le_dehors_intact():
    """Le cube de gltf_builder a 24 sommets — une copie par face. Sans soudure, chaque copie suivrait SA face et la
    peau intérieure se déchirerait ; avec, la coque est fermée, et l'intérieur est à `paroi` de chaque face (coins à
    √3 × paroi) : volume 2³ − 1,5³ exactement."""
    from app.services import hollow, mesh_edit, print3d
    sortie, r = hollow.creuser(_cube(), None, 0.25)
    tris = _tris(sortie)
    assert len(tris) == 24 and abs(_volume(tris) - (8.0 - 1.5 ** 3)) < 1e-9
    assert _ferme(sortie), "soudée, la peau intérieure ne se déchire pas"
    p = r["pieces"][0]
    assert (p["effondres"], p["plafonnes"], p["paroi"], p["paroi_max"]) == (0, 0, 0.25, 0.25)
    assert p["triangles_avant"] == 12 and p["normales_rentrantes"] is False and r["avertissement"] is None
    assert "plus mince que deux parois" in r["limite"]
    # le DEHORS est intact : même primitive, mêmes attributs (UV, normales), même matériau ; le dedans est une
    # primitive DE PLUS, POSITION seule, même matériau
    avant, _ = mesh_edit.lire_glb(_cube())
    doc, _ = mesh_edit.lire_glb(sortie)
    prims = doc["meshes"][0]["primitives"]
    assert len(prims) == 2 and set(prims[0]["attributes"]) == set(avant["meshes"][0]["primitives"][0]["attributes"])
    assert list(prims[1]["attributes"]) == ["POSITION"] and prims[1].get("material") == prims[0].get("material")
    dedans = doc["accessors"][prims[1]["attributes"]["POSITION"]]
    assert dedans["min"] == [-0.75] * 3 and dedans["max"] == [0.75] * 3, "l'épaisseur est CONSTANTE"
    assert print3d.bbox(tris) == ((-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0))


def test_creuser_COMPTE_l_effondrement_et_cherche_la_paroi_qui_tient():
    from app.services import hollow
    _s, r = hollow.creuser(_cube(), None, 1.5)               # plus que la demi-arête : retournée en entier
    p = r["pieces"][0]
    assert p["effondres"] == 12 and 1.0 - 1.5 / 4096 <= p["paroi_max"] <= 1.0 and r["paroi_max"] == p["paroi_max"]
    assert "effondré" in r["avertissement"] and "auto-intersecte" in r["avertissement"]
    # une PLAQUE plus mince que deux parois : les deux faces se croisent par translation, AUCUNE normale ne bascule ;
    # c'est le volume intérieur, retourné, qui le dit
    _s, r = hollow.creuser(_boite(4.0, 4.0, 0.2), None, 0.15)
    assert r["pieces"][0]["effondres"] == 12 and 0.1 - 0.15 / 4096 <= r["paroi_max"] <= 0.1
    _s, r = hollow.creuser(_boite(4.0, 4.0, 0.2), None, 0.05)
    assert r["pieces"][0]["effondres"] == 0 and r["avertissement"] is None


def _prisme_en_T() -> bytes:
    """Un socle 4 × 2 surmonté d'une AILETTE de 0,2 de large, extrudé sur 2 : fermé, soudé, sans jonction en T."""
    import struct
    from app.services import mesh_edit
    profil = [(-2, 0), (2, 0), (2, 2), (0.1, 2), (0.1, 4), (-0.1, 4), (-0.1, 2), (-2, 2)]
    n = len(profil)
    pos = [(x, y, -1.0) for x, y in profil] + [(x, y, 1.0) for x, y in profil]
    cap = [(0, 1, 2), (0, 2, 3), (0, 3, 6), (0, 6, 7), (3, 4, 5), (3, 5, 6)]      # socle en éventail + ailette
    tris = [(a, c, b) for a, b, c in cap] + [(a + n, b + n, c + n) for a, b, c in cap]
    for i in range(n):
        j = (i + 1) % n
        tris += [(i, j, j + n), (i, j + n, i + n)]
    pb = struct.pack(f"<{3 * len(pos)}f", *[c for q in pos for c in q])
    ib = struct.pack(f"<{3 * len(tris)}H", *[i for q in tris for i in q])
    doc = {"asset": {"version": "2.0"}, "buffers": [{"byteLength": len(pb) + len(ib)}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(pb)},
                           {"buffer": 0, "byteOffset": len(pb), "byteLength": len(ib)}],
           "accessors": [{"bufferView": 0, "componentType": 5126, "count": len(pos), "type": "VEC3",
                          "min": [-2, 0, -1], "max": [2, 4, 1]},
                         {"bufferView": 1, "componentType": 5123, "count": 3 * len(tris), "type": "SCALAR"}],
           "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
           "nodes": [{"name": "T", "mesh": 0}], "scenes": [{"nodes": [0]}], "scene": 0}
    return mesh_edit.ecrire_glb(doc, pb + ib)


def test_une_AILETTE_plus_mince_que_deux_parois_sur_un_socle_epais_est_COMPTEE():
    """Le volume intérieur reste positif (le socle domine) : seul le retournement des triangles de l'ailette le voit."""
    from app.services import hollow
    data = _prisme_en_T()
    assert _ferme(data) and _volume(_tris(data)) > 0
    _s, r = hollow.creuser(data, None, 0.15)
    p = r["pieces"][0]
    assert 0 < p["effondres"] < p["triangles_avant"], p
    assert 0.0 < p["paroi_max"] < 0.15 and "effondré" in r["avertissement"]
    _s, r = hollow.creuser(data, None, 0.05)
    assert r["pieces"][0]["effondres"] == 0


def test_creuser_PLAFONNE_l_arete_vive_et_le_dit():
    """Un coin très aigu : 1 / min(n_sommet · n_face) y explose. Le décalage est plafonné à PLAFOND parois, et les
    sommets plafonnés sont comptés — la paroi y est plus mince que demandé."""
    import struct
    from app.services import hollow, mesh_edit
    # un tétraèdre très effilé : trois sommets en triangle plat, le quatrième loin au-dessus
    pos = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.5, 0.866, 0.0), (0.5, 0.289, 20.0)]
    tris = [(0, 2, 1), (0, 1, 3), (1, 2, 3), (2, 0, 3)]
    pb = struct.pack("<12f", *[c for q in pos for c in q])
    ib = struct.pack("<12H", *[i for q in tris for i in q])
    doc = {"asset": {"version": "2.0"}, "buffers": [{"byteLength": len(pb) + len(ib)}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(pb)},
                           {"buffer": 0, "byteOffset": len(pb), "byteLength": len(ib)}],
           "accessors": [{"bufferView": 0, "componentType": 5126, "count": 4, "type": "VEC3",
                          "min": [0, 0, 0], "max": [1, 0.866, 20]},
                         {"bufferView": 1, "componentType": 5123, "count": 12, "type": "SCALAR"}],
           "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
           "nodes": [{"mesh": 0}], "scenes": [{"nodes": [0]}], "scene": 0}
    s, r = hollow.creuser(mesh_edit.ecrire_glb(doc, pb + ib), None, 0.01)
    assert r["pieces"][0]["plafonnes"] >= 1 and "arête vive" in r["avertissement"] and "plafonné à 3" in r["avertissement"]
    # le PLAFOND lui-même : aucun sommet ne s'enfonce de plus de 3 parois, et la pointe s'y arrête exactement
    d2, b2 = mesh_edit.lire_glb(s)
    from app.services import mesh_cut
    dedans = mesh_cut._lire_accesseur(d2, b2, d2["meshes"][0]["primitives"][1]["attributes"]["POSITION"])
    ecarts = [sum((a - b) ** 2 for a, b in zip(p0, p1)) ** 0.5 for p0, p1 in zip(pos, dedans)]
    assert max(ecarts) <= 3 * 0.01 + 1e-6 and abs(max(ecarts) - 3 * 0.01) < 1e-6, ecarts


def test_creuser_suit_l_echelle_MONDE_et_l_orientation_LOCALE():
    from app.services import hollow, mesh_edit
    # échelle uniforme 2 : 0,5 dans le monde = 0,25 dans le repère du nœud
    deux = _refaire(_cube(), lambda t: t, lambda d: d["nodes"][0].update({"scale": [2.0, 2.0, 2.0]}))
    s, r = hollow.creuser(deux, None, 0.5)
    doc, _ = mesh_edit.lire_glb(s)
    acc = doc["accessors"][doc["meshes"][0]["primitives"][1]["attributes"]["POSITION"]]
    assert r["pieces"][0]["echelle_monde"] == 2.0 and acc["max"] == [0.75] * 3 and r["pieces"][0]["paroi"] == 0.5
    # la paroi qui tient se dit dans le MONDE : demi-arête 2 (et non 1, celle du repère du nœud)
    _s, r = hollow.creuser(deux, None, 3.0)
    assert 2.0 - 3.0 / 4096 <= r["paroi_max"] <= 2.0
    # une échelle NON uniforme : une même paroi n'aurait pas la même épaisseur selon l'axe — refus dit
    plat = _refaire(_cube(), lambda t: t, lambda d: d["nodes"][0].update({"scale": [2.0, 2.0, 0.5]}))
    with pytest.raises(ValueError, match="non uniforme"):
        hollow.creuser(plat, None, 0.1)
    # normales RENTRANTES : on creuse quand même vers le dedans, et la coque reste cohérente avec le dehors
    s, r = hollow.creuser(_cube_casse("envers"), None, 0.25)
    doc, _ = mesh_edit.lire_glb(s)
    acc = doc["accessors"][doc["meshes"][0]["primitives"][1]["attributes"]["POSITION"]]
    assert r["pieces"][0]["normales_rentrantes"] is True and acc["max"] == [0.75] * 3
    assert abs(_volume(_tris(s)) + (8.0 - 1.5 ** 3)) < 1e-9


def test_creuser_EXIGE_un_maillage_ferme_et_refuse_ce_qu_il_ne_sait_pas_lire():
    from app.services import hollow, mesh_edit
    with pytest.raises(ValueError, match="non fermé"):
        hollow.creuser(_cube_casse("trou"), None, 0.1)
    for paroi in (0.0, -1.0, "2", True, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="paroi"):
            hollow.creuser(_cube(), None, paroi)
    doc, binc = mesh_edit.lire_glb(_cube())
    doc["extensionsRequired"] = ["KHR_draco_mesh_compression"]
    with pytest.raises(ValueError, match="draco"):
        hollow.creuser(mesh_edit.ecrire_glb(doc, binc), None, 0.1)
    with pytest.raises(ValueError, match="sans maillage"):
        hollow.creuser(_cube(), [999], 0.1)
    anime = _refaire(_cube(), lambda t: t, lambda d: (d["nodes"][0].update({"skin": 0}), d.update({"skins": [{"joints": [0]}]})))
    with pytest.raises(ValueError, match="skin"):
        hollow.creuser(anime, None, 0.1)


def test_creuser_au_dela_du_budget_refuse_et_propose_de_decimer(monkeypatch):
    from app.services import hollow
    monkeypatch.setattr(hollow, "MAX_TRIS", 11)
    with pytest.raises(ValueError, match="Décime d'abord"):
        hollow.creuser(_cube(), None, 0.1)
    monkeypatch.setattr(hollow, "MAX_TRIS", 12)
    hollow.creuser(_cube(), None, 0.1)


def test_un_maillage_PARTAGE_est_clone_creuser_l_un_ne_creuse_pas_l_autre():
    from app.services import hollow, mesh_edit

    def jumeau(d):
        d["nodes"].append({"name": "jumeau", "mesh": 0, "translation": [5.0, 0.0, 0.0]})
        d["scenes"][0]["nodes"].append(len(d["nodes"]) - 1)
    data = _refaire(_cube(), lambda t: t, jumeau)
    doc0, _ = mesh_edit.lire_glb(data)
    j = next(i for i, n in enumerate(doc0["nodes"]) if n.get("name") == "jumeau")
    s, r = hollow.creuser(data, [0], 0.25)
    doc, _ = mesh_edit.lire_glb(s)
    p = r["pieces"][0]
    assert p["partage_avec"] == [j]
    creuse = doc["nodes"][p["noeud_apres"]]
    autre = next(n for n in doc["nodes"] if n.get("name") == "jumeau")
    assert creuse["mesh"] != autre["mesh"]
    assert len(doc["meshes"][creuse["mesh"]]["primitives"]) == 2 and len(doc["meshes"][autre["mesh"]]["primitives"]) == 1


def test_la_route_creuser_ecrit_une_version_GARDE_la_saisie_et_juge_son_corps():
    d = _job("job_creux", _cube())
    with _client() as c:
        r = c.post("/api/etabli/creuser", json={"job": "job_creux", "version": 1, "paroi": 0.25,
                                                "paroi_millimetres": 2.0})
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["version"] == 2 and (d / "model.v2.glb").is_file()
        src = j["source"]
        assert src["operation"] == "creuser" and src["depuis"] == {"version": 1, "fichier": "model.glb"}
        assert src["paroi_millimetres"] == 2.0 and src["pieces"][0]["paroi"] == 0.25, "AUCUNE conversion à la route"
        assert src["avertissement"] is None and src["limite"]
        r = c.post("/api/etabli/creuser", json={"job": "job_creux", "version": 1, "paroi": 0.25, "noeuds": [0]})
        assert r.status_code == 200 and "paroi_millimetres" not in r.json()["source"]
        for corps in ({"paroi": 0}, {"paroi": "0.25"}, {"paroi": True}, {}, {"paroi": 0.25, "paroi_millimetres": -2},
                      {"paroi": 0.25, "paroi_millimetres": "2"}, {"paroi": 0.25, "noeuds": ["a"]},
                      {"paroi": 0.25, "noeuds": [-1]}, {"paroi": 0.25, "noeuds": 0}):
            assert c.post("/api/etabli/creuser", json={"job": "job_creux", "version": 1, **corps}).status_code == 400, corps
        _job("job_creux_ouvert", _cube_casse("trou"))
        r = c.post("/api/etabli/creuser", json={"job": "job_creux_ouvert", "version": 1, "paroi": 0.1})
        assert r.status_code == 400 and "non fermé" in r.json()["detail"] and "Réparer le maillage" in r.json()["detail"]
    assert not list((d.parent / "job_creux_ouvert").glob("model.v*.glb"))


# ── T090 / plan T12 : UN SEUL lecteur d'accesseur, et il APPLIQUE `sparse` ─────
def _cube_sparse() -> bytes:
    """Le cube du dépôt, dont UN sommet est déplacé par un accesseur `sparse`.

    glTF 2.0 §3.6.2.3 : `sparse` remplace `count` valeurs de l'accesseur de base, désignées par des index. Un
    lecteur qui l'ignore rend la géométrie d'AVANT la substitution."""
    import struct as _s
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube())
    acc = doc["accessors"][doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"]]
    tampon = bytearray(binc)
    while len(tampon) % 4:
        tampon.append(0)
    off_i = len(tampon); tampon += _s.pack("<H", 0)
    while len(tampon) % 4:
        tampon.append(0)
    off_v = len(tampon); tampon += _s.pack("<3f", -3.0, -3.0, -3.0)
    n = len(doc["bufferViews"])
    doc["bufferViews"] += [{"buffer": 0, "byteOffset": off_i, "byteLength": 2},
                           {"buffer": 0, "byteOffset": off_v, "byteLength": 12}]
    acc["sparse"] = {"count": 1,
                     "indices": {"bufferView": n, "byteOffset": 0, "componentType": 5123},
                     "values": {"bufferView": n + 1, "byteOffset": 0}}
    acc["min"] = [-3.0, -3.0, -3.0]
    doc["buffers"] = [{"byteLength": len(tampon)}]
    return mesh_edit.ecrire_glb(doc, bytes(tampon))


def test_UN_SEUL_lecteur_et_il_APPLIQUE_sparse_pour_les_deux_appelants():
    from app.services import mesh_cut, mesh_edit, print3d
    data = _cube_sparse()
    doc, binc = mesh_edit.lire_glb(data)
    i = doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
    pos = mesh_edit.lire_accesseur(doc, binc, i)
    assert pos[0] == (-3.0, -3.0, -3.0)              # la substitution est APPLIQUÉE
    assert sum(1 for p in pos if p == (-3.0, -3.0, -3.0)) == 1
    # les deux anciens lecteurs délèguent : même réponse, plus de refus, plus de silence
    assert mesh_cut._lire_accesseur(doc, binc, i)[0] == (-3.0, -3.0, -3.0)
    assert print3d._accessor(doc, binc, i)[0] == (-3.0, -3.0, -3.0)
    b = print3d.bbox(print3d.lire_glb_triangles(data))
    assert abs(b[0][0] - (-3.0)) < 1e-6              # le lecteur de print3d aussi


def test_le_lecteur_unique_garde_les_PERIMETRES_de_chaque_appelant():
    """`print3d` ne sait écrire que float32 / u16 / u32 ; `mesh_cut` lit tous les composants de glTF. Unifier ne
    doit pas ÉLARGIR print3d en douce : le périmètre reste un argument de l'appelant, et le refus garde son mot."""
    from app.services import mesh_edit, print3d
    doc, binc = mesh_edit.lire_glb(_cube())
    i = doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
    doc["accessors"][i]["componentType"] = 5121      # u8 : hors périmètre print3d
    with pytest.raises(ValueError, match="hors périmètre"):
        print3d._accessor(doc, binc, i)
    assert len(mesh_edit.lire_accesseur(doc, binc, i)) > 0   # le lecteur générique, lui, sait le lire


def test_un_accesseur_sans_bufferView_part_de_ZERO_comme_le_dit_glTF():
    """glTF 2.0 : quand `bufferView` est absent, les valeurs de base sont NULLES et `sparse` les remplace.
    `mesh_cut` le refusait ; il ne le refuse plus, il l'applique."""
    import struct as _s
    from app.services import mesh_edit
    doc, binc = mesh_edit.lire_glb(_cube())
    tampon = bytearray(binc)
    while len(tampon) % 4:
        tampon.append(0)
    oi = len(tampon); tampon += _s.pack("<H", 1)
    while len(tampon) % 4:
        tampon.append(0)
    ov = len(tampon); tampon += _s.pack("<3f", 7.0, 8.0, 9.0)
    n = len(doc["bufferViews"])
    doc["bufferViews"] += [{"buffer": 0, "byteOffset": oi, "byteLength": 2},
                           {"buffer": 0, "byteOffset": ov, "byteLength": 12}]
    doc["accessors"].append({"componentType": 5126, "type": "VEC3", "count": 3,
                             "sparse": {"count": 1,
                                        "indices": {"bufferView": n, "byteOffset": 0, "componentType": 5123},
                                        "values": {"bufferView": n + 1, "byteOffset": 0}}})
    doc["buffers"] = [{"byteLength": len(tampon)}]
    vals = mesh_edit.lire_accesseur(doc, bytes(tampon), len(doc["accessors"]) - 1)
    assert vals == [(0.0, 0.0, 0.0), (7.0, 8.0, 9.0), (0.0, 0.0, 0.0)]


def test_il_n_y_a_plus_qu_UN_lecteur_d_accesseur_dans_le_depot():
    """La dette se referme par une assertion, pas par une intention : deux lecteurs d'un `bufferView` dans deux
    modules, et le silence revient au premier fichier `sparse`.

    Le périmètre est `app/services/*.py`, SANS les sous-dossiers : `cards/gltf.py` relit le tampon que
    `gltf_builder` vient d'écrire pour reposer des bornes min/max (jamais de `sparse` là), et `cards/forge3d_scene`
    ne fait que recopier la clé `byteStride` d'une vue — ni l'un ni l'autre ne lit une pièce de l'Établi."""
    services = pathlib.Path(__file__).resolve().parent.parent / "app" / "services"
    porteurs = sorted(p.name for p in services.glob("*.py") if "byteStride" in p.read_text("utf-8"))
    assert porteurs == ["mesh_edit.py"], porteurs


# ── T091 / plan T16 : l'aperçu de tranchage INDICATIF ──────────────────────────
def test_trancher_un_cube_donne_des_sections_carrees_et_un_perimetre_juste():
    from app.services import mesh_slice
    r = mesh_slice.trancher(_cube(), None, "y", nombre=4)
    assert len(r["couches"]) == 4
    assert r["axe"] == "y" and abs(r["hauteur"] - 2.0) < 1e-9 and abs(r["z_min"] + 1.0) < 1e-9
    for c in r["couches"]:
        # le cube du dépôt a une arête de 2 : chaque section est un carré 2x2
        assert abs(c["perimetre"] - 8.0) < 1e-6, c
        assert len(c["segments"]) >= 4
        for (a, b) in c["segments"]:
            assert abs(a[1] - c["z"]) < 1e-9 and abs(b[1] - c["z"]) < 1e-9
    # les couches montent, au MILIEU de chaque tranche, et aucune ne touche les faces extrêmes
    zs = [c["z"] for c in r["couches"]]
    assert zs == [-0.75, -0.25, 0.25, 0.75]


def test_trancher_suit_l_AXE_demande_et_la_matrice_MONDE_du_noeud():
    """Le cube posé par un nœud translaté de +10 en x : sur l'axe x, les couches vivent entre 9 et 11."""
    from app.services import mesh_edit, mesh_slice
    doc, binc = mesh_edit.lire_glb(_cube())
    for nd in doc["nodes"]:
        if "mesh" in nd:
            nd["translation"] = [10.0, 0.0, 0.0]
    r = mesh_slice.trancher(mesh_edit.ecrire_glb(doc, binc), None, "x", nombre=2)
    assert abs(r["z_min"] - 9.0) < 1e-9 and [c["z"] for c in r["couches"]] == [9.5, 10.5]
    assert all(abs(c["perimetre"] - 8.0) < 1e-6 for c in r["couches"])


def test_trancher_refuse_ce_qu_il_ne_sait_pas_lire_et_borne_son_travail():
    from app.services import mesh_edit, mesh_slice
    with pytest.raises(ValueError, match="axe"):
        mesh_slice.trancher(_cube(), None, "w", nombre=4)
    for n in (0, -3, 501, 2.5, True):
        with pytest.raises(ValueError, match="couches"):
            mesh_slice.trancher(_cube(), None, "y", nombre=n)
    doc, binc = mesh_edit.lire_glb(_cube())
    doc["extensionsRequired"] = ["KHR_draco_mesh_compression"]
    with pytest.raises(ValueError, match="draco"):
        mesh_slice.trancher(mesh_edit.ecrire_glb(doc, binc), None, "y", nombre=4)
    with pytest.raises(ValueError, match="aucun triangle"):
        mesh_slice.trancher(_cube(), [999], "y", nombre=4)


def test_la_route_tranches_ne_touche_pas_au_disque_et_juge_son_corps():
    d = _job("job_tr", _cube())
    with _client() as c:
        r = c.post("/api/etabli/tranches", json={"job": "job_tr", "version": 1, "axe": "y", "nombre": 6})
        assert r.status_code == 200, r.text
        assert len(r.json()["couches"]) == 6
        assert sorted(p.name for p in d.iterdir()) == ["model.glb"], "AUCUNE version, aucune fiche écrite"
        for corps in ({"axe": "w", "nombre": 6}, {"axe": "y", "nombre": 0}, {"axe": "y", "nombre": 5000},
                      {"axe": "y", "nombre": "6"}, {"axe": "y", "nombre": True}, {"axe": "y", "noeuds": [-1]},
                      {"axe": "y", "noeuds": "0"}):
            assert c.post("/api/etabli/tranches",
                          json={"job": "job_tr", "version": 1, **corps}).status_code == 400, corps
        assert c.post("/api/etabli/tranches", json={"job": "job_tr", "version": 7}).status_code == 404

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
