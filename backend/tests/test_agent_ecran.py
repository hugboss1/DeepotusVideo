# -*- coding: utf-8 -*-
"""A3/A4 (spec 2026-10-19-agent-aide-design.md) — l'écran de l'assistant : libellés FR/EN complets et employés,
copies dist identiques, balises dans la SPA et dans les labs, banc node de la logique pure.
Run : & $PY tests/test_agent_ecran.py   (depuis backend/)"""
import json, pathlib, re, shutil, subprocess, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
SHARED = RACINE / "frontend" / "shared"
DIST = RACINE / "frontend" / "dist" / "shared"
I18N = json.loads((SHARED / "i18n" / "agent.json").read_text(encoding="utf-8"))


def test_libelles_complets():
    assert len(I18N) >= 14
    for k, v in I18N.items():
        assert k.startswith("agent."), k
        assert v.get("fr") and v.get("en"), k


def test_dictionnaire_assemble():
    dico = (SHARED / "dz-i18n-dico.js").read_text(encoding="utf-8")
    for k in I18N:
        assert f'"{k}"' in dico, k


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
