# -*- coding: utf-8 -*-
"""t343 (lot Scenario B8, 29/10/2026) — vidéo → mouvement sur le rig, retimage, hitboxes sur les os à l'export Godot.

Un BVH « Mixamo » (pose en T, centimètres, Y en haut) est reciblé sur un personnage riggé « Unreal » en pose en A
(os en Z en haut, armature -90° X × 0,01) : la DIRECTION de chaque os relié suit celle de la source à chaque image
(alignement des poses de repos), le bassin avance à l'échelle des hauteurs de bassin. Retimage (rognage, vitesse,
boucle, sur place), écriture du clip nommé dans le GLB (relu), chaîne GLB → GLB (la sortie d'Uthana), scène Godot
(.tscn : BoneAttachment3D + Area3D + CollisionShape3D, capsule le long de l'os) et ZIP. Routes : import, application
(une version de plus), export Godot ; voie vidéo Uthana SIMULÉE (clé 503 → bornes 400 → 409 sans confirme_cout →
plafond → tâche de fond → mouvement rangé). ffmpeg réel pour le petit clip. Aucune dépense.
Run : python tests/test_mouvement_rig.py (depuis backend/)"""
import asyncio, io, json, math, os, pathlib, shutil, subprocess, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzmouvement_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = ""; os.environ["UTHANA_API_KEY"] = ""; os.environ["ELEVENLABS_API_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from loguru import logger                                         # noqa: E402
logger.remove()
from app.config import settings                                   # noqa: E402
from app.services import mesh_edit, mouvement_rig as MR, uthana as UT  # noqa: E402
import _squelette_synthetique as SS                               # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]


def _src():
    return MR.lire_bvh(SS.bvh_source())


def _cible(glb=None):
    doc, _ = mesh_edit.lire_glb(glb or SS.glb_cible())
    return MR.squelette_glb(doc)


PAIRES = (("upperarm_l", "lowerarm_l", "LeftArm", "LeftForeArm"), ("lowerarm_l", "hand_l", "LeftForeArm", "LeftHand"),
          ("thigh_r", "calf_r", "RightUpLeg", "RightLeg"), ("upperarm_r", "lowerarm_r", "RightArm", "RightForeArm"))


def _poses(src, cib, res, k):
    rots, trans = [None] * len(cib), [None] * len(cib)
    for i, s in res["rot"].items():
        rots[i] = s[k]
    for i, s in res["trans"].items():
        trans[i] = s[k]
    _R, P, _S = MR.monde(cib, rots, trans)
    t_src = res["rapport"]["retimage"]["debut"] + res["temps"][k] * res["rapport"]["retimage"]["vitesse"]
    rs, ts = MR._pose(src, t_src)
    _Rs, Ps, _ = MR.monde(src["os"], rs, ts)
    return P, Ps


def _ecarts(src, cib, res, k):
    P, Ps = _poses(src, cib, res, k)
    nt = {o["nom"]: i for i, o in enumerate(cib)}
    ns = {o["nom"]: i for i, o in enumerate(src["os"])}
    return [SS.angle(MR._sub(P[nt[b]], P[nt[a]]), MR._sub(Ps[ns[sb]], Ps[ns[sa]])) for a, b, sa, sb in PAIRES]


# ── lecture ──────────────────────────────────────────────────────────────

def test_bvh_lu():
    m = _src()
    r = MR.resume(m)
    assert r["os"] == 21 and r["images"] == SS.N_IMAGES and abs(r["fps"] - 30) < 0.01 and r["format"] == "bvh", r
    i = [o["nom"] for o in m["os"]].index("LeftArm")
    assert m["os"][i]["t"] == (10.0, 0.0, 0.0) and m["os"][i]["parent"] is not None
    # 90° autour de Z à la dernière image : le bras (+X) pointe vers le haut (+Y)
    v = MR.q_rot(m["rot"][i][-1], (1, 0, 0))
    assert abs(v[0]) < 1e-3 and abs(v[1] - 1) < 1e-3, v
    assert m["trans"][0][-1] == (100.0, 100.0, 0.0) and all(t is None for t in m["trans"][1:])


def test_bvh_et_formats_refuses():
    for texte in ("", "BONJOUR", SS.bvh_source().split("MOTION")[0], SS.bvh_source()[:-400]):
        try:
            MR.lire_bvh(texte)
        except ValueError:
            continue
        raise AssertionError(f"BVH accepté à tort : {texte[:30]!r}")
    for nom in ("x.fbx", "x.obj"):
        try:
            MR.lire_fichier(nom, b"rien")
        except ValueError as e:
            assert ("FBX" in str(e)) == nom.endswith(".fbx")
        else:
            raise AssertionError(nom)


def test_roles_des_noms():
    attendu = {"mixamorig:LeftForeArm": "avantbras_g", "upperarm_l": "bras_g", "Bip01 R Thigh": "cuisse_d",
               "Spine02": "colonne", "Hips": "bassin", "pelvis": "bassin", "LHand": "main_g", "UpperArm.R": "bras_d",
               "RightToeBase": "orteil_d", "neck_01": "cou", "head": "tete", "clavicle_l": "epaule_g",
               "calf_r": "jambe_d", "LeftUpLeg": "cuisse_g", "LeftIndex1": None, "Armature": None}
    obtenu = {n: MR.role(n) for n in attendu}
    assert obtenu == attendu, {n: (obtenu[n], attendu[n]) for n in attendu if obtenu[n] != attendu[n]}


def test_correspondance_mixamo_vers_unreal():
    src, cib = _src(), _cible()
    m = MR.correspondance(src["os"], cib)
    noms = {cib[i]["nom"]: src["os"][j]["nom"] for i, j in m.items()}
    assert len(m) == len(cib) == 22, sorted(set(o["nom"] for o in cib) - set(noms))
    assert noms["spine_01"] == "Spine" and noms["spine_03"] == "Spine1" and noms["upperarm_l"] == "LeftArm"
    assert noms["thigh_r"] == "RightUpLeg" and noms["ball_l"] == "LeftToeBase" and noms["pelvis"] == "Hips"


def _chaine(*noms_parents):
    return [{"nom": n, "parent": p} for n, p in noms_parents]


def test_correspondance_leg_shin_de_meshy():
    """Mesuré le 31/10 sur un vrai BVH de Meshy Text to Motion : la cuisse s'y nomme « LeftLeg » et le tibia
    « LeftShin », quand le rig Meshy (convention Mixamo) dit « LeftUpLeg » / « LeftLeg ». Deux « jambes » enchaînées
    sans « cuisse » : la plus haute EST la cuisse — sinon le tibia recevait la rotation de la cuisse, figée."""
    meshy_bvh = _chaine(("Hips", None), ("LeftLeg", 0), ("LeftShin", 1), ("LeftFoot", 2),
                        ("RightLeg", 0), ("RightShin", 4), ("RightFoot", 5))
    mixamo = _chaine(("Hips", None), ("LeftUpLeg", 0), ("LeftLeg", 1), ("LeftFoot", 2),
                     ("RightUpLeg", 0), ("RightLeg", 4), ("RightFoot", 5))
    for src, cib, attendu in (
            (meshy_bvh, mixamo, {"LeftUpLeg": "LeftLeg", "LeftLeg": "LeftShin", "RightUpLeg": "RightLeg",
                                 "RightLeg": "RightShin", "LeftFoot": "LeftFoot", "RightFoot": "RightFoot",
                                 "Hips": "Hips"}),
            (mixamo, meshy_bvh, {"LeftLeg": "LeftUpLeg", "LeftShin": "LeftLeg", "RightLeg": "RightUpLeg",
                                 "RightShin": "RightLeg", "LeftFoot": "LeftFoot", "RightFoot": "RightFoot",
                                 "Hips": "Hips"})):
        m = MR.correspondance(src, cib)
        noms = {cib[i]["nom"]: src[j]["nom"] for i, j in m.items()}
        assert noms == attendu, noms
    # une seule « jambe » de chaque côté reste une jambe (pas de cuisse inventée)
    court = _chaine(("Hips", None), ("LeftLeg", 0), ("LeftFoot", 1))
    assert {court[i]["nom"]: mixamo[j]["nom"] for i, j in MR.correspondance(mixamo, court).items()} == \
        {"Hips": "Hips", "LeftLeg": "LeftLeg", "LeftFoot": "LeftFoot"}


# ── reciblage ────────────────────────────────────────────────────────────

def test_reciblage_suit_les_directions_de_la_source():
    src, cib = _src(), _cible()
    res = MR.recibler(src, cib)
    assert res["rapport"]["relies"] == 22 and res["rapport"]["porteur"] == "pelvis" and not res["rapport"]["non_relies"]
    for k in (0, 10, 20, 30):
        e = _ecarts(src, cib, res, k)
        assert max(e) < 0.5, (k, e)
    # TÉMOIN : sans alignement des poses de repos, la pose en A reste 45° sous la pose en T de la source
    res2 = MR.recibler(src, cib, aligner=False)
    e = _ecarts(src, cib, res2, 0)
    assert 44 < e[0] < 46 and 44 < e[3] < 46, e


def test_deplacement_du_bassin_et_sur_place():
    src, cib = _src(), _cible()
    i = [o["nom"] for o in cib].index("pelvis")
    res = MR.recibler(src, cib)
    P0, _ = _poses(src, cib, res, 0)
    P1, _ = _poses(src, cib, res, len(res["temps"]) - 1)
    # 100 cm de source × (0,96 m de bassin cible / 100 cm de bassin source) = 0,96 m, hauteur gardée
    assert abs(P1[i][0] - P0[i][0] - 0.96) < 1e-3 and abs(P1[i][1] - 0.95) < 1e-3, (P0[i], P1[i])
    res = MR.recibler(src, cib, retimage={"en_place": True})
    P1, _ = _poses(src, cib, res, len(res["temps"]) - 1)
    assert abs(P1[i][0]) < 1e-6 and abs(P1[i][1] - 0.95) < 1e-3, P1[i]


def test_retimage():
    src, cib = _src(), _cible()
    assert len(MR.recibler(src, cib)["temps"]) == 31
    r = MR.recibler(src, cib, retimage={"vitesse": 2})
    assert len(r["temps"]) == 16 and abs(r["rapport"]["secondes"] - 0.5) < 1e-6
    r = MR.recibler(src, cib, retimage={"debut": 0.5, "fin": 1.0})
    assert len(r["temps"]) == 16
    P, _ = _poses(src, cib, r, 0)
    nt = {o["nom"]: k for k, o in enumerate(cib)}
    d = MR._sub(P[nt["lowerarm_l"]], P[nt["upperarm_l"]])
    # à 0,5 s : bras levé de 45° (Z), colonne tournée de 10° (Y)
    attendu = MR.q_rot(MR.q_axe("Y", 10), (math.cos(math.radians(45)), math.sin(math.radians(45)), 0))
    assert SS.angle(d, attendu) < 0.5, SS.angle(d, attendu)
    r = MR.recibler(src, cib, retimage={"boucle": True, "fondu": 0.2, "en_place": True})
    for i, s in r["rot"].items():
        assert max(abs(a - b) for a, b in zip(s[-1], s[0])) < 1e-9 or max(abs(a + b) for a, b in zip(s[-1], s[0])) < 1e-9
    p = list(r["trans"].values())[0]
    assert max(abs(a - b) for a, b in zip(p[-1], p[0])) < 1e-9
    r = MR.recibler(src, cib, retimage={"fps": 15})
    assert len(r["temps"]) == 16 and r["fps"] == 15
    for mauvais in ({"vitesse": 10}, {"vitesse": 0}, {"debut": 0.8, "fin": 0.4}, {"debut": 3}, {"fin": "x"},
                    {"fondu": 5}, {"fps": 200}, {"vitesse": True}):
        try:
            MR.recibler(src, cib, retimage=mauvais)
        except ValueError:
            continue
        raise AssertionError(f"retimage accepté : {mauvais}")


# ── écriture du clip ─────────────────────────────────────────────────────

def test_clip_ecrit_relu_et_remplace():
    g = SS.glb_cible()
    sortie, rap = MR.appliquer(g, _src(), nom="Lever le bras", retimage={"vitesse": 0.5})
    assert rap["clip"] == "Lever le bras" and rap["images"] == 61
    inv = mesh_edit.rig_inventory(sortie)
    assert [c["nom"] for c in inv["clips"]] == ["Lever le bras"] and inv["clips"][0]["canaux"] == 23
    d0, b0 = mesh_edit.lire_glb(g)
    d1, b1 = mesh_edit.lire_glb(sortie)
    assert b1[:len(b0)] == b0 and d1["meshes"] == d0["meshes"] and d1["skins"] == d0["skins"]
    acc = d1["accessors"][d1["animations"][0]["samplers"][0]["input"]]
    assert acc["min"] == [0.0] and abs(acc["max"][0] - 2.0) < 1e-5
    # relu par le lecteur GLB : mêmes rotations que le reciblage (à la précision du float32)
    cib = _cible(g)
    res = MR.recibler(_src(), cib, retimage={"vitesse": 0.5})
    relu = MR.lire_glb_mouvement(sortie, "Lever le bras", fps=30)
    i = [o["nom"] for o in cib].index("upperarm_l")
    assert relu["n"] == 61 and max(abs(a - b) for a, b in zip(relu["rot"][i][40], res["rot"][i][40])) < 1e-5
    # même nom : remplacé ; autre nom : ajouté
    s2, _ = MR.appliquer(sortie, _src(), nom="Lever le bras")
    s3, _ = MR.appliquer(s2, _src(), nom="Saut")
    assert [c["nom"] for c in mesh_edit.rig_inventory(s3)["clips"]] == ["Lever le bras", "Saut"]
    for mauvais in ("", "   ", "///"):
        try:
            MR.appliquer(g, _src(), nom=mauvais)
        except ValueError:
            continue
        raise AssertionError(mauvais)


def test_sans_squelette_refuse():
    doc, binc = mesh_edit.lire_glb(SS.glb_cible())
    doc.pop("skins")
    doc["nodes"][-1].pop("skin")
    try:
        MR.appliquer(mesh_edit.ecrire_glb(doc, binc), _src(), nom="x")
    except ValueError as e:
        assert "squelette" in str(e)
    else:
        raise AssertionError("modèle sans squelette accepté")


def test_chaine_glb_vers_glb():
    """La sortie d'Uthana est un GLB animé (noms mixamorig:) : relu puis reciblé, il suit toujours le BVH d'origine."""
    uth, _ = MR.appliquer(SS.glb_cible(prefixe="mixamorig:"), _src(), nom="motion")
    src2 = MR.lire_glb_mouvement(uth)
    assert src2["clip"] == "motion" and src2["n"] == 31 and src2["os"][0]["base"] is not None
    cib = _cible()
    res = MR.recibler(src2, cib)
    src = _src()
    for k in (0, 15, 30):
        P, _ = _poses(src2, cib, res, k)
        _, Ps = _poses(src, cib, res, k)
        nt = {o["nom"]: i for i, o in enumerate(cib)}
        ns = {o["nom"]: i for i, o in enumerate(src["os"])}
        for a, b, sa, sb in PAIRES:
            e = SS.angle(MR._sub(P[nt[b]], P[nt[a]]), MR._sub(Ps[ns[sb]], Ps[ns[sa]]))
            assert e < 0.5, (k, a, e)


# ── Godot : hitboxes sur les os ──────────────────────────────────────────

def test_scene_godot_hitboxes():
    g = SS.glb_cible(prefixe="mixamorig:")
    choix = [{"os": "mixamorig:upperarm_l", "forme": "capsule", "rayon": 0.25, "role": "hurt"},
             {"os": "mixamorig:hand_r", "forme": "boite", "rayon": 0.5, "role": "hit"},
             {"os": "mixamorig:upperarm_l"}]                          # doublon : ignoré
    tscn, rap = MR.scene_godot(g, choix, res_glb="res://m.glb", res_script="res://h.gd", nom="Héros")
    assert tscn.startswith("[gd_scene load_steps=5 format=3]"), tscn[:60]
    assert tscn.count('type="BoneAttachment3D"') == 2 and tscn.count('type="Area3D"') == 2
    assert tscn.count('type="CollisionShape3D"') == 2 and 'bone_name = "mixamorig_upperarm_l"' in tscn
    assert '[sub_resource type="CapsuleShape3D" id="Forme_1"]\nradius = 7\nheight = 42' in tscn, tscn
    assert "collision_layer = 1" in tscn and "collision_layer = 2" in tscn and 'metadata/role = "hit"' in tscn
    # la capsule suit l'os : axe Y = (1, 0, 0) (vers lowerarm_l), centre à mi-longueur (14, 0, 0)
    ligne = next(l for l in tscn.splitlines() if l.startswith("transform ="))
    v = [float(x) for x in ligne.split("(")[1].rstrip(")").split(",")]
    lignes_b = [v[0:3], v[3:6], v[6:9]]
    col = lambda j: [lignes_b[i][j] for i in range(3)]                  # Transform3D : la base en LIGNES
    assert col(1) == [1, 0, 0] and v[9:] == [14, 0, 0], ligne
    x, y, z = col(0), col(1), col(2)
    assert abs(sum(a * b for a, b in zip(x, y))) < 1e-9 and abs(sum(a * b for a, b in zip(y, z))) < 1e-9
    assert [x[1] * y[2] - x[2] * y[1], x[2] * y[0] - x[0] * y[2], x[0] * y[1] - x[1] * y[0]] == z   # directe
    # un bout de chaîne (hand_r, sans enfant) : la moitié de la longueur de l'os, boîte de 2r de côté
    assert 'size = Vector3(12, 12, 12)' in tscn, tscn
    assert '[node name="H_ros" type="Node3D"]' in tscn and 'instance=ExtResource("1_modele")' in tscn
    assert [h["os_godot"] for h in rap["hitboxes"]] == ["mixamorig_upperarm_l", "mixamorig_hand_r"]
    for mauvais in ([], [{"os": "inconnu"}], [{"os": "mixamorig:head", "rayon": 3}],
                    [{"os": "mixamorig:head", "forme": "sphere"}], [{"os": "mixamorig:head", "role": "x"}], "head"):
        try:
            MR.scene_godot(g, mauvais, res_glb="a", res_script="b")
        except ValueError:
            continue
        raise AssertionError(mauvais)


def test_archive_godot():
    g, _ = MR.appliquer(SS.glb_cible(), _src(), nom="geste")
    octets, rap = MR.archive_godot(g, [{"os": "head"}, {"os": "hand_l", "role": "hit"}], dossier="job x/1", nom="Perso")
    z = zipfile.ZipFile(io.BytesIO(octets))
    noms = sorted(z.namelist())
    assert noms == ["deepotus/job_x_1/LISEZMOI.json", "deepotus/job_x_1/Perso.tscn", "deepotus/job_x_1/hitboxes_os.gd",
                    "deepotus/job_x_1/modele.glb"], noms
    assert z.read("deepotus/job_x_1/modele.glb") == g and rap["clips"] == ["geste"]
    tscn = z.read("deepotus/job_x_1/Perso.tscn").decode()
    assert 'path="res://deepotus/job_x_1/modele.glb"' in tscn and 'path="res://deepotus/job_x_1/hitboxes_os.gd"' in tscn
    gd = z.read("deepotus/job_x_1/hitboxes_os.gd").decode()
    assert "set_external_skeleton" in gd and "Skeleton3D" in gd and gd.startswith("extends Node3D")
    assert json.loads(z.read("deepotus/job_x_1/LISEZMOI.json"))["clips"] == ["geste"]


# ── routes ───────────────────────────────────────────────────────────────

def _job(nom: str, data: bytes) -> pathlib.Path:
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(data)
    return d


def test_routes_import_appliquer_godot():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    _job("perso", SS.glb_cible())

    async def main():
        o = {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/api/etabli/mouvement", params={"job": "perso", "version": 1})
            o["etat"] = (r.status_code, r.json())
            r = await c.post("/api/etabli/mouvement/importer", data={"job": "perso"},
                             files={"fichier": ("prise 1.bvh", SS.bvh_source().encode(), "text/plain")})
            o["import"] = (r.status_code, r.json())
            o["fbx"] = (await c.post("/api/etabli/mouvement/importer", data={"job": "perso"},
                                     files={"fichier": ("a.fbx", b"Kaydara", "application/octet-stream")})).status_code
            o["casse"] = (await c.post("/api/etabli/mouvement/importer", data={"job": "perso"},
                                       files={"fichier": ("a.bvh", b"HIERARCHY ROOT", "text/plain")})).status_code
            o["job_absent"] = (await c.post("/api/etabli/mouvement/importer", data={"job": "../x"},
                                            files={"fichier": ("a.bvh", b"x", "text/plain")})).status_code
            src = o["import"][1].get("source")
            corps = {"job": "perso", "version": 1, "source": src, "nom": "geste",
                     "retimage": {"vitesse": 1.5, "boucle": True}}
            r = await c.post("/api/etabli/mouvement/appliquer", json=corps)
            o["appliquer"] = (r.status_code, r.json())
            o["mauvais_retimage"] = (await c.post("/api/etabli/mouvement/appliquer",
                                                  json={**corps, "retimage": {"vitesse": 9}})).status_code
            o["source_absente"] = (await c.post("/api/etabli/mouvement/appliquer",
                                                json={**corps, "source": {"type": "fichier", "nom": "rien.bvh"}})).status_code
            o["source_chemin"] = (await c.post("/api/etabli/mouvement/appliquer",
                                               json={**corps, "source": {"type": "fichier", "nom": "../model.glb"}})).status_code
            r = await c.get("/api/etabli/mouvement", params={"job": "perso", "version": 2})
            o["etat2"] = (r.status_code, r.json())
            # retimer le clip de la version elle-même (même squelette)
            r = await c.post("/api/etabli/mouvement/appliquer", json={
                "job": "perso", "version": 2, "source": {"type": "clip", "nom": "geste"}, "nom": "geste lent",
                "retimage": {"vitesse": 0.5}})
            o["retimer"] = (r.status_code, r.json())
            r = await c.post("/api/etabli/mouvement/godot", json={
                "job": "perso", "version": 3, "nom": "Perso",
                "hitboxes": [{"os": "head"}, {"os": "hand_l", "role": "hit", "forme": "boite"}]})
            o["godot"] = (r.status_code, r.headers.get("content-type"), r.headers.get("x-dz-hitboxes"), r.content)
            o["godot_vide"] = (await c.post("/api/etabli/mouvement/godot",
                                            json={"job": "perso", "version": 3, "hitboxes": []})).status_code
            o["reseau"] = None
        async with AsyncClient(transport=ASGITransport(app=app, client=("192.168.1.20", 5000)), base_url="http://t") as c:
            o["reseau"] = (await c.get("/api/etabli/mouvement", params={"job": "perso"})).status_code
        return o
    o = asyncio.run(main())
    st, e = o["etat"]
    assert st == 200 and e["a_squelette"] and len(e["os"]) == 22 and e["sources"] == [] and e["clips"] == [], e
    assert e["video"]["cle"] is False and e["video"]["usd_seconde"] == 0.05
    st, j = o["import"]
    assert st == 200 and j["source"] == {"type": "fichier", "nom": "prise_1.bvh"} and j["fiche"]["images"] == 31, j
    assert o["fbx"] == 400 and o["casse"] == 400 and o["job_absent"] == 400
    st, j = o["appliquer"]
    assert st == 200 and j["version"] == 2, j
    assert o["mauvais_retimage"] == 400 and o["source_absente"] == 404 and o["source_chemin"] == 400
    st, e2 = o["etat2"]
    assert [c["nom"] for c in e2["clips"]] == ["geste"] and e2["sources"][0]["nom"] == "prise_1.bvh", e2
    st, j = o["retimer"]
    assert st == 200 and j["version"] == 3, j
    clips = mesh_edit.rig_inventory((settings.outputs_path / "assets3d" / "perso" / "model.v3.glb").read_bytes())["clips"]
    assert [c["nom"] for c in clips] == ["geste", "geste lent"]
    st, ct, n, corps = o["godot"]
    assert st == 200 and ct == "application/zip" and n == "2", (st, corps[:200])
    assert "deepotus/perso_v3/Personnage.tscn" not in zipfile.ZipFile(io.BytesIO(corps)).namelist()
    assert "deepotus/perso_v3/Perso.tscn" in zipfile.ZipFile(io.BytesIO(corps)).namelist()
    assert o["godot_vide"] == 400 and o["reseau"] in (401, 403), (o["godot_vide"], o["reseau"])


def _clip_video(dest: pathlib.Path, secondes=3, w=640, h=360, fps=30):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size={w}x{h}:rate={fps}",
                    "-t", str(secondes), "-pix_fmt", "yuv420p", str(dest)], check=True)


def test_route_video_uthana_simulee():
    if not shutil.which("ffmpeg"):
        print("    (ffmpeg absent : banc vidéo sauté)")
        return
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    _job("acteur", SS.glb_cible())
    up = settings.outputs_path / "uploads"
    up.mkdir(parents=True, exist_ok=True)
    _clip_video(up / "danse.mp4", 3)
    uth, _ = MR.appliquer(SS.glb_cible(prefixe="mixamorig:"), _src(), nom="motion")
    appels = []

    async def poster(video, nom):
        appels.append(("poster", pathlib.Path(video).suffix, nom, pathlib.Path(video).is_file()))
        return {"data": {"create_video_to_motion": {"job": {"id": "j-1", "status": "RESERVED"}}}}

    async def requete(jid):
        appels.append(("job", jid))
        return {"data": {"job": {"id": jid, "status": "FINISHED", "result": {"result": {"id": "m-9"}}}}}

    async def telecharger(url):
        appels.append(("dl", url))
        return uth
    vieux = (UT._poster, UT._requete, UT._telecharger)
    UT._poster, UT._requete, UT._telecharger = poster, requete, telecharger

    async def main():
        o = {}
        corps = {"job": "acteur", "video_filename": "danse.mp4", "nom": "danse"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            o["sans_cle"] = (await c.post("/api/etabli/mouvement/video", json={**corps, "confirme_cout": True})).status_code
            settings.UTHANA_API_KEY = "cle-de-banc"
            o["devis"] = (await c.get("/api/etabli/mouvement/video/devis",
                                      params={"job": "acteur", "video_filename": "danse.mp4"})).json()
            o["court"] = (await c.post("/api/etabli/mouvement/video", json={**corps, "fin": 1.0,
                                                                         "confirme_cout": True})).status_code
            o["chemin"] = (await c.post("/api/etabli/mouvement/video",
                                        json={**corps, "video_filename": "../x.mp4"})).status_code
            r = await c.post("/api/etabli/mouvement/video", json=corps)
            o["sans_confirme"] = (r.status_code, r.json())
            o["appels_avant"] = len(appels)
            r = await c.post("/api/etabli/mouvement/video", json={**corps, "confirme_cout": True},
                             headers={"X-DZ-Plafond": "confirme"})
            o["ok"] = (r.status_code, r.json())
            tache = r.json().get("tache")
            for _ in range(200):
                e = (await c.get("/api/etabli/mouvement/video/etat", params={"job": "acteur", "tache": tache})).json()
                if e.get("etat") in ("fini", "echec"):
                    break
                await asyncio.sleep(0.05)
            o["etat"] = e
            o["etat_inconnu"] = (await c.get("/api/etabli/mouvement/video/etat",
                                             params={"job": "acteur", "tache": "0" * 12})).status_code
            o["sources"] = (await c.get("/api/etabli/mouvement", params={"job": "acteur"})).json()["sources"]
            r = await c.post("/api/etabli/mouvement/appliquer", json={
                "job": "acteur", "version": 1, "source": e.get("source"), "nom": "danse"})
            o["appliquer"] = (r.status_code, r.json())
        return o
    try:
        o = asyncio.run(main())
    finally:
        UT._poster, UT._requete, UT._telecharger = vieux
        settings.UTHANA_API_KEY = ""
    assert o["sans_cle"] == 503
    d = o["devis"]
    assert d["devis"]["usd"] == 0.15 and d["devis"]["secondes"] == 3 and d["refus"] is None and d["cle"], d
    assert o["court"] == 400 and o["chemin"] == 400
    st, j = o["sans_confirme"]
    assert st == 409 and j["detail"]["devis"]["usd"] == 0.15 and o["appels_avant"] == 0, j
    st, j = o["ok"]
    assert st == 200 and j["devis"]["usd"] == 0.15, j
    e = o["etat"]
    assert e["etat"] == "fini" and e["source"]["nom"] == "danse.glb", e
    assert appels[0] == ("poster", ".mp4", "danse", True) and ("dl", UT.URL_CLIP.format(perso=UT.PERSONNAGE, mvt="m-9")) in appels
    assert o["etat_inconnu"] == 404
    s = o["sources"][0]
    assert s["origine"] == "uthana" and s["nom"] == "danse.glb" and s["format"] == "glb", s
    fiche = json.loads((settings.outputs_path / "assets3d" / "acteur" / "mouvements" / "danse.glb.json").read_text("utf-8"))
    assert fiche["devis_usd"] == 0.15 and fiche["uthana_mouvement"] == "m-9" and fiche["rognage"] == [0.0, 3.0]
    assert not list((settings.outputs_path / "assets3d" / "acteur" / "mouvements" / "_videos").glob("*.mp4"))
    st, j = o["appliquer"]
    assert st == 200 and j["version"] == 2, j


def test_devis_et_bornes_uthana():
    from app.services import pricing
    assert pricing.estimate({"kind": "video_mouvement", "secondes": 7.2})["total_usd"] == 0.4
    assert UT.devis(7.2) == {"fournisseur": "uthana", "modele": "video-to-motion-2.0", "secondes": 8,
                             "usd_seconde": 0.05, "usd": 0.4}
    infos = {"secondes": 90.0, "fps": 30, "largeur": 1080, "hauteur": 1920}
    assert UT.verifier(infos, 10, 40) == {"debut": 10.0, "fin": 40.0, "secondes": 30.0}
    for args in ((0, None), (0, 1.5), (50, 40), (0, 95)):
        try:
            UT.verifier(infos, *args)
        except ValueError:
            continue
        raise AssertionError(args)
    for mauvais in ({**infos, "fps": 12}, {**infos, "largeur": 200}, {**infos, "secondes": None}):
        try:
            UT.verifier(mauvais, 0, 30)
        except ValueError:
            continue
        raise AssertionError(mauvais)


def test_cle_uthana_posee_depuis_le_panneau():
    """Comme les clés de recherche de t354 : secret du coffre, posée par la route du panneau (pas par Réglages)."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services import coffre as CF, guides_fournisseurs as G
    assert "UTHANA_API_KEY" in CF.SECRETES
    g = G.GUIDES["UTHANA_API_KEY"]
    assert g["console"].startswith("https://uthana.com") and g["verifie_le"] == "2026-10-29" and "0,05 $" in g["fr"]

    async def main():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            a = (await c.post("/api/etabli/mouvement/cle", json={"valeur": "a b"})).status_code
            r = await c.post("/api/etabli/mouvement/cle", json={"valeur": "uth-cle-de-banc"})
            return a, r.status_code, r.json()
    try:
        a, st, j = asyncio.run(main())
        assert a == 400 and st == 200 and j["cle"] is True and "uth-cle" not in json.dumps(j), j
        assert UT.cle() == "uth-cle-de-banc"
    finally:
        settings.UTHANA_API_KEY = ""


def test_outil_agent_mouvement_lire():
    from app.services import agent_boites as B, agent_outils as ao
    assert "mouvement_lire" in B.BOITES["assets3d"]["outils"] and ao.OUTILS["mouvement_lire"]["nature"] == "lecture"
    assert B.verifier() == [], B.verifier()
    d = _job("agent_perso", SS.glb_cible())
    avant = sorted(x.name for x in d.iterdir())
    vieux = list(B.BOITES["assets3d"]["agents"])
    B.BOITES["assets3d"]["agents"] = ["essai"]
    try:
        ctx = ao.Ctx(cid="c1", agent="essai")
        r = asyncio.run(ao.executer("mouvement_lire", {"job": "agent_perso"}, ctx))
        assert r["ok"] and r["donnees"]["a_squelette"] and r["donnees"]["os"] == 22, r
        assert r["donnees"]["video"]["usd_seconde"] == 0.05 and r["donnees"]["clips"] == []
        for mauvais in ({"job": "../x"}, {"job": "agent_perso", "version": 0}, {"job": "inconnu"}):
            assert asyncio.run(ao.executer("mouvement_lire", mauvais, ctx))["ok"] is False, mauvais
    finally:
        B.BOITES["assets3d"]["agents"] = vieux
    assert sorted(x.name for x in d.iterdir()) == avant   # rien d'écrit


def test_ecran_mouvement():
    """Le module de l'Établi : à part d'etabli.js (généré par L8), clés FR/EN complètes, coût sur le bouton payant,
    confirmation AVANT l'envoi, aucun texte en dur."""
    import re
    js = (RACINE / "frontend" / "etabli" / "mouvement.js").read_text(encoding="utf-8")
    html = (RACINE / "frontend" / "etabli" / "index.html").read_text(encoding="utf-8")
    dico = json.loads((RACINE / "frontend" / "shared" / "i18n" / "mouvement3d.json").read_text(encoding="utf-8"))
    assert '<script type="module" src="mouvement.js"></script>' in html and 'id="panMouvement"' in html
    assert '<link rel="stylesheet" href="mouvement.css">' in html
    cles = {k for k in re.findall(r'\bT\("([a-z0-9_.]+)"', js) if not k.endswith(".")}
    cles |= set(re.findall(r'"(video\.(?:fini|echec|interrompu|en_cours))"', js))
    cles |= {f"origine.{o}" for o in ("import", "video", "meshy", "clip")}
    cles |= {"video.origine.telephone", "video.origine.bibliotheque"}
    cles |= {f"godot.role.{r}" for r in MR.ROLES_HITBOX} | {f"godot.forme.{f}" for f in MR.FORMES}
    assert len(cles) > 60, len(cles)
    for k in cles:
        assert "mouvement3d." + k in dico, k
    for k, v in dico.items():
        assert v["fr"] and v["en"] and set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"])), k
    assert 'T("video.lancer", { p: usd(' in js
    i_conf, i_post = js.index("D_.confirmer("), js.index('fetch("/api/etabli/mouvement/video"')
    assert i_conf < i_post and "confirme_cout: true" in js
    # copie du dictionnaire assemblé identique (/shared et dist/shared)
    a = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_bytes()
    assert a == (RACINE / "frontend" / "dist" / "shared" / "dz-i18n-dico.js").read_bytes()
    assert b"mouvement3d.panneau.titre" in a


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (mouvement sur le rig)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
