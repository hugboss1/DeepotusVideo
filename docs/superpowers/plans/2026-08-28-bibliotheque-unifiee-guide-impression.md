# Bibliothèque unifiée (vignettes partout + import Figma) & guide impression

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, session du 28/08). Steps use checkbox (`- [ ]`) syntax.

> Ordre utilisateur du 28/08 : (a) le chapitre du guide « Imprimer ses
> créations » (le reste connu d'hier, confirmé voulu) ; (b) « unifier la
> recherche et l'importation depuis la librairie » — un menu à MINIATURES
> des illustrations de la Bibliothèque + « importer un fichier depuis
> figma par exemple » ; (c) cette sélection à vignettes disponible depuis
> TOUTES les fonctionnalités de façon cohérente — l'exemple nommé : le
> nœud image du Studio, dont « le dropdown me donne la liste des noms, ce
> n'est pas pratique — je veux une vue directement sur le contenu réel de
> la librairie ». Expansion COMMITTÉE avant le code (patron établi).

**Goal :** un sélecteur de Bibliothèque UNIQUE — recherche + grille de
vignettes réelles + import (fichier local ET lien Figma) — injecté dans le
bundle comme `__dzLibPicker` et branché partout où l'app faisait choisir
une image PAR SON NOM ; plus le chapitre 20 du guide FR/EN (+ PDF
régénérés) sur l'impression 3D.

**Architecture :** le sélecteur est un overlay DOM autonome (patron
`__dzCatBar`/`__dzPrint3d` : préambule injecté + feuille propre, zéro
interop React) posé par un patcher NEUF en queue de chaîne ; l'import
Figma est un service backend pur à hooks monkeypatchables (patron
`_lancer_startfile`) sur l'API REST Figma (token personnel dans le .env) ;
le guide suit sa forme existante (sections `h2#cN` + TOC + Edge headless
pour les PDF).

---

## État des lieux MESURÉ (28/08) — où l'app fait choisir une image

| Écran | Aujourd'hui | Verdict |
|---|---|---|
| **Studio, nœud Image** (`Bh`) | `re` dropdown de NOMS + champ Filename + un aperçu | LA plainte — bouton « Parcourir » à greffer |
| **Quick — Start image / End image** (Seedance) | deux `re` dropdowns de NOMS | à greffer aussi (même geste) |
| Game Assets 3D — Source image | **déjà une grille de vignettes** | rien à faire (le précédent visuel du bundle) |
| Montage — Images (Bibliothèque) | **déjà une grille** (`svm-ovgrid`) | rien à faire |
| Library | est la bibliothèque | rien à faire |
| Cardforge / Vectorlab / Atelier | galeries visuelles propres (phases livrées) | rien à faire |
| Scheduler (`Bm.sourceImage`) | produit par les flux de génération, pas un choix par nom | rien à faire |

## Décisions (tranchées avant le code)

**G1 — Le sélecteur : `__dzLibPicker(opts, cb)`, un overlay DOM unique.**
Injecté par `scripts/patch_bundle_libpicker.py` (queue de chaîne après
print3d, marqueur `__dzLibPicker`, squelette vectorlab/print3d complet).
Contenu : en-tête (titre + recherche instantanée par sous-chaîne
insensible à la casse + ✕), grille de VIGNETTES réelles (`<img
loading="lazy">` sur `/api/images/<nom>`, nom en légende, clic =
`cb(nom)` + fermeture), pied : « ⬆ Importer un fichier… » (input file →
`POST /images/upload` existant → cb), « ◇ Depuis Figma… » (prompt du lien
→ `POST /api/images/import-figma` → cb, erreurs alertées TELLES QUELLES),
Annuler/Échap/clic-dehors = rien. Tri « récentes d'abord » par la
`mtime` que l'endpoint gagne (G3). Feuille injectée une fois
(`__dzLibPickerStyle`, tokens var(--…) — les deux thèmes gratuits).

**G2 — Les greffes : un bouton « 📚 Parcourir » À CÔTÉ des dropdowns,
jamais à leur place.** Trois ancres uniques : le nœud Image du Studio
(rangée « Bibliothèque » insérée avant le champ Filename —
`cb = t("filename", nom)`), Quick Start image (`cb = v`) et Quick End
image (`cb = k`). Les dropdowns existants restent : la greffe est
additive, l'ancre est le libellé exact du champ voisin (count==1
vérifié), le patcher refuse sinon.

**G3 — Backend : `mtime` sur ImageItem (additif) + import Figma.**
`ImageItem.mtime: float | None` rempli par `list_images` — aucun
consommateur cassé, le picker trie côté client. Import Figma :
`backend/app/services/figma_import.py` — `figma_cible(url)` PUR (clés
`figma.com/(file|design)/<KEY>`, `node-id=12-34` → `12:34`, refus
parlants : pas un lien Figma / pas de node-id « ouvre le calque et copie
son lien ») ; `importer(url, token, dossier)` appelle l'API REST
(`GET /v1/images/{key}?ids=<node>&format=png&scale=2`, en-tête
`X-Figma-Token`) puis télécharge le PNG (magic vérifié) vers
`figma_<key>_<node>.png` (réécrit en place — ré-importer rafraîchit).
Les DEUX pas réseau passent par des hooks module (`_get_json`,
`_get_bytes`) monkeypatchés au banc — le banc ne SORT jamais. Route
`POST /api/images/import-figma {url}` : token = `FIGMA_TOKEN` des
Settings/.env (patron des clés existantes) ; absent → 409 parlant
(« renseigne FIGMA_TOKEN … un Personal Access Token Figma ») ; erreurs
Figma → 502 avec le message. Banc NEUF `test_library_picker.py` (un
processus) : cible pure, route mockée bout-à-bout, 409/400/502, mtime,
et les MIROIRS du bundle (marqueur, greffes, patcher gardé).

**G4 — Guide, chapitre 20 « Imprimer ses créations » (FR/EN + PDF).**
Section `h2#c20` après c19 + entrée TOC, même grammaire que les chapitres
existants (steps numérotés, warn, code) : la Centauri Carbon 2 et
ElegooSlicer (installé = .3mf associé), les TROIS boutons « → Impression
3D » (Forge 3D : STL du gate, étanchéité garantie ; Game Assets 3D :
échelle mm au prompt, refus parlant de l'optimisé ; Vectorlab : extrusion
par calque `nom=mm`, le relief vitrail), le dossier
`DeepotusVideoGenData\assets\print3d\` (STL + 3MF + impression.json), la
garde du plateau 256 mm, le repli `SLICER_PATH`. PDFs régénérés par Edge
headless (`--print-to-pdf`, file://) — SANS captures nouvelles (une
capture réelle exigerait l'instance isolée du patron b409154 : assumé et
dit, le chapitre est textuel comme c17).

**G5 — Hors périmètre (assumé).** Un chapitre de guide Vectorlab complet
(le 20 référence l'export, pas l'éditeur) ; la dépréciation des dropdowns
de noms (ils restent en secours) ; le picker dans les surfaces sources
(elles ont leurs galeries) ; l'OAuth Figma (le token personnel suffit à
« par exemple ») ; tout coût API (Figma REST est gratuit).

## Structure de fichiers

```
docs/guide/fr.html, en.html            + TOC c20 + section c20
docs/guide/Deepotus-Guide-FR.pdf, EN   régénérés (Edge headless)
backend/app/models/schemas.py          ImageItem.mtime
backend/app/api/routes.py              list_images mtime ; POST /images/import-figma
backend/app/config.py                  FIGMA_TOKEN: str = ""
backend/app/services/figma_import.py   NEUF — pur + hooks réseau
backend/tests/test_library_picker.py   NEUF — RED d'abord
scripts/patch_bundle_libpicker.py      NEUF — queue de chaîne
frontend/dist/assets/index-BEOJX8L5.js patché (résultat committé)
```

## Tasks

- [ ] **T1 guide** : sections c20 FR/EN + TOC, PDF régénérés, déployés —
  commit
- [ ] **T2 backend RED** : test_library_picker.py (figma_cible pure —
  formats d'URL et refus ; route import-figma mockée : succès →
  figma_<key>_<node>.png écrit + {filename}, sans token → 409, URL sans
  node → 400, erreur Figma → 502 ; list_images porte mtime) → GREEN
  (schemas + config + service + routes) → voisins verts → commit
- [ ] **T3 patcher** : patch_bundle_libpicker.py (préambule picker +
  greffe Bh + greffes Quick ×2, sondes des marqueurs amont, deltas
  épinglés, --check, node --check du bundle, garde de double
  application) + miroirs au banc → commit
- [ ] **T4 déploiement & preuve réelle** : sha + stop/relance + santé ;
  preuves DOM : le picker s'ouvre DEPUIS le nœud Image du Studio,
  vignettes réelles listées, recherche filtre, clic → le nœud reçoit le
  fichier ; les boutons Quick présents ; import fichier local par le
  picker (PNG jetable → sélectionné → supprimé) ; Figma sans token →
  le 409 parlant TEL QUEL à l'écran ; nettoyage ; relevé ici ; push ;
  mémoires
