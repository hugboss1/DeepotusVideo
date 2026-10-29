"""t341 (lot Scenario, B5) — décor en calques de parallaxe : une peinture large découpée en 4 ou 5 calques
transparents nommés (ciel → premier plan), facteurs réglables, export Godot 4 `ParallaxBackground` (.tscn + PNG) et
PNG en ZIP, calques dans la Bibliothèque avec leur provenance.

Voie LOCALE vérifiée sur une peinture SYNTHÉTIQUE dont on connaît la profondeur (ciel clair en haut, collines
brumeuses, sol sombre et saturé en bas) : chaque bande retombe dans le bon calque, le ciel est opaque, aucun trou
sous le premier plan. Voie IA SIMULÉE (fal remplacé) : clé (503), devis + `confirme_cout` (409), plafonds, puis le
regroupement des calques rendus. La scène .tscn est relue comme Godot la lirait (sections, ext_resource, nœuds).

Run: & $PY tests/test_parallaxe.py   (depuis backend/ ; un processus par fichier)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzplx_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["FAL_KEY"] = ""
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import zipfile  # noqa: E402

import pytest  # noqa: E402
from loguru import logger  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

logger.remove()
from app.config import settings  # noqa: E402
from app.services import parallaxe as PX  # noqa: E402

W, H = 960, 320
#: bandes horizontales de la peinture synthétique, du loin (haut) au près (bas) : (y0, y1, couleur)
BANDES = [(0, 96, (200, 220, 240)),        # ciel : clair, peu saturé
          (96, 160, (170, 185, 200)),      # montagnes lointaines : brumeuses
          (160, 224, (110, 140, 120)),     # collines
          (224, 272, (60, 100, 40)),       # près : plus sombre, saturé
          (272, 320, (40, 25, 10))]        # premier plan : très sombre


def _peinture(nom="plx_peinture.png", w=W, h=H):
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y0, y1, c in BANDES:
        d.rectangle([0, y0 * h // H, w, y1 * h // H - 1], fill=c)
    im.save(settings.images_path / nom)
    return nom, im


def _appel(methode, chemin, corps=None, entetes=None):
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services.storage import init_db

    async def main():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            if methode == "POST":
                return await c.post(chemin, json=corps or {}, headers=entetes or {})
            if methode == "PUT":
                return await c.put(chemin, json=corps or {})
            return await c.get(chemin)
    return asyncio.run(main())


# ── la voie locale ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("n", [4, 5])
def test_locale_n_calques_de_la_taille_de_la_source_ciel_opaque(n):
    _nom, im = _peinture()
    cs = PX.decouper_local(im, n)
    assert len(cs) == n and all(c.size == im.size and c.mode == "RGBA" for c in cs)
    assert cs[0].getchannel("A").getextrema() == (255, 255)            # le ciel ferme le fond : jamais un trou
    for c in cs[1:]:
        assert c.getchannel("A").getextrema()[0] == 0                   # les autres sont transparents quelque part


def test_locale_chaque_bande_retombe_dans_son_calque():
    """Au milieu de chaque bande peinte, le calque qui OWNE le pixel (le plus proche dont l'alpha est plein et dont
    la couleur est celle de la source) est celui de la bande : le haut va au ciel, le bas au premier plan."""
    _nom, im = _peinture()
    cs = PX.decouper_local(im, 5)
    proprietaire = []
    for y0, y1, _c in BANDES:
        y = (y0 + y1) // 2
        k = max(i for i, c in enumerate(cs) if c.getpixel((W // 2, y))[3] > 200)
        proprietaire.append(k)
    assert proprietaire == sorted(proprietaire) and proprietaire[0] == 0 and proprietaire[-1] == 4, proprietaire


def test_locale_aucun_trou_sous_le_premier_plan():
    """Sous la bande d'un calque, le calque est REMPLI (alpha plein) d'une couleur étalée : le premier plan peut
    défiler plus vite sans ouvrir de trou transparent."""
    _nom, im = _peinture()
    cs = PX.decouper_local(im, 5)
    for k in range(1, 4):
        a = cs[k].getchannel("A")
        assert a.getpixel((W // 2, H - 5)) == 255, k                     # tout en bas : rempli
        r, g, b, _ = cs[k].getpixel((W // 2, H - 5))
        assert (r, g, b) != BANDES[-1][2], k                              # pas une copie du premier plan


def test_locale_refuse_un_nombre_hors_bornes():
    _nom, im = _peinture()
    for n in (3, 6, "x"):
        with pytest.raises(ValueError):
            PX.decouper_local(im, n)


def test_fondu_bords_rend_le_calque_bouclable():
    im = Image.new("RGBA", (200, 10), (255, 0, 0, 255))
    ImageDraw.Draw(im).rectangle([150, 0, 199, 9], fill=(0, 0, 255, 255))
    out = PX.fondu_bords(im, 0.1)
    assert out.size == (180, 10)                                       # la bande de droite (20 px) est fondue à gauche
    assert max(abs(a - b) for a, b in zip(out.getpixel((0, 5)), im.getpixel((180, 5)))) <= 8   # la colonne 0 SUIT la dernière
    assert out.getpixel((179, 5)) == im.getpixel((179, 5))
    assert out.getpixel((19, 5))[0] > 240                              # au bout du fondu, on retrouve la source
    assert out.getpixel((100, 5)) == im.getpixel((100, 5))             # le cœur ne bouge pas


def test_regrouper_paquets_contigus_et_taille_de_la_source():
    rendus = []
    for i in range(7):
        c = Image.new("RGBA", (100, 50), (0, 0, 0, 0))
        ImageDraw.Draw(c).rectangle([i * 10, 0, i * 10 + 9, 49], fill=(i * 30, 0, 0, 255))
        rendus.append(c)
    out = PX.regrouper(rendus, 4, (200, 100))
    assert len(out) == 4 and all(c.size == (200, 100) for c in out)
    # 7 calques → paquets [0,1] [2,3] [4,5]... contigus : le 1er paquet contient les rendus 0 et 1, pas le 2
    assert out[0].getpixel((10, 50))[3] == 255 and out[0].getpixel((50, 50))[3] == 0
    assert len(PX.regrouper(rendus[:3], 5, (100, 50))) == 3


def test_noms_et_facteurs():
    assert PX.noms_pour(5) == ["ciel", "lointain", "milieu", "proche", "premier_plan"]
    assert PX.noms_pour(4) == ["ciel", "lointain", "milieu", "premier_plan"]
    assert PX.noms_pour(3) == ["ciel", "milieu", "premier_plan"]
    f = PX.facteurs_pour(5)
    assert f == sorted(f) and f[0] < 0.2 and f[-1] > 1


# ── le devis ────────────────────────────────────────────────────────────────

def test_devis_vient_de_la_grille_des_tarifs():
    assert PX.devis("local", 5, W, H)["usd"] == 0
    assert PX.devis("qwen-layered", 5, W, H)["usd"] == pytest.approx(0.25)      # 5 calques × 0,05 $ (prudent)
    assert PX.devis("seedream-layerize", 4, 1000, 500)["usd"] == pytest.approx(17 * 0.03375, abs=1e-4)
    assert PX.devis("seedream-layerize", 4, 3072, 1024)["usd"] == pytest.approx(17 * 0.0675, abs=1e-4)
    with pytest.raises(ValueError):
        PX.devis("inconnu", 5, W, H)


def test_bornes_seedream():
    PX.verifier_taille("seedream-layerize", 3072, 1024)
    with pytest.raises(ValueError):
        PX.verifier_taille("seedream-layerize", 300, 300)                  # sous 512 × 512
    with pytest.raises(ValueError):
        PX.verifier_taille("local", 9000, 100)


# ── les routes ──────────────────────────────────────────────────────────────

def test_route_modeles_donne_le_devis_avant_tout_clic():
    r = _appel("GET", "/api/parallaxe/modeles?w=3072&h=1024&n=5")
    assert r.status_code == 200, r.text
    j = r.json()
    ids = [m["id"] for m in j["modeles"]]
    assert ids[0] == "local" and {"qwen-layered", "seedream-layerize"} <= set(ids)
    m = {x["id"]: x for x in j["modeles"]}
    assert m["local"]["devis"]["usd"] == 0 and m["qwen-layered"]["devis"]["usd"] > 0
    assert m["qwen-layered"]["cle_ok"] is False                           # sans clé : choisissable, refus au lancement
    assert j["noms"][0] == "ciel" and len(j["facteurs"]) == 5


def test_route_locale_puis_modifier_puis_exporter_godot_et_png():
    nom, _im = _peinture("plx_route.png")
    r = _appel("POST", "/api/parallaxe/decouper", {"image": nom, "n": 5, "modele": "local", "boucler": True})
    assert r.status_code == 200, r.text
    meta = r.json()
    pid = meta["pid"]
    assert re.match(r"^plx_[0-9a-f]{8}$", pid) and [c["id"] for c in meta["calques"]][0] == "ciel"
    assert meta["voie"] == "local" and meta["devis_usd"] == 0 and meta["calques"][-1]["devant"] is True

    # la Bibliothèque : un PNG par calque, source « tuiles », mère = la peinture, relation « parallaxe »
    from sqlalchemy import select
    from app.services.storage import LibraryAsset, async_session_factory

    async def lignes():
        async with async_session_factory() as s:
            return (await s.execute(select(LibraryAsset).where(LibraryAsset.filename.like(f"tile_{pid}_%")))).scalars().all()
    rows = asyncio.run(lignes())
    assert len(rows) == 5 and all((settings.images_path / x.filename).is_file() for x in rows)
    assert {x.source for x in rows} == {"tuiles"} and {x.parent_filename for x in rows} == {nom}
    assert {x.relation for x in rows} == {"parallaxe"} and json.loads(rows[0].recette)["decor"] == pid

    # réordonner, renommer, régler un facteur
    ordre = [dict(c) for c in meta["calques"]]
    ordre[1], ordre[2] = ordre[2], ordre[1]
    ordre[2]["facteur"] = 0.42
    ordre[0]["nom"] = "Ciel d'orage"
    r = _appel("PUT", f"/api/parallaxe/{pid}", {"calques": ordre})
    assert r.status_code == 200, r.text
    assert [c["id"] for c in r.json()["calques"]][:3] == ["ciel", "milieu", "lointain"]
    assert _appel("PUT", f"/api/parallaxe/{pid}", {"calques": ordre[:3]}).status_code == 400   # un calque perdu
    assert _appel("PUT", f"/api/parallaxe/{pid}", {"calques": [{**ordre[0], "facteur": 9}] + ordre[1:]}).status_code == 400

    r = _appel("GET", f"/api/parallaxe/{pid}/calque/ciel")
    assert r.status_code == 200 and r.content[:4] == b"\x89PNG"
    assert _appel("GET", f"/api/parallaxe/{pid}/calque/inconnu").status_code == 404
    assert _appel("GET", "/api/parallaxe/plx_zzzz").status_code == 400

    # Godot : un dossier avec la scène et ses PNG, chemins relatifs résolus dans le ZIP
    r = _appel("GET", f"/api/parallaxe/{pid}/export?format=godot")
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    z = zipfile.ZipFile(io.BytesIO(r.content))
    scenes = [n for n in z.namelist() if n.endswith(".tscn")]
    assert len(scenes) == 1
    tscn = z.read(scenes[0]).decode("utf-8")
    base = scenes[0].rsplit("/", 1)[0]
    chemins = re.findall(r'\[ext_resource type="Texture2D" path="([^"]+)" id="([^"]+)"\]', tscn)
    assert len(chemins) == 5 and all(f"{base}/{p}" in z.namelist() for p, _i in chemins)
    _verifier_tscn(tscn, meta["largeur"])
    assert '[node name="Ciel d\'orage" type="ParallaxLayer" parent="Fond"]' in tscn
    assert "motion_scale = Vector2(0.42, 0.42)" in tscn

    r = _appel("GET", f"/api/parallaxe/{pid}/export?format=png")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    pngs = sorted(n for n in z.namelist() if n.endswith(".png"))
    assert len(pngs) == 5 and pngs[0].endswith("1_ciel.png") and pngs[1].endswith("2_milieu.png")
    assert json.loads(z.read([n for n in z.namelist() if n.endswith("calques.json")][0]))["calques"][2]["facteur"] == 0.42
    assert _appel("GET", f"/api/parallaxe/{pid}/export?format=xyz").status_code == 400

    assert any(d["pid"] == pid for d in _appel("GET", "/api/parallaxe").json()["decors"])


def _verifier_tscn(tscn: str, largeur: int):
    """Relecture façon chargeur texte de Godot 4 : en-tête format=3 et load_steps = ressources + 1 ; chaque section
    est [type clé="valeur" …] ; chaque parent nommé existe ; chaque ExtResource désigne un id déclaré ; un
    ParallaxLayer par calque, avec motion_scale, motion_mirroring à la largeur et un Sprite2D non centré."""
    lignes = [x for x in tscn.split("\n") if x.strip()]
    entete = re.match(r'^\[gd_scene load_steps=(\d+) format=3\]$', lignes[0])
    assert entete, lignes[0]
    ids = re.findall(r'^\[ext_resource [^\]]* id="([^"]+)"\]$', tscn, re.M)
    assert int(entete.group(1)) == len(ids) + 1
    noeuds = re.findall(r'^\[node name="([^"]+)" type="(\w+)"(?: parent="([^"]+)")?\]$', tscn, re.M)
    assert noeuds[0] == ("Decor", "Node2D", "")
    chemins = {"."}
    for nom, _t, parent in noeuds[1:]:
        assert parent in chemins, (nom, parent)
        chemins.add(nom if parent == "." else f"{parent}/{nom}")
    for ligne in lignes:
        assert re.match(r'^(\[.+\]|[a-z_]+ = .+)$', ligne), ligne
    for ref in re.findall(r'ExtResource\("([^"]+)"\)', tscn):
        assert ref in ids
    types = [t for _n, t, _p in noeuds]
    assert types.count("ParallaxLayer") == types.count("Sprite2D") == len(ids)
    assert {"Fond", "DevantLeJeu"} <= {n for n, t, _p in noeuds if t == "ParallaxBackground"}
    assert tscn.count(f"motion_mirroring = Vector2({largeur}, 0)") == len(ids)
    assert tscn.count("centered = false") == len(ids)
    assert "layer = 1" in tscn                                              # le premier plan DEVANT le jeu


def test_route_ia_refuse_dans_l_ordre_puis_regroupe_le_rendu_simule():
    """Sans clé : 503. Clé, sans `confirme_cout` : 409 avec le devis, AUCUN appel. Confirmé : garde des plafonds
    (X-DZ-Plafond: confirme), faux Seedream qui rend l'image de base + 6 calques → 4 calques, fond opaque."""
    from app.services import asset3d_service as A3
    import fal_client
    nom, _im = _peinture("plx_ia.png", 1024, 512)
    appels = []

    async def faux_upload(p):
        appels.append(("upload", pathlib.Path(p).name))
        return "https://fal.example/source.png"

    async def faux_subscribe(ep, arguments=None, with_logs=False):
        appels.append(("fal", ep, arguments))
        return {"layers": [{"image": {"url": f"https://fal.example/{i}.png"}} for i in range(7)]}

    def faux_download(url, dest, timeout=120):
        i = int(url.rsplit("/", 1)[1].split(".")[0])
        c = Image.new("RGBA", (512, 256), (0, 0, 0, 0))
        ImageDraw.Draw(c).rectangle([0, i * 30, 511, i * 30 + 40], fill=(i * 30, 80, 200, 255))
        c.save(dest)
        appels.append(("dl", url))
        return True

    vieux = (A3._upload, fal_client.subscribe_async, A3._download)
    A3._upload, fal_client.subscribe_async, A3._download = faux_upload, faux_subscribe, faux_download
    corps = {"image": nom, "n": 4, "modele": "seedream-layerize"}
    try:
        sans_cle = _appel("POST", "/api/parallaxe/decouper", {**corps, "confirme_cout": True}).status_code
        settings.FAL_KEY = "cle-de-banc"
        r409 = _appel("POST", "/api/parallaxe/decouper", corps)
        avant = len(appels)
        r = _appel("POST", "/api/parallaxe/decouper", {**corps, "confirme_cout": True},
                   {"X-DZ-Plafond": "confirme"})
    finally:
        A3._upload, fal_client.subscribe_async, A3._download = vieux
        settings.FAL_KEY = ""
    assert sans_cle == 503 and avant == 0
    assert r409.status_code == 409 and r409.json()["detail"]["devis"]["usd"] > 0
    assert r.status_code == 200, r.text
    meta = r.json()
    assert ("fal", "bytedance/seedream/v5/pro/layerize", {"image_url": "https://fal.example/source.png"}) in appels
    assert [x for x in appels if x[0] == "dl"] and ("dl", "https://fal.example/0.png") not in appels   # base écartée
    assert len(meta["calques"]) == 4 and meta["voie"] == "fal" and meta["devis_usd"] > 0
    fond = Image.open(PX.dossier(meta["pid"]) / "calques" / meta["calques"][0]["fichier"])
    assert fond.size == (1024, 512) and fond.getchannel("A").getextrema() == (255, 255)


def test_route_qwen_demande_le_nombre_de_calques():
    from app.services import asset3d_service as A3
    import fal_client
    nom, _im = _peinture("plx_qwen.png", 800, 400)
    vus = []

    async def faux_upload(p):
        return "https://fal.example/s.png"

    async def faux_subscribe(ep, arguments=None, with_logs=False):
        vus.append((ep, arguments))
        return {"images": [{"url": f"https://fal.example/{i}.png"} for i in range(arguments["num_layers"])]}

    def faux_download(url, dest, timeout=120):
        Image.new("RGBA", (800, 400), (10, 20, 30, 255)).save(dest)
        return True

    vieux = (A3._upload, fal_client.subscribe_async, A3._download)
    A3._upload, fal_client.subscribe_async, A3._download = faux_upload, faux_subscribe, faux_download
    try:
        settings.FAL_KEY = "cle-de-banc"
        r = _appel("POST", "/api/parallaxe/decouper", {"image": nom, "n": 5, "modele": "qwen-layered",
                                                        "confirme_cout": True}, {"X-DZ-Plafond": "confirme"})
    finally:
        A3._upload, fal_client.subscribe_async, A3._download = vieux
        settings.FAL_KEY = ""
    assert r.status_code == 200, r.text
    assert vus == [("fal-ai/qwen-image-layered", {"image_url": "https://fal.example/s.png", "num_layers": 5,
                                                   "output_format": "png"})]
    assert [c["id"] for c in r.json()["calques"]] == PX.noms_pour(5)


def test_route_refus_gratuits():
    assert _appel("POST", "/api/parallaxe/decouper", {"image": "../x.png"}).status_code == 400
    assert _appel("POST", "/api/parallaxe/decouper", {"image": "absent.png"}).status_code == 404
    nom, _im = _peinture("plx_refus.png")
    assert _appel("POST", "/api/parallaxe/decouper", {"image": nom, "n": 9}).status_code == 400
    assert _appel("POST", "/api/parallaxe/decouper", {"image": nom, "modele": "zz"}).status_code == 400


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
