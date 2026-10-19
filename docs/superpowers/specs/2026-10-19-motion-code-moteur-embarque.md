# Rendu motion code (t238) sans Edge : moteur de navigateur embarqué — relevé du 19/10/2026

But : le nœud Studio « Rendu motion code » (t238, `backend/app/services/motion_code.py`) ne doit plus dépendre de
Microsoft Edge installé sur le PC. On livre avec l'application un moteur sans fenêtre ÉPINGLÉ, comme ffmpeg
(`app\bin`) et photocraft (`vendor\`), sans rien télécharger à l'exécution, et avec le MÊME bac à sable (CSP, profil
jetable, Fetch qui refuse tout, mandataire mort, délai 120 s / 20 s par image, horloge virtuelle).

Base : origin/main 4c16d972. Relevé fait sur les sources officielles le 19/10/2026 ; mesures sur ce PC (Windows 11).

## 1. Candidat : chrome-headless-shell (Chrome for Testing)

| | |
|---|---|
| Source | Chrome for Testing (GoogleChromeLabs), JSON officiel `last-known-good-versions-with-downloads.json` (horodaté 2026-10-17T09:18:35Z) |
| Canal Stable | **155.0.8059.84** (révision Chromium 1697595) — Beta 157.0.8103.6, Dev 158.0.8106.0, Canary 158.0.8110.0 |
| URL win64 | `https://storage.googleapis.com/chrome-for-testing-public/155.0.8059.84/win64/chrome-headless-shell-win64.zip` |
| sha256 du zip (mesuré) | `5ca590a4968864e219ea25ccd134597ef8898a733a4698c07fc3e8b2c480fef4` |
| Taille du zip | 123 681 250 octets (118 Mio) |
| Décompressé, complet | 290 511 280 octets (277 Mio) : exe 208 Mio, `locales\` 43 Mio (220 fichiers), icudtl 11 Mio, SwiftShader 5 Mio… |
| Décompressé, allégé | 247 150 164 octets (236 Mio) : on ne garde que les langues `en-US*` et `fr*` (8 fichiers sur 220) |
| Ce qui s'ajoute à l'installeur (estimation) | allégé, en LZMA2 solide (xz -9, comme `Compression=lzma2/max`) : **79 429 820 octets ≈ 76 Mio** (complet : 82 Mio) |

Taille de l'installeur aujourd'hui : `DeepotusVideoGen-Setup-2.8.0.exe` = 130 400 236 octets (124 Mio).
**Avec le moteur : ≈ 200 Mio (+76 Mio, +61 %) ; sur le disque après installation : +236 Mio.**

Pourquoi le « headless shell » et pas le Chrome for Testing complet : c'est le moteur Chromium sans l'interface du
navigateur (pas de fenêtre possible, pas d'extensions, pas de mise à jour, pas de compte), exactement ce dont le bac à
sable a besoin, et environ deux fois plus léger que `chrome-win64.zip`.

### Licence et avis à livrer
- Code Chromium : licence **BSD-3-Clause** (« The Chromium Authors »).
- L'archive contient `LICENSE.headless_shell` (2,4 Mio, 44 592 lignes) : la licence Chromium ET les avis de TOUS les
  composants tiers (ICU, V8, Skia, SwiftShader, ANGLE, libpng, zlib…). On le livre tel quel à côté de l'exe, plus une
  `NOTICE-chrome-headless-shell.txt` qui dit ce que c'est, sa version, d'où il vient et son empreinte (modèle :
  `vendor/NOTICE-photocraft.txt`).
- Le dépôt chrome-for-testing (scripts et JSON) est sous Apache-2.0 ; ça ne concerne pas les binaires.
- **Point d'attention, à trancher par toi** : le fichier `ABOUT` de l'archive dit « Google Chrome · Copyright 2026
  Google LLC · See the Terms of Service at chrome://terms ». Les binaires CfT sont donc construits et signés par Google.
  Ils sont redistribués couramment : Playwright (paquet `chromium-headless-shell` 156.0.8078.12, qui récupère ces mêmes
  archives CfT sur son CDN) et Puppeteer. Mais aucune page officielle ne dit en toutes lettres « redistribution
  permise dans un produit ». La page officielle précise aussi que CfT a été créé pour l'automatisation et les tests, et
  qu'il ne faut lui donner que du contenu de confiance. Chez nous, le contenu est écrit par un modèle, mais le bac à
  sable le borne (contrôle statique, CSP, aucune requête, aucune navigation, profil jetable). Si tu veux zéro
  ambiguïté sur la marque, l'alternative est une construction Chromium « pure » (révision 1697595, mêmes sources,
  licence BSD seule). Mais il n'en existe pas de version sans fenêtre officielle prête à l'emploi pour Windows : il
  faudrait la construire nous-mêmes. Ce n'est pas proposé.

### Mises à jour de sécurité
Un moteur épinglé ne se met pas à jour tout seul, contrairement à Edge. Le monter de version = changer le manifeste
(version, URL, sha256, tailles) puis reconstruire l'installeur. À faire à chaque release (le script affiche la
dernière Stable à côté de la version épinglée). Le risque est borné : on ne charge que des pages contrôlées, réseau et
navigation coupés.

## 2. Compatibilité mesurée (sans changer une ligne de motion_code.py)
`DEEPOTUS_EDGE=<…>\chrome-headless-shell.exe`, python embarqué, `backend/tests/test_motion_code.py` :
- archive complète : **85 PASS, 0 FAIL** ;
- archive allégée (langues en-US + fr) : **85 PASS, 0 FAIL** ; après le banc, comptés à la main :
  0 processus `chrome-headless-shell.exe` vivant, 0 profil `dz_motion_code_*` restant.

Drapeaux de `_lancer_edge` : `--headless=new` est accepté et ignoré (le shell est toujours sans fenêtre).
`--user-data-dir` (profil jetable), `--remote-debugging-port=0` + fichier `DevToolsActivePort` dans le profil,
`--proxy-server=http://127.0.0.1:9` / `--proxy-bypass-list=<-loopback>`, `--block-new-web-contents`,
`--deny-permission-prompts`, `--mute-audio`, `--hide-scrollbars`, `--disable-*` : tous acceptés, pas d'erreur de
démarrage.
Commandes CDP utilisées, toutes servies : `Browser.setDownloadBehavior`, `Target.createTarget` / `attachToTarget`
(session aplatie), `Page.enable`, `Runtime.enable`, `Fetch.enable` / `failRequest` / `requestPaused`,
`Page.addScriptToEvaluateOnNewDocument` (horloge virtuelle), `Emulation.setDeviceMetricsOverride`, `Page.navigate`
(coquille `data:`), `Page.setDocumentContent`, `Runtime.evaluate`, `Page.captureScreenshot`,
`Page.handleJavaScriptDialog` ; événements `Page.frameRequestedNavigation`, `Page.windowOpen`,
`Target.targetCreated`, `Page.javascriptDialogOpening`. Pièges P1-P11 (refus, navigation, fenêtre, fetch / XHR /
image déguisés, boucle infinie au chargement et dans dzFrame, 10 Mo) : arrêt propre.

**Trou trouvé dans le banc t238** : le contrôle « aucun Edge du bac à sable vivant » ne compte que les processus
`msedge.exe`. Avec un autre moteur, il ne voit rien. Correction prévue : compter le nom de l'exécutable du moteur
réellement utilisé (ou tout processus dont la ligne de commande contient `dz_motion_code_`, quel que soit son nom).

## 3. Comparaison
| | chrome-headless-shell CfT 155 | Playwright `chromium-headless-shell` | Edge du PC (aujourd'hui) |
|---|---|---|---|
| Binaire | archive CfT officielle | la MÊME archive CfT (156.0.8078.12), relayée par cdn.playwright.dev | celui que l'utilisateur a, ou pas |
| Épinglage | version + sha256 dans notre manifeste | idem, mais via le CDN d'un tiers | aucun (mis à jour par Windows) |
| Ajout à l'installeur | ≈ 76 Mio | ≈ 76 Mio | 0 |
| Dépendance Python | aucune (notre client CDP `websockets.sync` reste) | aucune si on prend juste le zip | aucune |
Conclusion : Playwright n'apporte rien (même binaire, un intermédiaire de plus). **Recommandation : CfT 155.0.8059.84,
archive officielle Google, allégée aux langues fr / en-US.**

## Décision de l'utilisateur (19/10/2026)
- **Validé : chrome-headless-shell CfT 155.0.8059.84, allégé aux langues fr + en-US** (≈ +76 Mio à l'installeur).
- **Edge reste en SECOURS** : moteur embarqué d'abord ; s'il manque, Edge s'il est installé ; sinon message FR / EN.

## 4. Câblage (validé)
1. `vendor/chrome-headless-shell.json` : version, révision, URL, taille, sha256 de l'archive, liste des langues
   gardées, taille + sha256 de chaque fichier gardé (comme `vendor/photocraft.json`).
2. `scripts/vendor_chrome_headless_shell.py` (modèle `vendor_photocraft.py`) : télécharge, vérifie taille + sha256
   AVANT d'extraire (sinon rien n'est extrait), refuse toute entrée qui sortirait du dossier, ne garde que les langues
   listées, vérifie chaque fichier → `vendor/chrome-headless-shell-155.0.8059.84/` (jamais versionné, `.gitignore`).
   `scripts/build-installer.ps1` étape 4d : appelle le script s'il est absent du poste de build, recopie dans
   `stage\app\vendor\…` avec `LICENSE.headless_shell` et `NOTICE-chrome-headless-shell.txt`.
   L'application ne télécharge JAMAIS rien.
3. Résolution dans `motion_code.py` : `trouver_moteur()` → (1) `DEEPOTUS_NAVIGATEUR` (bancs) ; (2) le moteur embarqué
   `<app>/vendor/chrome-headless-shell-<version>/chrome-headless-shell.exe` (dossier installé ou dossier du dépôt) ;
   (3) **à toi de choisir** : Edge en secours, ou plus du tout. Si aucun moteur : message clair FR / EN (« Le moteur de
   rendu motion code est absent : réinstalle Deepotus Video Gen » / « The motion code renderer is missing: reinstall
   Deepotus Video Gen »). `DEEPOTUS_EDGE` reste lu par compatibilité avec les bancs existants.
   Le bac à sable reste identique : mêmes drapeaux, mêmes commandes CDP, mêmes délais, même horloge.
4. Bancs : `test_motion_code_moteur.py` neuf (ROUGE sur la base, puis VERT) : ordre de résolution, moteur embarqué
   trouvé en premier, secours Edge selon ta décision, message FR / EN quand il n'y a rien, manifeste cohérent (sha256
   faux → rien extrait ; entrée `../` refusée ; langues gardées seulement), le build appelle le script ;
   `test_motion_code.py` rejoué avec le moteur embarqué, contrôle des orphelins par nom de moteur ; mutations (copie
   des sources par chemin complet avant, `cmp` après) ; `run-tests.ps1` complet en fond.

## 5. Livré (19/10/2026, local, non poussé)
- `vendor/chrome-headless-shell.json` (76 fichiers épinglés taille + sha256, langues `en-US`, `fr`),
  `vendor/NOTICE-chrome-headless-shell.txt`, `.gitignore` (`vendor/chrome-headless-shell-*/`).
- `scripts/vendor_chrome_headless_shell.py` : récupération (urllib, archive officielle), vérification taille + sha256
  AVANT extraction, refus des entrées hors dossier AVANT d'écrire, filtre des langues, revérification de l'arbre
  (fichier manquant / altéré / en trop, exe illisible, runtime Visual C++), échange atomique `.tmp` → dossier ;
  `--verifier [dossier]`, `--ecrire`, `--derniere` (Stable du jour vs version épinglée).
- `scripts/build-installer.ps1` étape 4d : fournit si absent, recopie dans `stage\app\vendor\`, copie manifeste +
  NOTICE, vérifie l'arbre PRÉPARÉ (écart = build arrêté). Le `.iss` prend `stage\app\*` récursivement : rien à changer.
- `motion_code.py` : `moteur_embarque()`, `trouver_moteur()` (DEEPOTUS_NAVIGATEUR > DEEPOTUS_EDGE > embarqué > Edge),
  `trouver_edge()` ne rend plus qu'Edge, message `moteur` FR / EN (« réinstalle l'application »), `_lancer_edge` :
  exe illisible → arrêt « navigateur » au lieu d'une trace. Drapeaux, CDP, délais, CSP, horloge : inchangés (S1, S2).
- Bancs : `test_motion_code_moteur.py` neuf (ROUGE sur la base : R0 ; VERT 35/35), `test_motion_code.py` 85/85 avec
  l'embarqué SANS variable d'environnement (M4 = l'embarqué ; contrôle des orphelins par le nom du moteur réellement
  utilisé, plus seulement `msedge.exe`), `test_studio_motion_code.py` 41/41. Mutations 22/22 tuées (copie de
  référence par chemin complet avant, `cmp` après : identiques) ; deux défauts révélés et corrigés en route (exe non PE
  → trace brute dans `controler` ; exe illisible → `OSError` brute au lancement).
