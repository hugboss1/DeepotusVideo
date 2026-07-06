# Atelier — Agent d'ingestion de manuscrit (design)

Date: 2026-07-06 · Base: Atelier P1/P2 (spec 2026-07-05)

## Besoin (utilisateur)
Importer un MANUSCRIT COMPLET et laisser un agent IA natif : segmenter par
chapitre (titres importés) ; lister chapitre par chapitre dans la bible tous
les personnages (+ caractéristiques), lieux, objets, dates, indications de
décor et d'ambiance ; faire une RELECTURE GLOBALE pour consolider les
descriptions initiales ; pré-surligner dans le texte toutes les zones
correspondant aux catégories de la bible. Un fichier compagnon (notes de
l'auteur) peut enrichir la consolidation.

## Taxonomie étendue (6 kinds)
`character` · `place` · `object` · `date` (époques, dates, marqueurs
temporels) · `ambiance` (lumière, météo, ton, atmosphère) · `decor`
(éléments de décor / set dressing). Chaque kind: couleur de surlignage,
cadrage de génération de référence dédié. `BibleEntity` gagne `aliases`
(JSON) et `evidence` (JSON: citations par chapitre) — auto-ALTER pour les
bases existantes (BIBLE_ENTITIES_COLUMNS).

## Pipeline (job arrière-plan avec progression)
1. **Segmentation** (`manuscript_agent.segment_chapters`) — heuristiques de
   titres (Chapitre/Chapter/Partie/Prologue…, numérotations, lignes courtes
   en CAPITALES précédées d'une ligne vide) ; repli = 1 chapitre. Titre
   importé, corps = texte du segment. (Les effets de mise en forme docx ne
   survivent pas au texte brut — titres seulement, assumé.)
2. **Extraction par chapitre** (LLM, chunks ≤11k, roster des entités déjà
   connues transmis pour la stabilité des noms) → entités {kind, name,
   aliases, description, quotes verbatim}.
3. **Consolidation globale** (LLM) — fusion doublons/alias inter-chapitres,
   description canonique par entité ; le FICHIER COMPAGNON (≤8k extrait) est
   fourni comme source d'autorité.
4. **Liens/surlignage** — pour chaque chapitre : spans sur toutes les
   mentions (nom + alias, bornes de mots, cap 40/entité/chapitre) + les
   passages cités (quotes) ; écrits dans `chapter.spans`.

Écritures DB: upsert entité par (kind, lower(name)) — un ré-import enrichit
au lieu de dupliquer. Chapitres créés dans l'ordre du manuscrit (série =
nom fourni). Job: dict en process + `GET /api/atelier/manuscript/{job_id}`
{phase, chapter_i/n, message, done, error, stats}.

## API / UI
- `POST /api/atelier/manuscript` (multipart: manuscript, companion?, series)
  → job_id. Extraction texte réutilisée d'Épisodes (txt/docx/pdf).
- `/atelier` : bouton « 📚 Manuscrit » → modal (fichier, compagnon optionnel,
  série) → barre de progression (poll 2 s) → rechargement chapitres+bible.
- Bible: 6 onglets ; légende + selbar étendues aux nouveaux kinds.

## Tests
Segmentation (unitaire, sans LLM) ; pipeline complet sur un manuscrit
synthétique 2 chapitres avec `_chat_dispatch` stubbé (extraction puis
consolidation) : chapitres créés + titres, entités consolidées (alias
fusionnés), spans posés (mentions + quotes), ré-import idempotent.
