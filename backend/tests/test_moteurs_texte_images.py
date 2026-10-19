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


def test_images_pas_une_liste_message_distinct():
    with pytest.raises(RuntimeError, match="liste attendue"):
        MT.images_valides({"mime": "image/png", "b64": PNG})
    with pytest.raises(RuntimeError, match="au plus"):
        MT.images_valides([{"mime": "image/png", "b64": PNG}] * (MT.MAX_IMAGES + 1))


def test_estimer_compte_les_images():
    sans = MT.estimer("anthropic", "x" * 400, "", 100)
    avec = MT.estimer("anthropic", "x" * 400, "", 100, images=2)
    assert avec["in_tok"] - sans["in_tok"] == 2 * MT.JETONS_IMAGE == 3200
    assert avec["out_tok"] == sans["out_tok"] == 100


class _Rep:
    def __init__(self, obj):
        self.status_code, self._obj, self.text = 200, obj, ""

    def json(self):
        return self._obj


REPONSES = {"anthropic": {"content": [{"type": "text", "text": "ok"}]},
            "openai": {"choices": [{"message": {"content": "ok"}}]},
            "gemini": {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]},
            "ollama": {"response": "ok"}}


def _espion(monkeypatch, moteur):
    vu = []

    def post(url, **kw):
        vu.append((url, kw.get("json")))
        return _Rep(REPONSES[moteur])
    monkeypatch.setattr(MT.httpx, "post", post)
    from app.services import gemini_llm
    monkeypatch.setattr(gemini_llm, "_headers", lambda: {})
    return vu


IMG = [{"mime": "image/png", "b64": PNG}]


def test_anthropic_image_avant_le_texte(monkeypatch):
    vu = _espion(monkeypatch, "anthropic")
    assert MT.tirer("anthropic", "claude-haiku-4-5-20251001", "où ?", "sys", 50, images=IMG) == "ok"
    c = vu[0][1]["messages"][0]["content"]
    assert c[0] == {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": PNG}}
    assert c[-1] == {"type": "text", "text": "où ?"}


def test_openai_image_en_url_data(monkeypatch):
    vu = _espion(monkeypatch, "openai")
    MT.tirer("openai", "gpt-4o-mini", "où ?", "sys", 50, images=IMG)
    c = vu[0][1]["messages"][-1]["content"]
    assert c[0] == {"type": "text", "text": "où ?"}
    assert c[1]["type"] == "image_url" and c[1]["image_url"]["url"] == f"data:image/png;base64,{PNG}"
    assert c[1]["image_url"]["detail"] == "high"


def test_gemini_image_inline(monkeypatch):
    vu = _espion(monkeypatch, "gemini")
    MT.tirer("gemini", "gemini-flash-latest", "où ?", "sys", 50, images=IMG)
    parts = vu[0][1]["contents"][0]["parts"]
    assert parts[0] == {"inlineData": {"mimeType": "image/png", "data": PNG}} and parts[-1] == {"text": "où ?"}


def test_ollama_images_brutes(monkeypatch):
    vu = _espion(monkeypatch, "ollama")
    monkeypatch.setattr(MT, "_show_ollama", lambda mod, timeout=4.0: {"capabilities": ["vision"]})
    MT.tirer("ollama", "llava", "où ?", "sys", 50, images=IMG)
    assert vu[0][1]["images"] == [PNG] and vu[0][1]["prompt"] == "où ?"


def test_sans_image_rien_ne_change(monkeypatch):
    vu = _espion(monkeypatch, "anthropic")
    MT.tirer("anthropic", "claude-haiku-4-5-20251001", "où ?", "sys", 50)
    assert vu[0][1]["messages"][0]["content"] == "où ?"
    vu = _espion(monkeypatch, "ollama")
    MT.tirer("ollama", "llama3", "où ?", "sys", 50)
    assert "images" not in vu[0][1]


def test_modele_aveugle_refuse_sans_requete(monkeypatch):
    vu = _espion(monkeypatch, "openai")
    with pytest.raises(RuntimeError):
        MT.tirer("openai", "gpt-3.5-turbo", "où ?", "sys", 50, images=IMG)
    with pytest.raises(RuntimeError):
        MT.tirer("openai", "gpt-4o-mini", "où ?", "sys", 50, images=[{"mime": "image/gif", "b64": PNG}])
    assert vu == []


def test_tirer_garde_chiffre_l_image_et_refuse_avant_le_plafond(monkeypatch):
    from app.services import plafonds as PLAF
    vu_ops = []

    async def verifier(op, categorie, ref=None):
        vu_ops.append(op)
    monkeypatch.setattr(PLAF, "verifier", verifier)
    monkeypatch.setattr(MT, "configure", lambda m: True)
    vu = _espion(monkeypatch, "anthropic")
    asyncio.run(MT.tirer_garde("anthropic", "claude-haiku-4-5-20251001", "p", "s", 50, categorie="aide", images=IMG))
    assert vu_ops[0]["in_tok"] >= MT.JETONS_IMAGE and vu
    vu_ops.clear()
    with pytest.raises(RuntimeError):
        asyncio.run(MT.tirer_garde("openai", "gpt-3.5-turbo", "p", "s", 50, categorie="aide", images=IMG))
    assert vu_ops == []                                           # refusé AVANT la garde : aucun 402 trompeur


@pytest.mark.parametrize("moteur,modele,attendu", [
    ("openai", "gpt-4o-mini", 36835), ("openai", "gpt-4o-mini-2024-07-18", 36835),
    ("openai", "gpt-4.1-mini", 2500), ("openai", "gpt-5-mini", 2500), ("openai", "gpt-5-nano", 2500),
    ("openai", "o4-mini", 2500),
    ("openai", "gpt-4o", 1600), ("openai", "gpt-5", 1600), ("anthropic", "claude-opus-5-5", 1600),
    ("gemini", "gemini-flash-latest", 1600),
])
def test_jetons_image_par_modele(moteur, modele, attendu):
    assert MT.jetons_image(moteur, modele) == attendu


def test_estimer_utilise_le_modele_de_l_appel_ou_celui_des_reglages(monkeypatch):
    sans = MT.estimer("openai", "x" * 400, "", 100, modele="gpt-4o-mini")
    avec = MT.estimer("openai", "x" * 400, "", 100, modele="gpt-4o-mini", images=1)
    assert avec["in_tok"] - sans["in_tok"] == 36835
    monkeypatch.setattr(MT, "modele_sain", lambda m: "gpt-4o-mini")
    d = MT.estimer("openai", "x" * 400, "", 100, images=1)
    assert d["in_tok"] - sans["in_tok"] == 36835


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
