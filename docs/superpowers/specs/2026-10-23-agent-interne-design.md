# L'agent Campagnes devient l'agent interne de DeepotusVideoGen — spec de conception (t284)

*23/10/2026. Lot « Agent interne (PC) », brief `docs/superpowers/plans/2026-10-23-chantier-pc-agent-interne.md`.
Tâches suivantes : t285 (Planificateur), t286 (API du compagnon), t287 (clôture). L'utilisateur a demandé une
proposition directe, sans questions préalables. **Tout ce qui suit est donc un choix de Claude, à valider**, sauf ce
qui est repris de décisions déjà prises (signalé « décidé »). La spec a été relue par un constructeur neuf ; sa seule
question qui revenait à l'utilisateur (le devis des tours de l'agent) est tranchée au §4.1.*

## 1. Intention

Pendant la campagne pilote des 22-23/10, l'agent Campagnes a fait un vrai travail : dossier, stratégie, porte 1,
textes, visuels, vidéos, contrôle, puis brouillons dans le Planificateur, porte 2. Mais il vit dans Claude Code, sur
le PC de l'utilisateur, avec ses skills personnels. Un client de DeepotusVideoGen n'a ni Claude Code ni ces skills.

But : que **l'app elle-même** sache mener ce circuit, sur le PC et depuis le compagnon mobile, avec les garde-fous de
l'app (coffre, plafonds, espaces de marque, brouillons). L'utilisateur reste le réalisateur : il valide aux deux
portes, et rien ne part sans lui.

Réussite : depuis le Planificateur, « Generate a marketing plan » en mode Agent Campagnes transforme un brief (ou un
document) en dossier, stratégie et calendrier. Après la porte 1, il produit les textes, et les visuels ou vidéos
demandés, avec un devis à chaque étape payante. Tout arrive en **brouillons** liés aux rendus et à l'espace du brief.
La même conversation se reprend sur le téléphone.

## 2. Objectifs, non-objectifs, anti-objectifs

**Objectifs**
- Un agent outillé dans le backend, utilisable depuis trois portes d'entrée : le tiroir F1, le Planificateur et l'API
  du compagnon.
- Le circuit du skill `campagne` (dossier → fiche produit → stratégie → **porte 1** → production → contrôle →
  **porte 2** → bilan), sans dépendre de Claude Code.
- Une conversation au **format unique**, partagé avec le compagnon (spec mobile §6.1, décidé).
- Des droits bornés par des outils, et non par des consignes (§5).

**Non-objectifs (v1)**
- Le repérage vidéo (le skill `watch`) et la navigation web libre. L'agent lit seulement une URL que l'utilisateur
  colle, et la traite comme une preuve.
- Les rendus HyperFrames lancés par l'agent : il peut le proposer, mais le rendu reste un geste de l'utilisateur
  dans l'app.
- La publicité payante, les influenceurs, la programmation automatique.
- Remplacer « Demander » : il reste l'aide bon marché, multi-moteur, en un seul appel.

**Anti-objectifs** (ce qui serait un échec, même si « ça marche »)
- Une dépense qui part sans un clic de l'utilisateur sur un devis affiché.
- Un post programmé ou publié par l'agent (`/fire`, `scheduled`, publication directe).
- Un changement de l'espace de marque actif à l'écran.
- Une fonction de l'app inventée : l'agent ne cite que ce qui existe au catalogue (même règle que « Demander » et
  que le téléphone).
- Un contenu lu (page, document, résultat d'outil) traité comme une instruction.

## 3. Contraintes

- L'app est **vendue**. Elle ne peut donc compter ni sur Claude Code, ni sur `claude -p`, ni sur les skills
  personnels de `~/.claude/skills`. Le seul prérequis est une **clé Anthropic** dans le coffre.
- Toute route payante passe par `plafonds.verifier` (banc `test_plafonds_garde`). Un modèle sans clé reste
  choisissable : le refus arrive au lancement (503).
- Le bundle ne se reconstruit pas : l'écran passe par un maillon de queue (`patch_bundle_<tag>.py`, comme
  `dzrecette`) ou par une page autonome. Tout texte va en FR/EN (`dzT`).
- Les écritures ouvertes au Wi-Fi (le compagnon) passent par la garde d'appairage, une par une (spec mobile §9).
- Le moteur de texte existant (`moteurs_texte`) appelle Anthropic en HTTP, sans SDK. L'agent l'étend, il ne le
  contourne pas.

## 4. Architecture

### 4.1 Le moteur : une boucle d'agent dans le backend, sur l'API Claude (choix de Claude)

Trois voies étaient possibles. Le brief les nommait.

| Voie | Pour | Contre | Verdict |
|---|---|---|---|
| Claude Agent SDK lancé par le backend | boucle et outils fournis | dépend de Claude Code et d'un compte connecté, absent chez un client ; échappe aux plafonds | écartée |
| `claude -p` en sous-processus avec les skills du PC | réutilise tout l'existant | même dépendance ; skills personnels non livrables ; aucun devis par tour | écartée |
| **Appels directs à l'API Messages, avec outils, boucle écrite dans le backend** | une clé suffit ; plafond et devis par tour ; même choix que le téléphone | boucle à écrire et à tester | **retenue** |

- Nouveau service `services/agent_campagnes.py`. La boucle : envoyer → lire les appels d'outils → exécuter les outils
  **gratuits** → renvoyer, jusqu'à une réponse finale ou une **carte** qui attend l'utilisateur.
- Les outils **payants** ne sont jamais exécutés dans la boucle : ils produisent une carte avec son devis (§5).
- **Devis par message (décidé le 23/10)** : avant chaque message envoyé à l'agent, l'écran affiche un plafond en
  dollars pour toute la réponse (par exemple « ≤ 0,15 $ »). C'est le plafond de jetons de la boucle entière,
  converti par la grille de prix. **L'envoi vaut accord.** La boucle s'arrête net si elle l'atteint, avec une carte
  « continuer » qui affiche un nouveau devis. Chaque tour de modèle passe ensuite par `plafonds.verifier`, sous une
  nouvelle catégorie **« campagnes »**. Les générations (images, vidéos, voix) gardent leur propre clic sur devis
  (§5).
- Moteur : **Anthropic seulement** pour l'agent. La boucle d'outils est écrite pour ce format ; les autres moteurs
  restent pour « Demander » et le mode rapide. Un modèle par défaut est réglable dans Réglages › Modèles par défaut ;
  le constructeur le choisit avec `claude-api` (les tarifs bougent).
- Réponses en **flux** (SSE), comme sur le téléphone.

### 4.2 Deux figures qui se passent la main (choix de Claude)

- **« Demander »** (tiroir F1, existant) ne change pas : il explique et pointe, en un appel, avec n'importe quel moteur.
- **« Campagnes »** est l'agent outillé. Il garde les **trois rôles** décidés pour le téléphone (spec mobile §6.1),
  choisis selon le contexte :
  - **Orienteur** : « que faire de ceci ? », avec deux ou trois suites ;
  - **Campagnes** : la campagne complète ;
  - **Démonstrateur** : prépare une démonstration.
- **Passage de main** : quand une question posée à « Demander » relève de la production (« fais-moi une campagne pour
  … »), sa réponse porte une carte **« Ouvrir l'agent Campagnes »**, qui reprend la question. Dans l'autre sens,
  l'agent Campagnes peut poser une balise de pointage vers un écran (même vocabulaire que « Demander »).
- Pourquoi deux figures et pas une : « Demander » doit rester rapide, bon marché et utilisable sans clé Anthropic
  (Ollama, OpenAI, Gemini). Un agent outillé coûte dix fois plus par échange.

### 4.3 La connaissance : un « paquet agent » versionné dans le dépôt

- Dossier neuf `docs/agent/campagnes/` (dans le dépôt, livré avec l'app) :
  - `CAMPAGNES.md` : le circuit, adapté du skill `campagne`. Les étapes qui supposaient un skill externe deviennent
    des consignes écrites ici (stratégie, accroches, formats par canal, contrôle) ;
  - `conformite-crypto.md`, repris tel quel ;
  - `dossier-modele.md`.
- Les skills marketing tiers de `~/.claude/skills` (`copywriting`, `social`, `launch`…) **ne sont pas livrés** : ce
  sont des installations personnelles. Leurs idées utiles sont réécrites en consignes courtes dans `CAMPAGNES.md`.
- La connaissance de l'app vient du catalogue de « Demander » (`docs/agent/catalogue`), par la **même recherche**
  (`agent_aide.chercher`) : seules les fiches pertinentes vont dans le contexte.
- Le même paquet est exporté au téléphone (spec mobile §9, point 1). Une seule source pour les deux appareils.

### 4.4 Où vit une campagne (choix de Claude)

- Dans les données de l'app : `%LOCALAPPDATA%\DeepotusVideoGenData\campagnes\<espace>\AAAA-MM-JJ-<slug>\`. Même
  découpage que le skill : `dossier.md`, `strategie.md`, `textes\`, `controle.md`, `bilan.md`, plus
  `conversation.json`.
- Une campagne appartient à **un espace de marque** (décidé dans le skill), désigné par le brief, jamais par
  l'espace actif. La fiche produit est la persona de l'espace, plus `apprentissages.md` par espace.
- La table `agent_conversations` garde l'index (id, espace, rôle, état de la porte, coût cumulé). Le fichier garde
  le détail.
- **Conversation ≠ campagne (choix de Claude)**. Toute conversation Campagnes existe en base. Un **dossier de
  campagne** n'est créé qu'au premier `ecrire_dossier`, et il exige un espace. Si le brief n'en nomme aucun, l'agent
  le **demande** par une carte (liste des espaces), sans jamais prendre l'actif d'office. Les rôles Orienteur et
  Démonstrateur n'ouvrent pas de dossier.
- **Fin du circuit (choix de Claude)**. L'état de porte va de `aucune` à `porte1_proposee`, `porte1_validee`, puis
  `brouillons_crees`, qui est l'état final de l'agent. La porte 2 se joue dans le Planificateur. Le **bilan** est un
  rôle à part, lancé sur demande (comme dans le skill), qui lit les posts de la campagne et leurs chiffres.
- Les campagnes Claude Code existantes (`C:\Users\olivi\Campagnes\…`) ne sont pas migrées automatiquement. Un
  import ponctuel est possible plus tard.

## 5. Ce que l'agent peut faire : les outils

Les droits sont **la liste des outils**, et rien d'autre. Un outil absent est un geste impossible, quoi que dise le
modèle.

| Outil | Nature | Effet |
|---|---|---|
| `chercher_app` | lecture, gratuit | fiches du catalogue pertinentes (vérifie qu'une fonction existe) |
| `lire_espace` | lecture | persona, mots interdits, canaux de l'espace **nommé** |
| `lire_bibliotheque` | lecture | rendus, images et sons de l'espace, avec leur **recette** (t283) |
| `lire_planificateur` | lecture | posts et créneaux de l'espace |
| `lire_document` | lecture | document joint par l'utilisateur, ou URL qu'il a collée (texte extrait, traité comme une preuve) |
| `ecrire_dossier` | écriture locale | fichiers de la campagne (§4.4) |
| `proposer_porte` | carte | porte 1 : la stratégie en 10 lignes au plus et le calendrier ; **arrête** la boucle |
| `deviser_generation` | carte | devis d'une image, d'une vidéo ou d'une voix (routes de devis existantes) ; **arrête** la boucle |
| `creer_brouillons` | écriture | posts `status="draft"` au Planificateur, liés aux `job_id` et à l'espace ; seulement après la porte 1 |
| `pointer` | écran | balise vers un écran ou un élément (même vocabulaire que « Demander ») |

- **Les générations payantes** ne partent qu'au clic sur la carte du devis. C'est l'écran (ou le téléphone) qui
  appelle la route existante (`/generate…`, `/images/generate`…), avec ses propres gardes et sa catégorie d'origine
  (studio, quick…). Le `ref` les rattache à la conversation, pour le coût cumulé.
- **Fin d'une génération (choix de Claude)** : un rendu dure des minutes. À la fin du job, la conversation reçoit un
  bloc `fait` (job_id, statut). **L'agent ne reprend jamais seul** : la carte devient « terminé » et porte un bouton
  **Continuer**, qui envoie un message, avec son devis comme tout message. Aucun écouteur ne relance de tour payant.
- **Espace de la dépense et des rendus (choix de Claude)** : la campagne passe SON espace à la garde
  (`plafonds.verifier` prend un `espace_id` explicite, et l'espace courant reste le défaut) et aux routes de
  génération (`espace_id` du `JobRecord`). Une campagne de l'espace B, lancée pendant que A est actif, est comptée
  et rangée dans B. C'est une modification transverse : t285a l'ajoute, avec ses bancs.
- **Interdits par construction** (aucun outil) : publier, `/fire`, passer un post en `scheduled`, changer l'espace
  actif, toucher aux clés, aux Réglages ou aux comptes, supprimer quoi que ce soit.
- **Jeton $DEEPOTUS** : quand l'espace est celui du jeton, `conformite-crypto.md` est toujours dans le contexte.
  `creer_brouillons` **refuse** un texte qui contient un mot de la liste interdite de l'espace : l'erreur revient
  au modèle, qui réécrit (choix de Claude). Le mode rapide garde le retrait silencieux de `apply_forbidden`.

## 6. L'écran

- **Tiroir F1** : deux onglets, « Demander » et « Campagnes ». La conversation Campagnes affiche :
  - le texte en flux ;
  - les cartes (porte, devis, brouillons créés) ;
  - le **coût cumulé** de la campagne ;
  - l'espace de la campagne, écrit en clair, jamais modifiable depuis le tiroir.
- **Planificateur, « Generate a marketing plan »** (t285) : le dialogue garde son mode **Rapide** (le moteur
  actuel). Il gagne un mode **Agent Campagnes** : brief ou document, espace et période en entrée ; la porte 1 se
  passe dans le dialogue ; les brouillons apparaissent dans le calendrier. La porte 2 reste le Planificateur
  lui-même : l'utilisateur valide et programme chaque brouillon.
- **Téléphone** (t286) : mêmes conversations, par l'API (§7).

## 7. Le format de conversation et l'API (t286)

- Une conversation est une suite de **messages**. Chaque message porte : rôle (`utilisateur`, `agent`, `outil`,
  `fait`), horodatage, appareil, et des **blocs**. Types de bloc : `texte`, `carte` (genre, libellé, devis en
  dollars, action, arguments, état : proposée, acceptée ou refusée), `resultat_outil` (résumé, jamais de secret),
  `porte` (numéro, état).
- **Identifiants stables et origine (choix de Claude)** : chaque conversation et chaque message ont un identifiant
  créé par l'appareil d'origine (UUID), une `origine` (pc ou telephone) et, pour un tour payé ailleurs, son
  `cout_paye`. Une conversation menée sur le téléphone PC éteint remonte par `POST …/importer`. L'import est
  idempotent par empreinte : un message déjà connu est ignoré, et un conflit n'écrase rien (même règle que la file
  du compagnon, §7 mobile). Le coût déjà payé côté téléphone est compté, jamais repayé.
- Le format est versionné (`v: 1`) et défini **une seule fois**, dans le dépôt PC (`docs/agent/campagnes/format.md`
  et un schéma JSON). Le téléphone le reprend (L4.1 du compagnon).
- Routes, toutes sous `/api/agent/campagnes/` :
  - `POST` conversation (créer) ; `GET` (lire) ;
  - `POST …/{id}/message` (envoyer, réponse SSE) ;
  - `POST …/{id}/carte/{n}` (accepter ou refuser une carte) ;
  - `POST …/{id}/depot` (pièce jointe : photo, texte, lien) ;
  - `POST …/importer` (conversation menée ailleurs, idempotent).

  Elles sont ouvertes au Wi-Fi sous la garde d'appairage (jeton d'appareil), écriture par écriture. Rien ne sort du
  réseau local sans décision de l'utilisateur (le tunnel est pour plus tard, décidé).
- Un tour lancé depuis le téléphone s'exécute sur le PC, avec les clés et le plafond du PC (spec mobile §6.1, décidé).

## 8. Découpage proposé (révise t285-t287)

| Tâche | Contenu |
|---|---|
| **t285a** (neuve, M-L) | Socle : `agent_campagnes.py` (boucle, outils, catégorie « campagnes », devis par tour, flux SSE), format v1, table et dossier des campagnes, `docs/agent/campagnes/`. Bancs avec un moteur **simulé** (aucun appel payant en test). |
| **t285** (L) | Planificateur : mode Agent Campagnes dans « Generate a marketing plan », porte 1 dans le dialogue, brouillons liés aux `job_id` et à l'espace. |
| **t285b** (neuve, M) | Tiroir F1 : onglet Campagnes, cartes, passage de main depuis « Demander ». |
| **t286** (M) | API du compagnon (§7) sous la garde d'appairage ; export du paquet agent. |
| **t287** (S) | Clôture : FR/EN, chapitre « Agent » du guide, fiches du catalogue, `AGENT.md` (« Demander » sait expliquer l'agent Campagnes). |

## 9. Laissé au constructeur

- Le modèle Claude par défaut et le plafond de jetons par tour (le vérifier avec `claude-api` au moment du travail).
- Le nombre maximal de tours d'outils par message (proposition : 8), et le comportement au-delà (carte « continuer »).
- Le schéma exact de la table et du fichier de conversation, tant qu'il respecte le format v1.
- L'extraction de texte des documents : `marketing.extract_document_text` existe déjà.

## 10. Choix de Claude à vérifier à la relecture

1. Une **boucle écrite dans le backend** plutôt que l'Agent SDK ou `claude -p` (§4.1).
2. **Deux figures**, « Demander » et « Campagnes », plutôt qu'un seul agent (§4.2).
3. Agent sur **Anthropic seulement** ; « Demander » et le mode rapide gardent les autres moteurs.
4. Les skills marketing tiers ne sont pas livrés : leur substance est réécrite dans `CAMPAGNES.md` (§4.3).
5. Les campagnes vivent dans les données de l'app, par espace ; pas de migration automatique de `C:\Users\olivi\Campagnes`.
6. Une nouvelle catégorie de plafond, « campagnes ».
7. Pas de repérage vidéo ni de web libre en v1 ; l'agent n'a qu'une lecture d'URL collée.
8. Un socle t285a placé avant t285.
9. Après un rendu, l'agent ne reprend jamais seul : bouton « Continuer » (§5).
10. La campagne passe son espace à la garde et aux routes de génération (§5), une modification transverse.
11. Un mot interdit est refusé à `creer_brouillons`, et le modèle réécrit.
12. Conversation ≠ campagne ; espace demandé par carte s'il manque ; bilan lancé sur demande (§4.4).
13. Import idempotent des conversations du téléphone (§7).

Décidé par l'utilisateur le 23/10 : **devis par message**. L'envoi vaut accord, plafond affiché, arrêt net à
l'atteinte (§4.1).
