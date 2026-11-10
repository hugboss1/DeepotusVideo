# -*- coding: utf-8 -*-
"""UN NOM DE PREREGLAGE VAUT SON DICT, A L'OCTET PRES.

Defaut constate le 10/11/2026 en habillant le film promo Instagram :
`POST /api/subtitles/export` avec `"style": "pop"` repondait 500. Le style
du moteur acceptait deja un nom (`_subs_body_style`), mais les lectures du
karaoke (`ui_karaoke`, `ui_karaoke_mode`) faisaient `.get` sur la chaine — et
comme le karaoke se lit AVANT le choix du format, srt, vtt et txt tombaient
aussi. Avec le dict complet du prereglage (pris dans `GET /presets`), tout
marchait.

Ce banc verrouille le contrat :

  * un nom ne fait plus jamais 500, quel que soit le format ;
  * l'ASS d'un nom est EXACTEMENT celui de son dict (meme style, meme
    karaoke, meme mode) — pas « a un arrondi pres » : l'apercu et le fichier
    grave ne doivent pas dependre de la forme postee ;
  * srt, vtt et txt sortent a l'identique dans les deux formes ;
  * `/subtitles/style` et `/subtitles/check` acceptent le nom aussi.

Lance seul (un processus par fichier, cf. scripts/run-tests.ps1) :
    python -m pytest backend/tests/test_subs_export_prereglage.py -q
"""
# Amorce : le python embarque ignore PYTHONPATH (._pth) ; sans elle,
# `python tests/<ce fichier>` ne trouve pas le paquet `app`.
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import subtitle_service as S
from app.services import subtitle_ui as SU

client = TestClient(app, raise_server_exceptions=False)

#: Une replique calee mot par mot : sans `words`, le karaoke ne s'ecrirait
#: pas et le test ne verrait pas la difference de mode.
PISTE = [{
    "start": 0.0, "end": 1.6, "text": "Une ligne de texte",
    "words": [{"start": 0.0, "end": 0.4, "word": "Une"},
              {"start": 0.4, "end": 0.8, "word": "ligne"},
              {"start": 0.8, "end": 1.1, "word": "de"},
              {"start": 1.1, "end": 1.6, "word": "texte"}],
}]

RATIOS = ("9:16", "16:9", "1:1")


def _presets(ratio):
    r = client.get("/api/subtitles/presets", params={"ratio": ratio})
    assert r.status_code == 200, r.text
    return {p["id"]: p["style"] for p in r.json()["presets"]}


def _export(fmt, style, ratio):
    return client.post("/api/subtitles/export",
                       json={"format": fmt, "segments": PISTE,
                             "style": style, "ratio": ratio})


def test_les_neuf_prereglages_sont_servis():
    assert set(_presets("9:16")) == set(S.STYLES)


@pytest.mark.parametrize("ratio", RATIOS)
@pytest.mark.parametrize("pid", sorted(S.STYLES))
def test_ass_du_nom_egal_ass_du_dict(pid, ratio):
    """Le cas du film promo : « pop » en ASS. Etendu aux neuf prereglages et
    aux trois cadres — la conversion des tailles depend du canevas."""
    by_name = _export("ass", pid, ratio)
    by_dict = _export("ass", _presets(ratio)[pid], ratio)
    assert by_name.status_code == 200, by_name.text
    assert by_dict.status_code == 200, by_dict.text
    assert by_name.content == by_dict.content
    assert "\\k" in by_name.text          # le karaoke est bien grave


@pytest.mark.parametrize("fmt", ["srt", "vtt", "txt"])
@pytest.mark.parametrize("pid", ["pop", "surligneur", "standard"])
def test_autres_formats_identiques(fmt, pid):
    by_name = _export(fmt, pid, "9:16")
    by_dict = _export(fmt, _presets("9:16")[pid], "9:16")
    assert by_name.status_code == 200, by_name.text
    assert by_name.content == by_dict.content


def test_nom_inconnu_retombe_sur_le_defaut_sans_500():
    """Un nom inconnu se lit comme le prereglage par defaut (regle de
    `resolve_style`), jamais comme une erreur serveur."""
    r = _export("ass", "n_existe_pas", "9:16")
    d = _export("ass", S.DEFAULT_STYLE, "9:16")
    assert r.status_code == 200, r.text
    assert r.content == d.content


def test_lectures_du_panneau_acceptent_un_nom():
    ui = SU.style_to_ui("pop")
    assert SU.ui_karaoke("pop") == SU.ui_karaoke(ui)
    assert SU.ui_karaoke_mode("pop") == SU.ui_karaoke_mode(ui)
    assert SU.ui_anim("pop") == SU.ui_anim(ui)
    assert SU.ui_word_anim("pop") == SU.ui_word_anim(ui)
    assert SU.ui_unsupported("prime") == SU.ui_unsupported(SU.style_to_ui("prime"))
    # formes absurdes : lues comme un style vide, jamais d'exception
    for bad in (None, 3, ["pop"]):
        assert SU.ui_karaoke(bad) is True
        assert SU.ui_karaoke_mode(bad) == "bond"


def test_routes_style_et_check_acceptent_un_nom():
    ui = _presets("9:16")["pop"]
    a = client.post("/api/subtitles/style", json={"style": "pop", "ratio": "9:16"})
    b = client.post("/api/subtitles/style", json={"style": ui, "ratio": "9:16"})
    assert a.status_code == 200, a.text
    ja, jb = a.json(), b.json()
    for k in ("style", "karaoke", "karaoke_mode", "unsupported"):
        assert ja[k] == jb[k], k
    c = client.post("/api/subtitles/check",
                    json={"segments": PISTE, "style": "pop", "ratio": "9:16"})
    assert c.status_code == 200, c.text
