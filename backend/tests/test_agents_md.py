# -*- coding: utf-8 -*-
"""A0 (spec 2026-10-19-agent-aide-design.md) — AGENTS.md à la racine : les sections attendues, et chaque chemin cité
entre accents graves dans « Fichiers clés » existe. CLAUDE.md y renvoie.
Run : & $PY tests/test_agents_md.py   (depuis backend/)"""
import pathlib, re, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
SECTIONS = ["## Vue d'ensemble", "## Architecture", "## Fichiers clés", "## Lancer et tester", "## Conventions",
            "## Git", "## Tenir ce fichier à jour"]


def _texte():
    return (RACINE / "AGENTS.md").read_text(encoding="utf-8")


def test_sections():
    t = _texte()
    manquantes = [s for s in SECTIONS if s not in t]
    assert not manquantes, manquantes


def test_chemins_cites_existent():
    t = _texte()
    bloc = t.split("## Fichiers clés", 1)[1].split("\n## ", 1)[0]
    chemins = [c for c in re.findall(r"`([^`]+)`", bloc) if "/" in c and " " not in c and "*" not in c]
    assert len(chemins) >= 12, chemins
    absents = [c for c in chemins if not (RACINE / c.rstrip("/")).exists()]
    assert not absents, absents


def test_claude_md_renvoie():
    assert "AGENTS.md" in (RACINE / "CLAUDE.md").read_text(encoding="utf-8")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
