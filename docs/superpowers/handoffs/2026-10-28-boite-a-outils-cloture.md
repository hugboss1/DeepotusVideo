# Passage de relais : clôture du chantier « boîte à outils » (t312 à t320, t328) — 28/10/2026

## Où on en est

Tous les lots du chantier restants sont **terminés sur leurs branches, rien n'est poussé ni fusionné dans main**.
La branche `chantier/boite-cloture` (worktree `.claude/worktrees/boite-cloture`) les contient TOUS, fusionnés,
avec les correctifs d'intégration, le guide, la traduction et le catalogue de l'agent (t320).

| Lot | Code | Branche | Tête | Contenu |
|---|---|---|---|---|
| t312 | C1 | `chantier/boite-scan` | 7dce0ae3 | Scanner une page → texte (OCR Windows local, secours Claude sur devis) |
| base | — | `chantier/boite-base-c-d` | 385e01a1 | t312 + origin/main (t353-t354) : base des lots t313-t320 |
| t313 | C2 | `chantier/boite-inspiration` | f65b5b1a | Inspiration → contenu neuf (Planificateur › « Depuis une inspiration ») |
| t314 | C3 | `chantier/boite-schema-motion` | c5d688d7 | Schéma → calques du Vectorlab → animation (Studio) |
| t315 | D1 | `chantier/boite-capture` | f3221655 | « Filmer l'app » (enregistreur, clics, caviardage) |
| t316 | D2 | `chantier/boite-skins` | f1cf9bd9 | Skins de capture (un par espace, éditeur, .zip) |
| t317 | D3 | `chantier/boite-montage-capture` | ae7e13a8 | Monter une capture (zooms, temps morts, chapitres, sous-titres) |
| t318 | D4 | `chantier/boite-live` | bf720108 | Direct multi-destinations (Twitch, YouTube Live, Kick, RTMP, annonce Discord) |
| t319 | D5 | `chantier/boite-tutoriels` | 39e8241a | Tutoriels et parcours partagés (.dzparcours, rejeu « Montrer ») |
| t328 | B3 | `chantier/boite-diffusions-whatsapp` | a4f34918 | Diffusions WhatsApp d'un post du Planificateur |
| t320 | — | `chantier/boite-cloture` | voir `git log -1` (rapport t320) | fusions + guide + traduction + catalogue + relais |

- Installation de référence : **b0bf7b9e** (t311, installée le 26-27/10). origin/main est à **77ddeb6e** (#472,
  prospects t360) : il n'est PAS un ancêtre de `boite-cloture` (la base a pris origin/main à t353-t354).
- Chaîne du bundle dans `boite-cloture` : … → `whatsapppage` → `dzcapture` → `dzinspiration` → `dzdiffusion`
  (queue). t314, t316, t317, t318 et t319 n'ont pas de maillon (fichiers JS séparés, entrées dans les labs ou les
  boîtes). Les inverses sont emboîtés en sens contraire en tête de `backend/tests/_i18n_l1_aide.py`.

## Ordre recommandé des PR

**Option A (recommandée) : une seule PR depuis `chantier/boite-cloture`.**
1. Dans le worktree, `git fetch` puis `git merge origin/main` (conflits additifs attendus : main.py, AGENTS.md,
   index.html, L10, dictionnaire, catalogue ; régénérer `i18n_assembler`, `i18n_l10_erreurs`, `catalogue.py`,
   `construire_guide.py` ; un maillon de bundle arrivé sur main entre-temps se rejoue EN OCTETS, jamais en texte).
2. Rejouer les bancs du rapport t320 (liste plus bas), comparer à origin/main.
3. PR `chantier/boite-cloture` → main, un titre par lot dans la description (le tableau ci-dessus).

**Option B : PR empilées**, si l'utilisateur veut relire lot par lot :
`boite-base-c-d` (t312 + origin/main) → `boite-inspiration` (t313) → `boite-schema-motion` (t314) →
`boite-capture` (t315) → `boite-skins` (t316) → `boite-montage-capture` (t317) → `boite-live` (t318) →
`boite-tutoriels` (t319) → `boite-diffusions-whatsapp` (t328, base t311) → `boite-cloture` (t320 : fusions,
correctifs d'intégration, guide, traduction, catalogue). Chaque PR vise la précédente ; les conflits d'intégration
sont déjà résolus dans les commits de fusion de `boite-cloture` (messages détaillés).

## Bancs de référence (rapport t320)

Verts dans `boite-cloture` : tous les bancs des lots (tutoriels ×3, agent_capture, agent_format, agent_inspiration,
agent_scan, agent_schema, capture ×7, diffusion_ecran, inspiration ×4, kapso_broadcasts, live ×3, scan ×6,
scheduler_whatsapp, schema ×3, skins ×3, whatsapp ×16, canaux_preremplis, espace_assistant_ecran,
garde_client_ecran, pour_qui_ecran, securites_client), transverses (i18n l0-l5, l7-l10, agent_catalogue 109,
agent_boites, agents_md, agent_connaissance, agent_aide, agent_ecran, agent_guide, plafonds_garde,
dialogues_partout, guide_v3 456, etabli_outils_page), `catalogue.py --check`, `i18n_l10_erreurs.py --check`,
`i18n_assembler.py --check`, `construire_guide.py --check`, `node qa/run.mjs` des quatre labs.
Rouges hérités (déjà rouges sur la base 385e01a1 / origin/main) : test_textes_moteur (W14), test_i18n_l6
(mod-didact), test_icones_g3_vectorlab, test_espaces_client, test_p2_diagnostic_bundle, test_i18n_l4_serveur,
test_reglages_traduction (K10).

## Choix à valider par l'utilisateur (repris des registres)

- **t313** : refus dès 12 mots consécutifs repris (lecture prudente de « plus de 12 ») ; l'animation n'est pas
  chiffrée dans la carte (elle passe par « Produire ») ; l'image captée n'est JAMAIS envoyée à fal ; seul point
  d'entrée : le bouton du Planificateur.
- **t314** : aucun maillon de bundle (menu Fichier du Vectorlab, envoi au Studio par `__dzRenderGraph`) ;
  détourage « local-chroma » maison ; ordre de révélation par tri topologique des flèches ; PNG des calques sous un
  nom stable réécrit à chaque envoi ; une analyse relancée refacture le détourage fal (pas de cache).
- **t315** : mode « l'app seule » par défaut (boîtes hors `#root` non filmées) ; onglet invérifiable refusé ;
  écrans secrets de Réglages inertes et floutés pendant une capture.
- **t316** : skin livré « Deepotus » par défaut, signature « Fait avec DeepotusVideo » active (désactivable), y
  compris chez un client ; l'outro est enregistrée (« Arrêter » la joue, ≤ 9 s) ; éditeur ouvert seulement depuis
  « Filmer l'app ».
- **t317** : rendu depuis la piste `scene` (le zoom agrandit aussi l'encart caméra) ; coupes automatiques seulement
  sur les attentes de génération ; brouillon au Planificateur à demain 10 h ; transcription comptée sous
  « montage ».
- **t318** : destinations du direct gérées dans la boîte « Passer en direct » (pas dans Réglages) ; Discord =
  annonce par webhook ; YouTube par clé collée (pas d'OAuth) ; **RTMP_SERVEUR est un champ public : une URL collée
  avec la clé y serait stockée en clair — à trancher**.
- **t319** : titres d'étape tirés du catalogue, jamais du texte lu ; le .dzparcours embarque la piste `scene` ;
  brouillons fabriqués dans `DATA_ROOT/tutoriels/<capture>/` (le registre prévoyait que t320 les « publie » :
  t320 a écrit le guide à partir des vraies captures des preuves, sans publier ces brouillons — voir Suites) ;
  100 parcours importés au plus.
- **t320** : en anglais l'« espace » de marque se dit « space » (WhatsApp, diffusion), « workspace » restant aux
  espaces de travail du Photolab ; doublons FR→EN tranchés (« Relire » = Read again, « refusé » = rejected,
  « désactivé » = off) ; certaines scènes du guide réutilisent une capture FR en anglais faute de capture EN
  (agent WhatsApp, diffusion, découpage du scan, inspiration).

## Constats relevés pendant t320 (chantiers séparés proposés)

- **Vectorlab, raccourcis affichés mais inactifs** : Ctrl+O, Ctrl+A, Ctrl+I, Ctrl+Entrée, Ctrl+Maj+N, Ctrl+,,
  Ctrl+Alt+H, Ctrl+N, Ctrl+Maj+M, Ctrl+Alt+Maj+S, Ctrl+G, Ctrl+Maj+G (core.js ne capte que Z, Y, S, D, C, V, 0, 1).
- **Vectorlab, libellés qui promettent plus** : « Restaurer le brouillon » toujours grisé (`VL.restaurerBrouillon`
  absent) ; « Nouveau depuis Presse-papiers » colle dans le document ouvert ; « Diviser au nœud » ajoute un nœud ;
  « Nouveau calque pixel » pose une image sur le calque actif ; « Créer un symbole » ouvre seulement le menu ;
  « Puissance » et « Sélectionner par attribut » montrent l'onglet Transformer, où leurs boutons ne sont pas.
- **Textes hors lots** : en FR le Planificateur s'intitule « Scheduler » et montre « Analytics » ; l'aperçu de
  Quick dit « Library » ; anglais américain mêlé (« Color », « Analyze ») ; « Détourage » traduit « Remove BG » ;
  108 doublons FR→EN anciens hors lots (homonymes pour la plupart : « Annuler » Undo/Cancel…).
- Les PDF du guide pèsent ~93 Mo (FR) et ~89 Mo (EN), versionnés comme avant.

## Suites

1. Fusionner origin/main dans `boite-cloture`, puis PR (sur demande de l'utilisateur seulement).
2. Publier les brouillons de tutoriels de t319 (scènes du guide à trois temps, fiches de lab) quand l'utilisateur
   aura enregistré ses propres parcours ; remplacer alors les scènes à capture FR seule par des captures EN.
3. Mesurer les repères (curseur, surlignage) des scènes neuves du guide avec `scripts/guide/capturer.js` : elles
   n'ont aujourd'hui que des bulles.
4. Localisateurs des fiches neuves (scan.*, inspiration.*, entrées de menu du Vectorlab) à relever avec
   `verifier_localisateurs.js` pour qu'elles deviennent pointables.
5. Trancher RTMP_SERVEUR (t318) et les constats Vectorlab ci-dessus.
6. Lots suivants du suivi : t329 (B5, appels et agent vocal WhatsApp) ; recette iPhone t304.

## Installation (uniquement sur demande explicite de l'utilisateur)

Script à écrire sur le modèle de `install_t308_t325.py` (méthode « table des hachages » du relais du 26/10) :
- **BASE** = l'installation précédente (b0bf7b9e) ; **CIBLE** = la tête de main après fusion de la PR.
- Pour chaque fichier modifié entre BASE et CIBLE : `git hash-object` (jamais sha256) du fichier installé sous
  `%LOCALAPPDATA%\DeepotusVideoGen`, comparé à BASE ; toute dérive (fichier installé ≠ BASE et ≠ CIBLE) ARRÊTE
  le script sans rien copier. Refaire la table juste avant de copier (installation concurrente).
- Sauvegarde des fichiers touchés et de `deepotus.db` dans `_backup_predeploy_<date>-t312-t320`, puis copie
  depuis `git show CIBLE:<chemin>` en octets (le bundle et les maillons sont en CRLF).
- Exclus : outils de dev restés anciens dans l'installation (`_i18n_l1_aide.py`, `g1_generer.py`,
  `test_etabli_canevas.py`, `test_i18n_l2.py`).
- Fichiers neufs à ne pas oublier : `frontend/dist/shared/dz-{scan,inspiration,capture*,skins*,montage-capture*,
  live*,tutoriels*,diffusion-whatsapp}.js`, `frontend/vectorlab/js/mod-schema.js`, `backend/app/api/{scan,
  inspiration,schema,capture,skins,capture_montage,live,tutoriels}_routes.py` et leurs services, `scan_ocr.ps1`,
  le guide (`docs/guide/*.html`, PDF, `img/`), le catalogue (`docs/agent/**`).
- Ne copier que si 8765 est libre, puis relancer avec `wscript %LOCALAPPDATA%\DeepotusVideoGen\scripts\launch-silent.vbs`
  et vérifier à l'écran en lecture seule (Filmer l'app, Direct, Depuis une inspiration, Scanner une page,
  Vectorlab › Fichier › Scanner un schéma…, guide FR/EN).
