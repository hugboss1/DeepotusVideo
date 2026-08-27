# Option de style « Vitrail Młoda Polska » dans l'app — design

> **RELEVÉ (27/08, fin de chantier) : LIVRÉ ET DÉPLOYÉ.** Skill
> `vitrail-mloda-polska` créé et testé RED→GREEN (baseline sans skill : nom
> d'artiste dans les prompts ; avec skill : conforme). Copies épinglées +
> preset + canon + `style` sur les deux routes + miroir atelier + patch
> bundle `episodes_style` : commits 04358c5 et 0606f8d, bancs style_da,
> style_vitrail, atelier ×2, image_model_default, manuscript, voiceover ×2
> verts, déployé sha-vérifié, santé 2.5.0, chip DA et select Épisodes
> prouvés dans l'app réelle (clic chip → bloc + canon `vitrail`). Amendement
> en cours de route : le preset backend DÉRIVE de la fiche à l'import (repli
> court si copie absente) au lieu d'un littéral dupliqué — D4 tenu plus
> fort ; le mode paragraphe des Épisodes stylise aussi ses prompts
> (première phrase), pas seulement le mode IA. L'éditeur vectoriel a son
> plan séparé (2026-08-27-editeur-vectoriel-vitrail.md), non implémenté.

**Date** : 2026-08-27. **Ordre utilisateur** : « génère un skill qui va reproduire dans
l'application un style vitrail en reprenant tous les codes du mouvement Jeune Pologne
(Młoda Polska) […] à intégrer dans la création d'illustrations sous forme d'option ».
**Source de la grammaire** : `docs/superpowers/specs/2026-08-27-guide-skill-prompts-mloda-polska.md`
(commit 4e8b026). **Session autonome** : l'ordre répond aux questions de cadrage ; ce
document consigne les options pesées et les décisions tranchées, comme l'ordre le
délègue (« l'architecture est à trancher »).

Ce design couvre le livrable 2 (l'option dans l'app) et fige au passage la forme des
fichiers partagés avec le livrable 1 (le skill). Le livrable 3 (éditeur vectoriel) a
son propre document de plan, soumis à l'utilisateur avant tout code.

---

## 1. Ce qui existe (exploré)

- **Atelier DA** (`frontend/atelier/` — surface modulaire en sources, servie à
  `/atelier` en iframe) : réglages `atelier_settings` (`global_style`, `style_canon`,
  `image_provider`, `style_ref_image`), chips de presets (`STYLE_PRESETS` en double :
  backend `manuscript_agent.py` + miroir `atelier.js`), canons de proportions
  (`PROPORTION_CANONS`, injectés dans les prompts des planches : `char`/`face` sur les
  personnages, `decor` sur les lieux/décors), planches de bible générées serveur
  (`POST /bible/entities/{id}/generate` : sujet + `Style: {global_style}` + canon).
- **Épisodes** (bundle compilé) : découpage en scènes `POST /episodes/scenes`
  (méthode `ai` → `_ai_scenes` écrit les `illustration_prompt` ; thème abyssal câblé
  en dur), illustrations par scène via `POST /images/generate` (prompt envoyé
  verbatim par le bundle).
- **`/images/generate`** : `{prompt, n, size, model}` — aucun paramètre de style.
- **Patrons établis** : copie épinglée sha+date+test de fraîcheur
  (`backend/app/services/cards/style_walkuski.py|json` + déclaration `SERIE_JUGE`
  dans le consommateur, tests B de `test_cards_face.py`) ; pont-skill à lecture live
  avec repli embarqué (`shotcraft_service.py`) ; chaîne de patchs du bundle
  (`scripts/patch_bundle_*.py`, ancres uniques + sauvegarde + `node --check`).

## 2. Décisions d'architecture

### D1 — Source de vérité : le skill ; l'app en copie épinglée (patron walkuski)

Options pesées :

1. **Bibliothèque de préréglages seule** (une entrée `STYLE_PRESETS` avec une chaîne
   statique). Le moins cher — mais la grammaire du guide (8 familles, variables,
   intensités, garde-fous, négatifs) se réduit à une phrase, le skill et l'app
   dérivent l'un de l'autre sans garde, et aucun juge futur n'est possible.
2. **Pont-skill à la shotcraft** (lecture live du skill + catalogue embarqué en
   repli). Bon pour un catalogue externe volumineux qui évolue seul ; ici la
   grammaire est à nous, stable, et la prod déployée doit être autonome et
   identique au poste de dev — la lecture live ajoute un chemin de code sans gain.
3. **Copie épinglée au patron walkuski** — retenue. Le skill user-level
   (`~/.claude/skills/vitrail-mloda-polska/`) est la source ; le backend embarque des
   copies datées et vérifiées par empreinte : `backend/app/services/style_vitrail.py`
   (copie byte-identique de `scripts/vitrail_prompt.py` du skill, module pur stdlib)
   et `backend/app/services/style_vitrail.json` (copie de `fiche_style.json`).
   Déclaration `VITRAIL_COPIE` (origine, `copie_le`, sha256 normalisés LF) dans le
   consommateur `manuscript_agent.py` ; test de fraîcheur qui compare au skill sur le
   poste de dev et se SAUTE en le disant ailleurs — à l'identique des tests B de
   `test_cards_face.py`. Leçon phase 6 respectée : le moteur se refactore AU SKILL
   puis se recopie.

Contrainte de byte-identité : le module ne peut pas coder deux chemins de fiche en
dur. Le chargeur essaie, relatifs à `__file__` : `style_vitrail.json` (déploiement
backend), puis `../fiche_style.json` (arborescence du skill), puis `fiche_style.json`.

### D2 — Où vit l'option : trois surfaces, aucune couplée en silence

1. **Atelier DA** (surface principale) : nouveau preset « Vitrail Młoda Polska »
   dans `STYLE_PRESETS` (backend + miroir `atelier.js`) + nouveau canon de
   proportions `vitrail` dans `PROPORTION_CANONS` (backend + miroir). Un canon dédié
   plutôt que De Vinci : le champ `decor` du canon académique impose « correct
   linear perspective » — exactement ce que l'espace décoratif aplati du vitrail
   refuse. Le canon `vitrail` porte des proportions monumentales (figure frontale
   7–8 têtes, hiérarchie simple) et des codes décor aplatis (espace ornemental,
   bordures, pas de perspective profonde). Mots-clés de détection (`vitrail`,
   `stained glass`, `mloda`, `młoda`, `witraż`…) pour `resolve_canon`.
2. **`POST /images/generate`** : paramètre optionnel `style` (id de famille de la
   fiche, ex. `vitrail`). Résolu serveur via le moteur épinglé :
   `prompt = appliquer(prompt, style)` — bloc de style + garde-fous ajoutés, garde
   anti-noms-d'artistes passée. Toute surface ou script peut opter sans patch UI.
3. **Épisodes** : paramètre optionnel `style` sur `POST /episodes/scenes`. Décision
   d'implémentation : l'agent LLM écrit des prompts SUJET (sans vocabulaire de
   style), puis le backend applique le bloc de style de façon **déterministe**
   (`appliquer()` sur chaque `illustration_prompt`) — testable aux sentinelles sans
   LLM, pas de dépendance à la docilité du modèle. Les prompts restent éditables
   dans les cartes de scène. Petit patch du bundle (chaîne établie,
   `scripts/patch_bundle_episodes_style.py`) : un select « Style » (Aucun / Vitrail
   Młoda Polska) à l'étape storyboard, transmis dans le corps de la requête.

Rejeté : appliquer `global_style` de l'Atelier aux Épisodes automatiquement
(couplage silencieux entre deux features distinctes) ; un select de style sur
l'écran Images (patch bundle plus lourd, `/images/generate?style=` couvre l'API et
le besoin réel est côté DA/Épisodes).

### D3 — Ce que la fiche contient (bornes mesurables, provenance honnête)

`fiche_style.json` structure les 8 familles du guide (vitrail sacré moderniste,
symbolisme, portrait atmosphérique, folklore, paysage monumental, impressionnisme,
synthétisme, arts décoratifs) : codes formels, palette en hex (ancres nommées depuis
le vocabulaire du guide — cobalt, rubis, émeraude, ambre…), lumière, motifs, bornes
de composition (fractions), bloc de style compact EN prêt-générateur, négatif par
famille ; plus la formule universelle (§5 du guide), les variables, la matrice de
mélange (§6), les garde-fous (§2 et §10) et la liste des artistes dont le nom ne
sort jamais dans un prompt. **Provenance déclarée** : contrairement à walkuski
(16 œuvres mesurées), ces bornes sont DÉCLARÉES depuis le guide, pas mesurées sur
corpus — la fiche le dit dans un champ `provenance`, et les bornes sont candidates à
une re-mesure future (un juge calibré est hors périmètre ici).

### D4 — Zéro dérive entre presets et fiche

Le preset backend reste une chaîne littérale (pas de lecture de fichier à l'import) ;
un test affirme `STYLE_PRESETS[vitrail].style_prompt == bloc_style("vitrail")` dérivé
de la fiche épinglée. Même verrou pour le miroir `atelier.js` (le test lit le fichier
et vérifie la présence du bloc et du canon).

## 3. Composants

| Pièce | Fichier | Rôle |
|---|---|---|
| Moteur (copie épinglée) | `backend/app/services/style_vitrail.py` | pur stdlib : `charger_fiche()`, `familles()`, `bloc_style(id)`, `negatif(id)`, `construire_prompt(...)` (formule §5), `appliquer(prompt, id)`, `garde_noms(prompt)` ; CLI pour l'usage skill |
| Fiche (copie épinglée) | `backend/app/services/style_vitrail.json` | la grammaire machine (D3) |
| Déclaration | `manuscript_agent.py` `VITRAIL_COPIE` | origine + date + sha256 (LF normalisé) |
| Preset + canon | `manuscript_agent.py` | entrée `STYLE_PRESETS` + entrée `PROPORTION_CANONS["vitrail"]` |
| Miroirs UI Atelier | `frontend/atelier/atelier.js` | chip preset + entrée canon (label + hint) |
| Style API images | `routes.py` `/images/generate` | param `style` → `appliquer()` + garde |
| Style Épisodes | `routes.py` `/episodes/scenes` + `_ai_scenes` | param `style` → prompts sujet + application déterministe |
| Patch bundle | `scripts/patch_bundle_episodes_style.py` | select Style au storyboard Épisodes + transmission du champ |

## 4. Tests (TDD, RED d'abord ; zéro dépense API — stubs fal/OpenAI/LLM du banc)

- `backend/tests/test_style_vitrail.py` (nouveau, un processus dédié) :
  épinglage (fichiers présents, déclaration sha exacte, fraîcheur vs skill avec skip
  motivé hors poste de dev) ; moteur (8 familles, prompt construit conforme à la
  formule — sujet, famille unique dominante, palette bornée, lumière explicite,
  médium, garde-fous « sans texte ni signature », négatif) ; **poison** : aucun nom
  des artistes du guide ne sort de `construire_prompt`/`appliquer`, `garde_noms`
  lève sur un prompt empoisonné ; preset == fiche (D4) ; miroirs atelier.js.
- `backend/tests/test_style_da.py` (étendu) : invariants du canon `vitrail`
  (complet, frame, heads bornés, « heads tall » énoncé), preset valide,
  `resolve_canon("stained glass vitrail")=="vitrail"`, et un tour de génération de
  planche stubbé qui vérifie l'injection du canon vitrail.
- Épisodes + images : asserts sur les prompts capturés par les stubs
  (`style="vitrail"` → bloc appliqué, négatif présent, pas de nom d'artiste ;
  sans style → comportement inchangé).
- Harnais : `scripts/run-tests.ps1` (un processus par fichier), suites des fichiers
  touchés vertes avant déploiement.

## 5. Déploiement

Patron éprouvé : copie sha-vérifiée des fichiers touchés vers
`%LOCALAPPDATA%\DeepotusVideoGen\backend` (+ `frontend/atelier/`, + bundle patché
`frontend/dist/assets/`), `scripts/stop.ps1`, relance
`%LOCALAPPDATA%\DeepotusVideoGen\runtime\python\python.exe -m uvicorn app.main:app
--host 127.0.0.1 --port 8765` (cwd = backend déployé), santé `/api/health` = 2.5.0.
Zéro tir payant : aucune génération d'image réelle sans devis/ordre explicite.

## 6. Hors périmètre

L'éditeur vectoriel (livrable 3, plan séparé soumis avant code) ; un juge mesuré
calibré du style vitrail (les bornes sont déclarées, pas mesurées — un corpus et un
étalonnage à la walkuski seraient un chantier ultérieur) ; les 7 familles non-vitrail
dans l'UI (le moteur les sert, l'UI n'expose que l'option vitrail demandée).
