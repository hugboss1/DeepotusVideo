# Assistant « Demander à Deepotus » — plan d'implémentation (lots A0 à A4)

> **Pour les agents qui exécutent :** SOUS-SKILL OBLIGATOIRE : superpowers:subagent-driven-development (recommandé)
> ou superpowers:executing-plans, tâche par tâche. Les étapes sont des cases `- [ ]` à cocher.

**But :** un tiroir « Demander » (F1) où l'utilisateur pose une question sur l'application. L'assistant répond en
quelques étapes, puis peut emmener l'utilisateur au bon écran, ouvrir le chapitre du guide qui va avec et faire glisser
un curseur jusqu'au bouton à cliquer, à la façon de Clicky.

**Architecture :**
- `docs/agent/` contient la connaissance : `AGENT.md` écrit à la main et `ancres.json`, le registre des cibles nommées.
- Un service backend assemble le message système à partir de cette connaissance, du résumé du guide et du contexte.
  Il appelle `moteurs_texte.tirer_garde` dans la catégorie de plafond « aide », puis transforme les balises
  `[POINT:…]`, `[ALLER:…]` et `[GUIDE:…]` en actions.
- Un script partagé chargé par la SPA, `/shared/dz-agent.js`, affiche le tiroir et le pointeur. Ce n'est pas un patch
  du bundle.
- Dans les labs affichés dans un cadre intégré, un script de cadre répond par `postMessage`.

**Pile :** FastAPI (Python embarqué), modules ES vanilla sans dépendance, bancs node `.test.mjs` et bancs Python
lancés depuis `backend/`.

**Spec :** `docs/superpowers/specs/2026-10-19-agent-aide-design.md`.

**Hors de ce plan :**
- A5, la vision en secours (balise `[VOIR]`). Il faut d'abord ajouter les images à `moteurs_texte`.
- A6, la voix.
- A7, le chapitre du guide.

Ces trois lots feront l'objet d'un second plan une fois A0 à A4 fusionnés.

**Écart volontaire avec la spec :** le moteur se choisit **dans le tiroir** (liste des moteurs configurés, mémorisée
dans `localStorage dz_agent_moteur`) et non dans Réglages › Défauts. Cela évite de patcher le bundle. Faute de choix,
le serveur prend le premier moteur configuré dans cet ordre : anthropic, openai, gemini, puis les autres.

---

## Conventions à connaître (aucun contexte supposé)

- **Python :** `$PY = "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe"`. Ce Python embarqué **ignore
  PYTHONPATH**. Chaque banc fait donc lui-même `sys.path.insert(0, <backend>)` et se lance depuis `backend/` :
  `& $PY tests/<banc>.py`. Les bancs pytest ont un lanceur
  `if __name__ == "__main__": sys.exit(pytest.main([__file__, "-q"]))`, sinon le banc `test_hygiene_lanceurs`
  échoue.
- **Bancs node :** `node frontend/shared/qa/<nom>.test.mjs`.
- **Le bundle `frontend/dist/assets/index-*.js` ne se touche pas** dans ce plan. Tout passe par
  `frontend/dist/index.html` et `/shared/`.
- **`/shared/x.js` est servi depuis `frontend/dist/shared/`.** La source est `frontend/shared/` et la copie dans dist
  doit être **identique octet pour octet** : on la copie avec `cp`, jamais à la main.
- **Le français est la langue de référence.** Tout texte visible passe par `dzT("agent.…")`, et le dictionnaire se
  reconstruit avec `& $PY scripts/i18n_assembler.py`.
- **Backend de preuve :** `& $PY scripts/guide/serve_guide.py` sert le code du worktree sur **8809**, avec un dossier
  de données jetable et aucune clé. On n'utilise jamais le 8765 de l'utilisateur.
- **Commits :** `git commit --only <fichiers>` et un message en français. Toujours terminer par
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Carte des fichiers

| Fichier | Rôle |
|---|---|
| `AGENTS.md` (créé) | Mode d'emploi du dépôt pour les agents de code (A0) |
| `CLAUDE.md` (créé) | Une ligne qui renvoie vers `AGENTS.md` |
| `docs/agent/AGENT.md` (créé) | Mode d'emploi de l'application **pour l'assistant** |
| `docs/agent/ancres.json` (créé) | Registre des cibles nommées |
| `backend/app/services/agent_aide.py` (créé) | Connaissance, message système, balises, choix du moteur, `demander` |
| `backend/app/api/agent_routes.py` (créé) | `GET /api/agent/etat`, `POST /api/agent/demander` |
| `backend/app/main.py` (modifié) | Enregistre le routeur |
| `backend/app/services/plafonds.py` (modifié) | Ajoute la catégorie `"aide"` |
| `frontend/shared/dz-agent-logique.js` (créé) | Logique pure : choix d'élément, courbe, étapes d'une action |
| `frontend/shared/dz-agent.js` (créé) | Tiroir, F1, appels, boutons, pointeur |
| `frontend/shared/dz-agent-cadre.js` (créé) | Répondeur `postMessage` dans les labs |
| `frontend/shared/i18n/agent.json` (créé) | Libellés FR et EN |
| `frontend/dist/shared/*` (copies) | Copies servies |
| `frontend/dist/index.html` (modifié) | Charge `dz-agent.js` |
| `frontend/{vectorlab,photolab,spritelab,tilelab}/index.html` (modifiés) | Chargent `dz-agent-cadre.js` |
| `backend/tests/test_agents_md.py` | Banc A0 |
| `backend/tests/test_agent_connaissance.py` | Banc A1 |
| `backend/tests/test_agent_aide.py` | Banc A2 (service et routes) |
| `backend/tests/test_agent_ecran.py` | Banc A3/A4 (copies, balises, i18n) |
| `frontend/shared/qa/agent_logique.test.mjs` | Banc node de la logique pure |

---

### Tâche 1 : A0, `AGENTS.md` à la racine

**Fichiers :**
- Créer : `AGENTS.md`, `CLAUDE.md`
- Banc : `backend/tests/test_agents_md.py`

- [ ] **Étape 1 : écrire le banc qui échoue**

```python
# -*- coding: utf-8 -*-
"""A0 (spec 2026-10-19-agent-aide-design.md) — AGENTS.md à la racine : les sections attendues, et chaque chemin cité
entre accents graves dans « Fichiers clés » existe. CLAUDE.md y renvoie.
Run : & $PY tests/test_agents_md.py   (depuis backend/)"""
import pathlib, re, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
SECTIONS = ["## Vue d'ensemble", "## Architecture", "## Fichiers clés", "## Lancer et tester", "## Conventions",
            "## Git", "## Tenir ce fichier à jour"]


def _texte():
    return (RACINE / "AGENTS.md").read_text(encoding="utf-8")


def test_sections():
    t = _texte()
    manquantes = [s for s in SECTIONS if s not in t]
    assert not manquantes, manquantes


def test_chemins_cites_existent():
    t = _texte()
    bloc = t.split("## Fichiers clés", 1)[1].split("\n## ", 1)[0]
    chemins = [c for c in re.findall(r"`([^`]+)`", bloc) if "/" in c and " " not in c and "*" not in c]
    assert len(chemins) >= 12, chemins
    absents = [c for c in chemins if not (RACINE / c.rstrip("/")).exists()]
    assert not absents, absents


def test_claude_md_renvoie():
    assert "AGENTS.md" in (RACINE / "CLAUDE.md").read_text(encoding="utf-8")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
```

- [ ] **Étape 2 : le lancer et le voir échouer**

Lancer : `& $PY tests/test_agents_md.py` (depuis `backend/`).
Attendu : 3 échecs, `FileNotFoundError` sur AGENTS.md.

- [ ] **Étape 3 : écrire `AGENTS.md`**

```markdown
# AGENTS.md — DeepotusVideo

Référence unique pour les agents de code (Claude Code, Cursor, Copilot…). `CLAUDE.md` y renvoie.
Pour aider l'UTILISATEUR de l'application, l'assistant intégré lit `docs/agent/AGENT.md`, pas ce fichier.

## Vue d'ensemble
DeepotusVideo est un studio local Windows, clavier d'abord, pour fabriquer des vidéos 9:16 virales et leurs
ressources. Il compte 14 écrans : Quick, Studio, Chapitres, Son & VFX, Montage, Planificateur, Modèles, News,
Bibliothèque, Game Assets, Vectorlab, Photolab, Avatar live et Réglages. Un seul utilisateur. Le français est la langue
de référence, l'anglais en est la traduction. Le produit est décrit dans `PRODUCT.md`, la direction visuelle dans
`DESIGN.md`.

## Architecture
- **Backend** FastAPI dans `backend/app` : les routes sont dans `api/`, les services dans `services/`, l'application
  dans `main.py`. Les données de l'utilisateur sont dans `%LOCALAPPDATA%\DeepotusVideoGen`.
- **SPA** : le bundle `frontend/dist/assets/index-*.js` est **prébâti puis patché**. On ne le reconstruit jamais
  depuis `frontend/src` (voir `frontend/SOURCE.md`). Toute modification passe par un script
  `scripts/patch_bundle_<tag>.py` (paires d'ancres uniques, sonde amont, `.bak_<tag>`, `--check`), et toute la chaîne
  se rejoue avec `scripts/repatch_all.py`.
- **Labs** : des pages autonomes `frontend/<lab>/index.html` avec leurs `js/mod-*.js`, affichées dans un cadre
  intégré de la SPA.
- **Scripts partagés** : la source est `frontend/shared/`, la copie identique est `frontend/dist/shared/`, le tout
  servi à `/shared/`.
- **LLM** : `backend/app/services/moteurs_texte.py`. `tirer` fait un seul appel, sans repli muet. `tirer_garde` passe
  par le plafond.
- **Dépenses** : toute route payante appelle `plafonds.verifier`, sinon le banc `test_plafonds_garde` échoue.
- **Clés** : le coffre est dans `services/coffre.py`, en localhost seulement.
- **Traduction** : `dzT(clé)` côté écran (`frontend/shared/i18n/*.json`, assemblés par
  `scripts/i18n_assembler.py`) ; côté serveur, `app.i18n`.

## Fichiers clés
| Fichier | Rôle |
|---|---|
| `backend/app/main.py` | Application, montages statiques, routeurs |
| `backend/app/api/routes.py` | Routes historiques (énorme ; préférer un routeur dédié) |
| `backend/app/api/settings_routes.py` | Réglages, index de recherche des Réglages |
| `backend/app/services/moteurs_texte.py` | Registre des moteurs de texte, `tirer`, `tirer_garde` |
| `backend/app/services/plafonds.py` | Plafonds de dépense mensuels |
| `backend/app/services/coffre.py` | Coffre à clés chiffré |
| `backend/app/services/espaces.py` | Espaces de marque |
| `frontend/dist/index.html` | Page de la SPA, scripts partagés |
| `frontend/shared/dz-i18n.js` | Runtime `dzT` |
| `frontend/shared/dz-plafonds.js` | Dialogue du 402 `dz_plafond` |
| `frontend/SOURCE.md` | Pourquoi le bundle ne se reconstruit pas |
| `scripts/repatch_all.py` | Rejoue la chaîne des patchers |
| `scripts/i18n_assembler.py` | Assemble le dictionnaire FR/EN |
| `scripts/guide/construire_guide.py` | Construit le guide utilisateur |
| `scripts/guide/serve_guide.py` | Backend de preuve (8809, sans clé) |
| `docs/guide/src/chapitres.json` | Chapitres du guide (lisibles par machine) |

## Lancer et tester
- Python embarqué : `$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe`. Il ignore PYTHONPATH : chaque banc
  insère `backend/` lui-même. On lance depuis `backend/` : `& $PY tests/<banc>.py`.
- Suite complète : `.\scripts\run-tests.ps1`.
- Bancs des labs et de `/shared` : `node frontend/<lab>/qa/<banc>.test.mjs`.
- Preuve à l'écran : `& $PY scripts/guide/serve_guide.py` (port 8809). Ne jamais toucher au 8765 de l'utilisateur.
- Installation : comparer les empreintes avec `git hash-object`, jamais sha256.

## Conventions
- Noms et commentaires en français. Chaque fonctionnalité est datée et rattachée à sa tâche (`t237`, `#387`…).
- Aucune chaîne visible en dur : `dzT`, avec une clé FR et une clé EN.
- Une copie `frontend/dist/shared` est identique à sa source, et un banc le vérifie.
- Un modèle sans clé reste choisissable et n'est jamais grisé : le refus arrive au lancement (503), avant le plafond.
- On n'écrit jamais une clé dans un journal, une URL ou une réponse.
- Les bancs arrivent avant le code (TDD). Les bancs de patch ont leur inverse.

## Git
- Une branche par chantier : `chantier/<sujet>` ou `claude/<sujet>`. Une PR par lot. Jamais de push forcé sur main.
- Dans un worktree partagé : `git commit --only <fichiers>`.
- Message en français, au format `<zone> : <quoi> (tNNN)`.

## Tenir ce fichier à jour
Quand l'architecture, une commande ou une convention change, mets à jour ce fichier dans la même PR. Quand une
fonctionnalité visible est livrée, mets aussi à jour `docs/agent/AGENT.md` et `docs/agent/ancres.json`.
```

- [ ] **Étape 4 : écrire `CLAUDE.md`**

```markdown
Lire `AGENTS.md` : c'est la référence unique pour les agents de code dans ce dépôt.
```

- [ ] **Étape 5 : relancer le banc et le voir réussir**

Lancer : `& $PY tests/test_agents_md.py`. Attendu : `3 passed`.

- [ ] **Étape 6 : commiter**

```bash
git add AGENTS.md CLAUDE.md backend/tests/test_agents_md.py
git commit --only AGENTS.md CLAUDE.md backend/tests/test_agents_md.py -m "agents : AGENTS.md racine pour les agents de code (A0)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 2 : A1, `ancres.json` (le rail et les Réglages)

**Fichiers :**
- Créer : `docs/agent/ancres.json`
- Banc : `backend/tests/test_agent_connaissance.py`

Il y a trois formes d'ancre :
- **Ancre d'élément :** `selecteur` CSS, plus éventuellement `texte` `{fr,en}` pour choisir parmi les éléments
  trouvés. Le texte se compare au `textContent` ou à l'attribut `title`.
- **Ancre de Réglages :** `reglages: "<section>"`, sans sélecteur. L'action ouvre la section.
- **Ancre de lab :** `cadre: "/vectorlab/"`. L'élément est cherché dans le cadre intégré dont l'adresse contient ce
  chemin.

- [ ] **Étape 1 : écrire le banc qui échoue**

```python
# -*- coding: utf-8 -*-
"""A1 (spec 2026-10-19-agent-aide-design.md) — la connaissance de l'assistant est cohérente :
ancres.json bien formé ; écrans connus ; sections de Réglages connues ; texte d'ancre présent dans l'application
(bundle ou dictionnaire) ; AGENT.md ne cite que des ancres, vues et chapitres qui existent.
Run : & $PY tests/test_agent_connaissance.py   (depuis backend/)"""
import json, pathlib, re, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "backend"))
from app.services import agent_aide as A                                    # noqa: E402

ANCRES = json.loads((RACINE / "docs" / "agent" / "ancres.json").read_text(encoding="utf-8"))["ancres"]
CHAPITRES = {c["id"] for c in json.loads((RACINE / "docs" / "guide" / "src" / "chapitres.json")
                                         .read_text(encoding="utf-8"))["chapitres"]}
BUNDLE = next((RACINE / "frontend" / "dist" / "assets").glob("index-*.js")).read_text(encoding="utf-8")
DICO = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_text(encoding="utf-8")
LABS = {"/vectorlab/", "/photolab/", "/spritelab/", "/tilelab/"}


def test_forme():
    ids = [a["id"] for a in ANCRES]
    assert len(ids) == len(set(ids)), "identifiants en double"
    for a in ANCRES:
        assert re.fullmatch(r"[a-z0-9]+(\.[a-z0-9_]+)+", a["id"]), a["id"]
        assert a.get("fr") and a.get("en"), a["id"]
        assert a.get("selecteur") or a.get("reglages"), a["id"]


def test_ecrans_et_sections():
    for a in ANCRES:
        assert a.get("ecran") is None or a["ecran"] in A.VUES, a
        assert a.get("reglages") is None or a["reglages"] in A.SECTIONS_REGLAGES, a
        assert a.get("cadre") is None or a["cadre"] in LABS, a


def test_textes_presents_dans_l_application():
    for a in ANCRES:
        t = a.get("texte")
        if not t:
            continue
        for lang in ("fr", "en"):
            v = json.dumps(t[lang], ensure_ascii=False)[1:-1]
            if a.get("cadre"):
                lab = RACINE / "frontend" / a["cadre"].strip("/")
                src = "".join(p.read_text(encoding="utf-8", errors="replace")
                              for p in [lab / "index.html", *sorted((lab / "js").glob("*.js"))] if p.exists())
                assert t[lang] in src or v in src or v in DICO, (a["id"], lang)
            else:
                assert v in BUNDLE or v in DICO, (a["id"], lang)


def test_le_rail_complet():
    rail = {a["ecran"] for a in ANCRES if a["id"].startswith("rail.")}
    assert rail == set(A.VUES), set(A.VUES) - rail


def test_agent_md_ne_cite_que_l_existant():
    t = (RACINE / "docs" / "agent" / "AGENT.md").read_text(encoding="utf-8")
    ids = {a["id"] for a in ANCRES}
    for typ, cible in re.findall(r"\[(POINT|ALLER|GUIDE):([^\]]+)\]", t):
        if cible.startswith("<"):
            continue                                        # gabarit de la règle (« [POINT:<ancre>] »)
        assert {"POINT": cible in ids, "ALLER": cible in A.VUES, "GUIDE": cible in CHAPITRES}[typ], (typ, cible)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
```

- [ ] **Étape 2 : écrire le squelette minimal de `agent_aide.py`** (le banc l'importe)

```python
# -*- coding: utf-8 -*-
"""Assistant « Demander à Deepotus » (spec docs/superpowers/specs/2026-10-19-agent-aide-design.md, 19/10/2026).

La connaissance vit dans docs/agent/ (AGENT.md écrit à la main, ancres.json) et docs/guide/src/ (chapitres.json,
jeveux.json). Ce module l'assemble en message système, appelle UN moteur de texte sous le plafond « aide », puis
transforme les balises de la réponse en actions pour l'écran. Il n'exécute RIEN de payant pour l'utilisateur.
"""
from __future__ import annotations

from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]
DOSSIER = RACINE / "docs" / "agent"
GUIDE = RACINE / "docs" / "guide" / "src"
# les vues du rail de la SPA (bundle : `Yu`), dans l'ordre du rail
VUES = ("quick", "studio", "episodes", "sonvfx", "montage", "scheduler", "templates", "news", "library", "assets3d",
        "vectorlab", "photolab", "avatarlive", "settings")
# les sections des Réglages (settings_routes._RUBRIQUES)
SECTIONS_REGLAGES = ("diag", "coffre", "appareils", "keys", "accounts", "personas", "branding", "pack", "defaults",
                     "paths", "news", "appearance", "pricing", "transfert", "espaces")
```

- [ ] **Étape 3 : le lancer et le voir échouer**

Lancer : `& $PY tests/test_agent_connaissance.py`.
Attendu : erreur à la collecte, `FileNotFoundError` sur `docs/agent/ancres.json`.

- [ ] **Étape 4 : écrire `docs/agent/ancres.json`**

On y met le rail (14 entrées, sélecteur `button.dzNavItem` relevé dans le bundle, où chaque entrée est un
`<button className="dzNavItem">`) et les sections des Réglages.

```json
{
  "version": 1,
  "note": "Registre des cibles de l'assistant (spec 2026-10-19-agent-aide-design.md). Une fonctionnalité livrée ajoute ses ancres ici ; tests/test_agent_connaissance.py vérifie tout.",
  "ancres": [
    {"id": "rail.quick", "ecran": "quick", "selecteur": "button.dzNavItem", "texte": {"fr": "Quick", "en": "Quick"}, "fr": "Quick dans la barre de gauche", "en": "Quick in the left bar"},
    {"id": "rail.studio", "ecran": "studio", "selecteur": "button.dzNavItem", "texte": {"fr": "Studio", "en": "Studio"}, "fr": "Studio dans la barre de gauche", "en": "Studio in the left bar"},
    {"id": "rail.chapitres", "ecran": "episodes", "selecteur": "button.dzNavItem", "texte": {"fr": "Chapitres", "en": "Chapters"}, "fr": "Chapitres dans la barre de gauche", "en": "Chapters in the left bar"},
    {"id": "rail.sonvfx", "ecran": "sonvfx", "selecteur": "button.dzNavItem", "texte": {"fr": "Son & VFX", "en": "Sound & VFX"}, "fr": "Son & VFX dans la barre de gauche", "en": "Sound & VFX in the left bar"},
    {"id": "rail.montage", "ecran": "montage", "selecteur": "button.dzNavItem", "texte": {"fr": "Montage", "en": "Montage"}, "fr": "Montage dans la barre de gauche", "en": "Montage in the left bar"},
    {"id": "rail.planificateur", "ecran": "scheduler", "selecteur": "button.dzNavItem", "texte": {"fr": "Planificateur", "en": "Scheduler"}, "fr": "Planificateur dans la barre de gauche", "en": "Scheduler in the left bar"},
    {"id": "rail.modeles", "ecran": "templates", "selecteur": "button.dzNavItem", "texte": {"fr": "Modèles", "en": "Templates"}, "fr": "Modèles dans la barre de gauche", "en": "Templates in the left bar"},
    {"id": "rail.news", "ecran": "news", "selecteur": "button.dzNavItem", "texte": {"fr": "News", "en": "News"}, "fr": "News dans la barre de gauche", "en": "News in the left bar"},
    {"id": "rail.bibliotheque", "ecran": "library", "selecteur": "button.dzNavItem", "texte": {"fr": "Bibliothèque", "en": "Library"}, "fr": "Bibliothèque dans la barre de gauche", "en": "Library in the left bar"},
    {"id": "rail.gameassets", "ecran": "assets3d", "selecteur": "button.dzNavItem", "texte": {"fr": "Game Assets", "en": "Game Assets"}, "fr": "Game Assets dans la barre de gauche", "en": "Game Assets in the left bar"},
    {"id": "rail.vectorlab", "ecran": "vectorlab", "selecteur": "button.dzNavItem", "texte": {"fr": "Vectorlab", "en": "Vectorlab"}, "fr": "Vectorlab dans la barre de gauche", "en": "Vectorlab in the left bar"},
    {"id": "rail.photolab", "ecran": "photolab", "selecteur": "button.dzNavItem", "texte": {"fr": "Photolab", "en": "Photolab"}, "fr": "Photolab dans la barre de gauche", "en": "Photolab in the left bar"},
    {"id": "rail.avatarlive", "ecran": "avatarlive", "selecteur": "button.dzNavItem", "texte": {"fr": "Avatar live", "en": "Avatar live"}, "fr": "Avatar live dans la barre de gauche", "en": "Avatar live in the left bar"},
    {"id": "rail.reglages", "ecran": "settings", "selecteur": "button.dzNavItem", "texte": {"fr": "Réglages", "en": "Settings"}, "fr": "Réglages dans la barre de gauche", "en": "Settings in the left bar"},
    {"id": "reglages.cles", "ecran": "settings", "reglages": "keys", "fr": "Réglages › Clés API", "en": "Settings › API keys"},
    {"id": "reglages.coffre", "ecran": "settings", "reglages": "coffre", "fr": "Réglages › Coffre à clés", "en": "Settings › Key vault"},
    {"id": "reglages.comptes", "ecran": "settings", "reglages": "accounts", "fr": "Réglages › Comptes connectés", "en": "Settings › Connected accounts"},
    {"id": "reglages.personas", "ecran": "settings", "reglages": "personas", "fr": "Réglages › Personas", "en": "Settings › Personas"},
    {"id": "reglages.espaces", "ecran": "settings", "reglages": "espaces", "fr": "Réglages › Espaces de marque", "en": "Settings › Brand spaces"},
    {"id": "reglages.marque", "ecran": "settings", "reglages": "branding", "fr": "Réglages › Kit de marque", "en": "Settings › Brand kit"},
    {"id": "reglages.defauts", "ecran": "settings", "reglages": "defaults", "fr": "Réglages › Valeurs par défaut", "en": "Settings › Provider defaults"},
    {"id": "reglages.budget", "ecran": "settings", "reglages": "pricing", "fr": "Réglages › Tarifs et budget", "en": "Settings › Pricing & budget"},
    {"id": "reglages.diagnostic", "ecran": "settings", "reglages": "diag", "fr": "Réglages › Diagnostic et mise à jour", "en": "Settings › Diagnostics and update"},
    {"id": "reglages.apparence", "ecran": "settings", "reglages": "appearance", "fr": "Réglages › Apparence et langue", "en": "Settings › Appearance and language"},
    {"id": "reglages.appareils", "ecran": "settings", "reglages": "appareils", "fr": "Réglages › Appareils (mobile)", "en": "Settings › Devices (mobile)"},
    {"id": "reglages.transfert", "ecran": "settings", "reglages": "transfert", "fr": "Réglages › Transfert entre machines", "en": "Settings › Transfer between machines"}
  ]
}
```

- [ ] **Étape 5 : écrire une première version de `docs/agent/AGENT.md`** (le banc la lit ; elle sera complétée à la
  tâche 3)

```markdown
# AGENT.md — ce que l'assistant sait de DeepotusVideo

(Brouillon A1, complété à la tâche 3.)
```

- [ ] **Étape 6 : relancer le banc et le voir réussir**

Lancer : `& $PY tests/test_agent_connaissance.py`. Attendu : `5 passed`.
Si `test_textes_presents_dans_l_application` échoue sur un libellé, c'est le libellé de l'ancre qu'il faut corriger
pour qu'il colle à celui de l'application, jamais le banc.

- [ ] **Étape 7 : commiter**

```bash
git commit --only docs/agent/ancres.json docs/agent/AGENT.md backend/app/services/agent_aide.py backend/tests/test_agent_connaissance.py -m "agent : registre des ancres (rail, Réglages) et banc de cohérence (A1)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

(Faire d'abord `git add` sur ces mêmes fichiers : `--only` ne prend pas un fichier jamais suivi.)

---

### Tâche 3 : A1, rédiger `docs/agent/AGENT.md`

**Fichiers :**
- Modifier : `docs/agent/AGENT.md`
- Banc : `backend/tests/test_agent_connaissance.py` (déjà écrit ; on y ajoute un test de structure)

- [ ] **Étape 1 : ajouter le test de structure qui échoue**

Ajouter avant le lanceur dans `backend/tests/test_agent_connaissance.py` :

```python
def test_agent_md_structure():
    t = (RACINE / "docs" / "agent" / "AGENT.md").read_text(encoding="utf-8")
    for s in ("## Qui tu aides", "## Les écrans", "## Parcours", "## Pièges fréquents", "## Comment répondre",
              "## Tenir ce fichier à jour"):
        assert s in t, s
    for v in A.VUES:
        assert f"[ALLER:{v}]" in t, v                     # chaque écran a sa ligne dans la carte
    assert len(t) < 24_000, "AGENT.md doit tenir dans un message système raisonnable"
```

- [ ] **Étape 2 : le lancer et le voir échouer**

Lancer : `& $PY tests/test_agent_connaissance.py`. Attendu : `test_agent_md_structure` FAIL sur `## Qui tu aides`.

- [ ] **Étape 3 : écrire `docs/agent/AGENT.md`**

Avant d'écrire, il faut lire `PRODUCT.md`, puis pour chaque écran le chapitre correspondant
`docs/guide/src/fr/<chapitre>.html`. Chaque ligne d'écran **doit** reprendre ce que dit le guide, sans rien
inventer. Le texte ci-dessous est la base ; les phrases de rôle sont tirées des descriptions du rail
(`coque.rail.*_desc` dans `frontend/shared/i18n/coque.json`).

```markdown
# AGENT.md — ce que l'assistant sait de DeepotusVideo

Tu es l'assistant intégré de DeepotusVideo. Ton seul rôle : aider l'utilisateur à comprendre COMMENT se servir de
l'application. Tu expliques et tu montres ; tu ne lances rien toi-même.

## Qui tu aides
Un créateur solo, souvent pressé, qui fabrique des vidéos verticales 9:16 et leurs ressources sur son PC Windows.
Il préfère le clavier, les réponses courtes et concrètes. Il peut écrire en français ou en anglais.

## Les écrans
Une ligne par écran : ce qu'on y fait, le chapitre du guide.
- [ALLER:quick] **Quick** — une vidéo complète en quelques minutes à partir d'une idée. [GUIDE:quick]
- [ALLER:studio] **Studio** — composer une vidéo plan par plan (nœuds, animation, avatar). [GUIDE:studio]
- [ALLER:episodes] **Chapitres** — transformer un texte long ou un roman en épisodes. [GUIDE:chapitres]
- [ALLER:sonvfx] **Son & VFX** — bruitages, musique, voix, effets visuels. [GUIDE:son-vfx]
- [ALLER:montage] **Montage** — monter, étalonner, sous-titrer et livrer. [GUIDE:montage]
- [ALLER:scheduler] **Planificateur** — programmer les publications (YouTube, Instagram, TikTok…). [GUIDE:planificateur]
- [ALLER:templates] **Modèles** — gabarits de mise en page réutilisables. [GUIDE:modeles]
- [ALLER:news] **News** — transformer une actualité en script puis en post. [GUIDE:news]
- [ALLER:library] **Bibliothèque** — retrouver, trier et envoyer images, vidéos et sons. [GUIDE:bibliotheque]
- [ALLER:assets3d] **Game Assets** — sprites, tuiles, cartes, matières, 3D, établi, plateau. [GUIDE:assets2d]
- [ALLER:vectorlab] **Vectorlab** — dessin vectoriel, logos, découpe. [GUIDE:vectorlab]
- [ALLER:photolab] **Photolab** — retouche photo par calques. [GUIDE:photolab]
- [ALLER:avatarlive] **Avatar live** — un personnage animé en direct. [GUIDE:avatar-live]
- [ALLER:settings] **Réglages** — clés, comptes, espaces de marque, budget, langue. [GUIDE:reglages]

## Parcours
- **Première vidéo** : [POINT:rail.quick] → écrire l'idée → choisir le format → Générer. [GUIDE:quick]
- **Brancher une clé d'API** : [POINT:reglages.cles] → coller la clé → Tester → Enregistrer. [GUIDE:cles]
- **Choisir les modèles par défaut** : [POINT:reglages.defauts]. [GUIDE:modeles-et-cles]
- **Limiter les dépenses** : [POINT:reglages.budget] → plafond mensuel global ou par moteur. [GUIDE:budget]
- **Changer d'espace de marque** : [POINT:reglages.espaces]. [GUIDE:marques]
- **Publier sur les réseaux** : brancher les comptes [POINT:reglages.comptes], puis [POINT:rail.planificateur]. [GUIDE:comptes]
- **Monter et livrer** : [POINT:rail.montage]. [GUIDE:montage-livrer]
- **Retrouver un fichier** : [POINT:rail.bibliotheque]. [GUIDE:bibliotheque]
- **Passer l'interface en anglais / français** : [POINT:reglages.apparence]. [GUIDE:installer]
- **Mettre à jour l'application** : [POINT:reglages.diagnostic]. [GUIDE:installer]
- **Utiliser le téléphone** : [POINT:reglages.appareils]. [GUIDE:mobile]
- **Changer de PC** : Réglages › Transfert entre machines (l'écran ne l'ouvre pas par section). [GUIDE:transfert]
- **Raccourcis clavier** : [GUIDE:raccourcis]. **Ça ne marche pas** : [GUIDE:depannage].

## Pièges fréquents
- **Modèle sans clé** : il reste choisissable ; le refus arrive au lancement. Réponse : brancher la clé
  [POINT:reglages.cles].
- **Plafond atteint** : une fenêtre demande de confirmer la dépense ; on peut relever le plafond
  [POINT:reglages.budget].
- **Mauvaise marque** : les contenus suivent l'espace de marque actif [POINT:reglages.espaces].
- **Interface dans la mauvaise langue** : [POINT:reglages.apparence].

## Comment répondre
1. Réponds dans la langue de la question, en 5 étapes au plus, phrases courtes, sans jargon technique.
2. Termine par les balises utiles, chacune seule sur une ligne :
   - `[POINT:<ancre>]` pour montrer un élément (une ancre de la liste « Ancres » ci-dessous, rien d'autre) ;
   - `[ALLER:<vue>]` pour ouvrir un écran ;
   - `[GUIDE:<chapitre>]` pour ouvrir le chapitre du guide (un id de la liste « Chapitres »).
   Au plus 3 balises. Une balise inconnue est supprimée : n'en invente jamais.
3. Si tu ne sais pas, dis-le et propose le chapitre le plus proche ou [GUIDE:depannage].
4. Ne promets jamais un bouton que tu ne vois pas dans la liste des ancres ; décris-le alors avec des mots.
5. Ne donne jamais de prix exact ni de conseil financier ; renvoie au budget [POINT:reglages.budget].
6. Ne demande jamais de clé, de mot de passe ni de donnée personnelle.

## Tenir ce fichier à jour
Toute fonctionnalité visible livrée ajoute ici sa ligne (écran ou parcours) et ses ancres dans `ancres.json`.
Le banc `backend/tests/test_agent_connaissance.py` refuse une ancre, une vue ou un chapitre qui n'existe pas.
```

- [ ] **Étape 4 : relancer le banc et le voir réussir**

Lancer : `& $PY tests/test_agent_connaissance.py`. Attendu : `6 passed`.

- [ ] **Étape 5 : commiter**

```bash
git commit --only docs/agent/AGENT.md backend/tests/test_agent_connaissance.py -m "agent : AGENT.md, le mode d'emploi de l'application pour l'assistant (A1)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 4 : A2, la connaissance et le message système

**Fichiers :**
- Modifier : `backend/app/services/agent_aide.py`
- Banc : `backend/tests/test_agent_aide.py`

- [ ] **Étape 1 : écrire le banc qui échoue**

```python
# -*- coding: utf-8 -*-
"""A2 (spec 2026-10-19-agent-aide-design.md) — le service de l'assistant : message système, balises, choix du moteur,
`demander` sous le plafond « aide », et les routes /api/agent.
Run : & $PY tests/test_agent_aide.py   (depuis backend/)"""
import asyncio, os, pathlib, sys, tempfile
import pytest

_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzagent_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.services import agent_aide as A                                    # noqa: E402


def test_systeme_contient_tout():
    s = A.systeme("montage", "fr", "Deepotus")
    assert "## Comment répondre" in s                       # AGENT.md
    assert "- quick : " in s and "- depannage : " in s       # chapitres
    assert "rail.montage" in s and "reglages.cles" in s      # ancres
    assert "écran ouvert : montage" in s and "espace de marque actif : Deepotus" in s


def test_systeme_anglais_et_prefixe_stable():
    fr, en = A.systeme("quick", "fr", ""), A.systeme("quick", "en", "")
    assert "- tour : Take a tour of the app" in en and "- tour : Faire le tour de l'application" in fr
    assert "langue : English" in en and "Take a tour" not in fr
    # le contexte est À LA FIN : deux écrans différents partagent tout le début (cache du préfixe)
    a, b = A.systeme("quick", "fr", "X"), A.systeme("montage", "fr", "Y")
    assert a.split("## Contexte")[0] == b.split("## Contexte")[0]
```

(La suite du banc arrive aux tâches 5 à 7, sans lanceur pour l'instant. Le lanceur `__main__` est ajouté à la
tâche 7.)

- [ ] **Étape 2 : le lancer et le voir échouer**

Lancer : `& $PY -m pytest tests/test_agent_aide.py -q`.
Attendu : `AttributeError: module 'app.services.agent_aide' has no attribute 'systeme'`.

- [ ] **Étape 3 : ajouter à `agent_aide.py`**

```python
import json
from functools import lru_cache


@lru_cache(maxsize=1)
def connaissance() -> dict:
    """Lue une fois par processus (les fichiers suivent l'installation, jamais l'utilisateur)."""
    ancres = json.loads((DOSSIER / "ancres.json").read_text(encoding="utf-8"))["ancres"]
    chap = json.loads((GUIDE / "chapitres.json").read_text(encoding="utf-8"))["chapitres"]
    jv = json.loads((GUIDE / "jeveux.json").read_text(encoding="utf-8"))["entrees"]
    return {"agent": (DOSSIER / "AGENT.md").read_text(encoding="utf-8"),
            "ancres": {a["id"]: a for a in ancres},
            "chapitres": {c["id"]: c for c in chap},
            "jeveux": jv}


def systeme(ecran: str, lang: str, espace: str = "") -> str:
    """AGENT.md + chapitres + « Je veux… » + ancres + vues, puis le contexte EN DERNIER : tout ce qui précède
    « ## Contexte » est identique d'une question à l'autre (cache du préfixe chez le fournisseur)."""
    k = connaissance()
    en = lang == "en"
    cle = "en" if en else "fr"
    chap = "\n".join(f"- {c['id']} : {c[cle]}" for c in k["chapitres"].values())
    jv = "\n".join(f"- {e[cle]} → {e['cible']}" for e in k["jeveux"])
    anc = "\n".join(f"- {a['id']} ({a.get('ecran') or 'partout'}) : {a[cle]}" for a in k["ancres"].values())
    return (f"{k['agent']}\n\n## Chapitres du guide (id : titre)\n{chap}\n\n## Je veux…\n{jv}\n\n"
            f"## Ancres (id (écran) : libellé)\n{anc}\n\n## Vues\n{', '.join(VUES)}\n\n"
            f"## Contexte\n- écran ouvert : {ecran or 'inconnu'}\n- espace de marque actif : {espace or 'inconnu'}\n"
            f"- langue : {'English' if en else 'français'}\n")
```

- [ ] **Étape 4 : relancer le banc et le voir réussir**

Lancer : `& $PY -m pytest tests/test_agent_aide.py -q`. Attendu : `2 passed`.

- [ ] **Étape 5 : commiter**

```bash
git add backend/tests/test_agent_aide.py
git commit --only backend/app/services/agent_aide.py backend/tests/test_agent_aide.py -m "agent : connaissance et message système à préfixe stable (A2)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 5 : A2, l'analyse des balises

**Fichiers :** `backend/app/services/agent_aide.py`, `backend/tests/test_agent_aide.py`

- [ ] **Étape 1 : ajouter les tests qui échouent** (à la fin de `test_agent_aide.py`)

```python
def test_balises_valides_deviennent_actions():
    texte, actions, rejets = A.analyser("Ouvre les Réglages.\n[POINT:reglages.cles]\n[GUIDE:cles]\n[ALLER:montage]")
    assert texte == "Ouvre les Réglages."
    assert [a["type"] for a in actions] == ["point", "guide", "aller"] and rejets == 0
    p = actions[0]
    assert p["cible"] == "reglages.cles" and p["reglages"] == "keys" and p["ecran"] == "settings"
    assert p["fr"] == "Réglages › Clés API" and actions[1]["en"]


def test_balises_inconnues_retirees_et_comptees():
    texte, actions, rejets = A.analyser("A [POINT:bouton.invente] B [ALLER:nulle-part] [GUIDE:x] [VOIR] [FOO:bar]")
    assert actions == [] and rejets == 5
    assert "[" not in texte and texte == "A  B"


def test_doublons_et_borne():
    t = " ".join(["[POINT:rail.quick]"] * 3 + [f"[POINT:{a}]" for a in
                  ("rail.studio", "rail.news", "rail.montage", "rail.photolab", "rail.vectorlab", "rail.reglages")])
    _, actions, rejets = A.analyser(t)               # 7 ancres distinctes, bornées à MAX_ACTIONS = 6
    assert len(actions) == A.MAX_ACTIONS == 6 and rejets == 0
    assert [a["cible"] for a in actions].count("rail.quick") == 1 and "rail.reglages" not in [a["cible"] for a in actions]


def test_texte_hostile():
    # une balise ne peut pas porter de code ni de chemin : seuls les ids connus passent
    texte, actions, rejets = A.analyser('[POINT:<img src=x onerror=alert(1)>] [GUIDE:../../etc] [POINT:rail.quick')
    assert actions == [] and rejets == 2
    assert texte.endswith("[POINT:rail.quick")          # balise non fermée : laissée telle quelle, c'est du texte
    assert A.analyser(None) == ("", [], 0)
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY -m pytest tests/test_agent_aide.py -q`.
Attendu : 4 échecs, `has no attribute 'analyser'`.

- [ ] **Étape 3 : implémenter**

```python
import re

# toute balise MAJUSCULE entre crochets, avec ou sans cible : les connues deviennent des actions, les autres sont
# retirées (comptées) — l'écran ne voit jamais une balise
BALISE = re.compile(r"\[([A-Z]{2,8})(?::([^\[\]\n]{1,80}))?\]")
MAX_ACTIONS = 6


def _action(typ: str, cible: str) -> dict | None:
    k = connaissance()
    if typ == "POINT" and cible in k["ancres"]:
        a = k["ancres"][cible]
        return {"type": "point", "cible": cible, "ecran": a.get("ecran"), "selecteur": a.get("selecteur"),
                "texte": a.get("texte"), "cadre": a.get("cadre"), "reglages": a.get("reglages"),
                "fr": a["fr"], "en": a["en"]}
    if typ == "ALLER" and cible in VUES:
        return {"type": "aller", "cible": cible}
    if typ == "GUIDE" and cible in k["chapitres"]:
        c = k["chapitres"][cible]
        return {"type": "guide", "cible": cible, "fr": c["fr"], "en": c["en"]}
    return None


def analyser(texte) -> tuple[str, list, int]:
    """(texte sans balises, actions dédoublonnées ≤ MAX_ACTIONS, nombre de balises rejetées)."""
    actions, vus, rejets = [], set(), 0

    def remplacer(m):
        nonlocal rejets
        a = _action(m.group(1), (m.group(2) or "").strip())
        if a is None:
            rejets += 1
        elif (a["type"], a["cible"]) not in vus and len(actions) < MAX_ACTIONS:
            vus.add((a["type"], a["cible"]))
            actions.append(a)
        return ""

    propre = BALISE.sub(remplacer, str(texte or ""))
    propre = re.sub(r"[ \t]+\n", "\n", propre)
    propre = re.sub(r"\n{3,}", "\n\n", propre).strip()
    return propre, actions, rejets
```

Note : dans `test_texte_hostile`, `[POINT:<img src=x onerror=alert(1)>]` correspond à la regex et finit rejeté
(cible inconnue). `[GUIDE:../../etc]` est rejeté de la même façon. La balise non fermée ne correspond pas.

- [ ] **Étape 4 : lancer et voir réussir**

Lancer : `& $PY -m pytest tests/test_agent_aide.py -q`. Attendu : `6 passed`.

- [ ] **Étape 5 : commiter**

```bash
git commit --only backend/app/services/agent_aide.py backend/tests/test_agent_aide.py -m "agent : balises POINT/ALLER/GUIDE en actions, inconnues retirées (A2)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 6 : A2, le choix du moteur et `demander`

**Fichiers :** `backend/app/services/agent_aide.py`, `backend/app/services/plafonds.py:34-36`,
`backend/tests/test_agent_aide.py`

- [ ] **Étape 1 : ajouter les tests qui échouent**

```python
from app.services import moteurs_texte as MT                                 # noqa: E402
from app.services import plafonds as PLAF                                    # noqa: E402


def _faux_etat(*configures):
    return lambda: [{"moteur": m, "nom": m.title(), "configure": m in configures, "fautif": False}
                    for m in ("anthropic", "openai", "gemini", "ollama")]


def test_choix_du_moteur(monkeypatch):
    monkeypatch.setattr(MT, "etat", _faux_etat("ollama", "openai"))
    assert A.choisir_moteur() == "openai"                      # préférence anthropic > openai > gemini
    monkeypatch.setattr(MT, "etat", _faux_etat("ollama"))
    assert A.choisir_moteur() == "ollama"                      # sinon le premier configuré
    monkeypatch.setattr(MT, "etat", _faux_etat())
    assert A.choisir_moteur() == ""
    monkeypatch.setattr(MT, "connu", lambda m: m == "gemini")
    monkeypatch.setattr(MT, "configure", lambda m: m == "gemini")
    assert A.choisir_moteur("gemini") == "gemini" and A.choisir_moteur("inconnu") == ""


def test_categorie_aide():
    assert "aide" in PLAF.CATEGORIES


def test_demander_appelle_tirer_garde(monkeypatch):
    vu = {}

    async def faux(moteur, modele, prompt, systeme, max_tokens=4000, json=False, *, categorie="", **kw):
        vu.update(moteur=moteur, prompt=prompt, systeme=systeme, categorie=categorie, max_tokens=max_tokens)
        return "Va dans les Réglages.\n[POINT:reglages.cles]\n[POINT:invente]"

    monkeypatch.setattr(A, "choisir_moteur", lambda d="": "anthropic")
    monkeypatch.setattr(MT, "tirer_garde", faux)
    monkeypatch.setattr(A, "_espace", lambda: "Deepotus")
    r = asyncio.run(A.demander({"question": "  Où mettre ma clé ?  ", "ecran": "quick", "lang": "fr",
                                "historique": [{"role": "user", "texte": "bonjour"},
                                               {"role": "assistant", "texte": "Salut"}, {"role": "pirate"}]}))
    assert vu["categorie"] == "aide" and vu["moteur"] == "anthropic" and vu["max_tokens"] == A.MAX_TOKENS
    assert vu["prompt"].endswith("Nouvelle question : Où mettre ma clé ?")
    assert "Utilisateur : bonjour" in vu["prompt"] and "pirate" not in vu["prompt"]
    assert "écran ouvert : quick" in vu["systeme"] and "Deepotus" in vu["systeme"]
    assert r["texte"] == "Va dans les Réglages." and [a["cible"] for a in r["actions"]] == ["reglages.cles"]
    assert r["rejets"] == 1 and r["moteur"] == "anthropic"


def test_demander_sans_moteur_repond_sans_llm(monkeypatch):
    monkeypatch.setattr(A, "choisir_moteur", lambda d="": "")
    r = asyncio.run(A.demander({"question": "help", "lang": "en"}))
    assert r["sans_cle"] is True and r["moteur"] == ""
    assert r["actions"][0]["cible"] == "reglages.cles" and "key" in r["texte"].lower()


def test_demander_bornes():
    with pytest.raises(ValueError):
        asyncio.run(A.demander({"question": "   "}))
    with pytest.raises(ValueError):
        asyncio.run(A.demander("pas un objet"))
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY -m pytest tests/test_agent_aide.py -q`.
Attendu : échecs sur `choisir_moteur`, `"aide" in CATEGORIES` et `demander`.

- [ ] **Étape 3 : ajouter `"aide"` à `plafonds.CATEGORIES`**

Dans `backend/app/services/plafonds.py`, ligne 34 à 36 :

```python
CATEGORIES = ("quick", "studio", "chapitres", "son", "montage", "news", "scheduler", "bibliotheque", "sprites",
              "tuiles", "matieres", "cartes", "moteurs3d", "marketing", "atelier", "vectorlab", "reglages",
              "dictee", "direct", "photolab", "aide")
```

- [ ] **Étape 4 : implémenter dans `agent_aide.py`**

```python
from loguru import logger

MAX_QUESTION = 2000
MAX_HISTORIQUE = 10
MAX_TOUR = 1000
MAX_TOKENS = 900
PREFERENCE = ("anthropic", "openai", "gemini")
SANS_CLE = {
    "fr": "Aucun moteur de texte n'est branché : l'assistant a besoin d'une clé (Anthropic, OpenAI, Gemini) ou d'un "
          "serveur local. Ouvre les Réglages › Clés API, colle ta clé, puis repose ta question.",
    "en": "No text engine is connected: the assistant needs an API key (Anthropic, OpenAI, Gemini) or a local "
          "server. Open Settings › API keys, paste your key, then ask again.",
}


def choisir_moteur(demande: str = "") -> str:
    """Le moteur demandé s'il est connu ET configuré ; sans demande, le premier configuré dans PREFERENCE, puis le
    premier configuré tout court ; "" si aucun. Jamais de repli d'un moteur demandé vers un autre."""
    from app.services import moteurs_texte as MT
    if demande:
        return demande if MT.connu(demande) and MT.configure(demande) else ""
    lignes = [l["moteur"] for l in MT.etat() if l["configure"] and not l.get("fautif")]
    for p in PREFERENCE:
        if p in lignes:
            return p
    return lignes[0] if lignes else ""


def _espace() -> str:
    try:
        from app.services import espaces as ES
        return str(ES.actif().get("nom") or "")
    except Exception:  # noqa: BLE001 — l'espace n'est qu'un contexte : son absence ne bloque pas l'aide
        return ""


def _historique(h) -> str:
    if not isinstance(h, list):
        return ""
    lignes = []
    for t in h[-MAX_HISTORIQUE:]:
        if isinstance(t, dict) and t.get("role") in ("user", "assistant") and isinstance(t.get("texte"), str):
            qui = "Utilisateur" if t["role"] == "user" else "Assistant"
            lignes.append(f"{qui} : {t['texte'].strip()[:MAX_TOUR]}")
    return ("Échange précédent :\n" + "\n".join(lignes) + "\n\nNouvelle question : ") if lignes \
        else "Nouvelle question : "


async def demander(corps, lang: str = "fr") -> dict:
    """{texte, actions, moteur, nom, rejets, sans_cle}. ValueError : corps ou question invalides. RuntimeError :
    le moteur a échoué. HTTPException 402 : plafond « aide » (remonte tel quel jusqu'au dialogue de l'écran)."""
    from app.services import moteurs_texte as MT
    if not isinstance(corps, dict):
        raise ValueError("Corps JSON attendu.")
    q = corps.get("question")
    q = q.strip()[:MAX_QUESTION] if isinstance(q, str) else ""
    if not q:
        raise ValueError("La question est vide.")
    lang = "en" if (corps.get("lang") or lang) == "en" else "fr"
    ecran = corps.get("ecran") if corps.get("ecran") in VUES else ""
    demande = corps.get("moteur").strip() if isinstance(corps.get("moteur"), str) else ""
    moteur = choisir_moteur(demande)
    if not moteur:
        _, actions, _ = analyser("[POINT:reglages.cles] [GUIDE:cles]")
        return {"texte": SANS_CLE[lang], "actions": actions, "moteur": "", "nom": "", "rejets": 0, "sans_cle": True}
    sortie = await MT.tirer_garde(moteur, "", _historique(corps.get("historique")) + q,
                                  systeme(ecran, lang, _espace()), MAX_TOKENS, categorie="aide")
    texte, actions, rejets = analyser(sortie)
    if rejets:
        logger.info(f"agent_aide : {rejets} balise(s) inconnue(s) retirée(s) ({moteur})")
    return {"texte": texte, "actions": actions, "moteur": moteur, "nom": MT.nom(moteur), "rejets": rejets,
            "sans_cle": False}


def etat() -> dict:
    from app.services import moteurs_texte as MT
    k = connaissance()
    moteurs = [{"moteur": l["moteur"], "nom": l["nom"], "cout": MT.nature_cout(l["moteur"])}
               for l in MT.etat() if l["configure"] and not l.get("fautif")]
    return {"moteur": choisir_moteur(), "moteurs": moteurs, "ancres": len(k["ancres"]),
            "chapitres": len(k["chapitres"])}
```

- [ ] **Étape 5 : lancer et voir réussir**

Lancer : `& $PY -m pytest tests/test_agent_aide.py -q`. Attendu : `11 passed`.
Lancer aussi : `& $PY tests/test_avatar_live_socle.py`. Ce banc vérifie `CATEGORIES` ; attendu : aucun FAIL.

- [ ] **Étape 6 : commiter**

```bash
git commit --only backend/app/services/agent_aide.py backend/app/services/plafonds.py backend/tests/test_agent_aide.py -m "agent : choix du moteur, demander sous le plafond « aide » (A2)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 7 : A2, les routes `/api/agent`

**Fichiers :**
- Créer : `backend/app/api/agent_routes.py`
- Modifier : `backend/app/main.py` (après la ligne 492, `app.include_router(motion_biblio_router, …)`)
- Banc : `backend/tests/test_agent_aide.py`

- [ ] **Étape 1 : ajouter les tests qui échouent et le lanceur**

```python
from fastapi.testclient import TestClient                                   # noqa: E402


def _client():
    from app.main import app
    return TestClient(app)


def test_route_etat(monkeypatch):
    monkeypatch.setattr(MT, "etat", _faux_etat("anthropic"))
    r = _client().get("/api/agent/etat")
    assert r.status_code == 200
    j = r.json()
    assert j["moteur"] == "anthropic" and j["ancres"] >= 25 and j["chapitres"] >= 40


def test_route_demander(monkeypatch):
    async def faux(corps, lang="fr"):
        return {"texte": f"ok {lang}", "actions": [], "moteur": "x", "nom": "X", "rejets": 0, "sans_cle": False}
    monkeypatch.setattr(A, "demander", faux)
    c = _client()
    r = c.post("/api/agent/demander", json={"question": "q"}, headers={"Accept-Language": "en"})
    assert r.status_code == 200 and r.json()["texte"] == "ok en"
    assert c.post("/api/agent/demander", content="pas du json",
                  headers={"Content-Type": "application/json"}).status_code == 400


def test_route_erreurs(monkeypatch):
    async def vide(corps, lang="fr"):
        raise ValueError("La question est vide.")

    async def panne(corps, lang="fr"):
        raise RuntimeError("moteur en panne")
    c = _client()
    monkeypatch.setattr(A, "demander", vide)
    assert c.post("/api/agent/demander", json={}).status_code == 400
    monkeypatch.setattr(A, "demander", panne)
    r = c.post("/api/agent/demander", json={"question": "q"})
    assert r.status_code == 502 and "panne" in r.json()["detail"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY tests/test_agent_aide.py`. Attendu : 404 sur `/api/agent/etat`.

- [ ] **Étape 3 : écrire `backend/app/api/agent_routes.py`**

```python
# -*- coding: utf-8 -*-
"""Assistant « Demander à Deepotus » (spec 2026-10-19-agent-aide-design.md, 19/10/2026) — /api/agent.

Boucle locale SEULEMENT, comme les Réglages : la question part vers le moteur de texte de l'utilisateur, sous le
plafond « aide » (le 402 `dz_plafond` remonte tel quel jusqu'au dialogue de /shared/dz-plafonds.js).
"""
from fastapi import APIRouter, HTTPException, Request

from app.services import agent_aide as A

router = APIRouter()

_HOTES_LOCAUX = ("127.0.0.1", "::1", "localhost", "testclient")


def _local(request: Request) -> None:
    host = (request.client.host if request.client else "") or ""
    if host not in _HOTES_LOCAUX:
        raise HTTPException(403, "L'assistant n'est accessible que depuis ce PC.")


@router.get("/etat")
async def etat(request: Request):
    _local(request)
    return A.etat()


@router.post("/demander")
async def demander(request: Request):
    _local(request)
    try:
        corps = await request.json()
    except ValueError:
        raise HTTPException(400, "Corps JSON attendu.") from None
    from app.i18n import langue_requete
    try:
        return await A.demander(corps, langue_requete(request))
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from None
```

- [ ] **Étape 4 : enregistrer le routeur dans `backend/app/main.py`**, juste après la ligne
  `app.include_router(motion_biblio_router, prefix="/api/motion")` :

```python
# Assistant « Demander à Deepotus » (19/10/2026) : /api/agent/etat, /api/agent/demander — aide à l'usage de l'app
from app.api.agent_routes import router as agent_router
app.include_router(agent_router, prefix="/api/agent")
```

- [ ] **Étape 5 : lancer et voir réussir**

Lancer : `& $PY tests/test_agent_aide.py`. Attendu : `14 passed`.
Lancer : `& $PY tests/test_plafonds_garde.py`. Attendu : aucun FAIL. Le recensement ne voit pas `agent_routes`, qui
appelle un service ; la garde est prouvée par `test_demander_appelle_tirer_garde`, comme pour la chorégraphie
motion.
Lancer : `& $PY tests/test_hygiene_lanceurs.py`. Attendu : aucun FAIL.

- [ ] **Étape 6 : commiter**

```bash
git add backend/app/api/agent_routes.py
git commit --only backend/app/api/agent_routes.py backend/app/main.py backend/tests/test_agent_aide.py -m "agent : routes /api/agent/etat et /api/agent/demander (A2)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 8 : A3, la logique pure de l'écran

**Fichiers :**
- Créer : `frontend/shared/dz-agent-logique.js`
- Banc : `frontend/shared/qa/agent_logique.test.mjs`

- [ ] **Étape 1 : écrire le banc qui échoue**

```js
// Assistant (spec 2026-10-19-agent-aide-design.md) — /shared/dz-agent-logique.js : la logique PURE du tiroir et du
// pointeur (aucun DOM à l'import) : choix de l'élément d'une ancre, composition cadre + intérieur, courbe du
// curseur, étapes d'une action, historique borné.
// Lancer : node frontend/shared/qa/agent_logique.test.mjs
import assert from "node:assert/strict";
import * as L from "../dz-agent-logique.js";

// 1. choisir l'élément parmi les candidats (texte ou title, exact d'abord, visibles seulement)
const C = [
  { texte: "Quick  ", titre: "", visible: true },
  { texte: "Studio nouveau", titre: "", visible: true },
  { texte: "", titre: "Montage", visible: true },
  { texte: "Réglages", titre: "", visible: false },
];
assert.equal(L.choisir(C, { texte: { fr: "Quick", en: "Quick" } }, "fr"), 0);
assert.equal(L.choisir(C, { texte: { fr: "Studio", en: "Studio" } }, "fr"), 1, "contient, à défaut d'exact");
assert.equal(L.choisir(C, { texte: { fr: "Montage", en: "Montage" } }, "en"), 2, "le title compte (rail replié)");
assert.equal(L.choisir(C, { texte: { fr: "Réglages", en: "Settings" } }, "fr"), -1, "invisible : ignoré");
assert.equal(L.choisir(C, {}, "fr"), 0, "sans texte : le premier visible");
assert.equal(L.choisir([], { texte: { fr: "x", en: "x" } }, "fr"), -1);
assert.equal(L.choisir(C, { texte: { fr: "quick", en: "Quick" } }, "fr"), 0, "casse et espaces ignorés");

// 2. composer un rectangle trouvé dans un cadre
assert.deepEqual(L.composer({ x: 100, y: 50 }, { x: 10, y: 20, w: 30, h: 40 }), { x: 110, y: 70, w: 30, h: 40 });
assert.equal(L.composer({ x: 0, y: 0 }, null), null);

// 3. courbe : départ à t=0, arrivée à t=1, et un vrai arc au milieu
const a = { x: 0, y: 0 }, b = { x: 400, y: 0 };
assert.deepEqual(L.courbe(a, b, 0), a);
assert.deepEqual(L.courbe(a, b, 1), b);
const m = L.courbe(a, b, 0.5);
assert.ok(Math.abs(m.x - 200) < 1e-9 && Math.abs(m.y) > 40, "l'arc s'écarte de la ligne droite");
assert.deepEqual(L.courbe(a, a, 0.5), a, "départ = arrivée : aucun NaN");

// 4. étapes d'une action selon l'écran courant
assert.deepEqual(L.etapes({ type: "aller", cible: "montage" }, "quick"), [{ faire: "aller", vue: "montage" }]);
assert.deepEqual(L.etapes({ type: "point", ecran: "settings", reglages: "keys" }, "quick"),
  [{ faire: "aller", vue: "settings" }, { faire: "reglages", section: "keys" }]);
assert.deepEqual(L.etapes({ type: "point", ecran: "montage", selecteur: "b" }, "montage"), [{ faire: "pointer" }]);
assert.deepEqual(L.etapes({ type: "point", ecran: "vectorlab", selecteur: "b" }, "quick"),
  [{ faire: "aller", vue: "vectorlab" }, { faire: "pointer" }]);
assert.deepEqual(L.etapes({ type: "point", ecran: null, selecteur: "button.dzNavItem" }, "news"), [{ faire: "pointer" }]);
assert.deepEqual(L.etapes({ type: "guide", cible: "quick" }, "news"), [{ faire: "guide", chapitre: "quick" }]);
assert.deepEqual(L.etapes({ type: "aller", cible: "../x" }, "news"), [], "vue inconnue : rien");
assert.deepEqual(L.etapes({ type: "guide", cible: "a/b" }, "news"), [], "chapitre au format douteux : rien");

// 5. historique borné aux 10 derniers tours, rôles valides seulement
const h = Array.from({ length: 14 }, (_, i) => ({ role: i % 2 ? "assistant" : "user", texte: "t" + i }));
h.push({ role: "pirate", texte: "x" });
const b2 = L.historiqueBorne(h);
assert.equal(b2.length, 10);
assert.equal(b2[9].texte, "t13");

// 6. le module n'utilise aucun objet du navigateur à l'import
assert.equal(typeof globalThis.document, "undefined");
console.log("agent_logique : OK");
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `node frontend/shared/qa/agent_logique.test.mjs`.
Attendu : `ERR_MODULE_NOT_FOUND ... dz-agent-logique.js`.

- [ ] **Étape 3 : écrire `frontend/shared/dz-agent-logique.js`**

```js
// dz-agent-logique.js — assistant « Demander à Deepotus » (spec docs/superpowers/specs/2026-10-19-agent-aide-design.md,
// 19/10/2026) : la logique PURE du tiroir (/shared/dz-agent.js) et du répondeur des labs (/shared/dz-agent-cadre.js).
// Module ES sans DOM ni window à l'import (banc node frontend/shared/qa/agent_logique.test.mjs).
// Servi à l'identique depuis frontend/dist/shared/ (/shared/…).

export const VUES = ["quick", "studio", "episodes", "sonvfx", "montage", "scheduler", "templates", "news", "library",
  "assets3d", "vectorlab", "photolab", "avatarlive", "settings"];
export const MAX_HISTORIQUE = 10;

const norm = (s) => String(s || "").replace(/\s+/g, " ").trim().toLowerCase();

// candidats : [{texte, titre, visible}] dans l'ordre du document ; rend l'index choisi ou -1
export function choisir(candidats, ancre, lang) {
  const vis = (candidats || []).map((c, i) => ({ ...c, i })).filter((c) => c.visible);
  const t = ancre && ancre.texte ? norm(ancre.texte[lang] || ancre.texte.fr) : "";
  if (!t) return vis.length ? vis[0].i : -1;
  const exact = vis.find((c) => norm(c.texte) === t || norm(c.titre) === t);
  if (exact) return exact.i;
  const proche = vis.find((c) => norm(c.texte).includes(t) || norm(c.titre).includes(t));
  return proche ? proche.i : -1;
}

// un rectangle relevé DANS un cadre intégré → coordonnées de la page
export function composer(cadre, interne) {
  if (!cadre || !interne) return null;
  return { x: cadre.x + interne.x, y: cadre.y + interne.y, w: interne.w, h: interne.h };
}

// Bézier quadratique : le point de contrôle s'écarte perpendiculairement de 30 % de la distance (≤ 160 px)
export function courbe(a, b, t) {
  const dx = b.x - a.x, dy = b.y - a.y;
  const d = Math.hypot(dx, dy);
  if (!d) return { x: a.x, y: a.y };
  const ecart = Math.min(160, d * 0.3);
  const c = { x: (a.x + b.x) / 2 - (dy / d) * ecart, y: (a.y + b.y) / 2 + (dx / d) * ecart };
  const u = 1 - t;
  return { x: u * u * a.x + 2 * u * t * c.x + t * t * b.x, y: u * u * a.y + 2 * u * t * c.y + t * t * b.y };
}

// ce que l'écran doit faire, dans l'ordre, pour une action rendue par /api/agent/demander
export function etapes(action, vueCourante) {
  if (!action) return [];
  if (action.type === "aller") return VUES.includes(action.cible) ? [{ faire: "aller", vue: action.cible }] : [];
  if (action.type === "guide") return /^[a-z0-9-]+$/.test(action.cible || "") ? [{ faire: "guide", chapitre: action.cible }] : [];
  if (action.type !== "point") return [];
  const out = [];
  if (action.ecran && VUES.includes(action.ecran) && action.ecran !== vueCourante) out.push({ faire: "aller", vue: action.ecran });
  if (action.reglages) out.push({ faire: "reglages", section: action.reglages });
  else out.push({ faire: "pointer" });
  return out;
}

export function historiqueBorne(h) {
  return (Array.isArray(h) ? h : [])
    .filter((t) => t && (t.role === "user" || t.role === "assistant") && typeof t.texte === "string")
    .slice(-MAX_HISTORIQUE);
}
```

Attention, le cas `{type:"point", ecran:"settings", reglages:"keys"}` vu depuis `quick` donne bien
`[aller settings, reglages keys]`. Le même cas vu depuis `settings` donne `[reglages keys]`.

- [ ] **Étape 4 : lancer et voir réussir**

Lancer : `node frontend/shared/qa/agent_logique.test.mjs`. Attendu : `agent_logique : OK`.

- [ ] **Étape 5 : commiter**

```bash
git add frontend/shared/dz-agent-logique.js frontend/shared/qa/agent_logique.test.mjs
git commit --only frontend/shared/dz-agent-logique.js frontend/shared/qa/agent_logique.test.mjs -m "agent : logique pure du tiroir et du pointeur (A3)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 9 : A3, les libellés FR et EN

**Fichiers :**
- Créer : `frontend/shared/i18n/agent.json`
- Régénérer : `frontend/shared/dz-i18n-dico.js` et sa copie dist (par l'assembleur)
- Banc : `backend/tests/test_agent_ecran.py`

- [ ] **Étape 1 : écrire le banc qui échoue**

```python
# -*- coding: utf-8 -*-
"""A3/A4 (spec 2026-10-19-agent-aide-design.md) — l'écran de l'assistant : libellés FR/EN complets et employés,
copies dist identiques, balises dans la SPA et dans les labs, banc node de la logique pure.
Run : & $PY tests/test_agent_ecran.py   (depuis backend/)"""
import json, pathlib, re, shutil, subprocess, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
SHARED = RACINE / "frontend" / "shared"
DIST = RACINE / "frontend" / "dist" / "shared"
I18N = json.loads((SHARED / "i18n" / "agent.json").read_text(encoding="utf-8"))


def test_libelles_complets():
    assert len(I18N) >= 14
    for k, v in I18N.items():
        assert k.startswith("agent."), k
        assert v.get("fr") and v.get("en"), k


def test_dictionnaire_assemble():
    dico = (SHARED / "dz-i18n-dico.js").read_text(encoding="utf-8")
    for k in I18N:
        assert f'"{k}"' in dico, k


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY tests/test_agent_ecran.py`. Attendu : `FileNotFoundError ... agent.json`.

- [ ] **Étape 3 : écrire `frontend/shared/i18n/agent.json`**

```json
{
  "agent.bouton": {"fr": "Demander", "en": "Ask"},
  "agent.bouton_titre": {"fr": "Demander à Deepotus (F1)", "en": "Ask Deepotus (F1)"},
  "agent.titre": {"fr": "Demander à Deepotus", "en": "Ask Deepotus"},
  "agent.accueil": {"fr": "Pose ta question sur l'application : je t'explique en quelques étapes et je te montre où cliquer.", "en": "Ask anything about the app: I'll explain in a few steps and show you where to click."},
  "agent.placeholder": {"fr": "Comment je… ?", "en": "How do I…?"},
  "agent.envoyer": {"fr": "Envoyer", "en": "Send"},
  "agent.fermer": {"fr": "Fermer", "en": "Close"},
  "agent.nouvelle": {"fr": "Nouvelle conversation", "en": "New conversation"},
  "agent.moteur": {"fr": "Moteur", "en": "Engine"},
  "agent.moteur_auto": {"fr": "Automatique", "en": "Automatic"},
  "agent.reflechit": {"fr": "Je cherche…", "en": "Looking…"},
  "agent.montrer": {"fr": "Montre-moi : {libelle}", "en": "Show me: {libelle}"},
  "agent.aller": {"fr": "Y aller", "en": "Go there"},
  "agent.guide": {"fr": "Guide : {titre}", "en": "Guide: {titre}"},
  "agent.introuvable": {"fr": "Je ne trouve pas ce bouton sur cet écran. Le chapitre du guide t'aidera.", "en": "I can't find this button on this screen. The guide chapter will help."},
  "agent.erreur": {"fr": "La réponse n'est pas arrivée : {msg}", "en": "No answer came back: {msg}"},
  "agent.cout_gratuit": {"fr": "gratuit", "en": "free"},
  "agent.cout_payant": {"fr": "payant, sous le plafond « aide »", "en": "paid, under the \"help\" cap"}
}
```

- [ ] **Étape 4 : assembler le dictionnaire**

Lancer : `& $PY scripts/i18n_assembler.py` (depuis la racine du worktree). L'assembleur écrit
`frontend/shared/dz-i18n-dico.js` et sa copie `frontend/dist/shared/dz-i18n-dico.js`. Vérifier ensuite avec
`git diff --stat` que seuls ces deux fichiers ont changé.

- [ ] **Étape 5 : lancer et voir réussir**

Lancer : `& $PY tests/test_agent_ecran.py`. Attendu : `2 passed`.
Lancer : `& $PY tests/test_i18n_l0.py`. Attendu : aucun FAIL (dictionnaire et copie identiques).

- [ ] **Étape 6 : commiter**

```bash
git add frontend/shared/i18n/agent.json backend/tests/test_agent_ecran.py
git commit --only frontend/shared/i18n/agent.json frontend/shared/dz-i18n-dico.js frontend/dist/shared/dz-i18n-dico.js backend/tests/test_agent_ecran.py -m "agent : libellés FR/EN du tiroir (A3)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 10 : A3, le tiroir `dz-agent.js`

**Fichiers :**
- Créer : `frontend/shared/dz-agent.js`, ainsi que les copies `frontend/dist/shared/dz-agent.js` et
  `frontend/dist/shared/dz-agent-logique.js`
- Modifier : `frontend/dist/index.html` (après la ligne 51, `<script src="/shared/dz-champ-ia.js"></script>`)
- Banc : `backend/tests/test_agent_ecran.py`

- [ ] **Étape 1 : ajouter les tests qui échouent** (avant le lanceur)

```python
FICHIERS = ["dz-agent.js", "dz-agent-logique.js"]
BALISE_SPA = '<script type="module" src="/shared/dz-agent.js"></script>'


def test_copies_dist_identiques():
    for f in FICHIERS:
        assert (SHARED / f).read_bytes() == (DIST / f).read_bytes(), f


def test_balise_dans_la_spa():
    html = (RACINE / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
    assert html.count(BALISE_SPA) == 1
    assert html.index("/shared/dz-plafonds.js") < html.index(BALISE_SPA), "après la couche des plafonds"


def test_cles_employees_existent():
    src = (SHARED / "dz-agent.js").read_text(encoding="utf-8")
    employees = set(re.findall(r'T\("(agent\.[a-z_]+)"', src))
    assert employees, "le tiroir passe par T(…)"
    assert employees <= set(I18N), employees - set(I18N)
    assert not re.search(r">[A-ZÀ-Ý][a-zà-ÿ]{3,}[^<]*<", src), "aucun texte visible en dur dans le HTML généré"


def test_banc_node_logique():
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent")
    r = subprocess.run([node, str(SHARED / "qa" / "agent_logique.test.mjs")], capture_output=True, text=True,
                       encoding="utf-8")
    assert r.returncode == 0 and "OK" in r.stdout, r.stderr[-800:]
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY tests/test_agent_ecran.py`. Attendu : FAIL sur les copies et la balise.

- [ ] **Étape 3 : écrire `frontend/shared/dz-agent.js`**

Le fichier contient le tiroir, F1, les appels et les actions. Le pointeur est ajouté à la tâche 11 ; ici, l'action
« pointer » ne fait qu'un défilement jusqu'à l'élément, pour livrer un tiroir utilisable dès cette tâche.

```js
// dz-agent.js — assistant « Demander à Deepotus » (spec docs/superpowers/specs/2026-10-19-agent-aide-design.md,
// 19/10/2026). SOURCE : frontend/shared/dz-agent.js ; copie OCTET POUR OCTET : frontend/dist/shared/dz-agent.js,
// chargée par frontend/dist/index.html (`<script type="module">`, après dz-plafonds.js). Aucune dépendance au runtime
// React : le tiroir vit à côté de la SPA. Le banc backend/tests/test_agent_ecran.py vérifie copies, balise et libellés.
//
// Le tiroir : bouton flottant « Demander » + F1 ; POST /api/agent/demander {question, historique, ecran, lang,
// moteur} ; sous chaque réponse, un bouton par action (Montre-moi / Y aller / Guide). L'historique reste dans
// sessionStorage (dz_agent_hist) ; le moteur choisi dans localStorage (dz_agent_moteur). Un 402 `dz_plafond` est
// traité par la couche /shared/dz-plafonds.js (elle enveloppe window.fetch) : rien à faire ici.
import { etapes, historiqueBorne, choisir } from "./dz-agent-logique.js";

if (!window.__dzAgent) {
  window.__dzAgent = true;

  const T = (k, v) => (window.dzT ? window.dzT(k, v) : k);
  const lang = () => (window.dzLang === "en" ? "en" : "fr");
  const lire = (s, k) => { try { return s.getItem(k); } catch (e) { return null; } };
  const ecrire = (s, k, v) => { try { s.setItem(k, v); } catch (e) { /* stockage indisponible : rien de grave */ } };
  const vue = () => lire(window.localStorage, "dz_view") || "quick";
  const el = (tag, attrs, enfants) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "on") for (const [e, f] of Object.entries(v)) n.addEventListener(e, f);
      else if (k === "texte") n.textContent = v;
      else n.setAttribute(k, v);
    }
    for (const c of enfants || []) n.appendChild(c);
    return n;
  };

  let hist = [];
  try { hist = historiqueBorne(JSON.parse(lire(window.sessionStorage, "dz_agent_hist") || "[]")); } catch (e) { hist = []; }
  const garder = () => ecrire(window.sessionStorage, "dz_agent_hist", JSON.stringify(historiqueBorne(hist)));

  const css = el("style", { texte: `
.dzAgentBtn{position:fixed;right:18px;bottom:18px;z-index:2147483000;border:1px solid var(--cyan,#3ee6d0);
 background:var(--panel,#0e1422);color:var(--ink-strong,#eaf2ff);border-radius:999px;padding:8px 14px;font-family:inherit;font-size:13px;font-weight:600;line-height:1;
 cursor:pointer;box-shadow:0 0 18px rgba(62,230,208,.25)}
.dzAgentTiroir{position:fixed;top:0;right:0;bottom:0;width:min(400px,100vw);z-index:2147483001;display:none;flex-direction:column;
 background:var(--panel,#0e1422);color:var(--ink,#c9d4e8);border-left:1px solid var(--line,#24304a);font-family:inherit;font-size:13px;line-height:1.5}
.dzAgentTiroir[data-ouvert="1"]{display:flex}
.dzAgentTete{display:flex;align-items:center;gap:8px;padding:12px 14px;border-bottom:1px solid var(--line,#24304a)}
.dzAgentTete h2{flex:1;margin:0;font-size:14px;color:var(--ink-strong,#eaf2ff)}
.dzAgentFil{flex:1;overflow:auto;padding:12px 14px;display:flex;flex-direction:column;gap:10px}
.dzAgentMsg{white-space:pre-wrap;border-radius:10px;padding:8px 10px;background:var(--panel-2,#141c2e)}
.dzAgentMsg[data-role="user"]{align-self:flex-end;background:var(--cyan-soft,rgba(62,230,208,.12))}
.dzAgentActions{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.dzAgentActions button,.dzAgentTete button,.dzAgentPied button{background:transparent;color:inherit;border:1px solid var(--line,#24304a);
 border-radius:8px;padding:4px 8px;cursor:pointer;font:inherit}
.dzAgentPied{display:flex;gap:6px;padding:10px 14px;border-top:1px solid var(--line,#24304a)}
.dzAgentPied textarea{flex:1;resize:none;min-height:38px;background:var(--panel-2,#141c2e);color:inherit;border:1px solid var(--line,#24304a);border-radius:8px;padding:6px}
.dzAgentTete select{background:var(--panel-2,#141c2e);color:inherit;border:1px solid var(--line,#24304a);border-radius:6px}` });

  const fil = el("div", { class: "dzAgentFil", role: "log", "aria-live": "polite" });
  const saisie = el("textarea", { placeholder: T("agent.placeholder"), "aria-label": T("agent.placeholder") });
  const choix = el("select", { "aria-label": T("agent.moteur"), title: T("agent.moteur") });
  const tiroir = el("aside", { class: "dzAgentTiroir", "aria-label": T("agent.titre") }, [
    el("div", { class: "dzAgentTete" }, [
      el("h2", { texte: T("agent.titre") }), choix,
      el("button", { texte: "↺", title: T("agent.nouvelle"), "aria-label": T("agent.nouvelle"),
        on: { click: () => { hist = []; garder(); dessiner(); } } }),
      el("button", { texte: "×", title: T("agent.fermer"), "aria-label": T("agent.fermer"), on: { click: () => basculer(false) } }),
    ]),
    fil,
    el("div", { class: "dzAgentPied" }, [saisie, el("button", { texte: T("agent.envoyer"), on: { click: () => envoyer() } })]),
  ]);
  const bouton = el("button", { class: "dzAgentBtn", texte: "? " + T("agent.bouton"), title: T("agent.bouton_titre"),
    on: { click: () => basculer() } });

  function basculer(ouvrir) {
    const o = ouvrir === undefined ? tiroir.dataset.ouvert !== "1" : ouvrir;
    tiroir.dataset.ouvert = o ? "1" : "0";
    if (o) { chargerMoteurs(); saisie.focus(); }
  }

  async function chargerMoteurs() {
    if (choix.dataset.charge) return;
    choix.dataset.charge = "1";
    try {
      const r = await fetch("/api/agent/etat");
      const j = await r.json();
      choix.replaceChildren(el("option", { value: "", texte: T("agent.moteur_auto") }),
        ...j.moteurs.map((m) => el("option", { value: m.moteur,
          texte: `${m.nom} · ${T(m.cout === "gratuit" ? "agent.cout_gratuit" : "agent.cout_payant")}` })));
      choix.value = lire(window.localStorage, "dz_agent_moteur") || "";
    } catch (e) { delete choix.dataset.charge; }
  }
  choix.addEventListener("change", () => ecrire(window.localStorage, "dz_agent_moteur", choix.value));

  function boutonAction(a) {
    const l = lang();
    const libelle = a.type === "point" ? T("agent.montrer", { libelle: a[l] || a.fr })
      : a.type === "guide" ? T("agent.guide", { titre: a[l] || a.fr }) : T("agent.aller");
    return el("button", { texte: libelle, on: { click: () => executer(a) } });
  }

  function dessiner(enAttente) {
    const msgs = hist.length ? hist : [{ role: "assistant", texte: T("agent.accueil") }];
    fil.replaceChildren(...msgs.map((m) => {
      const b = el("div", { class: "dzAgentMsg", "data-role": m.role, texte: m.texte });
      if (m.actions && m.actions.length) b.appendChild(el("div", { class: "dzAgentActions" }, m.actions.map(boutonAction)));
      return b;
    }));
    if (enAttente) fil.appendChild(el("div", { class: "dzAgentMsg", "data-role": "assistant", texte: T("agent.reflechit") }));
    fil.scrollTop = fil.scrollHeight;
  }

  async function envoyer() {
    const q = saisie.value.trim();
    if (!q) return;
    saisie.value = "";
    const avant = historiqueBorne(hist).map(({ role, texte }) => ({ role, texte }));
    hist.push({ role: "user", texte: q });
    dessiner(true);
    try {
      const r = await fetch("/api/agent/demander", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, historique: avant, ecran: vue(), lang: lang(), moteur: choix.value || "" }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : String(r.status));
      hist.push({ role: "assistant", texte: j.texte, actions: j.actions || [] });
    } catch (e) {
      hist.push({ role: "assistant", texte: T("agent.erreur", { msg: e.message }) });
      saisie.value = q;
    }
    garder();
    dessiner();
  }

  // ── les actions (le pointeur arrive à la tâche 11) ──
  const attendre = (ms) => new Promise((ok) => setTimeout(ok, ms));
  function aller(v) { window.dispatchEvent(new CustomEvent("deepotus:navigate", { detail: { view: v } })); }
  function ouvrirReglages(section) {
    try { const u = new URL(window.location.href); u.searchParams.set("section", section); window.history.replaceState(null, "", u); } catch (e) { /* URL non modifiable : l'événement suffit */ }
    window.dispatchEvent(new CustomEvent("dz-reglages-section", { detail: { section } }));
  }
  function candidats(doc, selecteur) {
    let n = [];
    try { n = Array.from(doc.querySelectorAll(selecteur)); } catch (e) { n = []; }
    return n.map((x) => {
      const r = x.getBoundingClientRect();
      return { noeud: x, texte: x.textContent, titre: x.getAttribute("title") || "", visible: r.width > 0 && r.height > 0 };
    });
  }
  async function trouver(a, delaiMs) {
    const fin = Date.now() + delaiMs;
    do {
      const c = candidats(document, a.selecteur);
      const i = choisir(c, a, lang());
      if (i >= 0) return c[i].noeud;
      await attendre(150);
    } while (Date.now() < fin);
    return null;
  }
  async function pointer(a) {
    const n = await trouver(a, 4000);
    if (!n) { hist.push({ role: "assistant", texte: T("agent.introuvable") }); garder(); dessiner(); return; }
    n.scrollIntoView({ block: "center", behavior: "smooth" });
  }
  async function executer(a) {
    for (const e of etapes(a, vue())) {
      if (e.faire === "aller") { aller(e.vue); await attendre(350); }
      else if (e.faire === "reglages") ouvrirReglages(e.section);
      else if (e.faire === "guide") window.open("/guide/#" + e.chapitre, "_blank", "noopener");
      else if (e.faire === "pointer") await pointer(a);
    }
  }
  window.__dzAgentExecuter = executer;     // pour la tâche 11 et les preuves

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "F1") { ev.preventDefault(); basculer(); }
    else if (ev.key === "Escape" && tiroir.dataset.ouvert === "1") basculer(false);
    else if (ev.key === "Enter" && !ev.shiftKey && ev.target === saisie) { ev.preventDefault(); envoyer(); }
  });

  const monter = () => { document.head.appendChild(css); document.body.append(bouton, tiroir); dessiner(); };
  if (document.body) monter(); else document.addEventListener("DOMContentLoaded", monter);
}
```

- [ ] **Étape 4 : ajouter la balise dans `frontend/dist/index.html`**, juste après
  `<script src="/shared/dz-champ-ia.js"></script>` (ligne 51) :

```html
    <script type="module" src="/shared/dz-agent.js"></script>
```

- [ ] **Étape 5 : copier dans dist**

```bash
cp frontend/shared/dz-agent.js frontend/dist/shared/dz-agent.js
cp frontend/shared/dz-agent-logique.js frontend/dist/shared/dz-agent-logique.js
```

- [ ] **Étape 6 : lancer et voir réussir**

Lancer : `& $PY tests/test_agent_ecran.py`. Attendu : `6 passed`.
Lancer : `& $PY tests/test_p2_plafonds_ecran.py`. Attendu : aucun FAIL (ce banc lit aussi `dist/index.html`).

- [ ] **Étape 7 : vérifier à l'écran sur le backend de preuve**

1. Lancer `& $PY scripts/guide/serve_guide.py` en arrière-plan.
2. Ouvrir `http://127.0.0.1:8809/` dans le navigateur intégré.
3. Appuyer sur F1 : le tiroir s'ouvre et affiche le message d'accueil.
4. Poser « où mettre ma clé ? ». Le backend de preuve n'a aucune clé, donc la réponse est celle de `SANS_CLE` avec
   les boutons « Montre-moi : Réglages › Clés API » et « Guide : … ».
5. Cliquer « Montre-moi » : l'écran Réglages s'ouvre sur la section Clés API.
6. `read_console_messages` ne doit montrer aucune erreur.
7. Faire une capture d'écran.

- [ ] **Étape 8 : commiter**

```bash
git add frontend/shared/dz-agent.js frontend/dist/shared/dz-agent.js frontend/dist/shared/dz-agent-logique.js
git commit --only frontend/shared/dz-agent.js frontend/dist/shared/dz-agent.js frontend/dist/shared/dz-agent-logique.js frontend/dist/index.html backend/tests/test_agent_ecran.py -m "agent : tiroir « Demander » (F1), actions Y aller / Réglages / Guide (A3)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 11 : A4, le pointeur

**Fichiers :** `frontend/shared/dz-agent.js` (et sa copie dist), `backend/tests/test_agent_ecran.py`

- [ ] **Étape 1 : ajouter le test qui échoue**

```python
def test_pointeur_present():
    src = (SHARED / "dz-agent.js").read_text(encoding="utf-8")
    assert "courbe(" in src and "dzAgentCurseur" in src and "dzAgentHalo" in src
    assert "prefers-reduced-motion" in src, "le mouvement réduit saute l'animation"
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY tests/test_agent_ecran.py`. Attendu : FAIL `test_pointeur_present`.

- [ ] **Étape 3 : implémenter dans `dz-agent.js`**

a) Remplacer la ligne d'import par :

```js
import { etapes, historiqueBorne, choisir, courbe } from "./dz-agent-logique.js";
```

b) Ajouter au CSS (dans le gabarit de `css`, avant le dernier accent grave) :

```css
.dzAgentCurseur{position:fixed;left:0;top:0;width:18px;height:18px;margin:-9px 0 0 -9px;border-radius:50%;z-index:2147483002;
 pointer-events:none;background:var(--cyan,#3ee6d0);box-shadow:0 0 16px 4px rgba(62,230,208,.6)}
.dzAgentHalo{position:fixed;z-index:2147483002;pointer-events:none;border:2px solid var(--cyan,#3ee6d0);border-radius:10px;
 box-shadow:0 0 0 4px rgba(62,230,208,.18),0 0 24px rgba(62,230,208,.45);transition:opacity .4s}
.dzAgentBulle{position:fixed;z-index:2147483002;pointer-events:none;background:var(--panel,#0e1422);color:var(--ink-strong,#eaf2ff);
 border:1px solid var(--cyan,#3ee6d0);border-radius:8px;padding:4px 8px;font-family:inherit;font-size:12px;font-weight:600;line-height:1.3;white-space:nowrap}
```

c) Remplacer `async function pointer(a) { … }` par :

```js
  const reduit = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let calques = [];
  function effacerPointeur() { calques.forEach((c) => c.remove()); calques = []; }

  function montrer(rect, libelle) {
    effacerPointeur();
    const arrivee = { x: rect.x + rect.w / 2, y: rect.y + rect.h / 2 };
    const b = bouton.getBoundingClientRect();
    const depart = { x: b.x + b.width / 2, y: b.y + b.height / 2 };
    const curseur = el("div", { class: "dzAgentCurseur" });
    const halo = el("div", { class: "dzAgentHalo" });
    Object.assign(halo.style, { left: rect.x - 6 + "px", top: rect.y - 6 + "px", width: rect.w + 12 + "px",
      height: rect.h + 12 + "px", opacity: "0" });
    const bulle = el("div", { class: "dzAgentBulle", texte: libelle });
    Object.assign(bulle.style, { left: Math.max(8, rect.x) + "px", top: Math.max(8, rect.y - 30) + "px", opacity: "0" });
    document.body.append(curseur, halo, bulle);
    calques = [curseur, halo, bulle];
    const finir = () => {
      curseur.style.transform = `translate(${arrivee.x}px,${arrivee.y}px)`;
      halo.style.opacity = "1"; bulle.style.opacity = "1";
      setTimeout(effacerPointeur, 3200);
    };
    if (reduit()) return finir();
    const debut = performance.now(), duree = 700;
    const pas = (t) => {
      const k = Math.min(1, (t - debut) / duree);
      const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;         // ease-in-out
      const p = courbe(depart, arrivee, e);
      curseur.style.transform = `translate(${p.x}px,${p.y}px)`;
      if (k < 1) requestAnimationFrame(pas); else finir();
    };
    requestAnimationFrame(pas);
  }
  document.addEventListener("pointerdown", (ev) => { if (!tiroir.contains(ev.target)) effacerPointeur(); }, true);

  async function pointer(a) {
    const n = await trouver(a, 4000);
    if (!n) { hist.push({ role: "assistant", texte: T("agent.introuvable") }); garder(); dessiner(); return; }
    n.scrollIntoView({ block: "center" });
    await attendre(60);
    const r = n.getBoundingClientRect();
    montrer({ x: r.x, y: r.y, w: r.width, h: r.height }, a[lang()] || a.fr);
  }
```

d) Pour qu'une ancre de Réglages soit aussi **montrée** (et pas seulement ouverte), remplacer dans `executer` la ligne
`else if (e.faire === "reglages") ouvrirReglages(e.section);` par :

```js
      else if (e.faire === "reglages") { ouvrirReglages(e.section); await attendre(300); }
```

- [ ] **Étape 4 : copier dans dist, puis lancer les bancs**

```bash
cp frontend/shared/dz-agent.js frontend/dist/shared/dz-agent.js
```

Lancer : `& $PY tests/test_agent_ecran.py`. Attendu : `7 passed`.

- [ ] **Étape 5 : vérifier à l'écran (8809)**

Dans la console du navigateur intégré :
`__dzAgentExecuter({type:"point",cible:"rail.montage",ecran:null,selecteur:"button.dzNavItem",texte:{fr:"Montage",en:"Montage"},fr:"Montage dans la barre de gauche",en:"Montage in the left bar"})`.
Attendu : le curseur part du bouton « Demander », décrit un arc, puis le halo et la bulle s'affichent sur l'entrée
Montage du rail.
- Faire une capture pendant que le halo est visible.
- Recommencer avec le mouvement réduit (`resize_window` ne l'émule pas ; tester en forçant
  `matchMedia = () => ({matches:true})` dans la console) : le halo apparaît sans animation.

- [ ] **Étape 6 : commiter**

```bash
git commit --only frontend/shared/dz-agent.js frontend/dist/shared/dz-agent.js backend/tests/test_agent_ecran.py -m "agent : pointeur à la Clicky (courbe, halo, bulle, mouvement réduit) (A4)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 12 : A4, le pointeur dans les labs (cadres intégrés)

**Fichiers :**
- Créer : `frontend/shared/dz-agent-cadre.js` et sa copie `frontend/dist/shared/dz-agent-cadre.js`
- Modifier : `frontend/shared/dz-agent.js` (et sa copie),
  `frontend/{vectorlab,photolab,spritelab,tilelab}/index.html`
- Banc : `backend/tests/test_agent_ecran.py`

- [ ] **Étape 1 : ajouter les tests qui échouent**

```python
LABS = ["vectorlab", "photolab", "spritelab", "tilelab"]
BALISE_LAB = '<script type="module" src="/shared/dz-agent-cadre.js"></script>'


def test_cadre_copie_et_balises():
    assert (SHARED / "dz-agent-cadre.js").read_bytes() == (DIST / "dz-agent-cadre.js").read_bytes()
    for lab in LABS:
        html = (RACINE / "frontend" / lab / "index.html").read_text(encoding="utf-8")
        assert html.count(BALISE_LAB) == 1, lab


def test_cadre_verifie_l_origine():
    src = (SHARED / "dz-agent-cadre.js").read_text(encoding="utf-8")
    assert "ev.origin !== location.origin" in src and "postMessage(" in src
    agent = (SHARED / "dz-agent.js").read_text(encoding="utf-8")
    assert "ev.origin !== location.origin" in agent, "le tiroir ne lit que les réponses de même origine"
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY tests/test_agent_ecran.py`. Attendu : 2 FAIL.

- [ ] **Étape 3 : écrire `frontend/shared/dz-agent-cadre.js`**

```js
// dz-agent-cadre.js — assistant « Demander à Deepotus » (spec 2026-10-19-agent-aide-design.md) : le RÉPONDEUR des
// labs affichés dans un cadre intégré de la SPA (Vectorlab, Photolab, Spritelab, Tilelab). La SPA demande
// {dzAgent:"trouve", id, selecteur, texte, lang} ; le lab répond {dzAgent:"rect", id, rect|null} avec le rectangle de
// l'élément dans SON viewport. Même origine seulement, dans les deux sens. SOURCE : frontend/shared ; copie
// identique : frontend/dist/shared (banc backend/tests/test_agent_ecran.py).
import { choisir } from "./dz-agent-logique.js";

if (!window.__dzAgentCadre && window.parent !== window) {
  window.__dzAgentCadre = true;
  window.addEventListener("message", (ev) => {
    if (ev.origin !== location.origin) return;
    const d = ev.data;
    if (!d || d.dzAgent !== "trouve" || typeof d.selecteur !== "string") return;
    let rect = null;
    try {
      const noeuds = Array.from(document.querySelectorAll(d.selecteur));
      const c = noeuds.map((x) => {
        const r = x.getBoundingClientRect();
        return { texte: x.textContent, titre: x.getAttribute("title") || "", visible: r.width > 0 && r.height > 0 };
      });
      const i = choisir(c, { texte: d.texte }, d.lang === "en" ? "en" : "fr");
      if (i >= 0) {
        noeuds[i].scrollIntoView({ block: "center" });
        const r = noeuds[i].getBoundingClientRect();
        rect = { x: r.x, y: r.y, w: r.width, h: r.height };
      }
    } catch (e) { rect = null; }
    ev.source.postMessage({ dzAgent: "rect", id: d.id, rect }, location.origin);
  });
}
```

- [ ] **Étape 4 : brancher les cadres dans `dz-agent.js`**

a) Ajouter `composer` à l'import :

```js
import { etapes, historiqueBorne, choisir, courbe, composer } from "./dz-agent-logique.js";
```

b) Ajouter avant `async function pointer(a)` :

```js
  let numero = 0;
  function demanderAuCadre(a) {
    const cadre = Array.from(document.querySelectorAll("iframe")).find((f) => (f.getAttribute("src") || "").includes(a.cadre));
    if (!cadre || !cadre.contentWindow) return Promise.resolve(null);
    const id = ++numero;
    return new Promise((ok) => {
      const fini = setTimeout(() => { window.removeEventListener("message", h); ok(null); }, 1500);
      function h(ev) {
        if (ev.origin !== location.origin || !ev.data || ev.data.dzAgent !== "rect" || ev.data.id !== id) return;
        clearTimeout(fini);
        window.removeEventListener("message", h);
        const b = cadre.getBoundingClientRect();
        ok(composer({ x: b.x, y: b.y }, ev.data.rect));
      }
      window.addEventListener("message", h);
      cadre.contentWindow.postMessage({ dzAgent: "trouve", id, selecteur: a.selecteur, texte: a.texte, lang: lang() },
        location.origin);
    });
  }
```

c) Au début de `pointer(a)`, ajouter la branche des cadres :

```js
    if (a.cadre) {
      let r = null;
      for (const fin = Date.now() + 4000; !r && Date.now() < fin;) { r = await demanderAuCadre(a); if (!r) await attendre(250); }
      if (!r) { hist.push({ role: "assistant", texte: T("agent.introuvable") }); garder(); dessiner(); return; }
      return montrer(r, a[lang()] || a.fr);
    }
```

- [ ] **Étape 5 : ajouter la balise dans les quatre labs**

Dans chaque `frontend/{vectorlab,photolab,spritelab,tilelab}/index.html`, juste après la ligne qui contient
`/shared/dz-plafonds.js` :

```html
  <script type="module" src="/shared/dz-agent-cadre.js"></script>
```

- [ ] **Étape 6 : copier dans dist, puis lancer les bancs**

```bash
cp frontend/shared/dz-agent-cadre.js frontend/dist/shared/dz-agent-cadre.js
cp frontend/shared/dz-agent.js frontend/dist/shared/dz-agent.js
```

Lancer : `& $PY tests/test_agent_ecran.py`. Attendu : `9 passed`.
Lancer : `& $PY tests/test_p2_plafonds_ecran.py`. Attendu : aucun FAIL (ce banc relit les `index.html` des labs).

- [ ] **Étape 7 : commiter**

```bash
git add frontend/shared/dz-agent-cadre.js frontend/dist/shared/dz-agent-cadre.js
git commit --only frontend/shared/dz-agent-cadre.js frontend/dist/shared/dz-agent-cadre.js frontend/shared/dz-agent.js frontend/dist/shared/dz-agent.js frontend/vectorlab/index.html frontend/photolab/index.html frontend/spritelab/index.html frontend/tilelab/index.html backend/tests/test_agent_ecran.py -m "agent : pointeur dans les labs en cadre intégré (postMessage même origine) (A4)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 13 : A1, les ancres des écrans, relevées sur la page réelle

**Fichiers :** `docs/agent/ancres.json`, `docs/agent/AGENT.md`

Le but est de compléter le registre avec les boutons principaux de Quick, Studio, Montage, Bibliothèque, Vectorlab et
Photolab : au moins 4 par écran, soit environ 24 ancres de plus. Les sélecteurs du bundle sont minifiés, d'où le
couple **sélecteur générique et texte visible**, que le banc vérifie.

- [ ] **Étape 1 : relever les candidats écran par écran (8809)**

Pour chaque vue, aller sur `http://127.0.0.1:8809/?view=<vue>` et exécuter dans le navigateur intégré :

```js
[...document.querySelectorAll("main button, main [role=tab], main a[href]")]
  .filter((b) => b.getBoundingClientRect().width > 0)
  .map((b) => ({ tag: b.tagName, cls: b.className && String(b.className).slice(0, 60), texte: b.textContent.trim().slice(0, 40), title: b.title }))
```

Pour un lab, cibler son cadre : `document.querySelector('iframe[src*="/vectorlab/"]').contentDocument`, à la place
de `document`.

- [ ] **Étape 2 : écrire les ancres**

Garder **les actions qu'un débutant cherche** : générer, exporter, importer, ajouter un plan, rendre, publier,
ouvrir le calque. Chaque ancre suit cette forme :

```json
{"id": "quick.generer", "ecran": "quick", "selecteur": "main button", "texte": {"fr": "<texte FR relevé>", "en": "<texte EN relevé en passant l'interface en anglais>"}, "fr": "Bouton Générer de Quick", "en": "Quick's Generate button"}
```

- Le texte EN se relève en passant l'interface en anglais : Réglages › Apparence, ou
  `localStorage.dz_lang = "en"` puis rechargement.
- Pour un lab : `"cadre": "/vectorlab/"` avec un sélecteur relevé dans le document du lab.
- Les chevrons `<…>` ci-dessus sont à remplacer par les valeurs **relevées** : aucun texte inventé. Le banc
  `test_textes_presents_dans_l_application` le vérifie.

- [ ] **Étape 3 : citer les nouvelles ancres dans les Parcours de `AGENT.md`**

Par exemple : « **Première vidéo** : [POINT:rail.quick] → écrire l'idée → [POINT:quick.generer]. [GUIDE:quick] ».

- [ ] **Étape 4 : lancer les bancs**

Lancer : `& $PY tests/test_agent_connaissance.py` et `& $PY tests/test_agent_aide.py`.
Attendu : tout vert. `test_route_etat` attend `ancres >= 25` et reste valable.

- [ ] **Étape 5 : prouver deux ancres à l'écran**

Sur 8809, avec `__dzAgentExecuter({...l'action rendue par A.analyser("[POINT:quick.generer]")...})`, montrer une
ancre de Quick et une ancre du Vectorlab (cadre). Faire une capture de chaque halo.

- [ ] **Étape 6 : commiter**

```bash
git commit --only docs/agent/ancres.json docs/agent/AGENT.md -m "agent : ancres des écrans relevées sur la page réelle (A1)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 14 : preuve complète, suite et PR

- [ ] **Étape 1 : faire tourner toute la suite**

Lancer : `.\scripts\run-tests.ps1`. Attendu : aucun nouveau FAIL par rapport à origin/main. Un FAIL préexistant se
note dans la PR, il ne se corrige pas ici.

- [ ] **Étape 2 : preuve de bout en bout avec un moteur réel (facultative, payante)**

Le 8809 n'a aucune clé. La preuve avec un moteur réel exige l'accord de l'utilisateur, car elle dépense, même un
peu, sous le plafond « aide ». Sans accord, on prouve avec un moteur local gratuit s'il en existe un (Ollama), sinon
on s'en tient à la réponse « sans clé » et aux appels `__dzAgentExecuter`.

- [ ] **Étape 3 : preuve FR et EN**

1. Sur 8809, en FR : F1, poser une question, cliquer « Montre-moi », faire une capture.
2. Passer en EN (`localStorage.dz_lang="en"`, recharger) et faire de même.
3. Vérifier que `read_console_messages` n'a aucune erreur.

- [ ] **Étape 4 : pousser et ouvrir la PR**

```bash
git push -u origin chantier/agent-guide
gh pr create --title "Assistant « Demander à Deepotus » : tiroir F1 + pointeur + AGENTS.md (A0-A4)" --body "<résumé des lots, captures FR/EN, bancs lancés, écart volontaire (moteur choisi dans le tiroir), suite : plan A5-A7>

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

- [ ] **Étape 5 : installation**

La copie dans `%LOCALAPPDATA%` ne se fait **qu'après fusion et accord de l'utilisateur**, selon la procédure
habituelle :
1. relever les empreintes avec `git hash-object` juste avant de copier ;
2. arrêter au moindre écart ;
3. fichiers à copier : `docs/agent/`, `backend/app/services/agent_aide.py`, `backend/app/api/agent_routes.py`,
   `backend/app/main.py`, `backend/app/services/plafonds.py`, les fichiers de `frontend/shared/` et
   `frontend/dist/shared/`, `frontend/dist/index.html` et les quatre `index.html` des labs ;
4. redémarrer le backend.
```
