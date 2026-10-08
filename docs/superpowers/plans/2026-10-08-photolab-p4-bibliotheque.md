# Photolab P4 — Bibliothèque, Envoyer vers, liens avec les autres labs (t139)

**But :** relier le Photolab au reste de Deepotus par les mécanismes EXISTANTS de la Bibliothèque (skill
`lab-externe-deepotus`, references/bibliotheque.md) : ouvrir, enregistrer avec son fichier de travail, envoyer vers
et depuis les autres écrans. Un export n'écrase jamais l'original.

**Déjà là (t136/t137) :** `/ouvrir` (copie d'une image de la Bibliothèque), `/bibliotheque` (PNG/JPG sous
`photolab_<horodatage>_<nom>`, source `photolab`), sélecteur `__dzLibPicker` du parent, grille de repli, dépôt d'un
fichier sur la scène.

## Ce que P4 ajoute

| # | Pièce | Où |
|---|-------|----|
| A1 | Fichier de travail : `/bibliotheque` enregistre aussi `biblio/<souche>.pcraft` (calques) ; l'index note `doc_id = <souche>.pcraft`. | `photolab_routes.py` |
| A2 | Lignée : `/bibliotheque` accepte `parent` (image de la Bibliothèque d'où vient le document) → `noter(parent=…, relation="retouche")`. Parent inconnu ou nom refusé : ignoré, jamais une erreur. | `photolab_routes.py` |
| A3 | Rouvrir avec les calques : `/ouvrir` d'une image `photolab_*` dont le fichier de travail existe ouvre une COPIE du `.pcraft` (`travail: true`) ; `calques: false` force l'image aplatie. L'original (image et `.pcraft`) n'est jamais réécrit. | `photolab_routes.py` |
| B1 | Contrat d'envoi entre écrans : l'expéditeur pose `top.__dzEnvoiImg = {cible, image, t}` ; le récepteur le CONSOMME au chargement (frais ≤ 120 s, même cible) ; `?img=` d'abord. | `frontend/shared/dz-envoi.js` |
| B2 | Bundle, maillon de queue `patch_bundle_plenvoi.py` : dans `__dzSendTo` (images) les cibles « Photolab », « Vectorlab », « Tile Lab » ; `__dzEnvoi(cible, nom)` ; `window.__dzEnvoyerVers(nom, de)` pour qu'un lab en iframe ouvre le MÊME menu. Pins `__dzSendTo` 2 → 3 (test_library_sendto, test_quick_bundle). | `scripts/`, bundle |
| C1 | Photolab : ouverture au chargement (`?img=` ou envoi) ; Fichier › « Envoyer vers… » = enregistrer dans la Bibliothèque (nouveau fichier) puis le menu du parent ; Enregistrer passe `parent`. Nom affiché sans le préfixe `photolab_<horodatage>_`. | `frontend/photolab/` |
| C2 | Vectorlab : un envoi crée un document à la taille de l'image et la pose (`?doc=…&img=…`). | `frontend/vectorlab/` |
| C3 | Tile Lab : un envoi choisit l'image comme source. | `frontend/tilelab/` |
| D | Textes : `photolab.envoi.*` (fr/en), libellés des cibles dans le dictionnaire de la surcouche. | `frontend/shared/i18n/` |

Studio, Quick, Montage, Sprite Lab, Cardforge, Scheduler, Chapitres : cibles EXISTANTES de `__dzSendTo`, atteintes
depuis le Photolab par `__dzEnvoyerVers` (aucune cible dupliquée).

## Bancs

- `test_photolab_biblio.py` (faux moteur) : A1-A3, refus, aucune réécriture de l'original, lignée, index.
- `test_photolab_fidelite.py` (vrai moteur) : `.pcraft` enregistré puis rouvert → mêmes calques, même rendu.
- `test_photolab_envoi.py` : le maillon (octets, deltas, rejeu sur le bundle de main 85b93a00, double application
  refusée, aucun .bak), le menu exécuté sous node (cibles, global posé, navigation, `de:"photolab"` sans Photolab),
  compteurs figés (`x.useState(` 731, `DzTracks` 181), `node --check`.
- `qa/envoi.test.mjs` (Photolab) : `lireEnvoi` (URL, global frais / périmé / autre cible, consommation), entrée de
  menu « Envoyer vers… », `nomDocument` sans préfixe.
- Mutations : supprimer l'écriture du `.pcraft`, ouvrir l'original au lieu d'une copie, oublier la consommation,
  retirer une cible, inverser la garde de fraîcheur.
- Preuve sur 8799 : Bibliothèque → Envoyer vers Photolab ; retouche ; Enregistrer (calques gardés) ; rouvrir ;
  Envoyer vers Vectorlab et Tile Lab.
