# -*- coding: utf-8 -*-
"""LES SEUILS AFFICHES SONT CEUX QUE LE MOTEUR APPLIQUE.

Defaut ferme au tour 7 : « On affiche les COMPTES sans jamais afficher les
REGLES. J'ai du retro-concevoir les seuils : c/s >= 20 (la ligne 11 a 20,1 est
marquee, la 12 a 19,9 ne l'est pas), ecart < ~2 images a 30 i/s. »

Le panneau ECRIT desormais ses quatre seuils et les laisse regler (les normes
varient selon le diffuseur : EBU 20 c/s, Netflix 17 en francais, reseaux 25).
Un seuil regle cote panneau et ignore cote moteur serait pire que pas de seuil
du tout : l'ecran afficherait « 17 c/s » pendant que les pastilles resteraient
calculees a 20. Ce fichier verrouille le contrat de `POST /subtitles/check` :

  * les seuils postes sont RESPECTES (une meme piste change de verdict) ;
  * ils sont RENVOYES, pour que le panneau puisse verifier ce qui a servi ;
  * un corps absent, hostile ou hors bornes retombe sur les constantes du
    moteur — on ne peut pas eteindre le controle qualite en postant
    `{"cps_warn": 0}`.

Lance seul (un processus par fichier, cf. scripts/run-tests.ps1) :
    python -m pytest backend/tests/test_subs_normes_api.py -q
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes import _subs_body_normes
from app.services import subtitle_service as S

client = TestClient(app)

# Une piste de controle a la FRONTIERE : « 20 caracteres exactement » dure
# 1,0 s, soit exactement 20 c/s — sous le seuil EBU (strictement superieur),
# au-dessus du seuil Netflix (17). C'est la ligne que le critique a du
# retro-concevoir en comparant deux repliques voisines.
PISTE = [
    {"start": 0.0, "end": 1.0, "text": "20 caracteres exact"},
    {"start": 2.0, "end": 5.0, "text": "Une replique posee, lisible"},
]


def _check(body):
    r = client.post("/api/subtitles/check", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _codes(d):
    return [w.get("kind") or w.get("code") for w in d["warnings"]]


def test_les_seuils_postes_sont_renvoyes():
    """Le panneau doit pouvoir VERIFIER avec quelle regle on l'a mesure."""
    d = _check({"segments": PISTE, "dur": 10,
                "normes": {"cps_warn": 17, "min_duration": 0.85,
                           "max_duration": 5, "min_gap": 0.083}})
    n = d["normes"]
    assert n["cps_warn"] == 17
    assert n["min_duration"] == 0.85
    assert n["max_duration"] == 5
    assert n["min_gap"] == 0.083


def test_sans_normes_le_moteur_garde_les_siennes():
    d = _check({"segments": PISTE, "dur": 10})
    n = d["normes"]
    assert n["cps_warn"] == S.CPS_WARN
    assert n["min_duration"] == S.MIN_DURATION
    assert n["max_duration"] == S.MAX_DURATION
    assert n["min_gap"] == S.MIN_GAP


def test_un_seuil_plus_severe_marque_davantage():
    """LE test qui compte : la meme piste, deux normes, deux verdicts."""
    large = _check({"segments": PISTE, "dur": 10,
                    "normes": {"cps_warn": 40}})
    serre = _check({"segments": PISTE, "dur": 10,
                    "normes": {"cps_warn": 8}})
    assert len(serre["warnings"]) > len(large["warnings"]), \
        "descendre le seuil doit marquer plus de repliques"
    # et le seuil serre parle bien de DEBIT
    assert any("debit" in str(k) or "vitesse" in str(k)
               for k in _codes(serre)), _codes(serre)


def test_la_duree_minimale_postee_agit():
    courte = [{"start": 0.0, "end": 0.9, "text": "brave"}]
    strict = _check({"segments": courte, "dur": 10,
                     "normes": {"min_duration": 2.0}})
    souple = _check({"segments": courte, "dur": 10,
                     "normes": {"min_duration": 0.5}})
    assert len(strict["warnings"]) > len(souple["warnings"])


def test_un_corps_hostile_ne_peut_pas_eteindre_le_controle():
    """Zero, negatif, chaine, NaN, absurde : on retombe sur le moteur."""
    for mauvais in ({"cps_warn": 0}, {"cps_warn": -5}, {"cps_warn": "beaucoup"},
                    {"cps_warn": 1e9}, {"cps_warn": None},
                    {"cps_warn": float("nan")}):
        n = _subs_body_normes({"normes": mauvais})
        assert n["cps_warn"] == S.CPS_WARN, mauvais
    # un corps qui n'est meme pas un objet
    for corps in ({"normes": "20"}, {"normes": []}, {}, {"normes": None}):
        n = _subs_body_normes(corps)
        assert n["cps_warn"] == S.CPS_WARN, corps


def test_un_minimum_au_dessus_du_maximum_ne_marque_pas_tout_deux_fois():
    """Sans garde-fou, min 9 s et max 3 s marqueraient CHAQUE replique des
    deux cotes a la fois : la borne basse cede, comme dans le panneau."""
    n = _subs_body_normes({"normes": {"min_duration": 3.9, "max_duration": 3.0}})
    assert n["min_duration"] <= n["max_duration"] - 0.09


def test_le_seuil_illisible_suit_le_seuil_regle():
    """CPS_ERROR valait 27 pour un CPS_WARN de 20. Le rapport suit : a 17 c/s,
    « illisible » ne peut pas rester a 27 — ce serait une seconde regle,
    invisible, que rien a l'ecran ne produirait."""
    n = _subs_body_normes({"normes": {"cps_warn": 17}})
    assert n["cps_error"] == pytest.approx(17 * 1.35, abs=0.01)
    assert n["cps_error"] > n["cps_warn"]
    # le defaut du moteur est preserve au point pres
    n20 = _subs_body_normes({"normes": {"cps_warn": 20}})
    assert n20["cps_error"] == pytest.approx(S.CPS_ERROR, abs=0.01)


def test_les_seuils_du_panneau_et_ceux_du_moteur_portent_les_memes_valeurs():
    """La couche `subs.js` declare `SUBS_NORM_DEF` ; le moteur declare
    CPS_WARN / MIN_DURATION / MAX_DURATION / MIN_GAP. Les deux doivent partir
    du MEME jeu, sinon un panneau hors ligne marquerait autrement qu'un
    panneau connecte — la divergence par le repli."""
    from pathlib import Path
    import re
    src = (Path(__file__).resolve().parents[2] / "frontend" / "patches" /
           "subs.js").read_text(encoding="utf-8")
    bloc = src.split("var SUBS_NORM_DEF=", 1)[1].split(";", 1)[0]
    lu = dict(re.findall(r"(\w+):([\d.]+)", bloc))
    assert float(lu["cps"]) == S.CPS_WARN
    assert float(lu["minS"]) == S.MIN_DURATION
    assert float(lu["maxS"]) == S.MAX_DURATION
    assert float(lu["gapMs"]) / 1000 == S.MIN_GAP
