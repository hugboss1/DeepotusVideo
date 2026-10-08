# Photolab P5 — installation, licences, repli natif, aide (t140)

**But :** livrer le moteur avec l'installeur sans confiance aveugle, dire d'où vient chaque pièce (À propos), offrir
le repli « app native » prévu par D10, et des fiches didactiques sur les options principales.

## Relevés (08/10/2026)

- `photocraft-cli.exe` et `photocraft.exe` n'importent ni `vcruntime140`, ni `msvcp140`, ni l'UCRT
  (`api-ms-win-crt-*`) : Rust, CRT statique. **Aucun redistribuable VC++ à installer** ; un banc le garde (si une
  version future en importe un, il rougit).
- L'archive livre `LICENSE-MIT`, `LICENSE-APACHE`, trois `OFL-*.txt` (polices BIZ UD Mincho, BIZ UD PGothic,
  Shippori Mincho), `README.md`, `portable.txt` (préférences de l'app native à côté de l'exe).
- L'installeur copie tout l'arbre préparé (`[Files] Source: "{#AppRoot}\*"`) : le dossier `vendor\` y entre s'il
  est préparé — aujourd'hui sans aucune vérification.
- `photocraft.exe --control <port> --control-token-file <f> --automation-read-root <d> --automation-write-root <d>` :
  serveur JSON lignes sur 127.0.0.1 ; 1re ligne `{"method":"auth","params":{"token":<64 hex>}}` ; `app.open {path}`,
  `app.save {path}` (relatifs aux racines), `app.quit`.

## Pièces

| # | Pièce | Où |
|---|-------|----|
| A1 | Manifeste fichier par fichier (`fichiers` : chemin → taille + sha256) dans `vendor/photocraft.json` ; `scripts/verifier_vendor.py <dossier>` (0 = conforme ; fichier manquant, en trop ou altéré = 1, liste dite). | `vendor/`, `scripts/` |
| A2 | `build-installer.ps1` étape 4c : fournit le moteur s'il manque (`vendor_photocraft.py`, release officielle, empreinte de l'archive), le VÉRIFIE fichier par fichier dans l'arbre préparé, pose `NOTICE-photocraft.txt` ; échec = build arrêté. | `scripts/build-installer.ps1` |
| B1 | `vendor/NOTICE-photocraft.txt` : composants tiers, licences, dépôt ; servi avec les licences par `GET /api/photolab/licences` (liste) et `/licences/{nom}` (liste blanche). | `vendor/`, routes |
| B2 | « À propos du Photolab » : dialogue maison — version du moteur, crédits, chaque licence ouvrable. | `mod-menus.js` |
| C1 | Repli natif : `POST /api/photolab/natif/ouvrir` (enregistre le document actif en `natif/<base>.pcraft`, lance ou réutilise `photocraft.exe --control` sur un port libre avec un jeton, `app.open`) ; `POST /natif/reprendre` (`app.save` puis ouverture dans le Photolab) ; `GET /natif/etat`. | `photolab_natif.py`, routes |
| C2 | Fichier › « Ouvrir dans l'app native » / « Reprendre depuis l'app native ». | `mod-menus.js`, `mod-fichier.js` |
| D1 | Ids stables : `pl-outil-<outil principal de l'emplacement>`, `pl-aj-<réglage>`. | `mod-outils.js`, `mod-reglages.js` |
| D2 | Fiches (skill didacticiel-option) : Sélection rectangulaire, Baguette magique, Recadrer, Teinte/Saturation ; encart partagé `mod-didact.js`. | `frontend/photolab/aide/` |
| E | Textes `photolab.apropos.*`, `photolab.natif.*` (fr/en). | `i18n/photolab.json` |

## Bancs

- `test_photolab_installeur.py` : manifeste = dossier (si présent), vérificateur (altéré, manquant, en trop),
  étape 4c présente et bloquante, aucune dépendance VC++ (imports PE), NOTICE cite chaque licence livrée.
- `test_photolab_natif.py` : FAUX serveur de contrôle (auth, app.open, app.save) — jeton exigé, port libre, chemins
  relatifs, réutilisation, reprise ; section VRAIE app native derrière `DZ_NATIF_REEL=1` (ouvre une fenêtre).
- `qa/` : menu (entrées natives), À propos ; `qa/aide.test.mjs` (contrôleur commun).
- Mutations ; preuve 8799.
