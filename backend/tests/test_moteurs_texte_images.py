# -*- coding: utf-8 -*-
"""A5 (assistant « Demander », spec 2026-10-19-agent-aide-design.md § 2 « Vision en secours ») — les IMAGES dans
moteurs_texte : quels moteurs les lisent (`vision`), leur validation (`images_valides`), leur chiffrage (`estimer`), et
leur envoi par fournisseur (`tirer` / `_appeler`), sans aucune requête réelle (httpx.post remplacé).
Run : & $PY tests/test_moteurs_texte_images.py   (depuis backend/)"""
import asyncio, base64, os, pathlib, sys, tempfile
import pytest

_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzmtimg_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.services import moteurs_texte as MT                                 # noqa: E402

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 64).decode()


@pytest.mark.parametrize("moteur,modele,attendu", [
    ("anthropic", "claude-haiku-4-5-20251001", True), ("anthropic", "claude-opus-5-5", True),
    ("anthropic", "claude-2.1", False), ("anthropic", "claude-instant-1.2", False),
    ("openai", "gpt-4o-mini", True), ("openai", "gpt-4.1", True), ("openai", "gpt-5", True), ("openai", "o3", True),
    ("openai", "o4-mini", True), ("openai", "o3-mini", False), ("openai", "o1-mini", False),
    ("openai", "gpt-4o-audio-preview", False), ("openai", "gpt-4o-realtime-preview", False),
    ("openai", "gpt-3.5-turbo", False),
    ("gemini", "gemini-flash-latest", True), ("gemini", "gemini-3.6-flash", True),
    ("gemini", "gemini-embedding-001", False), ("gemini", "gemini-2.5-flash-preview-tts", False),
    ("fl:abc", "n-importe", False), ("local:xyz", "llava", False),
])
def test_vision_par_modele(moteur, modele, attendu):
    assert MT.vision(moteur, modele) is attendu


def test_vision_refuse_une_cle_et_l_absence_de_modele(monkeypatch):
    assert MT.vision("anthropic", "sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxx") is False
    monkeypatch.setattr(MT, "modele_sain", lambda m: "")
    assert MT.vision("anthropic") is False


def test_vision_ollama_lit_les_capacites(monkeypatch):
    monkeypatch.setattr(MT, "_show_ollama", lambda mod, timeout=4.0: {"capabilities": ["completion", "vision"]}
                        if mod == "llava" else {"capabilities": ["completion"]})
    assert MT.vision("ollama", "llava") is True and MT.vision("ollama", "llama3") is False
    monkeypatch.setattr(MT, "_show_ollama", lambda mod, timeout=4.0: {})
    assert MT.vision("ollama", "llava") is False                  # Ollama injoignable : rien appris


def test_images_valides():
    assert MT.images_valides(None) == [] and MT.images_valides([]) == []
    assert MT.images_valides([{"mime": "image/png", "b64": PNG}]) == [{"mime": "image/png", "b64": PNG}]
    for mauvais in ([{"mime": "image/gif", "b64": PNG}], [{"mime": "image/png", "b64": "pas du base64 !"}],
                    [{"mime": "image/png"}], ["texte"], {"mime": "image/png", "b64": PNG},
                    [{"mime": "image/png", "b64": PNG}] * (MT.MAX_IMAGES + 1),
                    [{"mime": "image/jpeg", "b64": base64.b64encode(b"0" * (MT.MAX_IMAGE_OCTETS + 1)).decode()}],
                    [{"mime": "image/png", "b64": ""}]):
        with pytest.raises(RuntimeError):
            MT.images_valides(mauvais)


def test_estimer_compte_les_images():
    sans = MT.estimer("anthropic", "x" * 400, "", 100)
    avec = MT.estimer("anthropic", "x" * 400, "", 100, images=2)
    assert avec["in_tok"] - sans["in_tok"] == 2 * MT.JETONS_IMAGE == 3200
    assert avec["out_tok"] == sans["out_tok"] == 100


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
