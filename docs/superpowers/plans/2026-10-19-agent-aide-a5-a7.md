# Assistant « Demander à Deepotus » — plan d'implémentation (lots A5 à A7)

> **Pour les agents qui exécutent :** SOUS-SKILL OBLIGATOIRE : superpowers:subagent-driven-development (recommandé)
> ou superpowers:executing-plans, tâche par tâche. Les étapes sont des cases `- [ ]` à cocher.

**But :** compléter l'assistant livré en A0-A4. Quand aucune ancre nommée ne convient, il **regarde l'écran** (avec
l'accord de l'utilisateur et le coût affiché) et pointe l'endroit trouvé (A5). L'utilisateur peut **dicter** sa
question et **écouter** la réponse (A6). Le guide gagne un chapitre « Demander à Deepotus » (A7).

**Architecture :**
- A5 côté serveur : `moteurs_texte` apprend à joindre des images à UN appel (`tirer(..., images=)`, par fournisseur),
  à dire quels moteurs les lisent (`vision`) et à les chiffrer (`estimer(..., images=)`). `agent_aide` reconnaît
  `[VOIR]` et, seulement pour un appel avec capture, `[POINT:x,y:libellé]`. Une route gratuite
  `POST /api/agent/estimer` donne le devis ; le second `POST /api/agent/demander` porte l'image et `max_usd`.
- A5 côté écran : un module `dz-agent-vision.js` capture **l'onglet courant** (`getDisplayMedia`, tiroir masqué),
  réduit l'image à 1 280 px au plus et l'encode en JPEG. Le tiroir affiche l'accord (moteurs qui voient seulement,
  coût), envoie, puis pointe l'élément sous le point rendu.
- A6 : la dictée réutilise `dz-champ-ia.js` (voies 1 et 2, devis et accord de la voie 2) par une nouvelle entrée
  publique `DzChampIA.dictee.basculer(el)` et un événement `dzia-dictee`. La lecture passe par une route
  `POST /api/agent/lire` qui fait lire le texte par la voix des Réglages (Voicebox gratuit, ElevenLabs payant sous le
  plafond « aide »), dans un cache à part, jamais dans la Bibliothèque.
- A7 : chapitre `demander` du guide via le skill guide-deepotus, avec un backend de preuve dédié
  (`scripts/guide/serve_guide_agent.py`, faux Ollama texte + vision, faux Voicebox) et des scènes capturées FR puis EN.

**Pile :** FastAPI (Python embarqué), modules ES vanilla, bancs pytest lancés depuis `backend/`, bancs node `.test.mjs`,
`scripts/guide/capturer.js` (puppeteer-core) pour les scènes.

**Spec :** `docs/superpowers/specs/2026-10-19-agent-aide-design.md` (à jour de la livraison A0-A4).
**Plan précédent (format, conventions) :** `docs/superpowers/plans/2026-10-19-agent-aide.md`.
**Branche de départ :** `chantier/agent-guide` (A0-A4, 37 commits, non poussée). Travailler dans un worktree tiré de
cette branche, une PR par lot (A5, A6, A7) ou une PR unique si l'utilisateur le préfère.

---

## Décisions prises dans ce plan (à relire avant de coder)

| Sujet | Décision | Pourquoi |
|---|---|---|
| Capture | `navigator.mediaDevices.getDisplayMedia` avec `preferCurrentTab`, une seule image, pistes coupées aussitôt | Le dépôt n'a aucune bibliothèque de capture DOM ; une sérialisation DOM → canvas perd les labs en cadre, les `<canvas>` et les `<video>`. L'app tourne dans le navigateur par défaut sur `deepotus.localhost` (contexte sûr). Le navigateur demande lui-même le partage : c'est un **second** accord, après le nôtre. |
| Même onglet | Refus si la surface n'est pas `browser` ou si le rapport largeur/hauteur de l'image s'écarte de plus de 4 % de celui de la fenêtre | Sinon les coordonnées rendues ne correspondent pas à la page. |
| Tiroir pendant la capture | Masqué (`visibility:hidden`, tiroir et bouton), pointeur effacé, puis rétabli | Le tiroir couvre 400 px à droite. |
| Coordonnées | `[POINT:x,y:libellé]` accepté **uniquement** pour un appel avec image, borné à la taille de la capture ; libellé réduit à une ligne de 60 caractères, affiché en `textContent` | Un modèle sans image ne peut pas inventer de coordonnées. |
| Moteurs qui voient | `moteurs_texte.vision(moteur, modele)` : Claude (tous sauf `claude-2`/`instant`), OpenAI `gpt-4o`, `gpt-4.1`, `gpt-4.5`, `gpt-4-turbo`, `gpt-5*`, `gpt-6*`, `o1`, `o3`, `o4-mini` (hors audio/realtime/search/transcribe/tts, `o1-mini`, `o1-preview`, `o3-mini`), Gemini (hors embedding/tts/aqa), Ollama si `/api/show` annonce `vision` ; `fl:` et `local:` → non | Aucune API commune ne le dit pour les fournisseurs libres et serveurs ajoutés. L'accord ne propose que les moteurs qui voient. |
| Coût de la vision | `POST /api/agent/estimer` (gratuit) → `{usd}` ; `demander` avec image exige `max_usd` et répond **409** si le coût recalculé dépasse (tolérance 0,0001 $) | Même patron que la dictée (`/api/dictation/estimate` puis `max_usd`). Le devis se calcule sur une consigne de taille **nominale** pour que les deux calculs portent sur le même texte. |
| Jetons d'une image | `JETONS_IMAGE = 1600` par image ≤ 1 280 px (pire cas) | Anthropic ≈ l×h/750, OpenAI « high » ≤ 1 105, Gemini 258 par tuile. |
| Dictée | Bouton micro du tiroir → `DzChampIA.dictee.basculer(saisie)` ; l'état revient par l'événement `dzia-dictee` | Aucune duplication de la dictée (voie 1 navigateur, voie 2 MediaRecorder + devis + accord + `max_usd`). Le champ du tiroir n'est **pas** marqué `data-dz-ia` : ce n'est pas un champ de génération. |
| Lecture | `POST /api/agent/lire {texte, lang}` → MP3 ; voix = fournisseur des Réglages (`voice_providers.resolve_provider`) ; garde `plafonds.verifier(..., "aide")` pour ElevenLabs seulement ; cache `…/agent_lectures/<sha1>.mp3` (30 fichiers gardés) | `/api/audio/voiceover` écrit dans la Bibliothèque : inadapté. Une réponse relue repart du cache sans dépense. |
| Guide | Chapitre `demander`, famille `demarrer`, juste après `tour` ; lot `A7` ; backend de preuve **8815** (faux Ollama 8816, faux Voicebox 8817) | Ports libres (8809 guide, 8811-8813 motion). |
| Scène de vision | Le headless ne peut pas accorder `getDisplayMedia` : la scène montre la réponse `[VOIR]` puis l'accord (vrai devis), et le pointeur posé par `window.__dzAgentExecuter` sur une action `point_xy` calculée depuis le rectangle réel de l'élément | Le pointeur et l'accord sont les vrais ; seul le partage d'onglet n'est pas filmé (dit dans la légende). |

**Hors de ce plan :** `cache_control` Anthropic ; test automatisé des sélecteurs d'ancres ; lecture automatique de
chaque réponse (la lecture reste sur clic) ; voix du navigateur (`speechSynthesis`) en repli.

---

## Conventions à connaître (aucun contexte supposé)

- **Python :** `$PY = "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe"`. Il **ignore PYTHONPATH** :
  chaque banc fait `sys.path.insert(0, <backend>)` et se lance depuis `backend/` : `& $PY tests/<banc>.py`. Un banc
  pytest finit par `if __name__ == "__main__": sys.exit(pytest.main([__file__, "-q"]))`.
- **Bancs node :** `node frontend/shared/qa/<nom>.test.mjs`.
- **Le bundle `frontend/dist/assets/index-*.js` ne se touche pas.** Tout passe par `/shared/`.
- **`/shared/x.js` est servi depuis `frontend/dist/shared/`.** Source `frontend/shared/`, copie identique octet pour
  octet faite avec `cp` (jamais à la main). `dz-champ-ia.js` suit la même règle (banc `test_champ_ia.py`).
- **Libellés :** `frontend/shared/i18n/agent.json`, clés à **3 segments au moins** (`agent.vision.voir`), FR et EN,
  puis `& $PY scripts/i18n_assembler.py`. Aucun texte visible en dur dans `dz-agent*.js`.
- **`window.dzLang` est une FONCTION** dans la SPA : `typeof window.dzLang === "function" ? window.dzLang() : …`.
- **Messages d'erreur backend :** tout nouveau texte de `HTTPException`, `ValueError`, `RuntimeError` se traduit dans
  `scripts/i18n_l10_traductions.json` (ajouter les entrées **à la fin, sans retrier le fichier**), puis
  `& $PY scripts/i18n_l10_erreurs.py` et `--check`. Sinon les bancs motion et `studio_motion_guide` rougissent.
- **Toute route qui dépense** appelle `_PLAF.verifier` (alias exact `_PLAF`) dans sa fermeture : banc
  `test_plafonds_garde.py` (recensement AST de `tests/_recensement_payant.py`).
- **Backend de preuve :** jamais le 8765 de l'utilisateur. Guide : `scripts/guide/serve_guide.py` (8809) ; ce plan
  ajoute `scripts/guide/serve_guide_agent.py` (8815).
- **Suite complète dans un worktree neuf :** ~45 échecs PRÉEXISTANTS (photolab vendor, `.bak_*`, puppeteer). Toujours
  comparer avec un worktree d'`origin/main` avant de conclure.
- **Commits :** `git commit --only <fichiers>`, message en français au format `<zone> : <quoi> (A5)`, terminé par
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Carte des fichiers

| Fichier | Rôle | Lot |
|---|---|---|
| `backend/app/services/moteurs_texte.py` (modifié) | `vision`, `images_valides`, `JETONS_IMAGE`, `estimer(images=)`, `tirer/_appeler/tirer_garde(images=)` | A5 |
| `backend/app/services/agent_aide.py` (modifié) | `[VOIR]`, `[POINT:x,y:…]`, `_preparer`, `estimer_vue`, `demander` avec image, `CoutChange`, `etat` (vision, voix), lecture | A5, A6 |
| `backend/app/api/agent_routes.py` (modifié) | `POST /estimer`, 409/413 sur `/demander`, `POST /lire`, `/etat` hors boucle | A5, A6 |
| `docs/agent/AGENT.md` (modifié) | Règle `[VOIR]`, micro et lecture, chapitre `demander` | A5, A6, A7 |
| `frontend/shared/dz-agent-logique.js` (modifié) | `reduire`, `versEcran`, `memeOnglet`, `cliquable`, `prix`, étapes `voir` / `pointer_xy` | A5 |
| `frontend/shared/dz-agent-vision.js` (créé) | Capture de l'onglet | A5 |
| `frontend/shared/dz-agent.js` (modifié) | Accord, capture, envoi, pointage par coordonnées ; micro ; lecture | A5, A6 |
| `frontend/shared/dz-champ-ia.js` (modifié) | `dictee.basculer`, événement `dzia-dictee` | A6 |
| `frontend/shared/i18n/agent.json` (modifié) | Libellés `agent.vision.*`, `agent.voix.*` | A5, A6 |
| `frontend/dist/shared/*` (copies) | Copies servies | A5, A6 |
| `scripts/i18n_l10_traductions.json`, `backend/app/i18n/erreurs.json` | Messages d'erreur traduits | A5, A6 |
| `backend/tests/_recensement_payant.py`, `backend/tests/test_plafonds_garde.py` (modifiés) | Module `agent`, route `/lire` payante | A6 |
| `backend/tests/test_moteurs_texte_images.py` (créé) | Banc des images de `moteurs_texte` | A5 |
| `backend/tests/test_agent_vision.py` (créé) | Banc A5 service et routes | A5 |
| `backend/tests/test_agent_voix.py` (créé) | Banc A6 lecture et branchement de la dictée | A6 |
| `backend/tests/test_agent_aide.py`, `test_agent_ecran.py`, `test_agent_connaissance.py` (modifiés) | `[VOIR]` accepté, copies, libellés | A5, A6 |
| `frontend/shared/qa/agent_logique.test.mjs` (modifié) | Logique pure A5 | A5 |
| `scripts/guide/serve_guide_agent.py` (créé) | Backend de preuve du chapitre | A7 |
| `docs/guide/src/chapitres.json`, `jeveux.json` (modifiés) | Chapitre `demander` | A7 |
| `docs/guide/src/fr/demander.html`, `docs/guide/src/en/demander.html` (créés) | Texte du chapitre | A7 |
| `docs/guide/src/scenes/plans/a7.json`, `docs/guide/src/scenes/demander/*` (créés) | Scènes animées | A7 |
| `docs/guide/fr.html`, `en.html`, PDF (reconstruits) | Guide construit | A7 |
| `backend/tests/test_agent_guide.py` (créé) | Banc du chapitre | A7 |
| `docs/superpowers/specs/2026-10-19-agent-aide-design.md` (modifié) | Décrit A5-A7 livrés | fin |

---

# Lot A5 — la vision en secours

### Tâche 1 : A5, `moteurs_texte` sait quels moteurs voient et chiffre une image

**Fichiers :** `backend/app/services/moteurs_texte.py` (après `sortie_max`, et `estimer` lignes 332-341),
`backend/tests/test_moteurs_texte_images.py` (créé)

- [ ] **Étape 1 : écrire le banc qui échoue**

Créer `backend/tests/test_moteurs_texte_images.py` :

```python
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
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer (depuis `backend/`) : `& $PY tests/test_moteurs_texte_images.py`.
Attendu : échecs `AttributeError: module 'app.services.moteurs_texte' has no attribute 'vision'` (et `images_valides`,
`JETONS_IMAGE`), `TypeError` sur `estimer(..., images=2)`.

- [ ] **Étape 3 : implémenter**

Dans `backend/app/services/moteurs_texte.py`, ajouter `import base64` à côté de `import json as _json`, puis, juste
après la fonction `sortie_max` (avant le bloc `# ── l'appel (t232)`), ajouter :

```python
# ── les images (A5, assistant « Demander », 19/10/2026) ──────────────────────────────────────────────────────────
# Spec 2026-10-19-agent-aide-design.md § 2 « Vision en secours ». UN appel peut joindre des images (une capture
# d'écran) ; seuls les modèles qui les lisent en reçoivent. Relevé de la documentation des fournisseurs le 19/10/2026 :
# tous les Claude 3 et suivants, les GPT-4o / 4.1 / 4.5 / 4-turbo / 5 / 6 et o1 / o3 / o4-mini d'OpenAI (pas les
# variantes audio, temps réel, recherche, ni o1-mini / o1-preview / o3-mini), tous les Gemini de génération, et les
# modèles Ollama dont /api/show annonce « vision ». Fournisseurs libres (fl:) et serveurs ajoutés (local:) : aucune API
# commune pour le dire → non.
JETONS_IMAGE = 1600            # pire cas par image ≤ 1 280 px (Anthropic ≈ l×h/750 ; OpenAI « high » ≤ 1 105)
MAX_IMAGES = 4
MAX_IMAGE_OCTETS = 4_500_000   # image décodée, sous la limite de 5 Mo d'Anthropic
TYPES_IMAGE = ("image/jpeg", "image/png", "image/webp")
_OPENAI_VISION = re.compile(r"^(gpt-4o|gpt-4\.1|gpt-4\.5|gpt-4-turbo|gpt-5|gpt-6|o1|o3|o4-mini)(?:$|[.\-])")
_OPENAI_SANS_VISION = re.compile(r"(audio|realtime|search|transcribe|tts|^o1-mini|^o1-preview|^o3-mini)")


def vision(moteur: str, modele: str | None = None) -> bool:
    """Vrai si CE moteur et CE modèle (sinon celui des Réglages) lisent les images."""
    brut = (modele or modele_sain(moteur) or "").strip()
    mod = brut.lower()
    if not mod or ressemble_a_une_cle(brut):
        return False
    if moteur == "anthropic":
        return mod.startswith("claude-") and not mod.startswith(("claude-2", "claude-instant"))
    if moteur == "openai":
        return bool(_OPENAI_VISION.match(mod)) and not _OPENAI_SANS_VISION.search(mod)
    if moteur == "gemini":
        return mod.startswith("gemini-") and not any(x in mod for x in ("embedding", "-tts", "aqa"))
    if moteur == "ollama":
        caps = _show_ollama(brut).get("capabilities")
        return isinstance(caps, list) and "vision" in caps
    return False


def images_valides(images) -> list[dict]:
    """[{mime, b64}] vérifiées : type connu, base64 strict, ni vide ni trop lourde, MAX_IMAGES au plus. Une DONNÉE :
    rien n'est décodé au-delà de la vérification. RuntimeError sinon (rien n'est envoyé)."""
    if not images:
        return []
    if not isinstance(images, list) or len(images) > MAX_IMAGES:
        raise RuntimeError(f"au plus {MAX_IMAGES} images par appel")
    out = []
    for im in images:
        mime = im.get("mime") if isinstance(im, dict) else None
        b64 = im.get("b64") if isinstance(im, dict) else None
        if mime not in TYPES_IMAGE or not isinstance(b64, str) or not b64:
            raise RuntimeError("image illisible : type ou contenu manquant")
        try:
            brut = base64.b64decode(b64, validate=True)
        except ValueError:
            raise RuntimeError("image illisible : base64 invalide") from None
        if not brut or len(brut) > MAX_IMAGE_OCTETS:
            raise RuntimeError("image trop lourde (4,5 Mo au plus)")
        out.append({"mime": mime, "b64": b64})
    return out
```

Remplacer la fonction `estimer` par :

```python
def estimer(moteur: str, prompt: str, systeme: str = "", max_tokens: int = 4000, effort=None, *,
            modele: str = "", images: int = 0) -> dict:
    """L'op d'estimation d'UN appel, au moteur choisi : ~4 caractères par jeton en entrée, `max_tokens` en sortie (le
    pire cas). `pricing.estimate` la chiffre : 0 pour un local, tarif Anthropic + `a_mesurer` pour un fl.
    t239 : avec un `effort` que le modèle accepte (celui de l'appel, sinon celui des Réglages), la sortie estimée est
    celle qui sera demandée (`sortie_max`) ; sans effort, ou effort refusé, rien ne change.
    A5 : chaque image jointe compte JETONS_IMAGE jetons d'entrée."""
    from app.services import plafonds as _PLAF
    n = len(prompt or "") + len(systeme or "")
    out = sortie_max(int(max_tokens), effort_applique(moteur, modele, effort)) if effort is not None else int(max_tokens)
    return _PLAF.op_llm(-(-n // 4) + max(0, int(images or 0)) * JETONS_IMAGE, out, str(moteur or ""))
```

- [ ] **Étape 4 : lancer et voir réussir**

Lancer : `& $PY tests/test_moteurs_texte_images.py` → aucun échec.
Non-régression : `& $PY tests/test_moteurs_texte_tirer.py`, `& $PY tests/test_moteurs_effort.py` → aucun FAIL.

- [ ] **Étape 5 : commiter**

```bash
git commit --only backend/app/services/moteurs_texte.py backend/tests/test_moteurs_texte_images.py -m "moteurs : quels moteurs voient, images validées et chiffrées (A5)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 2 : A5, `tirer` envoie les images à chaque fournisseur

**Fichiers :** `backend/app/services/moteurs_texte.py` (`tirer`, `_appeler`, `tirer_garde`),
`backend/tests/test_moteurs_texte_images.py`

- [ ] **Étape 1 : ajouter les tests qui échouent**

Ajouter avant le lanceur de `backend/tests/test_moteurs_texte_images.py` :

```python
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
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY tests/test_moteurs_texte_images.py`.
Attendu : `TypeError: tirer() got an unexpected keyword argument 'images'`.

- [ ] **Étape 3 : implémenter**

Dans `tirer`, changer la signature et le corps :

```python
def tirer(moteur: str, modele: str, prompt: str, systeme: str, max_tokens: int = 4000, json: bool = False, *,
          timeout: float = 90.0, effort=None, images=None):
```

Ajouter à la docstring : `A5 : images = [{mime, b64}] (images_valides) ; refusées avant tout envoi si CE modèle ne
les lit pas (vision).` Puis, juste après le refus du modèle qui ressemble à une clé :

```python
    ims = images_valides(images)
    if ims and not vision(moteur, mod):
        raise RuntimeError(f"le modèle {mod} ne lit pas les images")
```

et remplacer l'appel final à `_appeler` par :

```python
    txt = _appeler(moteur, mod, prompt, systeme, max_tokens, json, timeout, eff, ims)
```

Dans `_appeler`, signature :

```python
def _appeler(moteur: str, mod: str, prompt: str, systeme: str, max_tokens: int, json: bool, timeout: float,
             effort: str = "", images: list | None = None) -> str:
```

Branche Anthropic : remplacer la construction de `body` par

```python
        contenu = ([{"type": "image", "source": {"type": "base64", "media_type": i["mime"], "data": i["b64"]}}
                    for i in images] + [{"type": "text", "text": prompt}]) if images else prompt
        body = {"model": mod, "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": contenu}]}
```

Branche OpenAI : remplacer la construction de `msgs` par

```python
        contenu = ([{"type": "text", "text": prompt}]
                   + [{"type": "image_url", "image_url": {"url": f"data:{i['mime']};base64,{i['b64']}",
                                                          "detail": "high"}} for i in images]) if images else prompt
        msgs = ([{"role": "system", "content": systeme}] if systeme else []) \
            + [{"role": "user", "content": contenu}]
```

Branche Gemini : remplacer la première ligne de `body` par

```python
        parts = [{"inlineData": {"mimeType": i["mime"], "data": i["b64"]}} for i in (images or [])] \
            + [{"text": prompt}]
        body = {"contents": [{"parts": parts}],
                "generationConfig": {"maxOutputTokens": max_tokens}}
```

Branche Ollama : après `body = {...}` ajouter

```python
        if images:
            body["images"] = [i["b64"] for i in images]
```

Les branches `fl:` et `local:` ne changent pas (`vision` y rend toujours faux, `tirer` refuse donc avant).

Dans `tirer_garde`, signature `..., timeout: float = 90.0, effort=None, images=None):`, ajouter à la docstring
`A5 : les images sont vérifiées et refusées AVANT la garde (un moteur aveugle ne déclenche jamais de 402).`, puis
remplacer le corps après le refus « non configuré » par (la variable s'appelle `mod`, comme dans `tirer` : le générateur L10 en
fait le même gabarit `{mod}` ; `vision` peut faire un POST synchrone vers Ollama, donc il tourne hors de la boucle) :

```python
    ims = images_valides(images)
    loop = asyncio.get_running_loop()
    if ims:
        mod = (modele or modele_sain(moteur)).strip()
        if not mod:
            raise RuntimeError(f"aucun modèle pour « {moteur} »")
        if not await loop.run_in_executor(None, vision, moteur, mod):      # Ollama : /api/show, bloquant
            raise RuntimeError(f"le modèle {mod} ne lit pas les images")
    await _PLAF.verifier(estimer(moteur, prompt, systeme, max_tokens, effort, modele=modele, images=len(ims)),
                         categorie, ref)
    return await loop.run_in_executor(
        None, lambda: tirer(moteur, modele, prompt, systeme, max_tokens, json, timeout=timeout, effort=effort,
                            images=ims))
```

- [ ] **Étape 4 : lancer et voir réussir**

Lancer : `& $PY tests/test_moteurs_texte_images.py` → aucun échec.
Non-régression : `& $PY tests/test_moteurs_texte_tirer.py`, `& $PY tests/test_moteurs_openai_sortie.py`,
`& $PY tests/test_motion_choregraphe.py` → aucun FAIL, sauf E1 (`i18n_l10_erreurs --check`, 6 messages neufs sans
traduction) : ce seul FAIL reste jusqu'à la Tâche 5, qui traduit les messages (L10).

- [ ] **Étape 5 : commiter**

```bash
git commit --only backend/app/services/moteurs_texte.py backend/tests/test_moteurs_texte_images.py -m "moteurs : tirer joint des images (Anthropic, OpenAI, Gemini, Ollama) (A5)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 3 : A5, les balises `[VOIR]` et `[POINT:x,y:libellé]`

**Fichiers :** `backend/app/services/agent_aide.py` (`_action`, `analyser`), `backend/tests/test_agent_aide.py`
(test `test_balises_inconnues_retirees_et_comptees`), `backend/tests/test_agent_vision.py` (créé)

- [ ] **Étape 1 : écrire le banc qui échoue**

Créer `backend/tests/test_agent_vision.py` :

```python
# -*- coding: utf-8 -*-
"""A5 (spec 2026-10-19-agent-aide-design.md § 2 « Vision en secours ») — l'assistant regarde l'écran : balises
[VOIR] et [POINT:x,y:libellé], devis gratuit, second appel avec capture et montant accepté, routes /api/agent.
Run : & $PY tests/test_agent_vision.py   (depuis backend/)"""
import asyncio, base64, os, pathlib, sys, tempfile
import pytest

_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzagentvue_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from app.services import agent_aide as A                                    # noqa: E402
from app.services import moteurs_texte as MT                                # noqa: E402

JPG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 64).decode()
IMAGE = {"mime": "image/jpeg", "b64": JPG, "largeur": 1280, "hauteur": 720}


def test_voir_devient_une_action():
    texte, actions, rejets = A.analyser("Je ne connais pas ce bouton.\n[VOIR]")
    assert texte == "Je ne connais pas ce bouton." and rejets == 0
    assert actions == [{"type": "voir", "cible": "ecran"}]
    assert A.analyser("[VOIR:quoi]")[1] == [] and A.analyser("[VOIR:quoi]")[2] == 1    # VOIR ne prend pas de cible


def test_point_xy_seulement_avec_une_capture():
    dims = {"largeur": 1280, "hauteur": 720}
    _, actions, rejets = A.analyser("Ici.\n[POINT:640,360:Générer]", dims)
    assert rejets == 0 and actions == [{"type": "point_xy", "cible": "640,360", "x": 640, "y": 360,
                                        "largeur": 1280, "hauteur": 720, "libelle": "Générer"}]
    assert A.analyser("[POINT:640,360:Générer]") == ("", [], 1)              # sans capture : refusé
    assert A.analyser("[POINT:1280,10:x]", dims)[2] == 1                     # hors de la capture (bornes strictes)
    assert A.analyser("[POINT:1279,719:x]", dims)[2] == 0
    assert A.analyser("[POINT:10, 20]", dims)[1][0]["libelle"] == ""         # libellé facultatif, espaces tolérés
    assert A.analyser("[POINT:reglages.cles]", dims)[1][0]["type"] == "point"   # une ancre reste une ancre
    assert A.analyser("[VOIR]", dims) == ("", [], 1)                         # pas de seconde capture en boucle


def test_point_xy_libelle_borne_et_sans_code():
    dims = {"largeur": 1280, "hauteur": 720}
    a = A.analyser("[POINT:1,2:" + "<b>x</b>\t" * 8 + "]", dims)[1][0]   # 76 car. : sous la borne de 80 de BALISE
    assert len(a["libelle"]) <= 60 and "\t" not in a["libelle"]
    b = A.analyser("[POINT:1,2:Gé\u202enérer\u200b]", dims)[1][0]
    assert b["libelle"] == "Générer"                                     # contrôle et format Unicode retirés


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
```

Dans `backend/tests/test_agent_aide.py`, remplacer `test_balises_inconnues_retirees_et_comptees` par :

```python
def test_balises_inconnues_retirees_et_comptees():
    texte, actions, rejets = A.analyser("A [POINT:bouton.invente] B [ALLER:nulle-part] [GUIDE:x] [VOIR] [FOO:bar]")
    assert actions == [{"type": "voir", "cible": "ecran"}] and rejets == 4     # A5 : [VOIR] est connue
    assert "[" not in texte and texte == "A  B"
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY -m pytest tests/test_agent_vision.py tests/test_agent_aide.py -q`.
Attendu : échecs sur `voir`, sur `analyser(..., dims)` (`TypeError` : un seul argument).

- [ ] **Étape 3 : implémenter**

Dans `backend/app/services/agent_aide.py`, juste après `MAX_ACTIONS = 6` :

```python
# A5 : coordonnées rendues par un moteur qui a VU une capture (pixels de la capture), libellé facultatif
XY = re.compile(r"^(\d{1,5})\s*,\s*(\d{1,5})\s*(?::(.*))?$")
```

Remplacer `_action` par :

```python
def _sans_controle(t: str) -> str:
    """Sans caractères de contrôle ni de format Unicode (catégories C* : U+202E, zéro-largeur…) : le libellé s'affiche."""
    return "".join(" " if c.isspace() else c for c in t if c.isspace() or not unicodedata.category(c).startswith("C"))


def _action(typ: str, cible: str, image: dict | None = None) -> dict | None:
    """image : {largeur, hauteur} de la capture jointe à l'appel (A5) — seule une réponse à une capture peut rendre des
    coordonnées, et jamais une nouvelle demande de capture."""
    k = connaissance()
    if typ == "POINT" and cible in k["ancres"]:
        a = k["ancres"][cible]
        return {"type": "point", "cible": cible, "ecran": a.get("ecran"), "selecteur": a.get("selecteur"),
                "texte": a.get("texte"), "cadre": a.get("cadre"), "reglages": a.get("reglages"),
                "partout": bool(a.get("partout")), "libelle": a.get("libelle"),
                "fr": a["fr"], "en": a["en"]}
    if typ == "POINT" and image:
        m = XY.match(cible)
        if m:
            x, y = int(m.group(1)), int(m.group(2))
            if x < image["largeur"] and y < image["hauteur"]:
                return {"type": "point_xy", "cible": f"{x},{y}", "x": x, "y": y, "largeur": image["largeur"],
                        "hauteur": image["hauteur"], "libelle": _ligne(_sans_controle(m.group(3) or ""), 60)}
        return None
    if typ == "VOIR" and not cible and not image:
        return {"type": "voir", "cible": "ecran"}
    if typ == "ALLER" and cible in VUES:
        return {"type": "aller", "cible": cible}
    if typ == "GUIDE" and cible in k["chapitres"]:
        c = k["chapitres"][cible]
        return {"type": "guide", "cible": cible, "fr": c["fr"], "en": c["en"]}
    return None
```

Remplacer la signature et l'appel dans `analyser` :

```python
def analyser(texte, image: dict | None = None) -> tuple[str, list, int]:
    """(texte sans balises ni indentation, actions dédoublonnées ≤ MAX_ACTIONS, nombre de balises rejetées).
    image : {largeur, hauteur} quand la réponse vient d'un appel avec capture (A5)."""
    actions, vus, rejets = [], set(), 0

    def remplacer(m):
        nonlocal rejets
        a = _action(m.group(1), (m.group(2) or "").strip(), image)
```

(le reste de `analyser` est inchangé).

- [ ] **Étape 4 : lancer et voir réussir**

Lancer : `& $PY -m pytest tests/test_agent_vision.py tests/test_agent_aide.py -q` → aucun échec.

- [ ] **Étape 5 : commiter**

```bash
git commit --only backend/app/services/agent_aide.py backend/tests/test_agent_vision.py backend/tests/test_agent_aide.py -m "agent : balises [VOIR] et [POINT:x,y:libellé] (A5)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 4 : A5, devis gratuit et second appel avec capture

**Fichiers :** `backend/app/services/agent_aide.py` (`_preparer`, `_cout`, `estimer_vue`, `demander`, `etat`),
`backend/tests/test_agent_vision.py`

- [ ] **Étape 1 : ajouter les tests qui échouent**

Ajouter avant le lanceur de `backend/tests/test_agent_vision.py` :

```python
def _moteur(monkeypatch, voit=True):
    monkeypatch.setattr(A, "choisir_moteur", lambda d="": "anthropic")
    monkeypatch.setattr(A, "_espace", lambda: "")
    monkeypatch.setattr(MT, "vision", lambda m, mod=None: voit)


def test_devis_gratuit_et_stable(monkeypatch):
    _moteur(monkeypatch)
    corps = {"question": "Où est le bouton qui exporte ?", "lang": "fr", "moteur": "anthropic"}
    d1 = A.estimer_vue(corps)
    assert d1["moteur"] == "anthropic" and d1["vision"] is True and d1["cout"] == "payant" and d1["usd"] > 0
    d2 = A.estimer_vue(dict(corps, image=IMAGE))            # une image jointe au devis est ignorée
    assert d2["usd"] == d1["usd"]


def test_devis_sans_moteur(monkeypatch):
    monkeypatch.setattr(A, "choisir_moteur", lambda d="": "")
    assert A.estimer_vue({"question": "q"}) == {"moteur": "", "nom": "", "usd": 0.0, "cout": "", "vision": False}


def test_demander_avec_capture(monkeypatch):
    _moteur(monkeypatch)
    vu = {}

    async def faux(moteur, modele, prompt, systeme, max_tokens=4000, json=False, *, categorie="", **kw):
        vu.update(prompt=prompt, systeme=systeme, images=kw.get("images"), categorie=categorie)
        return "C'est ce bouton.\n[POINT:100,50:Exporter]"
    monkeypatch.setattr(MT, "tirer_garde", faux)
    corps = {"question": "Où est le bouton qui exporte ?", "lang": "fr", "moteur": "anthropic"}
    usd = A.estimer_vue(corps)["usd"]
    r = asyncio.run(A.demander(dict(corps, image=IMAGE, max_usd=usd)))
    assert vu["images"] == [{"mime": "image/jpeg", "b64": JPG}] and vu["categorie"] == "aide"
    assert "1280×720" in vu["prompt"] and "[POINT:x,y:libellé]" in vu["prompt"]
    assert vu["systeme"] == A.systeme("", "fr", "")            # le préfixe système ne change pas (cache)
    assert r["actions"][0]["type"] == "point_xy" and r["actions"][0]["libelle"] == "Exporter"


def test_demander_capture_refusee(monkeypatch):
    _moteur(monkeypatch, voit=False)
    corps = {"question": "q", "image": IMAGE, "max_usd": 1.0}
    with pytest.raises(ValueError):
        asyncio.run(A.demander(corps))                        # moteur aveugle
    _moteur(monkeypatch)
    for mauvais in ({"max_usd": None}, {"max_usd": -1}, {"max_usd": float("nan")}, {"max_usd": True},
                     {"max_usd": 10 ** 400}):
        with pytest.raises(ValueError):
            asyncio.run(A.demander(dict(corps, **mauvais)))
    for image in ({**IMAGE, "largeur": 5000}, {**IMAGE, "mime": "image/gif"}, {**IMAGE, "b64": "%%%"}, "x"):
        with pytest.raises(ValueError):
            asyncio.run(A.demander(dict(corps, image=image)))
    with pytest.raises(A.CoutChange):
        asyncio.run(A.demander(dict(corps, max_usd=0.0)))      # coût recalculé > accepté : rien n'est envoyé


def test_etat_dit_quels_moteurs_voient(monkeypatch):
    monkeypatch.setattr(MT, "etat", lambda: [{"moteur": m, "nom": m, "configure": True, "fautif": False}
                                              for m in ("anthropic", "ollama")])
    monkeypatch.setattr(MT, "vision", lambda m, mod=None: m == "anthropic")
    j = A.etat()
    assert {m["moteur"]: m["vision"] for m in j["moteurs"]} == {"anthropic": True, "ollama": False}
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY -m pytest tests/test_agent_vision.py -q`.
Attendu : `AttributeError: … has no attribute 'estimer_vue'` (et `CoutChange`), `KeyError: 'vision'`.

- [ ] **Étape 3 : implémenter**

En tête de `agent_aide.py`, ajouter `import asyncio`, `import math` et `import unicodedata` aux imports. Après `SANS_CLE = {...}` :

```python
# A5 : la vision en secours. La consigne voyage dans la QUESTION (le système reste identique d'un appel à l'autre).
COTE_MAX = 1280                 # l'écran réduit la capture à 1 280 px au plus sur son grand côté
VUE_NOMINALE = (1280, 800)      # le devis se calcule sur cette taille : même texte au devis et à l'envoi
MAX_IMAGE_B64 = 6_000_000
EPS_USD = 0.0001                # une unité d'arrondi du devis (4 décimales)
CONSIGNE_VUE = {
    "fr": "Une capture de l'écran visible est jointe ({l}×{h} px). Trouve l'élément qui répond à la question et "
          "termine par [POINT:x,y:libellé] : x et y en pixels DE LA CAPTURE, au centre de l'élément ; libellé = son "
          "nom en 3 mots au plus. Si l'élément n'est pas sur la capture, dis-le, sans balise POINT.",
    "en": "A capture of the visible screen is attached ({l}×{h} px). Find the element that answers the question and "
          "end with [POINT:x,y:label]: x and y in pixels OF THE CAPTURE, at the centre of the element; label = its "
          "name in 3 words at most. If the element is not on the capture, say so, with no POINT tag.",
}


class CoutChange(Exception):
    """Le coût recalculé dépasse le montant accepté par l'utilisateur : rien n'est envoyé (409 sur la route)."""
```

Le libellé de balise doit être identique dans les deux langues pour le test (`[POINT:x,y:libellé]` en français) :
le test vérifie la version française.

Remplacer `demander` (et ajouter les fonctions qui le précèdent) par :

```python
def _image(im) -> tuple[dict, list]:
    """({largeur, hauteur}, [{mime, b64}]) d'une capture jointe ; ValueError si elle est illisible."""
    from app.services import moteurs_texte as MT
    if not isinstance(im, dict):
        raise ValueError("Image jointe illisible.")
    l, h, b64 = im.get("largeur"), im.get("hauteur"), im.get("b64")
    if not all(isinstance(v, int) and not isinstance(v, bool) and 0 < v <= COTE_MAX for v in (l, h)) \
            or not isinstance(b64, str) or len(b64) > MAX_IMAGE_B64:
        raise ValueError("Image jointe illisible.")
    try:
        images = MT.images_valides([{"mime": im.get("mime"), "b64": b64}])
    except RuntimeError as e:
        raise ValueError(str(e)) from None
    return {"largeur": l, "hauteur": h}, images


def _preparer(corps, lang: str) -> dict:
    """La question validée, le moteur, et les prompts d'un appel : `prompt` (envoyé), `devis` (consigne de vue à la
    taille nominale : le texte que chiffrent le devis ET la vérification de `max_usd`)."""
    if not isinstance(corps, dict):
        raise ValueError("Corps JSON attendu.")
    q = corps.get("question")
    q = q.strip()[:MAX_QUESTION] if isinstance(q, str) else ""
    if not q:
        raise ValueError("La question est vide.")
    lang = "en" if (corps.get("lang") or lang) == "en" else "fr"
    ecran = corps.get("ecran") if corps.get("ecran") in VUES else ""
    demande = corps.get("moteur").strip() if isinstance(corps.get("moteur"), str) else ""
    image, images = _image(corps["image"]) if corps.get("image") is not None else (None, None)
    base = _historique(corps.get("historique")) + q
    vue = "\n\n" + CONSIGNE_VUE[lang]
    return {"q": q, "lang": lang, "ecran": ecran, "moteur": choisir_moteur(demande), "image": image,
            "images": images,
            "prompt": base + (vue.format(l=image["largeur"], h=image["hauteur"]) if image else ""),
            "devis": base + vue.format(l=VUE_NOMINALE[0], h=VUE_NOMINALE[1])}


def _cout(p: dict, sys_txt: str) -> float:
    """Le coût estimé (USD, 4 décimales) d'un appel AVEC capture pour cette question."""
    from app.services import moteurs_texte as MT
    from app.services import pricing as PR
    op = MT.estimer(p["moteur"], p["devis"], sys_txt, MAX_TOKENS, "low", images=1)
    return round(float(PR.estimate(op).get("total_usd") or 0.0), 4)


def estimer_vue(corps, lang: str = "fr") -> dict:
    """Le devis GRATUIT d'un appel avec capture : {moteur, nom, usd, cout, vision}. Aucune image n'est lue ici."""
    from app.services import moteurs_texte as MT
    if isinstance(corps, dict) and "image" in corps:
        corps = {k: v for k, v in corps.items() if k != "image"}
    p = _preparer(corps, lang)
    if not p["moteur"]:
        return {"moteur": "", "nom": "", "usd": 0.0, "cout": "", "vision": False}
    return {"moteur": p["moteur"], "nom": MT.nom(p["moteur"]), "cout": MT.nature_cout(p["moteur"]),
            "vision": MT.vision(p["moteur"]), "usd": _cout(p, systeme(p["ecran"], p["lang"], _espace()))}


async def demander(corps, lang: str = "fr") -> dict:
    """{texte, actions, moteur, nom, rejets, sans_cle}. ValueError : corps, question ou capture invalides.
    CoutChange : le coût d'un appel avec capture dépasse `max_usd`. RuntimeError : le moteur a échoué.
    HTTPException 402 : plafond « aide » (remonte tel quel jusqu'au dialogue de l'écran)."""
    from app.services import moteurs_texte as MT
    p = _preparer(corps, lang)
    lang, moteur = p["lang"], p["moteur"]
    if not moteur:
        _, actions, _ = analyser("[POINT:reglages.cles] [GUIDE:cles]")
        return {"texte": SANS_CLE[lang], "actions": actions, "moteur": "", "nom": "", "rejets": 0, "sans_cle": True}
    sys_txt = systeme(p["ecran"], lang, _espace())
    if p["images"]:
        if not await asyncio.to_thread(MT.vision, moteur):
            raise ValueError("Ce moteur ne lit pas les images : choisis-en un qui voit l'écran.")
        mx = corps.get("max_usd")
        if isinstance(mx, bool) or not isinstance(mx, (int, float)):
            raise ValueError("Montant accepté (max_usd) manquant ou invalide.")
        try:
            mx = float(mx)              # un entier géant (10**400) lève OverflowError
        except (OverflowError, ValueError):
            raise ValueError("Montant accepté (max_usd) manquant ou invalide.") from None
        if not math.isfinite(mx) or mx < 0:
            raise ValueError("Montant accepté (max_usd) manquant ou invalide.")
        if await asyncio.to_thread(_cout, p, sys_txt) > mx + EPS_USD:      # peut interroger Ollama (synchrone)
            raise CoutChange()
    sortie = await MT.tirer_garde(moteur, "", p["prompt"], sys_txt, MAX_TOKENS, categorie="aide", effort="low",
                                  images=p["images"])
    texte, actions, rejets = analyser(sortie, p["image"])
    if not texte:
        if actions:
            texte = REPONSE_VIDE[lang]
        else:
            texte = SANS_REPONSE[lang]
            actions = analyser("[GUIDE:tour]")[1]
    if rejets:
        logger.info(f"agent_aide : {rejets} balise(s) inconnue(s) retirée(s) ({moteur})")
    return {"texte": texte, "actions": actions, "moteur": moteur, "nom": MT.nom(moteur), "rejets": rejets,
            "sans_cle": False}
```

Dans `etat`, la liste des moteurs devient :

```python
    moteurs = [{"moteur": l["moteur"], "nom": l["nom"], "cout": MT.nature_cout(l["moteur"]),
                "vision": MT.vision(l["moteur"])}
               for l in MT.etat() if l["configure"] and not l.get("fautif")]
```

- [ ] **Étape 4 : lancer et voir réussir**

Lancer : `& $PY -m pytest tests/test_agent_vision.py tests/test_agent_aide.py -q` → aucun échec.
Le test historique `test_demander_appelle_tirer_garde` passe toujours (`faux` accepte `**kw`).

- [ ] **Étape 5 : commiter**

```bash
git commit --only backend/app/services/agent_aide.py backend/tests/test_agent_vision.py -m "agent : devis gratuit et appel avec capture sous max_usd (A5)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 5 : A5, les routes `/api/agent/estimer` et `/demander` avec capture, messages traduits

**Fichiers :** `backend/app/api/agent_routes.py`, `backend/tests/test_agent_vision.py`,
`scripts/i18n_l10_traductions.json`, `backend/app/i18n/erreurs.json`

- [ ] **Étape 1 : ajouter les tests qui échouent**

Ajouter avant le lanceur de `backend/tests/test_agent_vision.py` :

```python
from fastapi.testclient import TestClient                                   # noqa: E402


def _client():
    from app.main import app
    return TestClient(app)


def test_route_estimer(monkeypatch):
    monkeypatch.setattr(A, "estimer_vue", lambda corps, lang="fr": {"moteur": "x", "usd": 0.01, "lang": lang})
    c = _client()
    r = c.post("/api/agent/estimer", json={"question": "q"}, headers={"Accept-Language": "en"})
    assert r.status_code == 200 and r.json()["lang"] == "en"
    assert c.post("/api/agent/estimer", content="pas du json",
                  headers={"Content-Type": "application/json"}).status_code == 400


def test_route_demander_cout_change_409(monkeypatch):
    async def change(corps, lang="fr"):
        raise A.CoutChange()
    monkeypatch.setattr(A, "demander", change)
    r = _client().post("/api/agent/demander", json={"question": "q"})
    assert r.status_code == 409 and "accord" in r.json()["detail"]


def test_route_demander_trop_lourde():
    r = _client().post("/api/agent/demander", content=b"{" + b" " * 8_000_001 + b"}",
                       headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_messages_traduits():
    import json, subprocess
    racine = pathlib.Path(__file__).resolve().parents[2]
    r = subprocess.run([sys.executable, str(racine / "scripts" / "i18n_l10_erreurs.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", cwd=str(racine),
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-800:]
    t = json.loads((racine / "scripts" / "i18n_l10_traductions.json").read_text(encoding="utf-8"))
    assert "Image jointe illisible." in t and "Demande trop lourde." in t
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY -m pytest tests/test_agent_vision.py -q`.
Attendu : 404 sur `/api/agent/estimer`, 400 au lieu de 409, 200/400 au lieu de 413, `--check` en échec.

- [ ] **Étape 3 : implémenter les routes**

Remplacer le contenu de `backend/app/api/agent_routes.py` par :

```python
# -*- coding: utf-8 -*-
"""Assistant « Demander à Deepotus » (spec 2026-10-19-agent-aide-design.md, 19/10/2026) — /api/agent.

Boucle locale SEULEMENT, comme les Réglages : la question part vers le moteur de texte de l'utilisateur, sous le
plafond « aide » (le 402 `dz_plafond` remonte tel quel jusqu'au dialogue de /shared/dz-plafonds.js).
A5 : `/estimer` donne le devis GRATUIT d'un appel avec capture ; `/demander` porte alors `image` et `max_usd` (409 si
le coût recalculé dépasse le montant accepté).
"""
import asyncio
import json

from fastapi import APIRouter, HTTPException, Request

from app.services import agent_aide as A

router = APIRouter()

_HOTES_LOCAUX = ("127.0.0.1", "::1", "localhost", "testclient")
MAX_CORPS = 8_000_000           # une capture JPEG de 1 280 px tient très en dessous


def _local(request: Request) -> None:
    host = (request.client.host if request.client else "") or ""
    if host not in _HOTES_LOCAUX:
        raise HTTPException(403, "L'assistant n'est accessible que depuis ce PC.")


async def _corps(request: Request):
    try:
        taille = int(request.headers.get("content-length") or 0)
    except ValueError:
        taille = 0
    if taille > MAX_CORPS:
        raise HTTPException(413, "Demande trop lourde.")        # refus AVANT de lire
    morceaux, total = [], 0
    async for morceau in request.stream():                       # lecture en flux, coupée à MAX_CORPS + 1 octets
        total += len(morceau)
        if total > MAX_CORPS:
            raise HTTPException(413, "Demande trop lourde.")
        morceaux.append(morceau)
    brut = b"".join(morceaux)
    try:
        return json.loads(brut or b"null")
    except ValueError:
        raise HTTPException(400, "Corps JSON attendu.") from None


@router.get("/etat")
async def etat(request: Request):
    _local(request)
    return await asyncio.to_thread(A.etat)      # la vision d'Ollama et la voix interrogent des serveurs locaux


@router.post("/estimer")
async def estimer(request: Request):
    _local(request)
    corps = await _corps(request)
    from app.i18n import langue_requete
    try:
        return await asyncio.to_thread(A.estimer_vue, corps, langue_requete(request))
    except ValueError as e:
        raise HTTPException(400, str(e)) from None


@router.post("/demander")
async def demander(request: Request):
    _local(request)
    corps = await _corps(request)
    from app.i18n import langue_requete
    try:
        return await A.demander(corps, langue_requete(request))
    except A.CoutChange:
        raise HTTPException(409, "Le coût a changé depuis ton accord : rien n'a été envoyé. Redemande.") from None
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from None
```

Note : `test_route_demander` de `test_agent_aide.py` envoie `content="pas du json"` → `json.loads` lève `ValueError`
(`JSONDecodeError`) → 400, comportement inchangé.

- [ ] **Étape 4 : traduire les nouveaux messages**

Lancer (depuis la racine) : `& $PY scripts/i18n_l10_erreurs.py --manquants $env:TEMP\agent_a5_manquants.json`, puis lire
ce fichier : il donne les gabarits EXACTS. Ajouter à la FIN de `scripts/i18n_l10_traductions.json` (sans retrier) une
entrée par gabarit, avec ces traductions :

| Gabarit (fr, source) | en |
|---|---|
| `au plus {MAX_IMAGES} images par appel` | `at most {MAX_IMAGES} images per call` |
| `image illisible : type ou contenu manquant` | `unreadable image: type or content missing` |
| `image illisible : base64 invalide` | `unreadable image: invalid base64` |
| `image trop lourde (4,5 Mo au plus)` | `image too large (4.5 MB at most)` |
| `le modèle {mod} ne lit pas les images` | `the model {mod} cannot read images` |
| `images illisibles : liste attendue` | `unreadable images: a list is expected` |
| `Image jointe illisible.` | `The attached image is unreadable.` |
| `Ce moteur ne lit pas les images : choisis-en un qui voit l'écran.` | `This engine cannot read images: choose one that can see the screen.` |
| `Montant accepté (max_usd) manquant ou invalide.` | `Accepted amount (max_usd) missing or invalid.` |
| `Le coût a changé depuis ton accord : rien n'a été envoyé. Redemande.` | `The cost changed since you agreed: nothing was sent. Ask again.` |
| `Demande trop lourde.` | `Request too large.` |

Format d'une entrée (les variables restent identiques des deux côtés) :

```json
 "Demande trop lourde.": {
  "fr": "Demande trop lourde.",
  "en": "Request too large."
 }
```

Si `--manquants` nomme une variable autrement (par exemple `{mod}`), recopier le gabarit EXACT qu'il donne. Puis :
`& $PY scripts/i18n_l10_erreurs.py` et `& $PY scripts/i18n_l10_erreurs.py --check` → code 0.

- [ ] **Étape 5 : lancer et voir réussir**

Lancer : `& $PY -m pytest tests/test_agent_vision.py tests/test_agent_aide.py -q` → aucun échec.
Puis `& $PY tests/test_studio_motion_guide.py` (depuis la racine : `& $PY backend/tests/test_studio_motion_guide.py`)
→ aucun FAIL sur le contrôle L10.

- [ ] **Étape 6 : commiter**

```bash
git commit --only backend/app/api/agent_routes.py backend/tests/test_agent_vision.py scripts/i18n_l10_traductions.json backend/app/i18n/erreurs.json -m "agent : routes /estimer et /demander avec capture, messages traduits (A5)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 6 : A5, `AGENT.md` apprend `[VOIR]`

**Fichiers :** `docs/agent/AGENT.md` (section « Comment répondre »), `backend/tests/test_agent_connaissance.py`

- [ ] **Étape 1 : ajouter le test qui échoue**

Ajouter avant le lanceur de `backend/tests/test_agent_connaissance.py` :

```python
def test_agent_md_explique_voir():
    t = (RACINE / "docs" / "agent" / "AGENT.md").read_text(encoding="utf-8")
    regle = t.split("## Comment répondre", 1)[1].split("## Tenir ce fichier à jour", 1)[0]
    assert "`[VOIR]`" in regle and "aucune ancre" in regle
    assert "[POINT:x,y" not in t, "les coordonnées ne s'écrivent qu'après une capture : la consigne les demande"
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY -m pytest tests/test_agent_connaissance.py -q` → échec sur `[VOIR]`.

- [ ] **Étape 3 : modifier `AGENT.md`**

Dans `docs/agent/AGENT.md`, la règle 2 de « Comment répondre » devient :

```markdown
2. Termine par les balises utiles, chacune seule sur une ligne :
   - `[POINT:<ancre>]` pour montrer un élément (une ancre de la liste « Ancres » ci-dessous, rien d'autre) ;
   - `[ALLER:<vue>]` pour ouvrir un écran ;
   - `[GUIDE:<chapitre>]` pour ouvrir le chapitre du guide (un id de la liste « Chapitres »).
   - `[VOIR]` quand l'utilisateur cherche un élément précis de l'écran et qu'aucune ancre de la liste ne lui
     correspond : l'écran lui proposera de te montrer une capture (avec son accord, coût affiché). Ajoute aussi le
     `[GUIDE:<chapitre>]` le plus proche, au cas où il refuse.
   Au plus 3 balises. Une balise inconnue est supprimée : n'en invente jamais.
```

et ajouter la règle 8 :

```markdown
8. L'utilisateur peut dicter sa question (micro du tiroir) et faire lire ta réponse à voix haute : écris des phrases
   qui se disent bien, sans tableau ni liste imbriquée.
```

- [ ] **Étape 4 : lancer et voir réussir**

Lancer : `& $PY -m pytest tests/test_agent_connaissance.py tests/test_agent_aide.py -q` → aucun échec.

- [ ] **Étape 5 : commiter**

```bash
git commit --only docs/agent/AGENT.md backend/tests/test_agent_connaissance.py -m "agent : AGENT.md explique [VOIR], la dictée et la lecture (A5)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 7 : A5, la logique pure de la capture et du pointage par coordonnées

**Fichiers :** `frontend/shared/dz-agent-logique.js`, `frontend/shared/qa/agent_logique.test.mjs`

- [ ] **Étape 1 : ajouter les tests qui échouent**

Dans `frontend/shared/qa/agent_logique.test.mjs`, juste avant le bloc « 6. le module n'utilise aucun objet du
navigateur à l'import », ajouter :

```js
// 8. A5 : capture réduite, point de la capture → écran, même onglet, élément cliquable, prix, étapes
assert.deepEqual(L.reduire(2560, 1440), { l: 1280, h: 720 });
assert.deepEqual(L.reduire(800, 600), { l: 800, h: 600 }, "jamais agrandie");
assert.deepEqual(L.reduire(1000, 3000), { l: 427, h: 1280 });
assert.equal(L.reduire(0, 10), null);
assert.equal(L.COTE_MAX, 1280);
const p5 = { x: 640, y: 360, largeur: 1280, hauteur: 720 };
assert.deepEqual(L.versEcran(p5, { l: 1920, h: 1080 }), { x: 960, y: 540 });
assert.deepEqual(L.versEcran({ ...p5, x: 5000, y: -3 }, { l: 1920, h: 1080 }), { x: 1920, y: 0 }, "borné");
assert.equal(L.versEcran({ x: 1, y: 1, largeur: 0, hauteur: 0 }, { l: 10, h: 10 }), null);
assert.equal(L.versEcran(p5, null), null);
assert.equal(L.versEcran({ ...p5, x: "a" }, { l: 10, h: 10 }), null);
assert.ok(L.memeOnglet(2560, 1314, { l: 1280, h: 657 }));
assert.ok(!L.memeOnglet(1920, 1080, { l: 1280, h: 657 }), "écran entier 16:9 contre un onglet plus bas : refusé");
assert.ok(!L.memeOnglet(0, 0, { l: 1, h: 1 }));
const nn = (tag, role, parent) => ({ tagName: tag, getAttribute: (k) => (k === "role" ? role : null), parentElement: parent || null });
const bt = nn("BUTTON", null), sp = nn("SPAN", null, bt);
assert.equal(L.cliquable(sp), bt, "remonte au bouton");
const onglet = nn("DIV", "tab");
assert.equal(L.cliquable(nn("I", null, onglet)), onglet, "rôle d'onglet");
assert.equal(L.cliquable(nn("DIV", null, nn("DIV", null))), null, "rien de cliquable : null");
assert.equal(L.cliquable(null), null);
let profond = bt;
for (let i = 0; i < 7; i++) profond = nn("SPAN", null, profond);
assert.equal(L.cliquable(profond), null, "6 niveaux au plus");
assert.equal(L.prix(0.01234, "fr"), "0,0123");
assert.equal(L.prix(0.01234, "en"), "0.0123");
assert.equal(L.prix("x", "fr"), "0,0000");
assert.deepEqual(L.etapes({ type: "voir", cible: "ecran" }, "quick"), [{ faire: "voir" }]);
assert.deepEqual(L.etapes({ type: "point_xy", x: 1, y: 2, largeur: 10, hauteur: 10 }, "quick"), [{ faire: "pointer_xy" }]);
assert.deepEqual(L.etapes({ type: "point_xy", x: "a", y: 2 }, "quick"), [], "coordonnées douteuses : rien");
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `node frontend/shared/qa/agent_logique.test.mjs` → `TypeError: L.reduire is not a function`.

- [ ] **Étape 3 : implémenter**

Dans `frontend/shared/dz-agent-logique.js`, dans `etapes`, juste avant `if (action.type !== "point") return [];` :

```js
  if (action.type === "voir") return [{ faire: "voir" }];
  if (action.type === "point_xy") return Number.isFinite(action.x) && Number.isFinite(action.y) ? [{ faire: "pointer_xy" }] : [];
```

Puis ajouter à la fin du fichier :

```js
// ── A5 : la vision en secours (capture de l'onglet, réponse en pixels de la capture) ──
export const COTE_MAX = 1280;

// la taille d'une capture réduite : grand côté ≤ max, proportions gardées, jamais agrandie
export function reduire(l, h, max = COTE_MAX) {
  if (!(l > 0 && h > 0)) return null;
  const k = Math.min(1, max / Math.max(l, h));
  return { l: Math.max(1, Math.round(l * k)), h: Math.max(1, Math.round(h * k)) };
}

// un point rendu en pixels de la capture → coordonnées de la fenêtre (vue : {l, h} au moment de la capture), borné
export function versEcran(a, vue) {
  if (!a || !vue || !(a.largeur > 0 && a.hauteur > 0) || !Number.isFinite(a.x) || !Number.isFinite(a.y)) return null;
  const x = Math.min(Math.max(0, a.x), a.largeur) * (vue.l / a.largeur);
  const y = Math.min(Math.max(0, a.y), a.hauteur) * (vue.h / a.hauteur);
  return { x: Math.round(x), y: Math.round(y) };
}

// l'image vient-elle de CET onglet ? même rapport largeur / hauteur que la fenêtre, à tol près
export function memeOnglet(l, h, vue, tol = 0.06) {
  if (!(l > 0 && h > 0) || !vue || !(vue.l > 0 && vue.h > 0)) return false;
  const r = vue.l / vue.h;
  return Math.abs(l / h - r) <= tol * r;
}

// l'élément à montrer sous un point : le plus proche ancêtre cliquable (6 niveaux au plus), sinon null
const CLIQUABLES = ["BUTTON", "A", "INPUT", "SELECT", "TEXTAREA", "LABEL", "SUMMARY"];
const ROLES = ["button", "tab", "menuitem", "link", "checkbox", "switch", "option"];
export function cliquable(n) {
  for (let x = n, i = 0; x && i < 6; x = x.parentElement, i++) {
    const role = x.getAttribute ? x.getAttribute("role") : null;
    if (CLIQUABLES.includes(x.tagName) || ROLES.includes(role)) return x;
  }
  return null;
}

// un montant en dollars, 4 décimales, virgule en français
export function prix(usd, lang) {
  const t = (Number(usd) || 0).toFixed(4);
  return lang === "en" ? t : t.replace(".", ",");
}
```

- [ ] **Étape 4 : lancer et voir réussir**

Lancer : `node frontend/shared/qa/agent_logique.test.mjs` → `agent_logique : OK`.

- [ ] **Étape 5 : copier et commiter**

```bash
cp frontend/shared/dz-agent-logique.js frontend/dist/shared/dz-agent-logique.js
git add frontend/dist/shared/dz-agent-logique.js
git commit --only frontend/shared/dz-agent-logique.js frontend/dist/shared/dz-agent-logique.js frontend/shared/qa/agent_logique.test.mjs -m "agent : logique pure de la capture et du pointage par coordonnées (A5)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 8 : A5, le module de capture `dz-agent-vision.js`

**Fichiers :** `frontend/shared/dz-agent-vision.js` (créé), `frontend/dist/shared/dz-agent-vision.js` (copie),
`backend/tests/test_agent_ecran.py`

- [ ] **Étape 1 : ajouter les tests qui échouent**

Dans `backend/tests/test_agent_ecran.py`, remplacer `FICHIERS = [...]` par :

```python
FICHIERS = ["dz-agent.js", "dz-agent-logique.js", "dz-agent-pointeur.js", "dz-agent-vision.js"]
```

et ajouter avant le lanceur :

```python
def test_capture_de_l_onglet():
    src = (SHARED / "dz-agent-vision.js").read_text(encoding="utf-8")
    assert "getDisplayMedia(" in src and "preferCurrentTab: true" in src
    assert 'displaySurface !== "browser"' in src and "memeOnglet(" in src, "seul CET onglet est accepté"
    assert "reduire(" in src and 'toDataURL("image/jpeg", 0.8)' in src
    assert src.count(".stop()") >= 1 and "finally" in src, "les pistes sont coupées quoi qu'il arrive"
    assert "avant()" in src and "apres()" in src, "le tiroir est masqué pendant la prise"
    assert "window.isSecureContext" in src
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY -m pytest tests/test_agent_ecran.py -q` → fichier absent.

- [ ] **Étape 3 : créer `frontend/shared/dz-agent-vision.js`**

```js
// dz-agent-vision.js — assistant « Demander à Deepotus », lot A5 (spec docs/superpowers/specs/2026-10-19-agent-aide-design.md
// § 2 « Vision en secours ») : UNE image de l'onglet courant, prise APRÈS l'accord de l'utilisateur dans le tiroir.
// getDisplayMedia (le navigateur demande lui-même le partage : second accord), une seule image, pistes coupées aussitôt.
// L'image est réduite à 1 280 px au plus (grand côté) et encodée en JPEG 0,8. Refus si l'utilisateur partage autre
// chose que CET onglet (les coordonnées rendues ne vaudraient rien). SOURCE : frontend/shared ; copie identique :
// frontend/dist/shared (banc backend/tests/test_agent_ecran.py).
import { reduire, memeOnglet } from "./dz-agent-logique.js";

export function captureDisponible() {
  const md = navigator.mediaDevices;
  return !!(window.isSecureContext && md && typeof md.getDisplayMedia === "function");
}

const image = () => new Promise((ok) => requestAnimationFrame(() => ok()));
// Les dimensions de l'image ET la taille de la fenêtre sont relevées dans le MÊME rappel : le bandeau « partage de cet
// onglet » du navigateur change la hauteur de la fenêtre au moment où il apparaît ou disparaît.
function nouvelleImage(video) {
  return new Promise((ok) => {
    const mesure = (meta) => ok({
      vw: (meta && meta.width) || video.videoWidth, vh: (meta && meta.height) || video.videoHeight,
      vue: { l: window.innerWidth, h: window.innerHeight },
    });
    const t = setTimeout(() => mesure(null), 600);
    if (typeof video.requestVideoFrameCallback === "function") video.requestVideoFrameCallback((_, meta) => { clearTimeout(t); mesure(meta); });
  });
}

// avant() masque le tiroir, apres() le rétablit. Rend {mime, b64, largeur, hauteur, vue:{l, h}}.
// Erreurs : NotAllowedError (partage refusé), Error("autre-surface") (pas cet onglet), Error("capture-vide").
export async function capturer({ avant, apres } = {}) {
  const flux = await navigator.mediaDevices.getDisplayMedia({
    video: { displaySurface: "browser" }, audio: false,
    preferCurrentTab: true, selfBrowserSurface: "include", surfaceSwitching: "exclude", monitorTypeSurfaces: "exclude",
  });
  try {
    const piste = flux.getVideoTracks()[0];
    const reglages = piste && piste.getSettings ? piste.getSettings() : {};
    if (reglages.displaySurface && reglages.displaySurface !== "browser") throw new Error("autre-surface");
    const video = document.createElement("video");
    video.muted = true;
    video.playsInline = true;
    video.srcObject = flux;
    await video.play();
    if (avant) avant();
    try {
      await image();
      await image();
      const { vw, vh, vue } = await nouvelleImage(video);     // une image prise APRÈS le masquage du tiroir
      if (!memeOnglet(vw, vh, vue)) throw new Error("autre-surface");
      const d = reduire(vw, vh);
      if (!d) throw new Error("capture-vide");
      const c = document.createElement("canvas");
      c.width = d.l;
      c.height = d.h;
      c.getContext("2d").drawImage(video, 0, 0, d.l, d.h);
      const url = c.toDataURL("image/jpeg", 0.8);
      return { mime: "image/jpeg", b64: url.slice(url.indexOf(",") + 1), largeur: d.l, hauteur: d.h, vue };
    } finally {
      if (apres) apres();
    }
  } finally {
    flux.getTracks().forEach((t) => t.stop());
  }
}
```

- [ ] **Étape 4 : copier, lancer et voir réussir**

```bash
cp frontend/shared/dz-agent-vision.js frontend/dist/shared/dz-agent-vision.js
```

Lancer : `& $PY -m pytest tests/test_agent_ecran.py -q` → aucun échec.

- [ ] **Étape 5 : commiter**

```bash
git add frontend/shared/dz-agent-vision.js frontend/dist/shared/dz-agent-vision.js
git commit --only frontend/shared/dz-agent-vision.js frontend/dist/shared/dz-agent-vision.js backend/tests/test_agent_ecran.py -m "agent : capture de l'onglet courant pour la vision en secours (A5)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 9 : A5, le tiroir demande l'accord, capture, envoie et pointe

**Fichiers :** `frontend/shared/dz-agent.js`, `frontend/shared/i18n/agent.json`, `frontend/dist/shared/dz-agent.js`,
dictionnaire assemblé (`frontend/shared/dz-i18n-dico.js` et sa copie dist, produits par `scripts/i18n_assembler.py`),
`backend/tests/test_agent_ecran.py`

- [ ] **Étape 1 : ajouter les tests qui échouent**

Ajouter avant le lanceur de `backend/tests/test_agent_ecran.py` :

```python
def test_vision_dans_le_tiroir():
    src = (SHARED / "dz-agent.js").read_text(encoding="utf-8")
    assert 'from "./dz-agent-vision.js"' in src
    r = src[src.index("async function regarder("):]
    assert r.index("captureDisponible()") < r.index("accord(") < r.index("capturer(") < r.index("envoyerVue("), \
        "disponibilité, accord (devis), capture, envoi : dans cet ordre"
    assert "/api/agent/estimer" in src and "max_usd" in src
    assert ".filter((m) => m.vision)" in src, "l'accord ne propose que les moteurs qui voient"
    assert 'e.faire === "voir"' in src and 'e.faire === "pointer_xy"' in src
    assert "versEcran(" in src and "cliquable(" in src and "document.elementFromPoint(" in src
    assert "occupe || enVue" in src, "une seule demande à la fois"


def test_libelles_vision():
    for k in ("agent.vision.voir", "agent.vision.accord", "agent.vision.accord_gratuit", "agent.vision.envoyer",
              "agent.vision.annuler", "agent.vision.moteur", "agent.vision.indisponible", "agent.vision.aucun_moteur",
              "agent.vision.refusee", "agent.vision.onglet", "agent.vision.ici", "agent.vision.devis"):
        assert k in I18N, k
    assert "${usd}" in I18N["agent.vision.accord"]["en"] and "{usd} $" in I18N["agent.vision.accord"]["fr"]
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY -m pytest tests/test_agent_ecran.py -q` → échecs sur `regarder` et les libellés.

- [ ] **Étape 3 : ajouter les libellés**

Ajouter à `frontend/shared/i18n/agent.json` (avant l'accolade finale, virgule après la dernière entrée existante) :

```json
  "agent.vision.voir": {"fr": "Regarder l'écran", "en": "Look at the screen"},
  "agent.vision.devis": {"fr": "Je calcule le coût…", "en": "Working out the cost…"},
  "agent.vision.accord": {"fr": "Pour trouver ce bouton, je dois voir l'écran : une capture de cet onglet part vers {nom}, pour environ {usd} $ sous le plafond « aide ». Ton navigateur va ensuite te demander de partager l'onglet.", "en": "To find this button I need to see the screen: a capture of this tab goes to {nom}, for about ${usd} under the \"help\" cap. Your browser will then ask you to share the tab."},
  "agent.vision.accord_gratuit": {"fr": "Pour trouver ce bouton, je dois voir l'écran : une capture de cet onglet part vers {nom}, sur ce PC, gratuitement. Ton navigateur va ensuite te demander de partager l'onglet.", "en": "To find this button I need to see the screen: a capture of this tab goes to {nom}, on this PC, for free. Your browser will then ask you to share the tab."},
  "agent.vision.accord_inconnu": {"fr": "Pour trouver ce bouton, je dois voir l'écran : une capture de cet onglet part vers {nom}, pour un coût que ce fournisseur ne publie pas, sous le plafond « aide ». Ton navigateur va ensuite te demander de partager l'onglet.", "en": "To find this button I need to see the screen: a capture of this tab goes to {nom}, at a cost this provider does not publish, under the \"help\" cap. Your browser will then ask you to share the tab."},
  "agent.vision.envoyer": {"fr": "Capturer et envoyer", "en": "Capture and send"},
  "agent.vision.annuler": {"fr": "Annuler", "en": "Cancel"},
  "agent.vision.moteur": {"fr": "Moteur qui voit l'écran", "en": "Engine that can see the screen"},
  "agent.vision.indisponible": {"fr": "Ce navigateur ne sait pas capturer l'onglet. Le chapitre du guide t'aidera.", "en": "This browser cannot capture the tab. The guide chapter will help."},
  "agent.vision.aucun_moteur": {"fr": "Aucun moteur branché ne lit les images (il en faut un : Claude, GPT-4o ou plus récent, Gemini, ou un modèle Ollama « vision »). Le chapitre du guide t'aidera.", "en": "No connected engine can read images (you need one: Claude, GPT-4o or newer, Gemini, or an Ollama \"vision\" model). The guide chapter will help."},
  "agent.vision.refusee": {"fr": "Capture annulée : rien n'a été envoyé.", "en": "Capture cancelled: nothing was sent."},
  "agent.vision.onglet": {"fr": "Il faut partager « cet onglet », pas un autre onglet ni l'écran entier : rien n'a été envoyé.", "en": "You need to share \"this tab\", not another tab or the whole screen: nothing was sent."},
  "agent.vision.ici": {"fr": "Ici", "en": "Here"}
```

Puis (depuis la racine) : `& $PY scripts/i18n_assembler.py`.

- [ ] **Étape 4 : brancher la vision dans `frontend/shared/dz-agent.js`**

a) Imports (lignes 10-11) :

```js
import { etapes, historiqueBorne, choisir, composer, candidats, versEcran, cliquable, prix } from "./dz-agent-logique.js";
import { creerPointeur } from "./dz-agent-pointeur.js";
import { capturer, captureDisponible } from "./dz-agent-vision.js";
```

b) Ajouter au CSS (fin de la chaîne du `<style>`, avant le backtick fermant) :

```css
.dzAgentAccord select{margin:6px 0;background:var(--bg-panel-2,#1c1c21);color:inherit;border:1px solid var(--stroke,#2a2930);border-radius:6px}
.dzAgentAccord p{margin:0}
```

c) Remplacer `chargerMoteurs` par une version qui garde l'état, et ajouter `moteursConnus` :

```js
  let etatAgent = null;     // réponse de /api/agent/etat (moteurs avec cout et vision ; voix en A6)
  let chargement = null;    // la promesse du chargement en cours ; remise à null à chaque ouverture du tiroir
  function chargerMoteurs() {
    if (chargement) return chargement;
    chargement = (async () => {
      try {
        const r = await fetch("/api/agent/etat");
        const j = await r.json();
        etatAgent = j;
        choix.replaceChildren(el("option", { value: "", texte: T("agent.moteur.auto") }),
          ...j.moteurs.map((m) => el("option", { value: m.moteur,
            texte: `${m.nom} · ${T(m.cout === "gratuit" ? "agent.moteur.cout_gratuit" : "agent.moteur.cout_payant")}` })));
        choix.value = lire(window.localStorage, "dz_agent_moteur") || "";
      } catch (e) { chargement = null; }
    })();
    return chargement;
  }
  async function moteursConnus() {
    await chargerMoteurs();
    return etatAgent && Array.isArray(etatAgent.moteurs) ? etatAgent.moteurs : [];
  }
```

d) Remplacer `boutonAction` et la ligne qui l'appelle dans `dessiner` :

```js
  // actionsDuMessage : toutes les actions du message d'où vient le clic (l'ancre introuvable renvoie vers ses guides)
  function boutonAction(a, actionsDuMessage, msg) {
    const l = lang();
    const libelle = a.type === "point" ? T("agent.action.montrer", { libelle: a[l] || a.fr })
      : a.type === "point_xy" ? T("agent.action.montrer", { libelle: a.libelle || T("agent.vision.ici") })
      : a.type === "voir" ? T("agent.vision.voir")
      : a.type === "guide" ? T("agent.action.guide", { titre: a[l] || a.fr }) : T("agent.action.aller");
    return el("button", { texte: libelle, on: { click: () => executer(a, actionsDuMessage, msg) } });
  }
```

et, dans `dessiner` :

```js
      if (m.actions && m.actions.length) b.appendChild(el("div", { class: "dzAgentActions" }, m.actions.map((x) => boutonAction(x, m.actions, m))));
```

e) Dans `envoyer` : la garde d'entrée devient `if (!q || occupe || enVue) return;` et la réponse garde sa question
(pour la capture) :

```js
      hist.push({ role: "assistant", texte: j.texte, actions: Array.isArray(j.actions) ? j.actions : [],
        question: q, avant });
```

et `btnNouvelle` : `on: { click: () => { if (occupe || enVue) return; hist = []; garder(); dessiner(); } }`.
Déclarer `let enVue = false;` juste à côté de `let occupe = false;`.

f) Ajouter, après la fonction `pointer`, la vision en secours :

```js
  // ── A5 : la vision en secours. Accord (moteurs qui voient, devis gratuit), capture de CET onglet tiroir masqué,
  // second appel avec max_usd = le montant affiché, puis pointage du premier point rendu.
  const cacher = () => { effacerPointeur(); tiroir.style.visibility = "hidden"; bouton.style.visibility = "hidden"; };
  const reafficher = () => { tiroir.style.visibility = ""; bouton.style.visibility = ""; };
  function dire(cle, guides) {
    hist.push({ role: "assistant", texte: T(cle), actions: guides || [], erreur: true });
    garder(); dessiner();
  }

  // rend {moteur, usd} accepté, ou null (annulé)
  function accord(vus, corps) {
    return new Promise((fin) => {
      const texte = el("p", { texte: T("agent.vision.devis") });
      const sel = el("select", { "aria-label": T("agent.vision.moteur"), title: T("agent.vision.moteur") },
        vus.map((m) => el("option", { value: m.moteur, texte: m.nom })));
      sel.value = (vus.find((m) => m.moteur === choix.value) || vus[0]).moteur;
      if (vus.length < 2) sel.hidden = true;
      const oui = el("button", { texte: T("agent.vision.envoyer") });
      const non = el("button", { texte: T("agent.vision.annuler") });
      const boite = el("div", { class: "dzAgentMsg dzAgentAccord", "data-role": "assistant", role: "group" },
        [texte, sel, el("div", { class: "dzAgentActions" }, [oui, non])]);
      let devis = null, tour = 0;
      const fermer = (r) => { boiteAccord = null; boite.remove(); fin(r); };
      async function chiffrer() {
        const moi = ++tour;
        oui.disabled = true; devis = null;
        texte.textContent = T("agent.vision.devis");
        try {
          const r = await fetch("/api/agent/estimer", { method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...corps, moteur: sel.value }) });
          const j = await r.json().catch(() => ({}));
          if (moi !== tour) return;
          if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : String(r.status));
          devis = j;
          texte.textContent = j.cout === "gratuit" ? T("agent.vision.accord_gratuit", { nom: j.nom })
            : j.cout === "a_mesurer" ? T("agent.vision.accord_inconnu", { nom: j.nom })
            : T("agent.vision.accord", { nom: j.nom, usd: prix(j.usd, lang()) });
          oui.disabled = !j.vision;
          if (j.vision) oui.focus();
        } catch (e) { if (moi === tour) texte.textContent = T("agent.reponse.erreur", { msg: (e && e.message) || "—" }); }
      }
      sel.addEventListener("change", chiffrer);
      oui.addEventListener("click", () => { if (devis) fermer({ moteur: devis.moteur, usd: devis.usd }); });
      non.addEventListener("click", () => fermer(null));
      boiteAccord = boite;
      fil.appendChild(boite);
      fil.scrollTop = fil.scrollHeight;
      chiffrer();
    });
  }

  async function regarder(msg, actionsDuMessage) {
    if (occupe || enVue || !msg || !msg.question) return;
    enVue = true;                                  // dès l'entrée : aucune autre demande pendant le chargement
    btnEnvoyer.disabled = true;
    try {
      const guides = (actionsDuMessage || []).filter((x) => x && x.type === "guide");
      if (!captureDisponible()) return dire("agent.vision.indisponible", guides);
      const vus = (await moteursConnus()).filter((m) => m.vision);
      if (!vus.length) return dire("agent.vision.aucun_moteur", guides);
      const corps = { question: msg.question, historique: msg.avant || [], ecran: vue(), lang: lang() };
      const ok = await accord(vus, corps);
      if (!ok) return;
      let cap;
      try { cap = await capturer({ avant: cacher, apres: reafficher }); }
      catch (e) {
        return dire(e && e.name === "NotAllowedError" ? "agent.vision.refusee"
          : e && e.message === "autre-surface" ? "agent.vision.onglet" : "agent.vision.indisponible", guides);
      }
      await envoyerVue({ ...corps, moteur: ok.moteur, max_usd: ok.usd,
        image: { mime: cap.mime, b64: cap.b64, largeur: cap.largeur, hauteur: cap.hauteur } }, cap.vue);
    } finally { enVue = false; btnEnvoyer.disabled = false; }
  }

  async function envoyerVue(corps, vueCapture) {
    occupe = true; btnEnvoyer.disabled = true; btnNouvelle.disabled = true;
    dessiner(true);
    let premier = null, actions = [];
    try {
      const r = await fetch("/api/agent/demander", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corps) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : String(r.status));
      if (typeof j.texte !== "string" || !j.texte.trim()) throw new Error("—");
      // pas de nouvelle demande de capture en réponse à une capture
      actions = (Array.isArray(j.actions) ? j.actions : []).filter((x) => x && x.type !== "voir").map((x) => (x && x.type === "point_xy" ? { ...x, vue: vueCapture } : x));
      hist.push({ role: "assistant", texte: j.texte, actions });
      premier = actions.find((x) => x && x.type === "point_xy") || null;
    } catch (e) {
      hist.push({ role: "assistant", texte: T("agent.reponse.erreur", { msg: (e && e.message) || "—" }), erreur: true });
    } finally {
      occupe = false; btnEnvoyer.disabled = false; btnNouvelle.disabled = false;
      garder(); dessiner();
    }
    if (premier) executer(premier, actions);       // à la Clicky : on montre tout de suite ce qu'on a trouvé
  }

  // un point rendu en pixels de la capture : l'élément cliquable dessous, sinon un petit halo sur le point
  async function pointerXY(a, moi) {
    effacerPointeur();
    const v = a.vue || { l: window.innerWidth, h: window.innerHeight };
    const p = versEcran(a, v);
    if (!p || moi !== tourPointeur) return;
    // le bandeau « partage de cet onglet » du navigateur réduit la fenêtre PENDANT la capture : si la hauteur a changé
    // depuis, un point du quart bas de la vue capturée (barres, boutons du bas) suit le bas de la fenêtre.
    if (window.innerHeight !== v.h && p.y > v.h * 0.75) p.y += window.innerHeight - v.h;
    // le tiroir couvre le point : on le ferme pour voir ce qu'il cachait (le point vient de la capture, tiroir masqué)
    const tb = tiroir.getBoundingClientRect();
    if (tiroir.dataset.ouvert === "1" && p.x >= tb.left && p.x <= tb.right && p.y >= tb.top && p.y <= tb.bottom) {
      basculer(false);
      await attendre(60);
      if (moi !== tourPointeur) return;
    }
    const sous = document.elementsFromPoint(p.x, p.y).find((e) => !tiroir.contains(e) && !bouton.contains(e));
    const n = sous && sous.tagName !== "IFRAME" ? cliquable(sous) : null;
    const libelle = a.libelle || T("agent.vision.ici");
    if (n) return montrer(n, libelle);
    montrer({ rect: () => ({ x: p.x - 16, y: p.y - 16, w: 32, h: 32 }) }, libelle);
  }
```

g) Remplacer `executer` :

```js
  // le jeton est pris AVANT toute navigation : un clic A (autre écran) puis un clic B (écran courant) → A abandonne
  async function executer(a, actionsDuMessage, msg) {
    const moi = ++tourPointeur;
    for (const e of etapes(a, vue())) {
      if (moi !== tourPointeur) return;
      if (e.faire === "aller") { aller(e.vue); await attendre(350); }
      else if (e.faire === "reglages") { ouvrirReglages(e.section); await attendre(300); }
      else if (e.faire === "guide") window.open("/guide/#" + e.chapitre, "_blank", "noopener");
      else if (e.faire === "pointer") await pointer(a, actionsDuMessage || [], moi);
      else if (e.faire === "pointer_xy") await pointerXY(a, moi);
      else if (e.faire === "voir") await regarder(msg, actionsDuMessage || []);
    }
  }
```

h) Corrections de revue (déjà reportées dans le code ci-dessus) à faire aussi dans le reste de `dz-agent.js` :
`let boiteAccord = null;` à côté de `let hist`, et `dessiner()` ajoute `if (boiteAccord) fil.appendChild(boiteAccord);`
avant le défilement ; `basculer(true)` fait `chargement = null; chargerMoteurs();` (clé ajoutée à chaud) ;
`regarder` pose `enVue = true` et désactive `btnEnvoyer` dès l'entrée (réactivé dans le `finally`) ; `pointerXY`
décale `y` du bandeau de partage, ferme le tiroir s'il couvre le point, puis lit `document.elementsFromPoint`.
Dans `dz-agent-vision.js`, `nouvelleImage` rend les dimensions de l'image et la taille de la fenêtre relevées dans le
même rappel de `requestVideoFrameCallback`. `memeOnglet` tolère 6 % (Tâche 7). Deux tests statiques de
`test_agent_ecran.py` (`test_corrections_de_revue_du_tiroir`, `test_capture_meme_image_pour_vue_et_taille`) les gardent.

- [ ] **Étape 5 : copier, lancer et voir réussir**

```bash
cp frontend/shared/dz-agent.js frontend/dist/shared/dz-agent.js
```

Lancer : `& $PY -m pytest tests/test_agent_ecran.py -q` et `node frontend/shared/qa/agent_logique.test.mjs` → aucun
échec. Lancer aussi `& $PY tests/test_i18n_l0.py` (clés à 3 segments) → aucun FAIL.

- [ ] **Étape 6 : commiter**

Lister les fichiers produits par l'assembleur avec `git status --short`, puis :

```bash
git commit --only frontend/shared/dz-agent.js frontend/dist/shared/dz-agent.js frontend/shared/i18n/agent.json frontend/shared/dz-i18n-dico.js frontend/dist/shared/dz-i18n-dico.js backend/tests/test_agent_ecran.py -m "agent : le tiroir regarde l'écran avec accord et coût affiché (A5)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

(Ajouter à `--only` tout autre fichier que `git status` montre modifié par `i18n_assembler.py`.)

---

### Tâche 10 : A5, preuve à l'écran

**Fichiers :** aucun (preuve). Le backend de preuve de la tâche 16 peut servir ici s'il est déjà écrit ; sinon :

- [ ] **Étape 1 : lancer un backend de preuve avec un faux moteur qui voit**

Écrire dans le dossier scratchpad un script `preuve_a5.py` copié de `scripts/guide/serve_guide_motion.py` (port 8815,
faux Ollama 8816) dont le faux Ollama répond :
- à `/api/show` : `{"capabilities": ["completion", "vision"]}` pour `llava-demo` ;
- à `/api/generate` **sans** `images` : `"Je ne connais pas ce bouton.\n[VOIR]\n[GUIDE:tour]"` ;
- à `/api/generate` **avec** `images` : `"C'est ici.\n[POINT:40,300:Rail]"`.
Puis `CAC.appliquer({"OLLAMA_MODEL": "llava-demo"})`. (La tâche 16 en donne le code complet.)

- [ ] **Étape 2 : vérifier dans le navigateur intégré**

`preview_start` sur `http://127.0.0.1:8815/` ; F1 ; poser « où est le bouton machin ? » ; vérifier : bouton
« Regarder l'écran » ; clic → l'accord affiche « gratuitement » et « Capturer et envoyer » actif ; Annuler → la boîte
disparaît, rien n'est envoyé (`read_network_requests` : aucun `POST /api/agent/demander` après l'estimation).
Puis, Capturer : le navigateur intégré peut refuser `getDisplayMedia` (message `agent.vision.refusee` ou
`indisponible` attendu, sans erreur console) ; faire la capture réelle dans **Chrome de l'utilisateur** seulement s'il
l'accepte. Vérifier enfin le pointeur par la console :
`window.__dzAgentExecuter({type:"point_xy",x:40,y:300,largeur:1280,hauteur:800,libelle:"Rail",vue:{l:innerWidth,h:innerHeight}})`
→ halo sur l'élément cliquable du rail. Capture d'écran pour la preuve, FR puis EN (`dz_lang`).

- [ ] **Étape 3 : arrêter le backend de preuve** (`preview_stop`), rien à commiter.

---

# Lot A6 — la voix

### Tâche 11 : A6, `dz-champ-ia.js` ouvre sa dictée aux autres champs

**Fichiers :** `frontend/shared/dz-champ-ia.js` (`rafraichirMicro` ligne ~1387, `W.DzChampIA` ligne ~1700),
`frontend/dist/shared/dz-champ-ia.js`, `backend/tests/test_agent_voix.py` (créé)

- [ ] **Étape 1 : écrire le banc qui échoue**

Créer `backend/tests/test_agent_voix.py` :

```python
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


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY -m pytest tests/test_agent_voix.py -q` → échec sur `basculer: basculerDictee`.

- [ ] **Étape 3 : implémenter**

Dans `frontend/shared/dz-champ-ia.js`, juste avant `function rafraichirMicro(el) {`, ajouter :

```js
  /* A6 (assistant « Demander », 19/10/2026) : chaque changement d'état de la dictée d'un champ est annoncé sur le
     champ lui-même (`dzia-dictee`, detail {etat, voie}) — le tiroir de l'assistant, qui n'est pas un champ IA marqué,
     y règle son propre bouton micro. Une seule annonce par état. */
  function signalerDictee(el) {
    var a = dic.active && dic.active.el === el ? dic.active : null;
    var e = a ? a.etat : "repos";
    if (el.__dziaSignal === e) return;
    el.__dziaSignal = e;
    try { el.dispatchEvent(new W.CustomEvent("dzia-dictee", { detail: { etat: e, voie: a ? a.voie : voieDictee() } })); } catch (x) {}
  }
```

puis la première ligne du corps de `rafraichirMicro` devient l'appel, avant la lecture du micro :

```js
  function rafraichirMicro(el) {
    signalerDictee(el);
    var st = el.__dzia, b = st && st.micro;
    if (!b) return;
```

Enfin, dans `W.DzChampIA`, l'objet `dictee` devient :

```js
    dictee: {
      voie: voieDictee,
      etat: function () { var a = dic.active; return { etat: a ? a.etat : "repos", voie: a ? a.voie : voieDictee(), voie1Ko: dic.voie1Ko, indispo: indispo(), veille: !!tVeille }; },
      arreter: arreterDictee,
      basculer: basculerDictee      // A6 : la dictée pour un champ non marqué (le tiroir de l'assistant)
    }
```

`basculerDictee`, `ecouter`, `enregistrer`, `finirDictee` acceptent déjà un champ sans `__dzia` (`b` absent → aucun
bouton à rafraîchir) ; `inserer` pose le texte au curseur par le setter du prototype (React n'est pas concerné ici).

- [ ] **Étape 4 : copier, lancer et voir réussir**

```bash
cp frontend/shared/dz-champ-ia.js frontend/dist/shared/dz-champ-ia.js
```

Lancer : `& $PY -m pytest tests/test_agent_voix.py -q` → aucun échec ; `& $PY tests/test_champ_ia.py` et
`& $PY tests/test_p1_champ_ia_ecarts.py` → aucun FAIL (comparer à `origin/main` si un FAIL préexiste).

- [ ] **Étape 5 : commiter**

```bash
git commit --only frontend/shared/dz-champ-ia.js frontend/dist/shared/dz-champ-ia.js backend/tests/test_agent_voix.py -m "champs IA : dictee.basculer et événement dzia-dictee pour l'assistant (A6)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 12 : A6, le micro du tiroir

**Fichiers :** `frontend/shared/dz-agent.js`, `frontend/shared/i18n/agent.json`, copies dist, dictionnaire assemblé,
`backend/tests/test_agent_voix.py`

- [ ] **Étape 1 : ajouter les tests qui échouent**

Ajouter avant le lanceur de `backend/tests/test_agent_voix.py` :

```python
I18N = json.loads((SHARED / "i18n" / "agent.json").read_text(encoding="utf-8"))


def test_micro_du_tiroir():
    src = (SHARED / "dz-agent.js").read_text(encoding="utf-8")
    assert "DzChampIA.dictee" in src and ".basculer(saisie)" in src
    assert 'saisie.addEventListener("dzia-dictee"' in src
    assert 'glyphe("dz-media-dicter")' in src and '"dz-media-arret"' in src
    assert "dicteeEnCours()" in src, "Échap pendant la dictée l'arrête sans fermer le tiroir"
    for k in ("agent.voix.dicter", "agent.voix.arreter", "agent.voix.indisponible"):
        assert k in I18N and I18N[k]["fr"] and I18N[k]["en"], k
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY -m pytest tests/test_agent_voix.py -q` → échec.

- [ ] **Étape 3 : libellés**

Ajouter à `frontend/shared/i18n/agent.json` :

```json
  "agent.voix.dicter": {"fr": "Dicter la question", "en": "Dictate the question"},
  "agent.voix.arreter": {"fr": "Arrêter la dictée", "en": "Stop dictation"},
  "agent.voix.indisponible": {"fr": "La dictée n'est pas disponible sur cette page.", "en": "Dictation is not available on this page."}
```

Puis `& $PY scripts/i18n_assembler.py`.

- [ ] **Étape 4 : le bouton micro dans `frontend/shared/dz-agent.js`**

a) Après la définition de `el`, ajouter l'icône Deepotus Glyph :

```js
  const NS = "http://www.w3.org/2000/svg";
  const glyphe = (cle) => {
    const s = document.createElementNS(NS, "svg");
    for (const [k, v] of Object.entries({ class: "dzi", width: "16", height: "16", "aria-hidden": "true", focusable: "false", "data-dz-icone": cle })) s.setAttribute(k, v);
    const u = document.createElementNS(NS, "use");
    u.setAttribute("href", "/shared/icons/dz-icons.svg#" + cle);
    s.appendChild(u);
    return s;
  };
```

b) Au CSS : `.dzAgentPied button[aria-pressed="true"]{border-color:#ef4444;background:#b91c1c;color:#fff}`.

c) Après `btnEnvoyer`, créer le bouton et la logique :

```js
  // A6 : la dictée passe par la couche des champs IA (/shared/dz-champ-ia.js) : voie 1 du navigateur, voie 2
  // enregistrée avec devis et accord. Le tiroir ne règle que son bouton, sur l'événement `dzia-dictee`.
  const dictee = () => (window.DzChampIA && window.DzChampIA.dictee) || null;
  const dicteeEnCours = () => { const d = dictee(); try { return !!d && d.etat().etat !== "repos"; } catch (e) { return false; } };
  const btnMicro = el("button", { type: "button", "aria-pressed": "false", title: T("agent.voix.dicter"),
    "aria-label": T("agent.voix.dicter"), on: { click: () => {
      const d = dictee();
      if (!d || typeof d.basculer !== "function") return dire("agent.voix.indisponible");
      d.basculer(saisie);
    } } }, [glyphe("dz-media-dicter")]);
  saisie.addEventListener("dzia-dictee", (ev) => {
    const e = (ev.detail && ev.detail.etat) || "repos";
    const ecoute = e === "ecoute" || e === "prise";
    btnMicro.setAttribute("aria-pressed", ecoute ? "true" : "false");
    btnMicro.title = T(ecoute ? "agent.voix.arreter" : "agent.voix.dicter");
    btnMicro.setAttribute("aria-label", btnMicro.title);
    btnMicro.replaceChildren(glyphe(ecoute ? "dz-media-arret" : "dz-media-dicter"));
    btnMicro.dataset.etat = e;
  });
```

`dire` est défini en tâche 9 (f) ; le déplacer **avant** ce bloc s'il est plus bas dans le fichier (une fonction
déclarée par `function` est hissée : aucun déplacement n'est nécessaire).

d) Le pied devient `el("div", { class: "dzAgentPied" }, [saisie, btnMicro, btnEnvoyer])`.

e) Dans `basculer`, à la fermeture, arrêter une dictée en cours dans le tiroir :

```js
    if (o) { chargerMoteurs(); saisie.focus(); }
    else {
      if (dicteeEnCours()) { try { dictee().arreter(); } catch (e) { /* rien à arrêter */ } }
      if (focusDedans) bouton.focus();     // le focus ne reste pas dans un tiroir masqué
    }
```

f) Dans l'écouteur `keydown`, la branche Échap du tiroir ne ferme pas pendant une dictée (la couche des champs IA
l'arrête elle-même) :

```js
    else if (ev.key === "Escape" && tiroir.dataset.ouvert === "1" && tiroir.contains(ev.target) && !dicteeEnCours()) {
```

- [ ] **Étape 5 : copier, lancer et voir réussir**

```bash
cp frontend/shared/dz-agent.js frontend/dist/shared/dz-agent.js
```

Lancer : `& $PY -m pytest tests/test_agent_voix.py tests/test_agent_ecran.py -q` → aucun échec.

- [ ] **Étape 6 : commiter**

```bash
git commit --only frontend/shared/dz-agent.js frontend/dist/shared/dz-agent.js frontend/shared/i18n/agent.json frontend/shared/dz-i18n-dico.js frontend/dist/shared/dz-i18n-dico.js backend/tests/test_agent_voix.py -m "agent : dicter sa question depuis le tiroir (A6)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 13 : A6, la route de lecture `/api/agent/lire`

**Fichiers :** `backend/app/services/agent_aide.py` (lecture, `etat_voix`, `etat`), `backend/app/api/agent_routes.py`,
`backend/tests/_recensement_payant.py`, `backend/tests/test_plafonds_garde.py`, `backend/tests/test_agent_voix.py`,
`scripts/i18n_l10_traductions.json`, `backend/app/i18n/erreurs.json`

- [ ] **Étape 1 : ajouter les tests qui échouent**

Ajouter avant le lanceur de `backend/tests/test_agent_voix.py` :

```python
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
```

Dans `backend/tests/_recensement_payant.py`, ajouter à `MODULES` :

```python
    "agent": RACINE / "api" / "agent_routes.py",   # A6 : la lecture de l'assistant (ElevenLabs, ou Voicebox gratuit)
```

Dans `backend/tests/test_plafonds_garde.py`, ajouter à `PAYANTES` :

```python
    ("agent", "POST", "/lire"),   # A6 (19/10/2026) : la réponse de l'assistant lue à voix haute (garde « aide »)
```

et, après le témoin du Photolab (`anciens["photolab"] = …`) :

```python
# A6 : la route de lecture de l'assistant n'existait pas en bfec23e — même témoin : le source actuel privé de sa garde
_ag = (RP.MODULES["agent"]).read_text(encoding="utf-8")
anciens["agent"] = _ag.replace("_PLAF.verifier(", "_sans_garde(") if "_PLAF.verifier(" in _ag else None
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY -m pytest tests/test_agent_voix.py -q` → 404 sur `/api/agent/lire`, attributs absents.
Lancer : `& $PY tests/test_plafonds_garde.py` → FAIL A0 (`/lire` n'existe pas).

- [ ] **Étape 3 : implémenter le service**

Dans `backend/app/services/agent_aide.py`, ajouter `import hashlib` aux imports, puis à la fin du fichier :

```python
# ── A6 : la lecture à voix haute (voix des Réglages : Voicebox local gratuit, ElevenLabs payant) ──
MAX_LECTURE = 1500               # caractères lus au plus : une réponse de l'assistant tient en dessous
GARDER_LECTURES = 30             # MP3 gardés dans le cache (les plus récents)
NOMS_VOIX = {"elevenlabs": "ElevenLabs", "voicebox": "Voicebox"}


def texte_a_lire(t) -> str:
    """Le texte d'une réponse à lire : une chaîne, sans balise, espaces réduits, bornée."""
    if not isinstance(t, str):
        return ""
    return " ".join(BALISE.sub(" ", t).split())[:MAX_LECTURE]


def dossier_lectures() -> Path:
    """Le cache des lectures, À PART de la Bibliothèque (jamais listé comme un média de l'utilisateur)."""
    from app.config import settings
    d = settings.images_path.parent / "agent_lectures"
    d.mkdir(parents=True, exist_ok=True)
    return d


def chemin_lecture(fournisseur: str, lang: str, texte: str) -> Path:
    h = hashlib.sha1(f"{fournisseur}|{lang}|{texte}".encode("utf-8")).hexdigest()[:20]
    return dossier_lectures() / f"{h}.mp3"


def op_lecture(fournisseur: str, texte: str) -> dict | None:
    """L'op de la garde des plafonds : ElevenLabs au caractère ; Voicebox (local) ne coûte rien → None."""
    return {"kind": "elevenlabs", "chars": len(texte)} if fournisseur == "elevenlabs" else None


def elaguer_lectures(garder: int = GARDER_LECTURES) -> None:
    fichiers = sorted(dossier_lectures().glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in fichiers[garder:]:
        p.unlink(missing_ok=True)


def etat_voix() -> dict:
    """{fournisseur, nom, cout} de la voix des Réglages ; fournisseur "" : aucune voix (le tiroir cache « Lire »)."""
    from app.services import voice_providers as VP
    p = VP.resolve_provider()
    return {"fournisseur": p, "nom": NOMS_VOIX.get(p, ""),
            "cout": "gratuit" if p == "voicebox" else ("payant" if p else "")}
```

Dans `etat()`, ajouter la voix au dictionnaire rendu :

```python
    return {"moteur": choisir_moteur(), "moteurs": moteurs, "ancres": len(k["ancres"]),
            "chapitres": len(k["chapitres"]), "voix": etat_voix()}
```

- [ ] **Étape 4 : implémenter la route**

Dans `backend/app/api/agent_routes.py`, ajouter `from fastapi.responses import FileResponse` aux imports, puis à la
fin :

```python
@router.post("/lire")
async def lire(request: Request):
    """A6 : lit une réponse de l'assistant avec la voix des Réglages. Voicebox (local) est gratuit ; ElevenLabs passe
    par le plafond « aide ». Le MP3 va dans un cache à part, jamais dans la Bibliothèque ; une réponse déjà lue repart
    du cache sans rien dépenser."""
    _local(request)
    corps = await _corps(request)
    texte = A.texte_a_lire(corps.get("texte") if isinstance(corps, dict) else None)
    if not texte:
        raise HTTPException(400, "Rien à lire.")
    lang = "en" if isinstance(corps, dict) and corps.get("lang") == "en" else "fr"
    loop = asyncio.get_running_loop()
    from app.services import voice_providers as VP
    prov = await loop.run_in_executor(None, VP.resolve_provider)
    if not prov:
        raise HTTPException(503, "Aucune voix disponible : ajoute la clé ElevenLabs ou lance Voicebox (Réglages).")
    dest = A.chemin_lecture(prov, lang, texte)
    if not dest.is_file():
        op = A.op_lecture(prov, texte)
        if op:
            from app.services import plafonds as _PLAF
            await _PLAF.verifier(op, "aide")
        from app.services.elevenlabs_service import VoiceoverService
        tmp = dest.with_name(dest.stem + ".part.mp3")
        try:
            await loop.run_in_executor(None, lambda: VoiceoverService().generate_long(
                text=texte, output_path=tmp, language=lang, provider=prov))
            tmp.replace(dest)
        except Exception as e:  # noqa: BLE001 — la cause est rendue à l'écran, la clé n'y figure jamais
            tmp.unlink(missing_ok=True)
            raise HTTPException(502, f"Lecture impossible : {e}") from None
        await loop.run_in_executor(None, A.elaguer_lectures)
    return FileResponse(str(dest), media_type="audio/mpeg")
```

Note : la fausse voix des tests est une classe dont `generate_long` accepte `provider=` ; la vraie
(`VoiceoverService.generate_long`) l'accepte aussi (appelée ainsi par `/api/audio/voiceover`).

- [ ] **Étape 5 : traduire les nouveaux messages**

Comme en tâche 5 étape 4 (`--manquants`, ajout à la fin sans retrier, régénération, `--check`) :

| Gabarit (fr) | en |
|---|---|
| `Rien à lire.` | `Nothing to read.` |
| `Aucune voix disponible : ajoute la clé ElevenLabs ou lance Voicebox (Réglages).` | `No voice available: add the ElevenLabs key or start Voicebox (Settings).` |
| `Lecture impossible : {e}` | `Cannot read aloud: {e}` |

- [ ] **Étape 6 : lancer et voir réussir**

Lancer : `& $PY -m pytest tests/test_agent_voix.py tests/test_agent_aide.py tests/test_agent_vision.py -q` → aucun
échec. `& $PY tests/test_plafonds_garde.py` → aucun FAIL (A0, A1, A2, A4 compris).
`& $PY scripts/i18n_l10_erreurs.py --check` (depuis la racine) → code 0.

- [ ] **Étape 7 : commiter**

```bash
git commit --only backend/app/services/agent_aide.py backend/app/api/agent_routes.py backend/tests/test_agent_voix.py backend/tests/_recensement_payant.py backend/tests/test_plafonds_garde.py scripts/i18n_l10_traductions.json backend/app/i18n/erreurs.json -m "agent : lire la réponse avec la voix des Réglages, sous le plafond « aide » (A6)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 14 : A6, le bouton « Lire » sous chaque réponse

**Fichiers :** `frontend/shared/dz-agent.js`, `frontend/shared/i18n/agent.json`, copies dist, dictionnaire assemblé,
`backend/tests/test_agent_voix.py`

- [ ] **Étape 1 : ajouter le test qui échoue**

```python
def test_lecture_dans_le_tiroir():
    src = (SHARED / "dz-agent.js").read_text(encoding="utf-8")
    assert '"/api/agent/lire"' in src and "URL.revokeObjectURL(" in src and "new Audio(" in src
    assert "etatAgent.voix" in src, "le bouton n'apparaît que si une voix est disponible"
    assert 'glyphe("dz-media-audio")' in src
    for k in ("agent.voix.lire_gratuit", "agent.voix.lire_payant", "agent.voix.stop", "agent.voix.erreur"):
        assert k in I18N, k
    assert "{nom}" in I18N["agent.voix.lire_payant"]["fr"] and "{msg}" in I18N["agent.voix.erreur"]["en"]
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY -m pytest tests/test_agent_voix.py -q` → échec.

- [ ] **Étape 3 : libellés**

```json
  "agent.voix.lire_gratuit": {"fr": "Lire à voix haute ({nom}, gratuit)", "en": "Read aloud ({nom}, free)"},
  "agent.voix.lire_payant": {"fr": "Lire à voix haute ({nom}, payant, sous le plafond « aide »)", "en": "Read aloud ({nom}, paid, under the \"help\" cap)"},
  "agent.voix.stop": {"fr": "Arrêter la lecture", "en": "Stop reading"},
  "agent.voix.erreur": {"fr": "La lecture n'a pas pu se faire : {msg}", "en": "Reading aloud failed: {msg}"}
```

Puis `& $PY scripts/i18n_assembler.py`.

- [ ] **Étape 4 : implémenter dans `frontend/shared/dz-agent.js`**

a) Avant `dessiner`, la lecture :

```js
  // A6 : une réponse lue par la voix des Réglages (POST /api/agent/lire → MP3). Un clic sur le bouton en cours arrête.
  let lecture = null;     // {audio, url, bouton}
  function arreterLecture() {
    if (!lecture) return;
    const l = lecture; lecture = null;
    try { l.audio.pause(); } catch (e) { /* déjà arrêtée */ }
    URL.revokeObjectURL(l.url);
    l.bouton.setAttribute("aria-pressed", "false");
  }
  async function lireTexte(texte, b) {
    const deja = lecture && lecture.bouton === b;
    arreterLecture();
    if (deja) return;
    b.disabled = true;
    try {
      const r = await fetch("/api/agent/lire", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texte, lang: lang() }) });
      if (!r.ok) { const j = await r.json().catch(() => ({})); throw new Error(typeof j.detail === "string" ? j.detail : String(r.status)); }
      const url = URL.createObjectURL(await r.blob());
      const audio = new Audio(url);
      lecture = { audio, url, bouton: b };
      b.setAttribute("aria-pressed", "true");
      b.title = T("agent.voix.stop");
      audio.addEventListener("ended", () => { if (lecture && lecture.audio === audio) arreterLecture(); });
      await audio.play();
    } catch (e) {
      arreterLecture();
      hist.push({ role: "assistant", texte: T("agent.voix.erreur", { msg: (e && e.message) || "—" }), erreur: true });
      garder(); dessiner();
    } finally { b.disabled = false; }
  }
  function boutonLire(m) {
    const v = etatAgent && etatAgent.voix;
    if (!v || !v.fournisseur || m.role !== "assistant" || m.erreur || !m.texte) return null;
    const titre = T(v.cout === "gratuit" ? "agent.voix.lire_gratuit" : "agent.voix.lire_payant", { nom: v.nom });
    const b = el("button", { type: "button", title: titre, "aria-label": titre, "aria-pressed": "false" }, [glyphe("dz-media-audio")]);
    b.addEventListener("click", () => lireTexte(m.texte, b));
    return b;
  }
```

b) Dans `dessiner`, après l'ajout des boutons d'action, ajouter le bouton « Lire » (le message d'accueil n'a pas de
texte lisible utile ; il est exclu parce qu'il n'est pas dans `hist`) :

```js
    fil.replaceChildren(...msgs.map((m) => {
      const b = el("div", { class: "dzAgentMsg", "data-role": m.role, texte: m.texte });
      const boutons = (m.actions || []).map((x) => boutonAction(x, m.actions, m));
      const lireB = hist.includes(m) ? boutonLire(m) : null;
      if (lireB) boutons.push(lireB);
      if (boutons.length) b.appendChild(el("div", { class: "dzAgentActions" }, boutons));
      return b;
    }));
```

c) Dans `basculer`, à la fermeture, `arreterLecture();` ; et `btnNouvelle` appelle `arreterLecture()` avant de vider.

d) `chargerMoteurs` est appelé à l'ouverture du tiroir ; après son `await`, `dessiner()` doit être rappelé pour faire
apparaître les boutons « Lire » des réponses déjà là : dans `basculer`, `if (o) { chargerMoteurs().then(() => dessiner()); saisie.focus(); }`.

- [ ] **Étape 5 : copier, lancer et voir réussir**

```bash
cp frontend/shared/dz-agent.js frontend/dist/shared/dz-agent.js
```

Lancer : `& $PY -m pytest tests/test_agent_voix.py tests/test_agent_ecran.py -q` → aucun échec ;
`node frontend/shared/qa/agent_logique.test.mjs` → OK.

- [ ] **Étape 6 : commiter**

```bash
git commit --only frontend/shared/dz-agent.js frontend/dist/shared/dz-agent.js frontend/shared/i18n/agent.json frontend/shared/dz-i18n-dico.js frontend/dist/shared/dz-i18n-dico.js backend/tests/test_agent_voix.py -m "agent : lire une réponse à voix haute depuis le tiroir (A6)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

**Corrections de revue des Tâches 11-14 (déjà reportées dans le code livré ; le code des étapes ci-dessus est l'état AVANT revue) :**

- `/lire` : verrou par clé de cache au niveau du module (`_VERROUS_LECTURE`), `dest.is_file()` revérifié SOUS le verrou avant la garde ; MP3 temporaire `<stem>.<uuid>.part` ; clé du cache = `chemin_lecture(fournisseur, lang, texte, voix)` avec `voix_lecture()` (voix et modèle ElevenLabs de la langue, ou `VOICEBOX_URL`). Banc : deux lectures simultanées d'une seule boucle (httpx `ASGITransport`, pas `TestClient` : un verrou asyncio ne se partage pas entre boucles) → une garde, une génération.
- `elaguer_lectures` ignore les `.part`, les fichiers disparus et les erreurs d'`unlink` ; la route ne fait jamais échouer la réponse sur un échec d'élagage.
- Écran : `lecture = {ctrl, bouton, texte, msg, titre}` posée AVANT le `fetch` (`AbortController`), `arreterLecture` fait `ctrl.abort()`, `AbortError` ignorée, rien n'est joué si la lecture a été remplacée pendant le chargement, `audio` « error » → message, erreur → `dessiner(occupe)`, reprise de l'état au redessin par `lecture.msg === m`, `title` et `aria-label` restaurés dans les deux sens.
- Dictée : `DzChampIA.dictee.abandonner(el)` ; le tiroir l'appelle à la fermeture et ne regarde que l'état de SA dictée (`btnMicro.dataset.etat`) ; états occupés → `aria-busy` et titre `agent.voix.occupe`.

### Tâche 15 : A6, preuve à l'écran

- [ ] **Étape 1 :** lancer le backend de preuve de la tâche 16 (ou `preuve_a5.py` complété d'un faux Voicebox qui
  répond 200 à `GET /health`) ; `preview_start` sur 8815.
- [ ] **Étape 2 :** F1 ; vérifier le bouton micro (title « Dicter la question ») ; clic → selon le navigateur
  intégré : voie 1 (« À l'écoute… ») ou voie 2 (accès au micro) ; `aria-pressed="true"` pendant l'écoute ; Échap
  arrête la dictée **sans** fermer le tiroir ; fermer le tiroir pendant l'écoute l'arrête.
- [ ] **Étape 3 :** poser une question ; sous la réponse, bouton « Lire à voix haute (Voicebox, gratuit) ». Avec le
  faux Voicebox, la lecture réelle échoue proprement (message `agent.voix.erreur`, aucune erreur console) : c'est
  attendu, aucun moteur TTS réel n'est lancé. Si l'utilisateur a Voicebox, la lecture réelle peut être faite sur son
  accord.
- [ ] **Étape 4 :** captures FR et EN ; arrêter le backend (`preview_stop`). Rien à commiter.

---

# Lot A7 — le chapitre du guide « Demander à Deepotus »

> Ce lot suit le skill **guide-deepotus** (l'invoquer avant de commencer : il porte la grammaire d'un chapitre, la
> capture des scènes et les vérifications). Les étapes ci-dessous en sont l'application à ce chapitre.

### Tâche 16 : A7, le backend de preuve `scripts/guide/serve_guide_agent.py`

**Fichiers :** `scripts/guide/serve_guide_agent.py` (créé)

- [ ] **Étape 1 : écrire le script**

```python
# Backend de PREUVE du guide pour « Demander à Deepotus » (lot A7, 19/10/2026) : code de ce dépôt, python embarqué,
# dossier de données jetable, port 8815 (jamais le 8765), AUCUNE dépense :
#   - faux Ollama sur 127.0.0.1:8816 : `llava-demo` (capacités completion + vision). Sans image, il répond selon la
#     question (clé → Réglages › Clés d'API ; montage → l'écran Montage ; sinon [VOIR]) ; avec une image, il rend
#     [POINT:x,y:Rail] au milieu du rail de gauche ;
#   - faux Voicebox sur 127.0.0.1:8817 : GET /health seulement (le bouton « Lire » apparaît ; aucune voix n'est
#     produite : la lecture réelle échoue proprement, ce que les scènes ne montrent pas).
# Les réponses sont ÉCRITES PAR DEEPOTUS pour la démonstration et n'emploient que des ancres et chapitres réels.
import json
import os
import pathlib
import re
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, OLLAMA, VOICEBOX = 8815, 8816, 8817
WT = pathlib.Path(__file__).resolve().parents[2] / "backend"
d = pathlib.Path(tempfile.mkdtemp(prefix="dzguide_agent_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(d)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(d / 't.db').as_posix()}"
os.environ["VOICEBOX_URL"] = f"http://127.0.0.1:{VOICEBOX}"
for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "OPENAI_API_KEY", "GEMINI_API_KEY", "OLLAMA_MODEL", "FAL_KEY",
          "ELEVENLABS_API_KEY", "HEYGEN_API_KEY", "SUMMARIZER_PROVIDER", "PLANNER_PROVIDER"):
    os.environ.pop(k, None)
(d / ".env").write_text("# guide A7\n", encoding="utf-8")
sys.path.insert(0, str(WT))
os.chdir(WT)
print("donnees de preuve :", d, flush=True)

REPONSES = [
    (re.compile(r"cl[ée]|key", re.I),
     {"fr": "Ta clé se pose dans Réglages, section Clés d'API.\n1. Ouvre Réglages, puis Clés d'API.\n"
            "2. Colle la clé sur la ligne du fournisseur, puis Enregistrer.\n[POINT:reglages.cles]\n[GUIDE:cles]",
      "en": "Your key goes in Settings, API keys section.\n1. Open Settings, then API keys.\n"
            "2. Paste the key on the provider's line, then Save.\n[POINT:reglages.cles]\n[GUIDE:cles]"}),
    (re.compile(r"mont|edit", re.I),
     {"fr": "Le montage se fait dans l'écran Montage, dans la barre de gauche.\n[POINT:rail.montage]\n[GUIDE:montage]",
      "en": "Editing happens in the Edit screen, in the left bar.\n[POINT:rail.montage]\n[GUIDE:montage]"}),
]
VOIR = {"fr": "Je ne connais pas ce bouton par son nom : je peux regarder ton écran pour le trouver.\n[VOIR]\n[GUIDE:tour]",
        "en": "I don't know this button by name: I can look at your screen to find it.\n[VOIR]\n[GUIDE:tour]"}


class FauxOllama(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _r(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        self._r({"models": [{"name": "llava-demo"}]})

    def do_POST(self):
        corps = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/show":
            return self._r({"capabilities": ["completion", "vision"]})
        prompt = corps.get("prompt", "")
        en = "langue : English" in corps.get("system", "")
        question = prompt.rsplit("Nouvelle question : ", 1)[-1].split("\n\n", 1)[0]
        if corps.get("images"):
            m = re.search(r"\((\d+)×(\d+) px\)", prompt)
            l, h = (int(m.group(1)), int(m.group(2))) if m else (1280, 800)
            texte = ("It's here, in the left bar." if en else "C'est ici, dans la barre de gauche.") \
                + f"\n[POINT:{max(1, l // 40)},{h // 3}:Rail]"
        else:
            texte = next((r["en" if en else "fr"] for motif, r in REPONSES if motif.search(question)),
                         VOIR["en" if en else "fr"])
        self._r({"response": texte, "done": True})


class FauxVoicebox(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        code = 200 if self.path == "/health" else 404
        self.send_response(code); self.send_header("Content-Length", "2"); self.end_headers(); self.wfile.write(b"{}")


for port, cls in ((OLLAMA, FauxOllama), (VOICEBOX, FauxVoicebox)):
    s = ThreadingHTTPServer(("127.0.0.1", port), cls)
    threading.Thread(target=s.serve_forever, daemon=True).start()

from app.main import app  # noqa: E402
from app.config import settings  # noqa: E402
from app.services import cles_a_chaud as CAC  # noqa: E402

settings.OLLAMA_URL = f"http://127.0.0.1:{OLLAMA}"
settings.VOICEBOX_URL = f"http://127.0.0.1:{VOICEBOX}"
CAC.appliquer({"OLLAMA_MODEL": "llava-demo"})
import uvicorn  # noqa: E402

uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
```

- [ ] **Étape 2 : l'essayer**

Lancer en arrière-plan : `& $PY scripts/guide/serve_guide_agent.py`. Puis :
`curl -s http://127.0.0.1:8815/api/agent/etat` → `moteur: "ollama"`, `vision: true`, `voix.fournisseur: "voicebox"`.
`curl -s -X POST http://127.0.0.1:8815/api/agent/demander -H "Content-Type: application/json" -d "{\"question\":\"où mettre ma clé ?\"}"`
→ action `point` `reglages.cles`. Avec « où est le bouton bidule ? » → action `voir`.

- [ ] **Étape 3 : commiter**

```bash
git add scripts/guide/serve_guide_agent.py
git commit --only scripts/guide/serve_guide_agent.py -m "guide : backend de preuve de l'assistant, faux Ollama qui voit et faux Voicebox (A7)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 17 : A7, le chapitre `demander` en français

**Fichiers :** `docs/guide/src/chapitres.json`, `docs/guide/src/jeveux.json`, `docs/guide/src/fr/demander.html` (créé),
`backend/tests/test_agent_guide.py` (créé)

- [ ] **Étape 1 : écrire le banc qui échoue**

Créer `backend/tests/test_agent_guide.py` :

```python
# -*- coding: utf-8 -*-
"""A7 (spec 2026-10-19-agent-aide-design.md, lot A7) — le chapitre « Demander à Deepotus » du guide : déclaré dans
chapitres.json (famille Démarrer, juste après « tour »), écrit en FR puis EN au même squelette, ses scènes capturées
FR et EN (plan a7), le guide construit à jour, et l'assistant qui le connaît.
Run : & $PY tests/test_agent_guide.py   (depuis backend/)"""
import json, pathlib, re, subprocess, sys
import pytest

RACINE = pathlib.Path(__file__).resolve().parents[2]
SRC = RACINE / "docs" / "guide" / "src"
CHAP = json.loads((SRC / "chapitres.json").read_text(encoding="utf-8"))["chapitres"]
SCENES = ["demander/tiroir", "demander/montrer", "demander/regarder", "demander/voix"]


def test_chapitre_declare():
    ids = [c["id"] for c in CHAP]
    c = next(c for c in CHAP if c["id"] == "demander")
    assert ids.index("demander") == ids.index("tour") + 1 and c["famille"] == "demarrer"
    assert c["fr"] == "Demander à Deepotus" and c["en"] == "Ask Deepotus" and c["lot"] == "A7"
    jv = json.loads((SRC / "jeveux.json").read_text(encoding="utf-8"))["entrees"]
    assert any(e["cible"] == "demander" for e in jv)


def _squelette(lang):
    h = (SRC / lang / "demander.html").read_text(encoding="utf-8")
    return h, re.findall(r'<h3>|<ol class="etapes">|data-scene="([^"]+)"|<aside class="(\w+)"', h)


def test_fr_et_en_meme_squelette():
    fr, sq_fr = _squelette("fr")
    en, sq_en = _squelette("en")
    assert sq_fr == sq_en and sq_fr
    for s in SCENES:
        assert f'data-scene="{s}"' in fr, s
    assert "F1" in fr and "<kbd>F1</kbd>" in en
    assert "plafond « aide »" in fr and "\"help\" cap" in en
    assert "Regarder l'écran" in fr and "Look at the screen" in en


def test_scenes_capturees():
    for s in SCENES:
        d = SRC / "scenes" / s
        assert (d / "scene.json").is_file(), s
        for lang in ("fr", "en"):
            assert list(d.glob(f"*.{lang}.webp")), (s, lang)


def test_guide_construit_a_jour():
    r = subprocess.run([sys.executable, str(RACINE / "scripts" / "guide" / "construire_guide.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", cwd=str(RACINE))
    assert r.returncode == 0, r.stdout[-1500:] + r.stderr[-800:]
    assert 'id="demander"' in (RACINE / "docs" / "guide" / "fr.html").read_text(encoding="utf-8")


def test_l_assistant_connait_le_chapitre():
    t = (RACINE / "docs" / "agent" / "AGENT.md").read_text(encoding="utf-8")
    assert "[GUIDE:demander]" in t


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
```

- [ ] **Étape 2 : lancer et voir échouer**

Lancer : `& $PY -m pytest tests/test_agent_guide.py -q` → `StopIteration` (chapitre absent), fichiers absents.

- [ ] **Étape 3 : déclarer le chapitre**

Dans `docs/guide/src/chapitres.json`, insérer juste après l'objet du chapitre `tour` (mêmes clés que lui ; l'icône
`dz-action-aide` existe dans `frontend/shared/icons/dz-icons.js`) :

```json
  {"id": "demander", "famille": "demarrer", "lot": "A7", "icone": "dz-action-aide",
   "fr": "Demander à Deepotus", "en": "Ask Deepotus", "anciens": [],
   "ecrans": ["Application (tiroir « Demander », F1)"], "etat": "v3"}
```

Dans `docs/guide/src/jeveux.json`, ajouter (après l'entrée « comprendre une icône ») :

```json
  {"fr": "demander à l'application comment faire", "en": "ask the app how to do something", "cible": "demander"},
```

- [ ] **Étape 4 : relever puis écrire le français**

Relever sur le backend de preuve (tâche 16, 8815, navigateur intégré) ce que l'utilisateur voit vraiment : le bouton
« ? Demander », F1, la liste des moteurs et leur coût, les boutons sous une réponse, l'accord de la vision, le micro,
« Lire à voix haute ». Écrire alors `docs/guide/src/fr/demander.html` selon la grammaire du skill (en-tête, avant de
commencer, geste principal en 3 à 7 étapes, aller plus loin, bon à savoir ≤ 3 encadrés, raccourcis) :

```html
<p class="chapeau-chap">Vous saurez poser une question sur l'application sans la quitter : Deepotus répond en quelques étapes, vous emmène au bon écran et montre le bouton à cliquer. Deux minutes ; il faut un moteur de texte branché (une clé, ou Ollama sur ce PC).</p>

<h3>Avant de commencer</h3>
<p>L'assistant se sert d'un moteur de texte que vous avez déjà : Anthropic, OpenAI, Gemini, ou un serveur local comme Ollama. Sans moteur, il vous montre où poser une clé. Il <strong>n'exécute jamais</strong> d'action payante à votre place : il explique et montre, vous cliquez.</p>

<h3>Poser une question</h3>
<figure class="scene" data-scene="demander/tiroir"></figure>
<ol class="etapes">
<li>Appuyez sur <kbd>F1</kbd>, ou cliquez <b class="ui">? Demander</b> en bas à droite : le tiroir s'ouvre.</li>
<li>Choisissez le <b class="ui">Moteur</b> en haut du tiroir, ou laissez <b class="ui">Automatique</b>. Chaque moteur dit s'il est gratuit ou payant.</li>
<li>Tapez votre question, par exemple « où je mets ma clé ? », puis <kbd>Entrée</kbd>.</li>
<li>La réponse tient en quelques étapes. Dessous, des boutons : <b class="ui">Montre-moi</b>, <b class="ui">Y aller</b>, <b class="ui">Guide</b>.</li>
</ol>

<h3>Se faire montrer le bouton</h3>
<figure class="scene" data-scene="demander/montrer"></figure>
<ol class="etapes">
<li>Cliquez <b class="ui">Montre-moi</b> : si le bouton est sur un autre écran, l'application y va d'abord.</li>
<li>Un curseur lumineux glisse jusqu'au bouton et l'entoure, avec son nom dans une bulle. Il disparaît au premier clic.</li>
<li>Cliquez <b class="ui">Guide</b> pour ouvrir le chapitre qui en parle, dans un nouvel onglet.</li>
</ol>

<h3>Quand l'assistant ne connaît pas le bouton</h3>
<figure class="scene" data-scene="demander/regarder"></figure>
<ol class="etapes">
<li>La réponse propose <b class="ui">Regarder l'écran</b>. Cliquez-le seulement si vous êtes d'accord.</li>
<li>Le tiroir dit quel moteur verra la capture et combien elle coûte. Seuls les moteurs qui lisent les images sont proposés.</li>
<li>Cliquez <b class="ui">Capturer et envoyer</b> : votre navigateur demande de partager l'onglet ; choisissez <strong>cet onglet</strong>.</li>
<li>L'assistant répond et le curseur montre l'endroit trouvé.</li>
</ol>

<h3>Dicter et écouter</h3>
<figure class="scene" data-scene="demander/voix"></figure>
<ol class="etapes">
<li>Cliquez le micro à côté de <b class="ui">Envoyer</b> et parlez ; cliquez-le encore, ou <kbd>Échap</kbd>, pour arrêter. Le texte arrive dans la saisie : relisez avant d'envoyer.</li>
<li>Sous une réponse, le bouton haut-parleur la lit avec la voix choisie dans les Réglages.</li>
</ol>

<aside class="cout"><i data-dz="dz-etat-plafond"></i><p>Une question coûte quelques fractions de centime avec un moteur payant, comptées dans le plafond « aide » de <span class="chemin"><b class="ui">Réglages</b> › <b class="ui">Tarifs et budget</b></span>. Avec Ollama sur ce PC, c'est gratuit. Regarder l'écran coûte un peu plus : le prix s'affiche avant.</p></aside>
<aside class="astuce"><i data-dz="dz-etat-information"></i><p>La dictée par le navigateur est gratuite. Quand elle passe par le serveur, l'application affiche la durée et le coût avant d'envoyer quoi que ce soit.</p></aside>
<aside class="attention"><i data-dz="dz-etat-avertissement"></i><p>La capture d'écran part vers le moteur choisi. Fermez d'abord ce que vous ne voulez pas montrer.</p></aside>

<h3>Raccourcis</h3>
<div class="tableau"><table>
<tr><th>Touche</th><th>Effet</th></tr>
<tr><td><kbd>F1</kbd></td><td>Ouvrir ou fermer le tiroir</td></tr>
<tr><td><kbd>Entrée</kbd></td><td>Envoyer la question</td></tr>
<tr><td><kbd>Maj</kbd> + <kbd>Entrée</kbd></td><td>Aller à la ligne</td></tr>
<tr><td><kbd>Échap</kbd></td><td>Effacer le pointeur, arrêter la dictée, fermer le tiroir</td></tr>
</table></div>
```

Les encadrés sont des `<aside class="cout|astuce|attention">` précédés de leur icône `<i data-dz="…">`, les tableaux
des `<div class="tableau"><table>` (relevé dans `fr/cles.html` et `fr/budget.html` ; `attention` porte
`dz-etat-avertissement` ailleurs dans le guide). Avant d'écrire, ouvrir `fr/raccourcis.html` pour la forme des lignes
de touches et la suivre si elle diffère.

- [ ] **Étape 5 : commiter le français**

```bash
git add docs/guide/src/fr/demander.html backend/tests/test_agent_guide.py
git commit --only docs/guide/src/chapitres.json docs/guide/src/jeveux.json docs/guide/src/fr/demander.html backend/tests/test_agent_guide.py -m "guide : chapitre « Demander à Deepotus » en français (A7)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 18 : A7, les scènes animées (FR puis EN)

**Fichiers :** `docs/guide/src/scenes/plans/a7.json` (créé), `docs/guide/src/scenes/demander/*` (produits)

- [ ] **Étape 1 : écrire le plan de capture**

Créer `docs/guide/src/scenes/plans/a7.json` sur le modèle de `t237.json` (lire ce fichier d'abord, et l'en-tête de
`scripts/guide/capturer.js` pour les étapes permises). Quatre scènes, base `http://127.0.0.1:8815`, taille
`[1440, 900]` :

```json
{
 "base": "http://127.0.0.1:8815",
 "preparation": "python scripts/guide/serve_guide_agent.py (port 8815, faux Ollama 8816 qui voit, faux Voicebox 8817, aucune dépense). A7 : chapitre « Demander à Deepotus ». Réponses écrites par Deepotus, ancres et chapitres réels.",
 "scenes": [
  {"scene": "demander/tiroir", "taille": [1440, 900],
   "titre": {"fr": "F1 → question → réponse en étapes", "en": "F1 → question → step-by-step answer"},
   "legende": {"fr": "Le tiroir s'ouvre avec F1 ; la réponse tient en quelques étapes, avec ses boutons.", "en": "The drawer opens with F1; the answer fits in a few steps, with its buttons."},
   "avant": [{"aller": "/"}, {"attente": 2500}],
   "captures": [
    {"nom": "ouvert", "etapes": [{"touche": "F1"}, {"attente": 600}]},
    {"nom": "question", "etapes": [{"saisir": ["css:#dzAgentTiroir textarea", {"fr": "Où je mets ma clé ?", "en": "Where do I put my key?"}]}]},
    {"nom": "reponse", "etapes": [{"touche": "Enter"}, {"attente": 2500}]}
   ],
   "temps": [
    {"capture": 0, "duree": 2.2, "surligne": "css:#dzAgentTiroir", "bulle": {"fr": "F1 ouvre le tiroir", "en": "F1 opens the drawer"}, "ancre": "css:#dzAgentTiroir h2"},
    {"capture": 1, "duree": 2.0, "curseur": "css:#dzAgentTiroir textarea", "surligne": "css:#dzAgentTiroir textarea"},
    {"capture": 2, "duree": 3.0, "surligne": "css:#dzAgentTiroir .dzAgentActions", "bulle": {"fr": "Montre-moi, Y aller, Guide", "en": "Show me, Go there, Guide"}, "ancre": "css:#dzAgentTiroir .dzAgentActions"}
   ]},
  {"scene": "demander/montrer", "taille": [1440, 900],
   "titre": {"fr": "Montre-moi → le curseur va au bouton", "en": "Show me → the cursor goes to the button"},
   "legende": {"fr": "L'application ouvre le bon écran, puis un curseur lumineux entoure le bouton.", "en": "The app opens the right screen, then a glowing cursor circles the button."},
   "avant": [{"aller": "/"}, {"attente": 2500}, {"touche": "F1"}, {"attente": 500},
             {"saisir": ["css:#dzAgentTiroir textarea", {"fr": "Comment monter ma vidéo ?", "en": "How do I edit my video?"}]},
             {"touche": "Enter"}, {"attente": 2500}],
   "captures": [
    {"nom": "bouton", "etapes": []},
    {"nom": "halo", "etapes": [{"clic": "css:#dzAgentTiroir .dzAgentActions button"}, {"attente": 1600}]}
   ],
   "temps": [
    {"capture": 0, "duree": 2.0, "curseur": "css:#dzAgentTiroir .dzAgentActions button", "clic": true},
    {"capture": 1, "duree": 3.0, "surligne": "css:.dzAgentHalo"}
   ]},
  {"scene": "demander/regarder", "taille": [1440, 900],
   "titre": {"fr": "Regarder l'écran → accord → pointage", "en": "Look at the screen → consent → pointing"},
   "legende": {"fr": "Le coût s'affiche avant toute capture ; le partage de l'onglet est demandé par le navigateur (non filmé).", "en": "The cost shows before any capture; the browser asks to share the tab (not filmed)."},
   "avant": [{"aller": "/"}, {"attente": 2500}, {"touche": "F1"}, {"attente": 500},
             {"saisir": ["css:#dzAgentTiroir textarea", {"fr": "Où est le bouton bidule ?", "en": "Where is the gizmo button?"}]},
             {"touche": "Enter"}, {"attente": 2500}],
   "captures": [
    {"nom": "voir", "etapes": []},
    {"nom": "accord", "etapes": [{"clic": {"fr": "texte:Regarder l'écran", "en": "texte:Look at the screen"}}, {"attente": 1500}]},
    {"nom": "pointe", "etapes": [{"clic": {"fr": "texte:Annuler", "en": "texte:Cancel"}},
      {"js": "const r=document.querySelector('button.dzNavItem').getBoundingClientRect();window.__dzAgentExecuter({type:'point_xy',x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2),largeur:innerWidth,hauteur:innerHeight,libelle:'Quick',vue:{l:innerWidth,h:innerHeight}})"},
      {"attente": 1600}]}
   ],
   "temps": [
    {"capture": 0, "duree": 2.2, "surligne": {"fr": "texte:Regarder l'écran", "en": "texte:Look at the screen"}},
    {"capture": 1, "duree": 3.2, "surligne": "css:.dzAgentAccord", "bulle": {"fr": "Coût affiché avant", "en": "Cost shown first"}, "ancre": "css:.dzAgentAccord"},
    {"capture": 2, "duree": 2.6, "surligne": "css:.dzAgentHalo"}
   ]},
  {"scene": "demander/voix", "taille": [1440, 900],
   "titre": {"fr": "Dicter, puis écouter la réponse", "en": "Dictate, then listen to the answer"},
   "legende": {"fr": "Le micro remplit la saisie ; le haut-parleur lit la réponse avec la voix des Réglages.", "en": "The mic fills the input; the speaker reads the answer with the voice from Settings."},
   "avant": [{"aller": "/"}, {"attente": 2500}, {"touche": "F1"}, {"attente": 600},
             {"saisir": ["css:#dzAgentTiroir textarea", {"fr": "Où je mets ma clé ?", "en": "Where do I put my key?"}]},
             {"touche": "Enter"}, {"attente": 2500}],
   "captures": [{"nom": "voix", "etapes": []}],
   "temps": [
    {"capture": 0, "duree": 2.2, "curseur": "css:.dzAgentPied button[aria-pressed]", "surligne": "css:.dzAgentPied button[aria-pressed]", "bulle": {"fr": "Dicter", "en": "Dictate"}, "ancre": "css:.dzAgentPied button[aria-pressed]"},
    {"capture": 0, "duree": 2.4, "curseur": "css:.dzAgentActions button[aria-pressed]", "surligne": "css:.dzAgentActions button[aria-pressed]", "bulle": {"fr": "Lire à voix haute", "en": "Read aloud"}, "ancre": "css:.dzAgentActions button[aria-pressed]"}
   ]}
 ]
}
```

Ajuster les repères à ce que la page montre vraiment (le skill impose des repères par libellé ou sélecteur, jamais par
coordonnées saisies). Si `capturer.js` ne connaît pas une étape (`touche` sur `F1`, `js`), relire son en-tête : il les
liste (`{"touche": …}`, `{"js": …}`).

- [ ] **Étape 2 : capturer**

Backend de preuve lancé (tâche 16), puis (le `NODE_PATH` vient du dépôt principal, comme pour t237) :

```bash
NODE_PATH=C:/Users/olivi/DeepotusVideo/scripts/qa/node_modules node scripts/guide/capturer.js docs/guide/src/scenes/plans/a7.json
```

Attendu : `docs/guide/src/scenes/demander/{tiroir,montrer,regarder,voix}/scene.json` et `*.fr.webp`, `*.en.webp`.
Regarder chaque WebP (outil Read sur l'image) : le tiroir, la réponse, l'accord avec « gratuitement », le halo.

- [ ] **Étape 3 : commiter les scènes**

```bash
git add docs/guide/src/scenes/plans/a7.json docs/guide/src/scenes/demander
git commit -m "guide : scènes animées du chapitre « Demander à Deepotus », FR et EN (A7)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Tâche 19 : A7, l'anglais, la construction et le PDF

**Fichiers :** `docs/guide/src/en/demander.html` (créé), `docs/guide/fr.html`, `docs/guide/en.html`,
`docs/guide/Deepotus-Guide-FR.pdf`, `docs/guide/Deepotus-Guide-EN.pdf`, `docs/agent/AGENT.md`

- [ ] **Étape 1 : traduire**

Créer `docs/guide/src/en/demander.html` : **même structure**, mêmes `data-scene`, mêmes encadrés, dans l'ordre. Les
libellés d'interface sont ceux de `agent.json` en anglais (« ? Ask », « Engine », « Automatic », « Show me »,
« Go there », « Guide », « Look at the screen », « Capture and send », « Dictate the question », « Read aloud »),
« Settings › Pricing and budget » comme dans `en/budget.html`, et le plafond se dit `the "help" cap`.

- [ ] **Étape 2 : l'assistant connaît son chapitre**

Dans `docs/agent/AGENT.md`, ajouter au parcours le plus proche (ou créer le parcours « Se faire aider ») une ligne qui
se termine par la balise seule sur sa ligne :

```markdown
### Se faire aider
1. F1 ouvre le tiroir « Demander » ; la réponse propose de montrer le bouton, d'ouvrir l'écran ou le guide.
2. Si l'assistant ne connaît pas un bouton, il propose de regarder l'écran (accord et coût d'abord).
    [GUIDE:demander]
```

(respecter le format des parcours existants : relire la section « Parcours » et la règle « aucune balise dans une
phrase »).

- [ ] **Étape 3 : construire et vérifier**

Depuis la racine :

```bash
& $PY scripts/guide/construire_guide.py
& $PY scripts/guide/construire_guide.py --check
& $PY scripts/guide/construire_guide.py --pdf
& $PY scripts/guide/relever_manques.py --check
```

Puis : `& $PY -m pytest tests/test_agent_guide.py tests/test_agent_connaissance.py -q` (depuis `backend/`),
`& $PY tests/test_guide_v3.py`, `& $PY tests/test_guide_liens_app.py` → aucun FAIL (comparer à `origin/main` pour un
FAIL préexistant).

- [ ] **Étape 4 : preuve à l'écran**

Ouvrir `docs/guide/fr.html#demander` puis `en.html#demander` dans le navigateur intégré : les quatre scènes s'animent,
la recherche trouve « Demander », le mode sombre reste lisible. Captures.

- [ ] **Étape 5 : commiter**

```bash
git add docs/guide/src/en/demander.html
git commit --only docs/guide/src/en/demander.html docs/agent/AGENT.md docs/guide/fr.html docs/guide/en.html docs/guide/Deepotus-Guide-FR.pdf docs/guide/Deepotus-Guide-EN.pdf -m "guide : « Ask Deepotus » en anglais, guide et PDF reconstruits (A7)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

(Ajouter à `--only` tout autre fichier construit que `git status --short` montre modifié, par exemple
`docs/guide/MANQUES.md`.)

---

### Tâche 20 : fin du chantier — spec, suite complète, PR

**Fichiers :** `docs/superpowers/specs/2026-10-19-agent-aide-design.md`

- [ ] **Étape 1 : mettre la spec à jour**

Dans la spec : l'en-tête dit « A0-A7 livrés » ; la section « Vision en secours » décrit ce qui est livré
(`[VOIR]`, accord avec devis `/api/agent/estimer`, capture `getDisplayMedia` de l'onglet courant, `max_usd` et 409,
`[POINT:x,y:libellé]` seulement après capture, `moteurs_texte.vision`) ; la section 3 cite `dz-agent-vision.js`, le
micro (`DzChampIA.dictee.basculer`) et « Lire » (`/api/agent/lire`, cache `agent_lectures`) ; le tableau des
erreurs ajoute « partage refusé » et « pas cet onglet » ; § 5 cite `test_moteurs_texte_images.py`,
`test_agent_vision.py`, `test_agent_voix.py`, `test_agent_guide.py` ; § 6 marque A5, A6, A7 « (livré) ».

- [ ] **Étape 2 : suite complète, comparée à `origin/main`**

Lancer `.\scripts\run-tests.ps1` dans ce worktree **et** dans un worktree propre d'`origin/main` ; comparer les listes
de FAIL : aucun FAIL nouveau. Bancs node : `node frontend/shared/qa/agent_logique.test.mjs`.

- [ ] **Étape 3 : commiter la spec**

```bash
git commit --only docs/superpowers/specs/2026-10-19-agent-aide-design.md -m "spec agent-aide : décrit la livraison A5-A7

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Étape 4 : PR (sur accord de l'utilisateur)**

Pousser la branche et ouvrir la PR seulement quand l'utilisateur le demande. Corps : ce que font A5, A6, A7, la
décision `getDisplayMedia`, les bancs, la preuve (captures FR/EN), et la ligne
`🤖 Generated with [Claude Code](https://claude.com/claude-code)`. L'installation vers `%LOCALAPPDATA%` (Python
applicatif touché → relance du backend) se vérifie par `git hash-object`, jamais sha256.
