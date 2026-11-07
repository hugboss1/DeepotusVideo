# -*- coding: utf-8 -*-
"""Card Forge — t421 (cartes hexagonales, 07/11/2026, tâche 3) : les SORTIES qui ne
savent pas encore dessiner un hexagone le disent, en 409 avec une phrase, au lieu
de livrer un rectangle.

Pièces hors périmètre (spec « Aperçu ») : Volume, Forge 3D, Export 3D, Édition, et
dans l'Impression le paquet imprimeur, le contrôle avant vol et le masque de foil.
Le refus vit dans `hexa.refuser_si_hex` (décision du contrôleur) ; la phrase est
française en dur, comme toutes les HTTPException de cards/.

Pour chaque route : un deck `hex_p50` reçoit 409 et la phrase ; le même appel sur
un deck `poker_us` passe — 200 quand la route a une charge simple à fabriquer
ici, sinon la route rend SA PROPRE réponse (jamais la phrase hexagonale) : c'est
ce qui prouve que la garde ne touche pas un rectangle.

Run (depuis backend/) : <embedded python> tests/test_cards_hexa_refus.py
"""
import asyncio
import io
import json
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                   # noqa: E402
from httpx import ASGITransport, AsyncClient                    # noqa: E402
from PIL import Image                                           # noqa: E402

from app.services.cards import contract as CT                   # noqa: E402
from app.services.cards import core as CC                       # noqa: E402
from app.services.cards import hexa as HX                       # noqa: E402

PHRASE = "ne gère pas encore les cartes hexagonales"


def _api(method: str, path: str, **kw):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            return await c.request(method, path, timeout=300.0, **kw)
    return asyncio.run(go())


def _png(w: int, h: int, rgb=(40, 90, 160)) -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (w, h), rgb).save(b, "PNG")
    return b.getvalue()


def _deck(fmt: str, frame: dict | None = None) -> str:
    did = CC.create_deck("Banc refus " + fmt, {"fmt": fmt, "dpi": 300})["id"]
    if frame is not None:
        f = dict(CC.read_deck(did).get("frame") or {})
        f.update(frame)
        assert CC.patch_deck(did, {"frame": f}) is not None
    return did


SCEAU = {"edge_mm": 3.4, "inner_mm": 5.5,
         "seal": {"on": True, "kind": "dorure", "width_mm": 1.2,
                  "scope": {"screen": True, "print": True, "mesh": False}}}


def _appel(nom: str, did: str, fmt: str):
    """L'appel de la route `nom`, avec une charge VALIDE pour le format."""
    g = CT.geom(fmt, 300)
    w, h = g.canvas_px
    carte = _png(w, h)
    if nom == "print/preflight":
        return _api("POST", f"/api/cards/{did}/print/preflight",
                    json={"slots": [], "cards": [], "file_checks": False})
    if nom == "print/pack":
        wm, hm = CT.profile_geom("mpc", "poker_us").canvas_px
        return _api("POST", f"/api/cards/{did}/print/pack", data={"spec": json.dumps({"profile": "mpc"})},
                    files=[("fronts", ("f0.png", _png(wm, hm), "image/png"))])
    if nom == "print/foil-mask":
        return _api("GET", f"/api/cards/{did}/print/foil-mask?dpi=600")
    if nom == "gltf/atlas":
        return _api("POST", f"/api/cards/{did}/gltf/atlas", params={"i": 0}, content=_png(64, 64),
                    headers={"content-type": "application/octet-stream"})
    if nom == "gltf/build":
        return _api("POST", f"/api/cards/{did}/gltf/build", json={})
    if nom == "solid/mesh":
        return _api("GET", f"/api/cards/{did}/solid/mesh", params={"fmt": fmt, "dpi": "300"})
    if nom == "forge3d/layers":
        return _api("POST", f"/api/cards/{did}/forge3d/layers",
                    files=[("layers", ("cadre.png", carte, "image/png")),
                           ("composite", ("composite.png", carte, "image/png"))],
                    data={"side": "front"})
    if nom == "forge3d/build3d":
        return _api("POST", f"/api/cards/{did}/forge3d/build3d", json={})
    if nom == "forge3d/boite":
        return _api("POST", f"/api/cards/{did}/forge3d/boite", json={"cartes": 54})
    if nom == "edition/tts":
        return _api("POST", f"/api/cards/{did}/edition/tts", data={"spec": json.dumps({"noms": ["Une"]})},
                    files=[("fronts", ("f0.png", carte, "image/png"))])
    if nom == "edition/livret":
        return _api("POST", f"/api/cards/{did}/edition/livret",
                    data={"spec": json.dumps({"titre": "Règles", "texte": "Court."})})
    if nom == "edition/mockup":
        return _api("POST", f"/api/cards/{did}/edition/mockup", data={"spec": json.dumps({"cible": "carre"})},
                    files=[("images", ("c.png", carte, "image/png"))])
    raise AssertionError(nom)


# route -> ce que le rectangle obtient : 200, ou le code de la route elle-même
ROUTES = {
    "print/preflight": 200,
    "print/pack": 200,
    "print/foil-mask": 200,
    "gltf/atlas": None,          # un atlas factice : la route le juge (pas la garde)
    "gltf/build": 409,           # « aucun atlas déposé » — la phrase de la route, pas l'hexagone
    "solid/mesh": 200,
    "forge3d/layers": None,      # une seule couche : la route juge la pile
    "forge3d/build3d": None,     # graphe vide : la route le dit
    "forge3d/boite": 200,
    "edition/tts": 200,
    "edition/livret": 200,
    "edition/mockup": 200,
}


@pytest.mark.parametrize("nom", list(ROUTES))
def test_un_hexagone_est_refuse_en_409_avec_la_phrase(nom):
    did = _deck("hex_p50", SCEAU if nom == "print/foil-mask" else None)
    r = _appel(nom, did, "hex_p50")
    assert r.status_code == 409, (nom, r.status_code, r.text[:300])
    d = r.json()["detail"]
    assert isinstance(d, str) and PHRASE in d, (nom, d)


@pytest.mark.parametrize("nom", list(ROUTES))
def test_un_rectangle_passe_la_garde(nom):
    did = _deck("poker_us", SCEAU if nom == "print/foil-mask" else None)
    r = _appel(nom, did, "poker_us")
    attendu = ROUTES[nom]
    if attendu is not None:
        assert r.status_code == attendu, (nom, r.status_code, r.text[:300])
    if r.status_code != 200:
        d = r.json().get("detail")
        assert PHRASE not in json.dumps(d, ensure_ascii=False), (nom, d)


def test_la_phrase_nomme_la_sortie_et_un_rectangle_ne_leve_rien():
    from fastapi import HTTPException
    HX.refuser_si_hex(CT.geom("poker_us", 300), "Le volume")         # rien
    with pytest.raises(HTTPException) as e:
        HX.refuser_si_hex(CT.geom("hex_f90", 300), "Le volume")
    assert e.value.status_code == 409
    assert e.value.detail.startswith("Le volume " + PHRASE)


def test_les_lectures_de_chargement_restent_ouvertes_a_l_hexagone():
    """Les routes que l'écran lit à l'ouverture (info, état) ne refusent pas :
    sans elles le panneau ne pourrait même pas dire qu'il ne gère pas l'hexagone."""
    did = _deck("hex_p50")
    for chemin in ("solid/info", "gltf/info", "forge3d/info", "edition/cibles", "print/sheets"):
        r = _api("GET", f"/api/cards/{did}/{chemin}")
        assert r.status_code == 200, (chemin, r.status_code, r.text[:200])


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
