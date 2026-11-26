# B5 (t329, option) — appels WhatsApp et agent vocal : note de décision

Date : 26/11/2026. Statut : **en attente d'une décision de l'utilisateur**. Rien n'est construit, rien n'est dépensé.
Relevé fait le 26/11 en lecture seule (aucun compte créé) : docs.kapso.ai (calling/overview, receive-calls,
outbound-calls, recordings-and-transcripts, voice-agents, pricing-faq), dépôts gokapso `whatsapp-voice-agent-pipecat` et
`whatsapp-voice-agent-starter`, daily.co/pricing/pipecat-cloud, docs.pipecat.ai (regions), developers.facebook.com
(cloud-api/calling, calling/pricing).

## Ce que la doc dit (faits)
- **Kapso relaie la signalisation, pas le son.** L'appel arrive par le webhook `calls` (`connect`, offre SDP), on répond
  `pre_accept` / `accept` / `terminate` en moins de 10 s. **Le son WebRTC va directement de Meta à un serveur média**,
  joignable en **UDP**, avec un relais TURN si besoin. Kapso précise qu'un tunnel (Tailscale Funnel…) livre les webhooks
  mais ne rend pas l'UDP joignable.
- **Appel sortant** : il faut d'abord la **permission d'appel** du contact (`call_permission_request` dans la fenêtre de
  24 h, ou par modèle). La permission se vérifie par `call_permissions`. Meta limite à 1 demande par jour et 2 par semaine,
  et révoque la permission après 4 appels sans réponse. Au plus 100 appels sortants par jour et par contact.
- **Prix Meta** : **tous les appels reçus sont gratuits**. Les appels émis sont facturés par tranches de 6 s, selon le
  pays appelé (grilles EUR du 01/04/2026, montant pour la France à lire dans la grille). Les demandes de permission sont
  facturées comme des messages. L'enregistrement et la transcription sont gratuits « pour l'instant ». Kapso ne prend pas
  de marge.
- **Conditions** : un numéro Cloud API **dédié** avec `calls_enabled` et une limite d'au moins 2 000 destinataires par
  jour. Les appels ne marchent pas dans le bac à sable Kapso. Un numéro en coexistence garde ses appels dans l'app
  WhatsApp Business.
- **Enregistrements et transcriptions** : `GET /api/v1/whatsapp_calls/{uuid}` puis `…/artifacts/recording` (32 Mio au
  plus) et `…/artifacts/transcription`, conservés **7 jours chez Meta**. `calls.details` et `fetchArtifact`, cités dans
  la tâche, n'existent pas sous ces noms.
- **Pipecat Cloud** (Daily) : de 0,01 $ à 0,03 $ par minute d'agent actif, selon la taille. La reconnaissance vocale, le
  modèle et la synthèse vocale sont facturés à part. Régions : us-west (par défaut), us-east, eu-central (Francfort),
  ap-south.

## Ce qui en découle pour DeepotusVideo
- L'app tourne sur le PC, **sans adresse publique** (décision de toujours, lot 4 : « pas de serveur à nous »). **Un agent
  vocal ne peut donc pas tourner sur le PC** sans une adresse HTTPS publique et un port UDP joignable ou un TURN.
- Les données vocales **sortent de chez l'utilisateur** dans toutes les options hébergées : c'est la même question que
  l'agent hors ligne (§12 de la spec mère).

## Options
| | Option | Hébergement | Coût par minute (ordre de grandeur) | Données |
|---|---|---|---|---|
| A | **Pipecat Cloud par l'intégration Kapso**, région eu-central, avec le persona, les horaires et les mots interdits de l'espace (déjà dans `agent_whatsapp.systeme`) | Daily (Francfort) | 0,01 $ d'agent, plus la reconnaissance, le modèle et la synthèse vocales | voix et transcription chez Daily et chez les fournisseurs de modèles |
| B | **Serveur « starter » (Python) hébergé** (Railway ou un petit serveur), ElevenLabs Agents | un serveur loué (le VPS Hostinger existe déjà) | ElevenLabs à la minute, plus l'hébergement | voix chez ElevenLabs, serveur à nous |
| C | **Sur le PC** derrière un tunnel et un TURN | PC + TURN loué | TURN et modèles | chez l'utilisateur, sauf les modèles |
| D | **Reporter** : garder les messages (B1-B4) ; un appel entrant reste dans WhatsApp Business ou est refusé | — | 0 | — |

Dans tous les cas, côté PC : le webhook `calls` passe par Kapso (pas besoin de route publique au PC si l'agent est
hébergé), les transcriptions et enregistrements relus par `whatsapp_calls/{uuid}` et rangés dans le journal de
l'espace, un plafond par espace (catégorie `whatsapp_appels`), les appels sortants seulement avec permission et devis.

## Recommandation (choix de Claude)
**D maintenant, A plus tard en n'acceptant que les appels reçus** : les appels reçus sont gratuits côté Meta, et seule la
minute d'agent est payée (eu-central). L'émission d'appels viendrait ensuite, avec devis et permission. Si le VPS
Hostinger doit servir, B est l'alternative qui garde le serveur chez nous.

## Questions à l'utilisateur
1. Option retenue : A, B, C ou D ?
2. Pour A ou B : accepte-t-on que la voix et les transcriptions passent chez un hébergeur (Daily ou ElevenLabs) ?
3. Appels émis (payants à la minute, permission du contact exigée) dès le départ, ou seulement les appels reçus ?
