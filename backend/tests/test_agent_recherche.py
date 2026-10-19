# -*- coding: utf-8 -*-
"""C3/C4 (spec 2026-10-19-agent-catalogue-design.md § 4) — la recherche dans le catalogue, les sections du message
système, [POINT:id] sur une fiche, le relevé de l'écran ouvert côté serveur.
Run : & $PY tests/test_agent_recherche.py   (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile
import pytest

_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzrech_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.services import agent_aide as A                                    # noqa: E402

LOC = {"selecteur": "button", "texte": {"fr": "lame · Alt+C", "en": "blade · Alt+C"}}
FAUX = {
    "montage.lame": {"id": "montage.lame", "ecran": "montage", "cadre": None, "type": "bouton",
                     "libelle": {"fr": "lame · Alt+C", "en": "blade · Alt+C"},
                     "infobulle": {"fr": "couper le clip à la tête", "en": "split the clip at the playhead"},
                     "role": {"fr": "Coupe le clip sélectionné à la tête de lecture.", "en": "Splits the clip."},
                     "synonymes": {"fr": ["scinder", "rasoir"], "en": ["cut", "razor"]},
                     "localisateur": LOC, "etat": "redige"},
    "vectorlab.creer": {"id": "vectorlab.creer", "ecran": "vectorlab", "cadre": "/vectorlab/", "type": "bouton",
                        "libelle": {"fr": "Créer", "en": "Create"}, "infobulle": None,
                        "role": {"fr": "", "en": ""}, "synonymes": {"fr": [], "en": []},
                        "localisateur": None, "etat": "extrait"},
    "photolab.couper": {"id": "photolab.couper", "ecran": "photolab", "cadre": "/photolab/", "type": "outil",
                        "libelle": {"fr": "Recadrage", "en": "Crop"}, "infobulle": None,
                        "role": {"fr": "Coupe les bords de l'image.", "en": "Crops the image."},
                        "synonymes": {"fr": ["couper"], "en": []}, "localisateur": None, "etat": "redige"},
}


@pytest.fixture
def faux(monkeypatch):
    monkeypatch.setattr(A, "catalogue", lambda: FAUX)
    A._index.cache_clear()
    A._par_texte.cache_clear()
    yield
    A._index.cache_clear()
    A._par_texte.cache_clear()


def test_synonymes_et_accents(faux):
    assert [x["id"] for x in A.chercher("scinder une séquence")][:1] == ["montage.lame"]
    assert A.chercher("creer")[0]["id"] == "vectorlab.creer"                 # accents ignorés
    assert A.chercher("") == [] and A.chercher("le la de") == []


def test_bonus_ecran_et_visible(faux):
    ids = [x["id"] for x in A.chercher("couper", "photolab")]
    assert ids[0] == "photolab.couper"
    ids = [x["id"] for x in A.chercher("couper", "photolab", visibles=["montage.lame"])]
    assert ids[0] == "montage.lame"
    assert len(A.chercher("couper", n=1)) == 1


def test_vrai_catalogue_charge():
    A.catalogue.cache_clear()
    A._index.cache_clear()
    assert len(A.catalogue()) >= 300
    assert all(f["etat"] != "retire" for f in A.catalogue().values())


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
