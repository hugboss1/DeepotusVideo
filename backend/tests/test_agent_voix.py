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


from app.services import agent_aide as A                                    # noqa: E402
from app.services import plafonds as PLAF                                   # noqa: E402
from app.services import voice_providers as VP                              # noqa: E402
from app.services import elevenlabs_service as ES                           # noqa: E402
from fastapi.testclient import TestClient                                   # noqa: E402


class _FausseVoix:
    appels = []

    def generate_long(self, text, output_path, language="EN", provider=None, **kw):
        _FausseVoix.appels.append((text, language, provider))
        pathlib.Path(output_path).write_bytes(b"ID3faux-mp3")


def _preparer(monkeypatch, fournisseur):
    _FausseVoix.appels = []
    gardes = []

    async def verifier(op, categorie, ref=None):
        gardes.append((op, categorie))
    monkeypatch.setattr(VP, "resolve_provider", lambda requested=None: fournisseur)
    monkeypatch.setattr(ES, "VoiceoverService", _FausseVoix)
    monkeypatch.setattr(PLAF, "verifier", verifier)
    from app.main import app
    return TestClient(app), gardes


def test_lire_voicebox_gratuit_et_cache(monkeypatch):
    c, gardes = _preparer(monkeypatch, "voicebox")
    r = c.post("/api/agent/lire", json={"texte": "Ouvre les Réglages.\n[POINT:reglages.cles]", "lang": "fr"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg" and r.content == b"ID3faux-mp3"
    assert _FausseVoix.appels == [("Ouvre les Réglages.", "fr", "voicebox")] and gardes == []
    r2 = c.post("/api/agent/lire", json={"texte": "Ouvre les Réglages.", "lang": "fr"})
    assert r2.status_code == 200 and len(_FausseVoix.appels) == 1          # relu depuis le cache : rien de dépensé


def test_lire_elevenlabs_sous_le_plafond_aide(monkeypatch):
    c, gardes = _preparer(monkeypatch, "elevenlabs")
    r = c.post("/api/agent/lire", json={"texte": "Hello there.", "lang": "en"})
    assert r.status_code == 200
    assert gardes == [({"kind": "elevenlabs", "chars": len("Hello there.")}, "aide")]


def test_lire_refus(monkeypatch):
    c, _ = _preparer(monkeypatch, "")
    assert c.post("/api/agent/lire", json={"texte": "x"}).status_code == 503
    c, _ = _preparer(monkeypatch, "voicebox")
    assert c.post("/api/agent/lire", json={"texte": "  [VOIR] "}).status_code == 400
    assert c.post("/api/agent/lire", json={"texte": 5}).status_code == 400


def test_texte_a_lire_borne():
    assert len(A.texte_a_lire("mot " * 2000)) == A.MAX_LECTURE
    assert A.texte_a_lire("a\n\n[GUIDE:cles]  b") == "a b"


def test_elaguer_garde_les_plus_recents():
    d = A.dossier_lectures()
    for i in range(A.GARDER_LECTURES + 5):
        p = d / f"f{i:03d}.mp3"
        p.write_bytes(b"x")
        os.utime(p, (1_000_000 + i, 1_000_000 + i))
    A.elaguer_lectures()
    restes = sorted(p.name for p in d.glob("*.mp3"))
    assert len(restes) == A.GARDER_LECTURES and "f000.mp3" not in restes


def test_etat_voix(monkeypatch):
    monkeypatch.setattr(VP, "resolve_provider", lambda requested=None: "voicebox")
    assert A.etat_voix() == {"fournisseur": "voicebox", "nom": "Voicebox", "cout": "gratuit"}
    monkeypatch.setattr(VP, "resolve_provider", lambda requested=None: "")
    assert A.etat_voix() == {"fournisseur": "", "nom": "", "cout": ""}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
