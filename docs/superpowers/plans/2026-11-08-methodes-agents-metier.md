# Plan — Méthodes et agents métier (t433-t443), 08/11/2026

Conception validée le 08/11 : `docs/superpowers/specs/2026-11-08-scenario-explorations-agents-design.md`.
Relevé : `docs/superpowers/specs/2026-11-08-scenario-explorations-releve.md`. Fiches sources (à nous, FR + EN) :
`docs/superpowers/specs/assets/2026-11-08-scenario-explorations/fiches.json` + `fiches_en.json`.

Une tâche à la fois, chacune avec TDD, des bancs, une preuve à l'écran dans les deux langues et sa PR. L'installation se fait sur accord.

| Tâche | Lot | Contenu | Dépend de |
|---|---|---|---|
| **t433** | M0 | FAITE, PR #526 fusionnée (70307bbe) : catalogue `knowledge/methodes.json` (construit par `scripts/methodes_construire.py`), service `methodes`, routes `/api/methodes`, outil d'agent `methodes_lire` (boîte « methodes », agent `mcp`), écran `/methodes/` (galerie, filtres famille/agent/écran, fiche, exemples copiables), entrée de la barre (maillon de queue `dzmethodes`), i18n `methodes.json`, bancs `test_methodes` + `test_methodes_ecran` | — |
| **t434** | M1 | FAITE (PR suivante après #526) : `services/briques.py` (B1 `mesurer` local + `avis` Claude vision payant aux critères fournis ; B3 `conformer` vers taille/cadence/durée d'une source, `comparer` dérive image par image), `services/ancres.py` (B2, copie de l'image, `references`, `verifier` par identity_drift), `services/registre_taches.py` + table `etapes_registre` (B7), routes `/api/briques/*`, boîte « briques » (5 outils de lecture, agent `mcp`), banc `test_briques` | t433 |
| t435 | M2 | agent **Monteur** + B4 chaîne vidéo→vidéo + B5 texte en code et calage sur la musique ; bouton « Méthodes » dans Montage et Quick (ouvre `/methodes/?ecran=montage`) ; « Lancer avec l'agent » sur ses fiches | t434 |
| t436 | M3 | agent **Réalisateur** (Chapitres, Plateau, Scène Blender ; s'appuie sur t331-t338) | t434 |
| t437 | M4 | agents **Retoucheur** + **Déclinaisons produit** (Studio, Photolab, Templates) | t434 |
| t438 | M5 | agent **Directeur d'acteurs** (Studio, Son & VFX, Avatar live) | t434 |
| t439 | M6 | agent **Publicitaire** (Quick, Montage, relais Campagnes) | t435 |
| t440 | M7 | agent **Artiste 2D de jeu** (Spritelab, Tilelab, Assets 2D ; s'appuie sur t340-t341) | t434 |
| t441 | M8 | agent **Artiste 3D de jeu** (Studio 3D, Établi, Matières, Forge 3D, Lib3D ; s'appuie sur t342-t344) | t434 |
| t442 | M9 | agent **Éditeur illustré** + outil B6 **Arbitre** | t434 |
| t443 | M10 | illustrations des 94 fiches (captures pour ce qui marche, images générées pour le reste, environ 2 $) + chapitre du guide « Méthodes et agents métier » + connaissance de l'assistant (catalogue, AGENT.md resserré) + `docs/licences/scenario-mit.md` | t435-t442 |

## Règles communes

- **Données** : on ne modifie jamais `knowledge/methodes.json` à la main. On corrige `fiches.json` ou `fiches_en.json`, puis on relance `python scripts/methodes_construire.py`. Le banc `test_methodes` 1.1 vérifie que le fichier est à jour.
- **Droits** : on ne copie ni texte ni média du site de Scenario. Le code d'un skill MIT (`licence_skill: "MIT"`) peut être adapté, avec la mention « © Scenario, licence MIT » dans le fichier qui le reprend.
- **Agents** : chaque agent métier est une boîte d'`agent_boites` avec son invite système bâtie depuis ses fiches. Une carte d'accord précède toute dépense (devis par message et plafonds). Campagnes reste figé à l'octet.
- **Tiroirs** : chaque écran hôte reçoit son bouton « Méthodes » avec le lot de son agent. Ce bouton ouvre la page pré-filtrée (`?ecran=<id>`), comme prévu dans `methodes.js`.
- **Chaîne du bundle** : `dzmethodes` est la queue au 08/11, posé après `dzcreer3d`. Tout maillon ajouté ensuite le sonde et appelle son inverse `avant_<neuf>` en tête de `avant_dzmethodes`.
