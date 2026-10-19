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
    "sonvfx.extraire": {"id": "sonvfx.extraire", "ecran": "sonvfx", "cadre": None, "type": "bouton",
                        "libelle": {"fr": "Extraire le son → {piste}", "en": "Extract the sound → {piste}"},
                        "infobulle": None, "role": {"fr": "", "en": ""}, "synonymes": {"fr": [], "en": []},
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


def test_gabarits_hors_index(faux):
    assert A.chercher("piste") == []                                  # {piste} est un gabarit, pas un mot
    assert A.chercher("extraire le son")[0]["id"] == "sonvfx.extraire"


def test_vrai_catalogue_charge():
    A.catalogue.cache_clear()
    A._index.cache_clear()
    assert len(A.catalogue()) >= 300
    assert all(f["etat"] != "retire" for f in A.catalogue().values())


def test_sections_apres_contexte(faux):
    s = A.systeme("montage", "fr", "", pertinents=A.chercher("scinder"),
                  visibles={"reconnus": [FAUX["vectorlab.creer"]], "inconnus": [{"t": "Bidule", "i": "fait un truc"}]})
    tete, fin = s.split("## Contexte")
    assert "## Éléments pertinents" not in tete and "## Éléments pertinents" in fin
    assert "montage.lame (montage) « lame · Alt+C » [pointable] : Coupe le clip" in fin
    assert "## À l'écran maintenant" in fin and "vectorlab.creer « Créer »" in fin
    assert "« Bidule » (fait un truc) — non documenté" in fin
    assert A.systeme("quick", "fr", "").split("## Contexte")[0] == tete      # préfixe stable


def test_fiche_non_redigee_signalee(faux):
    s = A.systeme("vectorlab", "en", "", pertinents=[FAUX["vectorlab.creer"]])
    assert "vectorlab.creer (vectorlab) « Create » : — not written yet: describe only what is visible" in s


def test_point_sur_fiche(faux):
    _, actions, rejets = A.analyser("[POINT:montage.lame] [POINT:sonvfx.extraire]")
    assert rejets == 1 and len(actions) == 1
    a = actions[0]
    assert a["type"] == "point" and a["selecteur"] == "button" and a["texte"] == LOC["texte"]
    assert a["ecran"] == "montage" and a["fr"] == "lame · Alt+C" and a["partout"] is False


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
