# -*- coding: utf-8 -*-
"""T107 (plan-moteurs-3d T8, D2) — banc de référence par sujet type. Le banc du banc : il RELIT le banc.json écrit et
vérifie que les chiffres viennent des fiches de maillage et du manifeste, jamais d'une saisie ; qu'une mesure ne peut
pas être rangée sous un AUTRE moteur que celui qui a produit le job ; qu'un moteur jamais mesuré n'invente rien ; que
/assets3d/engines cite le banc ; que POST /assets3d/banc range un job (local, gratuit) et refuse proprement.
Aucun réseau. Run : python tests/test_asset3d_banc.py (depuis backend/)"""
import asyncio, json, os, pathlib, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dzbanc_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["ELEVENLABS_API_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loguru import logger                                        # noqa: E402
logger.remove()
from app.config import settings                                  # noqa: E402
from app.services import asset3d_banc as B                       # noqa: E402
from app.services import asset3d_service as A3                   # noqa: E402
from app.services import gltf_builder, mesh_report               # noqa: E402


def _job(nom: str, moteur: str, forme: str = "sphere", **man) -> str:
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(gltf_builder.build_glb({}, None, forme, nom))
    A3.write_manifest(d, {"engine": moteur, "stage": "final", "version": 1, "texture_mode": "standard",
                          "shots": [], "quality": "medium", **man})
    mesh_report.write_report(nom, "model.glb", version=1, avec_silhouettes=True)
    return nom


def test_les_sujets_types_sont_trois_et_portent_leur_consigne():
    s = {x["id"]: x for x in B.sujets()}
    assert set(s) == {"personnage", "objet", "vehicule"}, sorted(s)
    for x in s.values():
        assert x["label"] and x["prompt"] and x["besoin"] in A3.BESOINS_3D, x


def test_mesurer_lit_la_fiche_du_maillage_et_pas_une_saisie():
    _job("bc_a", "tripo")
    L = B.mesurer("bc_a", "personnage")
    fiche = mesh_report.read_registry("bc_a")["entries"][-1]
    assert L["sujet"] == "personnage" and L["moteur"] == "tripo", L          # le moteur vient du MANIFESTE
    assert L["tris"] == fiche["geometry"]["tris"] > 0 and L["bytes"] == fiche["bytes"] > 0, L
    assert L["sha256"] == fiche["sha256"], L
    assert L["ferme"] == fiche["geometry"]["topologie"]["ferme"], L
    assert L["couverture"] == {k: fiche["silhouettes"][k]["couverture"] for k in ("face", "profil", "dessus")}, L
    assert abs(L["usd_estime"] - 0.30) < 1e-6, L                              # tripo texturé, sans vues
    relu = json.loads((settings.outputs_path / "assets3d" / "_banc" / "banc.json").read_text("utf-8"))
    assert L in relu["lignes"], relu


def test_le_cout_compte_les_vues_que_le_job_a_payees():
    _job("bc_v", "tripo-h3.1", multiview=True, views=4, texture_mode="HD", quality="hd")
    L = B.mesurer("bc_v", "objet")
    assert abs(L["usd_estime"] - (0.40 + 4 * 0.03)) < 1e-6, L                # H3.1 HD + 4 vues Seedream


def test_une_mesure_ne_se_range_pas_sous_un_autre_moteur():
    _job("bc_m", "trellis", "cube")
    try:
        B.mesurer("bc_m", "objet", "tripo"); raise AssertionError("rangée sous tripo")
    except ValueError as e:
        assert "trellis" in str(e) and "tripo" in str(e), e
    assert B.mesurer("bc_m", "objet", "trellis")["moteur"] == "trellis"     # le bon nom passe


def test_remesurer_le_meme_couple_remplace_la_ligne_sans_effacer_les_autres():
    _job("bc_b", "trellis", "cube")
    B.mesurer("bc_b", "objet")
    n1 = len(B.lire()["lignes"])
    B.mesurer("bc_b", "objet")
    assert len(B.lire()["lignes"]) == n1, "un couple sujet+moteur = UNE ligne"
    B.mesurer("bc_b", "vehicule")
    assert len(B.lire()["lignes"]) == n1 + 1


def test_le_resume_par_moteur_donne_ce_que_la_matrice_cite():
    _job("bc_c", "triposr", "cube"); B.mesurer("bc_c", "objet")
    _job("bc_c2", "trellis"); B.mesurer("bc_c2", "personnage")
    _job("bc_c3", "tripo", "cube"); B.mesurer("bc_c3", "vehicule")
    r = B.resume_par_moteur()
    x = r["triposr"]
    assert x["sujets"] >= 1 and x["tris_median"] > 0 and x["usd_median"] > 0, x
    assert "trellis" in r and "tripo" in r, sorted(r)
    assert "rodin" not in r, "un moteur jamais mesuré n'invente pas de chiffres"


def test_un_job_sans_fiche_ou_un_sujet_inconnu_refuse_au_lieu_de_deviner():
    (settings.outputs_path / "assets3d" / "bc_vide").mkdir(parents=True, exist_ok=True)
    try:
        B.mesurer("bc_vide", "objet"); raise AssertionError("aurait dû refuser")
    except FileNotFoundError as e:
        assert "fiche" in str(e).lower(), e
    _job("bc_p", "tripo")
    try:
        B.mesurer("bc_p", "poisson"); raise AssertionError("sujet inconnu")
    except ValueError as e:
        assert "poisson" in str(e), e
    assert all(l["sujet"] != "poisson" for l in B.lire()["lignes"])


def test_un_banc_illisible_ne_fait_pas_tomber_la_matrice():
    p = settings.outputs_path / "assets3d" / "_banc" / "banc.json"
    sauve = p.read_bytes()
    p.write_text("{pas du json", encoding="utf-8")
    try:
        assert B.lire()["lignes"] == [] and B.resume_par_moteur() == {}
    finally:
        p.write_bytes(sauve)


def test_routes():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    _job("bc_r", "rodin")

    async def main():
        o = {}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            e = (await c.get("/api/assets3d/engines")).json()
            o["avant"] = {m["id"]: m.get("banc") for m in e["engines"]}
            o["sujets"] = [s["id"] for s in e.get("sujets_banc") or []]
            r = await c.post("/api/assets3d/banc", json={"job": "bc_r", "sujet": "vehicule"})
            o["range"] = (r.status_code, r.json())
            o["apres"] = {m["id"]: m.get("banc") for m in (await c.get("/api/assets3d/engines")).json()["engines"]}
            o["sans_fiche"] = (await c.post("/api/assets3d/banc", json={"job": "bc_vide", "sujet": "objet"})).status_code
            o["poisson"] = (await c.post("/api/assets3d/banc", json={"job": "bc_r", "sujet": "poisson"})).status_code
            o["autre"] = (await c.post("/api/assets3d/banc", json={"job": "bc_r", "sujet": "objet",
                                                                  "moteur": "tripo"})).status_code
            o["vide"] = (await c.post("/api/assets3d/banc", json={})).status_code
            o["traversee"] = (await c.post("/api/assets3d/banc", json={"job": "../bc_r", "sujet": "objet"})).json()
        return o

    o = asyncio.run(main())
    assert o["sujets"] == ["personnage", "objet", "vehicule"], o["sujets"]
    assert o["avant"]["rodin"] is None and o["avant"]["tripo"]["mesures"] >= 1, o["avant"]   # trou dit tel quel
    st, L = o["range"]
    assert st == 200 and L["moteur"] == "rodin" and L["sujet"] == "vehicule", o["range"]
    assert o["apres"]["rodin"]["mesures"] == 1, o["apres"]["rodin"]
    assert o["sans_fiche"] == 404 and o["poisson"] == 400 and o["autre"] == 400 and o["vide"] == 400, o
    assert o["traversee"].get("job") in (None, "bc_r"), o["traversee"]                 # le nom du dossier, jamais un chemin


def lancer_tous():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception as e:                  # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom} — {type(e).__name__}: {e}")
    n = sum(1 for k in globals() if k.startswith("test_"))
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {n} tests, {len(rouges)} rouge(s) (asset3d_banc)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    lancer_tous()
