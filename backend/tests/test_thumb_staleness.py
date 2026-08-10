# -*- coding: utf-8 -*-
"""La vignette de carte est un RENDU 3D FIGE : elle ne vaut que pour la
géométrie qui l'a produite.

Le défaut réel : les vignettes capturées avant la correction du placage UV
(MESH_VERSION 2) montraient la matière EN MIROIR. Après correction, l'aperçu 3D
et l'export étaient justes, mais la GALERIE continuait d'afficher ces PNG
d'avant — c'est ce que voit l'utilisateur tant que la scène 3D de la carte
n'est pas montée (case « aperçus 3D vivants » décochée, carte hors budget,
ou simplement avant le chargement). Le texte s'y lisait à l'envers.

La règle verrouillée ici : une vignette non estampillée de la version de
géométrie COURANTE est tenue pour absente — par l'API comme par l'archive.
La carte retombe alors sur la couleur de base, qui est plate et juste.

Run : <embedded python> backend/tests/test_thumb_staleness.py
"""
import io
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                               # noqa: E402
from PIL import Image                                       # noqa: E402

from app.services import material_store as MS               # noqa: E402
from app.services.gltf_builder import MESH_VERSION          # noqa: E402


def _png(color=(200, 40, 40)) -> bytes:
    b = io.BytesIO()
    Image.new("RGB", (512, 512), color).save(b, format="PNG")
    return b.getvalue()


@pytest.fixture()
def mid():
    m = MS.create_material(name="temoin")
    yield m["id"]


def test_vignette_ecrite_est_estampillee(mid):
    ok, msg = MS.write_thumb(mid, _png())
    assert ok, msg
    d = MS.material_dir(mid)
    assert (d / "thumb.png").is_file()
    assert (d / "thumb.mv").read_text(encoding="utf-8").strip() == str(MESH_VERSION)
    assert MS.thumb_is_current(d) is True
    assert MS.read_material(mid)["thumb"] is True


def test_vignette_d_avant_est_tenue_pour_absente(mid):
    """Le cas exact du bug : le PNG existe, il est lisible, il est simplement
    d'une géométrie révolue. Il ne doit plus être annoncé."""
    MS.write_thumb(mid, _png())
    d = MS.material_dir(mid)
    (d / "thumb.mv").write_text(str(MESH_VERSION - 1), encoding="utf-8")
    assert (d / "thumb.png").is_file(), "le fichier reste sur le disque"
    assert MS.thumb_is_current(d) is False
    assert MS.read_material(mid)["thumb"] is False


def test_vignette_sans_estampille_est_tenue_pour_absente(mid):
    """Toutes les vignettes déjà sur les disques des utilisateurs sont dans ce
    cas : aucune estampille, donc antérieures à la correction."""
    MS.write_thumb(mid, _png())
    d = MS.material_dir(mid)
    (d / "thumb.mv").unlink()
    assert MS.thumb_is_current(d) is False
    assert MS.read_material(mid)["thumb"] is False


def test_estampille_illisible_est_tenue_pour_absente(mid):
    MS.write_thumb(mid, _png())
    d = MS.material_dir(mid)
    (d / "thumb.mv").write_text("n'importe quoi", encoding="utf-8")
    assert MS.thumb_is_current(d) is False


def test_recapture_reactive_la_vignette(mid):
    """Le remède de l'utilisateur — « Vignette de la carte » — doit suffire."""
    MS.write_thumb(mid, _png())
    d = MS.material_dir(mid)
    (d / "thumb.mv").write_text("0", encoding="utf-8")
    assert MS.thumb_is_current(d) is False
    ok, _ = MS.write_thumb(mid, _png((30, 200, 90)))
    assert ok
    assert MS.thumb_is_current(d) is True


def test_l_archive_n_emporte_pas_une_vignette_perimee(mid):
    """Le bordereau annonce le contenu du ZIP : une vignette périmée ne doit
    figurer ni dans l'un ni dans l'autre."""
    MS.write_thumb(mid, _png())
    mat = MS.read_material(mid)
    man = MS.export_manifest(mat, "zip", "standard", 0, 8, None, "sphere")
    noms = [f["name"] for f in man["extras"]]
    assert "thumb.png" in noms, "vignette courante : elle part"

    d = MS.material_dir(mid)
    (d / "thumb.mv").write_text(str(MESH_VERSION - 1), encoding="utf-8")
    man2 = MS.export_manifest(MS.read_material(mid), "zip", "standard",
                              0, 8, None, "sphere")
    assert "thumb.png" not in [f["name"] for f in man2["extras"]], \
        "vignette d'avant : elle ne part pas"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
