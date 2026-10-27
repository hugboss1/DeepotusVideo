# Agent Campagnes : veille, prospects et prospection humain-dans-la-boucle — spec de conception (brouillon)

*27/10/2026. Choix du §9 TRANCHÉS par l'utilisateur le 27/10 (P0) ; prochaine étape : plan détaillé de P1. Base : `origin/main` 55668f10 (agent interne
t284-t287 : 10 outils, aucun ne dépense ni ne publie ; WhatsApp Kapso t310 fusionné, t311 en cours). Sources :
veille n°1 (`C:\Users\olivi\Campagnes\_veille\2026-10-27\rapport.md`), skill `veille-concurrents`, spec boîte à
outils §5.5 et §6.3.*

## 1. Intention (mots de l'utilisateur, 27/10)

« Pouvoir automatiser depuis une solution IA non seulement des opérations avec humain dans la boucle, mais aussi
trouver automatiquement les leads ou clients auprès desquels mettre en relation l'agent Campagnes, pour planifier
l'envoi et la lecture des réponses vers les futurs prospects intéressés soit par la solution, soit par une
prestation clé en main », en tenant compte de WhatsApp (t310-t311).

Deux offres à servir : **la licence** (DeepotusVideoGen) et **la prestation clé en main** (l'utilisateur produit pour
le client avec l'app — rejoint les espaces « client » de t305-t309).

## 2. Objectifs, non-objectifs, anti-objectifs

- **Objectifs**
  1. La veille du skill `veille-concurrents` devient un **outil de l'agent intégré** (niveau 1 seulement : sources
     ouvertes, lecture seule), avec un écran « Veille » qui montre le rapport et ses angles.
  2. Une **fiche Prospects** (CRM léger, par espace) : qui, d'où vient le signal, quelle offre, quel canal, quels
     consentements, quel statut, prochaine action.
  3. L'agent **repère des signaux** (inbound d'abord, puis signaux publics) et **propose** des prospects qualifiés.
  4. L'agent **rédige** des séquences (1er message, relances) par canal et **les planifie** dans le Planificateur après
     accord ; il **lit les réponses** (WhatsApp, e-mail) et propose la suite ou passe la main.
- **Non-objectifs (ce lot)** : achat de fichiers, enrichissement par des courtiers de données, LinkedIn automatisé,
  pub payante.
- **Anti-objectifs (ce qui ne doit jamais arriver)**
  - un premier message **WhatsApp** à un contact sans accord enregistré (règle §6.3 déjà en place) ;
  - un **DM automatisé** sur X, Instagram ou LinkedIn (interdit par leurs conditions : l'agent rédige, l'humain envoie) ;
  - un e-mail commercial à un **particulier** sans consentement préalable (France, art. L34-5 CPCE) ;
  - un e-mail B2B sans identification de l'expéditeur, sans lien de désinscription, ou après une opposition ;
  - un pseudo ou un commentaire public republié dans un message, ou un prospect contacté **parce qu'il s'est plaint
    sous son nom** sans qu'il ait sollicité d'aide (on répond publiquement à une question publique, à la main, une fois) ;
  - un envoi sans **porte humaine** (comme le skill `campagne` : porte 1 stratégie + liste, porte 2 messages).

## 3. Contraintes légales et de plateforme (dures, côté serveur)

| Canal | Règle | Effet dans l'app |
|---|---|---|
| E-mail B2B (adresse pro) | intérêt légitime : offre liée à la profession, identité, désinscription simple, registre des oppositions | refus 409 sans `base_legale` = `interet_legitime_b2b` + domaine pro ; lien de désinscription obligatoire |
| E-mail particulier | consentement préalable (opt-in) | refus 409 sans consentement daté |
| WhatsApp | accord du contact (§6.3), fenêtre 24 h, modèles approuvés, STOP, préférence marketing Meta | réutilise t310 tel quel ; un prospect WhatsApp = un contact qui a écrit ou s'est inscrit avec WhatsApp coché |
| X / Instagram / LinkedIn | pas de DM automatisé | l'agent produit un **brouillon** ; bouton « Copier et ouvrir » ; l'humain envoie et coche « envoyé » |
| Tous | minimisation (RGPD) : source, date, base légale, durée de conservation (3 ans après dernier contact), droit d'opposition | champ `source` et `base_legale` obligatoires ; purge planifiée ; export / suppression d'un prospect |

## 4. Sources de prospects (par ordre de priorité)

1. **Inbound** (le meilleur et le plus sûr) : liste d'attente (t347), WhatsApp entrant (t310), Telegram, formulaire
   du site, réponses aux posts. Consentement natif.
2. **Signaux publics de besoin** tirés de la veille : posts « alternative à X », « combien de crédits pour… »,
   « je résilie X ». Usage : **réponse publique utile, à la main**, jamais de DM automatique ; si la personne répond
   ou s'inscrit, elle devient un prospect inbound.
3. **Entreprises publiques** (pour la prestation clé en main) : studios indé, agences, marques locales — à partir
   d'informations professionnelles publiées par l'entreprise elle-même (site, page contact). Pas de scraping de
   plateformes qui l'interdisent ; une recherche à la fois, sourcée.

## 5. Ce qu'on ajoute à l'agent (outils)

Les 10 outils existants restent. Nouveaux outils, tous **sans dépense ni envoi** sauf mention :

| Outil | Rôle | Garde |
|---|---|---|
| `veille_collecter` | lance la collecte niveau 1 (HN, YouTube via yt-dlp, App Store) sur un périmètre | lecture seule ; durée et volume plafonnés ; pas de navigateur connecté |
| `veille_lire` | lit le dernier rapport, la matrice, les angles | — |
| `prospects_chercher` | propose des prospects depuis l'inbound et les sources §4 | écrit en `propose`, jamais en `actif` |
| `prospects_qualifier` | score + offre (licence / prestation) + canal possible selon consentements | — |
| `sequence_proposer` | rédige 1er message + 2 relances par canal, dans la voix de l'espace | → porte 2 |
| `sequence_planifier` | met les envois validés dans le Planificateur | **porte humaine** + consentement + plafond + heures calmes |
| `reponses_lire` | lit les réponses (WhatsApp t310, e-mail IMAP) et les résume par prospect | — |
| `relance_proposer` | propose la suite ou « passer à l'humain » (prix, devis de prestation, plainte, STOP) | jamais d'engagement hors fiche produit |

Le compagnon (lot 4) reçoit les cartes « valider ces envois » au doigt (format de conversation v1 déjà partagé).

## 6. Données

`prospects` (par espace) : id, nom/entreprise, rôle, source (url + date), signal (résumé), offre, score, canaux
connus, consentements (canal, base légale, date, moyen), statut (`propose` → `qualifie` → `contacte` → `repondu` →
`rdv` / `client` / `perdu` / `oppose`), historique (messages envoyés/reçus, liens vers le journal WhatsApp),
prochaine action, purge_le. Registre des oppositions global (un « STOP » vaut pour tous les espaces de l'utilisateur).

## 7. Découpage proposé (lot « Veille & prospection », après t350)

| Lot | Contenu | Taille |
|---|---|---|
| P0 | Validation de cette spec (choix §9) — FAIT le 27/10 | S |
| P1 | Veille dans l'app : service + outils `veille_collecter` / `veille_lire` + écran « Veille » | M |
| P2 | Fiche Prospects (CRM léger, RGPD : base légale, purge, opposition, export) | L |
| P3 | Recherche et qualification (inbound d'abord, signaux publics, entreprises) | M |
| P4 | Séquences et brouillons par canal + portes (agent) | M |
| P5 | Canal e-mail : envoi SMTP de l'utilisateur, désinscription, lecture IMAP des réponses | L |
| P6 | WhatsApp prospection : opt-in, modèles marketing, lecture des réponses (après t311) | M |
| P7 | Relances, passage à l'humain, tableau de bord du pipeline | M |
| P8 | Compagnon : valider les envois, répondre au doigt, générer la campagne témoin d'un espace démonstration | M |
| P9 | Clôture : guide, traduction, catalogue de l'assistant | S |

## 8. Ce qui reste hors de l'app livrée

La veille **niveau 2** (X, Instagram dans le Chrome connecté) reste une séance assistée par Claude Code chez
l'utilisateur : l'app vendue ne pilote pas le navigateur connecté d'un client.

## 9. Décisions de l'utilisateur (P0, 27/10/2026)

1. **E-mail : les deux, au choix par espace.** Par défaut, la boîte SMTP/IMAP de l'utilisateur (envoi + lecture des
   réponses) ; un service d'envoi (Brevo…) branchable par espace pour les gros volumes. P5 livre d'abord SMTP/IMAP,
   puis l'adaptateur de service derrière la même interface (`envoyer`, `lire_reponses`, `desinscrire`).
2. **Espace client : dès le rendez-vous ET à la signature.**
   - au statut `rdv`, l'app crée un **espace « démonstration »** (persona, marque, produits du prospect) pour que le
     compagnon mobile génère une **campagne témoin** qui aide à convertir. Cet espace **ne publie jamais** : aucun
     canal de publication, aucun consentement de publication ; il est archivé si le prospect est `perdu` ;
   - à la **signature**, l'espace démonstration devient l'espace **client** (t305-t309) : canaux, consentements datés
     de publication, mode de publication. La campagne témoin y est conservée comme point de départ.
   - Conséquence : P2 ajoute le type d'espace `demonstration` ; P8 (compagnon) ajoute « générer la campagne témoin ».
3. **Plafond e-mail B2B : 30 par jour et par espace, montée progressive** : 10/jour la 1re semaine, 20 la 2e, 30
   ensuite ; pause automatique si les rebonds dépassent 5 % ou au premier signalement de spam ; réglable dans les
   Réglages, jamais au-delà sans action de l'utilisateur.
4. **Signaux publics : réponse publique, à la main.** L'agent montre le post et un brouillon de réponse utile, sans
   dénigrer ni nommer de prix d'un concurrent ; l'utilisateur publie depuis son compte, une fois par fil. Aucun
   brouillon de message privé. Si la personne répond ou s'inscrit, elle devient un prospect **entrant**.
