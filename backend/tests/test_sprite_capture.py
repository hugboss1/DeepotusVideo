"""t111 (plan-sprites T10, partie serveur) — le DÉPÔT d'une vue capturée depuis `<model-viewer>` : gardes, et la
MESURE de l'alpha.

Le banc ne fait pas tourner WebGL (la capture des huit orbites est l'écran, livré avec T12 après t110). Ce qu'il
mesure, c'est la porte : le nom de direction est une allowlist, le préfixe 8 hexadécimaux, la taille bornée avant
l'examen du contenu, la signature PNG vérifiée — et la réponse DIT si l'image reçue porte de la transparence : c'est
ce chiffre qui décidera du détourage, pas un souvenir sur le comportement de `toBlob()`. Puis les huit vues déposées
deviennent une feuille de huit directions taggées par la porte commune.

Run: python tests/test_sprite_capture.py   (depuis backend/ ; un processus par fichier)
"""
import io
import os
import pathlib
import subprocess
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzspc_")
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
from PIL import Image, ImageDraw  # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]
BASE = "fdababf3"
HUIT = ("south", "southwest", "west", "northwest", "north", "northeast", "east", "southeast")


def test_temoin_la_base_n_a_pas_la_route():
    r = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True,
                       cwd=str(RACINE)).stdout
    assert r and b"/assets/sprite/capture" not in r


def _png(transparent: bool, couleur=(200, 90, 40, 255)) -> bytes:
    im = Image.new("RGBA", (64, 64), (0, 0, 0, 0) if transparent else (18, 18, 22, 255))
    ImageDraw.Draw(im).ellipse([12, 12, 51, 51], fill=couleur)
    b = io.BytesIO()
    im.save(b, format="PNG")
    return b.getvalue()


def _appels(requetes):
    """[(méthode, chemin, kwargs)] dans UNE boucle (init_db compris) : [(statut, json ou None)]."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services.storage import init_db

    async def main():
        await init_db()
        out = []
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            for m, p, kw in requetes:
                r = await c.request(m, p, **kw)
                try:
                    out.append((r.status_code, r.json()))
                except ValueError:
                    out.append((r.status_code, None))
        return out
    return asyncio.run(main())


def _depot(d, prefixe, contenu, **kw):
    return ("POST", f"/api/assets/sprite/capture?dir={d}&prefix={prefixe}",
            {"content": contenu, "headers": {"Content-Type": "image/png"}, **kw})


def test_une_vue_transparente_est_ecrite_et_l_alpha_est_ANNONCE_une_opaque_aussi():
    from app.config import settings
    from app.services.storage import LibraryAsset, async_session_factory
    (s1, j1), (s2, j2) = _appels([_depot("northwest", "abc12345", _png(True)),
                                  _depot("south", "abc12345", _png(False))])
    assert (s1, s2) == (200, 200), (j1, j2)
    assert j1["filename"] == "gen_dir3d_abc12345_northwest.png" and j1["alpha"] is True
    assert j2["filename"] == "gen_dir3d_abc12345_south.png" and j2["alpha"] is False
    with Image.open(settings.images_path / j1["filename"]) as im:
        assert im.size == (64, 64) and im.getpixel((32, 32))[3] == 255
    assert not list(settings.images_path.glob("*.tmp")), "écriture atomique : aucun reste"

    async def source():
        async with async_session_factory() as s:
            return (await s.get(LibraryAsset, j1["filename"])).source
    assert asyncio.run(source()) == "sprites"


def test_les_gardes_de_la_porte():
    from app.config import settings
    avant = set(settings.images_path.iterdir())
    r = _appels([
        # la direction est une ALLOWLIST : un nom libre choisirait le nom d'un fichier de la Library
        _depot("../x", "abc12345", _png(True)), _depot("diagonale", "abc12345", _png(True)),
        _depot("South", "abc12345", _png(True)),
        # le préfixe aussi : 8 hexadécimaux minuscules, rien d'autre
        _depot("south", "../e", _png(True)), _depot("south", "ABC12345", _png(True)),
        _depot("south", "abc1234", _png(True)),
        # la taille borne AVANT l'examen du contenu
        _depot("south", "abc12345", b"\x89PNG\r\n\x1a\n" + b"\0" * (5 << 20)),
        # la signature : l'en-tête Content-Type ne prouve rien
        _depot("south", "abc12345", b"pas un png"),
        # la signature seule ne suffit pas : illisible = refusé
        _depot("south", "abc12345", b"\x89PNG\r\n\x1a\n" + b"\0" * 64),
        ("POST", "/api/assets/sprite/capture?dir=south", {"content": _png(True)}),
    ])
    assert [s for s, _ in r] == [400, 400, 400, 400, 400, 400, 413, 400, 400, 422], r
    assert set(settings.images_path.iterdir()) == avant, "aucun refus n'écrit dans la Library"


def test_huit_vues_deposees_deviennent_une_feuille_de_huit_directions():
    """Le chemin que l'écran prendra : huit dépôts, puis la porte commune avec la source `images` et un tag par
    direction, dans l'ordre de sprite_directions.HUIT."""
    from app.config import settings
    from app.services import sprite_directions as SD
    assert SD.HUIT == HUIT
    depots = _appels([_depot(d, "0badcafe", _png(True, (40 + 25 * i, 90, 40, 255))) for i, d in enumerate(HUIT)])
    noms = [j["filename"] for _, j in depots]
    assert all(j["alpha"] for _, j in depots)
    (s, j), = _appels([("POST", "/api/assets/sprite", {"json": {
        "source": {"kind": "images", "filenames": noms}, "remove_bg": "none", "columns": 4,
        "cell": {"size": 128}, "anim": {"tags": SD.tags_directions(list(HUIT))}}})])
    assert s == 200, j
    m = json.loads((settings.outputs_path / "sprites" / j["job_id"][:8] / "manifest.json").read_text("utf-8"))
    assert [t["name"] for t in m["anim"]["tags"]] == list(HUIT) and len(m["frames"]) == 8


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
