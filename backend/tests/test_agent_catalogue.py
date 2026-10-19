# -*- coding: utf-8 -*-
"""C1 (spec 2026-10-19-agent-catalogue-design.md) — le catalogue des éléments de l'assistant : extraction depuis le
code (dépôt factice en tmp_path), fusion sans écraser le rédigé, --check, et l'intégrité du vrai catalogue.
Run : & $PY tests/test_agent_catalogue.py   (depuis backend/)"""
import json, pathlib, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts" / "agent"))
sys.path.insert(0, str(RACINE / "backend"))
import catalogue_sources as S                                              # noqa: E402

BUNDLE = ('r.jsx("button",{className:"x",title:dzT("montage.outils.lame_titre"),icon:"dz-action-couper",'
          'children:dzT("montage.outils.lame")});r.jsx(K,{title:dzT("coque.rail.replier")});'
          'r.jsx("button",{onClick:f,title:"Lecture (Espace)"});r.jsx("button",{children:dzT("montage.outils.vide")})')


def _ecrire(p: pathlib.Path, txt: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")


@pytest.fixture
def depot(tmp_path):
    i18n = tmp_path / "frontend" / "shared" / "i18n"
    _ecrire(i18n / "montage.json", json.dumps({
        "montage.outils.lame": {"fr": "lame", "en": "blade"},
        "montage.outils.lame_titre": {"fr": "couper le clip", "en": "split the clip"},
        "montage.outils.vide": {"fr": "rien", "en": "nothing"}}, ensure_ascii=False))
    _ecrire(i18n / "coque.json", json.dumps({"coque.rail.replier": {"fr": "Replier", "en": "Collapse"},
                                             "commun.lit.lecture": {"fr": "Lecture (Espace)", "en": "Play (Space)"}}))
    _ecrire(i18n / "vectorlab.json", json.dumps({"vectorlab.core.grille_titre": {"fr": "Grille", "en": "Grid"}}))
    _ecrire(i18n / "photolab.json", json.dumps({"photolab.outil.pinceau": {"fr": "Pinceau", "en": "Brush"}}))
    _ecrire(tmp_path / "frontend" / "dist" / "assets" / "index-TEST.js", BUNDLE)
    _ecrire(tmp_path / "frontend" / "vectorlab" / "js" / "core.js", 'b.title = T("vectorlab.core.grille_titre");')
    _ecrire(tmp_path / "frontend" / "vectorlab" / "index.html", "<html></html>")
    _ecrire(tmp_path / "frontend" / "photolab" / "index.html", "<html></html>")
    _ecrire(tmp_path / "frontend" / "vectorlab" / "aide" / "index.json", json.dumps(
        [{"id": "plume", "titre": "Plume", "phrase": "Trace des courbes.", "titre_en": "Pen", "phrase_en": "Draws curves."}]))
    _ecrire(tmp_path / "backend" / "app" / "api" / "settings_routes.py",
            '_INDEX_FIXE = [\n    ("keys", "Clés API", "clé api jeton"),\n]\n')
    return tmp_path


def test_bundle_bouton_complet(depot):
    e = S.extraire(depot)
    x = e["montage.outils.lame"]
    assert x["type"] == "bouton" and x["ecran"] == "montage" and x["cadre"] is None
    assert x["libelle"] == {"fr": "lame", "en": "blade"}
    assert x["infobulle"] == {"fr": "couper le clip", "en": "split the clip"}
    assert x["icone"] == "dz-action-couper"
    assert set(x["sources"]) == {"i18n:montage.outils.lame", "i18n:montage.outils.lame_titre"}


def test_bundle_infobulle_seule_et_litteral(depot):
    e = S.extraire(depot)
    r = e["coque.rail.replier"]
    assert r["ecran"] == "commun" and r["libelle"] == {"fr": "", "en": ""} and r["infobulle"]["en"] == "Collapse"
    lit = [x for x in e.values() if x["id"].startswith("lit.")]
    assert len(lit) == 1 and lit[0]["infobulle"] == {"fr": "Lecture (Espace)", "en": "Play (Space)"}
    assert lit[0]["ecran"] == "commun"


def test_messages_ecartes(depot):
    assert "montage.outils.vide" not in S.extraire(depot)      # rôle « vide » = un message, pas un élément
