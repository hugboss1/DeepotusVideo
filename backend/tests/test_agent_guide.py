# -*- coding: utf-8 -*-
"""A7 (spec 2026-10-19-agent-aide-design.md, lot A7) — le chapitre « Demander à Deepotus » du guide : déclaré dans
chapitres.json (famille Démarrer, juste après « tour »), écrit en FR puis EN au même squelette, ses scènes capturées
FR et EN (plan a7), le guide construit à jour, et l'assistant qui le connaît.
Run : & $PY tests/test_agent_guide.py   (depuis backend/)"""
import json, pathlib, re, subprocess, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
SRC = RACINE / "docs" / "guide" / "src"
CHAP = json.loads((SRC / "chapitres.json").read_text(encoding="utf-8"))["chapitres"]
SCENES = ["demander/tiroir", "demander/montrer", "demander/regarder", "demander/voix"]


def test_chapitre_declare():
    ids = [c["id"] for c in CHAP]
    c = next(c for c in CHAP if c["id"] == "demander")
    assert ids.index("demander") == ids.index("tour") + 1 and c["famille"] == "demarrer"
    assert c["fr"] == "Demander à Deepotus" and c["en"] == "Ask Deepotus" and c["lot"] == "A7"
    jv = json.loads((SRC / "jeveux.json").read_text(encoding="utf-8"))["entrees"]
    assert any(e["cible"] == "demander" for e in jv)


def _squelette(lang):
    h = (SRC / lang / "demander.html").read_text(encoding="utf-8")
    return h, re.findall(r'<h3>|<ol class="etapes">|data-scene="([^"]+)"|<aside class="(\w+)"', h)


def test_fr_et_en_meme_squelette():
    fr, sq_fr = _squelette("fr")
    en, sq_en = _squelette("en")
    assert sq_fr == sq_en and sq_fr
    for s in SCENES:
        assert f'data-scene="{s}"' in fr, s
    assert "F1" in fr and "<kbd>F1</kbd>" in en
    assert "plafond « aide »" in fr and "\"help\" cap" in en
    assert "Regarder l'écran" in fr and "Look at the screen" in en


def test_scenes_capturees():
    for s in SCENES:
        d = SRC / "scenes" / s
        assert (d / "scene.json").is_file(), s
        for lang in ("fr", "en"):
            assert list(d.glob(f"*.{lang}.webp")), (s, lang)


def test_guide_construit_a_jour():
    r = subprocess.run([sys.executable, str(RACINE / "scripts" / "guide" / "construire_guide.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", cwd=str(RACINE))
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-800:]
    assert 'id="demander"' in (RACINE / "docs" / "guide" / "fr.html").read_text(encoding="utf-8")


def test_l_assistant_connait_le_chapitre():
    t = (RACINE / "docs" / "agent" / "AGENT.md").read_text(encoding="utf-8")
    assert "[GUIDE:demander]" in t


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
