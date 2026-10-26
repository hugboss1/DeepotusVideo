# Relevé documentaire Kapso (lecture seule, 27/10/2026)

Sources : pages publiques docs.kapso.ai (index https://docs.kapso.ai/llms.txt), spécifications OpenAPI https://docs.kapso.ai/api/platform/v1/openapi-platform.yaml et .../api/meta/whatsapp/openapi-whatsapp.yaml, https://kapso.com/pricing, pages Meta publiques. Aucun appel d'API, aucun compte. ATTENTION : les pages ont été lues via un outil qui résume ; les noms de champs viennent de ces extraits, à re-vérifier contre l'OpenAPI brute avant de coder.

## 0. Généralités
- Page : https://docs.kapso.ai/api/introduction.md
- Bases : Platform `https://api.kapso.ai/platform/v1` ; proxy WhatsApp `https://api.kapso.ai/meta/whatsapp/v24.0` (v24.0 = version actuelle documentée) ; Workflows = même base que Platform.
- Auth : en-tête `X-API-Key` pour les trois API. Le proxy WhatsApp accepte aussi `Authorization: Bearer ...` (jeton Meta, "rétrocompatibilité"). Une seule clé de projet suffit pour Platform + proxy.
- Format d'erreur : Platform = `{"error": "<texte>"}` (parfois avec `code`, ex. `marketing_preference_stopped`). Proxy = `{"error": {"message","type","code", "error_subcode"?, "fbtrace_id"?}}` (forme Meta).
- Deux familles de lecture : Platform (`/platform/v1/whatsapp/...`, à plat sur tout le projet, filtre par `phone_number_id`) et proxy (`/{phone_number_id}/...`, forme Meta + extension `kapso`).

## 1. Platform API : customers, setup links, numéros

### 1.1 Créer un customer
- POST `https://api.kapso.ai/platform/v1/customers` — https://docs.kapso.ai/api/platform/v1/customers/create-customer.md
- En-têtes : `X-API-Key`, `Content-Type: application/json`.
- Corps : `{"customer": {"name": string (requis), "external_customer_id": string|null}}`.
- Réponse 201 : `{"data": {"id" (UUID), "name", "external_customer_id", "created_at", "updated_at"}}`.
- Erreurs : 401 (clé absente/invalide), 422 (validation). Corps `{"error": string}`.

### 1.2 Lister customers
- GET `/platform/v1/customers` — https://docs.kapso.ai/api/platform/v1/customers/list-customers.md
- Query : `name_contains`, `external_customer_id`, `created_after`, `created_before`, `per_page` (min 1, défaut 20), `page` (défaut 1).
- Réponse : `{"data": [Customer...], "meta": {"page","per_page","total_pages","total_count"}}` ; en-têtes `X-Total`, `X-Total-Pages`, `X-Per-Page`, `X-Page`, `Link`. Plus récent d'abord. Pagination par page (pas curseur). Erreur 401.
- Maximum de `per_page` : NON TROUVÉ.

### 1.3 Lire un customer
- GET `/platform/v1/customers/{customer_id}` (UUID) — https://docs.kapso.ai/api/platform/v1/customers/get-customer.md
- Réponse 200 `{"data": Customer}` ; 401, 404 `{"error"}`.
- Existent aussi PATCH (update) et DELETE `/customers/{customer_id}` (pages update-customer / delete-customer, non lues en détail).

### 1.4 Créer un setup link
- POST `/platform/v1/customers/{customer_id}/setup_links` — https://docs.kapso.ai/api/platform/v1/setup-links/create-setup-link.md et guide https://docs.kapso.ai/docs/platform/setup-links/create-and-configure.md
- En-têtes : `X-API-Key`, `Content-Type: application/json`.
- Corps : `{"setup_link": {...}}`, tous champs optionnels :
  - `success_redirect_url`, `failure_redirect_url` (URI|null)
  - `language` : `en`,`es`,`pt`,`hi`,`id`,`ar` ou null (défaut : langue du navigateur). PAS de `fr` documenté.
  - `allowed_connection_types` : tableau de `coexistence`, `dedicated` (défaut les deux ; une seule valeur = choix automatique)
  - `meta_billing_mode` : `customer_managed` (défaut, le client paie Meta) | `partner_managed` (Kapso paie Meta et débite les crédits du projet). "Cannot be changed after creation" ; pour changer, créer un nouveau lien. `partner_managed` exige l'app Meta par défaut de Kapso ou une app Tech Provider via Multi-partner Solution active.
  - `provision_phone_number` (bool, défaut false) ; `phone_number_country_isos` (défaut ["US"]) ; `phone_number_area_code` (US seulement). Hors US = identifiants de téléphonie propres au projet requis.
  - `reconnect_phone_number` (E.164) : rafraîchir les identifiants d'un numéro existant ; exige provision false et mêmes connection types.
  - `allowed_origins` (HTTPS, pour `@kapso/sdk` ; inutile avec la page hébergée), `theme_config` (couleurs hex `#RRGGBB` : primary_color, background_color, text_color, muted_text_color, card_color, border_color, etc.).
- Réponse 201 : `{"data": {"id","status" (active|used|expired|revoked),"created_at","expires_at" (défaut 30 jours, nullable),"url" (page hébergée),"token" (renvoyé UNIQUEMENT à la création ; pour `@kapso/sdk`, à ne pas exposer),"success_redirect_url","failure_redirect_url","allowed_origins","allowed_connection_types","meta_billing_mode","theme_config","provision_phone_number","phone_number_area_code","phone_number_country_isos","reconnect_phone_number","language","whatsapp_setup_status" (pending|processing|completed|failed),"whatsapp_setup_error","provisioned_phone_number" ({id,phone_number,status,area_code,country_iso,country_dial_code,display_number}, optionnel)}}`.
- Erreurs : 401, 404 (customer inconnu), 422 `{"error": string}`.
- Durée : pas de paramètre de durée documenté (expiration fixée à 30 jours par défaut). Paramètre pour la régler : NON TROUVÉ.
- Mise à jour d'un lien : PATCH `/customers/{customer_id}/setup_links/{setup_link_id}` (page update-setup-link, non lue). Quelles options restent modifiables : NON TROUVÉ.
- Le guide précise : la page hébergée ne permet pas au client de changer la politique de facturation ni d'ajouter une mention ; expliquer l'accord avant d'envoyer le lien. Terminer la liaison ne prouve pas que la facturation Kapso a été attachée.

### 1.5 Savoir que la liaison est finie SANS webhook
Page : https://docs.kapso.ai/docs/platform/setup-links/detect-connection.md
- Option A (navigateur) : redirection vers `success_redirect_url` avec les paramètres `setup_link_id`, `status=completed`, `phone_number_id`, `business_account_id`, `whatsapp_config_id` (hérité), `provisioned_phone_number_id`, `display_phone_number` (URL-encodé). Échec : `setup_link_id` + `error_code` parmi `facebook_auth_failed`, `phone_verification_failed`, `waba_limit_reached`, `token_exchange_failed`, `link_expired`, `already_used`. Pas fiable seule (le client doit revenir). Une appli de bureau sans URL publique ne peut pas recevoir cette redirection facilement (pourrait pointer vers une page statique qui affiche l'id) : à décider.
- Option B (lecture) : GET `/platform/v1/customers/{customer_id}/setup_links` (page https://docs.kapso.ai/api/platform/v1/setup-links/list-setup-links.md). Query : `status` (active|used|expired|revoked), `created_after`, `created_before`, `per_page`, `page`. Réponse `{"data":[SetupLink...],"meta":{page,per_page,total_pages,total_count}}`, plus récent d'abord. Terminé quand `whatsapp_setup_status == "completed"` ; `whatsapp_setup_error` si `failed`. Erreurs 401, 404. Il n'existe pas de GET d'un lien unique dans l'index (liste seulement).
- Lister les numéros du customer : GET `/platform/v1/whatsapp/phone_numbers?customer_id=<uuid>` — https://docs.kapso.ai/api/platform/v1/phone-numbers/list-phone-numbers.md
  - Query : `phone_number_id`, `business_account_id`, `customer_id` (uuid), `messaging_enabled` (bool), `name_contains`, `created_after`, `created_before`, `per_page` (défaut 20), `page`.
  - Réponse `{"data":[...],"meta":{...}}`. Champs d'un numéro : `id` (= ID Meta du numéro), `internal_id` (UUID Kapso), `phone_number_id`, `meta_app_id`, `name`, `business_account_id`, `is_coexistence`, `inbound_processing_enabled`, `calls_enabled`, `webhook_verified_at`, `created_at`, `updated_at`, `customer_id`, `display_name`, `display_phone_number`, `display_phone_number_normalized`, `verified_name`, `quality_rating` (GREEN|YELLOW|RED|null), `code_verification_status`, `name_status`, `status`, `throughput_tier`, `whatsapp_business_manager_messaging_limit`, `is_official_business_account`, `is_pin_enabled`. `business_portfolio_id` et `business_verification` : seulement via GET d'un numéro.
  - Un numéro apparaît avec `customer_id` quand la liaison est terminée : sonder ce GET en plus du setup link est donc possible (inférence, pas confirmé par la doc).
  - Erreur documentée : 401 seulement.
- Autres : GET `/whatsapp/phone_numbers/{phone_number_id}` (détail), GET `/whatsapp/phone_numbers/{phone_number_id}/health` (`status` healthy|degraded|unhealthy|error, `timestamp`, `retry_after`, `error`, `checks`). Dans l'OpenAPI, `{phone_number_id}` de ces chemins : à confirmer s'il s'agit de l'ID Meta ou interne.

## 2. Envoi par le proxy
Page : https://docs.kapso.ai/api/meta/whatsapp/messages/send-a-message.md
- POST `https://api.kapso.ai/meta/whatsapp/v24.0/{phone_number_id}/messages` ; `X-API-Key` (ou Bearer). Optionnel `X-Kapso-Take-Control: true` (numéros partagés).
- Champs communs : `messaging_product: "whatsapp"` (requis), `type` (requis : text, image, video, audio, document, sticker, location, contacts, interactive, template, reaction), `to` (numéro ou ID de groupe) OU `recipient` (BSUID ou BSUID parent) ; si les deux, `to` l'emporte ; ne jamais mettre un BSUID dans `to`. `recipient_type` : `individual` (défaut) | `group`. `context.message_id` pour répondre.
- Texte : `{"type":"text","text":{"body":..., "preview_url": false}}`.
- Modèle : `{"type":"template","template":{"name","language":{"code"},"components":[{"type":"header|body|button","parameters":[...]}]}}`. Paramètres nommés : `parameter_name` ; positionnels : sans nom, remplissent {{1}}, {{2}} dans l'ordre. Boutons : `sub_type` (url|quick_reply|flow), `index` en chaîne ("0"). Exemple de structure complète des paramètres : non relevé en détail.
- Interactif à boutons : `{"type":"interactive","interactive":{"type":"button","body":{"text"<=1024},"action":{"buttons":[{"type":"reply","reply":{"id"<=256,"title"<=20}}]}}}` (1 à 3 boutons).
- markRead : même URL, corps `{"messaging_product":"whatsapp","status":"read","message_id":"<wamid>"}` ; `typing_indicator: {"type":"text"}` optionnel (disparaît à l'envoi ou ~25 s).
- Réponse 200 : `{"messaging_product","contacts":[{"input","wa_id" (envoi par numéro),"user_id" (envoi par BSUID)}],"messages":[{"id" (wamid),"message_status"? (accepted|held_for_quality_assessment)}]}`.
- Envoi marketing dédié : POST `/{phone_number_id}/marketing_messages` (https://docs.kapso.ai/api/meta/whatsapp/messages/send-a-marketing-message.md) : `type` obligatoirement `template`, `recipient_type` seulement `individual`, `to`|`recipient`, `biz_opaque_callback_data` (<=512). Même réponse. Pas d'info sur la nécessité de l'utiliser pour des modèles MARKETING (le send normal l'accepte-t-il ?) : NON TROUVÉ.
- BSUID (https://docs.kapso.ai/docs/whatsapp/business-scoped-user-ids) : répondre avec `to` si `message.from` existe, sinon `recipient = from_user_id`. Limites : fenêtre 24 h toujours requise hors modèle ; les numéros sandbox ne supportent pas les destinataires BSUID ; les modèles d'authentification ne peuvent pas être envoyés à un BSUID ; un BSUID est propre au portefeuille propriétaire du numéro émetteur ; une page contradictoire sur le calendrier (envois BSUID "début juillet 2026" vs "fonctionnent déjà") : à vérifier.
- Erreurs listées : 400 (ex. format de numéro), 401, 402 (facturation : `insufficient_credits`, `service_credits_exhausted`, `pricing_missing`, codes préfixés `service_`), 404 (numéro inconnu), 409 (`message_in_flight` = réessayer vite ; ou blocage de propriété `thread_not_owner` / `thread_ownership_unknown` / `meta_business_agent_control` ; les modèles passent quand même), 422 (`131047` fenêtre expirée ; `1026` destinataire incapable ; `marketing_preference_stopped` ; `messaging_account_mismatch`).

## 3. Lecture sans webhook

### 3.1 Messages — deux variantes
A. Platform : GET `/platform/v1/whatsapp/messages` — https://docs.kapso.ai/api/platform/v1/messages/list-messages.md
- Query : `phone_number_id`, `conversation_id` (uuid), `phone_number` (partiel), `business_scoped_user_id`, `direction` (inbound|outbound), `status` (pending|sent|delivered|read|failed), `message_type`, `has_media`, `limit` (1-100, défaut 20), `before`, `after` (curseurs Base64). PAS de `since`.
- Réponse : `{"data":[...],"paging":{"cursors":{"before","after"},"next","previous"}}`, plus récent d'abord.
- Message : requis `id`, `timestamp` (secondes Unix, CHAÎNE), `type`, `kapso`. Autres : `from`, `from_user_id`, `from_parent_user_id`, `to`, `to_user_id`, `to_parent_user_id`, `username`, `context{id,from,referred_product}`, et le contenu sous la clé du type (`text{body}`, `image`, `template`, `interactive`, `reaction`...). `type` : text, image, video, audio, document, location, interactive, template, reaction, contacts, sticker, button, order.
- `kapso` : `direction`, `status`, `whatsapp_conversation_id` (requis) ; `processing_status`, `origin` (cloud_api|business_app|history_sync), `phone_number`, `phone_number_id`, `has_media`, `contact_name`, `content` (texte à plat), `statuses` (historique brut Meta : id, status, timestamp, recipient_id), `transcript`, `media_data{url,filename,content_type,byte_size}`, `media_url`, `message_type_data`, `flow_response`, `flow_token`, `flow_name`, `order_text`.
- Erreur : 401 seulement.
- Un message : GET `/platform/v1/whatsapp/messages/{message_id}` (wamid), réponse `{"data": {...}}`.

B. Proxy : GET `/meta/whatsapp/v24.0/{phone_number_id}/messages` — https://docs.kapso.ai/api/meta/whatsapp/messages/list-messages.md
- Query : `conversation_id`, `direction`, `status`, `since` (ISO 8601, créés >= ), `until`, `limit` (1-100), `before`, `after`, `fields` (ex. `kapso(direction,status,processing_status)`).
- Réponse : `{"data":[...],"paging":{"cursors":{"before","after"}}}`. Ici `status` est sous `kapso`, pas au niveau supérieur. Le `since` n'existe que sur cette variante : utile pour une reprise par horodatage ; sinon reprise par curseur.
- Erreurs : 400, 401, 404 (numéro) `{"error":{message,type,code}}`.
- Sens de parcours : "plus récent d'abord" ; `after` = page suivante (donc plus ancienne) : pour un suivi incrémental, retenir le dernier `id`/`timestamp` vu et relire depuis la tête jusqu'à le retrouver. Un curseur de reprise « nouveaux messages depuis X » en dehors de `since` : NON TROUVÉ.
- Champs absents : `wa_id` n'est pas au niveau du message (seulement dans les contacts) ; `business_scoped_user_id` n'est pas dans le format Meta (équivalents `from_user_id`/`to_user_id`) mais est un filtre et un champ du format Kapso à plat selon la page BSUID. Messages sans numéro : `from` peut être absent.

### 3.2 Conversations
- Platform : GET `/platform/v1/whatsapp/conversations` — https://docs.kapso.ai/api/platform/v1/conversations/list-conversations.md. Query : `phone_number_id`, `phone_number`, `status` (active|ended), `assigned_user_id`, `unassigned`, `created_after/before`, `last_active_after/before`, `limit` (1-100), `before`, `after`. Réponse `data` + `paging` (comme ci-dessus). Erreurs 401, 422.
- Proxy : GET `/{phone_number_id}/conversations` (https://docs.kapso.ai/api/meta/whatsapp/conversations/list-conversations.md) : `status`, `assigned_user_id`, `unassigned`, `last_active_since`, `last_active_until`, `phone_number`, `limit`, `before`, `after`, `fields`. Erreurs 400, 401, 404, 422.
- Détail : GET `/{phone_number_id}/conversations/{conversation_id}` ; Platform : GET `/platform/v1/whatsapp/conversations/{conversation_id}`.
- Champs conversation : `id`, `phone_number` (null si BSUID seul), `business_scoped_user_id`, `parent_business_scoped_user_id`, `username`, `status`, `last_active_at`, `created_at`, `updated_at`, `whatsapp_config_id` (proxy), `phone_number_id`, `metadata`, et `kapso{contact_name, messages_count, last_message_id, last_message_type, last_message_timestamp, last_message_text, last_inbound_at, last_outbound_at}`.
- Fenêtre 24 h : se calcule avec `kapso.last_inbound_at` de la conversation (ouverte si now - last_inbound_at < 24 h). Sur le proxy, ajouter `fields=kapso()` pour obtenir l'extension (à confirmer qu'elle n'est pas incluse par défaut). Alternative : dernier message `kapso.direction == "inbound"`, `timestamp` en secondes. La doc ne donne pas de formule officielle : NON TROUVÉ (le calcul ci-dessus est une déduction ; le refus 422 `131047` fait foi).

### 3.3 Contacts
- GET `/platform/v1/whatsapp/contacts` (liste ; page de doc de la liste non lue, déduit de l'OpenAPI) : query `customer_id`, `customer_external_id`, `has_customer`, `profile_name_contains`, `wa_id_contains`, `business_scoped_user_id`, `created_after`, `created_before`, `page` (déprécié), `per_page`, `limit`, `before`, `after`. Réponse détaillée : NON LU.
- GET/PATCH/DELETE `/platform/v1/whatsapp/contacts/{identifier}` : identifiant = UUID, numéro ou BSUID ; 409 avec UUID candidats si ambigu. Contact : `wa_id`, champs BSUID, `username`.

## 4. Modèles
Page : https://docs.kapso.ai/api/meta/whatsapp/templates/list-message-templates.md
- GET `/meta/whatsapp/v24.0/{business_account_id}/message_templates` (le résumé dit "pour ce numéro" : contradiction, l'identifiant du chemin est l'ID WABA, `business_account_id` du numéro).
- Query : `name`, `status` (APPROVED|PENDING|REJECTED ; DISABLED existe selon https://docs.kapso.ai/docs/whatsapp/templates/lifecycle.md), `category` (AUTHENTICATION|MARKETING|UTILITY), `language` (ex. en_US), `limit` (1-100, défaut 20). Aucun paramètre de curseur documenté pour renvoyer `after` (alors que `paging.cursors` est dans la réponse) : à vérifier.
- Réponse : `{"data":[{"id","name","language","status","category","previous_category"?,"components":[...]}],"paging":{"cursors":{before,after}}}`. `parameter_format` (NAMED/POSITIONAL) : NON TROUVÉ dans la spec ; il faudra lire `components` (présence de `example.body_text_named_params`, forme Meta, non confirmée).
- Erreur : 401.
- Variante côté Platform (synchronisation) : POST `/whatsapp_templates/sync` (lifecycle) ; templates Platform ont `quality_score` (GREEN|YELLOW|RED|UNKNOWN|null). Chemin exact, hors index : NON TROUVÉ.
- Créer/mettre à jour : POST sur le même chemin (page create-or-update, non lue). Sync désactivée pour les numéros sandbox.

## 5. Opt-out marketing et erreurs
Page : https://docs.kapso.ai/docs/whatsapp/templates/marketing-opt-outs.md
- GET `https://api.kapso.ai/platform/v1/whatsapp/contacts/{identifier}/marketing_preferences` (identifier = UUID du contact ou numéro) ; `X-API-Key`. Pas de pagination. Réponse `{"data":[{"id","phone_number_id","status" (stopped|resumed),"detail","source" (meta_webhook|meta_delivery_error|meta_synchronous_error),"marketing_allowed","config_display_name","last_event_at","created_at","updated_at"}]}`. Tableau vide = abonné partout.
- GET `.../marketing_preferences/{phone_number_id}` pour un numéro. Erreurs 404 : "Marketing preference not found" (= abonné, pas d'enregistrement), "WhatsApp contact not found", "WhatsApp configuration not found" (lire le texte du message pour distinguer).
- Envoi MARKETING à un contact arrêté : 422 `{"error":"Contact stopped marketing messages on this WhatsApp number","code":"marketing_preference_stopped"}`, refusé avant Meta, non facturé, NE PAS réessayer ; passer par modèle utility/authentication ou autre numéro. Seuls les modèles MARKETING sont bloqués ; utility, authentication et messages libres en fenêtre ouverte passent. Blocage par numéro. Aucune API ne permet de réabonner ; le client le fait dans WhatsApp. Webhook (inutilisable ici) : `whatsapp.contact.marketing_preference_changed` avec `sequence`.
- 131050 (Meta, https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes/) : destinataire désinscrit du marketing, ne pas réessayer. Kapso en tire la source `meta_delivery_error`/`meta_synchronous_error`.
- 131070 : ABSENT de la page Meta des codes et de la doc Kapso. NON TROUVÉ.
- 409 `thread_not_owner` : cité seulement dans la page d'envoi (liste des 409), avec `thread_ownership_unknown` et `meta_business_agent_control`. Contexte numéros partagés (propriété `this_app|other_app|idle|unknown`) : messages libres exigent que Kapso tienne le fil ; modèles exemptés ; contournement `X-Kapso-Take-Control: true` seulement si Kapso est l'app d'escalade. Passage de contrôle : POST `/{phone_number_id}/thread_control` (corps `messaging_product`, `action` take|release|pass, `to`|`recipient`, `control_pass.target_role`, `metadata`) ; 200 / 403 / 409 `thread_control_in_progress` / 502 (résultat inconnu, ne pas réessayer automatiquement). Source : https://docs.kapso.ai/api/meta/whatsapp/conversations/pass-release-or-take-a-conversation.md. Pour un numéro non partagé (cas de l'appli), probablement sans objet.
- Codes Meta utiles (page Meta ci-dessus) : 131047 fenêtre 24 h dépassée, ne pas renvoyer en message libre, envoyer un modèle ; 130429 débit : réessayer après attente ; 131056 trop de messages au même destinataire : attendre, réessayer ; 131049 bloqué (engagement) : attendre au moins 24 h ; 131026 non livrable (numéro hors WhatsApp, CGU non acceptées) : ne pas boucler ; 131000 inconnu : réessayer ; 132000 nombre de paramètres incorrect ; 132001 modèle absent/non approuvé/langue fausse ; 132012 format de paramètre ; 132015 modèle en pause (qualité) ; 133010 numéro non enregistré ; 131042 problème de paiement ; 1026 destinataire incapable (cité par Kapso, absent de la page Meta). Pas de réessai : 131050, 131047 (tel quel), 131026, 132xxx, 131049 (avant 24 h), 133010, `marketing_preference_stopped`.
- Débit Kapso : 429 + `Retry-After` (voir 6).

## 6. Tarifs et limites
- Forfaits Kapso (https://kapso.com/pricing, https://docs.kapso.ai/docs/whatsapp/pricing-faq.md) : Free 0 $ : 2 000 messages/mois, 1 numéro, 1 Go, 2 $ de crédits + numéro US pré-vérifié ; Pro 25 $ : 100 000 messages, 3 numéros (puis 10 $/numéro/mois), 100 Go ; Platform 299 $ : 1 000 000 messages, 50 numéros (puis 5 $/numéro), 1 To ; Enterprise sur mesure. Appels d'API illimités. Les messages ENTRANTS comptent (et sortants, réactions comprises ; accusés de lecture non). Surcoût au-delà du quota de messages : NON TROUVÉ (la page FAQ n'en parle pas).
- Relevé « une seule clé = beaucoup de numéros » : le forfait Free ne comprend qu'un numéro ; un deuxième exige Pro. Les customers par forfait : NON TROUVÉ.
- Facturation Meta : par message livré, selon catégorie et indicatif du destinataire ; entrants gratuits (https://developers.facebook.com/docs/whatsapp/pricing/). Chez Kapso : crédits Kapso (au prix Meta, FX 5 % pour WABA non USD ; +5 % de frais de facturation gérée en Multi-partner Solution) ou paiement direct à Meta ; le choix vaut pour toute la WABA (https://docs.kapso.ai/docs/whatsapp/meta-message-billing.md). Deux modes côté setup link = `meta_billing_mode`.
- Messages de service : CONFIRMÉ par Meta et Kapso. Depuis le 01/10/2026, les messages non-modèle au-delà de 1 000 messages de service gratuits par numéro et par mois sont facturés ; les messages utility envoyés dans une fenêtre ouverte (jusqu'ici gratuits) le sont aussi ; tarif service = tarif utility pour octobre ; allocation non reportée ; Meta décide ce qui entre dans l'allocation. Fenêtre d'entrée gratuite (pub Click to WhatsApp) : jusqu'à 7 jours, tout gratuit. Exonération associations/gouvernements jusqu'au 31/12/2027. Sans moyen de paiement au 30/09/2026, la livraison des messages de service peut s'arrêter.
- Garde-fous Kapso : pas de blocage préalable de crédits pour un message de service ; si le solde <= 0 et une charge existe, pause de tous les envois potentiellement payants (raison `service_credits_exhausted`, 402) ; 402 avec code `service_...` si le tarif du marché ou le fuseau de la WABA manquent ; modèles : contrôle de crédit existant.
- Grille de prix : section « Rate cards and volume tiers » de https://developers.facebook.com/docs/whatsapp/pricing/ (CSV/PDF par devise, 16 devises ; ligne par marché = indicatif pays, colonnes marketing / utility / authentication / service) ; changements seulement au 1er jour d'un trimestre. Ne pas recopier. Les chiffres ne sont pas dans les pages Kapso.
- Limites de débit Kapso (https://docs.kapso.ai/api/rate-limits.md) : requêtes par minute et par clé : Free 100, Legacy 100, Pro 1 000, Platform 2 000, Enterprise 4 000 ; fenêtre fixe ; sans forfait actif = Free. En-têtes `X-RateLimit-Limit`, `X-RateLimit-Remaining` ; 429 avec `Retry-After: 60` (burst workflows : `Retry-After: 1`, `X-Burst-RateLimit-*`). Réessayer avec attente exponentielle, 5 essais maximum. Meta applique ses propres limites (paliers de messagerie quotidiens pour conversations initiées par l'entreprise ; 429 "Meta API rate limit exceeded").

## 7. Médias
- Dans les messages : `kapso.has_media`, `kapso.media_url` (URI, "Direct media URL"), `kapso.media_data{url, filename, content_type, byte_size}`. Expiration et authentification de ces URL : NON TROUVÉ (la page get-message le dit explicitement).
- Récupérer un média via proxy : GET `https://api.kapso.ai/meta/whatsapp/v24.0/{media_id}?phone_number_id=<id requis>` ; `X-API-Key`. Réponse : `messaging_product`, `id`, `url` (URL temporaire du domaine Meta, expire en 5 min ; auth pour la télécharger non précisée, côté Meta il faut un jeton), `mime_type`, `sha256`, `file_size` (chaîne), `download_url` (URL Kapso avec jeton intégré, valide 4 min), `download_url_expires_at` (ISO 8601). Source : https://docs.kapso.ai/api/meta/whatsapp/media/get-media-url.md. Erreurs 401, 404.
- Téléchargement : GET `https://api.kapso.ai/meta/whatsapp/media_download?token=<token>` (sans version ni en-tête d'auth ; le jeton signé suffit). Réponse : octets du fichier, `Content-Type` du média, `Content-Disposition: inline`, `Cache-Control: private, max-age=240`. 404 si jeton manquant/invalide/expiré ; 502 si échec côté WhatsApp. Source : https://docs.kapso.ai/api/meta/whatsapp/media/download-media-file.md. Domaine : `api.kapso.ai`.
- Envoi d'un média : POST `/platform/v1/whatsapp/media` (Platform) ou upload via proxy (pages upload-media, non lues en détail).

## 8. SDK
@kapso/whatsapp-cloud-api / dépôts gokapso : non lus (le brief le permettait « au besoin » ; l'OpenAPI et les pages de doc ont suffi). La page BSUID indique que le SDK TypeScript accepte `recipient` sur chaque constructeur de message, et que contacts list/get/update ne fonctionnent qu'avec l'URL de base Kapso et la clé API.

## Points à vérifier
1. Contre-vérifier les noms de champs dans l'OpenAPI brute (lecture par résumé automatique) : en particulier la forme de la réponse des modèles (`components`, absence de `parameter_format`), les en-têtes de pagination et le chemin de listage des contacts.
2. Détection de fin de liaison sans webhook : le GET des setup links donne `whatsapp_setup_status` ; confirmer en test qu'il passe à `completed` et que le numéro apparaît alors dans GET `/platform/v1/whatsapp/phone_numbers?customer_id=`, et si `customer_id` y est bien renseigné pour un customer relié par setup link.
3. Durée d'un setup link : 30 jours par défaut, aucun paramètre trouvé pour la changer ; `language` sans français (choisir `en` ou laisser le navigateur décider) ; seul `meta_billing_mode` est dit non modifiable ; effet exact de `customer_managed` quand le client n'a pas de moyen de paiement Meta (messages de service payants depuis le 01/10/2026).
4. Lecture incrémentale : pas de `since` sur la liste Platform ; `since` existe sur la liste du proxy. Ordre du plus récent au plus ancien ; stratégie à tester (arrêt au dernier `id` connu). Pas de formule officielle de la fenêtre 24 h (utiliser `kapso.last_inbound_at`) ; vérifier si `fields=kapso()` est nécessaire pour l'obtenir sur le proxy.
5. Opt-out : `marketing_preferences` est sur Platform par identifiant de contact (UUID ou numéro) ; pas de champ équivalent dans la conversation. Les erreurs 131070 et la forme exacte de `thread_not_owner` (et son lien avec un code Meta) restent NON TROUVÉES ; sans objet probablement pour un numéro non partagé.
6. Envoi MARKETING : confirmer si un modèle de catégorie MARKETING doit passer par `/marketing_messages` ou si `/messages` suffit ; le comportement de `held_for_quality_assessment`.
7. Envoi à un BSUID : modèles d'authentification impossibles ; sandbox non pris en charge ; deux textes de calendrier contradictoires sur l'activation des envois BSUID ; fonctionnement réel à tester sur un numéro de production.
8. Médias : durée de vie et authentification de `kapso.media_url` / `media_data.url` inconnues ; `download_url` ne vit que 4 min (télécharger tout de suite et stocker localement).
9. Tarifs : le prix par message Meta par pays n'est pas dans la doc Kapso (renvoi à Meta) ; surcoût de messages au-delà du quota Kapso inconnu ; nombre de customers par forfait inconnu ; les prix du forfait (25 $, 299 $) viennent de kapso.com/pricing, la FAQ de la doc n'en donne pas.
10. Maximum de `per_page` des listes Platform et gestion exacte du `Link` : non documentés.
11. Domaine : le site marketing est passé de kapso.ai à kapso.com (redirection 301) ; la doc et l'API restent sur docs.kapso.ai / api.kapso.ai.
