# -*- coding: utf-8 -*-
"""A6 (spec 2026-10-19-agent-aide-design.md, lot A6) — la voix de l'assistant : dictée de la question par la couche
des champs IA (/shared/dz-champ-ia.js, sans duplication), lecture de la réponse par la voix des Réglages
(POST /api/agent/lire, cache à part, plafond « aide » pour ElevenLabs seulement).
Run : & $PY tests/test_agent_voix.py   (depuis backend/)"""
import asyncio, json, os, pathlib, sys, tempfile
import pytest

_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzagentvoix_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
RACINE = pathlib.Path(__file__).resolve().parents[2]
SHARED = RACINE / "frontend" / "shared"
DIST = RACINE / "frontend" / "dist" / "shared"


def test_dictee_ouverte_aux_autres_champs():
    src = (SHARED / "dz-champ-ia.js").read_text(encoding="utf-8")
    assert "basculer: basculerDictee" in src, "DzChampIA.dictee.basculer(el) : la dictée pour un champ non marqué"
    assert '"dzia-dictee"' in src and "function signalerDictee(el)" in src
    r = src[src.index("function rafraichirMicro(el) {"):]
    assert r.index("signalerDictee(el);") < r.index("if (!b) return;"), "signalé AVANT le retour des champs sans micro"
    assert 'var VERSION = "1.3.0";' in src, "version inchangée (banc test_champ_ia)"
    assert (SHARED / "dz-champ-ia.js").read_bytes() == (DIST / "dz-champ-ia.js").read_bytes()


I18N = json.loads((SHARED / "i18n" / "agent.json").read_text(encoding="utf-8"))


def test_micro_du_tiroir():
    src = (SHARED / "dz-agent.js").read_text(encoding="utf-8")
    assert "DzChampIA.dictee" in src and ".basculer(saisie)" in src
    assert 'saisie.addEventListener("dzia-dictee"' in src
    assert 'glyphe("dz-media-dicter")' in src and '"dz-media-arret"' in src
    assert "dicteeEnCours()" in src, "Échap pendant la dictée l'arrête sans fermer le tiroir"
    for k in ("agent.voix.dicter", "agent.voix.arreter", "agent.voix.indisponible"):
        assert k in I18N and I18N[k]["fr"] and I18N[k]["en"], k


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
