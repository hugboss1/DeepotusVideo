# -*- coding: utf-8 -*-
"""t402 (31/10/2026) — Décor › Accessoire : poser un élément au sol (pivot en bas, centré) et à sa hauteur réelle,
écrit comme une version de plus ; rôles de décor → préréglage de triangles ; variantes (jobs neufs, graine
déterministe, teinte sur baseColorFactor) ; masque de vent `_WIND` ; cartes (imposteur) ; envoi au Plateau 3D.
Boîtes SYNTHÉTIQUES, aucune dépense.
Run : python tests/test_studio3d_decor.py (depuis backend/)"""
import asyncio, json, os, pathlib, struct, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzs3dec_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = ""
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loguru import logger                                         # noqa: E402
logger.remove()
from app.config import settings                                   # noqa: E402
from app.services import mesh_edit, print3d, studio3d_decor as SD, studio3d_ouvert as SO   # noqa: E402
from app.services.storage import init_db                         # noqa: E402
asyncio.run(init_db())

J = settings.outputs_path / "assets3d"


def boite(c, d):
    x0, y0, z0 = (c[i] - d[i] / 2 for i in range(3))
    x1, y1, z1 = (c[i] + d[i] / 2 for i in range(3))
    P = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    F = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6), (1, 2, 6), (1, 6, 5),
         (3, 0, 4), (3, 4, 7)]
    return print3d.glb_de_pieces([("m", [(P[a], P[b], P[e]) for a, b, e in F])])


ROCHER = boite((3.0, 5.0, -2.0), (2.0, 4.0, 1.0))          # flotte à y = 3..7, décentré
(J / "rocher").mkdir(parents=True, exist_ok=True)
(J / "rocher" / "model.glb").write_bytes(ROCHER)


def bornes(data):
    return print3d.bbox(print3d.lire_glb_triangles(data))


def test_poser_met_le_bas_au_sol_et_centre_sans_toucher_l_echelle():
    sortie, m = SD.poser(ROCHER)
    (x0, x1), (y0, y1), (z0, z1) = bornes(sortie)
    assert abs(y0) < 1e-6 and abs(y1 - 4.0) < 1e-6
    assert abs(x0 + x1) < 1e-6 and abs(z0 + z1) < 1e-6
    assert m["echelle"] == 1.0 and m["avant"]["bas"] == 3.0 and m["apres"]["bas"] == 0.0


def test_la_hauteur_reelle_met_a_l_echelle_uniformement():
    sortie, m = SD.poser(ROCHER, hauteur_m=1.0)
    (x0, x1), (y0, y1), (z0, z1) = bornes(sortie)
    assert abs(y1 - y0 - 1.0) < 1e-6 and abs(y0) < 1e-6
    assert abs((x1 - x0) - 0.5) < 1e-6 and abs((z1 - z0) - 0.25) < 1e-6      # proportions gardées
    assert m["echelle"] == 0.25


def test_les_refus():
    for h in (0, -1, 1000, True, "2"):
        try:
            SD.poser(ROCHER, hauteur_m=h)
        except ValueError:
            continue
        raise AssertionError(h)
    try:
        SD.budget("inconnu")
    except ValueError:
        pass
    else:
        raise AssertionError("rôle inconnu accepté")
    assert SD.budget("foule") == {"role": "foule", "preset": "micro", "triangles": 500}


def test_la_route_ecrit_une_version_qui_dit_sa_source():
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    async def go():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            ko = await c.post("/api/studio3d/decor/poser", json={"job": "../rocher"})
            absent = await c.post("/api/studio3d/decor/poser", json={"job": "inconnu"})
            mauvais = await c.post("/api/studio3d/decor/poser", json={"job": "rocher", "hauteur_m": 9999})
            ok = await c.post("/api/studio3d/decor/poser", json={"job": "rocher", "hauteur_m": 0.8})
            roles = await c.get("/api/studio3d/decor/roles")
            return ko, absent, mauvais, ok, roles
    ko, absent, mauvais, ok, roles = asyncio.run(go())
    assert (ko.status_code, absent.status_code, mauvais.status_code) == (400, 404, 400)
    assert ok.status_code == 200, ok.text
    assert ok.json()["version"] == 2
    f = SO.fiche("rocher")
    assert f["version"] == 2 and [(v["operation"], v["depuis"]) for v in f["versions"]][-1] == ("decor_poser", 1)
    (x0, x1), (y0, y1), _ = bornes((J / "rocher" / "model.v2.glb").read_bytes())
    assert abs(y1 - y0 - 0.8) < 1e-6 and abs(y0) < 1e-6
    assert [r["role"] for r in roles.json()["roles"]] == list(SD.ROLES)


# ── variantes ────────────────────────────────────────────────────────────────
def avec_materiau(data, couleur=(0.5, 0.4, 0.3, 1.0)):
    doc, binc = mesh_edit.lire_glb(data)
    doc["materials"] = [{"name": "pierre", "pbrMetallicRoughness": {"baseColorFactor": list(couleur)}}]
    for me in doc["meshes"]:
        for p in me["primitives"]:
            p["material"] = 0
    return mesh_edit.ecrire_glb(doc, binc)


PLANTE = avec_materiau(boite((0.0, 1.0, 0.0), (1.0, 2.0, 0.5)))    # posée : pied à y = 0, 2 m
(J / "plante").mkdir(parents=True, exist_ok=True)
(J / "plante" / "model.glb").write_bytes(PLANTE)
REGL = {"nombre": 3, "graine": 7, "echelle_pct": 20, "rotation": True, "teinte": 0.5, "luminosite": 0.2}


def test_le_tirage_est_deterministe_et_borne():
    r = SD.reglages_variantes(REGL)
    a = [SD.tirage(7, k, r) for k in (1, 2, 3)]
    assert a == [SD.tirage(7, k, r) for k in (1, 2, 3)]                   # même graine → mêmes variantes
    assert a != [SD.tirage(8, k, r) for k in (1, 2, 3)]
    assert len({x["teinte"] for x in a}) == 3                              # trois variantes distinctes
    for x in a:
        assert 0.8 <= x["echelle"] <= 1.2 and 0 <= x["rotation_y"] < 360
    sans = SD.reglages_variantes({**REGL, "rotation": False})
    assert [SD.tirage(7, k, sans)["echelle"] for k in (1, 2, 3)] == [x["echelle"] for x in a]
    assert all(SD.tirage(7, k, sans)["rotation_y"] == 0 for k in (1, 2, 3))
    for mauvais in ({"nombre": 1}, {"nombre": 9}, {"nombre": True}, {"graine": -1}, {"echelle_pct": 80},
                    {"teinte": "x"}, {"rotation": 1}):
        try:
            SD.reglages_variantes({**REGL, **mauvais})
        except ValueError:
            continue
        raise AssertionError(mauvais)


def test_une_variante_teinte_les_materiaux_met_a_l_echelle_et_garde_le_tampon():
    t = SD.tirage(7, 2, SD.reglages_variantes(REGL))
    sortie = SD.appliquer_variante(PLANTE, t)
    doc, binc = mesh_edit.lire_glb(sortie)
    _, binc0 = mesh_edit.lire_glb(PLANTE)
    assert binc == binc0                                                    # octet pour octet
    bc = doc["materials"][0]["pbrMetallicRoughness"]["baseColorFactor"]
    attendu = [round(c * m, 6) for c, m in zip((0.5, 0.4, 0.3), t["multiplicateur"])] + [1.0]
    assert bc == attendu and bc[:3] != [0.5, 0.4, 0.3]
    _, (y0, y1), _ = bornes(sortie)
    assert abs(y0) < 1e-6 and abs((y1 - y0) - 2.0 * t["echelle"]) < 1e-5    # pied au sol, hauteur × échelle
    # sans matériau : un matériau teinté est ajouté
    nu = SD.appliquer_variante(boite((0, 1, 0), (1, 2, 1)), t)
    d2, _ = mesh_edit.lire_glb(nu)
    assert d2["materials"][0]["pbrMetallicRoughness"]["baseColorFactor"][:3] == t["multiplicateur"]
    assert all(p["material"] == 0 for me in d2["meshes"] for p in me["primitives"])


def test_la_route_ecrit_des_jobs_neufs_et_resert_les_memes():
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    async def go():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            un = await c.post("/api/studio3d/decor/variantes", json={"job": "plante", **REGL})
            deux = await c.post("/api/studio3d/decor/variantes", json={"job": "plante", **REGL})
            autre = await c.post("/api/studio3d/decor/variantes", json={"job": "plante", **REGL, "graine": 8,
                                                                         "nombre": 2})
            ko = await c.post("/api/studio3d/decor/variantes", json={"job": "plante", **REGL, "nombre": 12})
            return un, deux, autre, ko
    un, deux, autre, ko = asyncio.run(go())
    assert un.status_code == 200, un.text
    v1 = un.json()["variantes"]
    assert [v["job"] for v in v1] == ["plante_var1", "plante_var2", "plante_var3"] and all(v["nouveau"] for v in v1)
    assert [(v["job"], v["nouveau"]) for v in deux.json()["variantes"]] == [(v["job"], False) for v in v1]
    assert [v["job"] for v in autre.json()["variantes"]] == ["plante_var4", "plante_var5"]
    assert ko.status_code == 400
    man = json.loads((J / "plante_var2" / "asset.json").read_text(encoding="utf-8"))
    assert man["variante"]["source_job"] == "plante" and man["variante"]["source_version"] == 1
    assert man["variante"]["graine"] == 7 and man["variante"]["index"] == 2
    assert man["stage"] == "variante" and "variante 2" in man["name"]
    assert (J / "plante_var2" / "model.glb").read_bytes() == SD.appliquer_variante(
        PLANTE, SD.tirage(7, 2, SD.reglages_variantes(REGL)))
    assert SO.fiche("plante_var2")["version"] == 1 and v1[1]["url"]


# ── masque de vent ───────────────────────────────────────────────────────────
def lire_vent(data):
    doc, binc = mesh_edit.lire_glb(data)
    out = []
    for me in doc["meshes"]:
        for p in me["primitives"]:
            pos = mesh_edit.lire_accesseur(doc, binc, p["attributes"]["POSITION"])
            w = mesh_edit.lire_accesseur(doc, binc, p["attributes"][SD.ATTRIBUT_VENT])
            out += [(q, x[0]) for q, x in zip(pos, w)]
    return doc, binc, out


def test_le_masque_de_vent_croit_avec_la_hauteur():
    sortie, rap = SD.masque_vent(PLANTE, courbe=1.0)
    doc, binc, pts = lire_vent(sortie)
    _, binc0 = mesh_edit.lire_glb(PLANTE)
    assert binc[:len(binc0)] == binc0                                       # ajouté en fin, rien de déplacé
    pts.sort(key=lambda e: e[0][1])
    vals = [w for _, w in pts]
    assert vals == sorted(vals) and vals[0] == 0.0 and vals[-1] == 1.0
    for (x, y, z), w in pts:
        assert abs(w - y / 2.0) < 1e-6                                      # linéaire : hauteur / 2 m
    assert rap["primitives"] == 1 and rap["pied"] == 0.0 and rap["sommet"] == 2.0
    acc = doc["accessors"][doc["meshes"][0]["primitives"][0]["attributes"][SD.ATTRIBUT_VENT]]
    assert acc["componentType"] == 5126 and acc["type"] == "SCALAR" and acc["min"] == [0.0] and acc["max"] == [1.0]
    # courbe et seuil
    assert SD.valeur_masque(0.5, 2.0) == 0.25 and SD.valeur_masque(0.2, 1.0, 0.25) == 0.0
    assert abs(SD.valeur_masque(0.625, 1.0, 0.25) - 0.5) < 1e-9
    for c, s in ((0.5, 0.0), (3.0, 0.4)):
        suite = [SD.valeur_masque(i / 50, c, s) for i in range(51)]
        assert all(a <= b for a, b in zip(suite, suite[1:])) and suite[-1] == 1.0
    for mauvais in ({"courbe": 0}, {"courbe": 9}, {"seuil": 1}, {"seuil": True}):
        try:
            SD.masque_vent(PLANTE, **mauvais)
        except ValueError:
            continue
        raise AssertionError(mauvais)


def test_le_masque_lit_la_hauteur_du_monde():
    # le maillage couché (sa hauteur locale est z) puis redressé par un nœud : le masque suit le MONDE
    couche = boite((0.0, 0.25, 1.0), (1.0, 0.5, 2.0))
    doc, binc = mesh_edit.lire_glb(couche)
    rot_x = [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]]           # z local → y monde
    mesh_edit._envelopper(doc, mesh_edit._matrice(rot_x, 1.0, [0.0, 0.0, 0.0]))
    sortie, _ = SD.masque_vent(mesh_edit.ecrire_glb(doc, binc))
    _, _, pts = lire_vent(sortie)
    for (x, y, z), w in pts:
        assert abs(w - (z / 2.0) ** 1.5) < 1e-6, ((x, y, z), w)


def test_la_route_du_vent_ecrit_une_version():
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    async def go():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            ok = await c.post("/api/studio3d/decor/vent", json={"job": "plante", "courbe": 2})
            ko = await c.post("/api/studio3d/decor/vent", json={"job": "plante", "seuil": 3})
            return ok, ko
    ok, ko = asyncio.run(go())
    assert ok.status_code == 200, ok.text
    assert ko.status_code == 400
    f = SO.fiche("plante")
    assert f["version"] == ok.json()["version"] == 2
    assert [(v["operation"], v["depuis"]) for v in f["versions"]][-1] == ("decor_vent", 1)
    _, _, pts = lire_vent((J / "plante" / "model.v2.glb").read_bytes())
    assert max(w for _, w in pts) == 1.0


# ── cartes (imposteur) ───────────────────────────────────────────────────────
def png(w, h):
    import zlib
    brut = b"".join(b"\x00" + bytes([0, 128, 0, 255]) * w for _ in range(h))

    def bloc(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + bloc(b"IDAT", zlib.compress(brut)) + bloc(b"IEND", b""))


def test_le_cadre_et_les_faces_des_cartes():
    c = SD.cadre_cartes(((-1.0, 3.0), (0.0, 2.0), (-0.5, 0.5)))           # même boîte que le banc node
    assert c["centre"] == [1.0, 1.0, 0.0] and abs(c["cote"] - 2 * (4.25 ** 0.5)) < 1e-12
    assert SD.cadre_cartes(((0, 1), (0, 10), (0, 1)))["cote"] == 10       # un arbre : la hauteur l'emporte
    assert [f["case"] for f in SD.faces_cartes(2)] == [0, 4, 2, 6]
    assert [f["case"] for f in SD.faces_cartes(3)] == [0, 4, 1, 5, 3, 7]
    for mauvais in (1, 4, True, "2"):
        try:
            SD.faces_cartes(mauvais)
        except ValueError:
            continue
        raise AssertionError(mauvais)


def test_l_imposteur_est_un_glb_valide():
    import base64
    atlas = png(256, 128)
    assert SD.lire_atlas("data:image/png;base64," + base64.b64encode(atlas).decode()) == atlas
    for mauvais in ("", "pas du base64 !", base64.b64encode(png(256, 256)).decode(),
                    base64.b64encode(b"GIF89a" + b"\x00" * 30).decode()):
        try:
            SD.lire_atlas(mauvais)
        except ValueError:
            continue
        raise AssertionError(mauvais[:20])
    b = ((-1.0, 3.0), (0.0, 2.0), (-0.5, 0.5))
    for plans in (2, 3):
        glb = SD.cartes(b, atlas, plans)
        doc, binc = mesh_edit.lire_glb(glb)
        tris = print3d.lire_glb_triangles(glb)
        assert len(tris) == 4 * plans                                       # deux faces × deux triangles par plan
        c = SD.cadre_cartes(b)
        (x0, x1), (y0, y1), (z0, z1) = print3d.bbox(tris)
        assert abs(y0 - (c["centre"][1] - c["cote"] / 2)) < 1e-6 and abs(y1 - y0 - c["cote"]) < 1e-6
        assert abs((x0 + x1) / 2 - 1.0) < 1e-6 and abs(x1 - x0 - c["cote"]) < 1e-6
        img = doc["images"][0]
        bv = doc["bufferViews"][img["bufferView"]]
        assert binc[bv["byteOffset"]:bv["byteOffset"] + bv["byteLength"]] == atlas and img["mimeType"] == "image/png"
        m = doc["materials"][0]
        assert m["alphaMode"] == "MASK" and "KHR_materials_unlit" in m["extensions"] and not m["doubleSided"]
        assert doc["extensionsUsed"] == ["KHR_materials_unlit"]
        pos = mesh_edit.lire_accesseur(doc, binc, 0)
        uv = mesh_edit.lire_accesseur(doc, binc, 2)
        assert doc["accessors"][0]["min"] == [min(p[i] for p in pos) for i in range(3)]
        # face 0 : vue de face (+Z), case 0 de l'atlas, enroulement anti-horaire vu de +Z
        assert all(0 <= u <= 0.25 and 0 <= v <= 0.5 for u, v in uv[:4])
        def nz(t):                                                         # composante z de la normale du triangle
            (a0, a1, _), (b0, b1, _), (c0, c1, _) = t
            return (b0 - a0) * (c1 - a1) - (b1 - a1) * (c0 - a0)
        assert nz(tris[0]) > 0 and nz(tris[1]) > 0                          # les triangles suivent les indices
        assert nz(tris[2]) < 0 and nz(tris[3]) < 0                          # son dos regarde −Z
        assert all(0.0 <= u <= 0.25 and 0.5 <= v <= 1 for u, v in uv[4:8])  # case 4 (180°) : 1re colonne, 2e ligne


def test_la_route_des_cartes_ecrit_un_fichier_telechargeable():
    import base64
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    atlas = "data:image/png;base64," + base64.b64encode(png(512, 256)).decode()

    async def go():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            ok = await c.post("/api/studio3d/decor/cartes", json={"job": "rocher", "version": 1, "atlas": atlas,
                                                                  "plans": 3})
            ko = await c.post("/api/studio3d/decor/cartes", json={"job": "rocher", "atlas": atlas, "plans": 5})
            fichier = await c.get("/api/studio3d/decor/cartes/rocher?version=1")
            absent = await c.get("/api/studio3d/decor/cartes/rocher?version=9")
            return ok, ko, fichier, absent
    ok, ko, fichier, absent = asyncio.run(go())
    assert ok.status_code == 200, ok.text
    assert ok.json()["triangles"] == 12 and ok.json()["fichier"] == "cartes.v1.glb"
    assert (ko.status_code, absent.status_code) == (400, 404)
    assert fichier.status_code == 200 and fichier.content[:4] == b"glTF"
    assert (J / "rocher" / "decor" / "cartes.v1.png").is_file()
    assert all(v["file"].startswith("model") for v in SO.fiche("rocher")["versions"])   # pas une version


# ── Plateau 3D ───────────────────────────────────────────────────────────────
def test_l_envoi_au_plateau_ajoute_une_instance_a_l_origine():
    from httpx import AsyncClient, ASGITransport
    from app.main import app

    async def go():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            sc = (await c.post("/api/scenes3d", json={"nom": "Forêt"})).json()
            un = await c.post("/api/studio3d/decor/plateau", json={"job": "plante", "scene": sc["id"]})
            deux = await c.post("/api/studio3d/decor/plateau", json={"job": "plante", "version": 1, "scene": sc["id"]})
            neuve = await c.post("/api/studio3d/decor/plateau", json={"job": "plante_var1"})
            ko = await c.post("/api/studio3d/decor/plateau", json={"job": "plante", "scene": "pas-une-scene"})
            lu = (await c.get(f"/api/scenes3d/{sc['id']}")).json()
            lu_neuve = (await c.get(f"/api/scenes3d/{neuve.json()['scene']}")).json()
            return un, deux, neuve, ko, lu, lu_neuve
    un, deux, neuve, ko, lu, lu_neuve = asyncio.run(go())
    assert un.status_code == 200, un.text
    assert deux.status_code == 200 and ko.status_code == 404
    insts = {i["id"]: i for i in lu["instances"]}
    a, b = insts["plante"], insts["plante_2"]
    assert a["source"] == {"kind": "assets3d", "job": "plante", "file": SO.fiche("plante")["versions"][-1]["file"]}
    assert b["source"]["file"] == "model.glb"
    assert a["transform"] == {"pos": [0.0, 0.0, 0.0], "rot": [0.0, 0.0, 0.0], "scale": 1.0} and a["role"] == "decor"
    assert [round(x, 6) for x in a["dims"]] == [1.0, 2.0, 0.5]                 # la taille réelle, en mètres
    assert un.json()["url"] == f"/plateau/?scene={lu['id']}"
    assert lu_neuve["nom"].startswith("Décor · ") and any(i["id"] == "plante_var1" for i in lu_neuve["instances"])
    assert SD.instance_plateau("x" * 60, "model.glb", "n", [1, 1, 1], set())["id"] == "x" * 34


def lancer_tous():
    rouges = []
    for nom, fn in list(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (Décor › Accessoire)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
