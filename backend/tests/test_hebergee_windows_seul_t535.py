"""t535 (20/11/2026) — couche hébergée, pièce ⑥ : les outils réservés à Windows se grisent sur le VPS.

Plan docs/superpowers/plans/2026-11-20-couche-hebergee-vps.md. Sur Linux, ces outils n'ont pas de sens ou pas de
binaire : Photolab (photocraft, build Windows seulement) et son app native, CLIP (roues win_amd64), l'ouverture d'un
.3mf dans le slicer (os.startfile, et un slicer sur un SERVEUR n'ouvre rien chez l'utilisateur), la pose dans Tabletop
Simulator (Documents de Windows). Chacun :
  - se dit indisponible dans son état (l'écran le grise) et dans GET /api/plateforme ;
  - refuse ses gestes par un 501 TRADUIT (plateforme.windows_seul), jamais un 500 ;
  - ne lance rien (aucun sous-processus).
Le scan OCR se dégrade déjà seul (503 + devis du secours Claude) ; Blender MCP et les logiciels 3D se disent
« absent » quand rien n'est installé. Le démarrage sous Linux est prouvé par le job « image » de image-vps.yml.

Sous Windows, ce banc SIMULE Linux (`plateforme.windows`).
Run (depuis backend/) : & $PY tests/test_hebergee_windows_seul_t535.py
"""
import os, pathlib, subprocess, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzwin535_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ.pop("PHOTOCRAFT_CLI", None)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from loguru import logger  # noqa: E402
logger.remove()
from app.main import app  # noqa: E402
from app.services import plateforme as PF  # noqa: E402

OUTILS = {"photolab", "clip", "slicer", "tts"}


@pytest.fixture
def linux(monkeypatch):
    monkeypatch.setattr(PF, "windows", lambda: False)
    lances = []
    vrai_run, vrai_popen = subprocess.run, subprocess.Popen
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: lances.append(a) or vrai_run(*a, **k))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: lances.append(a) or vrai_popen(*a, **k))
    yield lances
    assert lances == [], f"un outil Windows a lancé un processus sous Linux : {lances}"


@pytest.fixture
def windows(monkeypatch):
    monkeypatch.setattr(PF, "windows", lambda: True)


@pytest.fixture
def c():
    return TestClient(app)


def _refus(r, lang):
    assert r.status_code == 501, (r.status_code, r.text[:200])
    d = r.json()["detail"]
    assert ("Windows" in d), d
    return d


def test_etat_plateforme_linux(linux, c):
    fr = c.get("/api/plateforme", headers={"Accept-Language": "fr"}).json()
    en = c.get("/api/plateforme", headers={"Accept-Language": "en"}).json()
    assert fr["windows"] is False
    assert set(fr["indisponibles"]) == OUTILS
    for o in OUTILS:
        assert "Windows" in fr["indisponibles"][o] and "Windows" in en["indisponibles"][o]
        assert fr["indisponibles"][o] != en["indisponibles"][o]


def test_etat_plateforme_windows(windows, c):
    assert c.get("/api/plateforme").json() == {"windows": True, "indisponibles": {}}


def test_photolab_grise(linux, c):
    e = c.get("/api/photolab/etat").json()
    assert e["present"] is False and "Windows" in e["raison"]
    _refus(c.post("/api/photolab/nouveau", json={"width": 10, "height": 10}, headers={"Accept-Language": "fr"}), "fr")
    n = c.get("/api/photolab/natif/etat").json()
    assert n["present"] is False and "Windows" in n["raison"]
    _refus(c.post("/api/photolab/natif/ouvrir", json={}), "fr")


def test_photolab_moteur_linux_designe(linux, monkeypatch, c):
    """Un photocraft-cli désigné (PHOTOCRAFT_CLI, build Linux futur) n'est pas grisé."""
    from app.services import photolab_moteur as PM
    f = _tmp / "photocraft-cli"
    f.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setenv("PHOTOCRAFT_CLI", str(f))
    assert PM.chemin_cli() == f
    assert "photolab" not in c.get("/api/plateforme").json()["indisponibles"]


def test_clip_grise(linux, c):
    e = c.get("/api/library/clip/etat").json()
    assert e["disponible"] is False and "Windows" in e["raison"]
    fr = _refus(c.post("/api/library/clip/installer", headers={"Accept-Language": "fr"}), "fr")
    en = _refus(c.post("/api/library/clip/installer", headers={"Accept-Language": "en"}), "en")
    assert fr != en
    _refus(c.get("/api/library/recherche", params={"q": "chat", "moteur": "clip"}), "fr")


def test_slicer_grise(linux, c):
    _refus(c.post("/api/print3d/open", json={"dossier": "export-absent"}), "fr")
    from app.services import print3d as P3
    with pytest.raises(PF.ReserveWindows):
        P3.ouvrir_dans_slicer(_tmp / "x.3mf")


def test_tts_grise(linux, c):
    _refus(c.post("/api/cards/jeu-absent/edition/tts/poser"), "fr")


def test_windows_inchange(windows, c):
    assert c.get("/api/library/clip/etat").json()["disponible"] is True
    assert c.post("/api/print3d/open", json={"dossier": "export-absent"}).status_code == 404
    assert c.post("/api/cards/jeu-absent/edition/tts/poser").status_code not in (500, 501)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
