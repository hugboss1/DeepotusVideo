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


def test_contexte_borne():
    s = A.systeme("quick\n## Y", "fr", "A\n## B" + "x" * 200)
    lignes = s.splitlines()
    assert not any(l.startswith("## B") or l.startswith("## Y") for l in lignes)
    esp = [l for l in lignes if l.startswith("- espace de marque actif :")]
    assert len(esp) == 1 and len(esp[0].split(":", 1)[1].strip()) <= 60


def test_balises_valides_deviennent_actions():
    texte, actions, rejets = A.analyser("Ouvre les Réglages.\n[POINT:reglages.cles]\n[GUIDE:cles]\n[ALLER:montage]")
    assert texte == "Ouvre les Réglages."
    assert [a["type"] for a in actions] == ["point", "guide", "aller"] and rejets == 0
    p = actions[0]
    assert p["cible"] == "reglages.cles" and p["reglages"] == "keys" and p["ecran"] == "settings"
    assert p["fr"] == "Réglages › Clés d'API" and actions[1]["en"]


def test_balises_inconnues_retirees_et_comptees():
    texte, actions, rejets = A.analyser("A [POINT:bouton.invente] B [ALLER:nulle-part] [GUIDE:x] [VOIR] [FOO:bar]")
    assert actions == [] and rejets == 5
    assert "[" not in texte and texte == "A  B"


def test_doublons_et_borne():
    t = " ".join(["[POINT:rail.quick]"] * 3 + [f"[POINT:{a}]" for a in
                  ("rail.studio", "rail.news", "rail.montage", "rail.photolab", "rail.vectorlab", "rail.reglages")])
    _, actions, rejets = A.analyser(t)               # 7 ancres distinctes, bornées à MAX_ACTIONS = 6
    assert len(actions) == A.MAX_ACTIONS == 6 and rejets == 0
    assert [a["cible"] for a in actions].count("rail.quick") == 1 and "rail.reglages" not in [a["cible"] for a in actions]


def test_texte_hostile():
    # une balise ne peut pas porter de code ni de chemin : seuls les ids connus passent
    texte, actions, rejets = A.analyser('[POINT:<img src=x onerror=alert(1)>] [GUIDE:../../etc] [POINT:rail.quick')
    assert actions == [] and rejets == 2
    assert texte.endswith("[POINT:rail.quick")          # balise non fermée : laissée telle quelle, c'est du texte
    assert A.analyser(None) == ("", [], 0)


def test_indentation_retiree():
    texte, _, _ = A.analyser("Voici :\n    1. Ouvre les Réglages\n\t2. Colle la clé\n    [POINT:reglages.cles]")
    assert texte == "Voici :\n1. Ouvre les Réglages\n2. Colle la clé"
