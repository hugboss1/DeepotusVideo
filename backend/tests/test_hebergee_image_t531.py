"""t531 (20/11/2026) — couche hébergée, pièce ② : l'image et le déploiement du VPS.

Plan docs/superpowers/plans/2026-11-20-couche-hebergee-vps.md. Ce banc LIT les fichiers (le PC n'a pas Docker ; la
construction réelle est faite par .github/workflows/image-vps.yml) et épingle les invariants de sécurité :
  - uvicorn écoute 127.0.0.1:8765, sans --reload, avec --no-proxy-headers (sinon X-Forwarded-For remplace l'adresse
    cliente et les gardes locales refusent tout, ou pire la croient) ;
  - deepotus et caddy en réseau de l'hôte (un port publié arrive de la passerelle du pont, jamais de 127.0.0.1) ;
  - 8765 n'est publié nulle part ; le dépôt est monté en lecture seule ; SFTP sur 2222 par clé seulement ;
  - le Caddyfile exige un mot de passe et retire X-Forwarded-For et X-Real-IP ;
  - chaque paquet importé par app/ au démarrage est dans requirements.txt.
Run (depuis backend/) : & $PY tests/test_hebergee_image_t531.py
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
import ast
import pathlib
import re
import sys

import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
VPS = RACINE / "deploiement" / "vps"


def _lire(p: pathlib.Path) -> str:
    assert p.is_file(), f"absent : {p.relative_to(RACINE)}"
    return p.read_text(encoding="utf-8")


def _cmd_uvicorn(dockerfile: str) -> list[str]:
    m = re.search(r'^CMD\s+(\[.*\])\s*$', dockerfile, re.M)
    assert m, "CMD en forme JSON attendue"
    return ast.literal_eval(m.group(1))


def test_dockerfile_base_et_outils():
    d = _lire(RACINE / "Dockerfile")
    assert re.search(r"^FROM python:3\.13-slim", d, re.M)
    for paquet in ("ffmpeg", "chromium"):
        assert re.search(rf"apt-get install[^\n]*(\\\n[^\n]*)*\b{paquet}\b", d), paquet
    assert "requirements.txt" in d
    assert re.search(r"^USER\s+(?!root)\w+", d, re.M), "le conteneur ne tourne pas en root"
    env = " ".join(re.findall(r"^ENV\s+((?:[^\n]*\\\n)*[^\n]*)", d, re.M))
    assert "DEEPOTUS_DATA_DIR=/data" in env
    assert "DEEPOTUS_NAVIGATEUR=/usr/local/bin/chromium-conteneur" in env
    assert "HEALTHCHECK" in d and "/api/health" in d


def test_uvicorn_boucle_locale_sans_reload_sans_entetes_de_proxy():
    cmd = _cmd_uvicorn(_lire(RACINE / "Dockerfile"))
    assert cmd[:2] == ["uvicorn", "app.main:app"] or cmd[:4] == ["python", "-m", "uvicorn", "app.main:app"]
    assert cmd[cmd.index("--host") + 1] == "127.0.0.1"
    assert cmd[cmd.index("--port") + 1] == "8765"
    assert "--no-proxy-headers" in cmd
    assert not any(a.startswith("--reload") for a in cmd)
    assert "0.0.0.0" not in " ".join(cmd)


def test_lanceur_chromium_du_conteneur():
    s = _lire(RACINE / "deploiement" / "vps" / "chromium-conteneur")
    assert s.startswith("#!/bin/sh")
    assert "--no-sandbox" in s and '"$@"' in s
    assert "\r\n" not in s, "fins de ligne LF exigées (script shell)"
    assert "chromium-conteneur" in _lire(RACINE / "Dockerfile")


def test_dockerignore_ecarte_donnees_et_secrets():
    ig = _lire(RACINE / ".dockerignore")
    for motif in (".git", "**/__pycache__", "**/.env", "**/*.db", "installer", "docs/superpowers", "frontend/src"):
        assert motif in ig.split(), motif
    for garde in ("frontend", "frontend/dist", "docs", "docs/guide", "docs/agent", "assets"):
        assert garde not in ig.split(), garde


def test_image_porte_les_labs_le_guide_et_la_connaissance():
    """Le backend sert /atelier, /vectorlab, /photolab… depuis frontend/<lab>, /guide depuis docs/guide, et lit
    docs/agent (assistant, fiches modèle) : copier frontend/dist seul les ferait disparaître sans erreur."""
    d = _lire(RACINE / "Dockerfile")
    for src in ("frontend", "docs/guide", "docs/agent", "assets"):
        assert re.search(rf"^COPY {re.escape(src)} {re.escape(src)}$", d, re.M), src


def _service(compose: str, nom: str) -> str:
    m = re.search(rf"^  {nom}:\n((?:    .*\n|\s*\n)+)", compose, re.M)
    assert m, f"service {nom} absent"
    return m.group(1)


def test_compose_reseau_hote_et_ports():
    c = _lire(VPS / "docker-compose.yml")
    dz, caddy, sftp = _service(c, "deepotus"), _service(c, "caddy"), _service(c, "sftp")
    assert "network_mode: host" in dz and "network_mode: host" in caddy
    sans_commentaires = "\n".join(l.split("#", 1)[0] for l in c.splitlines())
    assert "8765" not in sans_commentaires, "8765 ne se publie jamais"
    assert "ports:" not in dz
    assert re.search(r'"2222:22"', sftp)
    assert "restart: unless-stopped" in dz


def test_compose_volumes():
    c = _lire(VPS / "docker-compose.yml")
    dz, sftp = _service(c, "deepotus"), _service(c, "sftp")
    assert "/srv/deepotus/data:/data" in dz
    assert re.search(r"/srv/deepotus/depot:/depot:ro\b", dz), "le dépôt est en lecture seule pour Deepotus"
    assert "/srv/deepotus/depot:/home/depot/upload" in sftp
    assert re.search(r"command:\s*depot::1000", sftp), "SFTP sans mot de passe : clé seulement"
    assert ".ssh/keys/" in sftp and "ssh_host_ed25519_key" in sftp


def test_caddyfile_mot_de_passe_et_entetes_retires():
    cf = _lire(VPS / "Caddyfile.exemple")
    assert "basic_auth" in cf
    assert "reverse_proxy 127.0.0.1:8765" in cf
    assert "header_up -X-Forwarded-For" in cf and "header_up -X-Real-IP" in cf
    assert re.search(r"max_size\s+8GB", cf)
    assert "read_timeout 30m" in cf and "write_timeout 30m" in cf
    assert "{$DEEPOTUS_HOSTNAME}" in cf


def test_env_exemple_sans_secret():
    e = _lire(VPS / ".env.exemple")
    assert re.search(r"^DEEPOTUS_HOSTNAME=studio\.deepotus\.tech$", e, re.M)
    assert not re.search(r"(KEY|TOKEN|SECRET)\s*=\s*\S", e)


def test_readme_pas_a_pas():
    r = _lire(VPS / "README.md")
    for etape in ("ufw", "2222", "fail2ban", "studio.deepotus.tech", "caddy hash-password", "docker compose up",
                  "chown", "ssh-keygen"):
        assert etape in r, etape


def test_workflow_construit_et_sonde():
    w = _lire(RACINE / ".github" / "workflows" / "image-vps.yml")
    assert "docker build" in w and "/api/health" in w
    assert "Origin: https://studio.deepotus.tech" in w
    assert "push" not in re.findall(r"docker (\w+)", w), "rien n'est publié"
    assert "tests/test_*_t53[0-5].py" in w, "les bancs t530-t535 tournent sous Linux (coffre 0600, askpass.sh…)"
    for lab in ("/atelier/", "/vectorlab/", "/photolab/", "/guide/"):
        assert lab in w, lab


# Paquets importés par app/ qui n'ont PAS à être dans requirements.txt : la stdlib, Blender (bpy), et les dépendances
# facultatives installées à la demande (CLIP : numpy/onnxruntime/tokenizers ; détourage : rembg) — t535 les grise.
_FACULTATIFS = {"bpy", "numpy", "onnxruntime", "tokenizers", "rembg"}
# Module -> distribution quand les noms diffèrent, et dépendances transitives sûres.
_DISTRIB = {"PIL": "pillow", "docx": "python-docx", "dotenv": "python-dotenv", "pydantic_settings": "pydantic-settings",
            "fal_client": "fal-client", "yaml": "pyyaml"}
_TRANSITIFS = {"anyio": "fastapi", "starlette": "fastapi", "certifi": "httpx", "msgpack": "fal-client",
               "websockets": "uvicorn"}


def test_requirements_couvrent_les_imports():
    req = {re.split(r"[<>=\[ ;]", l.strip(), maxsplit=1)[0].lower()
           for l in _lire(RACINE / "backend" / "requirements.txt").splitlines() if l.strip() and not l.startswith("#")}
    manque = {}
    for f in (RACINE / "backend" / "app").rglob("*.py"):
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            noms = ([a.name for a in n.names] if isinstance(n, ast.Import)
                    else [n.module] if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module else [])
            for m in noms:
                m = m.split(".")[0]
                if m in sys.stdlib_module_names or m == "app" or m in _FACULTATIFS:
                    continue
                d = _TRANSITIFS.get(m) or _DISTRIB.get(m) or m.replace("_", "-")
                if d.lower() not in req:
                    manque.setdefault(m, str(f.relative_to(RACINE)))
    assert not manque, manque


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
