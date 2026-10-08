# Traduction L1 — coque, navigation, Réglages, Bibliothèque (t141)

Skill `traduction-deepotus`. Base FR (langue de référence), EN par le dictionnaire ; `dzT(clé, vars)` global (chargé
avant le bundle), langue fixée au chargement (`dzSetLang` recharge).

## Périmètre mesuré (08/10/2026, main 92bec8ed)

Fermeture des composants appelés depuis la coque (`lg`, en-tête `ng`), les Réglages (`xm` et ses 14 onglets) et la
Bibliothèque (`vm`), vues des autres lots exclues (Studio `Lh`, Quick `um`, Scheduler `Lm`, News `pm`, Templates `fm`,
Chapitres, Son & VFX, Game Assets, Montage) et le Transfert (`DzTransfert`, lot L5). Balayage lexical du bundle
(chaînes "…" '…' et morceaux de gabarits) : ~870 littéraux candidats (bruit CSS compris) dans 53 composants, dont
~320 dans la couche `frontend/patches/montage.js` (Corbeille, Fiche, Recherche, Kits, Projets, Nettoyage,
Commentaires, Lignée, Méta…). S'y ajoutent les fonctions de module de la Bibliothèque (menu « Envoyer vers »,
sélecteur, puces de provenance, projets) et la liste du rail.

Le socle Vite est en ANGLAIS (« Connected accounts », « API keys »…) : son texte français est ÉCRIT (fr = référence),
l'anglais d'origine devient `en`. Les ajouts (Coffre, Plafonds, Dépenses, Appareils, Bibliothèque DAM) sont en
français : leur anglais est écrit.

## Mécanisme

| Origine du texte | Où il change |
|---|---|
| couche `frontend/patches/montage.js` | dans la couche, puis `scripts/refresh_layer.py --layer montage` |
| socle Vite et textes posés par les patchers | maillon de queue `scripts/patch_bundle_i18n_l1.py` : table de substitutions consignée (`scripts/i18n_l1_paires.json`, avant -> après, chacune unique et comptée), rejouée à l'octet près sur le bundle de base par le banc |

Une concaténation (« Coffre ouvert : »+n+« clé(s)… ») devient UN appel `dzT("reglages.coffre.ouvert", {n})` ; un
pluriel, deux clés `.un` / `.plusieurs`. Rien d'envoyé au serveur ni de stocké n'est traduit (ids, `provider`, clés
localStorage, noms de fichiers — `data-dz-brut`).

Dictionnaires : `frontend/shared/i18n/coque.json`, `reglages.json`, `biblio.json` (assemblés par
`scripts/i18n_assembler.py`).

## Bancs

- `test_i18n_l1.py` : maillon (octets, rejeu sur la base, double application refusée, aucun .bak), chaque `dzT`
  du périmètre résolu, fr/en non vides, mêmes variables, AUCUN littéral français visible restant dans le périmètre
  (balayage lexical rejoué, liste d'exceptions motivée), compteurs figés (`x.useState(` 731, `DzTracks` 181).
- Bancs existants qui lisent un texte du périmètre : mis à jour (clé + valeur du dictionnaire).
- Mutations ; balayage ; preuve FR et EN sur 8799 (coque, chaque onglet des Réglages, Bibliothèque et sa fiche).
