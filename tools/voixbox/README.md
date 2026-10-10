# Voixbox — ta voix « clonée » en direct, sur ton propre PC

Voixbox donne au **Direct** d'Avatar live une voix convertie **en local**, sur ta carte graphique : gratuit, sans
envoyer ta voix à un service en ligne. Il sert aussi pour la voix du Personnage, quand tu préfères ne pas passer par
ElevenLabs (la voie « cloud », payante, qui ne demande aucune installation).

Il est **optionnel**. Sans lui, l'écran Direct propose « Ma voix, telle quelle » et la voix ElevenLabs.

Ce qu'il faut :

- une carte graphique **NVIDIA** avec **6 Go** de mémoire ou plus (testé sur une RTX 2080 Ti 11 Go) ;
- environ **6 Go** de disque et **15 à 30 minutes** pour l'installation (une seule fois) ;
- **10 à 15 minutes** de ta voix enregistrée, puis **une heure** de calcul pour l'entraîner (une fois par voix).

Le moteur est **RVC** (Retrieval-based Voice Conversion, licence MIT), par sa « WebUI » officielle : la même
installation sert à **entraîner** une voix et à la **faire parler** pendant le Direct.

> Ne clone que **ta** voix, ou celle d'une personne qui t'a donné son accord. L'application te le fait confirmer à
> la création de chaque Personnage.

## 1. Installer (une fois)

Ouvre PowerShell **dans le dossier de l'application** (là où se trouve `tools\voixbox`) et lance :

    powershell -ExecutionPolicy Bypass -File tools\voixbox\installer.ps1

Le script fait, dans l'ordre :

1. installe `uv` (un gestionnaire Python) s'il n'est pas déjà là ;
2. télécharge la RVC WebUI, **épinglée** sur une version vérifiée ;
3. crée son Python 3.12 et y installe **torch pour CUDA 12.8** (environ 3 Go) ;
4. installe ses dépendances ;
5. télécharge ses poids (environ 560 Mo : HuBERT, RMVPE, modèles pré-entraînés, silences d'entraînement) ;
6. vérifie que la carte graphique est vue (`CUDA True | NVIDIA …`).

Il s'arrête à la première erreur et dit laquelle.

### Si ton antivirus est Avast (ou un autre qui « inspecte » les connexions)

C'était le cas sur la machine de référence : Avast intercepte les connexions sécurisées et pose une variable
`SSLKEYLOGFILE`. Le script s'en occupe **pour lui seul** (il n'est rien changé à ton système) :

- il retire `SSLKEYLOGFILE` de son propre environnement — sinon Python plante avec `no OPENSSL_Applink` ;
- `git`, `uv` et Python lisent les certificats **du magasin Windows** (schannel, `--native-tls`, `truststore`) —
  sinon les téléchargements échouent avec « certificate verify failed ».

`lancer.ps1` et `webui.ps1` font la même chose à chaque démarrage.

## 2. Enregistrer ta voix

La qualité de la voix clonée dépend presque tout entière de cet enregistrement.

- **10 à 15 minutes** de parole, **ta voix seule** : pas de musique, pas de deuxième voix, pas d'écho.
- Une pièce calme, le micro à 15-20 cm, toujours le même micro et la même distance.
- Parle **comme pendant tes directs** : même ton, même énergie. Varie les phrases (questions, chiffres, phrases
  longues et courtes).
- Évite les saturations : les crêtes ne doivent pas toucher le rouge.
- Plusieurs fichiers courts (30 s à 2 min) valent mieux qu'un seul long. WAV de préférence (MP3 et FLAC passent).
- Range-les dans **un dossier qui ne contient qu'eux**, par exemple `C:\Voix\oli`.

## 3. Entraîner la voix (une fois par voix)

1. Ouvre la WebUI :

       powershell -ExecutionPolicy Bypass -File tools\voixbox\webui.ps1

   Ton navigateur s'ouvre sur `http://127.0.0.1:7865`. La WebUI est en français. Laisse la fenêtre PowerShell
   ouverte pendant tout l'entraînement.

2. Va dans l'onglet **Entraîner**. (Les libellés ci-dessous sont ceux de la WebUI en français, mot pour mot.)

3. **Étape 1** — remplis :
   - **Nom de l'expérience** : un nom court **sans espace ni accent**, par exemple `oli`. Ce sera aussi le nom de la
     voix dans l'application ;
   - **Taux d'échantillonnage cible** : `40k` ;
   - **guidage de la hauteur** (« Indique si le modèle dispose d'un système de guidage de la hauteur… ») : **Oui** —
     facultatif pour la parole selon la WebUI, mais c'est lui qui garde l'intonation naturelle ;
   - **Version** : `v2`.

4. **Étape 2** — **Chemin du dossier d'entraînement** : le dossier de tes enregistrements (`C:\Voix\oli`).
   **Sélectionnez l'algorithme d'extraction de la hauteur** : **rmvpe** (cette version n'accepte que `pm` et `rmvpe`).

5. **Étape 3** — les réglages d'entraînement :
   - **Fréquence de sauvegarde (save_every_epoch)** : `25` ;
   - **Nombre total d'époques d'entraînement (total_epoch)** : **200** pour une voix de qualité (100 pour un premier
     essai) ;
   - **Taille du batch par GPU** : `8` avec 8 à 12 Go de mémoire graphique, `4` avec 6 Go ;
   - **Enregistrer un petit modèle final dans le dossier 'weights' à chaque point de sauvegarde** : **Oui** ;
   - garde les modèles de base pré-entraînés G et D proposés (`f0G40k.pth` et `f0D40k.pth`).

6. Clique **Entraînement en un clic**. La WebUI enchaîne quatre étapes, affichées une à une : découpage des
   données, extraction de la hauteur et des caractéristiques, entraînement du modèle, index. Compte environ
   **1 h 15** pour 200 époques sur une RTX 2080 Ti (mesuré le 10/10 : **18 minutes** pour 40 époques sur 10 min de
   voix, soit 21 s par époque, plus environ 2 minutes de préparation et d'index).

7. À la fin, le modèle est dans `tools\voixbox\rvc-webui\assets\weights\oli.pth` et son index dans
   `tools\voixbox\rvc-webui\logs\oli\added_….index`.

8. Range-les là où Voixbox les cherche :

       powershell -ExecutionPolicy Bypass -File tools\voixbox\ranger-voix.ps1 -Nom oli

   (dossier `%LOCALAPPDATA%\DeepotusVideoGen\voix_rvc\oli\`).

**Écouter avant de s'en servir** : dans l'onglet **Inférence du modèle** de la WebUI, onglet **Inférence unique**, choisis `oli.pth`, donne un court
enregistrement de ta voix normale et écoute le résultat. Si la voix grésille ou sonne métallique : plus d'époques,
ou un enregistrement plus propre. Si elle est trop aiguë ou trop grave, règle la **transposition** (en demi-tons).

## 4. S'en servir dans l'application

1. Lance Voixbox et **laisse la fenêtre ouverte** :

       powershell -ExecutionPolicy Bypass -File tools\voixbox\lancer.ps1

   Il affiche `Voixbox écoute http://127.0.0.1:17495 — 1 voix entraînée(s)`.

2. Dans l'application : **Avatar live → Direct → Voix envoyée → « Voix RVC locale — oli »**. Règle la
   transposition si besoin (par exemple `+12` pour une voix d'homme vers une voix de femme), puis démarre le direct.

3. La barre du direct affiche le nombre de segments convertis, la latence et les pertes.

## Latence (mesurée le 10/10/2026)

| Voie | Segment | Latence d'un segment | Retard de l'image |
|---|---|---|---|
| ElevenLabs (cloud) | 0,5 s | médiane 969 ms (920 à 1 330 ms ; 2,2 s au tout premier) | 2,1 s |
| Voixbox RVC (RTX 2080 Ti) | 0,5 s | médiane 110 ms, max 120 ms | 0,75 s |

La voie locale est donc presque **neuf fois plus rapide** que le cloud, et gratuite. Deux réglages de Voixbox ont été
nécessaires pour y arriver (mesurés, dans `server.py`) : l'index de la voix est lu une seule fois au lieu de l'être à
chaque segment (−220 ms), et la connexion reste ouverte entre deux segments.

Le **retard de l'image** est voulu : la vidéo envoyée à Decart est retardée d'autant que la voix, pour que les
lèvres et la voix arrivent ensemble.

## Dépannage

- **« Voixbox ne répond pas sur http://127.0.0.1:17495 »** : la fenêtre de `lancer.ps1` est fermée, ou le port est
  pris. Relance `lancer.ps1`. Pour un autre port, pose `VOIXBOX_URL=http://127.0.0.1:<port>` dans le `.env` de
  l'application.
- **La voix n'apparaît pas dans la liste** : vérifie que le dossier `voix_rvc\<nom>\` contient bien un `.pth` et
  que le nom ne contient que des lettres, chiffres, `-` ou `_`.
- **`no OPENSSL_Applink`** : la variable `SSLKEYLOGFILE` (Avast) est revenue. Passe toujours par les scripts
  `lancer.ps1` et `webui.ps1`, qui la retirent.
- **L'entraînement s'arrête à « Découpage des données »** avec `No module named 'infer'` ou `cannot import name
  'utils'` : la WebUI a été lancée sans `webui.ps1`. Ce script pose `PYTHONPATH` et `PYTHONSAFEPATH=1`, comme le
  Python embarqué du paquet officiel.

## Contrat (pour les développeurs)

| Requête | Corps | Réponse |
|---|---|---|
| `GET /health` | — | `{"ok": true, "moteur": "rvc", "sr": 16000, "gpu": "...", "modeles": [{"nom", "index"}]}` |
| `POST /convertir?modele=<nom>&transpose=<-12..12>` | PCM s16le mono 16 kHz, 10 s au plus | PCM s16le mono 16 kHz, en-tête `X-Latence-Ms` |

Bancs : `backend/tests/test_voixbox_contrat.py` (ce serveur, moteur factice) et
`backend/tests/test_avatar_voix_direct.py` (le client de l'application).
