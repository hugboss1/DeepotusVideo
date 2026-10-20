# Assistant « Demander » — catalogue des éléments et apprentissage continu (19/10/2026)

Branche `chantier/agent-catalogue`, tirée de `claude/plan-agent-a5-a7` (4fcfc8f4 : A0-A7 livrés).
Suite de `2026-10-19-agent-aide-design.md`.

## But

L'application va continuer d'évoluer. L'assistant doit connaître **chaque élément** de l'interface (bouton, onglet,
menu, outil, icône, réglage, raccourci) et ce qu'il fait, pour donner une réponse **cohérente et exacte** à tout
moment, sans que personne ait à réécrire sa connaissance à la main après chaque livraison.

Décisions de l'utilisateur (19/10) :

| Question | Décision |
|---|---|
| Quand l'agent apprend-il ? | **Les deux** : à chaque modification de l'app (développement) ET à chaque question (relevé de l'écran ouvert) |
| Qui rédige « à quoi ça sert » ? | **Extraction + skill** : un script extrait tout ce qui existe, le skill lit le code et rédige le rôle FR/EN, relu en PR |
| Comment retrouver les éléments utiles ? | **Recherche lexicale + synonymes**, écran ouvert prioritaire (pas d'embeddings) |
| Suivi | Les lots apparaissent dans le suivi des chantiers (lot « Assistant Demander ») |

Hors périmètre : un modèle qui « devine » le rôle d'un bouton chez l'utilisateur ; l'apprentissage automatique sur
les conversations des utilisateurs (rien n'est collecté).

## Ordre de grandeur (relevé du 19/10)

≈ 15 500 libellés FR/EN (`frontend/shared/i18n/*.json`), ≈ 470 infobulles dans le bundle, 526 icônes (lexique
imprimable), 35 fiches didactiques de labs, 41 chapitres du guide, l'index des Réglages. Trop pour un message
système : l'agent **cherche** au moment de la question.

## 1. Le catalogue — `docs/agent/catalogue/<ecran>.json`

Un fichier par écran ou lab (`quick.json`, `montage.json`, `vectorlab.json`…), une **fiche par élément** :

```json
{
  "id": "montage.lame",
  "ecran": "montage", "cadre": null,
  "type": "bouton",
  "libelle": {"fr": "lame · Alt+C", "en": "blade · Alt+C"},
  "infobulle": {"fr": "couper le clip sélectionné à la tête (Alt+C)", "en": "…"},
  "icone": "dz-action-couper", "raccourci": "Alt+C",
  "role": {"fr": "Coupe le clip sélectionné à la position de la tête de lecture, sans rien supprimer.",
           "en": "Splits the selected clip at the playhead, without deleting anything."},
  "synonymes": {"fr": ["couper", "scinder", "rasoir"], "en": ["cut", "split", "razor"]},
  "guide": "montage", "fiche": null,
  "localisateur": {"selecteur": "button", "texte": {"fr": "lame · Alt+C", "en": "blade · Alt+C"}},
  "sources": ["i18n:montage.outils.lame", "frontend/dist/assets/index-*.js#title"],
  "empreinte": "sha1 des textes sources",
  "etat": "redige"
}
```

- `type` ∈ bouton · onglet · menu · outil · icone · reglage · raccourci · champ · panneau.
- `etat` ∈ **extrait** (vient d'apparaître, rôle vide) · **redige** (rôle écrit par le skill) · **perime** (une source
  a changé depuis la rédaction) · **retire** (la source a disparu ; gardée une version pour les conversations en
  cours, puis supprimée par le skill).
- `role` : 1 à 2 phrases, ≤ 300 caractères par langue, dit **ce que fait l'élément, quand s'en servir, ce qu'il
  coûte** (payant, sous quel plafond, ou gratuit/local). Écrit d'après le **code**, jamais deviné.
- `localisateur` : même forme que les ancres livrées (sélecteur + texte FR/EN, `libelle`, `cadre`) ; toute fiche qui
  en a un est pointable par `[POINT:<id>]`.
- `ancres.json` reste la liste **choisie à la main** (rail, Réglages, parcours d'AGENT.md) ; une ancre et une fiche
  peuvent partager un id.

## 2. L'extracteur — `scripts/agent/catalogue.py`

Lit le **code** du dépôt, rien d'autre, et met à jour les fichiers du catalogue :

| Source | Ce qui en sort |
|---|---|
| `frontend/shared/i18n/*.json` (clés `zone.objet.role`) | libellés FR/EN regroupés par zone → écran |
| bundle `frontend/dist/assets/index-*.js` | infobulles `title:` (littérales et `dzT(…)`), `aria-label` |
| `frontend/<lab>/index.html`, `js/mod-*.js`, `mod-i18n` | outils, menus, infobulles des labs |
| `frontend/shared/icons/dz-icons.js` + lexique du guide | nom et sens des icônes |
| `frontend/<lab>/aide/index.json` | fiche didactique liée |
| `settings_routes._INDEX_FIXE` / `GET /api/reglages/index` | réglages et leur section |
| `docs/guide/src/chapitres.json` (`ecrans`) | chapitre lié |

Règles :
- **Fusion sans écrasement** : un `role` et des `synonymes` rédigés ne sont jamais réécrits par l'extracteur.
- Nouvelle source → fiche `extrait` ; empreinte changée → `perime` ; source disparue → `retire`.
- Sortie stable (tri par id, une fiche par ligne) pour des diffs lisibles en PR.
- `--check` : code 1 s'il reste une fiche `extrait`/`perime` sur un écran **couvert** (un écran devient couvert
  quand sa rédaction initiale est faite, liste dans `docs/agent/catalogue/_couverture.json`).
- `--rapport` : par écran, nombre de fiches par état (sert au skill et au suivi).

## 3. Bancs

- `backend/tests/test_agent_catalogue.py` : `catalogue.py --check` vert ; ids uniques ; chaque source citée
  existe ; chaque `guide` existe dans `chapitres.json` ; `role` non vide et ≤ 300 caractères dans les deux langues
  pour toute fiche `redige` ; localisateur : texte présent dans le bundle, le dictionnaire ou le lab (comme
  `test_agent_connaissance`).
- C'est ce banc qui « rappelle » le skill : **une livraison qui ajoute ou change un élément visible rougit tant que le
  catalogue n'est pas à jour**.

## 4. Chez l'utilisateur, à chaque question

1. **Relevé de l'écran** : le tiroir envoie avec la question la liste des éléments visibles de l'écran ouvert
   (`button`, `[role=tab]`, `[role=menuitem]`, `[title]`, `[aria-label]` : texte, infobulle, ≤ 120 entrées, chaque
   texte ≤ 80 caractères ; labs via le répondeur de cadre). Rien d'autre (pas de contenu des documents).
2. **Rapprochement** : le serveur relie chaque élément visible à sa fiche (libellé/infobulle normalisés, langue).
3. **Recherche** : index lexical construit au démarrage (accents et casse normalisés, FR+EN, libellés, infobulles,
   rôles, synonymes) ; score = correspondances pondérées + **bonus écran ouvert** + bonus « visible maintenant » ;
   15 fiches au plus.
4. **Message système** = AGENT.md + liste des chapitres + vues + `## Éléments pertinents` (id, chemin d'accès,
   rôle, coût) + `## À l'écran maintenant` (fiches reconnues, puis éléments visibles **non documentés** marqués
   comme tels) + contexte. Le préfixe stable reste en tête.
5. **Règles ajoutées à AGENT.md** : ne décrire un élément qu'à partir de sa fiche ; un élément « non documenté » se
   décrit par ce qu'on voit (libellé, infobulle), sans inventer sa fonction, et la réponse le dit.
6. `[POINT:<id>]` accepte les ids du catalogue qui ont un localisateur.
7. Coût : ≈ +1 500 jetons d'entrée par question ; réponse déterministe à question et écran égaux.

## 5. Le skill `connaissance-agent` (`~/.claude/skills/connaissance-agent/`)

Skill de **développement**, comme `guide-deepotus` : il se déclenche dès qu'une modification visible de
l'application est faite ou livrée (bouton, icône, outil, menu, réglage, raccourci, libellé), quand
`test_agent_catalogue` rougit, ou sur demande (« apprends à l'agent… », « mets à jour la connaissance de
l'assistant »). Procédure :

1. `python scripts/agent/catalogue.py` puis `--rapport` : liste des fiches `extrait` / `perime` / `retire`.
2. Pour chaque fiche à rédiger : **lire le code** de l'élément (gestionnaire, route appelée, garde de coût et
   plafond, effets) et écrire `role` FR puis EN + `synonymes`, d'après les gabarits par type (`references/`).
   Jamais de fonction devinée : si le code ne permet pas de conclure, le dire dans la PR.
3. Localisateur : relever sur la page réelle (backend de preuve `scripts/guide/serve_guide.py`), FR et EN.
4. AGENT.md : ajouter ou corriger un parcours si l'élément en change un ; `ancres.json` si l'élément mérite une
   ancre choisie.
5. Bancs : `test_agent_catalogue`, `test_agent_connaissance`, `test_agent_aide`.
6. Preuve : poser une question sur l'élément au tiroir (moteur local ou réponse simulée) et vérifier la réponse +
   le pointage.
7. Mettre à jour le suivi des chantiers si la tâche y figure.

Les skills `guide-deepotus` et `traduction-deepotus` gagnent une ligne : « après une livraison visible, lancer
connaissance-agent ».

## 6. Lots (suivi des chantiers, lot « Assistant Demander »)

| Lot | Contenu | Taille |
|---|---|---|
| C1 | Format du catalogue + extracteur + `--check`/`--rapport` + banc | M |
| C2 | Rédaction initiale, écran par écran, avec le skill (couverture progressive) | L |
| C3 | Index lexical, rapprochement, intégration dans `demander` + règles d'AGENT.md | M |
| C4 | Relevé de l'écran ouvert dans le tiroir et les labs | M |
| C5 | Skill `connaissance-agent` (+ lignes dans guide-deepotus et traduction-deepotus) | S |

C5 est écrit en premier (il fixe la procédure) ; C1 → C3 → C4 ; C2 avance en parallèle une fois C1 livré.

## Risques

- **Volume de rédaction (C2)** : des milliers de libellés ; on ne rédige que les éléments **interactifs** (pas
  chaque phrase d'aide) et on couvre écran par écran ; un écran non couvert ne bloque pas le banc.
- **Libellés composés à l'exécution** (« Générer {mode} ») : le localisateur utilise le gabarit sans variable ou
  l'infobulle ; sinon la fiche reste sans localisateur (non pointable, mais décrite).
- **Dérive** : tenue par `--check` et le banc, qui échouent dès qu'une source change.
- **Taille du message** : 15 fiches et ≤ 120 éléments visibles bornés ; mesuré en C3.
