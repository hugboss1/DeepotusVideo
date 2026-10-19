# -*- coding: utf-8 -*-
"""A2 (spec 2026-10-19-agent-aide-design.md) — le service de l'assistant : message système, balises, choix du moteur,
`demander` sous le plafond « aide », et les routes /api/agent.
Run : & $PY tests/test_agent_aide.py   (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile
import pytest

_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzagent_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.services import agent_aide as A                                    # noqa: E402


def test_systeme_contient_tout():
    s = A.systeme("montage", "fr", "Deepotus")
    assert "## Comment répondre" in s                       # AGENT.md
    assert "- quick : " in s and "- depannage : " in s       # chapitres
    assert "rail.montage" in s and "reglages.cles" in s      # ancres
    assert "écran ouvert : montage" in s and "espace de marque actif : Deepotus" in s


def test_systeme_anglais_et_prefixe_stable():
    fr, en = A.systeme("quick", "fr", ""), A.systeme("quick", "en", "")
    assert "- tour : Take a tour of the app" in en and "- tour : Faire le tour de l'application" in fr
    assert "langue : English" in en and "Take a tour" not in fr
    # le contexte est À LA FIN : deux écrans différents partagent tout le début (cache du préfixe)
    a, b = A.systeme("quick", "fr", "X"), A.systeme("montage", "fr", "Y")
    assert a.split("## Contexte")[0] == b.split("## Contexte")[0]
