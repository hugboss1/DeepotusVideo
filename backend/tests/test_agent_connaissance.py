# -*- coding: utf-8 -*-
"""A1 (spec 2026-10-19-agent-aide-design.md) — la connaissance de l'assistant est cohérente :
ancres.json bien formé ; écrans connus ; sections de Réglages connues ; texte d'ancre présent dans l'application
(bundle ou dictionnaire) ; AGENT.md ne cite que des ancres, vues et chapitres qui existent.
Run : & $PY tests/test_agent_connaissance.py   (depuis backend/)"""
import json, pathlib, re, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "backend"))
from app.services import agent_aide as A                                    # noqa: E402

ANCRES = json.loads((RACINE / "docs" / "agent" / "ancres.json").read_text(encoding="utf-8"))["ancres"]
CHAPITRES = {c["id"] for c in json.loads((RACINE / "docs" / "guide" / "src" / "chapitres.json")
                                         .read_text(encoding="utf-8"))["chapitres"]}
BUNDLE = next((RACINE / "frontend" / "dist" / "assets").glob("index-*.js")).read_text(encoding="utf-8")
DICO = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_text(encoding="utf-8")
LABS = {"/vectorlab/", "/photolab/", "/spritelab/", "/tilelab/"}


def test_forme():
    ids = [a["id"] for a in ANCRES]
    assert len(ids) == len(set(ids)), "identifiants en double"
    for a in ANCRES:
        assert re.fullmatch(r"[a-z0-9]+(\.[a-z0-9_]+)+", a["id"]), a["id"]
        assert a.get("fr") and a.get("en"), a["id"]
        assert a.get("selecteur") or a.get("reglages"), a["id"]


def test_ecrans_et_sections():
    for a in ANCRES:
        assert a.get("ecran") is None or a["ecran"] in A.VUES, a
        assert a.get("reglages") is None or a["reglages"] in A.SECTIONS_REGLAGES, a
        assert a.get("cadre") is None or a["cadre"] in LABS, a


def test_textes_presents_dans_l_application():
    for a in ANCRES:
        t = a.get("texte")
        if not t:
            continue
        for lang in ("fr", "en"):
            v = json.dumps(t[lang], ensure_ascii=False)[1:-1]
            if a.get("cadre"):
                lab = RACINE / "frontend" / a["cadre"].strip("/")
                src = "".join(p.read_text(encoding="utf-8", errors="replace")
                              for p in [lab / "index.html", *sorted((lab / "js").glob("*.js"))] if p.exists())
                assert t[lang] in src or v in src or v in DICO, (a["id"], lang)
            else:
                assert v in BUNDLE or v in DICO, (a["id"], lang)


def test_le_rail_complet():
    rail = {a["ecran"] for a in ANCRES if a["id"].startswith("rail.")}
    assert rail == set(A.VUES), set(A.VUES) - rail


def test_agent_md_ne_cite_que_l_existant():
    t = (RACINE / "docs" / "agent" / "AGENT.md").read_text(encoding="utf-8")
    ids = {a["id"] for a in ANCRES}
    for typ, cible in re.findall(r"\[(POINT|ALLER|GUIDE):([^\]]+)\]", t):
        if cible.startswith("<"):
            continue                                        # gabarit de la règle (« [POINT:<ancre>] »)
        assert {"POINT": cible in ids, "ALLER": cible in A.VUES, "GUIDE": cible in CHAPITRES}[typ], (typ, cible)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
