"""L'origine nommée deepotus.localhost (finitions UI, 20/09/2026).

Les navigateurs résolvent *.localhost en boucle locale sans fichier hosts
(RFC 6761) : l'application s'OUVRE sous http://deepotus.localhost:8765 tandis
que le serveur écoute toujours sur 127.0.0.1. Ce banc épingle : la constante
et l'URL, le garde CSRF (Origin), le garde SSRF (.localhost = privé), le
garde des Réglages (client TCP = boucle locale, quel que soit le nom), le
lanceur et les titres des pages standalone.

Run : python -m pytest backend/tests/test_origine_nommee.py -q
"""
import pathlib
import re

import pytest
from fastapi.testclient import TestClient

RACINE = pathlib.Path(__file__).resolve().parents[2]


def test_app_hostname_et_url():
    from app import config
    assert config.APP_HOSTNAME == "deepotus.localhost"
    assert config.app_url(8765) == "http://deepotus.localhost:8765"
    assert config.app_url() == f"http://deepotus.localhost:{config.settings.PORT}"


def test_deepotus_localhost_est_prive():
    from app.api.routes import _is_private_host
    assert _is_private_host("deepotus.localhost") is True
    assert _is_private_host("evil.localhost") is True
    assert _is_private_host("deepotus.example.com") is False


@pytest.mark.parametrize("origin,ok", [
    ("http://deepotus.localhost:8765", True),
    ("http://127.0.0.1:8765", True),
    ("http://localhost:8765", True),
    ("http://evil.example.com", False),
    ("http://deepotus.localhost.example.com", False),
])
def test_garde_csrf_accepte_l_origine_nommee(origin, ok):
    from app.main import app, _ALLOWED_ORIGIN_HOSTS
    assert "deepotus.localhost" in _ALLOWED_ORIGIN_HOSTS
    # SANS lifespan (pas de `with`) : le garde est un middleware et la route
    # ne lit que le .env — le lifespan, lui, réchauffe HeyGen (réseau) et
    # bloquait le banc (mesuré 20/09 : > 7 min sans sortie).
    c = TestClient(app)
    if True:
        r = c.post("/api/settings/keys", json={}, headers={"Origin": origin})
        # 403 « Cross-origin request blocked » = refusé par le garde ;
        # tout autre code = le garde a laissé passer.
        bloque = r.status_code == 403 and "Cross-origin" in r.text
        assert bloque is (not ok), (r.status_code, r.text[:120])


def test_settings_restent_accessibles_depuis_l_hote_nomme():
    from app.main import app
    c = TestClient(app, base_url="http://deepotus.localhost:8765")   # sans lifespan
    if True:
        r = c.get("/api/settings/keys", headers={"Host": "deepotus.localhost:8765"})
        assert r.status_code == 200


def test_lanceur_ouvre_l_url_nommee_et_sonde_l_ip():
    vbs = (RACINE / "scripts" / "launch-silent.vbs").read_text(encoding="utf-8", errors="replace")
    assert 'urlApp = "http://deepotus.localhost:8765"' in vbs
    assert "shell.Run urlApp, 1, False" in vbs
    assert 'url = "http://127.0.0.1:8765"' in vbs           # la sonde /api/health reste sur l'IP
    assert "shell.Run url, 1, False" not in vbs


def test_titres_des_pages_standalone():
    racine = RACINE / "frontend"
    for outil in ("vectorlab", "spritelab", "tilelab", "atelier", "cardforge",
                  "etabli", "materialforge", "studio3d"):
        html = (racine / outil / "index.html").read_text(encoding="utf-8")
        titre = re.search(r"<title>(.*?)</title>", html).group(1)
        assert titre.startswith("Deepotus — "), (outil, titre)


def test_guide_pointe_sur_l_url_nommee():
    for lang in ("fr", "en"):
        html = (RACINE / "docs" / "guide" / f"{lang}.html").read_text(encoding="utf-8")
        assert "http://127.0.0.1:8765" not in html, lang
        assert "http://deepotus.localhost:8765" in html, lang
