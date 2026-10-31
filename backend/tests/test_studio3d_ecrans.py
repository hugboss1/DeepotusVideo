# -*- coding: utf-8 -*-
"""t388 + t392 (31/10/2026) — 3D Studio à écrans : la fiche du modèle ouvert, la galerie d'Ouvrir, les préréglages de
Préparer, puis la page (coque, écrans, clés FR/EN) et le calcul des écrans sous node.

Jobs SYNTHÉTIQUES (aucun appel réseau, aucune dépense) : un personnage riggé (`_squelette_synthetique.glb_cible`,
une peau, 22 os) en deux versions, une boîte sans rig, un job au GLB abîmé et un dossier vide.
Run : python tests/test_studio3d_ecrans.py (depuis backend/)"""
import asyncio, json, os, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzs3e_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = ""; os.environ["ELEVENLABS_API_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from loguru import logger                                         # noqa: E402
logger.remove()
from app.config import settings                                   # noqa: E402
from app.services import mesh_optimize, print3d, studio3d_ouvert as SO   # noqa: E402
import _squelette_synthetique as SQ                               # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]
J = settings.outputs_path / "assets3d"


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
_job("perso", {"model.glb": boite(), "model.v2.glb": RIG, "model.opt.glb": boite()},
     {"name": "Sorcière", "engine": "tripo-h3.1", "stage": "final", "created_at": "2026-10-30T10:00:00+00:00"})
_job("caisse", {"model.glb": boite()}, {"engine": "trellis", "created_at": "2026-10-29T10:00:00+00:00"})
_job("abime", {"model.glb": b"pas un glb du tout, vraiment pas"}, {"created_at": "2026-10-28T10:00:00+00:00"})
(J / "vide").mkdir(parents=True, exist_ok=True)


def _client():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


# ── le service ───────────────────────────────────────────────────────────────

def test_la_fiche_lit_le_rig_et_les_comptes_dans_le_seul_json_du_glb():
    f = SO.fiche("perso")
    assert (f["job"], f["nom"], f["moteur"], f["version"], f["derniere"]) == ("perso", "Sorcière", "tripo-h3.1", 2, 2)
    os_attendus = len({j for sk in mesh_optimize._read_glb_json(J / "perso" / "model.v2.glb")["skins"]
                       for j in sk["joints"]})
    assert os_attendus > 10
    assert f["rig"] == {"rigge": True, "os": os_attendus, "animations": 0}
    assert f["sommets"] > 0 and f["triangles"] > 0 and f["maillages"] >= 1
    assert f["url"] == "/api/assets/3d/perso/version/2" and f["vignette"] is None     # aucune image : aucun lien
    # la chaîne de l'Établi : silhouette < première vue < rendu du moteur < capture de la version
    d = J / "perso"
    (d / "sil_v2").mkdir()
    (d / "sil_v2" / "silhouette_face.png").write_bytes(b"png")
    assert SO.vignette("perso", 2) == "/api/assets/3d/perso/silhouette/face?v=2"
    (d / "shot_0.png").write_bytes(b"png")
    assert SO.vignette("perso", 2) == "/api/assets/3d/perso/shot/0"
    (d / "preview.png").write_bytes(b"png")
    assert SO.vignette("perso", 2) == "/api/assets/3d/perso/preview"
    (d / "vignette_v2.png").write_bytes(b"png")
    assert SO.fiche("perso")["vignette"] == "/api/assets/3d/perso/vignette?v=2"
    assert SO.vignette("perso", 1) == "/api/assets/3d/perso/preview"                # v1 sans capture
    for f_ in ("sil_v2/silhouette_face.png", "shot_0.png", "preview.png", "vignette_v2.png"):
        (d / f_).unlink()
    (d / "sil_v2").rmdir()
    assert [v["version"] for v in f["versions"]] == [1, 2]
    assert f["decimee"]["file"] == "model.opt.glb"          # la décimée est dite, hors numérotation


def test_une_version_choisie_et_les_refus():
    f = SO.fiche("perso", 1)
    assert f["version"] == 1 and f["derniere"] == 2 and f["rig"]["rigge"] is False and f["triangles"] == 12
    for job, v in (("inconnu", None), ("perso", 7), ("vide", None), ("../perso", 9)):
        try:
            SO.fiche(job, v)
        except FileNotFoundError:
            continue
        raise AssertionError((job, v))
    try:
        SO.fiche("abime")
    except ValueError:
        pass
    else:
        raise AssertionError("un GLB abîmé doit lever ValueError")


def test_une_version_de_l_etabli_dit_sa_source_et_son_operation():
    """Préparer compare une décimée à SA source : la fiche de l'Établi (`source.depuis.version`) remonte dans
    `versions`. Un registre absent, abîmé ou sans `source` ne casse rien."""
    _job("ligne", {"model.glb": boite(), "model.v2.glb": boite(), "model.v3.glb": boite()},
         {"created_at": "2026-10-01T10:00:00+00:00"})
    reg = {"current": 3, "entries": [
        {"file": "model.glb", "version": 1},
        {"file": "model.v2.glb", "version": 2, "source": {"outil": "etabli", "operation": "reparer",
                                                          "depuis": {"version": 1, "fichier": "model.glb"}}},
        {"file": "model.v3.glb", "version": 3, "source": {"outil": "etabli", "operation": "decimer",
                                                          "depuis": {"version": 2, "fichier": "model.v2.glb"}}}]}
    (J / "ligne" / "report.json").write_text(json.dumps(reg), encoding="utf-8")
    v = {e["version"]: (e["operation"], e["depuis"]) for e in SO.fiche("ligne")["versions"]}
    assert v == {1: (None, None), 2: ("reparer", 1), 3: ("decimer", 2)}
    (J / "ligne" / "report.json").write_text("{pas du json", encoding="utf-8")
    assert [e["depuis"] for e in SO.fiche("ligne")["versions"]] == [None, None, None]
    shutil.rmtree(J / "ligne")


def test_la_galerie_garde_un_job_abime_et_trie_du_plus_recent():
    m = SO.modeles()
    assert [x["job"] for x in m] == ["perso", "caisse", "abime"], [x["job"] for x in m]
    assert m[0]["rig"]["rigge"] and not m[1]["rig"]["rigge"]
    assert m[2]["illisible"] is True and m[2]["rig"] == {"rigge": False, "os": 0, "animations": 0}
    assert m[1]["nom"] == "caisse"                          # sans nom au manifeste : l'id


def test_les_cibles_de_preparer_vont_de_500_a_200k():
    c = SO.preparer_cibles()
    assert [x["preset"] for x in c] == SO.PREPARER
    assert c[0]["triangles"] == 500 and c[-1]["triangles"] == 200000
    assert [x["triangles"] for x in c] == sorted(x["triangles"] for x in c)
    assert mesh_optimize.resolve_target(preset="max") == (200000, "max")


# ── les routes ───────────────────────────────────────────────────────────────

def test_les_routes_lisent_sans_rien_ecrire():
    avant = sorted(str(p) for p in J.rglob("*"))

    async def go():
        async with _client() as c:
            r1 = await c.get("/api/studio3d/modeles")
            r2 = await c.get("/api/studio3d/ouvert/perso", params={"version": 1})
            r3 = await c.get("/api/studio3d/ouvert/inconnu")
            r4 = await c.get("/api/studio3d/ouvert/abime")
            r5 = await c.get("/api/studio3d/preparer/cibles")
            return r1, r2, r3, r4, r5
    r1, r2, r3, r4, r5 = asyncio.run(go())
    assert r1.status_code == 200 and len(r1.json()["modeles"]) == 3
    assert r2.status_code == 200 and r2.json()["version"] == 1
    assert (r3.status_code, r4.status_code) == (404, 400)
    assert r5.json()["cibles"][-1] == {"preset": "max", "triangles": 200000}
    assert sorted(str(p) for p in J.rglob("*")) == avant


# ── la page ─────────────────────────────────────────────────────────────────

def test_la_page_charge_la_coque_apres_le_graphe_sans_texte_neuf_dans_le_html():
    html = (RACINE / "frontend/studio3d/index.html").read_text(encoding="utf-8")
    assert html.index('src="graphe_vues.js"') < html.index('src="ecrans/coque.js"')
    assert 'href="ecrans/ecrans.css"' in html
    # le graphe garde ses crochets : la coque le pilote par window.__dzStudio3d, sans toucher studio3d.js (L9)
    s3d = (RACINE / "frontend/studio3d/studio3d.js").read_text(encoding="utf-8")
    assert s3d.count("window.__dzStudio3d = { S, NODES };") == 1


def test_les_cles_des_ecrans_existent_en_fr_et_en():
    dico = json.loads((RACINE / "frontend/shared/i18n/studio3decrans.json").read_text(encoding="utf-8"))
    src = "".join((RACINE / "frontend/studio3d/ecrans" / f).read_text(encoding="utf-8")
                  for f in os.listdir(RACINE / "frontend/studio3d/ecrans") if f.endswith(".js"))
    cles = {k for k in re.findall(r'\bT\("([a-z0-9_.]+)"', src) if not k.endswith((".", "_"))}
    assert len(cles) > 40, len(cles)
    for k in cles:
        assert "studio3decrans." + k in dico, k
    from_calc = (RACINE / "frontend/studio3d/ecrans/coque_calc.js").read_text(encoding="utf-8")
    for e in re.findall(r'\{ id: "([a-z]+)", groupe', from_calc):
        for role in ("onglet", "aide"):
            assert f"studio3decrans.{role}.{e}" in dico, (role, e)
    for k, v in dico.items():
        assert k.startswith("studio3decrans.") and len(k.split(".")) == 3, k
        assert v["fr"] and v["en"], k
        assert set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"])), k
    # les familles composées à l'exécution (T("espece." + id), T(`prevu.${ecran}_${i}`), T("decor." + champ)…)
    calc = (RACINE / "frontend/studio3d/ecrans/decor_calc.js").read_text(encoding="utf-8")
    familles = {
        "espece": re.findall(r'\{ id: "([a-z_]+)", groupe:', calc),
        "groupe": json.loads("[" + calc.split("export const GROUPES = [", 1)[1].split("]", 1)[0] + "]"),
        "feuille": json.loads("[" + calc.split("export const FEUILLES = [", 1)[1].split("]", 1)[0] + "]"),
        "ecorce": json.loads("[" + calc.split("export const ECORCES = [", 1)[1].split("]", 1)[0] + "]"),
        "saison": json.loads("[" + calc.split("export const SAISONS = [", 1)[1].split("]", 1)[0] + "]"),
        "filtre": ["tous", "rigges", "non_rigges", "personnages", "decor"],
        "preset": __import__("app.services.studio3d_ouvert", fromlist=["PREPARER"]).PREPARER,
        "rendu": ["texture", "argile", "fil"],
        "fiche": ["sommets", "triangles", "maillages", "materiaux", "os", "animations", "moteur"],
        "prevu": [f"{e}_{i}" for e in ("texture", "rig", "affiner", "animer", "exporter", "decor") for i in range(1, 5)],
        "auj": ["graphe_texture", "graphe_rig", "etabli_rig", "etabli_poids", "etabli_mouvement", "graphe_animer",
                "etabli_export", "version"],
        "type": [f"{t}{s}" for t in ("gltf", "obj", "stl", "fbx", "vrm", "daz") for s in ("", "_aide")],
        "decor": ["echelle", "niveaux", "densite", "taillefeuille", "retombee", "ventforce", "ventvitesse",
                  "ventdirection", "frisson", "feuilles", "rameaux", "vent", "ciel", "taille_petit", "taille_moyen",
                  "taille_grand", "feuillage_reel", "feuillage_cartes", "onglet_arbres", "onglet_sol"],
    }
    assert len(familles["espece"]) == 23
    for fam, ids in familles.items():
        for i in ids:
            assert f"studio3decrans.{fam}.{i}" in dico, (fam, i)
    assembled = (RACINE / "frontend/shared/dz-i18n-dico.js").read_text(encoding="utf-8")
    assert '"studio3decrans.onglet.preparer"' in assembled, "relancer scripts/i18n_assembler.py"


def test_aucun_rayon_litteral_dans_les_ecrans():
    css = (RACINE / "frontend/studio3d/ecrans/ecrans.css").read_text(encoding="utf-8")
    assert not re.search(r"border-radius\s*:(?!\s*(?:var\(--r\)|0\b|50%))", css)
    for f in os.listdir(RACINE / "frontend/studio3d/ecrans"):
        if f.endswith(".js"):
            assert "border-radius" not in (RACINE / "frontend/studio3d/ecrans" / f).read_text(encoding="utf-8"), f


def test_le_calcul_des_ecrans_sous_node():
    node = shutil.which("node")
    if not node:
        print("    (node absent : banc JS sauté)")
        return
    r = subprocess.run([node, str(RACINE / "frontend/studio3d/qa/ecrans.test.mjs")], capture_output=True,
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
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (3D Studio à écrans)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
