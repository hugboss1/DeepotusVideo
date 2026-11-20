"""t530 (20/11/2026) — couche hébergée, pièce ① : le nom d'hôte public DEEPOTUS_HOSTNAME.

Plan docs/superpowers/plans/2026-11-20-couche-hebergee-vps.md. Sur le VPS, le navigateur ouvre
https://studio.deepotus.tech : Caddy transmet l'en-tête Host et l'Origin du domaine. Les gardes qui ne
connaissaient que deepotus.localhost (CSRF de main.py, écran de Blender et du MCP, WebSocket du direct)
acceptent aussi ce nom ; l'adresse cliente, elle, reste exigée locale (Caddy parle depuis 127.0.0.1).

Chaque cas tourne dans un SOUS-PROCESSUS : le nom est lu à l'import de app.config.
Run (depuis backend/) : & $PY tests/test_hebergee_hote_t530.py
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
import json
import pathlib
import subprocess
import sys
import tempfile
import textwrap

import pytest

BACKEND = pathlib.Path(__file__).resolve().parents[1]


def _lancer(code: str, nom: str | None) -> dict:
    """Exécute `code` (qui affiche un JSON en dernière ligne) avec DEEPOTUS_HOSTNAME = nom."""
    tmp = tempfile.mkdtemp(prefix="dzhote_")
    env = {k: v for k, v in os.environ.items() if k != "DEEPOTUS_HOSTNAME"}
    env.update({"DEEPOTUS_DATA_DIR": tmp,
                "DATABASE_URL": f"sqlite+aiosqlite:///{pathlib.Path(tmp, 't.db').as_posix()}",
                "PYTHONIOENCODING": "utf-8"})
    if nom is not None:
        env["DEEPOTUS_HOSTNAME"] = nom
    entete = "import sys, json; sys.path.insert(0, %r)\n" % str(BACKEND)
    r = subprocess.run([sys.executable, "-c", entete + textwrap.dedent(code)], cwd=str(BACKEND), env=env,
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


import os  # noqa: E402

_NOMS = """
from app import config
print(json.dumps({"nom": config.APP_HOSTNAME, "local": config.APP_HOSTNAME_LOCAL,
                  "ecran": sorted(config.NOMS_ECRAN), "url": config.app_url(8765)}))
"""


def test_defaut_inchange():
    v = _lancer(_NOMS, None)
    assert v == {"nom": "deepotus.localhost", "local": "deepotus.localhost",
                 "ecran": ["deepotus.localhost"], "url": "http://deepotus.localhost:8765"}


@pytest.mark.parametrize("brut", ["studio.deepotus.tech", " Studio.Deepotus.TECH ", "https://studio.deepotus.tech/",
                                  "studio.deepotus.tech:443"])
def test_nom_public_nettoye(brut):
    v = _lancer(_NOMS, brut)
    assert v["nom"] == "studio.deepotus.tech"
    assert v["ecran"] == ["deepotus.localhost", "studio.deepotus.tech"]
    assert v["url"] == "https://studio.deepotus.tech"


@pytest.mark.parametrize("brut", ["", "   ", "evil.com/../x", "a b.com", "ex*ample.com", "-moche.com", "x" * 300])
def test_nom_invalide_repli_local(brut):
    v = _lancer(_NOMS, brut)
    assert v["nom"] == "deepotus.localhost"
    assert v["ecran"] == ["deepotus.localhost"]


_CSRF = """
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
res = {}
for o in ("https://studio.deepotus.tech", "http://deepotus.localhost:8765", "https://evil.example.com",
          "https://studio.deepotus.tech.evil.com"):
    r = c.post("/api/settings/keys", json={}, headers={"Origin": o})
    res[o] = not (r.status_code == 403 and "Cross-origin" in r.text)
print(json.dumps(res))
"""


def test_garde_csrf_accepte_le_nom_public():
    v = _lancer(_CSRF, "studio.deepotus.tech")
    assert v == {"https://studio.deepotus.tech": True, "http://deepotus.localhost:8765": True,
                 "https://evil.example.com": False, "https://studio.deepotus.tech.evil.com": False}


def test_garde_csrf_refuse_le_domaine_sans_la_variable():
    v = _lancer(_CSRF, None)
    assert v["https://studio.deepotus.tech"] is False
    assert v["http://deepotus.localhost:8765"] is True


_ECRAN = """
from fastapi import HTTPException
from starlette.requests import Request
from app.api import blender_routes, mcp_routes
def req(origin):
    return Request({"type": "http", "method": "POST", "path": "/", "query_string": b"",
                    "headers": [(b"origin", origin.encode())], "client": ("127.0.0.1", 1)})
res = {}
for o in ("https://studio.deepotus.tech", "https://evil.example.com"):
    for nom, mod in (("blender", blender_routes), ("mcp", mcp_routes)):
        try:
            mod._ecran(req(o)); res[nom + " " + o] = True
        except HTTPException:
            res[nom + " " + o] = False
print(json.dumps(res))
"""


def test_gardes_ecran_blender_et_mcp():
    v = _lancer(_ECRAN, "studio.deepotus.tech")
    assert v == {"blender https://studio.deepotus.tech": True, "mcp https://studio.deepotus.tech": True,
                 "blender https://evil.example.com": False, "mcp https://evil.example.com": False}


_WS = """
from app.api.live_routes import _origine_sure
class WS:
    def __init__(self, client, host, origin):
        self.client = type("C", (), {"host": client})()
        self.headers = {"host": host} if origin is None else {"host": host, "origin": origin}
cas = {
  "public": ("127.0.0.1", "studio.deepotus.tech", "https://studio.deepotus.tech"),
  "public_port": ("127.0.0.1", "studio.deepotus.tech:443", "https://studio.deepotus.tech:443"),
  "public_sans_origin": ("127.0.0.1", "studio.deepotus.tech", None),
  "local": ("127.0.0.1", "127.0.0.1:8765", "http://127.0.0.1:8765"),
  "nomme_local": ("127.0.0.1", "deepotus.localhost:8765", "http://deepotus.localhost:8765"),
  "etranger": ("127.0.0.1", "mechant.example", "https://mechant.example"),
  "origin_differente": ("127.0.0.1", "studio.deepotus.tech", "https://mechant.example"),
  "client_distant": ("203.0.113.9", "studio.deepotus.tech", "https://studio.deepotus.tech"),
}
print(json.dumps({k: _origine_sure(WS(*v)) for k, v in cas.items()}))
"""


def test_websocket_du_direct_accepte_le_nom_public():
    v = _lancer(_WS, "studio.deepotus.tech")
    assert v == {"public": True, "public_port": True, "public_sans_origin": True, "local": True,
                 "nomme_local": True, "etranger": False, "origin_differente": False, "client_distant": False}


def test_websocket_du_direct_sans_la_variable():
    v = _lancer(_WS, None)
    assert v["public"] is False and v["local"] is True and v["etranger"] is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
