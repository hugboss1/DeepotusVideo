"""t339 (lot Scenario, B3) — une feuille de 8 DIRECTIONS depuis la planche d'un personnage de la bible.

Convention des feuilles 8 directions (relevé Scenario, iso-cycles) : 5 directions DESSINÉES (S, SE, E, NE, N) et 3 en
MIROIR (SW <- SE, W <- E, NW <- NE). Chez nous, la planche de la bible porte déjà face (S), profils (W, et E qui en est
le miroir logiciel) et dos (N) : ces vues se DÉCOUPENT, gratuitement. Restent à générer les diagonales SE et NE ; les
trois miroirs sont cochés par défaut, décochables pour générer vraiment SW et NW.

LA RÈGLE « NE JAMAIS MIROITER » : un personnage qui tient un objet ASYMÉTRIQUE (épée dans la main droite, bouclier
au bras gauche) changerait de main dans un miroir. Case cochée : aucun miroir accepté (400), et l'est lui-même est
GÉNÉRÉ — l'est de la planche est le miroir du profil gauche (PANEL_PLANS["character"]["mirrors"]).

L'ARGENT : toute vue générée passe par le devis (route /devis, aucune dépense), puis `confirme_cout: true` (409 sinon,
avec le devis), puis la garde des plafonds. Le générateur est SIMULÉ ici : aucun appel réel.

Run: python tests/test_sprite_huit_directions.py   (depuis backend/ ; un processus par fichier)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzsp8_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["FAL_KEY"] = ""
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio  # noqa: E402
import json  # noqa: E402

import pytest  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

HUIT = ("south", "southwest", "west", "northwest", "north", "northeast", "east", "southeast")
# des corps ASYMÉTRIQUES (moitié gauche colorée, moitié droite claire) : un miroir se voit au pixel
CORPS = {"front": (200, 40, 40), "left": (40, 200, 40), "right": (40, 40, 200), "back": (200, 200, 40)}
VISAGES = {"face_front": (120, 20, 20), "face_left": (20, 120, 20), "face_right": (20, 20, 120)}


def _corps(c):
    im = Image.new("RGB", (300, 400), (250, 250, 250))
    im.paste(Image.new("RGB", (150, 400), c), (0, 0))
    return im


@pytest.fixture(scope="module")
def planche():
    from app.config import settings
    from app.services import board_service as BS
    panneaux = {}
    for cle, c in list(CORPS.items()) + list(VISAGES.items()):
        n = f"pan8_{cle}.png"
        (_corps(c) if cle in CORPS else Image.new("RGB", (300, 400), c)).save(settings.images_path / n)
        panneaux[cle] = n
    return BS.compose_character_board(settings.images_path, panneaux)


# ── le plan (module pur) ─────────────────────────────────────────────────────
def _sources(plan):
    return {p["direction"]: (p["source"], p.get("de")) for p in plan}


def test_par_defaut_5_dessinees_dont_3_decoupees_et_3_miroirs():
    from app.services import sprite_directions as SD
    assert SD.DESSINEES == ("south", "southeast", "east", "northeast", "north")
    assert SD.MIROIRS == {"southwest": "southeast", "west": "east", "northwest": "northeast"}
    plan = SD.plan_huit()
    assert [p["direction"] for p in plan] == list(HUIT), "l'ordre des cases EST celui de HUIT (tags, exports)"
    assert _sources(plan) == {
        "south": ("planche", "front"), "east": ("planche", "right"), "north": ("planche", "back"),
        "southeast": ("generee", None), "northeast": ("generee", None),
        "southwest": ("miroir", "southeast"), "west": ("miroir", "east"), "northwest": ("miroir", "northeast")}
    assert SD.generations(plan) == ["northeast", "southeast"], "dans l'ordre de HUIT"


def test_decocher_les_miroirs_fait_generer_ou_decouper_vraiment():
    from app.services import sprite_directions as SD
    plan = SD.plan_huit(miroirs=[])
    s = _sources(plan)
    assert s["west"] == ("planche", "left"), "l'ouest est DESSINÉ sur la planche (profil gauche) : gratuit"
    assert s["southwest"] == ("generee", None) and s["northwest"] == ("generee", None)
    assert SD.generations(plan) == ["southwest", "northwest", "northeast", "southeast"]
    # un seul miroir décoché
    assert _sources(SD.plan_huit(miroirs=["west", "northwest"]))["southwest"] == ("generee", None)


def test_objet_asymetrique_ne_jamais_miroiter():
    from app.services import sprite_directions as SD
    with pytest.raises(ValueError, match="ne jamais miroiter"):
        SD.plan_huit(miroirs=["west"], asymetrique=True)
    plan = SD.plan_huit(miroirs=[], asymetrique=True)
    assert not [p for p in plan if p["source"] == "miroir"]
    # l'est de la planche est le MIROIR du profil gauche : l'objet y changerait de main — il est généré
    assert _sources(plan)["east"] == ("generee", None)
    assert _sources(plan)["west"] == ("planche", "left")
    assert len(SD.generations(plan)) == 5
    with pytest.raises(ValueError, match="miroir"):
        SD.plan_huit(miroirs=["east"])                # l'est est dessiné, jamais un miroir


def test_les_prompts_des_vues_generees():
    from app.services import sprite_directions as SD
    for d in ("southeast", "northeast", "southwest", "northwest", "east"):
        p = SD.prompt_vue(d, asymetrique=False)
        assert "exact same character" in p and "full body" in p.lower(), d
    assert "RIGHT" in SD.prompt_vue("southeast") and "LEFT" in SD.prompt_vue("southwest")
    assert "BACK" in SD.prompt_vue("northeast") and "FRONT" in SD.prompt_vue("southeast")
    assert "same hand" in SD.prompt_vue("southeast", asymetrique=True)
    assert "same hand" not in SD.prompt_vue("southeast")
    # la référence : la face pour les vues tournées vers la caméra, le dos pour les autres
    assert SD.reference_vue("southeast") == "front" and SD.reference_vue("northwest") == "back"
    with pytest.raises(ValueError):
        SD.prompt_vue("south")


# ── les routes ───────────────────────────────────────────────────────────────
def _appel(chemin, corps):
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services.storage import init_db

    async def main():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post(chemin, json=corps)
            j = None
            if r.status_code == 200 and "job_id" in r.json():
                j = (await c.get(f"/api/jobs/{r.json()['job_id']}")).json()
        return r, j
    return asyncio.run(main())


@pytest.fixture
def generateur(monkeypatch):
    """Le générateur SIMULÉ : une image unie par vue, aucun appel réseau ; la clé « existe »."""
    from app.api import routes as R
    from app.config import settings
    from app.services import image_providers as IP
    appels = []

    async def faux(prompt, ref, provider):
        appels.append({"prompt": prompt, "ref": ref.name, "provider": provider})
        n = f"gen_t339_{len(appels):02d}.png"
        _corps((10 * len(appels), 90, 160)).save(settings.images_path / n)
        return n
    monkeypatch.setattr(R, "_generer_vue_direction", faux)
    monkeypatch.setattr(IP, "missing_key", lambda m: None)
    return appels


def test_le_devis_ne_depense_rien_et_compte_les_generations(planche, generateur):
    r, _ = _appel("/api/assets/sprite/from-board/devis", {"board": planche, "directions": 8})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["generations"] == 2 and d["usd"] > 0 and d["provider"] == "flux"
    assert [p["direction"] for p in d["plan"]] == list(HUIT)
    r, _ = _appel("/api/assets/sprite/from-board/devis",
                  {"board": planche, "directions": 8, "miroirs": [], "objet_asymetrique": True})
    assert r.json()["generations"] == 5
    r, _ = _appel("/api/assets/sprite/from-board/devis", {"board": planche, "directions": 4})
    assert r.json()["generations"] == 0 and r.json()["usd"] == 0
    r, _ = _appel("/api/assets/sprite/from-board/devis",
                  {"board": planche, "directions": 8, "objet_asymetrique": True})
    assert r.status_code == 400 and "miroiter" in r.text
    assert generateur == [], "un devis ne génère rien"


def test_sans_confirmation_409_avec_le_devis_et_rien_ne_part(planche, generateur):
    r, _ = _appel("/api/assets/sprite/from-board", {"board": planche, "directions": 8})
    assert r.status_code == 409, r.text
    det = r.json()["detail"]
    assert det["generations"] == 2 and det["usd"] > 0
    assert generateur == []


def test_la_cle_absente_refuse_en_503_avant_le_devis(planche, monkeypatch):
    r, _ = _appel("/api/assets/sprite/from-board", {"board": planche, "directions": 8, "confirme_cout": True})
    assert r.status_code == 503, r.text          # FAL_KEY vide : refus AVANT la garde, aucune ligne de dépense


def test_huit_directions_confirmees_feuille_taggee_miroirs_au_pixel(planche, generateur, monkeypatch):
    from app.api import routes as R
    from app.config import settings
    gardes = []
    vrai = R._plafond

    async def plafond(op, categorie, ref=None):
        gardes.append((op, categorie))
        return await vrai(op, categorie, ref)
    monkeypatch.setattr(R, "_plafond", plafond)
    r, j = _appel("/api/assets/sprite/from-board",
                  {"board": planche, "directions": 8, "confirme_cout": True, "cell": {"size": 128}})
    assert r.status_code == 200, r.text
    assert j["status"] == "done", j.get("error")
    assert len(generateur) == 2 and {a["ref"].rsplit("_", 1)[1] for a in generateur} == {"front.png", "back.png"}
    assert ({"kind": "flux_kontext", "n": 2}, "sprites") in gardes, gardes
    court = r.json()["job_id"][:8]
    dossier = settings.outputs_path / "sprites" / court
    m = json.loads((dossier / "manifest.json").read_text("utf-8"))
    assert [(t["name"], t["from"], t["to"]) for t in m["anim"]["tags"]] == [(d, i, i) for i, d in enumerate(HUIT)]
    assert len(m["frames"]) == 8 and m["source"]["directions"] == "8/8"
    assert m["source"]["generations"] == 2 and m["source"]["objet_asymetrique"] is False
    plan = {p["direction"]: p for p in m["source"]["plan"]}
    assert plan["west"]["source"] == "miroir" and plan["southeast"]["source"] == "generee"
    # le miroir EST le miroir de sa source, au pixel (fichiers de la Library)
    for d, src in (("west", "east"), ("southwest", "southeast"), ("northwest", "northeast")):
        with Image.open(settings.images_path / plan[d]["fichier"]) as a, \
                Image.open(settings.images_path / plan[src]["fichier"]) as b:
            assert list(a.convert("RGB").getdata()) == list(ImageOps.mirror(b.convert("RGB")).getdata()), d
    # les exports connaissent les 8 directions, dans l'ordre, et lesquelles sont des miroirs
    atlas = json.loads((dossier / "sheet.atlas.json").read_text("utf-8"))
    dirs = atlas["meta"]["directions"]
    assert [x["name"] for x in dirs] == list(HUIT) and [x["frame"] for x in dirs] == list(range(8))
    assert {x["name"]: x.get("mirror_of") for x in dirs}["west"] == "east"
    assert {x["name"]: x["flip_h"] for x in dirs} == {d: d in ("southwest", "west", "northwest") for d in HUIT}
    p2d = json.loads((dossier / "sheet.paper2dsprites").read_text("utf-8"))
    assert [x["name"] for x in p2d["meta"]["directions"]] == list(HUIT)
    tres = (dossier / "sheet.tres").read_text("utf-8")
    assert all(f'&"{d}"' in tres for d in HUIT)


def test_objet_asymetrique_genere_l_est_et_refuse_tout_miroir(planche, generateur):
    r, _ = _appel("/api/assets/sprite/from-board",
                  {"board": planche, "directions": 8, "objet_asymetrique": True, "confirme_cout": True})
    assert r.status_code == 400 and "miroiter" in r.text, r.text
    assert generateur == []
    r, j = _appel("/api/assets/sprite/from-board", {"board": planche, "directions": 8, "objet_asymetrique": True,
                                                    "miroirs": [], "confirme_cout": True})
    assert r.status_code == 200, r.text
    assert j["status"] == "done", j.get("error")
    assert len(generateur) == 5 and all("same hand" in a["prompt"] for a in generateur)


def test_les_gardes_du_corps(planche, generateur):
    for corps in ({"board": planche, "directions": 6}, {"board": planche, "directions": "8"},
                  {"board": planche, "directions": 8, "miroirs": "west"},
                  {"board": planche, "directions": 8, "miroirs": ["nord"]},
                  {"board": planche, "directions": 8, "objet_asymetrique": "oui"}):
        r, _ = _appel("/api/assets/sprite/from-board", corps)
        assert r.status_code == 400, (corps, r.status_code, r.text)
    assert generateur == []


def test_quatre_directions_inchangees(planche):
    from app.config import settings
    r, j = _appel("/api/assets/sprite/from-board", {"board": planche})
    assert r.status_code == 200 and j["status"] == "done", r.text
    m = json.loads((settings.outputs_path / "sprites" / r.json()["job_id"][:8] / "manifest.json").read_text("utf-8"))
    assert m["source"]["directions"] == "4/8" and len(m["frames"]) == 4
    atlas = json.loads((settings.outputs_path / "sprites" / r.json()["job_id"][:8] / "sheet.atlas.json")
                       .read_text("utf-8"))
    assert [x["name"] for x in atlas["meta"]["directions"]] == ["south", "west", "east", "north"]
    assert not any(x["flip_h"] for x in atlas["meta"]["directions"])


def test_le_devis_compte_au_tarif_du_modele_REELLEMENT_appele(planche, monkeypatch):
    """Le tir FLUX passe par fal-ai/flux-kontext/dev, pas par FLUX schnell : le devis, l'affichage et la garde des
    plafonds comptent au tarif de CE modèle (0,025 $ par vue, relevé sur fal.ai le 29/10/2026)."""
    from app.api import routes as R
    from app.config import settings
    from app.services import pricing as P
    appels = []

    async def faux_flux(prompt, size, n, seed=None, model="", image_path=None, ratio=None, guidance=None):
        appels.append(model)
        nom = f"gen_kx_{len(appels)}.png"
        _corps((0, 0, 0)).save(settings.images_path / nom)
        return {"images": [nom], "seed": 1}
    monkeypatch.setattr(R, "_flux_generate", faux_flux)
    asyncio.run(R._generer_vue_direction("p", settings.images_path / "pan8_front.png", "flux"))
    endpoint, id_prix = R._SPRITE_VUE_FLUX
    assert appels == [endpoint] == ["fal-ai/flux-kontext/dev"], "le modèle appelé est celui que le devis chiffre"
    assert R._sprite_op_directions("flux", 2) == {"kind": id_prix, "n": 2}
    ligne = P.estimate(R._sprite_op_directions("flux", 1))["breakdown"][0]
    assert ligne["provider"] == "fal" and "Kontext" in ligne["label"] and ligne["usd"] == P.DEFAULTS["flux_kontext_usd"] == 0.025
    assert P.estimate(R._sprite_op_directions("flux", 2))["total_usd"] > P.estimate({"kind": "image", "n": 2})["total_usd"]
    r, _ = _appel("/api/assets/sprite/from-board/devis", {"board": planche, "directions": 8})
    assert r.json()["usd"] == round(2 * P.DEFAULTS["flux_kontext_usd"], 4), r.json()
    r, _ = _appel("/api/assets/sprite/from-board/devis",
                  {"board": planche, "directions": 8, "miroirs": [], "objet_asymetrique": True})
    assert r.json()["usd"] == round(5 * P.DEFAULTS["flux_kontext_usd"], 4)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
