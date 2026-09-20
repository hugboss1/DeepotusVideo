# Finitions UI — chantier 1 : une origine nommée `deepotus.localhost` — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** l'application s'ouvre et se sert sous `http://deepotus.localhost:8765/` (nom d'application, pas d'IP) ; `127.0.0.1` et `localhost` restent acceptés pour les bancs, curl et les scripts.

**Architecture :** une constante `APP_HOSTNAME = "deepotus.localhost"` et une fonction pure `app_url(port)` dans `backend/app/config.py` ; le garde CSRF de `main.py` et le garde des Réglages de `routes.py` acceptent ce nom ; le lanceur `scripts/launch-silent.vbs` ouvre l'URL nommée ; les titres des pages standalone deviennent « Deepotus — <outil> ». Aucun fichier hosts : Chrome, Edge et Firefox résolvent `*.localhost` en boucle locale (RFC 6761).

**Tech :** pydantic-settings, starlette middleware, pytest (python embarqué), VBScript du lanceur.

---

## Relevé (code lu le 20/09/2026, branche à `c97f9b0`)

| Lieu | Ligne | Fait | Décision |
|---|---|---|---|
| `backend/app/config.py` | 102-103 | `HOST = "127.0.0.1"`, `PORT = 8765` | on **garde** l'écoute sur 127.0.0.1 ; on ajoute `APP_HOSTNAME` et `app_url()` |
| `backend/app/main.py` | 206 | `_ALLOWED_ORIGIN_HOSTS = {"127.0.0.1", "localhost", "::1", ""}` — garde CSRF sur l'en-tête `Origin` des requêtes non-GET | ajouter `APP_HOSTNAME` |
| `backend/app/main.py` | 546 | **commentaire** « opens http://127.0.0.1:8765 » (le lanceur réel est le `.vbs`) | corriger le commentaire |
| `backend/app/api/routes.py` | 3547-3552 | `_require_localhost` compare `request.client.host` (l'IP du client TCP, jamais le nom) à `127.0.0.1 / ::1 / localhost / testclient` | **rien à changer** : avec `deepotus.localhost` le client TCP reste 127.0.0.1 ; on le prouve au banc |
| `backend/app/api/routes.py` | 69-79 | `_is_private_host` (SSRF) : `localhost`, `.local`, IP privées — `deepotus.localhost` n'est **pas** reconnu privé | ajouter `.endswith(".localhost")` (RFC 6761 : toujours la boucle locale) |
| `scripts/launch-silent.vbs` | 20, 60-63 | `url = "http://127.0.0.1:8765"` ; sonde `url & "/api/health"` puis `shell.Run url` | sonder sur 127.0.0.1, **ouvrir** `http://deepotus.localhost:8765` |
| `scripts/dz_postdeploy_probe.ps1` | 11 | `$api = "http://127.0.0.1:8765/api"` | garder (sonde) |
| `frontend/*/index.html` | 5-6 | titres « Vectorlab — Deepotus Video Gen », « Sprite Lab — … », « Tile Lab — … », « Atelier Chapitre — … », « Card Forge — … », « Établi — … », « Material Forge — … », « 3D Studio — … » ; bundle « Deepotus Video Gen 🐙 » | standalone → « Deepotus — Vectorlab » etc. ; le bundle garde son titre (dans `dist/index.html`, hors patcher) |
| standalone JS | — | aucune URL absolue `http://127.0.0.1` (seul `http://www.w3.org/2000/svg`) ; le bundle n'en porte qu'une : `http://127.0.0.1:11434` (Ollama, serveur tiers) | rien |
| `docs/guide/fr.html` | 292 | « ouvrez http://127.0.0.1:8765 » | mettre l'URL nommée |
| `backend/tests/test_security_guards.py` | 66-74 | table `_is_private_host` | ajouter `("deepotus.localhost", True)` |
| `_data_root` | config.py | indépendant du code | le backend de preuve tourne sur 8799 avec `DEEPOTUS_DATA_DIR` |

Écart assumé (spec) : le port reste dans l'URL ; le raccourci Inno pointe sur `launch-silent.vbs`, pas sur l'URL.

---

### Task 1 : `APP_HOSTNAME` + `app_url()` + garde CSRF + SSRF (TDD pytest)

**Files :**
- Modify : `backend/app/config.py`, `backend/app/main.py`, `backend/app/api/routes.py`
- Test : `backend/tests/test_origine_nommee.py` (neuf) ; `backend/tests/test_security_guards.py` (une ligne)

- [ ] **Step 1 : le banc RED**

```python
"""L'origine nommée deepotus.localhost (finitions UI, 20/09/2026)."""
import pytest
from fastapi.testclient import TestClient


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
    with TestClient(app) as c:
        r = c.post("/api/settings/keys", json={}, headers={"Origin": origin})
        # 403 « Cross-origin request blocked » = refusé par le garde ; tout autre code = passé
        assert (r.status_code == 403 and "Cross-origin" in r.text) is (not ok)


def test_settings_restent_accessibles_depuis_l_hote_nomme():
    from app.main import app
    with TestClient(app, base_url="http://deepotus.localhost:8765") as c:
        r = c.get("/api/settings/keys", headers={"Host": "deepotus.localhost:8765"})
        assert r.status_code == 200
```

- [ ] **Step 2 : RED** — `<python embarqué> -m pytest backend/tests/test_origine_nommee.py -q` → `AttributeError: APP_HOSTNAME`.
- [ ] **Step 3 : config.py** (après `APP_VERSION`) :

```python
# Origine nommée (finitions UI, 20/09/2026) : les navigateurs résolvent
# *.localhost en boucle locale sans fichier hosts (RFC 6761). Le serveur
# ÉCOUTE toujours sur HOST (127.0.0.1) ; c'est l'URL OUVERTE qui porte le nom.
APP_HOSTNAME = "deepotus.localhost"


def app_url(port: int | None = None) -> str:
    return f"http://{APP_HOSTNAME}:{port if port is not None else settings.PORT}"
```
  (`settings` est instancié plus bas dans le module : `app_url` le lit à l'appel — vérifier que `settings = Settings()` existe bien en fin de `config.py`.)
- [ ] **Step 4 : main.py 206** → `_ALLOWED_ORIGIN_HOSTS = {"127.0.0.1", "localhost", "::1", "", APP_HOSTNAME}` avec `from app.config import APP_HOSTNAME` (vérifier l'import existant de `config`) ; commentaire 546 → « opens http://deepotus.localhost:8765 (scripts/launch-silent.vbs) ».
- [ ] **Step 5 : routes.py 74** → `if h in ("localhost", "") or h.endswith(".local") or h.endswith(".localhost"):` ; `test_security_guards.py` : ajouter `("deepotus.localhost", True)` à la table.
- [ ] **Step 6 : GREEN** — le banc neuf + `test_security_guards.py` verts ; `import app.main` OK avec le python embarqué.
- [ ] **Step 7 :** commit `--only` : `origine nommee : APP_HOSTNAME deepotus.localhost, garde CSRF et SSRF, banc`.

### Task 2 : lanceur, titres, guide

- [ ] **Step 1 :** `scripts/launch-silent.vbs` : `url = "http://127.0.0.1:8765"` reste la sonde ; ajouter `Dim urlApp` … `urlApp = "http://deepotus.localhost:8765"` et `shell.Run urlApp, 1, False` à la place de `shell.Run url, 1, False`. Commentaire en tête : « opens http://deepotus.localhost:8765 (RFC 6761, no hosts file) ».
- [ ] **Step 2 :** titres : `frontend/vectorlab/index.html` « Deepotus — Vectorlab », `spritelab` « Deepotus — Sprite Lab », `tilelab` « Deepotus — Tile Lab », `atelier` « Deepotus — Atelier Chapitre », `cardforge` « Deepotus — Card Forge », `etabli` « Deepotus — Établi », `materialforge` « Deepotus — Material Forge », `studio3d` « Deepotus — 3D Studio ». Vérifier par `grep -rn "<title>" frontend/*/index.html`.
- [ ] **Step 3 :** `docs/guide/fr.html:292` (et l'équivalent `en.html` s'il existe : `grep -n "127.0.0.1:8765" docs/guide/*.html`) → `http://deepotus.localhost:8765`.
- [ ] **Step 4 :** banc statique dans `test_origine_nommee.py` :

```python
def test_lanceur_ouvre_l_url_nommee_et_sonde_l_ip():
    import pathlib
    vbs = (pathlib.Path(__file__).resolve().parents[2] / "scripts" / "launch-silent.vbs").read_text(encoding="utf-8", errors="replace")
    assert 'shell.Run urlApp, 1, False' in vbs and 'urlApp = "http://deepotus.localhost:8765"' in vbs
    assert 'url = "http://127.0.0.1:8765"' in vbs           # la sonde /api/health reste sur l'IP


def test_titres_des_pages_standalone():
    import pathlib, re
    racine = pathlib.Path(__file__).resolve().parents[2] / "frontend"
    for outil in ("vectorlab", "spritelab", "tilelab", "atelier", "cardforge", "etabli", "materialforge", "studio3d"):
        html = (racine / outil / "index.html").read_text(encoding="utf-8")
        titre = re.search(r"<title>(.*?)</title>", html).group(1)
        assert titre.startswith("Deepotus — "), (outil, titre)
```
- [ ] **Step 5 :** RED (titres anciens) → édition → GREEN ; commit `--only` : `origine nommee : le lanceur ouvre deepotus.localhost, titres « Deepotus — <outil> », guide`.

### Task 3 : preuve en réel sur 8799

- [ ] **Step 1 :** relancer le backend de preuve (python embarqué, `sys.path` du worktree, `DEEPOTUS_DATA_DIR` scratch, port 8799).
- [ ] **Step 2 :** `curl -s -o NUL -w "%{http_code}" http://deepotus.localhost:8799/vectorlab/` → 200 (curl résout `*.localhost` ? sinon `--resolve deepotus.localhost:8799:127.0.0.1` et noter que c'est le NAVIGATEUR qui résout) ; navigateur intégré : `navigate http://deepotus.localhost:8799/vectorlab/?doc=<id>` → `location.hostname === "deepotus.localhost"`, `document.title === "Deepotus — Vectorlab"`, `VL` chargé, `#stage` > 0.
- [ ] **Step 3 :** depuis cette page : `fetch("/api/vector/docs", {method:"POST", …})` (l'`Origin` envoyé par le navigateur = `http://deepotus.localhost:8799`) → 200 ; `fetch("/api/settings/keys")` → 200 ; et une requête avec `Origin: http://evil.example.com` posée via `curl -X POST -H "Origin: http://evil.example.com" http://127.0.0.1:8799/api/settings/keys` → 403.
- [ ] **Step 4 :** `taskkill` du PID 8799 ; consigner.

### Task 4 : déploiement (Python touché → relance par l'utilisateur), mémoire, push

- [ ] **Step 1 :** table `git hash-object` installé / base `c97f9b0` / cible pour `backend/app/config.py`, `backend/app/main.py`, `backend/app/api/routes.py`, `scripts/launch-silent.vbs`, les 8 `index.html`, `docs/guide/*.html`, `backend/tests/*` ; sauvegarde `_backup_predeploy_2026-09-20-origine` ; copie ; re-table.
- [ ] **Step 2 :** pré-vol sur l'installé : `<installé>\runtime\python\python.exe -c "import sys; sys.path.insert(0, r'<installé>\backend'); import app.main; from app.config import app_url; print(app_url())"`.
- [ ] **Step 3 :** l'utilisateur relance le backend installé ; vérifier ensuite `Get-Process` StartTime du PID qui écoute 8765 > LastWriteTime des .py — tant que ce n'est pas le cas, le rapport dit « en attente de relance ».
- [ ] **Step 4 :** relevé en tête du plan, mémoire, push.
