# Clapbox — embeddings CLAP en local (optionnel)

Clapbox sert la recherche de sons du tiroir Sons, **par description** et **par similarité**. Il est optionnel.

Sans Clapbox, l'application affiche pourquoi la recherche par description est indisponible. « Comme celui-ci » continue de marcher sur l'index déjà écrit.

Clapbox ne tourne jamais dans l'application : le Python embarqué n'a ni torch ni numpy. Il faut un environnement à part.

    py -3.11 -m venv .venv
    .venv\Scripts\python -m pip install -r requirements.txt
    .venv\Scripts\python server.py

Le service écoute sur `127.0.0.1:17494`. Au premier lancement, environ 2 Go de poids sont téléchargés dans le cache Hugging Face.

Ensuite, dans l'application, ouvre le tiroir Sons, active la recherche par description (✧) puis clique « indexer ».

Les sons générés **ensuite** ne s'indexent pas tout seuls. Relance « indexer » : seuls les sons nouveaux ou modifiés repassent par le service, grâce à leur signature `mtime:taille`.

## Réglages (fichier `.env` de l'application)

- `CLAPBOX_URL` : adresse du service local. Si elle est vide, l'application utilise `http://127.0.0.1:17494`.
- `CLAP_REMOTE_URL` et `CLAP_REMOTE_KEY` : repli vers un service distant qui parle le **même** contrat. Ce service est facturé par son hébergeur. La clé part en `Authorization: Bearer`, et seulement vers le service distant.

## Contrat

| Requête | Corps envoyé | Réponse |
|---|---|---|
| `GET /health` | — | `{"ok": true, "model": "...", "dim": 512}` |
| `POST /embed/text` | `{"texts": [...]}` | `{"dim", "model", "vectors": [[...]]}` |
| `POST /embed/audio` | multipart, champ `files` | `{"dim", "model", "vectors": [[...]]}` |

Deux bancs figent ce contrat :

- côté client : `backend/tests/test_sound_search_index.py`, avec un vrai serveur HTTP de test ;
- côté serveur : `backend/tests/test_clapbox_contrat.py`, avec ce serveur-ci et un moteur factice.
