# Relevé API Kapso Broadcasts (diffusions WhatsApp en masse)

Date : 2026-10-27. Lecture seule. Sources : docs.kapso.ai (llms.txt, pages Broadcasts, fiches d'endpoints `/api/platform/v1/broadcasts/*.md`, openapi-platform.yaml partiel), dépôt gokapso/whatsapp-broadcasts-example (`src/lib/kapso-api.ts`, README). L'API est marquée « alpha, susceptible de changer » par Kapso.

## 1. Base et authentification

- Base URL plateforme : `https://api.kapso.ai/platform/v1` ; les routes broadcast sont sous `/whatsapp/...`, soit `https://api.kapso.ai/platform/v1/whatsapp/broadcasts`.
- Authentification : en-tête `X-API-Key: <clé>` (schéma `ApiKeyAuth`, confirmé par la spec OpenAPI et l'exemple). Corps JSON : `Content-Type: application/json`.
- Corps d'entrée toujours enveloppé dans une clé `whatsapp_broadcast` (sauf `schedule`, voir plus bas).
- Spécifications OpenAPI disponibles : `https://docs.kapso.ai/api/platform/v1/openapi-platform.yaml` (très volumineux, ~424 000 caractères ; seuls les 100 000 premiers lus, section `paths` non lue — les fiches individuelles ont servi de source). Index : `https://docs.kapso.ai/llms.txt` ; texte complet : `https://docs.kapso.ai/llms-full.txt`.
- Concerne aussi l'API Meta proxifiée (templates) : `https://api.kapso.ai/meta/whatsapp/v23.0` (vu dans l'exemple), non détaillée ici.

## 2. Endpoints (tous sous `/platform/v1/whatsapp`)

| # | Méthode et chemin | Rôle | Succès | Erreurs documentées |
|---|---|---|---|---|
| 1 | `GET /broadcasts` | Liste, plus récents d'abord | 200 | 401 |
| 2 | `POST /broadcasts` | Crée un brouillon | 201 | 401, 404 (numéro ou template introuvable), 422 |
| 3 | `GET /broadcasts/{id}` | Détail et compteurs | 200 | 401, 404 |
| 4 | `PATCH /broadcasts/{id}` | Arrêter (`stopped`) ou annuler une planification (`draft`) | 200 | 401, 404, 422 |
| 5 | `POST /broadcasts/{id}/recipients` | Ajoute des destinataires (max 1000/appel) | 201 | 401, 404, 422 |
| 6 | `GET /broadcasts/{id}/recipients` | Liste paginée des destinataires | 200 | 401, 404 |
| 7 | `DELETE /broadcasts/{id}/recipients` | Vide tous les destinataires | 200 | 401, 404, 422 |
| 8 | `POST /broadcasts/{id}/send` | Envoi immédiat (asynchrone) | 202 | 401, 404, 422 |
| 9 | `POST /broadcasts/{id}/schedule` | Planifie | 202 | 401, 404, 422 |
| 10 | `POST /broadcasts/{id}/cancel` | Annule une planification | 200 | 401, 404, 422 |

`{id}` est un UUID. Il n'existe pas d'endpoint DELETE d'un broadcast dans la liste (la doc mentionne une « suppression » dans le tableau de bord pour la duplication ; endpoint API : non confirmé, absent de llms.txt).

### 2.1 Créer : `POST /broadcasts`

Corps :
```json
{"whatsapp_broadcast": {"name": "...", "phone_number_id": "1234567890", "whatsapp_template_id": "784203120908608"}}
```
- `name` (string, requis) : libellé de campagne.
- `phone_number_id` (string, requis) : identifiant du numéro WhatsApp d'envoi (id Meta du numéro, exemple `1234567890`). Doit être un numéro de production (pas sandbox).
- `whatsapp_template_id` (string, requis) : id Meta du template (préféré) ou UUID interne Kapso (héritage). Template approuvé exigé.
- Le broadcast est donc lié à un numéro et à UN template ; la langue est portée par le template (`whatsapp_template.language_code`, ex. `en_US`), pas par un champ de la requête. Pour un même nom en plusieurs langues, il faut l'id du template de la bonne langue (déduction ; non confirmé explicitement par la doc).

Réponse 201 `{"data": <WhatsappBroadcast>}` avec `status: "draft"` (voir 3).

### 2.2 Ajouter des destinataires : `POST /broadcasts/{id}/recipients`

- Seulement sur un broadcast `draft` (la page de vue d'ensemble dit aussi `scheduled` pour ajout/vidage ; la fiche de l'endpoint dit « draft broadcast »). Rejeté (422) si un import CSV/contacts est en cours ou si `copying`.
- Max 1000 recipients par requête ; minItems 1. Doublons ignorés.
- Corps :
```json
{"whatsapp_broadcast": {"recipients": [
  {"phone_number": "14155550123",
   "components": [{"type": "body", "parameters": [
      {"type": "text", "parameter_name": "first_name", "text": "John"},
      {"type": "text", "parameter_name": "discount", "text": "SAVE50"}]}]}
]}}
```
- Par destinataire : `phone_number` (string E.164 ; requis sauf si `whatsapp_contact_id` fourni), `whatsapp_contact_id` (uuid d'un contact Kapso existant, optionnel), `components` (tableau de composants au format Meta).
- Composant : `type` requis parmi `header`, `body`, `button` ; `sub_type` (boutons : `url` ou `quick_reply`) ; `index` (entier base 0, boutons) ; `parameters`.
- Paramètre : `type` (`text`, `image`, `video`, `document`), `parameter_name` (variable nommée du template), `text`, ou objet `image`/`video`/`document` (ex. `{"link": "https://..."}`) pour les en-têtes média. Exemple bouton URL dynamique : `{"type":"button","sub_type":"url","index":0,"parameters":[{"type":"text","text":"..."}]}`.
- Format du numéro : la spec de réponse (recipient) dit « E.164, sans plus » (`14155550123`). Les exemples de requête de la doc utilisent `+14155550123`. Les deux semblent acceptés en entrée ; la sortie est sans `+`. Non confirmé : la règle exacte de normalisation. Recommandation : envoyer sans `+` ou avec `+` de façon cohérente et comparer à la sortie en retirant le `+`.
- BSUID (identifiant utilisateur WhatsApp) : l'API d'ajout ne prend que `phone_number` ou `whatsapp_contact_id`. Une page « BSUIDs » existe dans la doc et le endpoint « Get contact » accepte un BSUID, mais l'usage d'un BSUID comme destinataire de broadcast : non confirmé.
- Paramètres par destinataire : passés via `components` ; les paramètres nommés (`parameter_name`) correspondent aux variables nommées du template, sinon positionnels dans l'ordre. Le nombre doit correspondre au template.
- Réponse 201 (même si certains destinataires échouent) :
```json
{"data": {"added": 495, "duplicates": 5, "errors": ["Recipient 3: template parameters invalid - requires 2 parameters but got 1", "Recipient 7: invalid phone number format"]}}
```
`errors` est un tableau de chaînes, avec l'index du destinataire dans le lot (« Recipient N »). Exemple de l'exemple Next.js : CSV, colonne 1 = numéro E.164, colonnes suivantes = paramètres dans l'ordre.

### 2.3 Lister les destinataires : `GET /broadcasts/{id}/recipients?page=1&per_page=20`

- `page` et `per_page` (entiers min 1). Défaut et maximum de `per_page` : non documentés (l'exemple de réponse montre 20 ; le client d'exemple utilise 20 par défaut). Pas de filtre par statut documenté.
- Réponse 200 : `{"data": [...], "meta": {"page", "per_page", "total_pages", "total_count"}}` et en-têtes `X-Total`, `X-Total-Pages`, `X-Per-Page`, `X-Page`, `Link`.
- Objet destinataire : `id` (uuid), `phone_number` (E.164 sans +), `status`, `sent_at`, `failed_at`, `delivered_at`, `read_at`, `responded_at` (date-time ou null), `error_message` (string|null), `error_details` (objet|null), `template_components`, `created_at`, `updated_at`.
- Itération : incrémenter `page` jusqu'à `meta.total_pages`.

### 2.4 Envoyer / planifier / annuler / arrêter

- `POST /broadcasts/{id}/send` (sans corps) : 202 `{"data": {"id", "status": "sending", "scheduled_at": null, "started_at": "...", "stopped_at": null, "completed_at": null}}`. Asynchrone ; suivre via `GET /broadcasts/{id}`. Sondage conseillé toutes les 5 à 10 s.
- `POST /broadcasts/{id}/schedule` corps `{"scheduled_at": "2025-10-12T17:00:00Z"}` (à plat, sans enveloppe `whatsapp_broadcast`, d'après la fiche ; ISO 8601 avec fuseau, dans le futur ; le broadcast doit être `draft` avec destinataires). 202, `status: "scheduled"`. Code d'erreur si pas de destinataires / date passée : 422 probable, non confirmé.
- `POST /broadcasts/{id}/cancel` : uniquement si `scheduled` ; 200, retour à `draft`, `scheduled_at` effacé. (Équivalent : `PATCH` avec `status: "draft"`.)
- Arrêt : `PATCH /broadcasts/{id}` corps `{"whatsapp_broadcast": {"status": "stopped"}}`, seulement si `sending`. Réponse 200 avec `stopped_at`. Les destinataires `pending` restent `pending`, plus aucun envoi n'est lancé.
- Vider : `DELETE /broadcasts/{id}/recipients` (draft ou scheduled ; un broadcast planifié repasse en `draft`), 200 avec le broadcast.

## 3. Objet broadcast (`data`)

Champs : `id` (uuid), `name`, `status`, `scheduled_at`, `started_at`, `stopped_at`, `completed_at` (nullables), `created_at`, `updated_at`, `phone_number_id` (string|null), `whatsapp_template` (objet|null), compteurs `total_recipients`, `pending_count`, `sent_count`, `delivered_count`, `read_count`, `failed_count`, `suppressed_count`, `responded_count`, `response_rate` (float, pourcentage de `responded_count` sur `sent_count`).

`whatsapp_template` : `id` (id Meta sinon UUID), `meta_template_id`, `name`, `language_code`, `category` (ex. `MARKETING`), `status` (ex. `approved`), `quality_score` (`GREEN`/`YELLOW`/`RED`/`UNKNOWN`/null, valeur courante), `components` (définition Meta : BODY, HEADER, BUTTON, avec exemples `body_text_named_params`).

Statuts du broadcast (enum) : `draft`, `scheduled`, `copying` (duplication en cours, « Preparing » au tableau de bord), `sending`, `stopped`, `completed`, `failed`.
Transitions : `draft` -> `sending` -> `completed|failed|stopped` ; `draft` -> `scheduled` -> `sending` ; `scheduled` -> `draft` (cancel) ; `copying` -> `draft` ou `failed`. Pendant un import CSV/contacts ou `copying`, les modifications renvoient 422.
Note : l'exemple de création omet `suppressed_count` bien qu'il soit dans le schéma ; le traiter comme optionnel (défaut 0).

## 4. Statuts par destinataire

Enum documenté dans la spec : `pending`, `sent`, `failed`, `suppressed`. Il n'y a PAS de statut `delivered` ni `read` : la distribution est lue via `delivered_at` / `read_at` / `responded_at` non nuls (le statut reste `sent`). `failed` : `failed_at`, `error_message`, `error_details` (`error_class`, et selon le cas `code`, `message`, `details`, `http_status`, `fbtrace_id` de Meta ; exemple : code 131047).

## 5. Suppression (désinscription marketing)

- Un contact ayant arrêté les messages marketing sur CE numéro est `suppressed` : rien n'est envoyé, rien n'est facturé. `error_details.code = "marketing_preference_stopped"` plus un champ `detail`.
- Appliqué aux templates de catégorie marketing uniquement (pas utilitaire/authentification). La préférence est par numéro d'envoi : un autre numéro atteint le contact.
- `suppressed_count` exclu des dénominateurs de `sent_count` et `failed_count`.
- Si Meta rejette avec l'erreur 131050, Kapso enregistre la désinscription, le destinataire reste `failed` (pas `suppressed`) et les envois marketing suivants seront `suppressed`.
- Webhook : `whatsapp.contact.marketing_preference_changed`. API de lecture : endpoints « List marketing preferences » / « Get marketing preference » (chemins exacts non relevés).

## 6. Limites, erreurs, idempotence, tarifs

- 1000 destinataires par appel d'ajout ; envoi cadencé automatiquement par Kapso selon le débit WhatsApp (taille de lot variable, chiffres non publiés). Broadcast = template uniquement ; numéro de production uniquement ; template approuvé.
- Limite de débit API (page https://docs.kapso.ai/api/rate-limits, relevée via une recherche web, pas lue directement) : par minute et par clé API (par IP sans clé), fenêtre fixe : Free 100, Legacy 100, Pro 1000, Platform 2000, Enterprise 4000 (le changelog confirme le doublement des limites payantes ; l'ancien chiffre subsiste dans llms-full.txt). 429 avec en-têtes de débit : réessayer avec backoff exponentiel en respectant `Retry-After` ; lire `X-RateLimit-Remaining`. À reconfirmer en lisant la page.
- Format d'erreur : corps `{"error": "<message>"}` pour 401 (clé absente/invalide), 404, 422. 429 et 5xx non décrits dans les fiches broadcast. Le client d'exemple lit `error` ou à défaut formule un message avec le code HTTP.
- Idempotence : aucune clé d'idempotence documentée. Seuls les doublons de numéro dans un broadcast sont ignorés (`duplicates`). Il faut donc ne pas rejouer `send` aveuglément ; relire l'état (`GET`) avant de réessayer. Comportement d'un `send` répété sur un broadcast déjà `sending` : non confirmé (422 probable).
- Tarifs : pas de tarif propre aux broadcasts dans les pages lues. Pages existantes : https://docs.kapso.ai/docs/whatsapp/pricing-faq (facturation Kapso et Meta, non lue). Les suppressed ne sont pas facturés. Frais Meta sur les templates marketing : non confirmé ici.

## 7. Pièges pour le client Python

1. Enveloppe `whatsapp_broadcast` partout, sauf `schedule` (corps `scheduled_at` à plat).
2. Créer avec `phone_number_id` + id Meta du template ; pas de champ langue.
3. Découper les destinataires par lots de 1000, lire `errors` même en 201 (renvoie des chaînes, pas des objets).
4. Pas de statut `delivered`/`read` côté destinataire : utiliser les horodatages.
5. Après `send` (202) : sonder `GET /broadcasts/{id}` jusqu'à `completed|failed|stopped`.
6. Normaliser les numéros pour comparer (`+` absent en sortie).
7. Gérer 429 avec `Retry-After`.

## 8. Non confirmé (résumé)

Défaut et maximum de `per_page` ; filtre par statut sur la liste des destinataires ; format exact accepté (avec ou sans `+`) ; BSUID en destinataire ; code HTTP pour dates passées ou broadcast vide ; envoi répété ; suppression d'un broadcast par API ; tarification ; chemins exacts des endpoints de préférence marketing ; lecture directe de la page de limites de débit ; section `paths` du fichier OpenAPI (non lue).
