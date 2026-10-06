"""t111 (plan-sprites T9, partie serveur) — les 4 directions DÉCOUPÉES dans la planche d'un personnage de la bible.

La planche est composée PAR CODE (`board_service.compose_character_board`) : son layout est déterministe, et le dépôt
sait déjà la découper (`board_service.decouper_planche`, tâche #62, 02/10). Le plan du 03/09 réécrivait un second
détecteur : il est antérieur à #62, et deux découpeurs auraient deux idées de ce qu'est une planche. T9 RÉUTILISE
celui de #62 — géométrie vérifiée à la hauteur exacte, vues écrites une fois et partagées.

Le fixture ne bricole pas une fausse planche : il appelle `compose_character_board`, celui-là même qui compose les
vraies. Si le layout change un jour, ce banc rougit, et c'est le but.

Run: python tests/test_sprite_directions.py   (depuis backend/ ; un processus par fichier)
"""
import os
import pathlib
import subprocess
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzspd_")
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
from PIL import Image  # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]
BASE = "fdababf3"
CORPS = {"front": (200, 40, 40), "left": (40, 200, 40), "right": (40, 40, 200), "back": (200, 200, 40)}
VISAGES = {"face_front": (120, 20, 20), "face_left": (20, 120, 20), "face_right": (20, 20, 120)}


def test_temoin_la_base_n_a_ni_module_ni_route():
    r = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True,
                       cwd=str(RACINE)).stdout
    assert r and b"/assets/sprite/from-board" not in r
    assert subprocess.run(["git", "cat-file", "-e", f"{BASE}:backend/app/services/sprite_directions.py"],
                          capture_output=True, cwd=str(RACINE)).returncode != 0


@pytest.fixture(scope="module")
def planche():
    from app.config import settings
    from app.services import board_service as BS
    panneaux = {}
    for cle, c in list(CORPS.items()) + list(VISAGES.items()):
        n = f"pan_{cle}.png"
        Image.new("RGB", (300, 400), c).save(settings.images_path / n)
        panneaux[cle] = n
    return BS.compose_character_board(settings.images_path, panneaux)


def test_les_quatre_CORPS_sortent_dans_l_ordre_des_directions(planche):
    from app.config import settings
    from app.services import sprite_directions as D
    noms = D.vues_de_planche(settings.images_path, planche, "character")
    assert [n.rsplit("_", 1)[1] for n in noms] == ["front.png", "left.png", "right.png", "back.png"]
    for n, cle in zip(noms, ("front", "left", "right", "back")):
        with Image.open(settings.images_path / n) as im:
            assert im.height == 560, (n, im.size)               # la bande des CORPS, pas celle des visages
            assert im.convert("RGB").getpixel((im.width // 2, im.height // 2)) == CORPS[cle], n
    assert D.directions() == ["south", "west", "east", "north"]


def test_les_tags_disent_UNE_image_par_direction():
    from app.services import sprite_directions as D
    from app.services.sprite_anim import normalize_anim
    tags = D.tags_directions(["south", "west", "east", "north"])
    assert [(t["name"], t["from"], t["to"]) for t in tags] == [("south", 0, 0), ("west", 1, 1), ("east", 2, 2),
                                                                ("north", 3, 3)]
    assert normalize_anim({"tags": tags}, 4)["tags"][3]["name"] == "north", "le service les accepte tels quels"


def test_une_image_qui_n_est_pas_une_planche_de_personnage_est_refusee_en_le_disant(planche):
    from app.config import settings
    from app.services import sprite_directions as D
    Image.new("RGB", (400, 300), (242, 239, 233)).save(settings.images_path / "uni.png")
    with pytest.raises(ValueError, match="planche de personnage"):
        D.vues_de_planche(settings.images_path, "uni.png", "character")
    with pytest.raises(ValueError, match="personnage"):        # un lieu n'a ni profil ni dos
        D.vues_de_planche(settings.images_path, planche, "location")


def _appel(chemin, corps):
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services.storage import init_db

    async def main():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post(chemin, json=corps)
            j = (await c.get(f"/api/jobs/{r.json()['job_id']}")).json() if r.status_code == 200 else None
        return r, j
    return asyncio.run(main())


def test_la_route_fabrique_une_feuille_de_4_directions_taggees_et_DIT_la_limite(planche):
    from app.config import settings
    r, j = _appel("/api/assets/sprite/from-board", {"board": planche, "cell": {"size": 128}})
    assert r.status_code == 200, r.text
    assert j["status"] == "done", j.get("error")
    assert j["title"] == f"Sprites · directions · {planche}"
    m = json.loads((settings.outputs_path / "sprites" / r.json()["job_id"][:8] / "manifest.json").read_text("utf-8"))
    assert [(t["name"], t["from"], t["to"]) for t in m["anim"]["tags"]] == [
        ("south", 0, 0), ("west", 1, 1), ("east", 2, 2), ("north", 3, 3)]
    assert m["source"]["kind"] == "images" and m["source"]["board"] == planche
    assert m["source"]["directions"] == "4/8", "la limite est ÉCRITE : les diagonales ne sont pas sur la planche"
    assert len(m["frames"]) == 4 and m["source"]["remove_bg"] == "chroma"


def test_les_vues_restent_des_vues_de_l_ATELIER_dans_la_bibliotheque(planche):
    """#62 indexe ces mêmes fichiers sous « atelier » et LI.noter ÉCRASE la provenance : le plan les notait
    « sprites », ce qui aurait reclassé les vues de l'Atelier à chaque feuille de directions."""
    from app.services.storage import LibraryAsset, async_session_factory
    _appel("/api/assets/sprite/from-board", {"board": planche})
    stem = pathlib.Path(planche).stem

    async def sources():
        async with async_session_factory() as s:
            return {c: (await s.get(LibraryAsset, f"{stem}_{c}.png")).source
                    for c in ("front", "left", "right", "back")}
    assert set(asyncio.run(sources()).values()) == {"atelier"}


def test_les_gardes_de_la_route(planche):
    for corps in ({}, {"board": ""}, {"board": "../" + planche}, {"board": "absent.png"}, {"board": "planche.txt"},
                  {"board": "uni.png"}, {"board": 3}):
        r, _ = _appel("/api/assets/sprite/from-board", corps)
        assert r.status_code == 400, (corps, r.status_code, r.text)
    r, _ = _appel("/api/assets/sprite/from-board", {"entity_id": "inconnu"})
    assert r.status_code == 404


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
