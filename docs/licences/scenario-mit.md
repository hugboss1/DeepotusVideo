# Méthodes inspirées de Scenario — droits et mentions (t443, 08/11/2026)

L'écran « Méthodes » et les neuf agents métier (t433-t442) reprennent des **méthodes** décrites publiquement par
Scenario (https://www.scenario.com/explorations, relevé du 08/11/2026). Ce fichier dit ce qui est repris et à quelles
conditions.

## Ce qui est repris

- **Des idées de méthode** : étapes, contrôles, seuils, pièges. Ce ne sont ni des textes ni du code. Les 94 fiches
  (`docs/superpowers/specs/assets/2026-11-08-scenario-explorations/fiches.json` et `fiches_en.json`, puis
  `backend/app/knowledge/methodes.json`) sont **rédigées par Deepotus**, en français et en anglais. Chaque fiche porte un
  lien « source » vers l'exploration d'origine.
- **Aucun texte, aucune illustration, aucune vidéo et aucun PDF du site** ne sont copiés dans le dépôt ni dans
  l'application. Ces contenus ne sont sous aucune licence ouverte. Le banc `test_methodes` 1.9 vérifie l'absence de
  plusieurs accroches du site.
- **Aucun code des skills de Scenario** n'est repris à ce jour : les outils des agents (`services/briques.py`,
  `musique_temps.py`, `monteur.py`, `chaine_video.py`, `acteurs.py`, `formats_pub.py`, `sprites_qc.py`,
  `web3d_qc.py`, `arbitre.py`, `mise_en_texte.py`) sont écrits pour l'application.

## Skills publiés sous licence MIT

45 des 93 skills relevés déclarent la licence MIT (en-tête `license: MIT`, ou publication dans
https://github.com/scenario-labs/skills). Le champ `licence_skill` de leur fiche vaut « MIT », et l'écran le dit
(« Le skill d'origine est publié sous licence MIT »).

a-cast-of-one, alter, apex-livery-studio, auto-edit, babel-tavern, blender-2d-animation, block-or-build,
celestial-orrery, continuity-heist, crimson-tower, dotties-voice, fan-cam, full-circle, game-ua-ads, graveyard-waves,
impossible-fitting-room, impossible-rides, kinetic-film, kumo-ramen, lamplighter, last-repair-shop, little-lights,
little-paper-voyage, material-worlds, mech-bay, mirage-house, mirror-keeper, motion-loops, one-more-take,
one-take-many-angles, open-house, paper-city, park-atlas, playable-ads, saint-seiya, scroll-courier,
side-pocket-defaistre, sleeping-giant, tap-to-install, the-corridor, the-drifting-afternoon, the-last-lantern,
two-rulers, video-color-grade, wish-you-were-here.

Les 48 autres skills ne déclarent aucune licence : on n'en reprend que la méthode, jamais le code ni le texte.

## Règle pour la suite

Si le code ou le texte d'un skill MIT est un jour adapté dans l'application, le fichier qui le reprend porte en tête :

```
Adapté de <nom du skill> — © Scenario, licence MIT (https://github.com/scenario-labs/skills)
```

Le texte de la licence MIT (copyright de Scenario) est alors ajouté ici et dans les mentions « À propos »
de l'application.
