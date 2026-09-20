# Vectorlab et surfaces 2D — finitions d'interface : origine nommée, dialogues maison, panneaux équilibrés, aide didactique animée (20/09/2026)

> Demande de l'utilisateur (19/09, quatre captures) : « à planifier et
> implémenter sans halluciner et dans une session neuve ». Ce spec relève
> ce qui EST dans le code (vérifié le 20/09 sur `chantier/vectorlab-affinity`
> à `e0ba55d`) et fixe les décisions. La session qui l'exécute écrit un
> plan par chantier avec `superpowers:writing-plans`, RED au banc d'abord,
> preuve en réel sur 8799 à 1400 × 900, déploiement par `git hash-object`,
> relevé en tête du plan.

## Faits relevés (à ne pas réinventer)

- Le titre « 127.0.0.1:8765 indique » des captures 1 et 4 est celui du
  **dialogue natif du navigateur** (`confirm` / `alert` / `prompt`). Il
  disparaît dès que l'application n'appelle plus ces fonctions. Le
  Vectorlab en a **20 appels** dans dix modules : `mod-biblio` 3,
  `mod-brouillon` 1 (restauration du brouillon, capture 1), `mod-charpente`
  2, `mod-export` 2, `mod-image` 2, `mod-layers` 2 (suppression de calque,
  capture 4), `mod-planches` 1, `mod-plateau` 4, `mod-tools` 2,
  `mod-vitrail` 1 ; le bundle React en a 3 (`TemplateList.jsx`,
  `studio/screens.jsx`, `studio/shell.jsx`). Un dialogue maison existe déjà
  pour l'impression 3D (`.vl-dlg-boite`, `.vl-dlg-tete` dans
  `vectorlab.css` ; `#impDlg` de `mod-impression`) : c'est le patron.
- L'origine : `backend/app/config.py:102` (`HOST = "127.0.0.1"`),
  `backend/app/main.py:546` (le lanceur ouvre `http://127.0.0.1:8765`),
  `main.py:206` (`_ALLOWED_ORIGIN_HOSTS = {"127.0.0.1", "localhost", "::1",
  ""}`), `routes.py:3551` (garde des hôtes locaux). Chrome, Edge et Firefox
  résolvent **`*.localhost` vers la boucle locale sans toucher au fichier
  hosts** (RFC 6761) : `http://deepotus.localhost:8765` fonctionne sans
  administration.
- Les bulles d'aide : `mod-infobulle.js` (`VL.infobulle.montrer(el)`,
  450 ms, texte du `title`) ; les phrases par outil : `VL.hints`
  (mod-charpente, barre d'état).
- Panneaux : rangées `.ap-ligne` (libellé 64 px + champs 28 px, règle
  « six boutons ne tiennent pas, deux rangées de trois »), pastilles
  `.px-pastille` 22 px, curseurs `<input type=range>` natifs (dureté,
  dépouille, opacité) — capture 2 (Remplissage : `conique`,
  `transparence`, ✕ décalés) et capture 3 (Pixel-art : « Tuile 16 × 16 »
  avec spinner natif, cases à cocher natives, boutons Quantifier /
  Extraire inégaux, pastilles serrées).

## Chantier 1 — une origine nommée

**Décision** : l'application s'ouvre et se sert sous
`http://deepotus.localhost:8765/` (nom d'application, pas d'IP). Le
lanceur (`main.py:546`) ouvre cette URL ; `_ALLOWED_ORIGIN_HOSTS` et la
garde de `routes.py:3551` acceptent `deepotus.localhost` (et gardent
`127.0.0.1` / `localhost` pour les outils en ligne de commande et les
bancs) ; `config.py` gagne `APP_HOSTNAME = "deepotus.localhost"` ; les
pages standalone (`/vectorlab/`, `/spritelab/`, `/tilelab/`, `/atelier`)
utilisent des URL RELATIVES (elles le font déjà : à vérifier au banc). Le
titre des pages devient « Deepotus — Vectorlab » etc. (pas d'hôte). Écart
assumé : le port reste dans l'URL (un port 80 demanderait des droits
administrateur) ; le raccourci d'installation (Inno Setup, `unins000.exe`
présent) pointe sur le lanceur, pas sur l'URL. **Python touché → relance
par l'utilisateur**, vérifiée par `StartTime` du processus contre
`LastWriteTime` des fichiers.

## Chantier 2 — dialogues maison partout

**Décision** : un module `frontend/vectorlab/js/mod-dialogue.js` pur en tête
(`dialogue_spec(type, message, options)` → `{titre, corps, boutons,
defaut}` bancable) + DOM : `VL.dialogue.confirmer(message, {ok, annuler,
danger})`, `VL.dialogue.informer(message)`, `VL.dialogue.saisir(message,
{valeur, valider})` — tous **asynchrones** (`await`), rendus dans
`#vlDlg` avec `.vl-dlg-boite` / `.vl-dlg-tete` (jetons `--aff-*`, typo de
l'application), Entrée = OK, Échap = Annuler, focus piégé, bouton
« danger » rouge pour les suppressions. Les 20 appels du Vectorlab passent
par ce module (les fonctions appelantes deviennent `async` là où il le
faut ; `mod-brouillon` : le dialogue de restauration montre l'heure du
brouillon et deux boutons « Restaurer » / « Repartir du serveur »). Le
bundle React : ses 3 appels passent par le composant de dialogue du
bundle s'il existe (`grep -rn "Dialog\|Modal" frontend/src` d'abord),
sinon par un `patch_bundle_dialogue` en queue de chaîne (contrat des
patchers : lire en octets, sonde du maillon aval, `version` dernier). Un
banc `qa/dialogue.test.mjs` (spec pur) + une preuve : `window.confirm`
stubé pour LEVER une erreur — aucune suppression, restauration ou export ne
le touche plus.

## Chantier 3 — panneaux équilibrés et contrôles maison

**Décision** : une passe d'ergonomie sur les panneaux du persona Vecteur
(Apparence, Remplissage, Couleurs globales) et du persona Pixel
(Pixel-art, Couleurs, Modèle, Ligne de temps, Ajustements) avec des
composants maison réutilisables dans `mod-controles.js` :
- **curseur** `.vl-curseur` (piste 4 px aux jetons `--aff-*`, poignée ronde
  14 px, valeur éditable au clic, molette ±1, Maj ±10) qui REMPLACE les
  `<input type=range>` natifs et les `<input type=number>` à pas fin
  (dureté, opacité, dépouille, rayon, tolérance, FPS, force
  d'accentuation, épaisseur de contour) ;
- **curseur de couleur** `.vl-curseur-couleur` : la piste porte un dégradé
  de la couleur (teinte, ou clair → foncé) et la poignée prend la couleur
  courante — pour la couleur courante / secondaire, à la place des
  pastilles natives `<input type=color>` (qui restent accessibles par un
  double-clic pour le sélecteur système) ;
- **bascule** `.vl-bascule` (interrupteur) à la place des cases natives ;
- **rangée de boutons** `.vl-rangee` : boutons de même largeur (`flex: 1 1
  0`), 28 px de haut, centrés, jamais plus de trois par rangée, libellés
  courts ; les pastilles de palette en grille 6 × n de 22 px avec 6 px
  d'écart.
Un **audit DOM bancable** (`qa/ergonomie.test.mjs` : pour chaque
`.ap-ligne` visible, `scrollWidth ≤ clientWidth + 1`, chaque contrôle ≥ 28
px, boutons d'une rangée à ± 1 px de largeur, aucun `<input type=range>`
ni `<input type=checkbox>` natif dans les panneaux visés) passe dans les
trois personas et sur plusieurs sélections ; le banc `theme.test.mjs`
refuse toujours les hex hérités.

## Chantier 4 — l'aide didactique animée et son skill

**Décision** : une **fiche didactique** par option (outil, bouton,
réglage), affichée au survol long (≥ 900 ms, après la bulle courte) ou par
« ? » sur la rangée, dans un encart `.vl-didact` (320 px) : titre, une
phrase « pour un enfant de cinq ans », et une **séquence animée à trois
temps** faite de **vraies captures** de l'application : 1) l'état de
départ, 2) la sélection ou le geste (curseur ou zone surlignés), 3) le
résultat. Format : une image animée **WebP** (ou une APNG) de 320 × 200
tournant en boucle avec 1,2 s par temps, produite par un script, jamais
dessinée à la main. Rangement : `frontend/vectorlab/aide/<module>.<id>.webp`
+ `aide/index.json` `{ id, titre, phrase, fichier, version }` ; le panneau
lit l'index ; une option sans fiche garde la bulle courte.

**Le skill `didacticiel-option`** (à créer avec `skill-creator`, dans
`C:\Users\olivi\.claude\skills\didacticiel-option\`) est la procédure qui
FABRIQUE une fiche : (1) lire le code de l'option (module, id, commande)
pour dire ce qu'elle fait sans inventer ; (2) préparer un document de
démonstration minimal (un objet, une image ou un calque pixel) sur le
backend de preuve 8799 ; (3) capturer les trois temps **dans la page**
par sérialisation du SVG de `#canvasHost` + `#overlay` (et du panneau
concerné) vers un canvas → PNG (la capture d'écran du volet intégré ne
dessine pas en onglet caché, mesuré ; la sérialisation SVG marche) ; (4)
assembler l'animation avec le python embarqué (Pillow : `save(...,
format="WEBP", save_all=True, duration=1200, loop=0)` ; APNG en repli) ;
(5) écrire la phrase « à un enfant de cinq ans » (une action, un effet,
aucun jargon) ; (6) inscrire la fiche dans `aide/index.json` et la
prouver (le survol long montre l'encart, l'image tourne, la phrase est
là). Le skill est écrit pour être rappelé à chaque nouvelle option, avec
un banc `evals/evals.json` de trois options (Contour sombre, Dépouille,
Créer le calque pixel) et une vérification que chaque fiche a bien trois
temps distincts (les PNG diffèrent) et une phrase ≤ 25 mots.

## Ordre et périmètre

1. Chantier 2 (dialogues) — il supprime aussi le « 127.0.0.1:8765 indique ».
2. Chantier 1 (origine nommée) — Python, relance.
3. Chantier 3 (panneaux) — audit d'abord, composants ensuite.
4. Chantier 4 (skill + fiches) — le skill, puis les trois fiches du banc,
   puis les options des captures (Remplissage, Pixel-art, Modèle).
Aucune dépendance payante ; tout se prouve sur 8799 ; chaque chantier a
son plan, son relevé, son déploiement.
