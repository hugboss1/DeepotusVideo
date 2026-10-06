"""T112 (spec sorceress, lot « Combat ») — hitboxes PAR FRAME : rectangles en pixels de cellule dans le manifeste,
écrits par une route qui ne touche QUE ce champ, bornés à la cellule, qui suivent leur frame quand l'éditeur T110
réordonne / duplique / supprime, et qui partent dans les exports texte (atlas JSON Hash, Paper2D) — fichiers du disque
(ZIP) ET téléchargements à la volée. Une feuille SANS hitbox garde ses exports à l'identique.

Run: python tests/test_sprite_hitbox.py   (depuis backend/ ; un processus par fichier)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzhit_")
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

COULEURS = [(220, 40, 40, 255), (40, 220, 40, 255), (40, 40, 220, 255)]


def _req(methode, chemin, corps=None):
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async def main():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.request(methode, "/api" + chemin, json=corps)
            return r.status_code, r.text, r.content
    return asyncio.run(main())


def _feuille(job):
    from app.config import settings
    from app.services import sprite_service as S
    noms = []
    for i, c in enumerate(COULEURS):
        im = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
        ImageDraw.Draw(im).rectangle([2, 2, 21, 21], fill=c)
        im.save(settings.images_path / f"{job}-{i}.png")
        noms.append(f"{job}-{i}.png")
    asyncio.run(S.generate_sprites({"source": {"kind": "images", "filenames": noms}, "cell": {"size": 128},
                                    "columns": 3, "fps_sample": 8}, job))
    return settings.outputs_path / "sprites" / job


def _manifeste(d):
    return json.loads((d / "manifest.json").read_text(encoding="utf-8"))


# ── le module pur ────────────────────────────────────────────────────────────

def test_une_frame_se_normalise_et_se_borne_a_la_cellule():
    from app.services import sprite_hitbox as H
    r = H.normaliser_frame([{"x": 10.4, "y": "5", "w": 20, "h": 30, "type": "hurt"},
                            {"x": 50, "y": 50, "w": 40, "h": 40},           # déborde : rogné à la cellule
                            {"x": 70, "y": 0, "w": 10, "h": 10}], 64, 64)   # entièrement dehors : écarté
    assert r == [{"x": 10, "y": 5, "w": 20, "h": 30, "type": "hurt"},
                 {"x": 50, "y": 50, "w": 14, "h": 14, "type": "hit"}], r    # type par défaut : hit


@pytest.mark.parametrize("mauvais, mot", [
    ([{"x": 0, "y": 0, "w": 0, "h": 5}], "vide"),
    ([{"x": 0, "y": 0, "w": 5, "h": 5, "type": "bouclier"}], "type"),
    (["pas un rectangle"], "rectangle"),
    ([{"x": "a", "y": 0, "w": 5, "h": 5}], "nombre"),
    ([{"x": 0, "y": 0, "w": 5, "h": 5}] * 17, "16"),
])
def test_les_refus_disent_quoi(mauvais, mot):
    from app.services import sprite_hitbox as H
    with pytest.raises(ValueError, match=mot):
        H.normaliser_frame(mauvais, 64, 64)


def test_toute_la_feuille_veut_une_liste_par_frame():
    from app.services import sprite_hitbox as H
    assert H.normaliser([[], [{"x": 1, "y": 1, "w": 2, "h": 2}], []], 3, 64, 64)[1] == [
        {"x": 1, "y": 1, "w": 2, "h": 2, "type": "hit"}]
    with pytest.raises(ValueError, match="3 frames"):
        H.normaliser([[], []], 3, 64, 64)


# ── la route ─────────────────────────────────────────────────────────────────

def test_ecrire_les_hitboxes_ne_touche_que_ce_champ_et_part_dans_les_exports():
    d = _feuille("j-hit")
    avant = _manifeste(d)
    with open(d / "sheet.ase", "rb") as f:
        ase_avant = f.read()
    corps = {"hitboxes": [[{"x": 4, "y": 4, "w": 20, "h": 30, "type": "hurt"}], [],
                          [{"x": 100, "y": 10, "w": 40, "h": 8, "type": "hit"}]]}
    st, txt, _ = _req("POST", "/assets/sprite/j-hit/hitboxes", corps)
    assert st == 200, txt
    apres = _manifeste(d)
    assert apres["frames"][0]["hitboxes"] == [{"x": 4, "y": 4, "w": 20, "h": 30, "type": "hurt"}]
    assert "hitboxes" not in apres["frames"][1], "une frame sans rectangle n'a pas de clé"
    assert apres["frames"][2]["hitboxes"] == [{"x": 100, "y": 10, "w": 28, "h": 8, "type": "hit"}], "rogné à 128"
    # rien d'autre n'a bougé
    for k in ("grid", "fps", "anim", "source", "created_at", "version"):
        assert apres[k] == avant[k], k
    for fa, fb in zip(avant["frames"], apres["frames"]):
        assert {k: v for k, v in fb.items() if k != "hitboxes"} == fa
    # les exports du DISQUE (ZIP) et le téléchargement à la volée portent les hitboxes
    atlas = json.loads((d / "sheet.atlas.json").read_text(encoding="utf-8"))
    nom0 = next(iter(atlas["frames"]))
    assert atlas["frames"][nom0]["hitboxes"] == apres["frames"][0]["hitboxes"], atlas["frames"][nom0]
    p2d = json.loads((d / "sheet.paper2dsprites").read_text(encoding="utf-8"))
    assert p2d["frames"][2]["hitboxes"][0]["w"] == 28 and "hitboxes" not in p2d["frames"][1]
    st, txt, _ = _req("GET", "/assets/sprite/j-hit/atlas")
    assert st == 200 and json.loads(txt)["frames"][nom0]["hitboxes"], txt[:200]
    with open(d / "sheet.ase", "rb") as f:
        assert f.read() == ase_avant, "l'Aseprite ne porte pas les hitboxes dans ce lot : inchangé"
    # le manifeste servi les rend
    st, txt, _ = _req("GET", "/assets/sprite/j-hit/manifest")
    assert json.loads(txt)["frames"][0]["hitboxes"][0]["type"] == "hurt"


def test_une_feuille_sans_hitbox_garde_ses_exports_a_l_identique():
    d = _feuille("j-sans")
    octets = {n: (d / n).read_bytes() for n in ("sheet.atlas.json", "sheet.paper2dsprites", "sheet.tres")}
    st, txt, _ = _req("POST", "/assets/sprite/j-sans/hitboxes", {"hitboxes": [[], [], []]})
    assert st == 200, txt
    assert all("hitboxes" not in f for f in _manifeste(d)["frames"])
    for n, o in octets.items():
        assert (d / n).read_bytes() == o, n


def test_les_refus_de_la_route():
    _feuille("j-ref")
    assert _req("POST", "/assets/sprite/inconnu/hitboxes", {"hitboxes": []})[0] == 404
    assert _req("POST", "/assets/sprite/j-ref/hitboxes", {"hitboxes": [[]]})[0] == 400          # 1 liste pour 3 frames
    assert _req("POST", "/assets/sprite/j-ref/hitboxes", {"hitboxes": "x"})[0] == 400
    st, txt, _ = _req("POST", "/assets/sprite/j-ref/hitboxes",
                      {"hitboxes": [[{"x": 0, "y": 0, "w": 5, "h": 5, "type": "bouclier"}], [], []]})
    assert st == 400 and "type" in txt, txt
    # `..%2F` : soit la route n'est pas atteinte (repli SPA), soit `Path(job).name` ramène au dossier des feuilles —
    # on teste l'ABSENCE DE FUITE (aucun manifeste écrit hors de outputs/sprites), pas un code
    from app.config import settings
    st, txt, _ = _req("POST", "/assets/sprite/..%2Fj-ref/hitboxes", {"hitboxes": [[], [], []]})
    assert st != 500 and not (settings.outputs_path / "j-ref").exists(), (st, txt[:120])


# ── l'éditeur T110 ───────────────────────────────────────────────────────────

def test_les_hitboxes_suivent_leur_frame_au_reassemblage():
    d = _feuille("j-ed")
    hb = [[{"x": 1, "y": 1, "w": 10, "h": 10, "type": "hit"}], [],
          [{"x": 2, "y": 2, "w": 20, "h": 20, "type": "hurt"}]]
    assert _req("POST", "/assets/sprite/j-ed/hitboxes", {"hitboxes": hb})[0] == 200
    st, txt, _ = _req("POST", "/assets/sprite/j-ed/reassemble", {"order": [2, 0, 0], "columns": 3})
    assert st == 200, txt
    m = _manifeste(d)
    assert [f.get("hitboxes") for f in m["frames"]] == [hb[2], hb[0], hb[0]], [f.get("hitboxes") for f in m["frames"]]
    atlas = json.loads((d / "sheet.atlas.json").read_text(encoding="utf-8"))
    assert [v.get("hitboxes") for v in atlas["frames"].values()] == [hb[2], hb[0], hb[0]], "exports du disque à jour"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
