"""t534 (20/11/2026) — couche hébergée, pièce ⑤ : rappels OAuth YouTube et TikTok sur le nom public.

Plan docs/superpowers/plans/2026-11-20-couche-hebergee-vps.md. Sur le PC, Google et TikTok renvoient vers la boucle
locale (http://127.0.0.1:8765/api/oauth/…, client « Application de bureau » / « Desktop »). Sur le VPS, le navigateur
est ailleurs : le rappel devient https://<DEEPOTUS_HOSTNAME>/api/oauth/…, que Caddy transmet depuis 127.0.0.1, et les
guides de clés disent de créer un client « Application Web » avec CETTE adresse.

Chaque cas tourne dans un SOUS-PROCESSUS : le nom est lu à l'import de app.config.
Run (depuis backend/) : & $PY tests/test_oauth_rappel_t534.py
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap

import pytest

BACKEND = pathlib.Path(__file__).resolve().parents[1]


def _lancer(code: str, nom: str | None) -> dict:
    tmp = tempfile.mkdtemp(prefix="dzoauth_")
    env = {k: v for k, v in os.environ.items() if k != "DEEPOTUS_HOSTNAME"}
    env.update({"DEEPOTUS_DATA_DIR": tmp, "PYTHONIOENCODING": "utf-8",
                "DATABASE_URL": f"sqlite+aiosqlite:///{pathlib.Path(tmp, 't.db').as_posix()}"})
    if nom is not None:
        env["DEEPOTUS_HOSTNAME"] = nom
    entete = "import sys, json; sys.path.insert(0, %r)\n" % str(BACKEND)
    r = subprocess.run([sys.executable, "-c", entete + textwrap.dedent(code)], cwd=str(BACKEND), env=env,
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


_RAPPELS = """
from app.services import youtube_publisher as Y, tiktok_publisher as T
from app.services import guides_fournisseurs as G
from urllib.parse import urlsplit, parse_qs
y = parse_qs(urlsplit(Y.auth_url("etat-y")).query)["redirect_uri"][0]
print(json.dumps({"y": Y.redirect_uri(), "t": T.redirect_uri(), "y_auth": y,
                  "g_y": G.guide("YOUTUBE_CLIENT_ID"), "g_t": G.guide("TIKTOK_CLIENT_KEY"),
                  "tous_y": G.tous()["YOUTUBE_CLIENT_ID"]}))
"""


def test_poste_inchange_octet_pour_octet():
    v = _lancer(_RAPPELS, None)
    assert v["y"] == "http://127.0.0.1:8765/api/oauth/youtube/callback"
    assert v["t"] == "http://127.0.0.1:8765/api/oauth/tiktok/callback/"
    assert v["y_auth"] == v["y"]
    assert "https://" not in v["g_y"]["fr"] and "Application de bureau" in v["g_y"]["fr"]
    assert "Desktop" in v["g_t"]["en"]


def test_vps_rappels_https_sur_le_nom_public():
    v = _lancer(_RAPPELS, "studio.deepotus.tech")
    assert v["y"] == "https://studio.deepotus.tech/api/oauth/youtube/callback"
    assert v["t"] == "https://studio.deepotus.tech/api/oauth/tiktok/callback/"
    assert v["y_auth"] == v["y"], "l'URL d'autorisation porte le même rappel"


def test_vps_guides_disent_le_client_web_et_l_adresse():
    v = _lancer(_RAPPELS, "studio.deepotus.tech")
    for g, uri in ((v["g_y"], "https://studio.deepotus.tech/api/oauth/youtube/callback"),
                   (v["g_t"], "https://studio.deepotus.tech/api/oauth/tiktok/callback/")):
        assert uri in g["fr"] and uri in g["en"]
    assert "Application Web" in v["g_y"]["fr"] and "Web application" in v["g_y"]["en"]
    assert "« Web »" in v["g_t"]["fr"] and "« Web »" in v["g_t"]["en"]
    assert v["tous_y"] == v["g_y"], "tous() et guide() disent la même chose"


def test_un_nom_localhost_garde_la_boucle_locale():
    v = _lancer(_RAPPELS, "deepotus.localhost")
    assert v["y"] == "http://127.0.0.1:8765/api/oauth/youtube/callback"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
